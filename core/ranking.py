"""Ranking real dos clubes (Brasil Série A e B e os principais sul-americanos do jogo).

Nota de 0 a 100 = 45% valor do elenco + 30% torcida + 25% prestígio.
- Valor do elenco (milhões de euros): Série A pelo Transfermarkt (Lance! Biz, janeiro de 2026); Série B e
  sul-americanos: estimativas a partir do Transfermarkt e das listas de Libertadores/Sul-Americana 2026.
- Torcida (0 a 100): Datafolha (novembro de 2024) para os clubes medidos; os outros, estimativa por porte.
- Prestígio (0 a 100): Ranking Nacional de Clubes da CBF 2026 para os brasileiros; títulos continentais e
  tradição para os estrangeiros.
Os times são identificados pelo número de cada um no jogo (kitserver/map.txt do GOGOSZ).

O ranking decide quem procura o técnico: demitido, chegam clubes do tamanho do prestígio dele (ou menores);
em alta, sondam clubes maiores do que o atual."""
import math, random

# id do jogo: (nome, país, liga, valor do elenco em € mi, torcida, prestígio, valor medido?)
CLUBES = {
    # ---- Brasil · Série A 2026 (valor: Transfermarkt jan/2026; prestígio: pontos CBF 2026) ----
    137: ('Palmeiras', 'Brasil', 'Série A', 209.9, 72, 85, True),
    1248: ('Flamengo', 'Brasil', 'Série A', 195.7, 100, 100, True),
    274: ('Cruzeiro', 'Brasil', 'Série A', 156.6, 58, 67, True),
    2453: ('Bahia', 'Brasil', 'Série A', 119.4, 52, 77, True),
    1249: ('Fluminense', 'Brasil', 'Série A', 110.8, 52, 80, True),
    1247: ('Corinthians', 'Brasil', 'Série A', 109.4, 90, 92, True),
    1246: ('Botafogo', 'Brasil', 'Série A', 101.4, 52, 79, True),
    289: ('Atlético Mineiro', 'Brasil', 'Série A', 97.8, 52, 84, True),
    2459: ('Red Bull Bragantino', 'Brasil', 'Série A', 94.6, 25, 60, True),
    136: ('Vasco da Gama', 'Brasil', 'Série A', 94.1, 64, 69, True),
    1254: ('Santos', 'Brasil', 'Série A', 90.6, 58, 54, True),
    1250: ('Grêmio', 'Brasil', 'Série A', 81.4, 64, 65, True),
    1255: ('São Paulo', 'Brasil', 'Série A', 75.0, 69, 83, True),
    1252: ('Internacional', 'Brasil', 'Série A', 63.7, 58, 61, True),
    1930: ('Athletico Paranaense', 'Brasil', 'Série A', 44.4, 42, 78, True),
    1937: ('Vitória', 'Brasil', 'Série A', 35.1, 46, 44, True),
    4077: ('Mirassol', 'Brasil', 'Série A', 31.8, 15, 34, True),
    1931: ('Coritiba', 'Brasil', 'Série A', 25.8, 38, 40, True),
    2697: ('Remo', 'Brasil', 'Série A', 21.6, 40, 23, True),
    4108: ('Chapecoense', 'Brasil', 'Série A', 14.6, 28, 26, True),
    # ---- Brasil · Série B 2026 (valor estimado; prestígio: pontos CBF 2026) ----
    5143: ('Fortaleza', 'Brasil', 'Série B', 30.0, 44, 64, False),
    2454: ('Ceará', 'Brasil', 'Série B', 22.0, 42, 44, False),
    1936: ('Sport', 'Brasil', 'Série B', 20.0, 44, 39, False),
    5142: ('Cuiabá', 'Brasil', 'Série B', 15.0, 18, 41, False),
    5137: ('Juventude', 'Brasil', 'Série B', 14.0, 20, 52, False),
    2450: ('América Mineiro', 'Brasil', 'Série B', 14.0, 24, 46, False),
    1933: ('Goiás', 'Brasil', 'Série B', 13.0, 30, 40, False),
    2451: ('Atlético Goianiense', 'Brasil', 'Série B', 13.0, 22, 46, False),
    5997: ('Novorizontino', 'Brasil', 'Série B', 12.0, 10, 27, False),
    5145: ('Criciúma', 'Brasil', 'Série B', 11.0, 24, 37, False),
    2452: ('Avaí', 'Brasil', 'Série B', 9.0, 24, 28, False),
    2691: ('Vila Nova', 'Brasil', 'Série B', 9.0, 22, 29, False),
    2506: ('CRB', 'Brasil', 'Série B', 8.0, 22, 38, False),
    5433: ('Operário-PR', 'Brasil', 'Série B', 8.0, 14, 28, False),
    5139: ('Botafogo-SP', 'Brasil', 'Série B', 7.0, 14, 25, False),
    2465: ('Ponte Preta', 'Brasil', 'Série B', 6.0, 24, 23, False),
    1935: ('Náutico', 'Brasil', 'Série B', 5.0, 30, 19, False),
    2408: ('Londrina', 'Brasil', 'Série B', 5.0, 14, 17, False),
    2068: ('São Bernardo', 'Brasil', 'Série B', 5.0, 8, 13, False),
    5574: ('Athletic-MG', 'Brasil', 'Série B', 4.0, 6, 10, False),
    # ---- Argentina ----
    138: ('River Plate', 'Argentina', 'Liga Profesional', 105.0, 92, 92, False),
    139: ('Boca Juniors', 'Argentina', 'Liga Profesional', 90.0, 95, 90, True),
    1237: ('Racing Club', 'Argentina', 'Liga Profesional', 80.0, 70, 72, False),
    1242: ('Rosario Central', 'Argentina', 'Liga Profesional', 52.0, 55, 50, True),
    5046: ('Talleres', 'Argentina', 'Liga Profesional', 45.0, 52, 45, False),
    1244: ('Vélez Sarsfield', 'Argentina', 'Liga Profesional', 45.0, 50, 65, False),
    1240: ('Independiente', 'Argentina', 'Liga Profesional', 42.0, 70, 80, False),
    1238: ('Estudiantes', 'Argentina', 'Liga Profesional', 42.0, 52, 75, True),
    1236: ('Argentinos Juniors', 'Argentina', 'Liga Profesional', 38.0, 35, 50, False),
    1929: ('Lanús', 'Argentina', 'Liga Profesional', 39.0, 40, 55, True),
    1243: ('San Lorenzo', 'Argentina', 'Liga Profesional', 30.0, 65, 62, False),
    2536: ('Belgrano', 'Argentina', 'Liga Profesional', 28.0, 50, 35, False),
    1922: ('Huracán', 'Argentina', 'Liga Profesional', 26.0, 45, 38, False),
    1241: ("Newell's Old Boys", 'Argentina', 'Liga Profesional', 25.0, 55, 50, False),
    1924: ('Godoy Cruz', 'Argentina', 'Liga Profesional', 24.0, 35, 35, False),
    2722: ('Defensa y Justicia', 'Argentina', 'Liga Profesional', 22.0, 25, 42, False),
    1927: ('Banfield', 'Argentina', 'Liga Profesional', 20.0, 38, 35, False),
    5389: ('Tigre', 'Argentina', 'Liga Profesional', 18.0, 30, 30, False),
    1239: ('Gimnasia La Plata', 'Argentina', 'Liga Profesional', 18.0, 45, 35, False),
    2719: ('Atlético Tucumán', 'Argentina', 'Liga Profesional', 17.0, 40, 30, False),
    5454: ('Platense', 'Argentina', 'Liga Profesional', 15.0, 25, 28, False),
    4995: ('Central Córdoba', 'Argentina', 'Liga Profesional', 13.0, 25, 22, False),
    # ---- Uruguai ----
    2491: ('Peñarol', 'Uruguai', 'Primera División', 41.0, 70, 82, True),
    2490: ('Nacional', 'Uruguai', 'Primera División', 38.0, 68, 80, False),
    2694: ('Defensor Sporting', 'Uruguai', 'Primera División', 15.0, 30, 45, False),
    2484: ('Liverpool-URU', 'Uruguai', 'Primera División', 12.0, 20, 30, False),
    2481: ('Danubio', 'Uruguai', 'Primera División', 8.0, 25, 35, False),
    2486: ('Montevideo Wanderers', 'Uruguai', 'Primera División', 7.0, 20, 30, False),
    # ---- Chile ----
    1256: ('Colo-Colo', 'Chile', 'Primera División', 30.0, 75, 65, False),
    2209: ('Universidad de Chile', 'Chile', 'Primera División', 25.0, 65, 55, False),
    2191: ('Universidad Católica', 'Chile', 'Primera División', 22.0, 50, 50, False),
    2707: ('Coquimbo Unido', 'Chile', 'Primera División', 10.0, 25, 25, False),
    2548: ('Palestino', 'Chile', 'Primera División', 8.0, 25, 30, False),
    2545: ('Huachipato', 'Chile', 'Primera División', 8.0, 20, 28, False),
    # ---- Colômbia ----
    2193: ('Atlético Nacional', 'Colômbia', 'Liga BetPlay', 30.0, 70, 70, False),
    1258: ('Millonarios', 'Colômbia', 'Liga BetPlay', 22.0, 65, 55, False),
    1257: ('América de Cali', 'Colômbia', 'Liga BetPlay', 22.0, 65, 55, False),
    2285: ('Junior', 'Colômbia', 'Liga BetPlay', 20.0, 55, 48, False),
    2210: ('Independiente Medellín', 'Colômbia', 'Liga BetPlay', 18.0, 55, 42, False),
    2361: ('Deportes Tolima', 'Colômbia', 'Liga BetPlay', 15.0, 35, 40, False),
    2657: ('Santa Fe', 'Colômbia', 'Liga BetPlay', 14.0, 50, 45, False),
    2284: ('Once Caldas', 'Colômbia', 'Liga BetPlay', 12.0, 40, 50, False),
    5208: ('Atlético Bucaramanga', 'Colômbia', 'Liga BetPlay', 10.0, 30, 30, False),
    2650: ('Deportivo Cali', 'Colômbia', 'Liga BetPlay', 10.0, 45, 40, False),
    # ---- Equador ----
    4034: ('Independiente del Valle', 'Equador', 'LigaPro', 31.0, 30, 55, True),
    4043: ('LDU Quito', 'Equador', 'LigaPro', 18.0, 55, 62, True),
    4041: ('Barcelona SC', 'Equador', 'LigaPro', 17.0, 70, 52, True),
    4003: ('Emelec', 'Equador', 'LigaPro', 10.0, 55, 45, False),
    1200: ('Macará', 'Equador', 'LigaPro', 8.0, 15, 20, True),
    5216: ('Universidad Católica-EQU', 'Equador', 'LigaPro', 8.0, 20, 25, False),
    4038: ('Aucas', 'Equador', 'LigaPro', 6.0, 30, 30, False),
    5190: ('Orense', 'Equador', 'LigaPro', 6.0, 15, 20, False),
    5193: ('Deportivo Cuenca', 'Equador', 'LigaPro', 5.0, 20, 25, True),
    # ---- Paraguai ----
    4044: ('Cerro Porteño', 'Paraguai', 'Primera División', 25.0, 60, 50, False),
    4035: ('Olimpia', 'Paraguai', 'Primera División', 22.0, 60, 70, False),
    4036: ('Libertad', 'Paraguai', 'Primera División', 22.0, 35, 45, False),
    2514: ('Guaraní-PAR', 'Paraguai', 'Primera División', 10.0, 30, 35, False),
    1818: ('Nacional-PAR', 'Paraguai', 'Primera División', 8.0, 25, 30, False),
    # ---- Peru ----
    2287: ('Alianza Lima', 'Peru', 'Liga 1', 16.0, 62, 50, False),
    2215: ('Universitario', 'Peru', 'Liga 1', 15.0, 62, 52, False),
    2216: ('Sporting Cristal', 'Peru', 'Liga 1', 15.0, 50, 50, False),
    4045: ('Melgar', 'Peru', 'Liga 1', 8.0, 35, 35, False),
    342: ('Cienciano', 'Peru', 'Liga 1', 6.0, 35, 40, False),
    # ---- Bolívia ----
    4040: ('Bolívar', 'Bolívia', 'División Profesional', 10.0, 50, 45, False),
    4001: ('The Strongest', 'Bolívia', 'División Profesional', 8.0, 48, 40, False),
    4033: ('Always Ready', 'Bolívia', 'División Profesional', 5.0, 25, 25, False),
    4002: ('Jorge Wilstermann', 'Bolívia', 'División Profesional', 4.0, 35, 30, False),
    5200: ('Blooming', 'Bolívia', 'División Profesional', 4.0, 30, 25, False),
    # ---- Venezuela ----
    4037: ('Caracas', 'Venezuela', 'Liga FUTVE', 4.0, 40, 30, False),
    2218: ('Deportivo Táchira', 'Venezuela', 'Liga FUTVE', 4.0, 40, 30, False),
    4046: ('Deportivo La Guaira', 'Venezuela', 'Liga FUTVE', 4.0, 25, 22, False),
    1957: ('Carabobo', 'Venezuela', 'Liga FUTVE', 3.0, 20, 18, False),
    5669: ('Monagas', 'Venezuela', 'Liga FUTVE', 3.0, 20, 18, False),
}

