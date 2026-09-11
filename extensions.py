"""
extensions.py
=============
Instâncias compartilhadas por toda a aplicação (padrão "extensions" do Flask):
conexão Mongo, cache Redis e o serviço do modelo de churn.

O modelo é carregado sob tentativa no import (como no `app.py` do PIM1): se o
artefato ainda não existir (primeira execução, antes de qualquer treino), a
aplicação sobe mesmo assim em modo degradado — o painel exibe isso claramente
e o módulo Admin permite treinar/recarregar sem reiniciar o processo.
"""
from __future__ import annotations

import logging

from storage import MongoStore, RedisCache
from model_service import ModelService

log = logging.getLogger("extensions")

mongo = MongoStore()
cache = RedisCache()

_estado = {"modelo": None}


def carregar_modelo() -> ModelService | None:
    try:
        _estado["modelo"] = ModelService()
    except Exception as e:  # noqa: BLE001
        _estado["modelo"] = None
        log.warning("Modelo indisponível (%s). Treine em Admin > Modelo.", e)
    return _estado["modelo"]


def get_modelo() -> ModelService | None:
    return _estado["modelo"]


carregar_modelo()  # tenta carregar já na inicialização do processo
