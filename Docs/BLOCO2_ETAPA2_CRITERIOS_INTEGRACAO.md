# Bloco 2, Etapa 2 — Critérios combinados, réguas, integração e correção geográfica

Branch `feat/novos-blocos-incrementais`, a partir de `efafa01`. Referência metodológica:
`IMPLEMENTATION_SPEC.md` v1.2.4 (CAP-SUB-01/02/03, CAP-ESP-02/03, CAP-DIS-03, RQ-CAP-08,
RQ-RES-06). A integração não declara conformidade integral com a SPEC: o que ficou fora está
na seção 9.

## 1. Situação das unidades

| Unidade | Situação | Commit |
| --- | --- | --- |
| U1 Origem da base Brasil | Concluída | `d6e6394` |
| U2 Camada geográfica complementar | Concluída: mecanismo e coordenadas oficiais incorporadas (camada versão 1) | `8dcb007`, `ec17a10` |
| U3 Critérios combinados | Concluída | `64f7f09` |
| U4 Recortes, rankings e faixas | Concluída (motor em `64f7f09`, interface na U5) | `64f7f09` |
| U5 Interface e conversa | Concluída | `007ba29` |
| U6 Validação, desempenho e documentação | Concluída (seções 7 e 8) | `e3e7f14`, `8005a11` e esta documentação |

**Coordenadas oficiais da U2.** O proxy deste ambiente recusa o acesso a `*.ibge.gov.br`, por isso
o arquivo oficial não foi baixado aqui. O usuário forneceu as coordenadas e a proveniência
extraídas do GeoPackage oficial de Localidades do Censo 2022, e a camada
`dados/brasil/complemento_coordenadas.json` (versão 1, SHA-256
`5db726905a916e43a05ef040ec610941967b85804a481d13920e8f5383dbb4a5`) foi escrita diretamente
segundo o contrato do validador, que a aceita como `valido`. Não houve autenticação independente
do arquivo junto ao servidor do IBGE: a verificação é a do usuário, no exemplar que ele forneceu
(seção 3.5). A pendência geográfica está resolvida: os seis municípios passam a ser avaliáveis
nas análises espaciais da base Brasil municipal.

## 2. Origem da base Brasil (U1)

- **Arquivos usados.** O backend lê diretamente `Dados_Brasil.xlsx` e
  `Dados_Municipios_Brasil.csv` da raiz do repositório. Não há cópia intermediária nem fallback:
  `.local/` não é lida (o teste com uma `.local` antiga e divergente comprova).
- **Integridade.** A cada requisição, tamanho e SHA-256 de cada arquivo são conferidos contra o
  manifesto governado `dados/brasil/manifesto.json` (esquema 1; `versao` = resumo canônico dos dois
  SHA-256, a mesma identidade de versão do Bloco 1). Arquivo alterado, manifesto ausente,
  desatualizado, ilegível ou inconsistente: recusa com motivo explícito; uploads continuam.
- **Cache.** O cache de quadros processados é chaveado por arquivo e versão; trocar a versão
  nunca reaproveita o quadro anterior. Versão inspecionada diferente da analisada é recusada.
- **Pasta externa.** `ADT_BRASIL_DATA_DIR` aponta, de forma explícita, para uma instalação com
  manifesto do instalador. É aceita com a versão governada, ou com outra versão somente quando
  `ADT_BRASIL_DATA_VERSION` a fixa exatamente; caso contrário, recusa.
- **Instalador.** Copia por padrão apenas a versão governada; catálogos sintéticos de teste exigem
  `--permitir-versao-nao-governada` (ou `governed=False`) e fixam a versão.
- **Diagnóstico.** `GET /api/brazil/source` e a área “Diagnóstico técnico da fonte” mostram modo,
  caminhos físicos, versão, versão governada, versão fixada e estado de integridade, sem conteúdo.

Testes: `backend/tests/test_brazil_source.py` (16 casos, inclusive reinício do processo e
ambiente remoto/local simulados por pasta externa).

## 3. Camada geográfica complementar (U2)

### 3.1. Escopo e premissa

