import sqlite3
import json
import os
import sys

def get_real_base_dir():
    """Descobre a verdadeira pasta onde o executável ou script está a correr."""
    if getattr(sys, 'frozen', False):
        return os.path.dirname(sys.executable)
    else:
        return os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))

class OfflineStorage:
    def __init__(self, db_name="offline_buffer.db"):
        base_dir = get_real_base_dir()
        self.db_path = os.path.join(base_dir, db_name)
        self._create_table()

    def _create_table(self):
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS pending_requests (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    endpoint TEXT NOT NULL,
                    payload TEXT NOT NULL,
                    retry_count INTEGER DEFAULT 0,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            conn.commit()

    def save_request(self, endpoint, payload_dict):
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute(
                "INSERT INTO pending_requests (endpoint, payload) VALUES (?, ?)",
                (endpoint, json.dumps(payload_dict))
            )
            conn.commit()

    def get_pending_requests(self, limit=5):
        """Puxa apenas os primeiros X pedidos para não bloquear o loop principal."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT id, endpoint, payload, retry_count FROM pending_requests ORDER BY id ASC LIMIT ?", (limit,))
            rows = cursor.fetchall()
            
            return [{"id": r[0], "endpoint": r[1], "payload": json.loads(r[2]), "retry_count": r[3]} for r in rows]

    def increment_retry(self, request_id):
        """Aumenta o contador de tentativas de um pedido."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("UPDATE pending_requests SET retry_count = retry_count + 1 WHERE id = ?", (request_id,))
            conn.commit()

    def delete_request(self, request_id):
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM pending_requests WHERE id = ?", (request_id,))
            conn.commit()