"""Assessor de imprensa do clube: cuida das redes sociais sozinho.

Ele publica (pós-jogo, semana, patrocínio, expulsões), responde a torcida no tom do momento e sabe dos
bastidores: finanças, punições internas, lesões e a situação do técnico. Conforme a personalidade dele e o
momento do técnico no clube, parte disso vaza para a imprensa como "fonte ligada ao clube".
O técnico não posta mais: fica só com a coletiva.
"""
import random
import hashlib
import datetime as dt

PERSONAS = [
    {'id': 'rafael', 'nome': 'Rafael Monteiro', 'estilo': 'sobrio', 'vaza': 0.10, 'lealdade': 0.85,
     'perfil': 'Ex-repórter de TV, diplomático e frio. Fala pouco, mede cada palavra e nunca bate de frente com a torcida.'},
    {'id': 'bia', 'nome': 'Bianca “Bia” Castanho', 'estilo': 'marketeira', 'vaza': 0.22, 'lealdade': 0.6,
     'perfil': 'Marketeira, vive de engajamento: emoji, meme e provocação leve. Adora um bastidor que rende clique.'},
    {'id': 'jorge', 'nome': 'Jorge Sales', 'estilo': 'veterano', 'vaza': 0.32, 'lealdade': 0.45,
     'perfil': 'Veterano de redação, 25 anos de futebol e amigo de todos os setoristas. Protege quem o protege; '
               'quando o barco balança, a informação escapa.'},
]

ESTILO_NOME = {'sobrio': 'Diplomático', 'marketeira': 'Marketeira', 'veterano': 'Veterano'}


def _seed(*p):
    return int(hashlib.md5('|'.join(map(str, p)).encode()).hexdigest()[:8], 16)


def _s2d(s):
    return dt.date.fromisoformat(str(s)[:10])


def _mi(v):
    from .mundo import eur_mi
    return eur_mi(v)


# ---------------- textos ----------------
POS_JOGO = {
    'sobrio': {
        'V': ['FIM DE JOGO | {clube} {gp} x {gc} {adv}.{gols} Três pontos importantes. Foco no próximo compromisso.',
              'Vitória do {clube}: {gp} x {gc} sobre o {adv}.{gols} Seguimos trabalhando.'],
        'E': ['FIM DE JOGO | {clube} {gp} x {gc} {adv}.{gols} Um ponto conquistado. Já estamos pensando no próximo jogo.'],
        'D': ['FIM DE JOGO | {clube} {gp} x {gc} {adv}.{gols} Resultado abaixo do esperado. Elenco e comissão já trabalham para a resposta.',
              'Derrota para o {adv}, {gp} x {gc}.{gols} O grupo sabe da responsabilidade e vai reagir.'],
    },
    'marketeira': {
        'V': ['APITO FINAL!!! 🔥🔥 {clube} {gp}x{gc} {adv}!{gols} Que noite, Nação! 💪',
              'É DO {CLUBE}! 😎 {gp}x{gc} no {adv}!{gols} Pode comemorar que hoje é nosso! 🎉'],
        'E': ['Fim de papo: {gp}x{gc} contra o {adv}.{gols} Pontinho na conta, mas a gente quer mais! 💪'],
        'D': ['Não foi o resultado que a gente queria. 💔 {gp}x{gc} para o {adv}.{gols} Cabeça erguida, tem jogo já já!',
              'Dói, Nação. {gp}x{gc}.{gols} Mas time grande se levanta. Bora! 🔁'],
    },
    'veterano': {
        'V': ['Encerrado: {clube} {gp} x {gc} {adv}.{gols} Jogo sério, vitória construída. Assim que se faz.',
              'Tá liquidado: {gp} x {gc} no {adv}.{gols} Time competitivo, do jeito que a casa gosta.'],
        'E': ['Encerrado: {clube} {gp} x {gc} {adv}.{gols} Faltou o detalhe. A semana é de ajuste.'],
        'D': ['Encerrado: {clube} {gp} x {gc} {adv}.{gols} Não tem o que esconder: dia ruim. Ninguém aqui está satisfeito.',
              'Derrota para o {adv}, {gp} x {gc}.{gols} O vestiário sabe o que precisa melhorar.'],
    },
}

