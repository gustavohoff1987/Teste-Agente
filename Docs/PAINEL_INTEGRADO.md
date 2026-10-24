# Painel integrado de bolhas

Decisões do responsável pelo produto de 21/10/2026: gráfico de bolhas autorizado, num painel próprio ao qual o usuário
acrescenta municípios. A população aparece sempre no tamanho da bolha. Os eixos dependem das análises escolhidas:
densidade ou quantidade e, com a referência, a distância até ela. Conjuntos de municípios agregados viram uma bolha, e a
variação percentual entre duas competências se integra ao desenho. A SPEC admite o gráfico de bolhas pelo
**Adendo BOL-20261021** (fim de `IMPLEMENTATION_SPEC.md`), que dá a redação vigente de RQ-REP-10 e o nome vigente de
CAP-REP-02. O corpo v1.2.4 continua literal, porque o catálogo CFG-DOC o confere pelo SHA-256 e pelos localizadores do
Anexo A.

Decisões de 22/10/2026 (página única de análise): uma análise integrada, sem as telas clássicas, sobre a base do Brasil
(estados ou municípios) ou sobre planilhas enviadas, com tendência, grupos por posição, faixas, condições, ordenação,
comparação e rotatividade. O complemento de 22/10/2026 do Adendo BOL-20261021 admite a cor da bolha pela família da
classe de tendência de CAP-TEN-01 e a rotatividade em barras de 100%.

Este documento descreve o motor e as rotas. A tela tem documento próprio.

## Dois formatos de pedido

`POST /api/painel` aceita dois formatos, decididos pela presença de `nivel` em `options`:

