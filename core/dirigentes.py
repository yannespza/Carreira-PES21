"""Dirigentes de cada clube: presidente, diretor de futebol e assessor de imprensa.

Nomes reais pesquisados em novembro de 2026 (presidente e diretor/executivo de futebol dos brasileiros; presidente
dos estrangeiros). Onde o nome não foi confirmado, fica em branco e o app mostra só o cargo; o técnico pode
preencher na aba Clube > Diretoria. O assessor de imprensa é um personagem do app (nome e personalidade
próprios de cada clube, sempre os mesmos).

Fontes principais: FootHub (executivos da Série A, jul/2026), sites dos clubes e imprensa regional, Wikipédia.
"""
import hashlib
import random
import unicodedata

# id do jogo: (presidente, diretor de futebol)
REAIS = {
    # ---- Série A ----
    137: ('Leila Pereira', 'Anderson Barros'),
    1248: ('Luiz Eduardo Baptista (Bap)', 'José Boto'),
    274: ('Pedro Lourenço', 'Bruno Spindel'),
    2453: ('Emerson Ferretti', 'Carlos Santoro'),
    1249: ('Mattheus Montenegro', 'Paulo Angioni'),
    1247: ('Osmar Stábile', 'Marcelo Paz'),
    1246: ('João Paulo Magalhães', 'Léo Coelho'),
    289: ('Sérgio Coelho', 'Paulo Bracks'),
    2459: ('André Rocha (CEO)', 'Diego Cerri'),
    136: ('Pedrinho', 'Admar Lopes'),
    1254: ('Marcelo Teixeira', 'Alexandre Mattos'),
    1250: ('Odorico Roman', 'Paulo Pelaipe'),
    1255: ('Harry Massis Jr.', 'Rafinha'),
    1252: ('Alessandro Barcellos', 'Fabinho Soldado'),
    1930: ('Mario Celso Petraglia', 'Márcio Lara'),
    1937: ('Fábio Mota', 'Sérgio Papellin'),
    4077: ('Edson Ermenegildo', 'Paulinho'),
    1931: ('Marianna Líbano', 'Jorge Andrade'),
    2697: ('Glauber Gonçalves', 'Luis Vagner Vivian'),
    4108: ('Alex Passos', 'Rafael Lima'),
    # ---- Série B ----
    5143: ('Bruno Cals', 'Pedro Martins (CEO)'),
    2454: ('João Paulo Silva', 'Gabriel Bedê'),
    1936: ('Matheus Souto Maior', 'Ítalo Rodrigues'),
    5142: ('Alessandro Dresch', None),
    5137: ('Fábio Pizzamiglio', None),
    2450: ('Marcus Salum', None),
    1933: ('Paulo Rogério Pinheiro', 'Michel Alves'),
    2451: ('Adson Batista', None),
    5997: ('Genilson da Rocha Santos', None),
    5145: ('Valter Minotto', None),
    2452: ('Bernardo Pessi', None),
    2691: ('Fábio Brasil', None),
    2506: ('Mário Marroquim', 'PC Gusmão'),
    5433: ('Álvaro Góes', None),
    5139: ('Eduardo Esteves', None),
    2465: ('Marco Antonio Eberlin', None),
    1935: ('Bruno Becker', None),
    2408: ('Guilherme Bellintani', None),
    2068: ('Antônio Moreno (Tony)', None),
    5574: ('Xandão Soares', None),
    # ---- Argentina ----
    138: ('Stefano Di Carlo', None), 139: ('Juan Román Riquelme', None), 1237: ('Diego Milito', None),
    1242: ('Gonzalo Belloso', None), 5046: ('Andrés Fassi', None), 1244: ('Fabián Berlanga', None),
    1240: ('Néstor Grindetti', None), 1238: ('Juan Sebastián Verón', None), 1236: ('Cristian Malaspina', None),
    1929: ('Nicolás Russo', None), 1243: ('Marcelo Culotta', None), 2536: ('Luis Fernando Artime', None),
    1922: ('David Garzón', None), 1241: ('Ignacio Astore', None), 1924: ('José Mansur', None),
    2722: ('José Lemme', None), 1927: ('Eduardo Spinosa', None), 2719: ('Mario Leito', None),
    # ---- Uruguai ----
    2491: ('Ignacio Ruglio', None), 2490: ('Ricardo Vairo', None), 2694: ('Diego Franzini', None),
    2484: ('José Luis Palma', None), 2486: ('Germán Barcala', None),
    # ---- Chile ----
    1256: ('Aníbal Mosa', None), 2209: ('Michael Clark', None), 2191: ('Juan Tagle', None),
    2548: ('Jorge Uauy', None), 2545: ('Victoriano Cerda', None),
    # ---- Colômbia ----
    2193: ('Sebastián Arango', None), 1258: ('Enrique Camacho', None), 2361: ('César Camargo', None),
    2657: ('Eduardo Méndez', None),
    # ---- Equador ----
    4034: ('Franklin Tello', None), 4043: ('Isaac Álvarez', None), 4041: ('Antonio Álvarez', None),
    4003: ('José Pileggi', None), 1200: ('Jorge Salazar', None),
    # ---- Paraguai ----
    4044: ('Juan José Zapag', None), 4035: ('Rodrigo Nogués', None), 4036: ('Rubén Di Tore', None),
    # ---- Peru ----
    2216: ('Joel Raffo', None), 2215: ('Franco Velazco (administrador)', None),
    # ---- Bolívia ----
    4040: ('Marcelo Claure', None), 4001: ('Daniel Terrazas', None),
}


def _seed(*p):
    return int(hashlib.md5('|'.join(map(str, p)).encode()).hexdigest()[:8], 16)


