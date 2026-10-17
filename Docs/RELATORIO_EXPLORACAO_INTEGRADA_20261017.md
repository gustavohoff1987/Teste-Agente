# Análise exploratória integrada — execução de 17/10/2026

## Objetivo e fronteiras

Incrementar a investigação territorial contínua por composição da apresentação existente,
preservando motores, métodos, dados, contratos, privacidade, histórico e conversação.
Branch exclusiva: `feat/novos-blocos-incrementais`. Sem branch nova, merge, reset, rebase ou push.

## Baseline efetivamente verificada

- HEAD inicial: `fe5dac336394223f43af9bc7a3eac38a080c8a69`; árvore inicialmente limpa, sem arquivos
  modificados ou não rastreados. Remoto confirmado pelo conector GitHub no mesmo SHA; Git HTTPS
  local apresentou falha de credenciais Schannel. Referência local de acompanhamento coincidente.
- `94b8c59`, `8457f41` e `be2f6b9` são ancestrais. Catálogo PT, continuidade, consciência de
  preparação/sessão e conversa ancorada foram inspecionados e exercitados na baseline.
- Backend: **481 aprovados, zero pulados**, com `PYTHONUTF8=1` e `ADT_REAL_DATA_DIR` na raiz.
  Tempo: 578,25 s. A tentativa anterior sem essas variáveis teve 451 aprovados, 29 pulados e
  uma falha no teste de governança por leitura CP1252; nenhum teste foi alterado para corrigi-la.
- `npm ci` e `npm run build`: aprovados. O Vite local mantinha `esbuild.exe` aberto; foi reiniciado
  para permitir a instalação. Foi restaurado em `127.0.0.1`; a restauração em `0.0.0.0` foi
  rejeitada pela revisão automática por exposição à rede. Build requer execução fora da restrição
  de leitura de diretórios ancestrais do sandbox Windows.
- Dez jornadas originais aprovadas, incluindo Brasil versionado, transporte Gemini simulado,
  filtros, mapas, séries e volume de 180 territórios. Nenhuma chamada ao provedor real.
- Governança aprovada em UTF-8; integridade Brasil `verificada`.
- [Registro de integridade](INTEGRIDADE_EXPLORACAO_20261017.json): SHA-256 de 38 arquivos
  protegidos e identidades AST de 226 funções/classes. Inclui todo backend de produto,
  dados, manifesto, SPEC, catálogo e workflow. A comparação durante a implementação não
  encontrou alteração nesses arquivos nem nas funções/classes.

## Investigação técnica e contratos

`POST /api/analyze` executa pré-exame e `compute`, que delega às operações determinísticas e
acrescenta representação, universo, indicadores, avaliabilidade e notas. A rota acrescenta UUID,
data/hora, hash da base, chave da execução e referência de sessão. `App` conserva resultados e
snapshots da preparação; seu reuso exige chave exata. Mapas, gráficos e tabelas utilizam
`metadata.representacao`, sem recálculo. Exportações são CSV, JSON e impressão existentes.

`SessionStore` verifica referências pelo token da sessão e fingerprint; `AnalysisAssistant`
envia somente a referência do resultado em exibição junto ao contexto já governado. A sessão
tem 1.800 segundos sem interação efetiva; limites e ausência de persistência não mudam.

Aplicam-se CAP-REP-04, CFG-REP, RQ-REP-05/06/15, RQ-RES-11, INV-09 e as regras conversacionais
vigentes. O CONCEPT não está presente como arquivo no checkout; suas referências foram
consultadas na SPEC, sem reconstruí-lo nem declarar leitura direta inexistente. SPEC e catálogo
permaneceram intactos. A distinção normativa de todos os motivos de não vigência segue a baseline;
o incremento não reimplementa o ciclo completo FN/CFG descrito na SPEC.

## Arquitetura implementada

- `InvestigationOverview`: visão acumulada paginada, abertura de etapas e identidade legível.
- `investigation.ts`: identidade e gate conservador de destaque, sem comparações analíticas.
- `InvestigationViewState`: apenas controles visuais por ID, sem duplicar linhas do resultado.
- `App`: histórico original e uma representação detalhada montada; expansão/recolhimento,
  mensagens de ausência/limite e transferência explícita de seleção.
