"""Cópia do save para análise a distância (o Claude lê pelo GitHub quando o PC está desligado).

Sempre que o jogo grava o save da carreira, o app espera alguns minutos sem mudança e manda uma cópia
para um repositório PRIVADO do GitHub do usuário. Cada dia tem a sua pasta e a cópia do dia é trocada a
cada envio, então no fim do dia fica a última modificação. Junto vai o arquivo do app desta carreira.

Pastas no repositório:
  saves/AAAA-MM-DD/<arquivo do save>     (ex.: saves/2026-11-16/ML00000006)
  saves/AAAA-MM-DD/app_carreira.json     (o que o app guardou da carreira)
  ultimo.json                            (data, hora, arquivo, versão do app)
Ficam só os últimos DIAS_GUARDAR dias.

O token fica só no PC (data/copia_remota.json), nunca vai para a tela nem para o GitHub.
Nada aqui grava no save."""
import base64, datetime as dt, json, os, threading, time, urllib.request, urllib.error

ESPERA_MIN = 10          # minutos sem o save mudar antes de enviar
DIAS_GUARDAR = 7
API = 'https://api.github.com'

status = {'ultimo_envio': None, 'ultimo_arquivo': None, 'erro': None, 'enviando': False}
_lock = threading.Lock()


def _arq(data_dir):
    return os.path.join(data_dir, 'copia_remota.json')


def ler_cfg(data_dir):
    try:
        with open(_arq(data_dir), encoding='utf-8') as f:
            return json.load(f)
    except Exception:
        return {}


def salvar_cfg(data_dir, cfg):
    with open(_arq(data_dir), 'w', encoding='utf-8') as f:
        json.dump(cfg, f, ensure_ascii=False, indent=1)


def publico(data_dir):
    """O que a tela pode ver (sem o token)."""
    c = ler_cfg(data_dir)
    return {'ativo': bool(c.get('ativo') and c.get('token') and c.get('repo')), 'repo': c.get('repo') or '',
            'tem_token': bool(c.get('token')), 'espera_min': ESPERA_MIN, 'dias': DIAS_GUARDAR, **status,
            'enviado_mtime': c.get('enviado_mtime')}


def _req(token, metodo, caminho, corpo=None):
    dados = json.dumps(corpo).encode() if corpo is not None else None
    r = urllib.request.Request(API + caminho, data=dados, method=metodo, headers={
        'Authorization': 'Bearer ' + token, 'Accept': 'application/vnd.github+json',
        'User-Agent': 'CarreiraPES21', 'Content-Type': 'application/json'})
    try:
        with urllib.request.urlopen(r, timeout=120) as resp:
            t = resp.read()
            return json.loads(t) if t else {}
    except urllib.error.HTTPError as e:
        if e.code == 404:
            return None
        msg = e.read().decode(errors='ignore')[:200]
        raise RuntimeError(f'GitHub respondeu {e.code}: {msg}')


def _sha(token, repo, caminho):
    r = _req(token, 'GET', f'/repos/{repo}/contents/{caminho}')
    return r.get('sha') if isinstance(r, dict) else None


def _enviar_arquivo(token, repo, caminho, conteudo, msg):
    corpo = {'message': msg, 'content': base64.b64encode(conteudo).decode()}
    sha = _sha(token, repo, caminho)
    if sha:
        corpo['sha'] = sha
    _req(token, 'PUT', f'/repos/{repo}/contents/{caminho}', corpo)


def _limpar_antigos(token, repo, hoje):
    pastas = _req(token, 'GET', f'/repos/{repo}/contents/saves') or []
    limite = (hoje - dt.timedelta(days=DIAS_GUARDAR - 1)).isoformat()
    for p in pastas:
        if p.get('type') == 'dir' and p['name'] < limite:
            for f in _req(token, 'GET', f'/repos/{repo}/contents/saves/{p["name"]}') or []:
                _req(token, 'DELETE', f'/repos/{repo}/contents/{f["path"]}',
                     {'message': f'remove cópia antiga {p["name"]}', 'sha': f['sha']})


def testar(token, repo):
    """Confere se o token consegue escrever no repositório e se ele é privado."""
    r = _req(token, 'GET', f'/repos/{repo}')
    if r is None:
        return {'ok': False, 'erro': 'Não achei o repositório (confira o nome e se o token tem acesso a ele).'}
    if not r.get('private'):
        return {'ok': False, 'erro': 'O repositório é público. Crie um repositório privado para as cópias do save.'}
    if not (r.get('permissions') or {}).get('push', True):
        return {'ok': False, 'erro': 'O token não tem permissão para escrever nesse repositório.'}
    return {'ok': True}


def enviar(data_dir, save_path, estado_path, versao, forcar=False):
    """Manda a cópia do save de hoje. Devolve True se enviou."""
    c = ler_cfg(data_dir)
    if not (c.get('ativo') and c.get('token') and c.get('repo')) or not save_path or not os.path.exists(save_path):
        return False
    m = os.path.getmtime(save_path)
    if not forcar:
        if c.get('enviado_mtime') == m:
            return False
        if time.time() - m < ESPERA_MIN * 60:
            return False
    if not _lock.acquire(blocking=False):
        return False
    status['enviando'] = True
    try:
        token, repo = c['token'], c['repo']
        dia = dt.datetime.fromtimestamp(m).date()
        nome = os.path.basename(save_path)
        with open(save_path, 'rb') as f:
            bruto = f.read()
        _enviar_arquivo(token, repo, f'saves/{dia.isoformat()}/{nome}', bruto, f'save {dia} {nome}')
        if estado_path and os.path.exists(estado_path):
            with open(estado_path, 'rb') as f:
                _enviar_arquivo(token, repo, f'saves/{dia.isoformat()}/app_carreira.json', f.read(), f'app {dia}')
        info = {'dia': dia.isoformat(), 'salvo_em': dt.datetime.fromtimestamp(m).isoformat(timespec='seconds'),
                'arquivo': nome, 'pasta_save': os.path.dirname(save_path), 'versao_app': versao,
                'enviado_em': dt.datetime.now().isoformat(timespec='seconds'), 'tamanho': len(bruto)}
        _enviar_arquivo(token, repo, 'ultimo.json', json.dumps(info, ensure_ascii=False, indent=1).encode(), 'último envio')
        try:
            _limpar_antigos(token, repo, dt.date.today())
        except Exception:
            pass
        c['enviado_mtime'] = m
        salvar_cfg(data_dir, c)
        status.update(ultimo_envio=info['enviado_em'], ultimo_arquivo=f'{dia.isoformat()}/{nome}', erro=None)
        return True
    except Exception as e:
        status['erro'] = str(e)
        return False
    finally:
        status['enviando'] = False
        _lock.release()
