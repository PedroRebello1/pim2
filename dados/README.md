# Dados

O modelo do professor pede que os dados fiquem nesta pasta. Neste projeto, os dados de origem são
exports do sistema de gestão da Academia Equilíbrio e Movimento (parcelas, catraca e tentativas de
cobrança no cartão) e **contêm dados pessoais** (nome, CPF, e-mail, telefone e cartão mascarado).
Por isso, e em respeito à LGPD e ao combinado com a academia, **eles não são versionados**.

O que o repositório traz, e o que alimenta o relatório, são os resultados agregados desses dados:

| Pasta | Conteúdo | Gerado por |
|---|---|---|
| `saidas/` | tabelas agregadas, gráficos e log do estudo dos dados | `scripts/03_analises.py` |
| `solucao_pim2/resultados/` | métricas, políticas, coeficientes, curva ROC e fila de ação (IDs pseudonimizados) | `solucao_pim2/motor_cobranca/rodar.py` |

Com esses arquivos, `python relatorio/gerar_relatorio.py` gera o relatório do zero em qualquer
computador, e é isso que o GitHub Actions confere a cada push.

## Reproduzir a partir dos exports brutos

Quem tiver os exports, com autorização da academia, reproduz o estudo e o motor com os comandos
abaixo. As pastas de exports, de cache e privada ficam **fora** do repositório.

```bash
python scripts/00_carregar.py <pasta_exports> <pasta_cache>
python scripts/01_cobertura_e_eventos.py <pasta_cache>
python scripts/02_vincular_transacoes.py <pasta_cache>
python -X utf8 scripts/03_analises.py <pasta_cache> > saidas/log_03_analises.txt
cd solucao_pim2/motor_cobranca && python rodar.py <pasta_exports> <pasta_privada>
```

O `> saidas/log_03_analises.txt` importa: o relatório lê alguns números desse log.

Depois, gere o relatório de novo: os números do texto, as tabelas e os gráficos se atualizam sozinhos.
