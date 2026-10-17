# Registro de mudanças de comportamento

Este registro guarda, em ordem cronológica, **toda mudança no que o usuário ou um consumidor da API
observa**. Isso inclui telas, fluxos, mensagens, cálculos, valores padrão, validações, exportações,
contratos da API e dados versionados. **Remoções de funções também entram.** Vale para qualquer autor:
pessoas, Claude, Codex ou envio de arquivos pela web do GitHub.

Vigência: commits posteriores a `dbaa0bd` (15/10/2026). O comportamento anterior está descrito no
`README.md` e nos documentos temáticos de `Docs/`.

## Como cumprir a regra

1. **Mudou comportamento:** no **mesmo commit**, acrescente uma entrada abaixo (a mais recente
   primeiro) e atualize o documento temático correspondente (`README.md` ou `Docs/...`).
2. **Alterou arquivos do produto sem mudar comportamento** (refatoração, ganho de desempenho sem
   efeito visível, atributo usado só por testes): escreva na mensagem do commit a linha
   `Comportamento: sem alteração — <motivo>`. Pela web do GitHub, use o campo de descrição do commit.
3. **Commit já publicado sem registro:** acrescente aqui uma entrada que cite o hash curto dele.
   O histórico não precisa ser reescrito.

O job `governanca` do CI (`.github/scripts/verificar_governanca.py`) recusa commits que alterem
`frontend/`, `backend/` (fora de `backend/tests/`), `dados/` ou os arquivos de dados da raiz sem
cumprir uma das três opções. Para conferir antes do push: `python .github/scripts/verificar_governanca.py`.

### Modelo de entrada

```markdown
### AAAA-MM-DD · `hash curto` · título curto
- **Antes:** como funcionava.
- **Agora:** como passa a funcionar.
- **Permanece:** o que continua igual e poderia parecer afetado.
- **Motivo:** decisão ou defeito que levou à mudança.
- **Documentação e testes:** o que foi atualizado junto.
```

## Entradas

### 2026-10-17 · Disponibilidade da investigação e encerramento visível

- **Antes:** expiração, reinício do servidor ou encerramento descartavam a investigação e recarregavam a página sem informar o motivo ao retornar.
- **Agora:** a abertura de uma nova sessão informa descarte por encerramento ou indisponibilidade/expiração, sem oferecer reabertura inexistente. A visão geral descreve apenas a página visível para evitar retenção de listas territoriais de todas as etapas.
- **Permanece:** prazo, isolamento, limites, descarte, memória temporária, contratos de API e proteções conversacionais. Guarda-se apenas um marcador de motivo no armazenamento da aba, removido no próximo aceite; nenhum resultado, token ou dado é persistido.
- **Motivo:** tornar a disponibilidade dos resultados compreensível e verificar as jornadas de maior volume e falhas.
- **Documentação e testes:** guia da investigação e relatório técnico; ampliação de `ui_investigation.py` com distância, paginação, limite real de referências, falha de rede e perda de sessão pelo backend.

### 2026-10-17 · Investigação progressiva e destaque territorial coordenado

- **Antes:** resultados podiam ser reabertos pelo histórico, mas faltava visão acumulada da investigação e controles visuais eram reiniciados ao navegar.
- **Agora:** etapas paginadas identificam operações, fontes, recortes, períodos, unidades e situação; cada resultado pode ser expandido/recolhido. Filtros, seleção, indicadores e páginas são lembrados por resultado. Destaque explícito entre etapas exige identidade compatível e informa diferenças; não transfere valores, classes ou relações. Resultados sem linhas e sem referência conversacional têm estados visíveis.
- **Permanece:** operações, motores, métodos, dados, SPEC, validações, exportações e histórico anterior; parâmetros só são retomados explicitamente, cálculos exigem execução, conversa usa referências verificadas e a retenção continua temporária.
- **Motivo:** permitir investigação contínua sem misturar resultados metodologicamente distintos.
- **Documentação e testes:** `ANALISE_EXPLORATORIA_INTEGRADA.md`, testes de compatibilidade do frontend e `ui_investigation.py` registrado no executor, com catálogo sintético e base versionada.

### 2026-10-17 · Incremento 3 — leitura ancorada de resultados

