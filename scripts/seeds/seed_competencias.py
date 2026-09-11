"""
Siembra aplicaciones de Prueba de Competencias Vocacionales Holland
para los 22 estudiantes que ya completaron la prueba de Intereses.
Usa los mismos perfiles RIASEC con pequeñas variaciones realistas.
"""
import sys, random
from datetime import datetime, timedelta

sys.path.insert(0, 'backend')
from backend.app import create_app
from backend.app.extensions import db
from backend.app.models.aplicacion import Aplicacion, ConfiguracionAplicacion
from backend.app.models.resultado import ResultadoDimension, PerfilVocacional
from backend.app.models.instrumento import Dimension, Escala
from backend.app.models.usuario import Usuario

random.seed(42)

RIASEC_INFO = {
    'Realista':     {'codigo': 'R', 'carreras': ['Ingeniería Civil', 'Agronomía', 'Arquitectura', 'Mecánica', 'Electricidad'], 'ambiente': 'Talleres, laboratorios, campos, plantas industriales'},
    'Investigador': {'codigo': 'I', 'carreras': ['Biología', 'Química', 'Medicina', 'Psicología', 'Matemáticas', 'Física'], 'ambiente': 'Laboratorios, universidades, centros de investigación'},
    'Artístico':    {'codigo': 'A', 'carreras': ['Bellas Artes', 'Diseño Gráfico', 'Música', 'Comunicación', 'Publicidad'], 'ambiente': 'Estudios, galerías, teatros, medios de comunicación'},
    'Social':       {'codigo': 'S', 'carreras': ['Psicología', 'Trabajo Social', 'Educación', 'Enfermería', 'Medicina'], 'ambiente': 'Hospitales, escuelas, centros comunitarios, ONGs'},
    'Emprendedor':  {'codigo': 'E', 'carreras': ['Administración', 'Derecho', 'Marketing', 'Economía', 'Negocios'], 'ambiente': 'Empresas, despachos jurídicos, agencias'},
    'Convencional': {'codigo': 'C', 'carreras': ['Contaduría', 'Administración', 'Sistemas', 'Estadística', 'Finanzas'], 'ambiente': 'Oficinas, bancos, archivos, entidades gubernamentales'},
}

DESCRIPCIONES = {
    'Realista':     'Presenta competencias destacadas en actividades prácticas y técnicas. Tiene habilidad manual y prefiere trabajar con objetos, máquinas y herramientas.',
    'Investigador': 'Demuestra competencias analíticas y científicas sobresalientes. Disfruta investigar, resolver problemas complejos y adquirir conocimientos.',
    'Artístico':    'Muestra competencias creativas y expresivas. Tiene capacidad para la innovación estética y la comunicación no convencional.',
    'Social':       'Sus competencias interpersonales son su fortaleza. Tiene habilidad para comunicarse, ayudar y trabajar colaborativamente con otras personas.',
    'Emprendedor':  'Posee competencias de liderazgo y persuasión. Tiene capacidad para dirigir proyectos, motivar personas y tomar decisiones estratégicas.',
    'Convencional': 'Evidencia competencias organizativas y de gestión de la información. Es preciso, ordenado y efectivo en ambientes estructurados.',
}

app = create_app()

