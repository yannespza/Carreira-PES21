"""Gestão do elenco: renovações, empréstimos, insatisfação de reservas, conversa individual e histórico no clube.

- Renovação: o diretor avisa quem tem contrato acabando em até 6 meses (data do "Dados do time"). O técnico
  decide renovar ou deixar sair. O jogador pode recusar (fase boa em clube que ele considera pequeno, moral baixa).
- Empréstimo: o auxiliar sugere jovens com pouco tempo de campo; o diretor procura clube. O empréstimo se cumpre
  na janela do jogo (como as transferências). Depois o app acompanha os números dele no outro clube.
- Insatisfação: jogador bom com poucos minutos reclama. O técnico conversa, promete minutos (cobrado em 21 dias)
  ou libera para negociação (entra na vitrine do mercado).
- Conversa individual: elogiar, cobrar ou acalmar. O efeito depende da fase do jogador.
- Histórico: jogos, gols, assistências e nota de cada temporada no clube (base do ídolo).
GRAVAR_NO_SAVE = False: renovação e empréstimo ficam "prontos" até o teste no PC."""
import random, datetime as dt
from .sim import d2s, s2d, _seed
from .gestao import moral_ajuste
from . import vestiario, mercado_reacoes, financas_clubes

GRAVAR_NO_SAVE = False
AVISO_CONTRATO_DIAS = 180
PRAZO_PROMESSA = 21
INTERVALO_CONVERSA = 7
CLUBES_EMPRESTIMO = ['Mirassol', 'Chapecoense', 'Remo', 'Coritiba', 'Vitória', 'Juventude', 'Goiás', 'Avaí', 'Criciúma',
                     'Ponte Preta', 'Novorizontino', 'Vila Nova', 'Botafogo-SP', 'Operário-PR', 'CRB', 'Athletic-MG']


def _g(state):
    g = state.setdefault('elenco_gestao', {})
    for k in ('renovacoes', 'emprestimos', 'insatisfeitos', 'conversas'):
        g.setdefault(k, [])
    g.setdefault('historico', {})
    return g


def _msg(engine, data, assunto, texto, clube, de='Diretor de futebol'):
    if engine:
        engine.s['mensagens'].append({'id': engine._id(), 'data': data, 'empresa': '__diretoria__',
                                      'de': f'{de} · {clube}', 'assunto': assunto, 'texto': texto,
                                      'tipo': 'diretoria', 'oferta_id': None, 'lida': False})


def _num(x):
    return f'{x:.1f}'.replace('.', ',')


def _stats(estat):
    return {j['id']: j for j in (estat or {}).get('jogadores', [])}


# ---------------------------------------------------------------- histórico no clube
def temporada(dia):
    return dia.year


def registrar_historico(state, estat, elenco, hoje):
    """Guarda os números da temporada atual de cada jogador (a súmula só tem a temporada corrente)."""
    if not hoje or not estat:
        return
    g = _g(state)
    ano = str(temporada(hoje))
    for t in estat.get('jogadores', []):
        h = g['historico'].setdefault(str(t['id']), {'nome': t['nome'], 'temporadas': {}})
        h['nome'] = t['nome']
        h['temporadas'][ano] = {k: t.get(k) for k in ('jogos', 'titular', 'minutos', 'gols', 'assist', 'amarelos',
                                                       'vermelhos', 'nota_media')}
    no_elenco = {str(j['id']) for j in elenco}
    for pid, h in g['historico'].items():
        h['no_elenco'] = pid in no_elenco


def historico_view(state):
    g = _g(state)
    out = []
    for pid, h in g['historico'].items():
        ts = h['temporadas']
        tot = {k: sum((t.get(k) or 0) for t in ts.values()) for k in ('jogos', 'titular', 'gols', 'assist')}
        notas = [(t.get('nota_media') or 0) * (t.get('jogos') or 0) for t in ts.values() if t.get('nota_media')]
        jn = sum((t.get('jogos') or 0) for t in ts.values() if t.get('nota_media'))
        out.append({'id': int(pid), 'nome': h['nome'], 'no_elenco': h.get('no_elenco', False), 'temporadas': len(ts),
                    'desde': min(ts) if ts else None, **tot, 'nota_media': round(sum(notas) / jn, 2) if jn else None,
                    'por_temporada': [{'ano': a, **ts[a]} for a in sorted(ts)]})
    return sorted(out, key=lambda x: (-x['no_elenco'], -x['jogos']))