- **Antes:** a conversa não recuperava o resultado apresentado por referência verificada e não distinguia explicação de novo cálculo.
- **Agora:** densidade, quantitativos e comparação territorial admitem leitura do resultado da sessão, segmentos com caminhos verificáveis, relações já produzidas pelo motor, documentação PT e simplificação sem retirar fatos ou limitações. Relação ausente oferece preparação explícita de comparação, sem executá-la. A preparação atual e o recorte do resultado permanecem distintos. Alteração de dados, referência forjada ou conteúdo adulterado não sustentam resposta. Cortesia e descrição geral não dependem de base pronta. A minimização no caminho de sessão também reconhece variações de acento/caixa e protege o nome do arquivo.
- **Permanece:** cálculos, validações analíticas, limites/modelo do Gemini, catálogo literal e bloqueio EN. As demais operações continuam acessíveis diretamente; sua leitura analítica conversacional recebe insuficiência documental até haver composição específica validada. Não há explicação causal nem novo ranking derivado pelo chat.
- **Motivo:** tornar resultados exploráveis com controles proporcionais por construção, sem LLM auditor ou interpretação analítica livre.
- **Documentação e testes:** README, `CONVERSACAO_INCREMENTO_FN.md`, `EVOLUCAO_CONVERSACIONAL_20261016.md`, `test_result_conversation.py`, ampliação de testes de sessão e da jornada `ui_semantic_continuity.py` já registrada.

### 2026-10-16 · Incremento 2 — seleção contextual e sessão temporária

- **Antes:** resultados existiam apenas no navegador; não havia vínculo de sessão no servidor, expiração efetiva ou controle de encerramento. “Esses municípios” e correções de indicador podiam perder o contexto.
- **Agora:** sessão opaca em memória com expiração de 1.800 segundos e encerramento; captura verificada da seleção/parametrização; IDs de resultados resolvidos somente na sessão de origem; respostas tardias rejeitadas por revisão. Referências dêiticas, correção de quantidade/densidade e inclusão de município reaproveitam preparação. A conversa informa possibilidades atuais sem executar.
- **Permanece:** métodos e motor, manipulação direta da interface, ausência de persistência de arquivos e limites do Gemini. API sem sessão conserva compatibilidade; a interface utiliza sessão.
- **Motivo:** consciência de tela sem confiar em resultados enviados pelo navegador nem criar banco de dados.
- **Documentação e testes:** README, `EVOLUCAO_CONVERSACIONAL_20261016.md`, `test_conversation_session.py` e ampliação de `ui_semantic_continuity.py`, já registrada no executor.

### 2026-10-16 · Incremento 1 — catálogo PT e continuidade conversacional

- **Antes:** explicações metodológicas usavam textos locais não materializados do catálogo; saudações podiam reiniciar a apresentação e referências explícitas só alcançavam a última mensagem.
- **Agora:** densidade, distância e agregação usam formas PT literais verificadas contra o Anexo A; EN bloqueado. O contrato reconhece intenção de esclarecimento, simplificação, próximos passos e alteração contextual. Cortesia do modelo é limitada por construção; saudação repetida é breve; referências explícitas atravessam perguntas intermediárias. Simplificação reorganiza formas existentes, sem paráfrase metodológica.
- **Permanece:** cálculos, dependências externas, modelo, cota e controles de execução. Nenhuma forma do catálogo foi reescrita.
- **Motivo:** autorização expressa de implementação e uso delimitado PT. Adendo APT-20261016 excepciona somente a dependência de aprovação EN para uso PT local.
- **Documentação e testes:** `DECISAO_CATALOGO_PT_20261016.md`, `EVOLUCAO_CONVERSACIONAL_20261016.md`, adendo da SPEC e `test_document_conversation.py`. Expectativa textual de densidade atualizada para a fórmula canônica; motivo documentado no relatório de execução.

### 2026-10-16 · Interpretações concorrentes, continuidade municipal e painéis de conversa/resultados

