# Auditoria investigativa da divergência entre 160 e 225 municípios

Data: 14/10/2026. Repositório: `gustavohoff1987/Teste-Agente`. Branch confirmada: `feat/novos-blocos-incrementais`. HEAD: `30dd58029cff68ed49773a4147970cf454195208`. A árvore de trabalho estava limpa no início. Auditoria exclusivamente investigativa, sem correções de algoritmos, SPEC, testes, fontes, camada geográfica ou configurações. Não houve commit, push, PR ou merge.

## 1. Resumo executivo

**Os 225 municípios foram reproduzidos pelo motor e por cálculo independente. A diferença de definição dos alvos explica 66 municípios, mantendo dados e geodésica constantes: o resultado passa de 225 para 159.**

Uma reconstrução candidata, denominada **H**, reproduz simultaneamente os números informados para o levantamento anterior: **1.125 alvos no primeiro quintil, 2.011 referências, 160 selecionados e 3.546.239 habitantes**. Ela usa os mesmos registros de junho de 2024, arredonda as densidades para duas casas antes de formar quintil e referências, preserva os empates e calcula distância esférica por Haversine com raio de 6.371,0088 km. O raio de 6.371 km produz o mesmo conjunto.

Essa concordância é evidência forte de uma explicação metodológica. **É COMPROVADO que essa combinação reproduz os totais; é PROVÁVEL, mas não comprovado, que ela corresponda ao procedimento histórico.** Não foi disponibilizada a lista histórica por código, seu script, seu arquivo original com hash ou o texto metodológico integral. A reconstrução H não deve ser identificada como a lista histórica autenticada.

O município decisivo para a diferença entre 159 e 160 é **Epitaciolândia/AC (`120025`)**, com 19.739 habitantes: sua referência mais próxima é Rio Branco/AC (`120040`). A distância elipsoidal é **154,751494784 km**, enquanto a esférica é **155,129291429 km**. Ele pertence ao primeiro quintil e muda de classificação exclusivamente pela distância.

Comparando A, o cenário atual, com H: **159 em comum, 66 exclusivos de A e 1 exclusivo de H**. Portanto, 225 − 160 = 65 é uma diferença líquida; a diferença simétrica contém **67 códigos**. Não são simplesmente “os mesmos 160 mais 65”.

Não foi encontrado defeito de software que explique os 225 nesta execução. Não houve evidência de mistura de competências. O resultado atual está coerente com seus parâmetros; isso não significa que seja a mesma pergunta científica do levantamento anterior.

## 2. Dados, integridade e métodos examinados

Foram lidos os dois arquivos originais versionados, o manifesto, a camada complementar, os módulos de carregamento e cálculo, os componentes de apresentação relevantes, a SPEC e os testes relacionados. A execução pela API foi local, por `TestClient`, sem provedor LLM. O recálculo independente não importou funções nem resultados do backend.

| Arquivo | SHA-256 |
| --- | --- |
| `Dados_Municipios_Brasil.csv` | `89c027c90a2db5a4a7a7b5e3282404fb12b2bc30d500a4a79e49b6793749f512` |
| `Dados_Brasil.xlsx` | `7caa74d7a49f2f7cd2adf87b1c0546f7755ec0291dcb0ffbfae7c387dceb91d3` |
| `dados/brasil/complemento_coordenadas.json` | `0ba2b664cc9b1acb6cc67e548eb5297128ae02fcd2b8f640d4c1dca39ffdbbf9` |

A versão lógica do catálogo é `819cf4628bff55b58e3405ec33ec01d675f27be2f3f085235217028eb608a3f4`. CSV: 9.968.224 bytes. XLSX: 7.786 bytes. As variáveis `ADT_BRASIL_DATA_DIR` e `ADT_BRASIL_DATA_VERSION` estavam ausentes no processo de reprodução do motor: a origem foi a raiz do repositório. As duas cópias em `.local/datasets/brasil` têm os mesmos hashes, mas não são lidas pelo carregador nessa configuração. O histórico Git local registra uma única introdução dos arquivos originais, em `a202be1`; isso não estabelece identidade com o arquivo usado no estudo anterior.

O CSV contém 122.534 linhas, uma única categoria (`MEDICINA`), 22 competências e nenhum campo vazio. Não há duplicação da chave `(código, competência, categoria)`. Em `202406` há 5.570 linhas e 5.570 códigos, todos com quantidade inteira não negativa e população positiva; não há quantidade zero. Há apenas 5.288 nomes distintos: usar o nome sozinho confundiria homônimos. Todos os identificadores municipais fornecidos têm seis dígitos; foram preservados como texto, sem inventar dígito verificador.

Em junho de 2024, a soma das populações é 212.583.750; a soma dos quantitativos municipais é 817.419. O XLSX nacional contém 502.495 para a mesma competência. O motor não usa esse quantitativo nacional na densidade municipal. A diferença entre soma municipal e contagem nacional não prova duplicação indevida dentro de um município: faltam microdados para auditar a unidade de contagem na origem e a mobilidade entre municípios. O perfil do catálogo declara `pessoas`; a documentação dos testes registra a declaração do usuário de profissionais distintos dentro do recorte, sem aditividade entre recortes.

O arquivo populacional não é separado: `população_estimada` está na mesma linha do quantitativo. A competência da linha é verificável; a edição e a data de referência da estimativa populacional não estão documentadas no arquivo. Não se confunde alinhamento das linhas pelo software com validação científica da fonte demográfica.

## 3. Reconstrução do processamento atual

As referências abaixo são do HEAD auditado; os números de linha permitem localizar a implementação.

