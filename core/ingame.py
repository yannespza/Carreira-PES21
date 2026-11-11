"""Mudanças visuais dentro do jogo, sempre para o clube da carreira atual (o estádio vem do map_teams.txt do
StadiumServer do GOGOSZ):
- faixas da torcida no estádio (apoio com aprovação alta, protesto com aprovação baixa);
- gramado conforme as finanças (impecável com finanças excelentes, seco e falhado com corte de custos);
- bandeirinhas de escanteio com as cores do clube e a marca do patrocinador master.
O app grava as texturas em GOGOSZ\\AppCarreira e o módulo AppCarreira.lua do Sider entrega esses arquivos ao
jogo só nos jogos em casa do clube."""
import os, re, shutil, struct, random, time
import numpy as np
from PIL import Image, ImageDraw, ImageFilter

PASTA = 'AppCarreira'
MODULO = 'AppCarreira.lua'

LUA = r'''-- App Carreira PES 21: entrega as texturas geradas pelo app (faixas, gramado, bandeirinhas)
-- nos jogos em casa do clube da carreira. Gerado pelo app; pode apagar que o app recria.
local root = ".\\GOGOSZ\\AppCarreira"
local regras = {}
local clube = nil
local em_casa = false

local function carregar()
    regras = {}
    clube = nil
    local f = io.open(root .. "\\mapa.txt", "r")
    if not f then return end
    for line in f:lines() do
        local t = line:match("^time=(%d+)")
        if t then clube = tonumber(t) end
        local m, a, q = line:match("^([^|]+)|([^|]+)|(%a+)")
        if m and a then regras[#regras + 1] = { m = string.lower(m), a = a, q = q } end
    end
    f:close()
end

local function set_teams(ctx, home, away)
    carregar()
    em_casa = (clube ~= nil and tonumber(home) == clube)
    if #regras > 0 then
        log(string.format("AppCarreira: clube %s, mandante %s, em casa: %s, %d arquivos", tostring(clube), tostring(home), tostring(em_casa), #regras))
    end
end

local function make_key(ctx, filename)
    if #regras == 0 then return nil end
    local fl = string.lower(filename)
    for _, r in ipairs(regras) do
        if (r.q == "sempre" or (r.q == "casa" and em_casa)) and #fl >= #r.m and fl:sub(-#r.m) == r.m then
            return "appcarreira:" .. r.a
        end
    end
end

local function get_filepath(ctx, filename, key)
    if key and key:sub(1, 12) == "appcarreira:" then
        return root .. "\\" .. key:sub(13)
    end
end

local function init(ctx)
    if root:sub(1, 1) == "." then root = ctx.sider_dir .. root end
    carregar()
    ctx.register("set_teams", set_teams)
    ctx.register("livecpk_make_key", make_key)
    ctx.register("livecpk_get_filepath", get_filepath)
end

return { init = init }
'''


def _limpo(s):
    return s.split('#', 1)[0].strip()


def estadio_do_time(pasta_jogo, team_id):
    """(id do estádio, pasta do estádio) do clube, pelo map_teams.txt do StadiumServer."""
    p = os.path.join(pasta_jogo, 'GOGOSZ', 'Estadios', 'map_teams.txt')
    try:
        linhas = open(p, encoding='utf-8-sig', errors='replace').read().splitlines()
    except OSError:
        return None
    for ln in linhas:
        c = [x.strip() for x in _limpo(ln).split(',')]
        if len(c) >= 4 and c[0].isdigit() and int(c[0]) == int(team_id) and c[1].isdigit():
            pasta = os.path.join(pasta_jogo, 'GOGOSZ', 'Estadios', c[3].replace('/', '\\').replace('\\', os.sep))
            return {'id': int(c[1]), 'nome': c[2], 'pasta': pasta}
    return None


def _texturas_estadio(est):
    d = os.path.join(est['pasta'], 'Asset', 'model', 'bg', 'st%03d' % est['id'], 'sourceimages', 'tga', '#windx11')
    try:
        return d, sorted(os.listdir(d))
    except OSError:
        return d, []


def _formato_ok(path):
    try:
        pf = struct.unpack_from('<H', open(path, 'rb').read(10), 8)[0]
        return pf in (0, 2, 3, 4)
    except OSError:
        return False


