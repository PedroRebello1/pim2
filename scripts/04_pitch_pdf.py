"""Gera o pitch técnico em PDF (HTML de impressão -> PDF via Edge headless).

Lê só os agregados de ../saidas/ (gerados pelo 03_analises.py), então os números do pitch são os
mesmos do estudo. Saídas: ../pitch/pitch_tecnico.html e ../Pitch_Tecnico_PIM2.pdf
Uso: python 04_pitch_pdf.py
"""
import subprocess
from pathlib import Path

import pandas as pd

BASE = Path(__file__).resolve().parent.parent
SAIDAS = BASE / "saidas"
HTML = BASE / "pitch" / "pitch_tecnico.html"
PDF = BASE / "Pitch_Tecnico_PIM2.pdf"
EDGE = Path(r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe")

rec = pd.read_csv(SAIDAS / "G_recuperacao_por_codigo_primeira_recusa.csv", encoding="utf-8-sig")
dia = pd.read_csv(SAIDAS / "G_retentativa_apos_51_por_dia_do_mes.csv", encoding="utf-8-sig")
cob = pd.read_csv(SAIDAS / "D_alunos_com_plano_por_mes.csv", encoding="utf-8-sig")


def grafico_recuperacao():
    """Barras horizontais: % de cartão-mês recuperado por código da 1ª recusa."""
    linhas = []
    for _, r in rec.iterrows():
        pct = r["taxa_recuperacao"] * 100
        cls = "bar ok" if pct >= 10 else "bar no"
        rotulo = "51 · saldo insuficiente" if str(r["codigoRetorno"]) == "51" else str(r["codigoRetorno"])
        linhas.append(f"<div class='hrow'><span class='hlab'>{rotulo}</span>"
                      f"<span class='htrack'><span class='{cls}' style='width:{max(pct, 0.6) / 40 * 100:.1f}%'></span></span>"
                      f"<span class='hval'>{pct:.0f}%</span><span class='hn'>n={r['casos']}</span></div>")
    return "\n".join(linhas)


def grafico_dia_do_mes():
    """Colunas: aprovação da re-tentativa após recusa 51, por faixa de dia do mês."""
    vmax = dia["taxa_aprovacao"].max()
    cols = []
    for _, r in dia.iterrows():
        pct = r["taxa_aprovacao"] * 100
        destaque = " hi" if r["faixa"] in ("10-11", "12-14") else ""
        cols.append(f"<div class='vcol'><span class='vval'>{pct:.0f}%</span>"
                    f"<span class='vbar{destaque}' style='height:{r['taxa_aprovacao'] / vmax * 100:.0f}%'></span>"
                    f"<span class='vlab'>{r['faixa']}</span></div>")
    return "\n".join(cols)


def sparkline(w=200, h=58):
    ys = cob["alunos_com_plano"].tolist()
    top = max(ys) * 1.2
    pts = " ".join(f"{6 + (w - 12) * i / (len(ys) - 1):.1f},{h - 6 - (h - 14) * v / top:.1f}" for i, v in enumerate(ys))
    x0, y0 = pts.split()[0].split(",")
    x1, y1 = pts.split()[-1].split(",")
    fim = f"{ys[-1]:,}".replace(",", ".")  # separador de milhar pt-BR
    return (f"<svg width='{w}' height='{h + 14}' viewBox='0 0 {w} {h + 14}'>"
            f"<line x1='6' x2='{w - 6}' y1='{h - 6}' y2='{h - 6}' stroke='#d9d8d3'/>"
            f"<polyline points='{pts}' fill='none' stroke='#2a78d6' stroke-width='2' stroke-linejoin='round'/>"
            f"<circle cx='{x0}' cy='{y0}' r='3' fill='#2a78d6'/><circle cx='{x1}' cy='{y1}' r='3' fill='#2a78d6'/>"
            f"<text x='{float(x0) + 5}' y='{float(y0) - 4}' font-size='9' fill='#0b0b0b'>{ys[0]}</text>"
            f"<text x='{float(x1) - 4}' y='{float(y1) - 7}' font-size='9' fill='#0b0b0b' text-anchor='end' font-weight='600'>{fim}</text>"
            f"<text x='6' y='{h + 10}' font-size='8.5' fill='#898781'>{cob['mes'].iloc[0]}</text>"
            f"<text x='{w - 6}' y='{h + 10}' font-size='8.5' fill='#898781' text-anchor='end'>{cob['mes'].iloc[-1]}</text></svg>")


def linha_cobertura(rotulo, celulas):
    css = {"P": "c pago", "C": "c canc", ".": "c vazio", "#": "c cob", "_": "c semcob"}
    return (f"<div class='crow'><span class='clab'>{rotulo}</span>"
            + "".join(f"<span class='{css[x]}'></span>" for x in celulas) + "</div>")


cobertura = (
    "<div class='fig-t'>Mesmo cancelamento, desfechos diferentes (8 meses)</div>"
    "<div class='cex'><div class='cex-t'>Troca de plano</div>"
    + linha_cobertura("Contrato A", "PPPPCCCC")
    + linha_cobertura("Contrato B", "....PPPP")
    + linha_cobertura("Aluno", "########")
    + "<div class='ccap'>→ coberto o tempo todo: <b>troca, não saída</b></div>"
    + "</div><div class='cex'><div class='cex-t'>Saída</div>"
    + linha_cobertura("Contrato A", "PPPPCCCC")
    + linha_cobertura("Aluno", "####____")
    + "<div class='ccap'>→ 4 meses sem cobertura: <b>saída</b></div>"
    + "</div><div class='cleg'><span class='c pago'></span>parcela paga/em aberto "
      "<span class='c canc'></span>parcela cancelada<br><span class='c cob'></span>mês coberto "
      "<span class='c semcob'></span>mês sem cobertura</div>"
)

CSS = """
@page { size: A4; margin: 13mm 15mm 13mm 15mm; }
* { box-sizing: border-box; -webkit-print-color-adjust: exact; print-color-adjust: exact; }
body { font-family: 'Segoe UI', Arial, sans-serif; font-size: 9.3pt; line-height: 1.42; color: #1d1d1b; margin: 0; }
h1 { font-size: 22pt; line-height: 1.12; margin: 2mm 0 2mm; color: #0b0b0b; letter-spacing: -0.3px; }
h2 { font-size: 12.5pt; margin: 5mm 0 2mm; color: #0b0b0b; padding-bottom: 1.2mm; border-bottom: 1.5px solid #0b0b0b; }
h3 { font-size: 10.2pt; margin: 3.2mm 0 1mm; color: #0b0b0b; }
p { margin: 0 0 1.6mm; }
ul { margin: 0.5mm 0 1.6mm; padding-left: 4.5mm; } li { margin-bottom: 0.7mm; }
b { color: #0b0b0b; }
.top { display: flex; justify-content: space-between; font-size: 8pt; color: #52514e; text-transform: uppercase;
       letter-spacing: 0.8px; border-bottom: 1px solid #d9d8d3; padding-bottom: 1.5mm; }
.lead { font-size: 10.4pt; line-height: 1.45; color: #2b2b29; margin: 1mm 0 4mm; }
.tiles { display: grid; grid-template-columns: repeat(4, 1fr); gap: 3mm; margin-bottom: 1mm; }
.tile { background: #f3f6fb; border-radius: 2mm; padding: 3mm 3mm 2.6mm; }
.tile .n { font-size: 17pt; font-weight: 700; color: #1c5cab; line-height: 1.1; }
.tile .t { font-size: 8.2pt; color: #2b2b29; margin-top: 1mm; line-height: 1.3; }
.two { display: grid; grid-template-columns: 1fr 1fr; gap: 5mm; }
.side { display: grid; grid-template-columns: 1fr 58mm; gap: 5mm; align-items: start; }
.side.wide { grid-template-columns: 1fr 74mm; }
.note { font-size: 8.3pt; color: #52514e; }
.box { border: 1px solid #d9d8d3; border-radius: 2mm; padding: 2.6mm 3.2mm; break-inside: avoid; }
.box.soft { background: #f7f7f5; border-color: #ecebe7; }
.fig { break-inside: avoid; }
.fig-t { font-size: 8.6pt; font-weight: 600; color: #0b0b0b; margin-bottom: 1.5mm; }
.hrow { display: grid; grid-template-columns: 34mm 1fr 9mm 11mm; align-items: center; gap: 1.5mm; height: 4.6mm; font-size: 8.2pt; }
.hlab { color: #2b2b29; } .hval { text-align: right; font-weight: 600; color: #0b0b0b; } .hn { color: #898781; font-size: 7.6pt; }
.htrack { height: 2.8mm; background: #f0efec; border-radius: 1mm; }
.bar { display: block; height: 100%; border-radius: 0 1mm 1mm 0; }
.bar.ok { background: #2a78d6; } .bar.no { background: #a9a7a0; }
.leg { font-size: 7.8pt; color: #52514e; margin-top: 1.4mm; }
.leg i { display: inline-block; width: 2.6mm; height: 2.6mm; border-radius: 0.6mm; vertical-align: -0.3mm; margin: 0 1mm 0 2.5mm; }
.vchart { display: flex; align-items: flex-end; gap: 1.2mm; height: 30mm; padding-top: 4mm; border-bottom: 1px solid #d9d8d3; }
.vcol { flex: 1; display: flex; flex-direction: column; justify-content: flex-end; align-items: center; height: 100%; position: relative; }
.vbar { width: 100%; background: #9ec5f4; border-radius: 1mm 1mm 0 0; display: block; }
.vbar.hi { background: #1c5cab; }
.vval { font-size: 7.6pt; color: #0b0b0b; margin-bottom: 0.6mm; }
.vlab { position: absolute; bottom: -4.2mm; font-size: 7.4pt; color: #52514e; }
.vaxis { font-size: 7.6pt; color: #898781; margin-top: 5.2mm; }
.cex { margin-bottom: 2mm; } .cex-t { font-size: 8.2pt; font-weight: 600; color: #52514e; margin-bottom: 0.8mm; }
.crow { display: flex; align-items: center; gap: 0.8mm; height: 4.4mm; font-size: 8.2pt; }
.clab { width: 17mm; flex: none; color: #2b2b29; }
.ccap { font-size: 8.2pt; color: #2b2b29; margin: 0.6mm 0 0 17.8mm; }
.c { display: inline-block; width: 5.4mm; height: 3.4mm; border-radius: 0.6mm; flex: none; }
.c.pago { background: #6da7ec; }
.c.canc { background: repeating-linear-gradient(45deg, #c9c7c0 0 1.2px, #f0efec 1.2px 3px); border: 1px solid #b5b3ad; }
.c.vazio { background: transparent; }
.c.cob { background: #1c5cab; }
.c.semcob { background: #fff; border: 1px dashed #a9a7a0; }
.cleg { font-size: 7.8pt; color: #52514e; margin-top: 1mm; }
.cleg .c { width: 3.2mm; height: 2.6mm; vertical-align: -0.3mm; margin: 0 0.8mm 0 2.4mm; }
.arch { display: grid; grid-template-columns: 27mm 4mm 31mm 4mm 34mm 4mm 1fr; align-items: center; margin: 2mm 0 1mm; }
.node { border: 1px solid #b5b3ad; border-radius: 1.6mm; padding: 1.8mm 2mm; font-size: 8.1pt; text-align: center; background: #fff; line-height: 1.3; }
.node.core { background: #f3f6fb; border-color: #86b6ef; }
.node b { display: block; font-size: 8.4pt; }
.arr { text-align: center; color: #898781; font-size: 10pt; }
.stack { display: grid; gap: 2mm; }
.mod { border-radius: 2mm; padding: 3mm 3.4mm; break-inside: avoid; }
.mod.m2 { background: #f3f6fb; border: 1px solid #cde2fb; }
.mod.m3 { background: #f7f7f5; border: 1px solid #e6e5e0; }
.mod .tag { font-size: 7.6pt; font-weight: 700; letter-spacing: 0.8px; text-transform: uppercase; color: #1c5cab; }
.mod.m3 .tag { color: #52514e; }
.mod h3 { margin-top: 0.6mm; }
.mod dl { margin: 1mm 0 0; display: grid; grid-template-columns: 18mm 1fr; gap: 1mm 2mm; font-size: 8.5pt; }
.mod dt { font-weight: 600; color: #52514e; } .mod dd { margin: 0; }
.road { display: grid; grid-template-columns: 0.8fr 1.2fr 1fr; gap: 3mm; }
.phase { border-top: 3px solid #2a78d6; padding-top: 1.6mm; font-size: 8.6pt; }
.phase.p0 { border-color: #898781; } .phase.p3 { border-color: #1c5cab; }
.phase .when { font-size: 7.8pt; font-weight: 700; text-transform: uppercase; letter-spacing: 0.7px; color: #52514e; }
.phase ol, .phase ul { padding-left: 4.2mm; margin: 1mm 0 0; }
table { width: 100%; border-collapse: collapse; font-size: 8.4pt; }
th { text-align: left; font-weight: 600; color: #52514e; border-bottom: 1px solid #b5b3ad; padding: 1mm 1.5mm; }
td { border-bottom: 1px solid #ecebe7; padding: 1.1mm 1.5mm; vertical-align: top; }
h2, h3 { break-after: avoid; }
.road, .two, .arch, .tiles, .keep { break-inside: avoid; }
.foot { margin-top: 4mm; font-size: 7.8pt; color: #898781; border-top: 1px solid #ecebe7; padding-top: 1.5mm; }
"""

BODY = f"""
<div class='top'><span>Projeto Integrador · Ciência de Dados e ML · CEUB</span><span>Pitch técnico · PIM II · out/2026</span></div>
<h1>Do churn ao ciclo de vida do aluno</h1>
<p class='lead'>Analisamos os exports reais do sistema da Academia Equilíbrio e Movimento: parcelas, catraca e tentativas
de cobrança no cartão. O modelo de churn do PIM I não se sustenta como está. Em compensação, os dados mostram um problema
concreto e mensurável, a <b>falha de cobrança no cartão recorrente</b>, e dão base para um <b>estudo de retenção bem definido</b>.
Propomos um tema único, com uma base de dados comum e dois módulos: <b>cobrança no PIM II</b> e <b>retenção no PIM III</b>.</p>

<div class='tiles'>
  <div class='tile'><div class='n'>93,5%</div><div class='t'>dos alunos que o rótulo do PIM I chamaria de churn continuam com plano ativo</div></div>
  <div class='tile'><div class='n'>R$ 42,6 mil</div><div class='t'>em mensalidades no cartão que não foram aprovadas em nenhum momento de set/26 (30% dos cartões)</div></div>
  <div class='tile'><div class='n'>23% × 0%</div><div class='t'>de recuperação: "saldo insuficiente" × códigos irreversíveis, que hoje são re-tentados até 65 vezes</div></div>
  <div class='tile'><div class='n'>16,7%</div><div class='t'>dos alunos pagantes não passaram na catraca nenhuma vez no mês</div></div>
</div>

<h2>1. O que os dados mostraram</h2>

<div class='side'>
  <div>
    <h3>1.1 O relatório de parcelas só traz quem é cliente hoje</h3>
    <p>Em 24 meses, a quantidade de alunos com plano só cresce (205 → 1.153), sem nenhuma queda. Dos 56 alunos que aparecem
    na catraca mas não nas parcelas, 54 estão inativos. Ou seja, <b>quem sai é removido do relatório</b>. Com esse arquivo
    não dá para medir churn, e qualquer modelo treinado nele aprende só com quem ficou.</p>
    <p>Como os contratos são numerados em sequência (Spearman 0,99996 com a data), as lacunas na numeração permitem
    <b>estimar a retenção</b>: só 21–40% dos contratos emitidos há 12 meses ou mais pertencem a quem ainda é cliente. Além disso,
    menos da metade dos cadastros recentes está ativa, o que indica um funil de visitantes que não convertem.</p>
  </div>
  <div class='box soft fig'><div class='fig-t'>Alunos com plano por mês, segundo o relatório</div>{sparkline()}
    <div class='note'>Uma curva que só sobe é sinal de que o relatório contém apenas sobreviventes.</div></div>
</div>

<h3>1.2 Parcela cancelada não significa que o aluno saiu</h3>
<div class='side wide'>
  <div>
    <p>Quando o aluno troca de plano ou renova antes do fim (por exemplo, sai da promoção de Black Friday para a de Natal),
    o sistema cancela o restante do contrato antigo e abre um novo. Por isso, <b>o estado do aluno deve ser medido pela cobertura mês a mês,
    em qualquer contrato</b>:</p>
    <ul>
      <li><b>Mês coberto:</b> existe uma mensalidade não cancelada (paga ou em aberto) em algum contrato do aluno.</li>
      <li><b>Saída:</b> N meses seguidos sem cobertura. Usamos N = 2 como valor provisório, a calibrar com a academia levando em conta os trancamentos.</li>
      <li>Meses recentes ainda não têm desfecho observável (são <b>censurados</b>). Por isso a abordagem é análise de sobrevivência, e não classificação binária.</li>
      <li>Se antes da saída houve parcelas em aberto e cartão recusado, a saída é provavelmente <b>involuntária</b>.</li>
    </ul>
    <p class='note'>Ao todo foram 788 trocas e renovações, a maioria dentro do mesmo tipo de plano. Dos 128 contratos promocionais, 94 viraram Gold regular.
    As métricas do PIM I (AUC 0,849) precisam ser recalculadas com essa definição.</p>
  </div>
  <div class='box fig'>{cobertura}</div>
</div>

<div class='keep'>
<h3>1.3 A "inadimplência" é, na prática, falha de cobrança</h3>
<p>Só 202 parcelas estão em aberto (~1%). O problema está no cartão recorrente:
<b>30% de aprovação por tentativa</b>, cobrança em lote diário às 12h e <b>86% das recusas concentradas em 238 cartões que nunca aprovam</b>,
re-tentados a cada 0–4 dias. As bandeiras limitam o número de re-tentativas e a adquirente prevê tarifa para o excesso: 37 cartões passaram de 15 recusas em 30 dias.
Além disso, 29% das mensalidades de planos recorrentes acabam pagas por PIX ou crédito, provavelmente no balcão, depois que o cartão falhou.</p>
<div class='two'>
  <div class='box fig'>
    <div class='fig-t'>Cartão-mês que começou recusado: % que aprovou depois, no mesmo mês</div>
    {grafico_recuperacao()}
    <div class='leg'><i style='background:#2a78d6'></i>vale re-tentar <i style='background:#a9a7a0'></i>não recupera
    · Pac* = códigos do sistema de gestão (significado a confirmar)</div>
  </div>
  <div class='box fig'>
    <div class='fig-t'>Re-tentativa após "saldo insuficiente": % aprovada por dia do mês</div>
    <div class='vchart'>{grafico_dia_do_mes()}</div>
    <div class='vaxis'>Dias 10–14: 17–20% · dias 1–7: 3–4%. Amostra de 43–165 tentativas por faixa, a confirmar com mais meses.</div>
  </div>
</div>
</div>

<div class='two' style='margin-top:1mm'>
  <div>
    <h3>1.4 Engajamento, jornada e operação</h3>
    <ul>
      <li>16,7% dos pagantes não tiveram nenhum acesso no mês, e outros 125 vieram só 1–2 vezes. Nos planos <b>promocionais</b>, a mediana é de 3,5 dias/mês e 31% não tiveram acesso. No Gold regular: 7 dias e 19%.</li>
      <li><b>23% dos ativos já ficaram 2+ meses sem plano e voltaram</b>: a reativação de ex-alunos é relevante.</li>
      <li>O mesmo plano chega a ter <b>14 preços</b> diferentes. Ticket médio de R$ 169; R$ 188 mil em mensalidades em set/26.</li>
      <li>Picos de entrada às 6–8h e 17–19h; vale às 12–14h.</li>
      <li>Ressalva: com só 1 mês de catraca, a frequência <b>ainda não antecipa</b> a saída. Quem saiu tinha frequência igual à de quem ficou nas duas semanas anteriores. É preciso um histórico longo.</li>
    </ul>
  </div>
  <div>
    <h3>1.5 Armadilhas que o pipeline precisa tratar</h3>
    <ul>
      <li><b>Data de pagamento</b> em cheque ou crédito parcelado = data da venda (no cheque, mediana de 182 dias antes do vencimento). Calcular atraso só para recorrente, PIX, débito e dinheiro.</li>
      <li>A flag <b>Recorrência</b> contradiz o nome do plano em 90% dos contratos. Usar o nome do plano ou a forma de pagamento.</li>
      <li><b>Contrato 0</b> = vendas avulsas (R$ 5,2 mil/mês). Separar das mensalidades.</li>
      <li>As <b>transações não têm matrícula</b>. O vínculo por dia + valor + nome cobre 63% das aprovadas.</li>
    </ul>
  </div>
</div>

<h2>2. Proposta: inteligência do ciclo de vida do aluno</h2>
<div class='arch'>
  <div class='node'><b>Exports</b>parcelas · catraca · transações</div><div class='arr'>→</div>
  <div class='node'><b>Ingestão</b>validação · dicionário · pseudonimização</div><div class='arr'>→</div>
  <div class='node core'><b>Base comum</b>estados aluno × mês + fatos de cobrança</div><div class='arr'>→</div>
  <div class='stack'>
    <div class='node core'><b>PIM II · Cobrança recorrente</b></div>
    <div class='node'><b>PIM III · Retenção</b></div>
    <div class='node' style='border-style:dashed'>Painel · fila de ação · registro de desfecho</div>
  </div>
</div>

<div class='two'>
  <div class='mod m2'><div class='tag'>PIM II · com os dados de hoje</div>
    <h3>Recuperação de cobrança recorrente</h3>
    <dl>
      <dt>Pergunta</dt><dd>Depois de uma recusa: re-tentar (em que dia?) ou pedir ao aluno um novo cartão ou PIX?</dd>
      <dt>Dados</dt><dd>Tentativas (código, nº da tentativa, dia do mês, emissor/BIN, valor, histórico do cartão) + parcelas.</dd>
      <dt>Baseline</dt><dd>Regras: não re-tentar códigos irreversíveis; concentrar as re-tentativas de "saldo insuficiente" nos dias de maior aprovação.</dd>
      <dt>Modelo</dt><dd>P(aprovação | tentativa) com regressão logística e gradient boosting, calibrados. Política: re-tentar quando P × valor supera o custo (tarifa e limite da bandeira).</dd>
      <dt>Validação</dt><dd>Temporal: treina nos meses anteriores e testa no seguinte. AUC/Brier e simulação de R$ recuperado, tentativas evitadas e dias até regularizar.</dd>
      <dt>Entrega</dt><dd>Fila diária explicável + painel de cobrança.</dd>
    </dl>
  </div>
  <div class='mod m3'><div class='tag'>PIM III · com o novo export</div>
    <h3>Retenção com análise de sobrevivência</h3>
    <dl>
      <dt>Pergunta</dt><dd>Quem tende a sair nos próximos 30/60/90 dias, e por quê?</dd>
      <dt>Dados</dt><dd>Parcelas incluindo inativos, cadastro completo, 12–24 meses de catraca, operações de contrato.</dd>
      <dt>Método</dt><dd>Kaplan–Meier por plano, coorte e forma de pagamento. Cox ou modelo de risco em tempo discreto com atributos de engajamento (tendência e recência), cobrança (falhas) e plano/preço/promoção.</dd>
      <dt>Validação</dt><dd>Backtest temporal: C-index, calibração por horizonte e ganho sobre uma regra simples (recência).</dd>
      <dt>Extensões</dt><dd>LTV por promoção, propensão de retorno (win-back), funil de visitantes, previsão de ocupação.</dd>
    </dl>
  </div>
</div>

<div class='box soft' style='margin-top:3mm'>
<b>Por que essa ordem.</b> Cobrança é o único problema que os dados de hoje sustentam. Tem valor em R$ claro e continua o tema
"inadimplência" do PIM I, agora com o diagnóstico correto. Retenção é o problema com maior potencial de ML, mas depende de dados que
<b>precisam ser pedidos agora</b> para estarem prontos no PIM III. A tabela de estados aluno × mês serve aos dois módulos e resolve as trocas de plano por construção.
</div>

<h2>3. Roteiro</h2>
<div class='road'>
  <div class='phase p0'><div class='when'>Agora</div>
    <ul><li>Validar com o dono as dores prioritárias</li><li>Pedir os exports (abaixo)</li><li>Confirmar os requisitos de cada PIM</li><li>Levar as perguntas à academia</li></ul></div>
  <div class='phase'><div class='when'>PIM II</div>
    <ol><li>Fundação de dados: pipeline, dicionário e tabela de estados, com testes dos casos-limite (troca, à vista, trancamento)</li>
    <li>Diagnóstico de cobrança</li><li>Baseline × modelo + simulação de R$</li><li>Fila de ação e painel</li></ol></div>
  <div class='phase p3'><div class='when'>PIM III</div>
    <ol start='5'><li>Retenção com sobrevivência</li><li>Piloto com a academia, registrando ações e desfechos</li><li>Avaliação e relatório final</li></ol></div>
</div>

<div class='two' style='margin-top:4mm'>
  <div>
    <h3>Dependências de dados (pedir agora)</h3>
    <table>
      <tr><th>Pedido</th><th>Para quê</th></tr>
      <tr><td>Parcelas <b>incluindo inativos</b>, todo o histórico</td><td>Medir churn de verdade</td></tr>
      <tr><td>Cadastro de clientes com data e motivo de cancelamento</td><td>Rótulo e causas de saída</td></tr>
      <tr><td>Catraca de 12–24 meses</td><td>Engajamento como sinal; ocupação</td></tr>
      <tr><td>Transações de 6–12 meses + tabela dos códigos Pac*</td><td>Robustez do módulo de cobrança</td></tr>
      <tr><td>Operações de contrato (trancamento, troca)</td><td>Calibrar a regra de saída</td></tr>
    </table>
  </div>
  <div>
    <h3>Perguntas para a academia</h3>
    <ul>
      <li>O que significam os códigos Pac014 e Pac003? Qual é a regra atual de re-tentativa?</li>
      <li>Quando o cartão falha, quem é avisado e o que acontece?</li>
      <li>Como trancamento e férias aparecem nas parcelas: as parcelas são canceladas ou adiadas?</li>
      <li>A partir de quando um aluno é considerado desistente?</li>
    </ul>
    <h3>Decisões do grupo</h3>
    <ul>
      <li>Aprovar o tema e a divisão PIM II / PIM III.</li>
      <li>Definir quem conduz a conversa com a academia.</li>
      <li>Recalcular as métricas do PIM I com o novo rótulo.</li>
    </ul>
  </div>
</div>

<div class='foot'>Números, método e scripts completos: <b>ESTUDO_DADOS_E_OPORTUNIDADES.md</b>, no repositório do projeto.
Janelas analisadas: parcelas com vencimento entre 15/10/2024 e 15/10/2026; catraca de 15/09 a 15/10/2026; cartão de 15/08 a 15/10/2026.</div>
"""

HTML.parent.mkdir(exist_ok=True)
HTML.write_text(f"<!doctype html><html lang='pt-BR'><head><meta charset='utf-8'><title>Pitch técnico PIM II</title>"
                f"<style>{CSS}</style></head><body>{BODY}</body></html>", encoding="utf-8")
subprocess.run([str(EDGE), "--headless=new", "--disable-gpu", "--no-pdf-header-footer",
                f"--print-to-pdf={PDF}", HTML.as_uri()], check=True, timeout=120)
print("PDF:", PDF, PDF.stat().st_size, "bytes")
