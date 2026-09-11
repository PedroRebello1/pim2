from flask import Blueprint, flash, redirect, render_template, request, url_for

import pipeline
from auth import login_obrigatorio
from config import config
from extensions import cache, carregar_modelo, get_modelo, mongo

admin_bp = Blueprint("admin", __name__, url_prefix="/admin")


@admin_bp.route("/", methods=["GET", "POST"])
@login_obrigatorio
def index():
    if request.method == "POST":
        acao = request.form.get("acao")

        if acao == "salvar_limiares":
            try:
                alto = float(request.form["limiar_alto"])
                medio = float(request.form["limiar_medio"])
                if not (0 <= medio < alto <= 1):
                    raise ValueError("os limiares devem satisfazer 0 <= médio < alto <= 1")
                mongo.salvar_config({"limiar_alto": alto, "limiar_medio": medio})
                flash("Limiares de risco atualizados.", "ok")
            except (KeyError, ValueError) as e:
                flash(f"Valores inválidos para os limiares: {e}", "erro")

        elif acao == "recarregar_modelo":
            carregar_modelo()
            flash("Modelo recarregado." if get_modelo() else "Falha ao recarregar o modelo.",
                  "ok" if get_modelo() else "erro")

        elif acao == "retreinar":
            registro = pipeline.executar_treino(request.form.get("data_referencia") or None)
            if registro["status"] == "sucesso":
                flash(f"Treino concluído: {registro.get('algoritmo')} "
                      f"(ROC-AUC {registro.get('roc_auc_teste', 0):.3f}).", "ok")
            else:
                flash(f"Falha no treino: {registro.get('erro')}", "erro")

        elif acao == "pontuar":
            registro = pipeline.executar_pontuacao(request.form.get("data_referencia") or None)
            if registro["status"] == "sucesso":
                flash(f"Pontuação concluída: {registro.get('n_alunos')} alunos, "
                      f"{registro.get('n_alto_risco')} em alto risco.", "ok")
            else:
                flash(f"Falha na pontuação: {registro.get('erro')}", "erro")

        return redirect(url_for("admin.index"))

    cfg = mongo.obter_config() if mongo.disponivel else {}
    modelo = get_modelo()
    alto, medio = pipeline.limiares_atuais()
    execucoes = mongo.serie_execucoes(limite=15) if mongo.disponivel else []

    return render_template(
        "admin_config.html", cfg=cfg, config=config, modelo=modelo,
        mongo_ok=mongo.disponivel, redis_ok=cache.disponivel,
        limiar_alto=alto, limiar_medio=medio, execucoes=execucoes,
    )
