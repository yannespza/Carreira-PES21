"""Ponte Lua -> Python para a partida ao vivo.

O módulo AppCarreiraAoVivo.lua roda dentro do jogo (Sider) e grava live_match_data.json na pasta do jogo
sempre que algo muda: placar, período, minuto. Este módulo lê esse arquivo numa thread de fundo, por
polling barato (mtime + tamanho a cada 0,5 s), sem travar o servidor nem a interface.

O que o Sider entrega de verdade (confirmado nos módulos do GOGOSZ instalados):
- match.stats(): home_score, away_score, period, clock_minutes, clock_seconds (o placar do patch usa isso);
- ctx.home_team, ctx.away_team, ctx.tournament_id, ctx.sider_dir e o evento display_frame (todo quadro);
- io.open para gravar arquivos.
Goleador: lido pela mesma cadeia de ponteiros que o GOGOSZ usa no GolsJogador.lua (só leitura).
Cartões, lesões e substituições não têm caminho conhecido: o modo sondagem grava fotos da memória quando
você aperta C, L, S ou R no menu do Sider, para comparar e achar onde o jogo guarda esses dados.
"""
import os, json, time, threading

MODULO = 'AppCarreiraAoVivo.lua'
ARQUIVO = 'live_match_data.json'

LUA = r'''-- AppCarreiraAoVivo.lua (App de Carreira PES 21)
-- Ponte com o app: grava live_match_data.json na pasta do jogo quando a partida muda.
-- Não desenha nada no campo e não escreve na memória do jogo: lê match.stats(), lê (só lê) a cadeia de
-- ponteiros do goleador que o próprio GOGOSZ usa (GolsJogador.lua) e grava arquivos.
-- Modo sondagem: no menu do Sider, com este módulo na tela, as teclas C, L, S e R gravam uma "foto" da memória
-- para descobrirmos onde o jogo guarda cartões, lesões e substituições.
local m = { version = "1.3" }

local ARQ, TMP, PASTA_SONDA
local quadro = 0
local ativo = false
local ult = nil
local casa, fora, torneio = nil, nil, nil
local eventos = {}
local seq = 0
local pend = nil          -- gol esperando a leitura do goleador
local nsondas = 0
local aviso = ""

-- cadeia do goleador (a mesma do GolsJogador.lua do GOGOSZ):
-- base do jogo + 0x3700A68 -> ponteiro; +0x0 -> ponteiro; +0x48 -> ponteiro; +0x1C4 = id do jogador (u32)
local OFS = { 0x3700A68, 0x0, 0x48, 0x1C4 }

local function esc(s)
    s = tostring(s)
    s = s:gsub('\\', '\\\\'):gsub('"', '\\"'):gsub('\n', '\\n'):gsub('\r', '')
    return s
end

local function json(v)
    local t = type(v)
    if t == "number" then
        if v ~= v or v == math.huge or v == -math.huge then return "null" end
        return tostring(v)
    elseif t == "boolean" then return v and "true" or "false"
    elseif t == "string" then return '"' .. esc(v) .. '"'
    elseif t == "table" then
        local vazio = true
        for _ in pairs(v) do vazio = false; break end
        if #v > 0 or vazio then
            local p = {}
            for i = 1, #v do p[#p + 1] = json(v[i]) end
            return "[" .. table.concat(p, ",") .. "]"
        end
        local p = {}
        for k, x in pairs(v) do
            local tx = type(x)
            if tx == "number" or tx == "string" or tx == "boolean" or tx == "table" then
                p[#p + 1] = '"' .. esc(k) .. '":' .. json(x)
            end
        end
        return "{" .. table.concat(p, ",") .. "}"
    end
    return "null"
end

-- ---------- leitura de memória (só leitura) ----------
-- O Sider do patch não oferece pcall: só lemos endereços que vieram de ponteiros conferidos.
local function bytes(addr, n)
    if not memory or not memory.read or type(addr) ~= "number" then return nil end
    local b = memory.read(addr, n)
    if type(b) == "string" and #b >= n then return b end
    return nil
end

local function le_u32(s, i)
    local a, b, c, d = s:byte(i, i + 3)
    if not d then return nil end
    return a + b * 256 + c * 65536 + d * 16777216
end

local function u32(a) local b = bytes(a, 4); return b and le_u32(b, 1) end
local function u64(a)
    local b = bytes(a, 8)
    if not b then return nil end
    local lo, hi = le_u32(b, 1), le_u32(b, 5)
    return lo and hi and (lo + hi * 4294967296)
end
local function ptr_ok(v) return type(v) == "number" and v > 0x10000 and v < 0x7fffffffffff end

local function cadeia()
    if not memory or not memory.get_process_info then return nil end
    local info = memory.get_process_info()
    if type(info) ~= "table" or not info.base then return nil end
    local p = u64(info.base + OFS[1]); if not ptr_ok(p) then return nil end
    local q = u64(p + OFS[2]); if not ptr_ok(q) then return nil end
    local r = u64(q + OFS[3]); if not ptr_ok(r) then return nil end
    return p, q, r
end

local function goleador()
    local p, q, r = cadeia()
    if not r then return nil end
    local id = u32(r + OFS[4])
    if id and id > 0 and id < 700000 then return id end
    return nil
end

-- ---------- arquivo para o app ----------
local function gravar(status)
    if not ARQ then return end
    local dados = {
        versao = m.version, status = status, seq = seq, casa = casa, fora = fora, torneio = torneio,
        placar = ult and { ult.home_score or 0, ult.away_score or 0 } or nil,
        periodo = ult and ult.period or nil,
        minuto = ult and ult.clock_minutes or nil, segundo = ult and ult.clock_seconds or nil,
        campos = ult, eventos = eventos, sondas = nsondas,
    }
    local txt = json(dados)
    local f = io.open(TMP, "w")
    if not f then return end
    f:write(txt)
    f:close()
    os.remove(ARQ)
    if not os.rename(TMP, ARQ) then
        local g = io.open(ARQ, "w")
        if g then g:write(txt); g:close() end
    end
end

local function evento(tipo, extra)
    seq = seq + 1
    local e = { seq = seq, tipo = tipo, periodo = ult and ult.period, minuto = ult and ult.clock_minutes,
                segundo = ult and ult.clock_seconds }
    for k, v in pairs(extra or {}) do e[k] = v end
    eventos[#eventos + 1] = e
    return e
end

local function copiar(st)
    local c = {}
    for k, v in pairs(st) do
        local t = type(v)
        if t == "number" or t == "string" or t == "boolean" then c[k] = v end
    end
    return c
end

-- ---------- sondagem ----------
local ROTULOS = { [0x43] = "cartao", [0x4C] = "lesao", [0x53] = "substituicao", [0x52] = "referencia" }

local function sonda(rotulo)
    if not PASTA_SONDA then return end
    local p, q, r = cadeia()
    nsondas = nsondas + 1
    local nome = string.format("%s%03d_%s_%s", PASTA_SONDA, nsondas, rotulo,
                               ult and tostring(ult.clock_minutes or 0) or "x")
    local partes, meta = {}, { rotulo = rotulo, n = nsondas, minuto = ult and ult.clock_minutes,
                                segundo = ult and ult.clock_seconds, placar = ult and { ult.home_score, ult.away_score },
                                casa = casa, fora = fora, regioes = {} }
    local pos = 0
    for _, reg in ipairs({ { "p", p, 0x400 }, { "q", q, 0x800 }, { "r", r, 0x4000 } }) do
        local b = reg[2] and bytes(reg[2], reg[3])
        if b then
            partes[#partes + 1] = b
            meta.regioes[#meta.regioes + 1] = { nome = reg[1], endereco = string.format("0x%X", reg[2]),
                                                 inicio_no_arquivo = pos, tamanho = #b }
            pos = pos + #b
        end
    end
    local f = io.open(nome .. ".bin", "wb")
    if f then f:write(table.concat(partes)); f:close() end
    local g = io.open(nome .. ".json", "w")
    if g then g:write(json(meta)); g:close() end
    aviso = string.format("Sonda %d gravada (%s, %s regiões)", nsondas, rotulo, #meta.regioes)
    log("AppCarreiraAoVivo: " .. aviso)
end

-- ---------- eventos do Sider ----------
function m.set_teams(ctx, home, away)
    if ativo then
        ativo = false
        evento("fim")
        gravar("encerrada")
    end
    casa, fora = home, away
    torneio = ctx.tournament_id
end

function m.display_frame(ctx)
    quadro = quadro + 1
    if quadro % 15 ~= 0 then return end
    -- goleador: lê um instante depois do gol (como o GOGOSZ faz)
    if pend and quadro >= pend.q then
        local id = goleador()
        if id then pend.e.jogador_id = id end
        if PASTA_SONDA and m.sondar_gols then sonda("gol") end
        pend = nil
        gravar("ao_vivo")
    end
    if not (match and match.stats) then return end
    local st = match.stats()
    if type(st) ~= "table" then
        if ativo then
            ativo = false
            evento("fim")
            gravar("encerrada")
        end
        return
    end
    local novo = copiar(st)
    if not ativo then
        ativo, eventos, seq, ult, pend = true, {}, 0, novo, nil
        casa = casa or ctx.home_team
        fora = fora or ctx.away_team
        torneio = torneio or ctx.tournament_id
        evento("inicio")
        gravar("ao_vivo")
        return
    end
    local mudou = false
    local hs, as = novo.home_score or 0, novo.away_score or 0
    local hs0, as0 = ult.home_score or 0, ult.away_score or 0
    local p0 = ult.period
    ult = novo
    if hs > hs0 then
        -- o gol só vai para o arquivo depois da leitura do goleador (30 quadros, meio segundo)
        pend = { e = evento("gol", { lado = "casa", placar = { hs, as } }), q = quadro + 30 }
    end
    if as > as0 then
        -- o gol só vai para o arquivo depois da leitura do goleador (30 quadros, meio segundo)
        pend = { e = evento("gol", { lado = "fora", placar = { hs, as } }), q = quadro + 30 }
    end
    if hs < hs0 or as < as0 then evento("correcao_placar", { placar = { hs, as } }); mudou = true end
    if novo.period ~= p0 then evento("periodo", { de = p0, para = novo.period }); mudou = true end
    if pend then return end
    if mudou or (novo.clock_minutes ~= nil and novo.clock_minutes ~= (m._min or -1)) then
        m._min = novo.clock_minutes
        gravar("ao_vivo")
    end
end

function m.key_down(ctx, vkey)
    local r = ROTULOS[vkey]
    if r then sonda(r) end
end

function m.overlay_on(ctx)
    local p, q, r = cadeia()
    return string.format([[App de Carreira · partida ao vivo %s
Cadeia do goleador: %s

MODO SONDAGEM (ajuda o app a achar cartões e lesões)
Logo depois de cada lance, aperte:
[C] Cartão   [L] Lesão   [S] Substituição   [R] Referência (lance comum)

Sondas gravadas nesta sessão: %d
%s]], m.version, r and "encontrada" or "não encontrada (fora da partida?)", nsondas, aviso)
end

function m.init(ctx)
    local base = ctx.sider_dir or ".\\"
    ARQ = base .. "live_match_data.json"
    TMP = base .. "live_match_data.tmp"
    PASTA_SONDA = base .. "GOGOSZ\\AppCarreira\\sondas\\"
    m.sondar_gols = true      -- grava uma sonda em cada gol (serve de referência conhecida)
    ctx.register("set_teams", m.set_teams)
    ctx.register("display_frame", m.display_frame)
    ctx.register("overlay_on", m.overlay_on)
    ctx.register("key_down", m.key_down)
    log("AppCarreiraAoVivo " .. m.version .. ": gravando a partida em " .. ARQ)
end

return m
'''


