"""Leitura do relatorio_pi.md: cabeçalho YAML + texto em Markdown com os atalhos ABNT.

Atalhos (os mesmos do modelo do professor, adaptados ao Word):

    # Resumo {.pre}              título centralizado, sem número, fora do sumário
    # Referências {.pos}         título centralizado, sem número, no sumário
    # Metodologia {#sec-met}     título numerado ("3 METODOLOGIA"), citável com @sec-met
    ::: fonte / ::: citacao      "Fonte: ..." e citação direta longa
    ::: listas                   lista de figuras, lista de tabelas e sumário
    ::: {#refs}                  lista de referências
    ![Legenda](#fig-id)          figura gerada por código (relatorio/figuras.py)
    ![Legenda](imagens/x.png){#fig-id largura=80%}   figura salva em arquivo
    : Legenda {#tbl-id}          tabela gerada por código (relatorio/tabelas.py) ou,
                                 se vier seguida de linhas | ... |, tabela escrita no texto
    $$ equação $$ {#eq-id}       equação centralizada e numerada
    {{nome}}                     valor calculado em relatorio/valores.py
    [@chave] e @chave            citações (refs.bib)
    @fig-id, @tbl-id, @sec-id, @eq-id   "Figura 1", "Tabela 2", "Seção 3", "Equação 1"

Este módulo só lê o texto: não sabe nada de Word. Faz parte do padrão: não edite.
"""
from __future__ import annotations

import re
import shlex
from dataclasses import dataclass, field

import yaml


class ErroRelatorio(Exception):
    """Erro no relatorio_pi.md, com a linha onde aconteceu."""


# ----------------------------------------------------------------------------- blocos
@dataclass
class Bloco:
    tipo: str            # titulo, paragrafo, lista, figura, tabela, div, codigo, equacao
    linha: int
    texto: str = ""
    nivel: int = 0
    classes: list = field(default_factory=list)
    id: str = ""
    attrs: dict = field(default_factory=dict)
    itens: list = field(default_factory=list)    # lista: [(nivel, texto)]; tabela: linhas do texto
    filhos: list = field(default_factory=list)   # conteúdo de ::: div
    ordenada: bool = False


RE_TITULO = re.compile(r"^(#{1,4})\s+(.+?)\s*(?:\{([^}]*)\})?\s*$")
RE_DIV_ABRE = re.compile(r"^(:{3,})\s*(?:\{([^}]*)\}|([A-Za-z][\w-]*))\s*$")
RE_DIV_FECHA = re.compile(r"^:{3,}\s*$")
RE_CERCA = re.compile(r"^(`{3,})\s*(.*)$")
RE_FIGURA = re.compile(r"^!\[(.*)\]\(([^)\s]+)\)\s*(?:\{([^}]*)\})?\s*$")
RE_LEGENDA_TAB = re.compile(r"^:\s+(.+?)\s*\{([^}]*#tbl-[^}]*)\}\s*$")
RE_EQUACAO = re.compile(r"^\$\$(.+?)\$\$\s*(?:\{([^}]*)\})?\s*$")
RE_ITEM = re.compile(r"^(\s*)([-*+]|\d+[.)])\s+(.*)$")
RE_TAB = re.compile(r"^\s*\|.*\|\s*$")


def ler_atributos(texto: str | None) -> tuple[str, list, dict]:
    """'#fig-x .classe largura=80%' -> ('fig-x', ['classe'], {'largura': '80%'})."""
    ident, classes, chaves = "", [], {}
    if not texto:
        return ident, classes, chaves
    for parte in shlex.split(texto):
        if parte.startswith("#"):
            ident = parte[1:]
        elif parte.startswith("."):
            classes.append(parte[1:])
        elif "=" in parte:
            k, v = parte.split("=", 1)
            chaves[k.strip()] = v.strip()
    return ident, classes, chaves


