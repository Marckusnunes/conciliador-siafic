"""
ui/tab_divergences.py
Aba 2: Painel focado exclusivamente nas contas com divergência ou pendência.
"""

import streamlit as st
from core.models import ResultadoConciliacao
from ui.tab_overview import build_grouped_dataframe


def render_tab_divergences(resultados: list[ResultadoConciliacao]) -> None:
    """Mostra apenas as linhas que apresentaram diferença ou falta de correspondência."""
    divergentes = [r for r in resultados if r.status != "Conciliado"]

    if not divergentes:
        st.info("Tudo certo! Nenhuma divergência encontrada.")
        return

    st.warning(f"Foram encontradas {len(divergentes)} conta(s) com divergência ou pendência.")
    df_div = build_grouped_dataframe(divergentes)
    st.dataframe(df_div, use_container_width=True)
