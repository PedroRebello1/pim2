"""Gráficos SVG mínimos, sem dependências (o ambiente não tem matplotlib).

Paleta: superfície clara #fcfcfb, série única azul #2a78d6, rampa sequencial azul para o heatmap.
Cada marca leva <title> para tooltip nativo ao passar o mouse.
"""
from html import escape

SUP, TXT, TXT2, MUTED, GRID, SERIE = "#fcfcfb", "#0b0b0b", "#52514e", "#898781", "#e6e5e0", "#2a78d6"
RAMPA = ["#f0efec", "#cde2fb", "#9ec5f4", "#6da7ec", "#3987e5", "#256abf", "#184f95", "#0d366b"]
FONTE = "font-family='system-ui,-apple-system,Segoe UI,Roboto,sans-serif'"


def _cabecalho(w, h, titulo, subtitulo):
    return [f"<svg xmlns='http://www.w3.org/2000/svg' width='{w}' height='{h}' viewBox='0 0 {w} {h}' {FONTE}>",
            f"<rect width='{w}' height='{h}' fill='{SUP}' rx='8'/>",
            f"<text x='20' y='28' font-size='15' font-weight='600' fill='{TXT}'>{escape(titulo)}</text>",
            f"<text x='20' y='47' font-size='12' fill='{TXT2}'>{escape(subtitulo)}</text>"]


