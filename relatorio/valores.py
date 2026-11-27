"""✏️ Números usados no texto do relatório: cada {{nome}} do relatorio_pi.md sai daqui.

Nunca digite um resultado à mão no texto: calcule aqui, a partir dos arquivos do repositório,
e use {{nome}} no relatorio_pi.md. Assim, quando o estudo ou o motor forem rodados com dados
novos, o relatório se atualiza sozinho ao ser gerado de novo.
"""
from __future__ import annotations

from datetime import datetime, timedelta

import pandas as pd

from abnt import numero_br, percentual_br
from fontes import dict_do_log, do_log, metricas, resultados, saidas

MESES = ["janeiro", "fevereiro", "março", "abril", "maio", "junho", "julho", "agosto", "setembro", "outubro",
         "novembro", "dezembro"]


# ----------------------------------------------------------------------------- formatos
def inteiro(v) -> str:
    return numero_br(int(round(float(v))), 0)


def pct(v, casas=1) -> str:
    """0.935 -> '93,5%'."""
    return percentual_br(float(v), casas)


def dec(v, casas=3) -> str:
    return numero_br(float(v), casas)


def mil_reais(v) -> str:
    """48693.85 -> 'R$ 48,7 mil'."""
    return "R$\u00a0" + numero_br(float(v) / 1000, 1) + "\u00a0mil"   # espaços que não quebram a linha


def pct_en(v, casas=1) -> str:
    return f"{float(v) * 100:.{casas}f}%"


def mes_extenso(periodo: str) -> str:
    """'2024-10' -> 'outubro de 2024'."""
    ano, mes = periodo.split("-")
    return f"{MESES[int(mes) - 1]} de {ano}"


def data(texto: str) -> datetime:
    return datetime.strptime(texto, "%d/%m/%Y")


