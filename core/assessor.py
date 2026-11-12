"""Assessor de imprensa do clube: cuida das redes sociais sozinho.

Ele publica (pós-jogo, semana, patrocínio, expulsões), responde a torcida no tom do momento e sabe dos
bastidores: finanças, punições internas, lesões e a situação do técnico. Conforme a personalidade dele e o
momento do técnico no clube, parte disso vaza para a imprensa como "fonte ligada ao clube".
O técnico não posta mais: fica só com a coletiva.
"""
import random
import hashlib
import datetime as dt

PERSONAS = [
    {'id': 'rafael', 'nome': 'Rafael Monteiro', 'estilo': 'sobrio', 'vaza': 0.10, 'lealdade': 0.85,
     'perfil': 'Ex-repórter de TV, diplomático e frio. Fala pouco, mede cada palavra e nunca bate de frente com a torcida.'},
    {'id': 'bia', 'nome': 'Bianca “Bia” Castanho', 'estilo': 'marketeira', 'vaza': 0.22, 'lealdade': 0.6,
     'perfil': 'Marketeira, vive de engajamento: emoji, meme e provocação leve. Adora um bastidor que rende clique.'},
    {'id': 'jorge', 'nome': 'Jorge Sales', 'estilo': 'veterano', 'vaza': 0.32, 'lealdade': 0.45,
     'perfil': 'Veterano de redação, 25 anos de futebol e amigo de todos os setoristas. Protege quem o protege; '
               'quando o barco balança, a informação escapa.'},
]

ESTILO_NOME = {'sobrio': 'Diplomático', 'marketeira': 'Marketeira', 'veterano': 'Veterano'}


def _seed(*p):
    return int(hashlib.md5('|'.join(map(str, p)).encode()).hexdigest()[:8], 16)


def _s2d(s):
    return dt.date.fromisoformat(str(s)[:10])


def _mi(v):
    from .mundo import eur_mi
    return eur_mi(v)


# ---------------- textos ----------------
from .vozes import L, Memoria, fmt

POS_JOGO = {
    'sobrio': {
        'V': L("""FIM DE JOGO | {clube} {gp} x {gc} {adv}.{gols} Três pontos importantes. Foco no próximo compromisso.|
Vitória do {clube}: {gp} x {gc} sobre o {adv}.{gols} Seguimos trabalhando.|
Encerrada a partida. {clube} {gp} x {gc} {adv}.{gols} Obrigado a todos que apoiaram.|
{clube} vence o {adv} por {gp} x {gc}.{gols} O grupo já se reapresenta amanhã.|
Resultado positivo: {gp} x {gc} contra o {adv}.{gols} Parabéns ao elenco e à comissão.|
FIM | {clube} {gp} x {gc} {adv}.{gols} Vitória construída com trabalho e concentração.|
Três pontos conquistados diante do {adv} ({gp} x {gc}).{gols} A sequência continua."""),
        'G': L("""FIM DE JOGO | {clube} {gp} x {gc} {adv}.{gols} Grande atuação do grupo. Obrigado, torcida.|
Atuação marcante: {clube} {gp} x {gc} {adv}.{gols} Pés no chão e foco na sequência.|
{clube} {gp} x {gc} {adv}.{gols} Noite especial para o clube. O trabalho segue."""),
        'E': L("""FIM DE JOGO | {clube} {gp} x {gc} {adv}.{gols} Um ponto conquistado. Já estamos pensando no próximo jogo.|
Empate com o {adv}: {gp} x {gc}.{gols} O grupo volta aos treinos para ajustar os detalhes.|
Encerrada a partida: {clube} {gp} x {gc} {adv}.{gols} Seguimos somando.|
{gp} x {gc} contra o {adv}.{gols} Resultado que nos mantém na disputa. Próximo compromisso já na mira."""),
        'D': L("""FIM DE JOGO | {clube} {gp} x {gc} {adv}.{gols} Resultado abaixo do esperado. Elenco e comissão já trabalham para a resposta.|
Derrota para o {adv}, {gp} x {gc}.{gols} O grupo sabe da responsabilidade e vai reagir.|
Encerrada a partida: {clube} {gp} x {gc} {adv}.{gols} Não era o resultado que buscávamos.|
{clube} perde para o {adv} por {gp} x {gc}.{gols} O foco agora é a recuperação para o próximo jogo.|
Resultado negativo diante do {adv} ({gp} x {gc}).{gols} Seguimos juntos."""),
    },
    'marketeira': {
        'V': L("""APITO FINAL!!! 🔥🔥 {clube} {gp}x{gc} {adv}!{gols} Que noite, Nação! 💪|
É DO {CLUBE}! 😎 {gp}x{gc} no {adv}!{gols} Pode comemorar que hoje é nosso! 🎉|
TRÊS PONTOS NA CONTA ✅ {gp}x{gc} no {adv}!{gols} Bora que tem mais! 🚀|
Ganhamos, Nação!!! 💪 {clube} {gp}x{gc} {adv}.{gols} Dorme feliz hoje 😴💚|
VITÓRIAAAA 🗣️ {gp}x{gc} contra o {adv}!{gols} Quem tava aqui comenta "eu vi" ⬇️|
Sofrido? Talvez. Nosso? COM CERTEZA 😎 {gp}x{gc} no {adv}!{gols}|
Placar final: {clube} {gp}x{gc} {adv} 🔥{gols} Esse grupo é diferente! 🙌"""),
        'G': L("""GOLEADA!!! 🔥🔥🔥 {clube} {gp}x{gc} {adv}!{gols} Hoje teve show, Nação!|
Alguém anota a placa?? 😂 {gp}x{gc} no {adv}!{gols} QUE TIMEEE|
ATROPELO! 🚜 {clube} {gp}x{gc} {adv}.{gols} Print e guarda pra sempre 📸"""),
        'E': L("""Fim de papo: {gp}x{gc} contra o {adv}.{gols} Pontinho na conta, mas a gente quer mais! 💪|
Empate com o {adv}: {gp}x{gc}.{gols} Bola pra frente que já tem jogo! ⏭️|
{gp}x{gc} 🤝 {adv}.{gols} Não foi do jeito que a gente queria, mas seguimos somando! 💚|
Ponto conquistado! {clube} {gp}x{gc} {adv}.{gols} Semana de ajuste e volta mais forte 💪"""),
        'D': L("""Não foi o resultado que a gente queria. 💔 {gp}x{gc} para o {adv}.{gols} Cabeça erguida, tem jogo já já!|
Dói, Nação. {gp}x{gc}.{gols} Mas time grande se levanta. Bora! 🔁|
Hoje não deu. 😔 {clube} {gp}x{gc} {adv}.{gols} A resposta vem em campo, juntos!|
Derrota pro {adv} ({gp}x{gc}).{gols} A gente sente com vocês. Próximo jogo é pra virar a chave 🔑|
Noite difícil, {gp}x{gc}.{gols} Ninguém solta a mão de ninguém 🤝"""),
    },
    'veterano': {
        'V': L("""Encerrado: {clube} {gp} x {gc} {adv}.{gols} Jogo sério, vitória construída. Assim que se faz.|
Tá liquidado: {gp} x {gc} no {adv}.{gols} Time competitivo, do jeito que a casa gosta.|
Fim de papo: {clube} {gp} x {gc} {adv}.{gols} Suou, brigou e levou. Futebol é isso.|
{clube} {gp} x {gc} {adv}.{gols} Vitória de time grande: sem firula e com os três pontos.|
Mais três na conta: {gp} x {gc} no {adv}.{gols} Agora é recuperar o fôlego e pensar no próximo.|
Missão cumprida diante do {adv}, {gp} x {gc}.{gols} Grupo de parabéns."""),
        'G': L("""Encerrado: {clube} {gp} x {gc} {adv}.{gols} Noite pra guardar na memória.|
{gp} x {gc} no {adv}.{gols} Faz tempo que não se via o {clube} assim. Mérito do grupo.|
Tá registrado: {clube} {gp} x {gc} {adv}.{gols} Atuação de gente grande."""),
        'E': L("""Encerrado: {clube} {gp} x {gc} {adv}.{gols} Faltou o detalhe. A semana é de ajuste.|
Empate com o {adv}, {gp} x {gc}.{gols} Não perdeu, mas também não ganhou. Bola pra frente.|
{clube} {gp} x {gc} {adv}.{gols} Jogo duro, ponto suado. Dá pra mais.|
Fim de jogo: {gp} x {gc}.{gols} O {adv} se fechou e faltou criatividade. Vamos corrigir."""),
        'D': L("""Encerrado: {clube} {gp} x {gc} {adv}.{gols} Não tem o que esconder: dia ruim. Ninguém aqui está satisfeito.|
Derrota para o {adv}, {gp} x {gc}.{gols} O vestiário sabe o que precisa melhorar.|
{clube} {gp} x {gc} {adv}.{gols} Doeu. E tem que doer. A resposta vem no próximo.|
Fim de jogo: {gp} x {gc} para o {adv}.{gols} Não vamos inventar desculpa.|
Perdemos para o {adv}, {gp} x {gc}.{gols} Cabeça no lugar e trabalho. É o único caminho."""),
    },
}