- **Antes:** o prompt limitava o modelo a uma capacidade; a interpretação não se ligava à seleção municipal local e pedidos subsequentes voltavam a orientações genéricas. A fonte e o carrossel repetiam-se após cada interação. O histórico só aparecia a partir do segundo cálculo, dentro do resultado; preparação e resultado longos afastavam o campo de mensagem.
- **Agora:** o contrato aceita até cinco candidatas de operação/indicador com âncoras literais no pedido sanitizado atual. Leituras materialmente diferentes apresentam escolhas; sem base, a escolha prepara rascunho e, com base, prepara a análise localmente. A capacidade validada pode ser ligada aos nomes municipais pelo Python, sem enviar o catálogo ao provedor. Comparações com um município perguntam qual outro; pedidos de dois ou três sem nomes pedem os nomes e aproveitam a próxima mensagem na mesma fonte. Não há seleção arbitrária de municípios. Orientação e agradecimento são atendidos inclusive durante essa pendência, sem apagá-la. A resposta do backend é preservada na conversa.
- **Interface:** conversa à esquerda e preparação/resultados à direita a partir de 1.024 px, com rolagens independentes e compositor visível; em telas estreitas, painéis empilhados. Botões levam à preparação ou ao resultado dentro da área de análise. A fonte atual tem identificação compacta; o carrossel fica recolhido depois da escolha. “Histórico de análises” permanece acessível desde zero ou um resultado e reabre cálculos em memória sem recalcular. A legenda do mapa acompanha a largura do painel, sem estreitar o canvas por causa da largura total da janela.
- **Permanece:** motor determinístico, confirmação e cálculo explícitos, dados e SPEC intactos, proteção do conteúdo enviado ao provedor, validação de homônimos/períodos e parâmetros metodológicos. Histórico temporário em memória; consultar resultado anterior não restaura opções silenciosamente. A cobertura da arquitetura FN/CFG da SPEC continua parcial.
- **Motivo:** permitir continuação natural após resultados e esclarecer ambiguidades reais, preservando a visibilidade da conversa e o acesso aos cálculos anteriores.
- **Documentação e testes:** README, `CONVERSACAO_INCREMENTO_FN.md`, `SEMANTIC_BRIDGE_ADAPTACOES.md` e Blocos 1/3. Testes de alternativas ancoradas/rejeitadas, municípios pendentes, privacidade e orientação durante pendência; nova jornada `ui_semantic_continuity.py` registrada no executor e CI com provedor simulado. As jornadas existentes mantêm cobertura: histórico passa a ser localizado no topo do painel e a fonte pelo identificador compacto; não dependem mais da apresentação repetida. No teste de resize do mapa, a falha era medir o canvas no tamanho de impressão antes de o `ResizeObserver` retornar à tela; a sincronização agora espera a largura efetiva do canvas, mantendo a tolerância e as verificações anteriores.


### 2026-10-15 · Conversa contextual e resultados com mapas, gráficos e filtros acessíveis

- **Antes:** respostas explicativas antes da escolha da fonte eram substituídas pela apresentação inicial; barras desapareciam acima de 40 territórios e linhas acima de oito. O mapa da base Brasil aguardava um formulário técnico na aba de resultados. Tabelas truncavam em 150 linhas; JSON embutido, checklist territorial duplicado e botões PNG sobrecarregavam a exploração.
- **Agora:** perguntas sobre capacidades, conceitos e agradecimentos recebem o conteúdo correspondente, inclusive antes da fonte e sem consumo do provedor nos casos locais. Barras com rolagem incluem todos os territórios; séries têm páginas de oito, preservando lacunas. Quantitativos de pessoas com FTS confirmado são apresentados como “profissionais”. Tabelas têm filtros por coluna, comparações numéricas, ordenação visual, páginas de 150 e CSV de todo o filtro. A seleção pela tabela só vai à preparação por ação explícita. Retomada de parâmetros continua direta; metadados técnicos ficam no JSON. Removidos formulário da aba Mapa e botões PNG.
- **Mapa Brasil:** a versão íntegra correspondente ao manifesto governado recebe configuração contextual **somente de apresentação**, com SIRGAS2000 e formato decimal da fonte; a premissa ilustrativa e sua origem ficam visíveis e no JSON. O datum original continua não declarado pela fonte. Não se aplica a uploads nem a versões externas diferentes; dados, pré-exame, métodos de distância e opções analíticas não são alterados. Em uploads, a origem pode ser configurada nas opções avançadas da preparação.
- **Permanece:** resultados integrais, valores nulos e precisão original, CSV superior, JSON, impressão e histórico temporário recolhido em “Análises anteriores”. Nenhum arquivo da base ou SPEC foi alterado; nenhum dado é enviado ao provedor de IA. Os controles de invalidação e as notas técnicas já retiradas continuam ausentes.
- **Motivo:** corrigir os fluxos apontados na navegação local e tornar as visualizações previstas no Bloco 3 acessíveis sem parâmetros técnicos nos resultados.
- **Documentação e testes:** README, Blocos 1 e 3; testes de conversa e representação (incluindo mapa automático, restrição de versão e invariância dos cálculos). As jornadas existentes mantêm a cobertura: retomada direta substitui a abertura do antigo painel; JSON exportado substitui o JSON em tela; tabela + reutilização explícita substituem o checklist; ausência dos PNG, impressão e exportações substituem a antiga expectativa de download de imagem. `ui_visibility_diagnostic.py` passa de diagnóstico do defeito a regressão com 180 territórios, filtros, paginação e séries. O manifesto permanece somente leitura.

