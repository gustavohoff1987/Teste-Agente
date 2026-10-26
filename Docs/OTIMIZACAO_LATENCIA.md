# Otimização controlada de desempenho e latência

Branch `feat/novos-blocos-incrementais`. Código de referência (baseline): `a202be1`, idêntico a
`03baebf` no código (o commit `a202be1` só acrescentou os dois arquivos de dados). Nenhum
resultado, universo analítico, regra, confirmação, campo de rastreabilidade ou comportamento
funcional foi alterado de propósito; onde a equivalência não pôde ser demonstrada, a mudança foi
descartada (seção 7).

**Resumo.** Com os dados reais, nesta máquina e na mesma rodada de medição:

| Operação | Antes | Depois | Variação |
|---|---|---|---|
| Exame dos dados do Brasil | 15,1 s | 7,7 s | −49% |
| Primeiro pré-exame da interface (sem período) | 16,8 s | 7,5 s | −55% |
| Pré-exame com seleção territorial | 6,6–6,8 s | 2,4–2,6 s | −61% a −63% |
| Densidade, comparação, evolução e agregação com seleção | 11,2–12,2 s | 2,7–2,8 s | −76% a −77% |
| Jornada completa do Bloco 1 no navegador | ~165 s | ~69 s | −58% |

As 229 respostas completas da API usadas como referência são idênticas às do código original em
todas as unidades; todos os testes que passavam continuam passando; o CI aprovou cada push.
Implementadas: U1, U2, U3, U4 e U6 (backend) e U7 (frontend). Descartadas com evidência: U5 e
outras sete alternativas (seção 7).

**Atualização de 21/10/2026 (U8–U11).** Com o servidor já aquecido, o exame da base caiu de 3,5–4,7 s para
0,3 s, o pré-exame repetido para 0,2–0,6 s e a parte local de uma mensagem do chat de 2–4 s para 0,3–0,5 s
(seção 4.9). A espera pelo Gemini (7,5–13 s por chamada, uma de 47 s; ver o
[diagnóstico de 21/10/2026](DIAGNOSTICO_LATENCIA_GEMINI_20261021.md)) não depende deste código e passou a
ser a maior parte do tempo de uma mensagem interpretada pelo provedor.

**Atualização de 26/10/2026 (conversa na página única).** A parte local de uma pergunta de conversa caiu de 130–800 ms para
27–63 ms (seção 4.10), sem mudar nenhuma resposta; o pedido de análise antes da escolha dos dados deixou de esperar o
provedor (o lembrete sai em ~3 ms); e nenhuma chamada nova ao provedor começa depois de 20 s do mesmo pedido.

## 1. Baseline e ambiente de medição

- **Código de referência**: `a202be1`, extraído com `git archive` para uma pasta temporária
  (backend e frontend, este compilado com as mesmas dependências).
- **Ambiente**: contêiner Linux, 4 vCPU Intel Xeon 2,8 GHz, 15 GiB; Python 3.11.17, pandas
  2.3.3, numpy 2.4.6, FastAPI 0.143, Starlette 1.7, uvicorn 0.54 (com uvloop e httptools, como
  `uvicorn[standard]` em produção); Node 22; Chromium 141 via Playwright 1.56.
- **API** (`backend/tests/bench_latency.py`): cada medição roda num processo novo que só
  importa o backend medido, com catálogo instalado em pasta temporária pelo instalador do
  projeto:
  - **pequeno**: catálogo sintético do Bloco 1 (4 municípios × 4 competências);
  - **nacional**: sintético, 5.570 municípios × 22 competências (122.540 linhas), com UF e região;
  - **real**: cópias temporárias de `Dados_Brasil.xlsx` e `Dados_Municipios_Brasil.csv`
    (122.534 linhas municipais), removidas ao final; nenhum registro é impresso.
- **Repetições**: aquecido, 25 (pequeno) ou 7 (nacional, real) por operação, além da primeira
  chamada; mediana e p95 (posto mais próximo; com 7 amostras, p95 = maior valor). A frio
  (`--cold`): cada operação é a primeira requisição de um processo novo. Memória: pico do
  `tracemalloc` por requisição, RSS máximo do processo e memória do quadro municipal.
- **Componentes**: leitura com SHA-256 (`load_brazil`), interpretação (`read_dataset`), perfil
  das colunas (`candidates`), catálogo territorial, função de pré-exame, cálculo, hash dos dados
  analisados e serialização da resposta.
- **Navegador** (`backend/tests/bench_ui_journey.py`): jornada do Bloco 1 com dados reais,
  servidor local sem rede externa e sem Gemini; mede duração por etapa, requisições, abortadas,
  KiB, tarefas longas (> 50 ms) e pré-exames repetidos ou idênticos ao vigente. Essa medição
  percorria as telas clássicas e saiu com elas em 22/10/2026 (página única; ver
  [`backend/tests/legado/README.md`](../backend/tests/legado/README.md)); os números da seção 4.8 ficam
  como registro. As medições do motor (`bench_latency.py`) continuam.
- **Perfis de execução**: cProfile das corrotinas dos endpoints (só nomes de funções e tempos).
- **Variação da máquina**: esta máquina mostrou-se ~3× mais lenta que a da sessão anterior
  (mesmo micro-benchmark: 2,23 s × 0,73 s) e oscilou até ~20% entre rodadas. Por isso só se
  comparam medições da mesma rodada, com versões em ordem alternada; os números absolutos não
  valem como garantia em outra infraestrutura.

## 2. Gargalos confirmados

Hipóteses do enunciado, verificadas com medições por componente (`bench_latency.py`), cProfile
das corrotinas dos endpoints e uma jornada de navegador instrumentada (requisições, bytes,
abortos, cargas repetidas e tarefas longas; nenhum registro da base é impresso).

| Hipótese | Resultado | Evidência |
|---|---|---|
| H1 — leitura repetida das fontes Brasil | **Confirmada.** Cada requisição relia e reinterpretava o CSV municipal | `read_dataset` 2,0–2,4 s por requisição (medianas nacional e real); `load_brazil` (leitura + SHA-256) só 0,02–0,05 s |
| H2 — preparação repetida no pré-exame | **Confirmada.** Funções puras recalculadas sobre os mesmos quadros | numa análise com seleção: `scoped()` 12×, `territory_catalog` 30×, `describe_hierarchy` 32×; `text_values()` 30× (12 em colunas já normalizadas) |
| H3 — catálogo territorial repetido | **Confirmada** (parte de H2) | catálogo do quadro completo 0,45 s por chamada (nacional), 30 chamadas por análise |
| H4 — transporte | **Confirmada em volume, não em tempo** | ~1,1 MB por pré-exame (`territory_choices` de 5.570 municípios); serialização 0,18–0,31 s; renderização no navegador: tarefas longas somam 131–189 ms na jornada inteira |
| H5 — pré-exames redundantes no frontend | **Confirmada** | jornada real no código original: 11–12 pré-exames, 4–5 abortados pelo navegador e 1 idêntico ao vigente; o servidor (uma requisição por vez) calcula **todos**, inclusive os abortados (seção 7, U5) |
| H6 — reprocessamento | **Confirmada** (H1+H2) | mesmas colunas normalizadas várias vezes por requisição; versão nova nunca reaproveitada |

