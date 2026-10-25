# Mapa da página única

O mapa saiu do produto com as telas clássicas em 22/10/2026 e volta, pelas decisões do responsável pelo produto de 23/10/2026,
como **segunda vista do gráfico de bolhas** da [área de análise](PAINEL_INTEGRADO_INTERFACE.md). É a mesma análise vista de
outro jeito: seleção, régua, condições, comparação, conjuntos, dica, tabela e título são os mesmos nas duas vistas. O mapa só
desenha o que o motor devolveu; nada é calculado na tela.

Código:

- `frontend/src/MapaAnalise.tsx`: o mapa (canvas), a dica, as legendas (com a dos quintis), a busca e o mapinha do canto;
- `frontend/src/mapaModel.ts`: modelo puro do desenho (projeção, enquadramento, tamanho, cor, marcas da legenda, nomes, alvo do
  clique, ligações, mapinha e transição). Não importa nenhum outro módulo em tempo de execução, para os testes em Node;
- `frontend/src/MiniMapa.tsx`: o mapinha (SVG);
- `frontend/src/transicaoVistas.ts`: a transição entre o gráfico e o mapa;
- `frontend/src/mapa.css`: os estilos;
- `frontend/src/mapaContrato.ts`: os tipos combinados entre a área, o mapa, o gráfico e o motor, com os seletores de teste.

O mapa antigo (`TerritoryMap.tsx`, no histórico até `748b3f9`) foi reaproveitado: canvas sem serviço externo nem chave de API,
projeção equirretangular só para desenhar, pontos em lotes, zoom, arrasto, pinça, duplo clique, teclado, alvo do clique maior
que o ponto e nomes que não se cobrem. As regras dele estão nas seções 4, 5 e 13 de
[Mapas e visualizações](BLOCO3_MAPAS_VISUALIZACOES.md), que ficam como histórico.

## Para que serve

O gráfico responde "quanto". O mapa responde "onde": onde ficam os municípios de uma faixa, quem atende às condições (os vazios
assistenciais aparecem como áreas sem pontos que atendem), onde estão a referência e os municípios marcados. O mapa **não mede
distância**: a posição serve só para o desenho. As distâncias da análise espacial são as do motor (geodésicas, em linha reta).

## Como a área monta o mapa

```ts
<MapaAnalise ref={mapaRef}
  itens={PainelItem[]}            // os mesmos itens desenháveis do gráfico; estados não chegam ao mapa
  dentro={Set<string>}             // ids dentro da régua e dos filtros; os demais esmaecem
  dados={{ competencia, referencial, pontos: Map<id, [lat, lon]>, semCoordenada }}   // do motor (POST /api/painel/mapa)
  indicador pintura={"camada" | "quintis" | "continua"} pintar valorContinuo rotuloContinuo dominio escala
  tamanho={{ valor, rotulo, maximo }} contextoBrasil legendaCor
  selecionados referencias ligacoes extraDoRotulo dicaDe rotulos brasil
  ativoExterno onAtivo onAlternar carregando/>
```

`mapaRef.current.posicoes()` devolve a posição de cada ponto na janela (para a transição) e `verTudo()` volta ao enquadramento
inicial. Os tipos completos estão em `mapaContrato.ts`.

## O que cada codificação mostra

