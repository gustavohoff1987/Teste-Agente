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
Ela mantém os identificadores de sempre (`#assistente`, `#assistant-input`, `latest-reply`, agora na última resposta do
histórico).

### Histórico da conversa

Desde 26/10/2026 (Frente VI da missão de 26/10/2026), a caixa mostra a conversa inteira, em ordem (`chat-historico`, papel
`log`): cada mensagem da pessoa aparece na hora, exatamente como ela escreveu, num balão discreto à direita
(`chat-mensagem` com `data-papel="usuario"`), e cada resposta do agente, à esquerda, com o rosto (`data-papel="agente"`).
A comunicação de indisponibilidade da conversa aparece como resposta do sistema, numa faixa suave com o título
"Assistente conversacional temporariamente indisponível" (`data-papel="aviso"`), no ponto da conversa em que aconteceu.
- **Tipografia (28/10/2026).** A letra das mensagens (15 px; 14 no celular) passa a valer também nos balões do agente, que
  herdavam a classe da antiga "última resposta" (`latest-reply`): a letra deles era menor que a da pessoa, a resposta longa era
  cortada em 140 px (90 no celular), com rolagem dentro do balão, e a hora ficava ao lado do texto; agora o balão mostra a
  resposta inteira, com a hora embaixo. Sobem os textos de apoio da caixa: o nome do agente no cabeçalho (15 px), a linha de
  apoio dele (12 px), o aviso de serviço indisponível (13 px; 12 no celular), a hora (12 px), "Enter para enviar" e
  "Privacidade da conversa" (12 px) e o campo de mensagem (15 px; 16 no celular, sem zoom ao focar), na Inter embutida no app
  ([tipografia](PAINEL_INTEGRADO_INTERFACE.md#tipografia)).
- **Visual (26/10/2026).** Letra maior (15 px; 14 px no celular), cada mensagem num balão com contorno e sombra leve (a da
  pessoa, à direita, no tom de realce; a do agente, à esquerda, com a borda de destaque), a hora no canto do balão (HH:MM,
  no relógio do navegador, como conteúdo gerado do atributo `data-hora`, fora do texto da mensagem), os parágrafos da
  resposta separados, o rótulo do começo do parágrafo em negrito ("Maior valor de densidade:") e os exemplos de pedido entre
  aspas (“…”) em destaque. A tela só realça (`blocosDoTexto`, em `historicoConversa.ts`): o texto da resposta é o mesmo, e as
  quebras entre parágrafos continuam nele, escondidas.
- **Rolagem.** O histórico rola sozinho (o campo de mensagem fica sempre à vista), abaixo da orientação, separado dela por
  uma linha, com a barra de rolagem visível. Quem envia vai ao fim, para ver a resposta; quando a resposta não cabe junto com
  a pergunta, a pergunta curta fica no alto e o começo da resposta logo abaixo, como num aplicativo de mensagens
  (`posicaoDaRolagem`, 26/10/2026; antes, a rolagem ia sempre ao fim, e a pergunta sumia acima da área visível). Quem está
  lendo mensagens antigas não é puxado quando a resposta chega: aparece o botão "Ir para a mensagem mais recente"
  (`chat-ir-ao-fim`).
- **Estados.** Enquanto a resposta não chega, "Interpretando o pedido…" fica no fim do histórico (`chat-processando`); depois
  de 12 s, "Ainda estou trabalhando no seu pedido…"; depois de 45 s, "O serviço de conversa está demorando mais que o normal;
  aguarde mais um pouco…". Aos 100 s, a tela interrompe a espera e responde com o aviso "A resposta demorou mais que o
  esperado" ("Interrompi a espera para você não ficar parado. Tente de novo em instantes ou siga pelos botões e controles da
  plataforma; o gráfico continua disponível."), sem código nem mensagem técnica (26/10/2026). Uma falha nunca apaga a
  pergunta: o aviso cordial entra como resposta, sem código HTTP nem mensagem técnica (limite de consultas só quando o
  provedor o confirmou; nas demais causas, a indisponibilidade).
- **Sem duplicar.** Cada mensagem tem um identificador único; renderizações e reenvios do mesmo estado não a repetem.
- **Navegação.** O histórico fica com a caixa, fora da área de análise: trocar a vista, a aba, o indicador, abrir o
  Histórico, a Nova análise e a troca de fonte não o apagam. Nova sessão encerra a conversa, como antes.
- **Original e cópia triada.** A tela guarda e mostra o texto original; ao backend vai a janela das 8 mensagens mais
  recentes (`turnos`, sem os avisos), que ele tria antes do provedor. O histórico visual não depende do que vai ao provedor
  e não gera chamada ao Gemini.
- **Tamanhos de tela.** Desde 26/10/2026, a caixa tem até 440 px de largura (470 px na abertura) e até 84% da altura da
  janela (no máximo 800 px), e a área da conversa tem pelo menos 220 px; no celular, ancorada embaixo, ocupa a largura e até
  80% da altura. Depois da primeira mensagem, a orientação do alto fica com letra menor (`data-compacta`), e a conversa ganha
  a área. A conversa vale para a sessão da aba: quando a sessão termina (Nova sessão, expiração por inatividade ou o servidor
  reiniciado), a página recomeça limpa, sem guardar o histórico em armazenamento persistente.
- **Situação do serviço.** Sem o Gemini disponível, uma faixa curta no alto da caixa (`chat-estado-do-servico`) diz que o
  recurso de conversa está temporariamente limitado e que os botões, os controles e os pedidos diretos sobre o gráfico
  continuam; "Verificar de novo" só consulta a situação, sem chamar o provedor.

**Abertura.** Antes dos dados, a caixa fica aberta e mais larga, perguntando "O que você quer analisar? Prefere usar os dados
do Brasil ou enviar os seus?", com **Usar dados do Brasil** e **Enviar meus dados**, as mesmas duas entradas da área de
análise (24/10/2026; o botão "Modelo de planilha XLSX", `chat-fonte-modelo`, saiu). "Enviar meus dados", pelo botão ou
pedido em palavras, abre a mesma janela de envio da área ("Abri a janela de envio: escolha o arquivo CSV ou Excel. O modelo de
planilha também está nela. Depois, confira as colunas no painel Colunas, no alto da página."). Um cumprimento antes dos dados
recebe "Olá! O que você quer analisar? Prefere usar os dados do Brasil ou enviar os seus?". Depois, ela fica compacta, com uma orientação curta para cada etapa: enquanto os dados do Brasil são
preparados, "Estou preparando os dados do Brasil. Em seguida, escolha os territórios que quer analisar."; com os dados prontos
e sem territórios escolhidos (a base abre sem seleção automática), "Os dados estão prontos. Escolha os territórios na Seleção
de Territórios ou me diga quais quer ver: o nome de um estado ou de municípios, ou “todos os estados”." (numa planilha, sem os
exemplos da base do Brasil; desde 24/10/2026, também no nível Estados sem nenhum estado marcado); nos estados, "Escolha no
gráfico quais estados abrir, ou me diga quais municípios quer ver." (na
planilha, com os nomes escolhidos, por exemplo "quais províncias abrir, ou … quais distritos"); e, com as unidades na tela,
"Peça mudanças no gráfico ou pergunte sobre ele, por exemplo: “…”, “…” ou “…”.", com três exemplos do que a análise aberta
faz (`exemplosDaAnalise`, 26/10/2026). Os exemplos nunca citam lugares (um nome fora da análise da pessoa confunde), usam o
indicador em uso e mudam conforme a conversa avança: na Distribuição, “os 5 municípios com maior densidade”, “compare o de
maior e o de menor densidade”, “municípios com menos de 1 médico por mil”, “mostre a tendência anual”, “explique esse
resultado” e “ver no mapa”; na Tendência, “mostre a trajetória anual”, “mostre a série temporal” e a comparação pelos
extremos; na Análise Espacial, “use como referência o município de maior densidade”, “os 5 mais distantes” e “municípios a
mais de 150 km”; na Rotatividade, “explique esse resultado” e “mostre a distribuição”. Cada exemplo é um comando que a
conversa entende. Até 26/10/2026, os exemplos eram fixos e citavam lugares ("mostre o Pará", "use Belém como referência",
"compare Manaus e Tefé"); as respostas do agente que davam exemplos com nomes também passaram a exemplos sem lugares
(“compare o de maior e o de menor densidade”, “use como referência o município de maior densidade”, “a mais de 150 km”).

**Escolha da fonte pela conversa.** "Usar dados do Brasil" e "enviar meus dados" fazem o mesmo que os botões, sem o provedor
de IA. Escolhidos os dados do Brasil, a resposta diz "Dados do Brasil escolhidos. Vou prepará-los; em seguida, escolha os
territórios na Seleção de Territórios ou me diga quais quer ver: o nome de um estado ou de municípios, ou “todos os
estados”."

**Antes dos dados.** Perguntas sobre o agente, a privacidade e os conceitos ("Como se calcula a densidade?") e sobre o
conteúdo da base do Brasil continuam respondidas localmente. Desde 26/10/2026, um pedido de análise feito antes da escolha
dos dados (comparar, ordenar, juntar, os N maiores, ver ou analisar territórios e indicadores; `pedido_de_analise`, em
`conversa_grafico.py`) recebe na hora, sem o provedor de IA, o lembrete "Para fazer essa análise, primeiro escolha os dados:
use os dados do Brasil ou envie os seus, em CSV ou Excel. Assim que a base estiver pronta, sigo com o seu pedido." (a tela
manda `lembrar_base` a `/api/llm/interpret`, que responde com `aguarda_base`), e os dois botões da escolha ficam em destaque
(`data-lembrete`) até a pessoa escolher; antes, o pedido ia ao intérprete com o provedor e podia ficar esperando até o prazo
das chamadas. O pedido fica guardado: quando a base fica pronta, ele segue pelo caminho completo (o intérprete local e, sem
resposta local, o comando já interpretado ou o intérprete contextual), com a resposta começando por "Com os dados prontos,
sigo com o seu pedido."; antes, sem resposta local, o pedido guardado se perdia. "Certo, quantos tem?" antes da escolha
recebe "Para continuar, escolha os dados: “Usar dados do Brasil” ou “Enviar meus dados”."

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
  mapa pode mostrar a análise agora) e `painel_resumo` (a frase-resumo do motor); desde 28/10/2026, na Análise Espacial,
  `painel_consulta` (a Escolha dos territórios em exibição, para "e em todo o país?" trocar só de onde a referência parte). Antes de o gráfico informar o contexto,
  `painel_familia` vai nulo: a conversa responde no formato do gráfico, nunca com orientações das telas que saíram. Numa
  planilha, vão também as escolhas das colunas e os nomes da unidade e do grupo (`rotulos`). O backend tira as chaves
  `painel_*` e `rotulos` das opções antes do pré-exame e do intérprete: nada delas vai ao provedor de IA, e a frase-resumo,
  que traz valores da base, fica só no backend local;
