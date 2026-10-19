# Contexto operacional — twice.fun

## Pedido vigente

Monitor Python local, dashboard visível e requisições com intervalo alvo de 1 segundo. Avisar quando /api/deployment.enabled passar a true e quando surgir token ou CA EVM/Solana nas fontes públicas / Explore. Alarme Windows: 8 bipes de 888 Hz, 888 ms cada, 120 ms entre eles. O usuário escolheu dashboard + beep, sem integração de mensagens externa.

## Entrega em 2026-09-13

Implementados monitor.py, twice_monitor/core.py, twice_monitor/service.py e dashboard.html. Processo iniciado por Start-Monitor.ps1 em segundo plano; dashboard em http://127.0.0.1:8888. Identidade/PID corrente e heartbeat ficam em runtime/process.json e runtime/status.json; não assumir PID fixo.

Consultas HTTP por fonte em workers independentes, renderização do Explore e painel com alvo de 1 segundo. Sem sobreposição por fonte; fonte lenta/429 respeita timeout e Retry-After. Novos scripts são descobertos pelo HTML, novas APIs de leitura por GETs anônimos reais do frontend. Endereços persistidos/deduplicados por SQLite, com baseline da investigação anterior.

## Validação real

- 15 testes unitários passaram, cobrindo enabled versus launcherEnabled, transições e reinício, endereço EVM versus tx hash, Solana/base58, ausência de falsos alertas com baseline real, token sem CA, mudança de layout, deduplicação, entrega persistente e oito chamadas Beep(888,888).
- Dashboard testado via Playwright/Edge: sem erros JavaScript e sem overflow horizontal em viewport de 390px.
- Capturas desktop/mobile em runtime/dashboard-desktop.png e runtime/dashboard-mobile.png; captura desktop inspecionada.
- Botão de teste gerou somente evento TESTE; sequência real no Windows concluiu com count=8, frequency_hz=888, duration_ms=888. Teste marcado como visto; preservado no histórico.
- Smoke live detalhado em runtime/live-validation.json. Na janela de validação, deployment/HTML/scripts avançaram 11 consultas em cerca de 11 segundos; config avançou 9 devido à latência da fonte. DOM em torno de 730ms.
- Às 20:55:26 UTC da validação: enabled=false, launcherEnabled=true, All/Fresh/Saved=0; nenhum token live usado como fixture positiva.

## Limites e operação

Saved pertence à sessão pessoal; o monitor usa browser isolado e cobre os tokens públicos de All/Fresh. CAs detectados são candidatos publicados, não confirmação on-chain. Sem carteira/autenticação/transação. Não há startup automático do Windows instalado. Monitor depende do PC ligado/rede; segue ativo ao fechar o dashboard.

Status: python monitor.py status
Parar: python monitor.py stop
Reabrir/iniciar: .\Start-Monitor.ps1
Testar áudio: python monitor.py test-beep

Nenhum trabalho de implementação obrigatório ficou pendente. Próximo evento esperado é uma alteração real no site; verificar runtime/status.json e o dashboard antes de reportar estado live.

## Parada solicitada pelo usuário

Em 2026-09-13T22:18:06.234+00:00, todos os componentes deste monitor foram encerrados a pedido do usuário: workers HTTP, navegador de coleta, áudio e servidor do dashboard. Verificado: processo Python e driver Playwright ausentes, porta 8888 sem listener e heartbeat running=false. runtime/stop.request permanece como indicação de parada explícita. Não reiniciar sem novo pedido do usuário.