## 3. Otimizações implementadas

Cada unidade foi aplicada isoladamente, com captura prévia do comportamento, testes de
equivalência, comparação antes/depois na mesma sessão e casos válidos, inválidos e ambíguos.

| Unidade | Commit | O que muda | Salvaguardas |
|---|---|---|---|
| U1 — interpretação verificada das fontes Brasil | `8d465ee` | O quadro interpretado do CSV/XLSX é guardado com chave (arquivo, versão verificada) | `load_brazil` continua lendo os dois arquivos e verificando o SHA-256 contra o manifesto **a cada requisição**, antes de qualquer reaproveitamento; uma entrada por fonte (nacional e municipal separadas); versão nova descarta a anterior; o quadro guardado nunca é entregue: cada requisição recebe cópia própria, feita sob trava; uploads nunca são guardados; limite `ADT_BRASIL_CACHE_MAX_MB` (padrão 512; 0 desliga) |
| U2 — memória por requisição | `f9abb9f` | `scoped`, `territory_catalog` e `describe_hierarchy` calculados uma vez por requisição HTTP | `request_memo.py`: contexto aberto por middleware ASGI para cada requisição e descartado ao final; chave = função, identidade do quadro (guardado para impedir reuso do `id`) e JSON dos parâmetros; exceções não são guardadas; fora de requisições nada é memorizado; os 10 pontos de chamada de `scoped()` só leem o recorte |
| U3 — valores distintos antes da normalização | `edf3c27`, `db7fe6c` | Catálogo e relações da hierarquia normalizam valores distintos, não cada linha | `distinct_raw()` só deduplica colunas puramente textuais: com números, 130260 e 130260.0 seriam fundidos (divergência latente da otimização F2 do Bloco 1, comprovada e corrigida em `edf3c27`, com teste) |
| U4 — cada coluna normalizada uma vez por requisição | `0b90f39` | `text_values()`/`texts()` memorizadas pela identidade da coluna | o pandas devolve o mesmo objeto `Series` para a mesma coluna do mesmo quadro; os chamadores só leem o resultado (inserir num quadro copia os valores) |
| U6 — normalização por valores distintos | `ec60a09` | `text_values()` normaliza cada valor distinto e reconstrói a coluna | só para colunas `object` cujos valores não nulos são todos textos; demais tipos seguem o caminho original; teste compara valor a valor (tipo inclusive) com a normalização linha a linha |
| U7 — seleção reaplicada sem novo pré-exame (frontend) | `176ccb2` | Reaplicar a mesma seleção (por exemplo, ao interpretar "Compare os selecionados.") não cria estado novo, e o navegador deixa de reenviar um pré-exame idêntico ao vigente | as confirmações continuam zeradas exatamente como antes; qualquer mudança de valor (IDs, ordem, confirmações, períodos) continua disparando o pré-exame; nenhuma decisão passa ao navegador |
| U8 — memória da versão da base Brasil | 21/10/2026 | Perfis das colunas (`candidates`), pré-exame (`preflight`), identidade e perfil da fonte (`source_identity`, `curated_profile`), catálogo territorial e valores protegidos da minimização (`protected_set`) calculados uma vez por versão, não por requisição | `request_memo.per_source`: vale só para o **objeto** da cópia íntegra entregue por `_brazil_frame` (marcado com `mark_source` quando o reaproveitamento de U1 está ligado); recortes e cópias derivadas não são marcados, ainda que herdem `attrs` (o risco da seção 7); chave = função, (arquivo, versão verificada), JSON dos argumentos e, no pré-exame, o SHA-256 da camada de coordenadas; integridade conferida antes, a cada requisição (U1); cada chamada recebe cópia própria (serialização), salvo o catálogo, compartilhado dentro da requisição como em U2; orçamento de 96 MB com descarte dos menos usados; uploads nunca; `ADT_BRASIL_CACHE_MAX_MB=0` desliga; os testes limpam a memória a cada caso |
| U9 — condição das coordenadas vetorizada | 21/10/2026 | `spatial_data` resume VALIDA/AUSENTE/INVALIDA por território com operações vetorizadas, sem uma função Python por território (~1 s por pré-exame na base municipal) | mesma regra: VALIDA só com todas as linhas válidas, AUSENTE só com todas ausentes; equivalência conferida em 300 casos sintéticos, inclusive território ausente |
| U10 — nomes do catálogo na conversa | 21/10/2026 | `exploration.normalize` memorizada; antes de cada expressão regular de nome, o trecho é procurado no texto | o trecho é condição necessária da expressão, que continua decidindo; com 5.570 nomes, o cache de expressões do Python (512) se esgotava e cada mensagem recompilava milhares delas |
| U11 — aquecimento na partida | 21/10/2026 | O servidor faz em segundo plano a mesma inspeção da base Brasil que a interface pede primeiro (pelo próprio app) e carrega a biblioteca conversacional; a primeira requisição à base espera o aquecimento em curso, em vez de repetir o cálculo em paralelo | só com a partida do servidor (o `TestClient` sem contexto não aquece); falha equivale a não aquecer; espera de no máximo 60 s; `ADT_AQUECIMENTO=0` desliga |

Ferramentas versionadas: `backend/tests/bench_latency.py` (`21e4f94`, `25ae44c`),
`backend/tests/bench_ui_journey.py` (`c21d903`) e os testes `test_brazil_cache.py`,
`test_request_memo.py` e os novos casos de `test_territorial_selection.py`.

## 4. Comparação antes/depois

Medições finais feitas na mesma rodada (13/10/2026, 05:35–06:39 UTC), com baseline e código
final em ordem alternada por perfil (pequeno: baseline→final; nacional: final→baseline; real:
baseline→final; real a frio: final→baseline). Status HTTP e tamanho das respostas são idênticos
em todas as operações.

### 4.1 Dados reais (aquecido, 7 repetições)