def pontos_idolo(h):
    """Pontuação de ídolo pelo histórico: gols, assistências, longevidade e nota."""
    nota = h.get('nota_media') or 6.3
    return h['gols'] * 1.0 + h['assist'] * 0.6 + h['jogos'] * 0.12 + (nota - 6.4) * 12 + (h['temporadas'] - 1) * 4


# ---------------------------------------------------------------- renovação
def checar_contratos(state, elenco, hoje, clube, engine=None):
    if not hoje:
        return
    g = _g(state)
    abertas = {r['id'] for r in g['renovacoes'] if r['status'] in ('pendente', 'renovado', 'pronta')}
    for j in elenco:
        fim = j.get('contrato_ate')
        if not fim or j['id'] in abertas:
            continue
        d = (s2d(fim) - hoje).days
        if 0 <= d <= AVISO_CONTRATO_DIAS and not any(r['id'] == j['id'] and r.get('fim') == fim for r in g['renovacoes']):
            g['renovacoes'].append({'id': j['id'], 'nome': j['nome'], 'pos': j.get('pos'), 'idade': j.get('idade'),
                                    'cgj': j.get('cgj'), 'fim': fim, 'status': 'pendente', 'aviso': d2s(hoje)})
            _msg(engine, d2s(hoje), f"Contrato terminando: {j['nome']}",
                 f"O contrato de {j['nome']} termina em {s2d(fim).strftime('%d/%m/%Y')}. Quer que a diretoria renove? "
                 "Responda na aba Elenco > Gestão.", clube)


def decidir_renovacao(state, pid, renovar, hoje, clube, estat=None, engine=None, time_id=None):
    g = _g(state)
    r = next((x for x in g['renovacoes'] if x['id'] == pid and x['status'] == 'pendente'), None)
    if not r:
        raise ValueError('Essa renovação não está mais pendente.')
    ds = d2s(hoje)
    t = _stats(estat).get(pid) or {}
    j = {'id': pid, 'nome': r['nome'], 'pos': r.get('pos'), 'idade': r.get('idade'), 'stats': t}
    fs = mercado_reacoes.fase(j)
    if not renovar:
        r.update(status='liberado', decidido=ds)
        moral_ajuste(state, r['nome'], -1, ds, 'não terá o contrato renovado', 30)
        _msg(engine, ds, f"{r['nome']} não será renovado",
             f"Comunicamos ao estafe de {r['nome']} que o clube não vai renovar. Ele sai quando o contrato terminar.", clube)
        _repercute(state, 'nao_renova', j, fs, ds, clube)
        return r
    rnd = random.Random(_seed('renova', pid, ds))
    aceita = 0.8
    if fs == 'boa':
        aceita -= 0.15 + max(0, 50 - financas_clubes.indice(time_id)) / 200
    if (r.get('idade') or 25) >= 31:
        aceita += 0.12
    aceita = max(0.3, min(0.95, aceita))
    if rnd.random() < aceita:
        aumento = round(rnd.uniform(5, 15) + (12 if fs == 'boa' else 0) - (6 if fs == 'ruim' else 0))
        anos = 1 if (r.get('idade') or 25) >= 31 else rnd.choice([2, 3, 3, 4])
        r.update(status='renovado', decidido=ds, anos=anos, aumento=max(0, aumento))
        moral_ajuste(state, r['nome'], 1, ds, 'renovou o contrato', 30)
        _msg(engine, ds, f"Renovação acertada: {r['nome']}",
             f"{r['nome']} renovou por {anos} ano{'s' if anos > 1 else ''}. "
             + ('' if GRAVAR_NO_SAVE else 'A nova data de contrato será gravada no save quando a gravação for ligada.'), clube)
        _repercute(state, 'renova', j, fs, ds, clube)
    else:
        r.update(status='recusou', decidido=ds)
        moral_ajuste(state, r['nome'], -1, ds, 'recusou a renovação', 21)
        _msg(engine, ds, f"{r['nome']} recusou renovar",
             f"O estafe de {r['nome']} recusou a proposta de renovação. Ele pode sair de graça no fim do contrato.", clube)
        _repercute(state, 'recusa_renovar', j, fs, ds, clube)
    return r


