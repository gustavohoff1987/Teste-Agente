# Bloco 3 — Mapas, visualizações avançadas e exploração visual integrada

Branch `feat/novos-blocos-incrementais`, a partir de `2d8f7a0` (fim da integração das coordenadas
oficiais do Bloco 2). Referências: Parte 13 da SPEC v1.2.4 (CAP-REP-01 a CAP-REP-06, CFG-REP,
RQ-REP-01 a RQ-REP-15) e os contratos de avaliabilidade, precisão, linhagem, privacidade e vigência
dos Blocos 1 e 2. **Este bloco não declara conformidade integral com a SPEC** (seção 15).

O Bloco 3 não cria operação analítica nem arquitetura analítica nova. O backend acrescenta aos
metadados de cada resultado um contrato compacto de apresentação, lido das próprias colunas do
resultado e da mesma geometria autorizada das análises espaciais; o frontend apenas representa esse
conteúdo. Nenhum número dos resultados muda por causa do bloco (seção 14).

Atualização de 15/10/2026: resultados com muitos territórios passam a ter barras com rolagem, séries paginadas e tabelas filtráveis; o mapa da versão Brasil governada usa configuração contextual de apresentação, descrita abaixo. As medições das seções 13 e 14 são históricas, anteriores a esses ajustes.

## 1. Situação das unidades

| Unidade | Conteúdo | Commit |
|---|---|---|
| U1 — contrato | `metadata.representacao` (indicadores, vínculo, série, geometria autorizada); testes sintéticos e reais | `5709d4a` |
| U2 — mapa | `TerritoryMap.tsx` (canvas), formatação RQ-REP-05 e paletas em `representation.ts` | `dfaf133` |
| U3/U4 — gráficos, painel, sincronização, histórico e exportações | `ResultWorkspace.tsx`, `ResultCharts.tsx`, integração em `App.tsx`, `CriteriaResults.tsx` e `DistributionResults.tsx`; jornada `ui_map_smoke.py` no CI | `5841f55` |
| Correção de roteiro anterior | corrida em `ui_block1_integration.py` (seção 14.3) | `22e1884` |
| U5 — regressão, desempenho e documentação | `bench_ui_map.py`, este documento e README | último commit da branch |

## 2. Arquitetura e bibliotecas

```
motor (resultado estruturado) ──► representation.payload() ──► metadata.representacao (versão 1)
                                     │  colunas do próprio resultado: rótulo, unidade, natureza
                                     │  geometria: territory_coordinates / nearest_inputs (regra espacial)
                                     ▼
ResultWorkspace (estado visual: aba, seleção, filtro, indicador) ──► TerritoryMap (canvas 2D)
                                                                 ├─► ResultCharts (Recharts)
                                                                 └─► tabelas existentes (CriteriaResults, DistributionResults, genérica)
```

- **Sem dependência nova.** Mapa em Canvas 2D nativo; gráficos com Recharts 2.15 e barras extensas em HTML com janela visual, sem biblioteca nova;
  ícones lucide-react, já presente. Nenhum serviço de mapas, tile, chave de API ou CDN: a jornada de
  navegador falha se a página fizer qualquer requisição fora de `127.0.0.1` (seção 12).
- **Backend:** `backend/representation.py` (novo) e uma chamada em `compute()` de `main.py`. Falha no
  contrato nunca invalida o resultado: o erro é registrado e a geometria vem `INDISPONIVEL` com
  motivo, mantendo tabela e exportações. A chave de execução não muda (metadados não entram na
  assinatura).
- **Frontend:** `ResultWorkspace.tsx` substitui, dentro da mesma página de resultados, o gráfico
  genérico dos “primeiros 12 registros” (subconjunto escolhido pelo sistema) e a tabela genérica,
  preservando a marcação `.data-table` e acrescentando `ResultTable.tsx`, compartilhada pelas tabelas genérica, de distribuição, de critérios e de competências temporais. Todas as linhas ficam acessíveis por páginas de 150.

## 3. Contrato de apresentação (`metadata.representacao`, versão 1)

| Campo | Conteúdo |
|---|---|
| `tabela` | `rows` ou `detail_rows` (distribuição e, desde 19/10/2026, comparação com competência dos valores: um registro por território, com densidade, quantidade e população, que leva os indicadores e o mapa do par; a tabela principal da comparação continua sendo `rows`, com as relações) |
| `vinculo` | coluna que identifica o território e a chave estável (`rotulo`, `codigo` ou `nome`) |
| `indicadores` | colunas representáveis do resultado: `coluna`, `rotulo`, `tipo` (`CONTINUO`, `CONTAGEM`, `POSICAO`, `CLASSE`, `ESTADO`), `unidade`, `origem` (capacidade), `classes` produzidas por capacidade, `nota` (TPL-11 para distâncias) |
| `serie` | descritor de série já calculada (competência, território, categoria, valor, unidade); só com duas ou mais competências. `quebras` (desde 19/10/2026) lista as unidades sem trajetória — tendência não avaliável por série não comparável —, desenhadas só como pontos (nos estados com municípios presentes diferentes, também o `nivel` e as competências da mudança). Nos resultados com níveis territoriais, `paineis` separa a série por tipo de contagem: na quantidade, um painel por nível; na densidade, municípios com o Brasil como referência e estados (soma dos municípios) à parte ([abrangência territorial](ABRANGENCIA_TERRITORIAL.md)) |
| `geometria` | `DISPONIVEL`: `ids`, `lat`, `lon` (arrays paralelos), `competencia`, `referencial`, `fonte`, `configuracao_apresentacao` (origem e premissa contextual, quando usada), `premissa_referencial` (quando o referencial é premissa interna da base oficial numa análise de distância), `complementados`, `sem_geometria` [{id, condição, motivo, texto}] e identidade da camada complementar (arquivo, SHA-256, identificador, versão, premissa, proveniência). `INDISPONIVEL`: desfecho `BLQ-DAD`, motivo e pendência (`REFERENCIAL_GEODESICO`, `REFERENCIAL_NAO_SUPORTADO`, `SEPARADOR_DECIMAL`, `PAPEIS_COORDENADAS`, `COMPETENCIA_UNICA`, `COORDENADAS_NAO_ASSOCIADAS`, `ESCOLHA_PENDENTE`; até 19/10/2026 este último se chamava `CONFIRMACAO`). `NAO_APLICAVEL`: agregação, rotatividade, evolução temporal (várias competências) e resultados só com Brasil e estados ("Mapa não aplicável: Brasil e estados são agregados sem ponto; marque municípios para ver o mapa."). Só municípios entram no mapa e em `sem_geometria`: Brasil e estados nunca têm ponto |
| `notas` | coordenadas complementadas, territórios fora do mapa, TPL-11 |
| `niveis` | só na rota de níveis (desde 19/10/2026): coluna "Nível", ordem dos níveis presentes, tipo de contagem de cada um e o nível desenhado no mapa ("Município") |
| `referencias` | só na densidade e no relatório com densidade da base oficial (desde 19/10/2026, D5): a taxa nacional de referência (rótulo, papel `REFERENCIA_DE_CONTEXTO`, unidade, nota e valores por competência), calculada no backend; a tela a desenha sem classificar nem colorir os municípios em relação a ela: marca e texto na legenda do mapa e linha tracejada nas barras dos municípios (seções 5 e 7); desde o visual completo (19/10/2026), também `serie`, a taxa de todas as competências da fonte nacional (competência sem população de junho fica com `valor` nulo, como lacuna), para o minigráfico do cartão de contexto |
| `resumo` | desde 19/10/2026 (decisão D7): frase-resumo, indicadores (KPIs) e procedência do resultado, compostos no backend (`backend/result_summary.py`) só com cópias de caminhos do próprio resultado, verificadas pelos mesmos verificadores da conversa sobre resultados: `versao`, `modelo` (análise), `texto`, `partes` (texto fixo do modelo e segmentos com `caminho`), `segmentos` (`tipo` VALOR, PARAMETRO ou RELACAO, `caminho`, `texto`), `indicadores` (até quatro: `rotulo`, `caminho`, `valor`, `texto`, `tipo`, `unidade`, `nivel`, `papel` `REFERENCIA_DE_CONTEXTO` na taxa nacional e `serie` com o caminho de uma lista do resultado para o minigráfico), `procedencia` (fonte e versão, fórmula, população do Brasil, tendência, níveis, tipo de contagem e chave de execução) e `nota`. Sem LEX-DES, LEX-NORM e LEX-CAU; LEX-CMP só nas relações do motor; LEX-TEN só com `metadata.tendencia`; a taxa nacional é "referência de contexto", nunca "acima" ou "abaixo". Fica fora de `llm_context` e de `provider_snapshot`; uma falha ao compô-lo só deixa o resultado sem resumo |

