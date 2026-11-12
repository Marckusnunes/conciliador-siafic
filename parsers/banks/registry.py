"""
parsers/banks/registry.py
Roteador que identifica automaticamente o layout do PDF bancário enviado.
"""

import io
import pdfplumber

from core.audit_logger import AuditLogger
from core.models import RegistroBanco
from parsers.banks.base import BaseBankParser
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


def parse_bank_pdf(
    file_bytes: bytes,
    filename: str,
    logger: AuditLogger | None = None,
) -> list[RegistroBanco]:
    """Lê o texto do PDF e aciona o especialista correspondente."""
    full_text = extract_raw_pdf_text(file_bytes)

    if not full_text.strip():
        raise ValueError(
            f"O PDF '{filename}' não possui texto selecionável (pode ser imagem escaneada)."
        )

    for parser in get_default_parsers():
        if parser.can_parse(full_text):
            registros = parser.parse(full_text, filename)
            if logger:
                for reg in registros:
                    logger.info(
                        filename,
                        f"Extrato identificado: {reg.banco} ({reg.tipo_conta}) | "
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