TXT_RENOVA = {
    ('renova', 'boa'): ['renovou! fica com a gente', 'grande notícia, um dos melhores do time continua', 'ESSE tem que ficar mesmo'],
    ('renova', 'ruim'): ['renovaram com ele?? não entendi', 'sério que renovaram?', 'contrato longo pra quem não joga...'],
    ('renova', 'normal'): ['renovação ok, ajuda no elenco', 'bom pra manter o grupo', 'fica, beleza'],
    ('nao_renova', 'boa'): ['deixar sair de graça um jogador desses?', 'como assim não renova?', 'diretoria perdida'],
    ('nao_renova', 'ruim'): ['fez certo, ciclo encerrado', 'já foi tarde', 'decisão correta'],
    ('nao_renova', 'normal'): ['ciclo encerrado, obrigado pelos serviços', 'tudo bem, abre espaço', 'ok, vida que segue'],
    ('recusa_renovar', 'boa'): ['vai sair de graça?? diretoria, resolve isso', 'perder um desses por contrato é amadorismo'],
    ('recusa_renovar', 'ruim'): ['quer sair? pode ir', 'não vai fazer falta'],
    ('recusa_renovar', 'normal'): ['recusou... paciência', 'se não quer ficar, segue o jogo'],
}


def _repercute(state, evento, j, fs, ds, clube):
    m = state.setdefault('mundo', {})
    m.setdefault('noticias', [])
    m.setdefault('posts', [])
    r = random.Random(_seed('rep', evento, j['id'], ds))
    ff = mercado_reacoes.fatos(j)
    lado = mercado_reacoes._juntar(mercado_reacoes._do_lado(ff, fs)[:2])
    tit = {'renova': f"{clube} renova com {j['nome']}", 'nao_renova': f"{clube} não vai renovar com {j['nome']}",
           'recusa_renovar': f"{j['nome']} recusa renovar com o {clube}"}[evento] + (f' ({lado})' if lado else '')
    m['noticias'].append({'data': ds, 'titulo': tit, 'tipo': 'transferencia', 'fonte': r.choice(mercado_reacoes.FONTES),
                          'destaque': False, 'jogador': j['nome']})
    ops = TXT_RENOVA.get((evento, fs)) or TXT_RENOVA[(evento, 'normal')]
    from . import vozes
    perfis = vozes.torcedores(clube)
    for (autor, nome), t in zip(r.sample(perfis, 2), r.sample(ops, min(2, len(ops)))):
        m['posts'].append({'data': ds, 'autor': autor, 'nome': nome, 'texto': vozes.humanizar(t, r), 'base': t,
                           'humor': 'mercado', 'tema': 'mercado', 'curtidas': r.randint(40, 900), 'reposts': r.randint(2, 80),
                           'respostas': [], 'jogador': j['nome']})


# ---------------------------------------------------------------- empréstimos
def sugerir_emprestimos(state, elenco, estat, hoje):
    """Jovens (até 22) com pouco tempo de campo: menos de 25% dos minutos do time."""
    if not estat:
        return []
    tab = _stats(estat)
    jogos_time = estat.get('jogos') or 0
    g = _g(state)
    ja = {e['id'] for e in g['emprestimos'] if e['status'] in ('negociando', 'acertado', 'pronta', 'emprestado')}
    out = []
    for j in elenco:
        if (j.get('idade') or 99) > 22 or j['id'] in ja:
            continue
        mins = (tab.get(j['id']) or {}).get('minutos') or 0
        share = mins / (jogos_time * 90) if jogos_time else 0
        if jogos_time >= 6 and share < 0.25:
            out.append({'id': j['id'], 'nome': j['nome'], 'pos': j.get('pos'), 'idade': j.get('idade'), 'cgj': j.get('cgj'),
                        'minutos': mins, 'motivo': f"{mins} minutos em {jogos_time} jogos do time"})
    return out


def emprestar(state, pid, elenco, hoje, clube, engine=None):
    g = _g(state)
    j = next((x for x in elenco if x['id'] == pid), None)
    if not j:
        raise ValueError('Jogador não está no elenco.')
    if any(e['id'] == pid and e['status'] in ('negociando', 'acertado', 'pronta') for e in g['emprestimos']):
        raise ValueError('A diretoria já procura clube para ele.')
    r = random.Random(_seed('emp', pid, d2s(hoje)))
    dias = r.randint(4, 10)
    g['emprestimos'].append({'id': pid, 'nome': j['nome'], 'pos': j.get('pos'), 'idade': j.get('idade'), 'cgj': j.get('cgj'),
                             'status': 'negociando', 'inicio': d2s(hoje), 'previsto': d2s(hoje + dt.timedelta(days=dias))})
    _msg(engine, d2s(hoje), f"Empréstimo: {j['nome']}",
         f"Vamos procurar um clube para {j['nome']} ganhar minutos. Resposta em até {dias} dias.", clube)


