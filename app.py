"""App de Carreira – Patrocínios (PES 2021 · GOGOSZ). Servidor local + motor de simulação."""
import os, sys, json, time, threading, glob, re, io, subprocess, traceback, webbrowser, datetime as dt
from http.server import ThreadingHTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs, unquote

APP_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, APP_DIR)
from core import marketing, ingame, cena, imprensa, tecnico, estudio, savedata, kits, sim, mundo, times, gestao, numeros
from core import rivais, vestiario, estrutura, diretoria, retro, tecnico_carreira, ranking, medico, aovivo, sumulas
from core import assessor, dirigentes, diretor, presidente, escalacao, posicao
from core.logos import LogoBank

PORT = 8765
DATA = os.path.join(APP_DIR, 'data')
LOG_PATH = os.path.join(DATA, 'app.log')
LOCK = threading.RLock()
LOGOS_LOCK = threading.Lock()     # uma leitura da pasta de logos por vez (botão e verificação automática)


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
    with open(tmp, 'w', encoding='utf-8') as f:
        json.dump(obj, f, ensure_ascii=False, indent=1, default=str)
        f.flush()
        os.fsync(f.fileno())          # grava de verdade no disco (PC desligado no meio não estraga o arquivo)
    os.replace(tmp, p)


CFG = jload(os.path.join(DATA, 'config.json'), {})


# ---------------- primeira configuração (PC novo, app emprestado) ----------------
def _docs_bases():
    home = os.path.expanduser('~')
    bases = [os.path.join(home, x) for x in ('Documents', 'Documentos')]
    try:
        for d in os.listdir(home):
            if d.lower().startswith('onedrive') and os.path.isdir(os.path.join(home, d)):
                bases += [os.path.join(home, d, x) for x in ('Documents', 'Documentos')]
    except OSError:
        pass
    return [b for b in bases if os.path.isdir(b)]


def _saves_em(pasta):
    return [p for p in glob.glob(os.path.join(pasta, '*', 'save', 'ML*'))
            if re.fullmatch(r'ML[0-9A-F]{8}', os.path.basename(p))]


def detectar_saves():
    """Pastas de save do PES 2021 (KONAMI, GOGOSZ...) dentro de Documentos, a mais usada primeiro."""
    achadas = {}
    for b in _docs_bases():
        try:
            n1 = [os.path.join(b, d) for d in os.listdir(b)]
        except OSError:
            continue
        for d in n1:
            if not os.path.isdir(d):
                continue
            cands = [d]
            try:
                cands += [os.path.join(d, x) for x in os.listdir(d) if os.path.isdir(os.path.join(d, x))]
            except OSError:
                pass
            for c in cands:
                ms = _saves_em(c)
                if ms:
                    achadas[c] = max(os.path.getmtime(m) for m in ms)
    return [k for k, _ in sorted(achadas.items(), key=lambda kv: -kv[1])]


def _jogo_ok(p):
    return bool(p) and os.path.isfile(os.path.join(p, 'PES2021.exe'))


def detectar_jogo():
    """Pastas com o PES2021.exe: caminhos da Steam e até 3 níveis abaixo da raiz de cada disco.
    As que têm o patch GOGOSZ (kitserver) vêm primeiro."""
    import string
    achadas = []
    pular = {'windows', '$recycle.bin', 'programdata', 'users', 'system volume information', 'recovery',
             'perflogs', 'msocache', 'intel', 'amd', 'nvidia', '$windows.~bt', '$windows.~ws', 'onedrivetemp'}
    for letra in string.ascii_uppercase[2:]:
        raiz = f'{letra}:\\'
        if not os.path.isdir(raiz):
            continue
        for sub in (r'Program Files (x86)\Steam', r'Program Files\Steam', 'SteamLibrary', 'Steam',
                    r'Games\Steam', r'Games\SteamLibrary'):
            p = os.path.join(raiz, sub, 'steamapps', 'common', 'eFootball PES 2021')
            if _jogo_ok(p):
                achadas.append(p)
        fila, vistos = [(raiz, 0)], 0
        while fila and vistos < 4000:
            d, nivel = fila.pop(0)
            vistos += 1
            try:
                itens = os.listdir(d)
            except OSError:
                continue
            if 'PES2021.exe' in itens:
                achadas.append(d)
                continue
            if nivel >= 3:
                continue
            for x in itens:
                if x.lower() in pular or x.startswith('.'):
                    continue
                c = os.path.join(d, x)
                if os.path.isdir(c):
                    fila.append((c, nivel + 1))
    vistas = []
    for a in achadas:
        if a not in vistas:
            vistas.append(a)
    tem_patch = lambda p: os.path.isfile(os.path.join(p, 'GOGOSZ', 'kitserver', 'map.txt'))
    return sorted(vistas, key=lambda p: not tem_patch(p))


def config_status():
    probs = []
    if not _jogo_ok(CFG.get('pasta_jogo')):
        probs.append('jogo')
    if not CFG.get('pasta_saves') or not _saves_em(CFG.get('pasta_saves')):
        probs.append('saves')
    return probs


def preparar_config():
    """PC novo: preenche sozinho o que conseguir achar e grava. O que faltar, a tela de configuração pede."""
    mudou = False
    if 'tecnico_nome' not in CFG and CFG.get('pasta_jogo'):
        # instalação antiga (antes do nome ser configurável): o nome era fixo
        CFG['tecnico_nome'] = 'Yannes Zola'; mudou = True
    if not CFG.get('pasta_logos'):
        CFG['pasta_logos'] = os.path.join(APP_DIR, 'Logos')
        os.makedirs(CFG['pasta_logos'], exist_ok=True)
        mudou = True
    if os.name == 'nt' and not _jogo_ok(CFG.get('pasta_jogo')):
        j = detectar_jogo()
        if j:
            CFG['pasta_jogo'] = j[0]; mudou = True
    if os.name == 'nt' and not (CFG.get('pasta_saves') and _saves_em(CFG['pasta_saves'])):
        sv = detectar_saves()
        if sv:
            CFG['pasta_saves'] = sv[0]; CFG.pop('save_escolhido', None); mudou = True
    if mudou:
        jsave(os.path.join(DATA, 'config.json'), CFG)


try:
    preparar_config()
except Exception:
    pass
TORNEIOS = {17: 'Brasileirão', 79: 'Série B', 81: 'Série C', 80: 'Série D', 23: 'Copa do Brasil',
            86: 'Supercopa do Brasil', 2: 'Libertadores', 3: 'Libertadores', 4: 'Libertadores (final)',
            5: 'Sudamericana', 6: 'Sudamericana (final)', 7: 'Recopa', 1: 'Intercontinental'}


def mapa_kitserver():
    """{id: 'Pais\\Liga\\Time'} do kitserver do GOGOSZ (país e liga de cada time do jogo)."""
    out = {}
    p = os.path.join(CFG.get('pasta_jogo', ''), 'GOGOSZ', 'kitserver', 'map.txt')
    try:
        for line in open(p, encoding='utf-8-sig', errors='replace'):
            m = re.match(r'\s*(\d+)\s*,\s*"([^"]+)"', line)
            if m:
                out[int(m.group(1))] = m.group(2)
    except OSError:
        pass
    return out


# pastas onde o patch guarda as minifotos dos jogadores (common\render\symbol\player\<id>.dds)
PASTAS_FOTO = ('Minifaces', 'Faces', 'Facesbase', 'Custom Players')


def foto_jogador(pid):
    """PNG da foto do jogador (cache em data/fotos); None se o patch não tiver foto dele."""
    cache = os.path.join(DATA, 'fotos')
    cf = os.path.join(cache, f'{pid}.png')
    if os.path.exists(cf):
        return open(cf, 'rb').read()
    if os.path.exists(cf + '.sem') and time.time() - os.path.getmtime(cf + '.sem') < 3 * 86400:
        return None          # sem foto: procura de novo a cada 3 dias (caso você instale fotos novas)
    os.makedirs(cache, exist_ok=True)
    for pasta in PASTAS_FOTO:
        f = os.path.join(CFG.get('pasta_jogo', ''), 'GOGOSZ', pasta, 'common', 'render', 'symbol', 'player', f'{pid}.dds')
        if os.path.exists(f):
            try:
                from PIL import Image
                im = Image.open(f).convert('RGBA')
                im.thumbnail((256, 256))
                b = io.BytesIO(); im.save(b, 'PNG'); open(cf, 'wb').write(b.getvalue())
                return b.getvalue()
            except Exception:
                log(traceback.format_exc())
    open(cf + '.sem', 'w').close()
    return None


