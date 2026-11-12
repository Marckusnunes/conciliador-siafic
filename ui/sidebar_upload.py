"""
ui/sidebar_upload.py
Painel principal de envio de arquivos em 2 colunas (Contábil à esquerda, Bancos à direita),
seguindo o layout direto e organizado por banco e tipo de extrato.
"""

from decimal import Decimal
import streamlit as st

from config.settings import TOLERANCIA_CENTAVOS


def render_upload_panel() -> dict:
    """Desenha os dois quadros principais de upload e o botão de processamento."""
    col_left, col_right = st.columns(2)

    with col_left:
        with st.container(border=True):
            st.subheader("1. Arquivos Contábeis (CSV)")
            f_saldos = st.file_uploader(
                "Conta corrente / Saldos (.CSV) - Relatório 013083",
                type=["csv"],
                accept_multiple_files=True,
                help="Envie um ou mais arquivos CSV de saldos bancários do SIAFIC.",
            )
            f_rendim = st.file_uploader(
                "Rendimentos (.CSV) - Relatório 014387",
                type=["csv"],
                accept_multiple_files=True,
                help="Envie um ou mais arquivos CSV de rendimentos financeiros do SIAFIC.",
            )

            st.divider()
            with st.expander("⚙️ Mapa De-Para e Parâmetros (Opcional)"):
                arquivo_de_para = st.file_uploader(
                    "Planilha De-Para (.xlsx ou .csv)",
                    type=["xlsx", "csv"],
                    accept_multiple_files=False,
                    help="Se não enviar, o sistema usa config/de_para_contas.csv do repositório.",
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
                    value="Relatório de Conciliação Contábil",
                )

    with col_right:
        with st.container(border=True):
            st.subheader("2. Extratos Bancários (PDF)")
            f_bb_cc = st.file_uploader(
                "🔵 Banco do Brasil - Conta Corrente",
                type=["pdf"],
                accept_multiple_files=True,
            )
            f_bb_inv = st.file_uploader(
                "🔵 Banco do Brasil - Investimentos (Fundos / Poupança)",
                type=["pdf"],
                accept_multiple_files=True,
            )

            st.divider()

            f_caixa_cc = st.file_uploader(
                "🟠 Caixa Econômica - Conta Corrente",
                type=["pdf"],
                accept_multiple_files=True,
            )
            f_caixa_inv = st.file_uploader(
                "🟠 Caixa Econômica - Investimentos",
                type=["pdf"],
                accept_multiple_files=True,
            )

            st.divider()

            f_bradesco_cc = st.file_uploader(
                "🔴 Bradesco - Conta Corrente",
                type=["pdf"],
                accept_multiple_files=True,
            )

    st.markdown("<br>", unsafe_allow_html=True)
    btn_processar = st.button(
        "Processar Conciliação",
        type="primary",
        use_container_width=True,
    )

    # Etiqueta cada PDF com o Banco e o Tipo escolhidos pelo usuário
    lista_pdfs_etiquetados = []
    for f in f_bb_cc or []:
        lista_pdfs_etiquetados.append((f.name, f.getvalue(), "BB", "CC"))
    for f in f_bb_inv or []:
        lista_pdfs_etiquetados.append((f.name, f.getvalue(), "BB", "INV"))
    for f in f_caixa_cc or []:
        lista_pdfs_etiquetados.append((f.name, f.getvalue(), "CAIXA", "CC"))
    for f in f_caixa_inv or []:
        lista_pdfs_etiquetados.append((f.name, f.getvalue(), "CAIXA", "INV"))
    for f in f_bradesco_cc or []:
        lista_pdfs_etiquetados.append((f.name, f.getvalue(), "BRADESCO", "CC"))

    return {
        "btn_processar": btn_processar,
        "arquivos_013083": f_saldos or [],
        "arquivos_014387": f_rendim or [],
        "lista_pdfs_etiquetados": lista_pdfs_etiquetados,
        "arquivo_de_para": arquivo_de_para,
        "tolerancia": Decimal(str(f"{tol_float:.2f}")),
        "titulo_pdf": titulo_pdf,
    }
