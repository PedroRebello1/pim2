from flask import Blueprint, render_template, request

from auth import login_obrigatorio
from extensions import mongo

financeiro_bp = Blueprint("financeiro", __name__, url_prefix="/financeiro")


@financeiro_bp.route("/")
@login_obrigatorio
def index():
    if not mongo.disponivel:
        return render_template("financeiro.html", mongo_ok=False)

    data_referencia = request.args.get("data_referencia") or None
    resumo = mongo.resumo_financeiro(data_referencia)
    formas = mongo.resumo_forma_pgto()
    inadimplencia = mongo.inadimplencia_por_plano()
    atrasadas = mongo.parcelas_em_aberto(atrasadas_only=True, limite=150)
    for parcela in atrasadas:
        aluno = mongo.buscar_aluno_por_id(parcela["id_aluno"])
        parcela["nome"] = aluno["nome"] if aluno else None
        parcela["matricula"] = aluno["matricula"] if aluno else None

    return render_template(
        "financeiro.html", mongo_ok=True, resumo=resumo, formas=formas,
        inadimplencia=inadimplencia, atrasadas=atrasadas, data_referencia=data_referencia,
    )
