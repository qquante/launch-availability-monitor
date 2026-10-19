> Historical project notes. Paths, operational status, badges and test claims below are retained as archival reference and have not all been revalidated. Use the root README and docs/REVIEW.md for this review snapshot.

# twice.fun — monitor local

Dashboard: http://127.0.0.1:8888

## Cobertura

- enabled estritamente booleano: alerta na primeira observação true e em cada transição observada OFF → ON. launcherEnabled:true sozinho não dispara.
- All launches e Fresh faces renderizados: token novo mesmo sem CA.
- Endereços EVM/Solana novos no HTML, scripts, DOM e JSON público.
- Saved é seleção pessoal: a sessão isolada não usa os favoritos/carteiras do navegador do usuário.
- Mudança no aviso principal e falhas de cobertura aparecem no painel.

## Intervalos e áudio

Cada fonte HTTP tem worker próprio, com intervalo alvo de **1 segundo entre inícios**, sem consultas sobrepostas na mesma fonte. Scripts descobertos pelo HTML também são consultados a cada segundo. ETag/Last-Modified são usados quando disponíveis. Fontes lentas não bloqueiam deployment.

O navegador renderiza com intervalo alvo de 1 segundo, usando respostas HTTP recentes já obtidas para não baixar os bundles duas vezes. APIs são descobertas por GETs reais da página pública. Escritas, rotas administrativas/autenticação, recursos externos e visual decorativo são bloqueados.

Latência real e último sucesso aparecem no dashboard. Timeouts, 429 e Retry-After aplicam backoff. Não há promessa de detecção exata em 1 segundo durante indisponibilidade/limitação.

Alarme: **8 chamadas winsound.Beep(888, 888)**, separadas por 120 ms. Eventos que chegam juntos são agrupados em uma sequência. Python toca no Windows mesmo com o dashboard fechado; volume e dispositivo dependem do sistema. Testar gera evento explicitamente TESTE, não um lançamento.

## Operação

    .\Start-Monitor.ps1
    python monitor.py status
    python monitor.py stop

Em primeiro plano:

    python monitor.py run

Teste sonoro:

    python monitor.py test-beep

Start-Monitor.ps1 abre processo sem terminal. Lock por pasta evita duas instâncias. O processo continua após fechar o dashboard; o PC precisa ficar ligado e com rede. Não há inicialização automática do Windows instalada.

## Estado e limites

- SQLite: runtime/monitor.sqlite3 — baseline, deduplicação, estado e eventos.
- Snapshot UTC: runtime/status.json.
- Logs rotativos: runtime/monitor.log; PID: runtime/process.json.
- Marcar como visto preserva o histórico.
- Som silenciado mantém alertas pendentes; são tocados em lote ao reativar.
- Encerramento durante a sequência pode fazer o áudio repetir no próximo início; eventos visuais não duplicam.
- CA detectado é candidato publicado: sintaxe/base58 não comprovam deployment, rede EVM específica ou token.
- Baseline real: research/2026-09-13-twice-fun.
- Sem carteira, chave, login, assinatura, transação, depósito ou broadcast.
- APIs privadas não monitoradas. Mudança estrutural do Explore gera falha visível.

## Dependências e testes

Python 3.14.5, requests 2.32.3, beautifulsoup4 4.13.4, Playwright 1.60.0, Edge instalado.

    python -m pip install -r requirements.txt
    python -m unittest discover -s tests -v

Testes sintéticos cobrem enabled, tokens/CAs, reinício, deduplicação e sequência sonora. Coleta live comprova só o estado observado, não um lançamento real.

Fontes: [Playwright / Edge](https://playwright.dev/python/docs/browsers) e [Python winsound.Beep](https://docs.python.org/3/library/winsound.html#winsound.Beep).
