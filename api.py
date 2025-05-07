from dotenv import load_dotenv
import os
import requests
from logger import server_log


class ApiHandler:
    def __init__(self):
        load_dotenv()
        self.host = os.getenv('FAST_API_HOST', 'localhost')
        
    def set_backup_status(self, id, status):
        api_url = f'http://{self.host}/api/v1/devices/{id}'
        data = {
            'backup_status': status
        }
        try:
            response = requests.put(api_url, json=data)
            
            if response.status_code == 200:
                server_log.debug("Данные успешно переданы")
            else:
                server_log.warning(f"Ошибка передачи данных {api_url}: {response.text}")
                
        except Exception as e:
            server_log.warning(f"Произошла ошибка: {e}")

api_handler = ApiHandler()
