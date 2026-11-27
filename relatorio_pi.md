---
# ==========================================================================
# PARTE 1 — DADOS DA CAPA E DA FOLHA DE ROSTO (saem daqui, automaticamente)
#     O título aparece na capa E na folha de rosto: é assim na ABNT.
# ==========================================================================
title: "Ciclo de vida do aluno"
subtitle: "motor de cobrança inteligente para recuperar pagamentos recorrentes de uma academia"
autores:
  - "Pedro Rebello"
  - "Guilherme Mendes"
  - "Eduardo Barros"
  - "Gabriel Francisco"
orientador: "Prof. MSc. Weslley Rodrigues"
rotulo-orientador: "Orientador"
instituicao: "Centro Universitário de Brasília – CEUB"
curso: "Curso de Ciência de Dados e Machine Learning"
cidade: "Brasília"
ano: "2026"
natureza: >-
  Relatório final apresentado à disciplina Projeto Integrador II do
  Curso de Ciência de Dados e Machine Learning do Centro Universitário
  de Brasília, como requisito parcial para aprovação.
# Folha de aprovação (opcional): descomente para incluir a banca examinadora.
# data-aprovacao: "2 de dezembro de 2026"
# banca:
#   - "Prof. MSc. Weslley Rodrigues (orientador)"
#   - "Prof. Nome Sobrenome, Me."
# A capa usa o logo do CEUB. Para uma capa só com texto: logo: false

# ==========================================================================
# 🔒 PARTE 2 — PADRÃO ABNT DO CURSO (NÃO ALTERE)
#     Margens, fontes, títulos, paginação e citações vêm de relatorio/abnt/.
# ==========================================================================
bibliography: refs.bib
---

