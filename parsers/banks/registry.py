"""
parsers/banks/registry.py
Roteador inteligente que usa a seleção do usuário (Banco + Tipo) e os leitores especializados.
"""

import io
import re
from decimal import Decimal
import pdfplumber

from core.account_key import normalize_account_keys
from core.audit_logger import AuditLogger
from core.models import RegistroBanco
from parsers.banks.base import BaseBankParser, extract_money_tokens, normalize_pdf_text
from parsers.banks.bb_corrente import BBCorrenteParser
from parsers.banks.bb_fundo import BBFundoParser
from parsers.banks.bb_poupanca import BBPoupancaParser
from parsers.banks.bradesco_corrente import BradescoCorrenteParser
from parsers.banks.caixa_fundo import CaixaFundoParser
from parsers.banks.caixa_govconta import CaixaGovContaParser


def get_default_parsers() -> list[BaseBankParser]:
    """Lista de todos os especialistas bancários ativos no sistema."""
    return [
        BBCorrenteParser(),
        BBFundoParser(),
        BBPoupancaParser(),
        CaixaGovContaParser(),
        CaixaFundoParser(),
        BradescoCorrenteParser(),
    ]


def extract_raw_pdf_text(file_bytes: bytes) -> str:
    """Extrai todo o texto bruto de um arquivo PDF."""
    with pdfplumber.open(io.BytesIO(file_bytes)) as pdf:
        return "\n".join(page.extract_text() or "" for page in pdf.pages)


def _fallback_parse_by_hint(
    text: str,
    filename: str,
    banco_hint: str,
    tipo_hint: str,
) -> RegistroBanco:
    """
    Leitor de contingência caso um PDF do banco tenha título diferente,
    aproveitando o Banco e o Tipo (CC ou INV) já apontados pelo usuário na tela.
    """
    ag_match = re.search(r"Ag[êe]ncia\s*[:\|]?\s*([\d\-]+)", text, re.IGNORECASE)
    cc_match = re.search(r"Conta(?:\s+corrente)?\s*[:\|]?\s*([\d\.\-\/X]+)", text, re.IGNORECASE)

    agencia = ag_match.group(1).strip() if ag_match else ""
    conta_orig = cc_match.group(1).strip() if cc_match else ""

    if not conta_orig:
        m_solto = re.search(r"\b(\d{4,12}-[\dX])\b", text, re.IGNORECASE)
        if m_solto:
            conta_orig = m_solto.group(1)

    chave_7d, chave_7d_sem_dv = normalize_account_keys(conta_orig)
    if not chave_7d:
        raise ValueError(f"Não foi possível identificar o número da conta em '{filename}'.")

    saldo_final = Decimal("0.00")
    rendimento_total = Decimal("0.00")

    for line in text.splitlines():
        norm_line = normalize_pdf_text(line)
        if any(ign in norm_line for ign in ("ANTERIOR", "BLOQUEADO", "DISPON", "RENTABILIDADE")):
            continue
        if any(g in norm_line for g in ("SALDO ATUAL", "SALDO FINAL", "SALDO TOTAL", "SALDO BRUTO", "SALDO")):
            vals = extract_money_tokens(line)
            if vals:
                saldo_final = vals[0] if "SALDO BRUTO" in norm_line else vals[-1]

    if tipo_hint == "INV":
        for line in text.splitlines():
            norm_line = normalize_pdf_text(line)
            if "ACUMULADO" in norm_line or "ANO" in norm_line:
                continue
            if any(g in norm_line for g in ("RENDIMENTO LIQUIDO", "RENDIMENTO BRUTO", "RENDIMENTO NO MES")):
                vals = extract_money_tokens(line)
                if vals:
                    rendimento_total = vals[0] if "BRUTO NO MES" in norm_line else vals[-1]
                    break
            if re.search(r"REAJ\.?\s*MON\.?\s*BC", norm_line) or re.search(r"\bJUROS\b", norm_line):
                vals = extract_money_tokens(line)
                if vals:
                    rendimento_total += vals[-1]

    return RegistroBanco(
        fonte_arquivo=filename,
        banco=banco_hint,
        tipo_conta="APLICACAO" if tipo_hint == "INV" else "CC",
        agencia=agencia,
        conta_original=conta_orig,
        chave_7d=chave_7d,
        chave_7d_sem_dv=chave_7d_sem_dv,
        saldo_cc=saldo_final if tipo_hint == "CC" else Decimal("0.00"),
        saldo_aplic=saldo_final if tipo_hint == "INV" else Decimal("0.00"),
        rendimento=rendimento_total if tipo_hint == "INV" else Decimal("0.00"),
        observacoes_auditoria=[
            f"Leitura realizada pelo modo assistido ({banco_hint} - {tipo_hint})."
        ],
    )


def parse_bank_pdf(
    file_bytes: bytes,
    filename: str,
    logger: AuditLogger | None = None,
    banco_hint: str | None = None,
    tipo_hint: str | None = None,
) -> list[RegistroBanco]:
    """Lê o texto do PDF usando os especialistas e, se necessário, o modo assistido."""
    full_text = extract_raw_pdf_text(file_bytes)

    if not full_text.strip():
        raise ValueError(
            f"O PDF '{filename}' não possui texto selecionável (pode ser imagem escaneada)."
        )

    registros: list[RegistroBanco] | None = None

    for parser in get_default_parsers():
        if parser.can_parse(full_text):
            registros = parser.parse(full_text, filename)
            break

    # Se nenhum parser rígido reconheceu o título, usa o Banco + Tipo apontados na tela:
    if registros is None and banco_hint and tipo_hint:
        registros = [_fallback_parse_by_hint(full_text, filename, banco_hint, tipo_hint)]

    if registros is not None:
        if logger:
            for reg in registros:
                logger.info(
                    filename,
                    f"Extrato lido: {reg.banco} ({reg.tipo_conta}) | "
                    f"Conta: {reg.conta_original} -> Chave: {reg.chave_7d}",
                )
                for obs in reg.observacoes_auditoria:
                    logger.alerta(filename, obs)
        return registros

    amostra = " ".join(full_text.split())[:180]
    raise ValueError(
        f"Layout bancário não reconhecido no arquivo '{filename}'. "
        f"Trecho inicial lido do PDF: [{amostra}...]"
    )
