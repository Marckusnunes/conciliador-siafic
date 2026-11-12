"""
parsers/banks/bb_corrente.py
Leitor do Extrato de Conta Corrente do Banco do Brasil.
"""

import re
from core.account_key import normalize_account_keys
from core.models import RegistroBanco
from parsers.banks.base import BaseBankParser, extract_money_tokens, normalize_pdf_text


class BBCorrenteParser(BaseBankParser):
    def can_parse(self, text: str) -> bool:
        norm = normalize_pdf_text(text)
        return (
            "EXTRATO DE CONTA CORRENTE" in norm
            and ("BANCO DO BRASIL" in norm or "AUTOATENDIMENTO.BB.COM.BR" in norm)
        )

    def parse(self, text: str, filename: str) -> list[RegistroBanco]:
        ag_match = re.search(r"Ag[êe]ncia\s*\|?\s*([\d\-]+)", text, re.IGNORECASE)
        cc_match = re.search(r"Conta\s+corrente\s*\|?\s*([\d\.\-X]+)", text, re.IGNORECASE)

        agencia = ag_match.group(1).strip() if ag_match else ""
        conta_orig = cc_match.group(1).strip() if cc_match else ""
        chave_7d, chave_7d_sem_dv = normalize_account_keys(conta_orig)

        observacoes: list[str] = []

        # 1. Busca linhas com 'SALDO' (aceita maiúsculas ou minúsculas e ignora 'Saldo Anterior')
        saldo_lines = [
            line for line in text.splitlines()
            if re.search(r"\bSALDO\b", line, re.IGNORECASE)
            and "ANTERIOR" not in line.upper()
            and "BLOQUEADO" not in line.upper()
            and "DISPON" not in line.upper()
        ]

        # 2. Caso especial: conta sem movimentação que só mostra 'Saldo Anterior'
        if not saldo_lines:
            norm = normalize_pdf_text(text)
            ant_lines = [
                line for line in text.splitlines()
                if "SALDO ANTERIOR" in normalize_pdf_text(line)
            ]
            if ant_lines and ("NAO FOI MOVIMENTADA" in norm or "SEM MOVIMENTACAO" in norm):
                saldo_lines = ant_lines
                observacoes.append(
                    "Conta sem movimentação no período: utilizado o 'Saldo Anterior' como saldo final."
                )

        if not saldo_lines:
            raise ValueError(f"Não foi possível localizar a linha 'SALDO' em '{filename}'.")

        valores = extract_money_tokens(saldo_lines[-1])
        if not valores:
            raise ValueError(
                f"Valor de saldo ilegível na linha '{saldo_lines[-1].strip()}' em '{filename}'."
            )

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
                observacoes_auditoria=observacoes,
            )
        ]