Somente os seis municípios autorizados, nas 22 competências (janeiro e junho de 2014 a 2024):
Ananás/TO (170100), Pescaria Brava/SC (421265), Balneário Rincão/SC (422000), Jaraguari/MS
(500490), Campestre da Serra/RS (430367) e Águas de Lindóia/SP (350050) — 132 registros, todos
com latitude inválida na fonte (por exemplo, `-63741`). Premissa metodológica do usuário: uma
coordenada fixa por município em todo o período (`COORDENADA_FIXA_2014_2024`), sem comprovação
independente de estabilidade histórica; não se estende a outros municípios.

### 3.2. Arquivo versionado e validação

`dados/brasil/complemento_coordenadas.json` (versão 1, seção 3.5). Cada leitura
valida: esquema, identificador e versão; versão da fonte municipal a que se aplica (SHA-256);
escopo temporal exatamente igual às 22 competências; premissa; fonte do IBGE (`https://…ibge.gov.br/`),
edição, definição do ponto (sede municipal), referencial declarado como SIRGAS 2000 com evidência
textual do metadado oficial e SHA-256 do arquivo oficial; municípios apenas os autorizados, com
nome, UF e código de 7 dígitos coerentes com o código-base; latitude e longitude finitas e no
intervalo. Camada inválida nunca é aplicada (estado `invalido` com motivo). A versão 1 registra
também o pacote compactado e seu SHA-256, o EPSG 4674, a geometria `POINT`, a origem das
coordenadas (geometria pontual, não os campos auxiliares de latitude e longitude), a classificação
da localidade, o número de registros de sede encontrados (um por município), a declaração de
verificação e `excecoes: []`.

### 3.3. Aplicação e rastreabilidade

A substituição ocorre ao ler coordenadas (`territory_coordinates` e `spatial_data`), nunca nos
arquivos nem no quadro: só para a base Brasil municipal na versão governada indicada pela camada,
só nas 22 competências, só onde o ponto original é inválido e com o nome conferido na própria
base; o ponto é substituído inteiro. Uploads nunca recebem a camada. Linhas e metadados indicam
as coordenadas complementadas (coluna “Coordenada complementada (camada oficial)” e
`complemento_geografico`, que registra também a proveniência oficial: produto, edição, arquivo e
SHA-256 do GeoPackage, referencial, EPSG, ponto e declaração de verificação). A versão da camada
entra na chave de execução das análises espaciais quando válida; análises não espaciais mantêm
chaves e valores. Resultado espacial calculado com outra versão da camada não é retomado nem
reutilizado sem novo cálculo, e uma preparação feita com outra versão é recusada (`geo_version`).
Para um catálogo de outra versão da fonte municipal (por exemplo, os catálogos sintéticos de
teste), a camada válida é registrada como `incompativel` na sobreposição, nos metadados, na
preparação e na chave de execução, que fica igual à de uma base sem camada.

### 3.4. Construtor a partir do arquivo oficial

`backend/build_geo_complement.py` lê o arquivo oficial (GeoPackage: ponto da geometria e
referencial de `gpkg_spatial_ref_sys`, exigindo EPSG:4674; CSV/XLSX: campos de latitude/longitude
e evidência textual do referencial), associa cada município por código (prefixo de 6 dígitos do
código de 7), nome, UF e categoria de sede informada pelo usuário, e registra exceção quando não
há exatamente um registro de sede (sem escolha arbitrária). Sem `--gravar`, só exibe a camada.
A versão 1 não foi gerada pelo construtor, porque o GeoPackage não está disponível neste
ambiente: o usuário autorizou escrever a camada diretamente com os valores e a proveniência que
forneceu. O construtor continua disponível para versões futuras.

Testes: `test_geo_complement.py` (25, inclusive as 22 competências, distâncias conferidas com
geodésica independente, conjuntos de referência e mínimos por período, 12 formas de camada
inválida, versão de fonte diferente, nome conferido na própria base, uploads, identidades e
rastreabilidade) e
`test_build_geo_complement.py` (10, com arquivos sintéticos CSV, XLSX e GeoPackage).

### 3.5. Coordenadas oficiais incorporadas (versão 1)

