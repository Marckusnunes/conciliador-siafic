"""
parsers/siafic/relatorio_013083.py
Processa o relatório 013083 (Saldos Bancários / Conformidade de UG) do SIAFIC.
"""

from decimal import Decimal

from config.settings import CODIGOS_CONTA_APLICACAO
from core.account_key import normalize_account_keys
from core.audit_logger import AuditLogger
from core.models import RegistroSIAFIC
from core.money import parse_brl_decimal
from parsers.siafic.reader import read_siafic_csv


def parse_relatorio_013083(
    file_bytes: bytes,
    filename: str,
    logger: AuditLogger | None = None,
) -> list[RegistroSIAFIC]:
    """
    Transforma as linhas do relatório 013083 em fichas padronizadas (RegistroSIAFIC),
    separando Saldo de Conta Corrente (CC) e Saldo de Aplicação.
    """
    df, meta = read_siafic_csv(file_bytes, filename, logger)

    col_conta = meta["col_conta"]
    col_valor = meta["col_valor"]
    col_desc = meta["col_desc"]
    col_contabil = meta["col_contabil"]

    registros: list[RegistroSIAFIC] = []

    for _, row in df.iterrows():
        conta_bruta = row[col_conta].strip()
        chave_7d, chave_7d_sem_dv = normalize_account_keys(conta_bruta)

        # Descarta linhas que não tenham números válidos de conta
        if not chave_7d:
            continue

        valor = parse_brl_decimal(row[col_valor])

        # Extrai a descrição: usa coluna própria ou o texto após o último hífen do Domicílio
        if col_desc and row[col_desc].strip():
            descricao = row[col_desc].strip()
        elif " - " in conta_bruta:
            descricao = conta_bruta.split(" - ")[-1].strip()
        else:
            descricao = conta_bruta

        # Divide o saldo entre Conta Corrente e Aplicação conforme a Conta Contábil
        saldo_cc = Decimal("0.00")
        saldo_aplic = Decimal("0.00")

        if col_contabil:
            texto_contabil = row[col_contabil].strip().upper()
            if any(cod in texto_contabil for cod in CODIGOS_CONTA_APLICACAO):
                saldo_aplic = valor
            else:
                saldo_cc = valor
        else:
            # Cenário sem coluna contábil: 100% vai para Conta Corrente
            saldo_cc = valor

        registros.append(
            RegistroSIAFIC(
                fonte_arquivo=filename,
                tipo_relatorio="013083",
                conta_original=conta_bruta,
                chave_7d=chave_7d,
                chave_7d_sem_dv=chave_7d_sem_dv,
                descricao=descricao,
                saldo_cc=saldo_cc,
                saldo_aplic=saldo_aplic,
                rendimento=Decimal("0.00"),
            )
        )

    if logger:
        logger.info(filename, f"Relatório 013083 processado: {len(registros)} registros válidos.")

    return registros
