"""
pipeline.py
===========
Orquestra as rotinas que no PIM1 eram três scripts CLI separados e
independentes (`ingest_parcelas.py`, `batch_scoring.py`, `train_model.py`).
Aqui viram três funções de uma só implementação, chamadas tanto pela
interface web (routes/ingestao_routes.py, routes/admin_routes.py) quanto
pelos scripts equivalentes em scripts/ — evitando a duplicação de lógica que
existia entre os scripts do PIM1.

Cada execução (ingestão, pontuação ou treino) é registrada na coleção
`execucoes`, com status, duração e principais números — a mesma ideia de
observabilidade do `model_runs` do PIM1 (seção 10 do doc de arquitetura),
agora cobrindo as três rotinas em um único histórico.
"""
from __future__ import annotations

import logging
import os
import shutil
from datetime import datetime, timezone

import pandas as pd

import churn_core as core
from config import config
from extensions import cache, carregar_modelo, get_modelo, mongo
from treino import treinar_sobre_base

log = logging.getLogger("pipeline")


def _mes_corrente() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m")


def _registrar(tipo: str, data_referencia: str | None, status: str, detalhes: dict,
                erro: str | None = None, inicio: datetime | None = None) -> dict:
    fim = datetime.now(timezone.utc)
    registro = {
        "run_id": f"{tipo}_{fim.strftime('%Y%m%d%H%M%S')}",
        "tipo": tipo,
        "data_execucao": fim.isoformat(),
        "data_referencia": data_referencia,
        "status": status,
        "erro": erro,
        "duracao_seg": round((fim - inicio).total_seconds(), 1) if inicio else None,
        **detalhes,
    }
    mongo.registrar_execucao(registro)
    log.info("[%s] %s: %s", registro["run_id"], status, {k: v for k, v in detalhes.items()})
    return registro


def limiares_atuais() -> tuple[float, float]:
    """Limiares de risco vigentes: config editável (Admin) > metadados do modelo > .env."""
    alto, medio = config.LIMIAR_ALTO, config.LIMIAR_MEDIO
    modelo = get_modelo()
    if modelo:
        alto, medio = modelo.limiar_alto, modelo.limiar_medio
    if mongo.disponivel:
        cfg = mongo.obter_config()
        alto = float(cfg.get("limiar_alto", alto))
        medio = float(cfg.get("limiar_medio", medio))
    return alto, medio


def executar_ingestao(caminho_export: str, data_referencia: str | None = None,
                       pontuar: bool = True) -> dict:
    """Camada raw (cópia imutável) -> limpeza -> cadastro + anonimização -> Mongo -> (pontuação)."""
    data_referencia = data_referencia or _mes_corrente()
    inicio = datetime.now(timezone.utc)

    if not mongo.disponivel:
        return _registrar("ingestao", data_referencia, "falha", {},
                           erro="MongoDB indisponível — não é possível persistir a ingestão.", inicio=inicio)
    try:
        destino_raw = os.path.join(config.RAW_DIR, data_referencia, os.path.basename(caminho_export))
        os.makedirs(os.path.dirname(destino_raw), exist_ok=True)
        if os.path.abspath(destino_raw) != os.path.abspath(caminho_export):
            shutil.copyfile(caminho_export, destino_raw)

        limpo, parcelas, cadastro = core.preparar_ingestao(caminho_export)
        base = core.construir_base_aluno(parcelas, com_alvo=True)

        n_parcelas = mongo.substituir_parcelas(data_referencia, core.parcelas_para_docs(parcelas, data_referencia))
        n_alunos = mongo.substituir_alunos(data_referencia, core.alunos_para_docs(base, data_referencia))
        n_cadastro = mongo.upsert_cadastro(core.cadastro_para_docs(cadastro))

        detalhes = {
            "n_parcelas": n_parcelas, "n_alunos": n_alunos, "n_cadastro_atualizado": n_cadastro,
            "taxa_churn": float(base[core.ALVO].mean()) if core.ALVO in base and len(base) else None,
            "arquivo_raw": destino_raw,
        }
        registro = _registrar("ingestao", data_referencia, "sucesso", detalhes, inicio=inicio)

        if pontuar and get_modelo():
            registro["pontuacao"] = executar_pontuacao(data_referencia)
        return registro
    except Exception as e:  # noqa: BLE001
        log.exception("Falha na ingestão")
        return _registrar("ingestao", data_referencia, "falha", {}, erro=str(e), inicio=inicio)


