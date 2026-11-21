"""Motor físico único: sequência de jogos, minutos, clima, viagem e altitude no mesmo risco por jogador.

- Sequência = jogos seguidos com no máximo 4 dias de intervalo em que o jogador atuou 45 minutos ou mais
  (jogo por semana não acumula). Ficar fora de um jogo zera a sequência.
- Carga ambiental de cada jogo: calor forte (+1), temporal (+1), viagem longa (+1; voo fretado +0,5),
  altitude (+2 a partir de 2.500 m, +3 a partir de 3.400 m; anulada pela viagem antecipada ou se o clube também
  é de altitude).
- Verde: normal. Amarelo: 3 seguidos, ou 2 com carga, ou 360+ minutos em 14 dias. Vermelho: 4+ seguidos, ou 3 com
  carga pesada.
- Quem estava no vermelho e jogou: sorteio de lesão muscular (12% a 30%, vezes o fator de altitude, no máximo 2 por jogo) no
  processamento depois do jogo; a lesão vai para o departamento médico do app.
- O efeito em campo (força do time) vai pelo módulo AppCarreiraForca.lua: o adversário ganha +1 ou +2 de força
  quando o grupo está muito desgastado ou na altitude. Mesmo mecanismo do Dynamic_Difficulty do patch.

Logística (jogos fora): voo comercial (barato), voo fretado (metade do desgaste da viagem), viagem antecipada
(só altitude ≥ 2.500 m; anula a altitude, custa caro e tira um pouco de moral pela semana fora).
"""
import datetime as dt
import random

from . import cidades, matchday

LOGISTICA = {
    'comercial': {'nome': 'Voo comercial', 'viagem': 1.0, 'altitude': 1.0},
    'fretado': {'nome': 'Voo fretado', 'viagem': 0.5, 'altitude': 1.0},
    'aclimatacao': {'nome': 'Viagem antecipada (aclimatação)', 'viagem': 0.5, 'altitude': 0.0},
}


def custo_logistica(km, tipo):
    km = km or 0
    if tipo == 'comercial':
        return int(round((15_000 + 8 * km) / 1000)) * 1000
    if tipo == 'fretado':
        return int(round((60_000 + 25 * km) / 1000)) * 1000
    return int(round((210_000 + 25 * km) / 1000)) * 1000


def _d(s):
    return dt.date.fromisoformat(str(s)[:10])


def carga_jogo(clube_nome, mandante_nome, data, chave, fora, logistica='comercial'):
    """Carga ambiental de uma partida e os motivos."""
    c = matchday.clima_partida(mandante_nome, data, chave)
    meu = cidades.do_time(clube_nome) or {}
    lg = LOGISTICA.get(logistica, LOGISTICA['comercial'])
    pts, mot = 0.0, []
    if c['calor']:
        pts += 1; mot.append('calor')
    if 'Temporal' in ' '.join(c['alertas']):
        pts += 1; mot.append('temporal')
    km = cidades.distancia_km(meu, cidades.do_time(mandante_nome)) if fora else 0
    if km and km >= 1000:
        pts += lg['viagem']; mot.append(f'viagem de {km} km')
    alt = c.get('altitude') or 0
    fator_alt = 1.0
    if fora and alt >= 2500 and (meu.get('altitude') or 0) < 2500:
        a = 3 if alt >= 3400 else 2
        fator_alt = (1.8 if alt >= 3400 else 1.35) if lg['altitude'] else 1.0
        if lg['altitude']:
            pts += a; mot.append(f'altitude de {alt} m')
        else:
            mot.append('altitude anulada pela aclimatação')
    return {'pontos': pts, 'motivos': mot, 'km': km, 'altitude': alt, 'fator_alt': fator_alt, 'clima': c}


