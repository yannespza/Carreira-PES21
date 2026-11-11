"""Cena da coletiva: as fotos do técnico (já sem o fundo) na frente de um painel de patrocinadores
montado com as cores e as marcas do clube atual, e a blusa pintada nas cores do clube com escudo."""
import os, io, json, zipfile, hashlib
import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

HUMORES = ('feliz', 'neutro', 'irritado')


def pasta(data_dir):
    return os.path.join(data_dir, 'tecnico', 'cena')


def disponiveis(data_dir):
    p = pasta(data_dir)
    try:
        meta = json.load(open(os.path.join(p, 'cena.json')))
    except (OSError, ValueError):
        return []
    return [h for h in meta if os.path.exists(os.path.join(p, h + '.png'))]


def importar_zip(data_dir, dados: bytes):
    p = pasta(data_dir)
    os.makedirs(p, exist_ok=True)
    with zipfile.ZipFile(io.BytesIO(dados)) as z:
        for nome in z.namelist():
            b = os.path.basename(nome)
            if b and (b.endswith('.png') or b == 'cena.json'):
                open(os.path.join(p, b), 'wb').write(z.read(nome))
    limpar_cache(data_dir)
    return disponiveis(data_dir)


def limpar_cache(data_dir):
    c = os.path.join(pasta(data_dir), 'cache')
    if os.path.isdir(c):
        for f in os.listdir(c):
            os.remove(os.path.join(c, f))


def _rgb(h):
    h = (h or '#1f6b3a').lstrip('#')
    return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))


def _fonte(tam):
    for f in ('arialbd.ttf', 'Arial Bold.ttf', 'DejaVuSans-Bold.ttf', 'LiberationSans-Bold.ttf'):
        try:
            return ImageFont.truetype(f, tam)
        except OSError:
            continue
    return ImageFont.load_default()


def _encaixar(img, w, h):
    img = img.convert('RGBA')
    bb = img.getbbox()
    if bb:
        img = img.crop(bb)
    img.thumbnail((w, h), Image.LANCZOS)
    return img


