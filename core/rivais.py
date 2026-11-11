"""Rivalidades e clássicos: o app reconhece os rivais do clube da carreira pelo nome (os clássicos do futebol
brasileiro e alguns sul-americanos) e trata o jogo contra eles como clássico: pesa mais na torcida, na
diretoria e no vestiário, rende manchete própria, provocação nas redes e faixa no estádio.
Também guarda a data de fundação dos clubes conhecidos, para a faixa de aniversário."""
import unicodedata, datetime as dt


def norm(s):
    s = unicodedata.normalize('NFKD', str(s or '')).encode('ascii', 'ignore').decode().lower()
    return ''.join(c if c.isalnum() else ' ' for c in s).split()


# chave do clube -> formas de reconhecer o nome (todas as palavras de uma forma precisam aparecer)
CLUBES = {
    'palmeiras': [['palmeiras']], 'corinthians': [['corinthians']], 'saopaulo': [['sao', 'paulo']],
    'santos': [['santos']], 'flamengo': [['flamengo']], 'fluminense': [['fluminense']], 'vasco': [['vasco']],
    'botafogo': [['botafogo']], 'gremio': [['gremio']], 'inter': [['internacional'], ['inter']],
    'galo': [['atletico', 'mineiro'], ['atletico', 'mg'], ['atl', 'mineiro'], ['galo']],
    'cruzeiro': [['cruzeiro']], 'america_mg': [['america', 'mineiro'], ['america', 'mg']],
    'bahia': [['bahia']], 'vitoria': [['vitoria']],
    'athletico': [['athletico'], ['atletico', 'paranaense'], ['atletico', 'pr']], 'coritiba': [['coritiba']],
    'sport': [['sport']], 'nautico': [['nautico']], 'santa_cruz': [['santa', 'cruz']],
    'ceara': [['ceara']], 'fortaleza': [['fortaleza']], 'goias': [['goias']],
    'atletico_go': [['atletico', 'goianiense'], ['atletico', 'go']], 'vila_nova': [['vila', 'nova']],
    'ponte': [['ponte', 'preta']], 'guarani': [['guarani']], 'avai': [['avai']], 'figueirense': [['figueirense']],
    'remo': [['remo']], 'paysandu': [['paysandu']], 'crb': [['crb']], 'csa': [['csa']],
    'juventude': [['juventude']], 'caxias': [['caxias']], 'bragantino': [['bragantino']], 'cuiaba': [['cuiaba']],
    'chapecoense': [['chapecoense']], 'criciuma': [['criciuma']],
    'boca': [['boca', 'juniors'], ['boca']], 'river': [['river', 'plate'], ['river']],
    'penarol': [['penarol']], 'nacional_uy': [['nacional']], 'colocolo': [['colo', 'colo']],
    'uchile': [['universidad', 'chile'], ['u', 'chile']],
}

RIVAIS = {
    'palmeiras': ['corinthians', 'saopaulo', 'santos'], 'corinthians': ['palmeiras', 'saopaulo', 'santos'],
    'saopaulo': ['corinthians', 'palmeiras', 'santos'], 'santos': ['corinthians', 'palmeiras', 'saopaulo'],
    'flamengo': ['fluminense', 'vasco', 'botafogo'], 'fluminense': ['flamengo', 'vasco', 'botafogo'],
    'vasco': ['flamengo', 'fluminense', 'botafogo'], 'botafogo': ['flamengo', 'fluminense', 'vasco'],
    'gremio': ['inter'], 'inter': ['gremio'], 'galo': ['cruzeiro', 'america_mg'], 'cruzeiro': ['galo', 'america_mg'],
    'america_mg': ['galo', 'cruzeiro'], 'bahia': ['vitoria'], 'vitoria': ['bahia'], 'athletico': ['coritiba'],
    'coritiba': ['athletico'], 'sport': ['nautico', 'santa_cruz'], 'nautico': ['sport', 'santa_cruz'],
    'santa_cruz': ['sport', 'nautico'], 'ceara': ['fortaleza'], 'fortaleza': ['ceara'],
    'goias': ['vila_nova', 'atletico_go'], 'atletico_go': ['goias', 'vila_nova'], 'vila_nova': ['goias', 'atletico_go'],
    'ponte': ['guarani'], 'guarani': ['ponte'], 'avai': ['figueirense'], 'figueirense': ['avai'],
    'remo': ['paysandu'], 'paysandu': ['remo'], 'crb': ['csa'], 'csa': ['crb'], 'juventude': ['caxias'],
    'caxias': ['juventude'], 'chapecoense': ['criciuma', 'avai'], 'criciuma': ['chapecoense', 'avai', 'figueirense'],
    'boca': ['river'], 'river': ['boca'], 'penarol': ['nacional_uy'], 'nacional_uy': ['penarol'],
    'colocolo': ['uchile'], 'uchile': ['colocolo'],
}

