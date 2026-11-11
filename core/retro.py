"""Retrospectiva das temporadas: números, maiores vitórias, sequências, clássicos, títulos e a manchete do ano.
Também monta a capa de jornal da temporada (imagem para guardar ou compartilhar)."""
import io
from PIL import Image, ImageDraw, ImageFilter
from .sim import COMP_NOMES
from .diretoria import temporada
from .sim import s2d


def _gols(p, tid):
    casa = p['mandante'] == tid
    return (p['gm'], p['gv']) if casa else (p['gv'], p['gm'])


def resumo(state, tid, nomes, rivais=()):
    def nm(i):
        n = (nomes or {}).get(i, f'Time {i}')
        return n.title() if n.isupper() else n
    por = {}
    for p in sorted(state.get('partidas', []), key=lambda p: p['data']):
        por.setdefault(temporada(s2d(p['data'])), []).append(p)
    g = state.get('gestao') or {}
    temps = {t['ano']: t for t in g.get('temporadas', [])}
    tits = g.get('titulos', [])
    noticias = (state.get('mundo') or {}).get('noticias', [])
    hist = (state.get('mundo') or {}).get('historico', [])
    out = []
    for ano in sorted(set(por) | set(temps), reverse=True):
        ps = por.get(ano, [])
        s = {'ano': ano, 'jogos': len(ps), 'V': 0, 'E': 0, 'D': 0, 'gp': 0, 'gc': 0}
        mv = pd = None
        seqv = seqi = curv = curi = 0
        cl = {'V': 0, 'E': 0, 'D': 0}
        for p in ps:
            gp, gc = _gols(p, tid)
            s[p['res']] += 1; s['gp'] += gp; s['gc'] += gc
            adv = p['visitante'] if p['mandante'] == tid else p['mandante']
            item = {'data': p['data'], 'gp': gp, 'gc': gc, 'adv': nm(adv), 'casa': p['mandante'] == tid}
            if gp > gc and (not mv or gp - gc > mv['gp'] - mv['gc'] or (gp - gc == mv['gp'] - mv['gc'] and gp > mv['gp'])):
                mv = item
            if gc > gp and (not pd or gc - gp > pd['gc'] - pd['gp']):
                pd = item
            curv = curv + 1 if p['res'] == 'V' else 0
            curi = curi + 1 if p['res'] != 'D' else 0
            seqv, seqi = max(seqv, curv), max(seqi, curi)
            if adv in rivais:
                cl[p['res']] += 1
        s['aproveitamento'] = round(100 * (3 * s['V'] + s['E']) / (3 * len(ps))) if ps else None
        s.update(maior_vitoria=mv, pior_derrota=pd, seq_vitorias=seqv, invencibilidade=seqi,
                 classicos=cl if sum(cl.values()) else None)
        t = temps.get(ano) or {}
        s.update(pos=t.get('pos'), n=t.get('n'), divisao=t.get('divisao'), acesso=t.get('acesso'),
                 rebaixado=t.get('rebaixado'), meta_cumprida=t.get('meta_cumprida'))
        s['titulos'] = [COMP_NOMES.get(x['comp'], x['comp']) for x in tits if temporada(s2d(x['data'])) == ano]
        ns = [n for n in noticias if n.get('data') and temporada(s2d(n['data'])) == ano]
        dest = [n for n in ns if n.get('destaque')]
        prio = ('lider', 'sobe', 'cai', 'classico_v', 'goleada', 'seq_vitorias', 'vexame')
        dest.sort(key=lambda n: (n.get('tipo') in prio[:3], n.get('tipo') in prio, n.get('data')), reverse=True)
        s['manchete'] = (dest or ns or [{}])[0].get('titulo')
        hs = [h for h in hist if temporada(s2d(h[0])) == ano]
        s['torcida'] = [hs[0][1], hs[-1][1]] if hs else None
        cs = [c for c in state.get('contratos', []) if temporada(s2d(c['inicio'])) == ano]
        s['patrocinios'] = {'novos': len(cs), 'valor': sum(c['valor'] for c in cs)}
        out.append(s)
    return out


def _fonte(t):
    from .cena import _fonte as f
    return f(t)


def _rgb(h):
    h = (h or '#1f6b3a').lstrip('#')
    return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))