| Município | UF | Código base | Código IBGE | Latitude | Longitude |
| --- | --- | --- | --- | --- | --- |
| Ananás | TO | 170100 | 1701002 | -6.374096 | -48.070240 |
| Pescaria Brava | SC | 421265 | 4212650 | -28.384400 | -48.866400 |
| Balneário Rincão | SC | 422000 | 4220000 | -28.831000 | -49.231000 |
| Jaraguari | MS | 500490 | 5004908 | -20.102000 | -54.436800 |
| Campestre da Serra | RS | 430367 | 4303673 | -28.799283 | -51.093783 |
| Águas de Lindóia | SP | 350050 | 3500501 | -22.471562 | -46.632068 |

- **Fonte:** IBGE, Censo Demográfico 2022, Localidades do Brasil
  (`https://geoftp.ibge.gov.br/organizacao_do_territorio/estrutura_territorial/localidades/Localidades_do_Brasil/2022/Localidades_Brasil_gpkg.zip`).
- **Arquivos:**
  - `BR_localidades_2022.gpkg`, SHA-256
    `d057a1638b16257f17338ea2b8a4fc1e0b4b4b93012c5a7fa294f44e401e2704`;
  - pacote `Localidades_Brasil_gpkg.zip`, SHA-256
    `1d96d5f0b379972a506d4b18c3696af974fbe59f8f6680557cb3a6dd38a0eb57`;
  - `gpkg_contents.last_change` = 2025-11-14T05:05:46.920Z.
- **Referencial:** SIRGAS 2000, EPSG:4674 (evidência: `gpkg_spatial_ref_sys`).
- **Ponto:** geometria `POINT` da sede municipal (`CT_LOCALIDADE` = Cidade; `SCT_LOCALIDADE` =
  Sede Municipal), não os campos auxiliares de latitude e longitude. Há exatamente um registro de
  sede por município.
- **Verificação:** extração e conferência pelo usuário no exemplar do GeoPackage que ele
  forneceu. **Não houve autenticação independente do arquivo junto ao servidor do IBGE.**
- **Premissa:** `COORDENADA_FIXA_2014_2024`, decisão metodológica do usuário: um único ponto por
  município nas 22 competências. Não é comprovação de estabilidade histórica.

**22 competências (dados reais).**

- **Base original:** em cada competência, exatamente os seis municípios têm ponto inválido, e
  nenhum outro. Nome e UF conferem nos 132 registros.
- **Com a camada:** os 132 registros (6 por competência) recebem o ponto oficial, e todos os
  demais pontos continuam os originais da própria competência. Em cada competência, as distâncias
  de todos os municípios aos seis são iguais às de uma busca geodésica exaustiva independente
  sobre as coordenadas efetivas.

**Junho de 2024** (MEDICINA, todos os municípios, referências com densidade ≥ 2,36, distância
geodésica). Valores da API iguais ao recálculo independente: CSV bruto, frações exatas e 22,3
milhões de geodésicas na busca exaustiva.

| Medida | Base original, sem complemento | Efetivo, com a camada |
| --- | --- | --- |
| Referências (densidade ≥ 2,36) | 2.007 | 2.007 |
| Referências com coordenada avaliável | 2.003 (4 inválidas) | 2.007 (4 complementadas) |
| Alvos com coordenada avaliável | 5.564 (6 inválidos) | 5.570 (6 complementados) |
| Alvos com mínimo do conjunto completo | 0 | 5.570 |
| Alvos com mínimo só entre as referências avaliáveis | 5.564 | 0 |
| Alvos não avaliáveis | 6 (`COORDENADA_INVALIDA`) | 0 |
| Limitações da referência mais próxima | `COBERTURA_PARCIAL`, `UNIDADES_NAO_AVALIAVEIS`, `DISTANCIA_GEODESICA_DIRETA` | `DISTANCIA_GEODESICA_DIRETA` |

As quatro referências complementadas são a mais próxima de 7 alvos: elas próprias, com distância
zero, e 3 outros municípios, cuja distância diminuiu.

**Critério densidade < 2,36 E distância > 155 km** (3.563 municípios com densidade < 2,36):

