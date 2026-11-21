"""Conselho do clube: acordo de metas por temporada e eleição a cada 3 temporadas (efeito dentro do app).

- Metas: no começo da temporada o técnico escolhe UMA meta com o conselho. No fim da temporada o app confere:
  cumpriu = verba extra no orçamento de transferências (crédito no save) e confiança da diretoria; não cumpriu
  = confiança cai.
- Eleição: a cada 3 temporadas (a partir da primeira que o app viu). Situação x Oposição; o placar depende de
  títulos/posição, saldo em clássicos, humor da torcida, confiança da diretoria e caixa. Se a oposição vencer,
  o novo presidente chega cobrando: confiança da diretoria volta a 50 e a meta seguinte fica mais difícil.
  Se a situação vencer: +10 de confiança e uma verba de boas-vindas.
"""
import random

METAS = {
    'titulo': {'nome': 'Ser campeão brasileiro', 'premio': 6_000_000, 'conf': 15},
    'g4': {'nome': 'Terminar no G4 (Libertadores direto)', 'premio': 3_000_000, 'conf': 10},
    'caixa': {'nome': 'Terminar a temporada com mais caixa do que começou', 'premio': 2_500_000, 'conf': 8},
    'base': {'nome': 'Dar minutos à base (3 jogadores de até 21 anos com 10+ jogos)', 'premio': 2_000_000, 'conf': 8},
}


def _c(st):
    c = st.setdefault('conselho', {})
    c.setdefault('temporadas', {})
    c.setdefault('primeira', None)
    c.setdefault('eleicoes', [])
    return c


def temporada(st):
    return int(str(st.get('data') or '2026')[:4])


def escolher(st, meta):
    if meta not in METAS:
        raise ValueError('Meta inválida.')
    c = _c(st)
    t = str(temporada(st))
    reg = c['temporadas'].setdefault(t, {})
    if reg.get('meta') and reg.get('resultado'):
        raise ValueError('A meta desta temporada já foi avaliada.')
    reg['meta'] = meta
    reg['caixa_ini'] = (st.get('dinheiro') or {}).get('orc_transf')
    return reg


def avaliar(reg, pos_final, caixa_fim, jovens_10):
    m = reg.get('meta')
    if m == 'titulo':
        return pos_final == 1
    if m == 'g4':
        return bool(pos_final) and pos_final <= 4
    if m == 'caixa':
        return caixa_fim is not None and reg.get('caixa_ini') is not None and caixa_fim > reg['caixa_ini']
    if m == 'base':
        return jovens_10 >= 3
    return False


def processar(st, pos_atual, jovens_10, mundo_m, eleicao_info):
    """Chamado a cada leitura do save. Na virada de ano avalia a meta e, a cada 3 temporadas, faz a eleição.
    Devolve mensagens [(de, assunto, texto)]."""
    c = _c(st)
    t = temporada(st)
    msgs = []
    c['primeira'] = c['primeira'] or t
    reg_ant = c['temporadas'].get(str(t - 1))
    # guarda a última posição vista de cada temporada
    c['temporadas'].setdefault(str(t), {})['pos'] = pos_atual or c['temporadas'][str(t)].get('pos')
    if reg_ant and reg_ant.get('meta') and not reg_ant.get('resultado'):
        caixa = (st.get('dinheiro') or {}).get('orc_transf')
        ok = avaliar(reg_ant, reg_ant.get('pos'), caixa, reg_ant.get('jovens_10', 0))
        M = METAS[reg_ant['meta']]
        reg_ant['resultado'] = 'cumprida' if ok else 'não cumprida'
        if ok:
            st.setdefault('debitos', []).append({'data': st.get('data'), 'valor': -M['premio'], 'status': 'pendente',
                                                 'motivo': f"bônus do conselho: {M['nome'].lower()}", 'origem': 'conselho'})
            mundo_m['diretoria'] = int(min(100, mundo_m.get('diretoria', 60) + M['conf']))
            msgs.append(('Conselho deliberativo', 'Meta cumprida', f"Meta de {t - 1} cumprida: {M['nome']}. "
                         f"O conselho liberou € {M['premio'] / 1e6:.1f} mi a mais no orçamento."))
        else:
            mundo_m['diretoria'] = int(max(0, mundo_m.get('diretoria', 60) - M['conf']))
            msgs.append(('Conselho deliberativo', 'Meta não cumprida', f"A meta de {t - 1} ({M['nome']}) não foi cumprida. "
                         "A confiança do conselho caiu."))
    c['temporadas'][str(t)]['jovens_10'] = jovens_10
    # eleição: a cada 3 temporadas completas desde a primeira
    if (t - c['primeira']) > 0 and (t - c['primeira']) % 3 == 0 and not any(e['ano'] == t for e in c['eleicoes']):
        r = random.Random(f'eleicao|{t}')
        sit = 50
        sit += (mundo_m.get('torcida', 60) - 60) * 0.4
        sit += (mundo_m.get('diretoria', 60) - 60) * 0.3
        sit += eleicao_info.get('saldo_classicos', 0) * 2
        sit += {1: 12, 2: 6, 3: 4, 4: 3}.get(eleicao_info.get('pos'), -4 if (eleicao_info.get('pos') or 20) > 8 else 0)
        sit += r.uniform(-8, 8)
        sit = max(5, min(95, round(sit)))
        venceu = 'situação' if sit >= 50 else 'oposição'
        e = {'ano': t, 'situacao': sit, 'oposicao': 100 - sit, 'vencedor': venceu}
        c['eleicoes'].append(e)
        if venceu == 'situação':
            mundo_m['diretoria'] = int(min(100, mundo_m.get('diretoria', 60) + 10))
            st.setdefault('debitos', []).append({'data': st.get('data'), 'valor': -3_000_000, 'status': 'pendente',
                                                 'motivo': 'verba do novo mandato (situação reeleita)', 'origem': 'conselho'})
            msgs.append(('Conselho deliberativo', f'Eleição: situação vence com {sit}%',
                         'A chapa que apoia o seu trabalho foi reeleita. Mais confiança e uma verba extra de € 3 mi.'))
        else:
            mundo_m['diretoria'] = 50
            msgs.append(('Conselho deliberativo', f'Eleição: oposição vence com {100 - sit}%',
                         'A oposição assumiu o clube. O novo presidente chega cobrando resultado: a confiança volta a 50.'))
    return msgs


def view(st):
    c = _c(st)
    t = str(temporada(st))
    reg = c['temporadas'].get(t, {})
    prox = None
    if c['primeira']:
        n = int(t) - c['primeira']
        prox = int(t) + (3 - n % 3) if n % 3 else (int(t) if not any(e['ano'] == int(t) for e in c['eleicoes']) and n else int(t) + 3)
    return {'temporada': int(t), 'meta': reg.get('meta'), 'metas': METAS, 'eleicoes': c['eleicoes'][-5:],
            'proxima_eleicao': prox,
            'historico': {k: {'meta': v.get('meta'), 'resultado': v.get('resultado')} for k, v in c['temporadas'].items() if v.get('meta')}}
