"""Fotos do técnico: recorte automático do fundo (parede lisa, fundo branco ou cinza) para a cena da coletiva."""
import os, io, glob
import numpy as np
from PIL import Image, ImageFilter

HUMORES = ('feliz', 'neutro', 'irritado')


def _cores_fundo(rgb, t):
    h, w, _ = rgb.shape
    borda = np.concatenate([rgb[:t].reshape(-1, 3), rgb[:, :t].reshape(-1, 3), rgb[:, -t:].reshape(-1, 3)])
    q = (borda // 12).astype(np.int32)
    k = q[:, 0] * 10000 + q[:, 1] * 100 + q[:, 2]
    vals, cont = np.unique(k, return_counts=True)
    cores = []
    for i in np.argsort(-cont)[:12]:
        if cont[i] < 0.01 * len(borda):
            break
        cores.append(borda[k == vals[i]].mean(0))
    return cores


def _alcance(m, sem):
    """Parte de m ligada às sementes (preenchimento por dilatação repetida, numa imagem pequena)."""
    alc = sem & m
    while True:
        nov = (np.array(Image.fromarray((alc * 255).astype(np.uint8)).filter(ImageFilter.MaxFilter(3))) > 0) & m
        if (nov == alc).all():
            return alc
        alc = nov


def recortar(img: Image.Image) -> Image.Image:
    """Tira o fundo liso da foto (a pessoa fica, o fundo vira transparente) e corta nas bordas da pessoa."""
    img = img.convert('RGB')
    if max(img.size) > 1400:
        img.thumbnail((1400, 1400), Image.LANCZOS)
    W, H = img.size
    f = max(1, int(np.ceil(max(W, H) / 360)))
    peq = np.array(img.resize((W // f, H // f), Image.BOX)).astype(np.int32)
    h, w, _ = peq.shape
    cores = _cores_fundo(peq, max(2, min(h, w) // 40))
    if not cores:
        return img.convert('RGBA')
    dist = np.min([np.abs(peq - c).max(axis=2) for c in cores], axis=0)
    # textura do fundo (parede) é suave: bordas fortes são da pessoa
    g = np.zeros((h, w), np.int32)
    g[:, 1:] = np.maximum(g[:, 1:], np.abs(np.diff(peq, axis=1)).max(axis=2))
    g[1:, :] = np.maximum(g[1:, :], np.abs(np.diff(peq, axis=0)).max(axis=2))
    fundo_cand = (dist < 30) & (g < 22)
    sem = np.zeros((h, w), bool)
    sem[0, :] = sem[:, 0] = sem[:, -1] = True     # embaixo costuma ser o corpo cortado: não semeia
    fundo = _alcance(fundo_cand, sem)
    pessoa = ~fundo
    # fecha buraquinhos e fica só com a maior parte (a pessoa)
    pm = Image.fromarray((pessoa * 255).astype(np.uint8)).filter(ImageFilter.MaxFilter(5)).filter(ImageFilter.MinFilter(5))
    pessoa = np.array(pm) > 0
    from .limpeza import _rotular
    lab = _rotular(pessoa)
    tam = np.bincount(lab.ravel()); tam[0] = 0
    if tam.max() == 0:
        return img.convert('RGBA')
    pessoa = lab == tam.argmax()
    # roupa da cor da parede some junto com o fundo: preenche cada linha de ponta a ponta e
    # suaviza o contorno (a silhueta de quem está de braços cruzados é "cheia")
    ys = np.nonzero(pessoa.any(axis=1))[0]
    esq = np.full(h, -1); dirx = np.full(h, -1)
    for y in ys:
        xs = np.nonzero(pessoa[y])[0]
        esq[y], dirx[y] = xs.min(), xs.max()
    k = max(3, h // 14)
    for arr, fn in ((esq, np.min), (dirx, np.max)):
        v = arr.copy()
        for y in ys:
            a, b = max(ys[0], y - k), min(ys[-1], y + k) + 1
            jan = v[a:b]
            jan = jan[jan >= 0]
            arr[y] = int(np.median(jan)) if len(jan) else v[y]
        arr[ys] = np.maximum.accumulate(arr[ys]) if False else arr[ys]
    cheio = np.zeros_like(pessoa)
    for y in ys:
        cheio[y, esq[y]:dirx[y] + 1] = True
    # ombros/cabeça: mantém o recorte fino onde ele é mais estreito que o preenchido
    topo = ys[0] + int(0.38 * (ys[-1] - ys[0]))
    cheio[:topo] = pessoa[:topo] | (cheio[:topo] & _alcance(~fundo_cand, pessoa)[:topo])
    pessoa = cheio
    alfa = Image.fromarray((pessoa * 255).astype(np.uint8)).resize((W, H), Image.BILINEAR)
    alfa = alfa.filter(ImageFilter.GaussianBlur(1.6)).point(lambda v: 0 if v < 40 else (255 if v > 215 else v))
    out = img.convert('RGBA')
    out.putalpha(alfa)
    bb = alfa.point(lambda v: 255 if v > 30 else 0).getbbox()
    return out.crop(bb) if bb else out


def salvar(pasta, humor, dados: bytes):
    """Guarda a foto enviada pelo app (já recortada). Várias fotos do mesmo humor viram variações."""
    os.makedirs(pasta, exist_ok=True)
    img = Image.open(io.BytesIO(dados))
    try:
        from PIL import ImageOps
        img = ImageOps.exif_transpose(img)
    except Exception:
        pass
    rec = recortar(img)
    n = len(glob.glob(os.path.join(pasta, f'{humor}*.png')))
    nome = f'{humor}.png' if n == 0 else f'{humor}_{n + 1}.png'
    rec.save(os.path.join(pasta, nome))
    os.makedirs(os.path.join(pasta, 'originais'), exist_ok=True)
    img.convert('RGB').save(os.path.join(pasta, 'originais', nome[:-4] + '.jpg'), quality=92)
    return nome


def apagar(pasta, nome):
    p = os.path.join(pasta, os.path.basename(nome))
    if os.path.exists(p) and p.lower().endswith('.png'):
        os.remove(p)


def listar(pasta):
    if not os.path.isdir(pasta):
        return {}
    out = {}
    for f in sorted(os.listdir(pasta)):
        if f.lower().endswith('.png'):
            h = f[:-4].split('_')[0].lower()
            out.setdefault(h if h in HUMORES else 'neutro', []).append(f)
    return out


# ---------------- agasalho do clube ----------------
def _pele(a):
    """Pele (rosto, pescoço, mãos) pelo espaço de cor YCbCr."""
    r, g, b = a[..., 0].astype(np.float32), a[..., 1].astype(np.float32), a[..., 2].astype(np.float32)
    y = 0.299 * r + 0.587 * g + 0.114 * b
    cb = 128 - 0.168736 * r - 0.331264 * g + 0.5 * b
    cr = 128 + 0.5 * r - 0.418688 * g - 0.081312 * b
    return (cb > 77) & (cb < 130) & (cr > 133) & (cr < 178) & (y > 45)


def vestir(recorte: Image.Image, cor1, cor2='#ffffff', escudo=None, patro=None):
    """Troca a roupa da foto recortada pelo agasalho do clube: mantém luz e dobras do tecido, pinta com a
    cor do clube, põe um friso da segunda cor nos ombros, o escudo no peito e o patrocinador master."""
    from PIL import ImageDraw
    im = recorte.convert('RGBA')
    a = np.array(im).astype(np.float32)
    H, W = a.shape[:2]
    alfa = a[..., 3] > 40
    pele = _pele(a) & alfa
    from .limpeza import _rotular
    # rosto: maior pedaço de pele na metade de cima; o pescoço termina onde esse pedaço termina
    lab = _rotular(pele[: H // 2 + H // 8])
    tam = np.bincount(lab.ravel()); tam[0] = 0
    if tam.max() < 50:
        return im
    rosto = lab == tam.argmax()
    ys, xs = np.nonzero(rosto)
    pescoco = int(ys.max())
    face_x0, face_x1 = int(xs.min()), int(xs.max())
    face_w = face_x1 - face_x0
    roupa = alfa.copy()
    roupa[:pescoco - max(2, H // 120)] = False
    roupa &= ~pele
    # barba/queixo: logo abaixo do rosto, na largura do rosto, o escuro é pelo, não roupa
    queixo = min(H, pescoco + int(face_w * 0.42))
    bx0, bx1 = max(0, face_x0 + face_w // 8), min(W, face_x1 - face_w // 8)
    cab = np.zeros_like(roupa); cab[:queixo, bx0:bx1] = True
    roupa &= ~cab
    # cabelo/barba ficam acima do pescoço; o que sobrou embaixo é roupa
    # luz suavizada: some com estampas/logos pequenos da roupa original, ficam só as dobras
    lum = np.array(Image.fromarray(a[..., :3].mean(2).astype(np.uint8)).filter(ImageFilter.MedianFilter(9))).astype(np.float32)
    ref = np.median(lum[roupa]) if roupa.any() else 128
    c1 = np.array([int(cor1.lstrip('#')[i:i + 2], 16) for i in (0, 2, 4)], np.float32)
    c2 = np.array([int(cor2.lstrip('#')[i:i + 2], 16) for i in (0, 2, 4)], np.float32)
    # relevo do tecido: luz relativa ao tom médio da roupa (dobras e sombras continuam)
    rel = np.clip((lum - ref) / 160.0, -0.4, 0.3)[..., None]
    pint = np.where(rel >= 0, c1 + (255 - c1) * rel * 0.8, c1 * (1 + rel))
    m = Image.fromarray((roupa * 255).astype(np.uint8)).filter(ImageFilter.GaussianBlur(1.2))
    mk = (np.array(m).astype(np.float32) / 255)[..., None]
    a[..., :3] = a[..., :3] * (1 - mk) + pint * mk
    out = Image.fromarray(np.clip(a, 0, 255).astype(np.uint8), 'RGBA')
    # friso da segunda cor do pescoço até os ombros (gola de agasalho)
    dr = ImageDraw.Draw(out)
    cx = (face_x0 + face_x1) / 2
    lw = max(3, W // 70)
    gola = Image.new('L', out.size, 0)
    gd = ImageDraw.Draw(gola)
    larg = (face_x1 - face_x0) * 0.62
    gd.line([(cx - larg, pescoco + H * 0.02), (cx, pescoco + H * 0.075), (cx + larg, pescoco + H * 0.02)],
            fill=255, width=lw)
    gola = Image.fromarray(((np.array(gola) > 0) & roupa).astype(np.uint8) * 255)
    out.paste(Image.new('RGBA', out.size, tuple(int(v) for v in c2) + (255,)), (0, 0), gola)
    # escudo (lado esquerdo do peito, à direita de quem vê) e patrocinador master (do outro lado)
    peito_y = int(pescoco + H * 0.11)
    tamanho = int((face_x1 - face_x0) * 0.42)
    for logo, lado in ((escudo, 1), (patro, -1)):
        if logo is None:
            continue
        lg = logo.convert('RGBA').copy()
        lg.thumbnail((tamanho if lado == 1 else int(tamanho * 1.5), tamanho), Image.LANCZOS)
        px = int(cx + lado * (face_x1 - face_x0) * 0.55 - lg.width / 2)
        py = peito_y - lg.height // 2
        if 0 <= px and px + lg.width <= W and py + lg.height <= H:
            reg = Image.fromarray((roupa[py:py + lg.height, px:px + lg.width] * 255).astype(np.uint8))
            msk = Image.fromarray(np.minimum(np.array(lg.split()[3]), np.array(reg)).astype(np.uint8))
            out.paste(lg, (px, py), msk)
    return out
