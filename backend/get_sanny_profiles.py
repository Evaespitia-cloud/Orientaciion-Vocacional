from app import create_app
from app.models.resultado import PerfilVocacional
from app.models.usuario import Usuario

app = create_app()

with app.app_context():
    print("=== PERFILES DE SANNY AGUALIMPIA ===")
    sanny = Usuario.query.filter(Usuario.email.like('%sanny%')).first()
    if sanny:
        print(f"Estudiante: {sanny.nombre_completo} (ID: {sanny.id})")
        perfiles = PerfilVocacional.query.filter(PerfilVocacional.aplicacion_id.in_([a.id for a in sanny.aplicaciones])).all()
        for p in perfiles:
            print(f"App ID: {p.aplicacion_id} | Perfil Principal: {p.perfil_principal} | Secundario: {p.perfil_secundario} | Código RIASEC: {p.datos_json.get('codigo_riasec') if p.datos_json else 'Ninguno'}")
            if p.datos_json and 'puntajes_por_area' in p.datos_json:
                print("  Puntajes:", p.datos_json['puntajes_por_area'])
    else:
        print("Sanny no encontrada.")
