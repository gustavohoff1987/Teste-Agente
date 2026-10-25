# Roteiros de navegador que saíram ou não rodam mais

Este README registra os roteiros de navegador que deixaram de rodar e onde a cobertura deles passou a existir (regra de
testes do `AGENTS.md`). São dois conjuntos:

1. **Os 16 roteiros do fluxo clássico, que saíram em 22/10/2026** com a página única de análise (seção seguinte). Os
   arquivos foram apagados e continuam no histórico do Git, por exemplo em
   `git show 748b3f9:backend/tests/ui_block1_smoke.py`.
2. **Os 7 roteiros anteriores ao redesenho conversacional de 12/10/2026**, movidos para esta pasta em 15/10/2026 (seção
   final). Eles não rodam.

Novos roteiros de navegador ficam em `backend/tests/` e são registrados em `backend/tests/run_ui_checks.py`. A verificação
de governança do CI recusa roteiros ativos que não rodam.

## Roteiros do fluxo clássico que saíram em 22/10/2026

Decisão do responsável pelo produto em 22/10/2026: uma página única de análise, sem as telas clássicas. Saíram da
interface o catálogo de 12 análises, a preparação (categoria, período, abrangência territorial e condições), os resultados
em abas (mapa, gráficos e tabelas), a investigação progressiva e os diagnósticos compostos. O motor (`/api/analyze` e as
capacidades) continua, com os testes do backend (pytest e dados reais). Ver `Docs/INTERFACE_CONVERSACIONAL_INTEGRADA.md`
e a entrada de 22/10/2026 em `Docs/REGISTRO_DE_COMPORTAMENTO.md`.

Os roteiros novos:
- `ui_pagina_unica.py` (suítes `bloco1` e `base-versionada`): abertura e aceite de privacidade, base do Brasil com os
  estados, Histórico e Nova análise sem recálculo, Nova sessão (CSV, foco no diálogo, falha ao encerrar, revogação), caixa
  da conversa arrastável, planilha de outro país pelo painel "Colunas", arquivo com duas abas, formato recusado e celular;
- `ui_conversa_grafico.py` (suítes `conversa`, sem provedor, e `gemini-simulado`): a conversa mudando o gráfico, o
  contexto do gráfico nos pedidos, esclarecimentos, ambiguidade em botões, pedidos de apresentação, análise anterior,
  planilha pela conversa e nada da base ao provedor;
- `ui_area_de_analise.py` (frente da área de análise): o gráfico, as famílias de análise, as funções, os Detalhes e o
  modo leve.