- Reutilizados: `PreviousAnalyses`, `ResultWorkspace`, `ResultTable`, `DistributionResults`,
  `CriteriaResults`, `TerritoryMap`, gráficos, preparação, exportações e `AnalysisAssistant`.
- Nenhum framework, serviço, banco, LLM ou dependência adicionado. Backend de produto intacto.

O comportamento está descrito em [Análise exploratória integrada](ANALISE_EXPLORATORIA_INTEGRADA.md).
As diferenças de operação, indicador e parâmetros ficam explícitas; destaque não autoriza
comparação de valores. Recortes diferentes continuam consultáveis de maneira independente.

## Funcionalidades entregues e preservadas

As etapas A a E foram implementadas na mesma execução de desenvolvimento. A visão geral mantém
as etapas concluídas, distingue a etapa em exibição e permite abrir contexto e navegar. Uma única
representação detalhada oferece aprofundamento, expansão/recolhimento, indicadores, tabelas,
distribuições, gráficos, séries, mapas, distâncias, recortes e notas conforme a operação existente.
O resultado anterior continua visível durante a execução e após uma falha de transporte.

Cada resultado lembra seus filtros, seleção, indicador, aba, ordenação e páginas. A transferência
explícita entre dimensões compatíveis leva somente IDs; seleção visual, filtro e preparação são
estados distintos. As confirmações metodológicas continuam necessárias para executar uma comparação.
Mudanças na preparação não reescrevem resultados anteriores. O histórico original permanece
acessível e a reabertura não requer nova chamada a `/api/analyze`.

A conversa acompanha o resultado aberto com a referência já resolvida pelo servidor. A jornada
verifica `BACKEND_VERIFIED_RESULT` e o ID exato após reabrir uma análise. Nenhum valor visual é
convertido em fonte de verdade, e não se acrescentou interpretação ao Gemini. Sua configuração,
minimização de dados e limites permaneceram intactos.

Estados vazios, carregamento, erro, ausência de linhas, limitação de referência conversacional e
descarte da sessão têm mensagens explícitas. Após encerramento ou indisponibilidade/expiração,
um marcador de motivo sem dados nem token explica que a investigação anterior foi descartada;
o próximo aceite remove o marcador. O limite de 64 referências/32 MiB por sessão e o prazo de
1.800 segundos não mudaram. Um resultado que excede o registro do servidor continua consultável
e exportável na aba, sem referência conversacional recuperável.

Preservados por revisão de código e regressão: operações, pré-exame, validações, agregação,
sobreposição, comparação, distâncias, séries, mapas, filtros, exportações CSV/JSON/impressão,
histórico, continuidade conversacional e isolamento. Não houve exclusão de função, dependência
ou teste, nem alteração nos motores e dados. A impressão inclui o resultado mesmo quando
recolhido na tela.

## Validação executada

| Verificação | Baseline | Entrega |
|---|---|---|
| Backend completo, incluindo dados reais | 481 aprovados, zero pulados | 487 aprovados, zero pulados; 460,09 s |
| Compatibilidade do frontend | Testes novos neste incremento | 24 aprovados, zero pulados |
| Instalação/build | `npm ci` e build aprovados | TypeScript e Vite aprovados; `prebuild` roda os 24 testes |
| Jornadas completas de navegador | Dez aprovadas | 12 aprovadas na primeira etapa e na repetição final |
| Dados Brasil | Integridade verificada | Integridade verificada, mesmos hashes e versão |
| Arquivos protegidos e identidades AST | 38 arquivos; 226 funções/classes | Zero divergências |
| Governança | Aprovada | Aprovada, incluindo os dois commits de produto e o registro das jornadas no CI |

Comandos executados em PowerShell, com `PYTHONUTF8=1`; no pytest também
`ADT_REAL_DATA_DIR=C:\Users\User\Desktop\Github\Teste-Agente`:

```text
python -m pytest -q -rs                       (em backend/)
npm ci                                      (em frontend/, baseline)
npm run build                               (em frontend/; inclui npm test)
python backend/tests/run_ui_checks.py
python backend/brazil_data.py diagnostico
python .github/scripts/verificar_governanca.py
python .local/integrity_exploration.py
git diff --check
```

