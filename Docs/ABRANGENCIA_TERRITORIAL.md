# Abrangência territorial: Brasil, estados e municípios

> **Página única (22/10/2026).** A tela descrita nas seções 4.1 (a taxa nacional no mapa, nas barras e no
> cabeçalho do resultado), 6 (a lista vertical da caixa "Abrangência territorial") e 7 (a caixa Período e os
> motivos da análise espacial na tela) saiu do produto com as telas clássicas e fica como histórico, assim como o
> roteiro de navegador citado na seção 9. Continuam o motor e a API (`options.abrangencia`), com os testes do
> backend. Na página única, o gráfico começa pelos 27 estados e abre os municípios de um estado, sem somar níveis
> ([área de análise](PAINEL_INTEGRADO_INTERFACE.md)); a cobertura do roteiro que saiu está em [`backend/tests/legado/README.md`](../backend/tests/legado/README.md).

Decisões do responsável pelo produto de 19/10/2026: **D3** (abrangência vertical com Brasil, estados,
todos os municípios e municípios), **D4** (população do Brasil pela soma municipal de junho) e **D5**
(taxa nacional como referência de contexto na densidade). Na mesma data, o responsável pelo produto
entregou a contagem de médicos únicos por estado, que virou a fonte estadual da base
(`Dados_Estados_Brasil.csv`): desde então, o estado é essa contagem, e não mais a soma dos municípios.
Este documento descreve o motor e a API (`backend/territorial_levels.py`) e, como histórico, a tela das
telas clássicas: a lista vertical da caixa "Abrangência territorial" (§6) e a taxa nacional no mapa e nas
barras (§4.1). As mudanças estão no
[registro](REGISTRO_DE_COMPORTAMENTO.md).

## 1. Princípios

- Cada nível é um universo próprio, e **nenhum nível é somado a outro** (RQ-DAD-30). Não há linha de
  total entre níveis.
- **Brasil (BR):** contagem nacional de `Dados_Brasil.xlsx`. Nunca é a soma dos municípios.
- **Estado (UF):** contagem de médicos únicos da fonte estadual (regra `UF-CONTAGEM-ESTADUAL-1`):
  contagem distinta dentro da UF e da competência, em que quem atua em mais de um município do estado
  conta uma vez. Nunca é a soma dos municípios. A população do estado é a soma da população estimada dos
  seus municípios, pelo prefixo do código IBGE, na própria competência (regra `UF-POP-MUNICIPIOS-1`, com
  a correspondência `brasil-cod-uf-prefix-1`; a coluna `uf` da fonte municipal não é usada). Quem atua em
  mais de um estado conta em cada um: a soma dos estados não é o total do Brasil, e o estado nunca é
  comparado com o Brasil.
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
| Evolução temporal | sim | sim (densidade sem população completa é lacuna) | sim | uma série por objeto; painéis por nível | 1 objeto |
| Comparações | sim, lado a lado | sim | sim | relações só dentro do nível | 2 objetos |
| Distribuição, Recortes e rankings | não | sim, só entre estados | sim | mesmo nível | 2 |
| Agregações | não | sim, só entre estados (soma das contagens estaduais) | sim | mesmo nível, um resultado | 2 |
| Análise espacial, Referência mais próxima, Critérios combinados | não | não (o grupo de municípios vale) | sim | — | 1 |
| Rotatividade | indisponível na base Brasil | — | — | — | — |

Motivos devolvidos pelo backend (mesmo texto no erro 422 e no pré-exame):

| Análise | Brasil fora | Estado fora |
|---|---|---|
| Distribuição | "Não se aplica: a distribuição agrupa vários territórios, e o Brasil é um só." | — |
| Recortes e rankings | "Não se aplica: o ranking ordena vários territórios, e o Brasil é um só." | — |
| Agregações | "Não se aplica: o total do Brasil vem pronto da fonte nacional e não é somado a outros territórios." | — |
| Espacial, mais próxima, critérios | "Não se aplica: as distâncias e os critérios usam a localização de cada município." | "Não se aplica: estados não têm um ponto único. Para usar os municípios de um estado, marque o grupo em Municípios." |
| Rotatividade | "A rotatividade não está disponível nos dados do Brasil: falta um identificador da mesma pessoa entre os períodos." | (o mesmo) |

Estados e municípios juntos na distribuição, no ranking ou na agregação são uma escolha pendente ("Você
marcou estados e municípios. … usa territórios do mesmo tipo: escolha qual manter."); o mínimo também é
conferido no backend ("… precisa de pelo menos dois territórios do mesmo tipo. Marque mais um.";
"A agregação precisa de pelo menos dois estados." ou "… dois municípios."). Na agregação de estados, as
escolhas "unidades sem sobreposição" e "pessoas distintas" são recusadas: "A agregação de estados é
sempre a soma das contagens estaduais (possível dupla contagem): quem atua em mais de um estado conta
em cada um, e a base não identifica as pessoas entre os estados." (na base atual, a soma dos estados
supera o total do Brasil em todas as competências).

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
- O índice da fonte municipal (membros por estado, nomes, população de junho por ano, população de cada
  estado por competência e a soma das quantidades dos municípios de cada estado, só para conferir a fonte
  estadual) é calculado uma vez por versão da base, com trava, e nunca guardado nos atributos do quadro.

