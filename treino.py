"""
treino.py
=========
Motor de treino do modelo de churn — compara cinco algoritmos por ROC-AUC em
validação cruzada, escolhe o melhor, reajusta o vencedor sobre toda a base e
salva a Pipeline completa + metadados. É a mesma lógica do `train_model.py`
do PIM1, extraída para uma função reutilizável (`treinar_sobre_base`).

No PIM1 essa lógica só rodava via CLI, sempre a partir de um arquivo Excel.
Aqui ela é comum a dois consumidores:
  * `scripts/train_model.py`  — CLI equivalente ao do PIM1 (a partir de um export);
  * `pipeline.executar_treino` — botão "Retreinar" do painel (Admin), que lê a
    base já ingerida no MongoDB, sem precisar de um arquivo novo.
"""
from __future__ import annotations

import json
import os
from datetime import datetime, timezone

import joblib
import numpy as np
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.ensemble import GradientBoostingClassifier, RandomForestClassifier
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (accuracy_score, average_precision_score, f1_score,
                              precision_score, recall_score, roc_auc_score)
from sklearn.model_selection import StratifiedKFold, cross_val_score, train_test_split
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler
from sklearn.tree import DecisionTreeClassifier

import churn_core as core
from config import config

try:
    from xgboost import XGBClassifier
    TEM_XGB = True
except Exception:
    TEM_XGB = False

RANDOM_STATE = 42
TEST_SIZE = 0.25


def construir_preprocessador() -> ColumnTransformer:
    try:
        ohe = OneHotEncoder(handle_unknown="ignore", sparse_output=False)
    except TypeError:  # sklearn < 1.2
        ohe = OneHotEncoder(handle_unknown="ignore", sparse=False)
    return ColumnTransformer([
        ("num", Pipeline([("imp", SimpleImputer(strategy="median")),
                          ("sc", StandardScaler())]), core.NUM_FEATURES),
        ("cat", Pipeline([("imp", SimpleImputer(strategy="most_frequent")),
                          ("oh", ohe)]), core.CAT_FEATURES),
    ])


def definir_modelos(y_tr):
    n_pos = int(np.sum(y_tr)); n_neg = int(len(y_tr) - n_pos)
    spw = n_neg / max(n_pos, 1)
    modelos = {
        "Regressão Logística": LogisticRegression(max_iter=1000, class_weight="balanced",
                                                  random_state=RANDOM_STATE),
        "Árvore de Decisão":   DecisionTreeClassifier(max_depth=5, class_weight="balanced",
                                                      random_state=RANDOM_STATE),
        "Random Forest":       RandomForestClassifier(n_estimators=300, class_weight="balanced",
                                                      random_state=RANDOM_STATE),
        "Gradient Boosting":   GradientBoostingClassifier(random_state=RANDOM_STATE),
    }
    if TEM_XGB:
        modelos["XGBoost"] = XGBClassifier(n_estimators=300, max_depth=4, learning_rate=0.1,
                                           subsample=0.9, colsample_bytree=0.9,
                                           scale_pos_weight=spw, eval_metric="logloss",
                                           random_state=RANDOM_STATE)
    return modelos


def treinar_sobre_base(base: pd.DataFrame, out_path: str | None = None,
                        meta_path: str | None = None) -> dict:
    """Recebe a base já pronta (1 linha por aluno, com `core.FEATURES` + `core.ALVO`)
    e devolve o dicionário de metadados do modelo salvo (inclui métricas de teste)."""
    out_path = out_path or config.MODEL_PATH
    meta_path = meta_path or config.MODEL_META_PATH

    X, y = base[core.FEATURES], base[core.ALVO]
    if y.nunique() < 2:
        raise ValueError("A base de treino precisa ter alunos com e sem churn (rótulo constante).")

    pre = construir_preprocessador()
    X_tr, X_te, y_tr, y_te = train_test_split(
        X, y, test_size=TEST_SIZE, stratify=y, random_state=RANDOM_STATE)
    modelos = definir_modelos(y_tr)

    skf = StratifiedKFold(n_splits=5, shuffle=True, random_state=RANDOM_STATE)
    cv = {}
    for nome, est in modelos.items():
        pipe = Pipeline([("prep", pre), ("clf", est)])
        scores = cross_val_score(pipe, X, y, cv=skf, scoring="roc_auc")
        cv[nome] = (float(scores.mean()), float(scores.std()))

    melhor = max(cv, key=lambda k: cv[k][0])

    pipe = Pipeline([("prep", pre), ("clf", modelos[melhor])])
    pipe.fit(X_tr, y_tr)
    p = pipe.predict_proba(X_te)[:, 1]
    yp = pipe.predict(X_te)
    metricas = {
        "acuracia": float(accuracy_score(y_te, yp)),
        "precisao": float(precision_score(y_te, yp, zero_division=0)),
        "recall":   float(recall_score(y_te, yp, zero_division=0)),
        "f1":       float(f1_score(y_te, yp, zero_division=0)),
        "roc_auc":  float(roc_auc_score(y_te, p)),
        "pr_auc":   float(average_precision_score(y_te, p)),
        "roc_auc_cv_media": cv[melhor][0],
        "roc_auc_cv_desvio": cv[melhor][1],
    }

    modelo_prod = Pipeline([("prep", construir_preprocessador()), ("clf", modelos[melhor])])
    modelo_prod.fit(X, y)

    versao = datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S")
    meta = {
        "modelo_versao": versao,
        "algoritmo": melhor,
        "treinado_em": datetime.now(timezone.utc).isoformat(),
        "n_alunos_treino": int(len(base)),
        "taxa_churn_treino": float(y.mean()),
        "features": core.FEATURES,
        "num_features": core.NUM_FEATURES,
        "cat_features": core.CAT_FEATURES,
        "metricas_teste": metricas,
        "metricas_cv": {k: {"media": v[0], "desvio": v[1]} for k, v in cv.items()},
        "limiar_alto": config.LIMIAR_ALTO,
        "limiar_medio": config.LIMIAR_MEDIO,
    }

    os.makedirs(os.path.dirname(out_path) or ".", exist_ok=True)
    joblib.dump({"pipeline": modelo_prod, "meta": meta}, out_path)
    with open(meta_path, "w", encoding="utf-8") as f:
        json.dump(meta, f, ensure_ascii=False, indent=2)

    return meta
