"""
core/models.py
Define as estruturas de dados padronizadas (Dataclasses) que trafegam entre os módulos.
"""

from dataclasses import dataclass, field
from decimal import Decimal

from core.account_key import (
    format_banco_agencia_conta_banco,
    format_banco_agencia_conta_siafic,
)


@dataclass
class RegistroSIAFIC:
    """Ficha padronizada para cada linha lida dos relatórios CSV do SIAFIC."""
    fonte_arquivo: str
    tipo_relatorio: str          # '013083' (Saldos) ou '014387' (Rendimentos)
    conta_original: str
    chave_7d: str                # Últimos 7 dígitos com dígito verificador
    chave_7d_sem_dv: str         # Últimos 7 dígitos ignorando o dígito verificador
    descricao: str = ""
    saldo_cc: Decimal = Decimal("0.00")
    saldo_aplic: Decimal = Decimal("0.00")
    rendimento: Decimal = Decimal("0.00")
    conta_completa: str = ""     # Formato Banco-Agência-Conta (ex: 001-2234-2956241)

    def __post_init__(self) -> None:
        if not self.conta_completa and self.chave_7d:
            self.conta_completa = format_banco_agencia_conta_siafic(
                self.conta_original, self.chave_7d
            )


@dataclass
class RegistroBanco:
    """Ficha padronizada para cada dado extraído de um extrato bancário PDF."""
    fonte_arquivo: str
    banco: str                   # 'BB', 'CAIXA' ou 'BRADESCO'
    tipo_conta: str              # 'CC', 'APLICACAO' ou 'POUPANCA'
    agencia: str
    conta_original: str
    chave_7d: str
    chave_7d_sem_dv: str
    saldo_cc: Decimal = Decimal("0.00")
    saldo_aplic: Decimal = Decimal("0.00")
    rendimento: Decimal = Decimal("0.00")
    observacoes_auditoria: list[str] = field(default_factory=list)
    conta_completa: str = ""     # Formato Banco-Agência-Conta (ex: 001-2234-2956241)

    def __post_init__(self) -> None:
        if not self.conta_completa and self.chave_7d:
            self.conta_completa = format_banco_agencia_conta_banco(
                self.banco, self.agencia, self.chave_7d
            )


@dataclass
class ResultadoConciliacao:
    """Ficha final que mostra lado a lado o SIAFIC e o Banco após o cruzamento."""
    chave_conciliacao: str
    metodo_pareamento: str       # Ex: 'Chave 7d', 'De-Para', 'Chave 7d (sem DV)'
    banco: str
    descricao: str
    siafic_cc: Decimal
    banco_cc: Decimal
    dif_cc: Decimal
    siafic_aplic: Decimal
    banco_aplic: Decimal
    dif_aplic: Decimal
    siafic_rend: Decimal
    banco_rend: Decimal
    dif_rend: Decimal
    status: str                  # 'Conciliado', 'Divergência de Saldo', etc.
    alertas: list[str] = field(default_factory=list)
    conta_completa: str = ""     # Formato Banco-Agência-Conta (ex: 001-2234-2956241)
