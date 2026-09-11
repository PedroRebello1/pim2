"""
storage.py
==========
Camada de acesso a dados: MongoDB (banco operacional) e Redis (cache).

Evolução do `storage.py` do PIM1: mantém o mesmo espírito de degradação
graciosa (se Mongo/Redis não estiverem disponíveis, o painel continua de pé
em modo limitado) e acrescenta os métodos que o módulo de gestão geral
precisa — cadastro de alunos, usuários do painel, configuração em runtime e
as agregações que alimentam o dashboard e o financeiro.
"""
from __future__ import annotations

import json
import logging
from datetime import datetime, timezone

from config import config

log = logging.getLogger("storage")


# ===========================================================================
# MongoDB
# ===========================================================================
def _uri_segura(uri: str) -> str:
    """Oculta a senha do URI para registro em log (usuario:senha@ -> usuario:***@)."""
    if "@" not in uri or "://" not in uri:
        return uri
    esquema, resto = uri.split("://", 1)
    cred, _, host = resto.partition("@")
    if ":" in cred:
        usuario = cred.split(":", 1)[0]
        cred = f"{usuario}:***"
    return f"{esquema}://{cred}@{host}"


def _usar_tls() -> bool:
    """Decide se a conexão deve usar TLS. Atlas (mongodb+srv) exige TLS sempre."""
    modo = config.MONGO_TLS
    if modo == "on":
        return True
    if modo == "off":
        return False
    uri = config.MONGO_URI.lower()                       # modo "auto"
    return uri.startswith("mongodb+srv://") or "mongodb.net" in uri or "tls=true" in uri


