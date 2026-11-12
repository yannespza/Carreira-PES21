"""Gestão do clube além dos patrocínios: coletivas de imprensa, eventos do vestiário, movimentação do
elenco (chegadas e saídas), revisão anual dos contratos e prancheta. Tudo roda só no app (não mexe no save)."""
import random, datetime as dt
from .sim import d2s, s2d, fmt_eur, _seed, TITULO_PESO, COMP_NOMES, comp_de

# ---------------- coletivas de imprensa ----------------
# cada resposta: texto, tom (rosto do técnico), efeito na torcida, efeito na diretoria e o estilo da resposta.
# O estilo mexe no vestiário (vestiario.coletiva) e na relação com a imprensa (REACAO abaixo).
PERGUNTAS = {
    'vitoria': [
        ('Vitória importante. O time já está no nível que você quer?',
         [('Ainda não. Gostei da entrega, mas temos muito a melhorar.', 'neutro', 1, 2, 'humilde'),
          ('Sim! Esse grupo pode brigar por tudo nesta temporada.', 'feliz', 3, -1, 'empolgar'),
          ('O mérito é todo dos jogadores. Eu só organizo.', 'feliz', 2, 1, 'proteger')]),
        ('A torcida já sonha alto. Dá para pensar em título?',
         [('Pensamos jogo a jogo. Título se conquista no fim.', 'neutro', 0, 2, 'corporativo'),
          ('Quem não sonha não chega. Vamos com tudo!', 'feliz', 4, -1, 'empolgar'),
          ('Ainda é cedo. Precisamos de reforços para isso.', 'neutro', -1, 1, 'pressao')]),
    ],
    'goleada': [
        ('Uma goleada dessas mostra o quê sobre o time?',
         [('Mostra que o trabalho está dando resultado.', 'feliz', 3, 2, 'corporativo'),
          ('Foi um dia inspirado. Não dá para empolgar com um jogo.', 'neutro', 0, 2, 'humilde'),
          ('Que o adversário respeite a gente daqui pra frente!', 'feliz', 4, -1, 'provocar')]),
    ],
    'empate': [
        ('O empate foi justo?',
         [('Merecíamos mais. Faltou capricho na finalização.', 'neutro', 1, 0, 'corporativo'),
          ('Foi justo. O adversário também jogou bem.', 'neutro', 0, 1, 'humilde'),
          ('A arbitragem prejudicou a gente hoje.', 'irritado', 2, -2, 'arbitragem')]),
        ('A torcida cobrou no apito final. Como você recebe isso?',
         [('A torcida tem razão de cobrar. Vamos melhorar.', 'neutro', 2, 1, 'culpa'),
          ('Peço paciência. O trabalho está no começo.', 'neutro', -1, 1, 'humilde'),
          ('Quem está aqui dentro sabe o que está fazendo.', 'irritado', -3, -1, 'proteger')]),
    ],
    'derrota': [
        ('O que faltou hoje?',
         [('A responsabilidade é minha. Eu errei na escalação.', 'neutro', 2, -1, 'culpa'),
          ('Faltou atitude de alguns jogadores.', 'irritado', 0, 0, 'expor'),
          ('Jogamos bem, o resultado não refletiu o jogo.', 'neutro', -2, 0, 'corporativo')]),
        ('Seu cargo está ameaçado?',
         [('Tenho total confiança da diretoria e do grupo.', 'neutro', 0, 1, 'corporativo'),
          ('Isso não é comigo. Eu trabalho e o resto é com a diretoria.', 'irritado', -1, -2, 'provocar'),
          ('Precisamos de reforços, e já pedi isso.', 'irritado', 1, -3, 'pressao')]),
    ],
    'vexame': [
        ('Uma derrota pesada. Qual a explicação?',
         [('Não há explicação. Peço desculpas à torcida.', 'irritado', 3, 0, 'culpa'),
          ('Foi um apagão coletivo. Vamos rever tudo.', 'irritado', 1, 1, 'humilde'),
          ('Alguns jogadores não honraram a camisa hoje.', 'irritado', 1, -1, 'expor')]),
    ],
    # clássicos
    'classico_v': [
        ('Vitória no clássico. Qual o recado para o rival?',
         [('Respeito o adversário. Hoje fomos melhores, só isso.', 'feliz', 1, 2, 'humilde'),
          ('A cidade tem dono. Eles sabem quem manda aqui!', 'feliz', 5, -1, 'provocar'),
          ('Essa vitória é da torcida, que empurrou o time o jogo todo.', 'feliz', 4, 1, 'proteger')]),
    ],
    'classico_e': [
        ('Empate no clássico. Fica um gosto amargo?',
         [('Clássico é sempre equilibrado. O ponto tem valor.', 'neutro', -1, 1, 'corporativo'),
          ('Fica, sim. A gente queria muito essa vitória pela torcida.', 'neutro', 2, 1, 'culpa'),
          ('O juiz não deixou o jogo correr. Faltou critério.', 'irritado', 1, -2, 'arbitragem')]),
    ],
    'classico_d': [
        ('Perder o clássico dói mais. Como fica o ambiente?',
         [('Dói muito. Peço desculpas à torcida, a culpa é minha.', 'irritado', 3, 0, 'culpa'),
          ('Alguns jogadores sentiram o peso do jogo.', 'irritado', 0, -1, 'expor'),
          ('É só um jogo. A temporada é longa.', 'neutro', -4, 0, 'corporativo')]),
    ],
    # perguntas de situação (entram como terceira pergunta quando o momento pede)
    'pressao': [
        ('A diretoria deu sinais de impaciência. Você teme pelo emprego?',
         [('Não penso nisso. Penso no próximo jogo.', 'neutro', 0, 1, 'corporativo'),
          ('Se eu tiver o elenco que pedi, a resposta vem em campo.', 'irritado', 0, -3, 'pressao'),
          ('Assumo o momento. Se não melhorar, a culpa é minha.', 'neutro', 2, 1, 'culpa')]),
    ],
    'lesao': [
        ('A ausência de {jogador} pesou?',
         [('Pesa, mas o elenco tem opções e confio em todos.', 'neutro', 0, 1, 'proteger'),
          ('Pesa muito. Não temos peça de reposição à altura.', 'irritado', -1, -2, 'pressao'),
          ('Não vou usar desfalque como desculpa.', 'neutro', 1, 1, 'humilde')]),
    ],
    'vestiario': [
        ('Fala-se em clima ruim no vestiário. É verdade?',
         [('Mentira. O grupo está fechado comigo.', 'irritado', 0, 0, 'proteger'),
          ('Tem jogador que precisa entender o momento do clube.', 'irritado', -1, -1, 'expor'),
          ('Toda equipe passa por isso. Vamos resolver aqui dentro.', 'neutro', 1, 1, 'corporativo')]),
    ],
}

