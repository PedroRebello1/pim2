"""✏️ Gráficos e diagramas do relatório. Cada ![Legenda](#fig-nome) do relatorio_pi.md chama aqui
a função marcada com @figura("fig-nome").

Regras (as mesmas do modelo do professor):
- comece com fig, ax = plt.subplots() e devolva a figura (return fig);
- não use plt.title(): o título é a legenda do relatorio_pi.md e sai acima da figura;
- cores, fonte e tamanho já seguem o padrão do curso (abnt/padrao.py): use PALETA,
  COR_PRINCIPAL, COR_DESTAQUE e COR_NEUTRA, e eixo_br() para números no padrão brasileiro.
"""
from __future__ import annotations

from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
from matplotlib.patches import FancyBboxPatch, Rectangle  # noqa: E402

from abnt import COR_DESTAQUE, COR_NEUTRA, COR_PRINCIPAL, PALETA, aplicar_padrao, eixo_br, numero_br  # noqa: E402
from abnt.markdown import ErroRelatorio  # noqa: E402
from fontes import resultados, saidas  # noqa: E402

FIGURAS = {}
MESES_CURTOS = ["jan", "fev", "mar", "abr", "mai", "jun", "jul", "ago", "set", "out", "nov", "dez"]


def figura(rotulo):
    def registrar(funcao):
        FIGURAS[rotulo] = funcao
        return funcao
    return registrar


class Figuras:
    """Gera cada figura uma vez por execução e devolve o caminho do PNG (300 dpi)."""

    def __init__(self, pasta: Path):
        self.pasta = Path(pasta)
        self.pasta.mkdir(parents=True, exist_ok=True)
        self.prontas: dict[str, Path] = {}
        aplicar_padrao()
        # Mesmo padrão do curso; "Liberation Serif" (métrica idêntica à Times New Roman) só entra
        # em máquinas sem a Times, como alguns Linux.
        matplotlib.rcParams["font.serif"] = ["Times New Roman", "Liberation Serif", "Times", "DejaVu Serif"]

    def obter(self, rotulo: str) -> Path:
        if rotulo not in self.prontas:
            if rotulo not in FIGURAS:
                raise ErroRelatorio(f"A figura @{rotulo} não existe em relatorio/figuras.py.")
            fig = FIGURAS[rotulo]()
            caminho = self.pasta / f"{rotulo}.png"
            fig.savefig(caminho, dpi=300, facecolor="white")
            plt.close(fig)
            from PIL import Image        # PNG sem transparência: sai igual no Word e no LibreOffice
            with Image.open(caminho) as im:
                im.convert("RGB").save(caminho, dpi=(300, 300))
            self.prontas[rotulo] = caminho
        return self.prontas[rotulo]


def mes_curto(periodo: str) -> str:
    ano, mes = periodo.split("-")
    return f"{MESES_CURTOS[int(mes) - 1]}/{ano[2:]}"


# ============================================================================= diagramas
@figura("fig-cobertura")
def cobertura():
    """Troca de plano x saída: o mesmo contrato com parcelas canceladas, lido pela cobertura."""
    fig, ax = plt.subplots(figsize=(6.3, 2.2))
    ax.set_xlim(0, 100)
    ax.set_ylim(0, 35)
    ax.axis("off")
    estilos = {
        "P": dict(facecolor=COR_PRINCIPAL, edgecolor=COR_PRINCIPAL),
        "C": dict(facecolor="white", edgecolor=COR_DESTAQUE, hatch="////"),
        "#": dict(facecolor=PALETA[2], edgecolor=PALETA[2]),
        "_": dict(facecolor="white", edgecolor=COR_NEUTRA),
    }
    casos = [
        ("Troca de plano", 1, [("Contrato A", "PPPPCCCC"), ("Contrato B", "....PPPP"), ("Aluno", "########")],
         "coberto o tempo todo: troca, não saída"),
        ("Saída", 53, [("Contrato A", "PPPPCCCC"), ("Aluno", "####____")],
         "4 meses sem cobertura: saída"),
    ]
    larg, alt, passo = 3.3, 3.2, 3.9
    for titulo, x0, linhas, conclusao in casos:
        ax.text(x0, 32.5, titulo, fontsize=10, fontweight="bold", va="center")
        for i, (nome, celulas) in enumerate(linhas):
            y = 26 - i * 4.9
            ax.text(x0, y + alt / 2, nome, fontsize=9, va="center")
            for j, c in enumerate(celulas):
                if c != ".":
                    ax.add_patch(Rectangle((x0 + 13 + j * passo, y), larg, alt, linewidth=0.8, **estilos[c]))
        ax.text(x0, 26 - len(linhas) * 4.9 + 1.4, "→ " + conclusao, fontsize=9, va="center", style="italic")
    legenda = [("P", "parcela paga ou em aberto"), ("C", "parcela cancelada"), ("#", "mês coberto"),
               ("_", "mês sem cobertura")]
    x = 1
    for c, texto in legenda:
        ax.add_patch(Rectangle((x, 1.2), 2.6, 2.4, linewidth=0.8, **estilos[c]))
        ax.text(x + 3.6, 2.4, texto, fontsize=8.5, va="center")
        x += 3.6 + 1.05 * len(texto) + 4
    return fig


