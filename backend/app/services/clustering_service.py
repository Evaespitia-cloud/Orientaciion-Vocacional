"""
Servicio de Clustering K-Means sobre perfiles RIASEC de estudiantes.

Agrupa estudiantes por similitud de puntajes Holland, selecciona
automáticamente k óptimo via silhouette score y persiste resultados en BD.
"""

import numpy as np
from itertools import combinations
from sklearn.cluster import KMeans
from sklearn.preprocessing import StandardScaler
from sklearn.decomposition import PCA
from sklearn.metrics import silhouette_score

from ..extensions import db
from ..models.resultado import PerfilVocacional
from ..models.aplicacion import Aplicacion
from ..models.ml_models import ClusteringResultado, ClusteringAsignacion

AREAS_HOLLAND = ['Realista', 'Investigador', 'Artístico', 'Social', 'Emprendedor', 'Convencional']
CODIGOS_RIASEC = {
    'Realista': 'R',
    'Investigador': 'I',
    'Artístico': 'A',
    'Social': 'S',
    'Emprendedor': 'E',
    'Convencional': 'C',
}

# Catálogo canónico de las 15 parejas no dirigidas posibles en RIASEC.
# Se genera desde AREAS_HOLLAND para que nombres y códigos no dependan del orden
# en que K-Means entregue los dos centroides dominantes.
NOMBRES_PATRON = {
    ('Realista', 'Investigador'): 'Técnico-Científico',
    ('Realista', 'Artístico'): 'Técnico-Creativo',
    ('Realista', 'Social'): 'Técnico-Social',
    ('Realista', 'Emprendedor'): 'Técnico-Emprendedor',
    ('Realista', 'Convencional'): 'Técnico-Administrativo',
    ('Investigador', 'Artístico'): 'Científico-Creativo',
    ('Investigador', 'Social'): 'Científico-Humanista',
    ('Investigador', 'Emprendedor'): 'Científico-Emprendedor',
    ('Investigador', 'Convencional'): 'Científico-Administrativo',
    ('Artístico', 'Social'): 'Creativo-Social',
    ('Artístico', 'Emprendedor'): 'Creativo-Emprendedor',
    ('Artístico', 'Convencional'): 'Creativo-Administrativo',
    ('Social', 'Emprendedor'): 'Social-Líder',
    ('Social', 'Convencional'): 'Social-Administrativo',
    ('Emprendedor', 'Convencional'): 'Empresarial-Administrativo',
}
PARES_RIASEC = tuple(combinations(AREAS_HOLLAND, 2))


