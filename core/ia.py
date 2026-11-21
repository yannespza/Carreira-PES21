"""IA opcional (desligada por padrão): Ollama no próprio PC ou uma API na nuvem compatível com OpenAI/Gemini.

Regras de segurança do app:
- toda resposta tem de ser JSON com as chaves esperadas; números fora da faixa são cortados (-5 a +5);
- tempo máximo de 20 segundos (2 minutos na primeira, enquanto o modelo carrega); qualquer falha devolve None e o app usa o texto pronto (modo "Desligada");
- a chave da API fica só no config do app no seu PC, nunca vai para a tela.
"""
import json
import re
import socket
import time
import urllib.error
import urllib.request

TIMEOUT = 20          # resposta normal (modelo já carregado na placa)
TIMEOUT_CARGA = 120   # primeira chamada: o Ollama ainda está levando o modelo para a placa de vídeo
MANTER = '60m'        # quanto tempo o Ollama segura o modelo na placa depois da última pergunta
ESTILOS = ['humilde', 'corporativo', 'empolgar', 'provocar', 'culpa', 'expor', 'proteger', 'arbitragem', 'pressao']
ULTIMO_ERRO = {'texto': ''}


def _post(url, corpo, headers=None, timeout=TIMEOUT):
    req = urllib.request.Request(url, data=json.dumps(corpo).encode('utf-8'),
                                 headers={'Content-Type': 'application/json', **(headers or {})})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read().decode('utf-8'))


def _base(url):
    # no Windows "localhost" às vezes tenta o endereço IPv6 primeiro e o Ollama só escuta no 127.0.0.1
    return (url or 'http://127.0.0.1:11434').rstrip('/').replace('://localhost', '://127.0.0.1')


def modelos_ollama(url='http://127.0.0.1:11434'):
    try:
        with urllib.request.urlopen(_base(url) + '/api/tags', timeout=3) as r:
            return [m['name'] for m in json.loads(r.read().decode('utf-8')).get('models', [])]
    except Exception:
        return []


def ollama_carregado(cfg):
    """O modelo configurado já está na memória da placa?"""
    try:
        with urllib.request.urlopen(_base(cfg.get('ia_ollama_url')) + '/api/ps', timeout=3) as r:
            nomes = [m.get('name') for m in json.loads(r.read().decode('utf-8')).get('models', [])]
        return _nome(cfg) in nomes or (_nome(cfg) + ':latest') in nomes
    except Exception:
        return False


def _nome(cfg):
    return (cfg.get('ia_modelo') or 'gemma4:12b').strip()


def _json_do_texto(t):
    t = (t or '').strip()
    t = re.sub(r'^```(?:json)?|```$', '', t, flags=re.M).strip()
    try:
        return json.loads(t)
    except ValueError:
        m = re.search(r'\{.*\}', t, re.S)
        if m:
            try:
                return json.loads(m.group(0))
            except ValueError:
                return None
    return None


def _erro_http(e):
    try:
        return json.loads(e.read().decode('utf-8')).get('error') or str(e)
    except Exception:
        return str(e)


def _ollama(cfg, sistema, pedido, timeout):
    url = _base(cfg.get('ia_ollama_url')) + '/api/chat'
    corpo = {'model': _nome(cfg), 'stream': False, 'format': 'json', 'think': False, 'keep_alive': MANTER,
             'options': {'temperature': 0.7},
             'messages': [{'role': 'system', 'content': sistema}, {'role': 'user', 'content': pedido}]}
    try:
        r = _post(url, corpo, timeout=timeout)
    except urllib.error.HTTPError as e:
        msg = _erro_http(e)
        if 'not found' in msg.lower():
            raise RuntimeError(f'O modelo "{_nome(cfg)}" não está baixado. No PowerShell rode: ollama pull {_nome(cfg)}')
        if 'think' not in msg.lower():
            raise RuntimeError(msg)
        corpo.pop('think')          # modelo sem "modo pensar": tenta de novo sem a opção
        r = _post(url, corpo, timeout=timeout)
    msg = r.get('message') or {}
    return _json_do_texto(msg.get('content') or msg.get('thinking'))


