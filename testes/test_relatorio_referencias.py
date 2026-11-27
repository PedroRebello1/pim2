"""Citações (NBR 10520) e referências (NBR 6023) a partir do refs.bib (relatorio/abnt/referencias.py)."""
import pytest

from abnt.markdown import ErroRelatorio
from abnt.referencias import Bibliografia, autores, ler_bib

BIB = r"""
% comentário: esta linha é ignorada
@book{hosmer2013,
  author    = {Hosmer, David W. and Lemeshow, Stanley and Sturdivant, Rodney X.},
  title     = {Applied logistic regression},
  edition   = {3},
  address   = {Hoboken},
  publisher = {Wiley},
  year      = {2013}
}
@article{brier1950,
  author  = {Brier, Glenn W.},
  title   = {Verification of forecasts expressed in terms of probability},
  journal = {Monthly Weather Review},
  volume  = {78},
  number  = {1},
  pages   = {1--3},
  year    = {1950}
}
@article{brown1992,
  author  = {Brown, Stephen J. and Goetzmann, William and Ibbotson, Roger G. and Ross, Stephen A.},
  title   = {Survivorship bias in performance studies},
  journal = {The Review of Financial Studies},
  year    = {1992}
}
@online{cielo_retry,
  author    = {{CIELO}},
  title     = {Card brands retry program},
  publisher = {Cielo},
  year      = {2024},
  url       = {https://exemplo.org/retry},
  urldate   = {2026-10-29}
}
@online{cielo_codigos,
  author    = {{CIELO}},
  title     = {Return codes {ABECS}},
  publisher = {Cielo},
  year      = {2024}
}
@book{fader2007,
  author = {Fader, Peter S. and Hardie, Bruce G. S.},
  title  = {How to project customer retention},
  year   = "2007"
}
"""


@pytest.fixture
def bib(tmp_path):
    arq = tmp_path / "refs.bib"
    arq.write_text(BIB, encoding="utf-8")
    b = Bibliografia(arq)
    for chave in ("hosmer2013", "brier1950", "brown1992", "cielo_retry", "cielo_codigos", "fader2007"):
        b.registrar(chave, 1)
    b.preparar()
    return b


def texto(trechos):
    return "".join(t for t, _ in trechos)


def test_le_campos_com_chaves_aninhadas_aspas_e_comentarios(tmp_path):
    arq = tmp_path / "refs.bib"
    arq.write_text(BIB, encoding="utf-8")
    obras = ler_bib(arq)
    assert len(obras) == 6
    assert obras["brier1950"]["pages"] == "1-3"                  # "--" vira hífen
    assert obras["fader2007"]["year"] == "2007"                  # valor entre aspas
    assert obras["cielo_codigos"]["title"] == "Return codes {ABECS}"


def test_chave_repetida_no_bib_e_erro(tmp_path):
    arq = tmp_path / "refs.bib"
    arq.write_text("@book{a, title={X}, year={2020}}\n@book{a, title={Y}, year={2021}}", encoding="utf-8")
    with pytest.raises(ErroRelatorio, match="duas vezes"):
        ler_bib(arq)


def test_autores_institucional_e_lista_incompleta():
    assert autores("{BRASIL}") == [{"sobrenome": "BRASIL", "prenome": "", "instituicao": True}]
    assert autores("Fulano Exemplo")[0]["sobrenome"] == "Exemplo"
    assert len(autores("Exemplo, Fulano and others")) == 4            # "and others" conta como et al.


@pytest.mark.parametrize("chave, esperado", [
    ("brier1950", "(Brier, 1950)"),
    ("fader2007", "(Fader; Hardie, 2007)"),
    ("hosmer2013", "(Hosmer; Lemeshow; Sturdivant, 2013)"),
    ("brown1992", "(Brown et al., 1992)"),
    ("cielo_retry", "(Cielo, 2024a)"),
    ("cielo_codigos", "(Cielo, 2024b)"),
])
def test_citacao_entre_parenteses(bib, chave, esperado):
    assert texto(bib.citacao([(chave, "")], narrativa=False)) == esperado


@pytest.mark.parametrize("chave, esperado", [
    ("brier1950", "Brier (1950)"),
    ("fader2007", "Fader e Hardie (2007)"),
    ("hosmer2013", "Hosmer, Lemeshow e Sturdivant (2013)"),
    ("brown1992", "Brown et al. (1992)"),
])
def test_citacao_no_texto(bib, chave, esperado):
    assert texto(bib.citacao([(chave, "")], narrativa=True)) == esperado


def test_et_al_sai_em_italico(bib):
    trechos = bib.citacao([("brown1992", "")], narrativa=False)
    assert ("et al.", frozenset({"i"})) in trechos


def test_citacao_com_pagina_e_com_varias_obras(bib):
    assert texto(bib.citacao([("brier1950", "p. 2")], narrativa=False)) == "(Brier, 1950, p. 2)"
    assert texto(bib.citacao([("brier1950", ""), ("fader2007", "")], narrativa=False)) == \
        "(Brier, 1950; Fader; Hardie, 2007)"


def test_referencia_de_livro(bib):
    ref = bib.referencia("hosmer2013")
    assert texto(ref) == ("HOSMER, David W.; LEMESHOW, Stanley; STURDIVANT, Rodney X. Applied logistic regression. "
                          "3. ed. Hoboken: Wiley, 2013.")
    assert ("Applied logistic regression", frozenset({"b"})) in ref       # título em negrito


def test_referencia_de_artigo(bib):
    assert texto(bib.referencia("brier1950")) == ("BRIER, Glenn W. Verification of forecasts expressed in terms of "
                                                  "probability. Monthly Weather Review, v. 78, n. 1, p. 1-3, 1950.")


def test_referencia_online_com_acesso_e_sem_local(bib):
    assert texto(bib.referencia("cielo_retry")) == ("CIELO. Card brands retry program. [S. l.]: Cielo, 2024a. "
                                                    "Disponível em: https://exemplo.org/retry. Acesso em: 29 out. 2026.")


def test_chaves_de_protecao_do_bibtex_nao_aparecem_na_referencia(bib):
    assert texto(bib.referencia("cielo_codigos")) == "CIELO. Return codes ABECS. [S. l.]: Cielo, 2024b."


def test_lista_so_com_as_citadas_em_ordem_alfabetica(tmp_path):
    arq = tmp_path / "refs.bib"
    arq.write_text(BIB, encoding="utf-8")
    b = Bibliografia(arq)
    for chave in ("hosmer2013", "fader2007", "brier1950"):        # ordem do texto
        b.registrar(chave, 1)
    b.preparar()
    assert [texto(r).split(",")[0] for r in b.lista()] == ["BRIER", "FADER", "HOSMER"]


def test_obra_fora_do_bib_e_erro_com_a_linha(bib):
    with pytest.raises(ErroRelatorio, match="Linha 12: a obra @nao_existe"):
        bib.registrar("nao_existe", 12)
