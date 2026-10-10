# Teste Agente — Portal Experimental

Experimento isolado de desenvolvimento para o **Agente Diagnóstico Territorial da Força de Trabalho na Saúde**.

- **Interface:** React + TypeScript + Tailwind; uma página responsiva com upload, **associação semântica por coluna**, confirmação guiada e **cartões destacados/esmaecidos pela matriz de aplicabilidade**, além de filtros, gráficos, tabelas e exportação CSV / impressão em PDF.
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

## Conversação com Gemini — primeira iteração (opcional)

A interface possui uma seção **Assistente IA** entre o carregamento/configuração dos dados e os dez cartões analíticos.

A conversa **não envia os arquivos CSV/Excel, seus campos ou registros ao Gemini**. Apenas mensagens digitadas pelo usuário, submetidas a uma camada conservadora de minimização e substituição de identificadores, são enviadas ao provedor. Isso **não implementa a triagem integral** de entidades nominais, estados e autorizações da SPEC v1.2.4. Não utilize dados pessoais ou sensíveis na conversa.

O LLM retorna uma proposta estruturada de operação/indicador; o backend valida os valores permitidos e só apresenta expressões territoriais, categorias e períodos ancorados no texto sanitizado. O texto explicativo mostrado na interface é composto por templates locais; **nenhum resultado factual, limiar ou cálculo vem do LLM**. A opção **Ver requisitos** só abre o cartão sugerido: não executa nem confirma nada.

### Configurar localmente (Windows PowerShell)

1. Certifique-se de que a chave da **Gemini Developer API** pertence ao projeto e à modalidade de faturamento pretendida. A disponibilidade do nível gratuito deve ser verificada diretamente no Google AI Studio; o aplicativo **não verifica nem garante custo zero**.
2. No PowerShell usado para iniciar o backend, sem colocar a chave nos arquivos do Git:

```powershell
cd "C:\Users\User\Desktop\Github\Teste-Agente\backend"
$chaveSegura = Read-Host "Cole a chave do Gemini" -AsSecureString
$ptr = [Runtime.InteropServices.Marshal]::SecureStringToBSTR($chaveSegura)
try { $env:GEMINI_API_KEY = [Runtime.InteropServices.Marshal]::PtrToStringBSTR($ptr) } finally { [Runtime.InteropServices.Marshal]::ZeroFreeBSTR($ptr) }
py -m uvicorn main:app --reload --port 8000
```

> O comando funciona no Windows PowerShell 5.1 e no PowerShell mais recente. A entrada da chave é ocultada; a variável é válida somente no processo do terminal e nos processos filhos. Não salve nem envie a chave ao chat ou ao GitHub.

Em outra janela:

```powershell
cd "C:\Users\User\Desktop\Github\Teste-Agente\frontend"
npm.cmd run dev
```

Abra `http://localhost:5173/#assistente`. Verifique **Gemini configurado**; escreva, por exemplo, "Quero analisar a distribuição da densidade de médicos por município em 202406", confirme o aviso de privacidade e clique em **Interpretar com Gemini**. Na resposta, clique **Ver requisitos** se desejar continuar no motor.

O backend utiliza por padrão `gemini-2.5-flash-lite`. A seleção opcional de outro modelo explicitamente admitido é feita por `ADT_GEMINI_MODEL` no ambiente do backend. Modelos e cotas disponíveis podem variar. A função usa uma chamada REST com JSON estruturado, timeout e erros tratados; nenhuma dependência nova é necessária. O contador de **20 requisições diárias** é apenas uma barreira local por processo, reiniciada quando o servidor reinicia: **não substitui cotas nem limites de faturamento do Google**.

Rotas experimentais: `GET /api/llm/status` (nunca retorna a chave) e `POST /api/llm/interpret`. O histórico de conversa permanece apenas na memória da aba do navegador; o backend não o grava. Testes offline utilizam respostas simuladas do provedor; a CI **não faz chamadas reais e não precisa de chave**. Falhas de conexão ou cota são mostradas sem alterar o motor analítico.

### Fronteira da SPEC

Referências: FN-INT-01/02 (propostas interpretativas), RQ-DAD-20 e RQ-PRV-02 (privacidade), INV-02/03/16 (autoridade factual), RQ-ESC-01/04 (escopo FTS), RQ-GOV-14 (decisões e confirmações). A implementação experimental não cobre o fluxo normativo completo de estados, alternativas ancoradas, catálogo documental V-16 e validações exaustivas. Antes de usar informações sensíveis ou alegar conformidade científica integral, essas lacunas precisam ser implementadas e auditadas.

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

## Ponte semântica e habilitação de análises

O motor `backend/semantic_bridge.py` reutiliza regras de reconhecimento governado da SPEC para propor a associação entre **nomes originais das colunas** e papéis analíticos internos, sem exigir renomeação pelo usuário. Correspondências não conclusivas (por exemplo, "Total de médicos únicos") aguardam confirmação e não autorizam deduções de unicidade. O exame automático `/api/inspect` fornece candidatos, perfis de colunas e uma matriz inicial; `/api/preflight` a recalcula após esclarecimentos. O endpoint `/api/analyze` **revalida** a habilitação antes da execução.

**Experimento sem LLM:** cartões clicáveis para solicitar análises diferem do canal conversacional normativo da SPEC. Ver `Docs/SEMANTIC_BRIDGE_ADAPTACOES.md` para rastreabilidade, divergências e limitações.

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
