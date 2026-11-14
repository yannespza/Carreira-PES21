"""Ficha completa dos jogadores (atributos, habilidades, estilo de jogo, posições) e o time de juniores.

Ficha: registro de 312 bytes do arquivo EDIT (o mesmo que tem o nome). Os primeiros 0x36 bytes são campos de
bits; as posições abaixo foram conferidas com a exportação do editor do patch (14 mil jogadores batendo campo a
campo).

Juniores: o save do Master League guarda os jogadores da base numa tabela de registros de 0x170 bytes
(número sequencial, id do jogador...; +0x164 CGJ atual), com o time principal e os juniores juntos. Outra
tabela, de 0xC0 bytes, guarda idade e a curva de CGJ de cada jogador do clube (principal e juniores)."""
import struct

import numpy as np

# atributo -> bit inicial (7 bits cada)
ATRIBUTOS = [
    ('Talento ofensivo', 112), ('Controle de bola', 119), ('Drible', 320), ('Condução firme', 128),
    ('Passe rasteiro', 135), ('Passe alto', 142), ('Finalização', 149), ('Cabeceio', 302),
    ('Chute colocado', 167), ('Curva', 160), ('Velocidade', 174), ('Aceleração', 181),
    ('Força do chute', 365), ('Impulsão', 192), ('Contato físico', 199), ('Equilíbrio', 206),
    ('Resistência', 213), ('Talento defensivo', 288), ('Desarme', 224), ('Agressividade', 231),
    ('Talento de goleiro', 238), ('Firmeza de goleiro', 245), ('Afastamento', 295), ('Reflexos', 358),
    ('Cobertura de goleiro', 256),
]
GRUPOS = {'Ataque': range(0, 10), 'Físico': range(10, 17), 'Defesa': range(17, 20), 'Goleiro': range(20, 25)}
# habilidades especiais: um bit cada, a partir do bit 383, nesta ordem
HABILIDADES = ['Malabarista', 'Arrancada', 'Explosão', 'Infiltração', 'Lançamento longo', 'Cruzamento precoce',
               'Chute de longe', 'Tesoura', 'Toque duplo', 'Elástico', 'Giro marselhês', 'Chapéu', 'Corte cruzado',
               'Corte por trás', 'Escocesa', 'Domínio com a sola', 'Cabeçada', 'Chute forte de longe',
               'Cavadinha', 'Chute colocado de longe', 'Chute sem efeito', 'Chute descendente', 'Chute ascendente',
               'Finalização acrobática', 'Toque de calcanhar', 'Chute de primeira', 'Passe de primeira',
               'Passe em profundidade', 'Passe na medida', 'Cruzamento preciso', 'Chute de trivela', 'Letra',
               'Passe sem olhar', 'Passe alto rasteiro', 'Tiro de meta baixo', 'Tiro de meta alto',
               'Arremesso longo', 'Reposição longa', 'Especialista em pênaltis', 'Pegador de pênaltis',
               'Malícia', 'Marcação individual', 'Volta para marcar', 'Interceptação', 'Corte acrobático',
               'Capitão', 'Talismã', 'Espírito de luta']
BIT_HAB = 383
# estilo de jogo (5 bits em 274), na ordem interna do jogo; nomes como o jogo em português quando conferidos
ESTILOS = ['Equilibrado', 'Artilheiro', 'Pivô de movimentação', 'Matador de área', 'Pivô', 'Armador criativo',
           'Ponta prolífico', 'Meia aberto', 'Especialista em cruzamentos', 'Camisa 10 clássico', 'Infiltrador',
           'Box-to-box', 'Destruidor', 'Orquestrador', 'Volante de contenção', 'Lateral ofensivo',
           'Lateral finalizador', 'Lateral defensivo', 'Provocador', 'Zagueiro-atacante', 'Goleiro ofensivo',
           'Goleiro defensivo']
SIGLAS = ['GO', 'ZC', 'LE', 'LD', 'VOL', 'MLG', 'MLE', 'MLD', 'MAT', 'PTE', 'PTD', 'SA', 'CA']
# aptidão em cada posição (2 bits: 0 não joga, 1 razoável, 2 boa)
BITS_POS = {'GO': 333, 'ZC': 335, 'LE': 337, 'LD': 339, 'VOL': 341, 'MLG': 343, 'MLE': 345, 'MLD': 347,
            'MAT': 349, 'PTD': 352, 'SA': 354, 'CA': 356, 'PTE': 372}


