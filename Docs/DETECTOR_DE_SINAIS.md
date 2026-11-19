# Detector de Sinais Territoriais

Ferramenta do Eixo II, na forma da **Proposta V3** (comando V23, de 13/11/2026). A referência metodológica é
[Detector e Simulador V3](DETECTOR_E_SIMULADOR_V3.md) (Partes A e B); a [V2.2](DETECTOR_E_SIMULADOR_V2_2.md) continua valendo no
que a V3 não muda (a descontinuidade de registro, as definições dos sinais 8 a 12). O perfil da base está em
[Perfil da base](PERFIL_DA_BASE_DETECTOR_SIMULADOR.md). Este documento descreve o que o sistema faz hoje: os **12 sinais** do
catálogo (os sinais 1 e 2 formam um item só, e por isso a tela lista 11 itens).

## O que é

O Detector **compara cada território com o que é comum na própria base**: territórios de tamanho parecido (o porte) e só o que
veio antes de cada data. Para cada território da seleção em uso, ele mostra a situação mais recente da janela e, à parte, o
histórico de sinais. Três coisas nunca se confundem:

1. **fato observado:** a contagem e a mudança entre registros (por exemplo, "caiu de 18 para 11, −38,9%"). Sempre aparece;
2. **raridade:** se a mudança é rara entre as mudanças anteriores de territórios do mesmo porte, com o mesmo tempo entre
   registros;
3. **nível do alerta:** **moderado**, **elevado** ou **crítico**, sempre escrito (nunca só pela cor) e sempre com o **tipo de
   critério**: "comparado com a base" ou "limite fixo" (um limite igual para todos os territórios). Até
   18/11/2026, a tela dizia "por convenção" no lugar de "limite fixo" (AJ-05, decisão do responsável): esse continua sendo o valor
   do campo `criterio` da resposta e o da nota do motor, e o estudo de calibração abaixo usa os dois nomes. Desde o AJ-07 (do mesmo
   dia), as exportações também dizem "limite fixo": a coluna "Tipo de critério" do CSV e as notas de "Exportar o método (JSON)".

Além dos três níveis, um território pode ficar **sem alerta**, **sem comparações suficientes** (a base ainda não tem história para
comparar, e a tela diz quantas comparações há e quantas o nível pede) ou **sem nível** (um conjunto, que não tem outros iguais para
comparar).

"Raro" quer dizer **incomum nesta base**, não comprovadamente pior: por construção, cerca de 1 em cada 20 territórios recebe
moderado em cada sinal comparado com a base. O nível descreve o sinal. Não é juízo de desassistência, de suficiência do atendimento
nem de prioridade de provimento. Ele é uma **divergência aprovada da SPEC** (CFG-NOR, 4.4.19: nenhum critério normativo
pré-configurado), válida só no Detector (decisão D-A do responsável, de 10/11/2026, com os nomes de 13/11/2026: moderado, elevado
e crítico; "sem comparações suficientes" no lugar de "sem classificação" e de "não calibrado"; e "alerta" para os três níveis,
sempre com o tipo de critério). Fora do Detector, o assistente continua recusando "crítico" sem critério.

O Detector calcula no motor (`backend/detector.py`, `backend/comparativos.py` e a régua comum `backend/reguas.py`, sobre
`backend/series_brasil.py`), sem o provedor de IA, e funciona com ele indisponível.

