# Teste Agente — Portal Experimental

Experimento isolado de desenvolvimento para o **Agente Diagnóstico Territorial da Força de Trabalho na Saúde**.

- **Interface:** React + TypeScript + Tailwind; após o banner, a conversa concentra escolha da fonte, carrossel de análises, campos editáveis no próprio texto, confirmações agrupadas, resultados e exportações. Ajustes metodológicos excepcionais continuam disponíveis em uma seção avançada recolhida.
- **Motor:** Python + FastAPI; as dez capacidades permanecem determinísticas.
- **Conversa opcional:** integração experimental com Gemini para propor interpretações de solicitações. A API de LLM não recebe a base, não executa análises nem confirma parâmetros automaticamente.
- **Documento de referência:** IMPLEMENTATION_SPEC.md v1.2.4, **apenas para os contratos metodológicos e semânticos**. A interface e a arquitetura física são novas, independentes das diretrizes de UX daquele projeto.
- **Gemini não é requisito para o funcionamento analítico.** Sem chave, a conversa fica indisponível e as dez capacidades continuam operacionais. Esta integração é apenas a primeira iteração e **não representa conformidade integral com a governança de LLM da SPEC**.

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
municípios. **Abrangência da análise** permite escolher Brasil ou Municípios
explicitamente. Trocar de recorte limpa resultados; confirmações comuns verificáveis
de período/categoria são preservadas. A preparação de cada recorte é mantida na memória
da aba e restaurada ao retornar à mesma versão, sempre com novo pré-exame do backend.

As fontes mantêm suas granularidades: não há junção de linhas, propagação de população
municipal para o Brasil ou soma automática de pessoas entre municípios. Agregação
municipal só ocorre com as declarações já exigidas pelo motor, inclusive o rótulo de
possível dupla contagem quando se autoriza somar componentes.

A plataforma reconhece automaticamente as associações e significados da base Brasil
**somente** quando a estrutura, o mapeamento e a categoria única MEDICINA correspondem
ao perfil governado (`backend/brazil_catalog_profile.py`), após a verificação de
integridade do catálogo. Nesse caso, a unidade de contagem declarada para o catálogo
é pessoas por território/período; isso **não** implica identidade única entre
municípios ou meses. Nenhum perfil é aplicado ao upload do usuário, a estruturas
desconhecidas ou a categorias inesperadas. Para bases fora do perfil, o fluxo
retoma as confirmações metodológicas habituais.

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
diferentes como pessoas únicas. A confirmação de premissas metodológicas não
verificáveis pelo catálogo, quando exigida, permanece obrigatória.

**Importar seus dados** mantém CSV, XLS e XLSX de qualquer país, inclusive escolha de
aba. As duas modalidades usam os mesmos contratos, filtros, motor, exportações e
verificação contextual do agente. Nenhum registro é enviado ao provedor de IA.

### Teste de navegação conversacional

Com o backend e o Vite locais em execução, e com dependências de
`backend/requirements-ui.txt` instaladas, execute:

```bash
cd backend
python tests/ui_conversational_smoke.py
```

O teste usa CSV sintético, bloqueia requisições externas e verifica escolha
de fonte, seletor inline, execução determinística e exportação dentro do chat.
Também é executado no job `ui-conversational` da CI. As bases brasileiras
reais continuam fora do Git e exigem validações locais próprias.

### Instalar a base Brasil (administração)

Os dados não acompanham o código no Git. Prepare uma cópia privada validada:

```powershell
python backend/install_brazil_data.py --source 'C:\Users\User\Desktop\Dados_Brasil'
```

O instalador valida os dois arquivos, preserva os bytes dos originais e grava cópias
e manifesto SHA-256 em `.local/datasets/brasil/`, ignorada pelo Git. Recusa sobrescrever
uma instalação existente. O aplicativo passa a ler essas cópias; não precisa mais
acessar a pasta original. Não publique as cópias em repositórios nem no diretório
público do frontend. Se a instalação estiver ausente, incompleta ou adulterada, a
interface informa a indisponibilidade e o upload continua funcionando.

A origem fica isolada em `backend/brazil_data.py`. O diretório padrão é relativo ao
projeto; `ADT_BRASIL_DATA_DIR` permite substituí-lo, e o instalador aceita
`--destination <pasta nova>`. Uma atualização pode ser instalada e validada em outra
pasta antes de alterar a configuração. A API verifica ambos os hashes e rejeita uma
versão diferente daquela inspecionada pela interface.

