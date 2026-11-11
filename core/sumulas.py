"""Súmulas das partidas da Master League, lidas do save.

O save guarda a temporada inteira numa tabela de registros de 0x254 bytes (um por partida):
  +0x04 u16 torneio   +0x07 u8 estado (bit 0x40 = jogada: 0x60 na liga, 0x40/0x50 nas copas; 0x20/0x00/0x10 a jogar)
  +0x08 u16 ano  +0x0A u8 mês  +0x0B u8 dia
  +0x14 u32 mandante (id << 14)   +0x18 u32 visitante   +0x1C u8 gols mandante   +0x1F u8 gols visitante
  +0x24 mandante e +0x134 visitante: 17 linhas de 16 bytes, uma por jogador que entrou em campo
     +0 u16 (0xFFFF = linha vazia)  +4 u32 id do jogador  +8 u8 gols  +9 u8 assistências
     +12 u32: bits 0-6 minutos jogados, bits 7-13 nota x10, bits 14-17 posição,
              bit 19 cartão amarelo, bit 20 expulsão (bit 18 junto da expulsão), bit 21 titular, bit 22 entrou em campo
              (titular/amarelo/vermelho só nas partidas que o usuário jogou; nas simuladas todos ficam como titular)
Liga e copas ficam em sequências separadas de registros, todas com o mesmo formato. Vale para jogos jogados
e simulados. Conferido em saves reais: a soma dos gols dos jogadores bate com o placar em ~98% dos jogos
(o resto são gols contra, que não vão para nenhum jogador).
"""
import struct

import numpy as np

STRIDE = 0x254
PALAVRAS = STRIDE // 4
JOGADA_BIT = 0x40
LINHAS, LINHA = 17, 16
LADO = (0x24, 0x134)
BIT_AMARELO, BIT_VERMELHO, BIT_TITULAR = 1 << 19, 1 << 20, 1 << 21


def _candidatos(a: np.ndarray):
    """Índices (em palavras de 4 bytes) que parecem início de registro de partida."""
    n = len(a) - PALAVRAS
    if n <= 0:
        return np.array([], dtype=np.int64)
    w1 = a[1:n + 1]
    est, torneio = w1 >> 24, w1 & 0xFFFF
    w2 = a[2:n + 2]
    ano, mes, dia = w2 & 0xFFFF, (w2 >> 16) & 0xFF, w2 >> 24
    casa = a[5:n + 5] >> 14
    fora = a[6:n + 6] >> 14
    gc = a[7:n + 7] & 0xFF
    ok = (((est & 0x0F) == 0) & (est <= 0x70) & (torneio > 0)
          & (ano >= 2000) & (ano <= 2100) & (mes >= 1) & (mes <= 12) & (dia >= 1) & (dia <= 31)
          & (casa > 0) & (casa < 20000) & (fora > 0) & (fora < 20000) & (casa != fora) & (gc < 30))
    return np.nonzero(ok)[0]


