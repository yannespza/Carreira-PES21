"""Lê a pasta de logos do usuário, tira o fundo e guarda uma cópia limpa para o app."""
import os, re, json
import numpy as np
from PIL import Image, ImageFilter

EXTS = ('.png', '.webp', '.jpg', '.jpeg')
VERSAO_CACHE = 2
JUNK = re.compile(r'\b(png|svg|webp|jpe?g|logo|logos|logotipo|logomarca|hd|transparent|transparente|background|'
                  r'no|sem|fundo|clipart|text|seeklogo|wine|mobile|phones|others|miscellaneous|black|blue|white|'
                  r'vertical|horizontal|vector|vetor|site|simbolo|símbolo|symbol|icon|icone|thumb|digital|pharma|'
                  r'brand|marca|oficial|official|kisspng|png\w*)\b|\(\d+\)|\b\w*\d{4,}\w*\b|\b\d{1,3}\b', re.I)
NOMES_FIXOS = {'rede condor': 'Condor', 'iti itau': 'iti Itau', 'nubank': 'Nubank', 'tim': 'TIM'}


def nice_name(fname):
    n = os.path.splitext(fname)[0]
    n = re.sub(r'[_\-.]+', ' ', n)
    n = re.sub(r'([a-z])([A-Z])', r'\1 \2', n) if ' ' not in n.strip() and not n.isupper() else n
    limpo = re.sub(r'\s+', ' ', JUNK.sub(' ', n)).strip()
    if not limpo:
        limpo = re.sub(r'\s+', ' ', n).strip()
    fixo = NOMES_FIXOS.get(limpo.lower())
    if fixo:
        return fixo
    limpo = re.sub(r'\s+', ' ', re.sub(r'[()\[\]{}.,]+', ' ', limpo)).strip() or limpo
    if limpo.isupper() and len(limpo) <= 4:
        return limpo
    pal = []
    for i, w in enumerate(limpo.split()):
        if i and w.lower() in ('do', 'da', 'de', 'dos', 'das', 'e'):
            pal.append(w.lower())
        elif w.isupper() and len(w) <= 4:
            pal.append(w)
        else:
            pal.append(w[:1].upper() + w[1:].lower())
    return ' '.join(pal)


_NOME_RUIM = re.compile(r'\d|\b(site|simbolo|vector|thumb|tipo|kiss|png|logo)\b', re.I)


