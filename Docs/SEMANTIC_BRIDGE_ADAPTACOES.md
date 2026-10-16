# Ponte semântica e habilitação analítica — adaptação experimental

**Repositório:** Teste-Agente, independente do projeto principal.
**Fonte normativa de referência:** `IMPLEMENTATION_SPEC.md` v1.2.4 (não alterada).
**Módulo:** `backend/semantic_bridge.py`.

## Contratos reaproveitados

| Contrato SPEC | Correspondência nesta entrega |
| --- | --- |
| CFG-VOC §4.4.9, CFG-DOM §4.3 | Aliases PT/EN governados de cabeçalhos; categoria completa reconhecida pelo conjunto explícito de aliases da FTS; padrões compostos apenas propõem uma associação |
| RQ-DAD-05 e RQ-DAD-06 | Campo reconhecido / proposto / confirmado / não associado; confirmação da função por atuação do usuário; significados não são inventados |
| RQ-DAD-13 e RQ-DAD-15 | `/api/inspect` e `/api/preflight` fornecem perfil de estrutura e matriz de aplicabilidade, sem cálculos substantivos |
| RQ-DAD-28 e RQ-DAD-29 | Correspondência explícita dos nomes de coluna ao motor; cabeçalhos numéricos normalizados igualmente no exame e na análise |
| RQ-DAD-36 | Verificação condicional por operação, sem exigir território para quantificações e séries temporais da base inteira |
| RQ-DAD-25/26 | Coordenadas por cabeçalho, tipo e faixa; nenhum referencial geodésico presumido |

## Fluxo

1. O upload recebe CSV, XLSX ou XLS e devolve os nomes das colunas, estrutura, propostas e exame inicial.
2. A interface lista **cada coluna original uma única vez**, com seu papel candidato e estado.
3. Campos inequívocos dos aliases governados são pré-associados; nomes compostos como "Total de médicos únicos" são candidatos **pendentes**, sem inferir a unidade ou o âmbito da unicidade.
4. O usuário confirma a associação ou declara o significado. A unidade de contagem, denominador, categoria constante, comparabilidade temporal e identidade longitudinal são confirmados **quando exigidos**.
5. O endpoint `/api/preflight` reavalia a estrutura e os significados, produzindo para cada análise `available`, `needs_confirmation` ou `unavailable` com razões legíveis.
6. Todos os cartões permanecem na tela, mas apenas `available` executa. `/api/analyze` **revalida a mesma matriz no servidor** antes do motor.
7. Os resultados são calculados apenas por solicitação explícita; a importação não calcula diagnósticos.

## Divergências arquiteturais explícitas

A seção 6.7 da SPEC (`RQ-FLX-14`) exige solicitação via conversação com LLM. A entrega inicial desta ponte usava cartões clicáveis como interface de solicitação. Os incrementos posteriores adicionaram interpretação conversacional, alternativas ancoradas e resolução territorial local, descritos em [Conversação incremental](CONVERSACAO_INCREMENTO_FN.md). A arquitetura conversacional normativa continua apenas parcialmente implementada; essa adaptação é local ao protótipo, não uma alteração retroativa da SPEC.

O estado de campo `recognized` é limitado ao **papel lexical/técnico da coluna**, não prova de todas as propriedades semânticas necessárias ao cálculo. A matriz pode pedir comprovações adicionais. A extração de termo de categoria de um cabeçalho composto é apenas sugestão até confirmação contextual.

## Limitações conscientes

- A ponte é uma implementação **parcial** dos contratos; não substitui CFG-VOC/CFG-DOM completos e versionados do sistema principal, nem todo o conjunto de requisitos da SPEC.
- Não há ingestão de várias bases simultâneas, tabelas largas com múltiplas medidas em colunas, metadados auxiliares, tratamento completo de individualização/privacidade ou linhagem persistente.
- O reconhecimento automático se limita a correspondência governada; padrões compostos são somente candidatos. Nenhuma similaridade estatística estabelece pertença à FTS.
- A verificação habilitadora é **potencial**: regras adicionais do motor analítico podem rejeitar a operação; esses motivos permanecem explícitos. É proibido inventar valores faltantes.
- Em bases sem território, `counts`, `temporal` e relatório de quantitativos podem operar sobre o conjunto **sem declarar esse conjunto como território**. Análises territoriais continuam exigindo geografia.
- Todo recálculo da matriz lê o arquivo enviado no próprio `localhost`; o protótipo não persiste os uploads. Ainda não adequado para produção, grandes arquivos ou dados individuais sensíveis.
- Formatos de competência/tempo devem ter posição temporal numérica inequívoca; séries temporais em formatos não suportados permanecem desabilitadas nesta versão.

## Validação

Os testes de API e motor ficam em `backend/tests/test_semantic_bridge.py` e `test_upload_api.py`. A build TypeScript/Vite roda no CI.

## Extensões para a base Brasil

Os aliases `pais`/`country` e `cod_ibge`/`codigo_ibge` são complementos operacionais
do protótipo. O código territorial permanece uma proposta que exige confirmação.
O par explícito `periodo_ano`/`periodo_mes` produz um campo AAAAMM derivado em memória,
proposto para confirmação e rastreado nos metadados, sem apagar colunas originais.
Não se presume equivalência entre totais nacionais e contagens municipais.
O catálogo escolhe uma fonte por recorte e reutiliza os contratos do upload.
Ver [integração e validação](DADOS_BRASIL_VALIDACAO.md).
