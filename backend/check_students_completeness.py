from app import create_app
from app.models.usuario import Usuario, Rol
from app.models.aplicacion import Aplicacion
from app.models.resultado import PerfilVocacional

app = create_app()

with app.app_context():
    print("=== ESTADO DE COMPLETITUD DE LOS ESTUDIANTES ===")
    
    # Obtener el rol de estudiante
    rol_estudiante = Rol.query.filter_by(nombre='estudiante').first()
    if not rol_estudiante:
        print("Error: No se encontró el rol 'estudiante'")
        exit()
        
    estudiantes = Usuario.query.filter_by(rol_id=rol_estudiante.id, activo=True).order_by(Usuario.apellidos, Usuario.nombres).all()
    
    total_estudiantes = len(estudiantes)
    completados = 0
    incompletos = 0
    sin_pruebas = 0
    
    for i, est in enumerate(estudiantes, 1):
        apps = Aplicacion.query.filter_by(usuario_id=est.id).all()
        print(f"\n{i}. Estudiante: {est.nombre_completo} ({est.email}) | Grado: {est.grado.nombre if est.grado else 'N/A'}")
        
        if not apps:
            print("  -> ESTADO: Sin pruebas registradas.")
            sin_pruebas += 1
            continue
            
        print(f"  -> Pruebas registradas ({len(apps)}):")
        has_completed = False
        has_profile = False
        
        for app in apps:
            inst_nombre = app.configuracion.instrumento.nombre if app.configuracion and app.configuracion.instrumento else "Desconocido"
            perfil = PerfilVocacional.query.filter_by(aplicacion_id=app.id).first()
            perfil_str = f"| Perfil: {perfil.perfil_principal} (Código RIASEC: {perfil.datos_json.get('codigo_riasec', 'N/A') if perfil.datos_json else 'N/A'})" if perfil else "| Sin Perfil Vocacional"
            
            print(f"     - App ID: {app.id} | Instrumento: {inst_nombre} | Estado: {app.estado} {perfil_str}")
            
            if app.estado == 'completada':
                has_completed = True
                if perfil:
                    has_profile = True
                    
        if has_completed and has_profile:
            completados += 1
            print("  -> ESTADO FINAL: COMPLETO (Tiene perfil vocacional y resultados).")
        else:
            incompletos += 1
            print("  -> ESTADO FINAL: INCOMPLETO (Pruebas en curso o sin perfil vocacional generado).")
            
    print("\n" + "="*50)
    print("=== RESUMEN GENERAL ===")
    print(f"Total Estudiantes Activos: {total_estudiantes}")
    print(f"Con perfil y resultados completos: {completados}")
    print(f"Con pruebas incompletas/en curso: {incompletos}")
    print(f"Sin ninguna prueba registrada: {sin_pruebas}")
    print("="*50)
