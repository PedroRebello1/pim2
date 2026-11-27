"""✏️ Tabelas do relatório. Cada linha ': Legenda {#tbl-nome}' do relatorio_pi.md chama aqui a função
marcada com @tabela("tbl-nome"), que monta um DataFrame e termina com return tabela_abnt(...).

tabela_abnt(df, nomes={coluna: "Cabeçalho"}, casas={coluna: casas_decimais}) formata os números no
padrão brasileiro e desenha a tabela no padrão ABNT/IBGE (sem linhas verticais). Tabelas de texto
fixo podem ser escritas direto no relatorio_pi.md, com | ... |.
"""
from __future__ import annotations

import pandas as pd

from abnt import numero_br, percentual_br, tabela_abnt
from abnt.markdown import ErroRelatorio
from fontes import do_log, metricas, resultados, saidas

TABELAS = {}


def tabela(rotulo):
    def registrar(funcao):
        TABELAS[rotulo] = funcao
        return funcao
    return registrar


def obter(rotulo: str):
    if rotulo not in TABELAS:
        raise ErroRelatorio(f"A tabela @{rotulo} não existe em relatorio/tabelas.py "
                            f"(ou falta a tabela | ... | logo abaixo da legenda no relatorio_pi.md).")
    return TABELAS[rotulo]()


def br(v, casas=0):
    return numero_br(v, casas)


# ============================================================================= dados
@tabela("tbl-inventario")
def inventario():
    log_parc = r"parcelas: (\d+) linhas \| alunos (\d+) \| contratos de plano (\d+) \| vencimento ([\d/]+)-([\d/]+)"
    log_aces = r"acessos: (\d+) linhas \| alunos (\d+) \| ([\d/]+)-([\d/]+)"
    m = metricas()
    linhas = [
        ["Parcelas", "mensalidades, vendas avulsas e acertos, com situação (paga, em aberto ou cancelada)",
         f"vencimentos de {do_log(log_parc, 4, str)} a {do_log(log_parc, 5, str)}",
         f"{br(do_log(log_parc, 1))} parcelas de {br(do_log(log_parc, 2))} alunos e {br(do_log(log_parc, 3))} contratos",
         "matrícula"],
        ["Acessos", "entradas registradas pela catraca",
         f"{do_log(log_aces, 3, str)} a {do_log(log_aces, 4, str)}",
         f"{br(do_log(log_aces, 1))} registros de {br(do_log(log_aces, 2))} alunos", "matrícula"],
        ["Transações", "tentativas de cobrança no cartão recorrente, com o código de retorno",
         f"{m['periodo'][0]} a {m['periodo'][1]}",
         f"{br(m['tentativas'])} tentativas de {br(m['cartoes'])} cartões",
         "nenhuma (titular e cartão mascarado)"],
    ]
    df = pd.DataFrame(linhas, columns=["Export", "Conteúdo", "Período", "Volume", "Chave do aluno"])
    return tabela_abnt(df, larguras=[2.1, 4.4, 3.0, 3.6, 2.9])


@tabela("tbl-status-contratos")
def status_contratos():
    st = saidas("C_status_contratos.csv").set_index("status")
    nomes = [
        ("renovacao", "Renovação, sem parcela cancelada"),
        ("troca_ou_renovacao", "Troca de plano ou renovação antecipada"),
        ("coberto_por_contrato_sobreposto", "Coberto por outro contrato do aluno"),
        ("saida_sem_renovar", "Saída ao fim do contrato, sem renovar"),
        ("saida_com_cancelamento", "Saída com parcelas canceladas"),
        ("em_curso_ou_censurado", "Em curso ou sem tempo de observação"),
        ("All", "**Total**"),
    ]
    df = pd.DataFrame([[rotulo, int(st.loc[k, "All"]), int(st.loc[k, "True"])] for k, rotulo in nomes],
                      columns=["Situação do contrato", "Contratos", "Com parcela cancelada"])
    return tabela_abnt(df)


@tabela("tbl-problema")
def problema():
    m = metricas()
    df = pd.DataFrame([
        ["Tentativas de cobrança no cartão", br(m["tentativas"])],
        ["Aprovação por tentativa", percentual_br(m["aprovacao_geral"], 1)],
        ["Cartão-mês recusado por código irreversível que nunca aprovou", br(m["irrev_cartao_mes"])],
        ["Re-tentativas inúteis depois dessas recusas", br(m["irrev_tentativas_inuteis"])],
        ["Dias entre a primeira e a última re-tentativa inútil (mediana)", br(m["irrev_dias_insistindo_mediana"])],
        ["Mensalidades nessa situação", "R$\u00a0" + br(m["irrev_valor"], 2)],
    ], columns=["Indicador", "Valor"])
    return tabela_abnt(df, alinhamentos={"Valor": "dir"})


