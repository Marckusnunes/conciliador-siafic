"""
ui/bac_formatter.py
Monta a identificação no formato '001-2234-2951981' a partir dos registros do SIAFIC e Bancos.
"""

import re
from core.models import RegistroBanco, RegistroSIAFIC

CODIGOS_BANCO = {
    "BB": "001",
    "BANCO DO BRASIL": "001",
    "CAIXA": "104",
    "CEF": "104",
    "CAIXA ECONOMICA": "104",
    "CAIXA ECONÔMICA": "104",
    "BRADESCO": "237",
}


def _normalizar_agencia(agencia_raw: str) -> str:
    ag_base = (agencia_raw or "").split("-")[0]
    digitos = re.sub(r"\D", "", ag_base)
    return str(int(digitos)).zfill(4) if digitos else ""


def _normalizar_banco(banco_raw: str) -> str:
    texto = (banco_raw or "").strip().upper()
    if not texto:
        return ""
    if texto in CODIGOS_BANCO:
        return CODIGOS_BANCO[texto]
    for nome, cod in CODIGOS_BANCO.items():
        if nome in texto:
            return cod
    digitos = re.sub(r"\D", "", texto)
    return digitos.zfill(3) if digitos else ""


def extrair_bac_siafic(conta_original: str, chave_7d: str) -> str:
    """Extrai '001-2234-0088501' de textos como '001 - 2234 - 0000000088501 - FMADCA...'."""
    if not chave_7d:
        return ""
    texto = (conta_original or "").strip()

    match_hifen = re.match(r"^\s*(\d{1,4})\s*-\s*(\d{1,6}(?:-[\dX])?)\s*-\s*([\d\.]+)", texto)
    if match_hifen:
        banco = match_hifen.group(1).zfill(3)
        agencia = _normalizar_agencia(match_hifen.group(2))
        if banco and agencia:
            return f"{banco}-{agencia}-{chave_7d}"

    match_ponto = re.match(r"^\s*(\d{1,4})\.\s*(\d{1,6})\.\s*(\d+)", texto)
    if match_ponto:
        banco = match_ponto.group(1).zfill(3)
        agencia = _normalizar_agencia(match_ponto.group(2))
        if banco and agencia:
            return f"{banco}-{agencia}-{chave_7d}"

    return chave_7d


def montar_bac_banco(banco: str, agencia: str, chave_7d: str) -> str:
    """Monta '001-2234-2951981' a partir dos campos extraídos do PDF bancário."""
    if not chave_7d:
        return ""
    cod_banco = _normalizar_banco(banco)
    ag_norm = _normalizar_agencia(agencia)
    if cod_banco and ag_norm:
        return f"{cod_banco}-{ag_norm}-{chave_7d}"
    if cod_banco:
        return f"{cod_banco}-{chave_7d}"
    return chave_7d


def construir_mapa_bac(
    registros_siafic: list[RegistroSIAFIC],
    registros_bancos: list[RegistroBanco],
) -> dict[str, str]:
    """Mapeia cada chave_7d para o formato '001-2234-2951981' encontrado."""
    mapa: dict[str, str] = {}

    for reg in registros_siafic:
        if reg.chave_7d and reg.chave_7d not in mapa:
            mapa[reg.chave_7d] = extrair_bac_siafic(reg.conta_original, reg.chave_7d)

    for reg in registros_bancos:
        if reg.chave_7d:
            bac_banco = montar_bac_banco(reg.banco, reg.agencia, reg.chave_7d)
            if bac_banco and (reg.chave_7d not in mapa or "-" not in mapa[reg.chave_7d]):
                mapa[reg.chave_7d] = bac_banco

    return mapa
