"""Montagem do Word no padrão ABNT (relatorio/abnt/word.py), checklist e o relatório de verdade."""
import docx
import pandas as pd
import pytest
from PIL import Image

import gerar_relatorio
from abnt import moeda_br, numero_br, percentual_br, tabela_abnt
from abnt.markdown import ErroRelatorio, ler_blocos, ler_relatorio
from abnt.referencias import Bibliografia
from abnt.word import LARGURA_CODIGO, DocumentoABNT, quebrar_codigo

RESUMO = " ".join(["palavra"] * 160)
RELATORIO = f"""# Resumo {{.pre}}

{RESUMO}

**Palavras-chave**: um; dois; três.

::: listas
:::

# Introdução

Texto com {{{{n}}}} casos [@livro2020]; veja a @fig-a, a @tbl-a, a @sec-met e a @eq-a.

## Objetivos

### Objetivo geral

![Um gráfico](#fig-a)

::: fonte
Fonte: autores.
:::

: Uma tabela {{#tbl-a}}

::: fonte
Fonte: autores.
:::

# Metodologia {{#sec-met}}

$$ y = a + b $$ {{#eq-a}}

# Referências {{.pos}}

::: {{#refs}}
:::
"""


@pytest.fixture
def documento(tmp_path):
    bib = tmp_path / "refs.bib"
    bib.write_text("@book{livro2020, author={Exemplo, Autora}, title={Um livro}, year={2020}}", encoding="utf-8")
    png = tmp_path / "fig.png"
    Image.new("RGB", (600, 300), "white").save(png, dpi=(300, 300))

    def montar(texto=RELATORIO):
        meta = {"title": "Título", "autores": ["Autora Exemplo"], "natureza": "Relatório de teste.", "cidade": "Brasília",
                "ano": "2026", "logo": False}
        doc = DocumentoABNT(meta, {"n": "42"}, Bibliografia(bib), lambda rotulo: png,
                            lambda rotulo: tabela_abnt(pd.DataFrame({"x": [1, 2]})), tmp_path)
        blocos = ler_blocos(texto.split("\n"))
        doc.numerar(blocos)
        return doc, blocos
    return montar


# ----------------------------------------------------------------------------- quebra do código do apêndice
def test_largura_do_codigo_cabe_na_pagina():
    assert LARGURA_CODIGO == 98          # 16 cm de largura útil, Courier New 7,5 pt, 2 caracteres de folga


def test_linha_curta_de_codigo_fica_igual():
    assert quebrar_codigo("    x = 1") == ["    x = 1"]


def test_linha_longa_quebra_no_espaco_com_recuo_da_continuacao():
    linha = "    self.cats = {c: [k for k, n in df[c].value_counts().items() if n >= self.min_cat] for c in CATEGORICAS}"
    partes = quebrar_codigo(linha)
    assert partes == ["    self.cats = {c: [k for k, n in df[c].value_counts().items() if n >= self.min_cat] for c in",
                      "        CATEGORICAS}"]
    assert all(len(p) <= LARGURA_CODIGO for p in partes)


def test_quebra_nao_perde_nem_inventa_texto():
    linha = "        " + " ".join(f"palavra{i}" for i in range(60))
    partes = quebrar_codigo(linha, 40)
    assert all(len(p) <= 40 for p in partes)
    assert " ".join(p.strip() for p in partes) == linha.strip()
    assert all(p.startswith(" " * 12) for p in partes[1:])


def test_trecho_sem_espaco_e_cortado_na_largura():
    partes = quebrar_codigo("x" * 250, 98)
    assert [len(p) for p in partes] == [98, 98, 62]
    assert "".join(p.strip() for p in partes) == "x" * 250


# ----------------------------------------------------------------------------- numeração e referências cruzadas
def test_numeracao_de_secoes_figuras_tabelas_e_equacoes(documento):
    doc, _ = documento()
    assert [(e["numero"], e["titulo"]) for e in doc.sumario] == [
        ("1", "INTRODUÇÃO"), ("1.1", "Objetivos"), ("1.1.1", "Objetivo geral"), ("2", "METODOLOGIA"),
        ("", "REFERÊNCIAS")]
    assert doc.rotulos == {"fig-a": "Figura 1", "tbl-a": "Tabela 1", "sec-met": "Seção 2", "eq-a": "Equação 1"}
    assert doc.avisos == []


