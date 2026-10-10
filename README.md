# Teste Agente — Portal Experimental

Experimento isolado de desenvolvimento para o **Agente Diagnóstico Territorial da Força de Trabalho na Saúde**.

- **Interface:** React + TypeScript + Tailwind; telas responsivas de início e resultados com upload, **associação semântica por coluna**, confirmação guiada e **seletor de análises em carrossel com indicação de aplicabilidade e seleção em relevo**, além de filtros, gráficos, tabelas e exportação CSV / impressão em PDF.
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

## Conversação com Gemini — iteração 2 contextual (opcional)

A interface possui uma área de conversa na página inicial, abaixo dos atalhos de análises. Antes de importar arquivos ou enviar mensagens, o usuário confirma a declaração de privacidade em um pop-up. O aceite vale para a sessão da aba, inclusive após recarregar a página; uma nova aba solicita nova confirmação. Se o navegador bloquear o armazenamento de sessão, o aceite permanece em memória até recarregar a página.

**Com base carregada:** cada mensagem segue para `POST /api/llm/interpret-context`. O arquivo é reenviado **somente ao backend Python local**, que revalida a estrutura, os mapeamentos, as confirmações e a matriz de aplicabilidade. O Gemini recebe apenas o pedido sanitizado e um resumo controlado de estados técnicos (papéis reconhecidos/confirmados e disponibilidade das capacidades). Nomes de campos, nomes de arquivo, territórios, categorias, períodos e linhas presentes no arquivo não são incluídos nesse resumo.

O Python também confronta deterministamente os períodos e categorias explicitamente propostos com os valores da base. Isso **não cria equivalências semânticas**: correspondência é literal após normalização básica de caixa e acentos; o nível territorial solicitado continua exigindo confirmação. A interface mostra habilitação, pendências e discrepâncias e **não executa operações**. Ao trocar a base ou alterar o contexto, propostas anteriores são descartadas na aba, evitando reuso silencioso de interpretação desatualizada.

**Sem base carregada:** o comportamento de primeira iteração continua disponível em `POST /api/llm/interpret`, mas a proposta é explicitamente preliminar e não verifica a existência dos valores sugeridos.

A conversa **não envia os arquivos CSV/Excel, seus campos ou registros ao Gemini**. Apenas mensagens digitadas pelo usuário, submetidas a uma camada conservadora de minimização e substituição de identificadores, são enviadas ao provedor. Isso **não implementa a triagem integral** de entidades nominais, estados e autorizações da SPEC v1.2.4. Não utilize dados pessoais ou sensíveis na conversa.

O LLM retorna uma proposta estruturada de operação/indicador; o backend valida os valores permitidos e só apresenta expressões territoriais, categorias e períodos ancorados no texto sanitizado. O texto explicativo mostrado na interface é composto por templates locais; **nenhum resultado factual, limiar ou cálculo vem do LLM**. A opção **Ver requisitos** só abre o cartão sugerido: não executa nem confirma nada.

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

`py backend/tests/ui_carousel_smoke.py` verifica as dez análises no seletor, setas, teclado, roda do mouse, gesto de deslizar no celular, destaque da seleção, ações do banner, responsividade e redução de movimento. Percorrer os cards não seleciona nem executa análises; a seleção permite abrir os requisitos, que continuam sendo verificados antes da execução.

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

Os testes reais leem os arquivos sem copiá-los para o Git e verificam seus hashes antes e depois. Sem a variável, os dois testes reais são omitidos. Para repetir o gate de Densidade no Chrome instalado, mantenha Python e Vite ativos e execute:

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