| Operação | Baseline mediana (p95) | Final mediana (p95) | Variação | Pico por requisição (MiB) baseline → final | Resposta (KiB) |
|---|---|---|---|---|---|
| Exame municipal (`/api/inspect`) | 15,09 s (16,59) | 7,70 s (8,46) | −49% | 179 → 109 | 1112 |
| Exame nacional | 0,092 s (0,11) | 0,13 s (0,17) | +38% | 10 → 10 | 12 |
| Pré-exame sem período (primeiro da interface) | 16,77 s (17,56) | 7,50 s (7,88) | −55% | 179 → 133 | 1107 |
| Pré-exame com período, sem seleção | 6,14 s (6,28) | 2,62 s (3,04) | −57% | 179 → 52 | 1107 |
| Pré-exame com seleção (municípios do AM) | 6,60 s (7,34) | 2,44 s (2,93) | −63% | 179 → 43 | 1107 |
| Pré-exame com seleção (3 municípios) | 6,78 s (7,06) | 2,64 s (2,70) | −61% | 179 → 43 | 1107 |
| Exploração ("municípios do Amazonas") | 4,42 s (5,33) | 2,18 s (2,33) | −51% | 179 → 43 | 1 |
| Densidade sem seleção | 9,58 s (10,22) | 3,73 s (4,29) | −61% | 179 → 52 | 1857 |
| Densidade com seleção (AM) | 11,23 s (11,86) | 2,71 s (2,88) | −76% | 179 → 43 | 24 |
| Comparação (3 municípios) | 11,92 s (12,34) | 2,77 s (3,00) | −77% | 179 → 43 | 5 |
| Evolução (3 municípios) | 11,87 s (12,12) | 2,75 s (2,90) | −77% | 179 → 43 | 13 |
| Agregação (3 municípios) | 12,20 s (13,12) | 2,78 s (2,94) | −77% | 179 → 43 | 4 |
| Quantitativos nacionais | 0,14 s (0,15) | 0,10 s (0,24) | −26% | 10 → 10 | 2 |

RSS máximo do processo: 624 MiB → 642 MiB. Contagens: 5.570 territórios, 62 no AM, 122.534 linhas.
O +38% do exame nacional (fonte de 22 linhas) não se confirmou na verificação da seção 4.6.

### 4.2 Nacional sintético (aquecido, 7 repetições)

| Operação | Baseline mediana (p95) | Final mediana (p95) | Variação | Pico por requisição (MiB) baseline → final | Resposta (KiB) |
|---|---|---|---|---|---|
| Exame municipal (`/api/inspect`) | 15,64 s (16,34) | 7,72 s (8,09) | −51% | 173 → 110 | 1151 |
| Exame nacional | 0,086 s (0,13) | 0,090 s (0,16) | +5% | 8 → 8 | 12 |
| Pré-exame sem período (primeiro da interface) | 17,66 s (18,66) | 6,23 s (6,84) | −65% | 174 → 135 | 1146 |
| Pré-exame com período, sem seleção | 6,60 s (6,97) | 2,31 s (2,59) | −65% | 171 → 53 | 1146 |
| Pré-exame com seleção (municípios do AM) | 6,78 s (7,59) | 2,32 s (2,88) | −66% | 171 → 42 | 1146 |
| Pré-exame com seleção (3 municípios) | 6,50 s (7,53) | 2,29 s (2,57) | −65% | 171 → 42 | 1146 |
| Exploração ("municípios do Amazonas") | 4,46 s (4,88) | 2,08 s (2,33) | −53% | 171 → 42 | 3 |
| Densidade sem seleção | 9,90 s (9,97) | 3,49 s (4,14) | −65% | 171 → 53 | 1910 |
| Densidade com seleção (AM) | 10,85 s (12,04) | 2,61 s (2,75) | −76% | 171 → 42 | 77 |
| Comparação (3 municípios) | 11,25 s (12,18) | 2,45 s (2,63) | −78% | 171 → 42 | 5 |
| Evolução (3 municípios) | 10,46 s (10,78) | 2,59 s (2,79) | −75% | 171 → 42 | 13 |
| Agregação (3 municípios) | 11,57 s (12,12) | 2,57 s (2,74) | −78% | 171 → 42 | 4 |
| Quantitativos nacionais | 0,094 s (0,12) | 0,089 s (0,10) | −5% | 8 → 8 | 2 |

RSS máximo do processo: 678 MiB → 644 MiB. Contagens: 5.570 territórios, 210 no AM, 122.540 linhas.

### 4.3 Catálogo pequeno do Bloco 1 (aquecido, 25 repetições)

| Operação | Baseline mediana (p95) | Final mediana (p95) | Variação | Pico por requisição (MiB) baseline → final | Resposta (KiB) |
|---|---|---|---|---|---|
| Exame municipal (`/api/inspect`) | 0,13 s (0,17) | 0,11 s (0,14) | −20% | < 1 → < 1 | 13 |
| Exame nacional | 0,054 s (0,081) | 0,050 s (0,077) | −8% | < 1 → < 1 | 11 |
| Pré-exame sem período (primeiro da interface) | 0,11 s (0,17) | 0,11 s (0,13) | −7% | < 1 → < 1 | 10 |
| Pré-exame com período, sem seleção | 0,12 s (0,15) | 0,099 s (0,16) | −18% | < 1 → < 1 | 10 |
| Pré-exame com seleção (municípios do AM) | 0,28 s (0,44) | 0,14 s (0,21) | −52% | < 1 → < 1 | 10 |
| Pré-exame com seleção (3 municípios) | 0,32 s (0,38) | 0,13 s (0,17) | −60% | < 1 → < 1 | 10 |
| Exploração ("municípios do Amazonas") | 0,031 s (0,041) | 0,029 s (0,039) | −7% | < 1 → < 1 | 0 |
| Densidade sem seleção | 0,16 s (0,24) | 0,15 s (0,23) | −5% | < 1 → < 1 | 4 |
| Densidade com seleção (AM) | 0,46 s (0,58) | 0,20 s (0,32) | −56% | < 1 → < 1 | 4 |
| Comparação (3 municípios) | 0,43 s (0,55) | 0,15 s (0,22) | −65% | < 1 → < 1 | 4 |
| Evolução (3 municípios) | 0,44 s (0,53) | 0,16 s (0,20) | −64% | < 1 → < 1 | 5 |
| Agregação (3 municípios) | 0,50 s (0,66) | 0,17 s (0,22) | −66% | < 1 → < 1 | 3 |
| Quantitativos nacionais | 0,069 s (0,090) | 0,071 s (0,091) | +3% | < 1 → < 1 | 2 |

