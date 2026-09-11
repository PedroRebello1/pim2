"""
scripts/train_model.py
=======================
CLI equivalente ao `train_model.py` do PIM1, mas agora fina: toda a lógica de
comparação/treino mora em `treino.py` e é a mesma usada pelo botão
"Retreinar" do painel (routes/admin_routes.py -> pipeline.executar_treino).
Este script serve para treinar direto de um arquivo de export, sem precisar
subir o painel nem ter uma ingestão prévia no MongoDB.

Uso (a partir da raiz do projeto):
    python scripts/train_model.py CAMINHO_DO_EXPORT.xls [--out modelos/churn_model.joblib]
"""
from __future__ import annotations

import argparse
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import churn_core as core  # noqa: E402
from config import config  # noqa: E402
from treino import treinar_sobre_base  # noqa: E402


def main():
    ap = argparse.ArgumentParser(description="Treina e serializa o modelo de churn a partir de um export.")
    ap.add_argument("export", help="Caminho do export Excel da academia (.xls/.xlsx)")
    ap.add_argument("--out", default=config.MODEL_PATH)
    ap.add_argument("--meta", default=config.MODEL_META_PATH)
    args = ap.parse_args()

    print(f"[1/3] Carregando e preparando base a partir de: {args.export}")
    _, parcelas, _ = core.preparar_ingestao(args.export)
    base = core.construir_base_aluno(parcelas, com_alvo=True)
    print(f"      Alunos: {len(base)} | Taxa de churn: {base[core.ALVO].mean()*100:.1f}%")

    print("[2/3] Comparando modelos (validação cruzada estratificada, 5 folds)...")
    meta = treinar_sobre_base(base, args.out, args.meta)

    print(f"[3/3] OK. Modelo: {meta['algoritmo']} | Versão: {meta['modelo_versao']} | "
          f"ROC-AUC teste: {meta['metricas_teste']['roc_auc']:.3f}")
    print(f"Salvo em: {args.out}")


if __name__ == "__main__":
    main()
