"""Leitura da memória do jogo pelo Sider (SOMENTE LEITURA, fase de diagnóstico).

Objetivo: confirmar se a tabela de jogadores do clube que está no save (registros de 0x170 bytes, id em +4)
também está na RAM do PES2021.exe durante o Master League, e com quais valores (dias de lesão, barra de energia,
seta de forma, valor de mercado, fim de contrato, listas de venda/empréstimo — posições da Cheat Table do
xAranaktu, deslocadas em −0x2C).

Como funciona, sem endereço fixo (vale para o GOGOSZ e para qualquer versão do exe):
- a cada save lido, o app grava GOGOSZ\\AppCarreira\\memoria_alvo.txt com uma ASSINATURA: 32 bytes do 1º registro
  da tabela do clube no save (a partir do id) e a lista de ids;
- o módulo AppCarreiraMemoria.lua procura essa assinatura nas regiões de memória do processo (só as grandes,
  gravadas e de leitura/escrita), no evento "set_teams" (antes de cada jogo) e no "context_reset" (volta ao menu);
- achando, grava GOGOSZ\\AppCarreira\\memoria_<evento>.txt com o registro inteiro em hexa de cada jogador;
- a cópia para o Claude envia esses arquivos junto com os saves.
NADA é gravado na memória do jogo nesta fase. Precisa de luajit.ext.enabled = 1 no sider.ini (o app liga)."""
import os, re, shutil, time
import numpy as np

MODULO = 'AppCarreiraMemoria.lua'
PASTA = os.path.join('GOGOSZ', 'AppCarreira')
PASSO = 0x170
TAM_ASSIN = 32

LUA = r'''-- App Carreira PES 21: leitura da memória do jogo (SOMENTE LEITURA, diagnóstico).
-- Procura na RAM a tabela de jogadores do clube (assinatura tirada do save pelo app) e grava o que achou em
-- GOGOSZ\AppCarreira\memoria_<evento>.txt. Não escreve nada na memória. Gerado pelo app; pode apagar.
local m = {}
local root = ".\\GOGOSZ\\AppCarreira"
local achado = nil      -- endereço (cdata) do 1º registro achado
local assin_achada = nil
local cdef_ok = false

local function tlog(...) log("AppCarreiraMemoria: " .. string.format(...)) end

local function hex2bin(h) return (h:gsub("%x%x", function(c) return string.char(tonumber(c, 16)) end)) end

local function ler_alvo()
    local f = io.open(root .. "\\memoria_alvo.txt", "r")
    if not f then return nil end
    local a = { ids = {} }
    for line in f:lines() do
        local k, v = line:match("^(%w+)=(.*)$")
        if k == "assinatura" then a.sig = hex2bin(v)
        elseif k == "passo" then a.passo = tonumber(v)
        elseif k == "desloc" then a.desloc = tonumber(v)
        elseif k == "id" then a.ids[#a.ids + 1] = tonumber(v) end
    end
    f:close()
    if not a.sig or #a.sig < 16 then return nil end
    a.passo = a.passo or 0x170
    a.desloc = a.desloc or 4
    return a
end

local function prepara_ffi()
    if cdef_ok then return true end
    if not ffi then
        tlog("LuaJIT FFI desligado: ponha luajit.ext.enabled = 1 no sider.ini")
        return false
    end
    pcall(ffi.cdef, [[
        typedef struct _AC_MBI { void* BaseAddress; void* AllocationBase; uint32_t AllocationProtect;
            size_t RegionSize; uint32_t State; uint32_t Protect; uint32_t Type; } AC_MBI;
        size_t VirtualQuery(const void* lpAddress, AC_MBI* lpBuffer, size_t dwLength);
    ]])
    cdef_ok = true
    return true
end

local function procurar(sig)
    local mbi = ffi.new("AC_MBI[1]")
    local addr = ffi.cast("uint64_t", 0x10000)
    local limite = ffi.cast("uint64_t", 0x7FFFFFFF0000ULL)
    local regioes = 0
    while addr < limite do
        if ffi.C.VirtualQuery(ffi.cast("void*", addr), mbi, ffi.sizeof("AC_MBI")) == 0 then break end
        local b = ffi.cast("uint64_t", mbi[0].BaseAddress)
        local sz = ffi.cast("uint64_t", mbi[0].RegionSize)
        if sz == 0 then break end
        -- MEM_COMMIT (0x1000), PAGE_READWRITE (0x04), regiões de 1 MB ou mais (onde ficam os dados do Master League)
        if mbi[0].State == 0x1000 and mbi[0].Protect == 0x04 and sz >= 0x100000 then
            regioes = regioes + 1
            local ok, res = pcall(memory.search, sig, b, b + sz)
            if ok and res then return res, regioes end
        end
        addr = b + sz
    end
    return nil, regioes
end

local function despejar(evento)
    local a = ler_alvo()
    if not a then return end
    if not prepara_ffi() then return end
    local t0 = os.clock()
    local p = nil
    if achado and assin_achada == a.sig and memory.read(achado, #a.sig) == a.sig then
        p = achado
    else
        local res, regioes = procurar(a.sig)
        if not res then
            tlog("assinatura NÃO encontrada (%d regiões olhadas, %.1fs)", regioes, os.clock() - t0)
            local f = io.open(root .. "\\memoria_" .. evento .. ".txt", "w")
            if f then f:write("achou=nao\nregioes=" .. regioes .. "\nquando=" .. os.date("%Y-%m-%d %H:%M:%S") .. "\n") f:close() end
            return
        end
        p = res
        achado, assin_achada = res, a.sig
    end
    local base = ffi.cast("char*", p) - a.desloc
    local f = io.open(root .. "\\memoria_" .. evento .. ".txt", "w")
    if not f then return end
    f:write("achou=sim\nendereco=" .. memory.hex(ffi.cast("uint64_t", base)) .. "\nquando=" .. os.date("%Y-%m-%d %H:%M:%S") .. "\n")
    -- registros em sequência a partir do 1º (mesma ordem do save), até o id deixar de bater com a lista
    local n = 0
    for i = 0, 120 do
        local r = base + i * a.passo
        local ok, bytes = pcall(memory.read, r, a.passo)
        if not ok then break end
        local id = memory.unpack("u32", bytes:sub(a.desloc + 1, a.desloc + 4))
        if id == 0 or id > 2000000 then break end
        f:write("reg=" .. i .. "|" .. id .. "|" .. memory.hex(bytes) .. "\n")
        n = n + 1
    end
    f:close()
    tlog("%s: tabela achada, %d registros gravados (%.1fs)", evento, n, os.clock() - t0)
end

function m.set_teams(ctx, home, away) pcall(despejar, "antes_do_jogo") end
function m.reset(ctx) pcall(despejar, "menu") end

function m.init(ctx)
    ctx.register("set_teams", m.set_teams)
    ctx.register("context_reset", m.reset)
    tlog("carregado (somente leitura)")
end

return m
'''


