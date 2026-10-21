# Painel integrado de bolhas

Decisões do responsável pelo produto de 21/10/2026: gráfico de bolhas autorizado, num painel próprio ao qual o usuário
acrescenta municípios. A população aparece sempre no tamanho da bolha. Os eixos dependem das análises escolhidas:
densidade ou quantidade e, com a referência, a distância até ela. Conjuntos de municípios agregados viram uma bolha, e a
variação percentual entre duas competências se integra ao desenho. A SPEC admite o gráfico de bolhas pelo
**Adendo BOL-20261021** (fim de `IMPLEMENTATION_SPEC.md`), que dá a redação vigente de RQ-REP-10 e o nome vigente de
CAP-REP-02. O corpo v1.2.4 continua literal, porque o catálogo CFG-DOC o confere pelo SHA-256 e pelos localizadores do
Anexo A.

Este documento descreve o motor e as rotas. A tela do painel tem documento próprio.

## Motor e rotas

### Visão geral

- **Rotas:** `POST /api/painel` e `POST /api/painel/referencias` (`backend/main.py`). O motor fica em
  `backend/painel.py`.
- **Base:** só a base Brasil oficial (fonte municipal), numa competência e numa categoria. Arquivo importado recebe 422:
  "O painel integrado usa só a base Brasil oficial (fonte municipal) nesta versão; …".
- **Números:** todo número vem do motor, pelas mesmas funções das análises, sem fórmula paralela. A tela só posiciona,
  filtra e desenha (RQ-REP-09). A régua "abaixo de / acima de" é filtro visual sobre os valores devolvidos e não inicia
  análise (RQ-REP-06).
- **Privacidade:** nenhum nome, valor, campo ou arquivo vai ao provedor de IA. As rotas não chamam o Gemini.

### Formulário (as duas rotas)

Multipart, no padrão de `/api/analyze`:

| Campo | Uso |
|---|---|
| `dataset` | `brazil` (obrigatório). |
| `scope` | `municipal` (ou `auto`, que no painel é municipal). |
| `dataset_version` | Versão da inspeção. Integridade conferida pelo manifesto a cada pedido; versão divergente → 422 "A base Brasil foi atualizada. …". |
| `mapping` | Mapeamento da inspeção (`suggested_mapping`). Precisa ser o do perfil oficial: código IBGE, município, período, categoria, quantidade e população e, com a referência, latitude e longitude. Vazio vale o perfil oficial; papel sem coluna é ignorado. |
| `options` | JSON descrito em cada rota. Chave desconhecida → 422 "Parâmetro não reconhecido no painel: …". |
| `geo_version` | Opcional, só na rota 1 com referência: como em `/api/analyze`, recusa o pedido se a camada complementar de coordenadas mudou depois da preparação. |
| `X-ADT-Session` | Cabeçalho opcional, só na rota 1: registra o evento de sessão `CONFIRMACAO`, como `/api/analyze`. |

`sheet` e `context_revision` são aceitos e não mudam o cálculo.

### Rota 1: `POST /api/painel`

`options`:

| Chave | Regra |
|---|---|
| `competencia` | Obrigatória quando a base tem mais de uma competência; precisa existir na versão → senão 422 "Competência inexistente nesta versão da base: …". |
| `competencia_inicial` | Opcional. Precisa existir e ser anterior a `competencia` (422 "… precisa ser anterior …"). Liga a variação (CAP-TMP-01), com as premissas temporais do perfil oficial (comparabilidade temporal e identidade territorial verificada nos dados). |
| `categoria` | Opcional com uma categoria na base (MEDICINA); com mais de uma, obrigatória. |
| `base` | `{"municipios": {"todos", "estados", "ids"}}`, a forma de `options.abrangencia.municipios`, com as mesmas regras (`territorial_levels.parse`). Ids no formato `code:<código IBGE>`, existentes na base (senão 422 "Municípios inexistentes …"). Pode ficar vazia quando há conjuntos. |
| `conjuntos` | Opcional; lista de até 50 `{id, rotulo, membros}`. O `id` tem até 64 letras, números, `_` ou `-`, sem repetir. O `rotulo` tem até 120 caracteres. Os `membros` são pelo menos dois municípios existentes, que podem estar fora de `base` (sem membros → 422 "… está sem membros …"). |
| `referencia` | Opcional; `{membros, criterio}`. Um membro: referência município; dois ou mais: conjunto de referência. `criterio` (`{atributo, ordem}`, opcional) só registra a origem (CAP-REF-01); ver extensões abaixo. Sem `referencia` não há distância. |

Resposta 200 (chaves fixas):

