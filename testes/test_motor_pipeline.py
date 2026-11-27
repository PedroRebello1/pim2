"""Motor completo (rodar.py) com exports sintéticos, numa pasta temporária.

Confere três coisas que o relatório depende: o motor roda de ponta a ponta com exports novos, os
resultados versionáveis não trazem dado pessoal, e o relatório consegue ler esses resultados.
"""
import json

import pandas as pd
import pytest

import fontes
import rodar
from sinteticos import salvar_xlsx, transacoes_sinteticas

ARQUIVOS = ["calibracao_teste.csv", "coeficientes.csv", "fila_amostra.csv", "fila_resumo.csv", "metricas.json",
            "politicas_teste.csv", "roc_teste.csv"]


@pytest.fixture(scope="module")
def execucao(tmp_path_factory):
    pasta = tmp_path_factory.mktemp("motor")
    exports, privada, resultados = pasta / "exports", pasta / "privada", pasta / "resultados"
    exports.mkdir()
    df = transacoes_sinteticas(n_cartoes=300, semente=11)
    # dois arquivos com linhas em comum (o carregador junta e tira as duplicadas) e um export que falhou
    salvar_xlsx(df.iloc[: len(df) * 2 // 3], exports / "transacoes_1.xlsx")
    salvar_xlsx(df.iloc[len(df) // 2:], exports / "transacoes_2.xlsx")
    (exports / "export_que_falhou.xlsx").write_bytes(b"PK")
    rodar.main([str(exports), str(privada), "--resultados", str(resultados)])
    return df, privada, resultados


def test_gera_todos_os_resultados(execucao):
    _, privada, resultados = execucao
    assert sorted(p.name for p in resultados.iterdir()) == ARQUIVOS
    assert (privada / "fila_do_dia.csv").exists()


def test_junta_exports_e_remove_duplicadas(execucao):
    df, _, resultados = execucao
    m = json.loads((resultados / "metricas.json").read_text(encoding="utf-8"))
    assert m["tentativas"] == len(df)
    assert m["cartoes"] == df["cartao"].nunique()
    assert m["periodo"] == ["15/08/2026", "15/10/2026"] and m["corte_teste"] == "01/10/2026"


def test_aprende_as_regras_do_perfil_sintetico(execucao):
    _, _, resultados = execucao
    m = json.loads((resultados / "metricas.json").read_text(encoding="utf-8"))
    assert m["codigos_irreversiveis"] == ["05", "Pac014"]
    assert m["teto_falhas"] is not None
    assert m["auc_teste"] > 0.75


def test_resultados_versionaveis_nao_tem_dados_pessoais(execucao):
    _, privada, resultados = execucao
    for arq in ARQUIVOS:
        texto = (resultados / arq).read_text(encoding="utf-8")
        assert "Titular Sintético" not in texto, arq      # nome do titular
        assert "******" not in texto, arq                 # cartão mascarado
    fila = pd.read_csv(privada / "fila_do_dia.csv", encoding="utf-8-sig")
    assert fila["titular"].str.startswith("Titular Sintético").all()   # a versão privada traz o nome


def test_amostra_da_fila_usa_pseudonimos(execucao):
    _, _, resultados = execucao
    amostra = pd.read_csv(resultados / "fila_amostra.csv")
    assert amostra["id"].str.fullmatch(r"C-[0-9A-F]{5}").all()


def test_recusa_pasta_privada_dentro_do_repositorio(tmp_path):
    dentro = rodar.REPOSITORIO / "fila_privada_de_teste"
    with pytest.raises(SystemExit) as erro:
        rodar.main([str(tmp_path), str(dentro), "--resultados", str(tmp_path / "r")])
    assert erro.value.code == 2
    assert not dentro.exists()


def test_recusa_pasta_sem_export_de_transacoes(tmp_path):
    (tmp_path / "vazia").mkdir()
    with pytest.raises(SystemExit):
        rodar.main([str(tmp_path / "vazia"), str(tmp_path / "privada"), "--resultados", str(tmp_path / "r")])


# ----------------------------------------------------------------------------- o relatório lê os resultados
@pytest.fixture
def relatorio_com_resultados_sinteticos(execucao, monkeypatch):
    _, _, resultados = execucao
    monkeypatch.setattr(fontes, "RESULTADOS", resultados)
    for f in (fontes._resultados, fontes.metricas):
        f.cache_clear()
    yield
    for f in (fontes._resultados, fontes.metricas):
        f.cache_clear()


def test_relatorio_regenera_com_resultados_novos_do_motor(relatorio_com_resultados_sinteticos, tmp_path):
    """Depois de rodar o motor com dados novos, os números, as tabelas e os gráficos saem sozinhos."""
    import figuras
    import tabelas
    import valores
    from abnt.tabela import TabelaABNT
    v = valores.calcular()
    assert v["fila_cartoes"].replace(".", "") == str(fontes.metricas()["fila_cartoes"])
    for rotulo in ("tbl-problema", "tbl-metricas", "tbl-calibracao", "tbl-regras", "tbl-politicas", "tbl-fila",
                   "tbl-fila-exemplos"):
        assert isinstance(tabelas.obter(rotulo), TabelaABNT), rotulo
    graficos = figuras.Figuras(tmp_path)
    for rotulo in ("fig-roc", "fig-razoes", "fig-politicas"):
        assert graficos.obter(rotulo).exists(), rotulo
