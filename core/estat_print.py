"""Estatísticas da partida pelo print da tela (intervalo e fim de jogo), lidas por uma IA que entende imagem.

Por que assim: a busca na memória (captura.py, 21/11/2026) não achou as estatísticas; o jogo provavelmente
nem guarda o total do time. A tela de "Intervalo" e "Fim de jogo" mostra tudo, então o app tira prints da tela
(Pillow ImageGrab, só no Windows) e o modelo do Ollama com visão (gemma4) devolve os números em JSON.

Fluxo: o módulo ao vivo (AppCarreiraAoVivo.lua) avisa a troca de período e o fim; o app chama `Sessao.iniciar`
que tira um print a cada 3 s por até 90 s e manda cada um (sem repetir prints iguais) para a IA até um bater com
a tela pedida. Também dá para mandar uma foto (do celular) pela aba Jogo > Estatísticas.
"""
import base64
import hashlib
import io
import os
import threading
import time

from core import ia

CAMPOS = ['posse', 'chutes', 'chutes_gol', 'faltas', 'impedimentos', 'escanteios', 'cobrancas_falta',
          'passes', 'passes_certos', 'cruzamentos', 'interceptacoes', 'desarmes', 'defesas']
ROTULOS = {'posse': 'Posse de bola (%)', 'chutes': 'Chutes', 'chutes_gol': 'Chutes a gol', 'faltas': 'Faltas',
           'impedimentos': 'Impedimentos', 'escanteios': 'Escanteios', 'cobrancas_falta': 'Cobranças de falta',
           'passes': 'Passes', 'passes_certos': 'Passes certos', 'cruzamentos': 'Cruzamentos',
           'interceptacoes': 'Interceptações', 'desarmes': 'Desarmes', 'defesas': 'Defesas'}

SISTEMA = ('Você lê telas do jogo de futebol eFootball PES 2021 e devolve só JSON. Nunca invente números: '
           'se a imagem não for a tela de estatísticas da partida, responda {"tela": "outra"}.')
PEDIDO = '''Esta imagem é a tela de estatísticas da partida ("Intervalo", "Fim de jogo" ou "Estatísticas dos times")?
Se for, a coluna da ESQUERDA é o time da casa e a da DIREITA é o time de fora; os nomes das linhas ficam no meio.
Linhas: "Posse de bola" (porcentagem), "Chutes (a gol)" = chutes e, entre parênteses, chutes a gol,
"Faltas (impedimento)" = faltas e, entre parênteses, impedimentos, "Escanteios", "Cobranças de falta",
"Passes (Certos)" = passes e, entre parênteses, passes certos, "Cruzamentos", "Interceptações", "Desarmes", "Defesas".
Responda só com JSON neste formato (números inteiros):
{"tela": "intervalo" ou "fim" ou "pausa" ou "outra", "time_casa": "...", "time_fora": "...", "placar": [casa, fora],
 "casa": {"posse": 0, "chutes": 0, "chutes_gol": 0, "faltas": 0, "impedimentos": 0, "escanteios": 0,
          "cobrancas_falta": 0, "passes": 0, "passes_certos": 0, "cruzamentos": 0, "interceptacoes": 0,
          "desarmes": 0, "defesas": 0},
 "fora": {mesmos campos}}
Use "intervalo" se o título for Intervalo, "fim" se for Fim de jogo, "pausa" se for o Menu de Pausa.'''


def _int(v):
    try:
        return int(str(v).replace('%', '').strip())
    except (TypeError, ValueError):
        return None


def validar(j):
    """Confere se a leitura faz sentido. Devolve (dados limpos, motivo do erro)."""
    if not isinstance(j, dict):
        return None, 'resposta vazia'
    tela = str(j.get('tela') or '').lower()
    if tela not in ('intervalo', 'fim', 'pausa'):
        return None, 'não era a tela de estatísticas'
    out = {'tela': tela, 'time_casa': str(j.get('time_casa') or '')[:40], 'time_fora': str(j.get('time_fora') or '')[:40]}
    pl = j.get('placar') or []
    out['placar'] = [_int(pl[0]), _int(pl[1])] if isinstance(pl, list) and len(pl) == 2 else None
    for lado in ('casa', 'fora'):
        d = j.get(lado) or {}
        out[lado] = {k: _int(d.get(k)) for k in CAMPOS}
        if any(v is None or v < 0 or v > 999 for v in out[lado].values()):
            return None, 'faltou algum número'
        x = out[lado]
        if x['passes_certos'] > x['passes'] or x['chutes_gol'] > x['chutes'] or x['posse'] > 100:
            return None, 'números incoerentes (certos maior que o total)'
    if abs(out['casa']['posse'] + out['fora']['posse'] - 100) > 1:
        return None, 'a posse não soma 100%'
    return out, ''


