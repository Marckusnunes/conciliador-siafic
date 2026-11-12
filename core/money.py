"""
core/money.py
Conversor monetário blindado para padrões bancários e governamentais brasileiros.
"""

import re
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP


def parse_brl_decimal(raw_value: str | None) -> Decimal:
    """
    Converte textos monetários em Decimal exato com 2 casas decimais.
    Exemplos que esta função resolve automaticamente:
      - '5.799,72 C'    -> Decimal('5799.72')
      - '6.63 C'        -> Decimal('6.63')
      - '20.413,27 D'   -> Decimal('-20413.27')
      - '(150,00)'      -> Decimal('-150.00')
      - '-2.547.456,25' -> Decimal('-2547456.25')
    """
    if raw_value is None:
        return Decimal("0.00")

    text = str(raw_value).strip().upper()
    if not text or text in {"-", "NAN", "NONE", "NULL"}:
        return Decimal("0.00")

    # 1. Verifica se existe indicação de valor negativo (Débito) antes de apagar letras
    is_negative = False
    if (
        "-" in text
        or ("(" in text and ")" in text)
        or re.search(r"\bDEB\b", text)
        or re.search(r"[\d,\.]\s*D\b", text)
    ):
        is_negative = True

    # 2. Apaga tudo o que não for número, vírgula ou ponto
    cleaned = re.sub(r"[^\d,\.]", "", text)
    if not cleaned:
        return Decimal("0.00")

    # 3. Ajusta o separador decimal para ponto (padrão matemático do Python)
    if "," in cleaned and "." in cleaned:
        # Se a vírgula vem depois do ponto (ex: 1.234,56), o ponto é separador de milhar
        if cleaned.rfind(",") > cleaned.rfind("."):
            cleaned = cleaned.replace(".", "").replace(",", ".")
        else:
            # Caso contrário (ex: 1,234.56), a vírgula é milhar
            cleaned = cleaned.replace(",", "")
    elif "," in cleaned:
        cleaned = cleaned.replace(",", ".")
    elif cleaned.count(".") > 1:
        # Ex: '1.000.000' sem centavos
        cleaned = cleaned.replace(".", "")

    try:
        value = Decimal(cleaned).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        if is_negative and value != Decimal("0.00"):
            return -abs(value)
        return value
    except InvalidOperation:
        return Decimal("0.00")
