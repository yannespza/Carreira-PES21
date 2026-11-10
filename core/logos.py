"""Lê a pasta de logos do usuário, tira o fundo e guarda uma cópia limpa para o app."""
import os, re, json
import numpy as np
from PIL import Image, ImageDraw

EXTS = ('.png', '.webp', '.jpg', '.jpeg')
JUNK = re.compile(r'(png|svg|webp|jpe?g|logo|logotipo|hd|transparent|background|clipart|text|seeklogo|wine|'
                  r'mobile|phones|others|miscellaneous|black|blue|vertical|\(\d+\)|\d{4,}\w*|[-_]\d+$)', re.I)


def nice_name(fname):
    n = os.path.splitext(fname)[0]
    n = re.sub(r'[_\-]+', ' ', n)
    n = JUNK.sub(' ', n)
    n = re.sub(r'\s+', ' ', n).strip()
    return n.title() if n else os.path.splitext(fname)[0]


def remove_background(im: Image.Image) -> Image.Image:
    a = np.array(im.convert('RGBA')).astype(np.int32)
    h, w, _ = a.shape
    rgb = a[:, :, :3]; mx = rgb.max(2); mn = rgb.min(2)
    transp = a[:, :, 3] < 30
    bg = ((mn > 185) & ((mx - mn) < 25)) | transp
    if bg[[0, -1], :].mean() < 0.5 and bg[:, [0, -1]].mean() < 0.5:
        out = Image.fromarray(a.astype('uint8'), 'RGBA')
    else:
        mask = Image.fromarray((bg * 255).astype('uint8'), 'L')
        border = [(x, 0) for x in range(0, w, 3)] + [(x, h - 1) for x in range(0, w, 3)] + \
                 [(0, y) for y in range(0, h, 3)] + [(w - 1, y) for y in range(0, h, 3)]
        for p in border:
            if mask.getpixel(p) == 255:
                ImageDraw.floodfill(mask, p, 128)
        m = np.array(mask)
        remove = m == 128
        outer_opaque = (~transp[remove]).mean() > 0.5 if remove.any() else False
        if outer_opaque:
            # buracos internos (miolo do "O", do "A"...) com a mesma cor do fundo
            remove |= (m == 255) & ~transp
        a[:, :, 3] = np.where(remove, 0, a[:, :, 3])
        out = Image.fromarray(a.astype('uint8'), 'RGBA')
    bb = out.split()[3].getbbox()
    return out.crop(bb) if bb else out


class LogoBank:
    def __init__(self, app_dir, logos_dir):
        self.app_dir = app_dir
        self.logos_dir = logos_dir
        self.cache_dir = os.path.join(app_dir, 'data', 'logos_cache')
        os.makedirs(self.cache_dir, exist_ok=True)
        self.map_path = os.path.join(app_dir, 'data', 'logos_map.json')
        self.map = json.load(open(self.map_path, encoding='utf-8')) if os.path.exists(self.map_path) else {}
        self._mem = {}

    def save_map(self):
        json.dump(self.map, open(self.map_path, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)

    def scan(self):
        """Procura logos novos na pasta do usuário. Retorna a lista de empresas novas."""
        novos = []
        if not os.path.isdir(self.logos_dir):
            return novos
        used = set(self.map.values())
        for root, _, files in os.walk(self.logos_dir):
            for f in files:
                if not f.lower().endswith(EXTS):
                    continue
                rel = os.path.relpath(os.path.join(root, f), self.logos_dir)
                if rel in self.map:
                    continue
                nome = nice_name(f)
                if nome in used:          # duplicado (mesma empresa)
                    self.map[rel] = nome
                    continue
                try:
                    im = Image.open(os.path.join(root, f))
                    if im.width < 600:
                        im = im.convert('RGBA').resize((im.width * 3, im.height * 3), Image.LANCZOS)
                    remove_background(im).save(os.path.join(self.cache_dir, nome + '.png'))
                except Exception:
                    continue
                self.map[rel] = nome; used.add(nome)
                pasta = os.path.basename(root) if root != self.logos_dir else ''
                novos.append({'nome': nome, 'pasta': pasta})
        self.save_map()
        return novos

    def path(self, nome):
        return os.path.join(self.cache_dir, nome + '.png')

    def load(self, nome):
        if nome not in self._mem:
            p = self.path(nome)
            self._mem[nome] = Image.open(p).convert('RGBA') if os.path.exists(p) else None
        return self._mem[nome]
