# Ponte semântica e habilitação analítica — adaptação experimental

**Repositório:** Teste-Agente, independente do projeto principal.
**Fonte normativa de referência:** `IMPLEMENTATION_SPEC.md` v1.2.4 (não alterada).
**Módulo:** `backend/semantic_bridge.py`.

## Contratos reaproveitados

| Contrato SPEC | Correspondência nesta entrega |
| --- | --- |
| CFG-VOC §4.4.9, CFG-DOM §4.3 | Aliases PT/EN governados de cabeçalhos; categoria completa reconhecida pelo conjunto explícito de aliases da FTS; padrões compostos apenas propõem uma associação |
| RQ-DAD-05 e RQ-DAD-06 | Campo reconhecido (regra conclusiva ou perfil oficial) / escolhido pelo usuário / sugestão não escolhida / não associado; a escolha no seletor substitui a confirmação (divergência registrada, D1 de 19/10/2026); significados não são inventados |
| RQ-DAD-13 e RQ-DAD-15 | `/api/inspect` e `/api/preflight` fornecem perfil de estrutura e matriz de aplicabilidade, sem cálculos substantivos |
| RQ-DAD-28 e RQ-DAD-29 | Correspondência explícita dos nomes de coluna ao motor; cabeçalhos numéricos normalizados igualmente no exame e na análise |
| RQ-DAD-36 | Verificação condicional por operação, sem exigir território para quantificações e séries temporais da base inteira |
| RQ-DAD-25/26 | Coordenadas por cabeçalho e valores num formato decimal único; valor fora da faixa não rebaixa a coluna (o elemento é que fica inválido); separador decimal verificado nos dados; nenhum referencial geodésico presumido |

## Fluxo

1. O upload recebe CSV, XLSX ou XLS e devolve os nomes das colunas, estrutura, propostas e exame inicial.
2. A interface lista **cada coluna original uma única vez**, com seu papel candidato e estado.
3. Campos inequívocos dos aliases governados são pré-associados; nomes compostos como "Total de médicos únicos", o código territorial, UF e região são **sugestões**: ficam no topo do seletor (`suggested_columns` do `/api/inspect`), marcadas "(sugerida)", e o seletor fica vazio até a escolha. Nada é inferido sobre a unidade ou o âmbito da unicidade.
4. O usuário **escolhe** colunas e parâmetros; não há confirmação de campo (decisão D1 do responsável pelo produto, 19/10/2026). Escolher a coluna estabelece o papel (enviado em `confirmed_roles`, que significa "papéis escolhidos"). A unidade de contagem, o indicador, o período e o referencial são escolhas; o objeto de análise é o texto informado (`category_constant` sem coluna de categoria, `object_declaration` com ela). Denominador, comparabilidade temporal e entre territórios, identidade territorial (verificada nos dados), aditividade, soma dos componentes, identidade longitudinal e cobertura da coorte são **premissas** aplicadas pelo backend (`backend/analysis_premises.py`), registradas em `analysis_premises` e nas notas; um `false` explícito na API continua recusando a premissa.
5. O endpoint `/api/preflight` reavalia a estrutura e os significados, produzindo para cada análise `available`, `needs_confirmation` (valor do contrato para "escolha pendente") ou `unavailable` com razões legíveis. Cada requisito traz `kind` (`escolha` ou `dados`) e `step` (0: identificar os dados; 1: parâmetros); cada estado de campo traz `origin` (`PERFIL_GOVERNADO`, `REGRA_CONFIGURADA`, `ESCOLHA_DO_USUARIO` ou `SUGESTAO_NAO_ESCOLHIDA`).
6. Todos os cartões permanecem na tela, mas apenas `available` executa. `/api/analyze` **revalida a mesma matriz no servidor** antes do motor.
7. Os resultados são calculados apenas por solicitação explícita; a importação não calcula diagnósticos.

## Divergências arquiteturais explícitas

A seção 6.7 da SPEC (`RQ-FLX-14`) exige solicitação via conversação com LLM. A entrega inicial desta ponte usava cartões clicáveis como interface de solicitação. Os incrementos posteriores adicionaram interpretação conversacional, alternativas ancoradas e resolução territorial local, descritos em [Conversação incremental](CONVERSACAO_INCREMENTO_FN.md). A arquitetura conversacional normativa continua apenas parcialmente implementada; essa adaptação é local ao protótipo, não uma alteração retroativa da SPEC.

O estado de campo `recognized` é limitado ao **papel lexical/técnico da coluna**, não prova de todas as propriedades semânticas necessárias ao cálculo. A matriz pode pedir comprovações adicionais. A extração de termo de categoria de um cabeçalho composto é apenas sugestão: a interface a oferece num botão "Usar sugestão", nunca a aplica sozinha.

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
do protótipo. O código territorial permanece uma **sugestão**: o nome do campo e a repetição de
códigos não bastam (SPEC L1327); o seletor fica vazio, com o código no topo, até a escolha do usuário.
O par explícito `periodo_ano`/`periodo_mes` produz um campo AAAAMM derivado em memória
(ano × 100 + mês), **reconhecido por regra conclusiva** porque os componentes são validados na
importação (componente inválido recusa o arquivo); se a base já tiver outra coluna de período
reconhecida pelo nome, a composição fica como sugestão. A composição é rastreada nos metadados,
sem apagar colunas originais.
Latitude e longitude com nome do vocabulário são reconhecidas quando todos os valores preenchidos
são numéricos num formato decimal único (inteiros, só vírgula decimal ou só ponto decimal); valor
fora da faixa não rebaixa a coluna, e a evidência informa quantos elementos estão fora do intervalo.
O separador decimal das coordenadas é verificado nos dados (`semantic_bridge.verified_separator`):
vírgula quando as coordenadas a usam e quantidades e populações não têm vírgula; formato misto
continua uma escolha.
Não se presume equivalência entre totais nacionais e contagens municipais.
O catálogo escolhe uma fonte por recorte e reutiliza os contratos do upload.
Ver [integração e validação](DADOS_BRASIL_VALIDACAO.md).
