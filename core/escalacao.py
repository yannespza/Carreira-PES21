"""Escalação do jogo (plano de jogo) dentro do save do Master League.

Achado comparando dois saves (espaços 7 e 8, 13/11/2026): o plano de jogo do clube do usuário é uma lista de
40 bytes logo antes do código do técnico do usuário (0xFFFFFFF5) e do nome dele.
- Cada byte é a vaga do jogador no elenco do clube (0 = 1º jogador da tabela de elencos do clube).
- Posições 0-10: titulares, na ordem das posições da formação.
- Posições 11-22: os 12 reservas.
- Posições 23-39: não relacionados e vagas vazias. Dois formatos aparecem nos saves: em alguns todas as 40
  vagas têm número (a lista é uma troca de ordem de 0..39); em outros só as vagas com jogador têm número
  (0..N-1) e o resto é 0xFF.
- 0xA0 bytes antes da lista fica a formação: 11 códigos de posição + 11 pares (profundidade, lado).

O jogo lê a lista quando a carreira é carregada: depois de gravar, basta voltar ao menu e carregar a carreira.
"""
import struct
from . import savedata

TAM = 40
VAZIO = 0xFF
N_TIT = 11
N_RES = 12
ID_TECNICO = b'\xf5\xff\xff\xff'
OFF_ID = 0x3c          # do início da lista até o código do técnico
OFF_FORM = 0xa0        # da formação até o início da lista

GRUPO = {'GL': 'G', 'ZAG': 'D', 'LE': 'D', 'LD': 'D', 'VOL': 'M', 'MEI': 'M', 'ME': 'M', 'MD': 'M',
         'PE': 'A', 'PD': 'A', 'ATA': 'A'}
PAPEL = savedata.POSICOES          # código de posição do PES -> sigla do app


def lista_valida(a):
    """Os 40 bytes são uma escalação? (0..N-1 sem repetir, com 0xFF nas vagas vazias, ou 0..39 completo)"""
    a = list(a)
    if len(a) != TAM:
        return False
    vals = [x for x in a if x != VAZIO]
    return len(vals) >= N_TIT and sorted(vals) == list(range(len(vals)))


def localizar(d: bytes):
    """Início da lista de escalação do clube do usuário, ou None."""
    p = d.find(ID_TECNICO)
    while p != -1:
        o = p - OFF_ID
        if o >= 0 and lista_valida(d[o:o + TAM]):
            return o
        p = d.find(ID_TECNICO, p + 1)
    return None


def formacao(d: bytes, off):
    """Papel e lugar no campo de cada um dos 11 titulares (None se o bloco não parecer uma formação)."""
    f = off - OFF_FORM
    if f < 0:
        return None
    cod = d[f:f + N_TIT]
    xy = d[f + N_TIT:f + 3 * N_TIT]
    # um goleiro (código 0) em qualquer vaga: a ordem das vagas segue a formação do jogo, não o GL primeiro
    if list(cod).count(0) != 1 or any(c >= len(PAPEL) for c in cod) or not all(0 < v < 0x60 for v in xy):
        return None
    out = []
    for i in range(N_TIT):
        prof, lado = xy[2 * i], xy[2 * i + 1]
        out.append({'papel': PAPEL[cod[i]], 'prof': prof, 'lado': lado})
    return out


def vagas(d: bytes, team_index):
    """Id do jogador em cada vaga do elenco do clube (None = vaga vazia)."""
    base = savedata._elenco_base(d)
    if base is None or team_index is None:
        return None
    o = base + team_index * savedata.ELENCO_PASSO
    out = []
    for s in range(TAM):
        pid = struct.unpack_from('<I', d, o + 8 * (s + 1))[0] & 0x3fffffff
        out.append(pid or None)
    return out


def ler(d: bytes, team_index):
    off = localizar(d)
    if off is None:
        return None
    vg = vagas(d, team_index)
    if not vg:
        return None
    return {'off': off, 'ordem': list(d[off:off + TAM]), 'vagas': vg, 'formacao': formacao(d, off)}


def grupos(ordem):
    return ordem[:N_TIT], ordem[N_TIT:N_TIT + N_RES], ordem[N_TIT + N_RES:]


