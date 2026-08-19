import customtkinter as ctk
import json
from pathlib import Path
from tkinter import messagebox
from utils import paths  # Import the centralized paths module
import time
import logging  # Import logging module
from xml.sax.saxutils import escape

# --- Constantes e Caminhos ---
# Configure basic logging for this script (INFO level)
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
# --- Template do Perfil XML para Wi-Fi ---
XML_TEMPLATE = """<?xml version="1.0"?>
<WLANProfile xmlns="http://www.microsoft.com/networking/WLAN/profile/v1">
    <name>{ssid}</name>
    <SSIDConfig>
        <SSID>
            <hex>{ssid_hex}</hex>
            <name>{ssid}</name>
        </SSID>
    </SSIDConfig>
    <connectionType>ESS</connectionType>
    <connectionMode>auto</connectionMode>
    <MSM>
        <security>
            <authEncryption>
                <authentication>{authentication}</authentication>
                <encryption>AES</encryption>
                <useOneX>false</useOneX>
            </authEncryption>
            <sharedKey>
                <keyType>passPhrase</keyType>
                <protected>false</protected>
                <keyMaterial>{password}</keyMaterial>
            </sharedKey>
        </security>
    </MSM>
</WLANProfile>
"""


def save_with_retry(filepath, content, encoding="utf-8", retries=5, delay=0.1):
    """
    Tenta salvar um arquivo, com múltiplas tentativas em caso de erro de permissão (PermissionError).
    Isso é útil para lidar com bloqueios temporários de arquivos, como os causados por antivírus.
    """
    last_exception = None
    for i in range(retries):
        try:
            with open(filepath, "w", encoding=encoding) as f:
                f.write(content)
            logging.info(f"Arquivo '{filepath}' salvo com sucesso na tentativa {i+1}.")
            return  # Sucesso, sai da função
        except PermissionError as e:
            last_exception = e
            logging.warning(
                f"Tentativa {i+1}/{retries} falhou ao salvar '{filepath}': {e}. Tentando novamente em {delay}s..."
            )
            time.sleep(delay)
        except Exception as e:
            # Para outros erros inesperados, falha imediatamente
            logging.error(f"Erro inesperado ao salvar '{filepath}': {e}")
            raise e

    logging.error(
        f"Não foi possível salvar o arquivo '{filepath}' após {retries} tentativas devido a erros de permissão."
    )
    if last_exception:
        raise last_exception


class WifiSetupApp(ctk.CTk):
    """Interface gráfica para a configuração inicial do perfil de Wi-Fi."""

    def __init__(self):
        super().__init__()

        self.title("Configurador de Wi-Fi")
        self.geometry("400x290")
        self.resizable(False, False)
        self.grid_columnconfigure(1, weight=1)

        ctk.CTkLabel(self, text="Nome da Rede (SSID):").grid(
            row=0, column=0, padx=20, pady=(20, 5), sticky="w"
        )
        self.ssid_entry = ctk.CTkEntry(self, placeholder_text="Ex: RedeDaBase")
        self.ssid_entry.grid(row=0, column=1, padx=20, pady=(20, 5), sticky="ew")

        ctk.CTkLabel(self, text="Senha:").grid(row=1, column=0, padx=20, pady=5, sticky="w")
        self.password_entry = ctk.CTkEntry(self, placeholder_text="Senha da rede", show="*")
        self.password_entry.grid(row=1, column=1, padx=20, pady=5, sticky="ew")

        self.show_password_var = ctk.BooleanVar(value=False)
        self.show_password_check = ctk.CTkCheckBox(
            self,
            text="Mostrar senha",
            variable=self.show_password_var,
            command=self._toggle_password_visibility,
            font=ctk.CTkFont(size=11),
        )
        self.show_password_check.grid(row=2, column=1, padx=20, pady=(0, 5), sticky="w")

        ctk.CTkLabel(self, text="Tipo de Segurança:").grid(row=3, column=0, padx=20, pady=5, sticky="w")
        self.security_menu = ctk.CTkOptionMenu(self, values=["WPA2PSK", "WPA3SAE"])
        self.security_menu.set("WPA2PSK")
        self.security_menu.grid(row=3, column=1, padx=20, pady=5, sticky="ew")

        save_button = ctk.CTkButton(self, text="Salvar Configuração", command=self.save_configuration)
        save_button.grid(row=4, column=0, columnspan=2, padx=20, pady=(15, 20), sticky="ew")

    def _toggle_password_visibility(self):
        """Alterna a exibição dos caracteres da senha."""
        if self.show_password_var.get():
            self.password_entry.configure(show="")
        else:
            self.password_entry.configure(show="*")

    def save_configuration(self):
        ssid = self.ssid_entry.get().strip()
        password = self.password_entry.get().strip()
        authentication = self.security_menu.get()

        if not ssid or not password:
            messagebox.showerror("Erro", "SSID e Senha são obrigatórios.")
            return

        try:
            # Garante que o diretório de assets exista antes de salvar os arquivos.
            paths.CONFIG_JSON_PATH.parent.mkdir(parents=True, exist_ok=True)

            # Hex encoding do SSID original em UTF-8
            ssid_hex = ssid.encode("utf-8").hex().upper()

            # Escapar caracteres especiais para evitar XML Injection e garantir parsing correto pelo netsh
            safe_ssid = escape(ssid)
            safe_password = escape(password)
            safe_auth = escape(authentication)

            xml_content = XML_TEMPLATE.format(
                ssid=safe_ssid, ssid_hex=ssid_hex, authentication=safe_auth, password=safe_password
            )
            # Usa a função de retry para evitar erros de bloqueio de arquivo
            save_with_retry(paths.WIFI_XML_PATH, xml_content, encoding="utf-8")

            config_data = {"wifi_configured": True, "wifi_ssid": ssid}
            # Usa a função de retry para evitar erros de bloqueio de arquivo
            save_with_retry(paths.CONFIG_JSON_PATH, json.dumps(config_data, indent=4), encoding="utf-8")

            messagebox.showinfo("Sucesso", f"Configuração de Wi-Fi para a rede '{ssid}' salva com sucesso!")
            self.quit()
            self.destroy()

        except Exception as e:
            messagebox.showerror(
                "Erro ao Salvar",
                f"Falha ao salvar a configuração:\n\n{e}\n\nVerifique se o programa não está sendo bloqueado por um antivírus ou se há outra instância dele aberta.",
            )


if __name__ == "__main__":
    ctk.set_appearance_mode("System")
    # Para evitar erros de tema ausente neste script independente,
    # usamos um tema padrão do customtkinter ("blue") que é garantido existir.
    # A aplicação principal (main.py) continuará usando o tema customizado.
    ctk.set_default_color_theme("blue")
    app = WifiSetupApp()
    app.mainloop()
