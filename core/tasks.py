import os
import subprocess
import logging
import json
import time
from utils import paths


def _get_wlan_interface():
    """Obtém o nome da primeira interface WLAN disponível para garantir que os comandos netsh sejam explícitos."""
    try:
        # Usar lista de argumentos sem shell=True e timeout para segurança e estabilidade
        result = subprocess.run(
            ["netsh", "wlan", "show", "interfaces"],
            capture_output=True,
            text=True,
            encoding="latin-1",
            errors="ignore",
            timeout=10,
        )
        if result.returncode == 0:
            lines = result.stdout.splitlines()
            for line in lines:
                stripped_line = line.strip()
                if (
                    stripped_line.startswith("Name") or stripped_line.startswith("Nome")
                ) and ":" in stripped_line:
                    interface_name = stripped_line.split(":", 1)[1].strip()
                    if interface_name:
                        logging.info(f"Interface Wi-Fi encontrada: '{interface_name}'")
                        return interface_name
        logging.warning("Nenhuma interface Wi-Fi encontrada.")
        return None
    except subprocess.TimeoutExpired:
        logging.error("Tempo limite esgotado ao buscar interfaces Wi-Fi.")
        return None
    except Exception as e:
        logging.error(f"Erro ao obter interface Wi-Fi: {e}")
        return None


def connect_wifi():
    """Adiciona o perfil de Wi-Fi do `wifi_profile.xml` e tenta conectar à rede configurada."""
    logging.info("Tentando conectar ao Wi-Fi configurado...")

    if not paths.CONFIG_JSON_PATH.exists() or not paths.WIFI_XML_PATH.exists():
        logging.warning("Configuração de Wi-Fi não encontrada. Execute 'setup_wifi.py' para configurar.")
        return

    try:
        with open(paths.CONFIG_JSON_PATH, "r", encoding="utf-8") as f:
            config_data = json.load(f)
    except (json.JSONDecodeError, FileNotFoundError) as e:
        logging.error(
            f"Arquivo de configuração de Wi-Fi corrompido ou ilegível: {e}. Execute 'setup_wifi.py'."
        )
        return

    if not config_data.get("wifi_configured") or "wifi_ssid" not in config_data:
        logging.warning("Wi-Fi não configurado no arquivo JSON. Execute 'setup_wifi.py'.")
        return

    wifi_ssid = config_data["wifi_ssid"]

    # Etapa 1: Obter a interface de rede explicitamente para evitar ambiguidades.
    interface = _get_wlan_interface()
    if not interface:
        logging.error("Não foi possível continuar a conexão Wi-Fi sem uma interface de rede sem fio.")
        return

    # Etapa 1: Deletar o perfil existente para garantir uma importação limpa.
    # Isso evita erros caso o perfil já exista, mas com uma senha ou configuração antiga.
    logging.info(
        f"--- Removendo perfil Wi-Fi antigo '{wifi_ssid}' da interface '{interface}' (se existir)... ---"
    )
    cmd_del = ["netsh", "wlan", "delete", "profile", f"name={wifi_ssid}", f"interface={interface}"]
    try:
        proc_del = subprocess.run(
            cmd_del, capture_output=True, text=True, encoding="latin-1", errors="ignore", timeout=10
        )
        # A saída é logada para depuração, mas não tratamos como erro, pois é esperado que falhe se o perfil não existir.
        if proc_del.stdout and "não foi encontrado" not in proc_del.stdout:
            logging.info(proc_del.stdout.strip())
        if proc_del.stderr:
            logging.warning(proc_del.stderr.strip())
    except subprocess.TimeoutExpired:
        logging.warning("Tempo limite esgotado ao remover perfil Wi-Fi antigo.")

    # Etapa 2: Adicionar o novo perfil a partir do arquivo XML.
    logging.info(f"--- Adicionando perfil de Wi-Fi à interface '{interface}' ---")
    cmd_add = [
        "netsh",
        "wlan",
        "add",
        "profile",
        f"filename={paths.WIFI_XML_PATH}",
        f"interface={interface}",
        "user=all",
    ]
    try:
        proc_add = subprocess.run(
            cmd_add, capture_output=True, text=True, encoding="latin-1", errors="ignore", timeout=10
        )
        if proc_add.stdout:
            logging.info(proc_add.stdout.strip())
        if proc_add.stderr:
            logging.error(proc_add.stderr.strip())
    except subprocess.TimeoutExpired:
        logging.error("Tempo limite esgotado ao adicionar perfil Wi-Fi.")

    # Adiciona uma pausa para permitir que o serviço WLAN processe o novo perfil e escaneie as redes.
    # Isso resolve uma condição de corrida comum onde o comando 'connect' é executado antes que o sistema
    # reconheça que a rede está disponível.
    logging.info("Aguardando 2 segundos para a estabilização da rede...")
    time.sleep(2)

    # Etapa 3: Conectar à rede.
    logging.info(f"--- Conectando à rede '{wifi_ssid}' na interface '{interface}' ---")
    cmd_conn = ["netsh", "wlan", "connect", f"name={wifi_ssid}", f"interface={interface}"]
    try:
        proc_conn = subprocess.run(
            cmd_conn, capture_output=True, text=True, encoding="latin-1", errors="ignore", timeout=10
        )
        if proc_conn.stdout:
            logging.info(proc_conn.stdout.strip())
        if proc_conn.stderr:
            logging.error(proc_conn.stderr.strip())
    except subprocess.TimeoutExpired:
        logging.error("Tempo limite esgotado ao conectar à rede Wi-Fi.")
    logging.info("-" * 35)