Os novos testes de frontend executam o módulo TypeScript real usando o compilador já instalado.
As jornadas utilizam navegador Chrome headless e API/motor reais; bloqueiam rede externa. O
transporte Gemini simulado fica restrito às suítes que já o declaravam. Não se substituiu cálculo
ou validação por resposta fabricada. A indisponibilidade de rede é injetada somente para verificar
o tratamento de erro. A verificação durante carregamento segura o transporte e depois o libera
para o motor real.

Os seis novos testes em `test_investigation_session.py` cobrem alternância de referência sem
cálculo ou chamada ao provedor, 65 cálculos e preservação das primeiras 64 referências, oito
requisições concorrentes com IDs distintos, isolamento entre sessões, leitura sem renovação
do prazo, expiração, adulteração, revisão obsoleta e tentativa de obter relação não calculada.
Os 24 testes de frontend cobrem identidade, fonte, versão/hash, método, campos, período, categoria,
unidade, duplicatas, sobreposição, recorte, IDs ambíguos, validade e representação ausentes,
coortes/agregados/séries e camadas geográficas diferentes.

### Jornadas exploratórias e alcance da evidência

Resultado da execução final do executor completo:

| Suíte | Roteiro | Resultado | Tempo |
|---|---|---|---|
| conversa | `ui_conversational_smoke.py` | Aprovado | 14 s |
| bloco1 | `ui_block1_smoke.py` | Aprovado | 29 s |
| bloco1 | `ui_block1_regression.py` | Aprovado | 8 s |
| bloco1 | `ui_nearest_smoke.py` | Aprovado | 14 s |
| bloco1 | `ui_criteria_smoke.py` | Aprovado | 21 s |
| bloco1 | `ui_map_smoke.py` | Aprovado | 33 s |
| bloco1 | `ui_visibility_diagnostic.py` | Aprovado | 34 s |
| bloco1 | `ui_investigation.py` | Aprovado | 41 s |
| gemini-simulado | `ui_block1_integration.py` | Aprovado | 5 s |
| gemini-simulado | `ui_semantic_continuity.py` | Aprovado | 13 s |
| base-versionada | `ui_block1_smoke.py` | Aprovado | 74 s |
| base-versionada | `ui_investigation.py` | Aprovado | 60 s |

- `ui_investigation.py`, catálogo sintético: nove resultados abertos na investigação, densidade,
  quintis, comparação e distância; filtros e seleção preservados; destaque no mapa; duas páginas
  de etapas; recorte e período incompatíveis; parâmetros novos sem recálculo dos anteriores;
  leitura conversacional da referência ativa; CSV/JSON existentes e impressão recolhida;
  falha de rede sem perda do histórico; limite real de referências preenchido pela API;
  troca de fonte, perda da sessão no servidor e encerramento voluntário.
- A mesma jornada com a base versionada: quatro resultados, 62 municípios do Amazonas,
  quintis, seleção no mapa, comparação com confirmação e bloqueio entre períodos/recortes.
- As dez jornadas anteriores permanecem no executor, incluindo CSV/XLSX, seleção, pré-exame,
  referência mais próxima, critérios, mapas, evolução temporal, agregação, exportações e
  consciência de contexto com transporte semântico simulado.
- Volume: regressão visual existente com 180 territórios; novo histórico paginado; 65 resultados
  no registro de sessão; aritmética independente dos 122.534 registros/5.570 municípios e
  geometria das 22 competências na suíte real de backend. Isso não constitui benchmark para
  quantidade ilimitada de resultados na aba.
- Responsividade verificada em 1.360, 768 e 390 px, sem extravasamento horizontal. Capturas
  desktop e móvel inspecionadas visualmente; controles e detalhes permanecem nos painéis roláveis.

As tentativas iniciais da jornada ampliada revelaram dois seletores incorretos no teste novo:
referência espacial buscada sem o código exibido e texto de importação inicial procurado após
troca de fonte. A inspeção mostrou o produto cumprindo o contrato. Corrigiram-se os seletores
para o rótulo territorial do universo e `current-source`, mantendo as mesmas verificações.
Nenhum teste preexistente foi afrouxado. A regressão de impressão causada pelo recolhimento foi
corrigida antes do primeiro commit e exercitada com mídia `print` na jornada.

