"""
ui/download_bar.py
Barra de botões para baixar os resultados em Excel, PDF e CSV.
"""

from datetime import datetime
import streamlit as st

from core.audit_logger import AuditLogger
from core.models import ResultadoConciliacao
from exporters.csv_exporter import export_to_csv
from exporters.excel_exporter import export_to_excel
from exporters.pdf_exporter import export_to_pdf


def render_download_bar(
    resultados: list[ResultadoConciliacao],
    logger: AuditLogger,
    titulo_pdf: str,
) -> None:
    """Exibe os 3 botões de exportação lado a lado."""
    st.subheader("Exportar Resultados")
    data_tag = datetime.now().strftime("%Y%m%d_%H%M")

    col1, col2, col3 = st.columns(3)

    with col1:
        xlsx_bytes = export_to_excel(resultados, logger)
        st.download_button(
            label="Baixar Planilha Excel (.xlsx)",
            data=xlsx_bytes,
            file_name=f"conciliacao_siafic_{data_tag}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            use_container_width=True,
        )

    with col2:
        pdf_bytes = export_to_pdf(resultados, titulo=titulo_pdf)
        st.download_button(
            label="Baixar Relatório Formal (.pdf)",
            data=pdf_bytes,
            file_name=f"relatorio_conciliacao_{data_tag}.pdf",
            mime="application/pdf",
            use_container_width=True,
        )

    with col3:
        csv_bytes = export_to_csv(resultados)
        st.download_button(
            label="Baixar Tabela CSV (.csv)",
            data=csv_bytes,
            file_name=f"conciliacao_siafic_{data_tag}.csv",
            mime="text/csv",
            use_container_width=True,
        )
