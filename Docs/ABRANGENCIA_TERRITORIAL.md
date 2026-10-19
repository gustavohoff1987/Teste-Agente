# Abrangência territorial: Brasil, estados e municípios

Decisões do responsável pelo produto de 19/10/2026: **D3** (abrangência vertical com Brasil, estados,
todos os municípios e municípios), **D4** (população do Brasil pela soma municipal de junho) e **D5**
(taxa nacional como referência de contexto na densidade). Este documento descreve o motor e a API
(`backend/territorial_levels.py`). A lista vertical na tela é a entrada seguinte do registro; até lá, a
interface continua enviando só municípios, e o comportamento visível muda apenas onde o
[registro](REGISTRO_DE_COMPORTAMENTO.md) indica.

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
  As métricas de avaliáveis continuam só sobre as linhas de municípios.
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
  relação: "Não avaliável: agregado parcial (…)".
- **Ranking e distribuição de estados:** universo "estados selecionados (soma dos municípios)"; estado
  parcial fica sem posição (ranking) ou fora das classes (distribuição, com nota), e com menos de dois
  estados avaliáveis o pedido é recusado ("Menos de dois estados avaliáveis em …"). Nota: "A dupla
  contagem varia entre os estados; a ordem e as classes podem refletir isso."
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
  ou na avaliabilidade do resultado municipal.

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
- A conversa (`/api/exploration/interpret`, `/api/llm/interpret-context`) continua recebendo só ids de
  município; "municípios da Paraíba" passa a incluir o 251365 (223 municípios na base atual).
  Abrangência, níveis, população nacional e taxa nacional nunca vão ao provedor de IA.

### 5.4 Chave de execução

- `options` guarda a abrangência normalizada (listas ordenadas): a ordem do pedido não muda a chave.
- `metodos` entra só quando usado: `niveis` (`NIVEIS-BR-UF-MUN-1`), `populacao_nacional`
  (`BR-POP-JUNHO-1`) e `estado` (`brasil-cod-uf-prefix-1`), além de `tendencia` na evolução.
- Mudam de propósito as chaves das densidades e dos relatórios com densidade da base oficial (D5) e as
  da rota de níveis. As demais chamadas antigas mantêm a chave.

## 6. Fora deste escopo e pontos residuais

- Lista vertical da abrangência na tela, taxa nacional no mapa e nas barras e análise espacial com
  escolha de competência: entrada seguinte do registro.
- "Estado de SP" (objeto) contra "municípios de SP" (grupo) na conversa: hoje os dois viram municípios.
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

## 7. Testes

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
  Crescimento; SP e RS não comparáveis na série completa; RS na série de junho).
