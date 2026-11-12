"""
parsers/banks/caixa_fundo.py
Leitor do Extrato de Fundo de Investimento da Caixa Econômica Federal.
"""

import re
from decimal import Decimal
from core.account_key import normalize_account_keys
from core.models import RegistroBanco
from parsers.banks.base import BaseBankParser, extract_money_tokens


class CaixaFundoParser(BaseBankParser):
    def can_parse(self, text: str) -> bool:
        upper = text.upper()
        return (
            "CAIXA" in upper
            and "EXTRATO FUNDO DE INVESTIMENTO" in upper
            and "RESUMO DA MOVIMENTAÇÃO" in upper
        )

    def parse(self, text: str, filename: str) -> list[RegistroBanco]:
        # Isola a conta (ex: 3703.000574428355-9) ignorando o CNPJ colado à esquerda
        acc_match = re.search(r"\b(\d{4})\.(\d{9,12}-\s*\d)\b", text)
        agencia = acc_match.group(1) if acc_match else ""
        conta_orig = re.sub(r"\s+", "", acc_match.group(2)) if acc_match else ""
        chave_7d, chave_7d_sem_dv = normalize_account_keys(conta_orig)

        resumo = re.split(r"Resumo da Movimenta[çc][ãa]o", text, flags=re.IGNORECASE)[-1]

        saldo_match = re.search(r"Saldo Bruto\*.*", resumo, re.IGNORECASE)
        rend_bruto_match = re.search(r"Rendimento Bruto no M[êe]s.*", resumo, re.IGNORECASE)
        irrf_match = re.search(r"\bIRRF\b.*", resumo, re.IGNORECASE)
        iof_match = re.search(r"\bIOF\b.*", resumo, re.IGNORECASE)

        # Em 'Saldo Bruto*', o 1º número é o valor em R$ (o 2º é quantidade de cotas)
        saldo_aplic = extract_money_tokens(saldo_match.group(0))[0] if saldo_match else Decimal("0.00")
        rend_bruto = extract_money_tokens(rend_bruto_match.group(0))[0] if rend_bruto_match else Decimal("0.00")
        irrf = extract_money_tokens(irrf_match.group(0))[0] if irrf_match else Decimal("0.00")
        iof = extract_money_tokens(iof_match.group(0))[0] if iof_match else Decimal("0.00")

        rendimento_liquido = rend_bruto - abs(irrf) - abs(iof)

        return [
            RegistroBanco(
                fonte_arquivo=filename,
                banco="CAIXA",
                tipo_conta="APLICACAO",
                agencia=agencia,
                conta_original=conta_orig,
                chave_7d=chave_7d,
                chave_7d_sem_dv=chave_7d_sem_dv,
                saldo_aplic=saldo_aplic,
                rendimento=rendimento_liquido,
            )
        ]
