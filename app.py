"""App de Carreira – Patrocínios (PES 2021 · GOGOSZ). Servidor local + motor de simulação."""
import os, sys, json, time, threading, glob, re, io, subprocess, traceback, webbrowser, datetime as dt
from http.server import ThreadingHTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs, unquote

APP_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, APP_DIR)
from core import savedata, kits, sim
from core.logos import LogoBank

PORT = 8765
DATA = os.path.join(APP_DIR, 'data')
LOG_PATH = os.path.join(DATA, 'app.log')
LOCK = threading.RLock()


def log(*a):
    line = time.strftime('%d/%m %H:%M:%S ') + ' '.join(str(x) for x in a)
    print(line)
    try:
        with open(LOG_PATH, 'a', encoding='utf-8') as f:
            f.write(line + '\n')
    except OSError:
        pass


def jload(p, default):
    try:
        return json.load(open(p, encoding='utf-8'))
    except Exception:
        return default


def jsave(p, obj):
    tmp = p + '.tmp'
    json.dump(obj, open(tmp, 'w', encoding='utf-8'), ensure_ascii=False, indent=1, default=str)
    os.replace(tmp, p)


CFG = jload(os.path.join(DATA, 'config.json'), {})
TORNEIOS = {17: 'Brasileirão'}


def team_names():
    names = {}
    p = os.path.join(CFG['pasta_jogo'], 'GOGOSZ', 'kitserver', 'map.txt')
    try:
        for line in open(p, encoding='utf-8-sig', errors='replace'):
            m = re.match(r'\s*(\d+)\s*,\s*"([^"]+)"', line)
            if m:
                names[int(m.group(1))] = m.group(2).split('\\')[-1]
    except OSError:
        pass
    return names