# times do jogo que não estão no banco: nota pela pasta/liga do kitserver
PADRAO_LIGA = {'SERIE C': (3.0, 20, 15), 'SERIE D': (1.0, 12, 8), 'OUTROS DA AMERICA': (1.0, 10, 8)}
PADRAO_PAIS = {'Argentina': (6.0, 25, 20), 'Uruguai': (3.0, 15, 15), 'Chile': (4.0, 15, 15),
               'Colombia': (4.0, 20, 18), 'Equador': (3.0, 15, 15), 'Paraguai': (3.0, 15, 15),
               'Peru': (2.5, 15, 15), 'Bolivia': (1.5, 12, 12), 'Venezuela': (1.5, 12, 10)}
PAISES_SUL = {'Brasil', 'Argentina', 'Uruguai', 'Chile', 'Colombia', 'Equador', 'Paraguai', 'Peru', 'Bolivia',
              'Venezuela'}
NOME_PAIS = {'Colombia': 'Colômbia', 'Bolivia': 'Bolívia'}
NIVEIS = [(80, 'Gigante'), (65, 'Grande'), (50, 'Médio'), (35, 'Emergente'), (0, 'Pequeno')]


def _nota(valor, torcida, prest):
    v = 100 * math.log1p(valor) / math.log1p(210)
    return round(0.45 * v + 0.30 * torcida + 0.25 * prest, 1)


