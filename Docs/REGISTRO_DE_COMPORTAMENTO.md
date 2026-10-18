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

### 2026-10-18 · Referencial e separador decimal internos nas distâncias da base oficial

- **Antes:** na base Brasil oficial, a análise espacial, a referência mais próxima e os critérios com distância pediam na preparação o referencial geodésico (SIRGAS2000). A referência mais próxima e os critérios também pediam o separador decimal das coordenadas, e a análise espacial ficava bloqueada ("Há valores não numéricos ou não finitos em latitude…") até o usuário escolher "Vírgula decimal" em "Formato dos valores numéricos", nas condições avançadas. Essas condições avançadas também exibiam, na base oficial, a caixa de comparabilidade entre territórios e as declarações da agregação, embora essas premissas já fossem internas e marcá-las ou desmarcá-las não mudasse o cálculo.
- **Agora:** na versão governada da base (integridade verificada e versão do manifesto), o referencial SIRGAS 2000 é regra do perfil, porque a fonte não o declara, e a vírgula decimal é verificada nos dados (coordenadas com vírgula decimal ou inteiras; quantidades e populações sem vírgula). As duas premissas entram só nas análises que usam coordenadas, com nota em "Método e limitações", registro em `governed_premises` e, no mapa, `premissa_referencial` e a legenda "Referencial SIRGAS 2000: premissa da base oficial…". A preparação mostra "Referencial: SIRGAS 2000 (premissa da base oficial)" e não exibe os seletores de referencial e de separador; o pré-exame descreve o requisito como premissa governada. Nas condições avançadas da base oficial, "Formato dos valores numéricos" passa a ser uma informação ("vírgula decimal nas coordenadas, verificada na base oficial"), e as caixas de premissas internas não aparecem.
- **Permanece:** distâncias, método geodésico e camada complementar; nenhuma transformação de referencial. Análises sem distância não recebem as duas opções (mesmas opções e chave de execução), e o mapa delas continua com a configuração só de apresentação. Bases importadas, versões externas fixadas e significados alterados continuam pedindo referencial, separador e declarações. Valor informado explicitamente pela API prevalece: referencial não suportado e ponto decimal com coordenadas com vírgula continuam recusados. A declaração de ausência de sobreposição, nas condições avançadas, continua disponível e prevalece sobre a soma dos componentes.
- **Motivo:** decisão do responsável pelo produto (18/10/2026), em resposta à pergunta deixada pela análise do vídeo de orientação: "pode deixar interno"; as caixas de confirmação das bases importadas são mantidas. As caixas que restavam nas condições avançadas eram uma lacuna da entrada "Premissas de comparabilidade internas na base oficial".
- **Documentação e testes:** README, validação da base Brasil (tabela de premissas internas), Blocos 2 e 3 e guia da interface. Novos testes do perfil (verificação do separador e restrição à versão governada) e da API na versão governada (pré-exame, resultados iguais aos declarados, notas, contrato do mapa, densidade sem as opções, conversa sobre o resultado na mesma preparação e prevalência do valor explícito). Testes reais: a lista de premissas da versão governada ganha as duas novas (mudança intencional), e espacial, mais próxima e critérios sem declaração dão o mesmo resultado que com declaração. `ui_block1_smoke.py`: na base real, a análise espacial calcula sem pedir referencial, com nota e legenda da premissa, e as condições avançadas não mostram seletores nem caixas de premissas internas; no catálogo sintético, o seletor de referencial continua.

### 2026-10-18 · Resultados mais legíveis: destaques, mapa com nomes e série temporal