@figura("fig-fluxo")
def fluxo():
    """Fluxo diário: export -> histórico -> modelo -> política -> fila, com as três ações."""
    fig, ax = plt.subplots(figsize=(6.3, 3.0))
    ax.set_xlim(0, 100)
    ax.set_ylim(0, 48)
    ax.axis("off")

    def caixa(x, y, w, h, texto, cor, preenchida=False, tamanho=8.5):
        ax.add_patch(FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.3,rounding_size=1.2", linewidth=1,
                                    edgecolor=cor, facecolor=cor if preenchida else "white"))
        ax.text(x + w / 2, y + h / 2, texto, ha="center", va="center", fontsize=tamanho,
                color="white" if preenchida else "black", linespacing=1.25)

    def seta(x1, y1, x2, y2, estilo="-|>", tracejada=False):
        ax.annotate("", xy=(x2, y2), xytext=(x1, y1),
                    arrowprops=dict(arrowstyle=estilo, color="#404040", lw=0.9, shrinkA=0, shrinkB=0,
                                    linestyle="--" if tracejada else "-"))

    etapas = ["Export diário\n(tentativas de\ncobrança)", "Histórico do\ncartão\n(atributos)", "Modelo\nP(aprovação)",
              "Política\n(regras +\nlimiar)", "Fila do dia\n(ação +\nmotivo)"]
    w, h, y = 16.4, 12, 31
    xs = [1 + k * 20.2 for k in range(5)]
    for k, (x, texto) in enumerate(zip(xs, etapas)):
        caixa(x, y, w, h, texto, COR_PRINCIPAL, preenchida=(k in (2, 3)))
        if k:
            seta(xs[k - 1] + w + 0.4, y + h / 2, x - 0.4, y + h / 2)
    acoes = [("Novo cartão ou PIX\n(código irreversível)", COR_DESTAQUE),
             ("Parar e contatar\n(teto de recusas)", COR_DESTAQUE),
             ("Re-tentar em dd/mm\n(P ≥ limiar)", PALETA[2]),
             ("Contato\n(chance baixa)", COR_NEUTRA)]
    wa, ha, ya = 22.6, 9.5, 7
    xa = [1 + k * 24.9 for k in range(4)]
    centro_fila = xs[4] + w / 2
    ax.plot([centro_fila, centro_fila], [y - 0.6, 22], color="#404040", lw=0.9)
    ax.plot([xa[0] + wa / 2, xa[-1] + wa / 2], [22, 22], color="#404040", lw=0.9)
    for x, (texto, cor) in zip(xa, acoes):
        seta(x + wa / 2, 22, x + wa / 2, ya + ha + 0.5)
        caixa(x, ya, wa, ha, texto, cor, tamanho=8)
    ax.text(50, 1.5, "O desfecho de cada ação é registrado e volta para o re-treino do modelo.",
            ha="center", fontsize=8.5, style="italic")
    return fig


# ============================================================================= diagnóstico dos dados
@figura("fig-alunos-por-mes")
def alunos_por_mes():
    d = saidas("D_alunos_com_plano_por_mes.csv")
    x = np.arange(len(d))
    y = d["alunos_com_plano"].to_numpy()
    fig, ax = plt.subplots()
    ax.plot(x, y, marker="o", markersize=3, color=COR_PRINCIPAL)
    marcas = [i for i in range(len(d)) if i % 3 == 0] + ([len(d) - 1] if (len(d) - 1) % 3 else [])
    ax.set_xticks(marcas)
    ax.set_xticklabels([mes_curto(d["mes"].iloc[i]) for i in marcas])
    for i, alinh in ((0, "left"), (len(d) - 1, "right")):
        ax.annotate(numero_br(y[i]), (x[i], y[i]), textcoords="offset points", xytext=(0, 7), ha=alinh, fontsize=9)
    ax.set_ylim(0, y.max() * 1.18)
    ax.set_xlabel("Mês de vencimento das parcelas")
    ax.set_ylabel("Alunos com plano")
    eixo_br(ax, "y")
    return fig


