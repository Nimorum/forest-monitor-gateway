import os
import time
import serial
import sys
import json
from dotenv import load_dotenv
from api_client import ForestApiClient
from storage import OfflineStorage

def get_real_base_dir():
    if getattr(sys, 'frozen', False):
        return os.path.dirname(sys.executable)
    return os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))

BASE_DIR = get_real_base_dir()
ENV_FILE = os.path.join(BASE_DIR, '.env')

class GatewayCore:
    def __init__(self):
        load_dotenv(ENV_FILE)
        self.port = os.getenv('SERIAL_PORT', '/dev/ttyACM0')
        self.baud = int(os.getenv('BAUD_RATE', '115200'))
        
        self.api = ForestApiClient(os.getenv('API_URL'), os.getenv('API_KEY'))
        self.db = OfflineStorage()
        
        self.ser = None
        self.running = False
        self.max_retries = int(os.getenv('MAX_RETRIES', '5'))

    def start(self):
        self.running = True
        self._connect_serial()
        self.run_loop()

    def stop(self):
        self.running = False
        if self.ser and self.ser.is_open:
            self.ser.close()
            print("[SISTEMA] Porta Série fechada.")

    def _connect_serial(self):
        try:
            self.ser = serial.Serial(self.port, self.baud, timeout=1)
            print(f"[OK] Conectado a {self.port} a {self.baud} bps.")
        except serial.SerialException as e:
            print(f"[ERRO] Falha ao abrir porta série: {e}")

    def run_loop(self):
        """O Loop Principal Independente"""
        print("[SISTEMA] Main Loop iniciado...")
        while self.running:

            self._read_radio()
            
            self._process_offline_queue()
            
            time.sleep(0.05) # Pequena pausa para não esgotar o CPU

    def _read_radio(self):
        if not self.ser or not self.ser.is_open:
            return

        if self.ser.in_waiting > 0:
            data = self.ser.readline()
            try:
                decoded = data.decode('utf-8').strip()
                if decoded:
                    print(f"[RÁDIO] Recebido: {decoded}")
                    self._handle_incoming_data(decoded)
            except Exception as e:
                pass # Ignorar lixo na linha

    def _handle_incoming_data(self, raw_string):
        """
        Faz o parse da string LoRa, valida o MAC e encaminha 
        para o endpoint correto baseado no campo 'method'.
        """
        try:
            data = json.loads(raw_string)
        except json.JSONDecodeError:
            print(f"[ERRO RÁDIO] Formato inválido. Não é um JSON: {raw_string}")
            return

        mac = data.get("mac_address")
        if not mac:
            print(f"[ERRO RÁDIO] Pacote descartado. 'mac_address' ausente no JSON: {data}")
            return
        
        data.set("collected_at", int(time.time()))

        method = data.get("method")
        
        if method == "register":
            endpoint = "/nodes/register"
            print(f"[GATEWAY] A processar REGISTO para o nó {mac}...")
            success, response, error_type = self.api.register_node(data)
            
        elif method == "telemetry":
            endpoint = "/telemetry"
            print(f"[GATEWAY] A processar TELEMETRIA do nó {mac}...")
            success, response, error_type = self.api.send_telemetry(data)
            
        else:
            print(f"[ERRO RÁDIO] Método '{method}' desconhecido para o MAC {mac}.")
            return

        if success:
            print(f"[API SUCCESS] Dados enviados para {endpoint} com sucesso!")
        else:
            print(f"[API FAIL] {response}. A guardar na base de dados para reenvio.")
            self.db.save_request(endpoint, data)

    def _process_offline_queue(self):
        """Tenta enviar pedidos que falharam anteriormente."""
        pending = self.db.get_pending_requests(limit=3, time_threshold_s=30) # Processa no máximo 3 de cada vez
        
        for req in pending:
            print(f"[QUEUE] A tentar reenviar pedido ID {req['id']} (Tentativa {req['retry_count']})...")
            
            success, response, error_type = self.api._post(req['endpoint'], req['payload'])
            
            if success:
                print(f"[QUEUE] Pedido ID {req['id']} enviado com sucesso! A apagar da DB.")
                self.db.delete_request(req['id'])
            else:
                if error_type == "NETWORK_ERROR":
                    print("[QUEUE] Sem internet.")
                    break # Se não há net, não vale a pena tentar os próximos pedidos
                
                elif error_type == "HTTP_ERROR" or error_type == "UNKNOWN_ERROR":
                    self.db.increment_retry(req['id'])
                    if req['retry_count'] >= self.max_retries:
                        print(f"[QUEUE] Pedido ID {req['id']} falhou demasiadas vezes ({self.max_retries}). Removido definitivamente.")
                        self.db.delete_request(req['id'])

if __name__ == "__main__":
    print("[SISTEMA] A arrancar Forest Gateway em Modo Daemon...")
    core = GatewayCore()
    try:
        core.start()
    except KeyboardInterrupt:
        core.stop()
        print("\n[SISTEMA] Gateway encerrado pelo utilizador.")