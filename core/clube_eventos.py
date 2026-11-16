"""Eventos do clube ligados à diretoria e à torcida.

- Pressão por vendas: com o orçamento de transferências no vermelho (ou quase zerado diante da folha), a
  diretoria pede para vender um jogador. Aceitar coloca o jogador na vitrine; recusar custa confiança.
- Planejamento de temporada: o técnico escolhe as posições prioritárias; o diretor de futebol prioriza esses
  nomes no mercado e, perto da janela, traz um relatório pronto dessas posições.
- Protestos e festa: sequências ruins geram protesto (CT, aeroporto, faixas); boas sequências, festa.
- Convocação: jogadores em grande fase são chamados para a seleção nas datas FIFA (valoriza no mercado).
Nada aqui grava no save."""
import random, datetime as dt
from .sim import d2s, s2d, _seed
from .gestao import moral_ajuste
from . import vozes, mercado, mercado_reacoes

INTERVALO_PEDIDO_VENDA = 30
PERDA_CONFIANCA_RECUSA = 8
DATAS_FIFA = [(3, 16), (6, 1), (9, 1), (10, 6), (11, 10)]     # início das datas FIFA no calendário da carreira


def _e(state):
    c = state.setdefault('clube_eventos', {})
    for k in ('pedidos_venda', 'protestos', 'convocacoes'):
        c.setdefault(k, [])
    c.setdefault('prioridades', [])
    return c


def _msg(engine, data, assunto, texto, clube, de='Presidência'):
    if engine:
        engine.s['mensagens'].append({'id': engine._id(), 'data': data, 'empresa': '__diretoria__',
                                      'de': f'{de} · {clube}', 'assunto': assunto, 'texto': texto,
                                      'tipo': 'diretoria', 'oferta_id': None, 'lida': False})


# ---------------------------------------------------------------- pressão por vendas
def checar_caixa(state, dinheiro, elenco, hoje, clube, engine=None, idolo=None):
    if not hoje or not dinheiro:
        return
    c = _e(state)
    orc = dinheiro.get('orc_transf')
    folha = dinheiro.get('salario_anual') or 0
    if orc is None:
        return
    crise = orc < 0 or (folha and orc < folha * 0.03)
    if not crise or any(p['status'] == 'pendente' for p in c['pedidos_venda']):
        return
    ult = c['pedidos_venda'][-1]['data'] if c['pedidos_venda'] else None
    if ult and (hoje - s2d(ult)).days < INTERVALO_PEDIDO_VENDA:
        return
    em_negocio = {p['jogador']['id'] for p in (state.get('mercado') or {}).get('propostas', [])
                  if p['status'] in ('consulta', 'aprovada', 'pronta')}
    cands = [j for j in elenco if j.get('cgj') and j['nome'] != idolo and j['id'] not in em_negocio]
    if not cands:
        return
    j = max(cands, key=lambda j: mercado.valor_base(j.get('cgj'), j.get('idade')))
    ds = d2s(hoje)
    p = {'id': j['id'], 'nome': j['nome'], 'pos': j.get('pos'), 'data': ds, 'status': 'pendente',
         'prazo': d2s(hoje + dt.timedelta(days=7)), 'orc': orc}
    c['pedidos_venda'].append(p)
    _msg(engine, ds, f"Diretoria pede a venda de {j['nome']}",
         f"O orçamento de transferências está {'no vermelho' if orc < 0 else 'praticamente zerado'}. "
         f"Para equilibrar as contas, a diretoria quer negociar {j['nome']}, o jogador mais valorizado do elenco. "
         "Aceite (ele entra na vitrine do mercado) ou recuse em até 7 dias na aba Elenco > Mercado. "
         "Recusar vai desgastar a sua relação com a diretoria.", clube)


def responder_pedido_venda(state, aceitar, hoje, clube, mundo=None, engine=None):
    c = _e(state)
    p = next((x for x in c['pedidos_venda'] if x['status'] == 'pendente'), None)
    if not p:
        raise ValueError('Não há pedido de venda em aberto.')
    ds = d2s(hoje)
    if aceitar:
        p.update(status='aceito', respondido=ds)
        lst = state.setdefault('mercado', {}).setdefault('listados', [])
        if p['id'] not in lst:
            lst.append(p['id'])
        moral_ajuste(state, p['nome'], -1, ds, 'foi colocado à venda pela diretoria', 21)
        if mundo is not None:
            mundo.m['noticias'].append({'data': ds, 'tipo': 'transferencia', 'destaque': True, 'fonte': 'Globo Esporte',
                                        'jogador': p['nome'], 'titulo': f"Em crise financeira, {clube} coloca {p['nome']} à venda"})
    else:
        p.update(status='recusado', respondido=ds)
        if mundo is not None:
            mundo.m['diretoria'] = max(0, mundo.m['diretoria'] - PERDA_CONFIANCA_RECUSA)
            mundo.m['noticias'].append({'data': ds, 'tipo': 'diretoria_cobra', 'destaque': True, 'fonte': 'Setorista',
                                        'titulo': f"Técnico barra venda de {p['nome']} e irrita a diretoria do {clube}"})
        _msg(engine, ds, 'Pedido de venda recusado',
             f"A diretoria registrou a sua recusa em vender {p['nome']}. As contas continuam no vermelho e a cobrança vai aumentar.", clube)
    return p