- **Antes:** um resultado com um único município mostrava no mapa só um ponto numa área vazia, sem destaque do valor principal. O gráfico de linhas começava o eixo em zero, achatando variações pequenas, e sempre mostrava a caixa de legenda, mesmo com uma série. As tabelas exibiam competências como 201406. A aba "Mapa (não aplicável)" abria com o título "Mapa indisponível para este resultado". A identidade do resultado listava todas as competências.
- **Agora:** densidade, quantitativos, relatório e evolução com até três registros mostram cartões de destaque com os valores do motor; na evolução, inicial → final, variação absoluta e percentual e a tendência do motor. O mapa nomeia os territórios quando há até 12 pontos (até três, também com o valor) e mostra grade de coordenadas em zoom alto. O gráfico de linhas enquadra o eixo vertical nos valores observados, informa quando ele não começa em zero, usa marcadores de 8 px, dispensa a caixa de legenda numa série única e rotula só o último valor de cada série (até quatro). As tabelas exibem competências como 06/2024, e a busca aceita 06/2024 ou 202406. "Mapa não aplicável a este resultado" tem título próprio e, na evolução, orienta como ver os territórios no mapa. A identidade do resultado resume mais de três competências por quantidade e extremos.
- **Permanece:** valores, cálculos, CSV (com as competências originais), contrato de representação, regra de não desenhar a evolução no mapa, ordem neutra e ausência de totais, médias, posições, classes e linhas de tendência. A escala de apresentação continua por 1.000 habitantes.
- **Motivo:** orientação em vídeo do responsável pelo produto (18/10/2026, 03:47–04:14 e 07:05–08:04): mapa só com um ponto, mapa considerado não aplicável e pedido de visualização mais inteligível, dentro das transformações admitidas pela Parte 13 da SPEC.
- **Documentação e testes:** Bloco 3 e README. Testes Node de `niceDomain`, `tableColumns` e `compactPeriods`. `ui_block1_smoke.py` (sintético e base real) exige três cartões na evolução e competência legível na tabela; `ui_conversational_smoke.py` exige o cartão do quantitativo nacional.

### 2026-10-18 · Preparação: abrangência, resumo visual e intervalo de períodos

- **Antes:** a abrangência ficava num recolhível "Alterar a abrangência territorial" em todas as análises, inclusive nas que só existem na fonte municipal. Trocar de recorte apagava a preparação e mostrava a escolha da fonte ("Preparando seus dados...") até o novo recorte chegar. "Parâmetros da análise" era um parágrafo com todas as competências na ordem do arquivo. A seleção de vários períodos começava com todos marcados e só aceitava cliques competência por competência, com pouca diferença visual entre marcadas e desmarcadas. Na troca de recorte entre análises, o período único de uma densidade podia ser copiado para a evolução temporal, que ficava com uma só competência.
- **Agora:** "Abrangência dos dados" é uma escolha visível entre Municípios e Brasil (total nacional) em quantitativos, evolução temporal e relatórios; nas demais análises, a preparação informa que usa somente a fonte municipal. Durante a troca, a preparação continua na tela, bloqueada, com aviso de carregamento; se o novo recorte falhar, ela é mantida com o motivo. "Resumo da análise" mostra cartões de fonte, categoria, períodos e indicador, com os períodos em ordem cronológica e resumidos por intervalo. O seletor de vários períodos tem "Intervalo: de … até …", "Todos os períodos disponíveis", "Limpar", chips marcados com ✓ e a descrição da escolha. Períodos só atravessam a troca de recorte, ou a restauração do rascunho do recorte, quando a análise de destino aceita o mesmo modo (único ou vários).
- **Permanece:** cálculos, pré-exame, contratos e dados; os padrões de abrangência por análise; a opção "Abrangência da análise" nas condições avançadas; a memória da preparação de cada recorte na aba.
- **Motivo:** orientação em vídeo do responsável pelo produto (18/10/2026): dúvida sobre a abrangência (02:17–03:12), troca de recorte que voltou à tela inicial (03:12–03:35), parâmetros em texto corrido e fora de ordem (05:21–05:50) e escolha de períodos que desmarcou o intervalo pretendido (05:59–06:17). O defeito da troca entre análises apareceu na verificação visual desta mudança.
- **Documentação e testes:** README, guia da interface, validação da base Brasil e preparação guiada. Testes Node de `periods.ts` (descrição e intervalo). `ui_conversational_smoke.py` passa a trocar a abrangência em Quantitativos e confere a informação fixa na Densidade e o resumo. `ui_criteria_smoke.py` escolhe o recorte nacional em Quantitativos antes do comando de critérios. `ui_stabilization.py` usa o intervalo de períodos e ganha uma regressão da troca de recorte entre análises. Nenhuma verificação existente foi removida.

### 2026-10-18 · Territórios dentro da preparação