class App:
    def __init__(self):
        self.logos = LogoBank(APP_DIR, CFG['pasta_logos'])
        self.names = team_names()
        self.state_path = None
        self.state = None
        self.engine = None
        self.career = None
        self.save_path = None
        self.save_mtime = None
        self.status = {'kits': 'ok', 'kits_msg': '', 'kits_prog': None, 'aviso': None, 'erro': None, 'lendo': False}
        self.kit_thread = None
        self.kits_aplicados = None

    # ----- arquivos -----
    def find_save(self):
        cands = glob.glob(os.path.join(CFG['pasta_saves'], '*', 'save', CFG.get('arquivo_save', 'ML00000000')))
        if not cands:
            cands = glob.glob(os.path.join(CFG['pasta_saves'], '*', 'save', 'ML*'))
        return max(cands, key=os.path.getmtime) if cands else None

    def game_running(self):
        if os.name != 'nt':
            return False
        try:
            out = subprocess.run(['tasklist', '/FI', 'IMAGENAME eq PES2021.exe', '/NH'], capture_output=True,
                                 text=True, creationflags=0x08000000).stdout
            return 'PES2021.exe' in out
        except Exception:
            return False

    def career_state_path(self, slot_name):
        safe = re.sub(r'[^\w\- ]', '_', slot_name).strip() or 'carreira'
        os.makedirs(os.path.join(DATA, 'carreiras'), exist_ok=True)
        return os.path.join(DATA, 'carreiras', safe + '.json')

    def persist(self):
        if self.state is not None:
            jsave(self.state_path, self.state)

    # ----- leitura do save -----
    def tick(self):
        path = self.find_save()
        if not path:
            self.status['erro'] = 'Não encontrei o save do Master League. Confira a pasta de saves.'
            return
        m = os.path.getmtime(path)
        if path == self.save_path and m == self.save_mtime:
            return
        # espera o jogo terminar de gravar (tamanho estável)
        s1 = os.path.getsize(path); time.sleep(1.5)
        if os.path.getsize(path) != s1 or os.path.getmtime(path) != m:
            return
        self.status['lendo'] = True
        try:
            car = savedata.Career(path, CFG['time_id'])
        except Exception as e:
            self.status['erro'] = f'Não consegui ler o save agora ({e}). Vou tentar de novo.'
            self.status['lendo'] = False
            return
        self.status['erro'] = None
        with LOCK:
            self.save_path, self.save_mtime, self.career = path, m, car
            sp = self.career_state_path(car.slot_name)
            novo = False
            if sp != self.state_path or self.state is None:
                self.state_path = sp
                self.state = jload(sp, {})
                novo = not self.state
            st = self.state
            # carreira nova no mesmo arquivo: a data voltou muito
            if st.get('data') and car.date and car.date < sim.s2d(st['data']) - dt.timedelta(days=30):
                arq = sp.replace('.json', time.strftime('_arquivo_%Y%m%d_%H%M%S.json'))
                os.replace(sp, arq) if os.path.exists(sp) else None
                self.state = st = {}
                novo = True
                log('carreira nova detectada; estado anterior arquivado em', arq)
            self.engine = sim.Engine(st, CFG.get('clube', 'Palmeiras'), CFG.get('atratividade_base', 68))
            nomes = [(n, '') for n in sorted(set(self.logos.map.values()))]
            self.engine.sync_empresas(nomes)
            st['save_info'] = {'arquivo': path, 'slot': car.slot_name, 'clube': car.club_line,
                               'lido_em': time.strftime('%d/%m %H:%M:%S')}
            st['dinheiro'] = car.money()
            if car.fin_off is None:
                self.status['erro'] = 'Não achei o bloco de finanças nesse save.'
            self.engine.registrar_partidas(car.results, CFG['time_id'], sim.d2s(car.date))
            self.engine.avancar(car.date, primeira_leitura=novo)
            self.verificar_creditos(car)
            self.aplicar_creditos()
            st['eventos'] = [e for e in st.get('eventos', []) if e['tipo'] != 'kits']
            self.persist()
        self.status['lendo'] = False
        log('save lido:', car.slot_name, car.date, 'patrocínio', st['dinheiro'].get('rec_patrocinio'))

    # ----- dinheiro no jogo -----
    def verificar_creditos(self, car):
        money = car.money()
        if not money:
            return
        for c in self.state.get('contratos', []):
            for pg in c['pagamentos']:
                if pg['status'] != 'creditado':
                    continue
                if money['rec_patrocinio'] >= pg['esperado'] - 100:
                    pg['status'] = 'confirmado'
                    log('crédito confirmado no jogo:', c['empresa'], pg['valor'])
                elif money['rec_transmissao'] >= pg.get('ref_transmissao', 0):
                    # o jogo gravou por cima sem recarregar: aplica de novo
                    pg['status'] = 'pendente'
                    self.state.setdefault('avisos', []).append(
                        'O jogo salvou antes de você recarregar a carreira. Vou creditar o patrocínio de novo.')
                else:
                    pg['status'] = 'confirmado'  # virou a temporada

    def aplicar_creditos(self):
        pend = self.engine.pagamentos_pendentes()
        multas = [m for m in self.state.get('multas', []) if m['status'] == 'pendente']
        if (not pend and not multas) or self.career is None or self.career.fin_off is None:
            return
        car = self.career
        total = 0; total_multa = 0
        for c, pg in pend:
            car.credit_sponsor(pg['valor'])
            total += pg['valor']
        for m in multas:
            car.credit_sponsor(-m['valor'])
            total_multa += m['valor']
        try:
            bk = car.write(os.path.join(DATA, 'backups_save'))
        except Exception as e:
            self.status['erro'] = str(e)
            return
        self.save_mtime = car.mtime
        money = car.money()
        hoje = self.state['data']
        for c, pg in pend:
            if not total:
                break
            pg['status'] = 'creditado'
            pg['esperado'] = money['rec_patrocinio']
            pg['ref_transmissao'] = money['rec_transmissao']
            pg['creditado_em'] = hoje
            self.engine.msg('pagamento', c['empresa'], hoje, posicao=sim.pos_txt(c['slot']),
                            valor=sim.fmt_eur(pg['valor']))
        for m in multas:
            m['status'] = 'aplicada'; m['aplicada_em'] = hoje
        self.state['dinheiro'] = money
        partes = []
        if total:
            partes.append(f'{sim.fmt_eur(total)} de patrocínio foram colocados no save')
        if total_multa:
            partes.append(f'{sim.fmt_eur(total_multa)} de multa de rescisão foram descontados')
        self.status['aviso'] = (' e '.join(partes) + '. No jogo, volte ao menu principal e carregue a carreira de novo '
                                'para o valor aparecer. Não salve antes de recarregar.')
        self.state['aviso_recarregar'] = True
        log('crédito aplicado no save:', total, 'backup', bk)

    # ----- uniformes -----
    def contratos_visiveis(self):
        return [c for c in self.state.get('contratos', []) if c['status'] == 'ativo']

    @staticmethod
    def assinatura(cs):
        return json.dumps(sorted([[c['id'], c['slot'], c['empresa'], c.get('escala'), c.get('inclinacao'),
                                   sorted((c.get('cores') or {}).items())] for c in cs]), ensure_ascii=False)

    def kits_pendentes(self):
        if self.state is None:
            return []
        atual = self.contratos_visiveis()
        aplicado = self.state.get('kits_aplicados')
        if aplicado is None:
            return ['primeira aplicação: deixar os 10 uniformes no padrão do app (inclui o 4º, listrado, sem patrocínios)']
        if self.assinatura(atual) == aplicado:
            return []
        antes = {c[0]: c for c in json.loads(aplicado)}
        mud = []
        for c in atual:
            if c['id'] not in antes:
                mud.append(f"entra {c['empresa']} ({kits.SLOTS[c['slot']]['nome']})")
            elif antes[c['id']] != json.loads(self.assinatura([c]))[0]:
                mud.append(f"ajuste no logo da {c['empresa']}")
        ids = {c['id'] for c in atual}
        for cid, c in antes.items():
            if cid not in ids:
                mud.append(f"sai {c[2]} ({kits.SLOTS[c[1]]['nome']})")
        return mud or ['atualização dos uniformes']

    def aplicar_kits(self):
        if self.kit_thread and self.kit_thread.is_alive():
            raise ValueError('Os uniformes já estão sendo gravados. Aguarde terminar.')
        cs = json.loads(json.dumps(self.contratos_visiveis()))
        sig = self.assinatura(cs)

        def prog(i, n, v):
            self.status['kits_prog'] = [i, n]
            self.status['kits_msg'] = f'Gravando uniforme {min(i + 1, n)} de {n}...' if i < n else 'Concluído'

        def run():
            self.status['kits'] = 'trabalhando'
            try:
                kits.install(APP_DIR, CFG['pasta_kits'], cs, self.logos.load, log, prog)
                with LOCK:
                    self.state['kits_aplicados'] = sig
                    self.persist()
                self.status['kits'] = 'ok'
                self.status['kits_msg'] = time.strftime('Uniformes aplicados às %H:%M:%S')
            except Exception as e:
                self.status['kits'] = 'erro'
                self.status['kits_msg'] = f'Erro ao gravar uniformes: {e}'
                log(traceback.format_exc())
            self.status['kits_prog'] = None

        self.kit_thread = threading.Thread(target=run, daemon=True)
        self.kit_thread.start()

    # ----- visão para a interface -----
    def view(self):
        st = self.state or {}
        eng = self.engine
        nm = lambda i: self.names.get(i, f'Time {i}')
        partidas = []
        for p in st.get('partidas', [])[-10:]:
            partidas.append({**p, 'mandante_nome': nm(p['mandante']), 'visitante_nome': nm(p['visitante']),
                             'torneio_nome': TORNEIOS.get(p['torneio'], 'Copa')})
        empresas = []
        for n, e in sorted(st.get('empresas', {}).items()):
            empresas.append({'nome': n, **e})
        return {
            'pronto': self.state is not None, 'versao': VERSAO,
            'clube': CFG.get('clube'), 'data': st.get('data'), 'dinheiro': st.get('dinheiro', {}),
            'atratividade': eng.atratividade() if eng else None, 'forma': eng.forma() if eng else '',
            'partidas': partidas[::-1],
            'ofertas': [o for o in st.get('ofertas', []) if o['status'] in ('aberta', 'aguardando')],
            'ofertas_hist': [o for o in st.get('ofertas', []) if o['status'] not in ('aberta', 'aguardando')][-20:][::-1],
            'contratos': st.get('contratos', []),
            'mensagens': st.get('mensagens', [])[-60:][::-1],
            'empresas': empresas,
            'slots': [{'id': k, **{kk: vv for kk, vv in kits.SLOTS[k].items() if kk != 'lugares'}} for k in kits.SLOT_ORDER],
            'livres': eng.slots_livres(eng.hoje()) if eng and eng.hoje() else [],
            'familias': kits.FAMILIAS,
            'save': st.get('save_info'), 'jogo_aberto': self.game_running(),
            'status': self.status, 'avisos': st.pop('avisos', []) if st else [],
            'kits_pendentes': self.kits_pendentes(), 'multas': st.get('multas', []),
            'multa_estimada': {c['id']: eng.multa_rescisao(c) for c in st.get('contratos', [])
                               if c['status'] == 'ativo'} if eng and eng.hoje() else {},
        }


