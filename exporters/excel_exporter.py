"""
exporters/excel_exporter.py
Gera planilha Excel (.xlsx) formatada com abas, fórmulas e destaque visual.
"""

import io
import openpyxl
from openpyxl.styles import Alignment, Font, PatternFill
from openpyxl.utils import get_column_letter

from core.audit_logger import AuditLogger
from core.models import ResultadoConciliacao


def _preencher_aba_conciliacao(
    ws,
    linhas: list[ResultadoConciliacao],
    header_fill: PatternFill,
    header_font: Font,
    ok_fill: PatternFill,
    warn_fill: PatternFill,
    money_fmt: str,
) -> None:
    """Preenche uma aba do Excel com os dados, fórmulas e estilos."""
    headers = [
        "Banco-Agência-Conta",
        "Conta Reduzida (7d)",
        "Pareamento",
        "Banco / Tipo",
        "Descrição",
        "SIAFIC CC",
        "Banco CC",
        "Dif. CC",
        "SIAFIC Aplic.",
        "Banco Aplic.",
        "Dif. Aplic.",
        "SIAFIC Rend.",
        "Banco Rend.",
        "Dif. Rend.",
        "Status",
        "Alertas de Auditoria",
    ]
    ws.append(headers)

    for col_idx in range(1, len(headers) + 1):
        cell = ws.cell(row=1, column=col_idx)
        cell.fill = header_fill
        cell.font = header_font
        cell.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)

    for row_idx, r in enumerate(linhas, start=2):
        ws.append([
            r.conta_completa or r.chave_conciliacao,
            r.chave_conciliacao,
            r.metodo_pareamento,
            r.banco,
            r.descricao,
            float(r.siafic_cc),
            float(r.banco_cc),
            f"=F{row_idx}-G{row_idx}",
            float(r.siafic_aplic),
            float(r.banco_aplic),
            f"=I{row_idx}-J{row_idx}",
            float(r.siafic_rend),
            float(r.banco_rend),
            f"=L{row_idx}-M{row_idx}",
            r.status,
            " | ".join(r.alertas) if r.alertas else "",
        ])

        # Formata todas as colunas financeiras em R$ (colunas 6 a 14)
        for money_col in range(6, 15):
            ws.cell(row=row_idx, column=money_col).number_format = money_fmt

        # Pinta a célula de Status (coluna 15)
        status_cell = ws.cell(row=row_idx, column=15)
        status_cell.fill = ok_fill if r.status == "Conciliado" else warn_fill
        status_cell.font = Font(bold=True)

    # Ajusta a largura das colunas automaticamente para nada ficar cortado
    for col in ws.columns:
        max_len = max((len(str(c.value or "")) for c in col), default=12)
        ws.column_dimensions[get_column_letter(col[0].column)].width = min(max(max_len + 3, 14), 42)


def export_to_excel(
    resultados: list[ResultadoConciliacao],
    logger: AuditLogger | None = None,
) -> bytes:
    """Cria o arquivo Excel completo na memória e retorna seus bytes."""
    wb = openpyxl.Workbook()

    header_fill = PatternFill(start_color="1F4E78", end_color="1F4E78", fill_type="solid")
    header_font = Font(color="FFFFFF", bold=True, size=10)
    ok_fill = PatternFill(start_color="E2EFDA", end_color="E2EFDA", fill_type="solid")
    warn_fill = PatternFill(start_color="FCE4D6", end_color="FCE4D6", fill_type="solid")
    money_fmt = 'R$ #,##0.00;[Red]-R$ #,##0.00;"-"'

    ws_all = wb.active
    ws_all.title = "Conciliação Completa"
    _preencher_aba_conciliacao(
        ws_all, resultados, header_fill, header_font, ok_fill, warn_fill, money_fmt
    )

    ws_div = wb.create_sheet(title="Divergências")
    divergentes = [r for r in resultados if r.status != "Conciliado"]
    _preencher_aba_conciliacao(
        ws_div, divergentes, header_fill, header_font, ok_fill, warn_fill, money_fmt
    )

    ws_aud = wb.create_sheet(title="Trilha de Auditoria")
    ws_aud.append(["Data/Hora", "Nível", "Arquivo / Origem", "Mensagem"])
    for col_idx in range(1, 5):
        cell = ws_aud.cell(row=1, column=col_idx)
        cell.fill = header_fill
        cell.font = header_font

    if logger:
        for ev in logger.eventos:
            ws_aud.append([ev.timestamp, ev.nivel, ev.origem, ev.mensagem])

    for col in ws_aud.columns:
        max_len = max((len(str(c.value or "")) for c in col), default=15)
        ws_aud.column_dimensions[get_column_letter(col[0].column)].width = min(max(max_len + 3, 16), 70)

    buffer = io.BytesIO()
    wb.save(buffer)
    return buffer.getvalue()