def executar_pontuacao(data_referencia: str | None = None) -> dict:
    """Aplica o modelo vigente sobre a base `alunos` já ingerida e grava `predicoes` + cache."""
    data_referencia = data_referencia or _mes_corrente()
    inicio = datetime.now(timezone.utc)

    modelo = get_modelo()
    if not modelo:
        return _registrar("scoring", data_referencia, "falha", {}, erro="Modelo não carregado.", inicio=inicio)
    if not mongo.disponivel:
        return _registrar("scoring", data_referencia, "falha", {}, erro="MongoDB indisponível.", inicio=inicio)

    try:
        docs = mongo.alunos_por_referencia(data_referencia)
        base = pd.DataFrame(docs)
        if base.empty:
            raise RuntimeError(f"Nenhuma base de alunos para {data_referencia}. Rode a ingestão primeiro.")

        probs = modelo.prob_lote(base)
        alto, medio = limiares_atuais()
        agora = datetime.now(timezone.utc).isoformat()
        docs_pred, cache_regs = [], {}
        for id_aluno, prob in zip(base["id_aluno"], probs):
            prob = float(prob)
            faixa = core.faixa_risco(prob, alto, medio)
            doc = {"id_aluno": id_aluno, "prob_churn": round(prob, 4), "faixa_risco": faixa,
                   "data_referencia": data_referencia, "modelo_versao": modelo.versao, "pontuado_em": agora}
            docs_pred.append(doc)
            cache_regs[id_aluno] = {k: doc[k] for k in
                                     ("prob_churn", "faixa_risco", "data_referencia", "modelo_versao")}

        n_alto = sum(1 for d in docs_pred if d["faixa_risco"] == "Alto")
        mongo.substituir_predicoes(data_referencia, docs_pred)
        cache.set_many(cache_regs)

        detalhes = {"n_alunos": len(docs_pred), "n_alto_risco": n_alto, "modelo_versao": modelo.versao}
        return _registrar("scoring", data_referencia, "sucesso", detalhes, inicio=inicio)
    except Exception as e:  # noqa: BLE001
        log.exception("Falha na pontuação")
        return _registrar("scoring", data_referencia, "falha", {}, erro=str(e), inicio=inicio)


def executar_treino(data_referencia: str | None = None) -> dict:
    """Retreina o modelo a partir da base `alunos` já ingerida no MongoDB (sem precisar de arquivo)."""
    inicio = datetime.now(timezone.utc)
    if not mongo.disponivel:
        return _registrar("treino", data_referencia, "falha", {}, erro="MongoDB indisponível.", inicio=inicio)
    try:
        docs = mongo.alunos_por_referencia(data_referencia) if data_referencia else mongo.todos_alunos_ml()
        if not docs:
            raise RuntimeError("Nenhuma base de alunos encontrada para treino. Rode a ingestão primeiro.")
        base = pd.DataFrame(docs).drop_duplicates(subset=["id_aluno"], keep="last")

        meta = treinar_sobre_base(base)
        carregar_modelo()  # recarrega o ModelService com o artefato recém-salvo

        detalhes = {
            "algoritmo": meta["algoritmo"], "roc_auc_teste": meta["metricas_teste"]["roc_auc"],
            "n_alunos_treino": meta["n_alunos_treino"], "modelo_versao": meta["modelo_versao"],
        }
        return _registrar("treino", data_referencia, "sucesso", detalhes, inicio=inicio)
    except Exception as e:  # noqa: BLE001
        log.exception("Falha no treino")
        return _registrar("treino", data_referencia, "falha", {}, erro=str(e), inicio=inicio)
