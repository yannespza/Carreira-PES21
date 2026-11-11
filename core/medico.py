"""Departamento médico para o controle manual no jogo.

O jogo não sabe das lesões do app: você não escala quem está no DM e volta a escalar quando o app liberar.
- Lesões no treino (semanais, gestao.py) e lesões em jogo (a cada partida nova, aqui).
- Cada caso mostra a lesão, a gravidade, a fase da recuperação, a previsão de volta e o progresso.
- Mensagem do departamento médico quando o jogador se machuca e quando é liberado.
- Tratamento intensivo pago (uma vez por lesão): corta 30% do tempo que falta.
- Nível do departamento médico (estrutura): lesões mais curtas; quando a obra termina, quem está no DM
  também volta antes.
"""
import random, datetime as dt
from .sim import d2s, s2d, _seed, fmt_eur
from . import estrutura

# lesões em jogo: (nome, como aconteceu, dias mín, dias máx, peso)
LESOES_JOGO = [
    ('Contusão', 'levou uma pancada forte numa dividida', 2, 7, 26),
    ('Estiramento na coxa', 'sentiu a parte de trás da coxa num pique', 8, 21, 20),
    ('Entorse de tornozelo', 'torceu o tornozelo num lance de disputa', 6, 18, 16),
    ('Lesão na panturrilha', 'sentiu a panturrilha e pediu para sair', 10, 25, 12),
    ('Pubalgia', 'sentiu dores no púbis durante o jogo', 14, 35, 7),
    ('Lesão muscular grau 2', 'teve uma lesão muscular confirmada em exame', 21, 40, 8),
    ('Lesão no joelho (ligamento)', 'torceu o joelho e saiu de maca', 35, 90, 6),
    ('Fratura', 'sofreu uma fratura num choque', 45, 100, 3),
    ('Ruptura do ligamento cruzado', 'rompeu o ligamento cruzado do joelho', 150, 240, 2),
]
CHANCE_JOGO = 0.14


def gravidade(dias):
    return 'leve' if dias <= 10 else 'moderada' if dias <= 30 else 'grave'


def fase(prog, tipo):
    if tipo != 'lesao':
        return 'afastado'
    return 'tratamento' if prog < 40 else 'fisioterapia' if prog < 80 else 'transição (treino com bola)'


def _msg(engine, data, assunto, texto):
    if engine is None:
        return
    engine.s['mensagens'].append({'id': engine._id(), 'data': data, 'empresa': '__diretoria__',
                                  'de': 'Departamento médico', 'assunto': assunto, 'texto': texto,
                                  'tipo': 'medico', 'oferta_id': None, 'lida': False})


def lesao_em_jogo(gestao, partida, elenco, mundo, engine=None):
    """A cada partida nova, chance de um jogador do elenco sair machucado."""
    g = gestao.g
    if not elenco or any(e.get('partida') == partida['chave'] for e in g['eventos']):
        return None
    st = gestao.s
    r = random.Random(_seed('lesjogo', partida['chave']))
    if r.random() > CHANCE_JOGO * estrutura.risco_treino(st):
        return None
    dia = s2d(partida['data'])
    livres = [j for j in elenco if not gestao.afastado(j['id'], dia) and not j['nome'].startswith('Jogador ')]
    if not livres:
        return None
    j = r.choice(livres)
    nome, como, dmin, dmax, _ = r.choices(LESOES_JOGO, [x[4] for x in LESOES_JOGO])[0]
    dias = max(2, int(round(r.randint(dmin, dmax) * estrutura.duracao_lesao(st))))
    volta = dia + dt.timedelta(days=dias)
    ev = {'id': f"ev{len(g['eventos']) + 1}", 'data': partida['data'], 'jogador_id': j['id'], 'jogador': j['nome'],
          'tipo': 'lesao', 'origem': 'jogo', 'partida': partida['chave'], 'titulo': nome,
          'texto': f"{j['nome']} {como}. Volta prevista: {volta.strftime('%d/%m/%Y')}.",
          'volta': d2s(volta), 'dias': dias}
    g['eventos'].append(ev)
    g['eventos'] = g['eventos'][-60:]
    from .gestao import moral_ajuste
    moral_ajuste(st, j['nome'], -1, partida['data'], nome.lower(), dias)
    mundo.noticia('lesao', partida['data'], r, destaque=dias >= 20, jogador=j['nome'], n=dias)
    mundo.m['noticias'][-1].update(jogador=j['nome'], volta=ev['volta'])
    _msg(engine, partida['data'], f"{j['nome']}: {nome.lower()} ({gravidade(dias)})",
         f"{ev['texto']} Tempo estimado de recuperação: {dias} dia(s). Não escale o jogador até a liberação.")
    return ev


