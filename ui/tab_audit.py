"""
ui/tab_audit.py
Abas 3 e 4: Log de Leitura dos PDFs/CSVs e Tabela De-Para aplicada.
"""

from decimal import Decimal
import pandas as pd
import streamlit as st

from core.audit_logger import AuditLogger
from core.models import RegistroBanco


def _fmt_brl(valor: Decimal) -> str:
    return f"{valor:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


def render_tab_log(
    registros_bancos: list[RegistroBanco],
    logger: AuditLogger,
) -> None:
    """Exibe a tabela resumo dos PDFs lidos e a trilha completa de execução."""
    st.subheader("Resumo dos Extratos Bancários Lidos")
    if registros_bancos:
        dados_pdfs = [
            {
                "Arquivo": r.fonte_arquivo,
                "Banco": r.banco,
                "Tipo": r.tipo_conta,
                "Conta Lida": r.conta_original,
                "Chave Gerada": r.chave_7d,
                "Saldo CC": _fmt_brl(r.saldo_cc),
                "Saldo Aplic./Poup.": _fmt_brl(r.saldo_aplic),
                "Rendimento": _fmt_brl(r.rendimento),
            }
            for r in registros_bancos
        ]
        st.dataframe(pd.DataFrame(dados_pdfs), use_container_width=True, hide_index=True)
    else:
        st.info("Nenhum extrato PDF foi lido nesta execução.")

    st.divider()
    st.subheader("Trilha de Auditoria Detalhada")
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


def render_tab_depara(mapa_de_para: dict[str, str]) -> None:
    """Exibe as regras De-Para ativas na conciliação."""
    if mapa_de_para:
        st.success(f"✅ De-Para ativo! {len(mapa_de_para)} mapeamento(s) carregado(s).")
        df_dp = pd.DataFrame(
            [{"Chave Antiga (Origem)": k, "Chave Nova (Destino)": v} for k, v in mapa_de_para.items()]
        )
        st.dataframe(df_dp, use_container_width=True, hide_index=True)
    else:
        st.info("Nenhuma regra De-Para cadastrada ou arquivo De-Para vazio.")