class MongoStore:
    def __init__(self):
        self.disponivel = False
        self.db = None
        try:
            from pymongo import ASCENDING, DESCENDING
            self._ASC, self._DESC = ASCENDING, DESCENDING

            if config.MONGO_MOCK:
                # Banco em memória (mongomock) — sem servidor, sem Docker, sem rede.
                # Útil em máquinas travadas (ex.: laboratório institucional). Os
                # dados não persistem entre execuções do processo.
                import mongomock
                client = mongomock.MongoClient()
                log.info("MONGO_MOCK=true — usando MongoDB em memória (mongomock, sem servidor real).")
            else:
                from pymongo import MongoClient
                kwargs = {"serverSelectionTimeoutMS": config.MONGO_TIMEOUT_MS}
                if _usar_tls():
                    import certifi
                    kwargs["tls"] = True
                    kwargs["tlsCAFile"] = certifi.where()
                client = MongoClient(config.MONGO_URI, **kwargs)
                client.admin.command("ping")
                log.info("MongoDB conectado: %s/%s", _uri_segura(config.MONGO_URI), config.MONGO_DB)

            self.db = client[config.MONGO_DB]
            self._garantir_indices()
            self.disponivel = True
        except Exception as e:  # noqa: BLE001
            log.warning("MongoDB indisponível (%s). Operando em modo degradado.", e)

    def _garantir_indices(self):
        pred = self.db[config.COL_PREDICOES]
        pred.create_index([("id_aluno", self._ASC), ("data_referencia", self._DESC)])
        pred.create_index([("data_referencia", self._DESC), ("prob_churn", self._DESC)])

        parc = self.db[config.COL_PARCELAS]
        parc.create_index([("id_aluno", self._ASC), ("data_referencia", self._DESC)])
        parc.create_index([("data_referencia", self._DESC)])
        parc.create_index([("situacao", self._ASC), ("vencimento", self._ASC)])

        self.db[config.COL_ALUNOS].create_index([("id_aluno", self._ASC), ("data_referencia", self._DESC)])
        self.db[config.COL_EXECUCOES].create_index([("data_execucao", self._DESC)])

        cad = self.db[config.COL_CADASTRO]
        cad.create_index([("matricula", self._ASC)], unique=True)
        cad.create_index([("id_aluno", self._ASC)])
        cad.create_index([("nome", self._ASC)])
        cad.create_index([("situacao", self._ASC)])

        self.db[config.COL_USUARIOS].create_index([("username", self._ASC)], unique=True)

    # ----- leitura: predições / risco ---------------------------------------
    def ultima_predicao(self, id_aluno: str):
        if not self.disponivel:
            return None
        return self.db[config.COL_PREDICOES].find_one(
            {"id_aluno": id_aluno}, sort=[("data_referencia", self._DESC)], projection={"_id": 0})

    def predicoes_aluno(self, id_aluno: str, limite: int = 12):
        if not self.disponivel:
            return []
        return list(self.db[config.COL_PREDICOES]
                    .find({"id_aluno": id_aluno}, projection={"_id": 0})
                    .sort("data_referencia", self._DESC).limit(limite))

    def ultima_data_referencia(self):
        if not self.disponivel:
            return None
        doc = self.db[config.COL_PREDICOES].find_one(
            sort=[("data_referencia", self._DESC)], projection={"data_referencia": 1, "_id": 0})
        return doc["data_referencia"] if doc else None

    def alto_risco(self, data_referencia: str | None = None, limite: int = 100):
        if not self.disponivel:
            return []
        data_referencia = data_referencia or self.ultima_data_referencia()
        if data_referencia is None:
            return []
        cur = (self.db[config.COL_PREDICOES]
               .find({"data_referencia": data_referencia, "faixa_risco": "Alto"}, projection={"_id": 0})
               .sort("prob_churn", self._DESC).limit(limite))
        return list(cur)

    def distribuicao_risco(self, data_referencia: str | None = None):
        if not self.disponivel:
            return [], None
        data_referencia = data_referencia or self.ultima_data_referencia()
        if data_referencia is None:
            return [], None
        pipeline = [{"$match": {"data_referencia": data_referencia}},
                    {"$group": {"_id": "$faixa_risco", "n": {"$sum": 1}}}]
        return list(self.db[config.COL_PREDICOES].aggregate(pipeline)), data_referencia

    # ----- leitura: parcelas / base ML --------------------------------------
    def carregar_parcelas(self, data_referencia: str | None = None) -> list[dict]:
        if not self.disponivel:
            return []
        data_referencia = data_referencia or self.ultima_data_parcelas()
        filtro = {"data_referencia": data_referencia} if data_referencia else {}
        return list(self.db[config.COL_PARCELAS].find(filtro, projection={"_id": 0}))

    def ultima_data_parcelas(self):
        if not self.disponivel:
            return None
        doc = self.db[config.COL_PARCELAS].find_one(
            sort=[("data_referencia", self._DESC)], projection={"data_referencia": 1, "_id": 0})
        return doc["data_referencia"] if doc else None

    def parcelas_aluno(self, id_aluno: str, limite: int = 100):
        if not self.disponivel:
            return []
        return list(self.db[config.COL_PARCELAS]
                    .find({"id_aluno": id_aluno}, projection={"_id": 0})
                    .sort("vencimento", self._DESC).limit(limite))

    def alunos_por_referencia(self, data_referencia: str | None = None):
        if not self.disponivel:
            return []
        filtro = {"data_referencia": data_referencia} if data_referencia else {}
        return list(self.db[config.COL_ALUNOS].find(filtro, projection={"_id": 0}))

    def todos_alunos_ml(self):
        """Todas as bases agregadas já carregadas (todas as competências) — usado no retreino geral."""
        if not self.disponivel:
            return []
        return list(self.db[config.COL_ALUNOS].find({}, projection={"_id": 0}))

    # ----- leitura: financeiro -----------------------------------------------
    def resumo_financeiro(self, data_referencia: str | None = None):
        if not self.disponivel:
            return []
        filtro = {"data_referencia": data_referencia} if data_referencia else {}
        pipeline = [{"$match": filtro},
                    {"$group": {"_id": "$situacao", "n": {"$sum": 1}, "valor": {"$sum": "$valor"}}},
                    {"$sort": {"_id": 1}}]
        return list(self.db[config.COL_PARCELAS].aggregate(pipeline))

    def resumo_forma_pgto(self, limite: int = 8):
        if not self.disponivel:
            return []
        pipeline = [{"$match": {"situacao": "Pago"}},
                    {"$group": {"_id": "$forma_pgto", "n": {"$sum": 1}, "valor": {"$sum": "$valor"}}},
                    {"$sort": {"valor": -1}}, {"$limit": limite}]
        return list(self.db[config.COL_PARCELAS].aggregate(pipeline))

    def inadimplencia_por_plano(self, limite: int = 15):
        if not self.disponivel:
            return []
        pipeline = [{"$match": {"situacao": "Em Aberto"}},
                    {"$group": {"_id": "$plano", "n_parcelas": {"$sum": 1}, "valor_total": {"$sum": "$valor"}}},
                    {"$sort": {"valor_total": -1}}, {"$limit": limite}]
        return list(self.db[config.COL_PARCELAS].aggregate(pipeline))

    def parcelas_em_aberto(self, atrasadas_only: bool = False, limite: int = 200):
        if not self.disponivel:
            return []
        filtro = {"situacao": "Em Aberto"}
        if atrasadas_only:
            filtro["vencimento"] = {"$lt": datetime.now(timezone.utc)}
        return list(self.db[config.COL_PARCELAS].find(filtro, projection={"_id": 0})
                    .sort("vencimento", self._ASC).limit(limite))

    # ----- leitura: cadastro (gestão de alunos) ------------------------------
    def listar_alunos(self, busca: str | None = None, situacao: str | None = None,
                       pagina: int = 1, por_pagina: int = 20):
        if not self.disponivel:
            return [], 0
        filtro = {}
        if situacao:
            filtro["situacao"] = situacao
        if busca:
            filtro["$or"] = [{"nome": {"$regex": busca, "$options": "i"}},
                              {"matricula": {"$regex": busca, "$options": "i"}}]
        col = self.db[config.COL_CADASTRO]
        total = col.count_documents(filtro)
        itens = list(col.find(filtro, projection={"_id": 0}).sort("nome", self._ASC)
                     .skip((pagina - 1) * por_pagina).limit(por_pagina))
        return itens, total

    def buscar_aluno(self, matricula: str):
        if not self.disponivel:
            return None
        return self.db[config.COL_CADASTRO].find_one({"matricula": str(matricula)}, projection={"_id": 0})

    def buscar_aluno_por_id(self, id_aluno: str):
        if not self.disponivel:
            return None
        return self.db[config.COL_CADASTRO].find_one({"id_aluno": id_aluno}, projection={"_id": 0})

    def resumo_planos(self):
        if not self.disponivel:
            return []
        pipeline = [{"$group": {"_id": "$plano", "n_alunos": {"$sum": 1},
                                 "ticket_medio": {"$avg": "$valor_mensalidade"},
                                 "cancelados": {"$sum": {"$cond": [{"$eq": ["$situacao", "Cancelado"]}, 1, 0]}}}},
                    {"$sort": {"n_alunos": -1}}]
        return list(self.db[config.COL_CADASTRO].aggregate(pipeline))

    def kpis_dashboard(self):
        if not self.disponivel:
            return {}
        total_alunos = self.db[config.COL_CADASTRO].count_documents({})
        ativos = self.db[config.COL_CADASTRO].count_documents({"situacao": "Ativo"})
        cancelados = self.db[config.COL_CADASTRO].count_documents({"situacao": "Cancelado"})
        ultima_ref = self.ultima_data_referencia()
        alto_risco = (self.db[config.COL_PREDICOES]
                      .count_documents({"data_referencia": ultima_ref, "faixa_risco": "Alto"})
                      if ultima_ref else 0)
        em_aberto = self.db[config.COL_PARCELAS].count_documents({"situacao": "Em Aberto"})
        atrasadas = self.db[config.COL_PARCELAS].count_documents(
            {"situacao": "Em Aberto", "vencimento": {"$lt": datetime.now(timezone.utc)}})
        return {
            "total_alunos": total_alunos, "ativos": ativos, "cancelados": cancelados,
            "ultima_referencia": ultima_ref, "alto_risco": alto_risco,
            "parcelas_em_aberto": em_aberto, "parcelas_atrasadas": atrasadas,
        }

    # ----- escrita: cadastro (upsert incremental, não é substituído a cada mês) ---
    def upsert_cadastro(self, docs: list[dict]) -> int:
        """Upsert por matrícula. Feito em laço (não em bulk_write) de propósito:
        mantém compatibilidade tanto com o MongoDB real quanto com o modo
        MONGO_MOCK (mongomock) sem exigir a mesma versão de API de bulk write
        dos dois — o volume desta coleção (milhares de linhas, não milhões)
        não justifica a complexidade extra do bulk."""
        if not self.disponivel or not docs:
            return 0
        col = self.db[config.COL_CADASTRO]
        n = 0
        for d in docs:
            res = col.update_one({"matricula": d["matricula"]}, {"$set": d}, upsert=True)
            if res.upserted_id is not None or res.modified_count:
                n += 1
        return n

    # ----- escrita: coleções mensais (idempotentes por data_referencia) -----
    def _substituir_em_lote(self, colecao: str, data_referencia: str, docs: list[dict]) -> int:
        col = self.db[colecao]
        col.delete_many({"data_referencia": data_referencia})
        lote = max(int(config.MONGO_BATCH), 1)
        for ini in range(0, len(docs), lote):
            pedaco = docs[ini:ini + lote]
            if pedaco:
                col.insert_many(pedaco, ordered=False)
        return len(docs)

    def substituir_parcelas(self, data_referencia: str, docs: list[dict]) -> int:
        return self._substituir_em_lote(config.COL_PARCELAS, data_referencia, docs)

    def substituir_alunos(self, data_referencia: str, docs: list[dict]) -> int:
        return self._substituir_em_lote(config.COL_ALUNOS, data_referencia, docs)

    def substituir_predicoes(self, data_referencia: str, docs: list[dict]) -> int:
        return self._substituir_em_lote(config.COL_PREDICOES, data_referencia, docs)

    def registrar_execucao(self, doc: dict):
        if self.disponivel:
            self.db[config.COL_EXECUCOES].insert_one(dict(doc))

    def serie_execucoes(self, tipo: str | None = None, limite: int = 20):
        if not self.disponivel:
            return []
        filtro = {"tipo": tipo} if tipo else {}
        return list(self.db[config.COL_EXECUCOES].find(filtro, projection={"_id": 0})
                    .sort("data_execucao", self._DESC).limit(limite))

    # ----- usuários do painel -------------------------------------------------
    def buscar_usuario(self, username: str):
        if not self.disponivel:
            return None
        return self.db[config.COL_USUARIOS].find_one({"username": username})

    def criar_usuario(self, username: str, senha_hash: str, papel: str = "admin"):
        if not self.disponivel:
            return
        self.db[config.COL_USUARIOS].update_one(
            {"username": username},
            {"$setOnInsert": {"username": username, "senha_hash": senha_hash, "papel": papel,
                               "criado_em": datetime.now(timezone.utc)}},
            upsert=True)

    def contar_usuarios(self) -> int:
        if not self.disponivel:
            return 0
        return self.db[config.COL_USUARIOS].count_documents({})

    # ----- configuração mutável (limiares de risco etc.) ----------------------
    def obter_config(self) -> dict:
        if not self.disponivel:
            return {}
        return self.db[config.COL_CONFIG].find_one({"_id": "app"}) or {}

    def salvar_config(self, dados: dict):
        if not self.disponivel:
            return
        dados = dict(dados)
        dados["atualizado_em"] = datetime.now(timezone.utc)
        self.db[config.COL_CONFIG].update_one({"_id": "app"}, {"$set": dados}, upsert=True)


