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
   critério**: "comparado com a base" ou "por convenção".

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
  dela.
- **Um nível por território:** o maior entre os seus sinais. Não há soma nem índice. Os sinais que vêm da mesma queda (queda
  recente, declínio, abaixo do que já teve e os três comparados com outros) contam como **um evento**, e a tela diz isso.
- **Aviso da base:** quando, numa mesma data, os territórios com queda rara passam do triplo do esperado (mais de 15%, com 100
  avaliações ou mais), a tela avisa que pode ter havido mudança no registro da base, e não nos territórios.
- **Estados como unidade:** têm régua própria, com a base dos estados (as contagens estaduais). É uma base pequena: os níveis
  mais graves podem ficar sem comparações suficientes.
- **Conjuntos:** sem nível. A tela mostra os fatos e o motivo.

## Os 12 sinais

Todos os limites são padrões e podem ser trocados em "Ajustar critérios" (a configuração passa a ser exploratória).

| # | Sinal | O que mede | Moderado | Elevado | Crítico | Critério |
|---|---|---|---|---|---|---|
| 1 | Poucos profissionais | Número no último registro | 4 ou 5 | 2 ou 3 | 1 | Por convenção |
| 2 | Nenhum profissional registrado | Zero confirmado, e há quanto tempo | — | — | Zero, com a duração | Por convenção |
| 3 | Declínio persistente | Quedas anuais seguidas (o mês âncora) e perda acumulada | 2 quedas e 10% ou mais | 3 quedas e 20% ou mais | 4 quedas e 30% ou mais | Por convenção |
| 4 | Desaceleração | A classe "Desaceleração do crescimento" da Análise de Tendência, nos 4 registros anuais | A classe em 2 anos seguidos | — | — | Por convenção (exploratório) |
| 5 | Instabilidade | Oscilação de 7 registros ÷ a típica do porte | 1 em 20 | — | — | Comparado com a base |
| 6 | Queda recente | Queda de um registro para o seguinte | 1 em 20, e pelo menos 2 profissionais e 10% | 1 em 100, e pelo menos 2 e 20% | 1 em 1.000, e pelo menos 3 e 30% | Comparado com a base, com tamanho mínimo |
| 7 | Abaixo do que já teve | Distância ao patamar: a maior média de 2 anos completos, antes dos 4 últimos registros | 2 últimos registros 15% ou mais abaixo | Isso, e 1 em 100 | 4 últimos registros 30% ou mais abaixo, e 1 em 1.000 | Por convenção e comparado com a base; patamar de pelo menos 20 |
| 8 | Menos profissionais por habitante | Variação da taxa por 1.000 habitantes em 2 anos | 1 em 20 | 1 em 100 | 1 em 1.000 | Comparado com a base; população comparável; pelo menos 20 no início da janela |
| 9 | Perda de posição | Variação do percentil da taxa em 2 anos | 1 em 20 | 1 em 100 | 1 em 1.000 | Idem |
| 10 | Mais longe da referência | Variação do índice ante o grupo de cima, sem o próprio território, em 2 anos | 1 em 20 | 1 em 100 | 1 em 1.000 | Idem; precisa de grupo de cima |
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
- **Sinal 6:** o nível é o mais grave em que a queda é rara **e** tem o tamanho mínimo daquele nível (o maior entre o mínimo em
  profissionais e a fração do que havia, arredondada para cima). Sem queda, a tela ainda diz que níveis a base sustenta para o
  porte.
- **Sinal 7:** o moderado é por convenção; o elevado e o crítico pedem também a raridade do afastamento entre territórios com
  patamar do mesmo porte. Com patamar abaixo de 20, é só descritivo.
- **Sinais 8 a 10:** as definições são as da V2.2 (a taxa = profissionais ÷ população × 1.000; o percentil pelo posto médio, no
  universo fixo da janela; o índice = 100 × taxa do território ÷ taxa da referência, com a referência na mesma unidade e sem o
  território). O que muda é o nível: a variação em 2 anos é comparada com as variações anteriores de territórios do mesmo porte.
- **Sinal 11:** nunca vira alerta e nunca usa as palavras "isolamento" ou "desassistência". O estado como unidade não tem um
  ponto único; num conjunto, vale o componente mais próximo.
- **Sinal 12:** lista os sinais com nível e diz quantos vêm da mesma queda. Sem soma de pontos e sem índice geral.

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
  o trecho sai da régua, e o registro do pico fica fora do patamar, da série anual e da instabilidade;
