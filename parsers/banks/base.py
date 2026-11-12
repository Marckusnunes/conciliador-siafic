"""
parsers/banks/base.py
Contrato base e funções auxiliares para todos os leitores de extratos PDF.
"""

import re
import unicodedata
from abc import ABC, abstractmethod
from decimal import Decimal

from core.models import RegistroBanco
from core.money import parse_brl_decimal

# Padrão que encontra valores monetários como:
# '5.799,72 C' | '6.63 C' | '-2.547.456,25' | '38.767,80C'
MONEY_TOKEN_RE = re.compile(
    r"-?\d{1,3}(?:[\.,]\d{3})*[\.,]\d{2}\s*[CD]?\b|-?\d+[\.,]\d{2}\s*[CD]?\b",
    re.IGNORECASE,
)


def normalize_pdf_text(text: str) -> str:
    """
    Remove acentos e espaços duplicados para facilitar a identificação do banco.
    Exemplo: 'Resumo  do  Mês' vira 'RESUMO DO MES'.
    """
    nfkd = unicodedata.normalize("NFKD", text)
    sem_acentos = "".join(c for c in nfkd if not unicodedata.combining(c))
    return re.sub(r"\s+", " ", sem_acentos).upper().strip()


def extract_money_tokens(text_line: str) -> list[Decimal]:
    """Procura todos os valores em dinheiro numa linha e devolve em Decimal exato."""
    tokens = MONEY_TOKEN_RE.findall(text_line)
    return [parse_brl_decimal(tok) for tok in tokens]


class BaseBankParser(ABC):
    """Modelo padrão que cada especialista bancário precisa seguir."""

    @abstractmethod
    def can_parse(self, text: str) -> bool:
        """Retorna True se o texto do PDF pertencer a este banco/layout."""

    @abstractmethod
    def parse(self, text: str, filename: str) -> list[RegistroBanco]:
        """Extrai os dados financeiros do PDF e devolve na ficha RegistroBanco."""