def _f(v, b, n):
    return (v >> b) & ((1 << n) - 1)


def ficha(raw: bytes):
    """Atributos, habilidades, estilo, pé, pé ruim, forma e posições do registro do EDIT."""
    if not raw:
        return None
    v = int.from_bytes(raw[:0x36], 'little')
    atr = {n: _f(v, b, 7) for n, b in ATRIBUTOS}
    if not all(30 <= x <= 99 for x in atr.values()):
        return None
    pos = _f(v, 269, 4)
    est = _f(v, 274, 5)
    return {
        'atributos': atr,
        'habilidades': [h for i, h in enumerate(HABILIDADES) if _f(v, BIT_HAB + i, 1)],
        'estilo': ESTILOS[est] if est < len(ESTILOS) else '',
        'posicao': SIGLAS[pos] if pos < len(SIGLAS) else '',
        'posicoes': {k: _f(v, b, 2) for k, b in BITS_POS.items() if _f(v, b, 2)},
        'pe': 'esquerdo' if _f(v, 381, 1) else 'direito',
        'pe_ruim_uso': _f(v, 126, 2) + 1, 'pe_ruim_precisao': _f(v, 318, 2) + 1,
        'forma': _f(v, 252, 3) + 1, 'resistencia_lesao': _f(v, 327, 2) + 1,
        'altura': raw[0x0a], 'peso': raw[0x0b] & 0x7f,
    }


def _tabela(a, passo, minimo, valido):
    """Começos de sequências de registros com número sequencial (u32) que sobe de 1 em 1."""
    n = len(a) - passo * minimo
    if n <= 0:
        return []
    i = np.arange(n)
    ok = (a[i] > 0) & (a[i + passo] == a[i] + 1) & (a[i + 2 * passo] == a[i] + 2) & (a[i + 1] > 0) & (a[i + 1] < 2_000_000)
    out = []
    for k in np.nonzero(ok)[0].tolist():
        if k >= passo and a[k - passo] == a[k] - 1:
            continue
        if valido(k):
            out.append(k)
    return out


def juniores(data: bytes):
    """[{id, situacao, cgj}] da tabela de jogadores do clube: o time principal e a base ficam na mesma tabela,
    em trechos com numeração própria. Quem não está no elenco principal é dos juniores."""
    a = np.frombuffer(data[:len(data) // 4 * 4], '<u4')
    P = 0x170 // 4
    st = lambda i: data[i * 4 + 0x13c]
    cg = lambda i: data[i * 4 + 0x164]

    def valido(k):
        return all(st(k + j * P) in (3, 11) and 40 <= cg(k + j * P) <= 99 for j in range(3))
    out, vistos = [], set()
    for k in _tabela(a, P, 3, valido):
        i = k
        while i + P <= len(a) and (i == k or a[i] == a[i - P] + 1) and st(i) in (3, 11):
            pid = int(a[i + 1])
            if pid not in vistos:
                vistos.add(pid)
                out.append({'id': pid, 'situacao': int(st(i)), 'cgj': cg(i)})
            i += P
    return out


def crescimento(data: bytes):
    """{id: {'idade', 'cgj', 'curva'}} da tabela de idade e evolução dos jogadores do clube."""
    a = np.frombuffer(data[:len(data) // 4 * 4], '<u4')
    P = 0xC0 // 4

    def valido(k):
        return 14 <= data[k * 4 + 8] <= 45
    ok = lambda i: 0 <= i and i + P <= len(a) and 0 < a[i + 1] < 2_000_000 and 14 <= data[i * 4 + 8] <= 45
    for k in _tabela(a, P, 3, valido):
        while ok(k - P):          # a numeração pula entre o time principal e os juniores: volta pelo formato
            k -= P
        out = {}
        i = k
        while ok(i):
            o = i * 4
            curva = [x for x in data[o + 9:o + 9 + 60] if x]
            out[int(a[i + 1])] = {'idade': data[o + 8], 'cgj': curva[-1] if curva else None, 'curva': curva}
            i += P
        if len(out) >= 10:
            return out
    return {}


def valor_estimado(cgj, idade):
    """Valor de mercado aproximado em euros (calibrado com o jogo: 69 de CGJ aos 18 anos = € 1 milhão)."""
    if not cgj:
        return None
    base = 1_000_000 * (1.23 ** (cgj - 69))
    if idade and idade > 21:
        base *= max(0.2, 1 - (idade - 21) * 0.07)
    return int(round(base, -4))