A jornada usa escolha direta para Distribuição: o pedido composto em texto não confirmou essa
operação no modo offline da baseline, e repetir densidade foi corretamente reutilizado sem
chamada ao motor. Não se alterou interpretação conversacional para contornar esse comportamento.

## Integridade além da contagem de testes

A comparação byte a byte por SHA-256 abrange todo backend de produto, bases, manifesto, camada
geográfica, SPEC, catálogo documental e arquivos `.github/`. As identidades AST complementam
essa verificação. Os hashes nacionais e municipais e a versão governada permanecem os do
registro inicial. O diff do incremento em `backend/` contém apenas testes e seu executor.

A revisão do diff confirmou a reutilização dos renderizadores e exportadores existentes,
manutenção das rotas e ausência de alteração de contratos analíticos. As jornadas confrontam
JSON exportado, IDs selecionados, referências do chat e resultados da API; contam chamadas ao
motor para comprovar navegação sem recálculo. A suíte real confere os originais antes e depois.
Essas evidências, além dos testes unitários, sustentam a preservação constatada nesta entrega.

## Limites explícitos

- Não há login, persistência permanente, restauração após recarga ou nova política de retenção.
- O enquadramento manual do mapa volta à extensão inicial quando a representação é remontada;
  filtros, seleção e indicador do resultado são preservados.
- Relações entre resultados incompatíveis, harmonização, inferência e novos cálculos pelo chat
  não foram implementados, conforme as fronteiras da missão. Agregados, coortes e séries
  continuam consultáveis, sem transferência de seleção individual entre etapas.
- A conversa sobre resultados preserva a cobertura governada da baseline; o incremento não
  habilita explicações livres de operações que ainda não têm composição documental autorizada.
- O CONCEPT não está disponível no checkout. Não há comprovação de inspeção direta desse arquivo;
  os contratos acessíveis foram conferidos na SPEC e na documentação vigente.
- Permanecem os avisos preexistentes de bundle Vite acima de 500 kB, depreciação Starlette/httpx
  e auditoria npm (sete ocorrências na instalação). Não se alteraram dependências fora do escopo.
- CI remoto não foi executado: não houve push. As mesmas suítes foram executadas localmente.

## Commits e estado da branch

- `819b1db` — investigação progressiva, identidade, controles por resultado, coordenação visual,
  testes e documentação; registrado após build, verificações direcionadas e 12 jornadas.
- `1765f97` — disponibilidade da sessão, descrição leve do histórico, testes ampliados e registro
  de validação; registrado após aprovação das 12 jornadas finais. HEAD de produto completo:
  `1765f971e5a646f1284819d9c5616cf4a5a1d0ed`.
- Este fechamento documental, `docs: concluir rastreabilidade da investigação integrada`, registra
  os hashes e o estado final, sem alteração de produto.

Branch mantida em `feat/novos-blocos-incrementais`; nenhum merge, reset, rebase, descarte ou push.
São três commits locais sobre a referência de acompanhamento `origin/feat/novos-blocos-incrementais`
utilizada na baseline (`fe5dac3`), sem commits atrás dela. A árvore rastreada termina limpa;
logs, capturas e registros locais ignorados em `.local/` são preservados. Não havia arquivo
não rastreado preexistente a incorporar ou descartar. A sequência pode ser identificada com
`git log --oneline fe5dac3..HEAD`.

## Aceite da entrega local

A implementação e a validação das etapas A a F estão concluídas. Estão implementados o painel
progressivo, a navegação e reabertura, o histórico preservado, os controles por resultado, a
coordenação visual condicionada à identidade, os estados de disponibilidade e a integração
conversacional por referência verificada. Não ficou etapa funcional deste incremento parcialmente
implementada. As capacidades não implementadas e as limitações da baseline estão discriminadas
acima, sem atribuir à interface novas capacidades analíticas.

Os critérios de preservação foram confrontados com código, hashes, testes e comportamento
observável; não foram identificadas regressões nessas verificações. Código, testes, guia e
registro de comportamento acompanham cada commit de produto. Publicação e CI remoto aguardam
autorização para push, conforme solicitado.
