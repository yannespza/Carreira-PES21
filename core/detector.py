"""Detecta patrocinadores na textura do uniforme (molde 2048x2048 do GOGOSZ/GUITAKITMAKER),
remove (preenchendo com o tecido ao redor) e aprende a posição de cada um."""
import numpy as np
from PIL import Image, ImageFilter

# áreas do molde onde podem existir patrocinadores (x0, y0, x1, y1, nome da área)
ZONAS = [
    (690, 990, 1360, 1880, 'frente'),
    (690, 40, 1360, 990, 'costas'),
    (440, 640, 790, 1200, 'manga_d'),
    (1260, 640, 1610, 1200, 'manga_e'),
    (0, 1180, 660, 1900, 'calcao_e'),
    (1390, 1180, 2048, 1900, 'calcao_d'),
    (0, 60, 690, 640, 'manga_longa_d'),
    (1360, 60, 2048, 640, 'manga_longa_e'),
]
# faixas do molde que não são uniforme (rótulos do kitmaker, gola, áreas de corte)
IGNORAR = [(1360, 0, 2048, 100), (0, 0, 690, 60), (0, 0, 530, 130), (0, 1890, 2048, 2048), (660, 1860, 1380, 2048)]


def _componentes(mask):
    """Rotula regiões conectadas (8 vizinhos) de uma máscara pequena. Retorna lista de caixas."""
    h, w = mask.shape
    lab = np.zeros((h, w), np.int32)
    caixas = []
    cur = 0
    ys, xs = np.nonzero(mask)
    for y0, x0 in zip(ys, xs):
        if lab[y0, x0]:
            continue
        cur += 1
        pilha = [(y0, x0)]; lab[y0, x0] = cur
        mnx = mxx = x0; mny = mxy = y0; n = 0
        while pilha:
            y, x = pilha.pop(); n += 1
            mnx = min(mnx, x); mxx = max(mxx, x); mny = min(mny, y); mxy = max(mxy, y)
            for dy in (-1, 0, 1):
                for dx in (-1, 0, 1):
                    yy, xx = y + dy, x + dx
                    if 0 <= yy < h and 0 <= xx < w and mask[yy, xx] and not lab[yy, xx]:
                        lab[yy, xx] = cur; pilha.append((yy, xx))
        caixas.append((mnx, mny, mxx + 1, mxy + 1, n))
    return caixas