# como cada jornalista recebe cada estilo de resposta (os outros estilos ele critica)
APROVA = {'duarte': {'culpa', 'humilde'}, 'ferraz': {'culpa', 'humilde', 'proteger'},
          'lacerda': {'proteger', 'corporativo', 'humilde'}, 'pilha': {'provocar', 'empolgar', 'pressao', 'expor'},
          'renata': {'corporativo', 'humilde', 'culpa'}, 'arnaldo': {'culpa', 'proteger', 'provocar'}}
REACAO = {
    'humilde': (['Pés no chão. Gosto de técnico assim.', 'Resposta madura, sem firula.'],
                ['Muito morno. Falta ambição nesse discurso.', 'Humildade demais vira conformismo.']),
    'corporativo': (['Equilíbrio, sem polêmica. Correto.', 'Falou o necessário e protegeu o ambiente.'],
                    ['Não disse nada. Coletiva protocolar.', 'Resposta de manual. Zero conteúdo.']),
    'empolgar': (['Pode sonhar sim! Esse time tem cara de campeão!', 'Isso que a torcida quer ouvir!'],
                 ['Cuidado com a euforia. Futebol cobra caro.', 'Prometeu demais. Vai ter que entregar.']),
    'provocar': (['Isso! Técnico tem que ter sangue no olho!', 'Gostei! Personalidade é tudo.'],
                 ['Provocação gratuita. Se perder o próximo, vira piada.', 'Desnecessário. Deu munição ao adversário.']),
    'culpa': (['Assumir a culpa é coisa de líder.', 'Chamou a responsabilidade. Respeito.'],
              ['Assumir a culpa toda hora não resolve nada.', 'Bonito no microfone. E o que muda em campo?']),
    'expor': (['Cobrança pública às vezes acorda o time.', 'Falou o que todo mundo viu!'],
              ['Expor jogador em público racha qualquer vestiário.', 'Apurei que a fala caiu muito mal no elenco.']),
    'proteger': (['Blindou o grupo. Liderança.', 'Técnico que protege o elenco ganha o vestiário.'],
                 ['Passou pano para quem não jogou nada.', 'Proteger é uma coisa, fingir que está tudo bem é outra.']),
    'arbitragem': (['Ele tem razão, o apito pesou hoje.', 'Precisava falar. A arbitragem foi ruim.'],
                   ['Reclamar da arbitragem é a desculpa mais velha do futebol.', 'Culpar o juiz esconde os próprios erros.']),
    'pressao': (['Ele tem razão: o elenco é curto.', 'Recado dado à diretoria. Corajoso.'],
                ['Jogar a culpa na diretoria em público? Isso tem preço.', 'Pedir reforço pelo microfone é queimar ponte.']),
}