- **descontinuidade de registro — quebra de fonte:** a soma municipal da UF abaixo da contagem estadual de médicos únicos (na
  base, só o Distrito Federal, de jan/2014 a jun/2017). O trecho sai da régua, e a janela do município começa depois dele;
- **verificar registro:** o salto sem volta observada e a queda de 10 ou mais que leva a contagem à metade ou menos. A queda
  grande que persiste **continua alertável**.

## Na tela

- **Onde:** o botão **Detector de Sinais** (`analise-ferramenta-detector`), na linha "Ferramentas" da navegação principal. A
  ferramenta abre no lugar do painel da aba e usa a **seleção em uso**: os municípios, os estados como unidade e os conjuntos.
  Sem territórios, diz "Nenhum território selecionado" e não pede nada ao motor.
- **Título e "Entenda"** (`detector-entenda-ferramenta`): "Compara cada território com o que é comum na própria base."
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
    contorno e a sigla do grupo de cima junto aos pontos dele. **O produto não tem a malha das divisas**: o mapa não as desenha
    (ver "Limitações").
  - **Gráfico** (`detector-bolhas`): o gráfico de bolhas do Agente, com uma bolha por território à vista que tem distância a
    mostrar. Na horizontal, a distância do sinal 11; na vertical, a taxa por 1.000 habitantes; o tamanho, a população; a cor, o
    nível. Tocar numa bolha ou num ponto abre os detalhes do território.
