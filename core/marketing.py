"""Marketing do clube: sugere campanhas de cor nos uniformes (Novembro Azul, Outubro Rosa, aniversário do clube...).

- A sugestão vem sempre no 3º ou no 4º uniforme (o que o clube tiver); os uniformes principais não mudam.
- O técnico aprova ou recusa. Aprovar grava as cores no Estúdio (na família do uniforme) até o fim da campanha;
  depois as cores de antes voltam sozinhas. Aplicar no jogo continua sendo clique do técnico.
- Aprovar ou recusar sempre rende nota na imprensa, post da conta oficial e reação da torcida nas redes.
- O efeito é só na marca do clube (valor da marca/atratividade para patrocinadores), nunca no prestígio do técnico,
  na confiança da diretoria nem no humor da torcida com o técnico.
"""
import copy
import datetime as dt
import random
import re

from .sim import d2s, s2d, _seed
from .vozes import L, Memoria, fmt, humanizar
from . import vozes

# ---------------- calendário de campanhas ----------------
# ini/fim = (mês, dia). antes = quantos dias antes do início o marketing já sugere.
# aceita = chance de a torcida gostar da camisa (0 a 1). tipo decide como a recusa pesa.
CAMPANHAS = {
    'amarelo': {'nome': 'Setembro Amarelo', 'ini': (9, 1), 'fim': (9, 30), 'antes': 7, 'tipo': 'causa', 'preset': 'amarelo',
                'causa': 'valorização da vida e prevenção ao suicídio', 'cor': 'amarela', 'corm': 'amarelo', 'aceita': 0.8},
    'rosa': {'nome': 'Outubro Rosa', 'ini': (10, 1), 'fim': (10, 31), 'antes': 8, 'tipo': 'causa', 'preset': 'rosa',
             'causa': 'conscientização sobre o câncer de mama', 'cor': 'rosa', 'aceita': 0.84},
    'azul': {'nome': 'Novembro Azul', 'ini': (11, 1), 'fim': (11, 30), 'antes': 8, 'tipo': 'causa', 'preset': 'azul',
             'causa': 'prevenção ao câncer de próstata', 'cor': 'azul', 'aceita': 0.86},
    'vermelho': {'nome': 'Dezembro Vermelho', 'ini': (12, 1), 'fim': (12, 20), 'antes': 7, 'tipo': 'causa', 'preset': 'vermelho',
                 'causa': 'luta contra o HIV e a aids', 'cor': 'vermelha', 'corm': 'vermelho', 'aceita': 0.74},
    'natal': {'nome': 'Edição de Natal', 'ini': (12, 15), 'fim': (12, 25), 'antes': 7, 'tipo': 'data', 'preset': 'natal',
              'cor': 'vermelha e branca', 'corm': 'vermelho e branco', 'aceita': 0.6},
}
ANIVERSARIO = {'nome': 'Aniversário do clube', 'antes': 12, 'tipo': 'clube', 'preset': 'aniversario', 'aceita': 0.9,
               'cor': 'dourada', 'corm': 'dourado'}
CAMPEAO = {'nome': 'Edição campeã', 'dias': 30, 'tipo': 'conquista', 'preset': 'dourado', 'aceita': 0.88, 'cor': 'dourada', 'corm': 'dourado'}

BONUS_MIN, BONUS_MAX = -8, 12            # limites do bônus de marca guardado
FONTES = ['Globo Esporte', 'Lance!', 'ESPN', 'Máquina do Esporte', 'Trivela']

# ---------------- textos ----------------
SUGESTAO = {
    'causa': L("""Professor, o {campanha} está chegando e o departamento de marketing quer vestir a causa: {causa}. Proposta: o {uniforme} do {clube} ganha a cor {cor} entre {ini} e {fim}. Os uniformes principais não mudam. Preciso do seu aval.|
Professor, é hora de pensar no {campanha}. A ideia é pintar o {uniforme} de {corm} durante a campanha ({ini} a {fim}) e usar o jogo para falar da {causa}. A camisa principal fica como está. Posso seguir?|
Boa tarde, professor. Todo clube grande entra no {campanha} e o {clube} não pode ficar de fora. Sugiro o {uniforme} na cor {cor}, de {ini} a {fim}. Se o senhor aprovar, eu cuido do restante com a assessoria.|
Professor, trago uma sugestão do marketing para o {campanha}: {uniforme} {corm}, valendo de {ini} até {fim}, em apoio à {causa}. Os principais ficam intactos. Preciso da sua decisão para avisar a assessoria."""),
    'clube': L("""Professor, o {clube} faz {anos} anos em {data}. O marketing sugere um {uniforme} comemorativo, com detalhes dourados, de {ini} a {fim}. Torcedor adora essa data. Aprova?|
O aniversário do clube ({anos} anos, dia {data}) merece um uniforme à altura. Proposta: {uniforme} em edição especial dourada, entre {ini} e {fim}. Os principais seguem como estão.|
Professor, {anos} anos de {clube}! O marketing quer uma camisa comemorativa no {uniforme} para a semana da data ({data}). A torcida pede isso todo ano. Posso seguir?"""),
    'conquista': L("""Professor, o título merece ser lembrado. O marketing sugere o {uniforme} em edição campeã, dourado e com estrelas, de {ini} a {fim}. A torcida vai querer vestir. Aprova?|
Professor, com a taça na mão, o marketing quer lançar o {uniforme} de campeão (dourado, com estrelas acima do escudo) de {ini} até {fim}. É a hora de vender camisa. O que o senhor acha?|
Professor, campeões merecem uma camisa de campeões. Proposta: {uniforme} dourado, de {ini} a {fim}. Os principais não mudam. Preciso do seu aval."""),
    'data': L("""Professor, o Natal está chegando e o marketing sugere o {uniforme} em edição natalina ({cor}), de {ini} a {fim}. É mais uma ação de loja do que de campo, mas costuma render bem nas redes. Aprova?|
Professor, proposta leve do marketing: {uniforme} de Natal, em {cor}, de {ini} a {fim}. Os principais ficam como estão. É decisão sua.|
O marketing quer vestir o {clube} de Natal: {uniforme} {corm}, de {ini} até {fim}. Dá assunto nas redes e vende na loja. Posso seguir?"""),
}

