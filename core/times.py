"""Cada carreira pode ser com um clube diferente: acha o clube do save, os uniformes dele no kitserver,
prepara bases limpas (sem patrocínio) e aprende onde ficam os patrocínios no molde do uniforme."""
import os, re, json, copy, shutil, unicodedata, threading, traceback
from PIL import Image
from . import ftex, detector, kits

# posições calibradas no jogo (molde GUITAKITMAKER, conferido no Palmeiras) – usadas quando o uniforme
# do clube não tem patrocínio naquela posição para servir de referência
PADRAO = copy.deepcopy(kits.SLOTS)
ORDEM_PADRAO = list(kits.SLOT_ORDER)
VARIANTES_PALMEIRAS = list(kits.VARIANTS)
FAMILIAS_PALMEIRAS = dict(kits.FAMILIAS)

# posições extras que o app passa a vender quando o uniforme original do clube tinha patrocínio nelas
EXTRAS = {
    'acima_peito': 'frente', 'gola': 'frente', 'laterais_frente': 'frente',
    'costas_baixo': 'costas', 'costas_laterais': 'costas',
}
ORDEM_TODAS = ['peito', 'acima_peito', 'barra', 'gola', 'laterais_frente', 'mangas', 'costas', 'costas_baixo',
               'costas_laterais', 'calcao', 'calcao_tras']
# tamanho máximo dos logos nas posições pequenas (a caixa achada pode juntar detalhes vizinhos)
LIMITE = {'acima_peito': (120, 55), 'gola': (110, 70)}
# índice da área de busca do detector -> índice do lugar calibrado (as mangas estão em outra ordem)
MAPA_LUGAR = {'mangas': {0: 1, 1: 0, 2: 3, 3: 2}}


def norm(s):
    s = unicodedata.normalize('NFKD', s or '').encode('ascii', 'ignore').decode()
    return re.sub(r'[^A-Z0-9]', '', s.upper())


def ler_map(pasta_jogo):
    mapa = {}
    p = os.path.join(pasta_jogo, 'GOGOSZ', 'kitserver', 'map.txt')
    try:
        for line in open(p, encoding='utf-8-sig', errors='replace'):
            m = re.match(r'\s*(\d+)\s*,\s*"([^"]+)"', line)
            if m:
                mapa[int(m.group(1))] = m.group(2)
    except OSError:
        pass
    return mapa


def candidatos(nome_clube, mapa):
    """Times do map.txt com o mesmo nome do clube do save (o Brasil vem primeiro)."""
    alvo = norm(nome_clube)
    if not alvo:
        return []
    exatos, parecidos = [], []
    for tid, path in mapa.items():
        n = norm(path.replace('/', '\\').split('\\')[-1])
        if n == alvo:
            exatos.append(tid)
        elif len(alvo) >= 4 and (n.startswith(alvo) or alvo.startswith(n)) and len(n) >= 4:
            parecidos.append(tid)
    br = lambda t: (0 if 'BRASIL' in norm(mapa[t].split('\\')[0]) else 1, t)
    return sorted(exatos, key=br) + sorted(parecidos, key=br)


def nome_curto(mapa, tid):
    return (mapa.get(tid) or f'Time {tid}').replace('/', '\\').split('\\')[-1]


def pasta_kits(pasta_jogo, mapa, tid):
    return os.path.join(pasta_jogo, 'GOGOSZ', 'kitserver', *mapa.get(tid, '').replace('/', '\\').split('\\'))


def listar_variantes(pasta):
    """Pastas p1, p1x1, ... de cada uniforme de linha e o arquivo principal da textura de cada uma."""
    out = []
    try:
        nomes = os.listdir(pasta)
    except OSError:
        return out
    for v in nomes:
        m = re.fullmatch(r'p(\d+)(x\d+)?', v.lower())
        if not m or not os.path.isdir(os.path.join(pasta, v)):
            continue
        arqs = [f for f in os.listdir(os.path.join(pasta, v)) if re.fullmatch(r'u\d+p\d+\.ftex', f.lower())]
        if not arqs:
            continue
        out.append((v, arqs[0][:-5], 'p' + m.group(1)))
    chave = lambda x: (int(re.findall(r'\d+', x[0])[0]), len(x[0]), x[0])
    return sorted(out, key=chave)