| Codificação | O que mostra |
|---|---|
| Posição | A sede do município (IBGE) na base do Brasil, ou a coordenada da planilha, como o motor autorizou para a competência. A nota `mapa-nota` diz isso pela fonte em uso ("Cada ponto é a sede do município (IBGE) na base do Brasil." ou "Cada ponto é a coordenada do distrito informada na planilha.", com os rótulos da planilha) e que a posição é só para o desenho. Projeção equirretangular (longitude × cosseno da latitude média), só para posicionar. |
| Tamanho | Área proporcional ao valor de tamanho que a área escolhe (população na densidade, quantidade na quantidade). Raio máximo de 16 px, menor que o do gráfico, e mínimo visível de 2,5 px; os maiores ficam atrás e os menores na frente, com um anel fino da cor da superfície separando os sobrepostos. A legenda `mapa-legenda-tamanho` mostra três valores redondos com o mesmo raio do desenho. O tamanho não muda com o zoom: a legenda vale sempre. |
| Cor, pintura "camada" | A mesma pintura do gráfico (grupos, faixas, condições, ordenação, classes ou variação), pela função `pintar` da área, com a mesma legenda (`legendaCor`). Valor não avaliável: anel tracejado cinza sobre a superfície, nunca preenchido como zero. Pintura apagada (não atende, fora dos primeiros): mais clara. |
| Cor, pintura "quintis" | Sem cor própria da análise (a distribuição sem grupos nem faixas e a análise espacial, sem condições nem ordenação), os 5 grupos iguais (quintis) do indicador que o motor devolve junto com a análise (`grupos_mapa` no topo e `grupo_mapa` em cada item; CAP-DIS-02), na rampa ordinal dos grupos do gráfico. A legenda (`mapa-legenda`, `data-tipo="quintis"`) diz "Cores do mapa: 5 grupos iguais (quintis) …, calculados pelo motor" e lista cada grupo com o rótulo e a contagem do motor (`mapa-quintil`). Sem grupo (sem valor do indicador): anel tracejado. Sem os grupos na resposta, a cor única do gráfico. |
| Cor, pintura "continua" | Só na rotatividade: a permanência da coorte inicial, de 0 a 100%, numa rampa sequencial de um tom (azul, do claro ao escuro), linear. A legenda (`mapa-legenda`, `data-tipo="continua"`) traz o mínimo e o máximo, marcas de leitura (não são limites de classe) e o aviso "A cor não é classe nem limiar". |
| Valor do Brasil | Só uma marca tracejada na legenda contínua, com o texto "referência de contexto; não classifica". O mapa não pinta ninguém "acima" ou "abaixo" do Brasil. |
| Esmaecido | Item fora da régua ou dos filtros visuais: no mesmo lugar e no mesmo tamanho, bem claro e sem interação. Nunca some. |
| Fundo | As demais unidades da fonte (os demais municípios do Brasil), em quadradinhos cinza bem claros, sem interação: dão o formato do território. |
| Anel escuro | Membro de um conjunto. O conjunto não tem ponto: o valor dele é a soma das contagens dos componentes, com possível dupla contagem (RQ-REP-14). A dica do membro diz de qual conjunto ele faz parte. |
| Mira | Com a referência pelos membros (vinda da conversa pelo nome), o membro da referência da análise espacial (distância 0), a mesma mira do gráfico. Com o território de referência por elegibilidade (24/10/2026), os territórios que ficaram como referência de algum município (`referencia.membros` da resposta), também os de fora da seleção, pelo ponto do fundo: todos, até 30; com mais, só os dos municípios marcados, os mesmos das ligações. A legenda de símbolos diz "mira: território de referência" (`mapa-simbolos`). Os elegíveis não entram como itens do gráfico. |
| Linha tracejada | Ligação ilustrativa, não é trajeto: de cada município marcado (até 30) ao território de referência dele (o mais próximo ou o mais distante dos elegíveis, desde 24/10/2026) ou, com a referência pelos membros, ao membro mais próximo, como o motor indicou (com os empates). O aviso `mapa-ligacoes` diz isso. Não há círculos de "X km". |
| Anéis de seleção | Marcado: anel escuro junto ao ponto. Sob o mouse, em foco, tocado ou destacado pelo gráfico ao lado: anel externo. Foco pelo teclado: também o contorno de foco da página. |
| Nomes | Dos marcados, dos que têm texto extra da área (por exemplo "1º" na ordenação) e, com até 12 pontos no resultado, de todos. Com zoom, mais nomes aparecem, sem cobrir uns aos outros, os pontos nomeados, os botões nem o mapinha; só o texto se move, nunca o ponto. |

## Decisões de 23/10/2026

1. **Pintura sem pergunta** (pedido do responsável, 23/10/2026, no lugar da pergunta "Como pintar o mapa?", que oferecia
   quintis, faixas, cor contínua ou condições): sem cor própria da análise, o mapa pinta os 5 grupos iguais (quintis) do motor,
   pelo método existente (CAP-DIS-02), com a legenda. Os quintis vêm com a análise, no mesmo pedido (`grupos_mapa`), para a
   troca de vista continuar sem pedir cálculo (RQ-REP-06). Os grupos e as faixas escolhidos na Análise de Distribuição, as
   condições, a ordenação e as classes da tendência continuam pintando o mapa como o gráfico.
