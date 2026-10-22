# Bloco 2, Etapa 1 — Referências territoriais elegíveis e referência geográfica mais próxima

> **Página única (22/10/2026).** O cartão "Referência mais próxima" e a interface da seção 9 saíram do produto
> com as telas clássicas e ficam como histórico, assim como os roteiros e as medições de navegador citados nas
> seções 10 e 11 (`ui_nearest_smoke.py` e `bench_ui_nearest.py`). Continua a capacidade na API (`/api/analyze`),
> com os testes do backend (`test_nearest_reference.py` e `test_nearest_real_data.py`). Na página única, a
> análise espacial mostra a distância até o membro mais próximo de um conjunto de referência
> ([área de análise](PAINEL_INTEGRADO_INTERFACE.md)); a cobertura dos roteiros que saíram está em [`backend/tests/legado/README.md`](../backend/tests/legado/README.md).

Branch `feat/novos-blocos-incrementais`, a partir de `15aa3c8` (13/10/2026). Esta etapa reúne
as antigas etapas 2A (referências territoriais) e 2B (referência mais próxima) e a atualização
do README sobre a política dos dados do Brasil. A Etapa 2 não foi iniciada.

> **Atualização de 13/10/2026 (Etapa 2).** As pendências da seção 13 foram tratadas em
> [Bloco 2, Etapa 2](BLOCO2_ETAPA2_CRITERIOS_INTEGRACAO.md): critérios combinados, ordenação,
> seleção por posição, faixas e integração final. A referência mais próxima passou a: ler a base
> Brasil diretamente dos arquivos versionados (manifesto governado); usar a camada geográfica
> complementar quando existir (coluna “Coordenada complementada (camada oficial)” e
> `complemento_geografico`, só quando aplicada); e compartilhar, numa mesma requisição, os insumos
> de referências e coordenadas entre o pré-exame e o cálculo. Resultados e chaves desta etapa não
> mudam sem a camada. Com a camada oficial incorporada (versão 1), o resultado real de 202406
> descrito abaixo corresponde à base original sem complemento; com a camada, as 2.007 referências
> têm coordenada avaliável e os 5.570 alvos têm o mínimo do conjunto completo (Etapa 2, seção 3.5).

Commits da etapa, em ordem: `d320a86` (motor), `d9c525a` (comando conversacional), `2f70f47`
(medição de desempenho), `ca85c4f` (correção do separador decimal), `f1c73e5` (interface),
`e68e8e5` (jornada no navegador e CI), `8fe7316` (responsividade no navegador), seguidos da
atualização do README e deste documento.

## 1. Escopo

Entregue:

- definição do conjunto de referências por **lista explícita** (nome ou código) ou por **critério
  simples de densidade** aplicado aos dados (CAP-REF-01 com critério atômico de CAP-SUB-01);
- para cada território-alvo, a **referência geograficamente mais próxima**, com código,
  distância geodésica direta em quilômetros, cobertura e limitações (CAP-ESP-01 e CAP-ESP-02);
- funcionamento com a base Brasil (recorte municipal) e com bases importadas (CSV, XLS, XLSX);
- integração à conversa, com cartão próprio, comando determinístico, controles simples,
  exportação de tabela e metadados, histórico, retomada e reutilização dos conjuntos;
- testes sintéticos, reais (opt-in), de navegador (inclusive na CI), de equivalência e de
  desempenho; README e esta documentação.

Fora do escopo desta etapa: critérios combinados, réguas e faixas de distância, recortes e
rankings por distância e integração final (Etapa 2); mapas, bolhas e gráficos espaciais;
distância viária e tempo de deslocamento.

## 2. Funcionalidades reutilizadas

