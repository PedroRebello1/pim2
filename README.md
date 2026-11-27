# PIM II: ciclo de vida do aluno

Projeto Integrador II (Ciência de Dados e Machine Learning, CEUB) com a Academia Equilíbrio e Movimento.
O relatório final segue o modelo do professor (`Professor-Weslley/pi-abnt`), no padrão ABNT do folder
*Aplicação das normas da ABNT em trabalhos acadêmicos* da Biblioteca do CEUB, mas é gerado em **Word
(.docx) e PDF**, com **Python no VS Code**, em vez de Quarto e RStudio.

> **Como começar e como entregar:** veja [ENTREGA.md](ENTREGA.md).

- **[relatorio_pi.pdf](relatorio_pi.pdf) / [relatorio_pi.docx](relatorio_pi.docx):** relatório final, gerado a partir do [relatorio_pi.md](relatorio_pi.md).
- **[solucao_pim2/](solucao_pim2/):** solução proposta, o Motor de Cobrança Inteligente (código, resultados e slides da apresentação).
- **[ESTUDO_DADOS_E_OPORTUNIDADES.md](ESTUDO_DADOS_E_OPORTUNIDADES.md):** estudo completo dos dados, com processo, achados, oportunidades, roteiro e dados a pedir.
- **[Pitch_Tecnico_PIM2.pdf](Pitch_Tecnico_PIM2.pdf):** resumo de 3 páginas com os achados e a proposta.
- **[scripts/](scripts/) e [saidas/](saidas/):** pipeline reproduzível do estudo (`00` → `04`) e seus resultados agregados.

Os exports brutos do sistema da academia contêm dados pessoais e **não são versionados** (veja [dados/README.md](dados/README.md)).
O relatório é gerado só com os resultados agregados que estão no repositório.

## O que tem aqui

| Arquivo / pasta | Para que serve | Você edita? |
|---|---|---|
| `relatorio_pi.md` | O relatório (texto, em Markdown) | **Sim** |
| `refs.bib` | Referências bibliográficas | **Sim** |
| `relatorio/valores.py` | Números citados no texto (`{{nome}}`) | **Sim** |
| `relatorio/figuras.py` | Gráficos e diagramas (`fig-...`) | **Sim** |
| `relatorio/tabelas.py` | Tabelas (`tbl-...`) | **Sim** |
| `relatorio/fontes.py` | Leitura dos arquivos de resultados do projeto | Raramente |
| `relatorio/gerar_relatorio.py` | Comando que gera o Word e o PDF | **Não** |
| `relatorio/abnt/` | Padrão ABNT do curso em Word: estilos, capa com o logo do CEUB, sumário, legendas, citações e o padrão visual dos gráficos (`padrao.py`, igual ao do professor) | **Não** |
| `relatorio_pi.docx`, `relatorio_pi.pdf` | Relatório gerado | Não (são gerados) |
| `requirements.txt` | Pacotes Python | **Sim** |
| `imagens/` | Prints e diagramas feitos fora do código | **Sim** |
| `dados/` | Explica por que os dados brutos não estão no repositório | Não |
| `scripts/`, `saidas/` | Estudo dos dados e seus resultados agregados | Sim, com dados novos |
| `solucao_pim2/` | Motor de Cobrança Inteligente, resultados e slides | Sim, com dados novos |
| `testes/` | Testes automáticos do motor e do gerador do relatório (`python -m pytest`) | Sim, ao mudar o código |
| `.github/workflows/render.yml` | Gera o relatório e roda os testes no GitHub a cada push | **Não** |
| `.vscode/` | Tarefas do VS Code: gerar o relatório (Ctrl+Shift+B), prévia em Word e testes | Não |

## Escrevendo o relatório

1. **Topo do `relatorio_pi.md` (PARTE 1):** título, autores, orientador etc. A capa e a folha de rosto são geradas sozinhas a partir daí.
   - **Folha de aprovação** (opcional): descomente `data-aprovacao` e `banca`.
   - **Logo da capa:** sai o do CEUB. Para uma capa só com texto, acrescente `logo: false`.
