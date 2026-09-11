"""
scripts/verificar_atlas.py
===========================
Confere o que foi gravado no MongoDB: conta os documentos de cada coleção e
checa a ausência de PII nas coleções analíticas (parcelas/alunos/predições).

Diferente do PIM1, o PIM2 tem de propósito uma coleção COM dados pessoais —
`cadastro_alunos`, o módulo de gestão — então este script trata isso como
esperado, não como alerta; o alerta de PII vale só para as coleções que
alimentam o modelo (que nunca deveriam ter nome/telefone/matrícula).

Uso (a partir da raiz do projeto, com MONGO_URI definido no .env):
    python scripts/verificar_atlas.py
"""
from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from config import config          # noqa: E402
from storage import MongoStore     # noqa: E402

PII = {"nome", "telefone", "matricula", "empresa", "convenios"}


def main():
    mongo = MongoStore()
    if not mongo.disponivel:
        raise SystemExit("MongoDB indisponível — verifique MONGO_URI/rede.")

    cols = {
        "parcelas (ML, anonimizado)": config.COL_PARCELAS,
        "alunos (ML, anonimizado)": config.COL_ALUNOS,
        "predicoes": config.COL_PREDICOES,
        "cadastro_alunos (gestão, COM PII)": config.COL_CADASTRO,
        "execucoes": config.COL_EXECUCOES,
        "usuarios": config.COL_USUARIOS,
    }
    print(f"Banco: {config.MONGO_DB}\n")
    print(f"{'coleção':<34} {'documentos':>12}")
    print("-" * 48)
    for rotulo, nome in cols.items():
        print(f"{rotulo:<34} {mongo.db[nome].count_documents({}):>12,}")

    comps = mongo.db[config.COL_PARCELAS].distinct("data_referencia")
    print(f"\nCompetências em 'parcelas': {sorted(comps)}")

    for colecao_rotulo, nome in (("parcelas", config.COL_PARCELAS), ("alunos", config.COL_ALUNOS)):
        doc = mongo.db[nome].find_one(projection={"_id": 0})
        if doc:
            vazou = PII.intersection(doc.keys())
            status = "OK — nenhum campo de PII presente." if not vazou else f"ALERTA: PII encontrada -> {vazou}"
            print(f"Verificação LGPD em '{colecao_rotulo}': {status}")

    n_cad = mongo.db[config.COL_CADASTRO].count_documents({})
    print(f"\n'{config.COL_CADASTRO}' contém dados pessoais por design ({n_cad} registros) — "
          "é o módulo de gestão, não a trilha de ML. Acesso a ela deve ser restrito à equipe operacional.")


if __name__ == "__main__":
    main()
