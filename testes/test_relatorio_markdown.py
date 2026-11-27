"""Leitura do relatorio_pi.md: blocos e texto corrido (relatorio/abnt/markdown.py)."""
import pytest

from abnt.markdown import (ErroRelatorio, ler_blocos, ler_inline, ler_relatorio, separar_cabecalho, sem_comentarios,
                           substituir_valores, texto_simples)


def blocos(texto, inicio=1):
    return ler_blocos(texto.split("\n"), inicio)


# ----------------------------------------------------------------------------- cabeçalho
def test_cabecalho_yaml():
    meta, corpo, linha = separar_cabecalho("---\ntitle: X\nautores:\n  - A\n---\n# Intro\n")
    assert meta == {"title": "X", "autores": ["A"]}
    assert corpo.startswith("# Intro") and linha == 6


@pytest.mark.parametrize("texto, trecho", [("# Sem cabeçalho", "precisa começar"),
                                           ("---\ntitle: X\n# esqueci de fechar", "não foi fechado")])
def test_cabecalho_mal_formado(texto, trecho):
    with pytest.raises(ErroRelatorio, match=trecho):
        separar_cabecalho(texto)


def test_comentarios_somem_mas_a_contagem_de_linhas_fica():
    texto = "a\n<!-- um\ncomentário\nlongo -->\nb"
    assert sem_comentarios(texto) == "a\n\n\n\nb"


def test_linha_do_erro_conta_o_cabecalho_e_os_comentarios(tmp_path):
    arq = tmp_path / "r.md"
    arq.write_text("---\ntitle: X\n---\n<!--\nnota\n-->\n| a | b |\n", encoding="utf-8")
    with pytest.raises(ErroRelatorio, match="Linha 7: tabela sem legenda"):
        ler_relatorio(arq)


# ----------------------------------------------------------------------------- blocos
def test_titulos_com_rotulo_e_classe():
    b = blocos("# Metodologia {#sec-met}\n\n## Dados\n\n# Resumo {.pre}")
    assert [(x.tipo, x.nivel, x.texto, x.id, x.classes) for x in b] == [
        ("titulo", 1, "Metodologia", "sec-met", []), ("titulo", 2, "Dados", "", []),
        ("titulo", 1, "Resumo", "", ["pre"])]


def test_paragrafo_junta_as_linhas():
    (b,) = blocos("primeira linha\nsegunda linha")
    assert (b.tipo, b.texto) == ("paragrafo", "primeira linha segunda linha")


def test_bloco_fonte_e_refs():
    b = blocos("::: fonte\nFonte: autores.\n:::\n\n::: {#refs}\n:::")
    assert (b[0].tipo, b[0].texto, b[0].filhos[0].texto) == ("div", "fonte", "Fonte: autores.")
    assert b[1].texto == "refs"


def test_bloco_aberto_sem_fechar_e_erro():
    with pytest.raises(ErroRelatorio, match="Linha 3: bloco '::: citacao' aberto e nunca fechado"):
        blocos("texto\n\n::: citacao\ncitação longa")


def test_figura_gerada_por_codigo_e_figura_de_arquivo():
    a, b = blocos("![Legenda A](#fig-a)\n\n![Legenda B](imagens/b.png){#fig-b largura=80%}")
    assert (a.tipo, a.id, a.texto, a.itens) == ("figura", "fig-a", "Legenda A", ["#fig-a"])
    assert (b.id, b.itens, b.attrs) == ("fig-b", ["imagens/b.png"], {"largura": "80%"})


def test_figura_sem_rotulo_fig_e_erro():
    with pytest.raises(ErroRelatorio, match="rótulo começando com 'fig-'"):
        blocos("![Legenda](imagens/x.png)")


def test_tabela_por_codigo_e_tabela_escrita_no_texto():
    a, b = blocos(": Gerada {#tbl-a}\n\n: Escrita {#tbl-b larguras=3,9}\n\n| x | y |\n|---|--:|\n| 1 | 2 |")
    assert (a.tipo, a.id, a.itens) == ("tabela", "tbl-a", [])
    assert (b.id, b.attrs, len(b.itens)) == ("tbl-b", {"larguras": "3,9"}, 3)