- desde 28/10/2026, o pedido de proximidade com uma condição ("o mais próximo de X com densidade acima de 2", "o de menor
  densidade e o mais próximo dele com densidade de no mínimo 1,5 por mil habitantes") vira a Escolha dos territórios da
  Análise Espacial (campo `consulta` do comando; a área o confere com `lerConsulta`), e não as Condições: o extremo vai para
  a base, pelas ordens do motor, e a condição para a referência; quando o motor calcula, a conversa lê a referência mais
  próxima e a distância e oferece, em botões, "Procurar em todo o país" e "Só no mesmo estado de cada um"
  ([conversa no gráfico](CONVERSACAO_INCREMENTO_FN.md), [diálogo governado](DIALOGO_GOVERNADO.md));
- os comandos da conversa incluem os grupos da distribuição ("divida em quintis", "sem os grupos") e a referência por
  critério ("a de maior densidade como referência"): desde 27/10/2026, a Escolha dos territórios abre na aba Referência com
  um filtro do atributo citado e, desde 25/10/2026, o operador do "maior" ou "menor" ("acima de" ou "abaixo de"); o valor é
  escolha da pessoa (a lista de candidatos, com "usar o primeiro", saiu em 24/10/2026; o painel Território de referência, em
  27/10/2026). A referência pelo nome vira os marcados da Referência;
- **ambiguidades** continuam com alternativas em botões (`CATALOGO_LOCAL`), e nada é calculado. Desde 26/10/2026, a
  resposta também pode ser escrita ("Município.", "a do Pará", "a de janeiro", "o primeiro"): a tela guarda a pergunta com
  as alternativas e a envia na memória da conversa (`conversa`), e o gestor de diálogo do backend escolhe a alternativa, como
  o clique ([diálogo governado](DIALOGO_GOVERNADO.md)). Escolher uma alternativa reinterpreta o pedido com a escolha; se a resposta não trouxer o campo `painel`, a operação escolhida vira a família ou a
  função equivalente (densidade e quantitativos → Distribuição com o indicador; evolução → Tendência; espacial e referência
  mais próxima → Análise espacial; comparação → Comparar; agregação → Juntar; ranking → Ordenar; critérios → Condições;
  relatório → Exportar);
- pendências da conversa continuam: "Compare Manaus" pergunta o outro município, e a resposta seguinte completa o pedido;
  a direção de uma ordenação é perguntada, nunca presumida;
- **continuidade pelo gestor de diálogo** (desde 26/10/2026): correções ("Não, o estado."; "Não, eu queria a evolução"),
  "não era isso que eu queria" e "desfaz" (a tela volta ao estado do gráfico antes da última mudança feita pela conversa, da
  pilha que ela guarda, até 8 estados), "volta para a comparação anterior", trocas ("troca o primeiro pelo segundo"),
  inclusões e retiradas, perguntas sobre o resultado em exibição ("qual deles tem a maior densidade?", respondidas com os
  valores e a ordem do motor, sem mudar o gráfico), explicações em quatro registros e perguntas sobre o estado da tela. Uma
  explicação de classe da Tendência abre "Entenda esta análise" com a classe destacada
  (`analise-apresentacao-destaque`), sem recalcular;
- **comparação indireta** (desde 26/10/2026): "compare o de maior e o de menor densidade", "comparar os municípios de maior
  e menor densidade", "compare os extremos", "compare os dois (três) maiores" e "qual a diferença entre o maior e o menor?"
  identificam quem entra pelas ordens do motor sobre o gráfico em exibição (com os empates) e abrem a comparação lado a lado,
  sem pedir os nomes; no gráfico de bolhas, as demais bolhas esmaecem ([área de análise](PAINEL_INTEGRADO_INTERFACE.md)).
  No plural sem quantidade ("compare os mais populosos"), a conversa pergunta se são os dois ou os três, com as duas
  alternativas em botões. Com um estado citado que não está no gráfico ("… do Pará"), a resposta mostra primeiro os
  municípios dele e traz o campo `continuar` (o pedido de continuação); quando o motor calcula o gráfico novo (outro
  resultado em exibição, ou depois de 8 s sem gráfico novo), a tela envia esse pedido sozinha, sem mostrá-lo como mensagem da
  pessoa, e a comparação aparece; na pergunta da diferença, a continuação lê a diferença calculada pelo motor. No máximo duas
  continuações seguidas; um pedido novo da pessoa cancela a que ainda esperava;
- **vista do desenho** (desde 23/10/2026, com o mapa como segunda vista do gráfico): "ver no mapa", "mostre no mapa", "abra
  o mapa" e "agora o mapa" mandam à área o pedido `{ vista: "mapa" }`, pelo mesmo caminho dos demais comandos, e a conversa
  responde "Mostrei o mapa no lugar do gráfico. Para voltar, peça “volte ao gráfico”."; "volte ao gráfico", "mostre no
  gráfico" e "agora o gráfico" mandam `{ vista: "grafico" }` ("Voltei ao gráfico. …"). Quando a área informa que o mapa não
  está disponível (`mapaDisponivel: false`: nos estados, que não têm um ponto; numa planilha sem latitude e longitude; na
  visão Série temporal), nenhum pedido sai, e a resposta é o motivo informado pela área (`motivoSemMapa`), seguido de "Nada mudou no
  gráfico.". Desde 26/10/2026, o motivo vai também ao backend local (`painel_motivo_sem_mapa`), para "o que estou vendo no
  mapa?" responder com ele. Já na vista pedida, a conversa só diz isso. Essas formas diretas são reconhecidas na tela, sem o intérprete;
  trocar de vista é estado visual e não recalcula (RQ-REP-06). Pedidos com mais do que a vista ("mostre o Pará no mapa",
  "onde ficam os municípios com menos de 1 médico por mil?", "a quantidade no gráfico") vão ao intérprete local, que devolve
  o comando com `vista` (ver [conversação incremental](CONVERSACAO_INCREMENTO_FN.md), "Conversa no gráfico"). Pelo
  intérprete com o provedor, os atos `show_map` e `show_chart` têm o mesmo tratamento;
- "agora a tabela" responde que a tabela fica em Detalhes, abaixo do gráfico (ou do mapa); nada é recalculado;
- **resumo do que está na tela** (desde 23/10/2026): "o que esse gráfico mostra?", "resuma o gráfico", "o que estou
  vendo?" e variações próximas, sem outro pedido junto, são respondidos na tela com a frase-resumo verificada do motor
  (`ContextoDoGrafico.resumo`, a mesma da área), como veio, sem paráfrase; sem gráfico calculado, "Ainda não há um gráfico
  calculado para resumir.". Nada vai ao intérprete nem ao provedor de IA. Desde 26/10/2026, "explique o resultado" e as
  demais formas com "explique", "explica", "explicar", "descreva", "descreve" ou "descrever" vão ao gestor de diálogo do backend, que responde com a frase-resumo
  e os fatos de cada território, copiados do motor e conferidos. Um pedido que muda a análise ("o que esse gráfico mostra
  em 2023?") ou pede outra forma ("explique de forma mais simples") segue para a interpretação;
- "volte ao resultado anterior" reabre a análise anterior do Histórico, da mesma fonte, sem recalcular;
- outras perguntas sobre o que está na tela usam o resultado do gráfico guardado na sessão (`displayed_result_id`). Até
  26/10/2026, a tela enviava esse identificador vazio: lia `result_id` na resposta guardada, que a normalização da área traz
  como `resultId`. Agora envia o do resultado em exibição.

**Continuidade (desde 21/10/2026).** Um pedido sem territórios usa os que estão no gráfico, e a resposta diz quais. Um
pedido só com o período ("E nos últimos 5 anos?") continua a análise. "Últimos N anos" e "último ano" (AT-34) são contados
até o último período da base e até hoje, pela data local do navegador: quando as duas contagens dão as mesmas competências,
o período é aplicado; quando divergem, a conversa oferece as duas leituras como alternativas, sem escolher. Essas
continuações são resolvidas no backend, sem o provedor de IA. A interpretação conta com exemplos da
[biblioteca conversacional](BIBLIOTECA_CONVERSACIONAL.md), internos e invisíveis na tela.

**Privacidade.** Nenhum arquivo, linha, registro individual, identificador, nome de campo ou credencial vai ao provedor de
IA. A planilha é reenviada só ao backend local; o contexto do gráfico vai ao intérprete local. Ao provedor vão a mensagem
triada, a janela da conversa triada, estados enumerados e o cartão do contexto montado pelo backend: a tela e o resultado
agregado em exibição (territórios, valores com as unidades, períodos, classes, notas e a frase-resumo), decisão de
26/10/2026. Sem o provedor, os pedidos sobre o gráfico, o gestor de diálogo, a escolha dos dados e as respostas locais
continuam disponíveis; o pedido que dependeria do provedor recebe, no histórico, a comunicação cordial de indisponibilidade.

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
- `historicoConversa.ts`: modelo puro do histórico (ordem, ids, janela enviada, rolagem e avisos cordiais).
- `conversationSession.ts`, `SessionPrivacy.tsx` e `WorkspaceDialog.tsx`: sessão, aceite e diálogos acessíveis.
- `AreaDeAnalise.tsx` e os `Painel*`: a área de análise.

Testes: `frontend/tests/paginaUnica.test.mjs`, `frontend/tests/conversaGrafico.test.mjs` (unitários; este também cobre a
vista do desenho, o pedido de resumo e as chaves novas do contexto) e `frontend/tests/historicoConversa.test.mjs` (o
histórico); os roteiros de navegador `backend/tests/ui_pagina_unica.py` (suítes `bloco1` e `base-versionada`) e
`backend/tests/ui_conversa_grafico.py` (suítes `conversa`, só com os canais locais e o aviso cordial, e `gemini-simulado`,
com o provedor simulado: redação conferida, reserva de contrato, limite e queda simulados com recuperação e a conferência do
que chega a ele). Os dois modos conferem o histórico: ordem, sem duplicar, navegação, original na tela, rolagem e celular. Este
roteiro confere, com os municípios na tela, "ver no mapa" (`area-de-analise` com `data-desenho="mapa"`), "volte ao gráfico"
(`data-desenho="grafico"`) e "o que esse gráfico mostra?" (a resposta traz o texto de `analise-resumo`) e, nos estados, "ver
no mapa" respondido com o motivo, sem mudar a vista. O que cobriam os roteiros do fluxo clássico, e onde essa cobertura
está agora, fica em [`backend/tests/legado/README.md`](../backend/tests/legado/README.md).
