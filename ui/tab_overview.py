"""
ui/tab_overview.py
Aba 1: Visão Geral com tabela agrupada em dois níveis (Dados | Conta Corrente | Aplicação | Rendimentos).
"""

from decimal import Decimal
import pandas as pd
import streamlit as st

from core.models import ResultadoConciliacao


def _fmt_brl(valor: Decimal) -> str:
    return f"{valor:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


def build_grouped_dataframe(resultados: list[ResultadoConciliacao]) -> pd.DataFrame:
    """Monta a tabela com cabeçalho duplo agrupado por bloco contábil."""
    linhas = []
    for r in resultados:
        desc_exibicao = (
            f"{r.banco} - {r.descricao}"
            if r.descricao and r.descricao != r.chave_conciliacao
            else r.banco
        )
        linhas.append({
            ("Dados", "Banco / Descrição"): desc_exibicao,
            ("Dados", "Conta Reduzida"): r.chave_conciliacao,
            ("Dados", "Status"): r.status,
            ("Conta Corrente", "Contábil"): _fmt_brl(r.siafic_cc),
            ("Conta Corrente", "Banco"): _fmt_brl(r.banco_cc),
            ("Conta Corrente", "Diferença"): _fmt_brl(r.dif_cc),
            ("Aplicação", "Contábil"): _fmt_brl(r.siafic_aplic),
            ("Aplicação", "Banco"): _fmt_brl(r.banco_aplic),
            ("Aplicação", "Diferença"): _fmt_brl(r.dif_aplic),
            ("Rendimentos", "Contábil"): _fmt_brl(r.siafic_rend),
            ("Rendimentos", "Banco"): _fmt_brl(r.banco_rend),
            ("Rendimentos", "Diferença"): _fmt_brl(r.dif_rend),
        })

    if not linhas:
        return pd.DataFrame()

    df = pd.DataFrame(linhas)
    df.columns = pd.MultiIndex.from_tuples(df.columns)
    return df


def render_tab_overview(resultados: list[ResultadoConciliacao]) -> None:
    """Exibe os indicadores resumidos, filtro rápido e a tabela agrupada."""
    total_contas = len(resultados)
    conciliadas = sum(1 for r in resultados if r.status == "Conciliado")
    divergentes = total_contas - conciliadas

    c1, c2, c3 = st.columns(3)
    c1.metric("Contas Analisadas", total_contas)
    c2.metric("Contas Conciliadas", conciliadas)
    c3.metric("Divergências / Pendências", divergentes)

    busca = st.text_input(
        "Buscar por conta, banco ou descrição:",
        placeholder="Digite o número da conta (ex: 0088501), banco ou fundo...",
    )

    filtrados = resultados
    if busca.strip():
        termo = busca.strip().lower()
        filtrados = [
            r for r in resultados
            if termo in r.chave_conciliacao.lower()
            or termo in r.banco.lower()
            or termo in r.descricao.lower()
            or termo in r.status.lower()
        ]

    df_display = build_grouped_dataframe(filtrados)
    if df_display.empty:
        st.info("Nenhum registro encontrado para o filtro informado.")
    else:
        st.dataframe(df_display, use_container_width=True, height=480)
