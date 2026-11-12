"""Diretor de futebol: cuida do dinheiro do futebol (transferências e salários).

O técnico pede:
- mover dinheiro entre transferências e salários; ou
- verba extra para contratações.
O diretor responde na hora, conforme o porte do clube, o caixa, a confiança da diretoria, o prestígio do técnico
e a personalidade dele: aceita, faz contraproposta (valor e/ou exigência com prazo) ou recusa.
Toda verba vem com um compromisso. Cumprido, a confiança sobe. Não cumprido, vem a punição combinada:
tirar parte da verba, mandar dinheiro para outro setor, congelar novos pedidos ou, no limite, a demissão.
Técnico muito vencedor nunca é demitido por isso: perde verba. Técnico novo não recebe exigência de título.
"""
import datetime as dt
import random

from .sim import d2s, s2d, _seed, fmt_eur
from .vozes import L, Memoria, fmt

ESPERA_APORTE = 45          # dias entre pedidos de verba extra
ESPERA_RECUSA = 21          # depois de uma recusa
ESPERA_MOVER = 14           # entre remanejamentos


def _st(state):
    d = state.setdefault('diretor', {})
    d.setdefault('pedidos', [])
    d.setdefault('compromissos', [])
    d.setdefault('seq', 0)
    return d


def _temporada(dia):
    return dia.year if dia.month >= 6 else dia.year - 1


def capacidade(state):
    """Quanto o clube consegue tirar do caixa para o futebol numa temporada (verba extra), em euros."""
    from . import ranking
    c = ranking.CLUBES.get(state.get('time_id'))
    if c:
        base = c[3] * 1e6 * 0.12 + c[4] * 25_000
    else:
        base = (state.get('atr_base', 55) ** 2) * 1_200
    din = state.get('dinheiro') or {}
    rec = (din.get('rec_patrocinio') or 0) + (din.get('rec_socios') or 0)
    base += rec * 0.05
    return int(max(300_000, round(base / 50_000) * 50_000))


def _vencedor(state):
    """Prestígio e títulos do técnico na carreira."""
    p = state.get('prestigio_tecnico') or 50
    tits = sum(len(t.get('titulos') or []) for t in (state.get('gestao') or {}).get('temporadas', []))
    return p, tits


def _perfil_tecnico(state):
    p, tits = _vencedor(state)
    if p >= 80 or tits >= 3:
        return 'vencedor'
    if p < 45 or len(state.get('partidas', [])) < 25:
        return 'novo'
    return 'medio'


def _meta(state, engine, hoje):
    from .diretoria import metas_da_temporada
    try:
        return metas_da_temporada(state, engine, hoje)
    except Exception:
        return None


def _pos_atual(state):
    linhas = (state.get('tabela') or {}).get('linhas') or []
    meu = next((l for l in linhas if l['id'] == state.get('time_id')), None)
    return (meu['pos'], len(linhas)) if meu and meu.get('j') else (None, len(linhas) or 20)


