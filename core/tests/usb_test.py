import customtkinter as ctk
import logging
import threading
import pythoncom
from functools import wraps
from .basetest import BaseTest


def _wmi_thread_safe(func):
    """Decorator para garantir a inicialização/desinicialização do COM em threads WMI."""

    @wraps(func)
    def wrapper(self, *args, **kwargs):
        if not self.wmi_available:
            return kwargs.get("default_return", None)
        try:
            pythoncom.CoInitialize()
            import wmi

            wmi_instance = wmi.WMI()
            return func(self, wmi_instance, *args, **kwargs)
        except Exception as e:
            logging.error(f"Erro durante a operação WMI em {func.__name__}: {e}")
            return kwargs.get("default_return", None)
        finally:
            pythoncom.CoUninitialize()

    return wrapper


class USBTest(BaseTest):
    """Teste de monitoramento de conexão de dispositivos USB via WMI."""

    def __init__(self, app_instance):
        super().__init__(app_instance, "Teste de Portas USB")
        self.scroll_frame = None
        self.previous_devices_state = set()
        self.usb_counter = 0
        self.wmi_available = False
        self.periodic_check_running = False
        self.check_interval_ms = 1500
        self.status_label = None

    @_wmi_thread_safe
    def _get_connected_usb_devices(self, wmi_instance, default_return=set()):
        """Retorna um set de DeviceIDs de entidades PnP conectadas via USB."""
        # Filtra por dispositivos no barramento USB ('USB\\') com Vendor ID ('VID_')
        # para selecionar hardware real e ignorar hubs de software ou dispositivos virtuais.
        return {
            device.DeviceID
            for device in wmi_instance.Win32_PnPEntity()
            if device.DeviceID and device.DeviceID.startswith("USB\\") and "VID_" in device.DeviceID
        }

    @_wmi_thread_safe
    def _get_device_name(self, wmi_instance, device_id, default_return="Dispositivo USB"):
        """Obtém um nome amigável para um dispositivo a partir do seu DeviceID."""
        devices = wmi_instance.Win32_PnPEntity(DeviceID=device_id)
        if devices:
            return devices[0].Caption or devices[0].Description or "Dispositivo USB"
        return "Dispositivo USB Desconhecido"

    def _setup_dialog_widgets(self):
        self.dialog.geometry("450x350")
        ctk.CTkLabel(self.dialog, text="Teste de Portas USB", font=ctk.CTkFont(size=16, weight="bold")).pack(
            pady=10
        )
        ctk.CTkLabel(
            self.dialog, text="Insira um dispositivo USB em cada porta.\nO monitoramento é automático."
        ).pack(pady=5)

        ctk.CTkLabel(self.dialog, text="Dispositivos detectados aparecerão abaixo:").pack(pady=5)

        self.scroll_frame = ctk.CTkScrollableFrame(self.dialog, label_text="Log de Detecção")
        self.scroll_frame.pack(pady=10, padx=10, fill="both", expand=True)

        self.status_label = ctk.CTkLabel(
            self.scroll_frame, text="Inicializando, aguarde...", text_color="gray"
        )
        self.status_label.pack(anchor="w")

        threading.Thread(target=self._initialize_usb_scan, daemon=True).start()

    def _initialize_usb_scan(self):
        """Realiza a varredura inicial de dispositivos em uma thread para não bloquear a UI."""
        try:
            import wmi

            self.wmi_available = True

            logging.info("Aguardando estabilização dos dispositivos USB internos (3 segundos)...")
            if self.stop_event.wait(timeout=3):
                logging.info("Teste de USB cancelado durante a inicialização.")
                return

            logging.info("Realizando varredura de linha de base dos dispositivos USB...")
            initial_devices = self._get_connected_usb_devices()
            self.previous_devices_state = initial_devices

            def update_ui_on_success():
                if not self.dialog or not self.dialog.winfo_exists():
                    return
                self.status_label.configure(text="Monitorando portas USB. Conecte um dispositivo.")
                self._start_periodic_usb_check()
                logging.info(
                    f"Inicialização concluída. {len(initial_devices)} dispositivos USB existentes foram registrados como linha de base."
                )

            self.app._update_gui_after_thread(update_ui_on_success)

        except ImportError:
            self.wmi_available = False
            error_msg = "A biblioteca 'WMI' não está instalada.\nInstale com: pip install WMI"
            logging.error(error_msg.replace("\n", " "))

            def update_ui_on_import_error():
                if not self.dialog:
                    return
                self.status_label.configure(text=error_msg, text_color="red")

            self.app._update_gui_after_thread(update_ui_on_import_error)

        except Exception as e:
            self.wmi_available = False
            error_msg = f"Falha ao inicializar o monitoramento WMI: {e}"
            logging.error(error_msg)

            def update_ui_on_general_error():
                if not self.dialog:
                    return
                self.status_label.configure(text=error_msg, text_color="red", wraplength=380)

            self.app._update_gui_after_thread(update_ui_on_general_error)

    def _start_periodic_usb_check(self):
        if not self.wmi_available:
            logging.warning("Não é possível iniciar a verificação periódica: WMI não disponível.")
            return
        if self.periodic_check_running:
            return

        self.periodic_check_running = True
        logging.info(
            f"Iniciando monitoramento periódico de USB a cada {self.check_interval_ms / 1000} segundos."
        )
        self._schedule_next_check()

    def _schedule_next_check(self):
        """Agenda a próxima verificação de USB na thread da UI."""
        if (
            self.periodic_check_running
            and self.dialog
            and self.dialog.winfo_exists()
            and not self.stop_event.is_set()
        ):
            self.app.after(self.check_interval_ms, self._run_periodic_check_in_thread)

    def _run_periodic_check_in_thread(self):
        if (
            self.periodic_check_running
            and self.dialog
            and self.dialog.winfo_exists()
            and not self.stop_event.is_set()
        ):
            threading.Thread(target=self._perform_wmi_check_and_update_ui, daemon=True).start()

    def _perform_wmi_check_and_update_ui(self):
        """Executa a consulta WMI em uma thread de trabalho e agenda a atualização da UI."""
        if not self.wmi_available or not self.periodic_check_running or self.stop_event.is_set():
            return

        results = {"new_devices": [], "error": None}
        try:
            current_devices = self._get_connected_usb_devices()
            newly_detected = current_devices - self.previous_devices_state

            for device_id in newly_detected:
                device_name = self._get_device_name(device_id)
                results["new_devices"].append({"id": device_id, "name": device_name})

            self.previous_devices_state = current_devices

        except Exception as e:
            results["error"] = e

        self.app._update_gui_after_thread(self._process_check_results, results)

    def _process_check_results(self, results):
        """Processa os resultados da verificação na thread da UI e agenda a próxima."""
        if not self.dialog or not self.dialog.winfo_exists():
            return

        if results["error"]:
            logging.warning(f"Erro na verificação de dispositivos USB: {results['error']}")

        if results["new_devices"]:
            success_color = "#2FA572"
            for device in results["new_devices"]:
                self.usb_counter += 1
                device_name = device["name"]
                device_id = device["id"]
                logging.info(f"Novo dispositivo USB detectado: {device_name} (ID: {device_id})")
                text = f"USB {self.usb_counter} OK - Detectado: {device_name}"
                ctk.CTkLabel(
                    self.scroll_frame, text=text, text_color=success_color, font=ctk.CTkFont(weight="bold")
                ).pack(anchor="w")

        if self.periodic_check_running and not self.stop_event.is_set():
            self._schedule_next_check()

    def cleanup(self):
        """Limpa recursos e para o monitoramento ao fechar o diálogo."""
        self.periodic_check_running = False
        super().cleanup()