| Roteiro que saiu | O que cobria | O que continua no produto e onde está a cobertura | O que saiu do produto |
|---|---|---|---|
| `ui_block1_smoke.py` | Jornada do Bloco 1 (sintética e base versionada): densidade dos municípios do Amazonas pela conversa, seleção, comparação, evolução com tendência, agregação, CSV e JSON contra o motor, histórico, retomada, larguras, teclado e distâncias com a premissa da base oficial | Municípios do Amazonas e comparação pela conversa: `ui_conversa_grafico.py`. Tendência, Juntar e distância: `ui_area_de_analise.py` e pytest (`test_trend.py`, `test_painel.py`). Histórico sem recálculo, CSV em precisão integral, base versionada e 390 px: `ui_pagina_unica.py` | Preparação, lista da abrangência, "Baixar registro técnico (JSON)", "Retomar parâmetros", "Usar seleção na próxima análise" e abas de resultados |
| `ui_block1_regression.py` | CSV e XLSX importados, identificadores opacos, comparação por quantidade, retomada, troca de fonte com o histórico preservado | Planilha enviada, XLSX com duas abas e troca de fonte com o Histórico preservado: `ui_pagina_unica.py`. Identificadores `name:` de planilha: `ui_conversa_grafico.py`. Comparação por quantidade: área e pytest (`test_engine.py`) | Retomada de parâmetros e seletores de colunas da preparação |
| `ui_nearest_smoke.py` | Referência mais próxima: critério, comando da conversa, exportações, reutilização, base importada com vírgula decimal e coordenadas inválidas | Distância até o membro mais próximo da referência: `ui_area_de_analise.py` e pytest (`test_painel.py`, `test_nearest_reference.py`, `test_nearest_real_data.py`). Vírgula decimal e coordenada inválida: pytest | Cartão "Referência mais próxima", reutilização como referências ou alvos e JSON técnico |
| `ui_criteria_smoke.py` | Critérios combinados: cinco comandos da conversa, régua, exportações, histórico, celular | Condições e Ordenar: `ui_area_de_analise.py` e pytest (`test_combined_criteria.py`, `test_criteria_conversation.py`) | Construtor de critérios da preparação e "Compare esse conjunto com o anterior" |
| `ui_map_smoke.py` | Mapa, gráficos e tabela sincronizados, seleção, filtros, zoom, PNG, impressão, celular | Tabela (Detalhes) e Imprimir/PDF: `ui_area_de_analise.py`. Contrato `metadata.representacao` de `/api/analyze`: pytest (`test_representation.py`, `test_representation_real.py`) | Mapa de pontos e visualizações da tela de resultados |
| `ui_visibility_diagnostic.py` | Exploração visual, filtros e paginação dos gráficos clássicos | Tabela em páginas: `ui_area_de_analise.py` | Gráficos da tela de resultados |
| `ui_investigation.py` | Investigação progressiva: vários resultados, reabertura, filtros por resultado, destaque entre resultados, falha de transporte, limite de referências, perda da sessão | Reabertura sem recálculo: `ui_pagina_unica.py`. Perda da sessão (410): `ui_pagina_unica.py` e pytest (`test_conversation_session.py`, `test_investigation_session.py`) | Diagnósticos compostos, destaque entre resultados e memória de filtros por resultado |
| `ui_integrated_workspace.py` | Sessões, análise independente e composição, navegação, teclado, CSV e JSON, quatro larguras, falha ao encerrar e revogação | Aceite de privacidade, diálogo de Nova sessão (CSV em precisão integral, foco), falha ao encerrar, revogação da sessão e Histórico: `ui_pagina_unica.py` | "Início", "Resultados", análise independente e composição e JSON técnico do resultado |
| `ui_sem_confirmacoes.py` | D1 (nenhuma confirmação de campo) nas 12 análises, base oficial e importada; K1 (nenhuma premissa com `false`) | D1 na planilha enviada (sugestão no topo, lista vazia até a escolha, sem caixas de confirmação): `ui_pagina_unica.py`. D1 e K1 na API: pytest (`test_sem_confirmacoes.py`). A página não envia premissas com `false` | Preparação das 12 análises |
| `ui_territorial_scope.py` | Lista da abrangência (Brasil, estados e municípios), espacial com competência, níveis na densidade, taxa nacional, ranking de estados, "Limpar seleção" | Estados como porta de entrada: `ui_pagina_unica.py` e `ui_area_de_analise.py`. Níveis nunca somados: área e pytest (`test_territorial_levels.py`, `test_levels_real_data.py`) | Caixa "Abrangência territorial" e ranking só de estados e Brasil |
| `ui_result_visuals.py` | Visual completo dos resultados (cabeçalho, níveis, comparação, evolução, ranking, distribuição, agregação, rotatividade, escala do mapa), celular e impressão; abas pela conversa | Séries da tendência, barras da rotatividade e comparação: `ui_area_de_analise.py`. Pedidos de apresentação pela conversa: `ui_conversa_grafico.py`. Resumo do motor: pytest (`test_result_summary.py`) | Cabeçalho do resultado, pirulito do ranking, faixa da distribuição e escala de cor do mapa |
| `ui_conversational_smoke.py` | Saudação, escolha adiada da fonte, intenção retomada, edições na preparação, duas fontes do Brasil, exportação | Perguntas locais antes dos dados, descrição dos dados do Brasil, escolha da fonte pela conversa, pedido guardado e retomado e planilha pela conversa: `ui_conversa_grafico.py` | Edições na preparação e escolha entre a fonte nacional e a municipal |
| `ui_block1_integration.py` | Interpretação preliminar e contextual pelo Gemini simulado, cálculo, proposta fora do contrato (502), recuperação, exemplos da biblioteca e minimização | `ui_conversa_grafico.py` (suíte `gemini-simulado`); o cálculo, pela área | — |
| `ui_semantic_continuity.py` | Ambiguidade com alternativas, explicação do resultado, nomes pendentes, orientação e agradecimento locais, "E agora?", histórico, compositor visível, encerramento | Ambiguidade em botões, nomes pendentes e respostas locais: `ui_conversa_grafico.py`. Compositor visível e encerramento: `ui_pagina_unica.py` | — (ver as lacunas) |
| `ui_stabilization.py` | Comandos de navegação, etapas, fonte oficial, períodos, comparações, CSV, quatro larguras, troca de análise sem recarregar a base | Fonte escolhida pela conversa: `ui_conversa_grafico.py`. Larguras: `ui_pagina_unica.py`. "Últimos N anos": pytest (`test_conversation_periods.py`) | Etapas da preparação, seletor de períodos e as caixas das 12 análises |
| `ui_painel_integrado.py` | Gráfico de bolhas: eixo, régua, municípios acrescentados, conjunto, distância, crescimento, conversa arrastável, 390 px, volta ao fluxo clássico | O gráfico: `ui_area_de_analise.py`. Caixa da conversa arrastável (mouse, teclado, posição guardada, minimizar): `ui_pagina_unica.py` | "Todas as análises" e "Outras análises" (a volta ao fluxo clássico) |

