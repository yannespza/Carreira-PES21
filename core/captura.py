"""Busca das estatísticas da partida na memória do jogo (somente leitura).

Histórico:
- v1 (4.9.1) não gravava: ctx.mis chega como userdata e tonumber() devolvia nil.
- v2 (4.9.4) usava pcall, que NÃO existe no Lua do Sider do patch.
- v3 (4.9.5) funcionou, mas o MATCH_INFO (ctx.mis) fica num bloco de 4 KB que quase não muda (só 2 bytes no jogo
  inteiro): as estatísticas não estão ali (Santos 1x1 Palmeiras, 21/11).
- v4 (4.9.6): busca estilo Cheat Engine. No intervalo, o usuário digita no app os passes da tela
  (casa total/certos, fora total/certos). O app grava captura\\busca.txt; o módulo lê (a cada 2 s), varre a
  memória privada do jogo (VirtualQuery: MEM_COMMIT, MEM_PRIVATE, leitura e escrita) atrás dos 4 números
  como u16 e u32 próximos (certos a até 0x100 bytes do total; o outro time a até 0x800), guarda até 40
  achados em resultado.txt e busca_000.bin (0x1000 bytes em volta de cada um) e procura ponteiros fixos
  para eles nas seções de dados do executável. Depois, a cada gol, pausa, intervalo, fim e 5 minutos,
  grava de novo esses mesmos trechos (hits_*.bin) para conferir com as fotos do fim de jogo.
"""

MODULO = 'AppCarreiraCaptura.lua'

