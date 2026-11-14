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


def _borrar(a, r):
    return np.array(Image.fromarray(np.clip(a, 0, 255).astype(np.uint8)).filter(ImageFilter.GaussianBlur(r))).astype(np.float32)


def mascara_tecido(img, mask, rosto=None):
    """Refina a máscara da blusa: só o tecido escuro (sem pele do pescoço, mão, barba ou fundo da borda) e
    recupera a gola, que a máscara desenhada à mão costuma cortar. Devolve 0..1."""
    a = np.array(img.convert('RGBA')).astype(np.float32)
    rgb, alfa = a[..., :3], a[..., 3] / 255
    lum = rgb.mean(2)
    quente = rgb[..., 0] - rgb[..., 2]                 # pele e barba puxam pro vermelho; o tecido não
    tecido = np.clip((24 - quente) / 14, 0, 1) * np.clip((135 - lum) / 45, 0, 1)
    m = np.array(mask.convert('L')).astype(np.float32) / 255
    grande = np.array(mask.convert('L').filter(ImageFilter.MaxFilter(41))).astype(np.float32) / 255
    if rosto:                                          # gola: faixa logo abaixo do queixo
        y0, y1 = int(rosto[3] - (rosto[3] - rosto[1]) * 0.25), int(rosto[3] + (rosto[3] - rosto[1]) * 0.45)
        gola = np.zeros_like(m)
        gola[max(0, y0):y1] = grande[max(0, y0):y1]
        m = np.maximum(m, gola * (tecido > 0.6))
    # buracos finos que a máscara desenhou (haste do microfone): fecha, vê o que era buraco e tira com folga
    mk = mask.convert('L')
    fechado = np.array(mk.filter(ImageFilter.MaxFilter(15)).filter(ImageFilter.MinFilter(15))) > 128
    buraco = Image.fromarray(((fechado & (np.array(mk) < 128)) * 255).astype(np.uint8)).filter(ImageFilter.MaxFilter(9))
    H, W = m.shape
    excl = 1 - np.array(buraco).astype(np.float32) / 255
    haste = haste_microfone(mask, img)
    if haste is not None:
        excl = excl * (1 - haste)
    if rosto:                                          # rosto e barba inteiros fora (elipse com folga embaixo)
        x0, y0, x1, y1 = rosto
        yy, xx = np.mgrid[:H, :W].astype(np.float32)
        d = ((xx - (x0 + x1) / 2) / ((x1 - x0) * 0.50)) ** 2 + ((yy - (y0 + (y1 - y0) * 0.5)) / ((y1 - y0) * 0.56)) ** 2
        excl = excl * np.clip((d - 1) * 4, 0, 1)
    # barba: pelos quentes e as sombras no meio deles (fechamento) ficam fora
    pelo = Image.fromarray(((quente > 12) * 255).astype(np.uint8))
    barba = np.array(pelo.filter(ImageFilter.MaxFilter(21)).filter(ImageFilter.MinFilter(17))).astype(np.float32) / 255
    if rosto:
        barba[int(rosto[3] + (rosto[3] - rosto[1]) * 0.25):] = 0     # abaixo do pescoço não tem barba
    excl = excl * (1 - barba)
    m = m * excl * tecido * np.clip((alfa - 0.3) / 0.4, 0, 1)
    # leva a tinta até o contorno do recorte (senão fica um fio preto em volta da blusa clara)
    borda = np.clip((24 - quente) / 14, 0, 1) * (lum < 110) * (alfa > 0.04) * excl
    cresce = np.array(Image.fromarray((m * 255).astype(np.uint8)).filter(ImageFilter.MaxFilter(9))).astype(np.float32) / 255
    m = np.maximum(m, cresce * borda)
    m = np.array(Image.fromarray((m * 255).astype(np.uint8)).filter(ImageFilter.GaussianBlur(0.8))).astype(np.float32) / 255
    return m


