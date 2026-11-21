# App Carreira PES 2021 · mapa rápido

Leia isto antes de abrir arquivos. Para achar uma função, rode `python3 ferramentas/indice.py <termo>`.
Ele mostra arquivo:linha de cada def/class/constante que bate, sem precisar ler os arquivos inteiros.

O usuário não programa. Responda em português, sem jargão. Uso pessoal/offline: não precisa de avisos de marca.
Depois de publicar, lembre o usuário de reiniciar o app com o botão ⏻.

## Onde está cada coisa

| Assunto | Arquivo |
|---|---|
| Servidor, leitura do save, API `/api/...`, view para a tela | `app.py` (classe App: `tick`, `ler_elenco`, `aplicar_creditos`, `view`, `carreira_view`; rotas no fim) |
| Interface (uma página: HTML+CSS+JS) | `web/index.html`. Aba Sistema: `rSistema()`; capitão/batedores: `rBola()`. Funções `rXxx()` desenham cada aba; `api()` chama o servidor. Visual vertical = bloco CSS "visual 4.0" no fim do `<style>`; o menu `#nav` fica no fim do body, fixo na LATERAL ESQUERDA (104 px, bloco CSS "4.7" no fim do `<style>`); sub-abas `.tabs2` quebram linha. |
| Ler/gravar o save (dinheiro, elenco, energia, contratos) | `core/savedata.py` (classe `Career`) e `core/pescrypt.py` (cripto) |
| Escalação/formação do plano de jogo | `core/escalacao.py` |
| Súmulas e partidas da temporada | `core/sumulas.py`, `core/campeonatos.py` |
| Ficha dos jogadores (EDIT), juniores | `core/jogadores.py` |
| Patrocínio: mercado, ofertas, contratos | `core/sim.py`, `core/presidente.py`, `core/mensagens.py` |
| Uniformes/kits, limpeza, detecção | `core/kits.py`, `core/limpeza.py`, `core/detector.py`, `core/estudio.py`, `core/times.py`, `core/ftex.py` |
| Coletiva: perguntas (só texto) | `core/coletiva_perguntas.py` |
| Coletiva: escolha das perguntas, reações | `core/gestao.py` (`coletiva_nova`, `_situacoes`, `responder`, `REACAO`) |
| Jornalistas, matérias, intros da coletiva | `core/imprensa.py` |
| Torcida, redes sociais, notícias | `core/mundo.py`, `core/vozes.py`, `core/textos.py`, `core/assessor.py` |
| Departamento médico, energia, programa de recuperação | `core/medico.py` |
| Estrutura do clube (obras), marca, gramado | `core/estrutura.py` |
| Diretoria, emprego, carreira do técnico | `core/diretoria.py`, `core/diretor.py`, `core/tecnico_carreira.py` |
| Foto/cena da coletiva | `core/tecnico.py`, `core/cena.py` |
| Visual no estádio via Sider (faixas, gramado) | `core/ingame.py` |
| Mercado: auxiliar, diretor de futebol, propostas, janelas, Europa | `core/mercado.py`; reações `core/mercado_reacoes.py` (imprensa com números) e `core/mercado_torcida.py` (torcida sem números) |
| Finanças reais dos clubes (índice de poder, caixa por janela) | `core/financas_clubes.py` + `core/clubes_financas_2025.json` |
| Comissão técnica: relatório pós-jogo, adversário, preleção, metas, base | `core/comissao.py` |
| Gestão do elenco: renovação, empréstimo, insatisfeitos, conversa, histórico | `core/gestao_elenco.py` |
| Pressão por vendas, planejamento, protestos/festa, convocação | `core/clube_eventos.py` |
| Prêmios da liga (craque da rodada, artilharia, seleção) | `core/premios.py` |
| Diagnóstico de memória do jogo via Sider (somente leitura; relatórios `memoria_*.txt` vão na cópia remota, pasta `memoria/`) | `core/memoria_jogo.py` |
| Cópia do save para o GitHub privado (análise a distância) | `core/copia_remota.py` (repo yannespza/carreira-pes21-saves: `saves/AAAA-MM-DD/HHMMSS_<arquivo>.pesz`, uma versão por gravação; na virada da semana ficam só as 2 mais recentes de cada save e o histórico do repo recomeça). Abrir/comparar/montar no /tmp/sim: `ferramentas/saves_remotos.py` |
| Aba Jogo (dia de jogo): clima/torcida no Sider, dossiê, tribunal, fadiga, viagem, bilheteria | `core/matchday.py` (force_weather.ini do StadiumServer, crowd_behavior.ini/crowd_standings.csv), `core/cidades.py` (cidade/altitude por nome), `core/dossie.py`, `core/tribunal.py`, `core/fadiga.py`, `core/forca.py` (AppCarreiraForca.lua: soma força no MATCH_INFO+0x20/+0x28 como o Dynamic_Difficulty), `core/bilheteria.py`; app: `App.matchday_atualizar`, `fadiga_atualizar`, `tribunal_dossie`; UI `rJogo()`/`JOGO_R` |
| Formações do patch (catálogo do EDIT, 628 B por time) e gravar formação | `escalacao.catalogo`, `escalacao.gravar_formacao` (tipo de gravação `formacao`, passa pelo espaço de teste); UI `escTrocarForm`, `papelZona`, `hungaro` |
| Aba História: museu permanente, hall da fama, carrascos, olheiros, análise | `core/museu.py` (state['museu']), `core/olheiros.py`; UI `rHist()`/`HIST_R` |
| IA opcional (Ollama/nuvem, JSON, 8 s, corte -5..+5) | `core/ia.py`; coletiva com resposta livre `gestao.responder_livre`, rota `/api/coletiva/livre`; config na aba Sistema |
Esses módulos são chamados em `App.mercado_processar` e `App.extras_processar`; a tela recebe `extras_view()`.
Nenhum deles grava no save (troca de clube, renovação e empréstimo esperam o teste no PC).

