import os
import requests, json

BASE = 'http://localhost:5000/api'
health = requests.get(BASE.replace('/api', '/api/health'), timeout=10)
print('health_status=', health.status_code)

admin = requests.post(BASE + '/auth/login', json={'email':'admin@orientacion.edu.co','password': os.getenv('ORIENTACION_API_PASSWORD', '')}, timeout=10)
print('login_status=', admin.status_code)
if admin.status_code == 200:
    token = admin.json().get('access_token')
    headers = {'Authorization': 'Bearer ' + token}
    cfg = requests.get(BASE + '/configuracion/15', headers=headers, timeout=10)
    print('config_status=', cfg.status_code)
    if cfg.status_code == 200:
        config = cfg.json().get('configuracion', {})
        print('config_instrument_id=', config.get('instrumento_id'))
        iid = config.get('instrumento_id')
        inst = requests.get(f'{BASE}/instrumentos/{iid}', headers=headers, timeout=10)
        print('instrument_status=', inst.status_code)
        if inst.status_code == 200:
            data = inst.json()
            instrument = data.get('instrumento', {})
            dims = instrument.get('dimensiones', [])
            interests = [d for d in dims if 'intereses' in (d.get('nombre') or '').lower()]
            print('dims=', len(dims))
            print('interests_dim_count=', len(interests))
            if interests:
                d = interests[0]
                print('interest_dimension_name=', d.get('nombre'))
                scales = d.get('escalas', [])
                print('interest_scales=', len(scales))
                if scales:
                    print('first_scale_items=', len(scales[0].get('items', [])))
                    print('first_scale_texts=', [i.get('texto') for i in scales[0].get('items', [])[:5]])
        else:
            print(inst.text[:500])
    else:
        print(cfg.text[:500])
else:
    print(admin.text[:500])