EXPULSAO = {
    'sobrio': L("""{nome} foi expulso e desfalca a equipe no próximo jogo.|{nome} recebeu cartão vermelho e cumpre suspensão na próxima partida.|
Desfalque: {nome}, expulso, não enfrenta o próximo adversário."""),
    'marketeira': L("""🟥 {nome} expulso e fora do próximo jogo. Bora segurar sem ele!|🟥 Vermelho pro {nome}. Próximo jogo é sem ele, mas com a gente! 💪|
{nome} levou o vermelho 🟥 e fica de fora da próxima. O grupo segura!"""),
    'veterano': L("""Expulsão de {nome} pesa: ele cumpre suspensão na próxima rodada.|{nome} foi expulso. Próximo jogo sem ele.|
Vermelho para {nome}. Vai fazer falta na próxima."""),
}

# respostas da conta oficial aos posts da torcida, por estilo e assunto do post
RESP = {
    'sobrio': {
        'euforia': L("""Obrigado pelo apoio! Seguimos juntos. 💚|A força da arquibancada faz diferença.|Que bom ver a torcida assim. O trabalho continua.|
Momento bom, mas o foco segue no próximo jogo.|Obrigado pelo carinho de sempre."""),
        'feliz': L("""Obrigado! O trabalho continua.|Juntos somos mais fortes.|Obrigado pela mensagem. Rumo ao próximo compromisso.|Seguimos assim."""),
        'neutro': L("""Agradecemos o carinho. Seguimos trabalhando.|Estamos atentos. O foco é a próxima partida.|
A comissão já trabalha nos ajustes.|O campeonato é longo. Seguimos firmes."""),
        'chateado': L("""Entendemos a frustração. O grupo também está incomodado e vai responder em campo.|
Cobrança faz parte. O compromisso de todos aqui é com o clube.|Compreendemos. A semana é de muito trabalho.|
Ninguém aqui aceita esse resultado. Vamos reagir."""),
        'revolta': L("""Respeitamos a cobrança da torcida. O momento pede união e trabalho.|
Ninguém está satisfeito. O elenco e a comissão trabalham para mudar esse cenário.|
A insatisfação é legítima. Pedimos apenas que ela venha com respeito.|O clube ouve a torcida. A resposta precisa vir em campo."""),
        'reforco': L("""O departamento de futebol está atento ao mercado.|Qualquer novidade será comunicada pelos canais oficiais.|
O planejamento do elenco é feito com responsabilidade."""),
        'estadio': L("""Ingressos disponíveis nos canais oficiais. Contamos com você!|Obrigado! Casa cheia faz diferença.|
Sócio-torcedor tem prioridade na compra. Confira no site oficial."""),
        'camisa': L("""Obrigado! O novo uniforme está disponível na loja oficial.|Que bom que gostou. Veste com orgulho!"""),
        'lesao': L("""O departamento médico divulgará atualizações pelos canais oficiais.|{jogador} segue em tratamento. Obrigado pelo carinho."""),
        'apoio_tecnico': L("""Obrigado pela confiança no trabalho da comissão.|O apoio da torcida é fundamental."""),
        'jogador_bom': L("""{jogador} agradece o carinho! 💚|Grande momento do {jogador}. Seguimos juntos."""),
        'ansiedade': L("""Falta pouco! O grupo segue se preparando.|Em breve tem jogo. Obrigado por acompanhar."""),
        'patro': L("""Parceria importante para o clube. Obrigado!|Agradecemos aos parceiros que acreditam no projeto."""),
        'classico': L("""Clássico é diferente. Obrigado pelo apoio.|Respeito ao rival, foco no nosso trabalho."""),
    },
    'marketeira': {
        'euforia': L("""ISSO AQUI É {CLUBE}!!! 🔥🔥|Vocês são demais, Nação! 💪😎|Tá chegando a hora... 👀🔥|
Esse comentário merece print 📸|Repete comigo: É O {CLUBE}! 🗣️|Que torcida é essa?! 😍"""),
        'feliz': L("""É nóis! 😎|Bora que tem mais! 💪|Esse é o espírito! 🙌|Dorme feliz hoje 😴💚|Segue o baile, Nação! 🕺"""),
        'neutro': L("""Tamo junto, Nação! 💪|Segue o baile! 🔁|Semana de ajuste e volta com tudo! 🔧|Próximo é nosso, confia 🙏"""),
        'chateado': L("""A gente sente junto, Nação. 💔 Próximo jogo é resposta!|Respira que ainda tem muita bola. 🙏|
Hoje não, mas amanhã é outro dia 💪|Ninguém solta a mão de ninguém 🤝"""),
        'revolta': L("""A gente ouviu, Nação. Ninguém aqui tá feliz. 💔|Momento difícil, mas é junto que a gente sai. 🙏|
Recebido, Nação. A resposta tem que vir em campo. 🔁|Cobrança justa. O grupo sabe. 💔"""),
        'reforco': L("""Fica de olho nas nossas redes 👀|Spoiler? Ainda não... 🤐|Quem sabe, quem sabe... 👀🔥"""),
        'estadio': L("""Bora lotar, Nação!! 🏟️🔥|Esse é o espírito! Te esperamos lá 💚|Ingressos no link da bio! 🎟️"""),
        'camisa': L("""Linda demais, né?! 😍 Já garantiu a sua?|Manto sagrado 🙌 Loja oficial no link da bio!|Ficou top, admite 😎"""),
        'lesao': L("""Volta logo, {jogador}! 🙏💚|O {jogador} já tá na fisio! Força, guerreiro 💪"""),
        'apoio_tecnico': L("""O professor agradece! 🙌|Juntos com o {tecnico}! 💪"""),
        'jogador_bom': L("""{jogador} tá voando mesmo! 🚀|Fase iluminada do {jogador} ✨|Concordamos 100% 😎"""),
        'escalacao': L("""Comenta aí sua escalação ⬇️|Técnico de sofá ativado 😂 Quem mais?"""),
        'rival': L("""Sem comentários... 🤐😂|Silêncio do outro lado, né? 👀"""),
        'base': L("""A base tá forte! 💎 Fica de olho|Vem aí uma geração diferenciada 👀"""),
        'ansiedade': L("""Falta pouquinho! ⏳🔥|A gente também tá contando as horas 😅|Já já tem {clube} em campo! ⚽"""),
        'patro': L("""Parceria de peso! 🤝🔥|Valeu, {empresa}! 💚|Parceiro que veste a camisa 😎"""),
        'classico': L("""Clássico é clássico! 😎🔥|Já tá doendo aí do outro lado? 😂|Semana de resenha liberada 😂"""),
    },
    'veterano': {
        'euforia': L("""Torcida empurrou hoje. Obrigado, gente.|É isso: time e arquibancada na mesma batida.|
Comemora, mas amanhã é treino.|Noite boa. Merecido."""),
        'feliz': L("""Vamos com calma, mas vamos.|Trabalho sério dá nisso.|Um passo de cada vez.|É por aí."""),
        'neutro': L("""Semana de ajustes. Paciência.|Ninguém ganha campeonato em uma rodada.|Dá pra mais, e o grupo sabe.|Vamos corrigir."""),
        'chateado': L("""Tem razão em cobrar. Quem joga sabe que deve mais.|A cobrança é justa. O vestiário ouviu.|
Não tem desculpa. Tem trabalho.|Doeu aqui também."""),
        'revolta': L("""Ninguém aqui vai fingir que está tudo bem.|Ouvimos. A resposta precisa vir em campo, e rápido.|
Cobrança é do jogo. Respeito também.|Momento duro. Vamos encarar de frente."""),
        'reforco': L("""Mercado tá sendo olhado com lupa.|Quando tiver nome fechado, vocês ficam sabendo aqui.|Ninguém contrata por contratar."""),
        'estadio': L("""Casa cheia é meio caminho andado.|Contamos com vocês lá."""),
        'camisa': L("""Camisa bonita pesa mais ainda. Tem que honrar."""),
        'lesao': L("""{jogador} está em tratamento. Sem pressa, para voltar inteiro.|O DM tá cuidando do {jogador}."""),
        'apoio_tecnico': L("""O professor recebeu o recado. Obrigado.|Confiança de quem acompanha faz diferença."""),
        'jogador_bom': L("""{jogador} vive grande fase. Mérito do trabalho dele.|O {jogador} faz por merecer."""),
        'ansiedade': L("""Falta pouco. Grupo pronto.|Semana tá acabando."""),
        'patro': L("""Parceiro que acredita no projeto.|Gente séria que tá com a gente."""),
        'classico': L("""Clássico a gente respeita e joga para ganhar.|Clássico é outra coisa. Valeu, torcida."""),
    },
}

