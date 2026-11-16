"""Torcida e imprensa reagindo ao mercado com os NÚMEROS do jogador (nada de comentário genérico).

Cada reação parte dos fatos do jogador na temporada: gols, assistências, jogos, quantas vezes foi titular,
nota média, cartões, idade e a comparação com quem joga hoje na posição. Fase boa = elogio; fase ruim = crítica;
reforço que não supera o titular = desconfiança; venda de quem vive grande fase = revolta; de quem vai mal = alívio.

Eventos: sondagem (negociação aberta), contratação acertada, negociação fracassada, proposta recebida,
venda aprovada e venda recusada. Tudo vai para state['mundo'] (notícias e redes sociais)."""
import random
from . import vozes
from .sim import _seed
from .textos import FONTES

NOME_POS = {'GL': 'goleiro', 'ZAG': 'zagueiro', 'LD': 'lateral-direito', 'LE': 'lateral-esquerdo', 'VOL': 'volante',
            'MEI': 'meia', 'MD': 'meia pela direita', 'ME': 'meia pela esquerda', 'PD': 'ponta-direita',
            'PE': 'ponta-esquerda', 'ATA': 'atacante'}


def _num(x):
    return f'{x:.1f}'.replace('.', ',')


OFENSIVOS = {'ATA', 'PD', 'PE', 'MEI', 'MD', 'ME'}


def fase(j):
    """'boa', 'ruim', 'normal' ou 'sem_jogos', pelos números da temporada."""
    s = j.get('stats') or {}
    jogos = s.get('jogos') or 0
    if jogos < 3:
        return 'sem_jogos'
    pts = 0
    nota = s.get('nota_media')
    if nota is not None:
        pts += 2 if nota >= 7.0 else 1 if nota >= 6.6 else -2 if nota < 6.0 else -1 if nota < 6.3 else 0
    tit = (s.get('titular') or 0) / jogos
    pts += 1 if tit >= 0.75 else -1 if tit < 0.35 else 0
    if j.get('pos') in OFENSIVOS:
        pg = ((s.get('gols') or 0) + 0.7 * (s.get('assist') or 0)) / jogos
        alvo = 0.45 if j.get('pos') == 'ATA' else 0.3
        pts += 2 if pg >= alvo * 1.4 else 1 if pg >= alvo else -2 if pg < alvo * 0.35 else 0
    return 'boa' if pts >= 2 else 'ruim' if pts <= -2 else 'normal'


def fatos(j, ref=None):
    """Fatos do jogador com sinal: {'bons': [...], 'ruins': [...], 'neutros': [...]}, sempre com números.
    Para defensores e goleiros o assunto é sequência e nota; gols só entram quando contam a favor."""
    s = j.get('stats') or {}
    jogos, tit = s.get('jogos') or 0, s.get('titular') or 0
    g, a = s.get('gols') or 0, s.get('assist') or 0
    nota = s.get('nota_media')
    bons, ruins, neutros = [], [], []
    ofens = j.get('pos') in OFENSIVOS
    if jogos:
        pl = lambda n, w: f'{n} {w}{"s" if n != 1 else ""}'
        ga = f'{pl(g, "gol")} e {pl(a, "assistência")} em {jogos} jogos'
        if ofens:
            pg = (g + 0.7 * a) / jogos
            alvo = 0.45 if j.get('pos') == 'ATA' else 0.3
            (bons if pg >= alvo else ruins if pg < alvo * 0.5 else neutros).append(ga)
        elif g + a >= 2:
            bons.append(f'{pl(g, "gol")} e {pl(a, "assistência")} mesmo sendo {NOME_POS.get(j.get("pos"), "defensor")}')
        if nota is not None:
            (bons if nota >= 6.8 else ruins if nota < 6.2 else neutros).append(f'nota média {_num(nota)}')
        if tit / jogos >= 0.75:
            bons.append(f'titular em {tit} de {jogos} jogos')
        elif tit / jogos < 0.4:
            ruins.append(f'só {tit} jogos como titular em {jogos}')
        else:
            neutros.append(f'{tit} jogos como titular em {jogos}')
        cart = (s.get('amarelos') or 0) + 3 * (s.get('vermelhos') or 0)
        if cart >= 6:
            ruins.append(f'{s.get("amarelos", 0)} amarelos e {s.get("vermelhos", 0)} vermelhos')
    else:
        ruins.append('quase não entrou em campo na temporada')
    f = {'bons': bons, 'ruins': ruins, 'neutros': neutros, 'idade': j.get('idade')}
    if ref and ref.get('cgj') and j.get('cgj'):
        d = j['cgj'] - ref['cgj']
        f['comp'] = (f'CGJ {j["cgj"]}, {d} acima do {ref["nome"]}' if d > 0 else
                     f'CGJ {j["cgj"]}, abaixo do {ref["nome"]} ({ref["cgj"]})' if d < 0 else
                     f'mesmo CGJ do {ref["nome"]} ({j["cgj"]})')
        f['melhora'] = d > 0
    return f


