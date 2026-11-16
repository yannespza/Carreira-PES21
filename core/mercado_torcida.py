"""Banco de textos da torcida para o mercado de transferências.

A torcida NÃO cita números: o tom vem dos números (fase boa, ruim, normal, sem jogos) e de traços do jogador
lidos da súmula (goleador, garçom, em seca, titular absoluto, reserva, nota alta ou baixa, cartões, jovem,
veterano, melhor ou pior que o titular atual). Cada post usa {n} (jogador), {clube}, {origem} e {comp}.

FASE[evento][fase] = posts principais; TRACO[contexto][traço] = posts extras sobre um traço.
contexto 'chegada' = sondagem e contratação; 'saida' = proposta e venda; 'fica' = recusa; 'perdeu' = fracasso."""
import random

FASE = {
    'sondagem': {
        'boa': [
            '{n} no {clube}? se for verdade é a melhor notícia da semana',
            'tô acompanhando o {n} no {origem}, tá jogando demais. traz!',
            'diretoria acordou! {n} é exatamente o que a gente precisa',
            'quem viu o {n} jogando esse ano sabe: é reforço de verdade',
            'pelo amor, fecha logo antes que outro clube atravesse',
            'se o {n} vier, já entra no time titular',
            'finalmente uma sondagem que faz sentido',
            '{n} tá voando. não deixa escapar',
            'esse rumor eu quero que seja verdade',
            'a torcida do {origem} vai chorar, mas a gente agradece',
            'o {n} é o tipo de jogador que muda jogo. vem!',
            'contrata e me avisa, já tô comprando a camisa',
        ],
        'ruim': [
            '{n}?? sério que é esse o alvo?',
            'vi o {n} jogando no {origem}, não convenceu ninguém',
            'a gente precisa de reforço, não de aposta',
            'se for pra trazer o {n} melhor ficar com o que tem',
            'quem indicou esse nome? queria entender',
            'nem a torcida do {origem} faz questão dele',
            'espero que seja só especulação da imprensa',
            'esse aí tá devendo faz tempo. passa',
            'não dá pra gastar dinheiro com quem não joga nada',
            'diretoria, por favor, olhem os jogos antes de sondar',
            'o {n} mal entra em campo e a gente quer trazer?',
            'sondagem estranha. vamos ver no que dá, mas não gostei',
        ],
        'normal': [
            '{n}... nem empolga nem assusta',
            'jogador correto. depende do preço',
            'pode ser uma boa peça de elenco, titular eu não sei',
            'não conheço tanto, mas pelo que vi é regular',
            'se vier pra compor, tudo bem. pra salvar o time, não',
            'tem dias bons e dias ruins. igual a todo mundo aqui',
            'sondagem morna. queria um nome mais forte',
            'ok, mas eu ainda prefiro alguém que resolva',
            'vou esperar ver jogando com a nossa camisa',
            'não é o reforço dos sonhos, mas também não é ruim',
        ],
        'sem_jogos': [
            '{n}? quase não jogou essa temporada, como avaliar?',
            'jogador que não entra em campo não tem como empolgar',
            'aposta total. tomara que a comissão saiba o que tá fazendo',
            'nem lembro a última vez que vi o {n} jogar',
            'contratar quem tá parado é arriscado demais',
            'se o auxiliar indicou, deve ter visto algo nos treinos. confio desconfiando',
        ],
    },
    'acertada': {
        'boa': [
            'CHEGOU! bem-vindo, {n}!',
            'contratação de peso. parabéns, diretoria',
            'que reforço! agora a gente briga por tudo',
            'o {n} vai fazer a torcida feliz, escreve aí',
            'essa foi a melhor contratação da janela',
            'já quero ver estreando no próximo jogo',
            'diretoria trabalhando bem pela primeira vez em muito tempo',
            '{n} é dos nossos agora. que fase ele vive',
            'chegou pra ser titular, não tenho dúvida',
            'aquele reforço que a gente pedia há meses',
            'o {origem} perdeu o melhor jogador e a gente ganhou',
            'manda a camisa 10 pra ele',
        ],
        'ruim': [
            'fecharam mesmo com o {n}... que tristeza',
            'espero estar errado, mas não vai dar certo',
            'dinheiro jogado fora',
            'contrataram quem ninguém queria',
            'vai ser mais um que passa sem deixar saudade',
            'tomara que aqui ele renda o que não rendeu no {origem}',
            'não sei o que viram nesse jogador',
            'mais um pro banco. e com salário de titular',
            'a torcida pediu reforço e veio isso',
            'vou dar uma chance, mas já tô desconfiado',
            'difícil defender essa contratação',
        ],
        'normal': [
            '{n} fechado. vai brigar por posição',
            'contratação ok. nem mais nem menos',
            'bom jogador de elenco. ajuda na temporada longa',
            'boa sorte, {n}. mostra serviço',
            'não empolga, mas também não dá pra reclamar',
            'é peça de reposição. tá valendo',
            'vamos ver se aqui ele cresce',
            'gostei, mas esperava um nome mais forte',
            'bem-vindo. agora é com você em campo',
            'contratação segura. às vezes é o que precisa',
        ],
        'sem_jogos': [
            'aposta da diretoria. torcendo pra dar certo',
            'chegou sem ritmo de jogo. vai precisar de tempo',
            'não vi jogar, então vou esperar antes de opinar',
            'contratação misteriosa. que surpreenda',
            'o {n} tem tudo pra ser a surpresa ou o fiasco da temporada',
        ],
    },
    'fracassou': {
        'boa': [
            'perdemos o {n}. diretoria lenta demais',
            'como deixa escapar um jogador desses?',
            'era o reforço que faltava e não veio',
            'diretoria amadora. de novo',
            'quem negociou o {n} tem que dar explicação',
            'outro clube vai aproveitar o que a gente deixou passar',
            'triste. o {n} faria diferença aqui',
            'nem pra fechar com quem tá voando',
            'o {origem} segurou e a gente desistiu fácil',
            'mais uma janela de promessa e nada',
        ],
        'ruim': [
            'ainda bem que não veio',
            'livramento!',
            'a melhor contratação é a que não acontece às vezes',
            'ufa. agora procura alguém que jogue bola',
            'pode deixar o {n} lá no {origem}, tá ótimo',
            'nunca fiquei tão feliz com negociação que deu errado',
            'diretoria, aproveita e esquece esse nome',
            'deus ouviu a torcida',
        ],
        'normal': [
            'não veio, paciência. tem opção melhor por aí',
            'não perdemos muita coisa',
            'próximo! o mercado tá cheio',
            'nem fez falta, mas mostra a dificuldade da diretoria',
            'tudo bem. só não pode acabar a janela sem ninguém',
            'era pra compor elenco mesmo. segue o jogo',
        ],
        'sem_jogos': [
            'era aposta mesmo. bola pra frente',
            'não dá pra lamentar quem nem jogava',
            'tá bom assim. foca em quem tá jogando',
        ],
    },
    'proposta': {
        'boa': [
            'vender o {n}? nem pensar',
            'o {comp} que vá procurar outro',
            'é dos melhores do time. não vende!',
            'se vender o {n} agora, a temporada acaba',
            'presidente, nem atende o telefone',
            'quem vai fazer o que ele faz?',
            'não tem dinheiro que pague o que o {n} tá jogando',
            'o {comp} quer levar o nosso melhor. NÃO',
            'segura o {n} até o fim do ano, pelo menos',
            'se vender, a torcida vai cobrar',
            'proposta indecente. recusa',
        ],
        'ruim': [
            'se pagarem bem, pode ir',
            'ouve a proposta pelo menos',
            'vende e usa o dinheiro pra trazer alguém que jogue',
            'o {comp} tá fazendo um favor pra gente',
            'não vai fazer falta nenhuma',
            'aceita antes que eles desistam',
            'até que enfim alguém quis o {n}',
            'sem ressentimento. boa sorte no {comp}',
            'libera o salário e a vaga',
        ],
        'normal': [
            'depende do valor',
            'dá pra repor se vier dinheiro bom',
            'não vende barato, mas também não precisa segurar a qualquer custo',
            'decisão difícil. ele ajuda, mas não é indispensável',
            'tô dividido. bom jogador, mas tem substituto',
            'se for proposta boa, eu venderia',
            'a diretoria tem que fazer a conta direitinho',
            'vender agora no meio da temporada é arriscado',
        ],
        'sem_jogos': [
            'nem joga. pode vender',
            'proposta pelo {n}? aproveita',
            'se tá parado aqui, melhor jogar em outro lugar',
        ],
    },
    'venda': {
        'boa': [
            'venderam o {n}. inacreditável',
            'diretoria vendeu o melhor do time no meio da temporada',
            'quem aprovou essa venda não assiste aos jogos',
            'o técnico liberou?? perdeu a moral comigo',
            'trocar o {n} por dinheiro é desistir da temporada',
            'triste dia. obrigado por tudo, {n}',
            'agora quero ver quem vai resolver os jogos',
            'o {comp} levou o nosso craque. revoltante',
            'a conta vai chegar em campo',
            'vende o melhor e depois reclama do resultado',
        ],
        'ruim': [
            'foi tarde',
            'boa venda. ninguém vai sentir falta',
            'agora usa o dinheiro direito, diretoria',
            'parabéns ao técnico, decisão certa',
            'boa sorte no {comp}. sério, de coração',
            'abriu vaga pra quem quer jogar',
            'ótimo negócio pro {clube}',
            'menos um no banco ganhando salário',
            'o {comp} vai descobrir o que a gente já sabia',
        ],
        'normal': [
            '{n} vendido. tomara que reponham à altura',
            'obrigado pelos serviços, {n}',
            'venda ok, se vier reposição',
            'não era titular absoluto, mas ajudava',
            'negócio justo pros dois lados',
            'agora tem que contratar logo',
            'vai deixar saudade? pouca, mas vai',
        ],
        'sem_jogos': [
            'nem estreou direito e já foi',
            'vendeu quem não jogava. faz sentido',
            'menos um no elenco. segue',
        ],
    },
    'recusa': {
        'boa': [
            'segurou o {n}! decisão certa',
            'fez certo. não se vende jogador nessa fase',
            'ESSE é o técnico que eu quero',
            'o {comp} que se contente com outro',
            'o {n} fica! dia feliz',
            'recusou proposta pelo melhor do time. respeito',
            'mostra que o {clube} é grande e não vende quem joga',
            'agora renova o contrato dele também',
        ],
        'ruim': [
            'recusou proposta pelo {n}? não entendi',
            'era a chance de vender e passou',
            'segurar o {n} pra quê?',
            'o técnico vê algo que a torcida não vê',
            'tomara que ele responda em campo, porque até agora nada',
            'vai se arrepender de não ter vendido',
            'perdeu dinheiro e a vaga continua ocupada',
        ],
        'normal': [
            'recusou, tudo bem. ele ajuda o elenco',
            'decisão do técnico, respeito',
            'manter quem conhece o grupo também vale',
            'se a proposta era baixa, fez certo',
            'ok. agora o {n} tem que mostrar que merecia ficar',
        ],
        'sem_jogos': [
            'recusou vender quem nem joga? estranho',
            'deve ter algum plano pro {n}. vamos ver',
        ],
    },
}