def processar_emprestimos(state, hoje, jan, clube, engine=None, stats_todos=None):
    g = _g(state)
    for e in g['emprestimos']:
        if e['status'] == 'negociando' and s2d(e['previsto']) <= hoje:
            r = random.Random(_seed('empres', e['id'], e['previsto']))
            if r.random() < 0.8:
                e.update(status='acertado', destino=r.choice(CLUBES_EMPRESTIMO), resolvido=d2s(hoje))
                quando = 'Ele se apresenta agora.' if jan.get('aberta') else f"Ele vai quando a janela abrir ({s2d(jan['abre']).strftime('%d/%m/%Y')})."
                _msg(engine, d2s(hoje), f"Empréstimo acertado: {e['nome']}",
                     f"{e['nome']} será emprestado ao {e['destino']} até o fim da temporada. {quando}", clube)
            else:
                e.update(status='sem_clube', resolvido=d2s(hoje))
                _msg(engine, d2s(hoje), f"Empréstimo: sem interessados em {e['nome']}",
                     f"Nenhum clube se interessou por {e['nome']} agora. Tentamos de novo mais perto da janela.", clube)
        elif e['status'] == 'acertado' and jan.get('aberta'):
            e['status'] = 'pronta'
        if stats_todos and e['status'] in ('pronta', 'emprestado'):
            s = stats_todos.get(e['id'])
            if s:
                e['no_destino'] = s


