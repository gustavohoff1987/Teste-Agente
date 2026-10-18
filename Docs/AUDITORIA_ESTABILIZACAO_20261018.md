# Auditoria e estabilização da aplicação — 18/10/2026

## Escopo e ponto de partida

Branch: `feat/novos-blocos-incrementais`. Base auditada: `7dd5d2cedfa77550d512932ff0ef6c866454c9cc`.
O trabalho anterior foi preservado. A atualização local até essa base foi feita por avanço linear,
sem merge e sem alterar `main`.

O [CI #330](https://github.com/gustavohoff1987/Teste-Agente/actions/runs/39093687443) estava reprovado:
`backend`, `dados-reais`, `frontend`, `ui-conversational` e `governanca` passaram;
`ui-block1` e, consequentemente, `resumo` falharam. A investigação começou pelo `resumo` e pelos
logs de `ui-block1`. As falhas foram reproduzidas localmente antes de alterar os roteiros.

## Diagnóstico, correção e rastreabilidade

| Problema e causa | Classificação e correção | Arquivos principais | Verificação |
|---|---|---|---|
| Preparação invisível após resultados; estados de etapa em dois componentes, regra CSS global e navegação com atraso competiam entre si. | Defeito do produto. `App` passa a controlar a etapa; navegação muda a etapa antes de procurar o destino da rolagem. Painéis inativos mantêm estado, mas ficam ocultos. | `App.tsx`, `AnalysisAssistant.tsx`, `workspaceNavigation.ts`, `styles.css` | Retorno, avanço, reutilização, reabertura do resultado atual, falhas de rede e restauração em `ui_stabilization`, `ui_investigation` e roteiros do Bloco 1. |
| Roteiros tentavam usar controles de etapas anteriores como se todos os painéis continuassem simultaneamente visíveis. | Testes desatualizados, coexistindo com o defeito acima. Roteiros passam a navegar pelos botões reais antes de interagir. As verificações substantivas foram preservadas. | `backend/tests/ui_support.py` e roteiros atualizados | Executor único, incluindo base versionada, exportação, seleção, mapas, gráficos e critérios. |
| O carrossel voltava à análise selecionada durante a exploração de outras opções; a lista recriada pelo pré-exame disparava seu efeito. | Defeito do produto. Sincronização depende do índice da seleção efetiva, não da identidade de uma lista recriada. | `ChatAnalysisCarousel.tsx` | Jornada de investigação seleciona e executa também a análise espacial; helper verifica o título escolhido. |
| Modo de período independente da seleção em `App`; voltar de etapa podia perder o estado de edição. Períodos e condições oficiais ficavam inacessíveis quando o pré-exame aprovava. | Defeito do produto. Estado único, transições atômicas, editor acessível para quantitativos, relatório e evolução. Seleção múltipla vazia bloqueia execução, inclusive pelo caminho avançado. | `PeriodSelection.tsx`, `ConversationalPreparation.tsx`, `App.tsx` | Período único, múltiplos, seleção vazia, retorno, CSV e importação em `ui_stabilization`; regressão conversacional e temporal. |
| Reconhecimento oficial podia continuar sendo usado depois de alterar significados ou unidade; troca de abrangência descartava confirmações já válidas do novo perfil. | Defeito do produto. Reconhecimento depende da correspondência exata com o perfil governado vigente. Troca de abrangência preserva apenas equivalências demonstradas e os papéis autorizados do novo perfil. | `curatedPreparation.ts`, `App.tsx` | Testes negativos de unidade, mapeamento, categoria e confirmações; jornadas nacional/municipal e importada. |
| Comparação A/B aparecia como um registro visual único; apresentação em cartões havia perdido filtros e ordenação. | Defeito de apresentação. Dois cartões territoriais com valores originais e resumo separado da relação. Filtros e ordenação restabelecidos; CSV conserva as linhas do motor. | `ResultTable.tsx` | Dois cartões A/B, três cartões após inclusão, valores integrais, filtro e igualdade do CSV com resposta da API. |
| “Quantos médicos existem no Brasil?” chegava ao intérprete sem o interrogativo: proteção nominal o confundia com um nome próprio. | Defeito de integração. “Quantos/Quantas” entram na lista de palavras interrogativas permitidas. | `backend/llm_bridge.py`, `test_llm_bridge.py` | Dois casos de integração preservam o interrogativo e continuam excluindo nome, e-mail e CPF. Transporte controlado na jornada de navegador. |
| Comandos locais acentuados de navegação não correspondiam à expressão normalizada; a última resposta desaparecia ao enviar nova mensagem. | Defeitos do produto. Normalização corrigida e resposta mais recente do agente selecionada independentemente da última mensagem do usuário. | `workspaceNavigation.ts`, `AnalysisAssistant.tsx` | Testes de acentuação, negação, comando analítico e navegação; jornada responsiva. |

Os caminhos do frontend da tabela são relativos a `frontend/src/`. Nenhuma correção alterou
fórmulas, métodos, regras do motor ou contratos analíticos. Não houve alteração da SPEC para
acomodar um comportamento. O número de cartões de A/B mudou deliberadamente de um para dois;
a relação numérica e o CSV continuam conferidos contra a resposta original.

## Jornadas e ambientes

`backend/tests/run_ui_checks.py` executa 14 jornadas: uma conversacional, oito do Bloco 1,
três com transporte Gemini simulado e duas com a base versionada. O novo
`ui_stabilization.py` está registrado nesse executor e, portanto, no CI existente.

A jornada de estabilização usa navegador, frontend, API e motor reais, com catálogo sintético
declarado. Apenas o transporte de interpretação externa é simulado. Ela percorre:

- “Usar dados do Brasil.” e “Quantos médicos existem no Brasil?”;
- “Mostre a densidade médica dos municípios do Amazonas em junho de 2024.”;
- “Compare Manaus e Tefé.” e “Inclua Parintins.”;
- “Mostre a evolução dos municípios selecionados.”;
- “Quero analisar vários períodos.” e “Volte para a seleção de territórios.”;
- alternância entre período único e múltiplos, persistência ao navegar, seleção vazia e exportação;
- reabertura do resultado atual pelo histórico sem recalcular;
- importação com confirmação explícita da unidade e da força de trabalho em saúde;
- larguras de 1440, 1024, 768 e 390 px, três etapas por largura, acesso ao compositor e ausência
  de transbordamento horizontal, com uma verificação adicional de fonte DejaVu Sans.

Cada envio de mensagem confere que nenhuma requisição de cálculo foi disparada. Os valores de
competências diferentes permanecem em linhas diferentes. Evolução temporal continuava exigindo
as declarações de comparabilidade e identidade territorial. A aplicação não presumia essas
declarações por reconhecer a fonte oficial.

> **Nota posterior (18/10/2026, tarde).** Por decisão do responsável pelo produto, essas
> premissas passaram a ser internas na base oficial: a comparabilidade temporal é regra do
> perfil governado e a identidade territorial é verificada nos dados. A jornada confere que as
> caixas não aparecem e que o resultado registra a origem. Ver o
> [registro de comportamento](REGISTRO_DE_COMPORTAMENTO.md) e as
> [premissas internas da base oficial](DADOS_BRASIL_VALIDACAO.md#premissas-internas-da-base-oficial).

Os roteiros anteriores cobrem também tabelas, gráficos, mapas e indisponibilidade, filtros,
seleção compartilhada, referências, critérios, investigação, limite de referências, perda de
sessão, falha de rede e exportações. As duas jornadas com a base versionada conferem o catálogo
real de 62 municípios do Amazonas e 22 competências, sem modificar os arquivos.

## Resultados locais

| Verificação | Resultado |
|---|---|
| `npm ci` seguido de `npm run build` | Aprovado: 29 testes do frontend, TypeScript e Vite. |
| Backend completo com `ADT_REAL_DATA_DIR` apontando para a raiz | 489 aprovados, nenhum pulado; 481,69 s. |
| Executor completo de navegador sobre o build final | 14 jornadas aprovadas: conversa (1), Bloco 1 (8), transporte simulado (3) e base versionada (2). Sem erros de JavaScript nas jornadas verificadas. |
| Diagnóstico e comparação de integridade | `integridade: verificada`; sete arquivos protegidos com SHA-256 idêntico ao registro anterior. |
| Governança | Conferida antes da publicação e novamente sobre o commit que reúne código, testes e documentação. |

No Windows, uma tentativa do pytest encontrou permissão insuficiente no diretório temporário
compartilhado. A execução completa foi repetida com `TEMP`/`TMP` exclusivos sob `.local`, sem
alterar testes ou produto; o resultado de 489 aprovações acima é o dessa execução válida.

Os logs locais ficam sob `.local/audit-*.log`; capturas ficam em `.local/ui-validation/`.
São evidências de execução, não dados analíticos versionados.

Resultado individual da bateria final:

| Suíte | Roteiro | Resultado |
|---|---|---|
| conversa | `ui_conversational_smoke.py` | Aprovado |
| bloco1 | `ui_block1_smoke.py` | Aprovado |
| bloco1 | `ui_block1_regression.py` | Aprovado |
| bloco1 | `ui_nearest_smoke.py` | Aprovado |
| bloco1 | `ui_criteria_smoke.py` | Aprovado |
| bloco1 | `ui_map_smoke.py` | Aprovado |
| bloco1 | `ui_visibility_diagnostic.py` | Aprovado |
| bloco1 | `ui_investigation.py` | Aprovado |
| bloco1 | `ui_integrated_workspace.py` | Aprovado |
| gemini-simulado | `ui_block1_integration.py` | Aprovado |
| gemini-simulado | `ui_semantic_continuity.py` | Aprovado |
| gemini-simulado | `ui_stabilization.py` | Aprovado |
| base-versionada | `ui_block1_smoke.py` | Aprovado |
| base-versionada | `ui_investigation.py` | Aprovado |

As capturas desktop e móvel foram também inspecionadas: compositor acessível junto à parte
inferior, última resposta visível, avatar preservado e uma etapa operacional principal visível.

## Integridade e fronteiras

[INTEGRIDADE_ESTABILIZACAO_20261018.json](INTEGRIDADE_ESTABILIZACAO_20261018.json) registra a
comparação dos hashes. Dados nacionais, municipais, manifesto, SPEC, avatar e workflow permanecem
idênticos. O diagnóstico da base verifica também os tamanhos e hashes previstos no manifesto.
O único arquivo de produção do backend alterado nesta revisão é `llm_bridge.py`, na preservação
dos dois interrogativos; os motores determinísticos não foram modificados.

Os valores dos resultados não foram recalculados na apresentação. A comparação mostra os
valores A e B recebidos, mantendo as diferenças e condições da mesma resposta. A exportação
continua a usar o contrato original do motor.

## Limites e pendências verificáveis

- **Gemini real:** não validado nesta bateria. A integração foi testada com transporte controlado
  e nos caminhos de indisponibilidade; isso não comprova disponibilidade, credencial ou qualidade
  do serviço externo real.
- **Lint dedicado:** o projeto não tem script nem configuração de lint. Foram executados os
  testes existentes, a checagem TypeScript e o build; não se declara aprovação de um lint ausente.
- **Dependências de desenvolvimento:** `npm audit` identifica sete alertas herdados (cinco altos e
  dois moderados) na cadeia do Tailwind 3. A correção automática proposta envolve Tailwind 4,
  uma migração de CSS que não foi incluída nesta estabilização. `npm audit --omit=dev` retorna zero
  vulnerabilidades. Os alertas não foram suprimidos nem tratados como resolvidos.
- **Avisos existentes:** Vite informa bundle principal maior que 500 kB; pytest informa depreciação
  da integração Starlette/httpx. Não causaram reprovação, mas permanecem registrados.

## Publicação e CI

A revisão será publicada somente após as verificações locais, em um único push para a branch
autorizada. A execução do CI deve ser consultada pelo SHA integral publicado na
[lista da branch](https://github.com/gustavohoff1987/Teste-Agente/actions?query=branch%3Afeat%2Fnovos-blocos-incrementais).
O relatório de entrega informa o SHA final, o link da execução e o resultado de cada um dos sete
jobs. Aprovação local não substitui essa conferência. Não há merge em `main` nesta entrega.
