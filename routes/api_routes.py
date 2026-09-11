"""
routes/api_routes.py
=====================
No PIM1 a API de predição (`app.py`) era o produto inteiro: uma aplicação
Flask à parte, só com os endpoints de churn. No PIM2 ela vira um módulo
interno do painel — mesmos endpoints, mesmo contrato JSON (compatível com
qualquer integração que já existisse), mas rodando dentro da mesma aplicação
e reaproveitando as mesmas conexões Mongo/Redis e o mesmo modelo carregado.

Autenticação: token de portador (`Authorization: Bearer <API_TOKEN>`),
independente do login por sessão do painel — API_TOKEN vazio (padrão em dev)
desliga a exigência de token.
"""
from __future__ import annotations

from functools import wraps

from flask import Blueprint, jsonify, request

import churn_core as core
import pipeline
from config import config
from extensions import cache, carregar_modelo, get_modelo, mongo

api_bp = Blueprint("api", __name__, url_prefix="/api")


def requer_token(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        if config.API_TOKEN:
            enviado = request.headers.get("Authorization", "").replace("Bearer ", "")
            if enviado != config.API_TOKEN:
                return jsonify({"erro": "não autorizado"}), 401
        return f(*args, **kwargs)
    return wrapper


def _erro(msg, code):
    return jsonify({"erro": msg}), code


@api_bp.get("/health")
def health():
    modelo = get_modelo()
    return jsonify({
        "status": "ok" if modelo else "degradado",
        "modelo_carregado": bool(modelo),
        "modelo_versao": modelo.versao if modelo else None,
        "algoritmo": modelo.meta.get("algoritmo") if modelo else None,
        "mongodb": mongo.disponivel,
        "redis": cache.disponivel,
    })


@api_bp.get("/aluno/<id_aluno>/risco")
@requer_token
def risco_aluno(id_aluno: str):
    """Risco mais recente do aluno: tenta o cache (Redis); se falhar, o MongoDB."""
    em_cache = cache.get(id_aluno)
    if em_cache:
        return jsonify({**em_cache, "id_aluno": id_aluno, "origem": "cache"})

    doc = mongo.ultima_predicao(id_aluno)
    if doc:
        cache.set(id_aluno, {k: doc.get(k) for k in
                              ("prob_churn", "faixa_risco", "data_referencia", "modelo_versao")})
        return jsonify({**doc, "origem": "mongodb"})

    if not mongo.disponivel:
        return _erro("MongoDB indisponível; não há predições persistidas para consultar.", 503)
    return _erro(f"Nenhuma predição encontrada para o aluno {id_aluno}.", 404)


@api_bp.post("/predict")
@requer_token
def predict():
    """Calcula o risco para os atributos enviados, sem persistir (simulação/on-demand)."""
    modelo = get_modelo()
    if not modelo:
        return _erro("Modelo não carregado. Treine em Admin > Modelo.", 503)
    payload = request.get_json(silent=True)
    if not isinstance(payload, dict):
        return _erro("Envie um corpo JSON com os atributos do aluno.", 400)

    prob = modelo.prob_uma_linha(payload)
    alto, medio = pipeline.limiares_atuais()
    return jsonify({
        "prob_churn": round(prob, 4),
        "faixa_risco": core.faixa_risco(prob, alto, medio),
        "modelo_versao": modelo.versao,
        "atributos_esperados": core.FEATURES,
    })


@api_bp.get("/alto-risco")
@requer_token
def alto_risco():
    """Lista priorizada de alunos em alto risco do mês corrente (ou de uma data_referencia)."""
    if not mongo.disponivel:
        return _erro("MongoDB indisponível; a lista depende de predições persistidas.", 503)
    data_ref = request.args.get("data_referencia")
    try:
        limite = min(int(request.args.get("limite", config.ALTO_RISCO_LIMIT)), 1000)
    except (TypeError, ValueError):
        limite = config.ALTO_RISCO_LIMIT

    referencia = data_ref or mongo.ultima_data_referencia()
    itens = mongo.alto_risco(data_referencia=referencia, limite=limite)
    return jsonify({"data_referencia": referencia, "total": len(itens), "alunos": itens})


@api_bp.post("/admin/reload-model")
@requer_token
def reload_model():
    """Recarrega o artefato do modelo sem reiniciar o processo (ex.: após retreino externo)."""
    carregar_modelo()
    modelo = get_modelo()
    if not modelo:
        return _erro("Falha ao recarregar o modelo.", 500)
    return jsonify({"status": "recarregado", "modelo_versao": modelo.versao})


@api_bp.post("/admin/ingestao")
@requer_token
def ingestao_api():
    """Dispara a ingestão de um export via API — útil para automatizar por cron/orquestrador
    externo (seção 5.1 do documento de arquitetura do PIM1), sem depender da tela web."""
    import os

    from werkzeug.utils import secure_filename

    arquivo = request.files.get("arquivo")
    if not arquivo or not arquivo.filename:
        return _erro("envie o arquivo em 'arquivo' (multipart/form-data)", 400)

    os.makedirs(config.UPLOAD_DIR, exist_ok=True)
    caminho = os.path.join(config.UPLOAD_DIR, secure_filename(arquivo.filename))
    arquivo.save(caminho)

    data_referencia = request.form.get("data_referencia") or None
    registro = pipeline.executar_ingestao(caminho, data_referencia)
    codigo = 200 if registro["status"] == "sucesso" else 500
    return jsonify(registro), codigo
