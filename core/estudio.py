"""Estúdio de uniformes: troca de cores do tecido (mantendo sombras e textura), modelos comemorativos e
estrelas de campeão acima do escudo."""
import math
import numpy as np
from PIL import Image, ImageDraw

PRESETS = {
    'dourado': {'nome': 'Dourado de campeão', 'cores': ['#c9a227', '#141414', '#f1e3a6']},
    'preto_dourado': {'nome': 'Preto e dourado', 'cores': ['#151515', '#c9a227', '#2a2a2a']},
    'branco_total': {'nome': 'Branco total', 'cores': ['#f3f3f3', '#d6d6d6', '#bdbdbd']},
    'retro': {'nome': 'Retrô (anos 80)', 'cores': ['#efe6d2', None, None], 'retro': True},
    'rosa': {'nome': 'Outubro Rosa', 'cores': ['#f06fa3', '#ffffff', '#b8326e']},
    'azul': {'nome': 'Novembro Azul', 'cores': ['#2b6fd6', '#ffffff', '#163e7a']},
    'aniversario': {'nome': 'Aniversário do clube', 'cores': [None, '#c9a227', None]},
    'amarelo': {'nome': 'Setembro Amarelo', 'cores': ['#f2c230', '#ffffff', '#a8801a']},
    'vermelho': {'nome': 'Dezembro Vermelho', 'cores': ['#d32f2f', '#ffffff', '#8e1b1b']},
    'natal': {'nome': 'Edição de Natal', 'cores': ['#c1272d', '#ffffff', '#14532d']},
    'treino': {'nome': 'Edição especial escura', 'cores': ['#1d2430', '#3a4556', None]},
}


def _hex(c):
    c = c.lstrip('#')
    return np.array([int(c[i:i + 2], 16) for i in (0, 2, 4)], np.float32)


def _hexs(v):
    return '#%02x%02x%02x' % tuple(int(max(0, min(255, x))) for x in v)


def _roxo(a):
    r, g, b = a[..., 0], a[..., 1], a[..., 2]
    return ((np.abs(r - 100) < 30) & (np.abs(g - 90) < 30) & (b > 220)) | \
           ((np.abs(r - 247) <= 3) & (np.abs(g - 247) <= 3) & (b >= 252))


def paleta(img: Image.Image, k=5):
    """Cores principais do tecido (k-means simples), da mais usada para a menos usada."""
    a = np.array(img.convert('RGB').resize((256, 256), Image.BOX)).reshape(-1, 3).astype(np.float32)
    a = a[~_roxo(a)]
    if len(a) < 50:
        return []
    rnd = np.random.default_rng(1)
    cent = a[rnd.choice(len(a), k, replace=False)]
    for _ in range(14):
        d = ((a[:, None, :] - cent[None]) ** 2).sum(2)
        lab = d.argmin(1)
        for i in range(k):
            if (lab == i).any():
                cent[i] = a[lab == i].mean(0)
    # junta centros muito parecidos
    ordem = np.argsort(-np.bincount(lab, minlength=k))
    out = []
    for i in ordem:
        frac = float((lab == i).mean())
        if frac < 0.02:
            continue
        if any(np.abs(cent[i] - _hex(o['cor'])).max() < 26 for o in out):
            continue
        out.append({'cor': _hexs(cent[i]), 'frac': round(frac, 3)})
    return out


def recolorir(img: Image.Image, trocas, retro=False):
    """trocas: lista [cor_original, cor_nova]. Cada pixel anda na direção da nova cor conforme o quanto
    ele é parecido com a original (as sombras e a textura do tecido continuam)."""
    if not trocas and not retro:
        return img
    rgba = np.array(img.convert('RGBA')).astype(np.float32)
    rgb = rgba[..., :3]
    prot = _roxo(rgb)
    srcs = [_hex(s) for s, d in trocas if s and d]
    dsts = [_hex(d) for s, d in trocas if s and d]
    if srcs:
        # pesos suaves: quem está entre duas cores (borda antialiased) recebe a mistura das duas mudanças
        d2 = np.stack([((rgb - s) ** 2).sum(2) for s in srcs], 0)
        w = np.exp(-d2 / (2 * 38.0 ** 2))
        tot = w.sum(0) + np.exp(-((np.sqrt(d2.min(0)) - 0) ** 2) / (2 * 38.0 ** 2)) * 0 + 1e-6
        w = w / np.maximum(tot, 1.0)
        out = rgb.copy()
        for wi, s, d in zip(w, srcs, dsts):
            # mantém o "relevo": a diferença entre o pixel e a cor original é aplicada sobre a nova cor,
            # escalada pela luminância para não estourar em cores claras/escuras
            ls, ld = max(s.mean(), 8.0), max(d.mean(), 8.0)
            delta = (rgb - s) * (min(2.2, max(0.45, ld / ls)) if ld < ls else 1.0)
            out += wi[..., None] * (d + delta - rgb)
        rgb = out
    if retro:
        cinza = rgb.mean(2, keepdims=True)
        rgb = rgb * 0.55 + cinza * 0.45
        rgb = rgb * np.array([1.04, 1.0, 0.9]) + np.array([10, 6, -4])
    rgb = np.where(prot[..., None], rgba[..., :3], rgb)
    rgba[..., :3] = np.clip(rgb, 0, 255)
    return Image.fromarray(rgba.astype(np.uint8), 'RGBA')


