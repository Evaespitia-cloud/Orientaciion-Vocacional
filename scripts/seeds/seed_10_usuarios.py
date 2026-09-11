import os
import secrets
DEMO_STUDENT_PASSWORD = os.getenv('DEMO_STUDENT_PASSWORD') or secrets.token_urlsafe(14) + 'Aa1!'
"""
Seed de 10 estudiantes adicionales con datos demográficos y simulación de pruebas.
Estados variados: algunos completan ambas, otros solo una, otros abandonan.
"""
import sys
import random
from datetime import datetime, timedelta

sys.path.insert(0, '.')

from backend.app import create_app
from backend.app.extensions import db
from backend.app.models.usuario import Usuario, Rol
from backend.app.models.aplicacion import Aplicacion, Respuesta, ConfiguracionAplicacion
from backend.app.models.instrumento import Escala
from backend.app.models.demografico import CampoDemografico, DatoDemografico
from backend.app.services.psicometrico_service import PsicometricoService
from backend.app.utils.audit import registrar_auditoria

random.seed(2026)

RIASEC = ['Realista', 'Investigador', 'Artístico', 'Social', 'Emprendedor', 'Convencional']

# 10 perfiles con dominancias distintas
USUARIOS_NUEVOS = [
    {
        'email': 'laura.torres@orientacion.edu.co',
        'nombres': 'Laura', 'apellidos': 'Torres Ruiz',
        'documento': '1020001001',
        'perfil': {'Realista':0.3,'Investigador':0.5,'Artístico':0.95,'Social':0.8,'Emprendedor':0.4,'Convencional':0.2},
        'demo': {'genero':'Femenino','edad':'17','grado_escolar':'11 grado','ciudad_region':'Bogotá','tipo_colegio':'Público','estrato':'Estrato 2','nombre_colegio':'Colegio Distrital Manuela Beltrán'},
        'estado': 'ambas_completas',
    },
    {
        'email': 'carlos.mendez@orientacion.edu.co',
        'nombres': 'Carlos', 'apellidos': 'Méndez Vargas',
        'documento': '1020001002',
        'perfil': {'Realista':1.0,'Investigador':0.8,'Artístico':0.1,'Social':0.2,'Emprendedor':0.5,'Convencional':0.6},
        'demo': {'genero':'Masculino','edad':'18','grado_escolar':'11 grado','ciudad_region':'Medellín','tipo_colegio':'Privado','estrato':'Estrato 4','nombre_colegio':'Colegio Colombo Británico'},
        'estado': 'ambas_completas',
    },
    {
        'email': 'sofia.guerrero@orientacion.edu.co',
        'nombres': 'Sofía', 'apellidos': 'Guerrero Pinto',
        'documento': '1020001003',
        'perfil': {'Realista':0.2,'Investigador':0.3,'Artístico':0.4,'Social':1.0,'Emprendedor':0.9,'Convencional':0.3},
        'demo': {'genero':'Femenino','edad':'16','grado_escolar':'10 grado','ciudad_region':'Cali','tipo_colegio':'Semi-privado','estrato':'Estrato 3','nombre_colegio':'IE Santa Librada'},
        'estado': 'ambas_completas',
    },
    {
        'email': 'andres.castillo@orientacion.edu.co',
        'nombres': 'Andrés', 'apellidos': 'Castillo Mora',
        'documento': '1020001004',
        'perfil': {'Realista':0.6,'Investigador':1.0,'Artístico':0.7,'Social':0.3,'Emprendedor':0.2,'Convencional':0.4},
        'demo': {'genero':'Masculino','edad':'17','grado_escolar':'11 grado','ciudad_region':'Barranquilla','tipo_colegio':'Público','estrato':'Estrato 3','nombre_colegio':'IED Simón Bolívar'},
        'estado': 'ambas_completas',
    },
    {
        'email': 'valentina.rios@orientacion.edu.co',
        'nombres': 'Valentina', 'apellidos': 'Ríos Acevedo',
        'documento': '1020001005',
        'perfil': {'Realista':0.4,'Investigador':0.3,'Artístico':0.6,'Social':0.5,'Emprendedor':1.0,'Convencional':0.8},
        'demo': {'genero':'Femenino','edad':'18','grado_escolar':'11 grado','ciudad_region':'Cartagena','tipo_colegio':'Privado','estrato':'Estrato 5','nombre_colegio':'Colegio Jorge Washington'},
        'estado': 'una_completa',   # Solo completa la primera prueba
    },
    {
        'email': 'miguel.herrera@orientacion.edu.co',
        'nombres': 'Miguel', 'apellidos': 'Herrera Salcedo',
        'documento': '1020001006',
        'perfil': {'Realista':0.9,'Investigador':0.2,'Artístico':0.3,'Social':0.4,'Emprendedor':0.6,'Convencional':1.0},
        'demo': {'genero':'Masculino','edad':'17','grado_escolar':'10 grado','ciudad_region':'Bucaramanga','tipo_colegio':'Público','estrato':'Estrato 2','nombre_colegio':'IED Ciudadela Real de Minas'},
        'estado': 'una_completa',
    },
    {
        'email': 'isabella.rojas@orientacion.edu.co',
        'nombres': 'Isabella', 'apellidos': 'Rojas Pedraza',
        'documento': '1020001007',
        'perfil': {'Realista':0.1,'Investigador':0.9,'Artístico':0.8,'Social':0.6,'Emprendedor':0.3,'Convencional':0.2},
        'demo': {'genero':'Femenino','edad':'16','grado_escolar':'10 grado','ciudad_region':'Manizales','tipo_colegio':'Privado','estrato':'Estrato 4','nombre_colegio':'Colegio Salesiano San Juan Bosco'},
        'estado': 'ambas_completas',
    },
    {
        'email': 'daniel.florez@orientacion.edu.co',
        'nombres': 'Daniel', 'apellidos': 'Flórez Ospina',
        'documento': '1020001008',
        'perfil': {'Realista':0.5,'Investigador':0.5,'Artístico':0.5,'Social':0.5,'Emprendedor':0.5,'Convencional':0.5},
        'demo': {'genero':'Masculino','edad':'18','grado_escolar':'11 grado','ciudad_region':'Pereira','tipo_colegio':'Semi-privado','estrato':'Estrato 3','nombre_colegio':'IE Boyacá'},
        'estado': 'abandonada',     # Abandona ambas pruebas
    },
    {
        'email': 'camila.jimenez@orientacion.edu.co',
        'nombres': 'Camila', 'apellidos': 'Jiménez Arango',
        'documento': '1020001009',
        'perfil': {'Realista':0.7,'Investigador':0.4,'Artístico':0.2,'Social':0.9,'Emprendedor':0.5,'Convencional':0.3},
        'demo': {'genero':'Femenino','edad':'17','grado_escolar':'11 grado','ciudad_region':'Ibagué','tipo_colegio':'Público','estrato':'Estrato 2','nombre_colegio':'IED Colegio San Simón'},
        'estado': 'ambas_completas',
    },
    {
        'email': 'juan.morales@orientacion.edu.co',
        'nombres': 'Juan', 'apellidos': 'Morales Sepúlveda',
        'documento': '1020001010',
        'perfil': {'Realista':0.3,'Investigador':0.8,'Artístico':0.9,'Social':0.4,'Emprendedor':0.7,'Convencional':0.2},
        'demo': {'genero':'Masculino','edad':'16','grado_escolar':'10 grado','ciudad_region':'Santa Marta','tipo_colegio':'Privado','estrato':'Estrato 4','nombre_colegio':'Colegio Externado Nacional'},
        'estado': 'en_progreso',    # Deja en progreso (no completada)
    },
]