<!-- ======================================================================
     COMO ESTE ARQUIVO VIRA O RELATÓRIO
     python relatorio/gerar_relatorio.py  (ou Ctrl+Shift+B no VS Code)
       -> relatorio_pi.docx e relatorio_pi.pdf, no padrão ABNT.
     {{nome}}        número calculado em relatorio/valores.py (nunca digite resultados à mão)
     ![...](#fig-x)  gráfico feito em relatorio/figuras.py
     : ... {#tbl-x}  tabela feita em relatorio/tabelas.py (ou escrita logo abaixo, com | ... |)
     [@chave]        citação do refs.bib; @fig-x / @tbl-x / @sec-x / @eq-x: referências cruzadas
     ====================================================================== -->

<!-- ======================================================================
     ELEMENTOS PRÉ-TEXTUAIS
     {.pre} = título centralizado, sem número, fora do sumário
     ====================================================================== -->

# Agradecimentos {.pre}

À Academia Equilíbrio e Movimento, que abriu seus dados e sua rotina de cobrança para este projeto, e à equipe docente do curso de Ciência de Dados e Machine Learning do CEUB, pela orientação ao longo do Projeto Integrador.

# Resumo {.pre}

<!-- Parágrafo único, de 150 a 500 palavras (NBR 6028). Palavras-chave separadas por ponto e vírgula. -->

Este trabalho, desenvolvido no Projeto Integrador II em parceria com a Academia Equilíbrio e Movimento, de Brasília, estuda o ciclo de vida do aluno a partir de exports reais do sistema de gestão da academia: parcelas, acessos pela catraca e tentativas de cobrança no cartão. O estudo dos dados mostrou três fatos que mudaram o rumo do projeto: o relatório de parcelas traz apenas quem ainda é cliente; parcela cancelada indica troca de contrato, e não saída, já que {{rotulo_pim1_com_plano}} dos alunos que o rótulo do semestre anterior trataria como evasão continuavam com plano; e a inadimplência da academia é, sobretudo, falha da cobrança recorrente, pois apenas {{aprovacao_geral}} das tentativas no cartão são aprovadas. Propõe-se um Motor de Cobrança Inteligente que, a cada recusa, estima a probabilidade de aprovação da próxima tentativa com uma regressão logística regularizada, implementada em NumPy, e recomenda uma de três ações: re-tentar numa data escolhida pelo modelo, pedir um novo cartão ou PIX, ou parar as re-tentativas e contatar o aluno. Com validação temporal, o modelo obteve AUC de {{auc_teste}} no mês de teste, contra {{auc_ref}} de uma referência baseada só no código da recusa. Na avaliação por *replay*, a política do modelo evitou {{pol_modelo_evitadas}} das re-tentativas e manteve {{pol_modelo_aprov}} das aprovações; uma regra simples, que não re-tenta códigos irreversíveis e para após {{teto}} recusas seguidas, evitou {{pol_regra2_evitadas}} das re-tentativas e manteve {{pol_regra2_aprov}} das aprovações. A fila de ação do último dia dos dados reuniu {{fila_cartoes}} cartões e {{fila_valor}} em mensalidades pendentes. Conclui-se que a maior alavanca é parar de insistir em recusas sem chance e pedir a troca do meio de pagamento já no primeiro dia, e que o ganho de re-tentar no dia certo precisa ser confirmado num piloto controlado com a academia.

**Palavras-chave**: cobrança recorrente; *churn* involuntário; regressão logística; validação temporal; ciência de dados.

# Abstract {.pre}

This work, developed in the Integrative Project II in partnership with the Equilíbrio e Movimento gym in Brasília, studies the student life cycle using real exports from the gym's management system: installments, turnstile entries and card billing attempts. The data study revealed three facts that changed the course of the project: the installments report contains only current customers; a cancelled installment indicates a contract change rather than an exit, since {{rotulo_pim1_com_plano_en}} of the students that the previous semester's label would treat as churners still had an active plan; and the gym's delinquency is mostly a failure of recurring billing, as only {{aprovacao_geral_en}} of card attempts are approved. We propose a Smart Billing Engine that, after each decline, estimates the probability that the next attempt will be approved with a regularized logistic regression implemented in NumPy, and recommends one of three actions: retry on a date chosen by the model, ask for a new card or a PIX payment, or stop retrying and contact the student. Under temporal validation, the model reached an AUC of {{auc_teste_en}} in the test month, against {{auc_ref_en}} for a baseline that uses only the decline code. In a replay evaluation, the model policy avoided {{pol_modelo_evitadas_en}} of the retries while keeping {{pol_modelo_aprov_en}} of the approvals; a simple rule that does not retry irreversible codes and stops after {{teto}} consecutive declines avoided {{pol_regra2_evitadas_en}} of the retries and kept {{pol_regra2_aprov_en}} of the approvals. The action queue for the last day of data gathered {{fila_cartoes}} cards and {{fila_valor_en}} in pending fees. The main lever is to stop insisting on declines with no chance of approval and to ask for a new payment method on the first day; the gain from retrying on the right day must be confirmed in a controlled pilot with the gym.

**Keywords**: recurring billing; involuntary churn; logistic regression; temporal validation; data science.

<!-- Lista de figuras, lista de tabelas e sumário — gerados automaticamente. -->

::: listas
:::

<!-- ======================================================================
     ELEMENTOS TEXTUAIS — a numeração das páginas começa aqui.
     NÃO numere os títulos à mão: "# Introdução" vira "1 INTRODUÇÃO".
     ====================================================================== -->

# Introdução

Academias de ginástica vivem de mensalidades. Como em outros negócios de assinatura, a receita depende menos de vender e mais de manter o aluno pagando mês após mês, e cada saída precisa ser reposta por uma matrícula nova [@fader2007; @ascarza2018]. Este trabalho foi desenvolvido no Projeto Integrador II (PIM II) do curso de Ciência de Dados e Machine Learning do CEUB, em parceria com a Academia Equilíbrio e Movimento, de Brasília, que cedeu exports reais do seu sistema de gestão: parcelas das mensalidades, entradas pela catraca e tentativas de cobrança no cartão de crédito recorrente.

No PIM I, o grupo treinou um classificador de evasão (*churn*) com XGBoost, que alcançou ROC-AUC de 0,849 usando como rótulo o fato de o aluno ter ao menos uma parcela cancelada. Neste semestre, antes de evoluir o modelo, as premissas foram testadas nos dados reais, e três descobertas mudaram o rumo do projeto. Primeiro, o relatório de parcelas só contém quem ainda é cliente na data do export, o que impede medir a evasão com ele. Segundo, parcela cancelada não significa saída: {{rotulo_pim1_com_plano}} dos alunos que aquele rótulo marcaria como evasão continuavam com plano ativo. Terceiro, a inadimplência da academia é, na prática, falha de cobrança no cartão recorrente: só {{aprovacao_geral}} das tentativas são aprovadas.

A partir desse diagnóstico, o projeto foi organizado em torno do ciclo de vida do aluno, sobre uma base comum, o estado de cada aluno em cada mês, e o PIM II ficou com o problema que os dados atuais já permitem resolver: recuperar a cobrança recorrente que falha no cartão, o chamado *churn* involuntário. A retenção dos alunos que decidem sair fica para o PIM III, porque depende de exports com ex-alunos e de um histórico longo de acessos que ainda não estão disponíveis.

## Justificativa

O sistema da academia cobra os cartões em lote, uma vez por dia, e re-tenta as recusas sem levar em conta o motivo informado pelo emissor. Entre {{periodo_ini}} e {{periodo_fim}}, houve {{irrev_cartao_mes}} casos em que um cartão passou o mês inteiro recusado depois de um código que praticamente nunca se recupera. Mesmo assim, esses cartões receberam {{irrev_tentativas}} re-tentativas inúteis, com uma mediana de {{irrev_dias}} dias entre a primeira e a última, e as mensalidades envolvidas somavam {{irrev_valor}} (@sec-cobranca).

Insistir tem custo. As bandeiras limitam o número de re-tentativas de uma transação negada e cobram tarifa pelo excesso; a Visa, por exemplo, aceita até 15 re-tentativas em 30 dias para recusas reversíveis e apenas uma para as irreversíveis [@cielo2024retentativa]. Enquanto o sistema insiste, o aluno que precisa trocar de cartão só é procurado semanas depois, e parte das mensalidades acaba paga por outro caminho: {{recorrentes_outro_meio}} das parcelas de planos recorrentes foram quitadas por PIX, cartão de crédito ou débito. Por fim, é o único problema do ciclo de vida com dados suficientes hoje, valor em reais mensurável e uma ação operacional simples.

## Objetivos

### Objetivo geral

Desenvolver e avaliar, com dados reais da academia, um motor de decisão que recomende, a cada recusa da cobrança recorrente no cartão, a ação com maior chance de recuperar a mensalidade usando menos tentativas.

### Objetivos específicos

- diagnosticar a qualidade e o significado dos campos dos exports do sistema de gestão;
- definir o estado do aluno em cada mês pela cobertura das mensalidades, separando troca de plano, renovação e saída;
- estimar a probabilidade de aprovação de cada re-tentativa com um modelo interpretável e validação temporal;
- comparar políticas de re-tentativa por meio de avaliação por *replay*;
- gerar uma fila diária de ação explicável, sem expor dados pessoais fora da academia.

## Estrutura do trabalho

A @sec-fundamentacao apresenta os conceitos que embasam o trabalho; a @sec-metodologia descreve os dados, as regras de preparação e o motor de cobrança; a @sec-resultados apresenta o diagnóstico dos dados e o desempenho do motor; e a @sec-conclusao traz as considerações finais, as limitações e os próximos passos.

# Fundamentação teórica {#sec-fundamentacao}

## Retenção em negócios de assinatura

Em negócios de assinatura, também chamados de contratuais, a empresa sabe quando o cliente sai, e a receita futura depende da taxa com que os clientes renovam ao longo do tempo [@fader2007]. Por isso a retenção é tratada como uma decisão de gestão: não basta prever quem vai sair; é preciso escolher quem abordar, quando e com qual ação, e medir o efeito dessa ação [@ascarza2018].

Neste trabalho, distingue-se a evasão voluntária, em que o aluno decide encerrar o plano, da evasão involuntária, em que o aluno pretende continuar, mas a cobrança falha por limite insuficiente ou por um cartão vencido, bloqueado ou substituído. As duas pedem ações diferentes: a primeira, uma conversa sobre o serviço; a segunda, a correção do meio de pagamento.

## Cobrança recorrente no cartão

Na cobrança recorrente, a academia envia periodicamente uma transação de valor conhecido à adquirente, que consulta o emissor do cartão. Quando a transação é negada, o emissor devolve um código de retorno com o motivo. A documentação da adquirente classifica esses códigos, por bandeira, em reversíveis, quando uma nova tentativa pode ser aprovada, como o 51 (saldo ou limite insuficiente), e irreversíveis, quando a mesma transação não será aprovada sem que algo mude, como uma conta encerrada ou um cartão inválido [@cielo2024codigos]. As bandeiras mantêm programas que limitam as re-tentativas depois de uma recusa e cobram tarifa pelo excesso [@cielo2024retentativa].

Os seis primeiros dígitos do cartão formam o BIN (*Bank Identification Number*), que identifica o emissor. Como a política de crédito varia entre emissores, a taxa histórica de aprovação por BIN é um atributo útil, embora tenha muitas categorias.

## Regressão logística regularizada

A regressão logística modela a probabilidade de um evento binário, aqui a aprovação de uma tentativa (*y* = 1), como uma função logística de uma combinação linear dos atributos [@hosmer2013]:

$$ *p* = P(*y* = 1 | **x**) = 1 / (1 + e^−*z*^),  com  *z* = β~0~ + β~1~*x*~1~ + … + β~k~*x*~k~ $$ {#eq-logistica}

Cada coeficiente tem leitura direta: exp(β~j~) é a razão de chances, isto é, o fator que multiplica a chance de aprovação quando o atributo *x*~j~ aumenta uma unidade e os demais ficam constantes [@hosmer2013]. Os coeficientes são estimados maximizando a log-verossimilhança. Com poucos eventos positivos e muitas categorias, a estimativa pode ficar instável; a regularização L2 acrescenta uma penalidade ao tamanho dos coeficientes, o que reduz a variância à custa de um pequeno viés [@hastie2009]:

$$ L~λ~(β) = Σ~i~ [*y*~i~ ln *p*~i~ + (1 − *y*~i~) ln(1 − *p*~i~)] − (λ/2) Σ~j≥1~ β~j~^2^ $$ {#eq-verossimilhanca}

O máximo da @eq-verossimilhanca não tem fórmula fechada e é encontrado pelo método de Newton, que, na regressão logística, equivale a mínimos quadrados reponderados iterativamente (IRLS) [@hastie2009]. A cada passo,

$$ β ← β − (**X**^T^**WX** + **Λ**)^−1^ [**X**^T^(**p** − **y**) + **Λ**β] $$ {#eq-newton}

em que **W** é a matriz diagonal com os valores *p*~i~(1 − *p*~i~) e **Λ** é a matriz diagonal com λ para cada coeficiente, exceto o intercepto, que não é penalizado.

## Categorias com muitos níveis

Atributos categóricos com muitos níveis, como o BIN, geram matrizes esparsas e categorias com poucos casos. Uma alternativa é substituir cada categoria pela taxa média do alvo dentro dela, suavizada em direção à taxa geral quando há poucos casos [@micci2001]:

$$ taxa~BIN~ = (*a*~BIN~ + *m* · *t*) / (*n*~BIN~ + *m*) $$ {#eq-bin}

em que *a*~BIN~ e *n*~BIN~ são as aprovações e as tentativas do BIN, *t* é a taxa geral de aprovação e *m* é o peso da suavização. Como o próprio alvo entra no cálculo, a taxa deve ser estimada só com dados de treino; caso contrário, informação do período avaliado vaza para o modelo e infla as métricas [@kaufman2012].

## Avaliação de modelos probabilísticos

A AUC (área sob a curva ROC) mede a capacidade de ordenação do modelo: é a probabilidade de uma aprovação sorteada ao acaso receber uma probabilidade estimada maior que a de uma recusa sorteada ao acaso. Vale 0,5 para um modelo sem informação e 1 para uma separação perfeita, e não depende de um limiar de decisão [@fawcett2006]. Como o motor usa o valor da probabilidade estimada, e não só a ordem, também importa a calibração: entre os casos com probabilidade estimada de 20%, cerca de 20% deveriam ser aprovados [@niculescu2005]. O escore de Brier resume ordenação e calibração no erro quadrático médio entre a probabilidade estimada e o resultado observado [@brier1950]:

$$ BS = (1/*n*) Σ~i~ (*p*~i~ − *y*~i~)^2^ $$ {#eq-brier}

Dados ordenados no tempo exigem validação temporal: o modelo é ajustado com o passado e avaliado num período posterior, como aconteceria em uso. Embaralhar as observações entre treino e teste deixaria o modelo ver o futuro e superestimaria o desempenho [@kaufman2012; @hyndman2021].

## Avaliação de políticas com dados históricos

Uma política de cobrança decide se e quando re-tentar. Avaliá-la com dados históricos é um problema contrafactual, porque só se observa o resultado da ação que foi de fato tomada. A avaliação por *replay* aproveita os registros em que a ação da política coincide com a ação registrada e descarta os demais; o método é não viesado quando as ações registradas foram escolhidas ao acaso [@li2011]. Na cobrança da academia, a política registrada re-tentou todas as recusas, de modo que o *replay* mede com rigor o efeito de deixar de re-tentar, isto é, as tentativas evitadas e as aprovações perdidas, mas não o de re-tentar em outro dia, que nunca foi observado. Para efeitos desse tipo, o padrão é o experimento controlado, em que parte dos casos recebe a política nova e parte continua com a atual [@kohavi2009].

## Viés de sobrevivência e censura

Quando um conjunto de dados mantém apenas os casos que “sobreviveram” até a data da coleta, as conclusões tiradas dele ficam distorcidas, porque os casos que saíram no caminho ficam invisíveis [@brown1992]. Em estudos de tempo até um evento, como o tempo até a saída de um aluno, há ainda a censura: para quem continua ativo, sabe-se apenas que o evento não aconteceu até o fim da observação. A análise de sobrevivência trata a censura de forma explícita [@kaplan1958; @cox1972] e é o caminho previsto para o estudo de retenção do PIM III.

# Metodologia {#sec-metodologia}

## Abordagem

O projeto segue a lógica da *Design Science Research*, em que um artefato é construído para resolver um problema real e avaliado no contexto em que será usado [@hevner2004]. As etapas acompanharam o processo CRISP-DM [@wirth2000]: entendimento do negócio com a academia, entendimento e preparação dos dados, modelagem, avaliação e implantação, aqui na forma de uma fila diária de ação.

## Dados utilizados

A academia exportou do seu sistema de gestão, em 15/10/2026, os relatórios resumidos na @tbl-inventario. Dois outros exports, o cadastro de clientes e uma segunda extração de parcelas, vieram vazios e não puderam ser usados.

: Inventário dos dados exportados pela academia {#tbl-inventario}

::: fonte
Fonte: elaborado pelos autores (2026), com dados da Academia Equilíbrio e Movimento.
:::

Os exports brutos contêm dados pessoais, como nome, CPF, e-mail e telefone, e por isso não fazem parte do repositório do projeto. Os scripts leem os arquivos de uma pasta local e gravam os dados intermediários fora do repositório; o que é versionado são apenas tabelas agregadas (pasta `saidas/`) e resultados do motor com identificadores pseudonimizados (pasta `solucao_pim2/resultados/`). Todos os números, tabelas e gráficos deste relatório são calculados a partir desses arquivos no momento em que o relatório é gerado.

Parcelas e acessos compartilham a matrícula do aluno, mas as tentativas de cobrança trazem apenas o nome do titular e o cartão mascarado. Para ligar uma tentativa a um aluno, o estudo usou uma heurística que casa cada aprovação com uma parcela paga no mesmo dia e com o mesmo valor, usando o nome só para desempatar. Ela liga a maior parte das aprovações, mas raramente os cartões que nunca aprovaram; por isso o motor de cobrança trabalha no nível do cartão e não depende desse vínculo.

## Preparação e regras de negócio

### Significado dos campos

Antes de qualquer modelo, cada campo foi conferido contra o comportamento esperado. Três achados mudaram a forma de usar os dados:

- a data de pagamento não é a data em que o aluno pagou o mês quando a forma de pagamento é cheque ou cartão de crédito parcelado: no cheque, a mediana é de {{cheque_mediana}} dias antes do vencimento, porque os cheques pré-datados são recebidos na venda;
- a indicação de recorrência do contrato não é confiável: em {{flag_recorrencia_nao}} dos contratos de planos com “recorrência” no nome, ela aparece como “Não”;
- as {{n_contrato0}} linhas do contrato número zero são vendas avulsas, diárias e acertos, e foram separadas das mensalidades.

Além disso, nenhuma das {{parc_cancelado}} parcelas canceladas tem data de pagamento, e elas se concentram no fim dos contratos: “cancelada” significa que o restante do contrato foi anulado, seja por troca de plano, renovação antecipada, trancamento ou saída.

### Estado do aluno pela cobertura

Quando o aluno troca de plano ou renova antes do fim de uma promoção, o sistema cancela as parcelas restantes do contrato antigo e abre um contrato novo. Olhando só o contrato, parece uma saída; olhando o aluno, ele nunca saiu. Por isso, o estado do aluno passou a ser medido pela cobertura mensal, com três regras:

1. um mês está coberto quando há, em qualquer contrato do aluno, uma parcela de mensalidade não cancelada com vencimento naquele mês; pagamentos à vista de vários meses são distribuídos pelos meses que cobrem;
2. há saída quando o aluno fica pelo menos dois meses seguidos sem cobertura, valor provisório a calibrar com a academia;
3. meses recentes, sem tempo suficiente de observação, não recebem rótulo (censura à direita).

A @fig-cobertura ilustra a diferença: nos dois casos o contrato A termina com parcelas canceladas, mas só no segundo o aluno fica sem cobertura.

![Mesmo cancelamento, desfechos diferentes: a cobertura separa troca de plano e saída](#fig-cobertura)

::: fonte
Fonte: elaborado pelos autores (2026).
:::

Cada contrato foi então classificado pelo que aconteceu depois do seu último mês coberto: troca de plano ou renovação, cobertura por outro contrato do aluno, saída ou contrato ainda em curso. O resultado está na @sec-resultados.

## Motor de Cobrança Inteligente

### Unidade de decisão e atributos

A primeira cobrança de cada mês sempre acontece. A decisão do motor está na re-tentativa, isto é, numa tentativa que vem logo depois de uma recusa do mesmo cartão. Para cada re-tentativa, o motor monta os atributos da @tbl-atributos, todos conhecidos antes da tentativa, para não haver vazamento de informação [@kaufman2012].

: Atributos de cada re-tentativa usados pelo modelo {#tbl-atributos larguras=3.4,9.6}

| Atributo | Descrição |
|---|---|
| `ult_cod` | código da última recusa (51, 62, Pac014 etc.) |
| `seq_falhas` | recusas seguidas do cartão até o momento |
| `n_tent_mes` | número da tentativa do cartão no mês |
| `dias_desde_ult` | dias desde a tentativa anterior |
| `ja_aprovou` | se o cartão já teve alguma aprovação no período |
| `faixa_dia` | faixa do dia do mês (efeito “dia do pagamento”) |
| `bandeira` | bandeira do cartão, pelo primeiro dígito |
| `bin_taxa` | taxa de aprovação do emissor (BIN), suavizada e calculada só no treino |
| `duas_parcelas` | se a cobrança junta duas parcelas |
| `log_valor` | logaritmo do valor cobrado |

::: fonte
Fonte: elaborado pelos autores (2026).
:::

### Modelo

O modelo é uma regressão logística com regularização L2, conforme a @eq-logistica e a @eq-verossimilhanca, ajustada pelo método de Newton da @eq-newton e implementada em NumPy [@harris2020], o que mantém o código curto, inspecionável e sem dependências além de pandas e NumPy. Os atributos numéricos são padronizados com a média e o desvio-padrão do treino; as categorias com menos de 25 casos no treino são agrupadas em “outros”; e a taxa do BIN segue a @eq-bin, com peso *m* = 20, calculada com todas as tentativas do período de treino. A intensidade da regularização (λ) é escolhida por validação temporal dentro do próprio treino: as duas últimas semanas servem de validação, e são testados os valores {{grade_l2}}.

### Regras de decisão aprendidas no treino

Além do modelo, o motor aprende três regras, sempre com os dados de treino:

- **códigos irreversíveis**: códigos após os quais a re-tentativa aprova no máximo 1%, com pelo menos 15 casos;
- **teto de falhas**: o menor número de recusas seguidas a partir do qual, entre os códigos recuperáveis, a aprovação fica abaixo de 1%, com pelo menos 30 casos;
- **limiar do modelo**: a menor probabilidade estimada que ainda preserva 95% das aprovações do treino.

### Validação e avaliação

A validação é temporal: o teste é sempre o último mês dos dados, que o modelo nunca viu. Com os exports atuais, o treino vai de {{treino_ini}} a {{treino_fim}} ({{retent_treino}} re-tentativas e {{aprov_treino}} aprovações) e o teste, de {{teste_ini}} a {{teste_fim}} ({{retent_teste}} re-tentativas e {{aprov_teste}} aprovações). O modelo é comparado com duas referências: uma taxa constante, igual à aprovação média do treino, e a taxa histórica de aprovação por código da última recusa, que representa uma regra simples, sem aprendizado de máquina.

As políticas de re-tentativa são avaliadas por *replay* no período de teste [@li2011]: cada re-tentativa real é mantida ou evitada pela política, e contam-se as tentativas que seriam feitas e as aprovações que continuariam acontecendo.

### Fila diária de ação

No último dia dos dados, o motor é reajustado com todo o histórico e aplicado aos cartões com cobrança pendente, ou seja, com recusa nos últimos sete dias e nenhuma aprovação no mês. Para cada cartão, estima-se a probabilidade de aprovação em cada um dos próximos dez dias, e a data sugerida é o primeiro dia que alcança 90% da melhor chance do período. A ação segue a ordem da @fig-fluxo: pedir novo cartão ou PIX se a última recusa tem código irreversível; parar as re-tentativas e contatar o aluno se o cartão atingiu o teto de falhas; re-tentar na data sugerida se a probabilidade supera o limiar; e contato nos demais casos. Cada recomendação sai com o motivo, em linguagem simples, para a recepção.

![Fluxo diário do Motor de Cobrança Inteligente](#fig-fluxo)

::: fonte
Fonte: elaborado pelos autores (2026).
:::

## Ferramentas

As análises foram feitas em Python, com pandas [@mckinney2010] e NumPy [@harris2020] para os dados e o modelo, openpyxl para a leitura dos exports e Matplotlib [@hunter2007] para os gráficos deste relatório. O código foi escrito no Visual Studio Code e versionado no GitHub. O relatório é gerado por um script em Python que lê o texto, recalcula números, tabelas e gráficos a partir dos arquivos do repositório e monta o documento em Word, no padrão ABNT do curso, convertido para PDF pelo LibreOffice. A cada envio ao GitHub, o GitHub Actions repete o processo numa máquina limpa, o que comprova a reprodutibilidade.

## Aspectos éticos

O projeto segue os princípios da finalidade e da necessidade da Lei Geral de Proteção de Dados Pessoais [@brasil2018, art. 6º]: os dados são usados só para o propósito combinado com a academia, apenas os campos necessários são lidos, e os identificadores dos resultados são pseudonimizados, lembrando que pseudonimizar não equivale a anonimizar. A fila com o nome do titular, de uso interno da recepção, é gravada numa pasta privada, fora do repositório. O motor não toma decisões automáticas sobre alunos: ele recomenda ações, e o contato é sempre feito por uma pessoa da equipe.

# Resultados {#sec-resultados}

## Diagnóstico dos dados

### O export de parcelas só contém sobreviventes

Se o export de parcelas trouxesse todos os alunos, o número de alunos com plano oscilaria com entradas e saídas. Em vez disso, ele cresce de forma contínua, de {{alunos_mes_ini}} em {{alunos_mes_ini_rotulo}} para {{alunos_mes_fim}} em {{alunos_mes_fim_rotulo}} (@fig-alunos-por-mes). É o desenho esperado quando o relatório traz só quem é cliente hoje, olhando para trás: dos {{n_alunos_cobertura}} alunos com mensalidade no export, apenas {{alunos_saida_antes}} têm o último mês coberto antes de setembro de 2026, e {{catraca_fora_inativos}} dos {{catraca_fora}} alunos que passaram na catraca, mas não aparecem nas parcelas, estavam inativos.

![Alunos com plano por mês, segundo o export de parcelas](#fig-alunos-por-mes)

::: fonte
Fonte: elaborado pelos autores (2026), com dados da Academia Equilíbrio e Movimento.
:::

Esse viés de sobrevivência [@brown1992] impede usar o arquivo para medir a evasão, a inadimplência histórica ou o cancelamento por plano. Ainda assim, a numeração dos contratos permite dimensionar o problema. Como o número do contrato é sequencial no tempo, a faixa de números de cada mês mostra quantos contratos foram emitidos, e o export mostra quantos deles pertencem a quem ainda é cliente (@fig-contratos-atuais). Dos contratos emitidos de {{coorte_recente_periodo}}, {{coorte_recente_min}} a {{coorte_recente_max}} ainda são de clientes atuais; entre os emitidos há 12 meses ou mais, a proporção cai para {{coorte_antiga_min}} a {{coorte_antiga_max}}, com exceção de dezembro de 2024, mês da promoção de Natal, com {{coorte_dez24}}. A estimativa é aproximada, mas mostra que a evasão real é bem maior do que o export sugere.

![Proporção dos contratos emitidos em cada mês cujo titular ainda é cliente](#fig-contratos-atuais)

::: fonte
Fonte: elaborado pelos autores (2026), com dados da Academia Equilíbrio e Movimento.
:::

### Parcela cancelada não é saída

A regra de cobertura classificou os {{n_contratos}} contratos de plano conforme o que aconteceu depois do último mês coberto (@tbl-status-contratos). Os {{n_troca}} contratos com parcelas canceladas em que o aluno seguiu coberto por um contrato novo são trocas de plano ou renovações antecipadas, e não saídas; há ainda {{n_renovacao}} renovações sem nenhuma parcela cancelada.

: Situação dos contratos de plano pela regra de cobertura {#tbl-status-contratos}

::: fonte
Fonte: elaborado pelos autores (2026), com dados da Academia Equilíbrio e Movimento.
:::

O rótulo usado no PIM I, “ter ao menos uma parcela cancelada”, marcaria {{rotulo_pim1_n}} dos {{n_alunos_cobertura}} alunos ({{rotulo_pim1_pct}}) como evasão, mas {{rotulo_pim1_com_plano}} deles ainda tinham plano em setembro de 2026. Na catraca, {{catraca_ativo_pos}} dos alunos marcados passaram no último mês com situação “Ativo”, contra {{catraca_ativo_neg}} entre os demais. Parcela cancelada é, portanto, um marcador de mudança de contrato, e o rótulo precisava ser substituído.

### A inadimplência é falha de cobrança {#sec-cobranca}

As parcelas em aberto são poucas: {{aberto_n}} parcelas de {{aberto_alunos}} alunos, que somam {{aberto_valor}}, com atraso mediano de {{aberto_atraso}} dias e {{aberto_recorrencia}} delas no convênio de cobrança recorrente. O problema aparece nas tentativas de cobrança: só {{aprovacao_geral}} das {{tentativas}} tentativas foram aprovadas, e {{tent_12h}} delas foram feitas no lote diário das 12h. Dos {{cartao_mes}} pares cartão-mês, {{nunca_aprovou_mes}} terminaram o mês sem nenhuma aprovação, e {{cartoes_15}} cartões receberam mais de 15 recusas em 30 dias, acima, por exemplo, do limite que a Visa aceita para recusas reversíveis [@cielo2024retentativa]. A @tbl-problema resume o custo de insistir em códigos que não se recuperam.

: Indicadores da cobrança recorrente entre {{periodo_ini}} e {{periodo_fim}} {#tbl-problema}

::: fonte
Fonte: elaborado pelos autores (2026), com dados da Academia Equilíbrio e Movimento.
:::

A chance de recuperar a mensalidade depende do motivo da primeira recusa do mês (@fig-recuperacao). Depois de um código 51, de saldo ou limite insuficiente, {{rec_51}} dos cartões aprovaram no mesmo mês; depois do Pac014, código do próprio sistema de gestão sem documentação pública, só {{rec_pac014}}; e vários códigos não tiveram nenhuma recuperação, embora continuassem sendo re-tentados por semanas.

![Proporção do cartão-mês iniciado com recusa que aprovou no mesmo mês, por código da primeira recusa](#fig-recuperacao)

::: fonte
Fonte: elaborado pelos autores (2026), com dados da Academia Equilíbrio e Movimento.
:::

O dia também importa. Depois de uma recusa por saldo insuficiente, a re-tentativa aprovou de {{dia_1_7_min}} a {{dia_1_7_max}} nos dias 1 a 7 do mês e de {{dia_10_14_min}} a {{dia_10_14_max}} nos dias 10 a 14 (@fig-dia-do-mes), o que sugere um efeito de salário e de fechamento de fatura. As amostras por faixa são pequenas, de {{dia_n_min}} a {{dia_n_max}} tentativas, e o efeito precisa ser confirmado com mais meses. O emissor também pesa: entre os dez BINs mais frequentes, a aprovação variou de {{bin_min}} a {{bin_max}}.

![Aprovação da re-tentativa após recusa por saldo insuficiente (código 51), por faixa do dia do mês](#fig-dia-do-mes)

::: fonte
Fonte: elaborado pelos autores (2026), com dados da Academia Equilíbrio e Movimento.
:::

## Desempenho do modelo

A validação temporal dentro do treino escolheu λ = {{l2}}, com AUC de validação de {{auc_val_l2}}. No mês de teste, o modelo separou bem as re-tentativas que seriam aprovadas: AUC de {{auc_teste}}, contra {{auc_ref}} da referência por código e {{auc_treino}} no próprio treino, sinal de que não houve sobreajuste (@tbl-metricas). O escore de Brier também ficou abaixo do da taxa constante.

: Desempenho do modelo no mês de teste ({{teste_ini}} a {{teste_fim}}) {#tbl-metricas}

::: fonte
Fonte: elaborado pelos autores (2026), com dados da Academia Equilíbrio e Movimento.
:::

A @fig-roc mostra a curva ROC no teste. Aceitando {{roc_fpr_ref}} de falsos positivos, o modelo já encontra {{roc_tpr_ref}} das re-tentativas aprovadas, que é o trecho da curva que interessa para decidir quais re-tentativas manter.

![Curva ROC do modelo no mês de teste](#fig-roc)

::: fonte
Fonte: elaborado pelos autores (2026), com dados da Academia Equilíbrio e Movimento.
:::

As probabilidades estimadas também são coerentes com o que aconteceu (@tbl-calibracao). No quinto das re-tentativas com maior probabilidade estimada, o modelo previu em média {{calib_top_prev}} de aprovação, e ocorreram {{calib_top_real}}; nos demais quintos, a probabilidade prevista não passou de {{calib_resto_prev}}, e a taxa observada, de {{calib_resto_real}}.

: Calibração do modelo no mês de teste, por quintil da probabilidade estimada {#tbl-calibracao}

::: fonte
Fonte: elaborado pelos autores (2026), com dados da Academia Equilíbrio e Movimento.
:::

A @fig-razoes mostra as razões de chances dos atributos de maior efeito. Uma recusa anterior por saldo insuficiente (51) multiplica a chance de aprovação por {{or_51}}, e tentar entre os dias 10 e 14 a multiplica por {{or_d10_14}}. No sentido oposto, cada desvio-padrão a mais de recusas seguidas reduz a chance a {{or_seq}} do que era, e uma recusa anterior pelo código Pac014, a {{or_pac014}}. Como o modelo é regularizado e os atributos se correlacionam, as razões de chances indicam a direção e a intensidade das associações, e não relações de causa.

![Razões de chances dos atributos de maior efeito no modelo (escala logarítmica)](#fig-razoes)

::: fonte
Fonte: elaborado pelos autores (2026), com dados da Academia Equilíbrio e Movimento.
:::

## Políticas avaliadas por *replay*

As regras aprendidas no treino estão na @tbl-regras.

: Regras de decisão aprendidas no período de treino {#tbl-regras}

::: fonte
Fonte: elaborado pelos autores (2026), com dados da Academia Equilíbrio e Movimento.
:::

A @tbl-politicas e a @fig-politicas comparam a política atual com três alternativas no mês de teste. Deixar de re-tentar os códigos irreversíveis (regra 1) evitou {{pol_regra1_evitadas}} das re-tentativas e perdeu {{pol_regra1_perdidas}}. A política do modelo evitou {{pol_modelo_evitadas}} das re-tentativas e manteve {{pol_modelo_aprov}} das aprovações. A regra 2, que soma à regra 1 o teto de {{teto}} recusas seguidas, foi a mais econômica: evitou {{pol_regra2_evitadas}} das re-tentativas e manteve {{pol_regra2_aprov}} das aprovações, com {{pol_regra2_por100}} aprovações a cada 100 tentativas, contra {{pol_atual_por100}} na política atual.

: Políticas de re-tentativa avaliadas por *replay* no mês de teste {#tbl-politicas}

::: fonte
Fonte: elaborado pelos autores (2026), com dados da Academia Equilíbrio e Movimento.
:::

![Re-tentativas feitas e aprovações mantidas por política, em relação à política atual](#fig-politicas)

::: fonte
Fonte: elaborado pelos autores (2026), com dados da Academia Equilíbrio e Movimento.
:::

A escolha entre o modelo e a regra 2 é uma troca entre recuperar mais e insistir menos. As regras são fáceis de explicar e de configurar no sistema; o modelo, por sua vez, é o que permite escolher o dia da re-tentativa, ganho que o *replay* não consegue medir. Por isso o motor combina os dois: as regras funcionam como barreira de segurança, e o modelo decide a data das re-tentativas que valem a pena.

## Fila de ação do dia

Em {{fila_data}}, último dia dos dados, a fila reuniu {{fila_cartoes}} cartões com {{fila_valor}} em mensalidades pendentes, divididos conforme a @tbl-fila. Os cartões que precisam de um novo meio de pagamento concentram {{fila_pct_novo_cartao}} desse valor, e hoje essa ação só acontece depois de semanas de recusas.

: Fila de ação de {{fila_data}}, por tipo de ação {#tbl-fila}

::: fonte
Fonte: elaborado pelos autores (2026), com dados da Academia Equilíbrio e Movimento.
:::

Na @tbl-fila-exemplos estão algumas recomendações da fila, com os cartões identificados por pseudônimos. A versão usada pela recepção traz o nome do titular e fica fora do repositório.

: Exemplos de recomendações da fila de ação {#tbl-fila-exemplos}

::: fonte
Fonte: elaborado pelos autores (2026), com dados da Academia Equilíbrio e Movimento.
:::

## Outros achados para o PIM III

O estudo também levantou sinais para o módulo de retenção. Entre os alunos com plano em setembro de 2026, {{sem_acesso_n}} ({{sem_acesso_pct}}) não passaram na catraca nenhuma vez entre {{acessos_ini}} e {{acessos_fim}}, e os alunos de planos promocionais foram os menos frequentes (@tbl-frequencia). Além disso, {{retornos_pct}} dos alunos ativos já tinham ficado dois meses ou mais sem plano e voltado. Com um único mês de catraca, porém, não foi possível mostrar que a queda de frequência antecede a saída: nas duas primeiras semanas, quem ficou inativo durante a janela teve frequência parecida com a de quem continuou ativo ({{freq_inativo}} e {{freq_ativo}} dias, em média). Esse teste depende de um histórico de 12 a 24 meses de acessos.

: Frequência na catraca por família de plano, de {{acessos_ini}} a {{acessos_fim}} {#tbl-frequencia}

::: fonte
Fonte: elaborado pelos autores (2026), com dados da Academia Equilíbrio e Movimento.
:::

# Conclusão {#sec-conclusao}

O PIM II começou com a intenção de evoluir o classificador de evasão do semestre anterior e terminou com um diagnóstico diferente do problema. Os dados reais mostraram que o export de parcelas só contém sobreviventes, que parcela cancelada marca troca de contrato e não saída, e que a inadimplência da academia é, sobretudo, falha da cobrança recorrente. A regra de cobertura aluno × mês resolveu a confusão entre troca de plano e saída e virou a base comum do projeto.

Sobre essa base, o Motor de Cobrança Inteligente atendeu aos objetivos propostos. O modelo de probabilidade de aprovação ordenou bem as re-tentativas do mês de teste, com AUC de {{auc_teste}} contra {{auc_ref}} da referência, e manteve as probabilidades calibradas no grupo de maior chance. As políticas avaliadas evitaram entre {{pol_regra1_evitadas}} e {{pol_regra2_evitadas}} das re-tentativas, mantendo entre {{pol_regra2_aprov}} e {{pol_regra1_aprov}} das aprovações. A fila diária traduz esses resultados em ações explicáveis para a recepção, sem expor dados pessoais fora da academia.

O trabalho tem limitações. Os dados cobrem só dois meses de tentativas, e o teste tem {{aprov_teste}} aprovações, o que deixa as métricas sensíveis a poucos casos. O *replay* mede com rigor o ganho de parar de insistir, mas não o de re-tentar no dia certo. Os códigos Pac\* vêm do sistema de gestão e não têm documentação pública, e a classificação de código irreversível usada pelo motor é empírica: a documentação da adquirente trata alguns desses códigos, como o 05, como reversíveis em certas bandeiras [@cielo2024codigos], o que reforça a necessidade de validar a tabela com a academia e com o suporte do sistema. Por fim, a regra de saída após dois meses sem cobertura é uma premissa que ainda precisa ser calibrada.

Os próximos passos são re-treinar o motor à medida que chegarem novos exports de transações, o que o carregador já aceita sem mudanças no código; propor à academia um piloto controlado, com metade dos cartões na política nova e metade na atual, medindo o valor recuperado, as tentativas evitadas e os dias até regularizar [@kohavi2009]; registrar o desfecho de cada ação da fila para realimentar o modelo; e iniciar, no PIM III, o módulo de retenção com análise de sobrevivência sobre a mesma base aluno × mês, a partir de um export com ex-alunos e de um histórico longo de acessos.

<!-- ======================================================================
     ELEMENTOS PÓS-TEXTUAIS
     {.pos} = título centralizado, sem número, aparece no sumário
     ====================================================================== -->

# Referências {.pos}

<!-- Gerada automaticamente a partir do refs.bib. Só aparecem as obras citadas no texto. -->

::: {#refs}
:::

# Apêndice A – Código-fonte principal {.pos}

O núcleo do motor é o ajuste da regressão logística regularizada pelo método de Newton (@eq-newton). O trecho abaixo é o método `ajustar` da classe `ModeloAprovacao`, no arquivo `solucao_pim2/motor_cobranca/modelo.py`.

```python arquivo=solucao_pim2/motor_cobranca/modelo.py funcao=ModeloAprovacao.ajustar
```

As regras de decisão aprendidas no treino vêm das funções abaixo, no arquivo `solucao_pim2/motor_cobranca/politicas.py`.

```python arquivo=solucao_pim2/motor_cobranca/politicas.py funcao=codigos_irreversiveis
```

```python arquivo=solucao_pim2/motor_cobranca/politicas.py funcao=teto_de_falhas
```

Repositório do projeto: <https://github.com/PedroRebello1/pim2>. O passo a passo para reproduzir o estudo, o motor e este relatório está no arquivo `README.md`.
