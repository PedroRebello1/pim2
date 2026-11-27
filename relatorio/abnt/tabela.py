"""Tabela no padrão ABNT/IBGE para o Word, a partir de um DataFrame do pandas.

Uso em relatorio/tabelas.py (mesma ideia do tabela_abnt() do modelo do professor):

    return tabela_abnt(df, nomes={"col": "Cabeçalho"}, casas={"col": 1})

Números saem no padrão brasileiro (1.234,56) e alinhados à direita; textos à esquerda.
Faz parte do padrão: não edite.
"""
from __future__ import annotations

from dataclasses import dataclass, field

import pandas as pd

from .padrao import numero_br


@dataclass
class TabelaABNT:
    cabecalho: list[str]
    linhas: list[list[str]]
    alinhamentos: list[str]                     # 'esq', 'dir' ou 'centro', uma por coluna
    larguras: list[float] | None = None         # em cm; se None, calcula pelo conteúdo
    tamanho: float = 10                         # tamanho da letra (ABNT: menor que o texto)
    notas: list[str] = field(default_factory=list)


def tabela_abnt(df: pd.DataFrame, nomes: dict | None = None, casas: int | dict = 2,
                larguras: list[float] | None = None, alinhamentos: dict | None = None) -> TabelaABNT:
    """Converte um DataFrame numa tabela ABNT.

    nomes: {coluna: "Cabeçalho"}; casas: casas decimais (um número ou {coluna: casas});
    larguras: larguras das colunas em cm (opcional); alinhamentos: {coluna: 'esq'|'dir'|'centro'}.
    Textos podem usar **negrito** e *itálico*.
    """
    nomes, alinhamentos = nomes or {}, alinhamentos or {}
    colunas = list(df.columns)

    def casas_de(col):
        return casas.get(col, 2) if isinstance(casas, dict) else casas

    def celula(valor, col):
        if valor is None or (not isinstance(valor, str) and pd.isna(valor)):
            return "–"
        if isinstance(valor, bool):
            return "Sim" if valor else "Não"
        if pd.api.types.is_integer(valor):
            return numero_br(valor, 0)
        if pd.api.types.is_float(valor):
            return numero_br(valor, casas_de(col))
        return str(valor)

    numericas = {c: pd.api.types.is_numeric_dtype(df[c]) and not pd.api.types.is_bool_dtype(df[c]) for c in colunas}
    alin = [alinhamentos.get(c, "dir" if numericas[c] else "esq") for c in colunas]
    corpo = [[celula(v, c) for c, v in zip(colunas, reg)] for reg in df.itertuples(index=False, name=None)]
    return TabelaABNT([str(nomes.get(c, c)) for c in colunas], corpo, alin, larguras)
