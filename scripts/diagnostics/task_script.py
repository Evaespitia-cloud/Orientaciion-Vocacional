import os
import requests
import json

login_url = 'http://localhost:5000/api/auth/login'
login_data = {
    'email': 'bienestar@orientacion.edu.co',
    'password': os.getenv('ORIENTACION_API_PASSWORD', '')
}

try:
    response = requests.post(login_url, json=login_data)
    print(f'Login Status: {response.status_code}')
    token = response.json().get('access_token')
    print(f'Access Token: {"Present" if token else "Not Found"}')

    if token:
        headers = {'Authorization': f'Bearer {token}'}
        summary_url = 'http://localhost:5000/api/estadisticas/resumen-estudiantes?page=1&per_page=5'
        res = requests.get(summary_url, headers=headers)
        print(f'Summary Status: {res.status_code}')
        try:
            print(json.dumps(res.json(), indent=2))
        except:
            print('Body (not JSON):')
            print(res.text[:500])
except Exception as e:
    print(f'Error: {e}')
