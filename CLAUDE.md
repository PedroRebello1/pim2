# Contexto para o Claude Code

O Claude Code carrega este arquivo automaticamente quando abre esta pasta. Ele resume o que foi decidido nas sessões anteriores e o que não dá para deduzir só lendo o código. **O repositório é público:** nada de dados pessoais aqui.

## Projeto

- Projeto Integrador de Ciência de Dados e Machine Learning do CEUB, em 3 semestres: PIM I (concluído em jun/2026), **PIM II (2º sem/2026, atual)** e PIM III (próximo).
- Parceiro: Academia Equilíbrio e Movimento (Brasília). Os dados são reais, exportados do sistema de gestão: parcelas, catraca e transações de cartão.
- Grupo: Pedro Rebello, Guilherme Mendes, Eduardo Barros e Gabriel Francisco.
- O PIM I fez um classificador de churn com o rótulo "≥1 parcela cancelada". O rótulo é inválido: 93,5% dos "positivos" continuam ativos. O código do PIM I não é reaproveitado.

## Onde estamos (29/10/2026)

1. **Estudo dos dados** (`ESTUDO_DADOS_E_OPORTUNIDADES.md`, `scripts/`, `saidas/`): achados, oportunidades A–G, roteiro, dados a pedir à academia (seção 9) e perguntas em aberto (seção 11).
2. **Pitch técnico** de 3 páginas para o grupo: `Pitch_Tecnico_PIM2.pdf`.
3. **Solução do PIM II** (`solucao_pim2/`): Motor de Cobrança Inteligente e 12 slides 16:9, para a apresentação ao professor em **30/10/2026**.

Direção acordada: tema "ciclo de vida do aluno", sobre uma base comum (estado aluno × mês).
- **PIM II:** churn involuntário, ou seja, recuperar a cobrança recorrente que falha no cartão.
- **PIM III:** retenção, com análise de sobrevivência. Depende de exports com ex-alunos e de um histórico longo de acessos, que ainda não chegaram.

Próximos passos: re-treinar quando chegarem mais meses de transações, propor um piloto A/B à academia e pedir os dados da seção 9 do estudo.

## Regras deste repositório

- **Sem dados pessoais no git:** nada de planilhas, nomes, CPF, e-mail ou telefone. O `.gitignore` bloqueia `*.xls*`, `*.csv.gz`, `*.pkl`, `*.parquet`, `data/` e `cache*/`. As saídas versionadas trazem só agregados e IDs pseudonimizados (`C-` + sha1[:5]).
- A fila do dia com o nome do titular vai para uma pasta privada **fora** do repositório.
- Antes de cada commit, procurar nomes de alunos ou titulares no diff. O nome "Guilherme" na capa dos slides é de um integrante do grupo, não é vazamento.
- Os exports brutos e o código antigo do PIM I ficam no repositório **privado** `PedroRebello1/pim2dev1`. Nunca enviar aquele histórico para este repositório.
- Nos materiais do grupo (pitch, slides, READMEs), não falar de repositórios anteriores nem do manuseio dos dados brutos. O grupo considera o assunto resolvido.
- Tudo fica dentro desta pasta (`ap2/`, raiz do git), porque as sessões do Claude Code são abertas aqui.
- Commit e push só quando o usuário pedir.

## Armadilhas dos dados (checar a cada novo export)

- **O export de parcelas (`ParcelaEmAbertoRel`) traz só os clientes ativos** na data do export. Isso é viés de sobrevivência: o arquivo não mede churn. Confirmar se um novo export inclui os inativos.
- **Parcela "Cancelada" não é saída.** A troca de plano gera uma ocorrência ativa no plano novo e uma cancelada no antigo. Renovação antecipada, trancamento e saída também cancelam parcelas.
- O estado do aluno vem da **cobertura**. Um mês está coberto se há mensalidade não cancelada em qualquer contrato. Saída é N ≥ 2 meses sem cobertura, com censura à direita.
- `Pagamento` em cheque ou cartão de crédito é a data da venda (pré-datado ou parcelado), não a do pagamento do mês.
- A flag `Recorrência` não é confiável. `Contrato 0` são vendas avulsas.
- O número do `Contrato` é sequencial no tempo (Spearman 0,99996), então as lacunas de ID estimam a retenção por coorte.
- As transações de cartão não trazem matrícula. O vínculo é heurístico (dia + valor + nome, com pareamento 1:1 guloso) e ancora cerca de 63% das aprovações.
- Os códigos `Pac*` vêm do sistema de gestão e não têm documentação pública.

