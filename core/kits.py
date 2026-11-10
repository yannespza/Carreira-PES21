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
    'mangas':       {'nome': 'Mangas (par)',             'valor_base': 4_000_000,
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
    'costas': [(690, 640, 1360, 1080)],
    'mangas': [(470, 760, 800, 1140), (1250, 760, 1580, 1140)],
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


def base_image(app_dir, variant, fname):
    key = (variant, fname)
    if key not in _base_cache:
        _base_cache[key] = ftex.read(os.path.join(app_dir, 'data', 'kits_base', variant, fname + '.ftex'))
    return _base_cache[key].copy()


def _lum(rgb):
    return 0.299 * rgb[0] + 0.587 * rgb[1] + 0.114 * rgb[2]


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
        mode = 'branco' if _lum(bg_rgb) < 140 else 'preto'
    col = {'branco': (255, 255, 255), 'preto': (25, 25, 25)}.get(mode)
    if col is None and mode.startswith('#') and len(mode) == 7:
        col = tuple(int(mode[i:i + 2], 16) for i in (1, 3, 5))
    col = col or (255, 255, 255)
    solid = Image.new('RGBA', logo.size, col + (255,))
    solid.putalpha(logo.split()[3])
    return solid


def place(canvas: Image.Image, logo: Image.Image, lugar, escala=1.0, inclinacao=0, cor='auto'):
    cx, cy, w, h, rot = lugar[:5]
    lado = lugar[5] if len(lugar) > 5 else 1   # inclinação espelhada entre os lados (mangas)
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


def compose(app_dir, variant, fname, familia, contratos, logo_loader):
    """contratos: lista de dicts com slot, empresa, escala, inclinacao, cores{familia: modo}"""
    img = base_image(app_dir, variant, fname)
    for c in contratos:
        slot = SLOTS.get(c['slot'])
        if not slot:
            continue
        logo = logo_loader(c['empresa'])
        if logo is None:
            continue
        cor = (c.get('cores') or {}).get(familia, 'auto')
        for lugar in slot['lugares']:
            place(img, logo, lugar, c.get('escala', 1.0), c.get('inclinacao', 0), cor)
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


def preview(img: Image.Image, width=520):
    """Junta as vistas (frente, costas, mangas, calção) numa imagem só para a tela do app."""
    parts = []
    for v in ('frente', 'costas', 'mangas', 'calcao'):
        p = _view(img, VIEWS[v])
        p = p.resize((width, int(p.height * width / p.width)), Image.LANCZOS)
        parts.append(p)
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
        tpl = os.path.join(app_dir, 'data', 'kits_base', variant, fname + '.ftex')
        ftex.write(img, tpl, dst)
        done.append(variant)
        log(f'uniforme {variant} atualizado')
    if progresso:
        progresso(len(VARIANTS), len(VARIANTS), '')
    return done
