"""Captura de memória da partida (somente leitura), para achar cartões, posse de bola e finalizações.

O módulo AppCarreiraCaptura.lua (versão 3) guarda cópias de até 1 MB da memória em volta do MATCH_INFO
(ctx.mis, a mesma estrutura que o Dynamic_Difficulty usa), dentro da região válida (VirtualQuery):
- quando o placar ou o período mudam (intervalo e fim de jogo);
- a cada 5 minutos de jogo;
- quando o relógio fica parado por 3 s (menu de pausa), uma vez por pausa: casa com as fotos da tela de estatísticas.
Não escreve nada no jogo. Escreve inicio.txt e mensagens no sider.log para diagnóstico.

Versão 1 (4.9.1) não gravava nada: ctx.mis chega como userdata (debug_log.txt do zola_debugger) e tonumber() devolvia nil.
Versão 2 (4.9.4) usava pcall, que NÃO existe no Lua do Sider do patch (lista de globais no debug_log.txt).

Arquivos: <pasta do jogo>\\GOGOSZ\\AppCarreira\\captura\\cap_<nº>_<min>m<seg>s_<placar>_p<período>_<motivo>_o<deslocamento>.bin
(até 60 por partida). O deslocamento (hex) é onde o MATCH_INFO começa dentro do arquivo.
"""
MODULO = 'AppCarreiraCaptura.lua'

LUA = r'''-- AppCarreiraCaptura.lua (App de Carreira PES 21) · versão 3 · SOMENTE LEITURA
-- Copia a memória em volta do MATCH_INFO em momentos-chave (gol, intervalo, fim, a cada 5 min, pausa) para o
-- app descobrir onde ficam cartões, posse de bola e finalizações. Não escreve nada no jogo. Gerado pelo app.
-- Feito para o Lua do Sider do patch: sem pcall; ctx.mis chega como userdata (o mesmo que o Dynamic_Difficulty usa).
local m = {}
local DIR = nil
local ANTES, DEPOIS, MAX = 0x80000, 0x80000, 60
local mis, n, ult_placar, ult_bloco = nil, 0, "", -1
local relogio, parado_desde, pausa_gravada = nil, nil, false
local VQ, MBI = nil, nil

local function hex(v)
    if type(v) ~= "number" then return tostring(v) end
    local hi = math.floor(v / 4294967296)
    if hi > 0 then return string.format("%X%08X", hi, v - hi * 4294967296) end
    return string.format("%X", v)
end

local function agora()
    if os and os.clock then return os.clock() end
    return os.time()
end

-- endereço como número comum (igual ao Dynamic_Difficulty: ffi.cast("char*", ctx.mis))
local function endereco(v)
    if type(v) == "number" then return v end
    if v == nil or not ffi then return nil end
    return tonumber(ffi.cast("uint64_t", ffi.cast("uintptr_t", ffi.cast("char*", v))))
end

local LEGIVEL = { [0x02] = true, [0x04] = true, [0x08] = true, [0x20] = true, [0x40] = true, [0x80] = true }

-- região de memória válida em volta do endereço (VirtualQuery do Windows), para nunca ler página inválida
local function limites(a)
    if not VQ then
        ffi.cdef[[
            typedef struct _ACC_MBI { void* BaseAddress; void* AllocationBase; uint32_t AllocationProtect;
                size_t RegionSize; uint32_t State; uint32_t Protect; uint32_t Type; } ACC_MBI;
            size_t ACC_VirtualQuery(const void* lpAddress, ACC_MBI* lpBuffer, size_t dwLength) asm("VirtualQuery");
        ]]
        VQ = ffi.C.ACC_VirtualQuery
        MBI = ffi.new("ACC_MBI[1]")
    end
    if VQ(ffi.cast("void*", ffi.cast("uintptr_t", a)), MBI, ffi.sizeof("ACC_MBI")) == 0 then return nil end
    local st, pr = tonumber(MBI[0].State), tonumber(MBI[0].Protect)
    if st ~= 0x1000 then return nil end                         -- MEM_COMMIT
    if pr >= 0x100 or not LEGIVEL[pr % 0x100] then return nil end  -- sem PAGE_GUARD/NOACCESS
    local b = tonumber(ffi.cast("uint64_t", ffi.cast("uintptr_t", MBI[0].BaseAddress)))
    return b, b + tonumber(MBI[0].RegionSize)
end

local function gravar(st, motivo)
    if not mis or not DIR or n >= MAX or not memory or not memory.read then return end
    local ini, fim = limites(mis)
    if not ini then log("AppCarreiraCaptura: região do MATCH_INFO não está legível") return end
    local a = math.max(mis - ANTES, ini)
    local z = math.min(mis + DEPOIS, fim)
    if z - a < 0x100 then return end
    local b = memory.read(a, z - a)
    if type(b) ~= "string" or #b < 0x100 then log("AppCarreiraCaptura: leitura vazia") return end
    n = n + 1
    local nome = string.format("%scap_%03d_%02dm%02ds_%dx%d_p%d_%s_o%s.bin", DIR, n, st.clock_minutes or 0,
        st.clock_seconds or 0, st.home_score or 0, st.away_score or 0, st.period or 0, motivo, hex(mis - a))
    local f = io.open(nome, "wb")
    if not f then log("AppCarreiraCaptura: não abriu " .. nome) return end
    f:write(b)
    f:close()
    log(string.format("AppCarreiraCaptura: cópia %d gravada (%s, %d KB)", n, motivo, math.floor(#b / 1024)))
end

function m.after_set_conditions(ctx)
    log("AppCarreiraCaptura: início da partida, ctx.mis é " .. type(ctx.mis))
    local v = endereco(ctx.mis)
    if not v or v < 0x10000 then log("AppCarreiraCaptura: sem endereço do MATCH_INFO") return end
    mis, n, ult_placar, ult_bloco = v, 0, "", -1
    relogio, parado_desde, pausa_gravada = nil, nil, false
    local ini, fim = limites(v)
    local txt = string.format("mis=%s regiao=%s..%s casa=%s fora=%s", hex(v), hex(ini), hex(fim),
        tostring(ctx.home_team), tostring(ctx.away_team))
    log("AppCarreiraCaptura: " .. txt)
    local f = DIR and io.open(DIR .. "inicio.txt", "w")
    if f then f:write(txt, "\n"); f:close() else log("AppCarreiraCaptura: não abriu inicio.txt") end
end

function m.frame(ctx)
    if not mis then return end
    local st = match and match.stats and match.stats()
    if type(st) ~= "table" or not st.clock_minutes then return end
    local t = agora()
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

function m.init(ctx)
    if not ffi then log("AppCarreiraCaptura: LuaJIT FFI desligado, captura parada") return end
    DIR = (ctx.sider_dir or ".\\") .. "GOGOSZ\\AppCarreira\\captura\\"
    ctx.register("after_set_conditions", m.after_set_conditions)
    ctx.register("display_frame", m.frame)
    log("AppCarreiraCaptura 3: carregado (somente leitura), pasta " .. DIR)
end

return m
'''


def instalar(pasta_jogo, backup_dir, log=print):
    import os
    from .ingame import instalar_modulo
    os.makedirs(os.path.join(pasta_jogo, 'GOGOSZ', 'AppCarreira', 'captura'), exist_ok=True)
    return instalar_modulo(pasta_jogo, backup_dir, log, nome=MODULO, conteudo=LUA)
