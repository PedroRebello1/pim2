"""Regressão logística L2 e métricas (solucao_pim2/motor_cobranca/modelo.py)."""
import itertools

import numpy as np
import pytest

from dados import atributos_tentativas
from modelo import CATEGORICAS, NUMERICAS, ModeloAprovacao, auc, brier, calibracao, curva_roc, lambda_por_validacao
from sinteticos import preparar, transacoes_sinteticas


def auc_por_pares(y, p):
    """Definição da AUC: chance de uma aprovação ter probabilidade maior que uma recusa (empate vale 1/2)."""
    pos = [pi for yi, pi in zip(y, p) if yi == 1]
    neg = [pi for yi, pi in zip(y, p) if yi == 0]
    return np.mean([1.0 if a > b else 0.5 if a == b else 0.0 for a, b in itertools.product(pos, neg)])


@pytest.fixture(scope="module")
def tentativas():
    return atributos_tentativas(preparar(transacoes_sinteticas(n_cartoes=300, semente=11)))


@pytest.fixture(scope="module")
def treino_teste(tentativas):
    t = tentativas
    corte = t["data"].max().to_period("M").start_time
    treino_all = t[t["data"] < corte]
    treino, teste = treino_all[treino_all["retentativa"]], t[(t["data"] >= corte) & t["retentativa"]]
    return treino, teste, treino_all, corte


# ----------------------------------------------------------------------------- métricas
def test_auc_igual_a_definicao_por_pares_inclusive_com_empates():
    rng = np.random.default_rng(0)
    y = rng.integers(0, 2, 60)
    p = rng.integers(0, 6, 60) / 5          # muitos empates
    assert auc(y, p) == pytest.approx(auc_por_pares(y, p))


def test_auc_extremos():
    y = np.array([0, 0, 1, 1])
    assert auc(y, [0.1, 0.2, 0.8, 0.9]) == 1
    assert auc(y, [0.9, 0.8, 0.2, 0.1]) == 0
    assert auc(y, [0.5, 0.5, 0.5, 0.5]) == 0.5


def test_brier():
    assert brier([1, 0], [1.0, 0.0]) == 0
    assert brier([1, 0], [0.5, 0.5]) == pytest.approx(0.25)


def test_curva_roc_vai_de_0_a_1_sem_voltar():
    rng = np.random.default_rng(1)
    y = rng.integers(0, 2, 200)
    roc = curva_roc(y, rng.random(200))
    assert (roc.iloc[0]["fpr"], roc.iloc[0]["tpr"]) == (0, 0)
    assert roc.iloc[-1]["fpr"] == pytest.approx(1) and roc.iloc[-1]["tpr"] == pytest.approx(1)
    assert (roc["fpr"].diff().dropna() >= 0).all() and (roc["tpr"].diff().dropna() >= 0).all()


def test_calibracao_em_quintis_ordenados():
    rng = np.random.default_rng(2)
    p = rng.random(500)
    cal = calibracao((rng.random(500) < p).astype(int), p)
    assert list(cal["faixa"]) == [0, 1, 2, 3, 4]
    assert list(cal["n"]) == [100] * 5
    assert cal["p_media"].is_monotonic_increasing


# ----------------------------------------------------------------------------- modelo
def test_ajuste_converge_para_o_otimo_da_verossimilhanca_penalizada(treino_teste):
    treino, _, treino_all, _ = treino_teste
    m = ModeloAprovacao(l2=1).ajustar(treino, treino["ok"], treino_all)
    X, y = m._matriz(treino), treino["ok"].to_numpy(float)
    reg = np.full(X.shape[1], m.l2)
    reg[0] = 0
    p = 1 / (1 + np.exp(-(X @ m.w)))
    gradiente = X.T @ (p - y) + reg * m.w
    assert np.abs(gradiente).max() < 1e-6


def test_modelo_ordena_melhor_que_o_acaso_no_teste(treino_teste):
    treino, teste, treino_all, _ = treino_teste
    m = ModeloAprovacao(l2=1).ajustar(treino, treino["ok"], treino_all)
    p = m.prever(teste)
    assert ((p > 0) & (p < 1)).all()
    assert auc(teste["ok"], p) > 0.75


def test_regularizacao_maior_encolhe_os_coeficientes(treino_teste):
    treino, _, treino_all, _ = treino_teste
    normas = [np.linalg.norm(ModeloAprovacao(l2=l2).ajustar(treino, treino["ok"], treino_all).w[1:])
              for l2 in (0.3, 3, 30)]
    assert normas[0] > normas[1] > normas[2]


def test_taxa_do_bin_usa_so_os_dados_passados_no_ajuste(treino_teste):
    treino, _, treino_all, _ = treino_teste
    m = ModeloAprovacao().ajustar(treino, treino["ok"], treino_all)
    novo = treino.head(1).assign(bin="999999")          # emissor que não aparece no treino
    assert m._bin_taxa(novo).iloc[0] == pytest.approx(treino_all["ok"].mean())
    # suavização: (aprovações + m * taxa geral) / (tentativas + m)
    b = treino_all["bin"].iloc[0]
    grupo = treino_all[treino_all["bin"] == b]["ok"]
    esperado = (grupo.sum() + 20 * treino_all["ok"].mean()) / (len(grupo) + 20)
    assert m.bin_map[b] == pytest.approx(esperado)


def test_categorias_raras_viram_outros(treino_teste):
    treino, _, treino_all, _ = treino_teste
    raro = treino.copy()
    raro.iloc[:3, raro.columns.get_loc("ult_cod")] = "XYZ"     # 3 casos < 25
    m = ModeloAprovacao().ajustar(raro, raro["ok"], treino_all)
    assert "XYZ" not in m.cats["ult_cod"]
    assert "ult_cod=outros" in m.nomes


def test_coeficientes_tem_um_por_atributo_sem_intercepto(treino_teste):
    treino, _, treino_all, _ = treino_teste
    m = ModeloAprovacao().ajustar(treino, treino["ok"], treino_all)
    coef = m.coeficientes()
    assert list(coef.columns) == ["atributo", "coef", "razao_chances"]
    assert "intercepto" not in set(coef["atributo"])
    assert set(NUMERICAS) <= set(coef["atributo"])
    assert all(any(a.startswith(c + "=") for a in coef["atributo"]) for c in CATEGORICAS)
    assert np.allclose(coef["razao_chances"], np.exp(coef["coef"]))


def test_lambda_escolhido_por_validacao_temporal_dentro_do_treino(treino_teste):
    treino, _, treino_all, corte = treino_teste
    grade = (0.3, 1, 3, 10, 30)
    l2, res = lambda_por_validacao(treino, "ok", treino_all, corte, grade)
    assert set(res) == set(grade)
    assert l2 in grade and res[l2] == max(res.values())


def test_ajuste_e_deterministico(treino_teste):
    treino, _, treino_all, _ = treino_teste
    a = ModeloAprovacao(l2=1).ajustar(treino, treino["ok"], treino_all).w
    b = ModeloAprovacao(l2=1).ajustar(treino, treino["ok"], treino_all).w
    assert np.array_equal(a, b)
