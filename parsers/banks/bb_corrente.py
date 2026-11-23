"""
parsers/banks/bb_corrente.py
Leitor do Extrato de Conta Corrente do Banco do Brasil.
"""

import re
from decimal import Decimal
from core.account_key import normalize_account_keys
from core.models import RegistroBanco
from parsers.banks.base import BaseBankParser, extract_money_tokens, normalize_pdf_text


def _extrair_agencia_conta(text: str) -> tuple[str, str]:
    """Extrai Agência e Conta Corrente aceitando quebras de linha, pipes ou dois-pontos."""
    ag_match = re.search(
        r"Ag[êe]ncia\s*[:\|\s]*([\d\-]+)",
        text,
        re.IGNORECASE,
    )
    cc_match = re.search(
        r"Conta(?:\s+corrente)?\s*[:\|\s]*([\d\.\-X]+)",
        text,
        re.IGNORECASE,
    )
    if not cc_match:
        cc_match = re.search(
            r"\b(295717-5|\d{5,9}-[\dX])\b",
            text,
            re.IGNORECASE,
        )

    agencia = ag_match.group(1).strip() if ag_match else ""
    conta_orig = cc_match.group(1).strip() if cc_match else ""
    return agencia, conta_orig


def _extrair_saldo_final(text: str, filename: str) -> tuple[Decimal, list[str]]:
    """
    Busca o saldo final na última linha de lançamentos com 'SALDO'
    (priorizando datas 30/ ou 31/ e ignorando 'Saldo Anterior' e cabeçalhos).
    """
    observacoes: list[str] = []
    lines = text.splitlines()
    norm = normalize_pdf_text(text)

    candidatos_fim_mes: list[Decimal] = []
    candidatos_saldo: list[Decimal] = []

    for idx, line in enumerate(lines):
        upper_line = line.upper()
        if not re.search(r"\bSALDO\b", upper_line):
            continue
        if any(ign in upper_line for ign in ("ANTERIOR", "BLOQUEADO", "DISPON")):
            continue

        vals_linha = extract_money_tokens(line)
        janela = " ".join(lines[idx : min(len(lines), idx + 4)])
        vals_janela = extract_money_tokens(janela)

        tem_data = bool(re.search(r"\b\d{2}/\d{2}/\d{4}\b", line)) or (
            idx > 0 and bool(re.search(r"\b\d{2}/\d{2}/\d{4}\b", lines[idx - 1]))
        )
        if not vals_linha and not tem_data:
            continue

        vals = vals_linha if vals_linha else vals_janela
        if not vals:
            continue

        contexto = f"{lines[idx - 1] if idx > 0 else ''} {line} {janela}"
        if re.search(r"\b(?:30|31)/\d{2}/\d{4}\b", contexto):
            candidatos_fim_mes.append(vals[-1])
        else:
            candidatos_saldo.append(vals[-1])

    if candidatos_fim_mes:
        return candidatos_fim_mes[-1], observacoes
    if candidatos_saldo:
        return candidatos_saldo[-1], observacoes

    ant_lines = [
        line for line in lines
        if "SALDO ANTERIOR" in normalize_pdf_text(line)
        and bool(extract_money_tokens(line))
    ]
    if ant_lines and ("NAO FOI MOVIMENTADA" in norm or "SEM MOVIMENTACAO" in norm):
        observacoes.append(
            "Conta sem movimentação no período: utilizado o 'Saldo Anterior' como saldo final."
        )
        return extract_money_tokens(ant_lines[-1])[-1], observacoes

    if "NAO FOI MOVIMENTADA" in norm or "SEM MOVIMENTACAO" in norm:
        observacoes.append(
            "Conta sem movimentação e sem linha de saldo numérico: assumido R$ 0,00."
        )
        return Decimal("0.00"), observacoes

    raise ValueError(f"Não foi possível localizar um valor de 'SALDO' em '{filename}'.")


class BBCorrenteParser(BaseBankParser):
    def can_parse(self, text: str) -> bool:
        norm = normalize_pdf_text(text)
        return (
            "EXTRATO DE CONTA CORRENTE" in norm
            and ("BANCO DO BRASIL" in norm or "AUTOATENDIMENTO.BB.COM.BR" in norm)
        )

    def parse(self, text: str, filename: str) -> list[RegistroBanco]:
        agencia, conta_orig = _extrair_agencia_conta(text)
        chave_7d, chave_7d_sem_dv = normalize_account_keys(conta_orig)
        saldo_final, observacoes = _extrair_saldo_final(text, filename)

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
