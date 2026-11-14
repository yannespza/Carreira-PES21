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
    energia_lesionados(state, hoje)
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
            retorno_sem_ritmo(state, e)
            if not e.get('voltou'):
                e['voltou'] = True
                mundo.noticia('retorno', e['volta'], random.Random(_seed('ret', e['id'])), jogador=quem)
                mundo.m['noticias'][-1]['jogador'] = quem
            _msg(engine, e['volta'], f'{quem} liberado', f'{quem} recebeu alta do departamento médico ({e["titulo"].lower()}) '
                 'e está liberado para jogar.')
        else:
            _msg(engine, e['volta'], f'{quem} de volta', f'{quem} cumpriu o afastamento ({e["titulo"].lower()}) e está à disposição.')


def energia_retorno(dias):
    """Energia (0..100%) de quem volta de lesão: sem ritmo de jogo nem de treino. Quanto mais tempo parado, menos.
    3 dias = 70%, 1 semana = 55%, 2 semanas = 43%, 1 mês = 30%, 2 meses = 18%, 3 meses = 11%, 6 meses = 8%."""
    import math
    if dias < 3:
        return None
    return int(max(8, min(70, round(70 - 12 * math.log2(dias / 3)))))


def retorno_sem_ritmo(state, e):
    """Marca a energia baixa para gravar no save quando o jogador recebe alta."""
    if not GRAVAR_ENERGIA or e.get('energia_retorno') is not None or not e.get('jogador_id'):
        return
    dias = (s2d(e['volta']) - s2d(e['data'])).days
    pct = energia_retorno(dias)
    if pct is None:
        return
    e['energia_retorno'] = pct
    state.setdefault('energia_set', {})[str(e['jogador_id'])] = int(round(pct * 255 / 100))
    e.setdefault('historico', []).append({'data': e['volta'], 'texto': f'Volta sem ritmo: energia em {pct}% '
                                          f'depois de {dias} dias parado'})


def energia_lesionados(state, hoje, energia=None):
    """Quem está no DM com lesão fica com a energia baixa no save (o jogo não sabe da lesão). Valor pelo tempo
    total de afastamento. Devolve True se marcou alguém novo para gravar."""
    if not hoje or not GRAVAR_ENERGIA:
        return False
    novo = False
    for e in (state.get('gestao') or {}).get('eventos', []):
        if e.get('tipo') != 'lesao' or not e.get('jogador_id'):
            continue
        if not s2d(e['data']) <= hoje < s2d(e['volta']):
            continue
        dias = (s2d(e['volta']) - s2d(e['data'])).days
        pct = energia_retorno(max(3, dias))
        # já gravado: só grava de novo se o jogo devolveu a energia (ex.: depois de um jogo sem ele)
        atual = (energia or {}).get(e['jogador_id'])
        if e.get('energia_baixa') is not None and (atual is None or atual <= round(pct * 255 / 100)):
            continue
        e['energia_baixa'] = pct
        state.setdefault('energia_set', {})[str(e['jogador_id'])] = int(round(pct * 255 / 100))
        novo = True
    return novo


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


# ---------------- energia (cansaço) e programa de recuperação ----------------
# Teste no jogo (14/11): o PES recalcula a energia ao carregar a carreira (pelos minutos do último jogo e os dias
# de descanso). O valor gravado no save é ignorado, então a gravação fica desligada até achar a fonte certa.
GRAVAR_ENERGIA = False
# A energia vem do save (0..255, 255 = barra ciano). O programa de recuperação, pago todo mês, devolve parte da
# energia que falta depois de cada jogo: o jogador volta ao 100% mais rápido. A alteração é gravada no save.
RECUPERACAO = [
    {'nivel': 0, 'nome': 'Sem programa', 'pct': 0, 'mensal': 0,
     'desc': 'Recuperação normal do jogo.'},
    {'nivel': 1, 'nome': 'Fisioterapia extra', 'pct': 15, 'mensal': 150_000,
     'desc': 'Massagem, piscina e sessões extras de fisioterapia depois dos jogos.'},
    {'nivel': 2, 'nome': 'Centro de recuperação', 'pct': 30, 'mensal': 350_000,
     'desc': 'Crioterapia, botas de compressão, controle de sono e nutrição individual.'},
    {'nivel': 3, 'nome': 'Ciência do esporte', 'pct': 45, 'mensal': 700_000,
     'desc': 'Monitoramento por GPS e exames de sangue, câmara hiperbárica e recuperação sob medida.'},
]


