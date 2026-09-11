"""
Script que simula a los 3 estudiantes respondiendo las dos pruebas Holland RIASEC.
Perfiles simulados:
  - estudiante1: Social/Artístico
  - estudiante2: Investigador/Realista
  - estudiante3: Emprendedor/Convencional
"""
import sys
sys.path.insert(0, '.')

from backend.app import create_app
from backend.app.extensions import db
from backend.app.models.aplicacion import Aplicacion, Respuesta, ConfiguracionAplicacion
from backend.app.models.instrumento import Item, Escala, Dimension, Instrumento
from backend.app.models.usuario import Usuario
from backend.app.services.psicometrico_service import PsicometricoService
from datetime import datetime, timedelta
import random

# Pesos de respuesta por estudiante: 1.0 = siempre afirmativa, 0.0 = siempre negativa
PERFILES = {
    'estudiante1@orientacion.edu.co': {
        # Fuerte en Social y Artístico
        'Realista':     0.2,
        'Investigador': 0.4,
        'Artístico':    0.9,
        'Social':       1.0,
        'Emprendedor':  0.4,
        'Convencional': 0.3,
    },
    'estudiante2@orientacion.edu.co': {
        # Fuerte en Investigador y Realista
        'Realista':     0.9,
        'Investigador': 1.0,
        'Artístico':    0.2,
        'Social':       0.3,
        'Emprendedor':  0.4,
        'Convencional': 0.5,
    },
    'estudiante3@orientacion.edu.co': {
        # Fuerte en Emprendedor y Convencional
        'Realista':     0.2,
        'Investigador': 0.3,
        'Artístico':    0.4,
        'Social':       0.5,
        'Emprendedor':  1.0,
        'Convencional': 0.9,
    },
}

random.seed(42)

def respuesta_intereses(area_nombre, peso):
    """Genera respuesta Sí/No para ítems de intereses según el peso del área."""
    return 1 if random.random() < peso else 0

def respuesta_competencias(item, area_nombre, peso):
    """
    Para opción múltiple, el ítem tiene opciones con valor 1 (correcta) y 0.
    Si el peso es alto, elige la opción de valor 1; si es bajo, elige una de las otras.
    """
    import json
    opciones = item.opciones if isinstance(item.opciones, dict) else json.loads(item.opciones)
    lista = opciones.get('opciones', [])
    correcta = next((i for i, o in enumerate(lista) if o.get('valor') == 1), 0)
    incorrectas = [i for i, o in enumerate(lista) if o.get('valor') != 1]
    if random.random() < peso:
        return correcta
    else:
        return random.choice(incorrectas) if incorrectas else correcta

def simular_aplicacion(app_ctx, usuario, config, perfil_pesos, offset_dias=0):
    """Crea una aplicación completada con respuestas simuladas y calcula el perfil."""
    with app_ctx.app_context():
        # Crear aplicación
        fecha = datetime.utcnow() - timedelta(days=offset_dias)
        aplicacion = Aplicacion(
            usuario_id=usuario.id,
            configuracion_id=config.id,
            estado='completada',
            ip_address='127.0.0.1',
            user_agent='SimuladorScript/1.0',
            fecha_inicio=fecha,
            fecha_fin=fecha + timedelta(minutes=random.randint(12, 25)),
        )
        db.session.add(aplicacion)
        db.session.flush()  # para obtener el ID

        instrumento = config.instrumento
        es_intereses = 'Intereses' in instrumento.nombre

        # Obtener todos los ítems del instrumento
        for dimension in instrumento.dimensiones:
            for escala in dimension.escalas:
                area = escala.nombre  # nombre del área RIASEC
                peso = perfil_pesos.get(area, 0.5)
                for item in escala.items:
                    if es_intereses:
                        valor = respuesta_intereses(area, peso)
                        texto = 'Sí' if valor == 1 else 'No'
                    else:
                        valor = respuesta_competencias(item, area, peso)
                        texto = str(valor)

                    resp = Respuesta(
                        aplicacion_id=aplicacion.id,
                        item_id=item.id,
                        valor=valor,
                        valor_texto=texto,
                        tiempo_respuesta_seg=random.randint(3, 12),
                    )
                    db.session.add(resp)

        db.session.commit()

        # Calcular puntajes y perfil
        try:
            PsicometricoService.calcular_puntajes_dimension(aplicacion.id)
            perfil = PsicometricoService.generar_perfil(aplicacion.id)
            print(f"    ✓ {instrumento.nombre[:35]:<35} → {perfil.perfil_principal}/{perfil.perfil_secundario}")
        except Exception as e:
            print(f"    ✗ Error procesando: {e}")
            db.session.rollback()
            return

        return aplicacion

def main():
    app = create_app()

    with app.app_context():
        # Obtener configuraciones activas
        configs = ConfiguracionAplicacion.query.filter_by(activa=True).all()
        if not configs:
            print("ERROR: No hay configuraciones activas. Ejecuta seed_instruments.py primero.")
            return
        print(f"Configuraciones encontradas: {len(configs)}")
        for c in configs:
            print(f"  [{c.id}] {c.nombre[:50]}")

        # Obtener estudiantes
        estudiantes = (
            Usuario.query
            .join(Usuario.rol)
            .filter(db.text("roles.nombre = 'estudiante'"))
            .filter(Usuario.activo == True)
            .all()
        )
        print(f"\nEstudiantes encontrados: {len(estudiantes)}")

        for estudiante in estudiantes:
            email = estudiante.email
            pesos = PERFILES.get(email, {a: 0.5 for a in ['Realista','Investigador','Artístico','Social','Emprendedor','Convencional']})
            print(f"\n  {email}")

            for config in configs:
                # Verificar si ya completó esta prueba
                ya = Aplicacion.query.filter_by(
                    usuario_id=estudiante.id,
                    configuracion_id=config.id,
                    estado='completada'
                ).first()
                if ya:
                    print(f"    ⚠ Ya completó: {config.nombre[:40]}")
                    continue

                simular_aplicacion(app, estudiante, config, pesos, offset_dias=random.randint(0, 5))

        print("\n✓ Simulación completada. Los estudiantes tienen sus resultados listos.")

if __name__ == '__main__':
    main()
