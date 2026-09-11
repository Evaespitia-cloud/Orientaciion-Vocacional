import sys
from datetime import datetime

sys.path.insert(0, 'c:/Users/ASUS/Desktop/ORIENTACION V/backend')
from app import create_app
from app.extensions import db
from app.models.usuario import Usuario
from app.models.aplicacion import Aplicacion, Respuesta
from app.models.resultado import ResultadoDimension, PerfilVocacional
from app.models.instrumento import Item, Escala, Dimension

app = create_app()

with app.app_context():
    print("=== BUSCANDO ESTUDIANTE DE PRUEBA ===")
    estudiante = Usuario.query.filter_by(email='santiago.reyes@orientacion.edu.co').first()
    if not estudiante:
        print("Estudiante no encontrado.")
        sys.exit(1)
    
    print(f"Estudiante: {estudiante.nombres} {estudiante.apellidos} (ID: {estudiante.id})")
    
    print("\n=== APLICACIONES ===")
    aplicaciones = Aplicacion.query.filter_by(usuario_id=estudiante.id).all()
    for app_obj in aplicaciones:
        print(f"\nAplicacion ID: {app_obj.id}")
        print(f"  Configuracion ID: {app_obj.configuracion_id}")
        print(f"  Instrumento: {app_obj.configuracion.instrumento.nombre if app_obj.configuracion else 'N/A'}")
        print(f"  Estado: {app_obj.estado}")
        print(f"  Progreso: {app_obj.progreso}%")
        print(f"  Fecha Fin: {app_obj.fecha_fin}")
        
        # Respuestas
        resps = Respuesta.query.filter_by(aplicacion_id=app_obj.id).all()
        print(f"  Total Respuestas: {len(resps)}")
        if resps:
            print("  Muestra de respuestas (primeras 5):")
            for r in resps[:5]:
                item = Item.query.get(r.item_id)
                print(f"    Item ID: {r.item_id} | Texto: '{item.texto[:40]}...' | Valor: {r.valor} | Valor Texto: '{r.valor_texto}'")
        
        # Resultados de dimensiones
        res_dims = ResultadoDimension.query.filter_by(aplicacion_id=app_obj.id).all()
        print("  Resultados Dimensiones:")
        for rd in res_dims:
            print(f"    Dim: {rd.dimension.nombre} | Bruto: {rd.puntaje_bruto} | Normalizado: {rd.puntaje_normalizado}% | Nivel: {rd.nivel}")
            
        # Perfil Vocacional
        perfil = PerfilVocacional.query.filter_by(aplicacion_id=app_obj.id).first()
        if perfil:
            print("  Perfil Vocacional:")
            print(f"    Principal: {perfil.perfil_principal}")
            print(f"    Secundario: {perfil.perfil_secundario}")
            print(f"    Codigo RIASEC: {perfil.datos_json.get('codigo_riasec') if perfil.datos_json else 'N/A'}")
            print(f"    Puntajes por Area:")
            if perfil.datos_json and 'puntajes_por_area' in perfil.datos_json:
                for area, val in perfil.datos_json['puntajes_por_area'].items():
                    print(f"      {area}: {val}")
        else:
            print("  Perfil Vocacional: NO GENERADO")