def run_vendor_updates(manufacturer: str):
    """Detecta o fabricante e tenta executar a ferramenta de atualização de drivers apropriada."""
    manufacturer_upper = manufacturer.upper()
    logging.info(f"Verificando atualizações de drivers para o fabricante: {manufacturer}")

    if "DELL" in manufacturer_upper:
        logging.info("Equipamento DELL detectado. Procurando Dell Command | Update...")
        dcu_possible_paths = [
            r"C:\Program Files\Dell\CommandUpdate\DellCommandUpdate.exe",
            r"C:\Program Files (x86)\Dell\CommandUpdate\DellCommandUpdate.exe",
        ]
        dcu_gui_path = None
        for path in dcu_possible_paths:
            if os.path.exists(path):
                dcu_gui_path = path
                break

        if dcu_gui_path:
            logging.info(f"Encontrado! Abrindo a interface do Dell Command | Update em '{dcu_gui_path}'...")
            logging.info(
                "O script continuará com os outros testes. Inicie a verificação de drivers manualmente no programa."
            )
            subprocess.Popen([dcu_gui_path])
        else:
            logging.info(
                "Versão clássica não encontrada. Tentando abrir a versão da Microsoft Store (UWP)..."
            )
            try:
                os.startfile("dell-command-update:")
            except OSError as e:
                logging.warning(f"Não foi possível abrir dell-command-update via protocolo: {e}")
            logging.info(
                "Se o programa não abrir, ele deve ser instalado previamente (seja a versão clássica ou da Store)."
            )
            logging.info(f"(Caminhos da versão clássica verificados: {dcu_possible_paths})")

    elif "LENOVO" in manufacturer_upper:
        logging.info("Equipamento LENOVO detectado. Procurando Lenovo System Update...")
        tvsu_possible_paths = [
            r"C:\Program Files (x86)\Lenovo\System Update\tvsu.exe",
            r"C:\Program Files\Lenovo\System Update\tvsu.exe",
        ]
        tvsu_path = None
        for path in tvsu_possible_paths:
            if os.path.exists(path):
                tvsu_path = path
                break

        if tvsu_path:
            logging.info(f"Encontrado! Abrindo a interface do Lenovo System Update em '{tvsu_path}'...")
            logging.info(
                "O script continuará com os outros testes. Inicie a verificação de drivers manualmente no programa."
            )
            subprocess.Popen([tvsu_path])
        else:
            logging.info(
                "Lenovo System Update não encontrado. Tentando abrir o Lenovo Vantage (versão da Microsoft Store)..."
            )
            try:
                os.startfile("lenovovantage:")
            except OSError as e:
                logging.warning(f"Não foi possível abrir lenovovantage via protocolo: {e}")
            logging.info(
                "Se nenhum programa abrir, a ferramenta de atualização da Lenovo deve ser instalada previamente."
            )
            logging.info(f"(Caminhos do System Update verificados: {tvsu_possible_paths})")
    else:
        logging.info("Nenhuma ferramenta de atualização dedicada encontrada para este fabricante.")
    logging.info("-" * 35)


def open_windows_update():
    """Abre a página do Windows Update nas configurações."""
    logging.info("Abrindo o Windows Update...")
    try:
        os.startfile("ms-settings:windowsupdate-action")
    except OSError as e:
        logging.error(f"Erro ao abrir Windows Update: {e}")
    logging.info("-" * 35)
