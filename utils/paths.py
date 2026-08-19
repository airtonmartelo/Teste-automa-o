import os
import sys
from pathlib import Path
from . import constants

# Lógica para determinar os caminhos base para recursos e execução
if getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS"):
    # Rodando como .exe (PyInstaller)
    BASE_RESOURCES_PATH = Path(sys._MEIPASS)
    BASE_EXECUTION_PATH = Path(sys.executable).parent
else:
    # Rodando como script .py
    BASE_EXECUTION_PATH = Path(__file__).resolve().parent.parent
    BASE_RESOURCES_PATH = BASE_EXECUTION_PATH

# --- Caminhos para arquivos que são LIDOS E ESCRITOS em tempo de execução ---
# Estes arquivos devem ficar ao lado do .exe para serem compartilhados entre os programas.
WIFI_XML_PATH = BASE_EXECUTION_PATH / "assets" / constants.XML_WIFI
CONFIG_JSON_PATH = BASE_EXECUTION_PATH / "assets" / "config.json"

# --- Caminhos para recursos SOMENTE LEITURA (empacotados no .exe) ---
# Estes caminhos apontam para a pasta temporária _MEIPASS quando o app está "congelado".

# Arquivos em 'assets/audio'
AUDIO_TEST_PATH = BASE_RESOURCES_PATH / "assets" / "audio" / constants.AUDIO_TEST_FILE
# Arquivos em 'assets/icons'
ICON_PATH = BASE_RESOURCES_PATH / "assets" / "icons" / constants.ICON_FILE
# Arquivos em 'assets/images'
LOGO_WHITE_PATH = BASE_RESOURCES_PATH / "assets" / "images" / "logo_white.png"
LOGO_DARK_PATH = BASE_RESOURCES_PATH / "assets" / "images" / "logo_dark.png"

# Arquivos em 'theme' (pasta de nível superior, não dentro de assets)
THEME_PATH = BASE_RESOURCES_PATH / "theme" / "custom_theme.json"
# Caminho para o diretório de relatórios (criado ao lado do .exe ou script)
LOGS_DIR_PATH = BASE_EXECUTION_PATH / constants.LOG_DIR