def _cores_borda(rgb, alfa):
    """Cores que dominam a borda da imagem (fundo liso, xadrez de "transparência falsa"...)."""
    h, w, _ = rgb.shape
    t = max(2, min(h, w) // 100)
    borda = np.concatenate([rgb[:t].reshape(-1, 3), rgb[-t:].reshape(-1, 3),
                            rgb[:, :t].reshape(-1, 3), rgb[:, -t:].reshape(-1, 3)])
    ab = np.concatenate([alfa[:t].ravel(), alfa[-t:].ravel(), alfa[:, :t].ravel(), alfa[:, -t:].ravel()])
    if (ab >= 30).mean() < 0.5:        # a imagem já tem fundo transparente: o que encosta na borda é o logo
        return []
    borda = borda[ab >= 30]
    q = borda // 12
    k = q[:, 0] * 10000 + q[:, 1] * 100 + q[:, 2]
    vals, cont = np.unique(k, return_counts=True)
    ordem = np.argsort(-cont)
    cores, soma = [], 0
    for i in ordem[:4]:
        if cont[i] / len(borda) < 0.08:
            break
        cores.append(borda[k == vals[i]].mean(0))
        soma += cont[i] / len(borda)
    return cores if soma >= 0.6 else []


def _componentes_borda(m):
    """Partes da máscara m ligadas à borda da imagem (preenchimento a partir da borda)."""
    h, w = m.shape
    alcan = np.zeros_like(m)
    alcan[0, :] = m[0, :]; alcan[-1, :] = m[-1, :]; alcan[:, 0] = m[:, 0]; alcan[:, -1] = m[:, -1]
    # propaga em escala reduzida (rápido) e depois refina no tamanho real
    while True:
        im = Image.fromarray((alcan * 255).astype(np.uint8)).filter(ImageFilter.MaxFilter(3))
        novo = (np.array(im) > 0) & m
        for _ in range(30):
            im = Image.fromarray((novo * 255).astype(np.uint8)).filter(ImageFilter.MaxFilter(3))
            novo2 = (np.array(im) > 0) & m
            if (novo2 == novo).all():
                break
            novo = novo2
        if (novo == alcan).all():
            return alcan
        alcan = novo


def remove_background(im: Image.Image) -> Image.Image:
    """Tira o fundo do logo: transparência que já existe, fundo liso (branco, cinza, colorido) e o xadrez de
    "transparência falsa" que vem em muitos PNG da internet. Buracos pequenos das letras (miolo do O, do A)
    também ficam transparentes; partes brancas grandes do desenho ficam."""
    rgba = np.array(im.convert('RGBA'))
    # trabalha numa cópia reduzida (fundo é coisa grande) e aplica a máscara no tamanho real
    h0, w0 = rgba.shape[:2]
    f = max(1, int(np.ceil(max(h0, w0) / 700)))
    peq = np.array(Image.fromarray(rgba).resize((max(1, w0 // f), max(1, h0 // f)), Image.BOX)).astype(np.int32)
    rgb, alfa = peq[..., :3], peq[..., 3]
    transp = alfa < 30
    cores = _cores_borda(rgb, alfa)
    if cores:
        dist = np.min([np.abs(rgb - c).max(axis=2) for c in cores], axis=0)
        fundo = (dist < 34) & ~transp
        fora = _componentes_borda(fundo | transp) & fundo
        if fora.mean() > 0.05:
            # buracos internos pequenos com a cor do fundo (miolo das letras)
            dentro = fundo & ~fora
            if dentro.any():
                from .limpeza import _rotular
                lab = _rotular(dentro)
                tam = np.bincount(lab.ravel()); tam[0] = 0
                lim = 0.015 * dentro.size
                fora |= dentro & (tam[lab] < lim)
                if len(cores) >= 2:     # xadrez de transparência falsa dentro do logo: sempre é fundo
                    perto = [np.abs(rgb - c).max(axis=2) < 34 for c in cores[:2]]
                    n0 = np.bincount(lab[dentro & perto[0]], minlength=len(tam))
                    n1 = np.bincount(lab[dentro & perto[1]], minlength=len(tam))
                    xadrez = (n0 >= 0.2 * tam) & (n1 >= 0.2 * tam) & (tam > 0)
                    fora |= dentro & xadrez[lab]
            # borda suave: pixels de transição entre o logo e o fundo ficam meio transparentes
            mask = Image.fromarray((fora * 255).astype(np.uint8)).resize((w0, h0), Image.BILINEAR)
            m = np.array(mask).astype(np.float32) / 255
            a = rgba.astype(np.float32)
            if cores:
                d = np.min([np.abs(a[..., :3] - c).max(axis=2) for c in cores], axis=0)
                suave = np.clip((d - 20) / 50, 0, 1)
                m = np.where((m > 0) & (m < 1), np.maximum(m, 1 - suave), m)
            a[..., 3] = a[..., 3] * (1 - m)
            rgba = np.clip(a + 0.5, 0, 255).astype(np.uint8)
    out = Image.fromarray(rgba, 'RGBA')
    bb = out.split()[3].point(lambda v: 255 if v > 20 else 0).getbbox()
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

    def _assinatura(self, caminho):
        try:
            st = os.stat(caminho)
            return [st.st_size, int(st.st_mtime)]
        except OSError:
            return None

    def _processar(self, caminho, nome):
        im = Image.open(caminho)
        if im.width < 600:
            im = im.convert('RGBA').resize((im.width * 3, im.height * 3), Image.LANCZOS)
        remove_background(im).save(os.path.join(self.cache_dir, nome + '.png'))
        self._mem.pop(nome, None)

    def scan(self):
        """Procura logos novos na pasta do usuário. Retorna a lista de empresas novas.
        Também refaz (com fundo transparente) as imagens trocadas na pasta e as que ficaram sem cópia limpa:
        essas vão para self.atualizados.
        Quando a limpeza dos logos melhora (VERSAO_CACHE), refaz todos e guarda os nomes que mudaram em
        self.renomeados (nome antigo -> novo) para o app atualizar as empresas."""
        novos = []
        self.renomeados = {}
        self.atualizados = []
        if not os.path.isdir(self.logos_dir):
            return novos
        refazer = self.map.get('_versao') != VERSAO_CACHE
        antigo = {k: v for k, v in self.map.items() if not k.startswith('_')}
        if refazer:
            self.map = {}
        used = set(v for k, v in self.map.items() if not k.startswith('_'))
        arqs = self.map.setdefault('_arquivos', {})
        dono = self.map.setdefault('_dono', {})      # empresa -> arquivo que deu a imagem atual
        for rel, nome in self.map.items():
            if not rel.startswith('_'):
                dono.setdefault(nome, rel)
        for root, _, files in os.walk(self.logos_dir):
            for f in sorted(files):
                if not f.lower().endswith(EXTS):
                    continue
                cam = os.path.join(root, f)
                rel = os.path.relpath(cam, self.logos_dir)
                if rel in self.map:
                    nome = self.map[rel]
                    sig = self._assinatura(cam)
                    trocou = rel in arqs and arqs[rel] != sig and dono.get(nome, rel) == rel
                    sem_img = not os.path.exists(self.path(nome)) and dono.get(nome, rel) == rel
                    if rel not in arqs and not sem_img:
                        arqs[rel] = sig          # versões antigas não guardavam a assinatura do arquivo
                    elif dono.get(nome) != rel:
                        arqs[rel] = sig          # outra imagem é a da empresa: esta só fica registrada
                    elif trocou or sem_img:
                        try:
                            self._processar(cam, nome)
                            arqs[rel] = sig
                            dono[nome] = rel
                            self.atualizados.append(nome)
                        except Exception:
                            pass
                    continue
                nome = nice_name(f)
                if rel in antigo and not _NOME_RUIM.search(antigo[rel]):
                    nome = antigo[rel]            # nome que o usuário já conhece fica
                if nome in used:          # duplicado (mesma empresa)
                    self.map[rel] = nome
                    if refazer and rel in antigo and antigo[rel] != nome:
                        self.renomeados[antigo[rel]] = nome
                    continue
                try:
                    self._processar(cam, nome)
                except Exception:
                    continue
                self.map[rel] = nome; used.add(nome)
                arqs[rel] = self._assinatura(cam); dono[nome] = rel
                if rel in antigo:
                    if antigo[rel] != nome:
                        self.renomeados[antigo[rel]] = nome
                    continue
                pasta = os.path.basename(root) if root != self.logos_dir else ''
                novos.append({'nome': nome, 'pasta': pasta})
        self.map['_versao'] = VERSAO_CACHE
        if self.renomeados:
            r = self.map.setdefault('_renomeados', {})
            r.update(self.renomeados)
        self.save_map()
        return novos

    def nomes(self):
        return sorted(set(v for k, v in self.map.items() if not k.startswith('_')))

    def definir(self, nome, dados: bytes):
        """Imagem escolhida no app para uma empresa: vai para a pasta de logos e vira a imagem da empresa
        (com o fundo tirado). Devolve o caminho gravado."""
        import io as _io
        im = Image.open(_io.BytesIO(dados))
        im.load()
        os.makedirs(self.logos_dir, exist_ok=True)
        base = re.sub(r'[\\/:*?"<>|]+', ' ', nome).strip() or 'empresa'
        cam = os.path.join(self.logos_dir, base + ' (app).png')
        im.save(cam)
        rel = os.path.relpath(cam, self.logos_dir)
        self._processar(cam, nome)
        self.map[rel] = nome
        arqs = self.map.setdefault('_arquivos', {})
        # a imagem nova passa a ser a "dona" da empresa: as outras do mesmo nome deixam de ser refeitas
        self.map.setdefault('_dono', {})[nome] = rel
        arqs[rel] = self._assinatura(cam)
        self.save_map()
        return cam

    def sem_imagem(self, nomes):
        return [n for n in nomes if not os.path.exists(self.path(n))]

    def path(self, nome):
        return os.path.join(self.cache_dir, nome + '.png')

    def load(self, nome):
        if nome not in self._mem:
            p = self.path(nome)
            self._mem[nome] = Image.open(p).convert('RGBA') if os.path.exists(p) else None
        return self._mem[nome]