- **Sem `nivel`: contrato de 21/10/2026** (seção "Motor e rotas"). Só a base Brasil oficial, com as chaves e a resposta
  de então, sem mudança. Uma chave da página única nesse formato é desconhecida (422 "Parâmetro não reconhecido no
  painel: … As chaves da página única valem com nivel …"), e uma planilha enviada é recusada com o texto de sempre.
- **Com `nivel`: página única, 22/10/2026** (seção "Página única"). Base Brasil (municípios ou estados) ou planilha
  enviada, as análises novas e os campos fixos de topo (`nivel`, `indicador`, `rotulos`, `disponibilidade`, `contexto`,
  `sessao`). A tela da página única envia sempre `nivel`.

`POST /api/painel/referencias` e `POST /api/painel/mapa` (23/10/2026) têm um formato só, com a base Brasil ou uma
planilha enviada.

## Motor e rotas

### Visão geral

- **Rotas:** `POST /api/painel`, `POST /api/painel/referencias` e `POST /api/painel/mapa` (`backend/main.py`). O motor
  fica em `backend/painel.py`; a frase-resumo da página única, em `backend/resumo_painel.py`.
- **Base (sem `nivel`):** só a base Brasil oficial (fonte municipal), numa competência e numa categoria. Arquivo importado
  recebe 422: "O painel integrado usa só a base Brasil oficial (fonte municipal) nesta versão; …". Com `nivel`, ver
  "Planilhas enviadas".
- **Números:** todo número vem do motor, pelas mesmas funções das análises, sem fórmula paralela. A tela só posiciona,
  filtra e desenha (RQ-REP-09). A régua "abaixo de / acima de" é filtro visual sobre os valores devolvidos e não inicia
  análise (RQ-REP-06).
- **Privacidade:** nenhum nome, valor, campo ou arquivo vai ao provedor de IA. As rotas não chamam o Gemini, e nem a
  frase-resumo nem as coordenadas do mapa entram em contexto enviado a ele.

### Formulário (as três rotas)

Multipart, no padrão de `/api/analyze`:

| Campo | Uso |
|---|---|
| `dataset` | `brazil` para a base do Brasil. Vazio com `file` (planilha enviada, só com `nivel` na rota 1). |
| `file` | Planilha enviada (CSV, XLSX ou XLS, até 30 MB), lida como em `/api/analyze`; nada é guardado. |
| `sheet` | Aba da planilha, quando o arquivo tem mais de uma (sem ela, 422 "Escolha a planilha (aba) do arquivo …"). |
| `scope` | `municipal` (ou `auto`, que no painel é municipal). Ignorado com planilha. |
| `dataset_version` | Versão da inspeção. Integridade conferida pelo manifesto a cada pedido; versão divergente → 422 "A base Brasil foi atualizada. …". |
| `mapping` | Mapeamento da inspeção. Na base Brasil, o do perfil oficial: código IBGE, município, período, categoria, quantidade e população e, com a referência, latitude e longitude; vazio vale o perfil oficial; papel sem coluna é ignorado. Nas planilhas, ver "Planilhas enviadas". |
| `options` | JSON descrito em cada rota. Chave desconhecida → 422 "Parâmetro não reconhecido no painel: …". |
| `geo_version` | Opcional, na rota 1 com referência e no mapa, só na base Brasil: como em `/api/analyze`, recusa o pedido se a camada complementar de coordenadas mudou depois da preparação. |
| `context_revision` | Revisão do contexto da sessão (a mesma da conversa). Na página única, decide se o resultado é gravado na sessão; nas rotas 2 e 3, aceita e não usada (nada é gravado). |
| `X-ADT-Session` | Cabeçalho opcional, só na rota 1: registra o evento de sessão `CONFIRMACAO`, como `/api/analyze`; na página única, grava também o resultado (seção "Sessão"). |

### Rota 1: `POST /api/painel` (contrato de 21/10/2026)

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
- **`distancia_km` (CAP-ESP-01 e CAP-ESP-02):** distância geodésica no elipsoide do referencial: GRS80 no SIRGAS 2000
  (premissa governada da base oficial) e, numa planilha, também WGS 84 no WGS 84 (desde 22/10/2026, Adendo REF-20261022), por `nearest_reference.territory_coordinates` e `nearest_exact`, como em `compute_nearest`, com as
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

`options`: `{competencia, categoria, universo: {"municipios": {...}}, criterio: {atributo, ordem}}` e, com planilha,
`premissas` e `rotulos` (seção "Planilhas enviadas"). `universo` tem a forma de `base`. `atributo` é `densidade`,
`quantidade` ou `populacao`; `ordem` é `desc` ou `asc`, sempre escolhida pelo usuário (CAP-SUB-02).

Resposta 200: `{criterio, competencia, categoria, candidatos: [{id, rotulo, uf, valor, posicao}], nao_avaliaveis:
[{id, rotulo, uf, motivos}]}`. Nas planilhas, `uf` é `null`.

- A ordem e as posições são as de `combined_criteria.ranking_of` (CAP-SUB-02): valores exatos, empates na mesma posição
  (1, 2, 2, 4) e, dentro do empate, ordem alfabética só para exibir.
- Os não avaliáveis (sem registro na competência) ficam em `nao_avaliaveis`, sem posição.
- "Usar o primeiro" é a seleção por posição (CAP-SUB-03), feita na tela: com empate na 1ª posição, a tela pede a escolha
  entre os empatados. A rota só lista; não inicia análise nem escolhe a referência.

### Rota 3: `POST /api/painel/mapa` (23/10/2026)

As coordenadas autorizadas do mapa da página única: as mesmas que a análise espacial já usa para medir as distâncias
(`nearest_reference.territory_coordinates`, pela memória da versão), sem cálculo novo. A tela desenha o mapa com elas;
o contrato com a tela é `DadosDoMapa` (`frontend/src/mapaContrato.ts`).

`options`: `{competencia, categoria}` e, com planilha, `premissas` e `rotulos` (as mesmas regras da rota 1; chave
desconhecida → 422 "Parâmetro não reconhecido no painel: …"). O pedido passa pelo mesmo portão do gráfico
(`painel.context`).

Resposta 200: `{"competencia", "referencial", "pontos": [{id, lat, lon}], "sem_coordenada": [{id, rotulo, motivo}]}`.

- **Unidades:** todas as do catálogo territorial da fonte, na ordem do código, cada uma em `pontos` ou em
  `sem_coordenada`. Os ids são os dos itens de `POST /api/painel` (`code:<código>` ou `name:<nome>`). Estados não têm
  ponto: o mapa é das unidades.
- **Base do Brasil:** a sede municipal do perfil oficial, em SIRGAS 2000 (`referencial: "SIRGAS2000"`), com a camada
  complementar governada nos municípios autorizados (`dados/brasil/complemento_coordenadas.json`), como na análise
  espacial. Coordenadas da competência pedida; as de outras competências não são tratadas como equivalentes.
- **Planilha:** as colunas de latitude e longitude no referencial confirmado em `premissas.crs` (`SIRGAS2000` ou
  `WGS84`, sem converter um no outro). Sem `crs`, a mesma pendência da análise espacial (`pendencia.chave: "crs"`);
  referencial fora dos aceitos → 422 "Referencial geodésico informado não suportado …"; separador decimal não
  verificável → pendência `number_format`. Sem colunas de latitude e longitude associadas → 422 "A planilha não tem
  colunas de latitude e longitude associadas: o mapa precisa delas."
- **`pontos`:** latitude e longitude em graus decimais, como lidas (e complementadas) pelo motor.
- **`sem_coordenada`:** a unidade sem coordenada válida na competência, com o rótulo e o motivo com o código, como nas
  distâncias: "Sem coordenada válida em junho de 2024: coordenadas ausentes (SEM_INFORMACAO_ESPACIAL)", "… coordenada
  não numérica ou fora do intervalo (COORDENADA_INVALIDA)", "… coordenadas divergentes no período
  (COORDENADA_INVALIDA)" ou, sem registro na competência, "… sem registro no período (SEM_REGISTRO_OBSERVADO)". Fica
  fora do mapa e entra em "Não avaliáveis".
- **Só leitura:** nada é registrado na sessão, nada vai ao provedor de IA, nenhuma distância é medida.

Com a base versionada de 22/10/2026, em junho de 2024 os 5.570 municípios têm ponto (os seis da camada complementar,
como ANANAS, pela sede oficial do IBGE); em janeiro de 2015, três municípios sem registro na competência ficam em
`sem_coordenada`.

### Erros

Respostas 422 com mensagem em português para:

- base que não é a oficial (sem `nivel`);
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
análise de densidade. A sessão expirada responde 410, como em `/api/analyze`. Escolha pendente (por exemplo, o referencial
que a versão da base não estabelece) traz também `pendencia` no corpo do 422 (seção "Pendências").

### Extensões compatíveis em relação ao contrato de 21/10/2026

- `referencia.criterio.universo` (opcional): o universo da ordenação, para a origem citar a posição exata vista pelo
  usuário. Sem ele, a posição é calculada entre os municípios base.
- `dominios.variacao_quantidade` e `dominios.variacao_populacao`, além de `variacao_densidade`.
- Rota 2: `categoria` e a lista `nao_avaliaveis` (o contrato pede a lista separada sem nomeá-la).
- `referencia` (booleano) em todos os itens: `true` só nos membros da referência e no conjunto igual a ela.

## Página única (com `nivel`, 22/10/2026)

O pedido com `nivel` vale o que está acima e mais o que segue. As análises novas usam as mesmas funções do motor que
`/api/analyze` usa para cada capacidade; nenhuma fórmula é nova:

| Análise | Capacidade | Função do motor |
|---|---|---|
| Estados | UF-CONTAGEM-ESTADUAL-1 e UF-POP-MUNICIPIOS-1 | `territorial_levels.state_part`, como a abrangência por estados |
| Tendência | CAP-TEN-01 (DA-15) | `trend.classify_frame` e `trend.summarize`, como a evolução temporal |
| Grupos por posição | CAP-DIS-02 | `main._compute(..., "distribution")` e `main.distribution_cuts` (Hyndman–Fan tipo 7) |
| Faixas e faixas de distância | CAP-DIS-03 e CAP-ESP-03 | `combined_criteria.band_edges` e `bands_of` |
| Condições | CAP-SUB-01 | `combined_criteria.parse_tree` e `evaluate` (três estados, combinação E) |
| Ordenação e N primeiros | CAP-SUB-02 e CAP-SUB-03 | `combined_criteria.ranking_of` e `select_top` |
| Comparação | CAP-CMP-01 | `main._compute(..., "comparisons")` |
| Membro mais próximo | CAP-ESP-02 | `nearest_reference.nearest_exact`, com os empates exatos |
| Rotatividade | CAP-ROT-01 | `main._compute(..., "rotation")` |
| Linha de contexto do Brasil | D5 (19/10/2026) | `territorial_levels.national_reference` |

### `options` da página única

Chaves estritas: além das do contrato de 21/10, só estas (desconhecida → 422 "Parâmetro não reconhecido no painel: …").

| Chave | Regra |
|---|---|
| `nivel` | Obrigatória: `"municipios"` ou `"estados"`. `estados` só na base do Brasil (planilha → 422 "O nível estados existe só na base do Brasil, …"). |
| `indicador` | Obrigatória: `"densidade"` ou `"quantidade"`, o indicador do gráfico. Vale para `grupos`, `grupos_mapa`, `faixas`, `tendencia`, `comparar` e para `ordenar` com `variacao`. Densidade sem população na planilha → 422 "A planilha não tem coluna de população associada: …". |
| `base` | Como no contrato de 21/10, só no nível municípios. Na planilha, `estados` traz os valores do grupo (coluna `grupo_territorial`) e `ids` os identificadores das unidades. |
| `conjuntos`, `referencia` | Como no contrato de 21/10, só no nível municípios. |
| `competencia_inicial` | Como no contrato de 21/10 (visão Mudança, CAP-TMP-01), nos dois níveis. |
| `tendencia` | `{"competencias": [...]}`: a janela, de 2 a 80 competências distintas e existentes, em qualquer ordem (o motor ordena). Com menos de quatro, o motor devolve o bloqueio (`BLQ-MET`, série insuficiente). |
| `grupos` | `{"tipo": "quartis" \| "quintis" \| "decis"}`. |
| `grupos_mapa` | `{"tipo": "quartis" \| "quintis" \| "decis"}`: os grupos por posição que pintam o mapa (23/10/2026; seção "Grupos do mapa"). A mesma validação de `grupos` (tipo inválido → 422 "Grupos por posição inválidos (grupos_mapa): use {"tipo": "quartis", "quintis" ou "decis"}."), nos dois níveis e com qualquer outra chave; pode vir junto com `grupos`, e cada um é calculado à parte. |
| `faixas` | Lista de 2 a 21 limites crescentes e distintos, não negativos, do `indicador` (números ou textos com vírgula ou ponto decimal, como `[0, 1, 2, 5]` ou `["0", "1,5"]`). Intervalos [a, b) e o último fechado. |
| `faixas_distancia` | A mesma forma, em km. Exige `referencia`. |
| `condicoes` | Lista de 1 a 12 `{"atributo", "operador", "valor"}` combinados por E. `atributo`: `densidade`, `quantidade`, `populacao` ou `distancia_km` (este exige `referencia`). `operador`: `<`, `<=`, `>`, `>=`, `=` ou `!=`. `valor`: número não negativo ou texto com vírgula ou ponto decimal; densidade por 1.000 habitantes, distância em km. |
| `ordenar` | `{"atributo", "ordem", "primeiros"}`. `atributo`: `densidade`, `quantidade`, `populacao`, `distancia_km` (exige `referencia`) ou `variacao` (a variação percentual do `indicador`, exige `competencia_inicial`). `ordem`: `desc` ou `asc`. `primeiros` (opcional): inteiro de 1 a 10.000. |
| `comparar` | Lista de 2 ou 3 ids distintos de itens da resposta (municípios, unidades, estados ou conjuntos), no `indicador`. Id que não está na resposta → 422 "Itens da comparação fora do gráfico: …". Itens relacionados (um conjunto e um membro dele, ou conjuntos com membros em comum) → 422 "Itens relacionados não são comparados: …". |
| `rotatividade` | `{"inicial", "final"}`: duas competências existentes, a final depois da inicial. Só na planilha com identificador individual; na base do Brasil → 422 com o motivo da indisponibilidade. |
| `premissas` | Só nas planilhas (seção "Planilhas enviadas"); na base do Brasil → 422 "Na base do Brasil, as premissas vêm do perfil oficial: …". |
| `rotulos` | Só nas planilhas; na base do Brasil → 422 "Na base do Brasil, os rótulos são fixos …". |

No nível `estados`, `base`, `conjuntos`, `referencia`, `faixas_distancia`, `rotatividade`, a condição e a ordenação por
`distancia_km` são recusados com o motivo (estados não têm um ponto único; a base vale só para municípios).

### Universo das análises

`grupos`, `grupos_mapa`, `faixas`, `faixas_distancia`, `condicoes` e `ordenar`, e as contagens de `tendencia`, valem no
**universo**: os municípios base (ou as unidades base da planilha) ou, no nível estados, os estados. Conjuntos e membros
da referência fora da base não entram no universo: os campos por item deles vêm `null`. A `tendencia` por item é
calculada para todos os itens, inclusive conjuntos (CAP-AGR-01 por competência; membros com registro diferentes na
janela → `INCOMPARABILIDADE`, pela entrada, como pede F-05b). A comparação aceita qualquer item da resposta.

### Resposta 200 da página única

Topo: as chaves do contrato de 21/10 e, sempre:

| Campo | Conteúdo |
|---|---|
| `nivel`, `indicador` | Os do pedido. |
| `rotulos` | `{"unidade": {singular, plural, genero}, "grupo": {singular, plural, genero}}`. Base do Brasil: município/municípios e estado/estados. Planilha: os recebidos ou, sem eles, unidade/unidades e grupo/grupos. `genero` é `"m"` ou `"f"`. |
| `disponibilidade` | O que a fonte permite, com o motivo: `{"distribuicao", "densidade", "espacial", "tendencia", "rotatividade", "estados", "grupos"}`, cada um `{"disponivel": bool, "motivo": texto, "pendencia": null \| {chave, opcoes, texto}}`. `motivo` é vazio quando nada limita; pode vir preenchido com `disponivel: true` (por exemplo, menos de quatro competências: só a mudança). `grupos` é a bolha do nível de cima (estados no Brasil; nas planilhas, sempre indisponível). |
| `contexto` | `{"brasil": {rotulo, competencia, densidade, quantidade, populacao, competencia_populacao, avaliabilidade, motivo, nota, regra_populacao}}` na base do Brasil: a taxa nacional da competência (`territorial_levels.national_reference`, a mesma de `metadata.referencia_nacional` da análise de densidade), sem classificar nada. Indisponível: os valores `null`, `avaliabilidade` `"NAO_AVALIAVEL"` e o `motivo`. Nas planilhas, `{"brasil": null}`. |
| `sessao` | `{"registrado": bool, "result_id": texto \| null, "motivo": texto \| null}` (seção "Sessão"). |
| `resumo` | A frase-resumo do motor (23/10/2026; seção "Frase-resumo"). Omitido só se a composição falhar. |
| `versao_base` | Base do Brasil: a versão verificada; planilha: o SHA-256 do arquivo enviado. |
| `dominios.tendencia` | Com `tendencia`: `[mínimo, máximo]` das observações devolvidas (ou `null`). |

Quando pedidos:

| Campo | Conteúdo |
|---|---|
| `tendencia` | O resumo do motor (`trend.summarize`): `capacidade`, `versao_metodo`, `desfecho` (`RES-VAL`, `RES-LIM`, `RES-SCL` ou `BLQ-MET`), `bloqueio`, `unidades_total`, `avaliaveis`, `nao_avaliaveis`, `contagens` (por classe), `sem_classificacao_por_motivo`, `nao_avaliaveis_por_motivo`, `familias`, `classes` ([{codigo, rotulo, familia}], a ordem da legenda), `rotulos_familia`, `rotulos_nao_avaliavel`, `rotulos_motivo`; e `indicador`, `unidade_valor`, `unidade_tempo`, `janela` ({periodos, inicio, fim, intervalos, intervalo_constante, serie_anual, serie_anual_disponivel, competencias_serie_anual}) e `universo`. As contagens são do universo. |
| `grupos` | `{tipo, k, atributo, cortes, rotulos, contagens, universo, classificados, nao_avaliaveis}`. `cortes` são os k − 1 pontos de corte do motor; `rotulos` e `contagens` vão do 1º ao k-ésimo grupo. |
| `grupos_mapa` | A mesma estrutura de `grupos`, com o mesmo cálculo (seção "Grupos do mapa"); `null` quando menos de duas unidades do universo têm valor do `indicador`. |
| `faixas`, `faixas_distancia` | `{atributo, capacidade, limites, convencao, rotulos, contagens, fora, nao_avaliaveis, universo}`. `atributo` é o `indicador` ou `distancia_km`; `capacidade`, `CAP-DIS-03` ou `CAP-ESP-03`; `limites` em texto decimal com ponto, sem arredondar (`["0", "100.5", "1000"]`); `rotulos` com vírgula, como na análise ("0 a <100,5", "100,5 a 1000"); `fora` e `nao_avaliaveis` são contagens. |
| `condicoes` | `{contagens: {ATENDE, NAO_ATENDE, NAO_AVALIAVEL}, universo, combinacao: "E", descricao, definicao: [{atributo, operador, valor, texto}]}`. |
| `ordenacao` | `{atributo, ordem, primeiros, universo, ordenados, nao_avaliaveis, selecionados, empates_no_corte, ids_selecionados}`; sem `primeiros`, `selecionados` e `ids_selecionados` são `null`. |
| `comparacao` | `{indicador, itens: [{id, rotulo, tipo, valor, avaliavel, motivos}], maior, menor, diferencas, relacoes, notas}`. Dois itens: `diferencas` = [{a, b, relacao, diferenca}], A e B em ordem de nome, relação A/B (`MAIOR`, `MENOR` ou `IGUALDADE`) e diferença assinada A − B. Três: `relacoes` = [{id, valor, proximo_valor_maior, mesmo_valor}] e `diferencas` vazia (sem diferenças automáticas entre pares, AT-84). `maior` e `menor` são listas de ids (empate: mais de um). Com menos de dois itens com valor, as listas ficam vazias, com a nota. |
| `rotatividade` | `{inicial, final, universo, avaliaveis, nao_avaliaveis}`. |

Itens: os campos do contrato de 21/10 e, sempre, `grupo_territorial` (base do Brasil: o prefixo IBGE do estado, como
`"13"`; planilha: o valor da coluna `grupo_territorial` ou `null`; estados e conjuntos: `null`). No nível estados, o item
é `tipo: "estado"`, `id: "uf:13"`, `rotulo: "Amazonas (AM)"`, `uf: "AM"`, sem `membros`, com `distancia_km` nulo. Nas
planilhas, o item da unidade continua `tipo: "municipio"` (o código do nível; o nome vem de `rotulos`), com `uf: null`.

Por item, quando pedidos (o campo vem em todos os itens; `null` fora do universo ou quando não se aplica):

| Campo | Forma |
|---|---|
| `referencia_mais_proxima` | Com `referencia`: `{id, rotulo, empate}`, o membro da referência à menor distância; `empate` lista todos os membros à mesma menor distância (vazia sem empate); `id` é o primeiro deles na ordem da referência. `null` sem distância avaliável e nos conjuntos. |
| `tendencia` | `{classe, familia, rotulo, motivo, motivo_texto, avaliavel, observacoes, velocidades}`. `classe`: CategoriaTendencia (`CRESCIMENTO`, `CRESCIMENTO_ACELERADO`, `CRESCIMENTO_DESACELERADO`, `DECLINIO`, `DECLINIO_ACELERADO`, `DECLINIO_DESACELERADO`, `SEM_CLASSIFICACAO`) ou `null`; `familia`: `CRESCIMENTO`, `DECLINIO`, `NENHUMA` ou `null` (não avaliável); `rotulo`: o rótulo DA-15 ("Desaceleração do crescimento", "Não avaliável: série insuficiente"); `motivo`: `SERIE_ESTAVEL`, `MUDANCA_DE_DIRECAO`, `SERIE_INSUFICIENTE`, `INCOMPARABILIDADE` ou `null`; `motivo_texto`: o texto do motivo ("3 de 4 observações necessárias"); `observacoes`: [{competencia, valor}] do indicador nas competências com valor (também nos não avaliáveis, para a visão Séries); `velocidades`: as velocidades do motor (variação do indicador por `unidade_tempo`, o mês nas competências AAAAMM) entre observações consecutivas, na ordem de `observacoes`; vazia quando não avaliável. |
| `grupo` | `{indice, rotulo}` (`indice` de 1 a k, "2º quartil"). |
| `grupo_mapa` | Com `grupos_mapa`: a mesma forma de `grupo` (`{indice, rotulo}`); `null` fora do universo, sem valor do `indicador` ou com `grupos_mapa` nulo. |
| `faixa`, `faixa_distancia` | `{indice, rotulo}` (`indice` a partir de 1), `"fora"` (fora de todas as faixas) ou `null` (não avaliável). |
| `condicoes` | `{situacao, por_condicao}`. `situacao`: `ATENDE`, `NAO_ATENDE` ou `NAO_AVALIAVEL` (nunca tratado como não atende). `por_condicao`: [{estado, valor, motivos}], na ordem de `condicoes.definicao`; `motivos` em códigos (`SEM_REGISTRO_OBSERVADO`, `SEM_INFORMACAO_ESPACIAL`, `DEPENDENCIA_NAO_AVALIAVEL`…). |
| `ordem` | `{posicao, selecionado}`: posição com empates na mesma posição (1, 1, 3), `null` quando não avaliável; `selecionado` é `null` sem `primeiros`. Com empate no corte, todos os empatados entram (`empates_no_corte`, `EMPATE_NO_CORTE`). |
| `rotatividade` | Unidades: `{inicial, final, coorte_inicial, permanencia, saida, permanencia_percentual, saida_percentual, avaliavel, motivo}`; unidade sem registro numa das competências fica não avaliável, com o motivo, nunca 0% ou 100%. Conjuntos: `null`. |

`notas` e `limitacoes` ganham as notas de cada análise pedida (método da tendência, pontos de corte, faixas, condições,
ordenação, comparação, coorte, estados e a linha de contexto) e `EMPATE_NO_CORTE`.

Exemplo de pedido (base do Brasil, municípios do Amazonas, Manaus como referência, tendência nos junhos de 2021 a 2024):

```json
{"nivel": "municipios", "indicador": "densidade", "competencia": "202406", "base": {"municipios": {"estados": ["13"]}},
 "referencia": {"membros": ["code:130260"]}, "tendencia": {"competencias": ["202106", "202206", "202306", "202406"]},
 "grupos": {"tipo": "quartis"}, "condicoes": [{"atributo": "densidade", "operador": "<", "valor": 1},
 {"atributo": "distancia_km", "operador": ">", "valor": 150}], "ordenar": {"atributo": "densidade", "ordem": "desc",
 "primeiros": 10}, "comparar": ["code:130260", "code:130420"]}
```

Um item da resposta, com a base versionada de 22/10/2026 (Tefé; valores em precisão integral, como saem do motor):

```json
{"id": "code:130420", "tipo": "municipio", "rotulo": "TEFE (AM)", "uf": "AM", "populacao": 79278, "quantidade": 69,
 "densidade": 0.8703549534549307, "distancia_km": 521.2473967291248,
 "inicial": {"populacao": null, "quantidade": null, "densidade": null},
 "variacao_percentual": {"populacao": null, "quantidade": null, "densidade": null},
 "avaliavel": {"densidade": true, "distancia": true, "variacao": null}, "motivos": [], "referencia": false,
 "grupo_territorial": "13",
 "referencia_mais_proxima": {"id": "code:130260", "rotulo": "MANAUS (AM)", "empate": []},
 "tendencia": {"classe": "SEM_CLASSIFICACAO", "familia": "NENHUMA", "rotulo": "Sem classificação",
   "motivo": "MUDANCA_DE_DIRECAO", "motivo_texto": "Mudança de direção", "avaliavel": true,
   "observacoes": [{"competencia": "202106", "valor": 0.9451476793248945},
                   {"competencia": "202206", "valor": 0.9620253164556962},
                   {"competencia": "202306", "valor": 0.9113924050632911},
                   {"competencia": "202406", "valor": 0.8703549534549307}],
   "velocidades": [0.0014064697609001407, -0.004219409282700422, -0.0034197876340300326]},
 "grupo": {"indice": 3, "rotulo": "3º quartil"},
 "condicoes": {"situacao": "ATENDE", "por_condicao": [
   {"estado": "ATENDE", "valor": 0.8703549534549307, "motivos": []},
   {"estado": "ATENDE", "valor": 521.2473967291248, "motivos": []}]},
 "ordem": {"posicao": 28, "selecionado": false}}
```

E os blocos do topo do mesmo pedido (trechos):

```json
{"grupos": {"tipo": "quartis", "k": 4, "atributo": "densidade",
            "cortes": [0.6706122929221101, 0.8547902785270952, 1.0599827223506684],
            "rotulos": ["1º quartil", "2º quartil", "3º quartil", "4º quartil"], "contagens": [16, 15, 15, 16],
            "universo": 62, "classificados": 62, "nao_avaliaveis": 0},
 "condicoes": {"contagens": {"ATENDE": 37, "NAO_ATENDE": 25, "NAO_AVALIAVEL": 0}, "universo": 62, "combinacao": "E",
               "descricao": "(densidade < 1 por 1.000 habitantes E distância à referência mais próxima > 150 km)",
               "definicao": [{"atributo": "densidade", "operador": "<", "valor": 1,
                              "texto": "densidade < 1 por 1.000 habitantes"},
                             {"atributo": "distancia_km", "operador": ">", "valor": 150,
                              "texto": "distância à referência mais próxima > 150 km"}]},
 "ordenacao": {"atributo": "densidade", "ordem": "desc", "primeiros": 10, "universo": 62, "ordenados": 62,
               "nao_avaliaveis": 0, "selecionados": 10, "empates_no_corte": false,
               "ids_selecionados": ["code:130353", "code:130260", "…"]},
 "comparacao": {"indicador": "densidade",
                "itens": [{"id": "code:130260", "rotulo": "MANAUS (AM)", "tipo": "municipio",
                           "valor": 2.074847150002237, "avaliavel": true, "motivos": []},
                          {"id": "code:130420", "rotulo": "TEFE (AM)", "tipo": "municipio",
                           "valor": 0.8703549534549307, "avaliavel": true, "motivos": []}],
                "maior": ["code:130260"], "menor": ["code:130420"],
                "diferencas": [{"a": "code:130260", "b": "code:130420", "relacao": "MAIOR",
                                "diferenca": 1.204492196547306}],
                "relacoes": [], "notas": ["Entre dois objetos: A e B em ordem de nome, relação A/B e diferença assinada A − B."]},
 "tendencia": {"capacidade": "CAP-TEN-01", "versao_metodo": "CAP-TEN-01/DA-15/1", "desfecho": "RES-VAL", "bloqueio": null,
               "unidades_total": 62, "avaliaveis": 62, "nao_avaliaveis": 0,
               "contagens": {"CRESCIMENTO": 17, "CRESCIMENTO_ACELERADO": 4, "CRESCIMENTO_DESACELERADO": 1, "DECLINIO": 0,
                             "DECLINIO_ACELERADO": 2, "DECLINIO_DESACELERADO": 0, "SEM_CLASSIFICACAO": 38},
               "familias": {"CRESCIMENTO": 22, "DECLINIO": 2, "NENHUMA": 38}, "indicador": "densidade",
               "unidade_valor": "por 1.000 habitantes", "unidade_tempo": "mês",
               "janela": {"periodos": ["202106", "202206", "202306", "202406"], "inicio": "202106", "fim": "202406",
                          "intervalos": [12], "intervalo_constante": true, "…": "…"},
               "universo": 62, "…": "…"},
 "contexto": {"brasil": {"rotulo": "Brasil (total nacional)", "competencia": "202406", "densidade": 2.363750757054573,
                         "quantidade": 502495, "populacao": 212583750, "competencia_populacao": "202406",
                         "avaliabilidade": "AVALIAVEL", "motivo": null, "nota": "…", "regra_populacao": "BR-POP-JUNHO-1"}},
 "sessao": {"registrado": false, "result_id": null, "motivo": "Sem sessão: o pedido não trouxe o cabeçalho X-ADT-Session."}}
```

### Grupos do mapa (`grupos_mapa`, 23/10/2026)

O mapa da página única deixa de perguntar "Como pintar o mapa?" e pinta, por padrão, os 5 grupos iguais (quintis) de
CAP-DIS-02. Para a troca de vista entre o gráfico e o mapa continuar sem pedir cálculo (RQ-REP-06), a tela pede os grupos
do mapa junto com a análise, numa chave própria, `grupos_mapa`, sem mudar o que o gráfico, a frase-resumo, a tabela e o
CSV mostram.

- **Pedido:** `"grupos_mapa": {"tipo": "quartis" | "quintis" | "decis"}`, validado como `grupos` (tipo inválido → 422
  "Grupos por posição inválidos (grupos_mapa): use {"tipo": "quartis", "quintis" ou "decis"}."). Vale nos dois níveis
  (municípios ou unidades da planilha, e estados), com qualquer outra chave, e pode vir junto com `grupos`: cada um é
  calculado à parte. Sem `nivel` (contrato de 21/10), é chave desconhecida, como as demais da página única.
- **Resposta:** no topo, `grupos_mapa`, com a mesma estrutura de `grupos` (`{tipo, k, atributo, cortes, rotulos,
  contagens, universo, classificados, nao_avaliaveis}`); em cada item, `grupo_mapa`, com a mesma forma de `grupo`
  (`{indice, rotulo}` ou `null`).
- **Cálculo:** o de `grupos`, sem método novo: a mesma função (`painel._groups`, pela distribuição de `main._compute` e os
  cortes de `main.distribution_cuts`, Hyndman–Fan tipo 7), as mesmas regras de empate (valores iguais no mesmo grupo) e de
  não avaliáveis (fora dos grupos) e a mesma memória da versão (`_reaproveitar(ctx, "grupos", …)`): com o mesmo tipo,
  universo e indicador, um vem do outro, sem recalcular, e `grupos_mapa` é igual a `grupos` do mesmo pedido.
- **Com menos de duas unidades com valor do `indicador` no universo:** `grupos_mapa` vem `null`, e `grupo_mapa` também, em
  todos os itens; o pedido não falha. `grupos`, nesse caso, continua recusado (422 "Os grupos por posição (CAP-DIS-02)
  exigem pelo menos dois municípios …"), porque foi pedido pela pessoa; `grupos_mapa` é pedido pela tela em todo pedido.
- **O resto da resposta não muda:** sem `grupos_mapa`, a resposta é a de antes (nem chave nova no topo, nem campo novo nos
  itens, e a mesma `chave_execucao`). Com ele, só se somam `grupos_mapa` e `grupo_mapa`, e a `chave_execucao` muda (o tipo
  pedido entra no pedido normalizado): as notas, as limitações, os domínios, a frase-resumo (`resumo` e as contagens que
  ela copia, `painel.summary_facts`) e a sessão continuam os mesmos. O CSV da tela é montado com todos os campos dos itens
  (`csvDaResposta`): para ele não mudar, a tela precisa deixar `grupo_mapa` de fora quando pedir os grupos do mapa.

Exemplo (Amazonas, junho de 2024, com a base versionada de 22/10/2026):

```json
{"nivel": "municipios", "indicador": "densidade", "competencia": "202406", "base": {"municipios": {"estados": ["13"]}},
 "grupos_mapa": {"tipo": "quintis"}}
```

```json
{"grupos_mapa": {"tipo": "quintis", "k": 5, "atributo": "densidade",
                 "cortes": [0.6535938011172193, 0.7713405825684332, 0.942585407617734, 1.138824760941643],
                 "rotulos": ["1º quintil", "2º quintil", "3º quintil", "4º quintil", "5º quintil"],
                 "contagens": [13, 12, 12, 12, 13], "universo": 62, "classificados": 62, "nao_avaliaveis": 0},
 "itens": [{"id": "code:130420", "rotulo": "TEFE (AM)", "…": "…", "grupo_mapa": {"indice": 3, "rotulo": "3º quintil"}},
           "…"]}
```

### Tendência na janela: a classe segue DA-15 (diagnóstico de 23/10/2026)

A classe de cada item é a de CAP-TEN-01 com os rótulos de DA-15, sem mudança (SPEC, CAP-TEN-01 e AT-53): as velocidades
são a variação do indicador por unidade de tempo (o mês nas competências AAAAMM) entre observações consecutivas, e
**basta uma velocidade positiva e uma negativa na janela** para a série ficar sem classificação por mudança de direção
(`SEM_CLASSIFICACAO`, `MUDANCA_DE_DIRECAO`). Janelas longas reúnem mais oscilações e, por isso, quase não têm classe.
Diagnóstico de 23/10/2026 com a base versionada (somente leitura), na densidade: com as 22 competências (janeiro e junho
de 2014 a 2024), os 62 municípios do Amazonas ficam todos sem classificação por mudança de direção (desfecho `RES-SCL`;
Manaus tem 17 subidas e 4 descidas); com os últimos 4 junhos (2021 a 2024), 17 `CRESCIMENTO`, 4
`CRESCIMENTO_ACELERADO`, 1 `CRESCIMENTO_DESACELERADO`, 2 `DECLINIO_ACELERADO` e 38 `SEM_CLASSIFICACAO`; o Brasil
inteiro, com as 22, 5.563 `SEM_CLASSIFICACAO` e 7 `CRESCIMENTO`; os 27 estados, com as 22, 22 `SEM_CLASSIFICACAO` e 5
`CRESCIMENTO`. Em todos esses casos, quem fica sem classificação fica por mudança de direção. A ausência generalizada de
classe em janelas longas vem da regra, não de falha no cálculo, e o método não muda.
`backend/tests/test_painel_tendencia.py` confere cada desfecho de AT-53 num catálogo sintético e esse diagnóstico com a
base versionada (job `dados-reais`).

Desde 24/10/2026, a tela pede a tendência com os **últimos 4 períodos** do ritmo escolhido no campo Período (anual: 06/2021 a
06/2024; semestral: 01/2023 a 06/2024, na base do Brasil), em `tendencia.competencias`, como qualquer janela: o motor e o
contrato não mudam, e uma janela pedida na conversa continua aceita como veio ([área de análise](PAINEL_INTEGRADO_INTERFACE.md)).

### Planilhas enviadas

Planilhas de qualquer país, com a estrutura da base do Brasil e a nomenclatura própria (distrito, condado, província,
região…). Só no formato com `nivel`, e só no nível municípios.

- **`mapping`:** o de `/api/inspect`, confirmado na tela (painel "Colunas"). Papéis: `territory` e `period` obrigatórios;
  `territory_id`, `category`, `count`, `population`, `latitude`, `longitude` e `identity` (identificador individual, que
  conta pessoas distintas quando não há `count` e permite a rotatividade) quando existem; e o papel próprio do gráfico
  **`grupo_territorial`**, a coluna-mãe opcional (província, estado, região), lida como o nível superior 1 de
  `describe_hierarchy` e `territory_catalog`, como no fluxo clássico: o motor o recebe em `hierarchy_columns`, não como
  papel da análise. Na base do Brasil, `grupo_territorial` é recusado (o grupo é o estado do código IBGE).
  - Ids das unidades: `code:<código>` quando o código está escolhido; senão `name:<nome>` (a identidade de `row_ids`).
  - Em `base.municipios`, `estados` traz os valores do grupo (`"Província Norte"`), e `ids` os ids das unidades. Unidade com
    mais de um valor de grupo na planilha não entra na escolha pelo grupo.
  - Papel desconhecido → 422; coluna inexistente → 422 "A coluna associada não existe nesta base: …".
- **D1, sem afrouxar:** um papel só vale reconhecido por regra conclusiva ou escolhido pela pessoa
  (`premissas.confirmed_roles`, como `confirmed_roles` em `/api/analyze`); coluna só sugerida → pendência `confirmed_roles`.
  O pedido passa pelo mesmo portão de `/api/analyze` (o pré-exame `preflight` da análise de densidade, ou de quantitativos
  sem população), com as mesmas mensagens.
- **`premissas`:** as escolhas da pessoa sobre a planilha, com os nomes das opções de `/api/analyze`: `confirmed_roles`
  (lista de papéis), `count_unit` (`pessoas`, `vinculos`, `postos` ou `outro`), `custom_count_unit`, `crs`,
  `number_format` (`decimal_comma` ou `decimal_point`), `object_declaration` (com coluna de categoria) ou
  `category_constant` (sem ela), `duplicate_policy` (`remove_exact`) e `component_columns`. Chave desconhecida → 422
  "Premissa não reconhecida no gráfico: …". As premissas da análise (`*_confirmed`) continuam aplicadas pelo backend
  (`analysis_premises`), nunca enviadas pela tela.
- **`rotulos`:** `{"unidade": {"singular", "plural", "genero"?}, "grupo": {...} | null}`, textos de até 40 caracteres.
  Sem `genero`, o motor o deduz da primeira palavra só para a concordância dos artigos (feminino em -a, -ade, -ção, -são e
  -gião). Todas as mensagens, notas e motivos que citariam "município" ou "estado" usam esses rótulos, com o gênero de
  cada um ("Distritos base (2024): 2 de 2 com registro", "Províncias inexistentes na planilha …", "A coluna da província
  (grupo_territorial) precisa ser diferente da coluna de distritos e do código."). Desde 23/10/2026, também o motivo da
  distância indisponível no nível de cima segue a estrutura reconhecida: na base do Brasil, "No nível dos estados, a
  distância não se aplica: os estados não têm um ponto único. Abra os municípios de um estado para usar a análise
  espacial."; numa estrutura de distritos e províncias, "No nível das províncias, … Abra os distritos de uma província …".
  Só os textos do nível `estados`, que existe apenas na base do Brasil (com a fonte estadual), citam o nível por esse nome
  ("O nível estados existe só na base do Brasil, …").
- **Sem população:** `disponibilidade.densidade` indisponível, densidade e população `null`; só o indicador `quantidade`.
- **Grupo:** sem um valor próprio de cada grupo, não há bolha de grupo (somar as unidades seria CAP-AGR-01, com possível
  dupla contagem); `disponibilidade.grupos` explica. O nível `estados` é só da base do Brasil.
- **Distância:** exige latitude e longitude e o referencial confirmado em `premissas.crs`: SIRGAS 2000 (`SIRGAS2000`,
  `SIRGAS 2000`…) ou, desde 22/10/2026, WGS 84 (`WGS84`, `WGS 84`…), cada um no seu elipsoide e sem converter um no outro;
  sem `crs`, pendência `crs` (opções `SIRGAS2000` e `WGS84`); com outro referencial, `disponibilidade.espacial` indisponível com o motivo
  e o pedido com `referencia` recusado (422 "Referencial geodésico informado não suportado …"), sem presumir nem
  transformar. O separador decimal é verificado nos dados (vírgula aplicada só com evidência); misto → pendência
  `number_format`.
- **Rotatividade:** só com `identity` (identificador individual); sem ele, `disponibilidade.rotatividade` indisponível.
  Os identificadores nunca voltam na resposta.
- **Contexto do Brasil:** não se aplica (`contexto.brasil` nulo).

Exemplo (`mapping` e `options`):

```json
{"territory": "distrito", "period": "ano", "category": "categoria", "count": "quantidade", "population": "populacao",
 "latitude": "latitude", "longitude": "longitude", "grupo_territorial": "provincia"}
```

```json
{"nivel": "municipios", "indicador": "densidade", "competencia": "2024",
 "rotulos": {"unidade": {"singular": "distrito", "plural": "distritos"},
             "grupo": {"singular": "província", "plural": "províncias"}},
 "premissas": {"count_unit": "pessoas", "crs": "SIRGAS2000"},
 "base": {"municipios": {"estados": ["Província Norte"]}}, "referencia": {"membros": ["name:Alto Rio"]}}
```

### Pendências

Escolha pendente (ChoiceRequired) responde 422 com o texto em `detail` e a pendência estruturada, para a tela oferecer a
escolha e repetir o pedido com `options.premissas`:

```json
{"detail": "Escolha a unidade de contagem: pessoas, vínculos, postos ou outra.",
 "pendencia": {"chave": "count_unit", "opcoes": ["pessoas", "vinculos", "postos", "outro"],
               "texto": "Escolha a unidade de contagem: pessoas, vínculos, postos ou outra."}}
```

| `chave` | Quando | `opcoes` |
|---|---|---|
| `count_unit` | Planilha com quantidade, sem a unidade de contagem. | `pessoas`, `vinculos`, `postos`, `outro` |
| `crs` | Distância numa planilha sem o referencial confirmado. | `SIRGAS2000`, `WGS84` |
| `number_format` | Coordenadas com separador decimal não verificável nos dados. | `decimal_comma`, `decimal_point` |
| `confirmed_roles` | Coluna mapeada só sugerida (sem regra nem escolha). | os papéis a escolher, como `["territory_id"]` |
| `object_declaration` ou `category_constant` | Objeto de análise não reconhecido (com ou sem coluna de categoria). | `[]` (texto livre) |
| `duplicate_policy` | Linhas idênticas em todas as colunas. | `remove_exact` |
| `component_columns` | Várias linhas por território, período e categoria. | `[]` (a tela oferece as colunas da planilha) |
| `null` | Escolha que a tela não resolve (por exemplo, o referencial que a versão da base do Brasil não estabelece, ou a ordem de um critério). | `[]` |

Com mais de uma escolha pendente, `detail` traz todas, e `pendencia`, a primeira. O formato de 21/10 também devolve
`pendencia` nos seus 422 de escolha pendente (o `detail` não muda).

### Frase-resumo (23/10/2026)

Toda resposta da página única (municípios, unidades da planilha ou estados) traz `resumo`, uma frase em palavras do que o
gráfico mostra, composta pelo motor (`backend/resumo_painel.py`) no modelo da frase-resumo de `/api/analyze`
(`result_summary.py`, decisão D7) e da verificação de segmentos da conversa (`result_conversation.verify_segment`):

Municípios do Amazonas em junho de 2024, com a base versionada de 22/10/2026 (trechos):

```json
{"versao": 1,
 "texto": "Em junho de 2024, o gráfico tem 62 municípios. Entre os municípios, a densidade vai de 0,36 a 2,15 por 1.000 habitantes; 0 municípios sem valor. Referência de contexto: taxa nacional de 2,36 por 1.000 habitantes (Brasil, total nacional); não classifica nem colore os itens do gráfico.",
 "partes": [{"texto": "Em "}, {"texto": "junho de 2024", "segmento": 0, "tipo": "PARAMETRO", "caminho": ["competencia"]},
            {"texto": ", o gráfico tem "},
            {"texto": "62", "segmento": 1, "tipo": "VALOR", "caminho": ["resumo", "contagens", "unidades"]}, "…"],
 "segmentos": [{"tipo": "PARAMETRO", "formato": "competencia", "caminho": ["competencia"], "texto": "junho de 2024"},
               {"tipo": "VALOR", "formato": "numero", "caminho": ["resumo", "contagens", "unidades"], "texto": "62"},
               {"tipo": "VALOR", "formato": "numero", "caminho": ["itens", 50, "densidade"], "texto": "0,36", "casas": 2},
               {"tipo": "VALOR", "formato": "numero", "caminho": ["itens", 47, "densidade"], "texto": "2,15", "casas": 2},
               "…"],
 "contagens": {"unidades": 62, "conjuntos": 0, "sem_valor": 0},
 "nota": "Frase composta só com valores, relações e contagens do motor, copiados da resposta e conferidos; nada é calculado na tela."}
```

`formato` diz a regra de apresentação do segmento: `numero` (com `casas` nas medidas contínuas), `texto` (nome ou nota,
como estão na resposta), `competencia` (a competência por extenso, "junho de 2024") ou `relacao` (a relação do motor na
comparação).

- **Só cópias verificadas:** cada número e cada nome da frase é um segmento com o caminho na própria resposta
  (`caminho`), conferido antes de a frase sair (`resumo_painel.verify`); se um segmento não confere, a frase é omitida.
  Nada é calculado no compositor: as contagens de itens (`contagens`) e as unidades de menor e de maior valor vêm do motor
  (`painel.summary_facts`); classes, grupos, faixas e condições são as contagens das análises; as relações da comparação
  são as que o motor devolveu (`comparacao.diferencas`, `maior` e `menor`).
- **Conteúdo, na ordem das análises pedidas:** itens no gráfico e de quanto a quanto vai o indicador entre as unidades,
  com as sem valor (distribuição); grupos por posição e faixas, com as contagens; a variação desde a competência inicial
  (mudança); a referência e de quanto a quanto vai a distância, com as faixas de distância e a nota da linha reta (TPL-11,
  análise espacial); a janela e a contagem por família de classe, ou o bloqueio do método (tendência); quantos atendem,
  não atendem e estão sem dado (condições); os valores comparados e a relação do motor (comparação: entre dois itens, a
  relação A/B e a diferença A − B; entre três, o maior e o menor valor, sem diferenças entre pares); de quanto a quanto
  vai a permanência da coorte inicial, em % (rotatividade); "soma das contagens dos componentes, com possível dupla
  contagem" (conjuntos); a nota da fonte estadual (estados); e, com a densidade na base do Brasil, a taxa nacional como
  referência de contexto. Os grupos que pintam o mapa (`grupos_mapa`) não entram: a frase é a mesma com ou sem eles.
- **Redação (as regras de `tests/test_result_summary.py`):** o texto fixo não usa LEX-DES, LEX-NORM nem LEX-CAU; LEX-CMP
  só nas relações copiadas do motor; LEX-TEN só com a tendência; a taxa do Brasil nunca é "acima" ou "abaixo", nem
  classifica ou colore os itens. Nomes das unidades pelos rótulos da fonte ("distritos", "províncias").
- **Números (RQ-REP-05):** duas casas nas medidas contínuas, contagens inteiras com separador de milhar, mais casas só
  quando o valor arredondaria para zero ou para preservar a relação entre os valores comparados na mesma frase (de
  quanto a quanto, os itens da comparação); a escala e a unidade junto da densidade ("por 1.000 habitantes"), "km" na
  distância e "%" na variação e na permanência.
- **Falha e privacidade:** uma falha ao compor nunca derruba a resposta (registrada no log, o campo é omitido). A frase
  vai para a tela e para a sessão com o resultado; não entra em contexto nenhum enviado ao provedor de IA.

### Sessão

Com o cabeçalho `X-ADT-Session`, a página única grava o resultado do gráfico na sessão para o Histórico e para a
conversa (`conversation_session.record_panel`), com um contexto próprio (`origem: "painel"`), sem chamar
`sessions.capture`: o contexto da conversa não é substituído.

- `sessao.result_id` lê o resultado em `GET /api/session/result/{result_id}`: a resposta inteira, com `result_id` e
  `metadata` (`operation: "painel"`, `validity`, `execution_key`, `method_version`, `created_at`). A conversa reconhece a
  mesma base e responde que a leitura conversacional do gráfico ainda não está implementada, sem calcular nem chamar o
  provedor.
- A revisão (`context_revision`) precisa ser a atual da sessão; com revisão antiga, o cálculo volta inteiro e
  `sessao.registrado` é falso, com o motivo ("O contexto mudou durante a resposta. …").
- Cada pedido do gráfico grava um resultado; ficam os 8 mais recentes do gráfico (`PANEL_KEEP`), e os mais antigos saem
  primeiro, também para abrir espaço nos limites da sessão (64 resultados, 32 MB). Os resultados de `/api/analyze` nunca
  saem por isso.
- Sem o cabeçalho: `{"registrado": false, "result_id": null, "motivo": "Sem sessão: …"}`. Sem `nivel` (contrato de
  21/10), nada é gravado e a resposta não traz `sessao`.

### Desvios em relação ao contrato de 22/10/2026

O contrato entre as frentes (seção 3) descreve os campos em parte; o que vale é o descrito acima. As diferenças e as
precisões:

- **Pedido:**
  - **formato decidido por `nivel`:** sem `nivel`, o contrato de 21/10, sem mudança; a página única envia sempre `nivel`;
  - **`indicador`** (obrigatória) entra em `options`: o contrato não diz a que indicador valem `grupos`, `faixas`,
    `tendencia`, `comparar` e `ordenar.atributo = "variacao"`;
  - **`premissas` e `rotulos` só nas planilhas:** na base do Brasil, 422 (o referencial e as demais premissas vêm do
    perfil oficial; o exemplo `premissas: {"crs": "SIRGAS2000"}` do contrato vale para a planilha). Os nomes são os das
    opções de `/api/analyze`, com `confirmed_roles`, `count_unit`, `custom_count_unit`, `object_declaration`,
    `category_constant`, `duplicate_policy` e `component_columns` além de `crs` e `number_format`;
  - **`comparar`** aceita só ids presentes na resposta e recusa itens relacionados;
  - **nível estados** recusa `base`, `conjuntos` (sem agregação de estados no gráfico), `referencia`, `faixas_distancia`,
    `rotatividade` e a distância em condições e ordenação.
- **Por item:**
  - `tendencia` traz também `familia` e `motivo_texto`; `velocidades` é a lista de números alinhada às observações;
  - `grupo.indice` vai de 1 a k; `faixa` e `faixa_distancia` são `{indice, rotulo}` (`indice` a partir de 1), `"fora"`
    ou `null` (não avaliável ou fora do universo);
  - `referencia_mais_proxima` traz `empate`, a lista dos membros à mesma menor distância (vazia sem empate);
  - `condicoes.por_condicao` é `[{estado, valor, motivos}]`, na ordem de `condicoes.definicao` do topo;
  - `ordem` é `{posicao, selecionado}`;
  - `rotatividade` tem os nomes `inicial`, `final`, `coorte_inicial`, `permanencia`, `saida`, `permanencia_percentual`,
    `saida_percentual`, `avaliavel` e `motivo`;
  - novo, sempre: `grupo_territorial`; nas planilhas, a unidade continua `tipo: "municipio"`.
- **No topo:**
  - `tendencia` é o resumo inteiro do motor (`janela` é um objeto; `contagens` é por classe), mais `indicador`,
    `unidade_valor`, `unidade_tempo` e `universo`;
  - `grupos`, `faixas`, `faixas_distancia`, `condicoes` e `ordenacao` trazem os campos a mais listados acima (universo,
    rótulos, limites, definição, selecionados); `fora` e `nao_avaliaveis` das faixas são contagens;
  - `comparacao` traz `indicador`, `relacoes` e `notas`; `maior` e `menor` são listas (empate); entre três itens, sem
    `diferencas` (AT-84);
  - `contexto.brasil` traz também `rotulo`, `competencia_populacao`, `avaliabilidade`, `motivo`, `nota` e
    `regra_populacao`, e é `null` nas planilhas;
  - `disponibilidade` ganha `distribuicao`, `densidade` e `grupos` (pedido de 22/10 sobre as planilhas) e o campo
    `pendencia` em cada entrada;
  - `sessao` ganha `motivo`;
  - novos: `nivel`, `indicador`, `rotulos` e `dominios.tendencia`.
- **Pendência:** a forma do contrato; `chave` pode ser `null` (escolha que a tela não resolve), e o formato de 21/10
  também a devolve.
- **Sessão:** `record_panel` em vez de `record_result`: a mesma conferência de revisão e os mesmos limites, mas o
  gráfico, que grava a cada pedido, guarda só os 8 resultados mais recentes, sem descartar os de `/api/analyze`.
- **Universo:** grupos, faixas, condições, ordenação e as contagens da tendência valem só nos itens base do nível.
- **Planilhas:** `versao_base` é o SHA-256 do arquivo enviado; `rotulos` aceita `genero`.

### Desvios em relação ao contrato de 23/10/2026 (mapa e frase-resumo)

O contrato entre as frentes (`frontend/src/mapaContrato.ts`, `DadosDoMapa`) vale como está; as precisões:

- **Mapa:** `sem_coordenada` cobre também a unidade do catálogo sem registro na competência (motivo
  `SEM_REGISTRO_OBSERVADO`), para que todo id de item tenha ponto ou motivo; `geo_version` (opcional, base Brasil) recusa
  o pedido se a camada complementar mudou depois da preparação, como em `POST /api/painel` com referência; o motivo vem
  em texto com o código entre parênteses, como os motivos dos itens.
- **Frase-resumo:** além de `texto`, o resumo traz `partes`, `segmentos`, `contagens`, `versao` e `nota` (seção
  "Frase-resumo"); no contrato de 21/10 (sem `nivel`), a resposta não muda.
- **Grupos do mapa:** com menos de duas unidades com valor do indicador, `grupos_mapa` vem `null` (e `grupo_mapa` nulo nos
  itens), sem recusar o pedido, porque a tela pede os grupos do mapa em todo pedido; `grupos` continua recusado nesse
  caso (seção "Grupos do mapa").

### Desempenho

- Uma preparação por competência pedida, sobre as linhas da competência e da categoria; na base Brasil verificada, a
  preparação da competência, as coordenadas da competência e as séries da tendência dos municípios (por janela e itens)
  ficam na memória da versão (`request_memo.per_source`, nas condições de U8 em `Docs/OTIMIZACAO_LATENCIA.md`, só sobre a
  cópia íntegra marcada).
- A tendência prepara numa só passagem as linhas da janela, só dos itens pedidos; distâncias vetorizadas
  (`nearest_exact`).
- A resposta já sai em tipos JSON nativos e é serializada direto, sem a conversão genérica do FastAPI e, desde
  23/10/2026, sem a conferência de referências circulares do `json` (os mesmos bytes).

Desde 23/10/2026 (meta de 0,4 a 0,8 s no servidor), sem mudar número nenhum:

- **Reaproveitamento entre pedidos** (`painel._reaproveitar`, sobre a mesma memória da versão, nas condições de U8): as
  distâncias até a referência, as condições, os grupos por posição (os de `grupos` e os do mapa, `grupos_mapa`, leem a
  mesma memória), as faixas, a ordenação, a tendência por item (nível municípios) e a linha de contexto do Brasil ficam
  guardadas por versão da base e da camada de coordenadas, com a chave de tudo de que cada cálculo depende (nível,
  mapeamento, competência, categoria, universo, itens, referência, janela, indicador, competência inicial e a definição da
  análise). Quando só a ordenação muda, o resto vem do pedido anterior; mudar o universo, a competência ou a referência
  recalcula o que depende deles. Cada pedido recebe cópia própria; planilhas enviadas nunca ficam guardadas.
- **Grupos por posição em bloco:** a distribuição de `main._compute` monta o detalhamento pelas colunas, sem uma
  `Series` por município (`iterrows`), com os mesmos valores, na mesma ordem (também em `/api/analyze`).
- **Variação exata em inteiros:** a variação percentual de `temporal_change.change` sobre pares de inteiros
  (`painel._percent`), sem um `Fraction` por operação; o float publicado é a divisão inteira com arredondamento correto
  (o mesmo de `float(Fraction)`), e o valor exato lido pela ordenação é o `Fraction` do mesmo par.
- **Ordenação:** `combined_criteria.ranking_of` recebe os avaliáveis já na ordem dela (`painel._ranked`, com o float do
  valor à frente na chave, monótono no valor exato; em float igual, decide o valor exato) e só confere a sequência.
- **Linhas da competência e chave de execução:** as posições das linhas por competência e categoria (`_row_positions`) e
  o resumo das linhas lido pela chave de execução (`_rows_hash`) ficam na memória da versão; as premissas do perfil
  oficial também (`_official_settings`); a condição de cada coordenada é lida uma vez por pedido. O quadro guardado da
  base Brasil já fica consolidado, e a cópia própria de cada pedido não refaz a consolidação (cerca de 50 ms a menos em
  todo pedido à base Brasil, em qualquer rota).
- **Compressão gzip** (`GZipMiddleware` do FastAPI, nível 1, a partir de 64 KB, para o cliente que aceita gzip, como o
  navegador): os 10,7 MB do pedido "com tudo" vão em 2,2 MB, com cerca de 0,08 s para comprimir. Descomprimido, o corpo é
  o mesmo byte a byte; nada depende do corpo cru (a tela e os roteiros de navegador leem o JSON já descomprimido).
- **Conferência:** o script de medição (`backend/tests/bench_painel.py`, não é teste) compara o SHA-256 canônico de cada
  corpo com o da medição anterior: nos casos da tabela e em outras 76 respostas (estados, conjuntos, planilhas, erros e
  sequências que mudam uma análise por vez), as respostas são as do código anterior, salvo o campo novo `resumo`. Os
  testes de `backend/tests/test_painel_desempenho.py` conferem cada atalho com o caminho que ele substitui.

Medição local de 23/10/2026 com a base versionada, as duas versões no mesmo ambiente, em rodadas alternadas (antes: o
código de `9f0c595`; depois: o atual): mediana de 10 pedidos depois do primeiro (duas rodadas de 5), no servidor de
teste (`TestClient`, que aceita gzip como o navegador: o tempo inclui comprimir e descomprimir), sem o aquecimento da
base (`ADT_AQUECIMENTO=0`). O primeiro pedido é o primeiro do caso no processo, na ordem da tabela (os casos anteriores
já deixaram parte da memória da versão). Este ambiente é mais lento que o de 22/10/2026: o pedido "com tudo", no código
anterior, levou 1,98 s aqui e 1,58 s lá.

| Pedido | Antes: tempo (primeiro pedido) | Depois: tempo (primeiro pedido) | Resposta | Transferido |
|---|---|---|---|---|
| Contrato de 21/10: todos os municípios, variação e referência | 0,76 s (1,23 s) | 0,38 s (1,02 s) | 2,6 MB | 0,6 MB |
| Página única: todos os municípios, distribuição | 0,35 s (0,37 s) | 0,18 s (0,29 s) | 2,4 MB | 0,2 MB |
| Página única: 27 estados (E1) | 0,22 s (0,20 s) | 0,10 s (0,10 s) | < 0,1 MB | < 0,1 MB |
| Página única: 27 estados, tendência de 11 junhos e quartis | 0,25 s (0,30 s) | 0,12 s (0,13 s) | < 0,1 MB | < 0,1 MB |
| Página única: Amazonas (62), tendência de 11 junhos e condições | 0,25 s (0,38 s) | 0,09 s (0,18 s) | 0,1 MB | < 0,1 MB |
| Página única: todos, tendência de 11 junhos e condições | 1,03 s (1,87 s) | 0,53 s (1,99 s) | 9,4 MB | 1,9 MB |
| Página única: todos, tendência de 22 competências e condições | 1,18 s (3,35 s) | 0,72 s (2,86 s) | 13,4 MB | 3,0 MB |
| Página única: todos, com tudo (variação, tendência, quintis, faixas, faixas de distância, condições, ordenação e comparação) | 1,98 s (1,84 s) | 0,76 s (0,87 s) | 10,7 MB | 2,2 MB |
| Página única: todos, tendência de 11 junhos e condições, com sessão | 1,39 s (1,25 s) | 0,73 s (0,98 s) | 9,4 MB | 1,9 MB |
| Mapa: coordenadas de todos os municípios (rota nova) | — | 0,11 s (0,12 s) | 0,3 MB | < 0,1 MB |

Todos os pedidos repetidos ficaram dentro da meta. Ficaram acima dela:

- **O primeiro pedido com a tendência de todos os municípios** (2,0 s com 11 junhos; 2,9 s com 22 competências): é o
  cálculo frio do motor, uma vez por versão e janela — a preparação das linhas da janela (`data_contract.prepare`, 61
  mil ou 122 mil linhas), a classificação (`trend.classify_frame`) e o resumo das linhas lido pela chave de execução —,
  mais, no mesmo pedido, as condições (`combined_criteria.evaluate`) e as distâncias (`nearest_exact`) ainda não
  guardadas. Nenhuma delas mudou: são as funções das análises, e acelerá-las é mudar o motor comum, fora desta rodada. O
  primeiro pedido do processo também calcula o catálogo territorial e as coordenadas da competência (cerca de 0,3 s); o
  aquecimento na partida (U11) faz só a inspeção.
- **O tamanho da resposta com a tendência:** 9,4 MB a 13,4 MB, por causa das observações e velocidades de cada
  município, que continuam na resposta (o contrato não muda). Serializar leva 0,2 s a 0,3 s e comprimir, cerca de
  0,1 s; com 22 competências, o pedido repetido fica em 0,72 s, perto do limite.
- **A gravação na sessão** acrescenta cerca de 0,2 s com 9,4 MB: a sessão serializa o resultado inteiro para conferir
  a integridade (`conversation_session.record_panel`).
