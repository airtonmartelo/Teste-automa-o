# Informações do Aplicativo
APP_VERSION = "1.0.0"
APP_TITLE = "Automatizador de Testes de Bancada - PCTEC"

# Nomes de arquivos e diretórios
LOG_DIR = "Relatorios"
XML_WIFI = "wifi_profile.xml"
AUDIO_TEST_FILE = "test_audio.wav"  # Nome do arquivo de áudio de teste
ICON_FILE = "app.ico"  # Nome do arquivo de ícone
# LOGO_FILE e THEME_FILE foram removidos pois seus caminhos são construídos diretamente em paths.py

# Status dos testes
STATUS_PASS = "PASS"
STATUS_FAIL = "FAIL"
STATUS_NA = "N/A"

# Configurações de áudio para PyAudio
CHUNK = 1024
CHANNELS = 1
RATE = 44100
RECORD_SECONDS = 5  # Duração da gravação do microfone
