"""Museu do clube: histórico permanente da sua gestão (não some na virada de temporada do PES).

O jogo apaga as súmulas quando a temporada vira; o app guarda cada partida do clube em state['museu'] na
primeira vez que a vê. Daí saem almanaque, recordes, histórico contra cada rival, hall da fama e os
"carrascos" (rivais com 3 ou mais gols contra o clube).
"""
import collections


def registrar(st, partidas, team_id, nomes_jog, nomes_clubes):
    M = st.setdefault('museu', {'jogos': {}, 'aposentadas': []})
    M.setdefault('jogos', {})
    M.setdefault('aposentadas', [])
    nm = lambda i: (nomes_jog.get(i) or {}).get('nome') or f'Jogador {i}'
    novos = 0
    for p in partidas:
        if team_id not in (p['mandante'], p['visitante']):
            continue
        k = f"{p['data']}|{p['mandante']}|{p['visitante']}|{p['torneio']}"
        if k in M['jogos']:
            continue
        casa = p['mandante'] == team_id
        nos = p['escalacao_mandante'] if casa else p['escalacao_visitante']
        eles = p['escalacao_visitante'] if casa else p['escalacao_mandante']
        adv = p['visitante'] if casa else p['mandante']
        M['jogos'][k] = {
            'data': p['data'], 'torneio': p['torneio'] & 1023, 'casa': casa, 'adv': adv,
            'adv_nome': nomes_clubes.get(adv, f'Time {adv}'),
            'gp': p['gols_mandante'] if casa else p['gols_visitante'], 'gc': p['gols_visitante'] if casa else p['gols_mandante'],
            'nos': [[x['id'], nm(x['id']), x['gols'], x['assist'], x['min']] for x in nos if x['min']],
            'eles': [[x['id'], nm(x['id']), x['gols']] for x in eles if x['gols']],
        }
        novos += 1
    return novos


def _temporada(data):
    a, m = int(data[:4]), int(data[5:7])
    return a if m >= 2 else a - 1          # temporada brasileira: fevereiro a dezembro/janeiro


