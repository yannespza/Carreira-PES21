"""Força extra do adversário dentro do jogo (desgaste do grupo e altitude), pelo mesmo caminho do
Dynamic_Difficulty.lua do patch: no evento after_set_conditions, MATCH_INFO + 0x20 (time 1, mandante) e
+ 0x28 (time 2, visitante) guardam o "impulso" de cada time.

O módulo AppCarreiraForca.lua lê GOGOSZ\\AppCarreira\\forca.txt e SOMA o valor ao que já estiver lá (o
Dynamic_Difficulty grava antes; por isso este módulo fica no fim da lista do sider.ini). Só age na partida
cujos dois times batem com o arquivo. Valor 0 = não mexe em nada.
"""
import os, re, shutil, time

MODULO = 'AppCarreiraForca.lua'

LUA = r'''-- AppCarreiraForca.lua (App de Carreira PES 21) · versão 1
-- Soma a força extra pedida pelo app (desgaste do grupo, altitude) ao impulso do time no MATCH_INFO,
-- o mesmo lugar que o Dynamic_Difficulty.lua do patch usa. Gerado pelo app; pode apagar.
local m = {}
local ARQ = ".\\GOGOSZ\\AppCarreira\\forca.txt"

local function ler()
    local f = io.open(ARQ, "r")
    if not f then return nil end
    local t = {}
    for line in f:lines() do
        local k, v = line:match("^(%w+)=(%-?%d+)")
        if k then t[k] = tonumber(v) end
    end
    f:close()
    return t
end

function m.after_set_conditions(ctx)
    if not ctx.mis or not ffi then return end
    local t = ler()
    if not t or not t.casa_id or not t.fora_id then return end
    if tonumber(ctx.home_team) ~= t.casa_id or tonumber(ctx.away_team) ~= t.fora_id then return end
    local p = ffi.cast("char*", ctx.mis)
    local function somar(off, extra)
        if not extra or extra == 0 then return end
        local a = p + off
        local atual = memory.unpack("u32", memory.read(a, 4))
        if atual > 20 then return end          -- valor estranho: não mexe
        local novo = math.max(0, math.min(10, atual + extra))
        memory.write(a, memory.pack("u32", novo))
        log(string.format("AppCarreiraForca: %s %d -> %d", memory.hex(a), atual, novo))
    end
    somar(0x20, t.casa)
    somar(0x28, t.fora)
end

function m.init(ctx)
    if not ffi then log("AppCarreiraForca: LuaJIT FFI desligado") return end
    ctx.register("after_set_conditions", m.after_set_conditions)
    log("AppCarreiraForca: carregado")
end

return m
'''


def instalar(pasta_jogo, backup_dir, log=print):
    """Grava o módulo e põe no FIM da lista de módulos do sider.ini (depois do Dynamic_Difficulty)."""
    mod = os.path.join(pasta_jogo, 'modules', MODULO)
    try:
        if not os.path.exists(mod) or open(mod, encoding='utf-8', errors='replace').read() != LUA:
            open(mod, 'w', encoding='utf-8').write(LUA)
    except OSError as e:
        log('não gravou o módulo de força:', e)
        return False
    ini = os.path.join(pasta_jogo, 'sider.ini')
    try:
        txt = open(ini, encoding='utf-8', errors='replace').read()
    except OSError:
        return False
    linhas = txt.splitlines(True)
    mods = [i for i, ln in enumerate(linhas) if re.match(r'\s*lua\.module\s*=', ln)]
    ja = [i for i in mods if MODULO.lower() in linhas[i].lower()]
    dd = [i for i in mods if 'dynamic_difficulty' in linhas[i].lower()]
    if ja and (not dd or ja[0] > dd[-1]):
        return True
    os.makedirs(backup_dir, exist_ok=True)
    shutil.copy2(ini, os.path.join(backup_dir, 'sider.ini.%d.bak' % int(time.time())))
    for i in reversed(ja):
        del linhas[i]
    mods = [i for i, ln in enumerate(linhas) if re.match(r'\s*lua\.module\s*=', ln)]
    pos = (mods[-1] + 1) if mods else len(linhas)
    if pos > 0 and not linhas[pos - 1].endswith('\n'):
        linhas[pos - 1] += '\n'
    linhas.insert(pos, f'lua.module = "{MODULO}"\n')
    open(ini, 'w', encoding='utf-8').write(''.join(linhas))
    log('módulo', MODULO, 'adicionado ao sider.ini')
    return True


def desinstalar(pasta_jogo):
    try:
        os.remove(os.path.join(pasta_jogo, 'GOGOSZ', 'AppCarreira', 'forca.txt'))
    except OSError:
        pass


def gravar(pasta_jogo, casa_id, fora_id, casa, fora):
    p = os.path.join(pasta_jogo, 'GOGOSZ', 'AppCarreira', 'forca.txt')
    os.makedirs(os.path.dirname(p), exist_ok=True)
    txt = f'casa_id={int(casa_id)}\nfora_id={int(fora_id)}\ncasa={int(casa)}\nfora={int(fora)}\n'
    try:
        if not os.path.exists(p) or open(p, encoding='utf-8').read() != txt:
            open(p, 'w', encoding='utf-8').write(txt)
        return True
    except OSError:
        return False
