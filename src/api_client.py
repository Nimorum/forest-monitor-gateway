import requests

class ForestApiClient:
    def __init__(self, base_url, api_key):
        self.base_url = base_url.rstrip('/') if base_url else ""
        self.headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
            "Accept": "application/json"
        }

    def _post(self, endpoint, payload):
        """Método interno para tratar os erros de forma inteligente."""
        url = f"{self.base_url}{endpoint}"
        try:
            response = requests.post(url, json=payload, headers=self.headers, timeout=5)
            response.raise_for_status()
            return True, response.json(), None
            
        except (requests.exceptions.ConnectionError, requests.exceptions.Timeout):
            # Erro de Rede (Sem internet, DNS falhou, etc) - Tentar infinitamente
            return False, "Falha de rede (Sem Internet)", "NETWORK_ERROR"
            
        except requests.exceptions.HTTPError as e:
            # Erro do Servidor (500, 404, 403, 422, etc) - Tentar X vezes
            return False, f"Erro da API: {e}", "HTTP_ERROR"
            
        except Exception as e:
            return False, str(e), "UNKNOWN_ERROR"

    def send_telemetry(self, payload):
        return self._post('/telemetry', payload)
        
    def register_node(self, payload):
        return self._post('/nodes/register', payload)