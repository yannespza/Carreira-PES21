"""Mercado de transferências do app: auxiliar técnico, diretor de futebol e propostas de outros clubes.

Como funciona (decidido com o usuário em 16/11/2026):
- O técnico escolhe as posições; o AUXILIAR varre os jogadores dos outros clubes (e os sem clube) e traz uma
  lista curta comparando com quem joga hoje na posição.
- O técnico indica um nome. O DIRETOR DE FUTEBOL negocia sozinho, alguns dias de jogo, e pode dar certo ou não.
  O técnico não vê preço, salário nem taxa (o custo existe e é descontado do orçamento quando a chegada for
  gravada no save).
- Outros clubes fazem propostas pelos jogadores do elenco. A diretoria CONSULTA o técnico, que aprova ou recusa.
  O valor acompanha o momento do jogador: gols, assistências, jogos como titular, nota, cartões, idade.
- Negócio fechado só se cumpre quando a JANELA DE TRANSFERÊNCIAS DO JOGO abre: aí o jogador sai de um clube e
  entra no outro. Com a janela fechada o app continua negociando; tudo fica na fila para a próxima abertura.
- Cada clube tem um caixa por janela, estimado pelas finanças reais (financas_clubes.py).

GRAVAR_NO_SAVE = False: a troca de clube no save ainda não está ligada (falta o teste no PC: comparar o save
antes e depois de uma transferência feita pelo jogo). Até lá o negócio fica "pronto para gravar".
Tudo aqui mexe só no estado do app (state['mercado'])."""
import random, datetime as dt
from .sim import d2s, s2d, _seed
from . import financas_clubes, mercado_reacoes

GRAVAR_NO_SAVE = False

# Janelas do CALENDÁRIO DO JOGO (mês, dia). Padrão do Master League do PES 2021; a confirmar no save.
# state['mercado']['janelas'] substitui, se o app achar as datas no save ou o usuário corrigir.
JANELAS_PADRAO = [{'nome': 'Janela do meio do ano', 'abre': (7, 1), 'fecha': (8, 31)},
                  {'nome': 'Janela do início do ano', 'abre': (1, 1), 'fecha': (1, 31)}]

POSICOES = ['GL', 'ZAG', 'LD', 'LE', 'VOL', 'MEI', 'MD', 'ME', 'PD', 'PE', 'ATA']
NOME_POS = {'GL': 'Goleiro', 'ZAG': 'Zagueiro', 'LD': 'Lateral direito', 'LE': 'Lateral esquerdo',
            'VOL': 'Volante', 'MEI': 'Meia', 'MD': 'Meia direita', 'ME': 'Meia esquerda',
            'PD': 'Ponta direita', 'PE': 'Ponta esquerda', 'ATA': 'Atacante'}
# posições parecidas que o auxiliar também considera
VIZINHAS = {'LD': ['MD'], 'LE': ['ME'], 'MD': ['PD', 'LD'], 'ME': ['PE', 'LE'], 'PD': ['MD', 'ATA'],
            'PE': ['ME', 'ATA'], 'VOL': ['MEI', 'ZAG'], 'MEI': ['VOL'], 'ATA': ['PD', 'PE'], 'ZAG': ['VOL'], 'GL': []}
# peso dos gols e assistências no "momento" do jogador, por posição
PESO_GOL = {'GL': 0, 'ZAG': 1.5, 'LD': 1.2, 'LE': 1.2, 'VOL': 1.2, 'MEI': 1.0, 'MD': 1.0, 'ME': 1.0,
            'PD': 0.8, 'PE': 0.8, 'ATA': 0.6}

DIAS_NEGOCIACAO = (3, 9)
PRAZO_RESPOSTA = 5            # dias para o técnico responder uma consulta de venda
CHANCE_PROPOSTA_SEMANA = 0.30  # perto da janela ou com ela aberta
MAX_CONSULTAS_ABERTAS = 2

