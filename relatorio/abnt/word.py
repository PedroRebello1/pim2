"""Monta o relatório no Word (.docx) no padrão ABNT do curso.

Equivale à extensão pi-abnt do modelo do professor (abnt.tex + before-body.tex + abnt.lua):
- página A4, margens 3/3/2/2 cm, Times New Roman 12, entrelinha 1,5, recuo de 1,25 cm (NBR 14724);
- capa com o logo do CEUB, folha de rosto e folha de aprovação opcional, preenchidas pelo YAML;
- títulos numerados: 1 PRIMÁRIA (negrito, maiúsculas), 1.1 Secundária (negrito),
  1.1.1 Terciária (normal), 1.1.1.1 Quaternária (itálico) (NBR 6024);
- lista de figuras, lista de tabelas e sumário com linha pontilhada (NBR 6027);
- paginação contada desde a folha de rosto e exibida a partir da Introdução, no canto superior direito;
- legendas "Figura 1 – Título" acima, "Fonte: ..." abaixo, em letra menor;
- citação direta longa com recuo de 4 cm; resumo em parágrafo único com entrelinha simples;
- referências alinhadas à esquerda, entrelinha simples, uma linha em branco entre elas.

Faz parte do padrão: não edite. O conteúdo fica no relatorio_pi.md.
"""
from __future__ import annotations

import ast
from pathlib import Path

from docx import Document
from docx.enum.section import WD_SECTION
from docx.enum.style import WD_STYLE_TYPE
from docx.enum.table import WD_CELL_VERTICAL_ALIGNMENT, WD_ROW_HEIGHT_RULE, WD_TABLE_ALIGNMENT
from docx.enum.text import WD_ALIGN_PARAGRAPH, WD_BREAK, WD_LINE_SPACING, WD_TAB_ALIGNMENT, WD_TAB_LEADER
from docx.opc.constants import RELATIONSHIP_TYPE as RT
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Cm, Pt, RGBColor

from .markdown import (Bloco, ErroRelatorio, Trecho, ler_inline, substituir_valores, texto_simples)
from .tabela import TabelaABNT

FONTE = "Times New Roman"
FONTE_CODIGO = "Courier New"
LARGURA_UTIL_CM = 16.0          # 21 cm - 3 cm - 2 cm
ALTURA_UTIL_CM = 24.7           # 29,7 cm - 3 cm - 2 cm
PEQUENA = 10                    # letra menor (legendas, fontes, citações longas, tabelas, paginação)
TAMANHO_CODIGO = 7.5            # blocos de código (Apêndice)
# Caracteres por linha de código: o Courier New tem largura fixa de 0,6 em (4,5 pt a 7,5 pt), então
# cabem 100 na largura útil; 2 de folga para o Word e o LibreOffice não quebrarem a linha sozinhos.
LARGURA_CODIGO = int(LARGURA_UTIL_CM / 2.54 * 72 / (0.6 * TAMANHO_CODIGO)) - 2
RESUMOS = {"resumo", "abstract", "resumen"}
PALAVRAS_CHAVE = ("palavras-chave", "keywords", "palabras clave")
ALINHA = {"esq": WD_ALIGN_PARAGRAPH.LEFT, "dir": WD_ALIGN_PARAGRAPH.RIGHT, "centro": WD_ALIGN_PARAGRAPH.CENTER}


# ============================================================================= XML auxiliar
# Ordem dos filhos exigida pelo esquema OOXML (o Word recusa arquivos fora de ordem).
ORDEM_PPR = ["w:pStyle", "w:keepNext", "w:keepLines", "w:pageBreakBefore", "w:framePr", "w:widowControl",
             "w:numPr", "w:suppressLineNumbers", "w:pBdr", "w:shd", "w:tabs", "w:suppressAutoHyphens", "w:kinsoku",
             "w:wordWrap", "w:overflowPunct", "w:topLinePunct", "w:autoSpaceDE", "w:autoSpaceDN", "w:bidi",
             "w:adjustRightInd", "w:snapToGrid", "w:spacing", "w:ind", "w:contextualSpacing", "w:mirrorIndents",
             "w:suppressOverlap", "w:jc", "w:textDirection", "w:textAlignment", "w:textboxTightWrap",
             "w:outlineLvl", "w:divId", "w:cnfStyle", "w:rPr", "w:sectPr", "w:pPrChange"]
ORDEM_RPR = ["w:rStyle", "w:rFonts", "w:b", "w:bCs", "w:i", "w:iCs", "w:caps", "w:smallCaps", "w:strike",
             "w:dstrike", "w:outline", "w:shadow", "w:emboss", "w:imprint", "w:noProof", "w:snapToGrid", "w:vanish",
             "w:webHidden", "w:color", "w:spacing", "w:w", "w:kern", "w:position", "w:sz", "w:szCs", "w:highlight",
             "w:u", "w:effect", "w:bdr", "w:shd", "w:fitText", "w:vertAlign", "w:rtl", "w:cs", "w:em", "w:lang",
             "w:eastAsianLayout", "w:specVanish", "w:oMath"]
ORDEM_TCPR = ["w:cnfStyle", "w:tcW", "w:gridSpan", "w:hMerge", "w:vMerge", "w:tcBorders", "w:shd", "w:noWrap",
              "w:tcMar", "w:textDirection", "w:tcFitText", "w:vAlign", "w:hideMark", "w:headers", "w:cellIns",
              "w:cellDel", "w:cellMerge", "w:tcPrChange"]
ORDEM_TBLPR = ["w:tblStyle", "w:tblpPr", "w:tblOverlap", "w:bidiVisual", "w:tblStyleRowBandSize",
               "w:tblStyleColBandSize", "w:tblW", "w:jc", "w:tblCellSpacing", "w:tblInd", "w:tblBorders", "w:shd",
               "w:tblLayout", "w:tblCellMar", "w:tblLook", "w:tblCaption", "w:tblDescription", "w:tblPrChange"]
ORDEM_SECTPR = ["w:headerReference", "w:footerReference", "w:footnotePr", "w:endnotePr", "w:type", "w:pgSz",
                "w:pgMar", "w:paperSrc", "w:pgBorders", "w:lnNumType", "w:pgNumType", "w:cols", "w:formProt",
                "w:vAlign", "w:noEndnote", "w:titlePg", "w:textDirection", "w:bidi", "w:rtlGutter", "w:docGrid",
                "w:printerSettings", "w:sectPrChange"]


def _inserir(pai, el, ordem: list[str]):
    """Insere `el` em `pai` na posição exigida pelo esquema, substituindo um igual que já exista."""
    tag = el.tag
    for velho in pai.findall(tag):
        if tag != qn("w:headerReference") and tag != qn("w:footerReference"):
            pai.remove(velho)
    nomes = [qn(t) for t in ordem]
    pos = nomes.index(tag) if tag in nomes else len(nomes)
    for filho in pai:
        if filho.tag in nomes and nomes.index(filho.tag) > pos:
            filho.addprevious(el)
            return el
    pai.append(el)
    return el