- **Autorização da geometria informada** pela regra das análises espaciais: referencial suportado
  (SIRGAS2000, sem transformação), papéis de latitude e longitude estabelecidos (regra, perfil
  oficial ou escolha), separador decimal escolhido ou verificado nos dados (em bases importadas, a
  vírgula verificada vale para desenhar os pontos; formato misto → `SEPARADOR_DECIMAL`) e camada
  complementar governada. Referência mais próxima e critérios com distância usam
  exatamente a leitura memorizada da própria análise (`nearest_inputs`); análise espacial usa o seu
  recorte; as demais usam a competência única do resultado. Várias competências → `COMPETENCIA_UNICA`
  (as coordenadas podem mudar entre competências e não são intercambiáveis).
- **Configuração contextual Brasil:** somente quando a fonte é Brasil, o perfil canônico é reconhecido, a integridade está verificada e a versão efetiva coincide com a governada. Sem CRS informado, a configuração de apresentação utiliza SIRGAS2000 e o formato decimal da fonte (vírgula, salvo opção explícita). É uma premissa ilustrativa autorizada para o desenho dos pontos nesta alteração; **não certifica o datum original**, ausente na fonte. A origem e a premissa ficam em `geometria.configuracao_apresentacao`, na tela e no JSON. Não altera opções, pré-exame, distância nem chave de execução. Referencial explícito não suportado continua bloqueado. Uploads e versões externas diferentes continuam exigindo informação de origem; não há padrão universal. Os cálculos espaciais mantêm sua exigência independente de referencial autorizado: na versão governada, ele é a premissa interna do perfil (SIRGAS 2000, opção `crs` em `governed_premises`), e a geometria dessas análises traz `premissa_referencial` em vez de `configuracao_apresentacao`; a legenda do mapa informa que as distâncias usam esse referencial.
- **Compacto e sem registros individualizados:** apenas coordenadas por território (sede municipal) já
  usadas pelas análises; ~234 KiB para 5.570 pontos (seção 13). Nenhum campo protegido.

## 4. Coordenadas e fontes geográficas

- **Competência do resultado:** o ponto de cada território é a coordenada efetiva da competência do
  resultado. A jornada de navegador cobre um município cuja coordenada muda entre 01/2024 e 06/2024 e
  confirma que cada resultado desenha a sua (seção 12).
- **Camada complementar:** os seis municípios com ponto inválido na fonte original recebem a
  coordenada fixa da camada versionada `dados/brasil/complemento_coordenadas.json` nas 22 competências,
  sob a premissa do usuário de coordenada fixa de 2014 a 2024. A origem aparece no detalhe do
  território (“complementada pela camada oficial … premissa do usuário”), na nota do mapa e no
  contrato. A camada não é aplicada a bases importadas por outros usuários. Como registrado no
  Bloco 2, não houve autenticação independente do arquivo junto ao servidor do IBGE.
- **Sem geometria válida:** territórios com coordenada ausente, inválida ou fora do intervalo
  permanecem no resultado e na tabela, listados à parte (“Sem coordenada válida na competência (N)”)
  com condição e motivo. Na análise espacial (desde 19/10/2026, RQ-DAD-25), esses territórios ficam
  não avaliáveis só eles: linha com distância vazia e “Condição” “Não avaliável: coordenada inválida”
  (ou “ausente”), fora do mapa (`sem_geometria`); a análise da base oficial usa uma competência por vez.
- **Limites de UF e do Brasil: não incorporados (pendência).** As malhas oficiais do IBGE não puderam
  ser obtidas neste ambiente (proxy recusou a conexão, HTTP 403). Malhas não oficiais (por exemplo,
  Natural Earth) não foram adotadas: não têm proveniência oficial verificável e usam outro datum, o
  que misturaria referenciais sem autorização. Consequências assumidas: mapa de pontos sem contorno,
  nenhum centróide substitui sede municipal, **nenhum mapa coroplético** (não há polígonos) e o mapa de
  pontos nunca depende de malha complementar.
- **Projeção só para desenho:** equirretangular (longitude × cosseno da latitude média). Nenhuma
  distância é calculada no frontend; todas vêm do motor (geodésica de Karney, GRS80).

## 5. Mapa territorial interativo (U2)

- Pontos em canvas, redesenhados por `requestAnimationFrame` em lotes por cor, com anel de superfície
  de 2 px; 5.570 pontos em 11 a 18 ms no primeiro desenho (seção 13).
- **Navegação:** botões “Ampliar”, “Reduzir” e “Ver a extensão completa”; Ctrl/⌘ + roda (ou roda com o
  mapa focado); duplo clique; arrastar; pinça; teclado no mapa focado (setas, +, −, 0/Home).
- **Seleção:** clique/toque com alvo ampliado (12 px mouse, 18 px toque), Shift ou “Seleção múltipla”
  para acumular, busca acessível por nome ou código (combobox com lista), linha da tabela (Enter ou
  espaço) e barra do gráfico. A seleção é estado visual e nunca inicia análise.
- **Estados e classes:** cores só para classes produzidas por capacidade (estados de CAP-SUB-01,
  alcance de CAP-ESP-02, quintis de CAP-DIS-02, faixas de CAP-DIS-03 ou de CAP-ESP-03). CAP-ESP-03
  (faixas de distância, com a convenção de CAP-DIS-03) não aparece na lista de RQ-REP-02; exibir suas
  pertenças é interpretação a confirmar. Indicador contínuo: escala
  contínua entre o menor e o maior valor do resultado, com unidade e intervalo na legenda e o aviso “a
  cor não é classe nem limiar”; **nenhum quantil, faixa ou classe criada no frontend.**
