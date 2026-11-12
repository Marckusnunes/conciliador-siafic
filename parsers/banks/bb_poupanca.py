"""
parsers/banks/bb_poupanca.py
Leitor do Extrato de Poupança Ouro do Banco do Brasil.
"""

import re
from decimal import Decimal
from core.account_key import normalize_account_keys
from core.models import RegistroBanco
from parsers.banks.base import BaseBankParser, extract_money_tokens


class BBPoupancaParser(BaseBankParser):
    def can_parse(self, text: str) -> bool:
        upper = text.upper()
        return "CONSULTAS - POUPEX" in upper or "POUPANÇA-OURO" in upper

    def parse(self, text: str, filename: str) -> list[RegistroBanco]:
        ag_match = re.search(r"Ag[êe]ncia\s*\|?\s*([\d\-]+)", text, re.IGNORECASE)
        cc_match = re.search(r"Conta\s*\|?\s*([\d\-X]+)", text, re.IGNORECASE)

        agencia = ag_match.group(1).strip() if ag_match else ""
        conta_orig = cc_match.group(1).strip() if cc_match else ""
        chave_7d, chave_7d_sem_dv = normalize_account_keys(conta_orig)

        # Extrai o saldo final da linha iniciada por SALDO
        saldo_lines = [
            line for line in text.splitlines()
            if re.match(r"^\s*SALDO\b", line.strip())
        ]
        if not saldo_lines:
            raise ValueError(f"Linha 'SALDO' não encontrada na poupança '{filename}'.")

        saldo_aplic = extract_money_tokens(saldo_lines[-1])[-1]

        # Soma todas as rubricas de rendimento do mês (REAJ.MON. BC + JUROS)
        rendimento_total = Decimal("0.00")
        for line in text.splitlines():
            upper_line = line.upper()
            if "REAJ.MON. BC" in upper_line or re.search(r"\bJUROS\b", upper_line):
                vals = extract_money_tokens(line)
                if vals:
                    rendimento_total += vals[-1]

        return [
            RegistroBanco(
                fonte_arquivo=filename,
                banco="BB",
                tipo_conta="POUPANCA",
                agencia=agencia,
                conta_original=conta_orig,
                chave_7d=chave_7d,
                chave_7d_sem_dv=chave_7d_sem_dv,
                saldo_aplic=saldo_aplic,
                rendimento=rendimento_total,
            )
        ]