def achar_tabelas(data: bytes, minimo=2):
    """Todas as sequências de registros de partida (a liga numa, cada copa noutra): [(offset, quantidade)]."""
    a = np.frombuffer(data[:len(data) // 4 * 4], '<u4')
    cand = _candidatos(a)
    cs = set(cand.tolist())
    out = []
    for w in cand.tolist():
        if w - PALAVRAS in cs:
            continue
        k, x = 0, w
        while x in cs:
            k += 1
            x += PALAVRAS
        if k >= minimo:
            out.append((w * 4, k))
    return out


def achar_tabela(data: bytes):
    """A maior sequência (a liga). Mantida para quem só precisa dela."""
    ts = achar_tabelas(data, 20)
    return max(ts, key=lambda t: t[1]) if ts else None


def _jogadores(data, base):
    out = []
    for j in range(LINHAS):
        e = base + j * LINHA
        if struct.unpack_from('<H', data, e)[0] == 0xFFFF:
            continue
        pid = struct.unpack_from('<I', data, e + 4)[0]
        if not pid:
            continue
        t = struct.unpack_from('<I', data, e + 12)[0]
        minutos, nota = t & 0x7F, ((t >> 7) & 0x7F) / 10
        out.append({'id': pid, 'gols': data[e + 8], 'assist': data[e + 9], 'min': minutos,
                    'nota': nota if minutos > 0 and nota > 0 else None,
                    'titular': bool(t & BIT_TITULAR), 'amarelo': bool(t & BIT_AMARELO),
                    'vermelho': bool(t & BIT_VERMELHO)})
    return out


def partidas(data: bytes, tabelas=None):
    """Todas as partidas já jogadas (ou simuladas) da temporada, com a súmula de cada time."""
    tabelas = tabelas if tabelas is not None else achar_tabelas(data)
    res, vistos = [], set()
    for ini, n in tabelas:
        for i in range(n):
            o = ini + i * STRIDE
            if o in vistos or not data[o + 7] & JOGADA_BIT:
                continue
            vistos.add(o)
            ano, mes, dia = struct.unpack_from('<H', data, o + 8)[0], data[o + 0x0A], data[o + 0x0B]
            casa, fora = struct.unpack_from('<II', data, o + 0x14)
            res.append({'registro': o, 'torneio': struct.unpack_from('<H', data, o + 4)[0],
                        'data': f'{ano:04d}-{mes:02d}-{dia:02d}',
                        'mandante': casa >> 14, 'visitante': fora >> 14,
                        'gols_mandante': data[o + 0x1C], 'gols_visitante': data[o + 0x1F],
                        'escalacao_mandante': _jogadores(data, o + LADO[0]),
                        'escalacao_visitante': _jogadores(data, o + LADO[1])})
    res.sort(key=lambda p: (p['data'], p['registro']))
    return res


def do_time(data: bytes, team_id: int):
    """Partidas jogadas pelo clube (liga e copas, jogadas ou simuladas), sem a súmula."""
    return [{k: p[k] for k in ('torneio', 'data', 'mandante', 'visitante', 'gols_mandante', 'gols_visitante')}
            for p in partidas(data) if team_id in (p['mandante'], p['visitante'])]


def do_clube(data: bytes, team_id: int, nomes=None, ultimas=15):
    """Estatísticas do clube na temporada: por jogador e as últimas súmulas."""
    nomes = nomes or {}
    nome = lambda pid: (nomes.get(pid) or {}).get('nome') or f'Jogador {pid}'
    jogos = [p for p in partidas(data) if team_id in (p['mandante'], p['visitante'])]
    tab = {}
    for p in jogos:
        meus = p['escalacao_mandante'] if p['mandante'] == team_id else p['escalacao_visitante']
        for j in meus:
            s = tab.setdefault(j['id'], {'id': j['id'], 'nome': nome(j['id']),
                                         'pos': (nomes.get(j['id']) or {}).get('pos', ''),
                                         'jogos': 0, 'titular': 0, 'minutos': 0, 'gols': 0, 'assist': 0,
                                         'amarelos': 0, 'vermelhos': 0, 'notas': []})
            s['jogos'] += 1
            s['titular'] += j['titular']
            s['amarelos'] += j['amarelo']
            s['vermelhos'] += j['vermelho']
            s['minutos'] += j['min']
            s['gols'] += j['gols']
            s['assist'] += j['assist']
            if j['nota'] is not None:
                s['notas'].append(j['nota'])
    lista = []
    for s in tab.values():
        notas = s.pop('notas')
        s['nota_media'] = round(sum(notas) / len(notas), 2) if notas else None
        s['nota_max'] = max(notas) if notas else None
        s['ultimas_notas'] = notas[-5:]
        lista.append(s)
    lista.sort(key=lambda s: (-s['jogos'], -s['minutos']))
    sumulas = []
    for p in jogos[-ultimas:][::-1]:
        casa = p['mandante'] == team_id
        meus = p['escalacao_mandante'] if casa else p['escalacao_visitante']
        sumulas.append({'data': p['data'], 'torneio': p['torneio'], 'mandante': p['mandante'],
                        'visitante': p['visitante'], 'gols_mandante': p['gols_mandante'],
                        'gols_visitante': p['gols_visitante'], 'em_casa': casa,
                        'jogadores': [{**j, 'nome': nome(j['id'])}
                                      for j in sorted(meus, key=lambda j: (not j['titular'], -j['min'], -(j['nota'] or 0)))]})
    return {'jogos': len(jogos), 'jogadores': lista, 'sumulas': sumulas}