def _cores_base(tile):
    """As 1–2 cores dominantes de um pedaço de tecido (quantizadas)."""
    q = (tile // 24).reshape(-1, 3)
    chaves = q[:, 0] * 10000 + q[:, 1] * 100 + q[:, 2]
    vals, cont = np.unique(chaves, return_counts=True)
    ordem = np.argsort(-cont)
    cores = []
    total = cont.sum()
    for j, i in enumerate(ordem[:3]):
        # a cor principal sempre conta; as outras só se forem uma parte grande do tecido (listras)
        if j > 0 and cont[i] / total < 0.30:
            break
        sel = chaves == vals[i]
        cores.append(tile.reshape(-1, 3)[sel].mean(0))
    return np.array(cores)


def detectar(img: Image.Image, escala=4):
    """Devolve caixas (x0,y0,x1,y1,zona) de possíveis patrocinadores, em coordenadas 2048."""
    rgb = np.array(img.convert('RGB').resize((2048 // escala, 2048 // escala), Image.BOX)).astype(np.float32)
    H, W, _ = rgb.shape
    T = 128 // escala            # tamanho do pedaço para estimar o fundo
    mascara = np.zeros((H, W), bool)
    for y in range(0, H, T):
        for x in range(0, W, T):
            # o fundo é estimado num pedaço maior em volta (3x3 pedaços)
            viz = rgb[max(0, y - T):y + 2 * T, max(0, x - T):x + 2 * T]
            base = _cores_base(viz)
            tile = rgb[y:y + T, x:x + T]
            d = np.min(np.linalg.norm(tile[:, :, None, :] - base[None, None], axis=3), axis=2)
            mascara[y:y + T, x:x + T] = d > 55
    # só dentro das zonas de uniforme
    zona_mask = np.zeros_like(mascara)
    for x0, y0, x1, y1, _ in ZONAS:
        zona_mask[y0 // escala:y1 // escala, x0 // escala:x1 // escala] = True
    for x0, y0, x1, y1 in IGNORAR:
        zona_mask[y0 // escala:y1 // escala, x0 // escala:x1 // escala] = False
    mascara &= zona_mask
    # junta letras próximas (dilatação simples)
    m = Image.fromarray((mascara * 255).astype('uint8')).filter(ImageFilter.MaxFilter(3))
    m = np.array(m) > 0
    caixas = []
    for x0, y0, x1, y1, n in _componentes(m):
        w, h = x1 - x0, y1 - y0
        area = w * h
        if area < 40 or max(w, h) < 8:
            continue
        if area > 0.25 * (W * H / 16):              # muito grande: faixa/desenho do uniforme
            continue
        if n / area < 0.18:                          # linha fina comprida (costura, friso)
            continue
        if max(w, h) / max(1, min(w, h)) > 12:
            continue
        X0, Y0, X1, Y1 = x0 * escala - 6, y0 * escala - 6, x1 * escala + 6, y1 * escala + 6
        if (Y1 - Y0) > 520 or (X1 - X0) > 620:      # faixa longa do desenho do uniforme
            continue
        bloco = rgb[y0:y1, x0:x1]
        roxo = ((bloco[:, :, 2] > 200) & (bloco[:, :, 0] < 150) & (bloco[:, :, 1] < 150)).mean()
        if roxo > 0.12:                               # área de molde do kitmaker (fora da camisa)
            continue
        cx, cy = (X0 + X1) / 2, (Y0 + Y1) / 2
        zona = next((z for a, b, c, d_, z in ZONAS if a <= cx < c and b <= cy < d_), 'outro')
        caixas.append([int(max(0, X0)), int(max(0, Y0)), int(min(2048, X1)), int(min(2048, Y1)), zona])
    return caixas


def _zona_de(caixa):
    """Peça do molde onde a caixa está (a que tem mais área em comum com ela)."""
    melhor, area = (0, 0, 2048, 2048), 0
    for x0, y0, x1, y1, z in ZONAS:
        a = max(0, min(x1, caixa[2]) - max(x0, caixa[0])) * max(0, min(y1, caixa[3]) - max(y0, caixa[1]))
        if a > area:
            melhor, area = (x0, y0, x1, y1), a
    return melhor


def preencher(a, caixa, proibido, R=6, sw=6, so_baixo=False):
    """Cobre a caixa copiando tecido da mesma peça, em tiras: primeiro de cima/baixo (mantém listras
    verticais); onde não der, de um lado/outro (listras horizontais)."""
    x0, y0, x1, y1 = [int(v) for v in caixa[:4]]
    H, W, _ = a.shape
    x0, y0, x1, y1 = max(0, x0), max(0, y0), min(W, x1), min(H, y1)
    w, h = x1 - x0, y1 - y0
    if w <= 0 or h <= 0:
        return
    zx0, zy0, zx1, zy1 = _zona_de(caixa)
    A = a[:, :, :3].astype(np.float32)
    feito = np.zeros((h, w), bool)
    # tiras verticais
    for sx in range(x0, x1, sw):
        ex = min(sx + sw, x1)
        top = A[max(0, y0 - R):y0, sx:ex]; bot = A[y1:min(H, y1 + R), sx:ex]
        melhor = None
        alc = 6 * h + 260 if so_baixo else 3 * h + 60
        for dy in list(range(h + 2, alc, 2)) + ([] if so_baixo else list(range(-3 * h - 60, -h - 1, 2))):
            sy0 = y0 + dy
            if sy0 - R < max(0, zy0) or sy0 + h + R > min(H, zy1):
                continue
            if proibido[sy0 - R:sy0 + h + R, sx:ex].any():
                continue
            e = 0.0
            if so_baixo:
                # perto da gola: o que importa é o tecido ser liso (sem desenho/logo) e casar embaixo
                bloco = A[sy0:sy0 + h, sx:ex]
                e += 4 * float(np.abs(bloco - bloco.mean(0, keepdims=True)).mean() ** 2)
            elif top.size:
                e += ((A[sy0 - top.shape[0]:sy0, sx:ex] - top) ** 2).mean()
            if bot.size:
                e += ((A[sy0 + h:sy0 + h + bot.shape[0], sx:ex] - bot) ** 2).mean()
            e += 0.01 * abs(dy)
            if melhor is None or e < melhor[0]:
                melhor = (e, sy0)
        if melhor is not None and (melhor[0] < 2500 or so_baixo):
            a[y0:y1, sx:ex] = a[melhor[1]:melhor[1] + h, sx:ex]
            feito[:, sx - x0:ex - x0] = True
    # tiras horizontais para o que sobrou
    if not feito.all():
        for sy in range(y0, y1, sw):
            ey = min(sy + sw, y1)
            if feito[sy - y0:ey - y0].all():
                continue
            esq = A[sy:ey, max(0, x0 - R):x0]; dir_ = A[sy:ey, x1:min(W, x1 + R)]
            melhor = None
            for dx in list(range(w + 2, 3 * w + 60, 2)) + list(range(-3 * w - 60, -w - 1, 2)):
                sx0 = x0 + dx
                if sx0 - R < max(0, zx0) or sx0 + w + R > min(W, zx1):
                    continue
                if proibido[sy:ey, sx0 - R:sx0 + w + R].any():
                    continue
                e = 0.0
                if esq.size:
                    e += ((A[sy:ey, sx0 - esq.shape[1]:sx0] - esq) ** 2).mean()
                if dir_.size:
                    e += ((A[sy:ey, sx0 + w:sx0 + w + dir_.shape[1]] - dir_) ** 2).mean()
                e += 0.01 * abs(dx)
                if melhor is None or e < melhor[0]:
                    melhor = (e, sx0)
            if melhor is not None:
                linha = a[sy:ey, melhor[1]:melhor[1] + w].copy()
                m = ~feito[sy - y0:ey - y0]
                a[sy:ey, x0:x1][m] = linha[m]
                feito[sy - y0:ey - y0] = True
    # depois: em cada coluna, mistura o tecido limpo logo acima e logo abaixo (mantém listras verticais)
    if not feito.all():
        livre = ~proibido
        for x in range(x0, x1):
            col = ~feito[:, x - x0]
            if not col.any():
                continue
            yu = y0 - 1
            while yu >= max(0, zy0) and not livre[yu, x]:
                yu -= 1
            yd = y1
            while yd < min(H, zy1) and not livre[yd, x]:
                yd += 1
            if yu < max(0, zy0) or yd >= min(H, zy1) or yd - yu > 4 * h + 200:
                continue
            t = (np.arange(y0, y1) - yu) / (yd - yu)
            linha = (A[yu, x][None] * (1 - t)[:, None] + A[yd, x][None] * t[:, None]).astype(np.uint8)
            a[y0:y1, x, :3][col] = linha[col]
            feito[:, x - x0] = True
    # último recurso: cor média da borda
    if not feito.all():
        borda = np.concatenate([A[max(0, y0 - R):y0, x0:x1].reshape(-1, 3), A[y1:y1 + R, x0:x1].reshape(-1, 3)])
        if len(borda):
            cor = borda.mean(0).astype(np.uint8)
            reg = a[y0:y1, x0:x1, :3]
            reg[~feito] = cor


def sugerir_manter(caixas):
    """Índices que provavelmente são escudo/marca do fornecedor (desmarcados por padrão)."""
    manter = set()
    for i, c in enumerate(caixas):
        x0, y0, x1, y1, zona = c[:5]
        cx, cy, w, h = (x0 + x1) / 2, (y0 + y1) / 2, x1 - x0, y1 - y0
        quadrado = 0.6 < w / max(1, h) < 1.6 and max(w, h) < 190
        if zona == 'frente' and 1100 < cy < 1290 and quadrado:
            manter.add(i)            # escudo e marca no peito
        if zona in ('calcao_e', 'calcao_d') and quadrado and 1450 < cy < 1800:
            manter.add(i)            # escudo/marca no calção
    return manter


def _tirar_manter(c, manter):
    """Encolhe a caixa para não encostar no escudo/marca do fornecedor."""
    x0, y0, x1, y1 = c[:4]
    for m in manter:
        if x0 >= m[2] or x1 <= m[0] or y0 >= m[3] or y1 <= m[1]:
            continue
        # corta pelo lado que perde menos área
        opc = [(m[2] - x0) * (y1 - y0), (x1 - m[0]) * (y1 - y0), (m[3] - y0) * (x1 - x0), (y1 - m[1]) * (x1 - x0)]
        k = int(np.argmin(opc))
        if k == 0: x0 = m[2]
        elif k == 1: x1 = m[0]
        elif k == 2: y0 = m[3]
        else: y1 = m[1]
        if x1 - x0 < 8 or y1 - y0 < 8:
            return None
    return [x0, y0, x1, y1]


def limpar(img: Image.Image, caixas, manter=()):
    """Apaga as caixas. 'manter' são caixas de escudo/marcas: não apaga, mas também não copia tecido delas."""
    a = np.array(img.convert('RGBA')).copy()
    caixas = [_tirar_manter(c, manter) for c in caixas]
    caixas = [c for c in caixas if c]
    proib = np.zeros(a.shape[:2], bool)
    for c in list(caixas) + list(manter):
        proib[max(0, c[1] - 3):c[3] + 3, max(0, c[0] - 3):c[2] + 3] = True
    # o roxo do molde (fora da peça) nunca serve de tecido
    rgbf = a[:, :, :3].astype(np.int16)
    proib |= (np.abs(rgbf[:, :, 0] - 105) < 30) & (np.abs(rgbf[:, :, 1] - 95) < 30) & (rgbf[:, :, 2] > 225)
    # outros detalhes do uniforme (achados pelo detector livre) também não servem de fonte
    for c in detectar(img):
        proib[max(0, c[1]):c[3], max(0, c[0]):c[2]] = True
    # da menor para a maior: as pequenas usam tecido limpo de perto
    for c in sorted(caixas, key=lambda c: (c[2] - c[0]) * (c[3] - c[1])):
        cx, cy = (c[0] + c[2]) / 2, (c[1] + c[3]) / 2
        # perto da gola: o tecido de cima é a gola em V; copia só de baixo (peito)
        preencher(a, c, proib, so_baixo=760 < cx < 1300 and 1000 < cy < 1160)
    return Image.fromarray(a, 'RGBA')


def desenhar(img: Image.Image, caixas, marcadas=None, largura=900):
    """Imagem para revisão: caixas numeradas (verde = vai apagar, cinza = manter)."""
    from PIL import ImageDraw
    s = largura / 2048
    im = img.convert('RGB').resize((largura, largura), Image.LANCZOS)
    d = ImageDraw.Draw(im)
    for i, c in enumerate(caixas):
        on = marcadas is None or i in marcadas
        cor = (200, 240, 49) if on else (130, 130, 130)
        box = [c[0] * s, c[1] * s, c[2] * s, c[3] * s]
        d.rectangle(box, outline=cor, width=2)
        d.rectangle([box[0], box[1] - 12, box[0] + 18, box[1]], fill=cor)
        d.text((box[0] + 3, box[1] - 12), str(i + 1), fill=(0, 0, 0))
    return im


# ---------------------------------------------------------------------------
# Posições padrão do molde GUITAKITMAKER (usado na maioria dos uniformes do GOGOSZ).
# Para cada posição: áreas de busca (x0,y0,x1,y1) na textura 2048 e o giro do logo em cada uma.
MOLDE = {
    'peito':           {'nome': 'Peito (master)', 'valor_base': 14_000_000, 'busca': [((800, 1260, 1250, 1530), 0)]},
    'acima_peito':     {'nome': 'Acima do master', 'valor_base': 600_000, 'busca': [((935, 1115, 1110, 1275), 0)]},
    'barra':           {'nome': 'Barra da camisa (frente)', 'valor_base': 1_700_000, 'busca': [((780, 1610, 1270, 1750), 0)]},
    'gola':            {'nome': 'Perto da gola (par)', 'valor_base': 2_100_000,
                        'busca': [((790, 1035, 940, 1140), 0), ((1110, 1035, 1265, 1140), 0)]},
    'laterais_frente': {'nome': 'Laterais da frente (par)', 'valor_base': 430_000,
                        'busca': [((760, 1360, 845, 1640), 90), ((1190, 1370, 1290, 1650), -90)]},
    'costas':          {'nome': 'Costas (alto)', 'valor_base': 3_100_000, 'busca': [((840, 760, 1210, 950), 180)]},
    'costas_baixo':    {'nome': 'Costas (baixo)', 'valor_base': 1_300_000, 'busca': [((840, 100, 1180, 440), 180)]},
    'costas_laterais': {'nome': 'Laterais das costas (par)', 'valor_base': 350_000,
                        'busca': [((735, 390, 850, 640), 90), ((1185, 390, 1300, 640), -90)]},
    'mangas':          {'nome': 'Mangas (par)', 'valor_base': 1_700_000,
                        'busca': [((550, 740, 740, 935), 0), ((550, 935, 740, 1110), 0),
                                  ((1315, 740, 1505, 935), 0), ((1315, 935, 1505, 1110), 0)]},
    'calcao':          {'nome': 'Calção – pernas (par)', 'valor_base': 1_150_000,
                        'busca': [((110, 1240, 250, 1540), -90), ((1795, 1220, 1935, 1535), 90)]},
    'calcao_tras':     {'nome': 'Calção – trás', 'valor_base': 500_000, 'busca': [((1800, 1620, 1890, 1850), 90)]},
}


def _fundo(borda, minimo=0.04):
    q = (borda // 20).reshape(-1, 3)
    k = q[:, 0] * 10000 + q[:, 1] * 100 + q[:, 2]
    vals, cont = np.unique(k, return_counts=True)
    tot = cont.sum()
    cores = [borda.reshape(-1, 3)[k == v].mean(0) for v, c in zip(vals, cont) if c / tot >= minimo]
    if not cores:
        cores = [np.median(borda.reshape(-1, 3), 0)]
    return np.array(cores)


def achar_no_retangulo(rgb, area, faixa=10, limiar=75, juntar=True, encosta=6):
    """Procura um logo dentro de uma área: compara cada pixel com as cores da borda da área."""
    x0, y0, x1, y1 = area
    reg = rgb[y0:y1, x0:x1]
    borda = np.concatenate([reg[:faixa].reshape(-1, 3), reg[-faixa:].reshape(-1, 3),
                            reg[:, :faixa].reshape(-1, 3), reg[:, -faixa:].reshape(-1, 3)])
    base = _fundo(borda)
    d = np.min(np.linalg.norm(reg[:, :, None, :] - base[None, None], axis=3), axis=2)
    m = d > limiar
    if m.mean() < 0.006:
        return None
    # agrupa os pedaços (letras) e fica com o maior grupo e os que estão colados nele
    h, w = m.shape
    pequeno = Image.fromarray((m * 255).astype('uint8')).resize((max(1, w // 2), max(1, h // 2)), Image.BOX)
    pequeno = np.array(pequeno.filter(ImageFilter.MaxFilter(7))) > 40
    comps = [c for c in _componentes(pequeno) if c[4] >= 12]
    if not comps:
        return None
    comps.sort(key=lambda c: -c[4])
    g = list(comps[0][:4])
    for c in comps[1:]:
        perto = not (c[0] > g[2] + encosta or c[2] < g[0] - encosta or c[1] > g[3] + encosta or c[3] < g[1] - encosta)
        # pedaços colados ao maior, ou outros logos de bom tamanho na mesma área (ex.: dois patrocínios nas costas)
        if (perto and c[4] > 0.08 * comps[0][4]) or (juntar and c[4] > 0.12 * comps[0][4] and c[4] >= 40):
            g = [min(g[0], c[0]), min(g[1], c[1]), max(g[2], c[2]), max(g[3], c[3])]
    bx0, by0, bx1, by1 = g[0] * 2, g[1] * 2, g[2] * 2, g[3] * 2
    bw, bh = bx1 - bx0, by1 - by0
    if bw < 14 or bh < 14:
        return None
    if (bh > 0.85 * h and bw < 40) or (bw > 0.85 * w and bh < 30) or (bw > 0.9 * w and bh > 0.9 * h):
        return None      # faixa/friso do desenho, não é logo
    return [int(x0 + bx0 - 4), int(y0 + by0 - 4), int(x0 + bx1 + 4), int(y0 + by1 + 4)]


# áreas de escudo e marca do fornecedor: nunca apagar e nunca usar como fonte de tecido
MANTER = [(1060, 1124, 1250, 1300), (790, 1120, 965, 1270), (40, 1640, 205, 1790)]


def detectar_manter(img: Image.Image):
    rgb = np.array(img.convert('RGB')).astype(np.float32)
    out = []
    for area in MANTER:
        c = achar_no_retangulo(rgb, area, juntar=False)
        if c:
            out.append(c)
    return out


def detectar_molde(img: Image.Image):
    """Para cada posição do molde, devolve onde há patrocinador hoje (caixa justa) ou nada."""
    rgb = np.array(img.convert('RGB')).astype(np.float32)
    achados = []
    for slot, info in MOLDE.items():
        for i, (area, rot) in enumerate(info['busca']):
            caixa = achar_no_retangulo(rgb, area)
            if caixa:
                achados.append({'slot': slot, 'lugar': i, 'rot': rot, 'caixa': caixa, 'zona': slot})
    return achados
