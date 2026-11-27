"""Padrão ABNT do curso para relatórios em Word (.docx) e PDF.

Equivale à pasta _extensions/Professor-Weslley/pi-abnt do modelo do professor, que faz o
mesmo papel no Quarto. Não edite os arquivos desta pasta: o conteúdo do relatório fica no
relatorio_pi.md, e as figuras, tabelas e números, em relatorio/figuras.py, tabelas.py e valores.py.
"""
from .markdown import ErroRelatorio  # noqa: F401
from .padrao import (COR_DESTAQUE, COR_NEUTRA, COR_PRINCIPAL, PALETA, aplicar_padrao, eixo_br,  # noqa: F401
                     moeda_br, numero_br, percentual_br)
from .tabela import TabelaABNT, tabela_abnt  # noqa: F401