# defesa (ou não) do técnico quando a torcida pede a cabeça dele
DEFESA = {
    True: L("""O trabalho do professor {tecnico} tem o respaldo de todos aqui.|Confiamos no trabalho do {tecnico} e da comissão.|
O {tecnico} tem a confiança do clube para virar esse momento.|A comissão do {tecnico} trabalha dobrado nesta semana.|
Ninguém aqui vai jogar o {tecnico} aos leões. É hora de união."""),
    False: L("""As avaliações são feitas internamente.|Cada decisão será tomada no momento certo.|O clube não comenta a situação da comissão técnica.|
Assuntos internos são tratados internamente.|A diretoria vai avaliar o momento com calma."""),
}

SEMANA = {
    'sobrio': L("""Semana de trabalho no CT. Elenco se prepara para a sequência da temporada.|Treino de hoje concluído. O grupo segue focado.|
Atividades técnicas e táticas marcaram a manhã no CT.|Elenco realizou trabalho físico e de finalização nesta tarde.|
Reapresentação concluída. Os atletas que atuaram fizeram regenerativo.|Departamento médico atualiza a situação dos atletas nos canais oficiais.|
Treino fechado hoje no CT. Preparação segue para o próximo compromisso.|Comissão técnica comandou trabalho tático em campo reduzido."""),
    'marketeira': L("""Bastidores do treino de hoje 🎥👀 Quem tá voando? Comenta aí! ⬇️|Semana de CT com sol e muito trabalho ☀️💪 #VamosJuntos|
Golaço no treino de hoje 🎯 Adivinha de quem? 👀|Rachão valendo vaga no time? 😂🔥 Assiste no nosso canal!|
POV: você é o goleiro no treino de finalização 😅🧤|Treino puxado hoje, mas a resenha tava garantida 😂☀️|
Quem aí tá contando os dias pro próximo jogo? 🙋‍♂️⏳|Dia de academia no CT 💪 O shape tá vindo!"""),
    'veterano': L("""Semana cheia no CT. Treino forte, sem firula.|Grupo fechado, trabalho em dia. É o que dá para dizer.|
CT movimentado hoje. Treino puxado, como tem que ser.|Treino de bola parada a semana toda. Detalhe ganha jogo.|
Comissão cobrando intensidade no treino. Gostamos de ver.|Elenco trabalhou em dois períodos hoje. Ninguém tá de férias."""),
}

