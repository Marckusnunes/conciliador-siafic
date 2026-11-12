"""
exporters/csv_exporter.py
Exporta o resultado da conciliação para arquivo CSV (padrão brasileiro com ';').
"""

import csv
import io
from decimal import Decimal

from core.models import ResultadoConciliacao


def _fmt_brl(valor: Decimal) -> str:
    """Formata um número Decimal para texto com vírgula (ex: 1234.56 -> '1234,56')."""
    return f"{valor:.2f}".replace(".", ",")


def export_to_csv(resultados: list[ResultadoConciliacao]) -> bytes:
    """Gera os bytes de um arquivo CSV pronto para download no Streamlit."""
    buffer = io.StringIO()
    writer = csv.writer(buffer, delimiter=";", lineterminator="\n")

    # Cabeçalho da tabela
    writer.writerow([
        "Conta_7d",
        "Metodo_Pareamento",
        "Banco_Tipo",
        "Descricao",
        "SIAFIC_CC",
        "Banco_CC",
        "Dif_CC",
        "SIAFIC_Aplic",
        "Banco_Aplic",
        "Dif_Aplic",
        "SIAFIC_Rend",
        "Banco_Rend",
        "Dif_Rend",
        "Status",
        "Alertas_Auditoria",
    ])

    for r in resultados:
        writer.writerow([
            r.chave_conciliacao,
            r.metodo_pareamento,
            r.banco,
            r.descricao,
            _fmt_brl(r.siafic_cc),
            _fmt_brl(r.banco_cc),
            _fmt_brl(r.dif_cc),
            _fmt_brl(r.siafic_aplic),
            _fmt_brl(r.banco_aplic),
            _fmt_brl(r.dif_aplic),
            _fmt_brl(r.siafic_rend),
            _fmt_brl(r.banco_rend),
            _fmt_brl(r.dif_rend),
            r.status,
            " | ".join(r.alertas) if r.alertas else "",
        ])

    # utf-8-sig adiciona a marcação que faz o Excel abrir acentos corretamente
    return buffer.getvalue().encode("utf-8-sig")
