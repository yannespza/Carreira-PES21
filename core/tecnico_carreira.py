"""Carreira do técnico que continua entre as carreiras do jogo.

Fica num arquivo só dele (data/tecnico/carreira.json), fora do estado de cada save. Cada clube comandado vira
uma passagem com jogos, aproveitamento, títulos, acessos, rebaixamentos e como terminou (demissão, saída).
Com isso o app calcula o prestígio do técnico (0 a 100), que vai junto para qualquer clube:
- soma (ou tira) atratividade para os patrocinadores do clube que ele estiver comandando;
- define a confiança inicial da diretoria quando ele chega num clube novo;
- deixa as metas da diretoria um pouco mais exigentes para técnico consagrado."""
import os, json, datetime as dt
from .sim import TITULO_PESO, COMP_NOMES

NIVEIS = [(80, 'Lenda'), (65, 'Consagrado'), (50, 'Respeitado'), (35, 'Promissor'), (0, 'Desconhecido')]


def _p(data_dir):
    return os.path.join(data_dir, 'tecnico', 'carreira.json')


def carregar(data_dir):
    try:
        return json.load(open(_p(data_dir), encoding='utf-8'))
    except (OSError, ValueError):
        return {'passagens': []}


def salvar(data_dir, c):
    os.makedirs(os.path.dirname(_p(data_dir)), exist_ok=True)
    tmp = _p(data_dir) + '.tmp'
    json.dump(c, open(tmp, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    os.replace(tmp, _p(data_dir))


def _stats(state):
    ps = state.get('partidas', [])
    tid = state.get('time_id')
    s = {'jogos': len(ps), 'V': 0, 'E': 0, 'D': 0, 'gp': 0, 'gc': 0}
    for p in ps:
        s[p['res']] += 1
        casa = p['mandante'] == tid
        s['gp'] += p['gm'] if casa else p['gv']
        s['gc'] += p['gv'] if casa else p['gm']
    g = state.get('gestao') or {}
    s['titulos'] = [{'comp': t['comp'], 'data': t['data']} for t in g.get('titulos', [])]
    temps = g.get('temporadas', [])
    s['acessos'] = sum(1 for t in temps if t.get('acesso'))
    s['rebaixamentos'] = sum(1 for t in temps if t.get('rebaixado'))
    s['temporadas'] = [{'ano': t['ano'], 'pos': t['pos'], 'divisao': t.get('divisao')} for t in temps]
    e = g.get('emprego') or {}
    s['saida'] = e.get('status') if e.get('status') in ('demitido', 'saiu') else None
    s['motivo_saida'] = e.get('motivo') if s['saida'] else None
    return s


def registrar(data_dir, chave, state, clube, hoje):
    """Atualiza a passagem atual com os números do estado da carreira. Devolve a carreira inteira."""
    c = carregar(data_dir)
    ps = c.setdefault('passagens', [])
    atual = next((p for p in ps if p['chave'] == chave), None)
    nova = atual is None
    if nova:
        atual = {'chave': chave, 'clube': clube, 'team_id': state.get('time_id'),
                 'inicio': state.get('data') or (hoje and hoje.isoformat())}
        ps.append(atual)
    for p in ps:                       # as outras passagens ficam encerradas
        if p is not atual and p.get('ativa'):
            p['ativa'] = False
            p['fim'] = p.get('ultima_leitura') or p.get('inicio')
    atual.update(_stats(state), ativa=True, clube=clube, team_id=state.get('time_id'),
                 ultima_leitura=state.get('data'))
    c['prestigio'] = prestigio(c)
    salvar(data_dir, c)
    return c, nova


def prestigio(c):
    ps = c.get('passagens', [])
    v = 45.0
    jogos = sum(p.get('jogos', 0) for p in ps)
    if jogos:
        pts = sum(3 * p.get('V', 0) + p.get('E', 0) for p in ps)
        ap = 100 * pts / (3 * jogos)
        v += max(-12, min(12, (ap - 50) / 2)) * min(1, jogos / 38)
    for p in ps:
        v += sum(TITULO_PESO.get(t['comp'], 1) * 4 for t in p.get('titulos', []))
        v += 5 * p.get('acessos', 0) - 8 * p.get('rebaixamentos', 0)
        if p.get('saida') == 'demitido':
            v -= 5
        elif p.get('saida') == 'saiu':
            v += 2
    v += min(6, len(ps) - 1) if len(ps) > 1 else 0      # rodagem
    return int(max(5, min(100, round(v))))


def nivel(prest):
    return next(n for lim, n in NIVEIS if prest >= lim)


def bonus_atratividade(prest):
    return int(round(((prest or 50) - 50) / 5))


def confianca_inicial(prest):
    return int(max(40, min(85, 60 + ((prest or 50) - 50) / 2)))


def view(c):
    ps = c.get('passagens', [])
    tot = {'jogos': 0, 'V': 0, 'E': 0, 'D': 0, 'gp': 0, 'gc': 0, 'titulos': 0}
    for p in ps:
        for k in ('jogos', 'V', 'E', 'D', 'gp', 'gc'):
            tot[k] += p.get(k, 0)
        tot['titulos'] += len(p.get('titulos', []))
    ap = round(100 * (3 * tot['V'] + tot['E']) / (3 * tot['jogos'])) if tot['jogos'] else None
    pr = c.get('prestigio', prestigio(c))
    return {'prestigio': pr, 'nivel': nivel(pr), 'bonus': bonus_atratividade(pr), 'aproveitamento': ap, **tot,
            'passagens': [{**p, 'titulos_nomes': [COMP_NOMES.get(t['comp'], t['comp']) for t in p.get('titulos', [])]}
                          for p in ps][::-1]}
