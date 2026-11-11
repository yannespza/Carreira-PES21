"""Diretoria e emprego do técnico.

- Metas da temporada conforme a divisão e o tamanho do clube (posição na liga, fase da Libertadores),
  além das metas de aproveitamento e de patrocínio que já existiam.
- Situação do cargo: firme, estável, pressionado, ameaçado.
- Ultimato: com a confiança muito baixa, a diretoria dá um prazo de 4 jogos. Sem reação, demissão.
- Fim de temporada: meta cumprida renova o contrato; rebaixamento ou meta perdida com confiança baixa demite.
- Sondagens: em alta, outros clubes procuram o técnico. Você recusa (e ganha moral) ou aceita.
- Demitido, chegam propostas de outros clubes. Para assumir, comece uma carreira nova com o clube no jogo:
  o app passa a acompanhar o novo time sozinho e a carreira do técnico continua (tecnico_carreira.py).
"""
import random, datetime as dt
from .sim import d2s, s2d, _seed

PRAZO_ULTIMATO = 4
REQ_CONFIANCA, REQ_TORCIDA, REQ_JOGOS = 78, 70, 10     # para outros clubes sondarem o técnico
INTERVALO_SONDAGEM, CHANCE_SONDAGEM = 90, 0.12          # dias entre sondagens e chance por semana


def temporada(dia):
    return dia.year if dia.month >= 6 else dia.year - 1


def _e(state):
    g = state.setdefault('gestao', {})
    e = g.setdefault('emprego', {})
    e.setdefault('status', 'empregado')
    e.setdefault('historico', [])
    e.setdefault('demissao_ativa', True)
    return e


