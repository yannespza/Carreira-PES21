"""Confere no save as posições da Cheat Table do xAranaktu (PES-2021-Cheat-Table, v21.1.0).

Na memória do jogo o registro de jogador do Master League tem o id em +0x30. Hipótese: a tabela do clube no save
(registros de 0x170 bytes, id em +4) é o mesmo registro, então campo_no_save = campo_na_memória − 0x2C.

Uso: python3 ferramentas/testar_tabela_ct.py <save.dec ou .pesz> <id1> [id2 ...]
Mostra, para cada id achado, os campos da hipótese. Se nome, clube, fim de contrato e valor de mercado fizerem
sentido para vários jogadores, a hipótese está confirmada."""
import os, struct, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

MEM = {  # nome: (offset na memória, tipo)  — da Cheat Table
    'nome': (0x38, 'str'), 'nome_camisa_clube': (0x75, 'str'), 'time': (0x12C, 'H'), 'liga': (0x12E, 'H'),
    'contrato_fim_ano': (0x138, 'H'), 'contrato_fim_mes': (0x13A, 'B'), 'contrato_fim_dia': (0x13B, 'B'),
    'afeicao': (0x13E, 'B'), 'flags_listado': (0x13F, 'B'), 'nacionalidade': (0x144, 'H'),
    'forma_seta': (0x147, 'B'), 'dias_indisponivel': (0x148, 'B'), 'listas_venda_emprestimo': (0x14A, 'B'),
    'papel_no_time': (0x150, 'B'), 'salario_anual_eur': (0x15C, 'I'), 'valor_mercado_eur': (0x174, 'I'),
}
DESLOC = 0x2C


def ler(caminho):
    b = open(caminho, 'rb').read()
    if caminho.endswith('.pesz'):
        from core.copia_remota import desempacotar
        raw, dec = desempacotar(b)
        if dec is None:
            from core import pescrypt
            dec = bytes(pescrypt.decrypt(raw).data)
        return dec
    return b


def campos(d, rec):
    out = {}
    for k, (o, t) in MEM.items():
        p = rec + o - DESLOC
        if t == 'str':
            s = d[p:p + 46].split(b'\0')[0]
            out[k] = s.decode('utf-8', 'replace')
        else:
            out[k] = struct.unpack_from('<' + t, d, p)[0]
    out['cgj_save'] = d[rec + 0x164]
    return out


if __name__ == '__main__':
    d = ler(sys.argv[1])
    for pid in map(int, sys.argv[2:]):
        alvo = struct.pack('<I', pid)
        i = d.find(alvo)
        while i != -1:
            rec = i - 4
            if rec >= 0 and rec + 0x170 <= len(d):
                c = campos(d, rec)
                if c['nome'] and c['nome'].isprintable():
                    print(f'id {pid} @0x{rec:x}:', c)
            i = d.find(alvo, i + 1)
