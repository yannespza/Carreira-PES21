"""Monta os uniformes: base limpa + logos dos contratos ativos, e grava na pasta do kitserver."""
import os
from PIL import Image
from . import ftex

# As 6 posições de patrocínio no molde dos uniformes do Palmeiras (textura 2048x2048).
# Cada posição pode ter mais de um lugar na textura (pares e lados repetidos do molde).
# cx, cy = centro; w, h = tamanho máximo (no sentido de leitura do logo); rot = giro em graus (anti-horário)
SLOTS = {
    'peito':        {'nome': 'Peito (master)',          'valor_base': 12_000_000,
                     'lugares': [(1024, 1330, 430, 150, 0)], 'vista': 'frente'},
    'barra':        {'nome': 'Barra da camisa (frente)', 'valor_base': 3_000_000,
                     'lugares': [(1024, 1690, 300, 90, 0)], 'vista': 'frente'},
    'mangas':       {'nome': 'Mangas (par)',             'valor_base': 4_000_000, 'inclinacao_padrao': 0,  # aprovado no jogo
                     # manga direita: frente (3R) e trás (1R) · manga esquerda: frente (7R) e trás (6R)
                     # o último número espelha a inclinação entre os lados
                     'lugares': [(651, 1010, 150, 62, 0, 1), (651, 780, 150, 62, 0, 1),
                                 (1394, 1010, 150, 62, 0, -1), (1394, 890, 150, 62, 0, -1)], 'vista': 'mangas'},
    'costas':       {'nome': 'Costas (alto)',            'valor_base': 3_500_000,
                     'lugares': [(1024, 805, 320, 56, 180)], 'vista': 'costas'},
    'calcao':       {'nome': 'Calção – pernas (par)',    'valor_base': 2_500_000,
                     'lugares': [(146, 1388, 210, 66, -90), (1902, 1400, 190, 66, 90)], 'vista': 'calcao'},
    'calcao_tras':  {'nome': 'Calção – trás',            'valor_base': 1_500_000,
                     'lugares': [(1846, 1732, 190, 48, 90)], 'vista': 'calcao'},
}
SLOT_ORDER = ['peito', 'barra', 'mangas', 'costas', 'calcao', 'calcao_tras']

# recortes da textura para a pré-visualização (cada vista pode juntar mais de um pedaço lado a lado)
VIEWS = {
    'frente': [(690, 1080, 1360, 1860)],
    'costas': [(765, 640, 1285, 1080)],
    'mangas': [(470, 700, 762, 1110), (1288, 700, 1580, 1110)],
    'calcao': [(0, 1190, 440, 1890), (1390, 1190, 2048, 1890)],
}

# uniformes do time: pasta da variação -> arquivo, e família de cor
VARIANTS = [
    ('p1', 'u0137p1', 'verde'), ('p1x1', 'u0137p1', 'verde'), ('p1x2', 'u0137p1', 'verde'), ('p1x3', 'u0137p1', 'verde'),
    ('p2', 'u0137p2', 'branco'), ('p2x1', 'u0137p2', 'branco'), ('p2x2', 'u0137p2', 'branco'), ('p2x3', 'u0137p2', 'branco'),
    ('p3', 'u0137p3', 'azul'), ('p4', 'u0137p1', 'listrado'),
]
FAMILIAS = {'verde': 'Verde', 'branco': 'Branco', 'azul': 'Azul',
            'listrado': 'Listrado'}

_base_cache = {}
ESTUDIO = {}        # família -> configuração do estúdio (cores novas, estrelas)
PROTEGER = {}       # variação -> caixas que o estúdio não pinta (escudo, marca)
ESCUDO = {}         # variação -> caixa do escudo (para as estrelas)
BASE = {'dir': None}     # pasta das bases limpas do clube da carreira atual
VIEWS_PADRAO = {k: list(v) for k, v in VIEWS.items()}