def metas_da_temporada(state, engine, hoje):
    """Calcula (uma vez por temporada) a meta de posição na liga e, se houver, a da Libertadores."""
    g = state.setdefault('gestao', {})
    mt = g.setdefault('metas_temp', {})
    ano = temporada(hoje)
    if str(ano) in mt:
        return mt[str(ano)]
    linhas = (state.get('tabela') or {}).get('linhas') or []
    n = len(linhas) or 20
    atr = state.get('atr_base', 60) + ((state.get('prestigio_tecnico') or 50) - 50) / 10
    comps = engine.competicoes_do_ano(ano) if engine else set()
    div = 'B' if 'serie_b' in comps else 'A'
    if div == 'B':
        liga = ({'alvo': 4, 'texto': 'Conquistar o acesso (terminar entre os 4 primeiros da Série B)'} if atr >= 50 else
                {'alvo': n // 2, 'texto': f'Fazer uma campanha segura na Série B (até o {n // 2}º lugar)'})
    elif atr >= 78:
        liga = {'alvo': 2, 'texto': 'Brigar pelo título (terminar entre os 2 primeiros)'}
    elif atr >= 68:
        liga = {'alvo': 4, 'texto': 'Terminar no G4 do campeonato'}
    elif atr >= 55:
        liga = {'alvo': n // 2, 'texto': f'Terminar na metade de cima da tabela (até o {n // 2}º)'}
    else:
        liga = {'alvo': n - 4, 'texto': f'Escapar do rebaixamento (até o {n - 4}º)'}
    liga['div'] = div
    copa = None
    if 'libertadores' in comps:
        copa = {'comp': 'libertadores', 'texto': 'Passar da fase de grupos da Libertadores'}
    mt[str(ano)] = {'ano': ano, 'liga': liga, 'copa': copa, 'definida': d2s(hoje)}
    return mt[str(ano)]


def _status_liga(state, meta):
    linhas = (state.get('tabela') or {}).get('linhas') or []
    tid = state.get('time_id')
    meu = next((l for l in linhas if l['id'] == tid), None)
    if not meu or not meu['j']:
        return {'status': 'aguardando', 'pos': None}
    a = meta['liga']['alvo']
    st = 'em_dia' if meu['pos'] <= a else 'perto' if meu['pos'] <= a + 3 else 'longe'
    return {'status': st, 'pos': meu['pos'], 'j': meu['j']}


def _status_copa(state, meta):
    if not meta.get('copa'):
        return None
    ano = meta['ano']
    ps = [p for p in state.get('partidas', []) if temporada(s2d(p['data'])) == ano]
    passou = any((int(p.get('torneio', 0)) & 1023) in (3, 4) for p in ps)
    return {'status': 'cumprida' if passou else 'em_andamento'}


def situacao(conf):
    return ('firme' if conf >= 70 else 'estavel' if conf >= 45 else 'pressionado' if conf >= 30 else 'ameacado')


def _msg(engine, data, assunto, texto, de=None, extra=None):
    engine.s['mensagens'].append({'id': engine._id(), 'data': data, 'empresa': '__diretoria__',
                                  'de': de or ('Presidência · ' + engine.clube), 'assunto': assunto, 'texto': texto,
                                  'tipo': 'diretoria', 'oferta_id': None, 'lida': False, **(extra or {})})


MAPA = {}        # {id: 'Pais\\Liga\\Time'} do kitserver (o app preenche ao abrir)


def _propostas(state, nomes, n=3, fortes=False, r=None):
    """Clubes do ranking real que procuram o técnico, conforme o prestígio dele (ranking.py)."""
    from . import ranking
    seed = (r or random.Random(1)).random()
    ps = ranking.propostas(state.get('prestigio_tecnico') or 50, state.get('time_id'), MAPA, n, fortes, seed)
    if ps:
        return ps
    return _propostas_tabela(state, nomes, n, fortes, r)


def _propostas_tabela(state, nomes, n=3, fortes=False, r=None):
    """Clubes que procuram o técnico: os de baixo da tabela quando ele está desempregado, os de cima numa sondagem."""
    r = r or random.Random(1)
    tid = state.get('time_id')
    linhas = [l for l in (state.get('tabela') or {}).get('linhas') or [] if l['id'] != tid]
    if linhas:
        linhas.sort(key=lambda l: l['pos'])
        pool = linhas[:6] if fortes else linhas[len(linhas) // 2:]
        esc = r.sample(pool, min(n, len(pool)))
        return [{'time_id': l['id'], 'nome': (l.get('nome') or (nomes or {}).get(l['id'], f"Time {l['id']}")).title()}
                for l in esc]
    outros = [(i, nm) for i, nm in (nomes or {}).items() if i != tid]
    return [{'time_id': i, 'nome': nm.title()} for i, nm in r.sample(outros, min(n, len(outros)))]


def demitir(state, engine, mundo, hoje, motivo, nomes):
    e = _e(state)
    if e['status'] != 'empregado':
        return
    ds = d2s(hoje)
    r = random.Random(_seed('dem', ds))
    e.update(status='demitido', data=ds, motivo=motivo, ultimato=None,
             propostas=_propostas(state, nomes, 3, False, r))
    e['historico'].append({'data': ds, 'tipo': 'demissao', 'texto': motivo})
    mundo.noticia('tecnico_demitido', ds, r, destaque=True)
    _msg(engine, ds, 'Comunicado: desligamento do técnico',
         f'{mundo.tecnico()}, a diretoria decidiu encerrar o seu trabalho no {mundo.clube}. Motivo: {motivo}. '
         'Agradecemos a dedicação. Clubes já procuraram seu empresário; veja as propostas na aba Clube > Diretoria.')
    mundo._torcida(4)          # a torcida respira com a troca


def processar(state, engine, mundo, hoje, nomes):
    """Chamado a cada save lido (depois da imprensa e do fim de liga)."""
    if not hoje:
        return
    e = _e(state)
    ds = d2s(hoje)
    meta = metas_da_temporada(state, engine, hoje)
    e.setdefault('contrato_ate', temporada(hoje) + 1)
    if e['status'] != 'empregado':
        return
    conf = mundo.m['diretoria']
    ult = e.get('ultimato')
    njogos = len(state.get('partidas', []))
    # ultimato
    if not ult and conf <= 25:
        e['ultimato'] = ult = {'data': ds, 'jogos_base': njogos, 'prazo': PRAZO_ULTIMATO}
        mundo.noticia('tecnico_ultimato', ds, random.Random(_seed('ult', ds)), destaque=True)
        _msg(engine, ds, f'ULTIMATO: {PRAZO_ULTIMATO} jogos',
             f'A confiança da diretoria chegou ao limite. Você tem {PRAZO_ULTIMATO} jogos para reagir. '
             'Precisamos de pelo menos 7 pontos nesse período, ou a confiança de volta a um nível aceitável.')
        e['historico'].append({'data': ds, 'tipo': 'ultimato', 'texto': f'Ultimato de {PRAZO_ULTIMATO} jogos'})
    if ult:
        ps = state.get('partidas', [])[ult['jogos_base']:]
        pts = sum({'V': 3, 'E': 1, 'D': 0}[p['res']] for p in ps)
        if conf >= 40 or (len(ps) >= ult['prazo'] and pts >= 7):
            e['ultimato'] = None
            mundo.m['diretoria'] = min(100, mundo.m['diretoria'] + 5)
            _msg(engine, ds, 'Ultimato superado', 'A reação apareceu. A diretoria renova a confiança no seu trabalho.')
            e['historico'].append({'data': ds, 'tipo': 'superou', 'texto': 'Superou o ultimato'})
        elif len(ps) >= ult['prazo'] and e['demissao_ativa']:
            demitir(state, engine, mundo, hoje, f'apenas {pts} pontos nos {len(ps)} jogos do ultimato', nomes)
            return
    # fim de temporada: renovação ou demissão
    temps = (state.get('gestao') or {}).get('temporadas', [])
    for t in temps:
        if t.get('avaliada'):
            continue
        t['avaliada'] = True
        mt = (state['gestao'].get('metas_temp') or {}).get(str(t['ano']))
        cumpriu = bool(mt and t['pos'] <= mt['liga']['alvo'])
        t['meta_cumprida'] = cumpriu
        r = random.Random(_seed('fimtemp', t['ano']))
        if t.get('rebaixado') and e['demissao_ativa']:
            demitir(state, engine, mundo, hoje, f'rebaixamento em {t["ano"]}', nomes)
            return
        if not cumpriu and conf < 45 and e['demissao_ativa']:
            demitir(state, engine, mundo, hoje, f'meta da temporada {t["ano"]} não cumprida ({t["pos"]}º lugar)', nomes)
            return
        if cumpriu or conf >= 55:
            anos = 2 if (cumpriu and (t.get('titulos') or t.get('acesso'))) else 1
            novo = t['ano'] + anos
            if novo <= e.get('contrato_ate', 0):
                continue           # o contrato já vai além disso
            e['contrato_ate'] = novo
            mundo.noticia('tecnico_renova', ds, r, destaque=True)
            _msg(engine, ds, 'Renovação de contrato',
                 f'Com a temporada {t["ano"]} ({t["pos"]}º lugar' + (', meta cumprida' if cumpriu else '') +
                 f'), a diretoria renovou o seu contrato até o fim da temporada {e["contrato_ate"]}.')
            e['historico'].append({'data': ds, 'tipo': 'renovacao', 'texto': f'Renovou até {e["contrato_ate"]}'})
    # sondagem de outro clube (no máximo uma a cada 90 dias)
    if conf >= REQ_CONFIANCA and mundo.m['torcida'] >= REQ_TORCIDA and not e.get('sondagem') and len(state.get('partidas', [])) >= REQ_JOGOS:
        u = e.get('ult_sondagem')
        semana = hoje.isocalendar()[:2]
        if (not u or (hoje - s2d(u)).days >= INTERVALO_SONDAGEM) and e.get('sond_semana') != list(semana):
            e['sond_semana'] = list(semana)
            r = random.Random(_seed('sond', *semana))
            if r.random() < CHANCE_SONDAGEM:
                cl = _propostas(state, nomes, 1, True, r)
                if cl:
                    e['sondagem'] = {'data': ds, **cl[0]}
                    e['ult_sondagem'] = ds
                    e['historico'].append({'data': ds, 'tipo': 'sondagem', 'texto': f'Sondado pelo {cl[0]["nome"]}'})
                    mundo.noticia('tecnico_sondado', ds, r, adv=cl[0]['nome'])
                    _msg(engine, ds, f'Sondagem do {cl[0]["nome"]}',
                         f'O {cl[0]["nome"]} procurou o seu empresário. Eles querem você no comando. '
                         'Decida na aba Clube > Diretoria.', de=f'{cl[0]["nome"]} · Diretoria de futebol')


def responder_sondagem(state, engine, mundo, aceitar):
    e = _e(state)
    s = e.get('sondagem')
    if not s:
        raise ValueError('Não há sondagem em aberto.')
    ds = state.get('data')
    r = random.Random(_seed('resp', ds, s['nome']))
    e['sondagem'] = None
    if aceitar:
        e.update(status='saiu', data=ds, motivo=f'aceitou proposta do {s["nome"]}', propostas=[s])
        e['historico'].append({'data': ds, 'tipo': 'saida', 'texto': f'Aceitou o {s["nome"]}'})
        mundo._torcida(-8)
        mundo.m['noticias'].append({'data': ds, 'tipo': 'tecnico_demitido', 'destaque': True, 'fonte': 'Globo Esporte',
                                    'titulo': f'{mundo.tecnico()} aceita proposta e deixa o {mundo.clube} rumo ao {s["nome"]}'})
    else:
        e['contrato_ate'] = e.get('contrato_ate', 0) + 1
        mundo._torcida(4)
        mundo.m['diretoria'] = min(100, mundo.m['diretoria'] + 4)
        mundo.noticia('tecnico_fica', ds, r, destaque=True, adv=s['nome'])
        e['historico'].append({'data': ds, 'tipo': 'fica', 'texto': f'Recusou o {s["nome"]} e renovou'})
    return e


def continuar(state, mundo):
    """Depois de demitido, seguir no mesmo clube mesmo assim (o presidente volta atrás)."""
    e = _e(state)
    if e['status'] == 'empregado':
        return e
    ds = state.get('data')
    e.update(status='empregado', ultimato=None, propostas=[])
    e['historico'].append({'data': ds, 'tipo': 'volta', 'texto': 'O presidente voltou atrás e manteve o técnico'})
    mundo.m['diretoria'] = max(mundo.m['diretoria'], 35)
    mundo.m['noticias'].append({'data': ds, 'tipo': 'diretoria_elogia', 'destaque': True, 'fonte': 'Lance!',
                                'titulo': f'Reviravolta: presidente volta atrás e mantém {mundo.tecnico()} no {mundo.clube}'})
    return e


def view(state, mundo, hoje):
    e = _e(state)
    meta = (state.get('gestao') or {}).get('metas_temp', {}).get(str(temporada(hoje))) if hoje else None
    conf = mundo.m['diretoria'] if mundo else 50
    ult = e.get('ultimato')
    restam = None
    if ult:
        restam = max(0, ult['prazo'] - (len(state.get('partidas', [])) - ult['jogos_base']))
    torcida = mundo.m.get('torcida', 50) if mundo else 50
    jogos = len(state.get('partidas', []))
    u = e.get('ult_sondagem')
    dias = (hoje - s2d(u)).days if u and hoje else None
    mercado = {'confianca': conf, 'torcida': torcida, 'jogos': jogos, 'dias_ult': dias,
               'requisitos': [{'nome': 'Confiança da diretoria', 'atual': conf, 'alvo': REQ_CONFIANCA},
                              {'nome': 'Humor da torcida', 'atual': torcida, 'alvo': REQ_TORCIDA},
                              {'nome': 'Jogos no comando', 'atual': jogos, 'alvo': REQ_JOGOS}],
               'intervalo_ok': dias is None or dias >= INTERVALO_SONDAGEM, 'intervalo': INTERVALO_SONDAGEM,
               'chance_semana': int(CHANCE_SONDAGEM * 100),
               'recebidas': [h for h in e['historico'] if h.get('tipo') in ('sondagem', 'fica', 'saida', 'demissao')][-20:][::-1]}
    return {'mercado': mercado, 'status': e['status'], 'situacao': situacao(conf), 'confianca': conf, 'contrato_ate': e.get('contrato_ate'),
            'ultimato': ult and {**ult, 'restam': restam}, 'sondagem': e.get('sondagem'),
            'propostas': e.get('propostas', []), 'motivo': e.get('motivo'), 'demissao_ativa': e['demissao_ativa'],
            'historico': e['historico'][-12:][::-1],
            'meta': meta and {**meta, 'liga_status': _status_liga(state, meta), 'copa_status': _status_copa(state, meta)}}
