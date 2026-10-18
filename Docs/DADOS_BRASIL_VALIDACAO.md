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

## Alterações dos campos e consumidores

| Estrutura anterior nos testes | Estrutura atual | Ajuste |
| --- | --- | --- |
| `Período` / `Competência` | `periodo_ano` + `periodo_mes` | Composição determinística AAAAMM em memória, com confirmação e linhagem |
| `ibge` | `cod_ibge` | Novo alias de código territorial; confirmação mantida |
| `categoria_profisional` | `categoria_profissional` | Alias correto já era suportado; testes atualizados, alias antigo preservado |
| `Contagem` / `Total de médicos únicos` | `quantidade` / `contagem` | Aliases existentes; unidade continua declarada pelo usuário |
| Nacional sem geografia/categoria explícitas | `pais`, `categoria_profissional` | Reconhecimento de país e uso da categoria da própria base |
| Coordenadas com vírgula | `latitude`, `longitude` | Formato já suportado mediante declaração; validação de intervalos mantida |

O leitor comum atende inspeção, pré-exame, cálculo e contexto conversacional.
`dataset_normalization.py` mantém os campos originais; `semantic_bridge.py` oferece
o campo derivado como proposta, não como confirmação. O motor mantém seus cálculos.
Filtros, multiplicidade e séries usam o mesmo período composto. Os metadados de
exportação registram a regra, os campos de origem, o recorte e a versão lógica.

## Uma base lógica, sem misturar granularidades

O catálogo `brazil_data.py` administra duas fontes privadas. A interface mostra
somente Dados do Brasil e a abrangência analítica. O padrão é nacional para contagens,
evolução temporal e relatórios; municipal para as outras operações. Nessas três análises,
as únicas com resultado nas duas fontes, o usuário escolhe a abrangência explicitamente; nas
demais, a preparação informa que só a fonte municipal se aplica. Trocar de recorte exige novas
confirmações.

Não há união, preenchimento ou soma entre fontes. Quantitativos nacionais são lidos
da fonte nacional; não são obtidos pela soma das contagens municipais. Na agregação
municipal, a aditividade das populações e a soma dos componentes são premissas internas da
base oficial (seção seguinte), e o total conserva o rótulo de possível dupla contagem.
Selecionar um recorte sem os requisitos necessários mantém a análise bloqueada.

## Premissas internas da base oficial

Decisão do responsável pelo produto (orientação de 18/10/2026): na base disponibilizada pela
plataforma, o usuário não confirma premissas de comparabilidade nem, nas análises de distância da
versão governada, o referencial e o separador decimal das coordenadas. `brazil_catalog_profile.py`
as aplica somente quando o perfil governado é reconhecido (estrutura, mapeamento canônico e
categoria única MEDICINA, depois da integridade conferida pelo manifesto). As opções aplicadas
ficam em `governed_premises`, e cada resultado afetado traz a nota correspondente em "Método e
limitações". O usuário não declara nada em nome da fonte.

| Premissa (opção do motor) | Recortes | Análises | Origem |
|---|---|---|---|
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
territorial não é aplicada e a confirmação volta à interface. Na mesma versão, as 122.534 linhas
municipais têm latitude e longitude preenchidas com vírgula decimal ou inteiras (132 latitudes e
44 longitudes inteiras), e quantidade e população estimada só com dígitos; sem essa evidência, o
separador decimal volta a ser pedido.

Limites: a comparabilidade temporal é premissa do perfil, não comprovação metodológica da
fonte, cuja procedência primária segue pendente (README, ponto 9). O mesmo vale para o
referencial SIRGAS 2000, que não certifica o datum original. As duas premissas de distância só
entram nas análises que usam coordenadas: nas demais, o mapa continua com a configuração só de
apresentação e as opções do cálculo não mudam. A declaração explícita de ausência de
sobreposição, nas opções avançadas, continua prevalecendo sobre a soma dos componentes, e um
referencial ou separador informado explicitamente pela API também prevalece (um referencial não
suportado ou o ponto decimal continuam recusados). Outras versões da base, bases importadas e
preparações com significados alterados mantêm todas as confirmações.

O catálogo compartilha as rotas existentes com uploads. A requisição usa `dataset=brazil`,
`scope=national|municipal|auto` e a versão retornada por `/api/inspect`. Nenhum caminho
de arquivo é aceito do navegador. Fonte residente e upload são mutuamente exclusivos.
Ambos os hashes são verificados; uma fonte ausente ou alterada impede usar o catálogo.
A conversa recebe somente os estados técnicos já previstos, nunca linhas ou arquivos.

## Qualidade dos dados e aplicabilidade

Foram encontrados 22 períodos (janeiro e junho de 2014 a 2024), 22 linhas nacionais e
122.534 municipais. Os códigos distinguem 5.570 municípios; nomes isolados geram
11.528 registros em 5.324 grupos com mais de uma linha. Confirmar o código elimina
essa ambiguidade sem somar municípios homônimos.

| Capacidade | Validação nas fontes atuais |
| --- | --- |
| Quantitativos | Nacional e municipal, preservando as contagens de cada fonte |
| Densidade | Municipal, quantidade / população × 1.000 |
| Distribuição | Quantidade e densidade, período único, quintis e empates conferidos |
| Comparações e rankings | Densidades e posições conferidas por período/categoria |
| Evolução temporal | Quantidade nacional; quantidade e densidade municipais; extremos ausentes e zeros respeitados |
| Agregação | Apenas soma explicitamente autorizada; resultado não identificado como total nacional de pessoas únicas |
| Espacial | Base completa bloqueada por coordenadas inválidas; cálculo confrontado com Haversine em subconjunto de teste válido (13/10/2026: executável com a camada complementar oficial, distâncias iguais à geodésica independente sobre as coordenadas efetivas) |
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
confirmações, conversa simulada e retorno ao upload internacional. Não há chamadas
reais ao provedor de IA nos testes.

Para a futura operação online, será necessário disponibilizar as fontes autorizadas
ao backend e configurar o diretório ou adaptar o carregador isolado, preservando
versões, integridade e granularidades. Não existe caminho fixo para a Área de Trabalho
no carregador. Esta etapa não escolhe nem implementa hospedagem, Docker, armazenamento
em nuvem ou publicação; essas decisões não são necessárias à implementação local.