- **Antes:** cada análise tinha três etapas, "1. Territórios", "2. Preparação" e "3. Resultados". A seleção territorial ocupava uma etapa própria, com "Avançar para preparação" e "Voltar aos territórios".
- **Agora:** duas áreas, "1. Preparação" e "2. Resultados". A seleção territorial é um bloco da preparação, com resumo de uma linha ("Territórios: todos os territórios do recorte" ou "1 selecionado: ABREU E LIMA (PE)") e os botões "Escolher territórios", "Alterar territórios" e "Concluir seleção". O bloco começa recolhido. Comandos como "Volte para a seleção de territórios.", "Usar seleção na próxima análise" e "Usar como municípios-alvo" abrem a preparação com o bloco expandido. Em referência mais próxima e critérios, o bloco se chama "Municípios-alvo" e "Universo dos critérios". No recorte nacional, o bloco só informa o território único (Brasil), e o comando de territórios explica que a escolha de municípios vale para a abrangência Municípios.
- **Permanece:** o componente de seleção (busca, estado, limpar, adicionar correspondências e atalhos de análise), a preservação da seleção ao navegar, os cálculos e os contratos. Nenhum controle volta a ser empilhado numa página longa.
- **Motivo:** orientação em vídeo do responsável pelo produto (18/10/2026, 00:45–01:47 e 04:19–04:36): a etapa de territórios é desnecessária e a segmentação incomoda, sem voltar à rolagem longa que motivou as etapas.
- **Documentação e testes:** guia da interface, README e nota na auditoria de estabilização. O auxiliar `workspace()` de `ui_support.py` abre o bloco quando a jornada pede territórios, e os roteiros usam o auxiliar em vez dos rótulos antigos. As verificações de seleção, valores e exportações não mudaram.

### 2026-10-18 · Premissas de comparabilidade internas na base oficial

- **Antes:** na base Brasil governada, a evolução temporal exigia as caixas "Confirmo que os quantitativos e os períodos são comparáveis." e "Os territórios correspondem às mesmas unidades ao longo do tempo.". Comparações e rankings só dispensavam a confirmação numa competência municipal identificada, por inferência do navegador. A agregação exigia declarar populações sem sobreposição e a forma de contagem. O resultado temporal dizia que as premissas tinham sido declaradas pelo usuário.
- **Agora:** com o perfil governado reconhecido, `brazil_catalog_profile.py` aplica no backend a comparabilidade temporal, a comparabilidade entre municípios, as populações sem sobreposição e a soma dos componentes (regras do perfil). A identidade territorial ao longo do tempo só é aplicada depois de verificar nos dados que cada código mantém o mesmo nome em todas as competências. A interface não mostra essas caixas na base oficial, nem nas opções avançadas. `curated_defaults.premises` lista as premissas do recorte; `governed_premises`, nas opções do resultado, registra as aplicadas; "Método e limitações" informa a origem de cada uma.
- **Permanece:** cálculos, fórmulas, valores e o rótulo "Soma dos componentes (possível dupla contagem)". Bases importadas e significados alterados continuam com todas as declarações. A declaração explícita de ausência de sobreposição, nas opções avançadas, prevalece sobre a soma. Nada novo vai ao provedor de IA: a conversa lê só uma lista fixa de opções. Dados, manifesto e SPEC inalterados.
- **Motivo:** orientação em vídeo do responsável pelo produto (18/10/2026, 06:17–07:01): na base disponibilizada, o usuário não tem como confirmar essas premissas; a verificação deve ser interna e sem regressão. A tentativa anterior (`9d3c7cf`, revertida) só escondia as caixas e deixava a evolução bloqueada.
- **Documentação e testes:** README, validação da base Brasil (seção nova), guia da interface, Bloco 1 e nota na auditoria de estabilização. Testes novos de backend (catálogo sintético, evidência da identidade territorial, importações) e com dados reais. Em `test_real_resident_aggregation_is_not_national_unique_count`, a expectativa de 422 sem declaração mudou de propósito; continuam conferidos o rótulo de dupla contagem, as somas e a diferença para a contagem nacional, agora sem declarações. `ui_block1_smoke.py` e `ui_stabilization.py` passam a exigir a ausência das caixas e a origem nas notas, mantendo os valores conferidos.

### 2026-10-18 · Estabilização de navegação, períodos e comparações