RSS máximo do processo: 122 MiB → 121 MiB. Contagens: 4 territórios, 3 no AM, 16 linhas.

### 4.4 Dados reais a frio (cada operação é a primeira requisição de um processo novo)

| Operação (primeira requisição do processo) | Baseline | Final | Variação |
|---|---|---|---|
| Exame municipal (`/api/inspect`) | 14,66 s | 10,94 s | −25% |
| Pré-exame sem período (primeiro da interface) | 17,25 s | 10,66 s | −38% |
| Pré-exame com período, sem seleção | 5,98 s | 6,35 s | +6% |
| Pré-exame com seleção (municípios do AM) | 6,91 s | 5,23 s | −24% |
| Exploração ("municípios do Amazonas") | 4,73 s | 5,26 s | +11% |
| Densidade com seleção (AM) | 10,57 s | 5,79 s | −45% |
| Comparação (3 municípios) | 10,46 s | 5,39 s | −48% |
| Evolução (3 municípios) | 9,63 s | 5,66 s | −41% |
| Agregação (3 municípios) | 11,96 s | 5,60 s | −53% |
| Quantitativos nacionais | 0,22 s | 0,16 s | −29% |

Na primeira requisição de cada processo (ou de cada nova versão dos dados), U1 paga uma vez a
medição exata da memória do quadro (0,49–0,56 s, exigida pelo limite `ADT_BRASIL_CACHE_MAX_MB`)
e a cópia defensiva (0,26–0,32 s); a partir da segunda requisição, cada uma economiza a
interpretação do CSV (~2,4 s). Por isso duas operações medidas isoladamente como primeira
requisição ficaram 6% e 11% mais lentas (uma amostra cada). Na interface, a primeira requisição
é sempre o exame, 25% mais rápido a frio.

### 4.5 Componentes isolados (dados reais, chamadas diretas fora de requisição)

| Componente (chamada isolada, fora de requisição) | Baseline mediana | Final mediana |
|---|---|---|
| load_brazil (leitura + SHA-256 das duas fontes) | 0,028 s | 0,048 s |
| read_dataset (CSV municipal) | 2,25 s | 2,42 s |
| candidates (perfil das colunas) | 0,76 s | 0,74 s |
| territory_catalog (quadro completo) | 0,49 s | 0,58 s |
| preflight (função) | 3,50 s | 2,07 s |
| compute densidade (função) | 2,28 s | 1,72 s |
| hash_pandas_object (data_sha256) | 0,52 s | 0,44 s |
| jsonable_encoder + json (resposta do preflight) | 0,27 s | 0,30 s |
| memória do DataFrame municipal (MiB) | 88,7 | 88,7 |

Leitura, interpretação, perfil, catálogo, hash e serialização não foram alterados: as
diferenças nessas linhas (até ±50% nas mais curtas) mostram o ruído da máquina na rodada. As
funções de pré-exame e de cálculo, que concentram as mudanças, caem 41% e 25% mesmo sem a
memória por requisição.

### 4.6 Fonte nacional de 22 linhas (sequência baseline, final, final, baseline; 25 repetições)

| Operação | Baseline (passadas 1 e 4) | Final (passadas 2 e 3) |
|---|---|---|
| Exame nacional | 0,086 s / 0,105 s | 0,073 s / 0,079 s |
| Quantitativos nacionais | 0,101 s / 0,128 s | 0,100 s / 0,094 s |

Verificação feita porque a rodada principal registrou +38% no exame nacional real
(0,092 → 0,13 s); com mais repetições e ordem alternada, o código final é 16–21% mais rápido.

### 4.7 Evolução por unidade (dados reais, mesma rodada de cada comparação)

| Versão | Exame | Pré-exame sem período | Pré-exame com seleção (AM) | Densidade com seleção (AM) |
|---|---|---|---|---|
| Baseline | 14,52 s | 15,15 s | 5,92 s | 9,67 s |
| U1+U2 | 11,16 s | 10,16 s | 2,92 s | 3,51 s |
| U3 | 10,63 s | 10,43 s | 2,72 s | 3,05 s |
| U4 | 9,27 s | 8,94 s | 2,52 s | 2,68 s |

U6 × U4 em outra rodada, nas duas ordens (média): exame 10,69 → 8,15 s (−24%); pré-exame sem
período 10,42 → 7,33 s (−30%); pré-exame com seleção 2,85 → 2,22 s (−22%).

Custo de `text_values()` por coluna, por cardinalidade (122.534 linhas, micro-medição): todos
os valores distintos +30% (43,5 → 56,6 ms); metade distintos −3%; 20% distintos −29%; 5.570
distintos (como municípios reais) −50%; 22 distintos −66%. Em colunas muito pequenas (≤ 200
linhas) há custo fixo de ~0,3 ms por chamada. Nas medições de ponta a ponta nenhuma operação
ficou mais lenta, mas um upload com identificador individual quase todo distinto pagaria
~13 ms a mais por normalização dessa coluna.

### 4.8 Jornada no navegador (dados reais; baseline, final, final, baseline)

Backend e frontend de cada versão, servidor local sem rede externa e sem Gemini, mesmo roteiro
(`backend/tests/bench_ui_journey.py`).

| Etapa | Baseline (passada 1) | Final (passada 2) | Final (passada 3) | Baseline (passada 4) |
|---|---|---|---|---|
| 1 dados do Brasil | 15,4 s | 12,4 s | 11,4 s | 15,4 s |
| 2 pergunta Amazonas | 20,3 s | 9,3 s | 10,3 s | 20,3 s |
| 3 densidade (resultado) | 17,4 s | 6,3 s | 5,3 s | 17,4 s |
| 4 seleção Manaus/Tefé/Parintins | 2,2 s | 1,0 s | 0,9 s | 0,9 s |
| 5 comparação | 40,1 s | 13,0 s | 10,9 s | 35,0 s |
| 6 evolução | 30,1 s | 12,8 s | 12,9 s | 33,0 s |
| 7 agregação | 32,3 s | 12,0 s | 13,0 s | 34,4 s |
| 8 retomada (reaproveitada) | 8,9 s | 3,8 s | 3,7 s | 7,7 s |
| **Total** | **166,7 s** | **70,5 s** | **68,4 s** | **164,2 s** |
| Requisições | 21 | 21 | 20 | 20 |
| Pré-exames (abortados) | 12 (5) | 12 (3) | 11 (2) | 11 (4) |
| Pré-exames idênticos ao vigente | 1 | 0 | 0 | 1 |
| Pré-exames repetidos (carga já enviada antes) | 2 | 1 | 1 | 2 |
| KiB recebidos | 8.913 | 11.127 | 11.127 | 8.913 |
| Tarefas longas no navegador (soma) | 189 ms | 131 ms | 154 ms | 175 ms |
| Marcar/desmarcar membro de resultado | 69 / 32 ms | 48 / 51 ms | 53 / 43 ms | 58 / 44 ms |