| Execução | ATENDE | NAO_ATENDE | NAO_AVALIAVEL | Desfecho |
| --- | --- | --- | --- | --- |
| Base original, sem aceitação | 0 | 2.007 | 3.563 (3.561 por dependência não avaliável, 2 por coordenada inválida) | `RES-VAZ` |
| Base original, cobertura parcial aceita | 225 | 5.343 | 2 (`COORDENADA_INVALIDA`) | `RES-LIM` |
| Efetivo, com a camada (com ou sem aceitação) | 225 | 5.345 | 0 | `RES-LIM` (só `DISTANCIA_GEODESICA_DIRETA`) |

Na comparação com a base original com cobertura parcial aceita:

- 2 municípios passam de `NAO_AVALIAVEL` a `NAO_ATENDE`: são os dois complementados com
  densidade < 2,36, e ambos estão a até 155 km de uma referência;
- 3 alvos têm distância menor, sem mudança de estado;
- nenhum outro estado muda.

A distância passa a ser afirmada entre todas as referências elegíveis, sem cobertura parcial nem
aceitação. Resultados não espaciais (quantitativos, população, densidades e períodos) não mudam
(seção 8).

## 4. Critérios combinados (U3)

Operação do motor `criteria` (fora do contrato do LLM, como `nearest`). Atributos por território,
na competência e na categoria escolhidas: densidade por 1.000 habitantes, quantidade, população,
distância à referência mais próxima, pertença a uma lista de territórios e UF (regra governada do
código IBGE; em bases importadas fica `NAO_AVALIAVEL`/`SIGNIFICADO_NAO_ESTABELECIDO`). Operadores
`<`, `≤`, `>`, `≥`, `=`, `≠` e pertença; composição E, OU e NÃO com as regras de CAP-SUB-01
(`ATENDE OU NAO_AVALIAVEL = ATENDE`; `NAO_ATENDE E NAO_AVALIAVEL = NAO_ATENDE`;
`ATENDE E NAO_AVALIAVEL = NAO_AVALIAVEL`; NÃO preserva `NAO_AVALIAVEL`).

- **Precisão.** Comparações exatas em frações racionais sobre os valores completos (densidade como
  `q × 1.000 / p`; distância pelo valor em km calculado); conversões de unidade exatas (km/m;
  por 1.000, 10.000 ou 100.000 habitantes). Sem arredondamento nem tolerância.
- **Por território e por nó:** estado, valor, motivos específicos nas folhas
  (`DADO_AUSENTE`, `DENOMINADOR_AUSENTE`, `DENOMINADOR_ZERO`, `SEM_REGISTRO_OBSERVADO`,
  `COORDENADA_INVALIDA`, `SEM_INFORMACAO_ESPACIAL`, `DEPENDENCIA_NAO_AVALIAVEL` com causas de
  origem) e `DEPENDENCIA_NAO_AVALIAVEL` no composto indeterminado; composto decidido não recebe
  motivo, mas as avaliações dos operandos são conservadas. Várias causas são todas preservadas.
- **Conjuntos e desfecho.** ATENDE, NAO_ATENDE e NAO_AVALIAVEL distintos, com contagens; RES-VAZ
  com avaliáveis e ATENDE vazio; sem avaliáveis, BLQ-DEP se o conjunto de referências vazio está
  entre as causas de todos os territórios (como na Etapa 1) e BLQ-DAD nos demais casos.
- **Critérios sucessivos** formam E sobre o universo de origem; o resultado não depende da ordem.
- **Distância** reaproveita CAP-ESP-02 (mesma busca geodésica exata da Etapa 1, sem refazê-la):
  `minimo_completo` quando avaliável; `minimo_avaliaveis` somente com aceitação explícita
  (`distance_scope`), rotulado “entre as referências avaliáveis (cobertura parcial)”.