@figura("fig-contratos-atuais")
def contratos_atuais():
    d = saidas("D_coorte_contratos_por_numeracao.csv")
    fig, ax = plt.subplots()
    cores = [COR_DESTAQUE if m == "2024-12" else COR_PRINCIPAL for m in d["m"]]
    ax.bar(np.arange(len(d)), d["pct_de_clientes_atuais"], color=cores, width=0.75)
    ax.set_xticks(np.arange(len(d))[::2])
    ax.set_xticklabels([mes_curto(m) for m in d["m"]][::2], rotation=45, ha="right")
    i_dez = int(np.flatnonzero(d["m"].to_numpy() == "2024-12")[0]) if (d["m"] == "2024-12").any() else None
    if i_dez is not None:
        ax.annotate("Natal 2024", (i_dez, d["pct_de_clientes_atuais"].iloc[i_dez]), textcoords="offset points",
                    xytext=(0, 5), ha="center", fontsize=8.5, color=COR_DESTAQUE)
    ax.set_ylim(0, 1)
    ax.set_xlabel("Mês de emissão do contrato")
    ax.set_ylabel("Contratos de clientes atuais")
    eixo_br(ax, "y", formato="percentual", casas=0)
    return fig


@figura("fig-recuperacao")
def recuperacao():
    d = saidas("G_recuperacao_por_codigo_primeira_recusa.csv")
    nomes = [f"{c} (saldo insuficiente)" if c == "51" else c for c in d["codigoRetorno"]]
    y = np.arange(len(d))[::-1]
    cores = [COR_PRINCIPAL if t >= 0.10 else COR_NEUTRA for t in d["taxa_recuperacao"]]
    fig, ax = plt.subplots(figsize=(6.3, 2.9))
    ax.barh(y, d["taxa_recuperacao"], color=cores, height=0.65)
    for yi, t, n in zip(y, d["taxa_recuperacao"], d["casos"]):
        ax.text(t + 0.006, yi, f"{numero_br(t * 100, 0 if t >= 0.01 or t == 0 else 1)}%  (n = {n})",
                va="center", fontsize=8.5)
    ax.set_yticks(y)
    ax.set_yticklabels(nomes)
    ax.set_xlim(0, max(0.45, d["taxa_recuperacao"].max() * 1.35))
    ax.set_xlabel("Cartão-mês que aprovou depois da 1ª recusa, no mesmo mês")
    ax.grid(axis="y", visible=False)
    ax.grid(axis="x", visible=True)
    eixo_br(ax, "x", formato="percentual", casas=0)
    return fig


@figura("fig-dia-do-mes")
def dia_do_mes():
    d = saidas("G_retentativa_apos_51_por_dia_do_mes.csv")
    x = np.arange(len(d))
    cores = [COR_DESTAQUE if f in ("10-11", "12-14") else COR_PRINCIPAL for f in d["faixa"]]
    fig, ax = plt.subplots()
    ax.bar(x, d["taxa_aprovacao"], color=cores, width=0.7)
    for xi, t in zip(x, d["taxa_aprovacao"]):
        ax.text(xi, t + 0.004, numero_br(t * 100, 1) + "%", ha="center", fontsize=8.5)
    ax.set_xticks(x)
    ax.set_xticklabels([f"{f.replace('-', '–')}\nn = {n}" for f, n in zip(d["faixa"], d["tentativas"])], fontsize=8.5)
    ax.set_ylim(0, d["taxa_aprovacao"].max() * 1.2)
    ax.set_xlabel("Faixa do dia do mês da re-tentativa")
    ax.set_ylabel("Re-tentativas aprovadas")
    eixo_br(ax, "y", formato="percentual", casas=0)
    return fig


# ============================================================================= modelo
@figura("fig-roc")
def roc():
    d = resultados("roc_teste.csv")
    from fontes import metricas
    m = metricas()
    fig, ax = plt.subplots(figsize=(4.4, 3.6))
    ax.plot([0, 1], [0, 1], linestyle="--", color=COR_NEUTRA, linewidth=1, label="Sem informação (AUC = 0,5)")
    ax.step(d["fpr"], d["tpr"], where="post", color=COR_PRINCIPAL, linewidth=1.6,
            label=f"Modelo (AUC = {numero_br(m['auc_teste'], 3)})")
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1.02)
    ax.set_xlabel("Taxa de falsos positivos")
    ax.set_ylabel("Taxa de verdadeiros positivos")
    ax.grid(axis="x", visible=True)
    eixo_br(ax, "x", casas=1)
    eixo_br(ax, "y", casas=1)
    ax.legend(loc="lower right")
    return fig


