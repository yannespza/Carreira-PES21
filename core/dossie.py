"""Dossiê do próximo adversário: jogo aéreo, velocidade da defesa, batedores e a carta de plano tático.

O provável time titular do adversário são os 11 que mais jogaram nas últimas partidas dele (súmulas do save).
Atributos vêm da base de dados do patch (fichas do EDIT). A carta tática escolhida é conferida depois do
jogo: se o plano funcionou (vitória, ou empate fora contra time mais forte), o grupo ganha moral.
"""
CARTAS = {
    'craque': ('Marcação individual no craque', 'Um volante gruda no principal jogador deles.'),
    'aereo': ('Explorar a bola aérea', 'Cruzamentos e escanteios na área; levar os zagueiros altos na bola parada.'),
    'blitz': ('Blitz nos primeiros 15 minutos', 'Pressão alta e linhas adiantadas no começo do jogo.'),
    'bloco': ('Bloco baixo e contra-ataque', 'Defender perto da área e sair rápido em velocidade.'),
}


def _m(lst, k):
    v = [x[k] for x in lst if x.get(k) is not None]
    return round(sum(v) / len(v), 1) if v else None


def _perfil(pids, fichas):
    out = []
    for pid, nome in pids:
        f = fichas(pid) or {}
        a = f.get('atributos') or {}
        out.append({'id': pid, 'nome': nome, 'pos': f.get('posicao', ''), 'altura': f.get('altura'),
                    'cabeceio': a.get('Cabeceio'), 'impulsao': a.get('Impulsão'), 'vel': a.get('Velocidade'),
                    'acel': a.get('Aceleração'), 'curva': a.get('Curva'), 'colocado': a.get('Chute colocado'),
                    'passe_alto': a.get('Passe alto')})
    return out


def provaveis(partidas, team_id, ultimas=5):
    """[(pid, minutos)] dos 11 que mais jogaram nas últimas partidas do time."""
    jogos = [p for p in partidas if team_id in (p['mandante'], p['visitante'])][-ultimas:]
    mins = {}
    for p in jogos:
        lado = p['escalacao_mandante'] if p['mandante'] == team_id else p['escalacao_visitante']
        for x in lado:
            mins[x['id']] = mins.get(x['id'], 0) + x['min']
    return [pid for pid, _ in sorted(mins.items(), key=lambda t: -t[1])[:16]]


def montar(partidas, adv_id, adv_nome, meus_ids, nomes_jog, fichas):
    nm = lambda i: (nomes_jog.get(i) or {}).get('nome') or f'Jogador {i}'
    def onze(lst):
        out, go = [], False
        for x in lst:
            if x['pos'] == 'GO':
                if go:
                    continue
                go = True
            out.append(x)
        return out[:11]
    deles = onze(_perfil([(i, nm(i)) for i in provaveis(partidas, adv_id)], fichas))
    nossos = onze(_perfil([(i, nm(i)) for i in (meus_ids or [])], fichas))
    if not deles:
        return None
    ar_d = {k: _m(deles, k) for k in ('altura', 'cabeceio', 'impulsao')}
    ar_n = {k: _m(nossos, k) for k in ('altura', 'cabeceio', 'impulsao')}
    defs = [x for x in deles if x['pos'] in ('ZC', 'LE', 'LD')]
    vel = _m(defs, 'vel'), _m(defs, 'acel')
    alertas, sugestao = [], []
    if ar_d['cabeceio'] and ar_n['cabeceio']:
        dif = ar_n['cabeceio'] - ar_d['cabeceio']
        if dif >= 4:
            alertas.append(f"Eles perdem no alto: cabeceio médio {ar_d['cabeceio']} contra {ar_n['cabeceio']} nosso.")
            sugestao.append('aereo')
        elif dif <= -4:
            alertas.append(f"Perigo na bola parada defensiva: cabeceio médio deles {ar_d['cabeceio']} contra {ar_n['cabeceio']}.")
    if vel[0]:
        if vel[0] < 70:
            alertas.append(f'Defesa lenta (velocidade média {vel[0]}): bola nas costas e contra-ataque.')
            sugestao.append('bloco')
        elif vel[0] >= 78:
            alertas.append(f'Defesa rápida (velocidade média {vel[0]}): melhor posse paciente que lançamento.')
    altos = sorted([x for x in deles if x['cabeceio']], key=lambda x: -x['cabeceio'])[:2]
    bat = sorted([x for x in deles if x['curva'] and x['colocado']],
                 key=lambda x: -(x['curva'] + x['colocado'] + (x['passe_alto'] or 0)))[:3]
    craque = max(deles, key=lambda x: (x['curva'] or 0) + (x['colocado'] or 0) + (x['vel'] or 0), default=None)
    return {'adv_id': adv_id, 'adv': adv_nome, 'titulares': deles, 'aereo_deles': ar_d, 'aereo_nosso': ar_n,
            'vel_defesa': vel[0], 'acel_defesa': vel[1], 'alertas': alertas,
            'batedores': [{'id': x['id'], 'nome': x['nome'], 'curva': x['curva'], 'colocado': x['colocado']} for x in bat],
            'cabeceadores': [{'id': x['id'], 'nome': x['nome'], 'cabeceio': x['cabeceio'], 'altura': x['altura']} for x in altos],
            'craque': craque and {'id': craque['id'], 'nome': craque['nome']},
            'sugestao': sugestao[:2] or ['blitz'],
            'cartas': {k: {'nome': v[0], 'texto': v[1]} for k, v in CARTAS.items()}}


def conferir_cartas(st, partidas, team_id):
    """Depois do jogo: plano cumprido (vitória) dá moral ao grupo. Devolve os resultados conferidos agora."""
    D = st.setdefault('dossie', {})
    feitos = []
    for c in D.get('cartas_escolhidas', []):
        if c.get('resultado'):
            continue
        p = next((p for p in partidas if p['data'] == c['data'] and team_id in (p['mandante'], p['visitante'])), None)
        if not p:
            continue
        casa = p['mandante'] == team_id
        gp, gc = (p['gols_mandante'], p['gols_visitante']) if casa else (p['gols_visitante'], p['gols_mandante'])
        ok = gp > gc or (c['carta'] == 'bloco' and gp == gc and not casa)
        c['resultado'] = 'funcionou' if ok else 'não funcionou'
        c['placar'] = f'{gp} x {gc}'
        feitos.append(c)
    return feitos
