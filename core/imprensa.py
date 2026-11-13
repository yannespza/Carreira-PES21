"""Imprensa viva: jornalistas com personalidade própria. Cada um escreve matérias e comenta nos programas
de debate do seu jeito (crítico, irônico, setorista, pilhado, analista tático, veterano), e eles se
revezam nas perguntas da coletiva."""
import random, hashlib

JORNALISTAS = {
    'duarte': {
        'nome': 'Marcelo Duarte', 'papel': 'O crítico', 'programa': 'Linha Final', 'veiculo': 'ESPN',
        'cor': '#c0392b', 'perfil': 'Analítico e duro. Cobra gestão, planejamento e não aceita desculpa. '
        'Ironia seca, números na ponta da língua, desconfia de empolgação.'},
    'ferraz': {
        'nome': 'Paulo Ferraz', 'papel': 'O irônico', 'programa': 'Bate-Bola', 'veiculo': 'Rádio Bandeirantes',
        'cor': '#8e44ad', 'perfil': 'Educado, cerebral e cortante. Compara o que o técnico disse ontem com o '
        'que faz hoje e cobra coerência com ironia fina.'},
    'lacerda': {
        'nome': 'Jorge Lacerda', 'papel': 'O setorista', 'programa': 'Canal do Lacerda', 'veiculo': 'Setorista',
        'cor': '#2980b9', 'perfil': 'Vive no CT. Calmo, bem informado, fala em "apurei" e "fontes do clube". '
        'Traz bastidor, departamento médico e mercado antes de todo mundo.'},
    'pilha': {
        'nome': 'Tiago "Pilha" Moura', 'papel': 'O pilhado', 'programa': 'Resenha Pilhada', 'veiculo': 'YouTube',
        'cor': '#f39c12', 'perfil': 'Torcedor-comunicador. Tudo é oito ou oitenta: vitória é título, derrota '
        'é crise. Grita, exagera, cria bordão e corneta sem dó.'},
    'renata': {
        'nome': 'Renata Lobo', 'papel': 'A analista tática', 'programa': 'Prancheta', 'veiculo': 'Globo Esporte',
        'cor': '#16a085', 'perfil': 'Tranquila e técnica. Fala de encaixe, linhas, pressão pós-perda e '
        'ocupação de espaço. Raramente levanta a voz.'},
    'arnaldo': {
        'nome': 'Arnaldo Viana', 'papel': 'O veterano', 'programa': 'Mesa Redonda de Domingo', 'veiculo': 'TV Gazeta',
        'cor': '#7f8c8d', 'perfil': 'Décadas de microfone. Saudosista, conta causo, compara com times do '
        'passado e defende o "futebol raiz".'},
}

# categoria da notícia -> situação do comentário
SIT = {'goleada': 'goleada', 'vitoria': 'bom', 'seq_vitorias': 'bom', 'invicto': 'bom', 'lider': 'bom',
       'lider_segue': 'bom', 'g4': 'bom', 'sobe': 'bom', 'empate': 'neutro', 'outro_lider': 'neutro',
       'derrota': 'ruim', 'seq_derrotas': 'ruim', 'z4': 'ruim', 'cai': 'ruim', 'vexame': 'vexame',
       'contrato': 'mercado', 'contrato_grande': 'mercado', 'rescisao': 'mercado', 'rumor_patro': 'mercado',
       'lesao': 'lesao', 'retorno': 'elenco', 'evento': 'elenco', 'jog_elogio': 'elenco', 'jog_critica': 'elenco',
       'diretoria_cobra': 'diretoria', 'diretoria_elogia': 'diretoria', 'coletiva': 'coletiva',
       'bastidores': 'bastidores'}