def haste_microfone(mask, img=None):
    """A haste do microfone aparece na máscara como um risco fino recortado só no começo. Acha esse risco,
    segue a haste foto abaixo (ela é mais clara que o tecido preto) e devolve a faixa dela 0..1, ou None."""
    from .limpeza import _rotular
    mk = mask.convert('L')
    fechado = np.array(mk.filter(ImageFilter.MaxFilter(15)).filter(ImageFilter.MinFilter(15))) > 128
    bur = fechado & (np.array(mk) < 128)
    if bur.sum() < 40:
        return None
    lab = _rotular(bur)
    melhor = None
    for r in np.unique(lab[lab > 0]):
        ys, xs = np.nonzero(lab == r)
        if len(xs) < 40:
            continue
        pts = np.stack([xs, ys], 1).astype(np.float32)
        c = pts.mean(0)
        _, sv, vt = np.linalg.svd(pts - c, full_matrices=False)
        if sv[0] < 5 * max(sv[1], 1):
            continue
        if melhor is None or sv[0] > melhor[0]:
            melhor = (sv[0], pts, c, vt[0])
    if melhor is None:
        return None
    _, pts, c, d = melhor
    if d[1] < 0:
        d = -d
    H, W = bur.shape
    proj = (pts - c) @ d
    a = c + d * proj.min()
    b = c + d * proj.max()
    caminho = [tuple(a), tuple(b)]
    if img is not None:            # segue a haste: a cada passo, o ponto mais claro perto do previsto
        lum = np.array(img.convert('L').filter(ImageFilter.GaussianBlur(1.5))).astype(np.float32)
        fundo = np.array(img.convert('L').filter(ImageFilter.GaussianBlur(9))).astype(np.float32)
        ridge = lum - fundo
        x, y = float(b[0]), float(b[1])
        dx, dy = float(d[0]), float(d[1])
        perdeu = 0
        for _ in range(400):
            x2, y2 = x + dx * 6, y + dy * 6
            if not (2 <= y2 < H - 2 and 8 <= x2 < W - 8):
                break
            yi = int(y2)
            xs_ = np.arange(int(x2) - 5, int(x2) + 6)
            v = ridge[yi, xs_]
            k = int(np.argmax(v))
            if v[k] < 2.5:
                perdeu += 1
                if perdeu > 3:
                    break
            else:
                perdeu = 0
                x2 = float(xs_[k])
            nd = np.array([x2 - x, y2 - y]); nd /= max(1e-6, np.linalg.norm(nd))
            dx, dy = 0.7 * dx + 0.3 * nd[0], 0.7 * dy + 0.3 * nd[1]
            n = np.hypot(dx, dy); dx, dy = dx / n, dy / n
            x, y = x2, y2
            caminho.append((x, y))
        # a parte de baixo (tubo preto grosso, na frente do braço) quase não tem brilho: segue reto
        caminho.append((x + dx * H, y + dy * H))
    else:
        caminho.append(tuple(c + d * (H * 2)))
    im = Image.new('L', (W, H), 0)
    ImageDraw.Draw(im).line(caminho, fill=255, width=15, joint='curve')
    return np.array(im.filter(ImageFilter.GaussianBlur(2))).astype(np.float32) / 255


def aparar_borda(img, mask):
    """Tira o fiapo claro do fundo antigo que sobra no contorno recortado da blusa."""
    a = np.array(img.convert('RGBA'))
    perto = np.array(mask.convert('L').filter(ImageFilter.MaxFilter(25))) > 128
    al = Image.fromarray(a[..., 3])
    ero = np.array(al.filter(ImageFilter.MinFilter(5)).filter(ImageFilter.GaussianBlur(1)))
    lum = a[..., :3].astype(np.float32).mean(2)
    claro = lum > 70
    a[..., 3] = np.where(perto & claro & (a[..., 3] < 255), np.minimum(a[..., 3], ero), a[..., 3])
    return Image.fromarray(a, 'RGBA')