def _elemento(tag: str, **attrs):
    el = OxmlElement(tag)
    for k, v in attrs.items():
        el.set(qn(k), str(v))
    return el


def _fontes(rPr, nome: str):
    """Define a fonte nas 4 faixas e remove as fontes do tema (que teriam prioridade)."""
    rf = rPr.find(qn("w:rFonts"))
    if rf is None:
        rf = _inserir(rPr, OxmlElement("w:rFonts"), ORDEM_RPR)
    for attr in ("w:asciiTheme", "w:hAnsiTheme", "w:eastAsiaTheme", "w:cstheme"):
        if rf.get(qn(attr)) is not None:
            del rf.attrib[qn(attr)]
    for attr in ("w:ascii", "w:hAnsi", "w:eastAsia", "w:cs"):
        rf.set(qn(attr), nome)


def _cor_preta(rPr):
    cor = rPr.find(qn("w:color"))
    if cor is not None:
        rPr.remove(cor)


def _anexar_pPr(pPr, tag: str, **attrs):
    """Acrescenta (ou substitui) um filho simples de w:pPr, respeitando a ordem do esquema."""
    return _inserir(pPr, _elemento(tag, **attrs), ORDEM_PPR)


def _marca_minima(par):
    """Parágrafo vazio de 1 pt (quebras de seção e fim de célula), para não empurrar página."""
    par.paragraph_format.line_spacing = Pt(1)
    par.paragraph_format.line_spacing_rule = WD_LINE_SPACING.EXACTLY
    par.paragraph_format.space_before = Pt(0)
    par.paragraph_format.space_after = Pt(0)
    rPr = _inserir(par._p.get_or_add_pPr(), OxmlElement("w:rPr"), ORDEM_PPR)
    _inserir(rPr, _elemento("w:sz", **{"w:val": 2}), ORDEM_RPR)
    _inserir(rPr, _elemento("w:szCs", **{"w:val": 2}), ORDEM_RPR)


def _borda(pai, lado: str, valor="single", tamanho=8, cor="000000"):
    el = pai.find(qn(f"w:{lado}"))
    if el is None:
        el = OxmlElement(f"w:{lado}")
        pai.append(el)
    el.set(qn("w:val"), valor)
    el.set(qn("w:sz"), str(tamanho))
    el.set(qn("w:space"), "0")
    el.set(qn("w:color"), cor)


def _bordas_tabela(tabela, topo=True, base=True):
    tblPr = tabela._tbl.tblPr
    bordas = tblPr.find(qn("w:tblBorders"))
    if bordas is None:
        bordas = _inserir(tblPr, OxmlElement("w:tblBorders"), ORDEM_TBLPR)
    for lado in ("top", "left", "bottom", "right", "insideH", "insideV"):
        _borda(bordas, lado, "nil", 0, "auto")
    if topo:
        _borda(bordas, "top", "single", 8)
    if base:
        _borda(bordas, "bottom", "single", 8)


def _borda_celula(celula, lado="bottom", tamanho=4):
    tcPr = celula._tc.get_or_add_tcPr()
    bordas = tcPr.find(qn("w:tcBorders"))
    if bordas is None:
        bordas = _inserir(tcPr, OxmlElement("w:tcBorders"), ORDEM_TCPR)
    _borda(bordas, lado, "single", tamanho)


def _sem_bordas(tabela):
    _bordas_tabela(tabela, topo=False, base=False)


def _campo(par, instrucao: str, resultado: str = "", tamanho=None):
    """Campo do Word num parágrafo (PAGE, SEQ...). `resultado` é o valor já calculado."""
    def r(filho):
        run = par.add_run()
        if tamanho:
            run.font.size = Pt(tamanho)
        run._r.append(filho)
        return run
    b = OxmlElement("w:fldChar")
    b.set(qn("w:fldCharType"), "begin")
    r(b)
    it = OxmlElement("w:instrText")
    it.set(qn("xml:space"), "preserve")
    it.text = f" {instrucao} "
    r(it)
    s = OxmlElement("w:fldChar")
    s.set(qn("w:fldCharType"), "separate")
    r(s)
    res = par.add_run(resultado)
    if tamanho:
        res.font.size = Pt(tamanho)
    e = OxmlElement("w:fldChar")
    e.set(qn("w:fldCharType"), "end")
    r(e)