def separar_cabecalho(texto: str) -> tuple[dict, str, int]:
    """Separa o YAML do topo. Devolve (metadados, corpo, nº da 1ª linha do corpo)."""
    linhas = texto.split("\n")
    if not linhas or linhas[0].strip() != "---":
        raise ErroRelatorio("O relatorio_pi.md precisa começar com o cabeçalho YAML entre linhas '---'.")
    for i in range(1, len(linhas)):
        if linhas[i].strip() == "---":
            try:
                meta = yaml.safe_load("\n".join(linhas[1:i])) or {}
            except yaml.YAMLError as e:
                raise ErroRelatorio(f"Erro no cabeçalho YAML do relatorio_pi.md: {e}") from e
            return meta, "\n".join(linhas[i + 1:]), i + 2
    raise ErroRelatorio("O cabeçalho YAML do relatorio_pi.md não foi fechado com uma linha '---'.")


def sem_comentarios(texto: str) -> str:
    """Remove <!-- comentários --> mantendo a contagem de linhas (para as mensagens de erro)."""
    return re.sub(r"<!--.*?-->", lambda m: "\n" * m.group(0).count("\n"), texto, flags=re.S)


def _inicia_bloco(linha: str) -> bool:
    return bool(RE_TITULO.match(linha) or RE_DIV_ABRE.match(linha) or RE_DIV_FECHA.match(linha)
                or RE_CERCA.match(linha) or RE_FIGURA.match(linha) or RE_LEGENDA_TAB.match(linha)
                or RE_EQUACAO.match(linha) or RE_ITEM.match(linha) or RE_TAB.match(linha))