### 2026-10-15 · Análises anteriores acessíveis na sessão

- **Antes:** o histórico existia apenas internamente; não havia acesso à lista de resultados já obtidos.
- **Agora:** após a segunda análise, o usuário dispõe de **“Análises anteriores”**, painel recolhido por padrão, com títulos, solicitação, período e indicação de qual resultado está em exibição. Pode reabrir um resultado desta sessão diretamente, sem nova chamada ao motor.
- **Permanece:** resultados e parâmetros continuam temporários e apenas em memória; nenhum login ou salvamento persistente. Reabrir não modifica automaticamente os parâmetros, a fonte ou a seleção atual. Resultados de outra fonte podem ser consultados, mas não reutilizados para novas análises. O controle de invalidação **não** foi restaurado.
- **Motivo:** disponibilizar ao usuário a consulta a análises anteriores, sem expor controles internos e sem sobrecarregar a interface.
- **Documentação e testes:** atualização de `Docs/BLOCO1_RESULTADOS_EXPLORAVEIS.md`; jornada `ui_block1_smoke.py` verifica quatro resultados, ida e volta entre eles, ausência de nova requisição e regressão com base sintética e Brasil real.

### 2026-10-15 · `dbaa0bd` · Histórico de resultados e invalidação retirados da interface

*Registro tardio: a mudança foi publicada sem registro. Ela foi confirmada pelo responsável pelo
produto em 15/10/2026, que decidiu mantê-la.*

- **Antes:** a página de resultados exibia o painel "Histórico de resultados", uma lista numerada dos
  resultados da sessão com a situação de cada um ("Válido · vigente", "Válido · histórico não vigente"
  ou "Invalidado") e o botão "Voltar ao resultado anterior". Na distribuição, o painel só aparecia a
  partir do segundo resultado. Cada resultado oferecia "Registrar correção que invalida este
  resultado": com um motivo factual, o resultado ficava INVALIDADO, perdia o CSV e a retomada de
  parâmetros e deixava de ser reaproveitado. Em "Método e limitações" apareciam, entre outras, as
  notas técnicas "Período AAAAMM composto em memória…" e "Identificação territorial: …".
- **Agora:**
  - A página mostra só o resultado atual. Não há lista de resultados nem botão para voltar ao anterior.
  - Não é possível invalidar um resultado pela interface. O JSON de "Método e parâmetros" traz sempre
    `validity: "VALIDO"` e `invalidation_reason: ""`. Os campos continuam no contrato por
    compatibilidade.
  - As duas notas técnicas citadas deixaram de aparecer na tela, mas continuam no JSON exportado.
- **Permanece:** o histórico em memória da sessão continua existindo internamente, e nada é gravado
  de forma permanente. Ele sustenta:
  - o reaproveitamento de cálculo idêntico ("Resultado existente recuperado, sem recalcular.");
  - a ação "Retomar parâmetros deste resultado";
  - a navegação entre competências já calculadas do mesmo pedido;
  - a recuperação de critérios combinados;
  - a indicação de situação do resultado ("válido e vigente" ou "histórico válido · não vigente").
- **Motivo:** simplificação da interface, por decisão do responsável pelo produto.
- **Documentação e testes:**
  - Documentos corrigidos junto com este registro: `Docs/MICROITERACAO_INTERFACE_DISTRIBUICAO_20261015.md`,
    `Docs/BLOCO3_MAPAS_VISUALIZACOES.md` (seção 9) e `Docs/BLOCO1_RESULTADOS_EXPLORAVEIS.md` (atualização final).
  - `ui_conversational_smoke.py` e `ui_block1_regression.py` verificam a ausência do painel, do controle
    de invalidação e das duas notas.
  - Os testes de invalidação pela interface foram retirados em `dbaa0bd`.


### 2026-10-17 · Regularização retrospectiva da iteração visual e do recorte Brasil

Registro retrospectivo dos commits publicados na mesma branch sem atualização simultânea deste documento. Esta regularização não equivale a homologação funcional; os testes de interface e o CI continuam sendo a evidência necessária.

