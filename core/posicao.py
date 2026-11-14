"""Posição dos jogadores para os textos da torcida, da imprensa e do assessor.

Uma frase pode começar com uma marca de setor, ex. "[MA]" = só para meio-campistas e atacantes:
G = goleiro, D = defensor (zagueiro e laterais), M = meio-campo, A = ataque.
Frase sem marca serve para qualquer posição. A marca nunca aparece no texto final.
Também existe o campo {funcao} ("o goleiro", "o zagueiro", "o meia"...), preenchido pela posição do jogador."""
import re

POS = {}          # nome do jogador -> sigla (GL, ZAG, LE, LD, VOL, MEI, ME, MD, PE, PD, ATA)

SETOR = {'GL': 'G', 'ZAG': 'D', 'LE': 'D', 'LD': 'D', 'VOL': 'M', 'MEI': 'M', 'MC': 'M', 'ME': 'M', 'MD': 'M',
         'PE': 'A', 'PD': 'A', 'SA': 'A', 'ATA': 'A'}
FUNCAO = {'GL': 'o goleiro', 'ZAG': 'o zagueiro', 'LE': 'o lateral', 'LD': 'o lateral', 'VOL': 'o volante',
          'MEI': 'o meia', 'MC': 'o meia', 'ME': 'o meia', 'MD': 'o meia', 'PE': 'o ponta', 'PD': 'o ponta',
          'SA': 'o atacante', 'ATA': 'o centroavante'}
_TAG = re.compile(r'^\[([GDMA]+)\]\s*')


def registrar(elenco):
    """Chamado sempre que o app lê o elenco do save."""
    POS.clear()
    for j in elenco or []:
        if j.get('nome') and j.get('pos'):
            POS[j['nome']] = j['pos']


def setor(nome):
    return SETOR.get(POS.get(nome or ''))


def funcao(nome):
    return FUNCAO.get(POS.get(nome or ''), 'o jogador')


def compativel(t, nome):
    m = _TAG.match(t)
    if not m:
        return True
    s = setor(nome)
    return s is not None and s in m.group(1)


def filtrar(pool, v):
    """Só as frases que combinam com a posição do jogador citado (se houver jogador no texto)."""
    nome = (v or {}).get('jogador')
    if not pool or not nome:
        return [t for t in pool if not _TAG.match(t)] or list(pool)
    ok = [t for t in pool if compativel(t, nome)]
    return ok or [t for t in pool if not _TAG.match(t)] or list(pool)


def limpar(t):
    return _TAG.sub('', t) if isinstance(t, str) else t


def completar(v):
    """Acrescenta {funcao} quando há jogador."""
    if v is not None and v.get('jogador') and 'funcao' not in v:
        v['funcao'] = funcao(v['jogador'])
    return v
