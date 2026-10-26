# Área de análise da página única

Decisões do responsável pelo produto de 22/10/2026: uma análise integrada, sem duas telas. A página é sempre a análise. Desde
23/10/2026, uma linha de abas reúne a **Seleção de Territórios** (o conjunto analisado, compartilhado por todas as análises) e as
quatro análises com os nomes padronizados: **Análise de Distribuição**, **Análise Espacial**, **Análise de Tendência** e
**Análise de Rotatividade**. As abas aparecem quando os dados estão prontos (24/10/2026). Cada aba abre com a apresentação do
que ela faz (nas análises, desde 24/10/2026, em "Entenda esta análise", recolhido por padrão desde 25/10/2026), mesmo quando a análise não pode ser
executada com os dados; as análises mostram os ajustes delas no mesmo painel. Há um indicador único, funções comuns a todas as análises e,
abaixo, os Detalhes. Desde a segunda rodada de 24/10/2026, **Desfazer** (até 25/10/2026, "Voltar") e **Limpar seleção** ficam
fixos no alto da área, lado a lado, em todas as abas (seção "Desfazer e Limpar seleção"). O desenho é o gráfico de bolhas e, desde 23/10/2026, também o mapa, como segunda vista da mesma análise
(Gráfico | Mapa | Lado a lado). No gráfico, o eixo Y é o indicador; o eixo X só aparece com a análise espacial. Este documento descreve a área de análise. O motor e as rotas
(`/api/painel`, `/api/painel/referencias` e `/api/painel/mapa`) estão em [Painel integrado de bolhas](PAINEL_INTEGRADO.md); a
estrutura da página (cabeçalho, fonte de dados, Histórico e conversa) fica no README e nos documentos da interface e da conversa.

Código: `frontend/src/AreaDeAnalise.tsx` (a área e o estado), `PainelChart.tsx` (bolhas, dica e legendas), `MapaAnalise.tsx`
(o mapa) e `transicaoVistas.ts` (a troca animada entre o gráfico e o mapa), montados pelo contrato de `mapaContrato.ts`,
`PainelTerritorios.tsx` (escolha dos territórios), `PainelSeries.tsx` (visão Série temporal da tendência), `PainelSetas.tsx`
(quadro de setas da tendência, na visão Tendência), `PainelRotatividade.tsx` (barras de
100%), `PainelGavetas.tsx` (painéis das funções), `PainelRuler.tsx` (régua), `PainelDetalhes.tsx` (tabela, não avaliáveis e
método), `painelModel.ts` (modelo puro), `painelApi.ts` (cliente do motor, único lugar com os nomes de campos) e `analise.css`.
A estrutura da página (`App.tsx`) monta a área direto, sem invólucro. No código e nos testes, os identificadores da área
começam por `analise-` (`data-testid="area-de-analise"`, `analise-...`); os do mapa, por `mapa-`.

## Como a página monta a área

```ts
<AreaDeAnalise
  fonte={null | { tipo: "brasil" | "arquivo", apiBase, datasetVersion, sheet, mapping, arquivo, nome, geoVersion?, premissas?, rotulos? }}
  periodos={string[]} categorias={string[]} categoria={string}
  niveis={bloco "niveis" da inspeção (base do Brasil)} municipios={catálogo das unidades}
  pedido={{ id, pedido } | null}        // comando da conversa: cada id novo é aplicado uma vez
  restaurar={EstadoSalvo | null}        // Histórico: reabre sem recalcular
  onContexto={c => ...}                 // a cada mudança do que está na tela
  onSalvar={e => ...}                   // a cada cálculo do motor
  onEscolherFonte={tipo => ...}         // "Usar dados do Brasil" e "Enviar meus dados" (abre a janela de envio), na abertura e no "Trocar"
  trocandoFonte={boolean}               // "Trocar" pedido na barra da fonte: a escolha volta à área, com "Cancelar"
  onCancelarTroca={() => ...}/>
```

- **Fonte:** `null` é a abertura (E0). A troca de fonte (outra versão, outra planilha) recomeça a área. "Nova análise" remonta a
  área (`key`): os mesmos dados, sem territórios escolhidos.