**Lacunas abertas** (lista de trabalho para os roteiros da conversa e da área):
- a explicação do resultado em exibição pela conversa ("O que esse resultado significa?") e o "E agora?" com o contexto
  do gráfico, no navegador;
- a vírgula decimal e as coordenadas inválidas de uma planilha, vistas no navegador.

**Outros arquivos que saíram com o fluxo clássico:**
- `bench_ui_criteria.py`, `bench_ui_journey.py`, `bench_ui_map.py` e `bench_ui_nearest.py`: medições de tempo do fluxo
  clássico no navegador, fora do CI. As medições do motor continuam (`bench_criteria.py`, `bench_latency.py`,
  `bench_nearest.py`).
- `prepare_ui_brazil_catalog.py`: o catálogo sintético de duas fontes da antiga suíte `conversa`. A suíte passou a usar o
  catálogo sintético do Bloco 1 (`prepare_block1_catalog.py`), com o roteiro `ui_conversa_grafico.py`.
- Testes unitários do frontend que saíram com os seus módulos, usados só pelas telas que saíram: `diagnostics.test.mjs`,
  `headerModel.test.mjs`, `investigation.test.mjs`, `preparationReadiness.test.mjs`, `representation.test.mjs`,
  `trend.test.mjs`, `visualModels.test.mjs` e `analysisCatalog.test.mjs` (o catálogo das 12 análises). De `workspace.test.mjs`, os testes de `normalizeCommand`, `viewCommand` e
  `previousResultCommand` foram para `conversaGrafico.test.mjs`; os de `navigationCommand` (navegação entre preparação e
  resultados) e de `governedRoles` (perfil oficial na preparação) saíram com as funções.

## Roteiros anteriores ao redesenho conversacional (15/10/2026)

Estes 7 roteiros testavam a interface **anterior ao redesenho conversacional de 12/10/2026**. Foram movidos para cá em
15/10/2026 por três motivos:

