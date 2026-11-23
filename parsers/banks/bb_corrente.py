"""
parsers/banks/bb_corrente.py
Leitor do Extrato de Conta Corrente do Banco do Brasil.
"""

import re
from decimal import Decimal
from core.account_key import normalize_account_keys
from core.models import RegistroBanco
from parsers.banks.base import BaseBankParser, extract_money_tokens, normalize_pdf_text

_RE_SALDO = re.compile(r"\bS\s*A\s*L\s*D\s*O\b", re.IGNORECASE)
_RE_ANTERIOR = re.compile(r"A\s*N\s*T\s*E\s*R\s*I\s*O\s*R", re.IGNORECASE)


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
            r"\b(\d{4,9}-[\dX])\b",
            text,
            re.IGNORECASE,
        )

    agencia = ag_match.group(1).strip() if ag_match else ""
    conta_orig = cc_match.group(1).strip() if cc_match else ""
    return agencia, conta_orig


def _extrair_saldo_bb(text: str, filename: str) -> tuple[Decimal, list[str]]:
    """
    Busca o saldo final na linha 'SALDO' ou 'S A L D O' (olhando também as linhas
    logo abaixo caso o valor venha quebrado), com fallback para 'Saldo Anterior' ou sem movimento.
    """
    observacoes: list[str] = []
    lines = text.splitlines()
    norm = normalize_pdf_text(text)

    candidatos_fim_mes: list[Decimal] = []
    candidatos_saldo: list[Decimal] = []

    for idx, line in enumerate(lines):
        upper_line = line.upper()
        if not _RE_SALDO.search(upper_line):
            continue
        if _RE_ANTERIOR.search(upper_line) or "BLOQUEADO" in upper_line or "DISPON" in upper_line:
            continue

        bloco = " ".join(lines[idx : min(len(lines), idx + 4)])
        valores = extract_money_tokens(line) or extract_money_tokens(bloco)
        if not valores:
            continue

        contexto = f"{lines[idx - 1] if idx > 0 else ''} {bloco}"
        if re.search(r"\b(?:30|31)/\d{2}/\d{4}\b", contexto):
            candidatos_fim_mes.append(valores[-1])
        else:
            candidatos_saldo.append(valores[-1])

    if candidatos_fim_mes:
        return candidatos_fim_mes[-1], observacoes

    if candidatos_saldo:
        return candidatos_saldo[-1], observacoes

    ant_lines = [
        line for line in lines
        if "SALDO ANTERIOR" in normalize_pdf_text(line)
        and bool(extract_money_tokens(line))
    ]
    if ant_lines:
        observacoes.append(
            "Linha final 'SALDO' não localizada: utilizado o 'Saldo Anterior' como referência."
        )
        return extract_money_tokens(ant_lines[-1])[-1], observacoes

    if any(k in norm for k in ("NAO FOI MOVIMENTADA", "SEM MOVIMENTACAO", "NAO HOUVE MOVIMENTACAO")):
        observacoes.append(
            "Conta sem movimentação e sem linha numérica de saldo: assumido R$ 0,00."
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
        saldo_final, observacoes = _extrair_saldo_bb(text, filename)

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