def quebrar_codigo(linha: str, largura: int = LARGURA_CODIGO) -> list[str]:
    """Quebra uma linha de código longa em pedaços de até `largura` caracteres.

    Cada continuação recebe o recuo da própria linha + 4 espaços. Sem isso, o Word e o LibreOffice
    devolvem o resto da linha para a margem esquerda e a indentação do Python fica ilegível.
    A quebra é feita no último espaço que cabe; um trecho sem espaço é cortado na largura.
    """
    if len(linha) <= largura:
        return [linha]
    recuo = len(linha) - len(linha.lstrip(" "))
    continuacao = " " * (recuo + 4 if recuo + 4 <= largura // 2 else 4)
    partes, resto, minimo = [], linha, recuo + 1
    while len(resto) > largura:
        corte = resto.rfind(" ", minimo, largura + 1)
        if corte < minimo:
            corte = largura
        partes.append(resto[:corte].rstrip())
        resto = continuacao + resto[corte:].lstrip(" ")
        minimo = len(continuacao) + 1
    partes.append(resto)
    return partes


def _fldchar(par, tipo):
    run = par.add_run()
    el = OxmlElement("w:fldChar")
    el.set(qn("w:fldCharType"), tipo)
    run._r.append(el)


def _instr(par, texto):
    run = par.add_run()
    it = OxmlElement("w:instrText")
    it.set(qn("xml:space"), "preserve")
    it.text = f" {texto} "
    run._r.append(it)


# ============================================================================= documento
class DocumentoABNT:
    def __init__(self, meta: dict, valores: dict, bib, obter_figura, obter_tabela, base: Path):
        self.meta, self.valores, self.bib, self.base = meta, valores, bib, Path(base)
        self.obter_figura, self.obter_tabela = obter_figura, obter_tabela
        self.avisos: list[str] = []

    # ------------------------------------------------------------------ 1ª passada: numeração
    def numerar(self, blocos: list[Bloco]):
        """Numera seções, figuras, tabelas e equações e registra as citações (na ordem do texto)."""
        cont = [0, 0, 0, 0]
        self.rotulos: dict[str, str] = {}
        self.sumario: list[dict] = []
        self.figuras: list[dict] = []
        self.tabelas: list[dict] = []
        self.num_bloco: dict[int, str] = {}
        self.referenciados: set[str] = set()
        n_eq = 0
        self.tem_refs = False

        def textos_de(b: Bloco):
            if b.tipo in ("paragrafo", "titulo", "figura", "tabela", "equacao"):
                yield b.texto, b.linha
            if b.tipo == "lista":
                for _, t in b.itens:
                    yield t, b.linha
            if b.tipo == "tabela":
                for linha in b.itens:
                    yield linha, b.linha

        for b in self._todos(blocos):
            for texto, linha in textos_de(b):
                for t in ler_inline(self._valores(texto, linha), linha):
                    if t.tipo == "cit":
                        for chave, _ in t.itens:
                            self.bib.registrar(chave, linha)
                    elif t.tipo == "ref":
                        self.referenciados.add(t.alvo)
            if b.tipo == "titulo":
                if "pre" in b.classes:
                    continue
                if "pos" in b.classes or "unnumbered" in b.classes:
                    self.sumario.append({"nivel": 1, "numero": "", "titulo": self._titulo_simples(b, True),
                                         "pos": True, "bloco": id(b)})
                    continue
                cont[b.nivel - 1] += 1
                for k in range(b.nivel, 4):
                    cont[k] = 0
                if any(c == 0 for c in cont[:b.nivel - 1]):
                    raise ErroRelatorio(f"Linha {b.linha}: título de nível {b.nivel} sem o nível acima "
                                        f"(ex.: '###' sem um '##' antes).")
                numero = ".".join(str(c) for c in cont[:b.nivel])
                self.num_bloco[id(b)] = numero
                self.sumario.append({"nivel": b.nivel, "numero": numero, "pos": False, "bloco": id(b),
                                     "titulo": self._titulo_simples(b, b.nivel == 1)})
                if b.id:
                    self._rotulo(b.id, f"Seção {numero}", b.linha)
            elif b.tipo == "figura":
                n = len(self.figuras) + 1
                self.num_bloco[id(b)] = str(n)
                self.figuras.append({"numero": n, "titulo": self._plano(b.texto, b.linha), "id": b.id})
                self._rotulo(b.id, f"Figura {n}", b.linha)
            elif b.tipo == "tabela":
                n = len(self.tabelas) + 1
                self.num_bloco[id(b)] = str(n)
                self.tabelas.append({"numero": n, "titulo": self._plano(b.texto, b.linha), "id": b.id})
                self._rotulo(b.id, f"Tabela {n}", b.linha)
            elif b.tipo == "equacao":
                n_eq += 1
                self.num_bloco[id(b)] = str(n_eq)
                if b.id:
                    self._rotulo(b.id, f"Equação {n_eq}", b.linha)
            elif b.tipo == "div" and b.texto == "refs":
                self.tem_refs = True
        for r in sorted(self.referenciados):
            if r not in self.rotulos:
                raise ErroRelatorio(f"A referência cruzada @{r} não aponta para nenhum rótulo do relatório.")
        for item, nome in [(f, "figura") for f in self.figuras] + [(t, "tabela") for t in self.tabelas]:
            if item["id"] not in self.referenciados:
                self.avisos.append(f"A {nome} '{item['titulo']}' (@{item['id']}) não é citada no texto.")
        self.bib.preparar()

    def _rotulo(self, ident, texto, linha):
        if ident in self.rotulos:
            raise ErroRelatorio(f"Linha {linha}: o rótulo #{ident} foi usado duas vezes.")
        self.rotulos[ident] = texto

    @staticmethod
    def _todos(blocos):
        for b in blocos:
            yield b
            if b.tipo == "div":
                yield from DocumentoABNT._todos(b.filhos)

    def _valores(self, texto, linha):
        return substituir_valores(texto, self.valores, linha)

    def _plano(self, texto, linha):
        return texto_simples(ler_inline(self._valores(texto, linha), linha))

    def _titulo_simples(self, b, maiusculas):
        t = self._plano(b.texto, b.linha)
        return t.upper() if maiusculas else t

    # ------------------------------------------------------------------ estilos
    def _estilos(self):
        d = self.doc
        st = d.styles
        # padrão do documento: Times 12, português do Brasil
        padroes = st.element.find(qn("w:docDefaults"))
        rPrDef = padroes.find(qn("w:rPrDefault")).find(qn("w:rPr"))
        _fontes(rPrDef, FONTE)
        for tag in ("w:sz", "w:szCs"):
            _inserir(rPrDef, _elemento(tag, **{"w:val": 24}), ORDEM_RPR)
        _inserir(rPrDef, _elemento("w:lang", **{"w:val": "pt-BR", "w:eastAsia": "en-US", "w:bidi": "ar-SA"}), ORDEM_RPR)
        pPrDef = padroes.find(qn("w:pPrDefault"))
        if pPrDef is not None and pPrDef.find(qn("w:pPr")) is not None:
            _anexar_pPr(pPrDef.find(qn("w:pPr")), "w:spacing", **{"w:after": 0, "w:line": 240, "w:lineRule": "auto"})

        normal = st["Normal"]
        self._formatar(normal, tamanho=12, alinhamento=WD_ALIGN_PARAGRAPH.JUSTIFY, recuo=1.25,
                       entrelinha=1.5, antes=0, depois=0)
        normal.paragraph_format.widow_control = True

        def estilo(nome, base="Normal", **kw):
            try:
                s = st[nome]
            except KeyError:
                s = st.add_style(nome, WD_STYLE_TYPE.PARAGRAPH)
            s.base_style = st[base] if base else None
            s.quick_style = True
            self._formatar(s, **kw)
            return s

        # títulos numerados (NBR 6024 / folder do CEUB)
        estilo("Heading 1", tamanho=12, negrito=True, alinhamento=WD_ALIGN_PARAGRAPH.LEFT, recuo=0, antes=0,
               depois=18, com_proximo=True, quebra=True, nivel=0, italico=False)
        estilo("Heading 2", tamanho=12, negrito=True, alinhamento=WD_ALIGN_PARAGRAPH.LEFT, recuo=0, antes=18,
               depois=12, com_proximo=True, nivel=1, italico=False)
        estilo("Heading 3", tamanho=12, negrito=False, alinhamento=WD_ALIGN_PARAGRAPH.LEFT, recuo=0, antes=18,
               depois=12, com_proximo=True, nivel=2, italico=False)
        estilo("Heading 4", tamanho=12, negrito=False, italico=True, alinhamento=WD_ALIGN_PARAGRAPH.LEFT, recuo=0,
               antes=18, depois=12, com_proximo=True, nivel=3)
        # títulos sem número: pré-textuais (fora do sumário) e pós-textuais (no sumário)
        estilo("Titulo pre-textual", tamanho=12, negrito=True, alinhamento=WD_ALIGN_PARAGRAPH.CENTER, recuo=0,
               antes=0, depois=24, com_proximo=True, quebra=True)
        estilo("Titulo pos-textual", tamanho=12, negrito=True, alinhamento=WD_ALIGN_PARAGRAPH.CENTER, recuo=0,
               antes=0, depois=24, com_proximo=True, quebra=True, nivel=0)
        estilo("Resumo", entrelinha=1.0, recuo=0, depois=12)
        estilo("Caption", tamanho=PEQUENA, negrito=False, italico=False, alinhamento=WD_ALIGN_PARAGRAPH.CENTER,
               recuo=0, entrelinha=1.0, antes=12, depois=4, com_proximo=True)
        estilo("Fonte", tamanho=PEQUENA, alinhamento=WD_ALIGN_PARAGRAPH.CENTER, recuo=0, entrelinha=1.0,
               antes=4, depois=12)
        estilo("Figura", alinhamento=WD_ALIGN_PARAGRAPH.CENTER, recuo=0, entrelinha=1.0, antes=0, depois=0,
               com_proximo=True)
        estilo("Citacao longa", tamanho=PEQUENA, recuo=0, esquerda=4.0, entrelinha=1.0, antes=12, depois=12)
        estilo("Referencia", alinhamento=WD_ALIGN_PARAGRAPH.LEFT, recuo=0, entrelinha=1.0, antes=0, depois=12)
        estilo("Texto de tabela", tamanho=PEQUENA, alinhamento=WD_ALIGN_PARAGRAPH.LEFT, recuo=0, entrelinha=1.0,
               antes=1, depois=1)
        estilo("Codigo", fonte=FONTE_CODIGO, tamanho=TAMANHO_CODIGO, alinhamento=WD_ALIGN_PARAGRAPH.LEFT, recuo=0,
               entrelinha=1.0, antes=0, depois=0)
        estilo("Equacao", alinhamento=WD_ALIGN_PARAGRAPH.LEFT, recuo=0, antes=6, depois=6)
        estilo("Lista ABNT", alinhamento=WD_ALIGN_PARAGRAPH.JUSTIFY, recuo=0)
        estilo("Capa", alinhamento=WD_ALIGN_PARAGRAPH.CENTER, recuo=0, entrelinha=1.0, antes=0, depois=0)
        estilo("Header", tamanho=PEQUENA, alinhamento=WD_ALIGN_PARAGRAPH.RIGHT, recuo=0, entrelinha=1.0)
        # sumário (NBR 6027): indicativos à esquerda, títulos alinhados, pontilhado até a página
        for n, (neg, ita) in enumerate([(True, False), (True, False), (False, False), (False, True)], start=1):
            s = estilo(f"toc {n}", tamanho=12, negrito=neg, italico=ita, alinhamento=WD_ALIGN_PARAGRAPH.LEFT,
                       recuo=0, entrelinha=1.5, antes=6 if n == 1 else 0, depois=0)
            pf = s.paragraph_format
            pf.left_indent, pf.first_line_indent = Cm(1.6), Cm(-1.6)
            pf.tab_stops.add_tab_stop(Cm(1.6))
            pf.tab_stops.add_tab_stop(Cm(LARGURA_UTIL_CM), WD_TAB_ALIGNMENT.RIGHT, WD_TAB_LEADER.DOTS)
        s = estilo("table of figures", tamanho=12, alinhamento=WD_ALIGN_PARAGRAPH.LEFT, recuo=0, entrelinha=1.5)
        pf = s.paragraph_format
        pf.left_indent, pf.first_line_indent = Cm(2.6), Cm(-2.6)
        pf.tab_stops.add_tab_stop(Cm(2.6))
        pf.tab_stops.add_tab_stop(Cm(LARGURA_UTIL_CM), WD_TAB_ALIGNMENT.RIGHT, WD_TAB_LEADER.DOTS)

    def _formatar(self, s, tamanho=None, negrito=None, italico=None, alinhamento=None, recuo=None, esquerda=None,
                  entrelinha=None, antes=None, depois=None, com_proximo=None, quebra=None, nivel=None, fonte=FONTE):
        rPr = s.element.get_or_add_rPr()
        _fontes(rPr, fonte)
        _cor_preta(rPr)
        f = s.font
        if tamanho is not None:
            f.size = Pt(tamanho)
        if negrito is not None:
            f.bold = negrito
        if italico is not None:
            f.italic = italico
        pf = s.paragraph_format
        if alinhamento is not None:
            pf.alignment = alinhamento
        if recuo is not None:
            pf.first_line_indent = Cm(recuo)
        if esquerda is not None:
            pf.left_indent = Cm(esquerda)
        if entrelinha is not None:
            pf.line_spacing = entrelinha
        if antes is not None:
            pf.space_before = Pt(antes)
        if depois is not None:
            pf.space_after = Pt(depois)
        if com_proximo is not None:
            pf.keep_with_next = com_proximo
        if quebra is not None:
            pf.page_break_before = quebra
        pf.keep_together = None
        if nivel is not None:
            _anexar_pPr(s.element.get_or_add_pPr(), "w:outlineLvl", **{"w:val": nivel})

    def _numeracao_listas(self):
        """Marcadores (•, –) e números (1., a)) das listas, com recuo ABNT."""
        numbering = self.doc.part.numbering_part.element
        self._abstratos = {}
        for nome, niveis in {
            "marcador": [("bullet", "•", 1.75, 0.5), ("bullet", "–", 2.5, 0.5)],
            "numero": [("decimal", "%1.", 1.85, 0.6), ("lowerLetter", "%2)", 2.6, 0.6)],
        }.items():
            ident = str(90 + len(self._abstratos))
            an = OxmlElement("w:abstractNum")
            an.set(qn("w:abstractNumId"), ident)
            mlt = OxmlElement("w:multiLevelType")
            mlt.set(qn("w:val"), "hybridMultilevel")
            an.append(mlt)
            for ilvl, (fmt, texto, esquerda, pendente) in enumerate(niveis):
                lvl = OxmlElement("w:lvl")
                lvl.set(qn("w:ilvl"), str(ilvl))
                for tag, val in (("w:start", "1"), ("w:numFmt", fmt), ("w:lvlText", texto), ("w:lvlJc", "left")):
                    el = OxmlElement(tag)
                    el.set(qn("w:val"), val)
                    lvl.append(el)
                pPr = OxmlElement("w:pPr")
                ind = OxmlElement("w:ind")
                ind.set(qn("w:left"), str(int(esquerda * 567)))
                ind.set(qn("w:hanging"), str(int(pendente * 567)))
                pPr.append(ind)
                lvl.append(pPr)
                rPr = OxmlElement("w:rPr")
                _fontes(rPr, FONTE)
                lvl.append(rPr)
                an.append(lvl)
            primeiro_num = numbering.find(qn("w:num"))
            if primeiro_num is not None:
                primeiro_num.addprevious(an)
            else:
                numbering.append(an)
            self._abstratos[nome] = ident

    def _nova_lista(self, ordenada: bool) -> int:
        numbering = self.doc.part.numbering_part.element
        ids = [int(n.get(qn("w:numId"))) for n in numbering.findall(qn("w:num"))]
        novo = max(ids + [0]) + 1
        num = OxmlElement("w:num")
        num.set(qn("w:numId"), str(novo))
        an = OxmlElement("w:abstractNumId")
        an.set(qn("w:val"), self._abstratos["numero" if ordenada else "marcador"])
        num.append(an)
        if ordenada:
            ov = OxmlElement("w:lvlOverride")
            ov.set(qn("w:ilvl"), "0")
            so = OxmlElement("w:startOverride")
            so.set(qn("w:val"), "1")
            ov.append(so)
            num.append(ov)
        numbering.append(num)
        return novo

    def _configurar_pagina(self, sec):
        sec.page_width, sec.page_height = Cm(21), Cm(29.7)
        sec.top_margin, sec.left_margin = Cm(3), Cm(3)
        sec.bottom_margin, sec.right_margin = Cm(2), Cm(2)
        sec.header_distance, sec.footer_distance = Cm(2), Cm(1.25)
        sec.gutter = Cm(0)

    # ------------------------------------------------------------------ texto corrido -> runs
    def _runs(self, par, trechos: list[Trecho], tamanho=None, maiusculas=False):
        for t in trechos:
            if t.tipo == "texto":
                self._run(par, t.texto.upper() if maiusculas else t.texto, t.fmt, tamanho)
            elif t.tipo == "link":
                self._link(par, t.alvo, t.texto, t.fmt, tamanho)
            elif t.tipo == "ref":
                self._run(par, self.rotulos[t.alvo], t.fmt, tamanho)
            elif t.tipo == "cit":
                for texto, fmt in self.bib.citacao(t.itens, t.narrativa):
                    self._run(par, texto, t.fmt | fmt, tamanho)

    def _run(self, par, texto, fmt=frozenset(), tamanho=None):
        r = par.add_run(texto)
        if "b" in fmt:
            r.bold = True
        if "i" in fmt:
            r.italic = True
        if "sup" in fmt:
            r.font.superscript = True
        if "sub" in fmt:
            r.font.subscript = True
        if "code" in fmt:
            if len(texto) > 20:          # caminhos longos: permite quebrar a linha depois de "/"
                r.text = texto.replace("/", "/\u200b")
            _fontes(r._r.get_or_add_rPr(), FONTE_CODIGO)
            r.font.size = Pt((tamanho or 12) - 1.5)
        elif tamanho:
            r.font.size = Pt(tamanho)
        return r

    def _link(self, par, url, texto, fmt=frozenset(), tamanho=None):
        rid = par.part.relate_to(url, RT.HYPERLINK, is_external=True)
        h = OxmlElement("w:hyperlink")
        h.set(qn("r:id"), rid)
        par._p.append(h)
        r = self._run(par, texto, fmt, tamanho)
        h.append(r._r)        # move o run para dentro do link (preto e sem sublinhado, como no impresso)

    def _paragrafo(self, texto, linha, estilo="Normal", tamanho=None, maiusculas=False):
        par = self.doc.add_paragraph(style=estilo)
        self._runs(par, ler_inline(self._valores(texto, linha), linha), tamanho, maiusculas)
        return par

    # ------------------------------------------------------------------ capa, folha de rosto, aprovação
    def _meta(self, chave, padrao=""):
        v = self.meta.get(chave, padrao)
        return " ".join(str(v).split()) if v is not None else ""

    def _linha_capa(self, cel, texto, negrito=True, maiusculas=True, tamanho=12, antes=0, alinhamento=None,
                    entrelinha=1.0):
        par = cel.add_paragraph(style="Capa")
        if alinhamento is not None:
            par.paragraph_format.alignment = alinhamento
        par.paragraph_format.space_before = Pt(antes)
        par.paragraph_format.line_spacing = entrelinha
        self._run(par, texto.upper() if maiusculas else texto, frozenset({"b"}) if negrito else frozenset(), tamanho)
        return par

    def _titulo_capa(self, cel, antes=0):
        par = cel.add_paragraph(style="Capa")
        par.paragraph_format.space_before = Pt(antes)
        par.paragraph_format.line_spacing = 1.5
        titulo, sub = self._meta("title"), self._meta("subtitle")
        self._run(par, titulo.upper() + (":" if sub else ""), frozenset({"b"}))
        if sub:
            par2 = cel.add_paragraph(style="Capa")
            par2.paragraph_format.line_spacing = 1.5
            self._run(par2, sub)

    def _tabela_pagina(self, alturas_cm: list[float]):
        """Tabela invisível de 1 coluna com linhas de altura exata: faz o papel do \\vfill do LaTeX."""
        t = self.doc.add_table(rows=len(alturas_cm), cols=1)
        t.alignment = WD_TABLE_ALIGNMENT.CENTER
        t.autofit = False
        _sem_bordas(t)
        for linha, h in zip(t.rows, alturas_cm):
            linha.height = Cm(h)
            linha.height_rule = WD_ROW_HEIGHT_RULE.EXACTLY
            cel = linha.cells[0]
            cel.width = Cm(LARGURA_UTIL_CM)
            cel._tc.remove(cel.paragraphs[0]._p)          # tira o parágrafo vazio padrão
        return t

    @staticmethod
    def _fechar_celulas(tabela):
        """Toda célula precisa terminar num parágrafo (exigência do Word)."""
        for linha in tabela.rows:
            for cel in linha.cells:
                filhos = [f for f in cel._tc if f.tag != qn("w:tcPr")]
                if not filhos or filhos[-1].tag != qn("w:p"):
                    _marca_minima(cel.add_paragraph(style="Capa"))

    def _quebra_secao(self, inicio_paginacao=False):
        """Fecha a seção atual e abre outra numa página nova.

        O python-docx guarda a seção anterior num parágrafo vazio no fim do texto; ele vira um
        parágrafo de 1 pt para não empurrar a página (a capa e a folha de rosto ocupam a página toda).
        """
        sec = self.doc.add_section(WD_SECTION.NEW_PAGE)
        par_quebra = self.doc.paragraphs[-1]
        par_quebra.style = self.doc.styles["Capa"]
        _marca_minima(par_quebra)
        self._configurar_pagina(sec)
        sp = sec._sectPr
        for velho in sp.findall(qn("w:pgNumType")):
            sp.remove(velho)                     # a nova seção continua a contagem da anterior
        if inicio_paginacao:
            _inserir(sp, _elemento("w:pgNumType", **{"w:start": 1}), ORDEM_SECTPR)
        return sec

    def _alt_autores(self) -> float:
        """Altura (cm) do bloco de autores: uma linha de 1,5 (≈ 0,75 cm) por autor."""
        return 0.75 * max(1, len(self.meta.get("autores", []))) + 0.3

    def _capa(self):
        logo = self.meta.get("logo", True)
        h_autores = 2.5 + self._alt_autores()            # 2,5 cm de espaço antes dos autores
        t = self._tabela_pagina([2.2, h_autores, 24.0 - 2.2 - h_autores - 2.3, 2.3])
        c0, c1, c2, c3 = (r.cells[0] for r in t.rows)
        c0.vertical_alignment = WD_CELL_VERTICAL_ALIGNMENT.TOP
        inst, curso = self._meta("instituicao"), self._meta("curso")
        if logo is not False:
            caminho = Path(__file__).with_name("logo-ceub.png") if logo in (True, None, "") else self.base / str(logo)
            cab = c0.add_table(rows=1, cols=2)
            cab.alignment = WD_TABLE_ALIGNMENT.CENTER
            cab.autofit = False
            _sem_bordas(cab)
            ce, cd = cab.rows[0].cells
            ce.width, cd.width = Cm(3.4), Cm(10.6)
            for gc, w in zip(cab._tbl.tblGrid.findall(qn("w:gridCol")), (3.4, 10.6)):
                gc.set(qn("w:w"), str(int(w * 567)))
            ce.vertical_alignment = cd.vertical_alignment = WD_CELL_VERTICAL_ALIGNMENT.CENTER
            p = ce.paragraphs[0]
            p.style = self.doc.styles["Capa"]
            p.paragraph_format.alignment = WD_ALIGN_PARAGRAPH.RIGHT
            p.add_run().add_picture(str(caminho), height=Cm(1.35))
            p = cd.paragraphs[0]
            p.style = self.doc.styles["Capa"]
            p.paragraph_format.alignment = WD_ALIGN_PARAGRAPH.LEFT
            self._run(p, inst)
            if curso:
                self._linha_capa(cd, curso, negrito=False, maiusculas=False, alinhamento=WD_ALIGN_PARAGRAPH.LEFT)
        else:
            self._linha_capa(c0, inst)
            if curso:
                self._linha_capa(c0, curso)
        c1.vertical_alignment = WD_CELL_VERTICAL_ALIGNMENT.TOP
        for k, nome in enumerate(self.meta.get("autores", [])):
            self._linha_capa(c1, str(nome), antes=71 if k == 0 else 0, entrelinha=1.5)   # 71 pt = 2,5 cm
        c2.vertical_alignment = WD_CELL_VERTICAL_ALIGNMENT.CENTER
        self._titulo_capa(c2)
        c3.vertical_alignment = WD_CELL_VERTICAL_ALIGNMENT.BOTTOM
        self._linha_capa(c3, self._meta("cidade"), entrelinha=1.5)
        self._linha_capa(c3, self._meta("ano"), entrelinha=1.5)
        self._fechar_celulas(t)

    def _bloco_natureza(self, cel, com_orientador=True):
        par = cel.add_paragraph(style="Capa")
        pf = par.paragraph_format
        pf.left_indent = Cm(8)
        pf.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
        self._run(par, self._meta("natureza"), tamanho=11)
        if com_orientador and self.meta.get("orientador"):
            par = cel.add_paragraph(style="Capa")
            par.paragraph_format.left_indent = Cm(8)
            par.paragraph_format.alignment = WD_ALIGN_PARAGRAPH.LEFT
            par.paragraph_format.space_before = Pt(10)
            rotulo = self._meta("rotulo-orientador", "Orientador(a)")
            self._run(par, f"{rotulo}: {self._meta('orientador')}", tamanho=11)

    def _folha_de_rosto(self):
        h_autores = self._alt_autores()
        t = self._tabela_pagina([h_autores, 5.6, 5.2, 24.0 - h_autores - 5.6 - 5.2])
        c0, c1, c2, c3 = (r.cells[0] for r in t.rows)
        for nome in self.meta.get("autores", []):
            self._linha_capa(c0, str(nome), entrelinha=1.5)
        c1.vertical_alignment = WD_CELL_VERTICAL_ALIGNMENT.BOTTOM
        self._titulo_capa(c1)
        c2.vertical_alignment = WD_CELL_VERTICAL_ALIGNMENT.CENTER
        self._bloco_natureza(c2)
        c3.vertical_alignment = WD_CELL_VERTICAL_ALIGNMENT.BOTTOM
        self._linha_capa(c3, self._meta("cidade"), entrelinha=1.5)
        self._linha_capa(c3, self._meta("ano"), entrelinha=1.5)
        self._fechar_celulas(t)

    def _folha_de_aprovacao(self):
        banca = self.meta.get("banca") or []
        if not banca:
            return
        par = self.doc.add_paragraph(style="Capa")
        par.paragraph_format.page_break_before = True
        t = self._tabela_pagina([2.6, 4.0, 4.4, 13.0])
        c0, c1, c2, c3 = (r.cells[0] for r in t.rows)
        for nome in self.meta.get("autores", []):
            self._linha_capa(c0, str(nome), entrelinha=1.5)
        c1.vertical_alignment = WD_CELL_VERTICAL_ALIGNMENT.CENTER
        self._titulo_capa(c1)
        self._bloco_natureza(c2, com_orientador=False)
        data = self._meta("data-aprovacao")
        self._linha_capa(c3, self._meta("cidade").upper() + (f", {data}" if data else ""), maiusculas=False)
        self._linha_capa(c3, "BANCA EXAMINADORA", antes=18)
        for membro in banca:
            self._linha_capa(c3, "_" * 40, negrito=False, antes=36)
            self._linha_capa(c3, str(membro), negrito=False, maiusculas=False, tamanho=PEQUENA)
        self._fechar_celulas(t)

    # ------------------------------------------------------------------ listas e sumário
    def _campo_lista(self, instrucao, entradas: list[tuple[str, str, frozenset]]):
        """Campo TOC do Word com o resultado já calculado (o Word atualiza com F9)."""
        if not entradas:
            entradas = [("Normal", "Nenhuma entrada.", frozenset())]
        pars = []
        for k, (estilo, texto, fmt) in enumerate(entradas):
            par = self.doc.add_paragraph(style=estilo)
            if k == 0:
                _fldchar(par, "begin")
                _instr(par, instrucao)
                _fldchar(par, "separate")
            self._run(par, texto, fmt)
            pars.append(par)
        _fldchar(pars[-1], "end")

    def _listas(self, paginas: dict | None):
        def pg(chave):
            return str(paginas.get(chave, "00")) if paginas else "00"

        if self.figuras:
            self._titulo_sem_numero("Lista de figuras", pos=False)
            self._campo_lista('TOC \\h \\z \\c "Figura"', [
                ("table of figures", f"Figura {f['numero']} –\t{f['titulo']}\t{pg(('fig', f['numero']))}", frozenset())
                for f in self.figuras])
        if self.tabelas:
            self._titulo_sem_numero("Lista de tabelas", pos=False)
            self._campo_lista('TOC \\h \\z \\c "Tabela"', [
                ("table of figures", f"Tabela {t['numero']} –\t{t['titulo']}\t{pg(('tbl', t['numero']))}", frozenset())
                for t in self.tabelas])
        self._titulo_sem_numero("Sumário", pos=False)
        entradas = []
        for k, e in enumerate(self.sumario):
            nivel = e["nivel"]
            texto = (f"{e['numero']}\t{e['titulo']}" if e["numero"] else e["titulo"]) + f"\t{pg(('sec', k))}"
            entradas.append((f"toc {nivel}", texto, frozenset()))
        self._campo_lista('TOC \\o "1-4" \\h \\z \\u', entradas)

    def _titulo_sem_numero(self, texto, pos: bool, quebra=True):
        par = self.doc.add_paragraph(style="Titulo pos-textual" if pos else "Titulo pre-textual")
        if not quebra:
            par.paragraph_format.page_break_before = False
        self._run(par, texto.upper())
        return par

    # ------------------------------------------------------------------ blocos
    def construir(self, blocos: list[Bloco], paginas: dict | None = None):
        self.doc = Document()
        self._estilos()
        self._numeracao_listas()
        self._configurar_pagina(self.doc.sections[0])
        cp = self.doc.core_properties
        cp.title = self._meta("title") + (": " + self._meta("subtitle") if self.meta.get("subtitle") else "")
        cp.author = "; ".join(str(a) for a in self.meta.get("autores", []))
        cp.language = "pt-BR"
        cp.subject = self._meta("natureza")
        cp.comments = "Gerado por relatorio/gerar_relatorio.py a partir do relatorio_pi.md"

        self._capa()
        self._quebra_secao(inicio_paginacao=True)
        self._folha_de_rosto()
        self._folha_de_aprovacao()
        self.contexto = {"textual": False, "resumo": False, "primeiro": False}
        for b in blocos:
            self._bloco(b, paginas)
        self._ajustes_finais()
        return self.doc

    def _bloco(self, b: Bloco, paginas, estilo_par=None):
        ctx = self.contexto
        if b.tipo == "titulo":
            return self._titulo(b)
        if b.tipo == "paragrafo":
            estilo = estilo_par or ("Resumo" if ctx["resumo"] else "Normal")
            par = self._paragrafo(b.texto, b.linha, estilo)
            if ctx["resumo"] and b.texto.lstrip("*_ ").lower().startswith(PALAVRAS_CHAVE):
                par.paragraph_format.space_before = Pt(12)
            return par
        if b.tipo == "lista":
            num = self._nova_lista(b.ordenada)
            for nivel, texto in b.itens:
                par = self._paragrafo(texto, b.linha, "Lista ABNT")
                numPr = par._p.get_or_add_pPr().get_or_add_numPr()
                numPr.get_or_add_ilvl().val = nivel
                numPr.get_or_add_numId().val = num
            return
        if b.tipo == "figura":
            return self._figura(b)
        if b.tipo == "tabela":
            return self._tabela(b)
        if b.tipo == "equacao":
            return self._equacao(b)
        if b.tipo == "codigo":
            return self._codigo(b)
        if b.tipo == "div":
            nome = b.texto
            if nome == "fonte":
                for f in b.filhos:
                    self._bloco(f, paginas, "Fonte")
            elif nome == "citacao":
                for f in b.filhos:
                    self._bloco(f, paginas, "Citacao longa")
            elif nome == "listas":
                ctx["resumo"] = False
                self._listas(paginas)
            elif nome == "refs":
                for trechos in self.bib.lista():
                    par = self.doc.add_paragraph(style="Referencia")
                    for texto, fmt in trechos:
                        if texto.startswith("http") or " http" in texto:
                            self._texto_com_links(par, texto, fmt)
                        else:
                            self._run(par, texto, fmt)
            elif nome == "quebra":
                self.doc.add_paragraph(style="Capa").add_run().add_break(WD_BREAK.PAGE)
            else:
                raise ErroRelatorio(f"Linha {b.linha}: bloco '::: {nome}' desconhecido. "
                                    f"Use fonte, citacao, listas, quebra ou {{#refs}}.")
            return
        raise ErroRelatorio(f"Linha {b.linha}: bloco do tipo {b.tipo} não suportado.")

    def _texto_com_links(self, par, texto, fmt):
        import re
        pos = 0
        for m in re.finditer(r"https?://\S+?(?=\.?(?:\s|$))", texto):
            self._run(par, texto[pos:m.start()], fmt)
            self._link(par, m.group(0), m.group(0), fmt)
            pos = m.end()
        self._run(par, texto[pos:], fmt)

    def _titulo(self, b: Bloco):
        ctx = self.contexto
        nome = self._plano(b.texto, b.linha)
        if "pre" in b.classes:
            ctx["resumo"] = nome.lower() in RESUMOS
            return self._titulo_sem_numero(nome, pos=False)
        ctx["resumo"] = False
        if "pos" in b.classes or "unnumbered" in b.classes:
            return self._titulo_sem_numero(nome, pos=True)
        primeiro = False
        if not ctx["textual"]:
            if b.nivel != 1:
                raise ErroRelatorio(f"Linha {b.linha}: o texto principal precisa começar com um título '# '.")
            ctx["textual"] = True
            primeiro = True
            sec = self._quebra_secao()
            sec.header.is_linked_to_previous = False
            cab = sec.header.paragraphs[0]
            cab.style = self.doc.styles["Header"]
            _campo(cab, "PAGE", "1", PEQUENA)
        numero = self.num_bloco[id(b)]
        par = self.doc.add_paragraph(style=f"Heading {b.nivel}")
        if primeiro:
            par.paragraph_format.page_break_before = False
        self._run(par, numero + " ")
        self._runs(par, ler_inline(self._valores(b.texto, b.linha), b.linha), maiusculas=(b.nivel == 1))
        return par

    def _legenda(self, tipo, numero, texto, linha):
        par = self.doc.add_paragraph(style="Caption")
        self._run(par, f"{tipo} ")
        _campo(par, f"SEQ {tipo} \\* ARABIC", str(numero))
        self._run(par, " – ")
        self._runs(par, ler_inline(self._valores(texto, linha), linha))
        return par

    def _figura(self, b: Bloco):
        numero = self.num_bloco[id(b)]
        alvo = b.itens[0]
        if alvo.startswith("#"):
            caminho = Path(self.obter_figura(b.id))
        else:
            caminho = self.base / alvo
            if not caminho.exists():
                raise ErroRelatorio(f"Linha {b.linha}: a imagem '{alvo}' não foi encontrada.")
        self._legenda("Figura", numero, b.texto, b.linha)
        par = self.doc.add_paragraph(style="Figura")
        largura = LARGURA_UTIL_CM
        if "largura" in b.attrs:
            largura = LARGURA_UTIL_CM * float(b.attrs["largura"].rstrip("%")) / 100
        else:
            from PIL import Image
            with Image.open(caminho) as im:
                dpi = (im.info.get("dpi") or (300, 300))[0] or 300
                largura = min(LARGURA_UTIL_CM, im.width / dpi * 2.54)
        par.add_run().add_picture(str(caminho), width=Cm(largura))

    def _tabela(self, b: Bloco):
        numero = self.num_bloco[id(b)]
        if b.itens:      # tabela escrita no texto (| ... |)
            tab = self._tabela_do_texto(b)
        else:
            tab = self.obter_tabela(b.id)
            if not isinstance(tab, TabelaABNT):
                raise ErroRelatorio(f"Linha {b.linha}: a função da tabela {b.id} precisa terminar com "
                                    f"return tabela_abnt(...).")
        self._legenda("Tabela", numero, b.texto, b.linha)
        self._montar_tabela(tab, b.linha)

    def _tabela_do_texto(self, b: Bloco) -> TabelaABNT:
        def celulas(linha):
            return [c.strip() for c in linha.strip().strip("|").split("|")]
        if len(b.itens) < 2 or not set(b.itens[1].replace("|", "").strip()) <= set(":- "):
            raise ErroRelatorio(f"Linha {b.linha}: tabela sem a linha separadora |---|---| depois do cabeçalho.")
        cab = celulas(b.itens[0])
        alin = []
        for sep in celulas(b.itens[1]):
            alin.append("centro" if sep.startswith(":") and sep.endswith(":") else "dir" if sep.endswith(":") else "esq")
        corpo = [celulas(l) for l in b.itens[2:]]
        larg = [float(x) for x in b.attrs["larguras"].split(",")] if "larguras" in b.attrs else None
        return TabelaABNT(cab, corpo, alin, larg)

    def _larguras(self, tab: TabelaABNT, tamanho) -> list[float]:
        if tab.larguras:
            return tab.larguras
        cm_por_letra = 0.0185 * tamanho
        def largura_texto(t):
            return max((len(p) for p in str(t).split()), default=1), len(str(t))
        larg = []
        for j in range(len(tab.cabecalho)):
            textos = [tab.cabecalho[j]] + [l[j] for l in tab.linhas if j < len(l)]
            palavra = max(largura_texto(t)[0] for t in textos)
            cheio = max(largura_texto(t)[1] for t in textos)
            larg.append([palavra * cm_por_letra + 0.45, cheio * cm_por_letra + 0.45])
        total_cheio = sum(c for _, c in larg)
        if total_cheio <= LARGURA_UTIL_CM:
            return [c for _, c in larg]
        minimo = [p for p, _ in larg]
        sobra = LARGURA_UTIL_CM - sum(minimo)
        if sobra <= 0:
            return [LARGURA_UTIL_CM * p / sum(minimo) for p in minimo]
        extra = [c - p for p, c in larg]
        return [p + sobra * e / sum(extra) if sum(extra) else p for (p, _), e in zip(larg, extra)]

    def _montar_tabela(self, tab: TabelaABNT, linha):
        n = len(tab.cabecalho)
        for k, l in enumerate(tab.linhas):
            if len(l) != n:
                raise ErroRelatorio(f"Linha {linha}: a linha {k + 1} da tabela tem {len(l)} colunas; o cabeçalho tem {n}.")
        larg = self._larguras(tab, tab.tamanho)
        t = self.doc.add_table(rows=1 + len(tab.linhas), cols=n)
        t.alignment = WD_TABLE_ALIGNMENT.CENTER
        t.autofit = False
        _bordas_tabela(t)
        grid = t._tbl.tblGrid
        for gc, w in zip(grid.findall(qn("w:gridCol")), larg):
            gc.set(qn("w:w"), str(int(w * 567)))
        for i, row in enumerate(t.rows):
            trPr = row._tr.get_or_add_trPr()
            cs = OxmlElement("w:cantSplit")
            trPr.append(cs)
            if i == 0:
                th = OxmlElement("w:tblHeader")
                trPr.append(th)
            textos = tab.cabecalho if i == 0 else tab.linhas[i - 1]
            for j, cel in enumerate(row.cells):
                cel.width = Cm(larg[j])
                cel.vertical_alignment = WD_CELL_VERTICAL_ALIGNMENT.CENTER if i == 0 else WD_CELL_VERTICAL_ALIGNMENT.TOP
                par = cel.paragraphs[0]
                par.style = self.doc.styles["Texto de tabela"]
                par.paragraph_format.alignment = ALINHA["centro" if i == 0 else tab.alinhamentos[j]]
                par.paragraph_format.keep_with_next = True
                self._runs(par, ler_inline(self._valores(textos[j], linha), linha), tab.tamanho)
                if i == 0:
                    _borda_celula(cel, "bottom", 4)

    def _equacao(self, b: Bloco):
        par = self.doc.add_paragraph(style="Equacao")
        ts = par.paragraph_format.tab_stops
        ts.add_tab_stop(Cm(LARGURA_UTIL_CM / 2), WD_TAB_ALIGNMENT.CENTER)
        ts.add_tab_stop(Cm(LARGURA_UTIL_CM), WD_TAB_ALIGNMENT.RIGHT)
        self._run(par, "\t")
        self._runs(par, ler_inline(self._valores(b.texto, b.linha), b.linha))
        self._run(par, f"\t({self.num_bloco[id(b)]})")

    def _codigo(self, b: Bloco):
        texto = b.texto
        if "arquivo" in b.attrs:
            caminho = self.base / b.attrs["arquivo"]
            if not caminho.exists():
                raise ErroRelatorio(f"Linha {b.linha}: o arquivo de código '{b.attrs['arquivo']}' não existe.")
            fonte = caminho.read_text(encoding="utf-8")
            if "funcao" in b.attrs:
                texto = self._extrair_funcao(fonte, b.attrs["funcao"], b.linha)
            elif "linhas" in b.attrs:
                a, z = (int(x) for x in b.attrs["linhas"].split("-"))
                texto = "\n".join(fonte.split("\n")[a - 1:z])
            else:
                texto = fonte
        linhas = [parte for l in texto.expandtabs(4).rstrip("\n").split("\n") for parte in quebrar_codigo(l)]
        for k, l in enumerate(linhas):
            par = self.doc.add_paragraph(style="Codigo")
            _anexar_pPr(par._p.get_or_add_pPr(), "w:shd", **{"w:val": "clear", "w:color": "auto", "w:fill": "F2F2F2"})
            if k == 0:
                par.paragraph_format.space_before = Pt(6)
            if k == len(linhas) - 1:
                par.paragraph_format.space_after = Pt(6)
            self._run(par, l if l else " ")

    @staticmethod
    def _extrair_funcao(fonte: str, nome: str, linha: int) -> str:
        arvore = ast.parse(fonte)
        partes = nome.split(".")
        nos = arvore.body
        alvo = None
        for p in partes:
            alvo = next((n for n in nos if isinstance(n, (ast.FunctionDef, ast.ClassDef, ast.AsyncFunctionDef))
                         and n.name == p), None)
            if alvo is None:
                raise ErroRelatorio(f"Linha {linha}: '{nome}' não foi encontrado no arquivo de código.")
            nos = alvo.body
        linhas = fonte.split("\n")
        inicio = min([alvo.lineno] + [d.lineno for d in getattr(alvo, "decorator_list", [])])
        trecho = linhas[inicio - 1:alvo.end_lineno]
        recuo = min((len(l) - len(l.lstrip()) for l in trecho if l.strip()), default=0)
        return "\n".join(l[recuo:] for l in trecho)

    # ------------------------------------------------------------------ acabamento
    def _ajustes_finais(self):
        # Word 2013+ (sem "modo de compatibilidade")
        settings = self.doc.settings.element
        for cs in settings.iter(qn("w:compatSetting")):
            if cs.get(qn("w:name")) == "compatibilityMode":
                cs.set(qn("w:val"), "15")
        zoom = settings.find(qn("w:zoom"))
        if zoom is not None:
            zoom.set(qn("w:percent"), "100")
        # remove a miniatura do modelo padrão do python-docx (mostraria uma página vazia)
        pkg = self.doc.part.package
        for rid, rel in list(pkg.rels.items()):
            if rel.reltype.endswith("/thumbnail"):
                del pkg.rels[rid]