| Etapa | Arquivo e função | Comportamento observado |
| --- | --- | --- |
| 1. Origem | `backend/brazil_data.py:86`, `_resolve`; `:116`, `_read_verified`; `:146`, `load_brazil` | Seleciona escopo municipal, verifica tamanho e SHA-256 dos dois arquivos; recusa versão incompatível. Não une municipal e nacional. |
| 2. Carregamento | `backend/main.py:66`, `read_dataset`; `:464`, `_brazil_frame`; `:521`, `_request_dataset` | CSV preservado como texto, delimitador identificado, colunas normalizadas; cache do quadro por arquivo/versão, cópia por requisição. |
| 3. Período | `backend/dataset_normalization.py:14`, `compose_period`; `nearest_reference.py:56`, `analysis_period`; `:77`, `_in_period` | Compõe ano × 100 + mês. A análise espacial exige uma única competência; `202406` é aplicada antes das medidas e da geometria. |
| 4. Categoria | `brazil_catalog_profile.py:27`, perfil; `nearest_reference.py:145`, `density_criterion`; `combined_criteria.py:209`, `_category` | `MEDICINA` é a única categoria. A seleção é explícita por valor, sem inferência de especialidades ou soma de categorias. |
| 5. Universo territorial | `territorial_selection.py:34`, `territory_catalog`; `data_contract.py:48`, `scoped`; `nearest_reference.py:246`, `nearest_inputs` | Identidade `code:<cod_ibge>`. Os alvos iniciais são os 5.570 observados no recorte; a condição de densidade é uma folha da avaliação, não uma exclusão prematura. |
| 6. Quantitativos | `combined_criteria.py:226`, `measures` | Lê a coluna `quantidade` na competência/categoria; exige uma linha por território. Não soma 22 períodos, não deduplica pessoas e não usa o total nacional. |
| 7. Denominador | `combined_criteria.py:226`, `measures`; `data_contract.py:171`, `prepare` | Critérios usam a população da mesma linha filtrada. Na operação genérica de densidade, a associação usa território/período e valida muitos-para-um. |
| 8. Densidades | `combined_criteria.py:349`, `Evaluator.values`; `nearest_reference.py:145`, `density_criterion` | Quantidade/população × 1.000. A comparação usa frações; o float serve à apresentação. Os inteiros reais estão abaixo de 2^53, preservados exatamente na conversão. |
| 9. Alvos que satisfazem densidade | `combined_criteria.py:423`, `_leaf_results` | Comparação estrita `< 2,36`: 3.563 atendem. Não é seleção por primeiro quintil. |
| 10. Referências | `nearest_reference.py:203`, `reference_set` | Densidade `≥ 2,36`, na mesma competência/categoria: 2.007. A seleção territorial de alvos não reduz automaticamente o universo de referências. |
| 11. Coordenadas | `nearest_reference.py:83`, `territory_coordinates`; `geo_complement.py:125`, `overlay` | Lê graus decimais com vírgula; verifica finitude, intervalos e conflitos. Aplica seis pontos da camada apenas quando autorizados e inválidos na base original. |
| 12. Busca e distância | `nearest_reference.py:317`, `nearest_exact`; `:376`, `compute_nearest` | Problema inverso de Karney/PROJ no GRS80. A corda 3D elimina apenas candidatos que não podem melhorar o mínimo. Referências empatadas são preservadas. Metros convertidos em km, sem arredondar para decidir. |
| 13. Critérios combinados | `combined_criteria.py:305`, `distance_values`; `:399`, `evaluate_tree`; `:608`, `compute_criteria` | AND trivalente: densidade `< 2,36` e distância `> 155`; mantém `ATENDE`, `NAO_ATENDE` e `NAO_AVALIAVEL`. Distância completa quando todas as referências são avaliáveis. |
| 14. Resultado | `main.py:159`, `compute`; `:758`, `analyze`; `frontend/src/CriteriaResults.tsx:42` | 225 atendem, 5.345 não atendem, zero não avaliáveis. API retorna 5.570 avaliações. A interface filtra `ATENDE`, mostra até 150 linhas por tabela e exporta todo o recorte filtrado. O limite visual não explica 160 ou 225. |

`RES-LIM` permanece porque a distância é geográfica direta, sem equivalência a trajeto viário ou acessibilidade. Não significa que existam municípios não avaliáveis nessa execução. A SPEC, seção CFG-MET (linhas 949–951), exige geodésica elipsoidal, precisão integral e arredondamento apenas na apresentação. O motor está alinhado a essa regra para o caso auditado.

## 4. Verificação temporal e estabilidade do universo

O filtro temporal é aplicado em `scoped`, `_in_period`, `density_criterion`, `measures` e na construção da geometria em `_nearest_inputs`. O catálogo de identidades pode examinar toda a base, mas não agrega quantitativos, populações ou coordenadas de períodos distintos. A geometria considera as linhas da competência, inclusive categorias se existissem várias; nesta fonte há uma única categoria. A camada usa uma coordenada fixa para seis municípios por premissa explícita, não por reaproveitamento acidental de resultados de outro período.

Foram executados os seguintes ensaios, sem gravar alterações nas fontes:

| Ensaio | Evidência |
| --- | --- |
| Base completa com filtro versus somente as 5.570 linhas de `202406` | Mesmas avaliações, medidas, distâncias, referências e contagens. |
| Alterar em memória os outros 116.964 registros para quantidade 99.999.999, população 1 e coordenadas 89/179 | Nenhuma alteração nas avaliações de `202406`. |
| Inverter a ordem das 122.534 linhas | Nenhuma alteração nos resultados. |
| API: `202406` → `202401` → `202406` | Janeiro retorna 237; junho volta ao mesmo conjunto de 225. |
| Omitir competência na base de vários períodos | HTTP 422, exigindo período único. |
| Solicitar simultaneamente `202401` e `202406` em critérios espaciais | HTTP 422. |

O memo em `request_memo.py` vive somente durante uma requisição; as chaves incluem os argumentos e o quadro. O cache persistente guarda o quadro bruto por versão, não o conjunto analítico final. As observações dinâmicas são compatíveis com esses mecanismos.

O universo **não é de 5.570 em todas as competências da fonte**: `201501` tem 5.567, `201506`, `201701` e `202001` têm 5.569; as demais têm 5.570. Isso explica 122.534, e não 122.540 linhas. As ausências são reais na fonte e não afetam `202406`. Os códigos ausentes são, respectivamente, `110110/313000/353286`, `430607`, `420555` e `431973`.

Janeiro e junho de 2024 têm populações e coordenadas idênticas em todos os municípios, mas quantitativos diferentes em 4.068. Janeiro tem 1.920 referências exatas, contra 2.007 em junho. A repetição do denominador na própria fonte não é prova de que o motor usou o período errado. O ano/vintage demográfico efetivo permanece sem comprovação externa.

**Conclusão temporal:** mistura de períodos como explicação dos 225 está DESCARTADA para a execução reconstruída. Não se afirma impossibilidade universal de falhas em qualquer configuração futura nem se conhece o processamento temporal histórico.

## 5. Recálculo independente

`independente.py` lê o CSV com `csv.DictReader`, delimitador `;`, UTF-8 com BOM tolerado, seleciona explicitamente ano/mês `202406` e categoria `MEDICINA`, preserva código textual e recusa duplicação de chave. Quantidade e população são inteiros; densidade e decisões de limiar usam `Fraction(q * 1000, p)`. As coordenadas são lidas com `Decimal` antes da conversão para float64. A camada é lida diretamente do JSON, com conferência de código, nome, UF, período e invalidade do ponto original.