- **Lista** (`detector-tabela`, 50 linhas por página, `detector-linha`), com quatro colunas:
  - **Território** (com o tipo, quando é estado como unidade ou conjunto);
  - **Alerta** (`detector-alerta`): o nível (`detector-nivel`: Moderado, Elevado ou Crítico) e o tipo de critério
    (`detector-criterio`); ou "Sem alerta", "Sem comparações suficientes" ou "Sem nível (conjunto)";
  - **Por quê** (`detector-por-que`): a frase do sinal principal, do motor, com quantos outros sinais têm nível ("Só 1 médico
    (+1 sinal)", "18% abaixo do que já teve (patamar de 130)");
  - **Último registro** (`detector-ultimo`): "jun/2024 · 5 médicos", com a marca de registro quando há (`detector-registro`:
    "verificar registro" ou "descontinuidade de registro").

  Os cabeçalhos ordenam a lista: pelo nome, pelo nível (o padrão: do crítico ao moderado; depois quem a base não pôde comparar,
  os conjuntos e os sem alerta) ou pelo número do último registro. A ordem não é um índice. Os cabeçalhos "Alerta" e "Por quê"
  têm "Entenda" (os níveis e os termos: porte, patamar, percentil e "1 em cada N"). No celular, a lista vira cartões.
- **Detalhe** (a seta de cada linha, `detector-detalhe`): o alerta do território, com o porquê e, quando há, "vêm da mesma
  queda: contam como um evento" (`detector-mesma-queda`); a série observada, só com os registros reais e as marcas de registro; a
  **série da taxa** (`detector-serie-da-taxa`), com a da referência tracejada; e os 12 sinais em quatro grupos
  (`detector-grupo`) — **Quantos há** (1–2), **Como mudou** (3 a 7), **Comparado com outros** (8 a 10) e **Onde fica** (11) —,
  mais **Juntos** (12). Em cada sinal (`detector-fenomeno`): o nível com o tipo de critério (ou "Sem alerta", "Sem comparações
  suficientes", "Sem nível (conjunto)", "Sem dado para avaliar", "Não avaliado" ou "Só contexto"), **uma frase**, o que a base
  ainda não sustenta ("Sem comparações suficientes para o crítico: há 203, e ele pede 999.") e o **"Entenda"**. A **explicação
  completa** (`detector-fenomeno-explicacao`) traz os sete campos: o que foi observado, qual critério, comparado com o comum, o
  que significa, o que não significa, limitações do dado e qualidade do registro. Há também o **histórico de sinais**
  (`detector-historico`, sinais 1 a 7), em que cada data é avaliada só com o que era conhecido nela.
- **"Entenda"** (`frontend/src/Entenda.tsx`, igual no Detector e no Simulador): fica escondido e abre com o mouse (ao passar por
  cima), com um toque ou pelo teclado (ao receber o foco; Enter ou Espaço fixam); fecha ao sair (o mouse deixa o botão e a
  caixa, o foco sai deles, Esc ou um toque fora). Traz duas ou três frases simples e um exemplo com números; a explicação
  inteira fica em "Ver explicação completa" (no sinal, os sete campos; na primeira tela, "Como foi calculado"). Os textos vêm do
  motor.
- **Ajustar critérios** (`detector-parametros`): os limites de cada sinal **em frases, com os campos dentro delas**
  (`detector-parametro-<grupo>-<campo>`), por exemplo: "Alerta elevado quando a queda for de pelo menos [2] médicos e [20]% do
  que havia, e for rara: em territórios do mesmo porte, só 1 em cada [100] mudanças anteriores foi uma queda igual ou maior."
  Ali fica também o início da janela ("Considerar os registros desde", `detector-janela-inicio`). Trocar um valor e aplicar
  torna a configuração **exploratória**: aviso no alto (`detector-exploratorio`), nos textos (uma nota) e nas exportações (a
  coluna "Configuração"). **"Voltar ao padrão"** (`detector-voltar-ao-padrao`) fica sempre à vista, desligado enquanto os
  critérios são os do padrão; os padrões nunca são trocados em silêncio.
- **Como foi calculado** (`detector-metodo`): as notas, os três níveis e a **régua da data** por porte — quantas comparações
  anteriores há e a partir de que queda (sinal 6) ou afastamento (sinal 7) ela é rara em cada nível, ou "sem comparações
  suficientes (203 de 999)". Com estados como unidade na seleção, também a régua dos estados.
- **Ligação com o Simulador de Cenários** (nos detalhes de cada território):
  - **"Abrir no Simulador"** (`detector-abrir-no-simulador`) abre o [Simulador](SIMULADOR_DE_CENARIOS.md) só com aquele
    território, com o contexto: a data avaliada, os sinais com nível ("Queda recente (elevado)") e, quando a pessoa escolheu uma
    janela no Detector, essa janela. A seleção principal não muda;
  - **"Simular recuperação"** (`detector-simular-recuperacao`) só aparece para o território que está abaixo do patamar (sinal
    7). Abre o Simulador com uma **meta hipotética**, que a pessoa pode trocar: voltar ao patamar. O resultado é um cenário e
    uma conta condicional, nunca uma recomendação.
- **Exportações:** a lista em CSV (uma linha por território: o alerta, o tipo de critério, o porquê, os sinais com nível, os da
  mesma queda, os sem comparações suficientes, o nível e os valores de cada sinal, a janela, a versão da base e do método e a
  configuração) e o método em JSON (a fonte, a janela, os critérios padrão e em uso, os níveis, a régua da data, a dos estados
  quando há, o aviso da base e as notas).

**Nomes da base.** Os textos usam os nomes que a base dá (`fonte.rotulos`): na base do Brasil, "médicos", "município", "estado"
e "Brasil". **Linguagem:** sem termos técnicos na primeira tela; "porte", "patamar", "percentil" e "1 em cada N" têm "Entenda".

## Rota

`POST /api/detector` (formulário, como `/api/painel`): `dataset=brazil`, `dataset_version` e `options` (JSON). Só lê e calcula:
nada é registrado na sessão, e nada vai ao provedor de IA. Conta nas vagas das operações pesadas (`carga.PESADAS`).

| Opção | Conteúdo |
|---|---|
| `base` | `{"municipios": {"todos", "estados", "ids"}}`, como no painel |
| `estados_unidade` | os estados como unidade (prefixos IBGE) |
| `conjuntos` | `[{"id", "rotulo", "membros", "versao"?}]`; membros do mesmo nível (`code:<IBGE>` ou `uf:<prefixo>`) |
| `janela` | `{"inicio", "fim"}`, competências da base; sem ela, a série inteira |
| `parametros` | os critérios trocados, por grupo: `estrutural` (`critico`, `elevado`, `moderado`), `declinio` (`<nível>_quedas`, `<nível>_perda`), `desaceleracao` (`anos`), `instabilidade` (`moderado_um_em`), `perda` (`<nível>_um_em`, `<nível>_minimo`, `<nível>_fracao`), `patamar` (`moderado`, `critico`, `minimo`, `elevado_um_em`, `critico_um_em`), `disponibilidade`, `posicao` e `defasagem` (`<nível>_um_em`) e `contexto` (`taxa_do_brasil_pct`); a resposta vem com `exploratorio: true` |
| `detalhe` | o id de um território da seleção: a resposta traz `territorio`, `linha`, `serie`, `historico`, `comparativo`, `coordenadas` e `fenomenos`, no lugar da lista |

A lista responde (versão `DETECTOR-SINAIS/V3/1`) com `versao`, `fonte` (com `rotulos`, os nomes da base), `janela`,
`competencias`, `parametros` (`padrao`, `em_uso`, `personalizados`, `editaveis`), `niveis` (o "1 em cada N" e as comparações que
cada nível pede), `grupos` (os grupos dos sinais), `portes`, `entenda` (os textos da primeira tela), `linhas`, `resumo`
(`niveis`, um nível por território; `com_nivel`, quantos territórios têm nível em cada sinal), `calibracao` (a régua da data: por
porte, as `comparacoes` e, em cada nível, `um_em`, `pede` e `queda_pct` — ou `afastamento_pct`, no sinal 7; e o `monitoramento`,
com `aviso_da_base`), `calibracao_dos_estados` (quando a seleção tem estados como unidade), `aviso_da_base`, `comparacao` (a
janela dos sinais 8 a 10, o estado dela, os trechos de população comparável e o critério da distância), `coordenadas`, `notas` e
`limitacoes`.

Em cada linha:

- `alerta`: `estado` (`alerta`, `sem_alerta`, `sem_comparacoes` ou `sem_nivel`), `nivel`, `sinal` (o principal), `criterio`,
  `outros`, `por_que`, `sinais` (cada sinal com nível: `sinal`, `nivel`, `criterio`), `mesma_queda`, `sem_comparacoes` (os sinais
  comparados com a base que ficaram sem comparações) e `motivo` (no conjunto);
- os campos de cada sinal, com `estado` e `classe` (o nível daquele sinal): `estrutural`, `perda`, `patamar`, `declinio`,
  `desaceleracao`, `instabilidade`, `disponibilidade`, `posicao`, `defasagem`, `contexto` e `coexistencia`; `registro`; `ultima`;
  `porte`; num conjunto, `ids_dos_membros`; num município que mudou de nome, `nomes_anteriores`.

No detalhe, cada item de `fenomenos` traz `chave`, `numero`, `nome`, `grupo`, `nivel`, `estado_do_nivel` (`alerta`,
`sem_alerta`, `sem_comparacoes`, `sem_nivel`, `sem_dado`, `nao_avaliado`, `contexto` ou `juntos`), `criterio_do_nivel`,
`exploratorio`, `situacao` (a frase), `entenda` (`texto` e `exemplo`), `sem_comparacoes` (os níveis que a base não sustenta, com
`comparacoes`, `pede` e `texto`) e os sete campos da explicação completa.

**Os campos que a resposta já trazia continuam**, com os valores da V3: `classe` (agora `moderado`, `elevado` ou `critico`);
`sinal`, nos sinais 3 e 8 a 10 (repete o nível); `patamar.critica` (`sem_comparacoes` quando os 4 últimos registros cumprem o
limite do crítico e a base não tem comparações para ele); `estado` e `classe` em cada item de `fenomenos`; e, na régua da data,
`transicoes`, `queda_incomum_pct` e `queda_muito_incomum_pct` (os cortes do elevado e do crítico), `observacoes`,
`afastamento_incomum_pct`, `alta` e `critica` (`calibrado` ou `sem_calibracao`) e `monitoramento.incomuns` (o mesmo que `raras`).
Os nomes dos critérios em `parametros` são os da tabela acima; um nome antigo (`perda.alta_alfa`) é recusado como desconhecido.

As limitações `RARO_E_INCOMUM_NA_BASE`, `CONJUNTO_SEM_NIVEL` e `COMPARACAO_SO_COM_POPULACAO_COMPARAVEL` acompanham toda resposta;
`CONFIGURACAO_EXPLORATORIA`, a que usa critérios diferentes do padrão. Erros de pedido vêm em 422, com o texto em português
(seleção vazia, território fora da base, competência fora da base, critério fora do intervalo ou fora de ordem — o nível mais
grave não pode ser mais comum que o menos grave).

A seleção segue o contrato compartilhado das ferramentas (`series_brasil.selecao`): o estado como unidade (ou num conjunto de
estados) e os municípios dele não entram juntos (RQ-DAD-30); um conjunto reúne territórios do mesmo nível.

## Calibração

Estudo de 13/11/2026 com a base versionada e a população nova (`scripts/calibrar_detector.py`, somente leitura; versão da base
`faa54169c5b6`, método `DETECTOR-SINAIS/V3/1`). Cada data é avaliada só com as mudanças anteriores a ela, e as descontinuidades
de registro já conhecidas ficam fora do passado, como no produto.

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
jun/2024, os estados têm 270 comparações, e o crítico pede 999). O moderado dos estados fica um pouco acima da meta: é preciso
acompanhar.

**Alertas de cada sinal, em todas as datas** (municípios, critérios padrão):

| Sinal | Avaliações | Moderado | Elevado | Crítico | Algum nível |
|---|---:|---:|---:|---:|---:|
| 1–2 Poucos médicos ou nenhum | 116.964 | 12,07% | 10,78% | 1,81% | 24,67% |
| 3 Declínio persistente | 105.822 | 3,97% | 0,59% | 0,10% | 4,66% |
| 4 Desaceleração | 83.546 | 0,21% | — | — | 0,21% |
| 5 Instabilidade | 63.085 | 5,58% | — | — | 5,58% |
| 6 Queda recente | 114.293 | 2,95% | 0,71% | 0,07% | 3,73% |
| 7 Abaixo do que já teve | 30.358 | 5,90% | 0,98% | 0,04% | 6,92% |
| 8 Menos médicos por habitante | 30.292 | 2,65% | 0,74% | 0,09% | 3,48% |
| 9 Perda de posição | 30.292 | 5,10% | 1,11% | 0,08% | 6,29% |
| 10 Mais longe da referência | 30.277 | 3,58% | 0,82% | 0,09% | 4,48% |

Leitura: os sinais comparados com a base ficam perto das metas (5%, 1% e 0,1%). O crítico do sinal 7 (0,04%) fica perto da meta
de 0,1% e passa a valer onde há 999 comparações. O sinal 3, por convenção, fica perto do que a raridade daria. Os sinais 1 e 2 são
uma convenção sobre o número de profissionais: um quarto das avaliações municipais tem 5 médicos ou menos.

**Em jun/2024** (5.570 municípios): 41 críticos, 434 elevados, 977 moderados e 4.118 sem alerta. Com algum alerta: 26,1%; com
algum alerta **comparado com a base**: 9,9% (o restante vem dos sinais por convenção, sobretudo "Poucos médicos"). Ao longo das
datas, a parcela com algum alerta comparado com a base vai de 3,2% a 11,5%, abaixo dos cerca de 20% que a Proposta V3 (Parte F)
põe como sinal para rever o padrão. Nesta data, 2,89% dos municípios tiveram uma queda rara (esperado: cerca de 5%), sem aviso
da base. Dos 27 estados como unidade, 3 têm moderado e 24, nenhum alerta.

**Sinal 8, os limites que a raridade dá em jun/2024** (a queda da taxa por habitante em 2 anos, por porte no início da janela):

| Porte | Variações anteriores | Moderado: queda maior que | Elevado | Crítico |
|---|---:|---:|---:|---:|
| 20 a 49 | 7.706 | 25,5% | 41,1% | 73,5% |
| 50 a 99 | 3.110 | 19,9% | 37,0% | 73,8% |
| 100 a 299 | 2.873 | 16,6% | 32,5% | 78,7% |
| 300 a 999 | 1.460 | 10,4% | 22,2% | 42,1% |
| 1.000 a 2.999 | 470 | 4,5% | 13,8% | sem comparações suficientes |
| 3.000 a 9.999 | 155 | 2,5% | 20,8% | sem comparações suficientes |
| 10.000 ou mais | 31 | 6,2% | sem comparações suficientes | sem comparações suficientes |
| Todas as janelas e portes juntos | 15.805 | 21,5% | 37,9% | 68,6% |

Com todos os portes juntos, os cortes ficam perto dos que a Proposta V3 estimou com a população anterior (23%, 38% e 60%).

**Sinal 11, o contexto em cada registro anual** (critério: a taxa do Brasil na data): em jun/2024, a taxa é de 2,36 por 1.000;
2.002 municípios ficam acima do critério e 3.566 têm distância a mostrar (mediana de 27,1 km; percentil 90, 112,2 km; maior,
838,6 km). Em jun/2014, eram 1,60 por 1.000, 1.565 municípios acima e mediana de 32,5 km. A distância é em linha reta: não é
distância por estrada, tempo de viagem nem acesso.

**O que continua sendo convenção:** os limites dos sinais 1 a 4, o tamanho mínimo do sinal 6, os 15% e os 30% do sinal 7, o
mínimo de 20 no patamar e nos sinais 8 a 10 e o critério do pico que volta. Todos podem ser trocados, como configuração
exploratória.

## Limitações

- O registro mais recente da base é jun/2024: nenhum sinal descreve a situação de hoje.
- "Raro" quer dizer incomum nesta base, não comprovadamente pior. O nível não é juízo de desassistência, de suficiência do
  atendimento nem de prioridade.
- A contagem municipal é a de médicos registrados no município: quem atua em mais de um conta em cada um. Um conjunto é a soma das
  contagens dos componentes, nunca "médicos únicos", e não tem nível.
- O Detector não infere rotatividade de pessoas, desassistência, isolamento assistencial, suficiência do cuidado nem causa.
- A base dos estados é pequena: o crítico nunca tem comparações suficientes, e o elevado só desde jun/2019.
- De 3.000 médicos para cima, os municípios não têm comparações suficientes para o crítico; de 10.000 para cima, o elevado dos
  sinais 8 a 10 também fica sem comparações.
- A variação em 2 anos (sinais 8 a 10) só existe em trechos com população comparável, lidos da própria base. A população é uma
  estimativa, e a taxa de um estado usa a contagem estadual sobre a soma das populações municipais.
- A distância (sinal 11) é em linha reta entre coordenadas: não mede acesso, deslocamento nem a organização da rede.
- **O mapa não desenha divisas:** o produto não tem a malha territorial (só as coordenadas dos municípios). O mapa mostra os
  pontos pelo nível e a sigla do grupo de cima junto aos pontos dele.
- O histórico de sinais cobre os sinais 1 a 7.
- A ferramenta ainda funciona só com a base do Brasil; a leitura de planilhas enviadas (a estrutura comum da Proposta V3) é a
  etapa seguinte do comando V23.

## Testes

- pytest: `backend/tests/test_reguas.py` — a régua comum (as dez faixas, a raridade com o "+1" e os empates, os mínimos, a
  retaguarda pelas vizinhas e, só no moderado, por todas as faixas com a mudança padronizada, e θ só com o passado);
  `backend/tests/test_detector.py` — os sinais em séries sintéticas (os níveis por convenção e a histerese; zero e ausência; a
  queda rara com os empates, só o passado, o tamanho mínimo e as comparações mínimas; a retaguarda; o pico que volta, a quebra
  de fonte e a queda grande que persiste; o patamar; o declínio; a desaceleração igual à classe da Análise de Tendência; a
  instabilidade; a régua própria dos estados e os conjuntos sem nível; os critérios ajustáveis; um nível por território e os
  efeitos da mesma queda; os sinais 8 a 10 pela raridade; a distância; os sinais juntos; os textos, com o "Entenda" de duas ou
  três frases), a rota com um catálogo sintético e, no job `dados-reais`, a base versionada (as taxas da régua por nível e por
  porte, a régua dos estados, a lista inteira com um nível por território, Rio Rufino/SC, o Distrito Federal antes de 2018, uma
  queda grande que persiste e a desaceleração igual à da Análise de Tendência).
- Node: `frontend/tests/detector.test.mjs` — a leitura da resposta, a lista de quatro colunas, o resumo dos níveis, os filtros,
  a ordem, os critérios em frases (todos os parâmetros do motor, uma vez cada), a régua em palavras, as exportações, o mapa e o
  gráfico pelos níveis, o que o Detector leva ao Simulador e o "Entenda" (mouse, toque e teclado);
  `frontend/tests/modoEscuro.test.mjs` — o contraste dos níveis no modo escuro.
- Navegador: `backend/tests/ui_detector.py` (suíte `base-versionada`) — a lista, o resumo clicável, os filtros e a ordem; o
  detalhe com os quatro grupos, o "Entenda" por mouse e teclado e a explicação completa; os critérios em frases e a configuração
  exploratória; a régua por porte; o estado como unidade; o mapa e o gráfico; os sinais comparados em jun/2021; "Simular
  recuperação"; e a tela de celular, com o "Entenda" pelo toque e a lista em cartões.