1. **Nunca rodaram no CI.** Por isso, suas falhas não apareciam em lugar nenhum.
2. **Falham contra a interface atual logo nos primeiros passos.** Execução de 15/10/2026 no commit
   `dbaa0bd`:
   - `ui_audit_smoke.py`: falta o texto "temporal.csv carregado";
   - `ui_carousel_smoke.py`: falta `#analises button[aria-pressed]`;
   - `ui_preparation_smoke.py`: falta o botão "Usar dados do Brasil" no painel antigo;
   - `ui_session_smoke.py`: falta "Proposta simulada…" no histórico da conversa;
   - `ui_integration_smoke.py`: falta "Sugestão preliminar: Densidade";
   - `ui_brazil_smoke.py` e `ui_smoke.py`: exigiam `ADT_REAL_DATA_DIR` e também usam o fluxo antigo.
3. **Mantê-los em `backend/tests/` dava uma falsa impressão de cobertura.**

Ficam aqui apenas como referência histórica. **Não rodam**: importam de `backend/tests/ui_support.py` funções (`select`,
`stage` e `card`) que não existem mais desde a página única (22/10/2026), e a interface que testavam saiu do produto.

### O que cobriam e onde essa cobertura estava em 15/10/2026

| Roteiro legado | O que cobria | Cobertura no CI em 15/10/2026 | Lacuna |
|---|---|---|---|
| `ui_audit_smoke.py` | A02 indicadores explícitos e navegação; A05 CSV em precisão integral; A08; A10 falha do pré-exame com orientação local | A05: `ui_block1_smoke`/`ui_block1_regression` conferem CSV e JSON contra o motor. A10: recuperação em `ui_block1_integration` | A02 e A08 na interface atual |
| `ui_carousel_smoke.py` | 10 cartões; teclado, roda do mouse, Ctrl+roda reservado ao zoom, deslizar no celular, movimento reduzido | Navegação pelo carrossel em `ui_visibility_diagnostic`; larguras de 390 e 768 px em `ui_block1_smoke` | Teclado, roda, deslizar e movimento reduzido no carrossel atual |
| `ui_preparation_smoke.py` | Etapas da preparação antiga; confirmação de código; distribuição com população; revalidação que não reaproveita habilitação; upload independente do catálogo | Preparação na conversa em `ui_conversational_smoke`, `ui_block1_*`; troca de fonte em `ui_block1_regression` | Erro de revalidação na preparação atual |
| `ui_session_smoke.py` | Aceite de privacidade e foco preso no modal; `sessionStorage` bloqueado; nova aba = nova sessão; falha e recuperação da conversa | Aceite ("Li e concordo") em todas as jornadas; recuperação em `ui_block1_integration` | Foco no modal, armazenamento bloqueado, nova aba |
| `ui_integration_smoke.py` | 14 verificações: fluxo preliminar, A09–A13, troca nacional/municipal, concorrência, XLSX com duas abas, XLS, CSV malformado, extensão não suportada, minimização ao provedor | XLSX com duas abas em `ui_block1_regression`; A12 e minimização em `ui_block1_integration`; XLS e extensão não suportada na API (`test_upload_api.py`); CSV malformado na API (`test_upload_api.py`, desde 15/10/2026) | Concorrência (resposta pendente invalidada) e XLS/CSV malformado vistos no navegador |
| `ui_brazil_smoke.py` | Catálogo Brasil: CSV nacional, densidade municipal, troca de abrangência, upload internacional, celular (dados reais) | Jornada do Bloco 1 com a base versionada (suíte `base-versionada`) e suíte de dados reais do backend (job `dados-reais`) | Troca de abrangência nacional/municipal com dados reais no navegador |
| `ui_smoke.py` | Upload real do CSV municipal (122.534 linhas) e exportação conferida linha a linha contra o original | Testes de dados reais do backend conferem todas as linhas com aritmética independente (job `dados-reais`) | Upload do arquivo grande pelo navegador |