TRACO = {
    'chegada': {
        'goleador': ['esse sabe onde fica o gol', 'atacante que faz gol é tudo que a gente pedia',
                     'finalmente alguém que empurra a bola pra rede', 'vem resolver o nosso problema de finalização'],
        'garcom': ['jogador que faz o time jogar. adoro', 'vai deixar os nossos atacantes na cara do gol',
                   'esse dá passe que ninguém vê', 'garçom de primeira. gostei'],
        'seca': ['atacante que não marca? complicado', 'o problema é que ele tá sem fazer gol há tempo',
                 'vem pra fazer gol ou pra correr?', 'tá numa seca braba. aqui vai mudar?'],
        'titular_absoluto': ['era titular absoluto lá, tem rodagem', 'jogador de confiança, joga todo jogo',
                             'tá acostumado a ser titular. ótimo sinal'],
        'reserva': ['era reserva lá e vai ser titular aqui?', 'nem no {origem} ele é titular...',
                    'sentou no banco a temporada toda'],
        'nota_alta': ['regularidade impressionante', 'joga bem quase todo jogo', 'consistente demais'],
        'nota_baixa': ['jogo bom dele é raridade', 'muito irregular', 'atuações bem fracas'],
        'cartoes': ['só espero que não leve cartão todo jogo', 'esquentadinho... vai desfalcar muito',
                    'precisa controlar a cabeça'],
        'jovem': ['garoto novo, tem muito pra evoluir aqui', 'investimento pro futuro. gostei',
                  'jovem ainda, dá tempo de crescer aqui'],
        'veterano': ['experiência ajuda num grupo jovem', 'contrato curto, por favor',
                     'vem pra ajudar agora, não pro futuro', 'já tá na reta final da carreira...'],
        'melhora': ['melhor que o nosso titular. sobe o nível', 'chega pra ser titular, sem dúvida',
                    'é upgrade na posição'],
        'piora': ['não é melhor do que o que já temos', 'pra que trazer alguém abaixo do nosso titular?',
                  'pra banco tá caro'],
        'mesmo_nivel': ['mesmo nível do que temos. serve pra concorrência', 'vai brigar de igual com o titular',
                        'reposição à altura, pelo menos'],
    },
    'saida': {
        'goleador': ['artilheiro não se vende', 'quem vai fazer os gols sem ele?',
                     'gol não nasce em árvore'],
        'garcom': ['quem vai criar as jogadas agora?', 'o time vai ficar sem criatividade',
                   'perdemos o cérebro do time'],
        'seca': ['atacante que não faz gol pode ir', 'sem gol, sem lugar', 'faz tempo que não balança a rede'],
        'titular_absoluto': ['é titular em quase todo jogo, não dá pra perder', 'peça fixa do time',
                             'o técnico confia nele, por que vender?'],
        'reserva': ['quase não joga mesmo', 'vida no banco não é vida', 'vai jogar em outro lugar, melhor pra todos'],
        'nota_alta': ['um dos mais regulares do elenco', 'raramente joga mal'],
        'nota_baixa': ['jogo ruim atrás de jogo ruim', 'tá devendo há muito tempo'],
        'cartoes': ['menos cartão pro time', 'vivia suspenso mesmo'],
        'jovem': ['vender jovem agora é vender o futuro', 'formou aqui e vai brilhar em outro lugar',
                  'ainda ia crescer muito'],
        'veterano': ['na idade dele, vender agora é negócio', 'aproveita o último bom contrato',
                     'já deu o que tinha que dar'],
    },
}
TRACO['fica'] = {
    'goleador': ['o artilheiro fica. gol garantido', 'segurou quem faz os gols. perfeito'],
    'garcom': ['o cérebro do time fica!', 'quem cria as jogadas continua aqui. ufa'],
    'seca': ['segurou um atacante que não marca...', 'ficar pra continuar sem fazer gol?'],
    'titular_absoluto': ['titular absoluto tem que ficar mesmo', 'peça fixa do time, fez certo'],
    'reserva': ['vai continuar no banco, então?', 'segurou pra deixar no banco?'],
    'nota_alta': ['um dos mais regulares fica. ótimo', 'regularidade assim não se vende'],
    'nota_baixa': ['ficar pra continuar jogando mal?', 'espero que melhore, porque até agora...'],
    'jovem': ['o garoto fica e vai crescer aqui', 'futuro do clube segue em casa'],
    'veterano': ['na idade dele era a hora de vender', 'experiência no grupo também conta'],
}
TRACO['perdeu'] = {
    'goleador': ['era o goleador que a gente precisava', 'deixamos escapar quem faz gol'],
    'garcom': ['ia criar muito aqui. pena', 'faltou um meia assim no elenco'],
    'seca': ['atacante sem gol, não fez falta', 'nem marcando ele tava'],
    'titular_absoluto': ['era titular absoluto lá, ia somar', 'jogador de confiança, uma pena'],
    'reserva': ['era reserva lá, não ia mudar nada', 'nem no {origem} jogava'],
    'nota_alta': ['jogava bem toda rodada. que pena', 'regular demais pra deixar passar'],
    'nota_baixa': ['jogando daquele jeito, melhor assim', 'não perdemos grande coisa'],
    'jovem': ['era investimento pro futuro', 'o garoto ia crescer aqui'],
    'veterano': ['na idade dele, tudo bem não vir', 'era solução de curto prazo mesmo'],
    'melhora': ['ia ser titular aqui. perdemos', 'era melhor que o nosso titular. triste'],
    'piora': ['nem era melhor que o nosso titular', 'não mudava o time, tá tranquilo'],
    'mesmo_nivel': ['era do nível do que já temos, sem drama'],
}
CONTEXTO = {'sondagem': 'chegada', 'acertada': 'chegada', 'fracassou': 'perdeu', 'proposta': 'saida',
            'venda': 'saida', 'recusa': 'fica'}

