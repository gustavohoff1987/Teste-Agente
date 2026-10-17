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

## Validação e estado da execução

Primeira etapa validada: 24 testes de compatibilidade aprovados; 48 testes direcionados de
conversa/sessão/documentação/governança e seis testes adversariais adicionais aprovados;
**12 jornadas completas aprovadas**, incluindo a nova investigação sintética e Brasil real.
Inspeção visual das capturas em desktop e 390 px confirmou a composição dentro dos painéis.
A jornada usa escolha direta para Distribuição: o pedido composto em texto não confirmou essa
operação no modo offline da baseline, e a tentativa de repetir densidade foi corretamente
reutilizada sem chamada ao motor. Não se alterou interpretação conversacional para contornar isso.

Validação completa, testes adversariais adicionais, commits e estado final serão registrados
após a execução. Este registro intermediário não declara aceite integral.