A jornada inteira caiu de ~165 s para ~69 s (−58%). Cada resposta tem o mesmo tamanho nas duas
versões (pré-exame: 1.107 KiB); o total recebido cresce porque, com o servidor mais rápido, mais
pré-exames terminam antes do clique seguinte em vez de serem abortados no meio da transferência
(9 concluídos contra 7). O pré-exame idêntico ao vigente desaparece (U7). O pré-exame "repetido"
restante é legítimo: a retomada reaplica os parâmetros da comparação depois de outros pedidos.

### 4.9 Memória da versão e aquecimento (21/10/2026; dados reais; Gemini simulado)

Mesma sessão e mesma máquina, código `695070b` (antes) e final (depois). `TestClient` no próprio processo,
28 pedidos das rotas da interface, duas repetições cada, depois de um primeiro exame. A repetição 1
mostra a primeira vez que cada combinação de opções aparece; a 2, a mesma combinação de novo. Os
arquivos da base foram só lidos, com SHA-256 conferido antes e depois. O Gemini foi simulado, de modo
que as linhas de mensagem medem só a parte local.

| Pedido | Antes (rep. 1 / 2) | Depois (rep. 1 / 2) |
|---|---|---|
| Exame da base (`/api/inspect`) | 3,53 / 4,28 s | 0,28 / 0,35 s |
| Exame para a análise espacial | 3,77 / 4,72 s | 0,32 / 0,27 s |
| Pré-exame, 10 combinações (faixa) | 0,94–1,86 / 0,92–2,31 s | 0,28–1,55 / 0,20–0,56 s |
| Análise, 10 combinações (faixa) | 0,77–2,92 / 0,74–3,13 s | 0,19–1,86 / 0,20–1,94 s |
| Densidade, todos os municípios (análise) | 2,56 / 2,54 s | 1,52 / 1,42 s |
| Interpretação local de duas mensagens (`/api/exploration/interpret`) | 2,09–2,19 / 1,96–2,06 s | 0,27–0,39 / 0,24–0,31 s |
| Três mensagens pelo provedor (`/api/llm/interpret-context`, sem a espera remota) | 2,76–3,98 / 2,68–2,95 s | 0,44–2,57 / 0,34–0,40 s |
| **Total dos 28 pedidos** | **49,3 / 50,9 s** | **22,2 / 14,2 s** |

As 56 respostas (28 pedidos × 2 repetições) são idênticas às do código anterior, com os mesmos status
HTTP. Foram desconsiderados só os campos voláteis: identificador e data do resultado, token, validade,
tempo decorrido e revisão.

Aquecimento (U11), num servidor `uvicorn` real:

| Situação | 1ª inspeção | 2ª inspeção |
|---|---|---|
| Sem aquecimento (`ADT_AQUECIMENTO=0`) | 6,77–6,94 s | 0,33–0,34 s |
| Com aquecimento, 12 s depois da partida | 0,39–0,46 s | 0,32–0,37 s |
| Com aquecimento, clique imediato | 6,56–7,52 s | 0,32–0,70 s |

No clique imediato, a primeira inspeção espera o aquecimento em curso. Antes dessa espera, as duas
inspeções disputavam o processador e a primeira levava 14,2 s.

### 4.10 Conversa na página única (26/10/2026; dados reais; Gemini simulado)

Pedido do responsável: depois das últimas mudanças da conversa, a preparação das respostas ganhou latência, e o começo sem
base ficava "processando". Mesma máquina, `TestClient` no próprio processo, base versionada instalada numa pasta temporária
(somente leitura), transporte do Gemini simulado e instantâneo: as linhas medem só o trabalho local (triagem, cartão,
conferência, gestor, gramática e, quando a resposta muda o gráfico, o cálculo do gráfico novo pelo motor). Mediana de 3 a 5
repetições; antes, o código de `dd5743f`; depois, o desta entrega.

| Pedido | Antes | Depois |
|---|---|---|
| Sem base: "Compare os municípios do Pará pela densidade" | 10 ms + a espera do Gemini (até 75 s por chamada) | 2,8 ms, sem chamada |
| Tendência de PORTO ALEGRE (RS): "Não entendi a aceleração." | 141 ms | 29 ms |
| Tendência: "Explique esse resultado." | 134 ms | 27 ms |
| 144 municípios do Pará: "Qual deles tem a maior densidade?" | 648 ms | 51 ms |
| Pará: "quantos municípios estão no gráfico?" | 800 ms | 63 ms |
| Pará: "Compare Belém e Ananindeua" (com o gráfico novo) | 552 ms | 287 ms |
| Pará: "compare o de maior e o de menor densidade" (com o gráfico novo) | 451 ms (pedia os nomes) | 134 ms (abre a comparação) |

Causas encontradas pelo perfil (cProfile) e corrigidas sem mudar o resultado:
- `resumo_painel.places_for` comparava todos os pares de valores a cada número de casas (quadrático: 144 valores, ~20 mil
  formatações por frase); agora formata cada valor uma vez por número de casas e conta os textos distintos. Equivalência
  conferida em `test_casas_comuns_sao_as_mesmas_da_comparacao_par_a_par` (309 listas, inclusive inteiros, empates e valores
  que só se separam em muitas casas);
- a triagem (`triagem.py`) procurava cada nome do vocabulário em cada texto; agora indexa os nomes pela primeira palavra
  (`_indice`, guardado entre pedidos) e só confere os que começam por uma palavra do texto, com o mesmo resultado;
- a proteção dos dados do Brasil (`main._protecao_do_pedido`) copiava a base e calculava o hash a cada pedido; agora fica
  guardada por versão da base e recorte (até 4);
- o contexto da investigação (`llm_context`) calculava a impressão da base inteira a cada pedido, e a gramática listava as
  competências da coluna a cada pedido; as duas ficam guardadas por cópia da fonte (`request_memo.per_source`).
Tempo de espera do provedor (`llm_bridge.ORCAMENTO_DE_REGENERACAO`): passados 20 s do pedido, nenhuma chamada nova começa
(nem regeneração nem redação); a chamada em curso mantém o prazo de 75 s (decisão de 21/10/2026). Na tela, a espera tem
prazo de 100 s e avisos de andamento aos 12 s e aos 45 s. O script da medição ficou fora do repositório (scratchpad da
sessão), como os demais benchmarks fora do CI.