EXPULSAO = {
    'sobrio': '{nome} foi expulso e desfalca a equipe no próximo jogo.',
    'marketeira': '🟥 {nome} expulso e fora do próximo jogo. Bora segurar sem ele!',
    'veterano': 'Expulsão de {nome} pesa: ele cumpre suspensão na próxima rodada.',
}

# respostas da conta oficial aos posts da torcida, por estilo e humor do post
RESP = {
    'sobrio': {
        'euforia': ['Obrigado pelo apoio! Seguimos juntos. 💚', 'A força da arquibancada faz diferença.'],
        'feliz': ['Obrigado! O trabalho continua.', 'Juntos somos mais fortes.'],
        'neutro': ['Agradecemos o carinho. Seguimos trabalhando.', 'Estamos atentos. O foco é a próxima partida.'],
        'chateado': ['Entendemos a frustração. O grupo também está incomodado e vai responder em campo.',
                     'Cobrança faz parte. O compromisso de todos aqui é com o clube.'],
        'revolta': ['Respeitamos a cobrança da torcida. O momento pede união e trabalho.',
                    'Ninguém está satisfeito. O elenco e a comissão trabalham para mudar esse cenário.'],
        'semana': ['Obrigado por acompanhar o dia a dia do clube.', 'Semana de trabalho intenso no CT.'],
        'patro': ['Parceria importante para o clube. Obrigado!'],
        'classico': ['Clássico é diferente. Obrigado pelo apoio.'],
    },
    'marketeira': {
        'euforia': ['ISSO AQUI É {CLUBE}!!! 🔥🔥', 'Vocês são demais, Nação! 💪😎', 'Tá chegando a hora... 👀🔥'],
        'feliz': ['É nóis! 😎', 'Bora que tem mais! 💪', 'Esse é o espírito! 🙌'],
        'neutro': ['Tamo junto, Nação! 💪', 'Segue o baile! 🔁'],
        'chateado': ['A gente sente junto, Nação. 💔 Próximo jogo é resposta!', 'Respira que ainda tem muita bola. 🙏'],
        'revolta': ['A gente ouviu, Nação. Ninguém aqui tá feliz. 💔', 'Momento difícil, mas é junto que a gente sai. 🙏'],
        'semana': ['Spoiler: tem novidade chegando 👀', 'Bastidores no nosso canal! 🎥'],
        'patro': ['Parceria de peso! 🤝🔥'],
        'classico': ['Clássico é clássico! 😎🔥', 'Já tá doendo aí do outro lado? 😂'],
    },
    'veterano': {
        'euforia': ['Torcida empurrou hoje. Obrigado, gente.', 'É isso: time e arquibancada na mesma batida.'],
        'feliz': ['Vamos com calma, mas vamos.', 'Trabalho sério dá nisso.'],
        'neutro': ['Semana de ajustes. Paciência.', 'Ninguém ganha campeonato em uma rodada.'],
        'chateado': ['Tem razão em cobrar. Quem joga sabe que deve mais.', 'A cobrança é justa. O vestiário ouviu.'],
        'revolta': ['Ninguém aqui vai fingir que está tudo bem.', 'Ouvimos. A resposta precisa vir em campo, e rápido.'],
        'semana': ['CT a todo vapor.', 'Semana cheia por aqui.'],
        'patro': ['Parceiro que acredita no projeto.'],
        'classico': ['Clássico a gente respeita e joga para ganhar.'],
    },
}

# defesa (ou não) do técnico quando a torcida pede a cabeça dele
DEFESA = {
    True: ['O trabalho do professor {tecnico} tem o respaldo de todos aqui.', 'Confiamos no trabalho do {tecnico} e da comissão.'],
    False: ['As avaliações são feitas internamente.', 'Cada decisão será tomada no momento certo.'],
}

SEMANA = {
    'sobrio': ['Semana de trabalho no CT. Elenco se prepara para a sequência da temporada.',
               'Treino de hoje concluído. O grupo segue focado.'],
    'marketeira': ['Bastidores do treino de hoje 🎥👀 Quem tá voando? Comenta aí! ⬇️',
                   'Semana de CT com sol e muito trabalho ☀️💪 #VamosJuntos'],
    'veterano': ['Semana cheia no CT. Treino forte, sem firula.',
                 'Grupo fechado, trabalho em dia. É o que dá para dizer.'],
}

