"""Perguntas da coletiva feitas a partir dos FATOS do jogo e do momento (gols, notas, lesões por desgaste,
tribunal, proposta de outro clube, moral baixa, carrasco, viagem, próximo adversário).

Cada pergunta tem 3 ou 4 respostas; cada resposta tem várias redações e o app sorteia uma, para a coletiva não
repetir as mesmas frases. Formato igual ao banco: (texto, tom, torcida, diretoria, estilo).
"""


def _r(r, frases, tom, torc, dire, estilo):
    return (r.choice(frases), tom, torc, dire, estilo)


def gerar(f, r, ja_usadas=()):
    """f: dicionário de fatos montado pelo app. Devolve [(pergunta, [respostas], jogador)] (no máximo 3)."""
    out = []
    usadas = set(ja_usadas or ())

    def add(chave, q, ans, jog=None):
        if chave in usadas:
            return
        out.append((q, ans, jog, chave))

    adv = f.get('adv', 'o adversário')
    # artilheiro do jogo
    for g in (f.get('nossos_gols') or [])[:1]:
        n = g['nome']
        if g['gols'] >= 2:
            q = r.choice([f'{n} marcou {g["gols"]} vezes hoje. Ele é o melhor atacante do campeonato?',
                          f'Mais uma noite de {n}: {g["gols"]} gols. Dá para segurar ele no clube?',
                          f'{n} decidiu de novo. O time depende demais dele?'])
        else:
            q = r.choice([f'{n} fez o gol. Como você avalia a fase dele?',
                          f'O gol de {n} mudou o jogo. Ele ganhou a vaga de titular?'])
        add('gol:' + n, q, [
            _r(r, [f'{n} está voando, mas o mérito é coletivo.', f'{n} merece. O grupo trabalhou para ele concluir.'], 'feliz', 2, 1, 'proteger'),
            _r(r, [f'É o melhor do Brasil hoje. Quem duvidar, que venha ver.', f'{n} joga em qualquer time do mundo.'], 'feliz', 3, -1, 'empolgar'),
            _r(r, ['Ninguém aqui é dono de posição. Ele sabe disso.', 'Fez a parte dele. Amanhã a cobrança é a mesma.'], 'neutro', 0, 2, 'corporativo'),
            _r(r, ['Ainda pode render mais. Cobro isso dele todo dia.', 'Fez o gol, mas errou muita coisa. Vamos conversar.'], 'irritado', -1, 1, 'expor')], n)
    # melhor e pior nota
    pior = f.get('pior')
    if pior and f.get('res') != 'V':
        n = pior['nome']
        q = r.choice([f'{n} teve uma atuação muito abaixo. Ele perde a vaga?',
                      f'A torcida pegou no pé de {n}. Como você vê a fase dele?',
                      f'{n} saiu vaiado. Ainda confia nele?'])
        add('pior:' + n, q, [
            _r(r, [f'Confio no {n}. Ninguém fica bom ou ruim em um jogo.', f'{n} tem crédito. Eu protejo meus jogadores.'], 'neutro', -1, 1, 'proteger'),
            _r(r, ['Todo mundo vai ser avaliado na semana. Sem exceção.', 'Quem treinar melhor joga. Simples.'], 'neutro', 0, 2, 'corporativo'),
            _r(r, [f'Não foi bem, e ele sabe. Vai ter que responder em campo.', f'O {n} precisa entender a camisa que veste.'], 'irritado', 1, 0, 'expor'),
            _r(r, ['A escalação foi minha. Se alguém falhou, fui eu.', 'Coloquei ele numa função difícil. A culpa é minha.'], 'neutro', 1, 1, 'culpa')], n)
    # gol do carrasco
    for c in (f.get('carrasco_marcou') or [])[:1]:
        n = c['nome']
        add('carr:' + n, r.choice([f'{n} marcou de novo contra vocês. Já são {c["gols"]} gols. O que falta para pará-lo?',
                                   f'{n} virou carrasco do clube. Faltou um plano para ele?']), [
            _r(r, ['Jogador decisivo decide. Precisamos marcar melhor como time.', 'Faltou encaixe na marcação. Vamos estudar.'], 'neutro', 0, 2, 'humilde'),
            _r(r, ['Errei a estratégia para ele. Assumo.', 'Deveria ter colocado marcação individual. Foi minha.'], 'neutro', 1, 1, 'culpa'),
            _r(r, ['Carrasco? Na próxima ele não vê a cor da bola.', 'Que aproveite enquanto pode.'], 'irritado', 2, -1, 'provocar')], n)
    # lesões por desgaste
    les = f.get('lesoes_desgaste') or []
    if les:
        nomes = ' e '.join([', '.join(les[:2]), les[2]] if len(les) >= 3 else les[:2]) if len(les) > 1 else les[0]
        add('les:' + nomes, r.choice([f'{nomes} se machucaram. O time está jogando demais?',
                                      f'Mais lesões musculares: {nomes}. A preparação física falhou?',
                                      f'O departamento médico está cheio. É o calendário ou o planejamento?']), [
            _r(r, ['O calendário brasileiro é desumano. Ninguém aguenta esse ritmo.', 'Jogamos a cada três dias. Uma hora o corpo cobra.'], 'irritado', 1, -1, 'pressao'),
            _r(r, ['Eu forcei alguns jogadores. Vou rodar mais o elenco.', 'Insisti com quem estava cansado. Erro meu.'], 'neutro', 1, 1, 'culpa'),
            _r(r, ['O departamento médico vai recuperar todos. Temos elenco.', 'Lesão faz parte. Quem entrar vai dar conta.'], 'neutro', 0, 2, 'corporativo'),
            _r(r, ['Alguns não se cuidam fora de campo. Vou cobrar.', 'Tem jogador que precisa ser mais profissional.'], 'irritado', 0, 0, 'expor')])
    # tribunal
    for p in (f.get('tribunal') or [])[:1]:
        n = p['jogador']
        add('trib:' + n, r.choice([f'{n} foi expulso direto e vai a julgamento. O clube vai defender?',
                                   f'A expulsão de {n} prejudicou o time. Ele errou?']), [
            _r(r, [f'Vamos defender o {n} até o fim. Foi um lance normal de jogo.', 'O clube está com ele. Vamos ao tribunal com tudo.'], 'neutro', 2, 0, 'proteger'),
            _r(r, ['Errou e prejudicou o grupo. Vai ser punido internamente.', 'Não aceito esse tipo de atitude.'], 'irritado', 0, 1, 'expor'),
            _r(r, ['O árbitro exagerou. Cartão amarelo, no máximo.', 'A arbitragem precisa ter critério. Não teve.'], 'irritado', 2, -1, 'arbitragem')], n)
    # proposta de outro clube
    for o in (f.get('ofertas') or [])[:1]:
        add('oferta:' + o, r.choice([f'Dizem que o {o} quer você. Vai sair?', f'Há uma proposta do {o} na mesa. Você fica?',
                                     f'O seu nome é falado no {o}. Isso mexe com você?']), [
            _r(r, ['Estou focado aqui. Tenho contrato e um projeto.', 'Meu compromisso é com este clube.'], 'neutro', 3, 3, 'corporativo'),
            _r(r, ['Fico feliz com o reconhecimento, mas não penso nisso agora.', 'Ser lembrado mostra que o trabalho está bom.'], 'feliz', 0, 1, 'humilde'),
            _r(r, ['Futebol é dinâmico. Tudo pode acontecer.', 'Nunca digo nunca. Vamos ver no fim da temporada.'], 'neutro', -4, -4, 'pressao')])
    # moral baixa
    for j in (f.get('moral_baixa') or [])[:1]:
        add('moral:' + j, r.choice([f'{j} parece desmotivado. Está tudo bem com ele?', f'Fala-se que {j} anda insatisfeito. É verdade?']), [
            _r(r, [f'O {j} é importante e vai voltar a sorrir. Conversamos sempre.', 'Está tudo bem. Ele tem meu apoio.'], 'neutro', 1, 1, 'proteger'),
            _r(r, ['Quem não estiver feliz, a porta está aberta.', 'Aqui não tem espaço para cara feia.'], 'irritado', 0, 0, 'expor'),
            _r(r, ['Assunto interno. Resolvemos no vestiário.', 'Isso não sai daqui de dentro.'], 'neutro', 0, 2, 'corporativo')], j)
    # altitude / viagem
    if f.get('altitude'):
        add('alt', r.choice([f'Próximo jogo a {f["altitude"]} metros. Como preparar o time?', 'A altitude preocupa?']), [
            _r(r, ['Vamos com antecedência e com o melhor planejamento.', 'Ciência e preparação. Não é desculpa.'], 'neutro', 1, 2, 'corporativo'),
            _r(r, ['É desumano jogar lá. A Conmebol precisa rever isso.', 'Futebol a essa altura é outro esporte.'], 'irritado', 1, -1, 'pressao'),
            _r(r, ['Com altitude ou sem, vamos buscar o resultado.', 'Grande joga em qualquer lugar.'], 'feliz', 2, 0, 'empolgar')])
    # próximo adversário
    if f.get('prox_adv'):
        p = f['prox_adv']
        add('prox:' + p, r.choice([f'O próximo é contra o {p}. O que esperar?', f'Já pensa no {p}?',
                                   f'O {p} vem em boa fase. É o jogo mais difícil da sequência?']), [
            _r(r, ['Jogo a jogo. Hoje é dia de descansar.', 'Primeiro recuperar o grupo. Depois a gente pensa nele.'], 'neutro', 0, 2, 'corporativo'),
            _r(r, ['Vamos para ganhar, como sempre.', 'Em casa ou fora, entramos para vencer.'], 'feliz', 2, 0, 'empolgar'),
            _r(r, [f'Respeitamos muito o {p}. Vai ser duro.', 'Adversário de qualidade. Precisamos estar no máximo.'], 'neutro', 1, 1, 'humilde'),
            _r(r, ['Eles que se preocupem com a gente.', 'Quem tem que estudar a gente são eles.'], 'feliz', 3, -1, 'provocar')])
    r.shuffle(out)
    return out[:3]
