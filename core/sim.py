"""Motor do mercado de patrocínio: atratividade, ofertas, negociação, contratos e pagamentos.
O tempo corre na data da carreira (lida do save), não na data real."""
import random, hashlib, datetime as dt
from . import mensagens
from .kits import SLOTS, SLOT_ORDER

PORTE_FATOR = {'grande': (1.0, 1.35), 'media': (0.55, 0.9), 'pequena': (0.25, 0.5)}
PORTE_MIN_ATR = {'grande': 58, 'media': 35, 'pequena': 0}
PERSONALIDADES = ['agressiva', 'paciente', 'fiel', 'oportunista']

EMPRESAS_PADRAO = {
    'Banco do Brasil': ('banco', 'grande'), 'Bradesco': ('banco', 'grande'), 'Caixa': ('banco', 'grande'),
    'Sicredi': ('banco', 'media'), 'iti Itau': ('banco', 'media'), 'Claro': ('telecom', 'grande'),
    'Vivo': ('telecom', 'grande'), 'TIM': ('telecom', 'grande'), 'Samsung': ('eletronicos', 'grande'),
    'Motorola': ('eletronicos', 'media'), 'Fiat': ('automoveis', 'grande'), 'Cimed': ('farmaceutica', 'media'),
    'Renner': ('varejo', 'media'), 'Madero': ('alimentacao', 'pequena'),
}


# o que cada perfil de empresa prefere nas cláusulas: (quer cláusula de desempenho?, multa de rescisão %)
PREF_CLAUSULAS = {'agressiva': (True, 20), 'oportunista': (True, 10), 'paciente': (False, 30), 'fiel': (False, 30)}
MULTAS = (10, 20, 30, 50)


def clausulas_txt(cl):
    d = 'com cláusula de desempenho (a empresa pode sair sem multa se o time for mal)' if cl.get('desempenho') \
        else 'sem cláusula de desempenho'
    return f"{d}; multa de rescisão de {cl.get('multa_pct', 30)}% do valor restante para quem romper"


def d2s(d): return d.isoformat()
def s2d(s): return dt.date.fromisoformat(s)


def fmt_eur(v):
    return '€ ' + f'{int(round(v)):,}'.replace(',', '.')


def fmt_data(d):
    return d.strftime('%d/%m/%Y')


def pos_txt(slot):
    return 'espaço “' + SLOTS[slot]['nome'] + '”'


def anos_txt(n): return f'{n} temporada' + ('s' if n > 1 else '')


def _seed(*parts):
    return int(hashlib.md5('|'.join(map(str, parts)).encode()).hexdigest()[:8], 16)


