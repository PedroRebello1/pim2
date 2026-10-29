# Solução proposta: Motor de Cobrança Inteligente

**PIM II · Ciclo de vida do aluno · Academia Equilíbrio e Movimento**

> Primeiro módulo da plataforma proposta em [ESTUDO_DADOS_E_OPORTUNIDADES.md](../ESTUDO_DADOS_E_OPORTUNIDADES.md).
> O protótipo funciona e foi avaliado com os dados reais de cobrança (15/08 a 15/10/2026).
> Apresentação: [slides/apresentacao.pdf](slides/apresentacao.pdf). Para apresentar no navegador: [slides/apresentacao.html](slides/apresentacao.html) (setas para navegar, F para tela cheia).

---

## 1. O problema

A "inadimplência" da academia é, na prática, **falha de cobrança no cartão recorrente**. O sistema cobra em lote diário (12h) e re-tenta as recusas sem levar em conta o motivo.

| Indicador (15/08 a 15/10/2026) | Valor |
|---|---|
| Tentativas de cobrança / aprovação por tentativa | 4.347 / 29,8% |
| Cartão-mês com recusa "irreversível" que nunca aprovou | **272** |
| Re-tentativas inúteis depois dessas recusas | **1.499** |
| Dias de insistência até alguém agir (mediana) | **7** |
| Mensalidades nessa situação | **R$ 48,7 mil** |

Re-tentar demais custa caro: as bandeiras limitam re-tentativas e a adquirente prevê tarifa para o excesso. Enquanto isso, quem precisa trocar o cartão só é procurado semanas depois.

## 2. A solução

A cada recusa, o motor estima **P(aprovação) da próxima tentativa** e escolhe uma de três ações:

| Ação | Quando | Por quê |
|---|---|---|
| **Re-tentar em dd/mm** | a chance compensa | o dia é escolhido pelo modelo: o primeiro dia que alcança 90% da melhor chance nos próximos 10 dias |
| **Pedir novo cartão ou PIX** | depois de um código que praticamente nunca se recupera | o aluno é avisado no 1º dia, não depois de semanas de recusas |
| **Parar e contatar** | a partir do teto de falhas seguidas | a chance cai abaixo de 1%, e assim se respeitam os limites das bandeiras |

Fluxo diário: **export → histórico do cartão → modelo → política → fila de ação com motivo**. O desfecho de cada ação deve ser registrado para re-treinar o modelo.

## 3. Como funciona

**Unidade de decisão:** a re-tentativa, ou seja, uma tentativa logo depois de uma recusa do mesmo cartão. A primeira cobrança do mês sempre acontece.

**Atributos** (todos conhecidos *antes* da tentativa, sem vazamento):

| Atributo | Descrição |
|---|---|
| `ult_cod` | código da última recusa (51, 62, Pac014…) |
| `seq_falhas` | recusas seguidas até agora |
| `n_tent_mes` | tentativas do cartão no mês |
| `dias_desde_ult` | dias desde a última tentativa |
| `faixa_dia` | faixa do dia do mês (efeito "dia do pagamento") |
| `bandeira`, `bin_taxa` | bandeira e taxa histórica de aprovação do emissor (BIN), suavizada e calculada só no treino |
| `duas_parcelas`, `log_valor` | cobrança de 2 parcelas de uma vez; valor |

**Modelo:** regressão logística com regularização L2, ajustada por Newton/IRLS e implementada em numpy (o ambiente não tem scikit-learn). O λ é escolhido por validação temporal dentro do treino.

**Regras aprendidas no treino** (nunca no teste):
- **Códigos irreversíveis** (re-tentativa aprova ≤ 1%, com pelo menos 15 casos): `05, 5c, 78, 79, Fa, Pac003, Pac014`
- **Teto de falhas:** 5 recusas seguidas. Entre os códigos recuperáveis, a partir daí a aprovação fica abaixo de 1%.
- **Limiar do modelo:** P ≥ 0,029, que mantém 95% das aprovações do treino.

**Validação:** temporal. Treino de 15/08 a 30/09 (2.063 re-tentativas, 65 aprovações). Teste de 01/10 a 15/10 (690 re-tentativas, 31 aprovações), um período que o modelo nunca viu.