| Componente existente | Uso nesta etapa |
| --- | --- |
| `data_contract.scoped` e o memo por requisição (`request_memo.per_request`) | Recorte dos alvos por período, categoria e seleção, sem recalcular dentro da mesma requisição |
| `territorial_selection.territory_catalog` | Identidade `code:`/`name:`, rótulos, estados derivados do código e motivos de seleção ambígua, para alvos **e** referências |
| `data_contract.canonical_crs` | Aliases governados de SIRGAS2000 (sem diferença de caixa e espaços nas pontas): `SIRGAS2000`, `SIRGAS 2000`, `SIRGAS-2000`, `SIRGAS_2000` |
| `data_contract.numbers` e a regra de vírgula declarada | Quantidade e população do critério; a mesma regra (vírgula só com separador escolhido ou verificado nos dados) vale para as coordenadas |
| `semantic_bridge.preflight` e `validate_operation` | Matriz de aplicabilidade e gates; `/api/analyze` revalida antes de executar |
| `analysis_premises.apply_premises` (com `brazil_catalog_profile.apply_curated_options`) | Perfil governado da base Brasil, campo a campo (unidade, população, objeto), e premissas da análise para uploads; nenhuma confirmação |
| `main.compute` (`_result`, metadados, avaliabilidade, chave de execução) | Resultado no mesmo formato das demais análises, com `metadata.nearest_reference` acrescentado |
| Histórico, retomada, reutilização, CSV e "Método e parâmetros" | Sem mudança de contrato; o estado das referências entra no instantâneo da preparação |
| `TerritorialSelection`, `PeriodSelection`, `InlineChoice` e o carrossel | Mesmos controles; a seleção de referências é uma segunda instância, em âmbar |
| Gramática local de exploração (`exploration.py`) | Novo comando que só prepara a operação e os alvos |
| Instalador com manifesto SHA-256 e o harness de equivalência da tarefa de latência | Dados reais por cópia validada; comparação integral das respostas antes e depois |

## 3. Contratos normativos (IMPLEMENTATION_SPEC v1.2.4)

| Requisito | Implementação | Verificação |
| --- | --- | --- |
| CAP-REF-01 — origem das referências | Lista explícita do usuário ou critério autorizado aplicado aos dados; CFG-REF vazio; sem modo escolhido, pendência (equivalente a PARAMETRO_FALTANTE). Forma (`LISTA_EXPLICITA`/`CRITERIO`), origem (`MANIFESTACAO_USUARIO`/`CRITERIO_AUTORIZADO_APLICADO_AOS_DADOS`) e parâmetros registrados | `test_explicit_list_with_references_in_other_state_and_target_also_reference`, `test_density_criterion_is_exact_at_the_boundary`, `test_preflight_capability_states_follow_the_contract` |
| CAP-REF-01 — proibições | O LLM não escolhe referências; nenhuma referência, densidade, região ou distância padrão; a condição não tem caráter normativo; o sentido de "referência" não é decidido quando ambíguo | `test_llm_interpretation_contract_is_not_widened`, `test_conversation_prepares_only_the_operation_and_targets` |
| CAP-SUB-01 — critério atômico | Operadores `<`, `≤`, `>`, `≥`, `=`, `≠`, sempre explicitados; valor sem unidade no único contexto da densidade (por 1.000 habitantes); comparação exata em frações (`quantidade × 1.000` contra `valor × população`) | `test_density_criterion_is_exact_at_the_boundary`, `test_criterion_candidates_without_denominator_are_listed_not_assumed`, teste real com recálculo independente |
| CAP-ESP-01 — distância | Problema geodésico inverso de Karney (GeographicLib, via pyproj), elipsoide GRS80 (a = 6.378.137 m, 1/f = 298,257222101), quilômetros em precisão integral | `test_geodesic_method_is_grs80_and_agrees_with_independent_vincenty` |
| RQ-DAD-25 — coordenadas | Faixas −90..90 e −180..180; ausência → `SEM_INFORMACAO_ESPACIAL`; fora da faixa ou não numérica → `COORDENADA_INVALIDA`; latitude e longitude estabelecidas por regra (nome e formato decimal único, sem rebaixar a coluna por valor fora da faixa), pelo perfil oficial ou pela escolha do usuário | `test_invalid_reference_gives_partial_minimum_never_presented_as_complete`, `test_targets_without_valid_coordinates_stay_in_universe` |
| RQ-DAD-26/27 — referencial | Sem referencial: pendência (REFERENCIAL_GEODESICO), nada presumido, salvo na versão governada da base Brasil, em que SIRGAS 2000 é premissa interna do perfil (configuração contextual autorizada pelo responsável pelo produto em 18/10/2026), registrada nas notas e em `governed_premises`; aliases governados canonicalizados; referencial informado e não suportado: execução recusada com motivo, sem transformação, aproximação ou substituição, e a base segue utilizável nas demais análises | `test_unsupported_reference_systems_are_never_transformed`, `test_governed_aliases_are_canonicalized`, `test_reference_system_is_never_presumed`, `test_governed_version_resolves_crs_and_decimal_separator_only_in_distance_analyses` |
| CAP-ESP-02 — mais próxima | Distância por par com avaliabilidade; `minimo_completo` e `minimo_avaliaveis` distintos; qualificador "entre as referências avaliáveis" obrigatório; COBERTURA_PARCIAL; empates preservados; sem inferência por limites | `test_invalid_reference_gives_partial_minimum_never_presented_as_complete`, `test_ties_preserve_every_reference`, `test_exact_search_equals_exhaustive_search` |
| TPL-11 / V-06 | Limitação `DISTANCIA_GEODESICA_DIRETA` com o texto de TPL-11 em notas, descrição e limitações estruturadas | testes de API e de navegador |
| RQ-CAP-08 — desfecho | `RES-LIM` quando há resultado (a limitação de distância direta é analítica); conjunto vazio → `BLQ-DEP` (`CONJUNTO_REFERENCIAS_VAZIO`); nenhuma referência avaliável → `BLQ-DAD` | `test_empty_reference_set_preserves_targets_without_distances`, `test_references_all_without_coordinates_produce_no_analytical_result` |
| RQ-ORQ-06 — chave de execução | A nova capacidade não altera a origem descrita da base Brasil (`default_scopes`), preservando a chave de execução das análises existentes | `test_engine_only_capability_keeps_the_existing_source_descriptor`, harness de equivalência |

