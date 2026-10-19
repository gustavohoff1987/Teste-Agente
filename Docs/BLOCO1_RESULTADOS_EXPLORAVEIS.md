# Bloco 1 — resultados exploráveis e seleção territorial

Origem: `feat/portal-uma-pagina-v1`, commit `d214ab73a52e7cd33f1fc3e8488b216d83a19571`.
Implementação exclusivamente em `feat/novos-blocos-incrementais`.

## Inspeção e reaproveitamento

A SPEC foi lida integralmente. Aplicam-se os contratos metodológicos e semânticos
delimitados pelo README; não se replica a arquitetura integral do projeto original.
Reutilizamos `AnalysisAssistant`, `ConversationalPreparation`, os controles de
competência, `DistributionResults`, exportações e o motor `compute`/`preflight`.
Os resultados já estavam dentro da conversa; a lacuna era o estado único substituível.
As fontes Brasil continuam separadas na mesma sessão lógica, com seus perfis governados.

O desenvolvimento acrescenta seleção estruturada antes dos cálculos, metadados de
universo, histórico em memória da sessão e comandos locais limitados a essas jornadas.
Nenhum armazenamento permanente de dados do usuário, cache de bases ou infraestrutura
dos Blocos 2 e 3 é introduzido.

## Contrato territorial

`options.territory_ids` omitido mantém o comportamento anterior. Presente, exige
lista não vazia e distinta de identificadores devolvidos em `territory_choices`.
`code:` preserva o código opaco original; `name:` é aceito somente sem ambiguidade
observada. Não existe dependência de IBGE para uploads. A seleção é aplicada pelo
Python antes de contagens, denominadores, distribuições, comparações e agregações.
Membros sem registros no recorte são bloqueados com motivo, nunca eliminados em silêncio.
Ausências temporais nos extremos mantêm a mudança não avaliável.

