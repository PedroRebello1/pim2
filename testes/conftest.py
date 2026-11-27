"""Configuração dos testes (python -m pytest, na raiz do repositório).

O relatório (relatorio/) e o motor (solucao_pim2/motor_cobranca/) são scripts que importam seus
módulos pela própria pasta; aqui essas pastas entram no caminho de importação.
"""
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
for pasta in (RAIZ / "relatorio", RAIZ / "solucao_pim2" / "motor_cobranca", Path(__file__).resolve().parent):
    if str(pasta) not in sys.path:
        sys.path.insert(0, str(pasta))
