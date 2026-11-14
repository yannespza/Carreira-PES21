"""Índice rápido do código: lista def/class/constantes (Python) e funções JS da interface com arquivo:linha.
Uso: python3 ferramentas/indice.py [termo]   (sem termo, lista tudo)"""
import os, re, sys
RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
termo = (sys.argv[1] if len(sys.argv) > 1 else '').lower()
PY = re.compile(r'^(\s*)(def|class)\s+(\w+)|^([A-Z][A-Z0-9_]{2,})\s*=')
JS = re.compile(r'^\s*(?:async\s+)?function\s+(\w+)')
arqs = ['app.py'] + sorted('core/' + f for f in os.listdir(os.path.join(RAIZ, 'core')) if f.endswith('.py')) + ['web/index.html']
for a in arqs:
    for n, linha in enumerate(open(os.path.join(RAIZ, a), encoding='utf-8'), 1):
        m = (JS if a.endswith('.html') else PY).match(linha)
        if not m:
            continue
        nome = m.group(1) if a.endswith('.html') else (m.group(3) or m.group(4))
        tipo = 'js' if a.endswith('.html') else (m.group(2) or 'const')
        if termo and termo not in nome.lower() and termo not in a.lower():
            continue
        ind = '  ' if not a.endswith('.html') and m.group(1) else ''
        print(f'{a}:{n}\t{ind}{tipo} {nome}')
