# Forest Monitor - LoRa Gateway 📡

Este repositório contém o código do Gateway Central responsável por fazer a ponte entre a rede LPWAN (LoRa) e a infraestrutura Cloud (API Laravel).

## 📌 Funcionalidade
O script atua como um serviço em segundo plano (daemon) a correr num PC local ou Raspberry Pi. As suas responsabilidades são:
1. **Escuta Contínua:** Ler os pacotes LoRa recebidos pelo recetor USB (SX1262/SX1276).
2. **Descodificação:** Extrair o MAC Address, coordenadas GPS (no deploy) e os dados de telemetria (sensores e Vbat).
3. **Encaminhamento:** Fazer o POST seguro (via API Key) destes dados para o endpoint `/api/telemetry` do Backend.
4. **Resiliência:** (A implementar) Buffer local em caso de falha de internet, garantindo a robustez do sistema distribuído.

## 🛠️ Stack Tecnológica
- **Linguagem:** Python 3.x
- **Dependências Principais:** `pyserial` (comunicação com rádio USB), `requests` (HTTP POSTs para a API), `python-dotenv` (gestão de chaves API).

## 🚀 Como Executar
1. Instalar dependências: `pip install -r requirements.txt`
2. Configurar o ficheiro `.env` com o URL do servidor Laravel e a API Key (Sanctum).
3. Executar o serviço: `python src/gateway.py`
