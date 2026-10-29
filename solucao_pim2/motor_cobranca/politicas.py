"""Políticas de re-tentativa, avaliação por replay e fila diária de ação.

Avaliação por replay: a primeira cobrança do cartão no mês sempre acontece; a política decide só
as RE-TENTATIVAS. Cada re-tentativa real é mantida ou evitada, e contamos as aprovações que
continuariam acontecendo. Isso mede com honestidade o lado "parar de insistir". Já o ganho de
"re-tentar num dia melhor" exige teste com a academia (não dá para observar o contrafactual).
"""
import hashlib

import numpy as np
import pandas as pd

from dados import FAIXAS_DIA, ROTULOS_DIA


def codigos_irreversiveis(treino, min_casos=15, taxa_max=0.01):
    """Códigos após os quais a re-tentativa praticamente nunca aprova no treino (≤ 1%, com suporte mínimo)."""
    s = treino.groupby("ult_cod")["ok"].agg(["size", "mean"])
    return sorted(s[(s["size"] >= min_casos) & (s["mean"] <= taxa_max)].index)


def teto_de_falhas(treino, irreversiveis, taxa_max=0.01, min_casos=30):
    """Menor k tal que, entre códigos RECUPERÁVEIS, a partir de k falhas seguidas a aprovação fica abaixo de taxa_max."""
    rec = treino[~treino["ult_cod"].isin(irreversiveis)]
    for k in range(2, int(rec["seq_falhas"].max()) + 1):
        cauda = rec[rec["seq_falhas"] >= k]
        if len(cauda) >= min_casos and cauda["ok"].mean() < taxa_max:
            return k
    return None


def limiar_por_retencao(p, y, retencao=0.95):
    """Maior limiar que ainda mantém `retencao` das aprovações do treino."""
    return float(np.quantile(np.asarray(p)[np.asarray(y) == 1], 1 - retencao))


def avaliar(teste, tentar, nome):
    t = teste.assign(tentar=np.asarray(tentar, bool))
    feitas = t[t["tentar"]]
    return {"politica": nome, "tentativas": int(len(feitas)), "aprovacoes": int(feitas["ok"].sum()),
            "valor_aprovado": float(feitas.loc[feitas["ok"] == 1, "valor"].sum()),
            "evitadas": int((~t["tentar"]).sum()), "aprovacoes_perdidas": int(t.loc[~t["tentar"], "ok"].sum())}


def pseudonimo(cartao_id):
    return "C-" + hashlib.sha1(cartao_id.encode()).hexdigest()[:5].upper()


def fila_do_dia(todas, modelo, irreversiveis, teto, tau, horizonte=10, janela_ativa=7):
    """Para cada cartão com cobrança pendente no último dia dos dados, recomenda a próxima ação."""
    hoje = todas["data"].max().normalize()
    ult = todas.sort_values("data").groupby("cartao_id").tail(1)
    mes_atual = ult["data"].dt.to_period("M")
    aprovou_no_mes = todas[todas["ok"] == 1].assign(m=lambda d: d["data"].dt.to_period("M")) \
        .groupby("cartao_id")["m"].max()
    pend = ult[(ult["ok"] == 0) & (ult["data"] >= hoje - pd.Timedelta(days=janela_ativa))
               & (ult["cartao_id"].map(aprovou_no_mes) != mes_atual)].copy()

    # cenários: próxima tentativa em cada um dos próximos dias
    cen = []
    for k in range(1, horizonte + 1):
        d = hoje + pd.Timedelta(days=k)
        c = pend.copy()
        c["ult_cod"] = c["codigoRetorno"]
        c["seq_falhas"] = c["seq_falhas"] + 1
        c["dias_desde_ult"] = (d - c["data"].dt.normalize()).dt.days
        c["n_tent_mes"] = np.where(c["data"].dt.to_period("M") == d.to_period("M"), c["n_tent_mes"] + 1, 1)
        c["faixa_dia"] = str(pd.cut([d.day], FAIXAS_DIA, labels=ROTULOS_DIA)[0])
        c["data_cenario"] = d
        cen.append(c)
    cen = pd.concat(cen, ignore_index=True)  # índice único: idxmax precisa apontar para 1 linha
    cen["p"] = modelo.prever(cen)
    # esperar sempre aumenta um pouco a chance; escolhe o PRIMEIRO dia que alcança 90% da melhor chance
    cen["p_max"] = cen.groupby("cartao_id")["p"].transform("max")
    melhor = cen[cen["p"] >= 0.9 * cen["p_max"]].sort_values("data_cenario").groupby("cartao_id").head(1).set_index("cartao_id")
    amanha = cen[cen["data_cenario"] == hoje + pd.Timedelta(days=1)].set_index("cartao_id")["p"]

    linhas = []
    for cid, r in melhor.iterrows():
        cod, seq = r["ult_cod"], int(r["seq_falhas"])
        if cod in irreversiveis:
            acao, motivo = "Contato: novo cartão ou PIX", f"após o código {cod}, a re-tentativa aprova ≤ 1% no histórico"
        elif teto and seq >= teto:
            acao, motivo = "Contato: parar re-tentativas", f"{seq} recusas seguidas; a partir de {teto} a aprovação fica abaixo de 1%"
        elif r["p"] >= tau:
            acao = f"Re-tentar em {r['data_cenario']:%d/%m}"
            motivo = f"P(aprovação) {r['p']:.0%} em {r['data_cenario']:%d/%m} contra {amanha[cid]:.0%} amanhã"
        else:
            acao, motivo = "Contato: baixa chance", f"P(aprovação) no máximo {r['p']:.0%} nos próximos {horizonte} dias"
        linhas.append({"cartao_id": cid, "titular": r["titular"], "cartao": r["cartao"], "valor": r["valor"],
                       "ultimo_codigo": cod, "recusas_seguidas": seq, "acao": acao, "motivo": motivo,
                       "p_melhor_dia": round(float(r["p"]), 3)})
    return hoje, pd.DataFrame(linhas)
