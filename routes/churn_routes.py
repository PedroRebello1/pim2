from flask import Blueprint, render_template, request

import churn_core as core
from auth import login_obrigatorio
from extensions import get_modelo, mongo
from pipeline import limiares_atuais

churn_bp = Blueprint("churn", __name__, url_prefix="/churn")


@churn_bp.route("/prever", methods=["GET", "POST"])
@login_obrigatorio
def prever():
    modelo = get_modelo()
    resultado = None

    if request.method == "POST":
        if not modelo:
            resultado = {"erro": "Modelo não carregado. Treine um modelo em Admin > Modelo."}
        else:
            payload = {campo: request.form.get(campo) for campo in core.FEATURES}
            prob = modelo.prob_uma_linha(payload)
            alto, medio = limiares_atuais()
            resultado = {
                "prob_churn": round(prob, 4),
                "faixa_risco": core.faixa_risco(prob, alto, medio),
                "modelo_versao": modelo.versao,
            }

    return render_template(
        "churn_predicao.html", resultado=resultado, modelo=modelo,
        num_features=core.NUM_FEATURES, cat_features=core.CAT_FEATURES,
        valores=request.form,
    )


@churn_bp.route("/alto-risco")
@login_obrigatorio
def alto_risco():
    referencia_pedida = request.args.get("data_referencia") or None
    itens, referencia = [], referencia_pedida

    if mongo.disponivel:
        referencia = referencia_pedida or mongo.ultima_data_referencia()
        itens = mongo.alto_risco(referencia, limite=200)
        for item in itens:
            aluno = mongo.buscar_aluno_por_id(item["id_aluno"])
            item["nome"] = aluno["nome"] if aluno else None
            item["matricula"] = aluno["matricula"] if aluno else None
            item["telefone"] = aluno["telefone"] if aluno else None

    return render_template("churn_alto_risco.html", itens=itens, referencia=referencia,
                            mongo_ok=mongo.disponivel)


@churn_bp.route("/execucoes")
@login_obrigatorio
def execucoes():
    itens = mongo.serie_execucoes(limite=50) if mongo.disponivel else []
    return render_template("churn_execucoes.html", itens=itens, mongo_ok=mongo.disponivel)