## O save (ML0000000X), já decriptado com `pescrypt.decrypt(raw).data`

- Dinheiro em unidades de €100. Cotação do jogo: 4,3 R$/€. Bloco de finanças: `savedata.FIN`.
- Elenco: `savedata.elenco(data, team_index)`, com registros de 8 bytes.
- **Energia** (cansaço do plano de jogo): tabela de registros de 12 bytes: `pid u32 | energia u8 (255 = ciano/100%) | marca u8 | 0 u16 | nº u32`.
  Use `savedata.energia(data, pids)`; para gravar, use `Career.definir_energia` (por padrão só sobe). ATENÇÃO (teste de 14/11): o jogo RECALCULA esse valor ao carregar (minutos do último jogo + dias de descanso) e ignora o que for gravado; por isso `medico.GRAVAR_ENERGIA = False`. A estimativa fica em `App.energia_pct`.
- Contratos: registros de 48 bytes. Use `contratos_clube`.
- Formação ativa: lista −0x1E0.
- Partidas: registros 0x254 (`sumulas`).
- Propostas de emprego ao técnico (jogo): `savedata.ofertas_tecnico` — u32 em FIN − 0x7C6D8 (14 vagas): (id do clube << 14) | código; 0xFFFFFFFF vazia.
- Uniformes: `App.kits_conferir` regrava se o patch trocar as texturas (`state['kits_arquivos']` = tamanho e data de cada variação).
- Tabela de jogadores do clube: registros 0x170 (`jogadores.juniores`).
- Detalhes completos: doc do projeto `claude/plano-de-jogo-no-save.md`.
- Estrutura do arquivo EDIT (Team-Player 284 B, plano de jogo 628 B, ficha 240 B): doc do projeto `claude/edit-file-wiki-pes2021.md`. Para procurar a tabela Team-Player num save: `ferramentas/achar_team_player.py`.

