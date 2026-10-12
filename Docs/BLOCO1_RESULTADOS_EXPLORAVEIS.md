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

Agregação continua exigindo fundamento para população e uma modalidade explícita
de contagem. A soma de componentes admite dupla contagem e não é rotulada como
pessoas distintas. A evolução mantém cada competência separada.

## Linha de base

- Python: 205 aprovados, incluindo fontes brasileiras reais; um aviso de depreciação.
- TypeScript/Vite: aprovado; aviso preexistente de tamanho do bundle.
- O primeiro pytest encontrou permissões na pasta temporária global. Reexecutado
  com `--basetemp=.local/pytest-baseline-bloco1`, sem falhas de produto.
- O smoke conversacional com catálogo real chegou ao cálculo nacional, mas esperava
  duas competências da fixture sintética e recebeu 22 reais. Essa premissa será
  validada com a fixture correta; não é contabilizada como aprovação.
