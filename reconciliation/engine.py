"""
reconciliation/engine.py
Motor principal de conciliação: calcula diferenças e classifica divergências.
"""

from decimal import Decimal

from config.settings import TOLERANCIA_CENTAVOS
from core.audit_logger import AuditLogger
from core.models import RegistroBanco, RegistroSIAFIC, ResultadoConciliacao
from reconciliation.consolidator import consolidate_bancos, consolidate_siafic
from reconciliation.matcher import match_accounts


def _classificar_divergencia(
    dif_cc: Decimal,
    dif_aplic: Decimal,
    dif_rend: Decimal,
    tolerancia: Decimal,
) -> str:
    """Define o rótulo de status com base nas diferenças calculadas."""
    erros: list[str] = []

    if abs(dif_cc) > tolerancia:
        erros.append("CC")
    if abs(dif_aplic) > tolerancia:
        erros.append("Aplicação")
    if abs(dif_rend) > tolerancia:
        erros.append("Rendimento")

    if not erros:
        return "Conciliado"
    if len(erros) > 1:
        return f"Divergência Múltipla ({', '.join(erros)})"
    if erros[0] == "Rendimento":
        return "Divergência de Rendimento"
    return f"Divergência de Saldo ({erros[0]})"


def run_reconciliation(
    registros_siafic: list[RegistroSIAFIC],
    registros_bancos: list[RegistroBanco],
    mapa_de_para: dict[str, str] | None = None,
    tolerancia: Decimal = TOLERANCIA_CENTAVOS,
    logger: AuditLogger | None = None,
) -> list[ResultadoConciliacao]:
    """
    Executa todo o fluxo de conciliação contábil x bancária e retorna
    a lista ordenada de ResultadoConciliacao.
    """
    mapa = mapa_de_para or {}

    siafic_consolidado = consolidate_siafic(registros_siafic, mapa)
    bancos_consolidado = consolidate_bancos(registros_bancos, mapa)
    pares = match_accounts(siafic_consolidado, bancos_consolidado)

    resultados: list[ResultadoConciliacao] = []

    for par in pares:
        dados_s = par["siafic"]
        dados_b = par["banco"]
        alertas: list[str] = list(par["alertas_match"])

        # Caso 1: Conta existe apenas no SIAFIC
        if dados_s is not None and dados_b is None:
            resultados.append(
                ResultadoConciliacao(
                    chave_conciliacao=par["chave"],
                    metodo_pareamento=par["metodo"],
                    banco="Não identificado",
                    descricao=dados_s["descricao"] or par["chave"],
                    siafic_cc=dados_s["saldo_cc"],
                    banco_cc=Decimal("0.00"),
                    dif_cc=dados_s["saldo_cc"],
                    siafic_aplic=dados_s["saldo_aplic"],
                    banco_aplic=Decimal("0.00"),
                    dif_aplic=dados_s["saldo_aplic"],
                    siafic_rend=dados_s["rendimento"],
                    banco_rend=Decimal("0.00"),
                    dif_rend=dados_s["rendimento"],
                    status="Não Localizado no Banco",
                    alertas=alertas,
                )
            )
            continue

        # Caso 2: Conta existe apenas nos Extratos Bancários
        if dados_b is not None and dados_s is None:
            bancos_str = "/".join(sorted(dados_b["bancos"]))
            tipos_str = "+".join(sorted(dados_b["tipos_conta"]))
            alertas.extend(dados_b["alertas"])

            resultados.append(
                ResultadoConciliacao(
                    chave_conciliacao=par["chave"],
                    metodo_pareamento=par["metodo"],
                    banco=f"{bancos_str} ({tipos_str})",
                    descricao="Conta sem lançamento no SIAFIC",
                    siafic_cc=Decimal("0.00"),
                    banco_cc=dados_b["saldo_cc"],
                    dif_cc=-dados_b["saldo_cc"],
                    siafic_aplic=Decimal("0.00"),
                    banco_aplic=dados_b["saldo_aplic"],
                    dif_aplic=-dados_b["saldo_aplic"],
                    siafic_rend=Decimal("0.00"),
                    banco_rend=dados_b["rendimento"],
                    dif_rend=-dados_b["rendimento"],
                    status="Não Localizado no SIAFIC",
                    alertas=alertas,
                )
            )
            continue

        # Caso 3: Conta encontrada nos dois lados -> Calcula diferenças
        bancos_str = "/".join(sorted(dados_b["bancos"]))
        tipos_str = "+".join(sorted(dados_b["tipos_conta"]))
        alertas.extend(dados_b["alertas"])

        dif_cc = dados_s["saldo_cc"] - dados_b["saldo_cc"]
        dif_aplic = dados_s["saldo_aplic"] - dados_b["saldo_aplic"]
        dif_rend = dados_s["rendimento"] - dados_b["rendimento"]

        status = _classificar_divergencia(dif_cc, dif_aplic, dif_rend, tolerancia)

        resultados.append(
            ResultadoConciliacao(
                chave_conciliacao=par["chave"],
                metodo_pareamento=par["metodo"],
                banco=f"{bancos_str} ({tipos_str})",
                descricao=dados_s["descricao"] or par["chave"],
                siafic_cc=dados_s["saldo_cc"],
                banco_cc=dados_b["saldo_cc"],
                dif_cc=dif_cc,
                siafic_aplic=dados_s["saldo_aplic"],
                banco_aplic=dados_b["saldo_aplic"],
                dif_aplic=dif_aplic,
                siafic_rend=dados_s["rendimento"],
                banco_rend=dados_b["rendimento"],
                dif_rend=dif_rend,
                status=status,
                alertas=alertas,
            )
        )

    # Ordena o resultado pelo número da conta padronizada
    resultados.sort(key=lambda r: r.chave_conciliacao)

    if logger:
        total = len(resultados)
        conciliados = sum(1 for r in resultados if r.status == "Conciliado")
        logger.info(
            "Motor de Conciliação",
            f"Conciliação concluída: {total} contas analisadas | {conciliados} conciliadas | {total - conciliados} com divergência/pendência.",
        )

    return resultados
