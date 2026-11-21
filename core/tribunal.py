"""Tribunal desportivo: vermelho direto abre processo; o técnico escolhe a defesa antes do próximo jogo.

- Só vermelho DIRETO (o save marca expulsão sem amarelo); expulsão por 2º amarelo não vai a julgamento.
- O próprio jogo já suspende 1 partida pelo vermelho. O tribunal pode somar partidas a essa.
- Defesa do clube (grátis): pena total de 2 a 4 jogos. Banca de advogados (custa do orçamento): absolvição,
  1 jogo ou no máximo 2.
- A pena vira um afastamento do app (mesmo mecanismo do departamento médico): o jogador fica bloqueado na
  escalação do app até depois do último jogo da pena. Dentro do PES ele continua escalável.
- Cartões só existem nas partidas jogadas por você (nas simuladas o jogo não grava cartões).
"""
import datetime as dt
import random

CUSTO_ADV = 120_000          # euros
ESTRATEGIAS = {
    'padrao': {'nome': 'Defesa do clube', 'custo': 0},
    'advogados': {'nome': 'Banca de advogados', 'custo': CUSTO_ADV},
}


def _d(s):
    return dt.date.fromisoformat(str(s)[:10])


def detectar(st, partidas, team_id, nomes_jog, nomes_clubes):
    """Abre processos novos para vermelhos diretos do clube. Devolve a lista de processos abertos agora."""
    T = st.setdefault('tribunal', {'processos': []})
    vistos = {p['id'] for p in T['processos']}
    novos = []
    for p in partidas:
        if team_id not in (p['mandante'], p['visitante']):
            continue
        casa = p['mandante'] == team_id
        meus = p['escalacao_mandante'] if casa else p['escalacao_visitante']
        if not any(not x['titular'] for x in meus):
            continue          # partida simulada: o jogo não grava cartões
        adv = p['visitante'] if casa else p['mandante']
        for x in meus:
            if x['vermelho'] and not x['amarelo']:
                pid = f"{p['data']}-{x['id']}"
                if pid in vistos:
                    continue
                proc = {'id': pid, 'jogador_id': x['id'], 'jogador': (nomes_jog.get(x['id']) or {}).get('nome') or f"Jogador {x['id']}",
                        'data_jogo': p['data'], 'adversario': nomes_clubes.get(adv, f'Time {adv}'),
                        'status': 'aguardando', 'aberto_em': st.get('data')}
                T['processos'].append(proc)
                novos.append(proc)
    T['processos'] = T['processos'][-40:]
    return novos


def julgar(st, proc_id, estrategia, proximos, hoje):
    """Julga o processo com a defesa escolhida. Devolve o processo julgado (com pena e afastamento)."""
    T = st.setdefault('tribunal', {'processos': []})
    proc = next((p for p in T['processos'] if p['id'] == proc_id), None)
    if not proc or proc['status'] != 'aguardando':
        raise ValueError('Processo não encontrado ou já julgado.')
    if estrategia not in ESTRATEGIAS:
        raise ValueError('Defesa inválida.')
    r = random.Random(f"trib|{proc_id}|{estrategia}")
    if estrategia == 'padrao':
        total = r.choices([2, 3, 4], weights=[45, 35, 20])[0]
    else:
        total = r.choices([1, 2, 3], weights=[55, 35, 10])[0]
    extra = max(0, total - 1)          # 1 jogo o próprio PES já cumpre
    proc.update(status='julgado', estrategia=estrategia, pena_total=total, pena_extra=extra, julgado_em=hoje,
                custo=ESTRATEGIAS[estrategia]['custo'])
    if estrategia == 'advogados':
        st.setdefault('debitos', []).append({'data': hoje, 'valor': CUSTO_ADV, 'status': 'pendente',
                                             'motivo': f"advogados no tribunal ({proc['jogador']})", 'origem': 'tribunal'})
    proc['resultado'] = ('absolvido: cumpre só o jogo automático' if extra == 0 else
                         f'suspenso por {total} jogos ({extra} além do automático)')
    if extra:
        # o jogo automático é o próximo; a pena extra cobre os 'extra' jogos seguintes
        futuros = sorted({p['data'] for p in proximos if not p.get('jogada') and p['data'] > str(hoje)})
        alvo = futuros[min(len(futuros) - 1, extra)] if futuros else None
        volta = (_d(alvo) + dt.timedelta(days=1)) if alvo else (_d(hoje) + dt.timedelta(days=7 * extra + 4))
        g = st.setdefault('gestao', {}).setdefault('eventos', [])
        ev = {'id': f"trib{proc_id}", 'data': str(hoje), 'jogador_id': proc['jogador_id'], 'jogador': proc['jogador'],
              'tipo': 'suspensao', 'titulo': 'Suspensão (tribunal)',
              'texto': f"{proc['jogador']} foi suspenso por {total} jogos pelo tribunal. Volta: {volta.strftime('%d/%m/%Y')}.",
              'volta': volta.isoformat()}
        g.append(ev)
        proc['volta'] = volta.isoformat()
    return proc


def julgar_vencidos(st, proximos, hoje):
    """Processo sem defesa escolhida até o dia do próximo jogo vai com a defesa do clube."""
    feitos = []
    prox = min((p['data'] for p in proximos if not p.get('jogada')), default=None)
    for p in list((st.get('tribunal') or {}).get('processos', [])):
        if p['status'] == 'aguardando' and prox and str(hoje) >= prox:
            feitos.append(julgar(st, p['id'], 'padrao', proximos, hoje))
    return feitos


def view(st):
    T = st.get('tribunal') or {}
    return {'processos': list(reversed(T.get('processos', [])))[:15],
            'estrategias': ESTRATEGIAS}
