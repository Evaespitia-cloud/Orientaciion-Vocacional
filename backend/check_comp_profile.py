import sys
sys.path.insert(0, 'c:/Users/ASUS/Desktop/ORIENTACION V/backend')
from app import create_app
from app.models.resultado import PerfilVocacional

app = create_app()

with app.app_context():
    # Find any PerfilVocacional for instrument 6 (Competencias)
    pv = PerfilVocacional.query.join(PerfilVocacional.aplicacion).filter(
        PerfilVocacional.aplicacion.has(configuracion_id=16)
    ).first()
    
    if pv:
        print(f"Perfil Vocacional ID: {pv.id} (Aplicacion ID: {pv.aplicacion_id})")
        print(f"datos_json: {pv.datos_json}")
    else:
        print("No se encontro PerfilVocacional para Competencias.")
