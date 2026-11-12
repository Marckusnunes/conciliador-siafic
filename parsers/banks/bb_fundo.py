"""
parsers/banks/bb_fundo.py
Leitor do Extrato Mensal de Fundos de Investimento do Banco do Brasil.
"""

import re
from decimal import Decimal
from core.account_key import normalize_account_keys
from core.models import RegistroBanco
from parsers.banks.base import BaseBankParser, extract_money_tokens, normalize_pdf_text


class BBFundoParser(BaseBankParser):
    def can_parse(self, text: str) -> bool:
        norm = normalize_pdf_text(text)
        eh_bb = (
            "BANCO DO BRASIL" in norm
            or "AUTOATENDIMENTO.BB.COM.BR" in norm
            or "BB MILENIO" in norm
            or "BB RF" in norm
        )
        eh_fundo = (
            "INVESTIMENTOS FUNDOS" in norm
            or "FUNDOS - MENSAL" in norm
            or "RESUMO DO MES" in norm
            or "SALDO ATUAL =" in norm
        )
        return eh_bb and eh_fundo

    def parse(self, text: str, filename: str) -> list[RegistroBanco]:
        ag_match = re.search(r"Ag[êe]ncia\s*\|?\s*([\d\-]+)", text, re.IGNORECASE)
        cc_match = re.search(r"Conta\s*\|?\s*([\d\.\-X]+)", text, re.IGNORECASE)

        agencia = ag_match.group(1).strip() if ag_match else ""
        conta_orig = cc_match.group(1).strip() if cc_match else ""
        chave_7d, chave_7d_sem_dv = normalize_account_keys(conta_orig)

        # Isola a tabela inferior 'Resumo do mês' se ela existir no texto
        partes_resumo = re.split(r"Resumo\s+do\s+m[êe]s", text, flags=re.IGNORECASE)
        bloco = partes_resumo[-1] if len(partes_resumo) > 1 else text

        # Busca o Saldo Final ('Saldo Atual =' ou 'Saldo Atual')
        saldo_match = re.search(r"Saldo\s+Atual\s*=.*", bloco, re.IGNORECASE)
        if not saldo_match:
            saldo_match = re.search(r"Saldo\s+Atual.*", bloco, re.IGNORECASE)

        # Busca o Rendimento ('Rendimento Líquido' ou 'Rendimento Bruto')
        rend_match = re.search(r"Rendimento\s+L[íi]quido.*", bloco, re.IGNORECASE)
        if not rend_match:
            rend_match = re.search(r"Rendimento\s+Bruto.*", bloco, re.IGNORECASE)

        tokens_saldo = extract_money_tokens(saldo_match.group(0)) if saldo_match else []
        tokens_rend = extract_money_tokens(rend_match.group(0)) if rend_match else []

        saldo_aplic = tokens_saldo[-1] if tokens_saldo else Decimal("0.00")
        rendimento = tokens_rend[-1] if tokens_rend else Decimal("0.00")

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
