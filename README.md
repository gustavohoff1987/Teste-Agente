# Teste Agente — Portal Experimental

Experimento isolado de desenvolvimento para o **Agente Diagnóstico Territorial da Força de Trabalho na Saúde**.

- **Interface:** React + TypeScript + Tailwind; uma única página responsiva, com cartões clicáveis, upload, mapeamento de colunas, filtros, gráficos, tabelas e exportação CSV / impressão em PDF.
- **Motor:** Python + FastAPI, operações determinísticas sem LLM.
- **Documento de referência:** IMPLEMENTATION_SPEC.md v1.2.4, **apenas para os contratos metodológicos e semânticos**. A interface e a arquitetura física são novas, independentes das diretrizes de UX daquele projeto.
- **Não há chamada Gemini** nesta versão. Uma integração posterior pode ser feita sem transferir cálculos para o modelo.

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

## Escopo e limitações desta primeira entrega

Os dez cartões apresentam a navegação e acionam rotas do motor. A versão implementa percursos iniciais para densidade, quantitativos, distribuição por quantis, comparação, mudança temporal, agregação, distância geodésica, ordenação, coortes e tabelas/relatório básico.

**Não declara conformidade integral com a SPEC.** Ainda são necessários, entre outros: suporte a várias bases e planilhas auxiliares simultâneas; normalização completa de tabelas largas e dados individualizados; catálogo de significados e vocabulário governado; todos os tratamentos de ambiguidade e estados de autorização; seleção territorial avançada; regras de comparabilidade longitudinal; todas as subclasses de tendência; referências e faixas espaciais; PDF gerado diretamente por servidor; cobertura exaustiva dos cenários de aceite; escala de grandes bases. Os cartões de comparação, tendência e rotatividade produzem resultados preliminares que exigem significados semânticos autorizados antes de uso substantivo.

Uploads são processados em memória por requisição e não são persistidos pelo aplicativo. O arquivo é reenviado a cada análise; o limite experimental é de 30 MB. Evite bases pessoais e sensíveis no protótipo. Para arquivos muito grandes, será preciso processamento incremental/local, sessão segura e proteção de dados aprofundada.

Amostras da interface são exemplos ilustrativos, **não diagnósticos reais**. Métodos não podem inventar limiares normativos nem presumir unicidade dos profissionais no agregado.
