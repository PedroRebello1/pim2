"""Gera o deck da apresentação (HTML navegável + PDF 16:9) a partir dos resultados do motor.

Uso: python gerar_slides.py   (depois de rodar ../motor_cobranca/rodar.py)
Navegação no HTML: setas / espaço / PgUp-PgDn; F = tela cheia.
"""
import json
import math
import subprocess
from pathlib import Path

import pandas as pd

AQUI = Path(__file__).resolve().parent
RES = AQUI.parent / "resultados"
ESTUDO = AQUI.parent.parent / "saidas"
EDGE = Path(r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe")

m = json.loads((RES / "metricas.json").read_text(encoding="utf-8"))
pol = pd.read_csv(RES / "politicas_teste.csv")
roc = pd.read_csv(RES / "roc_teste.csv")
fila = pd.read_csv(RES / "fila_resumo.csv")
amostra = pd.read_csv(RES / "fila_amostra.csv")
coef = pd.read_csv(RES / "coeficientes.csv").set_index("atributo")
rec = pd.read_csv(ESTUDO / "G_recuperacao_por_codigo_primeira_recusa.csv", encoding="utf-8-sig")
coorte = pd.read_csv(ESTUDO / "D_coorte_contratos_por_numeracao.csv", encoding="utf-8-sig").sort_values("idade_meses")


def dec(v, casas=1):
    """Número no formato pt-BR (milhar com ponto, decimal com vírgula)."""
    return f"{v:,.{casas}f}".replace(",", "X").replace(".", ",").replace("X", ".")


def brl(v):
    return f"R$ {dec(v, 2)}"


def mil(v):
    return f"R$ {dec(v / 1000, 1)} mil".replace(",0 mil", " mil")


def pct(v, casas=0):
    return f"{dec(v * 100, casas)}%"


def num(v):
    return dec(v, 0)


# ---------------------------------------------------------------- componentes gráficos
def barras_recuperacao():
    out = []
    for _, r in rec.iterrows():
        v = r["taxa_recuperacao"] * 100
        cls = "ok" if v >= 10 else "no"
        lab = "51 · saldo insuficiente" if str(r["codigoRetorno"]) == "51" else str(r["codigoRetorno"])
        out.append(f"<div class='hb'><span class='hl'>{lab}</span><span class='ht'><i class='{cls}' style='width:{max(v, .8) / 40 * 100:.1f}%'></i></span>"
                   f"<b>{v:.0f}%</b><em>n={r['casos']}</em></div>")
    return "".join(out)


def roc_svg(w=360, h=300):
    pad = 36
    pts = " ".join(f"{pad + (w - pad - 10) * x:.1f},{h - pad - (h - pad - 10) * y:.1f}" for x, y in zip(roc["fpr"], roc["tpr"]))
    grade = "".join(f"<line x1='{pad}' x2='{w - 10}' y1='{h - pad - (h - pad - 10) * g:.1f}' y2='{h - pad - (h - pad - 10) * g:.1f}' stroke='#ecebe7'/>"
                    f"<text x='{pad - 6}' y='{h - pad - (h - pad - 10) * g + 4:.1f}' font-size='11' fill='#898781' text-anchor='end'>{g:.1f}</text>"
                    for g in (0, .25, .5, .75, 1))
    return (f"<svg width='{w}' height='{h}' viewBox='0 0 {w} {h}'>{grade}"
            f"<line x1='{pad}' y1='{h - pad}' x2='{w - 10}' y2='10' stroke='#c9c7c0' stroke-dasharray='4 4'/>"
            f"<polyline points='{pts}' fill='none' stroke='#2a78d6' stroke-width='2.5'/>"
            f"<text x='{(w + pad) / 2}' y='{h - 6}' font-size='12' fill='#52514e' text-anchor='middle'>falsos positivos (taxa)</text>"
            f"<text x='12' y='{(h - pad) / 2}' font-size='12' fill='#52514e' text-anchor='middle' transform='rotate(-90 12 {(h - pad) / 2})'>aprovações capturadas</text>"
            f"<text x='{w - 16}' y='{h - pad - 14}' font-size='12' fill='#898781' text-anchor='end'>acaso (AUC 0,5)</text>"
            f"<text x='{w * 0.62:.0f}' y='{h * 0.6:.0f}' font-size='18' font-weight='700' fill='#1c5cab'>AUC {dec(m['auc_teste'], 2)}</text></svg>")


def fatores():
    itens = [("ult_cod=51", "recusa 51 (saldo)"), ("faixa_dia=10-14", "dias 10–14 do mês"),
             ("ult_cod=62", "recusa 62"), ("bandeira=4", "cartão Visa"),
             ("bandeira=2", "Mastercard série 2"), ("faixa_dia=5-7", "dias 5–7 do mês"), ("ult_cod=Pac014", "recusa Pac014")]
    out = []
    for k, rot in itens:
        orr = coef.loc[k, "razao_chances"]
        largura = min(abs(math.log(orr)) / 1.8 * 100, 100)  # escala log: ×6 ou ÷6 = barra cheia
        out.append(f"<div class='fx'><span class='fl'>{rot}</span><span class='ft'>"
                   f"<i class='{'up' if orr >= 1 else 'dn'}' style='width:{largura:.0f}%'></i></span><b>×{dec(orr, 2)}</b></div>")
    return "".join(out)


def barras_politicas():
    nomes = {"Atual: re-tenta tudo": "Hoje: re-tenta tudo",
             "Regra 1: não re-tentar códigos irreversíveis": "Regra 1 · códigos irreversíveis",
             "Modelo: re-tentar se P(aprovação) ≥ limiar": "Modelo · P(aprovação) ≥ limiar"}
    out = []
    for _, r in pol.iterrows():
        nome = nomes.get(r["politica"], f"Regra 2 · regra 1 + teto de {m['teto_falhas']} falhas")
        out.append(f"<div class='pg'><div class='pn'>{nome}<span>{dec(r['aprov_por_100'])} aprovações a cada 100 tentativas</span></div>"
                   f"<div class='pb'><div class='pr'><i class='t' style='width:{r['pct_tentativas'] * 100:.0f}%'></i><b>{pct(r['pct_tentativas'])} das tentativas</b></div>"
                   f"<div class='pr'><i class='a' style='width:{r['pct_aprovacoes'] * 100:.0f}%'></i><b>{pct(r['pct_aprovacoes'])} das aprovações</b></div></div></div>")
    return "".join(out)


def colunas_retencao():
    out = []
    for _, r in coorte.iterrows():
        v = r["pct_de_clientes_atuais"]
        out.append(f"<div class='rc'><span class='rv'>{v * 100:.0f}</span><i style='height:{v * 100:.0f}%'></i><span class='rl'>{int(r['idade_meses'])}</span></div>")
    return "".join(out)


def linha_cob(rot, cel):
    css = {"P": "pago", "C": "canc", ".": "vazio", "#": "cob", "_": "sem"}
    return f"<div class='cr'><span>{rot}</span>" + "".join(f"<i class='{css[c]}'></i>" for c in cel) + "</div>"


tabela_fila = "".join(
    f"<tr><td>{r['id']}</td><td>{brl(r['valor'])}</td><td>{r['ultimo_codigo']}</td><td>{r['recusas_seguidas']}</td>"
    f"<td><b>{r['acao']}</b></td><td>{r['motivo']}</td></tr>" for _, r in amostra.iterrows())
fila_g = fila.set_index("grupo")


def fila_card(grupo, rotulo, cls):
    if grupo not in fila_g.index:
        return ""
    r = fila_g.loc[grupo]
    return f"<div class='fc {cls}'><div class='fn'>{int(r['cartoes'])}</div><div class='fv'>{mil(r['valor'])}</div><div class='ft2'>{rotulo}</div></div>"


p_atual, p_mod, p_r2 = pol.iloc[0], pol.iloc[3], pol.iloc[2]

SLIDES = [
    # 1 ----------------------------------------------------------------------
    f"""<section class='slide capa'>
      <div class='kicker'>Projeto Integrador · Ciência de Dados e Machine Learning · CEUB</div>
      <h1>Ciclo de vida do aluno</h1>
      <p class='sub'>PIM II: o rumo do projeto e os primeiros resultados com dados reais</p>
      <div class='capa-rod'><div><b>Parceiro</b>Academia Equilíbrio e Movimento · Brasília</div>
      <div><b>Grupo</b>Pedro Rebello · Guilherme Mendes · Eduardo Barros · Gabriel Francisco</div>
      <div><b>Data</b>Outubro de 2026</div></div></section>""",
    # 2 ----------------------------------------------------------------------
    """<section class='slide'><div class='kicker'>Ponto de partida</div>
      <h2>No PIM I, previmos churn. Neste semestre, testamos as premissas nos dados reais.</h2>
      <div class='cols2'>
        <div class='card'><h3>PIM I</h3><ul>
          <li>Classificador de churn (XGBoost, ROC-AUC 0,849)</li>
          <li>Rótulo: aluno com <b>≥ 1 parcela cancelada</b> = churn</li>
          <li>Base: histórico de parcelas</li></ul></div>
        <div class='card azul'><h3>PIM II: o que fizemos</h3><ul>
          <li>Analisamos os 3 exports do sistema da academia: <b>parcelas, catraca e tentativas de cobrança no cartão</b></li>
          <li>Validamos cada premissa contra a catraca e a numeração interna do sistema</li>
          <li>Resultado: <b>três descobertas mudaram o rumo do projeto</b></li></ul></div>
      </div></section>""",
    # 3 ----------------------------------------------------------------------
    """<section class='slide'><div class='kicker'>O que os dados mostraram</div>
      <h2>Três descobertas</h2>
      <div class='cols3'>
        <div class='big'><div class='n'>93,5%</div><div class='t'>dos alunos que o rótulo do PIM I chamaria de churn <b>continuam com plano ativo</b></div>
          <p>Parcela cancelada é troca de plano ou renovação (ex.: Black Friday → Natal), não saída.</p></div>
        <div class='big'><div class='n'>205 → 1.153</div><div class='t'>alunos com plano por mês: a curva <b>só sobe</b></div>
          <p>O relatório de parcelas só traz quem é cliente hoje. Com ele, churn não é mensurável.</p></div>
        <div class='big'><div class='n'>30%</div><div class='t'>das tentativas de cobrança no cartão são aprovadas</div>
          <p>A "inadimplência" é, na prática, <b>falha de cobrança</b>: R$ 42,6 mil ficaram sem aprovação em set/26.</p></div>
      </div></section>""",
    # 4 ----------------------------------------------------------------------
    f"""<section class='slide'><div class='kicker'>Base comum do projeto</div>
      <h2>Trocas de plano: o estado do aluno é medido pela cobertura, não pelo contrato</h2>
      <div class='cols2 mid'>
        <div class='card'>
          <div class='cx'><div class='cxt'>Troca de plano</div>{linha_cob('Contrato A', 'PPPPCCCC')}{linha_cob('Contrato B', '....PPPP')}{linha_cob('Aluno', '########')}
            <div class='cap'>→ coberto o tempo todo: <b>troca, não saída</b></div></div>
          <div class='cx'><div class='cxt'>Saída</div>{linha_cob('Contrato A', 'PPPPCCCC')}{linha_cob('Aluno', '####____')}
            <div class='cap'>→ meses sem cobertura: <b>saída</b></div></div>
          <div class='leg'><i class='pago'></i>parcela paga/em aberto <i class='canc'></i>cancelada <i class='cob'></i>mês coberto <i class='sem'></i>sem cobertura</div>
        </div>
        <ul class='lista'>
          <li><b>Mês coberto:</b> existe mensalidade não cancelada em <i>qualquer</i> contrato do aluno</li>
          <li><b>Saída:</b> N meses seguidos sem cobertura (N = 2, a calibrar com a academia)</li>
          <li><b>Censura:</b> meses recentes ficam sem rótulo → análise de sobrevivência</li>
          <li>Tabela <b>aluno × mês</b> já construída: serve aos dois módulos do projeto</li>
        </ul>
      </div></section>""",
    # 5 ----------------------------------------------------------------------
    f"""<section class='slide'><div class='kicker'>Problema escolhido para o PIM II</div>
      <h2>O sistema insiste em cartões que não vão aprovar</h2>
      <div class='cols2 mid'>
        <div>
          <div class='stats'>
            <div><b>{num(m['irrev_cartao_mes'])}</b><span>cartão-mês com recusa "irreversível" que nunca aprovaram</span></div>
            <div><b>{num(m['irrev_tentativas_inuteis'])}</b><span>re-tentativas inúteis depois dessas recusas</span></div>
            <div><b>{m['irrev_dias_insistindo_mediana']:.0f} dias</b><span>de insistência (mediana) até alguém agir</span></div>
            <div><b>{mil(m['irrev_valor'])}</b><span>em mensalidades nessa situação (ago–out)</span></div>
          </div>
          <p class='nota'>Cobrança em lote diário às 12h · 86% das recusas vêm de cartões que nunca aprovam · as bandeiras limitam re-tentativas e a adquirente prevê tarifa para o excesso.</p>
        </div>
        <div class='card'><div class='ct'>Recusado na 1ª tentativa: % que aprovou depois, no mesmo mês</div>{barras_recuperacao()}
          <div class='leg'><i class='okb'></i>vale re-tentar <i class='nob'></i>não recupera</div></div>
      </div></section>""",
    # 6 ----------------------------------------------------------------------
    """<section class='slide'><div class='kicker'>A solução</div>
      <h2>Motor de Cobrança Inteligente</h2>
      <p class='lead'>A cada recusa, o motor estima a chance de a próxima tentativa aprovar e decide: <b>re-tentar (e em que dia)</b> ou <b>acionar o aluno</b>.</p>
      <div class='flow'>
        <div class='node'><b>1. Export diário</b>tentativas de cobrança e parcelas</div><span>→</span>
        <div class='node'><b>2. Histórico do cartão</b>último código, falhas seguidas, dia do mês, emissor</div><span>→</span>
        <div class='node azul'><b>3. Modelo</b>P(aprovação) da próxima tentativa</div><span>→</span>
        <div class='node azul'><b>4. Política</b>regras aprendidas + limiar do modelo</div><span>→</span>
        <div class='node'><b>5. Fila do dia</b>ação + motivo, por cartão</div>
      </div>
      <div class='acoes'>
        <div><b>Re-tentar em dd/mm</b>quando a chance compensa: o dia é escolhido pelo modelo</div>
        <div><b>Pedir novo cartão ou PIX</b>após códigos que não se recuperam: avisa no 1º dia, não depois de semanas</div>
        <div><b>Parar e contatar</b>a partir do teto de falhas seguidas, respeitando os limites das bandeiras</div>
      </div>
      <p class='nota'>O desfecho de cada ação é registrado e realimenta o modelo. Os dados pessoais ficam só na fila interna da academia.
      É o 1º módulo da plataforma: usa a mesma base aluno × mês que o módulo de retenção do PIM III.</p>
    </section>""",
    # 7 ----------------------------------------------------------------------
    f"""<section class='slide'><div class='kicker'>Resultado 1: o modelo</div>
      <h2>Prevê bem quais re-tentativas vão aprovar, em um mês que ele nunca viu</h2>
      <div class='cols3b'>
        <div class='card'>{roc_svg()}</div>
        <div>
          <div class='stats one'>
            <div><b>AUC {dec(m['auc_teste'], 2)}</b><span>no teste de outubro, contra {dec(m['auc_teste_referencia_codigo'], 2)} usando só o código da recusa</span></div>
            <div><b>Calibrado</b><span>no quintil de maior risco, previu 20% de aprovação e ocorreram 21%</span></div>
          </div>
          <p class='nota'>Regressão logística com regularização L2 (implementada em numpy). λ escolhido por validação temporal.
          Treino: 15/08–30/09 ({num(m['retentativas_treino'])} re-tentativas). Teste: 01–15/10 ({num(m['retentativas_teste'])} re-tentativas, {m['aprov_teste']} aprovações).</p>
        </div>
        <div class='card'><div class='ct'>O que muda a chance de aprovar (razão de chances)</div>{fatores()}
          <p class='nota'>Leitura de direção, não de causa.</p></div>
      </div></section>""",
    # 8 ----------------------------------------------------------------------
    f"""<section class='slide'><div class='kicker'>Resultado 2: a política</div>
      <h2>Até {pct(1 - p_r2['pct_tentativas'])} menos tentativas, mantendo {pct(p_r2['pct_aprovacoes'])} das aprovações</h2>
      <div class='cols2 mid w'>
        <div class='card'>{barras_politicas()}
          <div class='leg'><i class='tb'></i>tentativas feitas <i class='ab'></i>aprovações mantidas · base: política atual em outubro</div></div>
        <ul class='lista'>
          <li><b>Hoje:</b> {dec(p_atual['aprov_por_100'])} aprovações a cada 100 re-tentativas</li>
          <li><b>Modelo:</b> evita {pct(1 - p_mod['pct_tentativas'])} das re-tentativas e perde só {int(p_mod['aprovacoes_perdidas'])} das {int(p_atual['aprovacoes'])} aprovações</li>
          <li>Menos tentativas = menos tarifa de retentativa e menos risco de estourar o limite das bandeiras</li>
          <li>Os cartões que param de ser cobrados <b>vão para contato no mesmo dia</b></li>
          <li class='nota'>Avaliação por replay: mede com rigor o "parar de insistir". O ganho de "re-tentar no dia certo" exige um piloto com a academia.</li>
        </ul>
      </div></section>""",
    # 9 ----------------------------------------------------------------------
    f"""<section class='slide'><div class='kicker'>Resultado 3: o produto</div>
      <h2>A fila de ação de {m['fila_data'][:5]}: {m['fila_cartoes']} cartões, {mil(m['fila_valor'])} pendentes</h2>
      <div class='fcs'>
        {fila_card('Contato: novo cartão ou PIX', 'pedir novo cartão ou PIX hoje', 'c1')}
        {fila_card('Contato: parar re-tentativas', 'parar re-tentativas e contatar', 'c2')}
        {fila_card('Re-tentar em data indicada', 're-tentar na data indicada pelo modelo', 'c3')}
      </div>
      <table class='tb'><tr><th>Cartão</th><th>Valor</th><th>Último código</th><th>Falhas seguidas</th><th>Ação</th><th>Motivo</th></tr>{tabela_fila}</table>
      <p class='nota'>IDs pseudonimizados nesta apresentação. A versão interna traz o titular, para a recepção agir.</p>
    </section>""",
    # 10 ---------------------------------------------------------------------
    f"""<section class='slide'><div class='kicker'>Próximo módulo (PIM III)</div>
      <h2>Retenção: uma prévia já indica o tamanho do problema</h2>
      <div class='cols2 mid w'>
        <div class='card'><div class='ct'>% dos contratos emitidos cujo titular ainda é cliente, por idade do contrato (meses)</div>
          <div class='rchart'>{colunas_retencao()}</div>
          <p class='nota'>Estimado pelas lacunas da numeração sequencial de contratos, já que o export só traz quem ainda é cliente.</p></div>
        <ul class='lista'>
          <li>Após 12 meses, só <b>21–40%</b> dos contratos ainda são de clientes ativos</li>
          <li><b>16,7%</b> dos alunos pagantes não passaram na catraca no mês. Nas promoções, 31%</li>
          <li><b>23%</b> dos ativos já saíram e voltaram: a reativação é relevante</li>
          <li>Método: <b>análise de sobrevivência</b> (Kaplan–Meier, Cox) sobre a tabela aluno × mês, com sinais de engajamento</li>
          <li>Depende de um export <b>com ex-alunos</b> e de 12–24 meses de catraca, a pedir agora</li>
        </ul>
      </div></section>""",
    # 11 ---------------------------------------------------------------------
    """<section class='slide'><div class='kicker'>Rumo do projeto</div>
      <h2>Roteiro</h2>
      <div class='road'>
        <div class='ph p0'><div class='w'>Agora</div><ul><li>Validar as dores prioritárias com o dono</li><li>Pedir os exports com ex-alunos, 12–24 meses de catraca e mais meses de cobrança</li><li>Confirmar o significado dos códigos Pac*</li></ul></div>
        <div class='ph'><div class='w'>PIM II</div><ul><li>Base comum: pipeline, dicionário e tabela aluno × mês ✔</li><li>Motor de cobrança: modelo e políticas ✔</li><li><b>Piloto com a academia:</b> metade dos cartões com a política nova (teste A/B)</li><li>Painel e registro de desfechos</li></ul></div>
        <div class='ph p3'><div class='w'>PIM III</div><ul><li>Retenção com análise de sobrevivência</li><li>Engajamento (catraca) como sinal antecipado</li><li>Promoções, LTV e reativação</li><li>Avaliação com a academia e relatório final</li></ul></div>
      </div></section>""",
    # 12 ---------------------------------------------------------------------
    f"""<section class='slide'><div class='kicker'>Honestidade metodológica</div>
      <h2>Limitações e próximos passos</h2>
      <div class='cols2'>
        <div class='card'><h3>Limitações</h3><ul>
          <li>Só 2 meses de tentativas de cobrança; o teste tem {m['aprov_teste']} aprovações: <b>precisa de mais meses</b></li>
          <li>O replay não observa o contrafactual de "re-tentar em outro dia"</li>
          <li>Os códigos Pac* são do sistema de gestão: o significado precisa ser confirmado</li>
          <li>Transação → aluno vinculada por heurística (63% das aprovações)</li></ul></div>
        <div class='card azul'><h3>Próximos passos</h3><ul>
          <li>Re-treinar com os novos exports: o pipeline já aceita mais arquivos sem mudar o código</li>
          <li>Piloto A/B com a recepção usando a fila diária</li>
          <li>Medir R$ recuperado, tentativas evitadas e dias até regularizar</li>
          <li>Iniciar o módulo de retenção (PIM III)</li></ul></div>
      </div>
      <p class='fim'>Obrigado! · Perguntas?</p></section>""",
]

CSS = """
@page { size: 13.333in 7.5in; margin: 0; }
* { box-sizing: border-box; -webkit-print-color-adjust: exact; print-color-adjust: exact; }
html, body { margin: 0; background: #2b2b29; font-family: 'Segoe UI', Arial, sans-serif; color: #1d1d1b; }
.slide { width: 1280px; height: 720px; background: #fff; position: relative; padding: 52px 64px 48px; overflow: hidden;
         display: flex; flex-direction: column; }
.corpo { flex: 1; display: flex; flex-direction: column; justify-content: center; padding-bottom: 28px; }
.slide::after { content: 'PIM II · Ciclo de vida do aluno'; position: absolute; left: 64px; bottom: 22px; font-size: 12px; color: #a9a7a0; }
.slide .pg-n { position: absolute; right: 64px; bottom: 20px; font-size: 12px; color: #a9a7a0; }
.kicker { font-size: 14px; font-weight: 700; letter-spacing: 1.4px; text-transform: uppercase; color: #2a78d6; margin-bottom: 10px; }
h1 { font-size: 64px; margin: 0 0 12px; color: #0b0b0b; letter-spacing: -1px; }
h2 { font-size: 32px; line-height: 1.18; margin: 0 0 26px; color: #0b0b0b; letter-spacing: -0.3px; max-width: 1100px; }
h3 { font-size: 20px; margin: 0 0 12px; color: #0b0b0b; }
ul { margin: 0; padding-left: 22px; } li { font-size: 20px; line-height: 1.4; margin-bottom: 12px; }
.card li { font-size: 21px; } .card h3 { font-size: 24px; margin-bottom: 16px; }
.cols2 > .card { padding: 28px 32px; }
b { color: #0b0b0b; }
.lead { font-size: 22px; line-height: 1.4; margin: -8px 0 26px; color: #2b2b29; max-width: 1080px; }
.nota { font-size: 14px; color: #6b6a65; line-height: 1.4; margin-top: 14px; }
li.nota { list-style: none; margin-left: -22px; }
.card { background: #f7f7f5; border: 1px solid #ecebe7; border-radius: 14px; padding: 22px 26px; }
.card.azul { background: #f3f6fb; border-color: #cde2fb; }
.ct { font-size: 15px; font-weight: 600; color: #0b0b0b; margin-bottom: 12px; }
.cols2 { display: grid; grid-template-columns: 1fr 1fr; gap: 32px; }
.cols2.mid { align-items: center; } .cols2.w { grid-template-columns: 1.25fr 1fr; }
.cols3 { display: grid; grid-template-columns: repeat(3, 1fr); gap: 28px; }
.cols3b { display: grid; grid-template-columns: 384px 0.85fr 1.15fr; gap: 24px; align-items: start; }
/* capa */
.capa { background: linear-gradient(135deg, #0d366b 0%, #1c5cab 60%, #2a78d6 100%); color: #fff; padding: 110px 80px; }
.capa::after { color: rgba(255,255,255,.5); left: 80px; }
.capa .kicker { color: #cde2fb; } .capa h1 { color: #fff; } .capa b { color: #fff; }
.capa .sub { font-size: 28px; color: #e3eefc; margin: 0 0 90px; }
.capa-rod { display: grid; grid-template-columns: 1fr 1.6fr 0.8fr; gap: 30px; font-size: 17px; color: #e3eefc; border-top: 1px solid rgba(255,255,255,.3); padding-top: 22px; }
.capa-rod b { display: block; font-size: 13px; letter-spacing: 1.2px; text-transform: uppercase; color: #9ec5f4; margin-bottom: 6px; }
/* descobertas */
.big { background: #f3f6fb; border-radius: 14px; padding: 30px 30px 26px; min-height: 400px; }
.big .n { font-size: 52px; font-weight: 700; color: #1c5cab; line-height: 1.05; margin-bottom: 14px; }
.big .t { font-size: 20px; line-height: 1.35; color: #1d1d1b; margin-bottom: 18px; }
.big p { font-size: 17px; line-height: 1.45; color: #52514e; border-top: 1px solid #cde2fb; padding-top: 16px; margin: 0; }
/* cobertura */
.cx { margin-bottom: 18px; } .cxt { font-size: 15px; font-weight: 600; color: #52514e; margin-bottom: 6px; }
.cr { display: flex; align-items: center; gap: 4px; height: 30px; } .cr span { width: 110px; font-size: 16px; }
.cr i, .leg i { display: inline-block; width: 40px; height: 22px; border-radius: 4px; }
.leg i { width: 16px; height: 14px; vertical-align: -2px; margin: 0 6px 0 14px; }
.leg i:first-child { margin-left: 0; }
.pago { background: #6da7ec; } .canc { background: repeating-linear-gradient(45deg, #c9c7c0 0 2px, #f0efec 2px 6px); border: 1px solid #b5b3ad; }
.cob { background: #1c5cab; } .sem { background: #fff; border: 1.5px dashed #a9a7a0; } .vazio { background: transparent; }
.cap { font-size: 16px; margin: 6px 0 0 114px; }
.leg { font-size: 14px; color: #52514e; margin-top: 12px; }
.lista li { font-size: 20px; margin-bottom: 16px; }
/* stats */
.stats { display: grid; grid-template-columns: 1fr 1fr; gap: 18px; }
.stats.one { grid-template-columns: 1fr; }
.stats div { border-left: 4px solid #2a78d6; padding: 4px 0 4px 16px; }
.stats b { display: block; font-size: 40px; color: #1c5cab; line-height: 1.1; }
.stats span { font-size: 18px; color: #2b2b29; line-height: 1.35; display: block; margin-top: 4px; }
.stats.one b { font-size: 36px; } .stats.one span { font-size: 17px; }
/* barras horizontais de recuperação */
.hb { display: grid; grid-template-columns: 180px 1fr 46px 58px; align-items: center; gap: 10px; height: 34px; font-size: 16px; }
.ht { height: 14px; background: #ecebe7; border-radius: 4px; } .ht i { display: block; height: 100%; border-radius: 0 4px 4px 0; }
.ht i.ok, .okb { background: #2a78d6; } .ht i.no, .nob { background: #a9a7a0; }
.hb b { text-align: right; } .hb em { font-style: normal; font-size: 13px; color: #898781; }
/* fluxo */
.flow { display: flex; align-items: stretch; gap: 10px; margin-bottom: 26px; }
.flow span { align-self: center; color: #898781; font-size: 24px; }
.node { flex: 1; border: 1.5px solid #c9c7c0; border-radius: 12px; padding: 16px; font-size: 16px; line-height: 1.35; color: #52514e; background: #fff; }
.node b { display: block; font-size: 18px; color: #0b0b0b; margin-bottom: 4px; }
.node.azul { background: #f3f6fb; border-color: #86b6ef; }
.acoes { display: grid; grid-template-columns: repeat(3, 1fr); gap: 20px; }
.acoes div { background: #f7f7f5; border-radius: 12px; padding: 20px 22px; font-size: 17px; line-height: 1.4; color: #52514e; border-top: 4px solid #2a78d6; }
.acoes b { display: block; font-size: 20px; color: #0b0b0b; margin-bottom: 6px; }
/* fatores */
.fx { display: grid; grid-template-columns: 1fr 96px 58px; align-items: center; gap: 10px; min-height: 36px; font-size: 16px; }
.ft { height: 14px; position: relative; background: #f0efec; border-radius: 4px; }
.ft i { display: block; height: 100%; border-radius: 4px; } .ft i.up { background: #2a78d6; } .ft i.dn { background: #d95926; }
.fx b { text-align: right; }
/* políticas */
.pg { display: grid; grid-template-columns: 250px 1fr; gap: 16px; align-items: center; padding: 10px 0; border-bottom: 1px solid #ecebe7; }
.pg:last-of-type { border-bottom: 0; }
.pn { font-size: 16px; font-weight: 600; color: #0b0b0b; } .pn span { display: block; font-size: 13px; font-weight: 400; color: #6b6a65; margin-top: 2px; }
.pr { display: flex; align-items: center; gap: 10px; height: 26px; font-size: 14px; }
.pr i { display: block; height: 16px; border-radius: 0 4px 4px 0; min-width: 2px; } .pr b { white-space: nowrap; font-weight: 600; color: #2b2b29; }
.pr i.t, .tb2, i.tb { background: #a9a7a0; } .pr i.a, i.ab { background: #2a78d6; }
/* fila */
.fcs { display: grid; grid-template-columns: repeat(3, 1fr); gap: 20px; margin-bottom: 22px; }
.fc { border-radius: 12px; padding: 16px 22px; background: #f3f6fb; border-left: 6px solid #2a78d6; }
.fc.c1 { border-color: #1c5cab; } .fc.c2 { border-color: #898781; background: #f7f7f5; } .fc.c3 { border-color: #2a78d6; }
.fn { font-size: 38px; font-weight: 700; color: #0b0b0b; line-height: 1; display: inline-block; margin-right: 12px; }
.fv { font-size: 22px; font-weight: 600; color: #1c5cab; display: inline-block; }
.ft2 { font-size: 16px; color: #52514e; margin-top: 6px; }
table.tb { width: 100%; border-collapse: collapse; font-size: 16px; }
.tb th { text-align: left; color: #52514e; font-weight: 600; border-bottom: 1.5px solid #b5b3ad; padding: 8px 10px; }
.tb td { border-bottom: 1px solid #ecebe7; padding: 9px 10px; vertical-align: top; }
/* retenção */
.rchart { display: flex; align-items: flex-end; gap: 4px; height: 260px; padding-top: 22px; border-bottom: 1px solid #c9c7c0; margin-bottom: 26px; }
.rc { flex: 1; height: 100%; display: flex; flex-direction: column; justify-content: flex-end; align-items: center; position: relative; }
.rc i { width: 100%; background: #6da7ec; border-radius: 3px 3px 0 0; display: block; }
.rv { font-size: 11px; color: #52514e; margin-bottom: 3px; } .rl { position: absolute; bottom: -20px; font-size: 11px; color: #898781; }
/* roteiro */
.road { display: grid; grid-template-columns: 1fr 1.25fr 1.1fr; gap: 28px; }
.ph { border-top: 6px solid #2a78d6; padding-top: 16px; } .ph.p0 { border-color: #898781; } .ph.p3 { border-color: #0d366b; }
.ph .w { font-size: 16px; font-weight: 700; letter-spacing: 1.2px; text-transform: uppercase; color: #52514e; margin-bottom: 12px; }
.fim { position: absolute; right: 64px; bottom: 60px; font-size: 26px; font-weight: 700; color: #1c5cab; margin: 0; }
/* tela: um slide por vez, escalado */
@media screen {
  body { display: flex; align-items: center; justify-content: center; height: 100vh; overflow: hidden; }
  .slide { display: none; position: absolute; top: 50%; left: 50%; transform-origin: center;
           transform: translate(-50%, -50%) scale(var(--k, 1)); box-shadow: 0 10px 40px rgba(0,0,0,.4); }
  .slide.on { display: flex; }
}
@media print { body { background: #fff; } .slide { page-break-after: always; } .slide:last-of-type { page-break-after: auto; } }
"""

JS = """
const s = [...document.querySelectorAll('.slide')]; let i = 0;
s.forEach((el, k) => { const n = document.createElement('div'); n.className = 'pg-n'; n.textContent = (k + 1) + ' / ' + s.length; el.appendChild(n); });
function fit() { document.documentElement.style.setProperty('--k', Math.min(innerWidth / 1280, innerHeight / 720) * 0.96); }
function show(n) { i = Math.max(0, Math.min(s.length - 1, n)); s.forEach((el, k) => el.classList.toggle('on', k === i)); location.hash = i + 1; }
addEventListener('keydown', e => {
  if (['ArrowRight', 'PageDown', ' ', 'Enter'].includes(e.key)) show(i + 1);
  if (['ArrowLeft', 'PageUp', 'Backspace'].includes(e.key)) show(i - 1);
  if (e.key === 'Home') show(0); if (e.key === 'End') show(s.length - 1);
  if (e.key === 'f' || e.key === 'F') document.fullscreenElement ? document.exitFullscreen() : document.documentElement.requestFullscreen();
});
addEventListener('click', e => show(e.clientX > innerWidth / 3 ? i + 1 : i - 1));
addEventListener('resize', fit); fit(); show((parseInt(location.hash.slice(1)) || 1) - 1);
"""

def com_corpo(s):
    """Envolve tudo o que vem depois do título num bloco centralizado verticalmente (exceto a capa)."""
    if "</h2>" not in s:
        return s
    a, b = s.split("</h2>", 1)
    return a + "</h2><div class='corpo'>" + b.replace("</section>", "</div></section>")


SLIDES = [com_corpo(s) for s in SLIDES]
html = (f"<!doctype html><html lang='pt-BR'><head><meta charset='utf-8'><meta name='viewport' content='width=device-width,initial-scale=1'>"
        f"<title>PIM II · Ciclo de vida do aluno</title><style>{CSS}</style></head><body>{''.join(SLIDES)}<script>{JS}</script></body></html>")
saida_html = AQUI / "apresentacao.html"
saida_html.write_text(html, encoding="utf-8")
saida_pdf = AQUI / "apresentacao.pdf"
subprocess.run([str(EDGE), "--headless=new", "--disable-gpu", "--no-pdf-header-footer", f"--print-to-pdf={saida_pdf}",
                saida_html.as_uri()], check=True, timeout=120)
print("HTML:", saida_html, "| PDF:", saida_pdf, saida_pdf.stat().st_size, "bytes")