def tipo_partida(p, team_id):
    casa = p['mandante'] == team_id
    gp, gc = (p['gm'], p['gv']) if casa else (p['gv'], p['gm'])
    s = gp - gc
    return 'goleada' if s >= 3 else 'vitoria' if s > 0 else 'empate' if s == 0 else 'vexame' if s <= -3 else 'derrota'


def _reporter(tipo, i, chave):
    from . import imprensa
    k, intro = imprensa.pergunta_coletiva(tipo in ('vitoria', 'goleada'), i, chave)
    j = imprensa.JORNALISTAS[k]
    return {'reporter': k, 'reporter_nome': j['nome'], 'reporter_veiculo': j['programa'], 'intro': intro}


def moral_ajuste(state, nome, delta, data, motivo, dias=10):
    """Guarda um efeito na moral (nome do jogador ou '*' para o elenco todo) que vale por alguns dias."""
    g = state.setdefault('gestao', {})
    aj = g.setdefault('moral_aj', [])
    aj.append({'nome': nome, 'delta': delta, 'data': data, 'dias': dias, 'motivo': motivo})
    g['moral_aj'] = aj[-120:]


def moral_efetiva(state, elenco, hoje):
    """Moral do jogo (Dados do time) mais os efeitos ativos do app (notícias, eventos, resultados)."""
    if not hoje:
        return
    ativos = [a for a in (state.get('gestao') or {}).get('moral_aj', [])
              if s2d(a['data']) <= hoje < s2d(a['data']) + dt.timedelta(days=a['dias'])]
    for j in elenco:
        base = j.get('moral')
        # sem a moral do jogo (Dados do time), só os efeitos individuais aparecem
        meus = [a for a in ativos if a['nome'] == j['nome'] or (a['nome'] == '*' and base is not None)]
        if not meus:
            continue
        grupo = sum(a['delta'] for a in meus if a['nome'] == '*')
        soma = sum(a['delta'] for a in meus if a['nome'] != '*') + max(-1, min(1, grupo))
        j['moral_app'] = int(max(0, min(4, (2 if base is None else base) + soma)))
        j['moral_motivos'] = [f"{'+' if a['delta'] > 0 else ''}{a['delta']} {a['motivo']}" for a in meus][-4:]


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
    def coletiva_nova(self, partida, nomes, rivais=()):
        if any(c['partida'] == partida['chave'] for c in self.g['coletivas']):
            return
        # a coletiva anterior que ficou sem resposta expira
        for c in self.g['coletivas']:
            if c['status'] == 'aberta':
                c['status'] = 'expirada'
        tipo = tipo_partida(partida, self.team_id)
        casa = partida['mandante'] == self.team_id
        adv_id = partida['visitante'] if casa else partida['mandante']
        classico = adv_id in set(rivais or ())
        r = random.Random(_seed('col', partida['chave']))
        pool = PERGUNTAS['classico_' + partida['res'].lower()] if classico else PERGUNTAS[tipo]
        qs = [(q, ans, None) for q, ans in r.sample(pool, min(2, len(pool)))]
        if classico:
            outra = [x for x in PERGUNTAS[tipo] if x[0] not in [q for q, _, _ in qs]]
            if outra:
                qs.append((*r.choice(outra), None))
        # uma pergunta sobre o momento, quando ele pede
        dia = s2d(partida['data'])
        les = next((e for e in reversed(self.g['eventos']) if e.get('tipo') == 'lesao'
                    and s2d(e['data']) <= dia < s2d(e['volta'])), None)
        conf = (self.s.get('mundo') or {}).get('diretoria', 60)
        clima = ((self.g.get('vestiario') or {}).get('clima', 60))
        if conf <= 40 and partida['res'] != 'V':
            qs.append((*PERGUNTAS['pressao'][0], None))
        elif les and r.random() < 0.6:
            q, ans = PERGUNTAS['lesao'][0]
            qs.append((q.format(jogador=les['jogador']), ans, les['jogador']))
        elif clima < 40 and r.random() < 0.6:
            qs.append((*PERGUNTAS['vestiario'][0], None))
        qs = qs[:3]
        adv = nomes(adv_id)
        gp, gc = (partida['gm'], partida['gv']) if casa else (partida['gv'], partida['gm'])
        self.g['coletivas'].append({
            'id': f"col{len(self.g['coletivas']) + 1}", 'partida': partida['chave'], 'data': partida['data'],
            'titulo': f"{self.clube} {gp} x {gc} {adv}", 'tipo': tipo, 'status': 'aberta', 'classico': classico,
            'perguntas': [{'texto': q, 'respostas': [a[0] for a in ans], 'efeitos': [list(a[1:]) for a in ans],
                           'escolha': None, **_reporter(tipo, i, partida['chave'])} for i, (q, ans, _) in enumerate(qs)]})
        self.g['coletivas'] = self.g['coletivas'][-30:]

    def responder(self, cid, q, a, mundo):
        c = next((x for x in self.g['coletivas'] if x['id'] == cid), None)
        if not c or c['status'] != 'aberta':
            raise ValueError('Essa coletiva já terminou.')
        perg = c['perguntas'][q]
        if perg['escolha'] is not None:
            raise ValueError('Pergunta já respondida.')
        perg['escolha'] = a
        ef = perg['efeitos'][a]
        tom, dt_torc, dt_dir = ef[:3]
        estilo = ef[3] if len(ef) > 3 else None
        mundo._torcida(dt_torc)
        mundo.m['diretoria'] = int(max(0, min(100, mundo.m['diretoria'] + dt_dir)))
        if estilo:
            from . import vestiario
            vestiario.coletiva(self.s, estilo, c['data'])
            # o jornalista que perguntou reage na hora; a relação com a imprensa muda
            k = perg.get('reporter') or 'lacerda'
            bom = estilo in APROVA.get(k, set())
            rr = random.Random(_seed('reac', cid, q, a))
            perg['reacao'] = {'texto': rr.choice(REACAO[estilo][0 if bom else 1]), 'bom': bom}
            self.g['imprensa'] = int(max(0, min(100, self.g.get('imprensa', 55) + (3 if bom else -3))))
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
        ('lesao', 'Lesão no treino', 'sentiu uma lesão muscular no treino', 10, 24, -1, 0),
        ('lesao', 'Entorse no treino', 'torceu o tornozelo em um treino', 7, 18, -1, 0),
        ('lesao', 'Lesão no treino', 'teve um estiramento na coxa durante o treino', 14, 30, -1, 0),
        ('lesao', 'Pancada no treino', 'levou uma pancada forte em dividida no treino', 4, 9, 0, 0),
        ('lesao', 'Lesão no joelho', 'machucou o joelho no treino e passa por exames', 21, 45, -2, -1),
        ('lesao', 'Dores nas costas', 'sente dores nas costas e foi vetado pelo departamento médico', 5, 12, 0, 0),
    ]
    # moral (em "pontos" de seta) que cada tipo de evento tira do jogador enquanto dura
    MORAL_EVENTO = {'indisciplina': -1, 'lesao': -1, 'pessoal': 0}

    def semana(self, dia, elenco, mundo):
        """Chamado uma vez por semana da carreira: 6% de chance de um evento com um jogador do elenco."""
        if not elenco:
            return
        ds = d2s(dia)
        for e in self.g['eventos']:      # quem voltou de lesão vira notícia
            if e.get('tipo') == 'lesao' and not e.get('voltou') and s2d(e['volta']) <= dia:
                e['voltou'] = True
                mundo.noticia('retorno', e['volta'], random.Random(_seed('ret', e['id'])), jogador=e['jogador'])
                mundo.m['noticias'][-1]['jogador'] = e['jogador']
        from . import estrutura
        risco = estrutura.risco_treino(self.s)
        r = random.Random(_seed('evt', ds, self.clube))
        if r.random() > 0.08 * (1 + max(0, risco - 1)):
            return
        livres = [j for j in elenco if not self.afastado(j['id'], dia)]
        if not livres:
            return
        j = r.choice(livres)
        tipo, titulo, txt, dmin, dmax, dt_torc, dt_dir = r.choice(self.EVENTOS)
        if tipo == 'lesao' and r.random() > risco:
            return          # CT bom: a lesão no treino não aconteceu
        dias = r.randint(dmin, dmax)
        if tipo == 'lesao':
            dias = max(2, int(round(dias * estrutura.duracao_lesao(self.s))))
        volta = dia + dt.timedelta(days=dias)
        ev = {'id': f"ev{len(self.g['eventos']) + 1}", 'data': ds, 'jogador_id': j['id'], 'jogador': j['nome'],
              'tipo': tipo, 'titulo': titulo, 'texto': f"{j['nome']} {txt}. Volta prevista: {volta.strftime('%d/%m/%Y')}.",
              'volta': d2s(volta)}
        self.g['eventos'].append(ev)
        self.g['eventos'] = self.g['eventos'][-60:]
        privado = tipo == 'indisciplina'      # punição interna: só chega à imprensa se o assessor deixar vazar
        if privado:
            ev['interno'] = True
        else:
            mundo._torcida(dt_torc)
        mundo.m['diretoria'] = int(max(0, min(100, mundo.m['diretoria'] + dt_dir)))
        if tipo == 'lesao':
            ev['texto'] += ' Pelo jogo ele ainda aparece disponível: não escale até a volta.'
            mundo.noticia('lesao', ds, r, destaque=dias >= 20, jogador=j['nome'], n=dias)
            mundo.m['noticias'][-1].update(jogador=j['nome'], volta=ev['volta'])
        elif not privado:
            mundo.m['noticias'].append({'data': ds, 'tipo': 'evento', 'destaque': tipo == 'indisciplina',
                                        'fonte': r.choice(['Lance!', 'Globo Esporte', 'ESPN']),
                                        'jogador': j['nome'], 'titulo': f"{self.clube}: {ev['texto']}"})
        if self.MORAL_EVENTO.get(tipo):
            moral_ajuste(self.s, j['nome'], self.MORAL_EVENTO[tipo], ds, titulo, dias)
        if tipo == 'indisciplina':
            from . import vestiario
            vestiario.mexer(self.s, -4, f'{j["nome"]}: {titulo.lower()}', ds)

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
    # ---------- fim de campeonato: título, acesso, rebaixamento e bônus ----------
    def fim_de_liga(self, engine, mundo, tabela, dia):
        """Quando todos os times da tabela do clube completaram os jogos (turno e returno), registra a
        posição final. 1º lugar = título (paga o bônus dos contratos); 4 primeiros da Série B sobem;
        4 últimos da Série A caem."""
        linhas = (tabela or {}).get('linhas') or []
        n = len(linhas)
        if n < 8 or any(l['j'] < 2 * (n - 1) for l in linhas):
            return
        meu = next((l for l in linhas if l['id'] == self.team_id), None)
        if not meu:
            return
        temps = self.g.setdefault('temporadas', [])
        ano = dia.year if dia.month >= 6 else dia.year - 1
        if any(t['ano'] == ano for t in temps):
            return
        div = 'B' if 'serie_b' in engine.competicoes_do_ano(ano) else 'A'
        t = {'ano': ano, 'pos': meu['pos'], 'n': n, 'divisao': div, 'pts': meu['pts'], 'titulos': []}
        if meu['pos'] == 1:
            t['titulos'].append('brasileirao' if div == 'A' else 'serie_b')
        if div == 'B' and meu['pos'] <= 4:
            t['acesso'] = True
        if div == 'A' and meu['pos'] > n - 4:
            t['rebaixado'] = True
        temps.append(t)
        ds = d2s(dia)
        r = random.Random(_seed('fim', ano, self.clube))
        if t['titulos']:
            comp = COMP_NOMES[t['titulos'][0]]
            mundo.m['noticias'].append({'data': ds, 'tipo': 'lider', 'destaque': True, 'fonte': 'Globo Esporte',
                                        'titulo': f'É CAMPEÃO! {self.clube} conquista o título do {comp} {ano}'})
            mundo._torcida(15)
            mundo.m['diretoria'] = min(100, mundo.m['diretoria'] + 20)
            self.titulo(engine, t['titulos'][0], dia)
        if t.get('acesso'):
            mundo.m['noticias'].append({'data': ds, 'tipo': 'sobe', 'destaque': True, 'fonte': 'Lance!',
                                        'titulo': f'Acesso garantido! {self.clube} volta à Série A'})
            mundo._torcida(10)
        if t.get('rebaixado'):
            mundo.m['noticias'].append({'data': ds, 'tipo': 'cai', 'destaque': True, 'fonte': 'Lance!',
                                        'titulo': f'Rebaixado: {self.clube} vai disputar a Série B em {ano + 1}'})
            mundo._torcida(-20)
            mundo.m['diretoria'] = max(0, mundo.m['diretoria'] - 25)

    def copas(self, engine, mundo, dia):
        """Títulos de copa pelos jogos do save: final da Libertadores (torneio 4 do GOGOSZ, jogo único) vencida,
        ou vitória no último jogo do Intercontinental sem jogo seguinte depois de 20 dias."""
        ps = sorted(self.s.get('partidas', []), key=lambda p: p['data'])
        feitos = {(t['comp'], t['data'][:4]) for t in self.g.get('titulos', [])}
        for i, p in enumerate(ps):
            base = int(p.get('torneio', 0)) & 1023
            comp = None
            if base == 4 and p['res'] == 'V':
                comp = 'libertadores'
            elif base == 1 and p['res'] == 'V':
                depois = [q for q in ps[i + 1:] if (int(q.get('torneio', 0)) & 1023) == 1]
                if not depois and (dia - s2d(p['data'])).days >= 20:
                    comp = 'interclubes'
            if comp and (comp, p['data'][:4]) not in feitos:
                feitos.add((comp, p['data'][:4]))
                mundo.m['noticias'].append({'data': p['data'], 'tipo': 'lider', 'destaque': True, 'fonte': 'Globo Esporte',
                                            'titulo': f"É CAMPEÃO! {self.clube} conquista a {COMP_NOMES[comp]}!"})
                mundo._torcida(15)
                mundo.m['diretoria'] = min(100, mundo.m['diretoria'] + 20)
                self.titulo(engine, comp, s2d(p['data']))

    def titulo(self, engine, comp, dia):
        """Título conquistado: cada contrato com cláusula de bônus para essa competição paga
        cota anual x bônus% x peso do título (Copa do Brasil 1x, Brasileirão 2x, Libertadores 4x,
        Interclubes 6x, Super Mundial 10x)."""
        ds = d2s(dia)
        linhas = []
        for c in engine.s['contratos']:
            cl = c.get('clausulas') or {}
            if c['status'] != 'ativo' or not cl.get('bonus_pct') or comp not in (cl.get('competicoes') or []):
                continue
            if any(pg.get('tipo') == 'bonus' and pg.get('comp') == comp and pg['data'][:4] == ds[:4]
                   for pg in c['pagamentos']):
                continue
            v = int(round(c['valor'] * cl['bonus_pct'] / 100 * TITULO_PESO.get(comp, 1) / 50_000) * 50_000)
            c['pagamentos'].append({'data': ds, 'valor': v, 'status': 'pendente', 'tipo': 'bonus', 'comp': comp})
            linhas.append(f"• {c['empresa']}: {fmt_eur(v)} ({cl['bonus_pct']}% x {TITULO_PESO.get(comp, 1)})")
        self.g.setdefault('titulos', []).append({'comp': comp, 'data': ds})
        if linhas:
            engine.s['mensagens'].append({
                'id': engine._id(), 'data': ds, 'empresa': '__diretoria__', 'de': 'Departamento de marketing',
                'assunto': f'Bônus pelo título do {COMP_NOMES.get(comp, comp)}', 'tipo': 'diretoria',
                'oferta_id': None, 'lida': False,
                'texto': 'O título acionou as cláusulas de bônus dos patrocinadores. O dinheiro entra no '
                         'orçamento de transferências:\n' + '\n'.join(linhas)})

    def revisao_anual(self, engine, mundo, dia):
        ano = dia.year
        if dia.month != 1 or any(r['ano'] == ano for r in self.g['revisoes']):
            return
        ap = mundo.aproveitamento()
        if ap is None:
            self.g['revisoes'].append({'ano': ano, 'aproveitamento': None, 'mudancas': []})
            return
        fator = 1.15 if ap >= 70 else 1.08 if ap >= 60 else 0.85 if ap < 35 else 0.93 if ap < 45 else 1.0
        t = next((x for x in self.g.get('temporadas', []) if x['ano'] == ano - 1), {})
        tits = [x for x in self.g.get('titulos', []) if x['data'][:4] == str(ano - 1)]
        motivo = []
        if t.get('acesso'):
            fator = max(fator, 1.0) + 0.20; motivo.append('o acesso à Série A')
        if tits:
            fator = max(fator, 1.0) + 0.10 * len(tits); motivo.append('os títulos da temporada')
        rescindidos = []
        if t.get('rebaixado'):
            fator = min(fator, 1.0) - 0.25; motivo.append('o rebaixamento')
            # quem tem cláusula de desempenho sai sem multa
            for c in engine.s['contratos']:
                if c['status'] == 'ativo' and (c.get('clausulas') or {}).get('desempenho'):
                    engine._encerrar(c, d2s(dia), 'empresa (rebaixamento, cláusula de desempenho)')
                    rescindidos.append(c['empresa'])
        fator = round(fator, 2)
        mud = []
        for c in engine.s['contratos']:
            if c['status'] != 'ativo' or fator == 1.0:
                continue
            if c.get('anos', 1) < 2 and not (t.get('acesso') or t.get('rebaixado') or tits):
                continue      # contrato curto só muda em caso de acesso, rebaixamento ou título
            futuros = [pg for pg in c['pagamentos'] if pg['status'] == 'agendado' and pg.get('tipo') != 'multa']
            if not futuros:
                continue
            novo = int(round(c['valor'] * fator / 50_000) * 50_000)
            for pg in futuros:
                pg['valor'] = novo
            mud.append({'empresa': c['empresa'], 'antes': c['valor'], 'depois': novo})
            c['valor'] = novo
        self.g['revisoes'].append({'ano': ano, 'aproveitamento': ap, 'fator': fator, 'mudancas': mud,
                                   'rescindidos': rescindidos, 'motivo': motivo})
        if rescindidos:
            engine.s['mensagens'].append({
                'id': engine._id(), 'data': d2s(dia), 'empresa': '__diretoria__', 'de': 'Departamento de marketing',
                'assunto': 'Patrocinadores saíram após o rebaixamento', 'tipo': 'diretoria', 'oferta_id': None,
                'lida': False, 'texto': 'Com o rebaixamento, estes patrocinadores usaram a cláusula de desempenho e '
                                        'encerraram o contrato sem multa: ' + ', '.join(rescindidos) + '.'})
        if mud:
            subiu = fator > 1
            linhas = '\n'.join(f"• {m['empresa']}: {fmt_eur(m['antes'])} → {fmt_eur(m['depois'])}" for m in mud)
            engine.s['mensagens'].append({
                'id': engine._id(), 'data': d2s(dia), 'empresa': '__diretoria__', 'de': 'Departamento de marketing',
                'assunto': 'Revisão anual dos patrocínios', 'tipo': 'diretoria', 'oferta_id': None, 'lida': False,
                'texto': (f"Fechamos a revisão anual dos contratos com base no aproveitamento de {ap}% na temporada"
                          + (', considerando ' + ' e '.join(motivo) if motivo else '') + '. '
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
