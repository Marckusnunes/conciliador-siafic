"""
reconciliation/consolidator.py
Agrupa registros individuais do SIAFIC e dos Bancos em tabelas consolidadas por conta.
"""

from decimal import Decimal
from typing import Any

from core.account_key import format_banco_agencia_conta_banco, format_banco_agencia_conta_siafic
from core.models import RegistroBanco, RegistroSIAFIC


def consolidate_siafic(
    registros: list[RegistroSIAFIC],
    mapa_de_para: dict[str, str],
) -> dict[str, dict[str, Any]]:
    """
    Agrupa todas as linhas dos relatórios 013083 e 014387 por chave de conta.
    """
    consolidado: dict[str, dict[str, Any]] = {}

    for reg in registros:
        chave_final = mapa_de_para.get(reg.chave_7d, reg.chave_7d)
        usou_de_para = reg.chave_7d in mapa_de_para
        bac = format_banco_agencia_conta_siafic(reg.conta_original, chave_final)

        if chave_final not in consolidado:
            consolidado[chave_final] = {
                "chave_7d": chave_final,
                "chave_7d_sem_dv": reg.chave_7d_sem_dv,
                "conta_completa": bac,
                "descricao": reg.descricao,
                "saldo_cc": Decimal("0.00"),
                "saldo_aplic": Decimal("0.00"),
                "rendimento": Decimal("0.00"),
                "usou_de_para": usou_de_para,
                "fontes": set(),
            }

        item = consolidado[chave_final]
        if ("-" not in item.get("conta_completa", "")) and "-" in bac:
            item["conta_completa"] = bac
        if not item["descricao"] and reg.descricao:
            item["descricao"] = reg.descricao

        item["saldo_cc"] += reg.saldo_cc
        item["saldo_aplic"] += reg.saldo_aplic
        item["rendimento"] += reg.rendimento
        item["usou_de_para"] = item["usou_de_para"] or usou_de_para
        item["fontes"].add(reg.fonte_arquivo)

    return consolidado


def consolidate_bancos(
    registros: list[RegistroBanco],
    mapa_de_para: dict[str, str],
) -> dict[str, dict[str, Any]]:
    """
    Agrupa todos os extratos bancários PDF por chave de conta.
    """
    consolidado: dict[str, dict[str, Any]] = {}

    for reg in registros:
        chave_final = mapa_de_para.get(reg.chave_7d, reg.chave_7d)
        usou_de_para = reg.chave_7d in mapa_de_para
        bac = format_banco_agencia_conta_banco(reg.banco, reg.agencia, chave_final)

        if chave_final not in consolidado:
            consolidado[chave_final] = {
                "chave_7d": chave_final,
                "chave_7d_sem_dv": reg.chave_7d_sem_dv,
                "conta_completa": bac,
                "bancos": set(),
                "tipos_conta": set(),
                "saldo_cc": Decimal("0.00"),
                "saldo_aplic": Decimal("0.00"),
                "rendimento": Decimal("0.00"),
                "usou_de_para": usou_de_para,
                "alertas": [],
                "fontes": set(),
            }

        item = consolidado[chave_final]
        if ("-" not in item.get("conta_completa", "")) and "-" in bac:
            item["conta_completa"] = bac
        item["bancos"].add(reg.banco)
        item["tipos_conta"].add(reg.tipo_conta)
        item["saldo_cc"] += reg.saldo_cc
        item["saldo_aplic"] += reg.saldo_aplic
        item["rendimento"] += reg.rendimento
        item["usou_de_para"] = item["usou_de_para"] or usou_de_para
        item["alertas"].extend(reg.observacoes_auditoria)
        item["fontes"].add(reg.fonte_arquivo)

    return consolidado
