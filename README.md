# Carreira PES 21 — Patrocínios

App de carreira administrativa para o **PES 2021 (GOGOSZ Patch Conmebol)**, de uso pessoal e offline.

- Lê o save do Master League (data, dinheiro, resultados) sempre que o jogo salva.
- Simula o mercado de patrocínio: ofertas, negociação com cláusulas, contratos, rescisões.
- Coloca os logos nos uniformes do clube (via kitserver do Sider) e o dinheiro no caixa do jogo.

Este repositório guarda só o código. Logos, uniformes base, saves e o histórico da carreira ficam
apenas no computador (pasta `data/`).

## Atualização
O app verifica `versao.txt` neste repositório e, quando há versão nova, mostra o botão **Atualizar**.
Só os arquivos de código são trocados; a versão anterior fica guardada em `data/versoes/`.
