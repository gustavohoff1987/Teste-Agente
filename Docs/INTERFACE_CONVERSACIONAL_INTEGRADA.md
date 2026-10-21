# Interface conversacional integrada

A investigação ocupa toda a largura disponível, até 1.920 px. O banner conserva o texto, as cores
e as proporções compactas. O personagem é o SVG original de `BrandAvatar.tsx`, reutilizado sem
alterar rosto, vestimentas, proporções ou cores. Não há personagem novo nem imagem gerada.

## Navegação e sessão

| Ação | Comportamento |
|---|---|
| Início | Volta ao banner e à apresentação do agente. Preserva sessão, conversa, preparação e resultados. |
| Nova sessão | Abre diálogo com exportação CSV, Imprimir / PDF, Continuar nesta sessão e Iniciar nova sessão. A confirmação revoga a sessão no servidor e recarrega a aplicação. |
| Nova análise | Abre o catálogo diretamente no primeiro uso; com análise em andamento, oferece análise independente ou acréscimo ao diagnóstico. |
| Histórico | Reabre resultados existentes, sem recálculo e sem restaurar parâmetros implicitamente. Identifica análise independente e componentes. Fecha por clique externo ou Escape. |
| Resultados | Oculta a preparação, expande e navega diretamente para o conteúdo calculado. Mantém conversa acessível e não altera dados nem executa análises. |
| Painel integrado | Só com a base do Brasil pronta: abre o painel integrado de bolhas em tela grande, o mesmo do botão "Abrir o painel integrado" junto da fonte atual. Ver [Painel integrado: a tela](PAINEL_INTEGRADO_INTERFACE.md). |

“Alterar a preparação” e “Voltar às opções” tornam os controles visíveis novamente. Os controles
se distribuem em mais de uma linha em telas pequenas, sem menu lateral.
Diálogos nativos contêm o foco e devolvem-no ao controle acionador; Escape cancela. O encerramento
em andamento bloqueia novas confirmações. Falha de rede no encerramento mantém o diálogo e o
conteúdo da sessão, permitindo nova tentativa ou cancelamento.

Uma sessão pode conter diversas análises e diagnósticos. A transcrição, os arquivos importados,
as seleções, os parâmetros e os resultados ficam na memória da aba. Recarregar descarta o
histórico local. Encerramento e expiração continuam usando os limites e mecanismos existentes.
Nenhum grupo ou resultado é salvo no armazenamento persistente do navegador.

## Condução da investigação

O agente apresenta a escolha da fonte desde a entrada. Depois acompanha o reconhecimento,
as escolhas de colunas e parâmetros (sem confirmações de campo, decisão D1 de 19/10/2026), a escolha
de modalidade, recortes, períodos e execução. A preparação
existente continua verificando requisitos no backend. O catálogo apresenta a disponibilidade
informada pelo pré-exame; requisitos ausentes podem ser examinados e resolvidos na preparação.

A transcrição permanece em memória para continuidade, sem histórico visual acumulado. A última
resposta do agente permanece junto ao campo de digitação, em uma faixa contextual ancorada à base da janela dentro da investigação. O usuário
pode continuar perguntando durante a exploração de gráficos, mapas e tabelas. Alternativas de
interpretação permanecem acessíveis na conversa. Não há coluna reservada nem janela arrastável fora do painel integrado; nele,
a mesma conversa (última resposta, alternativas e campo de envio, com os mesmos identificadores) fica numa caixa flutuante com o
rosto do agente, arrastável e minimizável ([Painel integrado: a tela](PAINEL_INTEGRADO_INTERFACE.md)).

