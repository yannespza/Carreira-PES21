"""Números das camisas.

O jogo desenha o número das costas, o nome e o número do calção por cima do uniforme, com texturas
próprias de cada variação (config.txt do kitserver: BackNumbersFile, LegNumbersFile, NameFontFile).
A textura das costas tem os 10 algarismos lado a lado (0 a 9), em BC7.

Daqui saem: a cor que o número usa hoje, a prévia do "10" sobre a cor da camisa (com o aviso de pouco
contraste) e a troca da cor do número. Os originais ficam guardados na pasta das bases do clube.
"""
import os
import shutil

import numpy as np
from PIL import Image, ImageDraw

from . import ftex, estudio

CHAVES = ('BackNumbersFile', 'LegNumbersFile', 'NameFontFile')
_cache = {}


def _config(kit_dir, variant):
    p = os.path.join(kit_dir, variant, 'config.txt')
    out = {}
    try:
        for linha in open(p, encoding='utf-8', errors='ignore'):
            linha = linha.split(';')[0].strip()
            if '=' in linha:
                k, v = linha.split('=', 1)
                out[k.strip()] = v.strip()
    except OSError:
        pass
    return out


def arquivos(kit_dir, variant):
    """Nomes (sem .ftex) das texturas de número e nome desta variação que existem na pasta do kit."""
    cfg = _config(kit_dir, variant)
    nomes = []
    for k in CHAVES:
        n = cfg.get(k)
        if n:
            nomes.append(n)
            if k == 'NameFontFile':
                nomes.append(n + '_ex')     # letras acentuadas
    return [n for n in nomes if os.path.isfile(os.path.join(kit_dir, variant, n + '.ftex'))]


def costas(kit_dir, variant):
    n = _config(kit_dir, variant).get('BackNumbersFile')
    return n if n and os.path.isfile(os.path.join(kit_dir, variant, n + '.ftex')) else None


def _guarda(base_dir, variant):
    return os.path.join(base_dir, variant, 'numeros')


def guardar_originais(kit_dir, base_dir, variant):
    """Copia os originais uma única vez, antes da primeira troca de cor."""
    d = _guarda(base_dir, variant)
    for n in arquivos(kit_dir, variant):
        dst = os.path.join(d, n + '.ftex')
        if not os.path.isfile(dst):
            os.makedirs(d, exist_ok=True)
            shutil.copy2(os.path.join(kit_dir, variant, n + '.ftex'), dst)


def original(kit_dir, base_dir, variant, nome):
    g = os.path.join(_guarda(base_dir, variant), nome + '.ftex')
    return g if os.path.isfile(g) else os.path.join(kit_dir, variant, nome + '.ftex')


def _ler(path):
    try:
        st = os.stat(path)
    except OSError:
        return None
    k = (path, st.st_mtime, st.st_size)
    if k not in _cache:
        if len(_cache) > 16:
            _cache.clear()
        _cache[k] = ftex.read(path)
    return _cache[k].copy()


def cor_dominante(img):
    """Cor principal do número (a mais usada entre os pixels visíveis)."""
    a = np.array(img.convert('RGBA'))
    px = a[a[..., 3] > 200][:, :3]
    if not len(px):
        return None
    q = (px // 8).astype(np.int32)
    chave = q[:, 0] * 1024 + q[:, 1] * 32 + q[:, 2]
    v, n = np.unique(chave, return_counts=True)
    sel = px[chave == v[n.argmax()]].mean(0)
    return estudio._hexs(sel)


def recolorir(img, nova):
    src = cor_dominante(img)
    if not src or not nova or src.lower() == nova.lower():
        return img
    return estudio.recolorir(img, [[src, nova]])


def _lum(hexcor):
    c = estudio._hex(hexcor) / 255.0
    c = np.where(c <= 0.03928, c / 12.92, ((c + 0.055) / 1.055) ** 2.4)
    return 0.2126 * c[0] + 0.7152 * c[1] + 0.0722 * c[2]


def contraste(a, b):
    la, lb = sorted((_lum(a), _lum(b)), reverse=True)
    return round(float((la + 0.05) / (lb + 0.05)), 2)


def sugestao(camisa):
    """Branco ou preto, o que aparecer mais sobre a camisa."""
    return '#ffffff' if contraste('#ffffff', camisa) >= contraste('#141414', camisa) else '#141414'


def dez(img, fundo='#333333', altura=120):
    """Recorta o 1 e o 0 da textura das costas e monta um "10" sobre a cor da camisa."""
    img = img.convert('RGBA')
    w, h = img.size
    col = (np.array(img.getchannel('A')) > 40).sum(0)
    faixas, ini = [], None
    for x, v in enumerate(col.tolist() + [0]):
        if v and ini is None:
            ini = x
        elif not v and ini is not None:
            if faixas and ini - faixas[-1][1] < 6:      # pedaços do mesmo algarismo
                faixas[-1] = (faixas[-1][0], x)
            else:
                faixas.append((ini, x))
            ini = None
    if len(faixas) != 10:                               # fora do padrão: 10 células iguais
        cel = w / 10
        faixas = [(int(i * cel), int((i + 1) * cel)) for i in range(10)]
    digs = []
    for i in (1, 0):
        c = img.crop((faixas[i][0], 0, faixas[i][1], h))
        bb = c.getchannel('A').point(lambda v: 255 if v > 40 else 0).getbbox()
        if bb:
            c = c.crop(bb)
        s = altura / c.height
        digs.append(c.resize((max(1, int(c.width * s)), altura), Image.LANCZOS))
    gap = int(altura * 0.08)
    larg = sum(d.width for d in digs) + gap
    pad = int(altura * 0.28)
    out = Image.new('RGBA', (larg + 2 * pad, altura + 2 * pad), (0, 0, 0, 0))
    ImageDraw.Draw(out).rounded_rectangle([0, 0, out.width - 1, out.height - 1], radius=14,
                                          fill=tuple(int(x) for x in estudio._hex(fundo)) + (255,))
    x = pad
    for d in digs:
        out.alpha_composite(d, (x, pad))
        x += d.width + gap
    return out


def aplicar(kit_dir, base_dir, variant, cor, log=print):
    """Grava os números desta variação na cor pedida; sem cor, volta aos originais (se já foram trocados)."""
    nomes = arquivos(kit_dir, variant)
    if not nomes:
        return False
    if cor:
        guardar_originais(kit_dir, base_dir, variant)
    mudou = False
    for n in nomes:
        dst = os.path.join(kit_dir, variant, n + '.ftex')
        orig = os.path.join(_guarda(base_dir, variant), n + '.ftex')
        if cor:
            if not os.path.isfile(orig):
                continue
            ftex.write(recolorir(ftex.read(orig), cor), orig, dst)
            mudou = True
        elif os.path.isfile(orig) and open(orig, 'rb').read() != open(dst, 'rb').read():
            shutil.copy2(orig, dst)
            mudou = True
    if mudou:
        log(f'números do uniforme {variant} ' + (f'na cor {cor}' if cor else 'de volta ao original'))
    return mudou
