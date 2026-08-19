import os
import threading
import time
import wave
from datetime import datetime
from pathlib import Path
import pyaudio
import logging
from PIL import Image
import webbrowser
import json
import customtkinter as ctk
import tkinter
from tkinter import messagebox

# Importa dos novos módulos
from utils import constants, paths, config
from core import hardware, tasks, reporting
from core.tests.usb_test import USBTest
from core.tests.webcam_test import WebcamTest
from core.tests.keyboard_test import KeyboardTest
from core.tests.stress_test import StressTest


class LogHandler(logging.Handler):
    """Handler de logging para atualizar a GUI de forma thread-safe."""

    def __init__(self, app_instance):
        super().__init__()
        self.app = app_instance

    def emit(self, record):
        msg = self.format(record)
        # self.app pode ser None durante o desligamento.
        if self.app:
            self.app._update_gui_after_thread(self.update_gui, msg)
            pass

    def update_gui(self, msg):
        if not self.app or not self.app.winfo_exists():
            return
        if hasattr(self.app, "log_ticker_label"):
            self.app.log_ticker_label.configure(text=msg)

        if hasattr(self.app, "log_window") and self.app.log_window.winfo_exists():
            self.app.log_window.add_log_message(msg)


class LogWindow(ctk.CTkToplevel):
    """Janela para exibir o histórico de logs completo."""

    def __init__(self, parent):
        super().__init__(parent)
        self.title("Histórico de Logs")
        self.geometry("900x600")

        self.log_textbox = ctk.CTkTextbox(self, wrap="word", state="disabled")
        self.log_textbox.pack(expand=True, fill="both", padx=10, pady=10)
        self.protocol("WM_DELETE_WINDOW", self.withdraw)

    def add_log_message(self, msg: str):
        self.log_textbox.configure(state="normal")
        self.log_textbox.insert(tkinter.END, msg + chr(10))
        self.log_textbox.see(tkinter.END)
        self.log_textbox.configure(state="disabled")


class Tooltip:
    """
    Cria uma tooltip (dica de ferramenta) que aparece quando o mouse
    passa sobre um widget. A exibição é condicional ao estado do widget.
    """

    def __init__(self, widget, text):
        self.widget = widget
        self.text = text
        self.tooltip_win = None
        self.widget.bind("<Enter>", self.show_tooltip)
        self.widget.bind("<Leave>", self.hide_tooltip)

    def show_tooltip(self, event):
        """Exibe a tooltip se o widget estiver desabilitado."""
        if str(self.widget.cget("state")) == "disabled":
            # Coordenadas para posicionar a tooltip perto do cursor
            x = event.x_root + 15
            y = event.y_root + 10

            self.tooltip_win = ctk.CTkToplevel(self.widget)
            # Remove a barra de título e a borda da janela
            self.tooltip_win.wm_overrideredirect(True)
            self.tooltip_win.wm_geometry(f"+{x}+{y}")

            label = ctk.CTkLabel(
                self.tooltip_win,
                text=self.text,
                fg_color=("#333333", "#444444"),
                text_color="white",
                corner_radius=5,
                padx=8,
                pady=4,
                font=ctk.CTkFont(size=12),
            )
            label.pack()

    def hide_tooltip(self, event):
        """Esconde a tooltip."""
        if self.tooltip_win:
            self.tooltip_win.destroy()
        self.tooltip_win = None