- **Antes:** etapas controladas em dois componentes e uma regra CSS podiam ocultar a preparação; navegação atrasada após o cálculo podia desfazer o retorno do usuário. O seletor mantinha um modo local divergente dos períodos da análise. Configurações disponíveis desapareciam quando o pré-exame era aprovado; a atualização do pré-exame também podia reiniciar a navegação pelo carrossel. A comparação A/B era apresentada como um único território e perdia filtros. A proteção nominal removia o interrogativo “Quantos” do pedido ao intérprete.
- **Agora:** `App` controla a etapa única; botões, chat, retomada e reutilização abrem a etapa correspondente sem apagar escolhas. Os painéis inativos preservam estado e ficam ocultos; impressão continua incluindo o resultado. Período único e conjunto de períodos mudam atomicamente; seleção vazia não equivale a todos. A preparação oficial permite editar períodos e condições disponíveis; comparabilidade automática só vale com os significados reconhecidos preservados, em uma competência municipal identificada. O carrossel conserva a opção em exploração quando apenas a disponibilidade é atualizada. Comparações A/B exibem dois registros e as diferenças originais, com filtros, ordenação e exportação. A última resposta do agente permanece junto ao compositor. “Quantos/Quantas” são reconhecidos como interrogativos, mantendo a proteção de identificadores e dados.
- **Permanece:** dados, manifesto, SPEC, SVG do avatar, métodos, fórmulas, resultados numéricos e contratos analíticos. Importações e comparabilidade temporal conservam declarações necessárias. Mensagens preparam, nunca executam cálculos. CSV mantém as linhas originais do motor, inclusive a relação A/B.
- **Motivo:** auditoria da branch a partir de `7dd5d2c`, CI #330 reprovado e reprodução local da preparação oculta; falhas de produto distinguidas de roteiros que ainda interagiam com etapas simultâneas.
- **Documentação e testes:** guia da interface e README atualizados; relatório `AUDITORIA_ESTABILIZACAO_20261018.md`; nova jornada `ui_stabilization.py` registrada no executor, testes de comandos/validade do reconhecimento oficial e integração de proteção de identificadores. Roteiros existentes percorrem etapas sem remover asserções analíticas, de privacidade, exportação ou integridade. Nenhum teste foi removido ou enfraquecido.

### 2026-10-17 · Interface conversacional integrada, sessões e diagnósticos

- **Antes:** menu lateral permanente e chat em coluna separada; a investigação reunia todos os resultados sem distinguir diagnósticos; encerramento imediato por um controle separado.
- **Agora:** banner horizontal e cinco ações únicas (Início, Nova sessão, Nova análise, Histórico e Resultados); conversa expansível e campo contextual; personagem original junto à condução e aos resultados. Nova sessão exige confirmação, oferece exportação com limitação explícita por análise e revoga a sessão no servidor. Nova análise distingue criação independente e composição ordenada; intenção explícita na conversa evita a escolha redundante. O histórico reabre resultados e diagnósticos sem recálculo.
- **Permanece:** cálculos, fórmulas, validações, contratos analíticos/conversacionais, isolamento e limites de sessão, fontes nacional e municipal, manifesto, SPEC, personagem, visualizações, filtros e exportação técnica. Composição não harmoniza nem combina valores. Não há persistência nem exportação consolidada de múltiplas análises.
- **Motivo:** conduzir toda a investigação no mesmo ambiente, com distinção clara entre sessão, análise e diagnóstico, preservando identidade e rastreabilidade.
- **Documentação e testes:** guia da interface, relatório de rastreabilidade, README e guias temáticos atualizados. Jornadas preservam asserções funcionais e adotam a nova navegação; novo roteiro integrado registrado no executor. Teste de autorização PT corrigido para remover efetivamente o adendo em arquivos CRLF antes de exigir rejeição; nenhuma verificação de segurança foi relaxada.

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


### 2026-10-17 · CI #263 — contenção de largura intrínseca na interface integrada

- **7bde790:** CSS da área integrada ajustado para permitir encolhimento de componentes flexíveis, cartões e textos extensos, sem ocultação global de conteúdo.
- **Comportamento: sem alteração —** correção exclusivamente de apresentação responsiva; não modifica navegação, cálculos, contratos analíticos, dados, sessão ou personagem.
- **Evidência:** CI #263 (run 39084993288) aprovou backend, dados-reais, frontend e ui-conversational, mas ainda reprovou ui-block1 por transbordamento horizontal em quatro roteiros. A correção CSS foi insuficiente e exige diagnóstico de elemento excedente antes de nova intervenção.
- **Governança:** o job reprovou pela ausência deste registro no commit 7bde790; esta entrada regulariza a rastreabilidade documental sem afirmar que a regressão visual foi resolvida.