A inspeção dos arquivos locais confirmou `uf` e `regiao_geografica`, além de
`municipio` e `cod_ibge`. Uma unidade (`251365`) possui hierarquias divergentes na
fonte e permanece impedida para seleção até esclarecimento; as outras unidades
não são bloqueadas por esse conflito externo ao seu recorte.
A regra `brasil-cod-uf-prefix-1` deriva
somente o estado pelos dois primeiros dígitos, para o perfil governado municipal,
sem completar códigos de seis dígitos ou inventar limites territoriais. Referência:
[Tabela de códigos de municípios do IBGE](https://www.ibge.gov.br/explica/codigos-dos-municipios.php).
Essa regra não se aplica a uploads nem autoriza aditividade, identidade longitudinal
ou ausência de sobreposição de profissionais.

Agregação continua exigindo fundamento para população e uma modalidade de contagem. Na
base oficial, ambos são premissas internas do perfil governado (populações municipais
disjuntas e soma dos componentes); em uploads, são premissas da análise aplicadas pelo backend, com
nota e limitação, sem declarações (decisão D1, 19/10/2026). A soma de
componentes admite dupla contagem e não é rotulada como pessoas distintas. A evolução
mantém cada competência separada.

## Linha de base

- Python: 205 aprovados, incluindo fontes brasileiras reais; um aviso de depreciação.
- TypeScript/Vite: aprovado; aviso preexistente de tamanho do bundle.
- O primeiro pytest encontrou permissões na pasta temporária global. Reexecutado
  com `--basetemp=.local/pytest-baseline-bloco1`, sem falhas de produto.
- O smoke conversacional com catálogo real chegou ao cálculo nacional, mas esperava
  duas competências da fixture sintética e recebeu 22 reais. Essa premissa será
  validada com a fixture correta; não é contabilizada como aprovação.

## Validação final (12/10/2026)

Branch `feat/novos-blocos-incrementais`; commit inicial da validação `13aec9e`.
Comparação com `feat/portal-uma-pagina-v1` (`d214ab7`): somente os dois commits do
Bloco 1 (`f714637`, `13aec9e`). Ambiente: contêiner Linux, Python 3.11, pandas 2.3.3,
Node 22; navegador Chromium 141 via Playwright 1.56 (no CI, Chrome via Playwright).

### Dados reais

Os arquivos brasileiros reais **não estavam disponíveis** no ambiente de validação
(sem `.local/datasets/brasil`, `ADT_REAL_DATA_DIR` ou `ADT_BRASIL_DATA_DIR`). Toda a
validação abaixo usa fixtures sintéticas. A conclusão é técnica; a validação empírica
com os dados reais permanece pendente (ver Pendências).

### Testes executados

| Verificação | Resultado |
|---|---|
| `pytest` (backend) | 204 aprovados; 20 ignorados (`test_real_data.py`, exigem `ADT_REAL_DATA_DIR`; não contam como aprovação) |
| `npm run build` (TypeScript + Vite) | aprovado; aviso preexistente de tamanho do bundle |
| `ui_block1_smoke.py` (jornada ampliada) | aprovado |
| `ui_block1_regression.py` | aprovado |
| `ui_block1_integration.py` (transporte Gemini simulado) | falhou na versão recebida (defeito do teste); aprovado após correção |
| `ui_conversational_smoke.py` (fixture de duas fontes) | aprovado |
| `ui_session`, `ui_carousel`, `ui_audit`, `ui_preparation`, `ui_integration_smoke.py` | falham igualmente em `d214ab7` (roteiros desatualizados antes do Bloco 1); não são regressões |
| `ui_brazil_smoke.py`, `ui_smoke.py`, `ADT_BLOCK1_REAL=1` | não executados: exigem os dados reais |
| CI após as correções (`f78f67a`, `e749831`) | 4/4 jobs aprovados; em `e749831` o ui-block1 já executa jornada, regressão e integração simulada |

O CI passa a executar no job `ui-block1` a jornada, a regressão e a integração com
Gemini simulado (processo próprio que bloqueia rede externa; sem chave nem custo).

### Jornada validada (catálogo sintético)

1. Dados do Brasil; 2. "Mostre a densidade médica dos municípios do Amazonas em junho
de 2024."; 3. resultado na conversa, com densidade = quantidade / população × 1.000;
4. seleção de Manaus, Tefé e Parintins por código; 5. comparação com os mesmos valores
da densidade inicial; 6. evolução com competências separadas, extremos e variação
conferidos contra a série; 7. resultados anteriores reabertos sem alteração (CSV e JSON
reexportados iguais à resposta do motor); 8. retomada dos parâmetros da comparação,
reaproveitada sem nova chamada a `/api/analyze`; 9. agregação de uma competência,
rotulada como soma dos componentes com possível dupla contagem, com a aditividade
populacional como premissa interna do perfil oficial; 10. exportações CSV e "Método e parâmetros". Também foram
verificados reutilização de membros de um resultado, teclado e larguras de 390 e 768 px.
As capturas de cada etapa foram revisadas visualmente.

### Falhas encontradas e correções

| Falha comprovada | Correção |
|---|---|
| `ui_block1_integration.py` esperava 422; o contrato do backend (cenário A12) é 502 para resposta do modelo fora do contrato | teste corrigido (`ad649c9`) |
| Catálogo territorial recalculado 20–30 vezes por requisição; 0,73 s por chamada em escala nacional | valores distintos antes da normalização, níveis lidos dos nomes das colunas, sem `iterrows`: 0,13 s, mesma saída em 14 cenários (`2bd6e20`) |
| "Municípios do Paraná" virava o município Paraná (RN); idem Tocantins (MG), Mato Grosso (PB), São Paulo | nome idêntico de estado e município pede esclarecimento; maior expressão prevalece ("Rio Grande do Sul", "Mato Grosso do Sul") (`d613df8`) |
| Remover a associação do nome/código territorial mantinha IDs inexistentes; todo pré-exame era recusado (422) sem mensagem | seleção limpa ao remover ou mover a identidade territorial (`f78f67a`) |
| Busca da seleção com ~75 px em 390 px; metadados e série temporal roláveis sem teclado; contraste 4,37:1 no histórico | ajustes localizados de layout e acessibilidade (`c38e01e`) |

A jornada de teste também foi ampliada (`67d75f7`): a antiga verificação de
imutabilidade comparava um dicionário Python consigo mesmo.

### Desempenho (catálogo sintético de 5.570 municípios × 22 competências)

| Requisição | `d214ab7` | `13aec9e` | após correção |
|---|---|---|---|
| preflight sem seleção | 1,53 s | 2,45 s | 2,22 s |
| preflight com seleção (209) | — | 3,49 s | 2,47 s |
| densidade sem seleção | 2,13 s | 3,85 s | 3,31 s |
| densidade com seleção (209) | — | 6,66 s | 3,46 s |
| comparação (3) | — | 7,14 s | 3,62 s |
| evolução (3) | — | 6,21 s | 3,69 s |

Na interface, marcar um membro entre 5.570 leva 76–127 ms até o quadro seguinte.

### Pendências

- Validação empírica com os dados reais: `ADT_REAL_DATA_DIR=<pasta> pytest`;
  `ADT_BLOCK1_REAL=1 python backend/tests/ui_block1_smoke.py` com o catálogo real
  instalado (62 municípios, 22 competências); `ui_brazil_smoke.py` e `ui_smoke.py`.
  Conferir também a unidade `251365` com hierarquia divergente.
- O contrato da interpretação Gemini ainda aceita comparações só por densidade; a
  comparação por quantidade do Bloco 1 depende da gramática local ou dos controles.
  Alterar esse contrato é decisão de governança de LLM, não tomada aqui.
- Cor de destaque global (`#0c8792`) com contraste 4,28:1 em texto de 12 px, e a
  "Tabela detalhada" rolável sem foco: preexistentes, fora do escopo do Bloco 1.
- Em escala nacional, cada pré-exame devolve ~1,1 MiB de opções territoriais e cada
  resultado do universo observado ~1,9 MiB de metadados; aceitável no protótipo, a
  reavaliar antes de operação online.
- O histórico rotula todo resultado não vigente como "histórico"; a SPEC (RQ-LIN-20c)
  distingue deslocamento de foco de substituição de estado.
- Roteiros de navegador anteriores ao redesenho conversacional precisam ser atualizados.

### Conclusão

**CONCLUÍDO COM RESSALVAS.** As jornadas obrigatórias funcionam com dados sintéticos,
sem falhas impeditivas conhecidas e com CI aprovado. A ressalva principal é a
validação empírica com os dados brasileiros reais, ainda não executada.

### Atualização de 15/10/2026

- **Dados reais:** a validação empírica pendente acima passou a rodar em todo push, com a base
  Brasil versionada na raiz do repositório:
  - job `dados-reais`: integridade pelo manifesto e os 31 testes reais;
  - suíte `base-versionada` do job `ui-block1`: esta jornada com `ADT_BLOCK1_REAL=1`, ou seja,
    62 municípios do AM e 22 competências.

  Na execução local de 15/10/2026, os 29 testes reais passaram em cerca de 7,5 min e a jornada real
  passou em 79 s. A unidade `251365`, com hierarquia divergente, continua sem verificação dedicada.
- **Histórico de resultados:** o commit `dbaa0bd` retirou da interface a lista de resultados e o
  controle de invalidação. Com isso, o passo 7 da jornada validada ("resultados anteriores
  reabertos") e a ressalva sobre o rótulo "histórico" deixaram de se aplicar. A jornada atual confere
  o resultado vigente, a retomada e o reaproveitamento. Ver
  [`REGISTRO_DE_COMPORTAMENTO.md`](REGISTRO_DE_COMPORTAMENTO.md).
- **Roteiros anteriores ao redesenho:** `ui_brazil_smoke.py`, `ui_smoke.py` e os demais foram
  movidos para `backend/tests/legado/`. O README de lá traz o mapa do que cobriam e das lacunas.

### Atualização de interface — 15/10/2026: análises anteriores

O histórico interno continua temporário, sem login ou armazenamento permanente. Foi restituído ao
usuário um acesso discreto **“Histórico de análises”**, recolhido por padrão e sempre acessível no
topo do painel de análise, inclusive antes do primeiro cálculo. A lista apresenta os resultados do mais recente ao mais antigo,
destaca aquele que está aberto e permite reabrir os demais sem recalcular.

Reabrir um resultado não restaura silenciosamente suas opções de análise. A ação distinta
`Retomar parâmetros deste resultado` continua explícita e condicionada à compatibilidade da
fonte e da camada geográfica. Não foi restaurado o controle de invalidação. O teste
`ui_block1_smoke.py` confere a navegação sem novas chamadas de análise tanto com dados sintéticos
quanto com a base Brasil versionada (62 municípios do Amazonas).


## Ajustes de exploração dos resultados (15/10/2026)

A solicitação e a ação “Retomar parâmetros deste resultado” continuam acessíveis, sem o antigo painel com JSON. Os metadados completos são baixados em “Método e parâmetros”. O checklist “Selecionar territórios deste resultado” foi substituído pela seleção nas linhas da tabela, sincronizada com mapa e barras; “Usar seleção na próxima análise” aplica explicitamente os IDs à preparação, sem executar. A retomada permanece coberta por `ui_block1_smoke.py`, `ui_block1_regression.py`, `ui_nearest_smoke.py` e `ui_criteria_smoke.py`; a reutilização pela tabela é coberta por `ui_block1_smoke.py` e `ui_map_smoke.py`.

As tabelas principais e as competências da série usam filtros por coluna, ordenação visual e páginas de 150 registros. O CSV superior preserva o resultado integral; o CSV da tabela acompanha todo o filtro. As barras extensas e as séries paginadas são descritas em [Bloco 3](BLOCO3_MAPAS_VISUALIZACOES.md). O painel recolhido “Histórico de análises” continua disponível na sessão; os textos técnicos removidos anteriormente e o controle de invalidação não reaparecem.

## Continuidade da conversa e painéis (16/10/2026)

A interface usa um único fluxo horizontal para agente, seleção, preparação e resultados. O campo de mensagem acompanha a resposta recente, e o histórico conversacional pode ser expandido. A barra sob o banner contém Início, Nova sessão, Nova análise, Histórico e Resultados; adapta-se em telas estreitas. Consultar um resultado anterior não executa cálculos nem restaura parâmetros silenciosamente. Veja [Interface integrada](INTERFACE_CONVERSACIONAL_INTEGRADA.md).

Pedidos comparativos com nomes explícitos preparam diretamente o conjunto mencionado; falta de outro município gera pergunta específica. A resposta seguinte completa a seleção pendente da mesma fonte. Alternativas semânticas materialmente diferentes exigem escolha, conforme [conversação incremental](CONVERSACAO_INCREMENTO_FN.md). A jornada `ui_semantic_continuity.py`, registrada em `run_ui_checks.py`, verifica esses fluxos com provedor simulado, ausência de cálculo implícito, histórico desde o primeiro resultado e compositor visível em 1.280, 768 e 390 px.
