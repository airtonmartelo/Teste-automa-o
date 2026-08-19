import customtkinter as ctk
import threading
import cv2
from PIL import Image
import logging
from .basetest import BaseTest


class WebcamTest(BaseTest):
    """Teste para exibir o feed da webcam."""

    def __init__(self, app_instance):
        super().__init__(app_instance, "Teste de Webcam")
        self.webcam_label = None
        self.webcam_capture = None

    def _setup_dialog_widgets(self):
        """Configura a interface gráfica da janela de teste da webcam."""
        self.dialog.geometry("660x520")

        ctk.CTkLabel(self.dialog, text="Teste de Webcam", font=ctk.CTkFont(size=16, weight="bold")).pack(
            pady=10
        )

        self.webcam_label = ctk.CTkLabel(self.dialog, text="Iniciando câmera...")
        self.webcam_label.pack(padx=10, pady=10)

        # Inicia a thread do feed da webcam
        webcam_thread = threading.Thread(target=self._webcam_feed_thread)
        webcam_thread.daemon = True
        webcam_thread.start()

    def _webcam_feed_thread(self):
        """Thread que captura e exibe o feed da webcam."""
        try:
            # Usar cv2.CAP_DSHOW melhora a compatibilidade e velocidade no Windows
            self.webcam_capture = cv2.VideoCapture(0, cv2.CAP_DSHOW)
            if not self.webcam_capture.isOpened():
                logging.error("Não foi possível abrir a webcam.")
                self.app._update_gui_after_thread(
                    self.webcam_label.configure,
                    text="Erro: Webcam não encontrada ou em uso.",
                    text_color="red",
                )
                return

            while not self.stop_event.is_set():
                ret, frame = self.webcam_capture.read()
                if not ret:
                    logging.warning("Não foi possível ler o frame da webcam.")
                    break

                frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                pil_image = Image.fromarray(frame_rgb)
                ctk_image = ctk.CTkImage(
                    light_image=pil_image, dark_image=pil_image, size=(pil_image.width, pil_image.height)
                )
                self.app._update_gui_after_thread(self._update_webcam_label, ctk_image)
        finally:
            if self.webcam_capture:
                self.webcam_capture.release()
                logging.info("Recurso da webcam liberado.")

    def _update_webcam_label(self, ctk_image):
        """Atualiza o label da imagem na thread principal da UI."""
        if self.webcam_label and self.webcam_label.winfo_exists():
            self.webcam_label.configure(image=ctk_image, text="")