# ---------------------------------------------------------------- insatisfação
def checar_insatisfacao(state, elenco, estat, hoje, clube, mundo=None, engine=None, afastados=()):
    """Uma vez por semana: jogador com CGJ acima da mediana do elenco e menos de 30% dos minutos nos últimos 5 jogos."""
    if not hoje or not estat or not estat.get('sumulas'):
        return
    g = _g(state)
    if g.get('ult_insat') and (hoje - s2d(g['ult_insat'])).days < 7:
        return
    g['ult_insat'] = d2s(hoje)
    ult = estat['sumulas'][:5]
    if len(ult) < 4:
        return
    mins = {}
    for s in ult:
        for x in s['jogadores']:
            mins[x['id']] = mins.get(x['id'], 0) + (x.get('min') or 0)
    cgjs = sorted(j.get('cgj') or 0 for j in elenco if j.get('cgj'))
    if not cgjs:
        return
    mediana = cgjs[len(cgjs) // 2]
    ativos = {i['id'] for i in g['insatisfeitos'] if i['status'] in ('insatisfeito', 'promessa')}
    recentes = {i['id'] for i in g['insatisfeitos'] if (hoje - s2d(i['data'])).days < 45}
    for j in sorted(elenco, key=lambda j: -(j.get('cgj') or 0)):
        if j['id'] in ativos or j['id'] in recentes or j['nome'] in afastados or j.get('pos') == 'GL':
            continue
        share = mins.get(j['id'], 0) / (len(ult) * 90)
        if (j.get('cgj') or 0) >= mediana and share < 0.3:
            ds = d2s(hoje)
            g['insatisfeitos'].append({'id': j['id'], 'nome': j['nome'], 'pos': j.get('pos'), 'data': ds,
                                       'status': 'insatisfeito', 'minutos': mins.get(j['id'], 0), 'jogos': len(ult)})
            moral_ajuste(state, j['nome'], -1, ds, 'insatisfeito com o tempo de jogo', 21)
            vestiario.mexer(state, -2, f"{j['nome']} insatisfeito", ds)
            vestiario._evento(state, ds, 'reclamacao', f"{j['nome']} quer jogar mais",
                              f"{j['nome']} jogou {mins.get(j['id'], 0)} minutos nos últimos {len(ult)} jogos e pediu uma "
                              "conversa com o técnico.", [j['nome']], False)
            if mundo is not None:
                mundo.m['noticias'].append({'data': ds, 'tipo': 'jog_reclama', 'destaque': False, 'fonte': 'Setorista',
                                            'jogador': j['nome'],
                                            'titulo': f"Com {mins.get(j['id'], 0)} minutos nos últimos {len(ult)} jogos, {j['nome']} se incomoda com a reserva no {clube}"})
            _msg(engine, ds, f"{j['nome']} está insatisfeito",
                 f"{j['nome']} reclamou do pouco tempo de campo. Converse com ele, prometa minutos ou libere para negociação "
                 "na aba Elenco > Gestão.", clube, de='Auxiliar técnico')
            break


def responder_insatisfeito(state, pid, acao, hoje, clube, engine=None):
    g = _g(state)
    i = next((x for x in g['insatisfeitos'] if x['id'] == pid and x['status'] == 'insatisfeito'), None)
    if not i:
        raise ValueError('Esse jogador não está esperando resposta.')
    ds = d2s(hoje)
    r = random.Random(_seed('insat', pid, ds, acao))
    if acao == 'conversar':
        if r.random() < 0.55:
            i.update(status='resolvido', resposta='conversa', texto='Saiu da conversa mais tranquilo e prometeu trabalhar.')
            moral_ajuste(state, i['nome'], 1, ds, 'conversou com o técnico', 14)
        else:
            i.update(status='resolvido', resposta='conversa', texto='Ouviu, mas saiu da sala ainda chateado.')
            moral_ajuste(state, i['nome'], -1, ds, 'conversa não convenceu', 14)
    elif acao == 'prometer':
        i.update(status='promessa', resposta='promessa', prazo=d2s(hoje + dt.timedelta(days=PRAZO_PROMESSA)),
                 texto=f'Você prometeu mais minutos. Ele vai cobrar em {PRAZO_PROMESSA} dias.')
        moral_ajuste(state, i['nome'], 1, ds, 'recebeu a promessa de jogar mais', PRAZO_PROMESSA)
    elif acao == 'liberar':
        i.update(status='resolvido', resposta='liberado', texto='Liberado para negociação: entra na vitrine do mercado.')
        m = state.setdefault('mercado', {})
        lst = m.setdefault('listados', [])
        if pid not in lst:
            lst.append(pid)
    else:
        raise ValueError('Ação desconhecida.')
    return i


def cobrar_promessas(state, estat, hoje, clube, engine=None):
    g = _g(state)
    if not estat:
        return
    for i in g['insatisfeitos']:
        if i['status'] != 'promessa' or s2d(i['prazo']) > hoje:
            continue
        mins = 0
        jogos = 0
        for s in estat.get('sumulas', []):
            if i['data'] < s['data'] <= i['prazo']:
                jogos += 1
                mins += next((x.get('min') or 0 for x in s['jogadores'] if x['id'] == i['id']), 0)
        ds = d2s(hoje)
        if jogos and mins / (jogos * 90) >= 0.45:
            i.update(status='resolvido', texto=f'Promessa cumprida: jogou {mins} minutos em {jogos} jogos.')
            moral_ajuste(state, i['nome'], 1, ds, 'promessa de minutos cumprida', 21)
            vestiario.mexer(state, 2, 'promessa cumprida', ds)
        else:
            i.update(status='resolvido', texto=f'Promessa quebrada: só {mins} minutos em {jogos} jogos. Ele pediu para sair.')
            moral_ajuste(state, i['nome'], -2, ds, 'promessa de minutos não cumprida', 30)
            vestiario.mexer(state, -4, f"promessa quebrada com {i['nome']}", ds)
            lst = state.setdefault('mercado', {}).setdefault('listados', [])
            if i['id'] not in lst:
                lst.append(i['id'])
            _msg(engine, ds, f"{i['nome']} pediu para sair",
                 f"{i['nome']} cobrou a promessa de minutos ({mins} minutos em {jogos} jogos) e pediu para ser negociado.",
                 clube, de='Auxiliar técnico')


# ---------------------------------------------------------------- conversa individual
RESP = {
    ('elogiar', 'boa'): (1, ['Agradeceu e disse que quer manter o nível.', 'Saiu motivado, sorrindo.']),
    ('elogiar', 'normal'): (1, ['Gostou do reconhecimento.', 'Agradeceu a confiança.']),
    ('elogiar', 'ruim'): (0, ['Ficou sem graça: sabe que não vive boa fase.', 'Agradeceu, mas o grupo estranhou o elogio.']),
    ('elogiar', 'sem_jogos'): (0, ['Agradeceu, mas quer mesmo é jogar.']),
    ('cobrar', 'boa'): (-2, ['Achou a cobrança injusta e saiu irritado.', 'Não entendeu a bronca depois de jogar bem.']),
    ('cobrar', 'normal'): (0, ['Ouviu calado. Vamos ver a resposta em campo.', 'Disse que vai melhorar.']),
    ('cobrar', 'ruim'): (1, ['Reconheceu a fase e prometeu reagir.', 'Aceitou a cobrança e pediu mais treino.']),
    ('cobrar', 'sem_jogos'): (-1, ['Respondeu que é difícil render sem jogar.']),
    ('acalmar', 'boa'): (0, ['Disse que está tranquilo.']),
    ('acalmar', 'normal'): (1, ['Ficou mais leve depois da conversa.']),
    ('acalmar', 'ruim'): (1, ['A conversa tirou um peso das costas dele.', 'Agradeceu o apoio no momento difícil.']),
    ('acalmar', 'sem_jogos'): (1, ['Entendeu que a chance vai chegar.']),
}


def conversar(state, pid, tipo, elenco, estat, hoje, clube):
    if tipo not in ('elogiar', 'cobrar', 'acalmar'):
        raise ValueError('Tipo de conversa desconhecido.')
    g = _g(state)
    j = next((x for x in elenco if x['id'] == pid), None)
    if not j:
        raise ValueError('Jogador não está no elenco.')
    ult = next((c for c in reversed(g['conversas']) if c['id'] == pid), None)
    if ult and (hoje - s2d(ult['data'])).days < INTERVALO_CONVERSA:
        raise ValueError(f"Você conversou com {j['nome']} há pouco tempo. Espere alguns dias.")
    st = _stats(estat).get(pid) or {}
    fs = mercado_reacoes.fase({**j, 'stats': st})
    insat = any(i['id'] == pid and i['status'] == 'insatisfeito' for i in g['insatisfeitos'])
    delta, textos = RESP[(tipo, fs)]
    if tipo == 'acalmar' and insat:
        delta = 1
    r = random.Random(_seed('conv', pid, d2s(hoje), tipo))
    texto = r.choice(textos)
    ds = d2s(hoje)
    if delta:
        moral_ajuste(state, j['nome'], delta, ds, {'elogiar': 'elogio do técnico', 'cobrar': 'cobrança do técnico',
                                                   'acalmar': 'conversa com o técnico'}[tipo], 14)
    if tipo == 'elogiar' and fs == 'ruim':
        vestiario.mexer(state, -1, f"elogio a {j['nome']} sem jogar bem", ds)
    c = {'id': pid, 'nome': j['nome'], 'tipo': tipo, 'data': ds, 'fase': fs, 'efeito': delta, 'texto': texto}
    g['conversas'].append(c)
    g['conversas'] = g['conversas'][-60:]
    return c


# ---------------------------------------------------------------- tela
def view(state, elenco, estat, hoje, jan=None):
    g = _g(state)
    ultima_conv = {}
    for c in g['conversas']:
        ultima_conv[c['id']] = c
    return {
        'renovacoes': [r for r in g['renovacoes'] if r['status'] == 'pendente'],
        'renovacoes_feitas': [r for r in g['renovacoes'] if r['status'] != 'pendente'][-8:][::-1],
        'emprestimos': [e for e in g['emprestimos'] if e['status'] != 'sem_clube'][-10:][::-1],
        'sugestoes_emprestimo': sugerir_emprestimos(state, elenco, estat, hoje) if hoje else [],
        'insatisfeitos': [i for i in g['insatisfeitos'] if i['status'] in ('insatisfeito', 'promessa')],
        'insatisfeitos_passados': [i for i in g['insatisfeitos'] if i['status'] == 'resolvido'][-6:][::-1],
        'conversas': g['conversas'][-8:][::-1],
        'pode_conversar': {str(j['id']): not (ultima_conv.get(j['id']) and hoje and
                                              (hoje - s2d(ultima_conv[j['id']]['data'])).days < INTERVALO_CONVERSA) for j in elenco},
        'historico': historico_view(state)[:40],
        'gravar_no_save': GRAVAR_NO_SAVE,
    }
