"""Procura num save (ML...) ou no EDIT a tabela Team-Player descrita na wiki do PES 2021 (Edit file):
registro de 284 bytes = time(4) + 40 ids de jogador (4 cada) + 40 camisas (2 cada) + 40 bytes desconhecidos.
Uso: python3 ferramentas/achar_team_player.py <arquivo ou .pesz>  (mostra onde há sequências de registros assim)"""
import os, sys, struct
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
from core import pescrypt

R = 284


def carregar(caminho):
    raw = open(caminho, 'rb').read()
    if caminho.endswith('.pesz'):
        from core import copia_remota
        raw = copia_remota.desempacotar(raw)
        return raw if isinstance(raw, (bytes, bytearray)) and not hasattr(raw, 'data') else getattr(raw, 'data', raw)
    return pescrypt.decrypt(raw).data


def registro_ok(d, o):
    if o + R > len(d):
        return None
    if not struct.unpack_from('<I', d, o)[0]:      # o ID do time nunca é 0
        return None
    ids = struct.unpack_from('<40I', d, o + 4)
    n = 0
    while n < 40 and ids[n]:
        n += 1
    if n < 1 or any(ids[n:]):                      # nomes primeiro, zeros depois
        return None
    if len(set(ids[:n])) != n:
        return None
    cam = struct.unpack_from('<40H', d, o + 0xA4)
    if any(c > 999 for c in cam):
        return None
    return struct.unpack_from('<I', d, o)[0], n


def procurar(d, minimo=8):
    achados, o = [], 0
    while o + R <= len(d):
        r = registro_ok(d, o)
        if r:
            k, p = 1, o + R
            while registro_ok(d, p):
                k += 1
                p += R
            if k >= minimo:
                achados.append((o, k))
                o = p
                continue
        o += 4
    return achados


if __name__ == '__main__':
    d = carregar(sys.argv[1])
    res = procurar(d)
    if not res:
        print('nenhuma tabela Team-Player (284 bytes) encontrada')
    for o, k in res:
        print(f'offset 0x{o:X}: {k} times seguidos; primeiros times:', [registro_ok(d, o + i * R)[0] for i in range(min(k, 5))])
