# Base lógica Brasil — integração e validação em 10/10/2026

Implementação na branch `feat/portal-uma-pagina-v1`, exclusivamente no Teste-Agente.
As fontes são lidas sem alteração. Os dados residentes e as evidências de navegador
ficam em `.local/`, ignorada pelo Git; não houve publicação dos arquivos.

> **Atualização de 13/10/2026.** Desde o commit `a202be1` (12/10/2026), os dois arquivos
> originais estão versionados na raiz do repositório privado. As menções a fontes fora do
> Git refletem a situação de 10/10/2026. A política vigente está no README, em
> [Política dos dados do Brasil](../README.md#política-dos-dados-do-brasil); as cópias
> instaladas continuam em `.local/`, ignorada pelo Git.

> **Atualização do Bloco 2, Etapa 2 (13/10/2026).** O backend passou a ler diretamente os dois
> arquivos versionados na raiz, conferidos a cada requisição contra o manifesto governado
> `dados/brasil/manifesto.json` (tamanho e SHA-256); `.local/` não é mais lida, e uma pasta
> externa só é aceita de forma explícita, com a versão governada ou fixada. As menções abaixo à
> instalação obrigatória em `.local/` descrevem a situação anterior. Para os seis municípios com
> coordenadas inválidas, a camada geográfica complementar versionada
> `dados/brasil/complemento_coordenadas.json` (versão 1) **incorpora as coordenadas oficiais** da
> sede municipal: IBGE, Censo Demográfico 2022 — Localidades do Brasil (`BR_localidades_2022.gpkg`,
> SHA-256 `d057a1638b16…`), geometria pontual, SIRGAS 2000 (EPSG:4674), sob a premissa
> metodológica do usuário de uma coordenada fixa nas 22 competências de 2014 a 2024. As
> coordenadas foram extraídas e verificadas pelo usuário no exemplar do GeoPackage que ele
> forneceu; não houve autenticação independente do arquivo junto ao servidor do IBGE. Os arquivos
> originais não foram alterados: a substituição ocorre só ao ler coordenadas da base Brasil
> municipal, nessa versão da fonte, nos 132 registros com ponto inválido. A análise espacial da
> base completa em uma competência passou a ser executável, e a referência mais próxima e os
> critérios avaliam os 5.570 municípios. Detalhes:
> [Bloco 2, Etapa 2](BLOCO2_ETAPA2_CRITERIOS_INTEGRACAO.md).

> **Atualização de 19/10/2026: fonte estadual.** A base passou a ter três fontes: além da nacional e da
> municipal, `Dados_Estados_Brasil.csv`, com a contagem de médicos únicos por UF e competência (seção
> "Fonte estadual de médicos únicos", abaixo). Desde então, o estado é essa contagem, não a soma dos
> municípios; a população do estado continua vindo dos municípios. Versão governada `68944004901c…`
> (antes, `819cf4628bff…`; as fontes nacional e municipal não mudaram).

## Alterações dos campos e consumidores

| Estrutura anterior nos testes | Estrutura atual | Ajuste |
| --- | --- | --- |
| `Período` / `Competência` | `periodo_ano` + `periodo_mes` | Composição determinística AAAAMM em memória, reconhecida por regra (componentes validados), com linhagem |
| `ibge` | `cod_ibge` | Novo alias de código territorial; sugestão até ser escolhido no seletor (na base oficial, papel do perfil) |
| `categoria_profisional` | `categoria_profissional` | Alias correto já era suportado; testes atualizados, alias antigo preservado |
| `Contagem` / `Total de médicos únicos` | `quantidade` / `contagem` | Aliases existentes; unidade continua declarada pelo usuário |
| Nacional sem geografia/categoria explícitas | `pais`, `categoria_profissional` | Reconhecimento de país e uso da categoria da própria base |
| Coordenadas com vírgula | `latitude`, `longitude` | Separador decimal verificado nos dados (escolha só com formato misto); valor fora do intervalo não rebaixa a coluna |

O leitor comum atende inspeção, pré-exame, cálculo e contexto conversacional.
`dataset_normalization.py` mantém os campos originais; `semantic_bridge.py` reconhece
o campo derivado por regra conclusiva (os componentes são validados na importação). O motor mantém seus cálculos.
Filtros, multiplicidade e séries usam o mesmo período composto. Os metadados de
exportação registram a regra, os campos de origem, o recorte e a versão lógica.

## Uma base lógica, sem misturar granularidades

O catálogo `brazil_data.py` administra três fontes privadas (nacional, estadual e municipal). A interface
mostra somente Dados do Brasil e a abrangência analítica. A base é examinada uma vez, no recorte municipal,
com o bloco dos níveis; a caixa "Abrangência territorial" é uma lista vertical com o Brasil (total
nacional), os estados (médicos únicos da fonte estadual) e os municípios agrupados por estado
([abrangência territorial](ABRANGENCIA_TERRITORIAL.md)). Sem nada marcado vale o padrão da análise: o
Brasil em contagens, evolução temporal e relatórios; todos os municípios nas outras operações. A
interface envia a seleção em `options.abrangencia`, e o backend escolhe a fonte (rota municipal,
nacional ou de níveis) e refaz o pré-exame; trocar de análise não recarrega a base.

Não há união nem preenchimento de linhas entre fontes, e nenhuma fonte é somada à outra. Quantitativos
nacionais são lidos da fonte nacional; não são obtidos pela soma das contagens municipais. Desde
19/10/2026, a API aceita Brasil, estados e municípios como níveis da base oficial
([abrangência territorial](ABRANGENCIA_TERRITORIAL.md)), sempre em blocos separados e sem somar um nível a
outro: a densidade do Brasil combina a contagem nacional com a população municipal de junho do mesmo ano
(regra governada BR-POP-JUNHO-1), e o estado é a contagem de médicos únicos da fonte estadual, com a
população dos seus municípios (pelo prefixo do código IBGE) na própria competência (regras
UF-CONTAGEM-ESTADUAL-1 e UF-POP-MUNICIPIOS-1). A fonte estadual não é um recorte do pedido: ela é lida
só pela abrangência. Na agregação municipal e na de estados, a aditividade das populações e a soma dos
componentes são premissas internas da base oficial (seção seguinte), e o total conserva o rótulo de
possível dupla contagem.
Selecionar um recorte sem os requisitos necessários mantém a análise bloqueada.

## Premissas internas da base oficial

Decisão do responsável pelo produto (orientação de 18/10/2026): na base disponibilizada pela
plataforma, o usuário não confirma premissas de comparabilidade nem, nas análises de distância da
versão governada, o referencial e o separador decimal das coordenadas. `brazil_catalog_profile.py`
as aplica quando a fonte oficial é reconhecida (estrutura e categoria única MEDICINA, depois da
integridade conferida pelo manifesto), **campo a campo** (decisão D1 de 19/10/2026): cada papel cuja
coluna ainda é a canônica fica em `governed_roles`, e cada premissa vale só quando todos os papéis de
que depende estão governados. Mudar uma coluna não desliga o perfil inteiro: as premissas que
dependiam daquele papel passam à camada genérica (`analysis_premises.py`, com nota própria). As
opções aplicadas ficam em `governed_premises`, e cada resultado afetado traz a nota correspondente
em "Método e limitações". O usuário não declara nada em nome da fonte.

| Premissa (opção do motor) | Recortes | Análises | Origem |
|---|---|---|---|
| Papéis dependentes (todas as premissas) | — | — | `temporal`: período, categoria, contagem e território; identidade territorial: território, código e período; comparabilidade: contagem, população e território; populações: população e território; soma dos componentes: contagem e território; referencial: latitude e longitude; separador: latitude, longitude, contagem e população (só os papéis existentes no recorte contam) |
| Comparabilidade temporal (`temporal_comparability_confirmed`) | nacional e municipal | evolução temporal | regra do perfil: mesma fonte, categoria e unidade em todas as competências |
| Identidade territorial ao longo do tempo (`territory_longitudinal_confirmed`) | nacional e municipal | evolução temporal | verificada nos dados: um único território no recorte nacional; no municipal, cada código IBGE mantém o mesmo nome em todas as competências |
| Comparabilidade entre municípios (`comparison_confirmed`) | municipal | comparações e rankings | regra do perfil: mesma medida, unidade e população estimada em cada competência |
| Populações sem sobreposição (`population_additive_confirmed`) | municipal | agregação | regra do perfil: municípios são partes disjuntas do território nacional |
| Total como soma dos componentes (`component_sum_confirmed`) | municipal | agregação | regra do perfil: a base não identifica pessoas entre municípios; rótulo de possível dupla contagem |
| Referencial geodésico SIRGAS 2000 (`crs`) | municipal, só na versão governada | análise espacial, referência mais próxima e critérios com distância | regra do perfil: a fonte não declara o referencial; SIRGAS 2000 é o referencial da camada oficial do IBGE; nenhuma transformação |
| Vírgula como separador decimal das coordenadas (`number_format`) | municipal, só na versão governada | as mesmas | verificada nos dados: latitude e longitude preenchidas com vírgula decimal ou inteiras (ao menos uma com vírgula), e quantidade e população sem vírgula |

Verificação na versão governada (`819cf4628bff…`): 5.570 códigos e nenhum com mais de um nome
nas 22 competências. Faltam seis observações código–competência (três em janeiro de 2015 e uma
em junho de 2015, janeiro de 2017 e janeiro de 2020); elas continuam não avaliáveis nos
extremos da evolução, sem interpolação. Se uma versão futura falhar na verificação, a identidade
territorial não é aplicada e a evolução temporal fica impedida com o motivo ("Identidade territorial
ao longo do tempo não verificada"). Na mesma versão, as 122.534 linhas
municipais têm latitude e longitude preenchidas com vírgula decimal ou inteiras (132 latitudes e
44 longitudes inteiras), e quantidade e população estimada só com dígitos; sem essa evidência, o
separador decimal vira escolha do usuário.

### Regras governadas dos níveis territoriais (19/10/2026)

| Regra | O que faz | Onde vale |
|---|---|---|
| BR-POP-JUNHO-1 (decisão D4) | população do Brasil = soma da `população_estimada` dos municípios na competência de junho do ano, uma vez por município, usada em janeiro e em junho; município sem registro em junho não é estimado: a soma usa os municípios com registro, avaliável com limitações (`POPULACAO_NACIONAL_PARCIAL`) | densidade do Brasil na rota de níveis e taxa nacional de referência (D5) nas densidades da base oficial |
| UF-CONTAGEM-ESTADUAL-1 (19/10/2026) | contagem do estado = a da fonte estadual (médicos únicos dentro da UF e da competência), nunca a soma dos municípios; competência sem registro do estado é não avaliável | estados como objeto na rota de níveis |
| UF-POP-MUNICIPIOS-1 (19/10/2026) | população do estado = soma da `população_estimada` dos seus municípios na própria competência, uma vez por município, só com todos registrados; sem algum, a densidade do estado fica não avaliável (`DENOMINADOR_AUSENTE`), sem estimar | densidade, ranking, distribuição, comparação, evolução e agregação de estados |
| `brasil-cod-uf-prefix-1` | estado de cada município pelo prefixo do código IBGE (não pela coluna `uf`) | população dos estados, grupos de municípios e BR-POP-JUNHO-1 |
| NIVEIS-BR-UF-MUN-1 | Brasil, estados e municípios como universos separados, nunca somados entre si | rota de níveis |

Na versão governada: junho de 2024 soma 212.583.750 habitantes (densidade do Brasil 502.495 ÷ 212.583.750 ×
1.000 = 2,3638); junho de 2015 não tem o 430607 (CRISTAL DO SUL, RS), e a população de 2015 soma os 5.569
municípios com registro (204.450.315), com nota; nenhum ano tem população conflitante em junho. A
população de junho de 2016 inclui a linha do 251365 declarada PA na coluna `uf` (331.942), com nota de
qualidade da fonte.

### Fonte estadual de médicos únicos (19/10/2026)

**Procedência.** Planilha `medicos_unicos_municipios_estados_201401_202406.xlsx` (SHA-256
`51aa58879efc2b66b314e8e15d71cd0bf615ba23f79a6357f7c0cc9a7d637887`), entregue pelo responsável pelo produto
em 19/10/2026, com o pedido de integrar a contagem estadual à base. A aba "Estados" traz o título "MÉDICOS
ÚNICOS POR ESTADO", o subtítulo "Contagem distinta de chaves dentro da UF e competência — NÃO soma de
municípios" e uma tabela larga: uma linha por competência e uma coluna por UF. A planilha não fica
versionada; a procedência primária da contagem (sistema de origem e chave de unicidade) segue a mesma
pendência das demais fontes (README, ponto 9).

**Conversão.** `backend/build_state_source.py` confere a estrutura e grava os mesmos valores, sem somar,
estimar ou corrigir, em `Dados_Estados_Brasil.csv` (`uf;periodo_ano;periodo_mes;categoria_profissional;contagem`,
ponto e vírgula, fim de linha CRLF, como a fonte municipal; categoria MEDICINA, do título da aba). Resultado:
594 registros, 15.109 bytes, SHA-256 `7f64a828389d91228b30247787817701c8ffccdeee8b81234282c77926f936bc`,
registrado no manifesto governado. O teste `test_build_state_source.py` reproduz o arquivo versionado byte a
byte a partir dos registros e recusa, sem gravar, planilhas com outra estrutura.

**Validação (leitura independente da planilha e dos arquivos).** 27 UFs × 22 competências (janeiro e junho
de 2014 a 2024) = 594 registros, sem duplicidade de UF e competência, sem célula vazia, todas as contagens
inteiras e positivas, iguais às da planilha; as mesmas 22 competências das fontes nacional e municipal.
Em cada competência, Brasil ≤ soma dos estados ≤ soma dos municípios (junho de 2024: 502.495, 539.090 e
817.419), como esperado de contagens distintas em territórios maiores: quem atua em mais de um município
do estado conta uma vez no estado, e quem atua em mais de um estado conta em cada um.

**Limitações.**
- A fonte estadual não traz população: a do estado é a soma dos seus municípios na competência. Ela fica
  incompleta (densidade do estado não avaliável) em seis pares: RO (110110), MG (313000) e SP (353286) em
  janeiro de 2015, RS em junho de 2015 (430607) e janeiro de 2020 (431973) e SC em janeiro de 2017 (420555).
- No Distrito Federal, de janeiro de 2014 a junho de 2017 (oito competências), a contagem estadual supera a
  do seu único município (Brasília, 530010) na fonte municipal (em janeiro de 2014, 7.832 contra 4.640); a
  partir de janeiro de 2018, as duas coincidem. Uma contagem distinta não pode superar a soma das partes:
  as fontes divergem nesse período. Por decisão de integração, os valores entram como estão, com nota no
  resultado; a divergência foi levada ao responsável pelo produto.
- A população da PB em junho de 2016 inclui a linha do 251365 declarada PA na coluna `uf` (a mesma nota de
  qualidade da população do Brasil).
- A soma de estados não identifica pessoas: a agregação de estados é sempre a soma dos componentes, com
  possível dupla contagem.

Limites: a comparabilidade temporal é premissa do perfil, não comprovação metodológica da
fonte, cuja procedência primária segue pendente (README, ponto 9). O mesmo vale para o
referencial SIRGAS 2000, que não certifica o datum original. As duas premissas de distância só
entram nas análises que usam coordenadas: nas demais, o mapa continua com a configuração só de
apresentação e as opções do cálculo não mudam. A opção explícita de ausência de sobreposição
(`no_overlap_confirmed`), aceita só pela API desde 19/10/2026 (a tela não a oferece mais), continua
prevalecendo sobre a soma dos componentes, e um
referencial ou separador informado explicitamente pela API também prevalece (um referencial não
suportado ou o ponto decimal continuam recusados). Em outras versões da base, em bases importadas e
nos papéis que saíram do perfil, nenhuma confirmação é pedida: as mesmas condições são premissas da
análise (`analysis_premises`), com origem e nota; um `false` explícito na API continua recusando a
premissa.

O catálogo compartilha as rotas existentes com uploads. A requisição usa `dataset=brazil`,
`scope=national|municipal|auto` e a versão retornada por `/api/inspect`. Nenhum caminho
de arquivo é aceito do navegador. Fonte residente e upload são mutuamente exclusivos.
Os hashes das três fontes são verificados; uma fonte ausente ou alterada impede usar o catálogo.
A conversa recebe somente os estados técnicos já previstos, nunca linhas ou arquivos.

## Qualidade dos dados e aplicabilidade

Foram encontrados 22 períodos (janeiro e junho de 2014 a 2024), 22 linhas nacionais e
122.534 municipais. Os códigos distinguem 5.570 municípios; nomes isolados geram
11.528 registros em 5.324 grupos com mais de uma linha. Escolher o código (na base oficial, papel do
perfil) elimina essa ambiguidade sem somar municípios homônimos. Numa cópia importada da base
municipal, o código vem como sugestão no topo do seletor e a densidade fica numa escolha pendente
("Escolha a coluna do código territorial…") até a escolha; coordenadas e período são reconhecidos
por regra e a vírgula decimal é verificada nos dados.

| Capacidade | Validação nas fontes atuais |
| --- | --- |
| Quantitativos | Nacional, estadual e municipal, preservando as contagens de cada fonte: as 594 contagens estaduais iguais às da fonte, nunca a soma dos municípios, e, em cada competência, Brasil ≤ Σ estados ≤ Σ municípios (19/10/2026) |
| Densidade | Municipal, quantidade / população × 1.000; Brasil pela regra BR-POP-JUNHO-1 nas 22 competências, conferido com leitura independente (2,3638 em junho de 2024; 2015 com 5.569 municípios e a lista [430607]); estados pela contagem estadual ÷ população dos seus municípios na competência, nas 594 combinações, conferidos com leitura independente (SP 3,2390 em junho de 2024), com as seis densidades não avaliáveis por população incompleta (RO, MG e SP em 2015/1, SC em 2017/1, RS em 2015/6 e 2020/1); taxa nacional de referência nas densidades municipais (19/10/2026) |
| Distribuição | Quantidade e densidade, período único, quintis e empates conferidos |
| Comparações e rankings | Densidades e posições conferidas por período/categoria |
| Evolução temporal | Quantidade nacional; quantidade e densidade municipais; extremos ausentes e zeros respeitados; tendência CAP-TEN-01 igual a uma classificação independente (Fraction) nas séries completa e de junho, com as âncoras Brasil (Crescimento) e ANAMÃ 130008 em densidade de junho de 2021 a 2024 (Aceleração do crescimento) (19/10/2026); densidade do Brasil (BR-POP-JUNHO-1) em Crescimento com 22 observações na série completa e 11 na de junho; densidade dos estados com lacunas onde a população está incompleta (SP com 21 observações e RS com 20 na série completa; RS com 10 na de junho), classes iguais às da leitura independente |
| Agregação | Soma dos componentes como premissa (perfil oficial ou da análise), rotulada como possível dupla contagem; resultado não identificado como total nacional de pessoas únicas; "Todos os municípios" em junho de 2024 soma 817.419, com a nota de que não é o total do Brasil (502.495); agregação de estados pela soma das contagens estaduais (Região Norte 27.384; os 27 estados 539.090, acima do total do Brasil), sempre soma dos componentes (19/10/2026) |
| Espacial | Uma competência por vez (as coordenadas de nove municípios mudam entre competências; sem a escolha, a análise pede "Escolha uma competência no período da análise."). Com a camada complementar oficial, a base completa de uma competência é executável, com distâncias iguais à geodésica independente sobre as coordenadas efetivas (13/10/2026). Sem a camada, desde 19/10/2026 os seis municípios com ponto inválido ficam não avaliáveis (COORDENADA_INVALIDA) e os demais têm as mesmas distâncias do subconjunto válido, confrontado com Haversine; antes, o recorte inteiro era recusado |
| Rotatividade | Bloqueada corretamente: ausência de identificadores individuais longitudinais |
| Relatórios | Dados e densidades municipais, quantitativos nacionais e exportação CSV |

Há seis municípios com coordenadas fora dos intervalos válidos em cada período,
totalizando 132 linhas: ANANAS (170100), PESCARIA BRAVA (421265), BALNEARIO RINCAO
(422000), JARAGUARI (500490), CAMPESTRE DA SERRA (430367) e AGUAS DE LINDOIA (350050).
Exemplo: latitude `-63741`. Não é possível determinar a correção apenas pelo valor.
Também há coordenadas que variam ao longo do tempo. Não se corrigiram ou excluíram
linhas no aplicativo. O subconjunto válido existe somente no teste de distância.
(13/10/2026: a correção usa a camada complementar com as coordenadas oficiais do IBGE, sem
alterar os arquivos; ver a atualização no início deste documento.)

## Reproduzir a validação

### Resultados executados

| Verificação | Resultado |
| --- | --- |
| Suíte geral do backend | 105 passaram; 20 testes reais omitidos nessa execução por serem opt-in |
| Suíte com as duas fontes reais | 20 passaram, com comparações independentes e preservação dos hashes |
| Build do frontend (TypeScript + Vite) | Passou |
| Navegador: sessão e upload sintético | Passou; privacidade, teclado, densidade, CSV, conversa simulada e recuperação |
| Navegador: carrossel | Passou; dez análises, teclado, roda, gestos, seleção sem execução e responsividade |
| Navegador: catálogo Brasil | Passou; 22 linhas nacionais exportadas, 5.570 municípios no filtro, troca de recorte e retorno ao upload internacional |
| Navegador: upload municipal real | Passou; 122.534 linhas exportadas conferidas com Decimal, filtros, metadados, falha simulada de pré-exame e tela de 390 px |
| Integridade e Git | Originais e cópias com hashes idênticos; dados privados ignorados, nenhum CSV/XLS/XLSX rastreado pelo Git |

Os quatro fluxos de navegador terminaram sem erros JavaScript. No upload municipal,
o maior desvio absoluto na densidade exportada foi `5,91025063785 × 10⁻¹⁵`.
As evidências completas e capturas ficam somente em `.local/ui-validation/`.

O teste de atualização dos filtros identificou um botão habilitado durante o
pré-exame: o motor já recusava executar nesse intervalo. O botão de atualizar
resultados agora também fica desabilitado até a revalidação terminar; o teste
foi repetido e passou. Os cálculos analíticos não foram alterados.

Avisos não impeditivos: depreciação de httpx no cliente de testes Starlette, restrição
de escrita do cache pytest no sandbox e bundle Vite acima de 500 kB. A compilação e
os testes concluíram com sucesso. As chamadas ao provedor de IA foram simuladas;
esta validação não comprova disponibilidade ou quota do serviço externo.

### Comandos

```powershell
py -m pytest -q
$env:ADT_REAL_DATA_DIR = 'C:\Users\User\Desktop\Dados_Brasil'
py -m pytest -q backend/tests/test_real_data.py
cd frontend
npm.cmd run build
```

Com backend e Vite ativos, na raiz:

```powershell
python backend/tests/ui_session_smoke.py
python backend/tests/ui_carousel_smoke.py
python backend/tests/ui_brazil_smoke.py
python backend/tests/ui_smoke.py
```

> **Atualização (15/10/2026):** esses quatro roteiros usam a interface anterior ao redesenho
> conversacional e foram movidos para `backend/tests/legado/`. O README de lá traz o mapa do que
> cobriam e das lacunas. As verificações vigentes, inclusive com a base Brasil versionada, rodam
> no CI e pelo executor `backend/tests/run_ui_checks.py` (ver a seção "Testes" do README).

Os testes gerais usam fontes sintéticas e não precisam do catálogo real. Os testes
reais são opt-in e comparam os hashes dos originais antes e depois. O teste de upload
municipal confere o CSV exportado com Decimal, linha por linha. O teste do catálogo
confere exportação nacional, densidade municipal, troca de recorte, descarte de
escolhas, conversa simulada e retorno ao upload internacional. Não há chamadas
reais ao provedor de IA nos testes.

Para a futura operação online, será necessário disponibilizar as fontes autorizadas
ao backend e configurar o diretório ou adaptar o carregador isolado, preservando
versões, integridade e granularidades. Não existe caminho fixo para a Área de Trabalho
no carregador. Esta etapa não escolhe nem implementa hospedagem, Docker, armazenamento
em nuvem ou publicação; essas decisões não são necessárias à implementação local.
