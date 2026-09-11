from app import create_app
from app.models.resultado import PerfilVocacional
from app.models.usuario import Usuario

app = create_app()

with app.app_context():
    print("=== PERFILES VOCACIONALES EN LA BD ===")
    perfiles = PerfilVocacional.query.all()
    for p in perfiles:
        estudiante = p.aplicacion.usuario if p.aplicacion else None
        est_name = estudiante.nombre_completo if estudiante else 'Desconocido'
        print(f"Estudiante: {est_name} | App ID: {p.aplicacion_id} | Perfil Principal: {p.perfil_principal} | Secundario: {p.perfil_secundario} | Código RIASEC: {p.datos_json.get('codigo_riasec') if p.datos_json else 'Ninguno'}")
        if p.datos_json and 'puntajes_por_area' in p.datos_json:
            print("  Puntajes:", p.datos_json['puntajes_por_area'])