### 2026-10-17 · Diagnóstico dirigido de transbordamento no CI #264

- **2a57a06:** instrumenta a asserção já existente de largura em `ui_integrated_workspace.py` para incluir no erro o tamanho da página e os primeiros elementos que ultrapassam a janela, com coordenadas e dimensões. A condição de aprovação permanece exatamente a mesma.
- **Comportamento: sem alteração —** somente diagnóstico de teste Playwright; nenhum componente de produto, regra, dado ou cálculo foi modificado.
- **Motivo:** CI #264 manteve as quatro falhas de largura em `ui-block1`, apesar da correção CSS anterior. A evidência de qual elemento transborda é necessária para uma correção direcionada.
- **Validação:** aguardando logs do CI do novo commit; não declarar correção visual antes da nova evidência.


### 2026-10-17 · CI #266 — correção localizada da barra de visualizações

- **863d178:** o Playwright identificou viewport 390 px, largura da página 403 px e botão `Tabela` até x=403; a barra de abas `Mapa / Gráficos / Tabela` era `inline-flex` sem quebra. Passou a usar largura disponível e quebra de linha, preservando rótulos, seleção, papéis acessíveis e conteúdo das visualizações.
- **Comportamento:** a barra de visualizações passa a quebrar linhas em telas estreitas; não altera o cálculo, as representações, os dados, os contratos analíticos nem o personagem.
- **Limite:** SVGs e tabelas largas são conteúdo interno a examinar nos testes; não foram escondidos por `overflow-x:hidden` global nem houve redução das asserções.
- **Validação:** pendente de CI no commit que inclui esta entrada.


### 2026-10-17 · Respostas textuais na etapa de seleção de fonte

- **563af9d, 8152ff0:** a escolha explícita `Dados do Brasil` e equivalentes restritos passa a acionar o mesmo `chooseBrazil` utilizado pelo botão; pedidos explícitos de importação acionam o seletor existente. O roteamento ocorre somente enquanto não há fonte escolhida. O texto original permanece no contexto da sessão.
- **Comportamento:** respostas diretas à pergunta sobre a fonte deixam de ser tratadas como solicitações analíticas ambíguas. Solicitações de análise abertas continuam submetidas ao interpretador existente.
- **Escopo:** nenhum motor, regra analítica, base, SPEC ou SVG alterado. As demais simplificações da jornada (comparabilidade governada, etapas e apresentação de comparações) não foram implementadas por estes commits e exigem verificação específica.
- **Validação:** aguardando TypeScript, testes e CI do HEAD que inclui este registro; não declarar conclusão integral da iteração.


### 2026-10-17 · CI #271 — corrida do diálogo de privacidade após revogação de sessão

- **921c113:** em `ui_investigation.py`, após o encerramento da sessão pela API, o diálogo de privacidade pode surgir entre a consulta `is_visible()` e o clique em Resultados. O teste agora limita a tentativa de clique a 2,5 s e só tolera seu timeout quando o diálogo obrigatório realmente está visível; caso contrário, propaga a falha original.
- **Comportamento de produto: inalterado.** A privacidade continua bloqueando cliques no conteúdo de fundo; o teste exige aviso de sessão expirada, aceite explícito e limpeza dos resultados anteriores. Não usa `force=True`, não desabilita o diálogo nem remove asserções.
- **Validação:** aguardar o CI do HEAD; a correção elimina somente a corrida do roteiro e não implica aprovação antecipada da suíte.


### 2026-10-17 · Conversa contextual e compositor inferior

- **30b728a:** remove da apresentação a transcrição expansível da conversa; preserva mensagens na memória da sessão e move alternativas de esclarecimento da resposta atual para o contexto visível, sem depender da transcrição. O histórico de análises permanece separado e acessível.
- **d1bce10:** a investigação ocupa ao menos a altura disponível, com compositor ancorado na parte inferior quando há pouco conteúdo, e caixa de digitação contornada em verde alinhado à identidade do banner. A posição sticky existente é preservada na exploração de resultados.
- **Escopo:** interface conversacional e CSS; motor, dados, SPEC, personagem e API analítica inalterados.
- **Limites:** não automatiza confirmações metodológicas nem substitui a preparação por um novo fluxo progressivo; essas mudanças exigem implementação e testes específicos. Validação de CI pendente.

