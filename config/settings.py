"""
config/settings.py
Centraliza as constantes, tolerâncias contábeis e termos de busca do sistema.
"""

from decimal import Decimal

# Diferença máxima (em reais) para considerar uma conta como "Conciliada"
TOLERANCIA_CENTAVOS = Decimal("0.01")

# Padrão de leitura dos relatórios CSV exportados do SIAFIC
CSV_ENCODING = "latin-1"
CSV_SEPARATOR = ";"

# Nomes possíveis para a coluna que identifica a conta bancária no SIAFIC
TERMOS_COLUNA_CONTA = (
    "domicílio bancário",
    "domicilio bancario",
    "conta",
    "nº conta",
    "no conta",
    "conta contabil",
    "conta contábil",
)

# Nomes possíveis para a coluna que traz o saldo final ou rendimento no SIAFIC
TERMOS_COLUNA_VALOR = (
    "saldo final",
    "saldo atual",
    "movimento",
    "valor da receita",
    "valor",
)

# Palavras que impedem uma coluna numérica de ser escolhida como Saldo Final
TERMOS_EXCLUSAO_VALOR = (
    "anterior",
    "inicial",
    "débito",
    "debito",
    "crédito",
    "credito",
)

# Palavras que identificam linhas de resumo/totalização que devem ser descartadas
TERMOS_LINHA_TOTAL = (
    "total",
    "total por domicílio",
    "total por domicilio",
    "subtotal",
)

# Termos na coluna 'Conta contábil' (relatório 013083) que identificam Aplicação Financeira
CODIGOS_CONTA_APLICACAO = ("1111150", "APLICA")