def usar_time(t):
    """Troca posições, uniformes e famílias pelos do clube da carreira (muda os objetos no lugar)."""
    SLOTS.clear(); SLOTS.update({k: dict(v) for k, v in t['slots'].items()})
    SLOT_ORDER[:] = [s for s in t['ordem'] if s in SLOTS]
    VARIANTS[:] = [tuple(v) for v in t['variantes']]
    FAMILIAS.clear(); FAMILIAS.update(t['familias'])
    BASE['dir'] = t['base_dir']
    VIEWS.clear(); VIEWS.update({k: list(v) for k, v in VIEWS_PADRAO.items()})
    if any(s in SLOTS for s in ('costas_baixo', 'costas_laterais')):
        VIEWS['costas'] = [(725, 640, 1315, 960), (725, 90, 1315, 640)]
    if 'gola' in SLOTS or 'acima_peito' in SLOTS:
        VIEWS['frente'] = [(690, 990, 1360, 1860)]
    _base_cache.clear()
    PROTEGER.clear(); ESCUDO.clear()
    for fam, d in (t.get('deteccao') or {}).items():
        fora = set(d.get('desmarcados', []))
        for v, vv in d.get('variantes', {}).items():
            caixas = [a['caixa'] for a in vv.get('achados', []) if a.get('escudo') or
                      (a.get('chave') in fora and not a.get('desenho'))]
            PROTEGER[v] = caixas
            esc = [a['caixa'] for a in vv.get('achados', []) if a.get('escudo') and a['caixa'][0] > 1000
                   and 1000 < a['caixa'][1] < 1400]
            if esc:
                ESCUDO[v] = max(esc, key=lambda c: (c[2] - c[0]) * (c[3] - c[1]))
    if not ESCUDO:          # Palmeiras e clubes sem detecção: lugar de costume do escudo
        for v in VARIANTS:
            ESCUDO[v[0]] = [1098, 1105, 1222, 1232]


def base_path(app_dir, variant, fname):
    return os.path.join(BASE['dir'] or os.path.join(app_dir, 'data', 'kits_base'), variant, fname + '.ftex')


def base_image(app_dir, variant, fname):
    key = (BASE['dir'], variant, fname)
    if key not in _base_cache:
        _base_cache[key] = ftex.read(base_path(app_dir, variant, fname))
    return _base_cache[key].copy()


def _lum(rgb):
    return 0.299 * rgb[0] + 0.587 * rgb[1] + 0.114 * rgb[2]


CORES = {'branco': (255, 255, 255), 'verde': (0, 100, 55), 'vermelho': (220, 30, 40), 'azul': (15, 60, 145),
         'preto': (25, 25, 25)}


def colorize(logo: Image.Image, mode: str, bg_rgb):
    """mode: 'original', 'branco', 'preto', 'auto' ou cor '#rrggbb'."""
    logo = logo.convert('RGBA')
    if mode == 'original':
        return logo
    if mode == 'auto':
        # cor média do logo vs. fundo: se contrastar bem, mantém original; senão branco ou escuro
        px = [p for p in logo.getdata() if p[3] > 128]
        if px:
            avg = tuple(sum(p[i] for p in px) / len(px) for i in range(3))
            if abs(_lum(avg) - _lum(bg_rgb)) > 70:
                return logo
        mode = 'branco' if _lum(bg_rgb) < 140 else 'verde'
    col = CORES.get(mode)
    if col is None and mode.startswith('#') and len(mode) == 7:
        col = tuple(int(mode[i:i + 2], 16) for i in (1, 3, 5))
    col = col or (255, 255, 255)
    solid = Image.new('RGBA', logo.size, col + (255,))
    solid.putalpha(logo.split()[3])
    return solid


def place(canvas: Image.Image, logo: Image.Image, lugar, escala=1.0, inclinacao=0, cor='auto', dx=0, dy=0):
    cx, cy, w, h, rot = lugar[:5]
    lado = lugar[5] if len(lugar) > 5 else 1   # inclinação espelhada entre os lados (mangas)
    # deslocamento no sentido de leitura do logo (dx) e perpendicular a ele (dy), espelhado nos pares
    import math
    t = math.radians(rot)
    cx = cx + (dx * lado) * math.cos(t) + dy * math.sin(t)
    cy = cy - (dx * lado) * math.sin(t) + dy * math.cos(t)
    bg = canvas.convert('RGB').getpixel((int(cx), int(cy)))
    lg = colorize(logo, cor, bg)
    bw, bh = w * escala, h * escala
    s = min(bw / lg.width, bh / lg.height)
    lg = lg.resize((max(1, int(lg.width * s)), max(1, int(lg.height * s))), Image.LANCZOS)
    ang = rot + inclinacao * lado
    if ang:
        lg = lg.rotate(ang, expand=True, resample=Image.BICUBIC)
    # cola só a cor (o canal alfa do uniforme é 0 em toda a textura e precisa continuar assim)
    alpha = canvas.getchannel('A')
    rgb = canvas.convert('RGB')
    rgb.paste(lg.convert('RGB'), (int(cx - lg.width / 2), int(cy - lg.height / 2)), lg.getchannel('A'))
    rgb.putalpha(alpha)
    canvas.paste(rgb)


def ajuste(c, familia):
    """Ajuste do logo em um uniforme: cada uniforme tem o seu; se não tiver, usa o geral do contrato."""
    a = (c.get('ajustes') or {}).get(familia) or {}
    return {k: a.get(k, c.get(k, d)) for k, d in (('escala', 1.0), ('inclinacao', 0), ('dx', 0), ('dy', 0))}


_estudio_cache = {}