### 3.2 Estado

- **Contagem (UF-CONTAGEM-ESTADUAL-1):** a da fonte estadual `Dados_Estados_Brasil.csv`, por UF (a sigla,
  ligada ao código IBGE pela tabela do IBGE), competência e categoria, como está. Competência sem registro
  do estado na fonte estadual: "Não avaliável: sem registro nesta competência na fonte estadual", nunca
  zero. A fonte estadual não é um recorte do pedido (`scope=state` é recusado, e `available_scopes`
  continua nacional e municipal): ela só é lida pela abrangência. Com a fonte fora do perfil oficial (por
  exemplo, uma UF desconhecida), os estados ficam indisponíveis com o motivo ("Estados indisponíveis: a
  fonte estadual de médicos únicos precisa estar no perfil oficial da base Brasil. …"), e Brasil e
  municípios seguem. Um estado da lista sem registro na fonte estadual continua como grupo de municípios,
  mas não como estado.
- **População (UF-POP-MUNICIPIOS-1):** em cada competência, a soma da população estimada dos municípios
  do estado (prefixo do código IBGE), cada código uma vez, só com todos os municípios previstos
  registrados. Sem algum deles, a população não é estimada: a densidade do estado fica "Não avaliável:
  população estadual incompleta nesta competência (DENOMINADOR_AUSENTE)", a contagem continua avaliável
  e o resultado traz a nota "{Estado} em {competência}: população estadual incompleta, {k} de {N}
  municípios com registro na fonte municipal (sem registro: {códigos}); a população não é estimada e a
  densidade do estado não é avaliada.". Na base atual: RO, MG e SP em janeiro de 2015, SC em janeiro de
  2017 e RS em junho de 2015 e janeiro de 2020. População ausente, não positiva ou conflitante no mesmo
  município é erro, sem escolha arbitrária.
- **Densidade:** contagem estadual × 1.000 ÷ população do estado, em aritmética exata. São Paulo, junho
  de 2024: 148.909 ÷ 45.973.194 × 1.000 = **3,2390** por 1.000 habitantes.
- Rótulos: território "São Paulo (SP)", nível "Estado", tipo de contagem "Unidades distintas: contagem
  estadual (não é a soma dos municípios)", cobertura "População: 644 de 645 municípios; sem registro:
  353286" e "Competência da população" igual à competência.
- `metadata.populacao_estadual`: por estado e competência, `populacao`, `previstos`, `incluidos`,
  `ausentes`, `regra`, `avaliabilidade` e `motivo` (`DENOMINADOR_AUSENTE` quando incompleta).
- **Fontes que divergem:** a contagem distinta do estado não pode superar a soma das contagens dos seus
  municípios. Quando supera (com todos os municípios presentes), as duas fontes entram como estão e o
  resultado traz a nota "{Estado} em {competência}: a contagem estadual de médicos únicos ({q}) supera a
  soma das contagens dos seus municípios na fonte municipal ({s}); as duas fontes divergem nesta
  competência e entram como estão.". Na base atual, só o Distrito Federal, de janeiro de 2014 a junho de
  2017 (em janeiro de 2014, 7.832 contra 4.640).
- **Consistência na base atual:** em cada competência, Brasil ≤ soma dos estados ≤ soma dos municípios
  (junho de 2024: 502.495, 539.090 e 817.419).
- **251365:** PB pelo prefixo do código. Em 2016/6, a fonte declara PA na coluna `uf` (população
  331.942); a linha entra como está, com a nota `UF_DECLARADA_DIVERGENTE`: "Em {competência}, {n}
  registro(s) da fonte municipal trazem na coluna uf um estado diferente do indicado pelo código IBGE
  ({códigos}); o estado segue o código, e os valores entram como estão na fonte." Ela aparece na
  população do Brasil de 2016 (janeiro e junho), na população da PB em 2016/6 e nos municípios dessa
  competência. A constante `UF_DIVERGENTE_EXCLUI` (falsa) deixaria a linha fora das somas (a população
  da PB em 2016/6 ficaria incompleta). Nas bases importadas, a hierarquia divergente continua
  bloqueando a unidade.

### 3.3 Municípios

- Escolhas diretas (`ids`) continuam estritas: código inexistente ou sem registro no recorte é erro.
- Expansões ("Todos os municípios" e grupos por estado) viram os municípios **presentes** depois dos filtros de período e categoria; os ausentes ficam na nota de cobertura e em
  `metadata.selecao_territorial.expansoes` (previstos, incluídos e ausentes por competência).
- "Todos os municípios" sozinho sai sem `territory_ids`, com a nota de cobertura ("Todos os municípios:
  os 5.570 municípios previstos nesta versão da base têm registro no recorte escolhido." ou a lista dos
  ausentes por competência). Na agregação: "Soma dos 5.570 municípios (possível dupla contagem); não é
  o total do Brasil, que vem da contagem nacional."

### 3.4 Por análise na rota de níveis

- **Quantitativos, densidade e relatórios:** linhas por nível, na ordem Brasil → estados (por código)
  → municípios, com a coluna "Nível" e "Tipo de contagem". Competência pedida que não existe na fonte
  de um nível vira linha "Não avaliável: sem registro nesta competência na fonte
  {nacional|estadual|municipal}". Desde o visual completo (19/10/2026), as métricas são **por nível**, com a
  chave extra `nivel` (BR, UF ou MUN): "Brasil (total nacional): registros avaliáveis" e "…: registros não
  avaliáveis", "Estados: …" e "Municípios: …"; os números de níveis diferentes nunca são somados (antes,
  "Unidades avaliáveis" e "Não avaliáveis" contavam só os municípios). A descrição diz o que é cada bloco:
  "Densidade de pessoas por 1.000 habitantes por nível territorial (Brasil (total nacional), estados e
  municípios), em blocos separados; nenhum nível é somado a outro." e "Quantitativos de pessoas por nível
  territorial (…)" (antes, "pessoas por 1.000 habitantes.").
