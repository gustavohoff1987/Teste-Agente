# Abrangência territorial: Brasil, estados e municípios

Decisões do responsável pelo produto de 19/10/2026: **D3** (abrangência vertical com Brasil, estados,
todos os municípios e municípios), **D4** (população do Brasil pela soma municipal de junho) e **D5**
(taxa nacional como referência de contexto na densidade). Este documento descreve o motor e a API
(`backend/territorial_levels.py`) e a tela: a lista vertical da caixa "Abrangência territorial" (§6) e a
taxa nacional no mapa e nas barras (§4.1). As mudanças estão no [registro](REGISTRO_DE_COMPORTAMENTO.md).

## 1. Princípios

- Cada nível é um universo próprio, e **nenhum nível é somado a outro** (RQ-DAD-30). Não há linha de
  total entre níveis.
- **Brasil (BR):** contagem nacional de `Dados_Brasil.xlsx`. Nunca é a soma dos municípios.
- **Estado (UF):** soma dos municípios pelo prefixo do código IBGE (regra governada
  `brasil-cod-uf-prefix-1`). A coluna `uf` da fonte não é usada. É sempre SOMA_DOS_COMPONENTES, com
  possível dupla contagem: quem atua em mais de um município é contado em cada um. Nunca é comparado
  com o total do Brasil.
- **Município (MUN):** o caminho municipal de sempre. "Todos os municípios" e "Municípios de um estado"
  são expansões em municípios.
- Os pedidos que já existiam continuam com as mesmas linhas: só municípios seguem o caminho municipal;
  só o Brasil sem densidade, o caminho nacional. Os demais pedidos vão para a rota de níveis, que
  calcula cada universo com o mesmo motor (`data_contract.prepare`, `main._compute` com o quadro já
  preparado e `temporal_change.evolution`).

## 2. Matriz por análise (base oficial)

| Análise | Brasil | Estados | Municípios | Combinação | Mínimo |
|---|---|---|---|---|---|
| Densidade, Quantitativos, Relatórios | sim | sim (objeto) | sim | blocos por nível | 1 |
| Evolução temporal | sim | sim, com suporte por competência | sim | uma série por objeto; painéis por tipo de contagem | 1 objeto |
| Comparações | sim, lado a lado | sim | sim | relações só dentro do nível | 2 objetos |
| Distribuição, Recortes e rankings | não | sim, só entre estados | sim | mesmo nível | 2 |
| Agregações | não | entra pelos seus municípios | sim | união, um resultado | 2 municípios |
| Análise espacial, Referência mais próxima, Critérios combinados | não | não (o grupo de municípios vale) | sim | — | 1 |
| Rotatividade | indisponível na base Brasil | — | — | — | — |

Motivos devolvidos pelo backend (mesmo texto no erro 422 e no pré-exame):

| Análise | Brasil fora | Estado fora |
|---|---|---|
| Distribuição | "Não se aplica: a distribuição agrupa vários territórios, e o Brasil é um só." | — |
| Recortes e rankings | "Não se aplica: o ranking ordena vários territórios, e o Brasil é um só." | — |
| Agregações | "Não se aplica: o total do Brasil vem pronto da fonte nacional e não é somado a outros territórios." | — (o estado é expandido) |
| Espacial, mais próxima, critérios | "Não se aplica: as distâncias e os critérios usam a localização de cada município." | "Não se aplica: estados não têm um ponto único. Para usar os municípios de um estado, marque o grupo em Municípios." |
| Rotatividade | "A rotatividade não está disponível nos dados do Brasil: falta um identificador da mesma pessoa entre os períodos." | (o mesmo) |