def base_estudio(app_dir, variant, fname, cfg):
    """Base limpa já com as cores/estrelas do estúdio (guardada em memória por configuração)."""
    if not cfg or not cfg.get('ativo'):
        return base_image(app_dir, variant, fname)
    from . import estudio
    import json
    key = (BASE['dir'], variant, fname, json.dumps(cfg, sort_keys=True))
    if key not in _estudio_cache:
        if len(_estudio_cache) > 12:
            _estudio_cache.clear()
        esc = ESCUDO.get(variant) or [1085, 1030, 1200, 1140]
        prot = PROTEGER.get(variant) or [esc, [845, 1045, 955, 1140]]
        _estudio_cache[key] = estudio.aplicar(base_image(app_dir, variant, fname), cfg, esc, prot)
    return _estudio_cache[key].copy()


def compose(app_dir, variant, fname, familia, contratos, logo_loader, estudio_cfg=None):
    """contratos: lista de dicts com slot, empresa, escala, inclinacao, cores{familia: modo}"""
    img = base_estudio(app_dir, variant, fname, estudio_cfg if estudio_cfg is not None else ESTUDIO.get(familia))
    for c in contratos:
        slot = SLOTS.get(c['slot'])
        if not slot:
            continue
        logo = logo_loader(c['empresa'])
        if logo is None:
            continue
        cor = (c.get('cores') or {}).get(familia, 'auto')
        a = ajuste(c, familia)
        for lugar in slot['lugares']:
            place(img, logo, lugar, a['escala'], a['inclinacao'], cor, a['dx'], a['dy'])
    return img


def _view(img, rects):
    parts = [img.crop(r).convert('RGB') for r in rects]
    h = max(p.height for p in parts)
    w = sum(p.width for p in parts) + 8 * (len(parts) - 1)
    out = Image.new('RGB', (w, h), (14, 16, 20))
    x = 0
    for p in parts:
        out.paste(p, (x, 0)); x += p.width + 8
    return out


ROTULOS = {'frente': ['FRENTE'], 'costas': ['COSTAS'], 'mangas': ['MANGA DIREITA', 'MANGA ESQUERDA'],
           'calcao': ['CALCAO - ESQ.', 'CALCAO - DIR. / TRAS']}


def _rotulos(v):
    if v == 'costas' and len(VIEWS['costas']) > 1:
        return ['COSTAS - ALTO', 'COSTAS - BAIXO']
    return ROTULOS[v]


def _rotular(p, rotulos, n_partes):
    from PIL import ImageDraw
    d = ImageDraw.Draw(p)
    w = p.width / max(1, n_partes)
    for i, t in enumerate(rotulos):
        x = int(i * w) + 8
        tw = 7 * len(t) + 10
        d.rectangle([x, 6, x + tw, 24], fill=(12, 14, 18))
        d.text((x + 5, 9), t, fill=(200, 240, 49))
    return p


def preview(img: Image.Image, width=520):
    """Junta as vistas (frente, costas, mangas, calção) numa imagem só para a tela do app."""
    parts = []
    for v in ('frente', 'costas', 'mangas', 'calcao'):
        p = _view(img, VIEWS[v])
        p = p.resize((width, int(p.height * width / p.width)), Image.LANCZOS)
        parts.append(_rotular(p, _rotulos(v), len(VIEWS[v])))
    H = sum(p.height for p in parts) + 6 * (len(parts) - 1)
    out = Image.new('RGB', (width, H), (14, 16, 20))
    y = 0
    for p in parts:
        out.paste(p, (0, y)); y += p.height + 6
    return out


def install(app_dir, kit_dir, contratos, logo_loader, log=print, progresso=None):
    """Gera os uniformes e grava na pasta do kitserver (o jogo pode estar aberto)."""
    done = []
    for i, (variant, fname, fam) in enumerate(VARIANTS):
        if progresso:
            progresso(i, len(VARIANTS), variant)
        img = compose(app_dir, variant, fname, fam, contratos, logo_loader)
        dst = os.path.join(kit_dir, variant, fname + '.ftex')
        tpl = base_path(app_dir, variant, fname)
        ftex.write(img, tpl, dst)
        done.append(variant)
        log(f'uniforme {variant} atualizado')
        cfg = ESTUDIO.get(fam) or {}
        try:
            from . import numeros
            numeros.aplicar(kit_dir, BASE['dir'] or os.path.join(app_dir, 'data', 'kits_base'), variant,
                            cfg.get('cor_numero') if cfg.get('ativo') else None, log)
        except Exception as e:      # o uniforme já foi gravado; o número fica como estava
            log(f'números do uniforme {variant} não foram trocados: {e}')
    if progresso:
        progresso(len(VARIANTS), len(VARIANTS), '')
    return done