2. **Texto:** escreva normalmente em Markdown. **Não numere os títulos**: `# Introdução` vira "1 INTRODUÇÃO".
3. **Números no texto:** nunca digite um resultado à mão. Calcule em `relatorio/valores.py` e escreva `{{nome}}` no texto. Para ver todos os valores: `python relatorio/valores.py`.
4. **Gráficos e tabelas:** o texto só indica onde entram e qual a legenda; o código fica em `figuras.py` e `tabelas.py`.

   **Gráfico** (no `relatorio_pi.md`)
   ```
   ![Título do gráfico](#fig-meu-grafico)

   ::: fonte
   Fonte: elaborado pelos autores (2026).
   :::
   ```
   e em `relatorio/figuras.py`:
   ```python
   @figura("fig-meu-grafico")
   def meu_grafico():
       fig, ax = plt.subplots()
       ax.bar(x, y)
       return fig
   ```

   **Tabela** (no `relatorio_pi.md`)
   ```
   : Título da tabela {#tbl-minha-tabela}

   ::: fonte
   Fonte: elaborado pelos autores (2026).
   :::
   ```
   e em `relatorio/tabelas.py`:
   ```python
   @tabela("tbl-minha-tabela")
   def minha_tabela():
       return tabela_abnt(meu_dataframe, nomes={"col": "Cabeçalho"}, casas=2)
   ```
   Uma tabela de texto fixo pode ser escrita direto no `relatorio_pi.md`, logo abaixo da legenda, com `| ... |`.

   - O rótulo precisa começar com `fig-` ou `tbl-`: é isso que numera e permite citar com `@fig-...` e `@tbl-...`.
   - Não use `plt.title()`: o título vai na legenda e sai acima da figura, como manda a ABNT.
   - Prints e diagramas salvos em `imagens/`: `![Título](imagens/arquivo.png){#fig-nome largura=80%}`.
5. **Resumo e Abstract:** parágrafo único, de 150 a 500 palavras, com no mínimo 3 palavras-chave **separadas por ponto e vírgula** (`;`).
6. **Citações e referências** (NBR 10520 e NBR 6023): cadastre as obras no `refs.bib` e cite com `[@chave]` ou `@chave`.
   - Citação direta curta (até 3 linhas): no texto, entre aspas, com a página: `"trecho" [@chave, p. 12]`.
   - Citação direta longa (mais de 3 linhas): use o bloco `::: citacao`.
   - A lista de referências é montada sozinha, em ordem alfabética, só com as obras citadas.

### Atalhos

| No `relatorio_pi.md` | Resultado |
|---|---|
| `# Resumo {.pre}` | Título centralizado, sem número, fora do sumário |
| `# Referências {.pos}` | Título centralizado, sem número, no sumário |
| `# Metodologia {#sec-metodologia}` | Título numerado que pode ser citado com `@sec-metodologia` |
| `::: fonte` | Linha "Fonte: ..." abaixo de figura ou tabela |
| `::: citacao` | Citação direta longa: recuo de 4 cm, letra menor, entrelinha simples |
| `::: listas` | Lista de figuras, lista de tabelas e sumário |
| `::: quebra` | Quebra de página |
| `{{nome}}` | Valor calculado em `relatorio/valores.py` |
| `$$ fórmula $$ {#eq-nome}` | Equação centralizada e numerada; cite com `@eq-nome` |
| `@fig-x`, `@tbl-x`, `@sec-x`, `@eq-x` | "Figura 1", "Tabela 2", "Seção 3", "Equação 1" |
| `**negrito**`, `*itálico*`, `` `código` `` | Formatação no texto |
| `x^2^`, `x~i~` | Sobrescrito e subscrito |

O gerador confere sozinho parte do checklist de entrega: legenda e fonte em toda figura e tabela, toda figura e tabela citada no texto, tamanho do resumo, palavras-chave e obras citadas que faltam no `refs.bib`.

## Preparar o computador (uma única vez)

### Windows

