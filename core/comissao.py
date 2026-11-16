"""Comissão técnica: o auxiliar técnico trabalha com os números da súmula.

- Relatório depois de cada jogo: destaques, quem caiu de rendimento e sugestão de mudança no time.
- Análise do próximo adversário: forma, gols marcados e sofridos, artilheiros, quem está pendurado ou suspenso.
- Preleção: antes do jogo o técnico escolhe o tom; depois do resultado o auxiliar diz se funcionou.
- Metas individuais: o auxiliar propõe metas para alguns jogadores; cumprir dá moral, falhar tira.
- Base: recomenda subir um júnior quando ele está pronto (CGJ e evolução que o save guarda).
Nada aqui grava no save. A moral é a do app (gestao.moral_ajuste)."""
import random, datetime as dt
from .sim import d2s, s2d, _seed
from .gestao import moral_ajuste
from . import vestiario

OFENSIVOS = {'ATA', 'PD', 'PE', 'MEI', 'MD', 'ME'}
NOME_POS = {'GL': 'goleiro', 'ZAG': 'zagueiro', 'LD': 'lateral-direito', 'LE': 'lateral-esquerdo', 'VOL': 'volante',
            'MEI': 'meia', 'MD': 'meia pela direita', 'ME': 'meia pela esquerda', 'PD': 'ponta-direita',
            'PE': 'ponta-esquerda', 'ATA': 'atacante'}
TONS = {'motivar': 'Motivar o grupo', 'cobrar': 'Cobrar postura', 'tranquilizar': 'Tranquilizar'}


def _c(state):
    c = state.setdefault('comissao', {})
    for k in ('relatorios', 'metas', 'base_recomendados', 'prelecoes'):
        c.setdefault(k, [] if k != 'base_recomendados' else {})
    return c


def _num(x):
    return f'{x:.1f}'.replace('.', ',')


def _msg(engine, data, assunto, texto, clube):
    if engine:
        engine.s['mensagens'].append({'id': engine._id(), 'data': data, 'empresa': '__diretoria__',
                                      'de': 'Auxiliar técnico · ' + clube, 'assunto': assunto, 'texto': texto,
                                      'tipo': 'diretoria', 'oferta_id': None, 'lida': False})