TITULO_OK = {
    'causa': L("""{clube} veste o {campanha}: {uniforme} muda de cor e vira camisa da campanha|
{clube} aprova camisa do {campanha} e entra na causa dentro e fora de campo|
{uniforme} {corm} do {clube} marca o {campanha}|
Camisa {cor} do {clube} chega para o {campanha}: entenda a ação|
{clube} adere ao {campanha} com {uniforme} especial"""),
    'clube': L("""{clube} aprova uniforme comemorativo para os {anos} anos de fundação|
{uniforme} dourado marca o aniversário de {anos} anos do {clube}|
Aniversário de {anos} anos: {clube} lança camisa especial|
{clube} festeja {anos} anos com {uniforme} comemorativo"""),
    'conquista': L("""{clube} lança {uniforme} de campeão: dourado, com estrelas|
Edição campeã: {clube} aprova camisa para celebrar o título|
Torcida pediu e saiu: {clube} lança {uniforme} comemorativo do título"""),
    'data': L("""{clube} aprova {uniforme} de Natal: camisa tem {cor} e vira assunto|
Edição de Natal: {clube} muda a cor do {uniforme}|
{clube} entra no clima e lança camisa natalina"""),
}
TITULO_NAO = {
    'causa': L("""{clube} não vai vestir o {campanha}: marketing queria, comissão técnica disse não|
Sem camisa do {campanha}: {clube} recusa proposta do marketing|
{clube} fica de fora da onda do {campanha} nos uniformes|
Marketing sugeriu, técnico recusou: o {campanha} não terá camisa no {clube}"""),
    'clube': L("""Sem camisa especial: {clube} não terá uniforme nos {anos} anos|
{clube} recusa uniforme comemorativo do aniversário e gera reclamação|
Marketing queria festa, técnico disse não: aniversário do {clube} passa sem camisa"""),
    'conquista': L("""{clube} não terá camisa de campeão: ideia do marketing foi barrada|
Taça sem camisa especial: {clube} diz não à edição campeã"""),
    'data': L("""{clube} não terá camisa de Natal: proposta do marketing foi recusada|
Sem uniforme natalino: {clube} segue com a coleção normal"""),
}

TITULO_IGN = L("""{nome} passa em branco: sugestão de camisa do marketing ficou sem resposta no {clube}|
Sem resposta, sem camisa: {clube} deixa {nome} passar sem uniforme especial|
Proposta parada na gaveta: {clube} não terá camisa da ação {nome}""")
CITA_IGN = L("""\"Mandamos a proposta, mas não veio resposta a tempo\", disse {marketing}, do marketing do {clube}.|
\"A camisa estava pronta para produção. O prazo passou\", contou {marketing}.|
\"Fica o aprendizado: da próxima vez vamos levar a ideia com mais antecedência\", afirmou {marketing}.""")
CITA_OK = L("""\"Queremos que a camisa converse com a torcida\", disse {marketing}, responsável pelo marketing do {clube}.|
\"É uma ação simples, mas que dá visibilidade a algo importante\", afirmou {marketing}.|
\"O técnico entendeu a proposta e deu o aval rápido. Foi uma decisão que ajudou muito\", contou {marketing}.|
\"Trabalhamos meses nisso. A aprovação do professor {tecnico} foi essencial\", explicou {marketing}, do departamento de marketing.""")
CITA_NAO = L("""\"Respeitamos a decisão do professor {tecnico}, mas acreditávamos que era uma boa oportunidade\", disse {marketing}.|
\"Estava tudo pronto. Fica para uma próxima\", resumiu {marketing}, do marketing do {clube}.|
\"Não é o que o departamento queria, mas a palavra final é do campo\", afirmou {marketing}.|
\"A torcida pedia, nós queríamos, mas não houve acordo\", lamentou {marketing}.""")