1. **Instale o Python 3.11 ou mais novo** (<https://www.python.org/downloads/>). Na instalação, marque *Add python.exe to PATH*.
2. **Desative o Python da Microsoft Store:** Configurações → Aplicativos → Configurações avançadas de aplicativos → *Aliases de execução de aplicativo* → desligue `python.exe` e `python3.exe`.
3. **Instale o VS Code** (<https://code.visualstudio.com/>) e, dentro dele, a extensão **Python** (da Microsoft).
4. **Instale o Git** (<https://git-scm.com/download/win>), com as opções padrão.
5. **Instale o LibreOffice** (<https://www.libreoffice.org/download/>): é ele que converte o Word em PDF, igual ao GitHub. O caminho é encontrado sozinho.
6. **Ambiente do projeto.** Abra a pasta do repositório no VS Code, abra o terminal (Ctrl+') e rode:

   ```bash
   python -m venv .venv
   .venv\Scripts\activate
   pip install -r requirements.txt
   ```

   Depois, Ctrl+Shift+P → *Python: Select Interpreter* → escolha o `.venv`.

> **Guarde o repositório num caminho simples**, sem acentos, sem espaços e fora do OneDrive. Por exemplo: `C:\projetos\pim2`.

> **Prefere o Word ao LibreOffice para o PDF?** `pip install docx2pdf` e gere com `python relatorio/gerar_relatorio.py --conversor word`.
> O padrão continua sendo o LibreOffice, porque é o mesmo conversor do GitHub Actions.

### macOS

Instale Python, VS Code, Git (`xcode-select --install`) e LibreOffice. Os comandos são os mesmos; para ativar o ambiente, use `source .venv/bin/activate`.

## Gerar o relatório

- **No VS Code:** **Ctrl+Shift+B** (tarefa *Gerar relatório*). É o equivalente ao botão Render do RStudio.
- **No terminal:** `python relatorio/gerar_relatorio.py` (na raiz do repositório). Saem o `relatorio_pi.docx` e o `relatorio_pi.pdf`.
  - `--sem-pdf` gera só uma prévia em Word, `relatorio_pi_previa.docx`, mais rápida e sem os números de página do sumário (saem como 00). Ela não vai para o GitHub e não mexe no `relatorio_pi.docx` nem no `relatorio_pi.pdf`, que só mudam numa geração completa.
- **No GitHub:** a cada `push`, o GitHub Actions gera o relatório numa máquina limpa. Para baixar, vá na aba **Actions**, abra a execução mais recente e baixe **relatorio-pdf** em *Artifacts* (vem o PDF e o Word).
  - Se a execução ficar vermelha (❌), o relatório tem erro: clique nela para ver a mensagem.

O sumário e as listas de figuras e tabelas são campos do Word já preenchidos: o gerador converte o documento, confere em que página ficou cada título e monta de novo com os números certos. Se alguém editar o `.docx` direto no Word e as páginas mudarem, clique no sumário e aperte **F9** (Atualizar o índice inteiro). O caminho recomendado, porém, é editar o `relatorio_pi.md` e gerar de novo.

## Testes

```bash
pip install pytest
python -m pytest
```

Os testes (pasta `testes/`) levam uns 10 segundos e não precisam dos dados da academia: usam tentativas de cobrança sintéticas, no formato do export. Eles conferem os atributos de cada tentativa, o ajuste da regressão logística e as métricas, as regras e a fila do motor, o motor completo de ponta a ponta (inclusive que os resultados versionados não trazem nome nem cartão), a leitura do Markdown, as citações e referências ABNT e a montagem do relatório. No GitHub, eles rodam a cada push, ao lado da geração do relatório.

## Reproduzir o estudo e o motor de cobrança

Precisa dos exports brutos da academia, que ficam fora do repositório. Os comandos estão em [dados/README.md](dados/README.md).
Depois de rodar com dados novos, gere o relatório de novo: os números, as tabelas e os gráficos se atualizam sozinhos.
Os textos escritos à mão no `ESTUDO_DADOS_E_OPORTUNIDADES.md` e no `solucao_pim2/README.md` continuam precisando de atualização manual.

- O motor (`rodar.py`) se recusa a gravar a fila do dia, que traz o nome do titular, dentro do repositório: a pasta privada precisa ficar fora dele.
- O pitch (`scripts/04_pitch_pdf.py`) e os slides (`solucao_pim2/slides/gerar_slides.py`) usam o Edge ou o Chrome para gerar o PDF, no Windows, no macOS ou no Linux. Se nenhum for encontrado, informe o caminho do navegador na variável de ambiente `NAVEGADOR`.

## Problemas comuns

| Sintoma | Solução |
|---|---|
| `ModuleNotFoundError: No module named 'docx'` (ou `yaml`, `pypdf`, `matplotlib`) | Ative o `.venv` e rode `pip install -r requirements.txt`. No VS Code, confira o interpretador selecionado. |
| `Python was not found`, ou abre a Microsoft Store (Windows) | Faça o passo 2 do Windows. |
| `Nenhum conversor de PDF encontrado` | Instale o LibreOffice. Se ele estiver num lugar diferente, informe o caminho do `soffice.exe` na variável de ambiente `SOFFICE`. |
| `Não consegui gravar relatorio_pi.pdf` | Feche o PDF e o Word e gere de novo. |
| `ERRO: Linha N: o valor {{x}} não existe em relatorio/valores.py` | Crie a chave `x` em `relatorio/valores.py` ou corrija o nome no texto. |
| `ERRO: ... a obra @x não está no refs.bib` | Cadastre a obra no `refs.bib` ou corrija a chave. |
| `ERRO: A figura @fig-x não existe em relatorio/figuras.py` | Crie a função com `@figura("fig-x")`. O mesmo vale para tabelas (`@tabela("tbl-x")`). |
| Aviso `falta o bloco '::: fonte'` ou `não é citada no texto` | Acrescente o `::: fonte` abaixo da figura/tabela e cite-a com `@fig-...`/`@tbl-...`. |
| Sumário com páginas erradas depois de editar no Word | Clique no sumário e aperte F9, ou gere de novo pelo script. |
| Funciona no seu computador, mas fica ❌ no GitHub | Falta pacote no `requirements.txt`, ou um arquivo de resultados não foi enviado (confira `saidas/` e `solucao_pim2/resultados/`). Se o ❌ for no job *testes*, rode `python -m pytest` para ver qual teste falhou. |
| `a pasta privada precisa ficar fora do repositório` (motor) | Passe ao `rodar.py` uma pasta fora do repositório para a fila do dia, por exemplo `C:\academia\privado`. |
| `Não achei o Edge nem o Chrome` (pitch ou slides) | Instale um deles ou informe o caminho do executável na variável de ambiente `NAVEGADOR`. |
| Erro em caminho com acento, espaço ou `OneDrive` | Guarde o repositório em `C:\projetos\pim2`. |
