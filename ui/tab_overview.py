"""
ui/tab_overview.py
Aba 1: Visão Geral com tabela agrupada em dois níveis.
"""

from collections import defaultdict
from decimal import Decimal
import pandas as pd
import streamlit as st

from core.models import RegistroBanco, ResultadoConciliacao


def _fmt_brl(valor: Decimal) -> str:
    return f"{valor:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


def indexar_banco_agencia_conta(registros_bancos: list[RegistroBanco]) -> dict[str, str]:
    """Mapeia chave_7d -> 'BB | Ag. 2234-9 | Conta 295717-5' a partir dos PDFs lidos."""
    agrupado: dict[str, list[str]] = defaultdict(list)
    for reg in registros_bancos:
        partes = [reg.banco]
        if reg.agencia:
            partes.append(f"Ag. {reg.agencia}")
        if reg.conta_original:
            partes.append(f"Conta {reg.conta_original}")
        texto = " | ".join(partes)
        if texto not in agrupado[reg.chave_7d]:
            agrupado[reg.chave_7d].append(texto)

    return {chave: " ; ".join(itens) for chave, itens in agrupado.items()}


def _linha_agrupada(
    r: ResultadoConciliacao,
    detalhe_bancario: dict[str, str] | None = None,
) -> dict[tuple[str, str], str]:
    """Monta uma linha sem 'Banco / Descrição' e com 'Banco / Ag. / Conta'."""
    info_banco = (detalhe_bancario or {}).get(r.chave_conciliacao) or r.banco or "-"

    return {
        ("Dados", "Banco / Ag. / Conta"): info_banco,
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
    }


def build_grouped_dataframe(
    resultados: list[ResultadoConciliacao],
    detalhe_bancario: dict[str, str] | None = None,
) -> pd.DataFrame:
    """Monta a tabela com cabeçalho duplo agrupado por bloco contábil."""
    linhas = [_linha_agrupada(r, detalhe_bancario) for r in resultados]
    if not linhas:
        return pd.DataFrame()

    df = pd.DataFrame(linhas)
    df.columns = pd.MultiIndex.from_tuples(df.columns)
    return df


def _filtrar_resultados(
    resultados: list[ResultadoConciliacao],
    busca: str,
    detalhe_bancario: dict[str, str] | None = None,
) -> list[ResultadoConciliacao]:
    termo = busca.strip().lower()
    if not termo:
        return resultados
    mapa = detalhe_bancario or {}
    return [
        r for r in resultados
        if termo in r.chave_conciliacao.lower()
        or termo in r.banco.lower()
        or termo in r.descricao.lower()
        or termo in r.status.lower()
        or termo in mapa.get(r.chave_conciliacao, "").lower()
    ]


def render_tab_overview(
    resultados: list[ResultadoConciliacao],
    detalhe_bancario: dict[str, str] | None = None,
) -> None:
    """Exibe os indicadores resumidos, filtro rápido e a tabela agrupada."""
    total_contas = len(resultados)
    conciliadas = sum(1 for r in resultados if r.status == "Conciliado")
    divergentes = total_contas - conciliadas

    c1, c2, c3 = st.columns(3)
    c1.metric("Contas Analisadas", total_contas)
    c2.metric("Contas Conciliadas", conciliadas)
    c3.metric("Divergências / Pendências", divergentes)

    busca = st.text_input(
        "Buscar por conta, banco, agência ou status:",
        placeholder="Digite conta (ex: 0088501), banco, agência ou status...",
    )

    filtrados = _filtrar_resultados(resultados, busca, detalhe_bancario)
    df_display = build_grouped_dataframe(filtrados, detalhe_bancario)

    if df_display.empty:
        st.info("Nenhum registro encontrado para o filtro informado.")
    else:
        st.dataframe(df_display, use_container_width=True, height=480)
