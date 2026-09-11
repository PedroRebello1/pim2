# Painel de Gestão de Academias — CEUB (PIM2)

Continuação do **PIM1** (que entregou uma API de predição de churn/inadimplência
para academias). O PIM2 amplia o escopo: em vez de só servir o modelo, o
sistema agora é um **serviço web** — um painel administrativo focado em dados
para a gestão geral de uma academia — e a API do PIM1 passa a ser **uma
funcionalidade interna** dele, não mais uma aplicação à parte.

> Este é um esqueleto de PIM2: **funcional de ponta a ponta**, mas pensado
> para evoluir ao longo do semestre. A partir do PIM3 a base fica fixa — até
> lá, estrutura, nomes de coleções e telas podem mudar.

## O que dá para fazer com ele hoje

1. Gerar (ou usar) um export de parcelas da academia e **ingerir** pelo painel.
2. Ver o **cadastro de alunos** (busca, filtro por situação, ficha individual
   com histórico de parcelas e de risco).
3. Ver o **financeiro**: parcelas pagas/canceladas/em aberto, inadimplência
   por plano, formas de pagamento, lista de parcelas atrasadas.
4. **Treinar** o modelo de churn (compara 5 algoritmos, guarda o melhor) direto
   pelo painel, sem precisar de arquivo — ele lê a base já ingerida no Mongo.
5. **Pontuar** a base e ver a lista de alunos em **alto risco**, com nome e
   telefone (cruzando a trilha anonimizada com o cadastro).
6. **Simular** uma predição individual preenchendo os atributos manualmente.
7. Acompanhar o **histórico de execuções** (ingestão/pontuação/treino) — a
   mesma ideia de observabilidade do PIM1, agora cobrindo as três rotinas.
8. Ajustar os **limiares de risco** (Alto/Médio) em runtime, sem redeploy.
9. Consumir os mesmos dados por **API** (`/api/...`), para outra ferramenta
   ou automação — é a API do PIM1, agora um módulo interno.

## O que mudou em relação ao PIM1 (e por quê)

| PIM1 | PIM2 | Motivo |
|---|---|---|
| App Flask só com a API de churn | Painel web completo; a API vira um blueprint interno (`routes/api_routes.py`) | O curso pede um painel de gestão, não só um modelo servido |
| `id_aluno` via `pd.factorize` | `id_aluno` = hash estável da matrícula (`churn_core._id_estavel`) | No PIM1 o id do mesmo aluno podia mudar entre execuções (dependia da ordem das linhas). Isso quebraria qualquer tela que precisasse de histórico por aluno — corrigido aqui. |
| Só a trilha anonimizada (`parcelas`, `alunos`) | + `cadastro_alunos` (COM nome/telefone), separada da trilha de ML | Gestão geral precisa identificar o aluno; o modelo continua nunca vendo PII. Ver *Privacidade* abaixo. |
| 3 scripts CLI independentes e duplicados (`ingest_parcelas.py`, `batch_scoring.py`, `train_model.py`) | 1 orquestrador (`pipeline.py` + `treino.py`) usado tanto pela web quanto pelos scripts CLI que sobraram | Elimina a duplicação de lógica; a rotina roda igual pelo botão do painel ou pela linha de comando |
| `model_runs` (só rodadas de pontuação) | `execucoes` (ingestão + pontuação + treino) | Observabilidade unificada agora que há três rotinas, não uma |
| Sem autenticação de painel | Login por sessão (`auth.py`), 1 usuário admin seed | Painel administrativo precisa de login |
| Limiares só via `.env` | Limiares editáveis em runtime (coleção `configuracoes`, tela Admin) | Ajustar sem precisar reiniciar o serviço |

## Arquitetura em uma frase

`export mensal (.xls/.xlsx)` → upload no painel → **ingestão** (limpeza →
cadastro operacional + anonimização LGPD → atributos) → **MongoDB** (coleções
`cadastro_alunos`, `parcelas`, `alunos`) → **pontuação** do modelo →
`predicoes` → **Redis** (cache de risco por aluno) → consumo pelas telas do
painel e pela API interna (`/api/...`).