def _escala(vmax):
    passo = [1, 2, 5, 10, 20, 25, 50, 100, 200, 250, 500, 1000][0]
    for s in [1, 2, 5, 10, 20, 25, 50, 100, 200, 250, 500, 1000]:
        if vmax / s <= 6:
            passo = s
            break
    topo = passo * -(-vmax // passo)
    return topo, passo


def _grade(x0, x1, y0, y1, topo, passo, unidade):
    out = []
    v = 0
    while v <= topo:
        y = y1 - (y1 - y0) * v / topo
        out.append(f"<line x1='{x0}' x2='{x1}' y1='{y:.1f}' y2='{y:.1f}' stroke='{GRID}' stroke-width='1'/>")
        out.append(f"<text x='{x0 - 8}' y='{y + 4:.1f}' font-size='11' fill='{MUTED}' text-anchor='end'>{v:g}</text>")
        v += passo
    out.append(f"<text x='{x0 - 8}' y='{y0 - 12}' font-size='11' fill='{MUTED}' text-anchor='end'>{escape(unidade)}</text>")
    return out


def linha(xs, ys, caminho, titulo, subtitulo, unidade, w=760, h=340):
    x0, x1, y0, y1 = 60, w - 30, 75, h - 50
    topo, passo = _escala(max(ys))
    out = _cabecalho(w, h, titulo, subtitulo) + _grade(x0, x1, y0, y1, topo, passo, unidade)
    px = [x0 + (x1 - x0) * i / (len(xs) - 1) for i in range(len(xs))]
    py = [y1 - (y1 - y0) * v / topo for v in ys]
    out.append(f"<polyline points='{' '.join(f'{a:.1f},{b:.1f}' for a, b in zip(px, py))}' fill='none' "
               f"stroke='{SERIE}' stroke-width='2' stroke-linejoin='round'/>")
    for i, (a, b) in enumerate(zip(px, py)):
        out.append(f"<circle cx='{a:.1f}' cy='{b:.1f}' r='9' fill='transparent'><title>{xs[i]}: {ys[i]:g} {escape(unidade)}</title></circle>")
        if i % 3 == 0 or i == len(xs) - 1:
            out.append(f"<text x='{a:.1f}' y='{y1 + 18}' font-size='11' fill='{MUTED}' text-anchor='middle'>{xs[i]}</text>")
    for i in (0, len(xs) - 1):  # rótulo direto só nas pontas
        out.append(f"<circle cx='{px[i]:.1f}' cy='{py[i]:.1f}' r='4' fill='{SERIE}' stroke='{SUP}' stroke-width='2'/>")
        out.append(f"<text x='{px[i]:.1f}' y='{py[i] - 10:.1f}' font-size='12' font-weight='600' fill='{TXT}' "
                   f"text-anchor='{'start' if i == 0 else 'end'}'>{ys[i]:g}</text>")
    out.append("</svg>")
    caminho.write_text("\n".join(out), encoding="utf-8")


def barras(cats, vals, caminho, titulo, subtitulo, unidade, fmt="{:g}", rotulos_extra=None, w=760, h=340):
    x0, x1, y0, y1 = 60, w - 30, 75, h - 60
    topo, passo = _escala(max(vals) if max(vals) > 0 else 1)
    out = _cabecalho(w, h, titulo, subtitulo) + _grade(x0, x1, y0, y1, topo, passo, unidade)
    slot = (x1 - x0) / len(cats)
    bw = min(44, slot - 2)  # 2px de respiro entre barras adjacentes
    for i, (c, v) in enumerate(zip(cats, vals)):
        cx = x0 + slot * (i + .5)
        hb = (y1 - y0) * v / topo
        top = y1 - hb
        r = min(4, hb)
        xa, xb = cx - bw / 2, cx + bw / 2
        if hb > 0:
            d = (f"M{xa:.1f},{y1} L{xa:.1f},{top + r:.1f} Q{xa:.1f},{top:.1f} {xa + r:.1f},{top:.1f} "
                 f"L{xb - r:.1f},{top:.1f} Q{xb:.1f},{top:.1f} {xb:.1f},{top + r:.1f} L{xb:.1f},{y1} Z")
            out.append(f"<path d='{d}' fill='{SERIE}'><title>{escape(str(c))}: {fmt.format(v)}</title></path>")
        out.append(f"<text x='{cx:.1f}' y='{top - 6:.1f}' font-size='11' fill='{TXT}' text-anchor='middle'>{fmt.format(v)}</text>")
        out.append(f"<text x='{cx:.1f}' y='{y1 + 16}' font-size='11' fill='{TXT2}' text-anchor='middle'>{escape(str(c))}</text>")
        if rotulos_extra:
            out.append(f"<text x='{cx:.1f}' y='{y1 + 30}' font-size='10' fill='{MUTED}' text-anchor='middle'>{escape(rotulos_extra[i])}</text>")
    out.append("</svg>")
    caminho.write_text("\n".join(out), encoding="utf-8")


def heatmap(matriz, linhas, colunas, caminho, titulo, subtitulo, w=520, h=None):
    cw, ch, x0, y0 = 54, 20, 60, 85
    h = h or y0 + ch * len(linhas) + 50
    vmax = max(max(r) for r in matriz)
    out = _cabecalho(w, h, titulo, subtitulo)
    for j, c in enumerate(colunas):
        out.append(f"<text x='{x0 + cw * (j + .5):.1f}' y='{y0 - 8}' font-size='11' fill='{TXT2}' text-anchor='middle'>{c}</text>")
    for i, lab in enumerate(linhas):
        y = y0 + ch * i
        out.append(f"<text x='{x0 - 8}' y='{y + 14}' font-size='11' fill='{TXT2}' text-anchor='end'>{lab}</text>")
        for j, v in enumerate(matriz[i]):
            k = 0 if v < 0.5 else 1 + min(len(RAMPA) - 2, int((v / vmax) * (len(RAMPA) - 1)))
            out.append(f"<rect x='{x0 + cw * j + 1}' y='{y + 1}' width='{cw - 2}' height='{ch - 2}' rx='2' fill='{RAMPA[k]}'>"
                       f"<title>{colunas[j]} {lab}: {v:.1f} entradas/dia</title></rect>")
            if v >= vmax * .75:
                out.append(f"<text x='{x0 + cw * (j + .5):.1f}' y='{y + 14}' font-size='10' fill='#ffffff' text-anchor='middle'>{v:.0f}</text>")
    # legenda da rampa
    ly = y0 + ch * len(linhas) + 18
    out.append(f"<text x='{x0}' y='{ly + 10}' font-size='11' fill='{MUTED}'>menos</text>")
    for k, cor in enumerate(RAMPA[1:]):
        out.append(f"<rect x='{x0 + 42 + k * 22}' y='{ly}' width='20' height='12' rx='2' fill='{cor}'/>")
    out.append(f"<text x='{x0 + 42 + 7 * 22 + 4}' y='{ly + 10}' font-size='11' fill='{MUTED}'>mais (máx. {vmax:.0f})</text>")
    out.append("</svg>")
    caminho.write_text("\n".join(out), encoding="utf-8")
