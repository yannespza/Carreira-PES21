"""Mundo vivo do clube: imprensa, redes sociais, torcida e diretoria.
Tudo reage aos resultados lidos do save e aos contratos do app."""
import random, hashlib, datetime as dt

TORNEIO_LIGA = 17


def _seed(*p):
    return int(hashlib.md5('|'.join(map(str, p)).encode()).hexdigest()[:8], 16)


def eur_mi(v):
    from .sim import moeda
    simb, taxa = moeda()
    return f"{simb} {v * taxa / 1e6:.1f} mi".replace('.', ',')


# ---------------- textos ----------------
MANCHETES = {
    'goleada': ["{clube} atropela o {adv} e faz {placar}", "Show do {clube}: {placar} sobre o {adv}",
                "Massacre! {clube} não toma conhecimento do {adv} ({placar})",
                "{clube} dá aula e goleia o {adv} por {placar}"],
    'vitoria': ["{clube} vence o {adv} por {placar}", "{clube} supera o {adv} e soma mais três pontos",
                "Com {placar}, {clube} bate o {adv}", "{clube} faz o dever de casa: {placar} no {adv}",
                "Vitória importante: {clube} {placar} {adv}"],
    'empate': ["{clube} fica no {placar} com o {adv}", "Empate com o {adv} deixa gosto amargo no {clube}",
               "{clube} e {adv} não saem do {placar}", "Igualdade no placar: {clube} {placar} {adv}"],
    'derrota': ["{clube} perde para o {adv} por {placar}", "Tropeço: {clube} é derrotado pelo {adv}",
                "{adv} vence e complica a vida do {clube} ({placar})", "Noite ruim: {clube} cai diante do {adv}"],
    'vexame': ["Vexame! {clube} é goleado pelo {adv} ({placar})", "Apagão: {clube} leva {placar} do {adv}",
               "Torcida protesta após {placar} para o {adv}", "Crise à vista: {clube} sofre goleada do {adv}"],
    'seq_vitorias': ["{clube} embala: {n} vitórias seguidas", "Fase iluminada: {clube} chega a {n} triunfos em sequência",
                     "Ninguém segura o {clube}: {n} vitórias consecutivas"],
    'seq_derrotas': ["{clube} vive crise: {n} derrotas seguidas", "Pressão aumenta: {clube} perde a {n}ª seguida",
                     "Sequência negativa preocupa no {clube}: {n} jogos sem vencer"],
    'contrato_grande': ["{empresa} fecha com o {clube}: {valor} por temporada no {posicao}",
                        "Mercado aquecido: {clube} anuncia {empresa} como patrocinador",
                        "{clube} acerta com a {empresa} e reforça o caixa"],
    'contrato': ["{clube} anuncia a {empresa} no {posicao}", "Novo parceiro: {empresa} estampa o {posicao} do {clube}"],
    'rescisao': ["{empresa} deixa de patrocinar o {clube}", "Fim da parceria entre {clube} e {empresa}",
                 "{clube} perde o patrocínio da {empresa}"],
    'diretoria_cobra': ["Presidente cobra reação do {clube} após fase ruim", "Diretoria do {clube} pede mais em campo",
                        "Bastidores: clima esquenta na diretoria do {clube}"],
    'diretoria_elogia': ["Diretoria do {clube} elogia o trabalho do técnico", "Presidente celebra o momento do {clube}"],
}