**Vale para qualquer base** (comando V23, seção 2; Proposta V3, seção A.3): a base do Brasil ou uma planilha enviada, lida com o
mesmo mapeamento de colunas das análises. O que era fixo da base do Brasil passou a ser lido da própria base: as datas e os
intervalos, o mês da série anual, o grupo de cima, a população, as coordenadas, o que a contagem conta e os nomes. Na base do
Brasil, os textos continuam dizendo "médicos", "município", "estado", "junho" e "Brasil", e os resultados são os mesmos de antes.
Numa planilha, nenhum desses nomes aparece se não vier dela. A seção [Qualquer base](#qualquer-base) descreve o que muda.

## Os três níveis e a régua

| Nível | Raridade padrão | Comparações anteriores necessárias | Cor |
|---|---|---|---|
| Moderado | 1 em cada 20 | pelo menos 19 | amarelo |
| Elevado | 1 em cada 100 | pelo menos 99 | laranja |
| Crítico | 1 em cada 1.000 | pelo menos 999 | vermelho |

- **Quem entra na comparação:** todas as mudanças anteriores à data avaliada, de todos os territórios do mesmo porte, com o mesmo
  tempo entre registros (na base do Brasil, 5 ou 7 meses). Entram aumentos, estabilidade e quedas. Nada posterior à data entra.
- **A conta:** raridade = (mudanças anteriores iguais ou piores + 1) ÷ (total de mudanças anteriores + 1), contando os empates. O
  "+1" é a própria mudança: ele evita dizer "nunca aconteceu" quando a história é curta e fixa os mínimos de 19, 99 e 999.
- **Porte:** o número de profissionais no registro anterior (no sinal 7, o patamar; nos sinais 8 a 10, o número no início da
  janela), em dez faixas: 1–3, 4–9, 10–19, 20–49, 50–99, 100–299, 300–999, 1.000–2.999, 3.000–9.999 e 10.000 ou mais.
- **Retaguarda, quando faltam comparações na faixa:** primeiro, a faixa junta-se às vizinhas, uma de cada lado. Se ainda faltar,
  **só o moderado** junta todas as faixas, com a mudança padronizada pelo tamanho (mudança ÷ tamanho^(θ/2), com θ estimado só com
  o passado). Se nada bastar, o nível fica "sem comparações suficientes", com os números.
- **Descontinuidade de registro:** os picos que voltam e as quebras de fonte já conhecidos na data avaliada ficam fora do passado
  dela. Nos sinais 8 a 10, a janela de 2 anos que **começa ou termina** num registro assim não é avaliada ("descontinuidade de
  registro", sem nível) nem entra nas comparações dos outros territórios.
- **Um nível por território:** o maior entre os seus sinais. Não há soma nem índice. Os sinais que vêm da mesma queda (queda
  recente, declínio, abaixo do que já teve e os três comparados com outros) contam como **um evento**, e a tela diz isso: são
  "a mesma queda vista de ângulos diferentes" (desde 18/11/2026, AJ-10).
- **Aviso da base:** quando, numa mesma data, os territórios com queda rara passam do triplo do esperado (mais de 15%, com 100
  avaliações ou mais), a tela avisa que pode ter havido mudança no registro da base, e não nos territórios.
- **Estados como unidade:** têm régua própria, com a base dos estados (as contagens estaduais). É uma base pequena: os níveis
  mais graves podem ficar sem comparações suficientes.
- **Conjuntos:** sem nível. A tela mostra os fatos e o motivo.

## Os 12 sinais

Todos os limites são padrões e podem ser trocados em "Ajustar critérios" (a configuração passa a ser exploratória).

| # | Sinal | O que mede | Moderado | Elevado | Crítico | Critério |
|---|---|---|---|---|---|---|
| 1 | Poucos profissionais | Número no último registro | 4 ou 5 | 2 ou 3 | 1 | Limite fixo |
| 2 | Nenhum profissional registrado | Zero confirmado, e há quanto tempo | — | — | Zero, com a duração | Limite fixo |
| 3 | Declínio persistente | Quedas anuais seguidas (o mês âncora) e perda acumulada | 2 quedas e 10% ou mais | 3 quedas e 20% ou mais | 4 quedas e 30% ou mais | Limite fixo |
| 4 | Desaceleração | A classe "Desaceleração do crescimento" da Análise de Tendência, nos 4 registros anuais | A classe em 2 anos seguidos | — | — | Limite fixo (exploratório) |
| 5 | Instabilidade | Oscilação de 7 registros ÷ a típica do porte | 1 em 20 | — | — | Comparado com a base |
| 6 | Queda recente | Queda de um registro para o seguinte | 1 em 20, e pelo menos 2 profissionais e 10% | 1 em 100, e pelo menos 2 e 20% | 1 em 1.000, e pelo menos 3 e 30% | Comparado com a base, com tamanho mínimo |
| 7 | Abaixo do que já teve | Distância ao patamar: a maior média de 2 anos completos, antes dos 4 últimos registros | 2 últimos registros 15% ou mais abaixo | Isso, e 1 em 100 | 4 últimos registros 30% ou mais abaixo, e 1 em 1.000 | Limite fixo no moderado; comparado com a base no elevado e no crítico; patamar de pelo menos 20 |
| 8 | Menos profissionais por habitante | Variação da taxa por 1.000 habitantes em 2 anos | 1 em 20 | 1 em 100 | 1 em 1.000 | Comparado com a base; população comparável; pelo menos 20 no início da janela |
| 9 | Perda de posição | Variação do percentil da taxa em 2 anos | 1 em 20 | 1 em 100 | 1 em 1.000 | Idem |
| 10 | Perda em relação à referência | Variação do índice ante o grupo de cima, sem o próprio território, em 2 anos | 1 em 20 | 1 em 100 | 1 em 1.000 | Idem; precisa de grupo de cima |
| 11 | Distância | Km em linha reta até o território mais próximo com taxa de pelo menos X% da taxa da base toda, e a posição dessa distância | Só contexto | — | — | X ajustável de 10% a 500%; o padrão é 100% |
| 12 | Sinais juntos | Quais sinais com nível coincidem no território, agrupando os efeitos da mesma queda | Mostra quais coincidem; não soma | — | — | — |

Notas:

- **Sinais 1 e 2:** vale a situação mais grave entre os dois últimos registros válidos: a piora aparece na hora, e a melhora,
  depois de dois registros. Quando o nível vem do registro anterior, a frase diz qual era ("6 médicos (3 no registro
  anterior)"). Zero é registro observado (zero confirmado); a data sem registro é ausência de dado, nunca zero.
- **Uma queda de 2 para 1 profissional** não vira alerta de queda (sinal 6), porque é só 1: ela aparece como crítico em "Poucos
  profissionais" (sinal 1). O "Entenda" do sinal 6 traz esse exemplo.
- **Sinal 4:** mostra uma mudança de ritmo; não indica o que vem depois (na base do Brasil, a repetição da classe não antecipou o
  crescimento seguinte). O moderado é rotulado como exploratório.
- **Sinal 5:** a oscilação típica do porte (a escala com que cada mudança da janela é ajustada) é medida só nas mudanças
  anteriores de territórios com pelo menos 6 profissionais no registro anterior, por tipo de intervalo entre registros (na base do
  Brasil, 5 ou 7 meses), e só quando há pelo menos 100 delas (`detector.MEDIA_MINIMA_DA_INSTABILIDADE` e `MINIMO_DE_ESCALA`); sem
  isso, o sinal fica "sem a oscilação típica do porte para comparar". A Ficha A diz o mesmo.
- **Sinal 6:** o nível é o mais grave em que a queda é rara **e** tem o tamanho mínimo daquele nível (o maior entre o mínimo em
  profissionais e a fração do que havia, arredondada para cima). Sem queda, a tela ainda diz que níveis a base sustenta para o
  porte.
- **Sinal 7:** o moderado é por limite fixo; o elevado e o crítico pedem também a raridade do afastamento entre territórios com
  patamar do mesmo porte. Com patamar abaixo de 20, é só descritivo. O patamar é uma média e pode ter decimal: abaixo de 100, a
  frase o mostra com as casas ("patamar de 1,75", e não "patamar de 2"); de 100 para cima, o inteiro mais próximo. **Quando o
  sinal não é avaliado, a frase diz o motivo**, como nos sinais 5 e 8 a 10 (desde 15/11/2026): "43% abaixo do que já teve (patamar
  de 1,75, abaixo do mínimo de 20)", "No patamar ou acima dele (patamar de 3,25, abaixo do mínimo de 20)" ou, com uma
  descontinuidade nos últimos registros, "… (patamar de 40) · descontinuidade de registro".
- **Sinais 8 a 10:** as definições são as da V2.2 (a taxa = profissionais ÷ população × 1.000; o percentil pelo posto médio, no
  universo fixo da janela; o índice = 100 × taxa do território ÷ taxa da referência, com a referência na mesma unidade e sem o
  território). O que muda é o nível: a variação em 2 anos é comparada com as variações anteriores de territórios do mesmo porte.
  **A janela não começa nem termina num registro marcado** como pico que volta ou quebra de fonte (com o que era conhecido na
  data avaliada): nesse caso, o número aparece, com "descontinuidade de registro", sem comparação e sem nível, e a janela fica
  fora das comparações dos outros. Exemplo da base: Brochier (RS) teve 7, 31, 11 e 8 médicos de jan/2022 a jun/2023 (um pico que
  voltou); a variação de jun/2022 a jun/2024, de −74,4% na taxa, partia do registro do pico e deixou de ser alerta crítico.
- **Sinal 10, em palavras simples:** a frase diz quantas vezes a taxa da referência o território tinha e tem ("A taxa passou de
  1,27 para 0,72 vezes a dos demais municípios de São Paulo em 2 anos"); o índice e os pontos ("índice de 126,8 para 72,1: −54,7
  pontos") ficam na explicação completa. **O nome é "Perda em relação à referência"** desde 18/11/2026 (AJ-09; antes, "Mais
  longe da referência", que sugeria distância em km, o sinal 11, e nem sempre o território fica mais longe: Barra Bonita (SP)
  passou de 1,27 para 0,72 vez a taxa da referência, de 27% acima a 28% abaixo, quase à mesma distância). O que o sinal mede é
  a perda em relação à referência. "O que significa": "A taxa do território piorou em relação à da referência: caiu mais, ou
  subiu menos, que ela."; o exemplo: "Índice 100: taxa igual à da referência. De 90 para 75, o território perdeu 15 pontos em
  relação a ela; de 130 para 115 também, mesmo continuando acima."; sem comparações bastantes, "… se esta perda em relação à
  referência chega ao nível …". A chave (`defasagem`), os campos e os números não mudam.
- **Sinal 11:** nunca vira alerta e nunca usa as palavras "isolamento" ou "desassistência". O estado como unidade e o conjunto
  de estados não têm um ponto único, e o sinal não se aplica a eles (`comparativos.contexto`: só o nível dos municípios tem a
  distância); num conjunto de municípios, vale o componente mais próximo. **A frase diz o que é o território de referência** — o mais próximo
  com taxa de pelo menos X% da taxa da base toda, com o X em uso e o valor do critério — **e em que posição a distância fica**
  entre os territórios abaixo do critério (desde 15/11/2026). Rio Rufino (SC), em jun/2024: "A 21,3 km, em linha reta, de BOCAINA
  DO SUL (SC): o município mais próximo com taxa igual ou maior que a do Brasil (2,36 médicos por 1.000 habitantes). De cada 100
  municípios abaixo desse critério, 40 ficam mais perto de um município assim". Desde a revisão final do comando V23
  (15/11/2026): com o padrão de 100%, a frase diz "com taxa igual ou maior que a do Brasil" (com outro critério, "com pelo menos
  70% da taxa do Brasil"); e a posição vem em palavras simples — antes, "Mais longe que 40% dos municípios abaixo desse
  critério". Num conjunto, a frase não traz a posição.
- **O motivo na frase (desde a revisão final do comando V23, 15/11/2026).** Sempre que um sinal não é avaliado, não é calculável
  ou está indisponível, a frase da linha diz o motivo, em todas as bases, como já fazia o sinal 7 (`detector._na_frase`; o motivo
  inteiro continua na explicação completa):
  - sinal 3: "Sem a série anual para avaliar: faltam registros de junho para comparar";
  - sinal 5: "Oscilação não calculável: média abaixo de 6 médicos na janela" (ou "sem a oscilação típica do porte para
    comparar");
  - sinal 6: "Sem registro para comparar: falta o registro desta data" (ou "falta um registro anterior"); com descontinuidade, a
    frase diz qual ("… com descontinuidade de registro (pico que volta)");
  - sinal 7: "Não calculável: o patamar anterior é zero" e "Sem registro nesta data para comparar com o patamar";
  - sinais 8 a 10: "Sem registro em jan/2016"; "Não calculável: sem população válida na data (o denominador não é estimado)";
    com o valor da data à vista, ele vem antes ("Índice 314,3 ante a referência em jun/2021 · variação não calculável: sem taxa
    válida do território ou da referência no início ou no fim da janela"); "Sem referência: a UF deste município não tem outros
    municípios" (Brasília); "… · só descritivo: menos de 20 médicos no início da janela"; "… · comparação não habilitada: " com o
    motivo da população;
  - sinal 11: "Não se aplica ao estado como unidade: ele não tem um ponto único"; "Sem coordenada válida em jun/2024: a
    distância não pode ser medida"; "Não calculável: sem a taxa do Brasil na data";
  - sinal que a base não sustenta: "Indisponível nesta base: a base não tem população nem grupo de cima" (em `situacao`; a tela
    continua mostrando o rótulo "Indisponível nesta base" e, ao lado, os motivos por extenso).
- **Sinal 12:** lista os sinais com nível e diz quantos são a mesma queda ("4 desses sinais são a mesma queda vista de ângulos
  diferentes e contam como um evento só.", desde o AJ-10; antes, "… vêm da mesma queda e contam como um evento."). Sem soma
  de pontos e sem índice geral.

**População comparável (sinais 8, 9 e 10).** A variação em 2 anos só é calculada quando a janela de comparação (na série anual)
cabe inteira num **trecho de população comparável**. Os trechos vêm da própria base (`comparativos.populacao_comparavel`). Em
cada passagem de ano, a base inteira é olhada:

- **população repetida:** metade da base ou mais repete o valor do ano anterior, e isso não é o comum nas outras passagens;
- **salto:** 5% da base ou mais (e pelo menos 3 territórios) varia mais de 5%, e isso é 3 vezes ou mais o comum nas outras
  passagens.

Nos dois casos, o trecho termina ali. Alguns territórios parados ou com salto são normais e não desligam a comparação. Com a
população do Ministério da Saúde, em uso desde 13/11/2026, **a base inteira é um trecho só (2014–2024)**. Quando a janela não cabe
num trecho, o estado é "comparação não habilitada", com o motivo lido da base, e o valor da data (a taxa, o percentil e o índice)
continua à vista. A resposta da rota traz os trechos em `comparacao.trechos` e o motivo em `comparacao.motivo`.

**Qualidade do registro** (como na V2.2, seção 2.4):

- **descontinuidade de registro — pico que volta:** salto de 10 ou mais que ao menos dobra a contagem e volta, em até dois
  registros, a até 125% do valor anterior. Até a volta ser observada, o salto leva "verificar registro". A volta não gera alerta,
  o trecho sai da régua, e o registro do pico fica fora do patamar, da série anual e da instabilidade, e não pode ser o começo
  nem o fim da janela dos sinais 8 a 10;
- **descontinuidade de registro — quebra de fonte:** a soma municipal da UF abaixo da contagem estadual de médicos únicos (na
  base, só o Distrito Federal, de jan/2014 a jun/2017). O trecho sai da régua, e a janela do município começa depois dele; nos
  sinais 8 a 10, a janela de 2 anos que começa ou termina num registro do trecho não é avaliada;
- **verificar registro:** o salto sem volta observada e a queda de 10 ou mais que leva a contagem à metade ou menos. A queda
  grande que persiste **continua alertável**.

## Na tela

- **Onde:** o botão **Detector de Sinais** (`analise-ferramenta-detector`), na linha "Ferramentas" da navegação principal. A
  ferramenta abre no lugar do painel da aba e usa a **seleção em uso**: os municípios, os estados como unidade e os conjuntos.
  Sem territórios, diz "Nenhum território selecionado" e não pede nada ao motor.
- **Título e "Entenda"** (`detector-entenda-ferramenta`): "Compara cada território com o que é comum na própria base."
- **Ficha metodológica (PDF)** (`detector-ficha`, ao lado das exportações; desde 18/11/2026, AJ-03): abre numa nova aba a
  **Ficha A** (fonte em [`Docs/fichas/ficha_detector.html`](fichas/ficha_detector.html); o PDF,
  `frontend/public/fichas/ficha-detector.pdf`, sai com os arquivos estáticos da interface, e o link respeita a base da página,
  `ADT_BASE_DA_PAGINA`). Desde 18/11/2026 (AJ-06, comando de correção das fichas), ela é **só metodológica, para quem usa o
  Agente** (gestão, área técnica, pesquisa): abre com uma **leitura rápida** (o que o Detector faz, como ler o resultado e o que
  ele não diz) e explica o que ele mede, como mede, com que critérios e limites — os 12 sinais, os níveis e a régua, as
  condições, os parâmetros, os estados como unidade e os conjuntos, a mesma queda, o aviso da base, o histórico, a régua da data
  e o monitoramento, a meta de "Simular recuperação" e os limites —, com os números da base do Brasil em jun/2024 e a versão
  do método na abertura. Saiu dela o bastidor do desenvolvimento (as marcas de estado, os caminhos de arquivo, as rotas e os
  campos da API, os códigos da SPEC, das decisões e dos avisos, os hashes, as exportações e as versões), que continua neste
  documento; o tipo de critério se chama "limite fixo". A letra é a Inter estática das fichas (`Docs/fichas/fontes/`, com a
  licença OFL), embutida como TrueType (antes, a variável do site, embutida como Type 3).
- **Aviso da data** (`detector-data`): "Registro mais recente da base: jun/2024. Os sinais descrevem a situação até jun/2024, não
  a de hoje." Quando há, o **aviso da base** (`detector-aviso-da-base`).
- **Filtros, numa linha** (`ferramenta-filtros`): **Até** (`detector-janela-fim`, a data avaliada, entre as competências reais),
  **Nível** (`detector-filtro-nivel`), **Sinal** (`detector-filtro-sinal`: a linha passa quando o sinal tem nível nela; há também
  "Mais de um sinal com nível" e "Registro a verificar ou com descontinuidade") e **Buscar território** (`detector-busca`; o nome
  anterior de um município continua achando-o). Ao lado, **Ajustar critérios** e **Voltar ao padrão**, sempre à vista.
- **Resumo dos níveis** (`detector-resumo`): "[n] críticos · [n] elevados · [n] moderados · [n] sem alerta · [n] sem comparações
  suficientes" (e "[n] sem nível", quando há conjuntos). Cada item é um botão e funciona como o filtro "Nível".
- **Visões:** **Lista** (padrão), **Mapa** e **Gráfico** (`detector-vista-lista`, `detector-vista-mapa` e
  `detector-vista-grafico`). No Mapa e no Gráfico, a lista continua abaixo, como detalhe.
  - **Mapa** (`detector-mapa`): o mapa de pontos da Seleção, com cada município pintado pelo nível do alerta (com o filtro
    "Sinal", pelo nível daquele sinal), a legenda escrita com as contagens (`detector-legenda-niveis`), os conjuntos pelo
    contorno e a sigla do grupo de cima junto aos pontos dele. **Na base do Brasil, o mapa tem as divisas** (desde 15/11/2026,
    etapa 7 do comando V23; `data-divisas="carregadas"`), da malha municipal do IBGE (ver "A malha das divisas"):
    - **as divisas dos estados ficam sempre à vista** (`analise-mapa-divisas-dos-estados`);
    - **as dos municípios aparecem ao aproximar ou com um estado só**: quando a pessoa escolhe um estado em "Aproximar o mapa em"
      (`detector-mapa-aproximar`, com os estados dos territórios à vista; o mapa enquadra o estado inteiro, e o que aparece dos
      vizinhos em volta dele continua com os pontos, as áreas com nível e as divisas dos estados) ou quando os territórios à
      vista são de um estado só;
    - **a área de cada município à vista com nível leva a cor do nível** (`analise-mapa-area`), por baixo do ponto dele; quem não
      tem nível, e o que a malha tiver a mais, fica sem cor;
    - **a malha só é pedida quando o mapa abre**, uma vez; enquanto carrega, o mapa mostra os pontos e diz "As divisas estão
      sendo carregadas."; se o arquivo não puder ser lido, segue só com os pontos e diz isso;
    - **numa planilha, não há malha**: o mapa segue sem divisas e diz "A base não tem as divisas" (o nome do grupo situa os
      pontos).

    O mapa é desenhado na largura que tem na tela (`data-largura`): no celular, o texto mantém 12 px, e o mapa fica mais alto.
    **As coordenadas são as das análises** (desde a revisão final do comando V23, 15/11/2026): na base do Brasil, os seis
    municípios em que a fonte traz a latitude ou a longitude fora do intervalo válido ficam com a **sede municipal da camada
    oficial do IBGE** (`dados/brasil/complemento_coordenadas.json`), e o mapa tem os 5.570 pontos. A legenda diz quais pontos à
    vista vieram da camada (`detector-mapa-coordenadas-oficiais`): "Em 2 municípios à vista, o ponto é o da sede municipal, da
    camada oficial de coordenadas do IBGE, porque a base traz a coordenada deles fora do intervalo válido: BALNEARIO RINCAO (SC);
    PESCARIA BRAVA (SC)."
    **Quem está na lista e não tem ponto** aparece numa frase abaixo da legenda (`detector-mapa-fora`):
    quantos são, com que nível, quais e por quê — a base não traz a coordenada deles na data, ou traz a latitude ou a longitude
    fora do intervalo válido ("Fora do mapa: 1 comuna à vista (1 sem nível). Em jun/2024, a base não traz a coordenada de:
    Fenduna. Continua na lista, com o seu nível."). Assim, os pontos do mapa e os de fora somam a lista. Na base do Brasil,
    ninguém fica de fora; numa planilha, fica quem ela trouxer sem coordenada válida.
    **Os nomes dos grupos** (as siglas dos estados) ficam no centro dos pontos de cada grupo, **sem se sobrepor**: o que cobriria
    outro se afasta para o lugar livre mais perto (`data-deslocado`; desde a revisão final do V23 — antes, a sigla de Goiás e a do
    Distrito Federal ficavam uma sobre a outra no mapa do Brasil inteiro, e as que cobririam outra não apareciam).
  - **Gráfico** (`detector-bolhas`): o gráfico de bolhas do Agente, com uma bolha por território à vista que tem distância a
    mostrar. Na horizontal, a distância do sinal 11; na vertical, a taxa por 1.000 habitantes; o tamanho, a população; a cor, o
    nível. Tocar numa bolha ou num ponto abre os detalhes do território.

  Nas duas visões, a cor e o tamanho seguem o maior nível do território, e **a dica** de cada ponto e de cada bolha nomeia o
  sinal pintado (o principal do alerta; com o filtro "Sinal", aquele sinal), com o nível, e diz quantos outros sinais com nível
  o território tem: "ABELARDO LUZ (SC) · Menos médicos por habitante · elevado; mais 3 sinais com nível" (desde 18/11/2026,
  AJ-04; antes, só "nível elevado").
- **Lista** (`detector-tabela`, 50 territórios por página), com **cinco colunas** e **cada sinal com nível numa linha**, do mais
  grave ao menos grave (no empate, na ordem dos sinais), desde 18/11/2026 (AJ-04; antes, quatro colunas, uma linha por território
  e só o sinal principal no "Por quê", com "(+N sinais)"). Cada território é um grupo de linhas (`detector-linha`, com
  `data-linhas-de-sinal`), uma por sinal com nível (`detector-sinal-linha`, com `data-sinal` e `data-nivel`):
  - **Território** (com o tipo, quando é estado como unidade ou conjunto), uma vez para o grupo;
  - **Sinal** (`detector-sinal`): o nome do sinal, o mesmo do filtro "Sinal";
  - **Alerta** (`detector-alerta`): o nível do sinal (`detector-nivel`: Moderado, Elevado ou Crítico) e o tipo de critério
    (`detector-criterio`: "limite fixo" ou "comparado com a base"). Sem sinal com nível, o território tem uma linha só, com
    "Sem alerta", "Sem comparações suficientes" ou "Sem nível (conjunto)" e a coluna "Sinal" vazia;
  - **Por quê** (`detector-por-que`): a frase do motor sobre o sinal daquela linha. A do sinal principal é a da lista, sem a
    contagem "(+N sinais)"; a de cada outro sinal é a do detalhe do território (`fenomenos[].situacao`), que a página pede ao
    motor só para os territórios à vista com mais de um sinal com nível, dois de cada vez e só depois que a lista do pedido em
    uso chegou (enquanto isso, "Carregando a frase deste sinal…"; se o pedido falha, "A frase deste sinal está nos detalhes do
    território."). A página não escreve frase de resultado. Desde 18/11/2026 (AJ-08), **as frases já buscadas não são pedidas
    de novo**: os detalhes que chegaram certos ficam guardados por pedido, com a mesma chave da lista guardada (a versão da base,
    a planilha, a seleção, a data, a janela e os critérios), e saem junto com ela (a memória da tela guarda os seis últimos
    pedidos). Voltar a um pedido já visto — "Voltar ao padrão", trocar o "Até" e voltar, mudar a seleção e voltar — traz a
    lista e as frases da memória, sem pedir nada ao motor; abrir um território usa o detalhe guardado; um detalhe que falhou
    não fica guardado e é pedido de novo; a resposta atrasada de um pedido anterior nunca entra na lista à vista. Nada vai
    para o armazenamento do navegador, e "Nova sessão" recarrega a página e limpa tudo (antes do AJ-08, a lista vinha da
    memória, mas os detalhes eram apagados a cada troca de pedido e pedidos de novo);
  - **Último registro** (`detector-ultimo`), uma vez para o grupo: "jun/2024 · 5 médicos", com a marca de registro quando há
    (`detector-registro`: "verificar registro" ou "descontinuidade de registro").

  Quando dois ou mais sinais são da mesma queda, uma linha a mais do território diz isso (`detector-linha-nota`: "A, B e C são
  a mesma queda vista de ângulos diferentes: contam como um evento só."; até o AJ-10, "… vêm da mesma queda: contam como um
  evento."). O resumo, os contadores, os filtros, a ordem e as páginas continuam **por território**
  ("de N territórios"): com o filtro "Sinal", o território aparece com todos os seus sinais. Os cabeçalhos ordenam a lista: pelo
  nome, pelo nível (o padrão: do crítico ao moderado; depois quem a base não pôde comparar, os conjuntos e os sem alerta) ou pelo
  número do último registro. A ordem não é um índice. Desde o AJ-08, **cada cabeçalho fica numa linha** — o rótulo, a seta de
  ordenação e o "Entenda" — quando a área da lista tem pelo menos 1.100 px (numa tela de 1366 px, ela tem cerca de 1.250 px),
  sem rolagem horizontal; mais estreita, o cabeçalho quebra como antes. Os cabeçalhos **Sinal, Alerta, Por quê e Último registro** têm "Entenda"
  (`detector-entenda-sinal`, `-alerta`, `-por-que` e `-ultimo`) **escritos pela página**, com os nomes da base, que explicam só o
  campo, em duas ou três frases (o do alerta, os dois tipos de critério; o do último registro, a contagem da última data com
  registro, com o território e a data da primeira linha à vista, sem dizer que o número sozinho explica o alerta); o "Ver
  explicação completa" deles abre a seção da ficha (desde o AJ-03; antes, os "Entenda" do alerta e dos termos vinham do motor e
  explicavam o método: porte, patamar, percentil e "1 em cada N"). No celular, cada território vira um cartão: o nome e o último
  registro no alto e, em cada sinal, o nome e o alerta numa linha e o porquê abaixo.
- **Ressalvas de leitura** (`detector-ressalvas`, logo abaixo da lista; desde o AJ-03): "raro" quer dizer incomum nesta base,
  não comprovadamente pior, e o que o nível não é; a distância (sinal 11) só como contexto, quando a base tem o sinal; o estado
  como unidade, com régua própria, quando há algum na lista; e os conjuntos, sem nível, quando há algum. As demais ressalvas já
  estão na tela (a data do registro mais recente, a configuração exploratória, o aviso da base e "um nível por território").
- **Detalhe** (a seta de cada linha, `detector-detalhe`): o alerta do território, com o nome do sinal principal
  (`detector-detalhe-sinal`, desde o AJ-03), o porquê e, quando há, "… são a mesma queda vista de ângulos diferentes: contam como
  um evento só"
  (`detector-mesma-queda`); a série observada (`detector-serie`), só com os registros reais e as
  marcas de registro; a **série da taxa** (`detector-serie-da-taxa`), com a da referência tracejada e as datas escritas como nos
  outros gráficos do Detector ("jun/2021"); e os 12 sinais em quatro grupos
  (`detector-grupo`) — **Quantos há** (1–2), **Como mudou** (3 a 7), **Comparado com outros** (8 a 10) e **Onde fica** (11) —,
  mais **Juntos** (12). Em cada sinal (`detector-fenomeno`): o nível com o tipo de critério (ou "Sem alerta", "Sem comparações
  suficientes", "Sem nível (conjunto)", "Sem dado para avaliar", "Não avaliado" ou "Só contexto"), **uma frase**, o que a base
  ainda não sustenta ("Sem comparações suficientes para o crítico: há 864, e ele pede 999.") e o **"Entenda"**. A **explicação
  completa** (`detector-fenomeno-explicacao`) traz os sete campos: o que foi observado, qual critério, comparado com o comum, o
  que significa, o que não significa, limitações do dado e qualidade do registro. Há também o **histórico de sinais**
  (`detector-historico`, sinais 1 a 7), em que cada data é avaliada só com o que era conhecido nela; em cada data com alerta, o
  nível e o nome do sinal dele (`detector-historico-alerta`: a coluna com aquele nível; no empate, a primeira na ordem dos
  sinais; desde o AJ-03, nenhum resultado aparece sem o nome do sinal).
- **Gráficos na largura da tela** (desde 15/11/2026): a série observada é desenhada na largura que tem na tela (`data-largura`),
  em vez de ser encolhida: o texto dos eixos mantém 12 px também no celular, onde o gráfico fica mais alto (220 px, em vez de
  170) e mostra menos datas no eixo (um ano a cada quatro).
- **"Entenda"** (`frontend/src/Entenda.tsx`, igual no Detector e no Simulador): fica escondido e abre com o mouse (ao passar por
  cima), com um toque ou pelo teclado (ao receber o foco; Enter ou Espaço fixam); fecha ao sair (o mouse deixa o botão e a
  caixa, o foco sai deles, Esc ou um toque fora). Traz duas ou três frases simples e um exemplo com números; a explicação
  inteira fica em "Ver explicação completa": no sinal, os sete campos; no "Entenda" da ferramenta e nos dos cabeçalhos da lista,
  a ficha metodológica em PDF, numa nova aba, na seção certa (`#nameddest=<seção>`; até 18/11/2026, "Como foi calculado"). Os
  textos vêm do motor, menos os dos cabeçalhos da lista, escritos pela página.
- **Ajustar critérios** (`detector-parametros`): os limites de cada sinal **em frases, com os campos dentro delas**
  (`detector-parametro-<grupo>-<campo>`), por exemplo: "Alerta elevado quando a queda for de pelo menos [2] médicos e [20]% do
  que havia, e for rara: em territórios do mesmo porte, só 1 em cada [100] mudanças anteriores foi uma queda igual ou maior."
  Ali fica também o início da janela ("Considerar os registros desde", `detector-janela-inicio`). Trocar um valor e aplicar
  torna a configuração **exploratória**: aviso no alto (`detector-exploratorio`), nos textos (uma nota) e nas exportações (a
  coluna "Configuração"). **"Voltar ao padrão"** (`detector-voltar-ao-padrao`) fica sempre à vista, desligado enquanto os
  critérios são os do padrão; os padrões nunca são trocados em silêncio.
- **A régua da data nas exportações e na ficha** (desde 18/11/2026, AJ-03): **"Como foi calculado" saiu da tela**
  (`detector-metodo`: as notas, os três níveis, a régua da data por porte e o monitoramento, com a linha de versões). A
  explicação e os números da base do Brasil em jun/2024 estão na Ficha A (seção 13: "queda maior que 44,4% (com as faixas
  vizinhas: 2.720 comparações)", "sem comparações suficientes (864 de 999, com as faixas vizinhas)", "nenhuma queda chega a esse
  nível", com a leitura de cada célula). Os números da data e da base em uso continuam em **"Exportar o método (JSON)"**
  (`detector-exportar-metodo`, como antes): `regua_na_data` — por faixa de porte, na queda recente (`perda`) e no sinal 7
  (`patamar`), as comparações do porte e, em cada nível, a régua usada de fato (`umEm`, `pede`, `origem`: `porte`, `vizinhas` ou
  `todas`, `comparacoes`, `cortePct` e, com todas as faixas, `corteAtePct`), mais o `monitoramento` —, `regua_dos_estados_na_data`
  (com estados como unidade na seleção), os níveis, os critérios em uso, as notas, as limitações e as versões do método e da
  base. O teste da tela da régua em palavras saiu com ela; a régua continua conferida com o motor em
  `backend/tests/test_detector.py` (território a território) e, na exportação, em `frontend/tests/detector.test.mjs` e
  `backend/tests/ui_detector.py`.
- **Ligação com o Simulador de Cenários** (nos detalhes de cada território):
  - **"Abrir no Simulador"** (`detector-abrir-no-simulador`) abre o [Simulador](SIMULADOR_DE_CENARIOS.md) só com aquele
    território, com o contexto: a data avaliada, os sinais com nível ("Queda recente (elevado)") e, quando a pessoa escolheu uma
    janela no Detector, essa janela. A seleção principal não muda;
  - **"Simular recuperação"** (`detector-simular-recuperacao`) só aparece para o território que está abaixo do patamar (sinal
    7). Abre o Simulador com uma **meta hipotética**, que a pessoa pode trocar: voltar ao patamar, num número inteiro (o patamar
    arredondado para cima). A frase diz de onde a meta vem ("voltar ao patamar, 79 médicos (o patamar é de 78,25, a maior média
    de dois anos seguidos antes dos registros mais recentes, arredondado para cima)"). O resultado é um cenário e uma conta
    condicional, nunca uma recomendação.
- **Exportações:** a lista em CSV (uma linha por território: o alerta, o tipo de critério, o porquê, os sinais com nível, os da
  mesma queda, os sem comparações suficientes, o nível e os valores de cada sinal, a janela, a versão da base e do método e a
  configuração) e o método em JSON (a fonte, a janela, os critérios padrão e em uso, os níveis, a régua da data, a dos estados
  quando há, o aviso da base, as notas e a referência). Desde 18/11/2026 (AJ-07), com os nomes da tela: no CSV, o tipo de
  critério é "limite fixo" ou "comparado com a base" (`rotuloDoCriterio`, a mesma tabela da lista; antes, o valor do campo,
  "por convenção"); nas notas do JSON, "por convenção" vira "limite fixo" (`comOsNomesDaTela`, pela mesma tabela; a nota da
  resposta não muda, porque descreve os valores do campo `criterio`); e a referência do JSON é a "Ficha metodológica A — Detector
  de Sinais Territoriais (fichas/ficha-detector.pdf)" (antes, "Docs/DETECTOR_E_SIMULADOR_V3.md, Partes A e B"). Os números são
  os mesmos.

**Nomes da base.** Os textos usam os nomes que a base dá (`fonte.rotulos`): na base do Brasil, "médicos", "município", "estado"
e "Brasil". **Linguagem:** sem termos técnicos na primeira tela; "porte", "patamar", "percentil" e "1 em cada N" têm "Entenda".

## Qualquer base

Antes das ferramentas, o Agente lê a base e mostra o **perfil da base**, com o resumo "com esta base, dá para… / não dá para…
(motivo)". O perfil, com o da base do Brasil e o de uma planilha de teste, está em
[Perfil da base](PERFIL_DA_BASE_DETECTOR_SIMULADOR.md#9-o-perfil-que-o-agente-lê-qualquer-base).

Com uma **planilha enviada**:

- **Leitura.** O arquivo passa pelo mesmo portão das análises (`painel._upload_context`): as colunas do painel "Colunas", as
  premissas confirmadas, a categoria e os nomes. `backend/series_da_planilha.py` monta daí a mesma estrutura da base do Brasil.
  Nada é gravado, e nada vai ao provedor de IA.
- **Datas.** A coluna de período pode trazer `AAAAMM`, `AAAA-MM`, `AAAA-MM-DD` ou só o ano. Com só o ano, a base tem um registro
  por ano, as datas aparecem como "2023" e os textos não citam mês ("de um ano para o outro"). Sem datas reconhecíveis, com dois
  registros no mesmo mês ou com um registro só no tempo, a ferramenta recusa, dizendo por quê.
- **Intervalos.** Só se comparam mudanças com o mesmo tempo entre registros; durações com até 1 mês de diferença ficam juntas.
- **Série anual.** Usa o mês presente em todos os anos (o mês do último registro, quando ele se repete em todos). Sem nenhum, os
  sinais anuais (3, 4 e 8 a 10) ficam indisponíveis.
- **Territórios.** As unidades da planilha (pelo código, quando há a coluna; senão, pelo nome), os conjuntos delas e, desde
  15/11/2026 (etapa 7 do comando V23), **o grupo de cima como unidade**. A planilha não tem uma contagem própria do grupo: a
  série dele é **a soma das unidades dele, nas datas em que todas têm registro** (como um conjunto com todas elas; nas outras
  datas, é ausência de dado, nunca uma queda), e a contagem diz isso ("soma das contagens das áreas da zona, nas datas em que
  todas têm registro"). O grupo aparece com o nome dele e a palavra da base ("Norte (zona)"), tem a régua própria dos grupos —
  uma base pequena, em que os níveis mais graves costumam ficar "sem comparações suficientes" — e não entra junto com as unidades
  dele (RQ-DAD-30). Só o nível acima do grupo (o papel `grupo_territorial_superior`) fica fora das ferramentas, com o aviso.
- **O que a base não tem.** Sem população, os sinais 8 a 11 ficam **"Indisponível nesta base"**, com o motivo, em vez de "não
  calculável"; sem grupo de cima, o sinal 10; sem coordenadas com o referencial informado, o sinal 11. **Cada sinal diz tudo o
  que falta para ele** (`detector.motivos_da_falta`), e o detalhe do território e o perfil da base dizem o mesmo: sem população e
  sem grupo de cima, o sinal 10 diz as duas coisas ("A base não tem população: sem ela, não há taxa por habitante. A base não tem
  grupo de cima: não há referência para comparar."); sem população e sem coordenadas, o sinal 11 também. Na lista, o filtro
  "Sinal" e "Ajustar critérios" ficam só com os sinais que existem na base. O Mapa fica desligado sem coordenadas, e o
  Gráfico, sem a distância, cada um com o motivo.
- **O que a base não sustenta.** Os níveis continuam pedindo 19, 99 e 999 comparações: numa base curta, o elevado e o crítico
  aparecem como "sem comparações suficientes", com os números ("há 360, e ele pede 999").
- **Nomes.** Os do painel "Colunas" (a unidade, o grupo e o todo), com a concordância ("a comuna mais próxima", "das demais
  comunas"). A contagem é de "vínculos" ou "postos", quando a unidade de contagem informada diz isso. Senão, leva **o nome dos
  trabalhadores informado no envio** ("Quem são os trabalhadores contados?"), quando ele é um plural que os textos podem usar:
  "Enfermeiros" vira "enfermeiro" e "enfermeiros" ("Poucos enfermeiros ou nenhum enfermeiro registrado"); "Técnicos de
  enfermagem", "técnico de enfermagem" (só as palavras antes da primeira preposição vão para o singular). Um nome feminino (os
  textos concordam no masculino), dois nomes ("médicos e enfermeiros"), uma sigla ou uma palavra que não está no plural
  ("Enfermagem") ficam com "profissional" e "profissionais" (`series_da_planilha.nome_dos_trabalhadores`).

O **Simulador de Cenários** também abre com uma planilha (comando V23, Parte C), nos dois modos e também quando ela só traz o
ano: o detalhe do Detector oferece "Abrir no Simulador" e, quando o território tem patamar, "Simular recuperação". Só sem datas
que o Agente reconheça o botão do Simulador fica desligado, com o motivo, e o detalhe não oferece essas duas ações
([Simulador de Cenários](SIMULADOR_DE_CENARIOS.md), seção "Qualquer base").

## Rota

`POST /api/detector` (formulário, como `/api/painel`): `options` (JSON) e a base — `dataset=brazil` com `dataset_version`, ou,
desde o comando V23, uma planilha enviada, com `file`, `sheet` e `mapping` (o mapeamento de colunas, como em `/api/painel`). O
endereço e os campos que a resposta já trazia não mudaram. Só lê e calcula: nada é registrado na sessão, e nada vai ao provedor
de IA. Conta nas vagas das operações pesadas (`carga.PESADAS`).

| Opção | Conteúdo |
|---|---|
| `base` | `{"municipios": {"todos", "estados", "ids"}}`, como no painel |
| `estados_unidade` | os estados como unidade (prefixos IBGE) |
| `conjuntos` | `[{"id", "rotulo", "membros", "versao"?}]`; membros do mesmo nível (`code:<IBGE>` ou `uf:<prefixo>`) |
| `janela` | `{"inicio", "fim"}`, competências da base; sem ela, a série inteira |
| `parametros` | os critérios trocados, por grupo: `estrutural` (`critico`, `elevado`, `moderado`), `declinio` (`<nível>_quedas`, `<nível>_perda`), `desaceleracao` (`anos`), `instabilidade` (`moderado_um_em`), `perda` (`<nível>_um_em`, `<nível>_minimo`, `<nível>_fracao`), `patamar` (`moderado`, `critico`, `minimo`, `elevado_um_em`, `critico_um_em`), `disponibilidade`, `posicao` e `defasagem` (`<nível>_um_em`) e `contexto` (`taxa_do_brasil_pct`); a resposta vem com `exploratorio: true` |
| `detalhe` | o id de um território da seleção: a resposta traz `territorio`, `linha`, `serie`, `historico`, `comparativo`, `coordenadas` e `fenomenos`, no lugar da lista |
| `perfil` | `true`: a resposta traz só `versao`, `fonte` e `perfil` (o perfil da base, com `itens`, `da_para`, `nao_da_para`, `regua`, `tem`, `nomes` e `avisos`); não pede seleção |
| `rotulos`, `premissas`, `categoria` | só com uma planilha: os nomes do painel "Colunas", as premissas confirmadas e a categoria, como no pedido de `/api/painel` |

A lista responde (versão `DETECTOR-SINAIS/V3/1`) com `versao`, `fonte` (com `rotulos`, os nomes da base), `janela`,
`competencias`, `parametros` (`padrao`, `em_uso`, `personalizados`, `editaveis`), `niveis` (o "1 em cada N" e as comparações que
cada nível pede), `grupos` (os grupos dos sinais), `portes`, `entenda` (os textos da primeira tela), `linhas`, `resumo`
(`niveis`, um nível por território; `com_nivel`, quantos territórios têm nível em cada sinal), `calibracao` (a régua da data: por
porte, as `comparacoes` do próprio porte e, em cada nível, a régua usada de fato — `um_em`, `pede`, `avaliado`, `origem`
(`porte`, `vizinhas` ou `todas`: de onde vêm as comparações; sem comparações bastantes, a origem mais larga que foi tentada),
`comparacoes` (quantas são) e `queda_pct` — ou `afastamento_pct`, no sinal 7; com `origem: todas`, o corte muda com o tamanho, e
`queda_pct` e `queda_pct_ate` trazem os dois extremos da faixa; e o `monitoramento`, com `aviso_da_base`),
`calibracao_dos_estados` (quando a seleção tem estados como unidade), `aviso_da_base`, `comparacao` (a janela dos sinais 8 a 10,
o estado dela, os trechos de população comparável e o critério da distância), `coordenadas`, `sem_coordenada` (as unidades da
seleção que ficam fora do mapa: `id` e `motivo`, `ausente` ou `fora_do_intervalo`), `complemento_geografico` (desde a revisão
final do V23: na base do Brasil, o estado, a identidade e a proveniência da camada oficial de coordenadas, como nas análises
espaciais, e `territorios_complementados`, os territórios desta resposta cujo ponto veio dela; `null` numa planilha; também no
detalhe), `notas` e `limitacoes`. Desde o comando V23, `fonte` traz também `origem` (`brasil` ou `planilha`), `ancora` (o mês da série anual; `00` com
um registro por ano), `tem` (`populacao`, `coordenadas`, `grupo` e `serie_anual`) e `formas` (os nomes com artigo e preposição:
"o município", "a comuna", "do Brasil"); e a lista traz `indisponiveis` (sinal → motivo; vazio na base do Brasil; desde
15/11/2026, com todos os motivos do sinal, um depois do outro). Com população ausente, `comparacao.estado` é `indisponivel`, com
o `motivo`.

Em cada linha:

- `alerta`: `estado` (`alerta`, `sem_alerta`, `sem_comparacoes` ou `sem_nivel`), `nivel`, `sinal` (o principal), `criterio`,
  `outros`, `por_que`, `sinais` (cada sinal com nível: `sinal`, `nivel`, `criterio`), `mesma_queda`, `sem_comparacoes` (os sinais
  comparados com a base que ficaram sem comparações) e `motivo` (no conjunto);
- os campos de cada sinal, com `estado` e `classe` (o nível daquele sinal): `estrutural`, `perda`, `patamar`, `declinio`,
  `desaceleracao`, `instabilidade`, `disponibilidade`, `posicao`, `defasagem`, `contexto` e `coexistencia`; `registro`; `ultima`;
  `porte`; num conjunto, `ids_dos_membros`; num município que mudou de nome, `nomes_anteriores`. Nos sinais 8 a 10, o `estado`
  pode ser `descontinuidade_de_registro` (a janela começa ou termina num registro marcado); no detalhe, `territorio.<sinal>.marca`
  diz qual (`tipo`: `pico_que_volta` ou `quebra_de_fonte`; `ponta`: `inicio` ou `fim`; `competencia`). No sinal 3,
  `declinio.registros_anuais` (desde 15/11/2026) é o número de registros da série anual na janela, com um nome que vale para
  qualquer base; `declinio.junhos`, o nome de antes, continua na resposta, com o mesmo número.

No detalhe, cada item de `fenomenos` traz `chave`, `numero`, `nome`, `grupo`, `nivel`, `estado_do_nivel` (`alerta`,
`sem_alerta`, `sem_comparacoes`, `sem_nivel`, `sem_dado`, `nao_avaliado`, `contexto`, `juntos` ou `indisponivel` — o sinal que a
base não sustenta, com o motivo em `observado`), `criterio_do_nivel`,
`exploratorio`, `situacao` (a frase), `entenda` (`texto` e `exemplo`), `sem_comparacoes` (os níveis que a base não sustenta, com
`comparacoes`, `pede` e `texto`) e os sete campos da explicação completa.

**Os campos que a resposta já trazia continuam**, com os valores da V3: `classe` (agora `moderado`, `elevado` ou `critico`);
`sinal`, nos sinais 3 e 8 a 10 (repete o nível); `patamar.critica` (`sem_comparacoes` quando os 4 últimos registros cumprem o
limite do crítico e a base não tem comparações para ele); `estado` e `classe` em cada item de `fenomenos`; e, na régua da data,
`transicoes`, `queda_incomum_pct` e `queda_muito_incomum_pct` (os cortes do elevado e do crítico), `observacoes`,
`afastamento_incomum_pct`, `alta` e `critica` (`calibrado` ou `sem_calibracao`) e `monitoramento.incomuns` (o mesmo que `raras`).
Desde 14/11/2026, os cortes e `alta` e `critica` seguem a régua usada de fato (com as faixas vizinhas, quando o porte não basta):
um nível que o motor avalia com as vizinhas deixa de aparecer como `sem_calibracao`.
Os nomes dos critérios em `parametros` são os da tabela acima; um nome antigo (`perda.alta_alfa`) é recusado como desconhecido.

As limitações `RARO_E_INCOMUM_NA_BASE`, `CONJUNTO_SEM_NIVEL` e `COMPARACAO_SO_COM_POPULACAO_COMPARAVEL` acompanham toda resposta;
`CONFIGURACAO_EXPLORATORIA`, a que usa critérios diferentes do padrão. Erros de pedido vêm em 422, com o texto em português
(seleção vazia, território fora da base, competência fora da base, critério fora do intervalo ou fora de ordem — o nível mais
grave não pode ser mais comum que o menos grave). Sem base nenhuma, a rota responde "Escolha a base do Brasil ou envie uma
planilha: a ferramenta lê a base que estiver em uso." Com uma planilha, valem também as recusas do portão das análises (a coluna
territorial, o período e a contagem; as premissas pendentes voltam em `pendencia`, como em `/api/painel`) e as das datas.

A seleção segue o contrato compartilhado das ferramentas (`series_brasil.selecao`): o estado como unidade (ou num conjunto de
estados) e os municípios dele não entram juntos (RQ-DAD-30); um conjunto reúne territórios do mesmo nível. Numa planilha, os
identificadores são `code:<código>` (com a coluna de código) ou `name:<nome>`; o grupo de cima vai em `estados_unidade` pelo valor
da coluna de grupo e volta como o território `uf:<valor>` (desde 15/11/2026; antes, era recusado).

## Calibração

Estudo de 13/11/2026, refeito em 14/11/2026 (depois da revisão das capturas) e em 15/11/2026 (com a tabela do sinal 7 só entre
as avaliações em que o elevado e o crítico podiam sair; os demais números não mudaram), com a base versionada e a população nova
(`scripts/calibrar_detector.py`, somente leitura; versão da base `faa54169c5b6`, método `DETECTOR-SINAIS/V3/1`). Cada data é
avaliada só com as mudanças anteriores a ela, e as descontinuidades de registro já conhecidas ficam fora do passado, como no
produto. Na revisão, os sinais 8 a 10 deixaram de usar janelas com um registro marcado numa ponta: só os números desses três
sinais e os de jun/2024 mudaram.

**A régua da queda recente, só pela raridade** (sem o tamanho mínimo; com ele, há menos alertas). Municípios, 105.786 mudanças
avaliadas:

| Porte | Moderado (meta 5%) | Elevado (meta 1%) | Crítico (meta 0,1%) |
|---|---:|---:|---:|
| 1 a 3 | 2,53% | 0,55% | 0,00% |
| 4 a 9 | 4,14% | 0,78% | 0,05% |
| 10 a 19 | 4,67% | 0,77% | 0,09% |
| 20 a 49 | 4,97% | 1,06% | 0,11% |
| 50 a 99 | 5,95% | 1,35% | 0,20% |
| 100 a 299 | 5,45% | 1,09% | 0,14% |
| 300 a 999 | 5,13% | 1,08% | 0,12% |
| 1.000 a 2.999 | 4,40% | 0,90% | 0,00% |
| 3.000 a 9.999 | 4,88% | 0,75% | sem comparações suficientes |
| 10.000 ou mais | 3,19% (94 avaliações) | 0,00% (64 avaliações) | sem comparações suficientes |
| **Todos** | **4,50%** | **0,88%** | **0,08%** |

Os números batem com os da Proposta V3 (tabelas A.5 e B.1), com diferenças abaixo de 1 ponto. De 3.000 médicos para cima, a base
não tem 999 comparações de tamanho parecido: o crítico fica "sem comparações suficientes".

**Estados como unidade** (régua própria, 567 mudanças): moderado desde jun/2015, em 7,2% de 513 avaliações (meta 5%; a proposta
mediu 6,7% em 510, sem as marcas de descontinuidade); elevado desde jun/2019, nenhum alerta em 275 avaliações; crítico nunca (em
jun/2024, os estados têm 270 comparações, e o crítico pede 999). O moderado dos estados fica um pouco acima da meta. **Decisão do
responsável (15/11/2026, Pausa 2): o moderado dos estados continua em 1 em cada 20**; os 7,2% em 513 avaliações ficam
registrados aqui e na Parte F da [Proposta V3](DETECTOR_E_SIMULADOR_V3.md).

**Alertas de cada sinal, em todas as datas** (municípios, critérios padrão):

| Sinal | Avaliações | Moderado | Elevado | Crítico | Algum nível |
|---|---:|---:|---:|---:|---:|
| 1–2 Poucos médicos ou nenhum | 116.964 | 12,07% | 10,78% | 1,81% | 24,67% |
| 3 Declínio persistente | 105.822 | 3,97% | 0,59% | 0,10% | 4,66% |
| 4 Desaceleração | 83.546 | 0,21% | — | — | 0,21% |
| 5 Instabilidade | 63.085 | 5,58% | — | — | 5,58% |
| 6 Queda recente | 114.293 | 2,95% | 0,71% | 0,07% | 3,73% |
| 7 Abaixo do que já teve | 30.358 | 5,90% | 0,98% | 0,04% | 6,92% |
| 8 Menos médicos por habitante | 30.276 | 2,63% | 0,73% | 0,09% | 3,45% |
| 9 Perda de posição | 30.276 | 5,09% | 1,11% | 0,08% | 6,28% |
| 10 Perda em relação à referência | 30.267 | 3,56% | 0,80% | 0,09% | 4,45% |

Leitura: os sinais comparados com a base ficam perto das metas (5%, 1% e 0,1%). O crítico do sinal 7 (0,04%) fica perto da meta
de 0,1% e passa a valer onde há 999 comparações. O sinal 3, por convenção, fica perto do que a raridade daria. Os sinais 1 e 2 são
uma convenção sobre o número de profissionais: um quarto das avaliações municipais tem 5 médicos ou menos.

**Sinal 7, o elevado e o crítico só entre as avaliações em que eles podiam sair** (conferência pedida pelo responsável em
15/11/2026, na Pausa 2). A tabela acima divide os alertas por todas as 30.358 avaliações do sinal; esta conta só as que tinham
as comparações que o nível pede, no porte do patamar ou com as faixas vizinhas:

| Nível | Comparações que pede | Avaliações em que podia sair | Alertas | Taxa | Meta |
|---|---:|---:|---:|---:|---:|
| Elevado (ou crítico) | 99 | 28.507 | 310 | 1,09% | 1% |
| Crítico | 999 | 27.570 | 11 | 0,04% | 0,1% |

Com o denominador certo, o crítico continua em 0,04% (11 de 27.570), dentro do teto de 0,1%: **o crítico do sinal 7 continua**
(decisão do responsável). O elevado, contado junto com o crítico, fica em 1,09%, pouco acima da meta de 1%.

**Em jun/2024** (5.570 municípios): 40 críticos, 436 elevados, 978 moderados e 4.116 sem alerta (antes da revisão: 41, 434, 977
e 4.118). Com algum alerta: 1.454 municípios, 26,1%; com algum alerta **comparado com a base**: 9,9% (o restante vem dos sinais
por convenção, sobretudo "Poucos médicos"). Ao longo das datas, a parcela com algum alerta comparado com a base vai de 3,2% a
11,4%; a parcela com **algum alerta**, contando os por convenção, fica acima dos cerca de 20% que a Proposta V3 (Parte F) põe
como sinal para rever o padrão (26,1% em jun/2024). **Decisão do responsável (15/11/2026, Pausa 2): o limite de cerca de 20% vale
para os alertas comparados com a base** (9,9% em jun/2024), e o padrão de 1 em cada 20 continua; os dois números (26,1% e 9,9%)
ficam registrados aqui e na Parte F da Proposta V3. Nesta data, 2,89% dos municípios tiveram uma queda rara (esperado: cerca de
5%), sem aviso da base. Dos 27 estados como unidade, 3 têm moderado e 24, nenhum alerta.

**Municípios com alerta em jun/2024, por sinal e por nível.** Um município pode ter nível em mais de um sinal: as linhas não se
somam. O "sinal principal" é o de maior nível (no empate, o primeiro na ordem dos sinais).

| Sinal | Moderado | Elevado | Crítico | Com nível no sinal | É o sinal principal do alerta |
|---|---:|---:|---:|---:|---:|
| 1–2 Poucos médicos ou nenhum | 446 | 332 | 23 | 801 (14,4%) | 799 (14,3%) |
| 3 Declínio persistente | 131 | 21 | 3 | 155 (2,8%) | 115 (2,1%) |
| 4 Desaceleração | 16 | 0 | 0 | 16 (0,3%) | 16 (0,3%) |
| 5 Instabilidade | 260 | 0 | 0 | 260 (4,7%) | 196 (3,5%) |
| 6 Queda recente | 129 | 23 | 3 | 155 (2,8%) | 99 (1,8%) |
| 7 Abaixo do que já teve | 105 | 28 | 3 | 136 (2,4%) | 92 (1,7%) |
| 8 Menos médicos por habitante | 74 | 30 | 3 | 107 (1,9%) | 22 (0,4%) |
| 9 Perda de posição | 134 | 41 | 5 | 180 (3,2%) | 72 (1,3%) |
| 10 Perda em relação à referência | 99 | 31 | 4 | 134 (2,4%) | 43 (0,8%) |
| **Território: o maior nível entre os sinais** | 978 | 436 | 40 | **1.454 de 5.570 (26,1%)** | — |

Mais da metade dos municípios com alerta (799 de 1.454) tem como sinal principal "Poucos médicos ou nenhum", que é uma convenção
sobre o número de profissionais, e não uma comparação com a base.

**Sinal 8, os limites que a raridade dá em jun/2024** (a queda da taxa por habitante em 2 anos, por porte no início da janela).
Cada nível mostra a régua usada de fato: o porte ou, quando ele não tem comparações bastantes, o porte com as faixas vizinhas.

| Porte | Variações anteriores do porte | Moderado: queda maior que | Elevado | Crítico |
|---|---:|---:|---:|---:|
| 20 a 49 | 7.703 | 25,4% | 40,9% | 73,5% |
| 50 a 99 | 3.109 | 19,7% | 36,8% | 73,8% |
| 100 a 299 | 2.871 | 16,5% | 32,0% | 78,7% |
| 300 a 999 | 1.460 | 10,4% | 22,2% | 42,1% |
| 1.000 a 2.999 | 470 | 4,5% | 13,8% | 41,7% (com as faixas vizinhas: 2.081) |
| 3.000 a 9.999 | 151 | 1,5% | 20,8% | sem comparações suficientes (652 de 999, com as faixas vizinhas) |
| 10.000 ou mais | 31 | 6,2% | 20,8% (com as faixas vizinhas: 182) | sem comparações suficientes (182 de 999, com as faixas vizinhas) |
| Todas as janelas e portes juntos | 15.795 | 21,5% | 37,9% | 68,6% |

Com todos os portes juntos, os cortes ficam perto dos que a Proposta V3 estimou com a população anterior (23%, 38% e 60%).

**A régua de jun/2024 e o monitoramento da data** (os números da seção 13 da Ficha A, "A régua da data e o monitoramento"),
como saem de:

    python scripts/calibrar_detector.py --regua-da-data 202406

Base versionada `faa54169c5b6`, método `DETECTOR-SINAIS/V3/1`, critérios padrão. Cada nível mostra a régua usada de fato: quando
o porte não tem comparações bastantes, ela junta as faixas vizinhas (uma de cada lado) e, só no moderado, todas as faixas — a
célula diz de onde vieram as comparações e quantas são.

Queda recente (sinal 6), municípios, com as mudanças anteriores de 5 meses entre registros: a partir de que queda ela é rara, por
porte (o número de médicos antes).

| Porte (médicos) | Comparações do porte | Moderado (1 em cada 20) | Elevado (1 em cada 100) | Crítico (1 em cada 1.000) |
| --- | --- | --- | --- | --- |
| 1 a 3 | 6.572 | queda maior que 33,3% | queda maior que 50,0% | nenhuma queda chega a esse nível |
| 4 a 9 | 16.650 | queda maior que 25,0% | queda maior que 42,9% | queda maior que 75,0% |
| 10 a 19 | 12.035 | queda maior que 21,4% | queda maior que 36,8% | queda maior que 58,8% |
| 20 a 49 | 9.958 | queda maior que 17,1% | queda maior que 31,3% | queda maior que 56,4% |
| 50 a 99 | 3.969 | queda maior que 13,6% | queda maior que 29,4% | queda maior que 64,8% |
| 100 a 299 | 3.708 | queda maior que 10,0% | queda maior que 26,3% | queda maior que 52,4% |
| 300 a 999 | 1.901 | queda maior que 5,9% | queda maior que 17,3% | queda maior que 45,4% |
| 1.000 a 2.999 | 616 | queda maior que 2,5% | queda maior que 11,3% | queda maior que 44,4% (com as faixas vizinhas: 2.720 comparações) |
| 3.000 a 9.999 | 203 | queda maior que 2,2% | queda maior que 7,6% | sem comparações suficientes (864 de 999, com as faixas vizinhas) |
| 10.000 ou mais | 45 | queda maior que 1,3% | queda maior que 7,6% (com as faixas vizinhas: 248 comparações) | sem comparações suficientes (248 de 999, com as faixas vizinhas) |

Abaixo do que já teve (sinal 7), municípios: a partir de que afastamento do patamar ele é raro, por porte do patamar (os
afastamentos anteriores de todas as datas).

| Porte (médicos) | Comparações do porte | Elevado (1 em cada 100) | Crítico (1 em cada 1.000) |
| --- | --- | --- | --- |
| 20 a 49 | 13.942 | afastamento maior que 39,5% | afastamento maior que 62,2% |
| 50 a 99 | 5.321 | afastamento maior que 37,8% | afastamento maior que 68,2% |
| 100 a 299 | 5.109 | afastamento maior que 31,3% | afastamento maior que 76,1% |
| 300 a 999 | 2.552 | afastamento maior que 20,9% | afastamento maior que 34,9% |
| 1.000 a 2.999 | 806 | afastamento maior que 3,8% | afastamento maior que 31,3% (com as faixas vizinhas: 3.614 comparações) |
| 3.000 a 9.999 | 256 | afastamento maior que 17,5% | afastamento maior que 19,6% (com as faixas vizinhas: 1.116 comparações) |
| 10.000 ou mais | 54 | afastamento maior que 9,9% (com as faixas vizinhas: 310 comparações) | sem comparações suficientes (310 de 999, com as faixas vizinhas) |

Queda recente (sinal 6), estados como unidade: a régua própria, com a base dos estados (só as faixas com comparações).

| Porte (médicos) | Comparações do porte | Moderado (1 em cada 20) | Elevado (1 em cada 100) | Crítico (1 em cada 1.000) |
| --- | --- | --- | --- | --- |
| 300 a 999 | 25 | queda maior que 9,6% | sem comparações suficientes (47 de 99, com as faixas vizinhas) | sem comparações suficientes (47 de 999, com as faixas vizinhas) |
| 1.000 a 2.999 | 22 | qualquer queda | queda maior que 9,6% (com as faixas vizinhas: 169 comparações) | sem comparações suficientes (169 de 999, com as faixas vizinhas) |
| 3.000 a 9.999 | 122 | qualquer queda | queda maior que 7,4% | sem comparações suficientes (245 de 999, com as faixas vizinhas) |
| 10.000 ou mais | 101 | qualquer queda | queda maior que 1,5% | sem comparações suficientes (223 de 999, com as faixas vizinhas) |

Monitoramento: nesta data, 161 de 5.570 municípios tiveram uma mudança rara (1 em cada 20) no último registro: 2,9%, para um esperado de cerca de 5%; sem aviso da base (ele vale acima do triplo do esperado, com 100 avaliações ou mais).

O teste com dados reais de jun/2024 (`backend/tests/test_detector.py`) confere estes números com o motor: as três tabelas, célula
por célula, e as 161 raras entre 5.570 avaliadas.

**Sinal 11, o contexto em cada registro anual** (critério: a taxa do Brasil na data): em jun/2024, a taxa é de 2,36 por 1.000;
2.002 municípios ficam acima do critério e 3.568 têm distância a mostrar (mediana de 27,1 km; percentil 90, 112,1 km; maior,
838,6 km). Em jun/2014, eram 1,60 por 1.000, 1.565 municípios acima e mediana de 32,5 km. Com as coordenadas da camada oficial
(revisão final do V23), os seis municípios entram nesta conta: em jun/2024, quatro deles ficam acima do critério (e passam a ser
o município mais próximo de três vizinhos) e dois têm distância (Ananás/TO, a 30,9 km de Luzinópolis; Balneário Rincão/SC, a
15,3 km de Içara) — antes, 3.566 municípios com distância e percentil 90 de 112,2 km. A distância é em linha reta: não é
distância por estrada, tempo de viagem nem acesso.

**O que continua sendo convenção:** os limites dos sinais 1 a 4, o tamanho mínimo do sinal 6, os 15% e os 30% do sinal 7, o
mínimo de 20 no patamar e nos sinais 8 a 10 e o critério do pico que volta. Todos podem ser trocados, como configuração
exploratória.

## A malha das divisas

O arquivo da malha é versionado na interface, em `frontend/public/malha/` (não vai para o contêiner do motor), e é pedido pelo
navegador só quando o mapa do Detector abre:

- `municipios-ibge-qualidade-minima.json`: a malha municipal do Brasil, em TopoJSON (objeto `BRMU`), como veio do IBGE, byte a
  byte — 1.428.796 bytes, 5.570 geometrias, identificadas por `codarea` (7 dígitos: os 6 primeiros são o código do município
  na base);
- `fonte.json`: a fonte (a API de malhas geográficas do IBGE, v3:
  `https://servicodados.ibge.gov.br/api/v3/malhas/paises/BR?formato=application/json&qualidade=minima&intrarregiao=municipio`),
  a data da consulta (15/11/2026), o tamanho e o **SHA-256**
  (`b509836495fa76a9adf620a2a5c57b462b745bbb0613e9d98cc1123d494edc21`).

**Conferência:** os 5.570 códigos da base versionada têm divisa, e a malha não tem geometria além deles (nenhuma lagoa ou área
sem município nesta versão); o teste do job `dados-reais` confere isso, e o teste Node, o tamanho e o SHA-256 do arquivo. As
divisas dos estados não são outro arquivo: são os trechos da malha municipal entre municípios de estados diferentes, mais a borda
do país (1.669 trechos). `frontend/src/malhaModel.ts` lê o arquivo e monta o que o mapa desenha. Para atualizar a malha, troque
o arquivo sem alterar os bytes do IBGE, regrave `fonte.json` e registre a mudança (regras 1 e 2 do `AGENTS.md`).

## Limitações

- O registro mais recente da base é jun/2024: nenhum sinal descreve a situação de hoje.
- "Raro" quer dizer incomum nesta base, não comprovadamente pior. O nível não é juízo de desassistência, de suficiência do
  atendimento nem de prioridade.
- A contagem municipal é a de médicos registrados no município: quem atua em mais de um conta em cada um. Um conjunto é a soma das
  contagens dos componentes, nunca "médicos únicos", e não tem nível.
- O Detector não infere rotatividade de pessoas, desassistência, isolamento assistencial, suficiência do cuidado nem causa.
- A base dos estados é pequena: o crítico nunca tem comparações suficientes, e o elevado só desde jun/2019.
- De 3.000 médicos para cima, os municípios não têm comparações suficientes para o crítico, nem com as faixas vizinhas (em
  jun/2024: 864 e 248 comparações na queda recente; 652 e 182 nos sinais 8 a 10). De 10.000 para cima, o elevado é avaliado com
  as faixas vizinhas (o próprio porte tem 45 comparações na queda recente e 31 nos sinais 8 a 10).
- **Seis municípios usam a coordenada da camada oficial:** a base traz a latitude ou a longitude deles fora do intervalo válido,
  em todas as datas (Ananás/TO, Águas de Lindóia/SP, Pescaria Brava/SC, Balneário Rincão/SC, Campestre da Serra/RS e
  Jaraguari/MS). Desde a revisão final do comando V23 (15/11/2026, decisão do responsável), o Detector e o Simulador leem as
  coordenadas como as análises: nesses seis, vale a sede municipal da camada oficial do IBGE
  (`dados/brasil/complemento_coordenadas.json`), uma coordenada fixa nas 22 datas, por premissa do responsável. O arquivo da base
  não foi alterado. Eles têm ponto no mapa, a distância deles (sinal 11) é medida dessa coordenada, e eles podem ser o município
  mais próximo de um vizinho; a legenda do mapa e a explicação completa do sinal 11 dizem quando o ponto veio da camada. Com
  outra versão da fonte municipal, a camada não é aplicada (`complemento_geografico.estado: incompativel`), e esses municípios
  ficam fora do mapa, com o motivo. Uma planilha nunca recebe a camada.
- A variação em 2 anos (sinais 8 a 10) só existe em trechos com população comparável, lidos da própria base. A população é uma
  estimativa, e a taxa de um estado usa a contagem estadual sobre a soma das populações municipais.
- A distância (sinal 11) é em linha reta entre coordenadas: não mede acesso, deslocamento nem a organização da rede.
- **As divisas do mapa são só desenho:** a malha municipal do IBGE em qualidade mínima é simplificada (serve para situar, não
  para medir), e nenhuma área, distância ou valor é calculado com ela. Ela existe só para a base do Brasil: numa planilha, o
  mapa segue sem divisas, com os pontos pelo nível e o nome do grupo de cima junto aos pontos dele.
- O histórico de sinais cobre os sinais 1 a 7.
- Numa planilha enviada, o grupo de cima como unidade é a soma das unidades dele (a planilha não tem a contagem própria do
  grupo): não é o número de pessoas diferentes do grupo, e só existe nas datas em que todas as unidades dele têm registro. A
  régua dos grupos é montada com poucos territórios. O que a planilha não tem (população, coordenadas, grupo de cima ou série
  anual) deixa os sinais que dependem disso indisponíveis, com o motivo.

## Testes

- pytest: `backend/tests/test_reguas.py` — a régua comum (as dez faixas, a raridade com o "+1" e os empates, os mínimos, a
  retaguarda pelas vizinhas e, só no moderado, por todas as faixas com a mudança padronizada, e θ só com o passado);
  `backend/tests/test_detector.py` — os sinais em séries sintéticas (os níveis por convenção e a histerese; zero e ausência; a
  queda rara com os empates, só o passado, o tamanho mínimo e as comparações mínimas; a retaguarda; o pico que volta, a quebra
  de fonte e a queda grande que persiste; o patamar; o declínio; a desaceleração igual à classe da Análise de Tendência; a
  instabilidade; a régua própria dos estados e os conjuntos sem nível; os critérios ajustáveis; um nível por território e os
  efeitos da mesma queda; os sinais 8 a 10 pela raridade; a distância; os sinais juntos; os textos, com o "Entenda" de duas ou
  três frases; e, da revisão das capturas de 14/11/2026, os sinais 8 a 10 sem registro de pico ou de quebra de fonte nas pontas
  da janela, a régua da data conferida com o motor território a território — com as faixas vizinhas e com todas as faixas —, o
  patamar com decimal, o sinal 10 em palavras simples e quem fica fora do mapa, com o motivo; da revisão de 15/11/2026, a frase
  do sinal 7 não avaliado com o motivo, a do sinal 11 com o território de referência e a posição da distância, e
  `registros_anuais` ao lado de `junhos`), a rota com um catálogo sintético
  e, no job `dados-reais`, a base versionada (Brochier/RS sem alerta, a régua usada de fato, as coordenadas pela camada oficial —
  os 5.570 pontos, as 22 datas dos seis municípios, a distância de Ananás e de Balneário Rincão refeita por fora e os vizinhos que
  passam a ter um deles como o mais próximo —, o motivo na frase dos sinais não avaliados (e, em
  `backend/tests/test_geo_complement.py`, a base das ferramentas com a camada ausente, válida e de outra versão da fonte), as
  taxas da régua por nível e por porte, a régua dos estados, a lista inteira com um nível por território (desde o AJ-20, de
  18/11/2026, também o monitoramento de jun/2024 — 161 quedas raras entre 5.570 municípios avaliados — e as três tabelas da régua
  de jun/2024 da Ficha A e da seção "Calibração", célula por célula), Rio Rufino/SC, o
  Distrito Federal antes de 2018, uma queda grande que persiste, a desaceleração igual à da Análise de Tendência e os sinais 8
  a 12 com a população comparável);
  `backend/tests/test_ferramentas_qualquer_base.py` — o calendário lido da base (o mês da série anual, os meses de registro e os
  tipos de intervalo), a base montada de uma planilha (a planilha de teste `planilha_das_ferramentas.csv`, 20 distritos
  fictícios de seis em seis meses durante 10 anos, sem grupo e sem população; uma planilha com código, grupo, população e
  coordenadas; as datas aceitas e as recusas), o Detector e o perfil com a planilha (os níveis que ela sustenta, "Indisponível
  nesta base" e "sem comparações suficientes" com os números, a planilha só com anos, nenhum vocabulário da base do Brasil; os
  sinais indisponíveis com todos os motivos, iguais no detalhe e no perfil; e o nome dos trabalhadores informado no envio, com
  os nomes que valem e os que ficam com "profissionais"), a rota com o arquivo e, no job `dados-reais`, o perfil da base do
  Brasil.
- Node: `frontend/tests/detector.test.mjs` — a leitura da resposta, a lista de cinco colunas com um sinal por linha (AJ-04: a
  ordem dos sinais, a frase do principal sem "(+N sinais)" e a dos outros do detalhe, a linha única sem sinal, o detalhe pedido
  só para quem tem mais de um sinal, dois de cada vez, e os cartões do celular), a memória dos detalhes por pedido (AJ-08: só os
  que chegaram certos, só com a lista guardada e no mesmo limite dela; a resposta de outro pedido fora da lista à vista) e o
  cabeçalho numa linha só na lista do Detector, sem mudar as regras das outras tabelas, o resumo dos níveis, os filtros, a ordem, os
  critérios em frases (todos os parâmetros do motor, uma vez cada), a régua da data, o monitoramento e as versões na exportação
  do método (AJ-03; o teste da régua em palavras saiu com a tabela da tela), os "Entenda" dos cabeçalhos e as ressalvas da lista,
  o nome do sinal no detalhe e no histórico, as exportações, o mapa e o gráfico pelos níveis, com a dica do sinal, quem fica fora do mapa,
  quem está nele com a coordenada da camada oficial, o
  que o Detector leva ao Simulador, o "Entenda" (mouse, toque e teclado), qualquer base (o que a base
  tem, os sinais indisponíveis, as datas só com ano, a concordância e o perfil da base) e a série do território na largura da
  tela, com as datas da série da taxa como nos outros gráficos;
  `frontend/tests/fichas.test.mjs` — o endereço das fichas na base da página, com a seção pelo destino nomeado, os dois PDFs nos
  arquivos estáticos e o link das duas ferramentas, numa nova aba;
  `frontend/tests/modoEscuro.test.mjs` — o contraste dos níveis no modo escuro;
  `frontend/tests/malha.test.mjs` — a malha das divisas: a leitura do TopoJSON (com uma malha pequena feita à mão), as divisas a
  desenhar (as áreas com a cor do nível, as dos estados sempre, as dos municípios ao aproximar ou com um estado só), o pedido
  único do arquivo, o arquivo versionado (o tamanho, o SHA-256 e os 5.570 municípios) e a tela.
- pytest, no job `dados-reais`: `backend/tests/test_detector.py` confere que cada município da base tem divisa na malha
  versionada e que a malha não tem geometria além deles.
- pytest: `backend/tests/test_fichas_metodologicas.py` — os dois PDFs das fichas são válidos, com título, idioma pt-BR, tags,
  sumário, texto selecionável e os destinos nomeados de todas as seções (inclusive as que a página abre), e correspondem às
  fontes atuais (a impressão digital SHA-256 da fonte e do estilo); desde o AJ-06, o texto à vista sem o bastidor do
  desenvolvimento (as marcas de estado, os caminhos, as rotas e os campos da API, os códigos, os hashes, "motor", "código",
  "página", "por convenção", "jeito" e o nome antigo do sinal 10), as seções do comando na ordem, com o id de antes, a abertura
  com a versão do método, os textos novos do sinal 10 e da mesma queda, a letra estática das fichas com a do site intocada, nenhuma
  fonte Type 3 nos PDFs e as propriedades do PDF (assunto, palavras-chave e aplicativo) sem caminhos e sem SHA-256.
- Navegador: `backend/tests/ui_detector.py` (suíte `base-versionada`) — a lista de cinco colunas, o resumo clicável, os filtros
  e a ordem; o cabeçalho numa linha a 1366 px, sem rolagem horizontal (AJ-08); ABELARDO LUZ (SC), com quatro sinais de dois
  níveis, uma linha por sinal, com os nomes do filtro e o nível, o
  critério e a frase de cada um, das respostas reais da lista e do detalhe; o detalhe com os quatro grupos, o nome do sinal no
  alto e no histórico, o "Entenda" por mouse e teclado e a explicação completa; os critérios em frases e a configuração
  exploratória, com a memória dos detalhes (AJ-08: voltar ao padrão sem pedir de novo as frases que já chegaram; o detalhe
  que falhou, pedido de novo ao voltar ao pedido dele, com as frases da resposta nova); a ficha metodológica (o link e o "Ver explicação completa", com o PDF servido pela interface), os "Entenda" dos
  cabeçalhos e as ressalvas; a régua por porte e o monitoramento em "Exportar o método (JSON)", campo a campo com a resposta do
  motor, com a régua usada de fato em cada nível; o estado como unidade, com a régua dos estados na exportação; a dica do mapa e
  do gráfico; o mapa (com os dois
  municípios de Santa Catarina fora dele, ditos na legenda) e o gráfico; os sinais comparados em jun/2021; "Simular
  recuperação"; a tela de celular, com o "Entenda" pelo toque, a lista em cartões, a série do território desenhada na largura
  da tela (texto de 12 px) e o mapa na largura da tela, com as divisas; o mapa com as divisas dos estados, as dos municípios de
  Santa Catarina e as áreas com a cor do nível; e o perfil da base do Brasil, fechado até a pessoa pedir.
  `backend/tests/ui_detector_mapa.py` (mesma suíte) — o mapa com municípios de dois estados à vista (Santa Catarina e Roraima):
  as divisas dos estados sem as dos municípios; "Aproximar o mapa em", que enquadra o estado com as divisas dos municípios dele
  sem cortar as áreas com nível; um estado só à vista pela busca; e a malha pedida uma vez só, quando o mapa abre.
  Desde a revisão final do V23, o mesmo roteiro confere o Brasil inteiro: os 5.570 pontos, a nota das seis coordenadas da camada
  oficial e as siglas dos 27 estados sem sobreposição (`frontend/tests/mapa.test.mjs` confere a função que as afasta).
  `backend/tests/ui_planilha_de_teste.py` (suíte `bloco1`, desde a revisão final do V23) — os nomes da base, com a planilha de
  teste: 49 paradas no Detector e no Simulador (o modo simples, as quatro etapas do avançado, os "Entenda" e, desde o AJ-03,
  os "Entenda" dos cabeçalhos da lista no lugar de "Como foi calculado") sem "junho",
  "médicos" nem as outras palavras da base do Brasil, e com "julho" e "enfermeiros" nos mesmos lugares.
  `backend/tests/ui_planilha_ficticia.py` (suíte `bloco1`) — o mapa com a comuna sem coordenada fora dele, e o Detector com uma planilha enviada: o perfil aberto
  antes da ferramenta, a lista e o detalhe com os nomes da planilha e o Simulador desligado, com o motivo.