## 4. Método geodésico

- **Cálculo.** `pyproj.Geod(a=6378137.0, rf=298.257222101)` (pyproj 3.7.2, PROJ 9.5.1), que usa
  a solução de Karney do problema inverso. A distância em metros é dividida por 1.000 sem
  arredondamento; o arredondamento ocorre apenas na apresentação (até seis casas na tabela). O
  CSV e o JSON exportados trazem a precisão integral.
- **Conferência independente.** Em 200 pares aleatórios no Brasil, a diferença para uma
  implementação própria de Vincenty ficou abaixo de 1 mm. O meio meridiano do GRS80 (polo a polo)
  confere com 20.003.931,4586 m.
- **Busca exata da mais próxima.** A corda 3D entre dois pontos da superfície do elipsoide nunca
  excede a geodésica entre eles, porque o segmento de reta é o menor caminho no espaço. Para cada
  alvo, em blocos de 128 alvos:
  1. calculam-se as cordas até todas as referências avaliáveis (coordenadas ECEF no GRS80, h = 0);
  2. calculam-se as geodésicas das quatro menores cordas e toma-se a menor geodésica obtida como
     limite;
  3. calculam-se as geodésicas de **todas** as referências cuja corda não supera o limite,
     ampliado por uma margem de 10⁻¹² relativa mais 1 µm contra erros de ponto flutuante na corda;
     o limite é atualizado e o passo se repete até não restar candidata.
  Toda referência descartada tem corda maior que o limite, logo geodésica maior que a menor
  calculada: não pode ser a mais próxima nem empatar. A margem só amplia o conjunto calculado.
- **Mínimo e empates.** Decididos pelas geodésicas calculadas, por igualdade exata de ponto
  flutuante, sem tolerância nem arredondamento.
- **Equivalência com a busca exaustiva.** Exigida nos testes (cenários aleatórios no Brasil e no
  mundo; polos, linha de data, quase antípodas e pontos coincidentes; empates simétricos; seis
  referências coincidentes; anel de 64 referências quase equidistantes, em que a ordem das cordas
  difere da ordem geodésica) e em todas as medições de desempenho com dados reais.