LUA = r'''-- AppCarreiraCaptura.lua (App de Carreira PES 21) · versão 5 · SOMENTE LEITURA
-- Acha as estatísticas da partida na memória (como o Cheat Engine): no intervalo, o app grava os passes da
-- tela em captura\busca.txt e este módulo procura esses números. Não escreve nada no jogo. Gerado pelo app.
-- Feito para o Lua do Sider do patch: sem pcall; leitura direta pelo ffi só em memória conferida pelo VirtualQuery.
local m = {}
local DIR = nil
local MAXHITS, JANELA, MAXCAND = 40, 0x800, 2000000
local BUSCA = nil
local VQ, MBI, MBISZ = nil, nil, 0
local hits = {}
local busca_feita, confirma_feita, ult_poll, ptr_feito = "", "", -10, false
local n, ult_placar, ult_bloco = 0, "", -1
local relogio, parado_desde, pausa_gravada = nil, nil, false

local function hex(v)
    if type(v) ~= "number" then return tostring(v) end
    local hi = math.floor(v / 4294967296)
    if hi > 0 then return string.format("%X%08X", hi, v - hi * 4294967296) end
    return string.format("%X", v)
end
local function agora() if os and os.clock then return os.clock() end return os.time() end
local function num(p) return tonumber(ffi.cast("uint64_t", ffi.cast("uintptr_t", p))) end
local function ptr(a) return ffi.cast("void*", ffi.cast("uintptr_t", a)) end

local function prepara()
    if VQ then return end
    ffi.cdef[[
        typedef struct _ACC_MBI { void* BaseAddress; void* AllocationBase; uint32_t AllocationProtect;
            size_t RegionSize; uint32_t State; uint32_t Protect; uint32_t Type; } ACC_MBI;
        size_t ACC_VirtualQuery(const void* lpAddress, ACC_MBI* lpBuffer, size_t dwLength) asm("VirtualQuery");
        typedef struct _ACC_CAND { double a; int32_t reg; int16_t oc, ob, od; uint8_t w;
            uint16_t v0, v1, v2, v3; uint8_t modo; } ACC_CAND;
    ]]
    VQ = ffi.C.ACC_VirtualQuery
    MBI = ffi.new("ACC_MBI[1]")
    MBISZ = ffi.sizeof("ACC_MBI")
end

-- informação da região que contém o endereço: base, fim, estado, proteção, tipo
local function regiao(a)
    if VQ(ptr(a), MBI, MBISZ) == 0 then return nil end
    local b = num(MBI[0].BaseAddress)
    return b, b + tonumber(MBI[0].RegionSize), tonumber(MBI[0].State), tonumber(MBI[0].Protect), tonumber(MBI[0].Type)
end
local GRAVAVEL = { [0x04] = true, [0x40] = true }
local LEGIVEL = { [0x02] = true, [0x04] = true, [0x08] = true, [0x20] = true, [0x40] = true, [0x80] = true }
local function legivel(a, z)
    local b, f, st, pr = regiao(a)
    return b and st == 0x1000 and pr < 0x100 and LEGIVEL[pr] and z <= f
end

local function escreve(nome, txt, bin)
    local f = io.open(DIR .. nome, bin and "wb" or "w")
    if not f then log("AppCarreiraCaptura: não abriu " .. nome) return false end
    f:write(txt); f:close(); return true
end

-- candidatos guardados de forma compacta (até 1 milhão, ~40 MB), para aguentar memória cheia de números pequenos
local CAND, ncand, REGS = nil, 0, {}

-- varre um bloco de memória como inteiros de w bytes (1, 2 ou 4) atrás de A (total da casa) e C (certos ou
-- errados da casa, até 0x40 bytes); o time de fora tem que ter a MESMA arrumação (B em A+ob, D em A+ob+oc).
-- Para cada endereço de A guarda só a arrumação mais próxima (evita milhões de combinações do mesmo lugar).
local function varre(base, size, w, A, C, B, D, ireg, modo)
    local p = ffi.cast(w == 1 and "uint8_t*" or (w == 2 and "uint16_t*" or "uint32_t*"), ptr(base))
    local cnt = math.floor(size / w)
    local r1, r2 = math.floor(0x40 / w), math.floor(JANELA / w)
    for i = 0, cnt - 1 do
        if p[i] == A then
            local melhor_c, melhor_b = nil, nil
            for dc = -r1, r1 do
                local jc = i + dc
                if dc ~= 0 and jc >= 0 and jc < cnt and p[jc] == C then
                    for k = 1, r2 do
                        for _, db in ipairs({ k, -k }) do
                            local jb, jd = i + db, i + db + dc
                            if db ~= dc and jb >= 0 and jd >= 0 and jb < cnt and jd < cnt
                               and p[jb] == B and p[jd] == D then
                                if not melhor_b or math.abs(db) < math.abs(melhor_b) then melhor_c, melhor_b = dc, db end
                            end
                        end
                        if melhor_b and k >= math.abs(melhor_b) then break end
                    end
                end
            end
            if melhor_b then
                if ncand >= MAXCAND then return end
                local c = CAND[ncand]
                c.a = base + i * w; c.w = w; c.reg = ireg; c.modo = modo
                c.oc = melhor_c * w; c.ob = melhor_b * w; c.od = (melhor_b + melhor_c) * w
                if modo == 2 then c.v0, c.v1, c.v2, c.v3 = A, A - C, B, B - D   -- guarda sempre certos
                else c.v0, c.v1, c.v2, c.v3 = A, C, B, D end
                ncand = ncand + 1
            end
        end
    end
end

local function le(c, o)
    local r = REGS[c.reg]
    local a = c.a + o
    if a < r[1] or a + c.w > r[2] then return nil end
    if c.w == 1 then return ffi.cast("uint8_t*", ptr(a))[0] end
    if c.w == 2 then return ffi.cast("uint16_t*", ptr(a))[0] end
    return ffi.cast("uint32_t*", ptr(a))[0]
end

-- confere os candidatos. Fica quem se comporta como passes: total e certos só sobem, errados (total - certos)
-- também só sobem, certos <= total, no máximo 12 passes por minuto de jogo por time.
-- exato = {A, C, B, D}: confirmação do fim de jogo, fica só quem tem exatamente esses números.
local function conferir(A, C, B, D, minutos, exato)
    for k, r in ipairs(REGS) do r[3] = legivel(r[1], r[2]) or false end
    local m2 = 0
    hits = {}
    local teto = 12 * math.max(1, minutos) + 10
    for i = 0, ncand - 1 do
        local c = CAND[i]
        if REGS[c.reg][3] then
            local a, cc, b, d = le(c, 0), le(c, c.oc), le(c, c.ob), le(c, c.od)
            if a and cc and b and d and c.modo == 2 then cc, d = a - cc, b - d end   -- guardado como errados
            local ok = a and cc and b and d and a >= c.v0 and cc >= c.v1 and b >= c.v2 and d >= c.v3
               and cc >= 0 and d >= 0 and cc <= a and d <= b and a - cc >= c.v0 - c.v1 and b - d >= c.v2 - c.v3
               and a - c.v0 <= teto and b - c.v2 <= teto
            if ok and exato then ok = a == exato[1] and cc == exato[2] and b == exato[3] and d == exato[4] end
            if ok then
                c.v0, c.v1, c.v2, c.v3 = a, cc, b, d   -- sempre guardado como certos
                if m2 ~= i then CAND[m2] = c end
                if (exato or (a > A and cc > C and b > B and d > D)) and #hits < MAXHITS then
                    hits[#hits + 1] = { a = c.a, w = c.w, oc = c.oc, ob = c.ob, od = c.od,
                        rb = REGS[c.reg][1], rf = REGS[c.reg][2], v = { a, cc, b, d } }
                end
                m2 = m2 + 1
            end
        end
    end
    ncand = m2
end

local function trecho(h)
    local a = math.max(h.a - JANELA, h.rb)
    local z = math.min(h.a + JANELA, h.rf)
    if not legivel(a, z) then return string.rep("\0", 2 * JANELA) end
    local b = ffi.string(ptr(a), z - a)
    return string.rep("\0", (h.a - JANELA) < a and (a - (h.a - JANELA)) or 0) .. b ..
           string.rep("\0", math.max(0, (h.a + JANELA) - z))
end

-- ponteiros fixos: seções de dados do executável (MEM_IMAGE, gravável) que apontam para perto de um achado
local function ponteiros(linhas)
    local info = memory.get_process_info and memory.get_process_info()
    local base = info and info.base and num(info.base)
    if not base or #hits == 0 then return end
    local lo, hi = math.huge, 0
    for _, h in ipairs(hits) do lo = math.min(lo, h.a - 0x8000); hi = math.max(hi, h.a) end
    local a, total = base, 0
    while a < base + 0x40000000 do
        local b, f, st, pr, tp = regiao(a)
        if not b or b > base + 0x40000000 then break end
        if st == 0x1000 and tp == 0x1000000 and (pr == 0x04 or pr == 0x08) then
            local p = ffi.cast("uint32_t*", ptr(b))
            for i = 0, math.floor((f - b) / 8) - 1 do
                local v = p[2 * i + 1] * 4294967296 + p[2 * i]
                if v >= lo and v <= hi then
                    for k, h in ipairs(hits) do
                        if v <= h.a and h.a - v <= 0x8000 then
                            linhas[#linhas + 1] = string.format("ptr exe+%s -> %s (achado %d, +%s)", hex(b + i * 8 - base), hex(v), k, hex(h.a - v))
                            total = total + 1
                        end
                    end
                    if total > 200 then return end
                end
            end
        end
        if f <= a then break end
        a = f
    end
end

local function buscar(txt)
    local v = {}
    for x in txt:gmatch("%d+") do v[#v + 1] = tonumber(x) end
    if #v < 4 then return end
    -- 5º número = hora do pedido (o app grava); pedido com mais de 10 minutos é ignorado
    if v[5] and os and os.time and math.abs(os.time() - v[5]) > 600 then
        log("AppCarreiraCaptura: pedido de busca antigo ignorado") return
    end
    local A, C, B, D = v[1], v[2], v[3], v[4]
    prepara()
    if v[6] == 2 then
        if not BUSCA then log("AppCarreiraCaptura: confirmação sem busca anterior nesta partida") return end
        local st = match and match.stats and match.stats() or {}
        local antes = ncand
        conferir(BUSCA[1], BUSCA[2], BUSCA[3], BUSCA[4], st.clock_minutes or 90, { A, C, B, D })
        n = n + 1
        local linhas = { string.format("momento=%d confirmacao=%d(%d) x %d(%d) antes=%d ficaram=%d", n, A, C, B, D, antes, ncand) }
        for k, h in ipairs(hits) do
            linhas[#linhas + 1] = string.format("achado %d em %s largura=%d certos%+d fora%+d fora_certos%+d valores=%d(%d) x %d(%d)",
                k, hex(h.a), h.w, h.oc, h.ob, h.od, h.v[1], h.v[2], h.v[3], h.v[4])
        end
        if #hits > 0 and #hits <= 10 then ptr_feito = true; ponteiros(linhas) end
        local partes = {}
        for _, h in ipairs(hits) do partes[#partes + 1] = trecho(h) end
        escreve(string.format("hits_%03d.txt", n), table.concat(linhas, "\n") .. "\n")
        if #partes > 0 then escreve(string.format("hits_%03d.bin", n), table.concat(partes), true) end
        escreve("confirmacao.txt", table.concat(linhas, "\n") .. "\n")
        log(string.format("AppCarreiraCaptura: confirmação no fim: %d de %d candidatos batem", ncand, antes))
        return
    end
    log(string.format("AppCarreiraCaptura: procurando passes %d(%d) x %d(%d)...", A, C, B, D))
    local t0 = agora()
    if not CAND then CAND = ffi.new("ACC_CAND[?]", MAXCAND) end
    ncand, REGS, hits = 0, {}, {}
    BUSCA = { A, C, B, D }
    local nreg, mb, cheio = 0, 0, false
    local a = 0x10000
    while a < 0x7FFFFFFF0000 do
        local b, f, st, pr, tp = regiao(a)
        if not b or f <= a then break end
        if st == 0x1000 and tp == 0x20000 and GRAVAVEL[pr] then
            nreg = nreg + 1; mb = mb + (f - b) / 1048576
            REGS[nreg] = { b, f, true }
            for _, w in ipairs({ 4, 2, 1 }) do
                varre(b, f - b, w, A, C, B, D, nreg, 1)            -- certos
                varre(b, f - b, w, A, A - C, B, B - D, nreg, 2)    -- errados (total - certos)
            end
            if ncand >= MAXCAND and not cheio then
                cheio = true
                log(string.format("AppCarreiraCaptura: limite de candidatos atingido depois de %d MB", math.floor(mb)))
            end
        end
        a = f
    end
    local linhas = { "busca=" .. (txt:gsub("%s+$", "")),
        string.format("regioes=%d memoria_mb=%d segundos=%.1f candidatos=%d", nreg, math.floor(mb), agora() - t0, ncand) }
    escreve("resultado.txt", table.concat(linhas, "\n") .. "\n")
    log(string.format("AppCarreiraCaptura: busca terminou em %.1f s, %d candidatos", agora() - t0, ncand))
end

-- a cada momento-chave: elimina candidatos falsos e grava os que sobraram
local function gravar(st, motivo)
    if not BUSCA or n >= 80 then return end
    conferir(BUSCA[1], BUSCA[2], BUSCA[3], BUSCA[4], math.max(1, (st.clock_minutes or 45) - 45), nil)
    n = n + 1
    local linhas = { string.format("momento=%d tempo=%d:%02d placar=%dx%d periodo=%d motivo=%s candidatos=%d cresceram=%d",
        n, st.clock_minutes or 0, st.clock_seconds or 0, st.home_score or 0, st.away_score or 0, st.period or 0,
        motivo, ncand, #hits) }
    local partes = {}
    for k, h in ipairs(hits) do
        linhas[#linhas + 1] = string.format("achado %d em %s largura=%d certos%+d fora%+d fora_certos%+d valores=%d(%d) x %d(%d)",
            k, hex(h.a), h.w, h.oc, h.ob, h.od, h.v[1], h.v[2], h.v[3], h.v[4])
        partes[#partes + 1] = trecho(h)
    end
    if #hits > 0 and #hits <= 10 and not ptr_feito then ptr_feito = true; ponteiros(linhas) end
    escreve(string.format("hits_%03d.txt", n), table.concat(linhas, "\n") .. "\n")
    if #partes > 0 then escreve(string.format("hits_%03d.bin", n), table.concat(partes), true) end
    log(string.format("AppCarreiraCaptura: momento %d (%s), %d candidatos, %d cresceram", n, motivo, ncand, #hits))
end

function m.after_set_conditions(ctx)
    hits, n, ult_placar, ult_bloco, ptr_feito = {}, 0, "", -1, false
    -- (a busca e a confirmação já feitas continuam marcadas: não repete sozinha na partida seguinte)
    ncand, BUSCA = 0, nil
    relogio, parado_desde, pausa_gravada = nil, nil, false
    log("AppCarreiraCaptura 5: partida começou; digite os passes no app no intervalo")
end

function m.frame(ctx)
    local t = agora()
    if t - ult_poll >= 2 then
        ult_poll = t
        local f = io.open(DIR .. "busca.txt", "r")
        if f then
            local txt = f:read("*a") or ""
            f:close()
            if txt ~= busca_feita and txt:match("%d") then busca_feita = txt; buscar(txt) end
        end
        local g = io.open(DIR .. "confirma.txt", "r")
        if g then
            local txt = g:read("*a") or ""
            g:close()
            if txt ~= confirma_feita and txt:match("%d") then confirma_feita = txt; buscar(txt) end
        end
    end
    if not BUSCA then return end
    local st = match and match.stats and match.stats()
    if type(st) ~= "table" or not st.clock_minutes then return end
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
    log("AppCarreiraCaptura 5: carregado (somente leitura), pasta " .. DIR)
end

return m
'''