def jpeg_b64(img, largura=1600):
    img = img.convert('RGB')
    if img.width > largura:
        img = img.resize((largura, round(img.height * largura / img.width)))
    b = io.BytesIO()
    img.save(b, 'JPEG', quality=88)
    return base64.b64encode(b.getvalue()).decode('ascii')


def ler(cfg, img):
    """Lê uma imagem (PIL). Devolve (dados, motivo)."""
    j = ia.ler_imagem_json(cfg, SISTEMA, PEDIDO, [jpeg_b64(img)])
    if j is None:
        return None, ia.ULTIMO_ERRO['texto'] or 'a IA não respondeu'
    return validar(j)


def capturar():
    """Print da tela principal (Windows). None se não der."""
    try:
        from PIL import ImageGrab
        return ImageGrab.grab()
    except Exception:
        return None


def _escura(img):
    p = img.convert('L').resize((64, 36))
    v = list(p.getdata())
    return sum(v) / len(v) < 8


def _marca(img):
    return hashlib.md5(img.convert('L').resize((48, 27)).tobytes()).hexdigest()


class Sessao:
    """Tira prints em sequência e lê com a IA até achar a tela pedida ('intervalo' ou 'fim')."""

    def __init__(self, cfg, pasta, ao_ler, log=print):
        self.cfg, self.pasta, self.ao_ler, self.log = cfg, pasta, ao_ler, log
        self.rodando = {}
        self.status = {'texto': 'Esperando a próxima partida.', 'quando': None}
        os.makedirs(pasta, exist_ok=True)

    def _st(self, txt):
        self.status = {'texto': txt, 'quando': time.strftime('%H:%M:%S')}
        self.log('estatísticas por print:', txt)

    def iniciar(self, alvo, contexto, duracao=90, passo=3, max_leituras=15):
        if self.rodando.get(alvo):
            return
        self.rodando[alvo] = True
        threading.Thread(target=self._rodar, args=(alvo, contexto, duracao, passo, max_leituras), daemon=True).start()

    def _rodar(self, alvo, contexto, duracao, passo, max_leituras):
        try:
            fim, vistos, leituras, ultimo = time.time() + duracao, set(), 0, ''
            self._st(f'Tirando prints do {"intervalo" if alvo == "intervalo" else "fim de jogo"}...')
            while time.time() < fim and leituras < max_leituras:
                img = capturar()
                if img is None:
                    self._st('Não consegui tirar print da tela (só funciona no Windows).')
                    return
                if _escura(img):
                    ultimo = ('O print saiu preto: o PES deve estar em tela cheia exclusiva. Nas configurações do jogo '
                              '(Settings.exe), troque o modo de tela para "janela sem bordas".')
                    time.sleep(passo)
                    continue
                mk = _marca(img)
                if mk in vistos:
                    time.sleep(passo)
                    continue
                vistos.add(mk)
                leituras += 1
                dados, motivo = ler(self.cfg, img)
                if dados and (dados['tela'] == alvo or (alvo == 'fim' and dados['tela'] == 'fim')):
                    nome = os.path.join(self.pasta, time.strftime('%Y%m%d_%H%M%S_') + alvo + '.jpg')
                    img.convert('RGB').save(nome, 'JPEG', quality=85)
                    self._limpar()
                    self.ao_ler(alvo, dados, contexto, 'print')
                    self._st(f'{"Intervalo" if alvo == "intervalo" else "Fim de jogo"} lido do print.')
                    return
                ultimo = motivo or f'era a tela "{dados["tela"]}"'
                if 'Ollama' in ultimo or 'desligada' in ultimo or 'baixado' in ultimo:
                    break                      # problema de configuração: não adianta insistir
                time.sleep(1)
            self._st(f'Não achei a tela de estatísticas do {alvo} nos prints ({leituras} lidos). Último motivo: {ultimo}. '
                     'Se quiser, mande uma foto da tela pela aba Jogo > Estatísticas.')
        except Exception as e:
            self._st(f'Erro ao ler o print: {e}')
        finally:
            self.rodando[alvo] = False

    def _limpar(self, manter=20):
        try:
            fs = sorted(f for f in os.listdir(self.pasta) if f.endswith('.jpg'))
            for f in fs[:-manter]:
                os.remove(os.path.join(self.pasta, f))
        except OSError:
            pass
