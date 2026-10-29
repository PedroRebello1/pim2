"""Carrega os 3 exports do sistema da academia e grava um cache (pickle) FORA do repositório.

Uso: python 00_carregar.py <pasta_dos_xlsx> <pasta_cache>
O cache contém dados pessoais (nome, CPF, e-mail) -> nunca versionar.
"""
import sys
from pathlib import Path

import pandas as pd

SRC = Path(sys.argv[1])
CACHE = Path(sys.argv[2])
CACHE.mkdir(parents=True, exist_ok=True)


def brl(s):
    return pd.to_numeric(s.astype(str).str.replace(".", "", regex=False).str.replace(",", ".", regex=False), errors="coerce")


# --- Parcelas (relatório "Parcela em Aberto", filtro amplo) ---
p = pd.read_excel(SRC / "ParcelaEmAbertoRel-1792106356522.xlsx", dtype=str)
p["Valor"] = brl(p["Valor"])
for c in ["Faturamento", "Vencimento", "Pagamento"]:
    p[c] = pd.to_datetime(p[c], format="%d/%m/%Y", errors="coerce")
for c in ["Contrato", "Cod.Parcela"]:
    p[c] = pd.to_numeric(p[c], errors="coerce").astype("Int64")
p.to_pickle(CACHE / "parcelas.pkl")

# --- Acessos (catraca / reconhecimento facial) ---
a = pd.read_excel(SRC / "ListaAcessoRelCliente-564fb28d84ebc24b0a5a3899b1b3355b-1792106707566.xlsx", header=2, dtype={"Mat. cliente": str})
a["Data entrada"] = pd.to_datetime(a["Data entrada"], errors="coerce")
a.to_pickle(CACHE / "acessos.pkl")

# --- Transações de cartão (Cielo recorrência) ---
t = pd.read_excel(SRC / "1792107164615-1792107167701.xlsx", header=1, dtype=str)
t = t.loc[:, [c for c in t.columns if c and not str(c).startswith("Unnamed")]]
t["valor"] = pd.to_numeric(t["valor"], errors="coerce")
t["data"] = pd.to_datetime(t["data"], format="%d/%m/%Y %H:%M:%S", errors="coerce")
t.to_pickle(CACHE / "transacoes.pkl")

for nome, df in [("parcelas", p), ("acessos", a), ("transacoes", t)]:
    print(f"{nome}: {df.shape}")