class Times:
    """Guarda a configuração de cada clube em data/times/<id>/time.json."""

    def __init__(self, data_dir, cfg, log=print):
        self.data = data_dir
        self.cfg = cfg
        self.log = log
        self.mapa = ler_map(cfg.get('pasta_jogo', ''))
        self.prep = {}          # id -> progresso da preparação

    def dir(self, tid):
        return os.path.join(self.data, 'times', str(tid))

    def carregar(self, tid):
        p = os.path.join(self.dir(tid), 'time.json')
        try:
            return json.load(open(p, encoding='utf-8'))
        except Exception:
            pass
        if tid == 137 and os.path.isdir(os.path.join(self.data, 'kits_base', 'p1')):
            # o Palmeiras já foi preparado à mão nas versões anteriores
            t = {'id': 137, 'nome': 'Palmeiras', 'pasta': self.cfg.get('pasta_kits') or pasta_kits(
                     self.cfg['pasta_jogo'], self.mapa, 137),
                 'base_dir': os.path.join(self.data, 'kits_base'), 'variantes': VARIANTES_PALMEIRAS,
                 'familias': FAMILIAS_PALMEIRAS, 'slots': PADRAO, 'ordem': ORDEM_PADRAO, 'preparado': True,
                 'atratividade_base': self.cfg.get('atratividade_base', 68), 'deteccao': {}, 'legado': True}
            self.salvar(t)
            return t
        return None

    def salvar(self, t):
        os.makedirs(self.dir(t['id']), exist_ok=True)
        p = os.path.join(self.dir(t['id']), 'time.json')
        json.dump(t, open(p + '.tmp', 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
        os.replace(p + '.tmp', p)

    def novo(self, tid):
        pasta = pasta_kits(self.cfg['pasta_jogo'], self.mapa, tid)
        vs = listar_variantes(pasta)
        fams = {}
        for _, _, f in vs:
            fams.setdefault(f, f'Uniforme {f[1:]}')
        t = {'id': tid, 'nome': nome_curto(self.mapa, tid), 'pasta': pasta,
             'base_dir': os.path.join(self.dir(tid), 'kits_base'), 'variantes': [list(v) for v in vs],
             'familias': fams, 'slots': copy.deepcopy(PADRAO), 'ordem': list(ORDEM_PADRAO), 'preparado': False,
             'atratividade_base': 55, 'deteccao': {}}
        self.salvar(t)
        return t

    def obter(self, tid):
        return self.carregar(tid) or self.novo(tid)

    # ---------- preparação: backup, detecção, limpeza ----------
    def original(self, t, variant, fname):
        """Textura original (cópia de segurança do app; na primeira vez copia da pasta do jogo)."""
        bk = os.path.join(self.dir(t['id']), 'originais', variant, fname + '.ftex')
        if not os.path.exists(bk):
            os.makedirs(os.path.dirname(bk), exist_ok=True)
            shutil.copy2(os.path.join(t['pasta'], variant, fname + '.ftex'), bk)
        return bk

    def principal(self, t, fam):
        return next(v for v in t['variantes'] if v[2] == fam)

    def detectar(self, t, progresso=None):
        """Acha os patrocínios do uniforme original de cada família (só detecta; não grava nada no jogo)."""
        det = {}
        vs = t['variantes']
        for i, (variant, fname, fam) in enumerate(vs):
            if progresso:
                progresso(i, len(vs), f'Procurando patrocínios: {variant}')
            img = ftex.read(self.original(t, variant, fname))
            ach = detector.detectar_molde(img)
            man = detector.detectar_manter(img)
            d = det.setdefault(fam, {'variantes': {}, 'extras': [], 'desmarcados': []})
            d['variantes'][variant] = {'achados': ach, 'manter': man}
            if variant == self.principal(t, fam)[0]:
                img.convert('RGB').resize((1024, 1024), Image.LANCZOS).save(
                    os.path.join(self.dir(t['id']), f'revisao_{fam}.jpg'), quality=86)
        anterior = t.get('deteccao') or {}
        for fam, d in det.items():   # mantém as escolhas que o usuário já tinha feito
            if fam in anterior:
                d['extras'] = anterior[fam].get('extras', [])
                d['desmarcados'] = anterior[fam].get('desmarcados', [])
        t['deteccao'] = det
        self.salvar(t)
        return det

    @staticmethod
    def chave(a):
        return f"{a['slot']}:{a['lugar']}"

    def itens_revisao(self, t, fam):
        """Lista para a tela de revisão: caixas achadas no uniforme principal + as desenhadas à mão."""
        d = (t.get('deteccao') or {}).get(fam)
        if not d:
            return []
        v = self.principal(t, fam)[0]
        ach = d['variantes'].get(v, {}).get('achados', [])
        # posições achadas só nas outras variações também entram
        vistos = {self.chave(a) for a in ach}
        for vv in d['variantes'].values():
            for a in vv['achados']:
                if self.chave(a) not in vistos:
                    ach.append(a); vistos.add(self.chave(a))
        out = []
        for a in ach:
            nome = detector.MOLDE[a['slot']]['nome']
            if len(detector.MOLDE[a['slot']]['busca']) > 1:
                nome += f" · {a['lugar'] + 1}"
            out.append({'chave': self.chave(a), 'nome': nome, 'caixa': a['caixa'],
                        'marcado': self.chave(a) not in d.get('desmarcados', []), 'manual': False})
        for i, c in enumerate(d.get('extras', [])):
            out.append({'chave': f'extra:{i}', 'nome': 'Área marcada por você', 'caixa': c, 'marcado': True,
                        'manual': True})
        return out

    def limpar(self, t, progresso=None):
        """Apaga os patrocínios marcados em todas as variações e grava as bases limpas do app."""
        vs = t['variantes']
        for i, (variant, fname, fam) in enumerate(vs):
            if progresso:
                progresso(i, len(vs), f'Limpando {variant}')
            d = t['deteccao'][fam]
            principal = d['variantes'][self.principal(t, fam)[0]]
            proprio = d['variantes'].get(variant) or principal
            fora = set(d.get('desmarcados', []))
            caixas = {}
            for a in principal['achados'] + [x for vv in d['variantes'].values() for x in vv['achados']]:
                caixas.setdefault(self.chave(a), a['caixa'])
            for a in proprio['achados']:          # cada variação usa a caixa achada nela mesma
                caixas[self.chave(a)] = a['caixa']
            lista = [c for k, c in caixas.items() if k not in fora] + list(d.get('extras', []))
            orig = self.original(t, variant, fname)
            img = ftex.read(orig)
            limpo = detector.limpar(img, lista, proprio['manter'])
            dst = os.path.join(t['base_dir'], variant, fname + '.ftex')
            os.makedirs(os.path.dirname(dst), exist_ok=True)
            ftex.write(limpo, orig, dst)
        kits._base_cache.clear()
        self.aprender(t)
        t['preparado'] = True
        self.salvar(t)

    def aprender(self, t):
        """Guarda onde ficavam os patrocínios do uniforme original para encaixar os novos no mesmo lugar."""
        achados = {}
        for fam, d in (t.get('deteccao') or {}).items():
            fora = set(d.get('desmarcados', []))
            for a in d['variantes'][self.principal(t, fam)[0]]['achados']:
                if self.chave(a) in fora or (a['slot'] == 'calcao_tras' and fam != 'p1'):
                    continue
                achados.setdefault(a['slot'], {}).setdefault(a['lugar'], a)
        slots = copy.deepcopy(PADRAO)
        for slot, por_lugar in achados.items():
            molde = detector.MOLDE[slot]
            if slot in slots:
                base = slots[slot]
            else:
                if slot not in EXTRAS:
                    continue
                base = {'nome': molde['nome'], 'valor_base': molde['valor_base'], 'vista': EXTRAS[slot],
                        'lugares': [None] * len(molde['busca'])}
                slots[slot] = base
            lugares = list(base['lugares'])
            ref = None
            for i_busca, a in por_lugar.items():
                x0, y0, x1, y1 = a['caixa']
                rot = a['rot']
                w, h = (x1 - x0 - 8), (y1 - y0 - 8)
                if rot in (90, -90):
                    w, h = h, w
                k = MAPA_LUGAR.get(slot, {}).get(i_busca, i_busca)
                if k >= len(lugares):
                    continue
                antigo = lugares[k]
                lado = antigo[5] if antigo and len(antigo) > 5 else (1 if k % 2 == 0 or len(lugares) == 1 else -1)
                if slot == 'mangas':
                    lado = 1 if k < 2 else -1
                lim = LIMITE.get(slot)
                if lim:
                    w, h = min(w, lim[0]), min(h, lim[1])
                lugares[k] = [(x0 + x1) // 2, (y0 + y1) // 2, max(40, w), max(20, h), rot, lado]
                ref = lugares[k]
            for k, l in enumerate(lugares):        # par sem patrocínio de um dos lados: centro da área de busca
                if l is None:
                    inv = {v: kk for kk, v in MAPA_LUGAR.get(slot, {}).items()}
                    (bx0, by0, bx1, by1), rot = molde['busca'][inv.get(k, k)]
                    w, h = (ref[2], ref[3]) if ref else (bx1 - bx0, by1 - by0)
                    lugares[k] = [(bx0 + bx1) // 2, (by0 + by1) // 2, w, h, rot, 1 if k % 2 == 0 else -1]
            base['lugares'] = lugares
            base['aprendido'] = True
        t['slots'] = slots
        t['ordem'] = [s for s in ORDEM_TODAS if s in slots]

    def preparar(self, t, so_detectar=False, depois=None):
        """Roda em segundo plano: detecta e (se pedido) limpa. 'depois' é chamado no fim."""
        tid = t['id']
        if self.prep.get(tid, {}).get('rodando'):
            return

        def prog(i, n, msg):
            self.prep[tid] = {'rodando': True, 'i': i, 'n': n, 'msg': msg}

        def run():
            prog(0, 1, 'Começando...')
            try:
                if not t.get('deteccao') or so_detectar:
                    self.detectar(t, prog)
                if not so_detectar:
                    self.limpar(t, prog)
                self.prep[tid] = {'rodando': False, 'msg': 'Pronto', 'ok': True}
                if depois:
                    depois(t)
            except Exception as e:
                self.log(traceback.format_exc())
                self.prep[tid] = {'rodando': False, 'msg': f'Erro: {e}', 'erro': True}

        threading.Thread(target=run, daemon=True).start()