- **Elegibilidade desconhecida (§4.4).** Candidatos a referência cujo critério não pôde ser
  avaliado não são tratados como inelegíveis: sem a aceitação explícita de restringir a afirmação
  às referências confirmadas (`eligibility_scope`), a condição de distância fica
  `NAO_AVALIAVEL`/`DEPENDENCIA_NAO_AVALIAVEL`, e a lógica de três estados decide se isso afeta o
  resultado. Ficam registradas separadamente a cobertura da avaliação do critério de elegibilidade,
  a cobertura geográfica do conjunto elegível e o alcance da afirmação. Não há inferência por
  limites (F-09 não incorporada).
- **Alvos e referências independentes.** O universo selecionado não reduz o conjunto de referências.
- **Pré-condições.** Colunas de quantitativo/população exigidas só quando as condições as usam;
  população ausente ou quantitativo ausente bloqueiam com motivo; denominador e unidade de contagem
  confirmados; expressões livres e campos desconhecidos são recusados.

## 5. Ordenação, seleção por posição, faixas e comparação (U4)

- **CAP-SUB-02.** Ordenação por densidade, quantidade, população ou distância, com direção sempre
  escolhida pelo usuário; valores iguais compartilham posição (1, 2, 2, 4) pela comparação exata;
  não avaliáveis em lista separada; por padrão sobre o conjunto que atende aos critérios.
- **CAP-SUB-03.** N primeiros com todos os empatados na posição N (limitação `EMPATE_NO_CORTE`
  com N efetivo); com N exato e empate, pendência com pergunta, sem desempate.
- **CAP-DIS-03/CAP-ESP-03.** Faixas só com limites do usuário, `[a, b)` com o último intervalo
  fechado; contagem por faixa, pertença, fora de todas e não avaliáveis à parte.
- **Comparação de conjuntos** com uma definição anterior no mesmo contexto (competência,
  categoria, universo e referências): em ambos, só no atual, só no anterior e indeterminados
  (não avaliável em algum dos dois nunca é tratado como fora).
- **Reutilização.** O conjunto que atende ou os selecionados viram seleção territorial (análises
  do Bloco 1 e alvos do Bloco 2) ou lista de referências.

## 6. Interface e conversa (U5)

- **Cartão “Critérios combinados”** na mesma página e no mesmo fluxo da conversa. O construtor
  mostra a combinação atual e, para cada condição, uma régua com indicador, unidade, operador,
  valor, universo, competência/categoria e origem “escolha do usuário”. Nenhum operador ou valor
  é pré-selecionado; a régua deslizante só aparece depois de um resultado, posicionada na faixa
  observada (rotulada como não sendo ponto de corte). NÃO por condição; nova condição com E ou OU.
- **Ordenação, N primeiros e faixas** em áreas expansíveis; aceitações explícitas da cobertura
  parcial e da restrição às referências confirmadas só aparecem quando há distância.
- **Resultados.** Contagens; filtros Atendem / Não atendem / Não avaliáveis / Todos /
  Selecionados; tabela com estado e valor de cada condição, motivos e posição; exportação do
  recorte filtrado e da tabela completa (CSV) e do método e parâmetros (JSON integral); alcance da
  distância e coberturas; faixas; comparação; reutilização.
- **Parâmetros alterados** tornam o resultado exibido “não vigente” até nova execução validada
  pelo motor; respostas de pedidos anteriores são descartadas se o contexto mudou; resultado
  idêntico do histórico é recuperado sem recalcular; retomar o histórico restaura critérios,
  ordenação, faixas, aceitações e referências.
- **Conversa.** Canal determinístico (`backend/criteria_conversation.py`), consultado antes do LLM:
  “Mostre os municípios com menos de 2 médicos por mil habitantes” → densidade `<` 2 por 1.000
  habitantes; “Agora considere também distância superior a 150 km” → E com a condição anterior
  (sem escolher referências); “Ordene esses municípios pela distância” → pergunta a direção;
  “Mostre os 20 primeiros” → N primeiros com empates no corte; “Compare esse conjunto com o
  anterior” → comparação com o resultado anterior compatível. O operador adotado é sempre
  explicitado; ambiguidade material vira pergunta (quantidade ou densidade, separador de milhar,
  direção, várias condições numa mensagem). O LLM não recebe a capacidade nem seus estados.

## 7. Desempenho (U6)