def assinatura(data, elenco_ids=None):
    """Acha a tabela do clube no save (mesma regra de jogadores.juniores) e devolve (offset, assinatura, ids)."""
    from .jogadores import _tabela
    a = np.frombuffer(data[:len(data) // 4 * 4], '<u4')
    P = PASSO // 4
    st = lambda i: data[i * 4 + 0x13c]
    cg = lambda i: data[i * 4 + 0x164]
    alvo = set(elenco_ids or [])
    melhor = None
    for k in _tabela(a, P, 3, lambda k: all(st(k + j * P) in (3, 11) and 40 <= cg(k + j * P) <= 99 for j in range(3))):
        ids, i = [], k
        while i + P <= len(a) and (i == k or a[i] == a[i - P] + 1) and st(i) in (3, 11):
            ids.append(int(a[i + 1]))
            i += P
        bate = len(alvo & set(ids)) if alvo else len(ids)
        if melhor is None or bate > melhor[2]:
            melhor = (k, ids, bate)
    if not melhor:
        return None
    k, ids, _ = melhor
    o = k * 4 + 4
    return {'offset': k * 4, 'assinatura': data[o:o + TAM_ASSIN].hex(), 'ids': ids}


def preparar(pasta_jogo, data, elenco_ids, backup_dir, log=print):
    """Grava memoria_alvo.txt, instala o módulo e liga o LuaJIT FFI no sider.ini (com backup)."""
    if not pasta_jogo or not os.path.isdir(pasta_jogo):
        return False
    s = assinatura(data, elenco_ids)
    if not s:
        log('memória: tabela do clube não achada no save')
        return False
    pasta = os.path.join(pasta_jogo, PASTA)
    os.makedirs(pasta, exist_ok=True)
    txt = (f"assinatura={s['assinatura']}\npasso={PASSO}\ndesloc=4\noffset_no_save={s['offset']}\n"
           + ''.join(f'id={i}\n' for i in s['ids']))
    alvo = os.path.join(pasta, 'memoria_alvo.txt')
    try:
        if not os.path.exists(alvo) or open(alvo, encoding='utf-8').read() != txt:
            open(alvo, 'w', encoding='utf-8').write(txt)
    except OSError as e:
        log('memória: não gravou o alvo:', e)
        return False
    from . import ingame
    ingame.instalar_modulo(pasta_jogo, backup_dir, log, nome=MODULO, conteudo=LUA)
    ligar_ffi(pasta_jogo, backup_dir, log)
    return True


def ligar_ffi(pasta_jogo, backup_dir, log=print):
    ini = os.path.join(pasta_jogo, 'sider.ini')
    try:
        txt = open(ini, encoding='utf-8', errors='replace').read()
    except OSError:
        return False
    if re.search(r'^\s*luajit\.ext\.enabled\s*=\s*1', txt, re.M):
        return True
    os.makedirs(backup_dir, exist_ok=True)
    shutil.copy2(ini, os.path.join(backup_dir, 'sider.ini.%d.bak' % int(time.time())))
    nl = '\r\n' if '\r\n' in txt else '\n'
    if re.search(r'^\s*luajit\.ext\.enabled\s*=', txt, re.M):
        txt = re.sub(r'^(\s*luajit\.ext\.enabled\s*=\s*)\d+', r'\g<1>1', txt, flags=re.M)
    else:
        txt = txt.rstrip('\r\n') + nl + 'luajit.ext.enabled = 1' + nl
    open(ini, 'w', encoding='utf-8').write(txt)
    log('memória: LuaJIT FFI ligado no sider.ini')
    return True


def arquivos_lidos(pasta_jogo):
    p = os.path.join(pasta_jogo or '', PASTA)
    try:
        return [os.path.join(p, n) for n in os.listdir(p) if re.fullmatch(r'memoria_(antes_do_jogo|menu)\.txt', n)]
    except OSError:
        return []
