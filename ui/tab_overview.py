"""
ui/tab_overview.py
Aba 1: Visão Geral com indicadores (KPIs), filtros e tabela consolidada completa.
"""

from decimal import Decimal
import pandas as pd
import streamlit as st

from core.models import ResultadoConciliacao


def _fmt_brl(valor: Decimal) -> str:
    return f"R$ {valor:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


def render_tab_overview(resultados: list[ResultadoConciliacao]) -> None:
    """Exibe os cartões de resumo e a tabela completa com filtros."""
    total_contas = len(resultados)
    conciliadas = sum(1 for r in resultados if r.status == "Conciliado")
    divergentes = total_contas - conciliadas

    soma_dif_cc = sum((r.dif_cc for r in resultados), Decimal("0.00"))
    soma_dif_aplic = sum((r.dif_aplic for r in resultados), Decimal("0.00"))
    soma_dif_rend = sum((r.dif_rend for r in resultados), Decimal("0.00"))

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Contas Analisadas", total_contas)
    c2.metric("Contas Conciliadas", conciliadas)
    c3.metric("Divergências / Pendências", divergentes)
    c4.metric("Dif. Total (CC + Aplic.)", _fmt_brl(soma_dif_cc + soma_dif_aplic))

    st.caption(f"Diferença líquida em Rendimentos: {_fmt_brl(soma_dif_rend)}")
    st.divider()

    # Filtros interativos
    f1, f2 = st.columns([2, 1])
    busca = f1.text_input("Buscar por conta, descrição ou banco:", placeholder="Ex: 0088501, BB, FMADCA...")
    status_opcoes = ["Todos"] + sorted({r.status for r in resultados})
    status_sel = f2.selectbox("Filtrar por Status:", status_opcoes)

    filtrados = resultados
    if status_sel != "Todos":
        filtrados = [r for r in filtrados if r.status == status_sel]
    if busca.strip():
        termo = busca.strip().lower()
        filtrados = [
            r for r in filtrados
            if termo in r.chave_conciliacao.lower()
            or termo in r.descricao.lower()
            or termo in r.banco.lower()
        ]

    linhas_tabela = [
        {
            "Conta (7d)": r.chave_conciliacao,
            "Pareamento": r.metodo_pareamento,
            "Banco / Tipo": r.banco,
            "Descrição": r.descricao,
            "SIAFIC CC": _fmt_brl(r.siafic_cc),
            "Banco CC": _fmt_brl(r.banco_cc),
            "Dif. CC": _fmt_brl(r.dif_cc),
            "SIAFIC Aplic.": _fmt_brl(r.siafic_aplic),
            "Banco Aplic.": _fmt_brl(r.banco_aplic),
            "Dif. Aplic.": _fmt_brl(r.dif_aplic),
            "SIAFIC Rend.": _fmt_brl(r.siafic_rend),
            "Banco Rend.": _fmt_brl(r.banco_rend),
            "Dif. Rend.": _fmt_brl(r.dif_rend),
            "Status": r.status,
        }
        for r in filtrados
    ]

    st.dataframe(pd.DataFrame(linhas_tabela), use_container_width=True, hide_index=True)