def vencer_pedidos(state, hoje, clube, mundo=None, engine=None):
    for p in _e(state)['pedidos_venda']:
        if p['status'] == 'pendente' and s2d(p['prazo']) < hoje:
            p['status'] = 'recusado'
            p['respondido'] = d2s(hoje)
            p['sem_resposta'] = True
            if mundo is not None:
                mundo.m['diretoria'] = max(0, mundo.m['diretoria'] - PERDA_CONFIANCA_RECUSA // 2)
            _msg(engine, d2s(hoje), 'Pedido de venda sem resposta',
                 f"Você não respondeu ao pedido de venda de {p['nome']}. A diretoria entendeu como recusa.", clube)


# ---------------------------------------------------------------- planejamento
def definir_prioridades(state, posicoes, hoje):
    c = _e(state)
    c['prioridades'] = [p for p in posicoes if p in mercado.POSICOES][:4]
    c['prioridades_em'] = d2s(hoje) if hoje else None
    state.setdefault('mercado', {})['prioridades'] = c['prioridades']
    return c['prioridades']


def lembrete_planejamento(state, hoje, clube, engine=None):
    """No começo de cada temporada (janeiro) a diretoria pede o planejamento."""
    if not hoje or hoje.month != 1:
        return
    c = _e(state)
    if c.get('lembrete_ano') == hoje.year:
        return
    c['lembrete_ano'] = hoje.year
    _msg(engine, d2s(hoje), f'Planejamento da temporada {hoje.year}',
         'Quais posições você quer reforçar este ano? Marque as prioridades na aba Elenco > Mercado. '
         'O diretor de futebol vai concentrar as buscas nelas.', clube, de='Diretor de futebol')


def relatorio_prioridades(state, pool, meu_tid, elenco, hoje, jan, clube, engine=None):
    """Perto da janela (até 21 dias antes) o diretor entrega um relatório das posições prioritárias."""
    c = _e(state)
    if not c['prioridades'] or not pool or not hoje:
        return
    chave = jan.get('chave')
    if c.get('relatorio_janela') == chave:
        return
    if not (jan.get('aberta') or (jan.get('dias_para_abrir') or 999) <= 21):
        return
    c['relatorio_janela'] = chave
    rel = mercado.varrer(state, c['prioridades'], pool, meu_tid, elenco, hoje, por_posicao=3)
    nomes = ', '.join(f"{x['nome']} ({x['para']})" for x in rel['candidatos'][:6])
    _msg(engine, d2s(hoje), 'Nomes para as posições prioritárias',
         f"Separamos os melhores nomes para as prioridades do planejamento: {nomes or 'ninguém acima dos titulares atuais'}. "
         'O relatório completo está na aba Elenco > Mercado.', clube, de='Diretor de futebol')


# ---------------------------------------------------------------- protestos e festa
PROTESTO = {
    'titulos': ['Torcedores protestam no CT do {clube} depois de {n} jogos sem vitória',
                'Protesto no aeroporto: torcida do {clube} cobra o elenco após sequência de {n} jogos sem vencer',
                'Faixas no muro do CT: "{clube} sem raça" após {n} jogos sem vitória',
                'Organizada do {clube} pede reunião com a diretoria depois de {n} jogos sem vitória'],
    'posts': ['amanhã todo mundo no CT. chega!', 'não dá mais pra ver o time desse jeito', 'quero ver a cara deles no aeroporto',
              'diretoria e técnico, a paciência acabou', 'cadê a vergonha na cara?', 'esse elenco não honra a camisa',
              'protesto pacífico, mas firme. queremos respostas', 'faixa pronta. sábado no CT'],
}
FESTA = {
    'titulos': ['Festa no desembarque: torcida recebe o {clube} após {n} vitórias seguidas',
                'Clima de euforia: {n} vitórias seguidas e a torcida lota o treino aberto do {clube}',
                'Torcida faz corredor de fogos na chegada do {clube} depois de {n} vitórias seguidas'],
    'posts': ['que fase! todo mundo no aeroporto', 'esse time é muito bom de ver jogar', 'ninguém segura esse {clube}',
              'treino aberto lotado, que energia', 'segue assim que o título vem', 'orgulho desse elenco'],
}


def checar_sequencia(state, hoje, clube, mundo=None):
    if not hoje or mundo is None:
        return
    ps = state.get('partidas', [])
    if len(ps) < 4:
        return
    c = _e(state)
    ult = c['protestos'][-1]['data'] if c['protestos'] else None
    if ult and (hoje - s2d(ult)).days < 30:
        return
    sem_vencer = 0
    for p in reversed(ps):
        if p['res'] == 'V':
            break
        sem_vencer += 1
    vitorias = 0
    for p in reversed(ps):
        if p['res'] != 'V':
            break
        vitorias += 1
    ds = d2s(hoje)
    r = random.Random(_seed('seq', ds, clube))
    if sem_vencer >= 5:
        tipo, banco, n = 'protesto', PROTESTO, sem_vencer
        mundo._torcida(-3)
        mundo.m['diretoria'] = max(0, mundo.m['diretoria'] - 3)
        moral_ajuste(state, '*', -1, ds, 'protesto da torcida', 10)
    elif vitorias >= 4:
        tipo, banco, n = 'festa', FESTA, vitorias
        mundo._torcida(3)
        moral_ajuste(state, '*', 1, ds, 'festa da torcida', 10)
    else:
        return
    c['protestos'].append({'data': ds, 'tipo': tipo, 'n': n})
    mundo.m['noticias'].append({'data': ds, 'tipo': 'vestiario_racha' if tipo == 'protesto' else 'vestiario_unido',
                                'destaque': True, 'fonte': r.choice(mercado_reacoes.FONTES),
                                'titulo': r.choice(banco['titulos']).format(clube=clube, n=n)})
    perfis = vozes.torcedores(clube)
    for (autor, nome), t in zip(r.sample(perfis, 3), r.sample(banco['posts'], 3)):
        t = t.format(clube=clube)
        mundo.m['posts'].append({'data': ds, 'autor': autor, 'nome': nome, 'texto': vozes.humanizar(t, r), 'base': t,
                                 'humor': 'irritado' if tipo == 'protesto' else 'feliz', 'tema': tipo,
                                 'curtidas': r.randint(200, 4000), 'reposts': r.randint(20, 600), 'respostas': []})


# ---------------------------------------------------------------- convocação
def checar_convocacao(state, estat, elenco, hoje, clube, mundo=None, engine=None):
    if not hoje or not estat:
        return
    c = _e(state)
    data_fifa = next((dt.date(hoje.year, m, d) for m, d in DATAS_FIFA
                      if 0 <= (dt.date(hoje.year, m, d) - hoje).days <= 10), None)
    if not data_fifa or c.get('ult_data_fifa') == d2s(data_fifa):
        return
    c['ult_data_fifa'] = d2s(data_fifa)
    tab = {j['id']: j for j in estat.get('jogadores', [])}
    chamados = []
    for j in elenco:
        t = tab.get(j['id']) or {}
        if (t.get('jogos') or 0) >= 6 and (t.get('nota_media') or 0) >= 7.0 and (j.get('cgj') or 0) >= 76:
            chamados.append({'id': j['id'], 'nome': j['nome'], 'nota': t['nota_media'], 'jogos': t['jogos'],
                             'gols': t.get('gols', 0)})
    ds = d2s(hoje)
    for x in chamados[:4]:
        c['convocacoes'].append({**x, 'data': ds, 'data_fifa': d2s(data_fifa)})
        moral_ajuste(state, x['nome'], 1, ds, 'convocado para a seleção', 21)
        if mundo is not None:
            mundo.m['noticias'].append({'data': ds, 'tipo': 'jog_elogio', 'destaque': True, 'fonte': 'Globo Esporte',
                                        'jogador': x['nome'],
                                        'titulo': f"{x['nome']}, do {clube}, é convocado para a seleção: nota {x['nota']:.1f}".replace('.', ',', 1)
                                                  + f" em {x['jogos']} jogos na temporada"})
    if chamados and engine:
        _msg(engine, ds, 'Convocação para a seleção',
             'Convocados para a data FIFA de ' + data_fifa.strftime('%d/%m') + ': ' + ', '.join(x['nome'] for x in chamados[:4])
             + '. Eles se valorizam no mercado.', clube, de='Auxiliar técnico')
    c['convocacoes'] = c['convocacoes'][-40:]


def convocados_recentes(state, hoje, dias=120):
    if not hoje:
        return set()
    return {x['id'] for x in _e(state)['convocacoes'] if (hoje - s2d(x['data'])).days <= dias}


def view(state):
    c = _e(state)
    return {'prioridades': c['prioridades'], 'pedido_venda': next((p for p in c['pedidos_venda'] if p['status'] == 'pendente'), None),
            'pedidos_passados': [p for p in c['pedidos_venda'] if p['status'] != 'pendente'][-5:][::-1],
            'convocacoes': c['convocacoes'][-8:][::-1], 'sequencias': c['protestos'][-5:][::-1]}
