"""Limpeza automática de uniformes (molde GUITAKITMAKER, textura 2048x2048).

Ideia: o desenho do uniforme é feito de listras, faixas e curvas que se repetem — na vertical, na
horizontal ou espelhadas (o molde é simétrico: lado esquerdo e direito da textura se espelham em x=1024).
Um patrocínio é o que NÃO se explica por nenhuma dessas repetições. O app estima o tecido "sem logo" de
três jeitos (mediana na vertical, mediana na horizontal, espelho) e marca como logo só o que difere dos três.

Para apagar, copia tecido de verdade de onde ele está limpo (lado espelhado, mais acima/abaixo ou ao lado),
escolhendo a cópia que melhor casa com o tecido em volta do logo. Só os pixels do logo são trocados."""
import numpy as np
from PIL import Image, ImageFilter

from .detector import ZONAS, IGNORAR, MOLDE, MANTER, achar_no_retangulo

_DEBUG = False
ESC = 2                      # detecção em 1024x1024
JANELA = 101                 # janela das medianas (em pixels de 1024) ≈ 200 px na textura
LIMIAR = 46                  # diferença mínima (0-255, maior canal) para ser logo
MANTER_EXTRA = [(1840, 1540, 1995, 1870)]     # marca do fornecedor atrás do calção (comum no GOGOSZ)
# onde procurar escudo e marca do fornecedor (peito: escudo, marca; calção: escudo)
BUSCA_ESCUDO = [(1060, 1124, 1250, 1300), (790, 1120, 965, 1270), (40, 1630, 300, 1800)]
CENTRO_ESCUDO = [(1150, 1170), (885, 1150), (150, 1695)]   # onde costumam ficar (escudo, marca, escudo do calção)
# áreas que, por si só, já separam escudo/marca do resto (o escudo do calção vai só pela caixa achada)
AREAS_FIXAS = [(1060, 1124, 1250, 1300), (790, 1120, 965, 1270)]
ESCUDO_MEIO = (930, 1120, 1118, 1360)


# ---------------- utilidades ----------------
def _mediana_eixo(a, k, eixo):
    """Mediana móvel (janela k) ao longo de um eixo, em pedaços para economizar memória. a: uint8 HxWxC."""
    from numpy.lib.stride_tricks import sliding_window_view
    r = k // 2
    pad = [(0, 0)] * a.ndim
    pad[eixo] = (r, r)
    p = np.pad(a, pad, mode='reflect')
    out = np.empty_like(a)
    H = a.shape[0]
    passo = 48
    for y in range(0, H, passo):
        y1 = min(H, y + passo)
        if eixo == 0:
            bloco = p[y:y1 + 2 * r]
            v = sliding_window_view(bloco, k, axis=0)          # (y1-y, W, C, k)
        else:
            bloco = p[y:y1]
            v = sliding_window_view(bloco, k, axis=1)          # (y1-y, W, C, k)
        out[y:y1] = np.partition(v, r, axis=-1)[..., r]
    return out


def _dif(a, b):
    return np.abs(a.astype(np.int16) - b.astype(np.int16)).max(axis=2)


