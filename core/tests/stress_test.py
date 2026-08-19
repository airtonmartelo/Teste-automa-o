import customtkinter as ctk
import threading
import time
import logging
import psutil
import multiprocessing
import pythoncom
from .basetest import BaseTest


def cpu_stress_worker(stop_event):
    """Função que será executada por cada processo para consumir CPU."""
    while not stop_event.is_set():
        # Realiza um cálculo matemático contínuo e computacionalmente intensivo
        # para manter o core da CPU ocupado, garantindo 100% de uso.
        _ = [x * x for x in range(5000)]


class StressTest(BaseTest):
    """Teste para estressar a CPU e monitorar temperatura e frequência."""

    def __init__(self, app_instance):
        super().__init__(app_instance, "Teste de Stress da CPU")
        self.update_thread = None
        self.stress_processes = []
        self.stop_stress_event = multiprocessing.Event()
        self.is_running = False
        self.stress_start_time = 0
        self.max_stress_duration_sec = 300  # Limite máximo de segurança: 5 minutos

    def _setup_dialog_widgets(self):
        self.dialog.geometry("400x300")
        self.dialog.resizable(False, False)

        ctk.CTkLabel(
            self.dialog, text="Teste de Stress da CPU", font=ctk.CTkFont(size=16, weight="bold")
        ).pack(pady=10)

        stats_frame = ctk.CTkFrame(self.dialog, fg_color="transparent")
        stats_frame.pack(pady=10, padx=20, fill="x")
        stats_frame.grid_columnconfigure(1, weight=1)

        self.cpu_usage_label = self._create_stat_label(stats_frame, "Uso da CPU:", 0)
        self.cpu_temp_label = self._create_stat_label(stats_frame, "Temperatura:", 1)
        self.cpu_freq_label = self._create_stat_label(stats_frame, "Frequência Atual:", 2)

        self.toggle_button = ctk.CTkButton(self.dialog, text="Iniciar Teste", command=self.toggle_test)
        self.toggle_button.pack(pady=20, padx=20, fill="x")

        # Inicia a thread de atualização da UI (sem estresse)
        self.update_thread = threading.Thread(target=self._update_stats_thread, daemon=True)
        self.update_thread.start()

    def _create_stat_label(self, parent, text, row):
        ctk.CTkLabel(parent, text=text, anchor="w").grid(row=row, column=0, sticky="w", padx=(0, 10))
        label = ctk.CTkLabel(parent, text="--", anchor="e", font=ctk.CTkFont(weight="bold"))
        label.grid(row=row, column=1, sticky="e")
        return label

    def toggle_test(self):
        if self.is_running:
            self._stop_stress_test()
        else:
            self._start_stress_test()

    def _start_stress_test(self):
        logging.info("Iniciando teste de stress da CPU.")
        self.is_running = True
        self.stress_start_time = time.time()
        self.toggle_button.configure(text="Parar Teste", fg_color="#D04040")
        self.stop_stress_event.clear()

        num_cores = psutil.cpu_count(logical=True) or 2
        self.stress_processes = [
            multiprocessing.Process(target=cpu_stress_worker, args=(self.stop_stress_event,))
            for _ in range(num_cores)
        ]
        for p in self.stress_processes:
            p.start()

    def _stop_stress_test(self):
        if not self.is_running and not self.stress_processes:
            return
        logging.info("Parando teste de stress da CPU.")
        self.is_running = False
        self.toggle_button.configure(
            text="Iniciar Teste", fg_color=ctk.ThemeManager.theme["CTkButton"]["fg_color"]
        )
        self.stop_stress_event.set()

        for p in self.stress_processes:
            try:
                p.join(timeout=0.5)  # Espera um pouco para o processo terminar
                if p.is_alive():
                    p.terminate()  # Força o término se não parar
                    p.join(timeout=0.2)
                    if p.is_alive():
                        p.kill()  # Termina imediatamente se persistir
            except Exception as e:
                logging.warning(f"Erro ao encerrar processo de stress: {e}")
        self.stress_processes = []

    def _get_cpu_temperature_wmi(self):
        """Obtém a temperatura da CPU usando WMI. Tenta múltiplos métodos e retorna 'N/A' em caso de falha."""
        try:
            # É crucial inicializar o COM para cada thread que usa WMI
            pythoncom.CoInitialize()
            import wmi

            # --- Método 1: MSAcpi_ThermalZoneTemperature (comum) ---
            try:
                w = wmi.WMI(namespace="root\\wmi")
                temp_info = w.MSAcpi_ThermalZoneTemperature()
                if temp_info:
                    # A temperatura vem em décimos de Kelvin. Converter para Celsius.
                    temp_celsius = (temp_info[0].CurrentTemperature / 10.0) - 273.15
                    return f"{temp_celsius:.1f}°C"
            except (wmi.x_wmi, IndexError) as e:
                # Loga o erro específico do primeiro método, mas continua para o próximo
                logging.debug(
                    f"WMI (MSAcpi_ThermalZoneTemperature) falhou: {e}. Tentando método alternativo."
                )

            # --- Método 2: Win32_PerfFormattedData... (alternativa) ---
            try:
                w = wmi.WMI(namespace="root\\CIMV2")
                temp_info = w.Win32_PerfFormattedData_Counters_ThermalZoneInformation()
                if temp_info:
                    # A temperatura vem em Kelvin. Converter para Celsius.
                    temp_celsius = temp_info[0].Temperature - 273.15
                    return f"{temp_celsius:.1f}°C"
            except (wmi.x_wmi, IndexError) as e:
                logging.debug(f"WMI (Win32_PerfFormattedData...) falhou: {e}.")

            return "N/A"  # Se todos os métodos falharem
        except ImportError:
            logging.warning(
                "A biblioteca 'WMI' não está instalada. Não é possível obter a temperatura da CPU."
            )
            return "N/A"
        except Exception as e:
            # Captura erro de importação (WMI/pywin32 não instalado) ou erro de COM/WMI.
            logging.warning(f"Não foi possível obter a temperatura da CPU via WMI: {e}")
            return "N/A"
        finally:
            # Garante que o COM seja desinicializado para a thread
            pythoncom.CoUninitialize()

    def _update_stats_thread(self):
        while not self.stop_event.is_set():
            # Verificação do limite máximo de segurança
            if self.is_running and (time.time() - self.stress_start_time > self.max_stress_duration_sec):
                logging.warning(
                    "Limite de segurança de 5 minutos atingido. Finalizando teste de stress automaticamente."
                )
                self.app._update_gui_after_thread(self._stop_stress_test)

            # Uso da CPU
            usage = psutil.cpu_percent(interval=1)
            usage_text = f"{usage:.1f} %"

            # Temperatura
            temp_text = self._get_cpu_temperature_wmi()

            # Frequência
            try:
                freq = psutil.cpu_freq()
                freq_text = f"{freq.current / 1000:.2f} GHz" if freq else "N/A"
            except Exception:
                freq_text = "N/A"

            # Atualiza a GUI na thread principal
            self.app._update_gui_after_thread(self.cpu_usage_label.configure, text=usage_text)
            self.app._update_gui_after_thread(self.cpu_temp_label.configure, text=temp_text)
            self.app._update_gui_after_thread(self.cpu_freq_label.configure, text=freq_text)

    def cleanup(self):
        """Garante que os testes e threads sejam parados ao fechar a janela."""
        if self.is_running:
            self._stop_stress_test()
        super().cleanup()


if __name__ == "__main__":
    # Este bloco é necessário para que multiprocessing funcione corretamente em executáveis.
    multiprocessing.freeze_support()
