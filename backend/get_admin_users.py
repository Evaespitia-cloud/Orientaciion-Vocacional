from app import create_app
from app.models.usuario import Usuario, Rol

app = create_app()

with app.app_context():
    print("=== USUARIOS ADMINISTRATIVOS ===")
    usuarios = Usuario.query.all()
    for u in usuarios:
        if u.rol.nombre != 'estudiante':
            print(f"Usuario: {u.nombre_completo} | Email: {u.email} | Rol: {u.rol.nombre} | Activo: {u.activo}")