# ---------------- exigências ----------------
def _exigencia(state, engine, hoje, peso, r, tipo):
    """Monta a exigência conforme o tamanho do pedido (peso 0..1+), o técnico e o clube."""
    perfil = _perfil_tecnico(state)
    meta = _meta(state, engine, hoje) or {}
    liga = meta.get('liga') or {}
    alvo = liga.get('alvo') or 10
    div = liga.get('div', 'A')
    pos, n = _pos_atual(state)
    temp = _temporada(hoje)
    grande = (state.get('atr_base') or 55) >= 74
    njogos = len(state.get('partidas', []))
    if peso < 0.3 or tipo == 'mover':
        if r.random() < 0.5:
            jogos = r.choice([5, 6, 8])
            pts = int(round(jogos * 3 * (0.5 if perfil == 'novo' else 0.55 if perfil == 'medio' else 0.6)))
            return {'tipo': 'pontos', 'jogos': jogos, 'pontos': pts, 'base': njogos,
                    'texto': f'somar pelo menos {pts} pontos nos próximos {jogos} jogos'}
        jogos = r.choice([4, 5])
        return {'tipo': 'invicto', 'jogos': jogos, 'base': njogos,
                'texto': f'não perder nenhum dos próximos {jogos} jogos'}
    if peso < 0.75:
        if div == 'B':
            a = 4 if perfil != 'novo' or alvo <= 4 else max(4, alvo)
            return {'tipo': 'posicao', 'alvo': a, 'temporada': temp,
                    'texto': 'conquistar o acesso (terminar entre os 4 primeiros)' if a == 4 else f'terminar até o {a}º lugar'}
        a = alvo if perfil == 'novo' else max(1, alvo - (2 if perfil == 'vencedor' else 1))
        return {'tipo': 'posicao', 'alvo': a, 'temporada': temp, 'texto': f'terminar a temporada até o {a}º lugar'}
    # pedido grande
    if div == 'B':
        return {'tipo': 'posicao', 'alvo': 2 if perfil != 'novo' else 4, 'temporada': temp,
                'texto': 'subir como um dos 2 primeiros da Série B' if perfil != 'novo' else 'conquistar o acesso'}
    if grande and perfil != 'novo':
        return {'tipo': 'posicao', 'alvo': 1, 'temporada': temp, 'texto': 'ganhar o campeonato'}
    if perfil == 'novo':
        a = max(1, min(alvo, 6))
        return {'tipo': 'posicao', 'alvo': a, 'temporada': temp, 'texto': f'classificar o time até o {a}º lugar'}
    return {'tipo': 'posicao', 'alvo': max(1, min(alvo - 2, 4)), 'temporada': temp,
            'texto': f'terminar no G{max(1, min(alvo - 2, 4))} do campeonato'}


def _punicao(state, peso, valor, r, conf):
    perfil = _perfil_tecnico(state)
    if perfil == 'vencedor':
        if r.random() < 0.5:
            return {'tipo': 'retirar', 'valor': int(valor * r.choice([0.4, 0.5, 0.6]) / 50_000) * 50_000,
                    'texto': 'parte da verba volta para o caixa do clube'}
        return {'tipo': 'realocar', 'valor': int(valor * 0.5 / 50_000) * 50_000,
                'destino': r.choice(['as categorias de base', 'a reforma do CT', 'o pagamento de dívidas']),
                'texto': 'metade da verba vai para outro setor do clube'}
    if peso >= 0.75 and (perfil == 'novo' or conf < 60):
        return {'tipo': 'demissao', 'texto': 'o seu cargo fica em jogo (pode ser demitido)'}
    if peso >= 0.5:
        return {'tipo': 'retirar', 'valor': int(valor * 0.6 / 50_000) * 50_000,
                'texto': 'a maior parte da verba é retirada e a confiança da diretoria cai'}
    return r.choice([
        {'tipo': 'congelar', 'dias': 90, 'texto': 'nenhum pedido novo de verba por 90 dias'},
        {'tipo': 'confianca', 'texto': 'a confiança da diretoria no seu trabalho cai'}])


