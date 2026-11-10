"""Lê e grava as informações da carreira (Master League) dentro do save decriptado."""
import os, re, struct, shutil, time, datetime as dt
import numpy as np
from . import pescrypt

UNIT = 100  # o jogo guarda valores em unidades de €100


def find_finance_block(data: bytes):
    """Procura o bloco de finanças do clube do usuário (orçamento duplicado + salário + receitas)."""
    a = np.frombuffer(data[:len(data) // 4 * 4], '<i4')
    n = len(a) - 40
    i = np.arange(n)
    m = ((a[i] > 0) & (a[i] == a[i + 4]) & (a[i + 1] == 0) & (a[i + 2] == 0) & (a[i + 3] == 0)
         & (a[i + 6] == 0) & (a[i + 7] > 0) & (a[i + 7] < 10 ** 7) & (a[i] < 10 ** 8)
         & (a[i + 5] >= 0) & (a[i + 8] == 0))
    hits = np.where(m)[0]
    return int(hits[0]) * 4 if len(hits) else None


# posições dentro do bloco de finanças (a partir do orçamento de transferências)
FIN = {
    'orc_transf': 0x00, 'orc_transf_2': 0x10, 'orc_salario': 0x1c,
    'rec_transmissao': 0x2c, 'rec_patrocinio': 0x30, 'rec_socios': 0x34,
    'rec_bilheteria': 0x4c,
}


def find_results(data: bytes, team_id: int):
    """Registros de partidas do clube: blocos de 40 bytes com torneio, mandante, visitante e gols."""
    out = []
    code_lo, code_hi = team_id << 14, (team_id + 1) << 14
    a = np.frombuffer(data[:len(data) // 4 * 4], '<u4')
    cand = np.where((a >= code_lo) & (a < code_hi))[0]
    seen = set()
    for w in cand:
        for side in (1, 2):  # o código do clube pode estar como mandante (+4) ou visitante (+8)
            start = (w - side) * 4
            if start < 0 or start in seen:
                continue
            tour, home, away = struct.unpack_from('<3I', data, start)
            if not (0 < tour < 70000):
                continue
            hid, aid = home >> 14, away >> 14
            if not (0 < hid < 20000 and 0 < aid < 20000) or hid == aid:
                continue
            if team_id not in (hid, aid):
                continue
            hg = struct.unpack_from('<I', data, start + 0x10)[0]
            ag = struct.unpack_from('<I', data, start + 0x1c)[0]
            if hg > 20 or ag > 20:
                continue
            # registros vizinhos também precisam parecer registros (40 bytes) – evita falsos positivos
            seen.add(start)
            out.append({'offset': start, 'torneio': tour, 'mandante': hid, 'visitante': aid,
                        'gols_mandante': hg, 'gols_visitante': ag})
    # mantém só as sequências de registros contíguos (passo de 40 bytes)
    offs = sorted(r['offset'] for r in out)
    good = set()
    for o in offs:
        if o + 40 in offs or o - 40 in offs:
            good.add(o)
    res = [r for r in sorted(out, key=lambda r: r['offset']) if r['offset'] in good]
    return res


DATE_RE = re.compile(r'(\d{1,2})/(\d{1,2})/(\d{4})')


def team_index(data: bytes, team_id: int):
    """Número do clube na tabela de times da carreira (vem junto do id nos códigos id<<14 | número)."""
    a = np.frombuffer(data[:len(data) // 4 * 4], '<u4')
    sel = a[(a >> 14) == team_id] & 0x3fff
    sel = sel[sel > 0]
    if not len(sel):
        return None
    v, c = np.unique(sel, return_counts=True)
    return int(v[np.argmax(c)])


ELENCO_PASSO = 0x690


def _elenco_base(data: bytes):
    """Início da tabela de elencos: registros (id do jogador, número sequencial) de 8 bytes."""
    for o in range(0, min(len(data), 0x20000) - 64, 8):
        if (struct.unpack_from('<H', data, o + 4)[0] == 0 and struct.unpack_from('<H', data, o + 12)[0] == 1
                and struct.unpack_from('<H', data, o + 20)[0] == 2 and struct.unpack_from('<H', data, o + 28)[0] == 3
                and struct.unpack_from('<I', data, o + 8)[0] > 0):
            return o
    return None


def elenco(data: bytes, team_index: int):
    """Ids dos jogadores do clube (até 40 vagas por clube)."""
    base = _elenco_base(data)
    if base is None or team_index is None:
        return []
    o = base + team_index * ELENCO_PASSO
    out = []
    for j in range(1, 40):
        pid, idx = struct.unpack_from('<IH', data, o + 8 * j)
        if idx == 0xffff:
            break
        pid &= 0x3fffffff
        if pid:
            out.append(pid)
    return out


_NOMES = {}


def nomes_jogadores(edit_path):
    """Nomes dos jogadores do arquivo EDIT do save (registros de 312 bytes: id no início, nome em +0x36)."""
    try:
        m = os.path.getmtime(edit_path)
    except OSError:
        return {}
    if _NOMES.get('chave') == (edit_path, m):
        return _NOMES['nomes']
    d = bytes(pescrypt.decrypt(open(edit_path, 'rb').read()).data)
    R = 312
    melhor = (0, 0)
    for ini in range(R):          # acha o alinhamento dos registros
        ok = 0
        for k in range(200, 260):
            o = ini + k * R
            nm = d[o + 0x36:o + 0x36 + 0x3e].split(b'\0')[0]
            if 2 <= len(nm) <= 60 and nm[:1].isalpha() and 0 < struct.unpack_from('<I', d, o)[0] < 2_000_000:
                ok += 1
        if ok > melhor[0]:
            melhor = (ok, ini)
    nomes = {}
    o = melhor[1]
    while o + R <= len(d):
        pid = struct.unpack_from('<I', d, o)[0]
        nm = d[o + 0x36:o + 0x36 + 0x3e].split(b'\0')[0]
        if pid and nm and pid not in nomes and nm[:1].isalpha():
            try:
                nomes[pid] = {'nome': nm.decode('utf-8').strip(), 'altura': d[o + 0x0a]}
            except UnicodeDecodeError:
                pass
        o += R
    _NOMES.update(chave=(edit_path, m), nomes=nomes)
    return nomes


def clube_do_texto(club_line):
    return club_line.split('/')[0].strip()


class Career:
    def __init__(self, path, team_id=None, resolver=None):
        self.path = path
        self.team_id = team_id
        self.mtime = os.path.getmtime(path)
        raw = open(path, 'rb').read()
        self.raw_size = len(raw)
        self.sf = pescrypt.decrypt(raw)
        d = bytes(self.sf.data)
        desc = '\n'.join(self.sf.subtitle)
        m = DATE_RE.search(desc)
        self.date = dt.date(int(m.group(3)), int(m.group(2)), int(m.group(1))) if m else None
        self.slot_name = self.sf.subtitle[0] if self.sf.subtitle else ''
        lines = desc.split('\n')
        self.club_line = lines[1] if len(lines) > 1 else ''
        self.clube = clube_do_texto(self.club_line)
        if resolver:
            team_id = resolver(self.clube, d) or team_id
        self.team_id = team_id
        self.fin_off = find_finance_block(d)
        self.results = find_results(d, team_id)

    def money(self):
        if self.fin_off is None:
            return {}
        return {k: struct.unpack_from('<i', self.sf.data, self.fin_off + o)[0] * UNIT for k, o in FIN.items()}

    def zerar_patrocinio(self):
        """Tira do save a receita de patrocínio que veio com a carreira (e o mesmo valor do orçamento)."""
        o = self.fin_off + FIN['rec_patrocinio']
        v = struct.unpack_from('<i', self.sf.data, o)[0]
        if v > 0:
            struct.pack_into('<i', self.sf.data, o, 0)
            # o mesmo valor sai do orçamento, sem deixar o caixa negativo
            for key in ('orc_transf', 'orc_transf_2'):
                ob = self.fin_off + FIN[key]
                b = struct.unpack_from('<i', self.sf.data, ob)[0]
                struct.pack_into('<i', self.sf.data, ob, max(min(b, 0), b - v))
            return v * UNIT
        return 0

    def desfazer_zerar(self, valor, orc_antes):
        struct.pack_into('<i', self.sf.data, self.fin_off + FIN['rec_patrocinio'], valor // UNIT)
        for key in ('orc_transf', 'orc_transf_2'):
            struct.pack_into('<i', self.sf.data, self.fin_off + FIN[key], orc_antes // UNIT)

    def credit_sponsor(self, euros: int):
        """Soma 'euros' na receita de patrocínio e no orçamento de transferências."""
        u = int(round(euros / UNIT))
        for key in ('orc_transf', 'orc_transf_2', 'rec_patrocinio'):
            o = self.fin_off + FIN[key]
            v = struct.unpack_from('<i', self.sf.data, o)[0]
            struct.pack_into('<i', self.sf.data, o, v + u)

    def write(self, backup_dir, log=print):
        """Grava com segurança: backup, confere que o arquivo não mudou, grava, relê e confere."""
        if os.path.getmtime(self.path) != self.mtime:
            raise RuntimeError('O jogo gravou o save de novo enquanto o app trabalhava. Vou tentar de novo.')
        os.makedirs(backup_dir, exist_ok=True)
        # um backup por versão do save (não repete a cada tentativa)
        bk = os.path.join(backup_dir, f'ML_{int(self.mtime)}.bak')
        if not os.path.exists(bk):
            shutil.copy2(self.path, bk)
        new = pescrypt.encrypt(self.sf)
        chk = pescrypt.decrypt(new)
        if bytes(chk.data) != bytes(self.sf.data):
            raise RuntimeError('Falha na conferência do save. Nada foi alterado.')
        pasta, nome = os.path.split(self.path)
        erros = []
        gravou = False
        # jeito 1: arquivo temporário que o OneDrive ignora (~*.tmp) e troca de uma vez
        tmp = os.path.join(pasta, '~' + nome + '.tmp')
        for _ in range(3):
            try:
                with open(tmp, 'wb') as f:
                    f.write(new)
                os.replace(tmp, self.path)
                gravou = True
                break
            except OSError as e:
                erros.append(f'troca: {e}')
                time.sleep(0.7)
        if os.path.exists(tmp):
            try:
                os.remove(tmp)
            except OSError:
                pass
        # jeito 2: escreve por cima do próprio arquivo
        if not gravou:
            for _ in range(3):
                try:
                    with open(self.path, 'r+b') as f:
                        f.seek(0); f.write(new); f.truncate()
                    gravou = True
                    break
                except OSError as e:
                    erros.append(f'por cima: {e}')
                    time.sleep(0.7)
        if not gravou:
            log('falha ao gravar o save:', ' | '.join(erros))
            raise RuntimeError('O Windows não deixou gravar o save agora (' + erros[-1] + '). Vou tentar de novo em instantes.')
        # relê do disco e confere; se algo deu errado, volta o backup
        try:
            ok = bytes(pescrypt.decrypt(open(self.path, 'rb').read()).data) == bytes(self.sf.data)
        except Exception:
            ok = False
        if not ok:
            shutil.copyfile(bk, self.path)
            raise RuntimeError('A gravação do save não conferiu; o backup foi restaurado. Nada mudou.')
        self.mtime = os.path.getmtime(self.path)
        baks = sorted((f for f in os.listdir(backup_dir) if f.startswith('ML_')),
                      key=lambda f: os.path.getmtime(os.path.join(backup_dir, f)))
        for f in baks[:-30]:
            try:
                os.remove(os.path.join(backup_dir, f))
            except OSError:
                pass
        return bk