MOTIVOS_FRACASSO = {
    'clube': ['O {clube} não aceitou vender.', 'O {clube} pediu um valor muito acima do que a diretoria aceita pagar.',
              'O {clube} considera o jogador inegociável nesta janela.'],
    'jogador': ['O jogador preferiu ficar no {clube}.', 'O empresário pediu um salário fora da realidade do clube.',
                'O jogador recebeu proposta de um clube maior e esfriou a conversa.'],
    'orcamento': ['A diretoria não tem orçamento de transferências para esse negócio agora.'],
}


# ---------------------------------------------------------------- estado
def _m(state):
    m = state.setdefault('mercado', {})
    for k in ('relatorios', 'negociacoes', 'propostas', 'historico'):
        m.setdefault(k, [])
    m.setdefault('caixa', {})          # time_id -> {'janela': chave, 'saldo': euros}
    m.setdefault('seq', 0)
    return m


def _id(m, pref):
    m['seq'] += 1
    return f'{pref}{m["seq"]}'


def _msg(engine, data, assunto, texto, clube, extra=None):
    if not engine:
        return
    engine.s['mensagens'].append({'id': engine._id(), 'data': data, 'empresa': '__diretoria__',
                                  'de': 'Diretor de futebol · ' + clube, 'assunto': assunto, 'texto': texto,
                                  'tipo': 'diretoria', 'oferta_id': None, 'lida': False, **(extra or {})})


# ---------------------------------------------------------------- janelas do jogo
def janelas(state):
    js = (state.get('mercado') or {}).get('janelas') or JANELAS_PADRAO
    return [{**j, 'abre': tuple(j['abre']), 'fecha': tuple(j['fecha'])} for j in js]


def _intervalos(state, ano):
    out = []
    for j in janelas(state):
        for a in (ano - 1, ano, ano + 1):
            ini = dt.date(a, *j['abre'])
            fim = dt.date(a if j['fecha'] >= j['abre'] else a + 1, *j['fecha'])
            out.append((ini, fim, j['nome']))
    return sorted(out)


def janela(state, hoje):
    """Situação da janela no calendário do jogo: aberta agora? quando abre a próxima?"""
    if not hoje:
        return {'aberta': False, 'nome': None, 'abre': None, 'fecha': None, 'confirmada': False}
    confirmada = bool((state.get('mercado') or {}).get('janelas'))
    for ini, fim, nome in _intervalos(state, hoje.year):
        if ini <= hoje <= fim:
            return {'aberta': True, 'nome': nome, 'abre': d2s(ini), 'fecha': d2s(fim), 'chave': d2s(ini),
                    'confirmada': confirmada}
    ini, fim, nome = next(x for x in _intervalos(state, hoje.year) if x[0] > hoje)
    return {'aberta': False, 'nome': nome, 'abre': d2s(ini), 'fecha': d2s(fim), 'chave': d2s(ini),
            'dias_para_abrir': (ini - hoje).days, 'confirmada': confirmada}


# ---------------------------------------------------------------- avaliação dos jogadores
def cgj_estimado(ficha, pos=None):
    """CGJ aproximado pelos atributos (para jogadores de outros clubes, cujo CGJ o save não guarda)."""
    if not ficha:
        return None
    a = ficha['atributos']
    p = pos or ''
    if p == 'GL':
        ks = ['Talento de goleiro', 'Firmeza de goleiro', 'Afastamento', 'Reflexos', 'Cobertura de goleiro']
    elif p == 'ZAG':
        ks = ['Talento defensivo', 'Desarme', 'Cabeceio', 'Contato físico', 'Impulsão', 'Agressividade']
    elif p in ('LD', 'LE'):
        ks = ['Talento defensivo', 'Desarme', 'Velocidade', 'Resistência', 'Passe alto', 'Aceleração']
    elif p == 'VOL':
        ks = ['Talento defensivo', 'Desarme', 'Passe rasteiro', 'Resistência', 'Contato físico', 'Agressividade']
    elif p in ('MEI', 'MD', 'ME'):
        ks = ['Passe rasteiro', 'Passe alto', 'Controle de bola', 'Talento ofensivo', 'Drible', 'Resistência']
    elif p in ('PD', 'PE'):
        ks = ['Velocidade', 'Aceleração', 'Drible', 'Controle de bola', 'Talento ofensivo', 'Finalização']
    else:
        ks = ['Finalização', 'Talento ofensivo', 'Controle de bola', 'Força do chute', 'Cabeceio', 'Aceleração']
    v = sorted((a.get(k) or 50 for k in ks), reverse=True)
    base = sum(v[:4]) / 4 * 0.75 + sum(v) / len(v) * 0.25
    return int(round(base + 0.4 * len(ficha.get('habilidades') or []) ** 0.5))


