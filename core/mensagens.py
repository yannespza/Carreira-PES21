"""Banco de mensagens pré-escritas. Variáveis: {clube} {empresa} {valor} {posicao} {anos} {validade}
{inicio} {forma} {pedido} {contato}. Cada situação tem textos por personalidade."""
import random

CONTATOS = {
    'agressiva': ['Diretoria de Marketing', 'Head de Patrocínios', 'Diretor Comercial'],
    'paciente': ['Gerência de Marca', 'Coordenação de Patrocínios', 'Equipe de Relacionamento'],
    'fiel': ['Presidência', 'Diretoria Institucional', 'Gerência de Marca'],
    'oportunista': ['Agência de Mídia', 'Diretor de Growth', 'Equipe de Ativação'],
}

T = {
 'oferta': {
  'agressiva': [
   "Vamos direto ao ponto: a {empresa} quer o {posicao} do {clube}. Oferecemos {valor} por temporada, contrato de {anos}. A proposta vale até {validade}.",
   "O {clube} está em evidência e a {empresa} quer estar junto. {valor} por ano pelo {posicao}, {anos}. Precisamos de resposta até {validade}.",
   "Proposta firme da {empresa}: {valor} anuais pelo {posicao}, {anos} de contrato. Não costumamos esperar muito — prazo até {validade}.",
  ],
  'paciente': [
   "Olá! A {empresa} acompanha o {clube} há algum tempo e gostaria de abrir uma conversa sobre o {posicao}. Nossa proposta inicial é de {valor} por temporada, por {anos}. Fiquem à vontade para avaliar até {validade}.",
   "Prezados, temos interesse em construir uma parceria de longo prazo. Para o {posicao}, sugerimos {valor} por ano durante {anos}. Aguardamos retorno até {validade}.",
   "A {empresa} gostaria de associar sua marca ao {clube}. Pensamos no {posicao}, com investimento de {valor} por temporada ({anos}). Prazo para resposta: {validade}.",
  ],
  'fiel': [
   "A {empresa} acredita em parcerias duradouras. Gostaríamos de estampar nossa marca no {posicao} do {clube}: {valor} por ano, contrato de {anos}. Proposta válida até {validade}.",
   "Somos uma empresa que valoriza tradição, e o {clube} tem muito disso. Oferecemos {valor} anuais pelo {posicao}, por {anos}. Resposta até {validade}.",
  ],
  'oportunista': [
   "Vimos o momento do {clube} ({forma}) e queremos aproveitar a visibilidade. {valor} por temporada pelo {posicao}, {anos}. Proposta só até {validade}.",
   "Oportunidade rápida: a {empresa} paga {valor} por ano pelo {posicao} do {clube}, {anos}. Se não fecharmos até {validade}, vamos procurar outro clube.",
   "Campanha nova da {empresa} começando! Queremos o {posicao} do {clube}: {valor} anuais, {anos}. Validade até {validade}.",
  ],
 },
 'contraproposta_aceita': {
  'agressiva': ["Ok, vocês negociam bem. Fechamos em {valor} por temporada pelo {posicao}. Mandem o contrato.",
                "Aceitamos {valor} por ano. Mas esperamos resultados em campo."],
  'paciente': ["Avaliamos internamente e conseguimos chegar a {valor} por temporada. Será um prazer fechar com o {clube}.",
               "Boa notícia: a diretoria aprovou {valor} anuais para o {posicao}. Podemos seguir com a assinatura."],
  'fiel': ["Pelo {clube}, fazemos esse esforço: {valor} por ano. Que seja o início de uma longa parceria.",
           "Aceitamos {valor} anuais. Confiamos no projeto do clube."],
  'oportunista': ["Fechado em {valor} por temporada — mas precisamos ativar a marca logo.",
                  "Tudo bem, {valor} por ano. Vamos aproveitar o momento."],
 },
 'contraproposta_meio': {
  'agressiva': ["{pedido} é demais. Subimos para {valor} por temporada e essa é a última oferta. Prazo até {validade}.",
                "Não chegamos a {pedido}. Nosso teto é {valor} por ano. Válido até {validade}."],
  'paciente': ["Entendemos o pedido de {pedido}, mas conseguimos {valor} por temporada. Podemos fechar nesse valor? A proposta fica aberta até {validade}.",
               "Fizemos as contas e chegamos a {valor} anuais. Esperamos que atenda. Aguardamos até {validade}."],
  'fiel': ["Não alcançamos {pedido}, mas melhoramos para {valor} por ano. Prazo até {validade}.",
           "Nosso esforço máximo é {valor} anuais. Contamos com vocês até {validade}."],
  'oportunista': ["{pedido}? Fica difícil. {valor} por temporada e fechamos agora — até {validade}.",
                  "Podemos ir a {valor} por ano, nada mais. Até {validade}."],
 },
 'contraproposta_recusada': {
  'agressiva': ["Sem acordo. {pedido} está fora da realidade. Retiramos a proposta.",
                "Não vamos pagar {pedido}. A {empresa} segue outro caminho."],
  'paciente': ["Infelizmente não conseguimos chegar a {pedido}. Mantemos as portas abertas para o futuro.",
               "Agradecemos a conversa, mas {pedido} está acima do nosso orçamento. Quem sabe numa próxima oportunidade."],
  'fiel': ["Não podemos chegar a {pedido} agora. Seguimos torcendo pelo {clube}.",
           "Lamentamos, mas o valor de {pedido} não cabe no nosso planejamento."],
  'oportunista': ["{pedido}? Esquece. Já temos outro clube interessado.",
                  "Sem condições. Vamos investir em outro lugar."],
 },
 'resposta_procura_sim': {
  'agressiva': ["Recebemos a proposta do {clube}. Topamos: {valor} por temporada pelo {posicao}, {anos}. Vamos assinar.",],
  'paciente': ["Que bom receber o contato do {clube}! Aceitamos a proposta de {valor} anuais pelo {posicao}, por {anos}.",
               "Avaliamos com carinho e aceitamos: {valor} por ano no {posicao}, durante {anos}."],
  'fiel': ["Será uma honra. Aceitamos {valor} por temporada pelo {posicao}, {anos}.",],
  'oportunista': ["Bora! {valor} por ano no {posicao}, {anos}. Fechado.",],
 },
 'resposta_procura_nao': {
  'agressiva': ["Não temos interesse no momento. O {clube} precisa mostrar mais em campo.",
                "Proposta recusada. O valor não faz sentido para a {empresa} agora."],
  'paciente': ["Agradecemos o contato, mas nosso orçamento de patrocínio para esta temporada já está comprometido.",
               "Obrigado pela proposta. No momento, não conseguimos avançar."],
  'fiel': ["Agradecemos muito, mas já temos compromissos com outros parceiros neste período."],
  'oportunista': ["Hoje não. Se o {clube} engatar uma boa sequência, voltamos a conversar.",
                  "Passamos. A fase do time ({forma}) não ajuda a nossa campanha."],
 },
 'boas_vindas': {
  '_': ["Contrato assinado! A marca {empresa} estará no {posicao} do {clube} a partir de {inicio}. Valor: {valor} por temporada, durante {anos}."],
 },
 'pagamento': {
  '_': ["A {empresa} realizou o pagamento de {valor} referente ao patrocínio do {posicao}. O valor foi creditado no caixa do clube."],
 },
 'fim_contrato': {
  '_': ["O contrato da {empresa} no {posicao} chegou ao fim. O espaço está livre para novos patrocinadores."],
 },
 'ameaca': {
  'agressiva': ["A sequência recente ({forma}) preocupa a {empresa}. Se o desempenho não melhorar, vamos rever o contrato do {posicao}.",],
  'paciente': ["Estamos acompanhando a fase do time ({forma}) com atenção. Esperamos uma reação nos próximos jogos.",],
  'fiel': ["Momentos difíceis acontecem ({forma}). Seguimos juntos, mas a diretoria da {empresa} pediu uma reação.",],
  'oportunista': ["Do jeito que está ({forma}), a marca {empresa} perde exposição positiva. Precisamos de resultados ou vamos sair.",],
 },
 'rescisao': {
  '_': ["A {empresa} decidiu rescindir o contrato do {posicao} por causa dos resultados ({forma}). O espaço ficará livre."],
 },
 'rescisao_empresa': {
  '_': ["A {empresa} passou por um corte de orçamento de marketing e decidiu encerrar o patrocínio do {posicao}. Conforme o contrato, pagaremos a multa de {valor} ao clube."],
 },
 'rescisao_paga': {
  '_': ["Com a fase atual ({forma}), a {empresa} decidiu deixar o {posicao}. Como o contrato não tem cláusula de desempenho, pagaremos a multa de {valor} ao clube."],
 },
 'rescisao_clube': {
  'agressiva': ["Recebemos o aviso de rescisão do {posicao}. A multa de {valor} será cobrada. A {empresa} não esquece esse tipo de atitude.",],
  'paciente': ["Lamentamos a decisão do clube de encerrar o contrato do {posicao}. A multa contratual de {valor} será descontada. Desejamos sorte.",],
  'fiel': ["É uma pena encerrar essa parceria. Conforme o contrato, a multa de {valor} será aplicada. Seguiremos torcendo.",],
  'oportunista': ["Rescisão recebida. Multa de {valor} cobrada. Bola pra frente.",],
 },
 'expirou': {
  '_': ["A proposta da {empresa} para o {posicao} expirou sem resposta."],
 },
}

