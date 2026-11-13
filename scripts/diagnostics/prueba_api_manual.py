import os
import requests

login = requests.post('http://localhost:5000/api/auth/login', json={
    'email': 'admin@orientacion.edu.co',
    'password': os.getenv('ORIENTACION_API_PASSWORD', '')
})
print('Login:', login.status_code)
token = login.json().get('access_token', '')

r = requests.get('http://localhost:5000/api/usuarios/', headers={
    'Authorization': f'Bearer {token}'
})
print('Usuarios:', r.status_code)

data = r.json()
print('Total:', data.get('total'))
for u in data.get('usuarios', []):
    print(f"  {u['email']} - {u['rol']['nombre']}")