## 5. Conjunto de referências (CAP-REF-01)

- **Modo obrigatório.** Sem modo escolhido, a análise fica pendente. Nenhum modo, operador ou valor
  vem pré-selecionado.
- **Lista explícita.** Identificadores do catálogo territorial (`code:` quando o código está
  associado, senão `name:`). Lista vazia: pendência. Identificador inexistente: recusa explícita.
  Nomes homônimos sem código e seleções com hierarquia ambígua: recusa, com pedido do código.
  Referências podem estar em qualquer estado.
- **Critério simples.** Densidade por 1.000 habitantes comparada a um valor (vírgula ou ponto,
  finito, não negativo, até 32 caracteres), na competência e na categoria escolhidas (categoria
  única ou escolhida; categoria inexistente é recusada). Exige quantitativo e população
  estabelecidos (regra, perfil oficial ou escolha), unidade de contagem escolhida e a premissa do
  denominador (população da mesma linha), aplicada pelo backend; unidades em pessoas
  exigem valores inteiros. Cada candidato recebe `ATENDE`, `NAO_ATENDE` ou `NAO_AVALIAVEL`
  (`DADO_AUSENTE`, `DENOMINADOR_AUSENTE`, `DENOMINADOR_ZERO`). Candidatos não avaliáveis ficam
  listados à parte: não entram nem são excluídos por presunção. Exemplo da exatidão: 59/25.000 ×
  1.000 resulta em 2,3600000000000003 em ponto flutuante, mas atende "≥ 2,36" na comparação exata.
- **Universos distintos.** `universo_alvos` (seleção ou todos os territórios do período),
  `universo_candidatos` (lista do usuário ou territórios do período e da categoria do critério),
  `membros` (conjunto elegível) e `referencias_nao_avaliaveis` (membros sem coordenada avaliável).
- **Alvo que também é referência.** Não é excluído automaticamente: a distância zero até si mesmo
  é calculada, registrada (`alvo_e_referencia`) e informada em nota.

## 6. Estrutura da resposta

Cada linha da tabela (CSV) traz: Território-alvo, Código do alvo, Referência mais próxima,
Código da referência, Distância (km), Alcance (conjunto completo, entre as avaliáveis ou não
avaliável), Referências avaliáveis ("n de N"), Empate, Alvo também é referência e Condição.
As métricas contam alvos, referências autorizadas, mínimos do conjunto completo, mínimos só entre
as avaliáveis e não avaliáveis.

`metadata.nearest_reference` (exportado integralmente em "Método e parâmetros") contém:
`metodo` (capacidades, versão, algoritmo, implementação, referencial, elipsoide, unidade,
precisão e busca), `periodo_geometria`, `universo_alvos`, `conjunto_referencias` (forma, origem,
critério, universo de candidatos, membros com condição espacial e resumo da avaliação do
critério), `referencias_nao_avaliaveis`, `cobertura_referencias` (um registro por alvo, com
`minimo_completo` e `minimo_avaliaveis`), `cobertura`, `limitacoes`, `desfecho`,
`geodesicas_calculadas` e `pares_avaliaveis`. Com alvo avaliável, os motivos das referências
não avaliáveis são os mesmos para todos os alvos; cada registro aponta a lista do resultado em
vez de repeti-la, o que reduziu a resposta de 5.570 alvos de 9,6 MB para 6,5 MB.

## 7. Avaliabilidade, cobertura parcial, empates e conjunto vazio

- **Coordenadas por território.** Um território só tem coordenada válida se todas as suas linhas
  do período forem válidas e idênticas. Coordenadas válidas divergentes no mesmo período são
  tratadas como `COORDENADA_INVALIDA` (leitura adotada; a SPEC só prevê `SEM_INFORMACAO_ESPACIAL`
  e `COORDENADA_INVALIDA`). Referência listada sem registro no período: `SEM_REGISTRO_OBSERVADO`.
