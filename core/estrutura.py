"""Estrutura do clube e valor da marca.

Departamentos (nível 1 a 5) que você melhora pagando com o orçamento de transferências do save:
- Departamento médico: lesões duram menos;
- Centro de treinamento: menos lesões no treino e vestiário mais tranquilo;
- Manutenção do gramado: o gramado de casa se recupera mais rápido entre os jogos;
- Marketing: a marca do clube cresce mais e atrai patrocinadores melhores.
Cada melhoria vira uma obra com prazo; o efeito vale quando a obra termina.

Valor da marca (0 a 100): sobe com títulos, acessos, campanhas boas e torcida feliz; cai com rebaixamento.
Ela entra na atratividade para os patrocinadores e destrava investidas de empresas maiores."""
import datetime as dt
from .sim import d2s, s2d, fmt_eur

DEPTOS = {
    'medico': {'nome': 'Departamento médico', 'icone': '🩺',
               'efeito': ['lesões 25% mais longas', 'lesões no tempo normal', 'lesões 15% mais curtas',
                          'lesões 28% mais curtas', 'lesões 40% mais curtas']},
    'ct': {'nome': 'Centro de treinamento', 'icone': '🏋️',
           'efeito': ['30% mais lesões no treino', 'risco normal no treino', '15% menos lesões no treino',
                      '30% menos lesões e vestiário mais calmo', '45% menos lesões e vestiário mais calmo']},
    'gramado': {'nome': 'Manutenção do gramado', 'icone': '🌱',
                'efeito': ['gramado se recupera devagar', 'recuperação normal', 'recuperação 30% mais rápida',
                           'recuperação 60% mais rápida', 'recuperação no dobro da velocidade']},
    'marketing': {'nome': 'Marketing', 'icone': '📣',
                  'efeito': ['marca -2 na atratividade', 'sem bônus', 'marca +2 na atratividade',
                             'marca +4 na atratividade', 'marca +6 na atratividade']},
}
ORDEM = ['medico', 'ct', 'gramado', 'marketing']
DURACAO_LESAO = [1.25, 1.0, 0.85, 0.72, 0.6]
RISCO_TREINO = [1.3, 1.0, 0.85, 0.7, 0.55]
RECUP_GRAMADO = [0.6, 1.0, 1.3, 1.6, 2.0]
BONUS_MKT = [-2, 0, 2, 4, 6]
# custo para ir ao próximo nível (do 1 para o 2, ..., do 4 para o 5), em euros, antes do ajuste pelo porte do clube
CUSTO = [1_500_000, 3_000_000, 5_500_000, 9_000_000]
OBRA_DIAS = [21, 35, 50, 70]


def _e(state):
    e = state.setdefault('estrutura', {})
    base = 3 if state.get('atr_base', 60) >= 75 else 2
    for k in ORDEM:
        e.setdefault(k, {'nivel': base})
    return e


def nivel(state, k):
    """Nível em vigor (a obra em andamento ainda não conta)."""
    return _e(state)[k]['nivel']


def custo(state, k):
    n = nivel(state, k)
    if n >= 5:
        return None
    porte = 0.6 + state.get('atr_base', 60) / 100 * 0.8
    return int(round(CUSTO[n - 1] * porte / 100_000) * 100_000)


def duracao_lesao(state):
    return DURACAO_LESAO[nivel(state, 'medico') - 1]


def risco_treino(state):
    return RISCO_TREINO[nivel(state, 'ct') - 1]


def recup_gramado(state):
    return RECUP_GRAMADO[nivel(state, 'gramado') - 1]