def capa(s, clube, escudo, cores, tecnico):
    """Capa de jornal da temporada (1080 x 1350, para guardar ou postar)."""
    W, H = 1080, 1350
    c1 = _rgb((cores or ['#1f6b3a'])[0])
    papel = (244, 240, 230)
    img = Image.new('RGB', (W, H), papel)
    d = ImageDraw.Draw(img)
    # cabeçalho do jornal
    d.rectangle([0, 0, W, 150], fill=(20, 20, 22))
    d.text((48, 32), 'DIÁRIO DA CARREIRA', font=_fonte(64), fill=(255, 255, 255))
    d.text((52, 106), f'EDIÇÃO ESPECIAL · TEMPORADA {s["ano"]}/{str(s["ano"] + 1)[-2:]}', font=_fonte(26), fill=(200, 200, 200))
    d.rectangle([0, 150, W, 162], fill=c1)
    # manchete
    if s['titulos']:
        tit = f'{clube.upper()} CAMPEÃO!'
        sub = ' · '.join(s['titulos'])
    elif s.get('acesso'):
        tit, sub = 'ACESSO CONQUISTADO!', f'{clube} volta à elite'
    elif s.get('rebaixado'):
        tit, sub = 'QUEDA', f'{clube} é rebaixado'
    elif s.get('pos'):
        tit, sub = f'{clube.upper()} TERMINA EM {s["pos"]}º', 'Campanha da temporada'
    else:
        tit, sub = f'A TEMPORADA DO {clube.upper()}', 'Em andamento'
    tam = 96
    f = _fonte(tam)
    while d.textlength(tit, font=f) > W - 96 and tam > 40:
        tam -= 4; f = _fonte(tam)
    d.text((48, 196), tit, font=f, fill=(15, 15, 15))
    d.text((52, 196 + tam + 16), sub, font=_fonte(36), fill=c1)
    y = 196 + tam + 80
    # escudo grande com halo
    if escudo is not None:
        e = escudo.convert('RGBA').copy()
        k = 300 / max(e.width, e.height)
        e = e.resize((max(1, int(e.width * k)), max(1, int(e.height * k))), Image.LANCZOS)
        halo = Image.new('RGBA', (W, H), (0, 0, 0, 0))
        hd = ImageDraw.Draw(halo)
        cx, cy = W - 250, y + 210
        hd.ellipse([cx - 230, cy - 230, cx + 230, cy + 230], fill=c1 + (60,))
        halo = halo.filter(ImageFilter.GaussianBlur(30))
        img.paste(halo, (0, 0), halo)
        img.paste(e, (cx - e.width // 2, cy - e.height // 2), e)
    # números
    linhas = [('JOGOS', s['jogos']), ('VITÓRIAS', s['V']), ('EMPATES', s['E']), ('DERROTAS', s['D']),
              ('GOLS PRÓ', s['gp']), ('GOLS CONTRA', s['gc']),
              ('APROVEITAMENTO', f"{s['aproveitamento']}%" if s['aproveitamento'] is not None else '—')]
    for i, (k, v) in enumerate(linhas):
        yy = y + i * 62
        d.text((52, yy), k, font=_fonte(26), fill=(90, 90, 90))
        d.text((380, yy - 8), str(v), font=_fonte(44), fill=(15, 15, 15))
    y += len(linhas) * 62 + 30
    d.line([48, y, W - 48, y], fill=(30, 30, 30), width=3)
    y += 24
    dest = []
    if s.get('maior_vitoria'):
        m = s['maior_vitoria']; dest.append(f"Maior vitória: {m['gp']} x {m['gc']} no {m['adv']}")
    if s.get('pior_derrota'):
        m = s['pior_derrota']; dest.append(f"Pior derrota: {m['gp']} x {m['gc']} para o {m['adv']}")
    if s.get('seq_vitorias'):
        dest.append(f"Maior sequência de vitórias: {s['seq_vitorias']} jogo" + ('s' if s['seq_vitorias'] > 1 else ''))
    if s.get('invencibilidade'):
        dest.append(f"Maior invencibilidade: {s['invencibilidade']} jogo" + ('s' if s['invencibilidade'] > 1 else ''))
    if s.get('classicos'):
        c = s['classicos']; dest.append(f"Clássicos: {c['V']} vitórias, {c['E']} empates, {c['D']} derrotas")
    for t in dest[:5]:
        d.text((52, y), '• ' + t, font=_fonte(30), fill=(25, 25, 25))
        y += 48
    if s.get('manchete'):
        y += 14
        d.rectangle([48, y, W - 48, y + 110], fill=(20, 20, 22))
        txt = '“' + s['manchete'] + '”'
        tam = 30; f = _fonte(tam)
        while d.textlength(txt, font=f) > W - 140 and tam > 16:
            tam -= 2; f = _fonte(tam)
        d.text((70, y + 20), 'A MANCHETE DO ANO', font=_fonte(20), fill=(170, 170, 170))
        d.text((70, y + 52), txt, font=f, fill=(255, 255, 255))
    d.rectangle([0, H - 70, W, H], fill=c1)
    d.text((48, H - 52), f'Técnico: {tecnico}', font=_fonte(28), fill=(255, 255, 255))
    b = io.BytesIO()
    img.save(b, 'PNG', optimize=True)
    return b.getvalue()
