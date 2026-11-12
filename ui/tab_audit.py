"""
ui/tab_audit.py
Aba 3: Trilha de Auditoria e conferência dos extratos identificados.
"""

from decimal import Decimal
import pandas as pd
import streamlit as st

from core.audit_logger import AuditLogger
from core.models import RegistroBanco


def _fmt_brl(valor: Decimal) -> str:
    return f"R$ {valor:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


def render_tab_audit(
    registros_bancos: list[RegistroBanco],
    logger: AuditLogger,
) -> None:
    """Exibe como cada PDF foi classificado e o diário completo de execução."""
    st.subheader("1. Classificação Automática dos Extratos PDF")
    if registros_bancos:
        dados_pdfs = [
            {
                "Arquivo PDF": r.fonte_arquivo,
                "Banco Identificado": r.banco,
                "Tipo de Conta": r.tipo_conta,
                "Agência": r.agencia,
                "Conta Original": r.conta_original,
                "Chave (7d)": r.chave_7d,
                "Saldo CC": _fmt_brl(r.saldo_cc),
                "Saldo Aplic./Poup.": _fmt_brl(r.saldo_aplic),
                "Rendimento": _fmt_brl(r.rendimento),
            }
            for r in registros_bancos
        ]
        st.dataframe(pd.DataFrame(dados_pdfs), use_container_width=True, hide_index=True)
    else:
        st.info("Nenhum extrato PDF foi processado.")

    st.divider()
    st.subheader("2. Log Detalhado da Execução (Trilha de Auditoria)")
    if logger.eventos:
        dados_log = [
            {
                "Data/Hora": ev.timestamp,
                "Nível": ev.nivel,
                "Origem": ev.origem,
                "Mensagem": ev.mensagem,
            }
            for ev in logger.eventos
        ]
        st.dataframe(pd.DataFrame(dados_log), use_container_width=True, hide_index=True)
    else:
        st.info("Nenhum evento registrado.")