# ===========================================================================
# Redis
# ===========================================================================
class RedisCache:
    def __init__(self):
        self.disponivel = False
        self.r = None
        try:
            import redis
            self.r = redis.from_url(config.REDIS_URL, socket_connect_timeout=1.5, decode_responses=True)
            self.r.ping()
            self.disponivel = True
            log.info("Redis conectado: %s", config.REDIS_URL)
        except Exception as e:  # noqa: BLE001
            log.warning("Redis indisponível (%s). Cache desativado.", e)

    def _chave(self, id_aluno: str) -> str:
        return f"{config.REDIS_PREFIX}{id_aluno}"

    def get(self, id_aluno: str):
        if not self.disponivel:
            return None
        try:
            val = self.r.get(self._chave(id_aluno))
            return json.loads(val) if val else None
        except Exception:  # noqa: BLE001
            return None

    def set(self, id_aluno: str, dados: dict):
        if not self.disponivel:
            return
        try:
            self.r.set(self._chave(id_aluno), json.dumps(dados, default=str), ex=config.REDIS_TTL)
        except Exception:  # noqa: BLE001
            pass

    def set_many(self, registros: dict[str, dict]):
        if not self.disponivel or not registros:
            return
        try:
            pipe = self.r.pipeline()
            for id_aluno, dados in registros.items():
                pipe.set(self._chave(id_aluno), json.dumps(dados, default=str), ex=config.REDIS_TTL)
            pipe.execute()
        except Exception:  # noqa: BLE001
            pass