def team_names():
    names = {}
    p = os.path.join(CFG.get('pasta_jogo', ''), 'GOGOSZ', 'kitserver', 'map.txt')
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
        self.logos = LogoBank(APP_DIR, CFG.get('pasta_logos', ''))
        self.names = team_names()
        self.mapa = mapa_kitserver()
        diretoria.MAPA = self.mapa
        self.state_path = None
        self.state = None
        self.engine = None
        self.career = None
        self.save_path = None
        self.save_mtime = None
        self.status = {'kits': 'ok', 'kits_msg': '', 'kits_prog': None, 'aviso': None, 'erro': None, 'lendo': False}
        self.kit_thread = None
        self.kits_aplicados = None
        self.times = times.Times(DATA, CFG, log)
        sim.MOEDAS.update({k: (sim.MOEDAS[k][0], float(v)) for k, v in (CFG.get('taxas_moeda') or {}).items()
                           if k in sim.MOEDAS})
        sim.MOEDA['cod'] = CFG.get('moeda', 'EUR')
        self.time = None          # configuração do clube da carreira atual
        # partida ao vivo: o módulo Lua grava live_match_data.json; esta thread lê sem travar nada
        self.aovivo = aovivo.Monitor(lambda: CFG.get('pasta_jogo'), self.ao_vivo_evento, log=log)
        self.aovivo.start()
        if CFG.get('ao_vivo', True) and CFG.get('pasta_jogo') and os.path.isdir(CFG.get('pasta_jogo', '')):
            try:
                aovivo.instalar(CFG.get('pasta_jogo', ''), os.path.join(DATA, 'backups_save'), log)
            except Exception:
                log(traceback.format_exc())
        self.elenco = []
        self.moral_data = None
        self.estatisticas = None   # súmulas da temporada lidas do save (gols, assistências, minutos, notas)
        self.escalacao = None      # plano de jogo lido do save (ordem dos 40 jogadores)
        self._esc_pendente = False

    # ----- clube da carreira -----
    def tid(self):
        return self.time['id'] if self.time else CFG.get('time_id', 137)

    def clube(self):
        return self.time['nome'] if self.time else CFG.get('clube', 'Palmeiras')

    def resolver_time(self, clube, data):
        """Descobre o id do clube pelo nome que aparece no save (confere com os dados da carreira)."""
        cands = times.candidatos(clube, self.times.mapa)
        if not cands:
            return CFG.get('time_id') if times.norm(clube) == times.norm(CFG.get('clube', '')) else None
        if len(cands) == 1:
            return cands[0]
        for t in cands:
            if savedata.find_results(data, t):
                return t
        for t in cands:
            if savedata.team_index(data, t):
                return t
        return cands[0]

    def usar_time(self, tid):
        if self.time and self.time['id'] == tid:
            return
        t = self.times.obter(tid)
        self.time = t
        kits.usar_time(t)
        log('clube da carreira:', t['nome'], tid, '| uniformes:', len(t['variantes']),
            '| preparado' if t.get('preparado') else '| precisa preparar')
        if not t.get('preparado'):
            self.preparar_time()

    def preparar_time(self, so_detectar=False):
        t = self.time
        if not t['variantes']:
            self.status['erro'] = f"Não achei os uniformes do {t['nome']} na pasta do kitserver ({t['pasta']})."
            return

        def depois(tt):
            with LOCK:
                if self.time and self.time['id'] == tt['id']:
                    kits.usar_time(tt)
                    if self.state is not None and not so_detectar:
                        self.state['kits_aplicados'] = None
                        # posições novas aprendidas no uniforme também ganham as propostas de início
                        if self.state.get('ofertas_iniciais') and self.engine and self.engine.hoje():
                            usados = {o['slot'] for o in self.state['ofertas']} | {
                                c['slot'] for c in self.state['contratos']}
                            faltam = [x for x in kits.SLOT_ORDER if x not in usados]
                            if faltam:
                                self.engine.ofertas_iniciais(self.engine.hoje(), slots=faltam)
                        self.persist()
        self.times.preparar(t, so_detectar, depois)

    def ler_elenco(self, car):
        try:
            idx = savedata.team_index(bytes(car.sf.data), car.team_id)
            ids = savedata.elenco(bytes(car.sf.data), idx)
            edit = os.path.join(os.path.dirname(car.path), 'EDIT00000000')
            nomes = savedata.nomes_jogadores(edit) if os.path.exists(edit) else {}
            el = [{'id': i, **nomes.get(i, {'nome': f'Jogador {i}', 'pos': ''})} for i in ids]
            self.aovivo.jogadores = nomes          # goleador ao vivo: id -> nome
            # moral: só existe no arquivo "Dados do time" (USERT...) que o jogo grava quando você salva o elenco
            us = sorted(glob.glob(os.path.join(os.path.dirname(car.path), 'USERT*')), key=os.path.getmtime)
            self.moral_data = None
            if us:
                try:
                    mor = savedata.dados_usert(us[-1], ids)
                    if mor:
                        for j in el:
                            if j['id'] in mor:
                                j.update(mor[j['id']])
                        self.moral_data = time.strftime('%d/%m %H:%M', time.localtime(os.path.getmtime(us[-1])))
                except Exception:
                    log(traceback.format_exc())
            self.elenco = sorted(el, key=lambda j: savedata.ORDEM_POS.get(j.get('pos'), 99))
            posicao.registrar(self.elenco)
            try:
                self.estatisticas = sumulas.do_clube(bytes(car.sf.data), car.team_id, nomes)
            except Exception:
                log(traceback.format_exc())
                self.estatisticas = None
            if self.state is not None:
                self.state['elenco_nomes'] = [j['nome'] for j in el if not j['nome'].startswith('Jogador ')]
        except Exception:
            log(traceback.format_exc())
            self.elenco = []

    # ----- arquivos -----
    def listar_saves(self):
        from core import pescrypt
        out = []
        for p in glob.glob(os.path.join(CFG.get('pasta_saves', ''), '*', 'save', 'ML*')):
            if not re.fullmatch(r'ML[0-9A-F]{8}', os.path.basename(p)):
                continue
            try:
                with open(p, 'rb') as f:
                    head = f.read(8192)
                d = pescrypt.peek(head)
            except Exception:
                continue
            txt = '\n'.join(d)
            m = savedata.DATE_RE.search(txt)
            linhas = txt.split('\n')
            out.append({'caminho': p, 'arquivo': os.path.basename(p), 'nome': d[0] if d else os.path.basename(p),
                        'clube': (linhas[1].split('/')[0].strip() if len(linhas) > 1 else ''),
                        'data': f'{int(m.group(3)):04d}-{int(m.group(2)):02d}-{int(m.group(1)):02d}' if m else None,
                        'salvo_em': time.strftime('%d/%m/%Y %H:%M', time.localtime(os.path.getmtime(p))),
                        'mtime': os.path.getmtime(p)})
        return sorted(out, key=lambda x: -x['mtime'])

    def find_save(self):
        """O save da carreira: o último que o jogo gravou. Um save escolhido na lista vale até o jogo gravar
        outro save depois da escolha (aí o jogador está jogando aquele e o app passa para ele sozinho)."""
        cands = [p for p in glob.glob(os.path.join(CFG.get('pasta_saves', ''), '*', 'save', 'ML*'))
                 if re.fullmatch(r'ML[0-9A-F]{8}', os.path.basename(p))]
        novo = max(cands, key=os.path.getmtime) if cands else None
        esc = CFG.get('save_escolhido')
        if esc and os.path.exists(esc):
            desde = max(CFG.get('save_escolhido_em', 0), os.path.getmtime(esc))
            if not novo or os.path.normcase(novo) == os.path.normcase(esc) or os.path.getmtime(novo) <= desde:
                return esc
            log('o jogo gravou outro save depois do escolhido; passando para', novo)
            CFG.pop('save_escolhido', None)
            CFG.pop('save_escolhido_em', None)
            jsave(os.path.join(DATA, 'config.json'), CFG)
        return novo

    def game_running(self):
        if os.name != 'nt':
            return False
        try:
            out = subprocess.run(['tasklist', '/FI', 'IMAGENAME eq PES2021.exe', '/NH'], capture_output=True,
                                 text=True, creationflags=0x08000000).stdout
            return 'PES2021.exe' in out
        except Exception:
            return False

    def career_state_path(self, slot_name, team_id=None):
        """Arquivo do app para esta carreira. O nome vem do save ("Liga Master 03"), mas o jogo pode ter dois
        saves com o mesmo nome e clubes diferentes: nesse caso o clube entra no nome do arquivo."""
        safe = re.sub(r'[^\w\- ]', '_', slot_name).strip() or 'carreira'
        os.makedirs(os.path.join(DATA, 'carreiras'), exist_ok=True)
        base = os.path.join(DATA, 'carreiras', safe + '.json')
        if not team_id:
            return base
        alt = os.path.join(DATA, 'carreiras', f'{safe} - {team_id}.json')
        if os.path.exists(alt):
            return alt
        if not os.path.exists(base):
            return base
        dono = (self.state or {}).get('time_id') if self.state_path == base else jload(base, {}).get('time_id')
        return base if not dono or dono == team_id else alt

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
        if path == self.save_path and m == self.save_mtime and self.career is not None:
            # só o elenco foi salvo ("Dados do time"): relê moral e contratos sem esperar o save da carreira
            us = glob.glob(os.path.join(os.path.dirname(path), 'USERT*'))
            um = max(map(os.path.getmtime, us)) if us else None
            if um and um != getattr(self, '_usert_mtime', None):
                if getattr(self, '_usert_mtime', None) is not None:
                    with LOCK:
                        self.ler_elenco(self.career)
                    log('dados do time relidos (elenco salvo no jogo)')
                self._usert_mtime = um
            if self._esc_pendente and time.time() >= getattr(self, '_prox_tentativa', 0):
                with LOCK:
                    self.escalacao_processar(self.career)
                    self.persist()
            # save não mudou: se ficou crédito/multa pendente (ex.: falha ao gravar), tenta de novo
            if time.time() >= getattr(self, '_prox_tentativa', 0) and self.engine and self.career and (self.engine.pagamentos_pendentes() or any(
                    x['status'] == 'pendente' for x in (self.state or {}).get('multas', []) + (self.state or {}).get('debitos', []))):
                with LOCK:
                    self.aplicar_creditos()
                    self.persist()
            return
        # espera o jogo terminar de gravar (tamanho estável)
        s1 = os.path.getsize(path); time.sleep(1.5)
        if os.path.getsize(path) != s1 or os.path.getmtime(path) != m:
            return
        self.status['lendo'] = True
        try:
            car = savedata.Career(path, CFG.get('time_id'), self.resolver_time)
        except Exception as e:
            self.status['erro'] = f'Não consegui ler o save agora ({e}). Vou tentar de novo.'
            self.status['lendo'] = False
            return
        self.status['erro'] = None
        with LOCK:
            self.usar_time(car.team_id or CFG.get('time_id'))
            self.save_path, self.save_mtime, self.career = path, m, car
            sp = self.career_state_path(car.slot_name, car.team_id)
            novo = False
            if sp != self.state_path or self.state is None:
                self.state_path = sp
                self.state = jload(sp, {})
                novo = not self.state
                self.sync_estudio()
            st = self.state
            # carreira nova no mesmo arquivo: a data voltou muito
            # (ou voltou um pouco e o save tem menos jogos do clube do que o app já registrou)
            volta = st.get('data') and car.date and car.date < sim.s2d(st['data'])
            menos_jogos = False
            if volta:
                try:
                    menos_jogos = len(sumulas.do_time(bytes(car.sf.data), car.team_id)) < len(st.get('partidas', []))
                except Exception:
                    menos_jogos = False
            # ou o app guarda jogo com data depois da data do save (só pode ser de outra carreira)
            futuro = bool(car.date) and any(str(p.get('data', '')) > car.date.isoformat()
                                            for p in st.get('partidas', []) if isinstance(p, dict))
            if (volta and (car.date < sim.s2d(st['data']) - dt.timedelta(days=30) or menos_jogos)) or futuro:
                arq = sp.replace('.json', time.strftime('_arquivo_%Y%m%d_%H%M%S.json'))
                os.replace(sp, arq) if os.path.exists(sp) else None
                self.state = st = {}
                novo = True
                log('carreira nova detectada; estado anterior arquivado em', arq)
            st['time_id'] = self.tid()
            st['pais'] = (self.mapa.get(self.tid()) or 'Brasil').split('\\')[0]
            prest = tecnico_carreira.carregar(DATA).get('prestigio')
            if prest is not None:
                st['prestigio_tecnico'] = prest
            if novo:
                st['carreira_nova'] = True     # para a carreira do técnico abrir uma passagem nova
                # diretoria do clube novo recebe o técnico conforme o prestígio dele
                st.setdefault('mundo', {})['diretoria'] = tecnico_carreira.confianca_inicial(prest)
                # carreira começando agora (nenhum jogo no save): a receita de patrocínio do jogo volta a zero
                if not car.results and CFG.get('zerar_patrocinio_novo', False):
                    st['zerar_pat'] = {'status': 'pendente'}
            st['atr_base'] = self.time.get('atratividade_base', 60)
            self.engine = sim.Engine(st, self.clube(), self.time.get('atratividade_base', 60))
            for velho, novo_nome in (self.logos.map.get('_renomeados') or {}).items():
                self.engine.renomear_empresa(velho, novo_nome)
            nomes = [(n, '') for n in self.logos.nomes()]
            self.engine.sync_empresas(nomes)
            st['save_info'] = {'arquivo': path, 'slot': car.slot_name, 'clube': car.club_line,
                               'lido_em': time.strftime('%d/%m %H:%M:%S')}
            st['dinheiro'] = car.money()
            if car.tabela:
                st['tabela'] = {'linhas': car.tabela, 'data': sim.d2s(car.date) if car.date else None}
            # histórico financeiro (um ponto por data da carreira)
            fh = st.setdefault('fin_hist', [])
            ponto = {'data': sim.d2s(car.date), **st['dinheiro']}
            if fh and fh[-1]['data'] == ponto['data']:
                fh[-1] = ponto
            else:
                fh.append(ponto)
            st['fin_hist'] = fh[-200:]
            if car.fin_off is None:
                self.status['erro'] = 'Não achei o bloco de finanças nesse save.'
            # o app não mexe mais no dinheiro de transferências em carreira nova
            if (st.get('orc_inicial') or {}).get('status') == 'pendente':
                st['orc_inicial']['status'] = 'cancelado'
            antes = st.get('data')
            novas = self.engine.registrar_partidas(self.resultados_completos(car), self.tid(), sim.d2s(car.date))
            self.engine.avancar(car.date, primeira_leitura=novo)
            if novo:
                self.engine.ofertas_iniciais(car.date)
            self.presidente_processar()
            self.ler_elenco(car)
            self.verificar_creditos(car)
            self.aplicar_creditos()
            self.mundo_processar()
            self.gestao_processar(car, novas, None if novo else antes)
            self.carreira_processar(car, novo)
            self.assessor_processar(car, novas)
            self.escalacao_processar(car)
            if any(x['status'] == 'pendente' for x in st.get('debitos', [])):
                self.aplicar_creditos()        # punição do diretor de futebol (verba retirada)
            st['eventos'] = [e for e in st.get('eventos', []) if e['tipo'] != 'kits']
            self.persist()
        self.status['lendo'] = False
        threading.Thread(target=self.atualizar_ingame, daemon=True).start()
        log('save lido:', car.slot_name, car.date, 'patrocínio', st['dinheiro'].get('rec_patrocinio'))

    # ----- imprensa, torcida, diretoria -----
    def mundo_processar(self):
        try:
            self.state['cfg_tecnico'] = CFG.get('tecnico_nome') or 'Técnico'
            mu = mundo.Mundo(self.state, self.clube(), self.tid())
            mu.rivais = set(self.rivais_ids())
            mu.processar(self.engine, lambda i: self.names.get(i, f'Time {i}'))
        except Exception:
            log(traceback.format_exc())

    def gestao_processar(self, car, novas, antes):
        try:
            st = self.state
            mu = mundo.Mundo(st, self.clube(), self.tid())
            g = gestao.Gestao(st, self.clube(), self.tid())
            nomes = lambda i: self.names.get(i, f'Time {i}')
            if novas and antes:
                g.coletiva_nova(sorted(novas, key=lambda p: p['chave'])[-1], nomes, self.rivais_ids())
                for p in sorted(novas, key=lambda p: p['chave']):
                    medico.lesao_em_jogo(g, p, self.elenco, mu, self.engine)
            if car.date:      # campeonato terminou? título, acesso, rebaixamento (antes da revisão de janeiro)
                g.fim_de_liga(self.engine, mu, st.get('tabela'), car.date)
                g.copas(self.engine, mu, car.date)
            # eventos da semana e revisão de janeiro, para cada semana que passou desde a última leitura
            if antes and car.date:
                d = sim.s2d(antes)
                while d < car.date:
                    d = min(car.date, d + dt.timedelta(days=7))
                    g.semana(d, self.elenco, mu)
                    vestiario.semana(st, d, self.elenco, mu)
                    g.revisao_anual(self.engine, mu, d)
            g.elenco_mudou(self.elenco, car.money(), st.get('data'))
        except Exception:
            log(traceback.format_exc())

    def ao_vivo_evento(self, novos, dados):
        """Chamado pela thread do monitor quando o jogo grava eventos novos (gol, intervalo, fim)."""
        meu = self.tid()
        if meu not in (dados.get('casa'), dados.get('fora')):
            return
        lado_meu = 'casa' if dados.get('casa') == meu else 'fora'
        with LOCK:
            st = self.state
            if not st:
                return
            m = st.setdefault('mundo', {})
            for e in novos:
                if e.get('tipo') != 'gol':
                    continue
                nosso = e.get('lado') == lado_meu
                pl = e.get('placar') or dados.get('placar') or [0, 0]
                gp, gc = (pl[0], pl[1]) if lado_meu == 'casa' else (pl[1], pl[0])
                quem = (self.aovivo.jogadores.get(e.get('jogador_id')) or {}).get('nome') if e.get('jogador_id') else None
                txt = (f"GOOOOL{' DO ' + quem.upper() if quem else ''}! {gp} x {gc} aos {e.get('minuto', '?')}'! VAMOOOS {self.clube().upper()}! 🔥" if nosso else
                       f"Tomamos o gol aos {e.get('minuto', '?')}'. {gp} x {gc}. Acorda, time!")
                m.setdefault('posts', []).append({'data': st.get('data'), 'autor': '@torcida_aovivo', 'texto': txt,
                                                  'humor': 'euforia' if nosso else 'revolta', 'aovivo': True,
                                                  'curtidas': 0, 'reposts': 0, 'respostas': []})
            self.persist()

    def pessoas(self):
        st = self.state or {}
        return dirigentes.de(self.clube(), self.tid(), st.get('pais') or 'Brasil', st.get('dirigentes_editados'))

    def presidente_processar(self):
        try:
            if self.engine is not None and self.state is not None:
                presidente.Presidente(self.state, self.engine, self.clube(), self.pessoas()).processar()
        except Exception:
            log(traceback.format_exc())

    def diretor(self):
        return diretor.Diretor(self.state, self.engine, self.clube(), self.pessoas())

    def marketing(self):
        return marketing.Marketing(self.state, self.clube(), self.tid(), self.pessoas(), self.engine,
                                   CFG.get('tecnico_nome') or 'Técnico')

    def marketing_view(self):
        try:
            st = self.state
            return self.marketing().view(sim.s2d(st['data']) if st.get('data') else None)
        except Exception:
            log(traceback.format_exc()); return None

    def marketing_processar(self, mu, hoje):
        """Campanhas de cor no 3º/4º uniforme: sugere, encerra e devolve as cores de antes."""
        if not (self.time and self.time.get('preparado')):
            return
        def paleta_de(fam):
            v = next(x for x in kits.VARIANTS if x[2] == fam)
            return estudio.paleta(kits.base_image(APP_DIR, v[0], v[1]))
        self.marketing().processar(mu, hoje, kits.VARIANTS, paleta_de, estudio.PRESETS)
        self.sync_estudio()

    def assessor_processar(self, car, novas):
        """Assessor de imprensa: posts, respostas à torcida, briefing e (talvez) vazamentos."""
        try:
            st = self.state
            ass = assessor.Assessor(st, self.clube(), self.tid(), CFG.get('tecnico_nome') or 'Técnico')
            sums = (self.estatisticas or {}).get('sumulas') or []
            ass.processar(self.engine, novas or [], sums, lambda i: self.names.get(i, f'Time {i}'),
                          sim.d2s(car.date) if car.date else st.get('data'))
        except Exception:
            log(traceback.format_exc())

    def rivais_ids(self):
        st = self.state or {}
        return rivais.rivais(self.clube(), self.names, (st.get('gestao') or {}).get('rivais_manual'))

    def carreira_processar(self, car, novo):
        """Estrutura (obras), emprego do técnico, marca, gramado e a carreira do técnico entre clubes."""
        st = self.state
        try:
            mu = mundo.Mundo(st, self.clube(), self.tid())
            estrutura.avancar(st, car.date, mu)
            diretoria.processar(st, self.engine, mu, car.date, self.names)
            self.diretor().processar(mu, car.date, self.names)
            try:
                self.marketing_processar(mu, car.date)
            except Exception:
                log(traceback.format_exc())
            estrutura.registrar_marca(st, car.date)
            medico.processar(st, car.date, mu, self.engine)
            ingame.condicao_gramado(st, car.date, self.tid(), self.names)
            # cada carreira do jogo tem uma identidade própria: recomeçar no mesmo arquivo com o mesmo clube
            # vira uma passagem nova (o estado anterior foi arquivado) e não apaga a antiga
            if st.pop('carreira_nova', False) and not st.get('carreira_id'):
                st['carreira_id'] = time.strftime('%Y%m%d%H%M%S')
                if tecnico_carreira.tem_chave(DATA, os.path.basename(self.state_path or 'carreira') + '|' + str(self.tid())):
                    st['carreira_id_novo'] = True
            chave = os.path.basename(self.state_path or 'carreira') + '|' + str(self.tid())
            if st.get('carreira_id_novo'):
                chave += '|' + st['carreira_id']
            self.chave_tec = chave
            c, nova = tecnico_carreira.registrar(DATA, chave, st, self.clube(), car.date)
            st['prestigio_tecnico'] = c['prestigio']
            if nova and len(c['passagens']) > 1 and car.date:
                ant = [p for p in c['passagens'] if p['chave'] != chave]
                tits = sum(len(p.get('titulos', [])) for p in ant)
                nv = tecnico_carreira.nivel(c['prestigio'])
                mu.m['noticias'].append({'data': sim.d2s(car.date), 'tipo': 'tecnico_chega', 'destaque': True,
                                         'fonte': 'Globo Esporte', 'titulo': f"{mu.tecnico()} é o novo técnico do {self.clube()}: "
                                         f"{len(ant)} clube(s) na carreira, {tits} título(s) e prestígio de {nv.lower()}"})
        except Exception:
            log(traceback.format_exc())

    def dirigentes_view(self):
        p = self.pessoas()
        try:
            dv = self.diretor().view()
        except Exception:
            log(traceback.format_exc()); dv = None
        return {'presidente': {**p['presidente'], **presidente.Presidente(self.state, self.engine, self.clube(), p).view()}
                if self.engine else p['presidente'],
                'diretor': {**p['diretor'], **(dv or {})}, 'assessor': p['assessor'],
                'marcas_novas': (self.state.get('marcas_novas') or [])[-6:]}

    def carreira_view(self):
        st = self.state or {}
        hoje = sim.s2d(st['data']) if st.get('data') else None
        mu = mundo.Mundo(st, self.clube(), self.tid()) if st else None
        nm = lambda i: self.names.get(i, f'Time {i}')
        ids = self.rivais_ids()
        rr = rivais.retrospecto(st.get('partidas', []), self.tid(), set(ids))
        manual = (st.get('gestao') or {}).get('rivais_manual') or []
        auto = rivais.rivais(self.clube(), self.names, [])
        times = sorted({l['id']: l.get('nome') or nm(l['id']) for l in (st.get('tabela') or {}).get('linhas', [])
                        if l['id'] != self.tid()}.items(), key=lambda x: x[1])
        gr = st.get('gramado') or {}
        cond = gr.get('cond')
        try:
            ret = retro.resumo(st, self.tid(), self.names, set(ids))
        except Exception:
            log(traceback.format_exc()); ret = []
        return {
            'diretoria': diretoria.view(st, mu, hoje) if mu else None,
            'vestiario': vestiario.view(st), 'estrutura': estrutura.view(st, hoje),
            'imprensa': (st.get('gestao') or {}).get('imprensa', 55),
            'rivais': [{'id': i, 'nome': nm(i), 'auto': i in auto, 'classico': rivais.nome_classico(self.clube(), nm(i)),
                        **{k: (rr.get(i) or {}).get(k, 0) for k in ('V', 'E', 'D')}, 'jogos': (rr.get(i) or {}).get('jogos', [])}
                       for i in ids],
            'rivais_manual': manual, 'times_tabela': [{'id': i, 'nome': n} for i, n in times],
            'gramado': {'cond': cond, 'nivel': ingame.nivel_gramado(cond)[0] if cond is not None else None,
                        'hist': gr.get('hist', [])[-30:]},
            'retro': ret, 'tecnico': {**tecnico_carreira.view(tecnico_carreira.carregar(DATA)),
                                      'arquivadas': tecnico_carreira.arquivadas(DATA)},
            'medico': medico.view(st, hoje, {j['id'] for j in (self.elenco or [])} or None),
            'ranking': self.ranking_view(),
        }

    def ranking_view(self):
        t = ranking.tabela(self.mapa)
        atual = next((c for c in t if c['id'] == self.tid()), None)
        return {'lista': [{k: c[k] for k in ('id', 'pos', 'nome', 'pais', 'liga', 'valor', 'torcida', 'prestigio',
                                              'nota', 'nivel', 'medido')} for c in t if c['pais'] == 'Brasil' and c['liga'] in ('Série A', 'Série B')
                          or c['nota'] >= 25],
                'atual': atual, 'prestigio_tecnico': (self.state or {}).get('prestigio_tecnico'),
                'pais': (self.state or {}).get('pais')}

    def cores_time(self):
        t = self.time
        if not t:
            return None
        if not t.get('cores'):
            try:
                v = t['variantes'][0]
                t['cores'] = gestao.cores_do_uniforme(kits.base_image(APP_DIR, v[0], v[1]))
                self.times.salvar(t)
            except Exception:
                return None
        return t['cores']

    # ----- escalação do jogo (plano de jogo no save) -----
    def _indisponivel_fn(self, dia):
        """pid -> motivo se o app afastou o jogador nessa data (lesão, indisciplina, problema pessoal)."""
        st = self.state or {}
        g = gestao.Gestao(st, self.clube(), self.tid())

        def f(pid):
            ev = g.afastado(pid, dia) if dia else None
            if not ev:
                return None
            return {'motivo': ev.get('titulo') or ev.get('tipo'), 'tipo': ev.get('tipo'), 'volta': ev.get('volta')}
        return f

    def _posicao_fn(self):
        pos = {j['id']: j.get('pos', '') for j in (self.elenco or [])}
        return lambda pid: pos.get(pid, '')

    def _nome(self, pid):
        for j in self.elenco or []:
            if j['id'] == pid:
                return j['nome']
        return f'Jogador {pid}'

    def escalacao_processar(self, car):
        """Lê o plano de jogo do save; se houver afastado do app entre os relacionados, troca e grava."""
        self._esc_pendente = False
        if car is None:
            return
        try:
            d = bytes(car.sf.data)
            esc = escalacao.ler(d, savedata.team_index(d, car.team_id))
        except Exception:
            log(traceback.format_exc())
            esc = None
        self.escalacao = esc
        if not esc or not CFG.get('escalacao_auto', True) or not car.date:
            return
        indisp = self._indisponivel_fn(car.date)
        ordem, mud = escalacao.ajustar(esc, indisp, self._posicao_fn())
        # quem estava afastado e foi liberado vai para a 1ª vaga dos não relacionados
        st = self.state
        noelenco = [p for p in esc['vagas'] if p]
        afast_agora = [p for p in noelenco if indisp(p)]
        antes_afast = st.get('escalacao_afastados')
        liberados = [p for p in (antes_afast or []) if p in noelenco and p not in afast_agora]
        for pid in reversed(liberados):
            if escalacao.mover_para_primeiro_fora(ordem, esc['vagas'], pid):
                mud.append(('liberado', pid, None, None))
        st['escalacao_afastados'] = afast_agora
        if ordem == esc['ordem']:
            return
        antes = list(esc['ordem'])
        try:
            escalacao.gravar(car, esc, ordem)
            bk = car.write(os.path.join(DATA, 'backups_save'), log)
        except Exception as e:
            car.sf.data[esc['off']:esc['off'] + escalacao.TAM] = bytes(antes)
            esc['ordem'] = antes
            self._esc_pendente = True
            self._prox_tentativa = time.time() + 20
            self.status['erro'] = f'Não gravei a escalação agora ({e}). Vou tentar de novo.'
            log('escalação não gravada:', e)
            return
        self.save_mtime = car.mtime
        self.status['erro'] = None
        saem, entram, banco, liberado_txt = {}, [], [], []
        for m in mud:
            if not isinstance(m, tuple):
                continue
            tipo, entrou, saiu, info = m
            if tipo == 'liberado':
                liberado_txt.append(self._nome(entrou))
                continue
            if info:
                saem.setdefault(saiu, (info.get('motivo') or 'afastado').lower())
            if tipo == 'entra':
                entram.append(f'{self._nome(entrou)} no lugar de {self._nome(saiu)}')
            else:
                banco.append(self._nome(entrou))
        linhas = []
        if saem:
            linhas.append('fora dos relacionados: ' + ', '.join(f'{self._nome(p)} ({mot})' for p, mot in saem.items()))
        if entram:
            linhas.append('entram no time: ' + ', '.join(entram))
        if banco:
            linhas.append('sobem para o banco: ' + ', '.join(banco))
        if liberado_txt:
            linhas.append('liberados pelo departamento médico (1º dos não relacionados): ' + ', '.join(liberado_txt))
        texto = '; '.join(linhas) or 'jogadores afastados foram tirados dos relacionados'
        hoje = st.get('data')
        st.setdefault('escalacao_hist', []).append({'data': hoje, 'mudancas': linhas,
                                                    'lido_em': time.strftime('%d/%m %H:%M')})
        st['escalacao_hist'] = st['escalacao_hist'][-30:]
        st.setdefault('mensagens', []).append({
            'id': self.engine._id() if self.engine else f'esc{int(time.time())}', 'data': hoje,
            'empresa': '__diretoria__', 'de': 'Comissão técnica', 'assunto': 'Escalação ajustada no plano de jogo',
            'texto': texto[0].upper() + texto[1:] + '.',
            'tipo': 'medico', 'oferta_id': None, 'lida': False})
        aviso = ('Escalação ajustada: ' + texto + '. No jogo, volte ao menu principal e carregue a carreira de novo. '
                 'Não salve antes de recarregar.')
        self.status['aviso'] = (self.status['aviso'] + ' ' + aviso) if self.status.get('aviso') else aviso
        st['aviso_recarregar'] = True
        log('escalação ajustada no save:', texto, 'backup', bk)

    def escalacao_view(self):
        esc = self.escalacao
        car = self.career
        if not esc or not car:
            return None
        indisp = self._indisponivel_fn(car.date)
        pos = self._posicao_fn()

        def item(s):
            pid = esc['vagas'][s] if s < len(esc['vagas']) else None
            if pid is None:
                return {'vaga': s, 'vazio': True}
            return {'vaga': s, 'id': pid, 'nome': self._nome(pid), 'pos': pos(pid), 'fora': indisp(pid)}
        tit, res, fora = escalacao.grupos(esc['ordem'])
        det, curto = escalacao.nome_formacao(esc.get('formacao'))
        conhecidas = {'4-2-3-1', '4-1-4-1', '4-3-2-1', '4-4-1-1', '3-4-2-1', '4-3-3', '4-4-2', '3-5-2', '3-4-3', '5-3-2',
                      '5-4-1', '4-5-1', '4-1-2-1-2'}
        nome_f = det if (det in conhecidas or not curto or curto == det) else f'{det} (variação do {curto})'
        return {'titulares': [item(s) for s in tit], 'reservas': [item(s) for s in res], 'formacao_nome': nome_f,
                'fora': [item(s) for s in fora if s < len(esc['vagas']) and esc['vagas'][s] is not None],
                'ordem': esc['ordem'], 'formacao': esc.get('formacao'), 'auto': CFG.get('escalacao_auto', True),
                'hist': (self.state or {}).get('escalacao_hist', [])[-5:][::-1]}

    def escalacao_salvar(self, ordem):
        """Grava no save a escalação montada na tela."""
        car, esc = self.career, self.escalacao
        if not car or not esc:
            raise ValueError('Ainda não li a escalação do save.')
        if os.path.getmtime(car.path) != car.mtime:
            raise ValueError('O jogo salvou de novo. Espere o app ler o save e tente outra vez.')
        ordem = [int(x) for x in ordem]
        if sorted(ordem) != sorted(esc['ordem']):
            raise ValueError('Escalação inválida.')
        escalacao.validar(ordem, esc['vagas'], self._indisponivel_fn(car.date))
        antes = list(esc['ordem'])
        if ordem == antes:
            return False
        try:
            escalacao.gravar(car, esc, ordem)
            car.write(os.path.join(DATA, 'backups_save'), log)
        except Exception:
            car.sf.data[esc['off']:esc['off'] + escalacao.TAM] = bytes(antes)
            esc['ordem'] = antes
            raise
        self.save_mtime = car.mtime
        self.status['aviso'] = ('Escalação gravada no save. No jogo, volte ao menu principal e carregue a carreira '
                                'de novo. Não salve antes de recarregar.')
        self.state['aviso_recarregar'] = True
        log('escalação gravada pela tela')
        return True

    def elenco_view(self):
        st = self.state or {}
        el = [dict(j) for j in (self.elenco or [])]
        try:
            gestao.moral_efetiva(st, el, sim.s2d(st['data']) if st.get('data') else None)
        except Exception:
            log(traceback.format_exc())
        return el

    def _logos_vigentes(self):
        from PIL import Image
        st = self.state or {}
        ativos = sorted([c for c in st.get('contratos', []) if c['status'] in ('ativo', 'assinado')],
                        key=lambda c: -c.get('valor', 0))
        logos, patro = [], None
        for c in ativos:
            lp = self.logos.path(c['empresa'])
            if os.path.exists(lp) and c['empresa'] not in [n for n, _ in logos]:
                im = Image.open(lp)
                logos.append((c['empresa'], im))
                if c['slot'] == 'peito':
                    patro = im
        if patro is None and logos:
            patro = logos[0][1]
        return logos, patro

    def atualizar_ingame(self, forcar=False):
        """Faixas, gramado e bandeirinhas do estádio do clube atual (refeito só quando algo muda)."""
        if not CFG.get('visuais_jogo', True) or self.state is None or not self.tid():
            return
        try:
            from PIL import Image
            with LOCK:      # lê o estado com a trava: a leitura do save pode estar mexendo nele
                return self._atualizar_ingame(forcar, Image)
        except Exception:
            log(traceback.format_exc())

    def _atualizar_ingame(self, forcar, Image):
        if True:
            st = self.state
            if st is None:
                return
            cond = (st.get('gramado') or {}).get('cond', 75)
            gram = ingame.nivel_gramado(cond)
            hoje = sim.s2d(st['data']) if st.get('data') else None
            ids = set(self.rivais_ids())
            plano = ingame.plano_faixas(st, self.clube(), hoje, CFG.get('tecnico_nome') or 'Técnico',
                                        vestiario.idolo(st), [self.names.get(i) for i in ids])
            logos, patro = self._logos_vigentes()
            mestre = next((c['empresa'] for c in st.get('contratos', []) if c['status'] in ('ativo', 'assinado')
                           and c['slot'] == 'peito'), None)
            cores = self.cores_time() or []
            assin = [self.tid(), cores, mestre, plano['modo'], plano['motivo'].split(' (')[0], plano['fracao'],
                     sorted(plano['vars'].items()), list(gram), 2]
            if not forcar and st.get('ingame_assin') == assin:
                return
            ingame.instalar_modulo(CFG.get('pasta_jogo', ''), os.path.join(DATA, 'backups_save'), log)
            eb = self.escudo_png()
            esc = Image.open(io.BytesIO(eb)) if eb else None
            res = ingame.gerar(CFG.get('pasta_jogo', ''), self.tid(), self.clube(), cores, esc, patro, plano, gram, log)
            res['gramado_cond'] = cond
            res['em'] = st.get('data')
            st['ingame'] = res
            st['ingame_assin'] = assin
            log('visual do estádio atualizado:', res)
            self.persist()

    def cena_jpg(self, humor):
        """Foto da coletiva com o agasalho nas cores do clube e o painel dos patrocinadores vigentes."""
        if not cena.disponiveis(DATA):
            return None
        try:
            from PIL import Image
            st = self.state or {}
            cores = self.cores_time() or ['#1f6b3a', '#ffffff']
            def sat(h):
                c = [int(h.lstrip('#')[i:i + 2], 16) for i in (0, 2, 4)]
                return max(c) - min(c)
            cor1 = max(cores, key=sat) if max(sat(c) for c in cores) >= 40 else cores[0]
            cor2 = next((c for c in cores if c != cor1), '#ffffff')
            eb = self.escudo_png()
            esc = Image.open(io.BytesIO(eb)) if eb else None
            ativos = sorted([c for c in st.get('contratos', []) if c['status'] in ('ativo', 'assinado')],
                            key=lambda c: -c.get('valor', 0))
            logos, patro = [], None
            for c in ativos:
                lp = self.logos.path(c['empresa'])
                if os.path.exists(lp) and c['empresa'] not in [n for n, _ in logos]:
                    im = Image.open(lp)
                    logos.append((c['empresa'], im))
                    if c['slot'] == 'peito':
                        patro = im
            if patro is None and logos:
                patro = logos[0][1]
            return cena.compor(DATA, humor, cor1, cor2, esc, patro, logos, self.clube())
        except Exception:
            log(traceback.format_exc())
            return None

    def escudo_png(self):
        """Escudo do clube recortado do uniforme (caixa achada na detecção), com o tecido transparente."""
        t = self.time
        if not t:
            return None
        p = os.path.join(DATA, f"escudo3_{t.get('id', self.tid())}.png")
        if not os.path.exists(p) and not t.get('variantes'):
            return None                     # uniformes do clube ainda não preparados
        if not os.path.exists(p):
            try:
                from PIL import Image
                v = t['variantes'][0]
                if not os.path.exists(kits.base_path(APP_DIR, v[0], v[1])):
                    return None             # base do uniforme ainda não copiada (preparo em andamento)
                img = kits.base_image(APP_DIR, v[0], v[1]).convert('RGB').convert('RGBA')
                x0, y0, x1, y1 = [int(c) for c in (kits.ESCUDO.get(v[0]) or [1098, 1105, 1222, 1232])]
                x0, y0, x1, y1 = x0 - 12, y0 - 12, x1 + 12, y1 + 12
                cr = img.crop((x0, y0, x1, y1))
                m = estudio._mascara_logo(cr)
                out = Image.new('RGBA', cr.size, (0, 0, 0, 0))
                out.paste(cr, (0, 0), m)
                bb = out.getbbox()
                (out.crop(bb) if bb else out).save(p)
            except Exception:
                log(traceback.format_exc())
                return None
        return open(p, 'rb').read()

    def gestao_view(self):
        st = self.state or {}
        g = st.get('gestao') or {}
        hoje = sim.s2d(st['data']) if st.get('data') else None
        evs = []
        for e in g.get('eventos', [])[-20:][::-1]:
            evs.append({**e, 'ativo': bool(hoje and sim.s2d(e['data']) <= hoje < sim.s2d(e['volta']))})
        return {'coletivas': g.get('coletivas', [])[-8:][::-1], 'eventos': evs,
                'transferencias': g.get('transferencias', [])[-60:][::-1], 'prancheta': g.get('prancheta', {}),
                'revisoes': g.get('revisoes', [])[-5:][::-1],
                'rostos': tecnico.listar(os.path.join(DATA, 'tecnico')), 'cena': cena.disponiveis(DATA),
                'tecnico_nome': CFG.get('tecnico_nome') or 'Técnico'}

    # ----- dinheiro no jogo -----
    def verificar_creditos(self, car):
        money = car.money()
        if not money:
            return
        oi = self.state.get('orc_inicial')
        if oi and oi.get('status') == 'aplicado':
            if money['orc_transf'] == oi.get('antes') and oi.get('antes') != oi['valor']:
                oi['status'] = 'pendente'    # o jogo gravou por cima antes de recarregar
            elif sim.d2s(car.date) != oi.get('em'):
                oi['status'] = 'confirmado'
        z = self.state.get('zerar_pat')
        if z and z.get('status') == 'aplicado':
            creditou = any(pg['status'] in ('creditado', 'confirmado') for c in self.state.get('contratos', [])
                           for pg in c['pagamentos'])
            if money['rec_patrocinio'] <= 0 or creditou:
                z['status'] = 'confirmado'
            elif money['rec_patrocinio'] >= z.get('valor', 0) > 0:
                z['status'] = 'pendente'     # o jogo gravou por cima antes de recarregar
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
        z = self.state.get('zerar_pat')
        zerar = bool(z and z.get('status') == 'pendente')
        oi = self.state.get('orc_inicial')
        definir = bool(oi and oi.get('status') == 'pendente')
        debs = [x for x in self.state.get('debitos', []) if x['status'] == 'pendente']
        if (not pend and not multas and not zerar and not definir and not debs) or self.career is None or self.career.fin_off is None:
            return
        car = self.career
        total = 0; total_multa = 0
        orc_antes = car.money().get('orc_transf', 0)
        if definir and orc_antes == oi['valor']:
            oi.update(status='confirmado', antes=orc_antes, em=self.state['data'])
            definir = False
            if not pend and not multas and not zerar and not debs:
                return
        if definir:
            antes2 = car.money().get('orc_transf_2', 0)
            car.definir_orcamento(oi['valor'])
        zerado = car.zerar_patrocinio() if zerar else 0
        if zerar and not zerado and not pend and not multas and not debs:
            z.update(status='confirmado', valor=0)       # já estava zerado: nada a gravar
            return
        for c, pg in pend:
            car.credit_sponsor(pg['valor'])
            total += pg['valor']
        for m in multas:
            car.credit_sponsor(-m['valor'])
            total_multa += m['valor']
        total_deb = 0
        for x in debs:
            car.debitar(x['valor'])
            total_deb += x['valor']
        try:
            bk = car.write(os.path.join(DATA, 'backups_save'), log)
        except Exception as e:
            self.status['erro'] = str(e)
            log('não gravou o crédito:', e)
            if 'Bad file descriptor' in str(e) or 'No such file' in str(e):
                self.status['erro'] = ('O Windows bloqueou a gravação do save. Libere o Python em Segurança do Windows > '
                                       'Proteção contra ransomware > Permitir um aplicativo pelo Acesso controlado a pastas.')
            self._prox_tentativa = time.time() + 20
            # desfaz na memória o que foi somado (a próxima tentativa soma de novo)
            for c, pg in pend:
                car.credit_sponsor(-pg['valor'])
            for m in multas:
                car.credit_sponsor(m['valor'])
            for x in debs:
                car.debitar(-x['valor'])
            if zerado:
                car.desfazer_zerar(zerado, orc_antes)
            if definir:
                import struct as _st
                _st.pack_into('<i', car.sf.data, car.fin_off + savedata.FIN['orc_transf'], orc_antes // savedata.UNIT)
                _st.pack_into('<i', car.sf.data, car.fin_off + savedata.FIN['orc_transf_2'], antes2 // savedata.UNIT)
            return
        self.save_mtime = car.mtime
        self.status['erro'] = None
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
        for x in debs:
            x['status'] = 'aplicado'; x['aplicado_em'] = hoje
        if zerar:
            z.update(status='aplicado' if zerado else 'confirmado', valor=zerado, em=hoje)
        self.state['dinheiro'] = money
        partes = []
        if definir:
            oi.update(status='aplicado', antes=orc_antes, em=hoje)
            partes.append(f'o dinheiro de transferências do clube foi definido em {sim.fmt_eur(oi["valor"])} '
                          f'(antes: {sim.fmt_eur(orc_antes)}) para o início da carreira')
        if zerado:
            partes.append(f'a receita de patrocínio que veio com a carreira ({sim.fmt_eur(zerado)}) foi zerada '
                          'para os novos patrocinadores começarem do zero (o orçamento de transferências não foi alterado)')
        if total:
            partes.append(f'{sim.fmt_eur(total)} de patrocínio foram colocados no save')
        if total_multa:
            partes.append(f'{sim.fmt_eur(total_multa)} de multa de rescisão foram descontados')
        saiu = sum(x['valor'] for x in debs if x['valor'] > 0)
        entrou = -sum(x['valor'] for x in debs if x['valor'] < 0)
        if saiu:
            de_onde = 'por decisão da diretoria' if any(x.get('origem') == 'diretor' and x['valor'] > 0 for x in debs) else 'para as obras de estrutura'
            partes.append(f'{sim.fmt_eur(saiu)} saíram do orçamento de transferências {de_onde}')
        if entrou:
            partes.append(f'{sim.fmt_eur(entrou)} de verba extra da diretoria entraram no orçamento de transferências')
        if not partes:
            return
        partes[0] = partes[0][0].upper() + partes[0][1:]
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
                                   c.get('dx', 0), c.get('dy', 0), json.dumps(c.get('ajustes') or {}, sort_keys=True),
                                   sorted((c.get('cores') or {}).items())] for c in cs]), ensure_ascii=False)

    def sync_estudio(self):
        kits.ESTUDIO.clear()
        kits.ESTUDIO.update((self.state or {}).get('estudio') or {})

    def kits_pendentes(self):
        if self.state is None or not self.time or not self.time.get('preparado'):
            return []
        atual = self.contratos_visiveis()
        aplicado = self.state.get('kits_aplicados')
        if aplicado is None:
            return [f"primeira aplicação: deixar os {len(kits.VARIANTS)} uniformes do {self.clube()} sem os patrocínios "
                    "originais (confira a limpeza na aba Uniformes antes de aplicar)"]
        if aplicado == 'teste':
            return ['voltar ao normal depois do teste (contratos que ainda não começaram saem do uniforme)']
        mud_est = json.dumps(self.state.get('estudio') or {}, sort_keys=True) != \
            json.dumps(self.state.get('estudio_aplicado') or {}, sort_keys=True)
        desenho = [] if self.state.get('kits_desenho', 1) == kits.VERSAO_DESENHO else \
            ['logos redesenhados (letras brancas e placas como a da Condor não somem mais)']
        ja = set(self.state.get('kits_variantes') or [v[0] for v in kits.VARIANTS if not v[0].startswith('g')])
        novos = [v for v in kits.VARIANTS if v[0] not in ja]
        if novos:
            gol = [v for v in novos if kits.e_goleiro(v[2])]
            desenho = desenho + ([f"uniformes de goleiro ({len(gol)}) recebem os patrocínios"] if gol else []) + \
                ([f"{len(novos) - len(gol)} uniforme(s) novo(s) recebem os patrocínios"] if len(novos) > len(gol) else [])
        if self.assinatura(atual) == aplicado:
            return (['cores, estrelas ou número do Estúdio de uniformes'] if mud_est else []) + desenho
        antes = {c[0]: c for c in json.loads(aplicado)}
        mud = []
        for c in atual:
            if c['id'] not in antes:
                mud.append(f"entra {c['empresa']} ({kits.SLOTS.get(c['slot'], {}).get('nome', c['slot'])})")
            elif antes[c['id']] != json.loads(self.assinatura([c]))[0]:
                mud.append(f"ajuste no logo da {c['empresa']}")
        ids = {c['id'] for c in atual}
        for cid, c in antes.items():
            if cid not in ids:
                mud.append(f"sai {c[2]} ({kits.SLOTS.get(c[1], {}).get('nome', c[1])})")
        return (mud or ['atualização dos uniformes']) + desenho

    def aplicar_kits(self):
        if self.kit_thread and self.kit_thread.is_alive():
            raise ValueError('Os uniformes já estão sendo gravados. Aguarde terminar.')
        if not self.time or not self.time.get('preparado'):
            raise ValueError('Os uniformes do clube ainda estão sendo preparados. Aguarde terminar.')
        cs = json.loads(json.dumps(self.contratos_visiveis()))
        sig = self.assinatura(cs)
        self.sync_estudio()
        est = json.loads(json.dumps(self.state.get('estudio') or {}))

        def prog(i, n, v):
            self.status['kits_prog'] = [i, n]
            self.status['kits_msg'] = f'Gravando uniforme {min(i + 1, n)} de {n}...' if i < n else 'Concluído'

        def run():
            self.status['kits'] = 'trabalhando'
            try:
                kits.install(APP_DIR, self.time['pasta'], cs, self.logos.load, log, prog)
                with LOCK:
                    self.state['kits_aplicados'] = sig
                    self.state['kits_desenho'] = kits.VERSAO_DESENHO
                    self.state['kits_variantes'] = sorted(v[0] for v in kits.VARIANTS)
                    self.state['estudio_aplicado'] = est
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

    def time_view(self):
        t = self.time
        if not t:
            return None
        return {'id': t['id'], 'nome': t['nome'], 'preparado': bool(t.get('preparado')),
                'prep': self.times.prep.get(t['id']), 'n_uniformes': len(t['variantes']),
                'aprendidos': [k for k, v in t['slots'].items() if v.get('aprendido')]}

    def resultados_completos(self, car):
        """Partidas do clube: o histórico curto do save (só os jogos que você jogou) mais as súmulas da temporada,
        que também têm os jogos simulados. Um jogo que já está no histórico do app não entra de novo."""
        res = list(car.results or [])
        try:
            vistos = {(r['torneio'], r['mandante'], r['visitante']) for r in res}
            ja = {}
            for p in (self.state or {}).get('partidas', []):
                ja.setdefault((p['torneio'], p['mandante'], p['visitante']), []).append(p.get('data') or '')
            for i, m in enumerate(sumulas.do_time(bytes(car.sf.data), car.team_id or self.tid())):
                k = (m['torneio'], m['mandante'], m['visitante'])
                if k in vistos:
                    continue
                dj = sim.s2d(m['data'])
                if any(d and dj - dt.timedelta(days=1) <= sim.s2d(d[:10]) <= dj + dt.timedelta(days=200)
                       for d in ja.get(k, [])):
                    continue
                res.append({**m, 'offset': 10 ** 12 + i, 'data_jogo': m['data']})
        except Exception:
            log(traceback.format_exc())
        return res

    def estatisticas_view(self):
        e = self.estatisticas
        if not e:
            return None
        nm = lambda i: self.names.get(i, f'Time {i}')
        return {**e, 'sumulas': [{**p, 'mandante_nome': nm(p['mandante']), 'visitante_nome': nm(p['visitante']),
                                  'torneio_nome': TORNEIOS.get(p['torneio'] & 1023, f"Torneio {p['torneio']}")}
                                 for p in e['sumulas']]}

    # ----- visão para a interface -----
    def view(self):
        st = self.state or {}
        eng = self.engine
        nm = lambda i: self.names.get(i, f'Time {i}')
        partidas = []
        for p in st.get('partidas', [])[-10:]:
            partidas.append({**p, 'mandante_nome': nm(p['mandante']), 'visitante_nome': nm(p['visitante']),
                             'torneio_nome': TORNEIOS.get(p['torneio'] & 1023, 'Copa')})
        empresas = []
        for n, e in sorted(st.get('empresas', {}).items()):
            empresas.append({'nome': n, **e, 'global': sim.e_global(n, e)})
        return {
            'pronto': self.state is not None, 'versao': VERSAO,
            'config': {'problemas': config_status(), 'pasta_jogo': CFG.get('pasta_jogo', ''),
                       'pasta_saves': CFG.get('pasta_saves', ''), 'pasta_logos': CFG.get('pasta_logos', ''),
                       'tecnico_nome': CFG.get('tecnico_nome', ''), 'primeira': not CFG.get('configurado')},
            'clube': self.clube() if (self.time or self.state is not None or CFG.get('clube')) else '', 'time': self.time_view(),
            'moeda': {'cod': sim.MOEDA['cod'], 'simbolo': sim.moeda()[0], 'taxa': sim.moeda()[1],
                      'opcoes': {k: v[0] for k, v in sim.MOEDAS.items()}}, 'elenco': self.elenco_view(), 'moral_data': self.moral_data, 'data': st.get('data'), 'dinheiro': st.get('dinheiro', {}),
            'atratividade': eng.atratividade() if eng else None, 'forma': eng.forma() if eng else '',
            'partidas': partidas[::-1], 'tabela': st.get('tabela'),
            'linha_tempo': [{**p, 'mandante_nome': nm(p['mandante']), 'visitante_nome': nm(p['visitante']),
                             'torneio_nome': TORNEIOS.get(p['torneio'] & 1023, f"Torneio {p['torneio']}")}
                            for p in st.get('partidas', [])[-30:]],
            'gestao': self.gestao_view(), 'cores': self.cores_time(), 'carreira': self.carreira_view(),
            'ofertas': [o for o in st.get('ofertas', []) if o['status'] in ('aberta', 'aguardando')],
            'ofertas_hist': [o for o in st.get('ofertas', []) if o['status'] not in ('aberta', 'aguardando')][-20:][::-1],
            'contratos': st.get('contratos', []),
            'mensagens': st.get('mensagens', [])[-60:][::-1],
            'ingame': st.get('ingame'), 'empresas': empresas, 'empresas_removidas': st.get('empresas_removidas', []),
            'empresas_sem_logo': self.logos.sem_imagem([e['nome'] for e in empresas]),
            'redistrib': st.get('redistrib', [])[-6:][::-1],
            'slots': [{'id': k, **{kk: vv for kk, vv in kits.SLOTS[k].items() if kk != 'lugares'}} for k in kits.SLOT_ORDER],
            'livres': eng.slots_livres(eng.hoje()) if eng and eng.hoje() else [],
            'familias': kits.FAMILIAS if self.time else {},
            'save': st.get('save_info'), 'jogo_aberto': self.game_running(),
            'status': self.status, 'avisos': st.pop('avisos', []) if st else [],
            'kits_pendentes': self.kits_pendentes(), 'multas': st.get('multas', []),
            'fin_hist': st.get('fin_hist', [])[-60:],
            'mundo': mundo.Mundo(st, self.clube(), self.tid()).view() if st else None, 'jornalistas': imprensa.lista(),
            'assessor': assessor.Assessor(st, self.clube(), self.tid(), CFG.get('tecnico_nome') or 'Técnico').view() if st else None,
            'zerar_pat': st.get('zerar_pat'),
            'dirigentes': self.dirigentes_view() if st else None,
            'marketing': self.marketing_view() if st else None,
            'estatisticas': self.estatisticas_view(),
            'escalacao': self.escalacao_view() if st else None,
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


def atualizar_logos():
    """Lê a pasta de logos: empresas novas entram no app; imagens trocadas ou sem cópia limpa são refeitas
    com o fundo transparente."""
    with LOGOS_LOCK:
        novos = A.logos.scan()
        atualizados = list(A.logos.atualizados)
        renomeados = dict(A.logos.renomeados)
    if (novos or renomeados) and A.engine:
        with LOCK:
            for velho, novo_nome in renomeados.items():
                A.engine.renomear_empresa(velho, novo_nome)
            A.engine.sync_empresas([(n['nome'], n['pasta']) for n in novos])
            A.persist()
    if novos:
        log('logos novos:', [n['nome'] for n in novos])
    if atualizados:
        log('logos refeitos:', atualizados)
    return novos, atualizados


def logos_watcher():
    while True:
        try:
            atualizar_logos()
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
        try:
            self.end_headers()
            self.wfile.write(body)
        except (ConnectionError, OSError):
            pass   # a janela fechou ou recarregou no meio da resposta: não é erro

    def do_GET(self):
        u = urlparse(self.path)
        q = {k: v[0] for k, v in parse_qs(u.query).items()}
        try:
            if u.path.startswith('/web/') and u.path.endswith('.js'):
                p = os.path.join(APP_DIR, 'web', os.path.basename(u.path))
                if os.path.exists(p):
                    return self.send(200, open(p, 'rb').read(), 'text/javascript; charset=utf-8')
            if u.path in ('/', '/index.html'):
                return self.send(200, open(os.path.join(APP_DIR, 'web', 'index.html'), 'rb').read(), 'text/html; charset=utf-8')
            if u.path == '/api/saves':
                return self.send(200, {'saves': A.listar_saves(), 'atual': A.save_path})
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
            if u.path == '/api/aovivo':
                return self.send(200, {**A.aovivo.estado(A.names), 'meu': A.tid()})
            if u.path == '/api/estado':
                with LOCK:
                    return self.send(200, A.view())
            if u.path.startswith('/foto/') and u.path.endswith('.png'):
                try:
                    pid = int(os.path.basename(u.path)[:-4])
                except ValueError:
                    return self.send(404, {'erro': 'id'})
                b = foto_jogador(pid)
                return self.send(200, b, 'image/png') if b else self.send(404, {'erro': 'sem foto'})
            if u.path.startswith('/retro/') and u.path.endswith('.png'):
                with LOCK:
                    st = A.state or {}
                    ano = int(os.path.basename(u.path)[:-4])
                    s_ = next((x for x in retro.resumo(st, A.tid(), A.names, set(A.rivais_ids())) if x['ano'] == ano), None)
                if not s_:
                    return self.send(404, {'erro': 'temporada não encontrada'})
                from PIL import Image as _I
                eb = A.escudo_png()
                png = retro.capa(s_, A.clube(), _I.open(io.BytesIO(eb)) if eb else None, A.cores_time(),
                                 CFG.get('tecnico_nome') or 'Técnico')
                return self.send(200, png, 'image/png')
            if u.path.startswith('/tecnico/cena/'):
                humor = os.path.basename(unquote(u.path))[:-4]
                b = A.cena_jpg(humor)
                return self.send(200, b, 'image/jpeg') if b else self.send(404, {'erro': 'sem cena'})
            if u.path.startswith('/tecnico/'):
                nome = os.path.basename(unquote(u.path[9:]))
                p = os.path.join(DATA, 'tecnico', nome)
                if os.path.exists(p) and nome.lower().endswith('.png'):
                    return self.send(200, open(p, 'rb').read(), 'image/png')
                return self.send(404, {'erro': 'sem imagem'})
            if u.path == '/escudo.png':
                b = A.escudo_png()
                return self.send(200, b, 'image/png') if b else self.send(404, {'erro': 'sem escudo'})
            if u.path.startswith('/logo/'):
                nome = unquote(u.path[6:])
                if nome.lower().endswith('.png'):
                    nome = nome[:-4]
                p = A.logos.path(nome)
                if os.path.exists(p):
                    return self.send(200, open(p, 'rb').read(), 'image/png')
                return self.send(404, {'erro': 'logo'})
            if u.path == '/api/estudio':
                fam = q.get('familia') or next(iter(kits.FAMILIAS))
                variant, fname, _ = next(v for v in kits.VARIANTS if v[2] == fam)
                A.sync_estudio()
                pal = estudio.paleta(kits.base_image(APP_DIR, variant, fname))
                return self.send(200, {'paleta': pal, 'cfg': (A.state or {}).get('estudio', {}).get(fam),
                                       'presets': estudio.PRESETS, 'familias': kits.FAMILIAS})
            if u.path == '/api/estudio/previa':
                fam = q.get('familia') or next(iter(kits.FAMILIAS))
                variant, fname, _ = next(v for v in kits.VARIANTS if v[2] == fam)
                A.sync_estudio()
                cfg = json.loads(q['cfg']) if q.get('cfg') else None
                with LOCK:
                    cs = json.loads(json.dumps([c for c in (A.state or {}).get('contratos', [])
                                                if c['status'] in ('ativo', 'assinado')]))
                img = kits.compose(APP_DIR, variant, fname, fam, cs, A.logos.load, estudio_cfg=cfg)
                out = io.BytesIO()
                kits.preview(img, int(q.get('w', 640))).save(out, 'JPEG', quality=88)
                return self.send(200, out.getvalue(), 'image/jpeg')
            if u.path in ('/api/numero', '/api/numero/previa'):
                fam = q.get('familia') or next(iter(kits.FAMILIAS))
                variant, fname, _ = next(v for v in kits.VARIANTS if v[2] == fam)
                kd = (A.time or {}).get('pasta') or ''
                bd = kits.BASE['dir'] or os.path.join(APP_DIR, 'data', 'kits_base')
                nome = numeros.costas(kd, variant) if kd else None
                if not nome:
                    if u.path == '/api/numero':
                        return self.send(200, {'tem': False})
                    return self.send(404, {'erro': 'sem textura de número'})
                img = numeros._ler(numeros.original(kd, bd, variant, nome))
                orig = numeros.cor_dominante(img)
                cfg = json.loads(q['cfg']) if q.get('cfg') else (A.state or {}).get('estudio', {}).get(fam)
                cfg = dict(cfg or {}, ativo=True)
                pal = estudio.paleta(kits.base_estudio(APP_DIR, variant, fname, cfg))
                camisa = pal[0]['cor'] if pal else '#333333'
                cor = q.get('cor') or cfg.get('cor_numero') or orig
                if u.path == '/api/numero':
                    c = numeros.contraste(cor, camisa)
                    return self.send(200, {'tem': True, 'original': orig, 'atual': cor, 'camisa': camisa,
                                           'contraste': float(c), 'aviso': bool(c < 2.0), 'sugestao': numeros.sugestao(camisa)})
                if cor.lower() != (orig or '').lower():
                    img = numeros.recolorir(img, cor)
                out = io.BytesIO()
                numeros.dez(img, camisa, int(q.get('h', 110))).save(out, 'PNG')
                return self.send(200, out.getvalue(), 'image/png')
            if u.path == '/api/preview':
                fam = q.get('familia') or next(iter(kits.FAMILIAS))
                variant, fname, _ = next(v for v in kits.VARIANTS if v[2] == fam)
                with LOCK:
                    cs = json.loads(json.dumps([c for c in (A.state or {}).get('contratos', [])
                                                if c['status'] in ('ativo', 'assinado')]))
                if q.get('cand'):
                    cand = json.loads(q['cand'])
                    cs = [c for c in cs if c['slot'] != cand['slot'] and c.get('id') != cand.get('id')] + [cand]
                img = kits.compose(APP_DIR, variant, fname, fam, cs, A.logos.load)
                out = io.BytesIO()
                kits.preview(img, int(q.get('w', 520))).save(out, 'JPEG', quality=88)
                return self.send(200, out.getvalue(), 'image/jpeg')
            if u.path == '/api/time/revisao':
                t = A.time
                if not t:
                    return self.send(200, {'familias': {}})
                return self.send(200, {'familias': t['familias'], 'prep': A.times.prep.get(t['id']),
                                       'itens': {f: A.times.itens_revisao(t, f) for f in t['familias']},
                                       'preparado': bool(t.get('preparado')), 'nome': t['nome'],
                                       'legado': bool(t.get('legado'))})
            if u.path == '/api/time/imagem':
                # textura inteira (1024px): 'original' com as caixas ou 'limpa' (base do app)
                t = A.time
                fam = q.get('familia') or next(iter(t['familias']))
                variant, fname, _ = A.times.principal(t, fam)
                if q.get('tipo') == 'limpa':
                    from core import ftex
                    p = kits.base_path(APP_DIR, variant, fname)
                    if not os.path.exists(p):
                        return self.send(404, {'erro': 'ainda não limpo'})
                    img = ftex.read(p).convert('RGB').resize((1024, 1024))
                else:
                    p = os.path.join(A.times.dir(t['id']), f'revisao_{fam}.jpg')
                    if not os.path.exists(p):
                        return self.send(404, {'erro': 'ainda não detectado'})
                    img = __import__('PIL.Image', fromlist=['Image']).open(p)
                out = io.BytesIO()
                img.save(out, 'JPEG', quality=86)
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
        if u.path == '/api/save/escolher':
            caminho = body.get('caminho', '')
            if not os.path.exists(caminho):
                return self.send(400, {'erro': 'Esse save não existe mais.'})
            with LOCK:
                A.persist()
                CFG['save_escolhido'] = caminho
                CFG['save_escolhido_em'] = time.time()
                jsave(os.path.join(DATA, 'config.json'), CFG)
                A.save_path = None; A.save_mtime = None; A.state = None; A.state_path = None
                A.engine = None; A.career = None
            log('save escolhido:', caminho)
            return self.send(200, {'ok': True})
        if u.path.startswith('/api/time/'):
            try:
                with LOCK:
                    t = A.time
                    if not t:
                        raise ValueError('O app ainda está lendo o save.')
                    if A.times.prep.get(t['id'], {}).get('rodando'):
                        raise ValueError('A preparação dos uniformes ainda está rodando. Aguarde.')
                    if t.get('legado'):
                        raise ValueError('Os uniformes deste clube foram preparados à mão numa versão anterior do app.')
                    fam = body.get('familia')
                    d = (t.get('deteccao') or {}).get(fam) if fam else None
                    if u.path == '/api/time/marcar':
                        fora = set(d.get('desmarcados', []))
                        if body.get('chave', '').startswith('extra:'):
                            i = int(body['chave'].split(':')[1])
                            if not body.get('marcado') and 0 <= i < len(d['extras']):
                                d['extras'].pop(i)
                        elif body.get('marcado'):
                            fora.discard(body['chave'])
                        else:
                            fora.add(body['chave'])
                        d['desmarcados'] = sorted(fora)
                    elif u.path == '/api/time/extra':
                        c = [int(max(0, min(2048, v))) for v in body['caixa']]
                        x0, x1 = sorted((c[0], c[2])); y0, y1 = sorted((c[1], c[3]))
                        if x1 - x0 < 6 or y1 - y0 < 6:
                            raise ValueError('Área muito pequena.')
                        d.setdefault('extras', []).append([x0, y0, x1, y1])
                    elif u.path == '/api/time/limpar':
                        A.preparar_time()
                    elif u.path == '/api/time/detectar':
                        A.preparar_time(so_detectar=True)
                    else:
                        return self.send(404, {'erro': 'não encontrado'})
                    A.times.salvar(t)
                return self.send(200, {'ok': True})
            except ValueError as e:
                return self.send(400, {'erro': str(e)})
            except Exception as e:
                log(traceback.format_exc())
                return self.send(500, {'erro': str(e)})
        if u.path == '/api/moeda':
            cod = body.get('cod')
            if cod not in sim.MOEDAS:
                return self.send(400, {'erro': 'moeda desconhecida'})
            sim.MOEDA['cod'] = cod
            CFG['moeda'] = cod
            jsave(os.path.join(DATA, 'config.json'), CFG)
            return self.send(200, {'ok': True})
        if u.path == '/api/config/detectar':
            return self.send(200, {'jogo': detectar_jogo(), 'saves': detectar_saves()})
        if u.path == '/api/config/escolher':
            try:
                import tkinter as tk
                from tkinter import filedialog
                r = tk.Tk(); r.withdraw(); r.attributes('-topmost', True)
                p = filedialog.askdirectory(title=body.get('titulo') or 'Escolha a pasta',
                                            initialdir=body.get('inicial') or None)
                r.destroy()
            except Exception as e:
                return self.send(400, {'erro': f'Não consegui abrir a janela de pastas ({e}). Cole o caminho no campo.'})
            return self.send(200, {'pasta': os.path.normpath(p) if p else ''})
        if u.path == '/api/config':
            jogo = (body.get('pasta_jogo') or '').strip().strip('"')
            saves = (body.get('pasta_saves') or '').strip().strip('"')
            logos = (body.get('pasta_logos') or '').strip().strip('"')
            if not _jogo_ok(jogo):
                return self.send(400, {'erro': 'Não achei o PES2021.exe nessa pasta do jogo.'})
            if not _saves_em(saves):
                return self.send(400, {'erro': 'Não achei saves do Master League nessa pasta (ela deve ter subpastas com "save\\ML...").'})
            mudou_saves = saves != CFG.get('pasta_saves')
            CFG.update(pasta_jogo=jogo, pasta_saves=saves, configurado=True)
            if logos:
                CFG['pasta_logos'] = logos
            nome = (body.get('tecnico_nome') or '').strip()[:40]
            if nome:
                CFG['tecnico_nome'] = nome
            if mudou_saves:
                CFG.pop('save_escolhido', None)
            jsave(os.path.join(DATA, 'config.json'), CFG)
            self.send(200, {'ok': True})
            reiniciar()
            return
        if u.path == '/api/logos/atualizar':
            try:
                novos, atual = atualizar_logos()
            except Exception as e:
                log(traceback.format_exc())
                return self.send(500, {'erro': f'Não consegui ler a pasta de logos: {e}'})
            with LOCK:
                nomes = list(((A.state or {}).get('empresas') or {}).keys())
            return self.send(200, {'novas': [n['nome'] for n in novos], 'atualizadas': atual,
                                   'sem_imagem': A.logos.sem_imagem(nomes),
                                   'pasta': A.logos.logos_dir, 'pasta_existe': os.path.isdir(A.logos.logos_dir)})
        if u.path == '/api/logos/enviar':
            import base64
            nome = (body.get('nome') or '').strip()
            dados = body.get('dados') or ''
            if not nome or not dados:
                return self.send(400, {'erro': 'Faltou a empresa ou a imagem.'})
            try:
                raw = base64.b64decode(dados.split(',', 1)[-1])
                with LOGOS_LOCK:
                    A.logos.definir(nome, raw)
            except Exception as e:
                log(traceback.format_exc())
                return self.send(400, {'erro': f'Não consegui usar essa imagem ({e}).'})
            return self.send(200, {'ok': True})
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
                    vis = body.get('visual') or {}
                    for k in ('escala', 'inclinacao', 'dx', 'dy'):
                        if k in vis:
                            c[k] = float(vis[k])
                    if vis.get('ajustes'):
                        c['ajustes'] = vis['ajustes']
                    if vis.get('cores'):
                        c['cores'].update(vis['cores'])
                    A.aplicar_creditos()
                    A.mundo_processar()
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
                    fams = list(kits.FAMILIAS) if body.get('todos') else [body.get('familia')]
                    for c in A.state['contratos']:
                        if c['id'] == int(body['id']):
                            base = kits.ajuste(c, body.get('familia') or next(iter(kits.FAMILIAS)))
                            for k in ('escala', 'inclinacao', 'dx', 'dy'):
                                if k in body:
                                    base[k] = float(body[k])
                            for f in fams:
                                if f:
                                    c.setdefault('ajustes', {})[f] = dict(base)
                            if body.get('cores'):
                                c['cores'].update(body['cores'])
                    A.persist(); return self.send(200, {'ok': True})
                if u.path == '/api/estudio/salvar':
                    cfg = body.get('cfg') or {}
                    cfg['ativo'] = True
                    A.state.setdefault('estudio', {})[body['familia']] = cfg
                    A.sync_estudio(); A.persist()
                    return self.send(200, {'ok': True})
                if u.path == '/api/estudio/remover':
                    (A.state.get('estudio') or {}).pop(body['familia'], None)
                    A.sync_estudio(); A.persist()
                    return self.send(200, {'ok': True})
                if u.path == '/api/tecnico/foto':
                    import base64
                    dados = base64.b64decode(body['dados'].split(',')[-1])
                    humor = body.get('humor') if body.get('humor') in tecnico.HUMORES else 'neutro'
                    nome = tecnico.salvar(os.path.join(DATA, 'tecnico'), humor, dados)
                    return self.send(200, {'ok': True, 'nome': nome})
                if u.path == '/api/tecnico/apagar':
                    tecnico.apagar(os.path.join(DATA, 'tecnico'), body['nome'])
                    return self.send(200, {'ok': True})
                if u.path == '/api/tecnico/nova_carreira':
                    nome = (body.get('nome') or '').strip()[:40]
                    if nome:
                        CFG['tecnico_nome'] = nome
                        jsave(os.path.join(DATA, 'config.json'), CFG)
                        if A.state is not None:
                            A.state['cfg_tecnico'] = nome
                    chave = getattr(A, 'chave_tec', None)
                    st = A.state or {}
                    tecnico_carreira.zerar(DATA, chave, st.get('data'))
                    if chave and st:
                        c, _ = tecnico_carreira.registrar(DATA, chave, st, A.clube(), None)
                        st['prestigio_tecnico'] = c['prestigio']
                        A.persist()
                    return self.send(200, {'ok': True})
                if u.path == '/api/tecnico/nome':
                    CFG['tecnico_nome'] = (body.get('nome') or '').strip()[:40] or 'Técnico'
                    jsave(os.path.join(DATA, 'config.json'), CFG)
                    A.state['cfg_tecnico'] = CFG['tecnico_nome']
                    return self.send(200, {'ok': True})
                if u.path == '/api/ingame/atualizar':
                    A.atualizar_ingame(forcar=True)
                    return self.send(200, {'ok': True, 'ingame': (A.state or {}).get('ingame')})
                if u.path == '/api/tecnico/cena_zip':
                    import base64
                    dados = base64.b64decode(body['dados'].split(',', 1)[-1])
                    return self.send(200, {'ok': True, 'humores': cena.importar_zip(DATA, dados)})
                if u.path == '/api/marketing/responder':
                    if A.state is None:
                        return self.send(400, {'erro': 'O app ainda não leu o save da carreira.'})
                    try:
                        hoje = sim.s2d(A.state['data']) if A.state.get('data') else None
                        mu = mundo.Mundo(A.state, A.clube(), A.tid())
                        A.marketing().responder(body['id'], bool(body.get('aprovar')), mu, hoje)
                        A.sync_estudio(); A.persist()
                    except ValueError as e:
                        return self.send(400, {'erro': str(e)})
                    return self.send(200, {'ok': True})
                if u.path in ('/api/diretor/pedido', '/api/diretor/responder'):
                    car = A.career
                    if car is None or car.fin_off is None:
                        return self.send(400, {'erro': 'O app ainda não leu o save da carreira.'})
                    d = A.diretor()
                    try:
                        if u.path == '/api/diretor/pedido':
                            p = d.pedir(body['tipo'], int(body['valor']))
                        else:
                            p = d.responder(bool(body.get('aceitar')))
                        if p['status'] == 'aceito':
                            valor = (p.get('acordo') or {}).get('valor', p['valor'])
                            if p['tipo'] == 'mover':
                                novo = car.redistribuir(valor)
                                car.write(os.path.join(DATA, 'backups_save'), log)
                                A.save_mtime = car.mtime
                                A.state['dinheiro'] = car.money()
                                A.state.setdefault('redistrib', []).append({'data': A.state.get('data'), 'valor': valor, **novo})
                                A.status['aviso'] = ('Remanejamento gravado no save. No jogo, volte ao menu principal e carregue a '
                                                     'carreira de novo (sem salvar antes).')
                            else:
                                A.state.setdefault('debitos', []).append({'data': A.state.get('data'), 'valor': -valor,
                                                                          'motivo': 'verba extra da diretoria', 'status': 'pendente',
                                                                          'origem': 'diretor'})
                                A.aplicar_creditos()
                    except ValueError as e:
                        A.persist()
                        return self.send(400, {'erro': str(e)})
                    A.persist()
                    return self.send(200, {'ok': True, 'pedido': p})
                if u.path == '/api/dirigentes/nome':
                    ed = A.state.setdefault('dirigentes_editados', {})
                    nome = (body.get('nome') or '').strip()[:60]
                    if body.get('cargo') not in ('presidente', 'diretor'):
                        return self.send(400, {'erro': 'Cargo inválido.'})
                    if nome:
                        ed[body['cargo']] = nome
                    else:
                        ed.pop(body['cargo'], None)
                    A.persist()
                    return self.send(200, {'ok': True})
                if u.path == '/api/orcamento/redistribuir':
                    car = A.career
                    if car is None or car.fin_off is None:
                        return self.send(400, {'erro': 'O app ainda não leu o save da carreira.'})
                    valor = int(body['valor'])
                    try:
                        novo = car.redistribuir(valor)
                        car.write(os.path.join(DATA, 'backups_save'), log)
                    except ValueError as e:
                        return self.send(400, {'erro': str(e)})
                    A.save_mtime = car.mtime
                    A.state['dinheiro'] = car.money()
                    A.state.setdefault('redistrib', []).append({'data': A.state.get('data'), 'valor': valor, **novo})
                    A.persist()
                    return self.send(200, {'ok': True, **novo})
                if u.path == '/api/empresa/remover_sem_imagem':
                    st = A.state
                    rem = st.setdefault('empresas_removidas', [])
                    vig = {c['empresa'] for c in st.get('contratos', []) if c['status'] in ('ativo', 'assinado')}
                    tirar = [n for n in A.logos.sem_imagem(list(st.get('empresas', {}))) if n not in vig]
                    for nome in tirar:
                        if nome not in rem:
                            rem.append(nome)
                        st['empresas'].pop(nome, None)
                        for o in st.get('ofertas', []):
                            if o.get('empresa') == nome and o['status'] in ('aberta', 'aguardando'):
                                o['status'] = 'cancelada'
                    A.persist()
                    return self.send(200, {'removidas': tirar, 'mantidas_por_contrato': sorted(
                        n for n in A.logos.sem_imagem(list(st.get('empresas', {}))) if n in vig)})
                if u.path in ('/api/empresa/remover', '/api/empresa/restaurar'):
                    st = A.state
                    nome = body['nome']
                    rem = st.setdefault('empresas_removidas', [])
                    if u.path.endswith('remover'):
                        if any(c['empresa'] == nome and c['status'] in ('ativo', 'assinado') for c in st.get('contratos', [])):
                            return self.send(400, {'erro': 'Essa empresa tem contrato vigente. Rescinda antes de remover.'})
                        if nome not in rem:
                            rem.append(nome)
                        st.get('empresas', {}).pop(nome, None)
                        for o in st.get('ofertas', []):
                            if o.get('empresa') == nome and o['status'] in ('aberta', 'aguardando'):
                                o['status'] = 'cancelada'
                    else:
                        if nome in rem:
                            rem.remove(nome)
                        A.engine.sync_empresas([(nome, '')])
                    A.persist()
                    return self.send(200, {'ok': True})
                if u.path == '/api/reportagem':
                    st = A.state or {}
                    linhas = (st.get('tabela') or {}).get('linhas') or []
                    meu = next((l for l in linhas if l.get('id') == A.tid()), None)
                    ctx = {'clube': A.clube(), 'tecnico': CFG.get('tecnico_nome') or 'Técnico',
                           'pos': meu['pos'] if meu else None, 'torcida': (st.get('mundo') or {}).get('torcida', 50),
                           'jogador': (st.get('elenco_nomes') or ['o camisa 10'])[0]}
                    return self.send(200, imprensa.reportagem(body.get('noticia') or {}, ctx))
                if u.path == '/api/rede/postar':
                    mu = mundo.Mundo(A.state, A.clube(), A.tid())
                    ctx = mu.contexto_tecnico()
                    i = int(body['i'])
                    n_ctx = len(mundo.POSTS_TECNICO[ctx])
                    bom = mu.post_tecnico(ctx if i < n_ctx else 'geral', i if i < n_ctx else i - n_ctx,
                                          A.state.get('data') or '2026-01-01')
                    A.persist()
                    return self.send(200, {'ok': True, 'bom': bom})
                if u.path == '/api/coletiva/responder':
                    mu = mundo.Mundo(A.state, A.clube(), A.tid())
                    tom = gestao.Gestao(A.state, A.clube(), A.tid()).responder(
                        body['id'], int(body['pergunta']), int(body['resposta']), mu)
                    A.persist()
                    return self.send(200, {'ok': True, 'tom': tom})
                if u.path == '/api/diretoria/sondagem':
                    mu = mundo.Mundo(A.state, A.clube(), A.tid())
                    diretoria.responder_sondagem(A.state, eng, mu, bool(body.get('aceitar')))
                    A.persist(); return self.send(200, {'ok': True})
                if u.path == '/api/diretoria/continuar':
                    diretoria.continuar(A.state, mundo.Mundo(A.state, A.clube(), A.tid()))
                    A.persist(); return self.send(200, {'ok': True})
                if u.path == '/api/diretoria/demissao_ativa':
                    diretoria._e(A.state)['demissao_ativa'] = bool(body.get('ativo'))
                    A.persist(); return self.send(200, {'ok': True})
                if u.path == '/api/estrutura/investir':
                    if not A.state.get('data'):
                        raise ValueError('O app ainda não leu a data da carreira.')
                    o = estrutura.investir(A.state, body.get('depto'), sim.s2d(A.state['data']))
                    A.aplicar_creditos(); A.persist()
                    return self.send(200, {'ok': True, 'obra': o})
                if u.path == '/api/medico/tratar':
                    medico.tratar(A.state, body.get('id'), sim.s2d(A.state['data']))
                    A.aplicar_creditos(); A.persist(); return self.send(200, {'ok': True})
                if u.path == '/api/gramado/investir':
                    if not A.state.get('data'):
                        raise ValueError('O app ainda não leu a data da carreira.')
                    r_ = estrutura.investir_gramado(A.state, body.get('acao'), sim.s2d(A.state['data']))
                    A.aplicar_creditos(); A.persist()
                    threading.Thread(target=A.atualizar_ingame, kwargs={'forcar': True}, daemon=True).start()
                    return self.send(200, {'ok': True, **{k: r_[k] for k in ('nome', 'custo')}})
                if u.path == '/api/empresa/global':
                    e_ = eng.s['empresas'].get(body.get('nome'))
                    if not e_:
                        raise ValueError('Empresa não encontrada.')
                    e_['global'] = bool(body.get('global'))
                    A.persist(); return self.send(200, {'ok': True})
                if u.path == '/api/vestiario/capitao':
                    vestiario.definir_capitao(A.state, body.get('nome') or None, A.state.get('data'))
                    A.persist(); return self.send(200, {'ok': True})
                if u.path == '/api/rivais':
                    A.state.setdefault('gestao', {})['rivais_manual'] = [int(x) for x in body.get('ids') or []]
                    A.persist(); return self.send(200, {'ok': True})
                if u.path == '/api/escalacao':
                    mudou = A.escalacao_salvar(body.get('ordem') or [])
                    A.persist(); return self.send(200, {'ok': True, 'mudou': mudou})
                if u.path == '/api/escalacao/auto':
                    CFG['escalacao_auto'] = bool(body.get('auto'))
                    jsave(os.path.join(DATA, 'config.json'), CFG)
                    if CFG['escalacao_auto'] and A.career is not None:
                        A.escalacao_processar(A.career)
                    A.persist(); return self.send(200, {'ok': True})
                if u.path == '/api/prancheta':
                    g = gestao.Gestao(A.state, A.clube(), A.tid())
                    pos = {str(k): [round(float(v[0]), 1), round(float(v[1]), 1)] for k, v in (body.get('pos') or {}).items()}
                    g.g['prancheta'] = pos
                    A.persist()
                    return self.send(200, {'ok': True})
                if u.path == '/api/mensagens/lidas':
                    for m in A.state['mensagens']:
                        m['lida'] = True
                    A.persist(); return self.send(200, {'ok': True})
                if u.path == '/api/aviso/ok':
                    A.status['aviso'] = None; return self.send(200, {'ok': True})
                if u.path == '/api/kits/testar':
                    # grava só o uniforme escolhido com os contratos ativos + assinados, para conferir no jogo
                    fam = body.get('familia') or next(iter(kits.FAMILIAS))
                    variant, fname, _ = next(v for v in kits.VARIANTS if v[2] == fam)
                    cs = json.loads(json.dumps([c for c in A.state.get('contratos', []) if c['status'] in ('ativo', 'assinado')]))
                    if body.get('cand'):
                        cand = body['cand']
                        cs = [c for c in cs if c['slot'] != cand['slot']] + [cand]
                    img = kits.compose(APP_DIR, variant, fname, fam, cs, A.logos.load)
                    from core import ftex
                    ftex.write(img, kits.base_path(APP_DIR, variant, fname),
                               os.path.join(A.time['pasta'], variant, fname + '.ftex'))
                    A.state['kits_aplicados'] = 'teste'
                    A.persist()
                    return self.send(200, {'ok': True, 'uniforme': variant})
                if u.path == '/api/kits/aplicar':
                    A.aplicar_kits(); return self.send(200, {'ok': True})
                if u.path == '/api/contrato/rescindir':
                    multa = eng.rescindir(body['id'])
                    A.aplicar_creditos(); A.mundo_processar(); A.persist()
                    return self.send(200, {'ok': True, 'multa': multa})
                if u.path == '/api/empresa':
                    e = A.state['empresas'].get(body.get('nome'))
                    if not e:
                        raise ValueError('Essa empresa não está na lista.')
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
ARQUIVOS_CODIGO = ('app.py', 'versao.txt', 'Abrir App.bat', 'Instalar.bat', 'LEIA-ME.txt', 'core/', 'web/', 'recursos/')


def _vtuple(v):
    try:
        return tuple(int(x) for x in v.split('.'))
    except ValueError:
        return (0,)


def _ultimo_commit():
    """Pergunta ao GitHub qual é o commit mais novo (sem o cache de alguns minutos dos arquivos 'raw')."""
    import urllib.request
    req = urllib.request.Request(f'https://api.github.com/repos/{REPO}/commits/main',
                                 headers={'Accept': 'application/vnd.github.sha', 'User-Agent': 'CarreiraPES21'})
    with urllib.request.urlopen(req, timeout=8) as r:
        return r.read().decode().strip()


def checar_atualizacao():
    import urllib.request
    sha = _ultimo_commit()
    with urllib.request.urlopen(f'https://raw.githubusercontent.com/{REPO}/{sha}/versao.txt', timeout=8) as r:
        nova = r.read().decode().strip()
    return {'atual': VERSAO, 'nova': nova, 'tem': _vtuple(nova) > _vtuple(VERSAO), 'sha': sha}


def atualizar():
    """Baixa a versão nova do GitHub, guarda a atual em data/versoes e troca só os arquivos de código."""
    import urllib.request, zipfile, shutil
    url = f'https://github.com/{REPO}/archive/{_ultimo_commit()}.zip'
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
    tec = os.path.join(DATA, 'tecnico')
    if not os.path.isdir(tec):
        os.makedirs(tec, exist_ok=True)
        open(os.path.join(tec, 'LEIA-ME.txt'), 'w', encoding='utf-8').write(
            'Coloque aqui fotos do seu rosto em PNG com estes nomes:\n'
            '  feliz.png    - depois de vitória ou resposta animada na coletiva\n'
            '  neutro.png   - empate ou resposta comedida\n'
            '  irritado.png - derrota ou resposta dura\n'
            'O app mostra a expressão certa na sala de imprensa.\n')
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
    try:
        savedata.limpar_backups(os.path.join(DATA, 'backups_save'))
    except Exception:
        log(traceback.format_exc())
    # a pasta de logos é lida pela verificação automática logo em seguida (num PC novo isso leva um tempo,
    # e a janela do app não precisa esperar)
    threading.Thread(target=watcher, daemon=True).start()
    threading.Thread(target=logos_watcher, daemon=True).start()
    class Servidor(ThreadingHTTPServer):
        daemon_threads = True

        def handle_error(self, request, client_address):
            # conexões que a janela do app fecha no meio não são erro; o resto vai para o log
            exc = sys.exc_info()[1]
            if isinstance(exc, (ConnectionError, OSError)):
                return
            log(traceback.format_exc())

    srv = Servidor(('127.0.0.1', PORT), H)
    A.server = srv
    print('\n  App de Carreira rodando em', url, '\n')
    if '--sem-navegador' not in sys.argv and '--reiniciar' not in sys.argv:
        threading.Timer(0.8, lambda: abrir_janela(url)).start()
    srv.serve_forever()


if __name__ == '__main__':
    main()