A = App()


def watcher():
    while True:
        try:
            A.tick()
        except Exception:
            log(traceback.format_exc())
        time.sleep(3)


def logos_watcher():
    while True:
        try:
            novos = A.logos.scan()
            if novos and A.engine:
                with LOCK:
                    A.engine.sync_empresas([(n['nome'], n['pasta']) for n in novos])
                    A.persist()
                log('logos novos:', [n['nome'] for n in novos])
        except Exception:
            log(traceback.format_exc())
        time.sleep(20)


class H(BaseHTTPRequestHandler):
    def log_message(self, *a):
        pass

    def send(self, code, body, ctype='application/json; charset=utf-8'):
        if isinstance(body, (dict, list)):
            body = json.dumps(body, ensure_ascii=False, default=str).encode('utf-8')
        elif isinstance(body, str):
            body = body.encode('utf-8')
        self.send_response(code)
        self.send_header('Content-Type', ctype)
        self.send_header('Cache-Control', 'no-store')
        self.send_header('Content-Length', str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        u = urlparse(self.path)
        q = {k: v[0] for k, v in parse_qs(u.query).items()}
        try:
            if u.path in ('/', '/index.html'):
                return self.send(200, open(os.path.join(APP_DIR, 'web', 'index.html'), 'rb').read(), 'text/html; charset=utf-8')
            if u.path == '/api/versao':
                return self.send(200, {'versao': VERSAO})
            if u.path == '/api/atualizacao':
                try:
                    return self.send(200, checar_atualizacao())
                except Exception as e:
                    return self.send(200, {'atual': VERSAO, 'tem': False, 'erro': str(e)})
            if u.path in ('/icone.ico', '/icone.png', '/favicon.ico'):
                f = 'icone.png' if u.path.endswith('png') else 'icone.ico'
                return self.send(200, open(os.path.join(APP_DIR, 'web', f), 'rb').read(),
                                 'image/png' if f.endswith('png') else 'image/x-icon')
            if u.path == '/api/estado':
                with LOCK:
                    return self.send(200, A.view())
            if u.path.startswith('/logo/'):
                nome = unquote(u.path[6:])
                if nome.lower().endswith('.png'):
                    nome = nome[:-4]
                p = A.logos.path(nome)
                if os.path.exists(p):
                    return self.send(200, open(p, 'rb').read(), 'image/png')
                return self.send(404, {'erro': 'logo'})
            if u.path == '/api/preview':
                fam = q.get('familia', 'verde')
                variant, fname, _ = next(v for v in kits.VARIANTS if v[2] == fam)
                with LOCK:
                    cs = json.loads(json.dumps([c for c in A.state.get('contratos', []) if c['status'] in ('ativo', 'assinado')]))
                if q.get('cand'):
                    cand = json.loads(q['cand'])
                    cs = [c for c in cs if c['slot'] != cand['slot'] and c.get('id') != cand.get('id')] + [cand]
                img = kits.compose(APP_DIR, variant, fname, fam, cs, A.logos.load)
                out = io.BytesIO()
                kits.preview(img, int(q.get('w', 520))).save(out, 'JPEG', quality=88)
                return self.send(200, out.getvalue(), 'image/jpeg')
            if u.path == '/api/valor_justo':
                with LOCK:
                    return self.send(200, {'valor': A.engine.valor_justo(q['empresa'], q['slot'])})
            return self.send(404, {'erro': 'não encontrado'})
        except Exception as e:
            log(traceback.format_exc())
            return self.send(500, {'erro': str(e)})

    def do_POST(self):
        u = urlparse(self.path)
        n = int(self.headers.get('Content-Length') or 0)
        body = json.loads(self.rfile.read(n) or b'{}')
        if u.path == '/api/atualizar':
            try:
                n = atualizar()
            except Exception as e:
                return self.send(500, {'erro': f'Não consegui atualizar: {e}'})
            self.send(200, {'ok': True, 'arquivos': n})
            reiniciar()
            return
        if u.path == '/api/sair':
            self.send(200, {'ok': True})
            log('App encerrado pelo usuário')
            threading.Timer(0.5, lambda: os._exit(0)).start()
            return
        try:
            with LOCK:
                eng = A.engine
                if eng is None:
                    raise ValueError('O app ainda está lendo o save. Aguarde alguns segundos.')
                if u.path == '/api/oferta/aceitar':
                    c = eng.aceitar(body['id'])
                    A.aplicar_creditos()
                    A.persist()
                    return self.send(200, {'ok': True, 'contrato': c})
                if u.path == '/api/oferta/recusar':
                    eng.recusar(body['id']); A.persist(); return self.send(200, {'ok': True})
                if u.path == '/api/oferta/pedir_mais':
                    eng.pedir_mais(body['id'], int(body['pct']), body.get('clausulas'), body.get('anos'))
                    A.persist(); return self.send(200, {'ok': True})
                if u.path == '/api/procurar':
                    o = eng.procurar(body['empresa'], body['slot'], int(body['valor']), int(body['anos']),
                                     body.get('clausulas'))
                    A.persist(); return self.send(200, {'ok': True, 'oferta': o})
                if u.path == '/api/contrato/visual':
                    for c in A.state['contratos']:
                        if c['id'] == int(body['id']):
                            c['escala'] = float(body.get('escala', c['escala']))
                            c['inclinacao'] = float(body.get('inclinacao', c['inclinacao']))
                            c['cores'].update(body.get('cores', {}))
                    A.persist(); return self.send(200, {'ok': True})
                if u.path == '/api/mensagens/lidas':
                    for m in A.state['mensagens']:
                        m['lida'] = True
                    A.persist(); return self.send(200, {'ok': True})
                if u.path == '/api/aviso/ok':
                    A.status['aviso'] = None; return self.send(200, {'ok': True})
                if u.path == '/api/kits/aplicar':
                    A.aplicar_kits(); return self.send(200, {'ok': True})
                if u.path == '/api/contrato/rescindir':
                    multa = eng.rescindir(body['id'])
                    A.aplicar_creditos(); A.persist()
                    return self.send(200, {'ok': True, 'multa': multa})
                if u.path == '/api/empresa':
                    e = A.state['empresas'][body['nome']]
                    if body.get('porte') in sim.PORTE_FATOR:
                        e['porte'] = body['porte']
                    A.persist(); return self.send(200, {'ok': True})
            return self.send(404, {'erro': 'não encontrado'})
        except ValueError as e:
            return self.send(400, {'erro': str(e)})
        except Exception as e:
            log(traceback.format_exc())
            return self.send(500, {'erro': str(e)})


def _versao():
    try:
        return open(os.path.join(APP_DIR, 'versao.txt'), encoding='utf-8').read().strip()
    except OSError:
        return '0'


VERSAO = _versao()
REPO = 'yannespza/Carreira-PES21'
ARQUIVOS_CODIGO = ('app.py', 'versao.txt', 'Abrir App.bat', 'Instalar.bat', 'LEIA-ME.txt', 'core/', 'web/')


def _vtuple(v):
    try:
        return tuple(int(x) for x in v.split('.'))
    except ValueError:
        return (0,)


def checar_atualizacao():
    import urllib.request
    url = f'https://raw.githubusercontent.com/{REPO}/main/versao.txt'
    with urllib.request.urlopen(url, timeout=8) as r:
        nova = r.read().decode().strip()
    return {'atual': VERSAO, 'nova': nova, 'tem': _vtuple(nova) > _vtuple(VERSAO)}


def atualizar():
    """Baixa a versão nova do GitHub, guarda a atual em data/versoes e troca só os arquivos de código."""
    import urllib.request, zipfile, shutil
    url = f'https://github.com/{REPO}/archive/refs/heads/main.zip'
    with urllib.request.urlopen(url, timeout=60) as r:
        blob = r.read()
    z = zipfile.ZipFile(io.BytesIO(blob))
    raiz = z.namelist()[0].split('/')[0] + '/'
    bk = os.path.join(DATA, 'versoes', VERSAO)
    os.makedirs(bk, exist_ok=True)
    n = 0
    for nome in z.namelist():
        rel = nome[len(raiz):]
        if not rel or rel.endswith('/') or not rel.startswith(ARQUIVOS_CODIGO):
            continue
        dst = os.path.join(APP_DIR, *rel.split('/'))
        if os.path.exists(dst):
            os.makedirs(os.path.dirname(os.path.join(bk, rel)), exist_ok=True)
            shutil.copy2(dst, os.path.join(bk, rel))
        os.makedirs(os.path.dirname(dst), exist_ok=True)
        with open(dst, 'wb') as f:
            f.write(z.read(nome))
        n += 1
    log('atualizado do GitHub:', n, 'arquivos; versão anterior guardada em', bk)
    return n


def reiniciar():
    subprocess.Popen([sys.executable, os.path.join(APP_DIR, 'app.py'), '--reiniciar'], cwd=APP_DIR)
    threading.Timer(0.3, lambda: os._exit(0)).start()


def abrir_janela(url):
    """Abre o app numa janela própria (modo aplicativo do Edge/Chrome); se não achar, usa o navegador."""
    cands = [os.path.expandvars(p) for p in (
        r'%ProgramFiles(x86)%\Microsoft\Edge\Application\msedge.exe',
        r'%ProgramFiles%\Microsoft\Edge\Application\msedge.exe',
        r'%ProgramFiles%\Google\Chrome\Application\chrome.exe',
        r'%ProgramFiles(x86)%\Google\Chrome\Application\chrome.exe',
        r'%LocalAppData%\Google\Chrome\Application\chrome.exe')]
    perfil = os.path.join(DATA, 'janela')
    for exe in cands:
        if os.path.exists(exe):
            try:
                subprocess.Popen([exe, f'--app={url}', '--window-size=1440,900', f'--user-data-dir={perfil}',
                                  '--no-first-run', '--no-default-browser-check'])
                return
            except OSError:
                pass
    webbrowser.open(url)


def ja_aberto(url):
    import urllib.request
    try:
        urllib.request.urlopen(url + 'api/versao', timeout=1)
        return True
    except Exception:
        return False


def main():
    os.makedirs(DATA, exist_ok=True)
    url = f'http://127.0.0.1:{PORT}/'
    if '--reiniciar' in sys.argv:     # depois de atualizar: espera a versão antiga liberar a porta
        for _ in range(40):
            if not ja_aberto(url):
                break
            time.sleep(0.25)
    elif ja_aberto(url):          # o app já está rodando: só abre a janela de novo
        if '--sem-navegador' not in sys.argv:
            abrir_janela(url)
        return
    log('App iniciado, versão', VERSAO)
    A.logos.scan()
    threading.Thread(target=watcher, daemon=True).start()
    threading.Thread(target=logos_watcher, daemon=True).start()
    srv = ThreadingHTTPServer(('127.0.0.1', PORT), H)
    A.server = srv
    print('\n  App de Carreira rodando em', url, '\n')
    if '--sem-navegador' not in sys.argv and '--reiniciar' not in sys.argv:
        threading.Timer(0.8, lambda: abrir_janela(url)).start()
    srv.serve_forever()


if __name__ == '__main__':
    main()