| Campo | Conteúdo |
|---|---|
| `competencia`, `competencia_inicial`, `categoria` | Os efetivos; `competencia_inicial` é `null` sem variação. |
| `versao_base` | Versão verificada da base (SHA-256 das fontes). |
| `chave_execucao` | SHA-256 reproduzível: dados das competências usadas, fonte, mapeamento, pedido normalizado, premissas, métodos e camada de coordenadas válida (como em `/api/analyze`). |
| `referencia` | `null` ou `{tipo: "municipio" \| "conjunto", membros: [{id, rotulo}], origem}`. |
| `itens` | Municípios na ordem do código IBGE (RQ-REP-03): a base e os membros da referência. Depois, os conjuntos, na ordem do pedido. |
| `dominios` | `[mínimo, máximo]` dos valores avaliáveis devolvidos, ou `null` sem nenhum. |
| `notas`, `limitacoes` | Textos de método e premissas; códigos de limitação. |

Item `municipio`: `id`, `tipo`, `rotulo` ("MANAUS (AM)"), `uf`, `populacao`, `quantidade`, `densidade`,
`distancia_km`, `inicial`, `variacao_percentual`, `avaliavel`, `motivos`, `referencia`.

Item `conjunto`: `id`, `tipo`, `rotulo`, `membros` (na ordem do pedido), `populacao`, `quantidade`, `densidade`,
`contagem` (sempre `SOMA_DOS_COMPONENTES`), `distancia_km`, `distancia_km_max`, `inicial`, `variacao_percentual`,
`avaliavel`, `motivos`, `referencia`.

Regras dos campos:

- **Valores na `competencia`:** `populacao`, `quantidade` e `densidade` saem de `data_contract.prepare`, a mesma
  preparação da análise de densidade (CAP-IND-01 e CAP-IND-02). A densidade é quantidade ÷ população × 1.000, por 1.000
  habitantes, em precisão integral; a tela arredonda ao exibir. Contagens inteiras vêm como inteiros. Um município sem
  registro na competência fica com os três valores `null` e o motivo `SEM_REGISTRO_OBSERVADO`, nunca zero.
- **Conjunto (CAP-AGR-01):** `main._compute(..., "aggregate")`, a agregação municipal. Soma as quantidades e as
  populações dos membros com registro (cada município uma vez) e calcula a densidade do conjunto; o tipo de contagem é
  `SOMA_DOS_COMPONENTES`, com possível dupla contagem (RQ-REP-14). Se algum membro não tem registro, o agregado é parcial
  sobre os demais, com o motivo `AGREGADO_PARCIAL` e a lista dos de fora; sem nenhum membro com registro, os valores
  ficam `null`.
- **`distancia_km` (CAP-ESP-01 e CAP-ESP-02):** distância geodésica no GRS80 (SIRGAS 2000, premissa governada da base
  oficial), por `nearest_reference.territory_coordinates` e `nearest_exact`, como em `compute_nearest`, com as
  coordenadas da `competencia` e a camada complementar como na análise espacial.
  - Com um conjunto de referência, vale a distância até o membro mais próximo, pelo mínimo do conjunto completo
    (`minimo_completo`).
  - Se um membro da referência não tem coordenada válida, nenhuma distância é avaliável: `null` com
    `DEPENDENCIA_NAO_AVALIAVEL`, sem trocar pelo mínimo entre as avaliáveis.
  - Município sem coordenada válida: `null`, com `SEM_INFORMACAO_ESPACIAL` ou `COORDENADA_INVALIDA`.
  - Os membros da referência entram como itens, com distância 0 e `referencia: true`.
  - **Num conjunto base:** `distancia_km` é a do membro mais próximo e `distancia_km_max`, a do mais distante, no mesmo
    suporte dos valores do conjunto. Basta um membro sem coordenada para as duas ficarem `null`, com o motivo. O conjunto
    cujos membros são exatamente os da referência recebe `referencia: true`.
- **`variacao_percentual` (CAP-TMP-01, DA-14):** `temporal_change.change` sobre os valores exatos (Fraction; a
  densidade sai da quantidade e da população, sem passar pelo float), para população, quantidade e densidade.
  - Valor inicial zero: `null`, com `BASE_ZERO`.
  - Sem registro na competência inicial: `null`, com `SEM_REGISTRO_OBSERVADO`.
  - Conjunto com membros efetivos diferentes nas duas competências: `null`, com `INCOMPARABILIDADE`; cada valor vale
    isoladamente.
  - `inicial` traz os valores da `competencia_inicial`.
- **`inicial` e `variacao_percentual`:** sempre objetos com as chaves `populacao`, `quantidade` e `densidade`; os
  valores são `null` quando não há competência inicial.
- **`avaliavel`:** `{densidade, distancia, variacao}`.
  - `densidade` diz se há valores na competência.
  - `distancia` e `variacao` são `null` quando não foram pedidas (sem referência, sem competência inicial).
  - `variacao` só é `true` com as três variações avaliáveis.
- **`motivos`:** lista de textos em português, cada um terminado pelo código entre parênteses (por exemplo,
  "Distância não avaliável em junho de 2024: coordenadas ausentes (SEM_INFORMACAO_ESPACIAL)"). Inclui o agregado
  parcial, que é avaliável com limitação.