# ---------------------------------------------------------------- relatório pós-jogo
def relatorio_pos_jogo(state, estat, elenco, clube, engine=None, nomes_clubes=None):
    """Um relatório por partida nova (a mais recente da súmula do clube)."""
    if not estat or not estat.get('sumulas'):
        return None
    c = _c(state)
    s = estat['sumulas'][0]
    chave = f"{s['data']}|{s['mandante']}|{s['visitante']}"
    if any(r['chave'] == chave for r in c['relatorios']):
        return None
    js = [j for j in s['jogadores'] if j.get('min')]
    if not js:
        return None
    pos = {j['id']: j.get('pos') for j in elenco}
    tab = {j['id']: j for j in estat.get('jogadores', [])}
    nc = nomes_clubes or {}
    gp, gc = (s['gols_mandante'], s['gols_visitante']) if s['em_casa'] else (s['gols_visitante'], s['gols_mandante'])
    adv = nc.get(s['visitante'] if s['em_casa'] else s['mandante'], 'o adversário')
    res = 'vitória' if gp > gc else 'empate' if gp == gc else 'derrota'
    com_nota = [j for j in js if j.get('nota')]
    dest = sorted(com_nota, key=lambda j: (-j['nota'], -(j['gols'] + j['assist'])))[:3]
    destaques = []
    for j in dest:
        if j['nota'] < 6.6 and not (j['gols'] or j['assist']):
            continue
        feito = ', '.join(x for x in [f"{j['gols']} gol{'s' if j['gols'] != 1 else ''}" if j['gols'] else '',
                                      f"{j['assist']} assistência{'s' if j['assist'] != 1 else ''}" if j['assist'] else ''] if x)
        destaques.append({'nome': j['nome'], 'texto': f"nota {_num(j['nota'])}" + (f', {feito}' if feito else '')})
    quedas = []
    for j in com_nota:
        t = tab.get(j['id']) or {}
        ult = t.get('ultimas_notas') or []
        if len(ult) >= 3 and t.get('nota_media'):
            rec = sum(ult[-3:]) / 3
            if rec <= t['nota_media'] - 0.45 and rec < 6.4:
                quedas.append({'nome': j['nome'], 'texto': f"média {_num(rec)} nos últimos 3 jogos, contra {_num(t['nota_media'])} na temporada"})
    sugestoes = []
    titulares = [j for j in js if j.get('titular')]
    em_campo = {j['id'] for j in js}
    for j in sorted(titulares, key=lambda j: j.get('nota') or 6.5):
        if (j.get('nota') or 7) >= 6.0 or len(sugestoes) >= 2:
            continue
        p = pos.get(j['id'])
        alt = [t for t in estat.get('jogadores', []) if t['id'] not in em_campo and pos.get(t['id']) == p
               and t.get('nota_media') and t['nota_media'] >= (tab.get(j['id'], {}).get('nota_media') or 6) + 0.2]
        if alt:
            a = max(alt, key=lambda t: t['nota_media'])
            sugestoes.append(f"{a['nome']} no lugar de {j['nome']}: nota {_num(j['nota'])} hoje, e o {a['nome']} tem "
                             f"média {_num(a['nota_media'])} na temporada")
    rel = {'chave': chave, 'data': s['data'], 'adv': adv, 'placar': f'{gp} x {gc}', 'resultado': res,
           'destaques': destaques, 'quedas': quedas[:3], 'sugestoes': sugestoes}
    c['relatorios'].append(rel)
    c['relatorios'] = c['relatorios'][-15:]
    linhas = [f"Relatório da {res} por {gp} x {gc} contra o {adv}."]
    if destaques:
        linhas.append('Destaques: ' + '; '.join(f"{d['nome']} ({d['texto']})" for d in destaques) + '.')
    if quedas:
        linhas.append('Atenção: ' + '; '.join(f"{q['nome']} ({q['texto']})" for q in quedas[:3]) + '.')
    if sugestoes:
        linhas.append('Sugestão: ' + ' / '.join(sugestoes) + '.')
    _msg(engine, s['data'], f'Relatório do jogo: {gp} x {gc} contra o {adv}', ' '.join(linhas), clube)
    return rel


