# Como entregar o relatório final do PI

Adaptação do `ENTREGA.md` do modelo do professor (`Professor-Weslley/pi-abnt`) para o nosso fluxo em
**Word + PDF, com Python no VS Code**. Os passos de GitHub, reprodutibilidade e entrega no Moodle são os mesmos.

**Prazo:** até 23:59 do dia da apresentação: **Turma B, 02/12** · **Turma A, 04/12**.

## 1. Repositório do grupo (uma vez por grupo)

Só **um** integrante faz este passo.

O modelo do professor parte do botão **Use this template**, que gera um projeto em Quarto/R. Como o nosso relatório é
gerado em Python, o repositório de entrega é **este** projeto. Duas opções:

- **Usar o repositório atual**: em **Settings → General**, renomeie para `pi-<turma>-<sobrenomes>` (ex.: `pi-3a-rebello-mendes`)
  e, em **Danger Zone → Change repository visibility**, deixe **Private**.
- **Ou criar um repositório novo**, privado, com esse nome, e enviar esta pasta para ele.

## 2. Dar acesso ao professor e ao grupo

No repositório de entrega:

1. **Settings** → **Collaborators** → **Add people**.
2. Adicione **`Professor-Weslley`**.
3. Adicione também os colegas do grupo.

> O convite expira em 7 dias. Se o professor não aceitar a tempo, envie de novo.

## 3. Trazer o repositório para o computador

No VS Code: **Ctrl+Shift+P** → **Git: Clone** → cole o endereço do repositório (botão verde **Code** → HTTPS) e escolha
uma pasta **sem acentos e fora do OneDrive** (ex.: `C:\projetos`).

Depois, siga a seção **Preparar o computador** do [README](README.md).

## 4. Trabalhar no relatório

- Edite o `relatorio_pi.md` (texto), o `refs.bib` (referências) e, quando precisar, `relatorio/valores.py`,
  `relatorio/figuras.py` e `relatorio/tabelas.py`.
- Aperte **Ctrl+Shift+B** para gerar o `relatorio_pi.docx` e o `relatorio_pi.pdf` e confira o resultado.
- Salve o progresso no GitHub com frequência. Na aba **Source Control** do VS Code (Ctrl+Shift+G): marque os
  arquivos → escreva uma mensagem → **Commit** → **Sync/Push**. Inclua o `.docx` e o `.pdf` gerados.
- Antes de começar a trabalhar, faça **Pull** para receber as alterações dos colegas.
- Se dois colegas mexerem no `.docx`/`.pdf` ao mesmo tempo e o Git acusar conflito nesses arquivos, não tente juntar:
  faça o pull, gere o relatório de novo e faça o commit.
- A cada push, o GitHub gera o relatório sozinho (aba **Actions**). ✅ verde significa que ele saiu sem erro numa máquina limpa.

## 5. Garantir a reprodutibilidade

O professor vai **clonar o repositório e gerar o relatório do zero**. A entrega só vale se isso funcionar.

- **Dados:** os exports brutos da academia têm dados pessoais e não podem ir para o GitHub. O relatório é gerado só com
  os resultados agregados que estão no repositório (`saidas/` e `solucao_pim2/resultados/`), e a origem dos dados está
  explicada na Metodologia e em [dados/README.md](dados/README.md). **Confirme com o professor** que isso atende ao item
  "dados no repositório" do modelo.
- **Caminhos relativos:** todo o código do relatório lê os arquivos a partir da raiz do repositório; nada de `C:/Users/...`.
- **Pacotes:** todos estão no `requirements.txt`. Se usar um pacote novo, acrescente lá.
- **Sementes aleatórias:** o motor de cobrança é determinístico (regressão ajustada pelo método de Newton, sem sorteio),
  então os números são sempre os mesmos. Se algum código novo usar sorteio, fixe a semente (`random_state=42`, `np.random.seed(42)`).
- **Código da análise no repositório:** `scripts/` (estudo) e `solucao_pim2/motor_cobranca/` (motor); o relatório roda sozinho.
- **Nenhuma senha, token, chave de API ou dado pessoal** no repositório.

**Como saber se está reprodutível:** a aba **Actions** ✅ verde significa que o GitHub conseguiu gerar o relatório numa
máquina limpa, só com o que está no repositório.

## 6. Entregar (até o prazo)

1. Gere o relatório uma última vez, faça **Commit** e **Push** e confira se a aba **Actions** está ✅ verde.
2. **Crie a versão de entrega (release)** no GitHub:
   1. Na página do repositório, na coluna da direita, clique em **Releases** → **Create a new release**.
   2. Em **Choose a tag**, digite `entrega-final` e clique em **Create new tag: entrega-final on publish**.
   3. Em **Release title**, escreva `Entrega final`.
   4. Clique em **Publish release**.
   5. Copie o endereço da página que abrir (ex.: `https://github.com/seu-usuario/pi-3a-rebello-mendes/releases/tag/entrega-final`).
3. Baixe o PDF: **Actions** → execução mais recente → **relatorio-pdf** (ou use o `relatorio_pi.pdf` do repositório,
   que é o mesmo).
4. No Moodle, na tarefa de entrega, envie:
   - o **PDF** do relatório (arquivo);
   - o **link do repositório** e o **link da release** `entrega-final` (texto online).

> A release congela a versão entregue. O professor avalia **exatamente essa versão**, mesmo que o repositório receba
> commits depois. Se precisar corrigir algo **antes do prazo**, apague a release e a tag `entrega-final` e crie de novo.

## Checklist antes de entregar

- [ ] Capa e folha de rosto com o nome completo de todos os integrantes e do orientador.
- [ ] Endereço do repositório certo no Apêndice A do `relatorio_pi.md`.
- [ ] O gerador termina com "Checklist automático sem avisos" (figuras e tabelas com legenda, fonte e citadas no texto;
      resumo de 150 a 500 palavras; palavras-chave).
- [ ] Resumo e Abstract revisados, com palavras-chave.
- [ ] Toda obra citada está no `refs.bib` (o gerador acusa as que faltam) e só as citadas aparecem nas referências.
- [ ] Resultados agregados no repositório, caminhos relativos e `requirements.txt` completo.
- [ ] Nenhuma senha, token, chave de API ou dado pessoal no repositório.
- [ ] Aba **Actions** ✅ verde.
- [ ] Release `entrega-final` criada.
- [ ] `Professor-Weslley` adicionado como colaborador.
