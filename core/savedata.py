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


class Career:
    def __init__(self, path, team_id):
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
        self.fin_off = find_finance_block(d)
        self.results = find_results(d, team_id)

    def money(self):
        if self.fin_off is None:
            return {}
        return {k: struct.unpack_from('<i', self.sf.data, self.fin_off + o)[0] * UNIT for k, o in FIN.items()}

    def credit_sponsor(self, euros: int):
        """Soma 'euros' na receita de patrocínio e no orçamento de transferências."""
        u = int(round(euros / UNIT))
        for key in ('orc_transf', 'orc_transf_2', 'rec_patrocinio'):
            o = self.fin_off + FIN[key]
            v = struct.unpack_from('<i', self.sf.data, o)[0]
            struct.pack_into('<i', self.sf.data, o, v + u)

    def write(self, backup_dir):
        """Grava com segurança: backup, confere que o arquivo não mudou, grava, relê e confere."""
        if os.path.getmtime(self.path) != self.mtime:
            raise RuntimeError('O jogo gravou o save de novo enquanto o app trabalhava. Tente outra vez.')
        os.makedirs(backup_dir, exist_ok=True)
        stamp = time.strftime('%Y%m%d_%H%M%S')
        bk = os.path.join(backup_dir, f'ML_{stamp}.bak')
        shutil.copy2(self.path, bk)
        new = pescrypt.encrypt(self.sf)
        # confere a versão nova na memória antes de tocar no save
        chk = pescrypt.decrypt(new)
        if bytes(chk.data) != bytes(self.sf.data):
            raise RuntimeError('Falha na conferência do save. Nada foi alterado.')
        # grava direto por cima do arquivo (sem arquivo temporário na pasta do OneDrive, que atrapalha)
        ultimo_erro = None
        for tentativa in range(5):
            try:
                with open(self.path, 'r+b') as f:
                    f.seek(0); f.write(new); f.truncate()
                    f.flush(); os.fsync(f.fileno())
                ultimo_erro = None
                break
            except OSError as e:
                ultimo_erro = e
                time.sleep(1.0)
        if ultimo_erro:
            raise RuntimeError(f'O Windows não deixou gravar o save agora ({ultimo_erro}). Vou tentar de novo.')
        # relê do disco e confere; se algo deu errado, volta o backup
        try:
            ok = bytes(pescrypt.decrypt(open(self.path, 'rb').read()).data) == bytes(self.sf.data)
        except Exception:
            ok = False
        if not ok:
            shutil.copyfile(bk, self.path)
            raise RuntimeError('A gravação do save não conferiu; o backup foi restaurado. Nada mudou.')
        self.mtime = os.path.getmtime(self.path)
        # limpa backups antigos (mantém os 30 mais recentes)
        baks = sorted(f for f in os.listdir(backup_dir) if f.startswith('ML_'))
        for f in baks[:-30]:
            try:
                os.remove(os.path.join(backup_dir, f))
            except OSError:
                pass
        return bk