ROTULOS_ATRIBUTOS = {
    "seq_falhas": "Recusas seguidas (+1 DP)",
    "n_tent_mes": "Nº da tentativa no mês (+1 DP)",
    "dias_desde_ult": "Dias desde a tentativa anterior (+1 DP)",
    "ja_aprovou": "Cartão já aprovou antes (+1 DP)",
    "duas_parcelas": "Cobrança de duas parcelas (+1 DP)",
    "log_valor": "Valor cobrado, em log (+1 DP)",
    "bin_taxa": "Taxa de aprovação do emissor (+1 DP)",
}


def rotulo_atributo(nome: str) -> str:
    if nome in ROTULOS_ATRIBUTOS:
        return ROTULOS_ATRIBUTOS[nome]
    col, val = nome.split("=", 1)
    if col == "ult_cod":
        return "Última recusa: " + ("51 (saldo insuficiente)" if val == "51" else "outros códigos" if val == "outros" else val)
    if col == "faixa_dia":
        return "Dia do mês: " + ("outras faixas" if val == "outros" else val.replace("-", " a "))
    if col == "bandeira":
        return "Bandeira: " + ("outras" if val == "outros" else f"cartão iniciado em {val}")
    return nome


@figura("fig-razoes")
def razoes():
    d = resultados("coeficientes.csv")
    d = d[d["coef"].abs() > 1e-9]
    d = d.reindex(d["coef"].abs().sort_values(ascending=False).index).head(12).sort_values("coef")
    y = np.arange(len(d))
    cores = [COR_PRINCIPAL if c > 0 else COR_DESTAQUE for c in d["coef"]]
    fig, ax = plt.subplots(figsize=(6.3, 3.9))
    ax.barh(y, d["razao_chances"] - 1, left=1, color=cores, height=0.65)
    ax.axvline(1, color="#404040", linewidth=0.8)
    ax.set_xscale("log")
    for yi, r in zip(y, d["razao_chances"]):
        ax.text(r * (1.06 if r > 1 else 0.94), yi, "×" + numero_br(r, 2), va="center",
                ha="left" if r > 1 else "right", fontsize=8.5)
    ax.set_yticks(y)
    ax.set_yticklabels([rotulo_atributo(a) for a in d["atributo"]], fontsize=8.5)
    ax.set_xlim(0.08, 12)
    ax.set_xticks([0.1, 0.25, 0.5, 1, 2, 4, 8])
    ax.set_xticklabels([numero_br(v, 2).rstrip("0").rstrip(",") if v < 1 else numero_br(v, 0)
                        for v in [0.1, 0.25, 0.5, 1, 2, 4, 8]])
    ax.minorticks_off()
    ax.set_xlabel("Razão de chances de aprovação (escala logarítmica)")
    ax.grid(axis="y", visible=False)
    ax.grid(axis="x", visible=True)
    return fig


@figura("fig-politicas")
def politicas():
    d = resultados("politicas_teste.csv").sort_values("tentativas", ascending=False)
    base = d.iloc[0]
    nomes = [p.split(":")[0] for p in d["politica"]]
    descr = {"Atual": "Atual\n(re-tenta tudo)", "Regra 1": "Regra 1\n(sem códigos irreversíveis)",
             "Modelo": "Modelo\n(P ≥ limiar)", "Regra 2": "Regra 2\n(regra 1 + teto)"}
    y = np.arange(len(d))[::-1]
    tent = d["tentativas"] / base["tentativas"]
    aprov = d["aprovacoes"] / base["aprovacoes"]
    fig, ax = plt.subplots(figsize=(6.3, 3.4))
    ax.barh(y + 0.19, tent, height=0.36, color=COR_NEUTRA, label="Re-tentativas feitas")
    ax.barh(y - 0.19, aprov, height=0.36, color=COR_PRINCIPAL, label="Aprovações mantidas")
    for yi, t, a, nt, na in zip(y, tent, aprov, d["tentativas"], d["aprovacoes"]):
        ax.text(t + 0.01, yi + 0.19, f"{numero_br(t * 100, 0)}% ({nt})", va="center", fontsize=8.5)
        ax.text(a + 0.01, yi - 0.19, f"{numero_br(a * 100, 0)}% ({na})", va="center", fontsize=8.5)
    ax.set_yticks(y)
    ax.set_yticklabels([descr.get(n, n) for n in nomes], fontsize=8.5)
    ax.set_xlim(0, 1.18)
    ax.set_xlabel("Em relação à política atual")
    ax.grid(axis="y", visible=False)
    ax.grid(axis="x", visible=True)
    eixo_br(ax, "x", formato="percentual", casas=0)
    ax.legend(ncol=2, loc="upper center", bbox_to_anchor=(0.5, 1.12))
    return fig
