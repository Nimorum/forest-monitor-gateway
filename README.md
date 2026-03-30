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
- **Interface Gráfica:** `tkinter` (UI Nativa)
- **Dependências Principais:** `pyserial` (comunicação com rádio USB), `requests` (HTTP POSTs para a API), `python-dotenv` (gestão de chaves API).

## 🚀 Como Executar

### Opção A: Interface Gráfica (Recomendado para Desktop)
Uma interface visual interativa está disponível para facilitar a configuração, teste e monitorização dos dados:
1. Instalar dependências: `pip install -r requirements.txt`
2. Iniciar a interface: `python src/app.py`
3. Inserir a porta de comunicação (ex: `COM3` ou `/dev/ttyACM0`) e a API Key diretamente no painel.
4. Clicar em **Start Gateway**. As configurações são guardadas automaticamente no ficheiro `.env`.

### Opção B: Modo Consola / Daemon (Recomendado para Servidores/RPi)
Para executar o gateway de forma invisível ou em sistemas sem interface gráfica:
1. Instalar dependências: `pip install -r requirements.txt`
2. Configurar o ficheiro `.env` na raiz do projeto com o URL do servidor, a API Key e a Porta Serial.
3. Executar o serviço: `python src/gateway.py`

---

## 🐧 Configuração em Ambiente Linux (Ubuntu / Raspberry Pi OS)

Ao correr este gateway num ambiente Linux, a gestão de portas e permissões difere do Windows. Siga os passos abaixo para garantir a comunicação com o módulo de rádio USB.

### 1. Identificar a Porta de Comunicação
Ligue o módulo LoRa USB ao computador e abra o terminal para descobrir o caminho atribuído ao dispositivo:

```bash
# Verificar portas USB convencionais:
ls /dev/ttyUSB*

# Se não retornar resultados, verificar portas ACM:
ls /dev/ttyACM*

```
(Opcional: Pode usar o comando sudo dmesg | grep tty e observar as últimas linhas para confirmar o nome exato atribuído pelo sistema quando o dispositivo é ligado).

Configurar Permissões Globais (Erro "Permission denied")
Por razões de segurança, o Linux bloqueia a leitura de portas série a utilizadores normais. Para conceder acesso permanente ao seu utilizador, é necessário adicioná-lo ao grupo dialout:

```bash
sudo usermod -a -G dialout $USER
```
⚠️ Passo Obrigatório: Para que o sistema assuma o novo grupo de permissões, é estritamente necessário Terminar a Sessão (Log Out) e voltar a entrar, ou reiniciar o computador. Após o reinício, o Gateway conseguirá ler a porta /dev/tty... sem necessitar de privilégios de administrador (sudo).

## 🔧 Teste de Comunicação (Hardware)

Se não tiver a certeza se a placa está a responder corretamente na porta configurada, pode testar a comunicação manualmente através da Interface Gráfica ou de qualquer Monitor Série (ex: PuTTY, Arduino IDE).

A placa usa comandos **AT** para configuração. Para testar, siga estes passos:

1. **Entrar no Modo de Configuração:**
   Na caixa de envio de dados (na parte inferior da Interface Gráfica), digite o seguinte comando e clique em **Send Data**:
   ```text
   +++
   ```
   *(A placa não deve devolver nenhuma mensagem imediatamente, mas entrará em modo de escuta de comandos).*

2. **Testar a Resposta:**
   Em seguida, envie o comando para pedir a versão do Firmware:
   ```text
   AT+VER
   ```
   ✅ **Sucesso:** Se a ligação estiver correta, a placa irá responder com algo como `Ver1.2` seguido de `OK`. Isto confirma que o Gateway consegue falar com a placa!

3. **Sair do Modo de Configuração (Muito Importante):**
   Para que a placa volte a escutar as mensagens rádio dos sensores na floresta, tem **obrigatoriamente** de sair do modo de comandos enviando:
   ```text
   AT+EXIT
   ```
   A placa responderá com `OK` e voltará ao modo de funcionamento normal (Transparente).

**Dica:** Outros comandos úteis incluem `AT+HELP` (lista todos os comandos), `AT+RXCH?` (verifica o canal de receção) e `AT+SF?` (verifica o Spreading Factor).
