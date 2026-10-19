# Teste Agente — Portal Experimental

Experimento isolado de desenvolvimento para o **Agente Diagnóstico Territorial da Força de Trabalho na Saúde**.

- **Interface:** React + TypeScript + Tailwind em uma área de investigação horizontal, com banner e cinco ações: Início, Nova sessão, Nova análise, Histórico e Resultados. Cada análise tem duas áreas em abas, Preparação e Resultados, com um contorno que desce da aba ativa e envolve o conteúdo da etapa. Na base oficial, a preparação de todas as análises reúne as configurações nas mesmas caixas seletoras (Categoria, Período, Abrangência territorial e Indicador); nas bases importadas, a seleção de territórios é um bloco recolhível da preparação. O personagem original acompanha dados, preparação e resultados. A conversa preserva o contexto em memória e mostra a última resposta do agente junto ao campo de mensagem, inclusive durante a exploração de resultados.
- **Investigação progressiva:** análises independentes e diagnósticos compostos têm identificação própria. Cada componente mantém resultados, recortes, parâmetros e métodos; a composição não calcula valores conjuntos. Filtros e seleções visuais são lembrados por resultado. Veja [Interface conversacional integrada](Docs/INTERFACE_CONVERSACIONAL_INTEGRADA.md) e [Análise exploratória integrada](Docs/ANALISE_EXPLORATORIA_INTEGRADA.md).
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

**Usar dados do Brasil** verifica e disponibiliza as duas fontes conjuntamente em
uma sessão lógica: `Dados_Brasil.xlsx` (nacional) e
`Dados_Municipios_Brasil.csv` (municipal). O usuário não precisa escolher
os arquivos separadamente. São oferecidos como fontes independentes no chat,
sem concatenar seus registros. Ao escolher uma análise, o sistema usa o recorte
nacional para quantitativos, evolução temporal e relatórios; para as demais, usa
municípios. Nessas três análises, válidas nas duas fontes, a caixa **Abrangência territorial**
das configurações oferece o Brasil (total nacional) e os municípios, com busca e escolha de um ou
mais municípios; marcar municípios leva a análise ao recorte municipal. Com o total nacional
escolhido, a lista de municípios vem do último pré-exame municipal ou de uma consulta só de leitura
ao recorte municipal (`/api/inspect`), feita ao abrir a caixa. Nas demais, a caixa informa
que a análise usa somente a fonte municipal, sem uma opção que levaria ao bloqueio. Ao trocar de
recorte, a preparação continua na tela, bloqueada e com aviso de carregamento, até o novo
recorte chegar; a interface não volta à escolha da fonte. Trocar de recorte limpa resultados;
confirmações comuns verificáveis de período/categoria são preservadas quando a análise de
destino aceita o mesmo modo de período (único ou vários). A preparação de cada recorte é
mantida na memória da aba e restaurada ao retornar à mesma versão, sempre com novo pré-exame
do backend.

As fontes mantêm suas granularidades: não há junção de linhas, propagação de população
municipal para o Brasil ou soma automática de pessoas entre municípios. Na agregação
municipal da base oficial, o total é a soma dos componentes, sempre rotulada como possível
dupla contagem; em bases importadas, o motor continua exigindo as declarações de aditividade
e da forma de contagem.

A plataforma reconhece automaticamente as associações e significados da base Brasil
**somente** quando a estrutura, o mapeamento e a categoria única MEDICINA correspondem
ao perfil governado (`backend/brazil_catalog_profile.py`), após a verificação de
integridade do catálogo. Nesse caso, a unidade de contagem declarada para o catálogo
é pessoas por território/período; isso **não** implica identidade única entre
municípios ou meses. Nenhum perfil é aplicado ao upload do usuário, a estruturas
desconhecidas ou a categorias inesperadas. Para bases fora do perfil, o fluxo
retoma as confirmações metodológicas habituais.