- **d53bfc1, c5ade11:** roteiros de navegador atualizados para exigir ausência do histórico conversacional visível e continuar testando a continuidade semântica, escolhas contextuais, resultados e limpeza de sessão. Nenhuma asserção analítica foi retirada.


### 2026-10-17 · Preparação governada e etapa focalizada

- **b0f9044:** a confirmação de comparabilidade para comparação/ranking é inferida apenas quando a base brasileira é curada, municipal, com período único selecionado, unidade de contagem, quantitativo, população e território associados e denominador certificado pelo perfil curado. Em outros recortes ou arquivos importados, permanece a confirmação explícita. O motor continua validando o pedido.
- **64e0b29:** a seleção de período em operações de competência única é uma etapa focalizada na preparação conversacional da base curada, com retorno explícito à escolha. Os parâmetros e execução só aparecem após essa escolha; não são empilhados junto ao seletor.
- **Comportamento:** redução de confirmações redundantes apenas sob metadados governados e redução da rolagem acumulativa na etapa de período; nenhuma operação estatística, arquivo de dados, SVG, API ou SPEC alterados.
- **Limitações:** ainda falta simplificar integralmente todas as etapas e a apresentação comparativa em linhas distintas. O CI e a inspeção visual do HEAD são necessários antes de considerar estes ajustes aprovados.


### 2026-10-17 · Etapas ativas navegáveis na investigação

- **beb0412:** a área principal da investigação passa a exibir uma etapa por vez: seleção de territórios, preparação ou resultados. As etapas são acessíveis por botões com `aria-current="step"`; a etapa de resultados fica indisponível antes de haver resultado ou execução. O estado de parâmetros e seleção continua no componente pai, sem descarte ao navegar.
- **288f5da:** os comandos conversacionais restritos de navegação ("territórios", "preparação", "resultados", "voltar", "avançar") usam o mesmo estado dos botões, sem reinterpretar os comandos como análises ou recalcular dados.
- **d31f32c:** a navegação global para Resultados e a chegada de um resultado sincronizam a etapa ativa; a última resposta do agente acompanha preparação ou resultados.
- **Governança:** nenhuma alteração em algoritmos, bases, APIs, regras de validação ou exportação. A UI deixa de renderizar simultaneamente os três painéis; isso pode exigir atualização de testes de navegação que pressupunham o empilhamento anterior. Testes de CI e inspeção visual ainda pendentes.


### 2026-10-17 · Rastreabilidade complementar exigida pelo CI #290

- **648fb62** — Comportamento: a escolha do período na base curada torna-se uma etapa focalizada; informações de outras etapas deixam de ser exibidas simultaneamente.
- **f2595cf** — Comportamento: a tabela passa a admitir apresentação vertical dos registros comparados, sem alterar os dados exportados.
- **eef02d6** — Comportamento: a apresentação vertical é habilitada para a operação de comparação territorial.
- **b99948a** — Comportamento: a resposta atual do agente acompanha a preparação ativa, sem exigir rolagem até o rodapé.
- **82bc86e** — Comportamento: sem alteração — correção de fechamento JSX da resposta atual para restabelecer compilação.
- **Validação:** o CI #290 revelou erro de compilação JSX e quatro commits sem registro. As correções foram publicadas; aprovação depende da nova execução do CI.

- **2190e59** — Comportamento: sem alteração — remoção de efeito de rolagem que ainda referenciava o histórico visual já retirado; corrige erro TS2304 identificado no CI #292.

### 2026-10-18 · Inicialização da interface após CI #294

- **280f89d** — Comportamento: sem alteração — corrige a ordem de inicialização de `curatedComparisonReady` em `App.tsx`, posicionando-a antes do uso de `semanticOptions()` nas dependências de efeito avaliadas durante a renderização. Evita acesso à variável antes da inicialização e permite que o diálogo inicial de privacidade seja montado.
- **Diagnóstico:** no CI #294, backend, dados reais, compilação frontend e governança passaram; todos os roteiros Playwright falharam antes de começar, aguardando `Li e concordo`. A falha de renderização é consistente com a referência antecipada observada no código. A correção deve ser confirmada por nova execução de navegador; não se alteraram testes para contornar a falha.

### 2026-10-18 · Bateria de estabilização da navegação progressiva

