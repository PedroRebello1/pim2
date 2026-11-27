"""refs.bib -> citações (NBR 10520:2023) e lista de referências (NBR 6023:2018).

Segue as escolhas do estilo ABNT do modelo do professor:
- citação: (Sobrenome, ano), (A; B; C, ano), (Sobrenome et al., ano) a partir de 4 autores;
  no texto: Sobrenome (ano), A, B e C (ano), Sobrenome et al. (ano);
- referência: SOBRENOME, Prenome; ... ou SOBRENOME, Prenome et al. a partir de 4 autores;
  título principal em negrito; expressões latinas (In:, et al., [S. l.], [s. n.]) em itálico;
- mesmo autor e mesmo ano: 2024a, 2024b;
- só entram na lista as obras citadas no texto, em ordem alfabética.

Tipos aceitos no refs.bib: @book, @article, @inproceedings, @online e @legislation
(veja os exemplos comentados no próprio refs.bib). Faz parte do padrão: não edite.
"""
from __future__ import annotations

import re
import unicodedata

from .markdown import ErroRelatorio

ITALICO = frozenset({"i"})
NEGRITO = frozenset({"b"})
NORMAL = frozenset()
MESES = ["jan.", "fev.", "mar.", "abr.", "maio", "jun.", "jul.", "ago.", "set.", "out.", "nov.", "dez."]


# ----------------------------------------------------------------------------- leitura do .bib
def _valor(texto: str, i: int) -> tuple[str, int]:
    """Lê um valor de campo a partir de texto[i]: {…} (com chaves aninhadas), "…" ou número."""
    while texto[i].isspace():
        i += 1
    if texto[i] == "{":
        nivel, j = 0, i
        while j < len(texto):
            if texto[j] == "{":
                nivel += 1
            elif texto[j] == "}":
                nivel -= 1
                if nivel == 0:
                    return texto[i + 1:j], j + 1
            j += 1
        raise ErroRelatorio("refs.bib: chave '{' sem fechamento.")
    if texto[i] == '"':
        j = texto.index('"', i + 1)
        return texto[i + 1:j], j + 1
    m = re.match(r"[\w.-]+", texto[i:])
    return m.group(0), i + m.end()


def ler_bib(caminho) -> dict[str, dict]:
    texto = open(caminho, encoding="utf-8").read()
    texto = "\n".join(l for l in texto.split("\n") if not l.lstrip().startswith("%"))  # comentários
    obras = {}
    for m in re.finditer(r"@(\w+)\s*\{\s*([^,\s]+)\s*,", texto):
        tipo, chave = m.group(1).lower(), m.group(2)
        if tipo in ("comment", "string", "preamble"):
            continue
        i, campos = m.end(), {"tipo": tipo, "chave": chave}
        while True:
            mm = re.match(r"\s*(\w+)\s*=", texto[i:])
            if not mm:
                break
            nome = mm.group(1).lower()
            valor, i = _valor(texto, i + mm.end())
            valor = valor.replace("\\&", "&").replace("\\%", "%").replace("\\_", "_").replace("--", "-")
            campos[nome] = " ".join(valor.split())
            mm = re.match(r"\s*,", texto[i:])
            if not mm:
                break
            i += mm.end()
        if chave in obras:
            raise ErroRelatorio(f"refs.bib: a chave '{chave}' aparece duas vezes.")
        obras[chave] = campos
    return obras


def _sem_chaves(s: str) -> str:
    return s.replace("{", "").replace("}", "")


def autores(campo: str) -> list[dict]:
    """'Hosmer, David W. and Lemeshow, Stanley' -> [{'sobrenome','prenome','instituicao'}].

    'and others' no fim (lista incompleta de autores) conta como 4 ou mais autores (et al.).
    """
    lista = []
    nomes = re.split(r"\s+and\s+", campo.strip())
    if nomes and nomes[-1].strip().lower() == "others":
        nomes = nomes[:-1]
        while len(nomes) < 4:
            nomes.append("{et al.}")
    for nome in nomes:
        if nome.startswith("{") and nome.endswith("}"):        # autor institucional: {BRASIL}
            lista.append({"sobrenome": _sem_chaves(nome), "prenome": "", "instituicao": True})
        elif "," in nome:
            sobrenome, prenome = nome.split(",", 1)
            lista.append({"sobrenome": _sem_chaves(sobrenome).strip(), "prenome": _sem_chaves(prenome).strip(),
                          "instituicao": False})
        else:
            partes = _sem_chaves(nome).split()
            lista.append({"sobrenome": partes[-1], "prenome": " ".join(partes[:-1]), "instituicao": False})
    return lista