def vestir(img, mask, cor1, m=None):
    """Pinta a blusa escura com a cor do clube como tecido de verdade: as dobras e o brilho do original viram
    luz e sombra da cor nova (sombra multiplica, brilho clareia), com uma trama fina para não ficar chapado."""
    a = np.array(img.convert('RGBA')).astype(np.float32)
    if m is None:
        m = np.array(mask.convert('L')).astype(np.float32) / 255
    lum = a[..., :3].mean(2)
    sel = m > 0.6
    ref = float(np.median(lum[sel])) if sel.any() else 30.0
    alto = float(np.percentile(lum[sel], 97)) if sel.any() else ref + 40
    # luz relativa: <0 dobra/sombra, >0 brilho. Escala pelo contraste real da foto.
    rel = (lum - ref) / max(18.0, alto - ref)
    det = rel - _borrar(rel * 60 + 128, 6) / 60 + 128 / 60          # detalhe fino (costuras, zíper)
    rel = np.clip(rel + det * 0.6, -1.2, 1.6)
    c = np.array(_rgb(cor1), np.float32)
    clara = c.mean() > 170
    base = c * (0.80 if not clara else 0.93)
    sombra = base * np.clip(1 + rel * (0.55 if clara else 0.62), 0.18, 1)[..., None]
    brilho = base + (np.minimum(255, base * 1.25 + 40) - base) * np.clip(rel, 0, 1.6)[..., None] * 0.55
    pint = np.where(rel[..., None] >= 0, brilho, sombra)
    rng = np.random.default_rng(7)
    trama = (rng.standard_normal(lum.shape).astype(np.float32) * 2.2)[..., None]
    pint = pint + trama
    mm = m[..., None]
    a[..., :3] = a[..., :3] * (1 - mm) + pint * mm
    return Image.fromarray(np.clip(a, 0, 255).astype(np.uint8), 'RGBA'), rel


def estampar(frente, logo, cx, cy, larg, alt, m, rel, curva=1.0, giro=0.0, bordado=False):
    """Põe o logo no peito como estampa: curva com o tórax (lado de fora encolhe), inclina com o corpo,
    entorta nas dobras e recebe a luz e a sombra do tecido."""
    lg = _encaixar(logo, larg, alt)
    w, h = lg.size
    # curvatura do tórax: o lado mais longe do centro do peito encolhe e desce um pouco
    pad = 12
    tela = Image.new('RGBA', (w + 2 * pad, h + 2 * pad), (0, 0, 0, 0))
    tela.paste(lg, (pad, pad))
    W2, H2 = tela.size
    k = 0.10 * curva                                  # >0: lado direito da imagem é o de fora
    enc_e, enc_d = (1 - max(0, -k)), (1 - max(0, k))
    quad = (0, H2 * (1 - enc_e) / 2 - 2 * max(0, -k) * 10, 0, H2 - H2 * (1 - enc_e) / 2,
            W2, H2 - H2 * (1 - enc_d) / 2, W2, H2 * (1 - enc_d) / 2 - 2 * max(0, k) * 10)
    if curva:
        tela = tela.transform((W2, H2), Image.QUAD, quad, Image.BICUBIC)
        # compressão horizontal suave (cilindro); o escudo não passa por aqui para não perder a proporção
        xs = np.linspace(-1, 1, W2)
        src = np.sin(xs * 1.05) / np.sin(1.05)            # amostra mais perto da borda: as bordas encolhem
        tel = np.array(tela).astype(np.float32)
        idx = np.clip(((src + 1) / 2 * (W2 - 1)).round().astype(int), 0, W2 - 1)
        tel = tel[:, idx]
        tela = Image.fromarray(tel.astype(np.uint8), 'RGBA')
    if giro:
        tela = tela.rotate(giro, Image.BICUBIC, expand=True)
    W2, H2 = tela.size
    x0, y0 = int(cx - W2 / 2), int(cy - H2 / 2)
    FH, FW = m.shape
    if x0 < 0 or y0 < 0 or x0 + W2 > FW or y0 + H2 > FH:
        return
    reg = rel[y0:y0 + H2, x0:x0 + W2]
    mm = m[y0:y0 + H2, x0:x0 + W2]
    # entorta nas dobras: desloca pelo gradiente da luz do tecido
    suave = _borrar(reg * 60 + 128, 3) / 60
    gy, gx = np.gradient(suave)
    yy, xx = np.mgrid[:H2, :W2].astype(np.float32)
    sx = np.clip(xx - gx * 6, 0, W2 - 1).round().astype(int)
    sy = np.clip(yy - gy * 6, 0, H2 - 1).round().astype(int)
    t = np.array(tela).astype(np.float32)[sy, sx]
    # luz do tecido sobre a tinta: sombra escurece, brilho clareia de leve
    luz = np.clip(1 + reg * 0.42, 0.45, 1.35)[..., None]
    t[..., :3] = t[..., :3] * np.minimum(luz, 1) + (255 - t[..., :3]) * (np.maximum(luz, 1) - 1) * 0.5
    al = t[..., 3] * mm * (0.9 if not bordado else 0.97)
    t[..., 3] = al
    est = Image.fromarray(np.clip(t, 0, 255).astype(np.uint8), 'RGBA').filter(ImageFilter.GaussianBlur(0.55))
    if bordado:                                       # escudo bordado: relevo e sombrinha
        sb = Image.new('RGBA', est.size, (0, 0, 0, 0))
        sb.putalpha(est.split()[3].point(lambda v: int(v * 0.35)))
        frente.alpha_composite(sb.filter(ImageFilter.GaussianBlur(1.5)), (x0 + 1, y0 + 2))
    frente.alpha_composite(est, (x0, y0))