def test_documento_word_com_titulos_legendas_e_referencias(documento, tmp_path):
    doc, blocos = documento()
    caminho = tmp_path / "saida.docx"
    doc.construir(blocos).save(caminho)
    textos = [p.text for p in docx.Document(caminho).paragraphs]
    assert "1 INTRODUÇÃO" in textos and "1.1 Objetivos" in textos and "2 METODOLOGIA" in textos
    assert "Figura 1 – Um gráfico" in textos and "Tabela 1 – Uma tabela" in textos
    corpo = next(t for t in textos if t.startswith("Texto com"))
    assert corpo == "Texto com 42 casos (Exemplo, 2020); veja a Figura 1, a Tabela 1, a Seção 2 e a Equação 1."
    assert "EXEMPLO, Autora. Um livro. [S. l.: s. n.], 2020." in textos


def test_figura_nao_citada_gera_aviso(documento):
    doc, _ = documento(RELATORIO.replace("veja a @fig-a, ", "veja "))
    assert doc.avisos == ["A figura 'Um gráfico' (@fig-a) não é citada no texto."]


@pytest.mark.parametrize("troca, erro", [
    (("veja a @fig-a", "veja a @fig-b"), "referência cruzada @fig-b não aponta"),
    (("# Metodologia {#sec-met}", "# Metodologia {#fig-a}"), "rótulo #fig-a foi usado duas vezes"),
    (("## Objetivos", "## Objetivos\n\n#### Pulou um nível"), "título de nível 4 sem o nível acima"),
    (("[@livro2020]", "[@outro2021]"), "a obra @outro2021 não está no refs.bib"),
])
def test_erros_de_numeracao_e_de_citacao(documento, troca, erro):
    with pytest.raises(ErroRelatorio, match=erro):
        documento(RELATORIO.replace(*troca))


# ----------------------------------------------------------------------------- checklist automático
def test_checklist_sem_avisos(documento):
    doc, blocos = documento()
    assert gerar_relatorio.conferir({}, blocos, doc, RELATORIO) == []


def test_checklist_resumo_curto_sem_palavras_chave_e_sem_fonte(documento):
    texto = (RELATORIO.replace(RESUMO, "Resumo curto demais.").replace("um; dois; três", "uma só")
             .replace(": Uma tabela {#tbl-a}\n\n::: fonte\nFonte: autores.\n:::", ": Uma tabela {#tbl-a}"))
    doc, blocos = documento(texto)
    avisos = gerar_relatorio.conferir({}, blocos, doc, texto + "\n✏️ SUBSTITUA")
    assert any("O resumo tem 3 palavras" in a for a in avisos)
    assert any("Faltam palavras-chave" in a for a in avisos)
    assert any("falta o bloco '::: fonte' logo abaixo de @tbl-a" in a for a in avisos)
    assert any("✏️ SUBSTITUA" in a for a in avisos)


# ----------------------------------------------------------------------------- números no padrão brasileiro
def test_numeros_moeda_e_percentual():
    assert numero_br(1234567) == "1.234.567"
    assert numero_br(1234.5, 2) == "1.234,50"
    assert moeda_br(48693.85) == "R$ 48.693,85"
    assert percentual_br(0.153) == "15,3%"


def test_tabela_abnt_formata_e_alinha():
    df = pd.DataFrame({"nome": ["a", None], "n": [1200, 3], "taxa": [0.5, float("nan")], "ok": [True, False]})
    t = tabela_abnt(df, nomes={"n": "Casos"}, casas={"taxa": 1})
    assert t.cabecalho == ["nome", "Casos", "taxa", "ok"]
    assert t.linhas == [["a", "1.200", "0,5", "Sim"], ["–", "3", "–", "Não"]]
    assert t.alinhamentos == ["esq", "dir", "dir", "esq"]


# ----------------------------------------------------------------------------- o relatório de verdade
def test_relatorio_pi_monta_sem_avisos(tmp_path):
    """Equivale a 'python relatorio/gerar_relatorio.py --sem-pdf', sem gravar nada no repositório."""
    import figuras
    import tabelas
    import valores
    entrada = gerar_relatorio.BASE / "relatorio_pi.md"
    meta, blocos = ler_relatorio(entrada)
    doc = DocumentoABNT(meta, valores.calcular(), Bibliografia(gerar_relatorio.BASE / meta["bibliography"]),
                        figuras.Figuras(tmp_path).obter, tabelas.obter, gerar_relatorio.BASE)
    doc.numerar(blocos)
    doc.construir(blocos).save(tmp_path / "relatorio.docx")
    assert gerar_relatorio.conferir(meta, blocos, doc, entrada.read_text(encoding="utf-8")) == []
    assert len(doc.figuras) == 9 and len(doc.tabelas) == 11