POSTS = {
    'euforia': ["QUE TIME! 💚💚💚 {clube} é outro patamar", "esse time tá jogando por música, não tem pra ninguém 🔥",
                "dá pra sonhar com título sim, foda-se 💚", "{placar} e ainda foi pouco kkkkk",
                "o técnico merece estátua na porta do estádio 🏆"],
    'feliz': ["vitória importante, segue o baile 💚", "três pontos é o que importa", "boa, mas dá pra melhorar no segundo tempo",
              "bom resultado, bora manter a sequência", "{clube} trabalhando ✅"],
    'neutro': ["empate fora não é o fim do mundo", "jogo travado, faltou criatividade", "ponto é ponto... mas esperava mais",
               "time precisa de reforço no meio", "segue o campeonato"],
    'chateado': ["que fase... time sem alma", "não dá pra perder assim pro {adv}", "cadê a intensidade??",
                 "alguém explica essas substituições?", "torcida não merece isso"],
    'revolta': ["FORA TODO MUNDO 😡", "vergonha, {placar} é inaceitável", "diretoria acorda!! isso aqui é o {clube}",
                "devolve o dinheiro do ingresso", "chega de desculpa, quero resultado"],
}
ARROBAS = ['@verdao_raiz', '@alviverde_sp', '@palestrino10', '@torcedor_fiel', '@mancha_ofc', '@porco_doido',
           '@verde_mais', '@academia_fc', '@sp_palestra', '@nacao_verde', '@cronista_alviverde', '@jornalistaFC']

PRESIDENTE = {
    'boas_vindas': ["Bem-vindo ao comando do {clube}. A diretoria espera {meta_txt}. Conte com o nosso apoio."],
    'elogio': ["Estamos muito satisfeitos com o desempenho recente. Siga assim e o {clube} vai longe.",
               "O momento é excelente. A diretoria confia plenamente no seu trabalho."],
    'cobranca': ["A sequência recente preocupa a diretoria. Esperamos uma reação imediata.",
                 "Os resultados não estão à altura do {clube}. Precisamos de mais."],
    'ultimato': ["A paciência da diretoria está no limite. Sem reação nos próximos jogos, teremos que rever o comando técnico.",
                 "Sejamos francos: a situação é insustentável. Precisamos de vitórias já."],
    'meta_financeira': ["Ótimo trabalho no mercado de patrocínios: {valor} por temporada em contratos. O caixa agradece.",],
}