def _deb(state, hoje, valor, motivo):
    state.setdefault('debitos', []).append({'id': f"deb{len(state.get('debitos', [])) + 1}", 'data': d2s(hoje),
                                            'valor': int(valor), 'status': 'pendente', 'motivo': motivo})


def contratar_recuperacao(state, nivel, hoje):
    """Troca o programa de recuperação. O primeiro mês é cobrado na hora; depois, todo dia 1º."""
    nivel = int(nivel)
    if not 0 <= nivel < len(RECUPERACAO):
        raise ValueError('Programa inválido.')
    if nivel and not GRAVAR_ENERGIA:
        raise ValueError('O programa de recuperação está em teste: o jogo ainda não aceita a energia gravada pelo app.')
    g = state.setdefault('gestao', {})
    rec = g.setdefault('recuperacao', {'nivel': 0})
    if rec.get('nivel', 0) == nivel:
        return rec
    p = RECUPERACAO[nivel]
    if p['mensal']:
        orc = (state.get('dinheiro') or {}).get('orc_transf')
        if orc is not None and orc < p['mensal']:
            raise ValueError(f"O orçamento de transferências ({fmt_eur(orc)}) não cobre o primeiro mês ({fmt_eur(p['mensal'])}).")
        _deb(state, hoje, p['mensal'], f"Departamento médico: {p['nome']} ({hoje.strftime('%m/%Y')})")
    rec.update(nivel=nivel, desde=d2s(hoje), pago_ate=hoje.strftime('%Y-%m'))
    return rec


def cobrar_recuperacao(state, hoje):
    """Mensalidade do programa a cada mês novo (chamado a cada leitura do save)."""
    rec = (state.get('gestao') or {}).get('recuperacao') or {}
    p = RECUPERACAO[rec.get('nivel', 0)]
    if not p['mensal'] or not hoje:
        return
    mes = hoje.strftime('%Y-%m')
    pago = rec.get('pago_ate') or mes
    a, m = map(int, pago.split('-'))
    while (a, m) < (hoje.year, hoje.month):
        m += 1
        if m > 12:
            a, m = a + 1, 1
        _deb(state, hoje, p['mensal'], f"Departamento médico: {p['nome']} ({m:02d}/{a})")
    rec['pago_ate'] = mes


def recuperar(state, energia, ultima_partida):
    """Depois de cada jogo novo, devolve 'pct'% da energia que falta (uma vez por jogo). energia: {id: 0..255}.
    Devolve {id: valor novo} para gravar no save."""
    rec = (state.get('gestao') or {}).get('recuperacao') or {}
    pct = RECUPERACAO[rec.get('nivel', 0)]['pct']
    if not GRAVAR_ENERGIA or not pct or not ultima_partida:
        return {}
    feitos = rec.setdefault('feitos', {})
    out = {}
    for pid, v in energia.items():
        if v >= 255 or feitos.get(str(pid)) == ultima_partida:
            continue
        novo = int(round(v + (255 - v) * pct / 100))
        if novo > v:
            out[pid] = novo
            feitos[str(pid)] = ultima_partida
    return out


def view_energia(state, energia, elenco):
    rec = (state.get('gestao') or {}).get('recuperacao') or {}
    nomes = {j['id']: j for j in elenco or []}
    fixa = state.get('energia_fixa') or {}
    lista = [{'id': pid, 'nome': (nomes.get(pid) or {}).get('nome', str(pid)), 'pos': (nomes.get(pid) or {}).get('pos', ''),
              'energia': (nomes.get(pid) or {}).get('energia', int(round(v * 100 / 255))),
              'base': int(round(v * 100 / 255)), 'sem_ritmo': str(pid) in fixa and (nomes.get(pid) or {}).get('energia', 100) < 100}
             for pid, v in energia.items()]
    lista.sort(key=lambda x: x['energia'])
    return {'jogadores': lista, 'programas': RECUPERACAO if GRAVAR_ENERGIA else [], 'nivel': rec.get('nivel', 0),
            'desde': rec.get('desde'), 'gravavel': GRAVAR_ENERGIA}
