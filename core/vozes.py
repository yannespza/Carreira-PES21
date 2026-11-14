"""Vozes do mundo do clube: torcida nas redes, diretoria e assessoria.

Tudo é organizado por ASSUNTO, para que a resposta sempre converse com o post:
quem pede reforço recebe respostas sobre reforço, quem elogia o técnico recebe quem concorda,
quem discorda e quem faz piada sobre o técnico.

A Memória guarda os últimos textos usados de cada banco: o app evita repetir e só volta a uma frase
quando o banco inteiro já rodou (ou quase). Repetição existe, mas é rara.
"""
import random
import string
import unicodedata


def L(s):
    """Lista a partir de texto separado por | (deixa o banco legível)."""
    return [x.strip() for x in s.split('|') if x.strip()]


class _Vazio(dict):
    def __missing__(self, k):
        return ''


def fmt(txt, v):
    from . import posicao
    txt = posicao.limpar(txt)
    posicao.completar(v)
    try:
        return string.Formatter().vformat(txt, (), _Vazio(v))
    except (ValueError, IndexError):
        return txt


# ---------------- memória anti-repetição ----------------
class Memoria:
    def __init__(self, state):
        m = state.setdefault('mundo', {})
        self.u = m.setdefault('usados', {})

    def escolher(self, chave, pool, rnd, v=None):
        if not pool:
            return ''
        from . import posicao
        pool = posicao.filtrar(pool, v)       # frase de goleiro só para goleiro, de atacante só para atacante...
        recentes = self.u.setdefault(chave, [])
        livres = [t for t in pool if t not in recentes]
        if not livres:                      # banco rodou inteiro: volta o mais antigo
            ordem = {t: i for i, t in enumerate(recentes)}
            livres = sorted(pool, key=lambda t: ordem.get(t, -1))[:max(1, len(pool) // 4)]
        t = rnd.choice(livres)
        recentes.append(t)
        lim = max(2, min(80, int(len(pool) * 0.75)))
        del recentes[:-lim]
        return fmt(t, v or {})


def humanizar(txt, rnd, forte=True):
    """Jeito de quem escreve no celular: às vezes minúscula, sem ponto final."""
    if not txt:
        return txt
    if forte and rnd.random() < 0.35 and txt[0].isupper() and not txt[:2].isupper():
        txt = txt[0].lower() + txt[1:]
    if txt.endswith('.') and not txt.endswith('...') and rnd.random() < 0.55:
        txt = txt[:-1]
    return txt


# ---------------- torcedores ----------------
NOMES = L("""Lucas|Bruno|Rafa|Dudu|Ana|Carol|Thiago|Gabi|Pedro|João|Vini|Marcos|Léo|Fernanda|Júlia|Renan|Caio|Bia|
Diego|Matheus|Jéssica|Paulo|Tiago|Mari|Rodrigo|Camila|Felipe|Larissa|André|Patrícia|Gustavo|Aline|Henrique|Bruna|
Seu Zé|Dona Cida|Tio Beto|Fabinho|Juninho|Neto|Kaique|Wesley|Natália|Sérgio|Márcio|Luana|Igor|Rayssa|Davi|Talita""")
SOBRENOMES = L("""Andrade|Souza|Lima|Rocha|Mendes|Costa|Barros|Freitas|Nogueira|Pires|Teixeira|Alves|Moura|Cardoso|
Ribeiro|Duarte|Farias|Campos|Pacheco|Moreira|Siqueira|Bezerra|Queiroz|Fontes""")
GERAIS = [('@cornetafc', 'Corneta FC'), ('@resenha_fut', 'Resenha Fut'), ('@torcedor_fiel', 'Torcedor Fiel'),
          ('@tiozao_do_radio', 'Tiozão do Rádio'), ('@estatistica_fc', 'Estatística FC'),
          ('@vozdaarquibancada', 'Voz da Arquibancada'), ('@jornalistaFC', 'Jornalista FC'),
          ('@futebolraiz_br', 'Futebol Raiz'), ('@setorista_hoje', 'Setorista Hoje')]


def slug(clube):
    s = unicodedata.normalize('NFKD', clube).encode('ascii', 'ignore').decode().lower()
    return ''.join(ch for ch in s if ch.isalnum())[:12] or 'clube'


def torcedores(clube):
    """~45 perfis fixos por clube: contas coletivas, torcedores com nome e perfis gerais."""
    c = slug(clube)
    r = random.Random('torc|' + c)
    out = [(f'@{c}_raiz', f'{clube} Raiz'), (f'@torcida{c}', f'Torcida {clube}'), (f'@sou{c}', f'Sou {clube}'),
           (f'@nacao_{c}', f'Nação {clube}'), (f'@{c}depressao', f'{clube} Depressão'), (f'@fala{c}', f'Fala {clube}'),
           (f'@{c}_oficialfans', f'{clube} Oficial Fans'), (f'@{c}10', f'{clube} 10')]
    usados = set()
    nomes = NOMES[:]; r.shuffle(nomes)
    sobs = SOBRENOMES[:]; r.shuffle(sobs)
    i = 0
    while len(out) < 38:
        n = nomes[i % len(nomes)]
        sb = sobs[i % len(sobs)]
        i += 1
        base = unicodedata.normalize('NFKD', n).encode('ascii', 'ignore').decode().lower().replace(' ', '')
        h = r.choice([f'@{base}{c[:6]}', f'@{base}_{sb.lower()}', f'@{base}{r.randint(7, 99)}', f'@{base}.{c[:8]}',
                      f'@{base}_{c[:5]}{r.randint(1, 9)}'])
        if h in usados:
            continue
        usados.add(h)
        nome = n if r.random() < 0.45 else f'{n} {sb}'
        if r.random() < 0.18:
            nome += ' ' + r.choice(['⚽', '💚', '🏟️', '🔥', '🙏'])
        out.append((h, nome))
    return out + GERAIS


# ---------------- torcida: posts e respostas por assunto ----------------
# cada assunto: posts | concordo | discordo | zoeira
TORCIDA = {
    # ---- depois do jogo ----
    'euforia': {
        'posts': L("""QUE TIME! 🔥🔥🔥 {clube} é outro patamar|esse time tá jogando por música, não tem pra ninguém 🔥|
dá pra sonhar com título sim, me julguem|{placar} e ainda foi pouco kkkkk|o {tecnico} merece estátua na porta do estádio 🏆|
{jogador} jogou DEMAIS hoje, craque 👑|chora {adv} 😂😂|melhor fase que eu já vi desse {clube} e olha que eu sou velho|
ninguém para esse {clube} 🚀|tô rouco até agora, que jogo!!|passei o jogo inteiro em pé no sofá, coração não aguenta|
{placar} no {adv}, alguém anota a placa|time encaixado, toque de bola bonito, dá gosto de ver|
o {adv} veio pra empatar e saiu com {placar} na mala kkkk|essa camisa pesa e hoje o time honrou cada fio dela|
meu pai chorou vendo esse jogo, sério|liga o modo campeão, {clube}!!|quem falou mal do {tecnico} em agosto tá quietinho né|
olha o {clube} incomodando o campeonato inteiro 👀|sexta-feira já, segunda-feira, tanto faz: hoje é dia de comemorar"""),
        'concordo': L("""isso aí!! 🔥|verdade demais|time do povo|BORA|assino embaixo|melhor fase, sem discussão|
falou tudo|não tem como discordar|arrepiei aqui|que delícia de time|tô igual, sem voz|É ISSO|
dá pra sonhar sim, por que não?|o grupo comprou a ideia do {tecnico}, dá pra ver|merecido demais|
{jogador} tá voando mesmo|cada jogo melhor que o outro"""),
        'discordo': L("""calma, ainda não ganhamos nada|euforia agora é perigoso, pé no chão|o {adv} jogou muito mal, não é parâmetro|
gostei, mas a defesa ainda dá espaço|bonito, mas campeonato é maratona|não vamos repetir o erro de achar que já tá ganho|
segundo tempo caiu de rendimento, ninguém falou nada|time tá bem mas o banco é curto, quero ver com desfalque"""),
        'zoeira': L("""cadê os cornetas? 😂|o grupo do zap do trabalho tá em silêncio kkkk|vou mandar print pro meu cunhado|
manda o {adv} pedir música no Fantástico|tô com medo de acordar e ser sonho kkk|alguém chama a ambulância pro {adv}|
torcedor do {adv} sumiu da timeline kkkkk"""),
    },
    'feliz': {
        'posts': L("""vitória importante, segue o baile|três pontos é o que importa|boa, mas dá pra melhorar no segundo tempo|
bom resultado, bora manter a sequência|{clube} trabalhando ✅|{jogador} decisivo de novo 👏|sofrido mas veio, é isso|
vamo {clube}!! próximo jogo é guerra|gostei da postura do time hoje|o {tecnico} acertou nas mudanças|
não foi bonito, mas foi eficiente|vencer o {adv} nunca é fácil, valeu demais|quem não sofre não é torcedor, mas veio|
{placar} tá ótimo, saldo é saldo|time competiu do primeiro ao último minuto|deu pra dormir tranquilo hoje|
achei o meio mais organizado, evolução clara|foi no detalhe, mas campeonato se ganha assim|
vitória com cara de time grande|segura essa sequência, {clube}"""),
        'concordo': L("""concordo demais|segue o baile|dá pra melhorar mas tá bom|boa!|é isso, foco no próximo|👏👏|
vitória com personalidade|cada jogo um passo|o importante é somar|gostei da entrega|ganhou no coletivo|
deu gosto de ver a raça|vamo {clube}|
três pontos e cama|exatamente, vitória é vitória|o time tá entendendo o que o {tecnico} quer|{jogador} tá jogando muito|
melhor ganhar jogando feio do que perder jogando bonito|tamo junto|bora manter|time mais confiante, dá pra ver"""),
        'discordo': L("""ganhou mas sofreu demais, não me engana|contra time grande isso não vai dar|
sorte que o {adv} perdeu aquele gol|vitória sim, atuação nem tanto|ainda acho o meio muito lento|
nota 6, no máximo|o goleiro salvou a gente, vamos ser sinceros|se fosse outro adversário tinha empatado"""),
        'zoeira': L("""meu coração pediu demissão aos 40 do segundo tempo kkk|sofrer faz parte do pacote de sócio|
já posso respirar?|cardiologista agradece|vitória no estilo {clube}: com emoção até o fim"""),
    },
    'neutro': {
        'posts': L("""empate fora não é o fim do mundo|jogo travado, faltou criatividade|ponto é ponto... mas esperava mais|
time precisa de reforço no meio|segue o campeonato|[MA]{jogador} sumiu no jogo hoje|nem bom nem ruim, morno|[G]{jogador} salvou o ponto com aquela defesa|[D]{jogador} segurou a zaga, pelo menos isso|
dava pra ter vencido o {adv}|o {tecnico} precisa mexer mais cedo|{placar}, cada um leva um ponto pra casa|
faltou o último passe, o resto foi ok|jogo pra esquecer rápido|criou pouco, sofreu pouco, empate justo|
alguém mais achou que o time cansou no fim?|empate com gosto de derrota pra mim|empate com gosto de vitória pelo que foi o jogo|
esse time precisa de alguém que chame o jogo|meia-boca, mas segue"""),
        'concordo': L("""pois é|faltou pouco|temporada é longa|concordo em parte|🤔|falta um camisa 10|
o time trava quando precisa criar|faltou alguém pra decidir|esse ponto pode fazer falta|
gostei do esforço, faltou qualidade|
o empate não é ruim, ruim é não criar|faltou ousadia|justo o resultado|era jogo pra vencer"""),
        'discordo': L("""calma galera, não foi tão ruim|empate com o {adv} fora é bom resultado sim|
o time criou, faltou capricho, só isso|exagero, o time tá evoluindo|ninguém ganha todas|
eu vi um time organizado, não entendi a reclamação"""),
        'zoeira': L("""empate é tipo café sem açúcar|joguinho pra dormir no sofá|0 emoção, 100% bocejo kkk|
se eu soubesse tinha ido no aniversário da minha tia"""),
    },
    'chateado': {
        'posts': L("""que fase... time sem alma|não dá pra perder assim pro {adv}|cadê a intensidade??|
alguém explica essas substituições?|torcida não merece isso|{jogador} não pode ser titular|tá difícil defender esse time|[G]{jogador} engoliu um frango que não dá pra aceitar|[D]{jogador} deixou o atacante passar como se fosse cone|[A]{jogador} perdeu gol feito, inacreditável|
{tecnico} precisa achar o time logo|perder pro {adv} jogando desse jeito é triste|time entrou dormindo e acordou tarde|
de novo o mesmo filme, gol bobo e time perdido|o {clube} não pode se acostumar a perder|
sem padrão de jogo nenhum, cada um faz o que quer|toma gol e o time some, impressionante|
tô cansado de ver o mesmo erro toda semana|não tem um que chame a responsabilidade|
que domingo horrível|perdeu e mereceu perder, simples"""),
        'concordo': L("""triste|tá complicado|verdade|precisa mudar algo|faltou raça mesmo|😞|
o problema é o meio, não cria nada|time sem pegada|e o pior é que já tava previsto|toda semana a mesma coisa|
alguém precisa falar no vestiário|falou tudo, sem padrão"""),
        'discordo': L("""calma, o {adv} é bom time|uma derrota não apaga o que o time fez|
o {tecnico} tem crédito, deixa trabalhar|tem jogador fora, normal oscilar|foi um jogo ruim, acontece|
juiz também ajudou a complicar, vamos ser justos|não vou crucificar ninguém por um jogo"""),
        'zoeira': L("""vou desinstalar o futebol do celular|minha pressão subiu mais que o time|
o {adv} agradece a gentileza|nem a minha avó erra aquele passe|vou assistir novela no próximo jogo"""),
    },
    'revolta': {
        'posts': L("""FORA TODO MUNDO 😡|vergonha, {placar} é inaceitável|diretoria acorda!! isso aqui é o {clube}|
devolve o dinheiro do ingresso|chega de desculpa, quero resultado|fora {tecnico} 😤|esse elenco não tem vergonha na cara|
{placar}?? {placar}??? não tem explicação|vexame histórico, escreve aí|eu exijo respeito com essa camisa|
quero ver quem vai dar a cara na coletiva hoje|time apático, sem sangue, sem nada|já chega, alguém tem que pagar por isso|
protesto no CT amanhã, quem vai?|tô com vergonha de vestir a camisa no trabalho amanhã|
essa diretoria vai afundar o {clube}|nunca vi um time tão entregue|quem montou esse elenco tem que explicar"""),
        'concordo': L("""exatamente|ninguém aguenta mais|vergonha|FORA|concordo 100%|😡😡|limpa geral|
cansei de passar raiva|a camisa merece mais que isso|é inaceitável|quero ver alguém se explicar|
falou tudo, chega|tô junto no protesto|não dá mais|esse time não honra a camisa|a paciência acabou"""),
        'discordo': L("""calma, protesto com violência não ajuda|trocar técnico toda hora é o que afunda clube|
o elenco é fraco, o técnico faz o que dá|criticar é direito, xingar não|em momento ruim é que a torcida tem que apoiar|
fora todo mundo e vai entrar quem? pensa um pouco|não adianta só gritar, tem que cobrar com inteligência"""),
        'zoeira': L("""o {adv} devia pagar ingresso pra gente depois dessa|vou torcer pro time de botão agora|
nem no videogame eu tomo {placar}|time de várzea da minha rua joga mais|terapeuta vai ficar rico com a torcida"""),
    },

    # ---- semana (assuntos de bastidor) ----
    'reforco': {
        'posts': L("""contrata um meia aí diretoria pfv|precisamos de um centroavante de verdade|
lateral esquerdo é urgente, não dá mais|janela abrindo e nenhum nome? sério?|quero um camisa 10 que pense o jogo|
a diretoria vai esperar o campeonato acabar pra contratar?|um volante de marcação resolve metade dos problemas|
falta peça de reposição, se um machuca acabou|alguém tem notícia de reforço? tá muito quieto|
banco de reservas tá muito fraco, precisa de opção|se vier um zagueiro rápido já fico feliz|
olha o mercado aí, tem jogador bom sobrando|não quero nome de impacto, quero jogador que resolva"""),
        'concordo': L("""concordo, meio tá carente|centroavante é prioridade|faz tempo que peço isso|
o {tecnico} já falou que precisa, só a diretoria não ouve|sem reforço não chega a lugar nenhum|
pelo menos um nome pra brigar por posição|banco curto mata qualquer time|apoiado"""),
        'discordo': L("""tem que confiar na base também|o elenco é bom, falta encaixe|reforço sem dinheiro é ilusão|
contratar por contratar só enche a folha|prefiro esperar alguém bom do que trazer qualquer um|
o problema não é falta de jogador, é de padrão|melhor ajustar as contas antes de gastar"""),
        'zoeira': L("""já pedi no amigo secreto|vem aí o Pelé 2 kkkk|diretoria tá contratando no FIFA só|
o reforço vai ser o roupeiro novo|com o dinheiro que tem dá pra contratar o mascote"""),
    },
    'escalacao': {
        'posts': L("""quem vocês colocam de titular no próximo jogo?|{jogador} tem que começar jogando|
[DMA]eu tirava o {jogador} e colocava alguém mais rápido|três zagueiros ou linha de quatro? opinem|[G]{jogador} tem que ser o goleiro titular, sem discussão|[D]{jogador} na zaga dá outra segurança|[A]quero o {jogador} de referência lá na frente|[M]{jogador} tem que jogar de volante, ele organiza|
o {tecnico} precisa testar o time com dois volantes|[M]time ideal: goleiro, linha de quatro e {jogador} solto no meio|
quero ver o {jogador} de titular pelo menos uma vez|meio-campo precisa de mais saída de bola|
alguém mais acha que o time rende mais no 4-3-3?|deixa o {jogador} no banco e vê o que acontece|
time que ganhou não se mexe, ou mexe?"""),
        'concordo': L("""{jogador} titular sempre|concordo, o time fica mais leve|eu também faria isso|
4-3-3 é o que mais encaixa nesse elenco|faz sentido|dá pra testar sim|apoiado, precisa mudar algo"""),
        'discordo': L("""{jogador} ainda não tá pronto|não mexe no que tá funcionando|não concordo, perde marcação|
o {tecnico} vê o treino, a gente não|mudar esquema agora é arriscado|discordo total, o meio fica aberto"""),
        'zoeira': L("""me coloca de lateral que eu resolvo|técnico de sofá ativado kkk|eu no Football Manager já ganhei tudo com essa escalação|
cada torcedor um técnico, como sempre"""),
    },
    'estadio': {
        'posts': L("""ingresso comprado, bora lotar ✅|quem vai pro jogo? partiu estádio|
sócio-torcedor tá valendo muito a pena, recomendo|torcida tem que fazer a parte dela no próximo jogo|
festa na arquibancada vai ser linda, preparem as bandeiras|casa cheia faz diferença, bora|
já separei a camisa da sorte|vou levar meu filho pela primeira vez no estádio 🥹|
a fila do ingresso tá enorme, bom sinal|esse estádio lotado é outro time"""),
        'concordo': L("""bora!!|tô indo|já garanti o meu|vai ser lindo|casa cheia empurra o time|
leva sim, ele nunca vai esquecer|é nossa parte, vamos fazer|vou de caravana"""),
        'discordo': L("""ingresso tá muito caro pra esse futebol|com esse preço só vou quando o time melhorar|
o acesso ao estádio é horrível, tinha que melhorar isso|eu vou, mas o time precisa corresponder"""),
        'zoeira': L("""vou e vou rouco|minha esposa já sabe que domingo sou do {clube}|
camisa da sorte não lava há 3 jogos kkkk|vou de pijama se precisar"""),
    },
    'camisa': {
        'posts': L("""camisa nova do {clube} tá linda demais|o uniforme dessa temporada ficou bonito|
manto do {clube} com {empresa} ficou bonito hein|achei a camisa reserva mais bonita que a titular|
alguém sabe onde acha a camisa nova mais barata?|esse uniforme vai ficar marcado|
a terceira camisa podia ser mais ousada|comprei a camisa nova, tô me sentindo jogador"""),
        'concordo': L("""muito bonita mesmo|top demais|já comprei a minha|clássica, do jeito que tem que ser|
ficou elegante|melhor camisa dos últimos anos"""),
        'discordo': L("""achei sem graça|muito patrocínio, poluiu|preferia a do ano passado|preço tá absurdo|
bonita, mas o tecido é fraco"""),
        'zoeira': L("""camisa bonita não ganha jogo kkk|vai jogar com ela no sábado? kkk|
a minha já desbotou na primeira lavagem"""),
    },
    'apoio_tecnico': {
        'posts': L("""{tecnico} tem meu apoio|o trabalho do {tecnico} tá aparecendo, paciência|
dá tempo pro {tecnico}, time tá evoluindo|gosto do jeito que o {tecnico} fala com o grupo|
o {tecnico} pegou o time numa situação difícil, tá fazendo milagre|time tem cara agora, mérito do {tecnico}|
renova com o {tecnico} já|primeiro técnico em anos que tem uma ideia clara"""),
        'concordo': L("""concordo, tá evoluindo|apoio total|time tem padrão agora|o grupo fecha com ele|
deixa o homem trabalhar|merece respeito"""),
        'discordo': L("""ainda não me convenceu|tem crédito, mas não é infinito|as substituições dele me irritam|
gosto dele, mas é teimoso com algumas escolhas|vamos ver nos jogos grandes"""),
        'zoeira': L("""já tem até música pro {tecnico}? kkk|o homem é o novo professor Pardal|
manda o {tecnico} pra seleção logo"""),
    },
    'critica_tecnico': {
        'posts': L("""o {tecnico} já deu o que tinha que dar|alguém entende as escolhas do {tecnico}?|
time sem padrão, a culpa é do técnico|o {tecnico} insiste em quem não rende|já passou da hora de mudar o comando|
o {tecnico} é teimoso demais|sem plano B nenhum, sempre a mesma coisa|esse técnico não tem pulso com o elenco"""),
        'concordo': L("""concordo|teimosia vai derrubar ele|tá perdido|não tem mais ambiente|toda semana o mesmo erro|
já devia ter saído"""),
        'discordo': L("""o elenco é limitado, não é culpa só dele|trocar técnico toda hora não resolve|
dá tempo pro cara trabalhar|ele tirou leite de pedra até aqui|o problema é a diretoria, não o técnico"""),
        'zoeira': L("""o {tecnico} tá jogando de olho fechado|nem o GPS acha esse time|
contrata o técnico do meu time de várzea"""),
    },
    'jogador_bom': {
        'posts': L("""{jogador} tá jogando muita bola|{jogador} é o melhor do elenco disparado|renova com o {jogador} já!|
{jogador} merece convocação|que fase do {jogador}, impressionante|o {jogador} carrega esse time|
{jogador} foi o melhor em campo de novo|tô com medo de levarem o {jogador} na janela|[G]{jogador} fechou o gol de novo 🧤|[G]que goleiro, {jogador} pega tudo|[D]{jogador} não perde uma dividida, que zagueiro|[D]com o {jogador} atrás eu durmo tranquilo|[M]{jogador} dita o ritmo do meio-campo|[M]todo passe bom passa pelo pé do {jogador}|[A]{jogador} não para de fazer gol|[A]{jogador} na frente é gol certo"""),
        'concordo': L("""disparado|craque|merece demais|tem que blindar ele|melhor contratação dos últimos anos|
o cara é diferenciado"""),
        'discordo': L("""bom jogador, mas some nos jogos grandes|tá bem, mas melhor do elenco é exagero|
ainda precisa provar mais|oscila muito"""),
        'zoeira': L("""já tô fazendo a camisa personalizada|{jogador} pra presidente|quero ser o {jogador} quando crescer"""),
    },
    'jogador_ruim': {
        'posts': L("""{jogador} não pode ser titular|até quando o {jogador} vai jogar?|[MA]{jogador} sumiu nos últimos jogos|
{jogador} precisa de banco pra respirar|não entendo a insistência com o {jogador}|
o {jogador} tá devendo muito|{jogador} errou tudo de novo, impressionante|[G]{jogador} tomou mais um frango, não dá|[G]cada bola alta é um susto com o {jogador} no gol|[D]{jogador} deixou o atacante passar fácil de novo|[D]toda vez que o {jogador} sai pro bote a defesa fica exposta|[M]{jogador} não acerta um passe|[M]{jogador} só toca de lado, não cria nada|[A]{jogador} perdeu gol feito de novo|[A]atacante que não faz gol, né {jogador}"""),
        'concordo': L("""concordo|banco nele|tá devendo mesmo|não rende mais|já passou da hora|precisa de concorrência"""),
        'discordo': L("""calma, fase ruim todo mundo tem|ele joga machucado às vezes, ninguém sabe|
o time não ajuda ele|já resolveu muito jogo, tem crédito|não vou crucificar|ele faz o trabalho sujo que ninguém vê"""),
        'zoeira': L("""o {jogador} tá jogando com o pé trocado|deve tá jogando de ressaca kkk|
o {jogador} assinou com o adversário e esqueceu de avisar"""),
    },
    'lesao': {
        'posts': L("""alguém sabe se {jogador} volta pro próximo jogo?|perder o {jogador} agora é um baque|
força, {jogador}! volta logo 🙏|DM do {clube} precisa ser revisto, muita lesão|[MA]{jogador} faz muita falta, sem ele o time não cria|[G]sem o {jogador} no gol dá até medo|[D]sem o {jogador} a zaga fica perdida|[A]sem o {jogador} quem vai fazer os gols?|
saiu alguma informação sobre o {jogador}?|recupera com calma, {jogador}, não força"""),
        'concordo': L("""faz muita falta|torcendo pela recuperação|volta forte 🙏|sem ele o time perde muito|
melhor voltar 100% do que forçar"""),
        'discordo': L("""o elenco tem reposição, não é o fim do mundo|chance pra outro mostrar serviço|
já tava jogando mal antes da lesão, sinceramente"""),
        'zoeira': L("""DM do {clube} parece hospital de guerra|vou mandar um chá de boldo pro {jogador}"""),
    },
    'rival': {
        'posts': L("""rival tá muito quieto essa semana kkk|cadê os torcedores rivais que tavam falando grosso?|
o rival perdeu de novo e eu dei risada|semana boa é semana com rival perdendo|
nunca vi um rival tão desesperado|torcer contra o rival também é amor ao {clube}"""),
        'concordo': L("""kkkkkk sumiram|deixa eles|semana perfeita|melhor coisa|tão escondidos"""),
        'discordo': L("""foca no {clube}, rival é rival|cuidado que a gente também tá devendo|
melhor olhar pro próprio quintal"""),
        'zoeira': L("""já mandei figurinha pro meu cunhado|eles tão de luto até agora|o grupo da família tá pegando fogo kkk"""),
    },
    'base': {
        'posts': L("""tem que dar chance pros garotos da base|tem um menino na base que é diferenciado|
a base do {clube} sempre revela, confia|time grande valoriza a base|subir uns dois da base não custa nada|
o sub-20 tá jogando melhor que o profissional kkk"""),
        'concordo': L("""apoiado|base é o futuro|vamos dar minutagem pros meninos|já vi jogar, é bom mesmo|
mais barato e com amor à camisa"""),
        'discordo': L("""jogar menino em momento ruim queima o garoto|base é base, profissional é outra coisa|
melhor subir aos poucos"""),
        'zoeira': L("""sobe o meu sobrinho que ele joga muito kkk|tem garoto na base com 1,90 e 14 anos, confia"""),
    },
    'ansiedade': {
        'posts': L("""saudade de ver o {clube} jogar, cadê o jogo 😅|semana sem jogo é muito longa|
contando as horas pro próximo jogo|já tô ansioso pro próximo jogo|dia de jogo chega logo pfv|
sonhei com gol do {clube} essa noite kkkk"""),
        'concordo': L("""demais|tô igual|semana infinita|chega logo domingo|só penso nisso|ansiedade lá em cima|
conto as horas também|nem durmo direito em semana de jogo|já tô com a camisa separada|bora logo|
semana passa devagar quando não tem jogo|quero ver esse time em campo"""),
        'discordo': L("""melhor assim, time descansa|semana cheia de treino é bom|deixa o time ajustar"""),
        'zoeira': L("""vou assistir reprise de jogo antigo kkk|semana sem {clube} é semana sem sentido"""),
    },
    'treino': {      # respostas aos posts do dia a dia do CT publicados pelo clube
        'posts': L("""treino fechado de novo, o que será que vem aí 👀|bom ver o grupo sorrindo no CT"""),
        'concordo': L("""bora!!|grupo fechado é isso|ambiente bom aparece em campo|que venha o próximo jogo|
treino forte, jogo fácil|gosto de ver o time trabalhando|o {tecnico} tá cobrando, dá pra ver|esse elenco tá unido|
foco total 💪|vamo que vamo|isso que a gente quer ver|time com fome"""),
        'discordo': L("""treino bonito, quero ver no jogo|post de treino não ganha ponto|
menos vídeo e mais resultado|mostra o treino de finalização que tá fazendo falta|
treinar todo mundo treina, tem que jogar|legal, mas e o reforço?"""),
        'zoeira': L("""quem é o cara caindo no fundo do vídeo kkkk|o goleiro tomou caneta no treino?|
cadê o vídeo do rachão, queremos resenha|esse sol aí tá de graça? kkk|o lateral tá correndo mais no treino que no jogo"""),
    },
    'patro': {
        'posts': L("""{empresa} no manto do {clube}, gostei 👏|{empresa} patrocinando o {clube}?? agora vai|
vou trocar de {setor} só por causa da {empresa} kkkk|parceria top, {empresa} 💚|
a marca da {empresa} combinou com a camisa|bom ver empresa grande acreditando no {clube}|
quero ver esse dinheiro da {empresa} virar reforço"""),
        'concordo': L("""ficou top|boa parceria|😍|show|combinou demais|marca forte no peito"""),
        'discordo': L("""agora é contratar|camisa tá virando outdoor|patrocínio bom é o que paga em dia|
espero que o valor seja bom"""),
        'zoeira': L("""cadê o desconto pra torcedor?|vou pedir camisa de graça kkk|já virei cliente fiel"""),
    },
}
# reação aos posts do técnico (mantido para coletiva/outras partes)
TECNICO = {
    'tecnico_bom': L("""boa, professor! 👏|confiamos em você {tecnico}|é isso, comandante|tamo junto professor|
assim que se fala 🔥|o cara entende o grupo|palavra de quem sabe o que faz|time tem a sua cara|respeito demais"""),
    'tecnico_ruim': L("""fala menos e ganha mais|discurso bonito, mas cadê resultado?|vamos ver em campo|
palavras não ganham jogo|hmm, veremos|todo técnico fala isso antes de cair|prova em campo"""),
}

# pesos das posturas nas respostas, por assunto (concordo, discordo, zoeira)
POSTURA = {'euforia': (6, 2, 2), 'feliz': (6, 2, 1), 'neutro': (5, 3, 2), 'chateado': (6, 3, 1), 'revolta': (6, 3, 1)}


def respostas(tema, mem, rnd, autor, perfis, v, n):
    """n respostas coerentes com o assunto, cada uma de um torcedor diferente."""
    b = TORCIDA.get(tema) or TORCIDA['neutro']
    pesos = POSTURA.get(tema, (5, 3, 2))
    outros = [p for p in perfis if p[0] != autor]
    rnd.shuffle(outros)
    out, vistos = [], set()
    for i in range(min(n, len(outros))):
        post = rnd.choices(['concordo', 'discordo', 'zoeira'], pesos)[0]
        t = humanizar(mem.escolher(f'r:{tema}:{post}', b[post], rnd, v), rnd)
        if t in vistos:
            continue
        vistos.add(t)
        h, nome = outros[i]
        out.append({'autor': h, 'nome': nome, 'texto': t,
                    'curtidas': int(rnd.paretovariate(1.4) * rnd.randint(3, 60)) if post != 'zoeira'
                    else rnd.randint(20, 900)})
    return out


def temas_semana(torcida, tem_lesao):
    """Assuntos da semana conforme o humor da torcida (cada um com peso)."""
    if torcida >= 65:
        t = {'apoio_tecnico': 3, 'jogador_bom': 3, 'estadio': 3, 'ansiedade': 2, 'camisa': 2, 'rival': 2, 'base': 1,
             'escalacao': 2, 'reforco': 1}
    elif torcida >= 45:
        t = {'reforco': 3, 'escalacao': 3, 'jogador_bom': 2, 'jogador_ruim': 2, 'estadio': 2, 'camisa': 1,
             'ansiedade': 2, 'base': 2, 'apoio_tecnico': 1, 'critica_tecnico': 1, 'rival': 1}
    else:
        t = {'critica_tecnico': 3, 'reforco': 3, 'jogador_ruim': 3, 'escalacao': 2, 'base': 2, 'apoio_tecnico': 1,
             'estadio': 1}
    if tem_lesao:
        t['lesao'] = 4
    return t


# ---------------- diretoria ----------------
PRESIDENTE = {
    'boas_vindas': L("""Bem-vindo ao comando do {clube}. A diretoria espera {meta_txt}. Conte com o nosso apoio.|
Seja bem-vindo, {tecnico}. Nossa meta é {meta_txt}. Estamos juntos nessa caminhada.|
{tecnico}, é um prazer tê-lo conosco. O conselho aprovou seu nome por unanimidade. A meta: {meta_txt}.|
Bem-vindo à casa. Aqui a cobrança é grande, mas o apoio também. Esperamos {meta_txt}.|
Professor, o {clube} confia no seu trabalho. Combinamos {meta_txt}; o resto é com você e com o grupo."""),
    'elogio': L("""Estamos muito satisfeitos com o desempenho recente. Siga assim e o {clube} vai longe.|
O momento é excelente. A diretoria confia plenamente no seu trabalho.|
Parabéns pela sequência, {tecnico}. A torcida está empolgada e os patrocinadores também.|
O conselho elogiou seu trabalho na última reunião. Continue assim.|
{tecnico}, passei no CT ontem e o clima é outro. Isso é mérito seu. Parabéns.|
Recebi ligações de conselheiros só para elogiar o time. Faz tempo que isso não acontecia aqui.|
O {clube} voltou a ser respeitado. Siga com os pés no chão, mas aproveite o momento.|
Os números falam por si. A diretoria está contigo, professor.|
Patrocinadores, sócios e conselho: todo mundo satisfeito. Não lembro da última vez que isso aconteceu."""),
    'cobranca': L("""A sequência recente preocupa a diretoria. Esperamos uma reação imediata.|
Os resultados não estão à altura do {clube}. Precisamos de mais.|
{tecnico}, a torcida está impaciente e o conselho também. Precisamos de vitórias.|
Os patrocinadores estão perguntando sobre o momento do time. Precisamos virar essa chave.|
Professor, não é hora de pânico, mas é hora de reação. O que você precisa de nós?|
O conselho se reuniu ontem e o assunto foi um só: o desempenho do time. Conto com uma resposta em campo.|
Recebi muitas reclamações de sócios esta semana. Sei que o trabalho é longo, mas o resultado precisa aparecer.|
Não vou mentir: há pressão para mudanças. Por enquanto, sigo bancando seu trabalho.|
{tecnico}, o momento pede mais intensidade do grupo. Converse com os líderes do elenco."""),
    'ultimato': L("""A paciência da diretoria está no limite. Sem reação nos próximos jogos, teremos que rever o comando técnico.|
Sejamos francos: a situação é insustentável. Precisamos de vitórias já.|
{tecnico}, fiz o que pude para segurar o conselho. Agora depende só dos próximos resultados.|
Não há mais margem. Os próximos dois jogos vão decidir o futuro da comissão técnica.|
Respeito seu trabalho, mas o {clube} não pode esperar mais. Preciso de uma resposta imediata."""),
    'meta_financeira': L("""Ótimo trabalho no mercado de patrocínios: {valor} por temporada em contratos. O caixa agradece.|
Batemos a meta comercial: {valor} por temporada. Excelente negociação.|
O departamento financeiro comemorou: {valor} por temporada em patrocínios. Isso muda o nosso planejamento.|
Com {valor} anuais em contratos, o {clube} respira. Parabéns pela condução."""),
    'tabela_boa': L("""Ver o {clube} em {pos}º na tabela é motivo de orgulho. Mantenha o foco.|
A posição na tabela ({pos}º) agrada o conselho. Siga nesse ritmo.|
{pos}º lugar. Era exatamente o que esperávamos. Agora é manter.|
Abri a tabela hoje cedo e sorri: {clube} em {pos}º. Vamos sustentar isso até o fim.|
O {pos}º lugar tem valor, mas não vamos nos acomodar. A diretoria está satisfeita."""),
    'tabela_ruim': L("""O {pos}º lugar não é aceitável para o {clube}. Precisamos subir na tabela.|
A tabela preocupa: {pos}º colocado. Conto com uma reação rápida.|
Estar em {pos}º não condiz com o investimento feito. Precisamos reagir.|
{tecnico}, a posição na tabela ({pos}º) está tirando o sono do conselho.|
Com o {clube} em {pos}º, a cobrança vai aumentar. Vamos virar essa página logo."""),
}


# ---------------- migração dos posts antigos ----------------
def _tema_de(texto):
    import re
    t = texto.strip().lower()
    for tema, b in TORCIDA.items():
        for modelo in b['posts']:
            from . import posicao
            rx = re.escape(posicao.limpar(modelo).lower())
            rx = re.sub(r'\\\{[a-z_]+\\\}', '.*', rx)
            if re.fullmatch(rx, t):
                return tema
    return None


def migrar(state, clube):
    """Uma vez só: os posts antigos da torcida ganham assunto, nomes e respostas do banco novo."""
    m = state.setdefault('mundo', {})
    if m.get('vozes_v', 0) >= 1:
        return
    m['vozes_v'] = 1
    mem = Memoria(state)
    perfis = torcedores(clube)
    nomes = dict(perfis)
    for i, p in enumerate(m.get('posts', [])):
        if p.get('assessor') or p.get('tecnico') or p.get('tema') or p.get('humor') == 'classico':
            continue
        tema = _tema_de(p.get('texto', '')) or (p.get('humor') if p.get('humor') in TORCIDA else None)
        if not tema:
            continue
        rnd = random.Random(f"mig|{p.get('data')}|{p.get('autor')}|{i}")
        p['tema'] = tema
        if p.get('autor') in nomes:
            p['nome'] = nomes[p['autor']]
        oficiais = [r for r in p.get('respostas', []) if r.get('oficial')]
        el = state.get('elenco_nomes') or ['o camisa 10']
        v = {'clube': clube, 'CLUBE': clube.upper(), 'empresa': p.get('empresa', ''),
             'tecnico': state.get('cfg_tecnico') or 'o técnico', 'jogador': p.get('jogador') or rnd.choice(el)}
        p['respostas'] = oficiais + respostas(tema, mem, rnd, p.get('autor'), perfis, v, len(p.get('respostas', [])) - len(oficiais))
