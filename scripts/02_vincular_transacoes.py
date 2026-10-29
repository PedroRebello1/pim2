"""Vincula transações de cartão (Cielo) a matrículas.

O export de transações não tem matrícula, só nome do titular do cartão e cartão mascarado.
Estratégia em 2 passos:
 1. Âncora: transação APROVADA casa com parcela paga em CARTÃO RECORRENTE no mesmo dia e mesmo
    valor (soma do dia por matrícula, pois uma transação pode quitar 2 parcelas). Dentro de cada
    grupo dia+valor o pareamento é 1-para-1 (guloso pela maior similaridade de nome entre titular
    e Nome/Resp. Pgto). O titular muitas vezes é pai/mãe/cônjuge, então o nome só desempata.
 2. Propagação: o cartão (número mascarado + titular) herda a matrícula da âncora, o que liga
    também as tentativas RECUSADAS desse cartão.
Uso: python 02_vincular_transacoes.py <pasta_cache>
"""
import sys
import unicodedata
from difflib import SequenceMatcher
from pathlib import Path

import pandas as pd

CACHE = Path(sys.argv[1])
p = pd.read_pickle(CACHE / "parcelas.pkl")
t = pd.read_pickle(CACHE / "transacoes.pkl")


def norm(s):
    s = unicodedata.normalize("NFKD", str(s)).encode("ascii", "ignore").decode().upper()
    return " ".join(w for w in s.replace(".", " ").split() if w not in {"DE", "DA", "DO", "DOS", "DAS", "E"})


def sim(a, b):
    """Similaridade tolerante a abreviações: 1º nome, último sobrenome e iniciais do meio."""
    ta, tb = norm(a).split(), norm(b).split()
    if not ta or not tb:
        return 0.0
    first = ta[0] == tb[0]
    last = ta[-1] == tb[-1]
    meio = sum(any(x[0] == y[0] for y in tb[1:-1]) for x in ta[1:-1]) / max(1, len(ta) - 2)
    return 0.45 * first + 0.4 * last + 0.15 * meio + 0.1 * SequenceMatcher(None, " ".join(ta), " ".join(tb)).ratio()


t["ok"] = t["codigoRetorno"] == "00"
t["dia"] = t["data"].dt.normalize()
t["cartao_id"] = t["cartao"] + "|" + t["titular"].map(norm)
t["v"] = t["valor"].round(2)

rec = p[(p["Situação"] == "Pago") & (p["Forma Pgto"] == "CARTÃO RECORRENTE")]
dia_mat = rec.groupby(["Pagamento", "Matrícula"]).agg(valor=("Valor", "sum"), nome=("Nome", "first"),
                                                       resp=("Resp. Pgto", "first")).reset_index()
dia_mat["v"] = dia_mat["valor"].round(2)

anc = []
for (dia, v), grp in t[t["ok"]].groupby(["dia", "v"]):
    cand = dia_mat[(dia_mat["Pagamento"] == dia) & (dia_mat["v"] == v)]
    if cand.empty:
        continue
    pares = sorted(((max(sim(r["titular"], c["nome"]), sim(r["titular"], c["resp"])), i, j)
                    for i, (_, r) in enumerate(grp.iterrows()) for j, (_, c) in enumerate(cand.iterrows())),
                   reverse=True)
    usados_t, usados_c = set(), set()
    unico = len(grp) == 1 and len(cand) == 1
    for score, i, j in pares:
        if i in usados_t or j in usados_c:
            continue
        if score >= 0.45 or unico:  # 1º nome ou sobrenome bate, ou candidato único no dia/valor
            usados_t.add(i)
            usados_c.add(j)
            anc.append({"transacao": grp.iloc[i]["transacao"], "cartao_id": grp.iloc[i]["cartao_id"],
                        "Matrícula": cand.iloc[j]["Matrícula"], "score": score, "unico": unico})
anc = pd.DataFrame(anc)
mapa = anc.groupby("cartao_id")["Matrícula"].agg(lambda s: s.mode().iloc[0])
t["Matrícula"] = t["cartao_id"].map(mapa)
t.to_pickle(CACHE / "transacoes_vinc.pkl")

n_ok = t["ok"].sum()
print(f"aprovadas: {n_ok} | âncoras: {len(anc)} ({len(anc)/n_ok:.0%}) | por candidato único: {anc['unico'].sum()}")
print(f"cartões: {t['cartao_id'].nunique()} | cartões vinculados: {mapa.size}")
print(f"tentativas vinculadas: {t['Matrícula'].notna().mean():.0%} | recusadas vinculadas: {t.loc[~t['ok'], 'Matrícula'].notna().mean():.0%}")
print("cartões com mais de uma matrícula (família no mesmo cartão):", (anc.groupby("cartao_id")["Matrícula"].nunique() > 1).sum())
nunca = t.groupby("cartao_id")["ok"].max()
print(f"cartões que nunca aprovaram na janela: {(~nunca).sum()} (sem âncora possível)")
