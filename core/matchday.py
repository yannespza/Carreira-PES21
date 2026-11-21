"""Dia de jogo no Sider: clima da partida, torcida única nos clássicos paulistas e público ligado à tabela.

Usa os módulos que o patch GOGOSZ já tem instalados (o app só escreve os arquivos de configuração deles):
- StadiumServer.lua lê, a cada partida, GOGOSZ\\Estadios\\<estádio>\\force_weather.ini (Season, Time_of_day,
  Weather, Weather_Effects). O app escreve esse arquivo no estádio do mandante do próximo jogo do clube e apaga
  o que escreveu antes. Arquivo que não foi o app que criou nunca é tocado.
- crowd_behavior.lua lê modules\\crowd_behavior.ini ([team:ID] base_home/base_away, [rivalry:A:B] intensity) e
  modules\\crowd_standings.csv (posição, pontos e forma reais de cada time). O app escreve só o bloco dele no
  .ini, entre as linhas-marcador, e mantém o resto do arquivo como está.
Nada disso mexe no save.
"""
import os, re, random, datetime

from . import cidades

MARCA = '# App Carreira: gerado automaticamente (pode apagar; o app recria)'
INI_INI = '; >>> App Carreira (gerado automaticamente, não edite entre estas linhas)'
INI_FIM = '; <<< App Carreira'
PAULISTAS = ('palmeiras', 'corinthians', 'sao paulo', 'santos')

# chance de chuva (%) por região e mês (jan..dez), aproximada da climatologia
CHUVA = {
    'sudeste':      [45, 40, 38, 25, 18, 12, 10, 10, 18, 28, 35, 45],
    'sp_interior':  [45, 40, 35, 20, 12, 8, 6, 6, 15, 25, 35, 45],
    'sul':          [30, 30, 28, 25, 28, 30, 30, 28, 32, 32, 28, 28],
    'serra':        [32, 32, 30, 27, 30, 33, 33, 30, 34, 34, 30, 30],
    'nordeste':     [20, 25, 35, 45, 45, 40, 35, 22, 12, 8, 8, 12],
    'centro_oeste': [50, 45, 40, 22, 8, 3, 2, 4, 12, 30, 42, 50],
    'norte':        [60, 62, 65, 60, 50, 35, 28, 25, 28, 35, 42, 52],
    'altitude':     [45, 42, 38, 25, 12, 8, 8, 10, 15, 22, 28, 38],
    'platina':      [25, 25, 28, 25, 22, 20, 20, 20, 22, 28, 28, 25],
    'pacifico':     [3, 3, 3, 5, 10, 15, 15, 12, 8, 5, 3, 3],
    'tropical':     [35, 35, 40, 45, 45, 35, 30, 30, 35, 40, 40, 38],
}
# temperatura média da tarde (°C) por região e mês
TEMP = {
    'sudeste':      [29, 30, 29, 27, 24, 23, 23, 24, 25, 26, 27, 28],
    'sp_interior':  [31, 31, 31, 29, 27, 26, 26, 28, 31, 31, 31, 31],
    'sul':          [29, 29, 27, 24, 20, 17, 17, 18, 20, 23, 25, 28],
    'serra':        [26, 26, 24, 21, 17, 15, 14, 16, 18, 20, 23, 25],
    'nordeste':     [31, 31, 31, 30, 29, 28, 28, 28, 29, 30, 31, 31],
    'centro_oeste': [30, 30, 30, 30, 29, 28, 29, 32, 33, 32, 31, 30],
    'norte':        [31, 31, 31, 31, 32, 32, 33, 33, 34, 33, 33, 32],
    'altitude':     [15, 15, 15, 15, 14, 13, 13, 14, 15, 16, 17, 16],
    'platina':      [30, 28, 26, 22, 18, 15, 14, 17, 19, 22, 25, 28],
    'pacifico':     [27, 28, 27, 25, 22, 19, 18, 18, 19, 21, 23, 25],
    'tropical':     [32, 32, 32, 31, 30, 29, 29, 30, 31, 31, 31, 31],
}
QUENTES = ('nordeste', 'centro_oeste', 'sp_interior', 'norte', 'tropical')