- **Escala de cor contínua (desde 19/10/2026):** com todos os valores do resultado positivos, a escala é
  **logarítmica por padrão**: posição da cor = ln(valor ÷ mínimo) ÷ ln(máximo ÷ mínimo). Com zero ou
  valores negativos, só a linear, (valor − mínimo) ÷ (máximo − mínimo). A escolha "Escala de cor do mapa"
  (Logarítmica | Linear, fora da impressão) fica na legenda e é estado visual. O domínio continua o
  mínimo e o máximo do resultado (`__adtMapModel.domain`), e a escolha depende só do sinal dos valores e
  do usuário, nunca da magnitude. Na densidade dos 5.570 municípios (0,23 a 81,07 por 1.000 habitantes em
  06/2024), a escala linear deixava quase todos os pontos claros; a logarítmica distingue os valores
  baixos sem criar classe. A legenda marca os extremos (`legend-extreme`, "mín. 0,23" e "máx. 81,07"),
  traz marcas de leitura em 1, 2 e 5 × 10ⁿ (`legend-tick`, escritas sem zeros à direita: 0,5; 2; 50; são
  marcas do eixo, não limites de classe) e o texto `legend-scale` (`data-scale`): "Escala contínua logarítmica entre o menor e o maior valor do
  resultado: a cor avança em passos iguais a cada multiplicação do valor (de 1 a 10, de 10 a 100), e os
  valores baixos ficam mais distintos; a cor não é classe nem limiar." (na linear, "Escala contínua
  linear entre o menor e o maior valor do resultado; a cor não é classe nem limiar."). Com um só valor no
  resultado (mínimo igual ao máximo), o texto é "Um só valor no resultado: a cor fica no meio da rampa; a cor
  não é classe nem limiar." e a escolha da escala não aparece (as duas dariam a mesma cor). A marca da taxa
  nacional usa a mesma posição de cor. Com poucos territórios (até 12), o nome de cada ponto aparece junto
  dele; um nome que cobriria outro nome, outro ponto, os botões do mapa ou as coordenadas da borda de baixo vai para o
  outro lado do ponto ou um pouco acima ou abaixo (só o texto se move, nunca o ponto). `representacao_aplicada.escala` registra `tipo` ("mapeamento
  visual contínuo logarítmico" ou "… linear"), `transformacao`, `escolha`, `dominio`, `rampa` e
  `classificacao: false`; o gancho de teste `__adtMapModel.scale` traz a escala aplicada, e
  `__adtMapModel.fills` só é nulo para valor nulo. É transformação formal da apresentação (RQ-REP-02:
  "Escala visual contínua é transformação formal e não constitui classificação"); não muda a escala do
  indicador (por 1.000 habitantes, RQ-REP-11). Não é divergência da SPEC.
- **Taxa nacional de contexto (D5, desde 19/10/2026):** na densidade da base oficial de uma
  competência, a legenda mostra uma marca tracejada sobre a escala, na posição do valor (na borda quando
  fica fora dela), e o texto “Brasil (total nacional): 2,36 por 1.000 habitantes · referência de
  contexto; a cor dos municípios não é classificada em relação a ela.” (com “(fora da escala dos
  municípios)” quando cabe). O domínio de cor continua o mínimo e o máximo dos municípios e as cores não
  mudam (sem cor de juízo acima ou abaixo da taxa). O gancho de teste `__adtMapModel.reference` traz o
  valor desenhado. O mapa só tem municípios: Brasil e estados nunca têm ponto. Desde o visual completo
  (19/10/2026), a dica do ponto traz também "· Brasil (contexto): x,xx por 1.000 habitantes", e o
  detalhe do território selecionado, a linha "Brasil (contexto)" (`detail-national-reference`, "… · taxa
  nacional em 06/2024; referência de contexto, não classifica o território."), com casas suficientes para
  os dois valores não parecerem iguais (RQ-REP-05).
- **Mapa do par de comparação (desde 19/10/2026):** a comparação com competência dos valores desenha os
  territórios comparados na coordenada dessa competência (`tabela = detail_rows`); antes, o par aparecia
  como "Mapa indisponível", porque `rows` só tinha "Valor A" e "Valor B".
- **Não avaliável:** anel vazado cinza, nunca preenchido como zero, com legenda.
- **Referências:** losangos; esmaecidas quando fora do filtro e sem ligação.
- **Ligações:** tracejadas, só para até 30 territórios selecionados, rotuladas “ligação ilustrativa
  (não é trajeto)”.
- **Dica** contida na área do mapa; legenda como região própria (“Legenda do mapa”).
- **Poucos territórios (18/10/2026):** com até 12 pontos, o nome de cada território aparece junto ao
  ponto, com halo da superfície; com até três, também o valor do indicador representado. A grade de
  coordenadas ganhou passos de 0,05°, 0,02° e 0,01°, para que um ponto isolado venha com latitude e
  longitude de referência. Nomes e valores vêm do resultado (rótulos de metadado autorizado).
- **Paletas validadas** pelo validador de paletas (modo claro, superfície `#fcfcfb`):
  - par de estados ATENDE `#eb6834` / NÃO ATENDE `#2a78d6`: todas as verificações aprovadas (pior ΔE
    em daltonismo 24,7; contraste ≥ 3:1);
  - categórica de 8 posições: aprovada, com aviso de contraste em três cores, compensado por legenda
    visível e tabela;
  - sequencial azul de um só matiz, do claro ao escuro.

## 6. Referências e distâncias

- Alvos e referências distinguidos (círculo × losango). O detalhe do território traz:
  - referência(s) mais próxima(s) com nome e código, e distância geodésica do backend em km
    (RQ-REP-05, com o valor integral disponível);
  - empate com todas as referências apresentadas;
  - “o próprio alvo é referência (distância zero)”;
  - alcance, com as distinções do motor preservadas:
    - “Conjunto completo de referências” (`minimo_completo`);
    - referência mais próxima com referência sem coordenada válida na lista: “entre as referências
      avaliáveis — cobertura parcial: o mínimo do conjunto completo não é avaliável para este alvo;
      não equivale a ele” (`minimo_avaliaveis`, informado pelo motor sem aceitação do usuário);
    - critérios com a aceitação marcada: “entre as referências avaliáveis (cobertura parcial) — cobertura
      parcial aceita explicitamente; não equivale ao mínimo do conjunto completo”;
    - critérios restritos às referências confirmadas: “conjunto completo das referências de
      elegibilidade confirmada”.
- **Critérios sem distância avaliável:** o detalhe mostra as causas estruturadas do motor
  (elegibilidade desconhecida em N candidatos, referências sem coordenada avaliável com cobertura
  parcial não aceita, conjunto vazio, coordenada do alvo).
- **Referência sem coordenada válida:** fica fora do mapa e listada.
- **Distância** é sempre descrita como geodésica direta (TPL-11 na nota do mapa, na legenda das
  ligações e nas exportações).

## 7. Gráficos (U3)

- **Contagens do motor:** territórios por resultado dos critérios, por alcance da referência mais
  próxima ou por faixa. O não avaliável aparece em barra própria e nunca soma em “não atende”.
- **Barras por território:**
  - todos os territórios por padrão, ou os selecionados explicitamente; acima de 40, uma janela com rolagem monta apenas as barras próximas à área visível, mantendo **todos** os territórios acessíveis, inclusive o último;
  - ordem padrão pelo código territorial;
  - “ordem do resultado” só existe quando há ordenação do motor;
  - “valor, decrescente (apenas visual)” traz o aviso “Ordenação apenas visual: não constitui posição
    de ranking nem resultado”;
  - territórios sem valor são identificados como não avaliáveis, sem converter ausência em zero;
  - cada barra traz o valor do motor no fim (até 40 barras, no gráfico com eixo; acima, na lista com rolagem),
    num fundo opaco que passa por cima da linha da taxa nacional, sem barra nem número para quem não tem valor;
  - quantitativos com unidade pessoas e objeto estabelecido como força de trabalho em saúde (`fts_scope_confirmed`: perfil oficial, categorias reconhecidas pelo catálogo da força de trabalho em saúde ou premissa do objeto informado) usam “profissionais” apenas no rótulo de apresentação; a unidade metodológica original é preservada;
  - resultados com série temporal usam linhas, evitando representar a primeira competência como se fosse todo o resultado;
  - a distribuição inclui na aba Gráficos as frequências dos grupos calculados pelo motor, num gráfico só,
    com o título "Quantas unidades pertencem a cada quintil?" (quartil, decil ou faixa pelo número de
    classes) e a figura "Territórios por grupo da distribuição"; desde 19/10/2026 sai o gráfico repetido
    que `DistributionResults` desenhava abaixo dos grupos;
  - na densidade da base oficial de uma competência, a taxa nacional (D5) é uma linha tracejada
    vertical com o rótulo “Brasil 2,36” e a legenda “Brasil (total nacional): 2,36 por 1.000 habitantes,
    referência de contexto; a linha não classifica os municípios.” (`bars-reference-line`); ela entra no
    eixo, mas não muda a cor das barras, também na janela com rolagem;
  - na janela com rolagem, o número de cada barra fica logo depois do fim dela (perto da borda direita,
    dentro da barra), num fundo claro por cima da linha tracejada da referência;
  - com níveis territoriais (desde 19/10/2026), os municípios (`level-panel-mun`) e os estados
    (`level-panel-uf`, “· Estados (soma dos municípios)”) ficam em figuras separadas; nunca há barra do
    Brasil nem de um estado entre os municípios. Desde o visual completo, os blocos ficam no contêiner
    `levels-panel` ("Brasil, estados e municípios em blocos separados, cada um no seu eixo: nenhum nível é
    somado a outro nem comparado com outro."): o bloco do Brasil (`level-panel-br`) mostra o valor da linha
    do motor, o tipo de contagem e "Lado a lado: não entra em maior, menor nem diferença com estados ou
    municípios."; as barras dos estados têm textura listrada e o aviso `uf-warning` ("Soma dos municípios:
    possível dupla contagem · não comparável com a contagem nacional."), sem a linha nacional; nas barras dos
    municípios em ordem de código, um separador por estado (`bar-group-separator`, lido de
    `universe.members[].state`), sem reordenar nem contar.
- **Linhas:**
  - só para séries já calculadas pelo motor (evolução temporal; competências da própria série, sem
    presumir 22 períodos);
  - lacunas preservadas (`connectNulls=false`), sem tendência nem taxas novas criadas na tela; as unidades de
    `serie.quebras` aparecem só como pontos, sem linha de trajetória;
  - uma única competência não forma série;
  - com níveis territoriais, um gráfico por painel de `serie.paineis` (`level-panel-{id}`), sem misturar
    tipos de contagem;
  - todos os territórios ou a seleção explícita, com páginas de oito na ordem dos dados; navegação mostra o intervalo e o total, sem amostragem;
  - eixo vertical em números redondos ao redor dos valores observados (passo 1, 2, 2,5 ou 5 × 10ⁿ),
    para que a variação fique visível; quando o eixo não começa em zero, a legenda do gráfico informa
    onde começa. A unidade e a escala de apresentação (por 1.000 habitantes, CAP-IND-02) não mudam;
  - linhas de 2 px e marcadores de 8 px com anel da superfície; série única sem caixa de legenda (o
    território fica na legenda do gráfico); até quatro séries, rótulo direto só no último valor;
  - desde 19/10/2026, o Brasil marcado na abrangência (referência do painel da série de níveis) é uma linha
    tracejada em tinta; na densidade e no relatório com densidade (K10), a taxa nacional de cada competência
    entra como linha tracejada "Brasil (total nacional) · taxa nacional (contexto)", sem ligar lacunas, nunca
    no painel dos estados nem quando o Brasil já é uma série.
- **Evolução temporal (desde 19/10/2026):** além das linhas, pequenos múltiplos (`trend-small-multiples`,
  com `data-domain`; um `trend-small-multiple` por território, com `data-territory`), em SVG, 12 por página
  (navegação "Páginas dos pequenos múltiplos"), na **mesma escala em todas as páginas**, lacunas sem ligação,
  série de `serie.quebras` só com pontos, o Brasil marcado tracejado e o selo da classe do motor em cada um;
  e halteres do primeiro ao último período (`temporal-dumbbells`, `data-total`; `dumbbell-row`, círculo
  vazado no inicial e cheio no final, `dumbbell-delta` com a "Variação absoluta" do motor e o selo), na ordem
  do resultado, eixo a partir do zero, lista com rolagem acima de 40. Um bloco por painel de contagem na rota
  de níveis. Nada é interpolado nem ajustado.
- **Comparação (desde 19/10/2026), acima das abas:** `comparison-panel` com a legenda
  `comparison-values-caption` ("Competência dos valores: 06/2024 · janela de 06/2014 a 06/2024 (11
  competências): mudança e tendência de cada território. Relações (maior, menor, diferença) só dentro do mesmo
  nível."); a figura `comparison-side-by-side` com um bloco por nível (`comparison-group-br|uf|mun`, ou
  `comparison-group-todos` sem níveis), na ordem do motor, cada um no seu eixo a partir do zero; até seis
  objetos por nível em cartões `comparison-object` (`data-territory`) com densidade, quantidade e população da
  competência dos valores (só a quantidade no indicador quantidade), a condição e o selo de tendência do motor;
  abaixo, os valores, com a unidade escrita sobre a lista ("Valores por 1.000 habitantes, no eixo deste nível,
  a partir do zero"; lista com rolagem acima de 40). O par de cada nível (`comparison-pair-relation`) mostra a
  relação A/B e a "Diferença A − B" **do motor**. O Brasil fica "Lado a lado, sem relação"; os estados, com
  textura e `uf-warning`; não há linha nacional (K10). Com a janela, `comparison-dumbbell` (um grupo
  `comparison-dumbbell-group-*` por nível) com os halteres do primeiro ao último período, a variação e o selo
  `trend-badge` iguais aos de `detail_rows`, e a nota "Classes de tendência lado a lado: entre territórios, só se
  lê se a classe é a mesma; as classes não têm ordem entre si." Nos cartões da tabela
  (`comparison-territory-row`, mesma contagem de antes), o bloco `comparison-card-extra` acrescenta quantidade e
  população na competência dos valores, a mudança e o selo com o motivo, sem atributo `title` (o "Valor
  integral" continua um por cartão). Cada cartão mostra só as colunas do seu formato de linha: o de um território
  não lista as colunas vazias do par (Objeto A e B, Valor A e B, Relação A/B, Diferença A − B) nem as relações vazias
  com os vizinhos ("Próximo valor maior" e "Unidades com mesmo valor": o maior do nível não tem próximo valor maior, e
  o Brasil fica lado a lado, sem relação), e o resumo do par
  (`comparison-pair-summary`) não lista as colunas vazias do território (Território e o valor de cada território);
  vazio por formato não é "Não avaliável". A tabela, o CSV e os filtros continuam com todas as colunas. Sem razão nem diferença percentual automáticas (AT-84). Resultado sem
  `detail_rows` (chamada antiga) só vira painel quando tem um recorte (uma competência e uma categoria).
- **Ranking em pirulito (desde 19/10/2026):** `ranking-lollipop` (`data-total`; `lollipop-row` com
  `data-rank`) no lugar das barras do ranking: "Posição N" do motor, na ordem pedida (padrão: a do resultado),
  haste do zero ao valor, território sem valor sem haste e sem posição, sem linha nacional; estados no bloco
  `level-panel-uf`. Quando o arredondamento igualaria dois vizinhos de valores diferentes (por exemplo, 1,9810
  e 1,9783 nas posições 21 e 22 dos estados em 06/2024), o valor ganha as casas que os distinguem (RQ-REP-05).
- **Faixa da distribuição (desde 19/10/2026):** `distribution-strip` (`data-total`): um ponto por território
  na raia da classe do motor (ordem das classes do resumo), na posição do seu valor, cor ordinal pela classe,
  selecionados maiores; nenhum ponto de corte desenhado. O SVG é desenhado na largura do contêiner (o texto não
  estica) e, com todos os valores positivos, num **eixo logarítmico** entre o menor e o maior valor (a mesma
  transformação contínua da escala de cor do mapa; `data-scale`), com os extremos ("mín." e "máx.") e marcas
  1, 2 e 5 × 10ⁿ do eixo, que não são pontos de corte; com zero ou negativos, linear. Na densidade dos 5.570
  municípios (0,23 a 81,07), o eixo linear espremia os quatro primeiros quintis junto ao mínimo. O total do cabeçalho da distribuição
  (`distribution-total`, "N unidades territoriais classificadas (total do motor)") é a métrica "Unidades
  classificadas" do motor: a tela **não soma** mais as unidades das classes.
- **Cartão da agregação (desde 19/10/2026):** `aggregate-card`, fora de `result-highlights`: quantidade,
  população e densidade do motor; o `Tipo` do motor como selo obrigatório (`aggregate-type`, com textura na
  soma dos componentes e "soma das contagens dos componentes" sob a quantidade, RQ-REP-14); os membros
  (`aggregate-members`) e, quando o motor os declara em `selecao_territorial.expansoes`, os ausentes por
  competência (`aggregate-missing`). Sem linha nacional.
- **Rotatividade (desde 19/10/2026):** `rotation-cohort-bars` com uma `cohort-bar` (`data-territory`) por
  coorte: barra da coorte inicial dividida em "permanecem" e "saíram" com os percentuais do motor (% da coorte
  inicial); coorte não avaliável com contorno tracejado e o motivo. As cores só separam os grupos, sem juízo.
- **Cartões de destaque (painel simples, RQ-REP-10):** densidade, quantitativos, relatório e evolução
  com até três registros mostram, acima das abas, um cartão por registro com os valores do próprio
  motor, formatados por RQ-REP-05: território, categoria, valor principal, unidade e competência; na
  densidade, também quantidade e população. Na evolução, inicial → final, variação absoluta e
  percentual e a tendência do motor. A seta indica só o sinal da variação, sem cor de juízo, porque
  não há limiar normativo. Nenhum total, média, posição ou classe é criado. Desde 19/10/2026, a
  tendência aparece como selo da classe (`trend-badge`, com `data-class`), com o motivo, o número de
  observações e o minigráfico das velocidades do motor (`trend-velocities`). Com níveis (desde o visual
  completo), cada cartão traz o nível (`data-level`); o do estado tem textura, o aviso "possível dupla
  contagem · não comparável com a contagem nacional", a quantidade "na soma das contagens dos municípios" e
  a densidade "por 1.000 habitantes (soma dos municípios)" (RQ-REP-14; antes, "profissionais").
- **Tendência na evolução temporal (CAP-TEN-01):** a coluna Tendência da tabela mostra o selo; a aba
  Gráficos traz a contagem por classe do motor (`trend-counts`), na ordem da SPEC e com os não
  avaliáveis à parte; o filtro visual ganha as famílias (`trend-family-filter`); o aviso da etapa
  (`trend-stage-note`) mostra o bloqueio BLQ-MET ou o RES-SCL. Cores pela família: crescimento em
  azul, declínio em laranja, Sem classificação em verde-água (sempre com texto) e não avaliável em
  cinza tracejado; não há verde para "bom" nem vermelho para "ruim". Os indicadores declarados são
  Tendência (CLASSE), Direção da mudança (ESTADO), Variação absoluta e Variação percentual
  (CONTINUO); o mapa continua não aplicável. Ver `Docs/EVOLUCAO_TEMPORAL_E_TENDENCIA.md`.
- **Indicador compartilhado:** o indicador escolhido no mapa vale para as barras, e vice-versa,
  quando ambos o representam.
- **Dispersão e bolhas: não implementados.** RQ-REP-10 não os lista entre os tipos admitidos. Proposta
  de extensão de CFG-REP para decisão humana, sem alteração da SPEC:
  - “diagrama de dispersão de dois indicadores contínuos já presentes no mesmo resultado, mesma
    competência e mesmo universo, sem reta de ajuste, sem correlação e sem classes; não avaliáveis
    listados à parte”;
  - “bolhas” só se o tamanho codificar uma contagem do próprio resultado.
  - Pendente de aprovação.

## 8. Sincronização, filtros e reutilização (U4)

- **Seleção compartilhada** por identificador estável (código) entre mapa, busca, tabela e barras;
  painel “Territórios selecionados” com o detalhe do território em foco.
- **Filtro visual comum:**
  - critérios: Todos, Atendem, Não atendem, Não avaliáveis, Selecionados (seleção do motor) e Minha
    seleção (estado visual);
  - referência mais próxima: Todos, mínimo do conjunto completo, somente entre avaliáveis, não
    avaliáveis e Minha seleção;
  - demais análises: Todos e Minha seleção.
  - O filtro limita mapa (os demais pontos ficam esmaecidos) e tabela, usando apenas estados do motor.
- **Nenhuma requisição de análise** por zoom, seleção, filtro, indicador ou troca de aba (RQ-REP-06),
  conferido nas jornadas.
- **Reutilização explícita, sem execução:**
  - “Usar seleção na próxima análise” leva os territórios à seleção territorial compartilhada;
  - “Usar seleção como referências” (referência mais próxima e critérios) leva-os à lista de
    referências;
  - a aba Mapa não contém formulário de referencial/separador; em uploads, essas informações de origem podem ser revistas nas opções avançadas da preparação;
  - a execução continua pelo botão da preparação.

### Filtros da tabela

Cada coluna permite busca por texto sem distinguir acentos e comparações numéricas (`>`, `<`, `>=`, `<=`, `=`), com ponto ou vírgula decimal. Competências (“Período”, “Período inicial”, “Período final”) aparecem como mês/ano (06/2024); a busca aceita tanto 06/2024 quanto o valor original 202406, que continua no CSV. Ausências não atendem comparações numéricas. A ordenação é apenas visual e não modifica as posições calculadas. Páginas de 150 dão acesso a todos os registros; o CSV da tabela exporta **todo** o filtro, em precisão integral, sem ficar limitado à página. O CSV superior exporta o resultado original. Filtros por coluna não alteram mapa, gráficos ou preparação; o filtro visual comum segue separado e explícito.

## 9. Painel integrado, histórico e competências (U4)

- **Cabeçalho do resultado (desde 19/10/2026, decisão D7):** entre a descrição e as abas, o cabeçalho
  `result-header` (`ResultHeader.tsx`, funções puras em `headerModel.ts`) substitui a grade de métricas:
  - `result-summary`: a frase do motor (`metadata.representacao.resumo`), montada pelas partes; cada valor
    só é formatado para leitura (competência AAAAMM como mês/ano, inteiro com milhar, sinal tipográfico,
    decimais com as casas escritas pelo motor), em negrito; a relação e o texto fixo ficam como o motor
    escreveu. Exemplos com a base versionada: "Na competência 06/2024, densidade por 1.000 habitantes: 5.570
    registros avaliáveis e 0 não avaliáveis. Referência de contexto: taxa nacional de 2,36 por 1.000
    habitantes (Brasil, total nacional); não classifica nem colore os territórios." e, com níveis, "…, em
    blocos por nível, sem somar níveis: Brasil (total nacional), 2,36 por 1.000 habitantes; Estados (soma
    dos municípios), 1 registro avaliável e 0 não avaliáveis; Municípios, …";
  - `result-kpis` (lista) com até quatro `result-kpi` (`data-nivel` BR, UF ou MUN): valores do motor; a taxa
    nacional (só densidade e relatório com densidade, K10) é um cartão tracejado com o selo "contexto"
    (`data-papel="REFERENCIA_DE_CONTEXTO"`) e "Referência de contexto: não classifica nem colore os
    territórios."; sem valor único (várias competências), o último ponto avaliável da série do motor, com
    "em MM/AAAA (última competência avaliável da série)". O minigráfico (`kpi-sparkline`, `data-points`) desenha
    a lista apontada pelo motor (`serie.caminho`: a série nacional, ou as linhas do Brasil nos quantitativos
    nacionais), uma categoria só, em ordem cronológica, com lacunas sem ligação e só com duas ou mais
    competências; o rótulo acessível traz o intervalo, os extremos e as lacunas;
  - `result-provenance`: os itens de procedência do motor ("Fonte: Dados do Brasil, fonte municipal · versão
    …", "Fórmula: Densidade = quantidade ÷ população × 1.000 (CAP-IND-02)", "População do Brasil: regra
    BR-POP-JUNHO-1 (junho, soma dos municípios)", "Tendência: versão …", "Níveis", "Tipo de contagem",
    "Chave de execução").
  `result-title` e `result-status` não mudam. Resultados sem `resumo` (anteriores) mostram a grade de antes
  (`result-metrics`). A descrição do motor continua acima do cabeçalho, com as competências AAAAMM como
  mês/ano. A identidade do resultado mostra a "Situação do resultado" com acentos ("avaliável com
  limitações"; antes "avaliavel com limitacoes") e, em arquivo importado, o nome do arquivo (antes
  "[object Object]").
- **Painel próprio da análise (desde 19/10/2026):** antes das abas, a comparação (`comparison-panel`), o cartão
  da agregação (`aggregate-card`) e as barras da coorte (`rotation-cohort-bars`), descritos na seção 7.
- **Abas:** Mapa, Gráficos e Tabela, dentro do resultado no painel de análise, ao lado da conversa no computador. A aba
  Mapa indica “(indisponível)” ou “(não aplicável)” quando não há geometria, e o motivo fica a um
  clique, sem esconder tabela e gráficos. “Mapa não aplicável a este resultado” tem título próprio;
  na evolução temporal, orienta preparar uma densidade ou quantitativos de uma competência para ver
  os territórios no mapa. A regra de não desenhar a evolução no mapa continua a mesma.
- **Identidade do resultado:** até três competências por extenso; acima disso, quantidade e extremos
  (“22 competências, de 01/2014 a 06/2024”), com a lista completa no título do elemento e nas
  exportações.
- **Histórico:** cada resultado é reconstruído com os próprios dados, parâmetros, origem, versão da
  camada e limitações (`metadata.representacao` do resultado). Aviso em linguagem comum identifica a consulta a uma análise anterior e orienta revisar a preparação para atualizar; resultado invalidado fica só para consulta, sem reutilização da
  seleção. A compatibilidade de fonte e camada segue a regra existente (`compatible`).
  - **Atualização (16/10/2026):** o controle “Histórico” fica na barra horizontal, inclusive com zero ou um cálculo. Reabrir alterna o resultado no fluxo único; o campo de mensagem continua acessível. A disposição vigente está em `INTERFACE_CONVERSACIONAL_INTEGRADA.md`. O controle antigo de histórico foi removido no commit `dbaa0bd`: a lista "Histórico de resultados" e o controle de
    invalidação saíram da interface. A reconstrução descrita acima continua valendo para o resultado
    atual, para a retomada e para as competências calculadas. Não há mais como invalidar pela
    interface. Ver [`REGISTRO_DE_COMPORTAMENTO.md`](REGISTRO_DE_COMPORTAMENTO.md).
- **Competências calculadas:** navegação entre resultados já existentes do mesmo pedido que diferem
  só no período. Para esse agrupamento, opção desmarcada ou vazia equivale a opção ausente; o estado
  “vigente” continua exigindo a chave exata. Nenhum resultado é fabricado.
- **Dimensão do mapa:** a legenda usa coluna própria apenas quando o painel de análise tem ao menos 850 px; em painéis menores, fica abaixo do mapa. O canvas acompanha a largura efetiva do painel, inclusive após alternar entre impressão e tela.

## 10. Exportações

- **Preservadas:** CSV, JSON (“Método e parâmetros”) e impressão do navegador.
- **JSON:** passa a trazer `representacao`, com a geometria integral, e `representacao_aplicada`,
  o registro das transformações da representação em uso: aba, indicador, escala e domínio (ou classes
  da capacidade), filtro e seleção visuais, arredondamento, projeção, identidade da geometria e da
  camada, ordem das barras, filtros/ordem/página da tabela e página/categoria das séries.
- **PNG:** botões de imagem do mapa e dos gráficos removidos por solicitação do produto. O download JSON permanece com todos os pontos, método, parâmetros e origem; não há JSON embutido na página.
- **Impressão:** inclui a visualização aberta (mapa ou gráficos); os controles ficam fora. **Não há
  gerador de PDF no servidor**; “Imprimir / PDF” usa o recurso de impressão do navegador. SVG não é
  oferecido. A impressão reflete a visualização aberta e a página atual da tabela, sem prometer um relatório integral de todas as páginas.

## 11. Acessibilidade e responsividade

- **Teclado em todos os controles:**
  - mapa focável, com instruções no rótulo;
  - busca em combobox com lista;
  - abas com `role="tab"`;
  - linhas de tabela selecionáveis por Enter ou espaço;
  - legenda como região.
- **Alternativa textual:** tabela sempre disponível, gráficos com `figure` rotulada e territórios sem
  valor listados. Os visuais de 19/10/2026 usam `figure`/`figcaption`, SVG com `role="img"` e rótulo,
  listas com `role="list"`/`listitem`, listas longas com rolagem focável (`tabIndex`) e selos sempre com
  texto; os controles novos (escala de cor, páginas dos pequenos múltiplos) ficam fora da impressão, e o
  cabeçalho e os visuais aparecem nela.
- **Celular:** sem rolagem horizontal da página a 390 px (e a 768 px, conferido também nos visuais de
  19/10/2026); abaixo de 640 px, as barras com rolagem, as listas de valores da comparação, os halteres e o pirulito põem o nome do
  território numa linha própria, inteiro, e o desenho e o valor na linha de baixo; mapa com 360 px de altura, seletores em
  largura total e dica contida na área. O chat e a preparação conversacional seguem cobertos pelas
  jornadas existentes.

## 12. Fidelidade e testes

- **Backend:**
  - `test_representation.py`: densidade por
    competência com município que se desloca, inválido e ausente fora do mapa e listados; homônimos; casos bloqueados (referencial,
    separador, papéis, sem coordenadas, várias competências); agregação e evolução temporal sem mapa e
    com série; indicadores, unidades e classes; referência mais próxima com referências de outra UF e
    inválidas, alvo-referência e cobertura parcial; conjunto de referências vazio; critérios ligados
    por código; robustez (falha no contrato mantém linhas e chave); seis pontos complementados nas 22
    competências com a identidade da camada.
  - `test_representation_real.py` (opt-in com `ADT_REAL_DATA_DIR`): mapa automático nas 22 competências igual à
    leitura independente do CSV e da camada (SHA-256 conferido); cenário de critérios com 5.570
    pontos, ATENDE e referências contidas no mapa.
- **Navegador:** `ui_map_smoke.py`, no job `ui-block1` do CI, com base importada fictícia:
  1. mapa de upload indisponível sem referencial, sem formulário na aba Mapa; origem configurada na preparação sem executar;
  2. modelo desenhado idêntico à geometria da resposta, legenda com mínimo e máximo, territórios fora
     do mapa listados;
  3. seleção por busca de homônimo, por clique, com Shift e pela tabela;
  4. filtro “Minha seleção” e retorno do detalhe à tabela (“Ver na tabela”);
  5. troca de indicador, zoom, arrasto, teclado e extensão completa, sem nova análise;
  6. gráficos com ordenação visual rotulada e ausência dos controles PNG;
  7. geometria integral no JSON e reutilização da seleção sem execução;
  8. segunda competência, com o ponto deslocado e a navegação entre competências;
  9. histórico sem geometria;
  10. referência mais próxima com referências de outra UF e inválida, empate (ligações iguais às
      referências empatadas) e cobertura parcial informada pelo motor (sem o rótulo de aceitação);
  11. critérios com território não avaliável em anel vazado e filtro compartilhado;
  12. impressão;
  13. celular e redimensionamento.

  A jornada falha com qualquer erro de página ou requisição externa. A pinça (dois dedos) está
  implementada, mas não é exercitada pela automação, que roda em navegador de mesa.
- **Regressão de visibilidade:** `ui_visibility_diagnostic.py` usa 180 territórios sintéticos, confere barras sem seleção inicial, último território via rolagem, mudança de indicador, filtros/ordenação/páginas/CSV, distribuição e páginas de séries. `ui_block1_smoke.py` com a base versionada confere mapa automático e barras dos 62 municípios do AM. `ui_conversational_smoke.py` confere perguntas antes da fonte e agradecimento; todos os roteiros permanecem registrados em `run_ui_checks.py`.
- **Dados reais:** `bench_ui_map.py` confere que o modelo desenhado é a geometria da resposta
  (5.570 pontos), que o filtro inicial mostra exatamente os ATENDE desenhados e que as referências
  desenhadas são as do motor.
- **Visual completo (19/10/2026):**
  - `backend/tests/test_result_summary.py`: em todas as análises, cada segmento do resumo passa no
    verificador da conversa e o texto fixo não usa LEX-DES, LEX-NORM nem LEX-CAU; LEX-CMP só nas relações do
    motor; LEX-TEN só com `metadata.tendencia`; nunca "acima" ou "abaixo"; níveis sem soma e taxa nacional como
    contexto; o resumo e as entradas dele não chegam ao provedor; uma falha ao compô-lo não derruba a análise;
    segmento que não confere é recusado.
  - `backend/tests/test_comparison_window.py` e `test_representation.py` (mapa do par DISPONIVEL, com
    `tabela = detail_rows`); `test_territorial_levels.py` e `test_levels_real_data.py` (comparação com janela por
    nível, métricas por nível, série nacional).
  - Node: `frontend/tests/headerModel.test.mjs` (frase pelas partes, formatação, KPIs, minigráfico com lacunas) e
    `visualModels.test.mjs` (escala de cor sem classes, marcas, comparação por nível, halteres, pequenos
    múltiplos na mesma escala, faixa, coorte, agregação).
  - Navegador: `ui_result_visuals.py`, nas suítes `bloco1` e `base-versionada`: cabeçalho igual ao resumo do
    motor, níveis em blocos, comparação (relação e diferença do par, selo igual a `Tendência` de `detail_rows`,
    caixa "Competência dos valores" e envio de `comparison_values_period`), evolução (pequenos múltiplos e
    halteres), ranking (posição do motor), distribuição (total do motor, um só gráfico de contagens e classe de
    cada ponto), agregação (tipo de contagem), rotatividade (percentuais da coorte), escala logarítmica e linear
    do mapa com o domínio igual, taxa nacional só como contexto (cartão com o minigráfico da série do motor,
    linha nas barras dos municípios e nenhuma nos estados), nenhuma "Unidades avaliáveis" contando só
    municípios, 390 e 768 px sem rolagem horizontal e impressão; na base versionada, a série anual de junho
    com 11 competências e o mapa do par na competência 06/2024.

### Validação dos ajustes de 15/10/2026

- `ADT_REAL_DATA_DIR=<raiz> python -m pytest -q -rs`: **438 aprovados, nenhum pulado**; avisos de depreciação do TestClient e de permissão do cache do pytest no Windows.
- `npm ci` e `npm run build`: aprovados; permanece o aviso de tamanho do bundle.
- `python backend/tests/run_ui_checks.py`: **9 roteiros aprovados**; após o ajuste final de seleção das séries, a suíte `bloco1` foi repetida e os **6 roteiros passaram**, incluindo filtros registrados no JSON e retorno à primeira página das séries.
- Governança aprovada; diagnóstico de dados com `integridade: verificada` antes e depois. Nenhum arquivo versionado de dados nem a SPEC foi alterado.
- No Windows, os comandos Python foram executados com `PYTHONUTF8=1` para a saída e as mensagens de commits em português; sem isso, a página de códigos cp1252 prejudicava a verificação de governança e a impressão do resumo. Não foi necessário alterar as verificações.
- Conferência no navegador local: mapa automático com **5.570 pontos** e barras com todos os **5.570 territórios**, sem preenchimento de parâmetros na aba Mapa.

## 13. Desempenho

Mesma sessão, 4 CPUs, catálogo real instalado (5.570 municípios, 22 competências). Antes = árvore
`2d8f7a0` com o próprio frontend; depois = Bloco 3. Valores só de tempo e tamanho.

### 13.1. Mapa e visualizações no navegador (`bench_ui_map.py`; rodadas 1 e 2 na regressão final, 3 avulsa)

Cenário principal: junho de 2024, MEDICINA, densidade < 2,36 E distância > 155 km, referências com
densidade ≥ 2,36 e cobertura parcial aceita explicitamente. O cenário teve 5.570 territórios, 5.570
pontos, 0 sem geometria, 6 complementados, 2.007 referências e 225 que atendem, todos desenhados.

| Medida | Rodada 1 | Rodada 2 | Rodada 3 |
|---|---|---|---|
| requisição (s) | 3,32 | 3,29 | 3,33 |
| resposta → tabela (ms) | 413 | 381 | 462 |
| resposta → mapa desenhado (ms) | 489 | 449 | 529 |
| primeiro desenho de 5.570 pontos (ms) | 17,5 | 13,7 | 11,3 |
| tarefas longas (máximo, ms) | 1 (150) | 1 (141) | 1 (142) |
| clique → seleção desenhada, mediana / máx. (ms, 5 cliques) | 26,4 / 61,3 | 25,7 / 54,9 | 26,6 / 55,7 |
| clique → detalhes na tela, mediana / máx. (ms) | 27,2 / 62,1 | 26,5 / 55,7 | 27,5 / 56,6 |
| quadros de zoom e arrasto, mediana / p95 / máx. (ms, 41 quadros) | 1,6 / 3,8 / 4,4 | 1,4 / 4,4 / 6,0 | 1,3 / 4,2 / 6,6 |
| troca Mapa → Gráficos / Gráficos → Tabela / Tabela → Mapa (ms) | 94 / 18 / 70 | 81 / 28 / 79 | 75 / 21 / 63 |
| troca do indicador das barras (ms) | 62,5 | 49,6 | 47,8 |
| heap JS antes / com resultado e mapa / após interações (MB) | 11,7 / 26,4 / 28,2 | idem | idem |

Todos os quadros de navegação ficam abaixo de 7 ms (orçamento de 16 ms para 60 quadros por segundo).
Seleção, zoom, filtros e troca de aba não geram requisição de análise.

### 13.2. Efeito na latência das análises

**Navegador, cenário principal** (`bench_ui_criteria.py`, ordem alternada depois/antes/antes/depois):

| Caso | Requisição antes (s) | depois (s) | resposta → tabela antes (ms) | depois (ms) |
|---|---|---|---|---|
| densidade e distância, todos os municípios | 3,33 / 3,45 | 3,70 / 3,38 | 264 / 254 | 254 / 254 |
| com ordenação e 20 primeiros | 3,81 / 3,92 | 4,01 / 3,55 | 246 / 314 | 388 / 208 |

As faixas se sobrepõem: não há efeito mensurável na latência percebida. A resposta cresce de 5,22 para
5,44 MB (o contrato de apresentação, 234 KiB) e a digitação segue refletida no quadro seguinte
(5 a 17 ms antes e depois).

**Backend, mesmo cenário** (`bench_criteria.py`): requisição completa 3,64 s antes e 3,54 s depois;
com só o limiar alterado, 3,46 s e 3,12 s. As fases são equivalentes e as contagens, idênticas (225
ATENDE, 5.345 NAO_ATENDE, 0 NAO_AVALIAVEL).

**Custo do contrato medido dentro das requisições reais** (`representation.payload`, mediana de 7):

| Requisição | Contrato | Parcela | Pontos | Tamanho |
|---|---|---|---|---|
| critérios, cenário principal | 11 ms | 0,3% | 5.570 | 234 KiB |
| densidade, 5.570 municípios, com referencial declarado | 120 ms | 6,3% | 5.570 | 234 KiB |
| densidade, 62 municípios do Amazonas, com referencial | 116 ms | 8,6% | 62 | 4 KiB |

Na densidade, o custo vem da leitura de coordenadas da competência (`territory_coordinates`, do
Bloco 2, um `crosstab` por território). Por isso quase não diminui com menos territórios. Ela não foi
reescrita nem restrita às linhas dos territórios do resultado, porque a verificação do separador
decimal considera a coluna inteira, como nas análises espaciais. Fica registrada como otimização
possível. Nos critérios e na referência mais próxima, a leitura memorizada da própria análise é
reaproveitada (11 ms).

**Latência por operação** (`bench_latency.py --profile real`, mediana de 7):
- variações de −1,6% a +8,5%, sem padrão atribuível ao bloco;
- operações que o bloco não toca (pré-exames, agregação, que não tem mapa) também variam até +7%, o
  que dá a escala do ruído desta máquina;
- nessas requisições não há referencial declarado, então a geometria sai `INDISPONIVEL` sem leitura
  de coordenadas;
- tamanhos de resposta iguais (até +1 KiB) e contagens idênticas.

## 14. Regressão e equivalência

### 14.1. Suítes e jornadas

Execução na mesma sessão sobre o commit `22e1884` mais as mudanças da U5 (`final_regression_b3.sh`):

| Suíte | Resultado |
|---|---|
| pytest backend sintético | 385 aprovados (372 antes do bloco + 13 novos), 29 ignorados (opt-in com dados reais: 27 + 2 novos) |
| pytest com os dados reais (`ADT_REAL_DATA_DIR`) | 414 aprovados, nenhum ignorado (399 antes do bloco + 15 novos) |
| build do frontend (tsc estrito + vite) | aprovado |
| reprodução local do job `ui-block1` (smoke e regressão do Bloco 1, referência mais próxima, critérios, mapa, integração com Gemini simulado) | aprovada |
| reprodução local do job `ui-conversational` | aprovada |
| jornada do Bloco 1 com os dados reais (`ui_block1_smoke`, `ADT_BLOCK1_REAL=1`) | aprovada |
| referência mais próxima no navegador com os dados reais (3, 62 e 5.570 alvos) | aprovada; uma execução por pedido |
| critérios combinados e mapa no navegador com os dados reais | aprovados (seção 13) |

As correções finais de rótulo (seção 14.3) foram validadas depois com nova construção e nova execução
das duas reproduções de CI e da jornada do mapa.

### 14.2. Equivalência das respostas completas da API

Capturas de 76 a 77 casos por catálogo (Bloco 1 sintético, nacional sintético e real), com
identificadores e horários normalizados:

| Comparação | block1 | national | real |
|---|---|---|---|
| × baseline `15aa3c8`, removidos só os acréscimos declarados | 0 diferenças | 0 | 0 |
| × captura anterior ao Bloco 3 (`2d8f7a0`), remoção simétrica | 0 | 0 | 0 |
| × captura anterior ao Bloco 3, **sem remoção**: caminhos diferentes | só `acrescentado $.metadata.representacao` (20 casos de análise) | idem (20) | idem (19) |

Nenhum valor, linha, contagem, classe, motivo ou status mudou: o Bloco 3 só acrescentou
`metadata.representacao`. A chave de execução e o reaproveitamento de resultados idênticos não mudaram.

### 14.3. Defeitos encontrados e corrigidos

1. **Observador de tamanho do mapa depois da troca de aba** (`TypeError: Cannot set properties of
   null`): a notificação do `ResizeObserver` chegava com o canvas desmontado. Corrigido com guarda e
   cancelamento do quadro pendente; coberto pela jornada (falha com qualquer erro de página).
2. **Rótulo do alcance parcial da referência mais próxima:** a primeira versão do painel dizia
   “cobertura parcial aceita explicitamente” também para a referência mais próxima, em que o motor
   informa o mínimo entre as avaliáveis sem aceitação do usuário (RQ-REP-15). Corrigido; a jornada
   confere o rótulo certo e a ausência do rótulo de aceitação.
3. **Corrida no roteiro `ui_block1_integration.py` (anterior ao bloco)**, que derrubou o CI 208: a
   escolha do período dispara novo pré-exame, mas o botão de cálculo fica habilitado por ~8 a 10 ms
   antes de o efeito marcar o pré-exame em curso. Se o roteiro lesse o botão nesse intervalo, a mensagem
   saía durante o pré-exame e recebia 409 (“Aguarde ou repita a validação da base”), o comportamento
   previsto para o usuário.
   - Comprovação independente: linha do tempo registrada na página (habilitado 1.637,9 ms →
     desabilitado 1.645,5 ms → pré-exame de 1.788 a 1.854 ms) e reprodução do mesmo 409 com pré-exame
     retardado.
   - Correção (`22e1884`): o roteiro espera a resposta do pré-exame do período escolhido. Nenhuma
     asserção foi removida ou relaxada.
4. **Ajustes de interface detectados nas jornadas:**
   - competências irmãs não eram reconhecidas quando a preparação acrescentava opções desmarcadas;
   - o indicador das barras não acompanhava o do mapa;
   - a aba Mapa não indicava a indisponibilidade.

### 14.4. Roteiros legados e integridade dos dados

- **Os sete roteiros anteriores à interface conversacional** (`ui_brazil_smoke` e `ui_smoke` com
  dados reais, `ui_session_smoke`, `ui_carousel_smoke`, `ui_audit_smoke`, `ui_preparation_smoke`,
  `ui_integration_smoke`) falham no **mesmo ponto** da etapa anterior (7 de 7). Já falhavam no baseline,
  porque procuram elementos da interface pré-conversacional; nenhum passou a falhar por causa do bloco.
- **SHA-256** de `Dados_Brasil.xlsx`, `Dados_Municipios_Brasil.csv`, `dados/brasil/complemento_coordenadas.json`
  e das cópias do catálogo real: **inalterados** antes e depois de toda a regressão.

### 14.5. CI

- CI 208 (`5709d4a`, U1): falhou só na integração com Gemini simulado, pela corrida do item 14.3.3.
- CI 209 (`5841f55`, U3/U4): todos os jobs aprovados, inclusive a nova jornada do mapa.
- Commit final do bloco (U5): o resultado do CI é confirmado no relatório de entrega, já que a
  confirmação do último commit não pode constar do próprio commit.

## 15. Conformidade com a Parte 13 da SPEC

| Requisito | Situação | Evidência ou lacuna |
|---|---|---|
| CAP-REP-01 Tabela | Atendido no escopo do protótipo | tabelas existentes preservadas e sincronizadas |
| CAP-REP-02 Barras, linhas e série temporal | Atendido no escopo do protótipo | seção 7 |
| CAP-REP-03 Mapa | **Parcial** | pontos com geometria autorizada; sem polígonos nem limites oficiais |
| CAP-REP-04 Painel simples | Atendido no escopo do protótipo | justaposição na página de resultados, sem cálculo entre representações |
| CAP-REP-05 Relatório HTML e PDF | **Parcial** | página de resultados imprimível; sem relatório consolidado próprio nem PDF de servidor |
| CAP-REP-06 CSV | Preservado | sem mudança neste bloco |
| RQ-REP-01 Transformações registradas (EV-REPRESENTACAO) | **Parcial** | `representacao_aplicada` exportado no JSON; não é um evento persistido no servidor |
| RQ-REP-02 Classes só de capacidade | Atendido; faixas de distância (CAP-ESP-03) a confirmar | seção 5 |
| RQ-REP-03 Ordem padrão por código; reordenação visual sem posições | Atendido | seção 7 |
| RQ-REP-04 Não avaliável distinto de zero, com legenda | Atendido para mapa e gráficos | anel vazado, listas à parte |
| RQ-REP-05 Arredondamento de apresentação | Atendido nas representações novas | `formatNumber`, casas extras contra falso zero ou falsa igualdade; tabelas anteriores mantêm a formatação própria |
| RQ-REP-06 Controles não iniciam análise | Atendido | conferido nas jornadas |
| RQ-REP-07 Mapa exige geometria; senão BLQ-DAD | Atendido | seção 3 |
| RQ-REP-08 Painel sem cálculo entre representações | Atendido | inspeção do código |
| RQ-REP-09 Referências, parâmetros e limitações | Parcial | JSON traz origem e limitações; PNG removido da interface; o modo degradado da síntese não foi exercitado neste bloco |
| RQ-REP-10 Tipos admitidos | Atendido; dispersão e bolhas fora | seção 7 |
| RQ-REP-11 Escala e unidade da densidade | Atendido nas representações novas | unidade “por 1.000 habitantes” na legenda, nos eixos e nos detalhes |
| RQ-REP-12 Conteúdo de HTML, PDF e CSV | Parcial | ver CAP-REP-05; CSV sem mudança |
| RQ-REP-13 Visualizador da base | Não tratado neste bloco | — |
| RQ-REP-14 Tipo de contagem agregada nos rótulos | Atendido nas representações de 19/10/2026 | cartão da agregação com o `Tipo` do motor e "soma das contagens dos componentes"; estado "na soma das contagens dos municípios", com textura e aviso de possível dupla contagem (seção 7); a agregação continua sem mapa |
| RQ-REP-15 Qualificadores obrigatórios | Atendido para alcance e vigência nas representações novas | seções 6 e 9 |

## 16. Limitações científicas, pendências e decisões abertas

- **225 × 160 municípios:** o cenário principal produz 225 municípios que atendem; um levantamento
  anterior citado pelo usuário indicava 160. A diferença fica registrada como **questão de
  reconciliação metodológica**. Possíveis fontes, não verificadas:
  - competência e base populacional;
  - definição das referências;
  - distância geodésica direta versus viária;
  - sede municipal versus outra coordenada;
  - aceitação de cobertura parcial;
  - operadores inclusivos ou exclusivos;
  - arredondamento antes da comparação.

  Nada foi ajustado para aproximar os números: limiares, distâncias, referências e universos
  permanecem como pedidos.
- **Distância:** sempre geodésica direta; não representa trajeto, tempo de deslocamento nem
  acessibilidade.
- **Cobertura e elegibilidade:** alcance restrito e elegibilidade confirmada só com aceitação explícita
  e rotulados.
- **Premissa de coordenada fixa** dos seis municípios complementados mantida e explicitada.
- **Sem sugestão normativa:** limiares do cenário (2,36 por 1.000 habitantes; 155 km) são escolhas do
  usuário.
- **Pendências:**
  - limites oficiais de UF e do Brasil e qualquer mapa coroplético (seção 4);
  - dispersão e bolhas, aguardando aprovação humana (seção 7);
  - EV-REPRESENTACAO como evento persistido;
  - relatório consolidado HTML e PDF de servidor;
  - SVG.
- **Observação anterior ao bloco (resolvida em 19/10/2026):** `DistributionResults` (Bloco 1) somava no
  frontend o número de unidades por quintil para o total exibido ("N unidades territoriais avaliadas"). A
  soma saiu: o total é a métrica "Unidades classificadas" do motor ("N unidades territoriais classificadas
  (total do motor)", `distribution-total`), conforme RQ-REP-08. Saiu também o gráfico de contagens repetido.
- O Bloco 3 não criou novos blocos incrementais.
