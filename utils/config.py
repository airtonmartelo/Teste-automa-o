TEST_CATEGORIES = [
    {
        "category": "Sistema Operacional",
        "icon": "💻",
        "items": [
            {"key": "os_installed", "name": "Windows instalado corretamente"},
            {"key": "os_activated", "name": "Windows ativado"},
            {"key": "drivers_installed", "name": "Drivers instalados"},
            {"key": "no_device_manager_errors", "name": "Sem erros no Gerenciador de Dispositivos"},
        ],
    },
    {
        "category": "Atualizações",
        "icon": "🔄",
        "items": [
            {"key": "updates_windows", "name": "Windows Update concluído"},
            {"key": "updates_lenovo", "name": "Lenovo Update executado (quando aplicável)"},
            {"key": "updates_dell", "name": "Dell Command Update executado (quando aplicável)"},
            {"key": "updates_bios", "name": "BIOS/Firmware atualizados (quando aplicável)"},
        ],
    },
    {
        "category": "Tela e Vídeo",
        "icon": "📺",
        "items": [
            {"key": "display_working", "name": "Tela funcionando corretamente"},
            {"key": "display_brightness", "name": "Controle de brilho operacional"},
            {"key": "display_resolution", "name": "Resolução configurada corretamente"},
            {"key": "display_hdmi", "name": "Saída HDMI testada"},
            {"key": "display_video_playback", "name": "Reprodução de vídeo testada"},
        ],
    },
    {
        "category": "Teclado",
        "icon": "⌨",
        "items": [
            {"key": "keyboard_all_keys", "name": "Todas as teclas testadas"},
            {"key": "keyboard_fn_keys", "name": "Teclas de função (FN) funcionando"},
            {"key": "keyboard_caps_lock", "name": "Caps Lock funcionando"},
            {"key": "keyboard_brightness_keys", "name": "Ajuste de brilho via teclado funcionando"},
            {"key": "keyboard_volume_keys", "name": "Ajuste de volume via teclado funcionando"},
        ],
    },
    {
        "category": "Touchpad",
        "icon": "👆",
        "items": [
            {"key": "touchpad_working", "name": "Touchpad funcionando"},
            {"key": "touchpad_left_click", "name": "Clique esquerdo funcionando"},
            {"key": "touchpad_right_click", "name": "Clique direito funcionando"},
            {"key": "touchpad_scroll", "name": "Rolagem (scroll) funcionando"},
        ],
    },
    {
        "category": "Áudio e Multimídia",
        "icon": "🔊",
        "items": [
            {"key": "audio_speakers", "name": "Alto-falantes funcionando"},
            {"key": "audio_mic", "name": "Microfone funcionando"},
            {"key": "audio_webcam", "name": "Webcam funcionando"},
            {"key": "audio_headset", "name": "Entrada para headset/fone funcionando (quando aplicável)"},
        ],
    },
    {
        "category": "Conectividade",
        "icon": "📶",
        "items": [
            {"key": "conn_wifi", "name": "Wi-Fi funcionando"},
            {"key": "conn_bluetooth", "name": "Bluetooth funcionando"},
            {"key": "conn_lan", "name": "Rede cabeada funcionando (quando aplicável)"},
        ],
    },
    {
        "category": "Portas e Interfaces",
        "icon": "🔌",
        "items": [
            {"key": "ports_usb_left", "name": "USB esquerda testada"},
            {"key": "ports_usb_right", "name": "USB direita testada"},
            {"key": "ports_usbc", "name": "USB-C testada (quando aplicável)"},
            {"key": "ports_sd_card", "name": "Leitor de cartão SD testado (quando aplicável)"},
        ],
    },
    {
        "category": "Energia e Bateria",
        "icon": "🔋",
        "items": [
            {"key": "power_adapter_working", "name": "Fonte/carregador funcionando"},
            {"key": "power_connector_ok", "name": "Conector de energia sem mau contato"},
            {"key": "power_charging_ok", "name": "Equipamento carregando corretamente"},
            {"key": "battery_recognized", "name": "Bateria reconhecida pelo sistema"},
            {"key": "battery_charging_ok", "name": "Bateria carregando normalmente"},
        ],
    },
    {
        "category": "Inspeção Física",
        "icon": "🔍",
        "items": [
            {"key": "phys_chassis_ok", "name": "Carcaça sem danos relevantes"},
            {"key": "phys_hinges_ok", "name": "Dobradiças em bom estado"},
            {"key": "phys_lid_ok", "name": "Tampa abrindo e fechando corretamente"},
            {"key": "phys_screws_ok", "name": "Parafusos presentes e fixados"},
            {"key": "phys_adapter_ok", "name": "Fonte em bom estado físico"},
        ],
    },
    {
        "category": "Testes Gerais",
        "icon": "🧪",
        "items": [
            {"key": "general_reboot_ok", "name": "Equipamento reinicia corretamente"},
            {"key": "general_shutdown_ok", "name": "Equipamento desliga corretamente"},
            {"key": "general_sleep_ok", "name": "Suspensão funcionando"},
            {"key": "general_resume_ok", "name": "Retorno da suspensão funcionando"},
            {"key": "general_stability_ok", "name": "Sem travamentos durante os testes"},
        ],
    },
    {
        "category": "Testes de Stress",
        "icon": "🔥",
        "items": [
            {"key": "stress_cpu_ok", "name": "Teste de stress da CPU"},
            {"key": "stress_disk_ok", "name": "Verificação de saúde do disco (S.M.A.R.T.)"},
            {"key": "stress_screen_ok", "name": "Teste de cores da tela"},
        ],
    },
    {
        "category": "Softwares Corporativos",
        "icon": "📦",
        "items": [
            {"key": "sw_browser_ok", "name": "Navegador instalado"},
            {"key": "sw_office_ok", "name": "Pacote Office instalado (quando aplicável)"},
            {"key": "sw_teams_ok", "name": "Teams instalado (quando aplicável)"},
            {"key": "sw_remote_access_ok", "name": "Ferramenta de acesso remoto instalada"},
            {"key": "sw_vpn_ok", "name": "VPN instalada (quando aplicável)"},
            {"key": "sw_printers_ok", "name": "Impressoras configuradas (quando aplicável)"},
        ],
    },
]