def crear_usuario(datos: dict, rol_estudiante, app) -> Usuario:
    """Crea el usuario en la BD."""
    with app.app_context():
        existente = Usuario.query.filter_by(email=datos['email']).first()
        if existente:
            print(f"  [!]  Ya existe: {datos['email']}")
            return existente

        from werkzeug.security import generate_password_hash
        u = Usuario(
            email=datos['email'],
            password_hash=generate_password_hash(DEMO_STUDENT_PASSWORD),
            nombres=datos['nombres'],
            apellidos=datos['apellidos'],
            documento=datos['documento'],
            tipo_documento='TI',
            rol_id=rol_estudiante.id,
            activo=True,
        )
        db.session.add(u)
        db.session.commit()
        print(f"  [OK] Creado: {u.email}")
        return u


def seed_demograficos(usuario, demo: dict, campos_map: dict, app):
    """Inserta datos demográficos para el usuario."""
    with app.app_context():
        for campo_nombre, valor in demo.items():
            campo = campos_map.get(campo_nombre)
            if not campo:
                continue
            existente = DatoDemografico.query.filter_by(
                usuario_id=usuario.id, campo_id=campo.id
            ).first()
            if not existente:
                db.session.add(DatoDemografico(
                    usuario_id=usuario.id,
                    campo_id=campo.id,
                    valor=valor,
                ))
        db.session.commit()


