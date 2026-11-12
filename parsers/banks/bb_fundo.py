"""
parsers/banks/bb_fundo.py
Leitor do Extrato Mensal de Fundos de Investimento do Banco do Brasil.
"""

import re
from decimal import Decimal
from core.account_key import normalize_account_keys
from core.models import RegistroBanco
from parsers.banks.base import BaseBankParser, extract_money_tokens


class BBFundoParser(BaseBankParser):
    def can_parse(self, text: str) -> bool:
        upper = text.upper()
        return "INVESTIMENTOS FUNDOS - MENSAL" in upper and "RESUMO DO MÊS" in upper

    def parse(self, text: str, filename: str) -> list[RegistroBanco]:
        ag_match = re.search(r"Ag[êe]ncia\s*\|?\s*([\d\-]+)", text, re.IGNORECASE)
        cc_match = re.search(r"Conta\s*\|?\s*([\d\-X]+)", text, re.IGNORECASE)

        agencia = ag_match.group(1).strip() if ag_match else ""
        conta_orig = cc_match.group(1).strip() if cc_match else ""
        chave_7d, chave_7d_sem_dv = normalize_account_keys(conta_orig)

        # Isola apenas a tabela inferior 'Resumo do mês' para maior segurança
        resumo = re.split(r"Resumo do m[êe]s", text, flags=re.IGNORECASE)[-1]

        saldo_match = re.search(r"Saldo Atual\s*=.*", resumo, re.IGNORECASE)
        rend_match = re.search(r"Rendimento L[íi]quido.*", resumo, re.IGNORECASE)

        saldo_aplic = extract_money_tokens(saldo_match.group(0))[-1] if saldo_match else Decimal("0.00")
        rendimento = extract_money_tokens(rend_match.group(0))[-1] if rend_match else Decimal("0.00")

        return [
            RegistroBanco(
                fonte_arquivo=filename,
                banco="BB",
                tipo_conta="APLICACAO",
                agencia=agencia,
                conta_original=conta_orig,
                chave_7d=chave_7d,
                chave_7d_sem_dv=chave_7d_sem_dv,
                saldo_aplic=saldo_aplic,
                rendimento=rendimento,
            )
        ]
