"""Prêmios do campeonato montados pelas súmulas de TODOS os clubes: craque da rodada, artilharia, assistências,
seleção do campeonato (4-3-3) e revelação (até 21 anos).

Rodada = jogos da liga agrupados pela semana. Quando um jogador do seu clube é craque da rodada, a imprensa noticia
com os números e a torcida comenta; quem perde espaço na seleção não gera nada."""
import datetime as dt

LIGAS = {17: 'Série A', 79: 'Série B', 81: 'Série C', 80: 'Série D'}
VAGAS = [('GL', 1), ('LD', 1), ('ZAG', 2), ('LE', 1), ('VOL', 1), ('MEI', 2), ('PD', 1), ('ATA', 1), ('PE', 1)]
ALTERNATIVAS = {'MEI': ['MD', 'ME', 'VOL'], 'PD': ['MD', 'ATA'], 'PE': ['ME', 'ATA'], 'VOL': ['MEI'], 'LD': ['MD'],
                'LE': ['ME'], 'ATA': ['PD', 'PE'], 'ZAG': [], 'GL': []}


def _semana(data):
    d = dt.date.fromisoformat(data)
    a, s, _ = d.isocalendar()
    return f'{a}-S{s:02d}'


def calcular(partidas, team_id, nomes, clubes, idades=None, liga=None):
    """partidas: sumulas.partidas(save). nomes: {id: {nome, pos}}. clubes: {time_id: nome}.
    liga: código do torneio (10 bits de baixo); padrão = a liga em que o clube joga."""
    idades = idades or {}
    meus = [p for p in partidas if team_id in (p['mandante'], p['visitante'])]
    if liga is None:
        cont = {}
        for p in meus:
            c = p['torneio'] & 1023
            if c in LIGAS:
                cont[c] = cont.get(c, 0) + 1
        liga = max(cont, key=cont.get) if cont else 17
    jogos = [p for p in partidas if p['torneio'] & 1023 == liga]
    tab = {}
    rodadas = {}
    for p in jogos:
        sem = _semana(p['data'])
        for lado, tid in (('escalacao_mandante', p['mandante']), ('escalacao_visitante', p['visitante'])):
            for x in p[lado]:
                if not x['min']:
                    continue
                s = tab.setdefault(x['id'], {'id': x['id'], 'time_id': tid, 'jogos': 0, 'gols': 0, 'assist': 0,
                                             'notas': [], 'min': 0, 'craque': 0})
                s['time_id'] = tid
                s['jogos'] += 1
                s['gols'] += x['gols']
                s['assist'] += x['assist']
                s['min'] += x['min']
                if x['nota'] is not None:
                    s['notas'].append(x['nota'])
                    r = rodadas.setdefault(sem, {'data': p['data'], 'melhor': None})
                    r['data'] = max(r['data'], p['data'])
                    chave = (x['nota'], x['gols'] + x['assist'], x['min'])
                    if r['melhor'] is None or chave > r['melhor'][0]:
                        r['melhor'] = (chave, x['id'], tid, x['nota'], x['gols'], x['assist'])

    def info(pid, s=None):
        n = nomes.get(pid) or {}
        s = s or tab.get(pid) or {}
        tid = s.get('time_id')
        notas = s.get('notas') or []
        return {'id': pid, 'nome': n.get('nome') or f'Jogador {pid}', 'pos': n.get('pos') or '', 'time_id': tid,
                'clube': clubes.get(tid, f'Time {tid}'), 'meu': tid == team_id, 'jogos': s.get('jogos', 0),
                'gols': s.get('gols', 0), 'assist': s.get('assist', 0),
                'nota': round(sum(notas) / len(notas), 2) if notas else None, 'idade': idades.get(pid)}

    craques = []
    for sem in sorted(rodadas):
        m = rodadas[sem]['melhor']
        if not m:
            continue
        _, pid, tid, nota, g, a = m
        tab[pid]['craque'] += 1
        craques.append({**info(pid), 'rodada': len(craques) + 1, 'data': rodadas[sem]['data'],
                        'nota_jogo': nota, 'gols_jogo': g, 'assist_jogo': a})
    lista = list(tab.values())
    maxj = max((s['jogos'] for s in lista), default=0)
    minj = max(1, maxj // 2)
    art = sorted((s for s in lista if s['gols']), key=lambda s: (-s['gols'], s['jogos']))[:10]
    ass = sorted((s for s in lista if s['assist']), key=lambda s: (-s['assist'], s['jogos']))[:10]
    elegiveis = [s for s in lista if s['jogos'] >= minj and s['notas']]
    media = lambda s: sum(s['notas']) / len(s['notas'])
    usados, selecao = set(), []
    for pos, n in VAGAS:
        cand = [s for s in elegiveis if s['id'] not in usados and (nomes.get(s['id']) or {}).get('pos') == pos]
        if len(cand) < n:
            cand += [s for s in elegiveis if s['id'] not in usados and (nomes.get(s['id']) or {}).get('pos') in ALTERNATIVAS[pos]]
        for s in sorted(cand, key=lambda s: -(media(s) + s['gols'] * 0.02 + s['assist'] * 0.015))[:n]:
            usados.add(s['id'])
            selecao.append({**info(s['id'], s), 'vaga': pos})
    rev = [s for s in elegiveis if idades.get(s['id']) and idades[s['id']] <= 21]
    revelacao = info(max(rev, key=media)['id']) if rev else None
    craque_temp = max(elegiveis, key=lambda s: media(s) + s['craque'] * 0.08 + s['gols'] * 0.02) if elegiveis else None
    return {'liga': LIGAS.get(liga, 'Liga'), 'rodadas': len(craques), 'craques': craques[::-1][:12],
            'artilharia': [info(s['id'], s) for s in art], 'assistencias': [info(s['id'], s) for s in ass],
            'selecao': selecao, 'revelacao': revelacao,
            'craque_temporada': info(craque_temp['id'], craque_temp) if craque_temp else None,
            'meus_na_selecao': sum(1 for s in selecao if s['meu'])}


def noticiar(state, premios, clube, mundo_add):
    """Craque da rodada do seu clube vira notícia (uma vez por rodada). mundo_add(dict) publica."""
    vis = state.setdefault('premios_vistos', [])
    novos = []
    for c in premios.get('craques', []):
        chave = f"{c['data']}|{c['id']}"
        if c['meu'] and chave not in vis:
            vis.append(chave)
            feito = ', '.join(x for x in [f"{c['gols_jogo']} gol{'s' if c['gols_jogo'] != 1 else ''}" if c['gols_jogo'] else '',
                                          f"{c['assist_jogo']} assistência{'s' if c['assist_jogo'] != 1 else ''}" if c['assist_jogo'] else ''] if x)
            nota = f"{c['nota_jogo']:.1f}".replace('.', ',')
            mundo_add({'data': c['data'], 'tipo': 'jog_elogio', 'destaque': True, 'fonte': 'Lance!', 'jogador': c['nome'],
                       'titulo': f"{c['nome']}, do {clube}, é o craque da rodada da {premios['liga']}: nota {nota}"
                                 + (f' e {feito}' if feito else '')})
            novos.append(c)
    state['premios_vistos'] = vis[-200:]
    return novos
