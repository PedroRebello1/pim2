"""Pipeline completo do motor de cobrança: dados -> atributos -> modelo -> políticas -> fila.

Uso: python rodar.py <pasta_com_exports> <pasta_privada_fora_do_repo> [--resultados PASTA]
- resultados agregados e pseudonimizados -> ../resultados/ (ou a pasta indicada em --resultados)
- fila de ação COM nome do titular (uso interno da academia) -> <pasta_privada>/fila_do_dia.csv

A pasta privada precisa ficar FORA do repositório: a fila traz o nome do titular e o cartão
mascarado. O script se recusa a gravá-la dentro do repositório.
"""
import argparse
import json
from pathlib import Path

import pandas as pd

from dados import atributos_tentativas, carregar_exports
from modelo import ModeloAprovacao, auc, brier, calibracao, curva_roc, lambda_por_validacao
from politicas import avaliar, codigos_irreversiveis, fila_do_dia, limiar_por_retencao, pseudonimo, teto_de_falhas

AQUI = Path(__file__).resolve().parent
REPOSITORIO = AQUI.parents[1]
RESULTADOS = AQUI.parent / "resultados"


def dentro_do_repositorio(pasta: Path) -> bool:
    pasta = Path(pasta).resolve()
    return pasta == REPOSITORIO or REPOSITORIO in pasta.parents


