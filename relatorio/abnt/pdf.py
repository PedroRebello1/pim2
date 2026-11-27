"""Conversão .docx -> .pdf e localização das páginas para o sumário e as listas.

O Word guarda o sumário como um campo; quem calcula as páginas é o programa que desenha o
documento. Para o PDF sair com as páginas certas sem depender de ninguém clicar em
"Atualizar campo", o gerador faz duas passadas: monta o .docx, converte, lê em que página
ficou cada título e cada legenda, e monta de novo com esses números.

Conversores aceitos:
- LibreOffice (padrão; é o que o GitHub Actions usa). No Windows, instale de
  https://www.libreoffice.org/ e o caminho é encontrado sozinho.
- Microsoft Word, pelo pacote docx2pdf (Windows/macOS): python relatorio/gerar_relatorio.py --conversor word

Faz parte do padrão: não edite.
"""
from __future__ import annotations

import os
import re
import shutil
import subprocess
import tempfile
import unicodedata
from pathlib import Path

from .markdown import ErroRelatorio

CAMINHOS_LIBREOFFICE = [
    r"C:\Program Files\LibreOffice\program\soffice.exe",
    r"C:\Program Files (x86)\LibreOffice\program\soffice.exe",
    "/Applications/LibreOffice.app/Contents/MacOS/soffice",
    "/usr/bin/soffice",
    "/usr/bin/libreoffice",
]


def achar_libreoffice() -> str | None:
    for c in [os.environ.get("SOFFICE"), shutil.which("soffice"), shutil.which("libreoffice")] + CAMINHOS_LIBREOFFICE:
        if c and Path(c).exists():
            console = Path(c).with_suffix(".com")      # no Windows, o soffice.com espera a conversão terminar
            return str(console) if os.name == "nt" and console.exists() else c
    return None


def tem_word() -> bool:
    try:
        import docx2pdf  # noqa: F401
        return os.name == "nt" or Path("/Applications/Microsoft Word.app").exists()
    except ImportError:
        return False


def escolher_conversor(pedido: str) -> str | None:
    if pedido == "libreoffice":
        if not achar_libreoffice():
            raise ErroRelatorio("LibreOffice não encontrado. Instale (https://www.libreoffice.org/) ou informe o "
                                "caminho do soffice na variável de ambiente SOFFICE.")
        return "libreoffice"
    if pedido == "word":
        if not tem_word():
            raise ErroRelatorio("Para converter pelo Word: Windows ou macOS com o Word instalado e "
                                "'pip install docx2pdf'.")
        return "word"
    if achar_libreoffice():
        return "libreoffice"
    if tem_word():
        return "word"
    return None


def converter(docx: Path, pasta: Path, conversor: str) -> Path:
    """Converte e devolve o caminho do PDF (em `pasta`)."""
    pasta.mkdir(parents=True, exist_ok=True)
    pdf = pasta / (docx.stem + ".pdf")
    if pdf.exists():
        pdf.unlink()
    if conversor == "word":
        from docx2pdf import convert
        convert(str(docx), str(pdf))
    else:
        # perfil temporário: funciona mesmo com o LibreOffice aberto em outra janela
        with tempfile.TemporaryDirectory(prefix="lo_perfil_", ignore_cleanup_errors=True) as perfil:
            cmd = [achar_libreoffice(), f"-env:UserInstallation={Path(perfil).as_uri()}", "--headless",
                   "--convert-to", "pdf", "--outdir", str(pasta), str(docx)]
            r = subprocess.run(cmd, capture_output=True, text=True, timeout=600)
            _esperar_arquivo(pdf)
        if r.returncode != 0 or not pdf.exists():
            raise ErroRelatorio(f"O LibreOffice não conseguiu gerar o PDF.\n{r.stdout}\n{r.stderr}")
    return pdf


def _esperar_arquivo(caminho: Path, limite_s: float = 90):
    """Espera o PDF aparecer e parar de crescer (em alguns Windows o soffice devolve antes de terminar)."""
    import time
    inicio, tamanho = time.time(), -1
    while time.time() - inicio < limite_s:
        if caminho.exists():
            atual = caminho.stat().st_size
            if atual > 0 and atual == tamanho:
                return
            tamanho = atual
        time.sleep(0.5)


# ----------------------------------------------------------------------------- páginas
def _norm(texto: str) -> str:
    t = unicodedata.normalize("NFKC", texto).replace("\u00ad", "").replace("\u200b", "")
    t = re.sub(r"[\u2010-\u2015\u2212-]", "-", t)
    return re.sub(r"\s+", "", t).casefold()


def _achatar(outline):
    for item in outline:
        if isinstance(item, list):
            yield from _achatar(item)
        else:
            yield item


def localizar(pdf: Path, sumario: list[dict], figuras: list[dict], tabelas: list[dict], natureza: str) -> dict:
    """Devolve {('sec', i) | ('fig', n) | ('tbl', n): página exibida} para montar as listas."""
    from pypdf import PdfReader
    leitor = PdfReader(str(pdf))
    textos = [_norm(p.extract_text() or "") for p in leitor.pages]

    marca = _norm(natureza)[:40]
    rosto = next((i for i, t in enumerate(textos) if marca and marca in t), 1)
    sumario_pag = next((i for i, t in enumerate(textos) if t.startswith("sumário")), rosto)

    def exibida(i):
        return i - rosto + 1

    # títulos: primeiro pelos marcadores do PDF; se faltar algum, pelo texto das páginas
    marcadores = []
    try:
        for d in _achatar(leitor.outline):
            marcadores.append((_norm(d.title), leitor.get_destination_page_number(d)))
    except Exception:
        marcadores = []
    paginas, cursor_m, cursor_p = {}, 0, sumario_pag + 1
    for k, e in enumerate(sumario):
        alvo = _norm(f"{e['numero']} {e['titulo']}")
        achou = None
        for j in range(cursor_m, len(marcadores)):
            if marcadores[j][0] == alvo or marcadores[j][0].startswith(alvo[:60]):
                achou, cursor_m = marcadores[j][1], j + 1
                break
        if achou is None:
            for i in range(cursor_p, len(textos)):
                if alvo[:60] in textos[i]:
                    achou = i
                    break
        if achou is None:
            raise ErroRelatorio(f"Não achei no PDF a página do título '{e['numero']} {e['titulo']}'.")
        cursor_p = achou
        paginas[("sec", k)] = exibida(achou)

    inicio_textual = min((v for (t, _), v in paginas.items() if t == "sec"), default=1) + rosto - 1
    for tipo, chave, itens in (("Figura", "fig", figuras), ("Tabela", "tbl", tabelas)):
        cursor = inicio_textual
        for item in itens:
            alvo = _norm(f"{tipo} {item['numero']} – {item['titulo']}")[:45]
            achou = next((i for i in range(cursor, len(textos)) if alvo in textos[i]), None)
            if achou is None:
                alvo_curto = _norm(f"{tipo} {item['numero']} –")
                achou = next((i for i in range(cursor, len(textos)) if alvo_curto in textos[i]), None)
            if achou is None:
                raise ErroRelatorio(f"Não achei no PDF a página da {tipo.lower()} {item['numero']}.")
            cursor = achou
            paginas[(chave, item["numero"])] = exibida(achou)
    return paginas