def _roxo(a):
    """Áreas do molde do kitmaker (roxo e o branco-azulado colado no roxo): não são tecido."""
    a = a.astype(np.int16)
    roxo = (np.abs(a[..., 0] - 100) < 26) & (np.abs(a[..., 1] - 90) < 26) & (a[..., 2] > 225)
    branco = (np.abs(a[..., 0] - 247) <= 2) & (np.abs(a[..., 1] - 247) <= 2) & (a[..., 2] >= 253)
    if branco.any() and roxo.any():
        raio = max(4, a.shape[0] // 50)
        branco &= _dilatar(roxo, raio)
    else:
        branco[:] = False
    return roxo | branco


def _zonas_mask(H, W, esc):
    z = np.zeros((H, W), bool)
    for x0, y0, x1, y1, _ in ZONAS:
        z[y0 // esc:y1 // esc, x0 // esc:x1 // esc] = True
    for x0, y0, x1, y1 in IGNORAR:
        z[y0 // esc:y1 // esc, x0 // esc:x1 // esc] = False
    return z


def _dilatar(m, r):
    if r <= 0:
        return m
    im = Image.fromarray((m * 255).astype(np.uint8))
    if r > 6:      # raio grande: faz em escala menor (bem mais rápido) e volta ao tamanho
        f = max(2, r // 4)
        H, W = m.shape
        p = im.resize((max(1, W // f), max(1, H // f)), Image.BOX)
        p = p.filter(ImageFilter.MaxFilter(2 * (r // f) + 1))
        return np.array(p.resize((W, H), Image.NEAREST)) > 0
    return np.array(im.filter(ImageFilter.MaxFilter(2 * r + 1))) > 0


def _rotular(m):
    """Componentes conectados (4 vizinhos) com união por varredura — rápido o bastante em 1024."""
    H, W = m.shape
    lab = np.zeros((H, W), np.int32)
    pai = [0]

    def raiz(i):
        while pai[i] != i:
            pai[i] = pai[pai[i]]
            i = pai[i]
        return i
    ys, xs = np.nonzero(m)
    for y, x in zip(ys.tolist(), xs.tolist()):
        cima = lab[y - 1, x] if y else 0
        esq = lab[y, x - 1] if x else 0
        if cima and esq:
            a, b = raiz(cima), raiz(esq)
            lab[y, x] = min(a, b)
            if a != b:
                pai[max(a, b)] = min(a, b)
        elif cima or esq:
            lab[y, x] = cima or esq
        else:
            pai.append(len(pai))
            lab[y, x] = len(pai) - 1
    raizes = np.array([raiz(i) for i in range(len(pai))], np.int32)
    return raizes[lab]


# ---------------- detecção ----------------
def mascara_logos(img: Image.Image):
    """Máscara (1024x1024) dos pixels que não se explicam pelo tecido (listras verticais/horizontais),
    a diferença para o lado espelhado e a imagem reduzida."""
    rgb = np.array(img.convert('RGB').resize((1024, 1024), Image.BOX))
    peq = np.array(img.convert('RGB').resize((512, 512), Image.BOX))
    k = 125                                   # ≈ 500 px na textura: maior que quase todo logo
    bv = np.array(Image.fromarray(_mediana_eixo(peq, k, 0)).resize((1024, 1024), Image.BILINEAR))
    bh = np.array(Image.fromarray(_mediana_eixo(peq, k, 1)).resize((1024, 1024), Image.BILINEAR))
    esp = rgb[:, ::-1]
    # diferença para o espelho medida em retalhos 7x7 (texto sobre texto espelhado não "casa" por acaso)
    ds = np.full((1024, 1024), 255, np.float32)
    for dx in (-2, -1, 0, 1, 2):
        ds = np.minimum(ds, _media_caixa(_dif(rgb, np.roll(esp, dx, axis=1)).astype(np.float32), 7))
    # candidato: destoa do tecido na vertical ou na horizontal (logo ou desenho que não é listra reta)
    dv, dh = _dif(rgb, bv) > LIMIAR, _dif(rgb, bh) > LIMIAR
    cand = dv & dh
    # listras: onde só uma das medianas explica o tecido (a outra erra em boa parte da região), vale só ela
    # (logo branco sobre a listra azul de um uniforme listrado azul e branco, por exemplo)
    tv, th = _media_caixa(dv, 121), _media_caixa(dh, 121)
    extra = (dv & (th > 0.3) & (tv < 0.6 * th)) | (dh & (tv > 0.3) & (th < 0.6 * tv))
    cand &= _zonas_mask(1024, 1024, 2) & ~_dilatar(_roxo(rgb), 3)
    # sementes de logo: o lado espelhado é diferente (desenho do uniforme é simétrico)
    zm = _zonas_mask(1024, 1024, 2) & ~_dilatar(_roxo(rgb), 3)
    extra &= zm & ~cand
    fg = cand & (ds > LIMIAR)
    return cand, fg, ds, rgb, extra


def _zona_nome(cx, cy):
    for x0, y0, x1, y1, z in ZONAS:
        if x0 <= cx < x1 and y0 <= cy < y1:
            return z
    return 'outro'


def _slot_de(caixa):
    """Posição do molde mais provável para uma caixa (pelo centro); None se não bater com nenhuma."""
    cx, cy = (caixa[0] + caixa[2]) / 2, (caixa[1] + caixa[3]) / 2
    melhor = None
    for slot, info in MOLDE.items():
        for i, ((x0, y0, x1, y1), rot) in enumerate(info['busca']):
            m = 30
            if x0 - m <= cx <= x1 + m and y0 - m <= cy <= y1 + m:
                d = abs(cx - (x0 + x1) / 2) + abs(cy - (y0 + y1) / 2)
                if melhor is None or d < melhor[0]:
                    melhor = (d, slot, i, rot)
    return melhor[1:] if melhor else (None, None, 0)


def detectar_manter(img):
    rgb = np.array(img.convert('RGB')).astype(np.float32)
    out = []
    for area in BUSCA_ESCUDO:
        c = achar_no_retangulo(rgb, area, juntar=False, encosta=1)
        if c:
            out.append(c)
    return out


def _media_caixa(m, k, kw=None):
    """Média de uma máscara numa janela k (altura) x kw (largura) — imagem integral."""
    kw = kw or k
    ry, rx = k // 2, kw // 2
    p = np.pad(m.astype(np.float32), ((ry + 1, k - ry - 1), (rx + 1, kw - rx - 1)))
    s = p.cumsum(0).cumsum(1)
    H, W = m.shape
    return (s[k:k + H, kw:kw + W] - s[:H, kw:kw + W] - s[k:k + H, :W] + s[:H, :W]) / (k * kw)


def _escudos(cand):
    """Escudo e marca do fornecedor: em cada área de busca, o desenho mais "quadrado" e cheio perto do
    lugar de costume (só os pixels dentro da área contam, para não puxar patrocínio vizinho)."""
    out = []
    esc = None
    for ia, ((x0, y0, x1, y1), (ecx, ecy)) in enumerate(zip(BUSCA_ESCUDO, CENTRO_ESCUDO)):
        a = (x0 // 2, y0 // 2, x1 // 2, y1 // 2)
        sub = cand[a[1]:a[3], a[0]:a[2]]
        if sub.sum() < 40:
            continue
        lab = _rotular(_dilatar(sub, 1))
        total = np.bincount(lab[sub], minlength=lab.max() + 1)
        melhor, v = 0, None
        for u in np.nonzero(total >= 40)[0]:
            if u == 0:
                continue
            ys, xs = np.nonzero(lab == u)
            w, h = xs.max() - xs.min() + 1, ys.max() - ys.min() + 1
            # componente cortado pela borda da área: provavelmente é patrocínio vizinho
            corta = (xs.min() == 0) + (ys.min() == 0) + (xs.max() == sub.shape[1] - 1) + (ys.max() == sub.shape[0] - 1)
            dist = np.hypot((xs.min() + xs.max() + 2 * a[0]) - ecx, (ys.min() + ys.max() + 2 * a[1]) - ecy)
            nota = total[u] * (min(w, h) / max(w, h)) ** 2 / (1 + dist / 60) ** 2 / (1 + corta)
            if nota > melhor:
                melhor, v = nota, u
        if v is None:
            continue
        ys, xs = np.nonzero(lab == v)
        bx0, bx1, by0, by1 = xs.min() + a[0], xs.max() + 1 + a[0], ys.min() + a[1], ys.max() + 1 + a[1]
        out.append([int(bx0 * 2 - 4), int(by0 * 2 - 4), int(bx1 * 2 + 4), int(by1 * 2 + 4)])
        if ia == 0:
            esc = out[-1]
    # escudo no meio do peito (São Paulo, por exemplo): só procura se no lugar de costume não havia escudo de verdade
    if esc is None or min(esc[2] - esc[0], esc[3] - esc[1]) < 70:
        x0, y0, x1, y1 = ESCUDO_MEIO
        a = (x0 // 2, y0 // 2, x1 // 2, y1 // 2)
        sub = cand[a[1]:a[3], a[0]:a[2]]
        if sub.sum() >= 80:
            lab = _rotular(_dilatar(sub, 1))
            tot = np.bincount(lab[sub], minlength=lab.max() + 1)
            tot[0] = 0
            u = int(tot.argmax())
            ys, xs = np.nonzero(lab == u)
            w, h = xs.max() - xs.min() + 1, ys.max() - ys.min() + 1
            cx = (xs.min() + xs.max()) / 2 + a[0]
            # escudo: quase quadrado, grande, centrado em x = 1024 e cheio (não é texto)
            if min(w, h) / max(w, h) >= 0.6 and min(w, h) >= 35 and abs(cx - 512) < 12 and tot[u] >= 0.3 * w * h:
                if esc is not None:
                    out.remove(esc)
                out.append([int((xs.min() + a[0]) * 2 - 4), int((ys.min() + a[1]) * 2 - 4),
                            int((xs.max() + 1 + a[0]) * 2 + 4), int((ys.max() + 1 + a[1]) * 2 + 4)])
    return out


def _agrupar(cr, regiao, raio, fg):
    """Junta pedaços próximos em marcas; o que ficar grande demais é separado com raio menor e,
    se ainda assim não couber, pelas sementes de logo."""
    out = []
    lab = _rotular(_dilatar(cr, raio) & regiao)
    for v in np.unique(lab):
        if v == 0:
            continue
        ps = (lab == v) & cr
        if ps.sum() < 30:
            continue
        ys, xs = np.nonzero(ps)
        x0, x1, y0, y1 = int(xs.min()), int(xs.max()) + 1, int(ys.min()), int(ys.max()) + 1
        w, h = x1 - x0, y1 - y0
        if max(w, h) <= 260 and w * h <= 260 * 140 and (max(w, h) / max(1, min(w, h)) <= 7 or max(w, h) < 80):
            out.append((x0, y0, x1, y1, ps))
        elif raio > 2:
            out += _agrupar(ps, regiao, 2, fg)
        else:
            sub = _rotular(_dilatar(ps & fg, 6) & _dilatar(ps, 2))
            for u in np.unique(sub):
                if u == 0:
                    continue
                pu = (sub == u) & ps
                if (pu & fg).sum() < 15:
                    continue
                ys, xs = np.nonzero(pu)
                out.append((int(xs.min()), int(ys.min()), int(xs.max()) + 1, int(ys.max()) + 1, pu))
    return out


def detectar(img: Image.Image):
    """Lista de logos achados: caixa (coordenadas 2048), posição do molde e se é escudo/marca.
    'desenho': parece parte do desenho do uniforme (vem desmarcado na revisão)."""
    cand, fg, ds, rgb, extra = mascara_logos(img)
    # chuvisco do tecido (pontinhos da trama): fora
    lab = _rotular(cand)
    tam = np.bincount(lab.ravel()); tam[0] = 0
    cand &= tam[lab] >= 10
    estrito = cand.copy()
    # listras: o que só uma mediana acusa entra apenas colado num logo de verdade (fundo do logo, letras na listra)
    lab = _rotular(extra)
    tam = np.bincount(lab.ravel()); tam[0] = 0
    extra &= tam[lab] >= 10
    extra &= _dilatar(estrito & (_media_caixa(estrito, 13) >= 0.12), 10)
    fg &= cand
    # linhas finas (borda de listra, contorno, degradê) não ligam um logo ao outro: só o miolo denso agrupa
    nucleo = cand & (_media_caixa(cand, 13) >= 0.12)
    # linhas retas compridas (borda de listra, friso): também não agrupam
    linha = (_media_caixa(cand, 61, 1) >= 0.95) | (_media_caixa(cand, 1, 61) >= 0.95)
    nucleo &= ~_dilatar(linha, 1)
    manter = _escudos(cand)
    caixa_fix = np.zeros_like(fg)
    for m in AREAS_FIXAS + MANTER_EXTRA:
        caixa_fix[m[1] // 2:m[3] // 2 + 1, m[0] // 2:m[2] // 2 + 1] = True
    caixa_esc = np.zeros_like(fg)
    for m in manter:
        caixa_esc[max(0, m[1] // 2):m[3] // 2 + 1, max(0, m[0] // 2):m[2] // 2 + 1] = True
    # nas áreas fixas, cada pedaço vai inteiro para o lado onde está a maior parte dele; no escudo achado, pixel a pixel
    lab0 = _rotular(_dilatar(nucleo, 2))
    n0 = lab0.max() + 1
    tot = np.bincount(lab0[nucleo], minlength=n0)
    den = np.bincount(lab0[nucleo & caixa_fix], minlength=n0)
    lado = den >= 0.6 * np.maximum(tot, 1)
    lado[0] = False
    dentro = (lado[lab0] & _dilatar(nucleo, 2)) | caixa_esc
    caixas = []
    for regiao, raio in ((~dentro, 5), (dentro, 3)):   # escudo/marca nunca se mistura com patrocínio ao lado
        for x0, y0, x1, y1, ps in _agrupar(nucleo & regiao, regiao, raio, fg):
            # devolve os traços finos do próprio logo (letras vazadas, contornos) que ficaram fora do miolo
            px = ps | ((cand | extra) & regiao & _dilatar(ps, 8))
            ys, xs = np.nonzero(px)
            caixas.append((int(xs.min()), int(ys.min()), int(xs.max()) + 1, int(ys.max()) + 1, px, ps))
    # desenhos grandes do uniforme (faixa diagonal, recortes): logo encostado neles provavelmente é do desenho
    nuc_e = estrito & (_media_caixa(estrito, 13) >= 0.12) & nucleo
    labd = _rotular(_dilatar(nuc_e, 2))
    nd = labd.max() + 1
    ys_, xs_ = np.nonzero(labd)
    grande = np.zeros(nd, bool)
    if len(ys_):
        mnx = np.full(nd, 99999); mxx = np.zeros(nd, int); mny = np.full(nd, 99999); mxy = np.zeros(nd, int)
        np.minimum.at(mnx, labd[ys_, xs_], xs_); np.maximum.at(mxx, labd[ys_, xs_], xs_)
        np.minimum.at(mny, labd[ys_, xs_], ys_); np.maximum.at(mxy, labd[ys_, xs_], ys_)
        grande = np.maximum(mxx - mnx, mxy - mny) > 260
        grande[0] = False
    desenho = nuc_e & grande[labd]
    borda = _dilatar(_roxo(rgb), 2) | ~_zonas_mask(1024, 1024, 2)
    itens = []
    for x0, y0, x1, y1, pix, miolo in caixas:
        w, h = x1 - x0, y1 - y0
        if max(w, h) > 260 or w * h > 260 * 140:      # grande demais: é desenho do uniforme
            continue
        if max(w, h) / max(1, min(w, h)) > 9:   # faixa/friso/painel lateral comprido
            continue
        if _roxo(rgb[max(0, y0 - 4):y1 + 4, max(0, x0 - 4):x1 + 4]).mean() > 0.10:   # borda do molde
            continue
        n = int(pix.sum())
        if n / (w * h) < 0.07 and max(w, h) > 30:       # traço fino e comprido (curva, contorno): desenho
            continue
        caixa = [max(0, x0 * 2 - 12), max(0, y0 * 2 - 12), min(2048, x1 * 2 + 12), min(2048, y1 * 2 + 12)]
        cx, cy = (caixa[0] + caixa[2]) / 2, (caixa[1] + caixa[3]) / 2
        slot, lugar, rot = _slot_de(caixa)
        semente = (pix & fg).sum()
        com_semente = semente >= 15 and semente >= 0.08 * n
        if not com_semente:
            # igual dos dois lados: só é patrocínio se estiver num lugar de patrocínio e parecer texto
            # (várias letras soltas); estrelas, recortes e pontas de faixa ficam
            nlet = len(np.unique(_rotular(pix))) - 1
            if slot is None or max(w, h) < 30 or nlet < 4:
                continue
        area = (caixa[2] - caixa[0]) * (caixa[3] - caixa[1])
        def dentro_de(m, f):
            return (max(0, min(caixa[2], m[2]) - max(caixa[0], m[0])) *
                    max(0, min(caixa[3], m[3]) - max(caixa[1], m[1]))) > f * area
        # escudo/marca: caixa achada no lugar do escudo, ou item quase todo dentro das áreas de escudo/marca
        escudo = any(dentro_de(m, 0.4) for m in manter) or any(dentro_de(m, 0.7) for m in AREAS_FIXAS)
        na_marca_calcao = any(dentro_de(m, 0.7) for m in MANTER_EXTRA)
        anel = _dilatar(pix, 4) & ~pix
        colado = (anel & desenho & ~pix).sum() / max(1, anel.sum())
        na_borda = (_dilatar(miolo, 3) & borda).sum() >= 8      # cortado pela costura: estampa do tecido
        # pedaço de uma forma maior (faixa, listra): a mesma cor continua para fora da caixa do item
        cor = np.median(rgb[pix], axis=0)
        X0, Y0, X1, Y1 = max(0, x0 - 6), max(0, y0 - 6), min(1024, x1 + 6), min(1024, y1 + 6)
        perto = _dilatar(pix[Y0:Y1, X0:X1], 4)
        faixa = np.ones_like(perto); faixa[y0 - Y0:y1 - Y0, x0 - X0:x1 - X0] = False
        faixa &= perto
        igual = np.abs(rgb[Y0:Y1, X0:X1].astype(np.int16) - cor).max(axis=2) < 30
        continua = (faixa & igual).sum() / max(1, faixa.sum())
        cheio = n / (w * h)
        g = rgb[y0:y1, x0:x1].astype(np.int16)
        gr = np.zeros(g.shape[:2], bool)
        gr[:, 1:] |= np.abs(g[:, 1:] - g[:, :-1]).max(axis=2) > 40
        gr[1:, :] |= np.abs(g[1:] - g[:-1]).max(axis=2) > 40
        bordas = (_dilatar(gr, 1) & pix[y0:y1, x0:x1]).sum() / max(1, n)
        alongado = max(w, h) / max(1, min(w, h))
        # pedaço de listra/faixa lisa ou em degradê (quase sem contorno interno, comprido)
        faixa_lisa = alongado >= 2.8 and (cheio >= 0.8 or bordas < 0.3)
        if _DEBUG:
            print('item', [x0 * 2, y0 * 2, x1 * 2, y1 * 2], 'continua', round(continua, 2), 'cheio', round(cheio, 2),
                  'bordas', round(bordas, 2), 'along', round(alongado, 1))
        itens.append({'caixa': caixa, 'slot': slot, 'lugar': lugar, 'rot': rot, 'zona': _zona_nome(cx, cy),
                      'escudo': bool(escudo), 'desenho': bool((colado > 0.2 or na_borda or continua > 0.6 or faixa_lisa) and not escudo),
                      '_mc': na_marca_calcao})
    # atrás do calção: a marca do fornecedor costuma ser o item mais à direita; o resto é patrocínio
    mc = [it for it in itens if it['_mc']]
    for it in mc:
        it['escudo'] = it is max(mc, key=lambda t: t['caixa'][2])
    for it in itens:
        it.pop('_mc', None)
    itens.sort(key=lambda it: (it['caixa'][1] // 200, it['caixa'][0]))
    return itens


# ---------------- preenchimento ----------------
class _SAT:
    """Soma acumulada para saber em O(1) se um retângulo toca área proibida."""
    def __init__(self, m):
        self.s = np.pad(m.astype(np.int32).cumsum(0).cumsum(1), ((1, 0), (1, 0)))

    def soma(self, y0, x0, y1, x1):
        s = self.s
        return s[y1, x1] - s[y0, x1] - s[y1, x0] + s[y0, x0]


def limpar(img: Image.Image, itens, manter=()):
    """Apaga os itens (dicts de detectar() ou caixas desenhadas {'caixa': [...]}).
    'manter': caixas que nunca servem de fonte de tecido (escudo, marca, itens que o usuário quis manter)."""
    a = np.array(img.convert('RGBA')).copy()
    H, W = a.shape[:2]
    rgb = a[..., :3].astype(np.float32)
    base = _dilatar(_roxo(a[..., :3]), 2)
    protegido = np.zeros((H, W), bool)          # escudo/marca: nunca trocar esses pixels
    for mm in manter:
        base[max(0, mm[1] - 4):mm[3] + 4, max(0, mm[0] - 4):mm[2] + 4] = True
        protegido[max(0, mm[1] - 2):mm[3] + 2, max(0, mm[0] - 2):mm[2] + 2] = True
    # área de cada item: a caixa inteira (a troca só acontece onde a imagem difere do tecido limpo)
    regs = []
    for it in itens:
        x0, y0, x1, y1 = [int(v) for v in it['caixa'][:4]]
        x0, y0, x1, y1 = max(0, x0), max(0, y0), min(W, x1), min(H, y1)
        if x1 - x0 < 4 or y1 - y0 < 4:
            continue
        regs.append((x0, y0, x1, y1, np.ones((y1 - y0, x1 - x0), bool)))
    pend = np.zeros((H, W), bool)
    for x0, y0, x1, y1, loc in regs:
        pend[max(0, y0 - 4):y1 + 4, max(0, x0 - 4):x1 + 4] = True
    zonas = [(x0, y0, x1, y1) for x0, y0, x1, y1, _ in ZONAS]

    def zona_de(cx, cy):
        for z in zonas:
            if z[0] <= cx < z[2] and z[1] <= cy < z[3]:
                return z
        return (0, 0, W, H)

    ordem = sorted(range(len(regs)), key=lambda i: regs[i][4].sum())
    for i in ordem:
        for vez in range(3):
            x0, y0, x1, y1, loc = regs[i]
            if not loc.any():
                continue
            proib = base | pend
            zx0, zy0, zx1, zy1 = zona_de((x0 + x1) // 2, (y0 + y1) // 2)
            # anel: faixa de tecido em volta da caixa (fora dela), usada para escolher a melhor cópia
            R = 8
            alvo, loc_, anel = None, None, None
            X0, Y0, X1, Y1 = max(0, x0 - R), max(0, y0 - R), min(W, x1 + R), min(H, y1 + R)
            x0, y0, x1, y1, xo, yo = X0, Y0, X1, Y1, x0 - X0, y0 - Y0
            h, w = y1 - y0, x1 - x0
            alvo = rgb[y0:y1, x0:x1]
            loc = np.zeros((h, w), bool)
            loc[yo:yo + regs[i][3] - regs[i][1], xo:xo + regs[i][2] - regs[i][0]] = True
            bt = base[y0:y1, x0:x1]
            tmask = loc & ~bt                       # pixels de tecido a refazer (o molde fica como está)
            anel = ~loc & ~bt & ~pend[y0:y1, x0:x1]
            lados = []                              # anel separado por lado: cima, baixo, esquerda, direita
            for sl in ((slice(0, yo), slice(None)), (slice(yo + regs[i][3] - regs[i][1], None), slice(None)),
                       (slice(None), slice(0, xo)), (slice(None), slice(xo + regs[i][2] - regs[i][0], None))):
                m = np.zeros_like(anel); m[sl] = anel[sl]
                if m.sum() >= 12:
                    lados.append(m)
            cands = []

            def erro(fonte):
                if not lados:
                    return 40.0
                es = sorted(float(np.abs(fonte[m] - alvo[m]).mean()) for m in lados)
                return float(np.mean(es[:3])) if len(es) > 3 else float(np.mean(es[:max(1, len(es) - 1)])) if len(es) > 2 else float(np.mean(es))

            ntm = max(1, int(tmask.sum()))

            def valido(sy0, sx0, espelho=False):
                """Máscara dos pixels da fonte que servem (None se a fonte não serve quase nada)."""
                if sy0 < 0 or sx0 < 0 or sy0 + h > H or sx0 + w > W:
                    return None
                p = proib[sy0:sy0 + h, sx0:sx0 + w]
                if espelho:
                    p = p[:, ::-1]
                ruim = p & tmask
                if ruim.sum() > 0.35 * ntm:
                    return None
                return ~ruim

            def avaliar(fonte, nome, pen, ok=None, desl=None):
                if ok is None:
                    return
                falta = 1 - (ok & tmask).sum() / ntm
                cands.append((erro(fonte) + pen + falta * 25, nome, fonte, ok, desl))
            # 1) espelho (o molde é simétrico em x = 1024)
            for dx in (-4, -2, 0, 2, 4):
                sx0 = W - x1 + dx
                ok = valido(y0, sx0, True)
                if ok is not None:
                    avaliar(rgb[y0:y1, sx0:sx0 + w][:, ::-1], 'espelho', 0, ok, ('e', sx0 + w - 1 + x0))
            # 2) mesmo tecido mais acima/abaixo ou ao lado
            hb, wb = regs[i][3] - regs[i][1], regs[i][2] - regs[i][0]
            for dy in list(range(hb + 2, 3 * h + 260, 6)) + list(range(-hb - 2, -3 * h - 260, -6)):
                sy0 = y0 + dy
                if sy0 < zy0 - R or sy0 + h > zy1 + R:
                    continue
                ok = valido(sy0, x0)
                if ok is not None:
                    avaliar(rgb[sy0:sy0 + h, x0:x1], 'vertical', abs(dy) * 0.003, ok, ('v', dy))
            for dx in list(range(wb + 2, 3 * w + 260, 6)) + list(range(-wb - 2, -3 * w - 260, -6)):
                sx0 = x0 + dx
                if sx0 < zx0 - R or sx0 + w > zx1 + R:
                    continue
                ok = valido(y0, sx0)
                if ok is not None:
                    avaliar(rgb[y0:y1, sx0:sx0 + w], 'horizontal', abs(dx) * 0.003, ok, ('h', dx))
            # 3) interpolação linha a linha (faixa horizontal lisa) e coluna a coluna (listra vertical lisa)
            for nome, f in (('interp_h', _interp_h), ('interp_v', _interp_v)):
                r_ = f(rgb, proib, x0, y0, x1, y1)
                if r_ is not None:
                    avaliar(r_, nome, 1.5, np.ones_like(tmask))
            cands.sort(key=lambda c: c[0])
            # 4) por colunas: cada faixa escolhe seu deslocamento vertical (listras com curvas)
            col = _por_colunas(rgb, proib, tmask, x0, y0, x1, y1, zy0, zy1, alvo, anel, hb)
            if col is not None and (not cands or col[0] < cands[0][0] - 1.0):
                cands.insert(0, (col[0], 'colunas', col[2], np.ones_like(tmask), None))
            # monta a fonte: cada pixel vem da melhor cópia que serve naquele ponto
            fonte = _interpolar(rgb, proib, x0, y0, x1, y1, zy0, zy1)
            resto = tmask.copy()
            for c in cands[:12]:
                usar = resto & c[3]
                if usar.any():
                    fonte[usar] = c[2][usar]
                    resto &= ~usar
                if not resto.any():
                    break
            melhor = cands[0] if cands else (99, 'interpolado')
            if vez < 2 and len(melhor) > 4 and melhor[4] is not None:
                outros = pend.copy()
                outros[max(0, regs[i][1] - 4):regs[i][3] + 4, max(0, regs[i][0] - 4):regs[i][2] + 4] = False
                nova = _estender(rgb, base, regs[i][:4], melhor[4], outros)
                if nova is not None:
                    bx0, by0, bx1, by1 = nova
                    regs[i] = (bx0, by0, bx1, by1, np.ones((by1 - by0, bx1 - bx0), bool))
                    pend[max(0, by0 - 4):by1 + 4, max(0, bx0 - 4):bx1 + 4] = True
                    continue
            # caixa grande sem cópia boa (logo sobre listras com curva, degradê): apaga só as cores que não
            # existem no tecido em volta e preenche por difusão dos vizinhos
            if min(h, w) > 100 and h * w > 150 * 150 and (melhor[1] in ('interp_h', 'interp_v', 'interpolado') or melhor[0] > 6):
                nov = _novidade(alvo, anel, tmask)
                if 0 < nov.sum() < 0.6 * tmask.sum():
                    m2 = _dilatar(nov, 5) & tmask
                    fonte = alvo.copy()
                    fonte[m2] = _interp_mascara(alvo, ~m2 & ~bt)[m2]
                    melhor = (melhor[0], 'difusao')
            if _DEBUG:
                print('item', (x0, y0, x1, y1), melhor[1], round(melhor[0], 1), [(round(c[0], 1), c[1]) for c in cands[:3]], int(resto.sum()))
            # troca só onde a imagem difere do tecido limpo (dentro da área do logo), com borda suave
            dif = np.abs(fonte - alvo).max(axis=2)
            troca = tmask & (dif > 18)
            troca = _dilatar(troca, 2) & tmask & ~protegido[y0:y1, x0:x1]
            alfa = np.array(Image.fromarray((troca * 255).astype(np.uint8)).filter(ImageFilter.GaussianBlur(1.0)),
                            np.float32)[..., None] / 255
            alfa = np.maximum(alfa, troca[..., None].astype(np.float32))
            rgb[y0:y1, x0:x1] = alvo * (1 - alfa) + fonte * alfa
            break
        a0_, b0_, a1_, b1_ = regs[i][:4]
        pend[max(0, b0_ - 4):b1_ + 4, max(0, a0_ - 4):a1_ + 4] = False
        for j in ordem:     # devolve a máscara dos itens que ainda faltam e cruzam este retângulo
            if j == i:
                continue
            a0, b0, a1, b1, l2 = regs[j]
            if a0 < x1 + 8 and a1 > x0 - 8 and b0 < y1 + 8 and b1 > y0 - 8 and ordem.index(j) > ordem.index(i):
                pend[max(0, b0 - 4):b1 + 4, max(0, a0 - 4):a1 + 4] = True
    a[..., :3] = np.clip(rgb + 0.5, 0, 255).astype(np.uint8)
    return Image.fromarray(a, 'RGBA')


def _estender(rgb, base, caixa, desl, outros=None, maximo=48, limiar=40, frac=0.2):
    """O logo pode ter um fundo próprio (retângulo branco sobre a listra, por exemplo) que passa da caixa.
    Com a cópia escolhida, vê se as linhas/colunas logo fora da caixa também diferem da cópia; se sim,
    aumenta a caixa até onde o tecido volta a casar. Devolve a caixa nova ou None."""
    H, W = base.shape
    x0, y0, x1, y1 = caixa
    tipo, d = desl

    def fonte(ya, yb, xa, xb):
        if tipo == 'v':
            ya, yb = ya + d, yb + d
        elif tipo == 'h':
            xa, xb = xa + d, xb + d
        else:                                   # espelho: coluna x vem de d - x
            xa, xb = d - (xb - 1), d - xa + 1
        if ya < 0 or xa < 0 or yb > H or xb > W:
            return None
        if base[ya:yb, xa:xb].mean() > 0.3:
            return None
        blk = rgb[ya:yb, xa:xb]
        return blk[:, ::-1] if tipo == 'e' else blk

    def ruim(ya, yb, xa, xb, ry=0, rx=0):
        """Faixa (ya:yb, xa:xb) difere da cópia, é cor chapada e continua a faixa vizinha do lado da caixa
        (deslocada de ry, rx) — fundo do logo que vaza; um desenho que só começa ali fora não conta."""
        if ya < 0 or xa < 0 or yb > H or xb > W or base[ya:yb, xa:xb].mean() > 0.3:
            return False
        if outros is not None and outros[ya:yb, xa:xb].any():      # encostou em outro logo: para
            return False
        f = fonte(ya, yb, xa, xb)
        if f is None:
            return False
        orig = rgb[ya:yb, xa:xb]
        dif = np.abs(orig - f).max(axis=2) > limiar
        if dif.mean() <= frac:
            return False
        # fundo de logo é cor chapada; trama/estampa diferente não conta
        if float(orig[dif].std(axis=0).max()) >= 22:
            return False
        viz = rgb[ya + ry:yb + ry, xa + rx:xb + rx]
        if viz.shape != orig.shape:
            return False
        return (np.abs(orig - viz).max(axis=2)[dif] < 30).mean() > 0.7

    k = {'c': 0, 'b': 0, 'e': 0, 'd': 0}
    while k['c'] < maximo and ruim(y0 - k['c'] - 1, y0 - k['c'], x0, x1, ry=1):
        k['c'] += 1
    while k['b'] < maximo and ruim(y1 + k['b'], y1 + k['b'] + 1, x0, x1, ry=-1):
        k['b'] += 1
    while k['e'] < maximo and ruim(y0, y1, x0 - k['e'] - 1, x0 - k['e'], rx=1):
        k['e'] += 1
    while k['d'] < maximo and ruim(y0, y1, x1 + k['d'], x1 + k['d'] + 1, rx=-1):
        k['d'] += 1
    if not any(v >= 2 for v in k.values()):
        return None
    m = {a: (v + 4 if v >= 2 else 0) for a, v in k.items()}
    return (max(0, x0 - m['e']), max(0, y0 - m['c']), min(W, x1 + m['d']), min(H, y1 + m['b']))


def _novidade(alvo, anel, tmask, limiar=45):
    """Pixels da caixa com cor que não aparece no tecido em volta (o logo)."""
    viz = alvo[anel]
    if len(viz) < 30:
        return np.zeros_like(tmask)
    q = (viz // 16).astype(np.int32)
    k = q[:, 0] * 10000 + q[:, 1] * 100 + q[:, 2]
    vals, cont = np.unique(k, return_counts=True)
    ordem = np.argsort(-cont)[:48]
    paleta = [viz[k == vals[i]].mean(0) for i in ordem if cont[i] >= max(3, 0.003 * len(viz))]
    if not paleta:
        return np.zeros_like(tmask)
    d = np.full(tmask.shape, 999.0, np.float32)
    for c in paleta:
        d = np.minimum(d, np.abs(alvo - c).max(axis=2))
    return (d > limiar) & tmask


def _interp_mascara(img, conhecido):
    """Preenche o que falta interpolando ao longo do eixo em que o tecido muda menos (listra vertical:
    coluna a coluna; faixa horizontal: linha a linha). O que sobrar vai por difusão."""
    gy = np.abs(np.diff(img, axis=0)).max(axis=2)[conhecido[1:] & conhecido[:-1]].mean() if conhecido.any() else 0
    gx = np.abs(np.diff(img, axis=1)).max(axis=2)[conhecido[:, 1:] & conhecido[:, :-1]].mean() if conhecido.any() else 0
    vertical = gy <= gx
    a = img if vertical else img.transpose(1, 0, 2)
    k = conhecido if vertical else conhecido.T
    out = a.copy()
    falta = ~k
    idx = np.arange(a.shape[0])
    for x in range(a.shape[1]):
        col = k[:, x]
        if col.all() or col.sum() < 2:
            continue
        for c in range(3):
            out[~col, x, c] = np.interp(idx[~col], idx[col], a[col, x, c])
        falta[:, x] = False
    out = out if vertical else out.transpose(1, 0, 2)
    falta = falta if vertical else falta.T
    if falta.any():
        out = _difusao(out, ~falta)
    return out


def _difusao(img, conhecido):
    """Preenche os pixels desconhecidos com a média dos conhecidos em volta, do raio menor para o maior."""
    out = img.copy()
    falta = ~conhecido
    k_ = conhecido.astype(np.float32)
    for k in (5, 9, 17, 33, 65, 129):
        if not falta.any():
            break
        den = _media_caixa(k_, k)
        ok = falta & (den > 0.08)
        if ok.any():
            for c in range(3):
                num = _media_caixa(img[..., c] * k_, k)
                out[..., c][ok] = (num[ok] / den[ok])
            falta &= ~ok
    return out


def _por_colunas(rgb, proib, tmask, x0, y0, x1, y1, zy0, zy1, alvo, anel, hb):
    h, w = tmask.shape
    H = rgb.shape[0]
    fonte = alvo.copy()
    erros = []
    faixa = 8
    for c0 in range(0, w, faixa):
        c1 = min(w, c0 + faixa)
        tcol = tmask[:, c0:c1]
        if not tcol.any():
            continue
        acol = anel[:, c0:c1]
        melhor = None
        for dy in list(range(hb + 2, 3 * h + 320, 4)) + list(range(-hb - 2, -3 * h - 320, -4)):
            sy0 = y0 + dy
            if sy0 < max(0, zy0 - 8) or sy0 + h > min(H, zy1 + 8):
                continue
            if proib[sy0:sy0 + h, x0 + c0:x0 + c1][tcol].any():
                continue
            src = rgb[sy0:sy0 + h, x0 + c0:x0 + c1]
            e = float(np.abs(src[acol] - alvo[:, c0:c1][acol]).mean()) if acol.any() else 30.0
            e += abs(dy) * 0.002
            if melhor is None or e < melhor[0]:
                melhor = (e, src)
        if melhor is None:
            return None
        fonte[:, c0:c1] = melhor[1]
        erros.append(melhor[0])
    if not erros:
        return None
    return (float(np.mean(erros)), 'colunas', fonte)


def _ponta(rgb, proib, pts):
    """Primeiro pixel livre ao longo de uma lista de coordenadas (y, x)."""
    for y, x in pts:
        if 0 <= y < rgb.shape[0] and 0 <= x < rgb.shape[1] and not proib[y, x]:
            return rgb[y, x]
    return None


def _interp_h(rgb, proib, x0, y0, x1, y1):
    out = np.empty((y1 - y0, x1 - x0, 3), np.float32)
    t = (np.arange(x0, x1) - (x0 - 1)) / max(1, x1 - x0 + 1)
    for y in range(y0, y1):
        a = _ponta(rgb, proib, [(y, x0 - 1 - k) for k in range(40)])
        b = _ponta(rgb, proib, [(y, x1 + k) for k in range(40)])
        if a is None or b is None:
            return None
        out[y - y0] = a[None] * (1 - t[:, None]) + b[None] * t[:, None]
    return out


def _interp_v(rgb, proib, x0, y0, x1, y1):
    out = np.empty((y1 - y0, x1 - x0, 3), np.float32)
    t = (np.arange(y0, y1) - (y0 - 1)) / max(1, y1 - y0 + 1)
    for x in range(x0, x1):
        a = _ponta(rgb, proib, [(y0 - 1 - k, x) for k in range(40)])
        b = _ponta(rgb, proib, [(y1 + k, x) for k in range(40)])
        if a is None or b is None:
            return None
        out[:, x - x0] = a[None] * (1 - t[:, None]) + b[None] * t[:, None]
    return out


def _interpolar(rgb, proib, x0, y0, x1, y1, zy0, zy1):
    """Último recurso: em cada coluna, mistura o tecido limpo de cima e de baixo."""
    out = rgb[y0:y1, x0:x1].copy()
    for x in range(x0, x1):
        yu = y0 - 1
        while yu > zy0 and proib[yu, x]:
            yu -= 1
        yd = y1
        while yd < zy1 - 1 and proib[yd, x]:
            yd += 1
        t = ((np.arange(y0, y1) - yu) / max(1, yd - yu))[:, None]
        out[:, x - x0] = rgb[yu, x] * (1 - t) + rgb[yd, x] * t
    return out


def desenhar(img, itens, largura=1024):
    from PIL import ImageDraw
    s = largura / 2048
    im = img.convert('RGB').resize((largura, largura), Image.LANCZOS)
    d = ImageDraw.Draw(im)
    for i, it in enumerate(itens):
        c = it['caixa']
        cor = (130, 130, 130) if it.get('escudo') else (0, 200, 255) if it.get('desenho') else (255, 0, 255)
        d.rectangle([c[0] * s, c[1] * s, c[2] * s, c[3] * s], outline=cor, width=2)
        d.text((c[0] * s + 2, c[1] * s - 11), str(i + 1), fill=cor)
    return im