def instalar(pasta_jogo, backup_dir, log=print):
    import os
    from .ingame import instalar_modulo
    os.makedirs(os.path.join(pasta_jogo, 'GOGOSZ', 'AppCarreira', 'captura'), exist_ok=True)
    return instalar_modulo(pasta_jogo, backup_dir, log, nome=MODULO, conteudo=LUA)


# ---------- lado do app: pedir a busca e ler o resultado ----------
import os as _os
import time as _time
import re as _re


def _pasta(pasta_jogo):
    return _os.path.join(pasta_jogo or '', 'GOGOSZ', 'AppCarreira', 'captura')


def pedir_busca(pasta_jogo, casa_total, casa_certos, fora_total, fora_certos, fim=False):
    """Grava captura\\busca.txt com os passes da tela; o módulo lê em até 2 s e varre a memória."""
    v = [int(casa_total), int(casa_certos), int(fora_total), int(fora_certos)]
    if not (0 < v[0] < 2000 and 0 <= v[1] <= v[0] and 0 < v[2] < 2000 and 0 <= v[3] <= v[2]):
        raise ValueError('Confira os números: os certos não podem passar do total.')
    d = _pasta(pasta_jogo)
    _os.makedirs(d, exist_ok=True)
    # fim=True: confirmação na tela de fim de jogo (fica só quem tem exatamente esses números)
    with open(_os.path.join(d, 'confirma.txt' if fim else 'busca.txt'), 'w') as f:
        f.write('%d %d %d %d %d %d\n' % (tuple(v) + (int(_time.time()), 2 if fim else 1)))
    return v


