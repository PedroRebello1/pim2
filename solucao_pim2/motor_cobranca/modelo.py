"""P(aprovação | re-tentativa): regressão logística L2 em numpy (IRLS / Newton).

Sem scikit-learn no ambiente; a implementação é curta e totalmente inspecionável.
"""
import numpy as np
import pandas as pd

CATEGORICAS = ["ult_cod", "faixa_dia", "bandeira"]
NUMERICAS = ["seq_falhas", "dias_desde_ult", "ja_aprovou", "n_tent_mes", "duas_parcelas", "log_valor", "bin_taxa"]


def _sigmoide(z):
    return 1 / (1 + np.exp(-np.clip(z, -30, 30)))


class ModeloAprovacao:
    def __init__(self, l2=1.0, min_categoria=25, suavizacao_bin=20):
        self.l2, self.min_cat, self.m = l2, min_categoria, suavizacao_bin

    def _bin_taxa(self, df):
        return df["bin"].map(self.bin_map).fillna(self.bin_prior)

    def _matriz(self, df):
        cols = [np.ones(len(df))]
        nomes = ["intercepto"]
        x = df.assign(bin_taxa=self._bin_taxa(df))
        for c in NUMERICAS:
            cols.append(((x[c].astype(float) - self.mu[c]) / self.sd[c]).to_numpy())
            nomes.append(c)
        for c in CATEGORICAS:
            v = x[c].where(x[c].isin(self.cats[c]), "outros")
            for nivel in self.cats[c] + ["outros"]:
                cols.append((v == nivel).to_numpy(float))
                nomes.append(f"{c}={nivel}")
        self.nomes = nomes
        return np.column_stack(cols)

    def ajustar(self, df, y, df_bins):
        """df/y = re-tentativas de treino; df_bins = todas as tentativas do treino (taxa por emissor)."""
        self.bin_prior = df_bins["ok"].mean()
        s = df_bins.groupby("bin")["ok"].agg(["sum", "count"])
        self.bin_map = ((s["sum"] + self.m * self.bin_prior) / (s["count"] + self.m)).to_dict()
        self.cats = {c: [k for k, n in df[c].value_counts().items() if n >= self.min_cat] for c in CATEGORICAS}
        x = df.assign(bin_taxa=self._bin_taxa(df))
        self.mu = x[NUMERICAS].astype(float).mean()
        self.sd = x[NUMERICAS].astype(float).std().replace(0, 1)
        X, y = self._matriz(df), np.asarray(y, float)
        w = np.zeros(X.shape[1])
        reg = np.full(X.shape[1], self.l2)
        reg[0] = 0  # intercepto sem penalidade
        for _ in range(100):
            p = _sigmoide(X @ w)
            grad = X.T @ (p - y) + reg * w
            hess = (X * (p * (1 - p))[:, None]).T @ X + np.diag(reg)
            passo = np.linalg.solve(hess, grad)
            w -= passo
            if np.abs(passo).max() < 1e-8:
                break
        self.w = w
        return self

    def prever(self, df):
        return _sigmoide(self._matriz(df) @ self.w)

    def coeficientes(self):
        return pd.DataFrame({"atributo": self.nomes, "coef": self.w, "razao_chances": np.exp(self.w)}).iloc[1:]


# ---------------------------------------------------------------- métricas
def auc(y, p):
    y, p = np.asarray(y), np.asarray(p)
    r = pd.Series(p).rank().to_numpy()
    n1, n0 = y.sum(), len(y) - y.sum()
    return (r[y == 1].sum() - n1 * (n1 + 1) / 2) / (n1 * n0)


def brier(y, p):
    return float(np.mean((np.asarray(p) - np.asarray(y)) ** 2))


def curva_roc(y, p):
    y, p = np.asarray(y), np.asarray(p)
    ordem = np.argsort(-p)
    tp = np.cumsum(y[ordem]) / y.sum()
    fp = np.cumsum(1 - y[ordem]) / (len(y) - y.sum())
    return pd.DataFrame({"fpr": np.r_[0, fp], "tpr": np.r_[0, tp]})


def calibracao(y, p, n_faixas=5):
    df = pd.DataFrame({"y": y, "p": p})
    df["faixa"] = pd.qcut(df["p"].rank(method="first"), n_faixas, labels=False)
    return df.groupby("faixa").agg(p_media=("p", "mean"), taxa_real=("y", "mean"), n=("y", "size")).reset_index()


def lambda_por_validacao(treino, y_col, df_bins, data_corte, grade=(0.3, 1, 3, 10, 30)):
    """Escolhe o L2 com validação temporal DENTRO do treino (últimas 2 semanas como validação)."""
    ini_val = data_corte - pd.Timedelta(days=15)
    a, v = treino[treino["data"] < ini_val], treino[treino["data"] >= ini_val]
    bins_a = df_bins[df_bins["data"] < ini_val]
    res = {l2: auc(v[y_col], ModeloAprovacao(l2=l2).ajustar(a, a[y_col], bins_a).prever(v)) for l2 in grade}
    return max(res, key=res.get), res
