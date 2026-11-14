"""Gestão do clube além dos patrocínios: coletivas de imprensa, eventos do vestiário, movimentação do
elenco (chegadas e saídas), revisão anual dos contratos e prancheta. Tudo roda só no app (não mexe no save)."""
import random, datetime as dt
from .sim import d2s, s2d, fmt_eur, _seed, TITULO_PESO, COMP_NOMES, comp_de

# ---------------- coletivas de imprensa ----------------
# cada resposta: texto, tom (rosto do técnico), efeito na torcida, efeito na diretoria e o estilo da resposta.
# O estilo mexe no vestiário (vestiario.coletiva) e na relação com a imprensa (REACAO abaixo).
from .coletiva_perguntas import PERGUNTAS   # banco de perguntas (só texto)

# como cada jornalista recebe cada estilo de resposta (os outros estilos ele critica)
APROVA = {'duarte': {'culpa', 'humilde'}, 'ferraz': {'culpa', 'humilde', 'proteger'},
          'lacerda': {'proteger', 'corporativo', 'humilde'}, 'pilha': {'provocar', 'empolgar', 'pressao', 'expor'},
          'renata': {'corporativo', 'humilde', 'culpa'}, 'arnaldo': {'culpa', 'proteger', 'provocar'}}
REACAO = {
    'humilde': (['Pés no chão. Gosto de técnico assim.', 'Resposta madura, sem firula.', 'Discurso de quem sabe onde está pisando.', 'Sem salto alto. O vestiário agradece.'],
                ['Muito morno. Falta ambição nesse discurso.', 'Humildade demais vira conformismo.', 'Pés no chão demais: parece que já aceitou o meio da tabela.', 'Faltou ambição. Torcedor quer ouvir mais que isso.']),
    'corporativo': (['Equilíbrio, sem polêmica. Correto.', 'Falou o necessário e protegeu o ambiente.', 'Resposta segura. Não deu manchete para ninguém.', 'Equilibrado, como um técnico de clube grande deve ser.'],
                    ['Não disse nada. Coletiva protocolar.', 'Resposta de manual. Zero conteúdo.', 'Falou, falou e não respondeu.', 'Coletiva em piloto automático.']),
    'empolgar': (['Pode sonhar sim! Esse time tem cara de campeão!', 'Isso que a torcida quer ouvir!', 'A torcida vai à loucura com essa resposta!', 'Técnico que acredita contagia o grupo.'],
                 ['Cuidado com a euforia. Futebol cobra caro.', 'Prometeu demais. Vai ter que entregar.', 'Discurso de euforia costuma virar arquivo contra ele.', 'Prometeu a lua. Agora vai ter que buscar.']),
    'provocar': (['Isso! Técnico tem que ter sangue no olho!', 'Gostei! Personalidade é tudo.', 'Personalidade! O rival vai sentir.', 'Gostei do recado. Tem que ter casca.'],
                 ['Provocação gratuita. Se perder o próximo, vira piada.', 'Desnecessário. Deu munição ao adversário.', 'Arrumou uma briga que não precisava.', 'Fala de arquibancada, não de treinador.']),
    'culpa': (['Assumir a culpa é coisa de líder.', 'Chamou a responsabilidade. Respeito.', 'Tirou o peso do grupo. Atitude de líder.', 'Honestidade rara num microfone.'],
              ['Assumir a culpa toda hora não resolve nada.', 'Bonito no microfone. E o que muda em campo?', 'De tanto assumir culpa, uma hora a diretoria acredita.', 'Culpa assumida não marca gol.']),
    'expor': (['Cobrança pública às vezes acorda o time.', 'Falou o que todo mundo viu!', 'Disse o que precisava ser dito.', 'Recado direto: agora todo mundo sabe o que ele pensa.'],
              ['Expor jogador em público racha qualquer vestiário.', 'Apurei que a fala caiu muito mal no elenco.', 'Fala pública assim racha o vestiário em uma semana.', 'Quem expõe jogador perde o grupo.']),
    'proteger': (['Blindou o grupo. Liderança.', 'Técnico que protege o elenco ganha o vestiário.', 'Fechou com o elenco. O grupo vai correr por ele.', 'Blindagem total. Os jogadores vão gostar.'],
                 ['Passou pano para quem não jogou nada.', 'Proteger é uma coisa, fingir que está tudo bem é outra.', 'Proteção cega: ninguém foi cobrado.', 'Defendeu o indefensável.']),
    'arbitragem': (['Ele tem razão, o apito pesou hoje.', 'Precisava falar. A arbitragem foi ruim.', 'Reclamou com razão. Tinha lance para discutir.', 'Defendeu o clube. Alguém tinha que falar.'],
                   ['Reclamar da arbitragem é a desculpa mais velha do futebol.', 'Culpar o juiz esconde os próprios erros.', 'A arbitragem não perdeu o jogo sozinha.', 'Desculpa pronta de novo.']),
    'pressao': (['Ele tem razão: o elenco é curto.', 'Recado dado à diretoria. Corajoso.', 'Cobrou a diretoria com coragem.', 'Disse em público o que todo mundo fala em off.'],
                ['Jogar a culpa na diretoria em público? Isso tem preço.', 'Pedir reforço pelo microfone é queimar ponte.', 'Recado público à diretoria raramente termina bem.', 'Queimou a ponte com o presidente ao vivo.']),
}


