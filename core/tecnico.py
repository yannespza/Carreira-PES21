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
