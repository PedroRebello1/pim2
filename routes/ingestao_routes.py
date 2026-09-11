import os

from flask import Blueprint, flash, render_template, request
from werkzeug.utils import secure_filename

import pipeline
from auth import login_obrigatorio
from config import config
from extensions import mongo

ingestao_bp = Blueprint("ingestao", __name__, url_prefix="/ingestao")

EXTENSOES_PERMITIDAS = {".xls", ".xlsx"}


@ingestao_bp.route("/", methods=["GET", "POST"])
@login_obrigatorio
def index():
    resultado = None

    if request.method == "POST":
        arquivo = request.files.get("arquivo")
        data_referencia = request.form.get("data_referencia") or None

        if not arquivo or not arquivo.filename:
            flash("Selecione um arquivo de export (.xls ou .xlsx).", "erro")
        elif os.path.splitext(arquivo.filename)[1].lower() not in EXTENSOES_PERMITIDAS:
            flash("Formato não suportado — envie um .xls ou .xlsx.", "erro")
        else:
            nome_seguro = secure_filename(arquivo.filename)
            os.makedirs(config.UPLOAD_DIR, exist_ok=True)
            caminho = os.path.join(config.UPLOAD_DIR, nome_seguro)
            arquivo.save(caminho)

            resultado = pipeline.executar_ingestao(caminho, data_referencia)
            if resultado["status"] == "sucesso":
                flash(f"Ingestão concluída para {resultado['data_referencia']}.", "ok")
            else:
                flash(f"Falha na ingestão: {resultado.get('erro')}", "erro")

    historico = mongo.serie_execucoes(tipo="ingestao", limite=10) if mongo.disponivel else []
    return render_template("ingestao.html", resultado=resultado, historico=historico,
                            mongo_ok=mongo.disponivel)