def _juntar(partes):
    partes = [p for p in partes if p]
    if not partes:
        return ''
    return partes[0] if len(partes) == 1 else ', '.join(partes[:-1]) + ' e ' + partes[-1]


def _do_lado(ff, fs):
    """Fatos que combinam com a fase: elogio cita os bons, crítica cita os ruins."""
    if fs == 'boa':
        return ff['bons'] or ff['neutros']
    if fs == 'ruim':
        return ff['ruins'] or ff['neutros']
    return ff['neutros'] + ff['bons'][:1] + ff['ruins'][:1]


# ---------------------------------------------------------------- textos (sempre com números)
def _manchete(evento, j, fs, clube, ff, r):
    n, origem = j['nome'], j.get('clube') or 'sem clube'
    pos = NOME_POS.get(j.get('pos'), 'jogador')
    lado = _juntar(_do_lado(ff, fs)[:2])
    comp = j.get('comprador')
    if evento == 'sondagem':
        if fs == 'boa':
            return r.choice([f'{clube} sonda {n}, destaque do {origem}: {lado}',
                             f'Em alta no {origem} ({lado}), {n} entra na mira do {clube}'])
        if fs == 'ruim':
            return r.choice([f'{clube} sonda {n}, que vive fase ruim no {origem}: {lado}',
                             f'Interesse do {clube} no {pos} {n} surpreende: {lado}'])
        if fs == 'sem_jogos':
            return f'{clube} sonda {n}, {pos} do {origem} que quase não jogou na temporada'
        return f'{clube} consulta o {origem} sobre o {pos} {n} ({lado})'
    if evento == 'acertada':
        if fs == 'boa':
            return f'Reforço: {clube} acerta com {n}, que chega do {origem} com {lado}'
        if fs == 'ruim':
            return f'{clube} fecha com {n} mesmo após temporada fraca no {origem} ({lado})'
        return f'{clube} acerta a contratação do {pos} {n}, do {origem}' + (f' ({lado})' if lado else '')
    if evento == 'fracassou':
        return (f'{clube} perde a disputa por {n}, que tem {lado} no {origem}' if fs == 'boa' else
                f'Negociação entre {clube} e {n} não avança' + (f' ({lado})' if lado else ''))
    if evento == 'proposta':
        return (f'{comp} quer tirar {n} do {clube} no melhor momento: {lado}' if fs == 'boa' else
                f'{comp} faz proposta por {n}, do {clube}' + (f' ({lado})' if lado else ''))
    if evento == 'venda':
        if fs == 'boa':
            return f'{clube} aceita vender {n} em plena boa fase ({lado}) para o {comp}'
        if fs == 'ruim':
            return f'{clube} libera {n} para o {comp} após temporada abaixo ({lado})'
        return f'{n} deixa o {clube} rumo ao {comp}' + (f' ({lado})' if lado else '')
    if evento == 'recusa':
        return (f'{clube} recusa proposta do {comp} e segura {n} ({lado})' if fs == 'boa' else
                f'{clube} recusa proposta do {comp} por {n}' + (f', mesmo com {lado}' if fs == 'ruim' and lado else ''))
    return n


def _misto(n, ff, evento):
    """Fase normal: o lado bom e o lado ruim, com os números dos dois."""
    b = (ff['bons'] or ff['neutros'] or [''])[0]
    m = (ff['ruins'] or [''])[0]
    if b and m:
        return f'{n}: {b}, mas {m}. ' + ('pode dar certo' if evento == 'acertada' else 'tenho minhas dúvidas')
    return f'{n}: {b or m}. ' + ('vai brigar por posição' if evento == 'acertada' else 'nem empolga nem assusta')