- **Referência não avaliável.** `minimo_completo` fica `NAO_AVALIAVEL`
  (`DEPENDENCIA_NAO_AVALIAVEL`) para todos os alvos; `minimo_avaliaveis` é apresentado com o
  qualificador "entre as referências avaliáveis", limitação `COBERTURA_PARCIAL` e a lista das
  referências não avaliáveis com motivos. O segundo nunca substitui o primeiro em silêncio.
- **Alvo não avaliável.** Permanece no universo, com os dois mínimos não avaliáveis e o motivo do
  alvo; os demais alvos seguem calculados.
- **Ausência nunca vira zero.** Distância não avaliável é nula na tabela e no CSV, "Não avaliável"
  na tela e sem barra no gráfico.
- **Empates.** Todas as referências empatadas são apresentadas ("Sim (n referências)").
- **Conjunto vazio** (critério que nenhum candidato atende): nenhuma distância é calculada, o
  universo-alvo é preservado e os dois mínimos ficam `NAO_AVALIAVEL` com detalhe
  `CONJUNTO_REFERENCIAS_VAZIO`; desfecho `BLQ-DEP`.
- **Nenhuma referência avaliável:** desfecho `BLQ-DAD`. Com resultado: `RES-LIM`. Situação de
  avaliabilidade: `AVALIAVEL` só com todos os mínimos completos e sem outras limitações;
  `AVALIAVEL_COM_LIMITACOES` com resultado parcial; `NAO_AVALIAVEL` sem resultado.

## 8. Períodos e dados reais

- **Período explícito.** As coordenadas e o critério vêm de uma única competência; com mais de
  uma, a escolha é obrigatória, e a combinação de períodos é recusada. Coordenadas de outras
  competências não são tratadas como equivalentes: o teste real confirma que 201401 e 202406 usam
  cada um a sua geometria para municípios cujas coordenadas mudam.
- **Granularidade.** A capacidade existe só no recorte municipal (o único com coordenadas) e não
  soma nem mistura contagens entre as fontes nacional e municipal.
- **Resultado real** (202406, critério densidade ≥ 2,36, categoria MEDICINA; base original sem
  complemento): 5.570 alvos;
  2.007 referências atendem ao critério, das quais 4 sem coordenada válida; por isso,
  `minimo_completo` fica não avaliável para todos os alvos, e 5.564 recebem a mais próxima
  "entre as referências avaliáveis" com `COBERTURA_PARCIAL`; os 6 municípios com coordenadas
  fora do intervalo permanecem como `COORDENADA_INVALIDA`; 2.007 alvos também são referências
  (distância zero); desfecho `RES-LIM`; 22.256 geodésicas calculadas para 11,1 milhões de pares.
- **Conferências independentes** (`test_nearest_real_data.py`): conjunto do critério igual ao
  recálculo em frações sobre os textos originais; referências e alvos não avaliáveis iguais aos
  identificados por Decimal; amostra de alvos igual à busca exaustiva com pyproj; densidades do
  critério iguais às da análise de densidade do Bloco 1. Os SHA-256 dos originais são conferidos
  antes e depois.

## 9. Interface

> Histórico: esta tela saiu do produto com as telas clássicas em 22/10/2026 (ver a nota no início do documento).

A jornada completa ocorre na conversa:

1. **Base:** "Usar dados do Brasil" ou importação de arquivo.
2. **Alvos:** seleção compartilhada (título "Municípios-alvo", em azul) ou nomes citados no
   comando; sem seleção, todos os municípios do período são alvos.
3. **Modo:** "Lista de municípios por nome ou código" ou "Critério simples de densidade".
4. **Referências:** segunda seleção, em âmbar ("Municípios de referência"), ou operador e valor
   por 1.000 habitantes, sem sugestão.