C = {
    'duarte': {
        'goleada': ["Goleada é bonito, mas eu quero ver isso contra time grande. {placar} no {adv} não prova nada ainda.",
                    "Placar elástico esconde problema. Olha quantas chances o {adv} criou antes do primeiro gol.",
                    "Parabéns pelo {placar}. Agora, uma andorinha só não faz verão, e esse elenco tem buracos."],
        'bom': ["Ganhou, ótimo. Mas jogou mal por boa parte do tempo e o resultado mascara isso.",
                "O {clube} venceu apesar do {tecnico}, não por causa dele. Ainda não vejo um modelo de jogo claro.",
                "Vitória é obrigação para um clube com essa folha. Não tem o que comemorar demais."],
        'neutro': ["Empate que diz muito: time previsível, sem ideia quando precisa propor.",
                   "Um ponto que não serve para nada se o objetivo é brigar lá em cima."],
        'ruim': ["Não é azar. É planejamento ruim. Montaram um elenco desequilibrado e agora cobram o técnico.",
                 "O {clube} perdeu e mereceu perder. Faltou repertório, faltou intensidade, faltou tudo.",
                 "Eu avisei lá atrás: esse elenco não tem reposição. A conta chegou."],
        'vexame': ["Vexame. Não tem outra palavra. A diretoria precisa explicar o que está acontecendo no {clube}.",
                   "Tomar {placar} do {adv} é inadmissível. Isso é falta de comando dentro e fora de campo."],
        'mercado': ["Dinheiro de patrocínio é bem-vindo, mas quero ver onde vai ser investido. Clube brasileiro adora gastar mal.",
                    "Contrato bom no papel. Agora, cumpra as metas, senão vira manchete negativa em seis meses."],
        'lesao': ["Mais um no departamento médico. Isso é carga mal administrada, não é coincidência.",
                  "Lesão no treino diz muito sobre a preparação física. Alguém precisa olhar esses números."],
        'elenco': ["Um jogador não resolve, nem afunda time. O problema do {clube} é coletivo.",
                   "Elogio de uma semana vira cobrança na outra. Calma com o oba-oba."],
        'diretoria': ["A diretoria cobra o técnico em público, mas quem montou esse elenco foi ela.",
                      "Diretoria que fala demais costuma trabalhar de menos."],
        'bastidores': ["Bastidor agitado é sintoma. Clube organizado não vaza tanta coisa.",
                       "Muita fumaça. Quero ver fato, não especulação."],
        'coletiva': ["O técnico falou bonito na coletiva. Discurso eu também faço; quero ver em campo.",
                     "Respostas evasivas de novo. Coletiva virou exercício de não dizer nada."],
    },
    'ferraz': {
        'goleada': ["Curioso: semana passada o problema era o elenco curto. Hoje o mesmo elenco fez {placar}.",
                    "O {adv} colaborou bastante, convenhamos. Mas mérito de quem soube aproveitar."],
        'bom': ["O técnico disse que o time estava em evolução. Pelo menos hoje o placar concordou com ele.",
                "Vitória com a cara do treinador: pragmática. Se é sustentável, é outra conversa.",
                "Três pontos e um alívio. A pergunta é: o que mudou de verdade?"],
        'neutro': ["Empate é aquele resultado que todo mundo consegue defender. Inclusive o técnico, na coletiva.",
                   "Ficou no meio do caminho, como a ideia de jogo."],
        'ruim': ["O discurso de 'estamos no caminho certo' ficou difícil de sustentar depois de hoje.",
                 "Interessante como a culpa muda de endereço a cada derrota. Hoje foi do gramado?",
                 "Perder acontece. Perder sem saber por quê é que preocupa."],
        'vexame': ["Imagino a coletiva: 'precisamos rever algumas coisas'. Todas, eu diria.",
                   "{placar}. Nem o mais pessimista dos torcedores escreveria esse roteiro."],
        'mercado': ["Patrocínio novo, camisa nova, promessa nova. Resta saber se o futebol acompanha o marketing.",
                    "A {empresa} entra no {clube}. Que tenha mais paciência que alguns dirigentes."],
        'lesao': ["Desfalque no pior momento. Ou no melhor momento para justificar o próximo tropeço.",
                  "O departamento médico vai ganhar mais minutos de imprensa que o ataque."],
        'elenco': ["O mesmo jogador que era 'peça-chave' há um mês agora vai para o banco. Futebol é memória curta.",
                   "Fase. Todo mundo vive. A diferença é como o clube administra."],
        'diretoria': ["A diretoria 'confia no trabalho'. Historicamente, essa frase dura umas três rodadas.",
                      "Quando o presidente elogia demais, eu fico preocupado pelo técnico."],
        'bastidores': ["Muita gente falando em off. Pouca gente assinando embaixo.",
                       "O que sai do CT esta semana diz mais do que qualquer escalação."],
        'coletiva': ["Ele respondeu sem responder. Uma arte.",
                     "Gostei da franqueza. Vamos ver se ela sobrevive à próxima derrota."],
    },
    'lacerda': {
        'goleada': ["No vestiário o clima é de festa, apurei que o {tecnico} liberou o grupo amanhã.",
                    "Fontes da comissão me disseram que esse placar era treinado: pressão alta na saída do {adv}."],
        'bom': ["Bastidor: o elenco abraçou a ideia do {tecnico}. A vitória fortalece muito ele internamente.",
                "Apurei que a diretoria ficou satisfeita. Ninguém fala em mudança.",
                "Clima tranquilo no CT. A semana vai ser de ajustes, não de cobrança."],
        'neutro': ["No clube o empate foi visto como 'aceitável'. Mas há quem cobre mais coragem fora de casa.",
                   "Informação: o {tecnico} já sabe quem vai mexer para o próximo jogo."],
        'ruim': ["O clima ficou pesado. Apurei que houve conversa dura no vestiário depois do jogo.",
                 "Fontes da diretoria garantem que o {tecnico} segue. Mas a paciência não é infinita.",
                 "Teve jogador cobrando jogador. Não vou dizer nomes, mas a cobrança foi forte."],
        'vexame': ["Reunião de emergência marcada para amanhã cedo no CT. O ambiente está muito tenso.",
                   "Apurei que o presidente nem desceu ao vestiário. Isso diz tudo."],
        'mercado': ["Confirmo: o acordo com a {empresa} estava sendo costurado havia semanas. Valores acima do anterior.",
                    "Pelo que apurei, a {empresa} quer exposição no peito e tem pressa para fechar."],
        'lesao': ["Informação do departamento médico: {jogador} faz exames e a previsão é de {n} dias fora.",
                  "Apurei que a lesão de {jogador} aconteceu num treino de finalização. O clube vai preservar o atleta."],
        'elenco': ["Pelo que apurei, {jogador} conversou com o {tecnico} esta semana. O papo foi bom.",
                   "Bastidor: {jogador} está incomodado com a situação, mas não pede para sair."],
        'diretoria': ["Fontes do conselho: a cobrança é real, mas ninguém fala em demissão agora.",
                      "O presidente tem respaldo do conselho. As metas foram reforçadas em reunião."],
        'bastidores': ["Informação exclusiva: o clube monitora reforços para a próxima janela.",
                       "Apurei que o CT passa por melhorias. O {tecnico} pediu e foi atendido."],
        'coletiva': ["Depois da coletiva, o {tecnico} ainda conversou com a diretoria por quase uma hora.",
                     "A resposta do técnico repercutiu no elenco. Teve jogador que gostou."],
    },
    'pilha': {
        'goleada': ["ACABOOOOU! {placar} NO {adv}! É CAMPEÃO! Pode separar a faixa que esse time não perde mais! 🔥🔥",
                    "Meu Deus do céu! Que time é esse?! {tecnico} gênio, gênio, GÊNIO! ⚽⚽⚽",
                    "EU AVISEI! Eu falei na live que ia ser goleada! Chupa, secador! 😂"],
        'bom': ["Ganhou, tá ganho! O {clube} tá voando, quem não tá vendo é porque não quer! 🚀",
                "Vitória com sofrimento é a mais gostosa! Coração na boca mas três pontos no bolso!",
                "Respeita o {clube}! RES-PEI-TA! 🦅"],
        'neutro': ["Empatar com o {adv}?! Pelo amor de Deus, eu tô passando mal aqui! 😤",
                   "Um pontinho... É, galera, melhor que nada. Mas eu tô PISTOLA com o segundo tempo."],
        'ruim': ["ACABOU! Fora todo mundo! Tira o {tecnico}, tira a diretoria, tira até o roupeiro! 😡",
                 "Vergonha! VERGONHA! Esse time não tem alma, não tem raça, não tem nada!",
                 "Eu desisto. Vou desligar a live. Mentira, não vou, mas tô com vontade."],
        'vexame': ["{placar}?!? {placar}??? Eu tô sem palavras. Mentira, tenho várias e nenhuma pode ser dita aqui. 🤬",
                   "Isso não é derrota, é humilhação! Quero ver quem vai ter coragem de dar entrevista!"],
        'mercado': ["A {empresa} chegou chegando! Agora é dinheiro no bolso e reforço de peso, né, diretoria? 💰",
                    "Camisa com patrocínio novo! Já quero a minha! Mas quero também CAMISA 9, hein!"],
        'lesao': ["Machucou NO TREINO?! Gente, como é que machuca no treino?! Isso é praga de secador!",
                  "Sem o {jogador} a gente tá perdido! Corre, departamento médico, corre! 🏃"],
        'elenco': ["{jogador} é MONSTRO! Craque! Seleção já! 🐐", "{jogador}? Esquece. Banco. Agora."],
        'diretoria': ["Diretoria, abre o cofre e traz reforço! Chega de conversa!",
                      "O presidente falando bonito... quero ver é contratação, presidente!"],
        'bastidores': ["Tô sabendo de coisa grande chegando aí... confia no Pilha! 👀",
                       "Ih, o bastidor tá pegando fogo! Pipoca na mão, galera! 🍿"],
        'coletiva': ["O {tecnico} mandou o recado na coletiva! Gostei! Treinador tem que ter personalidade!",
                     "Coletiva morna, igual o time. Acorda, professor!"],
    },
    'renata': {
        'goleada': ["O {clube} encaixou a pressão pós-perda e o {adv} não conseguiu sair jogando. Os gols vieram daí.",
                    "Repara na amplitude: os pontas abertos esticaram a última linha do {adv} o jogo todo."],
        'bom': ["Vitória construída no meio-campo. A linha de cinco na saída de bola deu superioridade.",
                "Taticamente foi um jogo maduro: o time soube baixar o bloco quando precisou.",
                "O {tecnico} corrigiu no intervalo a distância entre as linhas. Fez diferença."],
        'neutro': ["Faltou profundidade. O {clube} rodou a bola, mas quase não atacou o espaço atrás da defesa.",
                   "Empate justo. Os dois times se anularam no meio."],
        'ruim': ["O problema não é só técnico. O time ficou espaçado e o {adv} explorou as costas dos laterais.",
                 "Muitas perdas de bola no terço inicial. Contra uma pressão alta, isso custa caro.",
                 "Faltou um plano B. Quando o {adv} fechou o corredor central, o {clube} não teve resposta."],
        'vexame': ["Desorganização total na transição defensiva. Cada contra-ataque do {adv} era meio gol.",
                   "Linha defensiva alta sem pressão na bola. É convite para tomar gol."],
        'mercado': ["Do ponto de vista de campo, o dinheiro novo precisa virar um volante de saída e um ponta de profundidade.",
                    "Receita maior permite planejar o elenco por função, não por nome."],
        'lesao': ["A ausência de {jogador} muda a estrutura: o {tecnico} perde uma peça de equilíbrio.",
                  "Sem {jogador}, a tendência é o time mudar o desenho para não perder o meio."],
        'elenco': ["{jogador} rende mais quando joga por dentro. Aberto, ele some.",
                   "O momento de {jogador} tem a ver com função. Não é só questão de vontade."],
        'diretoria': ["Pressão de diretoria costuma encurtar o trabalho. E trabalho curto raramente vira modelo de jogo.",
                      "Cobrança é normal. O importante é a comissão manter a ideia."],
        'bastidores': ["Mais do que reforço, o time precisa de treino. Calendário apertado atrapalha a evolução.",
                       "Vale observar o que o {tecnico} vai testar nos treinos desta semana."],
        'coletiva': ["Gostei da leitura do técnico. Ele entendeu onde o time sofreu.",
                     "A explicação tática dele bate com o que se viu em campo."],
    },
    'arnaldo': {
        'goleada': ["No meu tempo, goleada assim a gente comemorava com chope no bar da esquina. Bonito de ver!",
                    "Me lembrou aqueles times de antigamente, que entravam em campo e o adversário já tremia."],
        'bom': ["Vitória com raça, como antigamente. É disso que o torcedor gosta.",
                "O {clube} tem camisa. E camisa pesa, meu amigo."],
        'neutro': ["Empate fora de casa, antigamente, era bom resultado. Hoje todo mundo quer tudo.",
                   "Faltou aquele camisa 10 clássico, que pegava a bola e resolvia."],
        'ruim': ["Antigamente o jogador sentia a camisa. Hoje é muito celular e pouca vontade.",
                 "Já vi o {clube} cair e levantar muitas vezes. Mas esse time precisa de liderança."],
        'vexame': ["Em quarenta anos de microfone, poucas vezes vi uma coisa dessas. Triste.",
                   "Isso aí antigamente custava o emprego de muita gente no dia seguinte."],
        'mercado': ["No meu tempo camisa não tinha patrocínio. Mas tudo bem, o dinheiro ajuda a pagar o craque.",
                    "Patrocínio é bom, mas não entra em campo."],
        'lesao': ["Antigamente o sujeito jogava com o tornozelo enfaixado. Hoje é tudo ressonância.",
                  "Lesão no treino... no meu tempo o treino era um coletivo e uma pelada."],
        'elenco': ["{jogador} me lembra aqueles jogadores de antigamente: de raça.",
                   "Esse {jogador} precisa de alguém que pegue no braço e oriente."],
        'diretoria': ["Diretoria boa é a que aparece pouco e paga em dia.",
                      "Conheço esse filme: primeiro a diretoria apoia, depois procura culpado."],
        'bastidores': ["Futebol sempre teve bastidor. A diferença é que hoje tudo vira notícia na hora.",
                       "Isso me lembra uma história dos anos 80... mas fica para o próximo programa."],
        'coletiva': ["Treinador bom fala pouco e ganha muito.",
                     "Ele falou com sinceridade. Gostei, é raro hoje em dia."],
    },
}