**Premissas internas da base oficial.** Com o perfil governado reconhecido, a interface não
pede ao usuário as confirmações de comparabilidade. O backend as resolve e registra a origem de
cada uma em "Método e limitações" e nas opções exportadas (`governed_premises`). Comparabilidade
temporal, comparabilidade entre municípios, populações municipais sem sobreposição e agregação
como soma dos componentes são regras do perfil, decididas pelo responsável pelo produto em
18/10/2026. A identidade territorial ao longo do tempo só vale depois de verificada nos dados:
cada código IBGE mantém o mesmo nome em todas as competências. Sem essa evidência, a confirmação
volta a ser pedida. Nas análises de distância da versão governada (análise espacial, referência
mais próxima e critérios com distância), também são internos o referencial SIRGAS 2000, regra do
perfil porque a fonte não declara o referencial, e a vírgula como separador decimal das
coordenadas, verificada nos dados. Bases importadas e significados alterados mantêm todas as
declarações.
Detalhes em [validação da base Brasil](Docs/DADOS_BRASIL_VALIDACAO.md#premissas-internas-da-base-oficial).

No chat, a escolha da fonte só aparece depois da primeira mensagem. A pergunta
sobre o conteúdo dos dados brasileiros consulta `/api/brazil/description`, que
verifica as fontes e devolve apenas informações agregadas sobre período, categorias
e recortes, sem enviar registros ao Gemini. O agente associa pedidos explícitos
sobre municípios ao recorte municipal e pedidos nacionais à fonte nacional,
sem solicitar detalhes sobre os arquivos internos.

Períodos são apresentados em português (por exemplo, junho de 2024).
Quantitativos e relatórios podem mostrar vários períodos **separadamente**; análises
temporais podem restringir a seleção a múltiplos períodos. A agregação territorial
continua restrita a uma competência, para não tratar pessoas observadas em meses
diferentes como pessoas únicas. Fora do perfil governado, a confirmação de premissas
metodológicas não verificáveis pelo catálogo, quando exigida, permanece obrigatória.

**Importar seus dados** mantém CSV, XLS e XLSX de qualquer país, inclusive escolha de
aba. As duas modalidades usam os mesmos contratos, filtros, motor, exportações e
verificação contextual do agente. Nenhum registro é enviado ao provedor de IA.

### Teste de navegação conversacional

Com as dependências de `backend/requirements-ui.txt` instaladas e depois de `npm run build`
em `frontend/`, execute na raiz:

```bash
python backend/tests/run_ui_checks.py --suite conversa
```

O executor sobe o servidor local com um catálogo sintético de duas fontes, roda o roteiro
`ui_conversational_smoke.py` e encerra o servidor. O teste bloqueia requisições externas e
verifica escolha de fonte, seletor inline, execução determinística e exportação dentro do chat.
Também é executado no job `ui-conversational` do CI. As bases brasileiras reais não participam
desse teste: elas são verificadas pelos jobs `dados-reais` e `ui-block1` (suíte
`base-versionada`). Ver [Testes](#testes) e [Política dos dados do Brasil](#política-dos-dados-do-brasil).

### Origem da base Brasil (administração)

O backend lê diretamente os dois arquivos versionados na raiz deste repositório privado,
`Dados_Brasil.xlsx` e `Dados_Municipios_Brasil.csv`, conferindo a cada requisição o tamanho e o
SHA-256 de cada um contra o manifesto governado `dados/brasil/manifesto.json`. Não há cópia
intermediária nem fallback: `.local/` não é lida. Arquivo alterado ou manifesto ausente,
desatualizado ou inválido tornam a base indisponível, com o motivo; o upload continua
funcionando. A API rejeita uma versão diferente daquela inspecionada pela interface.

```bash
python backend/brazil_data.py diagnostico          # origem física, versão e integridade
python backend/brazil_data.py manifesto            # identidade atual dos arquivos versionados
python backend/brazil_data.py manifesto --gravar   # só ao atualizar os arquivos, com revisão no Git
```

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
em memória, no formato AAAAMM, mediante confirmação do papel temporal. Componentes
inválidos são rejeitados. A transformação e a versão da base constam em **Método e
parâmetros**. Cabeçalhos antigos continuam suportados.

Limitações verificadas nas fontes de 10/10/2026: não há população ou coordenadas no
recorte nacional, nem identificadores individuais em qualquer recorte. Há 132 linhas
municipais com coordenadas fora dos intervalos válidos na fonte original (seis municípios nos
22 períodos). Com a camada geográfica complementar oficial incorporada (ver os dez pontos
abaixo), as análises espaciais da base Brasil municipal usam, somente nesses 132 registros, o
ponto oficial da sede municipal: a análise espacial (distância a um território de referência) da
base completa em uma competência passou a ser executável, e a referência mais próxima e os
critérios avaliam os 5.570 municípios. Bases importadas não recebem o complemento; nelas, ponto
inválido continua não avaliável (`COORDENADA_INVALIDA`). Rotatividade não pode ser calculada
dessas contagens. Nenhum registro foi corrigido ou excluído nos arquivos.
Detalhes e cobertura: [validação da base Brasil](Docs/DADOS_BRASIL_VALIDACAO.md).

### Política dos dados do Brasil

Situação vigente em 13/10/2026, enquanto esta for a política de distribuição:

1. **Versionamento.** `Dados_Brasil.xlsx` e `Dados_Municipios_Brasil.csv` estão versionados
   na raiz deste repositório privado desde o commit `a202be1` (12/10/2026). SHA-256 dos
   arquivos versionados: `7caa74d7a49f2f7cd2adf87b1c0546f7755ec0291dcb0ffbfae7c387dceb91d3`
   (nacional) e `89c027c90a2db5a4a7a7b5e3282404fb12b2bc30d500a4a79e49b6793749f512` (municipal).
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
   e junho de 2014 a 2024), 22 linhas nacionais e 122.534 municipais, 5.570 municípios por
   código IBGE, categoria MEDICINA, quantidade e população estimada sem ausências. Limitações:
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
   repositório; identidade em `dados/brasil/manifesto.json` (versão `819cf4628bff…`).
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

O banner permanece acima da navegação horizontal. Dados, escolhas, preparação e resultados seguem um único fluxo, sem coluna fixa de chat. A transcrição não ocupa a área principal; a última resposta do agente e o campo de mensagem permanecem juntos durante a exploração. “Resultados” concentra a visualização e “Alterar a preparação” retorna aos controles, sem executar cálculos. “Nova análise” abre as modalidades ou oferece análise independente/composição quando existe trabalho em andamento. Pedidos explícitos de apresentação em linguagem natural dispensam essa escolha; pedidos ambíguos aguardam a decisão antes de calcular outro componente.

“Histórico” reabre resultados da sessão sem recalcular. “Nova sessão” sempre pede confirmação, oferece CSV e impressão do resultado em exibição e informa que cada componente precisa ser exportado separadamente. Confirmar encerra a sessão no servidor e recarrega a interface, descartando arquivos, referências, conversa, resultados e grupos em memória. Se o encerramento falhar, a tela mantém o conteúdo e informa o erro. Antes de importar arquivos ou enviar mensagens, o usuário confirma a declaração de privacidade. O aceite vale para a sessão da aba; após o encerramento, o aceite é solicitado novamente. Se o navegador bloquear o armazenamento de sessão, o aceite permanece em memória até recarregar a página.

**Com base carregada:** pedidos reconhecidos pela gramática local seguem para `POST /api/exploration/interpret`; os demais seguem para `POST /api/llm/interpret-context`. Orientações de catálogo são atendidas localmente, inclusive durante uma pergunta pendente sobre municípios. No modo de importação, o arquivo é reenviado **somente ao backend Python local**; no modo Brasil, o navegador envia apenas a referência ao catálogo, recorte e versão. O backend revalida a estrutura, os mapeamentos, as confirmações e a matriz de aplicabilidade. O Gemini recebe apenas o pedido sanitizado e um resumo controlado de estados técnicos (papéis reconhecidos/confirmados e disponibilidade das capacidades). Nomes de campos, nomes de arquivo, territórios, categorias, períodos e linhas presentes no arquivo não são incluídos nesse resumo.

O Python também confronta deterministamente os períodos e categorias explicitamente propostos com os valores da base. Isso **não cria equivalências semânticas**: correspondência é literal após normalização básica de caixa e acentos; o nível territorial solicitado continua exigindo confirmação. Uma interpretação apenas prepara a análise; o cálculo depende de ação explícita na preparação. Trocar a fonte invalida interpretações e pendências daquela fonte; a conversa e os resultados já calculados permanecem consultáveis na memória da aba. Alterações de parâmetros e recorte invalidam respostas ainda em trânsito e exigem nova revalidação no backend.

**Sem base carregada:** o comportamento de primeira iteração continua disponível em `POST /api/llm/interpret`, mas a proposta é explicitamente preliminar e não verifica a existência dos valores sugeridos.

A conversa **não envia os arquivos CSV/Excel, seus campos ou registros ao Gemini**. Apenas mensagens digitadas pelo usuário, submetidas a uma camada conservadora de minimização e substituição de identificadores, são enviadas ao provedor. Isso **não implementa a triagem integral** de entidades nominais, estados e autorizações da SPEC v1.2.4. Não utilize dados pessoais ou sensíveis na conversa.

O LLM classifica também intenções conversacionais e perguntas sobre o agente; o backend responde com textos de catálogo local. Saudações, agradecimentos, ajuda, importação, privacidade, limites e explicação de densidade contam com tratamento determinístico sem consumo de franquia. Perguntas como “O que é possível fazer nessa página?” recebem a orientação correspondente, sem substituir a resposta pela apresentação inicial. A fonte atual aparece em uma identificação compacta; trocar dados continua disponível.

Para pedidos analíticos, o contrato admite uma proposta única ou até cinco candidatas de operação/indicador, cada alternativa ancorada em trecho literal do pedido sanitizado atual. Leituras materialmente diferentes geram escolhas, sem selecionar uma automaticamente. Com base disponível, a escolha explícita prepara a operação no backend; sem base, prepara o rascunho da conversa. Depois de validar a capacidade, o Python resolve os nomes municipais da manifestação original contra o catálogo **somente localmente**, incluindo paráfrases como “coloque Manaus e Tefé lado a lado”. Se só um município for informado numa comparação, pergunta qual outro; “analise dois municípios também” pede os nomes e aproveita a mensagem seguinte, sem escolher os primeiros municípios da base. Homônimos e trechos de recorte não confirmados continuam exigindo esclarecimento. O texto exibido vem de templates locais; **nenhum resultado factual, limiar ou cálculo vem do LLM**. Essa ampliação é parcial: ver [conversação incremental](Docs/CONVERSACAO_INCREMENTO_FN.md).

A evolução autorizada do diálogo está registrada em [Evolução conversacional](Docs/EVOLUCAO_CONVERSACIONAL_20261016.md). A interface usa contexto temporário verificado no backend para seleção, parâmetros, possibilidades do pré-exame e referências a resultados. “Esses municípios”, correções de indicador e inclusão de município reaproveitam a preparação. “E agora?” informa o contexto sem calcular. Densidade, quantitativos e comparação territorial já admitem perguntas sobre o resultado apresentado, com origem verificada, preservação das notas e explicações metodológicas pelo catálogo PT. “Explique de maneira mais simples” reduz a expansão metodológica, conservando fatos e limitações. Relação não calculada oferece preparação de comparação. As demais leituras analíticas conversacionais permanecem limitadas; os respectivos resultados e controles da interface continuam disponíveis. EN não está autorizado nesta integração.

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

Rotas experimentais: `GET /api/llm/status` (nunca retorna a chave), `POST /api/llm/interpret` (sem base) e `POST /api/llm/interpret-context` (multipart, com base validada apenas pelo Python). A transcrição permanece na memória da aba. O backend mantém contexto técnico e referências a resultados em sessão temporária, sem banco ou gravação em disco, isolada por token opaco. Encerrar sessão ou completar 1.800 segundos sem interação efetiva elimina o contexto; polling não renova o prazo. Reiniciar o backend também elimina as sessões. Testes offline utilizam respostas simuladas do provedor; a CI **não faz chamadas reais e não precisa de chave**. Falhas de conexão ou cota são mostradas sem alterar o motor analítico. Ver [evolução conversacional](Docs/EVOLUCAO_CONVERSACIONAL_20261016.md).

### Fronteira da SPEC

Referências: FN-INT-01/02 (propostas interpretativas), CFG-AMB e CFG-OPC (ambiguidade e opções), RQ-DAD-20 e RQ-PRV-02 (privacidade), INV-02/03/16 (autoridade factual), RQ-ESC-01/04 (escopo FTS), RQ-GOV-14 (decisões e confirmações), C-04 (verificação determinística), RQ-ARQ-06 (minimização), RQ-ORQ-01 (planos governados). FN-INT-01/02/03 e FN-META-01 têm cobertura **parcial**; alternativas ancoradas e orientações de catálogo não equivalem ao fluxo normativo completo de estados, CFG-DOC/V-16 e validações exaustivas. FN-INT-04, FN-ORQ-01 e CAP-SIN-01 continuam pendentes. Antes de alegar conformidade integral, essas lacunas precisam ser implementadas e auditadas.

## Testes

As regras de trabalho para pessoas e agentes (Claude, Codex e outros) estão em
[`AGENTS.md`](AGENTS.md). Antes de cada push, rode as verificações proporcionais à mudança, conforme a
seção 4 do `AGENTS.md`; o CI roda todas em todo push e precisa terminar em PASS. Comandos de
referência, na raiz:

```bash
(cd backend && python -m pytest -q)                                   # backend
(cd backend && ADT_REAL_DATA_DIR="$(cd .. && pwd)" python -m pytest -q -rs)  # com a base versionada: nada pulado
(cd frontend && npm ci && npm run build)                              # TypeScript e build
python backend/tests/run_ui_checks.py                                 # todas as jornadas de navegador
python backend/tests/run_ui_checks.py --roteiro ui_stabilization.py   # só os roteiros indicados
python .github/scripts/verificar_governanca.py                        # registro de comportamento e jornadas no CI
```

Quando o risco justificar, o script `python scripts/verificar_tudo.py` roda todas essas verificações
na ordem e termina com um resumo do que passou, falhou ou ficou de fora, e por quê; os logs ficam em `.local/verificacao/`. Os testes
com dados reais só rodam quando a mudança toca o motor, a API ou os dados (`--dados-reais sim` força),
e o script decide sozinho a dispensa do `npm ci` descrita abaixo (`--npm-ci` força). No Windows, ele
já define `PYTHONUTF8=1` e uma pasta temporária gravável para o pytest. A governança confere os
commits; depois do commit, rode-a de novo antes do push.

Localmente, o `npm ci` pode ser dispensado quando `package.json` e `package-lock.json` não mudaram
desde o último `npm ci` bem-sucedido; basta o `npm run build`. O CI sempre roda o `npm ci`.

Para a conferência visual, `python scripts/capturar_telas.py` sobe o servidor de testes com a base
versionada e percorre as telas principais: início, preparação e resultado da densidade (mapa,
gráficos, tabela e celular), escolha de períodos da evolução temporal, preparação da análise espacial
e condições avançadas. As capturas ficam em `.local/capturas/`. Rode depois do `npm run build`; nada
vai para o provedor de IA e nenhum dado é alterado.

No Windows (PowerShell), defina `$env:ADT_REAL_DATA_DIR` com o caminho completo da raiz do
repositório. Sem o Google Chrome instalado, defina `ADT_BROWSER_CHANNEL=chromium` para as jornadas.

O workflow `.github/workflows/ci.yml` roda no push e em pull requests. Nenhuma verificação chama o
provedor real de IA.

| Job | O que verifica |
|---|---|
| `backend` | Suíte pytest. Os testes de dados reais são pulados aqui e rodam em `dados-reais`. |
| `dados-reais` | Integridade da base Brasil versionada (tamanho e SHA-256 contra `dados/brasil/manifesto.json`) e a suíte completa com os dados reais. Falha se algum teste for pulado. |
| `frontend` | TypeScript e build de produção. |
| `ui-conversational` | Jornada conversacional (suíte `conversa`). |
| `ui-block1` | Blocos 1 a 3 (suíte `bloco1`), interpretação com Gemini simulado (`gemini-simulado`) e jornada do Bloco 1 com a base versionada (`base-versionada`). |
| `governanca` | Toda mudança de comportamento está em [`Docs/REGISTRO_DE_COMPORTAMENTO.md`](Docs/REGISTRO_DE_COMPORTAMENTO.md) ou foi declarada sem alteração, e todo roteiro de navegador roda no CI. |
| `resumo` | Quadro único com o resultado de todos os jobs. Falha se qualquer um falhar. |

As jornadas de navegador rodam pelo executor único `backend/tests/run_ui_checks.py`. Ele prepara
os catálogos, sobe e encerra os servidores locais, roda cada roteiro isolado e, no final, lista
o resultado de todos. Uma falha não esconde as seguintes. Um push novo no mesmo ramo cancela a
execução anterior do CI, e o resultado exibido é sempre o do estado mais recente. Medições de
tempo (`backend/tests/bench_*.py`) ficam fora do CI.

Os roteiros de navegador anteriores à interface conversacional foram movidos para
[`backend/tests/legado/`](backend/tests/legado/README.md). Lá estão o motivo, o mapa do que
cobriam e as lacunas que ainda precisam de roteiros novos. A preparação em três etapas continua
descrita em [preparação guiada](Docs/PREPARACAO_GUIADA.md).

## Ponte semântica e habilitação de análises

O motor `backend/semantic_bridge.py` reutiliza regras de reconhecimento governado da SPEC para propor a associação entre **nomes originais das colunas** e papéis analíticos internos, sem exigir renomeação pelo usuário. Correspondências não conclusivas (por exemplo, "Total de médicos únicos") aguardam confirmação e não autorizam deduções de unicidade. O exame automático `/api/inspect` fornece candidatos, perfis de colunas e uma matriz inicial; `/api/preflight` a recalcula após esclarecimentos. O endpoint `/api/analyze` **revalida** a habilitação antes da execução.

**Experimento híbrido:** os cartões clicáveis para solicitar análises ainda diferem do canal conversacional normativo da SPEC; a interpretação com LLM não substitui os gates nem autoriza execução. Ver `Docs/SEMANTIC_BRIDGE_ADAPTACOES.md` para rastreabilidade, divergências e limitações.

Exemplo de CSV com `0`, `Competência`, `Total de médicos únicos`: a coluna `Competência` é reconhecida como período, `Total de médicos únicos` é **proposto** como quantitativo; o cabeçalho `0` não é presumido território. Após confirmação da contagem/unidade, categoria constante ou domínio FTS autorizado e comparabilidade temporal quando cabível, quantitativos e série temporal podem ficar disponíveis **sem inventar território nem população**. Densidade continuará indisponível sem o denominador e recorte apropriados.

## Validação local e resolução de registros múltiplos

Municípios ou outras unidades com o mesmo nome podem representar lugares distintos. Selecione a coluna territorial desejada e, nos requisitos da capacidade, associe e confirme o código que distingue essas unidades. O nome continua sendo apresentado junto ao código. O aplicativo não confere códigos em cadastros externos.

A unidade da contagem deve ser declarada. Profissionais distintos em um município, categoria e período não implicam aditividade entre recortes. Cópias idênticas exigem autorização específica para remoção; componentes desagregados exigem dimensões que os distingam e declaração de ausência de sobreposição. População repetida no mesmo território e período é utilizada uma vez; conflitos impedem o cálculo.

O CSV contém todos os resultados, com precisão numérica preservada; a tabela mostra até 150 linhas. “Método e parâmetros” exporta as associações, declarações, filtros, versão do método e identificação do conteúdo analisado. PDF usa a impressão do navegador e abrange a apresentação visível.

Na raiz do repositório, em PowerShell:

```powershell
py -m pip install -r backend/requirements-test.txt
$env:ADT_REAL_DATA_DIR = 'C:\Users\User\Desktop\Dados_Brasil'
py -m pytest -q
```

Os testes reais leem os arquivos somente em leitura e verificam seus hashes antes e depois. Sem a variável, eles são omitidos. Como a base Brasil está versionada na raiz do repositório, `ADT_REAL_DATA_DIR` pode apontar para a própria raiz. É assim que o job `dados-reais` do CI executa os 30 testes reais em todo push, sem nenhum teste pulado (ver [Testes](#testes)).

O antigo gate de Densidade pelo navegador (`ui_smoke.py`, upload do CSV municipal com conferência linha a linha) usa a interface anterior à conversacional e foi movido para [`backend/tests/legado/`](backend/tests/legado/README.md). Hoje, a conferência de todas as linhas contra aritmética independente roda no job `dados-reais`, e a jornada pelo navegador com a base versionada roda na suíte `base-versionada` (job `ui-block1`). Capturas das jornadas ficam em `.local/ui-validation/`, ignorada pelo Git.

## Referência geográfica mais próxima (Bloco 2, Etapa 1)

Para cada município-alvo, indica a referência autorizada geograficamente mais próxima, com
código, distância geodésica direta em quilômetros (Karney, elipsoide GRS80/SIRGAS2000, sem
arredondamento no cálculo) e cobertura das referências. Escolha o cartão **Referência mais
próxima** ou peça, por exemplo, "Calcule a referência mais próxima de Manaus, Tefé e
Parintins": o comando prepara só a operação e os alvos, sem criar referências nem executar.
As referências são definidas pelo usuário, por lista de municípios (nome ou código) ou por
critério simples de densidade (operador e valor por 1.000 habitantes, sem valor sugerido).
O período é escolhido explicitamente. Na versão governada da base Brasil, o referencial
SIRGAS 2000 e a vírgula decimal das coordenadas são premissas internas, registradas nas notas do
resultado; em bases importadas e em outras versões, referencial e separador decimal são
confirmados explicitamente, sem referencial presumido. Nenhum referencial é transformado.
Referências ou alvos sem coordenada válida
ficam registrados como não avaliáveis, com `minimo_completo` e `minimo_avaliaveis`
distintos, empates preservados e ausência nunca convertida em zero. A distância não
representa trajeto viário, tempo de deslocamento nem acessibilidade. O LLM não escolhe
referências nem recebe esta capacidade. Detalhes, testes e desempenho:
[Bloco 2, Etapa 1](Docs/BLOCO2_ETAPA1_REFERENCIAS_PROXIMIDADE.md).

## Critérios combinados, réguas e rankings (Bloco 2, Etapa 2)

O cartão **Critérios combinados** aplica condições simultâneas sobre densidade por 1.000
habitantes, quantidade, população, distância à referência mais próxima, pertença a uma lista de
territórios e UF, com `<`, `≤`, `>`, `≥`, `=`, `≠` combinados por E, OU e NÃO em três estados
(`ATENDE`, `NAO_ATENDE`, `NAO_AVALIAVEL`; indeterminação nunca vira “não atende”). Cada condição
tem uma régua com indicador, unidade, operador, valor, universo, competência/categoria e origem
“escolha do usuário”; não há pontos de corte padrão nem caráter legal, sanitário ou científico.
O resultado separa quem atende, não atende e não é avaliável (com motivos por condição),
permite ordenar (posições 1, 2, 2, 4), selecionar os N primeiros com os empatados no corte,
definir faixas `[a, b)` com o último intervalo fechado, comparar com o conjunto anterior,
exportar CSV/JSON e reutilizar o conjunto como seleção territorial ou referências. A distância
usa o mínimo do conjunto completo de referências; o mínimo entre as avaliáveis e a restrição às
referências de elegibilidade confirmada exigem aceitação explícita e ficam rotulados. Na conversa,
pedidos como “Mostre os municípios com menos de 2 médicos por mil habitantes”, “Agora considere
também distância superior a 150 km”, “Ordene esses municípios pela distância”, “Mostre os 20
primeiros” e “Compare esse conjunto com o anterior” são estruturados por um canal determinístico
(o LLM não recebe a capacidade), com perguntas quando há ambiguidade material. Detalhes, testes e
desempenho: [Bloco 2, Etapa 2](Docs/BLOCO2_ETAPA2_CRITERIOS_INTEGRACAO.md).

## Mapas e exploração visual integrada (Bloco 3)

Na própria página de resultados, as abas **Mapa**, **Gráficos** e **Tabela** representam o mesmo
resultado, sem nova análise. O backend anexa a cada resultado um contrato de apresentação
(`metadata.representacao`) com as colunas representáveis (rótulo, unidade, natureza e capacidade de
origem) e as coordenadas autorizadas de cada território na competência do resultado, pela mesma regra
das análises espaciais, respeitando a competência e a camada complementar governada. Na versão Brasil íntegra e correspondente ao manifesto governado, o mapa de uma única competência aparece automaticamente: uma configuração contextual adota SIRGAS2000 **somente para apresentação** e o formato decimal conhecido da fonte. O datum original não é declarado pela fonte; essa premissa ilustrativa fica identificada na tela e no JSON, sem mudar as opções analíticas ou calcular distâncias. Nas análises de distância dessa versão, o referencial já é premissa interna do cálculo: a legenda do mapa informa essa origem e o JSON a registra em `premissa_referencial`. Não há padrão para uploads ou outras versões externas. Sem localização confirmada, a interface explica a indisponibilidade e mantém tabela e gráficos; a configuração da origem de um upload fica nas opções avançadas da preparação, fora da aba Mapa. O mapa de
pontos (canvas, sem serviço externo nem chave de API) amplia, desloca, seleciona por clique, busca ou
tabela, mostra estados do motor, não avaliáveis em anel vazado, referências e ligações ilustrativas
(não trajeto); a seleção é compartilhada com tabela e gráficos e pode ser levada à próxima análise sem
executá-la. Barras e linhas usam só valores e classes do motor, sem quantis, tendências ou posições
criadas na tela. As barras incluem todos os territórios, com rolagem e montagem das linhas visíveis quando há mais de 40; séries com mais de oito territórios têm páginas de oito, sem excluir os demais. Quantitativos de pessoas com escopo de força de trabalho confirmado usam o rótulo “profissionais”. As tabelas têm filtros por coluna (texto e comparações numéricas como `>= 2`), ordenação visual, páginas de 150 registros e exportação CSV de todo o filtro. Competências aparecem como mês/ano (06/2024), sem alterar o CSV. Resultados de densidade, quantitativos, relatório e evolução com até três registros mostram cartões de destaque com os valores do motor (na evolução, inicial → final e variação). No mapa, até 12 pontos levam o nome do território. O gráfico de linhas enquadra o eixo vertical nos valores observados, informa quando ele não começa em zero e rotula só o último valor de cada série. O CSV superior continua integral. A consulta técnica fica no download “Método e parâmetros”; não há JSON embutido na tela, checklist territorial duplicado ou botões de imagem PNG. A impressão inclui a visualização e a página da tabela em exibição. Não há limites de UF nem mapas coropléticos (malha oficial indisponível neste
ambiente). Detalhes, testes, desempenho e conformidade: [Bloco 3](Docs/BLOCO3_MAPAS_VISUALIZACOES.md).

## Escopo e limitações do protótipo

Os doze cartões apresentam a navegação e acionam rotas do motor. A versão implementa percursos iniciais para densidade, quantitativos, distribuição por quantis, comparação, mudança temporal, agregação, distância geodésica, ordenação, coortes, tabelas/relatório básico, referência geográfica mais próxima, critérios combinados com rankings e faixas, e representação integrada em mapa de pontos, barras, linhas e tabela.

**Não declara conformidade integral com a SPEC.** Ainda são necessários, entre outros: suporte a várias bases e planilhas auxiliares simultâneas; normalização completa de tabelas largas e dados individualizados; versão integral do catálogo de significados e vocabulário governado; todos os tratamentos de ambiguidade e estados de autorização; seleção territorial avançada; regras de comparabilidade longitudinal; todas as subclasses de tendência; PDF gerado diretamente por servidor e relatório consolidado HTML; limites territoriais oficiais e mapas coropléticos; cobertura exaustiva dos cenários de aceite; escala de grandes bases. Os cartões de comparação, tendência e rotatividade produzem resultados preliminares que exigem significados semânticos autorizados antes de uso substantivo.

Uploads são processados em memória por requisição e não são persistidos pelo aplicativo. O arquivo é reenviado a cada análise; o limite experimental é de 30 MB. Evite bases pessoais e sensíveis no protótipo. Para arquivos muito grandes, será preciso processamento incremental/local, sessão segura e proteção de dados aprofundada.

Amostras da interface são exemplos ilustrativos, **não diagnósticos reais**. Métodos não podem inventar limiares normativos nem presumir unicidade dos profissionais no agregado.