def ajustar(esc, indisponivel, posicao):
    """Tira da escalação quem está indisponível e completa com quem pode jogar.

    esc: resultado de ler(); indisponivel(pid) -> motivo ou None; posicao(pid) -> sigla (GL, ZAG...).
    Regras: o titular indisponível dá lugar a um reserva da mesma posição (senão do mesmo setor, senão o 1º
    reserva de linha; goleiro só por goleiro). O reserva indisponível dá lugar ao 1º não relacionado
    disponível. Quem está indisponível vai para o fim da lista dos não relacionados.
    Devolve (nova ordem, lista de mudanças em texto); a ordem não muda se não houver nada a fazer."""
    ordem = list(esc['ordem'])
    vg = esc['vagas']
    form = esc.get('formacao')
    pid = lambda s: vg[s] if 0 <= s < len(vg) else None
    livre = lambda s: pid(s) is not None and not indisponivel(pid(s))
    mud = []

    def candidato(faixa, papel):
        """Melhor posição (índice na ordem) dentro da faixa para cobrir o papel."""
        cands = [i for i in faixa if livre(ordem[i])]
        if not cands:
            return None
        pos = lambda i: posicao(pid(ordem[i])) or ''
        if papel == 'GL':
            gl = [i for i in cands if pos(i) == 'GL']
            return gl[0] if gl else None
        for teste in (lambda i: pos(i) == papel,
                      lambda i: GRUPO.get(pos(i)) == GRUPO.get(papel),
                      lambda i: pos(i) != 'GL'):
            ok = [i for i in cands if teste(i)]
            if ok:
                return ok[0]
        return None

    banco = range(N_TIT, N_TIT + N_RES)
    fora = range(N_TIT + N_RES, TAM)
    # 1) titulares
    for i in range(N_TIT):
        s = ordem[i]
        if pid(s) is None or not indisponivel(pid(s)):
            continue
        papel = (form[i]['papel'] if form else None) or posicao(pid(s)) or ''
        j = candidato(banco, papel)
        if j is None:
            j = candidato(fora, papel)
        if j is None:
            mud.append(f'sem substituto para {_n(posicao, pid(s))}')
            continue
        ordem[i], ordem[j] = ordem[j], ordem[i]
        mud.append(('entra', pid(ordem[i]), pid(ordem[j]), indisponivel(pid(ordem[j]))))
    # 2) reservas
    for i in banco:
        s = ordem[i]
        if pid(s) is None or not indisponivel(pid(s)):
            continue
        papel = posicao(pid(s)) or ''
        j = candidato(fora, 'GL') if papel == 'GL' else None
        if j is None:
            cands = [k for k in fora if livre(ordem[k])]
            j = cands[0] if cands else None
        if j is None:
            continue
        ordem[i], ordem[j] = ordem[j], ordem[i]
        mud.append(('banco', pid(ordem[i]), pid(ordem[j]), indisponivel(pid(ordem[j]))))
    # 3) não relacionados: disponíveis primeiro, depois os indisponíveis, vagas vazias no fim
    resto = ordem[N_TIT + N_RES:]
    disp = [s for s in resto if livre(s)]
    ind = [s for s in resto if pid(s) is not None and not livre(s)]
    vaz = [s for s in resto if pid(s) is None]
    ordem[N_TIT + N_RES:] = disp + ind + vaz
    return ordem, mud


def _n(posicao, pid):
    return str(pid)


def validar(ordem, vg, indisponivel=None):
    """Confere uma ordem vinda da tela antes de gravar."""
    if len(ordem) != TAM or not lista_valida(ordem):
        raise ValueError('Escalação inválida.')
    if any(s >= len(vg) or vg[s] is None for s in ordem[:N_TIT]):
        raise ValueError('Faltam titulares: o time precisa de 11 jogadores.')
    if indisponivel:
        for s in ordem[:N_TIT + N_RES]:
            if s < len(vg) and vg[s] is not None and indisponivel(vg[s]):
                raise ValueError('Há jogador indisponível entre os relacionados.')


def gravar(car, esc, ordem):
    """Coloca a ordem na memória do save (a gravação no disco é feita por car.write)."""
    off = esc['off']
    atual = list(car.sf.data[off:off + TAM])
    if not lista_valida(atual) or sorted(atual) != sorted(ordem):
        raise RuntimeError('A escalação mudou de lugar no save.')
    car.sf.data[off:off + TAM] = bytes(ordem)
    esc['ordem'] = list(ordem)
