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


# ---------------- textos (banco em textos.py) ----------------
from .textos import MANCHETES, POSTS, PRESIDENTE, RESPOSTAS, POSTS_TECNICO, FONTES

ARROBAS_PALMEIRAS = ['@verdao_raiz', '@alviverde_sp', '@palestrino10', '@torcedor_fiel', '@mancha_ofc', '@porco_doido',
                     '@verde_mais', '@academia_fc', '@sp_palestra', '@nacao_verde', '@cronista_alviverde', '@jornalistaFC']


def arrobas(clube):
    if 'PALMEIRAS' in clube.upper():
        return ARROBAS_PALMEIRAS
    c = ''.join(ch for ch in __import__('unicodedata').normalize('NFKD', clube).lower() if ch.isalnum())[:12]
    return [f'@{c}_raiz', f'@torcida{c}', f'@{c}_oficialfans', f'@sou{c}', f'@{c}10', f'@nacao_{c}',
            f'@{c}depressao', f'@fala{c}', '@torcedor_fiel', '@jornalistaFC', '@cornetafc', '@resenha_fut']

TECNICO_PADRAO = 'Yannes Zola'


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
        self.rivais = set()       # ids dos rivais (o app preenche antes de processar)
        self.nomes = None

    # ---------- utilidades ----------
    def _hoje(self):
        return self.s.get('data')

    def tecnico(self):
        return (self.s.get('cfg_tecnico') or TECNICO_PADRAO)

    def _vars(self, v, rnd):
        v.setdefault('clube', self.clube)
        v.setdefault('tecnico', self.tecnico())
        el = self.s.get('elenco_nomes') or []
        v.setdefault('jogador', rnd.choice(el) if el else 'o camisa 10')
        if 'empresa' not in v:
            cs = [c['empresa'] for c in self.s.get('contratos', []) if c['status'] in ('ativo', 'assinado')]
            v['empresa'] = rnd.choice(cs) if cs else 'o novo patrocinador'
        v.setdefault('setor', 'marca')
        for k in ('adv', 'placar', 'n', 'pos', 'pts', 'lider', 'valor', 'posicao', 'frase', 'meta', 'classico'):
            v.setdefault(k, '')
        v.setdefault('CLUBE', str(v['clube']).upper())
        return v

    def noticia(self, tipo, data, rnd, destaque=False, **v):
        extra = {k: v[k] for k in ('placar', 'adv', 'empresa', 'n', 'pos', 'classico') if v.get(k) not in (None, '')}
        self._vars(v, rnd)
        txt = rnd.choice(MANCHETES[tipo]).format(**v)
        self.m['noticias'].append({'data': data, 'titulo': txt, 'tipo': tipo, 'fonte': rnd.choice(FONTES),
                                   'destaque': destaque, **extra})
        self.m['noticias'] = self.m['noticias'][-200:]

    def _respostas(self, humor, rnd, autor, v, n=None):
        pool = RESPOSTAS.get(humor) or RESPOSTAS['neutro']
        n = rnd.randint(0, 3) if n is None else n
        outros = [a for a in arrobas(self.clube) if a != autor]
        return [{'autor': rnd.choice(outros), 'texto': rnd.choice(pool).format(**v),
                 'curtidas': rnd.randint(0, 600)} for _ in range(n)]

    def posts(self, humor, data, rnd, n=3, **v):
        emp = v.get('empresa') if humor == 'patro' else None
        self._vars(v, rnd)
        for t in rnd.sample(POSTS[humor], min(n, len(POSTS[humor]))):
            autor = rnd.choice(arrobas(self.clube))
            cur = rnd.randint(40, 4000)
            self.m['posts'].append({'data': data, 'autor': autor, 'texto': t.format(**v), 'humor': humor,
                                    'curtidas': cur, 'reposts': int(cur * rnd.uniform(0.05, 0.3)),
                                    'respostas': self._respostas(humor, rnd, autor, v),
                                    **({'empresa': emp} if emp else {})})
        self.m['posts'] = self.m['posts'][-300:]

    def post_tecnico(self, contexto, idx, data):
        texto, efeito = POSTS_TECNICO[contexto][idx]
        rnd = random.Random(_seed('tec', data, contexto, idx, len(self.m['posts'])))
        v = self._vars({}, rnd)
        texto = texto.format(**v)
        # torcida reage conforme o momento: palavra bonita em fase ruim rende menos
        t = self.m['torcida']
        bom = efeito > 0 and (t >= 45 or rnd.random() < 0.5)
        self._torcida(efeito if bom else min(0, efeito))
        cur = int(rnd.randint(2000, 9000) * (0.6 + t / 100))
        arroba = '@' + ''.join(c for c in self.tecnico().lower() if c.isalnum())
        self.m['posts'].append({'data': data, 'autor': arroba, 'tecnico': True, 'texto': texto,
                                'humor': 'tecnico', 'curtidas': cur, 'reposts': int(cur * 0.2),
                                'respostas': self._respostas('tecnico_bom' if bom else 'tecnico_ruim', rnd, arroba, v,
                                                             n=rnd.randint(2, 4))})
        self.m['ult_post_tecnico'] = data
        return bom

    def contexto_tecnico(self):
        ps = self.s.get('partidas', [])
        if ps:
            ult = ps[-1]
            return {'V': 'vitoria', 'D': 'derrota', 'E': 'empate'}[ult['res']]
        return 'geral'

    def presidente(self, engine, tipo, data, **v):
        r = random.Random(_seed('pres', tipo, data))
        v.setdefault('clube', self.clube)
        v.setdefault('tecnico', self.tecnico())
        texto = r.choice(PRESIDENTE[tipo]).format(**v)
        assunto = {'boas_vindas': 'Metas da temporada', 'elogio': 'Mensagem da presidência',
                   'cobranca': 'Cobrança da diretoria', 'ultimato': 'URGENTE: situação do time',
                   'meta_financeira': 'Patrocínios', 'tabela_boa': 'Posição na tabela',
                   'tabela_ruim': 'Posição na tabela'}[tipo]
        engine.s['mensagens'].append({'id': engine._id(), 'data': data, 'empresa': '__diretoria__',
                                      'de': 'Presidência · ' + self.clube, 'assunto': assunto, 'texto': texto,
                                      'tipo': 'diretoria', 'oferta_id': None, 'lida': False})

    # ---------- metas ----------
    def metas(self):
        if 'metas' not in self.m:
            # meta de patrocínio proporcional ao tamanho do clube (posições do uniforme e atratividade)
            from .kits import SLOTS
            atr = self.s.get('atr_base', 60)
            pot = sum(v['valor_base'] for v in SLOTS.values()) * (0.45 + atr / 100 * 0.9)
            meta = int(round(pot * 0.6 / 500_000) * 500_000) or 5_000_000
            self.m['metas'] = {'aproveitamento': 60 if atr >= 60 else 55, 'patrocinio': meta}
        return self.m['metas']

    def liga(self):
        """Campeonato de pontos corridos da carreira: o torneio com mais jogos."""
        from collections import Counter
        c = Counter(p['torneio'] for p in self.s.get('partidas', []))
        ligas = [t for t, _ in c.most_common() if (int(t) & 1023) in (17, 79, 81, 80)]   # Séries A, B, C, D
        if ligas:
            return ligas[0]
        return c.most_common(1)[0][0] if c else TORNEIO_LIGA

    def aproveitamento(self):
        liga = self.liga()
        ps = [p for p in self.s.get('partidas', []) if p['torneio'] == liga]
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
                            meta_txt=f"aproveitamento de pelo menos {mt['aproveitamento']}% dos pontos no campeonato "
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
            pos = 'espaço “' + SLOTS.get(c['slot'], {}).get('nome', c['slot']) + '”'
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
        self._tabela(engine, data)
        self._semana(data)
        self._diretoria(engine, data)
        h = self.m['historico']
        if not h or h[-1][0] != data:
            h.append([data, self.m['torcida'], self.m['diretoria']])
        else:
            h[-1] = [data, self.m['torcida'], self.m['diretoria']]
        self.m['historico'] = h[-120:]

    def _tabela(self, engine, data):
        """Notícias de posição na tabela quando ela muda (lida do save)."""
        T = (self.s.get('tabela') or {}).get('linhas') or []
        if not T:
            return
        jogos = sum(l['j'] for l in T)
        ant = self.m.get('tab_ult') or {}
        if ant.get('jogos') == jogos:
            return
        meu = next((l for l in T if l['id'] == self.team_id), None)
        self.m['tab_ult'] = {'jogos': jogos, 'pos': meu['pos'] if meu else None,
                             'lider': T[0]['id']}
        if not meu or not ant:
            return
        r = random.Random(_seed('tab', data, jogos))
        n = len(T)
        pos, pa = meu['pos'], ant.get('pos')
        v = dict(pos=pos, pts=meu['pts'], lider=T[0].get('nome', ''))
        if pos == 1:
            self.noticia('lider' if pa != 1 else 'lider_segue', data, r, destaque=pa != 1, **v)
            if pa != 1:
                self._torcida(3)
        else:
            if pa and pos <= 4 < pa:
                self.noticia('g4', data, r, destaque=True, **v); self._torcida(2)
            elif pa and pos > n - 4 >= pa:
                self.noticia('z4', data, r, destaque=True, **v); self._torcida(-3)
            elif pa and pos < pa:
                self.noticia('sobe', data, r, **v)
            elif pa and pos > pa:
                self.noticia('cai', data, r, **v)
            if r.random() < 0.6:
                self.noticia('outro_lider', data, r, pts=T[0]['pts'], pos=pos, lider=T[0].get('nome', ''))
        # diretoria comenta a tabela de vez em quando
        al = self.m['alertas_dir']
        hoje = dt.date.fromisoformat(data)
        u = al.get('tabela')
        if meu['j'] >= 5 and (not u or (hoje - dt.date.fromisoformat(u)).days >= 45):
            if pos <= max(2, n // 6):
                al['tabela'] = data; self.presidente(engine, 'tabela_boa', data, pos=pos)
            elif pos > n - 4:
                al['tabela'] = data; self.presidente(engine, 'tabela_ruim', data, pos=pos)

    def _semana(self, data):
        """Bastidores: a cada semana da carreira sai alguma notícia e a torcida conversa nas redes."""
        hoje = dt.date.fromisoformat(data)
        u = self.m.get('ult_semana')
        if u and (hoje - dt.date.fromisoformat(u)).days < 7:
            return
        self.m['ult_semana'] = data
        r = random.Random(_seed('sem', data))
        for _ in range(r.randint(1, 2)):
            self.noticia('bastidores', data, r)
        # notícia sobre um jogador: elogio sobe a moral dele, crítica derruba (por uns 10 dias)
        el = self.s.get('elenco_nomes') or []
        if el and r.random() < 0.55:
            from .gestao import moral_ajuste
            jog = r.choice(el)
            imp = (self.s.get('gestao') or {}).get('imprensa', 55)     # relação com a imprensa
            bom = r.random() < (0.35 + self.m['torcida'] / 200 + (imp - 55) / 250)
            self.noticia('jog_elogio' if bom else 'jog_critica', data, r, jogador=jog)
            self.m['noticias'][-1]['jogador'] = jog
            moral_ajuste(self.s, jog, 1 if bom else -1, data, 'elogiado na imprensa' if bom else 'criticado na imprensa', 10)
        # rumor de patrocínio com empresa que ainda não está no clube
        emps = [e for e in (self.s.get('empresas') or {}) if not any(
            c['empresa'] == e and c['status'] in ('ativo', 'assinado') for c in self.s.get('contratos', []))]
        if emps and r.random() < 0.35:
            self.noticia('rumor_patro', data, r, empresa=r.choice(emps))
        self.posts('semana', data, r, n=r.randint(2, 4))
        cs = [c for c in self.s.get('contratos', []) if c['status'] == 'ativo']
        if cs and r.random() < 0.4:
            c = r.choice(cs)
            setor = ((self.s.get('empresas') or {}).get(c['empresa']) or {}).get('setor', 'marca')
            self.posts('patro', data, r, n=1, empresa=c['empresa'], setor=setor)

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
        adv_id = p['visitante'] if casa else p['mandante']
        classico = adv_id in self.rivais
        from . import vestiario
        vestiario.resultado(self.s, p, self.team_id, classico)
        if classico:
            from . import rivais
            from .gestao import moral_ajuste
            nome_c = rivais.nome_classico(self.clube, adv)
            self._torcida(round(delta * 0.6) + {'V': 3, 'E': 0, 'D': -3}[p['res']])
            self.m['diretoria'] = int(max(0, min(100, self.m['diretoria'] + {'V': 4, 'E': 0, 'D': -4}[p['res']])))
            self.noticia('classico_' + p['res'].lower(), p['data'], r, destaque=True, adv=adv, placar=placar, classico=nome_c)
            self.m['noticias'][-1].update(gp=gp, gc=gc, casa=casa)
            if p['res'] != 'E':
                moral_ajuste(self.s, '*', 1 if p['res'] == 'V' else -1, p['data'],
                             ('venceu' if p['res'] == 'V' else 'perdeu') + f' o {nome_c}', 10)
            self._provocacao(p, adv, nome_c, gp, gc, r)
        self._torcida(delta)
        if not classico:       # no clássico a manchete própria já saiu
            self.noticia(tipo, p['data'], r, destaque=tipo in ('goleada', 'vexame'), adv=adv, placar=placar)
            self.m['noticias'][-1].update(gp=gp, gc=gc, casa=casa)
        if tipo in ('goleada', 'vexame'):
            from .gestao import moral_ajuste
            moral_ajuste(self.s, '*', 1 if tipo == 'goleada' else -1, p['data'],
                         'goleada' if tipo == 'goleada' else 'goleada sofrida', 7)
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
            from .gestao import moral_ajuste
            moral_ajuste(self.s, '*', 1, p['data'], f'{n} vitórias seguidas', 10)
            humor = 'euforia'
        inv = 0
        for x in reversed(seq):
            if x['res'] != 'D':
                inv += 1
            else:
                break
        if inv in (5, 8, 10, 15, 20):
            self.noticia('invicto', p['data'], r, destaque=True, n=inv)
        if alvo == 'D' and n >= 3:
            self.noticia('seq_derrotas', p['data'], r, destaque=True, n=n); self._torcida(-3)
            from .gestao import moral_ajuste
            moral_ajuste(self.s, '*', -1, p['data'], f'{n} derrotas seguidas', 10)
            humor = 'revolta'
        # humor da torcida pesa nos posts
        t = self.m['torcida']
        if humor == 'feliz' and t >= 80:
            humor = 'euforia'
        if humor == 'chateado' and t <= 30:
            humor = 'revolta'
        self.posts(humor, p['data'], r, n=3, adv=adv, placar=placar)

    def _provocacao(self, p, adv, nome_c, gp, gc, r):
        """Depois do clássico, a torcida rival e a nossa se provocam nas redes."""
        from .rivais import norm
        tag = ''.join(norm(adv))[:12] or 'rival'
        placar = f'{gp} a {gc}'
        if p['res'] == 'V':
            nossos = [f'O {nome_c} é nosso! {placar} e o {adv} chorando de novo 😂', f'Freguês é freguês. {adv} sabe o caminho de casa.',
                      f'Semana inteira zoando o {adv}. Que delícia de {nome_c}!']
            deles = ['Sorte. Só sorte. Juiz ajudou.', 'Ganharam um jogo e já acham que são campeões kkkk',
                     'Aproveita que dura pouco.']
        elif p['res'] == 'D':
            nossos = [f'Inadmissível perder o {nome_c}. Quero explicação!', 'Clássico não se joga, se ganha. Vergonha.',
                      f'Uma semana inteira ouvindo piada do {adv}. Obrigado, time.']
            deles = [f'{placar} e foi pouco 😂', f'Liga pra gente quando aprender a jogar {nome_c}.',
                     'Freguesia confirmada. Bom dia pra quem é do lado certo.']
        else:
            nossos = [f'Empate no {nome_c} tem gosto de nada.', 'Clássico pede mais vontade.']
            deles = ['Saíram de campo comemorando empate kkk', 'Com esse time, empate foi lucro pra vocês.']
        v = self._vars({'adv': adv, 'placar': placar}, r)
        for t in r.sample(nossos, 2):
            autor = r.choice(arrobas(self.clube))
            cur = r.randint(2000, 15000)
            self.m['posts'].append({'data': p['data'], 'autor': autor, 'texto': t, 'humor': 'classico',
                                    'curtidas': cur, 'reposts': int(cur * 0.25),
                                    'respostas': [{'autor': f'@{tag}{r.choice(["_oficialfans", "10", "_raiz", "depressao"])}',
                                                   'texto': r.choice(deles), 'curtidas': r.randint(50, 3000)}]
                                                 + self._respostas('euforia' if p['res'] == 'V' else 'revolta', r, autor, v, n=1)})
        self.m['posts'] = self.m['posts'][-300:]

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
                'noticias': self.m['noticias'][-60:][::-1], 'posts': self.m['posts'][-60:][::-1],
                'tecnico': self.tecnico(), 'opcoes_post': [t for t, _ in POSTS_TECNICO[self.contexto_tecnico()]]
                + [t.replace('{clube}', self.clube) for t, _ in POSTS_TECNICO['geral']],
                'contexto_post': self.contexto_tecnico(),
                'historico': self.m['historico'][-40:]}