Estados e municípios juntos na distribuição ou no ranking são uma escolha pendente ("Você marcou
estados e municípios. … usa territórios do mesmo tipo: escolha qual manter."); o mínimo também é
conferido no backend ("… precisa de pelo menos dois territórios do mesmo tipo. Marque mais um.";
"A agregação precisa de pelo menos dois municípios.").

## 3. Regras de cálculo

### 3.1 Brasil e a regra BR-POP-JUNHO-1 (D4)

- **Numerador:** a contagem nacional da competência.
- **Denominador:** para o ano Y, a soma da `população_estimada` de cada município na competência de
  **junho** de Y, cada código uma vez. Ela vale para janeiro e para junho de Y (nunca a população de
  janeiro). Valores de referência de junho de 2024: 212.583.750 habitantes; densidade
  502.495 ÷ 212.583.750 × 1.000 = **2,3638** por 1.000 habitantes.
- **Município sem registro em junho:** a população não é estimada. Ela soma os municípios com registro,
  e o valor fica **avaliável com limitações**, motivo `POPULACAO_NACIONAL_PARCIAL`, com a lista dos
  ausentes. Na base atual, isso acontece só em 2015: falta o 430607 (CRISTAL DO SUL, RS) em junho, e a
  população de 2015 soma os 5.569 municípios com registro (204.450.315). Nota exibida:
  "Em junho de 2015, a base municipal não tem registro de 1 município (CRISTAL DO SUL, RS, 430607); a
  população do Brasil desse ano soma os 5.569 municípios com registro." A série nacional continua
  comparável para a tendência: 22 observações na série completa e 11 na série anual de junho, ambas
  "Crescimento".
- **Ano sem junho na fonte municipal:** densidade não avaliável (`SEM_COMPETENCIA_DE_JUNHO`), lacuna e
  nunca zero. População conflitante do mesmo município em junho é erro, sem escolha arbitrária.
- Densidade em aritmética exata (contagem × 1.000 ÷ população, arredondada só ao entregar). A regra é
  autorizada pela CAP-IND-02 (L1742) e leva a limitação `DENOMINADOR_ALTERNATIVO` no resultado.
- Colunas da linha: "Competência da população" (ex.: 202406), "Cobertura" (ex.: "População: 5.569 de
  5.570 municípios em junho de 2015; sem registro: 430607") e "Condição".
- O índice da fonte municipal (membros por estado, nomes e população de junho por ano) é calculado uma
  vez por versão da base, com trava, e nunca guardado nos atributos do quadro.

### 3.2 Estado

- Membros previstos: os códigos da versão com o prefixo do estado. Valores por competência e categoria:
  Σ quantidade e Σ população dos membros **presentes** naquela competência (mesmo suporte no numerador
  e no denominador). Densidade = Σq ÷ Σpop × 1.000.
- Rótulos: território "São Paulo (SP)", nível "Estado (soma dos municípios)", tipo de contagem
  "Soma dos componentes (possível dupla contagem)", cobertura "644 de 645 municípios; sem registro:
  353286".
- Membro sem registro: AGREGADO_PARCIAL, com o valor dos presentes e a nota "{Estado} em {competência}:
  soma parcial, {k} de {N} municípios; sem registro: {códigos}. O valor não representa o estado
  inteiro." Na base atual: RO, MG e SP em janeiro de 2015, SC em janeiro de 2017 e RS em junho de 2015
  e janeiro de 2020.
- `metadata.suporte_agregado`: por estado, competência e categoria, `previstos`, `incluidos`,
  `ausentes`, `tipo: "SOMA_DOS_COMPONENTES"`, `fundamento: "CAP-AGR-01"` e a regra.
- **251365:** PB pelo prefixo do código. Em 2016/6, a fonte declara PA na coluna `uf` (população
  331.942); a linha entra como está, com a nota `UF_DECLARADA_DIVERGENTE`: "Em {competência}, {n}
  registro(s) da fonte municipal trazem na coluna uf um estado diferente do indicado pelo código IBGE
  ({códigos}); o estado segue o código, e os valores entram como estão na fonte." Ela aparece na
  população do Brasil de 2016 (janeiro e junho), na PB em 2016/6 e nos municípios dessa competência. A
  constante `UF_DIVERGENTE_EXCLUI` (falsa) deixaria a linha fora das somas. Nas bases importadas, a
  hierarquia divergente continua bloqueando a unidade.

### 3.3 Municípios

- Escolhas diretas (`ids`) continuam estritas: código inexistente ou sem registro no recorte é erro.
- Expansões ("Todos os municípios", grupos por estado e, na agregação, estados) viram os municípios
  **presentes** depois dos filtros de período e categoria; os ausentes ficam na nota de cobertura e em
  `metadata.selecao_territorial.expansoes` (previstos, incluídos e ausentes por competência).
- "Todos os municípios" sozinho sai sem `territory_ids`, com a nota de cobertura ("Todos os municípios:
  os 5.570 municípios previstos nesta versão da base têm registro no recorte escolhido." ou a lista dos
  ausentes por competência). Na agregação: "Soma dos 5.570 municípios (possível dupla contagem); não é
  o total do Brasil, que vem da contagem nacional."

### 3.4 Por análise na rota de níveis

- **Quantitativos, densidade e relatórios:** linhas por nível, na ordem Brasil → estados (por código)
  → municípios, com a coluna "Nível" e "Tipo de contagem". Competência pedida que não existe na fonte
  de um nível vira linha "Não avaliável: sem registro nesta competência na fonte {nacional|municipal}".
  Desde o visual completo (19/10/2026), as métricas são **por nível**, com a chave extra `nivel` (BR, UF ou
  MUN): "Brasil (total nacional): registros avaliáveis" e "…: registros não avaliáveis", "Estados (soma dos
  municípios): …" e "Municípios: …"; os números de níveis diferentes nunca são somados (antes, "Unidades
  avaliáveis" e "Não avaliáveis" contavam só os municípios). A descrição diz o que é cada bloco: "Densidade de
  pessoas por 1.000 habitantes por nível territorial (Brasil (total nacional), estados (soma dos municípios) e
  municípios), em blocos separados; nenhum nível é somado a outro." e "Quantitativos de pessoas por nível
  territorial (…)" (antes, "pessoas por 1.000 habitantes.").
- **Evolução temporal:** uma única chamada de `evolution` para todos os objetos. O estado cujo conjunto
  de municípios presentes muda na janela recebe a INCOMPARABILIDADE pela entrada (`incomparable`):
  "Membros efetivos diferentes entre competências (201501: 353286 ausente)"; se os membros dos dois
  extremos forem diferentes, a mudança também não é avaliada (`change_incomparable`, condição
  "… (INCOMPARABILIDADE)"). Esses estados vão para `representacao.serie.quebras` com as competências,
  e a nota diz "A tendência de {Estado} não foi avaliada…" ou "A mudança e a tendência de {Estado} não
  foram avaliadas…". Na série completa da base atual, SP e RS não são comparáveis; na série de junho, só
  RS (430607 em 2015/6).
- **Comparações:** maior, menor, igual e diferença só entre objetos do mesmo nível, com o motor de
  sempre (par A/B ou três ou mais, AT-84). O Brasil e os objetos isolados ficam lado a lado: "Lado a
  lado: o Brasil é outro nível e não entra em maior, menor nem diferença com estados ou municípios.",
  "Lado a lado: único estado; a soma dos municípios não é comparada com municípios nem com o Brasil." e
  "Lado a lado: único município; não é comparado com outros níveis.". Estado parcial fica fora da
  relação: "Não avaliável: agregado parcial (…)". Métrica: "Territórios comparados".
- **Comparações com competência dos valores e janela (desde 19/10/2026, D6):** com `comparison_values_period`,
  as relações usam só essa competência, sempre dentro do mesmo nível (o Brasil lado a lado, sem relação; estado e
  município nunca relacionados), e `detail_rows` traz um registro por objeto, com o "Nível", quantidade, população,
  densidade, "Tipo de contagem", "Cobertura", "Competência da população" (Brasil na densidade), a condição e, com
  duas ou mais competências, a mudança e a tendência na janela. Estado parcial na competência dos valores fica fora
  das relações ("Não avaliável: agregado parcial (…)"), mas o registro dele guarda o valor ("Avaliável com
  limitações: soma parcial (AGREGADO_PARCIAL)"); o estado cujo suporte muda na janela recebe INCOMPARABILIDADE pela
  entrada de `evolution`, com a nota "A tendência de {Estado} não foi avaliada…". Municípios de `detail_rows` na
  ordem do código (RQ-REP-03). `metadata.comparacao.grupos` traz, por nível, o rótulo, o tipo de contagem, os
  objetos pedidos e se houve relação; `sem_relacao`, os objetos sem relação e o motivo. Métricas: "Territórios
  comparados" e "Competências na janela". Na série anual de junho com valores em 06/2024: Brasil 2,3638
  (Crescimento), SP 5,2032 (Crescimento), RS não comparável (430607 ausente em 06/2015) e AM, Manaus, Tefé e
  Parintins sem classificação (mudança de direção); ver `Docs/EVOLUCAO_TEMPORAL_E_TENDENCIA.md`, seção 8.
- **Ranking e distribuição de estados:** universo "estados selecionados (soma dos municípios)"; estado
  parcial fica sem posição (ranking) ou fora das classes (distribuição, com nota), e com menos de dois
  estados avaliáveis o pedido é recusado ("Menos de dois estados avaliáveis em …"). Nota: "A dupla
  contagem varia entre os estados; a ordem e as classes podem refletir isso.". Métricas (19/10/2026): no
  ranking, "Territórios ordenados" e "Não avaliáveis" (estado parcial conta como não avaliável); na
  distribuição, "Unidades classificadas", "Classes" e "Estados fora da distribuição"
- **Notas de nível:** procedência do Brasil ("Brasil (total nacional): contagem nacional de médicos da
  base Brasil, não a soma dos municípios. População: soma das populações estimadas dos {N} municípios em
  junho de {Y}, usada também em janeiro de {Y} (regra BR-POP-JUNHO-1). Densidade = contagem ÷ população
  × 1.000."; numa série de vários anos, "dos {N} municípios em junho de cada ano" quando todos os anos somam
  o mesmo número de municípios e "dos municípios com registro em junho de cada ano" quando algum ano é
  parcial, como a série que inclui 2015); janeiro com o Brasil e outro nível ("Em janeiro, a população do Brasil é a de junho do
  mesmo ano; nos estados e municípios, é a da própria competência."); estados ("Estados: soma dos
  municípios de cada estado (código IBGE). …"); mais de um nível ("Brasil, estados e municípios aparecem
  em blocos separados; nenhum nível foi somado a outro.").
- **Avaliabilidade:** `metadata.evaluability.limitacoes` reúne `NIVEIS_TERRITORIAIS_DIFERENTES`,
  `DENOMINADOR_ALTERNATIVO`, `POPULACAO_NACIONAL_PARCIAL`, `SOMA_COM_POSSIVEL_DUPLA_CONTAGEM` e
  `AGREGADO_PARCIAL`, quando cabem.

## 4. Taxa nacional de referência na densidade (D5)

- Aparece em `density` e em `report` com indicador densidade, na base oficial, sempre que o resultado
  tem municípios, **inclusive nas chamadas antigas da API, sem abrangência**.
- `metadata.referencia_nacional`: rótulo "Brasil (total nacional)", papel `REFERENCIA_DE_CONTEXTO`,
  unidade "por 1.000 habitantes", regra BR-POP-JUNHO-1, tipo de contagem, fontes, versão da base,
  limitações (`NIVEIS_TERRITORIAIS_DIFERENTES`, `DENOMINADOR_ALTERNATIVO`) e, por competência e
  categoria, numerador, denominador, competência da população, valor, avaliabilidade, motivo, ausentes
  e, quando parcial, a nota. Nota da referência: "Taxa nacional como referência de contexto: não
  classifica nem colore os municípios e não entra em rankings, distribuições ou agregações."
- `metadata.representacao.referencias`: os mesmos valores, para desenho. O frontend só desenha: não
  calcula, não classifica e não colore municípios acima ou abaixo da taxa.
- Falha no cálculo: `{"estado": "INDISPONIVEL", "motivo": …}`; a análise nunca falha por isso.
- Não entra em ranking, distribuição, comparação, agregação nem evolução, nem nas linhas, nas métricas
  ou na avaliabilidade do resultado municipal. Desde o visual completo (19/10/2026), aparece também como
  indicador de contexto do resumo do resultado (`metadata.representacao.resumo.indicadores`, papel
  `REFERENCIA_DE_CONTEXTO`) e na frase-resumo ("Referência de contexto: taxa nacional de 2,36 por 1.000
  habitantes (Brasil, total nacional); não classifica nem colore os territórios."), nunca como "acima" ou
  "abaixo"; com o Brasil como bloco do resultado, a frase não repete o valor.
- `serie` (19/10/2026), em `metadata.referencia_nacional` e em `representacao.referencias[]`: a taxa de **todas**
  as competências da fonte nacional (`competencia`, `categoria`, `valor`, `avaliabilidade`, `motivo`,
  `competencia_populacao`), para o minigráfico do cartão de contexto; competência sem população de junho fica com
  `valor` nulo (lacuna), e um ano inconsistente fora do resultado vira `NAO_AVALIAVEL`/`POPULACAO_NACIONAL_INCONSISTENTE`
  só na série, sem derrubar a referência.

### 4.1 Na tela

- **Legenda do mapa** (densidade de uma competência e uma categoria): uma marca tracejada sobre a escala,
  na posição do valor (na borda quando fica fora da escala), e o texto (`national-reference`) "Brasil
  (total nacional): 2,36 por 1.000 habitantes · referência de contexto; a cor dos municípios não é
  classificada em relação a ela.", com "(fora da escala dos municípios)" quando o valor fica fora dela e,
  em janeiro, "Em janeiro, a população do Brasil é a de junho de {Y}.". O domínio de cor continua o
  mínimo e o máximo dos municípios; as cores não mudam. O gancho de teste `__adtMapModel.reference`
  traz valor, competência, categoria e rótulo.
- **Barras dos municípios:** linha tracejada vertical com o rótulo "Brasil 2,36" e a legenda
  (`bars-reference-line`) "Brasil (total nacional): 2,36 por 1.000 habitantes, referência de contexto;
  a linha não classifica os municípios.". A referência entra no eixo; as barras não mudam de cor. Vale
  também nas barras com rolagem (mais de 40 municípios); nelas, o número de cada barra fica logo depois
  do fim dela (perto da borda direita, dentro da barra), num fundo claro por cima da linha tracejada, para
  que nem a barra nem a linha o cubram.
- Com vários níveis no resultado, as barras dos municípios (`level-panel-mun`) e as dos estados
  (`level-panel-uf`, "· Estados (soma dos municípios)", com o aviso de possível dupla contagem) ficam
  em figuras separadas; nunca há barra do Brasil entre municípios. A série temporal com vários painéis
  (`serie.paineis`) desenha um gráfico por painel (`level-panel-{id}`).
- **Visual completo (19/10/2026):** o cabeçalho do resultado traz o cartão de contexto da taxa nacional (borda
  tracejada, selo "contexto", minigráfico da `serie`) ou, quando o Brasil é um bloco do resultado, o cartão do
  Brasil com o mesmo minigráfico; a dica do ponto no mapa e o detalhe do território mostram "Brasil (contexto)"
  ao lado do valor do município. Os cartões de destaque trazem o nível; o do estado tem textura, o aviso
  "possível dupla contagem · não comparável com a contagem nacional", "na soma das contagens dos municípios" e
  "por 1.000 habitantes (soma dos municípios)" (RQ-REP-14). Na aba Gráficos, o contêiner `levels-panel` reúne o
  bloco do Brasil (`level-panel-br`: valor, tipo de contagem e "Lado a lado: não entra em maior, menor nem
  diferença com estados ou municípios."), os estados (`level-panel-uf`, textura listrada e `uf-warning`, sem
  linha nacional) e os municípios (`level-panel-mun`, com a linha nacional e um separador por estado,
  `bar-group-separator`, lido de `universe.members[].state`, sem reordenar nem contar). Na comparação, um bloco por
  nível, cada um no seu eixo, e os halteres por nível (ver `Docs/BLOCO3_MAPAS_VISUALIZACOES.md`).

## 5. Contrato da API

### 5.1 Pedido (`/api/analyze` e `/api/preflight`, `dataset=brazil`)

```json
"abrangencia": {"brasil": true, "estados": ["13", "35"],
                "municipios": {"todos": false, "estados": ["15"], "ids": ["code:130260"]}}
```

- `estados` são objetos UF (soma); `municipios.estados` são grupos (expansão); `ids` no formato do
  catálogo. `scope` precisa ser `auto` ou `municipal`; `mapping` é o mapeamento municipal da inspeção.
- Erros (422): upload com abrangência ("A abrangência por Brasil e estados existe só na base Brasil
  oficial."); abrangência com `territory_ids` ("Use a abrangência territorial ou a lista de territórios,
  não as duas."); `scope=national` ("Com a abrangência territorial, o recorte é resolvido pela análise;
  envie scope=auto."); nada marcado ("Nenhum território marcado na abrangência."); estado fora da lista
  ou sem membros ("Estado não reconhecido nesta base: {x}."); identificadores repetidos ou acima dos
  limites; nível não aceito (o motivo do §2).
- Absorção explícita, listada em `metadata.selecao_territorial.absorvidos`: "Todos os municípios"
  absorve grupos e ids; um grupo absorve os ids dele; na agregação, um estado absorve o grupo e os ids
  dele.

### 5.2 Roteamento e resposta

| Abrangência | Rota | Quadro |
|---|---|---|
| só municípios, ou estados na agregação | `municipal` | municipal, com `territory_ids` derivados (omitidos em "Todos os municípios") |
| só Brasil em quantitativos, ou na evolução e no relatório por quantidade | `nacional` | nacional |
| qualquer outra | `niveis` | as duas fontes, da mesma leitura verificada |

- `metadata.selecao_territorial`: `pedido`, `ids_canonicos` (`br`, `uf:35`, `mun:todos`, `mun:uf:35`,
  `code:…`), `absorvidos`, `rota` e `expansoes`.
- Na rota de níveis: `metadata.source.scope = "niveis"` com `fontes_usadas`; `universe.members` com
  `nivel` (BR, UF ou MUN) e `classification_scope` "universos separados por nível";
  `metadata.populacao_nacional` (por competência do Brasil); `metadata.suporte_agregado`;
  `representacao.niveis` (coluna, ordem, tipos e "Município" no mapa) e `serie.paineis` (na quantidade,
  um painel por nível; na densidade, municípios com o Brasil como referência e estados à parte).
- O mapa desenha só municípios. Sem municípios: "Mapa não aplicável: Brasil e estados são agregados sem
  ponto; marque municípios para ver o mapa."

### 5.3 Inspeção, pré-exame e conversa

- `/api/inspect` da base oficial no recorte municipal devolve `niveis`: regras, Brasil (períodos,
  competências com densidade não avaliável ou com limitações), estados com sigla, nome, `rotulo_grupo`
  ("Municípios do Amazonas", "Municípios da Paraíba") e número de municípios, total de municípios e a
  matriz por análise (`operacoes`, com `texto` e `motivos`). As listas de municípios continuam em
  `preflight.territory_choices`, agora com `state_code` e, no 251365, `hierarchy_note`.
- `/api/preflight` com abrangência segue o mesmo roteamento; na rota de níveis devolve o pré-exame da
  fonte municipal inteira mais `capabilities[op].niveis` (`brasil`, `estados`, `municipios` e, quando
  a seleção não cabe, `selecao`), com o pior estado das partes e os motivos prefixados ("Brasil: …").
  O pré-exame recebe a análise no campo `operation`.
- Escolha pendente na abrangência (estados e municípios juntos na distribuição ou no ranking, ou
  territórios de menos): o `/api/preflight` não recusa o pedido; devolve o pré-exame da fonte municipal
  inteira com a análise em "escolha pendente" (`needs_confirmation`), o motivo em `reasons` e em
  `capabilities[op].niveis.selecao`, e `abrangencia_pendente` com o mesmo texto. O `/api/analyze`
  continua recusando (422) com esse texto.
- A conversa (`/api/exploration/interpret`, `/api/llm/interpret-context`) continua recebendo só ids de
  município; "municípios da Paraíba" passa a incluir o 251365 (223 municípios na base atual).
  Abrangência, níveis, população nacional e taxa nacional nunca vão ao provedor de IA; desde 19/10/2026, nem
  o resumo do resultado, a comparação com janela (`metadata.comparacao`) ou a opção `comparison_values_period`.

### 5.4 Chave de execução

- `options` guarda a abrangência normalizada (listas ordenadas): a ordem do pedido não muda a chave.
- `metodos` entra só quando usado: `niveis` (`NIVEIS-BR-UF-MUN-1`), `populacao_nacional`
  (`BR-POP-JUNHO-1`) e `estado` (`brasil-cod-uf-prefix-1`), além de `tendencia` na evolução.
- Mudam de propósito as chaves das densidades e dos relatórios com densidade da base oficial (D5) e as
  da rota de níveis. As demais chamadas antigas mantêm a chave.
- Desde 19/10/2026, a comparação com `comparison_values_period` tem chave própria (a opção entra em `options` e,
  com a janela, `metodos.tendencia`); a interface sempre envia a opção quando há competência escolhida, então as
  comparações feitas pela tela mudam de chave. A comparação sem a opção mantém a chave.

## 6. A lista vertical na tela

- Só na caixa **Abrangência territorial** da base oficial (`TerritorialScopeSelector.tsx`, região
  "Seleção territorial compartilhada"). Os uploads e a "Seleção de referências" continuam com a seleção
  por pesquisa (`TerritorialSelection.tsx`).
- A inspeção da base oficial é sempre municipal e traz o bloco `niveis`; trocar de análise não chama
  `/api/inspect` nem troca de fonte. A lista de municípios vem da inspeção (fonte municipal inteira),
  nunca do pré-exame de uma rota nacional.
- Seções, com caixas de marcar nativas (Tab entre os controles, Espaço marca, botão abre cada grupo):
  - **Brasil:** "Brasil (total nacional)", com a ajuda "Total da fonte nacional; não é a soma dos
    municípios.".
  - **Estados** (selo "soma dos municípios"): o aviso "Cada estado é a soma dos seus municípios: o mesmo
    médico pode ser contado em mais de um município. Por isso, o valor do estado não é o número de
    médicos diferentes e a soma dos estados não é o total do Brasil.", "Todos os estados (N)"
    (tri-estado) e cada estado ("Amazonas (AM)", "soma de 62 municípios"). Sem estados identificados
    pelos códigos (bases sintéticas), a seção informa "Nenhum estado identificado pelos códigos desta
    base.".
  - **Municípios:** "Todos os municípios" ("Um valor para cada um dos 5.570 municípios.") e um grupo
    recolhível por estado: caixa do grupo ("Municípios do Amazonas (62)", tri-estado), botão "Amazonas
    (AM)" com "k de N municípios" e, aberto, os municípios ("MANAUS [130260]"; no 251365, a nota da UF
    declarada divergente). Com "Todos os municípios" marcado, grupos e municípios aparecem incluídos e
    desabilitados. Municípios sem estado identificado ficam numa lista simples.
- Resumo ao lado: "{n} selecionados", a composição ("Brasil · 1 estado · 3 municípios") ou "Padrão desta
  análise: …", a escolha pendente (`territory-rule-message`) e "Limpar seleção".
- **Padrão:** sem nada marcado vale o padrão da análise (§2: Brasil em quantitativos, evolução temporal
  e relatórios; todos os municípios nas demais), com o selo "padrão desta análise" e a caixa desmarcada.
  A primeira marcação substitui o padrão (nada é copiado); "Limpar seleção" volta a ele.
- **Entre análises:** os municípios marcados continuam valendo (como na conversa, nas transferências e
  em "Usar como municípios-alvo", que substituem a seleção pelos municípios). O Brasil e os estados só
  valem nas análises que os aceitam; nas demais, a seção fica desabilitada com o motivo do §2 em uma
  linha, e eles voltam a valer ao retornar a uma análise que os aceita. Sem nada aplicável, vale o
  padrão. Não há lista de itens "fora desta análise".
- Marcar um grupo absorve os municípios dele; desmarcar um município de um grupo marcado deixa os demais
  marcados; "Todos os municípios" absorve grupos e municípios.
- Resumo da caixa (`scope-summary`), na ordem Brasil → estados → municípios: "Brasil (total nacional)",
  "Amazonas (estado)", "Amazonas e Pará (estados)", "3 estados", "Todos os municípios", "Municípios do
  Amazonas (62)", "MANAUS (AM)", "MANAUS (AM) e TEFE (AM)", "3 municípios: MANAUS (AM), TEFE (AM) e mais
  1", e as combinações ("Brasil (total nacional), Amazonas (estado) e MANAUS (AM)").
- A interface envia em `options.abrangencia` só a parte que vale na análise (ou o padrão dela) e manda a
  análise no pré-exame; o backend escolhe a rota e confere aceitação, mínimo e mistura. Escolha pendente
  deixa a caixa em destaque, mostra "Ajuste a abrangência territorial para continuar." e mantém o
  cálculo desabilitado. Nada é calculado na tela. A rotatividade, indisponível na base Brasil, segue sem
  abrangência.
- A conversa continua recebendo só os municípios marcados (`territory_ids`). Um pedido explícito pelo
  país inteiro marca só o Brasil; "nos municípios", sem municípios marcados, marca "Todos os municípios".
- A densidade do Brasil fica disponível na caixa Indicador (sai "(somente municípios)").

## 7. Análise espacial: uma competência e validade por território

- Na base oficial, a caixa Período da análise espacial pede uma competência ("Escolher período"; sai
  "Não se aplica"), com a nota "As distâncias usam as coordenadas da competência escolhida; em algumas
  competências, a fonte traz coordenadas diferentes para o mesmo município.". Brasil e estados não se
  aplicam; o grupo de municípios de um estado vale (expandido nos municípios presentes na competência).
- RQ-DAD-25 (validade por elemento): coordenada ausente, não numérica ou fora dos intervalos deixa só
  aquele território não avaliável: "Distância (km)" vazia (nunca zero), "Condição" "Não avaliável:
  coordenada inválida" ou "Não avaliável: coordenada ausente" (a coluna só aparece quando há algum),
  no fim da ordem, fora do mapa (`sem_geometria`), com a nota "{n} território(s) sem coordenada válida no
  recorte ficam não avaliáveis (COORDENADA_INVALIDA), sem distância e fora do mapa; os demais foram
  calculados." e o resultado avaliável com limitações. Vale para a base oficial (depois da camada
  complementar) e para as bases importadas.
- Território de referência sem coordenada válida: recusado com "O território de referência não tem
  coordenada válida na competência escolhida. Escolha outro território de referência.".
- Coordenadas válidas diferentes para o mesmo território entre competências: "Coordenadas conflitantes
  para o mesmo território entre competências. Escolha uma competência no período da análise." (escolha
  pendente); na mesma competência, "Coordenadas conflitantes para o mesmo território na mesma
  competência. Verifique o identificador territorial.". Vírgula decimal com o ponto escolhido continua
  sendo erro de formato da coluna.
- A tela mostra os motivos do pré-exame da análise espacial (`spatial-reasons`) com o mesmo texto do
  backend.

## 8. Fora deste escopo e pontos residuais

- "Estado de SP" (objeto) contra "municípios de SP" (grupo) na conversa: hoje os dois viram municípios.
- Navegação avançada por teclado (foco único com setas, busca por letra), filtro de texto e itens "fora
  desta análise" na lista: fora da lista enxuta (ajustes do responsável de 19/10/2026).
- Lista vertical nos uploads e na "Seleção de referências".
- **Não são divergências da SPEC.** BR-POP-JUNHO-1 é regra autorizada da CAP-IND-02 (L1742), com
  DENOMINADOR_ALTERNATIVO; `brasil-cod-uf-prefix-1` é a correspondência autorizada para a soma por
  estado (CFG-TER L968; RQ-DAD-12 L1349), sempre SOMA_DOS_COMPONENTES (L1747, L1751); NIVEIS-BR-UF-MUN-1
  segue a RQ-DAD-30 (L1394).
- **Divergência da SPEC decidida pelo responsável (D4, ajuste de 2015).** A população parcial de 2015 não
  imputa nem estima ninguém, mas deixa o 430607 fora do denominador enquanto o numerador continua sendo a
  contagem nacional inteira. A SPEC pede, nesse caso, NAO_AVALIAVEL com DENOMINADOR_AUSENTE e não admite
  tratar a ausência por exclusão (CAP-IND-02 L1742; DA-10 L2838; INV-04 L292; AT-08 L2252), e a densidade
  parcial que ela autoriza exige numerador e denominador no mesmo suporte (CAP-AGR-01 L1751). Por decisão
  do responsável pelo produto, o Brasil de 2015 fica avaliável com limitações (`POPULACAO_NACIONAL_PARCIAL`),
  com a nota e a lista dos ausentes. A divergência está registrada no README e no
  [registro](REGISTRO_DE_COMPORTAMENTO.md); a SPEC não foi alterada.

## 9. Testes

- `backend/tests/test_territorial_levels.py` (CI, fontes sintéticas): contrato e erros, absorções,
  roteamento e paridade com os caminhos atuais, matriz das 12 análises, BR-POP-JUNHO-1 (inclusive
  junho parcial, ano sem junho e conflito), densidade do Brasil exata, estados e 251365, blocos sem
  soma, ranking e distribuição de estados, comparações por nível, evolução com INCOMPARABILIDADE e
  lacuna do Brasil, agregação, análises de distância, D5 (rotas antiga e nova, falha controlada),
  chaves, inspeção e pré-exame, conversa e privacidade do provedor, representação.
- `backend/tests/test_levels_real_data.py` (job `dados-reais`, sem pulos, com SHA-256 conferido antes
  e depois): as 22 densidades do Brasil contra a leitura independente (2,3638 em junho de 2024; 2015
  com 5.569 municípios e [430607]), a taxa nacional nas rotas antiga e nova, Σ estados = Σ municípios e
  Brasil sempre menor que a soma municipal, os seis agregados parciais, SP em 2015/1, PB em 2016/6,
  ranking dos estados, agregação de todos os municípios, 251365 na PB (223 municípios), análise
  espacial com todos os municípios e as âncoras da tendência (Brasil 22 e 11 observações em
  Crescimento; SP e RS não comparáveis na série completa; RS na série de junho); desde 19/10/2026, a comparação
  com a série anual de junho e valores em 06/2024 (Brasil, AM, SP, RS e três municípios do AM, conferida por leitura
  independente) e o resumo com a série nacional.
- `backend/tests/test_spatial_por_territorio.py` (CI): território com coordenada inválida, não numérica ou
  ausente não avaliável, referência inválida recusada, coordenadas que mudam entre competências e erro de
  formato. `test_territorial_levels.py` confere a escolha pendente no pré-exame. Com a base real
  (`test_real_data.py`), sem a camada os seis municípios ficam não avaliáveis e os demais têm as mesmas
  distâncias do subconjunto válido.
- Tela: `frontend/tests/territorialScope.test.mjs` (o que vale em cada análise, padrão, marcar e
  desmarcar, grupos, contagem, resumo, transferência e competências) e `representation.test.mjs` (taxa
  nacional só na densidade e nível dos itens); roteiro `backend/tests/ui_territorial_scope.py` nas suítes
  `bloco1` e `base-versionada` (lista, espacial com competência, Brasil + estado + município na densidade,
  taxa nacional na legenda e nas barras sem mudar o domínio, ranking só de estados, escolha pendente,
  "Limpar seleção", conversa que substitui a seleção pelos municípios sem receber a abrangência, nenhum
  `/api/inspect` ao trocar de análise, larguras de 390 e 768 px; na base versionada, 27 estados, o grupo de MG com 853
  municípios e "2,36 por 1.000 habitantes").
