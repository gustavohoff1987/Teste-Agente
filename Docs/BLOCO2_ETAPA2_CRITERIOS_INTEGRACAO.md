# Bloco 2, Etapa 2 — Critérios combinados, réguas, integração e correção geográfica

Branch `feat/novos-blocos-incrementais`, a partir de `efafa01`. Referência metodológica:
`IMPLEMENTATION_SPEC.md` v1.2.4 (CAP-SUB-01/02/03, CAP-ESP-02/03, CAP-DIS-03, RQ-CAP-08,
RQ-RES-06). A integração não declara conformidade integral com a SPEC: o que ficou fora está
na seção 9.

## 1. Situação das unidades

| Unidade | Situação | Commit |
| --- | --- | --- |
| U1 Origem da base Brasil | Concluída | `d6e6394` |
| U2 Camada geográfica complementar | Mecanismo concluído; **coordenadas oficiais não obtidas** (rede) | `8dcb007` |
| U3 Critérios combinados | Concluída | `64f7f09` |
| U4 Recortes, rankings e faixas | Concluída (motor em `64f7f09`, interface na U5) | `64f7f09` |
| U5 Interface e conversa | Concluída | `007ba29` |
| U6 Validação, desempenho e documentação | Concluída (seções 7 e 8) | `e3e7f14`, `8005a11` e esta documentação |

**Bloqueio específico da U2.** O proxy deste ambiente recusa `CONNECT` para todos os hosts
`*.ibge.gov.br` (HTTP 403 na política de rede; verificado em 13/10/2026 em `geoftp.ibge.gov.br`,
`www.ibge.gov.br` e `servicodados.ibge.gov.br`). Sem o arquivo oficial de Localidades do Censo
2022, nenhuma coordenada foi incorporada e nenhuma foi inventada: o arquivo
`dados/brasil/complemento_coordenadas.json` não existe, e os seis municípios continuam não
avaliáveis nas análises espaciais (`COORDENADA_INVALIDA`). Remédio: incluir
`geoftp.ibge.gov.br` nos domínios permitidos do ambiente e executar o construtor da seção 3.4.

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

`dados/brasil/complemento_coordenadas.json` (inexistente enquanto durar o bloqueio). Cada leitura
valida: esquema, identificador e versão; versão da fonte municipal a que se aplica (SHA-256);
escopo temporal exatamente igual às 22 competências; premissa; fonte do IBGE (`https://…ibge.gov.br/`),
edição, definição do ponto (sede municipal), referencial declarado como SIRGAS 2000 com evidência
textual do metadado oficial e SHA-256 do arquivo oficial; municípios apenas os autorizados, com
nome, UF e código de 7 dígitos coerentes com o código-base; latitude e longitude finitas e no
intervalo. Camada inválida nunca é aplicada (estado `invalido` com motivo).

### 3.3. Aplicação e rastreabilidade

A substituição ocorre ao ler coordenadas (`territory_coordinates` e `spatial_data`), nunca nos
arquivos nem no quadro: só para a base Brasil municipal na versão governada indicada pela camada,
só nas 22 competências, só onde o ponto original é inválido e com o nome conferido na própria
base; o ponto é substituído inteiro. Uploads nunca recebem a camada. Linhas e metadados indicam
as coordenadas complementadas (coluna “Coordenada complementada (camada oficial)” e
`complemento_geografico`). A versão da camada entra na chave de execução das análises espaciais
quando válida; análises não espaciais mantêm chaves e valores. Resultado espacial calculado com
outra versão da camada não é retomado nem reutilizado sem novo cálculo, e uma preparação feita com
outra versão é recusada (`geo_version`).

### 3.4. Construtor a partir do arquivo oficial

`backend/build_geo_complement.py` lê o arquivo oficial (GeoPackage: ponto da geometria e
referencial de `gpkg_spatial_ref_sys`, exigindo EPSG:4674; CSV/XLSX: campos de latitude/longitude
e evidência textual do referencial), associa cada município por código (prefixo de 6 dígitos do
código de 7), nome, UF e categoria de sede informada pelo usuário, e registra exceção quando não
há exatamente um registro de sede (sem escolha arbitrária). Sem `--gravar`, só exibe a camada.

