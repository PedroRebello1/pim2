"""
config.py
=========
Configuração central via variáveis de ambiente (12-factor), evoluída do PIM1.

Novidades em relação ao PIM1:
  * SECRET_KEY / ADMIN_USER / ADMIN_PASSWORD — o painel agora tem login.
  * COL_CADASTRO / COL_USUARIOS — novas coleções do módulo de gestão.
  * COL_EXECUCOES substitui COL_MODEL_RUNS: o log de execuções agora cobre
    ingestão, pontuação e treino (não só "rodadas do modelo").
  * RAW_DIR / UPLOAD_DIR — camada "raw" (seção 4.1 do doc de arquitetura do
    PIM1) simulada em disco local nesta fase (em produção seria um bucket).
"""
import os

try:
    from dotenv import load_dotenv
    load_dotenv()
except Exception:
    pass  # python-dotenv é opcional; sem ele apenas o ambiente real é lido


def _f(nome: str, default: float) -> float:
    try:
        return float(os.getenv(nome, default))
    except (TypeError, ValueError):
        return default


class Config:
    # ----- Aplicação web -----------------------------------------------------
    SECRET_KEY = os.getenv("SECRET_KEY", "dev-secret-troque-em-producao")
    ADMIN_USER = os.getenv("ADMIN_USER", "admin")
    ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD", "admin123")
    UPLOAD_MAX_MB = int(os.getenv("UPLOAD_MAX_MB", "50"))
    RAW_DIR = os.getenv("RAW_DIR", "data/raw")
    UPLOAD_DIR = os.getenv("UPLOAD_DIR", "data/uploads")

    # ----- Artefato do modelo -------------------------------------------------
    MODEL_PATH = os.getenv("MODEL_PATH", "modelos/churn_model.joblib")
    MODEL_META_PATH = os.getenv("MODEL_META_PATH", "modelos/churn_model.meta.json")

    # ----- Faixas de risco (padrão; podem ser sobrepostas em Admin > Config) --
    LIMIAR_ALTO = _f("LIMIAR_ALTO", 0.50)
    LIMIAR_MEDIO = _f("LIMIAR_MEDIO", 0.30)

    # ----- MongoDB (local em dev; MongoDB Atlas em produção) ------------------
    # MONGO_MOCK=true troca o MongoDB real por um banco EM MEMÓRIA (mongomock) —
    # não sobe servidor nenhum, não precisa de Docker nem de rede. Os dados somem
    # ao reiniciar o processo; serve só para testar o painel de ponta a ponta em
    # uma máquina sem Docker/serviços em background (ex.: laboratório da faculdade).
    MONGO_MOCK = os.getenv("MONGO_MOCK", "false").strip().lower() in ("1", "true", "yes")
    MONGO_URI = os.getenv("MONGO_URI", "mongodb://localhost:27017")
    MONGO_DB = os.getenv("MONGO_DB", "gestao_academia")
    MONGO_TIMEOUT_MS = int(os.getenv("MONGO_TIMEOUT_MS", "8000"))
    MONGO_BATCH = int(os.getenv("MONGO_BATCH", "5000"))
    MONGO_TLS = os.getenv("MONGO_TLS", "auto").strip().lower()

    COL_PARCELAS = os.getenv("COL_PARCELAS", "parcelas")           # transacional, anonimizado (ML)
    COL_ALUNOS = os.getenv("COL_ALUNOS", "alunos")                 # agregado por aluno, anonimizado (ML)
    COL_PREDICOES = os.getenv("COL_PREDICOES", "predicoes")        # saída do modelo
    COL_EXECUCOES = os.getenv("COL_EXECUCOES", "execucoes")        # log de ingestão/pontuação/treino
    COL_CADASTRO = os.getenv("COL_CADASTRO", "cadastro_alunos")    # operacional, COM dados pessoais
    COL_USUARIOS = os.getenv("COL_USUARIOS", "usuarios")           # login do painel
    COL_CONFIG = os.getenv("COL_CONFIG", "configuracoes")          # parâmetros editáveis em runtime

    # ----- Redis (cache de baixa latência) ------------------------------------
    REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")
    REDIS_TTL = int(os.getenv("REDIS_TTL", "2592000"))   # 30 dias
    REDIS_PREFIX = os.getenv("REDIS_PREFIX", "risco:")

    # ----- API interna (ver routes/api_routes.py) ------------------------------
    API_TOKEN = os.getenv("API_TOKEN", "")               # vazio = sem autenticação (apenas dev)
    ALTO_RISCO_LIMIT = int(os.getenv("ALTO_RISCO_LIMIT", "100"))


config = Config()
