import sys
sys.path.insert(0, 'c:/Users/ASUS/Desktop/ORIENTACION V/backend')
from app import create_app
from app.models.resultado import ResultadoDimension

app = create_app()

with app.app_context():
    res = ResultadoDimension.query.all()
    print(f"Total registros en resultados_dimension: {len(res)}")
    for r in res[:10]:
        print(f"ID: {r.id} | Aplicacion ID: {r.aplicacion_id} | Dimension ID: {r.dimension_id} | Bruto: {r.puntaje_bruto} | Normalizado: {r.puntaje_normalizado}")
