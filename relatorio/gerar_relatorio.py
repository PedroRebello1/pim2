"""Gera o relatório final em Word e PDF a partir do relatorio_pi.md.

    python relatorio/gerar_relatorio.py            # relatorio_pi.docx + relatorio_pi.pdf
    python relatorio/gerar_relatorio.py --sem-pdf  # prévia rápida: relatorio_pi_previa.docx
    python relatorio/gerar_relatorio.py --conversor word   # PDF pelo Microsoft Word (docx2pdf)

O relatorio_pi.docx e o relatorio_pi.pdf só são gravados numa geração completa, com os números de
página do sumário e das listas conferidos no PDF. A prévia (--sem-pdf, ou quando não há conversor de
PDF) sai em relatorio_pi_previa.docx, com as páginas em 00, e não mexe no relatório final.

No VS Code: Ctrl+Shift+B (tarefa "Gerar relatório"). É o equivalente ao botão Render do
RStudio no modelo do professor. Os números, as tabelas e os gráficos são calculados a partir
dos arquivos do repositório (saidas/ e solucao_pim2/resultados/), então o relatório sai igual
em qualquer computador.
"""
from __future__ import annotations

import argparse
import shutil
import sys
import time
from pathlib import Path

AQUI = Path(__file__).resolve().parent
BASE = AQUI.parent
sys.path.insert(0, str(AQUI))

from abnt import pdf as pdf_abnt  # noqa: E402
from abnt.markdown import ErroRelatorio, ler_relatorio  # noqa: E402
from abnt.referencias import Bibliografia  # noqa: E402
from abnt.word import DocumentoABNT  # noqa: E402


def conferir(meta: dict, blocos, doc: DocumentoABNT, texto: str) -> list[str]:
    """Parte automática do checklist de entrega (ENTREGA.md). `texto` é o Markdown lido."""
    avisos = list(doc.avisos)
    texto_resumo, dentro = [], False
    for b in blocos:
        if b.tipo == "titulo":
            dentro = "pre" in b.classes and b.texto.strip().lower() == "resumo"
        elif dentro and b.tipo == "paragrafo":
            texto_resumo.append(b.texto)
    if texto_resumo:
        corpo = [t for t in texto_resumo if not t.lstrip("*_ ").lower().startswith("palavras-chave")]
        palavras = len(" ".join(corpo).split())
        if not 150 <= palavras <= 500:
            avisos.append(f"O resumo tem {palavras} palavras (a NBR 6028 pede de 150 a 500).")
        chaves = [t for t in texto_resumo if t.lstrip("*_ ").lower().startswith("palavras-chave")]
        if not chaves or len(chaves[0].split(":", 1)[-1].split(";")) < 3:
            avisos.append("Faltam palavras-chave no resumo (mínimo de 3, separadas por ponto e vírgula).")
    else:
        avisos.append("O relatório não tem resumo (# Resumo {.pre}).")
    sequencia = list(doc._todos(blocos))
    for i, b in enumerate(sequencia):
        if b.tipo in ("figura", "tabela"):
            prox = sequencia[i + 1] if i + 1 < len(sequencia) else None
            if not (prox and prox.tipo == "div" and prox.texto == "fonte"):
                avisos.append(f"Linha {b.linha}: falta o bloco '::: fonte' logo abaixo de @{b.id}.")
    if "✏️ SUBSTITUA" in texto:
        avisos.append("Ainda há trechos marcados com '✏️ SUBSTITUA' no relatorio_pi.md.")
    return avisos


def main() -> int:
    ap = argparse.ArgumentParser(description="Gera relatorio_pi.docx e relatorio_pi.pdf a partir do relatorio_pi.md")
    ap.add_argument("--sem-pdf", action="store_true",
                    help="gera só uma prévia em Word (relatorio_pi_previa.docx), sem as páginas do sumário")
    ap.add_argument("--conversor", choices=["auto", "libreoffice", "word"], default="auto")
    ap.add_argument("--entrada", default="relatorio_pi.md")
    args = ap.parse_args()
    inicio = time.time()

    import figuras
    import tabelas
    import valores

    entrada = BASE / args.entrada
    meta, blocos = ler_relatorio(entrada)
    bib = Bibliografia(BASE / meta.get("bibliography", "refs.bib"))
    build = AQUI / "_build"
    build.mkdir(exist_ok=True)
    print("• calculando os valores do texto (relatorio/valores.py)")
    vals = valores.calcular()
    graficos = figuras.Figuras(build / "figuras")
    doc = DocumentoABNT(meta, vals, bib, graficos.obter, tabelas.obter, BASE)
    doc.numerar(blocos)

    conversor = None if args.sem_pdf else pdf_abnt.escolher_conversor(args.conversor)
    if not args.sem_pdf and conversor is None:
        print("! Nenhum conversor de PDF encontrado (LibreOffice ou Word). Gerando só a prévia em Word.\n"
              "  Instale o LibreOffice: https://www.libreoffice.org/download/")
    nome = entrada.stem
    docx_tmp = build / f"{nome}.docx"
    paginas, pdf_tmp, estavel = None, None, False
    for passada in range(1, 4):
        print(f"• montando o Word (passada {passada})")
        doc.construir(blocos, paginas).save(docx_tmp)
        if conversor is None:
            break
        print(f"• convertendo para PDF com {'o LibreOffice' if conversor == 'libreoffice' else 'o Word'}")
        pdf_tmp = pdf_abnt.converter(docx_tmp, build, conversor)
        novas = pdf_abnt.localizar(pdf_tmp, doc.sumario, doc.figuras, doc.tabelas, meta.get("natureza", ""))
        if novas == paginas:
            estavel = True
            break
        paginas = novas
    # Sem PDF não há como saber as páginas: a prévia vai para outro arquivo, e o relatório final
    # (que vai para o GitHub e para a entrega) continua sendo o da última geração completa.
    saidas = [(docx_tmp, f"{nome}.docx"), (pdf_tmp, f"{nome}.pdf")] if conversor else [(docx_tmp, f"{nome}_previa.docx")]
    for origem, destino in saidas:
        try:
            shutil.copyfile(origem, BASE / destino)
        except PermissionError:
            raise ErroRelatorio(f"Não consegui gravar {destino}: feche o arquivo no Word ou no leitor de PDF e rode de novo.")
        print(f"✓ {destino}")
    if conversor is None:
        como = "rode sem --sem-pdf (Ctrl+Shift+B)" if args.sem_pdf else "instale o LibreOffice e gere de novo"
        print(f"  Prévia sem os números de página do sumário e das listas (saem como 00). O {nome}.docx e o\n"
              f"  {nome}.pdf não foram alterados: para gerá-los, {como}.")
    avisos = conferir(meta, blocos, doc, entrada.read_text(encoding="utf-8"))
    if conversor and not estavel:
        avisos.append("Os números de página do sumário ainda mudavam na última passada: confira o sumário e as "
                      "listas no PDF antes de entregar.")
    for a in avisos:
        print(f"! {a}")
    print(f"Pronto em {time.time() - inicio:.0f} s." + ("" if avisos else " Checklist automático sem avisos."))
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except ErroRelatorio as e:
        print(f"\nERRO: {e}\n", file=sys.stderr)
        sys.exit(1)
