# Área de análise da página única

Decisões do responsável pelo produto de 22/10/2026: uma análise integrada, sem duas telas. A página é sempre a análise. Desde
23/10/2026, uma linha de abas reúne a **Seleção de Territórios** (o conjunto analisado, compartilhado por todas as análises) e as
quatro análises com os nomes padronizados: **Análise de Distribuição**, **Análise Espacial**, **Análise de Tendência** e
**Análise de Rotatividade**. Cada aba abre com a apresentação do que ela faz, mesmo quando a análise não pode ser executada com
os dados; as análises mostram os ajustes delas no mesmo painel. Há um indicador único, funções comuns a todas as análises e,
abaixo, os Detalhes. O desenho é o gráfico de bolhas e, desde 23/10/2026, também o mapa, como segunda vista da mesma análise
(Gráfico | Mapa | Lado a lado). No gráfico, o eixo Y é o indicador; o eixo X só aparece com a análise espacial. Este documento descreve a área de análise. O motor e as rotas
(`/api/painel`, `/api/painel/referencias` e `/api/painel/mapa`) estão em [Painel integrado de bolhas](PAINEL_INTEGRADO.md); a
estrutura da página (cabeçalho, fonte de dados, Histórico e conversa) fica no README e nos documentos da interface e da conversa.