def estado_jogadores(partidas, team_id, elenco, hoje, cargas):
    """Risco de cada jogador do elenco para o próximo jogo."""
    jogos = sorted([p for p in partidas if team_id in (p['mandante'], p['visitante'])], key=lambda p: p['data'])
    out = {}
    for j in elenco:
        pid = j['id']
        seq, carga, ult_data = 0, 0.0, None
        for p in reversed(jogos):
            lado = p['escalacao_mandante'] if p['mandante'] == team_id else p['escalacao_visitante']
            x = next((x for x in lado if x['id'] == pid), None)
            if ult_data and (_d(ult_data) - _d(p['data'])).days > 4:
                break
            if not x or x['min'] < 45:
                break
            seq += 1
            carga += (cargas.get(p['data']) or {}).get('pontos', 0)
            ult_data = p['data']
        if ult_data is None and jogos:
            pass
        # a sequência só vale se o último jogo dela foi recente (até 4 dias antes de hoje)
        ultimo = None
        for p in reversed(jogos):
            lado = p['escalacao_mandante'] if p['mandante'] == team_id else p['escalacao_visitante']
            if any(x['id'] == pid and x['min'] for x in lado):
                ultimo = p['data']
                break
        if seq and ultimo and (hoje - _d(ultimo)).days > 4:
            seq, carga = 0, 0.0
        m14 = 0
        for p in jogos:
            if 0 <= (hoje - _d(p['data'])).days <= 14:
                lado = p['escalacao_mandante'] if p['mandante'] == team_id else p['escalacao_visitante']
                m14 += sum(x['min'] for x in lado if x['id'] == pid)
        if seq >= 4 or (seq >= 3 and carga >= 2):
            nivel = 'vermelho'
        elif seq >= 3 or (seq >= 2 and carga >= 1) or m14 >= 360:
            nivel = 'amarelo'
        else:
            nivel = 'verde'
        out[pid] = {'id': pid, 'nome': j['nome'], 'pos': j.get('pos', ''), 'seq': seq, 'carga': round(carga, 1),
                    'min14': m14, 'nivel': nivel}
    return out


def prob_lesao(info, fator_alt):
    # calibrado em 20/11/2026: 45-65% derrubou 5 titulares de uma vez; agora 12% a 30% (altitude até 45%)
    return round(min(0.45, min(0.30, 0.12 + 0.03 * max(0, info['seq'] - 4)) * fator_alt), 2)

MAX_LESOES_JOGO = 2


def rolar_lesoes(st, partidas, team_id, hoje):
    """Quem jogou estando no vermelho (risco guardado antes do jogo): sorteio de lesão muscular."""
    F = st.setdefault('fadiga', {})
    antes = F.get('antes') or {}
    feitos = []
    for data, snap in list(antes.items()):
        p = next((p for p in partidas if p['data'] == data and team_id in (p['mandante'], p['visitante'])), None)
        if not p:
            if data < str(hoje - dt.timedelta(days=10)):
                antes.pop(data, None)
            continue
        lado = p['escalacao_mandante'] if p['mandante'] == team_id else p['escalacao_visitante']
        jogou = {x['id']: x['min'] for x in lado}
        fator = snap.get('_fator_alt', 1.0)
        n_les = 0
        for pid_s, info in sorted(snap.items(), key=lambda kv: -(kv[1].get('seq', 0) if isinstance(kv[1], dict) else 0)):
            if n_les >= MAX_LESOES_JOGO:
                break
            if pid_s.startswith('_') or info['nivel'] != 'vermelho':
                continue
            pid = int(pid_s)
            if not jogou.get(pid):
                continue
            pr = prob_lesao(info, fator)
            r = random.Random(f'lesao|{data}|{pid}')
            if r.random() < pr:
                dias = r.randint(7, 21)
                volta = _d(data) + dt.timedelta(days=dias + 1)
                tipo = r.choice(['estiramento muscular', 'contratura na coxa', 'lesão na panturrilha'])
                ev = {'id': f'fad{data}{pid}', 'data': data, 'jogador_id': pid, 'jogador': info['nome'],
                      'tipo': 'lesao', 'titulo': 'Lesão muscular (desgaste)',
                      'texto': f"{info['nome']} sofreu {tipo} depois de jogar no limite físico. Volta prevista: "
                               f"{volta.strftime('%d/%m/%Y')}.", 'volta': volta.isoformat()}
                st.setdefault('gestao', {}).setdefault('eventos', []).append(ev)
                feitos.append(ev)
                n_les += 1
        antes.pop(data, None)
    F['antes'] = antes
    return feitos


def forca_adversario(riscos, titulares_ids, carga_prox):
    """Força extra do adversário no módulo do jogo (0 a 2) pelo desgaste do nosso time e pela altitude."""
    vermelhos = sum(1 for i in titulares_ids if (riscos.get(i) or {}).get('nivel') == 'vermelho')
    amarelos = sum(1 for i in titulares_ids if (riscos.get(i) or {}).get('nivel') == 'amarelo')
    f = 0
    motivos = []
    if vermelhos >= 3 or vermelhos * 2 + amarelos >= 8:
        f += 1; motivos.append(f'{vermelhos} titulares no limite físico')
    if carga_prox and carga_prox.get('fator_alt', 1) > 1:
        f += 1; motivos.append(f"altitude de {carga_prox['altitude']} m")
    return min(2, f), motivos
