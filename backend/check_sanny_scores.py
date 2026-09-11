from app import create_app
from app.models.resultado import PerfilVocacional, ResultadoDimension
from app.models.aplicacion import Aplicacion

app = create_app()

with app.app_context():
    print("=== PERFIL VOCACIONAL (Sanny - App 1762) ===")
    p = PerfilVocacional.query.filter_by(aplicacion_id=1762).first()
    if p:
        print(f"ID: {p.id}")
        print(f"Perfil Principal: {p.perfil_principal}")
        print(f"Perfil Secundario: {p.perfil_secundario}")
        print("Datos JSON:", p.datos_json)
        
    print("\n=== RESULTADOS DIMENSION (Sanny - App 1762) ===")
    dims = ResultadoDimension.query.filter_by(aplicacion_id=1762).all()
    for d in dims:
        print(f"Dimensión: {d.dimension_nombre} | Bruto: {d.puntaje_bruto} | Normalizado: {d.puntaje_normalizado}")