PATRO = {
    'sobrio': L("""O {clube} agradece à {empresa} pela parceria.|{empresa} e {clube}: parceria que segue firme.|
Nosso agradecimento à {empresa}, parceira do clube nesta temporada.|Com a {empresa}, seguimos construindo o futuro do {clube}."""),
    'marketeira': L("""Parceria que veste a camisa! 🤝 Valeu, {empresa}! 🔥|{empresa} + {clube} = 💚 Combinação perfeita!|
Quem tem {empresa} tem tudo 😎 Obrigado, parceiro!|Nossa parceira {empresa} tá com a gente em todas! 🙌"""),
    'veterano': L("""{empresa} segue com a gente. Parceiro de verdade.|Parceiro de verdade aparece na hora difícil. Valeu, {empresa}.|
{empresa} acredita no {clube}. A gente agradece."""),
}

# briefing para a coletiva: assunto que vão perguntar + conselho (variado por estilo)
BRIEF_ABRE = {
    'sobrio': L("""Professor, um resumo antes da coletiva.|Professor, segue o cenário para a coletiva.|Professor, pontos para a entrevista."""),
    'marketeira': L("""Professor, olha o que tá bombando 👀|Professor, rapidinho antes da coletiva!|Professor, mapa das redes pra você."""),
    'veterano': L("""Professor, papo reto antes da coletiva.|Professor, escuta o velho aqui.|Professor, conversei com os setoristas."""),
}
BRIEF_DICA = {
    'expulsao': L("""Sugiro não expor o jogador em público; diga que o assunto será tratado internamente.|
Proteja o atleta na frente das câmeras. Bronca, se tiver, é no vestiário.|
Não alimente a polêmica: fale do coletivo e do próximo jogo."""),
    'cargo': L("""Mostre serenidade e assuma a responsabilidade; atacar a imprensa agora só piora.|
Nada de recado para a diretoria em público. Fale em trabalho e em união.|
Eles vão tentar arrancar uma frase de efeito. Não dê. Resposta curta e calma."""),
    'goleada': L("""Bom momento para valorizar o grupo sem prometer título.|Aproveite para elogiar o elenco, mas segure a euforia.|
Fale da evolução do time. Evite comparações com campeões."""),
    'vitoria': L("""Mantenha o pé no chão; elogie o coletivo.|Vitória dá crédito: use para reforçar a ideia de jogo.|
Agradeça a torcida e mire o próximo adversário."""),
    'empate': L("""Reconheça o que não funcionou, mas destaque o ponto somado.|Fale dos ajustes que vão ser feitos na semana.|
Nada de culpar o gramado ou o juiz. Fale do que dá para melhorar."""),
    'derrota': L("""Assuma a culpa pelo resultado e proteja os jogadores.|Seja autocrítico, mas não destrua o grupo em público.|
Uma frase de responsabilidade agora vale ouro com a torcida."""),
}
BRIEF_TEMA = {'expulsao': 'a expulsão de {jogador}', 'cargo': 'o seu cargo e a sequência ruim',
              'goleada': 'a goleada e as metas do time', 'vitoria': 'a sequência e quem vem pela frente',
              'empate': 'o que faltou para vencer', 'derrota': 'a derrota para o {adv}'}

