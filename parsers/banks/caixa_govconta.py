"""
parsers/banks/caixa_govconta.py
Leitor do Extrato Individualizado / GovConta da Caixa Econômica Federal.
"""

import re
from core.account_key import normalize_account_keys
from core.models import RegistroBanco
from parsers.banks.base import BaseBankParser, extract_money_tokens


class CaixaGovContaParser(BaseBankParser):
    def can_parse(self, text: str) -> bool:
        upper = text.upper()
        return "CAIXA" in upper and "EXTRATO INDIVIDUALIZADO" in upper

    def parse(self, text: str, filename: str) -> list[RegistroBanco]:
        # Localiza o padrão da conta no cabeçalho (ex: 4064 3709 000574174759-7)
        acc_match = re.search(r"\b(\d{4})\s+\d{4}\s+(\d{9,12}-\d)\b", text)
        agencia = acc_match.group(1) if acc_match else ""
        conta_orig = acc_match.group(2) if acc_match else ""
        chave_7d, chave_7d_sem_dv = normalize_account_keys(conta_orig)

        # Captura todas as linhas 'SALDO TOTAL' e pega exclusivamente a última ocorrência
        saldo_lines = [line for line in text.splitlines() if "SALDO TOTAL" in line.upper()]
        if not saldo_lines:
            raise ValueError(f"Nenhuma linha 'SALDO TOTAL' encontrada em '{filename}'.")

        valores = extract_money_tokens(saldo_lines[-1])
        if not valores:
            raise ValueError(f"Saldo final ilegível em '{filename}'.")

        return [
            RegistroBanco(
                fonte_arquivo=filename,
                banco="CAIXA",
                tipo_conta="CC",
                agencia=agencia,
                conta_original=conta_orig,
                chave_7d=chave_7d,
                chave_7d_sem_dv=chave_7d_sem_dv,
                saldo_cc=valores[-1],
            )
        ]
