"""
core/audit_logger.py
Registra eventos, alertas e metadados para a Trilha de Auditoria do sistema.
"""

from dataclasses import dataclass, field
from datetime import datetime


@dataclass
class AuditEvent:
    """Representa uma linha individual no relatório de auditoria."""
    timestamp: str
    nivel: str        # 'INFO', 'ALERTA' ou 'ERRO'
    origem: str       # Nome do arquivo ou etapa
    mensagem: str


@dataclass
class AuditLogger:
    """Armazena toda a sequência de acontecimentos durante uma conciliação."""
    eventos: list[AuditEvent] = field(default_factory=list)

    def _add(self, nivel: str, origem: str, mensagem: str) -> None:
        agora = datetime.now().strftime("%d/%m/%Y %H:%M:%S")
        self.eventos.append(
            AuditEvent(timestamp=agora, nivel=nivel, origem=origem, mensagem=mensagem)
        )

    def info(self, origem: str, mensagem: str) -> None:
        self._add("INFO", origem, mensagem)

    def alerta(self, origem: str, mensagem: str) -> None:
        self._add("ALERTA", origem, mensagem)

    def erro(self, origem: str, mensagem: str) -> None:
        self._add("ERRO", origem, mensagem)