def _rgb(h):
    h = (h or '#1f6b3a').lstrip('#')
    return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))


def _fonte(tam):
    from .cena import _fonte as f
    return f(tam)


def _texto_cabido(draw, txt, w, h, maxfrac=0.62):
    tam = int(h * maxfrac)
    f = _fonte(tam)
    while tam > 8 and draw.textlength(txt, font=f) > w * 0.9:
        tam -= 2
        f = _fonte(tam)
    return f


# ---------------- faixas ----------------
APOIO = ['VAMOS {CLUBE}!', 'AQUI É {CLUBE}', '{TECNICO} É NOSSO!', 'RUMO AO TÍTULO', 'ORGULHO DE SER {CLUBE}',
         '{IDOLO} É MONSTRO', 'NINGUÉM CALA ESSA TORCIDA', 'O {CLUBE} É GIGANTE']
PROTESTO = ['FORA DIRETORIA', 'VERGONHA!', 'TIME SEM ALMA', 'RESPEITA A CAMISA', 'ACORDA {CLUBE}!',
            'CHEGA DE VEXAME', 'QUEREMOS RAÇA', '{TECNICO} PEDE PRA SAIR']


def faixa(w, h, texto, cor1, cor2, escudo, protesto=False, idx=0):
    if protesto:      # protesto: fundo preto, letra vermelha, faixa "de cabeça para baixo"
        fundo, letra, borda = (12, 12, 12), (215, 25, 32), (215, 25, 32)
    else:
        c1, c2 = _rgb(cor1), _rgb(cor2)
        fundo, letra, borda = (c1, c2, c2) if idx % 2 == 0 else (c2, c1, c1)
        if sum(abs(a - b) for a, b in zip(fundo, letra)) < 120:
            letra = (255, 255, 255) if sum(fundo) < 380 else (20, 20, 20)
    img = Image.new('RGB', (w, h), fundo)
    d = ImageDraw.Draw(img)
    e = max(2, h // 26)
    d.rectangle([e, e, w - e - 1, h - e - 1], outline=borda, width=e)
    x0 = e * 3
    if escudo is not None and not protesto and w > h * 1.6:
        lg = escudo.convert('RGBA').copy()
        lg.thumbnail((int(h * 0.8), int(h * 0.8)), Image.LANCZOS)
        img.paste(lg, (x0, (h - lg.height) // 2), lg)
        img.paste(lg, (w - x0 - lg.width, (h - lg.height) // 2), lg)
        x0 += lg.width + e
    area = w - 2 * x0
    f = _texto_cabido(d, texto, area, h, 0.5)
    tw = d.textlength(texto, font=f)
    bb = d.textbbox((0, 0), texto, font=f)
    d.text((x0 + (area - tw) / 2, (h - (bb[3] - bb[1])) / 2 - bb[1]), texto, font=f, fill=letra)
    if protesto:
        img = img.rotate(180)
    # tecido: leve ruído e sombra nas bordas
    a = np.array(img).astype(np.float32)
    a *= (0.93 + 0.07 * np.random.default_rng(idx).random(a.shape[:2]))[..., None]
    return Image.fromarray(np.clip(a, 0, 255).astype(np.uint8)).convert('RGBA')


# ---------------- gramado ----------------
# As texturas do gramado do PES não guardam a cor da grama, e sim mapas:
#  pitch_alp:   R = ruído do gramado, G = desgaste/terra, B = área do campo, A = linhas do campo
#  pitch_grain: R e G = faixas do corte da grama (vertical e horizontal)
# Então o gramado "bom" tira o desgaste e reforça o corte; o "ruim" espalha falhas e apaga as faixas.
def _manchas(W, H, seed, escala=48, blur=2):
    rng = np.random.default_rng(seed)
    k = max(4, min(W, H) // escala)
    n = rng.random((max(2, H // k), max(2, W // k))).astype(np.float32)
    n = np.array(Image.fromarray((n * 255).astype(np.uint8)).resize((W, H), Image.BICUBIC)
                 .filter(ImageFilter.GaussianBlur(k / blur))).astype(np.float32) / 255
    return (n - n.min()) / max(1e-6, n.max() - n.min())


def gramado(img, nivel, seed=1, nome='pitch_alp.ftex'):
    a = np.array(img.convert('RGBA')).astype(np.float32)
    H, W = a.shape[:2]
    if 'grain' in nome.lower():
        for c in (0, 1):
            ch = a[..., c]
            m = ch.mean()
            if nivel == 'otimo':
                a[..., c] = m + (ch - m) * 1.45          # faixas de corte bem marcadas
            else:
                ruido = (_manchas(W, H, seed + c, 24, 1.5) - 0.5) * 40
                a[..., c] = m + (ch - m) * 0.35 + ruido  # grama sem corte, irregular
    else:
        campo = (a[..., 2] > 128).astype(np.float32)
        g = a[..., 1]
        if nivel == 'otimo':
            a[..., 1] = g * 0.2                          # quase sem desgaste
        else:
            n = _manchas(W, H, seed, 40, 2)
            falhas = np.clip((n - 0.45) * 3.0, 0, 1)
            buracos = np.clip((_manchas(W, H, seed + 7, 90, 1.2) - 0.82) * 8, 0, 1)
            a[..., 1] = np.clip(g * 1.6 + (falhas * 110 + buracos * 230) * campo, 0, 255)
    a = np.clip(a, 0, 255)
    return Image.fromarray(a.astype(np.uint8), 'RGBA')


# ---------------- bandeirinha ----------------
def bandeirinha(w, h, cor1, cor2, patro):
    c1, c2 = _rgb(cor1), _rgb(cor2)
    img = Image.new('RGBA', (w, h), c1 + (255,))
    d = ImageDraw.Draw(img)
    d.rectangle([0, int(h * 0.78), w, h], fill=c2 + (255,))
    d.rectangle([0, 0, w, int(h * 0.08)], fill=c2 + (255,))
    if patro is not None:
        pl = Image.new('RGBA', (int(w * 0.84), int(h * 0.5)), (255, 255, 255, 255))
        lg = patro.convert('RGBA').copy()
        bb = lg.getbbox()
        if bb:
            lg = lg.crop(bb)
        lg.thumbnail((int(pl.width * 0.9), int(pl.height * 0.85)), Image.LANCZOS)
        pl.alpha_composite(lg, ((pl.width - lg.width) // 2, (pl.height - lg.height) // 2))
        img.alpha_composite(pl, ((w - pl.width) // 2, int(h * 0.18)))
    return img


# ---------------- instalação no Sider ----------------
def instalar_modulo(pasta_jogo, backup_dir, log=print):
    """Grava o AppCarreira.lua em modules e põe na lista do sider.ini antes dos servidores de estádio."""
    mod = os.path.join(pasta_jogo, 'modules', MODULO)
    try:
        if not os.path.exists(mod) or open(mod, encoding='utf-8', errors='replace').read() != LUA:
            open(mod, 'w', encoding='utf-8').write(LUA)
    except OSError as e:
        log('não gravou o módulo do Sider:', e)
        return False
    ini = os.path.join(pasta_jogo, 'sider.ini')
    try:
        txt = open(ini, encoding='utf-8', errors='replace').read()
    except OSError:
        return False
    if MODULO.lower() in txt.lower():
        return True
    os.makedirs(backup_dir, exist_ok=True)
    shutil.copy2(ini, os.path.join(backup_dir, 'sider.ini.%d.bak' % int(time.time())))
    linhas = txt.splitlines(True)
    pos = None
    for i, ln in enumerate(linhas):
        l = ln.strip().lower()
        if l.startswith('lua.module') and any(k in l for k in ('stadium_banner', 'tournamentcornerflags', 'stadiumserver', 'menuserver')):
            pos = i
            break
    if pos is None:
        pos = max([i for i, ln in enumerate(linhas) if ln.strip().lower().startswith('lua.module')] or [len(linhas) - 1]) + 1
    nl = '\r\n' if '\r\n' in txt else '\n'
    linhas.insert(pos, f'lua.module = "{MODULO}"{nl}')
    open(ini, 'w', encoding='utf-8').write(''.join(linhas))
    log('módulo AppCarreira.lua adicionado ao sider.ini')
    return True


def gerar(pasta_jogo, team_id, clube, cores, escudo, patro, torcida, nivel_gramado, tecnico, idolo, log=print):
    """Monta as texturas do clube atual e o mapa.txt que o módulo do Sider lê. Devolve um resumo."""
    out = os.path.join(pasta_jogo, 'GOGOSZ', PASTA)
    os.makedirs(out, exist_ok=True)
    regras, resumo = [], {'estadio': None, 'faixas': None, 'gramado': None, 'bandeirinha': False}
    cor1 = cores[0] if cores else '#1f6b3a'
    cor2 = cores[1] if cores and len(cores) > 1 else '#ffffff'
    est = estadio_do_time(pasta_jogo, team_id)
    v = {'CLUBE': (clube or '').upper(), 'TECNICO': (tecnico or '').upper().split(' ')[0], 'IDOLO': (idolo or '').upper()}
    if est:
        resumo['estadio'] = est['nome']
        d, arqs = _texturas_estadio(est)
        st = 'st%03d' % est['id']
        # faixas da torcida: texturas de bandeira/faixa do próprio estádio
        modo = 'apoio' if torcida >= 75 else 'protesto' if torcida <= 30 else None
        alvo = [a for a in arqs if a.lower().endswith('.ftex') and not re.search(r'_(nrm|srm|bsm|lym|lbm|alp)', a.lower())
                and re.match(r'(flag|novo banner|banner|faixa)', a.lower()) and _formato_ok(os.path.join(d, a))]
        if modo and alvo:
            frases = PROTESTO if modo == 'protesto' else APOIO
            r = random.Random(f'{team_id}{modo}')
            for i, a in enumerate(alvo):
                src = os.path.join(d, a)
                try:
                    from . import ftex
                    base = ftex.read(src)
                    t = r.choice(frases).format(**v).replace('  ', ' ').strip()
                    if '{' in t or not t.strip('! '):
                        t = 'VAMOS ' + v['CLUBE']
                    img = faixa(base.width, base.height, t, cor1, cor2, escudo, modo == 'protesto', i)
                    nome = f'faixa_{i}.ftex'
                    ftex.write(img, src, os.path.join(out, nome))
                    regras.append((f'{st}\\sourceimages\\tga\\#windx11\\{a}', nome, 'casa'))
                except Exception as e:
                    log('faixa não gerada', a, e)
            resumo['faixas'] = modo
        # gramado
        if nivel_gramado in ('otimo', 'ruim'):
            for a in arqs:
                al = a.lower()
                if al in ('pitch_grain.ftex', 'pitch_alp.ftex') and _formato_ok(os.path.join(d, a)):
                    try:
                        from . import ftex
                        img = gramado(ftex.read(os.path.join(d, a)), nivel_gramado, team_id, al)
                        nome = f'gramado_{al}'
                        ftex.write(img, os.path.join(d, a), os.path.join(out, nome))
                        regras.append((f'{st}\\sourceimages\\tga\\#windx11\\{a}', nome, 'casa'))
                    except Exception as e:
                        log('gramado não gerado', a, e)
            resumo['gramado'] = nivel_gramado
    # bandeirinhas: textura de cor das bandeirinhas (a do TournamentCornerFlags serve de molde)
    molde = None
    tcf = os.path.join(pasta_jogo, 'GOGOSZ', 'TournamentCornerFlags')
    for comp in ('Default', 'Brasileiro A', 'Brasileiro B'):
        p = os.path.join(tcf, comp, 'Asset', 'model', 'bg', 'common', 'cornerflag', 'sourceimages', '#windx11', 'c_flag_bsm.ftex')
        if os.path.exists(p) and _formato_ok(p):
            molde = p
            break
    if molde and patro is not None:
        try:
            from . import ftex
            base = ftex.read(molde)
            w, h = max(base.width, 256), max(base.height, 256)
            ftex.write(bandeirinha(w, h, cor1, cor2, patro), molde, os.path.join(out, 'bandeirinha_bsm.ftex'))
            regras.append(('cornerflag\\sourceimages\\#windx11\\c_flag_bsm.ftex', 'bandeirinha_bsm.ftex', 'casa'))
            resumo['bandeirinha'] = True
        except Exception as e:
            log('bandeirinha não gerada', e)
    with open(os.path.join(out, 'mapa.txt'), 'w', encoding='utf-8') as f:
        f.write(f'time={int(team_id)}\n')
        for m, a, q in regras:
            f.write(f'{m}|{a}|{q}\n')
    resumo['arquivos'] = len(regras)
    return resumo