2. **Régua no mapa:** esmaece o que fica fora, em vez de esconder.
3. **Escala da cor:** a cor contínua ficou só na rotatividade (0 a 100%), linear; o mapa não tem escala própria. A logarítmica
   nunca entra sozinha (Parte 13: mudança automática de escala é proibida).
4. **Faixas de distância** não viram cor no mapa: a RQ-REP-02 não lista CAP-ESP-03 entre as classes que podem colorir. Elas
   continuam como linhas no gráfico e na tabela.
5. **Enquadramento inicial com contexto** (23/10/2026): o retângulo dos pontos da análise ganha uma margem de 25% do vão de
   cada lado e não fica menor que um quarto da extensão de todos os pontos da fonte (o desenho do país ou da planilha, ao
   fundo), nem maior que ela. O mapa abre com a geografia reconhecível em volta dos pontos, adaptado à seleção e sem escala fixa
   do Brasil; com todos os pontos escolhidos, é a vista da fonte inteira. "Ver tudo" volta a ele, e o zoom continua livre.

## Navegação

- **Botões** (canto superior direito): `mapa-ampliar`, `mapa-reduzir` e `mapa-ver-tudo` (volta ao enquadramento inicial).
- **Mouse:** arrastar move o mapa; Ctrl ou ⌘ com a roda (ou só a roda, com o mapa em foco) amplia e reduz em torno do cursor;
  duplo clique amplia; passar sobre um ponto mostra a dica; clicar marca ou desmarca, como na bolha. O alvo do clique é maior
  que o ponto: 12 px no mouse e 18 px no toque.
- **Toque:** arrastar com um dedo, pinça com dois; tocar num ponto marca e mostra a dica.
- **Teclado,** com o mapa em foco: as setas movem a vista; Shift e as setas vão ao ponto vizinho naquela direção (a vista
  acompanha); Enter ou espaço marcam o ponto em foco; + e − ampliam e reduzem; 0 ou Home voltam ao enquadramento inicial; Esc
  fecha a dica. Ao focar o mapa pelo teclado, o ponto mais perto do centro fica em foco.
- **Mapinha:** com zoom além do inicial, o mapinha (`minimapa`) aparece no canto inferior esquerdo com o retângulo da área à
  vista.
- **Busca:** "Achar um município no mapa" (`mapa-busca`) centra o mapa no ponto escolhido e mostra a dica dele, sem marcar nada.
- **A vista volta como foi deixada:** o zoom e o deslocamento ficam guardados para cada conjunto de itens durante a sessão,
  mesmo quando o mapa sai da tela; outra análise, com outros itens, começa no enquadramento inicial.

Navegar, marcar e trocar de vista são estado visual: não iniciam análise (RQ-REP-06).

## Transição entre as vistas

`transicaoVistas.ts` lê a posição de cada bolha do gráfico (`posicoesDoGrafico`, a partir de `[data-testid="analise-bolha"]`) e
anima, numa camada de canvas fixa por cima da área do desenho, cada bolha até o ponto do mesmo item no mapa (ou o contrário), em
cerca de `duracaoMs`, com suavização. Os itens que só existem num lado somem ou aparecem aos poucos. A camada cobre a vista nova
com a superfície e se desfaz no fim, revelando-a no mesmo lugar dos pontos. Com movimento reduzido (preferência do sistema), com
mais de 1.500 pontos num dos lados (`LIMITE_TRANSICAO`) ou com a área oculta, a troca é direta. A camada é removida ao terminar.

## O gráfico com o mapa

O gráfico (`PainelChart.tsx`) ganhou três propriedades opcionais (`GraficoComMapaProps`); sem elas, nada muda:

- `pontosDoMapa`: a dica (`analise-dica`) da bolha de uma unidade com ponto mostra o mapinha com o destaque ("onde fica?");
  estados e conjuntos não têm ponto;
- `ativoExterno`: a bolha do item sob o mouse no mapa ganha o anel (gráfico e mapa lado a lado);
- `onAtivo`: avisa a área quando a bolha ativa (mouse ou foco) muda.

## Onde o mapa não se aplica

- **Estados:** não têm ponto e não chegam ao mapa. A área desliga a vista "Mapa" com o motivo e oferece ver os municípios.
- **Planilha sem latitude e longitude** (ou sem referencial autorizado): sem geometria autorizada, não há mapa (RQ-REP-07); a
  tabela continua.
