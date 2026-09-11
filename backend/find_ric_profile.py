from app import create_app
from app.models.resultado import PerfilVocacional
from app.models.usuario import Usuario

app = create_app()

with app.app_context():
    print("=== BUSCANDO PERFILES CON CODIGO RIASEC 'RIC' ===")
    perfiles = PerfilVocacional.query.all()
    found = False
    for p in perfiles:
        code = p.datos_json.get('codigo_riasec') if p.datos_json else None
        if code == 'RIC' or p.perfil_principal == 'Realista' and p.perfil_secundario == 'Investigador':
            estudiante = p.aplicacion.usuario if p.aplicacion else None
            est_name = estudiante.nombre_completo if estudiante else 'Desconocido'
            print(f"Estudiante: {est_name} (Usuario ID: {p.aplicacion.usuario_id if p.aplicacion else 'N/A'})")
            print(f"App ID: {p.aplicacion_id}")
            print(f"Perfil Principal: {p.perfil_principal}")
            print(f"Perfil Secundario: {p.perfil_secundario}")
            print(f"Código RIASEC: {code}")
            if p.datos_json:
                print("Puntajes:", p.datos_json.get('puntajes_por_area'))
            found = True
            print("-" * 50)
            
    if not found:
        print("No se encontraron perfiles con 'RIC' o 'Realista-Investigador'.")
