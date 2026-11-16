"""Finanças reais dos clubes da Série A 2026 (balanços de 2025), para o mercado de transferências do app.

Dados em core/clubes_financas_2025.json (R$ milhões, valores reais, não do jogo):
receita de 2025, dívida total (Anresf), vendas de jogadores em 2025, índice de poder financeiro (0 a 100),
faixa do clube e orçamento sugerido por janela. Fontes: Sports Value, UOL, Anresf, balanços de Flamengo
e Palmeiras. Receita marcada como estimada quando o clube não publicou o número.

Uso previsto: o diretor de futebol decide quem compra e quanto cada clube pode pagar por janela.
Clubes fora da lista (Série B, estrangeiros) ganham um índice estimado pelo ranking (core/ranking.py).
Nada aqui grava no save."""
import json, os

ARQ = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'clubes_financas_2025.json')
COTACAO = 4.3          # R$ por euro, a mesma do jogo
_cache = None


def _dados():
    global _cache
    if _cache is None:
        try:
            with open(ARQ, encoding='utf-8') as f:
                d = json.load(f)
            _cache = {int(c['time_id']): c for c in d.get('clubes', []) if c.get('time_id') is not None}
        except Exception:
            _cache = {}
    return _cache


def _estimado(time_id):
    """Clube sem balanço na lista: índice a partir do ranking do app (valor do elenco, torcida, prestígio)."""
    try:
        from . import ranking
        c = ranking.CLUBES.get(int(time_id))
    except Exception:
        c = None
    if not c:
        return None
    nota = 0.45 * min(1.0, c[3] / 200) * 100 + 0.30 * c[4] + 0.25 * c[5]
    idx = max(5, min(60, round(nota * 0.6)))
    receita = round(150 * (2089 / 150) ** (idx / 100))
    return {'clube': c[0], 'time_id': int(time_id), 'receita_2025_mi': receita, 'receita_estimada': True,
            'divida_mi': None, 'indice_poder': idx, 'faixa': faixa(idx),
            'orcamento_janela_sugerido_mi': round(0.25 * receita), 'estimado_pelo_ranking': True}


def faixa(idx):
    return 'elite' if idx >= 75 else 'forte' if idx >= 50 else 'medio' if idx >= 25 else 'pequeno'


def clube(time_id):
    """Dados financeiros do clube (dicionário) ou None se não houver nada sobre ele."""
    try:
        tid = int(time_id)
    except (TypeError, ValueError):
        return None
    return _dados().get(tid) or _estimado(tid)


def indice(time_id, padrao=20):
    c = clube(time_id)
    return c['indice_poder'] if c else padrao


def orcamento_janela_eur(time_id):
    """Quanto o clube pode gastar por janela, em euros (para comparar com os valores do jogo)."""
    c = clube(time_id)
    if not c:
        return 0
    return round(c['orcamento_janela_sugerido_mi'] * 1_000_000 / COTACAO)


def todos():
    return sorted(_dados().values(), key=lambda c: -c['indice_poder'])
