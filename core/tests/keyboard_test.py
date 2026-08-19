import customtkinter as ctk
from .basetest import BaseTest
from utils import config


class KeyboardTest(BaseTest):
    """Teste interativo para o teclado físico e touchpad."""

    def __init__(self, app_instance):
        super().__init__(app_instance, "Teste de Teclado e Touchpad")
        self.keyboard_buttons = {}
        self.touchpad_buttons = {}
        self.log_textbox = None

    def _setup_dialog_widgets(self):
        """Configura a interface gráfica da janela de teste de teclado."""
        self.dialog.geometry("800x600")  # Increased height for log

        ctk.CTkLabel(
            self.dialog, text="Teste de Teclado e Touchpad", font=ctk.CTkFont(size=16, weight="bold")
        ).pack(pady=10)
        ctk.CTkLabel(
            self.dialog, text="Pressione as teclas ou clique com o touchpad para ver os botões acenderem."
        ).pack(pady=5)

        keyboard_frame = ctk.CTkFrame(self.dialog)
        keyboard_frame.pack(pady=5, padx=10)

        self._create_virtual_keyboard(keyboard_frame)

        # --- Touchpad Test ---
        touchpad_frame = ctk.CTkFrame(self.dialog, fg_color="transparent")
        touchpad_frame.pack(pady=10)

        left_click_btn = ctk.CTkButton(touchpad_frame, text="Clique Esquerdo", width=150, height=30)
        left_click_btn.pack(side="left", padx=10)
        self.touchpad_buttons["left"] = left_click_btn

        right_click_btn = ctk.CTkButton(touchpad_frame, text="Clique Direito", width=150, height=30)
        right_click_btn.pack(side="left", padx=10)
        self.touchpad_buttons["right"] = right_click_btn

        reset_button = ctk.CTkButton(self.dialog, text="Resetar Cores", command=self._reset_colors)
        reset_button.pack(pady=(0, 10))

        # --- Mini Log ---
        log_frame = ctk.CTkFrame(self.dialog)
        log_frame.pack(pady=10, padx=10, fill="x", expand=True)
        ctk.CTkLabel(log_frame, text="Log de Eventos de Tecla").pack()
        self.log_textbox = ctk.CTkTextbox(log_frame, height=100)
        self.log_textbox.pack(fill="x", expand=True, padx=5, pady=5)
        self.log_textbox.configure(state="disabled")  # Make it read-only for the user

        self.dialog.bind("<KeyPress>", self._on_key_press)
        self.dialog.bind("<Button-1>", self._on_left_click)
        self.dialog.bind("<Button-3>", self._on_right_click)

        self.dialog.focus_force()

    def cleanup(self):
        """Desvincula os eventos antes de fechar."""
        if self.dialog:
            self.dialog.unbind("<KeyPress>")
            self.dialog.unbind("<Button-1>")
            self.dialog.unbind("<Button-3>")
        super().cleanup()
        self.keyboard_buttons = {}
        self.touchpad_buttons = {}

    def _reset_colors(self):
        """Reseta a cor de todos os botões do teclado e touchpad para o padrão."""
        default_color = ctk.ThemeManager.theme["CTkButton"]["fg_color"]
        # Reset keyboard
        for item in self.keyboard_buttons.values():
            if isinstance(item, list):
                for button in item:
                    button.configure(fg_color=default_color)
            else:
                item.configure(fg_color=default_color)

        # Reset touchpad
        for button in self.touchpad_buttons.values():
            button.configure(fg_color=default_color)

    def _create_virtual_keyboard(self, parent_frame):
        """Cria os botões do teclado virtual com base no layout definido em config."""
        for row in config.KEYBOARD_LAYOUT:
            row_frame = ctk.CTkFrame(parent_frame, fg_color="transparent")
            row_frame.pack(pady=2, fill="x", expand=True)

            for key_text in row:
                width = 40
                if key_text in ["Backspace", "Tab", "Caps Lock", "Enter", "Shift", "Space"]:
                    width = 80 if key_text != "Space" else 200

                button = ctk.CTkButton(row_frame, text=key_text, width=width, height=30)
                button.pack(side="left", padx=2, pady=2)

                key_lower = key_text.lower()
                self.keyboard_buttons.setdefault(key_lower, []).append(button)

        # Converte entradas de lista com um único item em um item direto para simplificar o acesso
        for key, value in self.keyboard_buttons.items():
            if len(value) == 1:
                self.keyboard_buttons[key] = value[0]

    def _on_key_press(self, event):
        """Callback para o evento de pressionar tecla. Acende o botão correspondente e registra no log."""
        keysym = event.keysym

        # Log the key press event
        if self.log_textbox:
            self.log_textbox.configure(state="normal")
            self.log_textbox.insert(ctk.END, f"Tecla pressionada: keysym='{keysym}'\n")
            self.log_textbox.see(ctk.END)
            self.log_textbox.configure(state="disabled")

        button_text = config.KEYSYM_TO_BUTTON_TEXT.get(keysym, keysym).lower()

        if button_text in self.keyboard_buttons:
            target_button = None
            buttons = self.keyboard_buttons[button_text]

            if isinstance(buttons, list):
                if keysym.endswith("_L"):
                    target_button = buttons[0]
                elif keysym.endswith("_R"):
                    target_button = buttons[1]
                else:
                    target_button = buttons[0]
            else:
                target_button = buttons

            if target_button:
                # Idealmente, esta cor de 'sucesso' viria do arquivo de tema.
                # Usando um valor fixo por enquanto.
                target_button.configure(fg_color="#2FA572")

    def _on_left_click(self, event):
        """Callback para o clique esquerdo do mouse/touchpad."""
        if "left" in self.touchpad_buttons:
            self.touchpad_buttons["left"].configure(fg_color="#2FA572")

    def _on_right_click(self, event):
        """Callback para o clique direito do mouse/touchpad."""
        if "right" in self.touchpad_buttons:
            self.touchpad_buttons["right"].configure(fg_color="#2FA572")