with app.app_context():
    # Dynamic Instrument and Configuration lookup
    from backend.app.models.instrumento import Instrumento
    inst_comp = Instrumento.query.filter(Instrumento.nombre.like('%Competencias%')).first()
    if not inst_comp:
        print("ERROR: No se encontró el instrumento de Competencias Vocacionales")
        sys.exit(1)
        
    cfg = ConfiguracionAplicacion.query.filter_by(instrumento_id=inst_comp.id, activa=True).first()
    if not cfg:
        cfg = ConfiguracionAplicacion.query.filter_by(instrumento_id=inst_comp.id).first()
    if not cfg:
        print(f"ERROR: No existe configuración para el instrumento {inst_comp.id}")
        sys.exit(1)
    print(f"Config: [{cfg.id}] {cfg.nombre}")

    # Dimensión de Competencias
    dim = Dimension.query.filter_by(instrumento_id=inst_comp.id).first()
    if not dim:
        print(f"ERROR: No se encontró dimensión para el instrumento {inst_comp.id}")
        sys.exit(1)
    print(f"Dimensión: [{dim.id}] {dim.nombre}")

    # Escalas de Competencias
    escalas = Escala.query.filter_by(dimension_id=dim.id).all()
    escala_map = {e.nombre: e for e in escalas}
    print(f"Escalas: {[e.nombre for e in escalas]}")

    # Obtener todos los estudiantes que ya tienen perfiles de Intereses
    # Tomamos su perfil principal para usarlo como base en Competencias
    perfiles_existentes = db.session.query(
        PerfilVocacional.aplicacion_id,
        PerfilVocacional.perfil_principal,
        PerfilVocacional.perfil_secundario,
        Aplicacion.usuario_id,
        Aplicacion.configuracion_id,
    ).join(Aplicacion, Aplicacion.id == PerfilVocacional.aplicacion_id).all()

    # Un perfil por estudiante (el más reciente / config más alta)
    perfil_por_usuario = {}
    for p in perfiles_existentes:
        uid = p.usuario_id
        if uid not in perfil_por_usuario or p.configuracion_id > perfil_por_usuario[uid][2]:
            perfil_por_usuario[uid] = (p.perfil_principal, p.perfil_secundario, p.configuracion_id)

    print(f"\nEstudiantes a procesar: {len(perfil_por_usuario)}")

    # Verificar que no existan ya apps de Competencias
    existing = Aplicacion.query.filter_by(configuracion_id=cfg.id).count()
    if existing > 0:
        print(f"Ya existen {existing} aplicaciones para esta config. Abortando.")
        sys.exit(0)

    created = 0
    base_date = datetime(2025, 3, 1)

    for usuario_id, (perfil_principal, perfil_secundario, _) in sorted(perfil_por_usuario.items()):
        # Generar puntajes RIASEC con el perfil principal alto, secundario medio, resto bajos
        areas = list(RIASEC_INFO.keys())
        puntajes = {}
        for area in areas:
            if area == perfil_principal:
                puntajes[area] = random.randint(4, 5)     # 80–100%
            elif area == perfil_secundario:
                puntajes[area] = random.randint(2, 4)     # 40–80%
            else:
                puntajes[area] = random.randint(0, 2)     # 0–40%

        # Asegurar que el perfil principal sea el mayor
        puntajes[perfil_principal] = max(puntajes[perfil_principal], max(puntajes.values()))

        # Calcular puntaje normalizado global (promedio sobre 5 items × 6 áreas)
        total_items = 5
        suma_bruta = sum(puntajes.values())
        total_posible = total_items * len(areas)
        puntaje_norm = round(suma_bruta / total_posible * 100, 2)

        # Fecha aleatoria entre 2025-03-01 y 2025-06-30
        offset_dias = random.randint(0, 120)
        fecha_inicio = base_date + timedelta(days=offset_dias)
        fecha_fin = fecha_inicio + timedelta(minutes=random.randint(18, 45))

        # Crear Aplicacion
        nueva_app = Aplicacion(
            usuario_id=usuario_id,
            configuracion_id=cfg.id,
            estado='completada',
            fecha_inicio=fecha_inicio,
            fecha_fin=fecha_fin,
        )
        db.session.add(nueva_app)
        db.session.flush()

        # Crear ResultadoDimension (1 registro por app para la dimensión global)
        nivel = 'alto' if puntaje_norm >= 66 else ('medio' if puntaje_norm >= 33 else 'bajo')
        rd = ResultadoDimension(
            aplicacion_id=nueva_app.id,
            dimension_id=dim.id,
            puntaje_bruto=round(suma_bruta, 2),
            puntaje_normalizado=puntaje_norm,
            nivel=nivel,
        )
        db.session.add(rd)

        # Construir datos_json con puntajes por escala (igual que Intereses)
        puntajes_escala_json = {}
        puntajes_por_area_json = {}
        for area in areas:
            esc = escala_map.get(area)
            if not esc:
                continue
            pn = round(puntajes[area] / total_items * 100, 2)
            clave = f"{area} (Competencias Vocacionales)"
            puntajes_escala_json[clave] = {
                'dimension': dim.nombre,
                'escala_id': esc.id,
                'respondidos': total_items,
                'total_items': total_items,
                'escala_nombre': area,
                'puntaje_bruto': puntajes[area],
                'puntaje_normalizado': pn,
                'respuestas_positivas': puntajes[area],
            }
            puntajes_por_area_json[area] = {
                'total': total_items,
                'positivas': puntajes[area],
                'normalizado': pn,
                dim.nombre: puntajes[area],
            }

        # Ordenar areas por puntaje para obtener código RIASEC
        top3 = sorted(areas, key=lambda a: puntajes[a], reverse=True)[:3]
        codigo_riasec = ''.join(RIASEC_INFO[a]['codigo'] for a in top3)

        datos_json = {
            'advertencia': None,
            'codigo_riasec': codigo_riasec,
            'carreras_afines': RIASEC_INFO[perfil_principal]['carreras'],
            'puntajes_escala': puntajes_escala_json,
            'ambiente_trabajo': RIASEC_INFO[perfil_principal]['ambiente'],
            'formula_utilizada': {
                'areas': areas,
                'metodo': 'suma_binaria',
                'valor_negativo': 0,
                'valor_positivo': 1,
                'umbral_afinidad': 0.6,
                'criterio_dominante': 'puntaje_maximo',
            },
            'puntajes_por_area': puntajes_por_area_json,
            'resultados_dimension': [{
                'id': rd.id,
                'nivel': nivel,
                'dimension_id': dim.id,
                'aplicacion_id': nueva_app.id,
                'puntaje_bruto': float(suma_bruta),
                'dimension_nombre': dim.nombre,
                'puntaje_normalizado': float(puntaje_norm),
            }],
        }

        # Crear PerfilVocacional
        pv = PerfilVocacional(
            aplicacion_id=nueva_app.id,
            perfil_principal=perfil_principal,
            perfil_secundario=perfil_secundario,
            descripcion=DESCRIPCIONES[perfil_principal],
            fortalezas=f"Competencia destacada en área {perfil_principal}. Habilidades interpersonales y técnicas.",
            areas_desarrollo=f"Refuerzo en áreas {', '.join(a for a in areas if a not in (perfil_principal, perfil_secundario)[:2])}.",
            recomendaciones=f"Explorar programas en: {', '.join(RIASEC_INFO[perfil_principal]['carreras'][:3])}.",
            datos_json=datos_json,
        )
        db.session.add(pv)
        created += 1

    db.session.commit()
    print(f"\n✓ Creadas {created} aplicaciones de Competencias Vocacionales con perfiles RIASEC.")

    # Verificar resultado
    total_comp = Aplicacion.query.filter_by(configuracion_id=cfg.id, estado='completada').count()
    print(f"✓ Total completadas en config Competencias: {total_comp}")
