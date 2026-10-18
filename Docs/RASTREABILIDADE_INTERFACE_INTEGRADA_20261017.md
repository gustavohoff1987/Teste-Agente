# Rastreabilidade da interface integrada — 17/10/2026

## Reconhecimento e limites

Branch exclusiva: `feat/novos-blocos-incrementais`. HEAD inicial:
`0203f5482130ce3a169b91910f34177eac02d90b`. Árvore inicialmente limpa. Nenhuma nova branch,
merge, rebase, alteração da main ou configuração sensível. O CI inicial, execução
[261](https://github.com/gustavohoff1987/Teste-Agente/actions/runs/39076706648), estava aprovado.

Foram examinados App, AnalysisAssistant, preparação, histórico, investigação, sessão, exportação,
personagem, testes de navegador, executor, workflow, README e governança. A execução analítica
continua no backend; a nova organização de diagnósticos é exclusivamente uma associação em memória
a resultados existentes. Não altera a representação nem mistura valores.

Arquivos de produto autorizados e alterados: `frontend/src/App.tsx`, `AnalysisAssistant.tsx`,
`ChatAnalysisCarousel.tsx`, `PreviousAnalyses.tsx`, `InvestigationOverview.tsx`,
`conversationSession.ts`, `workspaceNavigation.ts`, `styles.css`; novos `WorkspaceDialog.tsx`
e `diagnostics.ts`. A documentação e os testes acompanham a mudança no mesmo commit.

O guia [Interface conversacional integrada](INTERFACE_CONVERSACIONAL_INTEGRADA.md) descreve as
fronteiras dos componentes, os cinco botões, os fluxos de sessão/análise/composição e a exportação.
O personagem permanece nas orientações, confirmações, preparação e apresentação; o mesmo
SVG é reutilizado, sem gerar variantes. O banner também reutiliza `WelcomeHero.tsx` sem modificá-lo.

### Arquivos de apoio alterados

- Documentação: `README.md`, `Docs/REGISTRO_DE_COMPORTAMENTO.md`,
  `Docs/ANALISE_EXPLORATORIA_INTEGRADA.md`, `Docs/BLOCO1_RESULTADOS_EXPLORAVEIS.md`,
  `Docs/BLOCO3_MAPAS_VISUALIZACOES.md`, `Docs/CONVERSACAO_INCREMENTO_FN.md`,
  `Docs/EVOLUCAO_CONVERSACIONAL_20261016.md`, o guia e este relatório, além de
  `Docs/INTEGRIDADE_INTERFACE_INTEGRADA_20261017.json` com os hashes antes/depois.
- Navegador, todos em `backend/tests/`: `ui_support.py`, `ui_block1_smoke.py`,
  `ui_block1_regression.py`, `ui_block1_integration.py`, `ui_conversational_smoke.py`,
  `ui_criteria_smoke.py`, `ui_investigation.py`, `ui_map_smoke.py`, `ui_nearest_smoke.py`,
  `ui_semantic_continuity.py`, `ui_visibility_diagnostic.py` e o novo `ui_integrated_workspace.py`.
- Registro e testes unitários: `backend/tests/run_ui_checks.py`,
  `backend/tests/test_document_conversation.py` e `frontend/tests/diagnostics.test.mjs`.

## Baseline local

- Integridade do catálogo: verificada; SHA-256 nacional
  `7caa74d7a49f2f7cd2adf87b1c0546f7755ec0291dcb0ffbfae7c387dceb91d3`; municipal
  `89c027c90a2db5a4a7a7b5e3282404fb12b2bc30d500a4a79e49b6793749f512`.
- Frontend: 24 testes aprovados, TypeScript e build aprovados. O sandbox impediu inicialmente
  o esbuild de ler diretórios ancestrais; executar o mesmo comando fora dele resolveu o acesso.
- Backend inicial: 456 passaram, 29 pulados por ausência de `ADT_REAL_DATA_DIR`, 2 falharam.
  A governança passou com `PYTHONUTF8=1`; a falha restante era do roteiro de autorização PT:
  dividir bytes CRLF por um marcador LF não removia o adendo, reenviando a SPEC completa.
  O teste agora normaliza as quebras e confirma que o adendo foi removido antes de exigir rejeição.
  O produto e a SPEC permanecem iguais. Os 25 testes focados passaram após essa correção.
- Navegador no build inicial: conversa, Bloco 1, regressão CSV/XLSX, referência mais próxima,
  critérios, mapa e diagnóstico de visibilidade passaram. A rodada foi interrompida antes de
  completar investigação/Gemini/base versionada; não é apresentada como aprovação local integral.

## Cobertura da mudança

As jornadas existentes mantêm as asserções analíticas, exportações, identidades e ausência de
recálculo. A escolha de composição foi adicionada ao caminho de execução. As asserções de duas
colunas foram substituídas por fluxo horizontal e compositor acessível; contadores vazios removidos
são verificados pela ausência de cartões, mantendo a cobertura de descarte.

`ui_integrated_workspace.py`, registrado no executor do CI, acrescenta cinco ações, confirmação e
cancelamento, foco por teclado, análise independente, composição, reabertura, CSV/JSON fiel,
quatro larguras, falha de fechamento e revogação real no servidor. `diagnostics.test.mjs` verifica
ordem, identidade, reutilização e interpretação restrita da intenção de apresentação.

### Diagnóstico dos ciclos de regressão

- Testes desatualizados: cliques no menu lateral, encerramento direto e asserção de duas colunas
  passaram a seguir a navegação horizontal e os diálogos. As verificações de números, fontes,
  exportações, privacidade e ausência de recálculo continuam ativas.
- Defeito de roteiro: a remoção do adendo em `test_document_conversation.py` falhava em CRLF;
  corrigiu-se a preparação da entrada, mantendo a exigência de rejeição pelo produto.
- Defeito de interface encontrado pelo teste novo: Shift+Tab podia deixar o diálogo;
  o componente agora contém o foco e devolve-o ao acionador quando fecha.
- Integração conversacional: comandos explícitos de organização são separados no navegador
  antes da interpretação local. A mensagem original é preservada; nenhum termo analítico
  desconhecido é descartado para fazer a validação passar. Não se alterou a gramática do backend.
- Ambiente: UTF-8 explícito resolve a saída de governança no terminal Windows; o build usa
  a permissão necessária ao esbuild. Nenhuma exceção foi adicionada ao CI.

## Validação final

| Verificação local | Resultado |
|---|---|
| Backend completo com `ADT_REAL_DATA_DIR` e dados versionados | 487 aprovados, nenhum pulado; 513,24 s |
| Frontend (`npm ci`, testes, TypeScript e Vite) | instalação concluída; 27 testes aprovados; build aprovado |
| Executor completo de navegador | 13 jornadas aprovadas, incluindo duas jornadas com a base versionada |
| Jornada integrada após acabamento final | aprovada novamente; 12 s; conteúdo calculado e compositor acessíveis em quatro larguras |
| Governança e `git diff --check` | aprovados; todas as jornadas registradas no CI |
| Diagnóstico dos dados | `integridade: verificada`; hashes idênticos aos do baseline |
| Bases, manifesto, complemento de coordenadas, SPEC, workflow e personagem | sete hashes SHA-256 conferidos, sem divergências |

As 13 jornadas abrangem conversa, importação CSV/XLSX, resultados do Bloco 1, referência mais
próxima, critérios, mapas, visibilidade, investigação, interface integrada, Gemini simulado,
continuidade semântica e duas execuções com a base brasileira. A jornada do Bloco 1 real contempla
62 municípios do Amazonas; exportações são comparadas aos valores devolvidos pelo motor.
O teste novo exercita recuperação do mesmo resultado em outro diagnóstico, sem novo pedido
de cálculo, e verifica o retorno HTTP 410 para o token da sessão encerrada.

Comparação com o baseline: 24 → 27 testes frontend; 12 → 13 execuções de jornadas no executor;
mesma suíte de 487 testes backend, agora integralmente aprovada com a base real. A falha CRLF
foi corrigida no roteiro, não no contrato; nenhuma asserção analítica foi removida. As mudanças
finais de texto, ocultação do painel vazio e acesso direto ao conteúdo foram recompiladas e
revalidadas pela jornada integrada.

Evidências locais geradas em `.local/`: `interface-real-data.log`, `interface-build-final.log`,
`interface-ui-final.log`, `interface-focus-final.log` e capturas `ui-validation/interface-integrada-*.png`
nas larguras 1440, 1024, 768 e 390 px. Esses arquivos são produzidos pelos testes e não incluem
credenciais. O [registro de integridade](INTEGRIDADE_INTERFACE_INTEGRADA_20261017.json) é versionado.

## Publicação e CI

Este relatório acompanha o commit da implementação na branch autorizada. O envio é único,
sem alteração da main. A evidência remota é o workflow **CI Portal Experimental** associado ao
SHA publicado, com os jobs `backend`, `dados-reais`, `frontend`, `ui-conversational`, `ui-block1`,
`governanca` e `resumo`. Este relatório registra a validação anterior ao envio; a resposta final
da missão informa o SHA e a URL da execução consultada, sem presumir aprovação remota.

## Limites mantidos

Exportação CSV e impressão são por análise; não consolidam uma sessão inteira. Impressão usa o
navegador e a página da tabela em exibição. Não há persistência entre sessões, novas operações
estatísticas ou validação metodológica automática de componentes heterogêneos. O provedor real
não é chamado pelos testes; indisponibilidade e transporte Gemini simulado são exercitados.