def view(st, prox_adv=None, nomes_atuais=None):
    M = st.get('museu') or {}
    J = sorted((M.get('jogos') or {}).values(), key=lambda j: j['data'])
    if not J:
        return {'vazio': True, 'aposentadas': M.get('aposentadas', [])}
    jog = collections.defaultdict(lambda: {'jogos': 0, 'gols': 0, 'assist': 0, 'nome': ''})
    for j in J:
        for pid, nome, g, a, mi in j['nos']:
            r = jog[pid]; r['jogos'] += 1; r['gols'] += g; r['assist'] += a; r['nome'] = nome; r['id'] = pid
    lista = list(jog.values())
    art = sorted(lista, key=lambda r: (-r['gols'], -r['jogos']))[:10]
    garc = sorted(lista, key=lambda r: (-r['assist'], -r['jogos']))[:10]
    jogos = sorted(lista, key=lambda r: -r['jogos'])[:10]
    res = lambda j: 'V' if j['gp'] > j['gc'] else 'D' if j['gp'] < j['gc'] else 'E'
    maior_v = max(J, key=lambda j: (j['gp'] - j['gc'], j['gp']))
    maior_d = max(J, key=lambda j: (j['gc'] - j['gp'], j['gc']))
    inv = best = 0
    ini = best_ini = best_fim = None
    for j in J:
        if res(j) != 'D':
            inv += 1
            ini = ini or j['data']
            if inv > best:
                best, best_ini, best_fim = inv, ini, j['data']
        else:
            inv, ini = 0, None
    temps = collections.defaultdict(lambda: {'j': 0, 'v': 0, 'e': 0, 'd': 0, 'gp': 0, 'gc': 0})
    for j in J:
        t = temps[_temporada(j['data'])]
        t['j'] += 1
        t['v' if res(j) == 'V' else 'e' if res(j) == 'E' else 'd'] += 1
        t['gp'] += j['gp']; t['gc'] += j['gc']
    for k, t in temps.items():
        t['aprov'] = round(100 * (3 * t['v'] + t['e']) / (3 * t['j'])) if t['j'] else 0
        t['temporada'] = k
    vs = collections.defaultdict(lambda: {'j': 0, 'v': 0, 'e': 0, 'd': 0, 'gp': 0, 'gc': 0, 'nome': ''})
    carr = collections.defaultdict(lambda: {'gols': 0, 'jogos': set()})
    for j in J:
        r = vs[j['adv']]; r['j'] += 1; r['nome'] = j['adv_nome']; r['id'] = j['adv']
        r['v' if res(j) == 'V' else 'e' if res(j) == 'E' else 'd'] += 1
        r['gp'] += j['gp']; r['gc'] += j['gc']
        for pid, nome, g in j['eles']:
            c = carr[pid]; c['gols'] += g; c['nome'] = nome; c['id'] = pid; c['jogos'].add(j['data'])
    carrascos = sorted(({'id': c['id'], 'nome': c['nome'], 'gols': c['gols'], 'jogos': len(c['jogos'])}
                        for c in carr.values() if c['gols'] >= 3), key=lambda c: -c['gols'])
    hall = [r for r in lista if r['jogos'] >= 150 or r['gols'] >= 100]
    quase = sorted([r for r in lista if r not in hall], key=lambda r: -(r['jogos'] / 150 + r['gols'] / 100))[:6]
    alerta = []
    if prox_adv and nomes_atuais is not None:
        ids_adv = set(nomes_atuais)
        alerta = [c for c in carrascos if c['id'] in ids_adv]
    return {'jogos_total': len(J), 'desde': J[0]['data'], 'artilheiros': art, 'garcons': garc, 'mais_jogos': jogos,
            'maior_vitoria': maior_v, 'maior_derrota': maior_d if maior_d['gc'] > maior_d['gp'] else None,
            'invencibilidade': {'jogos': best, 'de': best_ini, 'ate': best_fim},
            'temporadas': sorted(temps.values(), key=lambda t: t['temporada']),
            'rivais': sorted(vs.values(), key=lambda r: -r['j'])[:20], 'carrascos': carrascos[:15],
            'hall': hall, 'quase': quase, 'aposentadas': M.get('aposentadas', []), 'carrascos_prox': alerta}


def aposentar(st, numero, nome):
    M = st.setdefault('museu', {'jogos': {}, 'aposentadas': []})
    ap = M.setdefault('aposentadas', [])
    if any(a['numero'] == numero for a in ap):
        raise ValueError('Esse número já está aposentado.')
    ap.append({'numero': int(numero), 'nome': nome, 'data': st.get('data')})


def analise(partidas, team_id, elenco):
    """Depois do jogo: quem está sem jogar, seca de gols dos atacantes e série sem sofrer gols."""
    jogos = sorted([p for p in partidas if team_id in (p['mandante'], p['visitante'])], key=lambda p: p['data'])
    lado = lambda p: p['escalacao_mandante'] if p['mandante'] == team_id else p['escalacao_visitante']
    sem_jogar, seca = [], []
    for j in elenco:
        ult = [next((x for x in lado(p) if x['id'] == j['id']), None) for p in jogos[-4:]]
        if len(jogos) >= 3 and all(not x or not x['min'] for x in ult[-3:]) and (j.get('cgj') or 0) >= 72:
            n = sum(1 for x in reversed(ult) if not x or not x['min'])
            sem_jogar.append({'id': j['id'], 'nome': j['nome'], 'pos': j.get('pos', ''), 'jogos': n})
        if j.get('pos') in ('ATA', 'PE', 'PD', 'SA', 'CA'):
            jogou = [x for p in jogos for x in lado(p) if x['id'] == j['id'] and x['min']]
            ult5 = jogou[-5:]
            if len(ult5) >= 4 and not any(x['gols'] for x in ult5):
                seca.append({'id': j['id'], 'nome': j['nome'], 'jogos': len(ult5)})
    serie = 0
    for p in reversed(jogos):
        gc = p['gols_visitante'] if p['mandante'] == team_id else p['gols_mandante']
        if gc:
            break
        serie += 1
    return {'sem_jogar': sem_jogar, 'seca': seca, 'sem_sofrer': serie}
