# Detector de Sinais Territoriais

Ferramenta do comando V22 (Eixo II, etapas 3 e 5: o núcleo, de 10/11/2026, e os comparativos, de 11/11/2026). A referência
metodológica é [Detector e Simulador V2.2](DETECTOR_E_SIMULADOR_V2_2.md) (seções 2.4, 4, 4.1, 4.2 e 5, com as decisões D-A a D-C de
10/11/2026), e o perfil da base está em [Perfil da base](PERFIL_DA_BASE_DETECTOR_SIMULADOR.md). Este documento descreve o que o
sistema faz hoje: os **12 fenômenos** do catálogo (os fenômenos 1 e 2 formam uma só escala, e por isso a tela lista 11 itens).

## O que é

O Detector mostra, para cada território da seleção em uso, a **situação mais recente da janela** e, à parte, o **histórico de
sinais**. Ele separa três coisas que não se confundem:

1. **fato observado:** a contagem e a mudança entre registros (por exemplo, "−3 médicos, −30%, de jan/2024 a jun/2024"). Sempre
   aparece;
2. **excepcionalidade:** se a mudança é incomum para municípios do mesmo porte, no mesmo tipo de intervalo (5 ou 7 meses), medida
   só com o que aconteceu antes da data avaliada;
3. **sinal analítico:** a **intensidade do sinal** (atenção, alta, crítica), por fenômeno, com **limites provisórios**.

A intensidade do sinal descreve o indicador. Não é juízo de desassistência, de suficiência do atendimento nem de prioridade de
provimento. Ela é uma **divergência aprovada da SPEC** (CFG-NOR, 4.4.19: nenhum critério normativo pré-configurado), válida só no
Detector (decisão D-A do responsável, 10/11/2026); fora dele, o assistente continua recusando "crítico" sem critério.

O Detector calcula no motor (`backend/detector.py` e, para os fenômenos 8 a 12, `backend/comparativos.py`, sobre
`backend/series_brasil.py`), sem o provedor de IA, e funciona com ele indisponível. Só existe na **base do Brasil** (médicos, registros de janeiro e junho de 2014 a 2024); com uma planilha enviada, o
botão fica desligado, com o motivo (em palavras que não usam o vocabulário da base brasileira, porque a planilha pode ser de
outro país: "funcionam só com a base de médicos que vem com o Agente").

## Na tela

- **Onde:** o botão **Detector de Sinais** (`analise-ferramenta-detector`), na linha "Ferramentas" da navegação principal, acima
  das abas. A ferramenta abre no lugar do painel da aba e do desenho da análise, que continuam como estavam ao voltar para uma aba
  (`area-de-analise` leva `data-ferramenta`). Ela usa a **seleção em uso**: os municípios, os estados como unidade e os conjuntos.
  Sem territórios, diz "Nenhum território selecionado" e não pede nada ao motor.
- **Aviso da data** (`detector-data`): "Registro mais recente da base: jun/2024. Os sinais descrevem a situação até jun/2024, não
  a de hoje."
- **Janela:** início e fim entre as competências reais da base (`detector-janela-inicio` e `detector-janela-fim`). A situação é a
  do fim da janela; o histórico e a série de junho começam no início dela. Para um município com quebra de fonte, os indicadores
  começam depois da quebra.
