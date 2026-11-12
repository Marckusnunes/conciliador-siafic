"""
exporters/pdf_exporter.py
Gera relatório formal de conciliação bancária em PDF (A4 Paisagem).
"""

from datetime import datetime
from decimal import Decimal
from fpdf import FPDF

from core.models import ResultadoConciliacao


def _texto_seguro(texto: str, max_len: int = 45) -> str:
    """Garante compatibilidade com fontes padrão do PDF e limita textos longos."""
    limpo = (
        str(texto)
        .replace("—", "-")
        .replace("–", "-")
        .replace("•", "*")
        .encode("latin-1", errors="replace")
        .decode("latin-1")
    )
    if len(limpo) > max_len:
        return limpo[: max_len - 3] + "..."
    return limpo


def _fmt_moeda(valor: Decimal) -> str:
    """Formata valor Decimal como '1.234,56'."""
    texto = f"{valor:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    return texto


class _RelatorioPDF(FPDF):
    def __init__(self, titulo_relatorio: str):
        super().__init__(orientation="L", unit="mm", format="A4")
        self.titulo_relatorio = titulo_relatorio

    def header(self):
        self.set_font("Helvetica", "B", 13)
        self.cell(0, 8, _texto_seguro(self.titulo_relatorio, 90), border=0, align="L")
        self.ln(7)
        self.set_font("Helvetica", "", 8)
        emissao = datetime.now().strftime("%d/%m/%Y às %H:%M:%S")
        self.cell(0, 5, _texto_seguro(f"Emitido em: {emissao}", 90), border=0, align="L")
        self.ln(7)

    def footer(self):
        self.set_y(-12)
        self.set_font("Helvetica", "I", 8)
        self.cell(0, 8, f"Página {self.page_no()}/{{nb}}", align="R")


def export_to_pdf(
    resultados: list[ResultadoConciliacao],
    titulo: str = "Relatório de Conciliação Bancária - SIAFIC x Extratos",
) -> bytes:
    """Monta o PDF formal de conciliação e retorna seus bytes."""
    pdf = _RelatorioPDF(titulo_relatorio=titulo)
    pdf.alias_nb_pages()
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.add_page()

    # Bloco de Resumo Executivo
    total = len(resultados)
    conciliados = sum(1 for r in resultados if r.status == "Conciliado")
    divergentes = total - conciliados

    pdf.set_font("Helvetica", "B", 9)
    pdf.set_fill_color(240, 244, 248)
    resumo_txt = (
        f"Total de Contas: {total}   |   "
        f"Conciliadas: {conciliados}   |   "
        f"Com Divergência / Pendência: {divergentes}"
    )
    pdf.cell(0, 8, _texto_seguro(resumo_txt, 120), border=1, align="C", fill=True)
    pdf.ln(11)

    # Cabeçalho da Tabela (largura total = 277 mm na folha A4 paisagem)
    colunas = [
        ("Conta", 18),
        ("Banco/Tipo", 28),
        ("Descrição", 47),
        ("SIAFIC CC", 24),
        ("Banco CC", 24),
        ("Dif. CC", 22),
        ("SIAFIC Aplic", 25),
        ("Banco Aplic", 25),
        ("Dif. Rend", 22),
        ("Status", 42),
    ]

    pdf.set_font("Helvetica", "B", 7.5)
    pdf.set_fill_color(31, 78, 120)
    pdf.set_text_color(255, 255, 255)
    for nome_col, largura in colunas:
        pdf.cell(largura, 7, _texto_seguro(nome_col, 25), border=1, align="C", fill=True)
    pdf.ln()

    # Linhas de Dados
    pdf.set_font("Helvetica", "", 7)
    pdf.set_text_color(0, 0, 0)

    for r in resultados:
        if r.status == "Conciliado":
            pdf.set_fill_color(255, 255, 255)
        else:
            pdf.set_fill_color(252, 228, 214)

        valores_linha = [
            (r.chave_conciliacao, 18, "C"),
            (_texto_seguro(r.banco, 18), 28, "L"),
            (_texto_seguro(r.descricao, 30), 47, "L"),
            (_fmt_moeda(r.siafic_cc), 24, "R"),
            (_fmt_moeda(r.banco_cc), 24, "R"),
            (_fmt_moeda(r.dif_cc), 22, "R"),
            (_fmt_moeda(r.siafic_aplic), 25, "R"),
            (_fmt_moeda(r.banco_aplic), 25, "R"),
            (_fmt_moeda(r.dif_rend), 22, "R"),
            (_texto_seguro(r.status, 26), 42, "L"),
        ]

        for texto_cel, largura, alinhamento in valores_linha:
            pdf.cell(largura, 6, texto_cel, border=1, align=alinhamento, fill=True)
        pdf.ln()

    return bytes(pdf.output())