## Segurança das gravações (4.2.0) · contrato para outros modelos
Não reescreva a parte binária (`pescrypt.py`, `savedata.Career.write`, `escalacao.py`); use as funções abaixo.
- `savedata.TRAVA(caminho) -> motivo|None`: definida em `App.trava_gravacao`; bloqueia `Career.write` com partida ao vivo
  (`live_match_data.json` status `ao_vivo` < 90 s). Gravar com o PES aberto no menu é permitido e testado (vale ao recarregar).
- `Career.write(backup_dir, log, motivo)`: backup `data/backups_save/ML_<mtime>.bak` + ficha `.bak.json` (arquivo, carreira,
  data do jogo, motivos). `savedata.listar_backups`, `savedata.restaurar_backup` (guarda o atual antes). Mantém 15.
- `App.exigir_jogo_fechado(oque)`: restaurar e criar espaço de teste.
- Espaço de teste: `App.criar_slot_teste('ML0000000X')`, `voltar_slot_principal`, `no_slot_teste()`. CFG `slot_teste`,
  `slot_principal`. Ficha do app separada: nome da carreira + `TESTE_SUFIXO` (' - TESTE').
- Gravação nova ainda não testada no jogo: chame `App.gravacao_liberada('<tipo>')` (só passa no espaço de teste até
  `CFG['gravacoes_confirmadas']` ter o tipo; botão "Funcionou no jogo" → `/api/sistema/confirmar`). Tipos: `bola_parada`.
- Capitão e batedores: `escalacao.ler_bola_parada / gravar_bola_parada` (lista de escalação + 0x28: falta longa, curta,
  2ª, escanteio esq., dir., pênalti, 3 que sobem, capitão em +0x31; valores = vaga no elenco, 0xFF vazio).
- Painel pré-jogo: `App.briefing_texto/briefing_gravar` → `<pasta_jogo>\GOGOSZ\AppCarreira\briefing.txt` (texto UTF-8);
  `AppCarreiraAoVivo.lua` 1.5 mostra no `overlay_on`. Aba Sistema: `GET /api/sistema` (`App.sistema_view`).
- Ainda NÃO feito (depende de achar no save/memória): efetivar transferências/empréstimos/renovações, escrever na RAM.
- Versão: cada publicação vai direto para o PC do usuário; marque etapas concluídas com `git tag`.

## Gravações no save

Toda gravação passa por `App.aplicar_creditos()`. Ela junta as pendências e grava uma vez, com backup em `data/backups_save`:
- créditos de patrocínio;
- multas;
- `state['debitos']` (gastos do app);
- `state['energia_pend']` (só sobe);
- `state['energia_set']` (valor exato, volta de lesão).

Para criar um gasto novo, coloque um `{'valor', 'motivo', 'status': 'pendente'}` em `debitos` e chame `aplicar_creditos`.

## Fluxo de trabalho

1. **Teste** em `/tmp/sim`: copie `core/ web/ app.py` para `/tmp/sim/app/` e rode `python3 /tmp/sim/rodar.py`. Ele lê os saves de `/tmp/sim/saves/10000002/save/`. Teste a interface com playwright (`/tmp/sim/ui_*.py`).
2. **Versão**: atualize `versao.txt` e acrescente a nota em `LEIA-ME.txt`.
3. **Publicar**: faça `git commit` e `git push` em `origin` (github.com/yannespza/Carreira-PES21). O app do PC se atualiza sozinho pelo GitHub. Só os itens de `ARQUIVOS_CODIGO` em `app.py` são baixados.
4. **PC do usuário**: `F:\PES2021_GOGOZS PATCH4\App Carreira`. Saves em `C:\Users\yanne\OneDrive\Documents\GOGOSZ\eFootball PES 2021 SEASON UPDATE\10000002\save`. A carreira ativa é a do slot 7, arquivo `ML00000006`.
