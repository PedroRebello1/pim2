"""Arquivos do projeto que alimentam o relatório.

Só agregados e identificadores pseudonimizados, todos versionados no repositório:
- saidas/: tabelas e log do estudo dos dados (gerados por scripts/03_analises.py);
- solucao_pim2/resultados/: métricas, políticas e fila do motor (gerados por solucao_pim2/motor_cobranca/rodar.py).

Os exports brutos da academia (com dados pessoais) não entram aqui. Caminhos sempre relativos
à raiz do repositório.
"""
from __future__ import annotations

import ast
import json
import re
from functools import lru_cache
from pathlib import Path

import pandas as pd

from abnt.markdown import ErroRelatorio

BASE = Path(__file__).resolve().parents[1]
SAIDAS = BASE / "saidas"
RESULTADOS = BASE / "solucao_pim2" / "resultados"


def _ler_csv(caminho: Path) -> pd.DataFrame:
    if not caminho.exists():
        raise ErroRelatorio(f"Arquivo de dados não encontrado: {caminho.relative_to(BASE)}")
    return pd.read_csv(caminho, encoding="utf-8-sig", dtype={"codigoRetorno": str, "ultimo_codigo": str,
                                                              "cartao": str})


@lru_cache(maxsize=None)
def _saidas(nome):
    return _ler_csv(SAIDAS / nome)


@lru_cache(maxsize=None)
def _resultados(nome):
    return _ler_csv(RESULTADOS / nome)


def saidas(nome: str) -> pd.DataFrame:
    """Tabela agregada do estudo (pasta saidas/)."""
    return _saidas(nome).copy()


def resultados(nome: str) -> pd.DataFrame:
    """Resultado do motor de cobrança (pasta solucao_pim2/resultados/)."""
    return _resultados(nome).copy()


@lru_cache(maxsize=None)
def metricas() -> dict:
    return json.loads((RESULTADOS / "metricas.json").read_text(encoding="utf-8"))


@lru_cache(maxsize=None)
def log_estudo() -> str:
    """Saída do scripts/03_analises.py (UTF-8; aceita também UTF-16 e cp1252, comuns no Windows)."""
    bruto = (SAIDAS / "log_03_analises.txt").read_bytes()
    if bruto[:2] in (b"\xff\xfe", b"\xfe\xff"):
        return bruto.decode("utf-16")
    try:
        return bruto.decode("utf-8-sig")
    except UnicodeDecodeError:
        return bruto.decode("cp1252")


def do_log(padrao: str, grupo: int = 1, tipo=float):
    """Lê um número do log do estudo (saidas/log_03_analises.txt) com uma expressão regular."""
    m = re.search(padrao, log_estudo())
    if not m:
        raise ErroRelatorio(f"Não achei no saidas/log_03_analises.txt o trecho: {padrao}")
    valor = m.group(grupo).replace(",", "")
    return tipo(valor)


def dict_do_log(prefixo: str) -> dict:
    """Lê um dicionário impresso no log, ex.: "situação: {'Pago': 18625, ...}"."""
    m = re.search(re.escape(prefixo) + r"\s*(\{.*?\})", log_estudo())
    if not m:
        raise ErroRelatorio(f"Não achei no saidas/log_03_analises.txt o dicionário: {prefixo}")
    texto = re.sub(r"Period\('([^']+)', '[A-Z]+'\)", r"'\1'", m.group(1))
    return ast.literal_eval(texto)
