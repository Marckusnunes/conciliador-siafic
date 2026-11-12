"""
ui/sidebar_upload.py
Barra lateral do Streamlit para envio de arquivos e parâmetros da conciliação.
"""

from decimal import Decimal
import streamlit as st

from config.settings import TOLERANCIA_CENTAVOS


def render_sidebar() -> dict:
    """Desenha a barra lateral e devolve os arquivos enviados e configurações."""
    st.sidebar.header("1. Arquivos do SIAFIC (.csv)")
    arquivos_013083 = st.sidebar.file_uploader(
        "Relatório 013083 (Saldos Bancários)",
        type=["csv"],
        accept_multiple_files=True,
        help="Envie um ou mais arquivos CSV de saldos bancários do SIAFIC.",
    )
    arquivos_014387 = st.sidebar.file_uploader(
        "Relatório 014387 (Rendimentos)",
        type=["csv"],
        accept_multiple_files=True,
        help="Envie um ou mais arquivos CSV de rendimentos financeiros do SIAFIC.",
    )

    st.sidebar.divider()
    st.sidebar.header("2. Extratos Bancários (.pdf)")
    arquivos_pdf = st.sidebar.file_uploader(
        "Extratos (BB, Caixa, Bradesco)",
        type=["pdf"],
        accept_multiple_files=True,
        help="Envie todos os extratos PDF do mês (Conta Corrente, Poupança e Fundos).",
    )

    st.sidebar.divider()
    with st.sidebar.expander("Configurações Avançadas (Opcional)"):
        arquivo_de_para = st.file_uploader(
            "Tabela De-Para personalizada (.csv)",
            type=["csv"],
            accept_multiple_files=False,
            help="Se não enviar, o sistema usará o arquivo config/de_para_contas.csv do repositório.",
        )
        tol_float = st.number_input(
            "Tolerância de centavos (R$)",
            min_value=0.00,
            max_value=10.00,
            value=float(TOLERANCIA_CENTAVOS),
            step=0.01,
            format="%.2f",
        )
        titulo_pdf = st.text_input(
            "Título do Relatório PDF",
            value="Relatório de Conciliação Bancária - SIAFIC x Extratos",
        )

    return {
        "arquivos_013083": arquivos_013083 or [],
        "arquivos_014387": arquivos_014387 or [],
        "arquivos_pdf": arquivos_pdf or [],
        "arquivo_de_para": arquivo_de_para,
        "tolerancia": Decimal(str(f"{tol_float:.2f}")),
        "titulo_pdf": titulo_pdf,
    }