def _ordem(s: str) -> str:
    return unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode().upper()


# ----------------------------------------------------------------------------- bibliografia
class Bibliografia:
    def __init__(self, caminho):
        self.obras = ler_bib(caminho)
        self.citadas: list[str] = []
        self._sufixo: dict[str, str] = {}

    # -- uso no texto
    def registrar(self, chave: str, linha: int):
        if chave not in self.obras:
            raise ErroRelatorio(f"Linha {linha}: a obra @{chave} não está no refs.bib.")
        if chave not in self.citadas:
            self.citadas.append(chave)

    def preparar(self):
        """Depois de registrar todas as citações: resolve 2024a/2024b."""
        grupos: dict[tuple, list] = {}
        for chave in self.citadas:
            o = self.obras[chave]
            grupos.setdefault((self._rotulo(o), o.get("year", "s.d.")), []).append(chave)
        for chaves in grupos.values():
            if len(chaves) > 1:
                for letra, chave in zip("abcdefghij", sorted(chaves, key=lambda c: _ordem(self.obras[c].get("title", "")))):
                    self._sufixo[chave] = letra

    def _rotulo(self, o) -> str:
        """Nome usado na citação: Sobrenome, 'A; B; C' ou 'Sobrenome et al.' (sem formatação)."""
        nomes = autores(o.get("author", "{Anônimo}"))
        return "; ".join(self._nome_citacao(a) for a in nomes[:3]) if len(nomes) <= 3 else self._nome_citacao(nomes[0])

    @staticmethod
    def _nome_citacao(a: dict) -> str:
        if a["instituicao"]:
            return a["sobrenome"][:1].upper() + a["sobrenome"][1:].lower()
        return a["sobrenome"]

    def ano(self, chave: str) -> str:
        o = self.obras[chave]
        return o.get("year", "s.d.") + self._sufixo.get(chave, "")

    def citacao(self, itens: list[tuple[str, str]], narrativa: bool) -> list[tuple[str, frozenset]]:
        """Trechos (texto, formatação) de uma citação; 'et al.' sai em itálico."""
        out: list[tuple[str, frozenset]] = []
        if narrativa:
            for k, (chave, loc) in enumerate(itens):
                if k:
                    out.append(("; ", NORMAL))
                nomes = autores(self.obras[chave].get("author", "{Anônimo}"))
                if len(nomes) >= 4:
                    out += [(self._nome_citacao(nomes[0]) + " ", NORMAL), ("et al.", ITALICO)]
                elif len(nomes) == 1:
                    out.append((self._nome_citacao(nomes[0]), NORMAL))
                else:
                    ns = [self._nome_citacao(a) for a in nomes]
                    out.append((", ".join(ns[:-1]) + " e " + ns[-1], NORMAL))
                out.append((f" ({self.ano(chave)}{', ' + loc if loc else ''})", NORMAL))
            return out
        out.append(("(", NORMAL))
        for k, (chave, loc) in enumerate(itens):
            if k:
                out.append(("; ", NORMAL))
            nomes = autores(self.obras[chave].get("author", "{Anônimo}"))
            if len(nomes) >= 4:
                out += [(self._nome_citacao(nomes[0]) + " ", NORMAL), ("et al.", ITALICO)]
            else:
                out.append(("; ".join(self._nome_citacao(a) for a in nomes), NORMAL))
            out.append((f", {self.ano(chave)}{', ' + loc if loc else ''}", NORMAL))
        out.append((")", NORMAL))
        return out

    # -- lista de referências
    def _autoria(self, o) -> list[tuple[str, frozenset]]:
        nomes = autores(o.get("author", "{Anônimo}"))

        def um(a):
            if a["instituicao"]:
                return a["sobrenome"].upper()
            return f"{a['sobrenome'].upper()}, {a['prenome']}" if a["prenome"] else a["sobrenome"].upper()
        if len(nomes) >= 4:
            return [(um(nomes[0]) + " ", NORMAL), ("et al.", ITALICO), (" ", NORMAL)]
        texto = "; ".join(um(a) for a in nomes)
        return [(texto + ("" if texto.endswith(".") else ".") + " ", NORMAL)]

    @staticmethod
    def _acesso(o) -> list[tuple[str, frozenset]]:
        out = []
        if o.get("url"):
            out.append((f" Disponível em: {o['url']}.", NORMAL))
        if o.get("urldate"):
            a, m, d = (int(x) for x in o["urldate"].split("-"))
            out.append((f" Acesso em: {d} {MESES[m - 1]} {a}.", NORMAL))
        return out

    @staticmethod
    def _imprenta(o, ano: str) -> list[tuple[str, frozenset]]:
        """Local: Editora, ano. -> com [S. l.] e [s. n.] em itálico quando faltarem."""
        local, editora = o.get("address", ""), o.get("publisher", "")
        out = []
        if local and editora:
            out.append((f"{local}: {editora}, {ano}.", NORMAL))
        elif local:
            out += [(f"{local}: [", NORMAL), ("s. n.", ITALICO), (f"], {ano}.", NORMAL)]
        elif editora:
            out += [("[", NORMAL), ("S. l.", ITALICO), (f"]: {editora}, {ano}.", NORMAL)]
        else:
            out += [("[", NORMAL), ("S. l.: s. n.", ITALICO), (f"], {ano}.", NORMAL)]
        return out

    def referencia(self, chave: str) -> list[tuple[str, frozenset]]:
        # chaves que protegem maiúsculas no BibTeX ({ABECS}, {B}ayesian) não aparecem na referência;
        # o autor fica como está, porque {BRASIL} indica autor institucional
        o = {k: (v if k == "author" else _sem_chaves(v)) for k, v in self.obras[chave].items()}
        tipo = o["tipo"]
        ano = o.get("yeardisplay", o.get("year", "[s. d.]")) + self._sufixo.get(chave, "")
        out = self._autoria(o)
        titulo, sub = o.get("title", ""), o.get("subtitle", "")
        ed = f" {o['edition']}. ed." if o.get("edition") else ""

        if tipo == "book":
            out += [(titulo, NEGRITO), ((": " + sub) if sub else "", NORMAL), (".", NORMAL)]
            out += [(ed + " ", NORMAL)] + self._imprenta(o, ano)
        elif tipo == "article":
            out += [(titulo + (": " + sub if sub else "") + ". ", NORMAL), (o.get("journal", ""), NEGRITO)]
            partes = [f"v. {o['volume']}" if o.get("volume") else "", f"n. {o['number']}" if o.get("number") else "",
                      o.get("note", ""), f"p. {o['pages']}" if o.get("pages") else "", ano]
            out.append((", " + ", ".join(p for p in partes if p) + ".", NORMAL))
        elif tipo == "inproceedings":
            evento = o.get("eventtitle", "").upper()
            num = f", {o['eventnumber']}." if o.get("eventnumber") else ""
            out += [(titulo + (": " + sub if sub else "") + ". ", NORMAL), ("In", ITALICO),
                    (f": {evento}{num}, {o.get('eventyear', o.get('year', ''))}, {o.get('venue', '')}. ", NORMAL),
                    (o.get("booktitle", "Anais"), NEGRITO), (" [...]. ", NORMAL)]
            out += self._imprenta(o, ano)
            if o.get("pages"):
                out.append((f" p. {o['pages']}.", NORMAL))
        elif tipo == "online":
            out += [(titulo, NEGRITO), ((": " + sub) if sub else "", NORMAL), (". ", NORMAL)]
            out += self._imprenta(o, ano)
        elif tipo == "legislation":
            out += [(titulo + ". ", NORMAL)]
            if o.get("note"):
                out.append((o["note"].rstrip(".") + ". ", NORMAL))
            out += self._imprenta(o, ano)
        else:
            raise ErroRelatorio(f"refs.bib: tipo @{tipo} (chave {chave}) não é aceito. "
                                f"Use @book, @article, @inproceedings, @online ou @legislation.")
        out += self._acesso(o)
        # junta trechos vizinhos com a mesma formatação e tira espaços duplos
        limpo: list[tuple[str, frozenset]] = []
        for texto, fmt in out:
            if not texto:
                continue
            if limpo and limpo[-1][1] == fmt:
                limpo[-1] = (limpo[-1][0] + texto, fmt)
            else:
                limpo.append((texto, fmt))
        return [(re.sub(r"\s{2,}", " ", t).replace(" .", "."), f) for t, f in limpo]

    def lista(self) -> list[list[tuple[str, frozenset]]]:
        def ordem(chave):
            o = self.obras[chave]
            a = autores(o.get("author", "{Anônimo}"))[0]
            return (_ordem(a["sobrenome"]), _ordem(a["prenome"]), self.ano(chave), _ordem(o.get("title", "")))
        return [self.referencia(c) for c in sorted(self.citadas, key=ordem)]