PATRO = {
    'sobrio': 'O {clube} agradece à {empresa} pela parceria.',
    'marketeira': 'Parceria que veste a camisa! 🤝 Valeu, {empresa}! 🔥',
    'veterano': '{empresa} segue com a gente. Parceiro de verdade.',
}

# vazamentos: (chave, condição avaliada fora, manchete, efeito torcida, efeito diretoria)
VAZ_MANCHETE = {
    'lesao': ['Lesão de {jogador} é mais séria do que o {clube} admite; volta só em {volta}, diz fonte',
              'Bastidores: {jogador} preocupa e pode desfalcar o {clube} até {volta}'],
    'indisciplina': ['Fonte revela: {jogador} foi punido internamente no {clube} por {motivo}',
                     'Clima pesado: {jogador} levou punição interna no {clube}, conta pessoa próxima ao elenco'],
    'financas': ['Caixa apertado: {clube} tem só {valor} para contratações, segundo fonte do clube',
                 'Bastidores: diretoria do {clube} segura reforços; orçamento é de {valor}'],
    'cargo': ['Fonte: diretoria do {clube} já sonda nomes para o lugar de {tecnico}',
              'Situação de {tecnico} no {clube} é delicada, admitem pessoas do clube'],
    'expulsao': ['Bastidores: {tecnico} cobrou {jogador} no vestiário pela expulsão, diz fonte',
                 'Expulsão de {jogador} irritou a comissão do {clube}, revela fonte'],
    'positivo': ['Fonte: diretoria do {clube} quer renovar com {tecnico} e vê projeto de longo prazo',
                 'Bastidores: ambiente no {clube} é de confiança total em {tecnico}'],
    'patrocinio': ['Fonte: {empresa} está satisfeita e já fala em ampliar a parceria com o {clube}'],
}
VAZ_EFEITO = {'lesao': (-1, 0), 'indisciplina': (-1, -1), 'financas': (-2, -2), 'cargo': (-2, -3),
              'expulsao': (-1, 0), 'positivo': (2, 1), 'patrocinio': (1, 1)}

AVISO_VAZOU = {
    'leal': ['Professor, saiu na imprensa a informação sobre {assunto}. Não partiu de mim; estou apurando quem falou.',
             'Professor, vazou {assunto}. Já liguei para o setorista e pedi para segurar os próximos passos.'],
    'mentira': ['Professor, apareceu na imprensa {assunto}. Não sei de onde veio, mas é bom tomar cuidado com o que se fala no vestiário.'],
    'confessa': ['Professor, fui eu que soltei {assunto}. Era melhor sair por nós do que de outro jeito. Vai ajudar a imagem do clube.'],
}