Dados reais, competência 202406, 5.570 municípios; cenário do pedido do usuário (valores não
normativos): referências com densidade ≥ 2,36 (2.007), critérios densidade < 2,36 E distância
> 155 km com a cobertura parcial aceita, ordenação decrescente pela distância e 20 primeiros.

**Fases no servidor** (`backend/tests/bench_criteria.py`; mediana de 3; fora de uma requisição,
portanto sem a memorização por requisição):

| Fase | Tempo |
| --- | --- |
| Preparação: leitura e conferência das fontes (quadro em cache) | 0,33 s |
| Preparação: pré-exame de todas as capacidades | 3,74 s |
| Formação do conjunto de referências | 0,63 s |
| Distâncias (busca exata: 22.256 geodésicas em vez de 11.144.692 pares) | 0,93 s |
| Avaliação dos critérios combinados | 0,31 s |
| Ordenação e 20 primeiros | 0,004 s |
| Serialização da resposta (6,5 milhões de caracteres) | 0,23 s |

Requisição completa pela API: 5,66 s (6,34 MB); repetida mudando só o limiar de densidade: 5,63 s.
Na mesma requisição, referências e coordenadas são calculadas uma vez e compartilhadas entre o
pré-exame e o cálculo, e uma única busca geodésica serve a condição de distância, a ordenação, as
faixas e a comparação. Entre requisições, a reutilização das distâncias pouparia cerca de 1,5 s
(referências e distâncias, 28% da requisição) quando só um limiar derivado muda; como a latência
ficou no patamar das demais análises e um cache entre requisições exigiria invalidação por versão
dos dados, camada geográfica, referências, competência e formato das coordenadas, ele não foi
criado (não há necessidade comprovada); fica como proposta.

**Navegador** (`backend/tests/bench_ui_criteria.py`, mesmo método da Etapa 1, clique duplo com uma
única execução):

| Caso | Requisição | Resposta → tabela | Tarefas longas (maior) | Bloqueio acima de 50 ms | Digitação após o resultado |
| --- | --- | --- | --- | --- | --- |
| Densidade e distância, todos os municípios | 5,8 s | 396 ms | 2 (167 ms) | 161 ms | 15 ms |
| Com ordenação e 20 primeiros | 7,1 s | 384 ms | 9 (110 ms) | 329 ms | 19 ms |

Referência da Etapa 1 com 5.570 alvos: resposta → tabela 760 ms, maior tarefa longa 318 ms.

**Sem reintrodução de latência no Bloco 1** (`bench_latency.py --profile real`, 5 repetições;
entre parênteses, o resultado final da otimização de latência): exame municipal 7,83 s (7,70);
pré-exame com período 2,26 s (2,62); densidade sem seleção 3,38 s (3,73); densidade com seleção do
AM 2,47 s (2,71); comparação, evolução e agregação de 3 municípios 2,49–2,62 s (2,75–2,78).

**Transporte.** A resposta de 6,34 MB tem 3,59 MB de linhas da tabela (exportação integral),
1,71 MB de avaliações por território e 1,09 MB de membros do universo (metadado preexistente de
todas as análises). Compressão gzip reduziria a 0,67 MB (nível 1, 30 ms) ou 0,52 MB (nível 9,
231 ms); localmente o ganho de tempo é nulo, por isso fica como recomendação para a implantação
(normalmente no proxy reverso), sem retirar metadados nem alterar as exportações.

**Com a camada oficial.** As medições foram feitas na mesma sessão, alternando a árvore anterior
(`82199e7`, sem a camada) e a atual, duas rodadas cada. Os números absolutos desta sessão são
menores que os da tabela acima, medidos em outro momento do ambiente.

| Medida | Sem a camada | Com a camada |
| --- | --- | --- |
| Requisição completa dos critérios (mesmo cenário) | 2,53–2,68 s (6,34 MB) | 2,61–2,62 s (6,12 MB) |
| Pré-exame sem período, vírgula declarada | 2,66–3,05 s | 2,71–2,74 s |
| Pré-exame de junho de 2024 | 0,83–0,88 s | 0,83–0,88 s |
| Espacial de junho de 2024, todos os municípios | recusada (pontos inválidos) | 1,60–1,66 s |
| Bloco 1, `bench_latency.py --profile real` | — | 13 operações sem diferença além da variação entre repetições |