RECEPCAO = {
    'otima': L("""A reação da torcida foi excelente: o lançamento bombou nas redes e a camisa já aparece esgotada em parte da loja oficial.|
Nas redes, o assunto dominou o dia: elogios à ideia e à camisa, que muita gente já diz que vai comprar.|
A repercussão foi muito positiva, com torcedores postando fotos e pedindo o lançamento no uniforme titular."""),
    'boa': L("""A torcida recebeu bem a ação, com mais elogios que críticas nas redes oficiais do clube.|
Houve boa receptividade entre os torcedores, ainda que alguns tenham comentado que preferem a cor tradicional.|
O clima nas redes foi favorável: elogios à iniciativa e brincadeiras sobre a cor da camisa."""),
    'dividida': L("""A torcida ficou dividida: parte elogiou a iniciativa, parte reclamou do visual da camisa.|
Nas redes, o debate esquentou: quem apoia a causa defende a ideia, enquanto outros dizem que a camisa ficou estranha.|
A repercussão foi mista, com elogios à causa e críticas à escolha de cores."""),
    'ruim': L("""A reação foi ruim: muitos torcedores criticaram o visual da camisa e pediram que o clube volte atrás.|
Os comentários nas redes foram negativos, com críticas ao desenho e à cor, e a conta oficial até apagou algumas respostas.|
A ação não agradou: houve reclamação de sócio-torcedor e piadas em série sobre a camisa."""),
}
CRITICA = {
    'causa': L("""A decisão gerou críticas nas redes: parte da torcida e de comentaristas lembrou que quase todos os clubes aderem à causa e que o {clube} perdeu uma oportunidade de visibilidade.|
Nas redes, o assunto virou polêmica: torcedores cobraram o clube por não participar do {campanha}, e alguns lembraram que a camisa seria só no {uniforme}.|
Houve reação de parte da torcida e de movimentos ligados à causa, que esperavam a camisa. O clube ainda pode fazer ações fora do campo."""),
    'clube': L("""Torcedores reclamaram nas redes: uma data tão especial passou sem uniforme comemorativo.|
Parte da torcida cobrou o clube: o aniversário é motivo de festa e muita gente queria a camisa especial."""),
    'conquista': L("""Parte da torcida lamentou: queria a camisa de campeão para eternizar o título.|
Nas redes, torcedores pediram a edição campeã, mas o clube preferiu não lançar."""),
    'data': L("""O assunto rendeu pouco: a maioria da torcida ficou indiferente, com algumas brincadeiras sobre o 'Natal sem camisa'.|
A decisão passou quase despercebida, com poucos comentários nas redes."""),
}

OFICIAL = {
    'sobrio': L("""O {clube} vestirá o {uniforme} na cor {cor} durante o {campanha}. #{tag}|
Em apoio à {causa}, o {uniforme} do {clube} ganha novas cores. #{tag}|
Comunicado: o {clube} participa do {campanha} com uniforme especial. #{tag}"""),
    'marketeira': L("""Chegou a camisa do {campanha}! {corm} total, e o manto tá lindo demais 😍 #{tag}|
Vem ver o {uniforme} que muda de cor pelo {campanha} 💥 O {clube} veste a causa! #{tag}|
Prepara que o manto novo chegou 🔥 {campanha}: {cor} e muita história #{tag}"""),
    'veterano': L("""O {clube} entra no {campanha}. Uniforme especial a partir de agora. #{tag}|
Camisa especial do {campanha} aprovada. Detalhes na loja oficial. #{tag}|
Mais uma ação do {clube}: {campanha} com uniforme de cor especial. #{tag}"""),
}

OFICIAL_GERAL = {
    'sobrio': L("""O {clube} apresenta o {uniforme} especial: {nome}. #{tag}|
Edição especial: o {uniforme} do {clube} ganha novas cores. #{tag}|
Comunicado: o {clube} lança o {uniforme} da ação {nome}. #{tag}"""),
    'marketeira': L("""Olha o manto especial chegando 😍 {nome} no {uniforme}! #{tag}|
Edição especial no ar 🔥 Quem vai garantir a sua? #{tag}|
O {uniforme} vestiu festa 🎉 {nome} chegou! #{tag}"""),
    'veterano': L("""{nome}: uniforme especial aprovado. Detalhes na loja oficial. #{tag}|
O {clube} lança o {uniforme} da ação {nome}. #{tag}"""),
}

