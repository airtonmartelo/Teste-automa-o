import customtkinter as ctk
import threading
import logging


class BaseTest:
    """
    Classe base para todos os testes interativos.
    Gerencia a criação da janela de diálogo, o ciclo de vida e a limpeza de recursos.
    """

    def __init__(self, app_instance, name: str):
        self.app = app_instance
        self.name = name
        self.dialog = None
        self.stop_event = threading.Event()

    def run(self):
        """Cria a janela de diálogo do teste e inicia a lógica do teste."""
        self.dialog = ctk.CTkToplevel(self.app)
        self.dialog.title(self.name)
        # self.dialog.transient(self.app) # Removido para permitir janelas independentes

        # Bring window to foreground and give focus
        self.dialog.lift()
        self.dialog.attributes("-topmost", True)
        self.dialog.after(10, lambda: self.dialog.attributes("-topmost", False))
        self.dialog.focus_force()
        # self.dialog.grab_set() # Removido para permitir interação com outras janelas

        self._setup_dialog_widgets()

        self.dialog.protocol("WM_DELETE_WINDOW", self.cleanup)
        # self.app.wait_window(self.dialog) # Removido para não bloquear a thread principal da UI

        # Adiciona a instância do teste à lista de testes ativos na aplicação principal
        self.app.add_active_test(self)

    def _setup_dialog_widgets(self):
        """Subclasses devem implementar este método para criar a UI específica do teste."""
        raise NotImplementedError

    def cleanup(self):
        """Limpa os recursos (threads, etc.) e destrói a janela de diálogo."""
        logging.info(f"Finalizando teste: {self.name}")
        self.stop_event.set()
        if self.dialog:
            self.dialog.destroy()
            self.dialog = None

        # Remove a instância do teste da lista de testes ativos na aplicação principal
        self.app.remove_active_test(self)