# ----------------------------------------------------------------------------- valores
def calcular() -> dict[str, str]:
    v: dict[str, str] = {}
    m = metricas()

    # --- período, treino e teste do motor de cobrança (solucao_pim2/resultados/metricas.json)
    v["periodo_ini"], v["periodo_fim"] = m["periodo"]
    corte = data(m["corte_teste"])
    v["treino_ini"], v["treino_fim"] = m["periodo"][0], (corte - timedelta(days=1)).strftime("%d/%m/%Y")
    v["teste_ini"], v["teste_fim"] = m["corte_teste"], m["periodo"][1]
    v["tentativas"] = inteiro(m["tentativas"])
    v["aprovacao_geral"], v["aprovacao_geral_en"] = pct(m["aprovacao_geral"]), pct_en(m["aprovacao_geral"])
    v["retent_treino"], v["aprov_treino"] = inteiro(m["retentativas_treino"]), inteiro(m["aprov_treino"])
    v["retent_teste"], v["aprov_teste"] = inteiro(m["retentativas_teste"]), inteiro(m["aprov_teste"])
    grade = list(m["auc_validacao_por_l2"])
    grade_txt = [numero_br(float(g), 1 if float(g) % 1 else 0) for g in grade]
    v["grade_l2"] = "; ".join(grade_txt[:-1]) + " e " + grade_txt[-1]
    v["l2"] = numero_br(float(m["l2"]), 1 if float(m["l2"]) % 1 else 0)
    chave_l2 = next(k for k in m["auc_validacao_por_l2"] if float(k) == float(m["l2"]))
    v["auc_val_l2"] = dec(m["auc_validacao_por_l2"][chave_l2])
    v["auc_teste"], v["auc_teste_en"] = dec(m["auc_teste"]), f"{m['auc_teste']:.3f}"
    v["auc_ref"], v["auc_ref_en"] = dec(m["auc_teste_referencia_codigo"]), f"{m['auc_teste_referencia_codigo']:.3f}"
    v["auc_treino"] = dec(m["auc_treino"])
    v["teto"] = inteiro(m["teto_falhas"])
    v["irrev_cartao_mes"] = inteiro(m["irrev_cartao_mes"])
    v["irrev_tentativas"] = inteiro(m["irrev_tentativas_inuteis"])
    v["irrev_dias"] = inteiro(m["irrev_dias_insistindo_mediana"])
    v["irrev_valor"] = mil_reais(m["irrev_valor"])
    v["fila_data"], v["fila_cartoes"] = m["fila_data"], inteiro(m["fila_cartoes"])
    v["fila_valor"] = mil_reais(m["fila_valor"])
    v["fila_valor_en"] = f"BRL {m['fila_valor'] / 1000:.1f} thousand"

    # --- políticas avaliadas por replay (politicas_teste.csv)
    pol = resultados("politicas_teste.csv")
    base = pol[pol["politica"].str.startswith("Atual")].iloc[0]
    for chave, prefixo in [("atual", "Atual"), ("regra1", "Regra 1"), ("regra2", "Regra 2"), ("modelo", "Modelo")]:
        r = pol[pol["politica"].str.startswith(prefixo)].iloc[0]
        evitadas = 1 - r["tentativas"] / base["tentativas"]
        mantidas = r["aprovacoes"] / base["aprovacoes"]
        v[f"pol_{chave}_evitadas"], v[f"pol_{chave}_evitadas_en"] = pct(evitadas, 0), pct_en(evitadas, 0)
        v[f"pol_{chave}_aprov"], v[f"pol_{chave}_aprov_en"] = pct(mantidas, 0), pct_en(mantidas, 0)
        v[f"pol_{chave}_por100"] = numero_br(100 * r["aprovacoes"] / r["tentativas"], 1)
        perdidas = int(base["aprovacoes"] - r["aprovacoes"])
        v[f"pol_{chave}_perdidas"] = "uma aprovação" if perdidas == 1 else f"{perdidas} aprovações"

    # --- fila de ação (fila_resumo.csv)
    fila = resultados("fila_resumo.csv")
    novo = fila[fila["grupo"].str.contains("novo cartão")]["valor"].sum()
    v["fila_pct_novo_cartao"] = pct(novo / fila["valor"].sum(), 0)

    # --- modelo: ROC, calibração e razões de chances
    roc = resultados("roc_teste.csv")
    v["roc_fpr_ref"] = "10%"
    v["roc_tpr_ref"] = pct(roc.loc[roc["fpr"] <= 0.10, "tpr"].max(), 0)
    cal = resultados("calibracao_teste.csv").sort_values("faixa")
    v["calib_top_prev"], v["calib_top_real"] = pct(cal["p_media"].iloc[-1]), pct(cal["taxa_real"].iloc[-1])
    v["calib_resto_prev"], v["calib_resto_real"] = pct(cal["p_media"].iloc[:-1].max()), pct(cal["taxa_real"].iloc[:-1].max())
    coef = resultados("coeficientes.csv").set_index("atributo")["razao_chances"]
    v["or_51"], v["or_d10_14"] = numero_br(coef["ult_cod=51"], 1), numero_br(coef["faixa_dia=10-14"], 1)
    v["or_seq"], v["or_pac014"] = pct(coef["seq_falhas"], 0), pct(coef["ult_cod=Pac014"], 0)

    # --- estudo dos dados (saidas/ e o log do scripts/03_analises.py)
    v["rotulo_pim1_n"] = inteiro(do_log(r"rótulo PIM I \(>=1 parcela cancelada\): (\d+) de"))
    rot_pct = do_log(r"rótulo PIM I \(>=1 parcela cancelada\): \d+ de \d+ alunos \(([\d.]+)%\)") / 100
    v["rotulo_pim1_pct"] = pct(rot_pct)
    com_plano = do_log(r"ainda com plano em set/26: ([\d.]+)%") / 100
    v["rotulo_pim1_com_plano"], v["rotulo_pim1_com_plano_en"] = pct(com_plano), pct_en(com_plano)
    v["catraca_ativo_pos"] = pct(do_log(r"passaram na catraca como Ativo: ([\d.]+)%") / 100)
    v["catraca_ativo_neg"] = pct(do_log(r"\(negativos: ([\d.]+)%\)") / 100)

    meios = dict_do_log("parcelas de planos recorrentes pagas por:")
    v["recorrentes_outro_meio"] = pct(1 - meios["CARTÃO RECORRENTE"], 0)
    b = saidas("B_pagamento_menos_vencimento_por_forma.csv").set_index("Forma Pgto")
    v["cheque_mediana"] = inteiro(abs(b.loc["CHEQUE", "50%"]))
    flag = dict_do_log("flag Recorrência vs nome do plano (planos com 'RECORR' no nome):")
    v["flag_recorrencia_nao"] = pct(flag["Não"] / sum(flag.values()), 0)
    v["n_contrato0"] = inteiro(do_log(r"contrato 0 \(avulsas/acertos\): (\d+) linhas"))
    v["parc_cancelado"] = inteiro(dict_do_log("situação:")["Cancelado"])

    por_mes = saidas("D_alunos_com_plano_por_mes.csv")
    v["alunos_mes_ini"], v["alunos_mes_fim"] = inteiro(por_mes["alunos_com_plano"].iloc[0]), inteiro(por_mes["alunos_com_plano"].iloc[-1])
    v["alunos_mes_ini_rotulo"], v["alunos_mes_fim_rotulo"] = mes_extenso(por_mes["mes"].iloc[0]), mes_extenso(por_mes["mes"].iloc[-1])
    ultimo = dict_do_log("último mês de cobertura:")
    v["n_alunos_cobertura"] = inteiro(sum(ultimo.values()))
    v["alunos_saida_antes"] = inteiro(sum(n for mes, n in ultimo.items() if mes < "2026-09"))
    v["catraca_fora"] = inteiro(do_log(r"na catraca mas fora do export de parcelas: (\d+)"))
    v["catraca_fora_inativos"] = inteiro(do_log(r"na catraca mas fora do export de parcelas: \d+ \(Inativo: (\d+)\)"))

    coorte = saidas("D_coorte_contratos_por_numeracao.csv")
    recente = coorte[coorte["idade_meses"] <= 3]["pct_de_clientes_atuais"]
    meses_rec = sorted(coorte.loc[coorte["idade_meses"] <= 3, "m"])
    ini, fim = mes_extenso(meses_rec[0]), mes_extenso(meses_rec[-1])
    v["coorte_recente_periodo"] = (ini.split(" de ")[0] + " a " + fim) if ini[-4:] == fim[-4:] else f"{ini} a {fim}"
    v["coorte_recente_min"], v["coorte_recente_max"] = pct(recente.min(), 0), pct(recente.max(), 0)
    antiga = coorte[(coorte["idade_meses"] >= 12) & (coorte["m"] != "2024-12")]["pct_de_clientes_atuais"]
    v["coorte_antiga_min"], v["coorte_antiga_max"] = pct(antiga.min(), 0), pct(antiga.max(), 0)
    v["coorte_dez24"] = pct(coorte.loc[coorte["m"] == "2024-12", "pct_de_clientes_atuais"].iloc[0], 0)

    st = saidas("C_status_contratos.csv").set_index("status")
    v["n_contratos"] = inteiro(st.loc["All", "All"])
    v["n_troca"], v["n_renovacao"] = inteiro(st.loc["troca_ou_renovacao", "All"]), inteiro(st.loc["renovacao", "All"])

    aberto = r"em aberto: (\d+) parcelas \| (\d+) alunos \| R\$ ([\d,.]+) \| atraso mediano (\d+) dias \| no convênio de recorrência: (\d+)%"
    v["aberto_n"], v["aberto_alunos"] = inteiro(do_log(aberto, 1)), inteiro(do_log(aberto, 2))
    v["aberto_valor"] = mil_reais(do_log(aberto, 3))
    v["aberto_atraso"], v["aberto_recorrencia"] = inteiro(do_log(aberto, 4)), pct(do_log(aberto, 5) / 100, 0)
    v["tent_12h"] = inteiro(dict_do_log("horário das tentativas:")[12])
    cm = r"cartão-mês: (\d+) \| aprovou no mês: ([\d.]+)% \| nunca aprovou no mês: (\d+)"
    v["cartao_mes"], v["nunca_aprovou_mes"] = inteiro(do_log(cm, 1)), inteiro(do_log(cm, 3))
    v["cartoes_15"] = inteiro(do_log(r"cartões com >15 recusas em 30 dias: (\d+)"))

    rec = saidas("G_recuperacao_por_codigo_primeira_recusa.csv").set_index("codigoRetorno")["taxa_recuperacao"]
    v["rec_51"], v["rec_pac014"] = pct(rec["51"], 0), pct(rec["Pac014"], 1)
    dia = saidas("G_retentativa_apos_51_por_dia_do_mes.csv").set_index("faixa")
    inicio, meio = dia.loc[["1-4", "5-7"], "taxa_aprovacao"], dia.loc[["10-11", "12-14"], "taxa_aprovacao"]
    v["dia_1_7_min"], v["dia_1_7_max"] = pct(inicio.min()), pct(inicio.max())
    v["dia_10_14_min"], v["dia_10_14_max"] = pct(meio.min()), pct(meio.max())
    v["dia_n_min"], v["dia_n_max"] = inteiro(dia["tentativas"].min()), inteiro(dia["tentativas"].max())
    bins = saidas("G_aprovacao_por_bin_top10.csv")
    v["bin_min"], v["bin_max"] = pct(bins["aprov"].min(), 0), pct(bins["aprov"].max(), 0)

    acesso = r"acessos: \d+ linhas \| alunos \d+ \| ([\d/]+)-([\d/]+)"
    v["acessos_ini"], v["acessos_fim"] = do_log(acesso, 1, str), do_log(acesso, 2, str)
    sem = r"alunos com plano em set/26: (\d+) \| zero acessos no mês: (\d+) \(([\d.]+)%\)"
    v["sem_acesso_n"], v["sem_acesso_pct"] = inteiro(do_log(sem, 2)), pct(do_log(sem, 3) / 100)
    v["retornos_pct"] = pct(do_log(r"voltaram: \d+ de \d+ \((\d+)%\)") / 100, 0)
    v["freq_ativo"] = numero_br(do_log(r"\nAtivo\s+([\d.]+)\s+[\d.]+"), 1)
    v["freq_inativo"] = numero_br(do_log(r"\nInativo\s+([\d.]+)\s+[\d.]+"), 1)
    return v


if __name__ == "__main__":       # python relatorio/valores.py -> mostra todos os valores
    import sys
    from pathlib import Path
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    for k, val in calcular().items():
        print(f"{k:28s} {val}")