A geodésica independente é uma implementação vetorizada de **Vincenty inverso**, sem importar `nearest_reference.GEOD`, `nearest_exact`, o parser do projeto ou intermediários do motor. Usa `a = 6.378.137 m`, `f = 1/298,257222101`, tolerância de convergência de `10^-13` radianos, no máximo 200 iterações e erro explícito se não convergir. Todos os pares calculados convergiram. A busca é exaustiva: **5.570 × 2.007 = 11.178.990 pares**, em blocos de 128 alvos, sem poda por cordas.

O método segue as equações inversas de [Vincenty (1975), seções 3–4](https://geodesy.noaa.gov/PUBS_LIB/inverse.pdf). Sua limitação em pontos quase antípodas não ocorreu neste conjunto. O uso de esfera ou elipsoide corresponde a modelos geométricos distintos, conforme a [documentação do PROJ](https://proj.org/en/stable/geodesic.html).

Foram confrontadas as 5.570 densidades, classificações e referências mais próximas. Os conjuntos e as identidades da referência coincidiram integralmente. O maior desvio absoluto entre mínimos de Vincenty e do motor foi **9,8634700407 × 10^-10 km**, aproximadamente **0,000000986 m**, muito inferior à margem dos casos próximos de 155 km. A tolerância de conferência era `10^-6 km` (1 mm). Empates numéricos no auditor usam tolerância de `10^-9 km`; não houve divergência com os conjuntos de empates exatos do motor.

Para o primeiro quintil, a ordenação é municipal não ponderada por população. O quantil tipo 7 usa posição zero-based `h = (5570 − 1) × 0,2 = 1113,8`, interpolação racional e inclusão `densidade ≤ corte`. O corte exato é `157068200/149515409 = 1,0505151345303814`. Há 1.114 alvos; a maior densidade incluída é 1,0504937320540655 (Várzea da Roça/BA, `293305`) e a seguinte é 1,0505204851494605 (Sucupira do Norte/MA, `211190`). Não há empate exato nessa fronteira.

O arredondamento a duas casas, como experimento separado, usa Decimal `ROUND_HALF_UP`. O corte passa a 1,05: há 1.104 valores inferiores e 21 iguais, totalizando 1.125. `ROUND_HALF_EVEN` produz os mesmos conjuntos nessa base. Esse arredondamento cria empates que não existem na razão original.

## 6. Comparação controlada dos cenários

Em todas as linhas abaixo, a competência é `202406`, a categoria é `MEDICINA` e o universo de partida contém 5.570 municípios. “Alvos” significa os que atendem à condição de densidade/quintil antes da condição espacial. As populações são somas das mesmas linhas originais. Nenhum cenário foi ajustado para forçar o número 160.

| Cenário | Alvos | Referências | Selecionados | População selecionada |
| --- | --- | --- | --- | --- |
| A: densidade exata <2,36; GRS80 | 3.563 | 2.007 | 225 | 8.795.392 |
| B: Q1 exato; GRS80 | 1.114 | 2.007 | 159 | 3.526.500 |
| Q1 com 2 casas; referências exatas; GRS80 | 1.125 | 2.007 | 159 | 3.526.500 |
| Q1 exato; referências com 2 casas; GRS80 | 1.114 | 2.011 | 159 | 3.526.500 |
| Q1 e referências com 2 casas; GRS80 | 1.125 | 2.011 | 159 | 3.526.500 |
| A com limiar e referências em 2 casas; GRS80 | 3.559 | 2.011 | 225 | 8.795.392 |
| B exato; Haversine R=6371,0088 km | 1.114 | 2.007 | 160 | 3.546.239 |
| H candidato: Q1/referências com 2 casas; Haversine | 1.125 | 2.011 | 160 | 3.546.239 |


**A versus B isola apenas a definição dos alvos:** 3.563 → 1.114, redução de 2.449 candidatos; 225 → 159, redução de **66 selecionados e 5.268.892 habitantes**. B é subconjunto próprio de A. A API também foi executada com a lista Q1 independente como condição de pertença territorial e confirmou os mesmos 159, mantendo as 2.007 referências.

**B versus H isola a diferença espacial relevante depois dos testes de arredondamento:** +1 município e +19.739 habitantes. Arredondar apenas o quintil, apenas as referências ou ambos não muda o conjunto final com geodésica. Trocar só a geodésica por Haversine já produz os 160 e a população histórica, mesmo com 1.114 alvos e 2.007 referências. Arredondar também reproduz os dois totais intermediários históricos.

A ponte numérica completa é:

`225 − 66 + 0 + 1 = 160`

`8.795.392 − 5.268.892 + 0 + 19.739 = 3.546.239`

O zero representa o efeito final dos arredondamentos testados, não ausência de mudanças nos conjuntos intermediários. Essa decomposição é comprovada nos dados atuais; a atribuição desses procedimentos ao estudo anterior continua provável.

## 7. Diferenças territoriais e casos determinantes

### 7.1 Conjuntos comparados

| Comparação | Interseção | Exclusivos de A | Exclusivos do outro cenário | Diferença simétrica |
| --- | --- | --- | --- | --- |
| A (225) versus B (159, mesmo método) | 159 | 66 | 0 | 66 |
| A (225) versus H candidato (160) | 159 | 66 | 1 | 67 |
| B versus H candidato | 159 | 0 para B | 1 para H | 1 |

O CSV integral contém os 5.570 códigos, quantidade, população, fração exata e densidade decimal, pertença a ambos os quintis, condição de referência, coordenadas, referência mais próxima, distâncias, estados em A/B/H e motivos. A análise usa códigos, não diferenças de totais. A lista histórica verdadeira ainda não foi comparada porque não está disponível.

### 7.2 Epitaciolândia: caso mínimo da diferença geométrica

| Campo | Epitaciolândia/AC | Rio Branco/AC |
| --- | --- | --- |
| Código na base | 120025 | 120040 |
| Linha física do CSV, cabeçalho contado | 25150 | 101188 |
| Quantidade | 14 | 968 |
| População | 19.739 | 387.852 |
| Densidade por mil | 0,7092557880 | 2,4957973660 |
| Latitude | -11,02823983 | -9,978298753 |
| Longitude | -68,74486807 | -67,81052870 |
| Ponto complementado? | Não | Não |

Rio Branco é a referência mínima tanto com as 2.007 referências exatas quanto com as 2.011 arredondadas. Epitaciolândia pertence a ambos os Q1. Haversine supera o corte em 129,291 m; GRS80 fica abaixo em 248,505 m. A diferença entre modelos é 377,797 m, aproximadamente 0,244% da geodésica. Não é erro de arredondamento de float nem efeito da camada complementar.

Caso mínimo executável que evidencia **diferença de método, não defeito de software**:

```python
from math import radians, sin, cos, asin, sqrt
from pyproj import Geod
lat1, lon1 = -11.02823983, -68.74486807
lat2, lon2 = -9.978298753, -67.81052870
p1, p2 = radians(lat1), radians(lat2)
a = sin((p2-p1)/2)**2 + cos(p1)*cos(p2)*sin(radians(lon2-lon1)/2)**2
esfera = 6371.0088 * 2 * asin(sqrt(a))
elipsoide = Geod(a=6378137, rf=298.257222101).inv(lon1, lat1, lon2, lat2)[2] / 1000
print(elipsoide, esfera, elipsoide > 155, esfera > 155)
# aproximadamente 154.751494784, 155.129291429, False, True
```

### 7.3 Quatro referências acrescentadas por arredondar densidade

| Código | Município/UF | Quantidade | População | Densidade original |
| --- | --- | --- | --- | --- |
| 250310 | CABACEIRAS/PB | 13 | 5.515 | 2,3572076156 |
| 313490 | JACUTINGA/MG | 63 | 26.705 | 2,3591087811 |
| 315860 | SANTANA DO DESERTO/MG | 9 | 3.819 | 2,3566378633 |
| 354720 | SANTANA DA PONTE PENSA/SP | 4 | 1.698 | 2,3557126031 |


Todas têm densidade original abaixo de 2,36, mas arredondam para 2,36. Elas alteram nove distâncias mínimas no universo, incluindo as próprias distâncias que passam a zero; nenhuma mudança cruza o corte de 155 km. O conjunto de 225 e o de 159 permanecem idênticos por código.

### 7.4 Onze entradas adicionais no Q1 arredondado

| Código | Município/UF | Densidade original | Distância geodésica (km) |
| --- | --- | --- | --- |
| 210660 | MATOES/MA | 1,051051051 | 65,208196 |
| 210955 | RIBAMAR FIQUENE/MA | 1,053047255 | 46,287975 |
| 211190 | SUCUPIRA DO NORTE/MA | 1,050520485 | 133,113491 |
| 220640 | MONSENHOR GIL/PI | 1,052128168 | 55,492812 |
| 230040 | AIUABA/CE | 1,054852321 | 63,606077 |
| 291630 | ITAPEBI/BA | 1,052520787 | 44,991305 |
| 293015 | SERRA DO RAMALHO/BA | 1,052077854 | 69,489333 |
| 313110 | INIMUTABA/MG | 1,054435218 | 7,072217 |
| 314995 | PERIQUITO/MG | 1,053106665 | 16,891085 |
| 500568 | MUNDO NOVO/MS | 1,053317952 | 16,989260 |
| 510718 | RIBEIRAO CASCALHEIRA/MT | 1,054548941 | 128,511130 |


Nenhum desses onze municípios fica acima de 155 km. Por isso, 1.114 versus 1.125 não altera o conjunto final neste caso. A diferença de empates é material para a definição metodológica, mesmo com efeito final zero.

### 7.5 Sessenta e seis exclusivos do cenário atual

Todos os municípios da tabela seguinte têm densidade abaixo de 2,36, ficam acima de 155 km pela geodésica e estão fora tanto do Q1 exato quanto do Q1 com duas casas. **A razão da saída de A para B/H é a condição de primeiro quintil.** Distâncias abaixo estão arredondadas apenas para apresentação; o CSV conserva os valores calculados.

| Código | Município/UF | Densidade por mil | Referência mínima (código) | Distância (km) |
| --- | --- | --- | --- | --- |
| 110010 | GUAJARA-MIRIM/RO | 1,492435 | MONTE NEGRO (110140) | 229,104624 |
| 110033 | NOVA MAMORE/RO | 1,263335 | MONTE NEGRO (110140) | 223,333445 |
| 120005 | ASSIS BRASIL/AC | 1,283098 | RIO BRANCO (120040) | 219,574119 |
| 120020 | CRUZEIRO DO SUL/AC | 2,093879 | RIO BRANCO (120040) | 594,548173 |
| 130006 | AMATURA/AM | 1,139252 | RIO BRANCO (120040) | 732,496996 |
| 130008 | ANAMA/AM | 1,066098 | PORTO VELHO (110020) | 633,843153 |
| 130010 | ANORI/AM | 1,059558 | PORTO VELHO (110020) | 605,296203 |
| 130110 | CAREIRO/AM | 1,417915 | PORTO VELHO (110020) | 668,103929 |
| 130115 | CAREIRO DA VARZEA/AM | 1,060124 | BOA VISTA (140010) | 671,610093 |
| 130165 | GUAJARA/AM | 1,604800 | RIO BRANCO (120040) | 589,819884 |
| 130200 | ITAPIRANGA/AM | 1,480796 | BOA VISTA (140010) | 681,038736 |
| 130255 | MANAQUIRI/AM | 1,175848 | BOA VISTA (140010) | 691,028995 |
| 130260 | MANAUS/AM | 2,074847 | BOA VISTA (140010) | 662,003278 |
| 130300 | NHAMUNDA/AM | 1,137117 | BOA VISTA (140010) | 707,072095 |
| 130340 | PARINTINS/AM | 1,157362 | BOA VISTA (140010) | 744,309525 |
| 130353 | PRESIDENTE FIGUEIREDO/AM | 2,151254 | BOA VISTA (140010) | 543,821413 |
| 130356 | RIO PRETO DA EVA/AM | 1,205147 | BOA VISTA (140010) | 618,673077 |
| 130380 | SAO GABRIEL DA CACHOEIRA/AM | 1,471475 | BOA VISTA (140010) | 784,793575 |
| 130395 | SAO SEBASTIAO DO UATUMA/AM | 1,959664 | BOA VISTA (140010) | 672,230252 |
| 130400 | SILVES/AM | 1,612383 | BOA VISTA (140010) | 682,212086 |
| 130406 | TABATINGA/AM | 1,397286 | RIO BRANCO (120040) | 677,854612 |
| 140047 | RORAINOPOLIS/RR | 1,632786 | BOA VISTA (140010) | 209,611996 |
| 150060 | ALTAMIRA/PA | 1,744755 | TUCURUI (150810) | 289,753702 |
| 150145 | BELTERRA/PA | 1,477261 | TUCURUI (150810) | 599,228975 |
| 150180 | BREVES/PA | 1,625366 | BARCARENA (150130) | 207,298133 |
| 150360 | ITAITUBA/PA | 1,473624 | PARANAITA (510629) | 600,282666 |
| 150390 | JURUTI/PA | 1,501335 | TUCURUI (150810) | 736,454637 |
| 150550 | PARAGOMINAS/PA | 1,515380 | PRESIDENTE MEDICI (210923) | 183,683094 |
| 150680 | SANTAREM/PA | 1,659619 | TUCURUI (150810) | 580,446326 |
| 150812 | ULIANOPOLIS/PA | 1,414999 | AUGUSTINOPOLIS (170255) | 193,493478 |
| 150835 | VITORIA DO XINGU/PA | 1,827708 | TUCURUI (150810) | 278,204508 |
| 160015 | PEDRA BRANCA DO AMAPARI/AP | 1,377011 | BARCARENA (150130) | 447,475429 |
| 160023 | FERREIRA GOMES/AP | 1,539538 | BARCARENA (150130) | 386,398930 |
| 160027 | LARANJAL DO JARI/AP | 1,474887 | BARCARENA (150130) | 441,276319 |
| 160030 | MACAPA/AP | 2,169540 | BARCARENA (150130) | 319,925383 |
| 160050 | OIAPOQUE/AP | 1,377908 | BARCARENA (150130) | 691,299062 |
| 160053 | PORTO GRANDE/AP | 1,421951 | BARCARENA (150130) | 395,512271 |
| 160060 | SANTANA/AP | 1,706759 | BARCARENA (150130) | 326,528040 |
| 160070 | TARTARUGALZINHO/AP | 1,088139 | BARCARENA (150130) | 419,423640 |
| 171850 | RECURSOLANDIA/TO | 1,152406 | MIRACEMA DO TOCANTINS (171320) | 156,406045 |
| 172015 | SAO FELIX DO TOCANTINS/TO | 1,066667 | DIANOPOLIS (170700) | 161,620620 |
| 210140 | BALSAS/MA | 1,696609 | ARAGUAINA (170210) | 242,483544 |
| 210180 | BENEDITO LEITE/MA | 1,072003 | FLORIANO (220390) | 177,181479 |
| 210232 | BURITICUPU/MA | 1,089708 | IMPERATRIZ (210530) | 175,023448 |
| 210640 | MATA ROMA/MA | 1,311513 | PERITORO (210845) | 157,544146 |
| 210725 | NOVA COLINAS/MA | 2,138414 | LUZINOPOLIS (171245) | 204,209854 |
| 210970 | SAMBAIBA/MA | 1,578670 | PRESIDENTE DUTRA (210910) | 225,835521 |
| 211080 | SAO FELIX DE BALSAS/MA | 1,557286 | FLORIANO (220390) | 200,948145 |
| 220110 | AVELINO LOPES/PI | 1,170538 | IBOTIRAMA (291320) | 240,036077 |
| 220190 | BOM JESUS/PI | 2,110748 | FLORIANO (220390) | 294,279070 |
| 220290 | CORRENTE/PI | 1,308576 | BARREIRAS (290320) | 189,289099 |
| 220320 | CURIMATA/PI | 1,125346 | BARREIRAS (290320) | 246,106880 |
| 220760 | PARNAGUA/PI | 1,263485 | BARREIRAS (290320) | 217,031678 |
| 221120 | URUCUI/PI | 1,547111 | FLORIANO (220390) | 177,557325 |
| 230940 | NOVO ORIENTE/CE | 1,377268 | QUIXERAMOBIM (231140) | 168,222352 |
| 292600 | REMANSO/BA | 1,403640 | JUAZEIRO (291840) | 174,652033 |
| 430187 | BARRA DO QUARAI/RS | 1,152871 | MACAMBARA (431171) | 186,628993 |
| 510140 | ARIPUANA/MT | 1,114956 | PIMENTA BUENO (110018) | 252,359714 |
| 510335 | CONFRESA/MT | 1,678165 | DUERE (170730) | 263,578917 |
| 510510 | JUARA/MT | 1,615644 | NOVA MARINGA (510890) | 199,972876 |
| 510515 | JUINA/MT | 2,029289 | VILHENA (110030) | 209,174488 |
| 510627 | NOVO HORIZONTE DO NORTE/MT | 1,511944 | NOVA MARINGA (510890) | 181,203108 |
| 510680 | PORTO DOS GAUCHOS/MT | 1,230228 | NOVA MARINGA (510890) | 166,895748 |
| 510706 | QUERENCIA/MT | 1,542589 | AGUA BOA (510020) | 161,263767 |
| 510774 | SANTA CRUZ DO XINGU/MT | 1,058574 | GUARANTA DO NORTE (510410) | 276,835709 |
| 510788 | SERRA NOVA DOURADA/MT | 1,578117 | ARAGUACU (170200) | 194,208648 |


### 7.6 Identificação dos 159 comuns

Os códigos a seguir compõem simultaneamente B, A∩B e A∩H. Nomes, valores e referências de cada código estão no CSV integral e em `municipios_B.csv`.

```text
120030 120032 120033 120034 120035 120039 120042 120043 120060 130002
130014 130020 130030 130040 130050 130060 130063 130068 130080 130083
130090 130100 130120 130130 130140 130150 130160 130170 130180 130185
130190 130195 130210 130220 130230 130240 130250 130270 130280 130290
130310 130320 130330 130350 130360 130370 130390 130410 130420 130423
130426 130430 130440 140023 140040 140045 140050 140060 140070 150030
150040 150050 150070 150085 150100 150110 150172 150250 150285 150300
150310 150375 150445 150450 150475 150480 150503 150510 150530 150565
150580 150590 150600 150619 150670 150780 150797 150805 150815 160005
160010 160020 160021 160025 160040 160055 160080 170384 171240 210050
210080 210409 210410 210610 210950 211065 211157 211160 211200 220045
220070 220115 220130 220192 220250 220275 220300 220310 220323 220335
220360 220375 220440 220455 220552 220553 220590 220660 220665 220740
220870 220885 220890 220920 220930 220955 220975 221035 221135 290475
290590 292045 292440 293020 510035 510185 510269 510285 510325 510337
510517 510677 510735 510777 510785 510794 510860 520670 521270
```

## 8. Outras diferenças avaliadas, uma condição por vez

**Camada geográfica.** A fonte original tem seis coordenadas inválidas em cada competência. Em junho, quatro são referências e duas são alvos abaixo de 2,36. A camada não altera quantidade, população, densidade ou pertença às referências; recupera a avaliabilidade espacial.

| Código | Município/UF | Densidade | É referência? | Distância efetiva (km) |
| --- | --- | --- | --- | --- |
| 170100 | ANANAS/TO | 1,406866 | Não | 30,893056 |
| 350050 | AGUAS DE LINDOIA/SP | 3,781858 | Sim | 0,000000 |
| 421265 | PESCARIA BRAVA/SC | 2,373944 | Sim | 0,000000 |
| 422000 | BALNEARIO RINCAO/SC | 2,089864 | Não | 15,333319 |
| 430367 | CAMPESTRE DA SERRA/RS | 5,436424 | Sim | 0,000000 |
| 500490 | JARAGUARI/MS | 2,693603 | Sim | 0,000000 |


Entre os 5.564 pontos originalmente válidos, apenas Monte Sião/MG (`314340`), Imaruí/SC (`420720`) e Bandeirantes/MS (`500150`) mudam de referência mínima ao introduzir a camada. As distâncias passam, respectivamente, de 13,202137 para 7,335590 km, de 15,826062 para 6,775670 km e de 49,886952 para 21,475045 km. Nenhum cruza 155 km. Os seis complementados também não integram A ou B.

Sem camada e sem aceitar cobertura parcial, o motor retorna 0 `ATENDE`, 2.007 `NAO_ATENDE` e 3.563 `NAO_AVALIAVEL`. Isso **não equivale a demonstrar inexistência de municípios que atendem**. Com cobertura parcial aceita, retorna os mesmos 225 selecionados e dois não avaliáveis. Com camada, são os mesmos 225 e zero não avaliáveis. A distinção entre esses estados foi mantida na auditoria.

**Esfera e elipsoides.** Trocar somente GRS80 por WGS84 preserva A e B; a maior diferença entre mínimos é `2,4526 × 10^-8 km`. Trocar por esfera com raio 6.371,0088 km faz A ter 226 e B ter 160, com entrada de Epitaciolândia em ambos. O máximo desvio entre mínimos esféricos e elipsoidais no universo é 4,156310 km. A esfera de raio 6.371 km reproduz o mesmo H; a esfera de raio equatorial 6.378,137 km produziria 161 no Q1, acrescentando Buritinópolis/GO (`520396`). Os raios foram avaliados como convenções geométricas, não calibrados para obter 160.

**Métodos de quantil.** Os nove métodos de Hyndman–Fan disponíveis em NumPy foram avaliados sobre densidade não arredondada. Embora os cortes variem, todos selecionam os mesmos 1.114 municípios e os mesmos 159 remotos. Logo, somente trocar o estimador de quantil entre essas convenções não explica 1.125 ou 160. Não se aplicou ponderação populacional, que responderia a outra pergunta.

**Precisão da densidade.** Duas casas reproduzem 1.125/2.011; três casas produzem 1.114/2.007; quatro casas, 1.115/2.007; uma casa, 1.339/2.018. Truncar em duas casas, em vez de arredondar, produz 1.138/2.007. Essas sensibilidades evidenciam que arredondamento precisa fazer parte da documentação do método, sem constituir autorização para mudar o motor.

**Precisão da distância e operadores.** Arredondar a distância ao quilômetro inteiro antes de testar `>155` produz A=224 e B=158: São Félix do Araguaia/MT (`510785`), com 155,329117 km, passa a 155 e sai. Arredondar a uma ou duas casas não altera A/B. Nenhum município tem densidade exatamente 2,36 e nenhum mínimo está exatamente em 155 km; portanto `<` versus `≤` em 2,36 e `>` versus `≥` em 155 não explicam a diferença nesta base. O auditor não trocou os operadores dos cenários principais.

**Homônimos, duplicação e agregação.** Os códigos distinguem todos os municípios; não há duplicação de chave, quantidade ausente ou população não positiva em junho. A seleção de referências e o cálculo combinado recusam múltiplas linhas por território/categoria/período. Não há deduplicação de identificadores individuais porque eles não existem nos arquivos. A origem upstream dos quantitativos não pode ser auditada a partir de contagens agregadas.

**Versões e proveniência.** Os hashes fixam a versão atual, mas não há hash do levantamento anterior. O GeoPackage fonte das seis coordenadas não integra o material auditado; o JSON registra verificação pelo usuário e ausência de autenticação independente junto ao IBGE. Não se verificaram fisicamente todas as coordenadas originais contra limites territoriais oficiais. Esses limites não explicam por si sós o resultado, e nenhuma coordenada foi corrigida nesta investigação.

## 9. Classificação dos achados

| ID | Classificação | Natureza | Achado e evidência |
| --- | --- | --- | --- |
| F01 | COMPROVADO | Diferença metodológica | Trocar `<2,36` por Q1, mantendo o restante, retira 66 códigos: 225 → 159. CSV e cenários A/B. |
| F02 | COMPROVADO | Método/precisão | Densidade com duas casas produz exatamente 1.125 alvos e 2.011 referências; quatro referências e onze alvos adicionais identificados. |
| F03 | PROVÁVEL | Método histórico | O levantamento anterior teria arredondado densidades antes das seleções. A coincidência de dois totais é forte, mas falta registro do procedimento. |
| F04 | COMPROVADO | Método geográfico | Haversine acrescenta Epitaciolândia e reproduz 160/3.546.239; comparação exaustiva e caso mínimo. |
| F05 | PROVÁVEL | Método histórico | Uso histórico de distância esférica com raio próximo a 6.371 km. Quatro totais coincidem em H, mas não há script/lista histórica para autenticar. |
| F06 | DESCARTADO | Período/processamento | Mistura de competências como causa dos 225 reconstruídos: isolamento, perturbação fora do período e alternância de requisições não alteram junho. |
| F07 | DESCARTADO | Defeito de software, hipótese causal | Erro da busca otimizada como causa dos 225: todos os mínimos e referências conferem com busca exaustiva e fórmula independente. |
| F08 | COMPROVADO | Dados/avaliabilidade | Seis coordenadas inválidas e recuperação pela camada. O conjunto de aprovados não muda em relação ao alcance parcial; a cobertura muda. |
| F09 | DESCARTADO | Dados, hipótese causal | As quatro referências extras ou os onze empates adicionais, isoladamente, explicarem a diferença final: efeito zero sobre os conjuntos. |
| F10 | COMPROVADO | Universo/dados | Seis registros faltantes em competências antigas; nenhum em junho de 2024. Não são causa do resultado auditado. |
| F11 | INDETERMINADO | Dados históricos | Identidade da versão, lista e população do levantamento anterior; não há artefatos históricos verificáveis. |
| F12 | INDETERMINADO | Dados de origem | Deduplicação individual upstream, edição da população e validade física de todos os pontos; faltam microdados/metadados oficiais. |
| F13 | COMPROVADO | Testes/documentação | Aprovação técnica do cenário A não valida reprodução do estudo anterior; testes reais não incorporam sua lista nem seus métodos. |
| F14 | NÃO CONFIRMADO | Defeito de software | Defeito na implementação vigente que explique 225. Nenhum foi demonstrado no escopo; não é declaração de ausência universal de bugs. |
| F15 | DESCARTADO | Apresentação | Limite visual de linhas, arredondamento apenas visual ou ordenação explicarem as contagens: API contém 5.570 classificações e 225 códigos aprovados. |

## 10. Avaliação dos algoritmos e testes existentes

Execução desta auditoria: **150 passed, 1 warning in 276.64s (0:04:36)**. Sem alteração dos testes existentes. O log completo está em `testes.log`. Os avisos de depreciação do cliente HTTP não são falhas analíticas.

| Testes | O que validam | Independência e limites |
| --- | --- | --- |
| `test_nearest_real_data.py` | Referências por frações a partir do CSV; mínimos exaustivos de junho; todos os estados combinados com camada; seis pontos nas 22 competências; cobertura parcial. | Leitura e busca independentes, mas importa `GEOD` do próprio motor. O teste de junho com camada compara todos os municípios; o teste original sem camada verifica amostras. Não testa o Q1 como definição histórica. |
| `test_nearest_reference.py` | Busca otimizada contra exaustiva, empates, coordenadas inválidas/conflitantes, período obrigatório, categorias e limite exato de densidade. | As duas buscas compartilham `GEOD`; há também implementação Vincenty independente em 200 pares sintéticos e conferência polo a polo. Portanto a suíte não é inteiramente circular. |
| `test_combined_criteria.py` | Tabelas trivalentes, `<`/`≤`/`=`/`≥`, densidade exata 59/25.000, AND/OR/NOT, elegibilidade, universo, seleção, ranking e exportação. | Boa cobertura da semântica; o helper de distância usa `GEOD`. A fixture repete medidas em 2023/2024, limitando sua capacidade isolada de detectar vazamento temporal de medidas. |
| `test_real_data.py` | Densidades, quantitativos, denominadores e registros; distribuição tipo 7; séries e agregação. | Parte da construção esperada usa `read_dataset` do aplicativo, reduzindo independência do parser. O teste espacial legado aceita Haversine com `rtol=0.006`, `atol=0.002 km`; essa tolerância não assegura mesma classificação perto de 155 km. |
| `test_geo_complement.py` | Identidade, período, elegibilidade de pontos, nomes, versão, uploads sem camada e rastreabilidade. | Conferência numérica via outra instância de `pyproj.Geod`, não outra biblioteca geodésica. Não autentica o GeoPackage original nem a origem de cada ponto. |
| `test_split_period.py` | Composição ano/mês, valores inválidos, preservação das colunas e seleção de período. | Valida contrato estrutural; não substitui auditoria demográfica do período da população. |
| `test_brazil_cache.py`, `test_request_memo.py` | Integridade por requisição, versão, cópias, concorrência e isolamento do memo. | Sustentam ausência de contaminação por reutilização; ensaios adicionais desta auditoria verificaram o resultado nacional completo em junho. |

Os testes relacionados aos 225 **não tratam 225 como constante normativa**: o teste real mais completo constrói o conjunto esperado e compara estados por código; exige contagem positiva e coerência. Isso é melhor evidência que uma asserção isolada de total. Porém, seus critérios são `<2,36` e `>155`, não a pergunta histórica de Q1. Os valores 1.125, 2.011, 160 e 3.546.239 não integram uma validação histórica no repositório auditado.

As suítes reais são opt-in por `ADT_REAL_DATA_DIR`. O workflow `.github/workflows/ci.yml` não define essa variável para a suíte backend; aprovação do CI padrão pode omitir os testes reais mesmo com fontes versionadas. Nesta auditoria a variável foi definida explicitamente, e os testes selecionados não foram omitidos.

Lacunas relevantes: fixture científica histórica por código e hash; teste temporal adversarial em que quantidade, população e geometria variam separadamente; documentação da precisão antes de formar quintis; teste de classificação em torno de 155 km para modelos diferentes; proveniência upstream dos numeradores/denominadores. São recomendações, não correções executadas.

## 11. Questões ainda não resolvidas e limitações

Não foi fornecida uma relação histórica dos 160 códigos. A igualdade de quatro totais, inclusive população, torna H uma explicação consistente, mas não prova unicidade do conjunto nem identidade do fluxo original. As 66/1 exclusividades aqui apresentadas referem-se a **A versus H reconstruído**, jamais a uma lista histórica não vista.

Não foi possível comprovar qual fórmula, raio, precisão, coordenadas, versão dos quantitativos ou denominadores foram usados pelo levantamento anterior. Também não há informação suficiente para certificar se as coordenadas originais representam sede, centroide ou outro ponto em todos os municípios. O método atual segue o referencial declarado; a origem geodésica de cada ponto original não foi autenticada nesta auditoria.

A busca local em `.local` encontrou cópias e evidências de validação do aplicativo; algumas pastas antigas de pytest recusaram leitura por permissões do sistema. Não se alteraram permissões. Nenhum artefato histórico científico identificável foi localizado no material legível/versionado. Não foi feito fetch remoto nem presumido que o repositório local contém todo arquivo já produzido fora dele.

Não se executou uma nova jornada visual no navegador nem toda a suíte do produto. A apresentação foi inspecionada em código e os resultados foram verificados pela API. O objetivo foi auditar os cálculos pertinentes, não certificar integralmente o aplicativo. O relatório não avalia adequação clínica ou normativa do limiar médico, nem acesso por estrada, rios ou tempo de viagem.

## 12. Conclusão fundamentada

**A. Critérios diferentes:** COMPROVADO. Na mesma base/competência/geografia, o limiar de 2,36 seleciona 225; o Q1 exato seleciona 159. Há 66 municípios de diferença metodológica, identificados individualmente.

**B. Dados ou métodos distintos:** COMPROVADO quanto aos efeitos dos métodos experimentados, PROVÁVEL quanto à sua adoção histórica. Arredondar densidades explica 1.125 e 2.011 sem mudar o conjunto geodésico final. Haversine explica a entrada de Epitaciolândia, chegando a 160 e 3.546.239 habitantes. Não foi necessário trocar os dados para reproduzir todos os totais informados. Isso não prova que os arquivos históricos eram idênticos.

**C. Defeito de implementação:** NÃO CONFIRMADO como causa dos 225. O motor reproduz a definição atual, as referências e as distâncias foram verificadas independentemente, e os ensaios temporais não detectaram contaminação. Não há defeito causal demonstrado para apresentar ou corrigir. O caso mínimo de Epitaciolândia demonstra uma diferença de modelo geométrico, não uma falha no algoritmo vigente.

O diagnóstico mais sustentado é **diferença de pergunta analítica, combinada com diferença entre distância esférica e elipsoidal; a precisão da densidade explica os totais intermediários**. A atribuição histórica definitiva depende dos artefatos do levantamento anterior.

## 13. Recomendações para decisão humana

1. Obter a lista histórica dos 160 códigos, os dados originais/hash, o script e os parâmetros de distância e arredondamento. Comparar essa lista com H e testar especificamente Epitaciolândia.
2. Fixar a pergunta científica desejada: Q1 municipal com empates ou densidade abaixo de 2,36. São critérios diferentes; não selecionar um apenas porque produz a contagem conhecida.
3. Registrar precisão da densidade antes de ordenar/comparar, estimador de quantil, tratamento de empates, modelo de distância, elipsoide/raio e operadores de fronteira.
4. Documentar fonte, edição e significado da população e da quantidade de profissionais, inclusive não aditividade municipal. Arquivar a proveniência dos pontos e a premissa da camada.
5. Se autorizada em tarefa futura, ampliar a cobertura com fixtures científicas e casos adversariais de tempo/fronteira. Uma decisão de mudar método deve preceder qualquer alteração de código ou SPEC.
6. Manter distintos “execução correta do cenário A” e “reprodução do levantamento científico”. Não usar aprovação de testes técnicos como declaração de equivalência científica.

## 14. Evidências, reprodutibilidade e preservação

Todos os scripts e CSV auxiliares ficam em `C:/Users/User/AppData/Local/Temp/auditoria_160_225_20261014`, fora do repositório. Somente este relatório foi criado em `Docs/`. O diretório é temporário e deve ser preservado pelo responsável se desejar retenção permanente; não foi incorporado à aplicação.

| Evidência | Conteúdo |
| --- | --- |
| [comparacao_territorial.csv](C:/Users/User/AppData/Local/Temp/auditoria_160_225_20261014/comparacao_territorial.csv) | 5.570 municípios, estados A/B/H e causas |
| [diferencas_A_H_candidato.csv](C:/Users/User/AppData/Local/Temp/auditoria_160_225_20261014/diferencas_A_H_candidato.csv) | 67 diferenças por código entre A e H candidato |
| [diferencas_A_B.csv](C:/Users/User/AppData/Local/Temp/auditoria_160_225_20261014/diferencas_A_B.csv) | 66 diferenças, isolando a definição de alvo |
| [municipios_A.csv](C:/Users/User/AppData/Local/Temp/auditoria_160_225_20261014/municipios_A.csv) | 225 selecionados em A |
| [municipios_B.csv](C:/Users/User/AppData/Local/Temp/auditoria_160_225_20261014/municipios_B.csv) | 159 selecionados em B |
| [municipios_H_candidato.csv](C:/Users/User/AppData/Local/Temp/auditoria_160_225_20261014/municipios_H_candidato.csv) | 160 da reconstrução candidata, sem autenticação histórica |
| [independente.py](C:/Users/User/AppData/Local/Temp/auditoria_160_225_20261014/independente.py) | Releitura original, densidades e Vincenty exaustivo |
| [sensibilidades.py](C:/Users/User/AppData/Local/Temp/auditoria_160_225_20261014/sensibilidades.py) | Haversine, arredondamentos, quantis e qualidade temporal |
| [verificar_motor.py](C:/Users/User/AppData/Local/Temp/auditoria_160_225_20261014/verificar_motor.py) | API como objeto de teste e perturbações em memória |
| [inventario.json](C:/Users/User/AppData/Local/Temp/auditoria_160_225_20261014/inventario.json) | Hashes, registros, períodos, fonte nacional |
| [resultados_independentes.json](C:/Users/User/AppData/Local/Temp/auditoria_160_225_20261014/resultados_independentes.json) | Contagens e listas de todos os cenários principais |
| [sensibilidades.json](C:/Users/User/AppData/Local/Temp/auditoria_160_225_20261014/sensibilidades.json) | Conjuntos e evidências adicionais |
| [verificacao_motor.json](C:/Users/User/AppData/Local/Temp/auditoria_160_225_20261014/verificacao_motor.json) | Comparações numéricas e ensaios temporais |
| [motor_A.json](C:/Users/User/AppData/Local/Temp/auditoria_160_225_20261014/motor_A.json) | Resposta completa e parâmetros da API |
| [motor_B_resumo.json](C:/Users/User/AppData/Local/Temp/auditoria_160_225_20261014/motor_B_resumo.json) | Q1 independente executado como pertença territorial |
| [testes.log](C:/Users/User/AppData/Local/Temp/auditoria_160_225_20261014/testes.log) | Resultado da suíte selecionada |


`manifesto_evidencias.json`, no mesmo diretório temporário, registra os SHA-256 dos artefatos auxiliares desta execução. Esses hashes identificam as evidências salvas, não uma versão do levantamento histórico.

Ordem de reprodução (PowerShell, na raiz do repositório; ajustar apenas os caminhos locais de executáveis e saída ao ambiente):

```powershell
$auditDir = 'C:/Users/User/AppData/Local/Temp/auditoria_160_225_20261014'
$auditPython = 'C:/Users/User/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/python.exe'
& $auditPython "$auditDir/independente.py"
& $auditPython "$auditDir/sensibilidades.py"
python -B "$auditDir/verificar_motor.py"
$env:ADT_REAL_DATA_DIR = (Get-Location).Path
$env:PYTHONDONTWRITEBYTECODE = '1'
python -B -m pytest -q -p no:cacheprovider --basetemp "$auditDir/pytest_reexecucao" backend/tests/test_nearest_real_data.py backend/tests/test_nearest_reference.py backend/tests/test_combined_criteria.py backend/tests/test_real_data.py backend/tests/test_geo_complement.py backend/tests/test_split_period.py backend/tests/test_brazil_cache.py backend/tests/test_request_memo.py
```

O Python independente é 3.12.14, NumPy 2.3.5; o ambiente da aplicação é Python 3.12.10, NumPy 2.5.3, pandas 2.3.3, pyproj 3.8.0 e PROJ 9.8.1. O primeiro script precisa de NumPy e openpyxl apenas; lê o XLSX para verificar a fonte nacional, sem editá-lo. O segundo usa NumPy. O terceiro usa as dependências existentes do backend. Não foram instaladas bibliotecas ou alteradas dependências/configurações.

Os parâmetros estruturados exatos da API, mapeamento, fonte e árvore de critérios constam em `motor_A.json`; não há necessidade de interpretar uma frase em linguagem natural para reproduzir A. As razões e fórmulas acima também permitem reconstrução independente sem os scripts temporários.

Conferência final por SHA-256: **134 arquivos rastreados preexistentes verificados, zero alterados**. Evidência: `hashes_antes.json` e `integridade_final.json`. O relatório é a única adição autorizada no repositório. Nenhum dado, algoritmo, teste, parâmetro funcional ou SPEC foi alterado.
