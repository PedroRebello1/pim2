"""Reproduz todos os números citados em ESTUDO_DADOS_E_OPORTUNIDADES.md.

Lê o cache gerado por 00/01/02 e grava SOMENTE agregados (sem nome, CPF, e-mail, telefone ou
matrícula) em ../saidas/ (CSV) e ../saidas/graficos/ (SVG).
Uso: python 03_analises.py <pasta_cache>
"""
import sys
from pathlib import Path

import numpy as np
import pandas as pd

from svg import barras, heatmap, linha

CACHE = Path(sys.argv[1])
OUT = Path(__file__).resolve().parent.parent / "saidas"
GRAF = OUT / "graficos"
GRAF.mkdir(parents=True, exist_ok=True)
CORTE = pd.Timestamp("2026-10-15")

p = pd.read_pickle(CACHE / "parcelas.pkl")
a = pd.read_pickle(CACHE / "acessos.pkl")
t = pd.read_pickle(CACHE / "transacoes_vinc.pkl").sort_values("data")
ev = pd.read_pickle(CACHE / "eventos_contrato.pkl")
al = pd.read_pickle(CACHE / "alunos.pkl")
cov = pd.read_pickle(CACHE / "cobertura.pkl")


def secao(titulo):
    print(f"\n{'=' * 8} {titulo} {'=' * 8}")


def salvar(df, nome):
    df.to_csv(OUT / nome, encoding="utf-8-sig")


def familia(plano):
    s = str(plano)
    if "BOLSA" in s:
        return "Bolsa"
    if "GOLD +" in s or "CROSS + GOLD" in s:
        return "Gold + extra"
    if "NATAC" in s or "AQUÁT" in s:
        return "Natação/Hidro"
    if "CROSS" in s:
        return "Cross"
    if "HORARIO" in s:
        return "Horário especial"
    if "BLACK FRIDAY" in s or "PAPAI NOEL" in s:
        return "Promo (BF/Natal)"
    if "LUTAS" in s or "AVULSA" in s:
        return "Lutas/avulsa"
    return "Gold"


# ---------------------------------------------------------------- A. perfil
secao("A. Perfil das bases")
pc = p[p["Contrato"] != 0]
print(f"parcelas: {len(p)} linhas | alunos {p['Matrícula'].nunique()} | contratos de plano {pc['Contrato'].nunique()}"
      f" | vencimento {p['Vencimento'].min():%d/%m/%Y}-{p['Vencimento'].max():%d/%m/%Y}")
print("situação:", p["Situação"].value_counts().to_dict())
print(f"contrato 0 (avulsas/acertos): {(p['Contrato'] == 0).sum()} linhas")
print(f"acessos: {len(a)} linhas | alunos {a['Mat. cliente'].nunique()} | {a['Data entrada'].min():%d/%m/%Y}-{a['Data entrada'].max():%d/%m/%Y}"
      f" | com saída registrada {(a['Sentido'] == 'S').sum()}")
print(f"transações: {len(t)} | cartões {t['cartao_id'].nunique()} | {t['data'].min():%d/%m/%Y}-{t['data'].max():%d/%m/%Y}"
      f" | aprovadas {t['ok'].sum()} ({t['ok'].mean():.1%})")
print("flag Recorrência vs nome do plano (planos com 'RECORR' no nome):",
      pc[pc["Plano"].str.contains("RECORR", na=False)].drop_duplicates("Contrato")["Recorrência"].value_counts().to_dict())

# ---------------------------------------------------------------- B. semântica de "Pagamento"
secao("B. Pagamento - Vencimento (dias) por forma de pagamento")
pg = p[p["Situação"] == "Pago"].copy()
pg["dif"] = (pg["Pagamento"] - pg["Vencimento"]).dt.days
tab_b = pg.groupby("Forma Pgto")["dif"].describe(percentiles=[.05, .5, .95]).sort_values("count", ascending=False).head(7).round(1)
print(tab_b)
salvar(tab_b, "B_pagamento_menos_vencimento_por_forma.csv")
canc = p[p["Situação"] == "Cancelado"]
print(f"canceladas com data de pagamento: {canc['Pagamento'].notna().sum()} de {len(canc)}")

# ---------------------------------------------------------------- C. eventos de contrato / rótulo PIM I
secao("C. Eventos de contrato (cobertura) e teste do rótulo do PIM I")
tab_c = pd.crosstab(ev["status"], ev["tem_cancelada"], margins=True)
print(tab_c)
salvar(tab_c, "C_status_contratos.csv")
lab = pc.groupby("Matrícula")["Situação"].apply(lambda s: (s == "Cancelado").any())
pos = lab[lab].index
acc_ativo = set(a.loc[a["Situação"] == "Ativo", "Mat. cliente"])
print(f"rótulo PIM I (>=1 parcela cancelada): {lab.sum()} de {len(lab)} alunos ({lab.mean():.1%})")
print(f"  ainda com plano em set/26: {al.loc[pos, 'ativo_set26'].mean():.1%}"
      f" | passaram na catraca como Ativo: {np.mean([m in acc_ativo for m in pos]):.1%}"
      f" (negativos: {np.mean([m in acc_ativo for m in lab[~lab].index]):.1%})")