# quem assina a matéria conforme o assunto
ASSINA = {'goleada': ['renata', 'duarte', 'ferraz'], 'bom': ['renata', 'lacerda', 'ferraz'],
          'neutro': ['renata', 'ferraz', 'duarte'], 'ruim': ['duarte', 'ferraz', 'renata'],
          'vexame': ['duarte', 'ferraz'], 'mercado': ['lacerda'], 'lesao': ['lacerda'], 'elenco': ['lacerda', 'renata'],
          'diretoria': ['lacerda', 'duarte'], 'bastidores': ['lacerda'], 'coletiva': ['ferraz', 'lacerda']}

# como cada jornalista abre a pergunta na coletiva (a pergunta em si continua a mesma, para as respostas baterem)
INTRO = {
    'duarte': {'bom': ["Vou ser direto.", "Sem rodeios:", "Números à parte,"],
               'ruim': ["Desculpa, mas preciso perguntar.", "Vou ser direto, porque o torcedor merece resposta.",
                        "Não dá para fingir que está tudo bem."]},
    'ferraz': {'bom': ["Com todo respeito, e já que hoje deu certo,", "Curiosidade minha:"],
               'ruim': ["Na última coletiva o discurso foi outro, então pergunto:", "Com todo respeito,"]},
    'lacerda': {'bom': ["O clima no CT parece ótimo.", "Apurei que o grupo saiu satisfeito."],
                'ruim': ["Apurei que o vestiário ficou pesado.", "Há informação de cobrança interna."]},
    'pilha': {'bom': ["Professor, a torcida tá MALUCA!", "Fala, professor! Que jogo!"],
              'ruim': ["Professor, o torcedor tá revoltado!", "Professor, a live tá pegando fogo!"]},
    'renata': {'bom': ["Uma pergunta mais tática.", "Pensando no desenho do time,"],
               'ruim': ["Do ponto de vista tático,", "Olhando para a estrutura do time,"]},
    'arnaldo': {'bom': ["Professor, eu que acompanho o clube há quarenta anos:"],
                'ruim': ["Professor, eu que já vi muita coisa nesse futebol:"]},
}


