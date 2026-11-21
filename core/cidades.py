"""Cidade, região e altitude dos clubes (Brasil e principais da CONMEBOL), achados pelo nome do time no patch.

Usado pelo clima da partida, pela altitude e pela logística de viagem. O nome do patch é comparado sem acento
e em minúsculas; a primeira chave contida no nome vence (as mais específicas vêm primeiro).
"""
import re
import unicodedata

# chave do nome -> (cidade, UF/país, região, altitude em metros, latitude, longitude)
# regiões: sul, sudeste, sp_interior, nordeste, centro_oeste, norte, serra, altitude (andes), platina, pacifico, tropical
CLUBES = [
    ('red bull bragantino', 'Bragança Paulista', 'SP', 'sp_interior', 817, -22.95, -46.54),
    ('bragantino', 'Bragança Paulista', 'SP', 'sp_interior', 817, -22.95, -46.54),
    ('ponte preta', 'Campinas', 'SP', 'sp_interior', 685, -22.91, -47.06),
    ('guarani', 'Campinas', 'SP', 'sp_interior', 685, -22.91, -47.06),
    ('mirassol', 'Mirassol', 'SP', 'sp_interior', 580, -20.82, -49.52),
    ('novorizontino', 'Novo Horizonte', 'SP', 'sp_interior', 450, -21.47, -49.22),
    ('ituano', 'Itu', 'SP', 'sp_interior', 583, -23.26, -47.30),
    ('botafogo-sp', 'Ribeirão Preto', 'SP', 'sp_interior', 546, -21.17, -47.81),
    ('palmeiras', 'São Paulo', 'SP', 'sudeste', 760, -23.53, -46.68),
    ('corinthians', 'São Paulo', 'SP', 'sudeste', 760, -23.55, -46.47),
    ('sao paulo', 'São Paulo', 'SP', 'sudeste', 760, -23.60, -46.72),
    ('santos', 'Santos', 'SP', 'sudeste', 5, -23.95, -46.33),
    ('flamengo', 'Rio de Janeiro', 'RJ', 'sudeste', 10, -22.91, -43.23),
    ('fluminense', 'Rio de Janeiro', 'RJ', 'sudeste', 10, -22.91, -43.23),
    ('vasco', 'Rio de Janeiro', 'RJ', 'sudeste', 10, -22.89, -43.23),
    ('botafogo', 'Rio de Janeiro', 'RJ', 'sudeste', 10, -22.89, -43.29),
    ('atletico mineiro', 'Belo Horizonte', 'MG', 'sudeste', 852, -19.87, -43.97),
    ('atletico-mg', 'Belo Horizonte', 'MG', 'sudeste', 852, -19.87, -43.97),
    ('cruzeiro', 'Belo Horizonte', 'MG', 'sudeste', 852, -19.87, -43.97),
    ('america mineiro', 'Belo Horizonte', 'MG', 'sudeste', 852, -19.87, -43.97),
    ('america-mg', 'Belo Horizonte', 'MG', 'sudeste', 852, -19.87, -43.97),
    ('athletico', 'Curitiba', 'PR', 'sul', 935, -25.45, -49.28),
    ('atletico paranaense', 'Curitiba', 'PR', 'sul', 935, -25.45, -49.28),
    ('coritiba', 'Curitiba', 'PR', 'sul', 935, -25.42, -49.26),
    ('operario', 'Ponta Grossa', 'PR', 'sul', 975, -25.09, -50.16),
    ('gremio', 'Porto Alegre', 'RS', 'sul', 10, -29.97, -51.19),
    ('internacional', 'Porto Alegre', 'RS', 'sul', 10, -30.07, -51.24),
    ('juventude', 'Caxias do Sul', 'RS', 'serra', 817, -29.17, -51.18),
    ('chapecoense', 'Chapecó', 'SC', 'sul', 674, -27.10, -52.62),
    ('avai', 'Florianópolis', 'SC', 'sul', 3, -27.59, -48.55),
    ('figueirense', 'Florianópolis', 'SC', 'sul', 3, -27.59, -48.55),
    ('criciuma', 'Criciúma', 'SC', 'sul', 46, -28.68, -49.37),
    ('bahia', 'Salvador', 'BA', 'nordeste', 8, -12.98, -38.50),
    ('vitoria', 'Salvador', 'BA', 'nordeste', 8, -12.92, -38.46),
    ('sport', 'Recife', 'PE', 'nordeste', 4, -8.06, -34.90),
    ('nautico', 'Recife', 'PE', 'nordeste', 4, -8.04, -34.89),
    ('santa cruz', 'Recife', 'PE', 'nordeste', 4, -8.03, -34.89),
    ('fortaleza', 'Fortaleza', 'CE', 'nordeste', 21, -3.81, -38.52),
    ('ceara', 'Fortaleza', 'CE', 'nordeste', 21, -3.81, -38.52),
    ('crb', 'Maceió', 'AL', 'nordeste', 7, -9.66, -35.74),
    ('csa', 'Maceió', 'AL', 'nordeste', 7, -9.66, -35.74),
    ('abc', 'Natal', 'RN', 'nordeste', 30, -5.83, -35.21),
    ('sampaio correa', 'São Luís', 'MA', 'nordeste', 24, -2.53, -44.30),
    ('goias', 'Goiânia', 'GO', 'centro_oeste', 749, -16.68, -49.26),
    ('atletico goianiense', 'Goiânia', 'GO', 'centro_oeste', 749, -16.68, -49.26),
    ('atletico-go', 'Goiânia', 'GO', 'centro_oeste', 749, -16.68, -49.26),
    ('vila nova', 'Goiânia', 'GO', 'centro_oeste', 749, -16.68, -49.26),
    ('cuiaba', 'Cuiabá', 'MT', 'centro_oeste', 165, -15.60, -56.10),
    ('brasilia', 'Brasília', 'DF', 'centro_oeste', 1172, -15.78, -47.93),
    ('paysandu', 'Belém', 'PA', 'norte', 10, -1.45, -48.49),
    ('remo', 'Belém', 'PA', 'norte', 10, -1.45, -48.49),
    ('amazonas', 'Manaus', 'AM', 'norte', 92, -3.12, -60.02),
    # CONMEBOL
    ('always ready', 'El Alto', 'Bolívia', 'altitude', 4090, -16.50, -68.19),
    ('bolivar', 'La Paz', 'Bolívia', 'altitude', 3640, -16.50, -68.12),
    ('the strongest', 'La Paz', 'Bolívia', 'altitude', 3640, -16.50, -68.12),
    ('nacional potosi', 'Potosí', 'Bolívia', 'altitude', 3900, -19.58, -65.75),
    ('real potosi', 'Potosí', 'Bolívia', 'altitude', 3900, -19.58, -65.75),
    ('oriente petrolero', 'Santa Cruz de la Sierra', 'Bolívia', 'tropical', 416, -17.78, -63.18),
    ('blooming', 'Santa Cruz de la Sierra', 'Bolívia', 'tropical', 416, -17.78, -63.18),
    ('wilstermann', 'Cochabamba', 'Bolívia', 'altitude', 2558, -17.39, -66.16),
    ('ldu', 'Quito', 'Equador', 'altitude', 2850, -0.18, -78.47),
    ('liga de quito', 'Quito', 'Equador', 'altitude', 2850, -0.18, -78.47),
    ('aucas', 'Quito', 'Equador', 'altitude', 2850, -0.25, -78.53),
    ('el nacional', 'Quito', 'Equador', 'altitude', 2850, -0.18, -78.47),
    ('universidad catolica (ecu', 'Quito', 'Equador', 'altitude', 2850, -0.18, -78.47),
    ('independiente del valle', 'Sangolquí', 'Equador', 'altitude', 2500, -0.31, -78.45),
    ('barcelona sc', 'Guayaquil', 'Equador', 'tropical', 4, -2.19, -79.92),
    ('emelec', 'Guayaquil', 'Equador', 'tropical', 4, -2.19, -79.88),
    ('cusco', 'Cusco', 'Peru', 'altitude', 3400, -13.52, -71.97),
    ('cienciano', 'Cusco', 'Peru', 'altitude', 3400, -13.52, -71.97),
    ('garcilaso', 'Cusco', 'Peru', 'altitude', 3400, -13.52, -71.97),
    ('binacional', 'Juliaca', 'Peru', 'altitude', 3825, -15.50, -70.13),
    ('melgar', 'Arequipa', 'Peru', 'altitude', 2335, -16.40, -71.54),
    ('universitario', 'Lima', 'Peru', 'pacifico', 154, -12.06, -76.94),
    ('alianza lima', 'Lima', 'Peru', 'pacifico', 154, -12.07, -77.02),
    ('sporting cristal', 'Lima', 'Peru', 'pacifico', 154, -12.03, -77.04),
    ('millonarios', 'Bogotá', 'Colômbia', 'altitude', 2640, 4.65, -74.08),
    ('santa fe', 'Bogotá', 'Colômbia', 'altitude', 2640, 4.65, -74.08),
    ('atletico nacional', 'Medellín', 'Colômbia', 'tropical', 1495, 6.26, -75.59),
    ('independiente medellin', 'Medellín', 'Colômbia', 'tropical', 1495, 6.26, -75.59),
    ('junior', 'Barranquilla', 'Colômbia', 'tropical', 18, 10.93, -74.80),
    ('deportes tolima', 'Ibagué', 'Colômbia', 'tropical', 1285, 4.43, -75.21),
    ('america de cali', 'Cali', 'Colômbia', 'tropical', 1018, 3.43, -76.54),
    ('deportivo cali', 'Cali', 'Colômbia', 'tropical', 1018, 3.43, -76.54),
    ('river plate', 'Buenos Aires', 'Argentina', 'platina', 25, -34.55, -58.45),
    ('boca juniors', 'Buenos Aires', 'Argentina', 'platina', 25, -34.64, -58.36),
    ('racing', 'Avellaneda', 'Argentina', 'platina', 25, -34.67, -58.37),
    ('independiente', 'Avellaneda', 'Argentina', 'platina', 25, -34.67, -58.37),
    ('san lorenzo', 'Buenos Aires', 'Argentina', 'platina', 25, -34.65, -58.44),
    ('lanus', 'Lanús', 'Argentina', 'platina', 25, -34.71, -58.39),
    ('velez', 'Buenos Aires', 'Argentina', 'platina', 25, -34.64, -58.52),
    ('argentinos', 'Buenos Aires', 'Argentina', 'platina', 25, -34.61, -58.47),
    ('huracan', 'Buenos Aires', 'Argentina', 'platina', 25, -34.64, -58.40),
    ('estudiantes', 'La Plata', 'Argentina', 'platina', 25, -34.91, -57.94),
    ('gimnasia', 'La Plata', 'Argentina', 'platina', 25, -34.91, -57.94),
    ('talleres', 'Córdoba', 'Argentina', 'platina', 390, -31.37, -64.25),
    ('belgrano', 'Córdoba', 'Argentina', 'platina', 390, -31.42, -64.21),
    ('rosario central', 'Rosario', 'Argentina', 'platina', 25, -32.91, -60.67),
    ('newell', 'Rosario', 'Argentina', 'platina', 25, -32.96, -60.66),
    ('defensa y justicia', 'Florencio Varela', 'Argentina', 'platina', 25, -34.80, -58.27),
    ('godoy cruz', 'Mendoza', 'Argentina', 'platina', 750, -32.89, -68.87),
    ('penarol', 'Montevidéu', 'Uruguai', 'platina', 43, -34.83, -56.09),
    ('nacional', 'Montevidéu', 'Uruguai', 'platina', 43, -34.88, -56.16),
    ('defensor', 'Montevidéu', 'Uruguai', 'platina', 43, -34.91, -56.17),
    ('liverpool (uru', 'Montevidéu', 'Uruguai', 'platina', 43, -34.85, -56.20),
    ('olimpia', 'Assunção', 'Paraguai', 'tropical', 43, -25.27, -57.60),
    ('cerro porteno', 'Assunção', 'Paraguai', 'tropical', 43, -25.30, -57.62),
    ('libertad', 'Assunção', 'Paraguai', 'tropical', 43, -25.28, -57.60),
    ('guarani (par', 'Assunção', 'Paraguai', 'tropical', 43, -25.28, -57.60),
    ('colo-colo', 'Santiago', 'Chile', 'pacifico', 570, -33.51, -70.61),
    ('colo colo', 'Santiago', 'Chile', 'pacifico', 570, -33.51, -70.61),
    ('universidad de chile', 'Santiago', 'Chile', 'pacifico', 570, -33.46, -70.61),
    ('u. de chile', 'Santiago', 'Chile', 'pacifico', 570, -33.46, -70.61),
    ('universidad catolica', 'Santiago', 'Chile', 'pacifico', 570, -33.41, -70.53),
    ('deportivo tachira', 'San Cristóbal', 'Venezuela', 'tropical', 825, 7.77, -72.22),
    ('caracas', 'Caracas', 'Venezuela', 'tropical', 900, 10.49, -66.88),
]


def _norm(s):
    s = unicodedata.normalize('NFKD', str(s or '')).encode('ascii', 'ignore').decode().lower()
    return ' '.join(s.replace('.', ' ').split())


def do_time(nome):
    """{'cidade','uf','regiao','altitude','lat','lon'} do clube, ou None se não estiver na lista."""
    n = _norm(nome)
    if not n:
        return None
    for chave, cidade, uf, reg, alt, lat, lon in CLUBES:
        if re.search(r'(?<![a-z])' + re.escape(_norm(chave)) + r'(?![a-z])', n):
            return {'cidade': cidade, 'uf': uf, 'regiao': reg, 'altitude': alt, 'lat': lat, 'lon': lon}
    return None


def distancia_km(a, b):
    """Distância em linha reta entre duas cidades (fórmula de haversine)."""
    if not a or not b:
        return None
    from math import radians, sin, cos, asin, sqrt
    la1, lo1, la2, lo2 = map(radians, (a['lat'], a['lon'], b['lat'], b['lon']))
    h = sin((la2 - la1) / 2) ** 2 + cos(la1) * cos(la2) * sin((lo2 - lo1) / 2) ** 2
    return round(2 * 6371 * asin(sqrt(h)))