def _estrela(cx, cy, r):
    pts = []
    for i in range(10):
        ang = -math.pi / 2 + i * math.pi / 5
        rr = r if i % 2 == 0 else r * 0.42
        pts.append((cx + rr * math.cos(ang), cy + rr * math.sin(ang)))
    return pts


def estrelas(img: Image.Image, escudo, n, cor='#c9a227'):
    """Desenha n estrelas em arco acima do escudo (caixa no tamanho 2048 da textura)."""
    if not n or not escudo:
        return img
    img = img.convert('RGBA')
    x0, y0, x1, y1 = escudo
    w = x1 - x0
    r = max(7, min(16, w / (2.6 * max(n, 3))))
    cx = (x0 + x1) / 2
    cy = y0 - r * 2.3
    passo = r * 2.5
    cam = Image.new('RGBA', img.size, (0, 0, 0, 0))
    dr = ImageDraw.Draw(cam)
    c = tuple(int(v) for v in _hex(cor)) + (255,)
    for i in range(n):
        dx = (i - (n - 1) / 2) * passo
        dy = abs(i - (n - 1) / 2) * r * 0.35
        borda = tuple(int(v * 0.45) for v in c[:3]) + (255,)
        dr.polygon(_estrela(cx + dx, cy + dy, r + 1.6), fill=borda)
        dr.polygon(_estrela(cx + dx, cy + dy, r), fill=c)
    img.alpha_composite(cam)
    return img


def completar(trocas, pal):
    """Tons da paleta que não foram trocados acompanham a troca da cor parecida mais próxima
    (verde-escuro da listra vira dourado-escuro quando o verde vira dourado)."""
    ts = [[s, d] for s, d in trocas if s and d]
    usados = {s for s, _ in ts}
    extra = []
    for p in pal or []:
        c = p['cor']
        if c in usados or not ts:
            continue
        pc = _hex(c)
        s, d = min(ts, key=lambda t: np.abs(_hex(t[0]) - pc).sum())
        if np.abs(_hex(s) - pc).max() < 110 and np.abs(_hex(s) - pc).sum() > 0:
            extra.append([c, _hexs(_hex(d) + (pc - _hex(s)) * 0.8)])
    return ts + extra


def _mascara_logo(crop):
    """Dentro da caixa do escudo: o que é tecido (ligado à borda da caixa com a cor do tecido) pode mudar
    de cor; o resto é o desenho do escudo/marca e fica como estava."""
    from PIL import ImageFilter
    a = np.array(crop.convert('RGB')).astype(np.int32)
    h, w, _ = a.shape
    if h < 6 or w < 6:
        return None
    borda = np.concatenate([a[0], a[-1], a[:, 0], a[:, -1]])
    q = borda // 16
    k = q[:, 0] * 10000 + q[:, 1] * 100 + q[:, 2]
    vals, cont = np.unique(k, return_counts=True)
    cores = [borda[k == vals[i]].mean(0) for i in np.argsort(-cont)[:3] if cont[i] >= 0.12 * len(borda)]
    if not cores:
        return None
    tecido = np.min([np.abs(a - c).max(axis=2) for c in cores], axis=0) < 34
    alc = np.zeros_like(tecido)
    alc[0] = tecido[0]; alc[-1] = tecido[-1]; alc[:, 0] = tecido[:, 0]; alc[:, -1] = tecido[:, -1]
    for _ in range(max(h, w)):
        nov = (np.array(Image.fromarray((alc * 255).astype(np.uint8)).filter(ImageFilter.MaxFilter(3))) > 0) & tecido
        if (nov == alc).all():
            break
        alc = nov
    logo = ~alc
    m = Image.fromarray((logo * 255).astype(np.uint8)).filter(ImageFilter.MaxFilter(3)).filter(ImageFilter.GaussianBlur(0.8))
    return m


def aplicar(img: Image.Image, cfg, escudo=None, proteger=()):
    if not cfg or not cfg.get('ativo'):
        return img
    orig = img.convert('RGBA')
    img = recolorir(orig, completar(cfg.get('trocas') or [], cfg.get('paleta')), bool(cfg.get('retro')))
    for b in proteger or ():      # escudo e marca do fornecedor ficam com as cores originais
        x0, y0, x1, y1 = [max(0, int(v)) for v in b]
        m = _mascara_logo(orig.crop((x0, y0, x1, y1)))
        if m is not None:
            img.paste(orig.crop((x0, y0, x1, y1)), (x0, y0), m)
    if cfg.get('estrelas'):
        img = estrelas(img, escudo, int(cfg['estrelas']), cfg.get('cor_estrelas') or '#c9a227')
    return img
