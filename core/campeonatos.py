"""Campeonatos da temporada, lidos do save: tabelas de cada competição, grupos, mata-mata, jogos já
disputados e os próximos jogos.

O save guarda todas as partidas da temporada (jogadas e a jogar) em registros de 0x254 bytes (ver sumulas.py).
O código do torneio tem duas partes: os 10 bits de baixo dizem a competição (17 = Brasileirão, 3 = fase de
grupos da Libertadores...) e o resto diz o grupo ou o confronto (1024 = grupo A, 2048 = grupo B...).
A tabela de cada liga é montada com os jogos já disputados; quando o jogo também guardou a classificação
(mesmos clubes, mesmo número de jogos), vale a ordem do jogo."""
import struct
from collections import defaultdict

from . import sumulas, savedata

NOMES = {17: 'Brasileirão Série A', 79: 'Brasileirão Série B', 81: 'Brasileirão Série C', 80: 'Brasileirão Série D',
         23: 'Copa do Brasil', 86: 'Supercopa do Brasil', 2: 'Libertadores · fase prévia', 3: 'Libertadores',
         4: 'Libertadores · mata-mata', 5: 'Sul-Americana', 6: 'Sul-Americana · mata-mata', 7: 'Recopa Sul-Americana',
         1: 'Intercontinental'}
# ordem de importância para o clube brasileiro
PESO = {17: 0, 3: 1, 4: 1, 2: 1, 23: 2, 5: 3, 6: 3, 7: 4, 86: 5, 1: 6, 79: 7, 81: 8, 80: 9}
PAISES = {'Brasil': 'Brasil', 'Argentina': 'Argentina', 'Colombia': 'Colômbia', 'Equador': 'Equador',
          'Ecuador': 'Equador', 'Peru': 'Peru', 'Bolivia': 'Bolívia', 'Uruguai': 'Uruguai', 'Uruguay': 'Uruguai',
          'Chile': 'Chile', 'Venezuela': 'Venezuela', 'Paraguai': 'Paraguai', 'Paraguay': 'Paraguai',
          'Franca': 'França', 'France': 'França'}
LETRAS = 'ABCDEFGHIJKLMNOP'


def partidas_todas(data: bytes):
    """Todas as partidas da temporada (jogadas e a jogar)."""
    out, vistos = [], set()
    for ini, n in sumulas.achar_tabelas(data, 1):
        for i in range(n):
            o = ini + i * sumulas.STRIDE
            if o in vistos:
                continue
            vistos.add(o)
            tor = struct.unpack_from('<H', data, o + 4)[0]
            ano, mes, dia = struct.unpack_from('<H', data, o + 8)[0], data[o + 0x0A], data[o + 0x0B]
            casa, fora = struct.unpack_from('<II', data, o + 0x14)
            jogada = bool(data[o + 7] & sumulas.JOGADA_BIT)
            out.append({'tor': tor, 'comp': tor & 1023, 'grupo': tor >> 10, 'data': f'{ano:04d}-{mes:02d}-{dia:02d}',
                        'm': casa >> 14, 'v': fora >> 14, 'gm': data[o + 0x1C] if jogada else None,
                        'gv': data[o + 0x1F] if jogada else None, 'jogada': jogada})
    out.sort(key=lambda p: (p['data'], p['tor']))
    return out


def _tabela(jogos, times):
    t = {i: {'id': i, 'pts': 0, 'j': 0, 'v': 0, 'e': 0, 'd': 0, 'gp': 0, 'gc': 0} for i in times}
    for p in jogos:
        if not p['jogada']:
            continue
        for eu, gp, gc in ((p['m'], p['gm'], p['gv']), (p['v'], p['gv'], p['gm'])):
            x = t.setdefault(eu, {'id': eu, 'pts': 0, 'j': 0, 'v': 0, 'e': 0, 'd': 0, 'gp': 0, 'gc': 0})
            x['j'] += 1; x['gp'] += gp; x['gc'] += gc
            if gp > gc:
                x['v'] += 1; x['pts'] += 3
            elif gp == gc:
                x['e'] += 1; x['pts'] += 1
            else:
                x['d'] += 1
    for x in t.values():
        x['sg'] = x['gp'] - x['gc']
    return list(t.values())


def _ordenar(linhas, ordem_jogo=None):
    if ordem_jogo:
        pos = {l['id']: l['pos'] for l in ordem_jogo}
        linhas.sort(key=lambda x: pos.get(x['id'], 999))
    else:
        linhas.sort(key=lambda x: (-x['pts'], -x['v'], -x['sg'], -x['gp']))
    for i, x in enumerate(linhas):
        x['pos'] = i + 1
    return linhas


