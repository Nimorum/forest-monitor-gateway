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

        self.log_telemetry = os.getenv('LOG_TELEMETRY', 'False').lower() in ('true', '1', 't')
        
    def start(self):
        self.running = True
        self._connect_serial()
        self.run_loop()

    def stop(self):
        self.running = False
        if self.ser and self.ser.is_open:
            self.ser.close()
            print("[SYSTEM] Serial port closed.")

    def _connect_serial(self):
        try:
            self.ser = serial.Serial(self.port, self.baud, timeout=1)
            print(f"[OK] Connected to {self.port} at {self.baud} bps.")
        except serial.SerialException as e:
            print(f"[ERROR] Failed to open serial port: {e}")

    def run_loop(self):
        print("[SYSTEM] Main loop started...")
        while self.running:
            self._read_radio()
            self._process_offline_queue()
            time.sleep(0.05)

    def _read_radio(self):
        if not self.ser or not self.ser.is_open:
            return

        if self.ser.in_waiting > 0:
            data = self.ser.readline()
            try:
                decoded = data.decode('utf-8').strip()
                if not decoded:
                    return

                if decoded.startswith('AT') or decoded.startswith('+'):
                    print(f"[AT RESPONSE] {decoded}")
                    return

                if decoded.startswith('{'):
                    self._handle_json_payload(decoded)
                    return

                if len(decoded) <= 2:
                    try:
                        int(decoded, 16)
                        self._handle_rssi_payload(decoded)
                    except ValueError:
                        pass

            except Exception:
                pass
                
    def _handle_json_payload(self, json_string):
        try:
            data = json.loads(json_string)
        except json.JSONDecodeError:
            print(f"[RADIO ERROR] Invalid JSON format: {json_string}")
            return

        mac = data.get("mac_address")
        if not mac:
            print(f"[RADIO ERROR] Packet dropped. 'mac_address' missing: {data}")
            return

        data["collected_at"] = int(time.time())

        if self.log_telemetry:
            self.db.log_telemetry(data)

        method = data.get("method")
        
        if method == "register":
            endpoint = "/nodes/register"
            print(f"[GATEWAY] Processing REGISTRATION for node {mac}...")
            print(f"[GATEWAY] Payload: {json.dumps(data)}")
            success, response, error_type = self.api.register_node(data)
            
        elif method == "telemetry":
            endpoint = "/telemetry"
            print(f"[GATEWAY] Processing TELEMETRY from node {mac}...")
            print(f"[GATEWAY] Payload: {json.dumps(data)}")
            success, response, error_type = self.api.send_telemetry(data)
            
        else:
            print(f"[RADIO ERROR] Unknown method '{method}' for MAC {mac}.")
            return

        if success:
            print(f"[API SUCCESS] Data sent to {endpoint} successfully!")
        else:
            print(f"[API FAIL] {response}. Saving to database for resend.")
            self.db.save_request(endpoint, data)

    def _handle_rssi_payload(self, rssi_tail):
        try:
            rssi_val = -int(rssi_tail, 16)
            print(f"[DEBUG] RSSI: {rssi_val} dBm")
            if not self.log_telemetry:
                return
            self.db.update_latest_telemetry_rssi(rssi_val)
        except Exception as e:
            print(f"[RADIO ERROR] Failed to parse RSSI: {e}")

    def _process_offline_queue(self):
        pending = self.db.get_pending_requests(limit=3, time_threshold_s=10)
        
        for req in pending:
            print(f"[QUEUE] Attempting to resend request ID {req['id']} (Attempt {req['retry_count']})...")
            
            success, response, error_type = self.api._post(req['endpoint'], req['payload'])
            
            if success:
                print(f"[QUEUE] Request ID {req['id']} sent successfully! Deleting from DB.")
                self.db.delete_request(req['id'])
            else:
                if error_type == "NETWORK_ERROR":
                    print("[QUEUE] Network error detected. Keeping request in queue for next attempt.")
                    break
                
                elif error_type == "HTTP_ERROR" or error_type == "UNKNOWN_ERROR":
                    self.db.increment_retry(req['id'])
                    if req['retry_count'] >= self.max_retries:
                        print(f"[QUEUE] Request ID {req['id']} failed too many times ({self.max_retries}). Permanently removed.")
                        self.db.delete_request(req['id'])

if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--export":
        print("[SYSTEM] Exporting telemetry log to CSV...")
        db = OfflineStorage()
        db.export_telemetry_to_csv()
        sys.exit(0)

    print("[SYSTEM] Starting Forest Gateway in Daemon Mode...")
    core = GatewayCore()
    try:
        core.start()
    except KeyboardInterrupt:
        core.stop()
        print("\n[SYSTEM] Gateway shut down by user.")