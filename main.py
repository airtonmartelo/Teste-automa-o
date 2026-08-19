import customtkinter as ctk
from ctypes import windll
import logging
import multiprocessing

# Importa os módulos da nova estrutura
from gui.app import AutomacaoBancadaApp
from utils import paths


def main():
    # Melhora a renderização de fontes no Windows (requer Windows 8.1+)
    try:
        windll.shcore.SetProcessDpiAwareness(1)
    except (AttributeError, TypeError):
        logging.warning("Não foi possível configurar o DPI Awareness (requer Win 8.1+).")

    # Define o ID de aplicativo no Windows para garantir ícone em alta definição na barra de tarefas
    try:
        windll.shell32.SetCurrentProcessExplicitAppUserModelID("pctec.automacao.bancada.v2")
    except Exception:
        pass

    ctk.set_appearance_mode("System")
    try:
        ctk.set_default_color_theme(paths.THEME_PATH)
    except (FileNotFoundError, ValueError):
        logging.error(f"Tema não encontrado em {paths.THEME_PATH}. Usando fallback 'blue'.")
        ctk.set_default_color_theme("blue")  # Fallback para um tema padrão

    app = AutomacaoBancadaApp()
    app.mainloop()


if __name__ == "__main__":
    # Necessário para o correto funcionamento do multiprocessing ao gerar um executável
    multiprocessing.freeze_support()
    main()