- **Evolução temporal:** uma única chamada de `evolution` para todos os objetos. O estado é a série da
  fonte estadual, sem composição que mude entre competências; na densidade, a competência em que a
  população do estado está incompleta é lacuna (fora das observações, nunca zero), e a mudança usa os
  extremos quando eles têm valor. Na base atual, a densidade de SP tem 21 observações na série completa
  (sem 2015/1) e a do RS, 20 (sem 2015/6 e 2020/1); na série anual de junho, o RS tem 10. A quantidade
  de cada estado tem as 22 competências (RS de 21.680 a 33.985, "Crescimento").
- **Comparações:** maior, menor, igual e diferença só entre objetos do mesmo nível, com o motor de
  sempre (par A/B ou três ou mais, AT-84). O Brasil e os objetos isolados ficam lado a lado: "Lado a
  lado: o Brasil é outro nível e não entra em maior, menor nem diferença com estados ou municípios.",
  "Lado a lado: único estado; não é comparado com municípios nem com o Brasil." e "Lado a lado: único
  município; não é comparado com outros níveis.". Estado sem valor na competência (sem registro na fonte
  estadual ou, na densidade, sem a população completa) fica fora da relação, com a condição. Métrica:
  "Territórios comparados".
- **Comparações com competência dos valores e janela (desde 19/10/2026, D6):** com `comparison_values_period`,
  as relações usam só essa competência, sempre dentro do mesmo nível (o Brasil lado a lado, sem relação; estado e
  município nunca relacionados), e `detail_rows` traz um registro por objeto, com o "Nível", quantidade, população,
  densidade, "Tipo de contagem", "Cobertura", "Competência da população" (Brasil na densidade), a condição e, com
  duas ou mais competências, a mudança e a tendência na janela. Estado sem valor na competência dos valores fica
  fora das relações, com a condição, e o registro dele guarda a contagem; na janela, a densidade sem população
  completa é lacuna (extremo vazio, nunca NaN nem zero). Municípios de `detail_rows` na
  ordem do código (RQ-REP-03). `metadata.comparacao.grupos` traz, por nível, o rótulo, o tipo de contagem, os
  objetos pedidos e se houve relação; `sem_relacao`, os objetos sem relação e o motivo. Métricas: "Territórios
  comparados" e "Competências na janela". Na série anual de junho com valores em 06/2024: Brasil 2,3638
  (Crescimento), SP 3,2390 (Crescimento), AM 1,3991 (Crescimento), RS com 10 observações (sem 06/2015) e Manaus,
  Tefé e Parintins sem classificação (mudança de direção); ver `Docs/EVOLUCAO_TEMPORAL_E_TENDENCIA.md`, seção 8.