# ---------------------------------------------------------------- D. viés de sobrevivência e coortes
secao("D. Viés de sobrevivência e coortes estimadas pela numeração")
por_mes = cov[cov["mes"] <= pd.Period("2026-09", "M")].groupby("mes")["Matrícula"].nunique()
salvar(por_mes.rename("alunos_com_plano"), "D_alunos_com_plano_por_mes.csv")
print("alunos com plano por mês:", por_mes.iloc[[0, 1, 6, 12, 18, -1]].to_dict())
print("último mês de cobertura:", al["ultimo_mes"].value_counts().sort_index().to_dict())
linha(por_mes.index.astype(str).tolist(), por_mes.tolist(), GRAF / "D1_alunos_com_plano_por_mes.svg",
      "Alunos com plano por mês, segundo o export de parcelas",
      "Crescimento contínuo = só sobreviventes no export (quem saiu foi excluído)", "alunos")

c = pc.groupby("Contrato")["Faturamento"].min().reset_index()
c["m"] = c["Faturamento"].dt.to_period("M")
b = c.groupby("m")["Contrato"].agg(["max", "count"])
b["limite"] = b["max"].cummax()
b["emitidos"] = b["limite"].diff()
b = b.loc["2024-11":].copy()
b["pct_de_clientes_atuais"] = b["count"] / b["emitidos"]
b["idade_meses"] = [(pd.Period("2026-10", "M") - m).n for m in b.index]
print(b[["emitidos", "count", "pct_de_clientes_atuais"]].round(2).to_string())
salvar(b[["idade_meses", "emitidos", "count", "pct_de_clientes_atuais"]].rename(columns={"count": "visiveis"}),
       "D_coorte_contratos_por_numeracao.csv")
barras(b.index.astype(str).tolist(), (b["pct_de_clientes_atuais"] * 100).round(0).tolist(),
       GRAF / "D2_contratos_de_clientes_atuais.svg",
       "% dos contratos emitidos no mês cujo titular ainda é cliente",
       "Estimado pela numeração sequencial de contratos (ID emitidos vs. visíveis)", "%", fmt="{:.0f}%")

pcm = pc.assign(mat_n=pd.to_numeric(pc["Matrícula"]))
f1 = pcm.groupby("mat_n")["Faturamento"].min()
lim = f1.groupby(f1.dt.to_period("Q")).apply(lambda s: s.index.max()).cummax()
vis = set(pcm["mat_n"])
linhas, prev = [], None
for q, bnd in lim.items():
    if prev is not None and bnd > prev and q >= pd.Period("2024Q1", "Q"):
        n = bnd - prev
        v = sum(i in vis for i in range(prev + 1, bnd + 1))
        linhas.append({"trimestre_cadastro": str(q), "matriculas_emitidas": n, "ainda_ativas": v, "pct": round(v / n, 3)})
    prev = bnd
coorte_mat = pd.DataFrame(linhas).set_index("trimestre_cadastro")
print(coorte_mat.to_string())
salvar(coorte_mat, "D_coorte_matriculas_por_numeracao.csv")

# ---------------------------------------------------------------- E. jornada entre planos
secao("E. Transições de plano e retornos")
ev["de"] = ev["plano"].map(familia)
ev["para"] = ev["plano_seguinte"].map(lambda x: familia(x) if x else None)
tr = ev[ev["status"].isin(["troca_ou_renovacao", "renovacao"])]
mat_tr = pd.crosstab(tr["de"], tr["para"], margins=True)
print(mat_tr)
salvar(mat_tr, "E_matriz_transicao_planos.csv")
trc = tr[tr["tem_cancelada"]]
print(f"trocas com cancelamento que repetem o plano exato: {(trc['plano'] == trc['plano_seguinte']).mean():.0%}")
gap = al["meses"].apply(lambda m: max([(y - x).n for x, y in zip(m[:-1], m[1:])] or [1]) - 1)
print(f"alunos ativos que já ficaram >=2 meses sem plano e voltaram: {(gap >= 2).sum()} de {len(al)} ({(gap >= 2).mean():.0%})"
      f" | lacuna de 1 mês: {(gap == 1).sum()}")

