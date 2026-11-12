"""
parsers/banks/bb_corrente.py
Leitor do Extrato de Conta Corrente do Banco do Brasil.
"""

import re
from core.account_key import normalize_account_keys
from core.models import RegistroBanco
from parsers.banks.base import BaseBankParser, extract_money_tokens


class BBCorrenteParser(BaseBankParser):
    def can_parse(self, text: str) -> bool:
        upper = text.upper()
        return "EXTRATO DE CONTA CORRENTE" in upper and "BANCO DO BRASIL" in upper

    def parse(self, text: str, filename: str) -> list[RegistroBanco]:
        ag_match = re.search(r"Ag[êe]ncia\s*\|?\s*([\d\-]+)", text, re.IGNORECASE)
        cc_match = re.search(r"Conta corrente\s*\|?\s*([\d\-X]+)", text, re.IGNORECASE)

        agencia = ag_match.group(1).strip() if ag_match else ""
        conta_orig = cc_match.group(1).strip() if cc_match else ""
        chave_7d, chave_7d_sem_dv = normalize_account_keys(conta_orig)

        # Procura a última linha iniciada ou marcada com SALDO (ignora 'Saldo Anterior')
        saldo_lines = [
            line for line in text.splitlines()
            if re.search(r"\bSALDO\b", line) and "ANTERIOR" not in line.upper()
        ]
        if not saldo_lines:
            raise ValueError(f"Não foi possível localizar a linha 'SALDO' em '{filename}'.")

        valores = extract_money_tokens(saldo_lines[-1])
        if not valores:
            raise ValueError(f"Valor de saldo ilegível em '{filename}'.")

        return [
            RegistroBanco(
                fonte_arquivo=filename,
                banco="BB",
                tipo_conta="CC",
                agencia=agencia,
                conta_original=conta_orig,
                chave_7d=chave_7d,
                chave_7d_sem_dv=chave_7d_sem_dv,
                saldo_cc=valores[-1],
            )
        ]
