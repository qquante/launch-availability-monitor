# twice.fun — investigação para monitor Python

Data: 2026-09-13. Escopo concluído: consultas HTTP públicas e leitura dos cinco scripts referenciados no HTML. Monitor ainda não implementado nem iniciado.

## Resultado

Nenhum CA de token lançado foi identificado nas fontes públicas examinadas. Isso não prova ausência de lançamentos on-chain ou de projetos privados. A versão examinada não conecta a lista Explore a um feed público de tokens.

## HTTP verificado

| URL | Status | Resultado |
| --- | --- | --- |
| https://twice.fun/ | 200 HTML | `NO CA LIVE YET`, contêiner Explore vazio e cinco scripts. |
| https://twice.fun/api/deployment | 200 JSON | `enabled:false`, `launcherEnabled:true`, mensagem `Public Pons + PumpSwap launches are available.` |
| https://twice.fun/api/config | 200 JSON | Configuração Pons, Pump e funding; endereços de infraestrutura. |
| https://twice.fun/api/auth/session | 200 JSON | `authenticated:false`, `account:null`, `expiresAt:null`. |
| https://twice.fun/api/launches | 401 JSON | `Sign in with your wallet to use your launch records.` |

HTML e essas quatro respostas de API apresentaram `Cache-Control: no-store`. Não houve teste de carga ou limites de requisição.

## Frontend

- `app.js?v=4`: `const markets=[]`; `renderMarkets()` mostra a lista vazia. Sem fetch, polling, EventSource ou conexão WebSocket. Não foi encontrada alimentação de `markets` pelos demais scripts.
- `launch-client.js?v=2`: wrapper `ge(path, method="GET", body, headers)` chama `fetch('/api' + path)` e interpreta JSON. Consulta `/deployment` ao iniciar; `/config` é usada pelo fluxo de criação.
- `connection-flow.js?v=1`: UI de carteiras/criação usando `window.twiceWalletBridge`.
- `deploy-design.js?v=1`: apresentação do fluxo de lançamento.
- `scene.js?v=2`: apresentação visual; nenhuma fonte de token identificada.
- Mensagens de WebSocket nos bundles são de dependências Solana; não demonstram um feed público de tokens.
- O fluxo híbrido consulta seu projeto aproximadamente a cada 8 segundos na fase `launching`. Não atualiza a lista pública Explore.

## Rotas encontradas estaticamente

Somente as quatro APIs da tabela HTTP foram consultadas. A existência, resposta e autorização das demais rotas não foram verificadas no backend.

| Família | Uso no cliente |
| --- | --- |
| `/api/auth/{challenge,verify,logout}` | Login por assinatura e logout. |
| `/api/launches` | GET dos próprios registros; POST de plano. |
| `/api/launches/{id}` | Detalhe de projeto. |
| `/api/launches/{id}/setup` e `/setup/automatic` | Configuração/orçamento de MM. |
| `/api/funding-quote`, `/api/launch-estimate` | Estimativas por POST. |
| `/api/hybrid/launches` | Criação de fluxo híbrido por POST. |
| `/api/launches/{id}/hybrid` | Estado híbrido; ações anexas quote/review/accept/prepare/arm/verify/solana-wallet. |
| `/api/launches/{id}/{platform}/...` | Preparação, recuperação e submissão Pons/Pump. |
| `/api/launches/{id}/pool`, `/api/pool-intents/...` | Fundos, inventário e intenções de operação. |
| `/api/admin/...` | Custody, pools, MM e liquidez; não consultadas. |
| `/api/test-launch...` | Teste privado identificado no bundle; não consultado. |

Nenhuma rota de criação, assinatura, armamento, depósito ou broadcast foi executada. Um monitor de leitura não deve chamar ações arm/attach/stage/submit/dispatch/verify.

## Baseline de infraestrutura

| Endereço | Campo e significado declarado pela API |
| --- | --- |
| `0x7eD598BcEf8bd9Edd8C97A195C6d13f40801EC7e` | `pons.factory`, `chainId:4663`; não é evidência de token novo. |
| `6EF8rrecthR5Dkzon8Nwu78hRvfCKubJ14M5uBEwF6P` | `pump.program`, `network:Solana mainnet-beta`; não é mint de token novo. |