- **Ranking e distribuição de estados:** universo "estados selecionados (contagem estadual de médicos
  únicos)"; estado sem valor (sem registro na fonte estadual ou, na densidade, sem a população completa)
  fica sem posição (ranking) ou fora das classes (distribuição, com a nota "Fora da distribuição: {Estado}
  em {competência} ({condição})."), e com menos de dois estados avaliáveis o pedido é recusado ("Menos de
  dois estados avaliáveis em …"). Métricas (19/10/2026): no ranking, "Territórios ordenados" e "Não
  avaliáveis"; na distribuição, "Unidades classificadas", "Classes" e "Estados fora da distribuição". Na
  base atual, a densidade de junho de 2024 ordena DF, SP e RS nas três primeiras posições e AM, PA e MA
  nas três últimas.
- **Agregação de estados:** universo "estados agregados (soma das contagens estaduais)". Numa competência
  e numa categoria, soma as contagens estaduais e as populações dos estados, pelo mesmo motor da agregação
  municipal: tipo "Soma dos componentes (possível dupla contagem)", limitação
  `SOMA_COM_POSSIVEL_DUPLA_CONTAGEM` e a nota "Agregação de estados: soma das contagens estaduais de médicos
  únicos (soma dos componentes). Quem atua em mais de um estado é contado em cada um; o total não é o
  número de médicos diferentes do conjunto nem o total do Brasil.". `metadata.suporte_agregado` registra,
  na competência, os estados previstos, os incluídos e os não avaliáveis com o motivo (CAP-AGR-01). Estado
  sem contagem ou sem a população completa na competência fica fora: o agregado é parcial sobre os
  avaliáveis, com numerador e denominador no mesmo suporte, a limitação `AGREGADO_PARCIAL` e a nota
  "Agregação parcial em {competência}: {k} de {n} estados com contagem e população; fora: {Estado}
  ({condição}). O valor não representa o conjunto dos estados marcados."; sem nenhum avaliável, não há
  resultado ("Nenhum estado marcado tem contagem e população em {competência}: …"). Na base atual, junho
  de 2024: Região Norte, 27.384 médicos e 18.669.345 habitantes; os 27 estados, 539.090 (acima dos 502.495
  do Brasil).
- **Notas de nível:** procedência do Brasil ("Brasil (total nacional): contagem nacional de médicos da
  base Brasil, não a soma dos municípios. População: soma das populações estimadas dos {N} municípios em
  junho de {Y}, usada também em janeiro de {Y} (regra BR-POP-JUNHO-1). Densidade = contagem ÷ população
  × 1.000."; numa série de vários anos, "dos {N} municípios em junho de cada ano" quando todos os anos somam
  o mesmo número de municípios e "dos municípios com registro em junho de cada ano" quando algum ano é
  parcial, como a série que inclui 2015); janeiro com o Brasil e outro nível ("Em janeiro, a população do Brasil é a de junho do
  mesmo ano; nos estados e municípios, é a da própria competência."); estados ("Estados: contagem de
  médicos únicos da fonte estadual. Quem atua em mais de um município do estado conta uma vez; quem atua
  em mais de um estado conta em cada um, e por isso a soma dos estados não é o total do Brasil."), com a
  população na densidade ("População dos estados: soma das populações estimadas dos seus municípios
  (código IBGE) na própria competência (regra UF-POP-MUNICIPIOS-1). …"), as lacunas e as divergências de
  §3.2; mais de um nível ("Brasil, estados e municípios aparecem em blocos separados; nenhum nível foi
  somado a outro.").
- **Avaliabilidade:** `metadata.evaluability.limitacoes` reúne `NIVEIS_TERRITORIAIS_DIFERENTES`,
  `DENOMINADOR_ALTERNATIVO`, `POPULACAO_NACIONAL_PARCIAL`, `SOMA_COM_POSSIVEL_DUPLA_CONTAGEM` e
  `AGREGADO_PARCIAL` (agregação de estados com algum de fora), quando cabem; linha não avaliável (estado sem população completa, por exemplo) deixa o resultado avaliável com
  limitações.

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

> Histórico: esta tela saiu do produto com as telas clássicas em 22/10/2026 (ver a nota no início do documento).

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
  (`level-panel-uf`, "· Estados", com o aviso `uf-warning` "Fonte estadual: médicos únicos de cada estado ·
  a soma dos estados não é o total do Brasil.") ficam em figuras separadas; nunca há barra do Brasil entre municípios. A série temporal com vários painéis
  (`serie.paineis`) desenha um gráfico por painel (`level-panel-{id}`).
- **Visual completo (19/10/2026):** o cabeçalho do resultado traz o cartão de contexto da taxa nacional (borda
  tracejada, selo "contexto", minigráfico da `serie`) ou, quando o Brasil é um bloco do resultado, o cartão do
  Brasil com o mesmo minigráfico; a dica do ponto no mapa e o detalhe do território mostram "Brasil (contexto)"
  ao lado do valor do município. Os cartões de destaque trazem o nível; o do estado traz o aviso "médicos
  únicos de cada estado · a soma dos estados não é o total do Brasil" e a mesma unidade dos demais
  (profissionais; por 1.000 habitantes na densidade). Desde a fonte estadual, o estado não tem textura
  listrada nem o aviso de possível dupla contagem: são unidades distintas no estado. Na aba Gráficos, o
  contêiner `levels-panel` reúne o bloco do Brasil (`level-panel-br`: valor, tipo de contagem e "Lado a lado:
  não entra em maior, menor nem diferença com estados ou municípios."), os estados (`level-panel-uf`, com o
  `uf-warning`, sem linha nacional) e os municípios (`level-panel-mun`, com a linha nacional e um separador por estado,
  `bar-group-separator`, lido de `universe.members[].state`, sem reordenar nem contar). Na comparação, um bloco por
  nível, cada um no seu eixo, e os halteres por nível (ver `Docs/BLOCO3_MAPAS_VISUALIZACOES.md`).

## 5. Contrato da API

### 5.1 Pedido (`/api/analyze` e `/api/preflight`, `dataset=brazil`)

```json
"abrangencia": {"brasil": true, "estados": ["13", "35"],
                "municipios": {"todos": false, "estados": ["15"], "ids": ["code:130260"]}}
```

- `estados` são objetos UF (fonte estadual); `municipios.estados` são grupos (expansão); `ids` no formato
  do catálogo. `scope` precisa ser `auto` ou `municipal`; `mapping` é o mapeamento municipal da inspeção.
- Erros (422): upload com abrangência ("A abrangência por Brasil e estados existe só na base Brasil
  oficial."); abrangência com `territory_ids` ("Use a abrangência territorial ou a lista de territórios,
  não as duas."); `scope=national` ("Com a abrangência territorial, o recorte é resolvido pela análise;
  envie scope=auto."); nada marcado ("Nenhum território marcado na abrangência."); estado fora da lista,
  sem municípios na base ou sem registro na fonte estadual ("Estado não reconhecido nesta base: {x}.");
  fonte estadual indisponível (o motivo de §3.2); identificadores repetidos ou acima dos limites; nível não
  aceito (o motivo do §2).
- Absorção explícita, listada em `metadata.selecao_territorial.absorvidos`: "Todos os municípios"
  absorve grupos e ids; um grupo absorve os ids dele. Estados nunca absorvem municípios: cada um é um
  nível.

### 5.2 Roteamento e resposta

| Abrangência | Rota | Quadro |
|---|---|---|
| só municípios | `municipal` | municipal, com `territory_ids` derivados (omitidos em "Todos os municípios") |
| só Brasil em quantitativos, ou na evolução e no relatório por quantidade | `nacional` | nacional |
| qualquer outra (inclusive estados, também na agregação) | `niveis` | as fontes do pedido (nacional, estadual e municipal), da mesma leitura verificada |

- `metadata.selecao_territorial`: `pedido`, `ids_canonicos` (`br`, `uf:35`, `mun:todos`, `mun:uf:35`,
  `code:…`), `absorvidos`, `rota` e `expansoes`.
- Na rota de níveis: `metadata.source.scope = "niveis"` com `fontes_usadas` (`national`, `state` e
  `municipal`; a municipal entra com municípios ou com a população dos estados na densidade);
  `universe.members` com `nivel` (BR, UF ou MUN), `state_rule` e `classification_scope` "universos
  separados por nível"; `metadata.populacao_nacional` (por competência do Brasil);
  `metadata.populacao_estadual` (por estado e competência, na densidade); `metadata.suporte_agregado` (na
  agregação de estados);
  `representacao.niveis` (coluna, ordem, tipos e "Município" no mapa) e `serie.paineis` (na quantidade,
  um painel por nível; na densidade, municípios com o Brasil como referência e estados à parte).
- O mapa desenha só municípios. Sem municípios: "Mapa não aplicável: Brasil e estados são agregados sem
  ponto; marque municípios para ver o mapa."

### 5.3 Inspeção, pré-exame e conversa

- `/api/inspect` da base oficial no recorte municipal devolve `niveis`: regras (`regra_estado`
  `UF-CONTAGEM-ESTADUAL-1`, `regra_populacao_estadual` `UF-POP-MUNICIPIOS-1`, `regra_membros_estado`
  `brasil-cod-uf-prefix-1` e `regra_populacao_nacional`), Brasil (períodos, competências com densidade não
  avaliável ou com limitações), `fonte_estadual` (`disponivel`, `motivo` e `periodos`), estados com sigla,
  nome, `rotulo_grupo` ("Municípios do Amazonas", "Municípios da Paraíba"), número de municípios e
  `objeto` (com registro na fonte estadual), total de municípios e a matriz por análise (`operacoes`, com
  `texto` e `motivos`; sem a fonte estadual, "estado" sai de `aceita` com o motivo). As listas de municípios continuam em
  `preflight.territory_choices`, agora com `state_code` e, no 251365, `hierarchy_note`.
- `/api/preflight` com abrangência segue o mesmo roteamento; na rota de níveis devolve o pré-exame da
  fonte municipal inteira mais `capabilities[op].niveis` (`brasil`, `estados`, `municipios` e, quando
  a seleção não cabe, `selecao`), com o pior estado das partes e os motivos prefixados ("Brasil: …").
  O pré-exame recebe a análise no campo `operation`.
- Escolha pendente na abrangência (estados e municípios juntos na distribuição, no ranking ou na
  agregação, ou territórios de menos): o `/api/preflight` não recusa o pedido; devolve o pré-exame da fonte municipal
  inteira com a análise em "escolha pendente" (`needs_confirmation`), o motivo em `reasons` e em
  `capabilities[op].niveis.selecao`, e `abrangencia_pendente` com o mesmo texto. O `/api/analyze`
  continua recusando (422) com esse texto.
- A conversa (`/api/exploration/interpret`, `/api/llm/interpret-context`) continua recebendo só ids de
  município; "municípios da Paraíba" inclui o 251365 (223 municípios na base atual). Desde a fonte
  estadual, a gramática local da base oficial também marca estados como objeto (campo `estados` da
  proposta, que substitui a seleção na tela): o nome do estado ("Quantos médicos havia em Minas Gerais em
  junho de 2024?"), "estado de São Paulo" e "estados da Região Norte" (Grandes Regiões pelo primeiro dígito
  do código IBGE, conferidas com a coluna `regiao_geografica` da fonte municipal); "municípios de Minas
  Gerais" continua marcando o grupo de municípios. O nome que é de estado e de município ("São Paulo",
  "Paraná") só vira o estado com "estado de" ou com a palavra "estado" no pedido; com preposição e sem
  essa indicação, a conversa pergunta ("“São Paulo” identifica um estado e também um município. Diga
  “estado de São Paulo” ou “município de São Paulo”."), com a análise pendente para a resposta; sem
  preposição ("Compare São Paulo e Campinas"), continua o município. "Pará" só é o estado com acento
  ("para" é preposição). Desde 21/10/2026, "últimos N anos" e "último ano" seguem a AT-34: com as mesmas
  competências contadas até o último período da base e até hoje, o período é aplicado e dito na resposta; com
  contagens diferentes, a conversa oferece as duas leituras, e os territórios já escolhidos continuam (a resposta diz
  quais). Anos ("em 2024") e intervalos ("entre 2014 e 2024") viram as competências da base
  nesses anos; numa análise de uma competência, com mais de uma no ano, a conversa pede a escolha
  ("Em 2024, a base tem 2 competências (janeiro de 2024 e junho de 2024). Esta análise usa uma competência:
  …"). "Mostre a evolução do número de médicos …" prepara a evolução por quantidade. Na referência mais
  próxima, um estado como alvo é explicado ("… estados não têm um ponto único. …"); para comparar estados,
  o pedido precisa citar dois ou mais (ou usar a abrangência). Nada é calculado na conversa.
  Abrangência, níveis, população nacional e taxa nacional nunca vão ao provedor de IA; desde 19/10/2026, nem
  o resumo do resultado, a comparação com janela (`metadata.comparacao`) ou a opção `comparison_values_period`.

### 5.4 Chave de execução

- `options` guarda a abrangência normalizada (listas ordenadas): a ordem do pedido não muda a chave.
- `metodos` entra só quando usado: `niveis` (`NIVEIS-BR-UF-MUN-1`), `populacao_nacional`
  (`BR-POP-JUNHO-1`), `estado` (`UF-CONTAGEM-ESTADUAL-1`, até 19/10/2026 `brasil-cod-uf-prefix-1`) e
  `populacao_estadual` (`UF-POP-MUNICIPIOS-1`, na densidade com estados), além de `tendencia` na evolução.
  Com a fonte estadual, mudaram de propósito as chaves e os valores dos resultados com estados.
- Mudam de propósito as chaves das densidades e dos relatórios com densidade da base oficial (D5) e as
  da rota de níveis. As demais chamadas antigas mantêm a chave.
- Desde 19/10/2026, a comparação com `comparison_values_period` tem chave própria (a opção entra em `options` e,
  com a janela, `metodos.tendencia`); a interface sempre envia a opção quando há competência escolhida, então as
  comparações feitas pela tela mudam de chave. A comparação sem a opção mantém a chave.

## 6. A lista vertical na tela

> Histórico: esta tela saiu do produto com as telas clássicas em 22/10/2026 (ver a nota no início do documento).

- Só na caixa **Abrangência territorial** da base oficial (`TerritorialScopeSelector.tsx`, região
  "Seleção territorial compartilhada"). Os uploads e a "Seleção de referências" continuam com a seleção
  por pesquisa (`TerritorialSelection.tsx`).
- A inspeção da base oficial é sempre municipal e traz o bloco `niveis`; trocar de análise não chama
  `/api/inspect` nem troca de fonte. A lista de municípios vem da inspeção (fonte municipal inteira),
  nunca do pré-exame de uma rota nacional.
- Seções, com caixas de marcar nativas (Tab entre os controles, Espaço marca, botão abre cada grupo):
  - **Brasil:** "Brasil (total nacional)", com a ajuda "Total da fonte nacional; não é a soma dos
    municípios.".
  - **Estados** (selo "médicos únicos"): o aviso "Cada estado conta os médicos diferentes do estado (fonte
    estadual): quem atua em mais de um município do estado conta uma vez. Quem atua em mais de um estado
    conta em cada um; por isso, a soma dos estados não é o total do Brasil. A população do estado é a soma
    dos seus municípios na competência.", "Todos os estados (N)" (tri-estado) e cada estado com registro
    na fonte estadual ("Amazonas (AM)", "população de 62 municípios"). Sem estados identificados pelos
    códigos (bases sintéticas), a seção informa "Nenhum estado identificado pelos códigos desta base.";
    sem a fonte estadual, a seção fica desabilitada com o motivo.
  - **Municípios:** "Todos os municípios" ("Um valor para cada um dos 5.570 municípios.") e, desde
    21/10/2026, o seletor nativo **"Estado dos municípios"** (`territory-municipal-state`; cada estado com "k de N
    marcados"). Escolhido o estado, a lista dele fica à vista, logo abaixo, com rolagem própria:
    - a caixa "Todos os N municípios de …" (`territory-group-check-NN`, rótulo acessível "Municípios do Amazonas (62)",
      tri-estado) e "k de N marcados";
    - os municípios ("MANAUS [130260]"; no 251365, a nota da UF declarada divergente).

    Sem estado escolhido, vale o do primeiro município marcado. A linha "Marcados em: AM (2) · PA (1)" leva a cada
    estado com municípios marcados. A seção Estados avisa que cada caixa marca o estado inteiro e que os municípios
    ficam na seção Municípios. Com "Todos os municípios" marcado, o seletor e a lista saem, e a seção diz como voltar a
    escolher municípios. Municípios sem estado identificado ficam numa lista simples. Antes, cada estado era um grupo
    recolhível no fim da lista, e os municípios só apareciam ao abrir o grupo.
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
  deixa a caixa em destaque, mostra "Ajuste a abrangência territorial para continuar." e retém o
  cálculo: desde 21/10/2026, o clique em "Calcular e mostrar resultado" diz "Falta escolher: Abrangência territorial." e abre
  a lista, sem calcular. Nada é calculado na tela. A rotatividade, indisponível na base Brasil, segue sem
  abrangência.
- A conversa continua recebendo só os municípios marcados (`territory_ids`). Um pedido explícito pelo
  país inteiro marca só o Brasil; "nos municípios", sem municípios marcados, marca "Todos os municípios";
  estados citados no pedido (§5.3) substituem a seleção pelos estados.
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

- Resolvido com a fonte estadual (19/10/2026): "estado de SP" (objeto) e "municípios de SP" (grupo) são
  pedidos diferentes na conversa (§5.3).
- Navegação avançada por teclado (foco único com setas, busca por letra), filtro de texto e itens "fora
  desta análise" na lista: fora da lista enxuta (ajustes do responsável de 19/10/2026).
- Lista vertical nos uploads e na "Seleção de referências".
- **Não são divergências da SPEC.** BR-POP-JUNHO-1 é regra autorizada da CAP-IND-02 (L1742), com
  DENOMINADOR_ALTERNATIVO; UF-CONTAGEM-ESTADUAL-1 usa a contagem de pessoas distintas no território vinda de
  fonte autorizada (QUANTITATIVO_ABSOLUTO pela CAP-IND-01, L959; RQ-DAD-12 L1349), entregue pelo responsável
  pelo produto; UF-POP-MUNICIPIOS-1 compõe o denominador do estado pela correspondência autorizada
  `brasil-cod-uf-prefix-1` (CFG-TER L968) e, sem a população completa, deixa a densidade NAO_AVALIAVEL com
  DENOMINADOR_AUSENTE, sem imputar nem excluir ninguém (CAP-IND-02 L1742; INV-04 L292; DA-10); a agregação de
  estados é sempre SOMA_DOS_COMPONENTES (CAP-AGR-01, L1747, L1751); NIVEIS-BR-UF-MUN-1 segue a RQ-DAD-30
  (L1394). A recusa de "unidades sem sobreposição" na agregação de estados aplica a regra metodológica do
  responsável pelo produto (a soma interestadual não autoriza afirmar pessoas únicas no conjunto) e a
  coerência exigida da premissa do usuário (DA-07): na base, a soma dos estados supera o total do Brasil em
  todas as competências.
- **Divergência da SPEC decidida pelo responsável (D4, ajuste de 2015).** A população parcial de 2015 não
  imputa nem estima ninguém, mas deixa o 430607 fora do denominador enquanto o numerador continua sendo a
  contagem nacional inteira. A SPEC pede, nesse caso, NAO_AVALIAVEL com DENOMINADOR_AUSENTE e não admite
  tratar a ausência por exclusão (CAP-IND-02 L1742; DA-10 L2838; INV-04 L292; AT-08 L2252), e a densidade
  parcial que ela autoriza exige numerador e denominador no mesmo suporte (CAP-AGR-01 L1751). Por decisão
  do responsável pelo produto, o Brasil de 2015 fica avaliável com limitações (`POPULACAO_NACIONAL_PARCIAL`),
  com a nota e a lista dos ausentes. A divergência está registrada no README e no
  [registro](REGISTRO_DE_COMPORTAMENTO.md); a SPEC não foi alterada.

## 9. Testes

- `backend/tests/test_territorial_levels.py` (CI, fontes sintéticas, com fonte estadual que conta menos
  que a soma dos municípios, uma UF sem uma competência e uma competência em que as fontes divergem):
  contrato e erros, absorções, roteamento e paridade com os caminhos atuais, matriz das 12 análises,
  BR-POP-JUNHO-1 (inclusive junho parcial, ano sem junho e conflito), densidade do Brasil exata, estados da
  fonte estadual com a população dos municípios (completa, incompleta e sem registro), divergência entre
  fontes e 251365, blocos sem soma, ranking e distribuição de estados, comparações por nível, evolução com
  lacunas, agregação de estados (soma dos componentes, recusas) e de municípios, análises de distância, D5
  (rotas antiga e nova, falha controlada), chaves, inspeção e pré-exame, fonte estadual sem uma UF ou fora
  do perfil, conversa (estados, regiões, anos) e privacidade do provedor, representação.
- `backend/tests/test_build_state_source.py` (CI): conversão da planilha sintética (formato, valores sem
  mudança, recusas sem gravar) e reprodução byte a byte do arquivo versionado, com o SHA-256 do manifesto.
- `backend/tests/test_levels_real_data.py` (job `dados-reais`, sem pulos, com SHA-256 conferido antes
  e depois): as 22 densidades do Brasil contra a leitura independente (2,3638 em junho de 2024; 2015
  com 5.569 municípios e [430607]), a taxa nacional nas rotas antiga e nova, as 594 contagens estaduais e as
  594 densidades dos estados contra a leitura independente (população dos municípios na competência; as seis
  lacunas; SP 3,2390 em junho de 2024; PB em 2016/6; as oito notas do DF), Brasil ≤ Σ estados ≤ Σ municípios
  em cada competência, ranking dos estados, agregação da Região Norte, dos 27 estados e de todos os
  municípios, 251365 na PB (223 municípios), análise espacial com todos os municípios, as âncoras da
  tendência (Brasil 22 e 11 observações em Crescimento; SP e RS com as lacunas de população), a comparação
  com a série anual de junho e valores em 06/2024 (Brasil, AM, SP, RS e três municípios do AM, conferida por
  leitura independente), o resumo com a série nacional, as regiões contra a coluna `regiao_geografica` e as
  quatro perguntas da conversa (Minas Gerais, São Paulo, Região Norte e Rio Grande do Sul), com o cálculo.
- `backend/tests/test_spatial_por_territorio.py` (CI): território com coordenada inválida, não numérica ou
  ausente não avaliável, referência inválida recusada, coordenadas que mudam entre competências e erro de
  formato. `test_territorial_levels.py` confere a escolha pendente no pré-exame. Com a base real
  (`test_real_data.py`), sem a camada os seis municípios ficam não avaliáveis e os demais têm as mesmas
  distâncias do subconjunto válido.
- Tela: `frontend/tests/territorialScope.test.mjs` (o que vale em cada análise, padrão, marcar e
  desmarcar, grupos, contagem, resumo, transferência e competências) e `representation.test.mjs` (taxa
  nacional só na densidade e nível dos itens); roteiro `backend/tests/ui_territorial_scope.py` nas suítes
  `bloco1` e `base-versionada` (lista com o aviso da fonte estadual, espacial com competência, Brasil +
  estado (30 médicos únicos no sintético; 148.909 em SP na base) + município na densidade,
  taxa nacional na legenda e nas barras sem mudar o domínio, ranking só de estados, escolha pendente,
  "Limpar seleção", conversa que substitui a seleção pelos municípios sem receber a abrangência, nenhum
  `/api/inspect` ao trocar de análise, larguras de 390 e 768 px; na base versionada, 27 estados, o grupo de MG com 853
  municípios e "2,36 por 1.000 habitantes").
