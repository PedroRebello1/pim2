"""Regras aprendidas, avaliação por replay e fila do dia (solucao_pim2/motor_cobranca/politicas.py)."""
import zlib

import numpy as np
import pandas as pd
import pytest

from dados import atributos_tentativas
from politicas import avaliar, codigos_irreversiveis, fila_do_dia, limiar_por_retencao, pseudonimo, teto_de_falhas


def casos(ult_cod, n, aprovacoes, seq=1):
    return pd.DataFrame({"ult_cod": [ult_cod] * n, "ok": [1] * aprovacoes + [0] * (n - aprovacoes),
                         "seq_falhas": [seq] * n})


# ----------------------------------------------------------------------------- regras
def test_codigos_irreversiveis_pedem_no_maximo_1_por_cento_e_15_casos():
    treino = pd.concat([
        casos("A", 20, 0),      # 0% em 20 casos -> irreversível
        casos("B", 10, 0),      # 0%, mas só 10 casos -> fica de fora
        casos("C", 100, 1),     # exatamente 1% -> irreversível (o limite é inclusivo)
        casos("D", 100, 2),     # 2% -> recuperável
    ])
    assert codigos_irreversiveis(treino) == ["A", "C"]


def test_teto_de_falhas_ignora_codigos_irreversiveis():
    treino = pd.concat(
        [casos("51", 50, 10, seq=s) for s in (1, 2, 3)]          # recuperável: ~20% de aprovação
        + [casos("51", 40, 0, seq=s) for s in (4, 5, 6)]         # a partir de 4 recusas: 0%
        + [casos("05", 200, 0, seq=2)]                           # irreversível com 2 recusas: não conta
    )
    assert teto_de_falhas(treino, ["05"]) == 4


def test_teto_de_falhas_exige_30_casos_e_pode_nao_existir():
    poucos = pd.concat([casos("51", 50, 10, seq=1), casos("51", 20, 0, seq=5)])
    assert teto_de_falhas(poucos, []) is None
    sempre_aprova = pd.concat([casos("51", 50, 10, seq=s) for s in range(1, 8)])
    assert teto_de_falhas(sempre_aprova, []) is None


def test_limiar_e_o_quantil_de_5_por_cento_das_aprovacoes():
    """O limiar é o quantil de 5% das probabilidades das aprovações do treino, com a interpolação
    linear padrão do NumPy: mantém 95% das aprovações a menos de uma (o valor interpolado fica entre
    duas aprovações e deixa de fora a de baixo)."""
    rng = np.random.default_rng(3)
    p = rng.random(1000)
    y = (rng.random(1000) < p).astype(int)
    positivos = p[y == 1]
    tau = limiar_por_retencao(p, y, 0.95)
    assert tau == pytest.approx(np.quantile(positivos, 0.05))
    assert np.mean(positivos >= tau) >= 0.95 - 1 / len(positivos)


def test_avaliar_conta_tentativas_aprovacoes_e_perdas():
    teste = pd.DataFrame({"ok": [1, 0, 1, 0, 0], "valor": [100.0, 50, 80, 50, 50]})
    r = avaliar(teste, [True, False, False, True, True], "x")
    assert r == {"politica": "x", "tentativas": 3, "aprovacoes": 1, "valor_aprovado": 100.0, "evitadas": 2,
                 "aprovacoes_perdidas": 1}


def test_pseudonimo_curto_estavel_e_sem_o_nome():
    a = pseudonimo("411111******1111|FULANO DE TAL")
    assert a == pseudonimo("411111******1111|FULANO DE TAL")
    assert a != pseudonimo("411111******1111|BELTRANO")
    assert a.startswith("C-") and len(a) == 7 and a[2:] == a[2:].upper()
    assert "FULANO" not in a


# ----------------------------------------------------------------------------- fila do dia
class ModeloFalso:
    """Chance alta nos dias 10 a 14 e baixa nos demais, para conferir a escolha da data."""

    def prever(self, df):
        return np.where(df["faixa_dia"] == "10-14", 0.5, 0.1)


def cartao(nome, eventos, valor=99.9):
    return [(data, cod, f"4{zlib.crc32(nome.encode()) % 10 ** 5:05d}******0000", nome, valor, "1") for data, cod in eventos]


@pytest.fixture
def todas():
    linhas = (
        cartao("Irreversivel", [("2026-10-08 12:00", "05")])
        + cartao("Teto", [(f"2026-10-0{d} 12:00", "51") for d in (2, 3, 4, 5, 6, 7)])
        + cartao("Recuperavel", [("2026-10-08 12:00", "51")], valor=209.9)
        + cartao("Antigo", [("2026-09-20 12:00", "51")])                         # recusa há mais de 7 dias
        + cartao("Pagou", [("2026-10-02 12:00", "51"), ("2026-10-05 12:00", "00")])
        + cartao("PagouNoMes", [("2026-10-03 12:00", "00"), ("2026-10-08 12:00", "51")])
    )
    df = pd.DataFrame(linhas, columns=["data", "codigoRetorno", "cartao", "titular", "valor", "qtd_parcelas"])
    df["data"] = pd.to_datetime(df["data"])
    return atributos_tentativas(df)


def test_fila_so_traz_cartoes_com_cobranca_pendente(todas):
    hoje, fila = fila_do_dia(todas, ModeloFalso(), ["05"], teto=5, tau=0.2)
    assert hoje == pd.Timestamp("2026-10-08")
    assert set(fila["titular"]) == {"Irreversivel", "Teto", "Recuperavel"}


def test_fila_aplica_as_regras_na_ordem(todas):
    _, fila = fila_do_dia(todas, ModeloFalso(), ["05"], teto=5, tau=0.2)
    acao = fila.set_index("titular")["acao"]
    assert acao["Irreversivel"] == "Contato: novo cartão ou PIX"
    assert acao["Teto"] == "Contato: parar re-tentativas"       # 6ª recusa seguida >= teto de 5
    # chance máxima (50%) nos dias 10-14: o 1º dia que alcança 90% dela é 10/10
    assert acao["Recuperavel"] == "Re-tentar em 10/10"
    motivo = fila.set_index("titular")["motivo"]["Recuperavel"]
    assert motivo == "P(aprovação) 50% em 10/10 contra 10% amanhã"


def test_fila_sem_chance_suficiente_vira_contato(todas):
    _, fila = fila_do_dia(todas, ModeloFalso(), ["05"], teto=5, tau=0.9)
    assert fila.set_index("titular")["acao"]["Recuperavel"] == "Contato: baixa chance"


def test_fila_conta_a_proxima_recusa_seguida(todas):
    _, fila = fila_do_dia(todas, ModeloFalso(), ["05"], teto=None, tau=0.2)
    seguidas = fila.set_index("titular")["recusas_seguidas"]
    assert seguidas["Teto"] == 6 and seguidas["Recuperavel"] == 1
    assert fila.set_index("titular")["acao"]["Teto"].startswith("Re-tentar")   # sem teto, re-tenta