def simular_aplicacion_completa(usuario, config, perfil_pesos, offset_dias, app):
    """Crea una aplicación completada con perfil calculado."""
    with app.app_context():
        fecha = datetime.utcnow() - timedelta(days=offset_dias)
        ap = Aplicacion(
            usuario_id=usuario.id,
            configuracion_id=config.id,
            estado='completada',
            ip_address='127.0.0.1',
            user_agent='Seed10Script/1.0',
            fecha_inicio=fecha,
            fecha_fin=fecha + timedelta(minutes=random.randint(12, 28)),
        )
        db.session.add(ap)
        db.session.flush()

        instrumento = config.instrumento
        es_intereses = 'Intereses' in instrumento.nombre

        for dimension in instrumento.dimensiones:
            for escala in dimension.escalas:
                area = escala.nombre
                peso = perfil_pesos.get(area, 0.5)
                for item in escala.items:
                    if es_intereses:
                        val = 1 if random.random() < peso else 0
                        texto = 'Sí' if val == 1 else 'No'
                    else:
                        import json
                        opciones = item.opciones if isinstance(item.opciones, dict) else json.loads(item.opciones or '{}')
                        lista = opciones.get('opciones', [])
                        correcta = next((i for i, o in enumerate(lista) if o.get('valor') == 1), 0)
                        incorrectas = [i for i, o in enumerate(lista) if o.get('valor') != 1]
                        val = correcta if random.random() < peso else (random.choice(incorrectas) if incorrectas else correcta)
                        texto = str(val)

                    db.session.add(Respuesta(
                        aplicacion_id=ap.id,
                        item_id=item.id,
                        valor=val,
                        valor_texto=texto,
                        tiempo_respuesta_seg=random.randint(3, 15),
                    ))

        db.session.commit()
        try:
            PsicometricoService.calcular_puntajes_dimension(ap.id)
            perfil = PsicometricoService.generar_perfil(ap.id)
            print(f"      [OK] {instrumento.nombre[:35]:<35} -> {perfil.perfil_principal}/{perfil.perfil_secundario}")
        except Exception as e:
            print(f"      [ERROR] Error al calcular perfil: {e}")
            db.session.rollback()


def simular_en_progreso(usuario, config, offset_dias, app):
    """Crea una aplicación que quedó en progreso (sin terminar)."""
    with app.app_context():
        fecha = datetime.utcnow() - timedelta(days=offset_dias)
        ap = Aplicacion(
            usuario_id=usuario.id,
            configuracion_id=config.id,
            estado='en_progreso',
            progreso=random.randint(30, 70),
            ip_address='127.0.0.1',
            user_agent='Seed10Script/1.0',
            fecha_inicio=fecha,
        )
        db.session.add(ap)
        db.session.commit()
        print(f"      [~] {config.instrumento.nombre[:35]:<35} -> EN PROGRESO")


def simular_abandonada(usuario, config, offset_dias, app):
    """Crea una aplicación abandonada."""
    with app.app_context():
        fecha = datetime.utcnow() - timedelta(days=offset_dias)
        ap = Aplicacion(
            usuario_id=usuario.id,
            configuracion_id=config.id,
            estado='abandonada',
            progreso=random.randint(5, 30),
            ip_address='127.0.0.1',
            user_agent='Seed10Script/1.0',
            fecha_inicio=fecha,
        )
        db.session.add(ap)
        db.session.commit()
        print(f"      [X] {config.instrumento.nombre[:35]:<35} -> ABANDONADA")