ASSUNTOS = {
    'oferta': ['Proposta de patrocínio', 'Interesse no {posicao}', 'Nova proposta: {empresa}'],
    'contraproposta_aceita': ['Negociação concluída'], 'contraproposta_meio': ['Nova contraproposta'],
    'contraproposta_recusada': ['Negociação encerrada'], 'resposta_procura_sim': ['Resposta à sua proposta'],
    'resposta_procura_nao': ['Resposta à sua proposta'], 'boas_vindas': ['Contrato assinado'],
    'pagamento': ['Pagamento recebido'], 'fim_contrato': ['Fim de contrato'], 'ameaca': ['Preocupação com a fase'],
    'rescisao': ['Rescisão de contrato'], 'rescisao_empresa': ['Rescisão de contrato'],
    'rescisao_clube': ['Rescisão confirmada'], 'rescisao_paga': ['Rescisão de contrato'], 'expirou': ['Proposta expirada'],
}


def texto(tipo, personalidade, rnd: random.Random, **v):
    grupo = T[tipo]
    opcoes = grupo.get(personalidade) or grupo.get('_') or next(iter(grupo.values()))
    corpo = rnd.choice(opcoes).format(**v)
    assunto = rnd.choice(ASSUNTOS[tipo]).format(**v)
    return assunto, corpo