NOME_CLASSICO = {
    frozenset(['palmeiras', 'corinthians']): 'Dérbi', frozenset(['palmeiras', 'saopaulo']): 'Choque-Rei',
    frozenset(['palmeiras', 'santos']): 'Clássico da Saudade', frozenset(['corinthians', 'saopaulo']): 'Majestoso',
    frozenset(['corinthians', 'santos']): 'Clássico Alvinegro', frozenset(['saopaulo', 'santos']): 'San-São',
    frozenset(['flamengo', 'fluminense']): 'Fla-Flu', frozenset(['flamengo', 'vasco']): 'Clássico dos Milhões',
    frozenset(['flamengo', 'botafogo']): 'Clássico da Rivalidade', frozenset(['fluminense', 'vasco']): 'Clássico dos Gigantes',
    frozenset(['fluminense', 'botafogo']): 'Clássico Vovô', frozenset(['vasco', 'botafogo']): 'Clássico da Amizade',
    frozenset(['gremio', 'inter']): 'Gre-Nal', frozenset(['galo', 'cruzeiro']): 'Clássico Mineiro',
    frozenset(['bahia', 'vitoria']): 'Ba-Vi', frozenset(['athletico', 'coritiba']): 'Atletiba',
    frozenset(['sport', 'nautico']): 'Clássico dos Clássicos', frozenset(['ceara', 'fortaleza']): 'Clássico-Rei',
    frozenset(['ponte', 'guarani']): 'Dérbi Campineiro', frozenset(['remo', 'paysandu']): 'Re-Pa',
    frozenset(['goias', 'vila_nova']): 'Clássico Goiano', frozenset(['avai', 'figueirense']): 'Clássico da Ilha',
    frozenset(['juventude', 'caxias']): 'Ca-Ju', frozenset(['crb', 'csa']): 'Clássico das Multidões',
    frozenset(['boca', 'river']): 'Superclásico', frozenset(['penarol', 'nacional_uy']): 'Clásico Uruguayo',
}

# (dia, mês, ano) de fundação, para a faixa de aniversário
FUNDACAO = {
    'palmeiras': (26, 8, 1914), 'corinthians': (1, 9, 1910), 'saopaulo': (25, 1, 1930), 'santos': (14, 4, 1912),
    'flamengo': (17, 11, 1895), 'fluminense': (21, 7, 1902), 'vasco': (21, 8, 1898), 'botafogo': (12, 8, 1904),
    'gremio': (15, 9, 1903), 'inter': (4, 4, 1909), 'galo': (25, 3, 1908), 'cruzeiro': (2, 1, 1921),
    'america_mg': (30, 4, 1912), 'bahia': (1, 1, 1931), 'vitoria': (13, 5, 1899), 'athletico': (26, 3, 1924),
    'coritiba': (12, 10, 1909), 'sport': (13, 5, 1905), 'nautico': (7, 4, 1901), 'santa_cruz': (3, 2, 1914),
    'ceara': (2, 6, 1914), 'fortaleza': (18, 10, 1918), 'goias': (6, 4, 1943), 'atletico_go': (2, 4, 1937),
    'vila_nova': (29, 7, 1943), 'ponte': (11, 8, 1900), 'guarani': (1, 4, 1911), 'avai': (1, 9, 1923),
    'figueirense': (12, 6, 1921), 'remo': (5, 2, 1905), 'paysandu': (2, 2, 1914), 'juventude': (29, 6, 1913),
    'bragantino': (8, 1, 1928), 'cuiaba': (12, 12, 2001), 'chapecoense': (10, 5, 1973), 'criciuma': (13, 5, 1947),
    'boca': (3, 4, 1905), 'river': (25, 5, 1901),
}


