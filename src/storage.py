import sqlite3
import json
import os
import sys
import csv

def get_real_base_dir():
    if getattr(sys, 'frozen', False):
        return os.path.dirname(sys.executable)
    else:
        return os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))

class OfflineStorage:
    def __init__(self, db_name="offline_buffer.db"):
        base_dir = get_real_base_dir()
        self.db_path = os.path.join(base_dir, db_name)
        self._create_tables()

    def _create_tables(self):
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS pending_requests (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    endpoint TEXT NOT NULL,
                    payload TEXT NOT NULL,
                    retry_count INTEGER DEFAULT 0,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS telemetry_log (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    mac_address TEXT,
                    method TEXT,
                    rssi INTEGER,
                    raw_payload TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            conn.commit()

    def save_request(self, endpoint, payload_dict):
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT INTO pending_requests 
                (endpoint, payload, created_at, updated_at) 
                VALUES (?, ?, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
                """,
                (endpoint, json.dumps(payload_dict))
            )
            conn.commit()

    def get_pending_requests(self, limit=5, time_threshold_s=30):
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT id, endpoint, payload, retry_count FROM pending_requests "
                "WHERE (strftime('%s','now') - strftime('%s', updated_at)) > ? "
                "ORDER BY updated_at ASC LIMIT ?",
                (time_threshold_s, limit))
            rows = cursor.fetchall()
            
            return [{"id": r[0], "endpoint": r[1], "payload": json.loads(r[2]), "retry_count": r[3]} for r in rows]

    def increment_retry(self, request_id):
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute(
                "UPDATE pending_requests SET retry_count = retry_count + 1, updated_at = CURRENT_TIMESTAMP WHERE id = ?", 
                (request_id,)
            )
            conn.commit()

    def delete_request(self, request_id):
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM pending_requests WHERE id = ?", (request_id,))
            conn.commit()

    def update_request_timestamp(self, request_id):
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute(
                "UPDATE pending_requests SET updated_at = CURRENT_TIMESTAMP WHERE id = ?", 
                (request_id,)
            )
            conn.commit()

    def log_telemetry(self, data):
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT INTO telemetry_log 
                (mac_address, method, raw_payload, created_at, updated_at) 
                VALUES (?, ?, ?, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
                """,
                (
                    data.get("mac_address"),
                    data.get("method"),
                    json.dumps(data)
                )
            )
            conn.commit()

    def update_latest_telemetry_rssi(self, rssi_val):
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                UPDATE telemetry_log 
                SET rssi = ?, updated_at = CURRENT_TIMESTAMP 
                WHERE id = (SELECT id FROM telemetry_log ORDER BY id DESC LIMIT 1)
                """,
                (rssi_val,)
            )
            conn.commit()
    
    def export_telemetry_to_csv(self, output_filename="telemetry_export.csv"):
        base_dir = get_real_base_dir()
        export_path = os.path.join(base_dir, output_filename)
        
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT * FROM telemetry_log ORDER BY id ASC")
                rows = cursor.fetchall()
                
                column_names = [description[0] for description in cursor.description]

            with open(export_path, 'w', newline='', encoding='utf-8') as f:
                writer = csv.writer(f)
                writer.writerow(column_names)
                writer.writerows(rows)
                
            print(f"[SYSTEM] Telemetry successfully exported to {export_path}")
            return True
            
        except Exception as e:
            print(f"[ERROR] Failed to export telemetry to CSV: {e}")
            return False