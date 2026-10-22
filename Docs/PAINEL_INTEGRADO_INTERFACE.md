# Área de análise da página única

Decisões do responsável pelo produto de 22/10/2026: uma análise integrada, sem duas telas. A página é sempre o gráfico: famílias
de análise (Distribuição, Análise espacial, Tendência e Rotatividade), um seletor único de indicador, funções comuns a todas as
famílias e, abaixo, os Detalhes. O eixo Y é o indicador; o eixo X só aparece com a análise espacial. Este documento descreve a
área de análise. O motor e as rotas (`/api/painel` e `/api/painel/referencias`) estão em
[Painel integrado de bolhas](PAINEL_INTEGRADO.md); a estrutura da página (cabeçalho, fonte de dados, Histórico e conversa) fica
no README e nos documentos da interface e da conversa.

Código: `frontend/src/AreaDeAnalise.tsx` (a área e o estado), `PainelChart.tsx` (bolhas, dica e legendas),
`PainelTerritorios.tsx` (escolha dos territórios), `PainelSeries.tsx` (séries da tendência), `PainelRotatividade.tsx` (barras de
100%), `PainelGavetas.tsx` (painéis das funções), `PainelRuler.tsx` (régua), `PainelDetalhes.tsx` (tabela, não avaliáveis e
método), `painelModel.ts` (modelo puro), `painelApi.ts` (cliente do motor, único lugar com os nomes de campos) e `analise.css`.
A estrutura da página (`App.tsx`) monta a área direto, sem invólucro. No código e nos testes, os identificadores da área
começam por `analise-` (`data-testid="area-de-analise"`, `analise-...`).

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
  onEscolherFonte={tipo => ...}/>       // botões "Dados do Brasil" e "Enviar meus dados" da abertura