def valor_base(cgj, idade):
    """Valor de mercado em euros (mesma régua do app para os juniores: 69 de CGJ aos 18 anos = € 1 mi)."""
    if not cgj:
        return 0
    v = 1_000_000 * (1.23 ** (cgj - 69))
    if idade and idade > 21:
        v *= max(0.15, 1 - (idade - 21) * 0.07)
    elif idade and idade < 21:
        v *= 1 + (21 - idade) * 0.06
    return int(round(v, -4))


def momento(j):
    """Fator (0,6 a 1,8) e explicação do momento do jogador na temporada, pela súmula."""
    s = j.get('stats') or {}
    jogos = s.get('jogos') or 0
    if jogos < 3:
        return 1.0, ['poucos jogos na temporada']
    f, por = 1.0, []
    tit = (s.get('titular') or 0) / jogos
    f += (tit - 0.5) * 0.4
    por.append(f"titular em {s.get('titular', 0)} de {jogos} jogos")
    pg = PESO_GOL.get(j.get('pos'), 1.0)
    part = ((s.get('gols') or 0) * pg + (s.get('assist') or 0) * pg * 0.7) / jogos
    if pg:
        f += min(0.45, part * 0.6)
        if s.get('gols') or s.get('assist'):
            g_, a_ = s.get('gols', 0), s.get('assist', 0)
            por.append(f"{g_} gol{'s' if g_ != 1 else ''} e {a_} assistência{'s' if a_ != 1 else ''}")
    nota = s.get('nota_media')
    if nota:
        f += (nota - 6.2) * 0.18
        por.append(f'nota média {nota:.1f}'.replace('.', ','))
    if j.get('convocado'):
        f += 0.1
        por.append('convocado para a seleção')
    cart = (s.get('amarelos') or 0) + 3 * (s.get('vermelhos') or 0)
    if cart >= 6:
        f -= 0.08
        por.append(f"{s.get('amarelos', 0)} amarelos e {s.get('vermelhos', 0)} vermelhos")
    return round(max(0.6, min(1.8, f)), 2), por


def valor_momento(j):
    f, por = momento(j)
    return int(round(valor_base(j.get('cgj'), j.get('idade')) * f, -4)), f, por


# ---------------------------------------------------------------- caixa dos clubes
def caixa(m, tid, jan):
    """Saldo do clube nesta janela (reinicia a cada janela pelo orçamento sugerido nas finanças reais)."""
    if tid is None:
        return 10 ** 12
    c = m['caixa'].get(str(tid))
    if not c or c.get('janela') != jan.get('chave'):
        c = {'janela': jan.get('chave'), 'saldo': financas_clubes.orcamento_janela_eur(tid)}
        m['caixa'][str(tid)] = c
    return c['saldo']


def _gastar(m, tid, valor, jan):
    if tid is None:
        return
    caixa(m, tid, jan)
    m['caixa'][str(tid)]['saldo'] -= valor


