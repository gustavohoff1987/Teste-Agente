# Teste Agente — Portal Experimental

Experimento isolado de desenvolvimento para o **Agente Diagnóstico Territorial da Força de Trabalho na Saúde**.

- **Interface:** React + TypeScript + Tailwind numa **página única de análise** (desde 22/10/2026). Primeiro, o aceite de privacidade. No alto, o nome do agente e três ações: Nova sessão, Nova análise e Histórico. Logo abaixo, a fonte dos dados: "Dados do Brasil" ou "Enviar meus dados", com o resumo da fonte em uso e "Trocar". Depois, a área de análise: o gráfico de bolhas com as análises, as funções e os Detalhes ([área de análise](Docs/PAINEL_INTEGRADO_INTERFACE.md)). A conversa fica numa caixa flutuante com o rosto do agente, sempre na página, e muda o gráfico ("mostre o Pará", "compare Manaus e Tefé"). Não há catálogo de análises, preparação, tela de resultados nem mapa: as telas clássicas saíram do produto em 22/10/2026, e o motor (`/api/analyze` e as capacidades) continua. Veja [Interface conversacional integrada](Docs/INTERFACE_CONVERSACIONAL_INTEGRADA.md).
- **Histórico:** "Nova análise" guarda a análise em exibição no Histórico e volta ao começo do gráfico com os mesmos dados; o Histórico reabre a análise guardada como estava, sem recalcular. A investigação progressiva com diagnósticos compostos saiu em 22/10/2026 (histórico em [investigação territorial progressiva](Docs/ANALISE_EXPLORATORIA_INTEGRADA.md)).
- **Motor:** Python + FastAPI; as dez capacidades do contrato conversacional, a referência geográfica mais próxima (Bloco 2, Etapa 1) e os critérios combinados com réguas, rankings e recortes (Bloco 2, Etapa 2) são determinísticos.
- **Conversa opcional:** integração experimental com Gemini para propor interpretações de solicitações. A API de LLM não recebe a base, não executa análises nem confirma parâmetros automaticamente.
- **Documento de referência:** IMPLEMENTATION_SPEC.md v1.2.4, **apenas para os contratos metodológicos e semânticos**. A interface e a arquitetura física são novas, independentes das diretrizes de UX daquele projeto.
- **Gemini não é requisito para o funcionamento analítico.** Sem chave, as orientações locais sobre capacidades, importação, privacidade e conceitos continuam disponíveis; a interpretação aberta pelo Gemini requer configuração. Todas as capacidades analíticas continuam operacionais. Esta integração é apenas a primeira iteração e **não representa conformidade integral com a governança de LLM da SPEC**.

## Executar localmente

Requer Python 3.11+ e Node.js 20+.

Terminal 1:
```bash
cd backend
python -m venv .venv
# Windows PowerShell: .venv\\Scripts\\Activate.ps1
# macOS/Linux: source .venv/bin/activate
pip install -r requirements.txt
uvicorn main:app --reload --port 8000
```

Terminal 2:
```bash
cd frontend
npm install
npm run dev
```

Abrir `http://localhost:5173`. O Vite encaminha `/api` ao FastAPI local.
Documentação da API: `http://localhost:8000/docs`.

## Duas formas de carregar dados

**Dados do Brasil** verifica e disponibiliza as três fontes conjuntamente em
uma sessão lógica: `Dados_Brasil.xlsx` (nacional), `Dados_Estados_Brasil.csv` (estadual: médicos
únicos por UF, desde 19/10/2026) e `Dados_Municipios_Brasil.csv` (municipal). O usuário não precisa
escolher os arquivos separadamente, e os registros das fontes não são concatenados. A base é examinada
uma vez, no recorte municipal, com o bloco dos níveis (Brasil, estados e regras de cada análise); uma nova
análise não recarrega a base. Na página única, o gráfico começa pelos 27 estados, e um clique num estado
abre os municípios dele; nunca os 5.570 municípios de início ([área de análise](Docs/PAINEL_INTEGRADO_INTERFACE.md)).
A API de análise (`/api/analyze`) continua aceitando a seleção de níveis em `options.abrangencia` (Brasil,
estados e municípios): sem seleção vale o padrão de cada análise (o Brasil em quantitativos, evolução
temporal e relatórios; todos os municípios nas demais), mistura de estados e municípios em distribuição,
ranking e agregação, ou territórios de menos, volta como escolha pendente, com o motivo, e o backend
resolve a rota e confere o pedido; nada é calculado na tela. A caixa **Abrangência territorial** das telas
clássicas, que montava essa seleção numa lista vertical, saiu em 22/10/2026.

As fontes mantêm suas granularidades: não há junção de linhas nem soma automática de pessoas
entre municípios, e o total do Brasil nunca é a soma municipal. **Brasil, estados e municípios**
(19/10/2026) são níveis da base oficial na API (`options.abrangencia`), sempre em blocos separados e
nunca somados entre si: o Brasil é a contagem nacional, com densidade pela população municipal de
junho do mesmo ano (regra governada BR-POP-JUNHO-1: 2,3638 por 1.000 habitantes em junho de 2024; em
2015, falta o 430607 em junho e a população soma os 5.569 municípios com registro, com limitação); o
estado é a contagem de médicos únicos da fonte estadual (regra UF-CONTAGEM-ESTADUAL-1: quem atua em
mais de um município do estado conta uma vez; nunca a soma dos municípios), com densidade pela
população da própria competência, a soma dos seus municípios pelo prefixo do código IBGE (regra
UF-POP-MUNICIPIOS-1: São Paulo, junho de 2024, 148.909 ÷ 45.973.194 × 1.000 = 3,2390); sem algum
município do estado na competência, a população não é estimada e a densidade do estado fica não
avaliável (DENOMINADOR_AUSENTE), com a contagem preservada. Quem atua em mais de um estado conta em
cada um: a soma dos estados (539.090 em junho de 2024) não é o total do Brasil (502.495), e a
agregação de estados é sempre a soma dos componentes, com possível dupla contagem. A conversa marca
estados ("Quantos médicos havia em Minas Gerais em junho de 2024?", "estados da Região Norte") e
pergunta quando o nome também é de município ("São Paulo"). Nas
densidades da base oficial, o resultado de `/api/analyze` traz a taxa nacional como referência de contexto
(`metadata.referencia_nacional`, com a série nacional em `metadata.referencia_nacional.serie`), que não
classifica nem colore os municípios. A marca dessa referência na legenda do mapa, nas barras e no cabeçalho
do resultado saiu com as telas clássicas em 22/10/2026. Detalhes:
[abrangência territorial](Docs/ABRANGENCIA_TERRITORIAL.md). Na agregação
municipal da base oficial, o total é a soma dos componentes, sempre rotulada como possível
dupla contagem; em bases importadas, a soma dos componentes também é a premissa padrão da
agregação, com nota e a limitação SOMA_COM_POSSIVEL_DUPLA_CONTAGEM, e o usuário pode escolher
outro total (pessoas distintas pelo identificador, quando houver).

A plataforma reconhece automaticamente as associações e significados da base Brasil
quando a fonte é a base oficial íntegra (estrutura esperada e categoria única MEDICINA) do
perfil governado (`backend/brazil_catalog_profile.py`). O perfil vale **campo a campo**: cada
papel cuja coluna ainda é a canônica fica reconhecido pelo perfil, e mudar uma coluna tira só
aquele papel (as premissas que dependem dele passam à camada genérica). A unidade de contagem do
catálogo é pessoas por território/período, só com a contagem do perfil; isso **não** implica
identidade única entre municípios ou meses. Nenhum perfil é aplicado ao upload do usuário, a
estruturas desconhecidas ou a categorias inesperadas.

