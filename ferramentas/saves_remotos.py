"""Ferramenta do Claude para os saves enviados ao repositório privado (carreira-pes21-saves).

Uso (numa cópia do repositório de saves):
  python3 ferramentas/saves_remotos.py abrir  <arquivo.pesz> [pasta_saida]
      recria o save original (ML.../EDIT...) e grava também o decriptado (.dec) para análise
  python3 ferramentas/saves_remotos.py comparar <antes.pesz> <depois.pesz> [--max 60]
      lista os trechos que mudaram entre as duas versões (posição, tamanho, valores antes/depois)
  python3 ferramentas/saves_remotos.py montar <arquivo.pesz> <pasta_sim>
      coloca o save em <pasta_sim>/10000002/save/ para rodar o app de teste (/tmp/sim)"""
import os, sys, struct
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from core.copia_remota import desempacotar      # noqa: E402
from core import pescrypt                        # noqa: E402


def _nome(p):
    b = os.path.basename(p).replace('.pesz', '')
    return b.split('_', 1)[1] if '_' in b else b


def abrir(p, saida='.'):
    raw, dec = desempacotar(open(p, 'rb').read())
    if dec is None:
        dec = bytes(pescrypt.decrypt(raw).data)
    os.makedirs(saida, exist_ok=True)
    n = _nome(p)
    open(os.path.join(saida, n), 'wb').write(raw)
    open(os.path.join(saida, n + '.dec'), 'wb').write(dec)
    print(f'{n}: {len(raw)} bytes (original), {len(dec)} bytes decriptado -> {saida}')
    return raw, dec


def comparar(a, b, maximo=60):
    _, da = desempacotar(open(a, 'rb').read())
    _, db = desempacotar(open(b, 'rb').read())
    da = da if da is not None else bytes(pescrypt.decrypt(desempacotar(open(a, 'rb').read())[0]).data)
    db = db if db is not None else bytes(pescrypt.decrypt(desempacotar(open(b, 'rb').read())[0]).data)
    n = min(len(da), len(db))
    if len(da) != len(db):
        print(f'tamanhos diferentes: {len(da)} x {len(db)}')
    import numpy as np
    x = np.frombuffer(da[:n], np.uint8)
    y = np.frombuffer(db[:n], np.uint8)
    dif = np.nonzero(x != y)[0]
    print(f'{len(dif)} bytes diferentes')
    blocos, ini, ult = [], None, None
    for i in dif:
        if ini is None:
            ini = ult = int(i)
        elif i - ult <= 8:
            ult = int(i)
        else:
            blocos.append((ini, ult))
            ini = ult = int(i)
    if ini is not None:
        blocos.append((ini, ult))
    print(f'{len(blocos)} trechos alterados')
    for ini, fim in blocos[:maximo]:
        a0 = ini - ini % 4
        t = min(fim - a0 + 4, 32)
        va = ' '.join(f'{v:08x}' for v in struct.unpack_from(f'<{t // 4}I', da, a0)) if a0 + t <= n else ''
        vb = ' '.join(f'{v:08x}' for v in struct.unpack_from(f'<{t // 4}I', db, a0)) if a0 + t <= n else ''
        print(f'0x{ini:07x} ({fim - ini + 1} B)\n   antes:  {va}\n   depois: {vb}')
    return blocos


def montar(p, pasta_sim):
    dst = os.path.join(pasta_sim, '10000002', 'save')
    abrir(p, dst)
    os.remove(os.path.join(dst, _nome(p) + '.dec'))
    print('pronto para o app de teste em', dst)


if __name__ == '__main__':
    if len(sys.argv) < 3:
        print(__doc__)
        sys.exit(1)
    cmd = sys.argv[1]
    if cmd == 'abrir':
        abrir(sys.argv[2], sys.argv[3] if len(sys.argv) > 3 else '.')
    elif cmd == 'comparar':
        mx = int(sys.argv[sys.argv.index('--max') + 1]) if '--max' in sys.argv else 60
        comparar(sys.argv[2], sys.argv[3], mx)
    elif cmd == 'montar':
        montar(sys.argv[2], sys.argv[3])
    else:
        print(__doc__)
