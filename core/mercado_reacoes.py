"""Torcida e imprensa reagindo ao mercado com os NÚMEROS do jogador (nada de comentário genérico).

Cada reação parte dos fatos do jogador na temporada: gols, assistências, jogos, quantas vezes foi titular,
nota média, cartões, idade e a comparação com quem joga hoje na posição. Fase boa = elogio; fase ruim = crítica;
reforço que não supera o titular = desconfiança; venda de quem vive grande fase = revolta; de quem vai mal = alívio.

Eventos: sondagem (negociação aberta), contratação acertada, negociação fracassada, proposta recebida,
venda aprovada e venda recusada. Tudo vai para state['mundo'] (notícias e redes sociais)."""
import random
from . import vozes, mercado_torcida
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
    """Manchete da imprensa: cita os números que combinam com a fase."""
    n, origem = j['nome'], j.get('clube') or 'sem clube'
    pos = NOME_POS.get(j.get('pos'), 'jogador')
    lado = _juntar(_do_lado(ff, fs)[:2]) or 'pouco tempo em campo'
    comp = j.get('comprador') or 'outro clube'
    M = {
        ('sondagem', 'boa'): [f'{clube} sonda {n}, destaque do {origem}: {lado}',
                              f'Em alta no {origem} ({lado}), {n} entra na mira do {clube}',
                              f'{clube} monitora {n}; {pos} tem {lado} na temporada',
                              f'Exclusivo: {clube} faz primeiro contato por {n} ({lado})',
                              f'{n} vira prioridade do {clube} depois de {lado}'],
        ('sondagem', 'ruim'): [f'{clube} sonda {n}, que vive fase ruim no {origem}: {lado}',
                               f'Interesse do {clube} no {pos} {n} surpreende: {lado}',
                               f'{clube} avalia {n} apesar de {lado}',
                               f'Aposta? {clube} consulta {n}, com {lado} no {origem}'],
        ('sondagem', 'normal'): [f'{clube} consulta o {origem} sobre o {pos} {n} ({lado})',
                                 f'{n} aparece na lista do {clube}; {pos} tem {lado}',
                                 f'{clube} pede informações sobre {n}, do {origem}'],
        ('sondagem', 'sem_jogos'): [f'{clube} sonda {n}, {pos} do {origem} que quase não jogou na temporada',
                                    f'Sem espaço no {origem}, {n} entra no radar do {clube}'],
        ('acertada', 'boa'): [f'Reforço: {clube} acerta com {n}, que chega do {origem} com {lado}',
                              f'É do {clube}! {n} chega embalado por {lado}',
                              f'{clube} fecha com {n}, um dos destaques do {origem} ({lado})',
                              f'Negócio fechado: {n} troca o {origem} pelo {clube}'],
        ('acertada', 'ruim'): [f'{clube} fecha com {n} mesmo após temporada fraca no {origem} ({lado})',
                               f'{clube} aposta em {n}, que tem {lado} no {origem}',
                               f'Contratação de {n} divide opiniões: {lado}'],
        ('acertada', 'normal'): [f'{clube} acerta a contratação do {pos} {n}, do {origem} ({lado})',
                                 f'{n} é o novo reforço do {clube}; {pos} tem {lado}',
                                 f'{clube} confirma acerto com {n} para a disputa da posição'],
        ('fracassou', 'boa'): [f'{clube} perde a disputa por {n}, que tem {lado} no {origem}',
                               f'Negociação esfria e {n} ({lado}) não vem para o {clube}',
                               f'{origem} segura {n} e frustra o {clube}'],
        ('fracassou', 'ruim'): [f'Negociação entre {clube} e {n} não avança ({lado})',
                                f'{clube} desiste de {n} após {lado}'],
        ('fracassou', 'normal'): [f'{clube} e {n} não chegam a acordo ({lado})',
                                  f'Sem acerto, {n} segue no {origem}'],
        ('proposta', 'boa'): [f'{comp} quer tirar {n} do {clube} no melhor momento: {lado}',
                              f'{comp} faz proposta por {n}, destaque do {clube} ({lado})',
                              f'Assédio: {comp} mira {n} depois de {lado}'],
        ('proposta', 'ruim'): [f'{comp} faz proposta por {n}, que tem {lado} no {clube}',
                               f'{n}, em baixa no {clube} ({lado}), recebe proposta do {comp}'],
        ('proposta', 'normal'): [f'{comp} faz proposta por {n}, do {clube} ({lado})',
                                 f'{clube} recebe oferta do {comp} por {n}'],
        ('venda', 'boa'): [f'{clube} aceita vender {n} em plena boa fase ({lado}) para o {comp}',
                           f'{n} deixa o {clube} no auge: {lado}',
                           f'Venda polêmica: {clube} libera {n} ({lado}) ao {comp}'],
        ('venda', 'ruim'): [f'{clube} libera {n} para o {comp} após temporada abaixo ({lado})',
                            f'Sem espaço, {n} ({lado}) é vendido ao {comp}'],
        ('venda', 'normal'): [f'{n} deixa o {clube} rumo ao {comp} ({lado})',
                              f'{clube} acerta a venda de {n} ao {comp}'],
        ('recusa', 'boa'): [f'{clube} recusa proposta do {comp} e segura {n} ({lado})',
                            f'"Inegociável": {clube} diz não ao {comp} por {n}, que tem {lado}'],
        ('recusa', 'ruim'): [f'{clube} recusa proposta do {comp} por {n}, mesmo com {lado}',
                             f'{clube} diz não ao {comp} e mantém {n}, apesar de {lado}'],
        ('recusa', 'normal'): [f'{clube} recusa oferta do {comp} por {n} ({lado})'],
    }
    ops = M.get((evento, fs)) or M.get((evento, 'normal')) or [n]
    return r.choice(ops)


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
    compra = evento in ('sondagem', 'acertada')
    venda = evento in ('proposta', 'venda')
    if bons:
        deb += [r.choice([f'O que me chama a atenção é {bons[0]}. Isso não é acaso.',
                          f'Com {bons[0]}, qualquer clube grande olharia para ele.',
                          f'{bons[0].capitalize()}. Os números estão do lado dele.'])]
        if compra:
            deb.append(r.choice(['O torcedor pode ficar animado: chega para jogar.', 'É reforço de verdade, não de elenco.']))
        if venda:
            deb.append(r.choice(['Vender agora é abrir mão do momento.', 'Quem vai substituir isso no meio da temporada?']))
    if ruins:
        deb += [r.choice([f'Mas tem um porém: {ruins[0]}.', f'Eu fico com o pé atrás por causa de {ruins[0]}.',
                          f'{ruins[0].capitalize()}. Isso pesa.'])]
        if compra:
            deb.append(r.choice(['Não sei se resolve o problema do time.', 'É uma aposta, e aposta às vezes dá errado.']))
        if venda:
            deb.append(r.choice(['Para mim, é um bom momento para negociar.', 'Se o dinheiro for bom, não tem o que discutir.']))
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
    r.shuffle(deb)
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
    textos = mercado_torcida.posts(evento, fs, j, ff, clube, r, OFENSIVOS, ja)
    for (autor, nome), txt in zip(r.sample(perfis, min(len(perfis), len(textos))), textos):
        cur = int(r.randint(40, 700) * (1 + r.paretovariate(1.6)))
        m['posts'].append({'data': data, 'autor': autor, 'nome': nome, 'texto': vozes.humanizar(txt, r), 'base': txt,
                           'humor': 'mercado', 'tema': 'mercado_' + humor, 'curtidas': cur,
                           'reposts': int(cur * r.uniform(0.03, 0.3)), 'respostas': [], 'jogador': j['nome']})
    m['posts'] = m['posts'][-300:]
    if 'torcida' in m:
        m['torcida'] = max(0, min(100, m['torcida'] + DELTA_TORCIDA[humor]))
    return {'titulo': titulo, 'fase': fs, 'humor': humor, 'posts': textos}