# ---------------------------------------------------------------- F. receita e preço
secao("F. Receita, preço e meios de pagamento")
reg = p[p["Parcela"].str.match(r"^PARCELA \d+$") & (p["Situação"] != "Cancelado")].copy()
reg["mes"] = reg["Vencimento"].dt.to_period("M")
s = reg[reg["mes"] == "2026-09"]
print(f"set/26: {s['Matrícula'].nunique()} alunos faturados | R$ {s['Valor'].sum():,.0f} | ticket médio R$ {s.groupby('Matrícula')['Valor'].sum().mean():.2f}"
      f" | em aberto: {(s['Situação'] == 'Em Aberto').sum()} parcelas")
precos = s.groupby("Plano")["Valor"].agg(alunos="size", minimo="min", mediana="median", maximo="max", precos_distintos="nunique")
precos = precos.sort_values("alunos", ascending=False)
print(precos.head(8))
salvar(precos, "F_precos_por_plano_set26.csv")
av = p[(p["Contrato"] == 0) & (p["Situação"] == "Pago")]
av_mes = av.groupby(av["Pagamento"].dt.to_period("M"))["Valor"].sum().loc["2025-10":"2026-09"]
print(f"vendas avulsas pagas, média mensal out/25-set/26: R$ {av_mes.mean():,.0f} (min {av_mes.min():,.0f}, max {av_mes.max():,.0f})")
pl = p[(p["Situação"] == "Pago") & p["Plano"].str.contains("RECORR|REC 9", na=False)]
print("parcelas de planos recorrentes pagas por:", pl["Forma Pgto"].value_counts(normalize=True).round(3).head(4).to_dict())
ab = p[p["Situação"] == "Em Aberto"]
print(f"em aberto: {len(ab)} parcelas | {ab['Matrícula'].nunique()} alunos | R$ {ab['Valor'].sum():,.2f}"
      f" | atraso mediano {(CORTE - ab['Vencimento']).dt.days.median():.0f} dias"
      f" | no convênio de recorrência: {ab['Convênio de Cobrança'].str.contains('RECORR', na=False).mean():.0%}")

# ---------------------------------------------------------------- G. cobrança recorrente
secao("G. Cobrança recorrente (cartão)")
print("horário das tentativas:", t["data"].dt.hour.value_counts().head(3).to_dict())
t["mes"] = t["data"].dt.to_period("M")
g = t.groupby(["cartao_id", "mes"])
cm = g.agg(tent=("ok", "size"), aprov=("ok", "max"))
print(f"cartão-mês: {len(cm)} | aprovou no mês: {cm['aprov'].mean():.1%} | nunca aprovou no mês: {(~cm['aprov']).sum()}")
nunca = t.groupby("cartao_id")["ok"].max()
dec = t[~t["ok"]]
print(f"recusas: {len(dec)} | em cartões que nunca aprovaram na janela: {dec['cartao_id'].isin(nunca[~nunca].index).sum()}"
      f" | cartões que nunca aprovaram: {(~nunca).sum()}")
mx = dec.groupby("cartao_id").apply(lambda x: x.set_index("data")["ok"].rolling("30D").count().max())
print(f"cartões com >15 recusas em 30 dias: {(mx > 15).sum()} | >10: {(mx > 10).sum()}")
first = g.first()
ff = first[~first["ok"]].copy()
ff["recuperou"] = g["ok"].max().loc[ff.index]
rec = ff.groupby("codigoRetorno")["recuperou"].agg(casos="size", taxa_recuperacao="mean").sort_values("casos", ascending=False)
rec = rec[rec["casos"] >= 9].round(3)
print(rec)
salvar(rec, "G_recuperacao_por_codigo_primeira_recusa.csv")
barras(rec.index.tolist(), (rec["taxa_recuperacao"] * 100).round(0).tolist(), GRAF / "G1_recuperacao_por_codigo.svg",
       "Cartão-mês que começou recusado: % que aprovou depois, no mesmo mês",
       "Por código da 1ª recusa (n >= 9). Pac* = códigos do sistema de gestão", "%", fmt="{:.0f}%",
       rotulos_extra=[f"n={n}" for n in rec["casos"]])
t["prev"] = t.groupby("cartao_id")["codigoRetorno"].shift()
r = t[t["prev"] == "51"].copy()
r["faixa"] = pd.cut(r["data"].dt.day, [0, 4, 7, 9, 11, 14, 16, 19, 24, 27, 31],
                    labels=["1-4", "5-7", "8-9", "10-11", "12-14", "15-16", "17-19", "20-24", "25-27", "28-31"])