# ---------------------------------------------------------------- próximo adversário
def analise_adversario(partidas, proximo, team_id, nomes, nomes_clubes, nomes_jog=None):
    """partidas: sumulas.partidas(save); proximo: 1º item de state['proximos']."""
    if not proximo:
        return None
    adv = proximo['v'] if proximo['m'] == team_id else proximo['m']
    seus = [p for p in partidas if adv in (p['mandante'], p['visitante'])]
    if not seus:
        return {'adv': adv, 'nome': nomes_clubes.get(adv, proximo.get('vn') or proximo.get('mn')),
                'data': proximo['data'], 'casa': proximo['m'] == team_id, 'sem_dados': True}
    ult = seus[-5:]
    forma, gm, gs = [], 0, 0
    for p in ult:
        casa = p['mandante'] == adv
        a, b = (p['gols_mandante'], p['gols_visitante']) if casa else (p['gols_visitante'], p['gols_mandante'])
        gm += a
        gs += b
        forma.append('V' if a > b else 'E' if a == b else 'D')
    jog = {}
    for p in seus:
        lado = p['escalacao_mandante'] if p['mandante'] == adv else p['escalacao_visitante']
        for x in lado:
            s = jog.setdefault(x['id'], {'id': x['id'], 'gols': 0, 'assist': 0, 'amarelos': 0, 'vermelho_ultimo': False,
                                         'notas': [], 'jogos': 0})
            if x['min']:
                s['jogos'] += 1
            s['gols'] += x['gols']
            s['assist'] += x['assist']
            s['amarelos'] += x['amarelo']
            if x['nota'] is not None:
                s['notas'].append(x['nota'])
    if seus:
        ul = seus[-1]
        lado = ul['escalacao_mandante'] if ul['mandante'] == adv else ul['escalacao_visitante']
        for x in lado:
            if x['vermelho']:
                jog[x['id']]['vermelho_ultimo'] = True
    nm = lambda pid: ((nomes_jog or nomes or {}).get(pid) or {}).get('nome') or f'Jogador {pid}'
    perigo = sorted((s for s in jog.values() if s['gols'] + s['assist']), key=lambda s: -(s['gols'] + 0.7 * s['assist']))[:3]
    melhores = sorted((s for s in jog.values() if len(s['notas']) >= 3), key=lambda s: -sum(s['notas']) / len(s['notas']))[:2]
    suspensos = [nm(s['id']) for s in jog.values() if s['vermelho_ultimo']]
    pendurados = [nm(s['id']) for s in jog.values() if s['amarelos'] and s['amarelos'] % 3 == 2]
    n = len(ult)
    dica = []
    if gs / n >= 1.6:
        dica.append('a defesa deles sofre muito: vale ser agressivo')
    if gm / n >= 1.8:
        dica.append('o ataque é perigoso: cuidado com a transição')
    if forma.count('D') >= 3:
        dica.append('chegam pressionados pela sequência ruim')
    if forma.count('V') >= 4:
        dica.append('vivem grande fase: jogo para ter paciência')
    return {'adv': adv, 'nome': nomes_clubes.get(adv, f'Time {adv}'), 'data': proximo['data'], 'casa': proximo['m'] == team_id,
            'comp': proximo.get('comp'), 'forma': forma, 'gols_marcados': round(gm / n, 1), 'gols_sofridos': round(gs / n, 1),
            'perigo': [{'nome': nm(s['id']), 'gols': s['gols'], 'assist': s['assist']} for s in perigo],
            'melhores': [{'nome': nm(s['id']), 'nota': round(sum(s['notas']) / len(s['notas']), 1)} for s in melhores],
            'suspensos': suspensos, 'pendurados': pendurados[:4], 'dicas': dica}


# ---------------------------------------------------------------- preleção
def prelecao(state, proximo, tom, data):
    if tom not in TONS or not proximo:
        raise ValueError('Escolha um tom para a preleção.')
    c = _c(state)
    chave = f"{proximo['data']}|{proximo['m']}|{proximo['v']}"
    c['prelecoes'] = [p for p in c['prelecoes'] if p['chave'] != chave or p.get('avaliada')]
    c['prelecoes'].append({'chave': chave, 'data_jogo': proximo['data'], 'tom': tom, 'escolhida': data,
                           'm': proximo['m'], 'v': proximo['v']})
    c['prelecoes'] = c['prelecoes'][-20:]