def gerar_json(cfg, sistema, pedido, timeout=None):
    """Chama a IA configurada e devolve um dicionário, ou None (desligada, erro ou demora).
    O motivo da última falha fica em ULTIMO_ERRO['texto']."""
    modo = (cfg or {}).get('ia_modo', 'desligada')
    ULTIMO_ERRO['texto'] = ''
    try:
        if modo == 'ollama':
            if timeout is None:
                timeout = TIMEOUT if ollama_carregado(cfg) else TIMEOUT_CARGA
            j = _ollama(cfg, sistema, pedido, timeout)
            if j is None:
                ULTIMO_ERRO['texto'] = 'O modelo respondeu, mas não no formato que o app entende.'
            return j
        if modo == 'nuvem':
            url = cfg.get('ia_nuvem_url') or 'https://api.openai.com/v1/chat/completions'
            chave = cfg.get('ia_chave') or ''
            if 'generativelanguage.googleapis.com' in url:
                r = _post(url + ('&' if '?' in url else '?') + 'key=' + chave,
                          {'systemInstruction': {'parts': [{'text': sistema}]},
                           'contents': [{'role': 'user', 'parts': [{'text': pedido}]}],
                           'generationConfig': {'responseMimeType': 'application/json'}}, timeout=timeout or TIMEOUT)
                return _json_do_texto(r['candidates'][0]['content']['parts'][0]['text'])
            r = _post(url, {'model': cfg.get('ia_modelo') or 'gpt-4o-mini', 'response_format': {'type': 'json_object'},
                            'messages': [{'role': 'system', 'content': sistema}, {'role': 'user', 'content': pedido}]},
                      {'Authorization': 'Bearer ' + chave}, timeout=timeout or TIMEOUT)
            return _json_do_texto(r['choices'][0]['message']['content'])
        ULTIMO_ERRO['texto'] = 'A IA está desligada (escolha "Ollama no meu PC" e clique em Salvar).'
    except urllib.error.URLError as e:
        if isinstance(getattr(e, 'reason', None), (TimeoutError, socket.timeout)) or 'timed out' in str(e):
            ULTIMO_ERRO['texto'] = 'Demorou demais para responder.'
        elif modo == 'ollama':
            ULTIMO_ERRO['texto'] = ('Não achei o Ollama aberto no PC. Abra o Ollama (ícone perto do relógio) '
                                    'ou rode "ollama serve" no PowerShell.')
        else:
            ULTIMO_ERRO['texto'] = 'Sem conexão com o serviço: ' + str(e)
    except (TimeoutError, socket.timeout):
        ULTIMO_ERRO['texto'] = 'Demorou demais para responder.'
    except Exception as e:
        ULTIMO_ERRO['texto'] = str(e)[:200]
    return None