class Mundo:
    def __init__(self, state, clube='Palmeiras', team_id=137, base_torcida=62):
        self.s = state
        self.clube = clube
        self.team_id = team_id
        m = self.s.setdefault('mundo', {})
        m.setdefault('torcida', base_torcida)
        m.setdefault('diretoria', 70)
        m.setdefault('noticias', [])
        m.setdefault('posts', [])
        m.setdefault('vistos', {'partidas': [], 'contratos': [], 'encerrados': []})
        m.setdefault('historico', [])     # evolução (data, torcida, diretoria)
        m.setdefault('alertas_dir', {})
        self.m = m

    # ---------- utilidades ----------
    def _hoje(self):
        return self.s.get('data')

    def noticia(self, tipo, data, rnd, destaque=False, **v):
        v.setdefault('clube', self.clube)
        txt = rnd.choice(MANCHETES[tipo]).format(**v)
        fonte = rnd.choice(['Globo Esporte', 'Lance!', 'ESPN', 'UOL Esporte', 'Gazeta Esportiva', 'TNT Sports'])
        self.m['noticias'].append({'data': data, 'titulo': txt, 'tipo': tipo, 'fonte': fonte, 'destaque': destaque})
        self.m['noticias'] = self.m['noticias'][-200:]

    def posts(self, humor, data, rnd, n=3, **v):
        v.setdefault('clube', self.clube)
        for t in rnd.sample(POSTS[humor], min(n, len(POSTS[humor]))):
            self.m['posts'].append({'data': data, 'autor': rnd.choice(ARROBAS), 'texto': t.format(**v),
                                    'humor': humor, 'curtidas': rnd.randint(40, 4000)})
        self.m['posts'] = self.m['posts'][-300:]

    def presidente(self, engine, tipo, data, **v):
        r = random.Random(_seed('pres', tipo, data))
        v.setdefault('clube', self.clube)
        texto = r.choice(PRESIDENTE[tipo]).format(**v)
        assunto = {'boas_vindas': 'Metas da temporada', 'elogio': 'Mensagem da presidência',
                   'cobranca': 'Cobrança da diretoria', 'ultimato': 'URGENTE: situação do time',
                   'meta_financeira': 'Patrocínios'}[tipo]
        engine.s['mensagens'].append({'id': engine._id(), 'data': data, 'empresa': '__diretoria__',
                                      'de': 'Presidência · ' + self.clube, 'assunto': assunto, 'texto': texto,
                                      'tipo': 'diretoria', 'oferta_id': None, 'lida': False})

    # ---------- metas ----------
    def metas(self):
        return self.m.setdefault('metas', {'aproveitamento': 60, 'patrocinio': 15_000_000})

    def aproveitamento(self):
        ps = [p for p in self.s.get('partidas', []) if p['torneio'] == TORNEIO_LIGA]
        if not ps:
            return None
        pts = sum({'V': 3, 'E': 1, 'D': 0}[p['res']] for p in ps)
        return round(100 * pts / (3 * len(ps)))

    def patrocinio_anual(self):
        return sum(c['valor'] for c in self.s.get('contratos', []) if c['status'] in ('ativo', 'assinado'))

    # ---------- reação aos acontecimentos ----------
    def processar(self, engine, nomes):
        data = self._hoje()
        if not data:
            return
        vis = self.m['vistos']
        if not self.m.get('iniciado'):
            self.m['iniciado'] = True
            mt = self.metas()
            self.presidente(engine, 'boas_vindas', data,
                            meta_txt=f"aproveitamento de pelo menos {mt['aproveitamento']}% dos pontos no Brasileirão "
                                     f"e {eur_mi(mt['patrocinio'])} por temporada em patrocínios")
            # partidas já existentes não geram notícia retroativa
            vis['partidas'] = [p['chave'] for p in self.s.get('partidas', [])]
            vis['contratos'] = [c['id'] for c in self.s.get('contratos', [])]
            vis['encerrados'] = [c['id'] for c in self.s.get('contratos', []) if c['status'] in ('encerrado', 'rescindido')]
        # partidas novas
        for p in self.s.get('partidas', []):
            if p['chave'] in vis['partidas']:
                continue
            vis['partidas'].append(p['chave'])
            self._partida(p, nomes)
        # contratos novos e encerrados
        for c in self.s.get('contratos', []):
            r = random.Random(_seed('c', c['id'], c['status']))
            from .kits import SLOTS
            pos = 'espaço “' + SLOTS[c['slot']]['nome'] + '”'
            if c['id'] not in vis['contratos']:
                vis['contratos'].append(c['id'])
                grande = c['valor'] >= 5_000_000
                self.noticia('contrato_grande' if grande else 'contrato', data, r, destaque=grande,
                             empresa=c['empresa'], posicao=pos, valor=eur_mi(c['valor']))
                self._torcida(+3 if grande else +1)
            if c['status'] in ('encerrado', 'rescindido') and c['id'] not in vis['encerrados']:
                vis['encerrados'].append(c['id'])
                self.noticia('rescisao', data, r, empresa=c['empresa'], posicao=pos)
                self._torcida(-2 if c['valor'] >= 5_000_000 else -1)
        self._diretoria(engine, data)
        h = self.m['historico']
        if not h or h[-1][0] != data:
            h.append([data, self.m['torcida'], self.m['diretoria']])
        else:
            h[-1] = [data, self.m['torcida'], self.m['diretoria']]
        self.m['historico'] = h[-120:]

    def _torcida(self, delta):
        self.m['torcida'] = int(max(0, min(100, self.m['torcida'] + delta)))

    def _partida(self, p, nomes):
        casa = p['mandante'] == self.team_id
        gp, gc = (p['gm'], p['gv']) if casa else (p['gv'], p['gm'])
        adv = nomes(p['visitante'] if casa else p['mandante'])
        placar = f"{gp} a {gc}"
        r = random.Random(_seed('p', p['chave']))
        saldo = gp - gc
        if saldo >= 3:
            tipo, humor, delta = 'goleada', 'euforia', 7
        elif saldo > 0:
            tipo, humor, delta = 'vitoria', 'feliz', 4 + (1 if casa else 0)
        elif saldo == 0:
            tipo, humor, delta = 'empate', 'neutro', -1 if casa else 0
        elif saldo <= -3:
            tipo, humor, delta = 'vexame', 'revolta', -9
        else:
            tipo, humor, delta = 'derrota', 'chateado', -5 if casa else -4
        self._torcida(delta)
        self.noticia(tipo, p['data'], r, destaque=tipo in ('goleada', 'vexame'), adv=adv, placar=placar)
        # sequências
        seq = self.s.get('partidas', [])
        n = 0
        alvo = p['res']
        for x in reversed(seq):
            if x['res'] == alvo:
                n += 1
            else:
                break
        if alvo == 'V' and n >= 3:
            self.noticia('seq_vitorias', p['data'], r, destaque=True, n=n); self._torcida(2)
            humor = 'euforia'
        if alvo == 'D' and n >= 3:
            self.noticia('seq_derrotas', p['data'], r, destaque=True, n=n); self._torcida(-3)
            humor = 'revolta'
        # humor da torcida pesa nos posts
        t = self.m['torcida']
        if humor == 'feliz' and t >= 80:
            humor = 'euforia'
        if humor == 'chateado' and t <= 30:
            humor = 'revolta'
        self.posts(humor, p['data'], r, n=3, adv=adv, placar=placar)

    def _diretoria(self, engine, data):
        ap = self.aproveitamento()
        mt = self.metas()
        t = self.m['torcida']
        alvo = 70
        if ap is not None:
            alvo = 50 + (ap - mt['aproveitamento']) * 1.2
        alvo += (t - 60) * 0.3
        if self.patrocinio_anual() >= mt['patrocinio']:
            alvo += 8
        alvo = max(0, min(100, alvo))
        # muda devagar (no máximo 6 pontos por leitura)
        d = self.m['diretoria']
        d = d + max(-6, min(6, alvo - d))
        self.m['diretoria'] = int(round(d))
        al = self.m['alertas_dir']
        hoje = dt.date.fromisoformat(data)

        def pode(chave, dias):
            u = al.get(chave)
            return not u or (hoje - dt.date.fromisoformat(u)).days >= dias
        r = random.Random(_seed('dir', data))
        if self.m['diretoria'] <= 25 and pode('ultimato', 30):
            al['ultimato'] = data; self.presidente(engine, 'ultimato', data)
            self.noticia('diretoria_cobra', data, r, destaque=True)
        elif self.m['diretoria'] <= 40 and pode('cobranca', 21):
            al['cobranca'] = data; self.presidente(engine, 'cobranca', data)
            self.noticia('diretoria_cobra', data, r)
        elif self.m['diretoria'] >= 82 and pode('elogio', 30):
            al['elogio'] = data; self.presidente(engine, 'elogio', data)
            self.noticia('diretoria_elogia', data, r)
        if self.patrocinio_anual() >= mt['patrocinio'] and not al.get('meta_fin'):
            al['meta_fin'] = data
            self.presidente(engine, 'meta_financeira', data, valor=eur_mi(self.patrocinio_anual()))

    # ---------- efeito no mercado ----------
    def bonus_atratividade(self):
        return int(round((self.m['torcida'] - 60) / 5))

    def view(self):
        ap = self.aproveitamento()
        return {'torcida': self.m['torcida'], 'diretoria': self.m['diretoria'], 'metas': self.metas(),
                'aproveitamento': ap, 'patrocinio_anual': self.patrocinio_anual(),
                'noticias': self.m['noticias'][-40:][::-1], 'posts': self.m['posts'][-40:][::-1],
                'historico': self.m['historico'][-40:]}