def avaliar_prelecoes(state, partidas_clube, team_id, clube, engine=None):
    """Quando o jogo da preleção aparece na súmula, o auxiliar avalia se o tom funcionou."""
    c = _c(state)
    hist = [p for p in partidas_clube]
    for pr in c['prelecoes']:
        if pr.get('avaliada'):
            continue
        jogo = next((p for p in hist if p['data'] == pr['data_jogo'] and {p['mandante'], p['visitante']} == {pr['m'], pr['v']}), None)
        if not jogo:
            if s2d(pr['data_jogo']) < s2d(state.get('data') or pr['data_jogo']) - dt.timedelta(days=3):
                pr['avaliada'] = True          # jogo não apareceu (adiado ou fora da súmula)
            continue
        casa = jogo['mandante'] == team_id
        gp, gc = (jogo['gm'], jogo['gv']) if casa else (jogo['gv'], jogo['gm'])
        ant = [p for p in hist if p['data'] < jogo['data']][-3:]
        derrotas_antes = sum(1 for p in ant if p.get('res') == 'D')
        tom = pr['tom']
        if gp > gc:
            ok = True
            txt = {'motivar': 'O grupo entrou ligado desde o início. A preleção mexeu com eles.',
                   'cobrar': 'A cobrança surtiu efeito: o time correu mais e foi mais concentrado.',
                   'tranquilizar': 'Com a cabeça leve, o time jogou solto e decidiu nos detalhes.'}[tom]
        elif gp == gc:
            ok = tom == 'tranquilizar' or (tom == 'cobrar' and derrotas_antes >= 2)
            txt = ('O tom foi certo para o momento, faltou só o gol.' if ok else
                   'O time não respondeu como esperávamos. Talvez o tom não tenha sido o ideal para esse jogo.')
        else:
            ok = False
            txt = {'motivar': 'A motivação não se traduziu em campo. O time sentiu a pressão.',
                   'cobrar': 'A cobrança pesou. Alguns jogadores entraram travados.' if derrotas_antes < 2 else
                             'Nem a cobrança tirou o time da fase ruim.',
                   'tranquilizar': 'Faltou intensidade. O time entrou leve demais.'}[tom]
        pr.update(avaliada=True, ok=ok, texto=txt, placar=f'{gp} x {gc}')
        moral_ajuste(state, '*', 1 if ok else -1, jogo['data'], f'preleção ({TONS[tom].lower()})', 7)
        vestiario.mexer(state, 2 if ok else -1, 'preleção', jogo['data'])
        _msg(engine, jogo['data'], f'Preleção: {TONS[tom]} ({gp} x {gc})', txt, clube)


# ---------------------------------------------------------------- metas individuais
def propor_metas(state, estat, elenco, hoje, clube, engine=None):
    """No início de cada mês o auxiliar propõe até 3 metas para os próximos 30 dias."""
    if not hoje or not estat:
        return
    c = _c(state)
    mes = hoje.strftime('%Y-%m')
    if c.get('metas_mes') == mes:
        return
    c['metas_mes'] = mes
    tab = {j['id']: j for j in estat.get('jogadores', [])}
    pos = {j['id']: j.get('pos') for j in elenco}
    r = random.Random(_seed('metas', mes, clube))
    cand = [t for t in tab.values() if t.get('jogos', 0) >= 3 and pos.get(t['id'])]
    r.shuffle(cand)
    novas = []
    for t in sorted(cand, key=lambda t: -(t.get('minutos') or 0))[:8]:
        if len(novas) >= 3:
            break
        p = pos[t['id']]
        jogos = t['jogos']
        if p == 'ATA' or (p in OFENSIVOS and t['gols'] / jogos >= 0.2):
            alvo = max(2, round(t['gols'] / jogos * 4 + 0.5))
            novas.append({'tipo': 'gols', 'alvo': alvo, 'texto': f"marcar {alvo} gols nos próximos 30 dias"})
        elif p in OFENSIVOS:
            alvo = max(2, round(t['assist'] / jogos * 4 + 0.5))
            novas.append({'tipo': 'assist', 'alvo': alvo, 'texto': f"dar {alvo} assistências nos próximos 30 dias"})
        else:
            base = t.get('nota_media') or 6.4
            alvo = round(min(7.2, base + 0.3), 1)
            novas.append({'tipo': 'nota', 'alvo': alvo, 'texto': f"manter nota média de {_num(alvo)} nos próximos 30 dias"})
        novas[-1].update({'id': t['id'], 'nome': t['nome'], 'inicio': d2s(hoje), 'fim': d2s(hoje + dt.timedelta(days=30)),
                          'base': {'gols': t['gols'], 'assist': t['assist'], 'jogos': t['jogos'],
                                   'soma_notas': (t.get('nota_media') or 0) * jogos}, 'status': 'ativa'})
    c['metas'] = [m for m in c['metas'] if m['status'] != 'ativa'][-20:] + novas
    if novas:
        _msg(engine, d2s(hoje), 'Metas individuais do mês',
             'Combinei metas com alguns jogadores: ' + '; '.join(f"{m['nome']}: {m['texto']}" for m in novas) + '.', clube)


