"""Painel aluno x mês de cobertura e classificação de eventos de contrato.

Ideia central: uma parcela "Cancelada" NÃO significa que o aluno saiu. Trocas de plano e
renovações antecipadas cancelam o restante do contrato antigo enquanto um contrato novo
começa. Por isso o estado do aluno é medido pela COBERTURA (meses com parcela de plano
não cancelada, em qualquer contrato), e não pelo status de um contrato isolado.

Uso: python 01_cobertura_e_eventos.py <pasta_cache>
Saídas (no cache, contêm matrícula -> não versionar): cobertura.pkl, eventos_contrato.pkl, alunos.pkl
"""
import sys
from pathlib import Path

import numpy as np
import pandas as pd

CACHE = Path(sys.argv[1])
CORTE = pd.Timestamp("2026-10-15")          # data do export (último vencimento visível)
ULTIMO_MES_COMPLETO = pd.Period("2026-09", "M")  # vencimentos de 16-31/10 ainda não aparecem
GAP_SAIDA = 2                                # meses sem cobertura para considerar saída
MENSAL_REF = 190.0                           # valor mensal de referência p/ parcelas únicas à vista

p = pd.read_pickle(CACHE / "parcelas.pkl")
p = p[p["Contrato"] != 0].copy()  # contrato 0 = vendas avulsas / acertos, não é plano

# Parcelas que representam mensalidade do plano (exclui matrícula, produtos, anuidade, ajustes)
regular = p["Parcela"].str.match(r"^PARCELA (\d+|RENEGOCIADA|TRANSF.*|EDIÇÃO.*)$")
p = p[regular].copy()
p["mes"] = p["Vencimento"].dt.to_period("M")
valida = p["Situação"] != "Cancelado"

# --- cobertura: cada parcela válida cobre o mês do vencimento ---
cov = p[valida][["Matrícula", "Contrato", "mes", "Valor", "Vencimento"]].copy()

# Parcela única muito acima de uma mensalidade = pagamento à vista de um período.
n_parc = p.groupby("Contrato")["Cod.Parcela"].transform("count")
avista = p[valida & (n_parc == 1) & (p["Valor"] > 2 * MENSAL_REF)]
extra = []
for _, r in avista.iterrows():
    meses = int(min(12, round(r["Valor"] / MENSAL_REF)))
    for k in range(1, meses):
        extra.append({"Matrícula": r["Matrícula"], "Contrato": r["Contrato"], "mes": r["mes"] + k,
                      "Valor": 0.0, "Vencimento": r["Vencimento"] + pd.DateOffset(months=k)})
cov = pd.concat([cov, pd.DataFrame(extra)], ignore_index=True)
cov = cov[cov["mes"] <= pd.Period(CORTE, "M")]
cov.to_pickle(CACHE / "cobertura.pkl")

ativo = cov.groupby("Matrícula")["mes"].apply(lambda s: sorted(set(s)))


def coberto(mat, mes):
    return mes in set(ativo.get(mat, []))


# --- eventos por contrato ---
rows = []
for ct, x in p.groupby("Contrato"):
    mat = x["Matrícula"].iloc[0]
    canc = x[x["Situação"] == "Cancelado"]
    ok = x[x["Situação"] != "Cancelado"]
    meses_aluno = set(ativo.get(mat, []))
    ult_ok = ok["mes"].max() if len(ok) else x["mes"].min() - 1
    fim = ult_ok  # último mês coberto por este contrato
    seguintes = [fim + k for k in range(1, GAP_SAIDA + 1)]
    observavel = seguintes[-1] <= ULTIMO_MES_COMPLETO
    continua = any(m in meses_aluno for m in seguintes)
    # o aluno tem cobertura por OUTRO contrato que começa até 1 mês após o fim deste?
    outros = cov[(cov["Matrícula"] == mat) & (cov["Contrato"] != ct)]
    novo = outros[(outros["mes"] >= x["mes"].min()) & (outros["mes"] <= fim + 1)]
    tem_canc = len(canc) > 0
    if not observavel and not continua:
        status = "em_curso_ou_censurado"
    elif continua and len(novo):
        status = "troca_ou_renovacao" if tem_canc else "renovacao"
    elif continua:
        status = "coberto_por_contrato_sobreposto"  # outro contrato do aluno, iniciado antes, segue cobrindo
    else:
        status = "saida_com_cancelamento" if tem_canc else "saida_sem_renovar"
    rows.append({"Contrato": ct, "Matrícula": mat, "plano": x["Plano"].iloc[0],
                 "inicio": x["mes"].min(), "fim_coberto": fim, "n_validas": len(ok), "n_canceladas": len(canc),
                 "n_em_aberto": int((x["Situação"] == "Em Aberto").sum()),
                 "tem_cancelada": tem_canc, "status": status,
                 "plano_seguinte": outros[outros["mes"] > fim - 1].sort_values("mes")["Contrato"].head(1).tolist()})
ev = pd.DataFrame(rows)
# plano do contrato seguinte (para medir upgrade/downgrade)
plano_ct = p.groupby("Contrato")["Plano"].first()
ev["plano_seguinte"] = ev["plano_seguinte"].apply(lambda l: plano_ct.get(l[0]) if l else None)
ev.to_pickle(CACHE / "eventos_contrato.pkl")

# --- visão por aluno ---
al = pd.DataFrame({"meses": ativo})
al["primeiro_mes"] = al["meses"].apply(min)
al["ultimo_mes"] = al["meses"].apply(max)
al["n_meses"] = al["meses"].apply(len)
al["ativo_set26"] = al["meses"].apply(lambda m: pd.Period("2026-09", "M") in m)
al["ativo_out26"] = al["meses"].apply(lambda m: pd.Period("2026-10", "M") in m)
# lacunas internas (meses sem cobertura entre o 1º e o último) = possível pausa/retorno
al["lacunas"] = al.apply(lambda r: len(pd.period_range(r.primeiro_mes, r.ultimo_mes, freq="M")) - r.n_meses, axis=1)
al.to_pickle(CACHE / "alunos.pkl")

print("contratos classificados:", len(ev))
print(pd.crosstab(ev["status"], ev["tem_cancelada"], margins=True))
print("\nalunos com cobertura:", len(al), "| ativos em set/26:", al["ativo_set26"].sum(), "| out/26 (parcial):", al["ativo_out26"].sum())
print("alunos com lacuna interna:", (al["lacunas"] > 0).sum())
