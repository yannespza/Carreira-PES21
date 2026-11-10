"""Gestão do clube além dos patrocínios: coletivas de imprensa, eventos do vestiário, movimentação do
elenco (chegadas e saídas), revisão anual dos contratos e prancheta. Tudo roda só no app (não mexe no save)."""
import random, datetime as dt
from .sim import d2s, s2d, fmt_eur, _seed

# ---------------- coletivas de imprensa ----------------
# cada resposta: texto, tom (para o rosto do técnico) e efeito em torcida e diretoria
PERGUNTAS = {
    'vitoria': [
        ('Vitória importante. O time já está no nível que você quer?',
         [('Ainda não. Gostei da entrega, mas temos muito a melhorar.', 'neutro', 1, 2),
          ('Sim! Esse grupo pode brigar por tudo nesta temporada.', 'feliz', 3, -1),
          ('O mérito é todo dos jogadores. Eu só organizo.', 'feliz', 2, 1)]),
        ('A torcida já sonha alto. Dá para pensar em título?',
         [('Pensamos jogo a jogo. Título se conquista no fim.', 'neutro', 0, 2),
          ('Quem não sonha não chega. Vamos com tudo!', 'feliz', 4, -1),
          ('Ainda é cedo. Precisamos de reforços para isso.', 'neutro', -1, 1)]),
    ],
    'goleada': [
        ('Uma goleada dessas mostra o quê sobre o time?',
         [('Mostra que o trabalho está dando resultado.', 'feliz', 3, 2),
          ('Foi um dia inspirado. Não dá para empolgar com um jogo.', 'neutro', 0, 2),
          ('Que o adversário respeite a gente daqui pra frente!', 'feliz', 4, -1)]),
    ],
    'empate': [
        ('O empate foi justo?',
         [('Merecíamos mais. Faltou capricho na finalização.', 'neutro', 1, 0),
          ('Foi justo. O adversário também jogou bem.', 'neutro', 0, 1),
          ('A arbitragem prejudicou a gente hoje.', 'irritado', 2, -2)]),
        ('A torcida cobrou no apito final. Como você recebe isso?',
         [('A torcida tem razão de cobrar. Vamos melhorar.', 'neutro', 2, 1),
          ('Peço paciência. O trabalho está no começo.', 'neutro', -1, 1),
          ('Quem está aqui dentro sabe o que está fazendo.', 'irritado', -3, -1)]),
    ],
    'derrota': [
        ('O que faltou hoje?',
         [('A responsabilidade é minha. Eu errei na escalação.', 'neutro', 2, -1),
          ('Faltou atitude de alguns jogadores.', 'irritado', 0, 0),
          ('Jogamos bem, o resultado não refletiu o jogo.', 'neutro', -2, 0)]),
        ('Seu cargo está ameaçado?',
         [('Tenho total confiança da diretoria e do grupo.', 'neutro', 0, 1),
          ('Isso não é comigo. Eu trabalho e o resto é com a diretoria.', 'irritado', -1, -2),
          ('Precisamos de reforços, e já pedi isso.', 'irritado', 1, -3)]),
    ],
    'vexame': [
        ('Uma derrota pesada. Qual a explicação?',
         [('Não há explicação. Peço desculpas à torcida.', 'irritado', 3, 0),
          ('Foi um apagão coletivo. Vamos rever tudo.', 'irritado', 1, 1),
          ('Um dia ruim não apaga o nosso trabalho.', 'neutro', -4, -2)]),
    ],
}


def tipo_partida(p, team_id):
    casa = p['mandante'] == team_id
    gp, gc = (p['gm'], p['gv']) if casa else (p['gv'], p['gm'])
    s = gp - gc
    return 'goleada' if s >= 3 else 'vitoria' if s > 0 else 'empate' if s == 0 else 'vexame' if s <= -3 else 'derrota'