# traços que combinam com cada tom (não elogiar com traço ruim nem criticar com traço bom)
BONS = {'goleador', 'garcom', 'titular_absoluto', 'nota_alta', 'jovem', 'melhora'}
RUINS = {'seca', 'reserva', 'nota_baixa', 'cartoes', 'piora'}


def tracos(j, ff, ofensivos):
    s = j.get('stats') or {}
    jogos, tit = s.get('jogos') or 0, s.get('titular') or 0
    t = set()
    if jogos >= 3:
        g, a = s.get('gols') or 0, s.get('assist') or 0
        if j.get('pos') in ofensivos:
            alvo = 0.45 if j.get('pos') == 'ATA' else 0.3
            if g / jogos >= alvo:
                t.add('goleador')
            elif (g + 0.7 * a) / jogos < alvo * 0.35:
                t.add('seca')
            if a / jogos >= 0.3:
                t.add('garcom')
        if tit / jogos >= 0.8:
            t.add('titular_absoluto')
        elif tit / jogos < 0.35:
            t.add('reserva')
        nota = s.get('nota_media')
        if nota is not None:
            t.add('nota_alta' if nota >= 7.0 else 'nota_baixa' if nota < 6.0 else '')
        if (s.get('amarelos') or 0) + 3 * (s.get('vermelhos') or 0) >= 7:
            t.add('cartoes')
    idade = j.get('idade')
    if idade and idade <= 21:
        t.add('jovem')
    elif idade and idade >= 32:
        t.add('veterano')
    if ff.get('comp'):
        t.add('melhora' if ff.get('melhora') else 'mesmo_nivel' if 'mesmo CGJ' in ff['comp'] else 'piora')
    t.discard('')
    return t