def _pais(times, mapa):
    cont = defaultdict(int)
    for t in times:
        rel = (mapa or {}).get(t)
        if rel:
            cont[rel.split('\\')[0]] += 1
    if not cont:
        return None
    p = max(cont, key=cont.get)
    return PAISES.get(p, p) if cont[p] >= len(times) * 0.6 else None


def ler(data: bytes, team_id, nomes=None, mapa=None):
    """[{id, nome, tipo, pais, meu, tabelas: [{nome, linhas}], fases: [{nome, jogos}], jogos}] e os próximos jogos
    do clube."""
    nomes = nomes or {}
    nome = lambda i: nomes.get(i) or f'Time {i}'
    todas = partidas_todas(data)
    try:
        do_jogo = savedata.classificacoes(data)
    except Exception:
        do_jogo = []
    por_comp = defaultdict(list)
    for p in todas:
        por_comp[p['comp']].append(p)
    comps = []
    for cid, js in por_comp.items():
        if cid >= 1000:          # amistosos e jogos de seleção
            continue
        times = sorted({p['m'] for p in js} | {p['v'] for p in js})
        grupos = defaultdict(list)
        for p in js:
            grupos[p['grupo']].append(p)
        tabelas, fases = [], []
        n = len(times)
        if len(grupos) == 1 and 0 in grupos and n >= 6 and len(js) >= n * (n - 1) * 0.45:
            tipo = 'liga'
            linhas = _tabela(js, times)
            jmax = max((l['j'] for l in linhas), default=0)
            jogo = next((t for t in do_jogo if {l['id'] for l in t} == set(times) and max(l['j'] for l in t) == jmax), None)
            tabelas.append({'nome': '', 'linhas': _ordenar(linhas, jogo)})
        elif all(g > 0 for g in grupos) and all(len({p['m'] for p in g} | {p['v'] for p in g}) >= 3 for g in grupos.values()):
            tipo = 'grupos'
            for g in sorted(grupos):
                gj = grupos[g]
                gt = sorted({p['m'] for p in gj} | {p['v'] for p in gj})
                tabelas.append({'nome': f'Grupo {LETRAS[(g - 1) % len(LETRAS)]}', 'linhas': _ordenar(_tabela(gj, gt))})
        else:
            tipo = 'mata'
            # fases pela data: jogos com mais de 10 dias de distância começam outra fase
            atual, ult = [], None
            for p in sorted(js, key=lambda p: p['data']):
                if ult and (_dias(p['data']) - _dias(ult)) > 10 and atual:
                    fases.append(atual); atual = []
                atual.append(p); ult = p['data']
            if atual:
                fases.append(atual)
            fases = [{'nome': f'Fase {i + 1}', 'jogos': f} for i, f in enumerate(fases)]
            if fases:
                fases[-1]['nome'] = 'Final' if len(fases[-1]['jogos']) <= 2 and len(fases) > 1 else fases[-1]['nome']
        pais = 'Brasil' if cid in (17, 79, 80, 81, 23, 86) else _pais(times, mapa)
        if cid in NOMES:
            nm = NOMES[cid]
        else:
            nm = f"{'Liga' if tipo == 'liga' else 'Copa' if tipo == 'mata' and len(js) > 2 else 'Supercopa' if len(js) <= 2 else 'Torneio'}" \
                 f"{' — ' + pais if pais else f' {cid}'}"
        meu = team_id in times
        for t in tabelas:
            for l in t['linhas']:
                l['nome'] = nome(l['id'])
        comps.append({'id': cid, 'nome': nm, 'tipo': tipo, 'pais': pais or ('Internacional' if cid in (1, 2, 3, 4, 5, 6, 7) else ''),
                      'meu': meu, 'times': len(times), 'tabelas': tabelas,
                      'fases': [{'nome': f['nome'], 'jogos': [_jogo(p, nome) for p in f['jogos']]} for f in fases],
                      'jogos_total': len(js), 'jogados': sum(p['jogada'] for p in js),
                      'meus_jogos': [_jogo(p, nome) for p in js if team_id in (p['m'], p['v'])]})
    comps.sort(key=lambda c: (not c['meu'], PESO.get(c['id'], 50), c['pais'] != 'Brasil', c['pais'], c['nome']))
    meus = [p for p in todas if team_id in (p['m'], p['v'])]
    proximos = [dict(_jogo(p, nome), comp=NOMES.get(p['comp']) or next((c['nome'] for c in comps if c['id'] == p['comp']), ''))
                for p in meus if not p['jogada']][:12]
    return comps, proximos


def _dias(s):
    a, m, d = (int(x) for x in s.split('-'))
    import datetime as dt
    return dt.date(a, m, d).toordinal()


def _jogo(p, nome):
    return {'data': p['data'], 'm': p['m'], 'v': p['v'], 'mn': nome(p['m']), 'vn': nome(p['v']),
            'gm': p['gm'], 'gv': p['gv'], 'jogada': p['jogada']}
