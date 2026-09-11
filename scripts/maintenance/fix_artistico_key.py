# -*- coding: utf-8 -*-
"""Corrige la clave 'Artistico' → 'Artístico' en los perfiles de Santiago Reyes."""
import sys, os, copy
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'backend'))

from backend.app import create_app
app = create_app()

with app.app_context():
    from backend.app.extensions import db
    from backend.app.models.resultado import PerfilVocacional
    from backend.app.models.aplicacion import Aplicacion
    from backend.app.models.usuario import Usuario

    u = Usuario.query.filter_by(email='santiago.reyes@orientacion.edu.co').first()
    apps = Aplicacion.query.filter_by(usuario_id=u.id, estado='completada').all()

    for ap in apps:
        pv = PerfilVocacional.query.filter_by(aplicacion_id=ap.id).first()
        if not pv or not pv.datos_json:
            continue
        ppa = pv.datos_json.get('puntajes_por_area', {})
        if 'Artistico' not in ppa:
            print(f'ap_id={ap.id}: ya corregido, claves={list(ppa.keys())}')
            continue

        new_json = copy.deepcopy(pv.datos_json)
        fixed = {}
        for k, v in new_json['puntajes_por_area'].items():
            new_k = 'Artístico' if k == 'Artistico' else k
            fixed[new_k] = v
        new_json['puntajes_por_area'] = fixed
        pv.datos_json = new_json
        db.session.add(pv)
        print(f'ap_id={ap.id}: corregido, claves={list(fixed.keys())}')

    db.session.commit()
    print('Commit OK')
