"""
app.py
Ponto de entrada principal da aplicação Streamlit com layout em 2 colunas e 4 abas.
"""

import csv
import io
from decimal import Decimal
import pandas as pd
import streamlit as st

from core.account_key import TAMANHO_CHAVE, load_de_para_map, normalize_account_keys
from core.audit_logger import AuditLogger
from core.models import RegistroBanco, RegistroSIAFIC, ResultadoConciliacao
from parsers.banks.registry import parse_bank_pdf
from parsers.siafic.relatorio_013083 import parse_relatorio_013083
from parsers.siafic.relatorio_014387 import parse_relatorio_014387
from reconciliation.engine import run_reconciliation
from ui.download_bar import render_download_bar
from ui.sidebar_upload import render_upload_panel
from ui.tab_audit import render_tab_depara, render_tab_log
from ui.tab_divergences import render_tab_divergences
from ui.tab_overview import render_tab_overview

st.set_page_config(
    page_title="Conciliação Contábil",
    layout="wide",
    page_icon="📊",
    initial_sidebar_state="collapsed",
)

st.markdown(
    """
    <style>
        .block-container {padding-top: 2rem; padding-bottom: 2rem;}
        div[data-testid="stFileUploader"] section {padding: 10px;}
        h1 {font-size: 1.8rem;}
        h3 {font-size: 1.2rem;}
    </style>
    """,
    unsafe_allow_html=True,
)


def _carregar_de_para_upload(file_name: str, file_bytes: bytes) -> dict[str, str]:
    """Lê planilha De-Para enviada pelo usuário (aceita .xlsx ou .csv)."""
    mapa: dict[str, str] = {}

    if file_name.lower().endswith(".xlsx"):
        xls = pd.ExcelFile(io.BytesIO(file_bytes), engine="openpyxl")
        aba = "2025_JUNHO (2)" if "2025_JUNHO (2)" in xls.sheet_names else xls.sheet_names[0]
        df = pd.read_excel(xls, sheet_name=aba, dtype=str)
        if len(df.columns) >= 2:
            for _, row in df.iloc[:, :2].iterrows():
                c_ant, _ = normalize_account_keys(str(row.iloc[0]))
                c_nov, _ = normalize_account_keys(str(row.iloc[1]))
                if c_ant and c_nov:
                    mapa[c_ant] = c_nov
        return mapa

    texto = file_bytes.decode("utf-8-sig", errors="replace")
    sep = ";" if ";" in texto else ","
    reader = csv.DictReader(io.StringIO(texto), delimiter=sep)
    for row in reader:
        valores = list(row.values())
        if len(valores) >= 2:
            c_ant = (row.get("conta_origem") or valores[0] or "").strip().zfill(TAMANHO_CHAVE)
            c_nov = (row.get("conta_destino") or valores[1] or "").strip().zfill(TAMANHO_CHAVE)
            if c_ant and c_nov and c_ant != "0" * TAMANHO_CHAVE:
                mapa[c_ant] = c_nov
    return mapa


@st.cache_data(show_spinner="Lendo arquivos e cruzando dados...")
def _executar_pipeline(
    lista_013083: tuple[tuple[str, bytes], ...],
    lista_014387: tuple[tuple[str, bytes], ...],
    lista_pdfs: tuple[tuple[str, bytes, str, str], ...],
    de_para_info: tuple[str, bytes] | None,
    tolerancia_str: str,
) -> tuple[list[ResultadoConciliacao], list[RegistroBanco], AuditLogger, dict[str, str]]:
    """Executa toda a conciliação e guarda em cache para navegação instantânea."""
    logger = AuditLogger()
    registros_siafic: list[RegistroSIAFIC] = []
    registros_bancos: list[RegistroBanco] = []

    if de_para_info is not None:
        mapa_de_para = _carregar_de_para_upload(de_para_info[0], de_para_info[1])
        logger.info("De-Para", f"Planilha '{de_para_info[0]}' carregada ({len(mapa_de_para)} regras).")
    else:
        mapa_de_para = load_de_para_map("config/de_para_contas.csv")
        logger.info("De-Para", f"Tabela padrão config/de_para_contas.csv carregada ({len(mapa_de_para)} regras).")

    for nome, conteudo in lista_013083:
        try:
            registros_siafic.extend(parse_relatorio_013083(conteudo, nome, logger))
        except Exception as exc:
            logger.erro(nome, f"Falha ao processar relatório 013083: {exc}")

    for nome, conteudo in lista_014387:
        try:
            registros_siafic.extend(parse_relatorio_014387(conteudo, nome, logger))
        except Exception as exc:
            logger.erro(nome, f"Falha ao processar relatório 014387: {exc}")

    for nome, conteudo, banco_hint, tipo_hint in lista_pdfs:
        try:
            registros_bancos.extend(
                parse_bank_pdf(
                    file_bytes=conteudo,
                    filename=nome,
                    logger=logger,
                    banco_hint=banco_hint,
                    tipo_hint=tipo_hint,
                )
            )
        except Exception as exc:
            logger.erro(nome, f"Falha ao processar extrato PDF: {exc}")

    resultados = run_reconciliation(
        registros_siafic=registros_siafic,
        registros_bancos=registros_bancos,
        mapa_de_para=mapa_de_para,
        tolerancia=Decimal(tolerancia_str),
        logger=logger,
    )

    return resultados, registros_bancos, logger, mapa_de_para


def main() -> None:
    st.title("Sistema de Conciliação Financeira")
    st.markdown("---")

    dados = render_upload_panel()

    if dados["btn_processar"]:
        if not dados["arquivos_013083"]:
            st.warning("⚠️ Obrigatório carregar pelo menos um arquivo de Saldos (CSV - 013083).")
            return
        st.session_state["conciliacao_ativa"] = True

    if not st.session_state.get("conciliacao_ativa") or not dados["arquivos_013083"]:
        return

    pacote_013083 = tuple((f.name, f.getvalue()) for f in dados["arquivos_013083"])
    pacote_014387 = tuple((f.name, f.getvalue()) for f in dados["arquivos_014387"])
    pacote_pdfs = tuple(dados["lista_pdfs_etiquetados"])
    de_para_info = (
        (dados["arquivo_de_para"].name, dados["arquivo_de_para"].getvalue())
        if dados["arquivo_de_para"] is not None
        else None
    )

    resultados, registros_bancos, logger, mapa_de_para = _executar_pipeline(
        lista_013083=pacote_013083,
        lista_014387=pacote_014387,
        lista_pdfs=pacote_pdfs,
        de_para_info=de_para_info,
        tolerancia_str=str(dados["tolerancia"]),
    )

    erros = [ev for ev in logger.eventos if ev.nivel == "ERRO"]
    if erros:
        for err in erros:
            st.error(f"⚠️ **{err.origem}**: {err.mensagem}")

    if not resultados:
        st.error("O processamento não retornou dados.")
        return

    st.success("Processamento concluído.")

    tab1, tab2, tab3, tab4 = st.tabs([
        "📊 Visão Geral",
        "🚨 Apenas Divergências",
        "📝 Log de Leitura",
        "🔄 Mapa De-Para",
    ])

    with tab1:
        render_tab_overview(resultados)
        st.divider()
        render_download_bar(resultados, logger, dados["titulo_pdf"])

    with tab2:
        render_tab_divergences(resultados)

    with tab3:
        render_tab_log(registros_bancos, logger)

    with tab4:
        render_tab_depara(mapa_de_para)


if __name__ == "__main__":
    main()