def compor(data_dir, humor, cor1, cor2, escudo, patro, logos, clube, largura=900):
    p = pasta(data_dir)
    meta = json.load(open(os.path.join(p, 'cena.json')))
    if humor not in meta:
        humor = next(iter(meta))
    m = meta[humor]
    chave = hashlib.md5(json.dumps([humor, cor1, cor2, clube, [n for n, _ in logos], bool(escudo), bool(patro), largura, 10]).encode()).hexdigest()[:16]
    cdir = os.path.join(p, 'cache')
    os.makedirs(cdir, exist_ok=True)
    cf = os.path.join(cdir, chave + '.jpg')
    if os.path.exists(cf):
        return open(cf, 'rb').read()
    frente = Image.open(os.path.join(p, humor + '.png')).convert('RGBA')
    mask = Image.open(os.path.join(p, humor + '_camisa.png')).convert('L')
    W, H = frente.size
    fundo = painel(W, H, cor1, cor2, escudo, [l for _, l in logos], clube)
    m_tec = mascara_tecido(frente, mask, m.get('rosto'))
    frente = aparar_borda(frente, mask)
    frente, rel = vestir(frente, mask, cor1, m_tec)
    # escudo no peito (lado esquerdo de quem veste = direita de quem vê) e marca master do outro lado
    x0, y0, x1, y1 = m['rosto']
    fw = x1 - x0
    cx = (x0 + x1) / 2
    peito = int(y1 + (y1 - y0) * 0.40)
    gir = float(m.get('giro', 0))                    # inclinação do tronco na foto (graus)
    # escudo: no peito, em tecido livre (sem haste, microfone ou mão na frente); procura primeiro para dentro
    ex = cx + fw * 0.66
    # tamanho do escudo como no uniforme: uns 8 cm de altura, metade da largura do rosto
    esc_l, esc_a = int(fw * 0.40), int(fw * 0.46)
    r = int(fw * 0.23)
    def livre(x):
        y_a, x_a = max(0, peito - r), max(0, int(x - r))
        return m_tec[y_a:peito + r, x_a:int(x + r)].mean() if x_a < int(x + r) else 0
    if livre(ex) < 0.93:
        cands = [ex - p_ for p_ in range(6, int(fw * 0.4), 6)] + [ex + p_ for p_ in range(6, int(fw * 0.2), 6)]
        ok = [x for x in cands if livre(x) >= 0.93]
        ex = ok[0] if ok else max([ex] + cands, key=livre)
    if escudo is not None:
        estampar(frente, escudo, ex, peito, esc_l, esc_a, m_tec, rel, curva=0, giro=gir, bordado=True)
    if patro is not None:
        estampar(frente, patro, cx - fw * 0.60, peito + int(fw * 0.02), int(fw * 0.46), int(fw * 0.26), m_tec, rel,
                 curva=-1.0, giro=gir)
    fundo = fundo.convert('RGBA')
    fundo.alpha_composite(frente)
    out = fundo.convert('RGB')
    if out.width > largura:
        out = out.resize((largura, int(out.height * largura / out.width)), Image.LANCZOS)
    b = io.BytesIO()
    out.save(b, 'JPEG', quality=88)
    open(cf, 'wb').write(b.getvalue())
    return b.getvalue()
