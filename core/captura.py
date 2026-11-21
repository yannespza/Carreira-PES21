"""Captura de memória da partida (somente leitura), para achar cartões, posse de bola e finalizações.

O módulo AppCarreiraCaptura.lua (versão 2) guarda cópias de até 1 MB da memória em volta do MATCH_INFO
(ctx.mis, a mesma estrutura que o Dynamic_Difficulty usa), dentro da região válida (VirtualQuery):
- quando o placar ou o período mudam (intervalo e fim de jogo);
- a cada 5 minutos de jogo;
- quando o relógio fica parado por 3 s (menu de pausa), uma vez por pausa: casa com as fotos da tela de estatísticas.
Não escreve nada no jogo. Escreve inicio.txt e mensagens no sider.log para diagnóstico.

Versão 1 (4.9.1) não gravava nada: ctx.mis chega como ponteiro (userdata) e tonumber() devolvia nil.

Arquivos: <pasta do jogo>\\GOGOSZ\\AppCarreira\\captura\\cap_<nº>_<min>m<seg>s_<placar>_p<período>_<motivo>_o<deslocamento>.bin
(até 60 por partida). O deslocamento (hex) é onde o MATCH_INFO começa dentro do arquivo.
"""
MODULO = 'AppCarreiraCaptura.lua'

LUA = r'''-- AppCarreiraCaptura.lua (App de Carreira PES 21) · versão 2 · SOMENTE LEITURA
-- Copia a memória em volta do MATCH_INFO em momentos-chave (pausa, gol, intervalo, a cada 5 min) para o app
-- descobrir onde ficam cartões, posse de bola e finalizações. Não escreve nada no jogo. Gerado pelo app.
local m = {}
local DIR = ".\\GOGOSZ\\AppCarreira\\captura\\"
local ANTES, DEPOIS, MAX = 0x80000, 0x80000, 60
local mis, n, ult_placar, ult_bloco = nil, 0, "", -1
local relogio, parado_desde, pausa_gravada = nil, nil, false

local function num(v)
    if v == nil then return nil end
    if type(v) == "number" then return v end
    if ffi then
        local ok, r = pcall(function() return tonumber(ffi.cast("uint64_t", ffi.cast("uintptr_t", ffi.cast("void*", v)))) end)
        if ok and r then return r end
        ok, r = pcall(function() return tonumber(ffi.cast("uint64_t", v)) end)
        if ok and r then return r end
    end
    return tonumber(v)
end

local VQ = nil
local function limites(a)
    if not ffi then return nil end
    if not VQ then
        pcall(ffi.cdef, [[
            typedef struct _ACC_MBI { void* BaseAddress; void* AllocationBase; uint32_t AllocationProtect;
                size_t RegionSize; uint32_t State; uint32_t Protect; uint32_t Type; } ACC_MBI;
            size_t ACC_VirtualQuery(const void* lpAddress, ACC_MBI* lpBuffer, size_t dwLength) asm("VirtualQuery");
        ]])
        local ok, f = pcall(function() return ffi.C.ACC_VirtualQuery end)
        if not ok then log("AppCarreiraCaptura: VirtualQuery indisponível") return nil end
        VQ = f
    end
    local mbi = ffi.new("ACC_MBI[1]")
    if VQ(ffi.cast("void*", a), mbi, ffi.sizeof("ACC_MBI")) == 0 then return nil end
    if mbi[0].State ~= 0x1000 then return nil end
    local b = tonumber(ffi.cast("uint64_t", ffi.cast("uintptr_t", mbi[0].BaseAddress)))
    return b, b + tonumber(mbi[0].RegionSize)
end

local function gravar(st, motivo)
    if not mis or n >= MAX or not memory or not memory.read then return end
    local ini, fim = limites(mis)
    if not ini then log("AppCarreiraCaptura: região do MATCH_INFO não encontrada") return end
    local a = math.max(mis - ANTES, ini)
    local z = math.min(mis + DEPOIS, fim)
    if z - a < 0x100 then return end
    local ok, b = pcall(memory.read, ffi.cast("char*", a), z - a)
    if not ok or type(b) ~= "string" then log("AppCarreiraCaptura: leitura falhou: " .. tostring(b)) return end
    n = n + 1
    local nome = string.format("%scap_%03d_%02dm%02ds_%dx%d_p%d_%s_o%X.bin", DIR, n, st.clock_minutes or 0,
        st.clock_seconds or 0, st.home_score or 0, st.away_score or 0, st.period or 0, motivo, mis - a)
    local f = io.open(nome, "wb")
    if f then f:write(b); f:close() else log("AppCarreiraCaptura: não abriu " .. nome) return end
    if n == 1 then log(string.format("AppCarreiraCaptura: primeira cópia gravada (%d KB)", math.floor(#b / 1024))) end
end

function m.after_set_conditions(ctx)
    local ok, err = pcall(function()
        local v = num(ctx.mis)
        log(string.format("AppCarreiraCaptura: inicio da partida, mis tipo=%s valor=%s", type(ctx.mis), v and string.format("%X", v) or "nil"))
        if not v or v < 0x10000 then return end
        mis, n, ult_placar, ult_bloco = v, 0, "", -1
        relogio, parado_desde, pausa_gravada = nil, nil, false
        local ini, fim = limites(v)
        local f = io.open(DIR .. "inicio.txt", "w")
        if f then
            f:write(string.format("mis=%X regiao=%s..%s casa=%s fora=%s\n", v, ini and string.format("%X", ini) or "?",
                fim and string.format("%X", fim) or "?", tostring(ctx.home_team), tostring(ctx.away_team)))
            f:close()
        else
            log("AppCarreiraCaptura: não abriu " .. DIR .. "inicio.txt")
        end
    end)
    if not ok then log("AppCarreiraCaptura: erro no início: " .. tostring(err)) end
end

local function quadro()
    if not mis then return end
    local st = match and match.stats and match.stats()
    if type(st) ~= "table" or not st.clock_minutes then return end
    local t = os.clock()
    local placar = tostring(st.home_score) .. "x" .. tostring(st.away_score) .. "p" .. tostring(st.period)
    local bloco = math.floor((st.clock_minutes or 0) / 5)
    local r = (st.clock_minutes or 0) * 60 + (st.clock_seconds or 0)
    local motivo = nil
    if placar ~= ult_placar then motivo = "muda" elseif bloco ~= ult_bloco then motivo = "min" end
    ult_placar, ult_bloco = placar, bloco
    if r ~= relogio then
        relogio, parado_desde, pausa_gravada = r, t, false
    elseif not pausa_gravada and parado_desde and t - parado_desde >= 3 then
        pausa_gravada = true
        motivo = "pausa"
    end
    if motivo then gravar(st, motivo) end
end

function m.frame(ctx)
    local ok, err = pcall(quadro)
    if not ok then log("AppCarreiraCaptura: erro: " .. tostring(err)); mis = nil end
end

function m.init(ctx)
    ctx.register("after_set_conditions", m.after_set_conditions)
    ctx.register("display_frame", m.frame)
    log("AppCarreiraCaptura 2: carregado (somente leitura)")
end

return m
'''


def instalar(pasta_jogo, backup_dir, log=print):
    import os
    from .ingame import instalar_modulo
    os.makedirs(os.path.join(pasta_jogo, 'GOGOSZ', 'AppCarreira', 'captura'), exist_ok=True)
    return instalar_modulo(pasta_jogo, backup_dir, log, nome=MODULO, conteudo=LUA)
