"""
core/account_key.py
Padronização de números de contas bancárias/contábeis, formatação Banco-Agência-Conta e De-Para.
"""

import csv
import re
from pathlib import Path
from typing import Tuple

TAMANHO_CHAVE = 7

CODIGOS_BANCO: dict[str, str] = {
    "BB": "001",
    "BANCO DO BRASIL": "001",
    "CAIXA": "104",
    "CEF": "104",
    "CAIXA ECONOMICA": "104",
    "CAIXA ECONÔMICA": "104",
    "BRADESCO": "237",
}


def normalize_account_keys(raw_account: str) -> Tuple[str, str]:
    """
    Transforma qualquer formato de conta em duas chaves padronizadas:
      1. chave_7d: últimos 7 dígitos numéricos (preenchidos com zeros à esquerda)
      2. chave_7d_sem_dv: últimos 7 dígitos ignorando o último dígito verificador (DV)
    """
    if not raw_account:
        return "", ""

    text = str(raw_account).strip().upper()

    if " - " in text:
        parts = [p.strip() for p in text.split("-")]
        numeric_parts = [re.sub(r"\D", "", p) for p in parts if re.fullmatch(r"[\d\s\.]+", p)]
        long_numeric = [p for p in numeric_parts if len(p) > 4]
        if long_numeric:
            text = max(long_numeric, key=len)

    if len(text) > 12 and "." in text:
        blocks = [re.sub(r"\D", "", part) for part in text.split(".")]
        valid_blocks = [b for b in blocks if len(b) > 4]
        if valid_blocks:
            text = max(valid_blocks, key=len)

    if "/" in text:
        text = text.split("/")[-1]

    digits_only = re.sub(r"\D", "", text)
    if not digits_only:
        return "", ""

    chave_7d = digits_only[-TAMANHO_CHAVE:].zfill(TAMANHO_CHAVE)

    digits_without_dv = digits_only[:-1] if len(digits_only) > 1 else digits_only
    chave_7d_sem_dv = digits_without_dv[-TAMANHO_CHAVE:].zfill(TAMANHO_CHAVE)

    return chave_7d, chave_7d_sem_dv


def format_banco_agencia_conta_siafic(raw_account: str, chave_7d: str) -> str:
    """
    Extrai Banco, Agência e Conta de strings do SIAFIC e formata como '001-2234-0088501'.
    """
    if not chave_7d:
        return ""
    if not raw_account:
        return chave_7d

    text = str(raw_account).strip().upper()

    m_hifen = re.match(r"^\s*(\d{1,4})\s*-\s*(\d{1,6}(?:-[\dX])?)\s*-\s*([\d\.]+)", text)
    if m_hifen:
        banco = m_hifen.group(1).zfill(3)
        ag_base = m_hifen.group(2).split("-")[0]
        ag_digits = re.sub(r"\D", "", ag_base)
        agencia = str(int(ag_digits)).zfill(4) if ag_digits else "0000"
        return f"{banco}-{agencia}-{chave_7d}"

    m_ponto = re.match(r"^\s*(\d{1,4})\.\s*(\d{1,6})\.\s*(\d+)", text)
    if m_ponto:
        banco = m_ponto.group(1).zfill(3)
        ag_digits = re.sub(r"\D", "", m_ponto.group(2))
        agencia = str(int(ag_digits)).zfill(4) if ag_digits else "0000"
        return f"{banco}-{agencia}-{chave_7d}"

    return chave_7d


def format_banco_agencia_conta_banco(banco_nome: str, agencia_raw: str, chave_7d: str) -> str:
    """
    Monta o formato '001-2234-2956241' (Banco-Agência-Conta) a partir dos dados do PDF.
    """
    if not chave_7d:
        return ""

    b_upper = (banco_nome or "").strip().upper()
    digits_banco = re.sub(r"\D", "", b_upper)
    cod_banco = CODIGOS_BANCO.get(b_upper, digits_banco.zfill(3) if digits_banco else "000")

    ag_base = (agencia_raw or "").split("-")[0]
    ag_digits = re.sub(r"\D", "", ag_base)
    agencia = str(int(ag_digits)).zfill(4) if ag_digits else "0000"

    return f"{cod_banco}-{agencia}-{chave_7d}"


def load_de_para_map(csv_path: str | Path) -> dict[str, str]:
    """Lê o arquivo CSV de De-Para e devolve um dicionário {origem: destino}."""
    path = Path(csv_path)
    mapping: dict[str, str] = {}

    if not path.exists():
        return mapping

    with path.open("r", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f, delimiter=";")
        for row in reader:
            origem = (row.get("conta_origem") or "").strip().zfill(TAMANHO_CHAVE)
            destino = (row.get("conta_destino") or "").strip().zfill(TAMANHO_CHAVE)
            if origem and destino and origem != "0" * TAMANHO_CHAVE:
                mapping[origem] = destino

    return mapping


def apply_de_para(chave: str, mapa_de_para: dict[str, str]) -> Tuple[str, bool]:
    """Substitui a chave da conta caso exista uma regra cadastrada no De-Para."""
    if chave in mapa_de_para:
        return mapa_de_para[chave], True
    return chave, False