# vazamentos
VAZ_MANCHETE = {
    'lesao': L("""Lesão de {jogador} é mais séria do que o {clube} admite; volta só em {volta}, diz fonte|
Bastidores: {jogador} preocupa e pode desfalcar o {clube} até {volta}|
Exclusivo: departamento médico do {clube} trabalha com retorno de {jogador} só em {volta}|
{jogador} deve ficar fora mais tempo que o previsto, apura a reportagem"""),
    'indisciplina': L("""Fonte revela: {jogador} foi punido internamente no {clube} por {motivo}|
Clima pesado: {jogador} levou punição interna no {clube}, conta pessoa próxima ao elenco|
Bastidores: {jogador} foi afastado de atividades no {clube} após episódio de {motivo}|
{clube} pune {jogador} em silêncio; motivo seria {motivo}, diz fonte"""),
    'financas': L("""Caixa apertado: {clube} tem só {valor} para contratações, segundo fonte do clube|
Bastidores: diretoria do {clube} segura reforços; orçamento é de {valor}|
Exclusivo: {clube} terá apenas {valor} para a janela, revela pessoa ligada à diretoria|
Sem dinheiro: {clube} trabalha com {valor} e descarta nomes caros"""),
    'cargo': L("""Fonte: diretoria do {clube} já sonda nomes para o lugar de {tecnico}|
Situação de {tecnico} no {clube} é delicada, admitem pessoas do clube|
Bastidores: conselheiros do {clube} pressionam pela saída de {tecnico}|
{tecnico} tem prazo curto no {clube}, apura a reportagem"""),
    'expulsao': L("""Bastidores: {tecnico} cobrou {jogador} no vestiário pela expulsão, diz fonte|
Expulsão de {jogador} irritou a comissão do {clube}, revela fonte|
Clima tenso: {jogador} ouviu poucas e boas no vestiário do {clube} após o vermelho"""),
    'positivo': L("""Fonte: diretoria do {clube} quer renovar com {tecnico} e vê projeto de longo prazo|
Bastidores: ambiente no {clube} é de confiança total em {tecnico}|
{tecnico} é tratado como prioridade pela diretoria do {clube}, diz fonte|
Elenco do {clube} fecha com {tecnico}, contam pessoas próximas ao grupo"""),
    'patrocinio': L("""Fonte: {empresa} está satisfeita e já fala em ampliar a parceria com o {clube}|
Bastidores: {empresa} estuda aumentar investimento no {clube}|
Exclusivo: {empresa} quer renovar com o {clube} antes do prazo"""),
}
VAZ_EFEITO = {'lesao': (-1, 0), 'indisciplina': (-1, -1), 'financas': (-2, -2), 'cargo': (-2, -3),
              'expulsao': (-1, 0), 'positivo': (2, 1), 'patrocinio': (1, 1)}

AVISO_VAZOU = {
    'leal': L("""Professor, saiu na imprensa a informação sobre {assunto}. Não partiu de mim; estou apurando quem falou.|
Professor, vazou {assunto}. Já liguei para o setorista e pedi para segurar os próximos passos.|
Professor, a imprensa publicou {assunto}. Alguém de dentro falou. Vou descobrir quem foi.|
Professor, não gostei nada de ver {assunto} no jornal. Vou fechar mais o acesso ao vestiário."""),
    'mentira': L("""Professor, apareceu na imprensa {assunto}. Não sei de onde veio, mas é bom tomar cuidado com o que se fala no vestiário.|
Professor, publicaram {assunto}. Tem muita gente circulando no CT, né? Difícil saber.|
Professor, saiu {assunto}. Isso deve ter vindo de empresário de jogador, é sempre assim.|
Professor, vi {assunto} na imprensa. Melhor não comentar e deixar a poeira baixar."""),
    'confessa': L("""Professor, fui eu que soltei {assunto}. Era melhor sair por nós do que de outro jeito. Vai ajudar a imagem do clube.|
Professor, plantei {assunto} com um setorista de confiança. Notícia boa tem que circular.|
Professor, deixei vazar {assunto}. Isso fortalece o seu nome lá fora."""),
}


