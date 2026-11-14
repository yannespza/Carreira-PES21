"""Mudanças visuais dentro do jogo, sempre para o clube da carreira atual (o estádio vem do map_teams.txt do
StadiumServer do GOGOSZ):
- faixas da torcida no estádio conforme o momento (título, aniversário, clássico, apoio, protesto), em
  quantidade proporcional à força do momento;
- gramado conforme a condição (desgasta a cada jogo em casa, recupera com folga e manutenção);
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
-- v2: registra no sider.log o que o jogo pediu e o que foi entregue (diagnóstico).
local root = ".\\GOGOSZ\\AppCarreira"
local regras = {}
local clube = nil
local em_casa = false
local vistos = {}

local function existe(p)
    local f = io.open(p, "rb")
    if f then f:close() return true end
    return false
end

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
    vistos = {}
    em_casa = (clube ~= nil and tonumber(home or ctx.home_team) == clube)
    log(string.format("AppCarreira v2: clube %s, mandante %s, visitante %s, em casa: %s, %d regras",
        tostring(clube), tostring(home), tostring(away), tostring(em_casa), #regras))
end

local function make_key(ctx, filename)
    if #regras == 0 or not filename then return nil end
    local fl = string.lower(filename)
    for _, r in ipairs(regras) do
        if (r.q == "sempre" or (r.q == "casa" and em_casa)) and #fl >= #r.m and fl:sub(-#r.m) == r.m then
            if not vistos[fl] then
                vistos[fl] = true
                log("AppCarreira: troca " .. filename .. " -> " .. r.a)
            end
            return "appcarreira:" .. r.a
        end
    end
    -- diagnóstico: arquivos de faixa e bandeirinha que o jogo pediu e não estão nas regras
    if em_casa and not vistos[fl] and (fl:find("faixa", 1, true) or fl:find("c_flag", 1, true) or fl:find("cornerflag", 1, true)) then
        vistos[fl] = true
        log("AppCarreira: pedido sem regra: " .. filename)
    end
end

local function get_filepath(ctx, filename, key)
    if key and key:sub(1, 12) == "appcarreira:" then
        local p = root .. "\\" .. key:sub(13)
        if not vistos[p] then
            vistos[p] = true
            log("AppCarreira: entregando " .. p .. (existe(p) and "" or " (ARQUIVO NÃO EXISTE)"))
        end
        return p
    end
end

local function init(ctx)
    if root:sub(1, 1) == "." then root = ctx.sider_dir .. root end
    carregar()
    log("AppCarreira v2 iniciado: " .. root .. " (" .. #regras .. " regras)")
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
        pf, w, h = struct.unpack_from('<HHH', open(path, 'rb').read(14), 8)
        return pf in (0, 2, 3, 4) and w % 4 == 0 and h % 4 == 0   # compressão em blocos de 4x4
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


def gramado(img, nivel, seed=1, nome='pitch_alp.ftex', forca=1.0):
    """forca de 0 a 1: o quanto o gramado está impecável (otimo) ou castigado (ruim)."""
    a = np.array(img.convert('RGBA')).astype(np.float32)
    H, W = a.shape[:2]
    f = max(0.2, min(1.0, forca))
    if 'grain' in nome.lower():
        for c in (0, 1):
            ch = a[..., c]
            m = ch.mean()
            if nivel == 'otimo':
                a[..., c] = m + (ch - m) * (1 + 0.45 * f)          # faixas de corte bem marcadas
            else:
                ruido = (_manchas(W, H, seed + c, 24, 1.5) - 0.5) * 40 * f
                a[..., c] = m + (ch - m) * (1 - 0.65 * f) + ruido  # grama sem corte, irregular
    else:
        campo = (a[..., 2] > 128).astype(np.float32)
        g = a[..., 1]
        if nivel == 'otimo':
            a[..., 1] = g * (1 - 0.8 * f)                          # quase sem desgaste
        else:
            n = _manchas(W, H, seed, 40, 2)
            falhas = np.clip((n - 0.45) * 3.0, 0, 1)
            buracos = np.clip((_manchas(W, H, seed + 7, 90, 1.2) - 0.82) * 8, 0, 1)
            a[..., 1] = np.clip(g * (1 + 0.6 * f) + (falhas * 110 + buracos * 230 * f) * f * campo, 0, 255)
    a = np.clip(a, 0, 255)
    return Image.fromarray(a.astype(np.uint8), 'RGBA')


# ---------------- condição do gramado (0 a 100) ----------------
# Cada jogo em casa castiga o gramado e ele NÃO se recupera sozinho: só volta com investimento
# (estrutura.investir_gramado). Verão chuvoso (dez a mar) castiga mais; jogos em casa em sequência também.
# A equipe de gramado (estrutura) diminui o desgaste por jogo.
def condicao_gramado(state, hoje, team_id, nomes=None):
    from . import estrutura
    from .sim import d2s, s2d
    gr = state.setdefault('gramado', {'cond': 80.0, 'data': None, 'vistos': []})
    gr.setdefault('eventos', [])
    if not hoje:
        return gr
    vistos = set(gr.get('vistos', []))
    if not gr.get('data'):         # primeira leitura: jogos antigos não desgastam
        vistos |= {p['chave'] for p in state.get('partidas', [])}
    casa = sorted([p for p in state.get('partidas', []) if p['mandante'] == team_id and p['chave'] not in vistos],
                  key=lambda p: p['data'])
    ult = max((s2d(e['data']) for e in gr['eventos'] if e['tipo'] == 'jogo'), default=None)
    for p in casa:
        d = s2d(p['data'])
        chuva = 1.3 if d.month in (12, 1, 2, 3) else 1.0
        perda = 6 * chuva * estrutura.desgaste_gramado(state) + (3 if ult and (d - ult).days <= 4 else 0)
        antes = gr['cond']
        gr['cond'] = round(max(0.0, gr['cond'] - perda), 1)
        adv = (nomes or {}).get(p['visitante'], '')
        gr['eventos'].append({'data': p['data'], 'tipo': 'jogo', 'texto': f'Jogo em casa' + (f' contra {adv}' if adv else '')
                              + (' (chuva de verão)' if chuva > 1 else ''), 'antes': antes, 'depois': gr['cond']})
        ult = d
        vistos.add(p['chave'])
    o = gr.get('obra')
    if o and s2d(o['fim']) <= hoje:
        estrutura.aplicar_gramado(gr, o['ganho'], o['nome'] + ' (concluído)', o['fim'])
        gr.pop('obra')
    gr['eventos'] = gr['eventos'][-40:]
    gr['vistos'] = sorted(vistos)[-200:]
    gr['data'] = d2s(hoje)
    h = gr.setdefault('hist', [])
    if not h or h[-1][0] != gr['data']:
        h.append([gr['data'], gr['cond']])
    else:
        h[-1][1] = gr['cond']
    gr['hist'] = h[-40:]
    return gr


def nivel_gramado(cond):
    """(nivel, forca) para a textura: impecável a partir de 82, castigado até 45, normal entre os dois."""
    if cond >= 82:
        return 'otimo', round(0.5 + (cond - 82) / 36, 1)
    if cond <= 45:
        return 'ruim', round(max(0.35, (45 - cond) / 45 + 0.2), 1)
    return None, 0


# ---------------- faixas conforme o momento ----------------
TITULO = ['É CAMPEÃO!', 'OBRIGADO, CAMPEÕES!', '{CLUBE} CAMPEÃO {ANO}', '{COMP} É NOSSA!', 'ORGULHO DE SER {CLUBE}']
ANIVERSARIO = ['PARABÉNS {CLUBE}! {N} ANOS', '{N} ANOS DE GLÓRIA', 'FELIZ ANIVERSÁRIO, {CLUBE}', 'DESDE {FUND} COM VOCÊ']
CLASSICO = ['{RIVAL}, FREGUÊS!', 'O {CLASSICO} É NOSSO', 'A CIDADE TEM DONO']


def plano_faixas(state, clube, hoje, tecnico, idolo, rivais_nomes):
    """Qual faixa a torcida leva para o próximo jogo em casa: modo, frases, parte das faixas trocadas e motivo."""
    from . import rivais
    from .sim import s2d, COMP_NOMES
    from .diretoria import situacao
    m = state.get('mundo') or {}
    t = m.get('torcida', 50)
    g = state.get('gestao') or {}
    v = {'CLUBE': (clube or '').upper(), 'TECNICO': (tecnico or '').upper().split(' ')[0],
         'IDOLO': (idolo or '').upper(), 'ANO': '', 'COMP': '', 'N': '', 'FUND': '', 'RIVAL': '', 'CLASSICO': ''}
    if hoje:
        tit = [x for x in g.get('titulos', []) if 0 <= (hoje - s2d(x['data'])).days <= 30]
        if tit:
            v.update(ANO=str(s2d(tit[-1]['data']).year), COMP=COMP_NOMES.get(tit[-1]['comp'], '').upper())
            return {'modo': 'apoio', 'frases': TITULO, 'fracao': 1.0, 'vars': v, 'motivo': 'título recente'}
        an = rivais.aniversario(clube, hoje)
        if an:
            v.update(N=str(an[0]), FUND=str(an[1].year - an[0]))
            return {'modo': 'apoio', 'frases': ANIVERSARIO + APOIO[:3], 'fracao': 1.0, 'vars': v,
                    'motivo': f'aniversário de {an[0]} anos do clube'}
        cl = next((n for n in reversed(m.get('noticias', [])) if n.get('tipo') == 'classico_v'
                   and 0 <= (hoje - s2d(n['data'])).days <= 12), None)
        if cl and t >= 45:
            v.update(RIVAL=(cl.get('adv') or '').upper(), CLASSICO=(cl.get('classico') or 'CLÁSSICO').upper())
            return {'modo': 'apoio', 'frases': CLASSICO + APOIO[:4], 'fracao': 0.8, 'vars': v,
                    'motivo': 'vitória no clássico'}
    conf = m.get('diretoria', 60)
    ameacado = situacao(conf) == 'ameacado'
    if t >= 75:
        frases = APOIO + (['{IDOLO}, ÍDOLO!', 'É {IDOLO} QUE A GENTE QUER'] if idolo else [])
        return {'modo': 'apoio', 'frases': frases, 'fracao': round(min(1.0, 0.5 + (t - 75) / 30), 2), 'vars': v,
                'motivo': f'torcida em alta ({t}/100)'}
    if t <= 30 or (ameacado and t <= 45):
        frases = PROTESTO + (['FORA {TECNICO}!', '{TECNICO}, PEDE PRA SAIR'] if ameacado else [])
        return {'modo': 'protesto', 'frases': frases, 'fracao': round(min(1.0, 0.5 + (30 - min(t, 30)) / 30), 2),
                'vars': v, 'motivo': f'torcida revoltada ({t}/100)' + (' e técnico ameaçado' if ameacado else '')}
    return {'modo': None, 'frases': [], 'fracao': 0, 'vars': v, 'motivo': f'torcida neutra ({t}/100)'}


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
def instalar_modulo(pasta_jogo, backup_dir, log=print, nome=None, conteudo=None):
    """Grava o módulo Lua em modules e põe na lista do sider.ini antes dos servidores de estádio."""
    MODULO_, LUA_ = nome or MODULO, conteudo or LUA
    mod = os.path.join(pasta_jogo, 'modules', MODULO_)
    try:
        if not os.path.exists(mod) or open(mod, encoding='utf-8', errors='replace').read() != LUA_:
            open(mod, 'w', encoding='utf-8').write(LUA_)
    except OSError as e:
        log('não gravou o módulo do Sider:', e)
        return False
    ini = os.path.join(pasta_jogo, 'sider.ini')
    try:
        txt = open(ini, encoding='utf-8', errors='replace').read()
    except OSError:
        return False
    if MODULO_.lower() in txt.lower():
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
    linhas.insert(pos, f'lua.module = "{MODULO_}"{nl}')
    open(ini, 'w', encoding='utf-8').write(''.join(linhas))
    log(f'módulo {MODULO_} adicionado ao sider.ini')
    return True


def gerar(pasta_jogo, team_id, clube, cores, escudo, patro, plano, gram, log=print):
    """plano: resultado de plano_faixas; gram: (nivel, forca) de nivel_gramado."""
    """Monta as texturas do clube atual e o mapa.txt que o módulo do Sider lê. Devolve um resumo."""
    out = os.path.join(pasta_jogo, 'GOGOSZ', PASTA)
    os.makedirs(out, exist_ok=True)
    regras, resumo = [], {'estadio': None, 'faixas': None, 'gramado': None, 'bandeirinha': False}
    cor1 = cores[0] if cores else '#1f6b3a'
    cor2 = cores[1] if cores and len(cores) > 1 else '#ffffff'
    est = estadio_do_time(pasta_jogo, team_id)
    v = plano.get('vars') or {'CLUBE': (clube or '').upper()}
    nivel_gramado, forca = gram
    if est:
        resumo['estadio'] = est['nome']
        d, arqs = _texturas_estadio(est)
        st = 'st%03d' % est['id']
        # faixas da torcida: texturas de bandeira/faixa do próprio estádio
        modo = plano.get('modo')
        alvo = [a for a in arqs if a.lower().endswith('.ftex') and not re.search(r'_(nrm|srm|bsm|lym|lbm|alp)', a.lower())
                and re.match(r'(flag|novo banner|banner|faixa)', a.lower()) and _formato_ok(os.path.join(d, a))]
        if modo and alvo:
            frases = [f for f in plano['frases'] if not any('{%s}' % k in f and not v.get(k) for k in v)] or ['VAMOS {CLUBE}']
            r = random.Random(f'{team_id}{modo}{plano.get("motivo")}')
            # quanto mais forte o momento, mais faixas a torcida leva (o resto fica com as originais)
            r.shuffle(alvo)
            alvo = alvo[:max(1, int(round(len(alvo) * plano.get('fracao', 1))))]
            fila = []
            for i, a in enumerate(alvo):
                src = os.path.join(d, a)
                try:
                    from . import ftex
                    base = ftex.read(src)
                    if not fila:
                        fila = frases[:]
                        r.shuffle(fila)
                    t = fila.pop().format(**v).replace('  ', ' ').strip()
                    if '{' in t or not t.strip('! '):
                        t = 'VAMOS ' + v['CLUBE']
                    img = faixa(base.width, base.height, t, cor1, cor2, escudo, modo == 'protesto', i)
                    nome = f'faixa_{i}.ftex'
                    ftex.write(img, src, os.path.join(out, nome))
                    regras.append((f'{st}\\sourceimages\\tga\\#windx11\\{a}', nome, 'casa'))
                except Exception as e:
                    log('faixa não gerada', a, e)
            resumo['faixas'] = modo
            resumo['faixas_n'] = len(alvo)
        resumo['faixas_motivo'] = plano.get('motivo')
        # gramado
        if nivel_gramado in ('otimo', 'ruim'):
            for a in arqs:
                al = a.lower()
                if al in ('pitch_grain.ftex', 'pitch_alp.ftex') and _formato_ok(os.path.join(d, a)):
                    try:
                        from . import ftex
                        img = gramado(ftex.read(os.path.join(d, a)), nivel_gramado, team_id, al, forca)
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
