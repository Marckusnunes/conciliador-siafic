"""
core/account_key.py
Padronização de números de contas bancárias/contábeis e aplicação da tabela De-Para.
"""

import csv
import re
from pathlib import Path
from typing import Tuple

# Quantidade padrão de dígitos usada para cruzar contas entre SIAFIC e Bancos
TAMANHO_CHAVE = 7


def normalize_account_keys(raw_account: str) -> Tuple[str, str]:
    """
    Transforma qualquer formato de conta em duas chaves padronizadas:
      1. chave_7d: últimos 7 dígitos numéricos (preenchidos com zeros à esquerda)
      2. chave_7d_sem_dv: últimos 7 dígitos ignorando o último dígito verificador (DV)
    """
    if not raw_account:
        return "", ""

    text = str(raw_account).strip().upper()

    # 1. Padrão SIAFIC com hífens ("001 - 2234 - 0000000088501 - NOME DO FUNDO")
    # Isola apenas o maior bloco que contém somente números (ignora números no nome do fundo)
    if " - " in text:
        parts = [p.strip() for p in text.split("-")]
        numeric_parts = [re.sub(r"\D", "", p) for p in parts if re.fullmatch(r"[\d\s\.]+", p)]
        long_numeric = [p for p in numeric_parts if len(p) > 4]
        if long_numeric:
            text = max(long_numeric, key=len)

    # 2. Conta estruturada longa com pontos (ex: "001. 2234.0000000088501.1.7.59")
    if len(text) > 12 and "." in text:
        blocks = [re.sub(r"\D", "", part) for part in text.split(".")]
        valid_blocks = [b for b in blocks if len(b) > 4]
        if valid_blocks:
            text = max(valid_blocks, key=len)

    # 3. Se vier agência/conta separadas por barra (ex: "1234/56789-0"), pega após a última barra
    if "/" in text:
        text = text.split("/")[-1]

    # 4. Mantém apenas números (apaga traços, espaços e letras como o dígito 'X')
    digits_only = re.sub(r"\D", "", text)
    if not digits_only:
        return "", ""

    chave_7d = digits_only[-TAMANHO_CHAVE:].zfill(TAMANHO_CHAVE)

    # 5. Gera chave alternativa sem o último dígito verificador (DV)
    digits_without_dv = digits_only[:-1] if len(digits_only) > 1 else digits_only
    chave_7d_sem_dv = digits_without_dv[-TAMANHO_CHAVE:].zfill(TAMANHO_CHAVE)

    return chave_7d, chave_7d_sem_dv


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