def nivel(nota):
    return next(n for lim, n in NIVEIS if nota >= lim)


def tabela(mapa_jogo=None):
    """Ranking completo. mapa_jogo: {id: 'Pais\\Liga\\Time'} do kitserver, para incluir os times sem dados."""
    out = []
    for tid, (nome, pais, liga, valor, torc, prest, medido) in CLUBES.items():
        out.append({'id': tid, 'nome': nome, 'pais': pais, 'liga': liga, 'valor': valor, 'torcida': torc,
                    'prestigio': prest, 'medido': medido, 'nota': _nota(valor, torc, prest)})
    for tid, cam in (mapa_jogo or {}).items():
        if tid in CLUBES:
            continue
        p = cam.split('\\')
        if p[0] not in PAISES_SUL or len(p) < 2:
            continue
        liga = p[1] if p[0] == 'Brasil' and len(p) > 2 else 'Primera'
        base = PADRAO_LIGA.get(liga.upper()) if p[0] == 'Brasil' else PADRAO_PAIS.get(p[0])
        if not base:
            continue
        valor, torc, prest = base
        out.append({'id': tid, 'nome': p[-1], 'pais': NOME_PAIS.get(p[0], p[0]),
                    'liga': {'SERIE C': 'Série C', 'SERIE D': 'Série D'}.get(liga.upper(), 'Outras'),
                    'valor': valor, 'torcida': torc, 'prestigio': prest, 'medido': False,
                    'nota': _nota(valor, torc, prest)})
    out.sort(key=lambda c: -c['nota'])
    for i, c in enumerate(out, 1):
        c['pos'] = i
        c['nivel'] = nivel(c['nota'])
    return out