## 5. Equivalência de resultados

Antes de cada unidade, um capturador fora do Git gravou as respostas completas da API do código
original (status e corpo JSON integral, com a ordem das chaves) em 229 casos: 76 no catálogo
pequeno do Bloco 1, 76 no nacional sintético e 77 nos dados reais. Os casos cobrem exame,
pré-exame com e sem período, seleções (estado, trio, homônimos, IDs inexistentes), todas as
operações, uploads CSV/XLSX válidos e inválidos (códigos numéricos mistos, espaços, ausentes,
conflitos hierárquicos, filtros sem registros) e erros de versão. Só `result_id` (validado como
UUID) e `created_at` (validado como data ISO) são normalizados antes da comparação.

| Unidade | Casos idênticos ao original |
|---|---|
| U1 | 229/229 |
| U2 | 229/229 |
| U3 | 229/229 (+ 14 cenários do catálogo e da hierarquia contra a versão anterior ao Bloco 1) |
| U4 | 229/229 |
| U6 | 229/229 (+ 18 entradas sintéticas extremas e todas as colunas reais e nacionais, valor a valor) |
| U7 | não altera a API nem o cálculo: build, smoke, regressão e integração do Bloco 1 e roteiro conversacional aprovados; na jornada real, pré-exames idênticos ao vigente caem de 1 para 0 |
| U8–U11 (21/10/2026) | 56/56 respostas das rotas da interface com dados reais, contra `695070b` (seção 4.9); U9 também em 300 casos sintéticos, inclusive território ausente |

Status do baseline nos três catálogos: 200 em 162 casos, 422 em 64 e 503 em 3 (Gemini
desligado), reproduzidos igualmente.

## 6. Testes e regressões

### 6.1 Testes acrescentados

| Arquivo | Cobertura | Verificação por mutação |
|---|---|---|
| `test_brazil_cache.py` (6) | cópia própria por requisição (atributos copiados; o quadro guardado não leva `source`); integridade verificada a cada requisição (arquivo alterado → 422 "integridade"; removido → 422); versão nova nunca reaproveita conteúdo anterior (uma entrada por fonte); uploads nunca guardados; respostas idênticas com e sem reaproveitamento (`ADT_BRASIL_CACHE_MAX_MB=0`); 8 threads simultâneas | cada teste falha quando a proteção correspondente é retirada |
| `test_request_memo.py` (4) | nada memorizado fora de requisição; mesmas entradas compartilham resultado e entradas diferentes não; exceções não memorizadas; requisições não compartilham resultados; o middleware memoriza dentro de uma requisição HTTP (TestClient) | — |
| `test_brazil_cache.py` (+3, 21/10/2026) | resultados derivados reaproveitados só para a mesma versão verificada, e recalculados com `ADT_BRASIL_CACHE_MAX_MB=0`; uploads nunca entram na memória da versão; o aquecimento prepara a primeira inspeção sem mudar a resposta, e `ADT_AQUECIMENTO=0` não aquece | — |
| `test_request_memo.py` (+4, 21/10/2026) | fonte marcada reaproveita entre requisições com cópia própria por chamada; quadros não marcados ou derivados nunca reaproveitam; resultados compartilhados seguem o contrato da requisição; orçamento de bytes limitado | — |
| `test_territorial_selection.py` (+2) | códigos 130260 e 130260.0 continuam textos distintos no catálogo e no motor; `text_values()` igual, valor a valor e com o mesmo tipo, à normalização linha a linha | o primeiro falha no código anterior a `edf3c27`; o segundo, sem a condição "somente textos" |

Nenhum teste existente foi alterado, enfraquecido ou removido nesta tarefa.

### 6.2 Regressão final (HEAD `c21d903`)

| Suíte | Resultado |
|---|---|
| pytest do backend | **216 aprovados**, 20 omitidos (exigem dados reais; executados abaixo) |
| pytest com dados reais (`ADT_REAL_DATA_DIR`) | **20 aprovados**; SHA-256 dos originais idêntico antes e depois |
| build do frontend (tsc + Vite) | **aprovado** (aviso de tamanho de bloco já existente) |
| `ui_block1_smoke` e `ui_block1_regression` (catálogo sintético, como no CI) | **aprovados** |
| `ui_block1_integration` (transporte Gemini simulado) | **aprovado** |
| `ui_conversational_smoke` (catálogo sintético de duas fontes, como no CI) | **aprovado** |
| `ui_block1_smoke` com dados reais (`ADT_BLOCK1_REAL=1`) | **aprovado** no código final e no baseline |
| `bench_ui_journey.py` com dados reais | concluída nas 4 passadas (seção 4.8) |
| `ui_brazil_smoke`, `ui_smoke` (dados reais) | falham **igualmente** no baseline e no final, na mesma linha, antes de qualquer comparação de dados: procuram elementos anteriores à interface conversacional ("Usar dados do Brasil" fora da conversa; título "Configuração da análise") |
| `ui_session_smoke`, `ui_carousel_smoke`, `ui_audit_smoke`, `ui_preparation_smoke`, `ui_integration_smoke` | falham **igualmente** no baseline e no final, na mesma linha e com o mesmo erro: roteiros desatualizados antes do Bloco 1, já registrados em `BLOCO1_RESULTADOS_EXPLORAVEIS.md` |

Resumo: aprovadas todas as suítes que passavam no baseline; 7 roteiros antigos falham de forma
idêntica nas duas versões (nenhuma regressão); 20 testes omitidos no pytest padrão foram
executados à parte e aprovados; nenhuma suíte deixou de ser executada. As capturas de tela das
execuções com dados reais foram geradas em cópias temporárias fora do repositório e apagadas.

## 7. Alterações descartadas