# ---------------- textos ----------------
TXT = {
    'aceita': {
        'exigente': L("""Fechado, professor. O dinheiro sai, mas eu vou cobrar: {exig}.|
Liberado. Agora é resultado: {exig}. Combinado é combinado.|
Pode contar com a verba. Em troca, quero ver {exig}."""),
        'paciente': L("""Pode contar com isso, professor. Só peço {exig}. Sei que dá.|
Liberado. Confio no trabalho; o combinado é {exig}.|
Tudo certo. Vamos juntos: {exig} e seguimos crescendo."""),
        'calculista': L("""Fiz as contas e fecha. A condição é {exig}.|
Cabe no orçamento. Mas o investimento precisa de retorno: {exig}.|
Aprovado pelo financeiro, com uma condição: {exig}."""),
        'ousado': L("""Gosto de quem pede alto. Vai lá: {exig}.|
É aposta, e eu gosto de aposta. Só não me deixa na mão: {exig}.|
Liberado! Agora quero ver {exig}."""),
    },
    'contra': {
        'exigente': L("""Isso tudo não sai, professor. Consigo {valor}, e com uma condição: {exig}.|
O pedido é alto demais. Minha proposta: {valor}, desde que você se comprometa a {exig}."""),
        'paciente': L("""Não consigo tudo agora. Posso liberar {valor}, e o combinado seria {exig}. O que acha?|
Vamos devagar: {valor} agora, com o compromisso de {exig}."""),
        'calculista': L("""Pelos números, o máximo é {valor}. E preciso de garantia: {exig}.|
O caixa aguenta {valor}. Fecho se você assumir {exig}."""),
        'ousado': L("""Te dou {valor}, mas aí a régua sobe: {exig}. Topa?|
{valor} na mesa. Em troca, quero {exig}. Sem meio-termo."""),
    },
    'recusa': {
        'exigente': L("""Não, professor. Primeiro resultado, depois dinheiro.|
Negado. Com o time desse jeito, não tem conversa sobre verba."""),
        'paciente': L("""Agora não dá, professor. Vamos esperar o caixa respirar e conversamos de novo.|
Entendo o pedido, mas neste momento não consigo. Daqui a umas semanas a gente volta a falar."""),
        'calculista': L("""Os números não fecham. Não tenho de onde tirar esse valor.|
Fiz as contas três vezes. Não dá."""),
        'ousado': L("""Até eu acho exagero, professor. Pede de novo com um número que faça sentido.|
Esse não. Traz um pedido realista que eu banco."""),
    },
    'cumprido': L("""Professor, compromisso cumprido: {exig}. A diretoria reconhece o trabalho.|
Combinado é combinado, e você entregou: {exig}. Parabéns.|
Missão cumprida ({exig}). Isso conta muito na próxima conversa sobre verba."""),
    'falhou': L("""Professor, o combinado era {exig} e não aconteceu. Como acertamos: {pun}.|
Não deu: {exig} ficou pelo caminho. Vou cumprir o que combinamos: {pun}.|
Infelizmente o compromisso ({exig}) não foi cumprido. A consequência, como combinado: {pun}."""),
}
ASSUNTO = {'aceita': 'Verba liberada', 'contra': 'Contraproposta da diretoria de futebol',
           'recusa': 'Pedido de verba negado', 'cumprido': 'Compromisso cumprido', 'falhou': 'Compromisso não cumprido',
           'mover': 'Remanejamento do orçamento'}


