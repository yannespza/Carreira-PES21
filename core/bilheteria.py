"""Bilheteria e sócio-torcedor nos jogos em casa (efeito dentro do app).

O jogo continua pagando a bilheteria dele. O app soma ou desconta a diferença da faixa de preço escolhida em
relação à faixa Padrão (crédito ou débito no orçamento) e mexe no humor da torcida pelo resultado.
REGRA: na vitória o humor SEMPRE sobe (> 0), qualquer que seja o preço.
Sócios: a quantidade sobe com vitórias, clássicos vencidos e liderança, e cai com derrotas seguidas.
"""
import random

COTACAO = 4.3          # R$ por euro (cotação do jogo)
FAIXAS = {
    'popular': {'nome': 'Popular', 'preco': 35, 'ocup': (0.85, 1.00), 'humor': (4, 2, 0)},
    'padrao': {'nome': 'Padrão', 'preco': 65, 'ocup': (0.65, 0.85), 'humor': (3, 0, -2)},
    'grande': {'nome': 'Jogo grande', 'preco': 110, 'ocup': (0.50, 0.80), 'humor': (2, -2, -5)},
    'premium': {'nome': 'Premium / final', 'preco': 160, 'ocup': (0.35, 0.75), 'humor': (1, -4, -8)},
}
CAPACIDADE_PADRAO = 40_000


def _cfg(st):
    b = st.setdefault('bilheteria', {})
    b.setdefault('socios', 0)
    b.setdefault('escolhas', {})
    b.setdefault('jogos', [])
    b.setdefault('capacidade', CAPACIDADE_PADRAO)
    return b


CAPACIDADES = {'palmeiras': 43_713, 'corinthians': 47_605, 'sao paulo': 66_795, 'santos': 16_068, 'flamengo': 78_838,
               'fluminense': 78_838, 'vasco': 21_880, 'botafogo': 44_661, 'atletico mineiro': 46_000, 'cruzeiro': 61_846,
               'gremio': 55_662, 'internacional': 50_128, 'bahia': 47_907, 'fortaleza': 63_903, 'athletico': 42_372}


def definir_capacidade(st, clube_nome):
    from . import cidades
    n = cidades._norm(clube_nome)
    for k, v in CAPACIDADES.items():
        if k in n:
            _cfg(st)['capacidade'] = v
            return v
    return _cfg(st)['capacidade']


def iniciar_socios(st, rec_socios_euros):
    """Estimativa inicial de sócios pela receita de sócios do save (mensalidade média de R$ 60)."""
    b = _cfg(st)
    if not b['socios'] and rec_socios_euros:
        b['socios'] = int(max(5_000, min(180_000, rec_socios_euros * COTACAO / 12 / 60)))
    return b['socios']


def publico(st, faixa, crise, forma_boa):
    b = _cfg(st)
    lo, hi = FAIXAS[faixa]['ocup']
    o = (lo + hi) / 2 + (0.08 if forma_boa else 0)
    if crise and faixa in ('grande', 'premium'):
        o -= 0.25
    piso = min(0.70, b['socios'] / max(1, b['capacidade']))
    o = max(piso, min(1.0, o))
    return int(b['capacidade'] * o)


def processar(st, partidas, team_id, hoje_s, rivais_ids=()):
    """Jogos em casa já disputados que ainda não foram contabilizados. Devolve os lançamentos feitos."""
    b = _cfg(st)
    feitos = []
    vistos = {j['data'] for j in b['jogos']}
    meus = sorted([p for p in partidas if team_id in (p['mandante'], p['visitante'])], key=lambda p: p['data'])
    for i, p in enumerate(meus):
        if p['data'] in vistos or p['data'] < b.get('desde', hoje_s):
            continue
        casa = p['mandante'] == team_id
        gp, gc = (p['gols_mandante'], p['gols_visitante']) if casa else (p['gols_visitante'], p['gols_mandante'])
        res = 'V' if gp > gc else 'D' if gp < gc else 'E'
        antes = [x for x in meus[:i]][-3:]
        crise = len(antes) == 3 and all(
            ((x['gols_mandante'] < x['gols_visitante']) if x['mandante'] == team_id else
             (x['gols_visitante'] < x['gols_mandante'])) for x in antes)
        rival = (p['visitante'] if casa else p['mandante']) in set(rivais_ids or [])
        # sócios: todo jogo conta
        r = random.Random(f'socios|{p["data"]}')
        if res == 'V':
            b['socios'] = int(b['socios'] * (1 + (0.012 if rival else 0.005) + r.random() * 0.003))
        elif res == 'D':
            b['socios'] = int(b['socios'] * (1 - (0.010 if crise else 0.004)))
        reg = {'data': p['data'], 'casa': casa, 'resultado': res, 'placar': f'{gp} x {gc}'}
        if casa:
            fx = b['escolhas'].pop(p['data'], 'padrao')
            F = FAIXAS[fx]
            pub = publico(st, fx, crise, res == 'V')
            h = F['humor'][0 if res == 'V' else 1 if res == 'E' else 2]
            if res == 'V':
                h = max(1, h)            # regra: vitória sempre sobe o humor
            if res == 'D' and fx == 'popular' and gc - gp >= 3:
                h = -1
            # diferença para a faixa padrão: (preço x público) - (preço padrão x público padrão), em euros
            pub_pad = publico(st, 'padrao', crise, res == 'V')
            dif_rs = F['preco'] * pub - FAIXAS['padrao']['preco'] * pub_pad
            dif = int(round(dif_rs / COTACAO / 1000)) * 1000
            m = st.setdefault('mundo', {})
            m['torcida'] = int(max(0, min(100, m.get('torcida', 62) + h)))
            if dif:
                st.setdefault('debitos', []).append({'data': hoje_s, 'valor': -dif, 'status': 'pendente',
                                                     'motivo': f"bilheteria {F['nome'].lower()} ({p['data']})",
                                                     'origem': 'bilheteria'})
            reg.update(faixa=fx, publico=pub, humor=h, diferenca=dif, renda_rs=F['preco'] * pub)
            feitos.append(reg)
        b['jogos'].append(reg)
    b['jogos'] = b['jogos'][-60:]
    return feitos


def escolher(st, data, faixa):
    if faixa not in FAIXAS:
        raise ValueError('Faixa de preço inválida.')
    _cfg(st)['escolhas'][data] = faixa


def view(st, prox, team_id):
    b = _cfg(st)
    casa = bool(prox) and int(prox['m']) == int(team_id)
    sim = {}
    if casa:
        for k in FAIXAS:
            sim[k] = {'publico': publico(st, k, False, False), 'renda_rs': FAIXAS[k]['preco'] * publico(st, k, False, False)}
    return {'socios': b['socios'], 'capacidade': b['capacidade'], 'faixas': FAIXAS, 'simulacao': sim,
            'escolha': b['escolhas'].get(prox['data'], 'padrao') if casa else None, 'em_casa': casa,
            'jogos': [j for j in reversed(b['jogos']) if j.get('casa')][:10]}