# ---------------- núcleo ----------------
class Assessor:
    def __init__(self, state, clube, team_id, tecnico='Técnico'):
        self.s = state
        self.clube = clube
        self.tid = team_id
        self.tecnico = tecnico
        self.m = state.setdefault('mundo', {})
        self.m.setdefault('posts', [])
        self.m.setdefault('noticias', [])
        a = state.setdefault('assessor', {})
        if 'persona' not in a:
            r = random.Random(_seed('assessor', state.get('carreira_id') or clube, clube))
            a['persona'] = r.choice(PERSONAS)['id']
        a.setdefault('relacao', 60)
        a.setdefault('vistos_partidas', None)
        a.setdefault('respondidos', [])
        a.setdefault('vazados', [])
        a.setdefault('ult_semana', None)
        a.setdefault('ult_vazamento', None)
        a.setdefault('log', [])
        a.setdefault('seguidores', None)
        self.a = a
        self.p = next(p for p in PERSONAS if p['id'] == a['persona'])
        self.mem = Memoria(state)

    # ----- identidade -----
    def arroba(self):
        from .mundo import arrobas
        slug = arrobas(self.clube)[0].split('_')[0].lstrip('@') if arrobas(self.clube) else 'clube'
        if 'PALMEIRAS' in self.clube.upper():
            slug = 'palmeiras'
        return f'@{slug}oficial'

    # ----- momento do técnico -----
    def momento(self):
        dire = self.m.get('diretoria', 60)
        torc = self.m.get('torcida', 50)
        ult = [p['res'] for p in (self.s.get('partidas') or [])[-5:]]
        forma = sum({'V': 10, 'E': 0, 'D': -10}[x] for x in ult)
        v = round(0.5 * dire + 0.3 * torc + 0.2 * (50 + forma))
        if v >= 65:
            nivel, txt = 'alta', 'em alta'
        elif v >= 45:
            nivel, txt = 'estavel', 'estável'
        elif v >= 30:
            nivel, txt = 'pressao', 'sob pressão'
        else:
            nivel, txt = 'crise', 'em crise'
        return {'valor': max(0, min(100, v)), 'nivel': nivel, 'texto': txt}

    def _leal(self):
        """Lealdade efetiva: personalidade + relação com o técnico."""
        return 0.5 * self.p['lealdade'] + 0.5 * self.a['relacao'] / 100

    def _registrar(self, data, texto):
        self.a['log'].append({'data': data, 'texto': texto})
        self.a['log'] = self.a['log'][-30:]

    def _post(self, data, texto, humor, r, extra=None, n_resp=None):
        from .mundo import Mundo
        mu = Mundo(self.s, self.clube, self.tid)
        cur = int(r.randint(800, 6000) * (0.5 + self.m.get('torcida', 50) / 100) * (1.3 if self.p['estilo'] == 'marketeira' else 1))
        v = mu._vars({}, r)
        self.m['posts'].append({'data': data, 'autor': self.arroba(), 'assessor': True, 'texto': texto,
                                'humor': humor, 'curtidas': cur, 'reposts': int(cur * r.uniform(0.08, 0.25)),
                                'respostas': mu._respostas({'semana': 'treino'}.get(humor, humor), r, self.arroba(), {**v, **(extra or {})},
                                                           n=r.randint(1, 4) if n_resp is None else n_resp),
                                **(extra or {})})
        self.m['posts'] = self.m['posts'][-300:]
        seg = self.a.get('seguidores') or 0
        self.a['seguidores'] = int(seg + cur * r.uniform(0.02, 0.06))

    def _msg(self, engine, data, assunto, texto):
        if engine is None:
            return
        engine.s['mensagens'].append({'id': engine._id(), 'data': data, 'empresa': '__diretoria__',
                                      'de': f"{self.p['nome']} · Assessoria de imprensa", 'assunto': assunto,
                                      'texto': texto, 'tipo': 'assessor', 'oferta_id': None, 'lida': False})

    # ----- processamento a cada leitura do save -----
    def processar(self, engine, novas, sumulas_jogos, nomes_time, hoje):
        if not hoje:
            return
        ds = hoje if isinstance(hoje, str) else hoje.isoformat()
        partidas = self.s.get('partidas') or []
        if self.a.get('seguidores') is None:
            atr = self.s.get('atr_base', 55)
            self.a['seguidores'] = int(40_000 * (1 + atr / 25) ** 2)
        if self.a['vistos_partidas'] is None:
            # primeira vez: não comenta jogos e posts antigos
            self.a['vistos_partidas'] = [p['chave'] for p in partidas]
            self.a['respondidos'] = [self._chave_post(p) for p in self.m['posts']]
            self.a['ult_semana'] = ds
            self._registrar(ds, f"{self.p['nome']} assumiu a assessoria de imprensa do {self.clube}.")
            self._msg(engine, ds, 'Apresentação da assessoria',
                      f"Professor, sou {self.p['nome']}, da assessoria de imprensa. A partir de agora as redes do clube ficam comigo: "
                      f"publico, respondo a torcida e cuido da relação com os setoristas. A coletiva é sua. "
                      f"Qualquer assunto sensível, me avise antes.")
            return
        self._relacao()
        for p in partidas:
            if p['chave'] in self.a['vistos_partidas']:
                continue
            self.a['vistos_partidas'].append(p['chave'])
            self._pos_jogo(p, sumulas_jogos, nomes_time, engine)
        self.a['vistos_partidas'] = self.a['vistos_partidas'][-200:]
        self._responder(ds)
        self._semana(ds, engine)

    def _chave_post(self, p):
        return f"{p.get('data')}|{p.get('autor')}|{str(p.get('texto'))[:40]}"

    def _relacao(self):
        """A relação com o técnico acompanha (devagar) o momento dele no clube."""
        alvo = 35 + self.momento()['valor'] * 0.55
        r = self.a['relacao']
        self.a['relacao'] = int(round(r + max(-4, min(4, alvo - r))))

    def _pos_jogo(self, p, sumulas_jogos, nomes_time, engine):
        casa = p['mandante'] == self.tid
        gp, gc = (p['gm'], p['gv']) if casa else (p['gv'], p['gm'])
        adv = nomes_time(p['visitante'] if casa else p['mandante'])
        r = random.Random(_seed('ass_jogo', p['chave'], self.p['id']))
        sm = next((x for x in sumulas_jogos if x.get('mandante') == p['mandante'] and x.get('visitante') == p['visitante']
                   and str(x.get('data'))[:10] <= str(p['data'])[:10]), None)
        gols, expulsos = '', []
        if sm:
            g = [f"{j['nome']}{' (' + str(j['gols']) + ')' if j['gols'] > 1 else ''}" for j in sm.get('jogadores', []) if j.get('gols')]
            if g:
                gols = (' ⚽ ' if self.p['estilo'] == 'marketeira' else ' Gols: ') + ', '.join(g) + '.'
            expulsos = [j['nome'] for j in sm.get('jogadores', []) if j.get('vermelho')]
        res = 'G' if p['res'] == 'V' and gp - gc >= 3 else p['res']
        est = self.p['estilo']
        txt = self.mem.escolher(f'a:pj:{est}:{res}', POS_JOGO[est][res], r,
                                dict(clube=self.clube, CLUBE=self.clube.upper(), gp=gp, gc=gc, adv=adv, gols=gols))
        for nome in expulsos:
            txt += ' ' + self.mem.escolher(f'a:exp:{est}', EXPULSAO[est], r, {'nome': nome})
        humor = {'V': 'feliz' if gp - gc < 3 else 'euforia', 'E': 'neutro', 'D': 'chateado' if gc - gp < 3 else 'revolta'}[p['res']]
        self._post(p['data'], txt, humor, r)
        self._registrar(p['data'], f"Publicou o pós-jogo contra o {adv} ({gp} x {gc}).")
        # expulsão vira assunto de bastidor (pode vazar depois)
        for nome in expulsos:
            self.a.setdefault('segredos', []).append({'tipo': 'expulsao', 'jogador': nome, 'data': p['data']})
        # briefing para a coletiva
        k = self._briefing(p, gp, gc, adv, expulsos)
        est = self.p['estilo']
        v = {'jogador': expulsos[0] if expulsos else '', 'adv': adv}
        self._msg(engine, p['data'], f'Briefing pós-jogo: {adv}',
                  f"{self.mem.escolher('a:ba:' + est, BRIEF_ABRE[est], r)} Clima nas redes: {self._clima()}. "
                  f"Na coletiva, devem perguntar sobre {fmt(BRIEF_TEMA[k], v)}. {self.mem.escolher('a:bd:' + k, BRIEF_DICA[k], r)}")

    def _clima(self):
        t = self.m.get('torcida', 50)
        return ('euforia total' if t >= 85 else 'torcida animada' if t >= 65 else 'torcida dividida' if t >= 45
                else 'torcida impaciente' if t >= 25 else 'revolta da torcida')

    def _briefing(self, p, gp, gc, adv, expulsos):
        mom = self.momento()['nivel']
        seq = [x['res'] for x in (self.s.get('partidas') or [])[-3:]]
        if expulsos:
            return 'expulsao'
        if seq.count('D') >= 2 or mom in ('pressao', 'crise'):
            return 'cargo'
        if p['res'] == 'V':
            return 'goleada' if gp - gc >= 3 else 'vitoria'
        return 'empate' if p['res'] == 'E' else 'derrota'

    def _responder(self, ds):
        """Responde alguns posts novos da torcida no tom do momento."""
        r = random.Random(_seed('ass_resp', ds, len(self.m['posts'])))
        mom = self.momento()['nivel']
        leal = self._leal() >= 0.55
        feitos = 0
        for p in reversed(self.m['posts'][-25:]):
            k = self._chave_post(p)
            if k in self.a['respondidos'] or p.get('assessor') or p.get('tecnico') or p.get('aovivo'):
                continue
            self.a['respondidos'].append(k)
            humor = p.get('tema') or p.get('humor') or 'neutro'
            if humor == 'semana':
                humor = 'ansiedade'
            if humor == 'critica_tecnico':
                humor = 'revolta'
            if humor not in RESP[self.p['estilo']]:
                continue                     # assunto em que a conta oficial não se mete
            if feitos >= (3 if self.p['estilo'] == 'marketeira' else 2) or r.random() < (0.55 if self.p['estilo'] == 'sobrio' else 0.35):
                continue
            est = self.p['estilo']
            vv = {'CLUBE': self.clube.upper(), 'clube': self.clube, 'tecnico': self.tecnico,
                  'jogador': p.get('jogador') or '', 'empresa': p.get('empresa') or 'nosso parceiro'}
            txt = self.mem.escolher(f'a:r:{est}:{humor}', RESP[est][humor], r, vv)
            if humor in ('revolta', 'chateado') and mom in ('pressao', 'crise') and r.random() < 0.6:
                txt += ' ' + self.mem.escolher(f'a:def:{leal}', DEFESA[leal], r, vv)
            p.setdefault('respostas', []).insert(0, {'autor': self.arroba(), 'texto': txt, 'oficial': True,
                                                     'curtidas': r.randint(20, 900)})
            feitos += 1
        self.a['respondidos'] = self.a['respondidos'][-400:]
        if feitos:
            self._registrar(ds, f"Respondeu {feitos} torcedor{'es' if feitos > 1 else ''} nas redes.")

    def _semana(self, ds, engine):
        hoje = _s2d(ds)
        u = self.a.get('ult_semana')
        if u and (hoje - _s2d(u)).days < 7:
            return
        self.a['ult_semana'] = ds
        r = random.Random(_seed('ass_sem', ds, self.p['id']))
        # post institucional
        cs = [c for c in self.s.get('contratos', []) if c.get('status') == 'ativo']
        if cs and r.random() < 0.4:
            c = r.choice(cs)
            self._post(ds, self.mem.escolher('a:pat:' + self.p['estilo'], PATRO[self.p['estilo']], r,
                                             {'clube': self.clube, 'empresa': c['empresa']}), 'patro', r,
                       extra={'empresa': c['empresa']}, n_resp=r.randint(0, 2))
            self._registrar(ds, f"Publicou ação do patrocinador {c['empresa']}.")
        else:
            self._post(ds, self.mem.escolher('a:sem:' + self.p['estilo'], SEMANA[self.p['estilo']], r), 'semana', r,
                       n_resp=r.randint(0, 3))
            self._registrar(ds, 'Publicou o dia a dia do CT.')
        self._vazamento(ds, engine, r)

    # ----- bastidores e vazamentos -----
    def _segredos(self, ds):
        """O que o assessor sabe e ainda não vazou."""
        hoje = _s2d(ds)
        out = []
        ja = set(self.a['vazados'])
        g = self.s.get('gestao') or {}
        for e in g.get('eventos', []):
            k = f"ev:{e.get('id')}"
            if k in ja or not e.get('volta') or _s2d(e['volta']) <= hoje:
                continue
            if e.get('tipo') == 'lesao' and (e.get('dias') or (_s2d(e['volta']) - _s2d(e['data'])).days) >= 10:
                out.append(('lesao', k, {'jogador': e['jogador'], 'volta': _s2d(e['volta']).strftime('%d/%m')}))
            elif e.get('tipo') == 'indisciplina':
                out.append(('indisciplina', k, {'jogador': e['jogador'], 'motivo': (e.get('titulo') or 'indisciplina').lower()}))
        for x in self.a.get('segredos', []):
            k = f"exp:{x['jogador']}:{x['data']}"
            if k not in ja and (hoje - _s2d(x['data'])).days <= 10:
                out.append(('expulsao', k, {'jogador': x['jogador']}))
        din = self.s.get('dinheiro') or {}
        orc = din.get('orc_transf')
        if orc is not None and orc < 1_500_000 and f"fin:{ds[:7]}" not in ja:
            out.append(('financas', f"fin:{ds[:7]}", {'valor': _mi(orc)}))
        mom = self.momento()['nivel']
        if mom == 'crise' and self.m.get('diretoria', 60) <= 35 and f"cargo:{ds[:7]}" not in ja:
            out.append(('cargo', f"cargo:{ds[:7]}", {}))
        if mom == 'alta' and f"pos:{ds[:7]}" not in ja:
            out.append(('positivo', f"pos:{ds[:7]}", {}))
        if cs := [c for c in self.s.get('contratos', []) if c.get('status') == 'ativo']:
            if mom in ('alta', 'estavel') and f"pat:{ds[:7]}" not in ja:
                out.append(('patrocinio', f"pat:{ds[:7]}", {'empresa': random.Random(_seed(ds)).choice(cs)['empresa']}))
        return out

    def _vazamento(self, ds, engine, r):
        hoje = _s2d(ds)
        u = self.a.get('ult_vazamento')
        if u and (hoje - _s2d(u)).days < 13:          # no máximo um vazamento a cada duas semanas
            return
        tipos = self.a.setdefault('vaz_tipos', {})
        segs = [s for s in self._segredos(ds)          # mesmo assunto genérico só depois de 60 dias
                if s[0] in ('lesao', 'indisciplina', 'expulsao') or not tipos.get(s[0])
                or (hoje - _s2d(tipos[s[0]])).days >= 60]
        if not segs:
            return
        mom = self.momento()['nivel']
        leal = self._leal()
        chance = self.p['vaza'] * {'alta': 0.7, 'estavel': 1.0, 'pressao': 1.5, 'crise': 1.9}[mom] * (1.6 - leal)
        if r.random() > chance:
            return
        # num momento ruim, o assessor pouco leal solta o que prejudica; leal tenta segurar e solta o que ajuda
        boas = [s for s in segs if s[0] in ('positivo', 'patrocinio')]
        ruins = [s for s in segs if s[0] not in ('positivo', 'patrocinio')]
        if leal >= 0.6 and boas:
            tipo, k, v = r.choice(boas)
        elif ruins and (leal < 0.6 or r.random() < 0.4):
            tipo, k, v = r.choice(ruins)
        elif boas:
            tipo, k, v = r.choice(boas)
        else:
            return
        self.a['vazados'].append(k)
        self.a['vazados'] = self.a['vazados'][-200:]
        self.a['ult_vazamento'] = ds
        tipos[tipo] = ds
        from .textos import FONTES
        v = {**v, 'clube': self.clube, 'tecnico': self.tecnico}
        titulo = self.mem.escolher('a:vaz:' + tipo, VAZ_MANCHETE[tipo], r, v)
        self.m['noticias'].append({'data': ds, 'tipo': 'vazamento', 'titulo': titulo, 'destaque': tipo in ('cargo', 'financas'),
                                   'fonte': f"{r.choice(FONTES)} · fonte ligada ao clube", 'vazamento': True,
                                   **({'jogador': v['jogador']} if v.get('jogador') else {}),
                                   **({'empresa': v['empresa']} if v.get('empresa') else {})})
        self.m['noticias'] = self.m['noticias'][-200:]
        dt_t, dt_d = VAZ_EFEITO[tipo]
        self.m['torcida'] = int(max(0, min(100, self.m.get('torcida', 50) + dt_t)))
        self.m['diretoria'] = int(max(0, min(100, self.m.get('diretoria', 60) + dt_d)))
        if v.get('jogador') and tipo in ('indisciplina', 'expulsao'):
            from .gestao import moral_ajuste
            moral_ajuste(self.s, v['jogador'], -1, ds, 'exposto na imprensa', 10)
        assunto = {'lesao': f"a lesão de {v.get('jogador')}", 'indisciplina': f"a punição do {v.get('jogador')}",
                   'financas': 'o nosso orçamento', 'cargo': 'a sua situação no cargo', 'expulsao': f"a bronca no {v.get('jogador')}",
                   'positivo': 'a confiança da diretoria no seu trabalho', 'patrocinio': f"a parceria com a {v.get('empresa')}"}[tipo]
        if tipo in ('positivo', 'patrocinio'):
            modo = 'confessa'
        elif leal >= 0.6:
            modo = 'leal'
        else:
            modo = 'mentira'
        self._msg(engine, ds, 'Saiu na imprensa', self.mem.escolher('a:av:' + modo, AVISO_VAZOU[modo], r, {'assunto': assunto}))
        self._registrar(ds, f"Vazou à imprensa: {assunto}." if modo != 'leal' else f"Saiu na imprensa: {assunto} (diz que não foi ele).")

    # ----- visão -----
    def view(self):
        mom = self.momento()
        vaz = sum(1 for n in self.m.get('noticias', []) if n.get('vazamento'))
        return {'nome': self.p['nome'], 'perfil': self.p['perfil'], 'estilo': ESTILO_NOME[self.p['estilo']],
                'arroba': self.arroba(), 'relacao': self.a['relacao'], 'momento': mom,
                'seguidores': self.a.get('seguidores') or 0, 'vazamentos': vaz,
                'discricao': int(round(100 * (1 - self.p['vaza'] * 2))),
                'log': self.a['log'][-8:][::-1]}
