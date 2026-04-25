import tkinter as tk
from tkinter import scrolledtext
import threading
import sys
import os
from dotenv import load_dotenv, set_key

def get_real_base_dir():
    if getattr(sys, 'frozen', False):
        return os.path.dirname(sys.executable)
    return os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))

# --- Configuração de Caminhos ---
BASE_DIR = get_real_base_dir()
ENV_FILE = os.path.join(BASE_DIR, '.env')
SRC_DIR = os.path.join(BASE_DIR, 'src')

if not getattr(sys, 'frozen', False):
    SRC_DIR = os.path.join(BASE_DIR, 'src')
    if SRC_DIR not in sys.path:
        sys.path.append(SRC_DIR)

if SRC_DIR not in sys.path:
    sys.path.append(SRC_DIR)

from gateway import GatewayCore

class TextRedirector:
    """Captura todos os print() do sistema e injeta na interface gráfica de forma segura."""
    def __init__(self, widget):
        self.widget = widget

    def write(self, str_data):
        self.widget.after(0, self._append, str_data)

    def _append(self, str_data):
        self.widget.insert(tk.END, str_data)
        self.widget.see(tk.END)

    def flush(self):
        pass

class GatewayUI:
    def __init__(self, root):
        self.root = root
        self.root.title("Forest Monitor - LoRa Gateway Control Panel")
        self.root.geometry("750x600")

        load_dotenv(ENV_FILE)

        self.core = None
        self.core_thread = None

        self._build_interface()

        sys.stdout = TextRedirector(self.log_area)
        print("[SISTEMA] Interface Gráfica inicializada. Pronta a arrancar.")

    def _build_interface(self):
        """Constrói os elementos visuais da janela."""
        config_frame = tk.LabelFrame(self.root, text=" Configurações do Sistema ", padx=10, pady=10)
        config_frame.pack(pady=10, fill=tk.X, padx=15)

        tk.Label(config_frame, text="Porta (COM/TTY):").grid(row=0, column=0, sticky=tk.W)
        self.port_entry = tk.Entry(config_frame, width=20)
        self.port_entry.grid(row=0, column=1, padx=5, pady=2)
        self.port_entry.insert(0, os.getenv('SERIAL_PORT', '/dev/ttyACM0'))

        tk.Label(config_frame, text="Baud Rate:").grid(row=0, column=2, sticky=tk.W, padx=10)
        self.baud_entry = tk.Entry(config_frame, width=10)
        self.baud_entry.grid(row=0, column=3, padx=5, pady=2)
        self.baud_entry.insert(0, os.getenv('BAUD_RATE', '115200'))

        tk.Label(config_frame, text="API Endpoint:").grid(row=1, column=0, sticky=tk.W, pady=5)
        self.url_entry = tk.Entry(config_frame, width=50)
        self.url_entry.grid(row=1, column=1, columnspan=3, sticky=tk.W, padx=5)
        self.url_entry.insert(0, os.getenv('API_URL', 'http://dominio.com/api'))

        tk.Label(config_frame, text="API Key:").grid(row=2, column=0, sticky=tk.W, pady=5)
        self.key_entry = tk.Entry(config_frame, width=50, show="*")
        self.key_entry.grid(row=2, column=1, columnspan=3, sticky=tk.W, padx=5)
        self.key_entry.insert(0, os.getenv('API_KEY', ''))

        self.save_btn = tk.Button(config_frame, text="Guardar no .env", command=self.save_env)
        self.save_btn.grid(row=3, column=1, sticky=tk.W, pady=10)

        control_frame = tk.Frame(self.root)
        control_frame.pack(pady=5, fill=tk.X, padx=15)

        self.start_btn = tk.Button(control_frame, text="Ligar Gateway", command=self.start_gateway, bg="#28a745", fg="white", width=15)
        self.start_btn.pack(side=tk.LEFT, padx=5)

        self.stop_btn = tk.Button(control_frame, text="Parar Gateway", command=self.stop_gateway, bg="#dc3545", fg="white", state=tk.DISABLED, width=15)
        self.stop_btn.pack(side=tk.LEFT, padx=5)

        self.log_area = scrolledtext.ScrolledText(self.root, width=85, height=20, bg="#1e1e1e", fg="#d4d4d4")
        self.log_area.pack(pady=10, padx=15)

        bottom_frame = tk.Frame(self.root)
        bottom_frame.pack(pady=5, fill=tk.X, padx=15)

        self.send_entry = tk.Entry(bottom_frame, width=65)
        self.send_entry.pack(side=tk.LEFT, padx=5)
        self.send_entry.bind("<Return>", self.send_data)

        self.send_btn = tk.Button(bottom_frame, text="Enviar AT", command=self.send_data, state=tk.DISABLED)
        self.send_btn.pack(side=tk.LEFT, padx=5)

    def save_env(self):
        try:
            if not os.path.exists(ENV_FILE):
                with open(ENV_FILE, 'w') as f: f.write("")
            
            set_key(ENV_FILE, 'SERIAL_PORT', self.port_entry.get().strip())
            set_key(ENV_FILE, 'BAUD_RATE', self.baud_entry.get().strip())
            set_key(ENV_FILE, 'API_URL', self.url_entry.get().strip())
            set_key(ENV_FILE, 'API_KEY', self.key_entry.get().strip())
            
            print("[SISTEMA] Configurações guardadas com sucesso no .env")
        except Exception as e:
            print(f"[ERRO] Falha ao guardar .env: {e}")

    def start_gateway(self):
        self.save_env()

        load_dotenv(ENV_FILE, override=True)

        self.start_btn.config(state=tk.DISABLED)
        self.stop_btn.config(state=tk.NORMAL)
        self.send_btn.config(state=tk.NORMAL)

        self.core = GatewayCore()

        self.core_thread = threading.Thread(target=self.core.start, daemon=True)
        self.core_thread.start()

    def stop_gateway(self):
        if self.core:
            self.core.stop()
            
        self.start_btn.config(state=tk.NORMAL)
        self.stop_btn.config(state=tk.DISABLED)
        self.send_btn.config(state=tk.DISABLED)

    def send_data(self, event=None):
        if self.core and self.core.ser and self.core.ser.is_open:
            msg = self.send_entry.get().strip()
            if msg:
                self.core.ser.write((msg + "\r\n").encode('utf-8'))
                print(f"[AT TX] → {msg}")
                self.send_entry.delete(0, tk.END)
        else:
            print("[AVISO] Não pode enviar comandos AT. A placa não está ligada.")

if __name__ == "__main__":
    root = tk.Tk()
    
    # Restaura o output normal se a janela for fechada (boa prática)
    def on_closing():
        sys.stdout = sys.__stdout__
        root.destroy()
        
    root.protocol("WM_DELETE_WINDOW", on_closing)
    
    app = GatewayUI(root)
    root.mainloop()