def _rnd(*k):
    return random.Random(int(hashlib.md5('|'.join(map(str, k)).encode()).hexdigest()[:12], 16))


def _fmt(t, v):
    try:
        return t.format(**v)
    except (KeyError, IndexError):
        return t


def lista():
    return [{'id': k, **j} for k, j in JORNALISTAS.items()]


def situacao(noticia):
    s = SIT.get(noticia.get('tipo'), 'bastidores')
    if s == 'elenco' and noticia.get('tipo') == 'jog_critica':
        return 'elenco'
    return s


def reportagem(noticia, ctx):
    """Matéria completa (assinada por quem combina com o assunto) e a mesa de debate com 3 ou 4 jornalistas."""
    sit = situacao(noticia)
    r = _rnd(noticia.get('titulo'), noticia.get('data'))
    v = {'clube': ctx.get('clube', ''), 'tecnico': ctx.get('tecnico', 'o técnico'),
         'adv': noticia.get('adv') or 'o adversário', 'placar': noticia.get('placar') or '',
         'jogador': noticia.get('jogador') or ctx.get('jogador') or 'o camisa 10',
         'empresa': noticia.get('empresa') or 'a empresa', 'n': noticia.get('n') or '', 'pos': ctx.get('pos') or ''}
    autor = r.choice(ASSINA.get(sit, ['lacerda']))
    corpo = list(noticia.get('corpo') or []) or _corpo(sit, noticia, v, ctx, r, autor)
    outros = [k for k in JORNALISTAS if k != autor]
    r.shuffle(outros)
    mesa = []
    if noticia.get('tipo') == 'campanha':          # camisa de campanha do marketing: o debate é sobre ela
        from .marketing import MESA
        v['campanha'] = noticia.get('campanha_nome') or 'a campanha'
        frases = r.sample(MESA['ok' if noticia.get('aprovada') else 'nao'], 4)
    for i, k in enumerate([autor] + outros[:r.randint(2, 3)]):
        t = frases[i] if noticia.get('tipo') == 'campanha' else r.choice(C[k].get(sit) or C[k]['bastidores'])
        mesa.append({'jornalista': k, **JORNALISTAS[k], 'texto': _fmt(t, v)})
    prog = JORNALISTAS[r.choice([m['jornalista'] for m in mesa if m['jornalista'] != 'pilha'] or [autor])]['programa']
    return {'autor': {'id': autor, **JORNALISTAS[autor]}, 'corpo': corpo, 'mesa': mesa, 'programa': prog,
            'situacao': sit}