def _posts_texto(evento, j, fs, clube, ff, r):
    """Textos de torcedores (3 a 4), cada um com um fato do jogador que combina com a fase."""
    n = j['nome']
    fx = list(_do_lado(ff, fs)) or ['pouco tempo de campo']
    if fs == 'normal' and evento in ('fracassou', 'venda') and ff['ruins']:
        fx = list(ff['ruins'])          # alívio cita o que ia mal
    elif fs == 'normal' and evento in ('recusa', 'proposta') and ff['bons']:
        fx = list(ff['bons'])
    r.shuffle(fx)
    f1, f2 = fx[0], fx[1 % len(fx)]
    comp, idade = ff.get('comp'), ff.get('idade')
    t = []
    if evento == 'sondagem':
        t += {'boa': [f'{n}? {f1}. pode trazer ontem', f'{f1} no {j.get("clube")}. esse chega pra ser titular',
                      f'finalmente olhando quem tá voando: {f2}'],
              'ruim': [f'{n}?? {f1}. sério isso?', f'{f1} e querem trazer pro {clube}. não dá',
                       f'a gente precisa de reforço, não de aposta. {f2}'],
              }.get(fs, [_misto(n, ff, 'sondagem'), f'{n}: {f1}. vamos ver o que a diretoria acha'])
    elif evento == 'acertada':
        t += {'boa': [f'CHEGOU! {f1}. bem-vindo, {n}', f'{f2}. contratação de peso', f'quero ver o {n} repetir aqui: {f1}'],
              'ruim': [f'fecharam mesmo com o {n}... {f1}', f'{f2}. espero estar errado', f'{f1}. dinheiro jogado fora?'],
              }.get(fs, [_misto(n, ff, 'acertada'), f'{n} fechado. {f1}. vai brigar por posição'])
    elif evento == 'fracassou':
        t += ([f'perdemos o {n} com {f1}. diretoria lenta demais', f'{f2} e deixaram escapar'] if fs == 'boa' else
              [f'ainda bem que não veio. {f1}', f'{n} com {f2}? livramento'])
    elif evento == 'proposta':
        t += ([f'vender o {n} com {f1}? nem pensar', f'{f2}. é dos melhores do time, não vende'] if fs == 'boa' else
              [f'{n}: {f1}. se pagarem bem, pode ir', f'{f2}... ouve a proposta pelo menos'] if fs == 'ruim' else
              [f'{n}: {f1}. depende do valor', f'{f2}. dá pra repor se vier dinheiro bom'])
    elif evento == 'venda':
        t += ([f'venderam o {n} com {f1}. inacreditável', f'quem vai fazer o que o {n} faz? {f2}',
               f'vender o {n} com {f1} e trazer quem no lugar?'] if fs == 'boa' else
              [f'{n} vendido. {f1}. foi tarde', f'boa venda. {f2}', f'{f1}... agora usa o dinheiro pra trazer alguém que jogue'] if fs == 'ruim' else
              [f'{n} vendido. {f1}', f'{f2}. tomara que reponham à altura'])
    elif evento == 'recusa':
        t += ([f'segurou o {n}! {f1}', f'fez certo: {f2}, não se vende nessa fase'] if fs == 'boa' else
              [f'recusou proposta pelo {n} com {f1}? não entendi', f'{f2} e não quis vender...'])
    if comp and evento in ('sondagem', 'acertada'):
        t.append(f'{comp}. ' + ('aí sim, melhora o time' if ff.get('melhora') else
                               'mesmo nível, serve pra compor o elenco' if 'mesmo CGJ' in comp else
                               'pra que trazer alguém pior do que já temos?'))
    if idade and evento in ('sondagem', 'acertada'):
        if idade >= 32:
            t.append(f'{idade} anos... contrato curto, por favor')
        elif idade <= 21:
            t.append(f'{idade} anos e já {f1 if fs == "boa" else "no profissional"}. tem muito pra evoluir')
    r.shuffle(t)
    return t[:r.randint(3, 4)]