Para uma futura operação online, será necessário disponibilizar as fontes autorizadas
ao backend e configurar esse diretório ou adaptar o carregador para outra origem,
preservando o contrato de versão, integridade e granularidade. Os dados devem continuar
fora do Git e dos arquivos públicos do frontend. A escolha de infraestrutura, o
provisionamento e a publicação ficam para uma etapa futura; não foram implementados.

Campos `periodo_ano` e `periodo_mes` são preservados e compõem **Período (ano e mês)**
em memória, no formato AAAAMM, mediante confirmação do papel temporal. Componentes
inválidos são rejeitados. A transformação e a versão da base constam em **Método e
parâmetros**. Cabeçalhos antigos continuam suportados.

Limitações verificadas nas fontes de 10/10/2026: não há população ou coordenadas no
recorte nacional, nem identificadores individuais em qualquer recorte. Há 132 linhas
municipais com coordenadas fora dos intervalos válidos (seis municípios nos 22 períodos).
A análise espacial da base completa permanece bloqueada, e rotatividade não pode ser
calculada dessas contagens. Nenhum registro foi corrigido ou excluído automaticamente.
Detalhes e cobertura: [validação da base Brasil](Docs/DADOS_BRASIL_VALIDACAO.md).

## Conversação com Gemini — iteração 2 contextual (opcional)

O chat ocupa a área central da página inicial, com as dez análises em um carrossel compacto dentro da conversa. Antes de importar arquivos ou enviar mensagens, o usuário confirma a declaração de privacidade em um pop-up. O aceite vale para a sessão da aba, inclusive após recarregar a página; uma nova aba solicita nova confirmação. Se o navegador bloquear o armazenamento de sessão, o aceite permanece em memória até recarregar a página.

**Com base carregada:** cada mensagem segue para `POST /api/llm/interpret-context`. No modo de importação, o arquivo é reenviado **somente ao backend Python local**; no modo Brasil, o navegador envia apenas a referência ao catálogo, recorte e versão. O backend revalida a estrutura, os mapeamentos, as confirmações e a matriz de aplicabilidade. O Gemini recebe apenas o pedido sanitizado e um resumo controlado de estados técnicos (papéis reconhecidos/confirmados e disponibilidade das capacidades). Nomes de campos, nomes de arquivo, territórios, categorias, períodos e linhas presentes no arquivo não são incluídos nesse resumo.

O Python também confronta deterministamente os períodos e categorias explicitamente propostos com os valores da base. Isso **não cria equivalências semânticas**: correspondência é literal após normalização básica de caixa e acentos; o nível territorial solicitado continua exigindo confirmação. A interface mostra habilitação, pendências e discrepâncias e **não executa operações**. Uma nova base reinicia o histórico; alterações de parâmetros e recorte preservam a conversa, mas invalidam respostas ainda pendentes e exigem nova revalidação no backend.

**Sem base carregada:** o comportamento de primeira iteração continua disponível em `POST /api/llm/interpret`, mas a proposta é explicitamente preliminar e não verifica a existência dos valores sugeridos.

A conversa **não envia os arquivos CSV/Excel, seus campos ou registros ao Gemini**. Apenas mensagens digitadas pelo usuário, submetidas a uma camada conservadora de minimização e substituição de identificadores, são enviadas ao provedor. Isso **não implementa a triagem integral** de entidades nominais, estados e autorizações da SPEC v1.2.4. Não utilize dados pessoais ou sensíveis na conversa.

O LLM classifica também intenções conversacionais e perguntas sobre o agente; o backend responde com textos de catálogo local. Saudações, ajuda, importação, privacidade, limites e explicação de densidade contam com tratamento determinístico sem consumo de franquia. A parte implementada dessas funções é experimental, não corresponde à governança integral FN-INT/FN-META da SPEC. Para pedidos analíticos, o LLM retorna uma proposta estruturada de operação/indicador; o backend valida os valores permitidos e só apresenta expressões territoriais, categorias e períodos ancorados no texto sanitizado. O texto explicativo mostrado na interface é composto por templates locais; **nenhum resultado factual, limiar ou cálculo vem do LLM**. A opção **Ver requisitos** só abre o cartão sugerido: não executa nem confirma nada.

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

Rotas experimentais: `GET /api/llm/status` (nunca retorna a chave), `POST /api/llm/interpret` (sem base) e `POST /api/llm/interpret-context` (multipart, com base validada apenas pelo Python). O histórico de conversa permanece apenas na memória da aba do navegador; o backend não o grava. Testes offline utilizam respostas simuladas do provedor; a CI **não faz chamadas reais e não precisa de chave**. Falhas de conexão ou cota são mostradas sem alterar o motor analítico.

### Fronteira da SPEC