def _norm(s):
    return cidades._norm(s)


def eh_paulista_grande(nome):
    n = _norm(nome)
    return any(re.search(r'(?<![a-z])' + k + r'(?![a-z])', n) for k in PAULISTAS)


def clima_partida(mandante_nome, data_iso, chave=''):
    """Clima do jogo pela cidade do mandante, o mês e o dia da semana (sorteio fixo por partida)."""
    c = cidades.do_time(mandante_nome) or {'cidade': '?', 'regiao': 'sudeste', 'altitude': 0, 'uf': ''}
    d = datetime.date.fromisoformat(str(data_iso)[:10])
    rnd = random.Random(f'{data_iso}|{mandante_nome}|{chave}')
    reg = c['regiao']
    m = d.month - 1
    chuva = rnd.randint(1, 100) <= CHUVA.get(reg, CHUVA['sudeste'])[m]
    meio_semana = d.weekday() in (1, 2, 3)
    noite = True if meio_semana else rnd.random() < 0.45
    hora = ('21h30' if rnd.random() < 0.6 else '19h') if noite else ('16h' if rnd.random() < 0.6 else '18h30')
    temp = TEMP.get(reg, TEMP['sudeste'])[m] + rnd.randint(-2, 2) - (5 if noite else 0) - (3 if chuva else 0)
    if reg in ('sul', 'serra', 'platina', 'altitude'):
        estacao = 'winter' if d.month in (5, 6, 7, 8, 9) else 'summer'
    else:
        estacao = 'winter' if d.month in (6, 7, 8) else 'summer'
    alertas = []
    calor = not noite and not chuva and reg in QUENTES and temp >= 30
    if calor:
        alertas.append('Calor forte à tarde: desgaste maior no 2º tempo')
    if chuva and d.month in (12, 1, 2, 3) and reg in ('sudeste', 'sp_interior', 'centro_oeste'):
        alertas.append('Temporal de verão: gramado pesado')
    if c.get('altitude', 0) >= 2500:
        alertas.append(f"Altitude de {c['altitude']} m")
    return {'cidade': c['cidade'], 'uf': c.get('uf', ''), 'regiao': reg, 'altitude': c.get('altitude', 0),
            'chuva': chuva, 'noite': noite, 'hora': hora, 'temp': temp, 'estacao': estacao,
            'calor': calor, 'alertas': alertas,
            'texto': f"{c['cidade']} · {hora} · {'chuva' if chuva else 'tempo firme'} · {temp}°C"}


def gravar_clima(pasta_estadio, clima):
    """Escreve o force_weather.ini no estádio. Não sobrescreve arquivo que não seja do app."""
    if not pasta_estadio or not os.path.isdir(pasta_estadio):
        return None
    f = os.path.join(pasta_estadio, 'force_weather.ini')
    if os.path.exists(f):
        try:
            if MARCA not in open(f, encoding='utf-8', errors='replace').read():
                return None
        except OSError:
            return None
    txt = (MARCA + '\n'
           f"Season = {'Winter' if clima['estacao'] == 'winter' else 'Summer'}\n"
           f"Time_of_day = {'Night' if clima['noite'] else 'Day'}\n"
           f"Weather = {'Rainy' if clima['chuva'] else 'Fine'}\n"
           f"Weather_Effects = {'Forced' if clima['chuva'] else 'Default'}\n")
    try:
        if not os.path.exists(f) or open(f, encoding='utf-8').read() != txt:
            open(f, 'w', encoding='utf-8').write(txt)
        return f
    except OSError:
        return None


def apagar_clima(caminho):
    try:
        if caminho and os.path.exists(caminho) and MARCA in open(caminho, encoding='utf-8', errors='replace').read():
            os.remove(caminho)
    except OSError:
        pass