```

- **Fonte:** `null` é a abertura (E0). A troca de fonte (outra versão, outra planilha) recomeça a área. "Nova análise" pode
  remontar a área (`key`) para voltar a E1 com os mesmos dados.
- **Contexto (`onContexto`):** família, indicador, nível, universo, as unidades à vista (`idsNaTela`), competência, janela,
  referência e o título. Só é chamado quando algo muda.
- **Histórico (`onSalvar` e `restaurar`):** cada cálculo entrega `{titulo, definicao, resposta, quando}`. A `definicao` guarda o
  pedido, a família calculada, a chave do pedido e o estado visual (escala, régua e seleção); `restaurar` com esse objeto reabre
  o gráfico sem novo pedido ao motor.
- **Conversa (`pedido`):** os campos do objeto `painel` da conversa (família, indicador, nível, municípios, competência, janela,
  visão da tendência, referência, função, seleção, ordenação e condições). Cada campo é validado; o que não vale vira um aviso
  ("A competência … não existe nesta base"), nunca um erro. "Junte Manaus, Iranduba e Manacapuru" cria o conjunto; "compare
  Manaus e Tefé" pede a comparação; uma família indisponível fica de fora, com o motivo. Um pedido feito antes dos dados é
  aplicado quando a base fica pronta.
- **Nomenclatura territorial:** `fonte.rotulos` (`{unidade: {singular, plural}, grupo: {singular, plural} | null}`) ou os
  `rotulos` da resposta do motor. Na base do Brasil, município e estado; numa planilha, o que a pessoa confirmou (distrito,
  província…). Nenhum texto da área fixa "município" ou "estado": título, subtítulo, lista de territórios, trilha, dica, tabela,
  Detalhes, exportação e mensagens saem dos rótulos, com concordância simples ("Todas as províncias", "Ver os 12 distritos",
  "Cada bolha é uma comuna"). O gênero é o informado (`genero`) ou, sem ele, deduzido pela terminação.

## Estados da tela

| Estado | O que aparece |
|---|---|
| E0, antes dos dados | Moldura limpa, sem números nem bolhas de exemplo: "Escolha os dados para começar", com "Dados do Brasil" e "Enviar meus dados". As famílias ficam visíveis; clicar registra a intenção ("Você escolheu Tendência. Agora escolha os dados."). Título: "Diagnóstico territorial da força de trabalho em saúde". |
| E1, base do Brasil escolhida | Os estados em bolhas (`nivel: "estados"`), com a linha de contexto do Brasil, a instrução "Clique num estado para ver os municípios dele" e a lista de territórios ao lado. Nunca os 5.570 municípios de início. Numa planilha, o gráfico começa limpo, com a instrução de marcar unidades na lista. |
| E2, unidades na Distribuição | As bolhas das unidades escolhidas no eixo do indicador. |
| E3, outra família | Análise espacial, Tendência ou Rotatividade. |
| E4, função em uso | Um painel lateral aberto (no celular, sobe da base da tela). |

O estado vai em `data-estado` da área.

## Escolha dos territórios

Pedido do responsável (22/10/2026): a escolha precisa ser visível e didática, sem adivinhar onde clicar e sem depender de
digitar o nome de um município. A lista fica sempre à vista: na tela larga, numa coluna ao lado do gráfico; no celular, logo
abaixo dele.

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
- **Planilhas:** com coluna-mãe, a lista dos grupos, cada um com "Ver as N <unidades>" e as caixas das unidades, como os
  estados; sem coluna-mãe, a lista das unidades em ordem alfabética, com as caixas. Não há bolhas de grupo nas planilhas
  (`disponibilidade.grupos` do motor). No pedido, `base.municipios.estados` leva os valores do grupo e `ids`, `code:<código>` ou
  `name:<nome>`.
- **Abertura da planilha:** sem estados nem bolhas de grupo, a planilha abre com todas as unidades marcadas, e a lista fica à
  vista para restringir (na base do Brasil, a porta de entrada são os estados).
- **Sem unidades marcadas,** nada é pedido ao motor, e o gráfico pede a escolha.

## Famílias e opções

O seletor **Indicador** (Densidade ou Quantidade) vale em todas as famílias e não muda ao trocar de família. A **Competência**
vale na Distribuição e na Análise espacial (a mais recente, dita no título). A **escala** é linear, a partir do zero; a
logarítmica fica só por escolha da pessoa e só com todos os valores positivos (Parte 13, L1994). A escala logarítmica
automática de 22/10/2026 saiu.

- **Distribuição** (base, sempre ativa): grupos por posição (nenhum, quartis, quintis ou decis; CAP-DIS-02) ou faixas digitadas
  pela pessoa (CAP-DIS-03, limites como "0; 1; 2; 5"). O grupo e a faixa de cada bolha, os cortes e as contagens vêm do motor.
  Até cinco grupos ganham cor; nos decis, só as linhas de corte.
- **Análise espacial:** acrescenta o eixo X, a distância em linha reta (km) até a referência. A referência sai por critério
  (densidade, quantidade ou população, do maior para o menor ou o contrário, na ordem do motor, com "Usar o primeiro" e a
  escolha no empate), pelo nome ou pelos membros de um conjunto; com vários membros, a distância vai até o mais próximo, e a dica
  diz qual é (com os empates). Faixas de distância opcionais (CAP-ESP-03). A nota TPL-11 aparece sempre junto. Nos estados, a
  família espera a escolha de municípios (os estados não têm coordenadas). A disponibilidade vem do motor
  (`disponibilidade.espacial`): numa planilha sem coordenadas ou sem um referencial aceito (SIRGAS 2000 ou WGS 84), a aba fica
  desabilitada, com o motivo do motor; quando o motor pede a escolha do referencial, a tela mostra as opções que ele mandar.
- **Tendência:** a janela é escolha da pessoa (decisão 5a), com os atalhos "Últimos 4 junhos", "Série anual de junho" e "Todas
  as competências", ou as competências marcadas uma a uma. A visão é só estado visual (trocar não pede nada novo):
  - **Mudança:** entre a primeira e a última competência da janela (CAP-TMP-01), o cometa e a cor divergente contínua: azul é
    aumento, laranja é redução, cinza é sem mudança (V-05; nunca "crescimento"). "Primeira" e "Última" alternam as posições;
    "Reproduzir" desliza as bolhas da primeira à última (com movimento reduzido ou no modo leve, o botão vira "Ir para a
    última", sem animação).
  - **Classes:** CAP-TEN-01 na janela (pelo menos quatro competências). A bolha fica no valor da última competência, com o
    cometa desde a primeira, e a cor é a família da classe (crescimento azul, declínio laranja, sem classificação verde-água;
    não avaliável vazada). Aceleração e desaceleração ficam no rótulo, na dica e no filtro. Acima do gráfico, a contagem por
    classe do motor, que também filtra.
  - **Séries:** linhas por competência (no tempo real entre elas), até 12 unidades escolhidas (na tabela, nas bolhas ou "os de
    uma classe"), com pequenos múltiplos na mesma escala acima de 4. Um ponto por observação do motor; lacunas não são ligadas e
    não há linha ajustada. As velocidades do motor da unidade em foco aparecem em barras.
  - Com menos de quatro competências, Classes e Séries ficam indisponíveis, com o texto do catálogo ("A análise de tendência
    exige quatro observações válidas.").
- **Rotatividade:** só com dados enviados que tenham o identificador individual (CAP-ROT-01). Com a base do Brasil, a aba fica
  desabilitada, com o motivo e "Enviar meus dados"; o motivo do motor (`disponibilidade`) vale quando vem. O desenho são barras
  de 100%: permanência e saída da coorte inicial, com as contagens e os percentuais do motor; "da coorte inicial" vai em todo
  rótulo. A pessoa escolhe os períodos inicial e final.

## Eixos, marcas e cores

- **Eixo único (Distribuição, Tendência e estados):** Y é o indicador. As bolhas se espalham na horizontal só como arranjo, para
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
  contagem e a tabela dão o valor por outro caminho.
- **Símbolos:** anel escuro no conjunto ("soma das contagens dos componentes, com possível dupla contagem"), mira na referência,
  bolha vazada tracejada quando a camada de cor não tem valor (o motivo vai para Não avaliáveis).
- **Rótulos diretos seletivos:** siglas dos estados, itens destacados, conjuntos, referência, os N primeiros da ordenação (até 12)
  e a bolha sob o mouse ou em foco.
- **Estados e municípios** nunca no mesmo eixo nem somados; na visão dos estados, Juntar fica desligado.
- **Modo leve:** acima de 400 bolhas, uma camada de círculos simples que não muda ao passar o mouse; só as bolhas em destaque
  ganham o desenho completo. A régua só esconde; as posições não mudam. Sem animação. A tabela mostra 100 linhas por vez.

## Funções

Uma barra comum a todas as famílias; cada função abre um painel estreito ao lado do gráfico (por cima da parte direita do gráfico
entre 1.024 e 1.359 px; na base da tela abaixo de 1.024 px). No celular, as funções ficam no botão "Ferramentas".

| Função | O que faz | Pedido ao motor |
|---|---|---|
| Territórios | Leva à lista de territórios | Cada marcação pede de novo |
| Régua | Mostra só o que fica entre dois valores do indicador; só esconde (RQ-REP-06) | Nenhum |
| Condições | Separa quem atende a todas as condições, quem não atende e quem não tem dado (CAP-SUB-01, combinação "e"), com as contagens do motor; "Mostrar só quem atende" é filtro visual | `condicoes` |
| Ordenar | Ordem e posições do motor, empates na mesma posição, os N primeiros (CAP-SUB-02 e CAP-SUB-03) | `ordenar` |
| Comparar | 2 ou 3 itens lado a lado, com maior, menor e diferença do motor (CAP-CMP-01) | `comparar` |
| Juntar | As unidades escolhidas viram uma bolha (CAP-AGR-01), com a soma das contagens dos componentes e possível dupla contagem (RQ-REP-14) | `conjuntos` |
| Exportar | CSV com todos os itens do resultado, em precisão integral, com a avaliabilidade e o motivo; Imprimir / PDF; método e parâmetros em texto | Nenhum |

A seleção (clique ou Enter nas bolhas, ou a caixa na tabela) esmaece os demais; Comparar e Juntar agem sobre ela.

## Título e Detalhes

- **Título dinâmico:** "Densidade de médicos nos municípios do Amazonas · junho de 2024"; "Densidade de médicos nos estados ·
  junho de 2024"; "Densidade de médicos e distância até MANAUS (AM) · Amazonas · junho de 2024"; "Tendência da densidade de
  médicos · Amazonas · junho de 2021 a junho de 2024". "Médicos" sai da categoria MEDICINA; com outra, "profissionais de
  <categoria>". Subtítulo: "Cada bolha é um município. O tamanho mostra a população."
- **Detalhes,** abaixo do gráfico, em abas: Tabela (os mesmos itens do gráfico, na ordem do código territorial, com 100 linhas
  por página; clicar num cabeçalho só reordena, sem criar posições), Não avaliáveis (por aspecto, com o motivo do motor:
  indicador, distância, variação, tendência, condições e coorte) e Método e procedência (notas, limitações, origem da
  referência, TPL-11, janela, versão da base e chave de execução). Na impressão, as três partes aparecem.

## Pedido ao motor e estado visual

O cliente (`painelApi.ts`) monta o formulário de `/api/painel` (base do Brasil com `dataset=brazil`; planilha com `file`, a aba
e o mapeamento confirmado), envia as opções com as chaves do contrato e normaliza a resposta. Mudar universo, competência,
categoria, referência, janela, grupos, faixas, condições, ordenação, comparação, conjuntos ou premissas pede de novo
(com 150 ms de espera e o pedido anterior cancelado); o gráfico anterior fica à vista, mais claro, enquanto o motor responde. As
últimas seis respostas ficam na memória da tela: voltar a um estado já calculado não pede de novo. Indicador (sem grupos, faixas
ou tendência), escala, régua, seleção, visão da tendência, primeira ou última competência, filtros e páginas são só estado
visual.

- **Opções enviadas:** `nivel` (`"estados"` ou `"municipios"`) e `indicador` (`"densidade"` ou `"quantidade"`) em todo
  pedido, porque sem `nivel` o motor responde no contrato de 21/10, que não conhece as chaves da página única; `base`,
  `conjuntos`, `referencia`, `faixas_distancia`, `competencia_inicial` e `tendencia: {competencias}` (com quatro competências
  ou mais) conforme a família; `grupos` ou `faixas` na Distribuição; `condicoes`, `ordenar` e `comparar` quando pedidos;
  `rotatividade: {inicial, final}`; `premissas`, só nas planilhas (na base do Brasil, o motor recusa).
- **Planilhas:** as premissas escolhidas no painel Colunas (unidade de contagem, referencial, separador decimal) vão em todo
  pedido, somadas às que a pessoa confirma numa pendência. Sem população associada, o indicador começa na quantidade: o motor
  recusa a densidade sem população.
- **Recusa (422):** a mensagem do motor aparece acima do gráfico, com "Voltar ao último gráfico calculado" e "Tentar
  novamente". Com uma pendência de premissa (`pendencia: {chave, opcoes, texto}`), a tela oferece as opções do motor, sem lista fixa;
  a escolhida vai em `options.premissas`.
- **Campos da resposta lidos:** os de sempre (`itens`, `dominios`, `referencia`, `notas`, `limitacoes`, `versao_base`,
  `chave_execucao`) e, por item, `tipo`, `tendencia`, `grupo`, `faixa`, `faixa_distancia`, `referencia_mais_proxima`,
  `condicoes`, `ordem` e `rotatividade`; no topo, `nivel`, `tendencia`, `grupos`, `faixas`, `faixas_distancia`, `condicoes`,
  `ordenacao`, `comparacao`, `contexto.brasil`, `disponibilidade`, `sessao` e `rotulos`. Campo ausente vira vazio: a resposta de
  antes continua legível. Nos formatos do motor (`Docs/PAINEL_INTEGRADO.md`):
  - `referencia_mais_proxima.empate` lista todos os membros à mesma menor distância; cada um aparece uma vez;
  - `condicoes.por_condicao` traz o `estado` de cada condição, na ordem de `condicoes.definicao` do topo, de onde vem o texto;
  - os limites das faixas vêm em texto decimal com ponto, sem arredondar;
  - na comparação, `maior` e `menor` são listas de ids, com os valores em `itens`, e a diferença de dois itens vem em
    `{a, b, relacao, diferenca}`;
  - o motivo da tendência aparece em texto, com o código entre parênteses ("Mudança de direção (MUDANCA_DE_DIRECAO)").

## Acessibilidade

- **Teclado:** famílias e abas dos Detalhes com setas, Home e End; o gráfico é uma parada de tabulação, e as setas percorrem as
  bolhas (de cima para baixo no eixo único; da esquerda para a direita com a distância), Enter ou Espaço destacam (ou abrem os
  municípios do estado), Esc fecha a dica; Esc fecha o painel lateral e devolve o foco ao botão que o abriu.
- **Dica no foco** igual à do mouse; cada bolha é um botão com um rótulo com os valores; a régua tem dois `role="slider"`.
- **Equivalentes em texto:** a tabela, os não avaliáveis, as legendas com as contagens e as notas. A identidade nunca depende
  só da cor.
- **Movimento:** com `prefers-reduced-motion`, nenhuma transição nem animação.
- **Celular:** famílias em abas roláveis, funções no botão "Ferramentas", painel na base da tela e nenhuma rolagem horizontal.

## Limitações desta entrega e próximos passos

- A conversa e o Histórico dependem da estrutura da página (frente B1); a área entrega o contexto, o estado salvo e aplica o
  pedido.
- Tendência e Análise espacial na visão dos estados esperam a escolha de municípios (os estados ficam para depois).
- A rotatividade depende do motor aceitar planilhas com o identificador individual em `/api/painel`.
- A aplicação é toda clara; não há modo escuro.

## Testes

- **Modelo puro (Node):** `frontend/tests/painel.test.mjs`. Cobre a formatação pt-BR; o tamanho pela população; o eixo Y do
  indicador com o arranjo horizontal sem sobreposição; o modo leve preso à largura; a ausência de escala logarítmica
  automática; a análise espacial; o cometa vertical só com a variação do motor; as camadas de cor (classe, grupos, faixas,
  condições e ordem); a nomenclatura territorial (municípios e estados; distritos e províncias; comunas); a escolha de
  territórios (marcar e desmarcar unidades e grupos); a trilha e o título; as opções do pedido com as chaves do contrato; o que
  falta para pedir; a disponibilidade das famílias; o comando da conversa; a janela e as séries; a tabela em páginas; o CSV em
  precisão integral; o estado salvo; o contexto do gráfico; e a normalização da resposta no cliente.
- **Navegador:** `backend/tests/ui_area_de_analise.py`, nas suítes `bloco1` (catálogo sintético) e `base-versionada`
  (`ADT_BLOCK1_REAL=1`). Confere: E0 sem números nem pedido; E1 com os estados em bolhas, a lista sem digitar, a instrução e a
  ação na dica; abrir o Amazonas pela bolha e pela lista; marcar e desmarcar, marcar e desmarcar todos; a busca como
  complemento; voltar aos estados pela trilha; Quantidade sem pedido; a régua pelo teclado e pelo mouse; quartis; a análise
  espacial (o eixo X na base versionada; a recusa e a pendência no catálogo sintético); a tendência nas três visões; a
  rotatividade desabilitada; Condições, Ordenar, Comparar e Juntar; o CSV; os Detalhes; o modo leve com todos os municípios do
  Brasil (base versionada); e o celular. Cada bolha é conferida com a resposta do motor.
