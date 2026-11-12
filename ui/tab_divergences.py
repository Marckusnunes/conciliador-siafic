"""
ui/tab_divergences.py
Aba 2: Painel focado exclusivamente nas contas com divergência ou pendência.
"""

from decimal import Decimal
import pandas as pd
import streamlit as st

from core.models import ResultadoConciliacao


def _fmt_brl(valor: Decimal) -> str:
    return f"R$ {valor:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


def render_tab_divergences(resultados: list[ResultadoConciliacao]) -> None:
    """Mostra apenas as contas que exigem análise do auditor."""
    divergentes = [r for r in resultados if r.status != "Conciliado"]

    if not divergentes:
        st.success("Nenhuma divergência encontrada! Todas as contas estão conciliadas.")
        return

    st.warning(f"Foram encontradas {len(divergentes)} conta(s) com divergência ou sem correspondência.")

    linhas = [
        {
            "Conta (7d)": r.chave_conciliacao,
            "Banco / Tipo": r.banco,
            "Descrição": r.descricao,
            "Status": r.status,
            "Dif. CC": _fmt_brl(r.dif_cc),
            "Dif. Aplic.": _fmt_brl(r.dif_aplic),
            "Dif. Rend.": _fmt_brl(r.dif_rend),
            "Observações / Alertas": " | ".join(r.alertas) if r.alertas else "-",
        }
        for r in divergentes
    ]

    st.dataframe(pd.DataFrame(linhas), use_container_width=True, hide_index=True)
