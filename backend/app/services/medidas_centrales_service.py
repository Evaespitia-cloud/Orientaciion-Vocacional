from ..extensions import db
from ..models.aplicacion import Aplicacion
from ..models.resultado import ResultadoDimension, PerfilVocacional


class MedidasCentralesService:
    @staticmethod
    def medidas_centrales_perfiles() -> dict:
        """Devuelve estadísticos globales de los puntajes por perfil vocacional."""
        import numpy as np

        query = (
            db.session.query(
                PerfilVocacional.perfil_principal.label('area'),
                ResultadoDimension.puntaje_normalizado.label('puntaje')
            )
            .join(Aplicacion, Aplicacion.id == PerfilVocacional.aplicacion_id)
            .join(ResultadoDimension, ResultadoDimension.aplicacion_id == Aplicacion.id)
            .filter(Aplicacion.estado == 'completada')
            .filter(ResultadoDimension.puntaje_normalizado.isnot(None))
        )
        datos = {}
        for resultado in query.all():
            datos.setdefault(resultado.area or 'Sin área', []).append(float(resultado.puntaje))

        estadisticas = []
        for area, puntajes in datos.items():
            arr = np.array(puntajes)
            estadisticas.append({
                'area': area,
                'promedio': round(float(np.mean(arr)), 2),
                'mediana': round(float(np.median(arr)), 2),
                'desviacion': round(float(np.std(arr, ddof=1)), 2) if len(arr) > 1 else 0.0,
                'n': len(arr),
            })
        return {'medidas_centrales': estadisticas}
