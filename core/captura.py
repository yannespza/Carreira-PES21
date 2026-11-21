"""Captura de memória da partida (somente leitura), para achar cartões, posse de bola e finalizações.

O módulo AppCarreiraCaptura.lua guarda, a cada 20 segundos de partida, uma cópia de 32 KB do MATCH_INFO
(ctx.mis, a mesma estrutura que o Dynamic_Difficulty usa) e de 8 KB antes dele, com o minuto e o placar no
nome do arquivo. Também copia na hora em que o placar muda e no apito final. Não escreve nada no jogo.
Depois, comparando com a foto da tela de estatísticas do jogo, o app descobre onde ficam esses números.

Arquivos: <pasta do jogo>\\GOGOSZ\\AppCarreira\\captura\\cap_<nº>_<min>m<seg>s_<placar>.bin (até 150 por partida).
"""
MODULO = 'AppCarreiraCaptura.lua'

LUA = r'''-- AppCarreiraCaptura.lua (App de Carreira PES 21) · versão 1 · SOMENTE LEITURA
-- Copia o MATCH_INFO da partida a cada 20 s (e quando o placar muda) para o app descobrir
-- onde ficam cartões, posse de bola e finalizações. Não escreve nada no jogo. Gerado pelo app.
local m = {}
local DIR = ".\\GOGOSZ\\AppCarreira\\captura\\"
local mis, n, ult_t, ult_placar = nil, 0, -1e9, ""
local ANTES, TAM, MAX = 0x2000, 0x8000, 150

local function num(v)
    if type(v) == "number" then return v end
    if type(v) == "cdata" and ffi then return tonumber(ffi.cast("uint64_t", v)) end
    return tonumber(v)
end

local VQ = nil
local function limites(a)
    -- só lê dentro da região de memória onde o MATCH_INFO está (VirtualQuery), para nunca tocar página inválida
    if not ffi then return nil end
    if not VQ then
        pcall(ffi.cdef, [[
            typedef struct _ACC_MBI { void* BaseAddress; void* AllocationBase; uint32_t AllocationProtect;
                size_t RegionSize; uint32_t State; uint32_t Protect; uint32_t Type; } ACC_MBI;
            size_t ACC_VirtualQuery(const void* lpAddress, ACC_MBI* lpBuffer, size_t dwLength) asm("VirtualQuery");
        ]])
        local ok, f = pcall(function() return ffi.C.ACC_VirtualQuery end)
        if not ok then return nil end
        VQ = f
    end
    local mbi = ffi.new("ACC_MBI[1]")
    if VQ(ffi.cast("void*", a), mbi, ffi.sizeof("ACC_MBI")) == 0 then return nil end
    if mbi[0].State ~= 0x1000 then return nil end
    local b = tonumber(ffi.cast("uint64_t", mbi[0].BaseAddress))
    return b, b + tonumber(mbi[0].RegionSize)
end

local function gravar(motivo)
    if not mis or n >= MAX or not memory or not memory.read then return end
    local st = match and match.stats and match.stats() or {}
    if type(st) ~= "table" or not st.clock_minutes then return end
    local ini, fim = limites(mis)
    if not ini then return end
    local a = math.max(mis - ANTES, ini)
    local z = math.min(mis + TAM, fim)
    if z - a < 0x100 then return end
    local ok, b = pcall(memory.read, a, z - a)
    if not ok or type(b) ~= "string" then return end
    n = n + 1
    local nome = string.format("%scap_%03d_%02dm%02ds_%dx%d_p%d_%s_o%X.bin", DIR, n, st.clock_minutes or 0,
        st.clock_seconds or 0, st.home_score or 0, st.away_score or 0, st.period or 0, motivo, mis - a)
    local f = io.open(nome, "wb")
    if f then f:write(b); f:close() end
end

function m.after_set_conditions(ctx)
    local v = ctx.mis and num(ctx.mis)
    if v and v > 0x10000 then
        mis, n, ult_t, ult_placar = v, 0, -1e9, ""
        local f = io.open(DIR .. "inicio.txt", "w")
        local ini = limites(v)
        if f then f:write(string.format("mis=%X regiao=%s casa=%s fora=%s\n", v, ini and string.format("%X", ini) or "?", tostring(ctx.home_team), tostring(ctx.away_team))); f:close() end
    end
end

function m.frame(ctx)
    if not mis then return end
    local t = os.clock()
    local st = match and match.stats and match.stats()
    if type(st) ~= "table" or not st.clock_minutes then return end
    local placar = tostring(st.home_score) .. "x" .. tostring(st.away_score) .. "p" .. tostring(st.period)
    if placar ~= ult_placar then
        ult_placar = placar
        gravar("muda")
        ult_t = t
    elseif t - ult_t >= 20 then
        ult_t = t
        gravar("auto")
    end
end

function m.init(ctx)
    ctx.register("after_set_conditions", m.after_set_conditions)
    ctx.register("display_frame", m.frame)
    log("AppCarreiraCaptura: carregado (somente leitura)")
end

return m
'''


def instalar(pasta_jogo, backup_dir, log=print):
    import os
    from .ingame import instalar_modulo
    os.makedirs(os.path.join(pasta_jogo, 'GOGOSZ', 'AppCarreira', 'captura'), exist_ok=True)
    return instalar_modulo(pasta_jogo, backup_dir, log, nome=MODULO, conteudo=LUA)