def ler_imagem_json(cfg, sistema, pedido, imagens_b64, timeout=TIMEOUT_CARGA):
    """Manda imagens (JPEG em base64) para um modelo que entende imagem e devolve o JSON da resposta, ou None.
    Ollama: o modelo precisa ter visão (gemma4, por exemplo). O motivo da falha fica em ULTIMO_ERRO."""
    modo = (cfg or {}).get('ia_modo', 'desligada')
    ULTIMO_ERRO['texto'] = ''
    try:
        if modo == 'ollama':
            corpo = {'model': _nome(cfg), 'stream': False, 'format': 'json', 'think': False, 'keep_alive': MANTER,
                     'options': {'temperature': 0},
                     'messages': [{'role': 'system', 'content': sistema},
                                  {'role': 'user', 'content': pedido, 'images': list(imagens_b64)}]}
            url = _base(cfg.get('ia_ollama_url')) + '/api/chat'
            try:
                r = _post(url, corpo, timeout=timeout)
            except urllib.error.HTTPError as e:
                msg = _erro_http(e)
                if 'think' in msg.lower():
                    corpo.pop('think')
                    r = _post(url, corpo, timeout=timeout)
                elif 'not found' in msg.lower():
                    raise RuntimeError(f'O modelo "{_nome(cfg)}" não está baixado. No PowerShell rode: ollama pull {_nome(cfg)}')
                else:
                    raise RuntimeError(msg)
            j = _json_do_texto((r.get('message') or {}).get('content'))
            if j is None:
                ULTIMO_ERRO['texto'] = 'O modelo respondeu, mas não no formato que o app entende.'
            return j
        if modo == 'nuvem':
            url = cfg.get('ia_nuvem_url') or 'https://api.openai.com/v1/chat/completions'
            chave = cfg.get('ia_chave') or ''
            if 'generativelanguage.googleapis.com' in url:
                partes = [{'text': pedido}] + [{'inline_data': {'mime_type': 'image/jpeg', 'data': b}} for b in imagens_b64]
                r = _post(url + ('&' if '?' in url else '?') + 'key=' + chave,
                          {'systemInstruction': {'parts': [{'text': sistema}]}, 'contents': [{'role': 'user', 'parts': partes}],
                           'generationConfig': {'responseMimeType': 'application/json'}}, timeout=timeout)
                return _json_do_texto(r['candidates'][0]['content']['parts'][0]['text'])
            cont = [{'type': 'text', 'text': pedido}] + [{'type': 'image_url', 'image_url': {'url': 'data:image/jpeg;base64,' + b}}
                                                        for b in imagens_b64]
            r = _post(url, {'model': cfg.get('ia_modelo') or 'gpt-4o-mini', 'response_format': {'type': 'json_object'},
                            'messages': [{'role': 'system', 'content': sistema}, {'role': 'user', 'content': cont}]},
                      {'Authorization': 'Bearer ' + chave}, timeout=timeout)
            return _json_do_texto(r['choices'][0]['message']['content'])
        ULTIMO_ERRO['texto'] = 'A IA está desligada. Em Sistema > Inteligência artificial escolha "Ollama no meu PC".'
    except urllib.error.URLError as e:
        ULTIMO_ERRO['texto'] = ('Demorou demais para responder.' if 'timed out' in str(e) else
                                'Não achei o Ollama aberto no PC.' if modo == 'ollama' else 'Sem conexão: ' + str(e))
    except (TimeoutError, socket.timeout):
        ULTIMO_ERRO['texto'] = 'Demorou demais para responder.'
    except Exception as e:
        ULTIMO_ERRO['texto'] = str(e)[:200]
    return None


def testar(cfg):
    """Teste da aba Sistema: espera o modelo carregar e explica o problema em português."""
    modo = (cfg or {}).get('ia_modo', 'desligada')
    mods = modelos_ollama(cfg.get('ia_ollama_url')) if modo == 'ollama' else []
    if modo == 'ollama':
        nome = _nome(cfg)
        if mods and nome not in mods and (nome + ':latest') not in mods:
            return {'ok': False, 'modelos': mods,
                    'erro': f'O modelo "{nome}" não está baixado. No PowerShell rode: ollama pull {nome} '
                            f'(ou escreva um destes no campo: {", ".join(mods)}).'}
    t0 = time.time()
    j = gerar_json(cfg, 'Responda só JSON {"ok": true, "frase": "..."} com uma frase curta de futebol, '
                        'em português do Brasil.', 'teste', timeout=TIMEOUT_CARGA)
    seg = round(time.time() - t0, 1)
    if j:
        return {'ok': True, 'resposta': j, 'segundos': seg, 'modelos': mods}
    erro = ULTIMO_ERRO['texto'] or 'Não respondeu.'
    return {'ok': False, 'erro': erro, 'segundos': seg, 'modelos': mods}


