"""
ui/tab_overview.py
Aba 1: Visão Geral com tabela agrupada em dois níveis.
"""

import re
from decimal import Decimal
import pandas as pd
import streamlit as st

from core.models import ResultadoConciliacao


def _fmt_brl(valor: Decimal) -> str:
    return f"{valor:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


def _extrair_codigo_banco(banco: str) -> str:
    texto = (banco or "").strip().upper()
    if not texto:
        return ""
    if "BRASIL" in texto or texto == "BB" or texto.startswith("001"):
        return "001"
    if "CAIXA" in texto or "CEF" in texto or texto.startswith("104"):
        return "104"
    if "BRADESCO" in texto or texto.startswith("237"):
        return "237"
    digitos = re.sub(r"\D", "", texto)
    return digitos.zfill(3) if digitos else texto


def formatar_banco_agencia_conta(r: ResultadoConciliacao) -> str:
    """
    Formata a identificação no padrão '001-2234-2951981' quando disponível.
    """
    cod_banco = _extrair_codigo_banco(r.banco)
    conta = (r.chave_conciliacao or "").strip()

    # Tenta localizar agência no texto bruto de origem (ex.: '001 - 2234 - ...')
    origem_texto = f"{r.banco} - {r.descricao}"
    blocos = [p.strip() for p in origem_texto.split("-")]
    nums = [re.sub(r"\D", "", p) for p in blocos if re.fullmatch(r"[\d\s]+", p.strip())]

    agencia = ""
    if len(nums) >= 2:
        agencia = nums[1]

    if cod_banco and agencia and conta:
        return f"{cod_banco}-{agencia}-{conta}"
    if cod_banco and conta:
        return f"{cod_banco}-{conta}"
    return conta or cod_banco or "-"


def _linha_agrupada(r: ResultadoConciliacao) -> dict[tuple[str, str], str]:
    """Monta uma linha sem 'Banco / Descrição' e com 'Banco - Agência - Conta'."""
    return {
        ("Dados", "Banco - Agência - Conta"): formatar_banco_agencia_conta(r),
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


def build_grouped_dataframe(resultados: list[ResultadoConciliacao]) -> pd.DataFrame:
    """Monta a tabela com cabeçalho duplo agrupado por bloco contábil."""
    linhas = [_linha_agrupada(r) for r in resultados]
    if not linhas:
        return pd.DataFrame()

    df = pd.DataFrame(linhas)
    df.columns = pd.MultiIndex.from_tuples(df.columns)
    return df


def _filtrar_resultados(
    resultados: list[ResultadoConciliacao],
    busca: str,
) -> list[ResultadoConciliacao]:
    termo = busca.strip().lower()
    if not termo:
        return resultados
    return [
        r for r in resultados
        if termo in r.chave_conciliacao.lower()
        or termo in formatar_banco_agencia_conta(r).lower()
        or termo in r.banco.lower()
        or termo in r.descricao.lower()
        or termo in r.status.lower()
    ]


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
        "Buscar por conta, banco, agência ou status:",
        placeholder="Digite conta (ex: 0088501), 001-2234 ou status...",
    )

    filtrados = _filtrar_resultados(resultados, busca)
    df_display = build_grouped_dataframe(filtrados)

    if df_display.empty:
        st.info("Nenhum registro encontrado para o filtro informado.")
    else:
        st.dataframe(df_display, use_container_width=True, height=480)