def investir(state, k, hoje):
    """Começa a obra: o valor sai do orçamento de transferências do save (débito pendente, aplicado na
    próxima gravação segura) e o novo nível vale quando a obra termina."""
    if k not in DEPTOS:
        raise ValueError('Departamento desconhecido.')
    e = _e(state)
    if e[k].get('obra'):
        raise ValueError('Já tem uma obra em andamento nesse departamento.')
    c = custo(state, k)
    if c is None:
        raise ValueError('Esse departamento já está no nível máximo.')
    orc = (state.get('dinheiro') or {}).get('orc_transf')
    if orc is not None and orc < c:
        raise ValueError(f'O orçamento de transferências ({fmt_eur(orc)}) não cobre a obra ({fmt_eur(c)}).')
    n = e[k]['nivel']
    fim = hoje + dt.timedelta(days=OBRA_DIAS[n - 1])
    e[k]['obra'] = {'para': n + 1, 'inicio': d2s(hoje), 'fim': d2s(fim), 'custo': c}
    state.setdefault('debitos', []).append({'id': f"deb{len(state.get('debitos', [])) + 1}", 'data': d2s(hoje),
                                            'valor': c, 'status': 'pendente',
                                            'motivo': f"Obra: {DEPTOS[k]['nome']} nível {n + 1}"})
    return e[k]['obra']


def avancar(state, hoje, mundo=None):
    """Termina as obras cujo prazo passou."""
    if not hoje:
        return
    for k, d in _e(state).items():
        o = d.get('obra')
        if o and s2d(o['fim']) <= hoje:
            d['nivel'] = o['para']
            d.pop('obra')
            d.setdefault('historico', []).append({'data': o['fim'], 'nivel': o['para'], 'custo': o['custo']})
            if mundo is not None:
                mundo.m['noticias'].append({'data': o['fim'], 'tipo': 'estrutura', 'destaque': o['para'] >= 4,
                                            'fonte': 'Site oficial',
                                            'titulo': f"{mundo.clube} entrega obra: {DEPTOS[k]['nome'].lower()} chega ao nível {o['para']}"})
                mundo._torcida(1)


# ---------------- marca ----------------
def marca(state):
    """Valor da marca de 0 a 100 a partir da história da carreira no app."""
    g = state.get('gestao') or {}
    base = state.get('atr_base', 60)
    tit = len(g.get('titulos', []))
    temps = g.get('temporadas', [])
    ac = sum(1 for t in temps if t.get('acesso'))
    reb = sum(1 for t in temps if t.get('rebaixado'))
    torc = (state.get('mundo') or {}).get('torcida', 60)
    mkt = BONUS_MKT[nivel(state, 'marketing') - 1]
    v = base + 6 * tit + 4 * ac - 9 * reb + (torc - 60) / 4 + mkt
    return int(max(5, min(100, round(v))))


def bonus_atratividade(state):
    """Quanto a marca soma (ou tira) da atratividade calculada pelos resultados."""
    m = marca(state)
    return int(round((m - state.get('atr_base', 60)) / 3)) + BONUS_MKT[nivel(state, 'marketing') - 1]


def view(state, hoje):
    e = _e(state)
    out = []
    for k in ORDEM:
        d = e[k]
        n = d['nivel']
        o = d.get('obra')
        out.append({'id': k, **{x: DEPTOS[k][x] for x in ('nome', 'icone')}, 'nivel': n,
                    'efeito': DEPTOS[k]['efeito'][n - 1],
                    'proximo': DEPTOS[k]['efeito'][n] if n < 5 else None, 'custo': custo(state, k),
                    'obra': o and {**o, 'dias': max(0, (s2d(o['fim']) - hoje).days) if hoje else None},
                    'dias_obra': OBRA_DIAS[n - 1] if n < 5 else None})
    return {'deptos': out, 'marca': marca(state), 'marca_bonus': bonus_atratividade(state),
            'marca_hist': state.get('marca_hist', [])[-30:], 'debitos': state.get('debitos', [])[-12:][::-1]}


def registrar_marca(state, hoje):
    hist = state.setdefault('marca_hist', [])
    m = marca(state)
    if hoje and (not hist or hist[-1][0] != d2s(hoje)):
        hist.append([d2s(hoje), m])
    elif hist:
        hist[-1][1] = m
    state['marca_hist'] = hist[-60:]