def main():
    app = create_app()

    with app.app_context():
        # Rol estudiante
        rol_estudiante = Rol.query.filter_by(nombre='estudiante').first()
        if not rol_estudiante:
            print("ERROR: Rol 'estudiante' no encontrado.")
            return

        # Configuraciones activas
        configs = ConfiguracionAplicacion.query.filter_by(activa=True).all()
        if not configs:
            print("ERROR: No hay configuraciones activas.")
            return
        print(f"Configuraciones: {[c.nombre[:40] for c in configs]}\n")

        # Campos demográficos
        campos_demo = CampoDemografico.query.filter_by(activo=True).all()
        campos_map = {c.nombre: c for c in campos_demo}
        print(f"Campos demográficos: {list(campos_map.keys())}\n")

        # — PARTE 1: Extender fecha_fin de todas las configs a año 2099 —
        print("=== Extendiendo fecha_fin de configuraciones a año 2099 ===")
        fecha_infinita = datetime(2099, 12, 31, 23, 59, 59)
        for c in configs:
            c.fecha_fin = fecha_infinita
            print(f"  [OK] '{c.nombre[:50]}' -> sin vencimiento")
        db.session.commit()
        print()

        # — PARTE 2: Crear usuarios y simular pruebas —
        print("=== Creando 10 estudiantes y simulando pruebas ===")
        for datos in USUARIOS_NUEVOS:
            print(f"\n> {datos['nombres']} {datos['apellidos']} ({datos['email']})")

            # Crear usuario
            existente = Usuario.query.filter_by(email=datos['email']).first()
            if existente:
                usuario = existente
                print(f"  (ya existe, reutilizando)")
            else:
                from werkzeug.security import generate_password_hash
                usuario = Usuario(
                    email=datos['email'],
                    password_hash=generate_password_hash(DEMO_STUDENT_PASSWORD),
                    nombres=datos['nombres'],
                    apellidos=datos['apellidos'],
                    documento=datos['documento'],
                    tipo_documento='TI',
                    rol_id=rol_estudiante.id,
                    activo=True,
                )
                db.session.add(usuario)
                db.session.commit()
                print(f"  [OK] Usuario creado")

            # Datos demográficos
            for campo_nombre, valor in datos['demo'].items():
                campo = campos_map.get(campo_nombre)
                if not campo:
                    continue
                existe_dato = DatoDemografico.query.filter_by(
                    usuario_id=usuario.id, campo_id=campo.id
                ).first()
                if not existe_dato:
                    db.session.add(DatoDemografico(
                        usuario_id=usuario.id,
                        campo_id=campo.id,
                        valor=valor,
                    ))
            db.session.commit()
            print(f"  [OK] Datos demograficos insertados")

            # Simular pruebas según el estado del usuario
            estado = datos['estado']
            pesos = datos['perfil']
            offset = random.randint(1, 30)

            for idx, config in enumerate(configs):
                ya_completo = Aplicacion.query.filter_by(
                    usuario_id=usuario.id,
                    configuracion_id=config.id,
                    estado='completada'
                ).first()
                if ya_completo:
                    print(f"    [!]  Ya completo: {config.nombre[:40]}")
                    continue

                if estado == 'ambas_completas':
                    simular_aplicacion_completa(usuario, config, pesos, offset + idx * 3, app)

                elif estado == 'una_completa':
                    if idx == 0:
                        simular_aplicacion_completa(usuario, config, pesos, offset, app)
                    else:
                        simular_en_progreso(usuario, config, offset + 5, app)

                elif estado == 'en_progreso':
                    simular_en_progreso(usuario, config, offset + idx * 2, app)

                elif estado == 'abandonada':
                    simular_abandonada(usuario, config, offset + idx * 2, app)

    print("\n[OK] Seed completado: 10 estudiantes creados con datos demograficos y pruebas simuladas.")
    print(f"  Contraseña demo generada/definida por entorno: {DEMO_STUDENT_PASSWORD}")


if __name__ == '__main__':
    main()
