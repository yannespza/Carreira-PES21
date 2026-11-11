"""Vestiário vivo: clima do grupo (0 a 100), capitão, ídolo e panelinhas.

O clima sobe com vitórias e um capitão forte e cai com derrotas, indisciplina e técnico que expõe os jogadores
na coletiva. Com clima ruim surgem reclamações de barrados, panelinhas e racha; com clima bom, o grupo se
fecha. Os efeitos aparecem na moral do app (a seta com o ponto branco no cartão do jogador)."""
import random
from .sim import d2s, s2d, _seed
from .gestao import moral_ajuste


def _v(state):
    g = state.setdefault('gestao', {})
    v = g.setdefault('vestiario', {})
    v.setdefault('clima', 65)
    v.setdefault('eventos', [])
    v.setdefault('panelinhas', [])
    return v


def clima(state):
    return _v(state)['clima']


def mexer(state, delta, motivo=None, data=None):
    v = _v(state)
    cap = v.get('capitao')
    if delta < 0 and cap:      # capitão segura parte do baque
        delta = delta * 0.75
    try:
        from . import estrutura
        if delta < 0 and estrutura.nivel(state, 'ct') >= 4:
            delta *= 0.85
    except Exception:
        pass
    v['clima'] = int(max(0, min(100, round(v['clima'] + delta))))
    if motivo and data:
        v.setdefault('hist', []).append([data, v['clima'], motivo])
        v['hist'] = v['hist'][-80:]


def idolo(state):
    """Ídolo da torcida: o jogador mais elogiado nas notícias (do elenco atual)."""
    el = set(state.get('elenco_nomes') or [])
    cont = {}
    for n in (state.get('mundo') or {}).get('noticias', []):
        j = n.get('jogador')
        if j and j in el:
            cont[j] = cont.get(j, 0) + (2 if n.get('tipo') == 'jog_elogio' else -1 if n.get('tipo') == 'jog_critica' else 0)
    if not cont:
        return None
    j, p = max(cont.items(), key=lambda x: x[1])
    return j if p >= 2 else None


def definir_capitao(state, nome, data):
    v = _v(state)
    ant = v.get('capitao')
    v['capitao'] = nome or None
    if nome and nome != ant:
        moral_ajuste(state, nome, 1, data, 'recebeu a braçadeira de capitão', 21)
        if ant:
            moral_ajuste(state, ant, -1, data, 'perdeu a braçadeira de capitão', 14)
            mexer(state, -3, f'troca de capitão ({ant} → {nome})', data)
        _evento(state, data, 'capitao', f'{nome} é o novo capitão',
                f'{nome} recebeu a braçadeira' + (f' no lugar de {ant}.' if ant else '.'), [nome])


def _evento(state, data, tipo, titulo, texto, jogadores, bom=None):
    v = _v(state)
    v['eventos'].append({'data': data, 'tipo': tipo, 'titulo': titulo, 'texto': texto, 'jogadores': jogadores,
                         'bom': bom})
    v['eventos'] = v['eventos'][-60:]


def resultado(state, partida, team_id, classico=False):
    """Cada jogo novo mexe no clima do grupo."""
    d = {'V': 3, 'E': 0, 'D': -3}[partida['res']] * (2 if classico else 1)
    casa = partida['mandante'] == team_id
    gp, gc = (partida['gm'], partida['gv']) if casa else (partida['gv'], partida['gm'])
    if abs(gp - gc) >= 3:
        d += 2 if gp > gc else -3
    mexer(state, d, ('clássico ' if classico else '') + {'V': 'vitória', 'E': 'empate', 'D': 'derrota'}[partida['res']],
          partida['data'])


