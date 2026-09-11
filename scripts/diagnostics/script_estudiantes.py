import os
import requests

login_url = "http://localhost:5000/api/auth/login"
stats_url = "http://localhost:5000/api/estadisticas/resumen-estudiantes?page=1&per_page=10"
credentials = {
    "email": "bienestar@orientacion.edu.co",
    "password": os.getenv("ORIENTACION_API_PASSWORD", "")
}

try:
    login_response = requests.post(login_url, json=credentials)
    if login_response.status_code != 200:
        print(f"Login failed: {login_response.status_code}")
        print(login_response.text)
        exit(1)
    
    data_login = login_response.json()
    token = data_login.get('access_token') or data_login.get('token')
    
    if not token:
        print("No token found in response")
        exit(1)
    
    headers = {"Authorization": f"Bearer {token}"}
    stats_response = requests.get(stats_url, headers=headers)
    print(f"Status Code: {stats_response.status_code}")
    
    if stats_response.status_code == 200:
        data = stats_response.json()
        # Handle different possible response structures
        estudiantes = data.get('items') if isinstance(data, dict) and 'items' in data else (data.get('estudiantes') if isinstance(data, dict) and 'estudiantes' in data else data)
        
        if isinstance(estudiantes, list):
            for est in estudiantes[:10]:
                print(f"Nombre: {est.get('nombre_completo')}, Grado: {est.get('grado_nombre')}")
        else:
            print("Unexpected data format")
            print(data)
    else:
        print(stats_response.text)

except Exception as e:
    print(f"Error: {e}")