- **Unidade sem coordenada válida:** fica fora do mapa e aparece em Não avaliáveis, com o motivo do motor; a nota do mapa avisa.
- **Visão Série temporal** (a antiga visão Séries): a área desliga a vista "Mapa" com o motivo ("Na visão Série temporal, cada
  município é uma linha no tempo: o mapa fica com Tendência e Trajetória."). Ao abrir a Análise de Tendência, a vista é o
  gráfico, e o mapa continua como alternativa nas visões Tendência e Trajetória. Na rotatividade, o mapa fica desligado só sem latitude e
  longitude na planilha (com coordenadas, ele pinta a permanência da coorte inicial).

## Regras da SPEC respeitadas

- **Parte 13:** só transformações admitidas: mapeamento visual contínuo de valores existentes, formatação de apresentação e
  rótulos de metadado autorizado. Nenhuma quebra em quantis, intervalos ou classes, nenhum total, média, contagem, proporção,
  posição ou ranking criado na tela, nenhuma mudança automática de escala.
- **RQ-REP-02:** as classes que colorem os pontos vêm de capacidades do motor (grupos de CAP-DIS-02, também os quintis do
  mapa, `grupos_mapa`; faixas de CAP-DIS-03, condições de CAP-SUB-01, classes de CAP-TEN-01), pela mesma pintura do gráfico. A
  cor contínua da permanência não é classe, e a legenda diz isso. As faixas de distância (CAP-ESP-03) não viram cor.
- **RQ-REP-04:** não avaliável é um anel tracejado, distinto de zero, com legenda.
- **RQ-REP-06:** controles do mapa e troca de vista só mudam o estado visual.
- **RQ-REP-07:** o mapa só existe com geometria autorizada (os pontos do motor).
- **RQ-REP-09:** o mapa traz o que precisa para ser lido sozinho (nota do ponto, legendas, avisos) e não calcula nada: tamanhos,
  cores e posições saem dos valores do motor.
- **RQ-REP-14:** conjuntos rotulados como soma das contagens dos componentes, com possível dupla contagem.

## Acessibilidade

- O mapa é focável, com instruções no rótulo; o ponto em foco tem anel, contorno de foco e a dica, e a descrição dele vai para
  uma região lida pelos leitores de tela (`mapa-foco`).
- A tabela dos Detalhes continua sendo o caminho acessível para todos os valores.
- As legendas são regiões com rótulo; os controles têm nomes ("Ampliar o mapa", "Reduzir o mapa", "Ver tudo: volta ao
  enquadramento inicial").
- Nenhum significado depende só da cor: vazado é tracejado, a referência tem mira, o conjunto tem anel, e a dica e a tabela
  trazem os valores.
- Com movimento reduzido, a transição entre as vistas é direta.
- Na impressão, sai a vista que está na tela, sem os controles, a busca e a dica.

## Cores

As cores do mapa e do mapinha estão em `MAPA_CORES` (`mapaModel.ts`, modo claro) e `MAPA_CORES_ESCURO` (modo escuro), com as
mesmas chaves; `coresDoMapa(esquema)` escolhe o objeto pelo esquema em uso, e o componente o passa ao canvas e a `mapa.css`
como variáveis `--mapa-*`. A superfície e as tintas são as da paleta do gráfico. A rampa contínua do claro (`RAMPA_CONTINUA`,
`#86b6ef` → `#104281`, os passos 250 a 650 do azul) foi conferida no validador da skill de visualização
(`validate_palette.js --mode light --ordinal`): L monótono, passos de pelo menos 0,06, ponta clara a 2,06:1 da superfície e um
só matiz. As cores das camadas são as do gráfico, no mesmo esquema.

## Modo escuro

O mapa segue o esquema de cor do aparelho, como a página (decisão de 23/10/2026; sem botão), e a impressão é sempre clara. A
troca de esquema redesenha o canvas na hora; no começo da impressão, o mapa é redesenhado no claro antes de a página ir para a
impressão. O mapinha e a camada da transição usam as mesmas cores.

| Chave | Claro | Escuro | Por quê |
|---|---|---|---|
| `superficie` | `#fcfcfb` | `#1a1a19` | a superfície do gráfico no escuro (tabela "Chart chrome & ink" da skill) |
| `tinta`, `tinta2`, `muda` | `#0b0b0b`, `#52514e`, `#898781` | `#f0efec`, `#c3c2b7`, `#898781` | 15,2:1, 9,7:1 e 4,85:1 da superfície |
| `neutro` (pontos sem camada de cor) | `#008b9e` | `#1ba3b5` | a série única do escuro (validador: PASS) |
| `naoAvaliavel` (anel tracejado) | `#898781` | `#898781` | 4,85:1 da superfície escura |
| `fundo` (demais unidades) | `#d9d8d1` (1,39:1) | `#383835` (1,48:1) | recessivo como no claro |
| `esmaecido` e borda | `#e1e0d9` e `#d9d8d1` | `#2c2c2a` e `#383835` | fora da régua: bem perto da superfície, sem sumir |
| `miniPontos` | `#c3c2b7` (1,75:1) | `#45443f` (1,78:1) | o formato do Brasil no mapinha |
| `eixo`, `borda` | `#c3c2b7`, `#dfe7ed` | `#383835`, `#2e2e2b` | linhas finas da legenda e moldura |
| `painel` (controles, dica) | `#ffffff` | `#232321` | a superfície elevada da página no escuro |
| `controleTexto`, `textoApoio` | `#0e2840`, `#52606d` | `#e6e5df`, `#c3c2b7` | 12,5:1 e 8,8:1 sobre o painel |
| `controleBorda`, `controleRealce` | `#c9d8e2`, `#eef7f8` | `#45453f`, `#142d2e` | bordas e passagem do mouse |
| `destaqueTexto`, `destaqueFundo` | `#0c6b74`, `#effafb` | `#6fcbd2`, `#142d2e` | sem uso na tela desde 23/10/2026 (eram da opção recomendada da pergunta); continuam na paleta, a 7,7:1 |
| `foco` | `#3bb5be` | `#3bb5be` | 7,1:1 da superfície escura |
| `sombra` | `rgba(9, 37, 60, 0.12)` | `rgba(0, 0, 0, 0.5)` | sombras visíveis no escuro |

**Rampa contínua no escuro** (`RAMPA_CONTINUA_ESCURA`, por `rampaContinua(esquema)`): a âncora vira, do escuro (menor valor) ao
claro (maior): `#184f95`, `#256abf`, `#3987e5`, `#6da7ec` e `#9ec5f4` (passos 600 a 200, sem ir além do 600 na ponta junto da
superfície). Validador (`--ordinal --mode dark --surface "#1a1a19"`): L monótono, passos de pelo menos 0,06, ponta escura a
2,15:1 da superfície e um só matiz (3°): PASS. É a mesma rampa dos grupos e faixas do gráfico no escuro, com 5 tons. A legenda
contínua mostra a rampa do esquema em uso, com as mesmas marcas.

## Gancho de teste e seletores

- `mapa-analise`, com `data-pintura` (`camada`, `quintis` ou `continua`), `data-pontos` (pontos do resultado desenhados,
  inclusive os esmaecidos), `data-contexto` (pontos de fundo), `data-esmaecidos`, `data-escala` (`linear` na cor contínua;
  `nenhuma` nas demais pinturas) e `data-esquema` (`claro` ou `escuro`).
- `mapa-canvas`, `mapa-dica` (com `data-id`), `mapa-foco`, `mapa-legenda` (`data-tipo` = camada | quintis | continua), com
  `mapa-legenda-quintis` e `mapa-quintil` (`data-chave` e `data-contagem`, do motor) nos quintis,
  `mapa-legenda-min`, `mapa-legenda-max`, `mapa-legenda-marca`, `mapa-legenda-brasil`, `mapa-legenda-aviso`,
  `mapa-legenda-tamanho` e `mapa-legenda-tamanho-item`, `mapa-ampliar`, `mapa-reduzir`, `mapa-ver-tudo`, `mapa-busca`,
  `mapa-nota`, `mapa-simbolos`, `mapa-ligacoes`, `mapa-vazio`; `minimapa` (com `minimapa-destaque` e `minimapa-moldura`);
  `transicao-vistas` (a camada da transição, enquanto existe).
- `window.__adtMapa`, atualizado a cada desenho: `{ pintura, escala, dominio, contexto, esmaecidos, brasil, vista, largura,
  altura, desenhos, ms, esquema, superficie, pontos }` (`esquema`: `claro` ou `escuro`; `superficie`: a cor pintada no canvas). `pontos` traz `{ id, x, y, r, cor, esmaecido, selecionado, vazada, apagada, naTela }` de cada
  ponto do resultado, com `x` e `y` em pixels relativos ao canvas. `ms` é o tempo do último desenho. Sai quando o mapa sai da
  tela.

## Testes

- Node: `frontend/tests/mapa.test.mjs` (modelo puro): projeção e enquadramento, o enquadramento inicial com contexto (margem,
  mínimo de um quarto da fonte, nunca mais que ela, proporcional a qualquer fonte), zoom, tamanho com área proporcional, cor
  contínua linear e logarítmica, sem log automático, marcas da legenda e do Brasil, cena (estados e conjuntos sem ponto, fundo,
  membros, sem coordenada; a pintura dos quintis igual à da camada), esmaecidos que nunca somem, vazados nunca como zero, alvo do
  clique, vizinho pelo teclado, nomes sem sobreposição, ligações, mapinha, transição e cores. `frontend/tests/modoEscuro.test.mjs`:
  as cores do mapa por esquema (as mesmas chaves, a superfície, as tintas e o neutro do gráfico no escuro, os textos a 4,5:1 ou
  mais, o fundo e os esmaecidos recessivos), a rampa contínua do escuro (do escuro ao claro) e a cena no escuro (vazado na
  superfície escura, quintis com a cor que a área entrega). `frontend/tests/areaDeAnalise.test.mjs`: quando a área pinta pelos
  quintis e quando o pedido os leva.
- Navegador: `backend/tests/ui_mapa.py`, na suíte `base-versionada` (job `ui-block1`), confere o mapa contra as respostas de
  `/api/painel` e de `/api/painel/mapa`: nos estados (escolhidos na Seleção, no nível Estados, porque a base abre sem seleção),
  o mapa desligado, com o motivo e o atalho; todos os municípios do Brasil, com os pontos do motor, o fundo e os quintis do
  motor sem pergunta (a mesma contagem por cor que o motor devolveu por grupo e a legenda com as contagens); o Amazonas (desde
  24/10/2026, marcado pela caixa do estado na Seleção, porque abrir a lista de um estado só mostra a lista) com os pontos já guardados, os
  quintis dele e o enquadramento com contexto (os pontos do estado só na parte central do mapa); os quintis escolhidos no
  gráfico, iguais aos do mapa;
  a régua, que esmaece sem esconder; a seleção pelo clique e a dica; o zoom, o mapinha do canto e "Ver tudo"; o mapinha na dica
  do gráfico; o convite depois das Condições; a análise espacial com o Território de referência (desde a segunda rodada de
  24/10/2026: os elegíveis do mesmo estado acima da mediana da população, a referência de cada município entre eles e nunca ele
  mesmo, as ligações até o território de referência e a mira dele na legenda de símbolos); o lado a lado em 1.700 px, sem legenda repetida;
  o Histórico, que reabre a análise no mapa sem recalcular; e o celular. O roteiro da área
  (`backend/tests/ui_area_de_analise.py`) confere a ligação do mapa à área: a vista desligada, com o motivo e o atalho, e os
  convites.
  O roteiro do modo escuro (`backend/tests/ui_modo_escuro.py`, suíte `bloco1`) abre o mapa com o navegador no escuro e confere a
  superfície escura no canvas (`getImageData`), `data-esquema`, o gancho de teste e a legenda dos quintis legível; se o motor
  não entregar os pontos no catálogo sintético, confere só a área do mapa e registra isso na saída.

## Limitações e pendências

- Sem limites oficiais de estados nem do Brasil: o formato vem dos próprios pontos (seção 4 de
  [Mapas e visualizações](BLOCO3_MAPAS_VISUALIZACOES.md)).
- Estados em ladrilhos: não foram aprovados (precisariam de um adendo à SPEC); nos estados, o mapa fica desligado, com o motivo
  e o atalho para os municípios. Com o Brasil como unidade (24/10/2026), também: "O Brasil, como unidade, não tem um ponto no
  mapa: cada ponto do mapa é um município.", sem atalho.
