"""Ponte Lua -> Python para a partida ao vivo.

O módulo AppCarreiraAoVivo.lua roda dentro do jogo (Sider) e grava live_match_data.json na pasta do jogo
sempre que algo muda: placar, período, minuto. Este módulo lê esse arquivo numa thread de fundo, por
polling barato (mtime + tamanho a cada 0,5 s), sem travar o servidor nem a interface.

O que o Sider entrega de verdade (confirmado nos módulos do GOGOSZ instalados):
- match.stats(): home_score, away_score, period, clock_minutes, clock_seconds (o placar do patch usa isso);
- ctx.home_team, ctx.away_team, ctx.tournament_id, ctx.sider_dir e o evento display_frame (todo quadro);
- io.open para gravar arquivos.
Goleador, cartões e lesões NÃO vêm da API do Sider. O Lua grava todos os campos que match.stats()
devolver ("campos"), para descobrirmos se a sua versão traz algo a mais.
"""
import os, json, time, threading

MODULO = 'AppCarreiraAoVivo.lua'
ARQUIVO = 'live_match_data.json'

LUA = r'''-- AppCarreiraAoVivo.lua (App de Carreira PES 21)
-- Ponte com o app: grava live_match_data.json na pasta do jogo quando a partida muda.
-- Não desenha nada na tela e não escreve na memória do jogo: só lê match.stats() e grava um arquivo.
local m = { version = "1.0" }

local ARQ, TMP
local quadro = 0
local ativo = false
local ult = nil
local casa, fora, torneio = nil, nil, nil
local eventos = {}
local seq = 0
local inicio = 0

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
        if #v > 0 or next(v) == nil then
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

local function gravar(status)
    if not ARQ then return end
    local dados = {
        versao = m.version, status = status, seq = seq, casa = casa, fora = fora, torneio = torneio,
        placar = ult and { ult.home_score or 0, ult.away_score or 0 } or nil,
        periodo = ult and ult.period or nil,
        minuto = ult and ult.clock_minutes or nil, segundo = ult and ult.clock_seconds or nil,
        campos = ult, eventos = eventos,
    }
    local txt = json(dados)
    -- grava num temporário e troca de nome: o app nunca lê um arquivo pela metade
    local f = io.open(TMP, "w")
    if not f then return end
    f:write(txt)
    f:close()
    local ok = pcall(function()
        os.remove(ARQ)
        assert(os.rename(TMP, ARQ))
    end)
    if not ok then
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
end

local function copiar(st)
    local c = {}
    for k, v in pairs(st) do
        local t = type(v)
        if t == "number" or t == "string" or t == "boolean" then c[k] = v end
    end
    return c
end

function m.set_teams(ctx, home, away)
    -- times definidos para uma partida nova: fecha a anterior, se ficou aberta
    -- (match.stats() pode continuar respondendo nos menus depois do apito final)
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
    if quadro % 15 ~= 0 then return end          -- umas 4 leituras por segundo bastam
    if not (match and match.stats) then return end
    local ok, st = pcall(match.stats)
    if not ok or type(st) ~= "table" then
        if ativo then                             -- saiu da partida
            ativo = false
            evento("fim")
            gravar("encerrada")
        end
        return
    end
    local novo = copiar(st)
    if not ativo then
        ativo, eventos, seq, ult = true, {}, 0, novo
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
    if hs > hs0 then evento("gol", { lado = "casa", placar = { hs, as } }); mudou = true end
    if as > as0 then evento("gol", { lado = "fora", placar = { hs, as } }); mudou = true end
    if hs < hs0 or as < as0 then evento("correcao_placar", { placar = { hs, as } }); mudou = true end
    if novo.period ~= p0 then evento("periodo", { de = p0, para = novo.period }); mudou = true end
    if mudou or (novo.clock_minutes ~= nil and novo.clock_minutes ~= (m._min or -1)) then
        m._min = novo.clock_minutes
        gravar("ao_vivo")
    end
end

function m.init(ctx)
    local base = ctx.sider_dir or ".\\"
    ARQ = base .. "live_match_data.json"
    TMP = base .. "live_match_data.tmp"
    ctx.register("set_teams", m.set_teams)
    ctx.register("display_frame", m.display_frame)
    log("AppCarreiraAoVivo: gravando a partida em " .. ARQ)
end

return m
'''


def instalar(pasta_jogo, backup_dir, log=print):
    from .ingame import instalar_modulo
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
        evs = [e for e in (d.get('eventos') or []) if e.get('tipo') in ('gol', 'periodo', 'fim')]
        return {'instalado': True, 'ativo': ativo, 'status': d.get('status'), 'pausado': d.get('status') == 'ao_vivo' and not ativo,
                'casa': d.get('casa'), 'fora': d.get('fora'), 'casa_nome': nm(d.get('casa')), 'fora_nome': nm(d.get('fora')),
                'placar': d.get('placar'), 'periodo': d.get('periodo'), 'minuto': d.get('minuto'), 'segundo': d.get('segundo'),
                'eventos': evs[-20:], 'campos': sorted((d.get('campos') or {}).keys()), 'idade': idade}