class Engine:
    def __init__(self, state, clube='Palmeiras', base_atr=68):
        self.s = state
        self.clube = clube
        self.base_atr = base_atr
        s = self.s
        s.setdefault('empresas', {}); s.setdefault('ofertas', []); s.setdefault('contratos', [])
        s.setdefault('mensagens', []); s.setdefault('partidas', []); s.setdefault('seq', 1)
        s.setdefault('eventos', []); s.setdefault('multas', [])

    # ---------- empresas ----------
    def sync_empresas(self, nomes_pastas):
        for nome, pasta in nomes_pastas:
            if nome in self.s['empresas']:
                continue
            setor, porte = EMPRESAS_PADRAO.get(nome, ('outros', None))
            if porte is None:
                p = (pasta or '').lower()
                porte = 'grande' if 'grand' in p else 'pequena' if 'pequen' in p else 'media'
            r = random.Random(_seed(nome))
            self.s['empresas'][nome] = {'setor': setor, 'porte': porte,
                                        'personalidade': r.choice(PERSONALIDADES), 'bloqueio_ate': None}

    # ---------- utilidades ----------
    def _id(self):
        self.s['seq'] += 1
        return self.s['seq']

    def hoje(self):
        return s2d(self.s['data']) if self.s.get('data') else None

    def forma(self, n=5):
        ps = self.s['partidas'][-n:]
        return ''.join(p['res'] for p in ps) or '—'

    def atratividade(self):
        ps = self.s['partidas'][-8:]
        pts = 0.0
        for i, p in enumerate(ps):
            peso = 0.6 + 0.4 * (i + 1) / max(1, len(ps))
            pts += {'V': 4.0, 'E': 0.5, 'D': -3.5}[p['res']] * peso
        # sequência de vitórias pesa mais
        seq = 0
        for p in reversed(ps):
            if p['res'] == 'V': seq += 1
            else: break
        pts += 2.0 * max(0, seq - 2)
        return int(max(15, min(100, self.base_atr + pts)))

    def msg(self, tipo, empresa, data, oferta_id=None, **v):
        info = self.s['empresas'].get(empresa, {})
        pers = info.get('personalidade', 'paciente')
        r = random.Random(_seed(tipo, empresa, data, self.s['seq']))
        base = {'clube': self.clube, 'empresa': empresa, 'forma': self.forma(), 'contato': ''}
        base.update(v)
        assunto, corpo = mensagens.texto(tipo, pers, r, **base)
        contato = r.choice(mensagens.CONTATOS.get(pers, ['Marketing']))
        self.s['mensagens'].append({'id': self._id(), 'data': data, 'empresa': empresa, 'de': f'{empresa} · {contato}',
                                    'assunto': assunto, 'texto': corpo, 'tipo': tipo, 'oferta_id': oferta_id,
                                    'lida': False})

    def slots_livres(self, data):
        ocupados = {c['slot'] for c in self.s['contratos'] if c['status'] in ('assinado', 'ativo')}
        return [k for k in SLOT_ORDER if k not in ocupados]

    def setores_ocupados(self):
        return {self.s['empresas'].get(c['empresa'], {}).get('setor') for c in self.s['contratos']
                if c['status'] in ('assinado', 'ativo')} - {'outros', None}

    def valor_justo(self, empresa, slot, atr=None, r=None):
        atr = self.atratividade() if atr is None else atr
        porte = self.s['empresas'][empresa]['porte']
        lo, hi = PORTE_FATOR[porte]
        f = (lo + hi) / 2 if r is None else r.uniform(lo, hi)
        v = SLOTS[slot]['valor_base'] * f * (0.45 + atr / 100 * 0.9)
        return int(round(v / 50_000) * 50_000) or 50_000

    # ---------- partidas ----------
    def registrar_partidas(self, results, team_id, data):
        conhecidas = {p['chave'] for p in self.s['partidas']}
        novas = []
        for r in results:
            chave = f"{r['torneio']}-{r['mandante']}-{r['visitante']}-{r['offset']}"
            if chave in conhecidas:
                continue
            casa = r['mandante'] == team_id
            gp, gc = (r['gols_mandante'], r['gols_visitante']) if casa else (r['gols_visitante'], r['gols_mandante'])
            res = 'V' if gp > gc else 'E' if gp == gc else 'D'
            p = {'chave': chave, 'data': data, 'torneio': r['torneio'], 'mandante': r['mandante'],
                 'visitante': r['visitante'], 'gm': r['gols_mandante'], 'gv': r['gols_visitante'], 'res': res}
            self.s['partidas'].append(p); novas.append(p)
        return novas

    # ---------- avanço do tempo ----------
    def avancar(self, nova_data: dt.date, primeira_leitura=False):
        """Roda a simulação do último dia conhecido até a nova data."""
        antiga = self.hoje()
        self.s['data'] = d2s(nova_data)
        if primeira_leitura or antiga is None:
            self.s['ultima_semana'] = d2s(nova_data)
            self._gerar_ofertas(nova_data, forcar=2)
            return
        if nova_data <= antiga:
            return
        dia = antiga
        while dia < nova_data:
            dia += dt.timedelta(days=1)
            self._dia(dia)

    def _dia(self, dia):
        ds = d2s(dia)
        # ofertas expiram
        for o in self.s['ofertas']:
            if o['status'] in ('aberta',) and s2d(o['validade']) < dia:
                o['status'] = 'expirada'
                self.msg('expirou', o['empresa'], ds, o['id'], posicao=pos_txt(o['slot']))
        # respostas de negociação
        for o in self.s['ofertas']:
            if o['status'] == 'aguardando' and s2d(o['resposta_em']) <= dia:
                self._responder(o, dia)
        # contratos: início, pagamentos anuais, fim
        for c in self.s['contratos']:
            if c['status'] == 'assinado' and s2d(c['inicio']) <= dia:
                c['status'] = 'ativo'
                self.s['eventos'].append({'tipo': 'kits', 'data': ds})
            if c['status'] == 'ativo':
                for pg in c['pagamentos']:
                    if pg['status'] == 'agendado' and s2d(pg['data']) <= dia:
                        pg['status'] = 'pendente'
                if s2d(c['fim']) <= dia:
                    c['status'] = 'encerrado'
                    self.s['eventos'].append({'tipo': 'kits', 'data': ds})
                    self.msg('fim_contrato', c['empresa'], ds, posicao=pos_txt(c['slot']))
        # uma vez por semana: novas ofertas e humor dos patrocinadores
        ult = s2d(self.s.get('ultima_semana', ds))
        if (dia - ult).days >= 7:
            self.s['ultima_semana'] = ds
            self._gerar_ofertas(dia)
            self._humor_patrocinadores(dia)
            self._corte_de_verba(dia)

    def _gerar_ofertas(self, dia, forcar=0):
        ds = d2s(dia)
        atr = self.atratividade()
        r = random.Random(_seed('ofertas', ds, self.s['seq']))
        livres = self.slots_livres(dia)
        abertas = [o for o in self.s['ofertas'] if o['status'] in ('aberta', 'aguardando')]
        if not livres or len(abertas) >= 6:
            return
        n = forcar or (1 if r.random() < 0.35 + atr / 200 else 0) + (1 if r.random() < atr / 250 else 0)
        for _ in range(n):
            em_oferta = {o['slot'] for o in abertas}
            pool = [x for x in livres if x not in em_oferta] or livres
            pesos = [SLOTS[x]['valor_base'] for x in pool]
            slot = r.choices(pool, pesos)[0]
            cands = []
            for nome, e in self.s['empresas'].items():
                if any(o['empresa'] == nome for o in abertas) or any(
                        c['empresa'] == nome and c['status'] in ('assinado', 'ativo') for c in self.s['contratos']):
                    continue
                if e.get('bloqueio_ate') and s2d(e['bloqueio_ate']) > dia:
                    continue
                if e['setor'] in self.setores_ocupados():
                    continue
                if atr < PORTE_MIN_ATR[e['porte']]:
                    continue
                peso = {'grande': atr / 50, 'media': 1.0, 'pequena': max(0.3, (90 - atr) / 50)}[e['porte']]
                cands.append((nome, peso))
            if not cands:
                return
            nome = r.choices([c[0] for c in cands], [c[1] for c in cands])[0]
            valor = self.valor_justo(nome, slot, atr, r)
            anos = r.choice([1, 1, 2, 2, 3])
            validade = dia + dt.timedelta(days=r.randint(10, 21))
            inicio = dia + dt.timedelta(days=r.choice([0, 7, 14, 30]))
            pd, pm = PREF_CLAUSULAS[self.s['empresas'][nome]['personalidade']]
            cl = {'desempenho': pd if r.random() < 0.85 else not pd, 'multa_pct': pm}
            o = {'id': self._id(), 'empresa': nome, 'slot': slot, 'valor': valor, 'anos': anos,
                 'inicio': d2s(inicio), 'validade': d2s(validade), 'status': 'aberta', 'origem': 'empresa',
                 'criada': ds, 'rodadas': 0, 'clausulas': cl}
            self.s['ofertas'].append(o); abertas.append(o)
            self.msg('oferta', nome, ds, o['id'], posicao=pos_txt(slot), valor=fmt_eur(valor),
                     anos=anos_txt(anos), validade=fmt_data(validade))
            self._anexar_clausulas(cl)

    def _anexar_clausulas(self, cl):
        if self.s['mensagens']:
            self.s['mensagens'][-1]['texto'] += ' Condições: ' + clausulas_txt(cl) + '.'

    def _humor_patrocinadores(self, dia):
        ds = d2s(dia)
        f = self.forma(5)
        derrotas = f.count('D')
        if derrotas < 3:
            return
        r = random.Random(_seed('humor', ds))
        ativos = [c for c in self.s['contratos'] if c['status'] == 'ativo']
        for c in ativos:
            pers = self.s['empresas'].get(c['empresa'], {}).get('personalidade', 'paciente')
            if c.get('ameacado_em') and (dia - s2d(c['ameacado_em'])).days < 21:
                # já foi avisado: se continuar ruim, pode rescindir
                cl = c.get('clausulas', {'desempenho': True, 'multa_pct': 30})
                if derrotas >= 4 and pers in ('oportunista', 'agressiva'):
                    if cl.get('desempenho') and r.random() < 0.5:
                        self._encerrar(c, ds, 'empresa (cláusula de desempenho, sem multa)')
                        self.msg('rescisao', c['empresa'], ds, posicao=pos_txt(c['slot']))
                    elif not cl.get('desempenho') and r.random() < 0.15:
                        multa = self.multa_rescisao(c, dia)
                        self._encerrar(c, ds, 'empresa (pagou multa)')
                        if multa:
                            c['pagamentos'].append({'data': ds, 'valor': multa, 'status': 'pendente', 'tipo': 'multa'})
                        self.msg('rescisao_paga', c['empresa'], ds, posicao=pos_txt(c['slot']), valor=fmt_eur(multa))
                continue
            chance = {'oportunista': 0.7, 'agressiva': 0.5, 'paciente': 0.25, 'fiel': 0.1}[pers]
            if r.random() < chance:
                c['ameacado_em'] = ds
                self.msg('ameaca', c['empresa'], ds, posicao=pos_txt(c['slot']))

    def _encerrar(self, c, ds, por):
        c['status'] = 'rescindido'; c['fim'] = ds; c['rescindido_por'] = por
        for pg in c['pagamentos']:
            if pg['status'] == 'agendado':
                pg['status'] = 'cancelado'
        self.s['eventos'].append({'tipo': 'kits', 'data': ds})

    def multa_rescisao(self, c, dia=None):
        dia = dia or self.hoje()
        restante = max(0, (s2d(c['fim']) - dia).days) / 365 * c['valor']
        pct = (c.get('clausulas') or {}).get('multa_pct', 30) / 100
        return int(round(pct * restante / 50_000) * 50_000)

    def _corte_de_verba(self, dia):
        """De vez em quando uma empresa corta a verba e sai — paga multa ao clube."""
        ds = d2s(dia)
        r = random.Random(_seed('corte', ds))
        for c in self.contratos_ativos():
            if (dia - s2d(c['inicio'])).days < 60 or r.random() > 0.012:
                continue
            multa = self.multa_rescisao(c, dia)
            self._encerrar(c, ds, 'empresa (corte de verba)')
            if multa:
                c['pagamentos'].append({'data': ds, 'valor': multa, 'status': 'pendente', 'tipo': 'multa'})
            self.msg('rescisao_empresa', c['empresa'], ds, posicao=pos_txt(c['slot']), valor=fmt_eur(multa))

    def rescindir(self, contrato_id):
        """O clube rompe o contrato e paga a multa combinada (sobre o valor restante)."""
        c = next((x for x in self.s['contratos'] if x['id'] == int(contrato_id)), None)
        if not c or c['status'] not in ('ativo', 'assinado'):
            raise ValueError('Esse contrato não está ativo.')
        hoje = self.hoje(); ds = d2s(hoje)
        multa = self.multa_rescisao(c, hoje) if c['status'] == 'ativo' else \
            int(round((c.get('clausulas') or {}).get('multa_pct', 30) / 300 * c['valor'] / 50_000) * 50_000)
        self._encerrar(c, ds, 'clube')
        if multa:
            self.s['multas'].append({'id': self._id(), 'empresa': c['empresa'], 'valor': multa, 'data': ds,
                                     'status': 'pendente'})
        e = self.s['empresas'].get(c['empresa'])
        if e:
            e['bloqueio_ate'] = d2s(hoje + dt.timedelta(days=180))
        self.msg('rescisao_clube', c['empresa'], ds, posicao=pos_txt(c['slot']), valor=fmt_eur(multa))
        return multa

    # ---------- ações do usuário ----------
    def aceitar(self, oferta_id):
        o = self._oferta(oferta_id)
        if o['status'] != 'aberta':
            raise ValueError('Essa proposta não está mais aberta.')
        if o['slot'] not in self.slots_livres(self.hoje()):
            raise ValueError('Essa posição já está ocupada por outro contrato.')
        if self.s['empresas'][o['empresa']]['setor'] in self.setores_ocupados():
            raise ValueError('Já existe um patrocinador do mesmo setor (exclusividade).')
        o['status'] = 'aceita'
        hoje = self.hoje()
        inicio = max(s2d(o['inicio']), hoje)
        fim = inicio.replace(year=inicio.year + o['anos'])
        pags = [{'data': d2s(inicio.replace(year=inicio.year + i)), 'valor': o['valor'], 'status': 'agendado'}
                for i in range(o['anos'])]
        c = {'id': self._id(), 'empresa': o['empresa'], 'slot': o['slot'], 'valor': o['valor'], 'anos': o['anos'],
             'inicio': d2s(inicio), 'fim': d2s(fim), 'status': 'assinado', 'pagamentos': pags,
             'clausulas': dict(o.get('clausulas') or {'desempenho': False, 'multa_pct': 30}),
             'escala': 1.0, 'inclinacao': 0, 'cores': {'verde': 'auto', 'branco': 'auto', 'azul': 'auto', 'listrado': 'auto'}}
        self.s['contratos'].append(c)
        # outras ofertas para a mesma posição deixam de valer
        for x in self.s['ofertas']:
            if x is not o and x['slot'] == o['slot'] and x['status'] in ('aberta', 'aguardando'):
                x['status'] = 'cancelada'
        self.msg('boas_vindas', o['empresa'], d2s(hoje), posicao=pos_txt(o['slot']), valor=fmt_eur(o['valor']),
                 anos=anos_txt(o['anos']), inicio=fmt_data(inicio))
        self._dia_checar_inicio(c)
        return c

    def _dia_checar_inicio(self, c):
        hoje = self.hoje()
        if s2d(c['inicio']) <= hoje:
            c['status'] = 'ativo'
            for pg in c['pagamentos']:
                if s2d(pg['data']) <= hoje:
                    pg['status'] = 'pendente'
            self.s['eventos'].append({'tipo': 'kits', 'data': d2s(hoje)})

    def recusar(self, oferta_id):
        o = self._oferta(oferta_id)
        o['status'] = 'recusada'

    def pedir_mais(self, oferta_id, pct, clausulas=None, anos=None):
        o = self._oferta(oferta_id)
        if o['status'] != 'aberta':
            raise ValueError('Essa proposta não está mais aberta.')
        hoje = self.hoje()
        o['pedido'] = int(round(o['valor'] * (1 + pct / 100) / 50_000) * 50_000)
        o['clausulas_empresa'] = dict(o.get('clausulas') or {})
        if clausulas:
            o['clausulas_pedidas'] = {'desempenho': bool(clausulas.get('desempenho')),
                                      'multa_pct': int(clausulas.get('multa_pct', 30))}
        else:
            o['clausulas_pedidas'] = dict(o.get('clausulas') or {'desempenho': False, 'multa_pct': 30})
        if anos:
            o['anos_pedidos'] = int(anos)
        o['status'] = 'aguardando'
        o['rodadas'] += 1
        r = random.Random(_seed('resp', o['id'], o['rodadas']))
        o['resposta_em'] = d2s(hoje + dt.timedelta(days=r.randint(2, 7)))

    def procurar(self, empresa, slot, valor, anos, clausulas=None):
        hoje = self.hoje()
        if slot not in self.slots_livres(hoje):
            raise ValueError('Essa posição já está ocupada.')
        e = self.s['empresas'][empresa]
        if e.get('bloqueio_ate') and s2d(e['bloqueio_ate']) > hoje:
            raise ValueError(f'A {empresa} pediu um tempo antes de voltar a negociar.')
        if any(o['empresa'] == empresa and o['status'] in ('aberta', 'aguardando') for o in self.s['ofertas']):
            raise ValueError(f'Já existe uma negociação em andamento com a {empresa}.')
        r = random.Random(_seed('procura', empresa, d2s(hoje)))
        o = {'id': self._id(), 'empresa': empresa, 'slot': slot, 'valor': int(valor), 'pedido': int(valor),
             'anos': int(anos), 'inicio': d2s(hoje), 'validade': d2s(hoje + dt.timedelta(days=30)),
             'status': 'aguardando', 'origem': 'clube', 'criada': d2s(hoje), 'rodadas': 1,
             'resposta_em': d2s(hoje + dt.timedelta(days=r.randint(3, 8))),
             'clausulas_pedidas': {'desempenho': bool((clausulas or {}).get('desempenho', False)),
                                   'multa_pct': int((clausulas or {}).get('multa_pct', 30))}}
        self.s['ofertas'].append(o)
        return o

    def _oferta(self, oid):
        for o in self.s['ofertas']:
            if o['id'] == int(oid):
                return o
        raise ValueError('Proposta não encontrada.')

    def _responder(self, o, dia):
        ds = d2s(dia)
        e = self.s['empresas'][o['empresa']]
        pers = e['personalidade']
        atr = self.atratividade()
        justo = self.valor_justo(o['empresa'], o['slot'], atr)
        pedido = o['pedido']
        razao = pedido / justo
        # custo das cláusulas para a empresa
        pd, pm = PREF_CLAUSULAS[pers]
        cp = o.get('clausulas_pedidas') or o.get('clausulas') or {'desempenho': pd, 'multa_pct': pm}
        k = 0.5 if pers in ('agressiva', 'oportunista') else 0.2
        if pd and not cp['desempenho']:
            razao += 0.15 if pers in ('agressiva', 'oportunista') else 0.08
        elif not pd and cp['desempenho']:
            razao -= 0.03
        razao += (cp['multa_pct'] - pm) / 100 * k
        anos_ped = o.get('anos_pedidos', o['anos'])
        if anos_ped > o['anos'] and pers == 'oportunista':
            razao += 0.05
        r = random.Random(_seed('decide', o['id'], o['rodadas'], ds))
        tol = {'agressiva': 1.08, 'paciente': 1.18, 'fiel': 1.15, 'oportunista': 1.05}[pers]
        if atr < PORTE_MIN_ATR[e['porte']] or e['setor'] in self.setores_ocupados():
            p_aceita = 0.0
        else:
            p_aceita = max(0.0, min(0.95, 1.0 - (razao - 1.0) / (tol - 1.0 + 1e-6) * 0.6))
            if razao <= 1.0:
                p_aceita = 0.9
        v = dict(posicao=pos_txt(o['slot']), pedido=fmt_eur(pedido), anos=anos_txt(o['anos']))
        if o['origem'] == 'clube' and o['rodadas'] == 1:
            if r.random() < p_aceita:
                o['clausulas'] = dict(cp)
                o['valor'] = pedido; o['status'] = 'aberta'; o['validade'] = d2s(dia + dt.timedelta(days=14))
                self.msg('resposta_procura_sim', o['empresa'], ds, o['id'], valor=fmt_eur(pedido),
                         validade=fmt_data(dia + dt.timedelta(days=14)), **v)
                self._anexar_clausulas(o['clausulas'])
            else:
                o['status'] = 'recusada_empresa'
                e['bloqueio_ate'] = d2s(dia + dt.timedelta(days=45))
                self.msg('resposta_procura_nao', o['empresa'], ds, o['id'], valor=fmt_eur(pedido), **v)
            return
        x = r.random()
        if x < p_aceita:
            o['clausulas'] = dict(cp); o['anos'] = anos_ped
            o['valor'] = pedido; o['status'] = 'aberta'; o['validade'] = d2s(dia + dt.timedelta(days=10))
            self.msg('contraproposta_aceita', o['empresa'], ds, o['id'], valor=fmt_eur(pedido),
                     validade=fmt_data(dia + dt.timedelta(days=10)), **v)
            self._anexar_clausulas(o['clausulas'])
        elif x < p_aceita + 0.55 and o['rodadas'] < 3:
            novo = int(round((o['valor'] + (pedido - o['valor']) * r.uniform(0.3, 0.6)) / 50_000) * 50_000)
            o['valor'] = max(novo, o['valor']); o['status'] = 'aberta'
            o['validade'] = d2s(dia + dt.timedelta(days=10))
            # nas cláusulas, a empresa cede em algumas e volta à preferência dela em outras
            o['clausulas'] = {'desempenho': cp['desempenho'] if r.random() < 0.5 else pd,
                              'multa_pct': cp['multa_pct'] if r.random() < 0.5 else int(round((cp['multa_pct'] + pm) / 20) * 10)}
            if o['clausulas']['multa_pct'] not in MULTAS:
                o['clausulas']['multa_pct'] = min(MULTAS, key=lambda m: abs(m - o['clausulas']['multa_pct']))
            o['anos'] = anos_ped if r.random() < 0.6 else o['anos']
            self.msg('contraproposta_meio', o['empresa'], ds, o['id'], valor=fmt_eur(o['valor']),
                     validade=fmt_data(dia + dt.timedelta(days=10)), **v)
            self._anexar_clausulas(o['clausulas'])
        else:
            o['status'] = 'recusada_empresa'
            e['bloqueio_ate'] = d2s(dia + dt.timedelta(days=45))
            self.msg('contraproposta_recusada', o['empresa'], ds, o['id'], **v)

    # ---------- dinheiro ----------
    def pagamentos_pendentes(self):
        out = []
        for c in self.s['contratos']:
            for pg in c['pagamentos']:
                if pg['status'] == 'pendente':
                    out.append((c, pg))
        return out

    def contratos_ativos(self):
        return [c for c in self.s['contratos'] if c['status'] == 'ativo']