# ---------------- personalidades ----------------
PRES_PERFIS = {
    'apaixonado': ('Torcedor de arquibancada que virou presidente. Decide com o coração, comemora junto e '
                   'cobra em público quando o time vai mal.'),
    'empresario': ('Gestor de mercado: olha número, prazo e retorno. Fecha patrocínio pelo valor e pela '
                   'solidez da marca, sem paixão.'),
    'politico': ('Hábil nos bastidores e atento ao conselho. Prefere acordos que agradam a todos e evita '
                 'desgaste com a torcida.'),
    'conservador': ('Cauteloso com o caixa. Prefere contratos longos e seguros a valores altos com risco.'),
}
DIR_PERFIS = {
    'exigente': ('Libera dinheiro, mas cobra resultado com prazo. Não aceita desculpa e põe meta em tudo.'),
    'paciente': ('Acredita em projeto e dá tempo ao técnico. Prefere metas possíveis a promessas grandes.'),
    'calculista': ('Faz conta de tudo: folha, receita, venda de jogador. Só mexe no orçamento com garantia.'),
    'ousado': ('Gosta de apostar alto. Topa dar verba grande, mas a cobrança vem do mesmo tamanho.'),
}
# assessor: estilo de escrita (sobrio, marketeira, veterano) + postura com o técnico
POSTURAS = {
    'parceiro': {'lealdade': 0.9, 'vaza': 0.07, 'txt': 'Parceiro: segura a pressão junto com o técnico.'},
    'diplomatico': {'lealdade': 0.75, 'vaza': 0.12, 'txt': 'Diplomático: evita conflito e mede cada palavra.'},
    'desconfiado': {'lealdade': 0.5, 'vaza': 0.22, 'txt': 'Desconfiado: acha que todo mundo fala demais no vestiário.'},
    'desafiador': {'lealdade': 0.38, 'vaza': 0.3, 'txt': 'Desafiador: questiona as escolhas do técnico e não esconde isso.'},
    'ambicioso': {'lealdade': 0.55, 'vaza': 0.2, 'txt': 'Ambicioso: pensa no próprio nome e adora uma manchete.'},
    'cinico': {'lealdade': 0.42, 'vaza': 0.34, 'txt': 'Veterano cínico: já viu muito técnico cair e não se apega.'},
}
NOMES_ASS = ['Rafael Monteiro', 'Bianca Castanho', 'Jorge Sales', 'Camila Duarte', 'Thiago Rezende', 'Luana Prado',
             'Marcelo Viana', 'Patrícia Lobo', 'Rodrigo Falcão', 'Fernanda Aguiar', 'André Bastos', 'Juliana Freire',
             'Diego Antunes', 'Renata Quintela', 'Felipe Moraes', 'Larissa Teles', 'Gustavo Pimenta', 'Aline Brandão',
             'Eduardo Neves', 'Carolina Paiva', 'Bruno Leal', 'Natália Sampaio', 'Vinícius Coelho', 'Marina Rocha',
             'Henrique Tavares', 'Débora Cunha', 'Otávio Lins', 'Sabrina Matos', 'Caio Ferraz', 'Letícia Arruda']
NOMES_ASS_ES = ['Martín Ferreyra', 'Lucía Benítez', 'Santiago Correa', 'Valentina Ríos', 'Matías Sosa', 'Camila Ortiz',
                'Joaquín Peralta', 'Florencia Vega', 'Nicolás Acosta', 'Paula Medina', 'Federico Ruiz', 'Agustina Paz']
ESTILOS = ['sobrio', 'marketeira', 'veterano']
PERFIL_ESTILO = {'sobrio': 'Escreve de forma sóbria e institucional.',
                 'marketeira': 'Vive de engajamento: emoji, meme e provocação leve.',
                 'veterano': 'Fala direto, sem firula, com cara de redação antiga.'}


def _slug(s):
    return ''.join(ch for ch in unicodedata.normalize('NFKD', s or '').lower() if ch.isalnum())


def de(clube, tid, pais='Brasil', editados=None):
    """Os três dirigentes do clube (sempre os mesmos para o mesmo clube)."""
    r = random.Random(_seed('dirigentes', _slug(clube), tid))
    pres, dirf = REAIS.get(tid, (None, None))
    ed = editados or {}
    pp = r.choice(list(PRES_PERFIS))
    dp = r.choice(list(DIR_PERFIS))
    postura = r.choice(list(POSTURAS))
    estilo = r.choice(ESTILOS)
    nomes = NOMES_ASS if (pais or 'Brasil') == 'Brasil' else NOMES_ASS_ES
    ass_nome = nomes[_seed('ass', _slug(clube), tid) % len(nomes)]
    po = POSTURAS[postura]
    return {
        'presidente': {'nome': ed.get('presidente') or pres, 'real': bool(pres), 'perfil': pp, 'perfil_txt': PRES_PERFIS[pp]},
        'diretor': {'nome': ed.get('diretor') or dirf, 'real': bool(dirf), 'perfil': dp, 'perfil_txt': DIR_PERFIS[dp]},
        'assessor': {'id': f'clube:{_slug(clube)}:{tid}', 'nome': ass_nome, 'estilo': estilo, 'postura': postura,
                     'vaza': po['vaza'] + (0.03 if estilo == 'marketeira' else 0),
                     'lealdade': po['lealdade'], 'perfil': f"{po['txt']} {PERFIL_ESTILO[estilo]}"},
    }


def assinatura(cargo, d, clube):
    """Como a mensagem aparece em Mensagens."""
    nome = (d.get(cargo) or {}).get('nome')
    titulo = {'presidente': 'Presidência', 'diretor': 'Diretoria de futebol'}[cargo]
    return f'{nome} · {titulo}' if nome else f'{titulo} · {clube}'
