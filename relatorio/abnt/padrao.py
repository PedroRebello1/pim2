"""
padrao.py — Padrão visual único para gráficos e números do Projeto Integrador.

Todos os relatórios importam este arquivo, assim os gráficos ficam iguais
independentemente de quem fez a análise. NÃO altere cores ou fontes aqui;
se precisar de algo diferente, fale com o professor.

Uso no .qmd:
    from padrao import *
    aplicar_padrao()
"""
import matplotlib as mpl
import matplotlib.pyplot as plt
from matplotlib.ticker import FuncFormatter
import pandas as pd

# Paleta institucional (5 cores, amigável a daltônicos). Use na ordem.
PALETA = ["#1F4E79", "#C55A11", "#548235", "#7F6000", "#7030A0"]
COR_PRINCIPAL = PALETA[0]
COR_DESTAQUE = PALETA[1]
COR_NEUTRA = "#7F7F7F"


def aplicar_padrao():
    """Aplica fonte, tamanhos, cores e resolução padrão aos gráficos."""
    mpl.rcParams.update({
        "font.family": "serif",
        "font.serif": ["Times New Roman", "Times", "DejaVu Serif"],
        "font.size": 10,
        "axes.titlesize": 10,
        "axes.labelsize": 10,
        "xtick.labelsize": 9,
        "ytick.labelsize": 9,
        "legend.fontsize": 9,
        "legend.frameon": False,
        "axes.prop_cycle": mpl.cycler(color=PALETA),
        "axes.spines.top": False,
        "axes.spines.right": False,
        "axes.grid": True,
        "axes.grid.axis": "y",
        "grid.color": "#D9D9D9",
        "grid.linewidth": 0.6,
        "axes.axisbelow": True,
        # 16 cm de largura = largura útil da página A4 com margens ABNT
        "figure.figsize": (6.3, 3.4),
        "figure.dpi": 150,
        "savefig.dpi": 300,
        "savefig.bbox": "tight",
    })
    pd.set_option("display.float_format", lambda v: numero_br(v, 2))
    pd.set_option("display.max_columns", 20)


def numero_br(valor, casas=0):
    """1234.5 -> '1.234,50' (separadores brasileiros)."""
    texto = f"{valor:,.{casas}f}"
    return texto.replace(",", "X").replace(".", ",").replace("X", ".")


def moeda_br(valor, casas=2):
    """1234.5 -> 'R$ 1.234,50'."""
    return "R$ " + numero_br(valor, casas)


def percentual_br(valor, casas=1):
    """0.153 -> '15,3%'."""
    return numero_br(valor * 100, casas) + "%"


def tabela_abnt(df, nomes=None, casas=2):
    """Converte um DataFrame numa tabela para o relatório (padrão ABNT).

    Use num chunk Python com as opções:
        #| label: tbl-alguma-coisa
        #| tbl-cap: "Título da tabela"
        #| results: asis
    e termine o chunk com: print(tabela_abnt(minha_tabela))

    nomes: dicionário {coluna: "Cabeçalho"} para renomear colunas.
    casas: casas decimais dos números (um número para todas as colunas,
           ou um dicionário {coluna: casas}). Inteiros saem sem casas.
    Números saem no padrão brasileiro (1.234,56), alinhados à direita.
    """
    nomes = nomes or {}
    colunas = list(df.columns)

    def casas_de(col):
        return casas.get(col, 2) if isinstance(casas, dict) else casas

    def celula(valor, col):
        if pd.isna(valor):
            return "–"
        if isinstance(valor, (bool,)):
            return "Sim" if valor else "Não"
        if pd.api.types.is_integer(valor):
            return numero_br(valor, 0)
        if pd.api.types.is_float(valor):
            return numero_br(valor, casas_de(col))
        return str(valor).replace("|", "\\|")

    numericas = {c: pd.api.types.is_numeric_dtype(df[c]) and not pd.api.types.is_bool_dtype(df[c])
                 for c in colunas}
    cabecalho = "| " + " | ".join(str(nomes.get(c, c)) for c in colunas) + " |"
    alinhamento = "|" + "|".join("---:" if numericas[c] else ":---" for c in colunas) + "|"
    linhas = ["| " + " | ".join(celula(v, c) for c, v in zip(colunas, reg)) + " |"
              for reg in df.itertuples(index=False, name=None)]
    return "\n" + "\n".join([cabecalho, alinhamento] + linhas) + "\n"


def eixo_br(ax, eixo="y", casas=0, formato="numero"):
    """Formata os rótulos de um eixo no padrão brasileiro.

    formato: 'numero', 'moeda' ou 'percentual'.
    """
    funcs = {"numero": numero_br, "moeda": moeda_br, "percentual": percentual_br}
    f = FuncFormatter(lambda v, _: funcs[formato](v, casas))
    (ax.yaxis if eixo == "y" else ax.xaxis).set_major_formatter(f)
    return ax