- **Gráfico e mapa** (`detector-visual`, acima da tabela; pedido do responsável em 10/11/2026: os fenômenos 8 a 12 também em
  gráfico ou mapa, com os componentes que o Agente já tem, e a tabela como detalhe). Três vistas:
  - **Distância e taxa (bolhas)** (`detector-bolhas`, a vista inicial): o gráfico de bolhas do Agente, com uma bolha por
    território à vista que tem distância a mostrar. Na horizontal, a distância em linha reta até o município mais próximo que
    atende ao critério (fenômeno 11); na vertical, a taxa de médicos por 1.000 habitantes (fenômeno 8); o tamanho mostra a
    população; a linha tracejada é a taxa do critério. Tocar numa bolha abre os detalhes do território;
  - **Mapa dos sinais** (`detector-mapa`): o mapa de pontos da Seleção. Em destaque, os municípios com o fenômeno escolhido no
    filtro "Fenômeno" (sem filtro, os que têm sinais combinados); os conjuntos, pelo contorno dos componentes; vazados, os
    municípios de referência do contexto geográfico. Só entram as coordenadas que o motor mandou; o estado como unidade não tem
    ponto;
  - **Só a tabela.**

  Junto delas, a nota `detector-comparacao` diz a janela da comparação relativa e se ela é habilitada (ver "População
  comparável", abaixo) e o critério do contexto geográfico (a taxa mínima e quantos municípios do país a atendem).
- **Tabela** (`detector-tabela`, 50 linhas por página, `detector-linha`), com nove colunas: território; condição estrutural;
  trajetória; ritmo e instabilidade; **comparação relativa** (fenômenos 8, 9 e 10: a taxa por 1.000 habitantes, o percentil e o
  índice ante a referência, com a variação em 2 anos quando a comparação é habilitada); **contexto geográfico** (fenômeno 11; o
  cabeçalho, em `detector-criterio-do-contexto`, e a célula dizem o critério por extenso: "município mais próximo com 2,36 médicos
  por 1.000 habitantes ou mais" e "mais longe que 99% dos municípios abaixo de 2,36 médicos por 1.000 habitantes");
  **sinais combinados** (fenômeno 12); qualidade do registro; última observação. A intensidade aparece com o nome por extenso
  (`detector-intensidade`: Atenção, Alta, Crítica), nunca só pela cor. Na comparação relativa não há intensidade: a tabela diz
  "sinal forte", "sinal muito forte" ou "queda de posição", e a legenda explica que são sinais observados em 2 anos, com limites
  provisórios.
- **Filtros:** por fenômeno (poucos médicos; nenhum médico registrado; perda no último registro; perda com alerta; abaixo do
  patamar anterior; declínio em junhos seguidos; desaceleração do crescimento; registro a verificar ou com descontinuidade; queda
  da taxa por habitante; queda da posição relativa; defasagem ante a referência; sinais combinados), por porte (os médicos do
  último registro) e pelo nome; a ordem é por intensidade (só ordena a lista: não há índice geral), por nome ou por número de
  médicos. O gráfico e o mapa acompanham os filtros.
- **Detalhes** (a seta de cada linha, `detector-detalhe`): a série observada, só com os registros reais e as marcas de registro;
  a **série da taxa** por 1.000 habitantes (`detector-serie-da-taxa`, a Série temporal do Agente), com a taxa da referência do
  território tracejada; os 12 fenômenos (11 itens), cada um com sete campos — **o que foi observado**, **qual critério**,
  **quanto difere do habitual**, **o que significa**, **o que não significa**, **limitações do dado** e **qualidade do
  registro** —; e o **histórico de sinais** (`detector-historico`), em que cada data é avaliada só com o que era conhecido nela
  (o histórico cobre o núcleo, os fenômenos 1 a 7).
- **Ligação com o Simulador de Cenários** (nos detalhes de cada território):
  - **"Abrir no Simulador"** (`detector-abrir-no-simulador`) abre o [Simulador](SIMULADOR_DE_CENARIOS.md) só com aquele
    território na seleção local dele, com o contexto analítico: a data avaliada, os sinais à vista e, quando a pessoa escolheu
    uma janela no Detector, essa janela (a janela padrão do Detector, a série inteira, não é levada). A seleção principal não muda;
  - **"Simular recuperação"** (`detector-simular-recuperacao`; decisão D-B de 10/11/2026) só aparece para o território que está
    **abaixo do patamar anterior** (fenômeno 7). Abre o Simulador com uma **meta hipotética**, que a pessoa pode trocar: voltar
    ao patamar de X médicos. O resultado é um cenário e uma conta condicional, nunca uma recomendação.
- **Parâmetros** (`detector-parametros`): os limites da escala estrutural, da perda entre registros, do patamar, do declínio, da
  taxa por habitante, da posição relativa e da defasagem, e o critério do contexto geográfico (em % da taxa do Brasil) podem ser
  trocados. Qualquer valor diferente do padrão vira uma **configuração personalizada — exploratória** (`detector-exploratorio`),
  com "Voltar aos padrões"; os padrões nunca são trocados em silêncio.
- **Como foi calculado** (`detector-metodo`): as notas e, para a data avaliada, a partir de que queda (e de que afastamento do
  patamar) a variação é incomum, por porte.
- **Exportações:** a tabela em CSV (uma linha por território, com a janela, a versão da base e do método e a configuração em
  cada linha; desde a etapa 5, também a janela de comparação e o estado dela, a taxa, a população, o percentil, o índice, as
  variações em 2 anos, o estado e o sinal de cada indicador, a distância e o município do contexto geográfico, o critério e os
  sinais combinados) e o método em JSON (a fonte, a janela, os parâmetros padrão e em uso, a comparação da data, a comparação
  relativa e as notas).

**Linguagem simples (decisão D-C).** A tela diz "sem classificação", com o motivo ("poucos municípios parecidos na base para
dizer se esta queda é incomum"), no lugar de "não calibrado"; "limites provisórios", no lugar de "candidatos"; "incomum" e
"muito incomum", no lugar de "cauda de 1%" e "de 0,1%". Os termos técnicos ficam em "Qual critério", em "Como foi calculado" e
nas exportações. Dois textos da conferência de 10/11/2026 (pausa 2):

- no afastamento de patamar com intensidade alta, quando o afastamento também chega ao limite da crítica mas a base não permite
  avaliá-la, a linha da tabela diz "**crítica: sem base para avaliar**" (antes, "sem base para dizer se é muito incomum", que
  parecia contradizer a intensidade alta); o detalhe explica o porquê;
- no fenômeno 4 (desaceleração do crescimento), a situação diz "**Não se aplica: a série está em declínio**" ou "Não se aplica:
  a série não tem classificação de tendência" (antes, "Sem desaceleração do crescimento (declínio)"); em crescimento sem a
  classe, "Sem desaceleração: a série está em crescimento" ou "Sem desaceleração: o crescimento está acelerando".

## O que é calculado

Os números entre parênteses são os dos fenômenos do catálogo. Os limites são **provisórios** (candidatos da V2.2).

| Dimensão | Fenômeno | Regra | Resultado |
|---|---|---|---|
| Condição estrutural | Dependência de poucos médicos e ausência de médicos registrados (1–2) | Nenhum (zero confirmado) ou 1 médico: crítica; 2 ou 3: alta; 4 ou 5: atenção; 6 ou mais: sem sinal por esta escala. Vale a mais grave das duas últimas observações válidas. Impacto da saída de um médico: 100/N (com zero, não calculável). Duração do zero em registros e meses | Intensidade (convenção), com o número de médicos |
| Trajetória | Declínio persistente (3) | Série de junho, reduções em anos seguidos, perda desde o primeiro valor da sequência: 2 reduções e 10% ou mais (forte); 3 e 20% ou mais (muito forte) | Sinal observado, sem intensidade |
| Trajetória | Perda abrupta (6) | A perda entre dois registros sempre aparece. Alerta só com **magnitude** (alta: ≥ máx(2; ⌈0,2·N⌉) médicos; crítica: ≥ máx(3; ⌈0,3·N⌉)) **e excepcionalidade** (P(X ≤ x) ≤ 1% ou 0,1% entre as transições anteriores da célula porte × intervalo, contando empates; mínimo de 100 ou 1.000 transições) | Fato; alerta de intensidade alta ou crítica; ou sem classificação, com o motivo |
| Trajetória | Afastamento de patamar anterior (7) | Patamar: a maior média dos 4 registros de dois anos civis completos, em blocos que terminam antes dos 4 últimos registros. Os 2 últimos registros ≤ 85% do patamar: atenção. Com afastamento na cauda de 1% da faixa de porte do patamar: alta. Crítica (4 últimos ≤ 70% e cauda de 0,1%): não calibrável na base atual. Patamar abaixo de 20 médicos: descritivo | Atenção ou alta; descritivo; sem sinal |
| Ritmo e instabilidade | Desaceleração do crescimento (4) | A classe da Análise de Tendência (CAP-TEN-01, `trend.classify_pairs`) nos 4 junhos até o junho avaliado, com o número de médicos; atualizada só em junho. A repetição da classe um ano antes é exploratória | Sinal descritivo, sem intensidade |
| Ritmo e instabilidade | Instabilidade temporal (5) | Desvio-padrão das variações de 7 registros ÷ c·N̄^(θ/2), com θ = 1,35 e c por tipo de intervalo (só com transições anteriores); não calculável com média abaixo de 6 | Índice descritivo (1 = a oscilação típica do porte) |
| Comparação relativa | Deterioração da disponibilidade relativa (8) | Taxa = médicos ÷ população estimada da mesma competência × 1.000 (estado: a contagem estadual ÷ a soma das populações municipais; conjunto: a soma das contagens ÷ a soma das populações, nunca a média das taxas). Variação da taxa de junho a junho em 2 anos, com a decomposição (médicos, população e taxa). Queda de 10% ou mais: forte; de 20% ou mais: muito forte | O nível da data; sinal observado, sem intensidade; descritivo com menos de 20 médicos no início da janela |
| Comparação relativa | Deterioração da posição relativa (9) | Percentil pela taxa = (posto médio − 0,5) ÷ n × 100, com os empates no posto médio, no universo fixo dos municípios do Brasil com taxa válida nas duas datas da janela (para estados como unidade, o universo dos estados). Queda de 10 pontos ou mais: queda de posição; de 15 ou mais, terminando até o percentil 50: forte; de 25 ou mais, terminando até o percentil 25 e repetida na janela encerrada um ano antes: muito forte | O percentil da data; sinal observado; descritivo abaixo de 20 médicos; não se aplica a conjuntos |
| Comparação relativa | Ampliação da defasagem ante referência (10) | Índice = 100 × taxa do território ÷ taxa da referência, com a referência na mesma unidade do território e sem ele: município, os demais municípios da UF (soma municipal; o rótulo traz o estado com a preposição certa e um só par de parênteses, como "demais municípios do Amazonas (soma municipal)"); estado, os demais estados; conjunto, os demais territórios das mesmas UFs. Queda de 15 pontos ou mais com o índice final abaixo de 80: forte; de 25 ou mais com o final abaixo de 60: muito forte | O índice da data; sinal observado; descritivo abaixo de 20 médicos; referência inválida quando não há outros territórios na unidade (Brasília) |
| Contexto geográfico | Distância geográfica a territórios com maior disponibilidade de médicos (11) | Distância geodésica (SIRGAS 2000), pelas coordenadas da competência avaliada, até o município mais próximo com taxa igual ou maior que o critério (padrão: a taxa do Brasil na data; editável, em % dela). O percentil compara a distância com a dos municípios que não atendem ao critério. Num conjunto, vale o componente mais próximo | Só contexto: sem intensidade e sem sinal. "Atende ao critério", "sem coordenada válida" ou "não se aplica" (estado como unidade) |
| Coexistência | Coexistência de sinais (12) | Quatro combinações pré-definidas: poucos médicos (intensidade alta ou crítica) e perda no último registro; poucos médicos e declínio persistente; declínio persistente e queda da disponibilidade ou da posição relativa; abaixo do patamar anterior e poucos médicos. As repercussões de uma mesma queda (perda, declínio, patamar e os três indicadores relativos) contam como **um evento**, não como evidências independentes | As combinações presentes e as frentes de sinal. **Sem soma de pontos e sem índice geral** |

**População comparável (fenômenos 8, 9 e 10).** A variação em 2 anos só é calculada quando a janela de comparação (de junho a
junho, atualizada só em junho) cabe inteira num **trecho de população comparável**. Desde 13/11/2026 (comando V23), os trechos
vêm da própria base (`comparativos.populacao_comparavel`), e não de anos fixos. Em cada passagem de ano, de um junho ao
seguinte, a base inteira é olhada:

- **população repetida:** metade da base ou mais repete o valor do ano anterior, e isso não é o comum nas outras passagens;
- **salto:** 5% da base ou mais (e pelo menos 3 territórios) varia mais de 5%, e isso é 3 vezes ou mais o comum nas outras
  passagens.

Nos dois casos, o trecho termina ali. Alguns territórios parados ou com salto são normais e não desligam a comparação; uma base
com a população constante em todos os anos é um trecho só (a taxa varia só com a contagem). Com a população do Ministério da
Saúde, em uso desde 13/11/2026, **a base inteira é um trecho só (2014–2024)**: toda data com o junho de dois anos antes tem a
comparação, inclusive o último registro (jun/2024, com a janela de jun/2022 a jun/2024). Com a população anterior, a mesma
leitura dava 2014–2017 e 2018–2021 (ela saltava em 2018, repetia-se em 2022 e 2023 e mudava de base em 2024). Quando a janela
não cabe num trecho, o estado é **"comparação não habilitada"**, com o motivo lido da base (por exemplo, "a população de 2024
muda de patamar em boa parte da base"), e o nível da data (a taxa, o percentil e o índice) continua à vista. Sem o junho de
dois anos antes, "janela insuficiente". Para o fenômeno 10, aplicar a mesma regra é uma decisão conservadora desta
implementação: o índice usa as duas populações, e uma troca de série o mudaria sem mudança real. A resposta da rota traz os
trechos em `comparacao.trechos` e o motivo em `comparacao.motivo`.

**Sem intensidade (decisão D-A).** As convenções do anexo para os fenômenos 8, 9 e 10 não foram validadas. Elas entram como
**limites provisórios** de um **sinal observado** (forte, muito forte, queda de posição), como no declínio persistente, e nunca
como atenção, alta ou crítica; o campo "quanto difere do habitual" diz "Sem classificação de intensidade". O caso exato no limite
conta (uma queda de exatamente 20% é muito forte): as comparações têm tolerância numérica explícita. O fenômeno 11 é só contexto,
e o 12 não tem intensidade nem pontuação.

**Qualidade do registro** (seção 2.4 do anexo):

- **descontinuidade de registro — pico que volta:** salto de 10 ou mais médicos que ao menos dobra a contagem e volta, em até dois
  registros, a até 125% do valor anterior. Até a volta ser observada, o salto leva "verificar registro". A volta não gera alerta, o
  trecho sai da comparação com territórios parecidos, e o registro do pico fica fora do patamar, da série de junho e da
  instabilidade;
- **descontinuidade de registro — quebra de fonte:** a soma municipal da UF abaixo da contagem estadual de médicos únicos, nas
  competências em que todos os municípios da UF têm registro (na base, só o Distrito Federal, de jan/2014 a jun/2017). O trecho
  sai da comparação, e a janela do município começa depois dele. O registro que sai da quebra (Brasília, 4.070 → 8.851 em
  jan/2018) faz parte dela: na série, não leva "verificar registro", e a transição não é perda nem ganho a classificar;
- **verificar registro:** o salto sem volta observada e a queda de 10 ou mais médicos que leva a contagem à metade ou menos. A
  queda grande que persiste **continua alertável**.

**Estados que nunca viram "sem sinal" em silêncio:** valor observado; zero confirmado; ausência de dado (o registro que falta não
é zero); não calculável; janela insuficiente; descontinuidade de registro; e sem classificação por falta de comparação (com o
motivo). Nos fenômenos 8 a 12, somam-se: comparação não habilitada; descritivo (menos de 20 médicos no início da janela);
referência inválida; não se aplica; sem coordenada válida; e atende ao critério.

**Níveis.** A comparação com territórios parecidos é municipal. Para estados como unidade (a contagem estadual de médicos únicos)
e para conjuntos (a soma das contagens dos componentes, que só existe quando todos têm registro na competência), o Detector
mostra os fatos e os indicadores descritivos, sem intensidade. Nos fenômenos 8 e 10, estados e conjuntos têm a taxa e o índice,
com a agregação rotulada; no 9, o estado tem a posição entre os estados, e o conjunto não entra em universos de percentis; no 11,
o estado não tem ponto único, e o conjunto vale pelo componente mais próximo. O Brasil não é uma unidade do Detector (no
Simulador, é).

## Rota

`POST /api/detector` (formulário, como `/api/painel`): `dataset=brazil`, `dataset_version` e `options` (JSON). Só lê e calcula:
nada é registrado na sessão, e nada vai ao provedor de IA. Conta nas vagas das operações pesadas (`carga.PESADAS`).

| Opção | Conteúdo |
|---|---|
| `base` | `{"municipios": {"todos", "estados", "ids"}}`, como no painel |
| `estados_unidade` | os estados como unidade (prefixos IBGE) |
| `conjuntos` | `[{"id", "rotulo", "membros", "versao"?}]`; membros do mesmo nível (`code:<IBGE>` ou `uf:<prefixo>`) |
| `janela` | `{"inicio", "fim"}`, competências da base; sem ela, a série inteira |
| `parametros` | os limites personalizados (`estrutural`, `perda`, `patamar`, `declinio`, `disponibilidade`, `posicao`, `defasagem` e `contexto.taxa_do_brasil_pct`); a resposta vem com `exploratorio: true` |
| `detalhe` | o id de um território da seleção: a resposta traz `territorio`, `serie`, `historico`, `comparativo`, `coordenadas` e `fenomenos`, no lugar da tabela |

A tabela responde com `versao`, `fonte`, `janela`, `competencias`, `parametros` (`padrao`, `em_uso`, `personalizados`,
`editaveis`), `linhas`, `resumo`, `calibracao` (por porte, as transições anteriores e a queda a partir da qual a variação é
incomum; no patamar, o afastamento; e o monitoramento da data), `notas` e `limitacoes`. Desde a etapa 5 (versão
`DETECTOR-SINAIS/V2.2/2`), também:

- `comparacao`: a janela da comparação relativa (`de`, `ate`), o `estado` dela (`comparavel`, `comparacao_nao_habilitada` ou
  `janela_insuficiente`), os `trechos` com população comparável, o mínimo de médicos e o critério do contexto geográfico
  (`taxa_minima`, `taxa_do_brasil`, `pct_da_taxa_do_brasil`, quantos municípios `atendem` e o `universo` das distâncias);
- em cada linha, `disponibilidade` (`estado`, `taxa`, `populacao`, `variacao_pct`, `sinal`), `posicao` (`percentil`, `universo`,
  `variacao_pp`), `defasagem` (`indice`, `variacao_pontos`), `contexto` (`distancia_km`, `referencia`, `referencia_id`,
  `percentil`) e `coexistencia` (`combinacoes`, `textos`, `repercussoes`); num conjunto, `ids_dos_membros`; `dimensoes` ganha
  `comparacao` e `contexto`, sempre nulas (não há intensidade);
- `coordenadas`: `{id: [latitude, longitude]}` dos municípios da seleção (e dos componentes dos conjuntos) e dos municípios de
  referência do contexto geográfico, na competência avaliada. Sem coordenada válida, sem ponto;
- no detalhe, `comparativo`: por competência, a `taxa` do território, a da `referencia` (com o rótulo) e o `indice`.

A limitação `COMPARACAO_SO_COM_POPULACAO_COMPARAVEL` acompanha toda resposta. Erros de pedido vêm em 422, com o texto em português
(seleção vazia, território fora da base, competência fora da base, parâmetro fora do intervalo, planilha enviada).

A seleção segue o contrato compartilhado das ferramentas (`series_brasil.selecao`): o estado como unidade (ou num conjunto de
estados) e os municípios dele não entram juntos (RQ-DAD-30); um conjunto reúne territórios do mesmo nível.

## Calibração

Estudo de 10/11/2026 com a base versionada (`scripts/calibrar_detector.py`, somente leitura; versão da base `c4d82eeee4e4`,
método `DETECTOR-SINAIS/V2.2/1`). Tudo respeita as origens móveis: cada data é avaliada só com as transições anteriores a ela.

**Células da perda abrupta em jun/2024** (intervalo de 5 meses):

| Médicos antes | Transições anteriores | Queda incomum (1%) a partir de | Queda muito incomum (0,1%) a partir de |
|---|---:|---:|---:|
| 1 a 3 | 6.572 | 66,7% | — |
| 4 a 9 | 16.650 | 44,4% | 77,8% |
| 10 a 19 | 12.035 | 36,8% | 58,8% |
| 20 a 49 | 9.958 | 31,2% | 56,4% |
| 50 a 99 | 3.969 | 29,4% | 64,8% |
| 100 a 299 | 3.708 | 26,3% | 52,4% |
| 300 ou mais | 2.765 | 15,6% | 44,4% |

Todas as células têm o mínimo para os dois limites em jun/2024. Nas duas primeiras datas da base (jun/2014 e jan/2015), não há
transições anteriores do mesmo tipo de intervalo: sem classificação. Na faixa de 1 a 3 médicos, nenhuma queda cabe na cauda de
0,1% (a maior queda possível é comum demais), e a magnitude mínima de 2 médicos quase nunca é alcançada: ali, quem informa é a
escala estrutural.

**Afastamento de patamar em jun/2024** (cauda de 1% por faixa do patamar): 20 a 49 médicos, 13.942 avaliações anteriores, incomum
a partir de 39,5%; 50 a 99, 5.321 e 38,3%; 100 a 299, 5.109 e 31,9%; 300 ou mais, 3.668 e 19,4%. Municípios classificáveis
(patamar de 20 médicos ou mais): 2.312; com atenção, 104; com alta, 32. A crítica é não calibrável (23 municípios cumprem a
condição de magnitude).

**Monitoramento (dado real).** A taxa de transições na cauda de 1%, por data, vai de 0,48% (jun/2024) a 1,44% (jun/2017): perto
da meta por construção, e por isso não mede acerto. Em jun/2024: 27 transições na cauda, 24 alertas de intensidade alta e 3 de
crítica; 1.153 municípios com perda no último registro (o fato, à vista em todos).

**Modelo nulo sintético** (seção 4.2 do anexo: N(t+1) = N(t)·(1 + g) + ε, Var(ε) = φ·N^θ, inteiros não negativos; g = 2,69% em 5
meses e 3,53% em 7; φ = 0,0982 e 0,1142; θ = 1,35; 5 repetições, semente 20261110):

| Médicos antes | Falso alerta (alta) | Falso alerta (crítica) | Queda de 20% não detectada | Queda de 30% não detectada | Queda de 50% não detectada |
|---|---:|---:|---:|---:|---:|
| 1 a 3 | 0,02% | 0,000% | 100,0% | 100,0% | 100,0% |
| 4 a 9 | 0,72% | 0,056% | 92,1% | 86,4% | 20,1% |
| 10 a 19 | 0,76% | 0,103% | 87,4% | 57,5% | 0,5% |
| 20 a 49 | 0,89% | 0,096% | 70,0% | 19,6% | 0,0% |
| 50 a 99 | 0,30% | 0,002% | 63,6% | 6,8% | 0,0% |
| 100 a 299 | 0,04% | 0,000% | 67,6% | 2,2% | 0,0% |
| 300 ou mais | 0,00% | 0,000% | 78,1% | 0,3% | 0,0% |
| Todos | 0,55% | 0,055% | 80,4% | 43,8% | 14,9% |

Leitura: sem nenhuma queda real, 0,60% das avaliações recebem algum alerta (abaixo da meta de 1%, porque a magnitude também é
exigida). A regra detecta bem quedas de 30% ou mais a partir de 20 médicos e quedas de 50% a partir de 10; não detecta quedas de
20% (pelo desenho: a magnitude da alta começa em 20%, e a variação precisa ser incomum) nem perdas em municípios com até 3 médicos.
Esses números valem para o modelo nulo, com os parâmetros estimados na base; não são uma taxa de acerto em dado real.

**O que continua provisório:** os limites da escala estrutural e do declínio (convenções); as metas de 1% e 0,1%; o corte de 20
médicos e os 15% do patamar; o critério do pico que volta; θ e a forma da instabilidade. A desaceleração repetida segue
exploratória (na base, 182 municípios com a classe em jun/2024, 16 com repetição).

### Fotografia dos fenômenos 8 a 11 (13/11/2026, com a população nova)

`scripts/calibrar_detector.py --so-comparativos` (somente leitura; versão da base `faa54169c5b6`, método
`DETECTOR-SINAIS/V2.2/2`), nas nove datas de junho em que a comparação de 2 anos é habilitada (todas as que têm o junho de dois
anos antes). É uma fotografia da **sensibilidade** dos limites provisórios, não uma validação: não há taxa de acerto, e nenhum
desses indicadores tem intensidade. A fotografia de 11/11/2026, com a população anterior, só tinha quatro datas (jun/2016,
jun/2017, jun/2020 e jun/2021).

| Data | Janela | Avaliados (20 médicos ou mais no início) | Só descritivos | 8: forte | 8: muito forte | 9: queda de posição | 9: forte | 9: muito forte (confirmada) | 10: forte | 10: muito forte | Com sinais combinados (12) |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| jun/2016 | jun/2014 a jun/2016 | 1.863 | 3.704 | 214 | 174 | 110 | 53 | 0 | 114 | 43 | 353 |
| jun/2017 | jun/2015 a jun/2017 | 1.876 | 3.691 | 211 | 150 | 136 | 61 | 0 | 143 | 26 | 653 |
| jun/2018 | jun/2016 a jun/2018 | 1.872 | 3.694 | 143 | 112 | 137 | 66 | 0 | 119 | 24 | 606 |
| jun/2019 | jun/2017 a jun/2019 | 1.892 | 3.674 | 187 | 112 | 140 | 62 | 0 | 142 | 28 | 726 |
| jun/2020 | jun/2018 a jun/2020 | 1.978 | 3.592 | 153 | 107 | 132 | 62 | 1 | 117 | 19 | 646 |
| jun/2021 | jun/2019 a jun/2021 | 2.013 | 3.554 | 113 | 71 | 153 | 69 | 1 | 84 | 24 | 565 |
| jun/2022 | jun/2020 a jun/2022 | 2.108 | 3.459 | 103 | 89 | 203 | 89 | 1 | 125 | 22 | 482 |
| jun/2023 | jun/2021 a jun/2023 | 2.203 | 3.366 | 125 | 99 | 223 | 100 | 1 | 121 | 32 | 448 |
| jun/2024 | jun/2022 a jun/2024 | 2.408 | 3.162 | 135 | 109 | 237 | 121 | 0 | 136 | 38 | 363 |

Leitura: de 57% a 67% dos municípios têm menos de 20 médicos no início da janela e ficam só descritivos. Entre os avaliados, de
9% a 21% têm queda da taxa de 10% ou mais em 2 anos, uma parcela alta para um "sinal": o limite de 10% é pouco seletivo e segue
provisório. A queda de posição muito forte quase nunca se confirma em duas avaliações anuais seguidas (no máximo 1 caso por
data). Em jun/2024, com a comparação habilitada, há 244 municípios com queda da taxa, 358 com queda de posição e 174 com
defasagem ante a referência (Brasília fica com referência inválida no fenômeno 10), e os sinais combinados somam 363.

**Contexto geográfico em cada junho** (critério: a taxa do Brasil na data):

| Data | Taxa do Brasil (por 1.000) | Municípios que atendem | Municípios com distância | Distância mediana (km) | Percentil 90 (km) | Maior (km) |
|---|---:|---:|---:|---:|---:|---:|
| jun/2014 | 1,60 | 1.565 | 4.000 | 32,5 | 160,1 | 785,8 |
| jun/2016 | 1,68 | 1.421 | 4.144 | 33,6 | 142,7 | 816,1 |
| jun/2018 | 1,81 | 1.499 | 4.067 | 32,2 | 138,4 | 816,1 |
| jun/2020 | 1,91 | 1.569 | 3.996 | 31,0 | 128,0 | 816,1 |
| jun/2021 | 2,01 | 1.670 | 3.895 | 30,3 | 128,2 | 1.494,5 |
| jun/2022 | 2,11 | 1.837 | 3.730 | 28,5 | 124,2 | 1.009,5 |
| jun/2024 | 2,36 | 2.002 | 3.566 | 27,1 | 112,2 | 838,6 |

Em jun/2024, 2 municípios que não atendem ao critério não têm coordenada válida e ficam sem distância. A distância é em linha
reta: não é distância por estrada, tempo de viagem nem acesso.

## Limitações

- A base só tem médicos, e o registro mais recente é jun/2024: nenhum sinal descreve a situação de hoje.
- A contagem municipal é a de médicos registrados no município: quem atua em mais de um conta em cada um. Um conjunto é a soma das
  contagens dos componentes, nunca "médicos únicos".
- O Detector não infere rotatividade de pessoas, desassistência, isolamento assistencial, suficiência do cuidado nem causa.
- Estados como unidade e conjuntos não têm intensidade (a comparação é municipal).
- Os fenômenos 8, 9 e 10 não têm intensidade, e os limites deles não foram validados: são sinais observados. A variação em 2 anos
  só existe em trechos com população comparável, lidos da própria base (com a população atual, um trecho só, de 2014 a 2024).
- A população é uma estimativa, e a taxa de um estado usa a contagem estadual sobre a soma das populações municipais.
- O contexto geográfico é a distância em linha reta entre coordenadas: não mede acesso, deslocamento nem a organização da rede.
- Os sinais combinados não formam um índice: efeitos da mesma queda contam como um evento.
- O histórico de sinais cobre só o núcleo (fenômenos 1 a 7).

## Testes

- pytest: `backend/tests/test_detector.py` — as regras em séries sintéticas (escala e histerese; zero e ausência; a magnitude
  arredondada para cima, os empates, só as transições anteriores e o mínimo de transições; o pico que volta, a quebra de fonte e a
  queda grande que persiste; o patamar; o declínio; a desaceleração igual à classe da Análise de Tendência; a instabilidade; os
  níveis; os parâmetros exploratórios; os textos; e, dos fenômenos 8 a 12, a janela só em trechos com população comparável, o
  percentil pelo posto médio, a taxa e a decomposição com os limites exatos, a posição no universo fixo com a confirmação em duas
  avaliações, a defasagem ante a referência na mesma unidade, a distância ao município que atende ao critério e a coexistência
  sem índice geral), a rota com um catálogo sintético e, no job `dados-reais`, a base versionada (Rio Rufino/SC, o Distrito
  Federal antes de 2018, uma queda grande que persiste, a desaceleração igual à da Análise de Tendência, os números do perfil e
  os fenômenos 8 a 12: os trechos de população lidos da base, com a comparação habilitada em jun/2024, e os sinais observados em
  jun/2024 e em jun/2021).
- Node: `frontend/tests/detector.test.mjs` — a leitura da resposta, os textos da tabela em linguagem simples, os filtros, a ordem,
  os parâmetros e as exportações; a seleção no contrato das ferramentas; os itens das bolhas, as camadas do mapa, a série da taxa
  e o que o Detector leva ao Simulador.
- Navegador: `backend/tests/ui_detector.py` (suíte `base-versionada`), com as bolhas, o mapa, a janela até jun/2021 e "Simular
  recuperação".