# mesa de debate dos jornalistas sobre a camisa de campanha
MESA = {
    'ok': L("""Acho correta a decisão. Camisa de campanha não ganha jogo, mas o clube ganha imagem.|
É marketing, claro, mas é marketing do bem. O {clube} acertou em entrar na ação.|
Eu sou das antigas: camisa é camisa. Mas como é no uniforme reserva, não tenho do que reclamar.|
O {tecnico} fez bem em aprovar. Mostra que entende que o clube é maior que o vestiário.|
Vai vender camisa, vai dar assunto e não atrapalha em nada. Ação simples e inteligente.|
O importante agora é o clube fazer ação de verdade fora de campo, não só trocar a cor do tecido.|
Gostei do visual. Mas quero ver se o time vai jogar à altura da camisa nova.|
Patrocinador adora isso. A marca do {clube} sai fortalecida."""),
    'nao': L("""Não entendi a recusa. Era só o uniforme reserva e o clube perde visibilidade à toa.|
O técnico manda no campo, mas camisa é assunto do marketing. Decisão estranha.|
Eu até entendo: foco total no campeonato. Mas a imagem do clube sofre um pouco.|
Os outros clubes vão aderir e o {clube} vai ficar de fora. Isso pega mal.|
Sinceramente, pouca gente vai lembrar disso daqui a um mês. Tem coisa mais importante.|
Recusar uma ação dessas abre espaço para crítica desnecessária. Faltou sensibilidade.|
Tem torcedor que prefere a camisa tradicional, e esse pessoal gostou da decisão.|
O marketing ficou numa saia justa. Já tinha camisa pronta e agora ficou na gaveta."""),
}

# torcida: assuntos novos (entram no banco geral e valem para respostas também)
TEMAS = {
    'camp_ok': {
        'posts': L("""camisa do {campanha} do {clube} ficou linda demais|a camisa {cor} do {clube} é a mais bonita do ano, sem discussão|
bonito ver o {clube} falando de coisa importante, e a camisa ficou show|já quero a minha, qual loja tá vendendo?|
o {clube} acertou em cheio com a camisa do {campanha}|esse manto {corm} vai esgotar, apostando agora|
o marketing do {clube} acordou, camisa e causa certas|camisa {cor} com o escudo ficou diferente e elegante"""),
        'concordo': L("""muito bonita mesmo|já encomendei a minha|ficou top|ideia muito boa do clube|o marketing tá de parabéns|
apoio total, camisa e causa"""),
        'discordo': L("""bonita, mas preço tá salgado|prefiro a titular ainda|a cor não combina tanto assim|
causa certa, mas podia ter mais ação fora de campo"""),
        'zoeira': L("""agora só falta jogar bola kkk|camisa bonita não ganha jogo, mas ajuda kkk|vou comprar duas, uma pra guardar|
a mulher me mata se eu não comprar essa kkk"""),
    },
    'camp_ok_festa': {
        'posts': L("""camisa do {campanha} do {clube} ficou linda demais|essa edição especial do {clube} é a mais bonita do ano|
já quero a minha, qual loja tá vendendo?|o {clube} acertou em cheio com a camisa do {campanha}|
esse manto {corm} vai esgotar, apostando agora|o marketing do {clube} acordou, que camisa|
camisa {cor} com o escudo ficou diferente e elegante|isso é camisa de colecionador"""),
        'concordo': L("""muito bonita mesmo|já encomendei a minha|ficou top|ideia muito boa do clube|o marketing tá de parabéns|
vai pra coleção"""),
        'discordo': L("""bonita, mas preço tá salgado|prefiro a titular ainda|a cor não combina tanto assim|
mais uma camisa pra vender, né"""),
        'zoeira': L("""agora só falta jogar bola kkk|camisa bonita não ganha jogo, mas ajuda kkk|vou comprar duas, uma pra guardar|
a mulher me mata se eu não comprar essa kkk"""),
    },
    'camp_div': {
        'posts': L("""a causa é importante, mas a cor da camisa do {clube} ficou estranha|não curti o {corm} no manto, mas apoio a ideia|
bonita a iniciativa, o desenho podia ser melhor|camisa do {campanha} ficou meio estranha, mas a causa vale|
o {clube} podia ter caprichado mais no visual, mas a mensagem é boa|quem gostou levanta a mão, eu fiquei dividido"""),
        'concordo': L("""é isso, a causa é o que importa|também fiquei meio dividido|concordo, dá pra melhorar|ideia boa, execução média"""),
        'discordo': L("""achei bonita sim|que reclamação besta, é por uma causa|vocês reclamam de tudo kkk|o problema não é a cor, é o preço"""),
        'zoeira': L("""eu comprava até de bolinha se fosse pelo clube kkk|tão me chamando de rosa e eu nem liguei kkk|
vou usar pra trabalhar e ninguém vai notar kkk"""),
    },
    'camp_ruim': {
        'posts': L("""sinceramente a camisa {cor} do {clube} ficou horrível|quem aprovou essa camisa?|
o marketing do {clube} errou feio na camisa do {campanha}|nunca vou usar essa camisa, foi mal|
a ideia é boa, mas a camisa ficou feia demais|devolvam o manto de verdade, por favor|
não é possível que alguém olhou isso e disse que tava bom"""),
        'concordo': L("""também achei horrível|tá feia mesmo|marketing precisa rever isso|não compro nem de graça"""),
        'discordo': L("""exagero de vocês, ficou ok|é só um uniforme especial, relaxa|se não gosta, não compra|calma, é só um uniforme reserva"""),
        'zoeira': L("""parece pijama de criança kkk|meu cachorro tem coleira mais bonita kkk|vou guardar pra usar de pano de chão kkk|
nem o Photoshop salvaria essa camisa kkk"""),
    },
    'camp_recusa_festa': {
        'posts': L("""poxa, o {clube} não vai ter camisa do {campanha}?|queria muito a camisa do {campanha}, que pena|
quem decidiu que não ia ter camisa especial do {campanha}?|nada de camisa do {campanha}, a loja agradece kkk|
tava juntando dinheiro pra camisa do {campanha} e nada|sem camisa do {campanha}? fico triste, mas o foco é o campo"""),
        'concordo': L("""também queria|uma pena mesmo|o torcedor gosta dessas coisas|perderam uma venda certa"""),
        'discordo': L("""melhor assim, foco no campo|já tem camisa demais|o preço ia ser absurdo de qualquer jeito|
tanto faz, quero é título"""),
        'zoeira': L("""meu bolso agradece kkk|a minha esposa agradece kkk|vou desenhar uma no paint kkk"""),
    },
    'camp_recusa': {
        'posts': L("""o {clube} não vai aderir ao {campanha}? sério isso?|que pena o {clube} ficar de fora do {campanha}, marketing tinha ideia|
a gente veste a camisa o ano todo, custava vestir a causa um mês?|não entendi por que o {clube} recusou a camisa do {campanha}|
todo mundo participa e o {clube} fica de fora, decepcionado|quem decidiu isso devia explicar pra torcida|
bobagem, é só um uniforme reserva, deixa o marketing trabalhar"""),
        'concordo': L("""também não entendi|decepcionado mesmo|marketing tinha razão|clube perdeu uma boa chance"""),
        'discordo': L("""cada um decide o que vestir|o foco tem que ser o campo|sem tempo pra isso, o time precisa ganhar|
o professor sabe o que faz"""),
        'zoeira': L("""vai ver o {corm} não combina com o técnico kkk|tem que fazer camisa pra isso? kkk|já ia reclamar da camisa também, melhor assim kkk"""),
    },
}