- **0be6576** — Comportamento: a última resposta do agente permanece visível também na etapa Territórios. Preserva o contexto conversacional quando o usuário alterna entre as etapas, sem reintroduzir o histórico acumulado.
- **64db942, 42d4009, 666ba63, 0481a62, 29ed5a2** — Testes: adequação inicial dos roteiros Playwright para seleção territorial em etapa própria e histórico visual removido. As asserções de seleção e dados continuam.
- **aec647d, 223e393, 7c7d0e, a29a7e4, 08e84d3** — Testes: retorno explícito à etapa Preparação antes de configurar ou executar; substituição de navegação legada pela etapa numerada.
- **bb94ef8, 5417716, 7a33cd8, 14f39e8** — Testes: controles técnicos de dados importados e critérios são acessados pela etapa Preparação; a seleção compartilhada é verificada na etapa Territórios.
- **c9ceb01** — Testes: em base brasileira governada, a confirmação manual de comparabilidade não deve aparecer; a execução continua exigindo resposta analítica válida.
- **402c690** — Testes: comentário esclarece que bases importadas continuam exigindo declaração explícita de comparabilidade.
- **Garantias:** nenhum motor analítico, dado original, regra de pré-exame, API ou SPEC foi alterado. Os testes mantêm verificações de valores, quantidade, seleção, execução e identidade de resultados. A aprovação depende de execução CI completa, inclusive testes de navegador.

- **1fccd12** — Teste: valida reseleção territorial após abrir explicitamente a etapa Territórios e ausência da confirmação manual na base oficial governada.
- **c1bbc5c** — Comportamento: sem alteração — inclui `data-testid="comparison-territory-row"` nas linhas verticais da comparação, permitindo testes sem dependência da estrutura HTML visual.

- **8d52c50, 6e58f4b** — Testes: preservam o rótulo específico das condições avançadas para arquivos importados; a navegação até a etapa Preparação continua explícita. Não se altera o requisito de confirmar coordenadas importadas.

- **79e7daa** — Teste: verifica explicitamente três territórios em registros visuais separados na comparação, além da identidade e dos valores retornados pelo motor.

- **387c746** — Comportamento: a abrangência territorial, parâmetro contextual de fonte, permanece acessível durante a etapa de escolha de período. Corrige o bloqueio de navegação ao alternar base municipal/nacional identificado no teste conversacional do CI #322, sem exibir os demais parâmetros técnicos antecipadamente.

- **60d596d** — Teste: confirma que a descrição curada e o botão de cálculo surgem após a seleção de competência; a escolha de múltiplos períodos usa a navegação explícita de volta e avanço. Corrige expectativa de empilhamento no teste conversacional identificada no CI #324.

- **bc49fa3** — Comportamento: ao trocar de período único para múltiplos períodos, o seletor envia uma única transição `onMultiple(periods)`; o pai já limpa o período único. Evita callbacks conflitantes que poderiam esvaziar a seleção e bloquear Avançar. Detectado na execução conversacional do CI #326; requer validação posterior.

- **d7ff52d** — Teste: após HTTP 200 de análise, aguarda a renderização assíncrona da tabela antes de verificar uma linha; não altera o valor esperado nem o critério de aceitação. Falha de sincronização detectada no CI #328.

### 2026-10-18 — Regularização histórica da tentativa de simplificação revertida

Os commits abaixo foram publicados durante uma tentativa de simplificação da interface, posteriormente **integralmente revertida** pelo commit `40504a3761e739b6d4cf61c656fe4b95ed9c8c92`. Esta entrada registra o histórico exigido pela governança, **não reintroduz as mudanças**. O estado dos arquivos de produto e testes após a reversão corresponde exatamente à árvore da versão estável `5c40232fabbb4e266fdb5911e5aee0afe3a5f08d` (CI #331 aprovado).

- `ff7d023`: unificação experimental das etapas Territórios e Preparação; revertida.
- `68f69be`: redirecionamento experimental dos comandos territoriais; revertido.
- `9d3c7cf`: remoção experimental de confirmações de comparabilidade da interface; revertida.
- `15fba0d`: reformulação experimental de textos e abrangência territorial; revertida.
- `3575484`: ampliação experimental da tipografia operacional; revertida.
- `9678d22`: exibição condicional experimental do formato numérico; revertida.

**Situação atual:** nenhuma dessas alterações permanece no produto. A reversão mantém as regras analíticas, os testes e os dados do baseline aprovado. O presente commit altera exclusivamente este registro documental.