def _corpo(sit, n, v, ctx, r, autor):
    cl, tec = v['clube'], v['tecnico']
    p = []
    tab = ctx.get('pos')
    torc = ctx.get('torcida', 50)
    if sit in ('goleada', 'bom', 'neutro', 'ruim', 'vexame'):
        local = 'em casa' if n.get('casa') else 'fora de casa'
        abre = {'goleada': f"O {cl} não tomou conhecimento do {v['adv']} e construiu um placar de {v['placar']} {local}.",
                'bom': f"O {cl} venceu o {v['adv']} por {v['placar']} {local} e somou três pontos importantes.",
                'neutro': f"{cl} e {v['adv']} ficaram no {v['placar']} {local}, num jogo de poucas chances claras.",
                'ruim': f"O {cl} perdeu para o {v['adv']} por {v['placar']} {local} e volta a ser alvo de cobranças.",
                'vexame': f"Noite para esquecer: o {cl} foi atropelado pelo {v['adv']}, {v['placar']}, {local}."}[sit]
        p.append(abre)
        if tab:
            p.append(f"Com o resultado, o time aparece em {tab}º na tabela" +
                     (", colado no pelotão de cima." if tab <= 4 else ", ainda longe de onde a torcida quer." if tab > 8 else ", na briga pelas primeiras posições."))
        humor = ('A arquibancada saiu em festa' if torc >= 70 else 'A torcida deixou o estádio dividida' if torc >= 40
                 else 'Os protestos começaram ainda no apito final')
        p.append(f"{humor}, e o {tec} sabe que o próximo compromisso já vale como teste do momento do grupo.")
        if autor == 'renata':
            p.append(r.choice(["No desenho, o time alternou entre a linha de quatro sem a bola e uma saída em três, "
                               "com um dos volantes recuando entre os zagueiros.",
                               "O ponto-chave esteve na disputa pelo meio: quem controlou o corredor central ditou o ritmo."]))
        elif autor == 'duarte':
            p.append(r.choice(["Mais do que o placar, a atuação levanta perguntas sobre o planejamento da temporada.",
                               "O resultado não apaga os problemas estruturais que o time vem mostrando há semanas."]))
        else:
            p.append(r.choice(["Nos bastidores, a leitura é de que o grupo segue fechado com a comissão técnica.",
                               "Internamente, a avaliação é de que o time ainda tem margem para crescer."]))
    elif sit == 'mercado':
        p.append(f"{n.get('titulo')}. O movimento faz parte da estratégia comercial do {cl} para a temporada.")
        p.append(f"Segundo pessoas ligadas à diretoria, a negociação com a {v['empresa']} levou em conta a exposição "
                 f"do clube nas competições e o bom momento da marca nas redes sociais.")
        p.append("O valor exato não foi divulgado oficialmente, mas a cifra é tratada internamente como um dos "
                 "maiores contratos recentes do clube.")
    elif sit == 'lesao':
        p.append(f"O {cl} terá um desfalque importante: {v['jogador']} se machucou durante a semana de treinos.")
        p.append(f"O departamento médico estima cerca de {v['n'] or 'alguns'} dias de recuperação. "
                 "O atleta inicia tratamento imediatamente no CT.")
        p.append(f"Com a ausência, o {tec} deve mexer na escalação para os próximos jogos. "
                 "Opções no elenco não faltam, mas a peça é considerada difícil de substituir.")
    elif sit == 'elenco':
        p.append(f"{n.get('titulo')}.")
        p.append(f"O momento de {v['jogador']} virou um dos assuntos da semana no {cl}, nas resenhas e nas redes sociais.")
        p.append(f"Pessoas próximas ao jogador dizem que ele está atento à repercussão. A comissão do {tec} "
                 "acompanha de perto a situação.")
    elif sit == 'diretoria':
        p.append(f"{n.get('titulo')}.")
        p.append(f"A cúpula do {cl} acompanha os resultados com atenção e voltou a lembrar das metas da temporada.")
        p.append(f"Publicamente, o discurso é de apoio ao {tec}. Nos corredores, porém, a cobrança aumentou.")
    else:
        p.append(f"{n.get('titulo')}.")
        p.append(f"A movimentação nos bastidores do {cl} chamou a atenção nesta semana, com reuniões no CT e "
                 "conversas entre diretoria e comissão técnica.")
        p.append("Oficialmente, o clube não comenta. Mas o assunto já circula entre torcedores e jornalistas.")
    return p


def pergunta_coletiva(bom, idx, seed):
    """Quem faz a pergunta (revezando entre os jornalistas) e a frase com que ele abre."""
    pool = ['lacerda', 'pilha', 'renata', 'arnaldo', 'ferraz'] if bom else ['duarte', 'ferraz', 'pilha', 'lacerda', 'renata']
    _rnd(seed).shuffle(pool)
    k = pool[idx % len(pool)]
    return k, _rnd(seed, idx).choice(INTRO[k]['bom' if bom else 'ruim'])