**Continuidade da conversa (desde 21/10/2026).** O estado estruturado da conversa é a própria preparação: a análise,
os territórios da abrangência, os períodos, o indicador e a categoria. Cada mensagem os envia ao intérprete local, e a
sessão do backend guarda o contexto verificado. Um pedido que não cita territórios usa os já escolhidos, e a resposta
diz quais ("Mantive os 3 territórios já escolhidos na conversa: …"). Um pedido só com o período ("E nos últimos 5
anos?") continua a análise ativa. "Últimos N anos" e "último ano" (AT-34) são contados até o último período da base e
até hoje, pela data local do navegador:
- quando as duas contagens dão as mesmas competências, o período é aplicado e dito na resposta;
- quando divergem, a conversa apresenta as duas leituras como alternativas, sem escolher, e cada alternativa envia o
  pedido com os anos explícitos ("Comparação de 2020 a 2024");
- sem o número ("últimos anos"), a conversa pergunta quantos;
- na virada do ano, sem a data local, ela pede os anos.

Verbos comuns ("fazer", "faça", "veja", "saber") não impedem a interpretação local. O pedido feito antes da escolha dos
dados é interpretado de novo quando a base fica pronta, e os municípios citados nele vão para a abrangência, sem que
o usuário precise repeti-los. Essas continuações são resolvidas no backend, sem o provedor de IA. Antes, "quero fazer a
comparação dos últimos 5 anos" fazia a conversa perguntar de novo pelos municípios e descartava o período.

Com um resultado apresentado, a conversa também muda a apresentação sem recalcular: "mostre no gráfico", "agora a
tabela" e "ver no mapa" abrem a aba do resultado, e "volte ao resultado anterior" reabre o resultado calculado antes
do apresentado ("Resultado anterior reaberto, sem recalcular."; sem resultado anterior, a conversa avisa). Formas
diretas são reconhecidas na interface (`viewCommand` e `previousResultCommand` em `workspaceNavigation.ts`); as demais
chegam ao intérprete como atos de diálogo. A interpretação conta com exemplos da
[biblioteca conversacional](BIBLIOTECA_CONVERSACIONAL.md), internos e invisíveis na tela.

Os resultados indicam que os cálculos pertencem ao motor determinístico. O agente não altera
valores e o canal LLM continua recebendo apenas o conteúdo autorizado pelos contratos existentes.
Métodos, fontes e limitações permanecem nos componentes analíticos e no registro técnico avançado.
As preferências de movimento reduzido desativam transições, animações e rolagem suave.

## Análises independentes e diagnósticos

1. Executar a primeira análise cria uma análise independente identificada.
2. Nova análise → Iniciar uma análise independente preserva o resultado anterior no Histórico
   e abre uma preparação para outro grupo.
3. Nova análise → Acrescentar ao diagnóstico atual mantém o grupo atual; a próxima execução
   acrescenta um componente identificado, em ordem, com resultados e parâmetros próprios.
4. Abrir um componente conserva filtros e seleção visual desse resultado; o Histórico permite
   voltar a outro diagnóstico. O destaque territorial entre componentes continua condicionado à
   política já existente em `investigation.ts`.
5. Uma solicitação idêntica recupera o resultado existente. A organização pode referenciar esse
   resultado em outro grupo sem novo cálculo, sem duplicar linhas e sem mudar a identidade original.

Pedidos explícitos como “análise independente” ou “acrescente ao diagnóstico” definem somente a
intenção de apresentação no navegador. Prefixos explícitos como “Faça uma análise independente da”
e “Acrescente ao diagnóstico atual” são separados do pedido enviado ao interpretador local;
territórios, períodos e demais termos permanecem sujeitos às validações existentes. A mensagem
original permanece na conversa e no registro do pedido. A interpretação analítica mantém seus contratos. Se outra
execução puder modificar um diagnóstico e a intenção estiver indefinida, o diálogo pede apenas
essa escolha antes de calcular. Nenhuma interpretação executa cálculos automaticamente.

Compor não soma, combina, interpola, deduplica nem harmoniza valores. Cada componente conserva
fonte, recorte, categorias, períodos, unidades, método, limitações e parâmetros. Diferenças que
bloqueiam a coordenação territorial são indicadas nos cartões. Mesmo quando o destaque é
compatível, isso não certifica comparabilidade de valores. Resultados de fontes diferentes
continuam consultáveis individualmente; não há reinterpretação de unidades ou denominadores.

## Exportação

CSV exporta a tabela principal da análise em exibição. As tabelas de detalhe e as séries mantêm
seus controles próprios. O CSV filtrado continua exportando todo o filtro, conforme a tabela.
Imprimir / PDF usa a impressão do navegador e inclui a representação e a página da tabela em
exibição, mesmo quando o resultado está recolhido. O diálogo de Nova sessão não integra a impressão.

**Não existe exportação consolidada de todos os componentes por esses botões.** Para conservar
um diagnóstico ou sessão, reabra e exporte cada análise pelo Histórico. O diálogo explica essa
limitação antes do descarte. O JSON técnico mantém identidade, método, parâmetros e registro de
representação da análise e associação aos diagnósticos; fica somente em Opções técnicas avançadas.

## Componentes e fronteiras

- `App.tsx`: navegação, preparação existente, histórico e associação a diagnósticos.
- `diagnostics.ts`: referências ordenadas a resultados e intenção explícita de apresentação.
- `AnalysisAssistant.tsx`: contexto conversacional em memória, última resposta visível, escolhas e compositor contextual.
- `WorkspaceDialog.tsx`: confirmação acessível de análises e sessões.
- `PreviousAnalyses.tsx` e `InvestigationOverview.tsx`: consulta do histórico e componentes.
- `conversationSession.ts`: fechamento no servidor, incluindo criação de sessão ainda pendente.
- `workspaceNavigation.ts` e `styles.css`: fluxo único, responsividade, impressão e movimento reduzido.

Motor, API analítica, manifesto, dados originais, SPEC e SVG do personagem não são alterados.
A estabilização preserva “Quantos/Quantas” na proteção nominal da ponte de interpretação, sem
enviar identificadores ou dados da base ao provedor. Testes e evidências estão no
[relatório da interface](RASTREABILIDADE_INTERFACE_INTEGRADA_20261017.md) e na
[auditoria de estabilização](AUDITORIA_ESTABILIZACAO_20261018.md).

## Etapas operacionais, períodos e comparação

Somente uma área principal fica visível: **1. Preparação** ou **2. Resultados**. As duas aparecem
como abas: um contorno desce da aba ativa e envolve todo o conteúdo da etapa, para deixar claro o que
pertence à preparação (ou aos resultados); a aba Resultados fica esmaecida até haver um resultado. A
preparação começa com a orientação "Realize as configurações conforme a sua escolha.".

A seleção territorial faz parte da preparação. Na base oficial, ela fica na caixa **Abrangência
territorial** das configurações (descrita adiante). Nas bases importadas, e na base oficial com
significados alterados, um bloco de uma linha resume a seleção atual (por exemplo, “Territórios:
1 selecionado: ABREU E LIMA (PE)”) e só expande a busca quando o usuário escolhe “Escolher
territórios” ou “Alterar territórios”; “Concluir seleção” recolhe o bloco. Assim, a preparação
continua curta, sem a etapa própria de territórios nem a rolagem longa anterior. Em referência mais
próxima e critérios, a lista se chama “Municípios-alvo” e “Universo dos critérios”. Fora da
base oficial, no recorte nacional, o bloco só informa que há um único território (Brasil) e que a
escolha de municípios vale para a abrangência Municípios.
Voltar preserva seleção, opções e edição de períodos. “Retomar parâmetros” restaura a preparação
e a revalida. “Usar seleção na próxima análise” abre a preparação com a seleção territorial
expandida (na base oficial, a caixa Abrangência territorial); reutilizar referências abre a preparação. O Histórico e a navegação Resultados abrem
inclusive o mesmo resultado já selecionado.
Uma resposta assíncrona não agenda uma navegação posterior capaz de desfazer a escolha do usuário.
O carrossel de análises mantém a opção em exploração quando o pré-exame apenas atualiza sua
disponibilidade; selecionar outra análise continua abrindo a preparação correspondente.

“Usar dados do Brasil.” aciona a mesma seleção de fonte dos botões. “Volte para a seleção de
territórios.” abre a preparação com a seleção territorial expandida; os demais comandos de
navegação mudam somente a área visível. “Quero analisar vários
períodos.” abre a edição quando a modalidade admite múltiplas competências; nas demais, explica
que a operação exige uma competência e indica as modalidades apropriadas. Não altera o método.

No seletor múltiplo, a competência única já escolhida é preservada. Quando todas as competências
vêm incluídas por padrão (por exemplo, na evolução temporal), elas aparecem sem marca, com o aviso
"Todos os períodos estão incluídos. Para analisar só alguns, clique neles:", e o primeiro clique
escolhe só a competência clicada. Depois dessa escolha, ou de "Todos os períodos disponíveis", cada
clique acrescenta ou retira uma competência (as marcadas têm ✓ e fundo preenchido; as retiradas,
contorno tracejado). O usuário também escolhe um intervalo contínuo ("de janeiro de 2014 até junho
de 2015") ou limpa a escolha; sem nenhuma competência, precisa selecionar antes de concluir. Durante o
cálculo, a lista fica bloqueada. Uma linha
abaixo descreve a escolha ("4 competências, de janeiro de 2014 a junho de 2015"). Ao voltar para
período único, a primeira competência selecionada permanece. As competências não são somadas como pessoas únicas. Nas bases
importadas, as condições avançadas permanecem acessíveis mesmo depois de o pré-exame habilitar o cálculo; na base oficial, não
há condições avançadas (ver abaixo).

Na base oficial, a preparação reúne as **Configurações** em caixas seletoras, no lugar do texto
corrido dos parâmetros. Todas as análises mostram as mesmas quatro caixas, nesta ordem: **Categoria**
(a base oficial tem só MEDICINA), **Período**, **Abrangência territorial** e **Indicador**. Em
distribuição, comparações, evolução temporal e relatórios, o Indicador é a escolha entre Quantidade e
Densidade por 1.000 habitantes. Nas demais análises, a caixa mostra, numa opção só (como a
categoria), o indicador que o motor calcula: Densidade por 1.000 habitantes (densidade e recortes e
rankings), Quantidade (quantitativos), Quantidade e densidade por 1.000 habitantes (agregações),
Distância geodésica (km) (análise espacial), Permanência e rotatividade da coorte (%) (rotatividade),
Distância à referência mais próxima (km) (referência mais próxima) e, nos critérios combinados, os
atributos usados nas condições, na ordenação e nas faixas ("Definido nos critérios" enquanto não há
nenhum). Na análise espacial, o Período pede uma competência ("Escolher período"), com a nota "As
distâncias usam as coordenadas da competência escolhida; em algumas competências, a fonte traz
coordenadas diferentes para o mesmo município."; os motivos do pré-exame dessa análise (coordenadas,
competência, referência) aparecem abaixo das caixas com o texto do backend. Na rotatividade, a caixa
Período abre o período inicial e o final da coorte (sem escolha, valem a primeira e a última
competência). Na mesma grade entram o Agrupamento da distribuição, o
Território de referência da análise espacial e, fora da versão governada, o Referencial geodésico
das análises de distância; as referências da referência mais próxima e os critérios do usuário
continuam em quadros próprios logo abaixo. Não há caixa de fonte: a abrangência territorial já diz
se a análise usa o Brasil, os estados ou os municípios. Uma caixa ainda sem escolha fica destacada. Valores longos
aparecem por inteiro, com quebra de linha.

**Só as escolhas da análise retêm o cálculo (desde 21/10/2026).** Na base oficial, o botão "Calcular e mostrar
resultado" fica disponível o tempo todo, menos durante a conferência da análise ("Preparando a análise...") e o
cálculo. Ao clicar, se faltar alguma escolha, a tela diz quais faltam, pelo título das caixas e na ordem delas, em
`missing-choices` (por exemplo, "Falta escolher: Período e Indicador."). Ela também abre a lista do Período ou da
Abrangência territorial quando é essa a primeira que falta, e nada é calculado. Retêm o cálculo apenas a Categoria, o
Período, a Abrangência territorial (escolha pendente: mistura de níveis ou territórios de menos), o Indicador (quando a
análise pede a escolha entre quantidade e densidade) e, quando a análise os usa, o Território de referência e o
Referencial geodésico. Nada sobre a estrutura da base é pedido: não há "Ver outras condições da análise" (associação de
colunas, código IBGE, resoluções e conferências) nem o aviso "Ainda faltam condições específicas para esta análise". Com
as escolhas feitas, o que ainda impedir o cálculo aparece com o texto do pré-exame do backend. Uma falha do pré-exame
aparece na própria preparação, com "Verificar novamente".

A caixa **Período** abre, logo abaixo das configurações, a lista de competências descrita acima.
Numa análise de período único, escolher a competência recolhe a lista. Vários períodos só existem
em quantitativos, evolução temporal (que começa com todas as competências), comparações (desde
19/10/2026; ver adiante) e relatórios, por "Selecionar vários períodos"; "Concluir" recolhe a lista. Não há etapa separada de escolha do
período. A caixa mostra os períodos em ordem cronológica e resumidos por intervalo, com as lacunas
nomeadas (por exemplo, "20 competências, de junho de 2014 a junho de 2024, exceto junho de 2015");
até três competências fora de sequência aparecem pelo nome ("janeiro de 2014 e junho de 2015").
Quando a lista tem outros meses além de junho, o atalho **"Série anual (junho) · N competências"**
(ao lado de "Todos os períodos disponíveis") escolhe só as competências de junho, uma por ano, e o
resumo passa a "série anual de junho: 11 competências, de junho de 2014 a junho de 2024". Na
evolução temporal da base oficial, um texto explica por que a série anual muda a tendência
(janeiro e junho alternam intervalos de 5 e 7 meses, e qualquer queda entre duas vizinhas leva a
"Sem classificação (mudança de direção)"). No resultado da evolução, quando os intervalos não são
constantes e há ao menos quatro competências de junho na janela, o botão "Usar a série anual
(junho)" leva essas competências à caixa Período, sem calcular. O padrão continua sendo todas as
competências (ver `EVOLUCAO_TEMPORAL_E_TENDENCIA.md`).

A caixa **Abrangência territorial** abre uma lista vertical com caixas de marcar nativas (Tab entre
os controles, Espaço marca): **Brasil (total nacional)**;
**Estados** (selo "médicos únicos"), com o aviso de que cada estado conta os médicos diferentes do estado
(fonte estadual: quem atua em mais de um município do estado conta uma vez; quem atua em mais de um estado
conta em cada um, e a soma dos estados não é o total do Brasil), "Todos os estados" e cada estado com a
"população de N municípios" (a seção avisa que cada caixa marca o estado inteiro); e **Municípios**, com "Todos os
municípios" e, desde 21/10/2026, o seletor "Estado dos municípios". O estado escolhido mostra à vista a sua lista, com
"Todos os N municípios de …" e cada município; sem escolha, vale o estado do primeiro município marcado, e "Marcados
em: AM (2) · …" leva a cada estado com municípios marcados. Antes, os municípios ficavam num grupo recolhível dentro de
cada estado, no fim da lista. Os estados e os municípios do estado escolhido rolam por dentro, e os títulos das seções
ficam à vista. Ao lado, "{n}
selecionados", a composição ou o padrão da análise, a escolha pendente e "Limpar seleção". Sem nada
marcado vale o padrão da análise, com o selo "padrão desta análise": o Brasil em quantitativos,
evolução temporal e relatórios; todos os municípios nas demais. A primeira marcação substitui o
padrão. Os municípios marcados continuam valendo ao trocar de análise; o Brasil e os estados só
valem nas análises que os aceitam, e nas demais a seção fica desabilitada com o motivo em uma linha
(por exemplo, "Não se aplica: o ranking ordena vários territórios, e o Brasil é um só."). Estados e
municípios juntos na distribuição, no ranking ou na agregação, ou territórios de menos, deixam a caixa em destaque,
com o motivo do backend e "Ajuste a abrangência territorial para continuar.", e o cálculo bloqueado.
A base é examinada uma vez: trocar de análise não recarrega a base nem troca de fonte. A densidade do
Brasil fica disponível na caixa Indicador. Detalhes em
[abrangência territorial](ABRANGENCIA_TERRITORIAL.md).

Os padrões oficiais vêm do perfil validado no backend, campo a campo: mudar uma coluna tira só
aquele papel do perfil, e a base oficial nunca cai no fluxo das bases importadas. As premissas de
comparabilidade são internas: evolução temporal, comparações, rankings e agregação
não exibem caixas de confirmação, e a origem de cada premissa aparece
em "Método e limitações"
(ver [premissas internas da base oficial](DADOS_BRASIL_VALIDACAO.md#premissas-internas-da-base-oficial)).
Na versão governada, as análises de distância também não pedem o referencial nem o separador
decimal: as configurações mostram "Referencial das distâncias: SIRGAS 2000 (premissa da base oficial)", a legenda do mapa
informa essa origem, e o formato numérico, também premissa interna, não é pedido.

**Bases importadas** seguem a mesma regra, sem confirmações: o parágrafo da preparação diz
"Preenchi os campos reconhecidos com segurança; escolha os demais nos termos destacados". Cada termo
é um seletor; as sugestões do backend aparecem no topo, com "(sugerida)", e o seletor fica vazio até a
escolha (por exemplo, o código territorial, opcional, com "Sem código"). O período tem a opção "A base
tem um único período". Sem objeto reconhecido, aparece "O objeto da análise é [campo]", com o botão
"Usar sugestão" quando o cabeçalho sugere uma categoria. O botão "Executar análise" fica sempre
visível, desabilitado até a análise estar pronta, e os motivos pendentes aparecem logo abaixo. As
condições avançadas ficam em "Ajustar condições específicas ou situações excepcionais". O
separador decimal das coordenadas é verificado nos dados e só vira escolha quando o formato é misto;
o referencial continua um parâmetro. Na conversa, o território citado num pedido é registrado como
"Definido na abrangência territorial", sem pedido de confirmação.

A comparação de dois municípios apresenta um registro para cada objeto A/B, seguido pela relação,
diferença e condição retornadas pelo motor. Conjuntos maiores mantêm um registro por território.
Filtros e ordenação continuam disponíveis em “Filtrar e ordenar a comparação”. O CSV preserva
as colunas e valores originais; a separação é apenas visual.

**Comparação com janela (desde 19/10/2026, decisão D6).** A comparação aceita um período ou uma janela
de períodos ("Qual período (ou janela de períodos) você deseja usar na comparação?"). Sem período
escolhido, ela começa na **série anual de junho** (na base versionada, 11 competências, de junho de 2014 a
junho de 2024), com os valores na última; um período único já escolhido (vindo de outra análise ou da
conversa) é mantido. Com um período só, os valores lado a lado e as relações são os dele, e não há outra escolha.
Com dois ou mais períodos (desde 21/10/2026), a frase **"Valores lado a lado em [competência]"**
(`comparison-values-period`), logo abaixo das configurações, diz em que competência ficam os valores lado a lado e as
relações. Sem outra escolha, vale a última do período, com a indicação "(a última competência do período)". O
seletor da frase (`comparison-values-choice`, rótulo acessível "Competência dos valores lado a lado") oferece só as
competências do período escolhido, e a frase termina com "As demais competências do período mostram a mudança e a
tendência de cada território.". Até 21/10/2026, essa escolha era a caixa "Competência dos valores" na grade, que
aparecia também com um período só e repetia os períodos já escolhidos. Na base importada, continua o seletor na frase
quando há janela. A nota `comparison-window-note`, na lista do Período, explica: "Com um período, os valores lado a
lado e as relações (maior, menor, diferença) são os dele. Com dois ou mais, eles usam uma competência só, indicada
abaixo das configurações (sem outra escolha, a última), e cada território ganha também a mudança entre o primeiro e o
último período e a classe de tendência; sem variação percentual nem razão automáticas.". A interface envia
`comparison_values_period` (a competência única, a escolhida ou a última da janela); sem competência
escolhida, não envia e vale o comportamento anterior. **A conversa não recebe essa opção**: o contexto
enviado ao interpretador continua sem ela, e o agrupamento das competências calculadas a ignora. No
resultado, antes das abas, aparecem os valores lado a lado por nível, a relação e a diferença do par, os
halteres do primeiro ao último período e o selo da tendência de cada território; os cartões da tabela ganham
a quantidade, a população, a mudança e a tendência do território (ver
[Bloco 3](BLOCO3_MAPAS_VISUALIZACOES.md)).

**Perguntas sobre o resultado da comparação.** Quando os dois valores são iguais, o motor emite a relação
`IGUALDADE` e a resposta diz "O valor de A é igual ao de B."; antes, a conversa só reconhecia "IGUAL" e a
relação sumia da resposta. A frase-resumo do cabeçalho usa o mesmo texto da relação e os mesmos
verificadores; ela fica só na interface e não vai ao provedor de IA.