# Layout ABNT2 para o teste de teclado
KEYBOARD_LAYOUT = [
    ["Esc", "F1", "F2", "F3", "F4", "F5", "F6", "F7", "F8", "F9", "F10", "F11", "F12", "PrtSc", "Del"],
    ["'", "1", "2", "3", "4", "5", "6", "7", "8", "9", "0", "-", "=", "Backspace"],
    ["Tab", "Q", "W", "E", "R", "T", "Y", "U", "I", "O", "P", "["],
    ["Caps Lock", "A", "S", "D", "F", "G", "H", "J", "K", "L", "Ç", "]", "Enter"],
    ["Shift", "\\", "Z", "X", "C", "V", "B", "N", "M", ",", ".", ";", "/", "Shift"],
    ["Ctrl", "Win", "Alt", "Space", "AltGr", "Menu", "Ctrl", "Left", "Up", "Down", "Right"],
]

# Mapeamento de keysym do Tkinter para o texto do botão
KEYSYM_TO_BUTTON_TEXT = {
    "Return": "Enter",
    "BackSpace": "Backspace",
    "space": "Space",
    "Escape": "Esc",
    "Control_L": "Ctrl",
    "Control_R": "Ctrl",
    "Shift_L": "Shift",
    "Shift_R": "Shift",
    "Alt_L": "Alt",
    "ISO_Level3_Shift": "AltGr",
    "Alt_R": "AltGr",  # AltGr pode ser um dos dois
    "Caps_Lock": "Caps Lock",
    "Tab": "Tab",
    "Up": "Up",
    "Down": "Down",
    "Left": "Left",
    "Right": "Right",
    "Delete": "Del",
    "Print": "PrtSc",
    "Super_L": "Win",
    "Super_R": "Win",
    "Menu": "Menu",
    "minus": "-",
    "equal": "=",
    "bracketleft": "[",
    "bracketright": "]",
    "backslash": "\\",
    "semicolon": ";",
    "apostrophe": "'",
    "comma": ",",
    "period": ".",
    "slash": "/",
    # ABNT2 specific keysyms and their corresponding button text
    "ccedilla": "Ç",
    "Ccedilla": "Ç",  # For the Ç key
    "udiaeresis": "¨",  # For Shift + acute
    "question": "?",  # For Shift + slash
    "numbersign": "#",  # For Shift + 3
    "dollar": "$",  # For Shift + 4
    "percent": "%",  # For Shift + 5
    "ampersand": "&",  # For Shift + 7
    "asterisk": "*",  # For Shift + 8
    "parenleft": "(",  # For Shift + 9
    "parenright": ")",  # For Shift + 0
    "underscore": "_",  # For Shift + minus
    "plus": "+",  # For Shift + equal
    "exclam": "!",  # For Shift + 1
    "at": "@",  # For Shift + 2
    "section": "§",  # For Shift + apostrophe
    "degree": "°",  # For Shift + tilde
    "less": "<",  # For Shift + comma
    "greater": ">",  # For Shift + period
    "quotedbl": '"',  # For Shift + apostrophe (if it's not section)
    "braceright": "}",  # For AltGr + ]
    "braceleft": "{",  # For AltGr + [
    "bar": "|",  # For AltGr + backslash
    "EuroSign": "€",  # For AltGr + E
    "cent": "¢",  # For AltGr + C
    "mu": "µ",  # For AltGr + M
    "ordfeminine": "ª",  # For AltGr + º
    "ordmasculine": "º",  # For AltGr + ª
    "twosuperior": "²",  # For AltGr + 2
    "threesuperior": "³",  # For AltGr + 3
    "onequarter": "¼",  # For AltGr + 5
    "onehalf": "½",  # For AltGr + 6
    "threequarters": "¾",  # For AltGr + 7
}