def painel(W, H, cor1, cor2, escudo, logos, clube):
    """Parede de quadros alternando a cor do clube e branco, com escudo e patrocinadores, desfocada como
    numa foto de coletiva."""
    c1, c2 = _rgb(cor1), (245, 246, 248)
    out = Image.new('RGB', (W, H), (30, 32, 36))
    tw, th = int(W / 2.6), int(H / 6.2)
    gap = max(6, W // 110)
    itens = [('esc', escudo)] + [('logo', l) for l in logos] if logos else [('esc', escudo), ('txt', clube)]
    k = 0
    for row, y in enumerate(range(-th // 3, H, th + gap)):
        off = -(tw // 2) if row % 2 else 0
        for col, x in enumerate(range(off - gap, W + tw, tw + gap)):
            claro = (row + col) % 2 == 0
            fundo = c2 if claro else c1
            tile = Image.new('RGBA', (tw, th), fundo + (255,))
            tipo, obj = itens[k % len(itens)]
            k += 1
            if tipo == 'esc' and obj is not None:
                lg = _encaixar(obj, int(th * 0.75), int(th * 0.75))
                tile.alpha_composite(lg, ((tw - lg.width) // 2, (th - lg.height) // 2))
            elif tipo == 'logo' and obj is not None:
                lg = _encaixar(obj, int(tw * 0.72), int(th * 0.62))
                if not claro:      # logo em cima da cor do clube: placa branca por trás
                    pl = Image.new('RGBA', (lg.width + 24, lg.height + 16), (255, 255, 255, 235))
                    tile.alpha_composite(pl, ((tw - pl.width) // 2, (th - pl.height) // 2))
                tile.alpha_composite(lg, ((tw - lg.width) // 2, (th - lg.height) // 2))
            else:
                d = ImageDraw.Draw(tile)
                t = (clube or '').upper()
                tam = int(th * 0.28)
                f = _fonte(tam)
                while tam > 10 and d.textlength(t, font=f) > tw * 0.86:
                    tam -= 2
                    f = _fonte(tam)
                w = d.textlength(t, font=f)
                d.text(((tw - w) / 2, th * 0.34), t, font=f, fill=c1 if claro else (255, 255, 255))
            out.paste(tile.convert('RGB'), (x, y))
    out = out.filter(ImageFilter.GaussianBlur(max(2, W // 300)))
    # luz de coletiva: centro mais claro, bordas um pouco mais escuras
    yy, xx = np.mgrid[:H, :W]
    v = 1 - 0.28 * (((xx - W / 2) / (W / 1.2)) ** 2 + ((yy - H * 0.35) / (H / 1.1)) ** 2)
    a = np.array(out).astype(np.float32) * np.clip(v, 0.6, 1.05)[..., None]
    return Image.fromarray(np.clip(a, 0, 255).astype(np.uint8))


def vestir(img, mask, cor1):
    """Pinta a blusa escura com a cor do clube, mantendo dobras, zíper e sombras."""
    a = np.array(img).astype(np.float32)
    m = (np.array(mask).astype(np.float32) / 255)[..., None]
    lum = a[..., :3].mean(2)
    sel = np.array(mask) > 128
    ref = np.median(lum[sel]) if sel.any() else 30
    rel = np.clip((lum - ref) / 70.0, -0.6, 1.4)[..., None]
    c = np.array(_rgb(cor1), np.float32)
    clara = c.mean() > 170       # camisa branca/amarela: sombras precisam ser mais fortes
    base = c * (0.92 if not clara else 0.97)
    pint = np.where(rel >= 0, base + (255 - base) * rel * 0.45, base * (1 + rel * (1.0 if clara else 0.85)))
    a[..., :3] = a[..., :3] * (1 - m) + pint * m
    return Image.fromarray(np.clip(a, 0, 255).astype(np.uint8), img.mode)


def compor(data_dir, humor, cor1, cor2, escudo, patro, logos, clube, largura=900):
    p = pasta(data_dir)
    meta = json.load(open(os.path.join(p, 'cena.json')))
    if humor not in meta:
        humor = next(iter(meta))
    m = meta[humor]
    chave = hashlib.md5(json.dumps([humor, cor1, cor2, clube, [n for n, _ in logos], bool(escudo), bool(patro), largura, 4]).encode()).hexdigest()[:16]
    cdir = os.path.join(p, 'cache')
    os.makedirs(cdir, exist_ok=True)
    cf = os.path.join(cdir, chave + '.jpg')
    if os.path.exists(cf):
        return open(cf, 'rb').read()
    frente = Image.open(os.path.join(p, humor + '.png')).convert('RGBA')
    mask = Image.open(os.path.join(p, humor + '_camisa.png')).convert('L')
    W, H = frente.size
    fundo = painel(W, H, cor1, cor2, escudo, [l for _, l in logos], clube)
    frente = vestir(frente, mask, cor1)
    # escudo no peito (lado esquerdo de quem veste = direita de quem vê) e marca master do outro lado
    x0, y0, x1, y1 = m['rosto']
    fw = x1 - x0
    cx = (x0 + x1) / 2
    peito = int(y1 + (y1 - y0) * 0.36)
    sel = np.array(mask)
    for logo, lado, esc in ((escudo, 1, 0.22), (patro, -1, 0.30)):
        if logo is None:
            continue
        lg = _encaixar(logo, int(fw * (0.26 if lado == 1 else 0.42)), int(fw * esc))
        px, py = int(cx + lado * fw * 0.62 - lg.width / 2), peito - lg.height // 2
        if px < 0 or px + lg.width > W:
            continue
        reg = sel[py:py + lg.height, px:px + lg.width]
        alfa = np.minimum(np.array(lg.split()[3]), reg).astype(np.float32) * 0.93
        lg.putalpha(Image.fromarray(alfa.astype(np.uint8)))
        frente.alpha_composite(lg, (px, py))
    fundo = fundo.convert('RGBA')
    fundo.alpha_composite(frente)
    out = fundo.convert('RGB')
    if out.width > largura:
        out = out.resize((largura, int(out.height * largura / out.width)), Image.LANCZOS)
    b = io.BytesIO()
    out.save(b, 'JPEG', quality=88)
    open(cf, 'wb').write(b.getvalue())
    return b.getvalue()