**Sem confirmações de colunas e campos** (decisão do responsável pelo produto, 19/10/2026), em
nenhuma análise e em nenhuma base. O usuário só **escolhe** colunas e parâmetros. Um papel fica
estabelecido por regra conclusiva (alias governado; período AAAAMM composto e validado; latitude e
longitude com nome do vocabulário e valores num formato decimal único), pelo perfil oficial ou pela
escolha no seletor do painel "Colunas" (planilhas enviadas). Sugestões não conclusivas (código territorial,
UF, região, padrão de contagem, categoria sugerida pelo cabeçalho) deixam o seletor vazio, com a sugestão
no topo marcada "(sugerida)"; escolher a coluna a estabelece, e uma sugestão nunca é usada sem escolha. Na
API, o objeto de análise é o texto informado e o período único é uma opção de período (a página única pede o
objeto só quando a planilha não tem coluna de categoria, e não oferece o período único); o separador decimal das coordenadas é verificado nos dados (só vira escolha quando
o formato é misto); o referencial continua um parâmetro. As antigas declarações viram **premissas** aplicadas pelo backend
(`backend/analysis_premises.py`), com origem (`PERFIL_GOVERNADO`, `VERIFICADA_NOS_DADOS`,
`PREMISSA_DA_ANALISE`, `DECLARADA_PELO_USUARIO`), nota em "Método e limitações" e limitação
quando cabível; um valor `false` explícito na API continua recusando a premissa. Na rotatividade,
unidade sem registro em um dos períodos fica não avaliável (SEM_REGISTRO_OBSERVADO). O contrato da
API mantém `confirmed_roles` (papéis escolhidos), `needs_confirmation` (escolha pendente) e
`confirmed`; cada requisito traz `kind` (`escolha` ou `dados`) e `step`. Valor fora da faixa não
impede o reconhecimento da coluna de coordenada. Na análise espacial, coordenada ausente, não
numérica ou fora dos intervalos deixa só aquele território não avaliável (RQ-DAD-25: linha com
"Distância (km)" vazia e "Condição" "Não avaliável: coordenada inválida" ou "… ausente"); um território de referência sem coordenada válida é recusado com "O território de referência
não tem coordenada válida na competência escolhida. Escolha outro território de referência.", e
coordenadas válidas diferentes para o mesmo território pedem "Escolha uma competência no período da
análise.". Na base oficial, a análise espacial pede uma competência.

