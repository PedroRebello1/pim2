"""Leitura dos exports e construção dos atributos de cada tentativa de cobrança.

Os exports são reconhecidos pelo cabeçalho, não pelo nome do arquivo: basta colocar novos
arquivos na pasta (mais meses de transações, por exemplo) e rodar de novo. Arquivos do mesmo
tipo são concatenados e deduplicados.
"""
import unicodedata
from pathlib import Path

import numpy as np
import openpyxl
import pandas as pd

TIPOS = {"codigoRetorno": "transacoes", "Cod.Parcela": "parcelas", "Mat. cliente": "acessos"}
FAIXAS_DIA = [0, 4, 7, 9, 14, 16, 19, 24, 31]
ROTULOS_DIA = ["1-4", "5-7", "8-9", "10-14", "15-16", "17-19", "20-24", "25-31"]


def _tipo_e_cabecalho(caminho):
    if caminho.stat().st_size < 100:  # exports que falharam vêm com 2 bytes
        return None, None
    wb = openpyxl.load_workbook(caminho, read_only=True)
    for i, linha in enumerate(wb.worksheets[0].iter_rows(max_row=5, values_only=True)):
        for chave, tipo in TIPOS.items():
            if chave in [str(c) for c in linha]:
                return tipo, i
    return None, None


def carregar_exports(pasta):
    """Retorna {tipo: DataFrame} com tudo o que for reconhecido na pasta."""
    partes = {}
    for arq in sorted(Path(pasta).glob("*.xls*")):
        tipo, cab = _tipo_e_cabecalho(arq)
        if tipo:
            partes.setdefault(tipo, []).append(pd.read_excel(arq, header=cab, dtype=str))
    out = {k: pd.concat(v, ignore_index=True) for k, v in partes.items()}
    if "transacoes" in out:
        t = out["transacoes"]
        t = t.loc[:, [c for c in t.columns if c and not str(c).startswith("Unnamed")]].drop_duplicates("transacao")
        t["valor"] = pd.to_numeric(t["valor"], errors="coerce")
        t["data"] = pd.to_datetime(t["data"], format="%d/%m/%Y %H:%M:%S", errors="coerce")
        out["transacoes"] = t.dropna(subset=["data"])
    if "parcelas" in out:
        p = out["parcelas"].drop_duplicates("Cod.Parcela")
        p["Valor"] = pd.to_numeric(p["Valor"].str.replace(".", "", regex=False).str.replace(",", ".", regex=False), errors="coerce")
        for c in ["Vencimento", "Pagamento"]:
            p[c] = pd.to_datetime(p[c], format="%d/%m/%Y", errors="coerce")
        out["parcelas"] = p
    return out


def _norm(s):
    s = unicodedata.normalize("NFKD", str(s)).encode("ascii", "ignore").decode().upper()
    return " ".join(s.replace(".", " ").split())


def atributos_tentativas(t):
    """Uma linha por tentativa, com atributos conhecidos ANTES da tentativa (sem vazamento)."""
    t = t.copy()
    t["ok"] = (t["codigoRetorno"] == "00").astype(int)
    t["cartao_id"] = t["cartao"] + "|" + t["titular"].map(_norm)
    t = t.sort_values(["cartao_id", "data"]).reset_index(drop=True)
    g = t.groupby("cartao_id")
    t["ult_cod"] = g["codigoRetorno"].shift().fillna("nenhum")
    t["dias_desde_ult"] = (t["data"] - g["data"].shift()).dt.days.clip(upper=31).fillna(31)
    # falhas consecutivas imediatamente antes desta tentativa
    reset = (t["ok"] == 1).astype(int)
    bloco = reset.groupby(t["cartao_id"]).cumsum() - reset  # o bloco muda só DEPOIS de uma aprovação
    falha = 1 - t["ok"]
    t["seq_falhas"] = falha.groupby([t["cartao_id"], bloco]).cumsum() - falha
    t.loc[t["ult_cod"] == "nenhum", "seq_falhas"] = 0
    t["ja_aprovou"] = (g["ok"].cumsum() - t["ok"] > 0).astype(int)
    t["mes"] = t["data"].dt.to_period("M")
    t["n_tent_mes"] = t.groupby(["cartao_id", "mes"]).cumcount() + 1
    t["dia"] = t["data"].dt.day
    t["faixa_dia"] = pd.cut(t["dia"], FAIXAS_DIA, labels=ROTULOS_DIA).astype(str)
    t["bandeira"] = t["cartao"].str[0]
    t["bin"] = t["cartao"].str[:6]
    t["duas_parcelas"] = (t["qtd_parcelas"] == "2").astype(int)
    t["log_valor"] = np.log(t["valor"])
    # decisão relevante = re-tentar depois de uma recusa
    t["retentativa"] = (t["ult_cod"] != "nenhum") & (t["ult_cod"] != "00") & (t["seq_falhas"] >= 1)
    return t
