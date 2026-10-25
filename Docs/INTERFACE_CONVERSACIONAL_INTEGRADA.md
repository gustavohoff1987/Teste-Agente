# Interface conversacional integrada: a página única de análise

Desde 22/10/2026, a interface é uma página única: uma análise integrada, sem duas telas (decisão do responsável pelo produto
em 22/10/2026: "Eu só quero entrar por aquela linha, por aquele gráfico"). Este documento descreve a estrutura da página, a
fonte de dados, o Histórico, a sessão e a conversa. A área de análise (o gráfico, as famílias, as funções e os Detalhes) é
descrita no documento da área ([página principal: o gráfico de bolhas](PAINEL_INTEGRADO_INTERFACE.md)); o motor do gráfico,
em [painel integrado](PAINEL_INTEGRADO.md).

As telas clássicas saíram do produto: o catálogo de 12 análises, a preparação (categoria, período, abrangência e condições),
os resultados em abas (mapa, gráficos e tabelas), a investigação progressiva e os diagnósticos compostos. O motor
(`/api/analyze` e as capacidades) continua; a página usa `/api/painel`. A seção [O que saiu](#o-que-saiu-em-22102026)
resume a mudança.

## Estrutura da página

1. **Aceite de privacidade primeiro.** O pop-up traz só a declaração ("Declaro que não compartilharei dados pessoais ou
   sensíveis, seja por meio dos arquivos enviados ou das mensagens inseridas no chat.") e "Li e concordo"; depois de uma
   sessão encerrada, o aviso do descarte aparece acima dela. Até o aceite, a escolha da fonte e o envio de arquivos não
   funcionam.
2. **Cabeçalho.** O nome do agente ("Agente Diagnóstico Territorial", com o rosto do agente) no topo da página e, abaixo, o
   banner de apresentação (de volta em 23/10/2026): "FORÇA DE TRABALHO NA SAÚDE", "Transforme dados em diagnósticos
   territoriais." e "Um novo olhar sobre seus dados. Explore territórios, conecte informações e compreenda cenários." Abaixo
   do banner, à esquerda, com os dados prontos (24/10/2026), a navegação: **Nova sessão**, **Nova análise** e **Histórico**.
   Antes dos dados, ela não aparece: a primeira ação é escolher os dados. Não há "Início" nem "Resultados": a página é sempre
   a análise.
3. **Fonte dos dados:**
   - antes dos dados, as entradas ficam na área de análise e na conversa, com as mesmas ações: desde 24/10/2026, só **Usar
     dados do Brasil** e **Enviar meus dados**. "Enviar meus dados" abre sempre a mesma **janela de envio** ("Enviar meus
     dados", `envio-de-dados`), com o que enviar (CSV, XLS ou XLSX, até 30 MB), "Escolher o arquivo" e o **modelo de planilha**
     (a estrutura recomendada, com as colunas descritas, para consultar ou baixar em XLSX); "Cancelar" fecha sem mudar nada. O
     botão "Modelo de planilha XLSX" saiu da área e da conversa: o modelo fica na janela. Não há botões de fonte no alto da
     página;
   - depois, logo abaixo do cabeçalho, o resumo da fonte, por exemplo "Dados do Brasil · Medicina · jan/2014 a jun/2024" ou,
     numa planilha, "distritos.csv · distritos e províncias · Medicina · 2021 a 2024", com **Trocar** (e **Colunas**, na
     planilha);
   - "Trocar" traz as duas entradas de volta à área central, com "Cancelar" ("Escolha a nova fonte. A análise atual continua à
     vista até a nova fonte ficar pronta."); "Enviar meus dados" abre a mesma janela de envio. A troca só vale quando a nova
     fonte fica pronta: até lá, a análise continua com a fonte em uso, e um cancelamento ou um arquivo recusado não a tiram
     da tela;
   - na base do Brasil, "Diagnóstico técnico da fonte" mostra a origem, a versão e a integridade (sem conteúdo).
4. **Área de análise**: o gráfico com os valores do motor, nos estados E0 (antes dos dados) a E4 (funções em uso). Ver o
   documento da área.
5. **Conversa**: a caixa flutuante com o rosto do agente, sempre na página (ver [Conversa](#conversa)).

Uma linha de aviso abaixo da fonte confirma as ações da página ("Dados do Brasil prontos.", "Análise guardada no Histórico.
Nova análise com os mesmos dados.", "Análise reaberta como estava, sem recalcular: …") e some depois de alguns segundos.
No celular (abaixo de 640 px), o cabeçalho e a navegação quebram em linhas, a lista do Histórico ocupa a largura da tela e
a conversa fica ancorada embaixo, sem rolagem horizontal.

## Fonte de dados

### Base do Brasil

"Dados do Brasil" examina a base versionada uma vez, no recorte municipal, com o bloco dos níveis (Brasil e estados), por
`/api/inspect`, como antes. A área recebe a fonte (`FonteDados`: `tipo: "brasil"`, a versão da base, o token da camada
geográfica complementar e os rótulos fixos município/municípios e estado/estados), as competências, a categoria, os níveis e
o catálogo de municípios para a busca. Desde 23/10/2026, a base abre **sem territórios escolhidos**: a área abre a Seleção
de Territórios e espera; nada é pedido ao motor até a escolha. Antes, ela abria nos 27 estados. Desde 24/10/2026, a Seleção
tem três níveis, um por vez: o Brasil como unidade, os estados (um, vários ou todos) e os municípios, por estado e
cumulativos (ver o documento da área).

### Planilha enviada: o painel "Colunas"

"Enviar meus dados" aceita CSV, XLS e XLSX de até 30 MB, de qualquer país. Outro formato é recusado com "Formato não
reconhecido. Selecione um arquivo CSV, XLS ou XLSX.". Um arquivo Excel com várias abas pergunta "Qual aba deseja
utilizar?" antes das colunas. A estrutura é a mesma da base do Brasil; só os nomes se adaptam (distrito, condado, província).

O painel **Colunas** mostra a coluna de cada papel:
- **unidade territorial** (necessária), **código da unidade**, **grupo territorial** (a coluna-mãe: estado, província,
  região), **período** (necessário), **categoria**, **quantidade** (necessária), **população** (para a densidade),
  **latitude** e **longitude** (para a análise espacial) e **identificador individual** (para a rotatividade);
- as colunas reconhecidas por regra conclusiva já vêm escolhidas; as sugestões do `/api/inspect` aparecem no topo de cada
  lista, marcadas "(sugerida)", e nunca são usadas sem a escolha da pessoa (decisão D1 de 19/10/2026). Duas candidatas para a
  unidade (por exemplo, "distrito" e "provincia") deixam a lista vazia até a escolha;
- o grupo territorial é sugerido pelas colunas que o backend reconhece como nível superior (estado, província,
  departamento) depois da escolha da unidade;
- uma coluna representa um papel só: escolhida num papel, ela sai do anterior;
- **O que a quantidade conta?** (pessoas, vínculos de trabalho, postos de trabalho ou outra unidade, descrita);
- **Quem são os trabalhadores contados?**, só sem coluna de categoria: a profissão ou o conjunto de trabalhadores (por
  exemplo, médicos), que vai como objeto da análise (`category_constant`) ao pré-exame, à conversa e ao gráfico, e dá nome à
  categoria no título; sem ele, "Começar a análise" lista o que falta;
- **Referencial das coordenadas**, com latitude e longitude: a pessoa informa o referencial em que as coordenadas foram
  coletadas, **SIRGAS 2000** ou **WGS 84** (o WGS 84 desde 22/10/2026, pelo Adendo REF-20261022 da SPEC), e o sistema não
  converte um no outro. "Outro referencial" ou "Não sei" deixam a análise espacial indisponível, com o motivo ("Só os
  referenciais SIRGAS 2000 e WGS 84 são admitidos; com outro, ou sem saber qual é, nada é presumido."). O separador decimal
  das coordenadas só é pedido quando o formato é misto;
- **Nomes**: como se chamam as unidades e os grupos, no singular e no plural, com a sugestão a partir do nome da coluna
  ("distrito" sugere distrito e distritos; "provincia", província e províncias). Os nomes aparecem nos textos da página e da
  conversa: nenhum texto da estrutura diz "município" quando a fonte é uma planilha;
- **O que esta planilha permite**: Análise de Distribuição, Análise Espacial, Análise de Tendência e Análise de
  Rotatividade (os nomes das abas, desde 23/10/2026), cada uma disponível ou
  indisponível com o motivo, pelo pré-exame do backend (`/api/preflight`), refeito a cada escolha. A escolha que se faz no
  gráfico (por exemplo, a referência da análise espacial) não torna a análise indisponível.

**Começar a análise** (ou **Aplicar as colunas**, ao reabrir o painel de uma planilha em uso) passa a planilha à área. Sem a
unidade territorial, o período, a quantidade, o que ela conta ou os nomes, o clique lista o que falta, e nada é pedido ao
motor. A área recebe `FonteDados` com o arquivo (reenviado só ao backend local), o mapeamento confirmado na tela (com o papel
`grupo_territorial`), as premissas escolhidas (`confirmed_roles` com as colunas escolhidas no seletor, `count_unit`,
`custom_count_unit`, `crs` só com `SIRGAS2000` ou `WGS84`, como informado, e `number_format`) e os rótulos (`rotulos: {unidade, grupo}`). No pré-exame e na conversa, que usam os papéis atuais do
backend, o grupo segue em `hierarchy_columns` (nível superior 1), e as colunas escolhidas pela pessoa seguem em
`confirmed_roles`.

## Histórico e sessão

- **Histórico.** Cada análise da sessão guarda o último estado informado pela área ao calcular (`EstadoSalvo`: título,
  definição, resposta do motor e hora). A lista mostra a mais recente primeiro, com "Em exibição" na atual. Reabrir uma
  análise devolve o gráfico como estava, **sem recalcular** (a área recebe o estado em `restaurar`). Uma análise feita com
  outra fonte de dados fica na lista, desabilitada, até a pessoa voltar àquela fonte. O menu fecha com clique fora ou
  Escape, devolvendo o foco ao botão.
- **Nova análise** guarda a análise atual no Histórico e recomeça com os mesmos dados, sem territórios escolhidos (desde
  23/10/2026; antes, voltava aos estados). Desde 24/10/2026, a navegação só aparece com os dados prontos (antes, Nova análise
  ficava desabilitada antes dos dados).
- **Trocar de fonte** também guarda a análise atual; a área recomeça com a nova fonte.
- **Nova sessão** pede confirmação num diálogo com: **Exportar CSV** (a análise em exibição: um registro por item da resposta
  do motor, com todos os campos em precisão integral; objetos viram colunas "campo.subcampo", e texto que começaria uma
  fórmula leva um apóstrofo), **Imprimir / PDF**, **Continuar nesta sessão** e **Iniciar nova sessão**. Confirmar encerra a
  sessão no servidor e recarrega a página, descartando arquivos, conversa, Histórico e resultados em memória; se o
  encerramento falhar, o diálogo mostra o erro e mantém tudo. Para guardar outra análise, reabra-a pelo Histórico e exporte.
  Nada fica salvo entre sessões.

A sessão temporária, os limites e a revogação continuam como antes (`conversationSession.ts`). O resultado de cada gráfico
entra na sessão do backend (`/api/painel`), para o Histórico e para a conversa saberem o que está na tela. A revisão de
contexto da sessão muda com a fonte em uso.

## Conversa

A conversa fica na caixa flutuante com o rosto do agente, sempre na página: arrastável pelo cabeçalho (mouse, toque e
teclado: setas, Shift acelera e Home volta ao canto), minimizável e sempre dentro da janela; no celular, ancorada embaixo.
Ela mantém os identificadores de sempre (`#assistente`, `#assistant-input`, `latest-reply`). A transcrição fica em memória,
e a última resposta aparece junto do campo de mensagem.

**Abertura.** Antes dos dados, a caixa fica aberta e mais larga, perguntando "O que você quer analisar? Prefere usar os dados
do Brasil ou enviar os seus?", com **Usar dados do Brasil** e **Enviar meus dados**, as mesmas duas entradas da área de
análise (24/10/2026; o botão "Modelo de planilha XLSX", `chat-fonte-modelo`, saiu). "Enviar meus dados", pelo botão ou
pedido em palavras, abre a mesma janela de envio da área ("Abri a janela de envio: escolha o arquivo CSV ou Excel. O modelo de
planilha também está nela. Depois, confira as colunas no painel Colunas, no alto da página."). Um cumprimento antes dos dados
recebe "Olá! O que você quer analisar? Prefere usar os dados do Brasil ou enviar os seus?". Depois, ela fica compacta, com uma orientação curta para cada etapa: enquanto os dados do Brasil são
preparados, "Estou preparando os dados do Brasil. Em seguida, escolha os territórios que quer analisar."; com os dados prontos
e sem territórios escolhidos (a base abre sem seleção automática), "Os dados estão prontos. Escolha os territórios na Seleção
de Territórios ou me diga quais quer ver, por exemplo “mostre o Pará” ou “todos os estados”." (numa planilha, sem os
exemplos da base do Brasil; desde 24/10/2026, também no nível Estados sem nenhum estado marcado); nos estados, "Escolha no
gráfico quais estados abrir, ou me diga quais municípios quer ver." (na
planilha, com os nomes escolhidos, por exemplo "quais províncias abrir, ou … quais distritos"); e, com as unidades na tela,
exemplos de pedidos ("mostre o Pará", "use Belém como referência", "compare Manaus e Tefé").

**Escolha da fonte pela conversa.** "Usar dados do Brasil" e "enviar meus dados" fazem o mesmo que os botões, sem o provedor
de IA. Escolhidos os dados do Brasil, a resposta diz "Dados do Brasil escolhidos. Vou prepará-los; em seguida, escolha os
territórios na Seleção de Territórios ou me diga quais quer ver, por exemplo “mostre o Pará”."

**Antes dos dados.** Perguntas sobre o agente, a privacidade e os conceitos ("Como se calcula a densidade?") e sobre o
conteúdo da base do Brasil continuam respondidas localmente. Um pedido analítico feito antes da escolha fica guardado: quando
a base fica pronta, ele é interpretado de novo, já com a base, e os municípios citados nele vão para o gráfico.

**Com os dados.** Fora os pedidos atendidos na própria tela (a vista do desenho, a tabela, o resumo do que está na tela e a
análise anterior, descritos abaixo), cada pedido vai primeiro ao intérprete local (`POST /api/exploration/interpret`); sem
resposta local, ao intérprete contextual (`POST /api/llm/interpret-context`). A conversa não calcula nada:
- quando a resposta traz o campo **`painel`** (família, indicador, nível, municípios, competência, janela, visão da tendência,
  referência, função, seleção, ordenação, condições, grupos e vista do desenho), ele vira um **pedido para a área**, com um
  id novo a cada comando. Só os campos válidos entram, e os não citados (`null`) ficam de fora;
- "Mostre o Pará", "use Belém como referência", "compare Manaus e Tefé", "volte aos estados" e os demais comandos mudam o
  gráfico; os números vêm do motor, pedidos pela área. Desde 24/10/2026, um pedido feito com a Seleção de Territórios aberta
  leva a área à análise quando há territórios escolhidos (os resultados ficam nas análises); um pedido que muda os
  territórios (desde a segunda rodada de 24/10/2026, qualquer pedido que muda a área) pode ser desfeito com o Desfazer fixo
  no alto da área ("Desfazer: aplicar o pedido da conversa"; até 25/10/2026, o botão se chamava "Voltar"); e a comparação de
  antes só
  continua se os itens dela seguem na análise.
  O nível `brasil` (o Brasil como unidade) vale na base do Brasil; numa planilha, vira o aviso "O Brasil como unidade existe
  só nos dados do Brasil.";
- o **contexto** de cada pedido sai do que está no gráfico (`ContextoDoGrafico`): em `options` vão `territory_ids` (as
  unidades na tela, só as do catálogo territorial; com todos os municípios ou nos estados, nenhuma), `exploration_operation`
  (a família: distribuição → `density` ou `counts`, conforme o indicador; espacial → `spatial`; tendência → `temporal`;
  rotatividade → `rotation`), `exploration_indicator`, `comparison_indicator` e `temporal_indicator` (o indicador),
  `period_filter` (a competência) ou `period_filters` (a janela da tendência), `painel_familia` e a data local do navegador
  (`conversation_today`, para "últimos N anos"). O estado do gráfico vai também como está: `painel_indicador`,
  `painel_nivel`, `painel_municipios` (a escolha das unidades, inclusive "Todos"), `painel_competencia`, `painel_janela`,
  `painel_referencia` e, desde 23/10/2026, `painel_vista` (`grafico`, `mapa` ou `lado`), `painel_mapa_disponivel` (se o
  mapa pode mostrar a análise agora) e `painel_resumo` (a frase-resumo do motor). Antes de o gráfico informar o contexto,
  `painel_familia` vai nulo: a conversa responde no formato do gráfico, nunca com orientações das telas que saíram. Numa
  planilha, vão também as escolhas das colunas e os nomes da unidade e do grupo (`rotulos`). O backend tira as chaves
  `painel_*` e `rotulos` das opções antes do pré-exame e do intérprete: nada delas vai ao provedor de IA, e a frase-resumo,
  que traz valores da base, fica só no backend local;
- os comandos da conversa incluem os grupos da distribuição ("divida em quintis", "sem os grupos") e a referência por
  critério ("a de maior densidade como referência"): o Território de referência abre com o atributo citado e, desde
  25/10/2026, o operador do "maior" ou "menor"; a relação, a delimitação e o valor de corte são escolha da pessoa (a lista de
  candidatos, com "usar o primeiro", saiu em 24/10/2026);
- **ambiguidades** continuam com alternativas em botões (`CATALOGO_LOCAL`), e nada é calculado. Escolher uma alternativa
  reinterpreta o pedido com a escolha; se a resposta não trouxer o campo `painel`, a operação escolhida vira a família ou a
  função equivalente (densidade e quantitativos → Distribuição com o indicador; evolução → Tendência; espacial e referência
  mais próxima → Análise espacial; comparação → Comparar; agregação → Juntar; ranking → Ordenar; critérios → Condições;
  relatório → Exportar);
- pendências da conversa continuam: "Compare Manaus" pergunta o outro município, e a resposta seguinte completa o pedido;
  a direção de uma ordenação é perguntada, nunca presumida;
- **vista do desenho** (desde 23/10/2026, com o mapa como segunda vista do gráfico): "ver no mapa", "mostre no mapa", "abra
  o mapa" e "agora o mapa" mandam à área o pedido `{ vista: "mapa" }`, pelo mesmo caminho dos demais comandos, e a conversa
  responde "Mostrei o mapa no lugar do gráfico. Para voltar, peça “volte ao gráfico”."; "volte ao gráfico", "mostre no
  gráfico" e "agora o gráfico" mandam `{ vista: "grafico" }` ("Voltei ao gráfico. …"). Quando a área informa que o mapa não
  está disponível (`mapaDisponivel: false`: nos estados, que não têm um ponto; numa planilha sem latitude e longitude; na
  visão Série temporal), nenhum pedido sai, e a resposta é o motivo informado pela área (`motivoSemMapa`), seguido de "Nada mudou no
  gráfico.". Já na vista pedida, a conversa só diz isso. Essas formas diretas são reconhecidas na tela, sem o intérprete;
  trocar de vista é estado visual e não recalcula (RQ-REP-06). Pedidos com mais do que a vista ("mostre o Pará no mapa",
  "onde ficam os municípios com menos de 1 médico por mil?", "a quantidade no gráfico") vão ao intérprete local, que devolve
  o comando com `vista` (ver [conversação incremental](CONVERSACAO_INCREMENTO_FN.md), "Conversa no gráfico"). Pelo
  intérprete com o provedor, os atos `show_map` e `show_chart` têm o mesmo tratamento;
- "agora a tabela" responde que a tabela fica em Detalhes, abaixo do gráfico (ou do mapa); nada é recalculado;
- **resumo do que está na tela** (desde 23/10/2026): "o que esse gráfico mostra?", "resuma o gráfico", "explique o
  resultado", "o que estou vendo?" e variações próximas, sem outro pedido junto, são respondidos na tela com a frase-resumo
  verificada do motor (`ContextoDoGrafico.resumo`, a mesma da área), como veio, sem paráfrase; sem gráfico calculado, "Ainda
  não há um gráfico calculado para resumir.". Nada vai ao intérprete nem ao provedor de IA. Um pedido que muda a análise
  ("o que esse gráfico mostra em 2023?") ou pede outra forma ("explique de forma mais simples") segue para a interpretação;
- "volte ao resultado anterior" reabre a análise anterior do Histórico, da mesma fonte, sem recalcular;
- outras perguntas sobre o que está na tela usam o resultado do gráfico guardado na sessão (`displayed_result_id`).

**Continuidade (desde 21/10/2026).** Um pedido sem territórios usa os que estão no gráfico, e a resposta diz quais. Um
pedido só com o período ("E nos últimos 5 anos?") continua a análise. "Últimos N anos" e "último ano" (AT-34) são contados
até o último período da base e até hoje, pela data local do navegador: quando as duas contagens dão as mesmas competências,
o período é aplicado; quando divergem, a conversa oferece as duas leituras como alternativas, sem escolher. Essas
continuações são resolvidas no backend, sem o provedor de IA. A interpretação conta com exemplos da
[biblioteca conversacional](BIBLIOTECA_CONVERSACIONAL.md), internos e invisíveis na tela.

**Privacidade.** Nenhum dado, arquivo, nome de campo ou valor da base vai ao provedor de IA. A planilha é reenviada só ao
backend local; o contexto do gráfico vai ao intérprete local, e o provedor recebe apenas o pedido sanitizado e estados
enumerados. Sem o provedor, os pedidos sobre o gráfico, a escolha dos dados e as respostas locais continuam disponíveis; a
caixa avisa que as perguntas livres estão indisponíveis.

## Exportação

As exportações da análise ficam na função **Exportar** da área (CSV com precisão integral, avaliabilidade e motivo;
Imprimir/PDF; método e parâmetros). O diálogo de Nova sessão oferece o CSV da análise em exibição e Imprimir / PDF. Não há
exportação consolidada de todas as análises da sessão.

## O que saiu em 22/10/2026

| Saiu | Onde fica agora |
|---|---|
| Catálogo de 12 análises (carrossel) | Famílias e funções da área; a conversa continua aceitando os pedidos |
| Preparação (categoria, período, abrangência territorial, condições, "Calcular e mostrar resultado") | Escolhas dentro da área (indicador, competência, municípios, funções); colunas da planilha no painel "Colunas" |
| Resultados em abas (Mapa, Gráficos, Tabela), cabeçalho do resultado e visuais por análise | Gráfico de bolhas e Detalhes (Tabela, Não avaliáveis, Método e procedência) da área |
| Mapa de pontos | Ficou fora da página de 22 a 23/10/2026; desde então, volta como segunda vista do gráfico (Gráfico, Mapa e Lado a lado, na área), e a conversa troca a vista ("ver no mapa", "volte ao gráfico") |
| Investigação progressiva e diagnósticos compostos ("Acrescentar ao diagnóstico") | Histórico de análises |
| Navegação "Início" e "Resultados"; abas "1. Preparação" e "2. Resultados" | A página é sempre o gráfico |
| Comandos "volte para a seleção de territórios", "voltar à preparação", "mostre os resultados" e "quero analisar vários períodos" | Pedidos ao gráfico pela conversa |

A API não mudou com essa saída: `/api/analyze`, `/api/preflight` e as capacidades continuam, com os mesmos contratos.

## Componentes e fronteiras

- `App.tsx`: estrutura da página, fonte de dados, Histórico, Nova análise e Nova sessão; monta a área de análise.
- `BarraDaFonte.tsx`, `ColunasDaPlanilha.tsx` e `HistoricoDeAnalises.tsx`: fonte, painel "Colunas" e Histórico.
- `AnalysisAssistant.tsx` e `ChatFloatingBox.tsx`: a conversa e a caixa flutuante.
- `conversaGrafico.ts` e `paginaUnica.ts`: funções puras da conversa (campo `painel` → pedido, contexto → opções, comandos) e
  da estrutura (resumo da fonte, rótulos, colunas, Histórico, CSV da sessão), com os tipos do contrato da área.
- `conversationSession.ts`, `SessionPrivacy.tsx` e `WorkspaceDialog.tsx`: sessão, aceite e diálogos acessíveis.
- `AreaDeAnalise.tsx` e os `Painel*`: a área de análise.

Testes: `frontend/tests/paginaUnica.test.mjs` e `frontend/tests/conversaGrafico.test.mjs` (unitários; este também cobre a
vista do desenho, o pedido de resumo e as chaves novas do contexto); os roteiros de navegador `backend/tests/ui_pagina_unica.py`
(suítes `bloco1` e `base-versionada`) e `backend/tests/ui_conversa_grafico.py` (suítes `conversa`, só com os canais locais,
e `gemini-simulado`, com o provedor simulado e a conferência de que nada da base chega a ele, nem a frase-resumo). Este
roteiro confere, com os municípios na tela, "ver no mapa" (`area-de-analise` com `data-desenho="mapa"`), "volte ao gráfico"
(`data-desenho="grafico"`) e "o que esse gráfico mostra?" (a resposta traz o texto de `analise-resumo`) e, nos estados, "ver
no mapa" respondido com o motivo, sem mudar a vista. O que cobriam os roteiros do fluxo clássico, e onde essa cobertura
está agora, fica em [`backend/tests/legado/README.md`](../backend/tests/legado/README.md).
