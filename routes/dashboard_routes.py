from flask import Blueprint, render_template

from auth import login_obrigatorio
from extensions import cache, get_modelo, mongo

dashboard_bp = Blueprint("dashboard", __name__)


@dashboard_bp.route("/")
@login_obrigatorio
def index():
    kpis = mongo.kpis_dashboard() if mongo.disponivel else {}
    execucoes = list(reversed(mongo.serie_execucoes(tipo="scoring", limite=12))) if mongo.disponivel else []
    dist_risco, referencia = mongo.distribuicao_risco() if mongo.disponivel else ([], None)
    planos = (mongo.resumo_planos() or [])[:8] if mongo.disponivel else []
    modelo = get_modelo()

    return render_template(
        "dashboard.html",
        kpis=kpis, execucoes=execucoes, dist_risco=dist_risco, referencia=referencia,
        planos=planos, modelo=modelo, mongo_ok=mongo.disponivel, redis_ok=cache.disponivel,
    )