def processar(state, hoje, mundo, engine=None):
    """Avisa quem foi liberado e ajusta o DM quando o nível do departamento médico muda."""
    if not hoje:
        return
    g = state.setdefault('gestao', {})
    evs = g.get('eventos', [])
    # nível do departamento mudou: quem está no DM volta antes (ou depois)
    fat = estrutura.duracao_lesao(state)
    for e in evs:
        if e.get('tipo') != 'lesao' or s2d(e['volta']) <= hoje:
            continue
        f0 = e.setdefault('fator', fat)
        if f0 != fat:
            falta = (s2d(e['volta']) - hoje).days
            novo = max(1, int(round(falta * fat / f0)))
            e['volta'] = d2s(hoje + dt.timedelta(days=novo))
            e['fator'] = fat
            e.setdefault('historico', []).append({'data': d2s(hoje), 'texto': f'Departamento médico melhorou: volta antecipada para {s2d(e["volta"]).strftime("%d/%m/%Y")}'})
    for e in evs:
        if s2d(e['volta']) > hoje or e.get('avisado'):
            continue
        e['avisado'] = True
        if (hoje - s2d(e['volta'])).days > 21:     # casos antigos: só marca
            continue
        quem = e['jogador']
        if e.get('tipo') == 'lesao':
            if not e.get('voltou'):
                e['voltou'] = True
                mundo.noticia('retorno', e['volta'], random.Random(_seed('ret', e['id'])), jogador=quem)
                mundo.m['noticias'][-1]['jogador'] = quem
            _msg(engine, e['volta'], f'{quem} liberado', f'{quem} recebeu alta do departamento médico ({e["titulo"].lower()}) '
                 'e está liberado para jogar.')
        else:
            _msg(engine, e['volta'], f'{quem} de volta', f'{quem} cumpriu o afastamento ({e["titulo"].lower()}) e está à disposição.')


def custo_tratamento(e, hoje):
    falta = max(1, (s2d(e['volta']) - hoje).days)
    return int(round((25_000 + 3_000 * falta) / 1000) * 1000)


def tratar(state, eid, hoje):
    """Tratamento intensivo (fisioterapia extra, câmara hiperbárica): corta 30% do tempo que falta."""
    g = state.setdefault('gestao', {})
    e = next((x for x in g.get('eventos', []) if x['id'] == eid), None)
    if not e or e.get('tipo') != 'lesao' or s2d(e['volta']) <= hoje:
        raise ValueError('Esse jogador não está em tratamento.')
    if e.get('tratado'):
        raise ValueError('Esse jogador já recebeu o tratamento intensivo.')
    c = custo_tratamento(e, hoje)
    orc = (state.get('dinheiro') or {}).get('orc_transf')
    if orc is not None and orc < c:
        raise ValueError(f'O orçamento de transferências ({fmt_eur(orc)}) não cobre o tratamento ({fmt_eur(c)}).')
    falta = (s2d(e['volta']) - hoje).days
    novo = max(1, int(round(falta * 0.7)))
    e['volta'] = d2s(hoje + dt.timedelta(days=novo))
    e['tratado'] = True
    e.setdefault('historico', []).append({'data': d2s(hoje), 'texto': f'Tratamento intensivo: volta antecipada em {falta - novo} dia(s)'})
    state.setdefault('debitos', []).append({'id': f"deb{len(state.get('debitos', [])) + 1}", 'data': d2s(hoje),
                                            'valor': c, 'status': 'pendente',
                                            'motivo': f"Tratamento intensivo: {e['jogador']}"})
    return e


def view(state, hoje, elenco_ids=None):
    g = state.get('gestao') or {}
    ativos, liberados = [], []
    for e in g.get('eventos', []):
        if elenco_ids is not None and e.get('jogador_id') not in elenco_ids:
            continue
        ini, volta = s2d(e['data']), s2d(e['volta'])
        tot = max(1, (volta - ini).days)
        if hoje and ini <= hoje < volta:
            prog = int(round(100 * (hoje - ini).days / tot))
            ativos.append({**e, 'falta': (volta - hoje).days, 'total': tot, 'prog': prog,
                           'gravidade': gravidade(tot) if e['tipo'] == 'lesao' else e['tipo'],
                           'fase': fase(prog, e['tipo']),
                           'custo_trat': custo_tratamento(e, hoje) if e['tipo'] == 'lesao' and not e.get('tratado') else None})
        elif hoje and 0 <= (hoje - volta).days <= 14:
            liberados.append({**e, 'ha': (hoje - volta).days})
    ativos.sort(key=lambda x: x['volta'])
    liberados.sort(key=lambda x: x['volta'], reverse=True)
    return {'ativos': ativos, 'liberados': liberados, 'nivel': estrutura.nivel(state, 'medico'),
            'efeito': estrutura.DEPTOS['medico']['efeito'][estrutura.nivel(state, 'medico') - 1]}