5. **Escolhas:** período; em bases importadas e em outras versões, também o referencial
   (SIRGAS2000 sem presunção). O separador decimal das coordenadas é verificado nos dados (vírgula
   quando as coordenadas a usam e quantidades e populações não têm vírgula), com nota no resultado;
   só com formato misto ele vira escolha. Na versão governada da base Brasil, os dois são premissas
   internas, e o resumo da preparação mostra "Referencial: SIRGAS 2000 (premissa da base oficial)".
6. **Execução:** botão desabilitado até o pré-exame liberar; indicador "Preparando seu
   diagnóstico"; uma execução por vez, mesmo com clique duplo.
7. **Consulta:** métricas, tabela, notas de método e limitações.
8. **Reutilização:** "Usar como lista de referências" ou "Usar como municípios-alvo";
   histórico, retomada de parâmetros e recuperação sem recálculo.
9. **Exportação:** CSV da tabela e JSON de método e parâmetros.

**Conversa.** "Calcule a referência mais próxima de Manaus, Tefé e Parintins" prepara a operação
e os alvos citados, sem criar referências nem executar. Sem alvos citados, apenas seleciona a
análise. Nomes após "entre", que poderiam ser candidatos a referência, e critérios em texto livre
geram pedido de esclarecimento. O contrato do LLM não foi ampliado: o provedor não conhece esta
capacidade e não recebe seu estado (limitação registrada na seção 12).

Nenhuma arquitetura visual nova, mapa ou bolha: o cartão entra por último no carrossel
existente, e o gráfico genérico de barras mostra as distâncias dos primeiros 12 alvos.

## 10. Testes

- **Backend sintético** (`test_nearest_reference.py`, 34 testes): método geodésico e Vincenty;
  busca exata × exaustiva (3 sementes, 6 cenários cada); lista com referência em outro estado e
  alvo também referência; referência e alvos sem coordenada; coordenadas conflitantes; empates;
  fronteira exata do critério; candidatos sem denominador; conjunto vazio; nenhuma referência
  avaliável; referenciais não suportados, aliases e não presunção; período explícito e
  geometria por período; compatibilidade de categoria e período; vírgula decimal (inclusive ponto
  declarado com vírgulas); referências inexistentes, ambíguas e homônimas; independência entre
  alvos e referências; estados do pré-exame; contrato do LLM inalterado; determinismo; versão da
  base alterada após a preparação; descritor da base preservado; comando conversacional.
- **Dados reais** (`test_nearest_real_data.py`, 2 testes opt-in com `ADT_REAL_DATA_DIR`).
- **Navegador** (`ui_nearest_smoke.py`, no job `ui-block1` da CI): base Brasil sintética com
  comando, critério, clique duplo, exportações, reutilização e retomada; base importada fictícia
  com lista explícita, vírgula decimal, referência e alvos sem coordenada, coordenada que muda
  entre competências e distâncias conferidas por pyproj fora da API; larguras de 390 e 768 px.
- **Mutações** aplicadas temporariamente ao motor, todas detectadas: comparação do critério em
  ponto flutuante; mínimo completo afirmado com referência não avaliável; busca limitada às
  quatro primeiras cordas; empates truncados; vírgula aceita sem declaração. A mutação da busca
  limitada sobreviveu aos cenários aleatórios e motivou o anel de 64 referências e o empate de
  seis.
- **Equivalência:** respostas completas da API em 76 casos (Bloco 1), 76 (nacional sintética) e
  77 (real) iguais às do baseline `15aa3c8`, exceto o acréscimo da capacidade `nearest` na matriz
  de aplicabilidade. A primeira captura revelou chaves de execução alteradas pela inclusão em
  `default_scopes`; a capacidade passou a ter recorte próprio e as chaves voltaram a coincidir.

**Regressão final** (código de `8fe7316`, mesma árvore deste documento):

