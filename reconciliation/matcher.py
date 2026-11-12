"""
reconciliation/matcher.py
Realiza o pareamento determinístico em cascata entre SIAFIC e Bancos.
"""

from typing import Any


def match_accounts(
    siafic_map: dict[str, dict[str, Any]],
    banco_map: dict[str, dict[str, Any]],
) -> list[dict[str, Any]]:
    """
    Cruza as contas consolidadas do SIAFIC com as dos Bancos em ordem de prioridade:
      1. Chave exata de 7 dígitos (incluindo contas já vinculadas via De-Para)
      2. Fallback pela chave de 7 dígitos sem o dígito verificador (DV)
      3. Contas sem correspondência (apenas no SIAFIC ou apenas no Banco)
    """
    pares: list[dict[str, Any]] = []
    bancos_pareados: set[str] = set()

    # Índice auxiliar para busca rápida sem dígito verificador
    indice_sem_dv: dict[str, list[str]] = {}
    for chave_b, dados_b in banco_map.items():
        c_sem_dv = dados_b["chave_7d_sem_dv"]
        if c_sem_dv:
            indice_sem_dv.setdefault(c_sem_dv, []).append(chave_b)

    # 1. Percorre todas as contas do SIAFIC tentando encontrar o par no Banco
    for chave_s, dados_s in siafic_map.items():
        # Tentativa A: Match exato pela chave de 7 dígitos (ou De-Para)
        if chave_s in banco_map and chave_s not in bancos_pareados:
            dados_b = banco_map[chave_s]
            bancos_pareados.add(chave_s)
            metodo = "Via De-Para" if (dados_s["usou_de_para"] or dados_b["usou_de_para"]) else "Chave 7d Exata"
            pares.append({
                "chave": chave_s,
                "metodo": metodo,
                "siafic": dados_s,
                "banco": dados_b,
                "alertas_match": [],
            })
            continue

        # Tentativa B: Fallback ignorando o dígito verificador (DV)
        c_sem_dv = dados_s["chave_7d_sem_dv"]
        candidatos = [c for c in indice_sem_dv.get(c_sem_dv, []) if c not in bancos_pareados]

        if len(candidatos) == 1:
            chave_b_encontrada = candidatos[0]
            dados_b = banco_map[chave_b_encontrada]
            bancos_pareados.add(chave_b_encontrada)
            pares.append({
                "chave": chave_s,
                "metodo": "Chave 7d (sem DV)",
                "siafic": dados_s,
                "banco": dados_b,
                "alertas_match": [
                    f"Pareamento realizado ignorando dígito verificador (SIAFIC: {chave_s} <-> Banco: {chave_b_encontrada})."
                ],
            })
            continue

        # Tentativa C: Consta apenas no SIAFIC (não localizado nos extratos enviados)
        pares.append({
            "chave": chave_s,
            "metodo": "Sem correspondência",
            "siafic": dados_s,
            "banco": None,
            "alertas_match": [],
        })

    # 2. Adiciona as contas que vieram nos PDFs bancários mas não existem no SIAFIC
    for chave_b, dados_b in banco_map.items():
        if chave_b not in bancos_pareados:
            pares.append({
                "chave": chave_b,
                "metodo": "Sem correspondência",
                "siafic": None,
                "banco": dados_b,
                "alertas_match": [],
            })

    return pares