# ---------------------------------------------------------------- auxiliar técnico
def _titular_da_posicao(elenco, pos):
    da_pos = [j for j in elenco if j.get('pos') == pos and j.get('cgj')]
    return max(da_pos, key=lambda j: j['cgj']) if da_pos else None


def chance(meu_tid, j, pool_clube):
    """Chance (0 a 1) de o diretor fechar o negócio."""
    if j.get('time_id') is None:
        return 0.85
    p = 0.5 + (financas_clubes.indice(meu_tid) - financas_clubes.indice(j['time_id'])) / 150
    if pool_clube:
        top = sorted((x.get('cgj') or 0 for x in pool_clube), reverse=True)[:3]
        if top and (j.get('cgj') or 0) >= top[-1]:
            p -= 0.2                     # peça importante do clube
    idade = j.get('idade') or 25
    if idade >= 31:
        p += 0.1
    elif idade <= 21:
        p -= 0.1
    return round(max(0.05, min(0.9, p)), 2)


def chance_texto(c):
    return 'muito provável' if c >= 0.75 else 'provável' if c >= 0.55 else 'possível' if c >= 0.35 else 'difícil' if c >= 0.18 else 'muito difícil'


def varrer(state, posicoes, pool, meu_tid, elenco, hoje, por_posicao=5):
    """O auxiliar monta o relatório: os melhores candidatos de cada posição pedida."""
    m = _m(state)
    meus = {j['id'] for j in elenco}
    por_clube = {}
    for j in pool:
        por_clube.setdefault(j.get('time_id'), []).append(j)
    ocupados = {n['jogador']['id'] for n in m['negociacoes'] if n['status'] in ('negociando', 'acertada')}
    rel = {'id': _id(m, 'r'), 'data': d2s(hoje) if hoje else None, 'posicoes': [], 'candidatos': []}
    for pos in posicoes:
        if pos not in POSICOES:
            continue
        tit = _titular_da_posicao(elenco, pos)
        ref = (tit or {}).get('cgj') or 60
        cands = []
        for j in pool:
            if j['id'] in meus or j['id'] in ocupados or j.get('time_id') == meu_tid:
                continue
            if j.get('pos') != pos and pos not in VIZINHAS.get(j.get('pos'), []):
                continue
            if not j.get('cgj') or j['cgj'] < ref - 2:
                continue
            f, por = momento(j)
            c = chance(meu_tid, j, por_clube.get(j.get('time_id')))
            if pos in (m.get('prioridades') or []):
                c = round(min(0.92, c + 0.08), 2)       # o diretor se empenha nas prioridades do planejamento
            idade = j.get('idade') or 27
            nota = j['cgj'] + (f - 1) * 10 - max(0, idade - 29) * 1.2 + max(0, 23 - idade) * 0.8 + c * 6
            if j.get('pos') != pos:
                nota -= 3
            cands.append((nota, j, f, por, c))
        cands.sort(key=lambda x: -x[0])
        rel['posicoes'].append({'pos': pos, 'nome': NOME_POS[pos], 'titular': (tit or {}).get('nome'),
                                'titular_cgj': (tit or {}).get('cgj'), 'achados': len(cands)})
        for nota, j, f, por, c in cands[:por_posicao]:
            obs = []
            if tit:
                d = j['cgj'] - tit['cgj']
                obs.append(f"{'+' if d >= 0 else ''}{d} de CGJ sobre o {tit['nome']}" if d else f"mesmo nível do {tit['nome']}")
            else:
                obs.append('o elenco não tem ninguém de ofício na posição')
            if j.get('pos') != pos:
                obs.append(f"joga de {NOME_POS.get(j['pos'], j['pos'])}, mas faz a função")
            if f >= 1.15:
                obs.append('vive grande fase')
            elif f <= 0.85:
                obs.append('em baixa na temporada')
            if (j.get('idade') or 30) <= 22:
                obs.append('jovem, ainda pode evoluir')
            elif (j.get('idade') or 0) >= 32:
                obs.append('experiente, contrato curto')
            rel['candidatos'].append({
                'id': j['id'], 'nome': j['nome'], 'pos': j.get('pos'), 'para': pos, 'idade': j.get('idade'),
                'cgj': j['cgj'], 'time_id': j.get('time_id'), 'clube': j.get('clube') or 'Sem clube',
                'estilo': (j.get('ficha') or {}).get('estilo') or j.get('estilo'),
                'stats': j.get('stats') or {}, 'momento': f, 'momento_por': por,
                'chance': c, 'chance_texto': chance_texto(c), 'obs': obs,
                'ref': {'nome': tit['nome'], 'cgj': tit['cgj']} if tit else None})
    m['relatorios'].append(rel)
    m['relatorios'] = m['relatorios'][-6:]
    return rel