def main(argv=None):
    ap = argparse.ArgumentParser(description="Motor de cobrança: modelo, políticas avaliadas por replay e fila do dia.")
    ap.add_argument("exports", type=Path, help="pasta com os exports .xlsx do sistema da academia")
    ap.add_argument("privada", type=Path, help="pasta FORA do repositório para a fila com o nome do titular")
    ap.add_argument("--resultados", type=Path, default=RESULTADOS,
                    help="onde gravar os resultados agregados (padrão: solucao_pim2/resultados)")
    args = ap.parse_args(argv)
    DADOS, PRIVADO, OUT = args.exports, args.privada, args.resultados
    if not DADOS.is_dir():
        ap.error(f"a pasta de exports não existe: {DADOS}")
    if dentro_do_repositorio(PRIVADO):
        ap.error("a pasta privada precisa ficar fora do repositório, porque a fila do dia traz o nome "
                 "do titular e o cartão mascarado.")
    OUT.mkdir(parents=True, exist_ok=True)
    PRIVADO.mkdir(parents=True, exist_ok=True)

    ex = carregar_exports(DADOS)
    if "transacoes" not in ex:
        ap.error(f"nenhum export de transações (com a coluna codigoRetorno) foi reconhecido em {DADOS}")
    t = atributos_tentativas(ex["transacoes"])
    corte = t["data"].max().to_period("M").start_time  # teste = último mês dos dados (fora do treino)
    treino_all, teste_all = t[t["data"] < corte], t[t["data"] >= corte]
    treino, teste = treino_all[treino_all["retentativa"]], teste_all[teste_all["retentativa"]]
    print(f"tentativas: {len(t)} ({t['data'].min():%d/%m/%Y}-{t['data'].max():%d/%m/%Y}) | corte do teste: {corte:%d/%m/%Y}")
    print(f"re-tentativas: treino {len(treino)} ({treino['ok'].sum()} aprov.) | teste {len(teste)} ({teste['ok'].sum()} aprov.)")

    # ---------------------------------------------------------------- modelo
    l2, grade = lambda_por_validacao(treino, "ok", treino_all, corte)
    modelo = ModeloAprovacao(l2=l2).ajustar(treino, treino["ok"], treino_all)
    p_tr, p_te = modelo.prever(treino), modelo.prever(teste)
    # referência simples: taxa histórica de aprovação por último código (sem ML)
    taxa_cod = treino.groupby("ult_cod")["ok"].mean()
    p_ref = teste["ult_cod"].map(taxa_cod).fillna(treino["ok"].mean())
    metricas = {
        "periodo": [f"{t['data'].min():%d/%m/%Y}", f"{t['data'].max():%d/%m/%Y}"], "corte_teste": f"{corte:%d/%m/%Y}",
        "tentativas": int(len(t)), "cartoes": int(t["cartao_id"].nunique()), "aprovacao_geral": round(t["ok"].mean(), 4),
        "retentativas_treino": int(len(treino)), "aprov_treino": int(treino["ok"].sum()),
        "retentativas_teste": int(len(teste)), "aprov_teste": int(teste["ok"].sum()),
        "l2": l2, "auc_validacao_por_l2": {str(k): round(v, 3) for k, v in grade.items()},
        "auc_treino": round(auc(treino["ok"], p_tr), 3), "auc_teste": round(auc(teste["ok"], p_te), 3),
        "auc_teste_referencia_codigo": round(auc(teste["ok"], p_ref), 3),
        "brier_teste": round(brier(teste["ok"], p_te), 4), "brier_teste_constante": round(brier(teste["ok"], [treino["ok"].mean()] * len(teste)), 4),
    }
    curva_roc(teste["ok"], p_te).to_csv(OUT / "roc_teste.csv", index=False)
    calibracao(teste["ok"], p_te).to_csv(OUT / "calibracao_teste.csv", index=False)
    modelo.coeficientes().sort_values("coef").to_csv(OUT / "coeficientes.csv", index=False)

    # ---------------------------------------------------------------- políticas (regras aprendidas no treino)
    irrev = codigos_irreversiveis(treino)
    teto = teto_de_falhas(treino, irrev)
    tau = limiar_por_retencao(p_tr, treino["ok"], 0.95)
    regra_cod = ~teste["ult_cod"].isin(irrev)
    regra_teto = regra_cod & (teste["seq_falhas"] < teto) if teto else regra_cod
    pol = pd.DataFrame([
        avaliar(teste, [True] * len(teste), "Atual: re-tenta tudo"),
        avaliar(teste, regra_cod, "Regra 1: não re-tentar códigos irreversíveis"),
        avaliar(teste, regra_teto, f"Regra 2: regra 1 + teto de {teto} recusas seguidas"),
        avaliar(teste, p_te >= tau, "Modelo: re-tentar se P(aprovação) ≥ limiar"),
    ])
    base = pol.iloc[0]
    pol["pct_tentativas"] = (pol["tentativas"] / base["tentativas"]).round(3)
    pol["pct_aprovacoes"] = (pol["aprovacoes"] / base["aprovacoes"]).round(3)
    pol["aprov_por_100"] = (100 * pol["aprovacoes"] / pol["tentativas"]).round(1)
    pol.to_csv(OUT / "politicas_teste.csv", index=False)
    metricas.update({"codigos_irreversiveis": irrev, "teto_falhas": teto, "limiar_modelo": round(tau, 4)})

    # tempo perdido hoje (janela inteira): cartão-mês que bateu em código irreversível e nunca aprovou
    ret = t[t["retentativa"]]
    irr_cm = ret[ret["ult_cod"].isin(irrev)].groupby(["cartao_id", "mes"]).agg(
        primeira=("data", "min"), ultima=("data", "max"), tentativas=("ok", "size"), valor=("valor", "max"))
    aprov_cm = t.groupby(["cartao_id", "mes"])["ok"].max()
    irr_cm = irr_cm[aprov_cm.reindex(irr_cm.index).to_numpy() == 0]
    metricas.update({
        "irrev_cartao_mes": int(len(irr_cm)), "irrev_valor": round(float(irr_cm["valor"].sum()), 2),
        "irrev_tentativas_inuteis": int(irr_cm["tentativas"].sum()),
        "irrev_dias_insistindo_mediana": float((irr_cm["ultima"] - irr_cm["primeira"]).dt.days.median()),
    })

    # ---------------------------------------------------------------- fila do dia (modelo re-treinado com todo o histórico)
    final = ModeloAprovacao(l2=l2).ajustar(ret, ret["ok"], t)
    irrev_f = codigos_irreversiveis(ret)
    hoje, fila = fila_do_dia(t, final, irrev_f, teto_de_falhas(ret, irrev_f),
                             limiar_por_retencao(final.prever(ret), ret["ok"]))
    fila.drop(columns="cartao_id").sort_values(["acao", "valor"], ascending=[True, False]).to_csv(
        PRIVADO / "fila_do_dia.csv", index=False, encoding="utf-8-sig")
    fila["grupo"] = fila["acao"].str.replace(r"Re-tentar em .*", "Re-tentar em data indicada", regex=True)
    resumo = fila.groupby("grupo").agg(cartoes=("valor", "size"), valor=("valor", "sum")).reset_index()
    resumo.to_csv(OUT / "fila_resumo.csv", index=False)
    amostra = fila.assign(id=fila["cartao_id"].map(pseudonimo)).groupby("grupo").head(2)
    amostra[["id", "valor", "ultimo_codigo", "recusas_seguidas", "acao", "motivo"]].to_csv(OUT / "fila_amostra.csv", index=False)
    metricas.update({"fila_data": f"{hoje:%d/%m/%Y}", "fila_cartoes": int(len(fila)), "fila_valor": round(float(fila["valor"].sum()), 2)})

    (OUT / "metricas.json").write_text(json.dumps(metricas, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(metricas, ensure_ascii=False, indent=2))
    print(pol.to_string(index=False))
    print(resumo.to_string(index=False))


if __name__ == "__main__":
    main()