def instalar(pasta_jogo, backup_dir, log=print):
    from .ingame import instalar_modulo
    os.makedirs(os.path.join(pasta_jogo, 'GOGOSZ', 'AppCarreira', 'sondas'), exist_ok=True)
    return instalar_modulo(pasta_jogo, backup_dir, log, nome=MODULO, conteudo=LUA)


class Monitor(threading.Thread):
    """Lê o live_match_data.json em segundo plano. Não usa bibliotecas extras (polling de mtime)."""

    def __init__(self, pasta_jogo_fn, ao_evento=None, intervalo=0.5, log=print):
        super().__init__(daemon=True)
        self.pasta_jogo_fn = pasta_jogo_fn
        self.ao_evento = ao_evento
        self.intervalo = intervalo
        self.log = log
        self.dados = None
        self.lido_em = 0
        self._marca = None
        self._seq = 0
        self._lock = threading.Lock()
        self.parar = threading.Event()
        self.jogadores = {}      # id -> {'nome': ...} (o app preenche com o arquivo de elencos)

    def caminho(self):
        p = self.pasta_jogo_fn()
        return os.path.join(p, ARQUIVO) if p else None

    def _ler(self, arq):
        for _ in range(4):           # o jogo pode estar trocando o arquivo neste instante
            try:
                with open(arq, encoding='utf-8', errors='replace') as f:
                    return json.loads(f.read())
            except FileNotFoundError:
                time.sleep(0.05)
            except (OSError, ValueError):
                time.sleep(0.08)
        return None

    def run(self):
        while not self.parar.is_set():
            try:
                arq = self.caminho()
                if arq and os.path.exists(arq):
                    s = os.stat(arq)
                    marca = (s.st_mtime_ns, s.st_size)
                    if marca != self._marca:
                        d = self._ler(arq)
                        if d is not None:
                            self._marca = marca
                            self._atualizar(d)
            except Exception as e:      # nunca derruba o app
                self.log('ao vivo:', e)
            self.parar.wait(self.intervalo)

    def _atualizar(self, d):
        with self._lock:
            ant = self.dados
            self.dados = d
            self.lido_em = time.time()
        evs = d.get('eventos') or []
        # partida nova: a sequência recomeça
        if ant is None or (d.get('casa'), d.get('fora')) != (ant.get('casa'), ant.get('fora')) or \
                (evs and evs[0].get('tipo') == 'inicio' and (d.get('seq') or 0) < self._seq):
            self._seq = 0
        novos = [e for e in evs if (e.get('seq') or 0) > self._seq]
        if novos:
            self._seq = max(e.get('seq') or 0 for e in novos)
            if self.ao_evento:
                try:
                    self.ao_evento(novos, d)
                except Exception as e:
                    self.log('ao vivo (evento):', e)

    def estado(self, nomes=None):
        """Resumo para a interface. 'ativo' só se o arquivo foi atualizado há pouco."""
        with self._lock:
            d = dict(self.dados or {})
            idade = time.time() - self.lido_em if self.lido_em else None
        if not d:
            return {'instalado': True, 'ativo': False}
        nm = lambda i: (nomes or {}).get(i, f'Time {i}') if i is not None else '—'
        # o minuto do jogo anda a cada ~6 s reais: 90 s sem gravação = jogo pausado ou encerrado
        ativo = d.get('status') == 'ao_vivo' and idade is not None and idade < 90
        evs = [dict(e) for e in (d.get('eventos') or []) if e.get('tipo') in ('gol', 'periodo', 'fim')]
        for e in evs:
            if e.get('jogador_id'):
                e['jogador'] = (self.jogadores or {}).get(e['jogador_id'], {}).get('nome') or f"Jogador {e['jogador_id']}"
        return {'instalado': True, 'ativo': ativo, 'status': d.get('status'), 'pausado': d.get('status') == 'ao_vivo' and not ativo,
                'casa': d.get('casa'), 'fora': d.get('fora'), 'casa_nome': nm(d.get('casa')), 'fora_nome': nm(d.get('fora')),
                'placar': d.get('placar'), 'periodo': d.get('periodo'), 'minuto': d.get('minuto'), 'segundo': d.get('segundo'),
                'eventos': evs[-20:], 'campos': sorted((d.get('campos') or {}).keys()), 'idade': idade,
                'sondas': d.get('sondas') or 0}