class Gestao:
    def __init__(self, state, clube, team_id):
        self.s = state
        self.clube = clube
        self.team_id = team_id
        g = state.setdefault('gestao', {})
        g.setdefault('coletivas', [])
        g.setdefault('eventos', [])
        g.setdefault('transferencias', [])
        g.setdefault('prancheta', {})
        g.setdefault('revisoes', [])
        self.g = g

    # ---------- coletiva depois de cada jogo novo ----------
    def coletiva_nova(self, partida, nomes):
        if any(c['partida'] == partida['chave'] for c in self.g['coletivas']):
            return
        # a coletiva anterior que ficou sem resposta expira
        for c in self.g['coletivas']:
            if c['status'] == 'aberta':
                c['status'] = 'expirada'
        tipo = tipo_partida(partida, self.team_id)
        r = random.Random(_seed('col', partida['chave']))
        qs = r.sample(PERGUNTAS[tipo], min(2, len(PERGUNTAS[tipo])))
        casa = partida['mandante'] == self.team_id
        adv = nomes(partida['visitante'] if casa else partida['mandante'])
        gp, gc = (partida['gm'], partida['gv']) if casa else (partida['gv'], partida['gm'])
        self.g['coletivas'].append({
            'id': f"col{len(self.g['coletivas']) + 1}", 'partida': partida['chave'], 'data': partida['data'],
            'titulo': f"{self.clube} {gp} x {gc} {adv}", 'tipo': tipo, 'status': 'aberta',
            'perguntas': [{'texto': q, 'respostas': [a[0] for a in ans], 'efeitos': [list(a[1:]) for a in ans],
                           'escolha': None} for q, ans in qs]})
        self.g['coletivas'] = self.g['coletivas'][-30:]

    def responder(self, cid, q, a, mundo):
        c = next((x for x in self.g['coletivas'] if x['id'] == cid), None)
        if not c or c['status'] != 'aberta':
            raise ValueError('Essa coletiva já terminou.')
        perg = c['perguntas'][q]
        if perg['escolha'] is not None:
            raise ValueError('Pergunta já respondida.')
        perg['escolha'] = a
        tom, dt_torc, dt_dir = perg['efeitos'][a]
        mundo._torcida(dt_torc)
        mundo.m['diretoria'] = int(max(0, min(100, mundo.m['diretoria'] + dt_dir)))
        if all(p['escolha'] is not None for p in c['perguntas']):
            c['status'] = 'respondida'
            r = random.Random(_seed('colnot', cid))
            frase = c['perguntas'][0]['respostas'][c['perguntas'][0]['escolha']]
            mundo.m['noticias'].append({'data': self.s.get('data'), 'tipo': 'coletiva', 'destaque': False,
                                        'fonte': r.choice(['Lance!', 'Globo Esporte', 'ESPN', 'UOL Esporte']),
                                        'titulo': f'Técnico do {self.clube}: "{frase}"'})
        return tom

    # ---------- eventos do vestiário (só no app) ----------
    EVENTOS = [
        ('indisciplina', 'Atraso no treino', 'chegou atrasado ao treino e foi afastado', 4, 7, -1, -2),
        ('indisciplina', 'Balada antes do jogo', 'foi flagrado numa balada na véspera do jogo e está afastado', 7, 12, -4, -4),
        ('indisciplina', 'Discussão no vestiário', 'discutiu com companheiros e foi afastado pela comissão', 5, 9, -2, -3),
        ('pessoal', 'Problema familiar', 'foi liberado para resolver um problema familiar', 3, 7, 0, 0),
        ('pessoal', 'Intoxicação alimentar', 'teve uma intoxicação alimentar e está fora', 3, 5, 0, 0),
        ('pessoal', 'Acidente doméstico', 'sofreu um acidente doméstico e ficará fora', 7, 12, -1, 0),
    ]

    def semana(self, dia, elenco, mundo):
        """Chamado uma vez por semana da carreira: 6% de chance de um evento com um jogador do elenco."""
        if not elenco:
            return
        ds = d2s(dia)
        r = random.Random(_seed('evt', ds, self.clube))
        if r.random() > 0.06:
            return
        livres = [j for j in elenco if not self.afastado(j['id'], dia)]
        if not livres:
            return
        j = r.choice(livres)
        tipo, titulo, txt, dmin, dmax, dt_torc, dt_dir = r.choice(self.EVENTOS)
        dias = r.randint(dmin, dmax)
        volta = dia + dt.timedelta(days=dias)
        ev = {'id': f"ev{len(self.g['eventos']) + 1}", 'data': ds, 'jogador_id': j['id'], 'jogador': j['nome'],
              'tipo': tipo, 'titulo': titulo, 'texto': f"{j['nome']} {txt}. Volta prevista: {volta.strftime('%d/%m/%Y')}.",
              'volta': d2s(volta)}
        self.g['eventos'].append(ev)
        self.g['eventos'] = self.g['eventos'][-60:]
        mundo._torcida(dt_torc)
        mundo.m['diretoria'] = int(max(0, min(100, mundo.m['diretoria'] + dt_dir)))
        mundo.m['noticias'].append({'data': ds, 'tipo': 'evento', 'destaque': tipo == 'indisciplina',
                                    'fonte': r.choice(['Lance!', 'Globo Esporte', 'ESPN']),
                                    'titulo': f"{self.clube}: {ev['texto']}"})

    def afastado(self, pid, dia):
        for e in self.g['eventos']:
            if e['jogador_id'] == pid and s2d(e['data']) <= dia < s2d(e['volta']):
                return e
        return None

    # ---------- chegadas e saídas do elenco ----------
    def elenco_mudou(self, elenco, dinheiro, data):
        """Compara com a última leitura: ids novos são chegadas, ids que sumiram são saídas.
        O valor é estimado pela diferença do orçamento de transferências entre as duas leituras."""
        ids = [j['id'] for j in elenco]
        ant = self.g.get('elenco_ids')
        nomes = {j['id']: j['nome'] for j in elenco}
        nomes.update(self.g.get('elenco_nomes', {}) and {int(k): v for k, v in self.g['elenco_nomes'].items()
                                                          if int(k) not in nomes})
        orc = (dinheiro or {}).get('orc_transf')
        if ant is not None and ids:
            chegou = [i for i in ids if i not in ant]
            saiu = [i for i in ant if i not in ids]
            if chegou or saiu:
                diff = None
                if orc is not None and self.g.get('elenco_orc') is not None:
                    diff = orc - self.g['elenco_orc']
                n = len(chegou) + len(saiu)
                for i in chegou:
                    self.g['transferencias'].append({'data': data, 'tipo': 'chegada', 'id': i, 'nome': nomes.get(i, f'Jogador {i}'),
                                                     'valor': (diff / n if diff is not None and diff < 0 else None)})
                for i in saiu:
                    self.g['transferencias'].append({'data': data, 'tipo': 'saida', 'id': i, 'nome': nomes.get(i, f'Jogador {i}'),
                                                     'valor': (diff / n if diff is not None and diff > 0 else None)})
                self.g['transferencias'] = self.g['transferencias'][-200:]
        if ids:
            self.g['elenco_ids'] = ids
            self.g['elenco_orc'] = orc
            todos = {str(k): v for k, v in (self.g.get('elenco_nomes') or {}).items()}
            todos.update({str(j['id']): j['nome'] for j in elenco})
            self.g['elenco_nomes'] = todos

    # ---------- revisão anual dos contratos (janeiro) ----------
    def revisao_anual(self, engine, mundo, dia):
        ano = dia.year
        if dia.month != 1 or any(r['ano'] == ano for r in self.g['revisoes']):
            return
        ap = mundo.aproveitamento()
        if ap is None:
            self.g['revisoes'].append({'ano': ano, 'aproveitamento': None, 'mudancas': []})
            return
        fator = 1.15 if ap >= 70 else 1.08 if ap >= 60 else 0.85 if ap < 35 else 0.93 if ap < 45 else 1.0
        mud = []
        for c in engine.s['contratos']:
            if c['status'] != 'ativo' or fator == 1.0:
                continue
            futuros = [pg for pg in c['pagamentos'] if pg['status'] == 'agendado' and pg.get('tipo') != 'multa']
            if not futuros:
                continue
            novo = int(round(c['valor'] * fator / 50_000) * 50_000)
            for pg in futuros:
                pg['valor'] = novo
            mud.append({'empresa': c['empresa'], 'antes': c['valor'], 'depois': novo})
            c['valor'] = novo
        self.g['revisoes'].append({'ano': ano, 'aproveitamento': ap, 'fator': fator, 'mudancas': mud})
        if mud:
            subiu = fator > 1
            linhas = '\n'.join(f"• {m['empresa']}: {fmt_eur(m['antes'])} → {fmt_eur(m['depois'])}" for m in mud)
            engine.s['mensagens'].append({
                'id': engine._id(), 'data': d2s(dia), 'empresa': '__diretoria__', 'de': 'Departamento de marketing',
                'assunto': 'Revisão anual dos patrocínios', 'tipo': 'diretoria', 'oferta_id': None, 'lida': False,
                'texto': (f"Fechamos a revisão anual dos contratos com base no aproveitamento de {ap}% na temporada. "
                          + ('Os patrocinadores aceitaram reajustar para cima' if subiu else
                             'Com a campanha fraca, os patrocinadores reduziram as cotas')
                          + ' a partir das próximas parcelas:\n' + linhas)})


def cores_do_uniforme(img):
    """Duas cores principais da camisa (frente), para o tema do app."""
    from PIL import Image
    fr = img.convert('RGB').crop((720, 1100, 1330, 1850)).resize((96, 96))
    q = fr.quantize(colors=6, method=Image.Quantize.MEDIANCUT)
    pal = q.getpalette()[:18]
    cont = sorted(q.getcolors(), reverse=True)
    cores = [tuple(pal[i * 3:i * 3 + 3]) for _, i in cont]
    pri = cores[0]
    sec = next((c for c in cores[1:] if sum(abs(a - b) for a, b in zip(c, pri)) > 120), (255, 255, 255))
    hx = lambda c: '#%02x%02x%02x' % c
    return [hx(pri), hx(sec)]
