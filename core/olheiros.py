"""Rede de olheiros: missões de busca no banco de jogadores da carreira (todos os clubes e os sem clube)."""
MISSOES = {
    'jovens': ('Talentos até 23 anos', 'Jovens com nível alto para a idade.'),
    'sem_clube': ('Sem clube', 'Jogadores livres: só o salário, sem taxa de transferência.'),
    'destaques': ('Destaques da temporada', 'Quem está jogando bem nas súmulas desta temporada.'),
    'experientes': ('Experientes prontos', 'Veteranos de nível alto para reforço imediato.'),
}


def buscar(pool, missao, meu_tid, pos=None, limite=25):
    L = [j for j in pool if j.get('time_id') != meu_tid and (not pos or j.get('pos') == pos)]
    if missao == 'jovens':
        L = [j for j in L if j.get('idade') and j['idade'] <= 23 and (j.get('cgj') or 0) >= 68]
        L.sort(key=lambda j: (-(j.get('cgj') or 0), j['idade']))
    elif missao == 'sem_clube':
        L = [j for j in L if j.get('clube') == 'Sem clube']
        L.sort(key=lambda j: -(j.get('cgj') or 0))
    elif missao == 'destaques':
        L = [j for j in L if (j.get('stats') or {}).get('jogos', 0) >= 5 and ((j.get('stats') or {}).get('nota_media') or 0) >= 6.6]
        L.sort(key=lambda j: -((j['stats'].get('nota_media') or 0) + j['stats'].get('gols', 0) * 0.05))
    else:
        L = [j for j in L if j.get('idade') and j['idade'] >= 30 and (j.get('cgj') or 0) >= 76]
        L.sort(key=lambda j: -(j.get('cgj') or 0))
    return [{k: j.get(k) for k in ('id', 'nome', 'pos', 'idade', 'cgj', 'clube', 'estilo', 'stats')} for j in L[:limite]]
