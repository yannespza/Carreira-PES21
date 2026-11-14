# App Carreira PES 2021 · mapa rápido

Leia isto antes de abrir arquivos. Para achar uma função, rode `python3 ferramentas/indice.py <termo>`.
Ele mostra arquivo:linha de cada def/class/constante que bate, sem precisar ler os arquivos inteiros.

O usuário não programa. Responda em português, sem jargão. Uso pessoal/offline: não precisa de avisos de marca.
Depois de publicar, lembre o usuário de reiniciar o app com o botão ⏻.

## Onde está cada coisa

| Assunto | Arquivo |
|---|---|
| Servidor, leitura do save, API `/api/...`, view para a tela | `app.py` (classe App: `tick`, `ler_elenco`, `aplicar_creditos`, `view`, `carreira_view`; rotas no fim) |
| Interface (uma página: HTML+CSS+JS) | `web/index.html`. Funções `rXxx()` desenham cada aba; `api()` chama o servidor. |
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

## O save (ML0000000X), já decriptado com `pescrypt.decrypt(raw).data`

- Dinheiro em unidades de €100. Cotação do jogo: 4,3 R$/€. Bloco de finanças: `savedata.FIN`.
- Elenco: `savedata.elenco(data, team_index)`, com registros de 8 bytes.
- **Energia** (cansaço do plano de jogo): tabela de registros de 12 bytes: `pid u32 | energia u8 (255 = ciano/100%) | marca u8 | 0 u16 | nº u32`.
  Use `savedata.energia(data, pids)`; para gravar, use `Career.definir_energia` (por padrão só sobe). O save guarda a energia do fim do último jogo e o jogo SOMA a recuperação dos dias seguintes. A estimativa fica em `App.energia_pct`.
- Contratos: registros de 48 bytes. Use `contratos_clube`.
- Formação ativa: lista −0x1E0.
- Partidas: registros 0x254 (`sumulas`).
- Tabela de jogadores do clube: registros 0x170 (`jogadores.juniores`).
- Detalhes completos: doc do projeto `claude/plano-de-jogo-no-save.md`.

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