def ler_blocos(linhas: list[str], inicio: int = 1) -> list[Bloco]:
    """Converte as linhas do corpo numa lista de blocos. `inicio` = nº da 1ª linha no arquivo."""
    blocos: list[Bloco] = []
    i, n = 0, len(linhas)
    while i < n:
        linha = linhas[i]
        num = inicio + i
        if not linha.strip():
            i += 1
            continue

        m = RE_CERCA.match(linha)
        if m:
            cerca, info = m.group(1), m.group(2).strip()
            j = i + 1
            while j < n and not linhas[j].strip().startswith(cerca):
                j += 1
            if j >= n:
                raise ErroRelatorio(f"Linha {num}: bloco de código aberto com {cerca} e nunca fechado.")
            partes = info.split(maxsplit=1)
            lingua = partes[0] if partes else ""
            _, _, chaves = ler_atributos(partes[1] if len(partes) > 1 else "")
            blocos.append(Bloco("codigo", num, texto="\n".join(linhas[i + 1:j]), id=lingua, attrs=chaves))
            i = j + 1
            continue

        m = RE_TITULO.match(linha)
        if m:
            ident, classes, chaves = ler_atributos(m.group(3))
            blocos.append(Bloco("titulo", num, texto=m.group(2).strip(), nivel=len(m.group(1)),
                                classes=classes, id=ident, attrs=chaves))
            i += 1
            continue

        m = RE_DIV_ABRE.match(linha)
        if m:
            ident, classes, chaves = ler_atributos(m.group(2))
            nome = m.group(3) or (classes[0] if classes else "")
            if ident == "refs":
                nome = "refs"
            j, profundidade = i + 1, 1
            while j < n:
                if RE_DIV_FECHA.match(linhas[j]):
                    profundidade -= 1
                    if profundidade == 0:
                        break
                elif RE_DIV_ABRE.match(linhas[j]):
                    profundidade += 1
                j += 1
            if j >= n:
                raise ErroRelatorio(f"Linha {num}: bloco '::: {nome}' aberto e nunca fechado com ':::'.")
            filhos = ler_blocos(linhas[i + 1:j], inicio + i + 1)
            blocos.append(Bloco("div", num, texto=nome, id=ident, classes=classes, attrs=chaves, filhos=filhos))
            i = j + 1
            continue

        if RE_DIV_FECHA.match(linha):
            raise ErroRelatorio(f"Linha {num}: ':::' fechando um bloco que não foi aberto.")

        m = RE_FIGURA.match(linha)
        if m:
            legenda, alvo = m.group(1).strip(), m.group(2).strip()
            ident, classes, chaves = ler_atributos(m.group(3))
            if alvo.startswith("#"):
                ident = ident or alvo[1:]
            if not ident.startswith("fig-"):
                raise ErroRelatorio(f"Linha {num}: a figura precisa de um rótulo começando com 'fig-' "
                                    f"(ex.: ![Legenda](#fig-nome) ou {{#fig-nome}} depois do arquivo).")
            blocos.append(Bloco("figura", num, texto=legenda, id=ident, classes=classes, attrs=chaves,
                                itens=[alvo]))
            i += 1
            continue

        m = RE_LEGENDA_TAB.match(linha)
        if m:
            ident, classes, chaves = ler_atributos(m.group(2))
            j = i + 1
            while j < n and not linhas[j].strip():
                j += 1
            corpo = []
            while j < n and RE_TAB.match(linhas[j]):
                corpo.append(linhas[j].strip())
                j += 1
            blocos.append(Bloco("tabela", num, texto=m.group(1).strip(), id=ident, classes=classes,
                                attrs=chaves, itens=corpo))
            i = j if corpo else i + 1
            continue

        m = RE_EQUACAO.match(linha)
        if m:
            ident, classes, chaves = ler_atributos(m.group(2))
            blocos.append(Bloco("equacao", num, texto=m.group(1).strip(), id=ident, attrs=chaves))
            i += 1
            continue

        if RE_TAB.match(linha):
            raise ErroRelatorio(f"Linha {num}: tabela sem legenda. Coloque antes dela uma linha "
                                f"': Título da tabela {{#tbl-nome}}'.")

        m = RE_ITEM.match(linha)
        if m:
            ordenada = m.group(2)[0].isdigit()
            itens = []
            j = i
            while j < n:
                mm = RE_ITEM.match(linhas[j])
                if mm:
                    nivel = 1 if len(mm.group(1).expandtabs(4)) >= 2 else 0
                    itens.append([nivel, mm.group(3).strip()])
                    j += 1
                    continue
                if linhas[j].strip() and not _inicia_bloco(linhas[j]):
                    itens[-1][1] += " " + linhas[j].strip()   # continuação do item
                    j += 1
                    continue
                if not linhas[j].strip():
                    k = j
                    while k < n and not linhas[k].strip():
                        k += 1
                    if k < n and RE_ITEM.match(linhas[k]):
                        j = k
                        continue
                break
            blocos.append(Bloco("lista", num, ordenada=ordenada, itens=[tuple(x) for x in itens]))
            i = j
            continue

        # parágrafo: junta linhas até uma linha em branco ou o início de outro bloco
        partes = [linha.strip()]
        j = i + 1
        while j < n and linhas[j].strip() and not _inicia_bloco(linhas[j]):
            partes.append(linhas[j].strip())
            j += 1
        blocos.append(Bloco("paragrafo", num, texto=" ".join(partes)))
        i = j
    return blocos


def ler_relatorio(caminho) -> tuple[dict, list[Bloco]]:
    texto = open(caminho, encoding="utf-8").read().replace("\r\n", "\n").lstrip("﻿")
    meta, corpo, inicio = separar_cabecalho(texto)
    corpo = sem_comentarios(corpo)
    return meta, ler_blocos(corpo.split("\n"), inicio)


# ----------------------------------------------------------------------------- texto corrido
@dataclass
class Trecho:
    tipo: str                      # texto, cit, ref, link
    texto: str = ""
    fmt: frozenset = frozenset()   # 'b' negrito, 'i' itálico, 'code', 'sup', 'sub'
    itens: list = None             # citação: [(chave, localizador)]
    narrativa: bool = False
    alvo: str = ""                 # rótulo (@fig-x) ou endereço do link


