"""
Seed datos demográficos para los 3 estudiantes de prueba.
"""
import sys
sys.path.insert(0, '.')

from backend.app import create_app
from backend.app.extensions import db
from backend.app.models.demografico import CampoDemografico, DatoDemografico
from backend.app.models.usuario import Usuario


import random

EDADES = ['15', '16', '17', '18']
GENEROS = ['Femenino', 'Masculino', 'No binario']
GRADOS = ['10°', '11°']
CIUDADES = ['Bogotá', 'Medellín', 'Cali', 'Barranquilla', 'Cartagena', 'Bucaramanga', 'Manizales', 'Pereira', 'Santa Marta']
TIPOS_COLEGIO = ['Público', 'Privado', 'Semi-privado']
ESTRATOS = ['1', '2', '3', '4', '5', '6']

def main():
    app = create_app()

    with app.app_context():
        campos = {c.nombre: c for c in CampoDemografico.query.all()}
        print(f"Campos demográficos disponibles: {list(campos.keys())}")

        estudiantes = Usuario.query.filter_by(activo=True).all()
        print(f"Procesando {len(estudiantes)} estudiantes...")

        for usuario in estudiantes:
            datos = {
                'edad':          random.choice(EDADES),
                'genero':        random.choice(GENEROS),
                'grado_escolar': random.choice(GRADOS),
                'ciudad_region': random.choice(CIUDADES),
                'tipo_colegio':  random.choice(TIPOS_COLEGIO),
                'estrato':       random.choice(ESTRATOS),
            }
            print(f"\n  {usuario.email} (id={usuario.id})")
            for nombre_campo, valor in datos.items():
                campo = campos.get(nombre_campo)
                if not campo:
                    print(f"    ✗ Campo no existe: {nombre_campo}")
                    continue

                # Upsert
                existente = DatoDemografico.query.filter_by(
                    usuario_id=usuario.id,
                    campo_id=campo.id,
                ).first()

                if existente:
                    existente.valor = valor
                    print(f"    ↻ {campo.etiqueta}: {valor}")
                else:
                    db.session.add(DatoDemografico(
                        usuario_id=usuario.id,
                        campo_id=campo.id,
                        valor=valor,
                    ))
                    print(f"    ✓ {campo.etiqueta}: {valor}")

        db.session.commit()
        print("\n✓ Datos demográficos guardados correctamente.")

if __name__ == '__main__':
    main()
