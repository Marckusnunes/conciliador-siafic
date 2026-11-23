"""
parsers/banks/bb_corrente.py
Leitor do Extrato de Conta Corrente do Banco do Brasil.
"""

import re
from decimal import Decimal
from core.account_key import normalize_account_keys
from core.models import RegistroBanco
from parsers.banks.base import BaseBankParser, extract_money_tokens, normalize_pdf_text


def _extrair_agencia_conta_bb(text: str) -> tuple[str, str]:
    """Extrai Agência e Conta Corrente mesmo com quebras de linha ou pipes."""
    ag_match = re.search(r"Ag[êe]ncia\s*[\r\n\s\|:]*([\d\-]+)", text, re.IGNORECASE)
    cc_match = re.search(
        r"Conta\s+corrente\s*[\r\n\s\|:]*([\d\.\-X]+)", text, re.IGNORECASE
    )
    if not cc_match:
        cc_match = re.search(
            r"Conta\s*[\r\n\s\|:]*([\d\.\-X]{4,})", text, re.IGNORECASE
        )

    agencia = ag_match.group(1).strip() if ag_match else ""
    conta_orig = cc_match.group(1).strip() if cc_match else ""
    return agencia, conta_orig


def _extrair_saldo_final_bb(text: str) -> tuple[Decimal, list[str]]:
    """
    Localiza o saldo final na última linha de lançamentos com 'SALDO'
    (priorizando datas 30/ ou 31/ e ignorando 'Saldo Anterior' e cabeçalhos).
    """
    observacoes: list[str] = []
    lines = text.splitlines()
    norm_full = normalize_pdf_text(text)

    candidatos_fim_mes: list[Decimal] = []
    candidatos_saldo: list[Decimal] = []

    for idx, line in enumerate(lines):
        upper_line = line.upper()
        if not re.search(r"\bSALDO\b", upper_line):
            continue
        if any(ign in upper_line for ign in ("ANTERIOR", "BLOQUEADO", "DISPON")):
            continue

        # Ignora a linha isolada do cabeçalho da tabela ("| Saldo") sem valores numéricos
        bloco_janela = " ".join(lines[idx : min(len(lines), idx + 5)])
        valores_janela = extract_money_tokens(bloco_janela)
        valores_linha = extract_money_tokens(line)

        # Se a linha não tem número próprio e não é um lançamento (sem data na linha ou na anterior),
        # provavelmente é apenas o título da coluna "Saldo".
        tem_data = bool(re.search(r"\b\d{2}/\d{2}/\d{4}\b", line)) or (
            idx > 0 and bool(re.search(r"\b\d{2}/\d{2}/\d{4}\b", lines[idx - 1]))
        )
        if not valores_linha and not tem_data:
            continue

        vals = valores_linha if valores_linha else valores_janela
        if not vals:
            continue

        contexto_data = f"{lines[idx - 1] if idx > 0 else ''} {line} {bloco_janela}"
        eh_fim_mes = bool(re.search(r"\b(?:30|31)/\d{2}/\d{4}\b", contexto_data))

        if eh_fim_mes:
            candidatos_fim_mes.append(vals[-1])
        else:
            candidatos_saldo.append(vals[-1])

    if candidatos_fim_mes:
        return candidatos_fim_mes[-1], observacoes

    if candidatos_saldo:
        return candidatos_saldo[-1], observacoes

    # Fallback para conta sem movimentação que exibe apenas 'Saldo Anterior'
    for idx, line in enumerate(lines):
        if "SALDO ANTERIOR" in normalize_pdf_text(line):
            bloco_ant = " ".join(lines[idx : min(len(lines), idx + 4)])
            vals_ant = extract_money_tokens(bloco_ant)
            if vals_ant:
                observacoes.append(
                    "Conta sem movimentação no período: utilizado o 'Saldo Anterior' como saldo final."
                )
                return vals_ant[-1], observacoes

    if "NAO FOI MOVIMENTADA" in norm_full or "SEM MOVIMENTACAO" in norm_full:
        observacoes.append(
            "Conta sem movimentação e sem linha de saldo numérico: assumido R$ 0,00."
        )
        return Decimal("0.00"), observacoes

    raise ValueError("Não foi possível localizar um valor de 'SALDO' válido no extrato BB.")


class BBCorrenteParser(BaseBankParser):
    def can_parse(self, text: str) -> bool:
        norm = normalize_pdf_text(text)
        return "EXTRATO DE CONTA CORRENTE" in norm and (
            "BANCO DO BRASIL" in norm or "AUTOATENDIMENTO.BB.COM.BR" in norm
        )

    def parse(self, text: str, filename: str) -> list[RegistroBanco]:
        agencia, conta_orig = _extrair_agencia_conta_bb(text)
        chave_7d, chave_7d_sem_dv = normalize_account_keys(conta_orig)
        saldo_final, observacoes = _extrair_saldo_final_bb(text)

        return [
            RegistroBanco(
                fonte_arquivo=filename,
                banco="BB",
                tipo_conta="CC",
                agencia=agencia,
                conta_original=conta_orig,
                chave_7d=chave_7d,
                chave_7d_sem_dv=chave_7d_sem_dv,
                saldo_cc=saldo_final,
                observacoes_auditoria=observacoes,
            )
        ]