RE_INLINE = re.compile(r"""
  (?P<esc>\\[\\`*_{}\[\]()#+\-.!@^~|<>$:])
| (?P<crase>`+)(?P<code>.+?)(?P=crase)
| <(?P<auto>https?://[^>\s]+)>
| \[(?P<cit>@[^\]]+)\]
| \[(?P<lk_txt>[^\]]+)\]\((?P<lk_url>[^)\s]+)\)
| \*\*(?P<b>.+?)\*\*
| (?<![\w*])\*(?P<i>[^\s*](?:[^*]*?[^\s*])??)\*(?![\w*])
| (?<![\w_])_(?P<i2>[^\s_](?:[^_]*?[^\s_])??)_(?![\w_])
| \^(?P<sup>[^\s^][^^]*?)\^
| ~(?P<sub>[^\s~][^~]*?)~
| (?<![\w@./])@(?P<chave>[A-Za-z0-9_][\w:-]*\w)(?:\s?\[(?P<loc>[^\]@]+)\])?
""", re.X)

PREFIXOS_REF = ("fig-", "tbl-", "sec-", "eq-")


def ler_citacoes(conteudo: str, linha: int) -> list[tuple[str, str]]:
    itens = []
    for parte in conteudo.split(";"):
        parte = parte.strip()
        m = re.match(r"^@([\w:-]+)\s*(?:,\s*(.+))?$", parte)
        if not m:
            raise ErroRelatorio(f"Linha {linha}: citação mal escrita: [{conteudo}]. "
                                f"Use [@chave], [@chave, p. 12] ou [@a; @b].")
        itens.append((m.group(1), (m.group(2) or "").strip()))
    return itens


def ler_inline(texto: str, linha: int = 0, fmt: frozenset = frozenset()) -> list[Trecho]:
    out: list[Trecho] = []
    pos = 0

    def texto_puro(s):
        if s:
            if out and out[-1].tipo == "texto" and out[-1].fmt == fmt:
                out[-1].texto += s
            else:
                out.append(Trecho("texto", s, fmt))

    for m in RE_INLINE.finditer(texto):
        texto_puro(texto[pos:m.start()])
        pos = m.end()
        g = m.groupdict()
        if g["esc"]:
            texto_puro(g["esc"][1])
        elif g["code"] is not None:
            out.append(Trecho("texto", g["code"].strip(), fmt | {"code"}))
        elif g["auto"]:
            out.append(Trecho("link", g["auto"], fmt, alvo=g["auto"]))
        elif g["cit"]:
            out.append(Trecho("cit", fmt=fmt, itens=ler_citacoes(g["cit"], linha)))
        elif g["lk_txt"]:
            out.append(Trecho("link", g["lk_txt"], fmt, alvo=g["lk_url"]))
        elif g["b"]:
            out.extend(ler_inline(g["b"], linha, fmt | {"b"}))
        elif g["i"] or g["i2"]:
            out.extend(ler_inline(g["i"] or g["i2"], linha, fmt | {"i"}))
        elif g["sup"]:
            out.extend(ler_inline(g["sup"], linha, fmt | {"sup"}))
        elif g["sub"]:
            out.extend(ler_inline(g["sub"], linha, fmt | {"sub"}))
        elif g["chave"]:
            chave = g["chave"]
            if chave.startswith(PREFIXOS_REF):
                out.append(Trecho("ref", fmt=fmt, alvo=chave))
                if g["loc"]:
                    texto_puro(" [" + g["loc"] + "]")
            else:
                out.append(Trecho("cit", fmt=fmt, itens=[(chave, (g["loc"] or "").strip())], narrativa=True))
    texto_puro(texto[pos:])
    return out


def texto_simples(trechos: list[Trecho]) -> str:
    """Texto sem formatação (para o sumário e as listas)."""
    return "".join(t.texto for t in trechos if t.tipo in ("texto", "link"))


def substituir_valores(texto: str, valores: dict, linha: int) -> str:
    def troca(m):
        nome = m.group(1).strip()
        if nome not in valores:
            raise ErroRelatorio(f"Linha {linha}: o valor {{{{{nome}}}}} não existe em relatorio/valores.py.")
        return str(valores[nome])
    return re.sub(r"\{\{\s*([\w.-]+)\s*\}\}", troca, texto)
