import sys
sys.path.insert(0, 'c:/Users/ASUS/Desktop/ORIENTACION V/backend')
from app import create_app
from app.models.usuario import Usuario
from app.models.aplicacion import Aplicacion
from app.models.resultado import PerfilVocacional

app = create_app()

with app.app_context():
    print("=== ESTUDIANTES CON AMBAS PRUEBAS COMPLETADAS ===")
    
    # Query all students
    estudiantes = Usuario.query.filter(Usuario.activo == True).all()
    
    count = 0
    for est in estudiantes:
        apps = Aplicacion.query.filter_by(usuario_id=est.id, estado='completada').all()
        if len(apps) >= 2:
            instrumentos = [a.configuracion.instrumento_id for a in apps if a.configuracion]
            if 5 in instrumentos and 6 in instrumentos:
                count += 1
                print(f"Estudiante: {est.nombres} {est.apellidos} (ID: {est.id}) - Email: {est.email}")
                for a in apps:
                    print(f"  App ID: {a.id} | Config ID: {a.configuracion_id} | Inst ID: {a.configuracion.instrumento_id} | Nombre: {a.configuracion.instrumento.nombre}")
                    p = PerfilVocacional.query.filter_by(aplicacion_id=a.id).first()
                    if p:
                        print(f"    Perfil: {p.perfil_principal} | Codigo: {p.datos_json.get('codigo_riasec') if p.datos_json else 'N/A'}")
                        if p.datos_json and 'puntajes_por_area' in p.datos_json:
                            print(f"    Puntajes: {list(p.datos_json['puntajes_por_area'].items())[:3]}")
                if count >= 5:
                    print("... mostrando los primeros 5 estudiantes ...")
                    break
    print(f"\nTotal estudiantes con ambas completadas: {count}")
