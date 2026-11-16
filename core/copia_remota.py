"""Cópia dos saves para análise a distância (o Claude lê pelo GitHub quando o PC está desligado).

Sempre que o jogo grava um save do Master League (qualquer espaço, não só o da carreira ativa) ou o arquivo EDIT,
o app espera ESPERA_MIN minutos sem mudança e manda uma VERSÃO NOVA para o repositório PRIVADO do usuário.
Nada é substituído: cada gravação vira um arquivo próprio, com a hora no nome, para comparar antes e depois.

Pastas no repositório:
  saves/AAAA-MM-DD/HHMMSS_ML00000006.pesz   (save compactado; ferramentas/saves_remotos.py abre)
  saves/AAAA-MM-DD/HHMMSS_app_carreira.json (o que o app guardou da carreira ativa naquele momento)
  saves/AAAA-MM-DD/HHMMSS_EDIT00000000.pesz (só quando o EDIT muda)
  ultimo.json                               (lista das últimas versões enviadas)
Limpeza semanal: durante a semana tudo fica guardado. Na primeira gravação de uma semana nova, o app deixa só as
MANTER_VERSOES versões mais recentes de cada save (e o app_carreira.json delas) e recomeça o histórico do repositório
do zero com esses arquivos, para as versões apagadas não continuarem ocupando espaço no histórico do GitHub.

.pesz = o save decriptado e compactado (bem menor que o original) e que volta a ser o arquivo original byte a
byte (conferido antes de enviar; se não bater, vai o original compactado).
O token fica só no PC (data/copia_remota.json), nunca vai para a tela nem para o GitHub. Nada aqui grava no save."""
import base64, datetime as dt, json, os, re, struct, threading, time, urllib.request, urllib.error, zlib

ESPERA_MIN = 2           # minutos sem o arquivo mudar antes de enviar (o jogo terminou de gravar)
MANTER_VERSOES = 2       # versões de cada save que sobram na limpeza semanal
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
            'tem_token': bool(c.get('token')), 'espera_min': ESPERA_MIN, 'manter': MANTER_VERSOES, 'ultima_limpeza': c.get('limpeza_semana'), **status,
            'versoes': (c.get('ultimos') or [])[-8:][::-1]}


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


def _semana(d):
    a, w, _ = d.isocalendar()
    return f'{a}-S{w:02d}'


def limpar_semana(token, repo, manter=MANTER_VERSOES):
    """Deixa só as `manter` versões mais recentes de cada save e recomeça o histórico com elas (commit sem pai).
    Devolve (arquivos mantidos, arquivos removidos)."""
    info = _req(token, 'GET', f'/repos/{repo}')
    ramo = (info or {}).get('default_branch') or 'main'
    ref = _req(token, 'GET', f'/repos/{repo}/git/ref/heads/{ramo}')
    if not ref:
        return 0, 0
    commit = _req(token, 'GET', f'/repos/{repo}/git/commits/{ref["object"]["sha"]}')
    arvore = _req(token, 'GET', f'/repos/{repo}/git/trees/{commit["tree"]["sha"]}?recursive=1')
    blobs = [t for t in (arvore or {}).get('tree', []) if t.get('type') == 'blob']
    versoes = {}                       # arquivo do save -> [caminhos .pesz]
    for t in blobs:
        m = re.match(r'saves/(\d{4}-\d{2}-\d{2})/(\d{6})_(.+)\.pesz$', t['path'])
        if m:
            versoes.setdefault(m.group(3), []).append((m.group(1) + m.group(2), t['path']))
    ficam = set()
    for nome, lst in versoes.items():
        for _, caminho in sorted(lst)[-manter:]:
            ficam.add(caminho)
            if nome.startswith('ML'):
                ficam.add(caminho.replace('_' + nome + '.pesz', '_app_carreira.json'))
    novos = [{'path': t['path'], 'mode': t.get('mode', '100644'), 'type': 'blob', 'sha': t['sha']}
             for t in blobs if not t['path'].startswith('saves/') or t['path'] in ficam]
    removidos = len(blobs) - len(novos)
    if not removidos:
        return len(novos), 0
    tree = _req(token, 'POST', f'/repos/{repo}/git/trees', {'tree': novos})
    novo = _req(token, 'POST', f'/repos/{repo}/git/commits',
                {'message': f'limpeza semanal: ficam as {manter} versões mais recentes de cada save', 'tree': tree['sha'],
                 'parents': []})
    _req(token, 'PATCH', f'/repos/{repo}/git/refs/heads/{ramo}', {'sha': novo['sha'], 'force': True})
    return len(novos), removidos


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