| Alteração | Motivo |
|---|---|
| U5 — no servidor, não calcular pré-exames cujo navegador já desistiu (`request.is_disconnected()`) | Experimento com uvicorn real (uvloop + httptools, como em produção), dados reais: uma requisição lenta, três abandonadas pelo cliente na fila e a vigente. Sem a verificação, a vigente levou 16,74 s; com ela, 16,46 s. A desconexão só é processada pelo laço de eventos depois do teste, e as abandonadas continuam calculadas. Revertida |
| Contornar `jsonable_encoder` com JSON pré-serializado | Ganho máximo de ~0,18 s por pré-exame, com risco de alterar bytes, tratamento de NaN e tipos numpy |
| Reaproveitar no navegador o pré-exame embutido no exame (`/api/inspect`) | Não é equivalente: o exame usa só as opções curadas do servidor; o navegador envia filtro de categoria, `require_object_confirmation` e outras opções. Omitir o pré-exame do exame mudaria o contrato da API (decisão separada, seção 10) |
| Fila de um pré-exame por vez no navegador | Evitaria calcular intermediários quando várias mudanças ocorrem durante um pré-exame, mas exige baixar a resposta superada antes de enviar a vigente e, sem tempo-limite, travaria diante de uma requisição pendurada. Ganho real só com cliques muito rápidos (roteiros automáticos). Não implementada sem decisão |
| Cache global de respostas de pré-exame para o catálogo Brasil | Saltaria repetições idênticas, mas é infraestrutura nova com invalidação e compartilhamento entre usuários a demonstrar; fora do escopo. **Retomado em 21/10/2026 como U8**, por função e não por resposta HTTP: invalidação pela versão verificada (e pela camada de coordenadas), resultados só de dados públicos da base oficial e dos parâmetros do pedido, cópia própria a cada chamada |
| Memorizar `candidates()` por requisição | Sem ganho: as duas chamadas do exame recebem quadros diferentes (completo e recortado) |
| Cache entre requisições de `candidates()`/catálogo por versão | Inseguro: recortes herdam `attrs["source"]` do quadro completo e receberiam o perfil errado. **Resolvido em 21/10/2026 (U8)**: a marca é a identidade do objeto entregue por `_brazil_frame`, não `attrs`; um recorte é outro objeto e nunca é marcado (teste `test_unmarked_and_derived_frames_never_reuse_between_requests`) |
| Virtualização, paginação ou compressão da lista territorial | Sem evidência de ganho: a renderização no navegador não aparece como gargalo (tarefas longas somam até 189 ms na jornada inteira; marcar ou desmarcar um membro leva 32–69 ms) |

## 8. Memória

| Medida | Baseline | Final |
|---|---|---|
| Quadro municipal interpretado (real / nacional) | 88,7 / 87,3 MiB | 88,7 / 87,3 MiB |
| Pico por requisição, operações com seleção (real) | 179 MiB | 43 MiB |
| Pico por requisição, pré-exame com período sem seleção (real) | 179 MiB | 52 MiB |
| Pico por requisição, exame e pré-exame sem período (real) | 179 MiB | 109–133 MiB |
| RSS máximo do processo (real / nacional / pequeno) | 624 / 678 / 122 MiB | 642 / 644 / 121 MiB |
| Heap JavaScript ao fim da jornada (depende da coleta de lixo) | 18–19 MiB | 23–24 MiB |

- **Residente**: U1 mantém por processo uma cópia interpretada de cada fonte Brasil (municipal
  ~89 MiB; nacional, 22 linhas, desprezível). O ganho nos picos por requisição compensa: o RSS
  máximo ficou na mesma faixa.
- **Limite e invalidação**: `ADT_BRASIL_CACHE_MAX_MB` (padrão 512; 0 desliga) é comparado com a
  memória exata do quadro (`memory_usage(deep=True)`) antes de guardá-lo; quadro maior não é
  guardado. Uma entrada por fonte; versão nova (SHA-256 diferente no manifesto) descarta a
  anterior; uploads nunca são guardados.
- **Isolamento**: cada requisição recebe cópia própria, feita sob trava; o quadro guardado não
  carrega `attrs["source"]` e nunca é entregue diretamente.
- **Memória por requisição** (U2, U4): o espaço de memorização nasce e morre com a requisição
  HTTP; nada sobrevive a ela nem passa a outra requisição, com uma exceção: a memória da versão
  (U8), só para derivações da cópia íntegra da base Brasil, até 96 MB por processo (descarte dos
  menos usados), desligada com `ADT_BRASIL_CACHE_MAX_MB=0`. Uploads nunca entram nela.

## 9. CI

Workflow "CI Portal Experimental" (`.github/workflows/ci.yml`): pytest do backend, build do
frontend, roteiro conversacional no navegador (catálogo sintético de duas fontes) e job
`ui-block1` (smoke e regressão sem Gemini, integração com transporte Gemini simulado). Nenhum
job usa dados reais, credenciais ou o Gemini real. Execuções desta tarefa, todas na branch
`feat/novos-blocos-incrementais`:

| Execução | Commit (HEAD do push) | Conteúdo | Resultado |
|---|---|---|---|
| 187 | `8d465ee` | medidor de latência + U1 | sucesso |
| 188 | `f9abb9f` | U2 | sucesso |
| 189 | `db7fe6c` | U3 (`edf3c27` + `db7fe6c`) | sucesso |
| 190 | `0b90f39` | medidor ampliado + U4 | sucesso |
| 191 | `ec60a09` | U6 | sucesso |
| 192 | `c21d903` | U7 + sonda da jornada | sucesso |

Os jobs de UI do CI foram reproduzidos localmente com os mesmos comandos antes de cada push
que tocou o frontend. O push deste documento dispara uma nova execução, conferida após a
publicação.

## 10. Recomendações para os Blocos 2 e 3

Nenhuma destas recomendações foi implementada; todas exigem decisão.

1. **Pré-exame sem período e exame continuam os mais lentos** (seção 4): validam cada operação
   sobre as 122 mil linhas. Alternativas, todas mudanças de contrato: o exame deixar de embutir
   um pré-exame completo (o navegador já pede outro logo em seguida, com as próprias opções);
   adiar validações de linha inteira até a escolha de período ou operação; ou guardar
   respostas de pré-exame do catálogo Brasil por (versão verificada, associação, opções).
2. **Lista territorial fora do pré-exame**: `territory_choices` (~1,1 MB, 5.570 municípios)
   viaja em toda resposta. Um recurso separado, identificado pela versão dos dados e baixado uma
   vez, reduziria transporte e serialização. Os mapas do Bloco 3 não devem embutir geometrias
   no pré-exame pelo mesmo motivo.
3. **Novas funções puras dos Blocos 2 e 3** (referência geográfica múltipla, buscas espaciais)
   devem usar a memória por requisição (`request_memo.per_request`) e, se forem caras por
   versão (índices espaciais), seguir o modelo de U1: chave pela versão verificada por SHA-256,
   cópia por requisição, limite de memória, nada de uploads.
4. **Pré-exames superados no navegador**: se usuários relatarem lentidão ao marcar vários
   territórios, avaliar uma fila de um pré-exame por vez (interrompendo só o download da
   resposta superada e com tempo-limite) ou um identificador de sequência por aba que permita
   ao servidor dispensar pedidos superados.
