"""
parsers/siafic/reader.py
Leitor genérico e seguro para relatórios CSV exportados do SIAFIC.
"""

import io
import pandas as pd

from config.settings import (
    CSV_ENCODING,
    CSV_SEPARATOR,
    TERMOS_COLUNA_CONTA,
    TERMOS_COLUNA_VALOR,
    TERMOS_EXCLUSAO_VALOR,
    TERMOS_LINHA_TOTAL,
)
from core.audit_logger import AuditLogger


def read_siafic_csv(
    file_bytes: bytes,
    filename: str,
    logger: AuditLogger | None = None,
) -> tuple[pd.DataFrame, dict[str, str | None]]:
    """
    Lê os bytes de um arquivo CSV do SIAFIC, valida o layout e devolve:
      1. Uma tabela (DataFrame) limpa, sem subcabeçalhos repetidos nem linhas de Total.
      2. Um dicionário indicando o nome exato de cada coluna encontrada.
    """
    # 1. Decodifica o texto usando o padrão de sistemas governamentais (latin-1)
    text = file_bytes.decode(CSV_ENCODING, errors="replace")
    lines = text.splitlines()

    if not lines:
        raise ValueError(f"O arquivo '{filename}' está vazio.")

    # 2. Procura o cabeçalho nas primeiras 5 linhas (de cima para baixo)
    header_idx = None
    max_scan = min(5, len(lines))

    for idx in range(max_scan):
        cols = [c.strip().lower() for c in lines[idx].split(CSV_SEPARATOR)]
        has_conta = any(any(t in c for t in TERMOS_COLUNA_CONTA) for c in cols)
        has_valor = any(
            any(t in c for t in TERMOS_COLUNA_VALOR)
            and not any(ex in c for ex in TERMOS_EXCLUSAO_VALOR)
            for c in cols
        )
        if has_conta and has_valor:
            header_idx = idx
            break

    if header_idx is None:
        raise ValueError(
            f"Layout incompatível em '{filename}': não foram encontradas colunas "
            f"obrigatórias de Conta e Valor nas primeiras {max_scan} linhas."
        )

    # 3. Lê todas as colunas como texto puro (dtype=str) para não perder zeros à esquerda
    df = pd.read_csv(
        io.StringIO(text),
        sep=CSV_SEPARATOR,
        header=header_idx,
        dtype=str,
        keep_default_na=False,
    )
    df.columns = [str(c).strip() for c in df.columns]

    # 4. Identifica colunas (prioriza 'Domicílio bancário' se existir mais de uma coluna de conta)
    col_domicilio = next(
        (c for c in df.columns if "domicílio bancário" in c.lower() or "domicilio bancario" in c.lower()),
        None,
    )
    col_conta = col_domicilio or next(
        c for c in df.columns
        if any(t in c.lower() for t in TERMOS_COLUNA_CONTA)
    )
    col_valor = next(
        c for c in df.columns
        if any(t in c.lower() for t in TERMOS_COLUNA_VALOR)
        and not any(ex in c.lower() for ex in TERMOS_EXCLUSAO_VALOR)
    )
    col_desc = next(
        (c for c in df.columns if c != col_conta and ("descri" in c.lower() or "nome" in c.lower())),
        None,
    )
    col_contabil = next(
        (c for c in df.columns if "contábil" in c.lower() or "contabil" in c.lower()),
        None,
    )

    # 5. Limpa linhas inválidas: subcabeçalhos repetidos e linhas de Totalização
    clean_rows = []
    ignored_totals = 0

    for _, row in df.iterrows():
        val_conta = row[col_conta].strip()

        # Ignora linhas vazias ou linha seguinte que repete o título da coluna
        if not val_conta or val_conta.lower() == col_conta.lower():
            continue

        # Ignora linhas de resumo ('Total', 'Total por Domicílio Bancário', 'Subtotal')
        row_cells = [str(v).strip().lower() for v in row.values]
        is_total_row = any(
            any(cell == tot or cell.startswith(f"{tot} ") for tot in TERMOS_LINHA_TOTAL)
            for cell in row_cells
        )
        if is_total_row:
            ignored_totals += 1
            continue

        clean_rows.append(row)

    if logger:
        logger.info(
            filename,
            f"CSV lido com sucesso (cabeçalho na linha {header_idx + 1}). "
            f"Linhas válidas: {len(clean_rows)} | Linhas de total ignoradas: {ignored_totals}.",
        )

    df_clean = pd.DataFrame(clean_rows, columns=df.columns)
    metadata = {
        "col_conta": col_conta,
        "col_valor": col_valor,
        "col_desc": col_desc,
        "col_contabil": col_contabil,
    }
    return df_clean, metadata
