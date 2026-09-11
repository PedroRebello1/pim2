"""
auth.py
=======
Autenticação simples por sessão (server-side) para o painel administrativo.
Não usa Flask-Login nem qualquer biblioteca extra — apenas `flask.session`
(assinada com SECRET_KEY) e hashing de senha do próprio Werkzeug (dependência
que o Flask já traz).

Modo degradado: se o MongoDB não estiver disponível, não há onde consultar a
coleção `usuarios`, então o login aceita as credenciais de ADMIN_USER /
ADMIN_PASSWORD do ambiente — suficiente para demonstrar o painel offline,
claramente não recomendado para produção (ver README).
"""
from __future__ import annotations

from functools import wraps

from flask import g, redirect, request, session, url_for


def usuario_atual() -> str | None:
    return session.get("usuario")


def papel_atual() -> str:
    return session.get("papel", "admin")


def login_obrigatorio(view):
    @wraps(view)
    def wrapper(*args, **kwargs):
        if not usuario_atual():
            return redirect(url_for("auth.login", proximo=request.path))
        return view(*args, **kwargs)
    return wrapper