Em 22/10/2026, os roteiros citados nesta tabela como cobertura (`ui_block1_*`, `ui_visibility_diagnostic`,
`ui_conversational_smoke`) também saíram; a cobertura do que continua no produto está na seção anterior. Hoje: XLSX com duas
abas, extensão recusada e o aceite de privacidade com o foco no diálogo da Nova sessão ficam em `ui_pagina_unica.py`; a
recuperação depois de uma proposta recusada e a minimização ao provedor, em `ui_conversa_grafico.py`.

## `ui_painel_integrado.py` (saiu em 22/10/2026, com a página única de análise)

O roteiro do gráfico de bolhas de 21 e 22/10/2026 foi apagado, não movido para cá: a tela que ele percorria virou a área de
análise da página única (`frontend/src/AreaDeAnalise.tsx`). A cobertura passou para `backend/tests/ui_area_de_analise.py`,
registrado nas mesmas suítes (`bloco1` e `base-versionada`), e para os roteiros da estrutura da página (frente B1).

| O que `ui_painel_integrado.py` cobria | Onde está agora |
|---|---|
| Abertura com a base do Brasil, sem botão próprio | `ui_area_de_analise.py`, passos 1 e 2: E0 (moldura limpa, intenção da família) e E1 (os estados em bolhas); a abertura pela estrutura da página, em `ui_pagina_unica.py` (B1) |
| Brasil inteiro no modo leve (desenho, tabela em páginas, régua sem travar e sem pedido, dica no mouse) | `ui_area_de_analise.py`, passo 14 (base versionada), agora por escolha ("Todos os municípios do Brasil") |
| Escala logarítmica automática | Saiu do produto (decisão de 22/10/2026: sem escala automática); o passo 14 confere que o eixo continua linear |
| Eixo único com as bolhas iguais às da resposta | Passos 2 e 3, com o indicador no eixo vertical e o arranjo na horizontal |
| Dica no mouse e no foco | Passos 2 (bolha do estado, com a ação "Ver os municípios") e 3 |
| Quantidade sem novo pedido | Passo 6 |
| Régua pelo teclado e pelo mouse | Passo 7 |
| Municípios por busca | Passo 4 (a busca como complemento da lista) |
| Municípios arrastados para o gráfico | Saiu do produto: a escolha passou a ser a lista sempre à vista, com caixas de marcar (passos 3 a 5) |
| Conjunto agregado como bolha | Passo 12 (Juntar) |
| Distância com "Usar o primeiro" e a recusa do motor no catálogo sintético | Passo 9 (Análise espacial), conforme a disponibilidade do motor: o eixo da distância, a recusa com as opções da pendência que o motor mandar ou a aba desabilitada com o motivo. Desde a segunda rodada de 24/10/2026, a referência sai do Território de referência (a relação, a delimitação e a condição), no lugar de "Usar o primeiro", que saiu do produto |
| Crescimento com os percentuais, vista inicial e Reproduzir | Passo 10 (Tendência, visão Trajetória, a antiga Mudança) |
| Caixa da conversa arrastável (mouse e teclado) e envio de mensagem | Roteiros da estrutura da página e da conversa (`ui_pagina_unica.py` e `ui_conversa_grafico.py`, frente B1), donos da caixa |
| 390 px sem rolagem horizontal | Passo 16 (com as abas roláveis, o botão "Ferramentas" e o painel na base da tela; desde a segunda rodada de 24/10/2026, também Desfazer (o "Voltar" até 25/10/2026) e Limpar seleção dentro da largura e as duas áreas da Seleção uma sobre a outra); a conversa ancorada embaixo fica com a frente B1 |
| "Todas as análises" e a volta pelo "Início" sem recalcular | O fluxo clássico sai do produto com a página única (decisão de 22/10/2026, frente B1), e reabrir sem recalcular passa a ser o Histórico, em `ui_pagina_unica.py` (B1), que confere também que "Todas as análises" (`painel-voltar`) não existe mais |