Referências: FN-INT-01/02 (propostas interpretativas), RQ-DAD-20 e RQ-PRV-02 (privacidade), INV-02/03/16 (autoridade factual), RQ-ESC-01/04 (escopo FTS), RQ-GOV-14 (decisões e confirmações), C-04 (verificação determinística), RQ-ARQ-06 (minimização), RQ-ORQ-01 (planos governados). A implementação experimental **não realiza ainda** FN-INT-03/04, FN-ORQ-01, FN-META-01 e CAP-SIN-01, nem cobre o fluxo normativo completo de estados, alternativas ancoradas, catálogo documental V-16 e validações exaustivas. Antes de usar informações sensíveis ou alegar conformidade científica integral, essas lacunas precisam ser implementadas e auditadas.

## Testes

```bash
cd backend
python -m pytest -q
```

```bash
cd frontend
npm run build
```

A GitHub Action `.github/workflows/ci.yml` executa ambos no push e em pull requests.

Com os servidores locais ativos e `backend/requirements-ui.txt` instalado, `py backend/tests/ui_session_smoke.py` verifica a declaração por sessão, navegação por teclado, importação e cálculo com dados sintéticos, exportação CSV, conversa com e sem base, recuperação do serviço e telas desktop/mobile. As respostas de IA são simuladas; esse teste não chama o provedor.

O layout atual reúne chat e carrossel compacto e apresenta a preparação em três
etapas abaixo da conversa, após a escolha do usuário.
`python backend/tests/ui_preparation_smoke.py` verifica esse fluxo, incluindo seleção,
pendências, confirmação do código territorial, troca de abrangência, densidade,
quantitativos, população na distribuição, falha/recuperação do pré-exame e upload
internacional. Requer os servidores locais e o catálogo Brasil instalado; não chama
o Gemini. Ver [preparação guiada](Docs/PREPARACAO_GUIADA.md).

Os seis roteiros de navegador (`ui_session_smoke.py`, `ui_carousel_smoke.py`,
`ui_audit_smoke.py`, `ui_preparation_smoke.py`, `ui_brazil_smoke.py` e `ui_smoke.py`)
refletem a interface atual. Após `npm run build`, podem ser executados contra
`python backend/tests/serve_ui_offline.py` (build + API, sem transporte externo de IA),
com `ADT_UI_URL=http://127.0.0.1:18000/`; os dois últimos exigem `ADT_REAL_DATA_DIR`.
`python backend/tests/ui_integration_smoke.py` percorre a conversa pelo backend real, com
transporte Gemini simulado: inicie antes um processo novo de
`python backend/tests/serve_ui_fake_gemini.py` (porta 18200) a cada execução.

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

Os testes reais leem os arquivos sem copiá-los para o Git e verificam seus hashes antes e depois. Sem a variável, os 20 testes reais são omitidos. Para repetir o gate de Densidade no Chrome instalado, mantenha Python e Vite ativos e execute:

```powershell
py -m pip install -r backend/requirements-ui.txt
py backend/tests/ui_smoke.py
```

O teste importa a base real, confirma o contexto, resolve os homônimos, executa pela interface, baixa o CSV e confere cada linha contra o original usando Decimal. Evidência resumida e capturas ficam em `.local/ui-validation/`, ignorada pelo Git.

## Escopo e limitações do protótipo

Os dez cartões apresentam a navegação e acionam rotas do motor. A versão implementa percursos iniciais para densidade, quantitativos, distribuição por quantis, comparação, mudança temporal, agregação, distância geodésica, ordenação, coortes e tabelas/relatório básico.

**Não declara conformidade integral com a SPEC.** Ainda são necessários, entre outros: suporte a várias bases e planilhas auxiliares simultâneas; normalização completa de tabelas largas e dados individualizados; versão integral do catálogo de significados e vocabulário governado; todos os tratamentos de ambiguidade e estados de autorização; seleção territorial avançada; regras de comparabilidade longitudinal; todas as subclasses de tendência; referências e faixas espaciais; PDF gerado diretamente por servidor; cobertura exaustiva dos cenários de aceite; escala de grandes bases. Os cartões de comparação, tendência e rotatividade produzem resultados preliminares que exigem significados semânticos autorizados antes de uso substantivo.

Uploads são processados em memória por requisição e não são persistidos pelo aplicativo. O arquivo é reenviado a cada análise; o limite experimental é de 30 MB. Evite bases pessoais e sensíveis no protótipo. Para arquivos muito grandes, será preciso processamento incremental/local, sessão segura e proteção de dados aprofundada.

Amostras da interface são exemplos ilustrativos, **não diagnósticos reais**. Métodos não podem inventar limiares normativos nem presumir unicidade dos profissionais no agregado.