# ---------------- núcleo ----------------
class Assessor:
    def __init__(self, state, clube, team_id, tecnico='Técnico'):
        self.s = state
        self.clube = clube
        self.tid = team_id
        self.tecnico = tecnico
        self.m = state.setdefault('mundo', {})
        self.m.setdefault('posts', [])
        self.m.setdefault('noticias', [])
        a = state.setdefault('assessor', {})
        if 'persona' not in a:
            r = random.Random(_seed('assessor', state.get('carreira_id') or clube, clube))
            a['persona'] = r.choice(PERSONAS)['id']
        a.setdefault('relacao', 60)
        a.setdefault('vistos_partidas', None)
        a.setdefault('respondidos', [])
        a.setdefault('vazados', [])
        a.setdefault('ult_semana', None)
        a.setdefault('ult_vazamento', None)
        a.setdefault('log', [])
        a.setdefault('seguidores', None)
        self.a = a
        self.p = next(p for p in PERSONAS if p['id'] == a['persona'])

    # ----- identidade -----
    def arroba(self):
        from .mundo import arrobas
        slug = arrobas(self.clube)[0].split('_')[0].lstrip('@') if arrobas(self.clube) else 'clube'
        if 'PALMEIRAS' in self.clube.upper():
            slug = 'palmeiras'
        return f'@{slug}oficial'

    # ----- momento do técnico -----
    def momento(self):
        dire = self.m.get('diretoria', 60)
        torc = self.m.get('torcida', 50)
        ult = [p['res'] for p in (self.s.get('partidas') or [])[-5:]]
        forma = sum({'V': 10, 'E': 0, 'D': -10}[x] for x in ult)
        v = round(0.5 * dire + 0.3 * torc + 0.2 * (50 + forma))
        if v >= 65:
            nivel, txt = 'alta', 'em alta'
        elif v >= 45:
            nivel, txt = 'estavel', 'estável'
        elif v >= 30:
            nivel, txt = 'pressao', 'sob pressão'
        else:
            nivel, txt = 'crise', 'em crise'
        return {'valor': max(0, min(100, v)), 'nivel': nivel, 'texto': txt}

    def _leal(self):
        """Lealdade efetiva: personalidade + relação com o técnico."""
        return 0.5 * self.p['lealdade'] + 0.5 * self.a['relacao'] / 100

    def _registrar(self, data, texto):
        self.a['log'].append({'data': data, 'texto': texto})
        self.a['log'] = self.a['log'][-30:]

    def _post(self, data, texto, humor, r, extra=None, n_resp=None):
        from .mundo import Mundo
        mu = Mundo(self.s, self.clube, self.tid)
        cur = int(r.randint(800, 6000) * (0.5 + self.m.get('torcida', 50) / 100) * (1.3 if self.p['estilo'] == 'marketeira' else 1))
        v = mu._vars({}, r)
        self.m['posts'].append({'data': data, 'autor': self.arroba(), 'assessor': True, 'texto': texto,
                                'humor': humor, 'curtidas': cur, 'reposts': int(cur * r.uniform(0.08, 0.25)),
                                'respostas': mu._respostas(humor if humor in ('euforia', 'feliz', 'neutro', 'chateado', 'revolta') else 'neutro',
                                                           r, self.arroba(), v, n=r.randint(1, 3) if n_resp is None else n_resp),
                                **(extra or {})})
        self.m['posts'] = self.m['posts'][-300:]
        seg = self.a.get('seguidores') or 0
        self.a['seguidores'] = int(seg + cur * r.uniform(0.02, 0.06))

    def _msg(self, engine, data, assunto, texto):
        if engine is None:
            return
        engine.s['mensagens'].append({'id': engine._id(), 'data': data, 'empresa': '__diretoria__',
                                      'de': f"{self.p['nome']} · Assessoria de imprensa", 'assunto': assunto,
                                      'texto': texto, 'tipo': 'assessor', 'oferta_id': None, 'lida': False})

    # ----- processamento a cada leitura do save -----
    def processar(self, engine, novas, sumulas_jogos, nomes_time, hoje):
        if not hoje:
            return
        ds = hoje if isinstance(hoje, str) else hoje.isoformat()
        partidas = self.s.get('partidas') or []
        if self.a.get('seguidores') is None:
            atr = self.s.get('atr_base', 55)
            self.a['seguidores'] = int(40_000 * (1 + atr / 25) ** 2)
        if self.a['vistos_partidas'] is None:
            # primeira vez: não comenta jogos e posts antigos
            self.a['vistos_partidas'] = [p['chave'] for p in partidas]
            self.a['respondidos'] = [self._chave_post(p) for p in self.m['posts']]
            self.a['ult_semana'] = ds
            self._registrar(ds, f"{self.p['nome']} assumiu a assessoria de imprensa do {self.clube}.")
            self._msg(engine, ds, 'Apresentação da assessoria',
                      f"Professor, sou {self.p['nome']}, da assessoria de imprensa. A partir de agora as redes do clube ficam comigo: "
                      f"publico, respondo a torcida e cuido da relação com os setoristas. A coletiva é sua. "
                      f"Qualquer assunto sensível, me avise antes.")
            return
        self._relacao()
        for p in partidas:
            if p['chave'] in self.a['vistos_partidas']:
                continue
            self.a['vistos_partidas'].append(p['chave'])
            self._pos_jogo(p, sumulas_jogos, nomes_time, engine)
        self.a['vistos_partidas'] = self.a['vistos_partidas'][-200:]
        self._responder(ds)
        self._semana(ds, engine)

    def _chave_post(self, p):
        return f"{p.get('data')}|{p.get('autor')}|{str(p.get('texto'))[:40]}"

    def _relacao(self):
        """A relação com o técnico acompanha (devagar) o momento dele no clube."""
        alvo = 35 + self.momento()['valor'] * 0.55
        r = self.a['relacao']
        self.a['relacao'] = int(round(r + max(-4, min(4, alvo - r))))

    def _pos_jogo(self, p, sumulas_jogos, nomes_time, engine):
        casa = p['mandante'] == self.tid
        gp, gc = (p['gm'], p['gv']) if casa else (p['gv'], p['gm'])
        adv = nomes_time(p['visitante'] if casa else p['mandante'])
        r = random.Random(_seed('ass_jogo', p['chave'], self.p['id']))
        sm = next((x for x in sumulas_jogos if x.get('mandante') == p['mandante'] and x.get('visitante') == p['visitante']
                   and str(x.get('data'))[:10] <= str(p['data'])[:10]), None)
        gols, expulsos = '', []
        if sm:
            g = [f"{j['nome']}{' (' + str(j['gols']) + ')' if j['gols'] > 1 else ''}" for j in sm.get('jogadores', []) if j.get('gols')]
            if g:
                gols = (' ⚽ ' if self.p['estilo'] == 'marketeira' else ' Gols: ') + ', '.join(g) + '.'
            expulsos = [j['nome'] for j in sm.get('jogadores', []) if j.get('vermelho')]
        txt = r.choice(POS_JOGO[self.p['estilo']][p['res']]).format(
            clube=self.clube, CLUBE=self.clube.upper(), gp=gp, gc=gc, adv=adv, gols=gols)
        for nome in expulsos:
            txt += ' ' + EXPULSAO[self.p['estilo']].format(nome=nome)
        humor = {'V': 'feliz' if gp - gc < 3 else 'euforia', 'E': 'neutro', 'D': 'chateado' if gc - gp < 3 else 'revolta'}[p['res']]
        self._post(p['data'], txt, humor, r)
        self._registrar(p['data'], f"Publicou o pós-jogo contra o {adv} ({gp} x {gc}).")
        # expulsão vira assunto de bastidor (pode vazar depois)
        for nome in expulsos:
            self.a.setdefault('segredos', []).append({'tipo': 'expulsao', 'jogador': nome, 'data': p['data']})
        # briefing para a coletiva
        tema, dica = self._briefing(p, gp, gc, adv, expulsos)
        self._msg(engine, p['data'], f'Briefing pós-jogo: {adv}',
                  f"Clima nas redes: {self._clima()}. Na coletiva, devem perguntar sobre {tema}. {dica}")

    def _clima(self):
        t = self.m.get('torcida', 50)
        return ('euforia total' if t >= 85 else 'torcida animada' if t >= 65 else 'torcida dividida' if t >= 45
                else 'torcida impaciente' if t >= 25 else 'revolta da torcida')

    def _briefing(self, p, gp, gc, adv, expulsos):
        mom = self.momento()['nivel']
        seq = [x['res'] for x in (self.s.get('partidas') or [])[-3:]]
        if expulsos:
            return (f"a expulsão de {expulsos[0]}",
                    'Sugiro não expor o jogador em público; diga que o assunto será tratado internamente.')
        if seq.count('D') >= 2 or mom in ('pressao', 'crise'):
            return ('o seu cargo e a sequência ruim', 'Mostre serenidade e assuma a responsabilidade; '
                    'atacar a imprensa agora só piora.')
        if p['res'] == 'V' and gp - gc >= 3:
            return ('a goleada e as metas do time', 'Bom momento para valorizar o grupo sem prometer título.')
        if p['res'] == 'V':
            return ('a sequência e quem vem pela frente', 'Mantenha o pé no chão; elogie o coletivo.')
        if p['res'] == 'E':
            return ('o que faltou para vencer', 'Reconheça o que não funcionou, mas destaque o ponto somado.')
        return (f'a derrota para o {adv}', 'Assuma a culpa pelo resultado e proteja os jogadores.')

    def _responder(self, ds):
        """Responde alguns posts novos da torcida no tom do momento."""
        r = random.Random(_seed('ass_resp', ds, len(self.m['posts'])))
        mom = self.momento()['nivel']
        leal = self._leal() >= 0.55
        feitos = 0
        for p in reversed(self.m['posts'][-25:]):
            k = self._chave_post(p)
            if k in self.a['respondidos'] or p.get('assessor') or p.get('tecnico') or p.get('aovivo'):
                continue
            self.a['respondidos'].append(k)
            humor = p.get('humor') or 'neutro'
            if feitos >= (3 if self.p['estilo'] == 'marketeira' else 2) or r.random() < (0.55 if self.p['estilo'] == 'sobrio' else 0.35):
                continue
            banco = RESP[self.p['estilo']].get(humor) or RESP[self.p['estilo']]['neutro']
            txt = r.choice(banco).format(CLUBE=self.clube.upper(), clube=self.clube, tecnico=self.tecnico)
            if humor in ('revolta', 'chateado') and mom in ('pressao', 'crise') and r.random() < 0.6:
                txt += ' ' + r.choice(DEFESA[leal]).format(tecnico=self.tecnico)
            p.setdefault('respostas', []).insert(0, {'autor': self.arroba(), 'texto': txt, 'oficial': True,
                                                     'curtidas': r.randint(20, 900)})
            feitos += 1
        self.a['respondidos'] = self.a['respondidos'][-400:]
        if feitos:
            self._registrar(ds, f"Respondeu {feitos} torcedor{'es' if feitos > 1 else ''} nas redes.")

    def _semana(self, ds, engine):
        hoje = _s2d(ds)
        u = self.a.get('ult_semana')
        if u and (hoje - _s2d(u)).days < 7:
            return
        self.a['ult_semana'] = ds
        r = random.Random(_seed('ass_sem', ds, self.p['id']))
        # post institucional
        cs = [c for c in self.s.get('contratos', []) if c.get('status') == 'ativo']
        if cs and r.random() < 0.4:
            c = r.choice(cs)
            self._post(ds, PATRO[self.p['estilo']].format(clube=self.clube, empresa=c['empresa']), 'patro', r,
                       extra={'empresa': c['empresa']}, n_resp=r.randint(0, 2))
            self._registrar(ds, f"Publicou ação do patrocinador {c['empresa']}.")
        else:
            self._post(ds, r.choice(SEMANA[self.p['estilo']]), 'semana', r, n_resp=r.randint(0, 2))
            self._registrar(ds, 'Publicou o dia a dia do CT.')
        self._vazamento(ds, engine, r)

    # ----- bastidores e vazamentos -----
    def _segredos(self, ds):
        """O que o assessor sabe e ainda não vazou."""
        hoje = _s2d(ds)
        out = []
        ja = set(self.a['vazados'])
        g = self.s.get('gestao') or {}
        for e in g.get('eventos', []):
            k = f"ev:{e.get('id')}"
            if k in ja or not e.get('volta') or _s2d(e['volta']) <= hoje:
                continue
            if e.get('tipo') == 'lesao' and (e.get('dias') or (_s2d(e['volta']) - _s2d(e['data'])).days) >= 10:
                out.append(('lesao', k, {'jogador': e['jogador'], 'volta': _s2d(e['volta']).strftime('%d/%m')}))
            elif e.get('tipo') == 'indisciplina':
                out.append(('indisciplina', k, {'jogador': e['jogador'], 'motivo': (e.get('titulo') or 'indisciplina').lower()}))
        for x in self.a.get('segredos', []):
            k = f"exp:{x['jogador']}:{x['data']}"
            if k not in ja and (hoje - _s2d(x['data'])).days <= 10:
                out.append(('expulsao', k, {'jogador': x['jogador']}))
        din = self.s.get('dinheiro') or {}
        orc = din.get('orc_transf')
        if orc is not None and orc < 1_500_000 and f"fin:{ds[:7]}" not in ja:
            out.append(('financas', f"fin:{ds[:7]}", {'valor': _mi(orc)}))
        mom = self.momento()['nivel']
        if mom == 'crise' and self.m.get('diretoria', 60) <= 35 and f"cargo:{ds[:7]}" not in ja:
            out.append(('cargo', f"cargo:{ds[:7]}", {}))
        if mom == 'alta' and f"pos:{ds[:7]}" not in ja:
            out.append(('positivo', f"pos:{ds[:7]}", {}))
        if cs := [c for c in self.s.get('contratos', []) if c.get('status') == 'ativo']:
            if mom in ('alta', 'estavel') and f"pat:{ds[:7]}" not in ja:
                out.append(('patrocinio', f"pat:{ds[:7]}", {'empresa': random.Random(_seed(ds)).choice(cs)['empresa']}))
        return out

    def _vazamento(self, ds, engine, r):
        hoje = _s2d(ds)
        u = self.a.get('ult_vazamento')
        if u and (hoje - _s2d(u)).days < 13:          # no máximo um vazamento a cada duas semanas
            return
        tipos = self.a.setdefault('vaz_tipos', {})
        segs = [s for s in self._segredos(ds)          # mesmo assunto genérico só depois de 60 dias
                if s[0] in ('lesao', 'indisciplina', 'expulsao') or not tipos.get(s[0])
                or (hoje - _s2d(tipos[s[0]])).days >= 60]
        if not segs:
            return
        mom = self.momento()['nivel']
        leal = self._leal()
        chance = self.p['vaza'] * {'alta': 0.7, 'estavel': 1.0, 'pressao': 1.5, 'crise': 1.9}[mom] * (1.6 - leal)
        if r.random() > chance:
            return
        # num momento ruim, o assessor pouco leal solta o que prejudica; leal tenta segurar e solta o que ajuda
        boas = [s for s in segs if s[0] in ('positivo', 'patrocinio')]
        ruins = [s for s in segs if s[0] not in ('positivo', 'patrocinio')]
        if leal >= 0.6 and boas:
            tipo, k, v = r.choice(boas)
        elif ruins and (leal < 0.6 or r.random() < 0.4):
            tipo, k, v = r.choice(ruins)
        elif boas:
            tipo, k, v = r.choice(boas)
        else:
            return
        self.a['vazados'].append(k)
        self.a['vazados'] = self.a['vazados'][-200:]
        self.a['ult_vazamento'] = ds
        tipos[tipo] = ds
        from .textos import FONTES
        v = {**v, 'clube': self.clube, 'tecnico': self.tecnico}
        titulo = r.choice(VAZ_MANCHETE[tipo]).format(**v)
        self.m['noticias'].append({'data': ds, 'tipo': 'vazamento', 'titulo': titulo, 'destaque': tipo in ('cargo', 'financas'),
                                   'fonte': f"{r.choice(FONTES)} · fonte ligada ao clube", 'vazamento': True,
                                   **({'jogador': v['jogador']} if v.get('jogador') else {}),
                                   **({'empresa': v['empresa']} if v.get('empresa') else {})})
        self.m['noticias'] = self.m['noticias'][-200:]
        dt_t, dt_d = VAZ_EFEITO[tipo]
        self.m['torcida'] = int(max(0, min(100, self.m.get('torcida', 50) + dt_t)))
        self.m['diretoria'] = int(max(0, min(100, self.m.get('diretoria', 60) + dt_d)))
        if v.get('jogador') and tipo in ('indisciplina', 'expulsao'):
            from .gestao import moral_ajuste
            moral_ajuste(self.s, v['jogador'], -1, ds, 'exposto na imprensa', 10)
        assunto = {'lesao': f"a lesão de {v.get('jogador')}", 'indisciplina': f"a punição do {v.get('jogador')}",
                   'financas': 'o nosso orçamento', 'cargo': 'a sua situação no cargo', 'expulsao': f"a bronca no {v.get('jogador')}",
                   'positivo': 'a confiança da diretoria no seu trabalho', 'patrocinio': f"a parceria com a {v.get('empresa')}"}[tipo]
        if tipo in ('positivo', 'patrocinio'):
            modo = 'confessa'
        elif leal >= 0.6:
            modo = 'leal'
        else:
            modo = 'mentira'
        self._msg(engine, ds, 'Saiu na imprensa', r.choice(AVISO_VAZOU[modo]).format(assunto=assunto))
        self._registrar(ds, f"Vazou à imprensa: {assunto}." if modo != 'leal' else f"Saiu na imprensa: {assunto} (diz que não foi ele).")

    # ----- visão -----
    def view(self):
        mom = self.momento()
        vaz = sum(1 for n in self.m.get('noticias', []) if n.get('vazamento'))
        return {'nome': self.p['nome'], 'perfil': self.p['perfil'], 'estilo': ESTILO_NOME[self.p['estilo']],
                'arroba': self.arroba(), 'relacao': self.a['relacao'], 'momento': mom,
                'seguidores': self.a.get('seguidores') or 0, 'vazamentos': vaz,
                'discricao': int(round(100 * (1 - self.p['vaza'] * 2))),
                'log': self.a['log'][-8:][::-1]}
