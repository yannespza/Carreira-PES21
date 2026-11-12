"""Presidente do clube: cuida dos patrocínios sozinho.

A cada leitura do save ele olha as propostas abertas, escolhe a melhor de cada espaço da camisa, aceita,
negocia (pede mais) ou deixa passar, e procura empresas para espaços vazios. Sem veto do técnico.
Cada contrato fechado vira nota na imprensa explicando por que o presidente escolheu a marca e por que a
empresa quis o clube. O técnico continua controlando como a marca aparece no uniforme (aba Uniformes).
"""
import datetime as dt
import random

from .sim import d2s, s2d, _seed, fmt_eur, pos_txt, SLOTS
from .vozes import L, Memoria, fmt

# quanto da "proposta justa" cada perfil aceita sem negociar, e quanto pede a mais
REGUA = {'apaixonado': (0.9, 15), 'empresario': (1.02, 25), 'politico': (0.95, 15), 'conservador': (0.92, 10)}
VAZIO_DIAS = 21          # espaço vazio sem proposta: o presidente vai atrás

MOTIVO_PRES = {
    'apaixonado': L("""É uma marca que combina com a grandeza do {clube} e com a nossa torcida.|
Conversei pessoalmente com a {empresa} e senti que eles vestem a camisa de verdade.|
Quero o {clube} ao lado de marcas fortes, e a {empresa} é isso."""),
    'empresario': L("""Foi a melhor proposta da mesa: {valor} por temporada, {anos}.|
Comparamos números, prazo e solidez. A {empresa} ganhou em todos os critérios.|
O valor está acima da média do mercado para o espaço, e isso pesou."""),
    'politico': L("""Ouvimos o conselho e o departamento de marketing. A {empresa} foi consenso.|
É um acordo bom para todos: clube, torcida e parceiro.|
Uma marca respeitada, sem polêmica, que agrega ao {clube}."""),
    'conservador': L("""Preferimos segurança: contrato de {anos}, com uma empresa sólida.|
Não fomos atrás do maior número, e sim do parceiro mais confiável.|
É um contrato que dá previsibilidade ao caixa, e é disso que o {clube} precisa."""),
}
MOTIVO_EMP = {
    'torcida': L("""A empresa destacou o tamanho e o engajamento da torcida do {clube}.|
Segundo a {empresa}, a exposição para a torcida do {clube} foi decisiva."""),
    'momento': L("""O bom momento do time em campo pesou na decisão da {empresa}.|
A {empresa} quis associar a marca a um time em ascensão."""),
    'regiao': L("""A {empresa} quer crescer na região e viu no {clube} a vitrine ideal.|
Para a {empresa}, o {clube} abre portas num mercado onde ela quer crescer."""),
    'custo': L("""A {empresa} encontrou no {clube} um espaço de bom custo-benefício.|
Para a {empresa}, o valor cabe no orçamento e a visibilidade compensa."""),
}
TITULO = L("""{clube} anuncia a {empresa} no {pos}: {valor} por temporada|
Presidência do {clube} fecha com a {empresa} para o {pos}|
{empresa} chega ao {pos} do {clube}; acordo de {anos}|
{presidente} acerta com a {empresa}: {valor} por ano no {pos}""")