```
pim2_gestao_academia/
├── app.py                # fábrica da aplicação Flask
├── config.py              # configuração via .env
├── extensions.py          # conexões compartilhadas (Mongo, Redis, modelo)
├── auth.py / seed.py      # login por sessão + usuário admin inicial
├── churn_core.py          # limpeza, LGPD, features (evoluído do PIM1)
├── model_service.py       # carrega o artefato do modelo e faz inferência
├── treino.py               # motor de treino (5 algoritmos, escolhe o melhor)
├── pipeline.py             # orquestra ingestão / pontuação / treino
├── storage.py              # acesso a MongoDB + Redis, todas as agregações
├── routes/                 # blueprints: auth, dashboard, alunos, financeiro,
│                            #   churn, ingestao, admin, api
├── templates/ + static/    # painel server-rendered (Jinja2 + CSS próprio)
├── scripts/                # CLIs equivalentes ao PIM1 (dados de exemplo,
│                            #   treino a partir de arquivo, checagem do banco)
├── data/raw/                # cópia imutável dos exports recebidos (≈ bucket)
├── data/uploads/            # uploads temporários do painel
└── modelos/                 # artefato do modelo (joblib) + metadados (json)
```

### Coleções MongoDB

| Coleção | Conteúdo | Tem PII? |
|---|---|---|
| `cadastro_alunos` | Registro operacional (nome, telefone, plano, situação) — módulo de gestão | **Sim, por design** |
| `parcelas` | Trilha transacional anonimizada (entrada do modelo) | Não |
| `alunos` | Base agregada por aluno, anonimizada (features do modelo) | Não |
| `predicoes` | Saída do modelo (probabilidade, faixa de risco) por competência | Não |
| `execucoes` | Log de ingestão/pontuação/treino (observabilidade) | Não |
| `usuarios` | Login do painel (usuário + hash da senha) | Login, não do aluno |
| `configuracoes` | Parâmetros editáveis em runtime (limiares de risco) | Não |

## Como rodar

### Opção A — Docker Compose (recomendado, sem instalar nada manualmente)

```bash
docker compose up --build
```

Sobe MongoDB, Redis e o painel juntos. Acesse **http://localhost:8000** —
login inicial `admin` / `admin123` (definidos em `docker-compose.yml`,
troque em produção).

### Opção B — local, com MongoDB "de verdade" (sem Docker)

Serve se você tem como instalar/rodar um `mongod` (local, portátil, ou um
cluster grátis no MongoDB Atlas). Redis é sempre opcional — sem ele, a
aplicação sobe normal e só perde o cache de leitura (ver *Modo degradado*
abaixo).

```bash
pip install -r requirements.txt
cp .env.example .env          # ajuste MONGO_URI se precisar (Atlas, etc.)

# 1) gera um export sintético para testar (não são dados reais)
python scripts/gerar_dados_exemplo.py --alunos 400 --saida exemplo_export.xlsx

# 2) sobe o painel
python app.py                 # http://localhost:8000, login admin/admin123
```

### Opção C — máquina institucional, sem Docker e sem poder instalar serviço nenhum

Não precisa de MongoDB real: `MONGO_MOCK=true` troca o banco por um MongoDB
**em memória** (biblioteca `mongomock`) — roda dentro do próprio processo
Python, não abre porta nenhuma, não precisa de rede nem de permissão de
administrador. É a forma mais simples de testar o painel ponta a ponta num
laboratório travado.

```bash
pip install -r requirements.txt -r requirements-dev.txt
cp .env.example .env
# no .env, ajuste: MONGO_MOCK=true

python scripts/gerar_dados_exemplo.py --alunos 400 --saida exemplo_export.xlsx
python app.py                 # http://localhost:8000, login admin/admin123
```

Único cuidado: os dados **não persistem** entre execuções (somem ao encerrar
o `python app.py`) — sirva só para teste/demonstração, não para "deixar
rodando". Redis nem entra em cena aqui: com ou sem `MONGO_MOCK`, se não
houver um Redis real disponível a aplicação simplesmente desliga o cache
sozinha (ver abaixo).

### Modo degradado (sem MongoDB nem Redis)

Sem nenhum banco disponível (nem real, nem `MONGO_MOCK`), o painel ainda
sobe — login funciona pelas credenciais do `.env` (`ADMIN_USER`/
`ADMIN_PASSWORD`), mas dashboard, alunos, financeiro e churn ficam vazios até
o Mongo aparecer. É a mesma filosofia de degradação graciosa do PIM1: dá
para navegar e ver as telas, só não valida a lógica de dados de verdade —
para isso, use a Opção B ou C.

