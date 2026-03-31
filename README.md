# Forest Monitor - LoRa Gateway 📡

Este repositório contém o Gateway Core responsável por fazer a ponte entre a rede LPWAN (LoRa) e a infraestrutura Cloud (API Laravel). 

## 📌 Funcionalidades Principais
O gateway atua como um router intermédio a correr num PC local ou num Raspberry Pi. As suas responsabilidades principais incluem:
* **Escuta Contínua:** Lê os pacotes LoRa recebidos pelo recetor USB (SX1262/SX1276).
* **Descodificação de Pacotes:** Extrai o Endereço MAC, coordenadas GPS e os dados de telemetria (sensores e Vbat).
* **Encaminhamento Dinâmico:** Reencaminha dados de forma segura via HTTP POST para os endpoints do backend (`/nodes/register` ou `/telemetry`) utilizando uma API Key.
* **Resiliência (Smart Retry):** Possui um buffer offline integrado em SQLite. Se a ligação à internet falhar, os pacotes são guardados localmente em segurança e retransmitidos automaticamente assim que a ligação for restaurada.

## 🛠️ Stack Tecnológica
* **Linguagem:** Python 3.11
* **Interface Gráfica (GUI):** `tkinter` (UI Nativa para Desktop)
* **Base de Dados:** `sqlite3` (Armazenamento offline de pacotes)
* **Dependências:** `pyserial`, `requests`, `python-dotenv`
* **CI/CD:** Builds automáticas para Windows e Linux via GitHub Actions usando `PyInstaller`.

## 🚀 Instalação e Utilização

### Opção A: Executáveis Pré-compilados (Recomendado)
Não é necessário instalar o Python para correr este gateway. Os binários standalone são gerados automaticamente em cada lançamento (release).
1. Navegue até ao separador **Releases** no GitHub.
2. Descarregue o `.zip` mais recente para o seu sistema operativo (Windows ou Ubuntu).
3. Extraia os ficheiros e escolha o seu modo de funcionamento:
   * `gateway-ui`: Inicia o painel de controlo gráfico para configuração fácil e monitorização em tempo real.
   * `gateway-daemon`: Inicia o serviço de background (invisível), ideal para servidores e Raspberry Pis.

### Opção B: Correr a partir do Código-Fonte
Se pretender modificar o código ou executá-lo diretamente via Python:
1. Instale as dependências necessárias:
   ```bash
   pip install -r requirements.txt
   ```
2. **Para a Interface Gráfica:** Execute `python ui/app.py`
3. **Para o Serviço em Background:** Execute `python src/gateway.py`

## 🐧 Configuração em Ambiente Linux (Ubuntu / Raspberry Pi OS)

Ao correr este gateway num ambiente Linux, a gestão das portas USB requer permissões específicas. Siga estes passos para garantir uma comunicação sem falhas com o módulo de rádio LoRa.

### 1. Identificar a Porta de Comunicação
Ligue o seu módulo LoRa USB e abra o terminal para descobrir o caminho que lhe foi atribuído:

```bash
ls /dev/ttyUSB*
ls /dev/ttyACM*
```

### 2. Configurar Permissões Globais
O Linux bloqueia o acesso às portas série para utilizadores normais por defeito. Para conceder acesso permanente ao seu utilizador e evitar erros de "Permission denied", adicione o seu utilizador ao grupo `dialout`:

```bash
sudo usermod -a -G dialout $USER
```
**⚠️ Passo Obrigatório:** Tem de terminar a sessão (log out) e voltar a entrar (ou reiniciar a máquina) para que as novas permissões do grupo tenham efeito.

## 🔧 Teste de Comunicação de Hardware

Se não tiver a certeza de que a placa está a responder corretamente na porta configurada, pode testar a ligação manualmente utilizando o emissor de Comandos AT na `gateway-ui`.

1. **Entrar no Modo de Configuração:**
   Digite o seguinte na caixa de envio de comandos e clique em **Send**:
   ```text
   +++
   ```
   *(A placa não vai responder imediatamente, mas entrará em modo de escuta de comandos).*

2. **Testar a Resposta:**
   Envie o comando para solicitar a versão do firmware:
   ```text
   AT+VER
   ```
   ✅ **Sucesso:** A placa deverá responder com algo como `Ver1.2` seguido de `OK`. 

3. **Sair do Modo de Configuração (Crucial):**
   Para permitir que a placa retome a escuta de pacotes de sensores remotos, tem de sair do modo de comandos enviando:
   ```text
   AT+EXIT
   ```

## 📜 Referência de Comandos AT Comuns

Para obter a lista completa de comandos suportados pelo seu módulo específico, entre no Modo de Configuração (`+++`) e envie o comando de ajuda:
```text
AT+HELP
```
*(Em algumas versões de firmware, o comando poderá ser `AT+H` ou `AT+?`)*

Aqui está uma referência rápida para os comandos mais utilizados durante a configuração e depuração do Gateway:

| Comando | Descrição | Resposta Esperada |
| :--- | :--- | :--- |
| `AT+VER` | Verificar versão do firmware | `Ver1.2 OK` |
| `AT+HELP` | Listar todos os comandos AT disponíveis | *(Devolve a lista de comandos)* |
| `AT+RXCH?` | Consultar Canal de Receção atual (Frequência) | `RXCH:868.125 OK` |
| `AT+TXCH?` | Consultar Canal de Transmissão atual | `TXCH:868.125 OK` |
| `AT+SF?` | Consultar Spreading Factor (SF) | `SF:9 OK` |
| `AT+PWR?` | Consultar Potência de Transmissão (dBm) | `PWR:22 OK` |
| `AT+EXIT` | Sair do Modo de Configuração | `OK` |

> **⚠️ Nota Importante:** Lembre-se sempre de enviar `AT+EXIT` quando terminar a configuração. Se a placa for deixada em Modo de Configuração, irá ignorar toda a telemetria rádio recebida dos nós da floresta.