# ---------------------------------------------------------------- diretor de futebol (compras)
def indicar(state, cand_id, hoje, meu_tid, clube, engine=None):
    """O técnico indica um candidato do último relatório; o diretor abre a negociação."""
    m = _m(state)
    cand = None
    for rel in reversed(m['relatorios']):
        cand = next((c for c in rel['candidatos'] if c['id'] == cand_id), None)
        if cand:
            break
    if not cand:
        raise ValueError('Jogador não está nos relatórios do auxiliar.')
    if any(n['jogador']['id'] == cand_id and n['status'] in ('negociando', 'acertada') for n in m['negociacoes']):
        raise ValueError('A diretoria já está cuidando desse jogador.')
    r = random.Random(_seed('neg', cand_id, d2s(hoje)))
    valor, f, _ = valor_momento(cand)
    pedida = 1.0 if cand['time_id'] is None else 1.0 + financas_clubes.indice(cand['time_id']) / 200
    custo = int(round(valor * pedida * r.uniform(0.95, 1.2), -4)) if cand['time_id'] is not None else 0
    salario = int(round(max(valor * 0.12, 60_000) * r.uniform(0.9, 1.15), -3))
    dias = r.randint(*DIAS_NEGOCIACAO)
    n = {'id': _id(m, 'n'), 'jogador': {k: cand.get(k) for k in ('id', 'nome', 'pos', 'idade', 'cgj', 'time_id', 'clube',
                                                                    'stats', 'momento', 'ref')},
         'para': cand['para'], 'status': 'negociando', 'inicio': d2s(hoje), 'previsto': d2s(hoje + dt.timedelta(days=dias)),
         'chance': cand['chance'], 'custo': custo, 'salario': salario, 'motivo': None}
    m['negociacoes'].append(n)
    mercado_reacoes.reagir(state, 'sondagem', n['jogador'], d2s(hoje), clube, cand.get('ref'))
    _msg(engine, d2s(hoje), f'Negociação aberta: {cand["nome"]}',
         f'Recebemos a sua indicação. Já fizemos o primeiro contato com '
         f'{"o " + cand["clube"] if cand["time_id"] is not None else "o empresário do jogador"} '
         f'e devemos ter uma resposta em até {dias} dias.', clube)
    return n


def cancelar(state, neg_id):
    m = _m(state)
    n = next((x for x in m['negociacoes'] if x['id'] == neg_id), None)
    if not n or n['status'] not in ('negociando', 'acertada'):
        raise ValueError('Essa negociação não pode mais ser cancelada.')
    n['status'], n['motivo'] = 'cancelada', 'Cancelada a pedido do técnico.'
    return n


