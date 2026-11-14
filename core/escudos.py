"""Escudos dos clubes para a interface (tabelas, calendário, redes sociais).

De onde vem cada escudo, nesta ordem:
1. GOGOSZ\\Escudos\\common\\render\\symbol\\flag\\e_<id>_r_l.png (o escudo de verdade, quando o patch tem);
2. o uniforme 1 do clube no kitserver: o escudo fica sempre no peito esquerdo da textura; o app recorta só
   o desenho (o tecido em volta vira transparente).
Fica guardado em data\\escudos\\<id>.png; sem escudo, grava <id>.sem e tenta de novo em 3 dias."""
import os, io, re, time
import numpy as np
from PIL import Image, ImageFilter

CAIXA = (1030, 1030, 1275, 1295)        # região do peito esquerdo na textura 2048 (onde o escudo fica)
CENTRO = (125, 135)                      # centro esperado do escudo dentro da região


def _componentes(m):
    from .limpeza import _rotular
    lab = _rotular(m)
    out = []
    for r in np.unique(lab[lab > 0]):
        ys, xs = np.nonzero(lab == r)
        out.append({'n': len(xs), 'bb': [xs.min(), ys.min(), xs.max() + 1, ys.max() + 1],
                    'c': (xs.mean(), ys.mean())})
    return out


def do_uniforme(img):
    """Recorta o escudo da textura do uniforme (RGBA, fundo transparente) ou None."""
    from .estudio import _mascara_logo
    img = img.convert('RGB')
    if img.size != (2048, 2048):
        img = img.resize((2048, 2048))
    cr = img.crop(CAIXA)
    m = _mascara_logo(cr)
    if m is None:
        return None
    a = np.array(m) > 128
    comps = [c for c in _componentes(a) if c['n'] >= 40]
    if not comps:
        return None
    dist = lambda c: ((c['c'][0] - CENTRO[0]) ** 2 + (c['c'][1] - CENTRO[1]) ** 2) ** 0.5
    princ = min((c for c in comps if c['n'] >= 600) or comps, key=lambda c: dist(c) - c['n'] ** 0.5 * 2)
    x0, y0, x1, y1 = princ['bb']
    # junta pedaços pequenos colados no escudo (estrelas, contorno separado); uma passada só, para não
    # ir encadeando até o patrocínio de cima
    px0, py0, px1, py1 = x0, y0, x1, y1
    for c in comps:
        bx0, by0, bx1, by1 = c['bb']
        if c is princ or c['n'] > 0.3 * princ['n']:
            continue
        if bx0 <= px1 + 8 and bx1 >= px0 - 8 and by0 <= py1 + 8 and by1 >= py0 - 8:
            x0, y0, x1, y1 = min(x0, bx0), min(y0, by0), max(x1, bx1), max(y1, by1)
    w, h = x1 - x0, y1 - y0
    if w < 25 or h < 25 or w > 230 or h > 250 or max(w / h, h / w) > 2.4:
        return None
    out = Image.new('RGBA', (w, h), (0, 0, 0, 0))
    out.paste(cr.crop((x0, y0, x1, y1)), (0, 0), m.crop((x0, y0, x1, y1)))
    return out


def arquivo_patch(pasta_jogo, tid):
    base = os.path.join(pasta_jogo or '', 'GOGOSZ', 'Escudos', 'common', 'render', 'symbol', 'flag')
    for suf in ('_r_l.png', '_r_ll.png', '_r.png', '_f_l.png', '_f.png'):
        p = os.path.join(base, f'e_{int(tid):06d}{suf}')
        if os.path.exists(p):
            return p
    return None


def textura_kit(pasta_jogo, mapa, tid):
    rel = (mapa or {}).get(int(tid))
    if not rel:
        return None
    pasta = os.path.join(pasta_jogo or '', 'GOGOSZ', 'kitserver', *rel.replace('/', '\\').split('\\'))
    try:
        vs = sorted(v for v in os.listdir(pasta) if re.fullmatch(r'p1(x\d+)?', v.lower()))
    except OSError:
        return None
    for v in vs:
        try:
            arqs = sorted(f for f in os.listdir(os.path.join(pasta, v)) if re.fullmatch(r'u\d+p\d+(x\d+)?\.ftex', f.lower()))
        except OSError:
            continue
        if arqs:
            return os.path.join(pasta, v, arqs[0])
    return None


def png(data_dir, pasta_jogo, mapa, tid, log=print):
    """PNG do escudo do clube (bytes) ou None."""
    try:
        tid = int(tid)
    except (TypeError, ValueError):
        return None
    cache = os.path.join(data_dir, 'escudos')
    cf = os.path.join(cache, f'{tid}.png')
    if os.path.exists(cf):
        return open(cf, 'rb').read()
    if os.path.exists(cf + '.sem') and time.time() - os.path.getmtime(cf + '.sem') < 3 * 86400:
        return None
    os.makedirs(cache, exist_ok=True)
    im = None
    try:
        p = arquivo_patch(pasta_jogo, tid)
        if p:
            im = Image.open(p).convert('RGBA')
            bb = im.getbbox()
            im = im.crop(bb) if bb else im
        else:
            t = textura_kit(pasta_jogo, mapa, tid)
            if t:
                from . import ftex
                im = do_uniforme(ftex.read(t))
    except Exception as e:
        log(f'escudo do time {tid}: {e}')
        im = None
    if im is None:
        open(cf + '.sem', 'w').close()
        return None
    im.thumbnail((128, 128), Image.LANCZOS)
    b = io.BytesIO()
    im.save(b, 'PNG')
    open(cf, 'wb').write(b.getvalue())
    return b.getvalue()
