"""
seed.py
=======
Garante um usuário administrador inicial (idempotente — só cria se a coleção
`usuarios` estiver vazia). Rodado automaticamente na inicialização da app.
"""
from __future__ import annotations

import logging

from werkzeug.security import generate_password_hash

from config import config
from extensions import mongo

log = logging.getLogger("seed")


def garantir_admin():
    if not mongo.disponivel:
        log.warning("MongoDB indisponível — login usará as credenciais de ambiente (modo degradado).")
        return
    if mongo.contar_usuarios() == 0:
        mongo.criar_usuario(config.ADMIN_USER, generate_password_hash(config.ADMIN_PASSWORD), papel="admin")
        log.info("Usuário administrador inicial criado: %s", config.ADMIN_USER)
