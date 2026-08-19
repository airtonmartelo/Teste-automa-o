from datetime import datetime
import logging
import re
from pathlib import Path
from utils import paths, constants


def sanitize_filename(name: str) -> str:
    """Sanitiza strings para uso seguro em nomes de arquivos no Windows."""
    if not name:
        return "NAO_INFORMADO"
    # Remove qualquer caractere que não seja alfanumérico, hífen ou sublinhado
    sanitized = re.sub(r"[^a-zA-Z0-9_\-]", "_", str(name).strip())
    # Remove underscores duplicados
    sanitized = re.sub(r"_+", "_", sanitized).strip("_")
    return sanitized or "NAO_INFORMADO"


def generate_report_file(hardware_info: dict, patrimonio: str, test_widgets: dict, test_categories: list):
    """Gera o arquivo de texto do relatório com base nos dados da aplicação."""
    serial = hardware_info.get("Service_Tag_Serial", "DESCONHECIDO")
    now = datetime.now()

    paths.LOGS_DIR_PATH.mkdir(parents=True, exist_ok=True)

    # Sanitização contra Path Traversal e caracteres inválidos no Windows
    safe_patrimonio = sanitize_filename(patrimonio)
    safe_serial = sanitize_filename(serial)
    safe_filename = f"{safe_patrimonio}_{safe_serial}_{now.strftime('%Y-%m-%d')}.txt"

    caminho_salvamento = (paths.LOGS_DIR_PATH / safe_filename).resolve()
    base_logs_path = paths.LOGS_DIR_PATH.resolve()

    # Garante que o arquivo será gravado estritamente dentro do diretório de relatórios
    if not str(caminho_salvamento).startswith(str(base_logs_path)):
        logging.error(f"Tentativa de gravação fora do diretório permitido: {caminho_salvamento}")
        return None

    # Coleta todas as falhas para o resumo de descrição rápida
    falhas_detectadas = []
    for category_data in test_categories:
        for item in category_data["items"]:
            widgets = test_widgets.get(item["key"])
            if widgets:
                status = widgets["status_var"].get()
                if status == constants.STATUS_FAIL:
                    detalhe = widgets["details_entry"].get().strip()
                    if detalhe:
                        falhas_detectadas.append(
                            f"• [{category_data['category']}] {widgets['name']}: {detalhe}"
                        )
                    else:
                        falhas_detectadas.append(
                            f"• [{category_data['category']}] {widgets['name']} (Com defeito/falha)"
                        )

    try:
        with open(caminho_salvamento, "w", encoding="utf-8") as f:
            f.write("==================================================\n")
            f.write("        RELATÓRIO TRIAGEM (PCTEC)\n")
            f.write(f"Data/Hora: {now.strftime('%d/%m/%Y %H:%M:%S')}\n")
            f.write(f"Patrimônio: {patrimonio or 'NÃO INFORMADO'}\n")
            f.write(f"Equipamento: {hardware_info.get('Modelo', 'N/A')}\n")
            f.write(f"Fabricante: {hardware_info.get('Fabricante', 'N/A')}\n")
            f.write(f"Service Tag / Serial: {serial}\n")
            f.write(f"Processador: {hardware_info.get('Processador', 'N/A')}\n")
            f.write(f"Memoria RAM: {hardware_info.get('Memoria_RAM', 'N/A')}\n")
            f.write(f"Armazenamento: {hardware_info.get('Armazenamento', 'N/A')}\n")
            f.write("==================================================\n\n")

            # --- SEÇÃO DE RESUMO PARA COPIAR E COLAR NO SISTEMA WEB ---
            f.write("==================================================\n")
            f.write(">>> LAUDO / RESUMO DE FALHAS (COPIAR PARA WEB) <<<\n")
            f.write("==================================================\n")
            if falhas_detectadas:
                for falha in falhas_detectadas:
                    f.write(f"{falha}\n")
            else:
                f.write("• NENHUMA FALHA DETECTADA - EQUIPAMENTO 100% APROVADO\n")
            f.write("==================================================\n\n")

            # --- DETALHAMENTO COMPLETO DE TODOS OS TESTES ---
            f.write("DETALHAMENTO COMPLETO DE TODOS OS TESTES:\n")
            f.write("--------------------------------------------------\n")
            for category_data in test_categories:
                f.write(f"\n--- {category_data['category']} ---\n")
                for item in category_data["items"]:
                    widgets = test_widgets.get(item["key"])
                    if widgets:
                        status = widgets["status_var"].get()
                        f.write(f"[{status}] {widgets['name']}\n")
                        if status == constants.STATUS_FAIL:
                            detalhe = (
                                widgets["details_entry"].get().strip() or "Falha não detalhada pelo operador."
                            )
                            f.write(f"      L Detalhe da Falha: {detalhe}\n")

            f.write("\n==================================================\n")

        logging.info(f"Triagem concluída! Relatório gravado em: {caminho_salvamento}")
        return caminho_salvamento
    except Exception as e:
        logging.error(f"Falha ao gerar o arquivo de relatório: {e}")
        return None