class ClusteringService:

    @staticmethod
    def catalogo_combinaciones():
        """Lista las 15 combinaciones RIASEC disponibles para ML."""
        return [
            {
                'codigo': ''.join(CODIGOS_RIASEC[area] for area in pareja),
                'nombre': NOMBRES_PATRON[pareja],
                'areas': list(pareja),
            }
            for pareja in PARES_RIASEC
        ]

    @staticmethod
    def _pareja_riasec(areas):
        """Devuelve la combinación canónica para las dos áreas dominantes."""
        if len(areas) != 2 or frozenset(areas) not in {frozenset(par) for par in PARES_RIASEC}:
            raise ValueError('Las áreas dominantes deben formar una pareja RIASEC válida.')
        pareja = next(par for par in PARES_RIASEC if set(par) == set(areas))
        return {
            'codigo': ''.join(CODIGOS_RIASEC[area] for area in pareja),
            'nombre': NOMBRES_PATRON[pareja],
            'areas': list(pareja),
        }

    @staticmethod
    def _construir_matriz(configuracion_id=None):
        """
        Construye la matriz de características RIASEC a partir de perfiles completos.
        Retorna (app_ids, X numpy array) o raise ValueError si datos insuficientes.
        """
        # Subquery: última aplicación completada por estudiante
        # Usar una sola medición por estudiante evita que el mismo perfil
        # aparezca múltiples veces y distorsione la separación de clusters.
        filtro_estado = Aplicacion.estado == 'completada'
        if configuracion_id:
            filtro_estado = db.and_(filtro_estado, Aplicacion.configuracion_id == configuracion_id)

        subq = (
            db.session.query(
                Aplicacion.usuario_id,
                db.func.max(Aplicacion.fecha_fin).label('max_fecha')
            )
            .filter(filtro_estado)
            .group_by(Aplicacion.usuario_id)
            .subquery()
        )

        perfiles = (
            PerfilVocacional.query
            .join(Aplicacion)
            .join(
                subq,
                db.and_(
                    Aplicacion.usuario_id == subq.c.usuario_id,
                    Aplicacion.fecha_fin == subq.c.max_fecha,
                )
            )
            .filter(Aplicacion.estado == 'completada')
            .all()
        )

        app_ids, X = [], []
        for perfil in perfiles:
            datos = perfil.datos_json or {}
            puntajes = datos.get('puntajes_por_area', {})
            if not puntajes:
                continue
            row = [puntajes.get(area, {}).get('normalizado', 0.0) for area in AREAS_HOLLAND]
            X.append(row)
            app_ids.append(perfil.aplicacion_id)

        if len(X) < 6:
            raise ValueError(
                f'Se necesitan al menos 6 aplicaciones completadas con perfiles RIASEC. '
                f'Actualmente hay {len(X)}.'
            )

        return app_ids, np.array(X, dtype=float)

    @staticmethod
    def _describir_cluster(centroide_dict, n_estudiantes, cluster_idx):
        """Genera descripción textual de un cluster a partir de su centroide."""
        sorted_areas = sorted(centroide_dict.items(), key=lambda x: x[1], reverse=True)
        top2 = tuple(a for a, _ in sorted_areas[:2])
        combinacion = ClusteringService._pareja_riasec(top2)
        area_baja = sorted_areas[-1][0]
        return {
            'cluster': cluster_idx,
            'nombre': f"Grupo {cluster_idx + 1}: {combinacion['nombre']}",
            'combinacion_riasec': combinacion,
            'n_estudiantes': n_estudiantes,
            'centroide': centroide_dict,
            'areas_dominantes': list(top2),
            'area_menos_frecuente': area_baja,
            'interpretacion': (
                f'Estudiantes con alta afinidad hacia {top2[0]} y {top2[1]}. '
                f'Menor desarrollo en el área {area_baja}.'
            ),
        }

    @staticmethod
    def ejecutar(configuracion_id=None, n_clusters=None):
        """
        Ejecuta K-Means optimizado para máxima silueta.
        """
        app_ids, X = ClusteringService._construir_matriz(configuracion_id)

        # --- 1. FILTRADO DE RUIDO (Perfiles Planos) ---
        # Calculamos la desviación estándar de cada perfil
        std_per_student = X.std(axis=1)
        # Umbral: excluir perfiles donde la diferencia entre áreas sea mínima (ruido)
        umbral_ruido = 0.08
        mascara_ruido = std_per_student >= umbral_ruido

        # Datos para entrenar (sin ruido)
        X_train = X[mascara_ruido]
        app_ids_train = np.array(app_ids)[mascara_ruido]

        if len(X_train) < 6:
            # Fallback en caso de tener muy pocos datos válidos
            X_train = X
            app_ids_train = np.array(app_ids)
            mascara_ruido = np.ones(len(X), dtype=bool)

        # --- 2. IPSATIZACIÓN (Normalización por Sujeto) ---
        X_mean = X_train.mean(axis=1, keepdims=True)
        X_std = X_train.std(axis=1, keepdims=True)
        X_std[X_std == 0] = 1.0
        X_ipsat = (X_train - X_mean) / X_std

        # --- 3. ESTANDARIZACIÓN DE COLUMNAS (StandardScaler) ---
        scaler = StandardScaler()
        X_scaled = scaler.fit_transform(X_ipsat)

        # --- 4. REDUCCIÓN DE DIMENSIONALIDAD CON PCA ---
        # Reducimos a 3 componentes principales para concentrar la varianza
        pca = PCA(n_components=3, random_state=42)
        X_features = pca.fit_transform(X_scaled)

        # --- 5. BÚSQUEDA DEL K ÓPTIMO ---
        if n_clusters is None:
            max_k = min(6, len(X_train) // 3)
            max_k = max(max_k, 2)
            best_k, best_sil = 2, -1.0
            for k in range(2, max_k + 1):
                if len(X_train) / k < 3:
                    continue
                km = KMeans(n_clusters=k, random_state=42, n_init=20, max_iter=500, init='k-means++')
                labels_tmp = km.fit_predict(X_features)
                counts = np.bincount(labels_tmp)
                if counts.min() < 2:
                    continue
                sil = silhouette_score(X_features, labels_tmp)
                if sil > best_sil:
                    best_sil = sil
                    best_k = k
            n_clusters = best_k

        # --- 6. ENTRENAMIENTO DEL MODELO FINAL ---
        kmeans = KMeans(n_clusters=n_clusters, random_state=42, n_init=25, max_iter=600, init='k-means++')
        labels_train = kmeans.fit_predict(X_features)

        sil_score = float(silhouette_score(X_features, labels_train))
        inertia = float(kmeans.inertia_)

        # --- 7. ASIGNACIÓN POST-HOC DE ESTUDIANTES FILTRADOS (RUIDO) ---
        # Para no dejar fuera a los estudiantes de perfil plano, se les asigna al cluster
        # del centroide más cercano en el espacio original.
        labels_final = np.zeros(len(X), dtype=int)
        labels_final[mascara_ruido] = labels_train

        # Calcular centroides en espacio original
        centroides = []
        descripcion_clusters = []
        for k in range(n_clusters):
            mask = labels_final == k
            if mask.sum() > 0:
                centroid_orig = X[mask].mean(axis=0)
            else:
                centroid_orig = X_train[labels_train == k].mean(axis=0)
            centroid_dict = {area: round(float(v), 2) for area, v in zip(AREAS_HOLLAND, centroid_orig)}
            centroides.append(centroid_dict)
            desc = ClusteringService._describir_cluster(centroid_dict, int(mask.sum()), k)
            descripcion_clusters.append(desc)

        # Si había estudiantes excluidos por ruido plano, les asignamos el cluster más cercano
        indices_excluidos = np.where(~mascara_ruido)[0]
        centroides_np = np.array([[c[a] for a in AREAS_HOLLAND] for c in centroides])
        for idx in indices_excluidos:
            x_excl = X[idx]
            distancias = np.linalg.norm(centroides_np - x_excl, axis=1)
            labels_final[idx] = int(np.argmin(distancias))

        # --- 8. PERSISTENCIA EN BD ---
        resultado = ClusteringResultado(
            configuracion_id=configuracion_id,
            n_clusters=n_clusters,
            silhouette_score=round(sil_score, 4),
            inertia=round(inertia, 4),
            centroides=centroides,
            descripcion_clusters=descripcion_clusters,
            n_aplicaciones=len(X),
        )
        db.session.add(resultado)
        db.session.flush()

        for app_id, label, x_row in zip(app_ids, labels_final, X):
            centroid_np = centroides_np[label]
            dist = float(np.linalg.norm(x_row - centroid_np))
            asig = ClusteringAsignacion(
                clustering_resultado_id=resultado.id,
                aplicacion_id=app_id,
                cluster_id=int(label),
                distancia_centroide=round(dist, 4),
            )
            db.session.add(asig)

        db.session.commit()
        return resultado.to_dict()

    @staticmethod
    def historial(limit=10):
        """Retorna los últimos `limit` resultados de clustering."""
        resultados = (
            ClusteringResultado.query
            .order_by(ClusteringResultado.created_at.desc())
            .limit(limit)
            .all()
        )
        return [r.to_dict() for r in resultados]

    @staticmethod
    def detalle(resultado_id):
        """Retorna un resultado de clustering con todas sus asignaciones."""
        resultado = ClusteringResultado.query.get_or_404(resultado_id)
        data = resultado.to_dict()
        asignaciones = resultado.asignaciones.all()
        # Agrupar por cluster
        grupos = {}
        for asig in asignaciones:
            cid = asig.cluster_id
            grupos.setdefault(cid, []).append({
                'aplicacion_id': asig.aplicacion_id,
                'distancia': float(asig.distancia_centroide) if asig.distancia_centroide else None,
            })
        data['grupos'] = grupos
        return data

    @staticmethod
    def cluster_del_estudiante(aplicacion_id, resultado_id=None):
        """Retorna el cluster asignado a una aplicación dada."""
        query = ClusteringAsignacion.query.filter_by(aplicacion_id=aplicacion_id)
        if resultado_id:
            query = query.filter_by(clustering_resultado_id=resultado_id)
        else:
            # Usar el resultado más reciente
            query = query.join(ClusteringResultado).order_by(ClusteringResultado.created_at.desc())
        asig = query.first()
        if not asig:
            return None
        return {
            'cluster_id': asig.cluster_id,
            'distancia_centroide': float(asig.distancia_centroide) if asig.distancia_centroide else None,
            'resultado_id': asig.clustering_resultado_id,
        }