- **Entradas dos dados** (24/10/2026): só duas, "Usar dados do Brasil" e "Enviar meus dados", na área central
  (`analise-abertura`, com `analise-fonte-brasil` e `analise-fonte-arquivo`) e na conversa, com as mesmas ações; não há botões
  de fonte no alto da página. "Enviar meus dados" abre a **janela de envio** (`envio-de-dados`, em `JanelaDeEnvio.tsx`), a mesma
  em todas as entradas (a abertura, a conversa, o "Trocar" da fonte e o "Enviar meus dados" da Rotatividade): o que enviar (CSV,
  XLS ou XLSX, até 30 MB, uma linha por território, categoria e período), "Escolher o arquivo" (`envio-escolher-arquivo`) e o
  **modelo de planilha** (`envio-modelo`), com as colunas descritas e "Baixar o modelo de planilha (XLSX)"
  (`envio-modelo-baixar`); "Cancelar" (`envio-cancelar`) fecha sem mudar nada. O arquivo escolhido segue a preparação de sempre
  (as validações de formato e de tamanho, a aba e o painel Colunas). O botão "Modelo de planilha XLSX" da abertura
  (`analise-fonte-modelo`) e o da conversa saíram: o modelo fica na janela de envio. O "Trocar" da barra da fonte traz as mesmas
  duas entradas de volta à área (`analise-troca-fonte`: "Escolha a nova fonte. A análise atual continua à vista até a nova fonte
  ficar pronta.", com `analise-troca-cancelar`). A troca só vale quando a nova fonte fica pronta: com "Cancelar", na janela ou
  na preparação, ou com um arquivo recusado, a fonte e a análise em uso continuam como estavam.
- **Contexto (`onContexto`):** família, indicador, nível, universo, as unidades à vista (`idsNaTela`), competência, janela,
  referência e o título; desde 23/10/2026, também a vista em exibição (`vista`: `grafico`, `mapa` ou `lado`), a frase-resumo
  do motor que está na tela (`resumo`) e se o mapa pode aparecer (`mapaDisponivel`), com o motivo quando não pode
  (`motivoSemMapa`). Só é chamado quando algo muda.
- **Histórico (`onSalvar` e `restaurar`):** cada cálculo entrega `{titulo, definicao, resposta, quando}`. A `definicao` guarda o
  pedido, a família calculada, a chave do pedido e o estado visual (escala, régua, seleção e, desde 23/10/2026, a vista do
  desenho; o campo da cor contínua do mapa continua no estado, sempre falso, desde que a escolha saiu); `restaurar` com esse
  objeto reabre a análise sem novo pedido ao motor, na vista em que foi guardada. Trocar a vista depois do cálculo atualiza o
  estado guardado da mesma análise. Um estado de antes, sem esses campos, reabre no gráfico.
- **Conversa (`pedido`):** os campos do objeto `painel` da conversa (família, indicador, nível, municípios, competência, janela,
  visão da tendência, referência, função, seleção, ordenação, condições, grupos e, desde 23/10/2026, a vista: `vista: "mapa"`
  para "ver no mapa", `"grafico"` para "volte ao gráfico"). Cada campo é validado; o que não vale vira um aviso
  ("A competência … não existe nesta base"), nunca um erro. "Junte Manaus, Iranduba e Manacapuru" cria o conjunto; "compare
  Manaus e Tefé" pede a comparação; uma família indisponível fica de fora, com o motivo. O mapa é conferido na análise que
  resulta do pedido: "mostre os municípios do Amazonas no mapa" abre o mapa; nos estados, o aviso diz o motivo ("Mapa: Os
  estados não têm um ponto no mapa…"). Numa planilha sem população, um pedido pela densidade fica na quantidade, com o motivo.
  Um pedido feito antes dos dados é aplicado quando a base fica pronta.
- **Nomenclatura territorial:** `fonte.rotulos` (`{unidade: {singular, plural}, grupo: {singular, plural} | null}`) ou os
  `rotulos` da resposta do motor. Na base do Brasil, município e estado; numa planilha, o que a pessoa confirmou (distrito,
  província…). Nenhum texto da área fixa "município" ou "estado": título, subtítulo, lista de territórios, resumo da seleção, dica, tabela,
  Detalhes, exportação e mensagens saem dos rótulos, com concordância simples ("Todas as províncias", "Ver os 12 distritos",
  "Cada bolha é uma comuna"). O gênero é o informado (`genero`) ou, sem ele, deduzido pela terminação.

## Estados da tela

| Estado | O que aparece |
|---|---|
| E0, antes dos dados | Desde 24/10/2026, só a identificação e a escolha dos dados, mais acima e centradas, sem números nem bolhas de exemplo: o título com o nome da plataforma, "Diagnóstico Territorial da Força de Trabalho na Saúde" (`analise-titulo`; até a segunda rodada de 24/10/2026, "… em Saúde"), "Escolha seus dados para começar" (`analise-abertura-chamada`), uma frase ("Use os dados do Brasil, já preparados, ou envie a sua planilha em CSV ou Excel.") e os botões "Usar dados do Brasil" e "Enviar meus dados". Sem as abas e sem Nova sessão, Nova análise e Histórico, que aparecem com os dados prontos. A escolha da análise antes dos dados (a "intenção") saiu. |
| E1, dados carregados sem seleção | Sem seleção automática (23/10/2026), na base do Brasil e na planilha: a aba Seleção de Territórios aberta, com a lista; nada é pedido ao motor até a escolha, e nenhum resultado anterior fica à vista. Nas análises, antes da escolha: "Os dados do Brasil foram carregados e estão prontos para a análise." (ou "A planilha foi carregada…"), "Selecione os territórios que deseja analisar." e "Abrir a Seleção de Territórios". |
| E1, estados | Os estados em bolhas (`nivel: "estados"`), escolhidos na Seleção (o nível Estados: um, vários ou todos) ou pela conversa ("todos os estados"), com a linha de contexto do Brasil e a instrução "Clique num estado para ver os municípios dele". |
| E2, unidades na Distribuição | As bolhas das unidades escolhidas no eixo do indicador. |
| E3, outra família | Análise espacial, Tendência ou Rotatividade. |
| E4, função em uso | Um painel lateral aberto (no celular, sobe da base da tela). |

O estado vai em `data-estado` da área; a vista do desenho em exibição, em `data-desenho` (`grafico`, `mapa` ou `lado`).

## Escolha dos territórios

Pedido do responsável (22/10/2026): a escolha precisa ser visível e didática, sem adivinhar onde clicar e sem depender de
digitar o nome de um município. Desde 23/10/2026, a lista fica na aba **Seleção de Territórios**, a primeira da linha das
análises (`analise-aba-territorios`, com o resumo da seleção em `analise-aba-territorios-resumo`). Desde 24/10/2026, a aba é só
da seleção (`PainelTerritorios.tsx`): encontrar, navegar entre os níveis, marcar e desmarcar, ver o que está marcado e corrigir
ou limpar. O gráfico, o mapa, a frase-resumo e os Detalhes ficam nas análises (na Seleção, `analise-resultados` fica oculto).
A aba começa com uma orientação curta, sempre à vista: "Escolha os territórios que entram nas análises. A seleção vale para
todas elas e pode ser mudada a qualquer momento." As instruções sobre as caixas e os textos técnicos saíram. Cada aba de
análise mostra o resumo da seleção (`analise-selecao-resumo`) com "Alterar a seleção" (`analise-selecao-alterar`), que volta à
Seleção. O território de referência da Análise Espacial e o período da Análise de Tendência continuam dentro de cada análise.

**Duas áreas lado a lado** (segunda rodada de 24/10/2026, `analise-territorios-colunas`): à esquerda, cerca de metade da
largura, a busca no alto e a lista para marcar (`analise-territorios-lista`); à direita, o que já está marcado, em tempo real
(`analise-selecionados`, "Na análise"), presa abaixo dos controles do alto enquanto a lista rola, com rolagem própria. Abaixo de
900 px, as duas áreas ficam uma sobre a outra, e o que está marcado vem antes da lista, compacto (no máximo 40% da altura da
tela, com rolagem própria): a seleção nunca fica escondida depois da lista inteira.

- **Níveis, na base do Brasil** (24/10/2026): três, um em análise por vez (`analise-nivel`, com `analise-nivel-brasil`,
  `analise-nivel-estados` e `analise-nivel-municipios`; RQ-DAD-30: nenhum nível é somado a outro). Cada nível guarda a sua
  escolha: voltar a um nível devolve o que estava marcado nele. A base abre no nível dos municípios, sem nada marcado.
  - **Brasil:** o país inteiro como uma unidade (`analise-territorios-brasil`): o total nacional de profissionais e a
    população do país. Não é a soma dos estados nem a seleção de todos os municípios (seção "Brasil como unidade").
  - **Estados:** a lista dos 27 (`analise-estados`), com caixas: um, vários ou todos, com "Marcar todos os estados (27)" e
    "Desmarcar todos os estados" (`analise-marcar-todos` e `analise-desmarcar-todos`). Com só alguns marcados, o pedido leva a
    lista deles (`estados`).
  - **Municípios:** navegados por estado e cumulativos. Cada estado é uma linha (`analise-grupo`) com a caixa do estado inteiro
    (`analise-grupo-todos`, parcial quando há só alguns marcados, com "3 de 417 marcados" ou "Todos os 417 marcados") e "Ver os
    N municípios ›" (`analise-grupo-ver`), que **só abre a lista** do estado e não muda o que está marcado. Na lista aberta:
    "Voltar aos estados" (`analise-grupo-voltar`; desde a segunda rodada de 24/10/2026, maior e preenchido, como os botões de
    destaque, com a seta à esquerda; ele só fecha a lista e é diferente do Desfazer do alto, que desfaz passos), quantos estão
    marcados, "Marcar todos os municípios da Bahia" e
    "Desmarcar os municípios da Bahia" e as caixas, com atalhos pela letra inicial acima de 120 municípios. Marcar em outro
    estado soma ao que já estava marcado: o defeito de 24/10/2026 (marcar na Bahia e depois em Santa Catarina perdia a Bahia)
    vinha de a abertura da lista trocar a seleção pelo estado aberto, e foi corrigido na causa. No alto da lista dos estados,
    "Marcar todos os municípios do Brasil (5.570)" e "Desmarcar todos os municípios" (no lugar da opção "Todos os municípios do
    Brasil"). Desmarcar um município de um estado inteiro deixa os demais marcados, um a um; marcar o último que faltava
    devolve o estado inteiro.
- **Busca, no alto da área da esquerda** (`analise-busca`): "Buscar município ou estado" (no nível Estados, "Buscar estado"),
  pelo nome ou pelo código. O resultado (`analise-busca-resultado`) traz os estados e os municípios encontrados, com as caixas,
  sem abrir lista nenhuma; a busca não muda a seleção.
- **Na análise** (`analise-selecionados`, a área da direita): o resumo do que está marcado (`analise-selecionados-resumo`:
  "Brasil (total nacional)", "Todos os estados (27)", "Bahia e Santa Catarina", "Amazonas (62 municípios)", "3 municípios de 2
  estados", "PORTO ALEGRE (RS)", "Nenhum município marcado") e o botão da análise em uso ("Ver a Análise de Distribuição",
  `analise-ver-analise`). Abaixo (`analise-selecionados-itens`), o que entra, agrupado por estado (`analise-selecionado`): o
  estado inteiro numa linha ("Amazonas · todos os 62") e, quando são só alguns, cada município como uma etiqueta com o × dele
  (`analise-selecionado-unidade`, "Tirar ABAIRA (BA)"); cada estado com o × que o tira inteiro
  (`analise-selecionado-tirar-grupo`); os conjuntos do Juntar, cada um com o × que o desfaz (`analise-selecionado-conjunto`);
  no nível Estados, as etiquetas dos estados, também com o ×; no Brasil, ele mesmo. A lista fica inteira, sem recolher (o "Ver
  quais (N)" saiu). Uma unidade marcada sem um grupo da lista (numa planilha, sem o valor da coluna-mãe) aparece numa linha à
  parte. Sem nada marcado, "Nenhum município marcado ainda: marque na lista ao lado (abra um estado ou use a busca).". O mesmo
  resumo, em poucas palavras, aparece no título das análises, no resumo de cada aba e ao lado dos controles do alto
  (`analise-controles-territorios`; `resumoDoUniverso`, no lugar da trilha "Brasil › Amazonas", que saiu).
- **O que mudou, em palavras:** o que marca ou desmarca muitos de uma vez (os comandos coletivos, a caixa de um estado inteiro,
  o × que tira os municípios de um estado) diz o que mudou (`analise-selecao-aviso`: "Municípios da Bahia desmarcados. Para
  desfazer, use o botão Desfazer, no alto."). Toda mudança da Seleção, uma a uma ou coletiva, também o × de uma unidade, pode
  ser desfeita pelo Desfazer do alto (seção seguinte). O botão "Desfazer" da Seleção (com o aviso `analise-desfazer-aviso`)
  saiu na segunda rodada de 24/10/2026: o controle do alto faz o mesmo e mais e, desde 25/10/2026, leva o nome e o seletor
  dele (`analise-desfazer`). Os comandos dizem sobre
  qual conjunto agem: os estados, os municípios do Brasil ou os municípios de um estado.
- **No gráfico (E1):** clicar numa bolha de estado (ou Enter na bolha em foco) abre os municípios dele na análise; a dica da
  bolha sob o mouse ou em foco mostra a ação "Ver os N municípios". O Desfazer do alto (seção seguinte) desfaz a navegação, e
  o aviso diz isso ("Mostrando os municípios do Amazonas. Para voltar aos estados, use Desfazer, no alto.").
- **Planilhas:** sem os níveis Brasil e Estados, com os mesmos passos e a nomenclatura da planilha (a busca "Buscar distrito ou
  província"). Com coluna-mãe (o papel `grupo_territorial`), os grupos ficam como os estados ("Ver as N <unidades>", a caixa
  do grupo inteiro), com o grupo de cada unidade vindo do catálogo do pré-exame (`parents`, desde 23/10/2026); sem ela, a lista
  das unidades em ordem alfabética, com as caixas. "Marcar todos os distritos (4)" marca a planilha inteira. Sem a lista das
  unidades (quando o catálogo do pré-exame não veio, por exemplo com nomes que não permitem escolher uma a uma), "Marcar todos"
  continua valendo para a planilha inteira, e o resumo fica "Todos os condados", sem um número. Não há bolhas de grupo nas
  planilhas (`disponibilidade.grupos` do motor). No pedido, `base.municipios.estados` leva os valores do grupo, e `ids`,
  `code:<código>` ou `name:<nome>`.
- **Abertura:** a base do Brasil e a planilha abrem sem territórios marcados (23/10/2026); a área abre a Seleção. Antes, a base
  do Brasil abria nos estados, e a planilha, com todas as unidades marcadas.
- **Sem unidades marcadas,** nada é pedido ao motor, e o gráfico, o mapa e a frase-resumo da seleção anterior saem da tela;
  a área pede a escolha.

### Desfazer e Limpar seleção

Pedido do responsável (24/10/2026, segunda rodada, no lugar do Voltar só das navegações e dos Desfazer da primeira rodada): dois
controles globais, sempre à vista e lado a lado, no alto da área (`analise-controles-globais`, `role="toolbar"`), fixos ao rolar
a página (sem rolar até eles), em todas as abas, com os dados prontos. Ao lado deles, o resumo do que está na análise
(`analise-controles-territorios`).

- **Desfazer** (`analise-desfazer`, a seta curva do desfazer, ↶, o ícone universal do Ctrl+Z): um desfazer sequencial de toda a
  interação na área. Até 25/10/2026, chamava-se "Voltar" (`analise-voltar`), com a seta ←; o nome e a seta pareciam levar ao
  começo da sessão, e o responsável pediu o nome e o símbolo do desfazer (25/10/2026). Cada ação reversível guarda o estado de antes: marcar ou desmarcar territórios (uma a uma, coletivas, o × da lista
  da direita), trocar o nível, abrir a lista de um estado e "Voltar aos estados", abrir um estado pela bolha e o atalho do
  mapa, Limpar seleção, juntar e desfazer um conjunto, trocar de aba (também a ida à Seleção pelo "Alterar a seleção"), mudar
  um ajuste (o indicador, a categoria, a competência, os grupos e as faixas, o período, a visão, o intervalo da série, o
  território de referência), a régua, as condições, a ordenação, a comparação, o filtro da classe, "Mostrar só quem atende",
  os itens marcados no desenho, Limpar filtros, a escala e a vista do desenho, um pedido da conversa e a reabertura do
  Histórico. Cada Desfazer desfaz um passo, na ordem inversa, e devolve a seleção, a aba, a lista aberta, os ajustes, os filtros
  e a vista de antes; o arraste da régua, com passos seguidos em menos de 0,9 s, vira um passo só. A pilha guarda até 80 passos
  (`empilharPasso`). O botão diz o que vai desfazer no `title` e no nome acessível ("Desfazer: abrir a Análise de Tendência",
  `textoDoDesfazer`); os passos de um território só começam pelo verbo, e o nome fica como é ("Desfazer: desmarcar PARINTINS
  (AM)", "Desfazer: tirar MANAUS (AM)", "Desfazer: marcar Amazonas"); sem nada a desfazer, fica desligado, com "Nada para
  desfazer ainda". Depois de desfazer, o aviso diz o que foi desfeito ("Desfeito: limpar seleção.", `textoDoDesfeito`). O
  histórico não é o do navegador e não sai da área: recomeça com outra fonte de dados ou com Nova análise. Os passos desfeitos
  não são refeitos (não há "Refazer").
- **Limpar seleção** (`analise-limpar-selecao`, a vassoura; o nome é exatamente "Limpar seleção"): tira os territórios do
  nível em uso, porque cada nível guarda a sua escolha (decisão 5, 25/10/2026): em Municípios, os municípios e os conjuntos; em
  Estados, os estados. A escolha dos outros níveis, a base carregada e os ajustes das análises continuam. Os desenhos que
  dependem da seleção saem, a comparação sai com os itens, e o aviso diz "Seleção limpa: nenhum território na análise. A base
  de dados continua carregada. Para desfazer, use o botão Desfazer.". Sem nada marcado no nível em uso, fica desligado ("Nenhum território
  selecionado."); no nível Brasil, também, porque o país é a própria unidade ("No nível Brasil, o país inteiro é a unidade em
  análise: não há seleção para limpar."). É o único "limpar a seleção" da área: o botão "Limpar a seleção de municípios" da
  Seleção saiu.
- **Limpar filtros** (`analise-limpar-filtros`, o filtro riscado, na barra das funções das análises): continua tirando a régua,
  as condições, a ordenação, a comparação, o filtro da classe e os itens marcados no desenho, sem mexer nos territórios nem nos
  ajustes; ele só aparece com algum filtro em uso, e o Desfazer devolve os filtros ("Desfazer a limpeza",
  `analise-desfazer-filtros`, saiu).
- **Voltar aos estados** (`analise-grupo-voltar`, na lista aberta de um estado): contextual, maior e preenchido, só fecha a lista.

### Brasil como unidade

Decisões D3 e D4 (24/10/2026, pedido do responsável): no nível Brasil, a análise usa o país inteiro como uma unidade (`nivel:
"brasil"`), com a contagem da fonte nacional e a população pela regra BR-POP-JUNHO-1. O título fica "… no Brasil", e o subtítulo,
"A bolha é o Brasil inteiro, com o total nacional de profissionais. O tamanho mostra a população.". Valem a Distribuição (uma
bolha) e a Tendência (a série nacional, na mesma regra de classes); a linha de contexto do Brasil não aparece, porque o item já
é o total nacional. O que agrupa, ordena, filtra ou compara vários territórios não se aplica (matriz da D3): Grupos e faixas
saem dos ajustes, e as funções, exceto Exportar, ficam desligadas, com o motivo ("Com o Brasil como unidade, há um território
só: esta função vale para vários."); um painel de função aberto antes fecha. A Análise Espacial espera municípios ("A distância é medida entre municípios: o Brasil,
como unidade, não tem um ponto no mapa. Para usar esta análise, escolha municípios na Seleção de Territórios."), e o mapa fica
desligado, com o motivo ("O Brasil, como unidade, não tem um ponto no mapa: cada ponto do mapa é um município."), sem atalho.
Desde 24/10/2026, a Análise de Tendência também vale para os estados (um, vários ou todos), com a série estadual do motor.

## Abas, apresentação e ajustes de cada análise

Desde 23/10/2026, uma linha de abas (`role="tablist"`, "Seleção de territórios e análises"): a Seleção de Territórios e as
quatro análises, nesta ordem e na mesma linha (no celular, roláveis). Desde 24/10/2026, as abas aparecem só com os dados
prontos. A aba escolhida se liga a um painel colado nela (`analise-aba-painel`, `role="tabpanel"`, com `data-aba`), que começa
pela **apresentação** (`analise-apresentacao`): um título e um ou dois parágrafos, em linguagem simples, só sobre o que a área
faz, com os nomes territoriais da fonte (municípios e estados; distritos e províncias…), sem códigos internos. Na Análise de
Tendência, a apresentação lista o que significa cada classe (`analise-apresentacao-classes`, "O que significa cada classe").
Depois da apresentação, nas análises, vêm os ajustes (`analise-ajustes`, com `data-familia`), só o que vale para aquela análise,
e o resumo da seleção.

**"Entenda esta análise"** (24/10/2026): nas quatro análises, a apresentação fica num bloco recolhível (`analise-entenda`, um
`<details>` com o botão `analise-entenda-botao`), recolhido por padrão desde a primeira visita (25/10/2026, pedido do
responsável, para não ocupar espaço; antes, abria na primeira visita de cada aba, menos na Tendência), para os resultados
ficarem no alto; se a pessoa o abre ou fecha, a aba guarda a escolha na sessão. Na Seleção de Territórios, a orientação curta
continua sempre à vista.

**Toda aba abre** (23/10/2026), mesmo a de uma análise que não pode ser executada com os dados: as abas não ficam mais
desabilitadas (`data-disponivel` diz se a análise se executa). Nesse caso, o painel mostra a apresentação e o motivo
(`analise-familia-motivo`, "Indisponível com estes dados: …", com "Enviar meus dados" quando é o caso e "O desenho abaixo
continua com a <análise>"), sem os ajustes, e o desenho fica com a última análise executada; nada é pedido ao motor. Exemplo: a
Análise de Rotatividade com a base do Brasil, que tem contagens e não pessoas identificadas.

| Análise | Ajustes dentro dela |
|---|---|
| Análise de Distribuição | Indicador, Categoria (com mais de uma), Competência, Grupos e faixas |
| Análise Espacial | Indicador, Categoria, Competência, Território de referência (o definido, em palavras, e o botão que abre o painel "Território de referência") |
| Análise de Tendência | Indicador, Categoria, Período (Anual ou Semestral, com as 4 competências usadas; abre no Anual; o ritmo que a base não tem fica desligado, com o motivo) e Visão (Tendência, no quadro de setas, Trajetória e Série temporal; "Primeira", "Última" e "Reproduzir" só na Trajetória). Na Série temporal, o Intervalo da série no lugar do Período |
| Análise de Rotatividade | Períodos inicial e final da coorte e Categoria, sem indicador |
| Estados (E1), na Distribuição e na análise que espera os municípios (Espacial e Rotatividade) | Indicador, Competência, Grupos e faixas (o desenho é a distribuição); na Tendência, os da Tendência |
| Brasil como unidade | Indicador e Competência (sem Grupos e faixas: o Brasil é um só); na Tendência, os da Tendência |

O texto das apresentações tem medida de leitura limitada, entrelinha folgada, justificação com hifenização na tela larga (no
celular, alinhado à esquerda) e a mesma hierarquia em todas as abas.

- **Indicador** (Densidade ou Quantidade): um só para todas as abas. A escolha acompanha a pessoa ao trocar de aba e fica sempre
  à vista; quem escolheu Quantidade na Distribuição encontra Quantidade marcada na Tendência. Numa planilha sem população, o
  botão Densidade fica desligado, com o motivo à vista e no `title` ("Sem população na planilha: só a quantidade."): o motor
  recusa a densidade sem população.
- **Categoria:** quando a fonte tem mais de uma, fica junto do indicador.
- **Competência:** na Distribuição, na Análise espacial e nos estados (a mais recente, dita no título).
- **Escala:** sai dos ajustes, porque muda só o desenho ("como ver"): fica na barra das funções, junto da escolha da vista, e
  aparece só quando se aplica (no gráfico, fora da Rotatividade, do quadro de setas e da visão Série temporal; o mapa não tem
  escala própria). É linear, a
  partir do zero; a logarítmica fica só por escolha da pessoa e só com todos os valores positivos (Parte 13, L1994). A escala
  logarítmica automática de 22/10/2026 saiu.

O que cada análise mostra:

- **Distribuição** (base, sempre ativa): grupos por posição (nenhum, quartis, quintis ou decis; CAP-DIS-02) ou faixas digitadas
  pela pessoa (CAP-DIS-03, limites como "0; 1; 2; 5"). O grupo e a faixa de cada bolha, os cortes e as contagens vêm do motor.
  Até cinco grupos ganham cor; nos decis, só as linhas de corte.
- **Análise espacial:** acrescenta o eixo X, a distância em linha reta (km) até o território de referência. Desde a segunda
  rodada de 24/10/2026, o painel **"Território de referência"** (`analise-referencia`; o título "Referência da distância"
  saiu) é um fluxo só, no lugar da referência por critério com a lista de candidatos ("Usar o primeiro" e a escolha no
  empate), pelo nome ou por um conjunto:
  1. **Relação espacial** (`analise-ref-relacao-mais_proxima` e `analise-ref-relacao-mais_distante`): "Mais próximo" ou "Mais
     distante".
  2. **Delimitação geográfica** (`analise-ref-delimitacao`, "Onde procurar a referência"), só com os níveis que a fonte tem: na
     base do Brasil, "No mesmo estado de cada município", "Estados escolhidos", "Na mesma região de cada município", "Regiões
     escolhidas" (Norte, Nordeste, Sudeste, Sul e Centro-Oeste) e "No Brasil inteiro"; numa planilha com a coluna-mãe, "Na
     mesma província de cada distrito", "Províncias escolhidas" e "Na planilha inteira"; sem ela, só a planilha inteira. Os
     estados, as províncias ou as regiões escolhidos são caixas (`analise-ref-valores`, `analise-ref-valor-opcao`).
  3. **Condição do território de referência:** o atributo (`analise-ref-atributo`: Densidade, Quantidade ou População; numa
     planilha sem população, só a Quantidade), o operador (`analise-ref-operador-maior` e `analise-ref-operador-menor`: "Maior
     que" ou "Menor que") e o valor de corte (`analise-ref-valor`), com a unidade do atributo (profissionais por 1.000
     habitantes, profissionais ou habitantes) e a validação dele: a densidade aceita vírgula decimal ("2,36"); a quantidade e
     a população, só inteiros não negativos ("50.000" vale 50 mil); um valor inválido aparece com a orientação, e o pedido não
     sai.

  Nenhum campo tem valor padrão: até os cinco escolhidos, o painel diz o que falta (`analise-ref-falta`, "Falta escolher: a
  relação espacial, a delimitação…"); com eles, a prévia em palavras (`analise-ref-previa`, "Para cada município, o município
  mais próximo entre os municípios da Região Norte com densidade maior que 2,36 profissionais por 1.000 habitantes.") e
  "Aplicar o território de referência". O motor primeiro filtra os elegíveis (a delimitação e a condição, na competência) e
  depois escolhe, para cada município, o mais próximo ou o mais distante deles pelas distâncias geodésicas, **nunca ele
  mesmo**, com os empates; com vários municípios, cada um tem a sua referência (a dica e a tabela dizem qual: "Território de
  referência (o mais distante)"). Sem coordenada válida, sem elegível ou com um elegível sem coordenada, a distância fica não
  avaliável, com o motivo do motor ("Sem território de referência: nenhum outro município da Região Nordeste atende à
  condição …"), nunca zero. Quando nenhum município em análise fica com referência, um aviso acima do desenho
  (`analise-ref-sem-resultado`) diz o que aconteceu: sem ninguém da base na condição, "Nenhum município da base atende à
  condição população > 1000000000 habitantes: não há território de referência. Mude o atributo, o operador ou o valor de
  corte."; senão, as causas possíveis (quem atende fora da delimitação de cada um, só o próprio município na condição ou a
  coordenada que falta), com o motivo de cada um em Não avaliáveis; "Mudar o território de referência"
  (`analise-ref-sem-resultado-mudar`) reabre o painel. Trocar a seleção mantém o território de referência, e o painel reabre com a definição em uso
  ("Mudar"), para ajustar sem recomeçar; "Remover a referência" volta ao eixo único. Um conjunto (Juntar) não tem distância
  com o território de referência (cada membro tem a sua). Um pedido da conversa por critério ("use como referência o município
  de maior densidade") abre o painel com o atributo citado e, desde 25/10/2026 (decisão 4), o operador do "maior" ou "menor"
  ("Maior que" ou "Menor que"), com o aviso `analise-ref-da-conversa`; a relação, a delimitação e o valor de corte ficam com a
  pessoa, sem valor sugerido, e nada é escolhido pela posição na ordem (CAP-REF-01 pede uma condição, CAP-SUB-01); uma
  referência pelo nome, vinda da conversa, continua valendo (a distância até ela). Faixas de distância opcionais
  (CAP-ESP-03). **Territórios base** (25/10/2026, pedido do responsável, no início do painel; cumulativos desde a terceira
  rodada do mesmo dia): "Todos os selecionados" (`analise-ref-base-todos`, o padrão, que vale também para quem entrar depois)
  ou alguns, marcados um a um na lista das unidades em análise (`analise-ref-base`, caixas `analise-ref-base-opcao`; com a
  referência pelo nome, sem os membros dela; com algumas marcadas, "Todos" fica indeterminado, e marcar todas volta a
  "Todos"), no painel, não pelo clique no gráfico, que continua só marcando. Com o território de referência aplicado, cada território base aparece ligado ao seu: quando a
  referência não é desenhada no gráfico (por elegibilidade, a referência costuma ficar fora da seleção), entra uma bolha de
  contexto (`analise-referencia-da-base`, uma por referência, com `data-bases`), círculo claro com a mira, no início do eixo
  (0 km), na altura do indicador dela e com o tamanho pela população dela, os valores do motor (`referencia.membros`), com o
  nome "· referência" e a dica própria (população, profissionais, densidade e a distância até cada base ligada a ela, até 4);
  uma linha tracejada (`analise-ligacao-base`, com `data-base` e `data-referencia`) liga cada base a ela, e a distância entre
  as duas no eixo horizontal é a própria distância; no empate, uma linha até cada referência empatada (CAP-ESP-02). As bases
  escolhidas uma a uma ganham o anel e o nome "· território base"; com todos os selecionados, as bases ficam com o nome de
  sempre. Até 12 bases têm o nome à vista (e até 12 referências de contexto); com mais, a dica. O gráfico desenha no máximo
  30 ligações, das bases à vista (dentro da régua e dos filtros), as marcadas primeiro. Com a referência pelo nome, o membro
  já está no gráfico com a mira, e a linha vai até ele. A bolha de contexto não conta na frase-resumo, nos grupos, na régua,
  nos filtros, na tabela nem no CSV, e a mesma unidade em análise continua com a sua própria bolha. Acima do desenho,
  `analise-par-base` diz, com uma base, "Território base: BOA VISTA (RR) · Território de referência (o mais próximo):
  PRESIDENTE FIGUEIREDO (AM), a 543,82 km em linha reta." (sem referência, o motivo do motor) e, com mais, "Territórios base:
  4 (todos os selecionados) · cada um ligado ao seu território de referência (o mais próximo) por linha tracejada: …", com os
  quatro primeiros pares (base → referência, distância) e quantos faltam; quando o gráfico liga menos do que os pares com
  referência, diz quantas ligações desenha; sem bases, "Nenhum território base: …"; com várias bases e nenhuma com
  referência, a linha sai (o aviso `analise-ref-sem-resultado` diz o motivo). O botão `analise-par-base-mudar` reabre o
  painel. O resumo do Território de referência cita as bases só quando escolhidas uma a uma ("· território base: …",
  "· territórios base: … e …", "· N territórios base" ou "· nenhum território base"). No mapa, as ligações das bases vêm
  primeiro, e a referência fica no quadro, com o nome. É só estado visual (RQ-REP-06): o pedido ao motor é o mesmo, nada é
  calculado entre os dois (CAP-REF-01), e cada escolha é um passo do Desfazer ("Incluir BOA VISTA (RR) nos territórios base",
  "Tirar … dos territórios base", "Todos os selecionados como territórios base", "Nenhum território base") e fica no estado
  salvo (um território base guardado antes de serem cumulativos vira a lista com ele). A nota TPL-11 aparece sempre junto. Nos estados, a
  família espera a escolha de municípios (os estados não têm coordenadas). A disponibilidade vem do motor
  (`disponibilidade.espacial`): numa planilha sem coordenadas ou sem um referencial aceito (SIRGAS 2000 ou WGS 84), a aba abre
  com a apresentação e o motivo do motor, sem os ajustes; quando o motor pede a escolha do referencial, a tela mostra as opções
  que ele mandar.
- **Tendência:** desde 24/10/2026, o campo **Período** (`analise-periodo-anual` e `analise-periodo-semestral`) escolhe o ritmo, e a
  janela são os **últimos 4 períodos** dele, contados da competência mais recente: o mínimo de DA-15 (4 períodos, 3 avanços).
  Desde a segunda rodada de 24/10/2026 (pedido do responsável, no lugar de "sem ritmo padrão"), a análise **abre no Anual**
  (`janelaPadrao`), à vista no campo, e a pessoa pode trocar pelo Semestral; sem o anual na base, abre no único ritmo que ela
  tem (RQ-GOV-14: um só valor aplicável resolve o parâmetro); sem nenhum, nada de tendência é pedido, e o aviso diz "Escolha o
  período da tendência, anual ou semestral: a análise usa os últimos 4 períodos.". Ao abrir a aba, a vista do desenho é o
  **Gráfico** (o mapa continua como alternativa, na barra do desenho). No anual, a cada passo vale a competência mais perto de
  12 meses antes; no semestral, de 6 meses antes, com folga de 2 meses (de janeiro a junho são 5 meses; de junho a janeiro, 7).
  Na base do Brasil: anual = 06/2021, 06/2022, 06/2023 e 06/2024; semestral = 01/2023, 06/2023, 01/2024 e 06/2024. Sem 4 períodos
  assim (por exemplo, uma planilha só com junhos, no semestral, ou com um ano faltando, no anual), o ritmo fica desligado, com o
  motivo à vista. O texto do campo (`analise-periodo-texto`) lista as 4 competências usadas. Os atalhos "Últimos 4 junhos",
  "Série anual de junho" e "Todas as competências" e o painel que marcava as competências uma a uma saíram. Não há janela
  longa nem outra janela: a conversa pede o ritmo ([conversa no gráfico](CONVERSACAO_INCREMENTO_FN.md)), e uma janela que chegue
  à tela por ela (ou por outra rota) vale pelo ritmo dos intervalos dela (cerca de 12 meses entre as competências, o anual;
  cerca de 6, o semestral, com a mesma folga) e passa a ser os últimos 4 períodos desse ritmo, com o aviso "A tendência usa os
  últimos 4 períodos …"; sem ritmo, a janela não muda e o aviso pede a escolha (`janelaPeloRitmo`). A janela só vale para a
  tendência: a rotatividade usa os períodos da coorte, e as outras análises, uma competência. O método não muda (CAP-TEN-01).
  **Layout** (segunda rodada de 24/10/2026): os controles (os ajustes da aba) em cima; logo abaixo, a área principal, com as
  ferramentas (régua, condições, ordenação, comparação) e o desenho em destaque; à direita, o painel **"Como ler"**
  (`analise-tendencia-lateral`, `analise-explicacao`), com o subtítulo e a frase-resumo do motor, as contagens por classe, a
  legenda e, no quadro de setas, as velocidades da linha escolhida; o painel de uma função aberta fica por cima dele. Entre os
  dois, a **divisória** (`analise-divisoria`, `role="separator"`) muda a largura do painel: arrastando com o mouse ou o dedo,
  ou com as setas do teclado com o foco nela (Shift para passos maiores; Home e End vão aos limites), entre 240 px e a metade
  da área (no máximo 620 px; 340 px de início). Abaixo de 1.024 px, sem a divisória, o painel vai para baixo do desenho.
  **"Entenda esta análise"** começa recolhido desde a primeira visita, como nas outras análises, para o desenho ficar no alto.
  As visões, nesta ordem (`analise-visao-classes`, `analise-visao-mudanca` e `analise-visao-series`; os nomes de antes, Classes,
  Mudança e Séries, saíram); trocar de visão não refaz a seleção nem os ajustes:
  - **Trajetória** (no lugar da Mudança): entre a primeira e a última competência da janela (CAP-TMP-01), o cometa e a cor
    divergente contínua: azul é aumento, laranja é redução, cinza é sem mudança (V-05; nunca "crescimento"). Desde a segunda
    rodada de 24/10/2026, os períodos do meio da janela aparecem como pontos pequenos no caminho do rastro
    (`analise-trajeto-ponto`), com os valores observados do motor (sem imputar o período sem valor; sem a variação do motor,
    não há caminho, RQ-REP-15), e a dica lista o valor de cada período do meio, com ▲, ▼ ou ► desde o anterior. "Primeira" e
    "Última" alternam as posições; "Reproduzir" desliza as bolhas da primeira à última (com movimento reduzido ou no modo leve,
    o botão vira "Ir para a última", sem animação).
  - **Tendência, no quadro de setas** (24/10/2026, no lugar das bolhas; `PainelSetas.tsx`, `analise-setas`): como um painel de
    cotações, uma linha por unidade (`analise-seta-linha`), com o nome, o desenho dos períodos (um ponto por observação do
    motor e uma seta por avanço, `analise-seta`, com o sinal da velocidade do motor: para cima é alta, em azul; para baixo, queda,
    em laranja; para o lado, pausa, em cinza), o último valor e a variação entre o primeiro e o último período (CAP-TMP-01, do
    motor, com ▲ ou ▼) e a classe do motor, com o ícone da família, na coluna **"Tendência"** (desde a segunda rodada de
    24/10/2026, no lugar de "Classe (do motor)"; nenhum texto da interface fala em "motor"). A tela só posiciona e ordena: a classe e o sinal de cada seta
    são do motor (RQ-REP-02). Cada linha tem a própria escala vertical (o desenho mostra o caminho; os valores ficam ao lado, na
    dica e na tabela), com amplitude mínima de 5% do maior valor, para uma variação ínfima não parecer um salto. As linhas vêm
    agrupadas pela classe, na ordem da SPEC (os não avaliáveis no fim), e, dentro dela, pela variação, da maior para a menor; com
    a Ordenação em uso, pela posição do motor; com as Condições, a situação aparece ao lado do nome. São 50 linhas por página
    (`analise-setas-paginas`). A dica (`analise-seta-dica`), no mouse e no foco, lista cada período com o valor e o avanço até
    ele, a variação e o que a classe quer dizer; Escape fecha. Clicar na linha (ou Enter) escolhe a unidade, para Comparar e
    para as velocidades dela no painel "Como ler" (barras das velocidades do motor; antes, na visão Séries). No painel, a
    contagem por classe do motor, que também filtra (cada contagem traz no `title` o que a classe quer dizer), a legenda das
    setas (`analise-setas-legenda`) e a das famílias com as contagens. O eixo mostra os 4
    períodos. No lado a lado, a linha sob o mouse destaca o ponto no mapa, e o contrário também. A escala (linear ou logarítmica) não se
    aplica ao quadro.
  - **Classes explicadas** (23/10/2026; linguagem revista em 24/10/2026, para quem não é da estatística): a apresentação da aba
    diz o que acontece de um período para o seguinte (o indicador sobe, alta; cai, queda; ou fica igual, pausa) e, para cada
    classe de DA-15 (crescimento, aceleração e desaceleração do crescimento, declínio, aceleração e desaceleração de declínio,
    sem classificação e não avaliável), o que aconteceu com o indicador nos 4 períodos, com um exemplo curto ("Aceleração do
    crescimento: o indicador subiu em todos os períodos, e cada alta foi do mesmo tamanho ou maior que a anterior, com pelo
    menos uma maior: o crescimento ganhou ritmo. Exemplo: 10, 11, 13 e 16 (altas de 1, 2 e 3)."). Os exemplos seguem a regra
    do motor (conferidos nos testes com a mesma conta de `classify_speeds`). O texto só descreve a regra: não cria classe nem
    critério. A nota diz que, com períodos de distâncias diferentes, o tamanho de cada alta ou queda é comparado por mês, e
    termina com "A referência do método fica em Detalhes, na aba Método e procedência.", onde está a âncora do método
    (CAP-TEN-01, rótulos de DA-15); os códigos saíram da apresentação. A dica e os Não avaliáveis dizem o motivo de cada unidade sem classe em palavras, sem o código ("Sem classificação:
    entre os períodos, houve alta e queda (mudança de direção)."). Abaixo das contagens, uma nota
    (`analise-nota-sem-classificacao`) conta as unidades sem classificação por motivo, com os números do motor
    (`sem_classificacao_por_motivo`), e, quando nenhuma unidade recebeu classe, explica a regra: a classificação exige a mesma
    direção em todos os avanços, e uma única mudança de direção basta para a série ficar sem classificação; isso é o resultado
    do método, não falta de dados. O diagnóstico de 23/10/2026 (com a base
    versionada: 62 de 62 municípios do Amazonas sem classificação nas 22 competências, todos por mudança de direção; desde
    24/10/2026, a tela não pede essa janela) está em [Painel integrado de bolhas](PAINEL_INTEGRADO.md).
  - **Série temporal** (segunda rodada de 24/10/2026, no lugar da visão Séries, que mostrava só os 4 períodos da janela): a
    série histórica completa do indicador de cada unidade escolhida, lida dos dados a cada pedido (do primeiro ao último período
    que a base tem; na base do Brasil, 01/2014 a 06/2024), sem classificação e sem método novo: o valor observado em cada
    competência, pela mesma preparação da tendência (`serie` no pedido; [Painel integrado de bolhas](PAINEL_INTEGRADO.md)). O
    **Intervalo da série** (`analise-serie-intervalo`) fica no lugar do Período: "De" e "Até" (`analise-serie-inicio` e
    `analise-serie-fim`), com "Toda a série" (`analise-serie-toda`) para voltar à extensão inteira; o texto
    (`analise-serie-texto`) diz "Toda a série da base: 01/2014 a 06/2024 (22 competências)." ou "Intervalo escolhido: …".
    Linhas por competência (no tempo real entre elas), na cor única do gráfico, até 12 unidades: as marcadas (na tabela dos
    Detalhes ou, na visão Tendência, nas linhas do quadro de setas) ou, sem marcação, todas, quando são até 12 (com mais, a
    área pede a escolha, `analise-series-vazio`), com pequenos múltiplos na mesma escala acima de 4. Um ponto por valor observado; competência
    sem valor fica sem ponto, e a lacuna não é ligada; não há linha ajustada. Agregações diferentes ficam distintas: um conjunto
    com membros diferentes no intervalo fica só com os pontos, sem linha (`analise-serie-nao-comparavel`, com o motivo do
    motor, RQ-REP-15); estados e o Brasil, cada um com a série dele. A legenda (`analise-serie-legenda`) diz o que é cada
    marca. O CSV traz uma coluna por competência, e o Método, o intervalo (`analise-metodo-serie`).
  - Sem o período (nenhum ritmo na base), a Tendência e a Trajetória não são calculadas (o aviso pede a escolha); a Série
    temporal não depende dele. Com o período, a janela tem sempre os 4 períodos, e a unidade com menos de 4 observações
    válidas neles fica não avaliável, com o motivo do motor (série insuficiente).
- **Rotatividade:** só com dados enviados que tenham o identificador individual (CAP-ROT-01). Com a base do Brasil, a aba abre
  com a apresentação e o motivo ("A base do Brasil tem contagens, não pessoas: a rotatividade exige dados enviados com o
  identificador individual.") e "Enviar meus dados"; o motivo do motor (`disponibilidade`) vale quando vem. O desenho são barras
  de 100%: permanência e saída da coorte inicial, com as contagens e os percentuais do motor; "da coorte inicial" vai em todo
  rótulo. A pessoa escolhe os períodos inicial e final.

## Vista do desenho: gráfico, mapa e lado a lado

A análise tem duas vistas do mesmo resultado: o gráfico de bolhas e o mapa. A escolha fica na barra das funções, do lado direito,
colada no desenho e sempre à vista, inclusive no celular (`analise-desenho`, botões `analise-desenho-grafico`,
`analise-desenho-mapa` e `analise-desenho-lado`, com `aria-pressed`). Trocar de vista é estado visual: nada é pedido de novo ao
motor (RQ-REP-06), e seleção, régua, condições, comparação, conjuntos, dica, tabela e título são os mesmos nas duas vistas.
O desenho do mapa (pontos, cores, legendas, navegação e o que ele não mostra) está em [Mapa da página única](MAPA_DA_PAGINA_UNICA.md).

- **Vista inicial:** o gráfico. A escolha vale para a sessão da análise: não se perde ao trocar de aba, de território ou de
  competência, entra no Histórico e volta com ele. Sem o mapa disponível, aparece o gráfico, e a escolha continua guardada.
- **Lado a lado:** só com a janela de 1.600 px ou mais; gráfico e mapa ficam cada um com a metade, e o painel das funções fica
  por cima, como entre 1.024 e 1.359 px. Passar o mouse num desenho destaca o mesmo item no outro. Ao estreitar a janela, a
  escolha volta ao mapa.
- **Mapa indisponível,** com o botão desligado (`aria-disabled`, o motivo no `title`) e, ao acioná-lo, o motivo à vista
  (`analise-desenho-motivo`), como o das famílias:
  - **nos estados:** "Os estados não têm um ponto no mapa: cada ponto do mapa é um município.", com o atalho "Ver os municípios
    no mapa" (`analise-desenho-atalho`), que marca todos os municípios e abre o mapa. Os ladrilhos dos estados não foram
    aprovados: nada de mapa nesse nível;
  - **na planilha sem latitude e longitude** no mapeamento (também na rotatividade): o motivo, e a tabela continua;
  - **na visão Série temporal** da tendência, que é só do gráfico ("Na visão Série temporal, cada município é uma linha no
    tempo: o mapa fica com Tendência e Trajetória.").
- **Convite:** "Ver onde ficam no mapa" (`analise-convite-mapa`) aparece com as Condições aplicadas e na Análise espacial, com o
  mapa disponível e a vista no gráfico.
- **Troca animada:** entre o gráfico e o mapa, as bolhas deslizam até o lugar de cada ponto (cerca de 0,7 s). Com movimento
  reduzido, com mais de 400 itens (modo leve) ou no lado a lado, a troca é direta.
- **Pontos do mapa:** vêm do motor (`POST /api/painel/mapa`, o mesmo formulário de `/api/painel`, com a competência e a
  categoria do que está desenhado e, nas planilhas, as premissas e os rótulos): as coordenadas autorizadas de cada unidade e as
  que não têm coordenada válida, com o motivo. A tela pede quando o mapa aparece e, em segundo plano, quando o gráfico mostra
  unidades com o mapa disponível; guarda as últimas seis respostas por fonte e competência. Uma pendência do motor (por exemplo,
  o referencial de uma planilha) aparece na área do mapa, com as opções que ele mandar, como as pendências do gráfico.
- **O que a área entrega ao mapa:** todas as unidades em análise (sem os estados; os conjuntos dão o anel aos membros), também,
  desde 25/10/2026, as que o gráfico deixa de fora por falta do valor que as posiciona (`itensParaOMapa`): sem distância até o
  território de referência, sem o valor do indicador ou sem a coorte, cada uma no lugar dela, com a pintura da camada (na análise
  espacial, o quintil do indicador) ou, sem valor nela, vazada, e com o motivo na dica. Antes, o mapa tinha os mesmos itens do
  gráfico, e quem ficava sem distância (por exemplo, BOA VISTA (RR), com o território de referência no mesmo estado e densidade
  acima da taxa do Brasil) sumia também do mapa, embora tivesse coordenada. O que fica fora da régua e dos filtros aparece
  esmaecido, não escondido (decisão de 23/10/2026; `dentroDosFiltros`, os mesmos filtros do gráfico); sem o valor do indicador,
  com a régua em uso, também esmaece; a pintura do gráfico quando há uma camada de cor (grupos, faixas, condições,
  ordem, classes ou variação); na Rotatividade, a permanência da coorte inicial em cor contínua (0 a 100%); sem camada de cor
  da análise (a distribuição sem grupos nem faixas e a análise espacial, sem condições nem ordenação), os **5 grupos iguais
  (quintis)** do indicador, sem pergunta (23/10/2026): o pedido ao motor leva `grupos_mapa: {tipo: "quintis"}` junto com a
  análise, e o mapa pinta cada ponto pelo `grupo_mapa` do motor, com a legenda dos quintis (rótulos e contagens do motor). O
  gráfico, a frase-resumo, a tabela e o CSV não mudam com eles; sem os grupos na resposta (uma análise guardada antes, ou menos
  de duas unidades com valor), a cor única do gráfico (a unidade sem o valor do indicador, vazada). O tamanho pela população (densidade), pela quantidade ou pela coorte
  inicial; o valor do Brasil só como marca de contexto; a mesma dica do gráfico; a referência e as ligações ilustrativas, até
  30: desde 25/10/2026, as dos territórios base (escolhidos um a um, primeiro; com todos os selecionados, depois dos marcados)
  e as dos selecionados, até o membro da referência mais próximo; o enquadramento
  inicial cobre também as referências desenhadas, e a que fica fora do resultado ganha o nome quando uma ligação chega até
  ela. A pergunta "Como pintar o mapa?" (quintis, faixas ou cor
  contínua) saiu em 23/10/2026.
- **Não avaliáveis:** com o mapa à vista, as unidades sem coordenada válida ficam fora do mapa (no gráfico, continuam) e entram
  em Não avaliáveis, no aspecto "Sem coordenada válida para o mapa", com o motivo do motor.
- **Fora do gráfico** (25/10/2026): com o gráfico à vista, as unidades (e os conjuntos) que ele não pode desenhar, por falta do
  valor que as posiciona, ficam ditas acima do desenho, pelo nome (`analise-fora-do-grafico`, `textoForaDoDesenho`): "Fora do
  gráfico, sem distância até a referência: BOA VISTA (RR). O motivo está em Não avaliáveis, nos Detalhes; no mapa, o município
  aparece no lugar dele." Os motivos são três: sem valor do indicador na competência, sem distância até a referência e sem coorte
  inicial avaliável; até cinco nomes por motivo, com "e mais N". Não aparece quando nenhum território ficou com referência (o
  aviso `analise-ref-sem-resultado` diz o que aconteceu), na Série temporal nem com só o mapa à vista.
- **Depois da primeira vez,** o mapa continua montado (oculto) enquanto houver mapa: volta como foi deixado, com o zoom.

## Eixos, marcas e cores

- **Eixo único (Distribuição, Tendência na Trajetória e estados):** Y é o indicador. Na visão Tendência, o quadro de
  setas (acima) substitui as bolhas, com a escala própria de cada linha. As bolhas se espalham na horizontal só como arranjo, para
  não se sobreporem, e a nota diz "a posição horizontal é só arranjo". Arranjo exato até 400 bolhas (o gráfico cresce na altura
  se precisar); acima disso, ou se não couber, o arranjo leve, numa faixa limitada da largura, com bolhas semitransparentes.
- **Análise espacial:** X = distância até a referência (km), Y = indicador. Sem reta de tendência nem correlação.
- **Tamanho:** população, com área proporcional (raio pela raiz quadrada: o raio máximo, de 12 a 34 px conforme a largura, vai
  para a maior população do resultado) e diâmetro mínimo visível (raio de 4 px); legenda com três populações redondas (1, 2 ou
  5 × 10ⁿ), todas na proporção exata desde 25/10/2026 (`valoresDaLegendaDeTamanho`): a referência que ficaria abaixo do mínimo
  visível, e por isso seria desenhada maior do que a área dela, dá lugar ao menor número redondo que já alcança o mínimo (em
  Roraima, com BOA VISTA, 200 mil, 50 mil e 10 mil habitantes, no lugar de 5 mil). A conferência de 25/10/2026, com os 15
  municípios de Roraima, achou o raio de cada bolha igual ao da área proporcional à população, com duas casas.
- **Linhas de referência,** finas e sólidas: o contexto do Brasil na densidade ("Brasil · 2,36", que não classifica nada), os
  cortes dos grupos ou os limites das faixas, os limites da régua e as faixas de distância.
- **Cores,** uma camada de cada vez (condições, depois ordenação, depois a da família), conferidas com o validador da skill de
  visualização: série única em azul-petróleo `#008b9e`; famílias da tendência `#2a78d6`, `#eb6834` e `#1baf7a` (conferidas em
  todos os pares); grupos e faixas na rampa ordinal azul (de 2 a 5 tons, `--ordinal`); mudança no divergente azul e laranja com
  o zero cinza. Texto sempre em tinta, nunca na cor da série. O verde-água fica abaixo de 3:1 na superfície clara: a legenda, a
  contagem e a tabela dão o valor por outro caminho. Esses são os valores do modo claro; no escuro, os mesmos matizes em passos
  escolhidos para a superfície escura (seção "Modo escuro").
- **Símbolos:** anel escuro no conjunto ("soma das contagens dos componentes, com possível dupla contagem"), mira na referência,
  bolha vazada tracejada quando a camada de cor não tem valor (o motivo vai para Não avaliáveis).
- **Rótulos diretos seletivos:** siglas dos estados, itens destacados, conjuntos, referência, os N primeiros da ordenação (até 12)
  e a bolha sob o mouse ou em foco.
- **Estados e municípios** nunca no mesmo eixo nem somados; na visão dos estados, Juntar fica desligado.
- **Modo leve:** acima de 400 bolhas, uma camada de círculos simples que não muda ao passar o mouse; só as bolhas em destaque
  ganham o desenho completo. A régua só esconde; as posições não mudam. Sem animação. A tabela mostra 100 linhas por vez.

## Funções

Uma barra comum a todas as famílias; cada função abre um painel estreito ao lado do desenho (por cima da parte direita do desenho
entre 1.024 e 1.359 px e no lado a lado; na base da tela abaixo de 1.024 px). No celular, as funções ficam no botão
"Ferramentas"; a escala e a escolha da vista, na mesma linha, ficam sempre à vista.

| Função | O que faz | Pedido ao motor |
|---|---|---|
| Régua | Mostra só o que fica entre dois valores do indicador; só esconde (RQ-REP-06) | Nenhum |
| Condições | Separa quem atende a todas as condições, quem não atende e quem não tem dado (CAP-SUB-01, combinação "e"), com as contagens do motor; "Mostrar só quem atende" é filtro visual | `condicoes` |
| Ordenar | Ordem e posições do motor, empates na mesma posição, os N primeiros (CAP-SUB-02 e CAP-SUB-03) | `ordenar` |
| Comparar | 2 ou 3 itens lado a lado, com maior, menor e diferença do motor (CAP-CMP-01) | `comparar` |
| Juntar | As unidades escolhidas viram uma bolha (CAP-AGR-01), com a soma das contagens dos componentes e possível dupla contagem (RQ-REP-14) | `conjuntos` |
| Exportar | CSV com todos os itens do resultado, em precisão integral, com a avaliabilidade e o motivo (não muda com a vista); Imprimir / PDF, com a vista em exibição (no lado a lado, as duas, uma abaixo da outra) e a frase-resumo; método e parâmetros em texto, com a frase-resumo que está na tela | Nenhum |

A seleção (clique ou Enter nas bolhas, ou a caixa na tabela) destaca os itens marcados com o anel escuro e o nome; desde
25/10/2026, não esmaece os demais, que ficam com a cor inteira, como no mapa (antes, ficavam a 22% de opacidade, e, no modo
leve, a camada inteira a 30%; `opacidadeDaBolha`). Só a pintura apagada (não atende, fora dos primeiros) continua mais clara.

**Destaque da análise** (26/10/2026, pedido do responsável). Com uma comparação em exibição (2 ou 3 itens no gráfico, pelo
painel Comparar ou pela conversa, como "compare o de maior e o de menor densidade"), só os comparados ficam inteiros no
gráfico de bolhas; as demais bolhas da seleção esmaecem a 25% de opacidade (no modo leve, a camada inteira a 30%, com os
comparados redesenhados inteiros por cima). Na Análise Espacial com territórios base escolhidos um a um, sem comparação, ficam
inteiras as bases e as referências delas que o gráfico desenha. A bolha sob o mouse ou o foco e a do território de
referência continuam inteiras enquanto ativas. Marcar, sozinho, continua sem esmaecer; o mapa não muda. Só estado visual
(`destaqueDaAnalise` e `opacidadeComDestaque`, em `painelModel.ts`; `data-destaque` em cada bolha): nada vai ao motor.
Comparar e Juntar agem sobre a seleção. "Limpar filtros", com a vassoura, tira de uma vez a régua, as condições, a ordenação, a
comparação, o filtro da classe e os itens marcados, e o Desfazer do alto a desfaz (seção "Desfazer e Limpar seleção"). Uma comparação só continua enquanto os itens dela estão na
análise: ao trocar o nível ou tirar um item comparado da seleção, ela sai do pedido (com ela, o motor recusaria o pedido com
"Itens da comparação fora do gráfico"). Com o Brasil como unidade, só Exportar vale.

Desde a segunda rodada de 24/10/2026, os painéis **Comparar** e **Juntar** começam por uma orientação objetiva
(`analise-comparar-orientacao`, "Escolha dois ou três itens: clique nas bolhas do gráfico (ou nas linhas do quadro de setas) ou
marque a caixa na tabela dos Detalhes. Depois, use Comparar: o resultado diz qual é o maior, o menor e a diferença, e, no
gráfico de bolhas, os demais esmaecem para destacar os comparados." — até 26/10/2026, "…; os demais esmaecem. Depois, …",
que ainda descrevia o esmaecimento ao marcar, retirado em 25/10/2026; `analise-juntar-orientacao`) e mostram os itens escolhidos como etiquetas, cada uma com
o × (`analise-comparar-item`, `analise-juntar-item`), com o que falta ("Falta um item para comparar."). Os cartões grandes com os
valores de cada item saíram (os valores estão no gráfico, na dica e na tabela); o botão, o título do painel, o nome do conjunto
e o resultado da comparação continuam.

## Título e Detalhes

- **Título dinâmico:** "Densidade de médicos nos municípios do Amazonas · junho de 2024"; "Densidade de médicos nos estados ·
  junho de 2024"; "Densidade de médicos e distância até MANAUS (AM) · Amazonas · junho de 2024"; "Tendência da densidade de
  médicos · Amazonas · junho de 2021 a junho de 2024". "Médicos" sai da categoria MEDICINA; com outra, "profissionais de
  <categoria>". Subtítulo: "Cada bolha é um município. O tamanho mostra a população." Com uma ou duas unidades marcadas, o
  título usa os nomes delas ("… em PORTO ALEGRE (RS) · …"); no nível Brasil, "… no Brasil · …". Na visão Tendência,
  o subtítulo é "Cada linha é um município: as setas mostram a alta, a queda ou a pausa de um período para o seguinte."; na
  Trajetória, "Trajetória da densidade de médicos · Amazonas · junho de 2021 a junho de 2024", com "Cada bolha é um município. O
  tamanho mostra a população. O rastro sai do valor no primeiro período; os pontos pequenos são os períodos do meio."; na Série
  temporal, "Série temporal da densidade de médicos · Amazonas · janeiro de 2014 a junho de 2024", com "Cada linha é um
  município, com o valor observado em cada competência do intervalo."; com o território de referência, "Densidade de médicos e
  distância até o território de referência · Amazonas · junho de 2024". Na Análise de Tendência, o subtítulo e a frase-resumo
  ficam no painel "Como ler", à direita do desenho.
- **Desfazer** (`analise-desfazer`) e **Limpar seleção** ficam no alto da área, fora do título (seção "Desfazer e Limpar seleção").
- **Frase-resumo** (23/10/2026), logo abaixo do subtítulo (`analise-resumo`, lida pelos leitores de tela a cada mudança): o texto
  que o motor devolve em `resumo.texto`, como veio, só com números conferidos do resultado, sem julgamento nem causa. A tela não
  escreve nem completa a frase. Ela fala do indicador do cálculo (o `indicador` da resposta): quando a troca do indicador não
  pede nada novo ao motor, a frase sai até voltar o indicador do cálculo ou chegar um cálculo novo, para nunca descrever o outro
  indicador. Vale nas duas vistas, entra na impressão e no arquivo de método e vai no contexto da conversa. Sem frase na
  resposta, nada aparece no lugar. Desde 24/10/2026, a frase de um território só é individual, e a de vários não traz faixas
  artificiais nem contagens zeradas ([Painel integrado de bolhas](PAINEL_INTEGRADO.md)).
- **O que a classe quer dizer** (24/10/2026, `analise-resumo-significado`): com a tendência de um território só, uma linha abaixo
  da frase-resumo diz a classe que o motor atribuiu e o que ela significa, no texto fixo da explicação, sem o exemplo
  ("Aceleração do crescimento: o indicador subiu em todos os períodos…"; para o não avaliável, o motivo geral). Com vários
  territórios, as contagens por classe ficam acima do quadro de setas, só com as classes que têm territórios; com um só, as
  contagens saem. A classe do filtro em uso continua à vista, mesmo sem territórios, para o filtro poder ser desligado.
- **Detalhes,** abaixo do desenho, em abas: Tabela (os mesmos itens do gráfico, na ordem do código territorial, com 100 linhas
  por página; clicar num cabeçalho só reordena, sem criar posições), Não avaliáveis (por aspecto, com o motivo do motor:
  indicador, distância, variação, tendência, condições, coorte e, com o mapa à vista, coordenada do mapa) e Método e procedência
  (notas, limitações, origem da referência, TPL-11, janela, versão da base e chave de execução). Na impressão, as três partes
  aparecem.

## Pedido ao motor e estado visual

O cliente (`painelApi.ts`) monta o formulário de `/api/painel` (base do Brasil com `dataset=brazil`; planilha com `file`, a aba
e o mapeamento confirmado), envia as opções com as chaves do contrato e normaliza a resposta. Mudar universo, competência,
categoria, referência, janela, grupos, faixas, condições, ordenação, comparação, conjuntos ou premissas pede de novo
(com 150 ms de espera e o pedido anterior cancelado); o gráfico anterior fica à vista, mais claro, enquanto o motor responde. As
últimas seis respostas ficam na memória da tela: voltar a um estado já calculado não pede de novo. Indicador (sem grupos,
grupos do mapa, faixas, tendência, comparação ou ordenação pela variação: a resposta traz população, quantidade e densidade de
cada item, e a troca não pede nada ao motor; com os quintis do mapa no pedido, que seguem o indicador, a troca pede de novo, e a
volta a um indicador já calculado vem da memória), escala, régua, seleção, visão da tendência, primeira ou última competência,
filtros, páginas e a vista do desenho (gráfico, mapa ou lado a lado) são só estado visual. Os pontos do mapa vêm de
`POST /api/painel/mapa` (seção "Vista do desenho"), com memória própria por fonte e competência.

- **Opções enviadas:** `nivel` (`"estados"`, `"municipios"` ou, desde 24/10/2026, `"brasil"`) e `indicador` (`"densidade"` ou
  `"quantidade"`) em todo pedido, porque sem `nivel` o motor responde no contrato de 21/10, que não conhece as chaves da página
  única; no nível estados, `estados` (os prefixos dos estados marcados) quando são só alguns; no nível Brasil, só competência,
  categoria, indicador e, na tendência, a janela; `base`,
  `conjuntos`, `referencia` (desde a segunda rodada de 24/10/2026, o território de referência por elegibilidade:
  `{relacao, delimitacao: {tipo, valores?}, condicao: {atributo, operador, valor}}`; vinda da conversa, ainda pode ser
  `{membros}`), `faixas_distancia`, `competencia_inicial` e `tendencia: {competencias}` (com quatro competências
  ou mais) conforme a família; na visão Série temporal, `serie: {competencias}` (o intervalo; sem escolha, todas as
  competências da base) no lugar da janela, com a competência do pedido igual à última do intervalo; `grupos` ou `faixas` na
  Distribuição; `grupos_mapa: {tipo: "quintis"}` quando a análise não
  tem cor própria e o mapa está disponível (unidades com coordenadas, fora da visão Série temporal); `condicoes`, `ordenar` e
  `comparar` quando pedidos;
  `rotatividade: {inicial, final}`; `premissas`, só nas planilhas (na base do Brasil, o motor recusa); e, desde 24/10/2026,
  `rotulos` (os nomes da unidade e do grupo confirmados no painel Colunas), só nas planilhas, como já ia no pedido do mapa.
  Antes, sem eles, o motor respondia com "unidade/unidades", e a área e a frase-resumo trocavam os nomes da planilha pelos
  genéricos depois do primeiro cálculo.
- **Planilhas:** as premissas escolhidas no painel Colunas (unidade de contagem, referencial, separador decimal e, em
  `confirmed_roles`, as colunas que a pessoa escolheu no seletor, como no pré-exame, D1) vão em todo pedido, somadas às que a
  pessoa confirma numa pendência (um papel confirmado entra na lista `confirmed_roles`). Sem população associada, o indicador começa na quantidade: o motor
  recusa a densidade sem população.
- **Recusa (422):** a mensagem do motor aparece acima do gráfico, com "Voltar ao último gráfico calculado" e "Tentar
  novamente". Com uma pendência de premissa (`pendencia: {chave, opcoes, texto}`), a tela oferece as opções do motor, sem lista fixa;
  a escolhida vai em `options.premissas`.
- **Campos da resposta lidos:** os de sempre (`itens`, `dominios`, `referencia`, `notas`, `limitacoes`, `versao_base`,
  `chave_execucao`) e, por item, `tipo`, `tendencia`, `grupo`, `grupo_mapa`, `faixa`, `faixa_distancia`,
  `referencia_mais_proxima`, `condicoes`, `ordem` e `rotatividade` e, desde a segunda rodada de 24/10/2026,
  `referencia_do_item` (o território de referência de cada município, com os empates) e `serie` (`{observacoes, comparavel,
  motivo}`); no topo, `nivel`, `indicador`, `tendencia` (com
  `sem_classificacao_por_motivo`), `serie` (o intervalo), `referencia` (com `tipo: "elegiveis"`, a definição, os textos e as
  contagens da condição), `grupos`, `grupos_mapa`, `faixas`, `faixas_distancia`,
  `condicoes`, `ordenacao`, `comparacao`, `contexto.brasil`, `disponibilidade`, `sessao`, `rotulos` e `resumo` (`{texto}`, a
  frase-resumo). De `/api/painel/mapa`: `competencia`, `referencial`, `pontos` (`[{id, lat, lon}]`; ponto sem id ou fora do
  intervalo fica de fora) e `sem_coordenada` (`[{id, rotulo, motivo}]`). Campo ausente vira vazio: a resposta de antes continua
  legível. Nos formatos do motor (`Docs/PAINEL_INTEGRADO.md`):
  - `referencia_mais_proxima.empate` lista todos os membros à mesma menor distância; cada um aparece uma vez;
  - `condicoes.por_condicao` traz o `estado` de cada condição, na ordem de `condicoes.definicao` do topo, de onde vem o texto;
  - os limites das faixas vêm em texto decimal com ponto, sem arredondar;
  - na comparação, `maior` e `menor` são listas de ids, com os valores em `itens`, e a diferença de dois itens vem em
    `{a, b, relacao, diferenca}`;
  - o motivo da tendência aparece na tela em palavras, sem o código (dica e Não avaliáveis); o código fica só no CSV
    ("Mudança de direção (MUDANCA_DE_DIRECAO)").

## Acessibilidade

- **Teclado:** as abas (a Seleção e as análises) e as abas dos Detalhes com setas, Home e End; da aba escolhida, Tab leva ao
  painel dela (a apresentação e os ajustes; o painel é o `tabpanel` da aba); o gráfico é uma parada de tabulação, e as setas percorrem as bolhas (de cima para baixo no eixo único; da
  esquerda para a direita com a distância), Enter ou Espaço destacam (ou abrem os municípios do estado), Esc fecha a dica; Esc
  fecha o painel lateral e devolve o foco ao botão que o abriu.
- **Dica no foco** igual à do mouse; cada bolha é um botão com um rótulo com os valores; a régua tem dois `role="slider"`.
- **Vista do desenho:** botões com `aria-pressed`; o mapa desligado continua focável (`aria-disabled`) e, acionado, mostra o
  motivo. A frase-resumo fica numa região `aria-live="polite"`.
- **Equivalentes em texto:** a tabela, os não avaliáveis, as legendas com as contagens, as notas e a frase-resumo. A identidade
  nunca depende só da cor.
- **Movimento:** com `prefers-reduced-motion`, nenhuma transição nem animação; a troca entre o gráfico e o mapa é direta.
- **Celular:** a Seleção e as análises em abas roláveis, com o painel da aba na largura toda; funções no botão "Ferramentas"; escala e
  vista sempre à vista; painel das funções na base da tela e nenhuma rolagem horizontal.
- **Modo escuro:** textos, links, avisos e botões a 4,5:1 ou mais nas superfícies escuras; o foco visível a 3:1 ou mais (seção
  seguinte).

## Modo escuro

Decisão do responsável pelo produto de 23/10/2026: a página segue o esquema de cor do aparelho (`prefers-color-scheme`), sem
botão. Com o aparelho no escuro, a página inteira fica escura: a estrutura (cabeçalho, fonte dos dados, painel Colunas), a área
de análise (abas, ajustes, territórios, funções, painéis, avisos, Detalhes), o gráfico, o mapa e o mapinha, a dica, a conversa
flutuante e os diálogos (privacidade e Nova sessão). **A impressão é sempre clara**, com o aparelho no escuro ou não. Nada muda
nos valores, nos pedidos ao motor nem nos textos, e os seletores de teste continuam os mesmos: é só a cor.

**Como funciona**

- **Variáveis de cor** em `frontend/src/styles.css`: o claro em `:root`, com os valores de antes; o escuro num bloco
  `@media screen and (prefers-color-scheme: dark)`, que vale só na tela (por isso a impressão fica clara). `analise.css` e
  `mapa.css` não têm cor fixa: usam as variáveis. Os `--tom-*` são os canais RGB das cores das classes do Tailwind; em
  `tailwind.config.js`, `white`, `ink`, `teal`, `canvas`, `line` e os tons usados de `slate`, `amber`, `rose`, `blue` e `cyan`
  leem essas variáveis (com `<alpha-value>`), e as classes existentes (`bg-white`, `text-slate-600`, `border-line`…) mudam
  sozinhas. `color-scheme` acompanha (campos, listas e barras de rolagem nativas no escuro).
- **O gráfico e o mapa** escolhem a paleta em JavaScript pelo esquema em uso (`useEsquemaDeCor`, sobre a loja de
  `esquemaDeCor.ts`): `paletaDoGrafico` (`PALETA_CLARA` e `PALETA_ESCURA`, em `painelModel.ts`) para as bolhas, as linhas, a
  grade, os eixos, as legendas, as séries e a rotatividade; `coresDoMapa` e `rampaContinua` (em `mapaModel.ts`) para o mapa, o
  mapinha e a camada da transição. A troca de esquema redesenha na hora, também o canvas do mapa. No começo da impressão
  (`beforeprint`), a troca para o claro é síncrona (`flushSync`), e o desenho vai claro para a página impressa; no fim
  (`afterprint`), volta o escuro.
- **Superfícies do escuro** (da tabela "Chart chrome & ink" da skill de visualização): página `#0d0d0d`; cartões `#171716`;
  superfície do gráfico e do mapa `#1a1a19`; elevados `#232321` (dica, painel das funções, conversa, diálogos, menu do
  Histórico, controles e cartões do mapa). Quanto mais alto, mais claro.
- **Tintas e identidade:** texto principal `#e6e5df`, corpo `#dddcd5`, secundário `#c3c2b7`, apoio `#a5a49b`; destaque
  (azul-petróleo) `#4fbdc6` e links `#6fcbd2`. Os preenchimentos com texto branco no claro (aba e segmento escolhidos, botão
  primário, "Começar a análise", "Li e concordo", enviar) viram claros com texto escuro, a 7:1 ou mais. Avisos em âmbar
  (`#f6d28a` sobre `#2a2312`, 10,8:1) e erros em rosa (`#fda4af` sobre `#2e1719`, 8,9:1).

**Cores do desenho no escuro**, conferidas no validador da skill (`validate_palette.js --mode dark --surface "#1a1a19"`):

| Uso | Claro | Escuro | Validador |
|---|---|---|---|
| Série única (sem camada, "atendem", "os primeiros", permanência) | `#008b9e` | `#1ba3b5` | PASS (5,77:1) |
| Famílias da tendência | `#2a78d6`, `#eb6834`, `#1baf7a` | `#3987e5`, `#d95926`, `#199e70` | PASS em todos os pares: CVD ΔE 9,4; visão normal 20,9 |
| Setas do quadro (24/10/2026): alta e queda | `#2a78d6`, `#eb6834` | `#3987e5`, `#d95926` | PASS em todos os pares: CVD ΔE 24,7 (claro) e 26,8 (escuro); visão normal 33,6 e 31,8; ≥ 3:1 |
| Setas do quadro: pausa | `#898781` | `#898781` | 3,50:1 no claro e 4,85:1 no escuro (a forma da seta também diz a direção) |
| Grupos e faixas (2 a 5) | do claro (menor) ao escuro (maior) | do escuro (menor) ao claro (maior): 5 tons `#184f95` → `#9ec5f4` | `--ordinal` PASS (ponta escura a 2,15:1) |
| Mudança: aumento | `#9cc2ee` → `#184f95` | `#1c5cab` → `#3987e5` → `#9ec5f4` | `--ordinal` PASS |
| Mudança: redução | `#f2ad8c` → `#a8431b` | `#a8431b` → `#d95926` → `#f2ad8c` | `--ordinal` PASS; entre os braços, CVD ΔE 21,8 nos começos e 14,3 nas pontas |
| Mudança: zero | `#c9c7bf` | `#45443f` (1,78:1; ΔL ≥ 0,09 abaixo dos começos) | — |
| Neutro ("não atendem", "demais", "fora das faixas", "saíram") | `#c9c7bf` | `#5f5e5a` (2,68:1) | ao lado da série única: CVD ΔE 18,1, visão normal 20,8 |
| Anel do não avaliável | `#898781` | `#898781` (4,85:1) | — |
| Tinta, tinta secundária, muda | `#0b0b0b`, `#52514e`, `#898781` | `#f0efec`, `#c3c2b7`, `#898781` | 15,2:1, 9,7:1 e 4,85:1 |
| Grade e eixo | `#e1e0d9`, `#c3c2b7` | `#2c2c2a`, `#383835` | recessivos, como no claro |

No escuro, a magnitude fica na luminosidade ao contrário do claro: o maior grupo, o maior aumento e a maior redução são os tons
mais claros. Como no claro, o neutro é cinza de propósito (fica abaixo de 3:1 da superfície), com o alívio da legenda com as
contagens e da tabela; o que é vazado continua tracejado, e nenhum significado depende só da cor.

## Limitações desta entrega e próximos passos

- A conversa e o Histórico dependem da estrutura da página (frente B1); a área entrega o contexto, o estado salvo e aplica o
  pedido.
- A Análise espacial nos estados e no Brasil espera a escolha de municípios (os estados e o Brasil não têm um ponto no mapa);
  a Tendência vale para os estados e para o Brasil desde 24/10/2026.
- Não há mapa no nível dos estados: os ladrilhos dos estados não foram aprovados.
- A rotatividade depende do motor aceitar planilhas com o identificador individual em `/api/painel`.
- O modo escuro segue o aparelho, sem botão para escolher (decisão de 23/10/2026).

## Testes

- **Modelo puro (Node):** `frontend/tests/painel.test.mjs`. Cobre a formatação pt-BR; o tamanho pela população; o eixo Y do
  indicador com o arranjo horizontal sem sobreposição; o modo leve preso à largura; a ausência de escala logarítmica
  automática; a análise espacial; o cometa vertical só com a variação do motor; as camadas de cor (classe, grupos, faixas,
  condições e ordem); a nomenclatura territorial (municípios e estados; distritos e províncias; comunas); a escolha de
  territórios (marcar e desmarcar unidades e grupos; desde 24/10/2026, a seleção cumulativa entre estados, o que está marcado
  estado a estado, o resumo da seleção, inclusive a planilha sem a lista das unidades, e o lugar no título, com os nomes de uma
  ou duas unidades); o título; as opções do pedido com as chaves do contrato (também no nível Brasil e com os estados
  escolhidos); a comparação que sai quando os itens dela saem da análise; o que falta para pedir; a disponibilidade das famílias; o comando da conversa; a janela e as séries; a tabela em páginas; o CSV em
  precisão integral; o estado salvo; o contexto do gráfico; e a normalização da resposta no cliente. Desde 23/10/2026,
  `frontend/tests/areaDeAnalise.test.mjs` cobre os ajustes de cada análise (sem indicador na rotatividade; nos estados, os da
  distribuição), a disponibilidade do mapa com o motivo e o atalho, a pintura do mapa (a camada do gráfico, os quintis do motor
  ou a cor contínua da rotatividade, sem pergunta) e quando o pedido leva os quintis do mapa, a cor contínua e o tamanho, as
  ligações (até 30), o estado salvo com a vista (e o estado antigo sem ela), o aspecto "mapa" dos não avaliáveis, a vista
  pedida na conversa, a frase-resumo no cliente e no arquivo de método, os dados do mapa normalizados e, desde o pedido
  integrado de 23/10/2026, os nomes das abas, a abertura sem seleção, a apresentação de cada aba (base do Brasil, planilha de
  distritos e antes dos dados, sem códigos internos), o que significa cada classe da tendência, o motivo de cada unidade em
  palavras e a nota das sem classificação; desde 24/10/2026, o quadro de setas (um ponto por período, uma seta por avanço com o
  sinal do motor, a escala da linha, a lacuna sem ponto inventado e a ordem por classe), as classes em palavras simples, com um
  exemplo cada (os exemplos conferidos pela mesma regra do motor, `classify_speeds`, passo a passo), o que a classe quer dizer
  (`significadoDaClasse`), a Seleção só com a orientação curta e a apresentação sem códigos; desde a segunda rodada de
  24/10/2026, o histórico do Desfazer (um passo por ação, o arraste contínuo como um passo só, o limite de 80 passos e, desde
  25/10/2026, os textos do botão e do aviso com o nome Desfazer), o período com que a tendência abre (`janelaPadrao`: o anual; sem ele, o único ritmo; sem nenhum, a escolha), as
  visões (Tendência, Trajetória e Série temporal) e os ajustes de cada uma, o intervalo da Série temporal (a extensão inteira,
  o intervalo escolhido, a leitura da resposta, o CSV com uma coluna por competência e o método), o desenho dela (a cor única
  e o conjunto não comparável só com os pontos), a Trajetória (os períodos do meio no rastro e na dica, sem caminho sem a
  variação) e o território de referência (a guarda do formato, as delimitações que a fonte tem, o valor de corte pela natureza
  do atributo, a resposta com `referencia_do_item`, a dica, o CSV, as ligações do mapa e a apresentação); desde 25/10/2026, o mapa
  com todas as unidades em análise (`itensParaOMapa`), os filtros que esmaecem nele (`dentroDosFiltros`), a cor única vazada sem
  o valor do indicador, o aviso "Fora do gráfico" (`textoForaDoDesenho`) e a opacidade das bolhas, que não depende da seleção
  (`opacidadeDaBolha`); e os territórios base (`basesPossiveis`, `basesEmUso`, `normalizarBases`, `parDaBase`,
  `paresDasBases`, `referenciasDeContexto`, `textoDoParDaBase`, `textoDosTerritoriosBase`, `resumoDosTerritoriosBase` e
  `dicaDaReferenciaDeContexto`: todos ou alguns, a referência fora da análise, também em análise e pelo nome, o empate com
  todas as empatadas, sem referência, a referência de contexto com as bases ligadas, os textos e a dica, o pedido igual com e
  sem bases, o estado salvo, também o de antes, e a escala do gráfico com as referências de contexto). `frontend/tests/painel.test.mjs` cobre o
  campo Período: os últimos 4 períodos de cada ritmo (anual, semestral, base mensal, anos), o ritmo indisponível com o motivo e
  o ritmo de uma janela; e, desde a regra sem janela longa (24/10/2026), o ritmo pelos intervalos e a janela que vem da
  conversa (os últimos 4 do ritmo, com o aviso; sem ritmo, o aviso da escolha; nada na rotatividade nem na análise espacial);
  desde 25/10/2026, a legenda de tamanho na proporção exata (nenhuma referência abaixo do mínimo visível).
  O modo escuro tem `frontend/tests/modoEscuro.test.mjs`: a loja do esquema
  (o escuro só na tela e fora da impressão, o aviso síncrono no começo da impressão), as paletas do gráfico e do mapa por
  esquema (o claro igual ao de antes; no escuro, os valores validados, as rampas do escuro ao claro, o zero abaixo dos braços, o
  contraste), a pintura de cada camada no escuro, as variáveis de `styles.css` contra as paletas e contra as classes do
  Tailwind, o contraste dos textos, avisos, links e botões nas superfícies escuras e a ausência de cor fixa nas folhas de
  estilo.
- **Navegador:** `backend/tests/ui_area_de_analise.py`, nas suítes `bloco1` (catálogo sintético) e `base-versionada`
  (`ADT_BLOCK1_REAL=1`). Confere: E0 sem números nem pedido, desde 24/10/2026 sem as abas, só com a identificação, a chamada e
  as duas entradas; a base sem seleção automática (nenhum pedido, a Seleção aberta e as abas das análises com a apresentação
  em "Entenda esta análise", recolhido desde a primeira visita e, depois, como a pessoa deixou); os níveis da Seleção (Estados
  com "Marcar todos os estados", cada nível com a sua escolha); E1 com os estados escolhidos, a instrução e a ação na dica;
  desde 24/10/2026, a seleção cumulativa entre estados (abrir outro estado não muda nada nem pede ao motor), a busca no alto, o
  Brasil como unidade (só o nível no pedido, um item, a frase do motor, as funções e o mapa desligados, sem Grupos) e os estados
  escolhidos no pedido (`estados`); desde a segunda rodada de 24/10/2026, o nome da plataforma em E0; Desfazer (o "Voltar" até
  25/10/2026, desde então com a seta curva do desfazer, `lucide-undo`) e Limpar seleção no alto, lado a lado e fixos ao rolar (o
  Desfazer desligado, com "Nada para desfazer ainda", e, depois de cada passo, o `title` com o que ele desfaz: abrir uma aba,
  marcar e desmarcar, o × de um município e de um estado, abrir os municípios pela bolha, Limpar seleção, a régua, o território
  de referência, o período, a visão, Limpar filtros; cada Desfazer devolve o estado de antes, um passo por vez, com o aviso
  "Desfeito: …"); Limpar seleção sem apagar os dados (os botões de antes da Seleção, "Desfazer" e "Desfazer a limpeza", não
  existem mais: o único `analise-desfazer` é o do alto); "Voltar aos estados" preenchido e maior, abaixo do Desfazer do alto, e
  diferente dele (pelo estilo calculado); a Seleção em duas áreas, com o que está marcado à direita, estado a estado, e o × de
  cada município e de cada estado, desfeitos pelo Desfazer; as abas só com o nome (sem os apoios de antes); os ajustes dentro de cada
  análise (estados, Distribuição, Análise espacial e Tendência, com o mesmo indicador e a escala fora deles, na barra junto do
  desenho); a vista do desenho (o gráfico de início; nos estados e na Série temporal, o mapa desligado, com o motivo e o
  atalho); abrir o Amazonas pela bolha e pela lista; a frase-resumo do motor, com a competência da resposta (e fora da tela
  quando o indicador à vista não é o do cálculo); marcar e desmarcar, marcar e desmarcar todos (sem seleção, nada da seleção
  anterior à vista); os quintis do mapa no pedido e a Quantidade (um pedido; a volta à densidade, da memória); a régua pelo
  teclado e pelo mouse; quartis; a análise espacial com o Território de referência (o título "Referência da distância" e os
  controles da lista de candidatos ausentes; sem valor padrão, o que falta escolher; a prévia; o pedido com a relação, a
  delimitação e a condição; o eixo X e as distâncias iguais às do motor, nunca até o próprio município; o mais distante, nunca
  mais perto que o mais próximo; sem elegíveis, a mensagem `analise-ref-sem-resultado`, sem distância zero, e "Mudar o
  território de referência" reabrindo o painel com a definição em uso; o convite ao mapa na base versionada; a recusa e a
  pendência no catálogo sintético); a tendência (o Anual, ou o único ritmo da base, e o Gráfico ao abrir; "Entenda esta
  análise" recolhido; o painel "Como ler" à direita e a divisória pelo teclado, com os limites; as visões Tendência, Trajetória,
  com os pontos dos períodos do meio, e Série temporal, com toda a série e o intervalo escolhido em "De" e "Até", no pedido
  `serie`, e o Método; entre a Tendência e a Trajetória, a troca não pede nada ao motor), com a nota das sem classificação e o
  motivo em palavras na dica, o campo Período (o anual desligado, com o motivo, no catálogo sintético; os últimos 4 períodos no
  pedido) e o quadro de setas (cada linha com a classe na coluna "Tendência", uma seta por velocidade do motor com o sinal dela e
  um ponto por observação; a ordem por classe; o filtro pela contagem; a escolha da linha e as velocidades dela no painel; a
  dica no mouse e no foco); a rotatividade com a apresentação e o motivo, sem pedido; Condições (com o convite ao mapa),
  Ordenar, Comparar e Juntar (com a orientação e os escolhidos em etiquetas, sem os cartões de valores; desde 25/10/2026, as
  bolhas marcadas para Comparar sem esmaecer as demais, todas com a opacidade inteira); "Limpar filtros", desfeito pelo
  Desfazer; o CSV; os Detalhes; o modo leve com todos os municípios do Brasil (base versionada); e o celular (o painel dos
  ajustes na largura, a vista à vista, Desfazer e Limpar seleção dentro da largura e as duas áreas da Seleção uma sobre a
  outra). Cada bolha é conferida com a resposta do motor. O mapa em si (pontos, pintura, transição e lado a lado) tem
  roteiro próprio.
- **Navegador, mapa:** `backend/tests/ui_mapa.py`, na suíte `base-versionada`, confere o mapa contra as respostas do motor
  (detalhes em [MAPA_DA_PAGINA_UNICA.md](MAPA_DA_PAGINA_UNICA.md#testes)).
- **Navegador, modo escuro:** `backend/tests/ui_modo_escuro.py`, na suíte `bloco1`, com o navegador no escuro
  (`color_scheme="dark"`): o aviso de privacidade, a página com o banner, as entradas dos dados, as abas e a apresentação, a
  conversa, a base sem seleção, os estados e o Amazonas com fundo escuro e textos a 4,5:1 ou mais (pelo estilo calculado); as bolhas na série única do escuro (`#1ba3b5`), com o anel na superfície escura; a
  dica, o painel de uma função, os Detalhes e o diálogo de Nova sessão; o mapa (a superfície escura no canvas, as cores do
  escuro e a legenda dos quintis, ou, se o motor não entregar os pontos no catálogo sintético, só a área do mapa, com o
  registro na saída); e a
  impressão de volta ao claro. Tira capturas (`escuro-*.png`) para a conferência visual.