def _materia(evento, j, fs, clube, ff, r):
    """Corpo da matéria (3 parágrafos) e o debate dos jornalistas, tudo em cima dos números."""
    n, origem, comp = j['nome'], j.get('clube') or 'sem clube', j.get('comprador')
    pos = NOME_POS.get(j.get('pos'), 'jogador')
    s = j.get('stats') or {}
    bons, ruins = ff['bons'], ff['ruins']
    linha = _juntar(ff['bons'] + ff['neutros'] + ff['ruins'])
    p = []
    if evento in ('sondagem', 'acertada', 'fracassou'):
        abre = {'sondagem': f'O {clube} fez consultas pelo {pos} {n}, do {origem}.',
                'acertada': f'O {clube} acertou a contratação do {pos} {n}, que estava no {origem}.',
                'fracassou': f'A tentativa do {clube} de contratar {n}, do {origem}, não deu certo.'}[evento]
        p.append(abre + (f' Na temporada, ele soma {linha}.' if linha else ' Ele quase não jogou na temporada.'))
        if ff.get('comp'):
            p.append(f'Pela avaliação interna, o reforço tem {ff["comp"]}, ' +
                     ('o que explica o interesse da comissão técnica.' if ff.get('melhora') else
                      'e por isso há quem questione o que ele acrescenta ao elenco.'))
        if j.get('idade'):
            p.append(f'Aos {j["idade"]} anos, ' + ('é visto como aposta para o futuro.' if j['idade'] <= 22 else
                     'chegaria para resolver de imediato, num contrato mais curto.' if j['idade'] >= 31 else
                     'está na idade em que costuma render o melhor futebol.'))
    else:
        abre = {'proposta': f'O {comp} apresentou proposta ao {clube} por {n}.',
                'venda': f'O {clube} aceitou vender {n} ao {comp}.',
                'recusa': f'O {clube} recusou a proposta do {comp} por {n}.'}[evento]
        p.append(abre + (f' O {pos} tem {linha} na temporada.' if linha else ''))
        if s.get('jogos'):
            p.append(f'Com {s.get("titular", 0)} jogos como titular em {s["jogos"]}, ' +
                     ('é peça de confiança do técnico, e a saída abriria um buraco no time.' if fs == 'boa' else
                      'perdeu espaço, e a negociação é vista como natural.' if fs == 'ruim' else
                      'divide a posição, e o elenco tem opções para repor.'))
    deb = []
    if bons:
        deb += [f'Os números falam por ele: {_juntar(bons[:2])}. ' + ('Contratação certa.' if evento in ('sondagem', 'acertada') else
                'Vender agora é erro.' if evento in ('proposta', 'venda') else 'Fez bem em segurar.' if evento == 'recusa' else 'Perdeu um bom jogador.'),
                f'Eu olho {bons[0]} e vejo um jogador em ascensão.']
    if ruins:
        deb += [f'Não dá para ignorar: {_juntar(ruins[:2])}. ' + ('Não convence.' if evento in ('sondagem', 'acertada') else
                'Pode vender sem medo.' if evento in ('proposta', 'venda') else 'Não entendo segurar.' if evento == 'recusa' else 'Não fez falta.'),
                f'Com {ruins[0]}, eu teria dúvidas.']
    if ff.get('comp'):
        deb.append(f'A conta que importa: {ff["comp"]}. ' + ('Melhora o time.' if ff.get('melhora') else 'Não melhora o time titular.'))
    if j.get('idade') and evento in ('sondagem', 'acertada'):
        deb.append(f'{j["idade"]} anos pesa na decisão. ' + ('Tem margem para crescer.' if j['idade'] <= 22 else
                   'Tem prazo de validade.' if j['idade'] >= 31 else 'Idade boa.'))
    return p, deb[:4] if len(deb) >= 2 else []


def _humor(evento, fs):
    bom = {('sondagem', 'boa'), ('acertada', 'boa'), ('recusa', 'boa'), ('venda', 'ruim'), ('proposta', 'ruim')}
    ruim = {('sondagem', 'ruim'), ('acertada', 'ruim'), ('fracassou', 'boa'), ('venda', 'boa'), ('proposta', 'boa'),
            ('recusa', 'ruim')}
    return 'feliz' if (evento, fs) in bom else 'irritado' if (evento, fs) in ruim else 'neutro'


DELTA_TORCIDA = {'feliz': 2, 'irritado': -2, 'neutro': 0}


def reagir(state, evento, j, data, clube, ref=None):
    """Publica a notícia e os posts da torcida sobre o jogador. j: dados do jogador (com stats e momento);
    para vendas, j também tem 'comprador'. ref: titular atual da posição {nome, cgj}."""
    m = state.setdefault('mundo', {})
    m.setdefault('noticias', [])
    m.setdefault('posts', [])
    r = random.Random(_seed('reacao', evento, j.get('id'), data))
    fs = fase(j)
    ff = fatos(j, ref)
    titulo = _manchete(evento, j, fs, clube, ff, r)
    corpo, debate = _materia(evento, j, fs, clube, ff, r)
    m['noticias'].append({'data': data, 'titulo': titulo, 'tipo': 'transferencia', 'fonte': r.choice(FONTES),
                          'destaque': evento in ('acertada', 'venda'), 'jogador': j['nome'],
                          'corpo': corpo, **({'debate': debate} if debate else {})})
    m['noticias'] = m['noticias'][-200:]
    humor = _humor(evento, fs)
    perfis = vozes.torcedores(clube)
    ja = {p.get('base') for p in m['posts'][-80:]}
    textos = [x for x in _posts_texto(evento, j, fs, clube, ff, r) if x not in ja]
    for (autor, nome), txt in zip(r.sample(perfis, min(len(perfis), len(textos))), textos):
        cur = int(r.randint(40, 700) * (1 + r.paretovariate(1.6)))
        m['posts'].append({'data': data, 'autor': autor, 'nome': nome, 'texto': vozes.humanizar(txt, r), 'base': txt,
                           'humor': 'mercado', 'tema': 'mercado_' + humor, 'curtidas': cur,
                           'reposts': int(cur * r.uniform(0.03, 0.3)), 'respostas': [], 'jogador': j['nome']})
    m['posts'] = m['posts'][-300:]
    if 'torcida' in m:
        m['torcida'] = max(0, min(100, m['torcida'] + DELTA_TORCIDA[humor]))
    return {'titulo': titulo, 'fase': fs, 'humor': humor, 'posts': textos}
