from backend.app import create_app
from backend.app.models.instrumento import Instrumento, Dimension, Escala, Item

app = create_app()
app.app_context().push()

inst = Instrumento.query.get(5)
if not inst:
    print('instrument 5 not found')
    raise SystemExit

print('instrument', inst.id, inst.nombre)
for dim in inst.dimensiones.order_by(Dimension.orden).all():
    print('dimension', dim.id, dim.nombre)
    for esc in dim.escalas.order_by(Escala.orden).all():
        count = esc.items.filter_by(activo=True).count()
        print('  scale', esc.id, esc.nombre, 'count=', count)
        for item in esc.items.filter_by(activo=True).order_by(Item.orden).all()[:2]:
            print('    item', item.id, item.texto[:160])