5. **Vários usuários**: o servidor executa o cálculo de forma síncrona, uma requisição por vez
   por processo. Para uso simultâneo, avaliar mais de um processo (cada um com sua própria
   cópia guardada, ~90 MiB) antes de qualquer paralelismo dentro do processo.
6. **Medir antes de otimizar**: acrescentar as novas operações a `bench_latency.py` e os
   novos casos ao capturador de equivalência antes de qualquer mudança de desempenho.

## 11. Proposta separada: acesso seguro aos dados reais no Claude Code web

### Situação encontrada

Em 12/10/2026 23:20 (−03), o commit `a202be1` ("Add files via upload — Base de Dados do
Brasil") publicou `Dados_Brasil.xlsx` (7,8 KB) e `Dados_Municipios_Brasil.csv` (9,97 MB) na
raiz da branch `feat/novos-blocos-incrementais` do repositório **privado**. Esta tarefa não
adicionou, moveu nem removeu esses arquivos, e não alterou o `.gitignore` (que protege
`.local/`). Verificação estrutural, sem exibir registros: 122.534 linhas; colunas de região,
UF, município, código IBGE, coordenadas, categoria, ano, mês, quantidade e população estimada;
nenhuma coluna de identificação individual. O README ainda afirma que "os dados não acompanham
o código no Git": a política precisa ser decidida e registrada.

O aplicativo não lê os arquivos da raiz: usa cópias verificadas instaladas por
`backend/install_brazil_data.py` (manifesto SHA-256 em `.local/datasets/brasil/`, ignorada).

### Alternativas

| Critério | A. Repositório privado (situação atual) | B. Armazenamento externo privado + instalação autenticada |
|---|---|---|
| Viabilidade | Já em vigor; 10 MB, muito abaixo dos limites do GitHub | Exige bucket ou pasta privada, credencial de leitura e script de configuração do ambiente |
| Facilidade operacional | Clone traz os arquivos; basta `python backend/install_brazil_data.py --source . --destination .local/datasets/brasil` por sessão | Script baixa, confere SHA-256 e instala a cada sessão; credencial e domínio permitido configurados por você nas opções do ambiente |
| Segurança | Quem lê o repositório (colaboradores, apps instalados, forks privados) lê os dados; tornar o repositório público os expõe; o histórico mantém cada versão | Acesso controlado pela ACL do armazenamento e por segredo do ambiente; nada no histórico Git |
| Persistência entre sessões | Total (faz parte do clone) | Total, se o script rodar em toda sessão nova |
| Custos | Nenhum adicional | Desprezível para 10 MB (Drive/S3/GCS), mais manutenção do segredo |
| Compatibilidade com o instalador | Direta (`--source .`) | Direta (download para pasta temporária, depois `--source`) |
| Reversão | Remover do histórico exige reescrita (force-push), decisão destrutiva | Revogar a credencial ou o compartilhamento |

### Recomendação

Para estas duas fontes — estatísticas agregadas, sem identificação individual, 10 MB,
repositório privado — **A é a forma mais simples e é adequadamente segura**, desde que:
(1) a procedência e a licença das fontes sejam registradas; (2) o repositório permaneça
privado e o fork seja desabilitado (hoje `allow_forking` está ativo); (3) o README passe a
descrever a política (dados versionados, instalação obrigatória via instalador, `.local/`
continua ignorada); (4) atualizações substituam os arquivos por commits identificados,
sempre seguidos do instalador, que verifica o SHA-256.

Prefira **B** se a base passar a conter dados pessoais ou sensíveis, se o repositório puder
ser compartilhado com mais pessoas ou tornado público, ou se as versões crescerem muito.
Nesse caso, a remoção do histórico atual é uma decisão separada, destrutiva, que exige sua
autorização explícita.

Nenhuma credencial, script de ambiente ou alteração de histórico foi configurada nesta tarefa.

## 12. Limitações e pendências

- **Números absolutos não são garantia**: a máquina virtual oscilou (cerca de 3× mais lenta
  que a da sessão anterior e até 20% entre rodadas desta sessão). Valem as comparações feitas
  na mesma rodada; o CI não mede desempenho.
- **Dados reais**: validados empiricamente nesta sessão, porque os arquivos estão no
  repositório desde `a202be1`. Foram usadas cópias temporárias instaladas pelo instalador do
  projeto; os originais tiveram o SHA-256 conferido antes e depois e não foram alterados.
  Nenhum registro aparece em logs, relatórios ou commits.
- **Concorrência**: o reaproveitamento de U1 foi testado com 8 threads simultâneas e cópias
  independentes; não houve teste de carga com vários usuários reais. O servidor continua
  atendendo uma requisição de cálculo por vez por processo.
- **Jornada automatizada**: os cliques do roteiro são muito mais rápidos que os de uma
  pessoa, o que exagera a quantidade de pré-exames abortados (H5) em relação ao uso real.
- **Pré-exame sem período e exame** continuam na casa de vários segundos com dados reais nesta
  máquina; ganhos maiores dependem das decisões de contrato da seção 10.
- **Memória**: U1 mantém um quadro municipal por processo (~90 MiB); `ADT_BRASIL_CACHE_MAX_MB=0`
  desliga o reaproveitamento. A primeira requisição de cada processo ou versão paga ~0,8 s fixos
  (medição exata de memória e cópia) antes de passar a economizar ~2,4 s por requisição.
- **Espera pelo Gemini (21/10/2026)**: a chamada ao provedor levou 7,5–13 s nas medições do
  [diagnóstico](DIAGNOSTICO_LATENCIA_GEMINI_20261021.md), uma delas 47 s. Ela domina o tempo das mensagens
  interpretadas pelo provedor e não muda com estas otimizações. Exemplos, modelo e parâmetros seguem a
  decisão daquele diagnóstico.
- **Memória da versão (U8)**: até 96 MB a mais por processo; a primeira vez de cada combinação de opções
  ainda calcula tudo (pré-exame de 0,3–1,6 s nesta máquina).
- **Perfil de custo de U6**: em colunas com quase todos os valores distintos (identificadores
  individuais em uploads), a normalização da coluna fica ~30% mais lenta (~13 ms por 122 mil
  linhas); em colunas minúsculas, ~0,3 ms por chamada. Nenhuma operação medida ficou mais lenta.
- **Roteiros de UI antigos** (`ui_session`, `ui_carousel`, `ui_audit`, `ui_preparation`,
  `ui_integration_smoke`) já falhavam antes do Bloco 1; continuam fora do escopo.
- **Política dos dados no Git** e proteção do repositório (seção 11) aguardam sua decisão.