def avaliar_metas(state, estat, hoje, clube, engine=None, mundo=None):
    if not hoje or not estat:
        return
    c = _c(state)
    tab = {j['id']: j for j in estat.get('jogadores', [])}
    for m in c['metas']:
        if m['status'] != 'ativa':
            continue
        t = tab.get(m['id']) or {}
        b = m['base']
        jogos = (t.get('jogos') or 0) - b['jogos']
        if m['tipo'] == 'gols':
            feito = (t.get('gols') or 0) - b['gols']
        elif m['tipo'] == 'assist':
            feito = (t.get('assist') or 0) - b['assist']
        else:
            soma = (t.get('nota_media') or 0) * (t.get('jogos') or 0) - b['soma_notas']
            feito = round(soma / jogos, 1) if jogos > 0 else 0
        m['progresso'] = feito
        m['jogos'] = jogos
        cumpriu = feito >= m['alvo']
        if cumpriu and m['tipo'] != 'nota':
            m['status'] = 'cumprida'
        elif hoje >= s2d(m['fim']):
            m['status'] = 'cumprida' if cumpriu and jogos >= 2 else 'falhou'
        else:
            continue
        ds = d2s(hoje)
        if m['status'] == 'cumprida':
            moral_ajuste(state, m['nome'], 1, ds, 'cumpriu a meta do mês', 21)
            un = {'gols': 'gols', 'assist': 'assistências', 'nota': 'de nota média'}[m['tipo']]
            if mundo is not None:
                mundo.m['noticias'].append({'data': ds, 'tipo': 'jog_elogio', 'destaque': False, 'fonte': 'Setorista',
                                            'jogador': m['nome'],
                                            'titulo': f"{m['nome']} bate a meta da comissão: {_num(feito) if m['tipo'] == 'nota' else feito} {un} em {jogos} jogos"})
            _msg(engine, ds, f"Meta cumprida: {m['nome']}", f"{m['nome']} cumpriu a meta ({m['texto']}).", clube)
        else:
            moral_ajuste(state, m['nome'], -1, ds, 'não cumpriu a meta do mês', 14)
            _msg(engine, ds, f"Meta não cumprida: {m['nome']}",
                 f"{m['nome']} não chegou à meta ({m['texto']}): fez {_num(feito) if m['tipo'] == 'nota' else feito}.", clube)


# ---------------------------------------------------------------- base
def recomendar_base(state, juniores, elenco, hoje, clube, engine=None):
    """Júnior pronto: CGJ perto do pior jogador da posição no elenco, ou evolução forte nos últimos meses."""
    if not hoje or not juniores:
        return []
    c = _c(state)
    temp = str(hoje.year)
    feitos = c['base_recomendados'].setdefault(temp, [])
    out = []
    for j in juniores:
        cgj = j.get('cgj') or 0
        curva = [x for x in (j.get('curva') or []) if x]
        evol = (curva[-1] - curva[0]) if len(curva) >= 2 else 0
        mesmos = [e.get('cgj') or 0 for e in elenco if e.get('pos') == j.get('pos') and e.get('cgj')]
        pior = min(mesmos) if mesmos else 60
        pronto = cgj >= pior - 1 or (cgj >= 64 and evol >= 5)
        if not pronto:
            continue
        motivo = (f"CGJ {cgj}, perto do {pior} do jogador mais fraco da posição no elenco" if cgj >= pior - 1 else
                  f"subiu {evol} de CGJ nos últimos meses (hoje {cgj})")
        out.append({'id': j['id'], 'nome': j['nome'], 'pos': j.get('pos'), 'idade': j.get('idade'), 'cgj': cgj,
                    'motivo': motivo})
        if j['id'] not in feitos:
            feitos.append(j['id'])
            _msg(engine, d2s(hoje), f"Base: {j['nome']} está pronto",
                 f"Recomendo subir {j['nome']} ({NOME_POS.get(j.get('pos'), j.get('pos') or '')}, {j.get('idade') or '?'} anos) "
                 f"para o profissional: {motivo}. A promoção é feita no jogo (Juniores > promover).", clube)
    return out