def posts(evento, fs, j, ff, clube, r: random.Random, ofensivos, ja=()):
    """3 a 5 posts da torcida, sem números, no tom que os números pedem."""
    v = {'n': j['nome'], 'clube': clube, 'origem': j.get('clube') or 'antigo clube', 'comp': j.get('comprador') or 'outro clube'}
    base = list(FASE.get(evento, {}).get(fs) or FASE.get(evento, {}).get('normal') or [])
    r.shuffle(base)
    ctx = CONTEXTO.get(evento, 'chegada')
    tr = tracos(j, ff, ofensivos)
    # na fase boa, só traços bons; na ruim, só ruins; nas outras, os dois (dúvida)
    if fs == 'boa':
        tr &= BONS | {'veterano', 'mesmo_nivel'}
    elif fs == 'ruim':
        tr &= RUINS | {'veterano', 'mesmo_nivel'}
    extras = []
    for t in sorted(tr):
        ops = TRACO.get(ctx, {}).get(t)
        if ops:
            extras.append(r.choice(ops))
    r.shuffle(extras)
    escolha = base[:r.randint(2, 3)] + extras[:2]
    out = []
    for x in escolha:
        try:
            x = x.format(**v)
        except (KeyError, IndexError):
            continue
        if x not in ja and x not in out:
            out.append(x)
    r.shuffle(out)
    return out