def clube(tid, mapa_jogo=None):
    return next((c for c in tabela(mapa_jogo) if c['id'] == tid), None)


def propostas(prest_tecnico, atual_id, mapa_jogo=None, n=3, sondagem=False, seed=0, excluir=()):
    """Clubes que procuram o técnico.
    Demitido: clubes à altura do prestígio dele ou abaixo (nota entre prestígio-28 e prestígio+4).
    Sondagem (em alta): clubes maiores que o atual, até prestígio+15."""
    t = tabela(mapa_jogo)
    atual = next((c for c in t if c['id'] == atual_id), None)
    nota_atual = atual['nota'] if atual else 50
    p = prest_tecnico or 50
    if sondagem:
        lo, hi = nota_atual + 3, max(nota_atual + 8, p + 15)
    else:
        lo, hi = p - 28, p + 4
    pool = [c for c in t if lo <= c['nota'] <= hi and c['id'] != atual_id and c['id'] not in excluir]
    if len(pool) < n:     # amplia a faixa se faltar clube
        pool = sorted([c for c in t if c['id'] != atual_id and c['id'] not in excluir],
                      key=lambda c: abs(c['nota'] - (hi if sondagem else (lo + hi) / 2)))[:n * 3]
    r = random.Random(seed)
    # quanto mais perto do topo da faixa, mais chance (os melhores clubes que aceitam o técnico)
    esc = []
    pais = atual['pais'] if atual else 'Brasil'
    while pool and len(esc) < n:
        # quanto mais perto do topo da faixa, mais chance; clubes do mesmo país aparecem um pouco mais
        pesos = [(1 + (c['nota'] - lo) / 10) * (1.5 if c['pais'] == pais else 1) for c in pool]
        c = r.choices(pool, [max(0.2, w) for w in pesos])[0]
        esc.append(c)
        pool.remove(c)
    return [{'time_id': c['id'], 'nome': c['nome'], 'pais': c['pais'], 'liga': c['liga'], 'pos': c['pos'],
             'nota': c['nota'], 'nivel': c['nivel']} for c in esc]
