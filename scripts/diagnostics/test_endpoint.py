import requests
import sys
import os

# Add backend to path to import app correctly
sys.path.append(os.path.join(os.getcwd(), 'backend'))

from backend.app import create_app
from flask_jwt_extended import create_access_token

app = create_app()
with app.app_context():
    secret = app.config.get('JWT_SECRET_KEY')
    print(f'Using JWT_SECRET_KEY: {secret}')
    token = create_access_token(identity={'id': 1, 'email': 'admin@orientacion.edu.co', 'rol': 'ti'})
    headers = {'Authorization': f'Bearer {token}'}
    
    try:
        response = requests.get(
            'http://localhost:5000/api/estadisticas/resumen-estudiantes',
            headers=headers,
            params={'page': 1, 'per_page': 20}
        )
        print(f'Status: {response.status_code}')
        print(f'Response: {response.json()}')
    except Exception as e:
        print(f'Connection Error: {e}')