def _tem(n, k):
    return k in n and bool(n[k])


def _com_anos(d, a):
    return d.year - a


def _data(d):
    meses = ['', 'janeiro', 'fevereiro', 'março', 'abril', 'maio', 'junho', 'julho', 'agosto', 'setembro',
             'outubro', 'novembro', 'dezembro']
    return f'{d.day} de {meses[d.month]}'


def _curta(d):
    return f'{d.day:02d}/{d.month:02d}'


def registrar_temas():
    for k, b in TEMAS.items():
        vozes.TORCIDA.setdefault(k, b)
    vozes.POSTURA.setdefault('camp_ok', (6, 2, 2))
    vozes.POSTURA.setdefault('camp_div', (3, 4, 3))
    vozes.POSTURA.setdefault('camp_ok_festa', (6, 2, 2))
    vozes.POSTURA.setdefault('camp_ruim', (4, 4, 4))
    vozes.POSTURA.setdefault('camp_recusa', (4, 4, 2))
    vozes.POSTURA.setdefault('camp_recusa_festa', (4, 4, 3))


registrar_temas()


class Marketing:
    def __init__(self, state, clube, tid, pessoas=None, engine=None, tecnico=None):
        self.s = state
        self.clube = clube
        self.tid = tid
        self.p = pessoas or {}
        self.e = engine
        self.tecnico = tecnico or state.get('cfg_tecnico') or 'o técnico'
        d = state.setdefault('marketing', {})
        d.setdefault('sugestoes', [])      # esperando decisão
        d.setdefault('ativas', [])         # aprovadas e em vigor
        d.setdefault('hist', [])           # encerradas ou recusadas
        d.setdefault('feitas', {})         # campanha:ano -> status
        d.setdefault('marca_bonus', 0)
        self.d = d
        self.mem = Memoria(state)

    # ---------- pessoas ----------
    def nome_marketing(self):
        from . import dirigentes
        pais = self.s.get('pais') or 'Brasil'
        pool = dirigentes.NOMES_ASS if pais == 'Brasil' else dirigentes.NOMES_ASS_ES
        ass = (self.p.get('assessor') or {}).get('nome')
        k = dirigentes._seed('mkt', dirigentes._slug(self.clube), self.tid)
        for i in range(len(pool)):
            n = pool[(k + i * 7) % len(pool)]
            if n != ass:
                return n
        return pool[0]

    def assinatura(self):
        return f'{self.nome_marketing()} · Marketing'

    # ---------- uniformes ----------
    def _opcoes(self, variantes):
        """Famílias do 3º e do 4º uniforme: [(variante, família)]."""
        out = []
        for v in variantes:
            if re.match(r'^p[34]$', v[0]) and all(o[1] != v[2] for o in out):
                out.append((v[0], v[2]))
        return out

    def _ocupadas(self):
        return {a['familia'] for a in self.d['ativas']} | {s['familia'] for s in self.d['sugestoes']}

    # ---------- calendário ----------
    def _janelas(self, hoje):
        """Campanhas que podem ser sugeridas hoje: [(chave, info, ini, fim, extra)]."""
        out = []
        for k, c in CAMPANHAS.items():
            ini = dt.date(hoje.year, *c['ini'])
            fim = dt.date(hoje.year, *c['fim'])
            if ini - dt.timedelta(days=c['antes']) <= hoje <= fim:
                out.append((k, c, max(ini, hoje), fim, {}))
        from . import rivais
        f = rivais.FUNDACAO.get(rivais.chave(self.clube))
        if f:
            dia, mes, ano = f
            try:
                dd = dt.date(hoje.year, mes, dia)
            except ValueError:
                dd = None
            if dd and dd - dt.timedelta(days=ANIVERSARIO['antes']) <= hoje <= dd + dt.timedelta(days=3):
                out.append(('aniversario', ANIVERSARIO, max(dd - dt.timedelta(days=3), hoje), dd + dt.timedelta(days=3),
                            {'anos': hoje.year - ano, 'data': _data(dd)}))
        tits = [t for t in (self.s.get('gestao') or {}).get('titulos', []) if t.get('data')]
        if tits:
            ult = max(tits, key=lambda t: t['data'])
            dd = s2d(ult['data'])
            if 0 <= (hoje - dd).days <= 14:
                out.append((f"campeao{dd.isoformat()}", CAMPEAO, hoje, hoje + dt.timedelta(days=CAMPEAO['dias']),
                            {'estrelas': min(5, len(tits))}))
        return out

    # ---------- fluxo ----------
    def processar(self, mu, hoje, variantes, paleta_de, presets):
        """Encerra o que venceu e cria sugestões novas. paleta_de(família) devolve a paleta do uniforme."""
        if not hoje:
            return
        hs = d2s(hoje)
        self._encerrar(hoje, hs)
        opcoes = self._opcoes(variantes)
        if not opcoes:
            return
        for chave, c, ini, fim, extra in self._janelas(hoje):
            ano = hoje.year
            ck = f'{chave}:{ano}'
            if ck in self.d['feitas'] or any(s['campanha'] == chave and s['ano'] == ano for s in self.d['sugestoes']):
                continue
            livres = [o for o in opcoes if o[1] not in self._ocupadas()]
            if not livres:
                continue
            pref = livres[_seed('mkt', self.clube, chave) % len(livres)]
            variante, fam = pref
            try:
                pal = paleta_de(fam)
            except Exception:
                pal = []
            if not pal:
                continue
            trocas = []
            for i, cor in enumerate((presets.get(c['preset']) or {}).get('cores') or []):
                if cor and i < len(pal):
                    trocas.append([pal[i]['cor'], cor])
            cfg = {'trocas': trocas, 'paleta': pal, 'retro': False, 'estrelas': extra.get('estrelas', 0),
                   'cor_estrelas': '#c9a227', 'ativo': True, 'campanha': chave}
            if not trocas and not cfg['estrelas']:
                continue
            tipo = c['tipo']
            r = random.Random(_seed('mkt', self.clube, ck))
            ord_ = 'terceiro uniforme' if variante.startswith('p3') else 'quarto uniforme'
            curto = {'clube': f"aniversário de {extra.get('anos')} anos", 'data': 'Natal', 'conquista': 'título'}.get(tipo, c['nome'])
            v = {'campanha': curto, 'nome': c['nome'], 'causa': c.get('causa') or '', 'cor': c['cor'], 'corm': c.get('corm') or c['cor'], 'uniforme': ord_, 'clube': self.clube,
                 'ini': _curta(ini), 'fim': _curta(fim), 'anos': extra.get('anos', ''), 'data': extra.get('data', ''),
                 'marketing': self.nome_marketing(), 'tecnico': self.tecnico}
            texto = self.mem.escolher('mkt:sug:' + tipo, SUGESTAO[tipo], r, v)
            sg = {'id': f'{chave}-{ano}', 'campanha': chave, 'ano': ano, 'nome': c['nome'] if chave != 'aniversario'
                  else f"{c['nome']} ({extra.get('anos')} anos)", 'tipo': tipo, 'familia': fam, 'variante': variante,
                  'uniforme': ord_, 'ini': d2s(ini), 'fim': d2s(fim), 'cfg': cfg, 'texto': texto, 'sugerida_em': hs,
                  'vars': v, 'aceita': c['aceita'], 'preset': c['preset']}
            self.d['sugestoes'].append(sg)
            if self.e is not None:
                self.e.s['mensagens'].append({'id': self.e._id(), 'data': hs, 'empresa': '__diretoria__', 'de': self.assinatura(),
                                              'assunto': f"Sugestão de campanha: {sg['nome']}", 'tipo': 'diretoria',
                                              'oferta_id': None, 'lida': False,
                                              'texto': texto + ' (Decida na aba Uniformes, no topo.)'})
            self._hist_log(hs, f"Sugeriu {sg['nome']} no {ord_}.")

    def _hist_log(self, ds, txt):
        self.d.setdefault('log', []).append({'data': ds, 'texto': txt})
        self.d['log'] = self.d['log'][-30:]

    def _encerrar(self, hoje, hs):
        # sugestões que ninguém respondeu até o fim da campanha: viram "sem resposta" (pesa como recusa leve)
        for sg in list(self.d['sugestoes']):
            if s2d(sg['fim']) < hoje:
                self.d['sugestoes'].remove(sg)
                self.d['feitas'][f"{sg['campanha']}:{sg['ano']}"] = 'ignorada'
                self._efeito(sg, False, hs, ignorada=True)
        for a in list(self.d['ativas']):
            if s2d(a['fim']) < hoje:
                self.d['ativas'].remove(a)
                est = self.s.setdefault('estudio', {})
                if a.get('anterior'):
                    est[a['familia']] = a['anterior']
                else:
                    est.pop(a['familia'], None)
                self.d['hist'].append({**self._resumo(a), 'status': 'encerrada', 'em': hs})
                self.d['hist'] = self.d['hist'][-30:]
                if self.e is not None:
                    self.e.s['mensagens'].append({'id': self.e._id(), 'data': hs, 'empresa': '__diretoria__', 'de': self.assinatura(),
                                                  'assunto': f"{a['nome']} encerrada", 'tipo': 'diretoria', 'oferta_id': None,
                                                  'lida': False,
                                                  'texto': f"Professor, a campanha {a['nome']} acabou. O {a['uniforme']} volta às cores de antes "
                                                           "na próxima vez que o senhor aplicar os uniformes no jogo."})
                self._hist_log(hs, f"{a['nome']} encerrada: o {a['uniforme']} volta ao normal.")

    def _resumo(self, a):
        return {k: a.get(k) for k in ('id', 'nome', 'tipo', 'uniforme', 'familia', 'ini', 'fim', 'recepcao', 'delta_marca')}

    def responder(self, sid, aprovar, mu, hoje):
        sg = next((s for s in self.d['sugestoes'] if s['id'] == sid), None)
        if not sg:
            raise ValueError('Essa sugestão já foi respondida.')
        hs = d2s(hoje) if hoje else self.s.get('data')
        self.d['sugestoes'].remove(sg)
        self.d['feitas'][f"{sg['campanha']}:{sg['ano']}"] = 'aprovada' if aprovar else 'recusada'
        if aprovar:
            est = self.s.setdefault('estudio', {})
            anterior = copy.deepcopy(est.get(sg['familia']))
            est[sg['familia']] = copy.deepcopy(sg['cfg'])
            sg['anterior'] = anterior
            self.d['ativas'].append(sg)
        self._efeito(sg, aprovar, hs)
        if aprovar:
            self.d['ativas'][-1].update({k: sg.get(k) for k in ('recepcao', 'delta_marca')})
        return sg

    # ---------- efeito: imprensa, redes e marca ----------
    def _recepcao(self, sg, r):
        torc = (self.s.get('mundo') or {}).get('torcida', 50)
        p = max(0.2, min(0.95, sg['aceita'] + (torc - 50) / 250))
        x = r.random()
        if x < p * 0.55:
            return 'otima'
        if x < p:
            return 'boa'
        return 'dividida' if x < p + (1 - p) * 0.6 else 'ruim'

    def _efeito(self, sg, aprovar, hs, ignorada=False):
        from .mundo import Mundo
        r = random.Random(_seed('mkt:ef', self.clube, sg['id'], aprovar, ignorada))
        tipo = sg['tipo']
        v = dict(sg['vars'])
        v.setdefault('marketing', self.nome_marketing())
        v['tecnico'] = self.tecnico
        mu = Mundo(self.s, self.clube, self.tid)
        if aprovar:
            rec = self._recepcao(sg, r)
            sg['recepcao'] = rec
            delta = {'otima': 3, 'boa': 2, 'dividida': 0, 'ruim': -1}[rec]
            titulo = self.mem.escolher('mkt:tit:ok:' + tipo, TITULO_OK[tipo], r, v)
            corpo = [f"O {self.clube} oficializou o {sg['uniforme']} na cor {v['cor']} para a ação \"{sg['nome']}\", valendo de "
                     f"{_curta(s2d(sg['ini']))} a {_curta(s2d(sg['fim']))}. Os uniformes principais seguem como estão.",
                     self.mem.escolher('mkt:cita:ok', CITA_OK, r, v), self.mem.escolher('mkt:rec:' + rec, RECEPCAO[rec], r, v)]
            temas = {'otima': ['camp_ok'] * 3, 'boa': ['camp_ok', 'camp_ok', 'camp_div'],
                     'dividida': ['camp_ok', 'camp_div', 'camp_ruim'], 'ruim': ['camp_div', 'camp_ruim', 'camp_ruim']}[rec]
            if tipo != 'causa':                 # o assunto "dividido" fala da causa
                temas = ['camp_ok_festa' if t in ('camp_div', 'camp_ok') else t for t in temas]
        else:
            rec = 'recusada'
            sg['recepcao'] = rec
            if ignorada:
                delta = -1 if tipo in ('causa', 'clube') else 0
                titulo = self.mem.escolher('mkt:tit:ign', TITULO_IGN, r, v)
                corpo = [f"A campanha {sg['nome']} passou sem uniforme: o marketing do {self.clube} sugeriu, mas a proposta ficou sem resposta do técnico até o fim do prazo.",
                         self.mem.escolher('mkt:cita:ign', CITA_IGN, r, v), self.mem.escolher('mkt:crit:' + tipo, CRITICA[tipo], r, v)]
            else:
                delta = {'causa': -2, 'clube': -1}.get(tipo, 0)
                titulo = self.mem.escolher('mkt:tit:nao:' + tipo, TITULO_NAO[tipo], r, v)
                corpo = [f"O {self.clube} decidiu não colocar em campo o {sg['uniforme']} da ação \"{sg['nome']}\". A proposta partiu do departamento de marketing e foi recusada pelo técnico.",
                         self.mem.escolher('mkt:cita:nao', CITA_NAO, r, v), self.mem.escolher('mkt:crit:' + tipo, CRITICA[tipo], r, v)]
            temas = ['camp_recusa', 'camp_recusa', 'camp_recusa'] if tipo == 'causa' else \
                ['camp_recusa_festa'] * (1 if tipo == 'data' else 2)
        titulo = titulo[:1].upper() + titulo[1:]
        sg['delta_marca'] = delta
        self.d['marca_bonus'] = max(BONUS_MIN, min(BONUS_MAX, self.d['marca_bonus'] + delta))
        mu.m['noticias'].append({'data': hs, 'tipo': 'campanha', 'titulo': titulo, 'fonte': r.choice(FONTES),
                                 'aprovada': bool(aprovar), 'campanha_nome': sg['nome'],
                                 'destaque': aprovar and rec in ('otima', 'ruim'), 'corpo': corpo, 'campanha': sg['campanha']})
        mu.m['noticias'] = mu.m['noticias'][-200:]
        tag = ''.join(ch for ch in sg['nome'].title() if ch.isalnum())
        for t in temas:
            mu.posts(t, hs, r, n=1, campanha=v['campanha'], cor=v['cor'], corm=v.get('corm', v['cor']), causa=v.get('causa', ''))
        if aprovar:
            try:
                from . import assessor
                ass = assessor.Assessor(self.s, self.clube, self.tid, self.tecnico)
                est = (self.p.get('assessor') or {}).get('estilo') or ass.p.get('estilo') or 'sobrio'
                banco = OFICIAL if tipo == 'causa' else OFICIAL_GERAL
                txt = self.mem.escolher(f'mkt:of:{tipo == "causa"}:{est}', banco.get(est) or banco['sobrio'], r,
                                        {**v, 'tag': tag, 'nome': sg['nome']})
                tt = 'camp_ok' if tipo == 'causa' else 'camp_ok_festa'
                ass._post(hs, txt, tt, r, extra={'tema': tt}, n_resp=3)
            except Exception:
                pass
        self._hist_log(hs, f"{sg['nome']}: {'aprovada' if aprovar else ('sem resposta' if ignorada else 'recusada')} "
                           f"(marca {delta:+d}).")
        if not aprovar:
            self.d['hist'].append({**self._resumo(sg), 'status': 'sem resposta' if ignorada else 'recusada', 'em': hs})
            self.d['hist'] = self.d['hist'][-30:]

    # ---------- tela ----------
    def view(self, hoje):
        def dias(a):
            return max(0, (s2d(a['fim']) - hoje).days) if hoje else None
        return {'nome': self.nome_marketing(), 'marca_bonus': self.d['marca_bonus'],
                'sugestoes': [{**{k: s[k] for k in ('id', 'nome', 'tipo', 'uniforme', 'familia', 'ini', 'fim', 'texto')},
                               'cfg': s['cfg'], 'cor': s['vars'].get('cor'), 'dias': dias(s)} for s in self.d['sugestoes']],
                'ativas': [{**{k: s.get(k) for k in ('id', 'nome', 'uniforme', 'familia', 'ini', 'fim', 'recepcao', 'delta_marca')},
                            'dias': dias(s)} for s in self.d['ativas']],
                'hist': self.d['hist'][-8:][::-1], 'log': self.d.get('log', [])[-8:][::-1]}