Testes: `test_geo_complement.py` (24, inclusive as 22 competências, distâncias conferidas com
geodésica independente, conjuntos de referência e mínimos por período, 12 formas de camada
inválida, versão de fonte diferente, uploads, identidades e rastreabilidade) e
`test_build_geo_complement.py` (10, com arquivos sintéticos CSV, XLSX e GeoPackage).

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

## 8. Validação e regressão (U6)

**Testes novos** (todos com bases sintéticas geradas em tempo de teste, salvo os reais opt-in):

| Arquivo | Casos | Cobertura principal |
| --- | --- | --- |
| `test_brazil_source.py` | 16 | Origem, manifesto, cópias antigas, reinício, pasta externa, uploads independentes |
| `test_geo_complement.py` | 24 | Camada: 22 competências, geodésica independente, inválidas, identidades, critérios com distância |
| `test_build_geo_complement.py` | 10 | Construtor: CSV, XLSX, GeoPackage, exceções, referencial não comprovado |
| `test_combined_criteria.py` | 40 | Critério único, E/OU/NÃO, limites exatos, incompatíveis, população e quantitativos ausentes, referências vazias e não avaliáveis, elegibilidade desconhecida, cobertura parcial aceita e não aceita, ordem, empates, ranking, N primeiros, faixas, comparação, mudança de parâmetros, retomada, exportação, unidades |
| `test_criteria_conversation.py` | 31 | Os cinco comandos, vocabulário de operadores, unidades, ambiguidades, outros canais intactos, LLM sem a capacidade |
| `test_nearest_real_data.py` (novo cenário) | 1 | Dados reais, junho de 2024: densidade < 2,36 E distância > 155 km, com recálculo independente |
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

Cenário real de junho de 2024 com densidade ≥ 2,36 reexecutado **sem** a camada (ainda
inexistente): 2.007 referências; nenhum alvo com mínimo do conjunto completo, porque há
referências sem coordenada válida; 5.564 com mínimo entre as referências avaliáveis; 6 não
avaliáveis (`COORDENADA_INVALIDA`). Critérios densidade < 2,36 E distância > 155 km: sem aceitação,
nenhum município atende (a distância não é afirmada) e os de densidade ≥ 2,36 não atendem; com a
cobertura parcial aceita, 225 atendem, 5.343 não atendem e 2 não são avaliáveis.

Regressões encontradas e corrigidas durante a etapa: teste que percorre todas as operações sem o
parâmetro obrigatório da nova operação (parâmetro fornecido, sem remover asserções); papel de
quantitativo exigido além do contrato do pré-exame; desfecho BLQ-DEP aplicado a coordenadas
inválidas de referência (alinhado à Etapa 1: BLQ-DAD); unidade do cabeçalho com limiar em metros;
direção de ordenação assumida como crescente (agora sempre escolhida); condição pedida na conversa
perdida ao voltar do recorte nacional (agora aplicada depois do novo exame municipal).

## 9. Decisões, pendências e limitações

- Coordenadas oficiais dos seis municípios **pendentes** (seção 1); até lá, as análises espaciais
  da base completa os mantêm não avaliáveis, e a distância só é afirmada entre as referências
  avaliáveis mediante aceitação explícita.
- Distância geodésica direta (sem trajeto viário, tempo ou acessibilidade); referencial SIRGAS 2000
  declarado pelo usuário para a base, pois a fonte não o declara.
- Quantidade e densidade nos critérios usam a coluna de quantitativos (contagem por identificador
  individual não habilitada nesta etapa, como no critério de referências da Etapa 1).
- UF pela regra governada do código IBGE apenas na base Brasil municipal.
- Comparação de conjuntos restrita ao mesmo contexto; contextos diferentes exigem nova execução.
- F-09 (inferência por limites) não incorporada; nenhuma regra de desempate autorizada.