# ============================================================================= modelo
@tabela("tbl-metricas")
def metricas_modelo():
    m = metricas()
    df = pd.DataFrame([
        ["AUC no teste", br(m["auc_teste"], 3), br(m["auc_teste_referencia_codigo"], 3) + " (taxa por código da recusa)"],
        ["AUC no treino", br(m["auc_treino"], 3), "–"],
        ["Escore de Brier no teste", br(m["brier_teste"], 4), br(m["brier_teste_constante"], 4) + " (taxa constante)"],
        ["Re-tentativas no teste", br(m["retentativas_teste"]), "–"],
        ["Aprovações no teste", br(m["aprov_teste"]), "–"],
    ], columns=["Métrica", "Modelo", "Referência"])
    return tabela_abnt(df, alinhamentos={"Modelo": "dir"})


@tabela("tbl-calibracao")
def calibracao():
    c = resultados("calibracao_teste.csv").sort_values("faixa")
    df = pd.DataFrame({
        "Quintil": [f"{int(f) + 1}º" + (" (menor chance)" if i == 0 else " (maior chance)" if i == len(c) - 1 else "")
                    for i, f in enumerate(c["faixa"])],
        "Re-tentativas": c["n"].astype(int),
        "Probabilidade média prevista": [percentual_br(v, 1) for v in c["p_media"]],
        "Taxa observada": [percentual_br(v, 1) for v in c["taxa_real"]],
    })
    return tabela_abnt(df, alinhamentos={"Probabilidade média prevista": "dir", "Taxa observada": "dir"})


@tabela("tbl-regras")
def regras():
    m = metricas()
    df = pd.DataFrame([
        ["Códigos irreversíveis", "re-tentativa aprova no máximo 1%, com pelo menos 15 casos",
         ", ".join(m["codigos_irreversiveis"])],
        ["Teto de falhas", "aprovação abaixo de 1% a partir de k recusas seguidas, entre os códigos recuperáveis "
         "(pelo menos 30 casos)", f"{m['teto_falhas']} recusas seguidas"],
        ["Limiar do modelo", "mantém 95% das aprovações do treino", "P(aprovação) ≥ " + br(m["limiar_modelo"], 4)],
        ["Regularização", "maior AUC na validação temporal dentro do treino", "λ = " + br(m["l2"], 0)],
    ], columns=["Regra", "Critério", "Valor aprendido"])
    return tabela_abnt(df, larguras=[3.4, 7.4, 5.2])


@tabela("tbl-politicas")
def politicas():
    p = resultados("politicas_teste.csv").sort_values("tentativas", ascending=False)
    base = p.iloc[0]
    df = pd.DataFrame({
        "Política": p["politica"],
        "Re-tentativas": p["tentativas"].astype(int),
        "% do atual": [percentual_br(t / base["tentativas"], 0) for t in p["tentativas"]],
        "Aprovações": p["aprovacoes"].astype(int),
        "% mantidas": [percentual_br(a / base["aprovacoes"], 0) for a in p["aprovacoes"]],
        "Aprovações a cada 100 tentativas": [numero_br(100 * a / t, 1) for a, t in zip(p["aprovacoes"], p["tentativas"])],
    })
    return tabela_abnt(df, larguras=[5.0, 2.2, 1.7, 2.2, 1.9, 3.0],
                       alinhamentos={"% do atual": "dir", "% mantidas": "dir", "Aprovações a cada 100 tentativas": "dir"})


@tabela("tbl-fila")
def fila():
    f = resultados("fila_resumo.csv")
    total = f["valor"].sum()
    df = pd.DataFrame({
        "Ação recomendada": f["grupo"],
        "Cartões": f["cartoes"].astype(int),
        "Valor pendente (R$)": f["valor"],
        "% do valor": [percentual_br(v / total, 0) for v in f["valor"]],
    })
    df.loc[len(df)] = ["**Total**", int(f["cartoes"].sum()), total, percentual_br(1, 0)]
    return tabela_abnt(df, casas={"Valor pendente (R$)": 2}, alinhamentos={"% do valor": "dir"})


@tabela("tbl-fila-exemplos")
def fila_exemplos():
    a = resultados("fila_amostra.csv")
    df = pd.DataFrame({
        "Cartão": a["id"],
        "Valor (R$)": a["valor"],
        "Última recusa": a["ultimo_codigo"].astype(str),
        "Recusas seguidas": a["recusas_seguidas"].astype(int),
        "Ação": a["acao"],
        "Motivo": a["motivo"],
    })
    return tabela_abnt(df, casas={"Valor (R$)": 2}, larguras=[1.9, 1.5, 1.5, 1.6, 3.5, 6.0],
                       alinhamentos={"Última recusa": "centro", "Recusas seguidas": "centro"})


@tabela("tbl-frequencia")
def frequencia():
    h = saidas("H_frequencia_por_familia_de_plano.csv").sort_values("alunos", ascending=False)
    df = pd.DataFrame({
        "Família de plano": h["familia"],
        "Alunos": h["alunos"].astype(int),
        "Dias com acesso (mediana)": h["mediana"].astype(float),
        "Sem nenhum acesso": [percentual_br(v, 0) for v in h["pct_zero"]],
    })
    return tabela_abnt(df, casas={"Dias com acesso (mediana)": 1}, alinhamentos={"Sem nenhum acesso": "dir"})