class AutomacaoBancadaApp(ctk.CTk):
    def __init__(self):
        super().__init__()

        self.title(f"{constants.APP_TITLE} v{constants.APP_VERSION}")
        try:
            self.iconbitmap(paths.ICON_PATH)
        except Exception as e:
            logging.warning(f"Não foi possível carregar o ícone da janela: {e}")

        window_width = 1024
        window_height = 780
        screen_width = self.winfo_screenwidth()
        screen_height = self.winfo_screenheight()
        center_x = int(screen_width / 2 - window_width / 2)
        center_y = int(screen_height / 2 - window_height / 2)
        self.geometry(f"{window_width}x{window_height}+{center_x}+{center_y}")
        self.minsize(1024, 768)

        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=1)  # Área de conteúdo principal (para o main_frame)
        self.grid_rowconfigure(1, weight=0)  # Rodapé fixo para ações

        self.hardware_info = {}
        self.audio = pyaudio.PyAudio()
        self.stream_lock = threading.Lock()
        self.test_widgets = {}
        self.active_test_windows = []
        self.checklist_cards = []
        self.checklist_scroll_view = None
        self.checklist_max_view = None
        self.speaker_test_playing = False
        self.speaker_test_stream = None
        self.speaker_test_stop_event = threading.Event()
        self.microphone_is_recording = False
        self.microphone_is_playing = False
        self.microphone_frames = []
        self.microphone_stream = None
        self.microphone_playback_frame_index = 0
        self.microphone_stop_event = threading.Event()
        self.is_fully_initialized = False
        self.is_checklist_maximized = False

        self.log_window = LogWindow(self)
        self.log_window.withdraw()

        log_handler = LogHandler(self)
        log_handler.setFormatter(
            logging.Formatter("%(asctime)s - %(levelname)s - %(message)s", datefmt="%H:%M:%S")
        )
        logging.getLogger().addHandler(log_handler)
        logging.getLogger().setLevel(logging.INFO)

        # O frame principal agora é um CTkFrame normal para evitar a rolagem global.
        # A rolagem será contida exclusivamente dentro do checklist.
        self.main_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.main_frame.grid(row=0, column=0, padx=10, pady=(10, 0), sticky="nsew")
        self.main_frame.grid_columnconfigure(0, weight=1)
        # Configura as linhas para que os containers se ajustem, com o checklist (linha 3) expandindo.
        self.main_frame.grid_rowconfigure(0, weight=0)  # Header
        self.main_frame.grid_rowconfigure(1, weight=0)  # Top Container (Hardware + Import)
        self.main_frame.grid_rowconfigure(2, weight=0)  # Tools Container
        self.main_frame.grid_rowconfigure(3, weight=1)  # Checklist (Reporting Container)

        self._check_wifi_config()

        self.header_frame = ctk.CTkFrame(self.main_frame, fg_color="transparent")
        self.header_frame.grid(row=0, column=0, padx=15, pady=10, sticky="ew")
        self.header_frame.grid_columnconfigure(0, weight=1)
        self.header_frame.grid_columnconfigure(1, weight=0)

        log_ticker_frame = ctk.CTkFrame(self.header_frame, fg_color="transparent")
        log_ticker_frame.grid(row=0, column=0, sticky="ew", padx=(0, 20))

        self.log_ticker_label = ctk.CTkLabel(
            log_ticker_frame,
            text="Bem-vindo! O log de atividades aparecerá aqui.",
            font=ctk.CTkFont(size=11),
            text_color="#A0A0A0",
            anchor="w",
        )
        self.log_ticker_label.pack(side="left", fill="x", expand=True, padx=(0, 10))
        log_button = ctk.CTkButton(
            log_ticker_frame, text="📜 Logs", width=60, height=24, command=self.show_log_window
        )
        log_button.pack(side="left")

        try:
            logo_white_pil = Image.open(paths.LOGO_WHITE_PATH)
            logo_dark_pil = (
                Image.open(paths.LOGO_DARK_PATH) if paths.LOGO_DARK_PATH.exists() else logo_white_pil
            )
            logo_image = ctk.CTkImage(light_image=logo_dark_pil, dark_image=logo_white_pil, size=(200, 55))
            logo_label = ctk.CTkLabel(self.header_frame, image=logo_image, text="")
            logo_label.grid(row=0, column=1, sticky="e")
        except Exception as e:
            logging.error(f"Não foi possível carregar o logo: {e}")

        self.top_container = ctk.CTkFrame(self.main_frame, fg_color="transparent")
        self.top_container.grid(row=1, column=0, sticky="nsew")
        self.top_container.grid_columnconfigure(0, weight=1, uniform="half_split")
        self.top_container.grid_columnconfigure(1, weight=1, uniform="half_split")

        self.setup_hardware_frame(self.top_container)
        self.setup_import_frame(self.top_container)
        self.setup_tools_frame()
        self.setup_reporting_frame()

        # Os botões de ação final agora ficam em um rodapé fixo, fora da área de rolagem.
        self.final_actions_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.final_actions_frame.grid(row=1, column=0, padx=20, pady=15, sticky="ew")
        self.final_actions_frame.grid_columnconfigure(0, weight=1)
        self.final_actions_frame.grid_columnconfigure(1, weight=0)

        self.report_button = ctk.CTkButton(
            self.final_actions_frame,
            text="Finalizar e Gerar Relatório",
            command=self.generate_report,
            font=ctk.CTkFont(size=12, weight="bold"),
            state="disabled",
        )
        self.report_button.grid(row=0, column=0, padx=(0, 10), sticky="ew")
        Tooltip(self.report_button, "Preencha o campo 'Patrimônio' para habilitar.")

        open_folder_button = ctk.CTkButton(
            self.final_actions_frame, text="📂 Abrir Pasta", command=self.open_reports_folder, width=140
        )
        open_folder_button.grid(row=0, column=1, sticky="e")

        self.protocol("WM_DELETE_WINDOW", self._on_app_closing)
        threading.Thread(target=self.populate_hardware_info, daemon=True).start()

        # Evita o som de 'bell' de validação de entrada durante a inicialização.
        self.after(250, lambda: setattr(self, "is_fully_initialized", True))

    def _check_wifi_config(self):
        """Verifica se a configuração de Wi-Fi existe e loga um aviso se não."""
        wifi_configured = False
        if paths.CONFIG_JSON_PATH.exists():
            try:
                with open(paths.CONFIG_JSON_PATH, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    if data.get("wifi_configured"):
                        wifi_configured = True
            except (json.JSONDecodeError, FileNotFoundError):
                pass  # Se o arquivo estiver corrompido, o log de aviso será acionado.

        if not wifi_configured or not paths.WIFI_XML_PATH.exists():
            logging.warning(
                "AVISO: Configuração de Wi-Fi não encontrada. Execute 'setup_wifi.py' para configurar a conexão."
            )

    def show_log_window(self):
        if self.log_window.state() == "withdrawn":
            self.log_window.deiconify()
        self.log_window.lift()
        self.log_window.focus()

    def _validate_numeric_input(self, P, V):
        """Callback para permitir apenas dígitos em um CTkEntry."""
        is_valid = P == "" or P.isdigit()

        # Toca o som de erro apenas em eventos de digitação ('key').
        if not is_valid and V == "key" and self.is_fully_initialized:
            self.bell()

        return is_valid

    def setup_hardware_frame(self, parent_container):
        hw_frame = ctk.CTkFrame(parent_container)
        hw_frame.grid(row=0, column=0, padx=(10, 5), pady=10, sticky="nsew")
        # Configura o grid com 4 colunas para o novo layout
        hw_frame.grid_columnconfigure(0, weight=0)  # Label Esquerda
        hw_frame.grid_columnconfigure(1, weight=1)  # Input Esquerda
        hw_frame.grid_columnconfigure(2, weight=0)  # Label Direita
        hw_frame.grid_columnconfigure(3, weight=1)  # Input Direita

        ctk.CTkLabel(
            hw_frame, text="Informações do Equipamento", font=ctk.CTkFont(size=14, weight="bold")
        ).grid(row=0, column=0, columnspan=4, pady=(5, 10), sticky="w", padx=10)

        self.hw_labels = {}
        vcmd = (self.register(self._validate_numeric_input), "%P", "%V")

        # Patrimônio em destaque na primeira linha
        ctk.CTkLabel(hw_frame, text="Patrimônio:", anchor="w").grid(
            row=1, column=0, padx=10, pady=2, sticky="w"
        )
        self.patrimonio_entry = ctk.CTkEntry(hw_frame, placeholder_text="Apenas números")
        self.patrimonio_entry.configure(validate="all", validatecommand=vcmd)
        self.patrimonio_entry.grid(row=1, column=1, columnspan=3, padx=(0, 10), pady=2, sticky="ew")
        self.patrimonio_entry.bind("<KeyRelease>", self._on_patrimonio_change)

        # Organização dos demais itens em 2 colunas
        left_items = [
            {"label": "Modelo:", "key": "Modelo"},
            {"label": "Processador:", "key": "Processador"},
            {"label": "Armazenamento:", "key": "Armazenamento"},
        ]
        right_items = [
            {"label": "Fabricante:", "key": "Fabricante"},
            {"label": "Serial:", "key": "Service_Tag_Serial"},
            {"label": "Memória:", "key": "Memoria_RAM"},
        ]

        for i in range(len(left_items)):
            current_row = i + 2  # Começa na linha 2, abaixo do Patrimônio

            # Coluna da Esquerda
            left_item = left_items[i]
            ctk.CTkLabel(hw_frame, text=left_item["label"], anchor="w").grid(
                row=current_row, column=0, padx=10, pady=2, sticky="w"
            )
            left_entry = ctk.CTkEntry(hw_frame, state="readonly", placeholder_text="AGUARDANDO...")
            left_entry.grid(row=current_row, column=1, padx=(0, 10), pady=2, sticky="ew")
            self.hw_labels[left_item["key"]] = left_entry

            # Coluna da Direita
            right_item = right_items[i]
            ctk.CTkLabel(hw_frame, text=right_item["label"], anchor="w").grid(
                row=current_row, column=2, padx=(15, 5), pady=2, sticky="w"
            )
            right_entry = ctk.CTkEntry(hw_frame, state="readonly", placeholder_text="AGUARDANDO...")
            right_entry.grid(row=current_row, column=3, padx=(0, 10), pady=2, sticky="ew")
            self.hw_labels[right_item["key"]] = right_entry

    def setup_import_frame(self, parent_container):
        import_frame = ctk.CTkFrame(parent_container)
        import_frame.grid(row=0, column=1, padx=(5, 10), pady=10, sticky="nsew")
        import_frame.grid_rowconfigure((1, 2, 3), weight=1)
        import_frame.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(import_frame, text="Importação Web", font=ctk.CTkFont(size=14, weight="bold")).grid(
            row=0, column=0, pady=(5, 10), sticky="w", padx=15
        )

        import_rows = [
            {
                "icon": "📥",
                "label": "Importar Relatórios:",
                "btn_text": "Importar para Web (Em breve)",
                "cmd": None,
                "state": "disabled",
            },
            {
                "icon": "📦",
                "label": "Instalador Ninite:",
                "btn_text": "Abrir Site",
                "cmd": lambda: self.safe_open_url("https://ninite.com/"),
                "state": "normal",
            },
            {
                "icon": "📦",
                "label": "Office 365:",
                "btn_text": "Abrir Site",
                "cmd": lambda: self.safe_open_url(
                    "https://www.microsoft.com/pt-br/microsoft-365/download-office"
                ),
                "state": "normal",
            },
        ]

        for i, item in enumerate(import_rows):
            row_frame = ctk.CTkFrame(import_frame, fg_color="transparent")
            row_frame.grid(row=i + 1, column=0, sticky="ew", padx=(10, 15), pady=3)
            row_frame.grid_columnconfigure(0, weight=0)  # Ícone
            row_frame.grid_columnconfigure(1, weight=0)  # Label
            row_frame.grid_columnconfigure(2, weight=1)  # Botão

            ctk.CTkLabel(
                row_frame, text=item["icon"], font=ctk.CTkFont(size=20), width=32, anchor="center"
            ).grid(row=0, column=0, padx=(0, 5), pady=2, sticky="w")
            ctk.CTkLabel(
                row_frame, text=item["label"], width=145, anchor="w", font=ctk.CTkFont(size=12)
            ).grid(row=0, column=1, padx=(0, 10), pady=2, sticky="w")
            ctk.CTkButton(
                row_frame,
                text=item["btn_text"],
                command=item["cmd"],
                state=item["state"],
                height=30,
                font=ctk.CTkFont(size=12, weight="bold"),
            ).grid(row=0, column=2, padx=0, pady=2, sticky="ew")

    def safe_open_url(self, url: str):
        """Abre URLs externas validando estritamente os esquemas permitidos (HTTP/HTTPS)."""
        if url and (url.startswith("https://") or url.startswith("http://")):
            try:
                webbrowser.open(url)
            except Exception as e:
                logging.error(f"Falha ao abrir navegador para URL '{url}': {e}")
        else:
            logging.warning(f"Tentativa de abrir URL não permitida ou inválida: {url}")

    def _update_readonly_entry(self, entry_widget, new_text):
        """Helper para atualizar o texto de um CTkEntry 'readonly'."""
        entry_widget.configure(state="normal")
        entry_widget.delete(0, "end")
        entry_widget.insert(0, new_text)
        entry_widget.configure(state="readonly")

    def populate_hardware_info(self):
        self.hardware_info = hardware.get_hardware_info()
        logging.info("Dados de hardware coletados com sucesso.")

        self._update_gui_after_thread(
            self._update_readonly_entry, self.hw_labels["Modelo"], self.hardware_info.get("Modelo", "N/A")
        )
        self._update_gui_after_thread(
            self._update_readonly_entry,
            self.hw_labels["Fabricante"],
            self.hardware_info.get("Fabricante", "N/A"),
        )
        self._update_gui_after_thread(
            self._update_readonly_entry,
            self.hw_labels["Service_Tag_Serial"],
            self.hardware_info.get("Service_Tag_Serial", "N/A"),
        )
        self._update_gui_after_thread(
            self._update_readonly_entry,
            self.hw_labels["Processador"],
            self.hardware_info.get("Processador", "N/A"),
        )
        self._update_gui_after_thread(
            self._update_readonly_entry,
            self.hw_labels["Memoria_RAM"],
            self.hardware_info.get("Memoria_RAM", "N/A"),
        )
        self._update_gui_after_thread(
            self._update_readonly_entry,
            self.hw_labels["Armazenamento"],
            self.hardware_info.get("Armazenamento", "N/A"),
        )

    def add_active_test(self, test_instance):
        self.active_test_windows.append(test_instance)

    def remove_active_test(self, test_instance):
        if test_instance in self.active_test_windows:
            self.active_test_windows.remove(test_instance)

    def setup_tools_frame(self):
        # O container principal das ferramentas agora é transparente e ocupa toda a largura,
        # espelhando a estrutura do 'top_container' para garantir o alinhamento perfeito das colunas.
        self.tools_container = ctk.CTkFrame(self.main_frame, fg_color="transparent")
        self.tools_container.grid(row=2, column=0, pady=10, sticky="ew")
        self.tools_container.grid_columnconfigure(0, weight=1, uniform="half_split")
        self.tools_container.grid_columnconfigure(1, weight=1, uniform="half_split")

        # Card visual unificado
        card_frame = ctk.CTkFrame(self.tools_container)
        card_frame.grid(row=0, column=0, columnspan=2, sticky="nsew", padx=10)
        card_frame.grid_columnconfigure(0, weight=1, uniform="tools_half")
        card_frame.grid_columnconfigure(1, weight=1, uniform="tools_half")

        ctk.CTkLabel(card_frame, text="Ferramentas de Teste", font=ctk.CTkFont(size=14, weight="bold")).grid(
            row=0, column=0, columnspan=2, pady=(8, 12), sticky="w", padx=15
        )

        # Coluna Esquerda: Conectividade & Sistema
        tools_left_frame = ctk.CTkFrame(card_frame, fg_color="transparent")
        tools_left_frame.grid(row=1, column=0, sticky="nsew", padx=(5, 10), pady=(0, 12))
        tools_left_frame.grid_columnconfigure(0, weight=0)  # Ícone
        tools_left_frame.grid_columnconfigure(1, weight=0)  # Label
        tools_left_frame.grid_columnconfigure(2, weight=1)  # Botão de Ação Principal

        # Coluna Direita: Periféricos & Multimídia
        tools_right_frame = ctk.CTkFrame(card_frame, fg_color="transparent")
        tools_right_frame.grid(row=1, column=1, sticky="nsew", padx=(10, 5), pady=(0, 12))
        tools_right_frame.grid_columnconfigure(0, weight=0)  # Ícone
        tools_right_frame.grid_columnconfigure(1, weight=0)  # Label
        tools_right_frame.grid_columnconfigure(2, weight=1)  # Botão de Ação / Painel Duplo
        tools_right_frame.grid_columnconfigure(3, weight=0)  # Botão Site

        tools_left = [
            {
                "icon": "📶",
                "label": "Conexão Wi-Fi",
                "button_text": "Conectar",
                "cmd": lambda: threading.Thread(target=tasks.connect_wifi).start(),
            },
            {
                "icon": "⚙️",
                "label": "Updates Fabricante",
                "button_text": "Verificar",
                "cmd": lambda: threading.Thread(
                    target=tasks.run_vendor_updates, args=(self.hardware_info.get("Fabricante", ""),)
                ).start(),
            },
            {
                "icon": "🔄",
                "label": "Windows Update",
                "button_text": "Abrir",
                "cmd": lambda: threading.Thread(target=tasks.open_windows_update).start(),
            },
            {
                "icon": "🔥",
                "label": "Teste de Stress",
                "button_text": "Iniciar",
                "cmd": self.show_stress_test_dialog,
            },
            {
                "icon": "🔌",
                "label": "Portas USB",
                "button_text": "Monitorar",
                "cmd": self.show_usb_test_dialog,
            },
        ]

        tools_right = [
            {
                "icon": "⌨️",
                "label": "Teclado",
                "button_text": "Teste Interno",
                "cmd": self.show_keyboard_test_dialog,
                "site_url": "https://keyboard-test.space/pt/",
            },
            {
                "icon": "📷",
                "label": "Webcam",
                "button_text": "Teste Interno",
                "cmd": self.show_webcam_test_dialog,
                "site_url": "https://pt.webcamtests.com/",
            },
            {
                "icon": "📺",
                "label": "Teste de Tela",
                "button_text": "Cores / Dead Pixel",
                "cmd": lambda: self.safe_open_url("https://deadpixelcheck.com/"),
                "site_url": "https://www.youtube.com/watch?v=LXb3EKWsInQ",
            },
            {
                "icon": "🎤",
                "label": "Microfone",
                "button_text": "Teste Interno",
                "cmd": None,
                "site_url": "https://pt.mictests.com/",
            },
            {
                "icon": "🔊",
                "label": "Alto-falantes",
                "button_text": "Teste Interno",
                "cmd": None,
                "site_url": "https://www.youtube.com/watch?v=TtPAFtcvRV8",
            },
        ]

        # Renderização simétrica da Coluna Esquerda
        for row, tool in enumerate(tools_left):
            tools_left_frame.grid_rowconfigure(row, weight=1, minsize=38)

            ctk.CTkLabel(
                tools_left_frame, text=tool["icon"], font=ctk.CTkFont(size=20), width=32, anchor="center"
            ).grid(row=row, column=0, padx=(10, 5), pady=4, sticky="w")
            ctk.CTkLabel(
                tools_left_frame, text=tool["label"] + ":", width=145, anchor="w", font=ctk.CTkFont(size=12)
            ).grid(row=row, column=1, padx=(0, 10), pady=4, sticky="w")
            ctk.CTkButton(
                tools_left_frame,
                text=tool["button_text"],
                command=tool["cmd"],
                height=30,
                font=ctk.CTkFont(size=12, weight="bold"),
            ).grid(row=row, column=2, padx=(0, 10), pady=4, sticky="ew")

        # Renderização simétrica da Coluna Direita
        for row, tool in enumerate(tools_right):
            tools_right_frame.grid_rowconfigure(row, weight=1, minsize=38)

            ctk.CTkLabel(
                tools_right_frame, text=tool["icon"], font=ctk.CTkFont(size=20), width=32, anchor="center"
            ).grid(row=row, column=0, padx=(10, 5), pady=4, sticky="w")
            ctk.CTkLabel(
                tools_right_frame, text=tool["label"] + ":", width=145, anchor="w", font=ctk.CTkFont(size=12)
            ).grid(row=row, column=1, padx=(0, 10), pady=4, sticky="w")

            if tool["label"] == "Alto-falantes":
                speaker_frame = ctk.CTkFrame(tools_right_frame, fg_color="transparent", height=30)
                speaker_frame.grid(row=row, column=2, padx=(0, 6), pady=4, sticky="ew")
                speaker_frame.grid_columnconfigure(0, weight=1, uniform="audio_btns")
                speaker_frame.grid_columnconfigure(1, weight=1, uniform="audio_btns")

                play_button = ctk.CTkButton(
                    speaker_frame,
                    text="▶ Play",
                    command=self.start_speaker_test,
                    anchor="center",
                    corner_radius=6,
                    height=30,
                    font=ctk.CTkFont(size=12, weight="bold"),
                )
                play_button.grid(row=0, column=0, padx=(0, 2), sticky="ew")

                stop_button = ctk.CTkButton(
                    speaker_frame,
                    text="■ Stop",
                    command=self.stop_speaker_test,
                    state="disabled",
                    anchor="center",
                    corner_radius=6,
                    height=30,
                    font=ctk.CTkFont(size=12, weight="bold"),
                )
                stop_button.grid(row=0, column=1, padx=(2, 0), sticky="ew")

                self.test_widgets["speaker_play_button"] = play_button
                self.test_widgets["speaker_stop_button"] = stop_button

            elif tool["label"] == "Microfone":
                mic_frame = ctk.CTkFrame(tools_right_frame, fg_color="transparent", height=30)
                mic_frame.grid(row=row, column=2, padx=(0, 6), pady=4, sticky="ew")
                mic_frame.grid_columnconfigure(0, weight=1, uniform="audio_btns")
                mic_frame.grid_columnconfigure(1, weight=1, uniform="audio_btns")

                record_button = ctk.CTkButton(
                    mic_frame,
                    text="⏺ Gravar",
                    command=self.toggle_microphone_recording,
                    anchor="center",
                    corner_radius=6,
                    height=30,
                    font=ctk.CTkFont(size=12, weight="bold"),
                )
                record_button.grid(row=0, column=0, padx=(0, 2), sticky="ew")

                playback_button = ctk.CTkButton(
                    mic_frame,
                    text="▶ Play",
                    command=self.toggle_microphone_playback,
                    state="disabled",
                    anchor="center",
                    corner_radius=6,
                    height=30,
                    font=ctk.CTkFont(size=12, weight="bold"),
                )
                playback_button.grid(row=0, column=1, padx=(2, 0), sticky="ew")

                self.test_widgets["microphone_record_button"] = record_button
                self.test_widgets["microphone_playback_button"] = playback_button

            else:
                ctk.CTkButton(
                    tools_right_frame,
                    text=tool["button_text"],
                    command=tool["cmd"],
                    height=30,
                    font=ctk.CTkFont(size=12, weight="bold"),
                ).grid(row=row, column=2, padx=(0, 6), pady=4, sticky="ew")

            if tool.get("site_url"):
                ctk.CTkButton(
                    tools_right_frame,
                    text="Site",
                    width=52,
                    height=30,
                    font=ctk.CTkFont(size=12, weight="bold"),
                    command=lambda url=tool["site_url"]: self.safe_open_url(url),
                ).grid(row=row, column=3, padx=(0, 10), pady=4, sticky="e")

    def setup_reporting_frame(self):
        self.reporting_container = ctk.CTkFrame(self.main_frame)
        self.reporting_container.grid(row=3, column=0, padx=10, pady=(10, 0), sticky="nsew")
        self.reporting_container.grid_columnconfigure(0, weight=1)
        self.reporting_container.grid_rowconfigure(1, weight=1)

        title_frame = ctk.CTkFrame(self.reporting_container, fg_color="transparent")
        title_frame.grid(row=0, column=0, pady=(5, 10), sticky="ew", padx=10)
        title_frame.grid_columnconfigure(0, weight=1)  # Permite que o label do título expanda

        ctk.CTkLabel(
            title_frame, text="Checklist de Verificação", font=ctk.CTkFont(size=14, weight="bold")
        ).grid(row=0, column=0, sticky="w")

        self.maximize_button = ctk.CTkButton(
            title_frame, text="[  ]", width=30, height=24, command=self.toggle_checklist_maximize
        )
        self.maximize_button.grid(row=0, column=1, sticky="e")

        # Define uma altura inicial para garantir a visibilidade e usa sticky para expandir.
        self.checklist_scroll_view = ctk.CTkScrollableFrame(self.reporting_container, height=200)
        self.checklist_scroll_view.grid(row=1, column=0, padx=10, pady=(0, 10), sticky="nsew")
        self.checklist_scroll_view.grid_columnconfigure(0, weight=1)

        for category_data in config.TEST_CATEGORIES:
            # O master (pai) do card DEVE ser o scroll view para que a rolagem funcione corretamente.
            # A lógica de maximização foi ajustada para não precisar mais mover os cards entre containers.
            card = ctk.CTkFrame(self.checklist_scroll_view)
            card.pack(fill="x", expand=True, padx=5, pady=5)
            self.checklist_cards.append(card)

            header_frame = ctk.CTkFrame(card, fg_color="transparent", cursor="hand2")
            header_frame.pack(fill="x", padx=5, pady=2)

            header_frame.grid_columnconfigure(0, minsize=30, weight=0)
            header_frame.grid_columnconfigure(1, minsize=45, weight=0)
            header_frame.grid_columnconfigure(2, weight=1)
            header_frame.grid_columnconfigure(3, minsize=60, weight=0)

            toggle_icon_label = ctk.CTkLabel(
                header_frame, text="▶", font=ctk.CTkFont(size=14), width=25, anchor="center"
            )
            toggle_icon_label.grid(row=0, column=0, padx=(5, 0), sticky="w")

            category_icon_label = ctk.CTkLabel(
                header_frame,
                text=category_data.get("icon", "❓"),
                font=ctk.CTkFont(size=18),
                width=45,
                anchor="center",
            )
            category_icon_label.grid(row=0, column=1, padx=0, sticky="w")

            title_label = ctk.CTkLabel(
                header_frame,
                text=category_data["category"],
                font=ctk.CTkFont(size=15, weight="bold"),
                anchor="w",
            )
            title_label.grid(row=0, column=2, padx=(10, 0), sticky="ew")

            total_items = len(category_data["items"])
            counter_label = ctk.CTkLabel(
                header_frame, text=f"{total_items}/{total_items}", font=ctk.CTkFont(size=14)
            )
            counter_label.grid(row=0, column=3, padx=(0, 5), sticky="e")

            items_frame = ctk.CTkFrame(card, fg_color="transparent")
            category_info = {"counter_label": counter_label, "status_vars": [], "total_items": total_items}

            def toggle_lambda(event, f=items_frame, i=toggle_icon_label):
                self.toggle_category(f, i)

            header_frame.bind("<Button-1>", toggle_lambda)
            toggle_icon_label.bind("<Button-1>", toggle_lambda)
            category_icon_label.bind("<Button-1>", toggle_lambda)
            title_label.bind("<Button-1>", toggle_lambda)
            counter_label.bind("<Button-1>", toggle_lambda)
            for item in category_data["items"]:
                item_frame = ctk.CTkFrame(items_frame)
                item_frame.pack(fill="x", padx=10, pady=3)
                item_frame.grid_columnconfigure(0, weight=1)
                ctk.CTkLabel(item_frame, text=item["name"]).grid(row=0, column=0, sticky="w")
                status_var = ctk.StringVar(value=constants.STATUS_PASS)
                category_info["status_vars"].append(status_var)
                seg_button = ctk.CTkSegmentedButton(
                    item_frame,
                    values=[constants.STATUS_PASS, constants.STATUS_FAIL, constants.STATUS_NA],
                    variable=status_var,
                )
                seg_button.grid(row=0, column=1, sticky="e")
                details_entry = ctk.CTkEntry(item_frame, placeholder_text="Detalhes da falha...")
                details_entry.grid(row=1, column=0, columnspan=2, sticky="ew", pady=(5, 0))
                details_entry.grid_remove()
                seg_button.configure(
                    command=lambda v, e=details_entry, info=category_info: self._update_category_status(
                        v, e, info
                    )
                )
                self.test_widgets[item["key"]] = {
                    "status_var": status_var,
                    "details_entry": details_entry,
                    "name": item["name"],
                }

    def _update_category_status(self, value, details_entry, category_info):
        if value == constants.STATUS_FAIL:
            details_entry.grid()
            details_entry.focus()
        else:
            details_entry.delete(0, ctk.END)
            details_entry.grid_remove()
        pass_count = sum(1 for var in category_info["status_vars"] if var.get() == constants.STATUS_PASS)
        category_info["counter_label"].configure(text=f'{pass_count}/{category_info["total_items"]}')

    def toggle_category(self, items_frame, toggle_icon_label):
        if items_frame.winfo_viewable():
            items_frame.pack_forget()
            toggle_icon_label.configure(text="▶")
        else:
            items_frame.pack(fill="x", expand=True, padx=10, pady=(0, 10))
            toggle_icon_label.configure(text="▼")

    def toggle_checklist_maximize(self):
        """Maximiza ou restaura a visualização do checklist."""
        self.is_checklist_maximized = not self.is_checklist_maximized

        # Lista de widgets a serem escondidos/mostrados durante a maximização.
        widgets_to_toggle = [
            self.header_frame,
            self.top_container,
            self.tools_container,
            self.final_actions_frame,  # Este está no root, mas .grid()/.grid_remove() funciona igual.
        ]

        if self.is_checklist_maximized:
            logging.info("Maximizando checklist.")
            for widget in widgets_to_toggle:
                widget.grid_remove()
            # Apenas removemos os outros widgets. O layout do grid se encarrega de expandir
            # o reporting_container, que já contém o checklist_scroll_view.
            self.maximize_button.configure(text="><")
        else:
            logging.info("Restaurando layout normal.")
            for widget in widgets_to_toggle:
                widget.grid()
            # Apenas recolocamos os widgets no grid.
            self.maximize_button.configure(text="[  ]")

    def _update_gui_after_thread(self, callback, *args, **kwargs):
        def safe_callback():
            try:
                callback(*args, **kwargs)
            except tkinter.TclError as e:
                if "invalid command name" not in str(e):
                    raise

        self.after(0, safe_callback)

    def _show_test_dialog(self, test_class):
        """Abre uma janela de teste, garantindo que apenas uma instância exista."""
        for test in self.active_test_windows:
            if isinstance(test, test_class):
                if test.dialog and test.dialog.winfo_exists():
                    logging.info(f"A janela '{test.name}' já está aberta. Trazendo para a frente.")
                    test.dialog.lift()
                    test.dialog.focus_force()
                    return

        logging.info(f"Iniciando novo teste: {test_class.__name__}")
        test_instance = test_class(self)
        test_instance.run()

    def show_usb_test_dialog(self):
        self._show_test_dialog(USBTest)

    def show_keyboard_test_dialog(self):
        self._show_test_dialog(KeyboardTest)

    def show_stress_test_dialog(self):
        self._show_test_dialog(StressTest)

    def show_webcam_test_dialog(self):
        self._show_test_dialog(WebcamTest)

    def start_speaker_test(self):
        if self.speaker_test_playing:
            return

        if not str(paths.AUDIO_TEST_PATH).lower().endswith(".wav") or not os.path.exists(
            paths.AUDIO_TEST_PATH
        ):
            logging.error(
                f"Arquivo de áudio de teste (.wav) não encontrado ou inválido: {paths.AUDIO_TEST_PATH}"
            )
            messagebox.showerror("Erro", "Arquivo de áudio de teste (.wav) não encontrado ou inválido.")
            return

        self.speaker_test_playing = True
        self.speaker_test_stop_event.clear()

        self.test_widgets["speaker_play_button"].configure(state="disabled")
        self.test_widgets["speaker_stop_button"].configure(state="normal")

        threading.Thread(target=self._speaker_playback_thread, daemon=True).start()

    def stop_speaker_test(self):
        if not self.speaker_test_playing:
            return

        self.speaker_test_playing = False
        self.speaker_test_stop_event.set()

        if self.test_widgets.get("speaker_play_button"):
            self.test_widgets["speaker_play_button"].configure(state="normal")
            self.test_widgets["speaker_stop_button"].configure(state="disabled")

    def _speaker_playback_thread(self):
        logging.info("Iniciando reprodução do teste de alto-falantes.")
        try:
            with wave.open(str(paths.AUDIO_TEST_PATH), "rb") as wf:
                with self.stream_lock:
                    self.speaker_test_stream = self.audio.open(
                        format=self.audio.get_format_from_width(wf.getsampwidth()),
                        channels=wf.getnchannels(),
                        rate=wf.getframerate(),
                        output=True,
                    )

                data = wf.readframes(constants.CHUNK)
                while data and not self.speaker_test_stop_event.is_set():
                    self.speaker_test_stream.write(data)
                    data = wf.readframes(constants.CHUNK)
        except Exception as e:
            logging.error(f"Falha ao reproduzir áudio .wav: {e}")
        finally:
            with self.stream_lock:
                if self.speaker_test_stream:
                    self.speaker_test_stream.stop_stream()
                    self.speaker_test_stream.close()
                    self.speaker_test_stream = None
            self._update_gui_after_thread(self.stop_speaker_test)
            logging.info("Reprodução do teste de alto-falantes finalizada.")

    def toggle_microphone_recording(self):
        if self.microphone_is_recording:
            self.stop_microphone_recording()
        else:
            self.start_microphone_recording()

    def toggle_microphone_playback(self):
        """Inicia ou para a reprodução da gravação."""
        if self.microphone_is_playing:
            self.stop_microphone_playback()
        else:
            self.start_microphone_playback()

    def start_microphone_recording(self):
        if self.microphone_is_recording:
            return

        self.microphone_frames = []
        self.microphone_is_recording = True
        self.microphone_stop_event.clear()

        self._update_gui_after_thread(self._finalize_microphone_recording_ui, is_recording=True)

        logging.info(f"Iniciando gravação de microfone...")
        threading.Thread(target=self._microphone_record_thread, daemon=True).start()

    def stop_microphone_recording(self):
        if not self.microphone_is_recording:
            return

        self.microphone_is_recording = False
        self.microphone_stop_event.set()
        logging.info("Gravação de microfone concluída.")

    def _microphone_record_callback(self, in_data, frame_count, time_info, status):
        self.microphone_frames.append(in_data)
        if self.microphone_stop_event.is_set():
            return (None, pyaudio.paComplete)
        return (None, pyaudio.paContinue)

    def _microphone_record_thread(self):
        try:
            with self.stream_lock:
                self.microphone_stream = self.audio.open(
                    format=pyaudio.paInt16,
                    channels=constants.CHANNELS,
                    rate=constants.RATE,
                    input=True,
                    frames_per_buffer=constants.CHUNK,
                    stream_callback=self._microphone_record_callback,
                )

            self.microphone_stream.start_stream()
            logging.info("Stream de gravação iniciada (modo callback).")

            start_time = time.time()
            while self.microphone_stream.is_active():
                if time.time() - start_time > constants.RECORD_SECONDS:
                    break
                time.sleep(0.1)

        except Exception as e:
            logging.error(f"Falha ao gravar áudio do microfone: {e}")
            self._update_gui_after_thread(
                lambda: messagebox.showerror("Erro de Microfone", f"Falha ao gravar áudio: {e}")
            )
        finally:
            with self.stream_lock:
                if self.microphone_stream:
                    if self.microphone_stream.is_active():
                        self.microphone_stream.stop_stream()
                    self.microphone_stream.close()
                    self.microphone_stream = None
            self._update_gui_after_thread(self._finalize_microphone_recording_ui, is_recording=False)
            logging.info("Stream de gravação finalizada.")

    def _finalize_microphone_recording_ui(self, is_recording: bool):
        if not self.test_widgets.get("microphone_record_button"):
            return
        if is_recording:
            self.test_widgets["microphone_record_button"].configure(text="■ Parar", fg_color="#D04040")
            self.test_widgets["microphone_playback_button"].configure(state="disabled")
        else:
            self.test_widgets["microphone_record_button"].configure(
                text="⏺ Gravar", fg_color=ctk.ThemeManager.theme["CTkButton"]["fg_color"]
            )
            self.test_widgets["microphone_playback_button"].configure(
                state="normal" if self.microphone_frames else "disabled"
            )

    def start_microphone_playback(self):
        if self.microphone_is_playing:
            return
        if not self.microphone_frames:
            logging.warning("Nenhuma gravação de microfone para reproduzir.")
            return

        self.microphone_is_playing = True
        self.microphone_stop_event.clear()

        self._update_gui_after_thread(self._finalize_microphone_playback_ui, is_playing=True)

        logging.info("Iniciando reprodução da gravação do microfone...")
        threading.Thread(target=self._microphone_playback_thread, daemon=True).start()

    def stop_microphone_playback(self):
        if not self.microphone_is_playing:
            return

        self.microphone_is_playing = False
        self.microphone_stop_event.set()
        logging.info("Reprodução da gravação do microfone concluída.")

    def _microphone_playback_callback(self, in_data, frame_count, time_info, status):
        if self.microphone_stop_event.is_set() or self.microphone_playback_frame_index >= len(
            self.microphone_frames
        ):
            return (None, pyaudio.paComplete)

        data = self.microphone_frames[self.microphone_playback_frame_index]
        self.microphone_playback_frame_index += 1

        return (data, pyaudio.paContinue)

    def _microphone_playback_thread(self):
        self.microphone_playback_frame_index = 0
        try:
            with self.stream_lock:
                self.microphone_stream = self.audio.open(
                    format=pyaudio.paInt16,
                    channels=constants.CHANNELS,
                    rate=constants.RATE,
                    output=True,
                    frames_per_buffer=constants.CHUNK,
                    stream_callback=self._microphone_playback_callback,
                )

            self.microphone_stream.start_stream()
            logging.info("Stream de reprodução iniciada (modo callback).")

            while self.microphone_stream.is_active():
                time.sleep(0.1)

        except Exception as e:
            logging.error(f"Falha ao reproduzir gravação do microfone: {e}")
            self._update_gui_after_thread(
                lambda: messagebox.showerror("Erro de Microfone", f"Falha ao reproduzir áudio: {e}")
            )
        finally:
            with self.stream_lock:
                if self.microphone_stream:
                    if self.microphone_stream.is_active():
                        self.microphone_stream.stop_stream()
                    self.microphone_stream.close()
                    self.microphone_stream = None
            self._update_gui_after_thread(self._finalize_microphone_playback_ui, is_playing=False)
            logging.info("Stream de reprodução finalizada.")

    def _finalize_microphone_playback_ui(self, is_playing: bool):
        if not self.test_widgets.get("microphone_record_button"):
            return
        if is_playing:
            self.test_widgets["microphone_record_button"].configure(state="disabled")
            self.test_widgets["microphone_playback_button"].configure(text="■ Parar", fg_color="#D04040")
        else:
            self.test_widgets["microphone_record_button"].configure(state="normal")
            self.test_widgets["microphone_playback_button"].configure(
                text="▶ Play", fg_color=ctk.ThemeManager.theme["CTkButton"]["fg_color"]
            )

    def _on_app_closing(self):
        for test_instance in list(self.active_test_windows):
            test_instance.cleanup()
        self.stop_microphone_recording()
        self.stop_microphone_playback()
        self.stop_speaker_test()
        if self.audio:
            self.audio.terminate()
        self.destroy()

    def open_reports_folder(self):
        logging.info(f"Abrindo pasta de relatórios: {paths.LOGS_DIR_PATH}")
        try:
            paths.LOGS_DIR_PATH.mkdir(parents=True, exist_ok=True)
            resolved_path = paths.LOGS_DIR_PATH.resolve()
            if resolved_path.is_dir():
                os.startfile(resolved_path)
            else:
                raise NotADirectoryError(f"Caminho não é um diretório válido: {resolved_path}")
        except Exception as e:
            logging.error(f"Falha ao abrir a pasta de relatórios: {e}")
            messagebox.showerror(
                "Erro", f"Não foi possível abrir a pasta de relatórios em:\n{paths.LOGS_DIR_PATH}"
            )

    def generate_report(self):
        """Inicia a geração do relatório em uma thread para não bloquear a UI."""
        self.report_button.configure(state="disabled", text="Gerando relatório...")
        threading.Thread(target=self._generate_report_thread, daemon=True).start()

    def _on_patrimonio_change(self, event=None):
        """Habilita ou desabilita o botão de gerar relatório com base no campo patrimônio."""
        patrimonio_text = self.patrimonio_entry.get().strip()
        if patrimonio_text:
            self.report_button.configure(state="normal")
        else:
            self.report_button.configure(state="disabled")

    def _generate_report_thread(self):
        logging.info("Gerando relatório final...")
        patrimonio = self.patrimonio_entry.get().strip() or "NÃO INFORMADO"
        try:
            report_path = reporting.generate_report_file(
                hardware_info=self.hardware_info,
                patrimonio=patrimonio,
                test_widgets=self.test_widgets,
                test_categories=config.TEST_CATEGORIES,
            )
            if report_path:
                resolved_report = Path(report_path).resolve()
                base_logs = paths.LOGS_DIR_PATH.resolve()
                # Validação de segurança: o arquivo deve estar dentro da pasta de logs e ser .txt
                if (
                    str(resolved_report).startswith(str(base_logs))
                    and resolved_report.is_file()
                    and resolved_report.suffix.lower() == ".txt"
                ):
                    logging.info("Abrindo relatório...")
                    try:
                        os.startfile(resolved_report)
                    except Exception as e:
                        logging.error(f"Falha ao abrir o arquivo de relatório: {e}")
                else:
                    logging.error(f"Arquivo de relatório inválido ou não autorizado: {report_path}")
        except Exception as e:
            logging.error(f"Erro inesperado ao gerar relatório: {e}")
            self._update_gui_after_thread(messagebox.showerror, "Erro", f"Falha ao gerar relatório: {e}")
        finally:
            self._update_gui_after_thread(
                self.report_button.configure, state="normal", text="Finalizar e Gerar Relatório"
            )