- **`dominios`:** chaves `densidade`, `quantidade`, `populacao`, `distancia_km`, `variacao_densidade`,
  `variacao_quantidade` e `variacao_populacao`.
  - Os domínios dos indicadores incluem os valores da competência inicial, para as marcas de origem e destino caberem
    no eixo.
  - `distancia_km` inclui `distancia_km_max` dos conjuntos.
- **`origem` da referência (CAP-REF-01):** sem `criterio`, "Escolhida por você (lista explícita); …".
  - Com `criterio`, o motor recalcula a ordenação (CAP-SUB-02) na competência, no universo informado ou, sem ele, entre os
    municípios base. Exemplo: "Escolhida pelo critério densidade (maior para menor), 1ª posição entre os municípios base
    (62 municípios) em junho de 2024".
  - A referência não tem caráter normativo.
- **`limitacoes`:** `SOMA_COM_POSSIVEL_DUPLA_CONTAGEM` (com conjuntos), `AGREGADO_PARCIAL`,
  `DISTANCIA_GEODESICA_DIRETA` (com alguma distância calculada) e `UNIDADES_NAO_AVALIAVEIS` (algum item com valor não
  avaliável).
- **`notas`:** a fórmula da densidade e a unidade de contagem; a cobertura dos municípios base em cada competência; as
  premissas do perfil oficial (agregação, coordenadas, comparabilidade temporal); o texto TPL-11 da distância; o
  referencial e a competência das coordenadas; a camada complementar; a regra da variação; a coluna `uf` divergente do
  código IBGE, quando ocorre.

### Rota 2: `POST /api/painel/referencias`

`options`: `{competencia, categoria, universo: {"municipios": {...}}, criterio: {atributo, ordem}}`. `universo` tem a
forma de `base`. `atributo` é `densidade`, `quantidade` ou `populacao`; `ordem` é `desc` ou `asc`, sempre escolhida pelo
usuário (CAP-SUB-02).

Resposta 200: `{criterio, competencia, categoria, candidatos: [{id, rotulo, uf, valor, posicao}], nao_avaliaveis:
[{id, rotulo, uf, motivos}]}`.

- A ordem e as posições são as de `combined_criteria.ranking_of` (CAP-SUB-02): valores exatos, empates na mesma posição
  (1, 2, 2, 4) e, dentro do empate, ordem alfabética só para exibir.
- Os não avaliáveis (sem registro na competência) ficam em `nao_avaliaveis`, sem posição.
- "Usar o primeiro" é a seleção por posição (CAP-SUB-03), feita na tela: com empate na 1ª posição, a tela pede a escolha
  entre os empatados. A rota só lista; não inicia análise nem escolhe a referência.

### Erros

Respostas 422 com mensagem em português para:

- base que não é a oficial;
- mapeamento fora do perfil oficial;
- versão divergente;
- competência ou categoria inexistente;
- competência inicial que não é anterior;
- ids inexistentes ou repetidos;
- conjunto sem membros ou com um só;
- referência sem membros;
- critério com atributo ou ordem inválidos;
- chave desconhecida em `options`;
- pedido sem municípios base e sem conjuntos.

Erros de dados da preparação (população ausente ou conflitante, linhas repetidas) recusam o pedido com o mesmo texto da
análise de densidade. A sessão expirada responde 410, como em `/api/analyze`.

### Extensões compatíveis em relação ao contrato de 21/10/2026

- `referencia.criterio.universo` (opcional): o universo da ordenação, para a origem citar a posição exata vista pelo
  usuário. Sem ele, a posição é calculada entre os municípios base.
- `dominios.variacao_quantidade` e `dominios.variacao_populacao`, além de `variacao_densidade`.
- Rota 2: `categoria` e a lista `nao_avaliaveis` (o contrato pede a lista separada sem nomeá-la).
- `referencia` (booleano) em todos os itens: `true` só nos membros da referência e no conjunto igual a ela.

### Desempenho

- Uma preparação por competência pedida (cerca de 5.570 linhas na base real), sobre as linhas da competência e da
  categoria.
- Distâncias vetorizadas (`nearest_exact`), sem uma função Python por par.
- Índice municipal, perfil e catálogo territorial reaproveitados pela memória da versão: `municipal_index` e
  `request_memo.per_source`, nas condições de U8 em `Docs/OTIMIZACAO_LATENCIA.md`, só sobre a cópia íntegra marcada.
- A resposta já sai em tipos JSON nativos e é serializada direto, sem a conversão genérica do FastAPI.
- A latência com todos os municípios não foi medida nesta entrega; ver os próximos passos.

### Sessão e próximos passos

- **Sessão:** o resultado do painel ainda não entra na sessão da conversa (`record_result`). Hoje a sessão guarda
  resultados no formato de `/api/analyze` e captura o contexto da seleção da conversa, que o painel substituiria. Fica
  registrado como próximo passo, com o desenho de um contexto próprio do painel.
- **Medição de latência:** medir com a base real e todos os municípios (`backend/tests/bench_latency.py`, a estender
  para as rotas do painel).
- **Arquivos importados com coordenadas:** fora desta entrega.