dia = r.groupby("faixa", observed=True)["ok"].agg(tentativas="size", taxa_aprovacao="mean").round(3)
print(dia)
salvar(dia, "G_retentativa_apos_51_por_dia_do_mes.csv")
barras(dia.index.astype(str).tolist(), (dia["taxa_aprovacao"] * 100).round(1).tolist(), GRAF / "G2_retentativa_51_dia_do_mes.svg",
       "Re-tentativa após 'saldo insuficiente' (51): % aprovada por dia do mês",
       "Ago-out/2026; amostra pequena por faixa (43-165 tentativas)", "%", fmt="{:.0f}%",
       rotulos_extra=[f"n={n}" for n in dia["tentativas"]])
t["d1"] = t["cartao"].str[0]
print("aprovação por 1º dígito do cartão:", t.groupby("d1")["ok"].mean().round(2).to_dict())
binr = t.groupby(t["cartao"].str[:6])["ok"].agg(tentativas="size", aprov="mean").sort_values("tentativas", ascending=False).head(10).round(2)
print(f"BINs com mais tentativas: aprovação de {binr['aprov'].min():.0%} a {binr['aprov'].max():.0%}")
salvar(binr, "G_aprovacao_por_bin_top10.csv")

# ---------------------------------------------------------------- H. acessos
secao("H. Acessos (catraca)")
v = a[a["Sentido"] == "E"].copy()
v["d"] = v["Data entrada"].dt.date
v = v.drop_duplicates(["Mat. cliente", "d"])
v["dow"] = v["Data entrada"].dt.day_of_week
v["h"] = v["Data entrada"].dt.hour
hm = (pd.crosstab(v["h"], v["dow"]) / v.groupby("dow")["d"].nunique()).reindex(columns=range(7), fill_value=0)
hm = hm.loc[5:21]
salvar(hm.round(1), "H_media_entradas_hora_x_dia.csv")
heatmap(hm.values.tolist(), [f"{h}h" for h in hm.index], ["seg", "ter", "qua", "qui", "sex", "sáb", "dom"],
        GRAF / "H1_entradas_hora_dia.svg", "Média de entradas por hora e dia da semana",
        "Catraca, 15/09-15/10/2026 (1ª entrada do aluno no dia)")
freq = v.groupby("Mat. cliente").size()
print(f"visitas: {len(v)} em {v['d'].nunique()} dias | frequência mensal mediana {freq.median():.0f} dias (p25 {freq.quantile(.25):.0f}, p75 {freq.quantile(.75):.0f})")
ativos = al[al["ativo_set26"]].index
fa = freq.reindex(ativos).fillna(0)
print(f"alunos com plano em set/26: {len(ativos)} | zero acessos no mês: {(fa == 0).sum()} ({(fa == 0).mean():.1%}) | 1-2 acessos: {((fa > 0) & (fa <= 2)).sum()}")
cur = cov[cov["mes"] == "2026-09"].merge(p[["Contrato", "Plano"]].drop_duplicates("Contrato"), on="Contrato")
cur = cur.drop_duplicates("Matrícula").set_index("Matrícula")
cur["familia"] = cur["Plano"].map(familia)
cur["freq"] = freq.reindex(cur.index).fillna(0)
fam_freq = cur.groupby("familia")["freq"].agg(alunos="size", mediana="median", pct_zero=lambda x: (x == 0).mean()).round(2)
print(fam_freq)
salvar(fam_freq, "H_frequencia_por_familia_de_plano.csv")
he = cur[cur["familia"] == "Horário especial"].index
vh = v[v["Mat. cliente"].isin(he)]
print(f"Horário especial (11h-16h): {((vh['h'] < 11) | (vh['h'] >= 16)).mean():.0%} das visitas fora da faixa (n={len(vh)})")
print("tipos de acesso:", a["Tipo de acesso"].value_counts().head(4).to_dict())
sit = a.groupby("Mat. cliente")["Situação"].agg(lambda x: x.mode().iloc[0])
w1 = v[v["Data entrada"] < "2026-09-29"].groupby("Mat. cliente").size()
ult = v.groupby("Mat. cliente")["Data entrada"].max()
cmp_ = pd.DataFrame({"sit": sit, "freq_2_semanas": w1, "dias_sem_vir": (CORTE + pd.Timedelta(hours=23, minutes=59) - ult).dt.days})
cmp_ = cmp_.fillna({"freq_2_semanas": 0})
print(cmp_.groupby("sit")[["freq_2_semanas", "dias_sem_vir"]].mean().round(1))
mp, ma = set(p["Matrícula"]), set(a["Mat. cliente"])
fora = a[~a["Mat. cliente"].isin(mp)].drop_duplicates("Mat. cliente")
print(f"na catraca mas fora do export de parcelas: {len(ma - mp)} (Inativo: {(fora['Situação'] == 'Inativo').sum()})")