**Premissas internas da base oficial.** Com o perfil governado reconhecido, a interface não
pede ao usuário as confirmações de comparabilidade. O backend as resolve e registra a origem de
cada uma em "Método e limitações" e nas opções exportadas (`governed_premises`). Comparabilidade
temporal, comparabilidade entre municípios, populações municipais sem sobreposição e agregação
como soma dos componentes são regras do perfil, decididas pelo responsável pelo produto em
18/10/2026. A identidade territorial ao longo do tempo só vale depois de verificada nos dados:
cada código IBGE mantém o mesmo nome em todas as competências. Sem essa evidência, a premissa não é
aplicada e a análise temporal fica impedida com o motivo. Nas análises de distância da versão governada (análise espacial, referência
mais próxima e critérios com distância), também são internos o referencial SIRGAS 2000, regra do
perfil porque a fonte não declara o referencial, e a vírgula como separador decimal das
coordenadas, verificada nos dados. Em bases importadas e nos papéis que saíram do perfil, as mesmas
condições são premissas da análise (`analysis_premises`), com nota, sem caixas de declaração.
Detalhes em [validação da base Brasil](Docs/DADOS_BRASIL_VALIDACAO.md#premissas-internas-da-base-oficial).

Na abertura, a caixa da conversa pergunta o que a pessoa quer analisar e se prefere começar com os
dados do Brasil ou enviar os seus, com os dois botões; a escolha também vale por mensagem ("usar dados
do Brasil", "enviar meus dados"). A pergunta sobre o conteúdo dos dados brasileiros consulta
`/api/brazil/description`, que verifica as fontes e devolve apenas informações agregadas sobre período,
categorias e recortes, sem enviar registros ao Gemini. Pedidos explícitos sobre estados e municípios
mudam o gráfico ("mostre o Amazonas", "compare Manaus e Tefé"), sem solicitar detalhes sobre os
arquivos internos.

Períodos são apresentados em português (por exemplo, junho de 2024).
Quantitativos e relatórios podem mostrar vários períodos **separadamente**; análises
temporais podem restringir a seleção a múltiplos períodos. A agregação territorial
continua restrita a uma competência, para não tratar pessoas observadas em meses
diferentes como pessoas únicas. Fora do perfil governado, as premissas metodológicas são aplicadas
pelo backend e registradas no resultado; nenhuma confirmação é pedida.

**Enviar meus dados** aceita CSV, XLS e XLSX de qualquer país, até 30 MB, com a escolha da aba quando o
arquivo tem mais de uma. A planilha é lida com a estrutura da base do Brasil: unidade territorial (município,
distrito, condado…), código, grupo territorial (estado, província…), período, categoria, quantidade, população,
latitude e longitude, e o identificador individual para a rotatividade. O painel curto **"Colunas"**, no alto da
página, mostra o que foi reconhecido e pede só as escolhas que faltam:
- as colunas ambíguas, com a sugestão no topo, marcada "(sugerida)", nunca usada sem escolha;
- o que a quantidade conta (pessoas, vínculos, postos ou outra unidade, descrita);
- sem coluna de categoria, quem são os trabalhadores contados (por exemplo, médicos), que vira o objeto da análise;
- os nomes da unidade e do grupo, no singular e no plural, sugeridos pelo nome da coluna ("distrito" e
  "distritos", "província" e "províncias"). Eles valem nos textos da página e da conversa: com uma planilha, nenhum
  texto da estrutura diz "município";
- com latitude e longitude, o referencial em que as coordenadas foram coletadas: SIRGAS 2000 ou WGS 84 (este desde
  22/10/2026, pelo Adendo REF-20261022 da SPEC), e o sistema não converte um no outro: a distância é calculada no
  elipsoide do referencial informado (GRS80 ou WGS 84); com outro, ou sem saber qual é, a análise espacial fica
  indisponível, com o motivo, e nada é presumido. A base do Brasil continua em SIRGAS 2000.

O painel mostra também cada análise que a planilha permite ou não, com o motivo (sem as coordenadas não há
análise espacial; sem o identificador individual não há rotatividade). As duas fontes usam o mesmo motor, as mesmas
exportações e a mesma verificação contextual do agente. Nenhum registro é enviado ao provedor de IA. Detalhes em
[interface conversacional](Docs/INTERFACE_CONVERSACIONAL_INTEGRADA.md#fonte-de-dados).

### Teste de navegação conversacional

Com as dependências de `backend/requirements-ui.txt` instaladas e depois de `npm run build`
em `frontend/`, execute na raiz:

```bash
python backend/tests/run_ui_checks.py --suite conversa
```

O executor sobe o servidor local com o catálogo sintético do Bloco 1, roda o roteiro
`ui_conversa_grafico.py` e encerra o servidor. O teste bloqueia requisições externas e verifica as
respostas locais, a escolha da fonte pela conversa, os pedidos que mudam o gráfico com o contexto do
gráfico, os esclarecimentos pendentes e uma planilha enviada pela conversa, sem nada calculado pela
conversa. Também é executado no job `ui-conversational` do CI. As bases brasileiras reais não participam
desse teste: elas são verificadas pelos jobs `dados-reais` e `ui-block1` (suíte
`base-versionada`). Ver [Testes](#testes) e [Política dos dados do Brasil](#política-dos-dados-do-brasil).

### Origem da base Brasil (administração)

O backend lê diretamente os três arquivos versionados na raiz deste repositório privado,
`Dados_Brasil.xlsx`, `Dados_Estados_Brasil.csv` e `Dados_Municipios_Brasil.csv`, conferindo a cada
requisição o tamanho e o SHA-256 de cada um contra o manifesto governado `dados/brasil/manifesto.json`. Não há cópia
intermediária nem fallback: `.local/` não é lida. Arquivo alterado ou manifesto ausente,
desatualizado ou inválido tornam a base indisponível, com o motivo; o upload continua
funcionando. A API rejeita uma versão diferente daquela inspecionada pela interface.

```bash
python backend/brazil_data.py diagnostico          # origem física, versão e integridade
python backend/brazil_data.py manifesto            # identidade atual dos arquivos versionados
python backend/brazil_data.py manifesto --gravar   # só ao atualizar os arquivos, com revisão no Git
python backend/build_state_source.py <planilha.xlsx> [--gravar]  # fonte estadual a partir da planilha de médicos únicos
```

A fonte estadual vem da planilha de médicos únicos por estado entregue pelo responsável pelo produto
(aba "Estados", uma coluna por UF e uma linha por competência). `build_state_source.py` confere a
estrutura (título e subtítulo que declaram a contagem distinta dentro da UF, as 27 UFs, competências
AAAAMM únicas e contagens inteiras positivas) e grava os mesmos valores, sem somar nem estimar, no
formato das demais fontes; qualquer divergência recusa a conversão sem gravar.

Para responder mais rápido, o backend guarda por processo o quadro interpretado de cada versão verificada
e, sobre ele, os resultados que dependem só da versão: perfis das colunas, pré-exame, perfil da fonte e
catálogo territorial. A integridade continua conferida a cada requisição, antes de qualquer reaproveitamento.
Cada requisição recebe a sua cópia. Uma versão nova nunca reaproveita a anterior, e uploads nunca são guardados.
`ADT_BRASIL_CACHE_MAX_MB=0` desliga tudo isso. Ao iniciar, o servidor também faz em segundo plano a primeira
inspeção da base e carrega a biblioteca conversacional; a primeira requisição à base espera esse
aquecimento em curso. `ADT_AQUECIMENTO=0` desliga o aquecimento. Medições e salvaguardas:
[otimização de latência](Docs/OTIMIZACAO_LATENCIA.md).

Uma instalação externa continua possível para outra infraestrutura: `ADT_BRASIL_DATA_DIR`
aponta para uma pasta preparada por `python backend/install_brazil_data.py --source .
--destination <pasta nova>` (o instalador copia apenas a versão governada e recusa sobrescrever).
Ela só é aceita com a versão governada ou com a versão fixada exatamente em
`ADT_BRASIL_DATA_VERSION`; versão divergente é recusada. Não publique cópias em outros
repositórios nem no diretório público do frontend. O diagnóstico técnico também está em
`GET /api/brazil/source` e na área “Diagnóstico técnico da fonte” da interface (sem conteúdo).

Para uma futura operação online, será necessário disponibilizar as fontes autorizadas
ao backend e configurar esse diretório ou adaptar o carregador para outra origem,
preservando o contrato de versão, integridade e granularidade. Os dados devem continuar
fora dos arquivos públicos do frontend e de qualquer repositório público. A escolha de infraestrutura, o
provisionamento e a publicação ficam para uma etapa futura; não foram implementados.

Campos `periodo_ano` e `periodo_mes` são preservados e compõem **Período (ano e mês)**
em memória, no formato AAAAMM (ano × 100 + mês), reconhecido por regra conclusiva: componentes
inválidos são rejeitados na importação. Se a base já tiver outra coluna de período reconhecida pelo
nome, a composição fica como sugestão. A transformação e a versão da base constam em **Método e
parâmetros**. Cabeçalhos antigos continuam suportados.

Limitações verificadas nas fontes de 10/10/2026: não há população ou coordenadas no
recorte nacional (a densidade do Brasil usa a população municipal de junho, por regra governada;
ver [abrangência territorial](Docs/ABRANGENCIA_TERRITORIAL.md)), nem identificadores individuais em
qualquer recorte. A fonte estadual também não tem população: a do estado é a soma dos seus municípios
na competência, incompleta em seis pares de estado e competência (RO, MG e SP em janeiro de 2015; RS em
junho de 2015 e janeiro de 2020; SC em janeiro de 2017), em que a densidade do estado não é avaliada.
No Distrito Federal, de janeiro de 2014 a junho de 2017, a contagem estadual supera a do seu único
município na fonte municipal; as duas fontes entram como estão, com nota no resultado. Há 132 linhas
municipais com coordenadas fora dos intervalos válidos na fonte original (seis municípios nos
22 períodos). Com a camada geográfica complementar oficial incorporada (ver os dez pontos
abaixo), as análises espaciais da base Brasil municipal usam, somente nesses 132 registros, o
ponto oficial da sede municipal: a análise espacial (distância a um território de referência) da
base completa em uma competência passou a ser executável, e a referência mais próxima e os
critérios avaliam os 5.570 municípios. Bases importadas não recebem o complemento; nelas, ponto
inválido continua não avaliável (`COORDENADA_INVALIDA`), só naquele território. Rotatividade não pode ser calculada
dessas contagens. Nenhum registro foi corrigido ou excluído nos arquivos.
Detalhes e cobertura: [validação da base Brasil](Docs/DADOS_BRASIL_VALIDACAO.md).

### Política dos dados do Brasil

Situação vigente em 13/10/2026, enquanto esta for a política de distribuição:

1. **Versionamento.** `Dados_Brasil.xlsx` e `Dados_Municipios_Brasil.csv` estão versionados
   na raiz deste repositório privado desde o commit `a202be1` (12/10/2026), e
   `Dados_Estados_Brasil.csv` desde 19/10/2026. SHA-256 dos arquivos versionados:
   `7caa74d7a49f2f7cd2adf87b1c0546f7755ec0291dcb0ffbfae7c387dceb91d3` (nacional),
   `7f64a828389d91228b30247787817701c8ffccdeee8b81234282c77926f936bc` (estadual) e
   `89c027c90a2db5a4a7a7b5e3282404fb12b2bc30d500a4a79e49b6793749f512` (municipal).
2. **Originais preservados.** O aplicativo nunca altera esses arquivos. O instalador relê os
   bytes da origem depois da cópia, e os testes reais comparam o SHA-256 dos originais antes
   e depois de cada execução.
3. **Integridade obrigatória.** O backend usa os arquivos versionados somente quando
   tamanhos e SHA-256 correspondem ao manifesto governado `dados/brasil/manifesto.json`. Com
   arquivo alterado ou manifesto ausente, desatualizado ou inválido, a base Brasil fica
   indisponível e o upload continua funcionando.
4. **Sem cópias silenciosas.** `.local/` não é lida; uma instalação externa
   (`ADT_BRASIL_DATA_DIR`) só é usada quando configurada explicitamente e com a versão governada
   ou fixada em `ADT_BRASIL_DATA_VERSION`.
5. **Cópias fora do Git.** Instalações e cópias em `.local/` continuam ignoradas pelo Git (regra
   `.local/` do `.gitignore`).
6. **Fora do frontend público.** Arquivos e cópias não ficam em `frontend/` nem são servidos
   ao navegador, que recebe apenas resultados calculados pela API.
7. **Nenhum registro ao Gemini.** O provedor de IA recebe somente o pedido sanitizado e
   estados técnicos enumerados, nunca arquivos, linhas, nomes de campos ou valores.
8. **Repositório privado.** O repositório deve permanecer privado enquanto esta for a política
   de distribuição. Torná-lo público, ou ampliar o acesso de leitura, expõe os dados e todas as
   versões guardadas no histórico.
9. **Origem, cobertura e limitações.** Origem registrada: envio dos arquivos ao repositório no
   commit `a202be1`; a procedência primária (instituição produtora, data de extração e método
   de produção) não está documentada e permanece pendente. Cobertura: 22 competências (janeiro
   e junho de 2014 a 2024), 22 linhas nacionais, 594 estaduais (27 UFs × 22 competências) e
   122.534 municipais, 5.570 municípios por código IBGE, categoria MEDICINA, quantidade e população
   estimada sem ausências. A fonte estadual foi gravada por `build_state_source.py` a partir da
   planilha `medicos_unicos_municipios_estados_201401_202406.xlsx` (SHA-256 `51aa58879efc…`),
   entregue pelo responsável pelo produto em 19/10/2026, que não fica versionada. Limitações:
   sem população e coordenadas no recorte nacional; sem identificadores individuais; seis
   municípios com coordenadas fora do intervalo em todas as competências da fonte original
   (substituídas nas análises espaciais pela camada complementar oficial); nove municípios com
   coordenadas válidas que mudam entre competências; coordenadas com vírgula decimal e sem
   referencial geodésico declarado na fonte; nomes homônimos exigem o código. Evidências:
   [validação da base Brasil](Docs/DADOS_BRASIL_VALIDACAO.md),
   [proposta de acesso aos dados reais](Docs/OTIMIZACAO_LATENCIA.md#11-proposta-separada-acesso-seguro-aos-dados-reais-no-claude-code-web)
   e [Bloco 2, Etapa 1](Docs/BLOCO2_ETAPA1_REFERENCIAS_PROXIMIDADE.md).

**Licença e autorização de redistribuição: pendentes.** O repositório não registra a licença
das fontes nem autorização para redistribuí-las. Até esse registro, não redistribua os
arquivos fora deste repositório privado.

### Origem, integridade e coordenadas — dez pontos (Bloco 2, Etapa 2)

1. **Onde estão versionados.** `Dados_Brasil.xlsx` e `Dados_Municipios_Brasil.csv`, na raiz do
   repositório, com `Dados_Estados_Brasil.csv` desde 19/10/2026; identidade em
   `dados/brasil/manifesto.json` (versão `68944004901c…`; antes da fonte estadual, `819cf4628bff…`).
2. **Caminho usado pelo backend.** Os próprios arquivos da raiz do repositório; uma pasta
   externa apenas com `ADT_BRASIL_DATA_DIR` explícito e versão governada ou fixada.
3. **Prova de integridade.** Tamanho e SHA-256 de cada arquivo conferidos a cada requisição
   contra o manifesto governado; a versão inspecionada precisa coincidir com a analisada.
4. **Cópias antigas.** Não são lidas: `.local/` é ignorada pelo carregador e o teste com uma
   cópia antiga divergente comprova; o instalador só copia a versão governada.
5. **Camada complementar de coordenadas.** Arquivo versionado
   `dados/brasil/complemento_coordenadas.json` (versão 1, SHA-256 `5db726905a91…`), validado a
   cada leitura e aplicado só ao ler coordenadas da base Brasil municipal, na versão da fonte a que
   se refere (`Dados_Municipios_Brasil.csv`, SHA-256 `89c027c90a2d…`), apenas onde o ponto original
   é inválido; os arquivos originais e as bases importadas não são alterados.
6. **Municípios e competências.** Ananás/TO (170100), Pescaria Brava/SC (421265), Balneário
   Rincão/SC (422000), Jaraguari/MS (500490), Campestre da Serra/RS (430367) e Águas de
   Lindóia/SP (350050), nas 22 competências de janeiro e junho de 2014 a 2024 (132 registros).
7. **Fonte geográfica oficial — incorporada.** IBGE, Censo Demográfico 2022 — Localidades do
   Brasil: `BR_localidades_2022.gpkg` (SHA-256 `d057a1638b16…`; pacote
   `Localidades_Brasil_gpkg.zip`, SHA-256 `1d96d5f0b379…`; `gpkg_contents.last_change`
   2025-11-14T05:05:46.920Z), geometria pontual da sede municipal (`CT_LOCALIDADE` = Cidade,
   `SCT_LOCALIDADE` = Sede Municipal), SIRGAS 2000 (EPSG:4674 em `gpkg_spatial_ref_sys`),
   exatamente um registro de sede por município. As coordenadas foram extraídas e verificadas
   pelo usuário no exemplar do GeoPackage que ele forneceu; **não houve autenticação
   independente do arquivo junto ao servidor do IBGE** (o acesso a `*.ibge.gov.br` é bloqueado
   neste ambiente).
8. **Premissa humana.** Uma coordenada fixa por município nas 22 competências
   (`COORDENADA_FIXA_2014_2024`), decisão metodológica do usuário, sem comprovação independente
   de estabilidade histórica e sem extensão a outros municípios.
9. **Rastreio de versões e proveniência.** Versão da base pelo manifesto; identificador, versão,
   SHA-256 e proveniência oficial da camada (produto, arquivo e SHA-256 do GeoPackage, referencial,
   ponto e declaração de verificação) nos metadados (`complemento_geografico`) e na chave de
   execução das análises espaciais (não nas demais); municípios, linhas e coordenadas
   complementadas nos metadados e na coluna “Coordenada complementada (camada oficial)”;
   resultado espacial de outra versão da camada não é retomado em silêncio e preparação antiga é
   recusada. Para outra versão da fonte municipal, a camada é registrada como `incompativel` e não
   é aplicada.
10. **Limitações geográficas que permanecem.** A coordenada dos seis municípios é a mesma nas 22
    competências por premissa do usuário, não por comprovação de estabilidade histórica; bases
    importadas não recebem o complemento; nove municípios têm coordenadas válidas que mudam entre
    competências (cada competência usa a sua); a fonte original não declara referencial (na
    versão governada, SIRGAS 2000 é premissa interna do perfil, decidida pelo responsável pelo
    produto; a camada oficial é SIRGAS 2000); a distância é geodésica direta,
    sem trajeto, tempo ou acesso.

## Conversação com Gemini — iteração 2 contextual (opcional)

A página única (22/10/2026) tem, no alto, o nome do agente, a navegação (Nova sessão, Nova análise e Histórico) e a fonte dos dados; abaixo, a área de análise. A conversa fica numa caixa flutuante com o rosto do agente, sempre na página: arrasta-se com o mouse ou o teclado, guarda a posição e se minimiza; no celular, fica ancorada embaixo. A transcrição não ocupa a área principal; a última resposta do agente e o campo de mensagem permanecem juntos. A conversa age sobre o gráfico: o campo `painel` da resposta do intérprete vira um pedido para a área de análise, que pede os números ao motor. Não há "Início", "Resultados", preparação nem escolha entre análise independente e composição.

“Histórico” reabre as análises da sessão como estavam, sem recalcular. “Nova análise” guarda a análise em exibição no Histórico e volta ao começo do gráfico com os mesmos dados. “Nova sessão” sempre pede confirmação, oferece o CSV (valores do motor, em precisão integral) e a impressão da análise em exibição e lembra que outra análise precisa ser reaberta pelo Histórico para ser exportada. Confirmar encerra a sessão no servidor e recarrega a interface, descartando arquivos, referências, conversa e análises em memória. Se o encerramento falhar, a tela mantém o conteúdo e informa o erro. Antes de importar arquivos ou enviar mensagens, o usuário confirma a declaração de privacidade. O pop-up de início traz só essa declaração ("Declaro que não compartilharei dados pessoais ou sensíveis, seja por meio dos arquivos enviados ou das mensagens inseridas no chat.") e o botão "Li e concordo"; depois de uma sessão encerrada, o aviso de descarte aparece acima dela. O prazo da sessão não é exibido. O aceite vale para a sessão da aba; após o encerramento, o aceite é solicitado novamente. Se o navegador bloquear o armazenamento de sessão, o aceite permanece em memória até recarregar a página.

**Com base carregada:** pedidos reconhecidos pela gramática local seguem para `POST /api/exploration/interpret`; os demais seguem para `POST /api/llm/interpret-context`. Os dois levam em `options` o contexto do gráfico em exibição: os territórios na tela (`territory_ids`), a família, o indicador e a competência; esses valores ficam no backend local. Orientações de catálogo são atendidas localmente, inclusive durante uma pergunta pendente sobre municípios. No modo de importação, o arquivo é reenviado **somente ao backend Python local**; no modo Brasil, o navegador envia apenas a referência ao catálogo, recorte e versão. O backend revalida a estrutura, os mapeamentos, as escolhas, as premissas e a matriz de aplicabilidade. O Gemini recebe apenas o pedido sanitizado e um resumo controlado de estados técnicos (papéis reconhecidos/escolhidos e disponibilidade das capacidades). Nomes de campos, nomes de arquivo, territórios, categorias, períodos e linhas presentes no arquivo não são incluídos nesse resumo.

O Python também confronta deterministamente os períodos e categorias explicitamente propostos com os valores da base. Isso **não cria equivalências semânticas**: correspondência é literal após normalização básica de caixa e acentos, e o mês por extenso com ano e o ano sozinho viram as competências AAAAMM da base, como na gramática local ("junho de 2024" é 202406; um ano com várias competências fica em escolha, sem a pergunta de período inexistente); o nível territorial solicitado é o da abrangência territorial (base oficial) ou da coluna territorial escolhida (base importada), registrado como "Definido na abrangência territorial", sem pedido de confirmação. Uma interpretação não calcula nada: vira um pedido ao gráfico, e os números vêm do motor. Trocar a fonte invalida interpretações e pendências daquela fonte; a conversa e as análises do Histórico permanecem na memória da aba (as de outra fonte ficam listadas e reabrem com a fonte delas). Alterações de parâmetros e recorte invalidam respostas ainda em trânsito e exigem nova revalidação no backend.

**Sem base carregada:** o comportamento de primeira iteração continua disponível em `POST /api/llm/interpret`, mas a proposta é explicitamente preliminar e não verifica a existência dos valores sugeridos.

**Na página única de análise (desde 22/10/2026):** a conversa mexe no gráfico de bolhas. Quando o pedido toca o gráfico ("mostre o Pará", "use Belém como referência", "os 5 municípios com maior densidade", "compare Manaus e Tefé", "tendência nos últimos 4 anos", "volte aos estados"), as três rotas devolvem o campo `painel`: o comando com família, indicador, nível, municípios, competência, janela, referência, função, seleção, ordenação, condições e grupos. A conversa só interpreta; os números vêm do motor quando a tela aplica o comando. O estado do gráfico chega em `options`, e o pedido seguinte parte dele. Ambiguidades viram alternativas em botões, sem mudar o gráfico. Nas planilhas de outros países, as respostas usam os nomes das unidades e do grupo (distrito, província). Nada da base vai ao provedor. Formato e frases na seção "Conversa no gráfico" de [Docs/CONVERSACAO_INCREMENTO_FN.md](Docs/CONVERSACAO_INCREMENTO_FN.md).

A conversa **não envia os arquivos CSV/Excel, seus campos ou registros ao Gemini**. Apenas mensagens digitadas pelo usuário, submetidas a uma camada conservadora de minimização e substituição de identificadores, são enviadas ao provedor. Isso **não implementa a triagem integral** de entidades nominais, estados e autorizações da SPEC v1.2.4. Não utilize dados pessoais ou sensíveis na conversa.

O LLM classifica também intenções conversacionais e perguntas sobre o agente; o backend responde com textos de catálogo local. Saudações, agradecimentos, ajuda, importação, privacidade, limites e explicação de densidade contam com tratamento determinístico sem consumo de franquia. Perguntas como “O que é possível fazer nessa página?” recebem a orientação correspondente, sem substituir a resposta pela apresentação inicial. A fonte atual aparece no alto da página, num resumo de uma linha, com "Trocar".

Para pedidos analíticos, o contrato admite uma proposta única ou até cinco candidatas de operação/indicador, cada alternativa ancorada em trecho literal do pedido sanitizado atual. Leituras materialmente diferentes geram escolhas em botões na conversa, sem selecionar uma automaticamente. Com base disponível, a escolha explícita prepara a operação no backend e muda o gráfico; sem base, fica guardada até a escolha dos dados. Depois de validar a capacidade, o Python resolve os nomes municipais da manifestação original contra o catálogo **somente localmente**, incluindo paráfrases como “coloque Manaus e Tefé lado a lado”. Se só um município for informado numa comparação, pergunta qual outro; “analise dois municípios também” pede os nomes e aproveita a mensagem seguinte, sem escolher os primeiros municípios da base. Homônimos e trechos de recorte não reconhecidos continuam exigindo esclarecimento. O texto exibido vem de templates locais; **nenhum resultado factual, limiar ou cálculo vem do LLM**. Essa ampliação é parcial: ver [conversação incremental](Docs/CONVERSACAO_INCREMENTO_FN.md).

A evolução autorizada do diálogo está registrada em [Evolução conversacional](Docs/EVOLUCAO_CONVERSACIONAL_20261016.md). A interface usa contexto temporário verificado no backend para seleção, parâmetros, possibilidades do pré-exame e referências a resultados. “Esses municípios”, correções de indicador e inclusão de município reaproveitam o contexto do gráfico. “E agora?” informa o contexto sem calcular. Densidade, quantitativos e comparação territorial já admitem perguntas sobre o resultado apresentado, com origem verificada, preservação das notas e explicações metodológicas pelo catálogo PT. “Explique de maneira mais simples” reduz a expansão metodológica, conservando fatos e limitações. Relação não calculada oferece preparação de comparação. As demais leituras analíticas conversacionais permanecem limitadas; os controles da área de análise continuam disponíveis. EN não está autorizado nesta integração.

**Continuidade da conversa (21/10/2026).**
- Um pedido sem territórios usa os já escolhidos, e a resposta diz quais.
- Um pedido só com o período ("E nos últimos 5 anos?") continua a análise ativa.
- "Últimos N anos" é contado até o último período da base e até hoje, pela data local do navegador (AT-34). Se as
  duas contagens dão as mesmas competências, o período é aplicado; se divergem, a conversa oferece as duas leituras,
  sem escolher.
- O pedido feito antes da escolha dos dados é reinterpretado quando a base fica pronta, e os municípios citados nele
  vão para o gráfico.

Essas continuações não chamam o provedor de IA. Detalhes em
[interface conversacional](Docs/INTERFACE_CONVERSACIONAL_INTEGRADA.md).

Com o gráfico na tela, "agora a tabela" responde que a tabela fica em Detalhes, logo abaixo do gráfico, com os mesmos
valores do motor; "ver no mapa" explica que o mapa não faz parte da página única e que a distância até uma referência
fica na análise espacial; "mostre no gráfico" lembra que o gráfico já está na tela. "Volte ao resultado anterior" (ou
"à seleção anterior") reabre a análise anterior do Histórico, com os mesmos dados, sem recalcular (RQ-LIN-20). A
interface reconhece as formas diretas; as demais chegam ao intérprete, que as devolve como atos `show_map`,
`show_chart`, `show_table` e `previous_result`, com as mesmas respostas. Perguntas conceituais sobre os pontos de corte e as
classes da distribuição (CAP-DIS-02) e sobre a referência mais próxima (CAP-ESP-02) passam a ser respondidas com as
formas governadas do catálogo PT, como densidade, distância e agregação. Tendência, mudança temporal, comparação,
contagem, ranking, critérios e rotatividade continuam sem explicação metodológica na conversa: suas formas descrevem
etapas que o protótipo não implementa.

**Biblioteca de Inteligência Conversacional** (20/10/2026): a cada mensagem que chega ao provedor, o intérprete
recebe até cinco turnos de trajetórias sintéticas da biblioteca (`backend/biblioteca_conversacional/`), escolhidos
localmente pela mensagem, pela mensagem anterior e pelo estado verificado da conversa, e mascarados pelas mesmas
regras das mensagens do usuário (nenhum valor, campo ou arquivo da base). Os exemplos só mostram como mensagens
parecidas se mapeiam no contrato; não trazem fatos, métodos nem respostas, e a resposta do provedor passa pelas mesmas
validações. A resposta da API identifica os exemplos usados (`biblioteca`). `ADT_BIBLIOTECA_CONVERSACIONAL=0` desliga
a biblioteca e restaura o pedido anterior. Formato, manutenção e avaliação:
[Biblioteca conversacional](Docs/BIBLIOTECA_CONVERSACIONAL.md).

### Chave Gemini permanente no Windows (configuração única)

A aplicação aceita `GEMINI_API_KEY` de duas fontes, por esta ordem:
1. **Variável de ambiente do servidor ou hospedagem:** tem prioridade, adequada para publicação.
2. **Arquivo `backend/.env` local:** carregado automaticamente ao iniciar o FastAPI, útil no desenvolvimento.

O arquivo `.env` é **texto puro com segredo**, por isso não deve ser compartilhado, enviado ao ChatGPT, incluído em capturas nem publicado. Está excluído do Git por `.gitignore`; somente `backend/.env.example` (sem chave) é versionado. Preserve as permissões de acesso à sua conta Windows.

Após atualizar o repositório, abra um PowerShell na pasta `backend`:

```powershell
cd "C:\Users\User\Desktop\Github\Teste-Agente\backend"
py -m pip install -r requirements.txt
if (!(Test-Path .env)) { Copy-Item .env.example .env }
notepad .env
```

No Bloco de Notas, localize `GEMINI_API_KEY=` e **cole sua chave existente depois do sinal de igual**, sem espaços extras. Salve e feche. **Não envie capturas desta tela nem cole a chave no chat.**

Reinicie o backend (encerre o Uvicorn anterior com Ctrl+C, se necessário):

```powershell
py -m uvicorn main:app --reload --port 8000
```

No navegador abra a aplicação; para conferir sem expor a credencial, em outra janela PowerShell execute:

```powershell
Invoke-RestMethod http://127.0.0.1:8000/api/llm/status
```

O campo `configured: True` indica que o backend encontrou uma chave, **não garante que a Google ainda aceite a chave ou que haja quota gratuita**. A validação real requer uma solicitação à API.

Se `configured: False` persistir, confirme se o arquivo está precisamente em `backend/.env`, se o `GEMINI_API_KEY` foi preenchido e se o servidor foi reiniciado. Não é necessário criar uma nova chave diariamente.

**Alternativa sem arquivo persistente:** uma variável `GEMINI_API_KEY` definida manualmente no PowerShell ainda funciona e tem prioridade, mas dura somente naquela sessão de terminal. Para produção, cadastre a chave como **segredo do ambiente da hospedagem**, não envie `.env` à plataforma nem configure a chave no React.

O backend utiliza por padrão `gemini-3.5-flash-lite`. Os limites e o faturamento do Google variam e não são verificados pelo protótipo. O contador local de 20 solicitações por processo **não é um controle de custo ou segurança contra abuso**.

O timeout técnico do cliente HTTP do Gemini é de **75 segundos** (desde 21/10/2026; antes, 22).
Esse prazo vale por operação de conexão, leitura, escrita e espera por conexão do HTTPX, não como limite
global de duração da conversa. Quando ele expira, a API mantém HTTP 503 e a tela apresenta
"Tempo limite de 75 segundos excedido na comunicação com a API Gemini. Tente novamente.".
Demais falhas de transporte mantêm HTTP 503 e "Não foi possível alcançar a API Gemini. Tente novamente.".
Erros HTTP retornados pelo provedor mantêm o tratamento próprio de cota, autorização e falha da API;
não há nova tentativa automática. O prazo da sessão continua sendo 1.800 segundos.
Medições de recuperação local, tamanho do pedido e espera remota, com e sem exemplos:
[diagnóstico de latência do Gemini](Docs/DIAGNOSTICO_LATENCIA_GEMINI_20261021.md).

Rotas experimentais: `GET /api/llm/status` (nunca retorna a chave), `POST /api/llm/interpret` (sem base) e `POST /api/llm/interpret-context` (multipart, com base validada apenas pelo Python). A transcrição permanece na memória da aba. O backend mantém contexto técnico e referências a resultados em sessão temporária, sem banco ou gravação em disco, isolada por token opaco. Encerrar sessão ou completar 1.800 segundos sem interação efetiva elimina o contexto; polling não renova o prazo. Reiniciar o backend também elimina as sessões. Testes offline utilizam respostas simuladas do provedor; a CI **não faz chamadas reais e não precisa de chave**. Falhas de conexão ou cota são mostradas sem alterar o motor analítico. Ver [evolução conversacional](Docs/EVOLUCAO_CONVERSACIONAL_20261016.md).

### Fronteira da SPEC

Referências: FN-INT-01/02 (propostas interpretativas), CFG-AMB e CFG-OPC (ambiguidade e opções), RQ-DAD-20 e RQ-PRV-02 (privacidade), INV-02/03/16 (autoridade factual), RQ-ESC-01/04 (escopo FTS), RQ-GOV-14 (decisões e confirmações), C-04 (verificação determinística), RQ-ARQ-06 (minimização), RQ-ORQ-01 (planos governados). FN-INT-01/02/03 e FN-META-01 têm cobertura **parcial**; alternativas ancoradas e orientações de catálogo não equivalem ao fluxo normativo completo de estados, CFG-DOC/V-16 e validações exaustivas. FN-INT-04, FN-ORQ-01 e CAP-SIN-01 continuam pendentes. Antes de alegar conformidade integral, essas lacunas precisam ser implementadas e auditadas.

## Testes

As regras de trabalho para pessoas e agentes (Claude, Codex e outros) estão em
[`AGENTS.md`](AGENTS.md). O CI é o único ambiente de verificação (seção 4 do `AGENTS.md`): roda todos
os jobs em todo push e precisa terminar em PASS. Antes do push, rodam só checagens de segundos
(compilação do Python alterado, TypeScript sem build e, depois do commit, a governança). Os comandos
abaixo reproduzem o CI localmente e só rodam por pedido explícito do responsável pelo produto, ou,
para diagnosticar uma falha que o log do CI não explica, só o teste que falhou. Na raiz:

```bash
(cd backend && python -m pytest -q)                                   # backend
(cd backend && ADT_REAL_DATA_DIR="$(cd .. && pwd)" python -m pytest -q -rs)  # com a base versionada: nada pulado
(cd frontend && npm ci && npm run build)                              # TypeScript e build
python backend/tests/run_ui_checks.py                                 # todas as jornadas de navegador
python backend/tests/run_ui_checks.py --roteiro ui_pagina_unica.py    # só os roteiros indicados
python .github/scripts/verificar_governanca.py                        # registro de comportamento e jornadas no CI
```

Quando pedido, o script `python scripts/verificar_tudo.py` roda todas essas verificações
na ordem e termina com um resumo do que passou, falhou ou ficou de fora, e por quê; os logs ficam em `.local/verificacao/`. Os testes
com dados reais só rodam quando a mudança toca o motor, a API ou os dados (`--dados-reais sim` força),
e o script decide sozinho a dispensa do `npm ci` descrita abaixo (`--npm-ci` força). No Windows, ele
já define `PYTHONUTF8=1` e uma pasta temporária gravável para o pytest. A governança confere os
commits; depois do commit, rode-a de novo antes do push.

Localmente, o `npm ci` pode ser dispensado quando `package.json` e `package-lock.json` não mudaram
desde o último `npm ci` bem-sucedido; basta o `npm run build`. O CI sempre roda o `npm ci`.

Para a conferência visual, `python scripts/capturar_telas.py` sobe o servidor de testes com a base
versionada e percorre a página única: a abertura, os estados, o Amazonas e a comparação pedidos pela
conversa, o Histórico, o diálogo de Nova sessão, o painel "Colunas" de uma planilha de distritos e o
celular. As capturas ficam em `.local/capturas/`. Rode depois do `npm run build`; nada vai para o
provedor de IA e nenhum dado é alterado.

No Windows (PowerShell), defina `$env:ADT_REAL_DATA_DIR` com o caminho completo da raiz do
repositório. Sem o Google Chrome instalado, defina `ADT_BROWSER_CHANNEL=chromium` para as jornadas.

O workflow `.github/workflows/ci.yml` roda no push e em pull requests. Nenhuma verificação chama o
provedor real de IA.

| Job | O que verifica |
|---|---|
| `backend` | Suíte pytest. Os testes de dados reais são pulados aqui e rodam em `dados-reais`. |
| `dados-reais` | Integridade da base Brasil versionada (tamanho e SHA-256 contra `dados/brasil/manifesto.json`) e a suíte completa com os dados reais. Falha se algum teste for pulado. |
| `frontend` | TypeScript e build de produção. |
| `ui-conversational` | A conversa agindo no gráfico, sem provedor de IA (suíte `conversa`). |
| `ui-block1` | A página única com o catálogo sintético do Bloco 1 (suíte `bloco1`), a conversa com Gemini simulado (`gemini-simulado`) e a página com a base versionada (`base-versionada`). |
| `governanca` | Toda mudança de comportamento está em [`Docs/REGISTRO_DE_COMPORTAMENTO.md`](Docs/REGISTRO_DE_COMPORTAMENTO.md) ou foi declarada sem alteração, e todo roteiro de navegador roda no CI. |
| `resumo` | Quadro único com o resultado de todos os jobs. Falha se qualquer um falhar. |

As jornadas de navegador rodam pelo executor único `backend/tests/run_ui_checks.py`. Ele prepara
os catálogos, sobe e encerra os servidores locais, roda cada roteiro isolado e, no final, lista
o resultado de todos. Uma falha não esconde as seguintes. Um push novo no mesmo ramo cancela a
execução anterior do CI, e o resultado exibido é sempre o do estado mais recente. Medições de
tempo (`backend/tests/bench_*.py`) ficam fora do CI.

Os roteiros de navegador que saíram estão registrados em
[`backend/tests/legado/`](backend/tests/legado/README.md): os anteriores à interface conversacional
(15/10/2026) e os 16 do fluxo clássico (22/10/2026). Lá estão o motivo, o mapa do que cobriam, onde a
cobertura está hoje e as lacunas que ainda precisam de roteiros novos. A preparação em três etapas saiu
da interface com as telas clássicas; [preparação guiada](Docs/PREPARACAO_GUIADA.md) fica como histórico.

## Ponte semântica e habilitação de análises

O motor `backend/semantic_bridge.py` reutiliza regras de reconhecimento governado da SPEC para propor a associação entre **nomes originais das colunas** e papéis analíticos internos, sem exigir renomeação pelo usuário. Correspondências não conclusivas (por exemplo, "Total de médicos únicos") ficam como sugestão no topo do seletor, que permanece vazio até a escolha do usuário, e não autorizam deduções de unicidade. O exame automático `/api/inspect` fornece candidatos, perfis de colunas e uma matriz inicial; `/api/preflight` a recalcula após esclarecimentos. O endpoint `/api/analyze` **revalida** a habilitação antes da execução.

**Experimento híbrido:** os botões das análises na área de análise ainda diferem do canal conversacional normativo da SPEC; a interpretação com LLM não substitui os gates nem autoriza execução. Ver `Docs/SEMANTIC_BRIDGE_ADAPTACOES.md` para rastreabilidade, divergências e limitações.

Exemplo de CSV com `0`, `Competência`, `Total de médicos únicos`: a coluna `Competência` é reconhecida como período, `Total de médicos únicos` é **sugerido** como quantitativo (sem entrar no mapeamento); o cabeçalho `0` não é presumido território. Na API (`/api/preflight` e `/api/analyze`), depois de escolher a coluna de contagem e a unidade e de informar o objeto de análise, quantitativos e série temporal podem ficar disponíveis **sem inventar território nem população**; a comparabilidade temporal é premissa da análise, registrada no resultado. Densidade continuará indisponível sem o denominador e recorte apropriados. A página única desenha unidades territoriais: no painel "Colunas", as colunas da unidade territorial, do período e da quantidade são obrigatórias, e uma planilha sem elas não chega ao gráfico.

## Validação local e resolução de registros múltiplos

Municípios ou outras unidades com o mesmo nome podem representar lugares distintos. No painel "Colunas", escolha a coluna da unidade territorial e, no seletor do código, a coluna que distingue essas unidades (a coluna de código aparece como sugestão no topo, mas só vale depois de escolhida). O nome continua sendo apresentado junto ao código. O aplicativo não confere códigos em cadastros externos.

A unidade da contagem deve ser escolhida. Profissionais distintos em um município, categoria e período não implicam aditividade entre recortes. Na API, cópias idênticas só são removidas por escolha explícita (`duplicate_policy`); componentes desagregados exigem a escolha das dimensões que os distinguem (`component_columns`), e a soma das partes vira premissa com nota (e a limitação de possível dupla contagem quando a unidade é pessoas). Essas duas escolhas ficavam na preparação das telas clássicas, que saiu em 22/10/2026; o painel "Colunas" não as oferece. População repetida no mesmo território e período é utilizada uma vez; conflitos impedem o cálculo.

O CSV contém todos os resultados, com precisão numérica preservada. “Método e parâmetros” exporta as associações, escolhas, premissas aplicadas, filtros, versão do método e identificação do conteúdo analisado. PDF usa a impressão do navegador e abrange a apresentação visível.

Na raiz do repositório, em PowerShell:

```powershell
py -m pip install -r backend/requirements-test.txt
$env:ADT_REAL_DATA_DIR = 'C:\Users\User\Desktop\Dados_Brasil'
py -m pytest -q
```

Os testes reais leem os arquivos somente em leitura e verificam seus hashes antes e depois. Sem a variável, eles são omitidos. Como a base Brasil está versionada na raiz do repositório, `ADT_REAL_DATA_DIR` pode apontar para a própria raiz. É assim que o job `dados-reais` do CI executa os 33 testes reais em todo push, sem nenhum teste pulado (ver [Testes](#testes)).

O antigo gate de Densidade pelo navegador (`ui_smoke.py`, upload do CSV municipal com conferência linha a linha) usa a interface anterior à conversacional e foi movido para [`backend/tests/legado/`](backend/tests/legado/README.md). Hoje, a conferência de todas as linhas contra aritmética independente roda no job `dados-reais`, e a página única com a base versionada roda pelo navegador na suíte `base-versionada` (job `ui-block1`). Capturas das jornadas ficam em `.local/ui-validation/`, ignorada pelo Git.

## Referência geográfica mais próxima (Bloco 2, Etapa 1)

Para cada município-alvo, indica a referência autorizada geograficamente mais próxima, com
código, distância geodésica direta em quilômetros (Karney, no elipsoide do referencial: GRS80 no
SIRGAS 2000 ou WGS 84 no WGS 84, sem arredondamento no cálculo) e cobertura das referências. A capacidade continua na API
(`/api/analyze`); o cartão **Referência mais próxima** saiu da interface com as telas clássicas em
22/10/2026. Na página única, a análise espacial com um conjunto de referência mostra a distância até o
membro mais próximo ([área de análise](Docs/PAINEL_INTEGRADO_INTERFACE.md)).
Na API, as referências são definidas pelo usuário, por lista de municípios (nome ou código) ou por
critério simples de densidade (operador e valor por 1.000 habitantes, sem valor sugerido).
O período é escolhido explicitamente. Na versão governada da base Brasil, o referencial
SIRGAS 2000 e a vírgula decimal das coordenadas são premissas internas, registradas nas notas do
resultado; em bases importadas e em outras versões, o referencial é escolhido explicitamente, SIRGAS 2000
ou WGS 84 (nenhum referencial é presumido), e o separador decimal das coordenadas é verificado nos dados, com
nota (só vira escolha quando o formato é misto). Nenhum referencial é transformado: na base do Brasil, outro
referencial informado é recusado, com o motivo.
Referências ou alvos sem coordenada válida
ficam registrados como não avaliáveis, com `minimo_completo` e `minimo_avaliaveis`
distintos, empates preservados e ausência nunca convertida em zero. A distância não
representa trajeto viário, tempo de deslocamento nem acessibilidade. O LLM não escolhe
referências nem recebe esta capacidade. Detalhes, testes e desempenho:
[Bloco 2, Etapa 1](Docs/BLOCO2_ETAPA1_REFERENCIAS_PROXIMIDADE.md).

## Critérios combinados, réguas e rankings (Bloco 2, Etapa 2)

A capacidade de critérios combinados (API `/api/analyze`) aplica condições simultâneas sobre densidade por 1.000
habitantes, quantidade, população, distância à referência mais próxima, pertença a uma lista de
territórios e UF, com `<`, `≤`, `>`, `≥`, `=`, `≠` combinados por E, OU e NÃO em três estados
(`ATENDE`, `NAO_ATENDE`, `NAO_AVALIAVEL`; indeterminação nunca vira “não atende”). Cada condição
tem uma régua com indicador, unidade, operador, valor, universo, competência/categoria e origem
“escolha do usuário”; não há pontos de corte padrão nem caráter legal, sanitário ou científico.
O resultado separa quem atende, não atende e não é avaliável (com motivos por condição),
permite ordenar (posições 1, 2, 2, 4), selecionar os N primeiros com os empatados no corte e
definir faixas `[a, b)` com o último intervalo fechado. A distância
usa o mínimo do conjunto completo de referências; o mínimo entre as avaliáveis e a restrição às
referências de elegibilidade confirmada exigem aceitação explícita e ficam rotulados. Na página única,
as condições e a ordenação ficam nas funções Condições e Ordenar da área de análise; o cartão
**Critérios combinados**, a comparação com o conjunto anterior, o JSON técnico e a reutilização do
conjunto como seleção territorial ou referências saíram com as telas clássicas em 22/10/2026. Na conversa,
pedidos como “Mostre os municípios com menos de 2 médicos por mil habitantes”, “Agora considere
também distância superior a 150 km”, “Ordene esses municípios pela distância” e “Mostre os 20
primeiros” são estruturados por um canal determinístico
(o LLM não recebe a capacidade), com perguntas quando há ambiguidade material. Detalhes, testes e
desempenho: [Bloco 2, Etapa 2](Docs/BLOCO2_ETAPA2_CRITERIOS_INTEGRACAO.md).

## Evolução temporal e tendência (CAP-TMP-01 e CAP-TEN-01)

A evolução temporal traz, por território e categoria, a mudança entre a primeira e a última
competência (inicial, final, variação absoluta e percentual, a **direção da mudança** — Aumento,
Redução ou Sem mudança — e a condição, com base zero quando o inicial é 0) e a **tendência** da SPEC
(CAP-TEN-01, DA-15): Crescimento, Aceleração do crescimento, Desaceleração do crescimento, Declínio,
Aceleração do declínio, Desaceleração do declínio ou Sem classificação (mudança de direção ou série
estável), com o motivo e o número de observações. A classificação usa aritmética exata (a densidade
é recalculada como quantidade × 1.000 / população), sem imputar competências ausentes e com o tempo
transcorrido entre elas; com menos de quatro competências a etapa recebe BLQ-MET com os textos do
catálogo, e a mudança continua disponível. Contagens por classe, velocidades e janela ficam em
`metadata.tendencia` e `metadata.mudanca`, fora do contexto enviado à IA. Na página única, a análise
Tendência mostra a mudança, as classes e as séries, com a janela escolhida pela pessoa
([área de análise](Docs/PAINEL_INTEGRADO_INTERFACE.md)). Os selos, o filtro por família, a caixa Período
com o atalho "Série anual (junho)", os pequenos múltiplos e os halteres da aba Gráficos saíram com as
telas clássicas em 22/10/2026. Detalhes,
contagens com os dados reais e testes: [Evolução temporal e tendência](Docs/EVOLUCAO_TEMPORAL_E_TENDENCIA.md).

## Comparação territorial com competência dos valores (CAP-CMP-01 com CAP-TMP-01 e CAP-TEN-01)

Desde 19/10/2026 (decisão D6), a comparação aceita um período ou uma janela de períodos. A opção
`comparison_values_period` da API (a **competência dos valores**, que precisa estar na janela de
`period_filters` ou ser o `period_filter`) faz as relações da CAP-CMP-01 (par A/B com relação e diferença
assinada A − B; três ou mais com valores iguais e próximo valor maior, sem diferenças entre pares, AT-84) usarem
só essa competência, no formato de sempre em `rows`, com a cardinalidade do conjunto pedido. Em `detail_rows`
vem um registro por território: quantidade, população e densidade na competência dos valores, a condição e,
com duas ou mais competências, a mudança entre a primeira e a última (CAP-TMP-01: inicial, final, variação
absoluta, direção e condição) e a tendência (CAP-TEN-01: classe, motivo e observações), pela mesma
`temporal_change.evolution` da evolução temporal; **sem variação percentual, razão nem diferença percentual
automáticas**. A janela exige as premissas temporais da evolução (aplicadas pelo backend). O resultado traz
`metadata.comparacao` (competência dos valores, janela, grupos de relação por nível e objetos sem relação),
`metadata.tendencia` e `metadata.mudanca` (com a janela), e as métricas "Territórios comparados" e
"Competências na janela". Com os níveis da base oficial, as relações ficam só dentro do mesmo nível; o Brasil
fica lado a lado, sem relação, e o estado com suporte variável na janela não recebe tendência
(INCOMPARABILIDADE). Sem a opção, a comparação segue o caminho anterior (relações em cada competência). A
chave de execução muda com a opção e com a versão do método de tendência. Na página única, a função
Comparar põe 2 ou 3 itens lado a lado, com maior, menor e diferença vindos do motor
([área de análise](Docs/PAINEL_INTEGRADO_INTERFACE.md)); a tela clássica da comparação (série anual de
junho, a frase "Valores lado a lado em …", os halteres, os selos e o mapa do par) saiu em 22/10/2026. Na
conversa, a relação de valores iguais (IGUALDADE) aparece na resposta ("O valor de A é igual ao de B."); antes, sumia.
Detalhes: [Evolução temporal e tendência](Docs/EVOLUCAO_TEMPORAL_E_TENDENCIA.md) e
[abrangência territorial](Docs/ABRANGENCIA_TERRITORIAL.md).

## Mapas e exploração visual integrada (Bloco 3)

**Até 22/10/2026**, a tela de resultados tinha as abas **Mapa**, **Gráficos** e **Tabela**, que
representavam o mesmo resultado: o mapa de pontos (canvas, com seleção, zoom e escala de cor), barras,
linhas, o pirulito do ranking, a faixa da distribuição, os blocos dos níveis e o cabeçalho do resultado
com a frase-resumo, os indicadores e a procedência. Essas visualizações saíram do produto com as telas
clássicas; a análise na tela é o gráfico de bolhas da página única
([área de análise](Docs/PAINEL_INTEGRADO_INTERFACE.md)), sem mapa.

O que continua na API (`/api/analyze`):
- o contrato de apresentação (`metadata.representacao`) com as colunas representáveis (rótulo, unidade,
  natureza e capacidade de origem) e as coordenadas autorizadas de cada território na competência do
  resultado, pela mesma regra das análises espaciais, respeitando a competência e a camada complementar
  governada;
- a frase-resumo determinística do motor (`metadata.representacao.resumo`: só cópias verificadas de caminhos
  do resultado, sem LEX-DES, LEX-NORM nem LEX-CAU, sem "acima" ou "abaixo" da taxa nacional e fora do
  contexto da IA);
- as métricas do motor por análise (desde 19/10/2026, decisão D7): evolução temporal (séries, aumento,
  redução, sem mudança e mudança não avaliável entre os extremos), comparações (territórios comparados e
  competências na janela), agregação (territórios agregados), distribuição ("Unidades classificadas" e
  classes), ranking (ordenados e não avaliáveis), rotatividade (coortes avaliáveis e sem registro em um dos
  períodos), relatório de quantidade (registros territoriais) e, na rota de níveis, registros avaliáveis e
  não avaliáveis de cada nível; a descrição da densidade é "Densidade de pessoas por 1.000 habitantes.";
- na evolução temporal, selos, contagens e velocidades da tendência em `metadata.tendencia`.

Nenhuma classe, quebra ou quantil é criada na tela. Não há limites de UF nem mapas coropléticos (malha
oficial indisponível neste ambiente). Histórico do Bloco 3, testes do contrato e desempenho:
[Bloco 3](Docs/BLOCO3_MAPAS_VISUALIZACOES.md).

**Gráfico de bolhas: motor (21/10/2026) e página única (22/10/2026):** o gráfico de bolhas é admitido pelo
Adendo BOL-20261021 da SPEC. O motor serve `POST /api/painel` e `POST /api/painel/referencias`: população,
quantidade e densidade de cada município e de conjuntos agregados, distância até a referência e variação
percentual. Desde 22/10/2026, o pedido com `nivel` (página única de análise) aceita também planilhas enviadas,
com rótulos próprios (distritos, províncias…), e traz os estados, a tendência, os grupos por posição, as faixas,
as condições, a ordenação, a comparação, a rotatividade (só com identificador individual), a disponibilidade de
cada análise, a linha de contexto do Brasil e o registro do resultado na sessão; sem `nivel`, vale o contrato de
21/10. Rotas, campos e regras em [painel integrado](Docs/PAINEL_INTEGRADO.md). Na tela, desde 22/10/2026,
esse gráfico é a área de análise da página única, a única forma de análise da interface: as telas clássicas
("Todas as análises" e "Outras análises") saíram do produto. Detalhes em
[área de análise](Docs/PAINEL_INTEGRADO_INTERFACE.md).

## Escopo e limitações do protótipo

A interface é a página única de análise (22/10/2026): o gráfico de bolhas com Distribuição, Análise espacial, Tendência e Rotatividade e as funções da área de análise, guiado também pela conversa. O motor implementa percursos iniciais para densidade, quantitativos, distribuição por quantis, comparação, mudança temporal, agregação, distância geodésica, ordenação, coortes, tabelas/relatório básico, referência geográfica mais próxima, critérios combinados com rankings e faixas, e o contrato de representação (`metadata.representacao`).

**Não declara conformidade integral com a SPEC.** Ainda são necessários, entre outros: suporte a várias bases e planilhas auxiliares simultâneas; normalização completa de tabelas largas e dados individualizados; versão integral do catálogo de significados e vocabulário governado; todos os tratamentos de ambiguidade e estados de autorização; seleção territorial avançada (parcialmente atendida: estados e municípios no gráfico da página única; Brasil, estados e municípios na API de análise; ver [abrangência territorial](Docs/ABRANGENCIA_TERRITORIAL.md)); regras de comparabilidade longitudinal; PDF gerado diretamente por servidor e relatório consolidado HTML; limites territoriais oficiais e mapas coropléticos; cobertura exaustiva dos cenários de aceite; escala de grandes bases. As análises de comparação, tendência e rotatividade produzem resultados preliminares que exigem significados semânticos autorizados antes de uso substantivo.

**Divergências da SPEC decididas pelo responsável pelo produto** (registradas em [Docs/REGISTRO_DE_COMPORTAMENTO.md](Docs/REGISTRO_DE_COMPORTAMENTO.md); a SPEC não foi alterada):
- o aviso de prazo da sessão (RQ-FLX-19, TPL-09, AT-44) não é exibido no início da sessão; o pop-up traz só a declaração de privacidade (19/10/2026);
- nenhuma confirmação de colunas e campos (19/10/2026): a proposta não é apresentada para confirmação e a escolha no seletor substitui a confirmação (RQ-DAD-05, RQ-DAD-06); coordenadas sem confirmação, com o seletor vazio quando o reconhecimento não é conclusivo (RQ-DAD-25, na parte "requer confirmação do usuário"; a validade por elemento segue a SPEC); a identidade da pessoa (contagem de pessoas distintas e rotatividade) é estabelecida pela coluna de identificador individual, escolhida no seletor ou reconhecida pelo nome do vocabulário, sem regra de identidade autorizada nem declaração (RQ-DAD-35, CAP-ROT-01); aditividade e comparabilidade viram premissas com nota e limitação, e, na base importada, o significado longitudinal da chave territorial é verificado nos dados, não estabelecido por regra, metadado ou confirmação (RQ-DAD-36, CFG-TER); a interação "Confirmar significado de campo" da tabela de interação (L274) não existe;
- a densidade do Brasil de 2015 (regra BR-POP-JUNHO-1) é avaliável com limitações (`POPULACAO_NACIONAL_PARCIAL`): a população de junho soma os 5.569 municípios com registro, sem o 430607, enquanto o numerador continua sendo a contagem nacional inteira, em vez de NAO_AVALIAVEL por DENOMINADOR_AUSENTE e sem exclusão do ausente (CAP-IND-02 L1742, DA-10, INV-04, AT-08; a densidade parcial da CAP-AGR-01, L1751, exige o mesmo suporte no numerador e no denominador) (19/10/2026).

Uploads são processados em memória por requisição e não são persistidos pelo aplicativo. O arquivo é reenviado a cada análise; o limite experimental é de 30 MB. Evite bases pessoais e sensíveis no protótipo. Para arquivos muito grandes, será preciso processamento incremental/local, sessão segura e proteção de dados aprofundada.

Amostras da interface são exemplos ilustrativos, **não diagnósticos reais**. Métodos não podem inventar limiares normativos nem presumir unicidade dos profissionais no agregado.
