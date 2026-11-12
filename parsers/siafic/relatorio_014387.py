"""
parsers/siafic/relatorio_014387.py
Processa o relatório 014387 (Rendimentos de Aplicação Financeira) do SIAFIC.
"""

from decimal import Decimal

from core.account_key import normalize_account_keys
from core.audit_logger import AuditLogger
from core.models import RegistroSIAFIC
from core.money import parse_brl_decimal
from parsers.siafic.reader import read_siafic_csv


def parse_relatorio_014387(
    file_bytes: bytes,
    filename: str,
    logger: AuditLogger | None = None,
) -> list[RegistroSIAFIC]:
    """
    Transforma as linhas do relatório 014387 em fichas padronizadas (RegistroSIAFIC)
    preenchendo o campo 'rendimento'.
    """
    df, meta = read_siafic_csv(file_bytes, filename, logger)

    col_conta = meta["col_conta"]
    col_valor = meta["col_valor"]
    col_desc = meta["col_desc"]

    registros: list[RegistroSIAFIC] = []

    for _, row in df.iterrows():
        conta_bruta = row[col_conta].strip()
        chave_7d, chave_7d_sem_dv = normalize_account_keys(conta_bruta)

        if not chave_7d:
            continue

        valor_rendimento = parse_brl_decimal(row[col_valor])
        descricao = row[col_desc].strip() if (col_desc and row[col_desc].strip()) else ""

        registros.append(
            RegistroSIAFIC(
                fonte_arquivo=filename,
                tipo_relatorio="014387",
                conta_original=conta_bruta,
                chave_7d=chave_7d,
                chave_7d_sem_dv=chave_7d_sem_dv,
                descricao=descricao,
                saldo_cc=Decimal("0.00"),
                saldo_aplic=Decimal("0.00"),
                rendimento=valor_rendimento,
            )
        )

    if logger:
        logger.info(filename, f"Relatório 014387 processado: {len(registros)} registros válidos.")

    return registros
