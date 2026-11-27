"""Dados sintéticos para os testes: tentativas de cobrança inventadas, no mesmo formato do export de
transações da academia. Nenhum dado real: titulares, cartões e valores são gerados aqui.

Três perfis de cartão, para que o motor tenha o que aprender:
- "bom": aprova quase sempre na 1ª tentativa do mês;
- "saldo": recusa com o código 51 (saldo insuficiente) e aprova mais nos dias 10 a 14; a chance cai
  a cada recusa seguida, o que cria um teto de falhas;
- "morto": recusa sempre com um código irreversível (05 ou Pac014).
"""
from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

COLUNAS = ["transacao", "data", "valor", "codigoRetorno", "cartao", "titular", "qtd_parcelas"]


def transacoes_sinteticas(n_cartoes: int = 240, inicio: str = "2026-08-15", fim: str = "2026-10-15",
                          semente: int = 7) -> pd.DataFrame:
    """Tentativas de cobrança com as colunas do export (data como texto dd/mm/aaaa hh:mm:ss)."""
    rng = np.random.default_rng(semente)
    ini, fim_ = pd.Timestamp(inicio), pd.Timestamp(fim)
    linhas = []
    for k in range(n_cartoes):
        perfil = rng.choice(["bom", "saldo", "morto"], p=[0.55, 0.33, 0.12])
        cartao = f"{rng.choice(['4', '5'])}{rng.integers(10000, 99999)}******{rng.integers(1000, 9999)}"
        titular = f"Titular Sintético {k:04d}"
        valor = float(rng.choice([99.9, 169.9, 209.9]))
        parcelas = "2" if rng.random() < 0.1 else "1"
        dia_cobranca = int(rng.integers(1, 28))
        codigo_morto = str(rng.choice(["05", "Pac014"]))
        seguidas = 0                                   # recusas seguidas do cartão (atravessa os meses)
        for mes in pd.period_range(ini, fim_, freq="M"):
            d = mes.start_time + pd.Timedelta(days=dia_cobranca - 1)
            ultimo_dia = min(mes.end_time.normalize(), fim_)
            n = 0
            while d <= ultimo_dia:
                if d < ini:
                    d += pd.Timedelta(days=1)
                    continue
                n += 1
                if perfil == "bom":
                    p = 0.92 if n == 1 else 0.5
                elif perfil == "saldo":
                    p = (0.45 if 10 <= d.day <= 14 else 0.15) * 0.45 ** max(0, seguidas - 1)
                else:
                    p = 0.0
                ok = rng.random() < p
                seguidas = 0 if ok else seguidas + 1
                codigo = "00" if ok else (codigo_morto if perfil == "morto" else "51")
                hora = d + pd.Timedelta(hours=12, seconds=int(rng.integers(0, 3600)))
                linhas.append({"transacao": f"T{len(linhas) + 1:06d}", "data": hora.strftime("%d/%m/%Y %H:%M:%S"),
                               "valor": valor, "codigoRetorno": codigo, "cartao": cartao, "titular": titular,
                               "qtd_parcelas": parcelas})
                if ok:
                    break
                d += pd.Timedelta(days=int(rng.integers(1, 4)))
    return pd.DataFrame(linhas, columns=COLUNAS)


def preparar(df: pd.DataFrame) -> pd.DataFrame:
    """Converte como o carregador do motor faz (valor numérico e data em datetime)."""
    t = df.copy()
    t["valor"] = pd.to_numeric(t["valor"])
    t["data"] = pd.to_datetime(t["data"], format="%d/%m/%Y %H:%M:%S")
    return t


def salvar_xlsx(df: pd.DataFrame, caminho: Path, titulo: str = "Relatório de transações (sintético)"):
    """Grava como o sistema exporta: uma linha de título e o cabeçalho na 2ª linha."""
    import openpyxl
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.append([titulo])
    ws.append(list(df.columns))
    for linha in df.itertuples(index=False, name=None):
        ws.append([str(v) for v in linha])
    wb.save(caminho)