| Verificação | Resultado |
| --- | --- |
| pytest do backend com fontes sintéticas | 250 passaram, 22 omitidos (testes reais opt-in) |
| pytest completo com as duas fontes reais (`ADT_REAL_DATA_DIR`) | 272 passaram |
| Build do frontend (TypeScript + Vite) | passou |
| Job `ui-block1` reproduzido localmente (smoke, regressão, mais próxima, integração com Gemini simulado) | passou |
| Job `ui-conversational` reproduzido localmente | passou |
| Jornada do Bloco 1 com dados reais (`ui_block1_smoke.py`, 62 municípios do AM) | passou |
| Referência mais próxima no navegador com dados reais (`bench_ui_nearest.py`) | passou |
| Equivalência da API com `15aa3c8` (Bloco 1, nacional sintética, real) | 76, 76 e 77 casos; 0 diferenças além da capacidade acrescentada |
| SHA-256 dos originais e das cópias instaladas | inalterados |
| Sete roteiros anteriores à interface conversacional | falham no mesmo passo e linha que em `15aa3c8` e no baseline `a202be1`; não são regressões |
| CI no GitHub | runs 194, 195 e 196 verdes; o job `ui-block1` executa `ui_nearest_smoke.py` |

Casos adversariais pedidos e onde são cobertos:

| Caso | Cobertura |
| --- | --- |
| Conjunto vazio | `test_empty_reference_set_preserves_targets_without_distances` |
| Referência sem coordenada válida | `test_invalid_reference_gives_partial_minimum_never_presented_as_complete`; real (4 referências); navegador (base importada) |
| Alvo sem coordenada válida | `test_targets_without_valid_coordinates_stay_in_universe`; real (6 municípios); navegador |
| Coordenadas conflitantes | `test_conflicting_coordinates_in_the_period_are_not_evaluable` |
| Referências com o mesmo nome | `test_unknown_ambiguous_and_homonym_references_require_clarification` |
| Alvo também referência | `test_explicit_list_with_references_in_other_state_and_target_also_reference`; real (2.007 alvos); navegador |
| Empates | `test_ties_preserve_every_reference`; empates simétricos e seis coincidentes em `test_exact_search_equals_exhaustive_search`; navegador |
| Referências em estados diferentes | `test_explicit_list_with_references_in_other_state_and_target_also_reference` (referência no PA para alvos do AM) |
| Período inexistente | `test_period_must_be_explicit_and_existing_and_coordinates_come_from_it` |
| Categorias ou períodos incompatíveis | `test_category_and_period_compatibility_of_the_criterion` |
| Distâncias extremas | polos, linha de data e quase antípodas em `test_exact_search_equals_exhaustive_search`; meio meridiano no teste do método |
| Referências parcialmente avaliáveis | `test_invalid_reference_gives_partial_minimum_never_presented_as_complete`; real; navegador |
| Referencial não autorizado | `test_unsupported_reference_systems_are_never_transformed` |
| Versão ou fonte alterada após a preparação | `test_brazil_source_version_change_after_preparation_is_refused` |

## 11. Desempenho

Dados reais, competência 202406. Busca exata e exaustiva com resultado idêntico em todas as linhas
em que a exaustiva foi executada:

| Referências | Alvos | Geodésicas | Exata | Exaustiva | Pico de memória (exata) |
| --- | --- | --- | --- | --- | --- |
| 3 | 3 / 100 / 1.000 / 5.564 | todas as combinações | 0,001 / 0,005 / 0,058 / 0,45 s | 0,001 / 0,028 / 0,30 / 1,5 s | até 0,8 MiB |
| critério (2.003 avaliáveis) | 3 / 100 / 1.000 / 5.564 | 12 / 400 / 4.000 / 22.256 | 0,003 / 0,015 / 0,22 / 1,36 s | 0,012 / 0,32 / 3,5 / 20,2 s | até 16,9 MiB |
| todas (5.564) | 3 / 100 / 1.000 / 5.564 | 12 / 400 / 4.000 / 22.256 | 0,005 / 0,037 / 0,66 / 1,67 s | 0,029 / 0,91 / 7,7 s / não executada | até 45,7 MiB |

Requisição completa pela API (critério ≥ 2,36; mediana de 3 repetições; inclui leitura,
pré-exame, critério, busca e serialização): 3 alvos 3,24 s (400 KiB); 100 alvos 3,64 s (507 KiB);
1.000 alvos 4,16 s (1,5 MB); 5.570 alvos 6,14 s (6,5 MB). RSS máximo do processo: 362 MiB.
Script: `backend/tests/bench_nearest.py`.