# palavras que podem aparecer junto do nome sem mudar o clube ("Esporte Clube Vitória", "Vasco da Gama")
GENERICAS = set('fc ec sc se ac cr cf ca cfc fbc clube club de do da dos e esporte esportiva esportivo futebol foot ball '
                'regatas sport sporting sociedade associacao atletico athletic paulista paranaense recife gama porto '
                'alegrense red bull rj mg pr ba ce go pe rs s c a f r j u'.split())


def chave(nome):
    """Chave do clube conhecido a partir do nome que vem do jogo (ex.: 'FLUMINENSE', 'Atlético Mineiro')."""
    pal = set(norm(nome))
    if not pal:
        return None
    melhor, tam = None, 0
    for k, formas in CLUBES.items():
        for f in formas:
            # todas as palavras da forma aparecem e as que sobram são genéricas ("Santos Laguna" não é o Santos)
            if all(p in pal for p in f) and not (pal - set(f) - GENERICAS) and len(f) > tam:
                melhor, tam = k, len(f)
    # "Botafogo SP" e "Nacional" de outros países não são os clubes do mapa
    if melhor == 'botafogo' and 'sp' in pal:
        return None
    return melhor


def rivais(clube, nomes, manual=None):
    """ids dos rivais do clube entre os times conhecidos do jogo (dicionário id -> nome).
    Rivais escolhidos à mão na tela do app valem junto."""
    k = chave(clube)
    alvo = set(RIVAIS.get(k, []))
    out = []
    for tid, n in (nomes or {}).items():
        ck = chave(n)
        if ck and ck in alvo and ck != k:
            out.append(int(tid))
    for t in manual or []:
        if int(t) not in out:
            out.append(int(t))
    return out


def nome_classico(clube, adv):
    a, b = chave(clube), chave(adv)
    if a and b:
        return NOME_CLASSICO.get(frozenset([a, b])) or 'Clássico'
    return 'Clássico'


def aniversario(clube, hoje):
    """(anos, data) do aniversário do clube se a data da carreira estiver a até 7 dias dele."""
    f = FUNDACAO.get(chave(clube))
    if not f or not hoje:
        return None
    d, m, a = f
    try:
        este = dt.date(hoje.year, m, d)
    except ValueError:
        return None
    if abs((hoje - este).days) <= 7:
        return hoje.year - a, este
    return None


def retrospecto(partidas, team_id, ids_rivais):
    """V/E/D e os jogos contra cada rival, pelos jogos acumulados do app."""
    out = {}
    for p in partidas:
        adv = p['visitante'] if p['mandante'] == team_id else p['mandante']
        if adv not in ids_rivais:
            continue
        r = out.setdefault(adv, {'V': 0, 'E': 0, 'D': 0, 'jogos': []})
        r[p['res']] += 1
        casa = p['mandante'] == team_id
        gp, gc = (p['gm'], p['gv']) if casa else (p['gv'], p['gm'])
        r['jogos'].append({'data': p['data'], 'gp': gp, 'gc': gc, 'res': p['res'], 'casa': casa})
    for r in out.values():
        r['jogos'] = r['jogos'][-6:][::-1]
    return out
