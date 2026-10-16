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
| `tabela` | `rows` ou `detail_rows` (distribuição) |
| `vinculo` | coluna que identifica o território e a chave estável (`rotulo`, `codigo` ou `nome`) |
| `indicadores` | colunas representáveis do resultado: `coluna`, `rotulo`, `tipo` (`CONTINUO`, `CONTAGEM`, `POSICAO`, `CLASSE`, `ESTADO`), `unidade`, `origem` (capacidade), `classes` produzidas por capacidade, `nota` (TPL-11 para distâncias) |
| `serie` | descritor de série já calculada (competência, território, categoria, valor, unidade); só com duas ou mais competências |
| `geometria` | `DISPONIVEL`: `ids`, `lat`, `lon` (arrays paralelos), `competencia`, `referencial`, `fonte`, `configuracao_apresentacao` (origem e premissa contextual, quando usada), `complementados`, `sem_geometria` [{id, condição, motivo, texto}] e identidade da camada complementar (arquivo, SHA-256, identificador, versão, premissa, proveniência). `INDISPONIVEL`: desfecho `BLQ-DAD`, motivo e pendência (`REFERENCIAL_GEODESICO`, `REFERENCIAL_NAO_SUPORTADO`, `SEPARADOR_DECIMAL`, `PAPEIS_COORDENADAS`, `COMPETENCIA_UNICA`, `COORDENADAS_NAO_ASSOCIADAS`, `CONFIRMACAO`). `NAO_APLICAVEL`: agregação, rotatividade, evolução temporal (várias competências) |
| `notas` | coordenadas complementadas, territórios fora do mapa, TPL-11 |

- **Autorização da geometria informada** pela regra das análises espaciais: referencial suportado
  (SIRGAS2000, sem transformação), papéis de latitude e longitude estabelecidos, separador decimal
  declarado e camada complementar governada. Referência mais próxima e critérios com distância usam
  exatamente a leitura memorizada da própria análise (`nearest_inputs`); análise espacial usa o seu
  recorte; as demais usam a competência única do resultado. Várias competências → `COMPETENCIA_UNICA`
  (as coordenadas podem mudar entre competências e não são intercambiáveis).
- **Configuração contextual Brasil:** somente quando a fonte é Brasil, o perfil canônico é reconhecido, a integridade está verificada e a versão efetiva coincide com a governada. Sem CRS informado, a configuração de apresentação utiliza SIRGAS2000 e o formato decimal da fonte (vírgula, salvo opção explícita). É uma premissa ilustrativa autorizada para o desenho dos pontos nesta alteração; **não certifica o datum original**, ausente na fonte. A origem e a premissa ficam em `geometria.configuracao_apresentacao`, na tela e no JSON. Não altera opções, pré-exame, distância nem chave de execução. Referencial explícito não suportado continua bloqueado. Uploads e versões externas diferentes continuam exigindo informação de origem; não há padrão universal. Os cálculos espaciais mantêm sua exigência independente de referencial autorizado.
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
  com condição e motivo.
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
  linear entre o menor e o maior valor do resultado, com unidade e intervalo na legenda e o aviso “a
  cor não é classe nem limiar”; **nenhum quantil, faixa ou classe criada no frontend.**
- **Não avaliável:** anel vazado cinza, nunca preenchido como zero, com legenda.
- **Referências:** losangos; esmaecidas quando fora do filtro e sem ligação.
- **Ligações:** tracejadas, só para até 30 territórios selecionados, rotuladas “ligação ilustrativa
  (não é trajeto)”.
- **Dica** contida na área do mapa; legenda como região própria (“Legenda do mapa”).
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
  - quantitativos com unidade pessoas e escopo FTS confirmado usam “profissionais” apenas no rótulo de apresentação; a unidade metodológica original é preservada;
  - resultados com série temporal usam linhas, evitando representar a primeira competência como se fosse todo o resultado;
  - a distribuição inclui na aba Gráficos as frequências dos grupos calculados pelo motor.
- **Linhas:**
  - só para séries já calculadas pelo motor (evolução temporal; competências da própria série, sem
    presumir 22 períodos);
  - lacunas preservadas (`connectNulls=false`), sem tendência nem taxas novas;
  - uma única competência não forma série;
  - todos os territórios ou a seleção explícita, com páginas de oito na ordem dos dados; navegação mostra o intervalo e o total, sem amostragem.
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

Cada coluna permite busca por texto sem distinguir acentos e comparações numéricas (`>`, `<`, `>=`, `<=`, `=`), com ponto ou vírgula decimal. Ausências não atendem comparações numéricas. A ordenação é apenas visual e não modifica as posições calculadas. Páginas de 150 dão acesso a todos os registros; o CSV da tabela exporta **todo** o filtro, em precisão integral, sem ficar limitado à página. O CSV superior exporta o resultado original. Filtros por coluna não alteram mapa, gráficos ou preparação; o filtro visual comum segue separado e explícito.

## 9. Painel integrado, histórico e competências (U4)

- **Abas:** Mapa, Gráficos e Tabela, dentro do resultado no painel de análise, ao lado da conversa no computador. A aba
  Mapa indica “(indisponível)” ou “(não aplicável)” quando não há geometria, e o motivo fica a um
  clique, sem esconder tabela e gráficos.
- **Histórico:** cada resultado é reconstruído com os próprios dados, parâmetros, origem, versão da
  camada e limitações (`metadata.representacao` do resultado). Aviso em linguagem comum identifica a consulta a uma análise anterior e orienta revisar a preparação para atualizar; resultado invalidado fica só para consulta, sem reutilização da
  seleção. A compatibilidade de fonte e camada segue a regra existente (`compatible`).
  - **Atualização (16/10/2026):** o painel recolhido “Histórico de análises” fica sempre acessível no topo da área de análise, inclusive com zero ou um cálculo. Reabrir alterna o resultado à direita sem deslocar o compositor do chat. O controle antigo de histórico foi removido no commit `dbaa0bd`: a lista "Histórico de resultados" e o controle de
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
  valor listados.
- **Celular:** sem rolagem horizontal da página a 390 px, mapa com 360 px de altura, seletores em
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
| RQ-REP-14 Tipo de contagem agregada nos rótulos | Sem mudança | agregação não tem mapa; rótulos herdados |
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
- **Observação anterior ao bloco:** `DistributionResults` (Bloco 1) soma no frontend o número de
  unidades por quintil para o total exibido. Não foi alterado; fica registrado para revisão diante de
  RQ-REP-08.
- O Bloco 3 não criou novos blocos incrementais.