- **cd3b554, 9ed4bd8, eba9952:** simplificação do banner inicial, preservação do contrato de propriedades do componente, redução da altura e ajuste de legibilidade. Permanece a possibilidade de iniciar análise pela conversa e importar dados no fluxo existente.
- **c6acac3, a0ea2d4:** simplificação da identificação visível do resultado e supressão de estado técnico redundante; metadados técnicos permanecem disponíveis para exportação. Não há alteração pretendida de cálculo.
- **b5fa0a6, fd34839:** modo de resultados em largura ampliada com conversa abaixo, retirada de atalhos redundantes e limpeza de importação não utilizada. A navegação do histórico e a execução de análises devem permanecer disponíveis.
- **92863b3, 8a4d631, d7cfa00:** navegação com Início, Tipos de análise expansíveis e Resultados; uso do identificador declarado de cada análise e limpeza de importações. Não se pretende alterar o catálogo de análises nem os contratos analíticos.
- **78b7313, 9e9fd9d:** encaminhamento de pedidos explícitos pelo Brasil inteiro ao recorte nacional governado, com serialização da seleção após proposta conversacional. O objetivo é utilizar os registros nacionais próprios, e não somar registros municipais. A efetividade deste fluxo depende de validação específica com dados reais e jornadas de navegador.
- **911c7f7:** fechamento das duas expressões JSX condicionais do menu de análises (desktop e móvel) que impediam a compilação TypeScript, identificado na execução CI #235.

**Escopo preservado:** sem alteração deliberada dos arquivos de dados, motor determinístico, regras de cálculo ou especificação de implementação. **Pendências de validação:** build frontend, governança, jornadas de navegador e seleção do agregado nacional na interface. A regularização documental não substitui essas verificações.


### 2026-10-17 · Refinamento de navegação e persistência explícita da sessão

- **4d8fc5f:** menu Histórico de análises recolhe ao clicar fora, pressionar Escape ou selecionar análise anterior; preserva a consulta sem recálculo.
- **0b7d93f:** bordas azuis e contraste reforçado no painel de conversa, cabeçalho, barra de ferramentas e histórico; somente apresentação.
- **a709296, ca13784:** opção Nova análise restaurada nos menus desktop e móvel, com confirmação e aviso de que o histórico existe apenas na sessão. Nova análise limpa a seleção e o resultado em exibição, preservando fonte e histórico da sessão; não encerra sessão nem altera cálculos.
- **df0e491:** exportação CSV e impressão/PDF em evidência, aviso de que o histórico é temporário; o botão JSON foi removido da barra principal e sua função técnica deslocada para opções avançadas, preservando rastreabilidade e testes existentes.
- **bf1def0:** roteiro de navegador atualizado para acessar a exportação técnica na área avançada; preserva conferências de seleção visual e identificadores do resultado.

**Validação:** sujeita ao GitHub Actions no HEAD posterior a este registro. Nenhuma alteração deliberada no motor determinístico, nos arquivos nacionais/municipais ou nos contratos de cálculo.

### 2026-10-17 · CI #252 — manutenção das jornadas após recolhimento do histórico

- **d4ae485:** no teste de Bloco 1, reabre o histórico após a seleção anterior, preservando a asserção de que o item em exibição fica desabilitado, a contagem de resultados e a ausência de recálculo. O fechamento automático do menu permanece funcional.
- **ea230b0:** no teste de regressão, corrige a referência inexistente `board` para o localizador `result` já definido; mantém o teste da exportação técnica JSON e dos metadados.
- **Diagnóstico:** CI #252 (run 39074064405) apresentou duas falhas de histórico no mesmo roteiro (dados sintéticos e Brasil real) e uma falha por `NameError` em roteiro de regressão. Backend, dados reais, frontend, interface conversacional e governança haviam passado.
- **Escopo:** somente testes de navegador e este registro; nenhum cálculo, dado, contrato ou código de interface foi modificado. **Resultado:** pendente de aprovação do CI subsequente.

### 2026-10-17 · Contrato de testes de interface por comportamento

- **63365ba, 1977f2d:** adicionados identificadores estáveis (`data-testid`) aos controles de nova análise, confirmação, exportação CSV, impressão/PDF, opções técnicas e histórico. Os rótulos acessíveis permanecem disponíveis e a lógica de produção não foi alterada.
- **8a62496, 2486b14:** jornada Playwright estendida para confirmar fechamento do histórico por clique externo e cancelamento de nova análise sem recálculo nem perda do resultado; o botão é localizado dentro da navegação desktop. Permanecem as asserções de reabertura, contagem de linhas e não recálculo.
- **Diretriz permanente:** alterações de interface exigem identificar roteiros Playwright afetados, preservar asserções funcionais e acrescentar cobertura para novos comportamentos. Preferir seletores acessíveis e identificadores estáveis, sem afrouxar os critérios de aceite apenas para obter CI verde.
- **Validação:** aguarda execução do CI no HEAD desta iteração; não declarar aprovação antes de verificar os jobs.