def test_tabela_sem_legenda_e_erro():
    with pytest.raises(ErroRelatorio, match="tabela sem legenda"):
        blocos("| x | y |\n|---|---|")


def test_equacao_numerada():
    (b,) = blocos("$$ p = 1 / (1 + e^−z^) $$ {#eq-logistica}")
    assert (b.tipo, b.id, b.texto) == ("equacao", "eq-logistica", "p = 1 / (1 + e^−z^)")


def test_listas_com_continuacao_e_subnivel():
    (b,) = blocos("- item um\n  continua\n  - subitem\n- item dois")
    assert b.tipo == "lista" and not b.ordenada
    assert b.itens == [(0, "item um continua"), (1, "subitem"), (0, "item dois")]
    (n,) = blocos("1. primeiro\n2. segundo")
    assert n.ordenada and [t for _, t in n.itens] == ["primeiro", "segundo"]


def test_bloco_de_codigo_com_arquivo_e_funcao():
    (b,) = blocos("```python arquivo=solucao_pim2/x.py funcao=Classe.metodo\n```")
    assert (b.tipo, b.id, b.attrs) == ("codigo", "python", {"arquivo": "solucao_pim2/x.py", "funcao": "Classe.metodo"})


def test_bloco_de_codigo_sem_fechar_e_erro():
    with pytest.raises(ErroRelatorio, match="nunca fechado"):
        blocos("```python\nx = 1")


# ----------------------------------------------------------------------------- texto corrido
def formatos(texto):
    return [(t.tipo, t.texto, "".join(sorted(t.fmt))) for t in ler_inline(texto)]


def test_negrito_italico_codigo_sobrescrito_e_subscrito():
    assert formatos("**forte** e *leve*") == [("texto", "forte", "b"), ("texto", " e ", ""), ("texto", "leve", "i")]
    assert formatos("`x_y`") == [("texto", "x_y", "code")]
    assert formatos("x^2^ e H~2~O") == [("texto", "x", ""), ("texto", "2", "sup"), ("texto", " e H", ""),
                                         ("texto", "2", "sub"), ("texto", "O", "")]


def test_italico_nao_pega_sublinhado_no_meio_da_palavra():
    assert texto_simples(ler_inline("dias_desde_ult e seq_falhas")) == "dias_desde_ult e seq_falhas"


def test_citacoes_entre_colchetes_e_no_texto():
    (c,) = [t for t in ler_inline("como mostram [@fader2007; @hosmer2013, p. 12].") if t.tipo == "cit"]
    assert c.itens == [("fader2007", ""), ("hosmer2013", "p. 12")] and not c.narrativa
    (n,) = [t for t in ler_inline("segundo @fawcett2006, a AUC") if t.tipo == "cit"]
    assert n.itens == [("fawcett2006", "")] and n.narrativa


def test_referencia_cruzada_e_email_nao_e_citacao():
    trechos = ler_inline("veja a @fig-roc e escreva para fulano@example.com")
    assert [(t.tipo, t.alvo) for t in trechos if t.tipo != "texto"] == [("ref", "fig-roc")]


def test_links_e_escapes():
    trechos = ler_inline(r"site [CEUB](https://ceub.br), <https://x.org> e um \*asterisco\*")
    assert [(t.tipo, t.texto, t.alvo) for t in trechos if t.tipo == "link"] == [
        ("link", "CEUB", "https://ceub.br"), ("link", "https://x.org", "https://x.org")]
    assert texto_simples(trechos).endswith("um *asterisco*")


def test_citacao_mal_escrita_e_erro():
    with pytest.raises(ErroRelatorio, match="citação mal escrita"):
        ler_inline("[@a, p. 1; b]", 5)


def test_valores_do_texto():
    assert substituir_valores("AUC de {{auc}} e {{ n }}", {"auc": "0,922", "n": "143"}, 1) == "AUC de 0,922 e 143"
    with pytest.raises(ErroRelatorio, match=r"Linha 9: o valor \{\{x\}\} não existe"):
        substituir_valores("{{x}}", {}, 9)