def _resolver_compra(state, m, n, hoje, meu_tid, orcamento, jan, engine, clube):
    r = random.Random(_seed('res', n['id'], n['jogador']['id']))
    j = n['jogador']
    if n['custo'] > orcamento - _comprometido(m):
        n['status'], tipo = 'fracassou', 'orcamento'
    elif r.random() < n['chance']:
        n['status'], tipo = 'acertada', None
    else:
        n['status'], tipo = 'fracassou', r.choice(['clube', 'clube', 'jogador']) if j['time_id'] is not None else 'jogador'
    n['resolvido'] = d2s(hoje)
    mercado_reacoes.reagir(state, 'acertada' if n['status'] == 'acertada' else 'fracassou', j, d2s(hoje),
                           clube, j.get('ref'))
    if n['status'] == 'acertada':
        if j['time_id'] is not None:
            caixa(m, j['time_id'], jan)
            m['caixa'][str(j['time_id'])]['saldo'] += n['custo']
        quando = 'Ele se apresenta agora, com a janela aberta.' if jan['aberta'] else \
            f'Ele chega quando a janela abrir ({_dbr(jan["abre"])}).'
        _msg(engine, d2s(hoje), f'Contratação acertada: {j["nome"]}',
             f'Negócio fechado com {j["nome"]} ({NOME_POS.get(n["para"], n["para"])}). {quando}', clube)
    else:
        n['motivo'] = r.choice(MOTIVOS_FRACASSO[tipo]).format(clube=j['clube'])
        _msg(engine, d2s(hoje), f'Negociação encerrada: {j["nome"]}',
             f'Não foi possível contratar {j["nome"]}. {n["motivo"]}', clube)


def _comprometido(m):
    return sum(n['custo'] for n in m['negociacoes'] if n['status'] in ('acertada', 'pronta'))


def _dbr(s):
    d = s2d(s)
    return f'{d.day:02d}/{d.month:02d}/{d.year}'


# ---------------------------------------------------------------- propostas pelos jogadores do elenco
def _compradores(meu_tid, pool_tids):
    out = []
    for c in financas_clubes.todos():
        if c['time_id'] != meu_tid and (not pool_tids or c['time_id'] in pool_tids):
            out.append(c)
    return out


def _nova_proposta(state, m, hoje, meu_tid, elenco, jan, r, engine, clube, pool_tids):
    abertas = [p for p in m['propostas'] if p['status'] == 'consulta']
    if len(abertas) >= MAX_CONSULTAS_ABERTAS:
        return None
    ja = {p['jogador']['id'] for p in m['propostas'] if p['status'] in ('consulta', 'aprovada', 'pronta')}
    cands = [j for j in elenco if j.get('cgj') and j['id'] not in ja]
    if not cands:
        return None
    lst = set(m.get('listados') or [])
    pesos = [max(1, valor_momento(j)[0]) ** 0.5 * (6 if j['id'] in lst else 1) for j in cands]
    j = r.choices(cands, pesos)[0]
    valor, f, por = valor_momento(j)
    compradores = [c for c in _compradores(meu_tid, pool_tids) if caixa(m, c['time_id'], jan) >= valor * 0.85]
    if not compradores:
        return None
    comp = r.choices(compradores, [max(5, c['indice_poder']) ** 1.5 for c in compradores])[0]   # clubes fortes procuram mais
    oferta = int(round(min(caixa(m, comp['time_id'], jan), valor * r.uniform(0.85, 1.3)), -4))
    p = {'id': _id(m, 'p'), 'jogador': {k: j.get(k) for k in ('id', 'nome', 'pos', 'idade', 'cgj', 'stats')},
         'comprador': comp['clube'], 'comprador_id': comp['time_id'], 'valor': oferta, 'valor_momento': valor,
         'momento': f, 'momento_por': por, 'status': 'consulta', 'data': d2s(hoje),
         'prazo': d2s(hoje + dt.timedelta(days=PRAZO_RESPOSTA))}
    avaliacao = 'acima' if oferta > valor * 1.08 else 'abaixo' if oferta < valor * 0.92 else 'dentro'
    p['avaliacao'] = avaliacao
    m['propostas'].append(p)
    mercado_reacoes.reagir(state, 'proposta', {**p['jogador'], 'momento': f, 'comprador': comp['clube']},
                           d2s(hoje), clube)
    _msg(engine, d2s(hoje), f'Proposta do {comp["clube"]} por {j["nome"]}',
         f'O {comp["clube"]} fez uma proposta por {j["nome"]}. A diretoria avalia que o valor está {avaliacao} do que '
         f'ele vale hoje e quer a sua opinião antes de responder. Responda até {_dbr(p["prazo"])} na aba Elenco > Mercado.',
         clube)
    return p


