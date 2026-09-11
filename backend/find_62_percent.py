from app import create_app
from app.models.resultado import PerfilVocacional
from app.models.usuario import Usuario

app = create_app()

with app.app_context():
    print("=== BUSCANDO COINCIDENCIA DE 62% EN LA BD ===")
    perfiles = PerfilVocacional.query.all()
    for p in perfiles:
        if not p.datos_json or 'puntajes_por_area' not in p.datos_json:
            continue
        scores = p.datos_json['puntajes_por_area']
        for area, d in scores.items():
            norm = d.get('normalizado', 0)
            if abs(norm - 62.5) < 1.0 or abs(norm - 62.0) < 1.0:
                estudiante = p.aplicacion.usuario if p.aplicacion else None
                est_name = estudiante.nombre_completo if estudiante else 'Desconocido'
                print(f"Estudiante: {est_name} | App ID: {p.aplicacion_id}")
                print(f"  Area '{area}' has normalizado: {norm}")
                print("  Todos los puntajes de esta app:", scores)
                print("-" * 50)
