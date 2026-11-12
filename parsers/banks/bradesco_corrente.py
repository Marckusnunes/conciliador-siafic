"""
parsers/banks/bradesco_corrente.py
Leitor do Extrato Mensal / Por Período do Bradesco Net Empresa.
"""

import re
from decimal import Decimal
from core.account_key import normalize_account_keys
from core.models import RegistroBanco
from parsers.banks.base import BaseBankParser, extract_money_tokens


class BradescoCorrenteParser(BaseBankParser):
    def can_parse(self, text: str) -> bool:
        upper = text.upper()
        return "BRADESCO" in upper and "NET EMPRESA" in upper

    def parse(self, text: str, filename: str) -> list[RegistroBanco]:
        observacoes: list[str] = []

        # 1. Verifica se existe bloqueio judicial informado no quadro superior
        bloq_match = re.search(
            r"\b\d{4,5}\s*\|?\s*\d{5,9}-\d\s*\|?\s*[\d\.,]+\s*\|?\s*([\d\.,]+)\s*\|?\s*[\d\.,]+",
            text,
        )
        if bloq_match:
            vals_cabecalho = extract_money_tokens(bloq_match.group(0))
            if len(vals_cabecalho) >= 2 and vals_cabecalho[1] > Decimal("0.00"):
                observacoes.append(
                    f"Aviso Bradesco: Consta bloqueio judicial de R$ {vals_cabecalho[1]:,.2f} na data de emissão."
                )

        # 2. Corta o texto antes de 'Últimos Lançamentos' para ignorar movimentações futuras
        texto_mes = re.split(
            r"Os dados acima t[êe]m como base|Últimos Lançamentos",
            text,
            flags=re.IGNORECASE,
        )[0]

        acc_match = re.search(r"\b(\d{4,5})\s*\|?\s*(\d{5,9}-\d)\b", texto_mes)
        agencia = acc_match.group(1) if acc_match else ""
        conta_orig = acc_match.group(2) if acc_match else ""
        chave_7d, chave_7d_sem_dv = normalize_account_keys(conta_orig)

        # 3. Localiza a linha 'Total' do período e extrai o último valor (Saldo)
        total_lines = [
            line for line in texto_mes.splitlines()
            if re.match(r"^\s*Total\b", line.strip(), re.IGNORECASE)
        ]
        if not total_lines:
            raise ValueError(f"Linha 'Total' do período não encontrada em '{filename}'.")

        valores = extract_money_tokens(total_lines[-1])
        if not valores:
            raise ValueError(f"Saldo final ilegível na linha 'Total' de '{filename}'.")

        return [
            RegistroBanco(
                fonte_arquivo=filename,
                banco="BRADESCO",
                tipo_conta="CC",
                agencia=agencia,
                conta_original=conta_orig,
                chave_7d=chave_7d,
                chave_7d_sem_dv=chave_7d_sem_dv,
                saldo_cc=valores[-1],
                observacoes_auditoria=observacoes,
            )
        ]