def estado(pasta_jogo):
    """O que o módulo já fez: busca pedida, resultado e o último momento conferido."""
    d = _pasta(pasta_jogo)
    out = {'pedida': None, 'candidatos': None, 'segundos': None, 'momentos': 0, 'cresceram': None,
           'achados': [], 'ponteiros': 0}
    try:
        out['pedida'] = open(_os.path.join(d, 'busca.txt')).read().split()[:4]
    except OSError:
        pass
    try:
        txt = open(_os.path.join(d, 'resultado.txt')).read()
        m = _re.search(r'candidatos=(\d+)', txt)
        out['candidatos'] = int(m.group(1)) if m else None
        m = _re.search(r'segundos=([\d.]+)', txt)
        out['segundos'] = float(m.group(1)) if m else None
        m = _re.search(r'busca=([\d ]+)', txt)
        out['buscado'] = m.group(1).split()[:4] if m else None
    except OSError:
        pass
    try:
        nomes = sorted(x for x in _os.listdir(d) if x.startswith('hits_') and x.endswith('.txt'))
    except OSError:
        nomes = []
    out['momentos'] = len(nomes)
    try:
        txt = open(_os.path.join(d, 'confirmacao.txt')).read()
        m = _re.search(r'antes=(\d+) ficaram=(\d+)', txt)
        out['confirmacao'] = {'antes': int(m.group(1)), 'ficaram': int(m.group(2)),
                              'ponteiros': len(_re.findall(r'^ptr ', txt, _re.M))} if m else None
    except OSError:
        out['confirmacao'] = None
    if nomes:
        txt = open(_os.path.join(d, nomes[-1])).read()
        m = _re.search(r'cresceram=(\d+)', txt)
        out['cresceram'] = int(m.group(1)) if m else None
        out['achados'] = _re.findall(r'valores=(\d+\(\d+\) x \d+\(\d+\))', txt)[:5]
        out['ponteiros'] = len(_re.findall(r'^ptr ', txt, _re.M))
        out['ultimo'] = txt.splitlines()[0] if txt else ''
    return out

