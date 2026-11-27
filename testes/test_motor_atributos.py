"""Atributos de cada tentativa (solucao_pim2/motor_cobranca/dados.py), conferidos à mão."""
import numpy as np
import pandas as pd
import pytest

from dados import atributos_tentativas


def tentativas(linhas):
    df = pd.DataFrame(linhas, columns=["data", "codigoRetorno", "cartao", "titular", "valor", "qtd_parcelas"])
    df["data"] = pd.to_datetime(df["data"])
    return atributos_tentativas(df)


FULANO = ("411111******1111", "Fulano de Tal")


@pytest.fixture
def cartao_fulano():
    """Um cartão: recusa, recusa, aprova; mês seguinte recusa por código irreversível."""
    linhas = [
        ("2026-09-02 12:00", "51", *FULANO, 169.9, "1"),
        ("2026-09-03 12:00", "51", *FULANO, 169.9, "1"),
        ("2026-09-05 12:00", "00", *FULANO, 169.9, "1"),
        ("2026-10-02 12:00", "05", *FULANO, 169.9, "1"),
        ("2026-10-03 12:00", "05", *FULANO, 169.9, "1"),
        ("2026-11-01 12:00", "05", *FULANO, 169.9, "2"),
    ]
    return tentativas(linhas)


def test_ultimo_codigo_e_dias_desde_a_anterior(cartao_fulano):
    assert cartao_fulano["ult_cod"].tolist() == ["nenhum", "51", "51", "00", "05", "05"]
    assert cartao_fulano["dias_desde_ult"].tolist() == [31, 1, 2, 27, 1, 29]   # sem tentativa anterior: 31


def test_recusas_seguidas_zeram_depois_de_uma_aprovacao(cartao_fulano):
    # recusas imediatamente ANTES de cada tentativa, contadas desde a última aprovação
    assert cartao_fulano["seq_falhas"].tolist() == [0, 1, 2, 0, 1, 2]


def test_ja_aprovou_e_numero_da_tentativa_no_mes(cartao_fulano):
    assert cartao_fulano["ja_aprovou"].tolist() == [0, 0, 0, 1, 1, 1]
    assert cartao_fulano["n_tent_mes"].tolist() == [1, 2, 3, 1, 2, 1]


def test_retentativa_e_a_tentativa_logo_depois_de_uma_recusa(cartao_fulano):
    # 1ª tentativa do cartão e tentativa depois de uma aprovação não são re-tentativas
    assert cartao_fulano["retentativa"].tolist() == [False, True, True, False, True, True]


def test_primeira_cobranca_de_um_mes_depois_de_mes_recusado_conta_como_retentativa(cartao_fulano):
    """Definição atual do motor: re-tentativa é qualquer tentativa logo depois de uma recusa do mesmo
    cartão, mesmo quando é a primeira cobrança de um mês novo (aqui, 01/11 depois das recusas de outubro)."""
    novembro = cartao_fulano[cartao_fulano["data"].dt.month == 11].iloc[0]
    assert novembro["n_tent_mes"] == 1
    assert bool(novembro["retentativa"])


def test_atributos_do_cartao_e_do_valor(cartao_fulano):
    assert set(cartao_fulano["bandeira"]) == {"4"}
    assert set(cartao_fulano["bin"]) == {"411111"}
    assert cartao_fulano["duas_parcelas"].tolist() == [0, 0, 0, 0, 0, 1]
    assert np.allclose(cartao_fulano["log_valor"], np.log(169.9))
    assert cartao_fulano["ok"].tolist() == [0, 0, 1, 0, 0, 0]


@pytest.mark.parametrize("dia, faixa", [(1, "1-4"), (4, "1-4"), (5, "5-7"), (7, "5-7"), (8, "8-9"), (9, "8-9"),
                                        (10, "10-14"), (14, "10-14"), (15, "15-16"), (16, "15-16"),
                                        (17, "17-19"), (19, "17-19"), (20, "20-24"), (24, "20-24"),
                                        (25, "25-31"), (31, "25-31")])
def test_faixas_do_dia_do_mes(dia, faixa):
    t = tentativas([(f"2026-08-{dia:02d} 12:00", "51", *FULANO, 99.9, "1")])
    assert t["faixa_dia"].iloc[0] == faixa


def test_cartao_identificado_por_numero_e_titular_normalizado():
    t = tentativas([
        ("2026-09-01 12:00", "51", "522222******2222", "  Ciclâno  de Tál ", 99.9, "1"),
        ("2026-09-02 12:00", "51", "522222******2222", "CICLANO DE TAL", 99.9, "1"),
        ("2026-09-02 12:00", "51", "522222******2222", "Beltrano", 99.9, "1"),   # outro titular
    ])
    assert t["cartao_id"].nunique() == 2
    ciclano = t[t["cartao_id"].str.endswith("CICLANO DE TAL")]
    assert ciclano["seq_falhas"].tolist() == [0, 1]       # as duas grafias do nome são o mesmo cartão


def test_cartoes_nao_se_misturam():
    t = tentativas([
        ("2026-09-01 12:00", "51", *FULANO, 99.9, "1"),
        ("2026-09-01 12:05", "00", "533333******3333", "Beltrano", 99.9, "1"),
        ("2026-09-02 12:00", "51", *FULANO, 99.9, "1"),
    ])
    fulano = t[t["titular"] == "Fulano de Tal"]
    assert fulano["ult_cod"].tolist() == ["nenhum", "51"]
    assert fulano["ja_aprovou"].tolist() == [0, 0]       # a aprovação do outro cartão não conta