O cliente usa chain ID `0x1237` (=4663), RPC `https://rpc.mainnet.chain.robinhood.com` e explorer `https://robinhoodchain.blockscout.com`. Valores observados no site, sem verificação independente on-chain.

Os bundles contêm IDs de programas Solana de sistema, sysvars, loaders, stake, vote e compute budget. A regex ampla também captura `currentAuthorityDerivedKeyBasePubkey`, um identificador de código. Regex isolada não confirma endereço ou token.

## Campos relevantes

- Fluxo anterior: `launch.legs[].platform`, `.status`, `.token`, `.txHash`, `.prepared.predictedToken`.
- `prepared.predictedToken` é endereço previsto e não comprova deployment.
- `.token` é usado em links de token; `.txHash` em links de transação. Estados incluem prepared/pending/confirmed/failed/expired.
- Fluxo híbrido: `launchMethod === 'pons_pumpswap'`, `flow.hybrid`, estado `pons`, `markets.pump`, operações `seed_buy`, `sol_mint`, `sol_allocate`, `sol_pool`, `sol_prepare`.
- Inventário/liquidez contém `position.token`, endereço de reserva, `pool` e `lpMint`: são entidades diferentes.
- Esses campos foram observados no código consumidor. Não há resposta real de projeto/token para validar seu schema completo.

## Divergências importantes

- HTML mistura preview com instruções de operações mainnet.
- `/deployment`: `launcherEnabled:true`, mas `enabled:false`.
- `/config.funding`: `executionEnabled:false`, `depositsEnabled:false`, `deploymentPaused:true`, `launchReviewEnabled:false`, `launchRolloutEnabled:false`.
- O cliente contém criação direta de mint/pool PumpSwap, enquanto `/config.pump` descreve Pump.fun/Token-2022. Monitorar só o programa Pump.fun não garante cobertura do fluxo híbrido.

Esses sinais não demonstram execução real de lançamentos nem permitem concluir que todos os fluxos estejam desativados.

## Base proposta para implementação

1. Polling HTTP do HTML, `/api/deployment` e `/api/config`; não tratar `/api/launches` como feed público.
2. Descobrir scripts/links pelo HTML atual e comparar conteúdo/hash, mesmo se URL e `?v=` não mudarem.
3. Extrair candidatos de texto, atributos, links e JSON. Reexaminar scripts quando mudarem e descobrir futuras APIs a partir do frontend.
4. Separar eventos: endereço novo, token/ticker novo, alteração de aviso/configuração, mudança de API/interface e erro operacional.
5. Preservar endereço completo, case, contexto, URL/campo e horário observado UTC. Deduplicar EVM normalizando case; Solana preserva case.
6. Persistir baseline e eventos para não duplicar após restart. Registrar infraestrutura inicial sem anunciá-la como novo token.
7. Validar EVM como 20 bytes e Solana com base58 decodificada em 32 bytes. Distinguir hashes de transação, carteiras, programas, pools, LP mints e token mints.
8. Classificar candidato publicado, endereço previsto e token confirmado separadamente. Confirmação on-chain exige consultas adicionais de leitura na rede conhecida.
9. Usar timeout, backoff, Retry-After, limites de download, logs e alerta de perda de cobertura. Latência depende do polling e da publicação no site.
10. Destino de alerta ainda não definido. Nenhuma integração Telegram/Discord/webhook ou serviço persistente foi criada.

## Validação e limites

Leituras HTTP reais e análise estática concluídas. Navegador automatizado indisponível por erro `apply deny-read ACLs` do Windows: sem DOM executado ou captura de tráfego de navegador. Backend, APIs privadas e estado on-chain não auditados. Sem fixture positiva de lançamento real.

Evidências locais: HTML, cinco scripts, quatro respostas JSON e manifesto SHA-256. O manifesto comprova integridade local, não completude de APIs.

Próximo passo: implementar o monitor Python e validar detecção/deduplicação com fixtures sintéticas e disponibilidade com smoke HTTP real.