EUROPA = ['Benfica', 'Porto', 'Sporting', 'Ajax', 'PSV', 'Chelsea', 'Manchester City', 'Real Madrid', 'Barcelona',
          'Atlético de Madrid', 'Lyon', 'Monaco', 'Brighton', 'RB Leipzig', 'Bayer Leverkusen', 'Juventus', 'Milan',
          'Internazionale', 'Zenit', 'Shakhtar Donetsk', 'Lille', 'Villarreal', 'Real Betis', 'Feyenoord']
CHANCE_EUROPA_SEMANA = 0.12


def _proposta_europa(state, m, hoje, jovens, jan, r, engine, clube):
    """Clube europeu sonda uma joia (até 21 anos, CGJ 70+ ou evolução forte). Valores bem acima do mercado."""
    ja = {p['jogador']['id'] for p in m['propostas'] if p['status'] in ('consulta', 'aprovada', 'pronta')}
    cands = [j for j in jovens if (j.get('idade') or 99) <= 21 and (j.get('cgj') or 0) >= 68 and j['id'] not in ja]
    if not cands:
        return None
    j = max(cands, key=lambda j: (j.get('cgj') or 0) + r.random() * 4)
    valor, f, por = valor_momento(j)
    oferta = int(round(valor * r.uniform(1.8, 3.0), -4))
    comp = r.choice(EUROPA)
    p = {'id': _id(m, 'p'), 'jogador': {k: j.get(k) for k in ('id', 'nome', 'pos', 'idade', 'cgj', 'stats')},
         'comprador': comp, 'comprador_id': None, 'estrangeiro': True, 'valor': oferta, 'valor_momento': valor,
         'momento': f, 'momento_por': por, 'status': 'consulta', 'data': d2s(hoje), 'avaliacao': 'muito acima',
         'prazo': d2s(hoje + dt.timedelta(days=PRAZO_RESPOSTA)), 'junior': bool(j.get('junior'))}
    m['propostas'].append(p)
    mercado_reacoes.reagir(state, 'proposta_europa', {**p['jogador'], 'momento': f, 'comprador': comp}, d2s(hoje), clube)
    _msg(engine, d2s(hoje), f'{comp} quer {j["nome"]}',
         f'O {comp} fez uma proposta muito acima do valor de mercado por {j["nome"]}, de {j.get("idade")} anos. '
         f'É a chance de uma grande venda, mas a torcida vai se dividir. Responda até {_dbr(p["prazo"])} na aba Elenco > Mercado.',
         clube)
    return p


def responder(state, prop_id, aprovar, hoje, clube, engine=None):
    m = _m(state)
    p = next((x for x in m['propostas'] if x['id'] == prop_id), None)
    if not p or p['status'] != 'consulta':
        raise ValueError('Essa proposta não está mais aguardando a sua resposta.')
    p['status'] = 'aprovada' if aprovar else 'recusada'
    p['respondida'] = d2s(hoje)
    jan = janela(state, hoje)
    ev = ('venda_europa' if aprovar else 'recusa_europa') if p.get('estrangeiro') else ('venda' if aprovar else 'recusa')
    mercado_reacoes.reagir(state, ev,
                           {**p['jogador'], 'momento': p.get('momento'), 'comprador': p['comprador']}, d2s(hoje), clube)
    if aprovar:
        quando = 'Ele se despede agora, com a janela aberta.' if jan['aberta'] else \
            f'A saída acontece quando a janela abrir ({_dbr(jan["abre"])}).'
        _msg(engine, d2s(hoje), f'Venda acertada: {p["jogador"]["nome"]}',
             f'Aceitamos a proposta do {p["comprador"]}. {quando}', clube)
        _gastar(m, p['comprador_id'], p['valor'], jan)
        if p['jogador']['id'] in (m.get('listados') or []):
            m['listados'].remove(p['jogador']['id'])
    return p