class Diretor:
    def __init__(self, state, engine, clube, pessoas):
        self.s = state
        self.e = engine
        self.clube = clube
        self.p = pessoas            # saída de dirigentes.de()
        self.d = _st(state)
        self.perfil = pessoas['diretor']['perfil']
        self.mem = Memoria(state)

    def _assina(self):
        from .dirigentes import assinatura
        return assinatura('diretor', self.p, self.clube)

    def _msg(self, assunto, texto, data=None):
        if self.e is None:
            return
        self.e.s['mensagens'].append({'id': self.e._id(), 'data': data or self.s.get('data'), 'empresa': '__diretoria__',
                                      'de': self._assina(), 'assunto': assunto, 'texto': texto, 'tipo': 'diretoria',
                                      'oferta_id': None, 'lida': False})

    def _id(self):
        self.d['seq'] += 1
        return self.d['seq']

    def _conf(self):
        return (self.s.get('mundo') or {}).get('diretoria', 60)

    def espera(self, tipo):
        """Dias que faltam para poder pedir de novo (0 = pode)."""
        hoje = s2d(self.s['data']) if self.s.get('data') else None
        if not hoje:
            return 0
        bloq = self.d.get('bloqueio_ate')
        if bloq and s2d(bloq) > hoje:
            return (s2d(bloq) - hoje).days
        ult = [p for p in self.d['pedidos'] if (p['tipo'] == 'mover') == (tipo == 'mover')
               and p['status'] in ('aceito', 'recusado', 'contra_recusada')]
        if not ult:
            return 0
        u = ult[-1]
        gap = ESPERA_RECUSA if u['status'] in ('recusado', 'contra_recusada') else (ESPERA_MOVER if tipo == 'mover' else ESPERA_APORTE)
        falta = gap - (hoje - s2d(u['data'])).days
        return max(0, falta)

    def em_aberto(self):
        return next((p for p in self.d['pedidos'] if p['status'] == 'contra'), None)

    def pedir(self, tipo, valor):
        """tipo 'mover' (valor > 0: transferências → salários; < 0: salários → transferências) ou 'aporte'."""
        if tipo not in ('mover', 'aporte'):
            raise ValueError('Tipo de pedido inválido.')
        valor = int(valor)
        if not valor or (tipo == 'aporte' and valor <= 0):
            raise ValueError('Informe um valor.')
        if self.em_aberto():
            raise ValueError('Há uma contraproposta do diretor esperando a sua resposta.')
        falta = self.espera(tipo)
        if falta:
            raise ValueError(f'O diretor pediu um tempo: dá para conversar de novo em {falta} dias da carreira.')
        if tipo == 'aporte' and any(c['status'] == 'ativo' for c in self.d['compromissos'] if c.get('origem') == 'aporte'):
            raise ValueError('Você ainda tem um compromisso em aberto com a diretoria. Cumpra antes de pedir mais verba.')
        hoje = s2d(self.s['data'])
        ds = d2s(hoje)
        r = random.Random(_seed('dirpedido', ds, tipo, valor, self.d['seq']))
        din = self.s.get('dinheiro') or {}
        conf = self._conf()
        cap = capacidade(self.s)
        if tipo == 'mover':
            t0, s0 = din.get('orc_transf') or 0, din.get('orc_salario') or 0
            if valor > 0 and valor > t0:
                raise ValueError('Não há tanto dinheiro de transferências.')
            if valor < 0 and -valor > max(s0, 0):
                raise ValueError('Não há tanto saldo de salários.')
        pid = self._id()
        p = {'id': pid, 'data': ds, 'tipo': tipo, 'valor': valor, 'status': None}
        self.d['pedidos'].append(p)
        self.d['pedidos'] = self.d['pedidos'][-40:]
        perfil = self.perfil
        if tipo == 'mover':
            t, sal = din.get('orc_transf') or 0, din.get('orc_salario') or 0
            base = max(1, t + max(sal, 0))
            peso = abs(valor) / base
            # salário é gasto que se repete: aumentar a folha é o que mais pesa
            if valor > 0:
                peso *= {'calculista': 1.6, 'exigente': 1.3, 'paciente': 1.0, 'ousado': 0.8}[perfil]
            else:
                peso *= 0.5
            if peso < 0.18 or (peso < 0.3 and conf >= 65):
                p['status'] = 'aceito'
                p['resposta'] = 'Remanejamento aprovado sem condição.'
                self._msg(ASSUNTO['mover'], f"Professor, aprovado o remanejamento de {fmt_eur(abs(valor))} "
                          f"({'das transferências para os salários' if valor > 0 else 'dos salários para as transferências'}).")
                return p
            if peso > 0.7 and conf < 50:
                return self._recusa(p, r)
            ex = _exigencia(self.s, self.e, hoje, 0.2, r, 'mover')
            pun = {'tipo': 'confianca', 'texto': 'a confiança da diretoria no seu trabalho cai'}
            return self._contra(p, valor, ex, pun, r, mover=True)
        # verba extra
        peso = valor / cap
        peso *= {'exigente': 1.1, 'calculista': 1.25, 'paciente': 1.0, 'ousado': 0.8}[perfil]
        if conf < 30 or peso > 2.2 or (peso > 1.4 and perfil == 'calculista'):
            return self._recusa(p, r)
        if peso <= 0.35 and conf >= 55:
            ex = _exigencia(self.s, self.e, hoje, peso, r, 'aporte')
            pun = _punicao(self.s, peso, valor, r, conf)
            return self._aceita(p, valor, ex, pun, r)
        oferta = valor if peso <= 0.8 else int(min(valor, cap * r.uniform(0.6, 0.9)) / 50_000) * 50_000
        ex = _exigencia(self.s, self.e, hoje, oferta / cap, r, 'aporte')
        pun = _punicao(self.s, oferta / cap, oferta, r, conf)
        return self._contra(p, oferta, ex, pun, r)

    def _recusa(self, p, r):
        p['status'] = 'recusado'
        txt = self.mem.escolher(f'dir:recusa:{self.perfil}', TXT['recusa'][self.perfil], r)
        p['resposta'] = txt
        self._msg(ASSUNTO['recusa'], txt, p['data'])
        return p

    def _aceita(self, p, valor, ex, pun, r):
        p['status'] = 'aceito'
        p['acordo'] = {'valor': valor, 'exigencia': ex, 'punicao': pun}
        txt = self.mem.escolher(f'dir:aceita:{self.perfil}', TXT['aceita'][self.perfil], r, {'exig': ex['texto']})
        txt += f" Se não acontecer: {pun['texto']}."
        p['resposta'] = txt
        self._msg(ASSUNTO['aceita'], txt, p['data'])
        self._compromisso(p, valor, ex, pun)
        return p

    def _contra(self, p, valor, ex, pun, r, mover=False):
        p['status'] = 'contra'
        p['acordo'] = {'valor': valor, 'exigencia': ex, 'punicao': pun}
        v = fmt_eur(abs(valor))
        txt = self.mem.escolher(f'dir:contra:{self.perfil}', TXT['contra'][self.perfil], r, {'exig': ex['texto'], 'valor': v})
        if mover:
            txt = (f"Posso fazer o remanejamento de {v}, mas preciso de uma resposta em campo: {ex['texto']}.")
        txt += f" Se não acontecer: {pun['texto']}."
        p['resposta'] = txt
        self._msg(ASSUNTO['contra'], txt, p['data'])
        return p

    def responder(self, aceitar):
        p = self.em_aberto()
        if not p:
            raise ValueError('Não há contraproposta em aberto.')
        if not aceitar:
            p['status'] = 'contra_recusada'
            return p
        p['status'] = 'aceito'
        a = p['acordo']
        self._compromisso(p, a['valor'], a['exigencia'], a['punicao'])
        return p

    def _compromisso(self, p, valor, ex, pun):
        self.d['compromissos'].append({'id': p['id'], 'data': p['data'], 'origem': p['tipo'], 'valor': valor,
                                       'exigencia': ex, 'punicao': pun, 'status': 'ativo'})

    # ---------- acompanhamento ----------
    def processar(self, mundo, hoje, nomes=None):
        """A cada save lido: confere os compromissos em andamento."""
        if not hoje:
            return []
        ds = d2s(hoje)
        ps = self.s.get('partidas', [])
        temps = {t['ano']: t for t in (self.s.get('gestao') or {}).get('temporadas', [])}
        feitos = []
        for c in self.d['compromissos']:
            if c['status'] != 'ativo':
                continue
            ex = c['exigencia']
            ok = None
            if ex['tipo'] in ('pontos', 'invicto'):
                jogos = ps[ex['base']:ex['base'] + ex['jogos']]
                if ex['tipo'] == 'invicto' and any(j['res'] == 'D' for j in jogos):
                    ok = False
                elif len(jogos) >= ex['jogos']:
                    pts = sum({'V': 3, 'E': 1, 'D': 0}[j['res']] for j in jogos)
                    ok = True if ex['tipo'] == 'invicto' else pts >= ex['pontos']
            elif ex['tipo'] == 'posicao':
                t = temps.get(ex['temporada'])
                if t and t.get('pos'):
                    ok = t['pos'] <= ex['alvo']
            if ok is None:
                continue
            c['status'] = 'cumprido' if ok else 'falhou'
            c['resolvido'] = ds
            r = random.Random(_seed('dircomp', c['id'], ds))
            if ok:
                mundo.m['diretoria'] = min(100, mundo.m.get('diretoria', 60) + 6)
                self._msg(ASSUNTO['cumprido'], self.mem.escolher('dir:cumprido', TXT['cumprido'], r, {'exig': ex['texto']}), ds)
            else:
                self._punir(c, mundo, hoje, r, nomes)
            feitos.append(c)
        return feitos

    def _punir(self, c, mundo, hoje, r, nomes):
        ds = d2s(hoje)
        pun = c['punicao']
        ex = c['exigencia']
        txt_pun = pun['texto']
        if pun['tipo'] in ('retirar', 'realocar') and pun.get('valor'):
            orc = (self.s.get('dinheiro') or {}).get('orc_transf') or 0
            v = int(min(pun['valor'], max(0, orc)) / 50_000) * 50_000
            if v > 0:
                motivo = (f"diretoria retirou verba ({ex['texto']} não cumprido)" if pun['tipo'] == 'retirar' else
                          f"diretoria mandou verba para {pun.get('destino', 'outro setor')}")
                self.s.setdefault('debitos', []).append({'data': ds, 'valor': v, 'motivo': motivo, 'status': 'pendente',
                                                         'origem': 'diretor'})
                txt_pun = (f"vou tirar {fmt_eur(v)} do orçamento de transferências" if pun['tipo'] == 'retirar' else
                           f"{fmt_eur(v)} saem das transferências para {pun.get('destino', 'outro setor')}")
            mundo.m['diretoria'] = max(0, mundo.m.get('diretoria', 60) - 6)
        elif pun['tipo'] == 'congelar':
            self.d['bloqueio_ate'] = d2s(hoje + dt.timedelta(days=pun.get('dias', 90)))
            mundo.m['diretoria'] = max(0, mundo.m.get('diretoria', 60) - 4)
        elif pun['tipo'] == 'confianca':
            mundo.m['diretoria'] = max(0, mundo.m.get('diretoria', 60) - 12)
        self._msg(ASSUNTO['falhou'], self.mem.escolher('dir:falhou', TXT['falhou'], r,
                                                       {'exig': ex['texto'], 'pun': txt_pun}), ds)
        if pun['tipo'] == 'demissao':
            from . import diretoria
            e = diretoria._e(self.s)
            if e.get('demissao_ativa', True) and e.get('status') == 'empregado' and _perfil_tecnico(self.s) != 'vencedor':
                diretoria.demitir(self.s, self.e, mundo, hoje, f"compromisso com a diretoria não cumprido ({ex['texto']})", nomes)
            else:
                mundo.m['diretoria'] = max(0, mundo.m.get('diretoria', 60) - 15)

    def view(self):
        din = self.s.get('dinheiro') or {}
        return {'perfil': self.perfil, 'perfil_txt': self.p['diretor']['perfil_txt'], 'nome': self.p['diretor']['nome'],
                'capacidade': capacidade(self.s), 'confianca': self._conf(), 'tecnico': _perfil_tecnico(self.s),
                'espera_aporte': self.espera('aporte'), 'espera_mover': self.espera('mover'),
                'aberto': self.em_aberto(), 'pedidos': self.d['pedidos'][-8:][::-1],
                'compromissos': self.d['compromissos'][-10:][::-1],
                'orc_transf': din.get('orc_transf'), 'orc_salario': din.get('orc_salario')}