## 4. Resultados (teste de outubro)

**Modelo**

| Métrica | Modelo | Referência |
|---|---|---|
| AUC | **0,922** | 0,816 (só o código da recusa) |
| Brier | **0,034** | 0,043 (taxa constante) |
| Calibração (quintil de maior risco) | previu 20%, ocorreram 21% | |

**Políticas (replay):** cada re-tentativa real é mantida ou evitada, e contamos as aprovações que continuariam acontecendo.

| Política | Tentativas | Aprovações mantidas | Aprovações / 100 tentativas |
|---|---|---|---|
| Atual: re-tenta tudo | 690 (100%) | 31 (100%) | 4,5 |
| Regra 1: não re-tentar códigos irreversíveis | 319 (46%) | 30 (97%) | 9,4 |
| Modelo: P(aprovação) ≥ limiar | 202 (29%) | 29 (94%) | 14,4 |
| Regra 2: regra 1 + teto de 5 falhas | 112 (16%) | 28 (90%) | 25,0 |

**Fila de ação de 15/10/2026:** 143 cartões e R$ 24,2 mil pendentes.
- 76 cartões, **R$ 12,3 mil:** pedir novo cartão ou PIX hoje
- 45 cartões, **R$ 7,8 mil:** parar re-tentativas e contatar
- 22 cartões, **R$ 4,1 mil:** re-tentar na data indicada pelo modelo

## 5. Como rodar

```bash
cd solucao_pim2/motor_cobranca
python rodar.py <pasta_com_os_exports> <pasta_privada_fora_do_repo>
cd ../slides
python gerar_slides.py          # regera apresentacao.html e apresentacao.pdf com os números novos
```

- **Novos dados:** coloque os novos exports (.xlsx) na pasta e rode de novo. O carregador reconhece cada arquivo pelo cabeçalho, junta os arquivos do mesmo tipo e remove duplicatas. O teste passa a ser sempre o último mês dos dados.
- **Privacidade:** `resultados/` recebe só agregados e IDs pseudonimizados. A fila com o nome do titular, para uso interno da recepção, vai para `<pasta_privada>/fila_do_dia.csv`, **fora do repositório**.
- Dependências: Python 3, pandas, numpy, openpyxl. Para gerar o PDF, o Microsoft Edge.

## 6. Limitações

- Só 2 meses de tentativas: o teste tem 31 aprovações, e as métricas precisam ser confirmadas com mais meses.
- O replay mede com rigor o "parar de insistir". O ganho de "re-tentar no dia certo" não é observável nos dados históricos e precisa de um **piloto A/B** com a academia.
- Os códigos `Pac*` vêm do sistema de gestão. O significado precisa ser confirmado com o suporte.
- A fila identifica o cartão (titular + cartão mascarado). O vínculo com a matrícula do aluno é heurístico (ver o estudo).

## 7. Próximos passos

1. Re-treinar com mais meses de transações, assim que chegarem os novos exports.
2. **Piloto A/B:** metade dos cartões com a política nova, metade com a atual. Medir R$ recuperado, tentativas evitadas e dias até regularizar.
3. Painel e registro de desfechos para a recepção.
4. PIM III: módulo de retenção (análise de sobrevivência) sobre a mesma base aluno × mês.

## Estrutura

```
solucao_pim2/
├── README.md                ← este documento
├── motor_cobranca/
│   ├── dados.py             ← lê os exports (detecta o tipo) e monta os atributos por tentativa
│   ├── modelo.py            ← regressão logística L2 (numpy) + AUC, Brier, ROC, calibração
│   ├── politicas.py         ← regras, avaliação por replay, fila do dia
│   └── rodar.py             ← pipeline completo → resultados/
├── resultados/              ← métricas, políticas, coeficientes, ROC, fila (agregada/pseudonimizada)
└── slides/
    ├── gerar_slides.py      ← monta o deck a partir de resultados/
    ├── apresentacao.html    ← para apresentar no navegador
    └── apresentacao.pdf     ← 12 slides 16:9
```