def _preencher(t, v):
    try:
        return t.format(**v)
    except (KeyError, IndexError, ValueError):
        return t


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
        adv = nomes(adv_id)
        gp, gc = (partida['gm'], partida['gv']) if casa else (partida['gv'], partida['gm'])
        cod = int(partida.get('torneio') or 0) & 1023
        from .campeonatos import NOMES as NOMES_COMP
        v = {'adv': adv, 'placar': f'{gp} x {gc}', 'comp': NOMES_COMP.get(cod, 'copa').split(' · ')[0],
             'jogador': '', 'pos': '', 'seq': ''}
        # 1) duas perguntas sobre o resultado (variações de casa/fora e 0 x 0 entram no sorteio)
        if classico:
            pool = list(PERGUNTAS['classico_' + partida['res'].lower()])
            extra = list(PERGUNTAS[tipo])
        else:
            pool = list(PERGUNTAS[tipo])
            if tipo == 'vitoria' and not casa:
                pool += PERGUNTAS['vitoria_fora']
            if tipo in ('derrota', 'vexame') and casa:
                pool += PERGUNTAS['derrota_casa']
            if tipo == 'empate' and gp == 0:
                pool = PERGUNTAS['empate_0'] + pool[:3]
            extra = []
        qs = [(q, ans, None) for q, ans in r.sample(pool, min(2, len(pool)))]
        if extra:
            qs.append((*r.choice(extra), None))
        # 2) perguntas sobre o momento: sequência, tabela, copa, torcida, diretoria, lesão, vestiário, mercado
        dia = s2d(partida['data'])
        sit = self._situacoes(partida, dia, cod, v)
        r.shuffle(sit)
        sit.sort(key=lambda x: -x[0])         # as mais urgentes primeiro
        usados = {q for q, _, _ in qs}
        for _, chave, jog in sit:
            if len(qs) >= 4:
                break
            op = [x for x in PERGUNTAS[chave] if x[0] not in usados]
            if op:
                q, ans = r.choice(op)
                usados.add(q)
                qs.append((q, ans, jog))
        if len(qs) < 4 and r.random() < 0.5:
            q, ans = r.choice(PERGUNTAS['geral'])
            qs.append((q, ans, None))
        qs = [(_preencher(q, v), [(_preencher(a[0], v), *a[1:]) for a in ans], j) for q, ans, j in qs[:4]]
        self.g['coletivas'].append({
            'id': f"col{len(self.g['coletivas']) + 1}", 'partida': partida['chave'], 'data': partida['data'],
            'titulo': f"{self.clube} {gp} x {gc} {adv}", 'tipo': tipo, 'status': 'aberta', 'classico': classico,
            'perguntas': [{'texto': q, 'respostas': [a[0] for a in ans], 'efeitos': [list(a[1:]) for a in ans],
                           'escolha': None, **_reporter(tipo, i, partida['chave'])} for i, (q, ans, _) in enumerate(qs)]})
        self.g['coletivas'] = self.g['coletivas'][-30:]

    def _situacoes(self, partida, dia, cod, v):
        """[(urgência, chave do banco, jogador)] do momento do clube."""
        out = []
        ps = [p for p in self.s.get('partidas', []) if p.get('data', '') <= partida['data']][-12:]
        res = [p['res'] for p in ps]
        def seq(cond):
            n = 0
            for x in reversed(res):
                if not cond(x):
                    break
                n += 1
            return n
        sv, sd, sem_v, invic = seq(lambda x: x == 'V'), seq(lambda x: x == 'D'), seq(lambda x: x != 'V'), seq(lambda x: x != 'D')
        if sv >= 3:
            v['seq'] = sv; out.append((3, 'seq_vitorias', None))
        elif sd >= 2:
            v['seq'] = sd; out.append((4, 'seq_derrotas', None))
        elif sem_v >= 4:
            v['seq'] = sem_v; out.append((3, 'jejum', None))
        elif invic >= 6:
            v['seq'] = invic; out.append((2, 'invicto', None))
        tab = self.s.get('tabela') or []
        tab = tab.get('linhas') or [] if isinstance(tab, dict) else tab
        pos = next((i + 1 for i, l in enumerate(tab) if l.get('id') == self.team_id), None)
        if pos and len(tab) >= 10 and max(l.get('j', 0) for l in tab) >= 4:
            v['pos'] = pos
            if pos == 1:
                out.append((2, 'lider', None))
            elif pos <= 4:
                out.append((1, 'g4', None))
            elif pos > len(tab) - 4:
                out.append((4, 'z4', None))
        if cod not in (17, 79, 81, 80):
            out.append((2, 'copa', None))
        m = self.s.get('mundo') or {}
        torc, conf = m.get('torcida', 60), m.get('diretoria', 60)
        if conf <= 40 and partida['res'] != 'V':
            out.append((5, 'pressao', None))
        if torc < 35:
            out.append((3, 'torcida_protesto', None))
        elif torc >= 80 and partida['res'] == 'V':
            out.append((1, 'torcida_festa', None))
        les = next((e for e in reversed(self.g['eventos']) if e.get('tipo') == 'lesao'
                    and s2d(e['data']) <= dia < s2d(e['volta'])), None)
        if les:
            v['jogador'] = les['jogador']; out.append((2, 'lesao', les['jogador']))
        if (self.g.get('vestiario') or {}).get('clima', 60) < 40:
            out.append((3, 'vestiario', None))
        if self.g.get('imprensa', 55) < 35:
            out.append((2, 'imprensa_tensa', None))
        if dia.month in (1, 2, 7, 8):
            out.append((1, 'mercado', None))
        return out

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