def bloco_torcida(clube_id, clube_nome, prox, rivais_ids, nomes):
    """Texto do bloco do app no crowd_behavior.ini e a descrição da regra aplicada no próximo jogo."""
    L, regra = [], None
    for r in sorted(set(rivais_ids or [])):
        a, b = sorted((int(clube_id), int(r)))
        L += [f'[rivalry:{a}:{b}]', 'intensity = 1', '']
    if prox:
        m, v = int(prox['m']), int(prox['v'])
        if eh_paulista_grande(nomes.get(m, prox.get('mn', ''))) and eh_paulista_grande(nomes.get(v, prox.get('vn', ''))):
            L += [f'[team:{v}]', 'base_away = 0', '', f'[team:{m}]', 'base_home = 100', '']
            regra = {'tipo': 'torcida_unica', 'texto': 'Torcida única (determinação FPF/MP-SP): 100% mandante, 0% visitante'}
    return '\n'.join([INI_INI] + L + [INI_FIM]) + '\n', regra


def gravar_ini_torcida(pasta_jogo, bloco):
    p = os.path.join(pasta_jogo, 'modules', 'crowd_behavior.ini')
    if not os.path.exists(p):
        return False
    try:
        txt = open(p, encoding='utf-8-sig', errors='replace').read()
    except OSError:
        return False
    if INI_INI in txt and INI_FIM in txt:
        a = txt.index(INI_INI)
        b = txt.index(INI_FIM) + len(INI_FIM)
        novo = txt[:a] + bloco.rstrip('\n') + txt[b:]
    else:
        novo = txt.rstrip('\n') + '\n\n' + bloco
    if novo == txt:
        return True
    try:
        open(p, 'w', encoding='utf-8').write(novo)
        return True
    except OSError:
        return False


def csv_tabela(linhas, formas, torneio=17, escopo='default'):
    """crowd_standings.csv: uma linha por time e por rodada (todas as rodadas em andamento)."""
    n = len(linhas)
    rodadas = sorted({int(l['j']) for l in linhas})
    out = ['scope;tournament_id;round;team_id;rank;league_size;matches_played;form;source;points']
    for r in rodadas:
        for l in linhas:
            out.append(f"{escopo};{torneio};{r};{l['id']};{l['pos']};{n};{l['j']};{formas.get(l['id'], '')[-5:]};"
                       f"app_carreira;{l['pts']}")
    return '\n'.join(out) + '\n'


def gravar_csv(pasta_jogo, txt):
    p = os.path.join(pasta_jogo, 'modules', 'crowd_standings.csv')
    if not os.path.isdir(os.path.dirname(p)):
        return False
    try:
        if os.path.exists(p) and open(p, encoding='utf-8', errors='replace').read() == txt:
            return True
        open(p, 'w', encoding='utf-8').write(txt)
        return True
    except OSError:
        return False


def formas(partidas, torneio=17):
    """Sequência W/D/L de cada time no campeonato, do jogo mais antigo ao mais recente."""
    f = {}
    for p in sorted((p for p in partidas if (p['torneio'] & 1023) == torneio),
                    key=lambda p: p['data']):
        gm, gv = p['gols_mandante'], p['gols_visitante']
        rm = 'W' if gm > gv else 'L' if gm < gv else 'D'
        rv = {'W': 'L', 'L': 'W', 'D': 'D'}[rm]
        f[p['mandante']] = f.get(p['mandante'], '') + rm
        f[p['visitante']] = f.get(p['visitante'], '') + rv
    return f


ARBITROS = {
    'rigoroso': ('Rigoroso', 'apita tudo e dá cartão fácil: cuidado com carrinhos e reclamação'),
    'caseiro': ('Caseiro', 'costuma favorecer o time da casa nos lances divididos'),
    'deixa': ('Deixa o jogo correr', 'marca pouca falta: jogo mais físico e corrido'),
}


def arbitro(data_iso, chave, eh_classico=False):
    """Perfil do árbitro da partida (sorteio fixo por jogo; clássicos têm mais chance de árbitro rigoroso)."""
    r = random.Random(f'arb|{data_iso}|{chave}')
    pesos = [45, 25, 30] if eh_classico else [30, 30, 40]
    k = r.choices(list(ARBITROS), weights=pesos)[0]
    nome, efeito = ARBITROS[k]
    return {'perfil': k, 'nome': nome, 'efeito': efeito, 'texto': f'{nome} ({efeito})'}