### Primeiro uso pelo painel

1. Entre em **Ingestão mensal**, envie o `.xls`/`.xlsx` gerado (ou um export
   real) e informe a competência.
2. Entre em **Admin / Modelo** e clique em **"Retreinar com a base do Mongo"**
   (ele já lê o que acabou de ser ingerido — não precisa reenviar arquivo).
3. Volte em Admin e clique em **"Pontuar novamente"** para gerar as predições
   da competência (a ingestão já dispara isso automaticamente quando já há
   um modelo treinado).
4. Veja o resultado no **Dashboard**, em **Alunos** e em **Churn → Alto risco**.

### API interna (compatível com o `app.py` do PIM1)

```
GET  /api/health
POST /api/predict                       { "atraso_medio_dias": 12.5, "pct_em_dia": 0.2, ... }
GET  /api/aluno/<id_aluno>/risco
GET  /api/alto-risco?data_referencia=2026-06&limite=100
POST /api/admin/reload-model
POST /api/admin/ingestao                multipart/form-data: arquivo=<export.xlsx>
```

Protegida por `Authorization: Bearer <API_TOKEN>` quando `API_TOKEN` está
definido no `.env` (vazio = sem exigência, só para dev).

## Privacidade (LGPD) — o que mudou de propósito

O PIM1 tinha uma regra simples: nenhuma coleção guarda PII. O PIM2 é um
sistema de **gestão geral**, que por natureza precisa identificar o aluno
(a recepção precisa saber quem é "Maria", não só `ALUNO_82AF8BCE`). A
solução adotada foi **segregar**, não abandonar o princípio:

- `cadastro_alunos` é a **única** coleção com dados pessoais, e existe
  exatamente para isso — é o equivalente interno ao "sistema de origem"
  que o documento de arquitetura do PIM1 citava como o único lugar onde a
  reidentificação seria possível. Continua valendo.
- `parcelas`, `alunos` e `predicoes` — a trilha inteira que alimenta o
  modelo — seguem **sem PII**, exatamente como no PIM1. O `id_aluno` é o
  único elo entre as duas trilhas, e é um hash, não reversível sem o
  cadastro.
- `scripts/verificar_atlas.py` continua conferindo isso automaticamente.

Isso é uma decisão consciente de escopo do PIM2 (painel de gestão real
precisa de PII em algum lugar) e deve ser revisitada nos próximos PIMs com
controle de acesso por coleção/perfil — hoje qualquer usuário do painel
enxerga o cadastro.

## Limitações conhecidas / próximos passos (PIM3+)

- **Um único perfil de usuário.** Não há ainda controle de acesso por papel
  (ex.: recepção vs. gestor vs. cientista de dados) — todo usuário logado
  vê tudo, inclusive o cadastro com PII.
- **Camada raw em disco local** (`data/raw/`). Em produção seria um bucket
  (S3/MinIO), como o documento de arquitetura do PIM1 já previa.
- **Sem fila/orquestrador.** Ingestão e treino rodam de forma síncrona,
  bloqueando a requisição HTTP — para bases muito maiores que a atual
  (~71 mil parcelas) valeria mover para um job assíncrono.
- **Sem testes automatizados** no repositório entregue (o projeto foi
  validado manualmente ponta a ponta — ingestão → treino → pontuação →
  todas as telas — antes da entrega, mas isso não substitui uma suíte de
  testes).
- **Cadastro sem tela de edição.** Hoje `cadastro_alunos` só é populado pela
  ingestão; um CRUD manual (cadastrar aluno avulso, editar telefone etc.)
  fica para uma próxima etapa.
- Telas de **turmas/instrutores/horários** não foram feitas — a coluna
  `Turma` já existe na trilha de dados, mas o módulo ainda não existe.

## Créditos de dados

A lógica de limpeza, anonimização e engenharia de atributos vem do notebook
`Modelo_Churn_CEUB.ipynb` do PIM1 (comparação de 5 algoritmos, vencedor
XGBoost com ROC-AUC ≈ 0,849 na base real de ~71 mil parcelas / ~4,4 mil
alunos). O `scripts/gerar_dados_exemplo.py` gera dados **sintéticos** para
quem não tem o export real em mãos.