- **Fases** (`bench_criteria.py`): distâncias 0,49–0,50 s (antes 0,53–0,59), com 22.280
  geodésicas em vez de 22.256, para 11.178.990 pares avaliáveis.
- **Navegador, critérios:** resposta → tabela em 189 ms (295 ms com ordenação e 20 primeiros);
  digitação a 4–5 ms.
- **Navegador, referência mais próxima com todos os municípios:** 5.570 mínimos completos;
  resposta → tabela em 316 ms.

**Duas correções desta medição.**

- A sobreposição normalizava o nome de todas as linhas para conferir os seis municípios. Agora só
  as linhas candidatas são normalizadas: o custo caiu de 270 ms para 42 ms nas 22 competências e
  de 17 ms para 6 ms em uma. Antes da correção, o pré-exame sem período ficava 0,35–0,4 s mais
  lento com a camada.
- O roteiro das fases (`bench_criteria.py`) passou a associar ao quadro a identidade da origem,
  como faz a API. Sem ela, as fases medidas fora da requisição não aplicavam a camada.

## 8. Validação e regressão (U6)

**Testes novos** (todos com bases sintéticas geradas em tempo de teste, salvo os reais opt-in):

| Arquivo | Casos | Cobertura principal |
| --- | --- | --- |
| `test_brazil_source.py` | 16 | Origem, manifesto, cópias antigas, reinício, pasta externa, uploads independentes |
| `test_geo_complement.py` | 25 | Camada: 22 competências, geodésica independente, inválidas, nome conferido na própria base, identidades (inclusive `incompativel` para outra versão da fonte, com chave inalterada), proveniência nos resultados, critérios com distância |
| `test_build_geo_complement.py` | 10 | Construtor: CSV, XLSX, GeoPackage, exceções, referencial não comprovado |
| `test_combined_criteria.py` | 40 | Critério único, E/OU/NÃO, limites exatos, incompatíveis, população e quantitativos ausentes, referências vazias e não avaliáveis, elegibilidade desconhecida, cobertura parcial aceita e não aceita, ordem, empates, ranking, N primeiros, faixas, comparação, mudança de parâmetros, retomada, exportação, unidades |
| `test_criteria_conversation.py` | 31 | Os cinco comandos, vocabulário de operadores, unidades, ambiguidades, outros canais intactos, LLM sem a capacidade |
| `test_nearest_real_data.py` (cenários novos) | 4 | Dados reais, base original sem complemento (camada desconsiderada no teste) e efetivo com a camada: densidade < 2,36 E distância > 155 km; conjunto de referências e mínimos de junho de 2024 por busca exaustiva; 22 competências (132 registros) |
| `test_real_data.py` (cenário novo) | 1 | Análise espacial da base completa com a camada, geodésica independente e rastreio; o mesmo recorte importado segue recusado |
| `ui_criteria_smoke.py` | jornada | Desktop e celular: comandos, ambiguidade, régua, filtro e atualização, exploração, reutilização, histórico, exportações, clique duplo, troca de recorte |

**Regressão completa** (árvore de `007ba29` com a correção da troca de recorte e os testes desta
seção):

| Verificação | Resultado |
| --- | --- |
| pytest do backend (sintético) | 371 passaram; 23 reais omitidos (opt-in) |
| pytest completo com as fontes reais (`ADT_REAL_DATA_DIR`) | 394 passaram |
| TypeScript + Vite build | passou |
| Job `ui-block1` reproduzido (smoke, regressão, mais próxima, critérios, integração com Gemini simulado) | passou |
| Job `ui-conversational` reproduzido | passou |
| Jornada do Bloco 1 com dados reais | passou |
| Referência mais próxima e critérios no navegador com dados reais | passaram |
| Equivalência das respostas da API com o baseline `15aa3c8` (Bloco 1, nacional sintética, real) | 76, 76 e 77 casos; **0 diferenças** além das capacidades acrescentadas |
| SHA-256 dos originais e das cópias de teste | inalterados |
| Sete roteiros legados (anteriores à interface conversacional) | continuam falhando, **no mesmo passo** da Etapa 1 e do baseline `a202be1`; nenhuma falha nova |