def aquecer(cfg):
    """Carrega o modelo na placa em segundo plano (chamado ao abrir o app e ao abrir a coletiva)."""
    if (cfg or {}).get('ia_modo') != 'ollama' or ollama_carregado(cfg):
        return
    try:
        _post(_base(cfg.get('ia_ollama_url')) + '/api/generate', {'model': _nome(cfg), 'keep_alive': MANTER},
              timeout=TIMEOUT_CARGA)
    except Exception:
        pass


def _clamp(v, lo=-5, hi=5):
    try:
        return int(max(lo, min(hi, round(float(v)))))
    except (TypeError, ValueError):
        return 0


# palavras que puxam cada estilo, para o modo sem IA
PALAVRAS = {
    'culpa': ['culpa minha', 'minha culpa', 'eu errei', 'responsabilidade é minha', 'assumo'],
    'proteger': ['grupo', 'elenco', 'jogadores deram', 'confio nos', 'protejo', 'meus jogadores'],
    'provocar': ['rival', 'eles que', 'freguês', 'chora', 'cutucar'],
    'arbitragem': ['árbitro', 'arbitragem', 'juiz', 'var', 'pênalti claro'],
    'expor': ['fulano errou', 'faltou atitude de', 'não aceito', 'vai ter que melhorar', 'alguns jogadores'],
    'empolgar': ['título', 'campeão', 'vamos ganhar', 'ninguém nos para', 'torcida pode sonhar'],
    'pressao': ['pressão', 'cobrança', 'diretoria precisa', 'precisamos de reforço'],
    'humilde': ['passo a passo', 'humildade', 'trabalhar', 'jogo a jogo', 'pés no chão'],
}
EFEITO = {'humilde': (1, 1, 1), 'corporativo': (0, 1, 0), 'empolgar': (3, -1, 1), 'provocar': (2, -2, 1),
          'culpa': (1, 2, 2), 'expor': (-1, 0, -4), 'proteger': (1, 0, 3), 'arbitragem': (1, -1, 0),
          'pressao': (0, -3, 0)}


def avaliar_resposta(cfg, contexto, pergunta, resposta):
    """Avalia a resposta livre do técnico. Devolve estilo, impactos (-5..+5) e a fonte (ia ou regras)."""
    sistema = ('Você avalia respostas de um técnico de futebol brasileiro em entrevista coletiva. Responda APENAS um '
               'JSON com: estilo (um de ' + ', '.join(ESTILOS) + '), torcida, diretoria, vestiario, imprensa '
               '(inteiros de -5 a 5) e reacao (uma frase curta do jornalista, em português do Brasil).')
    pedido = f'Contexto: {contexto}\nPergunta: {pergunta}\nResposta do técnico: {resposta}'
    j = gerar_json(cfg, sistema, pedido)
    if isinstance(j, dict) and j.get('estilo') in ESTILOS:
        return {'estilo': j['estilo'], 'torcida': _clamp(j.get('torcida')), 'diretoria': _clamp(j.get('diretoria')),
                'vestiario': _clamp(j.get('vestiario')), 'imprensa': _clamp(j.get('imprensa')),
                'reacao': str(j.get('reacao') or '')[:200], 'fonte': 'ia'}
    motivo = ULTIMO_ERRO['texto']
    t = (resposta or '').lower()
    pont = {k: sum(t.count(p) for p in ps) for k, ps in PALAVRAS.items()}
    estilo = max(pont, key=pont.get) if max(pont.values()) else 'corporativo'
    tor, dire, vest = EFEITO[estilo]
    return {'estilo': estilo, 'torcida': tor, 'diretoria': dire, 'vestiario': vest, 'imprensa': 0, 'reacao': '',
            'fonte': 'regras', 'motivo': motivo}