## Decisões de método do motor de cobrança (não refazer sem motivo)

O código está em `solucao_pim2/motor_cobranca/`.

- A unidade de decisão é a re-tentativa, isto é, a tentativa logo após uma recusa do mesmo cartão. A 1ª cobrança do mês sempre acontece.
- Regressão logística L2 ajustada por Newton/IRLS em numpy. O λ sai de validação temporal dentro do treino. O target encoding do BIN usa só o treino.
- Validação temporal: o teste é sempre o último mês dos dados. Hoje o treino vai de 15/08 a 30/09 e o teste de 01/10 a 15/10.
- As políticas são avaliadas por **replay**, que mede bem o "parar de insistir". O ganho de "re-tentar no dia certo" só aparece num piloto A/B.
- Códigos irreversíveis: a re-tentativa aprova ≤ 1%, com pelo menos 15 casos. O critério não é "zero recuperações", porque o Pac014 tem 1 recuperação em cerca de 1.200.
- O teto de falhas é calculado só entre os códigos recuperáveis (≤ 1%, com pelo menos 30 casos) e hoje dá 5.
- O limiar do modelo é o que mantém 95% das aprovações do treino.
- Na fila, a data sugerida é o primeiro dia, nos próximos 10, que alcança 90% da melhor chance.

Resultados atuais (teste de out/2026):
- AUC 0,922, contra 0,816 da referência.
- O modelo evita 71% das re-tentativas e mantém 94% das aprovações.
- A fila de 15/10 tem 143 cartões e R$ 24,2 mil pendentes.

Detalhes em `solucao_pim2/resultados/metricas.json`.

## Como rodar

Os dados brutos ficam fora do repositório, por exemplo numa pasta local copiada de `pim2dev1`.

```bash
# Estudo (a pasta de cache também fica fora do repo)
python scripts/00_carregar.py <pasta_exports> <pasta_cache>
python scripts/01_cobertura_e_eventos.py <pasta_cache>
python scripts/02_vincular_transacoes.py <pasta_cache>
python scripts/03_analises.py <pasta_cache>        # gera saidas/
python scripts/04_pitch_pdf.py                     # gera Pitch_Tecnico_PIM2.pdf a partir de saidas/

# Solução
cd solucao_pim2/motor_cobranca && python rodar.py <pasta_exports> <pasta_privada>
cd ../slides && python gerar_slides.py             # gera apresentacao.html e apresentacao.pdf
```

O carregador do motor reconhece cada xlsx pelo cabeçalho, então novos exports entram sem mudar o código.

O pitch e os slides são gerados a partir dos CSVs. **Os números escritos à mão** em `solucao_pim2/README.md` e em `ESTUDO_DADOS_E_OPORTUNIDADES.md` precisam ser atualizados manualmente depois de rodar com dados novos.

## Ambiente da máquina original

- Windows 11, com Python 3.15.1, pandas 3.1, numpy 2.5 e openpyxl.
- **Sem scikit-learn e sem scipy:** tudo foi implementado em numpy.
- Os PDFs são gerados pelo Edge headless (`--print-to-pdf --no-pdf-header-footer`). O caminho do Edge está fixo na variável `EDGE` de `scripts/04_pitch_pdf.py` e de `solucao_pim2/slides/gerar_slides.py`. Em outra máquina, ajustar.
- Para revisar o layout, renderizar as páginas do PDF em PNG com pymupdf e olhar.
- Se chamar o Edge pelo Bash falhar, usar `Start-Process` no PowerShell.

## Preferências do usuário

- Conversa em português, às vezes em inglês. Os materiais do projeto são em português.
- Quer o processo documentado em Markdown e os artefatos salvos nesta pasta.
- Quando houver dúvida real sobre os dados, prefere uma pergunta a uma suposição. A troca de plano foi um exemplo.
- Materiais para o grupo devem ser enxutos, só com o importante.