**Regressão da integração das coordenadas oficiais** (commits `ec17a10` a `ffdfdef`):

| Verificação | Resultado |
| --- | --- |
| pytest do backend (sintético) | 372 passaram; 27 reais omitidos (opt-in) |
| pytest completo com as fontes reais (`ADT_REAL_DATA_DIR`) | 399 passaram |
| TypeScript + Vite build | passou |
| Jobs `ui-block1` e `ui-conversational` reproduzidos | passaram |
| Jornadas com dados reais (Bloco 1, referência mais próxima, critérios) | passaram; critérios com 225 que atendem e referência mais próxima com 5.570 mínimos completos, como no recálculo independente |
| Equivalência com o baseline `15aa3c8` (Bloco 1, nacional sintética, real) | 76, 76 e 77 casos; **0 diferenças** além das capacidades acrescentadas |
| Comparação integral com as capturas da Etapa 2 sem a camada | só muda a identidade da camada (ver abaixo); linhas e chaves de execução iguais |
| Sete roteiros legados | 7 de 7 falham no mesmo ponto da Etapa 2 |
| SHA-256 dos originais e das cópias de teste | inalterados |

Na comparação integral com as capturas da Etapa 2:

- **Catálogos sintéticos:** em 3 casos por catálogo, a camada passa de `ausente` a
  `incompativel`, com sua identidade.
- **Catálogo real:** em 2 casos de exame, a camada passa de `ausente` a `valido`.
- **Resultados não espaciais:** nenhum muda, inclusive densidades, quantitativos, populações e
  períodos.
- **Caso espacial do roteiro de equivalência:** é recusado igualmente nas três versões, por não
  declarar a vírgula decimal; os efeitos espaciais da camada são verificados pelos testes reais.

Cenário real de junho de 2024 (densidade ≥ 2,36 para as referências; densidade < 2,36 E distância
> 155 km): resultados da base original sem complemento e resultados efetivos com a camada oficial
na seção 3.5. Os testes reais afirmam os dois separadamente, sem alterar os valores de referência
da base original.

Regressões encontradas e corrigidas durante a etapa: teste que percorre todas as operações sem o
parâmetro obrigatório da nova operação (parâmetro fornecido, sem remover asserções); papel de
quantitativo exigido além do contrato do pré-exame; desfecho BLQ-DEP aplicado a coordenadas
inválidas de referência (alinhado à Etapa 1: BLQ-DAD); unidade do cabeçalho com limiar em metros;
direção de ordenação assumida como crescente (agora sempre escolhida); condição pedida na conversa
perdida ao voltar do recorte nacional (agora aplicada depois do novo exame municipal). Na
integração das coordenadas oficiais: a identidade da camada aparecia como `valido` nos metadados e
na chave de execução de catálogos de outra versão da fonte, embora a camada não fosse aplicada;
agora é `incompativel`, coerente com a sobreposição (teste que falha sem a correção).

## 9. Decisões, pendências e limitações

- Coordenadas oficiais dos seis municípios **incorporadas** (seção 3.5); a pendência geográfica
  está encerrada. Permanecem como limitações: a premissa do usuário de uma coordenada fixa em
  2014–2024, que não comprova estabilidade histórica; a ausência de autenticação independente do
  GeoPackage junto ao servidor do IBGE; e a regra de que bases importadas não recebem o
  complemento.
- Distância geodésica direta (sem trajeto viário, tempo ou acessibilidade); referencial SIRGAS 2000
  declarado pelo usuário para a base, pois a fonte não o declara.
- Quantidade e densidade nos critérios usam a coluna de quantitativos (contagem por identificador
  individual não habilitada nesta etapa, como no critério de referências da Etapa 1).
- UF pela regra governada do código IBGE apenas na base Brasil municipal.
- Comparação de conjuntos restrita ao mesmo contexto; contextos diferentes exigem nova execução.
- F-09 (inferência por limites) não incorporada; nenhuma regra de desempate autorizada.
