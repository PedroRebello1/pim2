"""
app.py
======
Painel de Gestão de Academias — CEUB (PIM2).

Evolução do PIM1: o que antes era só uma API de predição de churn (app.py do
PIM1) agora é um módulo interno (routes/api_routes.py, prefixo /api) dentro
de um serviço web maior — um painel administrativo focado em dados, cobrindo
cadastro de alunos, financeiro/inadimplência e o módulo de churn (predição,
alto risco, execuções), além das rotinas de ingestão, pontuação e treino que
no PIM1 eram scripts CLI avulsos (ver pipeline.py).

Execução (desenvolvimento):
    python app.py
Produção (recomendado):
    gunicorn -w 4 -b 0.0.0.0:8000 --timeout 120 app:app
"""
from __future__ import annotations

import logging

from flask import Flask

import seed
from auth import papel_atual, usuario_atual
from config import config
from extensions import cache, mongo  # noqa: F401 — garante a inicialização das conexões
from routes.admin_routes import admin_bp
from routes.alunos_routes import alunos_bp
from routes.api_routes import api_bp
from routes.auth_routes import auth_bp
from routes.churn_routes import churn_bp
from routes.dashboard_routes import dashboard_bp
from routes.financeiro_routes import financeiro_bp
from routes.ingestao_routes import ingestao_bp

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s [%(name)s] %(message)s")


def create_app() -> Flask:
    app = Flask(__name__)
    app.secret_key = config.SECRET_KEY
    app.config["MAX_CONTENT_LENGTH"] = config.UPLOAD_MAX_MB * 1024 * 1024

    for bp in (auth_bp, dashboard_bp, alunos_bp, financeiro_bp, churn_bp, ingestao_bp, admin_bp, api_bp):
        app.register_blueprint(bp)

    @app.context_processor
    def contexto_global():
        return {
            "usuario_logado": usuario_atual(),
            "papel_logado": papel_atual(),
            "mongo_status": mongo.disponivel,
            "redis_status": cache.disponivel,
        }

    with app.app_context():
        seed.garantir_admin()

    return app


app = create_app()

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8000, debug=True)
