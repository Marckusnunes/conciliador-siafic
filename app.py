"""
app.py
Ponto de entrada principal da aplicação Streamlit.
"""

import csv
import io
from decimal import Decimal
import streamlit as st

from core.account_key import TAMANHO_CHAVE, load_de_para_map
from core.audit_logger import AuditLogger
from core.models import RegistroBanco, RegistroSIAFIC, ResultadoConciliacao
from parsers.banks.registry import parse_bank_pdf
from parsers.siafic.relatorio_013083 import parse_relatorio_013083
from parsers.siafic.relatorio_014387 import parse_relatorio_014387
from reconciliation.engine import run_reconciliation
from ui.download_bar import render_download_bar
from ui.sidebar_upload import render_sidebar
from ui.tab_audit import render_tab_audit
from ui.tab_divergences import render_tab_divergences
from ui.tab_overview import render_tab_overview

st.set_page_config(
    page_title="Conciliador Bancário - SIAFIC",
    layout="wide",
)


def _ler_de_para_upload(file_bytes: bytes) -> dict[str, str]:
    """Lê uma tabela De-Para enviada pelo usuário na barra lateral."""
    texto = file_bytes.decode("utf-8-sig", errors="replace")
    reader = csv.DictReader(io.StringIO(texto), delimiter=";")
    mapa: dict[str, str] = {}
    for row in reader:
        origem = (row.get("conta_origem") or "").strip().zfill(TAMANHO_CHAVE)
        destino = (row.get("conta_destino") or "").strip().zfill(TAMANHO_CHAVE)
        if origem and destino and origem != "0" * TAMANHO_CHAVE:
            mapa[origem] = destino
    return mapa


@st.cache_data(show_spinner="Processando arquivos e executando conciliação...")
def _executar_pipeline_em_cache(
    lista_013083: tuple[tuple[str, bytes], ...],
    lista_014387: tuple[tuple[str, bytes], ...],
    lista_pdfs: tuple[tuple[str, bytes], ...],
    de_para_bytes: bytes | None,
    tolerancia_str: str,
) -> tuple[list[ResultadoConciliacao], list[RegistroBanco], AuditLogger]:
    """Executa a leitura e conciliação com cache para evitar reprocessamento ao filtrar."""
    logger = AuditLogger()
    registros_siafic: list[RegistroSIAFIC] = []
    registros_bancos: list[RegistroBanco] = []

    if de_para_bytes:
        mapa_de_para = _ler_de_para_upload(de_para_bytes)
        logger.info("De-Para", f"Tabela De-Para personalizada carregada ({len(mapa_de_para)} regras).")
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

    for nome, conteudo in lista_pdfs:
        try:
            registros_bancos.extend(parse_bank_pdf(conteudo, nome, logger))
        except Exception as exc:
            logger.erro(nome, f"Falha ao processar extrato PDF: {exc}")

    resultados = run_reconciliation(
        registros_siafic=registros_siafic,
        registros_bancos=registros_bancos,
        mapa_de_para=mapa_de_para,
        tolerancia=Decimal(tolerancia_str),
        logger=logger,
    )

    return resultados, registros_bancos, logger


def main() -> None:
    st.title("Conciliador Bancário Automatizado (SIAFIC × Extratos PDF)")
    st.markdown(
        "Envie os relatórios **013083** e **014387** do SIAFIC junto com os **extratos bancários em PDF** "
        "na barra lateral para iniciar a conciliação."
    )

    dados_sidebar = render_sidebar()

    tem_arquivos = (
        bool(dados_sidebar["arquivos_013083"])
        or bool(dados_sidebar["arquivos_014387"])
        or bool(dados_sidebar["arquivos_pdf"])
    )

    if not tem_arquivos:
        st.info("Aguardando o envio dos arquivos na barra lateral esquerda.")
        return

    pacote_013083 = tuple((f.name, f.getvalue()) for f in dados_sidebar["arquivos_013083"])
    pacote_014387 = tuple((f.name, f.getvalue()) for f in dados_sidebar["arquivos_014387"])
    pacote_pdfs = tuple((f.name, f.getvalue()) for f in dados_sidebar["arquivos_pdf"])
    de_para_bytes = (
        dados_sidebar["arquivo_de_para"].getvalue()
        if dados_sidebar["arquivo_de_para"] is not None
        else None
    )

    resultados, registros_bancos, logger = _executar_pipeline_em_cache(
        lista_013083=pacote_013083,
        lista_014387=pacote_014387,
        lista_pdfs=pacote_pdfs,
        de_para_bytes=de_para_bytes,
        tolerancia_str=str(dados_sidebar["tolerancia"]),
    )

    # Exibe alertas caso algum arquivo tenha falhado na leitura
    erros = [ev for ev in logger.eventos if ev.nivel == "ERRO"]
    if erros:
        for err in erros:
            st.error(f"**{err.origem}**: {err.mensagem}")

    aba1, aba2, aba3 = st.tabs([
        "Visão Geral",
        "Divergências e Pendências",
        "Trilha de Auditoria",
    ])

    with aba1:
        render_tab_overview(resultados)

    with aba2:
        render_tab_divergences(resultados)

    with aba3:
        render_tab_audit(registros_bancos, logger)

    st.divider()
    render_download_bar(resultados, logger, dados_sidebar["titulo_pdf"])


if __name__ == "__main__":
    main()