def empacotar(raw):
    """Save decriptado e compactado. Só usa o formato decriptado se voltar ao original byte a byte."""
    try:
        from . import pescrypt
        sf = pescrypt.decrypt(raw)
        refeito = pescrypt.encrypt(sf)
        if refeito == raw[:len(refeito)]:
            partes = [bytes(sf.enc_header), bytes(sf.file_header), bytes(sf.description), bytes(sf.logo),
                      bytes(sf.data), bytes(sf.serial), raw[len(refeito):]]
            cab = struct.pack('<7I', *map(len, partes))
            return b'PESZ1' + cab + zlib.compress(b''.join(partes), 6)
    except Exception:
        pass
    return b'PESZ0' + zlib.compress(raw, 6)


def desempacotar(blob):
    """Devolve (arquivo original, dados decriptados ou None)."""
    if blob[:5] == b'PESZ0':
        return zlib.decompress(blob[5:]), None
    if blob[:5] != b'PESZ1':
        raise ValueError('não é um .pesz')
    tam = struct.unpack_from('<7I', blob, 5)
    corpo = zlib.decompress(blob[5 + 28:])
    partes, p = [], 0
    for t in tam:
        partes.append(corpo[p:p + t])
        p += t
    from . import pescrypt
    eh, fh, desc, logo, data, serial, cauda = partes
    raw = pescrypt.encrypt(pescrypt.SaveFile(eh, fh, desc, logo, data, serial)) + cauda
    return raw, data


def _arquivos(pasta):
    out = []
    try:
        for n in os.listdir(pasta):
            if re.fullmatch(r'ML[0-9A-F]{8}', n) or n == 'EDIT00000000':
                out.append(os.path.join(pasta, n))
    except OSError:
        pass
    return out


def enviar(data_dir, save_path, estado_path, versao, forcar=False):
    """Manda uma versão nova de cada save (e do EDIT) que mudou desde o último envio. Devolve quantos enviou."""
    c = ler_cfg(data_dir)
    if not (c.get('ativo') and c.get('token') and c.get('repo')) or not save_path or not os.path.exists(save_path):
        return 0
    enviados = c.setdefault('enviados', {})          # caminho -> mtime enviado
    agora = time.time()
    pend = []
    for arq in _arquivos(os.path.dirname(save_path)):
        m = os.path.getmtime(arq)
        if enviados.get(arq) == m:
            continue
        if not forcar and agora - m < ESPERA_MIN * 60:
            continue
        pend.append((m, arq))
    if not pend or not _lock.acquire(blocking=False):
        return 0
    status['enviando'] = True
    n = 0
    try:
        token, repo = c['token'], c['repo']
        lista = []
        for m, arq in sorted(pend):
            quando = dt.datetime.fromtimestamp(m)
            dia, hora, nome = quando.date().isoformat(), quando.strftime('%H%M%S'), os.path.basename(arq)
            with open(arq, 'rb') as f:
                bruto = f.read()
            blob = empacotar(bruto)
            caminho = f'saves/{dia}/{hora}_{nome}.pesz'
            _enviar_arquivo(token, repo, caminho, blob, f'{nome} {dia} {hora}')
            item = {'arquivo': nome, 'caminho': caminho, 'salvo_em': quando.isoformat(timespec='seconds'),
                    'tamanho_original': len(bruto), 'tamanho_enviado': len(blob), 'ativo': arq == save_path}
            if arq == save_path and estado_path and os.path.exists(estado_path):
                with open(estado_path, 'rb') as f:
                    cj = f'saves/{dia}/{hora}_app_carreira.json'
                    _enviar_arquivo(token, repo, cj, f.read(), f'app {dia} {hora}')
                item['app_carreira'] = cj
            enviados[arq] = m
            c['enviados'] = enviados
            salvar_cfg(data_dir, c)
            lista.append(item)
            n += 1
        hist = c.setdefault('ultimos', [])
        hist.extend(lista)
        c['ultimos'] = hist[-40:]
        salvar_cfg(data_dir, c)
        info = {'versao_app': versao, 'enviado_em': dt.datetime.now().isoformat(timespec='seconds'),
                'save_ativo': os.path.basename(save_path), 'pasta_save': os.path.dirname(save_path), 'versoes': c['ultimos'][::-1]}
        _enviar_arquivo(token, repo, 'ultimo.json', json.dumps(info, ensure_ascii=False, indent=1).encode(), 'índice')
        sem = _semana(dt.date.today())
        if c.get('limpeza_semana') != sem:
            try:
                if c.get('limpeza_semana'):              # na primeira semana não há o que limpar
                    ficam, saiu = limpar_semana(token, repo)
                    status['ultima_limpeza'] = f'{sem}: {saiu} arquivos apagados, {ficam} mantidos'
                c['limpeza_semana'] = sem
                salvar_cfg(data_dir, c)
            except Exception as e:
                status['erro'] = f'limpeza semanal: {e}'
        ult = lista[-1]
        status.update(ultimo_envio=info['enviado_em'], ultimo_arquivo=ult['caminho'].replace('saves/', ''), erro=None,
                      enviados_agora=n)
        return n
    except Exception as e:
        status['erro'] = str(e)
        return n
    finally:
        status['enviando'] = False
        _lock.release()