def semana(state, dia, elenco, mundo):
    """Uma vez por semana da carreira: acontecimentos do vestiário conforme o clima."""
    if not elenco:
        return
    v = _v(state)
    ds = d2s(dia)
    if v.get('ult') and (dia - s2d(v['ult'])).days < 7:
        return
    v['ult'] = ds
    r = random.Random(_seed('vest', ds, mundo.clube))
    nomes = [j['nome'] for j in elenco if not j['nome'].startswith('Jogador ')]
    if len(nomes) < 5:
        return
    c = v['clima']
    cap = v.get('capitao') if v.get('capitao') in nomes else None
    if v.get('capitao') and not cap:          # capitão saiu do clube
        v['capitao'] = None
    # o clima volta devagar para o meio quando nada acontece
    v['clima'] = int(round(c + (60 - c) * 0.05))
    # panelinhas se desfazem quando o clima melhora
    v['panelinhas'] = [p for p in v['panelinhas'] if c < 55 and all(n in nomes for n in p['jogadores'])]
    if c < 35 and r.random() < 0.35:
        if cap and r.random() < 0.55:
            moral_ajuste(state, '*', 1, ds, f'capitão {cap} reuniu o grupo', 10)
            mexer(state, 8, f'{cap} apagou o incêndio', ds)
            _evento(state, ds, 'capitao_apaga', f'{cap} reúne o elenco', f'O capitão {cap} chamou uma conversa '
                    'só entre os jogadores depois da sequência ruim. O grupo saiu mais fechado.', [cap], True)
            mundo.m['noticias'].append({'data': ds, 'tipo': 'vestiario', 'destaque': False, 'fonte': 'Setorista',
                                        'jogador': cap, 'titulo': f'Capitão {cap} reúne elenco e pede união no {mundo.clube}'})
        else:
            moral_ajuste(state, '*', -1, ds, 'vestiário rachado', 14)
            mexer(state, -4, 'racha no vestiário', ds)
            _evento(state, ds, 'racha', 'Vestiário rachado', 'Discussões no treino e grupos separados no '
                    'refeitório. A comissão técnica tenta contornar.', [], False)
            mundo.noticia('vestiario_racha', ds, r, destaque=True)
            mundo._torcida(-2)
    elif c < 45 and r.random() < 0.3 and not any(e['tipo'] == 'reclamacao' and (dia - s2d(e['data'])).days < 28
                                                  for e in v['eventos']):
        j = r.choice(nomes)
        moral_ajuste(state, j, -1, ds, 'reclamou de falta de espaço', 14)
        mexer(state, -2, f'{j} reclamou nas redes', ds)
        _evento(state, ds, 'reclamacao', f'{j} reclama de falta de espaço', f'{j} publicou uma indireta nas redes '
                'depois de ficar fora do time. A diretoria pediu explicações.', [j], False)
        arroba = '@' + ''.join(ch for ch in j.lower() if ch.isalnum())[:15]
        mundo.m['posts'].append({'data': ds, 'autor': arroba, 'texto': r.choice([
            'Trabalho todo dia calado. Cada um sabe o que faz. 🙏', 'Quem me conhece sabe o que eu dou dentro de campo.',
            'Paciência tem limite. Deus sabe de tudo.', 'Sigo trabalhando… mas tem coisa que não dá pra entender.']),
            'humor': 'chateado', 'curtidas': r.randint(3000, 25000), 'reposts': r.randint(300, 4000), 'jogador': j,
            'respostas': mundo._respostas('chateado', r, arroba, mundo._vars({}, r), n=3)})
        mundo.noticia('jog_reclama', ds, r, jogador=j)
        mundo.m['noticias'][-1]['jogador'] = j
    elif c < 50 and not v['panelinhas'] and r.random() < 0.25:
        p = r.sample(nomes, 3)
        v['panelinhas'].append({'data': ds, 'jogadores': p})
        _evento(state, ds, 'panelinha', 'Panelinha no elenco', f'{", ".join(p[:-1])} e {p[-1]} formaram um grupo '
                'fechado e pouco se misturam com o resto do elenco.', p, False)
        mexer(state, -2, 'panelinha', ds)
    elif c >= 78 and r.random() < 0.3:
        moral_ajuste(state, '*', 1, ds, 'grupo unido', 10)
        _evento(state, ds, 'unido', 'Grupo fechado', r.choice([
            'Churrasco do elenco no fim de semana, organizado pelos mais experientes.',
            'Os jogadores gravaram um vídeo dançando no vestiário que viralizou entre a torcida.',
            'Elenco faz vaquinha para ajudar funcionários do CT. Clima leve nos treinos.']), [], True)
        mundo.noticia('vestiario_unido', ds, r)
        mundo._torcida(1)


def coletiva(state, estilo, data):
    """O que o técnico diz na coletiva também chega ao vestiário."""
    d = {'expor': -6, 'proteger': 4, 'culpa': 3, 'provocar': 1, 'humilde': 1, 'corporativo': 0, 'arbitragem': 1,
         'pressao': -2}.get(estilo, 0)
    if d:
        mexer(state, d, {'expor': 'técnico expôs jogadores na coletiva', 'proteger': 'técnico protegeu o grupo',
                         'culpa': 'técnico assumiu a culpa', 'pressao': 'técnico cobrou reforços em público'}.get(estilo,
                                                                                                         'coletiva'), data)
    if estilo == 'expor':
        moral_ajuste(state, '*', -1, data, 'exposto pelo técnico na coletiva', 7)
    elif estilo == 'proteger':
        moral_ajuste(state, '*', 1, data, 'técnico protegeu o grupo', 7)


def view(state):
    v = _v(state)
    return {'clima': v['clima'], 'capitao': v.get('capitao'), 'idolo': idolo(state),
            'panelinhas': v['panelinhas'], 'eventos': v['eventos'][-25:][::-1], 'hist': v.get('hist', [])[-30:]}
