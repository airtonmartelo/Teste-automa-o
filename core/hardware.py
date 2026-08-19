import wmi
import logging
import pythoncom


def get_hardware_info():
    """Coleta informações de hardware usando a biblioteca WMI para melhor performance."""
    logging.info("Coletando dados do equipamento via WMI...")
    pythoncom.CoInitialize()  # Inicializa o COM para esta thread
    try:
        c = wmi.WMI(namespace="root\\cimv2")

        cs = c.Win32_ComputerSystem()[0]
        product = c.Win32_ComputerSystemProduct()[0]
        bios = c.Win32_BIOS()[0]
        cpu = c.Win32_Processor()[0]
        # Soma o tamanho de todos os discos físicos
        disk_size = sum(int(disk.Size) for disk in c.Win32_DiskDrive())

        memoria_ram_bytes = int(cs.TotalPhysicalMemory)

        info = {
            "Fabricante": (cs.Manufacturer or "DESCONHECIDO").strip(),
            "Service_Tag_Serial": (bios.SerialNumber or "DESCONHECIDO").strip(),
            "Modelo": (product.Name or "EQUIPAMENTO_GENERICO").strip(),
            "Processador": (cpu.Name or "DESCONHECIDO").strip(),
            "Memoria_RAM": (
                f"{round(memoria_ram_bytes / (1024**3))} GB" if memoria_ram_bytes else "DESCONHECIDO"
            ),
            "Armazenamento": f"{round(disk_size / (1024**3))} GB" if disk_size else "DESCONHECIDO",
        }
        return info

    except Exception as e:
        logging.error(f"Falha ao coletar dados de hardware via WMI. Erro: {e}")
        logging.warning("Retornando valores padrão.")
        return {
            "Fabricante": "DESCONHECIDO",
            "Service_Tag_Serial": "DESCONHECIDO",
            "Modelo": "EQUIPAMENTO_GENERICO",
            "Processador": "DESCONHECIDO",
            "Memoria_RAM": "DESCONHECIDO",
            "Armazenamento": "DESCONHECIDO",
        }
    finally:
        pythoncom.CoUninitialize()  # Libera o COM para esta thread