Código: `frontend/src/AreaDeAnalise.tsx` (a área e o estado), `PainelChart.tsx` (bolhas, dica e legendas), `MapaAnalise.tsx`
(o mapa) e `transicaoVistas.ts` (a troca animada entre o gráfico e o mapa), montados pelo contrato de `mapaContrato.ts`,
`PainelTerritorios.tsx` (escolha dos territórios), `PainelSeries.tsx` (séries da tendência), `PainelSetas.tsx` (quadro de setas
da tendência, na visão Classes), `PainelRotatividade.tsx` (barras de
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
  onEscolherFonte={tipo => ...}         // "Dados do Brasil" e "Enviar meus dados", na abertura e no "Trocar" da fonte
  apiBase={string}                      // o endereço da API, para o "Modelo de planilha XLSX"
  trocandoFonte={boolean}               // "Trocar" pedido na barra da fonte: a escolha volta à área, com "Cancelar"
  onCancelarTroca={() => ...}/>
```

- **Fonte:** `null` é a abertura (E0). A troca de fonte (outra versão, outra planilha) recomeça a área. "Nova análise" remonta a
  área (`key`): os mesmos dados, sem territórios escolhidos.
- **Entradas dos dados** (23/10/2026): "Dados do Brasil", "Enviar meus dados" e "Modelo de planilha XLSX" ficam na área central
  (`analise-abertura`, com `analise-fonte-brasil`, `analise-fonte-arquivo` e `analise-fonte-modelo`) e na conversa, com as
  mesmas ações; não há mais botões de fonte no alto da página. O "Trocar" da barra da fonte traz as mesmas três entradas de
  volta à área (`analise-troca-fonte`, com `analise-troca-cancelar`), e a análise atual continua à vista até a nova fonte ficar
  pronta.
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
  província…). Nenhum texto da área fixa "município" ou "estado": título, subtítulo, lista de territórios, trilha, dica, tabela,
  Detalhes, exportação e mensagens saem dos rótulos, com concordância simples ("Todas as províncias", "Ver os 12 distritos",
  "Cada bolha é uma comuna"). O gênero é o informado (`genero`) ou, sem ele, deduzido pela terminação.

## Estados da tela

| Estado | O que aparece |
|---|---|
| E0, antes dos dados | Moldura limpa, sem números nem bolhas de exemplo: "Escolha os dados para começar", com "Dados do Brasil", "Enviar meus dados" e "Modelo de planilha XLSX". As abas ficam visíveis e abrem com a apresentação; clicar numa análise registra a intenção ("Você escolheu Análise de Tendência. Agora escolha os dados."). Título: "Diagnóstico territorial da força de trabalho em saúde". |
| E1, dados carregados sem seleção | Sem seleção automática (23/10/2026), na base do Brasil e na planilha: "Os dados do Brasil foram carregados e estão prontos para a análise." (ou "A planilha foi carregada…"), "Selecione os territórios que deseja analisar." e a aba Seleção de Territórios aberta, com a lista. Nada é pedido ao motor até a escolha, e nenhum resultado anterior fica à vista. |
| E1, estados | Os estados em bolhas (`nivel: "estados"`), escolhidos na Seleção ("Todos os estados (27)") ou pela conversa ("todos os estados"), com a linha de contexto do Brasil e a instrução "Clique num estado para ver os municípios dele". |
| E2, unidades na Distribuição | As bolhas das unidades escolhidas no eixo do indicador. |
| E3, outra família | Análise espacial, Tendência ou Rotatividade. |
| E4, função em uso | Um painel lateral aberto (no celular, sobe da base da tela). |

O estado vai em `data-estado` da área; a vista do desenho em exibição, em `data-desenho` (`grafico`, `mapa` ou `lado`).

## Escolha dos territórios

Pedido do responsável (22/10/2026): a escolha precisa ser visível e didática, sem adivinhar onde clicar e sem depender de
digitar o nome de um município. Desde 23/10/2026, a lista fica na aba **Seleção de Territórios**, a primeira da linha das
análises (`analise-aba-territorios`, com o resumo da seleção em `analise-aba-territorios-resumo`). O painel da aba começa com o
texto "Selecione os territórios que deseja incluir em suas análises. Você poderá acrescentar ou retirar territórios a qualquer
momento, e as análises serão atualizadas conforme a seleção realizada." e mostra a lista em colunas na tela larga. A mesma
seleção vale para todas as análises: cada aba de análise mostra o resumo dela (`analise-selecao-resumo`) com "Alterar a
seleção" (`analise-selecao-alterar`), que volta à Seleção. A referência da Análise Espacial e a janela da Análise de Tendência
continuam dentro de cada análise, separadas dos territórios analisados.

- **Brasil:** duas opções explícitas, "Todos os estados (27)" (a visão E1, com a linha de contexto do Brasil) e "Todos os
  municípios do Brasil (5.570)" (modo leve, mais lento).
- **Estados:** os 27 numa lista, com nome, sigla e a caixa "Todos os municípios de <estado>" (marca o estado inteiro, junto com o
  que já estiver marcado) e a ação "Ver os N municípios", que abre a lista do estado ali mesmo e põe só esse estado, inteiro, no gráfico.
- **Municípios do estado aberto:** caixas de marcar, na lista da página (sem rolagem escondida), com "Marcar todos" e "Desmarcar
  todos". Desmarcar um município de um estado inteiro deixa os demais marcados, um a um; marcar o último que faltava devolve o
  estado inteiro. Com mais de 120, atalhos pela letra inicial ajudam, e "Todas" mostra a lista inteira.
- **Busca:** "Procurar pelo nome ou código (opcional)", só como complemento.
- **No gráfico (E1):** clicar numa bolha de estado (ou Enter na bolha em foco) abre os municípios dele; a dica da bolha sob o
  mouse ou em foco mostra a ação "Ver os N municípios".
- **Trilha de volta,** em qualquer estado: "Brasil › Amazonas (62 municípios)", "Brasil › Amazonas › 3 municípios", "Brasil ›
  Todos os municípios (5.570)". "Brasil" volta aos estados; o nome do estado volta ao estado inteiro.
- **Planilhas:** com coluna-mãe (o papel `grupo_territorial`), a lista dos grupos, cada um com "Ver as N <unidades>" e as
  caixas das unidades, como os estados; o grupo de cada unidade vem do catálogo do pré-exame (`parents`, desde 23/10/2026;
  antes, a lista ficava sem os grupos). Sem coluna-mãe, a lista das unidades em ordem alfabética, com as caixas. Não há bolhas de grupo nas planilhas
  (`disponibilidade.grupos` do motor). No pedido, `base.municipios.estados` leva os valores do grupo e `ids`, `code:<código>` ou
  `name:<nome>`.
- **Abertura:** a base do Brasil e a planilha abrem sem territórios marcados (23/10/2026); a área avisa que os dados estão
  prontos e abre a Seleção. Antes, a base do Brasil abria nos estados, e a planilha, com todas as unidades marcadas.
- **Sem unidades marcadas,** nada é pedido ao motor, e o gráfico, o mapa e a frase-resumo da seleção anterior saem da tela;
  a área pede a escolha.

## Abas, apresentação e ajustes de cada análise

Desde 23/10/2026, uma linha de abas (`role="tablist"`, "Seleção de territórios e análises"): a Seleção de Territórios e as
quatro análises, nesta ordem e na mesma linha (no celular, roláveis). A aba escolhida se liga a um painel colado nela
(`analise-aba-painel`, `role="tabpanel"`, com `data-aba`), que começa pela **apresentação** (`analise-apresentacao`): um título e
um ou dois parágrafos, em linguagem simples, só sobre o que a área faz, com os nomes territoriais da fonte (municípios e
estados; distritos e províncias…). Na Análise de Tendência, a apresentação lista o que significa cada classe
(`analise-apresentacao-classes`). Depois da apresentação, nas análises, vêm os ajustes (`analise-ajustes`, com
`data-familia`), só o que vale para aquela análise, e o resumo da seleção.

**Toda aba abre** (23/10/2026), mesmo a de uma análise que não pode ser executada com os dados: as abas não ficam mais
desabilitadas (`data-disponivel` diz se a análise se executa). Nesse caso, o painel mostra a apresentação e o motivo
(`analise-familia-motivo`, "Indisponível com estes dados: …", com "Enviar meus dados" quando é o caso e "O desenho abaixo
continua com a <análise>"), sem os ajustes, e o desenho fica com a última análise executada; nada é pedido ao motor. Exemplo: a
Análise de Rotatividade com a base do Brasil, que tem contagens e não pessoas identificadas.

| Análise | Ajustes dentro dela |
|---|---|
| Análise de Distribuição | Indicador, Categoria (com mais de uma), Competência, Grupos e faixas |
| Análise Espacial | Indicador, Categoria, Competência, Referência (a escolhida e o botão que abre o painel da referência) |
| Análise de Tendência | Indicador, Categoria, Período (Anual ou Semestral, com as 4 competências usadas; o ritmo que a base não tem fica desligado, com o motivo) e Visão (Classes, no quadro de setas, Mudança e Séries; "Primeira", "Última" e "Reproduzir" só na Mudança) |
| Análise de Rotatividade | Períodos inicial e final da coorte e Categoria, sem indicador |
| Estados (E1), em qualquer aba, e análise que espera os municípios | Indicador, Competência, Grupos e faixas (o desenho é a distribuição) |

O texto das apresentações tem medida de leitura limitada, entrelinha folgada, justificação com hifenização na tela larga (no
celular, alinhado à esquerda) e a mesma hierarquia em todas as abas.

- **Indicador** (Densidade ou Quantidade): um só para todas as abas. A escolha acompanha a pessoa ao trocar de aba e fica sempre
  à vista; quem escolheu Quantidade na Distribuição encontra Quantidade marcada na Tendência. Numa planilha sem população, o
  botão Densidade fica desligado, com o motivo à vista e no `title` ("Sem população na planilha: só a quantidade."): o motor
  recusa a densidade sem população.
- **Categoria:** quando a fonte tem mais de uma, fica junto do indicador.
- **Competência:** na Distribuição, na Análise espacial e nos estados (a mais recente, dita no título).
- **Escala:** sai dos ajustes, porque muda só o desenho ("como ver"): fica na barra das funções, junto da escolha da vista, e
  aparece só quando se aplica (no gráfico, fora da Rotatividade e da visão Séries; o mapa não tem escala própria). É linear, a
  partir do zero; a logarítmica fica só por escolha da pessoa e só com todos os valores positivos (Parte 13, L1994). A escala
  logarítmica automática de 22/10/2026 saiu.

O que cada análise mostra:

- **Distribuição** (base, sempre ativa): grupos por posição (nenhum, quartis, quintis ou decis; CAP-DIS-02) ou faixas digitadas
  pela pessoa (CAP-DIS-03, limites como "0; 1; 2; 5"). O grupo e a faixa de cada bolha, os cortes e as contagens vêm do motor.
  Até cinco grupos ganham cor; nos decis, só as linhas de corte.
- **Análise espacial:** acrescenta o eixo X, a distância em linha reta (km) até a referência. A referência sai por critério
  (densidade, quantidade ou população, do maior para o menor ou o contrário, na ordem do motor, com "Usar o primeiro" e a
  escolha no empate), pelo nome ou pelos membros de um conjunto; com vários membros, a distância vai até o mais próximo, e a dica
  diz qual é (com os empates). Faixas de distância opcionais (CAP-ESP-03). A nota TPL-11 aparece sempre junto. Nos estados, a
  família espera a escolha de municípios (os estados não têm coordenadas). A disponibilidade vem do motor
  (`disponibilidade.espacial`): numa planilha sem coordenadas ou sem um referencial aceito (SIRGAS 2000 ou WGS 84), a aba abre
  com a apresentação e o motivo do motor, sem os ajustes; quando o motor pede a escolha do referencial, a tela mostra as opções
  que ele mandar.
- **Tendência:** desde 24/10/2026, o campo **Período** (`analise-periodo-anual` e `analise-periodo-semestral`) escolhe o ritmo, e a
  janela são os **últimos 4 períodos** dele, contados da competência mais recente: o mínimo de DA-15 (4 períodos, 3 avanços). A
  escolha é da pessoa, sem ritmo padrão (decisão 5a): até ela, nada de tendência é pedido, e o aviso diz "Escolha o período da
  tendência, anual ou semestral: a análise usa os últimos 4 períodos.". No anual, a cada passo vale a competência mais perto de
  12 meses antes; no semestral, de 6 meses antes, com folga de 2 meses (de janeiro a junho são 5 meses; de junho a janeiro, 7).
  Na base do Brasil: anual = 06/2021, 06/2022, 06/2023 e 06/2024; semestral = 01/2023, 06/2023, 01/2024 e 06/2024. Sem 4 períodos
  assim (por exemplo, uma planilha só com junhos, no semestral, ou com um ano faltando, no anual), o ritmo fica desligado, com o
  motivo à vista. O texto do campo (`analise-periodo-texto`) lista as 4 competências usadas. Os atalhos "Últimos 4 junhos",
  "Série anual de junho" e "Todas as competências" e o painel que marcava as competências uma a uma saíram. Uma janela pedida na
  conversa (ou de um estado salvo antes) continua valendo como veio, com o texto "Janela de N períodos…", até a escolha de um
  ritmo. O método não muda (CAP-TEN-01). A visão é só estado visual (trocar não pede nada novo):
  - **Mudança:** entre a primeira e a última competência da janela (CAP-TMP-01), o cometa e a cor divergente contínua: azul é
    aumento, laranja é redução, cinza é sem mudança (V-05; nunca "crescimento"). "Primeira" e "Última" alternam as posições;
    "Reproduzir" desliza as bolhas da primeira à última (com movimento reduzido ou no modo leve, o botão vira "Ir para a
    última", sem animação). Desde 24/10/2026, o cometa e esses botões ficam só na Mudança.
  - **Classes, no quadro de setas** (24/10/2026, no lugar das bolhas; `PainelSetas.tsx`, `analise-setas`): como um painel de
    cotações, uma linha por unidade (`analise-seta-linha`), com o nome, o desenho dos períodos (um ponto por observação do
    motor e uma seta por avanço, `analise-seta`, com o sinal da velocidade do motor: para cima é alta, em azul; para baixo, queda,
    em laranja; para o lado, pausa, em cinza), o último valor e a variação entre o primeiro e o último período (CAP-TMP-01, do
    motor, com ▲ ou ▼) e a classe do motor, com o ícone da família. A tela só posiciona e ordena: a classe e o sinal de cada seta
    são do motor (RQ-REP-02). Cada linha tem a própria escala vertical (o desenho mostra o caminho; os valores ficam ao lado, na
    dica e na tabela), com amplitude mínima de 5% do maior valor, para uma variação ínfima não parecer um salto. As linhas vêm
    agrupadas pela classe, na ordem da SPEC (os não avaliáveis no fim), e, dentro dela, pela variação, da maior para a menor; com
    a Ordenação em uso, pela posição do motor; com as Condições, a situação aparece ao lado do nome. São 50 linhas por página
    (`analise-setas-paginas`). A dica (`analise-seta-dica`), no mouse e no foco, lista cada período com o valor e o avanço até
    ele, a variação e o que a classe quer dizer; Escape fecha. Clicar na linha (ou Enter) escolhe a unidade, para Séries e
    Comparar. Acima do quadro, a contagem por classe do motor, que também filtra; cada contagem traz no `title` o que a classe
    quer dizer. Abaixo, a legenda das setas (`analise-setas-legenda`) e a das famílias com as contagens. Numa janela longa
    (pedida na conversa), a ponta da seta só aparece quando o avanço tem espaço, e o eixo mostra o primeiro e o último período.
    No lado a lado, a linha sob o mouse destaca o ponto no mapa, e o contrário também. A escala (linear ou logarítmica) não se
    aplica ao quadro.
  - **Classes explicadas** (23/10/2026; desde 24/10/2026, com o vocabulário das regrinhas: o **avanço** é a mudança de um período
    para o seguinte, alta, queda ou pausa): a apresentação da aba diz, em palavras, a regra de cada classe de DA-15 (crescimento,
    aceleração e desaceleração do crescimento, declínio, aceleração e desaceleração do declínio, sem classificação e não
    avaliável), que uma alta sozinha é só uma alta e duas ainda não são tendência (são precisos 4 períodos, 3 avanços), sem criar
    classe nem critério, e termina com a âncora do método (CAP-TEN-01, DA-15), exigida pela SPEC (V-05) para descrever as
    classes. A dica e os Não avaliáveis dizem o motivo de cada unidade sem classe em palavras, sem o código ("Sem classificação:
    entre os períodos, houve alta e queda (mudança de direção)."). Abaixo das contagens, uma nota
    (`analise-nota-sem-classificacao`) conta as unidades sem classificação por motivo, com os números do motor
    (`sem_classificacao_por_motivo`), e, quando nenhuma unidade recebeu classe, explica a regra: a classificação exige a mesma
    direção em todos os avanços, e uma única mudança de direção basta para a série ficar sem classificação; isso é o resultado
    do método, não falta de dados. O diagnóstico de 23/10/2026 (com a base
    versionada: 62 de 62 municípios do Amazonas sem classificação nas 22 competências, todos por mudança de direção) está em
    [Painel integrado de bolhas](PAINEL_INTEGRADO.md).
  - **Séries:** linhas por competência (no tempo real entre elas), até 12 unidades escolhidas (na tabela, nas bolhas ou "os de
    uma classe"; desde 24/10/2026, também nas linhas do quadro de setas), com pequenos múltiplos na mesma escala acima de 4. Um
    ponto por observação do motor; lacunas não são ligadas e não há linha ajustada. As velocidades do motor da unidade em foco aparecem em barras.
  - Com menos de quatro competências, Classes e Séries ficam indisponíveis, com o texto do catálogo ("A análise de tendência
    exige quatro observações válidas.").
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
  - **na visão Séries** da tendência, que é só do gráfico.
- **Convite:** "Ver onde ficam no mapa" (`analise-convite-mapa`) aparece com as Condições aplicadas e na Análise espacial, com o
  mapa disponível e a vista no gráfico.
- **Troca animada:** entre o gráfico e o mapa, as bolhas deslizam até o lugar de cada ponto (cerca de 0,7 s). Com movimento
  reduzido, com mais de 400 itens (modo leve) ou no lado a lado, a troca é direta.
- **Pontos do mapa:** vêm do motor (`POST /api/painel/mapa`, o mesmo formulário de `/api/painel`, com a competência e a
  categoria do que está desenhado e, nas planilhas, as premissas e os rótulos): as coordenadas autorizadas de cada unidade e as
  que não têm coordenada válida, com o motivo. A tela pede quando o mapa aparece e, em segundo plano, quando o gráfico mostra
  unidades com o mapa disponível; guarda as últimas seis respostas por fonte e competência. Uma pendência do motor (por exemplo,
  o referencial de uma planilha) aparece na área do mapa, com as opções que ele mandar, como as pendências do gráfico.
- **O que a área entrega ao mapa:** os mesmos itens do gráfico (sem os estados); o que fica fora da régua e dos filtros aparece
  esmaecido, não escondido (decisão de 23/10/2026); a pintura do gráfico quando há uma camada de cor (grupos, faixas, condições,
  ordem, classes ou variação); na Rotatividade, a permanência da coorte inicial em cor contínua (0 a 100%); sem camada de cor
  da análise (a distribuição sem grupos nem faixas e a análise espacial, sem condições nem ordenação), os **5 grupos iguais
  (quintis)** do indicador, sem pergunta (23/10/2026): o pedido ao motor leva `grupos_mapa: {tipo: "quintis"}` junto com a
  análise, e o mapa pinta cada ponto pelo `grupo_mapa` do motor, com a legenda dos quintis (rótulos e contagens do motor). O
  gráfico, a frase-resumo, a tabela e o CSV não mudam com eles; sem os grupos na resposta (uma análise guardada antes, ou menos
  de duas unidades com valor), a cor única do gráfico. O tamanho pela população (densidade), pela quantidade ou pela coorte
  inicial; o valor do Brasil só como marca de contexto; a mesma dica do gráfico; a referência e as ligações ilustrativas dos
  selecionados (até 30) até o membro da referência mais próximo. A pergunta "Como pintar o mapa?" (quintis, faixas ou cor
  contínua) saiu em 23/10/2026.
- **Não avaliáveis:** com o mapa à vista, as unidades sem coordenada válida ficam fora do mapa (no gráfico, continuam) e entram
  em Não avaliáveis, no aspecto "Sem coordenada válida para o mapa", com o motivo do motor.
- **Depois da primeira vez,** o mapa continua montado (oculto) enquanto houver mapa: volta como foi deixado, com o zoom.

## Eixos, marcas e cores

- **Eixo único (Distribuição, Tendência na Mudança e estados):** Y é o indicador. Na visão Classes da tendência, o quadro de
  setas (acima) substitui as bolhas, com a escala própria de cada linha. As bolhas se espalham na horizontal só como arranjo, para
  não se sobreporem, e a nota diz "a posição horizontal é só arranjo". Arranjo exato até 400 bolhas (o gráfico cresce na altura
  se precisar); acima disso, ou se não couber, o arranjo leve, numa faixa limitada da largura, com bolhas semitransparentes.
- **Análise espacial:** X = distância até a referência (km), Y = indicador. Sem reta de tendência nem correlação.
- **Tamanho:** população, com área proporcional (raio pela raiz quadrada) e diâmetro mínimo visível; legenda com três
  populações redondas.
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

A seleção (clique ou Enter nas bolhas, ou a caixa na tabela) esmaece os demais; Comparar e Juntar agem sobre ela.

## Título e Detalhes

- **Título dinâmico:** "Densidade de médicos nos municípios do Amazonas · junho de 2024"; "Densidade de médicos nos estados ·
  junho de 2024"; "Densidade de médicos e distância até MANAUS (AM) · Amazonas · junho de 2024"; "Tendência da densidade de
  médicos · Amazonas · junho de 2021 a junho de 2024". "Médicos" sai da categoria MEDICINA; com outra, "profissionais de
  <categoria>". Subtítulo: "Cada bolha é um município. O tamanho mostra a população."
- **Frase-resumo** (23/10/2026), logo abaixo do subtítulo (`analise-resumo`, lida pelos leitores de tela a cada mudança): o texto
  que o motor devolve em `resumo.texto`, como veio, só com números conferidos do resultado, sem julgamento nem causa. A tela não
  escreve nem completa a frase. Ela fala do indicador do cálculo (o `indicador` da resposta): quando a troca do indicador não
  pede nada novo ao motor, a frase sai até voltar o indicador do cálculo ou chegar um cálculo novo, para nunca descrever o outro
  indicador. Vale nas duas vistas, entra na impressão e no arquivo de método e vai no contexto da conversa. Sem frase na
  resposta, nada aparece no lugar.
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

- **Opções enviadas:** `nivel` (`"estados"` ou `"municipios"`) e `indicador` (`"densidade"` ou `"quantidade"`) em todo
  pedido, porque sem `nivel` o motor responde no contrato de 21/10, que não conhece as chaves da página única; `base`,
  `conjuntos`, `referencia`, `faixas_distancia`, `competencia_inicial` e `tendencia: {competencias}` (com quatro competências
  ou mais) conforme a família; `grupos` ou `faixas` na Distribuição; `grupos_mapa: {tipo: "quintis"}` quando a análise não
  tem cor própria e o mapa está disponível (unidades com coordenadas, fora da visão Séries); `condicoes`, `ordenar` e
  `comparar` quando pedidos;
  `rotatividade: {inicial, final}`; `premissas`, só nas planilhas (na base do Brasil, o motor recusa).
- **Planilhas:** as premissas escolhidas no painel Colunas (unidade de contagem, referencial, separador decimal e, em
  `confirmed_roles`, as colunas que a pessoa escolheu no seletor, como no pré-exame, D1) vão em todo pedido, somadas às que a
  pessoa confirma numa pendência (um papel confirmado entra na lista `confirmed_roles`). Sem população associada, o indicador começa na quantidade: o motor
  recusa a densidade sem população.
- **Recusa (422):** a mensagem do motor aparece acima do gráfico, com "Voltar ao último gráfico calculado" e "Tentar
  novamente". Com uma pendência de premissa (`pendencia: {chave, opcoes, texto}`), a tela oferece as opções do motor, sem lista fixa;
  a escolhida vai em `options.premissas`.
- **Campos da resposta lidos:** os de sempre (`itens`, `dominios`, `referencia`, `notas`, `limitacoes`, `versao_base`,
  `chave_execucao`) e, por item, `tipo`, `tendencia`, `grupo`, `grupo_mapa`, `faixa`, `faixa_distancia`,
  `referencia_mais_proxima`, `condicoes`, `ordem` e `rotatividade`; no topo, `nivel`, `indicador`, `tendencia` (com
  `sem_classificacao_por_motivo`), `grupos`, `grupos_mapa`, `faixas`, `faixas_distancia`,
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
- Tendência e Análise espacial na visão dos estados esperam a escolha de municípios (os estados ficam para depois).
- Não há mapa no nível dos estados: os ladrilhos dos estados não foram aprovados.
- A rotatividade depende do motor aceitar planilhas com o identificador individual em `/api/painel`.
- O modo escuro segue o aparelho, sem botão para escolher (decisão de 23/10/2026).

## Testes

- **Modelo puro (Node):** `frontend/tests/painel.test.mjs`. Cobre a formatação pt-BR; o tamanho pela população; o eixo Y do
  indicador com o arranjo horizontal sem sobreposição; o modo leve preso à largura; a ausência de escala logarítmica
  automática; a análise espacial; o cometa vertical só com a variação do motor; as camadas de cor (classe, grupos, faixas,
  condições e ordem); a nomenclatura territorial (municípios e estados; distritos e províncias; comunas); a escolha de
  territórios (marcar e desmarcar unidades e grupos); a trilha e o título; as opções do pedido com as chaves do contrato; o que
  falta para pedir; a disponibilidade das famílias; o comando da conversa; a janela e as séries; a tabela em páginas; o CSV em
  precisão integral; o estado salvo; o contexto do gráfico; e a normalização da resposta no cliente. Desde 23/10/2026,
  `frontend/tests/areaDeAnalise.test.mjs` cobre os ajustes de cada análise (sem indicador na rotatividade; nos estados, os da
  distribuição), a disponibilidade do mapa com o motivo e o atalho, a pintura do mapa (a camada do gráfico, os quintis do motor
  ou a cor contínua da rotatividade, sem pergunta) e quando o pedido leva os quintis do mapa, a cor contínua e o tamanho, as
  ligações (até 30), o estado salvo com a vista (e o estado antigo sem ela), o aspecto "mapa" dos não avaliáveis, a vista
  pedida na conversa, a frase-resumo no cliente e no arquivo de método, os dados do mapa normalizados e, desde o pedido
  integrado de 23/10/2026, os nomes das abas, a abertura sem seleção, a apresentação de cada aba (base do Brasil, planilha de
  distritos e antes dos dados, sem códigos internos), o que significa cada classe da tendência, o motivo de cada unidade em
  palavras e a nota das sem classificação; desde 24/10/2026, o quadro de setas (um ponto por período, uma seta por avanço com o
  sinal do motor, a escala da linha, a lacuna sem ponto inventado e a ordem por classe). `frontend/tests/painel.test.mjs` cobre o
  campo Período: os últimos 4 períodos de cada ritmo (anual, semestral, base mensal, anos), o ritmo indisponível com o motivo e
  o ritmo de uma janela. O modo escuro tem `frontend/tests/modoEscuro.test.mjs`: a loja do esquema
  (o escuro só na tela e fora da impressão, o aviso síncrono no começo da impressão), as paletas do gráfico e do mapa por
  esquema (o claro igual ao de antes; no escuro, os valores validados, as rampas do escuro ao claro, o zero abaixo dos braços, o
  contraste), a pintura de cada camada no escuro, as variáveis de `styles.css` contra as paletas e contra as classes do
  Tailwind, o contraste dos textos, avisos, links e botões nas superfícies escuras e a ausência de cor fixa nas folhas de
  estilo.
- **Navegador:** `backend/tests/ui_area_de_analise.py`, nas suítes `bloco1` (catálogo sintético) e `base-versionada`
  (`ADT_BLOCK1_REAL=1`). Confere: E0 sem números nem pedido, com as cinco abas na mesma linha, nos nomes padronizados, e a
  apresentação de cada aba (a da tendência com as classes); a base sem seleção automática (nenhum pedido, a Seleção aberta e as
  abas das análises com a apresentação); E1 com os estados escolhidos na Seleção, a lista sem digitar, a instrução e a ação na
  dica; os ajustes dentro de cada análise (estados, Distribuição, Análise espacial e Tendência, com o mesmo indicador e a escala
  fora deles, na barra junto do desenho); a vista do desenho (o gráfico de início; nos estados e em Séries, o mapa
  desligado, com o motivo e o atalho); abrir o Amazonas pela bolha e pela lista; a frase-resumo do motor, com a competência da
  resposta (e fora da tela quando o indicador à vista não é o do cálculo); marcar e desmarcar, marcar e desmarcar todos; a busca
  como complemento (sem seleção, nada da seleção anterior à vista); voltar aos estados pela trilha; os quintis do mapa no pedido
  e a Quantidade (um pedido; a volta à densidade, da memória); a régua pelo teclado e pelo mouse; quartis; a análise espacial (o
  eixo X e o convite ao mapa na base versionada; a recusa e a pendência no catálogo sintético); a tendência nas três visões, com
  a nota das sem classificação e o motivo em palavras na dica, e, desde 24/10/2026, o campo Período (sem ritmo padrão; o anual
  desligado, com o motivo, no catálogo sintético; os últimos 4 períodos no pedido) e o quadro de setas (cada linha com a classe
  do motor, uma seta por velocidade do motor com o sinal dela e um ponto por observação; a ordem por classe; o filtro pela
  contagem; a escolha da linha; a dica no mouse e no foco); a rotatividade com a apresentação e o motivo, sem pedido;
  Condições (com o convite ao mapa), Ordenar, Comparar e Juntar; o CSV; os Detalhes; o modo
  leve com todos os municípios do Brasil (base versionada); e o celular (o painel dos ajustes na largura e a vista à vista). Cada
  bolha é conferida com a resposta do motor. O mapa em si (pontos, pintura, transição e lado a lado) tem roteiro próprio.
- **Navegador, mapa:** `backend/tests/ui_mapa.py`, na suíte `base-versionada`, confere o mapa contra as respostas do motor
  (detalhes em [MAPA_DA_PAGINA_UNICA.md](MAPA_DA_PAGINA_UNICA.md#testes)).
- **Navegador, modo escuro:** `backend/tests/ui_modo_escuro.py`, na suíte `bloco1`, com o navegador no escuro
  (`color_scheme="dark"`): o aviso de privacidade, a página com o banner, as entradas dos dados, as abas e a apresentação, a
  conversa, a base sem seleção, os estados e o Amazonas com fundo escuro e textos a 4,5:1 ou mais (pelo estilo calculado); as bolhas na série única do escuro (`#1ba3b5`), com o anel na superfície escura; a
  dica, o painel de uma função, os Detalhes e o diálogo de Nova sessão; o mapa (a superfície escura no canvas, as cores do
  escuro e a legenda dos quintis, ou, se o motor não entregar os pontos no catálogo sintético, só a área do mapa, com o
  registro na saída); e a
  impressão de volta ao claro. Tira capturas (`escuro-*.png`) para a conferência visual.
