import sys
sys.path.insert(0, 'c:/Users/ASUS/Desktop/ORIENTACION V/backend')
from app import create_app
from app.services.estadistica_service import EstadisticaService
import json

app = create_app()

with app.app_context():
    print("Obteniendo evolución de Sanny Agualimpia (usuario_id=23) filtrado hasta App ID 1762...")
    evolucion = EstadisticaService.evolucion_estudiante(23, hasta_aplicacion_id=1762)
    print("\nHistorial de Evolución:")
    for h in evolucion['historial']:
        print(f"  App ID: {h['aplicacion_id']} | Fecha: {h['fecha']} | Perfil: {h['perfil_principal']} | Código RIASEC: {h['codigo_riasec']}")
        print(f"    Puntajes: {h['puntajes']}")
        
    print("\nObteniendo predicción filtrada hasta App ID 1762...")
    prediccion = EstadisticaService.prediccion_vocacional(23, hasta_aplicacion_id=1762)
    print(f"\nTendencias en predicción:")
    for t in prediccion['tendencias']:
        print(f"  Area: {t['area']} | Puntaje Actual: {t['puntaje_actual']} | Predicho: {t['prediccion_proxima']} | Tendencia: {t['tendencia']} | Cambio: {t['cambio_esperado']}")

