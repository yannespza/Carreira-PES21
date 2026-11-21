"""IA opcional (desligada por padrão): Ollama no próprio PC ou uma API na nuvem compatível com OpenAI/Gemini.

Regras de segurança do app:
- toda resposta tem de ser JSON com as chaves esperadas; números fora da faixa são cortados (-5 a +5);
- tempo máximo de 8 segundos; qualquer falha devolve None e o app usa o texto pronto (modo "Desligada");
- a chave da API fica só no config do app no seu PC, nunca vai para a tela.
"""
import json
import re
import urllib.request

TIMEOUT = 8
ESTILOS = ['humilde', 'corporativo', 'empolgar', 'provocar', 'culpa', 'expor', 'proteger', 'arbitragem', 'pressao']


def _post(url, corpo, headers=None, timeout=TIMEOUT):
    req = urllib.request.Request(url, data=json.dumps(corpo).encode('utf-8'),
                                 headers={'Content-Type': 'application/json', **(headers or {})})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read().decode('utf-8'))


def modelos_ollama(url='http://localhost:11434'):
    try:
        with urllib.request.urlopen(url.rstrip('/') + '/api/tags', timeout=3) as r:
            return [m['name'] for m in json.loads(r.read().decode('utf-8')).get('models', [])]
    except Exception:
        return []


def _json_do_texto(t):
    t = (t or '').strip()
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


def gerar_json(cfg, sistema, pedido):
    """Chama a IA configurada e devolve um dicionário, ou None (desligada, erro ou demora)."""
    modo = (cfg or {}).get('ia_modo', 'desligada')
    try:
        if modo == 'ollama':
            url = (cfg.get('ia_ollama_url') or 'http://localhost:11434').rstrip('/') + '/api/chat'
            r = _post(url, {'model': cfg.get('ia_modelo') or 'gemma3:12b', 'stream': False, 'format': 'json',
                            'keep_alive': '5m', 'options': {'temperature': 0.7},
                            'messages': [{'role': 'system', 'content': sistema}, {'role': 'user', 'content': pedido}]})
            return _json_do_texto((r.get('message') or {}).get('content'))
        if modo == 'nuvem':
            url = cfg.get('ia_nuvem_url') or 'https://api.openai.com/v1/chat/completions'
            chave = cfg.get('ia_chave') or ''
            if 'generativelanguage.googleapis.com' in url:
                r = _post(url + ('&' if '?' in url else '?') + 'key=' + chave,
                          {'systemInstruction': {'parts': [{'text': sistema}]},
                           'contents': [{'role': 'user', 'parts': [{'text': pedido}]}],
                           'generationConfig': {'responseMimeType': 'application/json'}})
                return _json_do_texto(r['candidates'][0]['content']['parts'][0]['text'])
            r = _post(url, {'model': cfg.get('ia_modelo') or 'gpt-4o-mini', 'response_format': {'type': 'json_object'},
                            'messages': [{'role': 'system', 'content': sistema}, {'role': 'user', 'content': pedido}]},
                      {'Authorization': 'Bearer ' + chave})
            return _json_do_texto(r['choices'][0]['message']['content'])
    except Exception:
        return None
    return None


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
    t = (resposta or '').lower()
    pont = {k: sum(t.count(p) for p in ps) for k, ps in PALAVRAS.items()}
    estilo = max(pont, key=pont.get) if max(pont.values()) else 'corporativo'
    tor, dire, vest = EFEITO[estilo]
    return {'estilo': estilo, 'torcida': tor, 'diretoria': dire, 'vestiario': vest, 'imprensa': 0, 'reacao': '',
            'fonte': 'regras'}