class Presidente:
    def __init__(self, state, engine, clube, pessoas):
        self.s = state
        self.e = engine
        self.clube = clube
        self.p = pessoas
        self.perfil = pessoas['presidente']['perfil']
        self.d = state.setdefault('presidente', {'log': []})
        self.d.setdefault('log', [])
        self.mem = Memoria(state)

    def _assina(self):
        from .dirigentes import assinatura
        return assinatura('presidente', self.p, self.clube)

    def _registrar(self, ds, txt):
        self.d['log'].append({'data': ds, 'texto': txt})
        self.d['log'] = self.d['log'][-40:]

    def _score(self, o, justo):
        e = self.s['empresas'].get(o['empresa'], {})
        razao = o['valor'] / max(1, justo)
        bonus = {'grande': 0.06, 'media': 0.0, 'pequena': -0.05}.get(e.get('porte'), 0)
        if self.perfil == 'conservador':
            bonus += 0.04 * (o.get('anos', 1) - 1)
        if self.perfil == 'apaixonado':
            bonus += 0.04 if e.get('porte') == 'grande' else 0
        return razao + bonus

    def processar(self):
        eng = self.e
        hoje = eng.hoje() if eng else None
        if not hoje:
            return
        ds = d2s(hoje)
        if self.d.get('ult') == ds:
            return
        self.d['ult'] = ds
        atr = eng.atratividade()
        regua, pede = REGUA[self.perfil]
        # propostas criadas antes do ajuste pelo porte do clube: valor corrigido uma única vez
        f = eng.fator_clube()
        for o in self.s['ofertas']:
            if o['status'] in ('aberta', 'aguardando') and not o.get('porte_ok'):
                o['porte_ok'] = True
                if f < 0.97:
                    o['valor'] = max(50_000, int(o['valor'] * f / 50_000) * 50_000)
                    if o.get('pedido'):
                        o['pedido'] = max(50_000, int(o['pedido'] * f / 50_000) * 50_000)
        abertas = [o for o in self.s['ofertas'] if o['status'] == 'aberta' and o['slot'] in SLOTS
                   and o['empresa'] in self.s['empresas']]
        por_slot = {}
        for o in abertas:
            por_slot.setdefault(o['slot'], []).append(o)
        for slot, ofs in por_slot.items():
            ocupados = eng.setores_ocupados(slot)
            livres_ofs = []
            for o in ofs:
                setor = self.s['empresas'].get(o['empresa'], {}).get('setor')
                if setor in ocupados and not o.get('substitui'):
                    eng.recusar(o['id'])
                    self._registrar(ds, f"Dispensou a {o['empresa']}: o clube já tem patrocinador do mesmo setor.")
                else:
                    livres_ofs.append(o)
            ofs = livres_ofs
            if not ofs:
                continue
            justos = {o['id']: eng.valor_justo(o['empresa'], slot, atr) for o in ofs}
            ofs.sort(key=lambda o: self._score(o, justos[o['id']]), reverse=True)
            best = ofs[0]
            sc = self._score(best, justos[best['id']])
            dias = (s2d(best['validade']) - hoje).days
            troca = best.get('substitui')
            if troca:
                atual = next((c for c in self.s['contratos'] if c['id'] == troca), None)
                if atual and best['valor'] < atual['valor'] * 1.2:
                    eng.recusar(best['id'])
                    self._registrar(ds, f"Recusou a {best['empresa']}: não vale trocar a {atual['empresa']} por esse valor.")
                    continue
            r = random.Random(_seed('pres', best['id'], best.get('rodadas', 0), ds))
            if sc >= regua or (dias <= 3 and sc >= regua - 0.12) or best.get('rodadas', 0) >= 2:
                self._fechar(best, justos[best['id']], atr, ds, r)
            elif best.get('rodadas', 0) < 2:
                pct = pede if sc < regua - 0.1 else max(5, pede // 2)
                try:
                    eng.pedir_mais(best['id'], pct)
                    self._registrar(ds, f"Pediu {pct}% a mais à {best['empresa']} pelo {pos_txt(slot)}.")
                except ValueError:
                    pass
        self._procurar(hoje, atr)

    def _fechar(self, o, justo, atr, ds, r):
        eng = self.e
        try:
            c = eng.aceitar(o['id'])
        except ValueError as ex:
            self._registrar(ds, f"Não fechou com a {o['empresa']}: {ex}")
            return
        e = self.s['empresas'].get(o['empresa'], {})
        anos = f"{c['anos']} temporada" + ('s' if c['anos'] > 1 else '')
        pres = self.p['presidente'].get('nome') or 'O presidente'
        v = {'clube': self.clube, 'empresa': o['empresa'], 'valor': fmt_eur(c['valor']), 'anos': anos,
             'pos': pos_txt(c['slot']), 'presidente': pres}
        motivo_p = self.mem.escolher('pres:mot:' + self.perfil, MOTIVO_PRES[self.perfil], r, v)
        torc = (self.s.get('mundo') or {}).get('torcida', 50)
        forma = ''.join(p['res'] for p in self.s.get('partidas', [])[-5:])
        if forma.count('V') >= 3:
            chave = 'momento'
        elif torc >= 65 or (self.s.get('atr_base') or 50) >= 72:
            chave = 'torcida'
        elif e.get('porte') == 'grande' and (self.s.get('atr_base') or 50) < 60:
            chave = 'custo'
        else:
            chave = r.choice(['regiao', 'torcida', 'custo'])
        motivo_e = self.mem.escolher('pres:emp:' + chave, MOTIVO_EMP[chave], r, v)
        neg = ('A negociação teve contraproposta do clube até chegar ao valor final.' if o.get('rodadas') else
               'O acordo saiu na primeira rodada de conversa.')
        corpo = [f"O {self.clube} oficializou a {o['empresa']} como patrocinadora do {pos_txt(c['slot'])} por "
                 f"{fmt_eur(c['valor'])} por temporada, num contrato de {anos}. {neg}",
                 f"\"{motivo_p}\", explicou {pres}.", motivo_e]
        titulo = self.mem.escolher('pres:tit', TITULO, r, v)
        self.s['mundo']['noticias'].append({'data': ds, 'tipo': 'contrato', 'titulo': titulo, 'empresa': o['empresa'],
                                            'fonte': r.choice(['Globo Esporte', 'Lance!', 'Máquina do Esporte', 'ESPN']),
                                            'destaque': SLOTS.get(c['slot'], {}).get('valor_base', 0) >= 2_500_000,
                                            'corpo': corpo, 'presidente': True})
        self.e.s['mensagens'].append({'id': self.e._id(), 'data': ds, 'empresa': '__diretoria__', 'de': self._assina(),
                                      'assunto': f"Novo patrocínio: {o['empresa']}", 'tipo': 'diretoria', 'oferta_id': None,
                                      'lida': False,
                                      'texto': f"Professor, fechamos com a {o['empresa']} no {pos_txt(c['slot'])}: "
                                               f"{fmt_eur(c['valor'])} por temporada, {anos}. {motivo_p} "
                                               "O visual da marca na camisa fica com você na aba Uniformes."})
        self.s.setdefault('marcas_novas', []).append({'contrato': c['id'], 'empresa': o['empresa'], 'slot': c['slot'], 'data': ds})
        self._registrar(ds, f"Fechou com a {o['empresa']} ({pos_txt(c['slot'])}, {fmt_eur(c['valor'])}/temporada).")

    def _procurar(self, hoje, atr):
        """Espaço vazio há um tempo e sem proposta: o presidente vai ao mercado."""
        eng = self.e
        u = self.d.get('ult_procura')
        if u and (hoje - s2d(u)).days < 7:
            return
        livres = eng.slots_livres(hoje)
        em_neg = {o['slot'] for o in self.s['ofertas'] if o['status'] in ('aberta', 'aguardando')}
        alvo = [x for x in livres if x not in em_neg]
        if not alvo:
            return
        vazio_desde = self.d.setdefault('vazio_desde', {})
        for x in list(vazio_desde):
            if x not in alvo:
                vazio_desde.pop(x)
        for x in alvo:
            vazio_desde.setdefault(x, d2s(hoje))
        prontos = [x for x in alvo if (hoje - s2d(vazio_desde[x])).days >= VAZIO_DIAS]
        if not prontos:
            return
        self.d['ult_procura'] = d2s(hoje)
        slot = max(prontos, key=lambda x: SLOTS.get(x, {}).get('valor_base', 0))
        from .sim import PORTE_MIN_ATR
        r = random.Random(_seed('procura_pres', d2s(hoje), slot))
        cands = []
        for nome, e in self.s['empresas'].items():
            if not eng.elegivel(nome) or e['setor'] in eng.setores_ocupados(slot):
                continue
            if e.get('bloqueio_ate') and s2d(e['bloqueio_ate']) > hoje:
                continue
            if any(o['empresa'] == nome and o['status'] in ('aberta', 'aguardando') for o in self.s['ofertas']):
                continue
            if any(c['empresa'] == nome and c['status'] in ('ativo', 'assinado') for c in self.s['contratos']):
                continue
            if atr < PORTE_MIN_ATR[e['porte']] - 5:
                continue
            cands.append(nome)
        if not cands:
            return
        nome = r.choice(cands)
        valor = int(eng.valor_justo(nome, slot, atr) * r.uniform(0.95, 1.1) / 50_000) * 50_000 or 50_000
        anos = 3 if self.perfil == 'conservador' else r.choice([1, 2, 2, 3])
        try:
            eng.procurar(nome, slot, valor, anos)
            self._registrar(d2s(hoje), f"Procurou a {nome} para o {pos_txt(slot)} ({fmt_eur(valor)}/temporada).")
        except ValueError:
            pass

    def view(self):
        return {'nome': self.p['presidente'].get('nome'), 'perfil': self.perfil,
                'perfil_txt': self.p['presidente']['perfil_txt'], 'log': self.d['log'][-12:][::-1]}