# ---------------------------------------------------------------- a cada save lido
def processar(state, engine, hoje, meu_tid, clube, elenco, orcamento=None, pool_tids=None, jovens=None):
    """Resolve negociações, cria propostas, vence consultas e cumpre os negócios quando a janela abre."""
    if not hoje:
        return
    m = _m(state)
    jan = janela(state, hoje)
    orc = orcamento if orcamento is not None else 10 ** 12
    for n in m['negociacoes']:
        if n['status'] == 'negociando' and s2d(n['previsto']) <= hoje:
            _resolver_compra(state, m, n, hoje, meu_tid, orc, jan, engine, clube)
    for p in m['propostas']:
        if p['status'] == 'consulta' and s2d(p['prazo']) < hoje:
            p['status'], p['motivo'] = 'expirada', 'O técnico não respondeu a tempo; a diretoria recusou.'
    # propostas novas: perto da janela (até 21 dias antes) ou com ela aberta, no máximo uma checagem por semana
    ult = m.get('ult_semana')
    if (jan['aberta'] or (jan.get('dias_para_abrir') or 999) <= 21) and (not ult or (hoje - s2d(ult)).days >= 7):
        m['ult_semana'] = d2s(hoje)
        r = random.Random(_seed('prop', d2s(hoje), meu_tid))
        lst = bool(m.get('listados'))
        if r.random() < CHANCE_PROPOSTA_SEMANA * (2 if lst else 1):
            _nova_proposta(state, m, hoje, meu_tid, elenco, jan, r, engine, clube, pool_tids)
        if r.random() < CHANCE_EUROPA_SEMANA:
            _proposta_europa(state, m, hoje, jovens if jovens is not None else elenco, jan, r, engine, clube)
    # janela aberta: os negócios fechados ficam prontos para a troca de clube no save
    if jan['aberta']:
        for n in m['negociacoes']:
            if n['status'] == 'acertada':
                n['status'], n['janela'] = 'pronta', jan['chave']
        for p in m['propostas']:
            if p['status'] == 'aprovada':
                p['status'], p['janela'] = 'pronta', jan['chave']
    m['janela'] = jan


# ---------------------------------------------------------------- tela
def view(state, hoje):
    m = _m(state)
    jan = janela(state, hoje)
    neg = m['negociacoes']
    sem_custo = lambda n: {k: v for k, v in n.items() if k not in ('custo', 'salario', 'chance')}
    return {
        'janela': jan, 'gravar_no_save': GRAVAR_NO_SAVE, 'posicoes': [{'sigla': p, 'nome': NOME_POS[p]} for p in POSICOES],
        'relatorio': m['relatorios'][-1] if m['relatorios'] else None,
        'negociando': [sem_custo(n) for n in neg if n['status'] == 'negociando'][::-1],
        'chegadas': [sem_custo(n) for n in neg if n['status'] in ('acertada', 'pronta')][::-1],
        'encerradas': [sem_custo(n) for n in neg if n['status'] in ('fracassou', 'cancelada')][-8:][::-1],
        'consultas': [p for p in m['propostas'] if p['status'] == 'consulta'][::-1],
        'saidas': [p for p in m['propostas'] if p['status'] in ('aprovada', 'pronta')][::-1],
        'propostas_passadas': [p for p in m['propostas'] if p['status'] in ('recusada', 'expirada')][-6:][::-1],
        'prioridades': m.get('prioridades') or [], 'listados': m.get('listados') or [],
    }
