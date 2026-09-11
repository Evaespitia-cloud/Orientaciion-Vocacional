import sys
sys.path.insert(0, 'c:/Users/ASUS/Desktop/ORIENTACION V/backend')
from app import create_app
from app.models.aplicacion import ConfiguracionAplicacion, Aplicacion
from app.models.instrumento import Instrumento, Dimension, Escala, Item

app = create_app()

with app.app_context():
    print("=== INSTRUMENTOS ===")
    insts = Instrumento.query.all()
    for i in insts:
        print(f"ID: {i.id} | Nombre: {i.nombre} | Activo: {i.activo}")
        dims = Dimension.query.filter_by(instrumento_id=i.id).all()
        for d in dims:
            print(f"  Dimension ID: {d.id} | Nombre: {d.nombre}")
            escalas = Escala.query.filter_by(dimension_id=d.id).all()
            for e in escalas:
                items_cnt = Item.query.filter_by(escala_id=e.id).count()
                print(f"    Escala ID: {e.id} | Nombre: {e.nombre} | Items: {items_cnt}")
                
    print("\n=== CONFIGURACIONES DE APLICACION ===")
    configs = ConfiguracionAplicacion.query.all()
    for c in configs:
        print(f"ID: {c.id} | Nombre: {c.nombre} | Instrumento ID: {c.instrumento_id} | Obligatoria: {c.obligatoria} | Activa: {c.activa}")