Navegador com dados reais (`backend/tests/bench_ui_nearest.py`):

| Caso | Requisição | Resposta → tabela | Maior tarefa longa | Digitação após o resultado |
| --- | --- | --- | --- | --- |
| 3 alvos | 3,5 s | 72 ms | nenhuma | 4,5 ms |
| 62 alvos (AM) | 3,7 s | 80 ms | nenhuma | 3,4 ms |
| 5.570 alvos | 6,4 s | 760 ms | 318 ms (bloqueio total 426 ms) | 19 ms |

Indicador de processamento visível e uma única execução em todos os casos. No caso de 5.570
alvos, o bloqueio vem sobretudo da cópia profunda do resultado para o histórico
(`structuredClone`, cerca de 120 ms) e da lista oculta de territórios do resultado, ambos
preexistentes e comuns a qualquer análise com todos os municípios. A serialização dos metadados
para a tela passou a ser memorizada e resume a cobertura por alvo; o JSON exportado permanece
integral.

## 12. Decisões, leituras adotadas e limitações

Decisões e leituras adotadas:

- coordenadas válidas divergentes no mesmo período → `COORDENADA_INVALIDA`;
- candidatos não avaliáveis pelo critério ficam listados à parte e **não** tornam o
  `minimo_completo` não avaliável, porque não integram o conjunto autorizado (CAP-REF-01).
  **Resolvido na Etapa 2:** nesta operação o campo continua relativo às referências confirmadas;
  nos critérios combinados, a condição de distância fica `NAO_AVALIAVEL` enquanto houver
  candidatos de elegibilidade desconhecida, salvo aceitação explícita do alcance restrito, e as
  coberturas da elegibilidade e geográfica e o alcance da afirmação são registrados à parte;
- referencial informado e não suportado → execução recusada com motivo (equivalente a
  BLQ-MET/METODO_NAO_INCORPORADO), sem objeto de resultado estruturado para a recusa;
- ponto decimal declarado com coordenadas que têm vírgula → recusa explícita;
- no comando conversacional, nomes citados são sempre alvos;
- `default_scopes` da base Brasil mantém as dez capacidades do contrato, para não alterar a chave
  de execução das análises existentes; a interface resolve o recorte municipal da nova capacidade.

Limitações:

- o critério usa coluna de quantitativo; contagem por identificador individual não foi habilitada;
- o LLM não foi ampliado: pedidos livres antes da escolha da base seguem ao canal do LLM, que não
  conhece a capacidade; a análise é escolhida pelo cartão ou pelo comando determinístico;
- o critério é definido pelos controles; o vocabulário de operadores em texto livre não é
  interpretado;
- a resposta de 5.570 alvos tem 6,5 MB e provoca uma tarefa longa de cerca de 0,3 s no navegador;
- distância apenas geodésica direta (sem trajeto viário, tempo ou acessibilidade);
- os roteiros de navegador anteriores à interface conversacional, que fixam dez cartões, já
  falhavam no baseline e não fazem parte da CI;
- um arquivo importado precisa permanecer no disco durante a sessão, porque cada pré-exame o
  reenvia (comportamento preexistente);
- procedência primária, licença e autorização de redistribuição da base Brasil seguem pendentes
  (ver README).

## 13. Pendências para a Etapa 2

- critérios combinados de referência (árvores de CAP-SUB-01) e pertença a classes produzidas por
  outras capacidades;
- réguas e faixas de distância, recortes e rankings por distância e comparações derivadas;
- integração final com as explorações do Bloco 1 e com a Etapa 2;
- decisão sobre candidatos não avaliáveis do critério (seção 12; resolvida na Etapa 2);
- fonte governada de referências (CFG-REF), se autorizada;
- eventual ampliação do contrato do LLM para esta capacidade, somente com autorização;
- redução opcional do custo de renderização de resultados muito grandes no navegador.
