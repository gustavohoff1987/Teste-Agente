# IMPLEMENTATION SPECIFICATION v1.2.4 — especificação consolidada
## Agente de Diagnóstico Territorial da Força de Trabalho na Saúde

| Campo | Valor |
|---|---|
| Documento-base | CONCEPT.md — "Estrutura Teórico-Conceitual do Agente de Diagnóstico Territorial da Força de Trabalho na Saúde" (Capítulos 1 a 14) |
| Versão | 1.2.4 |
| Data | 2026-10-02 |
| Versão anterior | 1.2.2 — baseline normativa da reconstrução (commit 8fd33a67a3e23fe9d42623f11334b2cf9aef7e79). A v1.2.3 (commit 8ac444f12c53bda6b6fe1f243c41c292c906ca40) foi usada como referência de controle, não como baseline de edição (§25.9) |
| Natureza | Reconstrução compacta sobre a v1.2.2, com D13–D28, D17-A, H1–H3 e D29–D42; a massa literal PT/EN das formas documentais governadas foi externalizada para Docs/CFG_DOC_CATALOG.yaml, sem alteração da autoridade normativa |
| Decisões incorporadas | DA-01 a DA-28 e tratamentos P-01 a P-23 (DECISOES_DA_01_A_07.md, DECISOES_DA_08_A_14.md, DECISOES_DA_15_A_21.md, DECISOES_DA_22_A_28.md, DECISOES_P_01_A_23.md), com os complementos aprovados na revisão anterior à v1.1 e as correções AV-01 a AV-10 registradas na seção 24.6; decisões técnicas F-01 a F-12 (DECISOES_F01_A_F12_FINAL.md), com F-09 registrada como não incorporada; Configuração Inicial de Implementação, com os 24 itens CFG e a capacidade CAP-ROT-01 (CONFIGURACAO_INICIAL_IMPLEMENTACAO_FINAL.md), registradas na Parte 25; D1–D12, ajustes de estado agregado e preservação histórica e precisão D8/TPL-12, exclusivamente na rodada de §25.8; D13–D28, D17-A (decisão humana aprovada), H1–H3 e D29–D42 na rodada de §25.9 |
| Situação | Candidata v1.2.4 — situação de fechamento e blockers registrados em §25.9 |
| Preservação | CONCEPT inalterado; nenhuma expansão de domínio, capacidade, família, formato de arquivo ou escolha tecnológica; tipos, enumerações, eventos, aliases e formas acrescentados limitam-se aos exigidos pelas decisões aprovadas (§25.9) |
| Artefato associado | Docs/CFG_DOC_CATALOG.yaml — catálogo literal PT/EN de CFG-DOC, versionado com esta SPEC (seção 4.4.23.6) |

### Sumário

- Parte 0 — Controle do documento e convenções
- Parte 1 — Finalidade, domínio, escopo e fronteiras de autoridade
- Parte 2 — Arquitetura lógica e componentes
- Parte 3 — Modelo de informação
- Parte 4 — Configuração governada
- Parte 5 — Dados, metadados, universo, triagem e exame habilitador
- Parte 6 — Ciclo de vida da sessão e da solicitação
- Parte 7 — Governança: gates, âncoras, autoridade, ambiguidade e autorização
- Parte 8 — Capacidades: contratos e catálogo v1.2.4
- Parte 9 — Orquestração e composição
- Parte 10 — Resultados analíticos estruturados
- Parte 11 — Linhas analíticas, estado, validade e vigência
- Parte 12 — Diagnóstico
- Parte 13 — Representação e entrega
- Parte 14 — Síntese e validação de saída
- Parte 15 — Incerteza, desfechos e respostas
- Parte 16 — Indisponibilidade e modo degradado
- Parte 17 — Rastreabilidade
- Parte 18 — Registros individualizados
- Parte 19 — Evolução controlada
- Parte 20 — Qualidade, validação e critérios de aceite
- Parte 21 — Matriz de rastreabilidade Concept → SPEC
- Parte 22 — Registro das decisões incorporadas
- Parte 23 — Tratamento dos pontos P-01 a P-23
- Parte 24 — Registro da revisão de consistência (v1.1)
- Parte 25 — Registro da incorporação F-01 a F-12 e da Configuração Inicial de Implementação (v1.2), com remediação e controle de regressão v1.2.1; remediação documental consolidada v1.2.2 em §25.8 e reconstrução compacta v1.2.4 em §25.9
- Anexo A — Mapa normativo de extração de CFG-DOC

---

## Parte 0 — Controle do documento e convenções

### 0.1. Objeto

Esta especificação converte o Concept em comportamento técnico verificável: componentes, contratos, estados, regras, entradas, saídas, pré-condições, exceções, limites, rastreabilidade e critérios de aceite. A versão 1.1 incorpora as decisões que resolveram as decisões em aberto e os pontos não inequívocos da versão 1.0 (Partes 22 e 23). Incorpora também as correções comportamentais aprovadas AV-01 a AV-10 (seção 24.6), preservando a versão 1.1, para revisão. Essas correções precisaram contratos e harmonizaram regras existentes; não acrescentam finalidades, famílias, exclusões ou autoridade factual ao LLM. A versão 1.2 incorpora as decisões técnicas F-01 a F-12 — F-09 registrada como não incorporada — e a Configuração Inicial de Implementação, que fixa o conteúdo dos 24 itens CFG e acrescenta a capacidade CAP-ROT-01 à família FAM-08 (Parte 25). A versão 1.2.1 executa exclusivamente as cinco remediações autorizadas e o controle de regressão da v1.2, sem alterar o Concept ou expandir o escopo; o registro está nas seções 25.5 a 25.7. Esta especificação define o que o sistema faz, como se comporta, quais regras, capacidades, configurações, pré-condições e resultados são válidos e quais decisões permanecem com o usuário; não escolhe linguagem, bibliotecas, frameworks, banco de dados, estrutura física de módulos ou ferramentas, que pertencem ao plano técnico de implementação (RQ-DOC-06). A versão 1.2.2 aplica D1–D12, os ajustes de execução das partes e preservação histórica e a precisão D8/TPL-12 em uma única rodada (§25.8), sem expansão de escopo ou alteração do Concept. A versão 1.2.4 é reconstruída sobre a v1.2.2: incorpora D13–D28, D17-A e H1–H3, materializadas originalmente na v1.2.3, usada apenas como referência de controle, e D29–D42; transfere a massa literal das formas documentais PT/EN para Docs/CFG_DOC_CATALOG.yaml (seção 4.4.23.6), mantendo o CONCEPT, a autoridade normativa da SPEC e as decisões anteriores no mérito (§25.9).

### 0.2. Precedência e integridade

- **RQ-DOC-01** — Em caso de conflito entre esta SPEC e o Concept, prevalece o Concept. O conflito DEVE ser registrado como defeito desta SPEC e corrigido em nova versão. [INSP]
- **RQ-DOC-02** — Nenhum requisito desta SPEC PODE ser lido como autorização de funcionalidade, capacidade, fonte ou autonomia não prevista no Concept ou nas decisões e na configuração registradas nas Partes 22 e 25. [INSP]
- **RQ-DOC-03** — O fechamento vigente da v1.2.4 é registrado em §25.9, sobre a baseline v1.2.2, commit 8fd33a67a3e23fe9d42623f11334b2cf9aef7e79; a v1.2.3, commit 8ac444f12c53bda6b6fe1f243c41c292c906ca40, é referência de controle, não baseline nem dependência de runtime. DA, P, AV, F e §§25.5–25.8 preservam integralmente seus corpos históricos, datas, contagens e conclusões; D1–D12 e D8/TPL-12 pertencem a §25.8. D13–D28, D17-A, H1–H3 e D29–D42 pertencem à rodada de §25.9; D17-A é decisão humana aprovada, com retirada total sem cancelamento produzindo ENCERRADA_SEM_RESULTADO. D13 mantém as quatro classes e a linguagem funcional não nominal, sob a regra de evidência positiva de D29. CFG-DOC exige catálogo literal PT/EN externo, versionado com esta SPEC, e Anexo A regenerado/reproduzível. Integridade do CONCEPT usa conteúdo Git e blob 84b6138743300ad0df4908471460c7c3bdc19d3d, UTF-8 sem BOM e LF; arquivo local CRLF é comparado normalizando exclusivamente CRLF→LF em memória, sem editar o arquivo. SHA-256 só é registrado com origem, representação e normalização; diferenças exclusivas LF/CRLF não são substantivas. Prontidão documental não declara testes de software ou aprovação comportamental. [INSP]
- **RQ-DOC-04** — Alteração de decisão incorporada é alteração governada, realizada no processo externo de desenvolvimento, e DEVE seguir a Parte 19. [INSP]
- **RQ-DOC-05** — Referências no formato [C §x.y] remetem a seções do Concept; "Caso n" remete à seção 14.(n+1) do Concept. [INSP]
- **RQ-DOC-06** — "Configuração Inicial de Implementação" designa o conteúdo governado de configuração com que o sistema é implementado e liberado nesta versão (seção 4.4) com o significado estabelecido nas decisões de configuração incorporadas. Escolhas tecnológicas do plano técnico de implementação (linguagem, bibliotecas, frameworks, armazenamento, estrutura física de módulos, ferramentas e implementação de algoritmos definidos em CFG-MET) NÃO DEVEM alterar comportamento, regra, método, estado, resultado ou fronteira de autoridade definidos nesta SPEC. [INSP]

### 0.3. Termos normativos

DEVE e NÃO DEVE indicam obrigação e proibição. PODE indica permissão sem obrigação. Não são usados termos de recomendação sem força normativa; todo requisito é verificável por uma das formas da seção 0.5.

### 0.4. Identificadores

| Prefixo | Significado | Parte |
|---|---|---|
| RQ-xxx-nn | Requisito normativo (DOC, ESC, ARQ, MOD, CFG, DAD, FLX, GOV, CAP, ORQ, RES, LIN, DIA, REP, SIN, INC, DEG, RAS, PRV, EVO, QUA) | todas |
| INV-nn | Invariante global | 1 |
| FAM-nn | Família autorizada de ação analítica | 1 |
| EXC-nn | Exclusão do escopo atual | 1 |
| C-nn | Componente lógico | 2 |
| CFG-xxx | Item de configuração governada | 4 |
| AMB-nn | Gatilho de ambiguidade | 7 |
| CAP-xxx-nn | Capacidade acionável | 8 |
| FN-xxx-nn | Função baseada em LLM | 8 |
| V-nn | Regra do validador de saída | 14 |
| EV-xxx | Tipo de evento de rastreabilidade | 17 |
| AT-nn | Cenário de aceite | 20 |
| M-nn | Métrica de qualidade | 20 |
| DA-nn | Decisão incorporada (registro de origem) | 22 |
| P-nn | Ponto do Concept e seu tratamento | 23 |
| AV-nn | Correção aprovada na revisão adversarial comportamental | 24.6 |
| F-nn | Decisão técnica incorporada (registro de origem F-01 a F-12) | 25 |
| TPL-nn | Modelo de mensagem do canal sistêmico (CFG-TPL) | 4.4.16 |
| LEX-xxx | Grupo lexical do validador (CFG-LEX) | 4.4.15 |
| `DOC:<fonte_normativa>[.<caminho>]` | Âncora documental de proposição normativa (CFG-DOC) | 4.4.23 |
| ROT-AT-nn | Teste mínimo de aceite de CAP-ROT-01 | 20.7 |

### 0.5. Formas de verificação

| Tag | Forma |
|---|---|
| [T-DET] | Teste automatizado determinístico de componente sem LLM (motor, estado, repositório, validadores) |
| [T-GOV] | Teste automatizado dos gates e validadores com saídas do LLM simuladas, inclusive adversariais |
| [T-LLM] | Avaliação de função baseada em LLM contra corpus representativo, acompanhada por métrica M-nn |
| [T-E2E] | Cenário ponta a ponta (AT-nn) |
| [INSP] | Inspeção documental, de configuração ou de código |

### 0.6. Notação de esquemas

Os esquemas são lógicos e independentes de tecnologia. Notação: `campo: Tipo — descrição`. Tipos: `Id`, `Texto`, `Inteiro`, `Decimal` (valor numérico em precisão integral), `Booleano`, `Timestamp` (UTC), `Hash` (resumo criptográfico do conteúdo canônico), `Enum<...>`, `Lista<...>`, `Ref<Entidade>`, `Opcional<...>`.

### 0.7. Glossário complementar

Os termos definidos em [C §13.3] mantêm aquelas definições. Os termos abaixo são introduzidos por esta SPEC.

| Termo | Definição |
|---|---|
| Componente | Unidade lógica C-nn com responsabilidades e permissões definidas na Parte 2. Não se confunde com "componente diagnóstico" [C §13.3]. |
| Gate | Ponto de decisão determinístico da governança (pertinência, admissibilidade, disponibilidade, pré-execução, autorização, validação de saída). |
| Registro de interpretação | Saída estruturada de uma função FN-*, registrada com natureza INTERPRETACAO_LLM. Nunca é fonte analítica. |
| Leitura semântica mínima | Registro de FN-INT-01 que distingue funções coexistentes da mensagem, identifica introdução deliberada de dados e contém apenas o necessário ao encaminhamento e à avaliação preliminar de pertinência e admissibilidade [C §5.2]. |
| Interpretação operacional | Registro produzido por FN-INT-02, ou atualizado deterministicamente por resposta estruturada, que organiza entregáveis, objetos, parâmetros, modo e linha. Depois de validada, é a referência de fidelidade da execução [C §9.4]. |
| Entregável | Unidade de resposta semanticamente distinta solicitada pelo usuário ou decorrente de ampliação explicitamente aceita, identificada e validada na interpretação operacional (valor, conjunto, relação, classificação, representação). Pode conter múltiplos elementos, unidades, relações e etapas. A enumeração de unidades e a decomposição técnica não criam entregáveis autônomos; sua autonomia decorre da intenção e da estrutura semântica validadas. Base da separabilidade, do atendimento e do papel diagnóstico (RQ-GOV-28, RQ-RES-04). Objetivo terminal governa a autonomia; intermediário contido não cria outro entregável. Retirada é ocorrência em escopo versionado e preserva estado histórico (RQ-FLX-02). Entregável composto registra ResultadoElemento por unidade semântica independente (RQ-RES-04); cancelamento explícito da solicitação leva entregáveis vigentes não terminais a CANCELADO, distinto da retirada (RQ-FLX-02). |
| Plano de composição | Grafo acíclico dirigido de etapas que produz os entregáveis. |
| Etapa | Acionamento de uma capacidade com parâmetros, entradas e papel definidos. |
| Assinatura material | Resumo dos elementos de uma leitura cuja diferença altera de forma relevante o resultado (seção 7.5). |
| Chave de execução | Resumo canônico das condições de uma etapa que determina a possibilidade de reuso (seção 9.3). |
| Autorização | Registro de C-04: ANALITICA habilita etapas de um plano sob um contexto de consistência; HABILITADORA restringe-se à introdução deliberada de dados e ao exame, conforme RQ-DAD-34. |
| Verificação pré-execução | Lista determinística de 12 verificações aplicada a cada etapa (seção 7.7). |
| Snapshot de configuração | Conjunto identificado das versões dos itens CFG, fixado no início da sessão e referenciado por contextos, resultados e eventos. |
| Sessão | Interação temporária e isolada de um usuário, sem login, com snapshot fixo; bases, linhas e resultados não persistem após o encerramento (DA-24, DA-25). Encerra por controle explícito ou 1800 segundos sem EV-INTERACAO_USUARIO válido do catálogo fechado de CFG-OPR; fechamento de interface não encerra imediatamente. Descarte integral e concorrência seguem RQ-FLX-17. |
| Idioma da sessão | Português ou inglês, determinado conforme RQ-FLX-18. |
| Avaliabilidade | Condição de cada elemento do universo para uma capacidade: AVALIAVEL, NAO_AVALIAVEL ou FORA_DO_UNIVERSO. |
| Pendência | Esclarecimento ou decisão aguardada do usuário, vinculada à solicitação e à linha quando legitimamente existente, quando analítica, ou à entrada ou base, quando habilitadora [C §7.8] (RQ-DAD-42, F-08). Pode ter escopo OBJETO antes de linha legítima; retirada remove apenas consumidores afetados, tornando SEM_APLICABILIDADE a pendência exclusiva sem consumidores. Antes da criação de entregáveis, vincula-se à solicitação, à entrada ou à base, sem exigir entregável vigente, e segue a fila determinística de RQ-FLX-01. |
| Conjunto de opções autorizadas | Lista fechada de alternativas proveniente de uma das origens admitidas por CFG-OPC (seção 4.4.11): enumeração fechada, contrato de capacidade, leituras concorrentes de CFG-AMB, interpretações materialmente concorrentes identificadas e ancoradas ou opções operacionais estruturadas; única origem admissível de alternativas em perguntas [C §9.5]. Materializado como ConjuntoOpcoesAutorizadas de OpcaoAutorizada, cada uma com id estável, valor estruturado e rótulos PT/EN governados (seção 4.4.11). |
| Evento | Registro imutável e encadeado no repositório de rastreabilidade (C-13), mantido durante a sessão. |
| Canal sistêmico | Mecanismo de comunicação independente do LLM (C-02) [C §9.11]. |
| Controle estruturado de interface | Ação de interface para upload, navegação, filtro, seleção, visualização, confirmação, resposta a opção de pendência ou exportação; nunca inicia análise substantiva (P-18). |
| Ficha de procedência | Visão derivada da rastreabilidade que mostra ao usuário a origem de parâmetros, dados, métodos e resultados. |
| Gatilho de ambiguidade | Regra determinística (CFG-AMB) que obriga a verificação de ambiguidade material. |
| Validador de saída | Função determinística da governança que verifica todo texto produzido pelo LLM antes da exibição (Parte 14). |
| Modo degradado | Operação sem participação do LLM (Parte 16). |
| Disponibilidade operacional | Condição corrente de funcionamento de capacidade ou componente, mantida fora da configuração governada (RQ-ARQ-11). |
| Elementos ativos | Elementos do estado da linha aplicáveis à solicitação corrente segundo escopo, validade e vigência. |
| Triagem estrutural e de privacidade | Exame determinístico que, antes de qualquer envio de conteúdo ao LLM, identifica e protege campos e trechos potencialmente identificadores — identificadores estruturados, campos de nome ou de identificação individual e entidades nominais cujo papel não esteja estabelecido (seção 5.5, F-01). Aplica as quatro classes de RQ-DAD-20; minimiza metadados e preserva linguagem funcional não nominal triada, sem exigir tipificação como entidade. Conteúdo nominal ou identificador originado do usuário só é liberado em claro com evidência determinística positiva de papel não pessoal. |
| Campo protegido | Campo ou trecho marcado como identificador direto, potencialmente identificador ou entidade nominal ambígua; usado apenas internamente pelo motor em operações autorizadas e representado ao LLM somente por placeholder (RQ-DAD-39). Alias de metadado não implica classificação pessoal; originais sujeitos à minimização e mapas também permanecem fora do LLM. |
| Visualizador da base | Recurso de interface que exibe a base carregada ao próprio usuário, com identificadores diretos mascarados por padrão; não é produto analítico. |
| Valor factual do usuário | Dado fornecido explicitamente pelo usuário para uso por capacidade, com origem e escopo registrados (DA-07). |
| Substituição explícita | Determinação do usuário de que seu valor substitua, no escopo indicado, dado existente na base (DA-03). |
| Critério normativo do usuário | Critério avaliativo definido explicitamente pelo usuário para sua análise, com classificação associada (DA-21). |
| Agregado parcial | Agregado calculado sobre os membros avaliáveis de um conjunto, com cobertura e suporte efetivo explícitos; no agregado multicategorial, um território só integra o suporte com todas as categorias solicitadas avaliáveis (F-05a); sua validade isolada não estabelece comparabilidade temporal (CAP-AGR-01). |
| Unidade de observação | O que cada registro representa, como um vínculo; distingue-se da unidade que o resultado mede (RQ-DAD-35). |
| Unidade de contagem | Entidade ou medida contada pelo indicador, como pessoas, vínculos ou postos, segundo significado autorizado. |
| Identidade de deduplicação | Chave ou regra autorizada que reconhece a mesma entidade, com domínio de unicidade e completude suficientes para a operação (RQ-DAD-35). |
| Suporte efetivo do agregado | Membros territoriais e categoriais efetivamente incluídos em cada período, com a composição do numerador e do denominador; não é a lista de identificadores de pessoas. |
| Pequena base conversacional | Conjunto de registros ou dados fornecido explicitamente na conversa que pode existir como dataset independente, materializado temporariamente em C-10, com procedência MANIFESTACAO_USUARIO e o mesmo fluxo de proteção e habilitação de arquivos (RQ-DAD-31 a RQ-DAD-34, RQ-DAD-40). "Pequena" não fixa limite metodológico de linhas (RQ-DAD-43). |
| Soma das contagens dos componentes | Resultado que soma as contagens ou presenças dos componentes de um agregado; pode conter dupla contagem quando uma mesma pessoa pertence a mais de um componente e não equivale a pessoas únicas (CAP-AGR-01). |
| Premissa factual do usuário | Informação fornecida explicitamente pelo usuário e aceita como premissa da análise, como a ausência de sobreposição entre componentes, registrada com origem, escopo, conteúdo e impacto (RQ-GOV-22). |
| Reconhecimento governado de categoria | Correspondência determinística entre a expressão que designa uma categoria e o vocabulário governado de CFG-DOM e CFG-VOC, com resultado FTS_INEQUIVOCA, FTS_CONTEXTUAL, FTS_AMBIGUA ou NAO_RECONHECIDA (seção 4.3). |
| Categoria de reconhecimento contextual | Categoria de CFG-DOM identificada por alias governado, cuja pertença à FTS exige âncora contextual autorizada; sem ela, a pertinência fica incerta, nunca NAO_PERTINENTE por esse motivo (FTS_CONTEXTUAL, seção 4.3). |
| Declaração de domínio da base | Afirmação, por fonte, metadado autorizado ou pelo usuário, de que uma base representa a FTS; estabelece a pertença de suas categorias apenas no escopo daquela base (RQ-DAD-19). |
| Escala de apresentação | Transformação formal da densidade canônica por habitante para exibição, como por 1.000 habitantes (DA-09). Referência ou critério sem unidade é interpretado somente pelo ContextoDeMedida determinístico único do objeto comparado (seção 3.2). |
| Referencial geodésico | Sistema de referência das coordenadas, cujo elipsoide é usado no cálculo de distâncias (ex.: SIRGAS2000, suportado sem ser padrão universal) (seção 5.6). |
| Registro de conteúdo não ancorado (RCNA) | Registro mantido pela governança de todo conteúdo factual que, por falha, tenha chegado ao usuário a partir de saída do LLM sem âncora válida (seção 7.1). |
| Linha de consolidação | Linha analítica destinada exclusivamente a comparar ou consolidar resultados de outras linhas [C §7.6]. |
| Vínculo resultado-linha | Associação entre um resultado e uma linha, portadora de papel e vigência (seção 3.2). |
| Configuração Inicial de Implementação | Conteúdo dos 24 itens CFG com que o sistema é implementado nesta versão, definido na seção 4.4 com conteúdo explícito ou vazio deliberado (RQ-DOC-06). |
| Configuração deliberadamente vazia | Item CFG sem conteúdo por decisão da versão, com comportamento na ausência explicitamente definido; não é lacuna nem autoriza valor padrão improvisado (RQ-CFG-12). |
| Valor factual complementar | Valor fornecido pelo usuário que completa objeto, base, recorte ou análise identificável, sem constituir dataset independente (ex.: população de um território em um período); fica associado ao objeto e à solicitação/linha aplicável quando existente; fornecido sem linha aplicável, pode ser reutilizado por qualquer linha compatível da sessão, sem exclusividade (RQ-DAD-40, RQ-LIN-21, F-06). |
| Declaração semântica | Informação do usuário sobre o significado de base ou elemento existente (ex.: "Esta base é de médicos de 2024"); estabelece ou atualiza metadado no escopo apropriado, sem criar base (RQ-DAD-40, F-06). |
| Aditividade | Possibilidade de somar valores de partes diferentes e tratar o resultado como o valor do conjunto, sem sobreposição ou dupla contagem indevida; verificada somente quando a operação agrega a dimensão correspondente (RQ-DAD-36, F-02). |
| Recorte | Combinação de indicador, categorias, universo ou territórios, períodos e modo territorial que delimita o objeto de uma solicitação; o recorte corrente da linha é mantido em EstadoLinha (RQ-LIN-19). |
| Dimensão da linha | Elemento do recorte (indicador, categoria, universo, período ou modo territorial) estabelecido com escopo de linha; permanece válido enquanto não for substituído ou restringido (RQ-LIN-19, F-07). |
| Resultado deslocado | Resultado VALIDO cujo vínculo passou a NAO_VIGENTE por mudança de foco ou de recorte da linha (DESLOCAMENTO_DE_FOCO); conserva caráter contemporâneo e pode ser componente, entrada de comparação ou resultado de outro recorte (RQ-LIN-20, F-03). |
| Caráter histórico | Condição do vínculo NAO_VIGENTE por SUBSTITUICAO_DE_ESTADO — nova versão, parâmetro, decisão, significado ou condição que substitui o estado de que o resultado dependia; NAO_VIGENTE não implica, por si só, caráter histórico (RQ-LIN-20, F-03). |
| Qualificador obrigatório | Indicação de alcance, cobertura ou natureza que integra o significado do resultado (ex.: "entre as referências avaliáveis", agregado parcial, soma das contagens dos componentes, "da coorte inicial", caráter histórico) e é preservada em toda apresentação (RQ-RES-11, V-15, F-04). |
| Entidade nominal ambígua | Expressão nominal em texto livre cujo papel — pessoa ou entidade não pessoal — não está estabelecido por fonte autorizada, estado validado, estrutura linguística governada ou declaração do usuário; permanece protegida até resolução (RQ-DAD-38, F-01). |
| Placeholder protegido | Rótulo estável na sessão (ex.: [CPF_1], [PESSOA_1]) que substitui valor protegido no conteúdo entregue ao LLM; o mapeamento para o original fica restrito ao processamento protegido (RQ-DAD-39). |
| Estado de preparação da entrada | Situação da entrada ou base na via HABILITADORA, registrada em StatusBase: recebida, triada, aguardando confirmação, examinada, disponível, bloqueada ou descartada (RQ-DAD-42, F-08). |
| Pendência habilitadora | Pendência vinculada à entrada ou base na via HABILITADORA (confirmação de uso, estrutura da entrada, natureza de entidade nominal necessária à materialização); reapresentada sem duplicata quando análise dependente é solicitada (RQ-FLX-22, F-08). |
| Âncora documental | Referência estruturada `DOC:<fonte_normativa>[.<caminho>]` a proposição normativa existente no Registro de Proposições Documentais vigente de CFG-DOC; sustenta toda explicação metodológica ou operacional exibida (seção 4.4.23, V-16, F-12). |
| Coorte inicial | Conjunto C0 de pessoas distintas presentes, em uma unidade analítica, no período inicial t0 de CAP-ROT-01; único conjunto que compõe o denominador das taxas de rotatividade e de permanência da coorte inicial (seção 8.4). |
| Identidade longitudinal | Identidade de deduplicação autorizada cujo âmbito de unicidade permite reconhecer a mesma pessoa em t0 e t1 no domínio da unidade ou da união analisada (RQ-DAD-35, CAP-ROT-01). |

---

## Parte 1 — Finalidade, domínio, escopo e fronteiras de autoridade

### 1.1. Finalidade e identidade

- **RQ-ESC-01** — O agente DEVE atuar exclusivamente na produção e exploração de diagnóstico territorial da força de trabalho na saúde (FTS): caracterização descritivo-analítica e rastreável da configuração e da dinâmica territorial e temporal da FTS [C §1.1–1.4, §8.3]. [INSP][T-E2E]
- **RQ-ESC-02** — Juízo avaliativo (adequação, insuficiência, prioridade, problema) só PODE integrar resultado ou síntese quando produzido por critério autorizado: critério pré-configurado em CFG-NOR (deliberadamente vazio na Configuração Inicial de Implementação) ou critério normativo definido explicitamente pelo usuário para a análise, registrado com valor, operador, unidade e escala, classificação associada, origem e escopo (RQ-GOV-31). O resultado DEVE indicar quando a classificação decorre de critério do usuário [C §1.2, §3.7, §8.3] (DA-21). [T-GOV][T-E2E: AT-16, AT-46]
- **RQ-ESC-03** — Nenhum requisito desta SPEC depende de modelo de linguagem, fornecedor ou tecnologia específicos [C §1.1, §11.10]. [INSP]

### 1.2. Domínio temático

- **RQ-ESC-04** — O objeto analítico DEVE ser a FTS. Não há lista fechada de profissões ou categorias: a pertença de uma categoria ao objeto é estabelecida por fonte ou metadado autorizado, por declaração de domínio da base (no escopo daquela base), por reconhecimento determinístico em vocabulário governado não exaustivo (seção 4.3) — automático para FTS_INEQUIVOCA e, para categoria de reconhecimento contextual (FTS_CONTEXTUAL), condicionado a âncora contextual autorizada — ou por declaração explícita do usuário de que ela integra a FTS no contexto da análise (RQ-DAD-19); a simples solicitação de uma categoria como objeto de análise não constitui declaração. O LLM NÃO DEVE acrescentar, fundir ou inferir categorias, territórios ou outros elementos factuais a partir de conhecimento latente [C §3.1, §5.8] (DA-04, P-06). [T-GOV][T-E2E: AT-48, AT-55]
- **RQ-ESC-05** — Dados populacionais, territoriais e geográficos DEVEM ser usados apenas em função auxiliar prevista em contrato de capacidade (denominador, atributo de ordenação, referência espacial, delimitação de universo) [C §3.1, §3.7, §5.2]. Pedido cujo objeto seja exclusivamente auxiliar segue RQ-GOV-04. [T-GOV]
- **RQ-ESC-06** — Semelhança estrutural entre uma solicitação sobre força de trabalho de outro setor e uma capacidade existente NÃO DEVE tornar a solicitação pertinente (Caso 24). [T-E2E: AT-24]

### 1.3. Famílias autorizadas de ação analítica

| ID | Família [C §3.1] | Base no Concept | Capacidades (v1.2) | Não abrange |
|---|---|---|---|---|
| FAM-01 | Avaliar estrutura, significado, consistência, cobertura e condições de uso dos dados | §4.3.3 | CAP-EXA-01 | Achados substantivos sobre a FTS no exame habilitador |
| FAM-02 | Calcular e explorar indicadores definidos da FTS | §4.3.5 | CAP-IND-01, CAP-IND-02 | Indicadores sem definição em CFG-IND; indicadores externos (EXC-04) |
| FAM-03 | Analisar territórios individualmente | §3.2 | Capacidades analíticas em modo INDIVIDUAL | — |
| FAM-04 | Comparar territórios, conjuntos, períodos ou categorias quando compatível | §4.3.7 | CAP-CMP-01 | Fusão de categorias ou períodos |
| FAM-05 | Analisar conjuntamente unidades mantidas distintas | §3.1, §3.2 | Capacidades analíticas em modo CONJUNTO_NAO_COMPARATIVO | Relações comparativas (pertencem a FAM-04) |
| FAM-06 | Produzir análises agregadas metodologicamente válidas | §4.3.8 | CAP-AGR-01 | Equivalência presumida com unidade superior observada |
| FAM-07 | Analisar distribuições e posições relativas | §4.3.6 | CAP-DIS-01, CAP-DIS-02, CAP-DIS-03 | Interpretação normativa de posição |
| FAM-08 | Analisar mudanças, trajetórias e tendências por métodos estabelecidos | §4.3.9, §4.3.10 | CAP-TMP-01, CAP-TEN-01, CAP-ROT-01 | Projeção ou previsão (Caso 4); agregados temporais sintéticos sem procedimento |
| FAM-09 | Estabelecer e usar referências territoriais segundo critérios autorizados | §4.3.11 | CAP-REF-01 | Caráter normativo da referência |
| FAM-10 | Analisar relações espaciais e distâncias | §4.3.12 | CAP-ESP-01, CAP-ESP-02, CAP-ESP-03 | Tempo de deslocamento, acessibilidade real, padrões espaciais (EXC-05) |
| FAM-11 | Construir subconjuntos e ordenações | §4.3.13 | CAP-SUB-01, CAP-SUB-02, CAP-SUB-03 | Expressões, consultas ou fórmulas livres |
| FAM-12 | Combinar capacidades em solicitações compostas | §4.4, §6.5 | Orquestração (Parte 9) | Criação de método por composição |
| FAM-13 | Produzir representações de resultados estruturados | §4.3.14, §8.12 | CAP-REP-01 a CAP-REP-06 | Classes, totais, tendências ou escalas calculados pela apresentação |
| FAM-14 | Produzir sínteses ancoradas em resultados estruturados | §4.3.15 | CAP-SIN-01 | Nova operação analítica |

A delimitação do universo (CAP-UNI-01, [C §4.3.4]) é suporte transversal às famílias FAM-02 a FAM-11 e não constitui família autônoma (P-02). Interpretar, conduzir e orquestrar [C §4.3.1, §4.3.2] são funções FN-* (Parte 8), não famílias de ação analítica.

- **RQ-ESC-07** — Uma ação é admissível no escopo somente se enquadrar em alguma FAM e não incidir em EXC [C §3.1]. [T-GOV]
- **RQ-ESC-08** — Ação enquadrada em FAM sem capacidade concreta em status ATIVA DEVE receber o desfecho ADM-SC com o motivo aplicável [C §3.1, §5.2]. [T-GOV]
- **RQ-ESC-09** — Nova capacidade dentro de FAM existente não exige revisão de escopo; nova família exige revisão deliberada de escopo pela Parte 19 [C §3.1, §11]. [INSP]

### 1.4. Exclusões do escopo atual

| ID | Exclusão [C §3.8] | Desfecho |
|---|---|---|
| EXC-01 | Busca ou avaliação de evidências científicas ou documentais | ADM-FE |
| EXC-02 | Recomendação automática de políticas, programas ou intervenções | ADM-FE |
| EXC-03 | Inferência causal | ADM-FE |
| EXC-04 | Análise autônoma de indicadores socioeconômicos, ambientais ou contextuais externos | ADM-FE |
| EXC-05 | Associação, correlação, regressão explicativa ou detecção autônoma de padrões espaciais | ADM-FE |
| EXC-06 | Interpretação sistemática de documentos não estruturados como fonte analítica | ADM-FE |
| EXC-07 | Uso autônomo de fontes externas para completar dados ou parâmetros | ADM-FE (ver também INV-14) |
| EXC-08 | Criação de novos métodos durante a interação | ADM-SC com motivo METODO_NAO_INCORPORADO e referência a EXC-08, quando a ação se enquadra em FAM [C §3.6]; ADM-FE quando não se enquadra (P-04) |
| EXC-09 | Exposição de registros pessoais individualizados como produto | ADM-FE (ver Parte 18) |
| EXC-10 | Registros individualizados como objeto de classificação, ranking, listagem ou diagnóstico individual | ADM-FE (ver Parte 18) |
| EXC-11 | Substituição do julgamento técnico ou da decisão substantiva do usuário | A decisão permanece pendente (BLQ-DEC); o pedido de delegação não é atendido (INV-06) |

- **RQ-ESC-10** — Parte de solicitação que incida em EXC DEVE receber o desfecho da tabela, sem execução analítica da parte excluída e sem conteúdo substitutivo produzido pelo LLM [C §3.8, §5.6]. [T-GOV][T-E2E: AT-04, AT-06]
- **RQ-ESC-13** — Os padrões PT/EN de CFG-EXC (seção 4.4.3) são sinais determinísticos que obrigam rechecagem da intenção e da admissibilidade (RQ-GOV-09). A presença do termo isolado não produz recusa automática: o desfecho da tabela só se aplica quando a leitura mínima, o contexto autorizado e os gates estabelecerem a incidência da exclusão. [T-GOV][T-E2E: AT-87]

### 1.5. Modos de tratamento territorial

| Modo | Definição [C §3.2] | Capacidade exigida |
|---|---|---|
| INDIVIDUAL | Uma unidade analisada como objeto específico | Capacidade da família solicitada |
| CONJUNTO_NAO_COMPARATIVO | Duas ou mais unidades distintas, resultados coexistentes sem relações calculadas | Capacidade da família, aplicada por unidade |
| CONJUNTO_COMPARATIVO | Unidades distintas com relações explícitas produzidas por capacidade | CAP-CMP-01 (ou ordenação CAP-SUB-02) sobre resultados compatíveis |
| AGREGADO | Dados combinados para resultado referente ao conjunto | CAP-AGR-01 |

- **RQ-ESC-11** — O modo territorial é elemento da interpretação operacional e da assinatura material. Quando não for determinado por fonte autorizada ou por estado válido e vigente, o usuário DEVE decidi-lo (Caso 3). [T-GOV][T-E2E: AT-03]
- **RQ-ESC-12** — Categorias e períodos distintos PODEM ser analisados lado a lado ou comparados, sem fusão. A agregação de categorias ou de territórios em um conjunto segue CAP-AGR-01, que distingue a soma das contagens dos componentes da contagem de pessoas únicas quando há possibilidade de sobreposição. Soma, média, acumulado ou outro agregado temporal exigem método específico incorporado; na ausência, o desfecho é ADM-SC com motivo NAO_INCORPORADA. O LLM NÃO DEVE inventar método de combinação [C §3.2, §4.3.7, §4.3.9] (P-21, DA-16). [T-GOV][T-E2E: AT-54]

### 1.6. Matriz de autoridade

Códigos: **D** decide; **P** propõe (registro de interpretação sem autoridade); **V** verifica e aplica regra; **E** executa; **X** proibido; **—** sem papel.

| Ato | Usuário | LLM (C-03, C-12) | Governança (C-04) | Orquestrador/Motor (C-05, C-06) | Configuração governada |
|---|---|---|---|---|---|
| Definir ou alterar finalidade, domínio, escopo, famílias, regras, métodos e catálogo | X | X | V | — | D (processo externo; congelada na sessão) |
| Leitura mínima e interpretação operacional | D (quando confirmação é exigida) | P | V | — | — |
| Classificar pertinência e admissibilidade | D (esclarece incerteza) | P | D (por regra) | — | regras |
| Estabelecer pertença de categoria à FTS | D (declaração explícita, inclusive de domínio da base) | P (só correspondência com alias existente) | D (reconhecimento determinístico, seção 4.3) | — | D (fonte ou metadado autorizado; vocabulário governado) |
| Informar disponibilidade de capacidade | — | X | D (CFG-CAP e disponibilidade operacional) | — | status |
| Fixar parâmetro substantivo, limiar, critério ou critério normativo | D (graus de liberdade) | P (estrutura o que foi dito) | V | — | D (quando fixado por regra) |
| Fornecer valor factual ou premissa factual, ou substituir valor da base no escopo | D | P (estrutura o que foi dito) | V | — | — |
| Definir universo, categoria, período, indicador, modo | D (escolha ainda aberta) | P | V (resolução inequívoca por fonte autorizada ou estado; RQ-GOV-14) | — | D (quando por regra) |
| Estruturar dados explícitos da conversa | D (fonte dos dados) | P (somente conteúdo sanitizado, com placeholders) | V (valores, entidades, relações e origem; associação aceita somente com relação estrutural única, RQ-DAD-41; seção 5.8) | E (normalização determinística) | regras de correspondência (CFG-VOC) |
| Classificar expressão nominal como pessoa ou entidade não pessoal na triagem | D (esclarece a natureza, RQ-DAD-38) | X | D (regras determinísticas) | — | D (CFG-PRV, CFG-VOC) |
| Escolher capacidade para intenção estabelecida, ordenar etapas, reutilizar resultado válido e vigente, escolher apresentação compatível | — | P | V | E | — |
| Escolher escala de apresentação | D | — | V | E | D (escala configurada para o indicador) |
| Autorizar execução de etapa | — (fornece decisões) | X | D | — | — |
| Executar cálculo, classificação, filtro, ordenação, agregação | — | X | — | E | — |
| Atribuir papel diagnóstico | D (intenção e ampliação) | P (identifica entregáveis) | D (na autorização) | — | — |
| Resolver conflito entre fontes | D (sem precedência aplicável) | X | V | — | D (precedência) |
| Confirmar significado de campo | D (sem metadado ou regra) | P (só correspondências com elementos autorizados) | V | — | D |
| Confirmar autorização de uso de base com campos protegidos | D | X | V | — | — |
| Revelar identificador no visualizador da base | D (ação explícita) | X | V | — | — |
| Abrir, retomar ou encerrar linha | D (quando material) | P | V | — | — |
| Classificar natureza de alteração | D (declara) | P | D (por âncora) | — | — |
| Recalcular após invalidação ou perda de vigência | D (pedido, inclusive implícito na solicitação) | P (oferta) | V | E | — |
| Sugerir análise e iniciar nova análise | D (solicita ou aceita pela conversação) | P | V | E (após aceite) | — |
| Redigir síntese | — | E (CAP-SIN-01) | V (validador) | — | — |
| Explicar método, regra, capacidade, limitação ou funcionamento | — | E (seleção e organização de texto canônico ou forma autorizada com âncora DOC:) | V (validador documental/estrutural, V-16) | — | D (CFG-DOC) |
| Apresentar resultado sem LLM | — | — | V | E (C-11, C-02) | — |

### 1.7. Invariantes globais

| ID | Invariante | Verificação |
|---|---|---|
| INV-01 | Nenhuma capacidade analítica é executada sem Autorização registrada que inclua a etapa [C §6.4]. | [T-GOV] |
| INV-02 | Todo valor, classificação, relação, ordenação, seleção, agregação, filtro ou cruzamento apresentado como resultado provém de dado autorizado ou de resultado estruturado de capacidade autorizada [C §5.6]. | [T-GOV][T-E2E] |
| INV-03 | O LLM nunca é origem de elemento factual ou substantivo; não existe tipo de fonte correspondente ao LLM [C §5.8, §8.6]. | [INSP][T-GOV] |
| INV-04 | Ausência de informação, dado ausente ou unidade sem registro nunca são convertidos em zero, média, estimativa, exclusão, falso ou verdadeiro; permanecem não avaliáveis, salvo método autorizado ou valor fornecido explicitamente pelo usuário, sempre registrados [C §7.4, §13.2 k] (DA-10). | [T-DET] |
| INV-05 | Bloqueio, falha ou indisponibilidade nunca são apresentados como resultado negativo, zero, nulo ou vazio [C §9.2, §9.12]. | [T-GOV][T-E2E] |
| INV-06 | Decisão substantiva não resolvida por regra não é tomada pelo sistema; delegação genérica do usuário não transfere autoridade [C §3.6]. | [T-GOV][T-E2E: AT-25] |
| INV-07 | Resultados estruturados são imutáveis após o registro [C §8.10]. | [T-DET] |
| INV-08 | Resultado INVALIDADO nunca é reutilizado como entrada nem apresentado como componente válido [C §7.7]. | [T-DET] |
| INV-09 | Reuso automático exige resultado VALIDO com vínculo VIGENTE na linha corrente, inclusive o vínculo restabelecido pelo retorno exato ao mesmo recorte (RQ-LIN-20); resultado deslocado por mudança de foco é usado como componente contemporâneo ou entrada de comparação sem reexecução, e uso de resultado de caráter histórico em comparação explicitamente solicitada segue RQ-ORQ-07 e RQ-ORQ-13 [C §7.7] (F-03). | [T-DET][T-E2E: AT-77] |
| INV-10 | Uma composição executa sob um contexto coerente e fixado. Resultados de contextos de origem distintos podem ser entradas compatíveis de comparação, com diferenças autorizadas registradas no contexto da nova composição (RQ-ORQ-13); diferenças de versões só quando forem objeto explícito, nunca como atualização silenciosa [C §6.5]. | [T-DET][T-E2E: AT-21, AT-67] |
| INV-11 | Representação e síntese não realizam operação analítica [C §4.3.14, §4.3.15]. | [T-GOV] |
| INV-12 | Resultado cuja rastreabilidade obrigatória não foi registrada não é apresentado como resultado analítico válido [C §5.10]. | [T-DET][T-E2E: AT-30] |
| INV-13 | Todo texto produzido por LLM passa pelo validador de saída antes de ser exibido. | [T-GOV] |
| INV-14 | Não há acesso a fontes externas; o catálogo desta versão não contém capacidade de busca externa [C §5.8]. | [INSP][T-GOV] |
| INV-15 | A configuração governada é somente leitura durante a interação e permanece congelada durante toda a sessão; nova versão só vale para nova sessão [C §5.3] (DA-01). | [INSP][T-GOV][T-E2E: AT-52] |
| INV-16 | Identificadores e registros individualizados não são enviados ao LLM nem aparecem em resultados, representações, sínteses, diagnósticos, relatórios ou exportações; no visualizador da base, identificadores diretos ficam mascarados por padrão; a triagem que estabelece a proteção é determinística e precede o LLM, que não decide se uma expressão designa pessoa ou entidade não pessoal; conteúdo nominal ou identificador originado do usuário só atravessa essa fronteira em claro com evidência determinística positiva de papel não pessoal [C §3.8] (DA-27, F-01). | [T-GOV][T-E2E: AT-37, AT-74, AT-75] |
| INV-17 | Nova análise substantiva só é iniciada por solicitação ou aceite do usuário; o exame habilitador não produz achados [C §3.3, §5.12]. | [T-GOV][T-E2E: AT-15, AT-26] |
| INV-18 | Nova solicitação analítica só é formulada pela conversação com o LLM; controles da interface não iniciam análise substantiva; estado visual não altera estado analítico, e a seleção só fundamenta análise quando capturada como manifestação do usuário [C §4.3.14, §11.11] (P-18). | [T-GOV][T-E2E: AT-13, AT-20] |

---

## Parte 2 — Arquitetura lógica e componentes

### 2.1. Correspondência entre camadas e componentes

| Camada [C §6.2] | Componentes |
|---|---|
| Interlocução | C-01 Interface; C-02 Canal Sistêmico; C-03 (funções de conversação) |
| Controle de pertinência | C-04 (gates de pertinência e admissibilidade), apoiado por FN-INT-01 |
| Interpretação | C-03 (FN-INT-01, FN-INT-02, FN-INT-03, FN-INT-04, FN-META-01), validado por C-04 |
| Orquestração | C-05 Orquestrador, apoiado por FN-ORQ-01 |
| Execução analítica | C-06 Motor Analítico |
| Resultados estruturados | C-07 Repositório de Resultados; C-08 Gestor de Linhas e Estado |
| Representação e síntese | C-11 Representação; C-12 Síntese |
| Transversais | C-09 Configuração; C-10 Dados e Metadados; C-13 Rastreabilidade |

### 2.2. Componentes

| ID | Componente | Natureza | Responsabilidade | Proibições |
|---|---|---|---|---|
| C-01 | Interface de Interação | Apresentação | Receber mensagens da conversação; oferecer controles estruturados (upload, navegação, filtros, seleção, visualização, confirmações, resposta a opções de pendências, exportação); exibir somente saídas validadas; manter estado visual separado do analítico; exibir o visualizador da base com máscara e os avisos obrigatórios; capturar seleção no envio; controle Encerrar sessão; mostrar aliases de metadados; registrar EV-INTERACAO_USUARIO do catálogo fechado de CFG-OPR | Iniciar análise por controle de interface; criar classes, filtros analíticos ou cálculos; exibir texto do LLM não validado; enviar dados ao LLM |
| C-02 | Canal Sistêmico | Determinística | Informar estados operacionais e avisos obrigatórios por modelos de mensagem (CFG-TPL), no idioma da sessão, preenchidos apenas com campos estruturados; TPL-04/13 e formas PT/EN; interpolação determinística; avisos de E1 e encerramento; opções somente com rótulos governados | Depender do LLM; produzir conteúdo analítico; trocar de idioma como contingência |
| C-03 | Serviço de Interpretação | LLM | Executar FN-INT-01 a FN-INT-04, FN-ORQ-01 e FN-META-01, devolvendo registros estruturados | Escrever em qualquer repositório; executar capacidades; ser fonte |
| C-04 | Governança | Determinística | Triagem estrutural e de privacidade antes do LLM, com validação determinística de identificadores estruturados, classificação de entidades nominais e atribuição de placeholders; gates; validação de âncoras; classificação de autoridade; detecção de ambiguidade material; verificação pré-execução; autorização; validador de saída; guarda de privacidade; quatro classes de D13 com evidência positiva de D29, V-16 por forma/idioma/versão e disposições e consequências de exclusão; validar autonomia estrutural, sem julgamento semântico geral | Aceitar decisões substantivas não autorizadas; alterar configuração; delegar ao LLM a decisão sobre natureza pessoal de expressão |
| C-05 | Orquestrador | Determinística | Validar e executar o plano autorizado; reavaliar etapas; reuso; replanejamento rastreável; suspensão; unidades semânticas independentes, ResultadoElemento, orçamento de retry invariável, propagação somente a consumidores efetivos e descarte de retorno tardio | Julgamento semântico; alterar parâmetros substantivos |
| C-06 | Motor Analítico | Determinística | Executar capacidades analíticas segundo contratos e métodos versionados | Executar sem Autorização; aceitar expressões livres |
| C-07 | Repositório de Resultados | Armazenamento | Guardar resultados imutáveis com resumo de conteúdo | Alterar resultado registrado |
| C-08 | Gestor de Linhas e Estado | Determinística | Linhas, estado e recorte corrente, contexto de interpretação, pendências analíticas e habilitadoras, motor de validade e vigência; escopos versionados de solicitação, retirada D17-A, fila de pendências pré-E4, relógio de inatividade por EV-INTERACAO_USUARIO e prioridade de encerramento concorrente | Promover elemento inválido; transferir decisões entre linhas |
| C-09 | Registro de Configuração | Armazenamento | Itens CFG versionados; snapshot fixado no início de cada sessão; catálogo literal PT/EN de formas por id_doc, fechado antes da publicação do snapshot | Aceitar escrita a partir da interação; trocar o snapshot durante a sessão |
| C-10 | Registro de Dados e Metadados | Armazenamento | Bases da sessão e seus estados de preparação, versões, metadados autorizados, mapeamentos semânticos, marcações de proteção, guarda restrita do original protegido e do mapeamento de placeholders, quadros de universo; aliases de metadados, seleção/papel das planilhas, negativa/reversão e descarte integral dos originais e mapas | Tratar texto contido nos dados como regra; manter bases após a sessão; expor original protegido ou mapeamento de placeholders fora do processamento protegido |
| C-11 | Representação | Determinística | Transformar resultados em tabelas, gráficos, mapas, painéis, relatório HTML, PDF e CSV com transformações formais autorizadas | Transformação com significado analítico; mudança automática de escala |
| C-12 | Síntese | LLM | Executar CAP-SIN-01, produzindo segmentos tipados com referências | Nova operação analítica; conteúdo não ancorado |
| C-13 | Rastreabilidade | Armazenamento | Registro de eventos somente acréscimo e encadeado durante a sessão; consultas de linhagem; ficha de procedência; eventos sanitizados de escopo/causas/estados; eliminação integral ao encerrar sessão | Apagar ou reescrever evento durante a sessão; registrar valores de campos protegidos |

### 2.3. Regras de fronteira

- **RQ-ARQ-01** — C-03 e C-12 NÃO DEVEM ter permissão de escrita em C-07, C-08, C-09, C-10 ou C-13. Seus registros são entregues a C-04 ou C-05, que os registram com natureza INTERPRETACAO_LLM ou SINTESE. [INSP][T-GOV]
- **RQ-ARQ-02** — C-06 DEVE recusar execução sem Autorizacao ativa. Para tipo ANALITICA, a etapa, o resumo do plano e o contexto devem coincidir; para tipo HABILITADORA, somente CAP-EXA-01 é admitida, para a entrada identificada, conforme RQ-DAD-34. [T-GOV]
- **RQ-ARQ-03** — Todo texto produzido por C-03 ou C-12 destinado ao usuário DEVE passar pelo validador de saída de C-04 antes de C-01 (INV-13). [T-GOV]
- **RQ-ARQ-04** — C-02 DEVE operar sem o LLM, usando somente modelos de CFG-TPL e campos estruturados registrados [C §9.11]. Conteúdo metodológico de TPL-12 usa exclusivamente as formas autorizadas de CFG-DOC, com verificação determinística de C-04; isso não autoriza nova síntese analítica. C-02 executa TPL-04 completo, TPL-13 e controle Encerrar sessão sem LLM, usando formas PT/EN governadas. C-11 interpola somente variáveis tipadas ancoradas; não traduz conteúdo documental durante a sessão. [T-DET]
- **RQ-ARQ-05** — C-11 DEVE aplicar somente transformações da lista autorizada de CFG-REP (Parte 13). [T-DET]
- **RQ-ARQ-06** — O contexto enviado a C-03 e C-12 DEVE ser montado por C-08 a partir da estrutura sanitizada pela triagem (RQ-DAD-23) e de resultados agregados ou territoriais, com origem e status de cada elemento, e NÃO DEVE conter identificadores nem registros individualizados (INV-16) (DA-27). Aplicar as quatro classes de RQ-DAD-20 em todo canal: nomes de campos, arquivos e planilhas sujeitos à minimização usam aliases; originais e mapas permanecem exclusivamente em C-10. Preservar fontes por IDs/versões/localizadores sanitizados, sem vazamento por perfil, procedência, eventos, produtos ou fallback. [T-GOV]
- **RQ-ARQ-07** — Todo acontecimento que influencie análise DEVE gerar evento em C-13 antes que a saída dependente se torne apresentável (INV-12). [T-DET]
- **RQ-ARQ-08** — C-09 DEVE expor apenas leitura aos demais componentes durante a interação (INV-15). [T-GOV]
- **RQ-ARQ-09** — A única via de produção de conteúdo analítico é C-06; nenhum outro componente PODE calcular, classificar, filtrar, ordenar ou agregar valores apresentados como resultado (INV-02). Estruturação e normalização de entrada em C-10, validadas por C-04, apenas preservam os fatos fornecidos; contagens e indicadores derivados são produzidos pelas capacidades, após a autorização aplicável. [INSP][T-GOV]
- **RQ-ARQ-10** — A indisponibilidade de C-03 ou C-12 NÃO DEVE impedir o funcionamento de C-02, C-04, C-05, C-06, C-07, C-08, C-11 e C-13 (Parte 16). Indisponibilidade exclusiva de síntese, depois de resultados necessários válidos, apresentáveis e rastreáveis, permite atendimento degradado por RQ-DEG-04, sem alterar a exigência de LLM nas etapas ainda necessárias. [T-E2E: AT-13, AT-14]
- **RQ-ARQ-11** — A disponibilidade operacional de capacidades e componentes DEVE ser mantida fora da configuração governada e consultada por C-04 em E5 e por C-05 antes de cada etapa; ela pode mudar durante a sessão sem alterar o snapshot (DA-01, P-03). [T-DET]

### 2.4. Naturezas de execução [C §6.3]

| Natureza | Componentes | Garantia exigida |
|---|---|---|
| Interlocução, interpretação e orquestração (LLM) | C-03 | Saída estruturada validada; sem autoridade; nunca fonte |
| Analítica determinística | C-06 | Reprodutibilidade: mesmas entradas, mesmas versões, mesmo resumo de conteúdo |
| Representação | C-11 | Transformações formais determinísticas e registradas |
| Síntese (LLM) | C-12 | Segmentos ancorados; validação obrigatória; variação apenas linguística [C §8.10] |
| Controle | C-02, C-04, C-05, C-08 | Determinística e verificável |

---

## Parte 3 — Modelo de informação

### 3.1. Enumerações canônicas

| Enumeração | Valores | Observações |
|---|---|---|
| TipoFonte | DADO_AUTORIZADO; METADADO_AUTORIZADO; CONFIGURACAO_GOVERNADA; MANIFESTACAO_USUARIO; RESULTADO_ESTRUTURADO; INFORMACAO_OPERACIONAL_SISTEMA | Fontes de [C §5.8, §7.2]. Não existe valor para o LLM (INV-03). |
| SubtipoManifestacao | AFIRMACAO_PROPRIA; ESCOLHA_DE_OPCAO_AUTORIZADA; SELECAO_DE_INTERFACE | Obrigatório quando TipoFonte = MANIFESTACAO_USUARIO [C §8.6]. Declarações, valores factuais, substituições e critérios do usuário são AFIRMACAO_PROPRIA. |
| TipoPedido | ANALITICO; SOBRE_O_AGENTE; CONCEITUAL_DOMINIO; CONTROLE; RESPOSTA; DADOS; CONVERSACIONAL | Funções não exclusivas, atribuídas a partes da mensagem. CONTROLE segue RQ-FLX-09; RESPOSTA é resposta a pendência; DADOS é fornecimento deliberado de dados; CONVERSACIONAL cobre saudações e agradecimentos sem dados nem análise. |
| OrigemBase | UPLOAD_USUARIO; DADOS_CONVERSACIONAIS_USUARIO; FONTE_CONFIGURADA | Identifica a porta de entrada; não substitui TipoFonte nem a procedência original. FONTE_CONFIGURADA não tem instância na Configuração Inicial de Implementação (CFG-FON). |
| TipoDadoConversacional | PEQUENA_BASE_CONVERSACIONAL; VALOR_FACTUAL_COMPLEMENTAR; DECLARACAO_SEMANTICA | Classificação validada de dados fornecidos na conversa (RQ-DAD-40, F-06). |
| TipoAutorizacao | HABILITADORA; ANALITICA | Vias distintas de RQ-DAD-34 e da seção 7.7. |
| FuncaoConteudo | AFIRMACAO_ANALITICA; METODOLOGICO_OPERACIONAL; CONECTIVO | Função verificável do segmento; tipagem pelo LLM não dispensa validação (RQ-SIN-10). |
| Pertinencia | PERTINENTE; PERTINENCIA_INCERTA; NAO_PERTINENTE | [C §5.2]. PERTINENCIA_INCERTA é estado transitório (P-11). |
| Desfecho | ADM-NP; ADM-FE; ADM-SC; BLQ-INF; BLQ-DEC; BLQ-DAD; BLQ-SIG; BLQ-MET; BLQ-DEP; OPR-FAL; OPR-IND; RES-VAL; RES-LIM; RES-SCL; RES-VAZ | Semântica na Parte 15 [C §9.2]. |
| MotivoSemCapacidade | NAO_INCORPORADA; METODO_NAO_INCORPORADO; TEMPORARIAMENTE_INDISPONIVEL; RETIRADA | Complementa ADM-SC; METODO_NAO_INCORPORADO também identifica o impedimento metodológico BLQ-MET por referencial informado não suportado (RQ-DAD-26), sem se tornar MotivoNaoAvaliavel. TEMPORARIAMENTE_INDISPONIVEL decorre da disponibilidade operacional conhecida antes da execução (P-03). |
| StatusCapacidade | ATIVA; NAO_INCORPORADA; RETIRADA | Registrado em CFG-CAP e congelado na sessão (DA-01). |
| DisponibilidadeOperacional | DISPONIVEL; TEMPORARIAMENTE_INDISPONIVEL | Mantida fora da configuração (RQ-ARQ-11). |
| Avaliabilidade | AVALIAVEL; NAO_AVALIAVEL; FORA_DO_UNIVERSO | Dimensão distinta do desfecho [C §9.2] (P-12). |
| MotivoNaoAvaliavel | SEM_REGISTRO_OBSERVADO; DADO_AUSENTE; DENOMINADOR_AUSENTE; DENOMINADOR_ZERO; BASE_ZERO; SERIE_INSUFICIENTE; SEM_INFORMACAO_ESPACIAL; COORDENADA_INVALIDA; SIGNIFICADO_NAO_ESTABELECIDO; INCOMPARABILIDADE; DEPENDENCIA_NAO_AVALIAVEL | Lista fechada; ampliação pela Parte 19. |
| DetalheMotivo | CONJUNTO_REFERENCIAS_VAZIO; IDENTIDADE_LONGITUDINAL_INSUFICIENTE | Detalhe fechado de DEPENDENCIA_NAO_AVALIAVEL (CAP-ESP-02, CAP-ROT-01). |
| MotivoSemClassificacao | MUDANCA_DE_DIRECAO; SERIE_ESTAVEL | Motivo obrigatório de SEM_CLASSIFICACAO em CAP-TEN-01 (DA-15). |
| CondicaoCriterio | ATENDE; NAO_ATENDE; NAO_AVALIAVEL | [C §4.3.13]. |
| OperadorLogico | E; OU; NAO | Lógica trivalente de CAP-SUB-01 (DA-19). |
| Validade | VALIDO; INVALIDADO | Propriedade do resultado [C §7.7]. |
| Vigencia | VIGENTE; NAO_VIGENTE | Propriedade do vínculo resultado-linha [C §7.7]. |
| MotivoNaoVigencia | DESLOCAMENTO_DE_FOCO; SUBSTITUICAO_DE_ESTADO | Motivo do vínculo NAO_VIGENTE; somente SUBSTITUICAO_DE_ESTADO confere caráter histórico (RQ-LIN-20, F-03). |
| Reproducao | ORIGEM_DISPONIVEL; ORIGEM_INDISPONIVEL | [C §7.7]. |
| Apresentabilidade | APRESENTAVEL; RASTREABILIDADE_PENDENTE | [C §5.10]. |
| PapelResultado | COMPONENTE_DIAGNOSTICO; SUPORTE_INTERMEDIARIO | Atribuído na autorização [C §5.9, §8.4] (P-23). |
| StatusSolicitacao | RECEBIDA; EM_ADMISSAO; AGUARDANDO_USUARIO; AUTORIZADA; EM_EXECUCAO; SUSPENSA; CONCLUIDA; CONCLUIDA_PARCIAL; ENCERRADA_SEM_RESULTADO; CANCELADA | Estado agregado; não substitui autorização nem estados de etapas e entregáveis. Transições na Parte 6. |
| StatusEntregavel | ATENDIDO; PENDENTE; INTERROMPIDO; NAO_EXECUTAVEL; CANCELADO | Atendimento da unidade semântica validada, conforme RQ-RES-04; ATENDIDO inclui RES-LIM, RES-VAZ e RES-SCL. CANCELADO decorre exclusivamente de cancelamento explícito da solicitação, é terminal e distinto de retirada, falha e interrupção (RQ-FLX-02). |
| StatusEtapa | PLANEJADA; AUTORIZADA; EM_EXECUCAO; CONCLUIDA; REUTILIZADA; BLOQUEADA; FALHOU; SUSPENSA; CANCELADA | Ciclo próprio da etapa; pode avançar em partes independentes durante AGUARDANDO_USUARIO (RQ-FLX-01). |
| StatusPendencia | ABERTA; RESPONDIDA; SEM_APLICABILIDADE; ENCERRADA | Pendência nunca é "invalidada" [C §7.8, §9.10]. |
| TipoPendencia | PERTINENCIA; AMBIGUIDADE_MATERIAL; PARAMETRO_FALTANTE; DECISAO_SUBSTANTIVA; CONFLITO_DE_FONTES; SIGNIFICADO_DE_CAMPO; CONFIRMACAO_DE_USO_DA_BASE; ESTRUTURA_DE_ENTRADA; NATUREZA_DE_ENTIDADE_NOMINAL; REFERENCIAL_GEODESICO; LINHA; EMPATE_NO_CORTE; CONTINUIDADE_DE_COMPOSICAO; NATUREZA_DE_ALTERACAO | EMPATE_NO_CORTE só quando o usuário exige exatamente N (DA-18). ESTRUTURA_DE_ENTRADA cobre separador de CSV, planilha de XLSX e formato não estabelecido (RQ-DAD-43); NATUREZA_DE_ENTIDADE_NOMINAL, a pergunta de RQ-DAD-38. Vinculação analítica ou habilitadora conforme RQ-DAD-42 (F-08). Antes da criação de entregáveis, a ordem das pendências segue as classes de prioridade de RQ-FLX-01. |
| NaturezaAlteracao | SUBSTITUICAO_DE_ESTADO; CORRECAO_OU_REPUDIO; SEM_EFEITO | [C §7.7, §7.9]. |
| StatusSignificado | AUTORIZADO_POR_METADADO; AUTORIZADO_POR_CONFIGURACAO; CONFIRMADO_PELO_USUARIO; PROPOSTO_NAO_CONFIRMADO; INDEFINIDO | Por atributo semântico de campo [C §7.3]; reconhecimento conclusivo por regra configurada gera AUTORIZADO_POR_CONFIGURACAO (RQ-DAD-06). |
| ProtecaoCampo | NAO_PROTEGIDO; IDENTIFICADOR_DIRETO; POTENCIALMENTE_IDENTIFICADOR; ENTIDADE_NOMINAL_AMBIGUA; CONFIRMADO_NAO_IDENTIFICADOR | Resultado da triagem (seção 5.5) (DA-27, F-01). ENTIDADE_NOMINAL_AMBIGUA permanece protegida até resolução (RQ-DAD-38). |
| NaturezaEntidadeNominal | TERRITORIO; ORGANIZACAO_INSTITUICAO; PESSOA; OUTRA_ENTIDADE_NAO_PESSOAL; MANTER_PROTEGIDA | Opções da pergunta determinística de CFG-PRV e seus efeitos (RQ-DAD-38). |
| TipoPlaceholder | CPF; EMAIL; TELEFONE; PESSOA; IDENTIFICADOR; ENTIDADE_PROTEGIDA; CAMPO; ARQUIVO; PLANILHA | Forma `[TIPO_n]`, estável na sessão (RQ-DAD-39). |
| ReconhecimentoFTS | FTS_INEQUIVOCA; FTS_CONTEXTUAL; FTS_AMBIGUA; NAO_RECONHECIDA | Resultado do reconhecimento governado de categorias (seção 4.3); FTS_CONTEXTUAL identifica categoria cuja pertença exige âncora contextual (CFG-DOM); NAO_RECONHECIDA e FTS_CONTEXTUAL sem âncora não significam NAO_PERTINENTE (DA-04). |
| ModoTerritorial | INDIVIDUAL; CONJUNTO_NAO_COMPARATIVO; CONJUNTO_COMPARATIVO; AGREGADO | [C §3.2]. |
| DimensaoRecorte | INDICADOR; CATEGORIA; UNIVERSO; PERIODO; MODO_TERRITORIAL | Dimensões do recorte e da linha (RQ-LIN-19, F-07). |
| ClasseAutoridade | FIXADA_POR_REGRA; PARAMETRIZAVEL_PELO_USUARIO; OPERACIONAL_AUTORIZADA; PROIBIDA | [C §5.5]. |
| NaturezaRegistro | MANIFESTACAO_USUARIO; INTERPRETACAO_LLM; DECISAO_GOVERNANCA; EXECUCAO_ANALITICA; RESULTADO_ESTRUTURADO; REPRESENTACAO; SINTESE; OPERACIONAL_SISTEMA; CONFIGURACAO; DADOS | Distingue origens na rastreabilidade [C §8.7]. |
| ModoExplicitacao | ADOTADA_SEM_EXPLICITACAO; ADOTADA_E_EXPLICITADA; CONFIRMADA_PELO_USUARIO | [C §5.7, §9.4]. |
| CategoriaTendencia | CRESCIMENTO; CRESCIMENTO_ACELERADO; CRESCIMENTO_DESACELERADO; DECLINIO; DECLINIO_ACELERADO; DECLINIO_DESACELERADO; SEM_CLASSIFICACAO | Rótulos de apresentação (DA-15): Crescimento; Aceleração do crescimento; Desaceleração do crescimento; Declínio; Aceleração do declínio; Desaceleração do declínio; Sem classificação. Direção derivada: CRESCIMENTO (três primeiras), DECLINIO (três seguintes), NENHUMA (SEM_CLASSIFICACAO) [C §4.3.10]. |
| DirecaoMudanca | AUMENTO; REDUCAO; SEM_MUDANCA | SEM_MUDANCA por igualdade exata (DA-14, P-17). |
| TipoContagemAgregada | UNIDADES_DISTINTAS; SOMA_DOS_COMPONENTES | UNIDADES_DISTINTAS: cada pessoa ou unidade contada uma vez no agregado; SOMA_DOS_COMPONENTES: soma das contagens ou presenças dos componentes, que pode conter dupla contagem (CAP-AGR-01). |
| FundamentoUnicidade | DEDUPLICACAO; ADITIVIDADE_AUTORIZADA; PREMISSA_DO_USUARIO | Base que permite apresentar agregado de pessoas como UNIDADES_DISTINTAS: deduplicação pelos dados, ausência de sobreposição estabelecida por metadado ou fonte autorizada, ou premissa fornecida pelo usuário (CAP-AGR-01). |
| CategoriaLimitacao | ANALITICA; TECNICA | ANALITICA acompanha o resultado; TECNICA fica na rastreabilidade (DA-22). |
| CanalEntrada | TEXTO; SELECAO_INTERFACE; CONTROLE_ESTRUTURADO | Nova solicitação analítica só pela conversação, canal TEXTO (P-18). |
| Idioma | PT; EN | DA-05. |
| CaminhoProposicaoDocumental | definicao; finalidade; natureza; entradas; parametros; precondicoes; metodo; avaliabilidade; saida; limitacoes; proibicoes; representacao; compatibilidade; privacidade; precedencia; escopo; comportamento | Vocabulário fechado de CFG-DOC (4.4.23); ausência de caminho não é um valor da enumeração. |
| IdiomaProposicaoDocumental | PT; EN | CFG-DOC (4.4.23): um registro normativo PT por id_doc; apresentação PT/EN nas formas governadas, sem registro EN duplicado. |
| TipoProposicaoDocumental | IDENTIDADE; FINALIDADE; CAPACIDADE; METODO; PRECONDICAO; LIMITACAO; PRIVACIDADE; DADOS; GOVERNANCA; OPERACIONAL; REPRESENTACAO; DESFECHO; AVALIABILIDADE | Classificação documental determinada pelo par fonte/caminho no Anexo A; sem criação de comportamento. |
| StatusSessao | ATIVA; ENCERRADA | DA-24, DA-25. |
| StatusBase | RECEBIDA; TRIADA; AGUARDANDO_CONFIRMACAO; EXAMINADA; DISPONIVEL; BLOQUEADA; DESCARTADA | Estados de preparação da entrada ou base e transições de RQ-DAD-42 (DA-02, DA-27, F-08). |
| PresencaNoUniverso | PRESENTE_COM_REGISTRO; ELEGIVEL_SEM_REGISTRO; FORA_DO_UNIVERSO | [C §7.4]. |
| TipoLinha | PADRAO; CONSOLIDACAO | [C §7.6]. |
| StatusLinha | ATIVA; INATIVA; ENCERRADA | [C §7.6, §9.10]. |
| DisposicaoSinalExclusao | ATIVO; DESCARTADO_POR_CONTEXTO; INDETERMINADO | Disposição obrigatória de cada ocorrência lexical de CFG-EXC; RQ-GOV-09. |
| MotivoBloqueioBase | MATERIALIZACAO_INTEGRAL_IMPOSSIVEL; AUTORIZACAO_NEGADA; FALHA_INTEGRIDADE | Causas fechadas de BLOQUEADA; somente AUTORIZACAO_NEGADA admite reversão explícita na mesma sessão ativa, que abre novo ciclo de confirmação sem reativar autorização ou derivados anteriores (RQ-DAD-42). |
| PapelPlanilha | DADOS_ANALITICOS; FONTE_AUXILIAR_DE_METADADOS | Seleção explícita, triagem e escopo próprios; papel não determina combinação. |
| MotivoEncerramentoSessao | ENCERRAMENTO_EXPLICITO; INATIVIDADE | Controle estruturado ou intervalo de 1.800 segundos sem interação efetiva do usuário. |
| DetalheBloqueio | QUADRO_UNIVERSO_AUSENTE | Complemento estrutural de BLQ-DAD; não pertence a MotivoNaoAvaliavel nem a DetalheMotivo. |
| TipoOcorrenciaEntregavel | RETIRADA_PELO_USUARIO | Ocorrência de escopo, sem novo StatusEntregavel; preserva estado histórico. |
| StatusExecucaoElemento | CONCLUIDO; NAO_EXECUTAVEL; INTERROMPIDO | Situação terminal de ResultadoElemento: INTERROMPIDO quando a execução do próprio elemento começou e falhou operacionalmente; NAO_EXECUTAVEL quando o elemento não pôde executar porque dependência efetiva falhou ou ficou sem condição, com DEPENDENCIA_NAO_AVALIAVEL e causa-raiz (RQ-RES-04, RQ-ORQ-14). |
| TipoInteracaoUsuario | ENVIO_MENSAGEM; UPLOAD; ESCOLHA_ARQUIVO; ESCOLHA_PLANILHA; CONFIRMACAO; ALTERACAO_FILTRO_ANALITICO; ALTERACAO_SELECAO_ANALITICA; MUDANCA_PARAMETRO; NAVEGACAO_CONTROLE_EFETIVO; REVELACAO_EXPLICITA; SOLICITACAO_RELATORIO; EXPORTACAO | Catálogo fechado de EV-INTERACAO_USUARIO que renova o prazo de inatividade da sessão, quando observável pela aplicação (CFG-OPR, RQ-FLX-17). |
| ConsequenciaExclusao | BLOQUEAR_NAO_EXECUTAR; AGUARDAR_ESCLARECIMENTO_OU_CONFIRMACAO; PROSSEGUIR_COM_LIMITACAO; DESCARTADO_POR_CONTEXTO | Consequência normativa de cada ocorrência registrada de CFG-EXC; entre consequências incompatíveis prevalece a ordem listada, sem precedência pelo número da EXC (RQ-GOV-09). |

### 3.2. Entidades

```text
Sessao
  id: Id
  inicio: Timestamp; fim: Opcional<Timestamp>
  ultima_interacao_efetiva: Timestamp — instante do último EV-INTERACAO_USUARIO válido (session_id, tipo: Enum<TipoInteracaoUsuario>, timestamp)
  expira_em: Timestamp — ultima_interacao_efetiva + session_inactivity_timeout
  session_inactivity_timeout: Inteiro — 1800 segundos, CFG-OPR
  motivo_encerramento: Opcional<Enum<MotivoEncerramentoSessao>>
  geracao_sessao: Id — validade de toda operação concorrente; encerramento invalida retornos tardios
  status: Enum<StatusSessao>
  idioma: Enum<Idioma> — RQ-FLX-18
  snapshot_config: Id — fixo durante toda a sessão (RQ-CFG-03)
  aviso_de_sessao_temporaria_exibido: Booleano — RQ-FLX-19
  bases, linhas: Lista<Id>

Ancora
  id: Id
  tipo_fonte: Enum<TipoFonte>
  subtipo: Opcional<Enum<SubtipoManifestacao>>
  referencia: Texto — localizador verificável: base+versão+campo+chave; item CFG+versão, inclusive ProposicaoDocumental.id_doc existente no registro vigente de CFG-DOC;
              evento de manifestação; resultado+caminho interno; chave operacional admitida
  valor_canonico: Opcional<Texto>
  trecho_origem_e_correspondencia: Opcional<{localizador, regra, versao}> — obrigatório na estruturação conversacional; preserva também a associação entre valores, entidades e períodos
  recuperada_de: Opcional<Ref<LinhaAnalitica>> — uso a partir do estado; a referência original é preservada
  validacao: Enum<VALIDA, INVALIDA> + motivo

Solicitacao
  id, sessao_id: Id
  linha_id: Opcional<Id>
  mensagens: Lista<Ref<Evento>>
  canal: Enum<CanalEntrada>
  idioma: Enum<Idioma>
  tipos_pedido: Lista<Enum<TipoPedido>> — união das funções das partes, sem exclusividade
  partes: Lista<ParteSolicitacao{id, trecho, funcoes: Lista<Enum<TipoPedido>>, pertinencia, admissibilidade, desfecho_admissao}>
  interpretacao: Opcional<Ref<InterpretacaoOperacional>>
  plano: Opcional<Ref<PlanoComposicao>>
  entregaveis: Lista<Ref<Entregavel>> — histórico da sessão
  escopo_vigente: Ref<EscopoSolicitacao>
  versoes_escopo: Lista<Ref<EscopoSolicitacao>>
  espera_E1: Opcional<{mensagem_sanitizada, captura_selecao, evento_indisponibilidade}>
  pendencias: Lista<Ref<Pendencia>>
  status: Enum<StatusSolicitacao>

LeituraMinima (saída de FN-INT-01)
  tipos_pedido: Lista<Enum<TipoPedido>>
  proposta_dados: Opcional<{tipo: Enum<TipoDadoConversacional>, registros, dimensoes_constantes,
                   ancoras_por_celula_e_relacao, padrao_associacao}> — seção 5.8 (RQ-DAD-40, RQ-DAD-41)
  partes: Lista<{
    trecho: Texto
    funcoes: Lista<Enum<TipoPedido>>
    objeto_declarado: Texto
    setor_declarado: Enum<FTS, OUTRO_SETOR, NAO_RELACIONADO, INDETERMINADO>
    elementos: Lista<{expressao, tipo: Enum<CATEGORIA, TERRITORIO, PERIODO, INDICADOR, PARAMETRO, OPERACAO, OUTRO>,
                      candidato: Opcional<Ref elemento existente em fonte autorizada>}>
    familias_candidatas: Lista<FAM-nn>
    indicios_exclusao: Lista<{sinal, exclusao: EXC-nn, ancora: Ref<Ancora>, disposicao: Enum<DisposicaoSinalExclusao>, consequencia: Enum<ConsequenciaExclusao>, justificativa_contextual_estruturada, resultado_rechecagem}> — uma entrada por ocorrência detectada; várias podem estar ativas
    referencias_contextuais: Lista<{expressao, alvo: Ref elemento do estado}>
  }>

InterpretacaoOperacional
  id, solicitacao_id: Id
  origem: Enum<FN_INT_02, ATUALIZACAO_POR_RESPOSTA_ESTRUTURADA>
  linha: {acao: Enum<CONTINUAR, ABRIR, RETOMAR>, linha_id: Opcional<Id>, objetivo_local: Opcional<Texto>}
  entregaveis: Lista<EntregavelInterpretado{
    id, descricao, familia: FAM-nn, capacidades_candidatas: Lista<CAP-xxx-nn>,
    objeto: {indicador, categorias, universo: DefinicaoUniverso, periodos},
    modo_territorial: Enum<ModoTerritorial>,
    parametros: Lista<{nome, valor, unidade_escala, ancora: Ref<Ancora>}>,
    criterios: Lista<CriterioAtomico ou CriterioComposto>,
    relacoes_pretendidas: Lista<{relacao, operandos, referencia_opcional, alcance, ancora_intencao}> — entre objetos e/ou contra referência, sem percentual ou ranking implícito,
    identidade_semantica: {objetivo_terminal, conteudo_necessario, dependencias, resultados_autonomos_solicitados, fundamento_autonomia, ancora_intencao} — não derivada da decomposição técnica,
    papel_pretendido: Enum<PapelResultado>,
    depende_de: Lista<Id de entregável>}>
  alternativas: Lista<InterpretacaoAlternativa> — leituras concorrentes identificadas
  alteracoes_de_estado: Lista<{elemento, valor_novo, natureza_proposta: Enum<NaturezaAlteracao>, ancora}>
  itens_nao_resolvidos: Lista<{elemento, tipo: Enum<TipoPendencia>, pendencia_id, entregaveis_ou_partes_afetadas}>
  modo_explicitacao: Enum<ModoExplicitacao>
  assinatura_material: Hash — calculada por C-04 (seção 7.5)
  resolucoes_parametros: Lista<{elemento, fontes, candidatos_aplicaveis, restricoes, regra, valor_resolvido}> — calculada e validada por C-04 (RQ-GOV-14)

CriterioAtomico
  atributo: Ref (campo autorizado, caminho de resultado estruturado existente ou RefSaidaEsperada)
  operador: Enum definido em CFG-MET (CAP-SUB-01)
  valor: Decimal, código categórico ou lista de códigos
  unidade_escala: Opcional<Texto>
  ancora_valor: Ref<Ancora>

CriterioComposto
  operador_logico: Enum<OperadorLogico>
  operandos: Lista<CriterioAtomico ou CriterioComposto> — um operando para NAO; dois ou mais para E e OU

DefinicaoUniverso
  forma: Enum<LISTA, CONDICAO, AGRUPAMENTO, QUADRO_COMPLETO>
  especificacao: lista de unidades, condição estruturada, agrupamento autorizado ou quadro
  ancora: Ref<Ancora>

Entregavel
  id, solicitacao_id, descricao, familia
  papel: Enum<PapelResultado> — atribuído na autorização
  etapas: Lista<Ref<Etapa>> — uma ou várias etapas para o mesmo entregável semântico; sua quantidade não define o atendimento
  identidade_semantica: {objetivo, unidades_ou_relacoes_solicitadas, ancora_intencao} — validada em RQ-GOV-28, preservada sob decomposições técnicas equivalentes
  status: Enum<StatusEntregavel>
  desfecho: Opcional<Enum<Desfecho>>
  resultado: Opcional<Ref<ResultadoEstruturado>>
  elementos: Lista<ResultadoElemento> — por unidade semântica independente do entregável composto; o estado agregado deriva deles (RQ-RES-04)
  cobertura_elementos: {validos, falhos, nao_avaliaveis} — contagens derivadas de elementos, sem confundir falha com não avaliabilidade
  causas_impedimento: Lista<{desfecho: Enum<Desfecho>, verificacao_ou_evento, elementos_afetados, dependencias_origem}> — causas efetivamente registradas, sem produzir resultado fictício

EscopoSolicitacao
  id, solicitacao_id, versao, evento_origem
  entregaveis_vigentes: Lista<Ref<Entregavel>> — pode ser vazia por retirada total D17-A
  retiradas: Lista<{entregavel, tipo: Enum<TipoOcorrenciaEntregavel>, ancora_usuario, estado_preservado, versao_anterior}>
  status_apurado: Enum<StatusSolicitacao> — por versão; não apaga apuração anterior
  consumidores: Lista<{entregavel, etapa_ou_unidade, pendencia}> — vínculos efetivos, inclusive compartilhados

VinculoResultadoSolicitacao
  resultado_id, solicitacao_id, entregavel_id, versao_escopo
  vigente_no_escopo: Booleano
  ocorrencia_retirada: Opcional<Ref<Evento>> — separada de VinculoResultadoLinha; retirada não invalida resultado nem outros consumidores

RefSaidaEsperada
  etapa_id, unidade_id_opcional, caminho_saida, dependencias_efetivas
  verificacao_desfecho: Ref<Evento> — ausência definitiva de saída, sem criar ResultadoEstruturado

CausaOrigem
  etapa: Ref<Etapa>; unidade: Opcional<Ref<UnidadeExecucao>>; evento: Ref<Evento>
  desfecho: Enum<Desfecho>; motivo: Opcional<Enum<MotivoSemCapacidade>>
  detalhe_bloqueio: Opcional<Enum<DetalheBloqueio>>
  causas_anteriores: Lista<Ref<CausaOrigem>> — grafo acíclico; não converte causa operacional em motivo analítico

UnidadeExecucao
  id, etapa_id, identidade_semantica, elemento_ou_relacao_ou_operando
  status: Enum<StatusEtapa>; tentativas: Inteiro; chave_idempotencia
  dependencias_efetivas, consumidores_efetivos
  saida: Opcional<Ref<ResultadoEstruturado>>; causas: Lista<Ref<CausaOrigem>>
  verificacoes, autorizacao, eventos — mesmas regras de etapa; orçamento por identidade semântica

CapturaSelecaoInterface
  id, sessao_id, mensagem_id, instante: Timestamp
  tipo_fonte: MANIFESTACAO_USUARIO; subtipo: SELECAO_DE_INTERFACE
  valores_selecionados, escopo, ancora — snapshot imutável no envio; não acrescenta operação

ResultadoElemento
  elemento_id: Id — identidade semântica estável do elemento, relação ou operando no entregável
  entregavel_id: Id; unidade_execucao: Opcional<Ref<UnidadeExecucao>>
  status_execucao: Enum<StatusExecucaoElemento> — registrado quando o elemento atinge situação terminal
  condicao_avaliabilidade: Opcional<Enum<Avaliabilidade>> — ausente somente em INTERROMPIDO
  motivo_nao_avaliavel: Opcional<Enum<MotivoNaoAvaliavel>> — DEPENDENCIA_NAO_AVALIAVEL em NAO_EXECUTAVEL por dependência
  causa_raiz_ref: Opcional<Ref<CausaOrigem>> — obrigatória em NAO_EXECUTAVEL e INTERROMPIDO
  resultado_ref: Opcional<{resultado: Ref<ResultadoEstruturado>, caminho}> — somente em CONCLUIDO
  limitacoes: Lista<{tipo, categoria: Enum<CategoriaLimitacao>, dados_estruturados}>

ContextoDeMedida
  objeto_comparado: Ref — operandos da relação ou atributo do critério a que se aplica
  indicador: Ref — item de CFG-IND ou atributo autorizado comparado
  unidade: Texto — unidade de medida do valor canônico
  denominador: Opcional<{definicao, periodo}> — quando o indicador for razão
  escala_apresentacao: Opcional<{escala, nivel: Enum<INDICADA_PELO_USUARIO, CONFIGURADA, FALLBACK_POR_1000>, ancora}> — precedência de RQ-REP-01
  origem: Ref<Ancora> — estado, parâmetro, configuração ou regra que o determina

OpcaoAutorizada
  id: Id — estável, <conjunto>.<valor>
  conjunto_id: Ref<ConjuntoOpcoesAutorizadas>
  valor: valor estruturado — valor enumerado, código de contrato, RefEscopo ou Ref<InterpretacaoAlternativa>
  rotulo_pt, rotulo_en: Texto — rótulos governados (seção 4.4.11); nunca código interno, texto do LLM ou tradução em runtime
  ancora: Ref<Ancora>

ConjuntoOpcoesAutorizadas
  id: Id — fonte normativa que define o conjunto ou conjunto dinâmico identificado na pergunta
  origem: Enum<ENUMERACAO, CONTRATO, CFG_AMB, INTERPRETACAO_CONCORRENTE, OPERACIONAL> — origens admitidas por CFG-OPC
  opcoes: Lista<OpcaoAutorizada> — ordem governada
  fonte_rotulos: Ref<ProposicaoDocumental.id_doc>, texto fixo de CFG-TPL/CFG-PRV ou valores/aliases dos objetos referidos
  pergunta_id: Opcional<Id>

RefEscopo
  tipo: Enum<SOLICITACAO, LINHA, ENTREGAVEL, OBJETO, ENTRADA, BASE, CAMPO, ARQUIVO, PLANILHA, PENDENCIA>
  id: Id; versao: Opcional<Id>
  rotulo_pt, rotulo_en: Texto — alias de privacidade, valor autorizado não protegido do objeto ou forma governada; idênticos quando provenientes dos dados; nunca original protegido
  ancora: Ref<Ancora>

InterpretacaoAlternativa
  id: Id — estável na pergunta
  leitura: elementos estruturados da leitura concorrente validada por C-04
  assinatura_material: Hash — distinta das demais alternativas (RQ-GOV-16/17)
  elementos_distintivos: Lista<{elemento, valor, rotulo_pt, rotulo_en}> — rótulos governados de cada elemento distintivo
  rotulo_pt, rotulo_en: Texto — composição determinística por C-02/C-11 (seção 4.4.11)
  ancoras: Lista<Ref<Ancora>>

PlanoComposicao
  id, versao, solicitacao_id
  origem: Enum<PROPOSTO_LLM, REPLANEJADO>
  etapas: Lista<Ref<Etapa>>
  arestas: Lista<{de, para, tipo: Enum<ENTRADA, UNIVERSO, CONDICAO>, partes_ou_operandos_necessarios}> — dependências efetivas, sem exigência de completude não prevista no contrato
  entregavel_por_etapa: Lista<{etapa, entregavel}> — referencia entregáveis semânticos já validados; uma ou várias etapas não mudam sua identidade
  hash: Hash

Etapa
  id, plano_id, capacidade_id, versao_capacidade
  metodo: Opcional<{id, versao}>
  parametros: Lista<{nome, valor, unidade_escala, ancora, classe_autoridade}>
  entradas: Lista<Ref<Etapa ou ResultadoEstruturado>>
  papel: Enum<PapelResultado>
  status: Enum<StatusEtapa>
  unidades: Lista<Ref<UnidadeExecucao>> — menor unidade semântica independente; agrupamento físico não altera estados
  chave_execucao: Opcional<Hash>
  verificacoes_avaliacoes: Lista<{elemento_ou_relacao_ou_no, estado, motivo, ancoras, dependencias}> — registros efetivamente produzidos, preservados também sem ResultadoEstruturado
  ocorrencias_operacionais: Lista<Ref<Evento>> — tentativa de síntese não altera estados de etapas analíticas concluídas

ContextoConsistencia
  id
  bases: Lista<{base_id, versao, hash}>
  mapeamentos: Lista<{mapeamento_id, versao}>
  regras_longitudinais_territoriais: Lista<{chave, significado, status: Enum<StatusSignificado>, origem, ancora, bases_versoes_esquemas, periodos, unidades, excecoes}> — somente regras aplicáveis e efetivamente utilizadas (CFG-TER)
  universos: Lista<{definicao: DefinicaoUniverso, hash}>
  snapshot_config: Id
  itens_config_relevantes: Lista<{item, versao}>
  parametros_substantivos: Lista<{nome, valor, ancora}>
  versoes_capacidades: Lista<{capacidade_id, versao}>
  entradas_comparadas: Lista<{resultado_id, contexto_origem_id, diferencas, dimensoes_comparadas, verificacao_compatibilidade}> — RQ-ORQ-13, quando aplicável
  hash: Hash

Autorizacao
  id, tipo: Enum<TipoAutorizacao>
  plano_id, plano_hash, contexto_id: opcionais — obrigatórios para ANALITICA
  entrada_habilitada: Opcional<{entrada_id, hash_original, base_id_opcional, versao_opcional, evento_introducao, snapshot_config, operacoes_permitidas}> — obrigatório para HABILITADORA; base/versão vinculadas após materialização
  etapas: Lista<Id> — etapa CAP-EXA-01 identificada também na via HABILITADORA
  papeis: Lista<{etapa, papel}>
  verificacoes: Lista<{etapa, item, resultado, detalhe}> — itens 1 a 12 para ANALITICA; controles de RQ-DAD-34 para HABILITADORA
  decisoes_usuario: Lista<Ref<Evento>>
  estado: Enum<ATIVA, SUSPENSA, REVOGADA, CONSUMIDA>
  emitida_em: Timestamp

ResultadoEstruturado (conteúdo imutável)
  id, capacidade_id, versao_capacidade, metodo, etapa_id
  solicitacao_id, linha_origem_id: opcionais — ausentes no exame automático
  chave_execucao, contexto_id: opcionais — contexto e chave analíticos obrigatórios na via ANALITICA
  autorizacao_id: Id — também no exame automático, vinculado à entrada habilitada
  entradas: Lista<{ref, hash}>
  parametros: Lista<{nome, valor, unidade_escala, ancora}>
  universo: {definicao, membros: Lista<{unidade, presenca: Enum<PresencaNoUniverso>}>}
  elementos: Lista<{elemento, valores, classe, avaliabilidade, motivo, detalhe: Opcional<Enum<DetalheMotivo>>}>
  conteudo: estrutura específica do contrato (valores, relações, conjuntos, ordenações, classificações)
  relacoes_comparativas: Opcional<Lista<{relacao, operandos, sentido, avaliabilidade, motivos, referencias_resultados_ou_bloqueios, alcance}>> — CAP-CMP-01; cobertura de objetos distinta do alcance das relações
  arvores_criterios: Opcional<Lista<{elemento, raiz, nos: Lista<{no, condicao, operador, atributo_ou_caminho, parametros, estado: Enum<CondicaoCriterio>, operandos, motivos: Lista<Enum<MotivoNaoAvaliavel>>, causas_origem: Lista<Ref<CausaOrigem>>, saida_esperada: Opcional<RefSaidaEsperada>, ancoras}>}>> — CAP-SUB-01; motivos específicos nas folhas e DEPENDENCIA_NAO_AVALIAVEL no composto indeterminado
  suporte_agregado: Opcional<Lista<{periodo, membros_previstos, membros_incluidos, membros_nao_avaliaveis,
                    chaves_numerador, chaves_denominador, correspondencias, tipo_contagem, fundamento_unicidade}>> — CAP-AGR-01; sem identificadores pessoais
  cobertura_referencias: Opcional<Lista<{unidade, referencias_autorizadas, referencias_avaliaveis,
                        referencias_nao_avaliaveis_com_motivo, minimo_completo, minimo_avaliaveis}>> — CAP-ESP-02
  coorte_conjunto: Opcional<{componentes_solicitados, avaliabilidade_conjunto,
                    causas: Lista<{alvo: Ref<conjunto ou componente>, motivo: Enum<MotivoNaoAvaliavel>,
                                   detalhe: Opcional<Enum<DetalheMotivo>>}>}>
                    — obrigatório para taxa de conjunto de CAP-ROT-01; preserva todas as causas aplicáveis,
                      sem eleger prioridade entre motivos; motivo do conjunto referencia essa lista quando plural;
                      componentes avaliáveis separados não redefinem componentes_solicitados
  cobertura: {n_universo, n_avaliaveis, n_nao_avaliaveis_por_motivo, n_fora_do_universo}
  desfecho: Enum<Desfecho>
  limitacoes: Lista<{tipo, categoria: Enum<CategoriaLimitacao>, dados_estruturados, elementos_afetados}>
  exclusoes: Lista<{elemento, motivo}>
  hash_conteudo: Hash
  criado_em: Timestamp

StatusResultado (registro separado, com histórico)
  resultado_id, validade, reproducao, apresentabilidade, motivo, evento

VinculoResultadoLinha
  resultado_id, linha_id
  papel: Enum<PapelResultado>
  vigencia: Enum<Vigencia>
  motivo_nao_vigencia: Opcional<{tipo: Enum<MotivoNaoVigencia>, causa: Ref<AlteracaoEstado> ou Ref<Solicitacao>}>
                       — caráter histórico somente com SUBSTITUICAO_DE_ESTADO (RQ-LIN-20)
  historico_de_papel: Lista<{papel, evento}>

LinhaAnalitica (existe somente durante a sessão)
  id, tipo: Enum<TipoLinha>, status: Enum<StatusLinha>
  objetivo_local: Texto estruturado, com âncora da manifestação do usuário
  linhas_origem: Lista<Id> — somente para CONSOLIDACAO
  estado_atual: Ref<EstadoLinha>

EstadoLinha (versão incremental)
  linha_id, versao
  bases_em_uso: Lista<{base_id, versao}>
  universos: Lista<DefinicaoUniverso>
  recorte_corrente: Lista<{dimensao: Enum<DimensaoRecorte>, valor, parametro: Ref<ParametroDecisao>}> — RQ-LIN-19
  parametros_e_decisoes: Lista<Ref<ParametroDecisao>>
  vinculos: Lista<Ref<VinculoResultadoLinha>>
  limitacoes_conhecidas, dependencias
  pendencias_abertas: Lista<Ref<Pendencia>>

ParametroDecisao
  id
  tipo: Enum<PARAMETRO, DECISAO, ESCLARECIMENTO_DE_INTENCAO, VALOR_FACTUAL, SUBSTITUICAO,
             CRITERIO_NORMATIVO, DECLARACAO_DE_CATEGORIA, ESCALA_DE_APRESENTACAO, PREMISSA_FACTUAL>
  valor, unidade_escala, ancora
  escopo: {solicitacao_id: Opcional<Id>, linha_id: Opcional<Id>, indicador, categorias, universo, periodos, objeto_especifico}
          — para VALOR_FACTUAL complementar, objeto_especifico e dimensões factuais originais identificam o objeto;
            solicitacao_id e linha_id registram a associação aplicável na manifestação, quando existente, e não são
            preenchidos por apropriação posterior do valor fornecido sem linha; consultas não alteram âncora ou escopo
          — sem indicação explícita, segue RQ-LIN-07, RQ-LIN-19 e RQ-LIN-21; o valor sem linha é referenciável
            por qualquer linha compatível da sessão, sem transferência, exclusividade ou nova origem factual
  dimensao_recorte: Opcional<Enum<DimensaoRecorte>> — presente quando o elemento é dimensão do recorte
  pendencia_de_origem: Opcional<Ref<Pendencia>> — escopo herdado da pendência resolvida (RQ-LIN-19)
  classe_autoridade, validade, ativo: Booleano
  criterio_normativo: Opcional<{operador, valor, unidade_escala, classificacao}> — obrigatório se tipo = CRITERIO_NORMATIVO
  valor_substituido: Opcional<Ref<Ancora>> — obrigatório se tipo = SUBSTITUICAO

Pendencia
  id, tipo: Enum<TipoPendencia>
  via: Enum<TipoAutorizacao> — ANALITICA: vinculada à solicitação e à linha quando legitimamente existente; HABILITADORA: à entrada ou base
  solicitacao_id, linha_id: Opcional<Id> — solicitacao_id obrigatório na via ANALITICA; linha_id pode estar ausente antes da criação legítima; não fabricar linha
  entrada_id, base_id: Opcional<Id> — ao menos um obrigatório na via HABILITADORA
  escopo_da_resposta: {nivel: Enum<SOLICITACAO, LINHA, OBJETO>, dimensao: Opcional<Enum<DimensaoRecorte>>, objetos}
                      — herdado pela resposta (RQ-LIN-19); OBJETO identifica entrada/base, versão, esquema, campos, períodos, unidades e exceções pertinentes; sem linha, usar OBJETO ou SOLICITACAO, sem propagação automática à linha futura
  solicitacoes_dependentes: Lista<Ref<Solicitacao>> — aguardam a mesma pendência, sem duplicata (RQ-FLX-22)
  pergunta: PerguntaEstruturada
  criada_em: Timestamp
  classe_prioridade: Opcional<Inteiro> — 1 a 4, somente na fila anterior à criação de entregáveis (RQ-FLX-01)
  status: Enum<StatusPendencia>
  resposta: Opcional<Ref<Evento>>
  motivo_encerramento: Opcional<Texto>
  dependentes_efetivos: Lista<{solicitacao, entregavel, etapa_ou_parte, condicao_afetada}> — delimita impedimento e retomada (RQ-FLX-04); entregável ausente antes de E4; resposta recebida não prova resolução validada

PerguntaEstruturada [C §12.2]
  decisao_necessaria: Texto estruturado
  influencia: Ref<ProposicaoDocumental.id_doc> ou marca DOCUMENTACAO_INSUFICIENTE
  motivo_documentado: Opcional<UsoDocumental> — somente forma governada pertinente; omitir quando inaplicável
  elementos_afetados: Lista<RefEscopo> — por alias ou rótulo governado, sem conteúdo protegido
  alternativas: Opcional<Ref<ConjuntoOpcoesAutorizadas>> — opções com rótulos governados; leitura concorrente entra como OpcaoAutorizada cujo valor referencia InterpretacaoAlternativa
  consequencia_sem_decisao: Enum<BLOQUEADO, LIMITADO, INDEFINIDO> + elementos afetados
  formato_resposta: Enum<ESCOLHA, VALOR_TIPADO, TEXTO_LIVRE>

AlteracaoEstado
  id, elemento_alterado: Ref, valor_anterior, valor_novo
  linha_id, solicitacao_id: Opcional<Id> — ao menos um alvo; retirada aponta à solicitação e à versão de escopo, sem exigir linha
  natureza: Enum<NaturezaAlteracao>, ancora_da_natureza: Ref<Ancora>
  origem: Enum<USUARIO, INGESTAO> — a configuração não muda durante a sessão (RQ-CFG-05)

Base (C-10)
  id, versao, hash, sessao_id, origem: Enum<OrigemBase>, status: Enum<StatusBase>
  motivo_bloqueio: Opcional<Enum<MotivoBloqueioBase>>
  fonte_original, ancoras, estrutura_original, normalizacoes, dimensoes_constantes, mapeamentos — originais restritos a C-10
  aliases_metadados: Lista<AliasMetadado>
  vinculo_pedido_preservado: Opcional<{mensagem_id, solicitacao_id_opcional, ancora, entrada_substituta_id_opcional}> — H3, sem interpretação fictícia
  unidade_observacao, unidades_contagem_habilitadas, identidade_deduplicacao — RQ-DAD-35
  formato_entrada: Opcional<{formato: Enum<CSV, XLSX, CONVERSA>, separador_csv, planilha_xlsx}> — RQ-DAD-43
  pendencias_habilitadoras: Lista<Ref<Pendencia>>; exame: Opcional<Ref<ResultadoEstruturado>> — RQ-DAD-42
  correspondencias_auxiliares: Lista<{bases, chaves, granularidades, cardinalidade, conflitos, regra}> — RQ-DAD-30
  origens_planilhas: Lista<{arquivo_id, arquivo_alias, planilha_id, planilha_alias, papel: Enum<PapelPlanilha>, ancora_selecao, escopo, bases_campos_destino, base_origem}> — uma origem na entrada independente; todas as origens e a regra autorizada na base combinada (RQ-DAD-43)

AliasMetadado
  entrada_id, versao, posicao_estrutural, tipo: Enum<TipoPlaceholder>, alias
  original_restrito_C10: Opcional<Ref> — somente se necessário à linhagem; nunca enviado ao LLM
  papel, ancora_papel, escopo — alias não afirma que o original é pessoal

CampoProtegido
  base_id: Opcional<Id>
  campo_ou_trecho: Texto — também localiza conteúdo protegido da mensagem antes da materialização da base
  protecao: Enum<ProtecaoCampo>
  indicios: Lista<Enum<NOME, PADRAO_ESTRUTURAL, METADADO, DECLARACAO_USUARIO, REGRA_CONFIGURADA>>
  regra_aplicada: Opcional<Ref item CFG-PRV>
  placeholder: Opcional<Texto> — forma [TIPO_n] (RQ-DAD-39); o original fica somente na guarda restrita de C-10
  natureza_entidade: Opcional<Enum<NaturezaEntidadeNominal>> — resolução de ENTIDADE_NOMINAL_AMBIGUA (RQ-DAD-38)
  confirmacao: Opcional<Ref<Evento>>
  posicao_funcional, padrao_estrutural, delimitacao_segura: registro da triagem de CFG-VOC/CFG-PRV
  escopo_tipificacao, ancora_tipificacao: opcionais — obrigatórios quando papel for estabelecido; não transferidos a contexto materialmente distinto
  escopo_linhagem: Ref — reaparições do mesmo conteúdo na linhagem permanecem protegidas até evidência positiva (RQ-DAD-39)

RCNA (entrada)
  id, evento_de_exibicao, conteudo_normalizado, tipo: Enum<VALOR, ENTIDADE, REFERENCIA_NORMATIVA, METODO, OUTRO>
```

ProposicaoDocumental — estrutura normativa completa na seção 4.4.23; integra a configuração e seu snapshot,
não o estado factual mutável da sessão.

### 3.3. Regras do modelo

- **RQ-MOD-01** — Todo elemento factual ou substantivo presente em interpretação, plano, etapa, parâmetro, decisão ou resultado DEVE possuir Âncora validada (seção 7.1). Registros de LLM não são âncoras. [T-GOV]
- **RQ-MOD-02** — O conteúdo de ResultadoEstruturado é imutável; validade, reprodução e apresentabilidade residem em StatusResultado, e papel e vigência residem em VinculoResultadoLinha, todos com histórico. A vigência no escopo da solicitação reside separadamente em VinculoResultadoSolicitacao. Retirada preserva conteúdo, estado histórico e vínculos de outros consumidores; RQ-FLX-02 apura o novo escopo. [T-DET]
- **RQ-MOD-03** — Resumos (Hash) DEVEM ser calculados sobre serialização canônica: ordem fixa de campos, números em representação exata, identificadores estáveis. [T-DET]
- **RQ-MOD-04** — As enumerações são fechadas; novos valores exigem a Parte 19. [INSP]
- **RQ-MOD-05** — Os esquemas são versionados; cada registro indica a versão do esquema. [INSP]
- **RQ-MOD-06** — Um resultado PODE ter vínculos com mais de uma linha por reuso de chave de execução (seção 9.3) ou como entrada de comparação/consolidação autorizada (RQ-ORQ-13, RQ-DIA-05); papel e vigência são avaliados por vínculo. Usá-lo como entrada não o promove a componente diagnóstico. [T-DET]
- **RQ-MOD-07** — Todo parâmetro, decisão, valor factual, substituição, declaração ou critério fornecido pelo usuário DEVE registrar origem e escopo (RQ-LIN-07) e NÃO DEVE alterar a configuração governada (DA-06, DA-07). [T-DET]

---

## Parte 4 — Configuração governada

### 4.1. Natureza e ciclo de vida

- **RQ-CFG-01** — Regras metodológicas, conceituais e de governança, métodos, capacidades e limites de autonomia DEVEM ser estabelecidos no processo externo de desenvolvimento e evolução do sistema, de forma documentada e versionada [C §5.3] (DA-01). Nem o usuário nem o LLM podem criá-los, alterá-los, suspendê-los ou substituí-los durante a interação (INV-15). [INSP][T-GOV]
- **RQ-CFG-02** — Cada item CFG DEVE ter identificador, versão imutável, conteúdo, referência ao RegistroMudanca que o originou (Parte 19) e data de efeito. Não se exige estrutura institucional de aprovação além desse registro (DA-01). [INSP]
- **RQ-CFG-03** — O snapshot vigente é fixado no início de cada sessão; toda autorização, resultado e evento da sessão DEVE referenciá-lo. [T-DET]
- **RQ-CFG-04** — Conteúdo de configuração NÃO DEVE ser originado de saída de LLM, de instruções textuais contidas em bases ou de decisões recorrentes de usuários [C §5.3, §3.6]. [INSP][T-GOV]
- **RQ-CFG-05** — A configuração permanece congelada durante toda a sessão. Nova versão publicada durante uma sessão não vale para as autorizações daquela sessão; aplica-se a novas sessões ou a mecanismo explícito de migração ou reinício, inexistente nesta versão. Decisões e parâmetros locais da análise nunca alteram a configuração global (DA-01). [T-DET][T-E2E: AT-52]
- **RQ-CFG-06** — A ausência de item CFG exigido por um contrato DEVE fazer falhar a pré-condição correspondente (BLQ-MET ou BLQ-SIG, conforme o contrato); o sistema NÃO DEVE improvisar valor padrão. [T-GOV]
- **RQ-CFG-07** — A Configuração Inicial de Implementação é a definida nesta SPEC — catálogo da seção 4.2, reconhecimento de categorias da seção 4.3 e conteúdo da seção 4.4 —, decorrente das decisões das Partes 22 e 25, e constitui o snapshot carregado em C-09 para as sessões desta versão. [INSP]
- **RQ-CFG-12** — Todo item CFG da Configuração Inicial de Implementação DEVE ter conteúdo explícito ou vazio deliberado com comportamento na ausência definido. Vazio deliberado (CFG-TER; CFG-REF; CFG-AUS quanto a métodos de imputação; CFG-NOR; e os vazios declarados dentro de outros itens) não é lacuna, não é preenchido pelo LLM, por conteúdo de bases ou por decisão do usuário e não autoriza valor padrão improvisado (RQ-CFG-06). Nenhum conteúdo exigido pela implementação desta versão permanece a elaborar. [INSP][T-GOV]

### 4.2. Catálogo de itens

| ID | Conteúdo | Uso | Decisões | Configuração Inicial de Implementação (v1.2) |
|---|---|---|---|---|
| CFG-DOM | Definição do domínio [C §3.1]; categorias de reconhecimento automático inequívoco e de reconhecimento contextual, não exaustivas, e termos genéricos ambíguos; papéis auxiliares admitidos | Pertinência; vocabulário | DA-04 | Seções 4.3 e 4.4.1: 15 categorias de reconhecimento automático, 3 de reconhecimento contextual e termos ambíguos, PT/EN; sem catálogo fechado de profissões nem de territórios; a ausência de uma categoria não a exclui da FTS |
| CFG-FAM | FAM-01 a FAM-14, descrições, notas "não abrange", mapeamento para capacidades | Admissibilidade | — | Tabela 1.3; FAM-08 inclui CAP-ROT-01; nenhuma nova família (4.4.2) |
| CFG-EXC | EXC-01 a EXC-11, descrições e sinais lexicais em português e inglês | Admissibilidade | DA-05 | Tabela 1.4 e padrões PT/EN da seção 4.4.3, como sinais de rechecagem, nunca de recusa automática |
| CFG-CAP | Registro de capacidades: contrato, versão, status | Disponibilidade | — | Catálogo 8.3, com CAP-ROT-01 (4.4.4) |
| CFG-MET | Métodos versionados: fórmulas, critérios, operadores, convenções, algoritmo geodésico, conjunto de referenciais geodésicos suportados, sem referencial padrão | Execução | DA-11 a DA-19 | Métodos da Parte 8; problema geodésico inverso pelo algoritmo de Karney; método de CAP-ROT-01; nenhum referencial padrão, global ou por contexto; nenhuma transformação entre referenciais (4.4.5) |
| CFG-IND | Definição operacional de indicadores: numerador, denominador, unidades de observação e de contagem admitidas, identidade de deduplicação, composição do denominador por dimensão agregada, alinhamento temporal, escala canônica e escala de apresentação configurada | CAP-IND-01, CAP-IND-02, CAP-AGR-01, CAP-ROT-01 | DA-09, F-02 | Quantitativo absoluto, densidade, ROTATIVIDADE_COORTE_INICIAL e PERMANENCIA_COORTE_INICIAL; nenhuma escala configurada por indicador, valendo por 1.000 habitantes para densidade (4.4.6) |
| CFG-TER | Hierarquias, correspondências e comparabilidade temporal de unidades territoriais | Agregação, mudança temporal, tendência, triagem | DA-16, F-01 | Deliberadamente vazio: nenhum catálogo de cidades ou de territórios, hierarquia, equivalência ou correspondência presumida (4.4.7) |
| CFG-REF | Conjuntos e critérios autorizados de referências territoriais | CAP-REF-01 | DA-17 | Deliberadamente vazio: referências por lista do usuário, fonte autorizada ou critério autorizado aplicado aos dados (4.4.8) |
| CFG-VOC | Vocabulários em português e inglês que ligam expressões aos mesmos conceitos internos, com aliases, variantes e regras de normalização do reconhecimento de categorias e de correspondência de cabeçalhos, operadores, conectores, marcadores e dados explícitos da conversa | Interpretação e validação | DA-04, DA-05, DA-19, F-01, F-11 | Seção 4.3 e grupos PT/EN da seção 4.4.9, inclusive padrões de associação, marcadores de entidade e termos de rotatividade; conceitos canônicos com aliases PT/EN equivalentes ou ausência registrada (RQ-CFG-14) |
| CFG-AMB | Gatilhos de ambiguidade em português e inglês | Seção 7.5 | DA-05 | AMB-01 a AMB-06 com formas PT/EN (4.4.10) |
| CFG-OPC | Origens admitidas de conjuntos de opções para perguntas | Perguntas | — | Sem alternativas substantivas próprias; cinco origens admitidas; conjuntos e rótulos PT/EN governados (4.4.11) |
| CFG-PRE | Regras de precedência entre fontes | Conflitos | DA-03 | Regras da seção 4.4.12 |
| CFG-AUS | Métodos autorizados de tratamento de ausência | Capacidades | DA-10 | Deliberadamente vazio quanto a imputação; exceção: valor fornecido explicitamente pelo usuário e admitido pelo contrato (4.4.13) |
| CFG-REP | Transformações formais, arredondamento, escalas, mapeamentos visuais, tipos de representação e formatos de entrega | C-11 e validador | DA-20, DA-23, F-04 | Parte 13 e regras da seção 4.4.14 |
| CFG-LEX | Léxicos do validador em português e inglês | Validador | DA-05, DA-22, F-12 | Grupos LEX-NORM, LEX-CAU, LEX-TEN, LEX-ACE, LEX-CMP, LEX-DES e LEX-HET e regra de numerais (4.4.15) |
| CFG-TPL | Modelos de mensagem do canal sistêmico em português e inglês, inclusive avisos obrigatórios | C-02 | DA-05, DA-24, DA-27 | TPL-01 a TPL-13, com TPL-04 e TPL-12 preservados em ordem governada (4.4.16) |
| CFG-REC | Autorização de recálculo espontâneo | Parte 11 | DA-08 | Nenhum recálculo espontâneo (4.4.17) |
| CFG-ESC | Regras de escopo de parâmetros e decisões | Parte 11 | DA-06, F-07 | RQ-LIN-07, RQ-LIN-19, RQ-LIN-21 e regras da seção 4.4.18 |
| CFG-NOR | Critérios normativos pré-configurados, com definição, fonte, escopo e versão | Qualificação avaliativa | DA-21 | Deliberadamente vazio; critérios do usuário são registrados na análise (RQ-GOV-31) (4.4.19) |
| CFG-LIM | Classificação e relevância das limitações | Resultados e síntese | DA-22, F-04 | Taxonomia de RQ-RES-06; heterogeneidade genérica vedada (4.4.20) |
| CFG-FON | Política de ingestão pelas duas portas, formatos, normalização e correspondência entre bases; autorização inicial restrita à habilitação (RQ-DAD-34); fontes configuradas | Parte 5 | DA-02, AV-02, AV-08, F-06, F-08 | Upload de CSV e XLSX e dados fornecidos na conversa, sem limite metodológico fixo de linhas; nenhuma fonte configurada (4.4.21) |
| CFG-PRV | Regras da triagem estrutural e de privacidade, placeholders e mascaramento; regras de anonimização ou supressão incorporadas por nova versão | Partes 5 e 18 | DA-27, F-01 | Regras da seção 4.4.22: evidência positiva para liberar conteúdo nominal; CPF com dígitos verificadores, e-mail, telefone, rótulos e padrões governados de identificadores pessoais em ordem determinística, campos de nome e de identificação, entidades nominais, pergunta de esclarecimento e placeholders; nenhum catálogo de cidades; nenhuma regra de anonimização ou limiar de supressão |
| CFG-DOC | Registro de Proposições Documentais, com identificação, extração, decomposição, classificação, condições, dependências e formas autorizadas determinísticas | Perguntas; FN-META-01; validador | F-12; remediação v1.2.1; precisão D8 em §25.8; D20, D31 e D32 em §25.9 | Seção 4.4.23, mapa do Anexo A e catálogo literal PT/EN externo Docs/CFG_DOC_CATALOG.yaml; snapshot governado; sem criação de proposições, formas ou rótulos livres durante a sessão |
| CFG-OPR | Parâmetros operacionais e chaves de informação operacional admitidas | Partes 9, 14 e 16 | DA-26 | Até 2 regenerações; até 1 nova tentativa por unidade semântica; timeout técnico distinto do timeout de sessão fixo de 1800 segundos; catálogo fechado de EV-INTERACAO_USUARIO; três chaves operacionais admitidas (4.4.24) |

### 4.3. Reconhecimento governado de categorias da FTS

- **RQ-CFG-08** — CFG-DOM e CFG-VOC DEVEM conter o vocabulário governado de categorias da Configuração Inicial de Implementação (tabelas abaixo): categorias de reconhecimento automático inequívoco, cuja pertença à FTS é reconhecida sem pergunta; categorias de reconhecimento contextual, identificadas por alias governado, mas cuja pertença exige âncora contextual autorizada; e termos genéricos ambíguos. Esse vocabulário não é catálogo fechado de profissões nem de territórios, não é exaustivo, não exclui categorias ausentes, não autoriza inferência pelo LLM, serve apenas para reconhecer os casos nele autorizados e só muda por nova versão da configuração (RQ-CFG-01, RQ-CFG-05). A ausência de uma categoria significa apenas que sua pertença não pode ser estabelecida por essa via, permanecendo as demais vias de RQ-DAD-19 (DA-04). [INSP][T-GOV]
- **RQ-CFG-09** — O reconhecimento, aplicado às expressões da solicitação e aos rótulos de categorias das bases, resulta em: FTS_INEQUIVOCA, quando a expressão completa corresponde, após a normalização de RQ-CFG-10, a alias de uma única categoria de reconhecimento automático, e então a pertença fica estabelecida com âncora em CONFIGURACAO_GOVERNADA, sem pergunta ao usuário; FTS_CONTEXTUAL, quando a expressão completa corresponde a alias de uma única categoria de reconhecimento contextual, caso em que a categoria fica identificada, mas a pertença à FTS só se estabelece por fonte ou metadado autorizado, declaração de domínio da base, contexto autorizado suficiente — elemento ancorado em fonte autorizada ou em estado válido e aplicável que estabeleça, no escopo, que a categoria integra a FTS — ou declaração explícita do usuário, e, sem essa âncora, a pertinência fica PERTINENCIA_INCERTA e segue o esclarecimento, nunca NAO_PERTINENTE por esse motivo; FTS_AMBIGUA, quando a expressão corresponde a termo genérico registrado como ambíguo ou a mais de uma categoria, caso em que se usam metadados, declaração de domínio ou contexto autorizado — o contexto da base resolve quando nela houver uma única categoria candidata segundo as correspondências governadas de CFG-DOM e CFG-VOC e as regras determinísticas de RQ-CFG-10, e categoria apenas semanticamente parecida, sem essa correspondência, não resolve — e, persistindo mais de uma leitura materialmente plausível ou nenhuma candidata governada, pede-se esclarecimento; NAO_RECONHECIDA, nos demais casos, em que a pertença depende das outras vias de RQ-DAD-19. NAO_RECONHECIDA não significa NAO_PERTINENTE (DA-04). [T-DET][T-E2E: AT-55, AT-56, AT-57, AT-88]
- **RQ-CFG-10** — A correspondência é determinística e usa regras governadas de normalização: caixa; espaços; hífens e separadores; acentuação para fins de correspondência; variantes de gênero cadastradas; singular e plural cadastrados ou tratados por regra governada; aliases e sinônimos registrados em CFG-VOC. Considera-se a expressão completa que designa a categoria; parte de expressão mais longa não basta (ex.: "médico" em "médico veterinário"). Correspondência aproximada, similaridade vetorial ou semelhança semântica não estabelecem pertença; servem apenas para indicar necessidade de esclarecimento ou apoiar proposta de correspondência com alias existente, sujeita a validação determinística. [T-DET][T-E2E: AT-55]
- **RQ-CFG-11** — O LLM PODE interpretar a expressão do usuário, propor correspondência com categoria ou alias já existente em CFG-DOM e CFG-VOC, identificar possível ambiguidade e redigir pergunta de esclarecimento. O LLM NÃO DEVE decidir, por conhecimento latente, que nova profissão ou ocupação pertence à FTS; criar aliases ou equivalências; transformar NAO_RECONHECIDA ou FTS_CONTEXTUAL em pertença estabelecida; nem ampliar a configuração. Ambiguidade apontada pelo LLM pode levar a esclarecimento, nunca a reconhecimento automático; a decisão de reconhecimento é de C-04 (DA-04). [T-GOV]
- **RQ-CFG-13** — Os aliases ACS e ACE só produzem reconhecimento quando a expressão completa ou o contexto autorizado não produzir outra leitura materialmente plausível; havendo outra, aplica-se o esclarecimento de RQ-CFG-09. [T-DET][T-E2E: AT-88]

Categorias de reconhecimento automático inequívoco (FTS_INEQUIVOCA):

| Categoria interna | Português | Inglês |
|---|---|---|
| MEDICINA | médico; médica; médicos; médicas; medicina; profissional médico; profissional médica | physician; physicians; medical doctor; medical doctors; medicine |
| ENFERMAGEM | enfermeiro; enfermeira; enfermeiros; enfermeiras; enfermagem | nurse; nurses; nursing |
| ODONTOLOGIA | dentista; dentistas; cirurgião-dentista; cirurgiã-dentista; cirurgiões-dentistas; odontólogo; odontóloga; odontologia | dentist; dentists; dentistry |
| FARMACIA | farmacêutico; farmacêutica; farmacêuticos; farmacêuticas; farmácia | pharmacist; pharmacists; pharmacy |
| FISIOTERAPIA | fisioterapeuta; fisioterapeutas; fisioterapia | physiotherapist; physiotherapists; physical therapist; physical therapists; physiotherapy; physical therapy |
| TERAPIA_OCUPACIONAL | terapeuta ocupacional; terapeutas ocupacionais; terapia ocupacional | occupational therapist; occupational therapists; occupational therapy |
| FONOAUDIOLOGIA | fonoaudiólogo; fonoaudióloga; fonoaudiólogos; fonoaudiólogas; fonoaudiologia | speech therapist; speech therapists; speech-language pathologist; speech-language pathologists; speech-language pathology; speech therapy |
| NUTRICAO | nutricionista; nutricionistas; nutrição | nutritionist; nutritionists; nutrition |
| BIOMEDICINA | biomédico; biomédica; biomédicos; biomédicas; biomedicina | Nenhum alias automático nesta versão (vazio deliberado) |
| TECNICO_ENFERMAGEM | técnico de enfermagem; técnica de enfermagem; técnicos de enfermagem; técnicas de enfermagem | nursing technician; nursing technicians |
| AUXILIAR_ENFERMAGEM | auxiliar de enfermagem; auxiliares de enfermagem | nursing assistant; nursing assistants |
| TECNICO_RADIOLOGIA | técnico em radiologia; técnica em radiologia; técnico de radiologia; técnica de radiologia | radiology technician; radiology technicians; radiologic technologist; radiologic technologists |
| AGENTE_COMUNITARIO_SAUDE | agente comunitário de saúde; agentes comunitários de saúde; ACS (RQ-CFG-13) | community health worker; community health workers |
| AGENTE_COMBATE_ENDEMIAS | agente de combate às endemias; agentes de combate às endemias; ACE (RQ-CFG-13) | endemic disease control agent; endemic disease control agents |
| PSICOLOGIA | psicólogo; psicóloga; psicólogos; psicólogas; psicologia | psychologist; psychologists; psychology |

Categorias de reconhecimento contextual (FTS_CONTEXTUAL; a pertença exige âncora contextual autorizada, RQ-CFG-09):

| Categoria interna | Português | Inglês |
|---|---|---|
| SERVICO_SOCIAL | assistente social; assistentes sociais; serviço social | social worker; social workers; social work |
| EDUCACAO_FISICA | profissional de educação física; profissionais de educação física; educação física | physical education professional; physical education professionals; physical education |
| VETERINARIA | veterinário; veterinária; veterinários; veterinárias; medicina veterinária | veterinarian; veterinarians; veterinary medicine |

Termos genéricos ambíguos (FTS_AMBIGUA quando usados isoladamente): técnico; técnica; técnicos; técnicas; auxiliar; auxiliares; agente; agentes; profissional; profissionais; especialista; especialistas; terapeuta; terapeutas; atendente; atendentes; gestor; gestora; gestores; gestoras; coordenador; coordenadora; coordenadores; coordenadoras; supervisor; supervisora; supervisores; supervisoras; technician; technicians; assistant; assistants; agent; agents; professional; professionals; specialist; specialists; therapist; therapists; attendant; attendants; manager; managers; coordinator; coordinators; supervisor; supervisors.

Expressões inglesas equivalentes a BIOMEDICINA e quaisquer outras expressões ausentes das tabelas seguem as demais vias de RQ-DAD-19 e, quando necessário, o esclarecimento de RQ-FLX-20. Não há catálogo fechado de profissões nem catálogo de cidades ou territórios (CFG-TER, CFG-PRV).

### 4.4. Conteúdo da Configuração Inicial de Implementação

As subseções abaixo definem o conteúdo normativo dos 24 itens CFG da Configuração Inicial de Implementação, na ordem do catálogo 4.2. Cada item tem conteúdo explícito ou vazio deliberado com comportamento estabelecido (RQ-CFG-12); nenhum é semente, exemplo inicial ou conteúdo a elaborar. Alterações seguem a Parte 19 e valem apenas para novas sessões (RQ-CFG-05).

- **RQ-CFG-14** — Itens lexicais governados funcionalmente relevantes — vocabulários, léxicos, gatilhos, marcadores, rótulos e modelos desta seção — representam conceitos canônicos independentes do idioma e mapeiam para os mesmos conceitos internos. Cada conceito possui aliases PT e aliases EN equivalentes ou ausência deliberada explicitamente registrada no próprio item (ex.: BIOMEDICINA sem alias automático em inglês; `turnover` sem correspondência determinística); a expressão sem correspondência segue interpretação candidata e esclarecimento (RQ-CFG-15, RQ-FLX-20). Formulações semanticamente equivalentes em PT e EN DEVEM resultar na mesma decisão estrutural, como "a cidade de X tinha 10 médicos" e "the city of X had 10 physicians". [INSP][T-GOV][T-E2E: AT-43, AT-88, AT-167]
- **RQ-CFG-15** — Sinal lexical, interpretação candidata, correspondência autorizada e validação determinística são estágios distintos. Expressão fora do vocabulário pode ser interpretada pelo LLM apenas como candidato; a correspondência só se torna autorizada quando sustentada por correspondência já presente em CFG-VOC ou CFG-DOM, por fonte ou metadado autorizado, por estado válido e aplicável previamente estabelecido ou por manifestação explícita do usuário no escopo pertinente, e é confirmada por C-04. A interpretação do LLM, isoladamente, nunca cria alias, equivalência, categoria, território, unidade, período ou relação factual, e a presença lexical isolada nunca é prova substantiva quando a regra exige validação da função, da âncora ou do contexto. A identificação da intenção analítica — capacidade de CFG-CAP, indicador de CFG-IND e operação — segue a interpretação operacional validada contra esses catálogos fechados (RQ-GOV-13 a RQ-GOV-18). Selecionar planilhas de XLSX não autoriza combinação nem inferência temporal pelos nomes; aplicar RQ-DAD-43. As distinções de intenção comparativa de CFG-VOC não criam aliases de domínio ou significado factual. [T-GOV][T-E2E: AT-85, AT-88, AT-90]

#### 4.4.1. CFG-DOM — domínio e reconhecimento governado de categorias

Conteúdo: definição do domínio [C §3.1] (RQ-ESC-01, RQ-ESC-04); vocabulário de categorias da seção 4.3 — 15 categorias de reconhecimento automático inequívoco, 3 categorias de reconhecimento contextual e termos genéricos ambíguos, em português e inglês —; papéis auxiliares admitidos (denominador, atributo de ordenação, referência espacial, delimitação de universo; RQ-ESC-05). O catálogo é governado, versionado e não exaustivo; a ausência de uma categoria não significa que ela não pertença à FTS, e sua pertença pode ser estabelecida por fonte ou metadado autorizado, declaração de domínio da base ou declaração explícita do usuário no escopo aplicável (RQ-DAD-19). Categorias de reconhecimento contextual em contexto indeterminado ficam com pertinência incerta e seguem o esclarecimento, nunca NAO_PERTINENTE por esse motivo.

#### 4.4.2. CFG-FAM — famílias autorizadas

FAM-01 a FAM-14, com descrições, restrições, notas "não abrange" e mapeamentos da tabela 1.3. FAM-08 inclui CAP-ROT-01 sem alteração de sua finalidade geral nem de suas notas. Nenhuma nova família é criada.

#### 4.4.3. CFG-EXC — exclusões e sinais determinísticos de verificação

EXC-01 a EXC-11, com descrições e desfechos da tabela 1.4. Os padrões abaixo são sinais determinísticos que obrigam rechecagem da intenção e da admissibilidade (RQ-ESC-13, RQ-GOV-09); a presença do termo isolado não produz recusa automática.

| Exclusão | Português | Inglês |
|---|---|---|
| EXC-01 | buscar evidências; pesquisar evidências; buscar artigos; pesquisar artigos; revisar literatura; busca bibliográfica; revisão bibliográfica; evidência científica; evidências científicas | search evidence; evidence search; search papers; search articles; literature search; literature review; scientific evidence |
| EXC-02 | recomende; recomendar política; recomendar intervenção; sugerir intervenção; sugerir política; qual política devo usar; qual intervenção devo usar | recommend; recommend a policy; recommend an intervention; suggest an intervention; suggest a policy; which policy should I use; which intervention should I use |
| EXC-03 | causa; causou; causar; explica; explicou; devido a; em razão de; efeito de; impacto de; leva a; levou a; resulta de | cause; caused; causes; explains; explained by; due to; because of; effect of; impact of; leads to; led to; results from |
| EXC-04 | analise o PIB; analise renda; analise pobreza; analise clima; analise temperatura; analise indicador socioeconômico; analise indicador ambiental | analyze GDP; analyze income; analyze poverty; analyze climate; analyze temperature; analyze socioeconomic indicator; analyze environmental indicator |
| EXC-05 | correlação; correlacione; regressão; associação estatística; Moran; autocorrelação espacial; cluster espacial; padrão espacial | correlation; correlate; regression; statistical association; Moran; spatial autocorrelation; spatial cluster; spatial pattern |
| EXC-06 | use este relatório como base de dados; extraia os dados deste PDF para a análise; interprete este documento como fonte analítica | use this report as the dataset; extract data from this PDF for the analysis; interpret this document as an analytical source |
| EXC-07 | busque na internet; procure na web; consulte fontes externas; complete com dados externos; pesquise o valor que falta | search the internet; search the web; consult external sources; complete with external data; look up the missing value |
| EXC-08 | crie um método; invente uma fórmula; desenvolva uma fórmula nova; use um método que você achar melhor | create a method; invent a formula; develop a new formula; use whatever method you think is best |
| EXC-09 e EXC-10 | liste os profissionais; liste os trabalhadores; mostre os nomes; ranking de pessoas; ranking de profissionais; classifique os trabalhadores; diagnostique cada profissional | list the professionals; list the workers; show the names; rank people; rank professionals; classify the workers; diagnose each professional |
| EXC-11 | você decide; escolha por mim; decida por mim; use o que achar melhor; defina o critério por mim | you decide; choose for me; decide for me; use whatever you think is best; define the criterion for me |

Pedidos sem família candidata, como projeção ou previsão (Caso 4), não dependem de sinal lexical: recebem ADM-FE pelo gate de admissibilidade (RQ-GOV-08). Todo sinal lexical detectado requer disposição ATIVO, DESCARTADO_POR_CONTEXTO ou INDETERMINADO em LeituraMinima; aplicar RQ-GOV-09, sem recusa automática por palavra isolada e sem novo julgamento semântico geral por C-04. Várias exclusões podem estar ativas simultaneamente; cada uma é registrada com justificativa e consequência normativa: exclusão ATIVO com desfecho ADM-FE ou ADM-SC → BLOQUEAR_NAO_EXECUTAR; EXC-11, cuja decisão permanece pendente, e disposição INDETERMINADO → AGUARDAR_ESCLARECIMENTO_OU_CONFIRMACAO; DESCARTADO_POR_CONTEXTO → DESCARTADO_POR_CONTEXTO; PROSSEGUIR_COM_LIMITACAO somente quando a regra aplicável admitir prosseguimento com limitação registrada. O desfecho operacional deriva da consequência prevalecente, na ordem BLOQUEAR_NAO_EXECUTAR > AGUARDAR_ESCLARECIMENTO_OU_CONFIRMACAO > PROSSEGUIR_COM_LIMITACAO > DESCARTADO_POR_CONTEXTO, nunca do número da EXC; não há precedência entre EXC-08 e EXC-03 (RQ-GOV-09).

#### 4.4.4. CFG-CAP — catálogo de capacidades

Contratos, versões e status da Parte 8, com CAP-ROT-01 (catálogo 8.3). Nenhuma capacidade é criada, inferida ou emulada durante a interação (RQ-CAP-10).

#### 4.4.5. CFG-MET — métodos governados

Conteúdo: os métodos da Parte 8 — medidas de posição e quantis pelo tipo 7 de Hyndman–Fan com fronteira na classe inferior (CAP-DIS-01, CAP-DIS-02); intervalos [a, b) com último intervalo fechado (CAP-DIS-03, CAP-ESP-03); relações comparativas (CAP-CMP-01); mudança temporal (CAP-TMP-01); tendência (CAP-TEN-01); agregação (CAP-AGR-01); operadores e lógica trivalente (CAP-SUB-01); ordenação e seleção com empates (CAP-SUB-02, CAP-SUB-03); rotatividade e permanência da coorte inicial (CAP-ROT-01) — e o método geodésico abaixo. Cada capacidade tem método único e versionado; não há método alternativo parametrizável pelo usuário (RQ-CAP-13).

Método geodésico de CAP-ESP-01: distância obtida pela solução do problema geodésico inverso com o algoritmo de Karney, calculada sobre o elipsoide associado ao referencial geodésico autorizado das coordenadas; resultado em quilômetros; precisão integral no cálculo e arredondamento apenas na apresentação. SIRGAS2000 DEVE ser suportado e não é padrão universal. Não há referencial geodésico padrão, global ou por contexto, nesta versão: sem referencial informado por metadado, fonte autorizada ou usuário, a análise espacial aguarda esclarecimento (pendência REFERENCIAL_GEODESICO, RQ-DAD-26). Não há transformação entre referenciais (RQ-DAD-27). A escolha da implementação do algoritmo pertence ao plano técnico e não altera o método (RQ-DOC-06). Conjunto governado de referenciais suportados na Configuração Inicial de Implementação: {SIRGAS2000}. Essa enumeração de suporte não é um novo enum nem um referencial padrão. C-04 verifica deterministicamente pertencimento antes da operação; capacidade de biblioteca técnica ou declaração do usuário não amplia o conjunto. Referencial informado não suportado gera BLQ-MET com METODO_NAO_INCORPORADO, sem aproximação, substituição ou transformação. Pode-se informar deterministicamente a lista suportada, sem sugerir qual referencial os dados possuem; a base permanece disponível para capacidades independentes (RQ-DAD-26/27). Aliases de D24: SIRGAS2000, SIRGAS 2000, SIRGAS-2000 e SIRGAS_2000, admitindo somente variação de caixa e espaços externos; normalização determinística remove espaços externos e compara sem distinguir caixa, sem converter separadores internos adicionais. Valor canônico SIRGAS2000; elipsoide GRS80; semieixo maior a = 6378137 m; achatamento inverso 1/f = 298.257222101; f = 1 / 298.257222101. Não inferir EPSG nem ampliar o conjunto suportado.

Vazios deliberados de CFG-MET: referencial padrão; transformação entre referenciais; regra de desempate (CAP-SUB-03); método de construção de intervalos (CAP-DIS-03, CAP-ESP-03); métodos de tratamento de ausência (CFG-AUS); posição percentual numérica (CAP-DIS-01). Na ausência, aplicam-se os desfechos e pendências dos respectivos contratos.

#### 4.4.6. CFG-IND — indicadores

| Indicador | Definição operacional | Capacidade |
|---|---|---|
| QUANTITATIVO_ABSOLUTO | Q(u, p, c) pela derivação autorizada de CAP-IND-01; unidade de observação, unidade de contagem e identidade de deduplicação conforme RQ-DAD-18 e RQ-DAD-35 | CAP-IND-01, CAP-AGR-01 |
| DENSIDADE | D(u, p, c) = Q(u, p, c) / P(u, p′), com p′ = p salvo DENOMINADOR_ALTERNATIVO; valor canônico por habitante; escala de apresentação por precedência: indicada pelo usuário → configurada para o indicador (nenhuma nesta versão) → por 1.000 habitantes; sem mudança automática de escala por magnitude; denominador de agregados pela composição por dimensão de CAP-AGR-01 | CAP-IND-02, CAP-AGR-01 |
| ROTATIVIDADE_COORTE_INICIAL | (N_saidas / N0) × 100, em percentual, sobre a coorte inicial C0 de t0; unidade de contagem pessoa; unidade de observação registro individual; identidade longitudinal exigida | CAP-ROT-01 |
| PERMANENCIA_COORTE_INICIAL | (N_permanentes / N0) × 100, em percentual, sobre a mesma coorte; quando avaliáveis, as duas taxas somam 100% | CAP-ROT-01 |

As propriedades semânticas exigidas são verificadas apenas quando necessárias à capacidade executada; aditividade territorial ou categorial não é exigida em cálculo que não realize a respectiva agregação (RQ-DAD-36). As taxas de CAP-ROT-01 são percentuais por definição e não seguem a precedência de escala de apresentação da densidade. Indicador sem definição nesta tabela recebe ADM-SC NAO_INCORPORADA (seção 8.6).

#### 4.4.7. CFG-TER — território

Configuração deliberadamente vazia. Não há catálogo de cidades, catálogo mundial de territórios, hierarquia territorial presumida, equivalência territorial presumida nem correspondência temporal global presumida. Correspondência estrutural entre níveis depende de relações explicitamente fornecidas e autorizadas; sem correspondência autorizada, a agregação entre níveis recebe BLQ-MET (CAP-AGR-01). O significado longitudinal da chave territorial, simples ou composta, DEVE estar estabelecido por regra autorizada, configuração, metadado autorizado, conteúdo de fonte autorizada que efetivamente o declare ou manifestação/confirmação explícita do usuário. Mera origem autorizada do arquivo, nome do campo e repetição de códigos não estabelecem esse significado. A regra registra chave, significado, StatusSignificado, origem, âncora e escopo de bases, versões, esquemas, períodos e unidades, com exceções autorizadas. Estabelecido que a mesma chave identifica a mesma unidade nos períodos abrangidos, sua igualdade permite correspondência determinística em massa, respeitando RQ-DAD-30. Ausência desse significado quando necessário gera BLQ-SIG e pendência de campo/esquema no escopo pertinente, nunca perguntas por território; uma resposta aplicável resolve todas as correspondências abrangidas (RQ-DAD-05/06). Exceções de fusão, desmembramento, alteração territorial, definição ou esquema prevalecem somente para unidades e períodos afetados. Incompatibilidade estabelecida segue CAP-TMP-01/TEN-01 e RQ-CAP-08. Identidade territorial não dispensa compatibilidade categorial, populacional, metodológica nem suporte efetivo de CAP-AGR-01. A triagem de privacidade não usa catálogo territorial (RQ-DAD-38); identidade pessoal de RQ-DAD-35 permanece distinta.

#### 4.4.8. CFG-REF — referências territoriais

Configuração deliberadamente vazia. Referências territoriais decorrem de lista explícita do usuário, de fonte autorizada ou de critério autorizado aplicado aos dados (conjunto produzido por CAP-SUB-01). O LLM não escolhe referências por conhecimento latente. Sem nenhuma dessas origens, CAP-REF-01 gera pendência PARAMETRO_FALTANTE.

#### 4.4.9. CFG-VOC — vocabulário governado

Regra de autoridade: RQ-CFG-15. Categorias: seção 4.3. Grupos: As quatro classes de RQ-DAD-20 regem a fronteira de privacidade. Este vocabulário governa correspondências específicas; não é lista exaustiva nem filtro obrigatório de verbos, qualificadores, operadores, relações, instruções ou estrutura linguística não pessoal necessários à interpretação.

| Grupo | Português | Inglês | Uso |
|---|---|---|---|
| Cabeçalhos territoriais | território; territorio; unidade territorial; município; municipio; cidade; estado; província; provincia; distrito; região; regiao | territory; territorial unit; municipality; city; state; province; district; region | Papel TERRITORIO (RQ-DAD-29) |
| Cabeçalhos temporais | período; periodo; ano; mês; mes; data | period; year; month; date | Papel PERIODO |
| Cabeçalhos populacionais | população; populacao; habitantes | population; inhabitants | Papel POPULACAO |
| Cabeçalhos categoriais | categoria; categoria profissional; profissão; profissao; ocupação; ocupacao | category; professional category; profession; occupation | Papel CATEGORIA |
| Coordenadas | latitude; lat — longitude; lon; lng | latitude; lat — longitude; lon; lng | Papel GEOMETRIA (RQ-DAD-25) |
| Operadores comparativos e analíticos | maior; menor; igual; acima; abaixo; diferença; diferenca; razão; razao; percentual; porcentagem; comparar; ordenar; selecionar; agregar | greater; lower; equal; above; below; difference; ratio; percentage; percent; compare; order; sort; select; aggregate | Candidatos de interpretação para CAP-CMP-01, CAP-SUB-01 a CAP-SUB-03 e CAP-AGR-01 |
| Conectores lógicos | e; ou; não; nao | and; or; not | CAP-SUB-01 |
| Marcadores temporais relativos | atual; hoje; este ano; ano passado; último ano; ultimo ano; recente | current; today; this year; last year; latest year; recent | AMB-04 |
| Marcadores de tipo de entidade — território | Conceitos MARCADOR_TERRITORIAL_* da tabela abaixo | Conceitos MARCADOR_TERRITORIAL_* da tabela abaixo | Triagem (RQ-DAD-38) |
| Marcadores de tipo de entidade — organização | Conceitos MARCADOR_ORGANIZACAO_* da tabela abaixo | Conceitos MARCADOR_ORGANIZACAO_* da tabela abaixo | Triagem (RQ-DAD-38) |
| Rotatividade | rotatividade da coorte inicial; rotatividade da coorte; taxa de saída da coorte inicial; taxa de saída da coorte; permanência da coorte inicial; permanência da coorte; retenção da coorte inicial; retenção da coorte | initial-cohort attrition; cohort attrition; initial-cohort retention; cohort retention | CAP-ROT-01 |

Marcadores de tipo de entidade, por conceito canônico (RQ-CFG-14):

| Conceito | Português | Inglês | Papel estabelecido |
|---|---|---|---|
| MARCADOR_TERRITORIAL_MUNICIPIO | município | municipality | TERRITORIO |
| MARCADOR_TERRITORIAL_CIDADE | cidade | city | TERRITORIO |
| MARCADOR_TERRITORIAL_ESTADO | estado | state | TERRITORIO |
| MARCADOR_TERRITORIAL_PROVINCIA | província | province | TERRITORIO |
| MARCADOR_TERRITORIAL_DISTRITO | distrito | district | TERRITORIO |
| MARCADOR_TERRITORIAL_REGIAO | região | region | TERRITORIO |
| MARCADOR_ORGANIZACAO_HOSPITAL | hospital | hospital | ORGANIZACAO_INSTITUICAO |
| MARCADOR_ORGANIZACAO_MINISTERIO | ministério | ministry | ORGANIZACAO_INSTITUICAO |
| MARCADOR_ORGANIZACAO_SECRETARIA | secretaria | secretariat | ORGANIZACAO_INSTITUICAO |
| MARCADOR_ORGANIZACAO_UNIVERSIDADE | universidade | university | ORGANIZACAO_INSTITUICAO |
| MARCADOR_ORGANIZACAO_INSTITUTO | instituto | institute | ORGANIZACAO_INSTITUICAO |

Padrões estruturais de posição de entidade, aplicados deterministicamente antes do LLM (CFG-PRV): `[ENTIDADE] [verbo governado] [QUANTIDADE] [CATEGORIA] [PERIODO]`, com os verbos de associação desta seção (incluindo "tinha"/"teve"/"had"); pares `[ENTIDADE]: [VALOR]` ou `[ENTIDADE] = [VALOR]`; posição de entidade em tabela/lista de estrutura inequívoca; e operandos nominais de construção comparativa explícita, como "compare [ENTIDADE] e [ENTIDADE] em [PERIODO]"/"compare [ENTITY] and [ENTITY] in [PERIOD]". Delimitadores, marcadores e continuidade estrutural precisam identificar o trecho de modo inequívoco; caso contrário, reter e esclarecer conforme RQ-DAD-33. Marcadores territoriais e organizacionais governados desta seção podem estabelecer o papel; a posição funcional sozinha não o estabelece. Capitalização não constitui regra de reconhecimento ou liberação (RQ-DAD-38).

Intenções comparativas governadas em PT/EN: "entre si"/"with each other" determina relações entre objetos; "com a referência"/"against the reference" e "em relação à referência"/"in relation to the reference", em pedido comparativo, determinam comparação contra o parâmetro, sem percentual implícito; "entre si e com a referência"/"with each other and against the reference" determina ambos. Diferença relativa/percentual exige intenção explícita ("diferença percentual"/"percentage difference", "diferença relativa"/"relative difference"); razão exige "razão"/"ratio" ou intenção correspondente explícita. Critério abaixo/acima segue CAP-SUB-01. Essas correspondências qualificam intenção, não criam aliases de domínio ou territórios; ambiguidade material remanescente segue CFG-AMB e RQ-GOV-17/20. D18: “referência”/“reference” isolado ou “considere como referência”/“consider as a reference” apenas declara contexto. Intenções “compare com”/“compare with”, “contra”/“against” ou “em relação a”/“in relation to”, quando vinculadas ao pedido comparativo, autorizam a relação correspondente; “acima de”/“above” e “abaixo de”/“below” como filtros permanecem critérios de CAP-SUB-01. Nenhuma dessas expressões autoriza percentual implícito. A presença do parâmetro sozinha não dispara comparação.

Operadores de critério e mapeamento: < — abaixo de; menos de; menor que; inferior a; below; less than. ≤ — até; ate; no máximo; no maximo; at most. > — acima de; mais de; maior que; superior a; above; more than; greater than. ≥ — a partir de; no mínimo; no minimo; at least. Os operadores =, ≠, pertença a lista e pertença a classe seguem o contrato de CAP-SUB-01.

Marcadores temporais relativos não resolvem período por si sós quando houver mais de uma âncora materialmente plausível; nesses casos aplica-se AMB-04.

Padrões autorizados de associação de dados conversacionais (RQ-DAD-41): `A: 10`; `A = 10`; entidade e valor na mesma sentença ou linha ligados por verbo governado — VERBO_ASSOCIACAO_PRESENTE: tem, têm, possui, possuem / has, have; VERBO_ASSOCIACAO_PASSADO: tinha, tinham, teve, tiveram / had; tabela ou lista repetitiva com estrutura inequívoca; duas listas de mesma cardinalidade ligadas por "respectivamente" ou "respectively"; continuação elíptica somente quando existir uma única associação estrutural possível. Havendo duas ou mais associações materialmente plausíveis, pede-se esclarecimento.

Rotatividade: as expressões do grupo têm correspondência direta com CAP-ROT-01. O termo isolado "rotatividade" aciona CAP-ROT-01 somente quando o usuário aceitar ou o contexto autorizado estabelecer que se trata do método incorporado nesta SPEC; o termo isolado "turnover" não tem correspondência determinística nesta versão e segue interpretação candidata e esclarecimento.

Literais numéricos são normalizados deterministicamente quando sua representação possui uma única interpretação materialmente plausível no contexto autorizado. Quando separadores de decimal e milhar permitirem duas ou mais interpretações materialmente diferentes, o sistema não escolhe com base apenas no idioma da sessão e solicita esclarecimento (RQ-FLX-20). O idioma da sessão pode ser usado como informação auxiliar de apresentação e reconhecimento linguístico, mas não como autoridade suficiente para resolver ambiguidade numérica substantiva. Não há convenção universal de separadores nem conversão silenciosa. `10` é inequívoco; `10,5` e `10.5` em construção inequívoca de decimal podem ser normalizados; `1,234` e `1.234`, quando puderem significar o decimal 1,234 ou o inteiro 1234, exigem esclarecimento. A regra de numerais de CFG-LEX (F-12a, seção 4.4.15) permanece aplicável. Nomes de indicadores de CFG-IND e de capacidades de CFG-CAP, na forma em que definidos, são termos governados.

#### 4.4.10. CFG-AMB — gatilhos de ambiguidade

Os seis gatilhos de RQ-GOV-18 têm as formas abaixo; a seção 7.5 define condições de disparo e leituras autorizadas.

| ID | Português | Inglês |
|---|---|---|
| AMB-01 | juntos; em conjunto; conjuntamente; combinados | together; jointly; combined |
| AMB-02 | referência; referencia | reference |
| AMB-03 | vazio significa zero; branco significa zero; nulo significa zero; ausente significa zero | empty means zero; blank means zero; null means zero; missing means zero |
| AMB-04 | marcadores temporais relativos de CFG-VOC | relative temporal markers of CFG-VOC |
| AMB-05 | cresceu; aumentou; subiu; caiu; diminuiu; declinou | grew; increased; rose; fell; decreased; declined |
| AMB-06 | principais; destaques; mais relevantes; piores; melhores | main; highlights; most relevant; worst; best |

#### 4.4.11. CFG-OPC — conjuntos de opções autorizadas

CFG-OPC não introduz alternativas substantivas próprias. As opções apresentáveis ao usuário somente provêm de: enumerações fechadas desta SPEC; alternativas explicitamente definidas em contratos de capacidade; leituras concorrentes previstas em CFG-AMB; duas ou mais interpretações materialmente concorrentes efetivamente identificadas e ancoradas; opções operacionais já estruturadas pela SPEC (ex.: planilhas disponíveis de um XLSX, opções de CFG-PRV). O LLM não cria alternativa factual, metodológica, normativa ou analítica. Sem conjunto autorizado, a pergunta é feita sem alternativas (TPL-04).

Toda opção ou interpretação apresentada ao usuário é OpcaoAutorizada de um ConjuntoOpcoesAutorizadas (seção 3.2), com id estável, valor estruturado, rotulo_pt e rotulo_en governados. Fontes de rótulo: (a) formas `rotulo.<valor>` do catálogo de CFG-DOC sob o id_doc indicado na tabela abaixo; (b) textos fixos de CFG-TPL e CFG-PRV; (c) para RefEscopo e opções operacionais, alias de privacidade ou valor autorizado não protegido do próprio objeto, idêntico nos dois idiomas; (d) para InterpretacaoAlternativa, composição determinística por C-02/C-11 da forma `rotulo.leitura` de DOC:RQ-GOV-17 com os rótulos governados dos elementos distintivos — formas `rotulo.<valor>` desta tabela, valores e aliases autorizados e números com unidade e escala. É proibido usar código interno como rótulo, pedir ao LLM que invente rótulo ou traduzir rótulo em runtime. TPL-04 e perguntas equivalentes, inclusive FN-INT-03, perguntas determinísticas e fallback, só apresentam rótulos governados. Ausência de rótulo obrigatório é erro de configuração/documentação: impede o fechamento documental da versão e, em runtime, impede apresentar a opção ou leitura afetada, sem substituição por código, texto livre ou tradução (RQ-CFG-06).

| Conjunto | Origem | Valores, em ordem governada | Rótulos PT/EN |
|---|---|---|---|
| AMB-01 | CFG_AMB | CONJUNTO_NAO_COMPARATIVO; CONJUNTO_COMPARATIVO; AGREGADO | DOC:RQ-GOV-18, formas rotulo.AMB-01.<valor> |
| AMB-02 | CFG_AMB | REFERENCIA_TERRITORIAL; PARAMETRO_DE_REFERENCIA | DOC:RQ-GOV-18, formas rotulo.AMB-02.<valor> |
| AMB-03 | CFG_AMB | SEMANTICA_DE_CODIFICACAO; REGRA_DE_TRATAMENTO_DE_AUSENCIA | DOC:RQ-GOV-18, formas rotulo.AMB-03.<valor> |
| AMB-04 | CFG_AMB | PERIODO_DA_DATA_CORRENTE; ULTIMO_PERIODO_DISPONIVEL; OUTRA_ANCORA_AUTORIZADA, com variável tipada da âncora | DOC:RQ-GOV-18, formas rotulo.AMB-04.<valor> |
| AMB-05 | CFG_AMB | MUDANCA_ENTRE_PERIODOS; TENDENCIA | DOC:RQ-GOV-18, formas rotulo.AMB-05.<valor> |
| NATUREZA_DE_ENTIDADE_NOMINAL | ENUMERACAO | TERRITORIO; ORGANIZACAO_INSTITUICAO; PESSOA; OUTRA_ENTIDADE_NAO_PESSOAL; MANTER_PROTEGIDA | Texto fixo de CFG-PRV (seção 4.4.22) |
| CONFIRMACAO_DE_USO_DA_BASE | OPERACIONAL | CONFIRMAR; NAO_CONFIRMAR | DOC:RQ-DAD-22, formas rotulo.<valor> |
| ESTRUTURA_DE_ENTRADA.separador | OPERACIONAL | VIRGULA; PONTO_E_VIRGULA | DOC:RQ-DAD-43, formas rotulo.separador.<valor> |
| ESTRUTURA_DE_ENTRADA.finalidade | CONTRATO | ENTRADAS_INDEPENDENTES; BASE_COMBINADA | DOC:RQ-DAD-43, formas rotulo.finalidade.<valor> |
| ESTRUTURA_DE_ENTRADA.papel | ENUMERACAO | DADOS_ANALITICOS; FONTE_AUXILIAR_DE_METADADOS | DOC:RQ-DAD-43, formas rotulo.papel.<valor> |
| ESTRUTURA_DE_ENTRADA.planilhas | OPERACIONAL | Planilhas disponíveis | Alias [PLANILHA_n] de cada planilha |
| UNIVERSO_SEM_QUADRO | CONTRATO | LISTA_EXPLICITA; UNIDADES_OBSERVADAS | DOC:RQ-DAD-10, formas rotulo.<valor> |
| PAPEL_DA_REFERENCIA | CONTRATO | CONTEXTO; COMPARACAO_CONTRA_REFERENCIA; CRITERIO | DOC:CFG-VOC, formas rotulo.papel_referencia.<valor> |
| NATUREZA_DE_ALTERACAO | ENUMERACAO | SUBSTITUICAO_DE_ESTADO; CORRECAO_OU_REPUDIO | DOC:RQ-LIN-12, formas rotulo.<valor> |
| LINHA | ENUMERACAO | CONTINUAR; ABRIR; RETOMAR, com RefEscopo da linha | DOC:RQ-LIN-02, formas rotulo.<valor> |
| CONTINUIDADE_DE_COMPOSICAO | CONTRATO | MANTER_CONTEXTO_ORIGINAL; REAUTORIZAR_NO_NOVO_CONTEXTO; CANCELAR | DOC:RQ-ORQ-11, formas rotulo.<valor> |
| ASSOCIACAO_DE_RESPOSTA | OPERACIONAL | Pendências candidatas, por RefEscopo; NOVA_SOLICITACAO | RefEscopo; DOC:RQ-FLX-10, forma rotulo.NOVA_SOLICITACAO |
| Leituras concorrentes | INTERPRETACAO_CONCORRENTE | InterpretacaoAlternativa validada | DOC:RQ-GOV-17, forma rotulo.leitura; elementos distintivos: DOC:ENUM-ModoTerritorial, DOC:ENUM-DimensaoRecorte, DOC:CFG-IND.definicao, DOC:CAP-CMP-01.metodo e PAPEL_DA_REFERENCIA, formas rotulo.<valor> |

#### 4.4.12. CFG-PRE — precedência entre fontes

Substituição factual explícita do usuário prevalece no escopo indicado e não altera a base original; divergência material entre fontes autorizadas sem precedência definida gera pendência CONFLITO_DE_FONTES, resolvida pelo usuário quando nenhuma regra aplicável a resolver; manifestação do usuário não substitui regra, método, capacidade, configuração ou invariante (RQ-GOV-21).

#### 4.4.13. CFG-AUS — ausência

Configuração deliberadamente vazia quanto a métodos de tratamento de ausência: não há imputação por zero, imputação por média, estimativa automática, exclusão silenciosa ou preenchimento pelo LLM. Valor ausente permanece NAO_AVALIAVEL, salvo valor factual fornecido explicitamente pelo usuário e admitido pelo contrato aplicável (RQ-GOV-22), com a limitação correspondente (INV-04, RQ-DAD-07). Pedido de tratamento de ausência recebe ADM-SC METODO_NAO_INCORPORADO (seção 8.6).

#### 4.4.14. CFG-REP — representação

Transformações e formatos da Parte 13, com as regras: cálculos em precisão integral; arredondamento apenas na apresentação; medidas contínuas com duas casas decimais por padrão; contagens inteiras; aumento automático de casas quando necessário para preservar visualmente sinal, ordem, igualdade, relação com limiar ou valor não nulo (RQ-REP-05). Tipos: tabela; gráfico de barras; gráfico de linhas ou série temporal; mapa com geometria autorizada; painel simples; relatório HTML; PDF; CSV. A apresentação não cria operação analítica. Resultados parciais, alcance "entre as referências avaliáveis", soma dos componentes, caráter histórico, não vigência e demais qualificadores obrigatórios permanecem explícitos nas representações e exportações (RQ-RES-11, RQ-REP-15).

#### 4.4.15. CFG-LEX — léxicos do validador

| Grupo | Português | Inglês | Regra |
|---|---|---|---|
| LEX-NORM — normatividade | adequado; inadequado; suficiente; insuficiente; deficitário; déficit; prioritário; crítico; problemático; ideal; excesso; carência | adequate; inadequate; sufficient; insufficient; deficient; deficit; priority; critical; problematic; ideal; excess; shortage | V-03 |
| LEX-CAU — causalidade | causa; explica; devido a; em razão de; leva a; impacto; efeito de; resulta de | cause; explains; due to; because of; leads to; impact; effect of; results from | V-04 |
| LEX-TEN — tendência | tendência; aceleração; desaceleração; crescimento acelerado; crescimento desacelerado; declínio | trend; acceleration; deceleration; accelerated growth; decelerated growth; decline | V-05 |
| LEX-ACE — acessibilidade | tempo de viagem; tempo de deslocamento; deslocamento; acesso; acessibilidade; isolamento | travel time; travel; access; accessibility; isolation | V-06 |
| LEX-CMP — relações quantitativas | maioria; a maior parte; dobro; metade; maior; menor; percentual; porcentagem; proporção; razão; primeiro; segundo; terceiro | majority; most; double; half; greater; lower; percentage; proportion; ratio; first; second; third | V-07 |
| LEX-DES — destaque | destaca-se; chama atenção; notável; principal; mais importante | stands out; draws attention; notable; main; most important | V-12 |
| LEX-HET — heterogeneidade | heterogeneidade; heterogêneo; heterogênea | heterogeneity; heterogeneous | V-13 |

Ordinais adicionais reconhecidos deterministicamente como ordinais são tratados em LEX-CMP. Regra de numerais (F-12a): algarismos são literais numéricos; numerais escritos inequívocos são literais numéricos; "um" e "uma" não são automaticamente numéricos e só representam 1 quando a construção for quantitativa e a âncora permitir verificar exatamente uma unidade; como artigo, não produzem literal numérico; em inglês, "one" é quantitativo quando funcionar como numeral verificável, e "a" e "an" não são literais numéricos. O reconhecimento de um literal não resolve a ambiguidade de separadores nem autoriza escolher seu valor pelo idioma; a normalização segue CFG-VOC (seção 4.4.9). A presença lexical apenas aciona a regra de validação correspondente; a decisão depende da função do segmento e da âncora (RQ-SIN-06, RQ-SIN-10).

#### 4.4.16. CFG-TPL — mensagens sistêmicas

Campos entre chaves são preenchidos exclusivamente por estado ou valores estruturados autorizados. Os textos são fixos; o LLM não os redige nem os altera.

| ID | Uso | Português | Inglês |
|---|---|---|---|
| TPL-01 | LLM indisponível (RQ-DEG-02/04) | O componente de linguagem está indisponível. Etapas necessárias que dependem dele aguardam restabelecimento. Resultados determinísticos válidos, apresentáveis e rastreáveis podem ser apresentados em modo degradado. Funcionalidades independentes permanecem disponíveis. | The language component is unavailable. Necessary steps that depend on it await recovery. Valid, presentable and traceable deterministic results can be displayed in degraded mode. Independent functions remain available. |
| TPL-02 | Componente indisponível (RQ-DEG-06) | A etapa não pôde ser executada porque o componente necessário está indisponível. Isso não significa ausência de dados nem resultado negativo. | The step could not be executed because the required component is unavailable. This does not mean that data are absent or that the result is negative. |
| TPL-03 | Falha de etapa (RQ-ORQ-14) | A etapa {etapa} não pôde ser concluída devido a {motivo}. Resultados independentes já válidos permanecem disponíveis. | The step {etapa} could not be completed because of {motivo}. Independent results that are already valid remain available. |
| TPL-04 | Pendência (RQ-GOV-19); seis posições fixas | Decisão: {decisao}. [Motivo documentado: {motivo_documentado}.] Elementos afetados: {elementos_afetados}. [Opções autorizadas: {alternativas}.] Sem decisão: {consequencia}. Formato da resposta: {formato_resposta}. | Decision: {decisao}. [Documented reason: {motivo_documentado}.] Affected elements: {elementos_afetados}. [Authorized options: {alternativas}.] Without a decision: {consequencia}. Response format: {formato_resposta}. |
| TPL-05 | ADM-NP | A solicitação não tem como objeto o diagnóstico territorial da força de trabalho na saúde e não será processada por este agente. | The request does not concern territorial diagnosis of the health workforce and will not be processed by this agent. |
| TPL-06 | ADM-FE | A solicitação está relacionada à força de trabalho na saúde, mas a operação pedida não faz parte do escopo desta versão do agente. | The request is related to the health workforce, but the requested operation is outside the scope of this version of the agent. |
| TPL-07 | ADM-SC | A análise solicitada pertence ao escopo do agente, mas a capacidade ou o método necessário não está disponível nesta versão. O sistema não substituirá esse método por outro sem autorização. | The requested analysis belongs to the agent's scope, but the required capability or method is not available in this version. The system will not replace it with another method without authorization. |
| TPL-08 | Limite de regeneração (RQ-SIN-05) | Não foi possível produzir uma formulação validada após as tentativas previstas. O conteúdo será apresentado apenas na forma estruturada disponível. | A validated formulation could not be produced after the allowed attempts. The content will be presented only in the available structured form. |
| TPL-09 | Sessão temporária (RQ-FLX-17/19) | Esta sessão e seu conteúdo são eliminados ao acionar Encerrar sessão ou após 30 minutos (1800 segundos) sem interação efetiva sua. Fechar a interface não encerra imediatamente. Atividade automática não renova o prazo. Exporte o que deseja conservar antes do encerramento; não há retomada entre sessões. | This session and its content are deleted when you select End session or after 30 minutes (1800 seconds) without an effective interaction from you. Closing the interface does not end the session immediately. Automatic activity does not reset the timeout. Export what you want to keep before the session ends; sessions cannot be resumed after termination. |
| TPL-10 | Campos protegidos (RQ-DAD-22) | Foram detectados campos que podem identificar ou individualizar pessoas nesta base. Antes da análise, esses campos serão tratados como protegidos. Eles poderão ser utilizados internamente apenas quando necessários a operações autorizadas, como contagem ou deduplicação, e não serão enviados ao LLM nem exibidos nos resultados analíticos. Confirme que você está autorizado a utilizar esta base. | Fields that may identify or individualize people were detected in this dataset. Before analysis, these fields will be treated as protected. They may be used internally only when required for authorized operations, such as counting or deduplication, and will not be sent to the LLM or displayed in analytical results. Confirm that you are authorized to use this dataset. |
| TPL-11 | Distância geodésica (V-06) | A distância apresentada é geográfica direta. Não representa distância viária, tempo de deslocamento ou acessibilidade real. | The reported distance is a direct geographic distance. It does not represent road distance, travel time, or actual accessibility. |
| TPL-12 | Apresentação estruturada em modo degradado (RQ-DEG-04, RQ-SIN-05) | Exatamente sete blocos em ordem fixa, omitindo apenas conteúdo inaplicável: 1. Resultado; 2. Parâmetros e origens; 3. Método e documentação [opcional]; 4. Cobertura; 5. Limitações; 6. Situação dos entregáveis; 7. Pendências. | Exactly seven blocks in fixed order, omitting only inapplicable content: 1. Result; 2. Parameters and sources; 3. Method and documentation [optional]; 4. Coverage; 5. Limitations; 6. Deliverable status; 7. Pending items. |
| TPL-13 | Impossibilidade técnica de materialização integral (RQ-DAD-43) | Não foi possível materializar integralmente esta entrada. Ela não foi analisada. Forneça um arquivo estruturado em formato admitido (CSV ou XLSX) e associe-o ao pedido preservado. O arquivo será uma nova entrada; a retomada depende da associação e habilitação válidas. | This input could not be fully materialized. It has not been analyzed. Provide a structured file in an accepted format (CSV or XLSX) and associate it with the preserved request. The file will be a new input; processing resumes only after valid association and preparation. |

Em TPL-04, colchetes indicam bloco condicional, não texto livre: omitir motivo quando inaplicável e opções quando não houver conjunto autorizado. Os demais quatro blocos permanecem, inclusive consequência e formato da resposta. motivo_documentado é UsoDocumental renderizado, nunca string livre da LLM; alternativas são exatamente as OpcaoAutorizada do ConjuntoOpcoesAutorizadas registrado, em ordem governada e com rótulos governados no idioma da sessão (CFG-OPC, seção 4.4.11). decisao vem da pendência estruturada; elementos_afetados são RefEscopo com aliases ou rótulos governados; consequencia deriva de BLOQUEADO/LIMITADO/INDEFINIDO (PT: bloqueado/limitado/indefinido; EN: blocked/limited/undefined); formato_resposta deriva de ESCOLHA/VALOR_TIPADO/TEXTO_LIVRE (PT: escolha/valor tipado/texto livre; EN: choice/typed value/free text). Valores substantivos das variáveis exigem âncoras; não autorizam método, fórmula ou opção adicional. Em TPL-12, o bloco "Parâmetros e origens" inclui a interpretação registrada (objeto, universo, períodos, modo e parâmetros com origem). A pergunta de natureza de entidade nominal tem texto fixado em CFG-PRV (seção 4.4.22). O bloco opcional "Método e documentação" de TPL-12 somente é exibido quando há conteúdo metodológico ou operacional aplicável, exclusivamente autorizado por CFG-DOC e validado por V-16. Pode conter método, fórmula, versão, condições, referências às proposições documentais utilizadas e outros elementos metodológicos autorizados que não pertençam a parâmetros e origens. Parâmetros, origens, escala efetivamente aplicada e procedência permanecem em "Parâmetros e origens"; cobertura e limitações permanecem em seus blocos; resultado, status e pendências, nos respectivos blocos. O novo bloco não é template independente nem recebe outro ID; não cria capacidade, altera método, fórmula ou condição, amplia a autoridade do LLM ou permite interpretação analítica, justificativa, causalidade, generalização, conclusão, inferência não ancorada ou paráfrase substantivamente livre. O fallback metodológico segue a mesma distribuição, sem produzir conteúdo substantivo novo. Em D17-A, Situação dos entregáveis informa conjunto vigente vazio e ENCERRADA_SEM_RESULTADO; Resultado distingue resultados anteriores históricos; Pendências exclui obrigações só dos retirados e preserva compartilhadas para seus consumidores. Retirada não é cancelamento, falha ou conclusão integral/parcial; a forma local `retirada_total` de DOC:TPL-12 materializa esse bloco em PT/EN. Em cancelamento explícito, Situação dos entregáveis informa a solicitação CANCELADA, os entregáveis vigentes não terminais CANCELADO e os entregáveis já concluídos com estado e resultado históricos preservados, pela forma local `cancelamento` de DOC:TPL-12. Cobertura distingue elementos válidos, falhos e não avaliáveis (RQ-RES-04). Formas locais e rótulos citados residem no catálogo externo de CFG-DOC (seção 4.4.23.6).

#### 4.4.17. CFG-REC — recálculo

Não há recálculo espontâneo. Se a nova solicitação implicar claramente recálculo, ela autoriza nova execução segundo os gates aplicáveis; se a mudança de estado afetar resultado anterior sem pedido de nova análise, o impacto é registrado e o agente pode oferecer reexecução; nenhuma alteração de dado ou parâmetro dispara cálculo analítico silencioso (RQ-LIN-15).

#### 4.4.18. CFG-ESC — escopo de parâmetros e decisões

Mantêm-se o menor escopo explicitamente indicado, a ausência de propagação de critérios ou decisões locais entre linhas e a ausência de alteração da configuração global (RQ-LIN-07). A recuperação por linhas compatíveis do valor factual fornecido sem linha aplicável, ainda associado ao mesmo objeto e escopo, segue RQ-LIN-21 e não constitui transferência ou ampliação de escopo. Acrescentam-se (RQ-LIN-19): resposta a pendência herda o escopo do parâmetro, objeto ou decisão da pendência que resolve; a mensagem isolada que contém a resposta não reduz esse escopo; restrição expressa do usuário prevalece; alterar uma dimensão não apaga outras dimensões ainda válidas e aplicáveis; resposta com escopo de linha permanece válida enquanto a dimensão correspondente não for substituída; resposta explicitamente ligada a objeto específico não se propaga a outro objeto. Exemplo normativo: "Qual período?" → "2023" → "agora enfermeiros": 2023 permanece quando a pendência de período era da linha; "Para médicos, use 2023" → "agora enfermeiros": 2023 não é transferido. Valor factual complementar segue RQ-LIN-21. Retirada versiona EscopoSolicitacao e restringe obrigações aos entregáveis vigentes; conjunto vazio por retirada total segue D17-A/RQ-FLX-02. OBJETO pode referenciar entrada/base, versão, esquema, campos, períodos, unidades e exceções; antes de linha legítima não há propagação automática para linha futura. Captura UI segue RQ-FLX-16.

#### 4.4.19. CFG-NOR — critérios normativos

Configuração deliberadamente vazia. Não há limiar pré-configurado que permita ao agente afirmar automaticamente que uma situação é adequada, inadequada, suficiente, insuficiente, crítica, prioritária, ideal ou deficitária. Critério normativo pode ser definido explicitamente pelo usuário no escopo da análise, com operador, valor, unidade e escala, classificação, origem e escopo registrados (RQ-GOV-31); sem ele, nenhum resultado é qualificado normativamente (V-03).

#### 4.4.20. CFG-LIM — limitações

Taxonomia de RQ-RES-06. Limitações analíticas obrigatórias acompanham o resultado; eventos técnicos sem efeito sobre o significado analítico permanecem na rastreabilidade. A apresentação preserva explicitamente: cobertura parcial; agregado parcial; unidades não avaliáveis; universo observado não exaustivo; possível dupla contagem; aditividade por premissa do usuário; comparabilidade; níveis territoriais diferentes; cobertura desigual entre períodos; categorias não comparáveis; diferença de definição; valor fornecido ou substituído pelo usuário; denominador alternativo; critério normativo do usuário; distância geodésica direta; empate no corte; conjunto vazio anterior. "Heterogeneidade" não é limitação analítica autônoma sem critério formal autorizado.

#### 4.4.21. CFG-FON — fontes e formatos de entrada

Duas portas de entrada: upload de arquivo estruturado e dados fornecidos explicitamente na conversa; não há fonte externa configurada. Formatos obrigatórios de upload: CSV, com separador vírgula ou ponto e vírgula, e XLSX, com uma ou mais planilhas. Estruturas admitidas: tabela longa; tabela larga simples; base individualizada; arquivos auxiliares separados; dimensões constantes declaradas por metadado ou pelo usuário. Dados na conversa não têm limite metodológico fixo de linhas. Regras de escolha de separador, de planilha e de materialização integral: RQ-DAD-43. Seleção múltipla distingue entradas independentes de base combinada conforme RQ-DAD-43; uso das planilhas não autoriza operação estrutural implícita. Combinação exige RQ-DAD-30 e regra determinada, com linhagem de arquivo e planilha. Abas não selecionadas não fornecem dados nem semântica; seleção de fonte auxiliar exige PapelPlanilha e vínculo explícito ao escopo (RQ-DAD-43). A enumeração técnica para escolha usa aliases sem leitura semântica de células. Impossibilidade de materialização integral usa TPL-13, bloqueia a entrada e preserva pedido/associação para arquivo substituto como nova entrada.

#### 4.4.22. CFG-PRV — privacidade pré-LLM

Toda triagem ocorre antes de qualquer envio de conteúdo ao LLM. Conteúdo nominal ou identificador originado do usuário só atravessa essa fronteira em claro com evidência determinística positiva de papel não pessoal; na ausência dessa evidência, recebe placeholder, e o esclarecimento só é aberto quando o papel for material à execução (RQ-DAD-20, RQ-DAD-38). Não há catálogo de cidades ou territórios para essa finalidade. Regras: CPF, e-mail, telefone, rótulos e padrões governados de identificadores pessoais (RQ-DAD-37); entidades nominais em texto livre e organizações (RQ-DAD-38); placeholders, persistência da proteção e mapeamento protegido (RQ-DAD-39). Aplicar integralmente as classes A/B/C/D de RQ-DAD-20: proteger A, liberar B quando necessário, minimizar C com aliases e permitir D, linguagem funcional não nominal, após triagem e sem tipificação como entidade. Ordem determinística para identificadores (RQ-DAD-37): 1. papel estrutural explicitamente tipado e autorizado; 2. rótulo governado de identificador pessoal; 3. padrão governado inequívoco; 4. papel não resolvido → proteger por padrão. Valor tipificado explicitamente como código territorial continua territorial mesmo quando seus dígitos coincidem com CPF válido. CPF válido exclui sequências de dígitos todos idênticos. Rótulo/valor inequívoco protege independentemente de formato. "Matrícula" isolada ou outro rótulo materialmente ambíguo é protegido por padrão; pergunta-se somente se a distinção for necessária à execução. Rótulos governados de identificadores pessoais e marcadores de telefone, por conceito canônico (RQ-CFG-14), além de equivalentes estabelecidos por metadado autorizado ou confirmação semântica no escopo da entrada:

| Conceito | Português | Inglês |
|---|---|---|
| CPF | CPF | CPF |
| CNS_PROF | CNS_PROF | CNS_PROF |
| NOME_PROF, quando representar dado pessoal | NOME_PROF | NOME_PROF |
| CRM | CRM | CRM |
| COREN | COREN | COREN |
| NIS | NIS | NIS |
| NOME_DE_PESSOA | nome; nome completo; nome da pessoa | name; full name; person name |
| IDENTIFICADOR_INDIVIDUAL | identificador individual; matrícula individual; registro individual | individual identifier |
| IDENTIFICADOR_PROFISSIONAL | identificador profissional individual; identificador do profissional | professional identifier |
| MATRICULA_PROFISSIONAL | matrícula profissional | professional ID; employee ID; staff number |
| REGISTRO_PROFISSIONAL | registro profissional | professional registration |
| ID_TRABALHADOR | ID do trabalhador | worker ID |
| MARCADOR_TELEFONE | telefone; tel.; celular | phone; telephone; tel.; mobile |

Metadados minimizados usam [CAMPO_n], [ARQUIVO_n], [PLANILHA_n]; mapas/originais nunca entram em FN, eventos, procedência ou produtos.

Reconhecimento nominal: os padrões de CFG-VOC identificam posições funcionais de entidade antes do LLM, e RQ-DAD-38 define a liberação por evidência positiva; ausência de tipificação autorizada e de marcador suficiente exige proteção/placeholder antes da leitura mínima. Conteúdo já protegido permanece protegido em toda reaparição no mesmo escopo de linhagem, independentemente da posição, até evidência positiva no escopo aplicável (RQ-DAD-39). Capitalização, aparência de nome, lista externa de nomes, conhecimento externo, similaridade semântica e decisão do LLM não decidem pessoa versus não pessoa nem liberam a expressão. Posição reconhecida cujo trecho não possa ser delimitado com segurança permanece retida; C-02 usa esclarecimento determinístico de RQ-DAD-33, sem enviar o conteúdo em claro ao LLM. Tipificação posterior conserva origem, âncora e escopo (RQ-DAD-38).

Pergunta determinística de esclarecimento de entidade nominal (pendência NATUREZA_DE_ENTIDADE_NOMINAL), apresentada por C-02 sem uso do LLM:

- PT: "Decisão: informe a natureza de {alias_entidade}. Elementos afetados: {alias_entidade}. Opções autorizadas: território; organização ou instituição; pessoa; outra entidade não pessoal; manter protegida. Sem decisão: permanece protegida e aguarda somente a operação dependente. Formato da resposta: escolha." Opções: território; organização ou instituição; pessoa; outra entidade não pessoal; manter protegida.
- EN: "Decision: specify the nature of {alias_entidade}. Affected elements: {alias_entidade}. Authorized options: territory; organization or institution; person; other non-person entity; keep protected. Without a decision: it remains protected and only the dependent operation waits. Response format: choice." Options: territory; organization or institution; person; other non-person entity; keep protected.

A variável alias_entidade é placeholder de CampoProtegido com âncora em C-10; jamais recebe original. Revelação explícita ao próprio usuário continua restrita ao visualizador protegido de RQ-REP-13/RQ-PRV-07, sem LLM ou evento desprotegido. Quando pertinente, inserir Motivo documentado/Documented reason depois de Decisão/Decision, exclusivamente pela forma autorizada de CFG-PRV.privacidade, conservando a ordem TPL-04. Placeholders: [CPF_n]; [EMAIL_n]; [TELEFONE_n]; [PESSOA_n]; [IDENTIFICADOR_n]; [ENTIDADE_PROTEGIDA_n]. Não são classificados como pessoais apenas por existirem: categorias profissionais; indicadores; períodos; valores quantitativos; territórios autorizados; organizações autorizadas; termos metodológicos; metadados somente segundo as quatro classes de RQ-DAD-20; nomes de campo, arquivo e planilha não têm liberação genérica. Vazios deliberados: regras de anonimização, pseudonimização ou supressão e limiar de supressão de células pequenas (RQ-PRV-09).

#### 4.4.23. CFG-DOC — Registro de Proposições Documentais

CFG-DOC contém o Registro de Proposições Documentais desta SPEC. O registro referencia exclusivamente conteúdo normativo existente, sem enciclopédia explicativa paralela. O contrato desta seção e o mapa normativo de extração do Anexo A fixam as unidades, a granularidade, a identificação, os trechos e a classificação. O implementador apenas materializa essas correspondências; não decide o que constitui uma proposição, não recorta aspectos por julgamento próprio e não usa conhecimento do LLM para completar o registro. A massa literal das formas autorizadas PT/EN, inclusive variantes e rótulos governados, reside no catálogo externo Docs/CFG_DOC_CATALOG.yaml (seção 4.4.23.6), versionado com esta SPEC. A externalização altera a organização física, não a autoridade normativa: definições, contratos, texto canônico PT, condições, dependências e relações de aplicabilidade permanecem nesta SPEC e no Anexo A; o catálogo é consultado pontualmente por id_doc.

##### 4.4.23.1. Estrutura e fontes

```text
ProposicaoDocumental
  id_doc: Texto — DOC:<fonte_normativa>[.<caminho>]; único no registro vigente
  fonte_normativa: Id — chave da unidade normativa no mapa do Anexo A
  caminho: Opcional<Enum<CaminhoProposicaoDocumental>> — ausente na unidade indivisa; nunca texto vazio
  texto_canonico_pt: Texto — reprodução dos trechos exatos indicados no mapa, na ordem indicada
  idioma_normativo: PT — único registro normativo por id_doc
  tipo_proposicao: Enum<TipoProposicaoDocumental>
  condicoes_aplicabilidade: Lista<{fonte_normativa: Id, trechos: Lista<LocalizadorNormativo>}> — referências, sem condição criada
  referencias_dependentes: Lista<ReferenciaNormativa> — unidades expressamente referidas necessárias à interpretação ou validade
  versao_fonte: Texto — versão da unidade ou da SPEC/configuração correspondente
  formas_apresentacao_autorizadas: — residentes no catálogo externo (4.4.23.6), pela chave id_doc
    pt: Lista<FormaApresentacao> — ao menos a forma `base`, idêntica a texto_canonico_pt
    en: Lista<FormaApresentacao> — mesmas formas locais, como apresentação equivalente da proposição PT, sem novo id_doc

FormaApresentacao
  id_forma_local: Texto — único dentro da proposição e idioma
  versao: Texto
  texto_template: Texto — literal governado no catálogo PT/EN, nunca tradução em runtime; forma `rotulo.*` contém rótulo governado de opção ou elemento (seção 4.4.11)
  variaveis_tipadas: Lista<{nome, tipo, origem_estruturada, ancora_requerida}>
  condicoes_de_uso: Lista<{referencias_regras: Lista<IdDoc>, descricao_literal: Texto}> — referências ao contrato/às verificações estruturadas governadas, sem decisão semântica pelo LLM
  referencias_necessarias: Lista<IdDoc> — cada ID resolve à fonte/caminho e às dependências de ReferenciaNormativa no Anexo A

UsoDocumental
  id_doc, versao_fonte: Texto
  idioma: Enum<Idioma>
  id_forma_local, versao_forma: Texto
  valores_das_variaveis: mapa de nomes declarados para valores tipados
  ancoras_concretas: Lista<Ref<Ancora>> — necessárias para aplicação concreta, não inventadas para descrição geral

LocalizadorNormativo
  linha: Inteiro — linha física da SPEC versionada, iniciada em 1
  inicio, fim: Inteiro — posições de caracteres Unicode na linha, iniciadas em 0; intervalo [inicio, fim)

ReferenciaNormativa
  unidade: Texto — identificador ou nome canônico expresso na fonte
  localizacao: Texto — definição normativa a que a referência resolve nesta versão, ou seção explícita do Concept
```

As origens admitidas são somente INV-*, RQ-*, CAP-*, CFG-*, FAM-*, EXC-*, V-*, TPL-*, enumeração canônica, termo do glossário, regra de desfecho e limitação tipada explicitamente definida. Não existe DOC: sem fonte normativa correspondente. Referências históricas DA, P, AV e F, cenários AT/ROT-AT, exemplos isolados e registros de auditoria não constituem fontes adicionais de proposições; referências expressas a eles continuam como rastreabilidade da fonte normativa que os cita. O Concept não é modificado nem convertido em fonte adicional de DOC:.

Os IDs existentes são conservados. Enumerações usam `ENUM-` seguido do nome canônico; termos do glossário usam `GLOSSARIO-` seguido do termo canônico; regras de desfecho usam `DESFECHO-` seguido do código; limitações tipadas usam `LIMITACAO-` seguido do valor canônico. Para essas chaves documentais, conserva-se cada caractere ASCII alfanumérico, hífen e sublinhado; cada outro caractere é representado pelos bytes de sua codificação UTF-8 em `%HH`, com hexadecimal maiúsculo, sem conversão de caixa nem remoção de acentos. É codificação reversível de nomes já existentes, não alias de domínio. O Anexo A fixa as chaves concretas; o ponto separa exclusivamente o caminho, quando presente.

As definições primárias são: requisitos identificados nas Partes 0 a 20, incluindo sua tabela ou lista normativa subordinada; invariantes na seção 1.7; famílias na seção 1.3; exclusões na seção 1.4; enumerações na seção 3.1; termos do glossário na seção 0.7; capacidades no catálogo 8.3 e contratos 8.4; configurações no catálogo 4.2 e conteúdo de 4.3/4.4 expressamente indicado no mapa; validadores na seção 14.2; modelos na seção 4.4.16; desfechos na tabela 15.1; limitações na enumeração e em RQ-RES-06. Menção ou referência em outra parte não cria segunda definição. Contrato compartilhado por CAP-REP-01 a CAP-REP-04 é fonte dos quatro IDs distintos, com a identidade de cada capacidade preservada no catálogo.

##### 4.4.23.2. Caminhos, tipos e idioma

| Enumeração | Valores fechados |
|---|---|
| CaminhoProposicaoDocumental | definicao; finalidade; natureza; entradas; parametros; precondicoes; metodo; avaliabilidade; saida; limitacoes; proibicoes; representacao; compatibilidade; privacidade; precedencia; escopo; comportamento |
| IdiomaProposicaoDocumental | PT; EN |
| TipoProposicaoDocumental | IDENTIDADE; FINALIDADE; CAPACIDADE; METODO; PRECONDICAO; LIMITACAO; PRIVACIDADE; DADOS; GOVERNANCA; OPERACIONAL; REPRESENTACAO; DESFECHO; AVALIABILIDADE |

Nesta versão, conforme decisão da remediação, há um registro normativo PT por id_doc. Os textos fixos normativos EN continuam preservados em suas fontes e continuam obrigatórios nas situações ali definidas, especialmente CFG-TPL e CFG-PRV; não originam registro duplicado nem proposição substantiva diferente. Apresentação em inglês utiliza formas EN previamente autorizadas vinculadas à mesma proposição PT; não há tradução substantivamente livre durante a sessão nem segundo registro normativo. Mudar o bloco de apresentação, inclusive para "Method and documentation", não cria proposição ou fonte documental. EN é idioma de apresentação em UsoDocumental, sem registro normativo adicional; idioma_normativo permanece PT. A proposição normativa canônica é PT; a forma EN é apresentação autorizada da mesma proposição e não constitui segunda norma independente. Forma EN só é autorizável quando preserva integralmente, em relação à forma PT de mesmo id_forma_local: modalidade normativa; obrigação; proibição; permissão; negação; quantificadores; alternativas; listas fechadas; estados; motivos; parâmetros; condições; exceções; e variáveis. Forma que omita, acrescente ou altere qualquer desses elementos é divergente: impede o fechamento documental e, em runtime, não é usada, aplicando-se a insuficiência de 4.4.23.5, sem tradução livre nem troca silenciosa de idioma. Ferramentas automáticas inventariam, extraem, pareiam e conferem variáveis e estrutura das formas; não decidem equivalência semântica, que exige revisão documental registrada na versão.

O mapa do Anexo A é fechado e exaustivo para esta versão: cada linha define exatamente um par fonte/caminho e seu tipo. A coluna de tipo é a função determinística de classificação desse par; não há classificação pelo LLM, por palavra-chave, por similaridade ou por decisão do materializador. Em unidade com uma única proposição funcional, o caminho fica ausente e o ID é `DOC:<fonte_normativa>`. Condição, exceção, ressalva, alternativa de uma mesma regra e consequência necessária à sua interpretação não são proposições independentes apenas por estarem em frases diferentes. Em unidade com aspectos funcionalmente independentes, o mapa os separa exclusivamente pelos caminhos fechados presentes e conserva as condições que restringem cada aspecto. O mesmo aspecto composto mantém os trechos na ordem da fonte, sem criar subcaminhos.

Nenhum caminho vazio é criado; a marca `—` no mapa significa ausência do campo, não caminho literal. Não há entrada para aspecto ausente. Não se inventa caminho durante a sessão. Ampliação do vocabulário exige evolução governada da SPEC. O denominador integra `metodo`, não um caminho adicional. Exemplos válidos do mapa: `DOC:RQ-DAD-07`, `DOC:CAP-ROT-01.metodo`, `DOC:CAP-ROT-01.precondicoes`, `DOC:CAP-AGR-01.metodo`, `DOC:CFG-PRV.privacidade` e `DOC:INV-16`.

##### 4.4.23.3. Extração, condições e dependências

Cada localizador do mapa aponta para trecho exato da SPEC 1.2.4, contando linhas e caracteres conforme 4.4.23.1. A leitura normaliza apenas terminações de linha para LF e desconsidera eventual BOM inicial. Não se altera texto, número, fórmula, negação, ordem de alternativas ou relação condicional. `texto_canonico_pt` resulta da concatenação, por LF, dos trechos listados, na ordem registrada. A separação de linhas é documental e não introduz conectivo nem modifica relações lógicas. Os localizadores não são números factuais apresentados ao usuário nem novos parâmetros analíticos.

`condicoes_aplicabilidade` contém as referências fixadas na coluna Condições do mapa, incluindo as qualificações de capacidade, estado, tipo de dado, idioma, avaliabilidade, parâmetro e escopo que a própria fonte explicita. `—` produz conjunto vazio. Uma referência pode abranger a regra condicional completa, inclusive suas alternativas e consequência, para conservar exatamente a relação prevista; a consequência não se converte em requisito de aplicabilidade adicional, e uma lista de referências não transforma alternativas em conjunção. Nenhuma condição é acrescentada, inferida, enfraquecida ou desligada da regra que limita. Quando um aspecto separado depende de ressalva ou condição expressa em outro trecho da mesma unidade, esse trecho está indicado na coluna Condições e deve acompanhar a verificação, mesmo que não seja duplicado em texto_canonico_pt.

`referencias_dependentes` copia a coluna Dependências do mapa, que fixa as unidades expressamente referidas nos trechos normativos e nas condições, incluindo seções que contêm as definições necessárias; `—` produz conjunto vazio. A resolução usa os IDs, nomes canônicos e seções exatos, sem busca semântica nem seleção posterior de dependências. `S:` identifica seção desta SPEC, `PARTE:` identifica parte, `CONCEPT:` conserva a seção explicitamente citada do Concept e `MODELO:` identifica a entidade nominal da seção 3.2. IDs de componentes, funções e gatilhos resolvem respectivamente nas seções 2.2, 8.5 e 7.5. Os demais IDs resolvem nas definições primárias indicadas em 4.4.23.1. Intervalos explicitamente citados são materializados pelos membros existentes; cada dependência é registrada uma vez. Referência ao próprio registro não é uma dependência adicional. As dependências não importam regras fora de seu escopo nem provocam extração recursiva de novas proposições. Referências a testes e registros históricos não são convertidas em premissas normativas; a citação ao Concept não autoriza extrair conteúdo ausente dos arquivos. Referência sem destino verificável na SPEC não autoriza completar a regra: é falha documental a corrigir por versão governada antes de aceitar o registro.

`versao_fonte` é a versão explicitamente atribuída à unidade/configuração; na ausência de versão própria, é `SPEC-1.2.4`. O mapa, a SPEC e o registro integram a mesma versão governada. Mudança de linhas ou de texto obriga regenerar os localizadores e verificar novamente a correspondência; não há ajuste discricionário de trechos pelo implementador.

##### 4.4.23.4. Algoritmo determinístico de construção

1. Percorrer todas as fontes normativas admitidas, pelos localizadores de definição fixados nesta seção e no Anexo A; menções repetidas não criam fontes.
2. Para unidade com uma única proposição funcional, criar exatamente a entrada sem caminho do mapa, `DOC:<fonte_normativa>`.
3. Para unidade com múltiplos aspectos independentes explicitamente separados no mapa, criar exatamente uma entrada por aspecto presente, `DOC:<fonte_normativa>.<caminho>`; não criar também a entrada raiz nem decomposição adicional.
4. Resolver os localizadores de cada entrada para trechos normativos exatos; extrair o texto conforme 4.4.23.3 e copiar o tipo determinado pelo par fonte/caminho.
5. Não introduzir conteúdo novo: texto, condições e dependências provêm exclusivamente das fontes e correspondências fixadas.
6. Não criar entrada por conhecimento, interpretação livre ou proposta do LLM.
7. Não acrescentar entrada, caminho, tipo, tradução normativa ou condição durante a sessão.
8. Integrar o registro, seu mapa e o catálogo externo de formas à configuração governada e ao snapshot carregado em C-09; a sessão consulta esse snapshot.
9. Alteração da fonte, do mapa ou do vocabulário exige nova versão e regeneração do registro; preserva-se o congelamento de configuração das sessões em andamento (RQ-CFG-05).
10. Verificar que id_doc é único, que fonte/caminho/tipo correspondem ao mapa, que trechos e dependências resolvem e que condições conservam a fonte; que o catálogo externo declara compatibilidade com esta versão da SPEC, contém exatamente os id_doc do mapa, sem entrada órfã, com forma PT `base` idêntica a texto_canonico_pt; e que cada forma EN possui par PT de mesmo id_forma_local, variáveis de mesmo nome e tipo e revisão de equivalência registrada (4.4.23.2). Falha impede aceitar a materialização como registro vigente; não se omite a entrada defeituosa silenciosamente.
11. Exigir que toda âncora DOC: usada em saída exista no registro vigente e seja pertinente à afirmação, sob V-16 e RQ-SIN-10.
12. Na ausência de proposição pertinente, produzir DOCUMENTACAO_INSUFICIENTE; não preencher a ausência por conhecimento do LLM.

O Anexo A é metadado normativo de extração, não um conjunto recursivo de novas proposições. CFG-DOC toma como fonte seu contrato nesta seção, sem gerar proposições a partir das linhas do próprio mapa. Duas materializações da mesma fonte, mapa e versão devem produzir os mesmos campos e IDs; ordem de armazenamento não altera a identidade documental.

##### 4.4.23.5. Validação de uso e fechamento

São autorizadas as funções já previstas: respostas sobre identidade, finalidade, capacidades disponíveis/indisponíveis/não incorporadas, métodos, pré-condições, limitações, dados, privacidade, motivos de bloqueio, funcionamento operacional, formatos, procedência e avaliabilidade. A autorização está limitada às proposições existentes e aplicáveis, com âncoras adicionais de estado, evento, pendência ou resultado quando a afirmação tratar das condições concretas da sessão.

Conteúdo metodológico ou operacional substantivo DEVE usar texto canônico ou forma/template determinístico previamente autorizado e associado à ProposicaoDocumental vigente. C-04 valida id_doc, versão, forma, condições vinculadas às verificações governadas correspondentes, dependências, âncoras, variáveis, tipos, origens e correspondência com o estado/resultado concreto. As condições são avaliadas pelos controles estruturados pertinentes, não por interpretação livre do texto normativo. Explicação geral é identificada como descrição; afirmar aplicação, bloqueio ou resultado exige também evento/estado/perfil/resultado que comprove o caso. O LLM pode propor proposições pertinentes, escolher formas autorizadas, organizar sua ordem e inserir conectores não substantivos; não cria método, justificativa, condição, generalização, causalidade, conclusão ou paráfrase substantivamente livre cuja fidelidade exija julgamento semântico genérico. Não valida a própria saída; tipagem e presença lexical não bastam. V-16 verifica correspondência documental, estrutural, condicional e de ancoragem, sem prova genérica de equivalência entre textos livres. Formulação não autorizada, condição omitida ou variável/afirmação concreta sem suporte é rejeitada; RQ-SIN-05 limita as regenerações e nunca exibe o texto rejeitado. Sem proposição pertinente, DOCUMENTACAO_INSUFICIENTE. Com proposição pertinente e falha da composição textual, C-11/C-02 apresentam fallback metodológico determinístico com conteúdo autorizado, distribuído pelos blocos de TPL-12, inclusive "Método e documentação" quando aplicável; TPL-08 comunica a falha. Nenhuma análise ou conteúdo substantivo novo é produzido.

As formas autorizadas contemplam, quando pertinente, o bloco opcional "Método e documentação" de TPL-12, conservando as mesmas proposições, fontes, condições, dependências, variáveis, âncoras e versões. Escala e origem concretas provêm de EV-REPRESENTACAO (RQ-REP-01, RQ-RAS-05), sem inferir precedência pela ausência de outros valores. O catálogo literal PT/EN externo da seção 4.4.23.6 integra CFG-DOC; suas formas não são novas fontes de proposições. Cada id_doc do mapa exige pelo menos a forma `base` em cada idioma e as variantes pertinentes. Ausência, incompatibilidade de versão ou divergência normativa impede fechamento documental. A aprovação editorial da versão precede publicação/uso de snapshot; sessões conservam as formas do snapshot inicial.

Contrato de interpolação e insuficiência documental (D20): C-02/C-11 interpolam deterministicamente somente variáveis declaradas e tipadas, provenientes de configuração, estado operacional, manifestação do usuário, evento ou resultado autorizado; preservar âncoras, escopo, privacidade e versão. São proibidos campos extras, originais protegidos e texto livre da LLM como fórmula, método, condição, alternativa, rótulo ou justificativa. FN-INT-03/FN-META-01 selecionam formas e referências, não traduzem nem parafraseiam conteúdo metodológico. Descrição geral de regra não afirma sua aplicação concreta; esta requer evento/estado/resultado existente e pertinente. V-16 verifica id_doc/versão da fonte, idioma, id/versão da forma, igualdade ao template interpolado, tipos/origens/âncoras, condições e dependências. Nenhum conteúdo metodológico adicional é permitido. Forma requerida ausente/incompatível rejeita o trecho em runtime e registra DOCUMENTACAO_INSUFICIENTE, apresentando a forma local `insuficiencia` de DOC:CFG-DOC.comportamento no idioma da sessão, sem tradução livre nem troca silenciosa para PT; resultado determinístico válido continua apresentável pelos blocos autorizados de TPL-12, preservando D6.

Formas documentais selecionadas para PerguntaEstruturada seguem o inventário de TPL-04: decisão, motivo documentado opcional, elementos, opções quando existentes, consequência e formato da resposta. O fallback preserva conteúdo, ordem, opções e rótulos governados, sem preencher motivo inaplicável.

##### 4.4.23.6. Catálogo externo de formas PT/EN e relações de aplicabilidade

O arquivo Docs/CFG_DOC_CATALOG.yaml é o catálogo literal das formas autorizadas desta versão. Ele declara identificação estável (`catalogo: CFG-DOC-CATALOG`), sua versão, a versão compatível desta SPEC (`versao_spec_compativel: 1.2.4`) e `versao_fonte` SPEC-1.2.4; usa id_doc como chave única, na ordem do Anexo A; preserva IDs, ids locais de forma, variáveis tipadas, condições de uso e referências necessárias; e é determinístico: UTF-8 sem BOM, LF, chaves sem âncoras ou aliases YAML e literais sem interpolação implícita. Não há catálogo concorrente, índice paralelo nem dependência da v1.2.3 em runtime.

A forma `base` de cada id_doc tem campos fixos declarados uma vez no próprio catálogo: sem variáveis; condição de uso única referenciando o próprio id_doc, com descrição literal "DESCRICAO_GERAL; preservar condições e dependências do mesmo id_doc no Anexo A; não afirmar aplicação concreta"; sem referências necessárias adicionais. Seu texto PT reproduz exatamente texto_canonico_pt; seu texto EN é a apresentação equivalente de 4.4.23.2. As formas `base` servem à descrição geral da proposição, conservam as condições e dependências do mesmo id_doc no Anexo A, inclusive ressalvas de outros aspectos, não afirmam aplicação concreta, não substituem mensagens operacionais e não possuem variáveis: chaves e símbolos em exemplos, esquemas e descrições de templates são literais metalinguísticos. Condições e fórmulas não são alteradas pelo idioma; tabelas de aliases e léxicos nas fontes são dados literais governados, não convite à tradução ou criação de sinônimos. A apresentação integral de uma capacidade seleciona os aspectos pertinentes com suas condições; uma descrição geral de aspecto não dispensa precondições, limitações ou qualificadores. Forma EN cuja `versao` seja anterior à da forma PT de mesmo id_forma_local, por alteração do literal PT nesta versão, não é apresentação autorizada da proposição vigente até ser restabelecida por revisão de equivalência registrada; em runtime aplica-se a insuficiência de 4.4.23.5, sem tradução livre nem troca silenciosa de idioma.

Formas `mensagem`, `pergunta_*`, `motivo_*`, `retirada_total`, `cancelamento`, `controle_encerramento`, `insuficiencia`, `transicoes`, `minimo_observacoes`, `bloqueio_observacoes` e `rotulo.*` aplicam somente as condições expressas em seus registros. Variáveis são declaradas com tipo, origem e âncora; somente elas admitem substituição. C-02/C-11 interpolam deterministicamente valores sanitizados. Listas preservam ordem governada e cardinalidade, com rótulos PT/EN governados (seção 4.4.11) e aliases; referências não introduzem método, opção, rótulo ou justificativa livre. Campos extras e originais protegidos são rejeitados. Rótulo documental necessário sem forma no idioma é erro de configuração/documentação; em runtime aplica-se insuficiência, nunca tradução livre. Uma mensagem concreta exige as âncoras existentes que comprovem a situação. IDs locais só são únicos dentro de id_doc e idioma. `referencias_necessarias` acrescenta as referências explícitas da variante às dependências da proposição; não as substitui. Condições são verificadas em estado estruturado por C-04 e não interpretadas livremente pelo LLM; a função de validação é V-16. `versao` de cada forma identifica a versão da SPEC em que seu literal foi estabelecido; o catálogo como um todo só é compatível com a versão declarada em `versao_spec_compativel`.

Em perguntas, blocos entre colchetes são condicionais: omitir motivo inaplicável e opções ausentes, conservando as demais posições. A forma `pergunta_*` já contém a decisão fixa do tipo; `alvo` nunca recebe instrução livre. Na forma geral TPL-04/mensagem, `decisao` é o fragmento inicial materializado da variante pertinente. `motivo_documentado` renderiza UsoDocumental pertinente da tabela abaixo ou outro aspecto explicitamente requerido pelo contrato da capacidade, nunca texto livre. Consequência e formato da resposta usam os rótulos fixos de CFG-TPL (seção 4.4.16). Quando a estrutura já está definida e H3 requer substituição, usar pergunta_substituicao_tecnica; quando apenas a estrutura exige esclarecimento, usar pergunta_estrutura; para AMB-05, pergunta_mudanca_ou_tendencia. São formas literais próprias, sem edição de cláusulas na sessão. Para natureza nominal, as formas fixas de CFG-PRV governam a pergunta determinística e preservam as cinco opções.

Descoberta de formas por componente, sem varredura integral do catálogo: (a) os id_doc de uma unidade normativa X são exatamente as linhas do Anexo A com Fonte X, com id_doc `DOC:X[.<caminho>]`; (b) toda forma `base` é localizada pela chave id_doc; (c) as variantes não base estão fixadas nas relações abaixo e em CFG-OPC (rótulos, seção 4.4.11).

| Componente ou situação | id_doc | Formas locais |
|---|---|---|
| Mensagens de CFG-TPL | DOC:TPL-01 a DOC:TPL-13 | mensagem |
| Pendência (TPL-04), por tipo | DOC:TPL-04 | pergunta_* da tabela seguinte; pergunta_estrutura; pergunta_substituicao_tecnica; pergunta_mudanca_ou_tendencia |
| Controle Encerrar sessão (RQ-FLX-09/17) | DOC:TPL-09 | controle_encerramento |
| Retirada total D17-A; cancelamento explícito (TPL-12, bloco 6) | DOC:TPL-12 | retirada_total; cancelamento |
| Transições agregadas (RQ-FLX-01) | DOC:RQ-FLX-01 | transicoes |
| Mínimo de observações de tendência e seu bloqueio | DOC:CAP-TEN-01.precondicoes | minimo_observacoes; bloqueio_observacoes |
| Pergunta e motivo de natureza nominal (CFG-PRV) | DOC:CFG-PRV.comportamento; DOC:CFG-PRV.privacidade | pergunta_nominal; pergunta_nominal_com_motivo; motivo_nominal |
| Insuficiência de forma documental | DOC:CFG-DOC.comportamento | insuficiencia |
| Rótulos de opções e leituras | id_doc indicados na tabela de CFG-OPC | rotulo.* |

| Tipo de pendência | Forma local de DOC:TPL-04 | id_doc do motivo pertinente | Forma local do motivo |
|---|---|---|---|
| PERTINENCIA | pergunta_pertinencia | DOC:RQ-GOV-04 | motivo_pertinencia |
| AMBIGUIDADE_MATERIAL | pergunta_ambiguidade_material | DOC:RQ-GOV-17 | motivo_ambiguidade_material |
| PARAMETRO_FALTANTE | pergunta_parametro_faltante | DOC:RQ-GOV-14 | motivo_parametro_faltante |
| DECISAO_SUBSTANTIVA | pergunta_decisao_substantiva | DOC:RQ-GOV-13 | motivo_decisao_substantiva |
| CONFLITO_DE_FONTES | pergunta_conflito_de_fontes | DOC:RQ-GOV-21 | motivo_conflito_de_fontes |
| SIGNIFICADO_DE_CAMPO | pergunta_significado_de_campo | DOC:RQ-DAD-05 | motivo_significado_de_campo |
| CONFIRMACAO_DE_USO_DA_BASE | pergunta_confirmacao_de_uso_da_base | DOC:RQ-DAD-22 | motivo_confirmacao_de_uso_da_base |
| ESTRUTURA_DE_ENTRADA | pergunta_estrutura_de_entrada | DOC:RQ-DAD-43 | motivo_estrutura_de_entrada |
| NATUREZA_DE_ENTIDADE_NOMINAL | pergunta_natureza_de_entidade_nominal | DOC:RQ-DAD-38 | motivo_natureza_de_entidade_nominal |
| REFERENCIAL_GEODESICO | pergunta_referencial_geodesico | DOC:RQ-DAD-26 | motivo_referencial_geodesico |
| LINHA | pergunta_linha | DOC:RQ-LIN-01 | motivo_linha |
| EMPATE_NO_CORTE | pergunta_empate_no_corte | DOC:CAP-SUB-03.parametros | motivo_empate_no_corte |
| CONTINUIDADE_DE_COMPOSICAO | pergunta_continuidade_de_composicao | DOC:RQ-ORQ-10 | motivo_continuidade_de_composicao |
| NATUREZA_DE_ALTERACAO | pergunta_natureza_de_alteracao | DOC:RQ-LIN-12 | motivo_natureza_de_alteracao |

#### 4.4.24. CFG-OPR — parâmetros operacionais

Até 2 regenerações do LLM após falha de validação; até 1 nova tentativa por unidade semântica independente idempotente, com orçamento preservado sob decomposição/reagrupamento (RQ-ORQ-14). O timeout é parâmetro técnico configurável por componente ou limitado pela plataforma; seu valor numérico não é fixado metodologicamente nesta SPEC, e o comportamento ao esgotá-lo segue os desfechos e modelos da SPEC (OPR-IND, OPR-FAL, TPL-01 a TPL-03). As únicas chaves de informação operacional admitidas como âncora são: data e hora corrente, com fuso ou offset quando disponível; identificador da sessão; estado estruturado da interface. Elas não fornecem fato de domínio, valor metodológico, critério analítico ou classificação substantiva. Quando o fuso ou offset não puder ser estabelecido e isso alterar materialmente a resolução de expressão temporal, cria-se pendência AMBIGUIDADE_MATERIAL (RQ-GOV-23). Parâmetro fixo da sessão: session_inactivity_timeout = 30 minutos = 1800 segundos; diferente do timeout técnico de componente. Catálogo fechado de EV-INTERACAO_USUARIO (TipoInteracaoUsuario) que renova o prazo, quando observável pela aplicação: envio de mensagem (ENVIO_MENSAGEM); upload (UPLOAD); escolha de arquivo (ESCOLHA_ARQUIVO); escolha de planilha (ESCOLHA_PLANILHA); confirmação (CONFIRMACAO); alteração de filtro analítico (ALTERACAO_FILTRO_ANALITICO); alteração de seleção analítica (ALTERACAO_SELECAO_ANALITICA); mudança de parâmetro (MUDANCA_PARAMETRO); navegação por controle efetivo da aplicação (NAVEGACAO_CONTROLE_EFETIVO); revelação explícita de conteúdo (REVELACAO_EXPLICITA); solicitação de relatório (SOLICITACAO_RELATORIO); exportação (EXPORTACAO). Não renovam: heartbeat; polling; refresh interno; renderização automática; reconexão automática sem ação do usuário; simples passagem do tempo; ação puramente local não recebida pela aplicação; processamento, retry e retornos automáticos. Cada EV-INTERACAO_USUARIO registra session_id, tipo do evento e timestamp, sem conteúdo protegido; o prazo de inatividade é contado desde o último EV-INTERACAO_USUARIO válido recebido antes da expiração. Controle Encerrar sessão e expiração são determinísticos e acionam descarte integral; aplicar prioridade de encerramento em concorrência (RQ-FLX-17).

---

## Parte 5 — Dados, metadados, universo, triagem e exame habilitador

### 5.1. Bases, autorização e sessão

- **RQ-DAD-01** — Toda base DEVE ser registrada em C-10 com identificador, versão, resumo de conteúdo, origem (OrigemBase: UPLOAD_USUARIO, DADOS_CONVERSACIONAIS_USUARIO ou FONTE_CONFIGURADA), sessão, status (StatusBase) e declaração de domínio, quando houver (base de FTS, base populacional, quadro territorial, base geográfica, outra auxiliar). A declaração de domínio decorre de fonte, metadado autorizado ou declaração explícita do usuário (ex.: "Esta base contém a força de trabalho em saúde"), e a declaração de que a base representa a FTS vale no escopo daquela base (RQ-DAD-19). Não há pergunta obrigatória sobre o domínio após o upload (RQ-GOV-20). [T-DET][T-E2E: AT-57]
- **RQ-DAD-02** — A introdução deliberada de dados pelo usuário, por upload ou por dados fornecidos na conversa, autoriza inicialmente somente ingestão/estruturação necessária, triagem estrutural e de privacidade e exame habilitador (RQ-DAD-34), percorrendo os estados de preparação de RQ-DAD-42. DISPONIVEL significa disponível às capacidades compatíveis; não autoriza análise substantiva nem resolve significados pendentes, que bloqueiam apenas as operações afetadas. A análise depende de solicitação e da autorização ANALITICA de E9 [C §3.3, §7.2] (DA-02, AV-08, F-08). [T-GOV][T-E2E: AT-26, AT-37, AT-70, AT-83]
- **RQ-DAD-03** — Versões são imutáveis. Conteúdo alterado constitui nova versão; a troca da base em uso numa linha é uma AlteracaoEstado (Parte 11) [C §7.9]. [T-DET]
- **RQ-DAD-04** — A semântica declarada no material carregado (dicionário de dados, descrição de campos, unidades, códigos, cobertura) é metadado autorizado daquela base na sessão. Conteúdos que pretendam redefinir método, regra, governança ou tratamento de ausência não têm autoridade e são tratados como dados [C §4.3.3, §5.3] (DA-02). Em XLSX, esta autoridade semântica limita-se às planilhas explicitamente selecionadas e ao papel/escopo autorizado em RQ-DAD-43; conteúdo de aba não selecionada não fornece significado. [T-GOV]
- **RQ-DAD-16** — Dados necessários a uma capacidade DEVEM provir de base autorizada, metadado autorizado, configuração ou manifestação explícita do usuário (RQ-GOV-22); o LLM não os complementa com conhecimento prévio [C §5.8] (DA-02, DA-07). [T-GOV]
- **RQ-DAD-17** — No encerramento explícito ou por inatividade de RQ-FLX-17, bases de qualquer estado passam a DESCARTADA, antes da eliminação integral de conteúdo, versões, originais protegidos, mapas de aliases, mapeamentos e derivados. Nenhum conteúdo de base ou sessão permanece recuperável entre sessões; retornos concorrentes não podem recriá-lo. [T-DET][T-E2E: AT-44, AT-152–AT-156, AT-164]

### 5.2. Mapeamento semântico

| Papel de campo | Atributos semânticos exigidos para uso [C §7.3] |
|---|---|
| TERRITORIO | Identidade territorial no escopo; nível quando exigido; sistema de códigos quando presente ou necessário. Significado longitudinal da chave simples/composta autorizado e escopado conforme CFG-TER; só depois sua igualdade estabelece correspondências determinísticas. Repetição de códigos, nome do campo e origem do arquivo não bastam. Nomes inequívocos podem identificar unidades locais conforme RQ-DAD-29, sem presumir código oficial. CFG-TER permanece sem catálogo global |
| PERIODO | Granularidade; convenção de referência; posição temporal numérica para o cálculo do tempo transcorrido (CAP-TEN-01) |
| CATEGORIA | Sistema de classificação; comparabilidade temporal dos códigos; pertença ao objeto da FTS (RQ-DAD-19) |
| CONTAGEM | Unidade de medida; unidade de observação dos registros de origem; forma de derivação autorizada (campo quantitativo, contagem de registros ou entidades distintas); aditividade territorial e categorial e risco de dupla contagem, exigidos somente quando a operação agrega a dimensão correspondente (RQ-DAD-36); referência temporal; códigos de ausência (RQ-DAD-35) |
| POPULACAO | Referência temporal; identidade e nível territorial; definição do denominador; aditividade territorial e população compartilhada entre categorias, exigidas somente quando a operação agrega a dimensão correspondente (RQ-DAD-36); códigos de ausência (CAP-AGR-01) |
| GEOMETRIA | Tipo (ponto por latitude e longitude em graus decimais, centróide, polígono); referencial geodésico (seção 5.6)  Referencial ausente segue REFERENCIAL_GEODESICO; referencial informado exige verificação de suporte em CFG-MET (RQ-DAD-26), sem CRS padrão. |
| ATRIBUTO_AUXILIAR | Significado; função auxiliar admitida |
| IDENTIFICADOR_INDIVIDUAL | Entidade identificada; âmbito de unicidade; completude; repetição legítima; condições de deduplicação dentro e entre territórios, categorias e períodos; proteção (RQ-DAD-35, seção 5.5) |

- **RQ-DAD-05** — Cada atributo semântico DEVE ter StatusSignificado e âncora. Etapa que dependa de atributo exigido pela operação (RQ-DAD-36) e INDEFINIDO ou PROPOSTO_NAO_CONFIRMADO DEVE ser bloqueada com BLQ-SIG, com pendência para que o usuário forneça ou confirme o significado [C §4.3.3, §9.2]. Na identidade territorial longitudinal, registrar a regra e suas exceções no escopo de campo/esquema de CFG-TER; pendência necessária é compartilhada por todas as correspondências abrangidas, sem confirmação por unidade. Informação desconhecida não bloqueia o exame nem operações independentes desse significado. [T-GOV]
- **RQ-DAD-06** — Significados podem ser estabelecidos por metadado autorizado, por regra determinística configurada (reconhecimento conclusivo gera AUTORIZADO_POR_CONFIGURACAO; reconhecimento que exige confirmação gera PROPOSTO_NAO_CONFIRMADO) ou por confirmação do usuário. O LLM PODE indicar correspondências entre expressões do usuário e elementos já presentes em fontes autorizadas, mas NÃO DEVE propor significado ou valor ausente para simples confirmação; faltando, o agente pede que o usuário o forneça, com opções neutras de CFG-OPC quando houver lista autorizada e sem indicar opção preferida. Para a pertença de categorias à FTS, o reconhecimento automático é o determinístico da seção 4.3, e semelhança semântica ou aproximada não a estabelece [C §7.3] (P-05, DA-04). Conteúdo de fonte autorizada só estabelece significado longitudinal quando efetivamente o declara, com origem e âncora preservadas; igualdade de chave aplica a regra, não a cria (CFG-TER). Confirmação incide sobre candidato já ancorado; se o significado estiver ausente, solicitar seu fornecimento. [T-GOV][T-E2E: AT-16, AT-55]
- **RQ-DAD-07** — Códigos de ausência DEVEM ser registrados com significado entre VALOR_ZERO_CODIFICADO, DESCONHECIDO, NAO_APLICAVEL, NAO_OBSERVADO e OUTRO_DECLARADO; somente VALOR_ZERO_CODIFICADO, estabelecido por metadado autorizado ou declaração do responsável pelos dados, produz zero. Valores ausentes não são transformados em zero, média, estimativa, exclusão ou qualquer outro valor: permanecem NAO_AVALIAVEL, salvo método autorizado em CFG-AUS (nenhum nesta versão; CFG-AUS deliberadamente vazio quanto a imputação) ou valor fornecido explicitamente pelo usuário (RQ-GOV-22). Declarações do tipo "vazio significa zero" acionam AMB-03 [C §7.3, §7.4] (DA-10). [T-DET][T-E2E: AT-33]
- **RQ-DAD-08** — Mudança posterior de significado confirmado, inclusive correção semântica explícita do usuário aceita dentro do escopo permitido, DEVE ser registrada como AlteracaoEstado: CORRECAO_OU_REPUDIO invalida os dependentes; SUBSTITUICAO_DE_ESTADO retira a vigência [C §4.3.3, §7.3] (P-10). [T-DET][T-E2E: AT-12]
- **RQ-DAD-18** — A unidade de contagem DEVE resultar de conteúdo explícito da base, metadado autorizado, regra configurada ou manifestação explícita do usuário; o nome do campo sozinho só a estabelece por regra configurada. Ela é distinta da unidade de observação. Não há conversão arbitrária entre pessoas, vínculos ou postos; contar pessoas distintas a partir de registros de vínculos por identidade autorizada é derivação admitida, conforme RQ-DAD-35 e CAP-IND-01 (DA-09, AV-03). [T-GOV][T-E2E: AT-50, AT-60]
- **RQ-DAD-36** — Cada capacidade DEVE exigir somente os atributos semânticos de que a operação executada depende, verificados no item 5 de RQ-GOV-24: (a) uma categoria em um território não exige atributo de aditividade territorial nem de compartilhamento populacional entre categorias; (b) agregação de territórios exige a aditividade territorial pertinente da contagem e da população; (c) agregação de categorias exige a forma de uso do denominador populacional entre categorias e o tratamento de sobreposição da contagem (CAP-AGR-01); (d) agregação simultânea de territórios e categorias exige ambos os conjuntos de propriedades. Aditividade é a possibilidade de somar valores de partes diferentes e tratar o resultado como o valor do conjunto, sem sobreposição ou dupla contagem indevida. Atributo não exigido pela operação não gera BLQ-SIG nem pergunta; atributo exigido e não estabelecido segue RQ-DAD-05 (F-02). Operação temporal exige o significado longitudinal territorial aplicável e suas exceções (CFG-TER), além das demais compatibilidades de seu contrato; não o exige de operação que dele não dependa. [T-GOV][T-E2E: AT-76]
- **RQ-DAD-19** — A pertença de uma categoria ao objeto da FTS é estabelecida por qualquer das vias abaixo, verificadas antes de qualquer pergunta: (a) fonte ou metadado autorizado; (b) declaração de domínio da base (RQ-DAD-01), que, no escopo daquela base, estabelece a pertença das categorias nela contidas, sem confirmação individual de cada uma; (c) reconhecimento determinístico por configuração governada com resultado FTS_INEQUIVOCA, ou FTS_CONTEXTUAL acompanhado de contexto autorizado suficiente (seção 4.3); (d) declaração explícita do usuário de que a categoria integra a FTS no contexto da análise, registrada como DECLARACAO_DE_CATEGORIA, com origem e escopo (RQ-LIN-07). A simples solicitação de uma categoria como objeto de análise não constitui declaração. A pertença estabelecida por (b) ou (d) vale apenas no respectivo escopo e não se torna classificação universal da profissão. Expressão FTS_AMBIGUA é resolvida por metadado, declaração de domínio ou contexto autorizado (ex.: única categoria candidata na base segundo as correspondências governadas de RQ-CFG-09, e não por similaridade semântica ou conhecimento latente do LLM); persistindo mais de uma leitura materialmente plausível, pergunta-se qual categoria está sendo analisada. Categoria NAO_RECONHECIDA, ou FTS_CONTEXTUAL sem âncora contextual, sem (a), (b) ou (d) gera PERTINENCIA_INCERTA e pedido de esclarecimento (RQ-GOV-04), nunca NAO_PERTINENTE por esse motivo. Quando o pedido se referir à FTS em conjunto e a composição das categorias não estiver estabelecida por essas vias, cria-se pendência para que o usuário a indique [C §3.1] (DA-04). [T-GOV][T-E2E: AT-48, AT-55, AT-56, AT-57, AT-88]

### 5.3. Universo analítico

- **RQ-DAD-09** — Universo completo exige quadro autorizado (base, metadado ou regra), metadado autorizado declarando a base exaustiva, ou lista explícita fornecida pelo usuário [C §4.3.4, §7.4]. Ausência de quadro necessário é BLQ-DAD com DetalheBloqueio.QUADRO_UNIVERSO_AUSENTE; não usar esse detalhe como motivo analítico. Seleção ativa capturada conforme RQ-FLX-16 pode definir universo explícito quando aplicável, sem presumir exaustividade de base observada. [T-GOV]
- **RQ-DAD-10** — Sem quadro, a etapa que exija universo completo DEVE ser bloqueada com BLQ-DAD com DetalheBloqueio QUADRO_UNIVERSO_AUSENTE. O agente PODE pedir a lista explícita ou oferecer, como alternativa distinta, análise sobre as unidades observadas, rotulada como tal (Parte 15). [T-GOV]
- **RQ-DAD-11** — Cada unidade do quadro recebe PRESENTE_COM_REGISTRO ou ELEGIVEL_SEM_REGISTRO; unidades presentes na base e ausentes do quadro recebem FORA_DO_UNIVERSO e são listadas em exclusões, sem conversão em zero, ausência ou não avaliável (Caso 17, P-12). [T-DET][T-E2E: AT-17]
- **RQ-DAD-12** — Agrupamentos territoriais só PODEM provir de fonte autorizada ou de composição explícita fornecida pelo usuário, registrada com origem e escopo; o LLM NÃO DEVE criá-los nem inferir sua composição [C §4.3.4, §5.8] (DA-04, DA-07). [T-GOV]

### 5.4. Exame habilitador

- **RQ-DAD-13** — Após a introdução deliberada de dados, sua ingestão/estruturação e a triagem, CAP-EXA-01 é executada automaticamente pela via HABILITADORA de RQ-DAD-34, restrita à lista abaixo. Não há exame de toda mensagem conversacional [C §3.3, §5.4] (DA-02, P-15, AV-08). [T-DET][T-E2E: AT-26, AT-65, AT-70]

| Permitido | Proibido |
|---|---|
| Estrutura, campos, tipos e número de linhas | Diagnósticos |
| Períodos, territórios e categorias disponíveis | Rankings, extremos e ordenações |
| Consistência estrutural e validade de códigos frente a quadro ou metadado | Classificações substantivas e tendências |
| Duplicidades por chave declarada | Comparações |
| Valores ausentes por campo | Magnitudes de indicadores da FTS |
| Cobertura: existência de registro por território, período e categoria | Conclusões analíticas não solicitadas |
| Semântica declarada, declaração de domínio existente e significados reconhecidos por regra, inclusive o estado de reconhecimento das categorias da base (seção 4.3), ou pendentes de confirmação | — |
| Compatibilidade entre elementos e condições de comparabilidade: distinguir códigos coincidentes de regra longitudinal autorizada, sua origem, escopo e exceções (CFG-TER) | Inferir identidade longitudinal da mera repetição de códigos |
| Matriz de aplicabilidade: condições necessárias atendidas e capacidades potencialmente habilitadas | — |

- **RQ-DAD-14** — O resultado do exame automático é SUPORTE_INTERMEDIARIO sem linha e não compõe diagnóstico. Quando o usuário solicitar o exame como entregável (FAM-01), o papel segue a seção 7.7 e o conteúdo permanece restrito à mesma lista. [T-GOV]
- **RQ-DAD-15** — A matriz de aplicabilidade é a única base admitida para afirmações do tipo "os dados permitem..." em sugestões (V-10). [T-GOV]

### 5.5. Triagem estrutural e de privacidade

- **RQ-DAD-20** — Antes de qualquer envio ao LLM, C-04 DEVE aplicar triagem determinística estrutural e de privacidade com quatro classes: A — conteúdo pessoal ou identificador protegido: proteger, nunca enviar em claro; B — entidade/papel não pessoal deterministicamente tipificado por fonte autorizada: liberar quando necessário; C — metadado textual não governado e não necessário semanticamente ao LLM, incluindo nome de campo, arquivo ou planilha: substituir por alias local, conservando o original necessário à linhagem somente em C-10; D — texto funcional não pessoal e não nominal necessário à interpretação: permitir após triagem determinística de privacidade, sem exigir tipificação como território, categoria ou organização. Verbos, operadores, qualificadores, relações, instruções e estrutura linguística necessários permanecem interpretáveis. CFG-VOC não é filtro exaustivo de toda linguagem natural. Cada campo/trecho sujeito à proteção recebe ProtecaoCampo; metadado minimizado recebe AliasMetadado, que não o classifica como pessoal. Posição nominal estruturalmente ambígua é protegida segundo RQ-DAD-38; incerteza localizada não suprime a linguagem funcional não nominal adjacente. Não se usam capitalização, aparência de nome, listas externas de nomes, conhecimento externo nem classificação pessoal pelo LLM. A fronteira cobre qualquer FN, contexto reconstruído, estrutura sanitizada, perfil de exame, opções, nomes de campos/arquivos/planilhas, eventos, linhagem, procedência, relatórios, exportações, regenerações e fallbacks. Esta triagem não transforma toda mensagem em base nem concede autorização analítica. Conteúdo nominal ou identificador originado do usuário, em qualquer posição, só atravessa a fronteira pré-LLM em claro com evidência determinística positiva de papel não pessoal — fonte autorizada, estado previamente validado no escopo, marcador ou construção governada de CFG-VOC, tipificação estrutural autorizada ou declaração explícita do usuário (classe B). Na ausência dessa evidência, recebe placeholder (classe A); se o papel for material à execução, abre-se esclarecimento (RQ-DAD-38); se não for, prossegue-se com o placeholder, sem pendência. Trecho cuja natureza nominal ou funcional não possa ser estabelecida deterministicamente com segurança é tratado como conteúdo nominal sem evidência (RQ-DAD-33). Linguagem funcional não nominal continua liberável (classe D). Conteúdo já protegido permanece protegido em toda reaparição no mesmo escopo de linhagem (RQ-DAD-39). [T-GOV][T-E2E: AT-116–AT-121, AT-164, AT-165, AT-166]
- **RQ-DAD-21** — Campos ambíguos são marcados POTENCIALMENTE_IDENTIFICADOR e seu significado DEVE ser confirmado pelo usuário antes do uso analítico (pendência SIGNIFICADO_DE_CAMPO). Campos IDENTIFICADOR_DIRETO e POTENCIALMENTE_IDENTIFICADOR são protegidos: não vão ao LLM e não aparecem em produtos analíticos; o motor PODE usá-los internamente em operações autorizadas, como contagem e deduplicação (DA-27). [T-GOV]
- **RQ-DAD-22** — Quando a triagem detectar campos potencialmente individualizantes, C-02 DEVE exibir o aviso abaixo, e a análise da base aguarda a confirmação do usuário (pendência CONFIRMACAO_DE_USO_DA_BASE). A confirmação registra manifestação do usuário e não constitui avaliação jurídica automática de conformidade. O texto é o de TPL-10, com equivalente em inglês na seção 4.4.16 (DA-27). A regra vale igualmente para pessoas confirmadas em dados conversacionais (RQ-DAD-38); natureza nominal e consentimento são decisões diferentes. Negativa impede análise e produz AUTORIZACAO_NEGADA; reversão exige manifestação explícita e nova confirmação TPL-10 na mesma sessão ativa (RQ-DAD-42). [T-GOV][T-E2E: AT-37]

> **Foram detectados campos que podem identificar ou individualizar pessoas nesta base. Antes da análise, esses campos serão tratados como protegidos. Eles poderão ser utilizados internamente apenas quando necessários a operações autorizadas, como contagem ou deduplicação, e não serão enviados ao LLM nem exibidos nos resultados analíticos. Confirme que você está autorizado a utilizar esta base.**

- **RQ-DAD-23** — O contexto de qualquer FN DEVE conter somente estrutura sanitizada, papéis, tipos, dimensões, posições e aliases; entidades não pessoais tipificadas quando necessárias, parâmetros autorizados, resultados agregados autorizados e texto funcional não nominal necessário após triagem. Nomes originais de campos, arquivos e planilhas sujeitos às classes A/C não integram contexto nem perfil de exame. Se o significado de um metadado for necessário, solicitar o papel de seu alias, por exemplo [CAMPO_1], sem encaminhar o original ao LLM; a resposta passa pela mesma triagem. Identificadores, valores protegidos e registros individuais não são enviados, inclusive para validar estruturação conversacional; originais e mapas permanecem em C-10. A classe D não exige tipificação como entidade nem enumeração integral em CFG-VOC (RQ-DAD-20/33/39). [T-GOV]
- **RQ-DAD-24** — A triagem e suas marcações são registradas (EV-TRIAGEM) e valem para a base durante a sessão. Regras adicionais de anonimização, pseudonimização ou supressão só são incorporadas por configuração governada; não há limiar universal de supressão de células pequenas nesta versão (DA-27). [INSP]
- **RQ-DAD-37** — Identificadores estruturados são reconhecidos e protegidos por regras determinísticas de CFG-PRV antes de qualquer envio ao LLM: (a) CPF confirmado exige cumulativamente 11 dígitos, formato compatível, dígitos verificadores válidos pelo algoritmo do CPF e sequência que não seja formada por dígitos todos idênticos, e é protegido, salvo papel estrutural explicitamente tipado e autorizado como código não pessoal (passo 1 abaixo); valor em campo ou construção explicitamente identificada como CPF permanece protegido mesmo que falhe na validação, sem ser classificado como CPF válido; (b) endereço com sintaxe válida de e-mail é protegido, sem verificação da existência da caixa postal; (c) telefone é protegido quando está em campo semanticamente identificado como telefone, celular, phone ou mobile, quando acompanhado de marcador explícito de CFG-PRV ou quando tem forma internacional inequívoca, com prefixo + e código de país; número isolado não é classificado como telefone apenas pela quantidade de dígitos; (d) valores de campo semanticamente estabelecido como nome ou identificador individual, segundo a lista de CFG-PRV, são protegidos. Em dados estruturados individualizados, a classificação usa cabeçalhos, metadados, estrutura da base e confirmações semânticas; campo cujo papel identificador permaneça materialmente incerto é POTENCIALMENTE_IDENTIFICADOR (RQ-DAD-21) (F-01). A associação estrutural inequívoca entre rótulo pessoal governado e valor em texto livre protege esse valor independentemente de formato CPF. Ordem determinística: 1. papel estrutural explicitamente tipado e autorizado; 2. rótulo governado de identificador pessoal de CFG-PRV — CPF, CNS_PROF, NOME_PROF quando representar dado pessoal, CRM, COREN, NIS, matrícula profissional, registro profissional, identificador do profissional, ID do trabalhador, employee ID, staff number e equivalentes ali governados; 3. padrão governado inequívoco, sem depender exclusivamente de marcador lexical exato, como CPF por formato e dígitos verificadores, e-mail por sintaxe e telefone em forma internacional inequívoca; 4. papel não resolvido → proteção por padrão. Valor tipificado explicitamente como código territorial continua territorial mesmo quando seus dígitos coincidem com CPF válido. Rótulo CPF protege inclusive valor inválido. Código territorial ou institucional deterministicamente tipificado não se torna pessoal apenas pela forma numérica. "Matrícula" isolada ou outro rótulo materialmente ambíguo é protegido por padrão; pergunta-se somente se a distinção for necessária à execução. A regra não recorre a listas externas de pessoas. [T-DET][T-GOV][T-E2E: AT-37, AT-74, AT-168]
- **RQ-DAD-38** — Em texto livre, expressão potencialmente nominal só é liberada como não pessoal quando seu papel estiver estabelecido, com evidência determinística positiva, por fonte autorizada, estado previamente validado, estrutura linguística governada ou declaração explícita do usuário. É reconhecida como território quando consta de base ou quadro territorial carregado, quando já está estabelecida como território no estado aplicável da conversa ou da linha, ou quando está explicitamente tipificada na própria construção por marcador territorial de CFG-VOC (ex.: "município de X", "cidade de X", "estado de Y", "província de Z"); construção institucional inequívoca com marcador de organização de CFG-VOC é tratada como entidade não pessoal. CFG-TER é deliberadamente vazio e o sistema não usa catálogo territorial ou catálogo de cidades. Expressão materialmente ambígua recebe ENTIDADE_NOMINAL_AMBIGUA, permanece protegida e não é enviada ao LLM como conteúdo liberado; quando sua identidade for necessária a uma operação, C-02 apresenta a pergunta determinística de CFG-PRV (pendência NATUREZA_DE_ENTIDADE_NOMINAL, habilitadora quando necessária à materialização de dados, analítica nos demais casos), usando alias na pergunta e permitindo acesso explícito ao original somente no visualizador protegido, sem enviá-lo ao LLM. Efeitos da resposta: território autoriza a tipificação territorial no escopo aplicável; organização ou instituição e outra entidade não pessoal liberam a expressão, preservando o tipo declarado; pessoa e manter protegida mantêm a proteção. Confirmação como PESSOA em dados conversacionais caracteriza entrada individualizada e exige CONFIRMACAO_DE_USO_DA_BASE/TPL-10: confirmar natureza não confirma autorização de uso. Após autorização e habilitação, identidade indispensável só pode ser usada internamente em operação permitida; análise individual continua excluída. Sem autorização, aplicar RQ-DAD-42; manter protegida sem papel suficiente conserva pendente somente a operação que dele dependa. O LLM não decide se a expressão designa pessoa ou entidade não pessoal (F-01). A identificação prévia de expressão potencialmente nominal é determinística: ENTIDADE_NOMINAL_AMBIGUA exige cumulativamente posição funcional de entidade em padrão de CFG-VOC, papel não estabelecido pelas vias autorizadas e ausência de marcador governado suficiente; a necessidade de decidir sua natureza determina somente a abertura de esclarecimento, nunca a liberação em claro. "Vitória tinha 10 médicos em 2024" ocupa a posição ENTIDADE sem papel e é protegida; "o município de Vitória tinha 10 médicos em 2024" e "a cidade de Vitória teve 10 médicos em 2024" têm marcador TERRITORIO, sem pendência de natureza, com a mesma decisão estrutural de "the city of Vitória had 10 physicians in 2024". Expressão já protegida permanece protegida quando reaparece em outra posição ou mensagem do mesmo escopo de linhagem (RQ-DAD-39). Capitalização isolada não basta para reconhecer nem liberar; não se usam listas de pessoas, bases externas de nomes ou classificação do LLM. Reconhecer essa posição não exige conhecer a identidade real. Posição reconhecida sem delimitação segura do trecho exige retenção conservadora e esclarecimento determinístico de RQ-DAD-33, sem envio em claro. A tipificação registra expressão/referência, papel, origem, âncora e escopo explícito; não é propagada para contexto materialmente distinto sem autoridade. Esta regra tipifica posições nominais de entidade, não toda linguagem natural. Texto funcional não nominal da classe D de RQ-DAD-20 permanece disponível após triagem; metadados da classe C seguem minimização mesmo quando não classificados como pessoais. [T-DET][T-GOV][T-E2E: AT-63, AT-75, AT-165–AT-167]
- **RQ-DAD-39** — Conteúdo pessoal protegido entregue ao LLM DEVE ser substituído por [CPF_n], [EMAIL_n], [TELEFONE_n], [PESSOA_n], [IDENTIFICADOR_n] ou [ENTIDADE_PROTEGIDA_n]. O mesmo valor protegido recebe o mesmo placeholder na sessão somente quando sua igualdade puder ser determinada com segurança; caso contrário, recebe outro. Metadados sujeitos à minimização usam [CAMPO_n], [ARQUIVO_n] e [PLANILHA_n], estáveis por identidade da entrada/versão e posição estrutural; igualdade textual em entradas distintas não transfere identidade, autorização ou negativa. O original necessário à linhagem e o mapa alias↔original ficam exclusivamente em C-10, nunca no LLM, eventos ou produtos; são eliminados ao encerrar a sessão. A substituição precede FN-INT-01 e qualquer fallback. Categorias, indicadores, períodos, quantidades e entidades não pessoais autorizadas podem ser liberados quando necessários, assim como entidades não pessoais com evidência positiva (classe B) e linguagem funcional não nominal triada (classe D); nomes de campos não possuem liberação genérica. Necessidade semântica não libera metadado original: esclarecer o papel pelo alias, conforme RQ-DAD-23. Delimitação nominal insegura exige retenção localizada e esclarecimento, sem bloquear genericamente o texto funcional. Conteúdo previamente classificado como protegido permanece protegido no mesmo escopo de linhagem — mensagens posteriores da sessão e contextos, entradas, bases e derivados que contenham ou reproduzam a ocorrência —, independentemente da posição em que reapareça, até evidência determinística positiva de papel não pessoal no escopo aplicável (RQ-DAD-38); recebe o mesmo placeholder quando a igualdade puder ser determinada com segurança. Essa persistência não transfere identidade de alias, autorização ou negativa entre entradas distintas. [T-DET][T-GOV][T-E2E: AT-116–AT-121, AT-166]

### 5.6. Coordenadas e referencial geodésico

- **RQ-DAD-25** — Campos de latitude e longitude em graus decimais são reconhecidos por regra configurada que combina nome de campo, tipo numérico e validade dos valores (latitude entre −90 e 90; longitude entre −180 e 180). Faltando um desses elementos, o significado fica PROPOSTO_NAO_CONFIRMADO e requer confirmação do usuário. Valor fora da faixa torna o elemento NAO_AVALIAVEL (COORDENADA_INVALIDA) (DA-17). Validade numérica de coordenadas e reconhecimento do campo não estabelecem referencial nem suporte geodésico; aplicar separadamente RQ-DAD-26. [T-DET][T-E2E: AT-51]
- **RQ-DAD-26** — O referencial geodésico é o informado por metadado, fonte autorizada, configuração contextual autorizada em CFG-MET ou pelo usuário, sem exigência de informação registro a registro. SIRGAS2000 DEVE ser suportado nativamente, sem ser presumido como padrão universal. A Configuração Inicial de Implementação não contém referencial padrão, global ou por contexto (seção 4.4.5): sem referencial informado, cria-se pendência REFERENCIAL_GEODESICO e a análise espacial aguarda esclarecimento (DA-17). Identificar o referencial não comprova suporte: C-04 verifica pertencimento ao conjunto de CFG-MET. Se suportado, prosseguir com método/parâmetros autorizados; se informado e não suportado, não executar a operação espacial, registrar BLQ-MET com METODO_NAO_INCORPORADO, sem transformá-lo, aproximá-lo ou substituí-lo. A base não se torna BLOQUEADA por esse motivo e permanece utilizável em capacidades independentes. A lista suportada pode ser informada sem sugerir o referencial dos dados. [T-GOV][T-E2E: AT-51]
- **RQ-DAD-27** — Pontos com referenciais diferentes só são usados em conjunto se houver transformação autorizada entre eles; nesta versão não há transformação incorporada (CFG-MET), e a etapa recebe BLQ-MET. Mesmo sem mistura de referenciais, um referencial conhecido não suportado impede a operação conforme RQ-DAD-26; não há transformação automática incorporada nesta versão. [T-GOV]

### 5.7. Contrato de entrada e normalização

- **RQ-DAD-28** — O sistema DEVE aceitar, pelas duas portas de CFG-FON, upload de arquivos estruturados pela interface conversacional — no mínimo CSV e XLSX (RQ-DAD-43) — e dados fornecidos diretamente na conversa. Arquivos admitem, no mínimo, tabela longa, tabela larga simples, base individualizada, arquivos auxiliares separados (FTS, população, quadro territorial e geometria) e dimensões constantes declaradas por metadado ou pelo usuário para toda a base. A representação interna PODE ser canônica; o usuário não precisa prepará-la previamente. Aplicam-se os mesmos papéis semânticos e contratos às duas portas (AV-02). [INSP][T-E2E: AT-59, AT-60, AT-61, AT-62, AT-63]
- **RQ-DAD-29** — A normalização DEVE preservar fonte, valores e associações entre dimensões, com correspondência rastreável entre células/cabeçalhos originais e registros internos. Em tabela larga simples, categoria, período ou outra dimensão de cabeçalhos só é extraída por correspondência autorizada (metadado, CFG-VOC ou manifestação explícita); ambiguidade material gera esclarecimento antes da operação afetada. Dimensão constante válida é aplicada aos registros no escopo declarado, sem exigir coluna física nem confirmação redundante. Nomes territoriais podem identificar unidades locais quando forem inequívocos no escopo; código oficial, nível ou pertencimento não é inventado. Quando necessário à capacidade e não estabelecido, pede-se o elemento faltante (RQ-DAD-05). [T-DET][T-GOV][T-E2E: AT-59, AT-62]
- **RQ-DAD-30** — Antes de combinar arquivos ou registros, C-04 DEVE verificar identidade e nível territorial, período e demais dimensões relevantes, granularidade, cardinalidade das chaves, duplicidades, conflitos e suporte da correspondência. População e geometria compartilhadas podem relacionar-se a várias categorias ou registros, mas sua repetição física não multiplica a medida; chaves do denominador seguem CAP-AGR-01. Junção muitos-para-muitos que multiplique registros ou medidas sem relação autorizada é bloqueada. Duplicidades não são descartadas nem somadas por aparência: sua interpretação exige dado, metadado ou regra autorizada; conflitos seguem RQ-GOV-21. Linhas elementares, níveis distintos, totais e subtotais DEVEM ser identificados e separados antes da operação afetada; não são somados conjuntamente. Indeterminação material gera BLQ-SIG ou BLQ-DEC com esclarecimento do significado ou da escolha necessária; nenhuma nova correspondência territorial é inferida pelo LLM. A igualdade de chaves só opera correspondência temporal sob significado longitudinal autorizado em CFG-TER, sem inferir estabilidade pela repetição; manter escopo, cardinalidade e exceções. Seleção de planilhas de XLSX não constitui autorização da combinação: RQ-DAD-43 determina finalidade e regra antes de aplicar estas verificações; não presumir esquema, período ou correspondência a partir do nome das abas. [T-DET][T-GOV][T-E2E: AT-61]
- **RQ-DAD-43** — Em upload, o sistema DEVE aceitar CSV e XLSX. Em CSV, o separador vírgula ou ponto e vírgula é determinado deterministicamente quando inequívoco; ambiguidade que altere a estrutura gera pendência habilitadora ESTRUTURA_DE_ENTRADA. Em XLSX com mais de uma planilha materialmente utilizável, quando pedido e contexto não determinarem qual usar, as planilhas disponíveis são apresentadas para escolha (ESTRUTURA_DE_ENTRADA), sem seleção substantiva pelo sistema. Dados na conversa não têm limite metodológico fixo de linhas e são aceitos enquanto puderem ser recebidos e materializados integralmente nos limites operacionais da plataforma e da sessão; se o limite técnico impedir a materialização integral, o sistema não trunca, não amostra silenciosamente, não analisa a parte recebida como se fosse o conjunto completo, informa a limitação e orienta o fornecimento por arquivo estruturado, e a entrada fica BLOQUEADA (RQ-DAD-42). Não há fonte externa configurada (CFG-FON). Selecionar duas ou mais planilhas autoriza utilizá-las, não concatenar, juntar, empilhar, unir ou relacionar temporalmente. Pedido/contexto deve determinar entradas independentes ou base combinada; intenção inequívoca prossegue, leituras materialmente plausíveis geram ESTRUTURA_DE_ENTRADA para esclarecer especificamente a finalidade restante, sem repetir a seleção já resolvida. Entradas independentes são materializadas e examinadas separadamente, com origem arquivo/planilha e escopo próprios; análise posterior entre elas segue os contratos de comparação, composição, consolidação, agregação ou temporalidade. Base combinada só é materializada após RQ-DAD-30, com esquema, dimensões, granularidade, chaves, cardinalidade, correspondência, compatibilidade e significado autorizados; sem regra única de combinação, há pendência e nenhuma escolha silenciosa. "Use as duas" não significa concatenação; nomes como Dados_2023 e Dados_2024 não autorizam períodos ou série temporal. Preservar linhagem de todas as planilhas e da regra aplicada. Abas não selecionadas não são materializadas, lidas semanticamente, interpretadas como dicionário/notas, usadas como metadados nem incluídas em contexto. Enumerar tecnicamente as abas para escolha é permitido por identidade/alias, sem ler células para extrair semântica. PapelPlanilha distingue DADOS_ANALITICOS de FONTE_AUXILIAR_DE_METADADOS; ambas exigem seleção explícita, triagem/privacidade, confirmação quando cabível, origem e escopo próprios. Fonte auxiliar registra vínculos às bases e campos destinatários; a finalidade independente/combinada é decisão ortogonal. Notas livres não redefinem métodos nem dispensam esclarecimento semântico. Em impossibilidade de materialização integral, registrar MATERIALIZACAO_INTEGRAL_IMPOSSIVEL, EV-FALHA/ESTADO-BASE e TPL-13 PT/EN: não truncar, amostrar ou analisar parcialmente. Preservar mensagem/âncora do pedido concomitante e associação à entrada; se solicitação já reconhecida, ela aguarda habilitação, caso contrário preservar vínculo sem fabricar interpretação. Pendência HABILITADORA/ESTRUTURA_DE_ENTRADA solicita arquivo substituto em formato já admitido. O arquivo é nova entrada; sua associação explícita e habilitação resolvem a pendência e retomam somente o processamento pertinente do pedido, sem exigir repetição nem reabrir solicitação terminal. A entrada impossível continua BLOQUEADA. A mensagem técnica não é limitação metodológica de resultado inexistente. [T-DET][T-GOV][T-E2E: AT-89]

### 5.8. Dados fornecidos na conversa

- **RQ-DAD-31** — Uma mensagem PODE conter simultaneamente conteúdo conversacional, dados, pedido analítico, resposta a pendência e controle (RQ-FLX-21). FN-INT-01 PODE propor estruturação dos dados explícitos em registros e dimensões; sua saída permanece INTERPRETACAO_LLM. C-04 DEVE verificar deterministicamente, contra a manifestação original protegida em C-10 e as correspondências governadas, cada valor, entidade, unidade, período e associação proposta (RQ-DAD-41), com localizadores de trechos/células e regras de normalização de CFG-VOC, sem resolver ambiguidade numérica substantiva somente pelo idioma da sessão. A presença isolada dos valores na mensagem não basta para validar relações entre eles. Conteúdo não sustentado é rejeitado; ambiguidade material exige esclarecimento; conteúdo inequívoco não exige confirmação redundante. A fonte factual permanece MANIFESTACAO_USUARIO/AFIRMACAO_PROPRIA, mesmo após materialização em base, sem atribuição ao LLM e sem validação externa de veracidade (RQ-GOV-22). A estruturação somente recebe conteúdo já sanitizado pela identificação estrutural de entidades em RQ-DAD-38; a verificação das associações não substitui a proteção pré-LLM. Em mensagem com dados e pedido, a ordem é determinística: primeiro verificar se os dados podem ser estruturalmente associados e materializados; somente depois avaliar ambiguidade material de interpretação. Se a estrutura ou a materialização não fechar, abre-se pendência habilitadora ESTRUTURA_DE_ENTRADA; se fechar e houver duas ou mais interpretações materialmente diferentes, AMBIGUIDADE_MATERIAL; coexistindo ambas, ESTRUTURA_DE_ENTRADA precede AMBIGUIDADE_MATERIAL (RQ-FLX-01). [T-GOV][T-E2E: AT-63, AT-64, AT-174]
- **RQ-DAD-32** — Pequena base conversacional (RQ-DAD-40) PODE ser materializada em base temporária da sessão, com origem DADOS_CONVERSACIONAIS_USUARIO, âncoras originais por registro e escopo definido pelo conjunto fornecido, submetido à ingestão, triagem e exame. Seu uso posterior exige seleção no escopo da análise e verificações normais, sem propagação de critérios ou decisões locais. Valor factual complementar (ex.: população de um território/período) permanece em ParametroDecisao/VALOR_FACTUAL, conforme RQ-GOV-22 e RQ-LIN-21, preservando objeto, âncora e escopo factual; fornecido sem linha aplicável, é recuperável por qualquer linha compatível da sessão, sem exclusividade, sem criar base artificial ou repetir exame completo; declaração semântica segue RQ-DAD-40. Saudações, agradecimentos e perguntas sobre capacidades não iniciam ingestão; fatos citados apenas como exemplo, hipótese ou pergunta não são automaticamente dados de análise. EXC-06 permanece aplicável à interpretação sistemática de documentos não estruturados. [T-GOV][T-E2E: AT-63, AT-64, AT-65]
- **RQ-DAD-33** — A proteção da seção 5.5 incide também sobre a mensagem original antes de FN-INT-01: C-04 retém identificadores, registros individualizados e trechos potencialmente identificadores, entregando ao LLM somente conteúdo sanitizado. Trecho cuja proteção, natureza nominal ou estrutura não possa ser estabelecida com segurança permanece retido; quando sua estrutura, significado ou natureza for material à execução, C-02 solicita esclarecimento (pendência ESTRUTURA_DE_ENTRADA, SIGNIFICADO_DE_CAMPO ou NATUREZA_DE_ENTIDADE_NOMINAL, conforme o caso) sem enviar o conteúdo ao LLM e sem reproduzir valores protegidos, com eventual revelação explícita restrita ao visualizador protegido de RQ-DAD-38; quando não for material, prossegue-se com placeholder (RQ-DAD-20). Registros individualizados estruturados podem ser ingeridos deterministicamente em C-10; não dependem de exposição ao LLM para estruturação. O original necessário à conferência de RQ-DAD-31 fica restrito a C-10 durante a sessão, com acesso determinístico, e não é copiado para contexto, eventos ou produtos; eventos guardam localizadores e marcações sem valores protegidos (RQ-RAS-07). Aplicam-se o aviso, a confirmação de uso, o uso interno autorizado e o descarte já previstos; dados pessoais na conversa não autorizam exposição analítica. A retenção é aplicada às classes A/C e aos trechos nominais estruturalmente incertos; preservar a linguagem funcional não nominal necessária da classe D de RQ-DAD-20. Nenhum original minimizado retorna por âncora, erro, procedência, fallback ou reconstrução de histórico. [T-GOV][T-E2E: AT-73, AT-165]
- **RQ-DAD-40** — Dados fornecidos na conversa são classificados, com validação de C-04, em: (a) PEQUENA_BASE_CONVERSACIONAL, quando a mensagem contém conjunto de registros ou dados que pode existir como dataset independente (ex.: "A tinha 10 médicos, B tinha 20 e C tinha 30 em 2024"), materializada conforme RQ-DAD-32; (b) VALOR_FACTUAL_COMPLEMENTAR, quando o valor completa objeto, base, recorte ou análise identificável (ex.: "Use população de 3 milhões para o território X em 2024"), registrado como ParametroDecisao/VALOR_FACTUAL com o escopo de RQ-LIN-21, preservada a associação ao objeto e, quando existente, à solicitação/linha aplicável; sem linha aplicável na manifestação, a recuperação posterior por linhas compatíveis não transfere nem consome o valor, sem criar base; (c) DECLARACAO_SEMANTICA, quando informa significado sobre base ou elemento existente (ex.: "Esta base é de médicos de 2024"), que estabelece ou atualiza metadado, dimensão constante ou significado no escopo apropriado, com origem MANIFESTACAO_USUARIO e StatusSignificado CONFIRMADO_PELO_USUARIO, sem criar base e, quando alterar significado já estabelecido, segundo RQ-DAD-08. Classificação materialmente ambígua entre essas formas gera esclarecimento (F-06). [T-GOV][T-E2E: AT-63, AT-64, AT-81]
- **RQ-DAD-41** — A associação entre entidades, valores, períodos e categorias fornecidos na conversa só é aceita automaticamente quando houver uma única relação estrutural materialmente plausível segundo os padrões de CFG-VOC (seção 4.4.9): par explícito (`A: 10`, `A = 10`); entidade e valor na mesma construção, por verbo governado (ex.: "A tem 10 médicos"); tabela ou lista repetitiva com estrutura inequívoca; duas listas de mesma cardinalidade ligadas por "respectivamente" ou "respectively", com correspondência por posição; continuação elíptica de padrão já estabelecido, quando existir uma única associação estrutural possível. O LLM PODE propor estrutura candidata, mas cada associação aceita DEVE ser validável deterministicamente contra o texto original protegido em C-10 (RQ-DAD-31); com duas ou mais associações plausíveis, o sistema não escolhe e solicita esclarecimento por pendência habilitadora ESTRUTURA_DE_ENTRADA, anterior a qualquer AMBIGUIDADE_MATERIAL de interpretação do pedido (RQ-DAD-31) (F-11). Associação estrutural única não resolve notação numérica ambígua: o valor segue CFG-VOC e, se necessário, esclarecimento antes da normalização. Os padrões de associação também delimitam posições funcionais de entidade na triagem de CFG-PRV; reconhecer a associação não estabelece, por si, a natureza da entidade (RQ-DAD-38). Ambiguidade numérica anterior à linha/solicitação usa pendência HABILITADORA/ESTRUTURA_DE_ENTRADA vinculada à entrada/base; não criar objetos analíticos fictícios. Esclarecimento sobre campo/esquema usa OBJETO com entrada/base, versão, esquema, campos, períodos, unidades e exceções autorizadas (H1). [T-GOV][T-E2E: AT-85]

### 5.9. Via de habilitação e identidade de contagem

- **RQ-DAD-34** — O ato de introduzir deliberadamente dados autoriza apenas sua habilitação; C-04 registra autorização HABILITADORA vinculada ao evento e à entrada original identificada, limitada a ingestão/estruturação necessária, triagens e CAP-EXA-01. A proteção preliminar de mensagens precede sua leitura; identificar função DADOS não executa análise. O registro identifica entrada, hash original, sessão, snapshot e operações permitidas; base e versão são vinculadas após materialização, sem exigir que já existam para iniciar estruturação. Proposta conversacional precisa ser validada por RQ-DAD-31 antes de materialização/exame, sem nova autorização do usuário. Para CAP-EXA-01, C-04 verifica entrada presente e íntegra, triagem concluída, contrato restrito ao exame, capacidade disponível, configuração aplicável e rastreabilidade; C-06 aceita a entrada a partir de TRIADA — inclusive em AGUARDANDO_CONFIRMACAO, sobre a versão protegida — sem exigir DISPONIVEL, plano analítico, linha ou E9. Significados desconhecidos são reportados no perfil, não presumidos nem exigidos para poder examiná-los. O perfil referencia essa autorização e a entrada, permanece SUPORTE_INTERMEDIARIO sem linha e não produz achados substantivos. A via não habilita outra capacidade e não satisfaz autorização ANALITICA. Para fonte configurada, quando houver, a permissão de ingestão deve constar em CFG-FON e sujeita-se às mesmas restrições. Exame pedido como entregável analítico segue E9 e a seção 7.7, com o mesmo limite de conteúdo. BLOQUEADA por AUTORIZACAO_NEGADA não autoriza exame nem manutenção de perfil ativo. Negativa revoga contextos, perfis, estruturas sanitizadas e derivados ativos, inclusive caches, histórico reconstruído, reuso e sugestões; originais necessários permanecem protegidos exclusivamente em C-10 até o fim da sessão, sem utilização analítica. Reversão explícita não reativa automaticamente a autorização nem os derivados anteriores; após nova confirmação positiva, a triagem e o exame necessários são refeitos sobre o original protegido ainda guardado em C-10, pela via HABILITADORA da mesma entrada (RQ-DAD-42). Retorno tardio deve revalidar autorização e sessão antes de qualquer publicação. [T-GOV][T-E2E: AT-70, AT-124]
- **RQ-DAD-35** — C-10 DEVE distinguir unidade de observação, unidade de contagem e identidade de deduplicação. Esta registra, com âncoras, a entidade identificada, âmbito de unicidade (inclusive entre arquivos, territórios, categorias e períodos quando necessários), completude no recorte, repetição legítima e regra de identidade autorizada. Uma linha por vínculo sustenta pessoas distintas quando a identidade de pessoa cobre a operação e as demais pré-condições são atendidas; a ausência de coluna física de quantidade não impede contagem determinística. Chave de vínculo não vira chave de pessoa, e código único somente dentro de município não deduplica pessoas entre municípios sem correspondência autorizada. Identidades ausentes ou ambíguas impedem a contagem única nos elementos afetados; não são descartadas silenciosamente nem presumidas distintas. Repetições legítimas da mesma pessoa são deduplicadas dentro de cada território/categoria/período ou sobre a união autorizada no agregado; períodos são contados separadamente, sem soma temporal implícita. A correspondência longitudinal de CAP-ROT-01 exige identidade de pessoa válida nos dois períodos e no domínio da unidade ou da união analisada; identidade válida apenas dentro de um período ou de um componente não sustenta permanência ou saída fora desse domínio. Identificadores protegidos ficam apenas no processamento interno, nunca nas saídas (CAP-IND-01, CAP-AGR-01, CAP-ROT-01, Parte 18). Quando necessário esclarecer significado longitudinal, a pendência tem escopo OBJETO do campo/esquema; resposta aplica-se em massa às correspondências abrangidas, com exceções preservadas, sem criação artificial de linha. [T-DET][T-GOV][T-E2E: AT-50, AT-60, ROT-AT-05, ROT-AT-07]
- **RQ-DAD-42** — C-10 DEVE registrar o estado de preparação de cada entrada ou base (StatusBase) e suas transições (EV-ESTADO-BASE): RECEBIDA → TRIADA, ao concluir a triagem determinística, que antecede qualquer envio ao LLM; TRIADA → EXAMINADA, ao concluir CAP-EXA-01 sobre a versão protegida, quando a estrutura estiver estabelecida; TRIADA ou EXAMINADA → AGUARDANDO_CONFIRMACAO, enquanto houver pendência habilitadora aberta que condicione o uso da entrada como um todo (confirmação de uso de RQ-DAD-22; estrutura da entrada de RQ-DAD-43; natureza de entidade nominal necessária à materialização de RQ-DAD-38); resolvidas essas pendências, a entrada segue para o exame, se ainda não concluído, e depois para DISPONIVEL; EXAMINADA → DISPONIVEL, com exame concluído e sem pendência habilitadora aberta; estado não terminal → BLOQUEADA, quando impedimento que afete a entrada como um todo não puder ser resolvido por pendência habilitadora (materialização integral impossível, RQ-DAD-43; autorização de uso negada pelo usuário; falha de integridade da entrada); qualquer estado → DESCARTADA, ao fim da sessão (RQ-DAD-17). O exame determinístico PODE operar sobre a versão protegida enquanto a confirmação de uso aguarda, e o registro indica se foi concluído. Pendência habilitadora vincula-se à entrada ou base; pendência analítica exige solicitação e só referencia linha quando legitimamente existente. Antes disso usa escopo SOLICITACAO ou OBJETO, sem linha fictícia. Qualquer uso que dependa de pendência não resolvida aguarda sua resolução; significados pendentes que não condicionem a base como um todo bloqueiam apenas as operações afetadas (RQ-DAD-05) (F-08). No caminho de entradas independentes de RQ-DAD-43, cada planilha tem estado, origem, escopo e exame próprios. Pendência de combinação não impede uma entrada independente já autorizada e materializável; a base combinada preserva origens e regra da composição. Nenhuma dessas situações amplia as causas fechadas de BLOQUEADA. MotivoBloqueioBase materializa exatamente MATERIALIZACAO_INTEGRAL_IMPOSSIVEL, AUTORIZACAO_NEGADA e FALHA_INTEGRIDADE. Na negativa, remover imediatamente perfil de exame, estrutura sanitizada, contexto e derivados ativos de todos os consumidores, incluindo reconstrução histórica, reuso e sugestões. A negativa leva a base a BLOQUEADA. A reversão deve ser explícita e inequívoca, na mesma sessão ativa, e não reativa automaticamente a autorização anterior: abre novo ciclo BLOQUEADA → AGUARDANDO_CONFIRMACAO, com TPL-10 reapresentado → confirmação positiva → triagem e exame necessários refeitos sobre o original protegido ainda guardado em C-10 → DISPONIVEL; a base permanece AGUARDANDO_CONFIRMACAO até a conclusão dessas etapas, e resposta insuficiente mantém a espera. A negativa anterior permanece histórica; perfis, estruturas sanitizadas, contextos e derivados anteriores não são reativados automaticamente. Se o original protegido já tiver sido descartado, a reversão não restaura a base: é necessária nova entrada. Nenhuma autorização ou negativa atravessa sessões. Isso não reabre entregáveis terminais. Nova carga, mesmo com hash idêntico, é nova entrada sem herdar autorização ou negativa. Bloqueios por integridade ou materialização impossível não admitem essa reversão. A tabela consolidada de estados da seção 6.3.1 é obrigatória. [T-DET][T-GOV][T-E2E: AT-70, AT-83, AT-89, AT-124]

---

## Parte 6 — Ciclo de vida da sessão e da solicitação

### 6.1. Sessão, idioma e avisos

- **RQ-FLX-17** — A sessão é temporária, isolada, sem conta/login, com snapshot fixo. CFG-OPR fixa session_inactivity_timeout = 30 minutos = 1800 segundos. C-08 registra ultima_interacao_efetiva e expira_em; somente EV-INTERACAO_USUARIO do catálogo fechado de CFG-OPR, validamente recebido antes da expiração e registrado com session_id, tipo e timestamp, renova o marco. Heartbeat, polling, refresh interno, renderização automática, reconexão automática sem ação do usuário, simples passagem do tempo, ação puramente local não recebida pela aplicação, processamento, retry, mensagens automáticas e retorno automático do LLM não renovam. Controle Encerrar sessão encerra imediatamente com ENCERRAMENTO_EXPLICITO; inatividade maior ou igual a 1800 segundos encerra com INATIVIDADE. Fechar a interface, desconectar ou colocar em segundo plano não encerra imediatamente. Reconexão tecnicamente possível antes da expiração mantém a mesma sessão e snapshot; após expiração, acesso cria nova sessão sem retomada ou recuperação de conteúdo anterior. No encerramento, todas as bases passam a DESCARTADA e são eliminados bases/versões, originais protegidos, mapas alias↔original, contextos, linhas, resultados, pendências, solicitações não terminais e todo conteúdo e rastreabilidade da sessão. C-13 é append-only apenas durante a sessão ativa; eventos de encerramento/descarte precedem a eliminação e não autorizam persistência entre sessões. Encerramento prevalece sobre upload, retry, resposta LLM e conclusão concorrentes; verificar estado/prazo/geração antes de aceitar qualquer retorno, descartando os tardios sem recriar objetos. Não converter encerramento de sessão em cancelamento implícito de solicitação. Aviso prévio de expiração não é obrigatório. [T-DET][T-E2E: AT-44, AT-152–AT-156, AT-164, AT-175]
- **RQ-FLX-18** — O idioma da sessão é português ou inglês: o escolhido explicitamente pelo usuário ou, na falta de escolha, o idioma predominante das mensagens do usuário, determinado deterministicamente; antes da primeira mensagem, vale o idioma da interface. O agente responde, pergunta, informa limitações e apresenta resultados no idioma da sessão. O idioma não altera métodos, capacidades ou conceitos internos; expressões equivalentes mapeiam para os mesmos conceitos; não há troca silenciosa de idioma como contingência (DA-05). [T-GOV][T-E2E: AT-43]
- **RQ-FLX-19** — No início da sessão, a interface DEVE exibir de forma clara o aviso abaixo, no idioma da sessão (DA-24). [T-E2E: AT-44]

> **Esta sessão e seu conteúdo são eliminados ao acionar Encerrar sessão ou após 30 minutos (1800 segundos) sem interação efetiva sua. Fechar a interface não encerra imediatamente. Atividade automática não renova o prazo. Exporte o que deseja conservar antes do encerramento; não há retomada entre sessões.**

O texto é o de TPL-09, com equivalente em inglês na seção 4.4.16.

- **RQ-FLX-20** — Expressão que não possa ser ancorada com segurança em elemento autorizado, em qualquer dos idiomas, gera pedido de esclarecimento, e não inferência silenciosa (DA-05). [T-GOV]

### 6.2. Estágios da solicitação

| Estágio | Responsável | Produz | Desvios |
|---|---|---|---|
| E0 Recepção e proteção | C-01, C-04, C-10, C-13 | Mensagem sanitizada por triagem determinística, com placeholders e entidades nominais ambíguas protegidas (RQ-DAD-33, RQ-DAD-37 a RQ-DAD-39), e evento sem valores protegidos; snapshot da seleção ativa capturado no envio, por RQ-FLX-16 | Upload segue a via HABILITADORA; controles não abrem análise (RQ-FLX-14) |
| E1 Leitura mínima e recuperação de contexto | C-08, C-03 (FN-INT-01), C-04 | LeituraMinima com funções coexistentes e proposta de dados explícitos, quando houver | Dados validados seguem RQ-DAD-34; retoma-se a parte analítica após habilitação; mensagem sem dados não gera exame; LLM indisponível: Parte 16 |
| E2 Pertinência | C-04 | Pertinencia por parte | NAO_PERTINENTE: ADM-NP. PERTINENCIA_INCERTA: pendência |
| E3 Admissibilidade preliminar | C-04 | Família admitida ou ADM-FE | Seção 7.3 |
| E4 Interpretação operacional e reavaliação da admissibilidade | C-03 (FN-INT-02), C-04 (validação) | InterpretacaoOperacional validada | Âncora inválida: regeneração ou pendência (P-01) |
| E5 Disponibilidade | C-04 | Capacidades disponíveis ou ADM-SC | Seção 7.4 |
| E6 Parâmetros, decisões e ambiguidades | C-04; C-03 (FN-INT-03 redige perguntas) | Partes determinadas e pendências com dependentes efetivos | AGUARDANDO_USUARIO agregado não impede E7–E12 das partes independentes (RQ-FLX-01) |
| E7 Planejamento | C-03 (FN-ORQ-01), C-05 (validação) | PlanoComposicao validado para entregáveis semânticos, com partes ainda não resolvidas identificadas e sem parâmetros inventados | Partes determinadas podem prosseguir durante AGUARDANDO_USUARIO; rejeição: até 2 regenerações, depois OPR-FAL (DA-26) |
| E8 Verificação pré-execução | C-04 | Lista de 12 itens; ContextoConsistencia | Falha: desfecho da seção 7.7 |
| E9 Autorização | C-04 | Autorizacao das etapas determinadas e aprovadas, com contexto e papéis | Obrigatória mesmo com solicitação em AGUARDANDO_USUARIO; não autorizar dependentes da pendência |
| E10 Execução | C-05, C-06 | Resultados por etapa | Reavaliação por etapa; falhas; suspensão |
| E11 Registro | C-07, C-13 | StatusResultado APRESENTAVEL | Rastreabilidade pendente: não apresentável |
| E12 Representação, síntese e continuidade | C-11, C-12, C-04 (validador), C-03 (FN-INT-04) | Saída validada ou apresentação estruturada autorizada; resultados, estados, limitações e pendências; sugestões quando aplicáveis | Modo degradado de RQ-DEG-04 pode atender entregável sem síntese; D8 segue CFG-DOC e TPL-12 |

### 6.3. Estados da solicitação

- **RQ-FLX-01** — StatusSolicitacao registra a situação agregada. Autorização, verificações de governança, contexto, dependências efetivas e StatusEtapa controlam cada parte. Enquanto existir pendência aberta, resolúvel e aplicável à continuidade de algum entregável vigente, a solicitação permanece AGUARDANDO_USUARIO; partes independentes podem percorrer E7–E12, incluindo planejamento, verificação, autorização, execução, reuso, registro e apresentação, sem passagem prévia do estado agregado por AUTORIZADA ou EM_EXECUCAO. Essa permanência não suspende partes independentes nem autoriza etapas bloqueadas, suspensas ou sem autorização válida. Somente as transições e permanências abaixo são permitidas. Antes de aplicar prioridades do estado agregado, atualizar o escopo e aplicar a retirada total D17-A de RQ-FLX-02. Antes da criação de entregáveis, StatusSolicitacao permanece EM_ADMISSAO, inclusive com pendência aberta; pendências habilitadoras da continuidade vinculam-se à solicitação, à entrada ou à base, sem exigir entregável vigente. Essa fila tem prioridade determinística: 1. autorização/privacidade obrigatória — CONFIRMACAO_DE_USO_DA_BASE, NATUREZA_DE_ENTIDADE_NOMINAL e SIGNIFICADO_DE_CAMPO de campo POTENCIALMENTE_IDENTIFICADOR; 2. estrutura ou materialização de entrada — ESTRUTURA_DE_ENTRADA; 3. ambiguidade material de interpretação — AMBIGUIDADE_MATERIAL; 4. demais esclarecimentos habilitadores. Dentro da mesma classe vale a ordem de criação; C-02 apresenta e C-08 processa as pendências nessa ordem. Indisponibilidade do LLM não é pendência do usuário, não compete nessa fila e mantém EM_ADMISSAO; E1 indisponível antes de interpretação válida permanece EM_ADMISSAO (RQ-DEG-02). A tabela de 6.3.1 materializa essas permanências e todas as transições adicionais. ENCERRADA_SEM_RESULTADO em escopo vazio não declara inexistência de resultados históricos. [T-DET][T-E2E: AT-91, AT-99, AT-100, AT-115, AT-176]

| De ou situação | Para ou permanência | Condição e alcance |
|---|---|---|
| RECEBIDA | EM_ADMISSAO | Início de E1; pendências anteriores à criação de entregáveis não alteram este estado |
| RECEBIDA ou EM_ADMISSAO, antes da criação de entregáveis | EM_ADMISSAO | Pendências pré-E4 abertas, na fila de prioridade acima, ou espera operacional de E1; sem transição para AGUARDANDO_USUARIO |
| Estado não terminal com entregável vigente | AGUARDANDO_USUARIO | Há pendência aberta, resolúvel e aplicável a entregável vigente; impedir somente os dependentes efetivos |
| AGUARDANDO_USUARIO | AGUARDANDO_USUARIO | Parte independente percorre E7–E12; resposta insuficiente não resolve a pendência; ou uma pendência é resolvida mas outra permanece aplicável |
| AGUARDANDO_USUARIO, após desaparecer a última pendência aplicável | EM_ADMISSAO | Há interpretação, planejamento, verificação ou autorização pertinente a realizar (E4–E9); retomada restrita, sem interromper ou reiniciar partes independentes |
| AGUARDANDO_USUARIO, após desaparecer a última pendência aplicável | EM_EXECUCAO | Sem E4–E9 pertinente restante, há execução, reuso, registro ou apresentação em andamento; preservar etapas e autorizações |
| AGUARDANDO_USUARIO, após desaparecer a última pendência aplicável | AUTORIZADA | Sem verificações restantes ou processamento em andamento, há etapas autorizadas prontas; seu início conduz a EM_EXECUCAO |
| AGUARDANDO_USUARIO, após desaparecer a última pendência aplicável | SUSPENSA | Continuidade depende exclusivamente de suspensão ou recuperação prevista; preservar condições próprias de restabelecimento e reautorização |
| EM_ADMISSAO | AUTORIZADA | E9 concluído, sem pendência resolúvel aplicável; percurso agregado normal, não requisito adicional para partes independentes durante a espera |
| AUTORIZADA | EM_EXECUCAO | Início de E10, sem pendência resolúvel aplicável |
| EM_EXECUCAO ou AUTORIZADA | SUSPENSA | Sem pendência resolúvel aplicável, a continuidade depende exclusivamente de suspensão da seção 9.5 ou de função indisponível necessária ao resultado; síntese dispensável de resultado já atendível segue RQ-DEG-04 |
| SUSPENSA | EM_ADMISSAO ou EM_EXECUCAO | Sem pendência resolúvel aplicável, recuperação exige primeiro E4–E9 quando pertinente; somente depois da verificação/reautorização aplicável retoma a execução (RQ-DEG-08) |
| Qualquer estado não terminal | CONCLUIDA, CONCLUIDA_PARCIAL ou ENCERRADA_SEM_RESULTADO | Nenhuma pendência resolúvel aplicável nem processamento pertinente restante, situação dos entregáveis determinada e apuração de RQ-FLX-02; inclui declínio ou perda de aplicabilidade, sem encerramento automático sem resultado |
| Qualquer estado não terminal | CANCELADA | Cancelamento explícito, conforme RQ-ORQ-16; entregáveis vigentes não terminais passam a CANCELADO |

Primeiro aplicar atualização do escopo, cancelamento explícito e retirada total de RQ-FLX-02. Para conjunto vigente não vazio, após desaparecer a última pendência, verificar nesta ordem determinística: necessidade de E4–E9; processamento em andamento; etapas autorizadas prontas; suspensão aplicável; encerramento. Cancelamento segue sua regra própria. Processamento pertinente abrange atividades ainda necessárias para cumprir ou encerrar justificadamente os entregáveis: interpretação, planejamento, verificações, autorização, execução, reuso, registro, apresentação e recuperação prevista; não se limita a cálculos já autorizados. Síntese dispensável após apresentação degradada válida (RQ-DEG-04) não constitui processamento restante. O ciclo independente PLANEJADA → AUTORIZADA → EM_EXECUCAO → CONCLUIDA, ou REUTILIZADA quando aprovado o reuso, pode ocorrer integralmente durante AGUARDANDO_USUARIO; sua conclusão não encerra a solicitação enquanto houver pendência ou processamento pertinente.

### 6.3.1. Transições e permanências complementares dos seis estados

As linhas abaixo integram RQ-FLX-01/02, RQ-DAD-42, RQ-ORQ-14 e RQ-FLX-17. Não acrescentam valores aos enums. Estados terminais da solicitação conservam histórico por versão de escopo. Descarte elimina objetos e não constitui novo estado de solicitação, entregável, etapa ou pendência.

| Objeto e origem | Destino/permanência | Precondição e efeito | Registro |
|---|---|---|---|
| Base `RECEBIDA` | `TRIADA` | Triagem determinística anterior ao LLM | EV-TRIAGEM; EV-ESTADO-BASE |
| Base `TRIADA` | `EXAMINADA` | Estrutura estabelecida; exame protegido permitido | EV-EXAME; EV-ESTADO-BASE |
| Base `TRIADA` ou `EXAMINADA` | `AGUARDANDO_CONFIRMACAO` | Pendência habilitadora condiciona a entrada inteira | EV-PENDENCIA; EV-ESTADO-BASE |
| Base `AGUARDANDO_CONFIRMACAO` | Permanece | Resposta insuficiente ou outra condição habilitadora ainda pendente | EV-RESPOSTA; EV-VERIFICACAO |
| Base com habilitação satisfeita | `DISPONIVEL` | Exame necessário concluído e uso autorizado | EV-CONFIRMACAO-USO; EV-EXAME; EV-ESTADO-BASE |
| Base em preparação | `BLOQUEADA` | Uma das três causas fechadas de bloqueio; negativa também exclui derivados ativos | EV-ESTADO-BASE; EV-PRIVACIDADE |
| Base `BLOQUEADA` por negativa | `AGUARDANDO_CONFIRMACAO` | Reversão explícita, inequívoca, na mesma sessão ativa, com original protegido ainda guardado em C-10; negativa anterior permanece histórica; autorização e derivados anteriores não são reativados | EV-MENSAGEM; EV-CONFIRMACAO-USO; EV-ESTADO-BASE |
| Base em reconfirmação | Permanece `AGUARDANDO_CONFIRMACAO` | Confirmação positiva registrada enquanto triagem e exame necessários são refeitos | EV-CONFIRMACAO-USO; EV-TRIAGEM; EV-EXAME |
| Base em reconfirmação | `DISPONIVEL` | Nova confirmação positiva, triagem e exame refeitos e demais condições satisfeitas | EV-CONFIRMACAO-USO; EV-ESTADO-BASE |
| Base `BLOQUEADA` por negativa, com original protegido já descartado | Permanece | Reversão não restaura a base; é necessária nova entrada | EV-INGESTAO da nova entrada |
| Base `BLOQUEADA` por impossibilidade técnica/integridade | Permanece | Novo arquivo constitui outra entrada; não é reversão D15 | EV-INGESTAO da nova entrada |
| Qualquer estado de Base | `DESCARTADA` | Encerramento da sessão; depois eliminar conteúdo e mapeamentos | EV-ESTADO-BASE; EV-SESSAO antes do descarte |
| Solicitação `EM_ADMISSAO` em E1 | Permanece | LLM indisponível antes de interpretação válida; a indisponibilidade não integra a fila de pendências | EV-INDISPONIBILIDADE; `OPR-IND` |
| Solicitação antes da criação de entregáveis | Permanece `EM_ADMISSAO` | Pendências pré-E4 abertas, apresentadas e processadas na fila de prioridade de RQ-FLX-01 | EV-PENDENCIA |
| Mesma solicitação em E1 | Permanece e retoma E1 | LLM retorna e sessão continua ativa; validar elegibilidade do contexto | EV-DISPONIBILIDADE; EV-LEITURA-MINIMA |
| Solicitação não terminal | `AGUARDANDO_USUARIO` | Existe pendência resolúvel aplicável a entregável vigente, inclusive habilitação de entrada substituta | EV-PENDENCIA |
| Solicitação `AGUARDANDO_USUARIO` | Permanece | Processamento independente ou resposta que não elimina todas as pendências aplicáveis | EV-EXECUCAO das partes e EV-RESPOSTA; EV-VERIFICACAO da pendência |
| Solicitação sem última pendência aplicável | Estado previsto em RQ-FLX-01 | Retomar apenas admissão/verificação, execução, autorização ou recuperação ainda necessária | EV-VERIFICACAO; EV-AUTORIZACAO |
| Solicitação com retirada parcial e conjunto vigente não vazio | Estado recalculado | Criar versão do conjunto vigente; preservar processamento independente e histórico | EV-ALTERACAO-ESTADO |
| Solicitação com todos os entregáveis vigentes retirados, sem cancelamento explícito | `ENCERRADA_SEM_RESULTADO` | D17-A: conjunto vigente vazio; desvincular obrigações retiradas e cancelar apenas trabalho sem consumidores | EV-ALTERACAO-ESTADO, versão do escopo e registro de estado; sem EV-CANCELAMENTO da solicitação |
| Solicitação já terminal, não explicitamente cancelada, com retirada posterior | Terminalidade recalculada na nova versão de escopo | Não reabrir execução; preservar estado anterior no histórico; se conjunto ficar vazio, aplicar D17-A | EV-ALTERACAO-ESTADO |
| Solicitação pronta para terminar, com conjunto vigente não vazio | `CONCLUIDA`, `CONCLUIDA_PARCIAL` ou `ENCERRADA_SEM_RESULTADO` | Aplicar RQ-FLX-02 ao conjunto vigente, sem pendências/processamento pertinentes | EV-VERIFICACAO, com estado agregado apurado |
| Solicitação não terminal | `CANCELADA` | Cancelamento explícito da solicitação; retirada parcial ou total não satisfaz essa condição; nenhuma nova execução é iniciada | EV-CANCELAMENTO |
| Solicitação `CANCELADA` | Permanece | Estado terminal e monotônico; retorno tardio não a reabre | EV-RETORNO_TARDIO_DESCARTADO, quando houver retorno |
| Entregável `PENDENTE` | `ATENDIDO` | Resultado admissível satisfaz seu objetivo semântico | EV-RESULTADO |
| Entregável `PENDENTE` | `NAO_EXECUTAVEL` ou `INTERROMPIDO` | Impedimento definitivo segundo RQ-RES-04; negativa não permanece como pendência fictícia | EV-VERIFICACAO, com referência ao evento da causa |
| Entregável retirado | Estado histórico preservado | Sair do conjunto vigente; ocorrência `RETIRADA_PELO_USUARIO`; não converter em falha ou interrupção | EV-ALTERACAO-ESTADO |
| Entregável vigente não terminal | `CANCELADO` | Cancelamento explícito da solicitação; terminal, monotônico e distinto de retirada | EV-CANCELAMENTO |
| Entregável já concluído no cancelamento | Estado e resultado históricos preservados | ATENDIDO, NAO_EXECUTAVEL ou INTERROMPIDO não é convertido em CANCELADO | EV-CANCELAMENTO |
| Entregável `CANCELADO` com retorno tardio de unidade, etapa ou chamada | Permanece `CANCELADO` | Retorno não reabre, não altera o estado, não entra no conjunto vigente, não é reincorporado ao contexto ativo nem reenviado ao LLM | EV-RETORNO_TARDIO_DESCARTADO |
| Entregável terminal após reversão de autorização | Permanece terminal | Nova autorização não o reativa; retomada/reexecução segue manifestação e fluxo normais | EV-VERIFICACAO; eventual nova execução requer EV-AUTORIZACAO próprio |
| Etapa/unidade `PLANEJADA` | `AUTORIZADA` | Verificações e autorização registradas para o escopo e os consumidores vigentes | EV-VERIFICACAO; EV-AUTORIZACAO |
| Etapa/unidade autorizada | `EM_EXECUCAO` | Gates válidos e dependências efetivas autorizadas | EV-AUTORIZACAO; EV-EXECUCAO |
| Unidade em execução | `CONCLUIDA` ou `REUTILIZADA` | Saída válida ou reuso autorizado | EV-EXECUCAO; EV-REUSO |
| Etapa `EM_EXECUCAO` com unidades em estados distintos | `CONCLUIDA`, `FALHOU`, `BLOQUEADA` ou `SUSPENSA` | Saída parcial admissível pelo contrato → CONCLUIDA, preservando cobertura/causas; falha operacional que impeça toda saída → FALHOU; impedimento não operacional → BLOQUEADA; recuperação obrigatória → SUSPENSA. Não relaxar CAP-ROT-01 nem sobrescrever estados das unidades | EV-EXECUCAO; EV-FALHA; EV-VERIFICACAO; EV-SUSPENSAO, conforme a causa |
| Unidade com falha recuperável | Nova tentativa em `EM_EXECUCAO` | Idempotência e orçamento de uma repetição ainda disponível | EV-FALHA; EV-EXECUCAO |
| Unidade com tentativa esgotada | `FALHOU` | `OPR-FAL`; afetar somente dependentes efetivos; ResultadoElemento INTERROMPIDO quando a execução do próprio elemento começou e falhou | EV-FALHA |
| Dependente sem condição operacional/metodológica | `BLOQUEADA` ou `SUSPENSA`, conforme contrato | Preservar causa original; não contaminar independentes; ResultadoElemento NAO_EXECUTAVEL com DEPENDENCIA_NAO_AVALIAVEL e causa-raiz quando a dependência efetiva falhou definitivamente | EV-VERIFICACAO; EV-SUSPENSAO |
| Etapa não concluída sem consumidor vigente | `CANCELADA` | Retirada de escopo elimina sua necessidade; não cancelar suporte compartilhado nem atribuir `CANCELADA` à solicitação por esse motivo | EV-ALTERACAO-ESTADO e EV-REPLANEJAMENTO |
| Pendência `ABERTA` | `RESPONDIDA` | Resposta válida resolve sua condição no escopo próprio | EV-RESPOSTA; EV-VERIFICACAO |
| Pendência `ABERTA` | Permanece | Resposta ambígua, inválida ou insuficiente | EV-RESPOSTA; EV-VERIFICACAO |
| Pendência `ABERTA` | `SEM_APLICABILIDADE` | Seu único consumidor saiu do escopo ou condição deixou de existir | EV-VERIFICACAO, com motivo e estado da pendência |
| Pendência compartilhada após retirada de um consumidor | Permanece para os consumidores restantes | Remover o vínculo da solicitação/entregável retirado; não impedir sua terminalidade por obrigação de outro consumidor | EV-ALTERACAO-ESTADO e EV-VERIFICACAO dos vínculos |
| Pendência `ABERTA` | `ENCERRADA` | Declínio/cancelamento definitivo previsto no fluxo | EV-VERIFICACAO, com motivo e estado da pendência |
| Sessão `ATIVA` | Permanece | EV-INTERACAO_USUARIO do catálogo fechado de CFG-OPR antes da expiração; atualizar última interação | EV-INTERACAO_USUARIO; EV-SESSAO registra o marco |
| Sessão `ATIVA` | Permanece | Fechamento, desconexão, segundo plano, heartbeat, polling, refresh interno, renderização ou reconexão automática, antes do limite | EV-SESSAO registra permanência, sem renovar o marco |
| Sessão `ATIVA` | `ENCERRADA` | Controle explícito ou tempo sem interação ≥ 1.800 segundos | EV-SESSAO; descarte imediato |
| Sessão `ENCERRADA` | Sem retorno a `ATIVA` | Novo acesso cria outra sessão; respostas tardias são descartadas | Novo EV-SESSAO |

- **RQ-FLX-02** — A terminalidade DEVE ser apurada na versão corrente de EscopoSolicitacao. Primeiro atualizar conjunto vigente, vínculos e consumidores. Cancelamento explícito da solicitação conserva CANCELADA: entregáveis vigentes não terminais passam a CANCELADO, entregáveis já concluídos preservam estado e resultado históricos, nenhuma nova execução é iniciada e resultado tardio não reabre solicitação nem entregável (RQ-ORQ-16). D17-A, decisão humana aprovada: retirada voluntária de TODOS os entregáveis vigentes, sem cancelamento explícito, deixa o conjunto vazio e produz ENCERRADA_SEM_RESULTADO; nunca CONCLUIDA por verdade vacuamente universal nem CONCLUIDA_PARCIAL. Resultados anteriores permanecem históricos/rastreáveis durante a sessão; a retirada não atribui NAO_EXECUTAVEL ou INTERROMPIDO aos retirados. Pendências exclusivas tornam-se SEM_APLICABILIDADE; retirar vínculos de pendências compartilhadas sem encerrá-las para outros consumidores. Cancelar somente etapas não concluídas sem consumidor vigente; suporte compartilhado continua. Para conjunto não vazio, após ausência de pendência resolúvel aplicável e processamento pertinente, e determinação da situação dos entregáveis vigentes: todos ATENDIDO → CONCLUIDA; pelo menos um ATENDIDO e outro definitivamente NAO_EXECUTAVEL/INTERROMPIDO → CONCLUIDA_PARCIAL; nenhum ATENDIDO → ENCERRADA_SEM_RESULTADO. PENDENTE não é convertido artificialmente. Retirada parcial não cria falha nem implica conclusão parcial. Solicitação já terminal e não explicitamente cancelada pode ter nova versão de escopo e terminalidade recalculada, sem reabrir execução e preservando a apuração anterior; conjunto vazio aplica D17-A. Registrar EV-ALTERACAO-ESTADO e replanejamento pertinente; retirada não gera EV-CANCELAMENTO da solicitação. Decomposição técnica não altera entregáveis nem terminalidade. [T-DET][T-E2E: AT-91, AT-99, AT-113–AT-115, AT-129, AT-163, AT-171]
- **RQ-FLX-03** — Execução ANALITICA exige E9 (INV-01). CAP-EXA-01 automático usa exclusivamente a autorização HABILITADORA de RQ-DAD-34, anterior e independente de E9. Leitura mínima e habilitação de dados não autorizam análise substantiva [C §5.2, §6.4] (P-01, AV-08). [T-GOV]
- **RQ-FLX-04** — A resposta é associada à pendência existente e validada no escopo herdado (RQ-LIN-19); seu recebimento não equivale à resolução. Resposta por opção segue RQ-FLX-15. Retomada de E4 e verificações subsequentes limita-se ao conteúdo afetado, ao ramo pertinente e a seus descendentes efetivos; outras pendências mantêm AGUARDANDO_USUARIO. Preservam-se elementos validados, resultados independentes válidos e etapas concluídas, reutilizadas ou em andamento. As etapas liberadas exigem verificações e autorização aplicáveis; não são automaticamente autorizadas pela resposta. Completar informação pendente não exige segunda decisão de continuidade pelo mesmo motivo. Se a resposta também alterar contexto já utilizado, aplicam-se RQ-DAD-08, RQ-ORQ-10/11 e Parte 11 somente aos dependentes afetados. Entregável ATENDIDO não é reexecutado sem causa normativa; reuso segue RQ-ORQ-06/07. Pertinência só é reavaliada diante de intenção materialmente distinta [C §5.9, §6.4]. [T-GOV][T-E2E: AT-83, AT-91, AT-99]

### 6.4. Contexto de interpretação

- **RQ-FLX-05** — C-08 DEVE montar o contexto enviado a C-03 com: idioma da sessão; linha ativa e objetivo local; elementos do estado com valor, origem, escopo, validade e vigência; pendências abertas; eventos recentes da linha; catálogo de capacidades com status e disponibilidade; vocabulários; estrutura sanitizada da base, trechos conversacionais liberados pela triagem e matriz de aplicabilidade (RQ-DAD-23). Elementos INVALIDADO aparecem marcados, apenas para resolução de referências. Identificadores e registros individualizados são excluídos [C §7.5] (DA-27). Elegibilidade de contexto/reuso exige base ainda autorizada e sessão ativa; excluir todos os derivados de entrada recusada, inclusive histórico reconstruído (RQ-DAD-42), e descartar retornos após encerramento (RQ-FLX-17). [T-GOV]
- **RQ-FLX-06** — Âncora para elemento INVALIDADO é rejeitada. Resultado cujo vínculo é NAO_VIGENTE por DESLOCAMENTO_DE_FOCO conserva caráter contemporâneo e pode ser usado como componente, entrada de comparação ou resultado de outro recorte quando identificado explícita ou inequivocamente por referência contextual (ex.: "compare os dois"), sem pedido de uso histórico. Vínculo NAO_VIGENTE por SUBSTITUICAO_DE_ESTADO tem caráter histórico e exige pedido de uso histórico identificável, satisfeito também por referência contextual inequívoca para a comparação de RQ-ORQ-13. Em nenhum caso se reativam parâmetros fora de escopo nem se exige confirmação adicional [C §5.7, §7.5] (F-03). [T-GOV][T-E2E: AT-31, AT-67, AT-77]

### 6.5. Rotas por tipo de pedido

- **RQ-FLX-07** — SOBRE_O_AGENTE: FN-META-01 responde somente com base em CFG e registros de C-13 (capacidades, regras, status, procedência); toda proposição metodológica ou operacional exibida referencia âncora DOC: de CFG-DOC (V-16). Nenhum fato de domínio é produzido [C §5.2] (F-12). [T-GOV][T-E2E: AT-38, AT-86]
- **RQ-FLX-08** — CONCEITUAL_DOMINIO: somente proposições com âncora DOC: de CFG-DOC, que cataloga o conteúdo normativo de CFG-IND, CFG-MET e das demais partes desta SPEC (seção 4.4.23); na falta, informa-se a limitação. Perguntas normativas dependem de critério autorizado: CFG-NOR ou critério do usuário aplicável ao escopo. Sem ambos, informa-se a ausência, sem fornecer valores, PODENDO explicar que o usuário pode definir critério para sua análise, sem sugerir valor (RQ-GOV-31). Critério local nunca é apresentado como norma geral [C §5.2] (DA-21). [T-GOV][T-E2E: AT-39, AT-71]
- **RQ-FLX-09** — CONTROLE: cancelar, trocar, retomar ou encerrar linha são tratados deterministicamente por C-05 e C-08, pela conversação ou por controle estruturado. Aceitar sugestão e pedir recálculo são manifestações na conversação e geram nova solicitação ANALITICO ancorada na manifestação; a solicitação que implique claramente recálculo segue RQ-LIN-15 (DA-08, P-18). Retirada parcial ou total de entregáveis é controle de escopo versionado segundo RQ-FLX-02, distinto de cancelamento explícito. C-01 disponibiliza o controle estruturado Encerrar sessão; C-02/C-08 o executam imediatamente sem depender de FN, com descarte de RQ-FLX-17. [T-DET]
- **RQ-FLX-10** — RESPOSTA: dada por texto ou por seleção de opção apresentada, é associada à pendência indicada pela interface, analítica ou habilitadora (RQ-DAD-42). Sem indicação, FN-INT-02 propõe a associação; se houver mais de uma pendência compatível ou se a mensagem puder ser nova solicitação com diferença material, cria-se pendência AMBIGUIDADE_MATERIAL listando as pendências candidatas e a opção "nova solicitação". [T-GOV]
- **RQ-FLX-11** — Solicitação mista: funções coexistentes seguem RQ-FLX-21. Cada parte de pedido recebe pertinência e admissibilidade próprias; partes analíticas pertinentes e admissíveis prosseguem se separáveis (seção 7.8). Pedido não admitido é entregável NAO_EXECUTAVEL com desfecho; saudação, dados, resposta a pendência ou controle não são por isso entregáveis analíticos recusados [C §5.2]. [T-GOV][T-E2E: AT-32, AT-64]

### 6.6. Interrupções

- **RQ-FLX-12** — Nova mensagem enquanto há pendências abertas não as encerra. Se a nova solicitação alterar o estado de modo incompatível com a solicitação pendente, as pendências passam a SEM_APLICABILIDADE (Parte 11) [C §7.8, §9.10]. [T-DET]
- **RQ-FLX-13** — Toda solicitação com parte ANALITICO, após a criação legítima de sua linha no fluxo, pertence a exatamente uma linha; antes dessa criação, pendência analítica exige solicitacao_id e admite linha_id ausente, sem linha fictícia (H1). Partes NAO_PERTINENTE, SOBRE_O_AGENTE, CONCEITUAL_DOMINIO, CONVERSACIONAL ou apenas DADOS não criam linha analítica; dados, respostas e controles podem atualizar bases ou estado pelas regras próprias, sem autorizar análise substantiva. [T-DET]

### 6.7. Interface, controles estruturados e captura de seleção

- **RQ-FLX-14** — Nova solicitação analítica é formulada exclusivamente pela conversação com o LLM. Tabelas, gráficos, mapas, painéis e demais elementos da interface não constituem canal para solicitar ou disparar análises (P-18). [T-GOV][T-E2E: AT-13]
- **RQ-FLX-15** — São permitidos controles estruturados para upload, navegação, filtros, seleção, alteração da visualização, confirmação de privacidade, exportação e resposta a opções de pendências já estruturadas; nenhum deles inicia, por si mesmo, análise substantiva. A resposta por opção atualiza deterministicamente a interpretação (origem ATUALIZACAO_POR_RESPOSTA_ESTRUTURADA), e o fluxo prossegue sem nova interpretação quando nenhuma função do LLM for necessária [C §9.11] (P-18). [T-GOV]
- **RQ-FLX-16** — C-01 DEVE capturar deterministicamente a seleção ativa da interface no envio de toda mensagem, como snapshot imutável com instante, valores, escopo, origem MANIFESTACAO_USUARIO/SELECAO_DE_INTERFACE e EV-CAPTURA-SELECAO, independentemente de referência textual explícita. Pedido que exige universo, sem universo textual materialmente diferente, usa a seleção ativa aplicável; o universo resultante é LISTA e deve ser explicitado. Texto e seleção equivalentes não geram confirmação redundante; divergência material gera pendência, sem substituição silenciosa. Mudança posterior da interface não altera a captura da mensagem. Seleção determina universo, nunca acrescenta operação analítica nem inicia análise por si só. [T-GOV][T-E2E: AT-20, AT-140, AT-141]

- **RQ-FLX-21** — O encaminhamento opera por partes e funções não exclusivas, preservando todas as funções identificadas na mensagem. Dados seguem a seção 5.8; saudações e agradecimentos sem dados recebem resposta conversacional breve, sem ingestão ou exame; pedidos sobre capacidades seguem RQ-FLX-07. Na mensagem com dados e pedido analítico, o pedido é preservado durante habilitação e confirmações necessárias, retomando E2–E9 com o perfil disponível, sem pedir que o usuário o repita; a estrutura e a materialização dos dados são verificadas antes de ambiguidade material de interpretação (RQ-DAD-31). Resposta a pendência e controle são associados aos respectivos alvos; conflito material entre funções gera esclarecimento, não descarte silencioso de parte da mensagem. Estados de RQ-FLX-01 regem solicitações analíticas; ingestão isolada usa StatusBase e sua autorização habilitadora, sem fabricar plano ou entregável analítico. Em XLSX, escolha de várias planilhas preserva o pedido e segue a distinção entre entradas independentes e combinação em RQ-DAD-43; não infere temporalidade pelo nome das abas. [T-GOV][T-E2E: AT-64, AT-65, AT-70, AT-174]
- **RQ-FLX-22** — Se solicitação analítica depender de entrada/base em AGUARDANDO_CONFIRMACAO, apresentar a pendência habilitadora concreta existente — decisão necessária, elementos afetados e opções autorizadas (TPL-04; TPL-10 para confirmação de uso) —, registrar a solicitação em solicitacoes_dependentes e manter AGUARDANDO_USUARIO quando houver entregável vigente afetado; antes da criação de entregáveis, a solicitação permanece EM_ADMISSAO com a pendência na fila de RQ-FLX-01; sem duplicata nem bloqueio genérico como única resposta. Partes independentes percorrem E7–E12 com autorização própria durante a espera (RQ-FLX-01, RQ-GOV-27/29). Resposta validada retoma somente o ramo e descendentes efetivamente dependentes, com verificações pertinentes de E2–E9 e RQ-FLX-04, sem repetição do pedido ou recálculo das partes concluídas; demais pendências conservam a espera agregada. Entradas independentes de XLSX seguem RQ-DAD-43 e não são bloqueadas por dúvida exclusiva de combinação. Recusa ou perda de aplicabilidade exige apuração contextual de RQ-FLX-02 (F-08). H3: entrada BLOQUEADA por materialização impossível pode ter pendência habilitadora para entrada substituta explicitamente associada; não confundir com desbloqueio da entrada antiga. Conservar pedido e aguardar nova habilitação. Retirada elimina apenas seus vínculos de consumo; pendência sem consumidor passa a SEM_APLICABILIDADE, e D17-A encerra escopo vazio. [T-GOV][T-E2E: AT-83, AT-91, AT-99, AT-110, AT-111]

---

## Parte 7 — Governança: gates, âncoras, autoridade, ambiguidade e autorização

### 7.1. Validação de âncoras

| Tipo de fonte | Condição de validade |
|---|---|
| DADO_AUTORIZADO | Base DISPONIVEL na sessão (RQ-DAD-42: entrada deliberada, triagem e exame concluídos e nenhuma pendência habilitadora aberta, inclusive confirmação de uso), versão presente no contexto, campo e chave existentes, valor igual ao armazenado |
| METADADO_AUTORIZADO | Item aceito no ato de autorização da base, versão presente no contexto |
| CONFIGURACAO_GOVERNADA | Item e versão presentes no snapshot aplicável |
| MANIFESTACAO_USUARIO | Evento existente na sessão; valor presente literalmente na manifestação (após normalização de CFG-VOC) ou na seleção capturada; entidades e relações de dados conversacionais verificadas conforme RQ-DAD-31; subtipo coerente; escopo registrado; regra RQ-GOV-03 atendida. ESCOLHA_DE_OPCAO_AUTORIZADA só vale para opção de conjunto autorizado apresentado em pergunta registrada |
| RESULTADO_ESTRUTURADO | Resultado VALIDO e APRESENTAVEL; caminho interno existente; para reuso na linha corrente, vínculo VIGENTE; resultado deslocado como componente ou entrada de comparação (RQ-LIN-20); resultado de caráter histórico com uso explicitamente autorizado |
| INFORMACAO_OPERACIONAL_SISTEMA | Chave admitida em CFG-OPR (data e hora corrente, com fuso ou offset quando disponível; identificador de sessão; estado estruturado de interface); vedada para fatos de domínio, parâmetros metodológicos e critérios [C §5.8] |

- **RQ-GOV-01** — C-04 DEVE validar toda âncora de todo registro de LLM antes do uso. Âncora inválida faz o elemento ser rejeitado: a interpretação é regenerada com a indicação do erro, até 2 regenerações (DA-26), ou o elemento passa a item não resolvido (pendência). Elemento com âncora inválida nunca é usado. [T-GOV][T-E2E: AT-27]
- **RQ-GOV-02** — Elemento recuperado do estado DEVE preservar a âncora original, acrescida de `recuperada_de` [C §5.10]. [T-DET]
- **RQ-GOV-03** — Regra preventiva: o conhecimento latente do LLM não é fonte factual; o LLM NÃO DEVE propor fato ausente para que o usuário apenas o confirme; faltando informação factual necessária, o agente pede que o usuário forneça o valor ou o significado. C-04 DEVE manter o RCNA com todo conteúdo factual que, por falha, tenha chegado ao usuário a partir de saída do LLM sem âncora válida. Confirmação, seleção ou referência a conteúdo do RCNA não o torna fonte autorizada, e a âncora é rejeitada; só é aceita afirmação própria em que o usuário forneça o valor literalmente, com o registro explicitado a ele como informação fornecida por ele [C §8.6] (P-05). [T-GOV][T-E2E: AT-16]

### 7.2. Gate de pertinência

- **RQ-GOV-04** — C-04 DEVE decidir a pertinência de cada parte a partir da LeituraMinima, pela relação da solicitação com a FTS e com a finalidade analítica, segundo a tabela. O julgamento semântico do LLM é proposta; categorias, territórios e demais elementos factuais não são inferidos de conhecimento latente; o reconhecimento automático de categorias é determinístico (seção 4.3); e a simples solicitação de uma categoria não é declaração de pertença [C §3.1, §5.2] (DA-04, P-06). [T-GOV][T-LLM: M-01]

| Condição | Pertinência |
|---|---|
| Objeto é força de trabalho de outro setor, sem declaração explícita do usuário de que integra a FTS no contexto da análise | NAO_PERTINENTE (Caso 24) |
| Tema claramente alheio à FTS e ao funcionamento do agente | NAO_PERTINENTE (Caso 5) |
| Parte com função SOBRE_O_AGENTE | PERTINENTE (rota FN-META-01) |
| Objeto é a FTS em geral ou indicador definido da FTS | PERTINENTE; a composição das categorias segue RQ-DAD-19 |
| Objeto é categoria com pertença estabelecida por fonte ou metadado autorizado, declaração de domínio da base, reconhecimento FTS_INEQUIVOCA, reconhecimento FTS_CONTEXTUAL com contexto autorizado suficiente ou declaração explícita do usuário (RQ-DAD-19) | PERTINENTE, sem pergunta sobre pertença |
| Objeto é expressão FTS_AMBIGUA (ex.: "técnicos") não resolvida por metadado, declaração de domínio ou contexto autorizado | PERTINENCIA_INCERTA, com pergunta sobre qual categoria está sendo analisada |
| Objeto é categoria FTS_CONTEXTUAL (ex.: "assistentes sociais") sem fonte, metadado, declaração de domínio, contexto autorizado suficiente ou declaração explícita | PERTINENCIA_INCERTA, com pedido de esclarecimento; nunca NAO_PERTINENTE por esse motivo (CFG-DOM) |
| Objeto é categoria NAO_RECONHECIDA sem fonte, metadado, declaração de domínio ou declaração explícita, ainda que solicitada pelo usuário (ex.: "analise a distribuição dos eletricistas") | PERTINENCIA_INCERTA, com pedido de esclarecimento; NAO_RECONHECIDA não equivale a NAO_PERTINENTE |
| Referência contextual resolvida para linha ativa pertinente | PERTINENTE |
| Objeto exclusivamente auxiliar (população, território, geografia) | PERTINENTE se vinculado a etapa ou resultado de linha ativa; caso contrário, PERTINENCIA_INCERTA |
| Setor indeterminado ou referência contextual não resolvida | PERTINENCIA_INCERTA |

- **RQ-GOV-05** — PERTINENCIA_INCERTA DEVE gerar pendência PERTINENCIA, com pergunta neutra, sem execução. [T-GOV]
- **RQ-GOV-06** — NAO_PERTINENTE DEVE gerar desfecho ADM-NP com mensagem breve de que o tema não pertence à finalidade ou ao domínio, PODENDO indicar os tipos de análise de CFG-FAM. Nenhum conhecimento geral é fornecido [C §5.2, Caso 5]. [T-GOV][T-E2E: AT-05]
- **RQ-GOV-07** — A semelhança estrutural com capacidade existente NÃO DEVE alterar a decisão (RQ-ESC-06). [T-GOV][T-E2E: AT-24]

### 7.3. Gate de admissibilidade

- **RQ-GOV-08** — Para cada parte pertinente: exclusão validada em `indicios_exclusao` gera o desfecho da tabela 1.4; ausência de família candidata gera ADM-FE por não enquadramento (ex.: projeção, Caso 4); havendo família sem exclusão, a parte é admissível [C §3.1, §5.2]. Somente disposição ATIVO validada em estrutura aciona a exclusão; DESCARTADO_POR_CONTEXTO permite prosseguir e INDETERMINADO gera pendência conforme RQ-GOV-09. Com várias exclusões ativas, a parte registra todas, com seus desfechos, e o desfecho operacional deriva da consequência prevalecente de RQ-GOV-09; nenhuma é suprimida pela numeração. Preservar verificação de família independente de sinais lexicais. [T-GOV][T-LLM: M-02][T-E2E: AT-173]
- **RQ-GOV-09** — Cada ocorrência de sinal determinístico CFG-EXC DEVE constar em LeituraMinima com sinal, EXC, âncora, DisposicaoSinalExclusao, justificativa contextual estruturada e resultado da rechecagem. ATIVO aplica a exclusão correspondente; DESCARTADO_POR_CONTEXTO permite prosseguir; INDETERMINADO exige pendência AMBIGUIDADE_MATERIAL pertinente. C-04 verifica cobertura de todas as ocorrências, valores da enumeração, âncoras, presença e consistência estrutural da justificativa; não realiza julgamento semântico geral da verdade da justificativa. Ocorrência omitida ou estruturalmente inválida provoca a reexecução já prevista de FN-INT-01 com indicação explícita; persistindo divergência, abrir pendência, sem sinais ignorados. Não ampliar limites de rechecagem/regeneração. Termo isolado não gera recusa automática; ausência de família candidata continua ADM-FE independentemente de sinal. Várias exclusões podem estar simultaneamente ativas; todas permanecem registradas com justificativa e ConsequenciaExclusao. O desfecho operacional deriva da consequência normativa, não do número da EXC; entre consequências incompatíveis prevalece BLOQUEAR_NAO_EXECUTAR > AGUARDAR_ESCLARECIMENTO_OU_CONFIRMACAO > PROSSEGUIR_COM_LIMITACAO > DESCARTADO_POR_CONTEXTO, sem precedência arbitrária entre EXC-08 e EXC-03 (seção 4.4.3). [T-GOV][T-E2E: AT-87, AT-126–AT-128, AT-173]
- **RQ-GOV-10** — A admissibilidade DEVE ser reavaliada após E4 quando a interpretação operacional indicar família ou exclusão diferente da de E3 (P-01). [T-GOV]
- **RQ-GOV-11** — Mensagem de ADM-FE DEVE informar que a solicitação se relaciona ao domínio, mas não integra o escopo atual, sem produzir o conteúdo excluído; PODE apresentar análises admitidas como alternativas explicitamente distintas [C §9.7, Casos 4 e 6]. [T-GOV][T-E2E: AT-04, AT-06]

### 7.4. Gate de disponibilidade

- **RQ-GOV-12** — Capacidade candidata com status diferente de ATIVA em CFG-CAP gera ADM-SC com motivo igual ao status. Capacidade ATIVA temporariamente indisponível segundo a disponibilidade operacional conhecida antes da execução gera ADM-SC com motivo TEMPORARIAMENTE_INDISPONIVEL; indisponibilidade ou falha detectada durante a execução é problema operacional (OPR-IND ou OPR-FAL). Capacidade ATIVA cuja variante ou método pedido não esteja incorporado (ex.: posição percentual em CAP-DIS-01) gera ADM-SC com motivo METODO_NAO_INCORPORADO. A comunicação é simples e não confunde indisponibilidade com ausência de dados, insuficiência metodológica ou inexistência de capacidade; o LLM NÃO DEVE reproduzir informalmente o comportamento ausente [C §5.6, §11.9] (P-03). [T-GOV][T-E2E: AT-35]

### 7.5. Autoridade e ambiguidade material

- **RQ-GOV-13** — Cada elemento da interpretação DEVE receber ClasseAutoridade segundo o contrato da capacidade. Na ausência de classificação contratual aplica-se a tabela [C §5.5]. [T-GOV]

| Elemento | Classe padrão |
|---|---|
| Capacidade para intenção já estabelecida; ordem das etapas; reuso válido e vigente; forma de apresentação dentro de CFG-REP | OPERACIONAL_AUTORIZADA |
| Indicador, categoria, universo, período, modo territorial | PARAMETRIZAVEL_PELO_USUARIO quando houver escolha substantiva aberta; resolução por fonte autorizada ou estado segue RQ-GOV-14 |
| Limiar, parâmetro de referência, critério, intervalo de frequência, N de seleção | PARAMETRIZAVEL_PELO_USUARIO |
| Critério normativo da análise; valor factual; premissa de ausência de sobreposição; substituição de valor da base; escala de apresentação; composição de agrupamento | PARAMETRIZAVEL_PELO_USUARIO, com origem e escopo registrados (DA-03, DA-07, DA-09, DA-16, DA-21) |
| Alternativa metodológica autorizada | PARAMETRIZAVEL_PELO_USUARIO somente quando o contrato permitir explicitamente; nesta versão os contratos não oferecem métodos alternativos (DA-06) |
| Método, fórmula, algoritmo ou expressão não prevista | PROIBIDA: ADM-SC METODO_NAO_INCORPORADO |
| Elemento não previsto no contrato | PARAMETRIZAVEL_PELO_USUARIO (na dúvida não se presume autoridade autônoma) |

- **RQ-GOV-14** — PARAMETRIZAVEL_PELO_USUARIO significa que uma escolha substantiva ainda aberta cabe ao usuário, não que todo valor precise vir de manifestação dele. Antes de criar pendência, C-04 DEVE determinar, por fontes autorizadas, metadados, configuração e estado válido, vigente e aplicável ao escopo, os candidatos admissíveis e as restrições da solicitação, registrando a resolução em InterpretacaoOperacional.resolucoes_parametros. Se houver um único valor aplicável com âncora válida, o parâmetro está resolvido e prossegue sem pergunta, preservando a origem real, inclusive DADO_AUTORIZADO ou METADADO_AUTORIZADO. Não se reclassifica origem como MANIFESTACAO_USUARIO. C-04 verifica unicidade e aplicabilidade independentemente da seleção proposta pelo LLM; um candidato omitido pelo LLM não prova unicidade. Sem valor necessário: PARAMETRO_FALTANTE (BLQ-INF); com escolhas materiais não resolvidas: DECISAO_SUBSTANTIVA (BLQ-DEC) ou AMBIGUIDADE_MATERIAL. Um único período/categoria só resolve o recorte se for compatível com o pedido, sem substituir período explicitamente solicitado nem ignorar AMB-04. Parâmetro ou dimensão ainda válido e aplicável ao escopo — inclusive dimensão da linha (RQ-LIN-19) e valor factual complementar (RQ-LIN-21) — não é perguntado novamente sem razão material [C §3.6, Caso 7] (AV-04, F-07). [T-GOV][T-E2E: AT-07, AT-66, AT-82]
- **RQ-GOV-15** — Delegação genérica ("você escolhe", "use o que achar melhor") não resolve escolha substantiva aberta. Depois da verificação de RQ-GOV-14, pendência necessária permanece, com opções somente autorizadas; se os parâmetros já estiverem inequivocamente determinados, o agente prossegue sem criar pergunta artificial [C §3.6]. [T-GOV][T-E2E: AT-25, AT-66]
- **RQ-GOV-16** — A assinatura material é o resumo canônico dos elementos cuja variação pode alterar de forma relevante o objeto, o universo, os parâmetros, o método, as capacidades acionadas, os entregáveis ou o significado do resultado: entregáveis (família, capacidade, método e versão); indicador e categorias; definição do universo; períodos; modo territorial; parâmetros substantivos com unidades e escalas; critérios (atributo, operador, valor e conectores lógicos); papéis pretendidos; ação de linha. Duas leituras são materialmente diferentes se e somente se suas assinaturas diferem (P-07). Integram a assinatura a identidade e quantidade semântica dos entregáveis validados, as relações pretendidas, seus operandos, alcance entre objetos e/ou contra referência, papel comparativo ou de critério da referência e âncoras da intenção. Mudança exclusivamente técnica na decomposição em etapas não altera essa identidade nem constitui nova intenção. Referência declarada é parâmetro contextual, não intenção automática de comparação; validar relação/operandos/alcance/âncora conforme CFG-VOC. Assinatura de escopo conserva objetivo terminal sem contar verbos ou decomposição técnica (RQ-GOV-28). Captura UI integra o universo efetivo conforme RQ-FLX-16. [T-DET]
- **RQ-GOV-17** — Havendo duas ou mais leituras com assinaturas diferentes, nenhuma determinada por fonte autorizada ou por estado válido e vigente no escopo, C-04 DEVE criar pendência AMBIGUIDADE_MATERIAL tendo as leituras como InterpretacaoAlternativa, apresentadas como OpcaoAutorizada com rótulos governados (seção 4.4.11). Leituras com a mesma assinatura permitem prosseguir, com registro e, quando a compreensão muda, modo ADOTADA_E_EXPLICITADA [C §5.7, §9.4, §9.5]. [T-GOV][T-LLM: M-04, M-05]
- **RQ-GOV-18** — Quando um gatilho de CFG-AMB for detectado, em português ou em inglês, a interpretação DEVE resolvê-lo por fonte autorizada ou estado; caso contrário, cria-se pendência mesmo que o LLM tenha indicado uma única leitura (DA-05). As alternativas da tabela abaixo são apresentadas como OpcaoAutorizada dos conjuntos AMB-01 a AMB-05 de CFG-OPC, com rótulos PT/EN governados. [T-GOV][T-E2E: AT-03, AT-33, AT-34]

| ID | Gatilho | Alternativas mínimas |
|---|---|---|
| AMB-01 | Formas de CFG-AMB ("juntos", "em conjunto", "conjuntamente", "combinados"; "together", "jointly", "combined") sobre duas ou mais unidades sem modo no estado | Em paralelo (CONJUNTO_NAO_COMPARATIVO); comparação (CONJUNTO_COMPARATIVO); agregado (AGREGADO) — Caso 3 |
| AMB-02 | "referência" ("reference") sem qualificador, quando coexistirem, como sentidos admissíveis no estado ou nas fontes aplicáveis, referência territorial e parâmetro de referência | Referência territorial; parâmetro de referência [C §4.3.11] |
| AMB-03 | "vazio", "branco", "nulo" ou "ausente" "significa zero" ("empty", "blank", "null" ou "missing" "means zero") | Semântica de codificação (o registro representa zero); regra de tratamento de ausência, executável só com CFG-AUS [C §7.3] |
| AMB-04 | Marcadores temporais relativos de CFG-VOC ("atual", "hoje", "este ano", "ano passado", "último ano", "recente"; "current", "today", "this year", "last year", "latest year", "recent") quando a data corrente e o último período disponível, ou outras âncoras autorizadas aplicáveis, produzirem leituras materialmente diferentes | Leitura ancorada em cada âncora plausível: período da data corrente; último período disponível na base; outra âncora autorizada aplicável [C §5.8] |
| AMB-05 | "cresceu", "aumentou", "subiu", "caiu", "diminuiu", "declinou" ("grew", "increased", "rose", "fell", "decreased", "declined") quando houver mais de dois períodos disponíveis e o período ou a natureza da análise não estiverem definidos | Mudança entre períodos a especificar (CAP-TMP-01); tendência (CAP-TEN-01) [C §4.3.9, §4.3.10] |
| AMB-06 | "principais", "destaques", "mais relevantes", "piores", "melhores" ("main", "highlights", "most relevant", "worst", "best") sem critério estruturado de ordenação ou seleção | Critério de ordenação, direção e quantidade definidos pelo usuário [C §4.3.15] |

- **RQ-GOV-19** — Toda PerguntaEstruturada DEVE seguir TPL-04 no idioma da sessão e nesta ordem: decisão; motivo documentado opcional e pertinente por UsoDocumental de CFG-DOC; elementos afetados; opções autorizadas quando existentes; consequência sem decisão; formato da resposta conforme o modelo. O motivo usa rótulo Motivo documentado/Documented reason e forma PT/EN materializada do mesmo id_doc. Omitir motivo inaplicável; se explicação requerida não estiver documentada, aplicar DOCUMENTACAO_INSUFICIENTE, sem inventá-la. FN-INT-03, fallback e perguntas determinísticas de CFG-PRV obedecem ao mesmo contrato. Opções provêm somente de CFG-OPC, como OpcaoAutorizada com rótulos PT/EN governados e aliases quando sujeitos à privacidade; é proibido usar código interno como rótulo, pedir ao LLM que invente rótulo ou traduzir rótulo em runtime, e ausência de rótulo obrigatório é erro de configuração/documentação (seção 4.4.11). Decisões, valores e âncoras são estruturados; nenhuma tradução/paráfrase metodológica livre ou opção, fato ou método de conhecimento latente. Não propor valor ausente para confirmação. C-04/V-16 verificam conteúdo, forma, variáveis e âncoras. Na via analítica, linha pode estar legitimamente ausente; na habilitadora basta entrada/base, sem objetos fictícios. [T-GOV][T-E2E: AT-16, AT-134–AT-137, AT-157, AT-162, AT-177]
- **RQ-GOV-20** — Se dados, metadados, configuração, estado e decisões anteriores determinarem inequivocamente a interpretação, o agente NÃO DEVE perguntar; se permanecerem duas ou mais leituras plausíveis com consequências materiais distintas, DEVE perguntar. Isso vale para a pertença de categorias: estabelecida por metadado, declaração de domínio da base ou reconhecimento FTS_INEQUIVOCA, ela não é perguntada, e não há pergunta obrigatória sobre o domínio após o upload; o esclarecimento só ocorre quando a informação for materialmente necessária e permanecer indeterminada. C-04 aplica o controle determinístico de resolução de RQ-GOV-14 também aos parâmetros dos contratos. A regra conservadora aplica-se à ambiguidade material, não a variações linguísticas [C §5.5, §9.4] (P-22, DA-04). [T-GOV][T-LLM: M-05][T-E2E: AT-57]

### 7.6. Conflitos, valores do usuário e dêiticos

- **RQ-GOV-21** — Substituição explícita, pelo usuário, de dado ou parâmetro existente não é conflito: o valor do usuário prevalece no escopo indicado, com registro da origem e da substituição, sem alterar a base original (CFG-PRE). Há conflito quando fontes autorizadas divergem materialmente — valores diferentes, após normalização de formato e unidade, em elemento efetivamente usado por etapa autorizada — e não está claro qual prevalece; o conflito gera pendência CONFLITO_DE_FONTES (BLQ-DEC) antes do uso, e a resolução é registrada com origem no usuário. Regras, métodos, capacidades e configuração nunca são sobrepostos por manifestação do usuário [C §5.3, §7.10, §8.6, Caso 19] (DA-03, P-10). [T-GOV][T-E2E: AT-19]
- **RQ-GOV-22** — O usuário PODE fornecer explicitamente valores e informações factuais necessários a capacidades autorizadas (ex.: população, composição de agrupamento, atributo de território, referência factual, ausência de sobreposição entre componentes de um agregado), desde que o contrato os admita. A informação é validada quanto a formato, tipo, unidade, coerência estrutural e compatibilidade com a capacidade, sem validação externa de veracidade; conjuntos conversacionais e valores complementares distinguem-se por RQ-DAD-31 e RQ-DAD-32; é registrada como manifestação do usuário, com origem, escopo explícito (RQ-LIN-07), conteúdo e impacto sobre a análise; não se propaga para outras linhas, sessões ou usuários; a recuperação, por linha compatível da mesma sessão, do valor factual fornecido sem linha aplicável permanece vinculada ao mesmo objeto e escopo, conforme RQ-LIN-21, sem transferência ou propagação; e gera a limitação correspondente (VALOR_FORNECIDO_PELO_USUARIO ou ADITIVIDADE_POR_PREMISSA_DO_USUARIO). O LLM estrutura a informação, mas não é sua fonte, não a completa e não a propõe para simples confirmação (RQ-GOV-03) (DA-07). [T-GOV][T-E2E: AT-08, AT-19, AT-54]
- **RQ-GOV-23** — Expressões relativas e dêiticas só são resolvidas por âncoras autorizadas; a informação operacional ancora "hoje" e "agora", com fuso ou offset quando disponível, e AMB-04 se aplica quando âncoras plausíveis divergem. Quando o fuso ou offset não puder ser estabelecido e isso alterar materialmente a resolução, cria-se pendência AMBIGUIDADE_MATERIAL (CFG-OPR) [C §5.8]. [T-GOV][T-E2E: AT-34]
- **RQ-GOV-31** — O usuário PODE definir explicitamente um critério normativo para sua análise (ex.: "nesta análise, considere insuficiente densidade abaixo de 1 por 1.000"). C-04 DEVE registrar valor, operador, unidade e escala, classificação associada, origem e escopo. O critério vale apenas no escopo indicado, não se torna regra global e não se propaga; critérios sobrepostos com classificações diferentes geram pendência. Critérios não são inventados nem recuperados da memória do LLM (DA-21). [T-GOV][T-E2E: AT-46]
- **RQ-GOV-32** — A declaração explícita do usuário de que uma categoria integra a FTS no contexto da análise é registrada com escopo (RQ-DAD-19); a simples solicitação da categoria não é tratada como declaração, e declaração de domínio da base ou do usuário não se converte em classificação universal nem amplia a configuração. O agente NÃO DEVE sugerir essa declaração como forma de tornar pertinente pedido sobre força de trabalho de outro setor (DA-04). [T-GOV][T-E2E: AT-24, AT-48]

### 7.7. Verificação pré-execução, contexto de consistência e autorização

- **RQ-GOV-24** — Antes de cada etapa da via ANALITICA, C-04 DEVE executar a lista abaixo; os itens 1 e 2 só são refeitos se replanejamento introduzir intenção materialmente distinta. A via HABILITADORA de CAP-EXA-01 usa os controles específicos de RQ-DAD-34, sem exigir base já DISPONIVEL [C §5.9]. O controle é por etapa e pelas entradas ou partes de entradas efetivamente necessárias a cada relação/elemento conforme contrato; estado agregado AGUARDANDO_USUARIO não é impedimento adicional para autorizar ou executar parte independente. Causa primária da falha fica vinculada à condição verificada, com motivos específicos e cadeia de dependências preservados, conforme RQ-CAP-08. Zero avaliáveis não substitui essa classificação. [T-GOV]

| Nº | Verificação | Falha |
|---|---|---|
| 1 | Pertinência PERTINENTE registrada para a parte | ADM-NP ou pendência |
| 2 | Família autorizada, sem exclusão | ADM-FE |
| 3 | Capacidade ATIVA na configuração da sessão e operacionalmente disponível | ADM-SC antes da execução; OPR-IND durante a execução |
| 4 | Bases necessárias DISPONIVEL e presentes no contexto | BLQ-DAD; base com pendência habilitadora aberta: a etapa aguarda essa pendência, reapresentada sem duplicata (RQ-FLX-22) |
| 5 | Atributos semânticos exigidos pela operação estabelecidos (RQ-DAD-36) | BLQ-SIG |
| 6 | Parâmetros obrigatórios presentes, tipados, dentro dos graus de liberdade e com âncora válida | BLQ-INF |
| 7 | Pré-condições metodológicas do contrato atendidas | BLQ-MET |
| 8 | Compatibilidade contratual de entradas/saídas; comparação entre contextos conforme RQ-ORQ-13; suporte e compatibilidade metodológica temporal de agregados conforme CAP-AGR-01 (F-05b); cobertura espacial conforme CAP-ESP-02 | BLQ-MET, ou avaliabilidade por elemento quando definida no contrato |
| 9 | Dependências efetivamente necessárias concluídas com resultado VALIDO/APRESENTAVEL quando o contrato exige valor; exceção CAP-SUB-01: predecessor encerrado sem resultado pode ser RefSaidaEsperada e folha NAO_AVALIAVEL/DEPENDENCIA_NAO_AVALIAVEL com CausaOrigem; avaliar árvore completa antes de decidir; pendência ainda resolúvel não é ausência definitiva; parcialidade contratual não exige completude artificial | BLQ-DEP somente para o que depende da entrada indisponível; preservar causa de origem e partes independentes (RQ-GOV-29, CAP-CMP-01) |
| 10 | Nenhuma decisão substantiva pendente que afete a etapa | BLQ-DEC |
| 11 | Resultados reutilizados VALIDO com vínculo VIGENTE; resultados deslocados usados como componente ou entrada de comparação (RQ-LIN-20); uso histórico autorizado (RQ-ORQ-07) | BLQ-DEP, ou nova execução quando autorizada |
| 12 | Coincidência com o contexto da autorização, inclusive referências e diferenças autorizadas dos contextos de entrada (RQ-ORQ-13), sem exigir identidade entre os contextos de origem | Suspensão (seção 9.5) |

- **RQ-GOV-25** — Pré-condições metodológicas (ex.: número de períodos, presença de geometria) DEVEM ser calculadas por C-04 ou C-06, nunca pelo LLM [C §5.9]. [T-GOV]
- **RQ-GOV-26** — A autorização ANALITICA DEVE fixar o ContextoConsistencia completo da composição, incluindo entradas de contextos distintos e sua verificação de compatibilidade quando aplicável (RQ-ORQ-13) [C §5.9, §6.5]. [T-DET]
- **RQ-GOV-27** — A Autorizacao de tipo ANALITICA só é emitida com interpretação validada, sem pendência aberta que afete as etapas autorizadas, com plano validado (seção 9.1) e com a lista de verificação aprovada para as etapas sem dependências pendentes; as demais etapas são reverificadas na execução. A autorização é válida para suas etapas e contexto mesmo durante AGUARDANDO_USUARIO; não exige passagem prévia do estado agregado por AUTORIZADA ou EM_EXECUCAO. O plano pode identificar partes ainda pendentes sem autorizar sua execução. A resposta que libere um ramo não substitui as verificações e autorizações pertinentes. [T-GOV]
- **RQ-GOV-28** — O LLM propõe entregáveis estruturados; a governança os valida; ambiguidade material sobre o que é entregável gera pendência. Na autorização, etapas cuja saída constitua entregável validado (pedido do usuário ou ampliação aceita) recebem COMPONENTE_DIAGNOSTICO; as demais, SUPORTE_INTERMEDIARIO. Resultados de suporte não são promovidos silenciosamente; o papel só muda por ampliação do usuário (Parte 12) [C §5.9, §8.4] (P-23). Número e identidade dos entregáveis derivam dos resultados semanticamente distintos solicitados. Um objetivo aplicado a várias unidades pode ser um único entregável; relatórios autônomos explicitamente pedidos são entregáveis distintos. Quantidade de unidades, capacidades ou etapas não cria autonomia semântica. A governança valida essa identidade antes da decomposição técnica e a preserva em reformulações equivalentes (RQ-QUA-06); o plano não cria novos entregáveis nem modifica terminalidade por escolhas técnicas. D21: resultado intermediário integralmente contido no objetivo terminal é conteúdo necessário, não entregável adicional por mera menção. Calcular densidades e comparar constitui um entregável comparativo; tabela e relatório explicitamente separados constituem dois. Um entregável adicional exige âncora de artefato/apresentação distintos, ação explicitamente independente ou objetivo autônomo. InterpretacaoOperacional registra objetivo terminal, conteúdo, dependências e fundamento de autonomia. C-04 valida estrutura/âncoras, sem novo classificador semântico geral; leituras materialmente concorrentes geram pendência. A assinatura não depende do número de verbos, etapas ou lotes. D17: retirada versiona o conjunto vigente e registra RETIRADA_PELO_USUARIO; não altera mérito do estado histórico nem promove suporte a componente. [T-GOV][T-E2E: AT-22]

### 7.8. Separabilidade e execução parcial

- **RQ-GOV-29** — A separabilidade DEVE ser calculada sobre as dependências efetivas do grafo e da interpretação: impedimento bloqueia as etapas, relações ou partes que necessitem daquela entrada e seus descendentes efetivos (BLQ-DEP), não partes independentes. Cada entregável semântico conserva as dependências obrigatórias de seu contrato e de depende_de; avaliabilidade parcial contratualmente admitida não é transformada em exigência de completude por agrupar operações numa etapa. CAP-CMP-01 verifica operandos de cada relação; relação que exige todos não usa subconjunto substituto. Parte independente só executa com autorização válida, sem modificar silenciosamente o sentido do pedido e com resultado válido e interpretável isoladamente; pode percorrer E7–E12 durante AGUARDANDO_USUARIO. Suporte de entregável bloqueado não é promovido a resposta por conveniência; elementos avaliáveis de um resultado parcial autorizado conservam o papel do entregável semântico. Entrada sem resultado referencia registros da etapa impedida, sem resultado fictício. A decomposição técnica não cria entregáveis nem altera conteúdo, avaliabilidade ou terminalidade [C §5.2, §5.9, §9.6]. [T-DET][T-E2E: AT-41, AT-91, AT-97, AT-113, AT-115]
- **RQ-GOV-30** — Na execução parcial, a resposta DEVE apresentar, junto com os resultados parciais e na mesma resposta, quais partes foram executadas, quais não puderam ser processadas ou avaliadas, o motivo de cada uma e quais entregáveis posteriores ficaram impossibilitados por dependência. NÃO DEVE apresentar resultado parcial como completo, substituir a análise impossibilitada, tratar dependência ausente como resultado negativo ou combinar resultados incompatíveis. Exemplo: "Foi possível calcular a densidade do território A. A densidade do território B não pôde ser calculada porque o denominador populacional não está disponível. Por esse motivo, a comparação entre A e B também não pôde ser realizada." [C §9.6] (P-08). Na mesma interação, distinguir partes que aguardam pendência resolúvel, elementos não avaliáveis e impossibilidade definitiva, com motivos, alcance, dependentes efetivos e pergunta necessária. A expressão "impossibilitados" não transforma espera resolúvel em não executabilidade definitiva. A ocorrência OPR-IND restrita à síntese dispensável é informada sem negar o atendimento de RQ-DEG-04. O exemplo de A, B e comparação não estabelece regra de um entregável por unidade; autonomia semântica segue RQ-GOV-28. [T-GOV][T-E2E: AT-41]

---

## Parte 8 — Capacidades: contratos e catálogo v1.2.4

### 8.1. Esquema de contrato

Todo contrato registrado em CFG-CAP DEVE conter: identificador, nome, famílias, versão, status, natureza de execução, objetivo, entradas (tipos e obrigatoriedade), parâmetros (tipo, domínio, unidade ou escala, ClasseAutoridade, valor fixado por regra quando houver), elementos que o usuário pode fornecer, dados requeridos (papéis e atributos semânticos), pré-condições metodológicas verificáveis, método (referência a CFG-MET e versão), esquema de saída, regras de avaliabilidade, regras de desfecho, limitações padrão, compatibilidades de entrada e saída, escolhas proibidas, decisões de origem e testes mínimos [C §5.5, §5.9, §13.3].

### 8.2. Regras comuns

- **RQ-CAP-01** — Nenhuma capacidade é executada fora de seu contrato registrado. [T-GOV]
- **RQ-CAP-02** — Mesmas entradas canônicas e mesmas versões DEVEM produzir o mesmo `hash_conteudo` [C §8.10]. [T-DET][T-E2E: AT-40]
- **RQ-CAP-03** — Cálculos, filtros, classificações, comparações e decisões analíticas DEVEM usar o valor completo disponível, em aritmética exata, sem arredondamento prévio; o arredondamento ocorre somente na apresentação (RQ-REP-05) (DA-20). [T-DET]
- **RQ-CAP-04** — Cada elemento do universo recebe avaliabilidade própria. Nenhum elemento é descartado silenciosamente; NAO_AVALIAVEL nunca é tratado como zero ou como NAO_ATENDE (INV-04) [C §7.4, §8.11]. [T-DET]
- **RQ-CAP-05** — Toda saída DEVE conter cobertura, exclusões, limitações tipadas, parâmetros com âncoras, método e versão e identificador do contexto. [T-DET]
- **RQ-CAP-06** — Expressões livres, consultas, fórmulas ou código recebidos como parâmetro DEVEM ser rejeitados [C §3.5, §4.3.13]. [T-GOV]
- **RQ-CAP-07** — Classificações só são produzidas por métodos de CFG-MET ou por critério normativo do usuário registrado (RQ-GOV-31); capacidades não emitem julgamentos textuais. [INSP]
- **RQ-CAP-08** — A apuração distingue existência de resultado analítico e classificação causal do impedimento. Em ordem: (a) nenhum elemento ou relação solicitada avaliável, inclusive universo unitário: não há resultado analítico, e o desfecho segue a causa normativa primária registrada; (b) seleção ou subconjunto com avaliáveis e conjunto ATENDE vazio: RES-VAZ; (c) capacidade classificatória em que nenhum elemento avaliável recebeu classe: RES-SCL; (d) há limitação analítica: RES-LIM; (e) demais casos: RES-VAL. Limitações acompanham o resultado em qualquer caso. Em (a), dado necessário ausente/insuficiente gera BLQ-DAD; significado necessário ausente/não autorizado, BLQ-SIG; método não incorporado ou condição metodológica não satisfeita, inclusive incompatibilidade entre tipos de contagem, BLQ-MET; falha/indisponibilidade operacional, OPR-* aplicável; dependência anterior necessária não satisfeita, BLQ-DEP com cadeia até a causa de origem. BLQ-INF, BLQ-DEC e admissão conservam seus casos próprios. Zero avaliáveis não determina BLQ-DAD automaticamente nem substitui a classificação do contrato e da verificação pré-execução (seção 7.7). Motivo analítico por elemento, classe do desfecho e causas secundárias permanecem distintos e rastreáveis; INCOMPARABILIDADE não é substituída por dado ausente. A apuração aplica-se ao resultado do entregável semântico, independentemente da quantidade técnica de etapas, sem flexibilizar condições de completude do contrato [C §8.11, §9.2]. Falha parcial de unidade operacional preserva saídas independentes conforme RQ-ORQ-14; o estado da etapa agregadora não apaga estados ou causas das unidades, e entregáveis compostos apuram cada elemento por ResultadoElemento (RQ-RES-04). Em CAP-SUB-01, árvore com RefSaidaEsperada é avaliada antes deste critério de resultado, sem criar saída fictícia nem relaxar a coorte de CAP-ROT-01. [T-DET][T-E2E: AT-80, AT-97, AT-112, AT-113, AT-115]
- **RQ-CAP-09** — Variáveis auxiliares só influenciam a análise nas funções previstas no contrato [C §3.7]. [T-GOV]
- **RQ-CAP-10** — Capacidade que não esteja ATIVA e operacionalmente disponível nunca é executada nem emulada [C §11.9]. [T-GOV]
- **RQ-CAP-11** — Saídas de capacidades não contêm identificadores individuais (Parte 18). [T-GOV]
- **RQ-CAP-12** — Os elementos que o usuário pode fornecer são declarados no contrato; valores fornecidos são validados quanto a formato, tipo, unidade, coerência estrutural e compatibilidade e registrados com origem e escopo (RQ-GOV-22) (DA-07). [T-GOV]
- **RQ-CAP-13** — Método alternativo só é escolhido pelo usuário quando o contrato o permite; nesta versão cada capacidade tem método único e versionado (DA-06, CFG-MET). [INSP]

### 8.3. Catálogo v1.2.4

| ID | Capacidade | Família | Natureza | Status | Decisões |
|---|---|---|---|---|---|
| CAP-EXA-01 | Examinar dados | FAM-01 | Determinística | ATIVA | DA-02 |
| CAP-UNI-01 | Delimitar universo | Suporte transversal | Determinística | ATIVA | DA-07, DA-16 |
| CAP-IND-01 | Quantitativo absoluto | FAM-02 | Determinística | ATIVA | DA-09, DA-27 |
| CAP-IND-02 | Densidade | FAM-02 | Determinística | ATIVA | DA-03, DA-07, DA-09, DA-10, DA-20 |
| CAP-AGR-01 | Indicador agregado | FAM-06 | Determinística | ATIVA | DA-09, DA-10, DA-16 |
| CAP-DIS-01 | Medidas de posição | FAM-07 | Determinística | ATIVA; posição percentual não incorporada | DA-11 |
| CAP-DIS-02 | Quantis e classes de posição | FAM-07 | Determinística | ATIVA | DA-11 |
| CAP-DIS-03 | Distribuição de frequências | FAM-07 | Determinística | ATIVA | DA-12 |
| CAP-CMP-01 | Comparação estruturada | FAM-04 | Determinística | ATIVA | DA-13 |
| CAP-TMP-01 | Mudança temporal | FAM-08 | Determinística | ATIVA | DA-14 |
| CAP-TEN-01 | Tendência | FAM-08 | Determinística | ATIVA | DA-15 |
| CAP-ROT-01 | Rotatividade e permanência da coorte inicial | FAM-08 | Determinística | ATIVA | Configuração Inicial de Implementação (seção 25.3) |
| CAP-REF-01 | Referências territoriais | FAM-09 | Determinística | ATIVA | DA-17 |
| CAP-ESP-01 | Distância | FAM-10 | Determinística | ATIVA | DA-17 |
| CAP-ESP-02 | Referência mais próxima | FAM-10 | Determinística | ATIVA | DA-17 |
| CAP-ESP-03 | Faixas de distância | FAM-10 | Determinística | ATIVA | DA-12, DA-17 |
| CAP-SUB-01 | Subconjunto por critério | FAM-11 | Determinística | ATIVA | DA-19, DA-20, DA-21 |
| CAP-SUB-02 | Ordenação | FAM-11 | Determinística | ATIVA | DA-18 |
| CAP-SUB-03 | Seleção por posição | FAM-11 | Determinística | ATIVA | DA-18 |
| CAP-REP-01 | Tabela | FAM-13 | Apresentação | ATIVA | DA-20, DA-23 |
| CAP-REP-02 | Gráfico de barras, gráfico de linhas e série temporal | FAM-13 | Apresentação | ATIVA | DA-20, DA-23 |
| CAP-REP-03 | Mapa | FAM-13 | Apresentação | ATIVA, se houver geometria autorizada | DA-17, DA-23 |
| CAP-REP-04 | Painel simples | FAM-13 | Apresentação | ATIVA, como justaposição de CAP-REP-01 a CAP-REP-03 | DA-23 |
| CAP-REP-05 | Relatório consolidado HTML e exportação PDF | FAM-13 | Apresentação | ATIVA | DA-23, DA-24 |
| CAP-REP-06 | Exportação tabular CSV | FAM-13 | Apresentação | ATIVA | DA-20, DA-23 |
| CAP-SIN-01 | Síntese analítica | FAM-14 | LLM com validação | ATIVA | DA-05, DA-22, DA-26 |

Todas as 26 capacidades do catálogo estão ATIVA na Configuração Inicial de Implementação. O que permanece não incorporado está na seção 8.6.

### 8.4. Contratos

**CAP-EXA-01 — Examinar dados.** Entradas: entrada TRIADA (versão protegida), com mapeamentos conhecidos e quadro opcional; semântica ainda indefinida não impede o perfil. Execução automática após introdução deliberada por upload ou conversa, sob autorização HABILITADORA (RQ-DAD-34), sem E9 nem base previamente DISPONIVEL; sua conclusão leva a entrada a EXAMINADA (RQ-DAD-42). Quando solicitada como entregável, usa a via ANALITICA e base DISPONIVEL. Saída (perfil da base): estrutura, campos e tipos; listas de períodos, territórios e categorias; consistência estrutural e validade de códigos; duplicidades por chave; ausentes por campo; existência de registro por combinação; semântica declarada e significados reconhecidos por regra ou pendentes de confirmação, inclusive declaração de domínio existente e estado de reconhecimento das categorias da base pela configuração governada (seção 4.3); condições de comparabilidade, distinguindo códigos coincidentes de significado longitudinal autorizado, âncoras, escopo e exceções (CFG-TER); matriz de aplicabilidade por capacidade. O exame não pergunta obrigatoriamente pelo domínio da base (RQ-GOV-20). Proibido: o conteúdo da coluna "Proibido" de RQ-DAD-13 (DA-02, P-15). Na seleção de planilhas independentes, materializar e examinar cada entrada com origem e escopo próprios; combinação depende da regra autorizada e das verificações de RQ-DAD-30/43, sem inferir temporalidade pelo nome da planilha. D13/D15/D25: perfil e estrutura usam aliases para metadados minimizados, preservando tipos/papéis e linguagem funcional triada. Não examinar base recusada nem usar células de abas não selecionadas. Fonte auxiliar selecionada obedece ao próprio escopo; negativa elimina perfil/contexto ativo (RQ-DAD-20/23/42/43).

**CAP-UNI-01 — Delimitar universo.** Entradas: DefinicaoUniverso, quadro e bases. Parâmetros PARAMETRIZAVEL_PELO_USUARIO: categoria, períodos e nível territorial quando exigido pelo recorte/operação, resolvidos sem pergunta quando inequívocos (RQ-GOV-14, RQ-DAD-29). Pré-condições: QUADRO_COMPLETO exige quadro (RQ-DAD-09); AGRUPAMENTO exige fonte autorizada ou composição explícita do usuário (RQ-DAD-12); identificadores de LISTA inexistentes no quadro ou na base são reportados, não descartados. Saída: membros com PresencaNoUniverso, forma de definição preservada e unidades fora do universo em exclusões. Condições com critério analítico são executadas por CAP-SUB-01. QUADRO_COMPLETO sem quadro produz BLQ-DAD/DetalheBloqueio.QUADRO_UNIVERSO_AUSENTE. Captura UI válida pode fornecer LISTA conforme RQ-FLX-16; não representa operação nem presume quadro completo.

**CAP-IND-01 — Quantitativo absoluto.** Entradas: universo, base de FTS e definição de CFG-IND. Parâmetros: categorias e períodos, conforme RQ-GOV-14. Unidade de observação, unidade de contagem e identidade seguem RQ-DAD-18 e RQ-DAD-35. O procedimento determinístico aplica, conforme a estrutura e o significado autorizados: soma de campos quantitativos aditivos; contagem de registros quando cada registro representa a unidade que se deseja contar e suas repetições estão resolvidas; ou contagem de identidades distintas da entidade medida. Não se exige coluna física de quantidade em base individualizada. Contar pessoas distintas a partir de vínculos com identificador de pessoa suficiente não é conversão entre unidades; contar linhas de vínculos como pessoas sem essa condição é proibido.

Quando a medida for pessoa, cada pessoa é contada uma vez em cada território, categoria e período em que esteja presente; vários vínculos na mesma combinação não a multiplicam. Uma pessoa em dois municípios conta em ambos, e o agregado segue CAP-AGR-01. Sem identidade suficiente ou unicidade estabelecida para a medida pedida, pessoas únicas não são produzidas (BLQ-MET quando a condição é global; SIGNIFICADO_NAO_ESTABELECIDO ou DADO_AUSENTE nos elementos afetados conforme a causa); não se descartam registros com identidade ausente para declarar total completo. A contagem na unidade de observação PODE ser oferecida como análise distinta, se habilitada. Várias categorias produzem valores separados; sua união exige CAP-AGR-01. Contagem de pessoas no universo FTS sem recorte categorial conta a união das identidades no território/período, sem somar totais por categoria; a composição autorizada da FTS permanece exigida (RQ-DAD-19). Avaliabilidade: unidade sem registro recebe SEM_REGISTRO_OBSERVADO, salvo VALOR_ZERO_CODIFICADO ou metadado de exaustividade que estabeleça zero; valor ausente recebe DADO_AUSENTE. Saída: valor, unidade medida e fundamento da contagem por território/período/categoria ou universo autorizado, sem identificadores pessoais.

**CAP-IND-02 — Densidade.** Fórmula: D(u, p, c) = Q(u, p, c) / P(u, p′), sendo Q o quantitativo de CAP-IND-01 e P o denominador populacional do mesmo território. Por padrão, p′ = p; outro denominador ou período só é usado quando explicitamente indicado pelo usuário ou por regra autorizada, com registro e limitação DENOMINADOR_ALTERNATIVO (DA-09). Valor canônico: razão por habitante, em precisão integral. Escala de apresentação, por precedência: (1) escala explicitamente indicada pelo usuário; (2) escala configurada para o indicador em CFG-IND (nenhuma nesta versão); (3) por 1.000 habitantes. A escala é transformação de apresentação e não muda automaticamente conforme a magnitude do resultado. Pré-condições: atributos de POPULACAO exigidos pela operação estabelecidos (RQ-DAD-36; em território e categoria únicos, sem agregação, aditividade territorial e compartilhamento populacional não são exigidos); mesma unidade territorial; conflito de fonte do denominador resolvido antes do cálculo (RQ-GOV-21). Valor de população fornecido explicitamente pelo usuário (RQ-GOV-22) ou em substituição explícita (RQ-GOV-21) é usado no escopo indicado, com a limitação correspondente. Avaliabilidade: Q não avaliável gera DEPENDENCIA_NAO_AVALIAVEL; P ausente gera DENOMINADOR_AUSENTE (Caso 8); P igual a zero gera DENOMINADOR_ZERO. A ausência não é tratada por imputação, estimativa ou exclusão (DA-10). Denominadores de agregados seguem exclusivamente a composição por dimensão de CAP-AGR-01. Proibido: estimar denominador; usar valor não ancorado.

**CAP-AGR-01 — Indicador agregado.** Entradas: conjunto de territórios ou de categorias definido por fonte autorizada ou indicado explicitamente pelo usuário, sem composição inferida pelo LLM, e indicador. Método (DA-16, AV-01): o agregado é calculado a partir dos componentes, nunca pela média das densidades individuais; sua densidade é Q agregado / P correspondente, com escala aplicada depois. O denominador é composto pela dimensão agregada: (a) territórios distintos: somam-se populações territorialmente distintas e aditivas no agregado, segundo definição e período autorizados; (b) categorias no mesmo território/período: a população compartilhada entra uma única vez; (c) combinação territorial e categorial: constrói-se P pelas unidades territoriais efetivamente incluídas segundo a regra de cobertura multicategorial abaixo, sem repeti-lo pelo número de categorias. A chave do denominador identifica território, período e definição populacional, com correspondências autorizadas; valores numericamente iguais em territórios distintos não são duplicatas, e valores conflitantes para a mesma chave seguem RQ-GOV-21. Total territorial e seus componentes não são somados juntos (RQ-DAD-30). A sobreposição de pessoas no numerador não multiplica nem deduplica população por si só. Regra de sobreposição (complemento de DA-16), aplicável a territórios e a categorias: quando a unidade de contagem é pessoa e uma mesma pessoa pode pertencer a mais de um componente, a soma das contagens dos componentes não equivale à contagem de pessoas únicas do agregado. O resultado declara seu TipoContagemAgregada:

- UNIDADES_DISTINTAS (pessoas únicas no agregado): obtido por deduplicação sobre a união dos componentes, quando houver identidade de deduplicação suficiente para toda a união (RQ-DAD-35), ou pela soma das contagens, quando a ausência de sobreposição estiver estabelecida por metadado ou fonte autorizada ou por premissa fornecida explicitamente pelo usuário (RQ-GOV-22). O resultado registra o FundamentoUnicidade e, no caso de premissa, a limitação ADITIVIDADE_POR_PREMISSA_DO_USUARIO.
- SOMA_DOS_COMPONENTES: soma das contagens ou presenças dos componentes, produzida quando o usuário a pede, inclusive depois de informado de que as pessoas únicas não podem ser estabelecidas (ex.: "mesmo assim, some os municípios"). Leva a limitação SOMA_COM_POSSIVEL_DUPLA_CONTAGEM e nunca é rotulada como número de pessoas únicas ou de profissionais distintos (V-14, RQ-REP-14).

Sem deduplicação e sem informação de ausência de sobreposição, a contagem de pessoas únicas não é produzida, e a soma não é apresentada como tal: cria-se pendência DECISAO_SUBSTANTIVA que informa que a soma das contagens dos componentes pode ser produzida, com possível dupla contagem, e que a contagem única depende de dados de deduplicação ou de informação do usuário sobre ausência de sobreposição, sem propor essa informação para simples confirmação (RQ-GOV-03). Quando o próprio pedido já for de soma das contagens, ela é produzida diretamente como SOMA_DOS_COMPONENTES. Para outras unidades de contagem, o agregado exige aditividade estabelecida por metadado ou confirmação do usuário (RQ-DAD-05, RQ-DAD-36). Pré-condições territoriais: membros do mesmo nível ou correspondência autorizada por dado, metadado, fonte autorizada ou manifestação explícita do usuário (CFG-TER deliberadamente vazio, seção 4.4.7); nenhuma equivalência com unidade superior observada é presumida. Categorias combinadas exigem significado compatível e a regra de sobreposição acima; nível territorial não é atributo de categoria. Cobertura: se parte dos membros não for avaliável, produz-se agregado parcial sobre os avaliáveis, com limitação AGREGADO_PARCIAL que informa quantos membros foram incluídos e quantos ficaram de fora, com a lista; o agregado parcial não é apresentado como representativo do conjunto completo e é o método autorizado previsto na exceção de DA-10, não exclusão silenciosa. Em agregado multicategorial — duas ou mais categorias solicitadas conjuntamente —, a unidade de inclusão é o território: em cada período, um território só integra o agregado se todas as categorias solicitadas forem avaliáveis nele; território com apenas parte delas fica NAO_AVALIAVEL para o agregado (DEPENDENCIA_NAO_AVALIAVEL), e nem suas categorias avaliáveis nem sua população entram no numerador ou no denominador; a população integral de um território nunca é usada quando o objeto multicategorial solicitado está apenas parcialmente observado nele. O agregado com cobertura incompleta é identificado como parcial (AGREGADO_PARCIAL) e registra os territórios não avaliáveis e as categorias não avaliáveis em cada um, com motivos (F-05a). Se nenhum membro for avaliável, não há resultado analítico; o desfecho segue a causa normativa de RQ-CAP-08, sendo BLQ-DAD quando dado necessário estiver ausente ou insuficiente. Correspondência estrutural autorizada entre níveis não estabelece, por si, significado longitudinal: este segue CFG-TER.

Para densidade parcial, numerador e denominador correspondem ao mesmo suporte efetivamente incluído, e cada população territorial compartilhada é contada uma vez nesse suporte. O resultado registra, por período, membros previstos, incluídos e não avaliáveis com motivos, combinações território–categoria que compõem Q, chaves territoriais/populacionais que compõem P e correspondências aplicadas (ResultadoEstruturado.suporte_agregado). Esses registros não contêm identidades individuais. Mudança temporal ou tendência exige compatibilidade determinística do suporte entre períodos: os membros efetivos e suas correspondências devem representar o mesmo conjunto. Mudanças nos valores ou nas pessoas presentes não são, por si sós, mudança de suporte. Exige também compatibilidade metodológica entre os períodos (F-05b): identidade de TipoContagemAgregada; de FundamentoUnicidade e, quando a unicidade decorrer de deduplicação, do domínio da identidade utilizada; de unidade de contagem; de definição populacional; de método e versão relevantes; e dos demais componentes metodológicos que alterem o significado do valor. Valores UNIDADES_DISTINTAS não são comparáveis com valores SOMA_DOS_COMPONENTES; os componentes divergentes são registrados. Quando os membros efetivos representam conjuntos diferentes ou a compatibilidade metodológica não se verifica, cada agregado permanece válido isoladamente, mas CAP-TMP-01 e CAP-TEN-01 marcam INCOMPARABILIDADE, sem crescimento, declínio ou aceleração, e CAP-CMP-01 segue RQ-ORQ-13. É proibido selecionar automaticamente membros comuns; isso seria método distinto não incorporado por esta correção (AV-07).

**CAP-DIS-01 — Medidas de posição.** Estatísticas (DA-11): MINIMO e MAXIMO, com todas as unidades que os atingem; MEDIANA, valor central para número ímpar de observações e média dos dois valores centrais para número par; PERCENTIL p, pelo método Hyndman–Fan tipo 7, com h = (n − 1)·p + 1 e interpolação linear entre as observações ordenadas de posições ⌊h⌋ e ⌊h⌋ + 1. Opera sobre os elementos avaliáveis; não avaliáveis são listados e a cobertura é explicitada (Caso 17). A posição relativa de uma unidade é expressa pela posição na ordenação (CAP-SUB-02) e pela classe de quantil (CAP-DIS-02); a posição percentual numérica é METODO_NAO_INCORPORADO. Proibido: interpretação normativa de posição [C §4.3.6].

**CAP-DIS-02 — Quantis e classes de posição.** Parâmetro PARAMETRIZAVEL_PELO_USUARIO: número de classes K (quartis, quintis, decis ou outro). Pontos de corte: q_k = percentil tipo 7 em k/K, para k = 1 a K − 1, calculados sobre os elementos avaliáveis. Pertença, com valores coincidentes com o corte na classe inferior: classe 1, x ≤ q_1; classe k, q_(k−1) < x ≤ q_k; classe K, x > q_(K−1). Valores iguais recebem sempre a mesma classe, sem desempate artificial; classes podem ter tamanhos diferentes, inclusive vazias. Não avaliáveis ficam fora das classes e são listados. Exemplo: valores 3, 5, 7, 9, 11 em quartis têm cortes 5, 7 e 9 e classes Q1 {3, 5}, Q2 {7}, Q3 {9} e Q4 {11} (DA-11). Saída: cortes em precisão integral, pertença, tamanho das classes e cobertura.

**CAP-DIS-03 — Distribuição de frequências.** Intervalos fornecidos explicitamente pelo usuário ou por método autorizado (nenhum nesta versão, CFG-MET); o LLM não cria intervalos, e na falta deles cria-se pendência (DA-12). Convenção interna [a, b): inclui o limite inferior e exclui o superior; o último intervalo inclui também o limite superior final. Notação explícita do usuário é respeitada. Apresentação intuitiva, como "0 a <1", com o último intervalo exibido como fechado, como "2 a 3". Saída: contagem de unidades avaliáveis por intervalo, pertença de cada unidade, unidades fora de todos os intervalos e não avaliáveis à parte.

**CAP-CMP-01 — Comparação estruturada.** Relações (DA-13): IGUALDADE; ORDEM (maior ou menor); DIFERENCA_ABSOLUTA (a − b); RAZAO (a / b; com b = 0, NAO_AVALIAVEL por BASE_ZERO); DIFERENCA_RELATIVA ((a − r) / r × 100, em relação à referência r explicitamente definida; com r = 0, NAO_AVALIAVEL por BASE_ZERO; referência não explícita gera pendência). Comando genérico entre dois objetos produz valores lado a lado, IGUALDADE ou ORDEM e DIFERENCA_ABSOLUTA; entre três ou mais objetos, produz valores e ordem do conjunto avaliável, sem diferenças automáticas de todos os pares. Diferenças adicionais exigem pares explicitamente indicados ou intenção comparativa contra referência explicitamente estabelecida. A cardinalidade e as relações autorizadas são as do pedido, não as dos objetos que restarem avaliáveis. A diferença a − b é assinada, não módulo; operandos e sentido da subtração são explícitos. Comparação intencionalmente solicitada contra parâmetro de referência autorizado produz, por objeto aplicável, valor, igualdade ou ordem e diferença x − r. "Em relação à referência" não implica percentual: RAZAO e DIFERENCA_RELATIVA exigem intenção explícita correspondente. "Entre si" estabelece relações entre objetos; "entre si e com a referência" estabelece ambos os alcances. A referência usada como limiar ou critério ("abaixo de", "acima de") segue CAP-SUB-01, sem classificação normativa não autorizada. Referência sem unidade só é interpretada automaticamente quando houver exatamente um ContextoDeMedida determinístico para o objeto comparado — indicador, unidade, denominador e escala de apresentação, inclusive a escala resolvida pela precedência de CAP-IND-02, com fallback governado por 1.000 habitantes para densidade —, com registro do valor declarado, do contexto adotado, de sua origem e do valor convertido pela matemática vigente. Sem nenhum ContextoDeMedida determinístico, PARAMETRO_FALTANTE (BLQ-INF); com mais de um, pendência AMBIGUIDADE_MATERIAL; nenhum contexto, unidade ou escala é inventado (H2). CAP-SUB-01 aplica a mesma regra. Ordem comparativa não cria posições de ranking nem altera a ordem visual de RQ-REP-03; ranking exige CAP-SUB-02. Havendo universo territorial inequívoco estabelecido na linha, a comparação o usa, sem agregação territorial silenciosa; permanecendo plausível mais de uma delimitação territorial materialmente distinta, cria-se pendência AMBIGUIDADE_MATERIAL (F-10). Pré-condições de compatibilidade: mesmo indicador e definição; mesma unidade de contagem; mesma escala canônica; métodos e versões relevantes compatíveis; significado e territorialidade compatíveis; para agregados, a compatibilidade metodológica de CAP-AGR-01 (F-05b). Contextos de origem distintos são admitidos conforme RQ-ORQ-13, sem exigir identidade integral nem recálculo artificial; a dimensão deliberadamente comparada é registrada. Mudanças entre períodos são tratadas por CAP-TMP-01; comparação de categorias não as funde. [C §4.3.7]. D18: declarar referência contextual não solicita comparação, critério, ranking ou percentual. “Considere 2,36 como referência e analise A, B e C” registra o parâmetro e não produz x − r; papel materialmente indefinido gera uma pendência. Relações exigem intenção governada e âncora, conforme CFG-VOC. O valor intermediário contido na comparação não é entregável autônomo (D21).

Avaliabilidade de CAP-CMP-01: cada relação autorizada é avaliada pelos operandos efetivamente necessários. Objeto não avaliável impede suas relações dependentes, preservando a causa, mas não impede relações independentes entre avaliáveis compatíveis. A existência de resultado exige ao menos uma relação solicitada avaliável; valores lado a lado não tornam relação impossível avaliável. Relações avaliáveis coexistindo com relações não avaliáveis produzem resultado com limitação conforme RQ-CAP-08. Sem relação avaliável, o desfecho segue a causa normativa; comparação dependente de cálculo anterior bloqueado conserva BLQ-DEP e sua cadeia de origem (RQ-GOV-29). Um território e uma referência autorizada podem formar a relação; não são necessários dois territórios. Relação que exija todos os operandos não usa subconjunto substituto. A divisão ou reunião de etapas não altera relações, avaliabilidade ou entregáveis semânticos.

Saída de CAP-CMP-01: objetos originalmente solicitados, atributos, valores disponíveis, relações autorizadas com operandos e sentido, avaliabilidade por relação, causas e referências aos resultados ou registros de bloqueio, cobertura dos objetos e alcance das relações separados. Ordem restrita aos avaliáveis é identificada como parcial, nunca como ordem completa do conjunto. Objeto não avaliável não é descartado. Entrada sem resultado remete à etapa impedida, sem ResultadoEstruturado fictício; falha operacional não vira dado ausente (RQ-RES-10/11).

**CAP-TMP-01 — Mudança temporal.** Entradas: valores do indicador por unidade em períodos p1 < p2, ou pares de intervalos. Saída por unidade (DA-14): variação absoluta v2 − v1; variação percentual (v2 − v1) / v1 × 100 quando v1 ≠ 0; direção AUMENTO se v2 > v1, REDUCAO se v2 < v1 e SEM_MUDANCA se v2 = v1, por igualdade exata e sem tolerância. Com v1 = 0, direção e variação absoluta são calculadas normalmente e a variação percentual é NAO_AVALIAVEL por BASE_ZERO (0 → 5: AUMENTO e +5; 0 → 0: SEM_MUDANCA e 0; 5 → 0: REDUCAO, −5 e −100%). Não se adicionam constantes ou pseudocontagens. A comparação entre intervalos informa a mudança de cada intervalo e a diferença entre elas, rotulada como comparação entre intervalos, sem qualificação de aceleração [C §4.3.9]. Pré-condição: significado longitudinal territorial autorizado no escopo, com aplicação determinística e exceções conforme CFG-TER, além de categoria, definição, método e demais significados compatíveis entre períodos. Significado necessário ausente gera BLQ-SIG com pendência; incompatibilidade estabelecida gera BLQ-MET quando global ou INCOMPARABILIDADE por unidade quando contratualmente aplicável; preservar as unidades independentes. Para agregados, verificam-se também o suporte efetivo e a compatibilidade metodológica de CAP-AGR-01 (F-05b): conjuntos efetivos diferentes ou componente metodológico divergente tornam a mudança NAO_AVALIAVEL (INCOMPARABILIDADE), preservando os valores isolados; se nenhum elemento puder ser avaliado, RQ-CAP-08 preserva a classe causal: incompatibilidade metodológica gera BLQ-MET, mantendo INCOMPARABILIDADE; não BLQ-DAD por mera ausência de avaliáveis. Proibido: afirmar tendência; criar agregados temporais sintéticos (RQ-ESC-12).

**CAP-TEN-01 — Tendência.** Método (DA-15), sobre a posição temporal numérica do PERIODO (seção 5.2):

1. Pré-condições da etapa: semântica temporal do PERIODO estabelecida (senão BLQ-SIG); a base contém ao menos quatro períodos distintos válidos para o indicador (senão BLQ-MET com motivo SERIE_INSUFICIENTE, Caso 9).
2. Por unidade, o significado longitudinal territorial e as exceções seguem CFG-TER; semântica necessária ausente segue RQ-DAD-05. Usam-se as observações válidas e comparáveis, sem imputação de períodos ausentes e com o tempo efetivamente transcorrido entre elas. Menos de quatro observações: NAO_AVALIAVEL (SERIE_INSUFICIENTE). Quebra de comparabilidade dentro da série solicitada, inclusive composição efetiva ou componente metodológico diferente de agregados segundo CAP-AGR-01 (F-05b): NAO_AVALIAVEL (INCOMPARABILIDADE); a análise de um trecho comparável só ocorre como alternativa distinta escolhida pelo usuário. Exceção local não afeta unidades independentes; ausência total de avaliáveis segue a causa normativa em RQ-CAP-08, sem converter incompatibilidade metodológica em dado ausente.
3. Velocidades: v_i = (y_(i+1) − y_i) / (t_(i+1) − t_i), variação absoluta do indicador por unidade de tempo, em precisão integral; não se usa variação percentual.
4. Todas as variações nulas: SEM_CLASSIFICACAO (SERIE_ESTAVEL). Variações positivas e negativas na mesma série: SEM_CLASSIFICACAO (MUDANCA_DE_DIRECAO).
5. Família de crescimento — todas as velocidades ≥ 0 e ao menos uma > 0. Com alguma velocidade igual a zero: CRESCIMENTO. Com todas > 0: não decrescentes com pelo menos um aumento estrito, CRESCIMENTO_ACELERADO; não crescentes com pelo menos uma redução estrita, CRESCIMENTO_DESACELERADO; constantes ou sem monotonicidade, CRESCIMENTO.
6. Família de declínio — todas as velocidades ≤ 0 e ao menos uma < 0. Com alguma velocidade igual a zero: DECLINIO. Com todas < 0, sobre as magnitudes |v_i|: não decrescentes com pelo menos um aumento estrito, DECLINIO_ACELERADO; não crescentes com pelo menos uma redução estrita, DECLINIO_DESACELERADO; constantes ou sem monotonicidade, DECLINIO.

Saída: observações usadas, velocidades, classe com o rótulo de DA-15, motivo de SEM_CLASSIFICACAO, avaliabilidade e versão do método. A filtragem por direção abrange as três classes da família. Proibido: imputação; classificação linguística pelo LLM; tratar SEM_CLASSIFICACAO como falta de dados [C §4.3.10] (Casos 9 e 10; AT-53).

**CAP-ROT-01 — Rotatividade e permanência da coorte inicial.** Família FAM-08; natureza determinística; não substitui CAP-TMP-01 nem CAP-TEN-01. Objetivo: medir, entre dois períodos definidos, a permanência e a saída das mesmas pessoas que compunham a coorte inicial de cada unidade analítica. O indivíduo é apenas insumo protegido do processamento longitudinal; a saída é exclusivamente agregada ou territorial.

Entradas e parâmetros: base individualizada DISPONIVEL; período inicial t0 e período final t1, PARAMETRIZAVEL_PELO_USUARIO e resolvidos por RQ-GOV-14 quando inequívocos, com t1 posterior a t0 (t1 igual ou anterior a t0: BLQ-INF); categoria ou conjunto categorial e território ou universo, quando aplicáveis; identidade de deduplicação suficiente para reconhecer a mesma pessoa entre t0 e t1 no universo solicitado (identidade longitudinal, RQ-DAD-35). Cada execução usa exatamente dois pontos analíticos; solicitação com múltiplos pares compõe execuções independentes, desde que cada par seja explicitamente definido ou inequivocamente resolvido pelo estado autorizado.

Método (CFG-MET), por unidade analítica solicitada: C0 é o conjunto de pessoas distintas presentes na unidade em t0 e C1, o conjunto de pessoas distintas presentes em t1, após deduplicação, pela identidade autorizada, de registros repetidos da mesma pessoa no mesmo território, categoria e período; P = C0 ∩ C1 e N_permanentes = |P|; S = C0 \ C1 e N_saidas = |S|; N0 = |C0|. ROTATIVIDADE_COORTE_INICIAL = (N_saidas / N0) × 100; PERMANENCIA_COORTE_INICIAL = (N_permanentes / N0) × 100; quando avaliáveis, as duas taxas somam 100%. Somente pessoas de C0 compõem o denominador; pessoas presentes apenas em t1 não o integram e não alteram as taxas. Pessoa presente em t0, ausente em período intermediário e presente em t1 é permanente nesta capacidade, que compara apenas os dois pontos definidos. Cálculo em precisão integral (RQ-CAP-03).

Identidade e privacidade: a capacidade só é avaliável quando a identidade autorizada permite reconhecer a mesma pessoa entre t0 e t1 no universo solicitado. O identificador permanece protegido, é usado pelo motor apenas para deduplicação e correspondência longitudinal e não é enviado ao LLM nem aparece em eventos, resultados, tabelas, gráficos, mapas, relatórios ou exportações; a saída referencia a identidade somente por metadado ou âncora protegida (RQ-PRV-10). Base sem identidade individual autorizada: BLQ-MET. Registro da unidade, em t0 ou em t1, sem identidade suficiente para determinar a composição da coorte ou a permanência de seus membros torna a unidade NAO_AVALIAVEL (DEPENDENCIA_NAO_AVALIAVEL, detalhe IDENTIDADE_LONGITUDINAL_INSUFICIENTE), sem exclusão silenciosa de registros nem presunção de pessoas distintas. Premissa do usuário de ausência de sobreposição não substitui a identidade longitudinal.

Ausência e coorte vazia: unidade do universo sem registro observado em t0 ou em t1 é NAO_AVALIAVEL (SEM_REGISTRO_OBSERVADO), salvo metadado de exaustividade que estabeleça a ausência de pessoas no período para a unidade; a falta de registros em t1 nunca é convertida em saída de toda a coorte, nem a falta em t0 em coorte vazia (INV-04). Período t0 ou t1 inexistente na base: BLQ-DAD. Com N0 = 0 estabelecido, registram-se N_saidas = 0 e N_permanentes = 0, e as duas taxas são NAO_AVALIAVEL (DENOMINADOR_ZERO); 0% nunca é apresentado como taxa. A avaliabilidade da unidade refere-se às taxas; contagens determinadas são registradas como componentes.

Agregação: CAP-ROT-01 NÃO admite agregado parcial de coorte. Taxas de componentes não são somadas nem promediadas. Taxa de conjunto territorial ou categorial é calculada sobre a coorte construída na união autorizada dos registros subjacentes, com deduplicação e identidade longitudinal válidas no domínio da união, de modo que a mesma pessoa presente em dois componentes conte uma única vez. Se a identidade não for válida nesse domínio, ou se qualquer componente necessário ao conjunto solicitado for NAO_AVALIAVEL, a taxa do conjunto é NAO_AVALIAVEL. Quando a causa for identidade, registra-se DEPENDENCIA_NAO_AVALIAVEL com detalhe IDENTIDADE_LONGITUDINAL_INSUFICIENTE; outras causas preservam seus motivos próprios, vinculados aos componentes afetados, sem substituição genérica por motivo de identidade. Componentes individuais avaliáveis podem ser apresentados separadamente, identificados como tais. Componentes não avaliáveis não são silenciosamente removidos, o conjunto não é redefinido apenas para os avaliáveis e o resultado dos componentes restantes não pode ser apresentado como taxa do conjunto originalmente solicitado. Esta regra é exclusiva de CAP-ROT-01 e não altera o agregado parcial autorizado em CAP-AGR-01.

Saída estruturada mínima, por unidade analítica: período inicial; período final; N0; N_permanentes; N_saidas; ROTATIVIDADE_COORTE_INICIAL em percentual; PERMANENCIA_COORTE_INICIAL em percentual; avaliabilidade; motivo e detalhe, quando aplicáveis; identidade de deduplicação referenciada apenas por metadado ou âncora protegida; método e versão; cobertura; limitações (RQ-RES-06); contexto de consistência. Para conjunto solicitado, preservam-se sua composição original, a avaliabilidade do conjunto e os componentes não avaliáveis com seus motivos próprios; taxas individuais separadas mantêm o objeto a que pertencem. Desfecho segundo RQ-CAP-08.

Síntese: somente valores estruturados da capacidade, com o qualificador "da coorte inicial" (RQ-RES-11, V-15). Exemplo válido: "Entre os 10 trabalhadores presentes no período inicial, 3 não estavam presentes no período final, correspondendo a uma rotatividade da coorte inicial de 30%. Os outros 7 estavam presentes nos dois períodos, correspondendo a 70% de permanência." Em inglês, os termos são initial-cohort attrition e initial-cohort retention (CFG-VOC). Se o conjunto não for avaliável, a síntese informa essa condição e não apresenta a taxa dos componentes restantes como taxa do conjunto.

Representação: tabela; gráfico de barras; comparação estruturada; mapa territorial, quando houver geometria autorizada e o resultado estiver territorializado; painel simples; relatório HTML ou PDF; exportação CSV; síntese ancorada. A capacidade não produz série temporal e não tem representação em gráfico de linhas; nenhuma representação expõe indivíduos. A apresentação de componentes individuais avaliáveis mantém separados seus rótulos e a condição NAO_AVALIAVEL do conjunto originalmente solicitado, sem apresentar agregado parcial de coorte.

Compatibilidade: resultados podem ser comparados por CAP-CMP-01, inclusive entre execuções de pares de períodos distintos quando o par for a dimensão deliberadamente comparada (RQ-ORQ-13), e podem ser insumo das capacidades cujos contratos admitam valores por unidade; não constituem série para CAP-TMP-01 ou CAP-TEN-01, e sua agregação segue exclusivamente a regra acima, não CAP-AGR-01 (seção 8.6).

Não abrange: causa ou motivo da saída; novas entradas como componente da taxa; turnover baseado em média de estoque; duração do vínculo; tempo até a saída; sobrevivência; hazard; primeira saída; número de episódios de saída; reentrada como evento próprio; rotatividade mensal acumulada; projeção de rotatividade; interrupções intermediárias. Esses pedidos seguem a seção 8.6. Proibido: expor identificadores ou registros individuais; calcular taxa de conjunto pela média das taxas dos componentes; imputar presença ou ausência; tratar falta de registro como saída. Testes mínimos: ROT-AT-01 a ROT-AT-09 (seção 20.7).

Granularidade semântica de CAP-ROT-01: um objetivo de calcular rotatividade para A, B e A+B pode constituir um entregável com três unidades avaliadas; A válida e B/A+B não avaliáveis podem produzir RES-LIM e ATENDIDO segundo RQ-CAP-08 e RQ-RES-04. Isso não calcula parcialmente a coorte de A+B: a união permanece não avaliável quando qualquer componente necessário impedir seu cálculo. Relatórios autônomos explicitamente pedidos podem constituir entregáveis distintos. A divisão em uma ou várias etapas preserva identidade semântica, conteúdo, avaliabilidade e estados (RQ-GOV-28, RQ-ORQ-01).

**CAP-REF-01 — Referências territoriais.** Entradas: lista explícita do usuário, fonte autorizada ou conjunto produzido por critério autorizado aplicado aos dados (resultado de CAP-SUB-01); CFG-REF é deliberadamente vazio nesta versão (seção 4.4.8), e sem nenhuma dessas origens cria-se pendência PARAMETRO_FALTANTE. O LLM não escolhe referência com base em conhecimento próprio. Saída: conjunto de referência, forma de definição e origem. Proibido: atribuir caráter normativo à referência; decidir o sentido de "referência" quando ambíguo (AMB-02) [C §4.3.11] (DA-17). A indicação de referência não cria operação comparativa; registrar seu papel contextual e aplicar CFG-VOC/CAP-CMP-01 somente quando a intenção correspondente estiver estabelecida, esclarecendo ambiguidade material uma vez.

**CAP-ESP-01 — Distância.** Distância geodésica direta, em quilômetros, calculada no elipsoide do referencial geodésico estabelecido por RQ-DAD-26, pela solução do problema geodésico inverso com o algoritmo de Karney, registrado e versionado em CFG-MET (seção 4.4.5), em precisão integral (DA-17). Coordenadas conforme RQ-DAD-25; sem coordenadas válidas, o elemento é NAO_AVALIAVEL (SEM_INFORMACAO_ESPACIAL ou COORDENADA_INVALIDA). Referencial informado DEVE pertencer ao conjunto suportado em CFG-MET; caso contrário, BLQ-MET com METODO_NAO_INCORPORADO, sem transformação, aproximação ou substituição, preservando o uso não espacial da base. Sem referencial estabelecido, a etapa aguarda a pendência REFERENCIAL_GEODESICO; referenciais diferentes sem transformação autorizada geram BLQ-MET (RQ-DAD-27). Limitação obrigatória DISTANCIA_GEODESICA_DIRETA, com o texto de TPL-11 [C §4.3.12]. Canonicalizar exclusivamente os aliases governados de CFG-MET para SIRGAS2000; elipsoide GRS80, a = 6378137 m, 1/f = 298.257222101, f = 1 / 298.257222101. Nenhuma inferência EPSG, CRS default ou transformação é autorizada.

**CAP-ESP-02 — Referência mais próxima.** Para cada unidade-alvo, calcula-se a distância a cada referência autorizada por CAP-REF-01, com avaliabilidade e motivo por par. Empates preservam todas as referências empatadas (DA-17). A saída distingue dois campos, ambos com referências selecionadas e distância: `minimo_completo`, a referência mais próxima do conjunto completo, e `minimo_avaliaveis`, a mais próxima entre as referências avaliáveis. No método incorporado, afirmar o primeiro exige conjunto não vazio e todas as distâncias necessárias avaliáveis para aquela unidade. Se alguma referência não puder ser avaliada, `minimo_completo` é NAO_AVALIAVEL (DEPENDENCIA_NAO_AVALIAVEL); as distâncias calculáveis e `minimo_avaliaveis` podem ser apresentados com rótulo "entre as referências avaliáveis", COBERTURA_PARCIAL e identificação das referências não avaliáveis e motivos. O segundo nunca substitui silenciosamente o primeiro, e seu qualificador de alcance é obrigatório (RQ-RES-11). Não há método de inferência por limites: ainda que as distâncias avaliáveis permitam delimitar o valor do mínimo completo, operações que dependem de `minimo_completo` não avaliável permanecem NAO_AVALIAVEL (F-09, não incorporada).

Com conjunto não vazio e nenhuma referência avaliável, ambos os mínimos são NAO_AVALIAVEL (DEPENDENCIA_NAO_AVALIAVEL, com os motivos espaciais dos pares). Com conjunto de referências vazio, ambos são NAO_AVALIAVEL (DEPENDENCIA_NAO_AVALIAVEL, detalhe CONJUNTO_REFERENCIAS_VAZIO); isso não esvazia o universo-alvo e não produz distância zero, ausência da unidade ou resposta negativa. Sem nenhum elemento avaliável, aplica-se RQ-CAP-08, preservando a comunicação dos motivos. Cobertura é registrada por unidade-alvo em `cobertura_referencias`; a menor distância entre A = 100 km, B = 150 km e C não avaliável é 100 km apenas entre as avaliáveis.

Filtros, faixas, ordenações, seleções, comparações e demais composições que peçam distância à referência mais próxima usam `minimo_completo`; sua não avaliabilidade propaga-se segundo os contratos e a lógica trivalente. Usar `minimo_avaliaveis` como atributo analítico exige pedido ou aceite explícito dessa alternativa, com escopo e cobertura preservados em todas as dependentes. É escolha do alcance do resultado, não novo algoritmo de distância. Mesma limitação geodésica de CAP-ESP-01 (AV-06).

**CAP-ESP-03 — Faixas de distância.** Faixas fornecidas pelo usuário ou por método autorizado, com a convenção [a, b) e o último intervalo fechado de CAP-DIS-03; mesma limitação de CAP-ESP-01; se a entrada for referência mais próxima, o campo e a cobertura obedecem a CAP-ESP-02 (DA-12, DA-17).

**CAP-SUB-01 — Subconjunto por critério.** Critérios atômicos sobre atributos autorizados, caminhos de resultados estruturados existentes ou RefSaidaEsperada com dependência efetiva encerrada sem resultado, com operadores numéricos <, ≤, >, ≥, =, ≠, operadores categóricos = e ≠, pertença a lista e pertença a classe produzida por capacidade. Vocabulário de operadores de critério de CFG-VOC (seção 4.4.9), inclusive as variantes sem acento ali registradas: "abaixo de", "menos de", "inferior a", "below", "less than" → <; "até", "no máximo", "at most" → ≤; "acima de", "mais de", "superior a", "above", "more than", "greater than" → >; "a partir de", "no mínimo", "at least" → ≥. O operador adotado é sempre explicitado; expressão fora do vocabulário gera pendência. O valor do critério é comparado após conversão exata de unidade e escala; valor sem unidade segue a regra de ContextoDeMedida de CAP-CMP-01: exatamente um contexto determinístico do atributo comparado é adotado e explicitado; nenhum gera PARAMETRO_FALTANTE (BLQ-INF); mais de um gera pendência AMBIGUIDADE_MATERIAL. As comparações usam precisão integral (DA-20).

Critérios compostos (DA-19), com E, OU e NÃO em lógica de três estados: E resulta ATENDE se todos atendem, NAO_ATENDE se algum não atende e NAO_AVALIAVEL nos demais casos; OU resulta ATENDE se algum atende, NAO_ATENDE se todos não atendem e NAO_AVALIAVEL nos demais casos; NÃO inverte ATENDE e NAO_ATENDE e mantém NAO_AVALIAVEL. O LLM apenas estrutura os critérios; a avaliação é do motor. Critérios sucessivos sobre atributos equivalem à conjunção E sobre o universo de origem, e o resultado independe da ordem; universo definido por seleção por posição ou por lista restringe as etapas seguintes.

Complemento: é o conjunto NAO_ATENDE, nunca inclui NAO_AVALIAVEL e preserva a classe de origem de cada membro, de modo que unidades SEM_CLASSIFICACAO não sejam apresentadas como de outra direção (Caso 18). Critério normativo do usuário (RQ-GOV-31): unidades que atendem recebem a classificação definida, identificada como critério do usuário; as que não atendem não recebem classificação complementar (DA-21). Desfecho RES-VAZ quando há avaliáveis e o conjunto ATENDE é vazio. Critério sobre referência mais próxima respeita o alcance e a avaliabilidade dos campos de CAP-ESP-02. Proibido: expressões analíticas livres fora do contrato e simulação de operação intermediária não executada. Essa proibição não impede representar ausência definitiva de saída por RefSaidaEsperada conforme a avaliabilidade abaixo, nem bloqueia linguagem funcional não pessoal antes da interpretação [C §4.3.13].

Avaliabilidade de CAP-SUB-01: preservar os três estados por elemento e por nó da árvore autorizada. Composto indeterminado por operando necessário NAO_AVALIAVEL recebe DEPENDENCIA_NAO_AVALIAVEL; causas específicas e âncoras permanecem nos operandos. Múltiplas causas são todas preservadas, sem prioridade arbitrária. Composto ATENDE ou NAO_ATENDE não recebe motivo de não avaliabilidade apenas por conter operando não avaliável. Conservar avaliações efetivamente disponíveis mesmo quando outro operando seja decisivo; isso não autoriza executar dependência bloqueada nem criar operação intermediária. Sem elemento avaliável, aplicar RQ-CAP-08 e conservar verificações/avaliações realizadas nos registros de etapa, sem resultado analítico fictício (RQ-RES-01). D27: predecessor efetivamente encerrado sem ResultadoEstruturado produz folha NAO_AVALIAVEL, motivo DEPENDENCIA_NAO_AVALIAVEL e CausaOrigem ligada à etapa/unidade/evento, com desfecho e motivo próprios, inclusive BLQ-MET/METODO_NAO_INCORPORADO quando aplicável. RefSaidaEsperada referencia a saída que não existe, sem fabricar resultado. Gate 9 admite avaliar a árvore completa; dependência ainda pendente/resolúvel não é antecipada como definitivamente ausente. ATENDE OU NAO_AVALIAVEL = ATENDE; NAO_ATENDE E NAO_AVALIAVEL = NAO_ATENDE; ATENDE E NAO_AVALIAVEL = NAO_AVALIAVEL. Aplicar RQ-CAP-08 somente depois da avaliação, preservando causas e a árvore em etapa quando nenhum elemento for avaliável.

Saída de CAP-SUB-01: para cada elemento, árvore com raiz e vínculos entre nós, condição, operador, atributo ou caminho de resultado, parâmetros, CondicaoCriterio, motivos e âncoras; conjuntos ATENDE, NAO_ATENDE e NAO_AVALIAVEL permanecem distintos. A árvore integra o conteúdo imutável e verificável de ResultadoEstruturado (RQ-RES-10). Representações, sínteses e exportações conservam vínculos, estados e causas, podendo usar tabela equivalente; o LLM não reconstrói a avaliação. Explicação de dependência lógica utiliza esses registros e CFG-DOC sob RQ-SIN-10, sem causalidade sobre o fenômeno.

**CAP-SUB-02 — Ordenação.** Parâmetros PARAMETRIZAVEL_PELO_USUARIO: atributo ou resultado autorizado e direção. Valores iguais não são desempatados artificialmente e compartilham posição; os rótulos seguem a sequência 1, 2, 2, 4, em que a posição seguinte a um empate soma o número de empatados. Não avaliáveis ficam em lista separada, sem posição; a ordenação por referência mais próxima preserva o campo completo ou entre avaliáveis autorizado em CAP-ESP-02 (DA-18).

**CAP-SUB-03 — Seleção por posição.** Parâmetro PARAMETRIZAVEL_PELO_USUARIO: N. Seleciona as N primeiras unidades da ordenação e todas as empatadas com a unidade da posição N; se o número efetivo ultrapassar N, informa-o com a limitação EMPATE_NO_CORTE. Exemplo: "top 5" com três unidades empatadas na 5ª posição resulta em 7 unidades. Se o usuário exigir exatamente N, é necessária regra de desempate autorizada (nenhuma nesta versão, CFG-MET) ou nova decisão do usuário (pendência EMPATE_NO_CORTE) (DA-18). Não avaliáveis não são selecionados e são listados.

**CAP-REP-01 a CAP-REP-04 — Representações.** Tabela; gráfico de barras, gráfico de linhas e série temporal; mapa; painel simples. Entradas: resultados APRESENTAVEL. Transformações e regras: Parte 13 (DA-23).

**CAP-REP-05 — Relatório consolidado HTML e exportação PDF.** Conteúdo: componentes ou resultados pedidos, representações, síntese validada ou apresentação estruturada (modo degradado), parâmetros com origem, interpretação adotada, limitações analíticas, procedência, pendências e rótulo de componentes históricos; o PDF reproduz o relatório. Sem identificadores e sem operação analítica nova (RQ-REP-12) (DA-23, DA-24).

**CAP-REP-06 — Exportação tabular CSV.** Conteúdo: resultados tabulares em precisão integral, com indicador, unidade de contagem e escala no cabeçalho e colunas de avaliabilidade e motivo; sem identificadores e sem arredondamento de apresentação (RQ-REP-12) (DA-20, DA-23).

**CAP-SIN-01 — Síntese analítica.** Executada por C-12 segundo a Parte 14.

### 8.5. Funções baseadas em LLM

| Função | Entrada | Saída | Restrições | Validação | Falha |
|---|---|---|---|---|---|
| FN-INT-01 Leitura mínima | Mensagem sanitizada, com placeholders (RQ-DAD-39), e contexto (RQ-FLX-05) | LeituraMinima, incluindo proposta de dados explícitos quando houver | Não decide pertinência nem pertença; não produz fatos; estrutura apenas conteúdo fornecido pelo usuário; não decide se expressão nominal designa pessoa ou entidade não pessoal (RQ-DAD-38); propõe tipo de dado conversacional e associações candidatas (RQ-DAD-40, RQ-DAD-41) A entrada já deve ter sido protegida pela triagem estrutural de RQ-DAD-38; conteúdo nominal sem evidência positiva de papel não pessoal chega somente como placeholder (RQ-DAD-20); reconhecer entidade ou delimitar trecho incerto nunca é delegado ao LLM para liberar dados em claro. | C-04: FAM/EXC válidos, âncoras, funções coexistentes e validação de dados de RQ-DAD-31 e RQ-DAD-41 | Até 2 regenerações; persistindo, pendência; indisponibilidade: Parte 16 |
| FN-INT-02 Interpretação operacional | Mensagem, LeituraMinima, contexto, contratos | InterpretacaoOperacional | Valores só com âncora; listar leituras concorrentes como InterpretacaoAlternativa estruturada, sem redigir seus rótulos; propor ação de linha e natureza de alterações; não propor fato ausente (P-05); correspondência de categorias só com aliases existentes, sem criar equivalências (RQ-CFG-11) Registra identidade semântica dos entregáveis, relações pretendidas, operandos, alcance entre objetos/contra referência e âncoras da intenção; comparação, critério e percentual não são intercambiáveis. A proposta é validada por RQ-GOV-16/28, sem derivar entregáveis da decomposição em etapas. | RQ-GOV-01 e RQ-GOV-13 a 18 | Até 2 regenerações; pendência |
| FN-INT-03 Redação de perguntas | PerguntaEstruturada de C-04 e formas CFG-DOC | Seleção de formas/variáveis estruturadas; interpolação por C-02/C-11 | Mesma ordem TPL-04; motivo opcional por UsoDocumental; opções e leituras somente com rótulos governados de CFG-OPC; sem rótulo criado, tradução/paráfrase metodológica livre, fatos ou opções adicionais | V-16, tipos, fontes, âncoras, opções exatamente autorizadas e rótulos governados | TPL-04 determinístico com mesmos elementos e ordem |
| FN-INT-04 Sugestões | Resultados, matriz de aplicabilidade, catálogo | Sugestões estruturadas (capacidade, objeto, referência de suporte) | Só capacidades ATIVA e possibilidades suportadas pela matriz; nenhuma execução | V-10 | Omitir sugestões |
| FN-ORQ-01 Proposta de plano | Interpretação validada e contratos | PlanoComposicao proposto | Só capacidades do catálogo; nenhum parâmetro novo O plano preserva entregáveis semânticos validados, identifica dependências efetivas e admite partes independentes determinadas durante AGUARDANDO_USUARIO, sem autorizar pendentes (RQ-ORQ-01). | Seção 9.1 | Até 2 regenerações; OPR-FAL |
| FN-META-01 Respostas sobre o agente | Pergunta, CFG, registros de C-13 | Segmentos com proposições/versões/formas autorizadas de CFG-DOC e âncoras concretas pertinentes | Nenhum fato de domínio; seleciona e organiza texto canônico ou formas autorizadas, sem paráfrase substantivamente livre | C-04: V-16, RQ-SIN-10 | RQ-SIN-05 e fallback TPL-12, inclusive bloco metodológico opcional; sem proposição pertinente, DOCUMENTACAO_INSUFICIENTE |

### 8.6. Ações admissíveis sem capacidade concreta

| Pedido | Família | Desfecho |
|---|---|---|
| Soma, média, acumulado ou outro agregado temporal | FAM-08 | ADM-SC NAO_INCORPORADA (P-21) |
| Indicador sem definição em CFG-IND | FAM-02 | ADM-SC NAO_INCORPORADA [C §4.3.5, §11.5] |
| Método ou fórmula proposta pelo usuário | Família correspondente | ADM-SC METODO_NAO_INCORPORADO, referência EXC-08 (P-04) |
| Posição percentual numérica de uma unidade | FAM-07 | ADM-SC METODO_NAO_INCORPORADO (DA-11) |
| Imputação, estimativa ou outro tratamento de valores ausentes | Família correspondente | ADM-SC METODO_NAO_INCORPORADO (DA-10) |
| Conversão arbitrária entre unidades de contagem | FAM-02 | ADM-SC METODO_NAO_INCORPORADO; não abrange contagem de pessoas distintas por identidade autorizada em registros de vínculos (RQ-DAD-35, DA-09) |
| Transformação entre referenciais geodésicos | FAM-10 | ADM-SC METODO_NAO_INCORPORADO (RQ-DAD-27) |
| Desempate de valores iguais | FAM-11 | Sem regra autorizada nesta versão; exigência de N exato gera pendência (DA-18) |
| Mudança temporal, tendência ou agregado temporal de taxas de CAP-ROT-01 entre pares de períodos | FAM-08 | ADM-SC METODO_NAO_INCORPORADO; a comparação entre execuções de pares explicitamente definidos segue CAP-CMP-01 (RQ-ORQ-13) |
| Medidas de rotatividade não incorporadas (novas entradas na taxa, turnover por média de estoque, duração de vínculo, tempo até a saída, sobrevivência, hazard, primeira saída, episódios de saída, reentrada como evento, rotatividade mensal acumulada, interrupções intermediárias) e motivo da saída | FAM-08 | ADM-SC METODO_NAO_INCORPORADO; causa da saída segue EXC-03 (ADM-FE); projeção de rotatividade, ADM-FE (Caso 4) |

---

## Parte 9 — Orquestração e composição

### 9.1. Validação do plano

- **RQ-ORQ-01** — C-05 DEVE validar o plano proposto por FN-ORQ-01 quanto a: (a) capacidades existentes e ATIVA; (b) compatibilidade de tipos de entrada e saída segundo os contratos; (c) ausência de ciclos; (d) cada entregável vigente da interpretação e da versão de EscopoSolicitacao ligado a ao menos uma etapa necessária, e cada etapa ativa ancestral de ao menos um entregável vigente; etapas sem consumidor após retirada seguem RQ-FLX-02; (e) parâmetros idênticos aos da interpretação ancorada ou classificados como OPERACIONAL_AUTORIZADA no contrato; (f) inexistência de entregável ausente da interpretação; (g) ordem de encadeamento de universos igual à da interpretação. A rejeição registra os motivos e provoca até 2 regenerações (DA-26); esgotadas estas, a solicitação recebe OPR-FAL comunicado por C-02 [C §4.4, §5.4]. A validação inclui preservação da identidade semântica dos entregáveis e relações autorizadas, com dependências por operandos/partes efetivamente necessários. Uma ou várias etapas não alteram conteúdo, avaliabilidade, StatusEntregavel, StatusSolicitacao ou terminalidade. Partes determinadas podem ser planejadas durante AGUARDANDO_USUARIO; partes não resolvidas permanecem identificadas, sem parâmetros inventados ou autorização tácita (RQ-GOV-27/29). Plano referencia EscopoSolicitacao vigente e consumidores efetivos por unidade independente. Retirada cancela somente trabalho sem consumidores; escopo vazio aplica D17-A, sem cancelar a solicitação. Conservar a identidade semântica de RQ-GOV-28 e o orçamento por unidade de RQ-ORQ-14. [T-GOV][T-LLM: M-06]
- **RQ-ORQ-02** — Todo plano ANALITICO é proposto por FN-ORQ-01 e validado por C-05; não há planos analíticos derivados de controles de interface (P-18). Ingestão e exame automático seguem a via HABILITADORA de RQ-DAD-34, sem plano analítico nem dependência de FN-ORQ-01. [T-GOV]
- **RQ-ORQ-03** — O plano e seu resumo DEVEM ser registrados e vinculados à Autorização. [T-DET]

### 9.2. Execução e fidelidade

- **RQ-ORQ-04** — As etapas são executadas em ordem topológica; etapas independentes PODEM ser paralelas. Para cada etapa: verificação pré-execução, cálculo da chave, busca de reuso, execução por C-06, registro em C-07, eventos e atualização de status. O ciclo das etapas independentes ocorre também durante AGUARDANDO_USUARIO, sem exigir transição agregada prévia; reuso, registro e apresentação seguem os mesmos controles. Resolução de pendência retoma somente o ramo e seus descendentes efetivos, preservando etapas independentes concluídas ou em andamento (RQ-FLX-04). [T-DET]
- **RQ-ORQ-05** — C-05 DEVE executar somente etapas contidas na Autorização, com os parâmetros autorizados. Qualquer divergência interrompe a execução com OPR-FAL (motivo FIDELIDADE). A sequência executada é registrada para comparação com a planejada [C §5.10, §10.3]. A autorização deve estar ativa para as etapas e o contexto aplicáveis; StatusSolicitacao não substitui essa verificação nem constitui exigência adicional de AUTORIZADA/EM_EXECUCAO durante espera agregada. [T-GOV][M-09]

### 9.3. Reuso

- **RQ-ORQ-06** — A chave de execução DEVE ser o resumo canônico de: capacidade e versão; método e versão; parâmetros; resumos das entradas; versões de bases e mapeamentos; definição e membros do universo; versões dos itens CFG relevantes. A substituição de uma nova execução por resultado existente exige a mesma chave, resultado VALIDO e APRESENTAVEL e vigência/uso histórico conforme RQ-ORQ-07. Isso difere de utilizar resultados existentes como entradas de uma comparação: nesse caso, aplica-se RQ-ORQ-13 sem exigir chaves idênticas entre os objetos comparados nem recalculá-los para esse fim. O reuso cria vínculo na linha corrente, gera EV-REUSO e marca a etapa como REUTILIZADA; no retorno exato a recorte anterior, o vínculo do resultado deslocado é restabelecido como VIGENTE, sem duplicação (RQ-LIN-20) [C §5.4, §7.9] (F-03). Elegibilidade de contexto/reuso exige base ainda autorizada e sessão ativa; excluir todos os derivados de entrada recusada, inclusive histórico reconstruído (RQ-DAD-42), e descartar retornos após encerramento (RQ-FLX-17). [T-DET][T-E2E: AT-77]
- **RQ-ORQ-07** — Resultado INVALIDADO nunca é reutilizado (INV-08). Resultado com vínculo NAO_VIGENTE de caráter histórico (SUBSTITUICAO_DE_ESTADO) só é usado mediante pedido explícito de comparação que identifique o resultado histórico ou a versão, inclusive referência contextual inequívoca como "compare os dois"; resultado deslocado (DESLOCAMENTO_DE_FOCO) é usado como componente contemporâneo ou entrada de comparação conforme RQ-FLX-06 e RQ-LIN-20. A diferença entre os focos comparados não invalida seus resultados de origem; não se reativam automaticamente parâmetros ou decisões fora do escopo. Elegibilidade de contexto/reuso exige base ainda autorizada e sessão ativa; excluir todos os derivados de entrada recusada, inclusive histórico reconstruído (RQ-DAD-42), e descartar retornos após encerramento (RQ-FLX-17). [T-DET][T-E2E: AT-31, AT-67, AT-77]

### 9.4. Replanejamento

- **RQ-ORQ-08** — O replanejamento é admitido quando resultados exigem adaptação dentro da mesma intenção (ex.: incluir capacidade que produza relação exigida por entregável autorizado; percurso alternativo autorizado para etapa bloqueada). Não pode alterar parâmetros substantivos, universo, método ou modo. Etapas novas passam pela validação da seção 9.1 e por nova versão da Autorização. O replanejamento é registrado com o motivo (EV-REPLANEJAMENTO). Se alterar a assinatura material, pertinência e admissibilidade são reavaliadas e o usuário é consultado [C §5.9, §6.5]. Replanejamento por retirada registra nova versão de escopo, vínculos removidos e consumidores remanescentes, sem reabrir execução terminal. Apurar estado por RQ-FLX-02, incluindo retirada total D17-A. [T-GOV]
- **RQ-ORQ-09** — Conjunto intermediário vazio não é falha quando constitui o próprio universo-alvo: etapas dependentes sobre esse universo vazio produzem RES-VAZ com CONJUNTO_VAZIO_ANTERIOR e referência à origem. Conjunto vazio usado como referência espacial não torna vazio o universo-alvo; CAP-ESP-02 rege sua não avaliabilidade. [T-DET][T-E2E: AT-68]

### 9.5. Suspensão e reautorização

- **RQ-ORQ-10** — Quando uma AlteracaoEstado (nova versão de base carregada pelo usuário, confirmação ou correção de significado, alteração de parâmetro, decisão ou substituição pelo usuário) ou a indisponibilidade operacional de capacidade afetar elemento do ContextoConsistencia de composição com etapas não terminais, C-05 DEVE identificar as etapas afetadas, direta ou transitivamente, e colocá-las em SUSPENSA; etapas não afetadas prosseguem no contexto original. A configuração não muda durante a sessão (RQ-CFG-05) [C §6.5, §7.10, Caso 21] (DA-01). [T-DET][T-E2E: AT-21]
- **RQ-ORQ-11** — A continuidade exige decisão do usuário (pendência CONTINUIDADE_DE_COMPOSICAO): (a) manter o contexto original, admitido somente se a alteração tiver sido SUBSTITUICAO_DE_ESTADO e a manutenção for compatível com a intenção; (b) reautorizar as etapas afetadas no novo contexto, recalculando também as etapas já executadas cujos resultados alimentem as seguintes; (c) cancelar. Se a alteração for CORRECAO_OU_REPUDIO de elemento do contexto original, a opção (a) não é oferecida. [T-GOV]
- **RQ-ORQ-12** — Todas as novas etapas de um entregável DEVEM executar sob o contexto de consistência fixado na autorização. Entradas já produzidas podem manter contextos de origem distintos quando RQ-ORQ-13 as admitir; esses contextos são referenciados, nunca reescritos para aparentar identidade (INV-10). [T-DET]

### 9.6. Comparação entre contextos e versões

- **RQ-ORQ-13** — Resultados de contextos distintos PODEM alimentar comparação autorizada quando forem metodologicamente compatíveis e suas diferenças forem as dimensões que a solicitação pretende comparar (categoria, período, território ou versão explicitamente indicada), ou diferenças explicitamente admitidas pelo contrato. C-04 DEVE registrar resultados e contextos de origem, diferenças, dimensões comparadas, âncoras da intenção e verificação determinística de definição do indicador, unidade de contagem, escala canônica, método/versão relevantes, significado dos dados, territorialidade e demais pré-condições, inclusive, para agregados, a compatibilidade metodológica de CAP-AGR-01 (F-05b). Diferença deliberada de categoria ou período não exige identidade integral de ContextoConsistencia; diferença de versão não autoriza misturar métodos ou significados incompatíveis. Incompatibilidade material gera BLQ-MET com as divergências, ou não avaliabilidade quando o contrato a define; aceitação genérica do usuário não a remove. As novas operações executam sob um único contexto que referencia as entradas compatíveis, sem recalcular resultados existentes apenas para igualar contextos. Comparação temporal usa CAP-TMP-01 ou CAP-TEN-01 e preserva a exigência de suporte efetivo de CAP-AGR-01. Resultados históricos válidos podem ser usados nos termos de RQ-ORQ-07; consolidação entre linhas segue RQ-DIA-05, sem transferência de decisões locais [C §4.3.7, §6.5] (AV-05). Incompatibilidade que torne todos os elementos/relações não avaliáveis continua metodológica: BLQ-MET e motivo específico INCOMPARABILIDADE, conforme RQ-CAP-08, inclusive tipos de contagem incompatíveis; não se converte em BLQ-DAD. Relações independentes compatíveis de CAP-CMP-01 permanecem avaliáveis. [T-GOV][T-E2E: AT-67, AT-69]

### 9.7. Falhas e cancelamento

- **RQ-ORQ-14** — Falha operacional DEVE ser apurada por menor unidade semântica independente de execução — elemento, relação ou operando — com identidade, StatusEtapa, tentativas, saída, causa e dependências. Etapa em lote não transmite falha de B a A/C independentes. Uma nova tentativa é permitida somente para unidade idempotente, limitada pelo mesmo orçamento de uma repetição por identidade semântica; decompor/reagrupar não multiplica esse orçamento. Esgotado, unidade FALHOU/OPR-FAL; comunicar por TPL-03 e propagar impedimento somente a consumidores efetivos, preservando CausaOrigem. Etapa com saída admissível fica CONCLUIDA, com cobertura e causas registradas; FALHOU somente quando falha impede toda a saída, BLOQUEADA para impedimento não operacional e SUSPENSA quando contrato exige recuperação. Cada elemento terminal de entregável composto registra ResultadoElemento: INTERROMPIDO quando sua própria execução começou e falhou operacionalmente; NAO_EXECUTAVEL, com DEPENDENCIA_NAO_AVALIAVEL e causa_raiz_ref, quando não pôde executar porque dependência efetiva falhou; CONCLUIDO, com resultado e avaliabilidade próprios, nos demais casos. Falha de B não contamina A e C. Estado agregado não sobrescreve estados individuais. Saídas A/C válidas permanecem utilizáveis; não confundir falha com dado ausente, insuficiência metodológica ou inexistência de capacidade. Aplicar exceção trivalente de CAP-SUB-01 antes de bloquear toda árvore. Não ampliar métodos ou relaxar completude de coorte CAP-ROT-01. Tempos limite técnicos seguem CFG-OPR; retries não renovam inatividade da sessão. [T-DET][T-E2E: AT-147–AT-151, AT-163, AT-164, AT-170]
- **RQ-ORQ-15** — Indisponibilidade de componente gera OPR-IND e segue a Parte 16. [T-E2E: AT-13, AT-14]
- **RQ-ORQ-16** — Cancelamento pelo usuário: etapas pendentes passam a CANCELADA; resultados já registrados permanecem válidos, com os papéis autorizados; a solicitação passa a CANCELADA; entregáveis vigentes não terminais passam a CANCELADO e entregáveis já concluídos preservam estado e resultado históricos; nenhuma nova execução é iniciada. Cancelamento é terminal e monotônico: retorno posterior de unidade, etapa ou chamada cancelada não reabre solicitação nem entregável, não altera CANCELADA/CANCELADO, não entra no conjunto vigente de resultados, não é reincorporado ao contexto ativo nem reenviado ao LLM e registra EV-RETORNO_TARDIO_DESCARTADO; com a sessão já encerrada, prevalecem as regras de descarte de RQ-FLX-17. Retirada de entregáveis não equivale a cancelamento explícito da solicitação: aplicar nova versão de escopo e D17-A/RQ-FLX-02; cancelamento de etapa sem consumidores não produz CANCELADA na solicitação. [T-DET][T-E2E: AT-171, AT-172]

---

## Parte 10 — Resultados analíticos estruturados

- **RQ-RES-01** — Toda execução que produza resultado analítico DEVE registrá-lo em ResultadoEstruturado. Falha de pré-condição ou ausência total de elemento/relação avaliável conforme RQ-CAP-08 não produz resultado analítico: desfecho e causas ficam registrados na etapa e no entregável. Verificações e avaliações efetivamente realizadas, inclusive árvores e motivos de CAP-SUB-01, são preservadas nesses registros, sem fabricar resultado válido nem apresentar operação não executada como concluída [C §8.2]. [T-DET]
- **RQ-RES-02** — O conteúdo é imutável e identificado por resumo; estados mutáveis ficam em registros separados (RQ-MOD-02, INV-07). [T-DET]
- **RQ-RES-03** — Os resultados de um entregável DEVEM conter todo valor, relação, seleção, ordenação e classificação que a resposta enunciará. Se faltar elemento exigido por entregável autorizado, C-05 PODE replanejar (RQ-ORQ-08); a síntese nunca o supre [C §8.2]. [T-GOV]
- **RQ-RES-04** — O desfecho do entregável semântico é o de seu resultado terminal (RQ-CAP-08) ou da condição normativa/etapa que impede seu atendimento, com origem rastreável. RES-* corresponde a ATENDIDO, inclusive RES-LIM. Bloqueio com pendência resolúvel aplicável mantém PENDENTE, assim como os descendentes que dependam da resolução; código e causa são preservados. ADM-* ou BLQ-* sem continuidade resolúvel corresponde a NAO_EXECUTAVEL; OPR-* que impeça o atendimento corresponde a INTERROMPIDO, observadas suspensão e recuperação. OPR-IND restrito à tentativa de síntese dispensável não interrompe o entregável analítico já apresentado validamente em modo degradado (RQ-DEG-04). PENDENTE também pode representar processamento em curso e não determina sozinho AGUARDANDO_USUARIO. Elementos não avaliáveis em resultado atendido não criam automaticamente pendência nem entregáveis adicionais. Estados de etapas e eventos operacionais não substituem StatusEntregavel. Retirada não é desfecho de execução: conservar o estado do entregável no histórico e excluí-lo apenas do conjunto vigente. Não atribuir NAO_EXECUTAVEL/INTERROMPIDO por retirada; terminalidade do escopo vazio segue D17-A. Falha interna de unidade não interrompe automaticamente objetivo satisfeito por resultado admissível; apurar contrato, cobertura e dependências reais (RQ-ORQ-14). Entregável composto representa cada unidade semântica independente por ResultadoElemento: INTERROMPIDO, NAO_EXECUTAVEL por dependência — com DEPENDENCIA_NAO_AVALIAVEL e causa-raiz — e CONCLUIDO permanecem distintos por elemento; falha de B não contamina A e C; o estado e o desfecho agregados derivam dos elementos segundo RQ-CAP-08; a cobertura distingue elementos válidos, falhos e não avaliáveis. CANCELADO decorre exclusivamente de cancelamento explícito da solicitação e aplica-se aos entregáveis vigentes não terminais; entregável já concluído conserva estado e resultado; retirada continua distinta de cancelamento, falha e interrupção (RQ-FLX-02, RQ-ORQ-16). [T-DET][T-E2E: AT-91, AT-99, AT-100, AT-112, AT-113, AT-115, AT-170, AT-171]
- **RQ-RES-05** — As situações de ausência DEVEM ser representadas de forma distinta [C §7.4, §8.11]: [T-DET][T-E2E: AT-08, AT-17]

| Situação | Representação |
|---|---|
| Informação não fornecida | Pendência (BLQ-INF), sem resultado |
| Dado ausente | Elemento NAO_AVALIAVEL (DADO_AUSENTE, DENOMINADOR_AUSENTE) |
| Unidade elegível sem registro | NAO_AVALIAVEL (SEM_REGISTRO_OBSERVADO), presença ELEGIVEL_SEM_REGISTRO |
| Valor zero | Valor 0 AVALIAVEL, somente se observado ou VALOR_ZERO_CODIFICADO |
| Unidade fora do universo | FORA_DO_UNIVERSO, listada em exclusões |
| Conjunto vazio por critério | RES-VAZ |
| Método executado sem classe | SEM_CLASSIFICACAO por elemento; RES-SCL quando nenhum elemento é classificado |
| Bloqueio, falha ou indisponibilidade | Desfecho BLQ-*, OPR-*, sem resultado |

- **RQ-RES-06** — Limitações DEVEM ser tipadas e classificadas por CategoriaLimitacao. São ANALITICAS, e acompanham obrigatoriamente o resultado na apresentação e na síntese, as que afetam universo, cobertura, comparabilidade, método ou interpretação: COBERTURA_PARCIAL; UNIDADES_NAO_AVALIAVEIS; UNIVERSO_OBSERVADO_NAO_EXAUSTIVO; AGREGADO_PARCIAL; SOMA_COM_POSSIVEL_DUPLA_CONTAGEM; ADITIVIDADE_POR_PREMISSA_DO_USUARIO; COMPARABILIDADE; NIVEIS_TERRITORIAIS_DIFERENTES; COBERTURA_DESIGUAL_ENTRE_PERIODOS; CATEGORIAS_NAO_COMPARAVEIS; DIFERENCA_DE_DEFINICAO; VALOR_FORNECIDO_PELO_USUARIO; VALOR_SUBSTITUIDO_PELO_USUARIO; DENOMINADOR_ALTERNATIVO; CRITERIO_NORMATIVO_DO_USUARIO; DISTANCIA_GEODESICA_DIRETA; EMPATE_NO_CORTE; CONJUNTO_VAZIO_ANTERIOR. São TECNICAS, e ficam apenas na rastreabilidade, os eventos sem efeito sobre o significado analítico, como ORIGEM_INDISPONIVEL. O termo "heterogeneidade" não é usado como limitação sem critério formal autorizado; descreve-se a condição concreta observada [C §9.8] (DA-16, DA-22, P-19). TPL-13 comunica falha técnica de materialização da entrada, sem constituir limitação metodológica nem acompanhar resultado inexistente; o evento continua técnico e o pedido preservado segue RQ-DAD-43. COBERTURA_PARCIAL identifica elementos falhos (INTERROMPIDO) separadamente de UNIDADES_NAO_AVALIAVEIS, sem converter falha em dado ausente (RQ-RES-04). [T-DET]
- **RQ-RES-07** — Um resultado só é APRESENTAVEL após o registro persistido de seu evento e dos eventos de suas dependências em C-13; antes disso é RASTREABILIDADE_PENDENTE e não é exibido como resultado analítico (INV-12) [C §5.10]. [T-DET][T-E2E: AT-30]
- **RQ-RES-08** — Resultados intermediários DEVEM ser preservados estruturados; o LLM nunca os reconstrói a partir da narrativa [C §8.8]. [T-GOV]
- **RQ-RES-09** — Reexecução com a mesma chave que produza resumo diferente DEVE gerar OPR-FAL (motivo REPRODUTIBILIDADE) e evento de investigação [C §8.10]. [T-DET]

- **RQ-RES-10** — O resultado DEVE preservar as distinções contratuais necessárias às dependentes: suporte efetivo por período e composição do denominador em agregados; cobertura e alcance completo/entre avaliáveis em referência mais próxima; territórios e categorias não avaliáveis em agregado multicategorial (F-05a); TipoContagemAgregada e fundamento da unicidade em agregados; contextos de origem e dimensões deliberadamente comparadas; em CAP-ROT-01, composição do conjunto originalmente solicitado, sua avaliabilidade e motivos dos componentes necessários, sem redefinição do conjunto nem agregado parcial de coorte. Usam-se as estruturas de 3.2 e as limitações de RQ-RES-06 (COBERTURA_PARCIAL, COMPARABILIDADE e COBERTURA_DESIGUAL_ENTRE_PERIODOS, quando aplicáveis), com condições concretas. Uma limitação não torna avaliável operação que o contrato bloqueia. Agregados isolados válidos permanecem apresentáveis mesmo quando sua mudança temporal é INCOMPARABILIDADE. CAP-CMP-01 conserva relações autorizadas, operandos, sentido, alcance e causas, distinguindo cobertura dos objetos do alcance das relações. CAP-SUB-01 conserva a árvore avaliada e os motivos por nó, ou os referencia nos registros da etapa quando não houver resultado analítico. Mapeamentos e contexto preservam a regra longitudinal territorial e exceções efetivamente utilizadas. Folha de critério cuja dependência efetiva se encerrou sem ResultadoEstruturado registra RefSaidaEsperada e CausaOrigem (etapa/unidade/evento/desfecho/motivo/detalhe), além de NAO_AVALIAVEL/DEPENDENCIA_NAO_AVALIAVEL. BLQ-MET ou outro desfecho não entra em MotivoNaoAvaliavel. Preservar árvore completa, inclusive sem resultado, em verificacoes_avaliacoes da etapa; não fabricar ResultadoEstruturado. [T-DET][T-E2E: AT-58, AT-67, AT-68, AT-69, AT-79, AT-80]
- **RQ-RES-11** — Qualificadores de alcance, cobertura e natureza fazem parte obrigatória do significado do resultado, são registrados no ResultadoEstruturado e DEVEM ser preservados em toda apresentação textual, síntese, relatório, exportação e representação derivada: alcance "entre as referências avaliáveis" de `minimo_avaliaveis`, apresentado como "mais próxima entre as referências avaliáveis" ou formulação semanticamente equivalente; agregado parcial autorizado em CAP-AGR-01, nunca apresentado como do conjunto completo e não aplicável à coorte de CAP-ROT-01; SOMA_DOS_COMPONENTES e UNIDADES_DISTINTAS por premissa do usuário; caráter histórico e resultado deslocado de outro recorte; "da coorte inicial" em CAP-ROT-01; distância geográfica direta; critério normativo do usuário; limitações ANALITICAS de RQ-RES-06. Paráfrase que elimine ou atenue o qualificador é rejeitada (V-15) (F-04). Ordem comparativa parcial explicita seu alcance entre avaliáveis; não elimina objetos pedidos nem suas causas. Explicações de critério composto conservam vínculos e motivos por nó, sem análise ou causalidade nova (CAP-CMP-01, CAP-SUB-01). [T-GOV][T-E2E: AT-78]

---

## Parte 11 — Linhas analíticas, estado, validade e vigência

### 11.1. Linhas

- **RQ-LIN-01** — A primeira solicitação ANALITICO da sessão cria uma linha; o objetivo local é registrado com âncora na manifestação do usuário. Linhas existem somente durante a sessão [C §7.6] (DA-24). [T-DET]
- **RQ-LIN-02** — Permanece-se na linha quando a solicitação for extensão, repetição, comparação ou aprofundamento do mesmo objetivo local, inclusive com mudança de período, território, categoria ou recorte. Abre-se nova linha quando surgir objetivo analítico materialmente distinto ou quando a continuidade misturar dependências incoerentes. A estrutura de linhas opera internamente, sem exigir do usuário gestão de linhas: FN-INT-02 propõe, e só se cria pendência LINHA quando houver duas ou mais opções plausíveis com efeito material sobre o diagnóstico ou sobre o escopo de decisões anteriores [C §7.6] (DA-06). [T-GOV][T-E2E: AT-11]
- **RQ-LIN-03** — A troca de linha torna a anterior INATIVA sem apagá-la. A retomada DEVE reavaliar validade e vigência de todos os elementos antes de qualquer reuso [C §7.6, §9.9]. [T-DET][T-E2E: AT-11]
- **RQ-LIN-04** — Decisões e parâmetros não se transferem entre linhas; a recuperação de valor factual originalmente associado ao objeto da sessão segue RQ-LIN-21 e não transfere decisões ou parâmetros locais [C §9.9, Caso 11]. [T-DET]
- **RQ-LIN-05** — Encerrar uma linha não apaga seus resultados historicamente válidos [C §9.10]. [T-DET]
- **RQ-LIN-06** — Linha de consolidação só é criada por pedido ou autorização explícita do usuário, com as linhas de origem identificadas; comparações exigem a verificação de compatibilidade de RQ-DIA-05 [C §7.6, §8.3]. [T-GOV]

### 11.2. Escopo de parâmetros e decisões

- **RQ-LIN-07** — Parâmetros, decisões, valores factuais, substituições, declarações e critérios permanecem vinculados ao menor escopo explicitamente indicado e aos objetos a que se referem; parâmetros analíticos (limiares, parâmetros de referência, critérios, intervalos, N, K) referem-se ao indicador e às categorias do recorte em que foram estabelecidos (Caso 11). Complemento aprovado: na ausência de escopo indicado, o elemento vale para a solicitação corrente; expressões como "nesta análise" o estendem à linha analítica; o usuário pode ampliar explicitamente o alcance. Resposta a pendência e dimensões da linha seguem RQ-LIN-19; valor factual complementar, RQ-LIN-21. A recuperação do valor factual fornecido sem linha aplicável por outra linha compatível da mesma sessão preserva o objeto e o escopo originais (RQ-LIN-21) e não é propagação. Fora dessa recuperação, nenhum elemento se propaga automaticamente para outros objetos, categorias, linhas, sessões ou usuários, nem altera a configuração global [C §7.6, Casos 3 e 11] (DA-06, P-14, F-06, F-07). [T-DET][T-E2E: AT-11, AT-82]
- **RQ-LIN-08** — Um elemento é reutilizado em solicitação posterior somente quando seu escopo a abrange e seus objetos coincidem, ou quando o usuário o referencia explicitamente, inclusive por construção elíptica que retome a solicitação anterior. Nos demais casos, o agente PODE oferecer a reutilização, sem presumi-la; pedido como "faça o mesmo para enfermeiros" não transfere parâmetro escopado a médicos (Caso 11), mas preserva as dimensões da linha ainda válidas, como o período (RQ-LIN-19) (DA-06, F-07). [T-GOV][T-E2E: AT-11, AT-82]

### 11.3. Estado

- **RQ-LIN-09** — O EstadoLinha DEVE ser versionado a cada alteração; os elementos ativos são calculados por solicitação segundo escopo, validade e vigência [C §7.8]. [T-DET]
- **RQ-LIN-10** — Alterações de território, período, categoria, parâmetro, critério, base ou linha atualizam o estado e desativam elementos incompatíveis sem apagá-los (ex.: parâmetros escopados a outra categoria ficam inativos para o novo foco); dimensões da linha não alteradas permanecem (RQ-LIN-19), e os efeitos sobre vínculos de resultados seguem RQ-LIN-20 [C §7.10]. [T-DET][T-E2E: AT-42, AT-77, AT-82]

### 11.4. Motor de validade e vigência

- **RQ-LIN-11** — Todo resultado DEVE registrar suas dependências: bases e versões, significados, definição do universo, parâmetros, métodos, itens CFG e resultados de entrada [C §7.9]. [T-DET]
- **RQ-LIN-12** — A natureza CORRECAO_OU_REPUDIO só é atribuída com âncora que declare incorreção, falta de autorização ou insustentabilidade metodológica: declaração ou correção semântica explícita do usuário, dentro do escopo permitido, ou errata em metadado autorizado. A simples substituição é SUBSTITUICAO_DE_ESTADO (Caso 12). Ambiguidade entre as duas com efeito material gera pendência NATUREZA_DE_ALTERACAO. Alteração sem dependentes é SEM_EFEITO (P-10). [T-GOV][T-E2E: AT-12]
- **RQ-LIN-13** — A propagação é transitiva e segue a tabela [C §7.7, §7.9, §8.9]: [T-DET]

| Natureza | Efeito nos dependentes |
|---|---|
| SUBSTITUICAO_DE_ESTADO | Vínculos na linha afetada passam a NAO_VIGENTE com motivo SUBSTITUICAO_DE_ESTADO e caráter histórico (RQ-LIN-20); validade preservada |
| CORRECAO_OU_REPUDIO | StatusResultado INVALIDADO em todas as linhas; vínculos NAO_VIGENTE |
| SEM_EFEITO | Nenhum |

- **RQ-LIN-14** — Universo definido por condição preserva a condição; mudança de dados que possa alterar a composição torna os dependentes NAO_VIGENTE, por SUBSTITUICAO_DE_ESTADO, até reavaliação. Universo por lista fixa preserva os membros, e seus valores seguem as próprias dependências. Se a definição do universo de origem for reconhecida como incorreta, os dependentes são invalidados [C §7.9]. [T-DET]
- **RQ-LIN-15** — Não há recálculo substantivo espontâneo. Alteração que afete resultados anteriores tem o impacto registrado e os resultados afetados identificados. Se a própria solicitação do usuário implicar claramente o recálculo (ex.: "use este novo valor e refaça a densidade"), ele é executado sem nova confirmação, com autorização normal; caso contrário, o agente informa os resultados afetados e oferece a reexecução [C §7.9, §8.9, Caso 12] (DA-08). [T-GOV][T-E2E: AT-12]
- **RQ-LIN-16** — Indisponibilidade técnica do artefato ou versão de origem não invalida o resultado: registra-se ORIGEM_INDISPONIVEL e a limitação correspondente; usos que exijam verificar a origem (recálculo, releitura da base) recebem BLQ-DEP [C §7.7]. [T-DET]
- **RQ-LIN-17** — Pendências tornadas incompatíveis pela mudança de estado passam a SEM_APLICABILIDADE; nunca são "invalidadas" e permanecem no histórico [C §7.8, §9.10]. [T-DET]
- **RQ-LIN-18** — EV-VIGENCIA e EV-INVALIDACAO DEVEM registrar a alteração causadora, o motivo de não vigência e os resultados afetados. [T-DET]
- **RQ-LIN-19** — Escopo de respostas e dimensões da linha: (a) resposta a pendência herda o escopo do parâmetro, objeto ou decisão da pendência que resolve (Pendencia.escopo_da_resposta), e a mensagem isolada que contém a resposta não reduz esse escopo; (b) pendência sobre dimensão do recorte (indicador, categoria, universo, período ou modo territorial) exigida pela análise da linha tem escopo de linha, e sua resposta torna-se dimensão da linha; pendência sobre elemento de objeto específico tem o escopo desse objeto; (c) restrição expressa do usuário prevalece (ex.: "para médicos, use 2023" vincula 2023 a médicos); (d) alterar uma dimensão do recorte não apaga as demais dimensões ainda válidas e aplicáveis: mudar apenas a categoria preserva período, território e demais dimensões da linha; (e) dimensão da linha permanece válida enquanto não for substituída ou restringida e compõe EstadoLinha.recorte_corrente; (f) valor explicitamente vinculado a objeto específico não se propaga a outro objeto; (g) parâmetro ainda válido e aplicável não é perguntado novamente sem razão material. Exemplo normativo: "Analise médicos." → "Qual período?" → "2023." → "Agora enfermeiros.": a análise de enfermeiros usa 2023; se o usuário tivesse dito "para médicos, use 2023", 2023 não seria transferido (F-07). Escopo OBJETO de campo/esquema pode anteceder linha legítima e inclui entrada/base, versão, esquema, campos, períodos, unidades e exceções. Resposta não ganha automaticamente escopo de linha futura. Retirada de entregável afeta vínculos do escopo da solicitação, não a validade global do resultado. [T-DET][T-GOV][T-E2E: AT-82]
- **RQ-LIN-20** — Vigência e caráter dos resultados na mudança de foco: (a) mudança de foco ou de recorte da linha — nova solicitação sobre outro indicador, categoria, universo, período ou modo, sem alterar os elementos de que o resultado anterior depende — torna o vínculo desse resultado NAO_VIGENTE com motivo DESLOCAMENTO_DE_FOCO, sem caráter histórico: o resultado permanece VALIDO e pode ser componente contemporâneo do diagnóstico, entrada de comparação ou resultado de outro recorte; (b) quando nova versão de base, parâmetro, decisão, significado ou condição substitui o estado de que o resultado dependia (SUBSTITUICAO_DE_ESTADO), o vínculo passa a NAO_VIGENTE com esse motivo e assume caráter histórico; havendo ambos os motivos, prevalece SUBSTITUICAO_DE_ESTADO; (c) NAO_VIGENTE não implica, por si só, caráter histórico; (d) no retorno exato a recorte anterior, C-08 restabelece o vínculo VIGENTE do resultado deslocado quando ele permanece VALIDO, sua chave de execução corresponde às condições correntes e nenhuma de suas dependências foi substituída, e o resultado é reutilizado sem reexecução nem duplicação (EV-REUSO); caso contrário, aplica-se RQ-LIN-15 (F-03). [T-DET][T-E2E: AT-42, AT-77]
- **RQ-LIN-21** — Valor factual complementar (RQ-DAD-40) fica associado ao objeto específico identificável a que se refere, com sua âncora e escopo factual originais (território, período e, quando pertinente, categoria, base ou outra dimensão que determine seu significado). Havendo solicitação analítica ou linha aplicável no momento da manifestação, a associação correspondente continua registrada: à solicitação e à linha dela, ou, sem solicitação ativa, à linha corrente aplicável. Quando não houver linha analítica aplicável nesse momento, o valor permanece associado ao objeto no estado da sessão e pode ser recuperado posteriormente por qualquer linha cuja análise seja compatível com esse objeto e com o escopo do valor. Seu uso por uma linha não o transfere para essa linha, não o torna exclusivo dela e não impede seu uso por outra linha compatível. Não expira ao final da mensagem; a âncora factual original permanece, e a aplicabilidade depende de o valor não ter sido substituído, restringido ou invalidado no escopo pertinente. O valor não se propaga quando território, período, categoria ou outra dimensão pertinente alterar seu significado; população territorial pode servir a categorias distintas do mesmo território e período quando seu escopo não for categorial, mas não a outro período. Restrições expressas são preservadas; não há persistência entre sessões (RQ-DAD-17). A recuperação do mesmo objeto não amplia critérios ou decisões locais, não altera a configuração e segue RQ-GOV-21 e RQ-GOV-22 (F-06). [T-DET][T-E2E: AT-81]

---

## Parte 12 — Diagnóstico

- **RQ-DIA-01** — O diagnóstico de uma linha é a visão dos vínculos com papel COMPONENTE_DIAGNOSTICO e resultado VALIDO. Componentes NAO_VIGENTE por SUBSTITUICAO_DE_ESTADO são apresentados como históricos, com as condições de origem explícitas; componentes deslocados por mudança de foco (DESLOCAMENTO_DE_FOCO) permanecem componentes contemporâneos, identificados pelo recorte a que se referem (RQ-LIN-20); resultados invalidados só aparecem na rastreabilidade [C §8.3, §8.4] (F-03). Apresentação da solicitação considera EscopoSolicitacao e VinculoResultadoSolicitacao correntes: retirados não integram atendimento vigente; resultados anteriores podem ser exibidos como históricos durante a sessão, sem invalidar outros vínculos. Retirada total sem cancelamento explícito é ENCERRADA_SEM_RESULTADO (D17-A), nunca conclusão integral/parcial por vacuidade. [T-DET][T-E2E: AT-22, AT-77]
- **RQ-DIA-02** — Um resultado integra o diagnóstico quando responde ao objetivo da linha ou a ampliação autorizada, deriva de dados e parâmetros compatíveis, tem dependências válidas, não foi invalidado e tem relação identificável com os demais componentes [C §8.4]. Apresentação da solicitação considera EscopoSolicitacao e VinculoResultadoSolicitacao correntes: retirados não integram atendimento vigente; resultados anteriores podem ser exibidos como históricos durante a sessão, sem invalidar outros vínculos. Retirada total sem cancelamento explícito é ENCERRADA_SEM_RESULTADO (D17-A), nunca conclusão integral/parcial por vacuidade. [T-DET]
- **RQ-DIA-03** — Resultado de suporte só se torna componente por pedido ou aceitação do usuário (EV-AMPLIACAO) e nunca é promovido silenciosamente. O LLM não seleciona resultados para o diagnóstico nem propõe seletivamente resultados intermediários por relevância; quando o usuário pedir o diagnóstico, os resultados intermediários disponíveis PODEM ser listados integralmente, em ordem de produção [C §8.4, Caso 22] (P-23). [T-GOV][T-E2E: AT-22]
- **RQ-DIA-04** — "Gerar o diagnóstico" é entregável de consolidação da linha, apresentado na conversação e como relatório HTML exportável em PDF (CAP-REP-05), com dados tabulares exportáveis em CSV (CAP-REP-06), sem nova operação analítica [C §8.12] (DA-23). [T-GOV][T-E2E: AT-44]
- **RQ-DIA-05** — A articulação de resultados de linhas distintas ocorre em linha de consolidação autorizada, com verificação determinística de compatibilidade segundo RQ-ORQ-13 e as condições dos contratos. Diferenças que constituem as dimensões comparadas não exigem contextos idênticos nem recálculo artificial. Incompatibilidade impede a relação analítica e é explicitada; não impede exibir componentes individualmente válidos com suas condições, sem apresentá-los como trajetória ou comparação compatível [C §8.3, §8.4]. [T-DET]
- **RQ-DIA-06** — O diagnóstico PODE conter qualificação normativa produzida por critério analítico autorizado: CFG-NOR, quando existir, ou critério normativo explicitamente definido pelo usuário (RQ-GOV-31, V-03). Neste último caso, preserva valor, operador, unidade/escala, classificação, origem e escopo e explicita: "Segundo o critério definido pelo usuário nesta análise, densidades abaixo de 1 por 1.000 foram classificadas como insuficientes", quando esses forem os parâmetros registrados. Consolidar não transforma o critério local em regra global, não amplia seu escopo nem altera CFG; fora do escopo, a classificação só pode ser relatada como resultado de origem, sem reaplicação [C §8.3] (AV-09). [T-GOV][T-E2E: AT-71]

---

## Parte 13 — Representação e entrega

| Transformações admitidas (CFG-REP) | Transformações proibidas na apresentação |
|---|---|
| Formatação numérica e arredondamento de apresentação (RQ-REP-05) | Quebras em quantis, intervalos ou classes discretas |
| Escala de apresentação pela precedência de CAP-IND-02 | Mudança automática de escala conforme a magnitude |
| Mapeamento visual contínuo de valores existentes | Linhas de tendência |
| Ordem neutra por código territorial ou ordem de resultado de ordenação | Totais, médias, contagens, proporções |
| Rótulos provenientes de metadado autorizado | Rankings e posições |
| Notação intuitiva de intervalos ("0 a <1") | Qualificações com significado analítico |
| Mascaramento de identificadores no visualizador da base | Destaques não estruturados |

- **RQ-REP-01** — C-11 DEVE aplicar somente transformações admitidas e registrar as transformações de cada representação (EV-REPRESENTACAO) [C §4.3.14, §5.10]. Sempre que uma precedência produzir escolha concreta, EV-REPRESENTACAO registra valor escolhido, nível da precedência e origem/âncora correspondente. Para escala: indicada pelo usuário → configurada → fallback por 1.000 habitantes (CAP-IND-02), sem mudança dessa precedência. Explicação posterior consulta o evento, não infere o nível pela ausência de valores. Escala e procedência continuam no bloco "Parâmetros e origens"; conteúdo de "Método e documentação" segue CFG-DOC e não determina escala. [T-DET][T-E2E: AT-29]
- **RQ-REP-02** — Classes discretas em mapas ou gráficos só PODEM exibir pertenças produzidas por capacidade (CAP-DIS-02, CAP-DIS-03, CAP-SUB-01, CAP-TEN-01). Escala visual contínua é transformação formal e não constitui classificação [C §4.3.14, Caso 20]. [T-GOV]
- **RQ-REP-03** — A ordem padrão é a do código territorial; outra ordem exige resultado de CAP-SUB-02. Reordenação interativa feita pelo usuário é estado visual (INV-18), não exibe posições e não constitui resultado. [T-DET]
- **RQ-REP-04** — Elementos não avaliáveis DEVEM ser exibidos de forma distinta de zero, com legenda; RES-VAZ é exibido como conjunto vazio com o critério aplicado; entregáveis bloqueados são exibidos com o desfecho [C §5.11]. Pendência resolúvel é exibida como espera, com seu motivo e dependentes, sem conversão em impossibilidade definitiva; relações comparativas parciais preservam objetos, causas e alcance de CAP-CMP-01. A árvore avaliada de CAP-SUB-01 pode ser tabular, sem perder vínculos, estados ou motivos. [T-DET]
- **RQ-REP-05** — Apresentação numérica (DA-20): medidas contínuas (densidades, variações, razões, distâncias, medianas, percentis e cortes) com duas casas decimais; contagens inteiras sem casas decimais. O arredondamento decimal convencional é aplicado aos dígitos do valor absoluto, preservando o sinal: terceira casa de 0 a 4 mantém a segunda; de 5 a 9 aumenta a segunda em uma unidade (1,234 → 1,23; 1,235 → 1,24; −1,235 → −1,24). Exceção: quando o arredondamento puder ocultar ou aparentemente contradizer relação analítica relevante — valor não nulo exibido como zero; sinal ou direção de mudança; relação com limiar ou critério; ordem ou igualdade entre valores exibidos juntos —, o número de casas dos valores envolvidos é aumentado automaticamente até preservar visualmente a relação verdadeira. O valor em precisão integral permanece disponível no detalhe, no CSV e na rastreabilidade. [T-DET][T-E2E: AT-47]
- **RQ-REP-06** — Controles estruturados de interface (upload, navegação, filtros, seleção, ampliação ou redução de recortes visuais, alteração da forma de visualização, consulta de detalhes, confirmação de privacidade, resposta a opções e exportação) produzem apenas estado visual ou ações de entrega e não iniciam análise; seleção usada em solicitação conversacional posterior segue RQ-FLX-16 [C §4.3.14, §11.11] (P-18). [T-GOV][T-E2E: AT-20]
- **RQ-REP-07** — Mapa exige geometria autorizada (polígonos ou pontos por latitude e longitude, conforme a seção 5.6); sem ela, a representação em mapa do entregável recebe BLQ-DAD e PODE ser oferecida tabela. [T-DET]
- **RQ-REP-08** — Painel simples é justaposição de representações dos mesmos resultados, sem cálculo entre elas (DA-23). [INSP]
- **RQ-REP-09** — Toda representação DEVE carregar referências aos resultados, parâmetros com origem e limitações necessárias à leitura autônoma, inclusive em modo degradado (Caso 14). Árvores, relações e causas estruturadas são preservadas; nenhuma representação calcula análise adicional. Apresentação válida sem síntese segue RQ-DEG-04, com status do entregável distinto da ocorrência operacional. [T-DET]
- **RQ-REP-10** — Tipos admitidos, conforme a natureza do resultado (DA-23, P-16): interação conversacional estruturada; tabela; gráfico de barras para comparações e distribuições; gráfico de linhas para séries temporais; mapa para resultados territoriais com geometria; painel simples; relatório consolidado HTML; exportação do relatório em PDF; exportação tabular em CSV. [INSP]
- **RQ-REP-11** — Escala e unidade acompanham todo valor de densidade exibido (ex.: "2,36 por 1.000 habitantes"); a escala segue a precedência de CAP-IND-02 e não muda automaticamente conforme a magnitude do resultado; taxas de CAP-ROT-01 são exibidas em percentual e identificadas como da coorte inicial (DA-09). [T-DET][T-E2E: AT-47, ROT-AT-01]
- **RQ-REP-12** — O relatório HTML e o PDF (CAP-REP-05) DEVEM preservar a distinção entre componentes e históricos, parâmetros com origem, interpretação adotada, limitações analíticas, pendências e procedência [C §8.12]; o CSV (CAP-REP-06) contém valores em precisão integral, escala no cabeçalho e colunas de avaliabilidade. Nenhuma exportação contém identificadores ou registros individualizados (DA-23, DA-24, DA-27). Exportações preservam também alcance comparativo, causas por relação e vínculos da árvore de critérios quando aplicáveis, sem reconstrução pelo LLM ou exposição de identificadores; modo degradado não dispensa esses conteúdos. Aplicar as quatro classes de RQ-DAD-20 em todo canal: nomes de campos, arquivos e planilhas sujeitos à minimização usam aliases; originais e mapas permanecem exclusivamente em C-10. Preservar fontes por IDs/versões/localizadores sanitizados, sem vazamento por perfil, procedência, eventos, produtos ou fallback. [T-GOV][T-E2E: AT-44]
- **RQ-REP-13** — O visualizador da base PODE exibir a base ao próprio usuário durante a sessão, com identificadores diretos mascarados por padrão. A revelação só ocorre por ação explícita do próprio usuário no visualizador e não autoriza envio ao LLM nem exposição em resultados, representações, sínteses ou relatórios; o visualizador não é produto analítico (DA-27). [T-GOV][T-E2E: AT-37]
- **RQ-REP-14** — Rótulos de tabelas, gráficos, mapas, relatórios e exportações de agregados seguem o TipoContagemAgregada do resultado: SOMA_DOS_COMPONENTES é rotulada como soma das contagens dos componentes, com indicação de possível dupla contagem, e nunca como pessoas únicas ou profissionais distintos; UNIDADES_DISTINTAS fundamentada em premissa do usuário exibe essa origem. Preferência de apresentação não altera o tipo do resultado (DA-16). [T-GOV][T-E2E: AT-54]

- **RQ-REP-15** — Representações, sínteses e exportações DEVEM preservar os qualificadores obrigatórios de RQ-RES-11, entre eles o alcance de CAP-ESP-02: "mais próxima entre as referências avaliáveis" não é rotulada como mais próxima do conjunto completo. Resultado de caráter histórico é rotulado como tal; resultado deslocado não é rotulado como histórico (RQ-LIN-20). Agregados com suporte efetivo temporalmente incompatível podem ser apresentados isoladamente com cobertura e membros, mas não unidos por linha que sugira trajetória do mesmo agregado nem acompanhados de mudança ou tendência inexistente. HTML, PDF, CSV e modo degradado preservam suporte, alcance, avaliabilidade, origens e limitações necessários à leitura autônoma, sem recomposição analítica em C-11 (F-04). [T-GOV][T-E2E: AT-68, AT-69, AT-71, AT-78]

---

## Parte 14 — Síntese e validação de saída

### 14.1. Entrada e saída da síntese

- **RQ-SIN-01** — C-12 recebe: solicitação; interpretação e seu modo de explicitação; resultados APRESENTAVEL dos entregáveis; parâmetros com âncoras; limitações; status e desfechos dos entregáveis; pendências; léxicos de CFG-LEX; regras de CFG-REP; âncoras documentais de CFG-DOC pertinentes (seção 4.4.23). Conteúdo metodológico inclui identidade, versão, forma autorizada, variáveis com origens e controles de condições/dependências de CFG-DOC; incidência concreta exige os registros que a comprovem. Situação de atendimento e pendências são as do conjunto vigente de EscopoSolicitacao; resultados de entregáveis retirados só entram como históricos explicitamente identificados, sem obrigação ativa nem falha fabricada. Retirada total segue D17-A/RQ-FLX-02 e os sete blocos de TPL-12. [T-GOV]
- **RQ-SIN-02** — A saída DEVE ser sequência de segmentos tipados: VALOR, CLASSIFICACAO, RELACAO, SELECAO, ORDENACAO, CONTAGEM, LIMITACAO, PARAMETRO, PROCEDENCIA, INTERPRETACAO_ADOTADA, STATUS_ENTREGAVEL, SUGESTAO, PERGUNTA, EXPLICACAO_METODOLOGICA, DESCRICAO_CAPACIDADE e CONECTIVO. Cada segmento também declara FuncaoConteudo; exceto CONECTIVO, contém referências a resultado/caminho, parâmetro, âncora, evento, pendência ou âncora documental DOC: compatível com sua função (RQ-SIN-10, V-16). CONECTIVO não contém números, entidades nem termos relacionais, normativos ou causais. Segmentos metodológicos usam texto canônico ou formas autorizadas de CFG-DOC, com interpolações verificáveis, sem paráfrase substantivamente livre; a organização não substitui validação de C-04. [T-GOV]
- **RQ-SIN-03** — A síntese PODE verbalizar valores, classes e relações presentes nos resultados; organizar a apresentação segundo o pedido; explicitar parâmetros, procedência e limitações; relacionar narrativamente o que já está estruturado; e sugerir desdobramentos sem executá-los [C §4.3.15]. [INSP]

### 14.2. Regras do validador de saída

| Regra | Verificação | Base |
|---|---|---|
| V-01 | Todo literal numérico — algarismos e numerais por extenso inequívocos, segundo a regra de numerais de CFG-LEX — corresponde a valor de resultado, parâmetro ou âncora referenciado no segmento, conforme a escala e o arredondamento de apresentação aplicados (RQ-REP-05, RQ-REP-11), inclusive casas adicionais da exceção de apresentação. "Um" e "uma" ("one") só são literais numéricos quando a construção for quantitativa e a âncora permitir verificar exatamente uma unidade; como artigo, e "a" e "an", não acionam validação numérica. Interpolações de formas de CFG-DOC seguem a mesma verificação de tipo, valor e origem. | [C §5.6] (F-12) |
| V-02 | Toda entidade factual mencionada resolve para resultado, estado ou manifestação autorizada; em conteúdo metodológico/operacional, conceitos e exemplos documentados resolvem para âncora DOC: ou pendência, sem serem afirmados como fatos dos dados (RQ-SIN-10, V-16). Formas de CFG-DOC e seu bloco metodológico seguem esses controles de entidades e âncoras. | [C §5.8] |
| V-03 | Em AFIRMACAO_ANALITICA, termos de LEX-NORM (seção 4.4.15) só com classificação produzida por critério autorizado — de CFG-NOR (deliberadamente vazio nesta versão) ou definido pelo usuário (RQ-GOV-31) — e, neste caso, com indicação explícita de que o critério é do usuário. Perguntas e explicações normativas seguem RQ-SIN-10, sem sugerir valores não autorizados | [C §3.7, §8.3] (DA-21) |
| V-04 | Termos de LEX-CAU não aparecem como afirmação sobre o fenômeno | [C §3.7, §3.8] |
| V-05 | Uso de termos de LEX-TEN para afirmar classificação dos dados exige resultado correspondente de CAP-TEN-01; mudança entre períodos é aumento, redução ou ausência de mudança ancorada em CAP-TMP-01. Menção metodológica/operacional em pergunta, descrição de capacidade, pré-condição, bloqueio, indisponibilidade ou sugestão é permitida com âncora apropriada (RQ-SIN-10), sem afirmar tendência. SEM_CLASSIFICACAO não é falta de dados, falha ou inexistência do fenômeno | [C §4.3.9, §4.3.10] (DA-15) |
| V-06 | Resultado de distância é acompanhado da indicação de TPL-11 (distância geográfica direta, não distância viária, tempo de deslocamento ou acessibilidade real); termos de LEX-ACE não o qualificam | [C §4.3.12] (DA-17) |
| V-07 | Em afirmações sobre os dados, comparativos, contagens, proporções, razões, percentuais e termos de LEX-CMP, inclusive ordinais reconhecidos deterministicamente, exigem relação, contagem ou ordenação estruturada referenciada | [C §4.3.15, §8.5] |
| V-08 | Toda limitação ANALITICA dos resultados referenciados aparece em segmento LIMITACAO, e toda interpretação ADOTADA_E_EXPLICITADA aparece em segmento INTERPRETACAO_ADOTADA. Texto canônico, formas autorizadas e fallback TPL-12 conservam essas obrigações. | [C §5.7, §9.8] (DA-22) |
| V-09 | Todo entregável vigente não ATENDIDO aparece na mesma resposta dos resultados parciais, com status, motivo e dependentes efetivos; distinguir pendência resolúvel, não avaliabilidade, impossibilidade definitiva, elemento falho (INTERROMPIDO) e cancelamento (CANCELADO). Resultado parcial não é apresentado como completo. OPR-IND de síntese dispensável não é apresentado como interrupção do entregável ATENDIDO (RQ-DEG-04). Bloqueio, falha e indisponibilidade não são negativo, zero ou vazio | [C §9.6, §9.12] |
| V-10 | Sugestões são rotuladas como tais, referenciam capacidade ATIVA e linha da matriz de aplicabilidade, não contêm valores, parâmetros normativos, agrupamentos ou métodos ausentes de fontes autorizadas e não são executadas | [C §5.12] |
| V-11 | Componente NAO_VIGENTE por SUBSTITUICAO_DE_ESTADO é rotulado como histórico, com condições de origem; resultado deslocado por mudança de foco não é rotulado como histórico e é identificado pelo recorte a que se refere; resultado INVALIDADO não é apresentado como válido | [C §8.4] (F-03) |
| V-12 | Em qualificações analíticas dos dados, termos de LEX-DES só por pedido do usuário, ordenação ou seleção estruturada ou regra de CFG | [C §4.3.15] |
| V-13 | Termos de LEX-HET não são usados como limitação ou qualificação sem critério formal autorizado; a condição concreta é descrita pelas limitações tipadas de RQ-RES-06 | [C §9.8] (DA-22, P-19) |
| V-14 | Resultado SOMA_DOS_COMPONENTES é verbalizado como soma das contagens dos componentes, ou equivalente, com indicação de possível dupla contagem, e não como número de pessoas únicas, profissionais distintos ou total de pessoas; resultado UNIDADES_DISTINTAS fundamentado em premissa do usuário menciona essa origem | [C §4.3.8] (DA-16) |
| V-15 | Qualificadores obrigatórios de RQ-RES-11 presentes nos resultados referenciados são preservados no segmento ou por referência inequívoca a segmento anterior que os enuncie para o mesmo resultado; paráfrase que os elimine ou atenue — inclusive "mais próxima" sem o alcance "entre as referências avaliáveis", agregado parcial apresentado como do conjunto completo, taxa de CAP-ROT-01 sem "da coorte inicial", resultado histórico sem rótulo — é rejeitada. Formas de CFG-DOC e fallback TPL-12 preservam os mesmos qualificadores. | [C §5.7, §9.8] (F-04) |
| V-16 | Toda afirmação metodológica/operacional substantiva deve corresponder literalmente a forma PT/EN materializada de ProposicaoDocumental vigente. Verificar id_doc e versao_fonte, idioma, id_forma_local e versao_forma, igualdade ao template interpolado, variáveis declaradas/tipadas, origens e âncoras, condições de uso e referências necessárias. Rejeitar campos extras, original protegido, conteúdo metodológico adicional, tradução/paráfrase livre, omissão de condição ou afirmação concreta sem evento/estado/resultado existente. Descrição geral não prova aplicação. Forma requerida ausente/adulterada/incompatível bloqueia fechamento; em runtime rejeita trecho e usa insuficiencia PT/EN de CFG-DOC, sem troca de idioma. D6 preserva resultado válido em TPL-12; regenerações seguem RQ-SIN-05. FN-INT-03, FN-META-01, perguntas/fallbacks e os sete blocos estão sujeitos ao mesmo contrato; LLM não valida a própria saída. | [C §5.2, §5.8]; CFG-DOC; RQ-GOV-19 |

- **RQ-SIN-04** — O validador DEVE ser aplicado a todo texto de LLM exibido: sínteses, perguntas, sugestões, respostas sobre o agente e mensagens de desfecho redigidas por LLM (INV-13). [T-GOV]
- **RQ-SIN-05** — Violação provoca regeneração com a lista de violações, até 2 regenerações (DA-26); persistindo, a saída é apresentada em modo degradado (Parte 16). O texto rejeitado nunca é exibido e a validação é registrada (EV-VALIDACAO-SAIDA). Quando falhar a composição metodológica mas houver conteúdo documental autorizado pertinente, C-11 e C-02 apresentam fallback estruturado determinístico por TPL-12: método, fórmula, versão, condições e referências documentais no bloco opcional "Método e documentação"; parâmetros, origens e escala no bloco correspondente; cobertura e limitações nos respectivos blocos. TPL-08 informa o esgotamento. Não exibir o texto rejeitado nem criar conteúdo substantivo; ausência de proposição pertinente continua DOCUMENTACAO_INSUFICIENTE. Esse fallback não altera por si os estados de entregável/solicitação nem cria retomada automática de síntese (RQ-DEG-04). [T-GOV][T-E2E: AT-28]
- **RQ-SIN-06** — Os léxicos do validador são os grupos de CFG-LEX (seção 4.4.15), em português e inglês, que mapeiam para as mesmas regras. A presença lexical aciona a regra correspondente à função verificada do segmento (RQ-SIN-10), não rejeição automática por palavra isolada; explicação metodológica não é validada apenas por presença ou ausência de palavras-chave (V-16); na dúvida não resolvida sobre âncora ou função, o validador rejeita (DA-05, F-12). [T-GOV][M-07][T-E2E: AT-86]
- **RQ-SIN-07** — A formulação linguística PODE variar entre execuções; valores, classes, relações, limitações e significado NÃO DEVEM variar [C §8.10]. A variação metodológica é limitada à seleção e organização de texto canônico ou formas autorizadas de CFG-DOC e conectores não substantivos; não permite paráfrase substantivamente livre. [T-E2E: AT-40]
- **RQ-SIN-08** — A adaptação ao usuário PODE alterar forma de apresentação, nível de detalhe e condução do diálogo, mas NÃO DEVE alterar procedimentos, critérios, limites de governança, origem das informações, condições das capacidades ou significado dos resultados [C §12.8]. [T-GOV]
- **RQ-SIN-09** — A síntese é redigida no idioma da sessão (RQ-FLX-18), com os mesmos valores, classes, relações e limitações em qualquer idioma (DA-05). Em EN, conteúdo metodológico utiliza formas EN previamente autorizadas do mesmo id_doc PT, inclusive no bloco "Method and documentation"; não cria registro normativo EN nem tradução substantivamente livre. [T-E2E: AT-43]

- **RQ-SIN-10** — C-04 DEVE validar a função de cada segmento e sua âncora, não somente o léxico. AFIRMACAO_ANALITICA exige resultado estruturado que sustente sujeito, predicado/classificação e valor/relação. METODOLOGICO_OPERACIONAL abrange perguntas, explicações de método/pré-condição, descrições de capacidade, bloqueios, indisponibilidades e sugestões: exige âncora DOC: de CFG-DOC para a regra (V-16), pendência para a pergunta, evento/status para o bloqueio e perfil/resultado para condições concretas dos dados. Formulações sobre alternativas de análise, mínimos de pré-condição ou bloqueios somente são exibidas por texto canônico ou forma previamente autorizada da proposição pertinente; número mínimo provém do contrato, número observado provém do perfil/resultado e incidência de bloqueio provém do evento/estado correspondente. C-04 verifica id_doc, versão, forma, condições pelos controles governados, dependências, âncoras e interpolações com tipos e origens, conforme CFG-DOC e V-16; não exige equivalência semântica genérica entre textos livres nem aceita paráfrase substantivamente livre. Descrição geral de método não afirma que foi aplicado. Rejeição segue RQ-SIN-05, sem exibir texto rejeitado, e fallback autorizado nos blocos de TPL-12, inclusive "Método e documentação" quando pertinente. Etiquetar conclusão sobre os dados como explicação não a autoriza. Esse mesmo controle evita falsos positivos equivalentes em V-02, V-03, V-07 e V-12; V-04, V-06 e V-13 continuam vedando qualificação causal, de acessibilidade ou de heterogeneidade não sustentada, sem bloquear menção à própria proibição. V-01 continua exigindo origem para todo número, inclusive mínimos de pré-condição. Nenhuma função permite fatos, normas ou análises inventados (AV-10, F-12). D20 aplica UsoDocumental e o catálogo literal PT/EN de CFG-DOC a todo conteúdo documental, inclusive perguntas e fallbacks; variáveis não podem veicular paráfrase metodológica livre. Texto funcional de D13 permitido à interpretação não amplia a liberdade de apresentação documental. [T-GOV][T-E2E: AT-28, AT-72, AT-86]

---

## Parte 15 — Incerteza, desfechos e respostas

### 15.1. Taxonomia de desfechos

| Código | Grupo [C §9.2] | Situação | Obrigações de comunicação |
|---|---|---|---|
| ADM-NP | Admissão | Não pertinente ao domínio | Informar brevemente; PODE indicar tipos de análise; sem conhecimento geral |
| ADM-FE | Admissão | Pertinente, fora do escopo atual | Informar relação com o domínio e não admissibilidade; alternativas distintas |
| ADM-SC | Admissão | Admissível sem capacidade disponível: não incorporada, método não incorporado, retirada ou temporariamente indisponível antes da execução (P-03) | Informar o motivo de forma simples; não simular; alternativas distintas |
| BLQ-INF | Bloqueio | Informação ou parâmetro não fornecido | Pedir a informação ou informar a dependência; sem valores de memória |
| BLQ-DEC | Bloqueio | Decisão do usuário pendente, inclusive conflito de fontes | Pergunta estruturada |
| BLQ-DAD | Bloqueio | Dado necessário ausente ou insuficiente, inclusive quadro de universo ausente; zero avaliáveis não determina esta classe sem essa causa (RQ-CAP-08) | Informar que o resultado não pode ser produzido nas condições existentes |
| BLQ-SIG | Bloqueio | Significado dos dados não estabelecido | Pedir confirmação com opções autorizadas |
| BLQ-MET | Bloqueio | Condição metodológica não satisfeita, inclusive incompatibilidade de método/tipo de contagem ou referencial conhecido não suportado | Informar a condição e seu motivo metodológico; alternativas distintas |
| BLQ-DEP | Bloqueio | Dependência anterior não satisfeita | Indicar a etapa de origem |
| OPR-FAL | Operacional | Falha de componente ou capacidade (inclui FIDELIDADE, REPRODUTIBILIDADE, RASTREABILIDADE) | Canal sistêmico |
| OPR-IND | Operacional | Indisponibilidade de componente ou capacidade detectada durante a execução (P-03); tentativa de síntese dispensável não interrompe atendimento analítico válido (RQ-DEG-04) | Canal sistêmico; não confundir ocorrência operacional com ausência de dados, insuficiência metodológica ou estado do entregável |
| RES-VAL | Resultado | Resultado válido | — |
| RES-LIM | Resultado | Resultado válido com limitações | Limitações |
| RES-SCL | Resultado | Resultado válido sem classificação prevista | Distinguir de falta de dados e de falha |
| RES-VAZ | Resultado | Vazio por aplicação legítima de critério | Explicitar critério e cobertura |

PERTINENCIA_INCERTA é estado transitório tratado por pendência (P-11). A avaliabilidade dos elementos é dimensão distinta e não substitui o desfecho [C §9.2].

- **RQ-INC-01** — Os códigos DEVEM permanecer distintos em qualquer apresentação, preservando no mínimo as distinções de [C §5.11] (INV-05). [T-GOV]
- **RQ-INC-02** — A resposta à incerteza DEVE seguir a matriz [C §9.3–9.5]: [T-GOV]

| Situação | Resposta |
|---|---|
| Informação válida já estabelecida | Prosseguir |
| Leitura única ou leituras de mesma assinatura, com fundamento autorizado | Prosseguir com interpretação registrada, explicitada quando altera a compreensão |
| Leituras de assinaturas distintas; decisão substantiva; informação faltante; significado indefinido; conflito sem precedência; dúvida sobre escopo | Pedir esclarecimento (pendência) |
| Opções autorizadas existentes | Apresentar alternativas para decisão |
| Parte bloqueada com partes separáveis | Autorizar e executar as partes independentes, inclusive durante AGUARDANDO_USUARIO; apresentar resultados, motivos, estados e pergunta aplicável conjuntamente (RQ-FLX-01/04, RQ-GOV-29/30) |
| Análise impossível com alternativa suportada | Sugerir alternativa explicitamente distinta |
| Etapa sem condição necessária | Interromper a etapa |
| Nenhuma via | Informar que a análise não pode ser executada nas condições existentes |

- **RQ-INC-03** — Alternativas DEVEM ser compatíveis com a finalidade, suportadas pela matriz de aplicabilidade e pelo catálogo, e apresentadas como distintas da análise pedida (ex.: mudança entre dois períodos em vez de tendência) [C §9.7, Caso 9]. [T-GOV][T-E2E: AT-09]
- **RQ-INC-04** — Encerramento sem resultado DEVE indicar o estado da taxonomia e nunca apresentar a ausência de resultado como negativo, zero, nulo ou vazio [C §9.12]. [T-GOV]
- **RQ-INC-05** — Cada pendência é perguntada uma vez e não é duplicada; só é reapresentada a pedido do usuário, após mudança de contexto ou quando nova solicitação depender dela (RQ-FLX-22), e parâmetro ainda válido e aplicável não é perguntado novamente (RQ-LIN-19). [T-DET][T-E2E: AT-82, AT-83]

---

## Parte 16 — Indisponibilidade e modo degradado

- **RQ-DEG-01** — A indisponibilidade do LLM é declarada quando chamadas falham ou excedem o tempo limite configurado por componente, ou o limite técnico da plataforma; gera OPR-IND e EV-INDISPONIBILIDADE [C §9.11] (DA-26). OPR-IND e EV-INDISPONIBILIDADE identificam a tentativa e o componente afetados; sua incidência sobre o atendimento depende de RQ-RES-04 e RQ-DEG-04, sem conversão automática em interrupção analítica. [T-DET]
- **RQ-DEG-02** — Antes da interpretação, C-02 informa a indisponibilidade no idioma da sessão; nenhuma capacidade analítica é acionada por tentativa nem intenção presumida. Controles de navegação, visualização e exportação permanecem disponíveis. Upload estruturado pode prosseguir pela via HABILITADORA independente do LLM (RQ-DAD-34); estruturação conversacional que ainda dependa de FN-INT-01 aguarda seu restabelecimento, sem expor conteúdo protegido nem improvisar interpretação. Não há canal alternativo para nova análise substantiva (P-18). D19: indisponibilidade em E1 antes de interpretação válida mantém a solicitação EM_ADMISSAO, registra EV-INDISPONIBILIDADE/OPR-IND e TPL-01; não é pendência do usuário nem compete na fila de pendências anteriores à criação de entregáveis, cuja ordem segue RQ-FLX-01; não produz SUSPENSA ou interpretação fictícia. Preservar mensagem sanitizada e captura UI. No retorno dentro da mesma sessão ativa, revalidar contexto/autorizações, excluir derivados recusados e reenviar automaticamente à mesma E1, sem novo pedido. Atividade automática não renova inatividade; expiração descarta espera e conteúdo, e retorno posterior não retoma sessão encerrada. [T-E2E: AT-13, AT-70, AT-176]
- **RQ-DEG-03** — Durante composição, etapas determinísticas já autorizadas e independentes de novo julgamento semântico prosseguem no mesmo contexto; etapas que dependam de reinterpretação, replanejamento ou reautorização ficam SUSPENSA [C §6.5, §9.11]. A suspensão afeta somente etapas necessárias ao resultado; a síntese dispensável de resultado já válido segue RQ-DEG-04. Havendo pendência resolúvel aplicável, o estado agregado continua AGUARDANDO_USUARIO, sem remover a suspensão própria da etapa (RQ-FLX-01). [T-DET]
- **RQ-DEG-04** — Quando todos os resultados analíticos necessários ao entregável já estiverem VALIDO, APRESENTAVEL e rastreáveis, a indisponibilidade do LLM exclusivamente na síntese NÃO impede atendimento: C-11 e C-02 preservam e apresentam deterministicamente os resultados, interpretação, parâmetros, cobertura, limitações, qualificadores de RQ-RES-11, estados e pendências, conforme TPL-12. A tentativa de síntese não executada recebe OPR-IND e EV-INDISPONIBILIDADE; não é registrada como síntese realizada, não invalida o resultado, não altera etapas analíticas CONCLUIDA/REUTILIZADA nem converte o entregável em INTERROMPIDO. Concluída a apresentação válida, o entregável é ATENDIDO, e a solicitação segue RQ-FLX-01/02 considerando demais entregáveis e pendências, sem permanecer SUSPENSA apenas pela síntese. A síntese não é retomada automaticamente no restabelecimento; pedido textual posterior constitui nova solicitação ou retomada explicitamente requerida, com os controles de contexto aplicáveis. A ausência de conteúdo ainda necessário, de apresentabilidade ou de rastreabilidade não satisfaz esta condição; LLM necessário à interpretação, determinação ou produção do resultado segue suspensão/impedimento aplicável. Nenhum componente determinístico produz interpretação, comparação, destaque analítico, causalidade, conclusão ou síntese nova além dos registros autorizados [C §9.11, Caso 14]. A apresentação metodológica eventualmente aplicável usa exclusivamente texto canônico ou formas autorizadas de CFG-DOC no bloco opcional "Método e documentação" de TPL-12, sob V-16; parâmetros, escala, cobertura e limitações conservam seus blocos. Isso não é nova síntese determinística nem muda as condições de atendimento acima. [T-DET][T-E2E: AT-14, AT-100, AT-101]
- **RQ-DEG-05** — Pendências já estruturadas por C-04 PODEM ser apresentadas por modelo de CFG-TPL e respondidas por opção; a resposta é processada deterministicamente (RQ-FLX-15), e o fluxo prossegue apenas até a próxima etapa que exija função do LLM, que fica SUSPENSA. A indisponibilidade restrita à síntese dispensável segue RQ-DEG-04 e não impõe nova suspensão depois de concluída a apresentação válida. Pergunta e fallback obedecem à mesma ordem completa de TPL-04, motivo opcional por UsoDocumental e opções autorizadas com rótulos PT/EN governados (seção 4.4.11); não dependem de tradução/paráfrase livre nem de rótulo criado pelo LLM. [T-DET][T-E2E: AT-136, AT-177]
- **RQ-DEG-06** — Indisponibilidade de outros componentes: C-06 gera OPR-IND nas etapas; C-13 torna os resultados RASTREABILIDADE_PENDENTE; C-09 impede novas autorizações; C-10 gera OPR-IND nas etapas que dependem de dados; C-07 impede execução. [T-DET]
- **RQ-DEG-07** — Esta SPEC não exige componente LLM alternativo; se houver, ele DEVE ser registrado e validado como troca de LLM (RQ-EVO-05). [INSP]
- **RQ-DEG-08** — Restabelecido o componente, etapas SUSPENSA retomam somente após nova verificação pré-execução. A retomada abrange somente etapas necessárias efetivamente suspensas; exclui a síntese dispensada pelo atendimento em modo degradado de RQ-DEG-04. Não reexecutar partes independentes válidas nem remover pendências por simples restabelecimento. Espera operacional de E1 permanece EM_ADMISSAO e retoma a própria E1 por RQ-DEG-02, sem exigir transição SUSPENSA; encerrar sessão prevalece sobre qualquer restabelecimento. [T-DET]
- **RQ-DEG-09** — Os modelos de CFG-TPL, em português e inglês, são os da seção 4.4.16: TPL-01 indisponibilidade do LLM; TPL-02 indisponibilidade de componente; TPL-03 falha de etapa; TPL-04 pendência; TPL-05, TPL-06 e TPL-07 mensagens de ADM-NP, ADM-FE e ADM-SC; TPL-08 limite de regeneração atingido; TPL-09 aviso de sessão temporária (RQ-FLX-19); TPL-10 aviso de campos protegidos (RQ-DAD-22); TPL-11 limitação de distância geográfica direta (V-06); TPL-12 apresentação estruturada em modo degradado (RQ-DEG-04). A pergunta de natureza de entidade nominal tem texto fixado em CFG-PRV (seção 4.4.22). Campos entre chaves são preenchidos exclusivamente por estado ou valores estruturados autorizados (DA-05). A estrutura completa e o bloco metodológico opcional de TPL-12 obedecem ao contrato de CFG-TPL e CFG-DOC; nenhuma forma produz conteúdo substantivo novo. TPL-13 comunica impossibilidade de materialização integral em PT/EN; arquivo substituto é nova entrada e só retoma pedido preservado após associação e habilitação válidas (RQ-DAD-43). [INSP]
- **RQ-DEG-10** — Parâmetros operacionais (DA-26): até 2 regenerações do LLM por falha de validação; até 1 nova tentativa por unidade semântica independente idempotente, sem aumento de orçamento por decomposição; timeout como parâmetro técnico configurável por componente ou limitado pela plataforma, sem valor metodológico fixado nesta SPEC (CFG-OPR, seção 4.4.24); esgotadas as tentativas ou o timeout, comunicação estruturada da falha ou indisponibilidade pelos desfechos e modelos aplicáveis. As ocorrências operacionais são registradas no seu âmbito; uma tentativa de síntese dispensável esgotada não interrompe o resultado atendido em RQ-DEG-04. [INSP][T-DET]

---

## Parte 17 — Rastreabilidade

- **RQ-RAS-01** — C-13 DEVE ser somente acréscimo durante a sessão ativa. Cada evento contém: identificador, tipo, natureza (NaturezaRegistro), instante, sessão, snapshot, referências, resumo do evento anterior (encadeamento) e resumo próprio. solicitacao_id e linha_id são opcionais até que esses objetos existam legitimamente; eventos habilitadores referenciam entrada/base e escopo, sem criar solicitação ou linha fictícia. A ligação posterior conserva a origem do evento. Encerramento da sessão elimina também a rastreabilidade de sessão conforme RQ-FLX-17; somente acréscimo não significa persistência entre sessões [C §5.10]. [T-DET]
- **RQ-RAS-02** — Tipos mínimos de evento: os da tabela abaixo. Registrar também disposições e consequências de exclusão; captura UI no envio; EV-INTERACAO_USUARIO do catálogo fechado de CFG-OPR, com session_id, tipo e timestamp; retirada por EV-ALTERACAO-ESTADO com alvo solicitação, versões, consumidores e D17-A; cancelamento de solicitação e entregáveis; EV-RETORNO_TARDIO_DESCARTADO para retorno posterior a cancelamento; falhas/tentativas, ResultadoElemento por unidade e causas; negativa/reversão; materialização impossível e vínculo substituto; sessão e motivo do encerramento. Âncoras podem existir sem linha legítima, identificando entrada/base ou solicitação. Todos os eventos são sanitizados e eliminados no fim da sessão. [T-DET]

| Evento | Natureza |
|---|---|
| EV-MENSAGEM, EV-RESPOSTA, EV-CANCELAMENTO, EV-AMPLIACAO, EV-CAPTURA-SELECAO, EV-SUGESTAO-ACEITA, EV-CONFIRMACAO-USO, EV-REVELACAO, EV-INTERACAO_USUARIO | MANIFESTACAO_USUARIO |
| EV-LEITURA-MINIMA, EV-INTERPRETACAO, EV-PLANO, EV-SUGESTAO, EV-META | INTERPRETACAO_LLM |
| EV-PERTINENCIA, EV-ADMISSIBILIDADE, EV-DISPONIBILIDADE, EV-VALIDACAO-INTERPRETACAO, EV-VALIDACAO-PLANO, EV-PENDENCIA, EV-CONFLITO, EV-VERIFICACAO, EV-AUTORIZACAO, EV-REPLANEJAMENTO, EV-SUSPENSAO, EV-REAUTORIZACAO, EV-VIGENCIA, EV-INVALIDACAO, EV-LINHA, EV-VALIDACAO-SAIDA, EV-PRIVACIDADE, EV-RCNA, EV-TRIAGEM | DECISAO_GOVERNANCA |
| EV-EXECUCAO, EV-REUSO, EV-EXAME | EXECUCAO_ANALITICA |
| EV-RESULTADO | RESULTADO_ESTRUTURADO |
| EV-REPRESENTACAO, EV-EXPORTACAO | REPRESENTACAO |
| EV-SINTESE, EV-PERGUNTA (quando redigida pelo LLM) | SINTESE |
| EV-FALHA, EV-INDISPONIBILIDADE, EV-PERGUNTA (quando por modelo), EV-SESSAO, EV-RETORNO_TARDIO_DESCARTADO | OPERACIONAL_SISTEMA |
| EV-ALTERACAO-ESTADO | MANIFESTACAO_USUARIO ou DADOS, conforme a origem |
| EV-INGESTAO, EV-ESTADO-BASE | DADOS |
| EV-CONFIG | CONFIGURACAO |

- **RQ-RAS-03** — Os elementos exigidos por [C §5.10, §8.7] DEVEM ser reconstruíveis a partir dos eventos: solicitação e linha (EV-MENSAGEM, EV-LINHA); interpretação (EV-INTERPRETACAO); pertinência, admissibilidade e disponibilidade (eventos homônimos); decisões (EV-RESPOSTA, EV-CONFLITO); dados e versões, mapeamentos, parâmetros e origens, regras e métodos (EV-AUTORIZACAO com o contexto); capacidades e sequências planejada e executada (EV-PLANO, EV-EXECUCAO, EV-REPLANEJAMENTO); verificações (EV-VERIFICACAO); intermediários e dependências, exclusões, não avaliáveis e limitações (EV-RESULTADO); validade e vigência (EV-VIGENCIA, EV-INVALIDACAO); representações (EV-REPRESENTACAO); síntese (EV-SINTESE); seleções usadas (EV-CAPTURA-SELECAO). Reconstruir estado agregado durante E7–E12 independentes, pendência resolvida, ramo retomado, resultados preservados/reutilizados e identidade semântica dos entregáveis; conservar causas normativas e sua cadeia, relações e operandos, regra longitudinal com escopo/exceções e árvore por nó. EV-INDISPONIBILIDADE distingue tentativa de síntese não realizada de atendimento analítico em modo degradado. [T-DET]
- **RQ-RAS-04** — A linhagem DEVE retornar as origens aplicáveis: na via ANALITICA, solicitação, interpretação, decisões, plano, contexto, etapas, entradas, bases/versões, configuração, resultado, representação e síntese; na HABILITADORA, evento de introdução, entrada original, normalização, triagem, autorização específica e perfil do exame, sem exigir plano ou linha inexistentes. Comparações preservam os contextos de origem e sua compatibilidade; dados conversacionais preservam MANIFESTACAO_USUARIO e localizadores validados, sem valores protegidos em eventos. Planilhas independentes preservam arquivo, planilha e escopo próprios; base combinada conserva todas as origens e a regra autorizada. Tipificação nominal e regra longitudinal territorial preservam sua origem e escopo sem propagação indevida; comparação e critério conservam causas e registros de etapas quando não existir resultado analítico. Aplicar as quatro classes de RQ-DAD-20 em todo canal: nomes de campos, arquivos e planilhas sujeitos à minimização usam aliases; originais e mapas permanecem exclusivamente em C-10. Preservar fontes por IDs/versões/localizadores sanitizados, sem vazamento por perfil, procedência, eventos, produtos ou fallback. [T-DET]
- **RQ-RAS-05** — A ficha de procedência DEVE mostrar, para cada parâmetro, universo e critério, o valor, o tipo de origem e a âncora, com a interpretação do LLM apresentada separadamente, nunca como origem [C §5.10, §8.7]. Escolha concreta por precedência, inclusive escala indicada/configurada/fallback por 1.000 habitantes, conserva valor, nível utilizado e origem/âncora em EV-REPRESENTACAO. A explicação metodológica consulta esse registro e a proposição de CFG-DOC, sem inferência por ausência; bloco opcional de TPL-12 não substitui a ficha nem altera a precedência. Aplicar as quatro classes de RQ-DAD-20 em todo canal: nomes de campos, arquivos e planilhas sujeitos à minimização usam aliases; originais e mapas permanecem exclusivamente em C-10. Preservar fontes por IDs/versões/localizadores sanitizados, sem vazamento por perfil, procedência, eventos, produtos ou fallback. [T-DET][T-E2E: AT-38]
- **RQ-RAS-06** — A integridade do encadeamento DEVE ser verificável durante a sessão. É proibida a retenção de conteúdo de eventos ou resultados da sessão após o encerramento; o relatório exportado preserva procedência, limitações e parâmetros (RQ-REP-12) (DA-24). O encerramento explícito ou após 1800 segundos de inatividade exige descarte integral de RQ-FLX-17, incluindo originais, aliases, contextos e conteúdo de eventos. Imutabilidade de C-13 vale apenas na sessão ativa, sem retenção entre sessões ou recuperação após expiração. [T-DET]
- **RQ-RAS-07** — Eventos NÃO DEVEM conter valores protegidos, inclusive em EV-MENSAGEM, EV-LEITURA-MINIMA e registros de validação de dados conversacionais. A guarda original restrita em C-10 permite a conferência determinística sem copiá-la para C-13; eventos retêm localizadores, marcações e placeholders (RQ-DAD-39), nunca o mapeamento entre placeholder e original. EV-REVELACAO registra somente campo, instante e ação. EV-ESTADO-BASE registra cada transição de StatusBase com a pendência ou etapa causadora (RQ-DAD-42). EV-INGESTAO registra origem, normalizações e correspondências; EV-AUTORIZACAO distingue HABILITADORA de ANALITICA e seus controles (DA-27, RQ-DAD-33, RQ-DAD-34). Reconhecimento nominal registra regra estrutural, localizador e escopo da tipificação, sem valor protegido ou mapeamento original-placeholder. Esses controles também valem para os registros de seleção/combinação de planilhas. Aplicar as quatro classes de RQ-DAD-20 em todo canal: nomes de campos, arquivos e planilhas sujeitos à minimização usam aliases; originais e mapas permanecem exclusivamente em C-10. Preservar fontes por IDs/versões/localizadores sanitizados, sem vazamento por perfil, procedência, eventos, produtos ou fallback. [T-GOV]

---

## Parte 18 — Registros individualizados

- **RQ-PRV-01** — Bases com registros individualizados, provenientes de arquivo ou conversa (RQ-DAD-33), PODEM ser usadas como insumo de capacidades determinísticas autorizadas, inclusive contagem, deduplicação e produção de resultados territoriais ou agregados, após a triagem (seção 5.5) e a confirmação de uso (RQ-DAD-22) [C §3.8] (DA-27). [T-GOV]
- **RQ-PRV-02** — Identificadores diretos e registros individuais NÃO DEVEM ser enviados ao LLM; o LLM recebe apenas a estrutura sanitizada, com placeholders no lugar de conteúdo protegido, e resultados agregados ou territoriais necessários à interpretação e à síntese (RQ-DAD-23, RQ-DAD-37 a RQ-DAD-39, INV-16). [T-GOV][T-E2E: AT-74, AT-75]
- **RQ-PRV-03** — Os esquemas de saída admitem apenas unidades territoriais, conjuntos, períodos e categorias. Identificadores individuais não aparecem em tabelas, gráficos, mapas, relatórios, exportações, sínteses ou diagnóstico; a guarda de privacidade de C-04 verifica cada saída antes da apresentação, e violação bloqueia a saída e gera EV-PRIVACIDADE. [T-GOV][T-E2E: AT-37]
- **RQ-PRV-04** — Pedidos que tomem indivíduos como objeto recebem ADM-FE por EXC-09 ou EXC-10. [T-GOV]
- **RQ-PRV-05** — O motor PODE usar identificadores internamente quando necessário a operação autorizada, como deduplicação e correspondência longitudinal de CAP-ROT-01; esse uso não gera saída com identificadores. [T-DET]
- **RQ-PRV-06** — O exame de base individualizada reporta apenas estrutura e cobertura agregadas, sem listar identificadores. [T-GOV]
- **RQ-PRV-07** — A visualização da base pelo próprio usuário segue RQ-REP-13: identificadores diretos mascarados por padrão e revelação apenas por ação explícita do usuário no visualizador, sem efeito sobre o LLM ou sobre produtos analíticos. [T-GOV]
- **RQ-PRV-08** — Bases individualizadas não são persistidas além da sessão (RQ-DAD-17). A confirmação de uso registra a manifestação do usuário e não constitui avaliação jurídica automática de conformidade (DA-27). O encerramento explícito ou após 1800 segundos de inatividade exige descarte integral de RQ-FLX-17, incluindo originais, aliases, contextos e conteúdo de eventos. Imutabilidade de C-13 vale apenas na sessão ativa, sem retenção entre sessões ou recuperação após expiração. [T-DET]
- **RQ-PRV-09** — Não há limiar universal de supressão de células pequenas nesta versão (CFG-PRV); regras adicionais de anonimização, pseudonimização ou supressão só são incorporadas por configuração governada (Parte 19) (DA-27, P-20). [INSP]
- **RQ-PRV-10** — Em CAP-ROT-01, identificadores individuais são usados pelo motor exclusivamente para deduplicação e correspondência longitudinal entre t0 e t1; não são enviados ao LLM, não constam de eventos, resultados, representações, sínteses, diagnósticos, relatórios ou exportações, e a identidade é referenciada apenas por metadado ou âncora protegida. Pedido de listar quem saiu, quem permaneceu ou quem reentrou recebe ADM-FE (EXC-09, EXC-10). [T-GOV][T-E2E: ROT-AT-08]

---

## Parte 19 — Evolução controlada

- **RQ-EVO-01** — Toda alteração de finalidade, domínio, escopo, capacidades, métodos, indicadores, fontes, regras, componente de linguagem, interação ou apresentação DEVE ter RegistroMudanca no processo externo de desenvolvimento antes de produzir efeito, e só vale em nova versão aplicada a novas sessões (RQ-CFG-05). A falta de resposta adequada a qualquer das dez questões de [C §11.12] impede tratar a alteração como simples extensão operacional (DA-01). [INSP]

```text
RegistroMudanca
  id
  objeto: Enum<FINALIDADE, DOMINIO, ESCOPO, CAPACIDADE, METODO, INDICADOR, FONTE, REGRA,
               LLM, INTERACAO, APRESENTACAO, DECISAO_INCORPORADA>
  descricao: Texto
  respostas [C §11.12]:
    Q1 compatibilidade com a finalidade
    Q2 permanência no domínio atual ou necessidade de revisá-lo
    Q3 necessidade analítica atendida
    Q4 nova capacidade ou modificação de existente
    Q5 natureza de execução
    Q6 dados, parâmetros e regras exigidos
    Q7 decisões que permanecem com o usuário
    Q8 riscos de interpretação ou uso indevido
    Q9 forma de rastreamento dos resultados
    Q10 efeitos sobre capacidades e resultados existentes
  impacto [C §11.9]: capacidades dependentes; composições; interpretações disponíveis;
                     resultados produzidos; sugestões; regras de governança
  natureza_do_efeito_em_resultados: Enum<SUBSTITUICAO_DE_ESTADO, CORRECAO_OU_REPUDIO>
  evidencias_de_validacao: testes selecionados conforme RQ-QUA-02
  registro: responsável e data de efeito no processo de desenvolvimento (DA-01)
  versao_resultante: Id do snapshot aplicado a novas sessões
```

- **RQ-EVO-02** — Mudança de status de capacidade em CFG-CAP só ocorre em nova versão: nas sessões seguintes, novas admissões recebem ADM-SC com o motivo e as sugestões deixam de considerá-la. Indisponibilidade operacional durante a sessão segue RQ-GOV-12 e RQ-ORQ-10. Resultados existentes permanecem válidos, salvo declaração de correção; o LLM nunca emula capacidade retirada ou indisponível [C §11.9] (DA-01, P-03). [T-GOV][T-E2E: AT-35]
- **RQ-EVO-03** — Nova família exige revisão de escopo; nova capacidade em família existente exige contrato completo e validação, sem revisão de escopo (RQ-ESC-09). [INSP]
- **RQ-EVO-04** — Novo indicador ou método só é incorporado com definição metodológica explícita; a aptidão do LLM para produzir o conteúdo não é justificativa (Caso 23) [C §11.4, §11.5]. [INSP][T-E2E: AT-23]
- **RQ-EVO-05** — Troca ou atualização do componente de linguagem DEVE preservar: limites de uso do conhecimento prévio; controle de pertinência; distinção entre decisões operacionais e substantivas; subordinação à governança; precedência das capacidades determinísticas; rastreabilidade das decisões; proibição de produção autônoma de fatos. A ativação exige validação proporcional ao impacto (Parte 20): camadas L3 e L4 e cenários essenciais, com registro e avaliação de erros materiais, sem ampliar a autonomia do LLM [C §11.10] (DA-28). [T-LLM][T-E2E]
- **RQ-EVO-06** — Alteração de decisão incorporada (Parte 22) é registrada como RegistroMudanca, atualiza esta SPEC e os itens CFG afetados e é validada conforme RQ-QUA-02. [INSP]
- **RQ-EVO-07** — Novos recursos de interação e apresentação não criam análises fora das capacidades nem canal de disparo de análises; o estado visual permanece separado do analítico [C §11.11] (P-18). [INSP]
- **RQ-EVO-08** — Nova fonte configurada exige RegistroMudanca, mapeamento semântico e análise de compatibilidade com os resultados existentes; bases fornecidas pelo usuário, por upload ou conversa, seguem a Parte 5 [C §11.6] (DA-02). [INSP]
- **RQ-EVO-09** — Resultados registram as versões sob as quais foram produzidos; novas versões não os alteram retroativamente [C §11.8]. [T-DET]
- **RQ-EVO-10** — Ampliação de vocabulários, aliases, categorias, léxicos, padrões de privacidade, modelos, referências ou referenciais padrão da Configuração Inicial de Implementação, bem como o preenchimento de item deliberadamente vazio, só ocorre por RegistroMudanca e nova versão da configuração (RQ-CFG-01, RQ-CFG-12); não ocorre durante a sessão, por interpretação do LLM ou por conteúdo de bases. [INSP]

---

## Parte 20 — Qualidade, validação e critérios de aceite

### 20.1. Validação proporcional ao risco

| Camada | Objeto | Aplicação (DA-28) |
|---|---|---|
| L1 | Capacidades determinísticas: casos de borda (ausência, zero, empates, fronteiras de quantis, base zero, séries curtas, lacunas temporais, coordenadas inválidas, referenciais; na coorte inicial, reentrada, coorte vazia, registros repetidos, identidade insuficiente e pessoas em mais de um componente) e propriedades (determinismo, preservação do universo, ausência diferente de zero); triagem determinística (CPF com dígitos verificadores, e-mail, telefone, entidades nominais, placeholders); separadores de CSV e planilhas de XLSX | Testes da capacidade ou regra alterada e de suas dependentes |
| L2 | Governança: gates, âncoras, autoridade, gatilhos, verificação pré-execução, autorização, separabilidade, suspensão e triagem de privacidade, com saídas do LLM simuladas, inclusive adversariais | Integral para os invariantes críticos; demais por impacto |
| L3 | Funções FN-* em corpus representativo em português e inglês, com formulações adversariais e ambiguidades | A cada mudança de função ou de modelo; erros materiais registrados e avaliados |
| L4 | Validador de saída: textos válidos e textos com violações conhecidas por regra V-01 a V-16, em português e inglês | Integral no corpus (invariante crítico de síntese) |
| L5 | Cenários ponta a ponta AT-01 a AT-178 e testes ROT-AT-01 a ROT-AT-09, como catálogo de referência | Conjunto essencial (RQ-QUA-03) e cenários ligados à mudança |
| L6 | Regressão orientada ao impacto de cada RegistroMudanca | Seleção pelas camadas e cenários afetados |

- **RQ-QUA-01** — Os invariantes críticos da tabela abaixo DEVEM ter aprovação integral antes de qualquer liberação (DA-28). [INSP]

| Invariante crítico | Requisitos | Verificação | Cenários essenciais |
|---|---|---|---|
| Cálculos determinísticos produzem os resultados esperados | RQ-CAP-02, RQ-CAP-03, Parte 8 | L1 | AT-01, AT-17, AT-40, AT-53, ROT-AT-01 |
| O LLM não substitui o motor analítico | INV-02, INV-03, RQ-ARQ-09 | L2 | AT-04, AT-06, AT-27 |
| Nenhuma execução ocorre sem autorização válida | INV-01, RQ-ARQ-02 | L2 | AT-02, AT-13 |
| Ausência não é convertida silenciosamente em zero | INV-04, RQ-DAD-07 | L1, L2 | AT-08, AT-17, AT-33 |
| Dados individualizados não são expostos indevidamente | INV-16, Parte 18 | L2 | AT-37, AT-74, AT-75, ROT-AT-08 |
| A síntese não cria números, classificações ou conclusões inexistentes no resultado estruturado | INV-11, INV-13, V-01 a V-16 | L4 | AT-28, AT-54, AT-78, AT-86 |
| O executado corresponde ao autorizado | RQ-ORQ-05, M-09 | L2 | AT-02, AT-21 |

- **RQ-QUA-02** — A seleção de testes é proporcional ao risco e ao impacto da mudança: capacidade alterada exige L1 da capacidade e seus casos de borda; mudança em fluxo principal exige os cenários essenciais do fluxo; mudança em função ou modelo do LLM exige L3, L4 e cenários essenciais. Alteração pequena não exige a execução integral do catálogo (DA-28). [INSP]
- **RQ-QUA-03** — O conjunto essencial de cenários reúne os da tabela de RQ-QUA-01 e os fluxos principais: solicitação simples (AT-01), composta (AT-02), esclarecimento (AT-03), fora do escopo (AT-04), não pertinente (AT-05), modo degradado (AT-13, AT-14), privacidade (AT-37) e sessão e exportação (AT-44). [INSP]
- **RQ-QUA-04** — Erros materiais do LLM (fato não ancorado, pertinência ou admissibilidade incorreta, ambiguidade material não detectada, plano infiel, violação não detectada pelo validador) DEVEM ser registrados e avaliados; as métricas M-01 a M-08 são acompanhadas sem limiar numérico de liberação (DA-28). [INSP]
- **RQ-QUA-05** — O conjunto de dados de teste DEVE incluir: universo de 100 unidades com registros para 92; denominador ausente e denominador zero; base com dois períodos e séries de quatro ou mais períodos com os padrões de AT-53; versões v1 e v2 da mesma base; códigos de ausência; base individualizada com e sem identificador de pessoa, com pessoas presentes em mais de um município e em mais de uma categoria; contagens agregadas por município sem identificador; tabelas largas simples, dimensões constantes, arquivos auxiliares com chaves únicas e conflitantes, totais/subtotais misturados, pequenos conjuntos no chat e mensagens mistas, populações compartilhadas entre categorias, referências parcialmente avaliáveis, agregados com suportes diferentes entre períodos; bases com e sem declaração de domínio, com categorias de reconhecimento automático, contextual, ambíguas e não reconhecidas pela configuração; coordenadas com e sem referencial informado; formulações em português e inglês; base individualizada longitudinal com identidade de pessoa em dois ou mais períodos, reentrada, registros repetidos, lacunas de identidade, coorte vazia e pessoas em dois componentes; mensagens e arquivos com CPF válido e inválido, e-mails, telefones com e sem marcador, números isolados e expressões nominais tipificadas e ambíguas; CSV com vírgula e com ponto e vírgula, inclusive estrutura ambígua, e XLSX com várias planilhas; agregados multicategoriais com cobertura incompleta e agregados com TipoContagemAgregada diferente entre períodos. Incluir os cenários AT-91 a AT-115 e suas variantes obrigatórias da seção 20.9, com múltiplas pendências, decomposições técnicas equivalentes, comparação parcial, regras territoriais escopadas, árvores aninhadas, reconhecimento nominal estrutural, formas documentais e falhas de composição, referenciais suportados/não suportados e planilhas independentes/combinadas. Catálogo vigente: AT-01–AT-178 e ROT-AT-01–ROT-AT-09. Incluir integralmente os cenários e variantes da seção 20.10: quatro classes de privacidade com controles positivos/negativos, metadados e histórico reconstruído, autorização/negativa/reversão, disposições de exclusão, retirada total D17-A, referência contextual/comparativa, E1, formas PT/EN e interpolação, objetivo terminal, UI, CRS, planilhas auxiliares, falha parcial, árvore trivalente sem resultado, relógio de 1800 segundos e concorrência. Incluir integralmente os cenários da seção 20.11: evidência positiva e persistência da proteção, simetria PT/EN, identificadores governados, ContextoDeMedida, falha parcial por elemento, cancelamento e retorno tardio, múltiplas exclusões, reversão de autorização, mensagem mista, renovação de sessão, fila anterior à criação de entregáveis, rótulos governados e consulta ao catálogo externo. Mantêm-se todos os cenários anteriores. [INSP]
- **RQ-QUA-06** — Robustez [C §10.7]: variantes de formulação, inclusive no outro idioma suportado, produzem o mesmo desfecho de governança e o mesmo conteúdo analítico. Decomposições técnicas distintas de pedido semanticamente equivalente conservam identidade/quantidade de entregáveis, conteúdo, avaliabilidade e estados de entregável/solicitação; comparar essas propriedades independentemente de IDs de etapa. D21/D26 exigem mesmos objetivos terminais, valores, avaliabilidade, estados e terminalidade para reformulações equivalentes, lote ou decomposições alternativas; inclusive falha de uma unidade e retirada de escopo. Formulações semanticamente equivalentes em PT e EN produzem a mesma decisão estrutural (RQ-CFG-14). A comparação documental desses contratos não equivale a teste de software executado. [T-E2E]
- **RQ-QUA-07** — Consistência entre camadas [C §10.4]: todo segmento de síntese e todo elemento de representação ou exportação resolve para resultado, parâmetro ou âncora (V-01, V-02, RQ-REP-09). Aplicar também a nós de critérios, relações parciais, causas e fallback metodológico de CFG-DOC/TPL-12; estado agregado não substitui controles de etapa. Verificar sete blocos, terceiro opcional, formas PT/EN ligadas à mesma proposição e procedência concreta da precedência. V-16 exige formas literais PT/EN versionadas no catálogo externo compatível; a forma EN é apresentação da mesma proposição PT e preserva modalidade, obrigação, proibição, permissão, negação, quantificadores, alternativas, listas fechadas, estados, motivos, parâmetros, condições, exceções, unidades, números e variáveis (seção 4.4.23.2), com rejeição de variável extra ou sem âncora. TPL-04 mantém seis posições, motivo pertinente opcional; TPL-12 exatamente sete blocos; TPL-13 existe em PT/EN. Ausência de forma ou rótulo requerido bloqueia fechamento documental. [T-E2E: AT-162, AT-177, AT-178]

### 20.2. Cenários de aceite derivados dos casos do Concept

Salvo indicação em contrário, os cenários assumem bases carregadas e examinadas na sessão, com a pertença das categorias à FTS estabelecida por uma das vias de RQ-DAD-19.

**AT-01 — Solicitação simples (Caso 1).** Dado: bases de FTS e populacional carregadas na sessão, examinadas e com significados estabelecidos; nenhuma escala indicada nem configurada. Quando: "Qual é a densidade da categoria X no território A em 2024?". Então: PERTINENTE; FAM-02; CAP-IND-02 disponível; lista de verificação aprovada; EV-AUTORIZACAO anterior a EV-EXECUCAO; resultado RES-VAL com quantitativo, população e densidade canônica; apresentação por 1.000 habitantes com duas casas decimais; síntese aprovada em V-01; papel COMPONENTE_DIAGNOSTICO.

**AT-02 — Solicitação composta (Caso 2 e §4.4).** Dado: séries de quatro ou mais períodos, coordenadas com referencial informado e conjunto de referências indicado pelo usuário. Quando: "Entre os territórios com tendência de declínio, identifique os que estão a mais de 150 km da referência mais próxima e compare os cinco de maior população em densidade, tendência e distância". Então: plano com universo, densidade, tendência (CAP-TEN-01), distância à referência mais próxima (CAP-ESP-02), critérios "declínio" e "> 150 km" avaliados como conjunção trivalente, ordenação por população, seleção de cinco com empatados no corte incluídos e N efetivo informado, comparação, representação e síntese; 150 km ancorado na manifestação; nenhum critério, limiar ou referência criado pelo LLM; unidades com série insuficiente NAO_AVALIAVEL; limitação de distância geográfica direta presente; verificação registrada por etapa; papéis atribuídos na autorização. O significado longitudinal territorial, o suporte geodésico e as compatibilidades estão autorizados no escopo. A árvore da conjunção conserva operandos, estados, motivos e âncoras; a comparação genérica de três ou mais selecionados apresenta valores e ordem dos avaliáveis, sem diferenças automáticas de todos os pares. O ranking e a seleção de cinco decorrem do pedido explícito.

**AT-03 — "Analise juntos" (Caso 3).** Dado: cinco territórios indicados, sem modo no estado. Quando: "Analise esses municípios juntos". Então: AMB-01; pendência com as três alternativas (em paralelo, comparação, agregado), apresentadas como OpcaoAutorizada do conjunto AMB-01, com rótulos PT/EN governados, sem código interno ou rótulo produzido pelo LLM; nenhuma execução antes da resposta; resposta registrada como ESCLARECIMENTO_DE_INTENCAO com escopo na linha e no conjunto; o mesmo pedido para outro conjunto gera nova pergunta (DA-16).

**AT-04 — Pertinente fora do escopo (Caso 4).** Quando: "Projete a densidade da força de trabalho na saúde desses municípios até 2040". Então: PERTINENTE; ADM-FE por não enquadramento; nenhum valor projetado; alternativa admitida, se oferecida, rotulada como distinta.

**AT-05 — Fora do domínio (Caso 5).** Quando: "Qual foi o campeão do campeonato brasileiro?". Então: NAO_PERTINENTE; ADM-NP; nenhum fato sobre o tema; PODE listar tipos de análise; nenhuma linha criada.

**AT-06 — Tema externo (Caso 6).** Quando: "A temperatura média desses territórios pode explicar a distribuição da força de trabalho na saúde?". Então: PERTINENTE; ADM-FE por EXC-03 (e EXC-04 ou EXC-05); nenhuma temperatura de memória; variante com coluna de temperatura na base produz o mesmo desfecho; mensagem aprovada em V-04.

**AT-07 — Informação não fornecida (Caso 7).** Dado: nenhum parâmetro no estado nem em CFG. Quando: "Mostre os municípios abaixo do parâmetro de referência". Então: BLQ-INF; pendência PARAMETRO_FALTANTE; pergunta sem valores sugeridos (P-05); CAP-SUB-01 não executada.

**AT-08 — Dado ausente (Caso 8).** Dado: denominador ausente para o território e o período. Então: NAO_AVALIAVEL (DENOMINADOR_AUSENTE); BLQ-DAD; nenhum zero, média ou estimativa; o agente informa a ausência e PODE pedir que o usuário forneça o valor, sem sugeri-lo. Variante: o usuário informa explicitamente a população daquele território e período; o valor é validado e usado no escopo indicado, com limitação VALOR_FORNECIDO_PELO_USUARIO (DA-07, DA-10).

**AT-09 — Mudança sem tendência (Caso 9).** Dado: base com dois períodos. Quando: "A densidade cresceu?". Então: CAP-TMP-01; direção por comparação exata; variação absoluta e percentual; síntese sem afirmação analítica de tendência; explicação metodológica ancorada é permitida (V-05, RQ-SIN-10). Quando: "Há tendência de crescimento?". Então: BLQ-MET (SERIE_INSUFICIENTE, menos de quatro períodos) e a mudança entre os dois períodos oferecida como alternativa distinta. Variante com base zero: 0 → 5 resulta AUMENTO, +5 e percentual NAO_AVALIAVEL (BASE_ZERO); 5 → 0 resulta REDUCAO, −5 e −100% (DA-14).

**AT-10 — Série sem classificação (Caso 10).** Dado: série de quatro ou mais observações com mudança de direção (ex.: 10, 12, 11, 13). Então: SEM_CLASSIFICACAO com motivo MUDANCA_DE_DIRECAO; RES-SCL; trajetória e velocidades presentes; síntese não descreve o resultado como falta de dados, falha ou inexistência do fenômeno. Variante: série estável resulta motivo SERIE_ESTAVEL.

**AT-11 — Continuidade contextual (Caso 11).** Dado: linha de médicos. Quando: "Considere 2,36 por mil como parâmetro de referência nesta análise" e depois "Agora mostre os territórios abaixo do parâmetro de referência". Então: parâmetro com escopo na linha e nos objetos (médicos, densidade); reuso com âncora original e `recuperada_de`; operador "<" explicitado. Quando: "Agora faça o mesmo para enfermeiros". Então: mesma linha; parâmetro não aplicado; oferta de reutilização sem presunção. Variante: parâmetro dado sem escopo ("mostre os abaixo de 2,36 por mil") vale só para aquela solicitação, e a referência explícita posterior ("e os acima desse valor?") o reutiliza. Análise autônoma de enfermeiros abre nova linha; o retorno a médicos retoma a linha com reavaliação e reuso (DA-06).

**AT-12 — Alteração que invalida (Caso 12).** Dado: resultados produzidos com v1. Quando: o usuário carrega v2 e diz "substituí a base; refaça a densidade". Então: vínculos antigos NAO_VIGENTE e resultados VALIDO; recálculo sob v2 sem nova confirmação (DA-08). Quando: carrega v2 sem pedir recálculo. Então: impacto registrado, resultados afetados informados e reexecução oferecida. Quando: o usuário corrige o significado de campo usado (contava vínculos, não pessoas). Então: CORRECAO_OU_REPUDIO; dependentes INVALIDADO; fora do diagnóstico; presentes apenas na rastreabilidade.

**AT-13 — LLM indisponível antes da interpretação (Caso 13).** Então: C-02 informa por modelo, no idioma da sessão; nenhuma execução ANALITICA por tentativa nem análise iniciada por controle; upload pode produzir exame sob autorização HABILITADORA, com EV-EXAME, sem LLM; navegação e exportação continuam disponíveis. Dados conversacionais ainda não estruturados que dependam do LLM aguardam, sem interpretação improvisada (P-18, RQ-DEG-02). Este caso exige LLM antes de determinar o resultado necessário; não se confunde com AT-100, em que o resultado já válido permite atendimento em modo degradado. Durante espera em E1, StatusSolicitacao permanece EM_ADMISSAO; retorno na mesma sessão ativa retoma a mensagem e seleção capturadas após revalidar contexto. Expiração descarta a espera (AT-132/133).

**AT-14 — LLM indisponível após a execução (Caso 14).** Dado: todos os resultados necessários VALIDO, APRESENTAVEL e rastreáveis, com EV-RESULTADO registrado. Então: apresentação determinística por TPL-12 na ordem Resultado; Parâmetros e origens (incluindo interpretação e escala); Método e documentação [opcional, somente conteúdo autorizado aplicável]; Cobertura; Limitações; Situação dos entregáveis; Pendências. Omitir apenas blocos sem conteúdo aplicável. Após apresentação válida, ATENDIDO; tentativa de síntese recebe OPR-IND e EV-INDISPONIBILIDADE, sem INTERROMPIDO nem suspensão da solicitação apenas por isso. Estados agregados consideram outras pendências/entregáveis. Nenhuma nova síntese determinística nem retomada automática de síntese após restabelecimento.

**AT-15 — Sugestão (Caso 15).** Dado: análise territorial concluída com base de quatro ou mais períodos. Então: sugestão que referencia CAP-TMP-01 ou CAP-TEN-01 e a matriz de aplicabilidade; nenhuma execução antes do aceite; aceite pela conversação gera nova solicitação ancorada em EV-SUGESTAO-ACEITA.

**AT-16 — Proposta factual do LLM (Caso 16).** Dado: CFG-NOR vazio. Quando: "Quais territórios estão abaixo do adequado?". Então: pendência pedindo que o usuário defina o critério, sem valores atribuídos a organismo, estudo ou prática externa (V-01, V-03, V-10, P-05), sem opções criadas e com decisão, consequência e formato da resposta em formas governadas PT/EN. Saída simulada do LLM com valor recomendado de memória é rejeitada. Conteúdo registrado no RCNA seguido de "pode usar esse" tem a âncora rejeitada. Se o usuário definir o critério, a classificação é identificada como critério do usuário (AT-46); sem definição, nenhum resultado é qualificado como inadequado.

**AT-17 — Unidade elegível sem registro e quantis (Caso 17).** Dado: quadro com 100 unidades e registros para 92. Quando: "Quintis entre todas as unidades". Então: cortes Hyndman–Fan tipo 7 sobre as 92 avaliáveis, com valores iguais ao corte na classe inferior; 8 unidades NAO_AVALIAVEL (SEM_REGISTRO_OBSERVADO), listadas e não convertidas em zero; cobertura 92/100; RES-LIM. Verificação de fronteira: valores 3, 5, 7, 9, 11 em quartis têm cortes 5, 7 e 9 e classes Q1 {3, 5}, Q2 {7}, Q3 {9}, Q4 {11} (DA-11).

**AT-18 — Complemento com não avaliáveis (Caso 18).** Dado: parte do universo com menos de quatro observações. Quando: "Liste os territórios que não estão em tendência de declínio". Então: complemento igual ao conjunto NAO_ATENDE, com as classes de origem preservadas (família de crescimento e SEM_CLASSIFICACAO); não avaliáveis excluídos e listados à parte; síntese distingue os grupos.

**AT-19 — Conflito e substituição (Caso 19).** Dado: base com 48 mil habitantes para o território. Quando: o usuário informa "a população é de 52 mil", sem indicar substituição. Então: pendência CONFLITO_DE_FONTES antes do cálculo; nenhuma escolha silenciosa; resolução registrada com origem. Quando: "use 52 mil em vez do valor da base e refaça a densidade". Então: substituição explícita sem conflito; valor do usuário prevalece no escopo; base original inalterada; limitação VALOR_SUBSTITUIDO_PELO_USUARIO; recálculo sem nova confirmação (DA-03, DA-08).

**AT-20 — Seleção visual (Caso 20).** Dado: filtro visual aplicado ao mapa. Quando: "Qual é a mediana desses territórios?". Então: EV-CAPTURA-SELECAO; universo LISTA com origem SELECAO_DE_INTERFACE; mediana calculada (média dos dois valores centrais se o número for par); classes discretas exibidas no mapa, se houver, provenientes de capacidade (RQ-REP-02); o filtro, sozinho, não iniciou análise.

**AT-21 — Alteração durante composição (Caso 21).** Dado: composição em curso com tendência calculada sob v1. Quando: o usuário carrega v2 antes do subconjunto e das distâncias. Então: etapas dependentes SUSPENSA; pendência CONTINUIDADE_DE_COMPOSICAO; nenhuma etapa executada sob v2 com o resultado de v1; a reautorização recalcula a tendência sob v2; resultados sob v1 permanecem válidos e não vigentes; combinação de versões só como comparação explícita (RQ-ORQ-13). A configuração não muda durante a sessão (AT-52).

**AT-22 — Intermediário e componente (Caso 22).** Dado: plano com resultado usado apenas para alimentar etapa posterior. Então: papel SUPORTE_INTERMEDIARIO. Quando: "gere o diagnóstico". Então: somente componentes; intermediários apenas listados integralmente como disponíveis; nenhuma seleção pelo LLM. Quando o usuário aceita incorporar um intermediário: EV-AMPLIACAO e papel COMPONENTE_DIAGNOSTICO registrado.

**AT-23 — Evolução (Caso 23).** [INSP] Dado: proposta de capacidade de projeção. Então: RegistroMudanca com Q1 a Q10, contrato, método, dados, governança, rastreabilidade e validação proporcional; a nova versão só vale para novas sessões; até lá, pedidos de projeção recebem ADM-FE; nenhuma previsão textual pelo LLM.

**AT-24 — Outro setor (Caso 24).** Quando: "Analise a distribuição territorial de professores da rede estadual de educação básica". Então: NAO_PERTINENTE; nenhuma execução, ainda que a base tenha campos estruturalmente compatíveis; o agente não sugere declarar a categoria como FTS (RQ-GOV-32).

### 20.3. Cenários derivados de invariantes e regras

**AT-25 — Delegação genérica.** Dado: pendência de limiar. Quando: "você escolhe". Então: pendência mantida; explicação de que a decisão é do usuário; nenhum valor escolhido; opções apenas de CFG-OPC, com rótulos PT/EN governados.

**AT-26 — Exame habilitador.** Quando: introdução deliberada por upload ou pequeno conjunto de dados na conversa. Então: triagem antes de qualquer envio ao LLM; perfil com estrutura, períodos, territórios, categorias, consistência, duplicidades, ausentes, cobertura, semântica declarada e matriz de aplicabilidade; nenhum diagnóstico, ranking, classificação, tendência, comparação ou magnitude de indicador da FTS; nenhuma mensagem com achados (DA-02).

**AT-27 — Parâmetro não ancorado.** Dado: saída simulada de FN-INT-02 com limiar 3,0 ausente da mensagem e do estado. Então: âncora inválida; elemento rejeitado; até 2 regenerações; persistindo, pendência; EV-VALIDACAO-INTERPRETACAO registrado.

**AT-28 — Síntese não suportada.** Dado: texto simulado com "A tem o dobro de B" sem relação estruturada e "tendência de queda" sem resultado de CAP-TEN-01. Então: V-07 e V-05 violadas; até 2 regenerações; persistindo, modo degradado; texto rejeitado nunca exibido. Variante metodológica: rejeitar conteúdo fora de forma autorizada de CFG-DOC; após o limite, TPL-08 e fallback de AT-106, com método/fórmula/versão/condições no bloco opcional de TPL-12, parâmetros, cobertura e limitações nos próprios blocos, sem conteúdo novo.

**AT-29 — Representação analítica indevida.** Quando: pedido de mapa em quintis. Então: as classes vêm de CAP-DIS-02 (tipo 7, valores do corte na classe inferior); C-11 não calcula quebras; mapa com escala contínua é admitido; a escala não muda automaticamente conforme a magnitude.

**AT-30 — Rastreabilidade pendente.** Dado: C-13 indisponível no registro de EV-RESULTADO. Então: RASTREABILIDADE_PENDENTE; valor não exibido como resultado; restabelecido o registro, APRESENTAVEL.

**AT-31 — Resultado invalidado.** Quando: nova solicitação reutilizaria resultado INVALIDADO. Então: não há reuso; nova execução autorizada ou BLQ-DEP; referência ao invalidado apenas na rastreabilidade.

**AT-32 — Solicitação mista.** Quando: "Qual a densidade de X em A em 2024 e quem ganhou o campeonato?". Então: parte analítica executada; parte não pertinente registrada como entregável NAO_EXECUTAVEL com ADM-NP; status CONCLUIDA_PARCIAL; nenhum fato sobre a parte não pertinente.

**AT-33 — "Vazio significa zero".** Quando: o usuário declara que vazio significa zero. Então: AMB-03; se a resposta indicar semântica de codificação, VALOR_ZERO_CODIFICADO confirmado pelo usuário; se indicar tratamento de desconhecidos como zero, a conversão não é aplicada por falta de método autorizado (DA-10), e o agente PODE pedir os valores explícitos (DA-07).

**AT-34 — Dêitico temporal.** Dado: data corrente em 2026 e base até 2024. Quando: "densidade no último ano". Então: AMB-04; pendência com as leituras ancoradas na data corrente e no último período disponível; nenhuma escolha silenciosa. Variante em que as âncoras plausíveis coincidem: prossegue com interpretação explicitada. Variante em que o fuso ou offset da data corrente não pode ser estabelecido e a virada de data altera a leitura: pendência AMBIGUIDADE_MATERIAL (RQ-GOV-23).

**AT-35 — Capacidade temporariamente indisponível.** Dado: CAP-IND-02 marcada como temporariamente indisponível na disponibilidade operacional antes da solicitação. Então: ADM-SC com motivo TEMPORARIAMENTE_INDISPONIVEL, comunicado de forma simples. Variante: indisponibilidade detectada durante a execução gera OPR-IND e suspensão das etapas afetadas. Nenhuma estimativa pelo LLM; nenhuma confusão com ausência de dados (P-03).

**AT-36 — Empate no corte.** Dado: três unidades empatadas na 5ª posição. Quando: "os cinco maiores". Então: sete unidades selecionadas, com posições 1, 2, 3, 4, 5, 5, 5, N efetivo informado e limitação EMPATE_NO_CORTE; nenhum desempate. Quando: "exatamente cinco". Então: pendência EMPATE_NO_CORTE, por não haver regra de desempate autorizada (DA-18).

**AT-37 — Registros individualizados.** Dado: base com campo de CPF e campo ambíguo "codigo". Quando: upload. Então: triagem antes do LLM; CPF como IDENTIFICADOR_DIRETO, inclusive valores que falhem nos dígitos verificadores, que permanecem protegidos sem ser classificados como CPF válido (RQ-DAD-37); "codigo" como POTENCIALMENTE_IDENTIFICADOR, com pendência de significado; aviso de RQ-DAD-22 (TPL-10) exibido; base em AGUARDANDO_CONFIRMACAO e análise aguardando confirmação; visualizador com CPF mascarado; revelação só por ação do usuário no visualizador, sem efeito sobre o LLM ou sobre produtos. "Liste os profissionais do território A" recebe ADM-FE (EXC-09, EXC-10); contagens territoriais são admitidas; nenhuma saída analítica, evento ou contexto do LLM contém identificadores (DA-27).

**AT-38 — Pedido sobre o agente.** Quando: "Quais análises você faz?" e "De onde veio o 2,36?". Então: respostas por FN-META-01 a partir de CFG-FAM e do status das capacidades; ficha de procedência com a manifestação do usuário, o evento e o escopo. Para escolha concreta por precedência, consultar EV-REPRESENTACAO com valor, nível utilizado e origem/âncora; eventual bloco metodológico de TPL-12 não dispensa esse evento.

**AT-39 — Pergunta normativa e conceitual.** Quando: "Qual é a densidade ideal de médicos?". Então: o agente informa que não há critério normativo autorizado, não fornece valor de memória e PODE informar que o usuário pode definir critério para a própria análise, sem sugerir valor. Quando: "O que é densidade?". Então: resposta a partir de CFG-IND e CFG-DOC (DA-21).

**AT-40 — Reprodutibilidade.** Quando: a mesma solicitação, ou paráfrase, é executada duas vezes com as mesmas versões. Então: mesmo `hash_conteudo`; mesmos valores nas sínteses; variação apenas de redação. Variantes com uma ou várias etapas para o mesmo pedido preservam conteúdo analítico, avaliabilidade, identidade e quantidade semântica de entregáveis e estados agregados; IDs técnicos de etapas podem diferir. Conteúdo metodológico limita-se às formas autorizadas de CFG-DOC.

**AT-41 — Separabilidade.** Dado: denominador de B ausente e impossibilidade definitiva no contexto, sem pendência resolúvel aplicável nem processamento pertinente por concluir. Quando: o usuário pede relatórios autônomos de densidade de A e de B em 2024 e um terceiro entregável de comparação A × B. Então: A ATENDIDO; B NAO_EXECUTAVEL com BLQ-DAD; comparação NAO_EXECUTAVEL com BLQ-DEP e cadeia até B; solicitação CONCLUIDA_PARCIAL. Na mesma resposta, apresentar A, informar denominador ausente de B e dependência da comparação, sem resultado fictício. Havendo pendência resolúvel, aplica-se AT-91 e não se encerra. A autonomia vem do pedido, não da contagem de unidades ou etapas (RQ-GOV-28/29).

**AT-42 — Mudança de foco na linha.** Quando: a linha passa de médicos para enfermeiros. Então: parâmetros escopados a médicos ficam inativos e não são usados; o resultado de médicos passa a NAO_VIGENTE por DESLOCAMENTO_DE_FOCO, sem caráter histórico; ao retornar, os parâmetros são reativados após reavaliação e o resultado anterior, se compatível, volta a VIGENTE e é reutilizado sem reexecução (RQ-LIN-20).

### 20.4. Cenários derivados das decisões incorporadas

**AT-43 — Interação em inglês.** Quando: "What is the density of nurses in territory A in 2024?". Então: interpretação para os mesmos conceitos internos; resposta, perguntas e limitações em inglês; validador com léxico em inglês; mesmo conteúdo analítico da formulação em português; nenhuma troca silenciosa de idioma, inclusive nas mensagens do canal sistêmico, com os textos em inglês de CFG-TPL (DA-05). Termos sem correspondência governada em inglês (ex.: expressão equivalente a BIOMEDICINA) seguem interpretação candidata e esclarecimento no idioma da sessão, sem mapeamento criado pelo LLM (RQ-CFG-14, RQ-CFG-15). Modo degradado usa os sete blocos de TPL-12 e "Method and documentation" opcional quando pertinente, com formas EN autorizadas ligadas aos mesmos id_doc PT; preservar âncoras, estados, cobertura e limitações.

**AT-44 — Sessão temporária e exportação.** Então: aviso de RQ-FLX-19 exibido no início; relatório HTML e PDF com componentes, representações, síntese validada, parâmetros com origem, limitações, procedência e pendências, sem identificadores; CSV com valores em precisão integral, escala no cabeçalho e colunas de avaliabilidade; ao encerrar, bases e resultados descartados; outra sessão não acessa dados da anterior (DA-23, DA-24, DA-25). Quando houver apresentação degradada, preservar TPL-12 e seu bloco metodológico opcional aplicável, mesmas âncoras, alcance comparativo, árvore avaliada e estados, sem interpretação ou síntese nova. Encerrar sessão e inatividade de 1800 segundos descartam integralmente originais, aliases, contextos, pendências, resultados e conteúdo de eventos; fechar a interface não encerra imediatamente. Atividade automática não renova o prazo (AT-152–156).

**AT-45 — Agregado parcial.** Dado: conjunto de 10 territórios, 2 sem denominador. Quando: "densidade do conjunto". Então: densidade agregada igual ao quantitativo agregado dos 8 avaliáveis dividido pela soma de suas populações; limitação AGREGADO_PARCIAL com 8 incluídos e 2 fora, listados; o resultado não é apresentado como representativo dos 10; nunca média de densidades. Com unidade de contagem pessoa, o quantitativo agregado segue AT-54; suporte efetivo territorial/categorial e chaves populacionais são registrados por período, e a validade temporal é verificada em AT-69 (DA-16).

**AT-46 — Critério normativo do usuário.** Quando: "Nesta análise, considere insuficiente densidade abaixo de 1 por 1.000". Então: critério registrado (valor, operador, unidade, escala, classificação, origem, escopo); unidades abaixo classificadas como insuficientes, com indicação de que o critério é do usuário; demais sem classificação complementar; critério não aplicado em outra linha; segundo critério sobreposto com outra classificação gera pendência; a classificação autorizada permanece no diagnóstico e nas exportações, conforme AT-71 (DA-21).

**AT-47 — Arredondamento e escala.** Então: 1,234 → 1,23; 1,235 → 1,24; −1,235 → −1,24; valor 2,3549 frente ao limiar 2,35 exibido como 2,355; variação de 0,004 exibida como 0,004 e não como 0,00; contagens inteiras sem casas decimais. Escala: a indicada pelo usuário (ex.: por 100.000) prevalece; sem indicação, vale a escala configurada para o indicador; sem ambas, por 1.000 habitantes; nenhuma mudança automática de escala pela magnitude; valor integral disponível no detalhe e no CSV (DA-09, DA-20).

**AT-48 — Eletricistas e declaração de domínio.** Dado: base sem metadado nem declaração de domínio, com a categoria "eletricista", que não consta do vocabulário governado. Quando: "Analise a distribuição dos eletricistas". Então: NAO_RECONHECIDA; a solicitação não é tratada como declaração; PERTINENCIA_INCERTA e pedido de esclarecimento neutro. Quando: "Neste estudo, considere os eletricistas como parte da força de trabalho na saúde e analise sua distribuição". Então: declaração explícita registrada com escopo e pedido PERTINENTE. Dado: base declarada pelo usuário como base de FTS ("Esta base contém a força de trabalho em saúde"), com a categoria "eletricistas". Quando: "Analise os eletricistas". Então: PERTINENTE sem pergunta, pela declaração de domínio no escopo daquela base; nenhuma inferência de que eletricistas pertencem universalmente à FTS e nenhuma alteração da configuração (DA-04).

**AT-49 — Lógica composta.** Dado: A = ATENDE, B = NAO_AVALIAVEL, C = NAO_ATENDE. Então: A E B = NAO_AVALIAVEL; C E B = NAO_ATENDE; A OU B = ATENDE; C OU B = NAO_AVALIAVEL; NÃO B = NAO_AVALIAVEL; NÃO A = NAO_ATENDE; critérios sucessivos em ordens diferentes produzem o mesmo resultado; "above" e "acima de" mapeiam para o mesmo operador (DA-19). Árvore aninhada conserva cada condição, operador, atributo/caminho, parâmetros, CondicaoCriterio, operandos, estado, motivo e âncoras. Composto NAO_AVALIAVEL por dependência recebe DEPENDENCIA_NAO_AVALIAVEL e mantém causas específicas nos filhos; operandos não avaliáveis permanecem acessíveis mesmo quando outro é decisivo. Nenhum resultado lógico acima muda.

**AT-50 — Unidade de contagem e deduplicação.** Dado: base individualizada de vínculos sem identificador de pessoa. Quando: "quantas pessoas trabalham em A?". Então: resultado não apresentado como pessoas únicas (BLQ-MET); contagem de vínculos oferecida como análise distinta; nenhuma conversão entre unidades. Variante com identificador de pessoa autorizado, completo e com domínio de unicidade suficiente, mesmo sem coluna de quantidade: vínculos repetidos no mesmo município contam uma pessoa, presença em dois municípios conta em ambos, e a união conta uma pessoa no agregado (RQ-DAD-35, AT-60, DA-09, DA-16).

**AT-51 — Referencial geodésico.** Dado: coordenadas válidas sem referencial informado (a Configuração Inicial de Implementação não contém referencial padrão). Quando: pedido de distância. Então: pendência REFERENCIAL_GEODESICO; nenhuma distância calculada. Quando o usuário informa SIRGAS2000: distância geodésica em quilômetros, pela solução do problema inverso com o algoritmo de Karney sobre o elipsoide do referencial, com a limitação de distância geográfica direta; empates na referência mais próxima preservados; coordenadas fora da faixa como NAO_AVALIAVEL (COORDENADA_INVALIDA); campo com nome não reconhecido e valores válidos exige confirmação do usuário (DA-17). Variante com referencial informado fora do conjunto suportado em CFG-MET: BLQ-MET/METODO_NAO_INCORPORADO, nenhuma transformação, aproximação ou substituição; usos não espaciais continuam possíveis.

**AT-52 — Configuração congelada.** Dado: nova versão de configuração publicada durante a sessão. Então: a sessão mantém o snapshot inicial em todas as autorizações; a nova versão vale apenas para nova sessão; usuário e LLM não alteram configuração na conversa (DA-01).

**AT-53 — Classificação de tendência.** Dado: séries anuais. Então: 10, 11, 12, 14 → ACELERAÇÃO DO CRESCIMENTO; 10, 12, 14, 16 → CRESCIMENTO; 10, 14, 16, 17 → DESACELERAÇÃO DO CRESCIMENTO; 20, 18, 15, 11 → ACELERAÇÃO DO DECLÍNIO; 20, 12, 8, 6 → DESACELERAÇÃO DO DECLÍNIO; 10, 12, 12, 15 → CRESCIMENTO (intervalo com velocidade zero); 10, 12, 15, 17 → CRESCIMENTO (ritmo sem monotonicidade); 10, 12, 11, 13 → SEM_CLASSIFICACAO (MUDANCA_DE_DIRECAO); 5, 5, 5, 5 → SEM_CLASSIFICACAO (SERIE_ESTAVEL); três observações → NAO_AVALIAVEL (SERIE_INSUFICIENTE); observações 2018: 10, 2019: 12, 2021: 16, 2022: 18 → velocidades 2, 2, 2 e CRESCIMENTO, por normalização pelo tempo transcorrido (DA-15).

**AT-54 — Agregação com possível sobreposição.** Dado: base apenas com contagens de médicos por município, sem identificador e sem informação sobre sobreposição. Quando: "quantos médicos há no conjunto dos municípios A, B e C?". Então: a soma não é apresentada como número de pessoas únicas; pendência informa que as contagens dos componentes podem ser somadas, com possível dupla contagem, e que a contagem única depende de dados de deduplicação ou de informação do usuário, sem propor essa informação. Quando: "mesmo assim, some os municípios". Então: resultado SOMA_DOS_COMPONENTES, rotulado como soma das contagens dos componentes, com limitação SOMA_COM_POSSIVEL_DUPLA_CONTAGEM; síntese, tabela, relatório e CSV não o chamam de profissionais únicos (V-14, RQ-REP-14). Quando: "essas contagens correspondem a indivíduos únicos e não há profissionais repetidos entre os municípios". Então: premissa registrada com origem no usuário, escopo, conteúdo e impacto; agregado UNIDADES_DISTINTAS com FundamentoUnicidade PREMISSA_DO_USUARIO e limitação ADITIVIDADE_POR_PREMISSA_DO_USUARIO. Variante com identificador: agregado por deduplicação sobre a união, sem pergunta. A mesma lógica vale para a soma de médicos e enfermeiros quando uma pessoa pode pertencer às duas categorias (DA-07, DA-09, DA-16).

**AT-55 — Reconhecimento automático de categoria.** Dado: base sem declaração de domínio. Quando: "Analise a distribuição dos médicos". Então: "médicos" corresponde, após normalização, a alias de MEDICINA; FTS_INEQUIVOCA; PERTINENTE, com âncora em CONFIGURACAO_GOVERNADA; nenhuma pergunta sobre pertença. Variantes: "Medicos", "MÉDICAS" e "cirurgiao dentista" são reconhecidos pela normalização governada; "médico veterinário" não é reconhecido como MEDICINA, pois a correspondência considera a expressão completa (DA-04).

**AT-56 — Expressão ambígua.** Quando: "Analise os técnicos". Então: FTS_AMBIGUA. Candidatas são apenas as categorias da base compatíveis com a expressão segundo as correspondências governadas de CFG-DOM e CFG-VOC e as regras determinísticas de RQ-CFG-10. Se houver uma única candidata (ex.: apenas "Técnico de enfermagem"), o contexto resolve e a análise prossegue com a interpretação explicitada, sem pergunta; se houver mais de uma (ex.: "Técnico de enfermagem" e "Técnico em radiologia"), o agente pergunta qual categoria de técnicos está sendo analisada, com as candidatas como alternativas. Se a base tiver apenas categoria que pareça semanticamente relacionada, sem correspondência governada, o contexto não resolve e o agente pergunta. O LLM não cria equivalência nem escolhe a categoria (DA-04).

**AT-57 — Ausência de pergunta redundante.** Dado: upload de base sem declaração de domínio. Então: nenhuma pergunta obrigatória sobre o domínio após o upload; o perfil do exame informa o estado de reconhecimento das categorias. Quando: "densidade de enfermeiros e de dentistas em 2024". Então: FTS_INEQUIVOCA para ambas e nenhuma pergunta sobre pertença. Dado: o usuário declarou "Esta base contém a força de trabalho em saúde". Então: pedidos sobre qualquer categoria da base prosseguem sem pergunta de pertença. Dado: base sem declaração, com a categoria "psicólogo". Quando: "analise os psicólogos". Então: FTS_INEQUIVOCA (PSICOLOGIA), sem pergunta sobre pertença. Dado: base sem declaração, com a categoria "assistente social". Quando: "analise os assistentes sociais". Então: FTS_CONTEXTUAL sem âncora contextual, PERTINENCIA_INCERTA e pedido de esclarecimento, e não NAO_PERTINENTE (DA-04, P-22).

### 20.5. Cenários das correções comportamentais aprovadas

**AT-58 — Denominador conforme a dimensão agregada (AV-01).** Dado: M1 tem 10 médicos e 20 enfermeiros, população 10.000; M2 tem 5 médicos e 15 enfermeiros, população 5.000; mesmo período e populações territoriais aditivas. Nos casos sem sobreposição, unicidade é estabelecida por fonte autorizada. Então: médicos nos dois territórios = 15/15.000 × 1.000 = 1 por mil; duas categorias em M1 = 30/10.000 × 1.000 = 3 por mil; ambas as categorias nos dois territórios = 50/15.000 × 1.000, sem repetir população por categoria. Variante: 5 das pessoas de M1 estão nas duas categorias e a identidade permite deduplicação; união = 25 e densidade = 2,5 por mil, com P = 10.000. Soma das contagens pedida conscientemente = 30/10.000, rotulada SOMA_DOS_COMPONENTES com possível dupla contagem, sem multiplicar P. Chaves e suportes permitem reconstruir cada cálculo.

**AT-59 — Tabela larga simples (AV-02).** Dado: colunas território, medicos_2024, medicos_2026, populacao_2024, populacao_2026, com correspondências autorizadas de cabeçalhos e semântica de contagem estabelecida. Então: normalização para registros por território/categoria/período, com origem por célula e sem duplicação de população; a análise prossegue sem exigir reformatação manual. Variante com cabeçalhos "M24" e "M26" sem dicionário/regra: esclarecimento do significado antes da operação, sem inferência pelo LLM nem descarte dos dados.

**AT-60 — Registros de vínculos, pessoas e identidade (AV-02, AV-03).** Dado: nenhuma coluna de quantidade; cada linha representa vínculo; identificador autorizado identifica pessoa, é completo e único em toda a base. Pessoa A tem dois vínculos de médico em M1 e um em M2, B um em M1, C um em M2; A também é enfermeiro em M1. Então: médicos M1 = 2, M2 = 2; união municipal de médicos = 3; em M1, médicos = 2, enfermeiros = 1, união de pessoas = 2. Contagem de vínculos permanece distinta (3 vínculos médicos em M1). Pessoa presente em períodos diferentes é contada em cada período, sem total temporal implícito. Variante com código único somente dentro de município: deduplicação local permitida quando suficiente, mas união intermunicipal bloqueada sem correspondência autorizada. Identidade ausente não é silenciosamente removida nem convertida em pessoa adicional. Nenhum identificador chega ao LLM ou ao resultado.

**AT-61 — Arquivos auxiliares, cardinalidade e subtotais (AV-02).** Dado: arquivo FTS por município/categoria/ano, população com uma linha por município/ano, quadro territorial e geometria em arquivos separados, chaves e granularidades estabelecidas. Então: correspondência registrada; população compartilhada não multiplica o denominador nem a junção multiplica o numerador; capacidades compatíveis são habilitadas. Variantes: população duplicada para a mesma chave com valores conflitantes gera resolução antes do cálculo; chave territorial ambígua gera esclarecimento; junção muitos-para-muitos com multiplicação indevida é bloqueada; tabela com municípios, total estadual e subtotais de categoria não é somada integralmente. Se a distinção de níveis/totais não estiver estabelecida, a operação aguarda esclarecimento.

**AT-62 — Dimensões constantes (AV-02, AV-04).** Dado: tabela território/quantitativo/população e metadado "pessoas médicas, municípios, 2024", aplicável à base toda. Então: categoria, unidade, nível e período materializados internamente com origem no metadado, sem exigir colunas repetidas nem perguntar o já determinado. Variante com declaração explícita do usuário produz origem MANIFESTACAO_USUARIO. Nomes territoriais inequívocos no escopo podem sustentar análise local; nenhuma identidade oficial, região ou hierarquia é inventada.

**AT-63 — Pequeno conjunto de dados no chat (AV-02, AV-08).** Dado: "Brasília" estabelecida como território no estado aplicável da sessão, ou a mensagem a tipifica (ex.: "o município de Brasília") (RQ-DAD-38). Quando: "Brasília tinha 10 médicos em 2024 e 15 em 2026. A população era 3 milhões em 2024 e 3,1 milhões em 2026." Então: classificação como pequena base conversacional (RQ-DAD-40), identificação de dados, proposta estruturada, validação das associações e normalizações (3 milhões = 3.000.000), base temporária de origem DADOS_CONVERSACIONAIS_USUARIO, triagem e exame habilitador, sem cálculo substantivo espontâneo. Valores e relações mantêm âncora MANIFESTACAO_USUARIO; nenhum pedido de confirmação redundante. Em solicitação posterior de densidade, atendidas as pré-condições semânticas, usam-se Q = 10 e P = 3.000.000 em 2024, Q = 15 e P = 3.100.000 em 2026. Saída simulada do LLM que acrescente população, código oficial ou troque a associação entre anos e valores é rejeitada mesmo contendo números presentes na mensagem. Variante sem papel estabelecido para "Brasília": ENTIDADE_NOMINAL_AMBIGUA, conteúdo enviado ao LLM apenas com placeholder e pergunta determinística de CFG-PRV antes da materialização; resposta "território" autoriza a tipificação territorial no escopo aplicável. A posição nominal no padrão governado é reconhecida antes do LLM. Sem marcador/tipificação aplicável, proteger independentemente da capitalização ou familiaridade do nome; a resposta registra âncora e escopo, sem propagação universal.

**AT-64 — Mensagem mista e valor complementar (AV-02).** Dado: significado e identidade territorial estabelecidos. Quando: "Brasília: 10 médicos em 2024 e 15 em 2026; Goiânia: 8 em 2024 e 11 em 2026. Compare a mudança dos quantitativos." Então: funções DADOS e ANALITICO coexistem; o conjunto é habilitado e o pedido preservado para E2–E9, sem repetição pelo usuário; CAP-TMP-01 produz mudanças +5 e +3 e CAP-CMP-01 executa a comparação pedida, com diferença absoluta +2 entre as mudanças, sem nova confirmação. Variante: "Use população de 3 milhões para Brasília em 2024 e calcule a densidade" fornece valor complementar escopado, sem base artificial. Mensagem que responda a pendência e contenha novo pedido ou controle preserva ambos, resolvendo apenas conflitos materiais de aplicação.

**AT-65 — Conversação sem dados (AV-02, AV-08).** Quando: "Olá", "Obrigado" ou "O que você consegue fazer?". Então: proteção preliminar da mensagem; funções CONVERSACIONAL ou SOBRE_O_AGENTE, conforme o caso; resposta breve ou FN-META-01; nenhuma ingestão, base, CAP-EXA-01, linha ou análise criada. Pergunta hipotética que mencione números não é automaticamente convertida em base.

**AT-66 — Parâmetro único determinado (AV-04).** Dado: base autorizada contém apenas médicos em 2024 e o universo municipal pedido está determinado. Quando: "calcule a densidade nos municípios desta base". Então: C-04 verifica candidatos e escopo, resolve categoria/período com âncoras reais, sem pergunta e sem registrar falsa manifestação do usuário. Variante com dois períodos materialmente possíveis e nenhum estado/regra que resolva: esclarecimento. Variante com estado vigente e aplicável que fixa um deles: prossegue. "Use o que achar melhor" não cria pergunta se tudo já estiver resolvido nem resolve escolha ainda aberta.

**AT-67 — Comparação entre solicitações e contextos (AV-05).** Quando: "Analise o quantitativo de médicos em 2024", "Agora os enfermeiros", "Compare os dois". Dado: mesmo território, definição de quantitativo e unidade pessoa compatíveis. Então: referência contextual identifica os dois resultados, inclusive o anterior, deslocado por mudança de foco (NAO_VIGENTE por DESLOCAMENTO_DE_FOCO, sem caráter histórico, RQ-LIN-20); diferenças de categoria são a dimensão comparada; C-04 registra compatibilidade e os contextos de origem no novo contexto da comparação. CAP-CMP-01 usa os resultados existentes, sem recálculo para igualar contextos e sem transferir critérios locais. Variante entre linhas segue consolidação autorizada; variante pessoas × vínculos ou significados incompatíveis é bloqueada; versões distintas exigem que a diferença de versão seja objeto explícito. Mudança superveniente durante execução continua sujeita a suspensão (AT-21).

**AT-68 — Cobertura de referências espaciais (AV-06).** Dado: para U, distâncias às referências A = 100 km, B = 150 km e C não avaliável. Então: mínimo completo NAO_AVALIAVEL; mínimo entre avaliáveis = A, 100 km, com cobertura 2/3 e motivo de C; resposta nunca afirma que A é a mais próxima do conjunto completo. Filtro "> 90 km da referência mais próxima" recebe NAO_AVALIAVEL para U, não ATENDE; ordenação não lhe atribui posição pelo mínimo parcial. Pedido explícito da alternativa "entre as referências avaliáveis" permite filtro/ordenação nesse alcance, preservado nas saídas e dependentes. Variantes: nenhuma referência avaliável ou conjunto de referências vazio geram os motivos de CAP-ESP-02, sem distância zero, ausência de U ou RES-VAZ artificial; ausência de qualquer elemento avaliável gera BLQ-DAD. Variante (F-09, não incorporada): com distâncias avaliáveis A = 50 km e B = 150 km e C não avaliável, o mínimo completo seria necessariamente de no máximo 50 km, mas o filtro "> 90 km da referência mais próxima" permanece NAO_AVALIAVEL para U e não recebe NAO_ATENDE, pois não há método de inferência por limites (CAP-ESP-02).

**AT-69 — Agregados parciais e falsa trajetória (AV-07).** Dado: conjunto autorizado {M1, M2}, com suporte efetivo {M1} em 2020 (Q = 10) e {M1, M2} em 2021–2023 (Q = 30, 40, 50), por ausência em 2020. Então: quatro agregados isolados válidos, com coberturas e membros explícitos; CAP-TMP-01 entre 2020 e 2023 e CAP-TEN-01 sobre a série registram INCOMPARABILIDADE, sem crescimento ou aceleração, e sem escolher membros comuns. Representação pode mostrar valores isolados, não linha de trajetória do mesmo agregado. Variantes: mudança da composição categorial também é verificada; mesmos membros efetivos em todos os períodos permitem análise se as demais condições forem atendidas; mudança de pessoas presentes, mantendo o suporte territorial/categorial, não bloqueia por si só a análise.

**AT-70 — Habilitação antes de autorização analítica (AV-08).** Quando: upload estruturado ou conjunto conversacional validado. Então: autorização HABILITADORA identifica entrada e operações; a entrada passa de RECEBIDA a TRIADA; CAP-EXA-01 aceita a entrada TRIADA e produz perfil sem E9, plano ou linha; a base torna-se DISPONIVEL após exame e resolução das pendências habilitadoras (RQ-DAD-42). Nenhuma outra capacidade pode usar essa autorização. Pedido misto de análise só executa após E9; upload sozinho não gera análise. Variantes: significado indefinido é reportado, não impede o próprio exame; campos protegidos exigem confirmação antes da análise; upload pode ser examinado em modo degradado quando não depende de interpretação do LLM.

**AT-71 — Critério do usuário no diagnóstico (AV-09).** Dado: critério de AT-46 e resultado de CAP-SUB-01 autorizado como componente. Quando: "gere o diagnóstico". Então: classificação "insuficiente" preservada no diagnóstico, HTML/PDF/CSV, com valor 1, operador <, escala por 1.000, origem e escopo, explicitamente atribuída ao critério definido pelo usuário. CFG-NOR permanece vazio. Em outra categoria/linha fora do escopo, o critério não é reaplicado; consolidação relata a classificação nas condições originais, sem transformá-la em norma global.

**AT-72 — Função do conteúdo no validador (AV-10).** Dado: formas canônicas/templates pertinentes previamente autorizados em CFG-DOC e as âncoras abaixo. Então: pergunta ancorada em pendência "Você quer comparar dois períodos ou analisar a tendência?" e explicação contratual "A análise de tendência exige quatro observações válidas" são aprovadas sem resultado de CAP-TEN-01. Com perfil que registre três observações e evento de bloqueio, "Não foi possível analisar a tendência porque há apenas três observações válidas" também é aprovada. "Os médicos apresentam tendência de declínio" sem CAP-TEN-01 permanece rejeitada, inclusive se o LLM a etiquetar como EXPLICACAO_METODOLOGICA. Variantes equivalentes: pergunta sobre critério de insuficiência sem propor limiar; descrição da proibição de inferência causal; número de pré-condição documentado. Frases de pergunta citadas neste caso são o conteúdo do bloco Decisão; sua apresentação completa conserva as seis posições de TPL-04, o motivo documentado quando pertinente e as opções autorizadas, em ambos os idiomas. Nenhuma dessas permissões autoriza qualificação analítica ou fato sem âncora. Aceitação exige identidade, versão, forma, condições, dependências e interpolações verificadas; conclusão indevida também é rejeitada dentro de "Método e documentação", sem teste de equivalência semântica entre textos livres.

**AT-73 — Privacidade em dados conversacionais (AV-02, AV-03, AV-08).** Dado: mensagem com registros individuais estruturados de vínculos e identificador pessoal, acompanhados de pedido de contagem. Então: C-04 protege o conteúdo antes do LLM; C-10 pode ingerir os registros deterministicamente; o contexto recebe apenas estrutura sanitizada; aviso e confirmação de uso precedem análise, e identidade suficiente permite deduplicação interna. Original protegido não aparece em EV-MENSAGEM, proposta do LLM, produtos ou exportações; descarte ocorre ao fim da sessão. Variante de formato individualizado não reconhecido com segurança: conteúdo retido e pedido de esclarecimento sanitizado, sem enviá-lo ao LLM para tentar reconhecê-lo.

### 20.6. Cenários da incorporação F-01 a F-12 e da Configuração Inicial de Implementação

**AT-74 — Triagem de identificadores estruturados (F-01, CFG-PRV).** Dado: mensagem e arquivo com CPF de dígitos verificadores válidos; campo rotulado "CPF" com valor de 11 dígitos cujos dígitos verificadores falham; e-mail com sintaxe válida; telefone em campo "celular"; número "+55 61 99999-0000" em texto livre; número isolado de nove dígitos, sem marcador. Então: triagem determinística antes de qualquer envio ao LLM; CPF válido protegido como CPF; valor do campo "CPF" protegido sem ser classificado como CPF válido; e-mail protegido sem verificação da caixa postal; telefone do campo "celular" e forma internacional inequívoca protegidos; número isolado não classificado como telefone apenas pela quantidade de dígitos; o LLM recebe [CPF_1], [EMAIL_1], [TELEFONE_1] e demais placeholders, e o mesmo CPF repetido recebe o mesmo placeholder; o mapeamento fica restrito a C-10 e não aparece em eventos nem produtos; categorias, períodos e valores quantitativos não são protegidos apenas por existirem (RQ-DAD-37, RQ-DAD-39). CPF válido também exige dígitos não todos idênticos; 11111111111 não é CPF válido, mas rótulo pessoal governa proteção independentemente do formato. D13 preserva linguagem funcional não pessoal triada e minimiza metadados (AT-116–123).

**AT-75 — Entidade nominal ambígua (F-01, CFG-PRV).** Dado: nenhuma base ou estado estabelece o papel das expressões. Quando: "Compare Silva e Rio Branco em 2024." Então: as duas expressões recebem ENTIDADE_NOMINAL_AMBIGUA, permanecem protegidas e chegam ao LLM apenas como [ENTIDADE_PROTEGIDA_1] e [ENTIDADE_PROTEGIDA_2]; como a identidade é necessária à operação, C-02 apresenta, sem uso do LLM, a pergunta determinística de CFG-PRV para cada expressão por alias, com revelação do original somente no visualizador protegido por ação explícita do próprio usuário; saída simulada do LLM que classifique qualquer delas como território ou pessoa é desconsiderada. Resposta "território" autoriza a tipificação territorial no escopo aplicável e a análise segue os gates; resposta "pessoa" mantém a proteção, caracteriza entrada individualizada quando integrar dados e exige TPL-10; resposta "manter protegida" não autoriza uso de identidade ainda sem papel suficiente. Natureza confirmada não equivale a autorização de uso; operação individual permanece excluída. Variantes: "município de Rio Branco" é reconhecido como território pela construção tipificada; "Rio Branco" presente como território em base carregada, também; "hospital X" é tratado como entidade não pessoal; não se usa catálogo de cidades (RQ-DAD-38). Reconhecer os operandos nominais pela construção comparativa governada antes do LLM; capitalização isolada não decide proteção/liberação. Tipificação de outra base/versão/escopo inaplicável não libera a expressão. Delimitação insegura segue AT-104.

**AT-76 — Atributos exigidos pela operação (F-02).** Dado: base de médicos por território com população, sem metadado de aditividade territorial nem de compartilhamento populacional entre categorias. Quando: "Qual a densidade de médicos no território A em 2024?" Então: densidade calculada sem BLQ-SIG e sem pergunta sobre aditividade ou compartilhamento. Quando: "densidade de médicos em A e B juntos, como agregado". Então: exige-se a aditividade territorial pertinente da contagem e da população; indefinida, BLQ-SIG com pendência restrita a esse atributo. Quando: "densidade de médicos e enfermeiros juntos em A". Então: exigem-se a forma de uso do denominador entre categorias e o tratamento de sobreposição de CAP-AGR-01, sem exigir aditividade territorial (RQ-DAD-36).

**AT-77 — Mudança de foco, retorno e caráter histórico (F-03).** Quando: "Analise médicos em 2024" (R1); "Agora enfermeiros" (R2); "Volte aos médicos". Então: após R2, o vínculo de R1 é NAO_VIGENTE por DESLOCAMENTO_DE_FOCO, sem rótulo histórico; R1 permanece componente contemporâneo do diagnóstico e pode ser comparado com R2 por "compare os dois" sem pedido de uso histórico; no retorno, R1 volta a VIGENTE e é reutilizado sem reexecução nem duplicata (EV-REUSO). Variante: nova versão da base de médicos é carregada antes do retorno. Então: o vínculo de R1 é NAO_VIGENTE por SUBSTITUICAO_DE_ESTADO, com caráter histórico e rótulo correspondente; o retorno não o reativa; nova análise segue RQ-LIN-15; uso de R1 em comparação exige pedido de uso histórico identificável (RQ-LIN-20).

**AT-78 — Qualificadores obrigatórios (F-04).** Dado: `minimo_avaliaveis` com alcance "entre as referências avaliáveis"; agregado parcial com 8 de 10 territórios; resultado SOMA_DOS_COMPONENTES; resultado de CAP-ROT-01. Então: saídas simuladas do LLM que afirmem "a referência mais próxima é A", apresentem a densidade como do conjunto completo, falem em número de profissionais para a soma ou em "rotatividade de 30%" sem "da coorte inicial" são rejeitadas (V-15, V-14) e regeneradas; formulações que preservem o qualificador no segmento ou por referência inequívoca a segmento anterior são aceitas; relatório, CSV e modo degradado preservam os qualificadores (RQ-RES-11).

**AT-79 — Agregado multicategorial parcial (F-05a).** Dado: territórios M1, M2 e M3; médicos e enfermeiros avaliáveis em M2 e M3; em M1, médicos avaliáveis e enfermeiros NAO_AVALIAVEL. Quando: "densidade de médicos e enfermeiros juntos em M1, M2 e M3 em 2024". Então: M1 é NAO_AVALIAVEL para o agregado (DEPENDENCIA_NAO_AVALIAVEL); nem os médicos nem a população de M1 entram no cálculo; o agregado usa Q e P de M2 e M3, com a população de cada território contada uma vez; o resultado é identificado como parcial (AGREGADO_PARCIAL), com M1 e a categoria não avaliável identificados e motivados. Variante com território único M1: M1 não integra o agregado, sua população integral não é usada e, sem território incluído, aplica-se RQ-CAP-08 com a categoria não avaliável identificada.

**AT-80 — Compatibilidade temporal de agregados (F-05b).** Dado: agregado de médicos em A e B, com os mesmos membros efetivos, UNIDADES_DISTINTAS por deduplicação em 2020 e SOMA_DOS_COMPONENTES em 2021. Quando: "como mudou o total de médicos de A e B entre 2020 e 2021?". Então: cada agregado é válido isoladamente, com seu tipo; a mudança é NAO_AVALIAVEL (INCOMPARABILIDADE), com o componente divergente registrado; nenhuma variação, crescimento ou declínio é afirmado. Variantes: FundamentoUnicidade diferente (deduplicação e premissa do usuário), domínio de identidade, unidade de contagem, definição populacional ou versão de método diferentes produzem o mesmo desfecho; em CAP-TEN-01, INCOMPARABILIDADE; em CAP-CMP-01, verificação de RQ-ORQ-13. Quando nenhuma mudança for avaliável por essa incompatibilidade, o desfecho é BLQ-MET, preservando INCOMPARABILIDADE; não BLQ-DAD. Agregados isolados válidos são preservados; causa e componentes divergentes permanecem rastreáveis.

**AT-81 — Valor factual complementar e declaração semântica (F-06).** Dado: linha que analisa o território X. Quando: "Use população de 3 milhões para o território X em 2024."; depois "densidade de médicos em X em 2024"; depois "e de enfermeiros?". Então: VALOR_FACTUAL_COMPLEMENTAR associado a X/2024 e à solicitação/linha aplicável, sem base criada; usado nas duas solicitações, sem expirar ao fim da mensagem e sem uso para X em 2023. Variante sem linha analítica aplicável na manifestação: o valor permanece no objeto X/2024 da sessão; duas linhas distintas L1 e L2 que posteriormente analisem esse objeto com escopo compatível podem usá-lo, em qualquer ordem, com a mesma âncora original; o uso em L1 não preenche linha_id como proprietário, não transfere o valor, não o consome e não impede o uso em L2. Mudança para território Y, período 2023 ou categoria que altere o significado do valor impede o reuso; população territorial sem restrição categorial continua aplicável às categorias compatíveis. Restrição expressa, substituição ou invalidação é respeitada no escopo pertinente; encerrada a sessão, não há recuperação em outra sessão. Quando: "Esta base é de médicos de 2024." Então: DECLARACAO_SEMANTICA que estabelece categoria e período constantes da base como CONFIRMADO_PELO_USUARIO, sem criar base; alteração de significado já estabelecido segue RQ-DAD-08. Quando: "A tinha 10 médicos, B tinha 20 e C tinha 30 em 2024." Então: pequena base conversacional (RQ-DAD-32, RQ-DAD-40).

**AT-82 — Escopo de parâmetros e respostas (F-07).** Quando: "Analise médicos." → pendência de período exigida pela linha → "2023." → "Agora enfermeiros." Então: enfermeiros em 2023, sem nova pergunta de período; território e demais dimensões preservados; a mensagem isolada "2023" não reduz o escopo da resposta. Variante: "Para médicos, use 2023." → "Agora enfermeiros." Então: 2023 não é transferido, e o período de enfermeiros segue RQ-GOV-14. Variante: limiar estabelecido para a densidade de médicos não é aplicado a enfermeiros (Caso 11, AT-11) (RQ-LIN-07, RQ-LIN-19).

**AT-83 — Pendência habilitadora e análise concorrente (F-08).** Dado: upload com campos protegidos; exame concluído sobre a versão protegida; base em AGUARDANDO_CONFIRMACAO (TPL-10). Quando: "Qual a densidade de médicos em A?", antes da confirmação. Então: o agente reapresenta a pendência de confirmação existente, com decisão, elementos afetados e opções, registra a solicitação como dependente, sem pendência duplicada e sem bloqueio genérico; confirmado o uso, a base passa a DISPONIVEL e a solicitação retoma sem ser repetida (RQ-FLX-22). Variantes: autorização de uso negada, base BLOQUEADA e solicitação dependente não executada, com o motivo informado; parte separável que não dependa da base prossegue. Parte independente determinada percorre E7–E12 com autorização própria enquanto a solicitação permanece AGUARDANDO_USUARIO. Resposta resolve somente o ramo pertinente e descendentes efetivos, com reuso válido e sem reiniciar o concluído. Outra pendência conserva espera; última pendência resolvida com processamento restante segue a tabela de RQ-FLX-01. Recusa com resultado prévio só permite terminalidade depois de apuradas aplicabilidade e situação final. Planilhas independentes seguem AT-110/111. Reversão explícita da negativa na mesma sessão exige nova TPL-10; não reabre entregável terminal. Negativa elimina perfil/estrutura/contexto ativo, inclusive reconstrução histórica, reuso e sugestões (AT-124/125). Pergunta segue a ordem completa de TPL-04.

**AT-84 — Comparação genérica (F-10).** Dado: densidades de médicos em A e B em 2024, com universo {A, B} estabelecido na linha. Quando: "Compare A e B." Então: valores lado a lado, ordem e diferença absoluta; nenhuma razão nem diferença relativa. Quando: "Quantas vezes a densidade de A é a de B?" Então: RAZAO. Quando: comparação pedida com mais de uma delimitação territorial materialmente plausível e sem universo inequívoco na linha. Então: pendência AMBIGUIDADE_MATERIAL; nenhuma agregação territorial silenciosa. Com três ou mais objetos: valores e ordem do conjunto avaliável, sem diferenças automáticas dos pares, mesmo se restarem dois avaliáveis. Pares e diferenças expressamente pedidos são respeitados. Contra referência: x − r, igualdade/ordem; "em relação" não implica percentual; "entre si e com referência" inclui ambos os alcances. Não converter DIFERENCA_ABSOLUTA em módulo nem gerar ranking não pedido.

**AT-85 — Associação de dados conversacionais (F-11).** Quando: "A e B tinham 10 e 20 médicos, respectivamente, em 2024." Então: associação por posição aceita. Quando: "A: 10; B: 20". Então: pares explícitos aceitos. Quando: "A e B tinham 10 e 20 médicos em 2024.", sem padrão autorizado que determine uma única associação. Então: esclarecimento, sem escolha pelo sistema. Saída simulada do LLM que associe A a 20 é rejeitada na validação contra o texto original protegido (RQ-DAD-31, RQ-DAD-41).

**AT-86 — Numerais e explicações metodológicas (F-12).** Dado: resultado com três territórios não avaliáveis. Então: "três territórios não foram avaliados" é aceito por corresponder ao valor ancorado; "dois territórios" é rejeitado (V-01); "uma análise de tendência exige observações válidas" não aciona validação numérica por "uma" como artigo; "um território não foi avaliado" é rejeitado quando o valor ancorado não é exatamente um. Quando: "Como é calculada a densidade?" Então: a resposta utiliza texto canônico ou template previamente autorizado da proposição com âncora DOC: de CAP-IND-02, com condições e interpolações verificadas, e é aceita; formulação que acrescente justificativa não documentada (ex.: "porque é o padrão internacional") ou regra geral derivada de regra local é rejeitada por V-16, ainda que sem palavras-chave vedadas; sem proposição ancorada, informa-se DOCUMENTACAO_INSUFICIENTE. Variantes numéricas PT/EN: `10` normaliza como dez; `10,5` e `10.5`, em construção decimal inequívoca, normalizam como dez e meio; `1,234` ou `1.234` com leituras plausíveis de decimal e milhar geram AMBIGUIDADE_MATERIAL em ambos os idiomas, sem conversão antes da resposta. Trocar somente o idioma não resolve a pendência. "one territory" exige âncora exatamente igual a um; "a method" e "an analysis" não criam literais. Variantes documentais: duas materializações da mesma versão produzem os mesmos IDs, textos, tipos, condições e dependências; caminho não cadastrado, fonte inexistente, ID duplicado, trecho divergente ou referência órfã impedem aceitar o registro como vigente. Texto que suprima uma condição, acrescente fato, justificativa, método ou critério, ou generalize uma regra local é rejeitado pela governança, mesmo que o LLM declare conformidade; falha segue RQ-SIN-05. A apresentação EN preserva a mesma proposição PT e não cria outro ID; textos fixos EN continuam sendo os de CFG-TPL/CFG-PRV. Ausência de proposição pertinente gera DOCUMENTACAO_INSUFICIENTE; nenhuma entrada é criada na sessão. Alteração da fonte ou dos vocabulários exige nova versão e regeneração do registro, sem modificar o snapshot de sessão em andamento. Apresentar a mesma proposição no bloco "Método e documentação" não cria ID, não dispensa condições/versões/âncoras e não permite tradução livre; formas EN são previamente autorizadas. As três proposições adicionadas na rodada histórica v1.2.2 foram CAP-CMP-01.avaliabilidade, CAP-SUB-01.avaliabilidade e CAP-SUB-01.saida. Na v1.2.4, conservar seus IDs, as fontes auxiliares e TPL-13 incorporados por D13–D28 e as enumerações aprovadas por D35, D38 e D40, segundo o mapa recalculado, sem duplicação normativa; formas e rótulos residem no catálogo externo (AT-178). Motivo documentado opcional usa UsoDocumental e formas literais PT/EN; pergunta respeita todas as posições de TPL-04 e não cria linha fictícia (AT-134–137/157).

**AT-87 — Sinais de exclusão (CFG-EXC).** Quando: "O que causou a queda de médicos em A?" Então: sinal de EXC-03; incidência estabelecida pela rechecagem; ADM-FE (EXC-03). Quando: "Calcule a densidade de médicos em A usando a população do mesmo período, devido à revisão da base." Então: o sinal "devido a" é detectado e rechecado, a intenção é de cálculo de densidade e a solicitação prossegue, sem recusa automática. Quando: "Qual será o número de médicos em 2030?" Então: ADM-FE pelo gate de admissibilidade, sem depender de sinal lexical (RQ-GOV-08, RQ-GOV-09, RQ-ESC-13).

**AT-88 — Categorias da Configuração Inicial (CFG-DOM).** Então: "analise os psicólogos" e "analyze physicians" resultam em FTS_INEQUIVOCA, sem pergunta de pertença; "analise os assistentes sociais" sem âncora contextual resulta em PERTINENCIA_INCERTA e esclarecimento, nunca NAO_PERTINENTE, e a mesma expressão com base declarada como da força de trabalho em saúde resulta em PERTINENTE; "ACS" com outra leitura materialmente plausível no contexto gera esclarecimento (RQ-CFG-13); "agentes comunitários de saúde" e "técnicos de enfermagem" resultam em FTS_INEQUIVOCA; "técnicos", isolado, em FTS_AMBIGUA (AT-56); expressão inglesa equivalente a BIOMEDICINA resulta em NAO_RECONHECIDA, sem alias criado pelo LLM (RQ-CFG-09, RQ-CFG-11).

**AT-89 — Entrada por arquivo e limites de materialização (CFG-FON).** Então: CSV com separador ponto e vírgula inequívoco tem estrutura estabelecida sem pergunta; CSV cuja estrutura admite vírgula e ponto e vírgula com resultados materialmente distintos gera ESTRUTURA_DE_ENTRADA, sem escolha pelo sistema; XLSX com duas planilhas utilizáveis e pedido sem indicação apresenta as planilhas para escolha; conjunto na conversa materializável integralmente é aceito sem limite metodológico de linhas; conjunto que excede o limite técnico não é truncado, amostrado ou analisado parcialmente como completo — a entrada fica BLOQUEADA, a limitação é informada e orienta-se o envio por arquivo estruturado (RQ-DAD-42, RQ-DAD-43). Selecionar ambas não concatena: finalidade independente inequívoca gera duas bases e exames; intenção de combinar exige regra determinada e RQ-DAD-30; leituras plausíveis diferentes exigem esclarecimento específico. Dados_2023/Dados_2024 não estabelecem período, série ou identidade longitudinal. Abas são oferecidas por aliases sem leitura semântica das não selecionadas. Fonte auxiliar exige seleção/papel/vínculos. Materialização impossível usa TPL-13 e motivo MATERIALIZACAO_INTEGRAL_IMPOSSIVEL, com pedido preservado; arquivo substituto é nova entrada, retomada só após associação/habilitação (AT-145/146/161).

**AT-90 — Rotatividade no fluxo conversacional (CAP-ROT-01, CFG-VOC).** Dado: base individualizada DISPONIVEL, com identidade longitudinal válida e registros de 2022 e 2024. Quando: "Qual a rotatividade da coorte inicial de médicos em A entre 2022 e 2024?" Então: CAP-ROT-01 com t0 = 2022 e t1 = 2024, saída estruturada mínima do contrato e síntese com o qualificador "da coorte inicial". Quando: "Qual a rotatividade de médicos em A?" Então: o termo isolado não aciona CAP-ROT-01 sem aceite ou contexto autorizado; esclarecimento sobre o método incorporado e, se necessário, sobre t0 e t1. Quando: "What is the turnover of nurses?" Então: sem correspondência determinística; interpretação candidata e esclarecimento em inglês. Variantes: "compare a rotatividade da coorte inicial de 2020–2022 com a de 2022–2024" compõe duas execuções e CAP-CMP-01; "a rotatividade está aumentando?" recebe ADM-SC METODO_NAO_INCORPORADO; "por que saíram?", ADM-FE (EXC-03); "liste quem saiu", ADM-FE (EXC-09, EXC-10); base sem identificador individual autorizado, BLQ-MET; t1 igual ou anterior a t0, BLQ-INF. Variantes A, B e A+B seguem a identidade semântica validada de AT-113/114/115; não alterar períodos, coorte, identidade, exclusões, métodos nem a proibição de taxa parcial do conjunto.

### 20.7. Testes mínimos de CAP-ROT-01

Nos testes, letras designam pessoas pela identidade autorizada, usada apenas internamente.

**ROT-AT-01 — Caso básico.** C0 = {A, B, C, D, E}; C1 = {A, B, C, X, Y}. Então: N0 = 5; N_permanentes = 3; N_saidas = 2; rotatividade da coorte inicial de 40%; permanência de 60%; X e Y não entram no denominador.

**ROT-AT-02 — Todos permanecem.** C0 = {A, B, C}; C1 = {A, B, C, D}. Então: rotatividade de 0%; permanência de 100%; D não entra no denominador.

**ROT-AT-03 — Ninguém permanece.** C0 = {A, B, C}; C1 = {D, E, F}. Então: rotatividade de 100%; permanência de 0%.

**ROT-AT-04 — Reentrada.** A está presente em t0, ausente em período intermediário e presente em t1. Então: A é permanente em CAP-ROT-01.

**ROT-AT-05 — Identidade insuficiente.** Há registros potencialmente pertencentes à coorte sem identidade longitudinal suficiente. Então: a unidade afetada é NAO_AVALIAVEL (DEPENDENCIA_NAO_AVALIAVEL, detalhe IDENTIDADE_LONGITUDINAL_INSUFICIENTE); nenhum registro é descartado silenciosamente.

**ROT-AT-06 — Registros repetidos.** A mesma pessoa aparece em múltiplos registros no mesmo período. Então: é contada uma vez após a deduplicação autorizada.

**ROT-AT-07 — Conjunto sem agregado parcial de coorte.** A mesma pessoa aparece em dois componentes territoriais ou categoriais do conjunto solicitado. Então: é contada uma única vez somente quando a identidade longitudinal é válida no domínio da união; calculam-se as taxas da coorte da união, sem soma nem média das taxas individuais. Sem essa validade: taxa do conjunto NAO_AVALIAVEL, DEPENDENCIA_NAO_AVALIAVEL com detalhe IDENTIDADE_LONGITUDINAL_INSUFICIENTE. Variante: componente A avaliável e componente B com identidade insuficiente; A pode ser apresentado separadamente, B e o conjunto permanecem não avaliáveis; não se redefine o conjunto como A. Variante: B não avaliável por SEM_REGISTRO_OBSERVADO, DADO_AUSENTE ou DENOMINADOR_ZERO; o conjunto é NAO_AVALIAVEL, e o motivo próprio é preservado com o componente afetado, sem atribuir causa de identidade. B com coorte vazia estabelecida não é silenciosamente retirado, mesmo quando A tem N0 positivo. Síntese, tabela, mapa, relatório e exportação não apresentam o resultado de A como taxa do conjunto A+B. Contraprova: CAP-AGR-01 continua produzindo o agregado parcial autorizado, com seu suporte e limitações explícitos (AT-79), sem importar a vedação exclusiva de CAP-ROT-01.

**ROT-AT-08 — Privacidade.** Então: identificadores são usados internamente; nenhum identificador ou registro individual alcança o LLM, eventos ou qualquer produto analítico (RQ-PRV-10).

**ROT-AT-09 — Coorte vazia.** N0 = 0. Então: contagens iguais a zero registradas; taxas percentuais NAO_AVALIAVEL por DENOMINADOR_ZERO.

### 20.8. Métricas

| Métrica | Definição | Camada | Uso |
|---|---|---|---|
| M-01 | Pertinência: matriz de confusão das três classes; destaque para NAO_PERTINENTE classificado como PERTINENTE | L3 | Acompanhamento; erros materiais registrados (RQ-QUA-04) |
| M-02 | Admissibilidade: exclusões não detectadas e famílias incorretas | L3 | Acompanhamento; erros materiais registrados |
| M-03 | Exatidão estrutural da interpretação: proporção de campos corretos (entregáveis, objeto, universo, períodos, parâmetros, modo, ação de linha) | L3 | Acompanhamento; erros materiais registrados |
| M-04 | Revocação de ambiguidade material: casos com leituras de assinaturas distintas em que a pendência foi criada | L3 | Acompanhamento; erros materiais registrados |
| M-05 | Perguntas desnecessárias: pendências criadas quando o corpus indica leitura determinada | L3 | Acompanhamento |
| M-06 | Planos válidos na primeira proposta | L3 | Acompanhamento |
| M-07 | Sensibilidade do validador: violações detectadas no corpus adversarial, por regra e por idioma | L4 | 100% no corpus (invariante crítico) |
| M-08 | Saídas em modo degradado por falha de validação | L5 e operação | Acompanhamento |
| M-09 | Fidelidade entre executado e autorizado | L2 e L5 | 100% (invariante crítico) |

---

### 20.9. Cenários da remediação v1.2.2 e regressão dirigida

Os cenários abaixo são critérios documentais de aceite, não declarações de execução de testes de sistema. As variantes integram os mesmos IDs e não criam nova numeração. Dados, intenções e pré-condições não objeto de falha de cada cenário devem ser autorizados e válidos no escopo.

**AT-91 — Execução parcial com pendência.** Dois entregáveis autônomos atendidos; terceiro PENDENTE; solicitação AGUARDANDO_USUARIO; ciclo independente E7–E12; pergunta pertinente em TPL-04, com opções e rótulos governados quando houver conjunto autorizado; retomada restrita após resposta.

**AT-92 — Referência e alcance comparativo.** Em pedido comparativo ancorado, “em relação à referência 2,36” produz igualdade/ordem e x − 2,36; nenhum percentual automático.

**AT-93 — Referência como critério.** “Abaixo de 2,36” aciona CAP-SUB-01 com `<`, lógica trivalente e nenhuma substituição por comparação simples.

**AT-94 — Chave longitudinal em escala.** Milhares de territórios com significado autorizado; correspondência determinística sem perguntas individuais.

**AT-95 — Chave sem significado longitudinal.** Códigos repetidos não bastam; pendência de campo/esquema; resposta aplicável resolve correspondências em massa.

**AT-96 — Exceção territorial localizada.** Ruptura afeta somente unidades e períodos pertinentes; demais comparações preservadas.

**AT-97 — Comparação parcial e reformulação.** A e C avaliáveis, B não; mesmo conteúdo e desfecho comparativo entre formulações; causa de B explícita; nenhuma diferença adicional não pedida.

**AT-98 — Árvore e causa de critério composto.** Densidade ATENDE; distância NAO_AVALIAVEL/SEM_INFORMACAO_ESPACIAL; E NAO_AVALIAVEL/DEPENDENCIA_NAO_AVALIAVEL; causas e operandos acessíveis.

**AT-99 — Encerramento parcial definitivo.** Pelo menos um ATENDIDO e outro definitivamente NAO_EXECUTAVEL ou INTERROMPIDO; nenhuma pendência nem processamento pertinente; CONCLUIDA_PARCIAL.

**AT-100 — Resultado válido e LLM indisponível somente na síntese.** Apresentação degradada; entregável ATENDIDO; OPR-IND e EV-INDISPONIBILIDADE para a tentativa; solicitação não suspensa só por isso; nenhuma síntese automática posterior.

**AT-101 — LLM indisponível antes de etapa necessária ao resultado.** Suspensão ou impedimento conforme contrato; nenhuma intenção presumida; partes determinísticas independentes preservadas; distinção explícita de AT-100.

**AT-102 — “Vitória tinha 10 médicos em 2024” sem tipificação.** Reconhecimento da posição de entidade, ENTIDADE_NOMINAL_AMBIGUA, proteção e placeholder antes do LLM.

**AT-103 — Mesma estrutura com “o município de Vitória”.** TERRITORIO reconhecido pelo marcador; nenhuma pendência de natureza da entidade; demais verificações permanecem.

**AT-104 — Posição de entidade com delimitação insegura.** Retenção do conteúdo incerto e esclarecimento conservador; nenhum envio em claro.

**AT-105 — Explicação por CFG-DOC.** Proposição vigente, condições e dependências verificadas; texto canônico/template; interpolações ancoradas; nenhuma equivalência semântica livre exigida de C-04.

**AT-106 — Falha da composição textual metodológica.** Texto rejeitado não exibido; fallback estruturado determinístico com conteúdo autorizado por CFG-DOC. Método, fórmula, versão, condições e referências documentais aplicáveis podem ser apresentados no bloco opcional “Método e documentação” de TPL-12. Parâmetros e origens permanecem em seu bloco; cobertura e limitações, nos respectivos blocos. Nenhum conteúdo substantivo novo é produzido. Em EN, usar forma EN literal do mesmo id_doc; ausência/incompatibilidade usa mensagem governada de insuficiência, nunca tradução livre (AT-162).

**AT-107 — Precedência da escala.** Variantes usuário, configuração e fallback; evento registra nível utilizado e âncora; explicação posterior usa o registro.

**AT-108 — Referencial geodésico suportado.** Operação prossegue com referencial informado, método e parâmetros autorizados; nenhum padrão inferido. Os quatro aliases aprovados, variantes de caixa e espaços externos convergem a SIRGAS2000/GRS80 com a = 6378137 m e 1/f = 298.257222101; não inferir EPSG ou transformar CRS (AT-143/144).

**AT-109 — Referencial informado não suportado.** BLQ-MET com motivo metodológico existente; nenhuma transformação, aproximação ou substituição; base utilizável em capacidades independentes.

**AT-110 — Duas planilhas como entradas independentes.** Intenção independente estabelecida; duas materializações e exames, origens próprias, nenhuma concatenação. Variante “use as duas” sem contexto suficiente gera esclarecimento. Planilhas não selecionadas não fornecem significado; fonte auxiliar selecionada possui origem, papel e escopo próprio (AT-145/146).

**AT-111 — Pedido de combinar duas planilhas.** Aplicar RQ-DAD-30; combinar somente com regra autorizada determinada; múltiplas combinações plausíveis geram pendência. Finalidade de combinação não é inferida do papel DADOS_ANALITICOS/FONTE_AUXILIAR_DE_METADADOS; preservam-se seleção, vínculos e triagem (AT-146).

**AT-112 — UNIDADES_DISTINTAS em 2022 e SOMA_DOS_COMPONENTES em 2024.** Mudança NAO_AVALIAVEL, motivo INCOMPARABILIDADE, desfecho BLQ-MET; não BLQ-DAD; agregados isolados preservados.

**AT-113 — Um objetivo de rotatividade aplicado a A, B e A+B.** Um entregável semântico; A válido e B/A+B não avaliáveis podem produzir RES-LIM; nenhuma coorte agregada parcial.

**AT-114 — Relatórios autônomos de A, B e A+B.** Entregáveis semanticamente separados; estados próprios; terminalidade sobre esses entregáveis após condições de encerramento.

**AT-115 — Uma etapa versus várias etapas para o mesmo pedido.** Mesmo conteúdo analítico, avaliabilidade, granularidade semântica, StatusEntregavel e StatusSolicitacao. Identificadores técnicos de etapas podem diferir. Retirada parcial/total conserva a invariância e segue D17-A; suporte compartilhado permanece válido e conjunto vigente vazio não produz conclusão por vacuidade (AT-129/163).

#### Variantes obrigatórias

**Estados, retomada e indisponibilidade:**

- Ciclo completo E7–E12 independente durante AGUARDANDO_USUARIO.
- Resolução de uma entre várias pendências.
- Última pendência resolvida com interpretação, autorização ou execução restante.
- Suspensão de uma etapa coexistindo com pendência aplicável.
- Desaparecimento da última pendência sem encerramento antecipado.
- Resposta insuficiente que não resolve a pendência.
- Declínio ou perda de aplicabilidade com resultados prévios.
- Todos atendidos, nenhum atendido e cancelamento explícito.
- Complemento de informação versus correção de contexto utilizado.
- Modo degradado durante espera por outra pendência.
- Restabelecimento do LLM sem síntese automática do entregável já atendido.
- Pedido posterior explícito de síntese, com contexto reavaliado.
- Resultado não apresentável ou com rastreabilidade pendente, ao qual D6 não se aplica.
- Presença ou ausência do bloco metodológico opcional sem alterar os estados e as condições de atendimento de D6.

**Comparação e referência:**

- Dois objetos; três ou mais; pares explícitos; entre si; contra referência; ambos os alcances.
- Percentual e razão explícitos.
- Referência zero e precisão junto ao limiar.
- Ausência de ranking automático.
- Um território e uma referência como operandos.
- Nenhuma relação avaliável.
- Relação que exige objeto indisponível.
- Causa proveniente de resultado parcial versus etapa bloqueada.
- Incompatibilidade metodológica e falha operacional sem conversão em dado ausente.

**Semântica territorial e critérios:**

- Chave composta, duplicidades e cardinalidade inválida.
- Regra fora do escopo de base, versão ou período.
- Fusões, desmembramentos e mudanças de esquema.
- Agregados com chave válida, mas suporte ou método incompatível.
- E com NAO_ATENDE e NAO_AVALIAVEL.
- OU com ATENDE e NAO_AVALIAVEL.
- NÃO de NAO_AVALIAVEL.
- Árvores aninhadas e múltiplas causas específicas.
- Critérios sucessivos em ordens equivalentes.
- Ausência total de avaliáveis com registros preservados, sem resultado fictício.

**Privacidade e documentação:**

- Capitalização alterada sem mudar a proteção estrutural.
- Nome conhecido pelo senso comum, mas sem tipificação autorizada.
- Tipificação válida em um contexto e inaplicável em outro.
- Mesmo marcador governado em PT/EN.
- Conteúdo metodológico com condição omitida, versão errada ou variável sem âncora.
- Explicação geral de pré-condição versus afirmação sobre sua ocorrência concreta.
- Tentativa de introduzir conclusão analítica em segmento metodológico.
- Apresentação EN vinculada à mesma proposição PT.
- Falha de validação sem exposição do texto rejeitado.
- Fallback metodológico com método, fórmula, versão, condições e referências documentais autorizadas em “Método e documentação”.
- Fallback sem conteúdo metodológico ou operacional aplicável, com omissão do bloco opcional.
- Parâmetros, origens, cobertura e limitações mantidos em seus blocos próprios.
- Bloco opcional na terceira posição, preservando a ordem relativa de TPL-12.
- Tentativa de inserir justificativa, generalização, inferência não ancorada ou paráfrase livre no bloco opcional, com rejeição pelos controles existentes.
- Formas PT/EN do bloco vinculadas às mesmas proposições, sem novos IDs motivados apenas pela localização da apresentação.
- Explicação de escala apoiada no valor, nível e âncora registrados em EV-REPRESENTACAO, sem inferência por ausência.

**Planilhas e espacialidade:**

- Seleção múltipla com intenção independente inequívoca.
- Seleção múltipla ambígua.
- Combinação inequívoca com chaves válidas.
- Combinação com cardinalidade indevida ou significado ausente.
- Nomes de planilhas sugerindo períodos sem autoridade suficiente.
- Referencial ausente, suportado, não suportado e mistura que exigiria transformação não incorporada.
- Lista de suportados apresentada sem sugerir identidade dos dados.

#### Regressão dirigida

| Grupo | Cenários | Propriedades preservadas |
|---|---|---|
| Ausência, precisão e conjuntos | AT-08/17/18/33/47/68 | Ausência distinta de zero/falso; complemento; precisão integral; restrições espaciais. |
| Temporalidade e agregação | AT-09/10/45/53/54/58/69/79/80 | Fórmulas, mínimos, aditividade, suporte, sobreposição e compatibilidade; AT-80 recebe a precisão causal. |
| Estado, escopo e reuso | AT-11/12/19/21/31/32/52/67/76/77/81/82 | Correção versus substituição, vigência, escopo, configuração congelada e reuso legítimo. |
| Autoridade, apresentação e privacidade | AT-04/06/13/14/22/27/28/30/37/38/43/44/70/72/74/75/78 | Autorizações, papéis, proteção, rastreabilidade e validação, com harmonizações identificadas; bloco metodológico sem efeito sobre estados ou autoridade. |
| Documentação e fallback metodológico | AT-86/105/106/107 | Conteúdo canônico/template; bloco opcional de TPL-12; distribuição dos campos; precedência concreta; mesma proposição PT/EN; nenhuma análise nova. |
| Robustez e rotatividade | AT-40/90; ROT-AT-01–09 | Determinismo, identidade pessoal, coorte original, qualificadores e ausência de agregado parcial. |

#### Verificações documentais

- Preservação textual dos corpos históricos, separando notas posteriores.
- Atribuição de D1–D12 e da precisão D8/TPL-12 exclusivamente à rodada de §25.8.
- Regras vigentes distintas dos registros históricos.
- Ausência de referências operantes a formulações substituídas.
- Coerência entre matriz, normas, modelos, testes e proposições.
- TPL-12 com sete blocos em toda descrição completa, sem estrutura concorrente.
- “Método e documentação” identificado como opcional e condicionado a conteúdo aplicável.
- Ausência de novo template independente, tipo de fonte ou proposição criada apenas pela mudança de bloco.
- AT-106 coerente com a estrutura de TPL-12 e os controles de D8.
- IDs únicos e referências resolvidas.
- Contagens vigentes recalculadas sem reescrever contagens históricas.
- Duas materializações documentais idênticas da mesma versão.
- CONCEPT integralmente inalterada.

---

### 20.10. Cenários de D13–D28, D17-A e H1–H3

Cenários originados na v1.2.3 e conservados na reconstrução v1.2.4, a executar na validação comportamental posterior; esta publicação documental não declara testes de runtime realizados. Aplicar variantes PT/EN aos casos de interpretação, perguntas e apresentação. Os controles positivos de D13 incluem linguagem funcional não pessoal não enumerada integralmente em CFG-VOC.

| ID | Cenário e resultado obrigatório |
|---|---|
| AT-116 | Nome pessoal em frase com CPF válido: CPF e trecho pessoal/nominal sujeito à proteção não chegam em claro a qualquer FN, evento ou produto. A instrução funcional não pessoal da mesma frase permanece interpretável após triagem, sem exigir sua tipificação como entidade. |
| AT-117 | Nome pessoal sem CPF em metadado textual não governado e semanticamente desnecessário: alias aplicado sem depender de aparência de nome; texto funcional não pessoal do pedido é preservado. |
| AT-118 | Nome de campo potencialmente nominal: LLM recebe alias e estrutura; significado só é estabelecido por fonte/declaração autorizada. A instrução não pessoal que indica como utilizar o campo pode chegar ao LLM após triagem. |
| AT-119 | Nome de arquivo contendo texto pessoal ou metadado não governado desnecessário: alias em contexto, procedência, eventos e exportações; instruções funcionais não pessoais externas ao nome não são bloqueadas por falta de tipificação. |
| AT-120 | Nome de planilha contendo texto pessoal ou metadado não governado desnecessário: alias nas opções e linhagem; seleção continua rastreável e a instrução funcional não pessoal permanece disponível à interpretação. |
| AT-121 | Metadado necessário à interpretação: perguntar papel de `[CAMPO_n]`, sem enviar original; resposta passa pela triagem. Variantes positivas: entidade não pessoal tipificada pode ser liberada quando necessária; verbos, operadores, qualificadores e relações não pessoais necessários podem passar sem tipificação como entidade. |
| AT-122 | `11111111111`: não reconhecer CPF válido. Sob rótulo pessoal governado, proteger mesmo assim; código territorial tipificado não vira identificador pessoal. |
| AT-123 | Registro profissional em texto livre com associação inequívoca ao rótulo: proteger independentemente de formato CPF. |
| AT-124 | Negativa → `BLOQUEADA` → reversão explícita → `AGUARDANDO_CONFIRMACAO` com TPL-10 → confirmação positiva → triagem e exame refeitos → `DISPONIVEL`. A negativa anterior permanece histórica; autorização e derivados anteriores não são reativados; original protegido já descartado exige nova entrada; nada atravessa sessões. Não reabrir entregável terminal; upload idêntico é outra entrada. |
| AT-125 | Negativa remove perfil, estrutura e derivados de todo contexto ativo, inclusive histórico reconstruído, reuso e sugestões. |
| AT-126 | Sinal CFG-EXC `ATIVO`: aplicar a exclusão correspondente, com âncora e disposição registradas. |
| AT-127 | Sinal `DESCARTADO_POR_CONTEXTO`: prosseguir; C-04 confere estrutura sem julgamento semântico geral. |
| AT-128 | Sinal `INDETERMINADO`: uma pendência aplicável; nenhum sinal sem disposição ou exclusão silenciosa. |
| AT-129 | Retirada parcial: versionar escopo e apurar apenas os restantes. Retirada de todos, sem cancelamento explícito: conjunto vigente vazio e `ENCERRADA_SEM_RESULTADO`, inclusive com resultados anteriores ou estado anteriormente terminal. Preservar histórico; não converter retirados em `NAO_EXECUTAVEL/INTERROMPIDO`; não produzir `CONCLUIDA/CONCLUIDA_PARCIAL` nem EV-CANCELAMENTO da solicitação. Variante de cancelamento explícito conserva `CANCELADA`. Verificar suporte e pendências compartilhados. |
| AT-130 | “Considere 2,36 como referência e analise A, B e C”: registrar contexto; não criar diferenças ou comparação. Papel material indefinido gera uma pendência AMBIGUIDADE_MATERIAL com o conjunto PAPEL_DA_REFERENCIA e rótulos PT/EN governados. |
| AT-131 | Intenção comparativa governada contra 2,36: produzir relações previstas em CAP-CMP-01; nenhum percentual automático. |
| AT-132 | LLM indisponível em E1 e retorno na mesma sessão: permanecer `EM_ADMISSAO`, registrar indisponibilidade e retomar sem novo pedido. |
| AT-133 | LLM indisponível em E1 e expiração: descartar espera e entrada; retorno do serviço não retoma sessão encerrada. |
| AT-134 | Pergunta metodológica PT: decisão, motivo documental autorizado, elementos, opções com rótulos governados e consequência na ordem prevista. |
| AT-135 | Mesmo caso em EN: usar forma EN materializada do mesmo `id_doc` e rótulos EN governados das opções, sem tradução livre. |
| AT-136 | Falha/indisponibilidade na redação de pergunta: fallback determinístico conserva conteúdo, ordem e opções; resposta estruturada continua possível. |
| AT-137 | Explicação metodológica EN por FN-META-01: forma autorizada, variáveis ancoradas e condições preservadas. |
| AT-138 | “Calcule as densidades e compare”: um entregável comparativo, contendo os valores necessários. |
| AT-139 | Tabela e relatório explicitamente separados: dois entregáveis autônomos, com atendimento próprio. |
| AT-140 | Seleção ativa + pedido que exige universo e não o explicita: usar snapshot da seleção, exibir universo e não acrescentar operação. |
| AT-141 | Seleção ativa + universo textual materialmente diferente: esclarecer sem substituição silenciosa. |
| AT-142 | Entidade conversacional confirmada como pessoa: proteção mantida, TPL-10 obrigatório; autorização não permite análise individual; negativa aplica D15. |
| AT-143 | Variantes aprovadas de SIRGAS2000: mesmo valor canônico, elipsoide, parâmetros e resultado sob o método vigente. |
| AT-144 | CRS não suportado ou código não incorporado: `BLQ-MET/METODO_NAO_INCORPORADO`; nenhuma inferência EPSG, transformação ou padrão implícito. |
| AT-145 | Aba não selecionada contém dicionário ou notas: nenhuma influência semântica, materialização ou uso como metadado. |
| AT-146 | Aba selecionada como fonte auxiliar: triagem, origem própria e vínculos explícitos; aplicação limitada ao escopo autorizado. |
| AT-147 | Lote com A e C válidos e falha de B: preservar A/C, repetir apenas B se permitido, propagar somente dependências efetivas; ResultadoElemento A/C CONCLUIDO e B INTERROMPIDO (AT-170). |
| AT-148 | Folha dependente de etapa sem resultado: `NAO_AVALIAVEL/DEPENDENCIA_NAO_AVALIAVEL`, com referência à causa, sem resultado fictício. |
| AT-149 | `ATENDE OU NAO_AVALIAVEL`: resultado lógico `ATENDE`, com causa desconhecida preservada. |
| AT-150 | `NAO_ATENDE E NAO_AVALIAVEL`: resultado lógico `NAO_ATENDE`, com causa preservada. |
| AT-151 | `ATENDE E NAO_AVALIAVEL`: resultado lógico `NAO_AVALIAVEL`; aplicar RQ-CAP-08 somente após avaliação. |
| AT-152 | Controle “Encerrar sessão”: encerramento e descarte imediatos, sem depender da LLM. |
| AT-153 | Relógio controlado: ativa antes de 1.800 segundos; expirada no limite; EV-INTERACAO_USUARIO válido anterior renova o prazo; retry automático não renova (AT-175). |
| AT-154 | Fechar interface/desconectar/segundo plano: nenhum encerramento imediato; descarte no prazo de inatividade. |
| AT-155 | Reconexão antes da expiração, tecnicamente possível: mesma sessão, mesmo snapshot e conteúdo ainda autorizado. |
| AT-156 | Acesso após expiração: nova sessão, sem bases, contexto, mapeamentos ou solicitações anteriores. |
| AT-157 | Número ambíguo em entrada antes de linha/solicitação: pendência habilitadora `ESTRUTURA_DE_ENTRADA`, ligada à entrada. |
| AT-158 | Quadro de universo ausente: `BLQ-DAD` com `DetalheBloqueio.QUADRO_UNIVERSO_AUSENTE`, sem enum analítico inválido. |
| AT-159 | Esclarecimento longitudinal sobre campo/esquema: resposta aplica-se em massa ao objeto autorizado, preservando exceções e limites de escopo. |
| AT-160 | Referência comparativa sem unidade: exatamente um ContextoDeMedida determinístico é usado e explicitado; nenhum gera PARAMETRO_FALTANTE; múltiplos geram pendência (AT-169). |
| AT-161 | Limite técnico conversacional: TPL-13, entrada bloqueada, nenhum truncamento; pedido concomitante preservado e retomado após arquivo válido explicitamente associado. |
| AT-162 | Forma requerida PT/EN ausente, adulterada ou de versão incompatível: fechamento bloqueado; runtime rejeita trecho e não traduz livremente. |
| AT-163 | Reformulações equivalentes, lote único e decomposições alternativas: mesmos entregáveis, valores, avaliabilidade, estados e terminalidade. |
| AT-164 | Corridas entre negativa, retorno da LLM, conclusão de etapa e encerramento: nenhuma fonte recusada é reutilizada e nenhum conteúdo é recriado após descarte. Nos envios ainda admissíveis durante sessão ativa, aplicar as quatro classes: proteger conteúdo pessoal/metadados pertinentes sem bloquear texto funcional não pessoal por falta de tipificação como entidade. |

### 20.11. Cenários de D29–D42

Cenários normativos da reconstrução v1.2.4, a executar no reteste comportamental dirigido; esta publicação documental não declara testes de runtime realizados. Aplicar variantes PT/EN aos casos de interpretação, perguntas e apresentação.

| ID | Cenário e resultado obrigatório |
|---|---|
| AT-165 | Dado: A e B estabelecidos como territórios pela base carregada. Quando: "conforme pedido de Ana Souza, compare a densidade de médicos de A e B em 2024". Então: o nome, fora das posições estruturais de CFG-VOC e sem evidência positiva de papel não pessoal, chega ao LLM somente como placeholder; como seu papel não é material à execução, prossegue-se sem pendência; a linguagem funcional não nominal permanece interpretável. Variante em que o papel é material abre NATUREZA_DE_ENTIDADE_NOMINAL. Capitalização, listas de nomes, conhecimento externo, similaridade e LLM não decidem; variante EN equivalente produz a mesma decisão. |
| AT-166 | Expressão protegida como `[ENTIDADE_PROTEGIDA_1]` em "Silva tinha 10 médicos em 2024" reaparece em mensagem posterior fora de posição estrutural ("e o Silva?"), em contexto reconstruído, procedência e fallback: permanece protegida com o mesmo placeholder, independentemente da posição, até evidência positiva no escopo, como a declaração "Silva é um município", que a tipifica como TERRITORIO no escopo aplicável. A persistência não transfere alias, autorização ou negativa entre entradas distintas. |
| AT-167 | "A cidade de Vitória tinha 10 médicos em 2024", "a cidade de Vitória teve 10 médicos em 2024" e "the city of Vitória had 10 physicians in 2024": MARCADOR_TERRITORIAL_CIDADE estabelece TERRITORIO e VERBO_ASSOCIACAO_PASSADO estabelece a associação; mesma decisão estrutural nos dois idiomas, sem pendência de natureza. Variantes sem marcador são protegidas igualmente em PT e EN. |
| AT-168 | Campo tipificado por metadado autorizado como código territorial contém valor de 11 dígitos com dígitos verificadores de CPF válidos: permanece territorial, pois o passo 1 prevalece sobre o passo 3. Rótulos governados CRM, COREN, NIS, CNS_PROF, matrícula profissional, employee ID e staff number protegem os valores associados independentemente do formato. CPF com formato e dígitos válidos, sem rótulo, é protegido por padrão governado. "Matrícula" isolada é protegida por padrão e só gera pergunta se a distinção for necessária à execução. Número de papel não resolvido recebe `[IDENTIFICADOR_n]`. |
| AT-169 | Referência e critério sem unidade: (a) densidade sem escala indicada ou configurada — ContextoDeMedida único com fallback por 1.000 habitantes; "abaixo de 2,36" e "compare com a referência 2,36" usam e explicitam por 1.000; (b) atributo sem indicador, unidade, denominador ou escala determinável — nenhum ContextoDeMedida: PARAMETRO_FALTANTE (BLQ-INF), sem escala inventada; (c) quantitativo e densidade igualmente aplicáveis ao objeto comparado — dois contextos: pendência AMBIGUIDADE_MATERIAL. CAP-CMP-01 e CAP-SUB-01 produzem a mesma decisão para o mesmo valor. |
| AT-170 | Entregável composto com elementos A, B e C e relação D dependente de B: A e C CONCLUIDO e válidos; a execução de B começa e falha operacionalmente após o orçamento — ResultadoElemento INTERROMPIDO com causa-raiz OPR-FAL; D NAO_EXECUTAVEL com DEPENDENCIA_NAO_AVALIAVEL e causa_raiz_ref para B. Falha de B não contamina A e C; o estado agregado deriva dos elementos; a cobertura distingue válidos (A, C), falhos (B) e não avaliáveis (D). Lote único e decomposição alternativa produzem os mesmos elementos e estados. |
| AT-171 | Solicitação com entregável X ATENDIDO, Y em execução e Z PENDENTE recebe cancelamento explícito: solicitação CANCELADA; Y e Z CANCELADO; X conserva ATENDIDO e seu resultado histórico; nenhuma nova execução é iniciada; TPL-12 informa a situação pela forma `cancelamento`. Retirada total sem cancelamento continua ENCERRADA_SEM_RESULTADO (D17-A), sem CANCELADO. |
| AT-172 | Após o cancelamento de AT-171, chegam o retorno da unidade de Y e uma resposta tardia do LLM: nada reabre; CANCELADA/CANCELADO permanecem; o retorno não entra no conjunto vigente de resultados, não é reincorporado ao contexto ativo nem reenviado ao LLM; registra-se EV-RETORNO_TARDIO_DESCARTADO. Com a sessão já encerrada, prevalece o descarte de RQ-FLX-17, sem recriar objetos. |
| AT-173 | Pedido com sinais ATIVO de EXC-08 ("crie um método") e EXC-03 ("explique a causa") na mesma parte: ambas registradas com justificativa e consequência BLOQUEAR_NAO_EXECUTAR; a parte não é executada; a comunicação informa as duas exclusões, sem precedência pela numeração. Variante com EXC-11 (AGUARDAR_ESCLARECIMENTO_OU_CONFIRMACAO) e EXC-03 (BLOQUEAR_NAO_EXECUTAR): prevalece BLOQUEAR_NAO_EXECUTAR, com ambas registradas. Sinal DESCARTADO_POR_CONTEXTO coexistente não altera o desfecho. |
| AT-174 | Mensagem com dados e pedido: (a) associação entre entidades e valores com duas leituras estruturais plausíveis — pendência habilitadora ESTRUTURA_DE_ENTRADA, sem avaliar leituras do pedido; (b) dados estruturalmente fechados e pedido com duas leituras de assinaturas diferentes — AMBIGUIDADE_MATERIAL; (c) ambas as condições — ESTRUTURA_DE_ENTRADA precede AMBIGUIDADE_MATERIAL, avaliada somente após a resolução estrutural. O pedido é preservado sem repetição. |
| AT-175 | Relógio controlado: cada tipo de TipoInteracaoUsuario registra EV-INTERACAO_USUARIO com session_id, tipo e timestamp e renova o prazo; heartbeat, polling, refresh interno, renderização automática, reconexão automática sem ação do usuário, simples passagem do tempo e ação puramente local não recebida pela aplicação não renovam. A expiração ocorre 1.800 segundos após o último EV-INTERACAO_USUARIO válido. |
| AT-176 | Antes da criação de entregáveis coexistem PERTINENCIA, AMBIGUIDADE_MATERIAL, ESTRUTURA_DE_ENTRADA e CONFIRMACAO_DE_USO_DA_BASE, criadas nessa ordem: StatusSolicitacao permanece EM_ADMISSAO; apresentação e processamento seguem CONFIRMACAO_DE_USO_DA_BASE, ESTRUTURA_DE_ENTRADA, AMBIGUIDADE_MATERIAL e PERTINENCIA; dentro da mesma classe vale a ordem de criação. Indisponibilidade do LLM em E1 não entra na fila nem altera EM_ADMISSAO. Criados os entregáveis, pendência aplicável a entregável vigente leva a AGUARDANDO_USUARIO. |
| AT-177 | Pendência AMB-01 em sessão EN: as opções provêm das formas `rotulo.AMB-01.*` de DOC:RQ-GOV-18 ("in parallel", "comparison", "aggregate"); em PT, "em paralelo", "comparação" e "agregado". Cada opção tem id estável AMB-01.<valor>, valor estruturado e rótulos PT/EN. Saída simulada do LLM com rótulo próprio ou com CONJUNTO_COMPARATIVO como rótulo é rejeitada; o fallback determinístico apresenta os mesmos rótulos. Opção sem rótulo governado no idioma não é apresentada e registra erro de configuração, sem tradução em runtime. Leituras concorrentes usam a composição governada `rotulo.leitura`. |
| AT-178 | Consulta documental de CAP-SUB-01: o Anexo A fornece os id_doc DOC:CAP-SUB-01.<caminho>; cada um é obtido no catálogo externo pela chave id_doc, sem varredura integral; a forma PT `base` coincide com texto_canonico_pt; as formas EN corrigidas nesta versão — DOC:RQ-FLX-17, DOC:CAP-TMP-01.saida, DOC:CAP-AGR-01.entradas, DOC:CAP-ROT-01.precondicoes, DOC:CAP-ROT-01.parametros, DOC:RQ-REP-02, DOC:CAP-SUB-01.avaliabilidade, DOC:CAP-IND-02.metodo, DOC:RQ-FLX-02 e DOC:FAM-03.natureza — preservam os elementos de 4.4.23.2. Forma EN com `versao` anterior à da forma PT de mesmo id_forma_local, como a de DOC:CAP-SUB-01.metodo, não é apresentada em sessão EN: aplica-se a insuficiência, sem tradução livre nem troca silenciosa de idioma. Catálogo com versão incompatível, entrada órfã, id_doc ausente ou forma EN divergente impede fechamento; em runtime aplica-se a insuficiência PT/EN, sem tradução livre. |

---

## Parte 21 — Matriz de rastreabilidade Concept → SPEC

| Concept | Tema | SPEC |
|---|---|---|
| §1.1–1.5 | Identidade, finalidade, objeto, resultado central, papel do usuário | 1.1, 1.6, Parte 12 |
| §2.1–2.5 | Problema, complexidade, riscos, transformação pretendida | Partes 2, 6 e 7 |
| §3.1 | Domínio e famílias autorizadas | 1.2, 1.3, 4.3, 4.4.1, 4.4.9, RQ-DAD-19 (DA-04) |
| §3.2 | Flexibilidade do escopo e modos territoriais | 1.5, RQ-ESC-11, RQ-ESC-12, CAP-UNI-01, CAP-AGR-01 (P-21) |
| §3.3 | Interação, mobilidade e exame habilitador | Parte 6, 5.4, 6.7, RQ-DAD-42, RQ-FLX-22 (DA-02, P-18, F-08); precisão v1.2.2: RQ-DAD-43, RQ-FLX-01/04, AT-91/110/111 |
| §3.4 | Dependência da estrutura dos dados | Parte 5, 8.4, 7.7; precisão v1.2.2: RQ-DAD-30/43, CAP-EXA-01, AT-110/111 |
| §3.5 | Limites do LLM | INV-02, INV-03, RQ-ARQ-01, 7.1, Parte 14; precisão v1.2.2: CFG-DOC, V-16, AT-105/106 |
| §3.6 | Decisões substantivas e delegação | 7.5, INV-06 (DA-06) |
| §3.7 | Limites interpretativos | V-03 a V-06, V-13, RQ-CAP-09, 4.4.3 (DA-21) |
| §3.8 | Fora do escopo e registros individualizados | 1.4, 5.5, RQ-DAD-37 a RQ-DAD-39, 4.4.22, Parte 18 (DA-27, F-01); precisão v1.2.2: RQ-DAD-38, CFG-PRV, AT-102 a AT-104 |
| §4.1–4.2 | Conceito e organização das capacidades | 8.1, 8.2 |
| §4.3.1–4.3.2 | Interpretar, conduzir e orquestrar | 8.5, Parte 9 |
| §4.3.3 | Examinar os dados | 5.2, 5.4, 5.5, CAP-EXA-01 (DA-02); precisão v1.2.2: CFG-TER, CAP-EXA-01, AT-94 a AT-96, AT-110/111 |
| §4.3.4 | Delimitar o universo | 5.3, CAP-UNI-01 |
| §4.3.5 | Indicadores | CAP-IND-01, CAP-IND-02, 4.4.6, RQ-DAD-36 (DA-09, F-02) |
| §4.3.6 | Distribuições | CAP-DIS-01 a CAP-DIS-03 (DA-11, DA-12) |
| §4.3.7 | Comparar | CAP-CMP-01, RQ-ORQ-13 (DA-13, AV-05, F-10); precisão v1.2.2: CAP-CMP-01 (relações e avaliabilidade), AT-92/97 |
| §4.3.8 | Agregar | CAP-AGR-01 (DA-16, F-05); precisão v1.2.2: RQ-CAP-08, CAP-AGR-01 (F-05a/F-05b preservadas), AT-112 |
| §4.3.9 | Mudanças temporais | CAP-TMP-01, CAP-ROT-01 (DA-14, F-05b; Configuração Inicial de Implementação); precisão v1.2.2: CFG-TER, RQ-CAP-08, AT-94 a AT-96, AT-112 |
| §4.3.10 | Tendências | CAP-TEN-01; CAP-ROT-01 não produz série (DA-15, F-05b); precisão v1.2.2: CFG-TER, RQ-ORQ-13, AT-112 |
| §4.3.11 | Referências territoriais | CAP-REF-01, AMB-02 (DA-17); precisão v1.2.2: CAP-CMP-01 e CAP-SUB-01 distinguem parâmetro de referência e critério de referência territorial, AT-92/93 |
| §4.3.12 | Relações espaciais | CAP-ESP-01 a CAP-ESP-03, 5.6, 4.4.5, V-06 (DA-17; F-09 não incorporada); precisão v1.2.2: RQ-DAD-26, AT-108/109 |
| §4.3.13 | Subconjuntos e ordenações | CAP-SUB-01 a CAP-SUB-03 (DA-18, DA-19); precisão v1.2.2: CAP-SUB-01 (árvore, avaliabilidade e saída), AT-93/98 |
| §4.3.14 | Representações | Parte 13 (DA-20, DA-23); precisão v1.2.2: RQ-REP-01, EV-REPRESENTACAO, TPL-12, AT-106/107 |
| §4.3.15 | Síntese | Parte 14, RQ-SIN-10, RQ-RES-11, 4.4.15, 4.4.23 (DA-05, AV-10, F-04, F-12); precisão v1.2.2: CFG-DOC, V-16, TPL-12, AT-105/106 |
| §4.4 | Composição | Parte 9, 7.8 (P-08); precisão v1.2.2: RQ-GOV-28/29, AT-113 a AT-115 |
| §5.1–5.2 | Função da governança e pertinência | 7.2, 7.3, Parte 6 (DA-04, P-01) |
| §5.3 | Fontes e autoridade das regras | Parte 4, RQ-GOV-21 (DA-01, DA-03) |
| §5.4 | Autonomia condicionada | 1.6, Parte 9 |
| §5.5 | Decisões operacionais e substantivas | 7.5 (DA-06, P-22); precisão v1.2.2: RQ-GOV-16/27/28, RQ-DAD-43, AT-91/110/111/115 |
| §5.6 | Precedência determinística | INV-02, RQ-ARQ-09; precisão v1.2.2: CFG-DOC, V-16, RQ-REP-01, AT-105 a AT-107 |
| §5.7 | Ambiguidades e contexto | 7.5, 6.4 (P-07); precisão v1.2.2: RQ-FLX-04, CFG-TER, RQ-DAD-38/43, AT-91/95/102/110 |
| §5.8 | Informações externas e conhecimento prévio | 7.1, 5.5, INV-03, INV-14, RQ-GOV-03, RQ-GOV-23, 4.4.24 (P-05); precisão v1.2.2: CFG-DOC, V-16, RQ-DAD-38, AT-102 a AT-106 |
| §5.9 | Condições de acionamento e contexto de consistência | 7.7; precisão v1.2.2: RQ-GOV-24/27/29, RQ-FLX-01/04, AT-91/115 |
| §5.10 | Rastreabilidade | Parte 17, RQ-RES-07; precisão v1.2.2: RQ-RAS-03 a RQ-RAS-05, AT-107 |
| §5.11 | Transparência | Parte 15 (P-03) |
| §5.12 | Sugestões | FN-INT-04, V-10 |
| §6.1–6.3 | Camadas e naturezas de execução | Parte 2 |
| §6.4 | Fluxo | Parte 6 (P-01); precisão v1.2.2: RQ-FLX-01/02/04, E7–E12 independentes, AT-91/99/100 |
| §6.5 | Composição e encadeamento | 9.4 a 9.6; precisão v1.2.2: RQ-GOV-29, RQ-ORQ-01/04, AT-97/113 a AT-115 |
| §6.6 | Arquitetura e governança | Partes 2 e 7 |
| §7.1–7.2 | Dados e fontes autorizadas | 5.1, 5.7 a 5.9, 7.1, RQ-DAD-40 a RQ-DAD-43, 4.4.21 (DA-02, DA-07, AV-02, AV-08, F-06, F-08, F-11); precisão v1.2.2: RQ-DAD-43, AT-110/111 |
| §7.3 | Significado dos dados | 5.2, 5.6 (DA-09, P-05); precisão v1.2.2: CFG-TER, RQ-DAD-38, AT-94 a AT-96, AT-102 a AT-104 |
| §7.4 | Ausência, unidade sem registro, zero | RQ-RES-05, RQ-DAD-07, RQ-DAD-11 (DA-10) |
| §7.5 | Histórico e contexto | 6.4 |
| §7.6 | Linha analítica | 11.1, 11.2, RQ-LIN-19, RQ-LIN-21, 4.4.18 (DA-06, P-14, F-06, F-07) |
| §7.7–7.9 | Validade, vigência, estado, reutilização | 11.3, 11.4, 9.3, RQ-LIN-20 (DA-08, F-03) |
| §7.10 | Alterações durante a interação | RQ-LIN-10, 9.5 (DA-01) |
| §7.11 | Histórico, contexto, linha, estado e rastreabilidade | Partes 11 e 17 |
| §8.1–8.2 | Resultados estruturados | Parte 10; precisão v1.2.2: RQ-RES-01/04/10, CAP-CMP-01, CAP-SUB-01, AT-97/98/113 |
| §8.3–8.4 | Diagnóstico | Parte 12 (P-23, AV-09) |
| §8.5 | Resultado, representação e síntese | Partes 13 e 14; precisão v1.2.2: RQ-REP-01/09, CFG-DOC, TPL-12, RQ-DEG-04, AT-100/106/107 |
| §8.6 | Procedência | 7.1, RQ-GOV-03; precisão v1.2.2: RQ-RAS-04/05, RQ-DAD-38/43, AT-107/110/111 |
| §8.7 | Rastreabilidade do diagnóstico | Parte 17; precisão v1.2.2: RQ-RAS-03/04/05, EV-REPRESENTACAO, AT-107 |
| §8.8 | Resultados intermediários | RQ-RES-08, RQ-DIA-03 |
| §8.9–8.10 | Validade e reprodutibilidade | 11.4, RQ-CAP-02, RQ-RES-09; precisão v1.2.2: RQ-QUA-06, RQ-GOV-28, RQ-ORQ-01, AT-115 |
| §8.11 | Limitações e resultados não classificatórios | RQ-CAP-08, RQ-RES-05, RQ-RES-06 (DA-22, P-09); precisão v1.2.2: RQ-CAP-08, RQ-RES-04/10, AT-98/112/113 |
| §8.12 | Consolidação e formas de entrega | RQ-DIA-04, CAP-REP-05, CAP-REP-06 (DA-23, DA-24); precisão v1.2.2: RQ-REP-12, TPL-12, CFG-DOC, AT-44/106 |
| §9.1–9.10 | Incerteza, esclarecimento, execução parcial, alternativas, continuidade | Parte 15, 7.5, 7.8, Parte 11 (P-08); precisão v1.2.2: RQ-FLX-01/02/04, RQ-GOV-27/29, AT-91/99/115 |
| §9.11 | Indisponibilidade de componentes | Parte 16 (DA-26, P-18); precisão v1.2.2: RQ-DEG-04, TPL-12, AT-100/101/106 |
| §9.12 | Encerramento sem resultado | RQ-INC-04; precisão v1.2.2: RQ-FLX-02, AT-99 |
| §10.1–10.13 | Qualidade e validação | Parte 20 (DA-28); precisão v1.2.2: 20.9, RQ-QUA-06/07, AT-91 a AT-115 |
| §10.14 | Testes pertencem à especificação | Parte 20 |
| §11.1–11.13 | Evolução controlada | Parte 19 (DA-01) |
| §12.1–12.3 | Usuário, conhecimento esperado, relação | 1.6, RQ-GOV-19, RQ-FLX-17 (DA-25); precisão v1.2.2: RQ-GOV-19/30, CFG-DOC, V-16, TPL-12, AT-105/106 |
| §12.4–12.8 | Contextos de uso e limites da adaptação | RQ-SIN-07, RQ-SIN-08, RQ-FLX-18, RQ-CFG-14 (DA-05) |
| §13.1–13.3 | Premissas e definições | 0.7, 3.1, INV-01 a INV-18 |
| §14.2–14.25 | Casos conceituais 1 a 24 | AT-01 a AT-24 |

---

### 21.1. Rastreabilidade de D13–D42, D17-A e H1–H3

D13–D42, D17-A e H1–H3 são operacionalizadas pelos contratos atuais. Esta matriz registra impactos; a fonte normativa são as definições primárias, não o plano ou relatórios de baterias.

| Decisão | Requisitos principais | Modelos/enums | CFG | Componentes | FN | Templates | Validadores | Eventos principais | ATs existentes e novos | Anexo A |
|---|---|---|---|---|---|---|---|---|---|---|
| D13, quatro classes | DAD-20–24/33/38/39; ARQ-06; RAS-04/05/07; PRV-01–08 | Proteção, aliases, âncoras, Base; preservar texto funcional | PRV/VOC/FON/DOC | C-01–04/08/10–13 | Todas as FN consumidoras de contexto | 04/10/12 | C-04: proteção A/C e passagem B/D; V-02/16 | TRIAGEM/PRIVACIDADE/EXAME/EXPORTACAO | 37/60/63/73–76/89/102–104 → 116–121/164 | Política das quatro classes, privacidade e placeholders |
| D14 | DAD-20/21/33/37/39; PRV-02/03/05 | CampoProtegido | PRV/VOC/DOC | C-02/04/10/13 | INT-01/02 recebem placeholders e conteúdo sanitizado | 04 | C-04 | TRIAGEM/PRIVACIDADE | 74 → 122/123 | Regras e vocabulário pessoal |
| D15 | DAD-17/22/34/42; FLX-04–06/22; ORQ-06/07/10/11 | Base, bloqueio, contexto, dependentes | PRV/TPL/OPR/DOC | C-02/04/05/07/08/10/13 | INT-01/02; ORQ-01 | 04/10/12 | C-04; V-09/11 | CONFIRMACAO-USO/ESTADO-BASE/PRIVACIDADE | 70/83 → 124/125/164 | Ciclo da base e novo enum estrutural |
| D16 | GOV-01/08/09; RAS-02 | LeituraMinima, disposição | EXC/DOC | C-03/04/13 | INT-01/03 | 04/06 | C-04; V-16 na explicação | LEITURA-MINIMA/ADMISSIBILIDADE/PENDENCIA | 87 → 126–128 | GOV, EXC e enum de disposição |
| D17 + D17-A | FLX-01/02/09; GOV-28/29; ORQ-01/08/16; RES-04; DIA-01/02 | Escopo versionado, conjunto vazio, ocorrência, vínculo | ESC/DOC/TPL | C-01/02/04/05/07/08/11–13 | INT-02; ORQ-01; META-01 | 04/12 | C-04; V-09/11/16 | ALTERACAO-ESTADO/REPLANEJAMENTO; CANCELAMENTO somente se explícito | 91/99/113–115 → 129 | Retirada total → ENCERRADA_SEM_RESULTADO; distinção de cancelamento |
| D18 | GOV-14/16–20/28; CMP/REF/SUB | Parâmetro e relação pretendida | VOC/AMB/REF/DOC | C-03–06/08/11–13 | INT-02/03; ORQ-01 | 04/12 | C-04; V-07/16 | INTERPRETACAO/VALIDACAO-INTERPRETACAO/PENDENCIA | 84/92/93 → 130/131 | CAP-CMP/REF/SUB e VOC |
| D19 | FLX-01; DEG-01/02/08/09; ARQ-10/11 | Espera operacional da solicitação | OPR/TPL/DOC | C-01–04/08/13 | INT-01 | 01 | C-04 | INDISPONIBILIDADE/DISPONIBILIDADE | 13/101 → 132/133/164 | Estados e degradação |
| D20 | GOV-19; SIN-01/04/05/07/09/10; FLX-18; QUA-07 | Proposição, forma, segmento, pergunta | DOC/TPL/PRV | C-02/03/04/09/11–13 | INT-03; META-01 | 01–13 conforme conteúdo | V-16 e validadores de conteúdo aplicáveis | PERGUNTA/META/VALIDACAO-SAIDA/SINTESE | 28/38/43/72/86/105–107 → 134–137/162 | Contrato e catálogo integral de formas |
| D21 | GOV-16/28/29; ORQ-01/08; RES-04/08; QUA-06 | Interpretação e entregável | CAP/VOC/DOC | C-03–08/11–13 | INT-02; ORQ-01 | 04/12 | C-04; V-09 | INTERPRETACAO/VALIDACAO-INTERPRETACAO/PLANO | 41/113–115 → 138/139/163 | Identidade semântica e terminalidade |
| D22 | FLX-16; DAD-09; GOV-14/16/21; LIN-19/20 | Manifestação e snapshot UI | ESC/VOC/DOC | C-01/03/04/08/13 | INT-01/02/03 | 04/12 | C-04; V-02/08 | CAPTURA-SELECAO/INTERPRETACAO/PENDENCIA | 20/67 → 140/141 | Universo e captura |
| D23 | DAD-21/22/31/33/38–42; PRV-01–06/10 | Natureza nominal, Base, Pendencia | PRV/VOC/TPL/DOC | C-01–04/08/10/13 | INT-01/02/03 | 04/10 | C-04 | RESPOSTA/PRIVACIDADE/CONFIRMACAO-USO | 60/63/73/75/83 → 142 | Autorização e proteção conversacional |
| D24 | DAD-25–27; CAP-13; CAP-ESP-01 | Referencial e parâmetros | MET/DOC | C-04/06/09/11/13 | INT-02/03; META-01 | 04/11/12 | C-04; V-06/16 | VERIFICACAO/EXECUCAO/REPRESENTACAO | 51/108/109 → 143/144 | CFG-MET e CAP-ESP-01 |
| D25 | DAD-04/06/13/16/29/30/42/43; RAS-04/05/07 | Papel da aba e vínculos | FON/PRV/VOC/DOC | C-01/02/04/08/10/13 | INT-01/02/03 | 04/10 | C-04; V-16 na procedência | INGESTAO/TRIAGEM/EXAME/ESTADO-BASE | 61/89/110/111 → 145/146 | Ingestão, metadados e enum de papel |
| D26 | ORQ-01/04/14/15; GOV-24/29; CAP-08; RES-01/04/10; QUA-06 | Unidade de execução, causa | OPR/TPL/DOC | C-04–08/11–13 | ORQ-01; META-01 | 03/12 | C-04; V-08/09/15 | EXECUCAO/FALHA/REUSO/RESULTADO | 35/41/97/112–115 → 147/163 | Falha, dependências e parcialidade |
| D27 | GOV-24; ORQ-01/04/14; RES-01/10; CAP-08; CAP-SUB-01 | Saída esperada, folha, causa | MET/DOC | C-04–08/11–13 | INT-02; ORQ-01; META-01 | 12 | C-04; V-08/15/16 | VERIFICACAO/EXECUCAO/RESULTADO | 49/98/112 → 148–151 | SUB, causalidade e gates |
| D28 | FLX-09/17/19; DAD-17/42; PRV-08; RAS-06; DEG-02/08 | Sessão, relógio, encerramento | OPR/TPL/PRV/DOC | C-01/02/04/05/07–13 | Nenhuma FN necessária para encerrar | 09 | C-04; V-16 no texto explicativo | SESSAO/ESTADO-BASE | 44 → 152–156/164 | Sessão, descarte e enum de motivo |
| H1 | DAD-09/10/35/41/42; FLX-21/22; LIN-19/21 | Pendencia, objeto, DetalheBloqueio | VOC/ESC/DOC | C-04/08/10/13 | INT-01/02/03 | 04 | C-04; V-16 | PENDENCIA/RESPOSTA/VERIFICACAO | 82/85/86/95 → 157–159 | Tipos, motivos e escopos |
| H2 | GOV-14/19; REP-01/05/11; RAS-05; CAP-CMP-01 | Parâmetro e escala | VOC/REP/DOC | C-04/06/08/11/13 | INT-02/03; META-01 | 04/12 | V-01/07/16 | INTERPRETACAO/EXECUCAO/REPRESENTACAO | 47/92/107 → 160 | CMP e origem da escala |
| H3 | DAD-31/33/34/40–43; FLX-01/04/21/22; ARQ-04; RES-06 | Entrada, vínculo, pendência | FON/TPL/OPR/DOC | C-01/02/04/08/10/13 | INT-01/02/03, quando pertinentes | 04/13 | C-04; V-16 | INGESTAO/ESTADO-BASE/FALHA/PENDENCIA | 64/89 → 161 | TPL-13, materialização e retomada |
| D29 | DAD-20/33/38/39; INV-16; PRV-02 | CampoProtegido com escopo de linhagem | PRV/VOC/DOC | C-04/10/13 | INT-01 recebe placeholders | 04/10 | C-04 | TRIAGEM/PRIVACIDADE | 102–104/116–121 → 165/166 | RQ-DAD-20/33/38/39, INV-16 e CFG-PRV |
| D30 | CFG-14; DAD-38/41; QUA-06 | Conceitos canônicos lexicais | VOC/AMB/LEX/PRV/DOC | C-04 | INT-01/02 | — | V-03/06/12 | TRIAGEM/INTERPRETACAO | 43/88/102/103 → 167 | RQ-CFG-14, CFG-VOC, CFG-AMB, CFG-LEX e CFG-PRV |
| D31 | CFG-DOC 4.4.23.2/4.4.23.6; V-16; QUA-07 | ProposicaoDocumental, FormaApresentacao | DOC | C-04/09/11 | INT-03; META-01 | 01–13 | V-16 | VALIDACAO-SAIDA | 105/106/134–137/162 → 178 | CFG-DOC e catálogo externo |
| D32 | GOV-17/18/19; DEG-05; CFG-OPC | OpcaoAutorizada, RefEscopo, ConjuntoOpcoesAutorizadas, InterpretacaoAlternativa | OPC/AMB/TPL/PRV/DOC | C-02/04/11 | INT-02/03 | 04 | V-16 | PERGUNTA/PENDENCIA | 03/16/25/91/130/134/135 → 177 | CFG-OPC e formas rotulo.* |
| D33 | DAD-37 | CampoProtegido | PRV/DOC | C-04/10 | INT-01 recebe placeholders | 10 | C-04 | TRIAGEM/PRIVACIDADE | 74/122/123 → 168 | RQ-DAD-37 e CFG-PRV |
| D34 | CAP-CMP-01; CAP-SUB-01; REP-01/11 | ContextoDeMedida | IND/REP/VOC/DOC | C-04/06/11 | INT-02 | 04/12 | V-01/07/16 | INTERPRETACAO/REPRESENTACAO/PENDENCIA | 92/93/107/160 → 169 | CAP-CMP-01, CAP-SUB-01 e glossário |
| D35 | ORQ-14; RES-04/06; CAP-08 | ResultadoElemento, StatusExecucaoElemento | OPR/DOC | C-05/06/07/11 | ORQ-01 | 03/12 | V-08/09 | EXECUCAO/FALHA/RESULTADO | 147/148/163 → 170 | RQ-ORQ-14, RQ-RES-04 e enum novo |
| D36 | FLX-01/02; ORQ-16; RES-04 | StatusEntregavel com CANCELADO | TPL/DOC | C-05/08/11 | — | 12 | V-09 | CANCELAMENTO | 129 → 171 | RQ-RES-04, ENUM-StatusEntregavel e TPL-12 |
| D37 | FLX-01; DEG-02 | Pendencia com classe de prioridade | OPR/DOC | C-02/04/08 | INT-01 | 04 | — | PENDENCIA | 13/132/157 → 176 | RQ-FLX-01 e RQ-DEG-02 |
| D38 | FLX-17; RAS-02 | Sessao, TipoInteracaoUsuario | OPR/TPL/DOC | C-01/08/13 | Nenhuma FN | 09 | — | INTERACAO_USUARIO/SESSAO | 153 → 175 | CFG-OPR, RQ-FLX-17 e enum novo |
| D39 | ORQ-16; FLX-17; RAS-02 | — | DOC | C-05/08/13 | — | — | — | RETORNO_TARDIO_DESCARTADO | 164 → 172 | RQ-ORQ-16 |
| D40 | GOV-08/09 | LeituraMinima, ConsequenciaExclusao | EXC/DOC | C-04 | INT-01 | 05/06/07 | — | LEITURA-MINIMA/ADMISSIBILIDADE | 87/126–128 → 173 | RQ-GOV-08/09, CFG-EXC e enum novo |
| D41 | DAD-34/42 | Base | PRV/TPL/DOC | C-02/04/10 | — | 10 | — | CONFIRMACAO-USO/ESTADO-BASE/TRIAGEM/EXAME | 70/83/124/125 | RQ-DAD-34/42 |
| D42 | DAD-31/41; FLX-21 | Pendencia | VOC/DOC | C-04/08 | INT-01/02 | 04 | — | PENDENCIA | 63/64/85/157 → 174 | RQ-DAD-31/41 e RQ-FLX-21 |

---

## Parte 22 — Registro das decisões incorporadas

Registro das decisões DA-01 a DA-28 e dos elementos que as implementam. As precisões aprovadas AV-01 a AV-10 são registradas aqui apenas quando harmonizam sua expressão operacional; não reabrem as decisões. A rodada está consolidada na seção 24.6.

**DA-01 — Processo de configuração governada.** Decisão: regras, métodos, capacidades e limites de autonomia são imutáveis durante a interação; mudanças só no processo externo de desenvolvimento, documentadas e versionadas; sem estrutura institucional complexa; separação entre configuração global e decisões locais. Complemento aprovado: configuração congelada durante toda a sessão; nova versão só vale para nova sessão ou mecanismo futuro e explícito de migração ou reinício. Incorporação: RQ-CFG-01 a RQ-CFG-03, RQ-CFG-05, INV-15, RQ-ARQ-11, RQ-FLX-17, RQ-ORQ-10, Parte 19, AT-52.

**DA-02 — Ingestão e autorização de dados e metadados.** Decisão harmonizada por AV-02 e AV-08: introdução deliberada por upload estruturado ou pequeno conjunto na conversa autoriza inicialmente ingestão, triagem e exame pela via HABILITADORA; disponibilidade da base após exame e confirmações não substitui autorização analítica E9; o exame se limita a reconhecer estrutura, cobertura, semântica e capacidades possíveis, sem análise espontânea; dados vêm de fonte autorizada ou de manifestação explícita, nunca do LLM. Incorporação: RQ-DAD-01 a RQ-DAD-04, RQ-DAD-13, RQ-DAD-16, CAP-EXA-01, CFG-FON, RQ-DAD-28 a RQ-DAD-34, RQ-FLX-21, AT-26, AT-59 a AT-65, AT-70, AT-73. Precisão v1.2 (F-06, F-08, CFG-FON): estados de preparação RECEBIDA, TRIADA, AGUARDANDO_CONFIRMACAO, EXAMINADA, DISPONIVEL, BLOQUEADA e DESCARTADA; pendência habilitadora vinculada à entrada e reapresentada sem duplicata; classificação dos dados conversacionais; CSV e XLSX (RQ-DAD-40, RQ-DAD-42, RQ-DAD-43, RQ-FLX-22).

**DA-03 — Precedência entre fontes.** Decisão: substituição explícita pelo usuário prevalece no escopo, com registro e sem alterar a base; conflito só interrompe a análise quando há divergência material sem precedência clara; regras e métodos nunca são sobrepostos pelo usuário. Incorporação: RQ-GOV-21, CFG-PRE, CAP-IND-02, RQ-RES-06, AT-19.

**DA-04 — Critérios operacionais de pertinência.** Decisão: pertinência pela relação com a FTS e com a finalidade; sem lista fechada de categorias; categoria integra a FTS por fonte ou metadado autorizado ou por declaração explícita do usuário; temas claramente alheios são não pertinentes; casos realmente ambíguos geram esclarecimento; o LLM não infere elementos factuais. Complementos aprovados: a simples solicitação de uma categoria como objeto de análise não constitui declaração de pertença; declaração autorizada de que a base representa a FTS estabelece, no escopo daquela base, a pertença de suas categorias, sem classificação universal; reconhecimento determinístico por vocabulário governado de CFG-DOM e CFG-VOC, não exaustivo, com resultados FTS_INEQUIVOCA, FTS_AMBIGUA e NAO_RECONHECIDA, sem inferência pelo LLM e sem pergunta obrigatória sobre o domínio após o upload; NAO_RECONHECIDA não equivale a NAO_PERTINENTE. Incorporação: RQ-ESC-04, 4.3 (RQ-CFG-08 a RQ-CFG-11), RQ-DAD-01, RQ-DAD-06, RQ-DAD-19, RQ-GOV-04, RQ-GOV-20, RQ-GOV-32, CFG-DOM, CFG-VOC, AT-24, AT-48, AT-55 a AT-57. Precisão v1.2 (CFG-DOM): o vocabulário deixa de ser semente e passa a conteúdo da Configuração Inicial de Implementação, com 15 categorias de reconhecimento automático, entre elas PSICOLOGIA, e 3 de reconhecimento contextual (FTS_CONTEXTUAL), sem catálogo fechado de profissões (seção 4.3, RQ-CFG-13, AT-88).

**DA-05 — Idiomas, vocabulários, léxicos e modelos de mensagem.** Decisão: português e inglês, com arquitetura aberta a outros idiomas; o idioma não altera métodos; resposta no idioma predominante, salvo escolha explícita; expressões equivalentes mapeiam para os mesmos conceitos; expressão não ancorável gera esclarecimento; sem troca silenciosa de idioma. Incorporação: RQ-FLX-18, RQ-FLX-20, RQ-GOV-18, RQ-SIN-06, RQ-SIN-09, CFG-VOC, CFG-AMB, CFG-LEX, CFG-TPL, Parte 14, AT-43. Precisão v1.2: conteúdo PT/EN de CFG-VOC, CFG-AMB, CFG-LEX, CFG-TPL e CFG-EXC fixado na seção 4.4; ausência deliberada de equivalente em um idioma e separação entre sinal lexical, interpretação candidata, correspondência autorizada e validação determinística (RQ-CFG-14, RQ-CFG-15).

**DA-06 — Escopo padrão de parâmetros e decisões.** Decisão: parametrização só nos graus de liberdade do contrato; menor escopo explicitamente indicado; sem propagação automática; ampliação explícita pelo usuário; oferta de reutilização sem presunção; decisões locais não alteram a configuração; método escolhido pelo usuário só quando o contrato permitir; linhas internas, com nova linha para objetivo materialmente distinto. Complemento aprovado: sem escopo indicado, o parâmetro vale para a solicitação corrente; "nesta análise" o estende à linha. Incorporação: RQ-LIN-02, RQ-LIN-07, RQ-LIN-08, RQ-GOV-13, RQ-CAP-13, RQ-MOD-07, CFG-ESC, AT-11, AT-42. Precisão v1.2 (F-07): resposta a pendência herda o escopo da pendência; dimensão da linha permanece até ser substituída; alterar uma dimensão não apaga as demais; vínculo explícito a objeto não se propaga (RQ-LIN-19, AT-82).

**DA-07 — Valores factuais fornecidos pelo usuário.** Precisão AV-02: conjuntos conversacionais seguem RQ-DAD-31 e RQ-DAD-32; valor complementar pode permanecer escopado sem base artificial, e a fonte é MANIFESTACAO_USUARIO. Decisão: o usuário pode fornecer dados factuais necessários a capacidades autorizadas, validados quanto a formato, tipo, unidade, coerência e compatibilidade, sem validação externa de veracidade, com origem, escopo explícito e sem propagação; substituição conforme DA-03; o LLM não é a fonte. Complemento aprovado: a informação de que não há sobreposição entre componentes de um agregado é aceita como premissa factual do usuário, registrada com origem, escopo, conteúdo e impacto sobre a agregação. Incorporação: RQ-GOV-22, RQ-DAD-12, RQ-DAD-16, RQ-CAP-12, CAP-IND-02, CAP-AGR-01, AT-08, AT-54. Precisão v1.2, remediada na v1.2.1 (F-06): valor factual complementar preserva objeto, âncora e escopo; sem linha aplicável na manifestação, é recuperável por qualquer linha compatível da sessão, sem transferência ou exclusividade; associação existente permanece registrada; não expira ao fim da mensagem e não se propaga quando isso muda seu significado (RQ-LIN-21, AT-81).

**DA-08 — Recálculo automático.** Decisão: sem recálculo espontâneo; impacto registrado; recálculo sem nova confirmação quando a solicitação o implica claramente; nos demais casos, oferta de reexecução. Incorporação: RQ-LIN-15, RQ-FLX-09, CFG-REC, AT-12, AT-19.

**DA-09 — Definição operacional dos indicadores.** Precisão AV-03: unidade de observação, medida e identidade são distintas; pessoas podem ser contadas em registros de vínculos por identidade autorizada suficiente, sem coluna de quantidade (RQ-DAD-35, AT-60). Decisão: unidade de contagem da base, de metadado ou de confirmação, sem conversão silenciosa; pessoas únicas exigem identificador ou regra de deduplicação; denominador do mesmo território e período, salvo indicação explícita ou regra; escala de apresentação parametrizável sem alterar o indicador canônico. Complemento aprovado: escala por precedência — indicada pelo usuário, configurada para o indicador, por 1.000 habitantes —, sem mudança automática pela magnitude; valor canônico por habitante. Incorporação: RQ-DAD-18, CAP-IND-01, CAP-IND-02, CAP-AGR-01, CFG-IND, RQ-REP-11, AT-01, AT-47, AT-50.

**DA-10 — Tratamento de ausência.** Decisão: ausentes nunca são transformados automaticamente em zero, média, estimativa, exclusão ou outro valor; permanecem NAO_AVALIAVEL, salvo método autorizado ou valor explícito do usuário; ausência é distinta de zero. Incorporação: INV-04, RQ-DAD-07, CFG-AUS, CAP-IND-02, CAP-AGR-01, AT-08, AT-33.

**DA-11 — Mediana, percentis, quantis e posição relativa.** Decisão: método único, determinístico e versionado; mediana central ou média dos dois centrais; Hyndman–Fan tipo 7; empates preservados, com classes de tamanhos diferentes. Complemento aprovado: valores coincidentes com o corte pertencem à classe inferior (Q1: x ≤ q1; Qk: q(k−1) < x ≤ qk; última classe: x > q(K−1)). Incorporação: CAP-DIS-01, CAP-DIS-02, CFG-MET, AT-17, AT-20, AT-29.

**DA-12 — Distribuição de frequências.** Decisão: convenção [a, b), apresentação intuitiva e último intervalo fechado quando necessário; faixas do usuário ou de método autorizado; o LLM não cria intervalos; na falta, esclarecimento. Incorporação: CAP-DIS-03, CAP-ESP-03.

**DA-13 — Relações comparativas e compatibilidade.** Precisão AV-05: contextos distintos não impedem comparação de dimensões deliberadamente diferentes; entradas compatíveis são preservadas no novo contexto, sem recálculo artificial (RQ-ORQ-13, AT-67). Decisão: igualdade, ordem, diferença absoluta, razão e diferença relativa ou percentual em relação a referência explícita; compatibilidade metodológica exigida; mudanças entre períodos pela capacidade temporal. Incorporação: CAP-CMP-01. Precisão v1.2 (F-10): comando genérico de comparação produz valores lado a lado, igualdade ou ordem e diferença absoluta; razão e diferença relativa somente com intenção explícita; universo inequívoco da linha, sem agregação silenciosa (AT-84).

**DA-14 — "Sem mudança" e base zero.** Decisão: SEM_MUDANCA por igualdade exata; variação percentual convencional; com base zero, direção e variação absoluta normais e percentual NAO_AVALIAVEL por BASE_ZERO; sem pseudocontagens. Incorporação: CAP-TMP-01, AT-09.

**DA-15 — Método de tendência.** Decisão: mínimo de quatro observações válidas e comparáveis; variações sucessivas normalizadas pelo tempo transcorrido; sem imputação; seis classes e SEM_CLASSIFICACAO com motivo; variação absoluta por unidade de tempo. Complemento aprovado: aceleração e desaceleração por monotonicidade não estrita com pelo menos uma mudança estrita, sobre velocidades positivas (crescimento) ou magnitudes de velocidades negativas (declínio); velocidades constantes mantêm a classe básica; intervalo com velocidade zero impede a qualificação. Incorporação: CAP-TEN-01, 3.1, AMB-05, AT-02, AT-09, AT-10, AT-18, AT-53.

**DA-16 — Agregação territorial.** Decisão: agregado a partir dos componentes, nunca pela média das densidades; numerador conforme aditividade ou deduplicação e denominador conforme dimensão agregada (AV-01): soma de populações territoriais distintas e aditivas, população compartilhada uma única vez entre categorias; agregado parcial permitido, com cobertura explícita e sem representar o universo completo; dupla contagem controlada; nenhuma equivalência presumida; "juntos" ambíguo gera esclarecimento. Complemento aprovado (regra de agregação com possível sobreposição, aplicável a territórios e a categorias): quando a unidade de contagem é pessoa e uma mesma pessoa pode pertencer a mais de um componente, ela é contada uma vez em cada componente em que está presente, e a contagem de pessoas únicas do agregado exige deduplicação sobre a união ou informação autorizada, inclusive premissa do usuário, que estabeleça ausência de sobreposição; sem essas condições, a soma pode ser executada a pedido do usuário como soma das contagens dos componentes, com possível dupla contagem explicitada, e nunca é rotulada como pessoas únicas. Precisão AV-07: agregados parciais são válidos isoladamente, mas mudança/tendência exige suporte efetivo compatível entre períodos, sem seleção automática de membros comuns. Incorporação: CAP-IND-01, CAP-AGR-01, CAP-TMP-01, CAP-TEN-01, RQ-ESC-12, RQ-GOV-22, RQ-RES-06, RQ-RES-10, RQ-REP-14, RQ-REP-15, V-14, 3.1, AMB-01, AT-03, AT-45, AT-54, AT-58, AT-69. Precisão v1.2 (F-05): no agregado multicategorial, o território só integra o suporte com todas as categorias solicitadas avaliáveis; comparabilidade temporal de agregados exige também identidade de TipoContagemAgregada, fundamento da unicidade, unidade de contagem, definição populacional e método (AT-79, AT-80).

**DA-17 — Distância, referência mais próxima e faixas.** Precisão AV-06: mínimo do conjunto completo distingue-se do mínimo entre referências avaliáveis; cobertura incompleta não autoriza substituição silenciosa nas capacidades dependentes (CAP-ESP-02, AT-68). Decisão: distância geodésica direta em quilômetros; reconhecimento de latitude e longitude por estrutura e validade; referencial informado quando disponível; SIRGAS2000 suportado nativamente; referência definida pelo usuário ou por fonte autorizada; empates preservados; faixas [a, b); limitação obrigatória. Complemento aprovado: sem referencial informado, usa-se o padrão previamente autorizado para o contexto; sem nenhum dos dois, pede-se esclarecimento; SIRGAS2000 não é padrão universal. Incorporação: 5.6, CAP-REF-01, CAP-ESP-01 a CAP-ESP-03, CFG-MET, CFG-REF, V-06, AT-02, AT-51. Precisão v1.2 (CFG-MET, CFG-REF): a Configuração Inicial de Implementação não contém referencial padrão, global ou por contexto, de modo que a ausência de referencial informado leva ao esclarecimento; o método é o problema geodésico inverso pelo algoritmo de Karney; CFG-REF é deliberadamente vazio; F-09 não foi incorporada, sem inferência por limites (seções 4.4.5 e 4.4.8, AT-68).

**DA-18 — Ordenação, empate e corte.** Decisão: sem desempate artificial; empatados no corte incluídos por padrão, com aviso de N efetivo; N exato exige regra autorizada ou decisão do usuário; posições compartilhadas. Incorporação: CAP-SUB-02, CAP-SUB-03, AT-02, AT-36.

**DA-19 — Operadores, vocabulário e lógica composta.** Decisão: E, OU e NÃO em lógica de três estados; o LLM estrutura e o motor avalia; vocabulário em português e inglês. Incorporação: CAP-SUB-01, 3.2, CFG-VOC, AT-49.

**DA-20 — Precisão e arredondamento.** Decisão: valor completo em cálculos e decisões; duas casas para medidas contínuas e inteiros para contagens; arredondamento convencional só na apresentação; aumento automático de casas quando o arredondamento ocultar relação relevante; precisão integral disponível. Incorporação: RQ-CAP-03, RQ-REP-05, V-01, CAP-REP-06, AT-47.

**DA-21 — Critérios normativos.** Harmonização AV-09: classificações locais autorizadas permanecem no diagnóstico e exportações com origem e escopo, sem tornarem-se normas globais (RQ-DIA-06, AT-71). Decisão: sem critérios pré-carregados na Configuração Inicial de Implementação (CFG-NOR deliberadamente vazio); critério definido explicitamente pelo usuário, registrado e identificado no resultado; critérios configurados por nova versão, com definição, fonte, escopo e versão; nunca da memória do LLM; escopo restrito, sem propagação. Incorporação: RQ-ESC-02, RQ-GOV-31, RQ-FLX-08, CAP-SUB-01, CFG-NOR, V-03, AT-16, AT-39, AT-46.

**DA-22 — Limitações e heterogeneidade.** Decisão: limitações analíticas acompanham o resultado; eventos técnicos ficam na rastreabilidade; "heterogeneidade" genérica não é usada sem critério formal; condições concretas são descritas. Incorporação: RQ-RES-06, 3.1, CFG-LIM, V-08, V-13.

**DA-23 — Representações e formatos de entrega.** Decisão: interação conversacional estruturada, tabelas, gráficos de barras e de linhas, mapas, painel simples, relatório HTML e exportação em PDF e CSV; a apresentação não cria análise. Incorporação: Parte 13, CAP-REP-01 a CAP-REP-06, RQ-DIA-04, AT-44.

**DA-24 — Persistência e retenção.** Decisão: sessões e linhas temporárias; resultados disponíveis durante a sessão; sem persistência obrigatória; arquitetura preparada para persistência futura; exportações para conservação; aviso obrigatório; sem retenção permanente obrigatória. Incorporação: RQ-FLX-19, RQ-DAD-17, RQ-LIN-01, RQ-RAS-06, CAP-REP-05, AT-44.

**DA-25 — Identificação de usuários e acesso.** Decisão: sessões temporárias e isoladas, sem login e sem compartilhamento; identificação, autenticação e compartilhamento ficam para evolução posterior. Incorporação: RQ-FLX-17, AT-44.

**DA-26 — Parâmetros operacionais.** Decisão: até 2 regenerações do LLM; até 1 nova tentativa para etapa determinística idempotente; tempos limite configuráveis ou limite da plataforma; comunicação estruturada ao esgotar as tentativas; indisponibilidade não confundida com ausência de dados, insuficiência metodológica ou inexistência de capacidade. Incorporação: RQ-DEG-01, RQ-DEG-10, RQ-GOV-01, RQ-ORQ-01, RQ-ORQ-14, RQ-SIN-05, CFG-OPR.

**DA-27 — Proteção de registros individualizados.** Harmonização AV-08: a proteção também antecede o envio de mensagens ao LLM; original protegido fica restrito a C-10, com eventos sem valores pessoais (RQ-DAD-33, AT-73). Decisão: bases individualizadas como insumo de capacidades determinísticas; triagem determinística antes do LLM; campos ambíguos confirmados pelo usuário; identificadores e registros individuais fora do LLM e dos produtos; uso interno pelo motor; visualizador com mascaramento por padrão; aviso e confirmação de uso, sem avaliação jurídica; sem persistência além da sessão; sem limiar universal de supressão. Complemento aprovado: revelação somente por ação explícita do usuário no visualizador, sem autorizar envio ao LLM nem exposição em produtos. Incorporação: 5.5, Parte 18, INV-16, RQ-ARQ-06, RQ-REP-13, RQ-RAS-07, CFG-PRV, AT-37. Precisão v1.2 (F-01, CFG-PRV): regras determinísticas para CPF com dígitos verificadores, e-mail, telefone, campos de nome e de identificação e entidades nominais; pergunta determinística de natureza; placeholders estáveis; o LLM não decide se uma expressão designa pessoa (RQ-DAD-37 a RQ-DAD-39, AT-74, AT-75).

**DA-28 — Limiares e gates de liberação.** Decisão: validação proporcional ao risco e ao impacto; invariantes críticos com aprovação integral; testes por impacto; corpus do LLM representativo, com casos adversariais e ambíguos; erros materiais registrados e avaliados; cenários como catálogo de referência. Incorporação: Parte 20, RQ-EVO-05.

---

**Nota de precisão posterior — nova rodada registrada em §25.8:** os registros precedentes permanecem históricos; as decisões aqui referidas pertencem exclusivamente à nova rodada. DA-13: D2/D4, CAP-CMP-01; DA-19: D5, CAP-SUB-01; DA-26: D6, RQ-DEG-04 distingue tentativa de síntese e atendimento; DA-27: D7, RQ-DAD-38/CFG-PRV; DA-17: D9, RQ-DAD-26/CFG-MET.

## Parte 23 — Tratamento dos pontos P-01 a P-23

Tratamento adotado para cada ponto do Concept identificado na versão 1.0 como não inequívoco, conforme DECISOES_P_01_A_23.md e complementos aprovados.

**P-01 — Ordem entre admissibilidade e interpretação operacional [C §5.2, §6.4].** Tratamento: leitura mínima, pertinência preliminar e famílias candidatas, admissibilidade preliminar, interpretação operacional e reavaliação da admissibilidade; a leitura mínima pode identificar dados explícitos e funções coexistentes da mensagem, sem autorizar análise; a via HABILITADORA precede a análise e não depende de E9 (AV-02, AV-08). Incorporação: RQ-DAD-31, RQ-DAD-34, RQ-FLX-21, 6.2, RQ-FLX-03, RQ-GOV-08, RQ-GOV-10.

**P-02 — Famílias de §3.1 e de §4.3.** Tratamento: §3.1 define o escopo; §4.3 organiza as capacidades; CAP-UNI-01 é suporte transversal; análise individual e conjunta são modos. Incorporação: 1.3, 1.5.

**P-03 — Dupla natureza de "temporariamente indisponível" [C §9.2, §9.11].** Tratamento: indisponibilidade conhecida antes da execução gera ADM-SC; falha ou indisponibilidade durante a execução gera problema operacional; comunicação simples. Incorporação: RQ-ARQ-11, RQ-GOV-12, 15.1, AT-35.

**P-04 — Método proposto pelo usuário [C §3.6, §3.8].** Tratamento: dentro de família permitida, método não incorporado; análise fora do escopo, ADM-FE. Incorporação: 1.4 (EXC-08), 8.6.

**P-05 — Conteúdo do LLM confirmado pelo usuário [C §8.6].** Precisão AV-02: estruturar dados que o usuário já forneceu, validados contra a manifestação original, não cria origem LLM nem exige reconfirmação (RQ-DAD-31). Tratamento: regra preventiva — o LLM não propõe fato ausente para simples confirmação; o agente pede o valor ou o significado; a confirmação de fato introduzido pelo LLM não o torna fonte autorizada. Incorporação: RQ-GOV-03, RQ-GOV-19, RQ-DAD-06, 8.5, AT-16.

**P-06 — "Relação suficiente" com o domínio [C §5.2].** Tratamento: DA-04 e complementos: a pertença decorre de fonte ou metadado autorizado, declaração de domínio da base, reconhecimento determinístico por configuração governada ou declaração explícita do usuário; a simples solicitação de uma categoria não é declaração. Incorporação: RQ-GOV-04, RQ-DAD-19, 4.3, AT-48, AT-55 a AT-57; na v1.2, FTS_CONTEXTUAL e AT-88.

**P-07 — Materialidade da ambiguidade [C §5.7, §9.4].** Tratamento: é material quando leituras plausíveis alteram de forma relevante objeto, universo, parâmetros, método, capacidades, entregáveis ou significado do resultado. Incorporação: RQ-GOV-16, RQ-GOV-17.

**P-08 — Execução isolada [C §4.4, §5.9].** Tratamento: uma parte só é executada se estruturalmente independente, sem mudança silenciosa de significado e com resultado interpretável isoladamente; as partes não executadas são comunicadas junto com os resultados parciais. Incorporação: RQ-GOV-29, RQ-GOV-30, V-09, AT-41.

**P-09 — Único elemento não avaliável [C §8.11, §9.2].** Tratamento: com parte avaliável, resultado com limitação; sem nenhum elemento avaliável, bloqueio por insuficiência de dados ou por condição necessária não satisfeita. Incorporação: RQ-CAP-08.

**P-10 — Conflito entre fontes [C §5.3, §9.2].** Tratamento: DA-03; substituição explícita não é conflito; correção semântica explícita é aceita no escopo permitido, com registro; conflito real sem precedência gera pendência; configuração não é sobrescrita. Incorporação: RQ-GOV-21, RQ-DAD-08, RQ-LIN-12.

**P-11 — Pertinência incerta [C §5.2, §9.2].** Tratamento: estado transitório tratado por pendência. Incorporação: RQ-GOV-05, 3.1.

**P-12 — Unidade fora do universo [C §7.4, §9.2].** Tratamento: avaliabilidade FORA_DO_UNIVERSO, sem conversão em zero, ausência ou não avaliável. Incorporação: RQ-DAD-11.

**P-13 — Relações comparativas [C §4.3.7].** Tratamento: DA-13, com compatibilidade entre contextos segundo AV-05. Incorporação: CAP-CMP-01, RQ-ORQ-13.

**P-14 — Escopo padrão de decisões [C §7.6, Caso 11].** Tratamento: DA-06, com o complemento de escopo na solicitação corrente e extensão à linha por "nesta análise"; na v1.2, escopo herdado de pendência e dimensões da linha (F-07). Incorporação: RQ-LIN-07, RQ-LIN-08, RQ-LIN-19.

**P-15 — Limites do exame habilitador [C §3.3].** Tratamento: DA-02, com via HABILITADORA específica para upload e conjunto conversacional (AV-08), sem análise substantiva. Incorporação: RQ-DAD-13, RQ-DAD-34, CAP-EXA-01.

**P-16 — Painéis e séries [C §4.3.14, §8.5].** Tratamento: DA-23. Incorporação: RQ-REP-08, RQ-REP-10.

**P-17 — Mudança nula entre períodos [C §4.3.9].** Tratamento: DA-14. Incorporação: CAP-TMP-01, 3.1.

**P-18 — Estado de interface e seleção [C §5.8, §4.3.14, §11.11].** Tratamento: nova solicitação analítica somente pela conversação com o LLM; controles estruturados permitidos para upload, navegação, filtros, seleção, visualização, confirmação de privacidade, exportação e resposta a opções de pendências já estruturadas, sem iniciar análise; seleção usada em solicitação posterior é capturada como manifestação do usuário; o canal de entrada tipada da versão 1.0 foi removido. Incorporação: INV-18, 6.7, RQ-REP-06, RQ-ORQ-02, RQ-DEG-02, RQ-DEG-05, AT-13, AT-20.

**P-19 — Heterogeneidade [C §9.8].** Tratamento: DA-22. Incorporação: RQ-RES-06, V-13.

**P-20 — Controles de privacidade [C §3.8].** Tratamento: DA-27 e AV-08; recepção de arquivo ou mensagem, triagem determinística e proteção antes do LLM, estruturação admitida, exame habilitador, confirmações necessárias e autorização analítica; execução interna e produtos territoriais/agregados. Incorporação: 5.5, RQ-DAD-31 a RQ-DAD-35, Parte 18; na v1.2, RQ-DAD-37 a RQ-DAD-39 e RQ-DAD-42 (F-01, F-08).

**P-21 — Combinação de categorias e agregados temporais [C §3.2, §4.3.9].** Tratamento: análise lado a lado permitida; a agregação de categorias ou de territórios segue a regra de sobreposição de CAP-AGR-01, que distingue soma de contagens de pessoas únicas e compõe o denominador conforme a dimensão agregada (AV-01); soma, média, acumulado ou outro agregado temporal exigem método específico incorporado; o LLM não inventa método de combinação. Incorporação: RQ-ESC-12, CAP-AGR-01, 8.6, AT-54.

**P-22 — Perguntas redundantes e regra conservadora [C §5.5, §9.4].** Tratamento: não perguntar o que está determinado; perguntar quando houver leituras plausíveis com consequências materiais distintas. Incorporação: RQ-GOV-14, RQ-GOV-20, AT-66 (controle determinístico de AV-04).

**P-23 — Papel diagnóstico [C §5.9, §8.4].** Tratamento: o LLM propõe entregáveis e a governança os valida; ambiguidade material gera pergunta; resultados intermediários não são promovidos silenciosamente; incorporação por pedido ou aceitação do usuário. Incorporação: RQ-GOV-28, RQ-DIA-03, AT-22.

---

**Nota de precisão posterior — nova rodada registrada em §25.8:** os registros precedentes permanecem históricos; as decisões aqui referidas pertencem exclusivamente à nova rodada. P-08: D1/D4/D12, RQ-FLX-01/02/04 e RQ-GOV-28/29; P-09: D4/D5/D11, RQ-CAP-08 e RQ-RES-04/10 distinguem avaliabilidade, causa e resultado.

## Parte 24 — Registro da revisão de consistência (v1.1)

### 24.1. Verificações

| Verificação | Método | Resultado |
|---|---|---|
| Referências cruzadas de identificadores (RQ, INV, FAM, EXC, C, CFG, AMB, CAP, FN, V, EV, AT, M, DA, P, AV) | Automatizada | 590 identificadores definidos; nenhuma referência sem definição; nenhuma definição duplicada |
| Referências a seções e Partes desta SPEC | Automatizada | Todas resolvem para títulos existentes |
| Referências ao Concept | Automatizada, contra os títulos de CONCEPT.md | Referências verificadas contra as seções existentes; nenhuma seção inexistente |
| Casos citados | Automatizada | Todos entre 1 e 24; cada caso tem cenário próprio (AT-01 a AT-24) |
| Forma de verificação por requisito | Automatizada | 269 requisitos RQ, todos com forma de verificação indicada |
| Contagens | Automatizada | 28 decisões registradas; 23 pontos tratados; 10 correções AV incorporadas; 73 cenários; 18 invariantes; 14 regras do validador; 9 métricas; 25 capacidades; 6 funções baseadas em LLM; 24 itens CFG; 47 tipos de evento |
| Estrutura do documento | Automatizada | Tabelas com número de colunas consistente; blocos de código balanceados; Partes 0 a 24 presentes; versão 1.1 para revisão |
| Terminologia | Automatizada | "o LLM" em todo o documento; nenhuma forma feminina remanescente |
| Remanescentes da v1.0 nas Partes 0 a 21 | Automatizada | Nenhuma ocorrência de decisão em aberto, regra transitória, canal de entrada tipada ou método de teste no lugar de método decidido |
| Compatibilidade com o Concept | Releitura e inspeção das alterações aprovadas | Nenhuma contradição identificada na incorporação AV-01 a AV-10; Concept preservado |
| Coerência entre decisões | Inspeção | Tensões harmonizadas: DA-10 × DA-16 (agregado parcial como método autorizado); P-05 × DA-02 e [C §7.3] (proposta de significado por regra configurada; o LLM só aponta correspondências); DA-01 × P-03 (disponibilidade operacional fora da configuração congelada); regra de agregação com possível sobreposição × P-21 e DA-09 (agregação de categorias e territórios pela mesma regra); reconhecimento governado × DA-04 (vocabulário não exaustivo; NAO_RECONHECIDA não equivale a NAO_PERTINENTE) |

### 24.2. Principais alterações em relação à versão 1.0

| Partes | Alteração |
|---|---|
| 0 | Situação sem decisões em aberto; glossário ampliado (sessão, idioma, triagem, campo protegido, visualizador, escala, referencial, agregado parcial, soma das contagens dos componentes, premissa factual do usuário, substituição explícita, critério normativo do usuário, disponibilidade operacional); termos da v1.0 retirados |
| 1 e 2 | Critério normativo do usuário (RQ-ESC-02); pertença de categorias sem lista fechada (RQ-ESC-04); agregação de categorias e agregados temporais (RQ-ESC-12); matriz de autoridade ampliada; INV-04, INV-15, INV-16 e INV-18 reformulados; triagem em C-04, controles e visualizador em C-01, exportações em C-11, snapshot fixo em C-09; RQ-ARQ-11 |
| 3 e 4 | Novas enumerações e entidades (Sessao, CriterioComposto, CampoProtegido, TipoContagemAgregada, FundamentoUnicidade, ReconhecimentoFTS); tipos de ParametroDecisao ampliados; entrada tipada removida; configuração congelada por sessão, catálogo CFG com o conteúdo decidido e reconhecimento governado de categorias (4.3) |
| 5 e 6 | Introdução deliberada de dados como autorização inicial de habilitação, distinta da analítica (precisada na seção 24.6); semântica declarada; unidade de contagem; pertença de categorias; triagem com aviso obrigatório (5.5); coordenadas e referencial (5.6); descarte ao fim da sessão; sessão, idioma e aviso de sessão temporária (6.1); nova solicitação apenas pela conversação (6.7) |
| 7 | Pertinência (DA-04); regra preventiva (P-05); substituição explícita e conflito (DA-03); valores e premissas factuais do usuário (DA-07); critério normativo (RQ-GOV-31); separabilidade e comunicação da execução parcial (P-08) |
| 8 | Todas as capacidades ativas, com os métodos decididos (tipo 7 com fronteira na classe inferior, tendência com monotonicidade não estrita e ao menos uma mudança estrita, distância geodésica, lógica E/OU/NÃO, inclusão de empates no corte, escala padrão, regra de agregação com possível sobreposição); CAP-REP-05 e CAP-REP-06 |
| 9 a 12 | Suspensão sem mudança de configuração; parâmetros operacionais; limitações analíticas e técnicas; escopo na solicitação corrente; recálculo implícito na solicitação; relatório de diagnóstico |
| 13 | Arredondamento e exceção de apresentação; escala; tipos e formatos de entrega; controles de interface; visualizador da base; rótulos de agregados |
| 14 a 17 | Validador bilíngue; limitação de distância; heterogeneidade; rótulo da soma das contagens dos componentes (V-14); comunicação de indisponibilidade; modo degradado sem canal alternativo; novos eventos; retenção restrita à sessão |
| 18 e 19 | Proteção de registros individualizados conforme DA-27; evolução com configuração aplicada a novas sessões |
| 20 | Validação proporcional ao risco; invariantes críticos; conjunto essencial; cenários AT-43 a AT-54; métricas sem limiar numérico |
| 21 a 23 | Matriz atualizada; registro das decisões incorporadas; tratamento dos pontos P |
| Ajustes finais | Pertença de categoria sem inferência pela simples solicitação e com reconhecimento determinístico por CFG-DOM e CFG-VOC, declaração de domínio da base e ausência de pergunta obrigatória após o upload (4.3, RQ-ESC-04, RQ-DAD-01, RQ-DAD-19, RQ-GOV-04, RQ-GOV-20, RQ-GOV-32, AT-48, AT-55 a AT-57); regra de agregação com possível sobreposição para territórios e categorias (CAP-IND-01, CAP-AGR-01, RQ-ESC-12, RQ-GOV-22, RQ-RES-06, RQ-REP-14, V-14, AT-45, AT-50, AT-54); leituras 17 a 26 revisadas |

### 24.3. Leituras adotadas na incorporação e sua revisão

Aceitas na revisão anterior à v1.1:

1. DA-04 × Caso 24 — pedido sobre força de trabalho de outro setor, sem declaração explícita, é não pertinente, e o agente não sugere a declaração (RQ-GOV-04, RQ-GOV-32).
2. DA-10 × DA-16 — o agregado parcial é o método autorizado previsto na exceção de DA-10 (CAP-AGR-01).
3. P-05 × DA-02 — proposta de significado só por regra configurada; o LLM aponta correspondências com elementos autorizados (RQ-DAD-06).
4. DA-19 — critérios sucessivos equivalem à conjunção E, independentemente da ordem (CAP-SUB-01).
5. DA-18 — rótulos de posição 1, 2, 2, 4 (CAP-SUB-02).
6. DA-20 — regra de dígitos sobre o valor absoluto e escopo da exceção de apresentação (RQ-REP-05).
7. DA-17 — geodésica calculada no elipsoide do referencial (CAP-ESP-01).
8. DA-03 — divergência material como diferença de valor, após normalização, em elemento usado por etapa autorizada (RQ-GOV-21).
9. DA-16 — agregado parcial automático sobre os membros avaliáveis (CAP-AGR-01).
10. DA-11 — posição relativa pela ordenação e pela classe de quantil; posição percentual não incorporada (CAP-DIS-01).
11. DA-23 — CSV em precisão integral (CAP-REP-06).
12. DA-12 — último intervalo fechado (CAP-DIS-03).
13. DA-05 — determinação do idioma da sessão (RQ-FLX-18).
14. DA-21 — só a classificação definida é atribuída; critérios sobrepostos geram pergunta (RQ-GOV-31).
15. DA-28 — conjunto essencial de cenários (RQ-QUA-03).
16. DA-15 — rótulos da DA-15 equivalentes aos códigos do Concept (3.1).

Revisadas nesta versão:

17. Confirmada — DA-01 × P-03: disponibilidade operacional mantida fora da configuração congelada, para permitir ADM-SC por indisponibilidade temporária durante a sessão (RQ-ARQ-11, RQ-GOV-12).
18. Confirmada — P-18: resposta por opção a pendência estruturada processada deterministicamente, inclusive em modo degradado, até a próxima etapa que exija o LLM (RQ-FLX-15, RQ-DEG-05).
19. Confirmada — DA-15: base com menos de quatro períodos gera BLQ-MET antes da execução; unidade com menos de quatro observações é NAO_AVALIAVEL; quebra de comparabilidade na série gera NAO_AVALIAVEL (INCOMPARABILIDADE), e o trecho comparável só é analisado como alternativa escolhida pelo usuário (CAP-TEN-01).
20. Confirmada — DA-09: "resultar da base" significa conteúdo explícito da base ou regra configurada; o nome do campo, sozinho, não estabelece a unidade de contagem (RQ-DAD-18).
21. Corrigida e refinada — DA-04: a simples solicitação de uma categoria como objeto não é declaração de pertença; a pertença decorre de fonte ou metadado autorizado, de declaração de domínio da base (no escopo da base), de reconhecimento determinístico por configuração governada ou de declaração explícita do usuário; sem nenhuma dessas vias, PERTINENCIA_INCERTA e pedido de esclarecimento; pedido sobre a FTS em conjunto sem composição estabelecida gera pergunta (RQ-ESC-04, RQ-DAD-19, RQ-GOV-04, RQ-GOV-32, 4.3, AT-48, AT-55 a AT-57).
22. Confirmada — DA-17: reconhecimento de coordenadas por nome, tipo e faixa válida; pontos em referenciais diferentes sem transformação autorizada geram BLQ-MET (RQ-DAD-25, RQ-DAD-27).
23. Confirmada — DA-27: estrutura sanitizada com nomes, tipos, papéis e marcação de proteção de todos os campos, sem valores protegidos (RQ-DAD-23).
24. Confirmada — DA-20: casas adicionais aplicadas apenas aos valores envolvidos na relação (RQ-REP-05).
25. Confirmada — DA-13: razão e diferença relativa com base zero resultam NAO_AVALIAVEL (BASE_ZERO) (CAP-CMP-01).
26. Confirmada e harmonizada com a regra de agregação — P-21: a agregação de categorias segue CAP-AGR-01; o total de pessoas únicas exige deduplicação ou informação que estabeleça ausência de sobreposição, e a soma das contagens por categoria é produzida a pedido, rotulada como tal; contagem de pessoas sem filtro de categoria não é combinação de categorias (CAP-IND-01, CAP-AGR-01, RQ-ESC-12, 8.6).

### 24.4. Decisões incorporadas nesta revisão

**Regra de agregação com possível sobreposição (complemento de DA-16, com DA-07 e DA-09).** Aplica-se a territórios e a categorias quando a unidade de contagem é pessoa. A pessoa é contada uma vez em cada componente do nível analisado em que está presente. A contagem de pessoas únicas no agregado exige deduplicação sobre a união dos componentes ou informação autorizada que estabeleça ausência de sobreposição, inclusive premissa fornecida explicitamente pelo usuário, registrada com origem, escopo, conteúdo e impacto. Sem essas condições, a soma não é apresentada como pessoas únicas, mas pode ser produzida a pedido do usuário como soma das contagens dos componentes, com possível dupla contagem explicitada; preferência de apresentação não altera esse rótulo. Incorporação: CAP-IND-01, CAP-AGR-01, RQ-ESC-12, RQ-GOV-13, RQ-GOV-22, RQ-RES-06, RQ-REP-14, V-14, 3.1, 3.2, AT-45, AT-50, AT-54.

**Pertença de categoria à FTS (complementos de DA-04).** A simples solicitação de uma categoria não é declaração de pertença. A pertença decorre de fonte ou metadado autorizado; de declaração de domínio da base, que vale no escopo daquela base e não gera classificação universal; de reconhecimento determinístico por vocabulário governado de CFG-DOM e CFG-VOC, não exaustivo, com resultados FTS_INEQUIVOCA, FTS_AMBIGUA e NAO_RECONHECIDA; ou de declaração explícita do usuário. O LLM apenas propõe correspondência com aliases existentes e aponta ambiguidades; não há pergunta obrigatória sobre o domínio após o upload; NAO_RECONHECIDA não equivale a NAO_PERTINENTE. Incorporação: RQ-ESC-04, 4.3 (RQ-CFG-08 a RQ-CFG-11), RQ-DAD-01, RQ-DAD-06, RQ-DAD-19, RQ-GOV-04, RQ-GOV-20, RQ-GOV-32, AT-48, AT-55 a AT-57.

### 24.5. Conteúdo de configuração necessário à implementação (encerrado na v1.2)

Na versão 1.1, esta seção listava conteúdo de configuração a elaborar. Na versão 1.2, esse conteúdo está integralmente definido na Configuração Inicial de Implementação (seção 4.4), sem itens remanescentes:

1. CFG-TPL — TPL-01 a TPL-12, em português e inglês, inclusive os avisos obrigatórios de RQ-FLX-19, RQ-DAD-22 e V-06 (seção 4.4.16).
2. CFG-VOC, CFG-AMB e CFG-LEX — vocabulários, correspondências de cabeçalhos, padrões de associação de dados conversacionais, marcadores, gatilhos e léxicos em português e inglês (seções 4.4.9, 4.4.10 e 4.4.15).
3. CFG-PRV — regras determinísticas de triagem de arquivos e mensagens antes do LLM, pergunta de natureza de entidade nominal e placeholders (seção 4.4.22).
4. CFG-DOM e CFG-VOC — categorias de reconhecimento automático e contextual e termos genéricos ambíguos, em português e inglês (seção 4.3); ampliações somente por nova versão (RQ-EVO-10).

Os antigos conteúdos opcionais são, nesta versão, vazios deliberados com comportamento definido: nenhum referencial geodésico padrão, global ou por contexto (esclarecimento, RQ-DAD-26); nenhuma escala de apresentação configurada por indicador (por 1.000 habitantes, CAP-IND-02); nenhuma malha territorial configurada (mapas dependem de geometria autorizada presente nas bases, RQ-REP-07; CFG-TER deliberadamente vazio). O registro da incorporação está na Parte 25.

### 24.6. Incorporação das correções adversariais comportamentais

Rodada de 2026-09-28: incorporação exclusiva das correções consolidadas e aprovadas AV-01 a AV-10, com harmonização imediata. Mantidos IMPLEMENTATION SPECIFICATION v1.1 — para revisão, precedência e conteúdo do Concept, finalidade, famílias, exclusões e arquitetura LLM + governança determinística. As remissões DA/P registram rastreabilidade; nenhuma decisão encerrada foi reaberta.

| Correção | Incorporação principal | Aceite específico |
|---|---|---|
| AV-01 | CFG-IND, CAP-AGR-01, suporte do resultado, RQ-RES-10, DA-16/P-21: denominador por dimensão, sem repetir população por categoria | AT-58 |
| AV-02 | OrigemBase, funções coexistentes, RQ-DAD-28 a RQ-DAD-33, RQ-FLX-21, CFG-FON/CFG-VOC: arquivos comuns, dados no chat e valores complementares | AT-59 a AT-65, AT-73 |
| AV-03 | Glossário, RQ-DAD-18, RQ-DAD-35, CAP-IND-01/CAP-AGR-01: observação, medida e identidade de deduplicação | AT-50, AT-60 |
| AV-04 | Matriz de autoridade, InterpretacaoOperacional, RQ-GOV-14/RQ-GOV-15/RQ-GOV-20: resolução determinística sem pergunta e com origem real | AT-62, AT-66 |
| AV-05 | INV-09/INV-10, ContextoConsistencia, RQ-FLX-06, CAP-CMP-01, RQ-ORQ-06/RQ-ORQ-07/RQ-ORQ-12/RQ-ORQ-13, RQ-DIA-05 | AT-67 |
| AV-06 | CAP-ESP-02 e dependentes, RQ-ORQ-09, RQ-RES-10, RQ-REP-15: alcance do mínimo e cobertura por unidade | AT-68 |
| AV-07 | CAP-AGR-01, CAP-TMP-01, CAP-TEN-01, suporte_agregado, RQ-RES-10, RQ-REP-15: suporte temporal compatível sem membros comuns automáticos | AT-45, AT-69 |
| AV-08 | TipoAutorizacao, RQ-ARQ-02, RQ-DAD-02/RQ-DAD-13/RQ-DAD-20/RQ-DAD-33/RQ-DAD-34, RQ-FLX-03, seção 7.7, CAP-EXA-01, RQ-DEG-02, rastreabilidade | AT-26, AT-65, AT-70, AT-73 |
| AV-09 | RQ-FLX-08, RQ-DIA-06, DA-21: critério local autorizado preservado no diagnóstico e entrega | AT-46, AT-71 |
| AV-10 | FuncaoConteudo, RQ-SIN-02/RQ-SIN-06/RQ-SIN-10, V-02/V-03/V-05/V-07/V-12: menção metodológica ancorada distinta de afirmação analítica | AT-28, AT-72 |

Verificação transversal: origens preservadas; LLM nunca fonte; proteção válida nas duas portas; exame sem análise substantiva; comparação continua condicionada à compatibilidade; agregado isolado não é invalidado por incomparabilidade temporal; critério local não vira configuração; afirmação analítica exige resultado estruturado. Não foi identificada contradição com o Concept nem decisão adicional nesta rodada. O conteúdo de configuração a elaborar continua descrito em 24.5, sem novas decisões conceituais. (Nota da versão 1.2: esse conteúdo foi definido na Configuração Inicial de Implementação, seção 4.4; ver 24.5 e Parte 25.)

Limites da verificação: inspeção e verificações documentais automatizadas; os cenários da Parte 20 são critérios de aceite, não testes de sistema executados nesta incorporação. Não houve implementação de código do sistema.

---

**Nota de precisão posterior — nova rodada registrada em §25.8:** os registros precedentes permanecem históricos; as decisões aqui referidas pertencem exclusivamente à nova rodada. AV-10: D8, CFG-DOC/V-16 e RQ-SIN-05/10 limitam conteúdo metodológico a texto canônico ou forma previamente autorizada, com o bloco opcional de TPL-12.

## Parte 25 — Registro da incorporação F-01 a F-12 e da Configuração Inicial de Implementação (v1.2)

Rodada de 2026-09-29: incorporação exclusiva das decisões técnicas F-01 a F-12 (DECISOES_F01_A_F12_FINAL.md) e da Configuração Inicial de Implementação (CONFIGURACAO_INICIAL_IMPLEMENTACAO_FINAL.md), com harmonização imediata. Mantidos o Concept, sua precedência, a finalidade, as famílias, as exclusões e a arquitetura LLM + governança determinística. Não foram criadas capacidades além de CAP-ROT-01 nem feitas escolhas tecnológicas (RQ-DOC-06). Esta parte é registro; as regras estão nas partes normativas indicadas.

### 25.1. Decisões técnicas F-01 a F-12

| Decisão | Conteúdo incorporado | Localização principal | Cenários |
|---|---|---|---|
| F-01 | Privacidade pré-LLM: identificadores estruturados, entidades nominais, pergunta determinística e placeholders; o LLM não decide se expressão designa pessoa | INV-16, C-04, C-10, RQ-DAD-20, RQ-DAD-33, RQ-DAD-37 a RQ-DAD-39, RQ-PRV-02, 4.4.22 | AT-37, AT-63, AT-74, AT-75 |
| F-02 | Propriedades semânticas exigidas por operação; definição de aditividade | RQ-DAD-05, RQ-DAD-36, 5.2, CAP-IND-02, CAP-AGR-01, RQ-GOV-24 (item 5), 4.4.6 | AT-76 |
| F-03 | Mudança de foco sem caráter histórico; retorno ao recorte; caráter histórico só por substituição de estado | MotivoNaoVigencia, VinculoResultadoLinha, INV-09, RQ-FLX-06, RQ-ORQ-06, RQ-ORQ-07, RQ-GOV-24 (item 11), RQ-LIN-13, RQ-LIN-14, RQ-LIN-20, RQ-DIA-01, RQ-REP-15, V-11 | AT-42, AT-67, AT-77 |
| F-04 | Qualificadores obrigatórios preservados em toda apresentação | RQ-RES-11, RQ-REP-15, V-15, CAP-ESP-02, 4.4.14, 4.4.20 | AT-78 |
| F-05a | Território só integra agregado multicategorial com todas as categorias avaliáveis | CAP-AGR-01, RQ-RES-10 | AT-79 |
| F-05b | Compatibilidade metodológica temporal de agregados | CAP-AGR-01, CAP-TMP-01, CAP-TEN-01, CAP-CMP-01, RQ-ORQ-13, RQ-GOV-24 (item 8) | AT-80 |
| F-06 | Pequena base conversacional, valor factual complementar e declaração semântica; manutenção do valor complementar no objeto da sessão, com associação aplicável registrada e recuperação compatível sem exclusividade (v1.2.1) | TipoDadoConversacional, RQ-DAD-32, RQ-DAD-40, RQ-LIN-21 | AT-63, AT-81 |
| F-07 | Escopo herdado da pendência; dimensões da linha; restrição expressa; não repergunta | Pendencia, ParametroDecisao, EstadoLinha, RQ-FLX-04, RQ-GOV-14, RQ-LIN-07, RQ-LIN-08, RQ-LIN-19, RQ-INC-05, 4.4.18 | AT-11, AT-82 |
| F-08 | Estados explícitos da entrada; pendência habilitadora vinculada à entrada; reapresentação sem duplicata | StatusBase, Pendencia, Base, RQ-DAD-02, RQ-DAD-34, RQ-DAD-42, RQ-FLX-22, RQ-GOV-24 (item 4), RQ-INC-05, EV-ESTADO-BASE | AT-70, AT-83 |
| F-09 | Não incorporada (decisão rejeitada): não há método de inferência por limites | CAP-ESP-02 (vedação expressa) | AT-68 (variante) |
| F-10 | Comparação genérica: valores lado a lado, igualdade ou ordem e diferença absoluta; razão e diferença relativa apenas se explícitas; universo da linha | CAP-CMP-01 | AT-84 |
| F-11 | Associação conversacional só com relação estrutural única validável | RQ-DAD-31, RQ-DAD-41, FN-INT-01, 4.4.9 | AT-85 |
| F-12 | Numerais ("um"/"uma" e artigos) e explicações metodológicas ancoradas em CFG-DOC | V-01, V-02, V-16, RQ-SIN-06, RQ-SIN-10, RQ-FLX-07, RQ-FLX-08, FN-META-01, 4.4.15, 4.4.23 | AT-86 |

**Nota de precisão posterior — nova rodada registrada em §25.8:** os registros precedentes permanecem históricos; as decisões aqui referidas pertencem exclusivamente à nova rodada. F-10: D2, CAP-CMP-01 e CFG-VOC; F-01: D7, reconhecimento estrutural pré-LLM em RQ-DAD-38; F-12: D8, CFG-DOC/V-16 e TPL-12; F-08/F-11: D10, RQ-DAD-43 e entradas independentes/combinação; F-05a/F-05b: conteúdo preservado, D11 qualifica apenas o desfecho causal em RQ-CAP-08/RQ-ORQ-13.

### 25.2. Configuração Inicial de Implementação

Os 24 itens estão definidos na seção 4.4 (4.4.1 CFG-DOM a 4.4.24 CFG-OPR), resumidos no catálogo 4.2, com o vocabulário de categorias na seção 4.3. Vazios deliberados, todos com comportamento definido: CFG-TER; CFG-REF; CFG-NOR; CFG-AUS quanto a métodos de imputação; e, dentro de outros itens, referencial padrão e transformação entre referenciais, desempate, método de intervalos e posição percentual numérica (CFG-MET), escala configurada por indicador (CFG-IND), alias inglês de BIOMEDICINA (CFG-DOM), correspondência determinística de "turnover" (CFG-VOC), regras de anonimização e limiar de supressão (CFG-PRV) e fonte configurada (CFG-FON). O termo MVP foi substituído por "Configuração Inicial de Implementação" ou por "nesta versão" (RQ-DOC-06).

### 25.3. CAP-ROT-01

Incorporada ao catálogo 8.3 na FAM-08, como capacidade determinística ATIVA, com: contrato na seção 8.4; indicadores ROTATIVIDADE_COORTE_INICIAL e PERMANENCIA_COORTE_INICIAL em CFG-IND (4.4.6); vocabulário PT/EN em CFG-VOC (4.4.9); método em CFG-MET (4.4.5); privacidade em RQ-PRV-10 e RQ-PRV-05; detalhe IDENTIDADE_LONGITUDINAL_INSUFICIENTE em DetalheMotivo; identidade longitudinal em RQ-DAD-35; qualificador "da coorte inicial" em RQ-RES-11, RQ-REP-11 e V-15; não abrangências na seção 8.6; testes ROT-AT-01 a ROT-AT-09 (20.7) e cenário de fluxo AT-90. Não altera a finalidade da FAM-08, não substitui CAP-TMP-01 ou CAP-TEN-01 e não cria outra capacidade.

### 25.4. Conteúdo substituído

| Versão 1.1 | Versão 1.2 | Origem |
|---|---|---|
| Semente conservadora de reconhecimento de categorias, com psicólogo ausente e sem categorias contextuais (4.3) | Vocabulário da Configuração Inicial: 15 categorias de reconhecimento automático, 3 de reconhecimento contextual (FTS_CONTEXTUAL) e termos ambíguos, PT/EN | CFG-DOM |
| StatusBase CARREGADA, AGUARDANDO_CONFIRMACAO, AUTORIZADA e DESCARTADA; evento EV-AUTORIZACAO-BASE | StatusBase RECEBIDA, TRIADA, AGUARDANDO_CONFIRMACAO, EXAMINADA, DISPONIVEL, BLOQUEADA e DESCARTADA; evento EV-ESTADO-BASE | F-08 |
| Todo componente NAO_VIGENTE apresentado como histórico (RQ-DIA-01, V-11) | Caráter histórico somente por SUBSTITUICAO_DE_ESTADO; resultado deslocado é contemporâneo | F-03 |
| Referencial padrão por contexto em CFG-MET como via operante (RQ-DAD-26) | Nenhum referencial padrão; esclarecimento; algoritmo de Karney | CFG-MET |
| Sinais lexicais de projeção e previsão em RQ-GOV-09 | Padrões PT/EN de CFG-EXC como sinais de rechecagem; projeção pelo gate de admissibilidade | CFG-EXC |
| "No MVP", "configuração v1.1" e "sementes" dos léxicos | "Nesta versão", Configuração Inicial de Implementação e grupos de CFG-LEX | RQ-DOC-06, CFG-LEX |
| Explicação metodológica ancorada em "contrato ou CFG" | Âncora DOC: de CFG-DOC, verificada por V-16 | F-12 |
| Seção 24.5 com conteúdo de configuração a elaborar | Seção 24.5 encerrada | RQ-CFG-12 |
| AT-57 com "psicólogo" não reconhecido | "Psicólogo" FTS_INEQUIVOCA; "assistente social" FTS_CONTEXTUAL | CFG-DOM |
| Correspondência territorial "em CFG-TER" como via | Correspondência por dado, metadado, fonte autorizada ou manifestação explícita; CFG-TER vazio | CFG-TER |

**Nota de precisão posterior — nova rodada registrada em §25.8:** os registros precedentes permanecem históricos; as decisões aqui referidas pertencem exclusivamente à nova rodada. A correspondência territorial "por dado" da tabela histórica de §25.4 recebe a precisão D3 em CFG-TER: igualdade da chave aplica correspondência somente após significado longitudinal autorizado, com escopo e exceções.

### 25.5. Leituras adotadas na incorporação

As leituras abaixo registram a incorporação da v1.2 e as correções expressamente autorizadas para a v1.2.1. As decisões adicionais validadas no comando de remediação permanecem preservadas; as remediações não alteram o Concept nem expandem o escopo.

1. FTS_CONTEXTUAL foi criado como valor de ReconhecimentoFTS para representar as categorias contextuais de CFG-DOM; "contexto autorizado suficiente" é elemento ancorado em fonte autorizada ou em estado válido e aplicável que estabeleça, no escopo, a pertença à FTS.
2. ACS e ACE com outra leitura materialmente plausível seguem o esclarecimento previsto para FTS_AMBIGUA (RQ-CFG-13).
3. Os estados de F-08 foram mapeados para StatusBase; BLOQUEADA aplica-se a impedimentos que afetam a entrada como um todo e não se resolvem por pendência habilitadora: materialização integral impossível, autorização de uso negada e falha de integridade.
4. F-03: o motivo de não vigência é registrado no vínculo; havendo os dois motivos, prevalece SUBSTITUICAO_DE_ESTADO; o retorno exato ao recorte restabelece o vínculo VIGENTE e reutiliza o resultado.
5. F-07: pendência sobre dimensão do recorte exigida pela análise da linha tem escopo de linha; parâmetros analíticos permanecem vinculados ao indicador e às categorias do recorte em que foram estabelecidos, preservando o Caso 11 e AT-11.
6. F-06 (remediação v1.2.1): sem linha aplicável na manifestação, o valor permanece associado ao objeto na sessão, com âncora e escopo factuais originais, recuperável por qualquer linha compatível; uso não transfere, não consome e não torna o valor exclusivo. Associação já existente à solicitação/linha continua registrada; restrições e incompatibilidades são respeitadas (RQ-LIN-21).
7. F-05a foi aplicada a todo agregado multicategorial, inclusive de território único; F-05b foi lida como exigência de identidade, entre períodos, de cada componente listado, compreendendo na "deduplicação" o FundamentoUnicidade e o domínio da identidade utilizada.
8. CAP-ROT-01 (consolidada na v1.2.1): não admite agregado parcial de coorte; qualquer componente necessário não avaliável torna a taxa do conjunto NAO_AVALIAVEL, sem remover componentes ou redefinir o conjunto. Identidade insuficiente usa DEPENDENCIA_NAO_AVALIAVEL com IDENTIDADE_LONGITUDINAL_INSUFICIENTE; demais causas preservam seus motivos. Componentes avaliáveis podem ser apresentados separadamente, nunca como taxa do conjunto. CAP-AGR-01 conserva seu agregado parcial. Permanecem: falta de registro não é saída (INV-04); sem gráfico de linhas, por não haver série; comparação entre pares por CAP-CMP-01; mudança ou tendência de taxas como método não incorporado (8.6).
9. A regra de autoridade de CFG-VOC aplica-se a aliases, equivalências, categorias, territórios, unidades, períodos e relações factuais; a identificação da intenção analítica — capacidade, indicador e operação — segue a interpretação operacional validada contra os catálogos fechados de CFG-CAP e CFG-IND (RQ-CFG-15), como já fazia a versão 1.1 nos cenários AT-01, AT-43, AT-50 e AT-54.
10. Literais numéricos (remediação v1.2.1): normalização somente com interpretação materialmente única no contexto autorizado; separadores com leituras materialmente diferentes geram esclarecimento, sem decisão baseada apenas no idioma da sessão. F-12a permanece preservada (CFG-VOC, CFG-LEX, AT-86).
11. CFG-DOC (remediação v1.2.1): o Registro de Proposições Documentais é materializado mecanicamente pelo contrato da seção 4.4.23 e pelo mapa normativo de extração do Anexo A. Os caminhos e tipos são fechados, o denominador usa metodo, cada ID tem um registro normativo PT e os textos fixos EN das fontes permanecem preservados. Não há decisão posterior de granularidade, identificação ou classificação nem geração pelo LLM durante a sessão.
12. TPL-12 não tem bloco próprio de interpretação: a interpretação registrada integra o bloco "Parâmetros e origens".

### 25.6. Verificação da remediação e do controle de regressão (v1.2.1)

A v1.2 foi preservada como base normativa; o relatório de incorporação foi usado como apoio e a v1.1 somente como baseline de regressão. A comparação integral encontrou 186 blocos textuais de diferença entre v1.1 e v1.2, incluindo 61 requisitos existentes alterados e 21 requisitos novos, sem remoção de requisito. As diferenças comportamentais foram classificadas por fundamento: A — incorporações autorizadas; B — harmonizações técnico-normativas necessárias; C — alteração substantiva não explicada. As cinco remediações foram aplicadas e o diff v1.2 → v1.2.1 foi verificado quanto ao escopo. Nenhuma alteração substantiva adicional da classe C foi identificada nos três arquivos examinados. Diferenças editoriais não foram tratadas como regressão.

Preservadas: F-05a inclusive no território único; F-05b com TipoContagemAgregada, FundamentoUnicidade, domínio da identidade quando por deduplicação, unidade de contagem, definição populacional, método/versão e demais componentes materiais; FTS_CONTEXTUAL; esclarecimento de ACS/ACE com leitura alternativa material; distinção entre deslocamento de foco e caráter histórico, precedência de SUBSTITUICAO_DE_ESTADO e retorno ao recorte sob as condições de reuso; as três causas aprovadas de StatusBase.BLOQUEADA; interpretação dentro de “Parâmetros e origens” em TPL-12. F-09 permanece não incorporada. O texto do contrato CAP-AGR-01, seu agregado parcial e as fórmulas aprovadas foram preservados. CFG-MET e o contrato de Karney foram preservados.

Remediações verificadas: valor factual sem linha aplicável recuperável por qualquer linha compatível, sem exclusividade ou transferência; CAP-ROT-01 sem agregado parcial e com motivos próprios preservados; Registro de Proposições Documentais com campos, fontes, IDs, caminhos, tipos, extração, condições e dependências fixados; esclarecimento de notação numérica materialmente ambígua independentemente do idioma; ausência de antecipação de catálogo territorial como mecanismo futuro específico. As variantes de AT-81, AT-86 e ROT-AT-07 registram os critérios de aceite correspondentes.

Integridade documental: 290 requisitos RQ, com numeração contígua em cada prefixo; 18 invariantes; 14 famílias; 11 exclusões; 26 capacidades; 24 itens CFG e 24 subseções principais de configuração; 12 modelos TPL; 7 grupos LEX; 16 regras V; 90 cenários AT; 9 testes ROT-AT; 28 registros DA; 23 P; 6 gatilhos AMB. As enumerações documentais de CFG-DOC foram harmonizadas com 3.1. As definições primárias foram distinguidas de menções e referências para a contagem. O Anexo A fixa a cobertura concreta de fontes e proposições documentais. Foram verificados IDs únicos, resolução de referências internas, existência e exatidão dos trechos, ausência de caminhos não autorizados, estrutura de tabelas e fechamento dos blocos de código. Não foram encontradas referências internas órfãs, definições primárias duplicadas, enumerações incompatíveis, tabelas quebradas, contradições nas remediações ou marcadores operantes de conteúdo ainda a elaborar. Menções históricas a pendências de versões anteriores continuam identificadas como históricas.

Limites da verificação: inspeção e verificações documentais automatizadas sobre os três arquivos fornecidos e a versão produzida. O Concept e os documentos externos de decisões/configuração citados pela v1.2 não foram fornecidos e não foram reconstituídos; suas citações foram preservadas, sem alegar verificação externa do conteúdo. A autoridade adotada foi a indicada no comando de remediação. Os cenários da Parte 20 são critérios de aceite, não testes de sistema executados. Não houve implementação do sistema nem escolha de tecnologia.

### 25.7. Decisões substantivas em aberto e situação de fechamento

Não foi identificada decisão substantiva em aberto após as cinco remediações e o controle de regressão no conjunto documental examinado. Não houve alteração do Concept nem expansão de escopo. As decisões da v1.2 expressamente validadas foram preservadas, e nenhuma alteração substantiva adicional não explicada foi mantida silenciosamente.

CFG-DOC está especificado por contrato determinístico completo e mapa fechado de extração: não permanece definição de granularidade, fonte, identificador, caminho, classificação, condição ou dependência delegada ao implementador. Permanece apenas implementar/materializar tecnicamente o Registro de Proposições Documentais conforme esse contrato. Os demais trabalhos técnicos já previstos — fixação dos valores técnicos de timeout e escolha da implementação do algoritmo de Karney — permanecem sob RQ-DOC-06, sem alteração metodológica ou comportamental.

Situação: **PRONTA PARA AUDITORIA FINAL DE FECHAMENTO.** Esta declaração não é autorização de implementação direta; a auditoria final de fechamento é a etapa seguinte.

---

### 25.8. Remediação documental consolidada v1.2.2 — D1–D12

Baseline: v1.2.1, HEAD dee92faba15f8bc8e9a77a6cced1ce1fe42c7702. Versão resultante: v1.2.2. Data: 2026-09-30. Referência aprovada: PLANO_FINAL_CONSOLIDADO_DE_REMEDIACAO_IMPLEMENTATION_SPEC_D1_D12_TPL12.md; aplicação subordinada ao Concept e restrita ao escopo aprovado. Esta é a única rodada posterior à v1.2.1; não há §25.9.

| Decisão | Conteúdo aplicado | Regras e aceite | Situação |
|---|---|---|---|
| D1 | Execução parcial com pendência | RQ-FLX-01/02/04; RQ-GOV-27/29; AT-91/99 | APPLIED |
| D2 | Papel do parâmetro de referência | CAP-CMP-01; CAP-SUB-01; CFG-VOC; AT-92/93 | APPLIED |
| D3 | Comparabilidade temporal territorial | CFG-TER; RQ-DAD-05/06/30/36; CAP-TMP-01/TEN-01; AT-94 a AT-96 | APPLIED |
| D4 | Comparação parcial | CAP-CMP-01; RQ-GOV-29; RQ-RES-10/11; AT-97 | APPLIED |
| D5 | Árvore do critério composto | CAP-SUB-01; RQ-RES-10; AT-98 | APPLIED |
| D6 | Modo degradado após resultado determinístico válido | RQ-DEG-04; TPL-01/12; AT-100/101 | APPLIED |
| D7 | Entidade nominal pré-LLM | RQ-DAD-38/39; CFG-PRV/VOC; AT-102 a AT-104 | APPLIED |
| D8 | CFG-DOC, V-16 e explicação metodológica; precisão TPL-12 | CFG-DOC; V-16; RQ-SIN-05/10; RQ-REP-01; RQ-RAS-05; TPL-12; AT-105 a AT-107 | APPLIED |
| D9 | Referencial geodésico não suportado | CFG-MET; RQ-DAD-26; CAP-ESP-01; AT-108/109 | APPLIED |
| D10 | Múltiplas planilhas XLSX | RQ-DAD-30/43; CFG-FON; AT-110/111 | APPLIED |
| D11 | Causa raiz do bloqueio | RQ-CAP-08; RQ-ORQ-13/14; RQ-RES-04; AT-112 | APPLIED |
| D12 | Granularidade semântica dos entregáveis | Entregável; RQ-GOV-28/29; RQ-ORQ-01; RQ-RES-04; RQ-QUA-06; AT-113 a AT-115 | APPLIED |

O ajuste de estado agregado distingue StatusSolicitacao do ciclo autorizado das partes independentes E7–E12, preservando AGUARDANDO_USUARIO, retomada restrita e terminalidade de RQ-FLX-01/02/04. O ajuste histórico preserva os corpos DA, P, AV, F e §§25.5–25.7; notas separadas atribuem as novas precisões somente a esta rodada. A precisão D8/TPL-12 incorpora o terceiro bloco opcional "Método e documentação", sem novo template, capacidade, enum, status, motivo analítico, método, fórmula, fonte documental ou registro normativo EN.

**Nota de precisão posterior — nova rodada registrada em §25.8:** as conclusões de §§25.5–25.7 são históricas e permanecem intactas. D8 precisa o uso vigente de CFG-DOC/V-16 e a estrutura de TPL-12, mantendo interpretação em "Parâmetros e origens"; método/fórmula/versão/condições e referências documentais cabem no bloco opcional aplicável. D6 distingue atendimento determinístico válido de tentativa de síntese indisponível. O fechamento vigente é o desta seção, por RQ-DOC-03.

Verificações efetivamente realizadas em 2026-09-30: inspeção normativa das decisões D1–D12, dos estados agregados e por parte, da terminalidade, das dependências efetivas, da classificação causal, das formas documentais e do fallback; revisão dos cenários e variantes da seção 20.9 contra os respectivos contratos; buscas sistemáticas por referências obsoletas, formulações substituídas, IDs órfãos, duplicatas e marcadores editoriais. As duas descrições completas vigentes de TPL-12 contêm os mesmos sete blocos, com o terceiro opcional; permanecem 12 templates. Foram verificadas as 37 linhas afetadas da matriz Concept → SPEC. Nenhuma decisão substantiva adicional foi necessária.

Integridade verificada: 290 requisitos RQ, 18 invariantes, 14 famílias, 11 exclusões, 26 capacidades, 24 itens CFG, 16 validadores, 12 templates, 115 cenários AT e 9 ROT-AT; IDs únicos e numeração dos ATs contígua. Apenas os 20 ATs existentes previstos no plano foram harmonizados; os 9 ROT-AT e os demais ATs anteriores permanecem textualmente preservados. As enumerações canônicas conservam os mesmos valores. A lógica trivalente, os métodos/fórmulas e os corpos dos contratos não afetados foram comparados com a baseline; F-05a/F-05b e a ausência de agregado parcial em CAP-ROT-01 permanecem preservadas. Tabelas e blocos de código verificados; nenhum TODO, TBD, FIXME ou referência interna órfã identificado.

CFG-DOC/Anexo A: cobertura recalculada de 566 fontes normativas e 693 proposições, com 101 proposições existentes atualizadas em texto e exatamente três novos IDs: DOC:CAP-CMP-01.avaliabilidade, DOC:CAP-SUB-01.avaliabilidade e DOC:CAP-SUB-01.saida. Todos os pares fonte/caminho, tipos, textos, condições, intervalos e dependências foram verificados contra as definições primárias e os trechos exatos. Nenhum ID duplicado, caminho/tipo inválido, intervalo inválido ou dependência não resolvida. Um registro normativo PT por id_doc; textos canônicos e formas fixas PT/EN vinculadas às mesmas proposições, com verificação dos campos de interpolação e dos blocos de apresentação. O Anexo A não extrai testes, histórico, notas, o plano ou suas próprias linhas como fontes novas. Duas materializações independentes da mesma versão produziram conteúdos idênticos; o procedimento foi uma verificação editorial externa ao repositório, sem ferramenta de produto ou arquitetura adicional.

Preservação histórica verificada: os 204 trechos não vazios das Partes 22 a 25.7 continuam idênticos e na mesma ordem, excetuadas apenas as notas posteriores separadas, sem reescrever os corpos antigos. CONCEPT.md e o plano aprovado permanecem bit a bit idênticos ao preflight. SHA-256 de CONCEPT.md: E9ED3CFF97BBBFB7598BC3EFBD29D8FACE047B81E43D864FA442CAD9BA055F42; blob Git: 84b6138743300ad0df4908471460c7c3bdc19d3d. O único arquivo do repositório alterado nesta rodada é Docs/IMPLEMENTATION_SPEC.md.

Limites do aceite: verificação documental, normativa e de coerência comportamental sobre a SPEC. Os cenários AT-01–115 e ROT-AT-01–09 são critérios de aceite documentais; não houve execução de testes de software nem implementação tecnológica. A bateria comportamental externa de 50 testes é posterior e não integra esta rodada.

Situação de fechamento: **PASS DOCUMENTAL — PRONTA PARA A BATERIA COMPORTAMENTAL POSTERIOR.** D1–D12: APPLIED. Nenhum blocker aberto. READY_FOR_BEHAVIORAL_BATTERY_50: YES. Esta declaração não afirma aprovação da bateria posterior e não autoriza merge automático.

DECISOES_ADICIONAIS: NENHUMA. Alterações limitadas às consequências necessárias das decisões aprovadas e às harmonizações normativas necessárias; nenhuma mudança substantiva da classe C incorporada.

---

### 25.9. Reconstrução compacta v1.2.4 — D13–D42, D17-A e H1–H3

Data efetiva: 2026-10-02. Branch: fix/spec-remediation-v1.2.4-compact. Baseline normativa: IMPLEMENTATION_SPEC v1.2.2, commit 8fd33a67a3e23fe9d42623f11334b2cf9aef7e79. Referência de controle: v1.2.3, commit 8ac444f12c53bda6b6fe1f243c41c292c906ca40, na branch codex/spec-remediation-v1.2.3, não alterada, usada para conferir materializações anteriores, recuperar o catálogo documental e preservar IDs e rastreabilidade; não é baseline de edição nem dependência de runtime. Autoridade: CONCEPT; decisões humanas aprovadas D13–D28, D17-A e H1–H3; D29–D42, que convertem os achados BFINAL-01 a BFINAL-14.

Enquadramento histórico: os corpos de §§25.5–25.8 permanecem integralmente preservados. As afirmações de §25.8 sobre rodada única, inexistência de §25.9, contagens e prontidão descrevem a publicação v1.2.2, não o fechamento corrente. A v1.2.3 materializou D13–D28, D17-A e H1–H3; a validação comportamental posterior identificou necessidade de remediação, registrada como BFINAL-01 a BFINAL-14 e decidida em D29–D42. Este registro não declara a v1.2.3 integralmente inválida nem reescreve sua história; suas declarações de fechamento não são reproduzidas.

Método: v1.2.2 + delta normativo aprovado = v1.2.4. O delta de D13–D28, D17-A e H1–H3 foi portado do corpo normativo da v1.2.3, em 80 trechos revisados, sem o catálogo inline, o Anexo A e o fechamento daquela versão; D29–D42 foram aplicadas sobre esse resultado. A massa literal das formas PT/EN foi externalizada em Docs/CFG_DOC_CATALOG.yaml (seção 4.4.23.6), extraída mecanicamente do catálogo da v1.2.3. A SPEC conserva definição e contratos de CFG-DOC, regras PT/EN, proibições de tradução e paráfrase livres, fallback, relações componente→id_doc e o mapa id_doc→fonte do Anexo A, regenerado mecanicamente. A externalização altera a organização física, não a autoridade normativa. Não foram criados índice documental separado, banco vetorial, RAG, embeddings ou nova camada de governança.

| Decisões | Materialização principal | Situação |
|---|---|---|
| D13–D28, D17-A, H1–H3 | Delta revisado portado sobre a v1.2.2; matriz 21.1; AT-116–AT-164 | INCORPORADAS |
| D29 | RQ-DAD-20/33/38/39; INV-16; CFG-PRV: evidência positiva pré-LLM, placeholder, esclarecimento só quando material, persistência no escopo de linhagem | INCORPORADA |
| D30 | RQ-CFG-14; CFG-VOC, CFG-AMB, CFG-LEX e CFG-PRV: conceitos canônicos PT/EN, inclusive cidade/city e tinha/teve/had | INCORPORADA |
| D31 | 4.4.23.2 e 4.4.23.6; RQ-QUA-07; V-16: forma EN como apresentação equivalente; dez formas EN corrigidas | INCORPORADA NA NORMA; VALIDAÇÃO EN INTEGRAL PENDENTE |
| D32 | Seção 3.2; CFG-OPC; RQ-GOV-17/18/19; RQ-DEG-05; formas rotulo.* | INCORPORADA |
| D33 | RQ-DAD-37; CFG-PRV: papel tipado, rótulo governado, padrão governado e proteção por padrão | INCORPORADA |
| D34 | CAP-CMP-01; CAP-SUB-01; ContextoDeMedida | INCORPORADA |
| D35 | ResultadoElemento; StatusExecucaoElemento; RQ-ORQ-14; RQ-RES-04/06; RQ-CAP-08 | INCORPORADA |
| D36 | StatusEntregavel com CANCELADO; RQ-FLX-01/02; RQ-ORQ-16; forma `cancelamento` de TPL-12 | INCORPORADA |
| D37 | RQ-FLX-01; RQ-DEG-02: EM_ADMISSAO e classes de prioridade antes da criação de entregáveis | INCORPORADA |
| D38 | CFG-OPR; RQ-FLX-17; TipoInteracaoUsuario; EV-INTERACAO_USUARIO | INCORPORADA |
| D39 | RQ-ORQ-16; RQ-FLX-17; RQ-RAS-02; EV-RETORNO_TARDIO_DESCARTADO | INCORPORADA |
| D40 | RQ-GOV-08/09; CFG-EXC; ConsequenciaExclusao | INCORPORADA |
| D41 | RQ-DAD-34/42: ciclo de reversão sem reativação automática | INCORPORADA |
| D42 | RQ-DAD-31/41; RQ-FLX-21: estrutura e materialização antes de ambiguidade material | INCORPORADA |

D31 — auditoria de equivalência EN, executada de forma contida. Os pares PT/EN foram extraídos do catálogo da v1.2.3 (700 id_doc; 753 formas por idioma). A triagem mecânica, de inventário e pareamento, sem decidir equivalência, conferiu códigos de enum, estado e motivo, IDs normativos, números, variáveis, negações, alternativas, modalidade, quantificadores, condições, listas, tabelas e proporção de tamanho: dos 624 pares base com PT inalterado, 225 têm sinal forte, dos quais 8 são casos conhecidos, 182 só sinal fraco e 217 nenhum sinal; 4 das 53 formas não base têm sinal forte; 76 pares base têm PT alterado nesta versão. Revisão semântica e correção foram aplicadas somente aos dez casos conhecidos — DOC:RQ-FLX-17, DOC:CAP-TMP-01.saida, DOC:CAP-AGR-01.entradas, DOC:CAP-ROT-01.precondicoes, DOC:CAP-ROT-01.parametros, DOC:RQ-REP-02, DOC:CAP-SUB-01.avaliabilidade, DOC:CAP-IND-02.metodo, DOC:RQ-FLX-02 e DOC:FAM-03.natureza —, cujas formas EN recebem versao 1.2.4. Formas EN criadas: base dos três enums novos e 54 formas novas por idioma, rotulo.* de D32 e `cancelamento` de D36. As demais 690 formas EN base e 53 não base da v1.2.3 foram preservadas literalmente, sem reescrita; entre elas, 74 formas EN base cujo PT foi alterado nesta versão mantêm versao 1.2.3 e não são utilizáveis em runtime até seu restabelecimento (4.4.23.6). Revisão preliminar de 25 pares sinalizados, interrompida por instrução de contenção, confirmou 13 divergências com PT inalterado e 4 atualizações exigidas por PT alterado, sem divergência em 8; não aplicadas, constam de registro externo ao repositório como insumo da validação posterior. A equivalência semântica integral do catálogo EN não foi auditada nesta execução e permanece como validação posterior: não bloqueia a construção desta SPEC compacta, mas impede declarar fechamento documental integral PT/EN e aceitar o catálogo como registro vigente (4.4.23.4, passo 10).

Verificações mecânicas efetivamente executadas por script determinístico externo ao repositório sobre a SPEC e o catálogo finais, todas com PASS: working tree; CONCEPT inalterado (blob 84b6138743300ad0df4908471460c7c3bdc19d3d; SHA-256 c095d81f010a34b8b8cea3f7885448d9b84a048bb3cb88331cfdc744e1dfe65f, UTF-8 sem BOM e LF; sem diff contra a baseline); ausência de TODO/TBD não autorizados; IDs de definição primária únicos; referências resolvidas; todos os id_doc esperados presentes; catálogo sem entrada órfã; referências da SPEC a id_doc e formas locais resolvidas; formas PT/EN pareadas; variáveis PT/EN compatíveis; enums, tipos, estados e ATs referenciados existentes; versão SPEC/catálogo compatível; ausência de dependência runtime da v1.2.3; ausência de localizador quebrado; ausência de duplicação normativa acidental. Duas gerações do catálogo e a regeneração do Anexo A produziram resultados idênticos.

Validação documental: inspeção dirigida confirmou D13–D28, D17-A e H1–H3 preservadas no corpo portado; D29–D42 incorporadas; ausência de contradição identificada entre regras novas e anteriores nos requisitos alterados; rótulos de opções e leituras somente governados (D32); distinção entre falha (INTERROMPIDO), não execução (NAO_EXECUTAVEL) e cancelamento (CANCELADO) (D35/D36); estado terminal não reaberto por retorno tardio (D39); ausência de precedência pela numeração das exclusões (D40); ausência de reativação automática de autorização (D41); estrutura antes de interpretação (D42). Exceção registrada: D31, conforme o parágrafo anterior.

Contagens: 290 requisitos RQ; 18 invariantes; 14 famílias; 11 exclusões; 26 capacidades; 24 itens CFG; 16 validadores; 13 templates; 64 enumerações canônicas, com StatusExecucaoElemento, TipoInteracaoUsuario e ConsequenciaExclusao; 66 termos de glossário; 15 desfechos; 19 limitações tipadas. Aceite: AT-01–AT-178 contíguos e únicos, com AT-165–AT-178 novos e AT-03, AT-16, AT-25, AT-86, AT-91, AT-124, AT-130, AT-134, AT-135, AT-147, AT-153 e AT-160 ajustados; nenhum AT removido; ROT-AT-01–ROT-AT-09 inalterados. CFG-DOC: 576 fontes e 703 proposições no Anexo A; catálogo com 703 id_doc e 810 formas por idioma.

Escopo: Docs/IMPLEMENTATION_SPEC.md alterado e Docs/CFG_DOC_CATALOG.yaml criado; CONCEPT inalterado. Ferramentas e registros de auditoria permanecem fora do repositório. Commits apenas locais, sem push, até revisão humana.

Situação de fechamento: **CANDIDATA v1.2.4** — construção compacta concluída e D29–D42 incorporadas; SPEC não declarada fechada. Blocker de fechamento: validação posterior da equivalência semântica integral EN do catálogo (D31). Esta publicação não afirma execução de testes de software nem aprovação comportamental. DECISOES_SUBSTANTIVAS_NOVAS: NENHUMA.

---

## Anexo A — Mapa normativo de extração de CFG-DOC

Este mapa integra CFG-DOC e fixa a materialização da versão 1.2.4. Não é fonte recursiva de novas proposições. Cada linha define um par fonte/caminho; `DOC:<fonte>[.<caminho>]` é sua identidade. Localizadores contam linhas físicas desde 1 e caracteres Unicode desde 0, em intervalos [início,fim), na SPEC integral entregue. Normalizar somente terminações de linha para LF e desconsiderar eventual BOM inicial na leitura. Concatenar os trechos na ordem listada, separados por LF. `=texto` referencia todos os trechos da coluna Texto; `—` significa campo ausente ou conjunto vazio. Tipo, condições e dependências estão fixados para cada par e resolvem pelas definições primárias de 4.4.23.1/3. Condições conservam suas alternativas e consequências; não se tornam conjunção de precondições. As formas PT/EN do catálogo externo Docs/CFG_DOC_CATALOG.yaml (seção 4.4.23.6) pertencem ao mesmo registro normativo PT, são localizadas pela chave id_doc e não geram fonte adicional. A seção 4.4.23.6, ATs, histórico e este Anexo estão excluídos da extração.

Cobertura recalculada: 576 fontes normativas e 703 proposições. IDs preservados quando fonte/caminho permaneceu igual. Em relação à v1.2.2, fontes novas limitadas aos seis enums auxiliares e a TPL-13, de D13–D28, e aos enums StatusExecucaoElemento, TipoInteracaoUsuario e ConsequenciaExclusao, de D35, D38 e D40. Sem raiz adicional para fonte decomposta em aspectos. Localizadores regenerados mecanicamente para esta versão e conferidos por extração (§25.9).

| Grupo | Fontes | Proposições |
|---|---:|---:|
| RQ | 290 | 290 |
| INV | 18 | 18 |
| FAM | 14 | 28 |
| EXC | 11 | 11 |
| V | 16 | 16 |
| TPL | 13 | 13 |
| ENUM | 64 | 64 |
| GLOSSARIO | 66 | 66 |
| CAP | 26 | 134 |
| CFG | 24 | 29 |
| DESFECHO | 15 | 15 |
| LIMITACAO | 19 | 19 |

| Fonte normativa | Caminho | Tipo | Texto: trechos exatos | Condições: referências aos trechos | Dependências |
|---|---|---|---|---|---|
| RQ-DOC-01 | — | GOVERNANCA | L56:18-170 | =texto | — |
| RQ-DOC-02 | — | GOVERNANCA | L57:18-216 | — | — |
| RQ-DOC-03 | — | GOVERNANCA | L58:18-1205 | =texto | CFG-DOC; S:25.5; S:25.8; S:25.9; TPL-12 |
| RQ-DOC-04 | — | GOVERNANCA | L59:18-149 | — | PARTE:19 |
| RQ-DOC-05 | — | GOVERNANCA | L60:18-123 | — | — |
| RQ-DOC-06 | — | GOVERNANCA | L61:18-561 | — | CFG-MET; S:4.4 |
| RQ-ESC-01 | — | GOVERNANCA | L186:18-270 | — | CONCEPT:1.1; CONCEPT:8.3 |
| RQ-ESC-02 | — | GOVERNANCA | L187:18-552 | =texto | CFG-NOR; CONCEPT:1.2; CONCEPT:3.7; CONCEPT:8.3; RQ-GOV-31 |
| RQ-ESC-03 | — | GOVERNANCA | L188:18-132 | =texto | CONCEPT:1.1; CONCEPT:11.10 |
| RQ-ESC-04 | — | GOVERNANCA | L192:18-828 | =texto | CONCEPT:3.1; CONCEPT:5.8; RQ-DAD-19; S:4.3 |
| RQ-ESC-05 | — | GOVERNANCA | L193:18-313 | =texto | CONCEPT:3.1; CONCEPT:3.7; CONCEPT:5.2; RQ-GOV-04 |
| RQ-ESC-06 | — | GOVERNANCA | L194:18-179 | — | — |
| RQ-ESC-07 | — | GOVERNANCA | L217:18-115 | =texto | CONCEPT:3.1 |
| RQ-ESC-08 | — | GOVERNANCA | L218:18-150 | =texto | CONCEPT:3.1; CONCEPT:5.2 |
| RQ-ESC-09 | — | GOVERNANCA | L219:18-163 | =texto | CONCEPT:11; CONCEPT:3.1; PARTE:19 |
| RQ-ESC-10 | — | GOVERNANCA | L237:18-195 | — | CONCEPT:3.8; CONCEPT:5.6 |
| RQ-ESC-13 | — | GOVERNANCA | L238:18-345 | =texto | CFG-EXC; RQ-GOV-09; S:4.4.3 |
| RQ-ESC-11 | — | GOVERNANCA | L249:18-217 | =texto | — |
| RQ-ESC-12 | — | GOVERNANCA | L250:18-541 | =texto | CAP-AGR-01; CONCEPT:3.2; CONCEPT:4.3.7; CONCEPT:4.3.9 |
| RQ-ARQ-01 | — | OPERACIONAL | L345:18-204 | — | C-03; C-04; C-05; C-07; C-08; C-09; C-10; C-12; C-13 |
| RQ-ARQ-02 | — | OPERACIONAL | L346:18-249 | =texto | C-06; CAP-EXA-01; MODELO:Autorizacao; RQ-DAD-34 |
| RQ-ARQ-03 | — | OPERACIONAL | L347:18-144 | — | C-01; C-03; C-04; C-12; INV-13 |
| RQ-ARQ-04 | — | OPERACIONAL | L348:18-497 | =texto | C-02; C-04; C-11; CFG-DOC; CFG-TPL; CONCEPT:9.11; TPL-04; TPL-12; TPL-13 |
| RQ-ARQ-05 | — | OPERACIONAL | L349:18-101 | =texto | C-11; CFG-REP; PARTE:13 |
| RQ-ARQ-06 | — | OPERACIONAL | L350:18-610 | — | C-03; C-08; C-10; C-12; INV-16; RQ-DAD-20; RQ-DAD-23 |
| RQ-ARQ-07 | — | OPERACIONAL | L351:18-146 | =texto | C-13; INV-12 |
| RQ-ARQ-08 | — | OPERACIONAL | L352:18-101 | =texto | C-09; INV-15 |
| RQ-ARQ-09 | — | OPERACIONAL | L353:18-401 | =texto | C-04; C-06; C-10; INV-02 |
| RQ-ARQ-10 | — | OPERACIONAL | L354:18-366 | =texto | C-02; C-03; C-04; C-05; C-06; C-07; C-08; C-11; C-12; C-13; PARTE:16; RQ-DEG-04 |
| RQ-ARQ-11 | — | OPERACIONAL | L355:18-254 | — | C-04; C-05 |
| RQ-MOD-01 | — | DADOS | L817:18-203 | — | S:7.1 |
| RQ-MOD-02 | — | DADOS | L818:18-407 | — | MODELO:VinculoResultadoLinha; MODELO:VinculoResultadoSolicitacao; RQ-FLX-02 |
| RQ-MOD-03 | — | DADOS | L819:18-162 | — | — |
| RQ-MOD-04 | — | DADOS | L820:18-79 | =texto | PARTE:19 |
| RQ-MOD-05 | — | DADOS | L821:18-88 | — | — |
| RQ-MOD-06 | — | DADOS | L822:18-295 | — | RQ-DIA-05; RQ-ORQ-13; S:9.3 |
| RQ-MOD-07 | — | DADOS | L823:18-220 | — | RQ-LIN-07 |
| RQ-CFG-01 | — | GOVERNANCA | L831:18-362 | — | CONCEPT:5.3; INV-15 |
| RQ-CFG-02 | — | GOVERNANCA | L832:18-235 | =texto | PARTE:19 |
| RQ-CFG-03 | — | GOVERNANCA | L833:18-138 | — | — |
| RQ-CFG-04 | — | GOVERNANCA | L834:18-178 | — | CONCEPT:3.6; CONCEPT:5.3 |
| RQ-CFG-05 | — | GOVERNANCA | L835:18-349 | =texto | — |
| RQ-CFG-06 | — | GOVERNANCA | L836:18-199 | =texto | — |
| RQ-CFG-07 | — | GOVERNANCA | L837:18-290 | — | C-09; S:4.2; S:4.3; S:4.4 |
| RQ-CFG-12 | — | GOVERNANCA | L838:18-511 | =texto | CFG-AUS; CFG-NOR; CFG-REF; CFG-TER; RQ-CFG-06 |
| RQ-CFG-08 | — | GOVERNANCA | L871:18-834 | =texto | CFG-DOM; CFG-VOC; RQ-CFG-01; RQ-CFG-05; RQ-DAD-19 |
| RQ-CFG-09 | — | GOVERNANCA | L872:18-1673 | =texto | CFG-DOM; CFG-VOC; RQ-CFG-10; RQ-DAD-19 |
| RQ-CFG-10 | — | GOVERNANCA | L873:18-704 | =texto | CFG-VOC |
| RQ-CFG-11 | — | GOVERNANCA | L874:18-586 | — | C-04; CFG-DOM; CFG-VOC |
| RQ-CFG-13 | — | GOVERNANCA | L875:18-226; L877:0-68; L879:0-42; L881:0-166; L882:0-102; L883:0-166; L884:0-117; L885:0-174; L886:0-165; L887:0-237; L888:0-95; L889:0-133; L890:0-159; L891:0-114; L892:0-212; L893:0-158; L894:0-172; L895:0-115; L897:0-115; L899:0-42; L901:0-120; L902:0-192; L903:0-143; L905:0-629; L907:0-282 | L875:18-226; L897:0-115; L905:0-629; L907:0-282 | CFG-PRV; CFG-TER; RQ-CFG-09; RQ-DAD-19; RQ-FLX-20 |
| RQ-CFG-14 | — | GOVERNANCA | L913:18-743 | — | RQ-CFG-15; RQ-FLX-20 |
| RQ-CFG-15 | — | GOVERNANCA | L914:18-1171 | =texto | C-04; CFG-CAP; CFG-DOM; CFG-IND; CFG-VOC; RQ-DAD-43; RQ-GOV-13; RQ-GOV-14; RQ-GOV-15; RQ-GOV-16; RQ-GOV-17; RQ-GOV-18 |
| RQ-DAD-01 | — | DADOS | L1316:18-656 | =texto | C-10; ENUM-OrigemBase; ENUM-StatusBase; RQ-DAD-19; RQ-GOV-20 |
| RQ-DAD-02 | — | DADOS | L1317:18-572 | =texto | CONCEPT:3.3; CONCEPT:7.2; RQ-DAD-34; RQ-DAD-42; V-08 |
| RQ-DAD-03 | — | DADOS | L1318:18-158 | — | CONCEPT:7.9; MODELO:AlteracaoEstado; PARTE:11 |
| RQ-DAD-04 | — | DADOS | L1319:18-523 | =texto | CONCEPT:4.3.3; CONCEPT:5.3; RQ-DAD-43 |
| RQ-DAD-16 | — | DADOS | L1320:18-243 | — | CONCEPT:5.8; RQ-GOV-22 |
| RQ-DAD-17 | — | DADOS | L1321:18-352 | — | RQ-FLX-17 |
| RQ-DAD-05 | — | DADOS | L1336:18-612 | =texto | CFG-TER; CONCEPT:4.3.3; CONCEPT:9.2; ENUM-StatusSignificado; MODELO:Etapa; RQ-DAD-36 |
| RQ-DAD-06 | — | DADOS | L1337:18-1078 | =texto | CFG-OPC; CFG-TER; CONCEPT:7.3; S:4.3 |
| RQ-DAD-07 | — | DADOS | L1338:18-665 | =texto | AMB-03; CFG-AUS; CONCEPT:7.3; CONCEPT:7.4; RQ-GOV-22 |
| RQ-DAD-08 | — | DADOS | L1339:18-300 | — | CONCEPT:4.3.3; CONCEPT:7.3; MODELO:AlteracaoEstado |
| RQ-DAD-18 | — | DADOS | L1340:18-483 | =texto | CAP-IND-01; RQ-DAD-35; V-03 |
| RQ-DAD-36 | — | DADOS | L1341:18-1114 | =texto | CAP-AGR-01; CFG-TER; RQ-DAD-05; RQ-GOV-24 |
| RQ-DAD-19 | — | DADOS | L1342:18-1627 | =texto | CONCEPT:3.1; RQ-CFG-09; RQ-DAD-01; RQ-GOV-04; RQ-LIN-07; S:4.3 |
| RQ-DAD-09 | — | DADOS | L1346:18-464 | =texto | CONCEPT:4.3.4; CONCEPT:7.4; ENUM-DetalheBloqueio; RQ-FLX-16 |
| RQ-DAD-10 | — | DADOS | L1347:18-287 | — | ENUM-DetalheBloqueio; PARTE:15 |
| RQ-DAD-11 | — | DADOS | L1348:18-263 | — | — |
| RQ-DAD-12 | — | DADOS | L1349:18-246 | =texto | CONCEPT:4.3.4; CONCEPT:5.8 |
| RQ-DAD-13 | — | DADOS | L1353:18-277; L1355:0-24; L1357:0-62; L1358:0-84; L1359:0-120; L1360:0-50; L1361:0-65; L1362:0-113; L1363:0-200; L1364:0-236; L1365:0-106 | — | CAP-EXA-01; CFG-TER; CONCEPT:3.3; CONCEPT:5.4; RQ-DAD-34; S:4.3; V-08 |
| RQ-DAD-14 | — | DADOS | L1367:18-243 | =texto | FAM-01; S:7.7 |
| RQ-DAD-15 | — | DADOS | L1368:18-136 | — | V-10 |
| RQ-DAD-20 | — | DADOS | L1372:18-2513 | =texto | C-04; C-10; CFG-VOC; ENUM-ProtecaoCampo; MODELO:AliasMetadado; RQ-DAD-33; RQ-DAD-38; RQ-DAD-39 |
| RQ-DAD-21 | — | DADOS | L1373:18-410 | — | — |
| RQ-DAD-22 | — | DADOS | L1374:18-691; L1376:0-399 | =texto | C-02; RQ-DAD-38; RQ-DAD-42; S:4.4.16; TPL-10 |
| RQ-DAD-23 | — | DADOS | L1378:18-856 | =texto | C-10; CFG-VOC; RQ-DAD-20; RQ-DAD-33; RQ-DAD-39 |
| RQ-DAD-24 | — | DADOS | L1379:18-302 | =texto | EV-TRIAGEM |
| RQ-DAD-37 | — | DADOS | L1380:18-2641 | =texto | CFG-PRV; RQ-DAD-21 |
| RQ-DAD-38 | — | DADOS | L1381:18-3703 | =texto | C-02; CFG-PRV; CFG-TER; CFG-VOC; RQ-DAD-20; RQ-DAD-33; RQ-DAD-39; RQ-DAD-42; TPL-10 |
| RQ-DAD-39 | — | DADOS | L1382:18-1834 | =texto | C-10; FN-INT-01; RQ-DAD-23; RQ-DAD-38 |
| RQ-DAD-25 | — | DADOS | L1386:18-555 | =texto | ENUM-Validade; RQ-DAD-26 |
| RQ-DAD-26 | — | DADOS | L1387:18-1003 | =texto | C-04; CFG-MET; S:4.4.5 |
| RQ-DAD-27 | — | DADOS | L1388:18-378 | =texto | CFG-MET; RQ-DAD-26 |
| RQ-DAD-28 | — | DADOS | L1392:18-625 | =texto | CFG-FON; RQ-DAD-43; V-02 |
| RQ-DAD-29 | — | DADOS | L1393:18-779 | =texto | CFG-VOC; RQ-DAD-05 |
| RQ-DAD-30 | — | DADOS | L1394:18-1406 | =texto | C-04; CAP-AGR-01; CFG-TER; RQ-DAD-43; RQ-GOV-21 |
| RQ-DAD-43 | — | DADOS | L1395:18-3457 | =texto | CFG-FON; ENUM-PapelPlanilha; EV-ESTADO-BASE; EV-FALHA; RQ-DAD-30; RQ-DAD-42; TPL-13 |
| RQ-DAD-31 | — | DADOS | L1399:18-1675 | =texto | C-04; C-10; CFG-VOC; FN-INT-01; RQ-DAD-38; RQ-DAD-41; RQ-FLX-01; RQ-FLX-21; RQ-GOV-22 |
| RQ-DAD-32 | — | DADOS | L1400:18-1040 | =texto | EXC-06; MODELO:ParametroDecisao; RQ-DAD-40; RQ-GOV-22; RQ-LIN-21 |
| RQ-DAD-33 | — | DADOS | L1401:18-1589 | =texto | C-02; C-04; C-10; FN-INT-01; RQ-DAD-20; RQ-DAD-31; RQ-DAD-38; RQ-RAS-07; S:5.5 |
| RQ-DAD-40 | — | DADOS | L1402:18-1244 | =texto | C-04; ENUM-StatusSignificado; MODELO:ParametroDecisao; RQ-DAD-08; RQ-DAD-32; RQ-LIN-21 |
| RQ-DAD-41 | — | DADOS | L1403:18-1648 | =texto | C-10; CFG-PRV; CFG-VOC; RQ-DAD-31; RQ-DAD-38; S:4.4.9 |
| RQ-DAD-34 | — | DADOS | L1407:18-2211 | =texto | C-04; C-06; C-10; CAP-EXA-01; CFG-FON; RQ-DAD-31; RQ-DAD-42; S:7.7 |
| RQ-DAD-35 | — | DADOS | L1408:18-1681 | =texto | C-10; CAP-AGR-01; CAP-IND-01; CAP-ROT-01; PARTE:18 |
| RQ-DAD-42 | — | DADOS | L1409:18-3335 | =texto | C-10; CAP-EXA-01; ENUM-MotivoBloqueioBase; ENUM-StatusBase; EV-ESTADO-BASE; RQ-DAD-05; RQ-DAD-17; RQ-DAD-22; RQ-DAD-38; RQ-DAD-43; S:6.3.1; TPL-10 |
| RQ-FLX-17 | — | OPERACIONAL | L1417:18-1751 | — | C-08; C-13; CFG-OPR; EV-INTERACAO_USUARIO |
| RQ-FLX-18 | — | OPERACIONAL | L1418:18-536 | =texto | — |
| RQ-FLX-19 | — | OPERACIONAL | L1419:18-122; L1421:0-308; L1423:0-65 | — | S:4.4.16; TPL-09 |
| RQ-FLX-20 | — | OPERACIONAL | L1425:18-185 | — | — |
| RQ-FLX-01 | — | OPERACIONAL | L1447:18-1879; L1449:0-61; L1451:0-113; L1452:0-199; L1453:0-174; L1454:0-187; L1455:0-244; L1456:0-207; L1457:0-205; L1458:0-221; L1459:0-172; L1460:0-79; L1461:0-254; L1462:0-214; L1463:0-317; L1464:0-144; L1466:0-999; L1470:0-284; L1472:0-75; L1474:0-100; L1475:0-110; L1476:0-144; L1477:0-145; L1478:0-143; L1479:0-153; L1480:0-307; L1481:0-189; L1482:0-162; L1483:0-171; L1484:0-161; L1485:0-153; L1486:0-184; L1487:0-179; L1488:0-164; L1489:0-171; L1490:0-204; L1491:0-203; L1492:0-193; L1493:0-322; L1494:0-259; L1495:0-260; L1496:0-188; L1497:0-153; L1498:0-108; L1499:0-205; L1500:0-177; L1501:0-152; L1502:0-178; L1503:0-262; L1504:0-233; L1505:0-159; L1506:0-126; L1507:0-113; L1508:0-452; L1509:0-152; L1510:0-192; L1511:0-316; L1512:0-238; L1513:0-124; L1514:0-109; L1515:0-164; L1516:0-273; L1517:0-140; L1518:0-182; L1519:0-216; L1520:0-124; L1521:0-130 | =texto | C-02; C-08; C-10; CAP-ROT-01; CFG-OPR; ENUM-StatusEtapa; ENUM-StatusSolicitacao; EV-ALTERACAO-ESTADO; EV-AUTORIZACAO; EV-CANCELAMENTO; EV-CONFIRMACAO-USO; EV-DISPONIBILIDADE; EV-ESTADO-BASE; EV-EXAME; EV-EXECUCAO; EV-FALHA; EV-INDISPONIBILIDADE; EV-INGESTAO; EV-INTERACAO_USUARIO; EV-LEITURA-MINIMA; EV-MENSAGEM; EV-PENDENCIA; EV-PRIVACIDADE; EV-REPLANEJAMENTO; EV-RESPOSTA; EV-RESULTADO; EV-RETORNO_TARDIO_DESCARTADO; EV-REUSO; EV-SESSAO; EV-SUSPENSAO; EV-TRIAGEM; EV-VERIFICACAO; MODELO:Etapa; MODELO:ResultadoElemento; RQ-DAD-42; RQ-DEG-02; RQ-DEG-04; RQ-DEG-08; RQ-FLX-02; RQ-FLX-17; RQ-ORQ-14; RQ-ORQ-16; RQ-RES-04; S:9.5 |
| RQ-FLX-02 | — | OPERACIONAL | L1523:18-1855 | =texto | EV-ALTERACAO-ESTADO; EV-CANCELAMENTO; MODELO:EscopoSolicitacao; RQ-ORQ-16 |
| RQ-FLX-03 | — | OPERACIONAL | L1524:18-270 | =texto | CAP-EXA-01; CONCEPT:5.2; CONCEPT:6.4; INV-01; RQ-DAD-34; V-08 |
| RQ-FLX-04 | — | OPERACIONAL | L1525:18-981 | =texto | CONCEPT:5.9; CONCEPT:6.4; PARTE:11; RQ-DAD-08; RQ-FLX-15; RQ-LIN-19; RQ-ORQ-06; RQ-ORQ-07; RQ-ORQ-10; RQ-ORQ-11 |
| RQ-FLX-05 | — | OPERACIONAL | L1529:18-790 | =texto | C-03; C-08; CONCEPT:7.5; RQ-DAD-23; RQ-DAD-42; RQ-FLX-17 |
| RQ-FLX-06 | — | OPERACIONAL | L1530:18-685 | =texto | CONCEPT:5.7; CONCEPT:7.5; RQ-ORQ-13 |
| RQ-FLX-07 | — | OPERACIONAL | L1534:18-287 | =texto | C-13; CFG-DOC; CONCEPT:5.2; FN-META-01; V-16 |
| RQ-FLX-08 | — | OPERACIONAL | L1535:18-554 | =texto | CFG-DOC; CFG-IND; CFG-MET; CFG-NOR; CONCEPT:5.2; RQ-GOV-31; S:4.4.23 |
| RQ-FLX-09 | — | OPERACIONAL | L1536:18-644 | — | C-01; C-02; C-05; C-08; RQ-FLX-02; RQ-FLX-17; RQ-LIN-15 |
| RQ-FLX-10 | — | OPERACIONAL | L1537:18-427 | =texto | FN-INT-02; RQ-DAD-42 |
| RQ-FLX-11 | — | OPERACIONAL | L1538:18-397 | =texto | CONCEPT:5.2; RQ-FLX-21; S:7.8 |
| RQ-FLX-12 | — | OPERACIONAL | L1542:18-236 | =texto | CONCEPT:7.8; CONCEPT:9.10; PARTE:11 |
| RQ-FLX-13 | — | OPERACIONAL | L1543:18-485 | =texto | — |
| RQ-FLX-14 | — | OPERACIONAL | L1547:18-230 | — | — |
| RQ-FLX-15 | — | OPERACIONAL | L1548:18-488 | =texto | CONCEPT:9.11 |
| RQ-FLX-16 | — | OPERACIONAL | L1549:18-734 | =texto | C-01; EV-CAPTURA-SELECAO |
| RQ-FLX-21 | — | OPERACIONAL | L1551:18-1111 | =texto | ENUM-StatusBase; RQ-DAD-31; RQ-DAD-43; RQ-FLX-01; RQ-FLX-07; S:5.8 |
| RQ-FLX-22 | — | OPERACIONAL | L1552:18-1434 | =texto | RQ-DAD-43; RQ-FLX-01; RQ-FLX-02; RQ-FLX-04; RQ-GOV-27; RQ-GOV-29; TPL-04; TPL-10 |
| RQ-GOV-01 | — | GOVERNANCA | L1569:18-311 | — | C-04 |
| RQ-GOV-02 | — | GOVERNANCA | L1570:18-121 | — | CONCEPT:5.10 |
| RQ-GOV-03 | — | GOVERNANCA | L1571:18-665 | =texto | C-04; CONCEPT:8.6 |
| RQ-GOV-04 | — | GOVERNANCA | L1575:18-485; L1577:0-26; L1579:0-153; L1580:0-87; L1581:0-66; L1582:0-114; L1583:0-298; L1584:0-203; L1585:0-265; L1586:0-288; L1587:0-76; L1588:0-168; L1589:0-84 | L1579:0-153; L1588:0-168 | C-04; CFG-DOM; CONCEPT:3.1; CONCEPT:5.2; FN-META-01; RQ-DAD-19; S:4.3 |
| RQ-GOV-05 | — | GOVERNANCA | L1591:18-106 | — | — |
| RQ-GOV-06 | — | GOVERNANCA | L1592:18-237 | — | CFG-FAM; CONCEPT:5.2 |
| RQ-GOV-07 | — | GOVERNANCA | L1593:18-106 | — | RQ-ESC-06 |
| RQ-GOV-08 | — | GOVERNANCA | L1597:18-683 | =texto | CONCEPT:3.1; CONCEPT:5.2; RQ-GOV-09; S:1.4 |
| RQ-GOV-09 | — | GOVERNANCA | L1598:18-1330 | =texto | C-04; CFG-EXC; ENUM-ConsequenciaExclusao; ENUM-DisposicaoSinalExclusao; EXC-03; EXC-08; FN-INT-01; S:4.4.3 |
| RQ-GOV-10 | — | GOVERNANCA | L1599:18-153 | =texto | — |
| RQ-GOV-11 | — | GOVERNANCA | L1600:18-260 | =texto | CONCEPT:9.7 |
| RQ-GOV-12 | — | GOVERNANCA | L1604:18-769 | — | CAP-DIS-01; CFG-CAP; CONCEPT:11.9; CONCEPT:5.6 |
| RQ-GOV-13 | — | GOVERNANCA | L1608:18-181; L1610:0-28; L1612:0-152; L1613:0-190; L1614:0-114; L1615:0-267; L1616:0-188; L1617:0-98; L1618:0-114 | L1608:18-181; L1613:0-190; L1616:0-188; L1618:0-114 | CFG-REP; CONCEPT:5.5; ENUM-ClasseAutoridade; RQ-GOV-14 |
| RQ-GOV-14 | — | GOVERNANCA | L1620:18-1336 | =texto | AMB-04; C-04; CONCEPT:3.6; MODELO:InterpretacaoOperacional; RQ-LIN-19; RQ-LIN-21; V-04 |
| RQ-GOV-15 | — | GOVERNANCA | L1621:18-338 | =texto | CONCEPT:3.6; RQ-GOV-14 |
| RQ-GOV-16 | — | GOVERNANCA | L1622:18-1259 | =texto | CFG-VOC; RQ-FLX-16; RQ-GOV-28 |
| RQ-GOV-17 | — | GOVERNANCA | L1623:18-472 | =texto | C-04; CONCEPT:5.7; CONCEPT:9.4; CONCEPT:9.5; MODELO:InterpretacaoAlternativa; MODELO:OpcaoAutorizada; S:4.4.11 |
| RQ-GOV-18 | — | GOVERNANCA | L1624:18-387; L1626:0-39; L1628:0-275; L1629:0-250; L1630:0-246; L1631:0-485; L1632:0-343; L1633:0-266 | L1624:18-387; L1629:0-250; L1630:0-246; L1631:0-485; L1632:0-343 | AMB-01; AMB-02; AMB-03; AMB-04; AMB-05; AMB-06; CAP-TEN-01; CAP-TMP-01; CFG-AMB; CFG-AUS; CFG-OPC; CFG-VOC; CONCEPT:4.3.10; CONCEPT:4.3.11; CONCEPT:4.3.15; CONCEPT:4.3.9; CONCEPT:5.8; CONCEPT:7.3; MODELO:OpcaoAutorizada |
| RQ-GOV-19 | — | GOVERNANCA | L1635:18-1292 | =texto | C-04; CFG-DOC; CFG-OPC; CFG-PRV; FN-INT-03; MODELO:OpcaoAutorizada; S:4.4.11; TPL-04; V-16 |
| RQ-GOV-20 | — | GOVERNANCA | L1636:18-794 | =texto | C-04; CONCEPT:5.5; CONCEPT:9.4; RQ-GOV-14 |
| RQ-GOV-21 | — | GOVERNANCA | L1640:18-701 | =texto | CFG-PRE; CONCEPT:5.3; CONCEPT:7.10; CONCEPT:8.6 |
| RQ-GOV-22 | — | GOVERNANCA | L1641:18-1156 | =texto | RQ-DAD-31; RQ-DAD-32; RQ-GOV-03; RQ-LIN-07; RQ-LIN-21 |
| RQ-GOV-23 | — | GOVERNANCA | L1642:18-387 | =texto | AMB-04; CFG-OPR; CONCEPT:5.8 |
| RQ-GOV-31 | — | GOVERNANCA | L1643:18-499 | =texto | C-04 |
| RQ-GOV-32 | — | GOVERNANCA | L1644:18-457 | =texto | RQ-DAD-19 |
| RQ-GOV-24 | — | GOVERNANCA | L1648:18-733; L1650:0-28; L1652:0-76; L1653:0-49; L1654:0-135; L1655:0-183; L1656:0-87; L1657:0-111; L1658:0-67; L1659:0-300; L1660:0-554; L1661:0-73; L1662:0-226; L1663:0-212 | =texto | C-04; CAP-AGR-01; CAP-CMP-01; CAP-ESP-02; CAP-EXA-01; CAP-SUB-01; CONCEPT:5.9; MODELO:CausaOrigem; MODELO:RefSaidaEsperada; RQ-CAP-08; RQ-DAD-34; RQ-DAD-36; RQ-FLX-22; RQ-GOV-29; RQ-LIN-20; RQ-ORQ-07; RQ-ORQ-13; S:9.5 |
| RQ-GOV-25 | — | GOVERNANCA | L1665:18-158 | =texto | C-04; C-06; CONCEPT:5.9 |
| RQ-GOV-26 | — | GOVERNANCA | L1666:18-223 | =texto | CONCEPT:5.9; CONCEPT:6.5; MODELO:ContextoConsistencia; RQ-ORQ-13 |
| RQ-GOV-27 | — | GOVERNANCA | L1667:18-629 | =texto | MODELO:Autorizacao; S:9.1 |
| RQ-GOV-28 | — | GOVERNANCA | L1668:18-1797 | =texto | C-04; CONCEPT:5.9; CONCEPT:8.4; MODELO:InterpretacaoOperacional; PARTE:12; RQ-QUA-06 |
| RQ-GOV-29 | — | GOVERNANCA | L1672:18-1177 | =texto | CAP-CMP-01; CONCEPT:5.2; CONCEPT:5.9; CONCEPT:9.6 |
| RQ-GOV-30 | — | GOVERNANCA | L1673:18-1244 | =texto | CONCEPT:9.6; RQ-DEG-04; RQ-GOV-28 |
| RQ-CAP-01 | — | CAPACIDADE | L1685:18-81 | — | — |
| RQ-CAP-02 | — | CAPACIDADE | L1686:18-110 | — | CONCEPT:8.10 |
| RQ-CAP-03 | — | CAPACIDADE | L1687:18-243 | =texto | RQ-REP-05 |
| RQ-CAP-04 | — | CAPACIDADE | L1688:18-205 | — | CONCEPT:7.4; CONCEPT:8.11; INV-04 |
| RQ-CAP-05 | — | CAPACIDADE | L1689:18-151 | — | — |
| RQ-CAP-06 | — | CAPACIDADE | L1690:18-131 | — | CONCEPT:3.5; CONCEPT:4.3.13 |
| RQ-CAP-07 | — | CAPACIDADE | L1691:18-179 | =texto | CFG-MET; RQ-GOV-31 |
| RQ-CAP-08 | — | CAPACIDADE | L1692:18-1882 | =texto | CAP-ROT-01; CAP-SUB-01; CONCEPT:8.11; CONCEPT:9.2; MODELO:RefSaidaEsperada; MODELO:ResultadoElemento; RQ-ORQ-14; RQ-RES-04; S:7.7 |
| RQ-CAP-09 | — | CAPACIDADE | L1693:18-107 | =texto | CONCEPT:3.7 |
| RQ-CAP-10 | — | CAPACIDADE | L1694:18-120 | — | CONCEPT:11.9 |
| RQ-CAP-11 | — | CAPACIDADE | L1695:18-90 | — | PARTE:18 |
| RQ-CAP-12 | — | CAPACIDADE | L1696:18-246 | — | RQ-GOV-22 |
| RQ-CAP-13 | — | CAPACIDADE | L1697:18-170 | =texto | CFG-MET |
| RQ-ORQ-01 | — | OPERACIONAL | L1868:18-1567 | =texto | C-02; C-05; CONCEPT:4.4; CONCEPT:5.4; ENUM-StatusEntregavel; ENUM-StatusSolicitacao; FN-ORQ-01; MODELO:EscopoSolicitacao; RQ-FLX-02; RQ-GOV-27; RQ-GOV-28; RQ-GOV-29; RQ-ORQ-14 |
| RQ-ORQ-02 | — | OPERACIONAL | L1869:18-271 | — | C-05; FN-ORQ-01; RQ-DAD-34 |
| RQ-ORQ-03 | — | OPERACIONAL | L1870:18-88 | — | — |
| RQ-ORQ-04 | — | OPERACIONAL | L1874:18-572 | =texto | C-06; C-07; RQ-FLX-04 |
| RQ-ORQ-05 | — | OPERACIONAL | L1875:18-473 | =texto | C-05; CONCEPT:10.3; CONCEPT:5.10; ENUM-StatusSolicitacao |
| RQ-ORQ-06 | — | OPERACIONAL | L1879:18-1057 | =texto | CONCEPT:5.4; CONCEPT:7.9; EV-REUSO; RQ-DAD-42; RQ-FLX-17; RQ-LIN-20; RQ-ORQ-07; RQ-ORQ-13 |
| RQ-ORQ-07 | — | OPERACIONAL | L1880:18-826 | =texto | INV-08; RQ-DAD-42; RQ-FLX-06; RQ-FLX-17; RQ-LIN-20 |
| RQ-ORQ-08 | — | OPERACIONAL | L1884:18-776 | =texto | CONCEPT:5.9; CONCEPT:6.5; EV-REPLANEJAMENTO; RQ-FLX-02; S:9.1 |
| RQ-ORQ-09 | — | OPERACIONAL | L1885:18-332 | =texto | CAP-ESP-02 |
| RQ-ORQ-10 | — | OPERACIONAL | L1889:18-555 | =texto | C-05; CONCEPT:6.5; CONCEPT:7.10; MODELO:AlteracaoEstado; MODELO:ContextoConsistencia; RQ-CFG-05 |
| RQ-ORQ-11 | — | OPERACIONAL | L1890:18-495 | =texto | — |
| RQ-ORQ-12 | — | OPERACIONAL | L1891:18-308 | =texto | INV-10; RQ-ORQ-13 |
| RQ-ORQ-13 | — | OPERACIONAL | L1895:18-1782 | =texto | C-04; CAP-AGR-01; CAP-CMP-01; CAP-TEN-01; CAP-TMP-01; CONCEPT:4.3.7; CONCEPT:6.5; MODELO:ContextoConsistencia; RQ-CAP-08; RQ-DIA-05; RQ-ORQ-07; V-05 |
| RQ-ORQ-14 | — | OPERACIONAL | L1899:18-1596 | =texto | CAP-ROT-01; CAP-SUB-01; CFG-OPR; ENUM-StatusEtapa; MODELO:CausaOrigem; MODELO:Etapa; MODELO:ResultadoElemento; TPL-03 |
| RQ-ORQ-15 | — | OPERACIONAL | L1900:18-82 | — | PARTE:16 |
| RQ-ORQ-16 | — | OPERACIONAL | L1901:18-932 | — | EV-RETORNO_TARDIO_DESCARTADO; RQ-FLX-02; RQ-FLX-17 |
| RQ-RES-01 | — | REPRESENTACAO | L1907:18-509 | =texto | CAP-SUB-01; CONCEPT:8.2; RQ-CAP-08 |
| RQ-RES-02 | — | REPRESENTACAO | L1908:18-133 | — | INV-07; RQ-MOD-02 |
| RQ-RES-03 | — | REPRESENTACAO | L1909:18-265 | =texto | C-05; CONCEPT:8.2; RQ-ORQ-08 |
| RQ-RES-04 | — | REPRESENTACAO | L1910:18-2022 | =texto | ENUM-StatusEntregavel; MODELO:ResultadoElemento; RQ-CAP-08; RQ-DEG-04; RQ-FLX-02; RQ-ORQ-14; RQ-ORQ-16 |
| RQ-RES-05 | — | REPRESENTACAO | L1911:18-101; L1913:0-28; L1915:0-65; L1916:0-77; L1917:0-106; L1918:0-81; L1919:0-69; L1920:0-41; L1921:0-111; L1922:0-79 | L1918:0-81; L1921:0-111 | CONCEPT:7.4; CONCEPT:8.11; ENUM-Desfecho |
| RQ-RES-06 | — | REPRESENTACAO | L1924:18-1381 | =texto | CONCEPT:9.8; ENUM-CategoriaLimitacao; RQ-DAD-43; RQ-RES-04; TPL-13 |
| RQ-RES-07 | — | REPRESENTACAO | L1925:18-233 | =texto | C-13; CONCEPT:5.10; INV-12 |
| RQ-RES-08 | — | REPRESENTACAO | L1926:18-137 | — | CONCEPT:8.8 |
| RQ-RES-09 | — | REPRESENTACAO | L1927:18-157 | — | CONCEPT:8.10 |
| RQ-RES-10 | — | REPRESENTACAO | L1929:18-1753 | =texto | CAP-CMP-01; CAP-ROT-01; CAP-SUB-01; ENUM-MotivoNaoAvaliavel; ENUM-TipoContagemAgregada; MODELO:CausaOrigem; MODELO:RefSaidaEsperada; RQ-RES-06 |
| RQ-RES-11 | — | REPRESENTACAO | L1930:18-1137 | =texto | CAP-AGR-01; CAP-CMP-01; CAP-ROT-01; CAP-SUB-01; RQ-RES-06; V-15 |
| RQ-LIN-01 | — | GOVERNANCA | L1938:18-203 | =texto | CONCEPT:7.6 |
| RQ-LIN-02 | — | GOVERNANCA | L1939:18-615 | =texto | CONCEPT:7.6; FN-INT-02 |
| RQ-LIN-03 | — | GOVERNANCA | L1940:18-181 | — | CONCEPT:7.6; CONCEPT:9.9 |
| RQ-LIN-04 | — | GOVERNANCA | L1941:18-227 | =texto | CONCEPT:9.9; RQ-LIN-21 |
| RQ-LIN-05 | — | GOVERNANCA | L1942:18-96 | — | CONCEPT:9.10 |
| RQ-LIN-06 | — | GOVERNANCA | L1943:18-219 | =texto | CONCEPT:7.6; CONCEPT:8.3; RQ-DIA-05 |
| RQ-LIN-07 | — | GOVERNANCA | L1947:18-1063 | =texto | CONCEPT:7.6; RQ-LIN-19; RQ-LIN-21 |
| RQ-LIN-08 | — | GOVERNANCA | L1948:18-511 | =texto | RQ-LIN-19 |
| RQ-LIN-09 | — | GOVERNANCA | L1952:18-166 | — | CONCEPT:7.8 |
| RQ-LIN-10 | — | GOVERNANCA | L1953:18-373 | — | CONCEPT:7.10; RQ-LIN-19; RQ-LIN-20 |
| RQ-LIN-11 | — | GOVERNANCA | L1957:18-185 | — | CONCEPT:7.9 |
| RQ-LIN-12 | — | GOVERNANCA | L1958:18-462 | =texto | — |
| RQ-LIN-13 | — | GOVERNANCA | L1959:18-82; L1961:0-37; L1963:0-162; L1964:0-93; L1965:0-23 | L1963:0-162; L1964:0-93 | CONCEPT:7.7; CONCEPT:7.9; CONCEPT:8.9; RQ-LIN-20 |
| RQ-LIN-14 | — | GOVERNANCA | L1967:18-399 | =texto | CONCEPT:7.9 |
| RQ-LIN-15 | — | GOVERNANCA | L1968:18-458 | =texto | CONCEPT:7.9; CONCEPT:8.9 |
| RQ-LIN-16 | — | GOVERNANCA | L1969:18-255 | =texto | CONCEPT:7.7 |
| RQ-LIN-17 | — | GOVERNANCA | L1970:18-170 | — | CONCEPT:7.8; CONCEPT:9.10 |
| RQ-LIN-18 | — | GOVERNANCA | L1971:18-136 | — | EV-INVALIDACAO; EV-VIGENCIA |
| RQ-LIN-19 | — | GOVERNANCA | L1972:18-1605 | =texto | MODELO:Pendencia |
| RQ-LIN-20 | — | GOVERNANCA | L1973:18-1180 | =texto | C-08; EV-REUSO; RQ-LIN-15 |
| RQ-LIN-21 | — | GOVERNANCA | L1974:18-1526 | =texto | RQ-DAD-17; RQ-DAD-40; RQ-GOV-21; RQ-GOV-22 |
| RQ-DIA-01 | — | REPRESENTACAO | L1980:18-855 | =texto | CONCEPT:8.3; CONCEPT:8.4; MODELO:EscopoSolicitacao; MODELO:VinculoResultadoSolicitacao; RQ-LIN-20 |
| RQ-DIA-02 | — | REPRESENTACAO | L1981:18-639 | =texto | CONCEPT:8.4; MODELO:EscopoSolicitacao; MODELO:VinculoResultadoSolicitacao |
| RQ-DIA-03 | — | REPRESENTACAO | L1982:18-425 | =texto | CONCEPT:8.4; EV-AMPLIACAO |
| RQ-DIA-04 | — | REPRESENTACAO | L1983:18-259 | — | CAP-REP-05; CAP-REP-06; CONCEPT:8.12 |
| RQ-DIA-05 | — | REPRESENTACAO | L1984:18-525 | =texto | CONCEPT:8.3; CONCEPT:8.4; RQ-ORQ-13 |
| RQ-DIA-06 | — | REPRESENTACAO | L1985:18-707 | =texto | CFG-NOR; CONCEPT:8.3; RQ-GOV-31; V-03; V-09 |
| RQ-REP-01 | — | REPRESENTACAO | L2001:18-658 | =texto | C-11; CAP-IND-02; CFG-DOC; CONCEPT:4.3.14; CONCEPT:5.10; EV-REPRESENTACAO |
| RQ-REP-02 | — | REPRESENTACAO | L2002:18-256 | =texto | CAP-DIS-02; CAP-DIS-03; CAP-SUB-01; CAP-TEN-01; CONCEPT:4.3.14 |
| RQ-REP-03 | — | REPRESENTACAO | L2003:18-216 | =texto | CAP-SUB-02; INV-18 |
| RQ-REP-04 | — | REPRESENTACAO | L2004:18-517 | =texto | CAP-CMP-01; CAP-SUB-01; CONCEPT:5.11 |
| RQ-REP-05 | — | REPRESENTACAO | L2005:18-895 | =texto | — |
| RQ-REP-06 | — | REPRESENTACAO | L2006:18-422 | =texto | CONCEPT:11.11; CONCEPT:4.3.14; RQ-FLX-16 |
| RQ-REP-07 | — | REPRESENTACAO | L2007:18-210 | =texto | S:5.6 |
| RQ-REP-08 | — | REPRESENTACAO | L2008:18-120 | — | — |
| RQ-REP-09 | — | REPRESENTACAO | L2009:18-400 | =texto | RQ-DEG-04 |
| RQ-REP-10 | — | REPRESENTACAO | L2010:18-373 | — | — |
| RQ-REP-11 | — | REPRESENTACAO | L2011:18-313 | — | CAP-IND-02; CAP-ROT-01 |
| RQ-REP-12 | — | REPRESENTACAO | L2012:18-958 | =texto | C-10; CAP-REP-05; CAP-REP-06; CONCEPT:8.12; RQ-DAD-20 |
| RQ-REP-13 | — | REPRESENTACAO | L2013:18-368 | =texto | — |
| RQ-REP-14 | — | REPRESENTACAO | L2014:18-449 | — | ENUM-TipoContagemAgregada |
| RQ-REP-15 | — | REPRESENTACAO | L2016:18-779 | =texto | C-11; CAP-ESP-02; RQ-LIN-20; RQ-RES-11 |
| RQ-SIN-01 | — | REPRESENTACAO | L2024:18-787 | =texto | C-12; CFG-DOC; CFG-LEX; CFG-REP; MODELO:EscopoSolicitacao; RQ-FLX-02; S:4.4.23; TPL-12 |
| RQ-SIN-02 | — | REPRESENTACAO | L2025:18-776 | =texto | C-04; CFG-DOC; ENUM-FuncaoConteudo; RQ-SIN-10; V-16 |
| RQ-SIN-03 | — | REPRESENTACAO | L2026:18-296 | — | CONCEPT:4.3.15 |
| RQ-SIN-04 | — | REPRESENTACAO | L2049:18-185 | — | INV-13 |
| RQ-SIN-05 | — | REPRESENTACAO | L2050:18-901 | =texto | C-02; C-11; EV-VALIDACAO-SAIDA; PARTE:16; RQ-DEG-04; TPL-08; TPL-12 |
| RQ-SIN-06 | — | REPRESENTACAO | L2051:18-459 | =texto | CFG-LEX; RQ-SIN-10; S:4.4.15; V-16 |
| RQ-SIN-07 | — | REPRESENTACAO | L2052:18-339 | =texto | CFG-DOC; CONCEPT:8.10 |
| RQ-SIN-08 | — | REPRESENTACAO | L2053:18-277 | — | CONCEPT:12.8 |
| RQ-SIN-09 | — | REPRESENTACAO | L2054:18-359 | =texto | RQ-FLX-18 |
| RQ-SIN-10 | — | REPRESENTACAO | L2056:18-2058 | =texto | C-04; CFG-DOC; RQ-SIN-05; TPL-12; V-01; V-02; V-03; V-04; V-06; V-07; V-10; V-12; V-13; V-16 |
| RQ-INC-01 | — | DESFECHO | L2084:18-140 | — | CONCEPT:5.11; INV-05 |
| RQ-INC-02 | — | DESFECHO | L2085:18-75; L2087:0-23; L2089:0-50; L2090:0-159; L2091:0-185; L2092:0-72; L2093:0-231; L2094:0-94; L2095:0-55; L2096:0-88 | L2090:0-159 | CONCEPT:9.3; MODELO:Etapa; RQ-FLX-01; RQ-FLX-04; RQ-GOV-29; RQ-GOV-30 |
| RQ-INC-03 | — | DESFECHO | L2098:18-249 | — | CONCEPT:9.7 |
| RQ-INC-04 | — | DESFECHO | L2099:18-168 | — | CONCEPT:9.12 |
| RQ-INC-05 | — | DESFECHO | L2100:18-268 | =texto | RQ-FLX-22; RQ-LIN-19 |
| RQ-DEG-01 | — | OPERACIONAL | L2106:18-423 | =texto | CONCEPT:9.11; EV-INDISPONIBILIDADE; RQ-DEG-04; RQ-RES-04 |
| RQ-DEG-02 | — | OPERACIONAL | L2107:18-1196 | — | C-02; EV-INDISPONIBILIDADE; FN-INT-01; RQ-DAD-34; RQ-FLX-01; TPL-01 |
| RQ-DEG-03 | — | OPERACIONAL | L2108:18-515 | =texto | CONCEPT:6.5; CONCEPT:9.11; RQ-DEG-04; RQ-FLX-01 |
| RQ-DEG-04 | — | OPERACIONAL | L2109:18-1738 | =texto | C-02; C-11; CFG-DOC; CONCEPT:9.11; EV-INDISPONIBILIDADE; RQ-FLX-01; RQ-FLX-02; RQ-RES-11; TPL-12; V-16 |
| RQ-DEG-05 | — | OPERACIONAL | L2110:18-643 | =texto | C-04; CFG-TPL; RQ-DEG-04; RQ-FLX-15; S:4.4.11; TPL-04 |
| RQ-DEG-06 | — | OPERACIONAL | L2111:18-245 | =texto | C-06; C-07; C-09; C-10; C-13 |
| RQ-DEG-07 | — | OPERACIONAL | L2112:18-142 | =texto | RQ-EVO-05 |
| RQ-DEG-08 | — | OPERACIONAL | L2113:18-531 | =texto | RQ-DEG-02; RQ-DEG-04 |
| RQ-DEG-09 | — | OPERACIONAL | L2114:18-1047 | =texto | CFG-DOC; CFG-PRV; CFG-TPL; RQ-DAD-22; RQ-DAD-43; RQ-DEG-04; RQ-FLX-19; S:4.4.16; S:4.4.22; TPL-01; TPL-02; TPL-03; TPL-04; TPL-05; TPL-06; TPL-07; TPL-08; TPL-09; TPL-10; TPL-11; TPL-12; TPL-13; V-06 |
| RQ-DEG-10 | — | OPERACIONAL | L2115:18-651 | =texto | CFG-OPR; RQ-DEG-04; S:4.4.24 |
| RQ-RAS-01 | — | GOVERNANCA | L2121:18-631 | =texto | C-13; CONCEPT:5.10; ENUM-NaturezaRegistro; RQ-FLX-17 |
| RQ-RAS-02 | — | GOVERNANCA | L2122:18-734; L2124:0-21; L2126:0-178; L2127:0-91; L2128:0-333; L2129:0-56; L2130:0-40; L2131:0-51; L2132:0-64; L2133:0-130; L2134:0-74; L2135:0-39; L2136:0-28 | L2132:0-64; L2133:0-130 | CFG-OPR; EV-ADMISSIBILIDADE; EV-ALTERACAO-ESTADO; EV-AMPLIACAO; EV-AUTORIZACAO; EV-CANCELAMENTO; EV-CAPTURA-SELECAO; EV-CONFIG; EV-CONFIRMACAO-USO; EV-CONFLITO; EV-DISPONIBILIDADE; EV-ESTADO-BASE; EV-EXAME; EV-EXECUCAO; EV-EXPORTACAO; EV-FALHA; EV-INDISPONIBILIDADE; EV-INGESTAO; EV-INTERACAO_USUARIO; EV-INTERPRETACAO; EV-INVALIDACAO; EV-LEITURA-MINIMA; EV-LINHA; EV-MENSAGEM; EV-META; EV-PENDENCIA; EV-PERGUNTA; EV-PERTINENCIA; EV-PLANO; EV-PRIVACIDADE; EV-RCNA; EV-REAUTORIZACAO; EV-REPLANEJAMENTO; EV-REPRESENTACAO; EV-RESPOSTA; EV-RESULTADO; EV-RETORNO_TARDIO_DESCARTADO; EV-REUSO; EV-REVELACAO; EV-SESSAO; EV-SINTESE; EV-SUGESTAO; EV-SUGESTAO-ACEITA; EV-SUSPENSAO; EV-TRIAGEM; EV-VALIDACAO-INTERPRETACAO; EV-VALIDACAO-PLANO; EV-VALIDACAO-SAIDA; EV-VERIFICACAO; EV-VIGENCIA; MODELO:ResultadoElemento |
| RQ-RAS-03 | — | GOVERNANCA | L2138:18-1146 | =texto | CONCEPT:5.10; CONCEPT:8.7; EV-AUTORIZACAO; EV-CAPTURA-SELECAO; EV-CONFLITO; EV-EXECUCAO; EV-INDISPONIBILIDADE; EV-INTERPRETACAO; EV-INVALIDACAO; EV-LINHA; EV-MENSAGEM; EV-PLANO; EV-REPLANEJAMENTO; EV-REPRESENTACAO; EV-RESPOSTA; EV-RESULTADO; EV-SINTESE; EV-VERIFICACAO; EV-VIGENCIA |
| RQ-RAS-04 | — | GOVERNANCA | L2139:18-1221 | =texto | C-10; RQ-DAD-20 |
| RQ-RAS-05 | — | GOVERNANCA | L2140:18-885 | =texto | C-10; CFG-DOC; CONCEPT:5.10; CONCEPT:8.7; EV-REPRESENTACAO; RQ-DAD-20; TPL-12 |
| RQ-RAS-06 | — | GOVERNANCA | L2141:18-537 | — | C-13; RQ-FLX-17; RQ-REP-12 |
| RQ-RAS-07 | — | GOVERNANCA | L2142:18-1224 | =texto | C-10; C-13; ENUM-StatusBase; EV-AUTORIZACAO; EV-ESTADO-BASE; EV-INGESTAO; EV-LEITURA-MINIMA; EV-MENSAGEM; EV-REVELACAO; RQ-DAD-20; RQ-DAD-33; RQ-DAD-34; RQ-DAD-39; RQ-DAD-42 |
| RQ-PRV-01 | — | PRIVACIDADE | L2148:18-342 | — | CONCEPT:3.8; RQ-DAD-22; RQ-DAD-33; S:5.5 |
| RQ-PRV-02 | — | PRIVACIDADE | L2149:18-312 | =texto | INV-16; RQ-DAD-23; RQ-DAD-37; RQ-DAD-38; RQ-DAD-39 |
| RQ-PRV-03 | — | PRIVACIDADE | L2150:18-356 | =texto | C-04; EV-PRIVACIDADE |
| RQ-PRV-04 | — | PRIVACIDADE | L2151:18-95 | — | EXC-09; EXC-10 |
| RQ-PRV-05 | — | PRIVACIDADE | L2152:18-214 | =texto | CAP-ROT-01 |
| RQ-PRV-06 | — | PRIVACIDADE | L2153:18-125 | =texto | — |
| RQ-PRV-07 | — | PRIVACIDADE | L2154:18-243 | =texto | RQ-REP-13 |
| RQ-PRV-08 | — | PRIVACIDADE | L2155:18-487 | — | C-13; RQ-DAD-17; RQ-FLX-17 |
| RQ-PRV-09 | — | PRIVACIDADE | L2156:18-235 | =texto | CFG-PRV; PARTE:19 |
| RQ-PRV-10 | — | PRIVACIDADE | L2157:18-453 | =texto | CAP-ROT-01; EXC-09; EXC-10 |
| RQ-EVO-01 | — | GOVERNANCA | L2163:18-459; L2166:0-15; L2167:2-4; L2168:2-88; L2169:15-65; L2170:2-18; L2171:2-23; L2172:4-39; L2173:4-63; L2174:4-37; L2175:4-50; L2176:4-27; L2177:4-42; L2178:4-44; L2179:4-46; L2180:4-43; L2181:4-57; L2182:2-86; L2183:21-75; L2184:2-85; L2185:2-65; L2186:2-79; L2187:2-60 | L2163:18-459 | CONCEPT:11.12; CONCEPT:11.9; RQ-CFG-05; RQ-QUA-02 |
| RQ-EVO-02 | — | GOVERNANCA | L2190:18-419 | =texto | CFG-CAP; CONCEPT:11.9; RQ-GOV-12; RQ-ORQ-10 |
| RQ-EVO-03 | — | GOVERNANCA | L2191:18-164 | =texto | RQ-ESC-09 |
| RQ-EVO-04 | — | GOVERNANCA | L2192:18-187 | =texto | CONCEPT:11.4; CONCEPT:11.5 |
| RQ-EVO-05 | — | GOVERNANCA | L2193:18-540 | =texto | CONCEPT:11.10; PARTE:20 |
| RQ-EVO-06 | — | GOVERNANCA | L2194:18-172 | — | PARTE:22; RQ-QUA-02 |
| RQ-EVO-07 | — | GOVERNANCA | L2195:18-201 | — | CONCEPT:11.11 |
| RQ-EVO-08 | — | GOVERNANCA | L2196:18-234 | =texto | CONCEPT:11.6; PARTE:5 |
| RQ-EVO-09 | — | GOVERNANCA | L2197:18-136 | — | CONCEPT:11.8 |
| RQ-EVO-10 | — | GOVERNANCA | L2198:18-404 | =texto | RQ-CFG-01; RQ-CFG-12 |
| RQ-QUA-01 | — | GOVERNANCA | L2215:18-124; L2217:0-71; L2219:0-138; L2220:0-96; L2221:0-90; L2222:0-104; L2223:0-114; L2224:0-162; L2225:0-79 | — | INV-01; INV-02; INV-03; INV-04; INV-11; INV-13; INV-16; PARTE:18; PARTE:8; RQ-ARQ-02; RQ-ARQ-09; RQ-CAP-02; RQ-CAP-03; RQ-DAD-07; RQ-ORQ-05; V-01; V-02; V-03; V-04; V-05; V-06; V-07; V-08; V-09; V-10; V-11; V-12; V-13; V-14; V-15; V-16 |
| RQ-QUA-02 | — | GOVERNANCA | L2227:18-358 | =texto | — |
| RQ-QUA-03 | — | GOVERNANCA | L2228:18-307 | — | RQ-QUA-01 |
| RQ-QUA-04 | — | GOVERNANCA | L2229:18-309 | — | — |
| RQ-QUA-05 | — | GOVERNANCA | L2230:18-2845 | =texto | ENUM-TipoContagemAgregada; MODELO:ContextoDeMedida; S:20.10; S:20.11; S:20.9 |
| RQ-QUA-06 | — | GOVERNANCA | L2231:18-811 | =texto | CONCEPT:10.7; RQ-CFG-14 |
| RQ-QUA-07 | — | GOVERNANCA | L2232:18-1037 | =texto | CFG-DOC; CFG-TPL; CONCEPT:10.4; RQ-REP-09; S:4.4.23.2; TPL-04; TPL-12; TPL-13; V-01; V-02; V-16 |
| INV-01 | — | GOVERNANCA | L289:11-107 | — | CONCEPT:6.4 |
| INV-02 | — | GOVERNANCA | L290:11-214 | — | CONCEPT:5.6 |
| INV-03 | — | GOVERNANCA | L291:11-130 | — | CONCEPT:5.8; CONCEPT:8.6 |
| INV-04 | — | GOVERNANCA | L292:11-297 | =texto | CONCEPT:13.2; CONCEPT:7.4 |
| INV-05 | — | GOVERNANCA | L293:11-132 | — | CONCEPT:9.12; CONCEPT:9.2 |
| INV-06 | — | GOVERNANCA | L294:11-146 | — | CONCEPT:3.6 |
| INV-07 | — | GOVERNANCA | L295:11-75 | — | CONCEPT:8.10 |
| INV-08 | — | GOVERNANCA | L296:11-113 | — | CONCEPT:7.7 |
| INV-09 | — | GOVERNANCA | L297:11-416 | =texto | CONCEPT:7.7; RQ-LIN-20; RQ-ORQ-07; RQ-ORQ-13 |
| INV-10 | — | GOVERNANCA | L298:11-341 | =texto | CONCEPT:6.5; RQ-ORQ-13 |
| INV-11 | — | GOVERNANCA | L299:11-88 | — | CONCEPT:4.3.14; CONCEPT:4.3.15 |
| INV-12 | — | GOVERNANCA | L300:11-133 | — | CONCEPT:5.10 |
| INV-13 | — | GOVERNANCA | L301:11-91 | — | — |
| INV-14 | — | GOVERNANCA | L302:11-116 | — | CONCEPT:5.8 |
| INV-15 | — | GOVERNANCA | L303:11-173 | =texto | CONCEPT:5.3 |
| INV-16 | — | GOVERNANCA | L304:11-569 | =texto | CONCEPT:3.8 |
| INV-17 | — | GOVERNANCA | L305:11-143 | =texto | CONCEPT:3.3; CONCEPT:5.12 |
| INV-18 | — | GOVERNANCA | L306:11-287 | =texto | CONCEPT:11.11; CONCEPT:4.3.14 |
| FAM-01 | finalidade | FINALIDADE | L200:11-95; L200:98-104 | — | CONCEPT:4.3.3 |
| FAM-01 | natureza | CAPACIDADE | L200:120-173 | — | — |
| FAM-02 | finalidade | FINALIDADE | L201:11-59; L201:62-68 | — | CONCEPT:4.3.5 |
| FAM-02 | natureza | CAPACIDADE | L201:96-163 | — | CFG-IND; EXC-04 |
| FAM-03 | finalidade | FINALIDADE | L202:11-47; L202:50-54 | — | CONCEPT:3.2 |
| FAM-03 | natureza | CAPACIDADE | L202:101-102 | — | — |
| FAM-04 | finalidade | FINALIDADE | L203:11-84; L203:87-93 | L203:11-84 | CONCEPT:4.3.7 |
| FAM-04 | natureza | CAPACIDADE | L203:109-140 | — | — |
| FAM-05 | finalidade | FINALIDADE | L204:11-61; L204:64-74 | — | CONCEPT:3.1; CONCEPT:3.2 |
| FAM-05 | natureza | CAPACIDADE | L204:135-177 | — | FAM-04 |
| FAM-06 | finalidade | FINALIDADE | L205:11-64; L205:67-73 | — | CONCEPT:4.3.8 |
| FAM-06 | natureza | CAPACIDADE | L205:89-142 | — | — |
| FAM-07 | finalidade | FINALIDADE | L206:11-54; L206:57-63 | — | CONCEPT:4.3.6 |
| FAM-07 | natureza | CAPACIDADE | L206:103-137 | — | — |
| FAM-08 | finalidade | FINALIDADE | L207:11-80; L207:83-98 | — | CONCEPT:4.3.10; CONCEPT:4.3.9 |
| FAM-08 | natureza | CAPACIDADE | L207:138-216 | — | — |
| FAM-09 | finalidade | FINALIDADE | L208:11-84; L208:87-94 | — | CONCEPT:4.3.11 |
| FAM-09 | natureza | CAPACIDADE | L208:110-141 | — | — |
| FAM-10 | finalidade | FINALIDADE | L209:11-51; L209:54-61 | — | CONCEPT:4.3.12 |
| FAM-10 | natureza | CAPACIDADE | L209:101-171 | — | EXC-05 |
| FAM-11 | finalidade | FINALIDADE | L210:11-46; L210:49-56 | — | CONCEPT:4.3.13 |
| FAM-11 | natureza | CAPACIDADE | L210:96-136 | — | — |
| FAM-12 | finalidade | FINALIDADE | L211:11-57; L211:60-70 | — | CONCEPT:4.4; CONCEPT:6.5 |
| FAM-12 | natureza | CAPACIDADE | L211:98-130 | — | — |
| FAM-13 | finalidade | FINALIDADE | L212:11-61; L212:64-78 | — | CONCEPT:4.3.14; CONCEPT:8.12 |
| FAM-13 | natureza | CAPACIDADE | L212:107-174 | — | — |
| FAM-14 | finalidade | FINALIDADE | L213:11-65; L213:68-75 | — | CONCEPT:4.3.15 |
| FAM-14 | natureza | CAPACIDADE | L213:91-114 | — | — |
| EXC-01 | — | LIMITACAO | L225:11-70; L225:73-79 | — | — |
| EXC-02 | — | LIMITACAO | L226:11-74; L226:77-83 | — | — |
| EXC-03 | — | LIMITACAO | L227:11-28; L227:31-37 | — | — |
| EXC-04 | — | LIMITACAO | L228:11-94; L228:97-103 | — | — |
| EXC-05 | — | LIMITACAO | L229:11-98; L229:101-107 | — | — |
| EXC-06 | — | LIMITACAO | L230:11-88; L230:91-97 | — | — |
| EXC-07 | — | LIMITACAO | L231:11-77; L231:80-106 | — | INV-14 |
| EXC-08 | — | LIMITACAO | L232:11-55; L232:58-201 | L232:58-201 | CONCEPT:3.6 |
| EXC-09 | — | LIMITACAO | L233:11-72; L233:75-96 | — | PARTE:18 |
| EXC-10 | — | LIMITACAO | L234:11-111; L234:114-135 | — | PARTE:18 |
| EXC-11 | — | LIMITACAO | L235:11-82; L235:85-170 | — | INV-06 |
| V-01 | — | GOVERNANCA | L2032:9-626 | =texto | CFG-DOC; CFG-LEX; RQ-REP-05; RQ-REP-11 |
| V-02 | — | GOVERNANCA | L2033:9-362 | =texto | CFG-DOC; RQ-SIN-10; V-16 |
| V-03 | — | GOVERNANCA | L2034:9-370 | =texto | CFG-NOR; RQ-GOV-31; RQ-SIN-10; S:4.4.15 |
| V-04 | — | GOVERNANCA | L2035:9-71 | — | — |
| V-05 | — | GOVERNANCA | L2036:9-473 | =texto | CAP-TEN-01; CAP-TMP-01; RQ-SIN-10 |
| V-06 | — | GOVERNANCA | L2037:9-202 | — | TPL-11 |
| V-07 | — | GOVERNANCA | L2038:9-232 | =texto | — |
| V-08 | — | GOVERNANCA | L2039:9-260 | =texto | TPL-12 |
| V-09 | — | GOVERNANCA | L2040:9-498 | =texto | RQ-DEG-04 |
| V-10 | — | GOVERNANCA | L2041:9-228 | — | — |
| V-11 | — | GOVERNANCA | L2042:9-278 | =texto | — |
| V-12 | — | GOVERNANCA | L2043:9-140 | =texto | — |
| V-13 | — | GOVERNANCA | L2044:9-173 | — | RQ-RES-06 |
| V-14 | — | GOVERNANCA | L2045:9-320 | — | — |
| V-15 | — | GOVERNANCA | L2046:9-533 | =texto | CAP-ROT-01; CFG-DOC; RQ-RES-11; TPL-12 |
| V-16 | — | GOVERNANCA | L2047:9-924 | =texto | CFG-DOC; FN-INT-03; FN-META-01; RQ-SIN-05; TPL-12 |
| TPL-01 | — | REPRESENTACAO | L1094:11-42; L1094:45-313 | =texto | RQ-DEG-02; RQ-DEG-04 |
| TPL-02 | — | REPRESENTACAO | L1095:11-46; L1095:49-190 | =texto | RQ-DEG-06 |
| TPL-03 | — | REPRESENTACAO | L1096:11-37; L1096:40-157 | =texto | RQ-ORQ-14 |
| TPL-04 | — | REPRESENTACAO | L1097:11-53; L1097:56-269 | L1097:11-53; L1097:56-269; L1108:0-2942 | CFG-DOC; CFG-OPC; CFG-PRV; MODELO:ConjuntoOpcoesAutorizadas; MODELO:OpcaoAutorizada; MODELO:RefEscopo; RQ-GOV-19; RQ-RES-04; S:4.4.11; S:4.4.22; S:4.4.23.6; TPL-12; V-16 |
| TPL-05 | — | REPRESENTACAO | L1098:11-17; L1098:20-148 | =texto | — |
| TPL-06 | — | REPRESENTACAO | L1099:11-17; L1099:20-150 | =texto | — |
| TPL-07 | — | REPRESENTACAO | L1100:11-17; L1100:20-209 | =texto | — |
| TPL-08 | — | REPRESENTACAO | L1101:11-44; L1101:47-194 | =texto | RQ-SIN-05 |
| TPL-09 | — | REPRESENTACAO | L1102:11-43; L1102:46-348 | =texto | RQ-FLX-17; RQ-FLX-19 |
| TPL-10 | — | REPRESENTACAO | L1103:11-40; L1103:43-436 | =texto | RQ-DAD-22 |
| TPL-11 | — | REPRESENTACAO | L1104:11-37; L1104:40-163 | =texto | V-06 |
| TPL-12 | — | REPRESENTACAO | L1105:11-76; L1105:79-303 | L1105:11-76; L1105:79-303; L1108:0-2942 | CFG-DOC; CFG-OPC; CFG-PRV; MODELO:ConjuntoOpcoesAutorizadas; MODELO:OpcaoAutorizada; MODELO:RefEscopo; RQ-DEG-04; RQ-RES-04; RQ-SIN-05; S:4.4.11; S:4.4.22; S:4.4.23.6; TPL-04; V-16 |
| ENUM-TipoFonte | — | IDENTIDADE | L375:14-151; L375:154-217 | =texto | CONCEPT:5.8; CONCEPT:7.2; INV-03 |
| ENUM-SubtipoManifestacao | — | IDENTIDADE | L376:24-92; L376:95-247 | =texto | CONCEPT:8.6; ENUM-TipoFonte |
| ENUM-TipoPedido | — | IDENTIDADE | L377:15-103; L377:106-334 | =texto | RQ-FLX-09 |
| ENUM-OrigemBase | — | IDENTIDADE | L378:15-79; L378:82-252 | =texto | CFG-FON; ENUM-TipoFonte |
| ENUM-TipoDadoConversacional | — | IDENTIDADE | L379:27-104; L379:107-180 | =texto | RQ-DAD-40 |
| ENUM-TipoAutorizacao | — | IDENTIDADE | L380:20-43; L380:46-89 | =texto | RQ-DAD-34; S:7.7 |
| ENUM-FuncaoConteudo | — | IDENTIDADE | L381:19-75; L381:78-162 | =texto | RQ-SIN-10 |
| ENUM-Pertinencia | — | IDENTIDADE | L382:16-63; L382:66-124 | =texto | CONCEPT:5.2 |
| ENUM-Desfecho | — | IDENTIDADE | L383:13-143; L383:146-177 | =texto | CONCEPT:9.2; PARTE:15 |
| ENUM-MotivoSemCapacidade | — | IDENTIDADE | L384:24-103; L384:106-392 | =texto | ENUM-MotivoNaoAvaliavel; RQ-DAD-26 |
| ENUM-StatusCapacidade | — | IDENTIDADE | L385:21-53; L385:56-108 | =texto | CFG-CAP |
| ENUM-DisponibilidadeOperacional | — | IDENTIDADE | L386:31-71; L386:74-115 | =texto | RQ-ARQ-11 |
| ENUM-Avaliabilidade | — | AVALIABILIDADE | L387:19-61; L387:64-110 | =texto | CONCEPT:9.2 |
| ENUM-MotivoNaoAvaliavel | — | AVALIABILIDADE | L388:23-251; L388:254-293 | =texto | PARTE:19 |
| ENUM-DetalheMotivo | — | AVALIABILIDADE | L389:18-82; L389:85-155 | =texto | CAP-ESP-02; CAP-ROT-01 |
| ENUM-MotivoSemClassificacao | — | IDENTIDADE | L390:27-60; L390:63-125 | =texto | CAP-TEN-01 |
| ENUM-CondicaoCriterio | — | IDENTIDADE | L391:21-54; L391:57-69 | =texto | CONCEPT:4.3.13 |
| ENUM-OperadorLogico | — | IDENTIDADE | L392:19-29; L392:32-72 | =texto | CAP-SUB-01 |
| ENUM-Validade | — | IDENTIDADE | L393:13-31; L393:34-68 | =texto | CONCEPT:7.7 |
| ENUM-Vigencia | — | IDENTIDADE | L394:13-33; L394:36-84 | =texto | CONCEPT:7.7 |
| ENUM-MotivoNaoVigencia | — | IDENTIDADE | L395:22-66; L395:69-175 | =texto | RQ-LIN-20 |
| ENUM-Reproducao | — | IDENTIDADE | L396:15-53; L396:56-65 | =texto | CONCEPT:7.7 |
| ENUM-Apresentabilidade | — | IDENTIDADE | L397:22-60; L397:63-73 | =texto | CONCEPT:5.10 |
| ENUM-PapelResultado | — | IDENTIDADE | L398:19-64; L398:67-114 | =texto | CONCEPT:5.9; CONCEPT:8.4 |
| ENUM-StatusSolicitacao | — | IDENTIDADE | L399:22-164; L399:167-269 | =texto | PARTE:6 |
| ENUM-StatusEntregavel | — | IDENTIDADE | L400:21-80; L400:83-332 | =texto | RQ-FLX-02; RQ-RES-04 |
| ENUM-StatusEtapa | — | IDENTIDADE | L401:16-114; L401:117-217 | =texto | RQ-FLX-01 |
| ENUM-StatusPendencia | — | IDENTIDADE | L402:20-69; L402:72-119 | =texto | CONCEPT:7.8; CONCEPT:9.10 |
| ENUM-TipoPendencia | — | IDENTIDADE | L403:18-312; L403:315-700 | =texto | RQ-DAD-38; RQ-DAD-42; RQ-DAD-43; RQ-FLX-01 |
| ENUM-NaturezaAlteracao | — | IDENTIDADE | L404:22-77; L404:80-95 | =texto | CONCEPT:7.7; CONCEPT:7.9 |
| ENUM-StatusSignificado | — | IDENTIDADE | L405:22-136; L405:139-274 | =texto | CONCEPT:7.3; RQ-DAD-06 |
| ENUM-ProtecaoCampo | — | IDENTIDADE | L406:18-139; L406:142-261 | =texto | RQ-DAD-38; S:5.5 |
| ENUM-NaturezaEntidadeNominal | — | IDENTIDADE | L407:28-117; L407:120-192 | =texto | CFG-PRV; RQ-DAD-38 |
| ENUM-TipoPlaceholder | — | IDENTIDADE | L408:20-109; L408:112-160 | =texto | RQ-DAD-39 |
| ENUM-ReconhecimentoFTS | — | IDENTIDADE | L409:22-82; L409:85-317 | =texto | CFG-DOM; S:4.3 |
| ENUM-ModoTerritorial | — | IDENTIDADE | L410:20-88; L410:91-100 | =texto | CONCEPT:3.2 |
| ENUM-DimensaoRecorte | — | IDENTIDADE | L411:20-77; L411:80-130 | =texto | RQ-LIN-19 |
| ENUM-ClasseAutoridade | — | IDENTIDADE | L412:21-100; L412:103-112 | =texto | CONCEPT:5.5 |
| ENUM-NaturezaRegistro | — | IDENTIDADE | L413:21-189; L413:192-238 | =texto | CONCEPT:8.7 |
| ENUM-ModoExplicitacao | — | IDENTIDADE | L414:21-93; L414:96-111 | =texto | CONCEPT:5.7; CONCEPT:9.4 |
| ENUM-CategoriaTendencia | — | IDENTIDADE | L415:23-155; L415:158-456 | =texto | CONCEPT:4.3.10 |
| ENUM-DirecaoMudanca | — | IDENTIDADE | L416:19-48; L416:51-97 | =texto | — |
| ENUM-TipoContagemAgregada | — | IDENTIDADE | L417:25-65; L417:68-255 | =texto | CAP-AGR-01 |
| ENUM-FundamentoUnicidade | — | IDENTIDADE | L418:24-81; L418:84-303 | =texto | CAP-AGR-01 |
| ENUM-CategoriaLimitacao | — | IDENTIDADE | L419:23-41; L419:44-117 | =texto | — |
| ENUM-CanalEntrada | — | IDENTIDADE | L420:17-63; L420:66-133 | =texto | — |
| ENUM-Idioma | — | IDENTIDADE | L421:11-17; L421:20-26 | =texto | — |
| ENUM-CaminhoProposicaoDocumental | — | IDENTIDADE | L422:32-235; L422:238-328 | =texto | CFG-DOC |
| ENUM-IdiomaProposicaoDocumental | — | IDENTIDADE | L423:31-37; L423:40-163 | =texto | CFG-DOC |
| ENUM-TipoProposicaoDocumental | — | IDENTIDADE | L424:29-181; L424:184-285 | =texto | — |
| ENUM-StatusSessao | — | IDENTIDADE | L425:17-33; L425:36-49 | =texto | — |
| ENUM-StatusBase | — | IDENTIDADE | L426:15-101; L426:104-192 | =texto | RQ-DAD-42 |
| ENUM-PresencaNoUniverso | — | IDENTIDADE | L427:23-85; L427:88-97 | =texto | CONCEPT:7.4 |
| ENUM-TipoLinha | — | IDENTIDADE | L428:14-34; L428:37-46 | =texto | CONCEPT:7.6 |
| ENUM-StatusLinha | — | IDENTIDADE | L429:16-41; L429:44-60 | =texto | CONCEPT:7.6; CONCEPT:9.10 |
| GLOSSARIO-Componente | — | IDENTIDADE | L113:15-147 | — | CONCEPT:13.3; PARTE:2 |
| GLOSSARIO-Gate | — | IDENTIDADE | L114:9-150 | — | — |
| GLOSSARIO-Registro%20de%20interpreta%C3%A7%C3%A3o | — | IDENTIDADE | L115:30-135 | — | — |
| GLOSSARIO-Leitura%20sem%C3%A2ntica%20m%C3%ADnima | — | IDENTIDADE | L116:29-255 | — | CONCEPT:5.2; FN-INT-01 |
| GLOSSARIO-Interpreta%C3%A7%C3%A3o%20operacional | — | IDENTIDADE | L117:30-255 | — | CONCEPT:9.4; FN-INT-02 |
| GLOSSARIO-Entreg%C3%A1vel | — | IDENTIDADE | L118:15-936 | — | MODELO:ResultadoElemento; RQ-FLX-02; RQ-GOV-28; RQ-RES-04 |
| GLOSSARIO-Plano%20de%20composi%C3%A7%C3%A3o | — | IDENTIDADE | L119:24-84 | — | — |
| GLOSSARIO-Etapa | — | IDENTIDADE | L120:10-83 | — | — |
| GLOSSARIO-Assinatura%20material | — | IDENTIDADE | L121:24-125 | — | S:7.5 |
| GLOSSARIO-Chave%20de%20execu%C3%A7%C3%A3o | — | IDENTIDADE | L122:22-116 | — | S:9.3 |
| GLOSSARIO-Autoriza%C3%A7%C3%A3o | — | IDENTIDADE | L123:16-195 | — | C-04; RQ-DAD-34 |
| GLOSSARIO-Verifica%C3%A7%C3%A3o%20pr%C3%A9-execu%C3%A7%C3%A3o | — | IDENTIDADE | L124:29-103 | — | S:7.7 |
| GLOSSARIO-Snapshot%20de%20configura%C3%A7%C3%A3o | — | IDENTIDADE | L125:29-156 | — | — |
| GLOSSARIO-Sess%C3%A3o | — | IDENTIDADE | L126:11-377 | — | CFG-OPR; EV-INTERACAO_USUARIO; RQ-FLX-17 |
| GLOSSARIO-Idioma%20da%20sess%C3%A3o | — | IDENTIDADE | L127:21-73 | — | RQ-FLX-18 |
| GLOSSARIO-Avaliabilidade | — | IDENTIDADE | L128:19-123 | — | — |
| GLOSSARIO-Pend%C3%AAncia | — | IDENTIDADE | L129:14-532 | — | CONCEPT:7.8; RQ-DAD-42; RQ-FLX-01 |
| GLOSSARIO-Conjunto%20de%20op%C3%A7%C3%B5es%20autorizadas | — | IDENTIDADE | L130:35-530 | — | CFG-AMB; CFG-OPC; CONCEPT:9.5; MODELO:ConjuntoOpcoesAutorizadas; MODELO:OpcaoAutorizada; S:4.4.11 |
| GLOSSARIO-Evento | — | IDENTIDADE | L131:11-108 | — | C-13 |
| GLOSSARIO-Canal%20sist%C3%AAmico | — | IDENTIDADE | L132:20-82 | — | C-02; CONCEPT:9.11 |
| GLOSSARIO-Controle%20estruturado%20de%20interface | — | IDENTIDADE | L133:38-209 | — | — |
| GLOSSARIO-Ficha%20de%20proced%C3%AAncia | — | IDENTIDADE | L134:25-133 | — | — |
| GLOSSARIO-Gatilho%20de%20ambiguidade | — | IDENTIDADE | L135:27-107 | — | CFG-AMB |
| GLOSSARIO-Validador%20de%20sa%C3%ADda | — | IDENTIDADE | L136:23-131 | — | PARTE:14 |
| GLOSSARIO-Modo%20degradado | — | IDENTIDADE | L137:19-63 | — | PARTE:16 |
| GLOSSARIO-Disponibilidade%20operacional | — | IDENTIDADE | L138:32-147 | — | RQ-ARQ-11 |
| GLOSSARIO-Elementos%20ativos | — | IDENTIDADE | L139:21-120 | — | — |
| GLOSSARIO-Triagem%20estrutural%20e%20de%20privacidade | — | IDENTIDADE | L140:40-616 | — | RQ-DAD-20; S:5.5 |
| GLOSSARIO-Campo%20protegido | — | IDENTIDADE | L141:20-374 | — | RQ-DAD-39 |
| GLOSSARIO-Visualizador%20da%20base | — | IDENTIDADE | L142:25-168 | — | — |
| GLOSSARIO-Valor%20factual%20do%20usu%C3%A1rio | — | IDENTIDADE | L143:29-137 | — | — |
| GLOSSARIO-Substitui%C3%A7%C3%A3o%20expl%C3%ADcita | — | IDENTIDADE | L144:27-130 | — | — |
| GLOSSARIO-Crit%C3%A9rio%20normativo%20do%20usu%C3%A1rio | — | IDENTIDADE | L145:34-145 | — | — |
| GLOSSARIO-Agregado%20parcial | — | IDENTIDADE | L146:21-322 | — | CAP-AGR-01 |
| GLOSSARIO-Unidade%20de%20observa%C3%A7%C3%A3o | — | IDENTIDADE | L147:26-132 | — | RQ-DAD-35 |
| GLOSSARIO-Unidade%20de%20contagem | — | IDENTIDADE | L148:24-132 | — | — |
| GLOSSARIO-Identidade%20de%20deduplica%C3%A7%C3%A3o | — | IDENTIDADE | L149:31-167 | — | RQ-DAD-35 |
| GLOSSARIO-Suporte%20efetivo%20do%20agregado | — | IDENTIDADE | L150:32-199 | — | — |
| GLOSSARIO-Pequena%20base%20conversacional | — | IDENTIDADE | L151:32-371 | — | C-10; RQ-DAD-31; RQ-DAD-32; RQ-DAD-33; RQ-DAD-34; RQ-DAD-40; RQ-DAD-43 |
| GLOSSARIO-Soma%20das%20contagens%20dos%20componentes | — | IDENTIDADE | L152:39-245 | — | CAP-AGR-01 |
| GLOSSARIO-Premissa%20factual%20do%20usu%C3%A1rio | — | IDENTIDADE | L153:32-229 | — | RQ-GOV-22 |
| GLOSSARIO-Reconhecimento%20governado%20de%20categoria | — | IDENTIDADE | L154:42-254 | — | CFG-DOM; CFG-VOC; S:4.3 |
| GLOSSARIO-Categoria%20de%20reconhecimento%20contextual | — | IDENTIDADE | L155:43-256 | — | CFG-DOM; S:4.3 |
| GLOSSARIO-Declara%C3%A7%C3%A3o%20de%20dom%C3%ADnio%20da%20base | — | IDENTIDADE | L156:34-210 | — | RQ-DAD-19 |
| GLOSSARIO-Escala%20de%20apresenta%C3%A7%C3%A3o | — | IDENTIDADE | L157:27-267 | — | MODELO:ContextoDeMedida; S:3.2 |
| GLOSSARIO-Referencial%20geod%C3%A9sico | — | IDENTIDADE | L158:26-179 | — | S:5.6 |
| GLOSSARIO-Registro%20de%20conte%C3%BAdo%20n%C3%A3o%20ancorado%20%28RCNA%29 | — | IDENTIDADE | L159:45-199 | — | S:7.1 |
| GLOSSARIO-Linha%20de%20consolida%C3%A7%C3%A3o | — | IDENTIDADE | L160:26-129 | — | CONCEPT:7.6 |
| GLOSSARIO-V%C3%ADnculo%20resultado-linha | — | IDENTIDADE | L161:28-113 | — | S:3.2 |
| GLOSSARIO-Configura%C3%A7%C3%A3o%20Inicial%20de%20Implementa%C3%A7%C3%A3o | — | IDENTIDADE | L162:42-192 | — | RQ-DOC-06; S:4.4 |
| GLOSSARIO-Configura%C3%A7%C3%A3o%20deliberadamente%20vazia | — | IDENTIDADE | L163:39-202 | — | RQ-CFG-12 |
| GLOSSARIO-Valor%20factual%20complementar | — | IDENTIDADE | L164:31-421 | — | RQ-DAD-40; RQ-LIN-21 |
| GLOSSARIO-Declara%C3%A7%C3%A3o%20sem%C3%A2ntica | — | IDENTIDADE | L165:25-225 | — | RQ-DAD-40 |
| GLOSSARIO-Aditividade | — | IDENTIDADE | L166:16-248 | — | RQ-DAD-36 |
| GLOSSARIO-Recorte | — | IDENTIDADE | L167:12-209 | — | RQ-LIN-19 |
| GLOSSARIO-Dimens%C3%A3o%20da%20linha | — | IDENTIDADE | L168:22-217 | — | RQ-LIN-19 |
| GLOSSARIO-Resultado%20deslocado | — | IDENTIDADE | L169:24-266 | — | RQ-LIN-20 |
| GLOSSARIO-Car%C3%A1ter%20hist%C3%B3rico | — | IDENTIDADE | L170:22-264 | — | RQ-LIN-20 |
| GLOSSARIO-Qualificador%20obrigat%C3%B3rio | — | IDENTIDADE | L171:29-307 | — | RQ-RES-11; V-15 |
| GLOSSARIO-Entidade%20nominal%20amb%C3%ADgua | — | IDENTIDADE | L172:29-279 | — | RQ-DAD-38 |
| GLOSSARIO-Placeholder%20protegido | — | IDENTIDADE | L173:26-219 | — | RQ-DAD-39 |
| GLOSSARIO-Estado%20de%20prepara%C3%A7%C3%A3o%20da%20entrada | — | IDENTIDADE | L174:36-218 | — | ENUM-StatusBase; RQ-DAD-42 |
| GLOSSARIO-Pend%C3%AAncia%20habilitadora | — | IDENTIDADE | L175:27-272 | — | RQ-FLX-22 |
| GLOSSARIO-%C3%82ncora%20documental | — | IDENTIDADE | L176:22-261 | — | CFG-DOC; S:4.4.23; V-16 |
| GLOSSARIO-Coorte%20inicial | — | IDENTIDADE | L177:19-239 | — | CAP-ROT-01; S:8.4 |
| GLOSSARIO-Identidade%20longitudinal | — | IDENTIDADE | L178:28-204 | — | CAP-ROT-01; RQ-DAD-35 |
| CAP-EXA-01 | definicao | IDENTIDADE | L1703:15-29 | — | — |
| CAP-EXA-01 | natureza | CAPACIDADE | L1703:32-38; L1703:41-55; L1703:58-63 | — | FAM-01 |
| CAP-EXA-01 | entradas | DADOS | L1734:33-452; L1734:1225-1767 | =texto | RQ-DAD-20; RQ-DAD-23; RQ-DAD-30; RQ-DAD-34; RQ-DAD-42; RQ-DAD-43 |
| CAP-EXA-01 | saida | REPRESENTACAO | L1734:453-1154 | L1734:33-452; L1734:1225-1767 | CFG-TER; RQ-DAD-20; RQ-DAD-23; RQ-DAD-30; RQ-DAD-34; RQ-DAD-42; RQ-DAD-43; RQ-GOV-20; S:4.3 |
| CAP-EXA-01 | proibicoes | LIMITACAO | L1734:1155-1224 | L1734:33-452; L1734:1225-1767 | RQ-DAD-13; RQ-DAD-20; RQ-DAD-23; RQ-DAD-30; RQ-DAD-34; RQ-DAD-42; RQ-DAD-43 |
| CAP-UNI-01 | definicao | IDENTIDADE | L1704:15-33 | — | — |
| CAP-UNI-01 | natureza | CAPACIDADE | L1704:36-55; L1704:58-72; L1704:75-80 | — | — |
| CAP-UNI-01 | entradas | DADOS | L1736:37-81 | L1736:82-266; L1736:267-498 | MODELO:DefinicaoUniverso; RQ-DAD-09; RQ-DAD-12; RQ-DAD-29; RQ-GOV-14 |
| CAP-UNI-01 | parametros | OPERACIONAL | L1736:82-266 | L1736:82-266; L1736:267-498 | RQ-DAD-09; RQ-DAD-12; RQ-DAD-29; RQ-GOV-14 |
| CAP-UNI-01 | precondicoes | PRECONDICAO | L1736:267-498 | L1736:82-266; L1736:267-498 | RQ-DAD-09; RQ-DAD-12; RQ-DAD-29; RQ-GOV-14 |
| CAP-UNI-01 | saida | REPRESENTACAO | L1736:499-867 | L1736:82-266; L1736:267-498 | CAP-SUB-01; ENUM-DetalheBloqueio; ENUM-PresencaNoUniverso; RQ-DAD-09; RQ-DAD-12; RQ-DAD-29; RQ-FLX-16; RQ-GOV-14 |
| CAP-IND-01 | definicao | IDENTIDADE | L1705:15-36 | — | — |
| CAP-IND-01 | natureza | CAPACIDADE | L1705:39-45; L1705:48-62; L1705:65-70 | — | FAM-02 |
| CAP-IND-01 | entradas | DADOS | L1738:40-95 | L1738:96-793; L1740:0-938; L1740:939-1119 | CAP-AGR-01; CFG-IND; ENUM-Avaliabilidade; RQ-DAD-18; RQ-DAD-19; RQ-DAD-35; RQ-GOV-14 |
| CAP-IND-01 | parametros | OPERACIONAL | L1738:96-793 | L1738:96-793; L1740:0-938; L1740:939-1119 | CAP-AGR-01; ENUM-Avaliabilidade; RQ-DAD-18; RQ-DAD-19; RQ-DAD-35; RQ-GOV-14 |
| CAP-IND-01 | metodo | METODO | L1740:0-938 | L1738:96-793; L1740:0-938; L1740:939-1119 | CAP-AGR-01; ENUM-Avaliabilidade; RQ-DAD-18; RQ-DAD-19; RQ-DAD-35; RQ-GOV-14 |
| CAP-IND-01 | avaliabilidade | AVALIABILIDADE | L1740:939-1119 | L1738:96-793; L1740:0-938; L1740:939-1119 | CAP-AGR-01; ENUM-Avaliabilidade; RQ-DAD-18; RQ-DAD-19; RQ-DAD-35; RQ-GOV-14 |
| CAP-IND-01 | saida | REPRESENTACAO | L1740:1120-1260 | L1738:96-793; L1740:0-938; L1740:939-1119 | CAP-AGR-01; ENUM-Avaliabilidade; RQ-DAD-18; RQ-DAD-19; RQ-DAD-35; RQ-GOV-14 |
| CAP-IND-02 | definicao | IDENTIDADE | L1706:15-24 | — | — |
| CAP-IND-02 | natureza | CAPACIDADE | L1706:27-33; L1706:36-50; L1706:53-58 | — | FAM-02 |
| CAP-IND-02 | metodo | METODO | L1742:28-407 | L1742:28-407; L1742:702-1182 | CAP-IND-01; RQ-DAD-36; RQ-GOV-21; RQ-GOV-22 |
| CAP-IND-02 | representacao | REPRESENTACAO | L1742:408-701 | L1742:28-407; L1742:702-1182 | CAP-IND-01; CFG-IND; RQ-DAD-36; RQ-GOV-21; RQ-GOV-22 |
| CAP-IND-02 | precondicoes | PRECONDICAO | L1742:702-1182 | L1742:28-407; L1742:702-1182 | CAP-IND-01; RQ-DAD-36; RQ-GOV-21; RQ-GOV-22 |
| CAP-IND-02 | avaliabilidade | AVALIABILIDADE | L1742:1183-1491 | L1742:28-407; L1742:702-1182 | CAP-AGR-01; CAP-IND-01; ENUM-Avaliabilidade; RQ-DAD-36; RQ-GOV-21; RQ-GOV-22 |
| CAP-IND-02 | proibicoes | LIMITACAO | L1742:1492-1547 | L1742:28-407; L1742:702-1182 | CAP-IND-01; RQ-DAD-36; RQ-GOV-21; RQ-GOV-22 |
| CAP-AGR-01 | definicao | IDENTIDADE | L1707:15-33 | — | — |
| CAP-AGR-01 | natureza | CAPACIDADE | L1707:36-42; L1707:45-59; L1707:62-67 | — | FAM-06 |
| CAP-AGR-01 | entradas | DADOS | L1744:37-205 | L1744:206-1607; L1746:0-487; L1747:0-380; L1749:0-714; L1749:715-1112; L1749:1113-2527; L1751:177-488; L1751:489-1648 | CAP-CMP-01; CAP-TEN-01; CAP-TMP-01; CFG-TER; ENUM-FundamentoUnicidade; ENUM-TipoContagemAgregada; RQ-CAP-08; RQ-DAD-05; RQ-DAD-30; RQ-DAD-35; RQ-DAD-36; RQ-GOV-03; RQ-GOV-21; RQ-GOV-22; RQ-ORQ-13; RQ-REP-14; S:4.4.7; V-01; V-07; V-14 |
| CAP-AGR-01 | metodo | METODO | L1744:206-1607; L1746:0-487; L1747:0-380; L1749:0-714; L1751:0-176 | L1744:206-1607; L1746:0-487; L1747:0-380; L1749:0-714; L1749:715-1112; L1749:1113-2527; L1751:177-488; L1751:489-1648 | CAP-CMP-01; CAP-TEN-01; CAP-TMP-01; CFG-TER; ENUM-FundamentoUnicidade; ENUM-TipoContagemAgregada; RQ-CAP-08; RQ-DAD-05; RQ-DAD-30; RQ-DAD-35; RQ-DAD-36; RQ-GOV-03; RQ-GOV-21; RQ-GOV-22; RQ-ORQ-13; RQ-REP-14; S:4.4.7; V-01; V-07; V-14 |
| CAP-AGR-01 | precondicoes | PRECONDICAO | L1749:715-1112 | L1744:206-1607; L1746:0-487; L1747:0-380; L1749:0-714; L1749:715-1112; L1749:1113-2527; L1751:177-488; L1751:489-1648 | CAP-CMP-01; CAP-TEN-01; CAP-TMP-01; CFG-TER; ENUM-FundamentoUnicidade; ENUM-TipoContagemAgregada; RQ-CAP-08; RQ-DAD-05; RQ-DAD-30; RQ-DAD-35; RQ-DAD-36; RQ-GOV-03; RQ-GOV-21; RQ-GOV-22; RQ-ORQ-13; RQ-REP-14; S:4.4.7; V-01; V-07; V-14 |
| CAP-AGR-01 | avaliabilidade | AVALIABILIDADE | L1749:1113-2527 | L1744:206-1607; L1746:0-487; L1747:0-380; L1749:0-714; L1749:715-1112; L1749:1113-2527; L1751:177-488; L1751:489-1648 | CAP-CMP-01; CAP-TEN-01; CAP-TMP-01; CFG-TER; ENUM-FundamentoUnicidade; ENUM-TipoContagemAgregada; RQ-CAP-08; RQ-DAD-05; RQ-DAD-30; RQ-DAD-35; RQ-DAD-36; RQ-GOV-03; RQ-GOV-21; RQ-GOV-22; RQ-ORQ-13; RQ-REP-14; S:4.4.7; V-01; V-07; V-14 |
| CAP-AGR-01 | saida | REPRESENTACAO | L1751:177-488 | L1744:206-1607; L1746:0-487; L1747:0-380; L1749:0-714; L1749:715-1112; L1749:1113-2527; L1751:177-488; L1751:489-1648 | CAP-CMP-01; CAP-TEN-01; CAP-TMP-01; CFG-TER; ENUM-FundamentoUnicidade; ENUM-TipoContagemAgregada; RQ-CAP-08; RQ-DAD-05; RQ-DAD-30; RQ-DAD-35; RQ-DAD-36; RQ-GOV-03; RQ-GOV-21; RQ-GOV-22; RQ-ORQ-13; RQ-REP-14; S:4.4.7; V-01; V-07; V-14 |
| CAP-AGR-01 | compatibilidade | PRECONDICAO | L1751:489-1648 | L1744:206-1607; L1746:0-487; L1747:0-380; L1749:0-714; L1749:715-1112; L1749:1113-2527; L1751:177-488; L1751:489-1648 | CAP-CMP-01; CAP-TEN-01; CAP-TMP-01; CFG-TER; ENUM-FundamentoUnicidade; ENUM-TipoContagemAgregada; RQ-CAP-08; RQ-DAD-05; RQ-DAD-30; RQ-DAD-35; RQ-DAD-36; RQ-GOV-03; RQ-GOV-21; RQ-GOV-22; RQ-ORQ-13; RQ-REP-14; S:4.4.7; V-01; V-07; V-14 |
| CAP-DIS-01 | definicao | IDENTIDADE | L1708:15-33 | — | — |
| CAP-DIS-01 | natureza | CAPACIDADE | L1708:36-42; L1708:45-59; L1708:62-103 | — | FAM-07 |
| CAP-DIS-01 | metodo | METODO | L1753:37-650 | =texto | CAP-DIS-02; CAP-SUB-02 |
| CAP-DIS-01 | proibicoes | LIMITACAO | L1753:651-707 | L1753:37-650 | CAP-DIS-02; CAP-SUB-02; CONCEPT:4.3.6 |
| CAP-DIS-02 | definicao | IDENTIDADE | L1709:15-43 | — | — |
| CAP-DIS-02 | natureza | CAPACIDADE | L1709:46-52; L1709:55-69; L1709:72-77 | — | FAM-07 |
| CAP-DIS-02 | parametros | OPERACIONAL | L1755:47-141 | L1755:142-690 | — |
| CAP-DIS-02 | metodo | METODO | L1755:142-690 | =texto | — |
| CAP-DIS-02 | saida | REPRESENTACAO | L1755:691-769 | L1755:142-690 | — |
| CAP-DIS-03 | definicao | IDENTIDADE | L1710:15-42 | — | — |
| CAP-DIS-03 | natureza | CAPACIDADE | L1710:45-51; L1710:54-68; L1710:71-76 | — | FAM-07 |
| CAP-DIS-03 | parametros | OPERACIONAL | L1757:46-223 | L1757:46-223; L1757:495-637 | CFG-MET |
| CAP-DIS-03 | metodo | METODO | L1757:224-396 | L1757:46-223; L1757:495-637 | CFG-MET |
| CAP-DIS-03 | representacao | REPRESENTACAO | L1757:397-494 | L1757:46-223; L1757:495-637 | CFG-MET |
| CAP-DIS-03 | saida | REPRESENTACAO | L1757:495-637 | L1757:46-223; L1757:495-637 | CFG-MET |
| CAP-CMP-01 | definicao | IDENTIDADE | L1711:15-37 | — | — |
| CAP-CMP-01 | natureza | CAPACIDADE | L1711:40-46; L1711:49-63; L1711:66-71 | — | FAM-04 |
| CAP-CMP-01 | metodo | METODO | L1759:41-2422 | L1759:41-2422; L1759:2423-3345; L1761:0-930 | CAP-AGR-01; CAP-IND-02; CAP-SUB-01; CAP-SUB-02; CAP-TMP-01; CFG-VOC; CONCEPT:4.3.7; ENUM-Avaliabilidade; MODELO:ContextoDeMedida; RQ-CAP-08; RQ-GOV-29; RQ-ORQ-13; RQ-REP-03 |
| CAP-CMP-01 | compatibilidade | PRECONDICAO | L1759:2423-3345 | L1759:41-2422; L1759:2423-3345; L1761:0-930 | CAP-AGR-01; CAP-IND-02; CAP-SUB-01; CAP-SUB-02; CAP-TMP-01; CFG-VOC; CONCEPT:4.3.7; ENUM-Avaliabilidade; MODELO:ContextoDeMedida; RQ-CAP-08; RQ-GOV-29; RQ-ORQ-13; RQ-REP-03 |
| CAP-CMP-01 | saida | REPRESENTACAO | L1763:0-554 | L1759:41-2422; L1759:2423-3345; L1761:0-930 | CAP-AGR-01; CAP-IND-02; CAP-SUB-01; CAP-SUB-02; CAP-TMP-01; CFG-VOC; CONCEPT:4.3.7; ENUM-Avaliabilidade; MODELO:ContextoDeMedida; RQ-CAP-08; RQ-GOV-29; RQ-ORQ-13; RQ-REP-03; RQ-RES-10; RQ-RES-11 |
| CAP-CMP-01 | avaliabilidade | AVALIABILIDADE | L1761:0-930 | L1759:41-2422; L1759:2423-3345; L1761:0-930 | CAP-AGR-01; CAP-IND-02; CAP-SUB-01; CAP-SUB-02; CAP-TMP-01; CFG-VOC; CONCEPT:4.3.7; ENUM-Avaliabilidade; MODELO:ContextoDeMedida; RQ-CAP-08; RQ-GOV-29; RQ-ORQ-13; RQ-REP-03 |
| CAP-TMP-01 | definicao | IDENTIDADE | L1712:15-31 | — | — |
| CAP-TMP-01 | natureza | CAPACIDADE | L1712:34-40; L1712:43-57; L1712:60-65 | — | FAM-08 |
| CAP-TMP-01 | entradas | DADOS | L1765:35-122 | L1765:35-122; L1765:123-765; L1765:766-1660 | CAP-AGR-01; CFG-TER; CONCEPT:4.3.9; RQ-CAP-08 |
| CAP-TMP-01 | saida | REPRESENTACAO | L1765:123-765 | L1765:35-122; L1765:123-765; L1765:766-1660 | CAP-AGR-01; CFG-TER; CONCEPT:4.3.9; RQ-CAP-08 |
| CAP-TMP-01 | precondicoes | PRECONDICAO | L1765:766-1660 | L1765:35-122; L1765:123-765; L1765:766-1660 | CAP-AGR-01; CFG-TER; CONCEPT:4.3.9; RQ-CAP-08 |
| CAP-TMP-01 | proibicoes | LIMITACAO | L1765:1661-1739 | L1765:35-122; L1765:123-765; L1765:766-1660 | CAP-AGR-01; CFG-TER; CONCEPT:4.3.9; RQ-CAP-08; RQ-ESC-12 |
| CAP-TEN-01 | definicao | IDENTIDADE | L1713:15-24 | — | — |
| CAP-TEN-01 | natureza | CAPACIDADE | L1713:27-33; L1713:36-50; L1713:53-58 | — | FAM-08 |
| CAP-TEN-01 | metodo | METODO | L1767:28-101; L1771:0-163; L1772:0-151; L1773:0-335; L1774:0-347 | L1769:0-215; L1770:0-795; L1771:0-163 | CAP-AGR-01; CFG-TER; RQ-CAP-08; RQ-DAD-05; S:5.2 |
| CAP-TEN-01 | precondicoes | PRECONDICAO | L1769:0-215 | L1769:0-215; L1770:0-795; L1771:0-163 | CAP-AGR-01; CFG-TER; RQ-CAP-08; RQ-DAD-05 |
| CAP-TEN-01 | avaliabilidade | AVALIABILIDADE | L1770:0-795 | L1769:0-215; L1770:0-795; L1771:0-163 | CAP-AGR-01; CFG-TER; RQ-CAP-08; RQ-DAD-05 |
| CAP-TEN-01 | saida | REPRESENTACAO | L1776:0-193 | L1769:0-215; L1770:0-795; L1771:0-163 | CAP-AGR-01; CFG-TER; RQ-CAP-08; RQ-DAD-05 |
| CAP-TEN-01 | proibicoes | LIMITACAO | L1776:194-330 | L1769:0-215; L1770:0-795; L1771:0-163 | CAP-AGR-01; CFG-TER; CONCEPT:4.3.10; RQ-CAP-08; RQ-DAD-05 |
| CAP-ROT-01 | definicao | IDENTIDADE | L1714:15-59 | — | — |
| CAP-ROT-01 | natureza | CAPACIDADE | L1714:62-68; L1714:71-85; L1714:88-93 | — | FAM-08 |
| CAP-ROT-01 | metodo | METODO | L1778:63-144; L1782:0-835; L1788:0-1229 | L1778:145-412; L1780:0-669; L1782:0-835; L1784:0-920; L1786:0-649; L1788:0-1229; L1790:0-647; L1792:0-597; L1794:0-547; L1796:0-400; L1800:0-593 | CAP-AGR-01; CAP-CMP-01; CAP-TEN-01; CAP-TMP-01; CFG-MET; CFG-VOC; ENUM-Desfecho; FAM-08; INV-04; RQ-CAP-03; RQ-CAP-08; RQ-DAD-35; RQ-GOV-14; RQ-GOV-28; RQ-ORQ-01; RQ-ORQ-13; RQ-PRV-10; RQ-RES-04; RQ-RES-06; RQ-RES-11; S:8.6; V-15 |
| CAP-ROT-01 | finalidade | FINALIDADE | L1778:145-412 | L1778:145-412; L1780:0-669; L1782:0-835; L1784:0-920; L1786:0-649; L1788:0-1229; L1790:0-647; L1792:0-597; L1794:0-547; L1796:0-400; L1800:0-593 | CAP-AGR-01; CAP-CMP-01; CAP-TEN-01; CAP-TMP-01; CFG-MET; CFG-VOC; ENUM-Desfecho; INV-04; RQ-CAP-03; RQ-CAP-08; RQ-DAD-35; RQ-GOV-14; RQ-GOV-28; RQ-ORQ-01; RQ-ORQ-13; RQ-PRV-10; RQ-RES-04; RQ-RES-06; RQ-RES-11; S:8.6; V-15 |
| CAP-ROT-01 | entradas | DADOS | L1780:0-669 | L1778:145-412; L1780:0-669; L1782:0-835; L1784:0-920; L1786:0-649; L1788:0-1229; L1790:0-647; L1792:0-597; L1794:0-547; L1796:0-400; L1800:0-593 | CAP-AGR-01; CAP-CMP-01; CAP-TEN-01; CAP-TMP-01; CFG-MET; CFG-VOC; ENUM-Desfecho; INV-04; RQ-CAP-03; RQ-CAP-08; RQ-DAD-35; RQ-GOV-14; RQ-GOV-28; RQ-ORQ-01; RQ-ORQ-13; RQ-PRV-10; RQ-RES-04; RQ-RES-06; RQ-RES-11; S:8.6; V-15 |
| CAP-ROT-01 | privacidade | PRIVACIDADE | L1784:0-920 | L1778:145-412; L1780:0-669; L1782:0-835; L1784:0-920; L1786:0-649; L1788:0-1229; L1790:0-647; L1792:0-597; L1794:0-547; L1796:0-400; L1800:0-593 | CAP-AGR-01; CAP-CMP-01; CAP-TEN-01; CAP-TMP-01; CFG-MET; CFG-VOC; ENUM-Desfecho; INV-04; RQ-CAP-03; RQ-CAP-08; RQ-DAD-35; RQ-GOV-14; RQ-GOV-28; RQ-ORQ-01; RQ-ORQ-13; RQ-PRV-10; RQ-RES-04; RQ-RES-06; RQ-RES-11; S:8.6; V-15 |
| CAP-ROT-01 | avaliabilidade | AVALIABILIDADE | L1786:0-649; L1800:0-593 | L1778:145-412; L1780:0-669; L1782:0-835; L1784:0-920; L1786:0-649; L1788:0-1229; L1790:0-647; L1792:0-597; L1794:0-547; L1796:0-400; L1800:0-593 | CAP-AGR-01; CAP-CMP-01; CAP-TEN-01; CAP-TMP-01; CFG-MET; CFG-VOC; ENUM-Desfecho; INV-04; RQ-CAP-03; RQ-CAP-08; RQ-DAD-35; RQ-GOV-14; RQ-GOV-28; RQ-ORQ-01; RQ-ORQ-13; RQ-PRV-10; RQ-RES-04; RQ-RES-06; RQ-RES-11; S:8.6; V-15 |
| CAP-ROT-01 | saida | REPRESENTACAO | L1790:0-647; L1800:0-593 | L1778:145-412; L1780:0-669; L1782:0-835; L1784:0-920; L1786:0-649; L1788:0-1229; L1790:0-647; L1792:0-597; L1794:0-547; L1796:0-400; L1800:0-593 | CAP-AGR-01; CAP-CMP-01; CAP-TEN-01; CAP-TMP-01; CFG-MET; CFG-VOC; ENUM-Desfecho; INV-04; RQ-CAP-03; RQ-CAP-08; RQ-DAD-35; RQ-GOV-14; RQ-GOV-28; RQ-ORQ-01; RQ-ORQ-13; RQ-PRV-10; RQ-RES-04; RQ-RES-06; RQ-RES-11; S:8.6; V-15 |
| CAP-ROT-01 | representacao | REPRESENTACAO | L1792:0-597; L1794:0-547 | L1778:145-412; L1780:0-669; L1782:0-835; L1784:0-920; L1786:0-649; L1788:0-1229; L1790:0-647; L1792:0-597; L1794:0-547; L1796:0-400; L1800:0-593 | CAP-AGR-01; CAP-CMP-01; CAP-TEN-01; CAP-TMP-01; CFG-MET; CFG-VOC; ENUM-Desfecho; INV-04; RQ-CAP-03; RQ-CAP-08; RQ-DAD-35; RQ-GOV-14; RQ-GOV-28; RQ-ORQ-01; RQ-ORQ-13; RQ-PRV-10; RQ-RES-04; RQ-RES-06; RQ-RES-11; S:8.6; V-15 |
| CAP-ROT-01 | compatibilidade | PRECONDICAO | L1796:0-400 | L1778:145-412; L1780:0-669; L1782:0-835; L1784:0-920; L1786:0-649; L1788:0-1229; L1790:0-647; L1792:0-597; L1794:0-547; L1796:0-400; L1800:0-593 | CAP-AGR-01; CAP-CMP-01; CAP-TEN-01; CAP-TMP-01; CFG-MET; CFG-VOC; ENUM-Desfecho; INV-04; RQ-CAP-03; RQ-CAP-08; RQ-DAD-35; RQ-GOV-14; RQ-GOV-28; RQ-ORQ-01; RQ-ORQ-13; RQ-PRV-10; RQ-RES-04; RQ-RES-06; RQ-RES-11; S:8.6; V-15 |
| CAP-ROT-01 | limitacoes | LIMITACAO | L1798:0-375 | L1778:145-412; L1780:0-669; L1782:0-835; L1784:0-920; L1786:0-649; L1788:0-1229; L1790:0-647; L1792:0-597; L1794:0-547; L1796:0-400; L1800:0-593 | CAP-AGR-01; CAP-CMP-01; CAP-TEN-01; CAP-TMP-01; CFG-MET; CFG-VOC; ENUM-Desfecho; INV-04; RQ-CAP-03; RQ-CAP-08; RQ-DAD-35; RQ-GOV-14; RQ-GOV-28; RQ-ORQ-01; RQ-ORQ-13; RQ-PRV-10; RQ-RES-04; RQ-RES-06; RQ-RES-11; S:8.6; V-15 |
| CAP-ROT-01 | proibicoes | LIMITACAO | L1798:376-616 | L1778:145-412; L1780:0-669; L1782:0-835; L1784:0-920; L1786:0-649; L1788:0-1229; L1790:0-647; L1792:0-597; L1794:0-547; L1796:0-400; L1800:0-593 | CAP-AGR-01; CAP-CMP-01; CAP-TEN-01; CAP-TMP-01; CFG-MET; CFG-VOC; ENUM-Desfecho; INV-04; RQ-CAP-03; RQ-CAP-08; RQ-DAD-35; RQ-GOV-14; RQ-GOV-28; RQ-ORQ-01; RQ-ORQ-13; RQ-PRV-10; RQ-RES-04; RQ-RES-06; RQ-RES-11; S:20.7; S:8.6; V-15 |
| CAP-ROT-01 | precondicoes | PRECONDICAO | L1780:0-669 | L1778:145-412; L1780:0-669; L1782:0-835; L1784:0-920; L1786:0-649; L1788:0-1229; L1790:0-647; L1792:0-597; L1794:0-547; L1796:0-400; L1800:0-593 | CAP-AGR-01; CAP-CMP-01; CAP-TEN-01; CAP-TMP-01; CFG-MET; CFG-VOC; ENUM-Desfecho; INV-04; RQ-CAP-03; RQ-CAP-08; RQ-DAD-35; RQ-GOV-14; RQ-GOV-28; RQ-ORQ-01; RQ-ORQ-13; RQ-PRV-10; RQ-RES-04; RQ-RES-06; RQ-RES-11; S:8.6; V-15 |
| CAP-ROT-01 | parametros | OPERACIONAL | L1780:0-669 | L1778:145-412; L1780:0-669; L1782:0-835; L1784:0-920; L1786:0-649; L1788:0-1229; L1790:0-647; L1792:0-597; L1794:0-547; L1796:0-400; L1800:0-593 | CAP-AGR-01; CAP-CMP-01; CAP-TEN-01; CAP-TMP-01; CFG-MET; CFG-VOC; ENUM-Desfecho; INV-04; RQ-CAP-03; RQ-CAP-08; RQ-DAD-35; RQ-GOV-14; RQ-GOV-28; RQ-ORQ-01; RQ-ORQ-13; RQ-PRV-10; RQ-RES-04; RQ-RES-06; RQ-RES-11; S:8.6; V-15 |
| CAP-REF-01 | definicao | IDENTIDADE | L1715:15-39 | — | — |
| CAP-REF-01 | natureza | CAPACIDADE | L1715:42-48; L1715:51-65; L1715:68-73 | — | FAM-09 |
| CAP-REF-01 | entradas | DADOS | L1802:43-379 | L1802:43-379; L1802:440-792 | AMB-02; CAP-SUB-01; CFG-REF; CFG-VOC; CONCEPT:4.3.11; S:4.4.8 |
| CAP-REF-01 | saida | REPRESENTACAO | L1802:380-439 | L1802:43-379; L1802:440-792 | AMB-02; CAP-SUB-01; CFG-REF; CFG-VOC; CONCEPT:4.3.11; S:4.4.8 |
| CAP-REF-01 | proibicoes | LIMITACAO | L1802:440-792 | L1802:43-379; L1802:440-792 | AMB-02; CAP-SUB-01; CFG-REF; CFG-VOC; CONCEPT:4.3.11; S:4.4.8 |
| CAP-ESP-01 | definicao | IDENTIDADE | L1716:15-24 | — | — |
| CAP-ESP-01 | natureza | CAPACIDADE | L1716:27-33; L1716:36-50; L1716:53-58 | — | FAM-10 |
| CAP-ESP-01 | metodo | METODO | L1804:28-1111 | =texto | CFG-MET; CONCEPT:4.3.12; RQ-DAD-25; RQ-DAD-26; RQ-DAD-27; S:4.4.5; TPL-11 |
| CAP-ESP-02 | definicao | IDENTIDADE | L1717:15-38 | — | — |
| CAP-ESP-02 | natureza | CAPACIDADE | L1717:41-47; L1717:50-64; L1717:67-72 | — | FAM-10 |
| CAP-ESP-02 | metodo | METODO | L1806:42-228; L1808:0-643; L1810:0-497 | L1806:42-228; L1806:229-445; L1806:446-1221; L1808:0-643; L1810:0-497 | CAP-ESP-01; CAP-REF-01; RQ-CAP-08; RQ-RES-11; V-06 |
| CAP-ESP-02 | saida | REPRESENTACAO | L1806:229-445 | L1806:42-228; L1806:229-445; L1806:446-1221; L1808:0-643; L1810:0-497 | CAP-ESP-01; CAP-REF-01; RQ-CAP-08; RQ-RES-11; V-06 |
| CAP-ESP-02 | avaliabilidade | AVALIABILIDADE | L1806:446-1221 | L1806:42-228; L1806:229-445; L1806:446-1221; L1808:0-643; L1810:0-497 | CAP-ESP-01; CAP-REF-01; RQ-CAP-08; RQ-RES-11; V-06 |
| CAP-ESP-03 | definicao | IDENTIDADE | L1718:15-34 | — | — |
| CAP-ESP-03 | natureza | CAPACIDADE | L1718:37-43; L1718:46-60; L1718:63-68 | — | FAM-10 |
| CAP-ESP-03 | metodo | METODO | L1812:38-294 | =texto | CAP-DIS-03; CAP-ESP-01; CAP-ESP-02 |
| CAP-SUB-01 | definicao | IDENTIDADE | L1719:15-39 | — | — |
| CAP-SUB-01 | natureza | CAPACIDADE | L1719:42-48; L1719:51-65; L1719:68-73 | — | FAM-11 |
| CAP-SUB-01 | metodo | METODO | L1814:43-1130; L1816:0-598; L1818:0-579 | L1814:43-1130; L1816:0-598; L1818:0-579; L1820:0-1461 | CAP-CMP-01; CAP-ESP-02; CFG-VOC; ENUM-Avaliabilidade; ENUM-Desfecho; MODELO:CausaOrigem; MODELO:ContextoDeMedida; MODELO:RefSaidaEsperada; RQ-CAP-08; RQ-GOV-31; RQ-RES-01; S:4.4.9 |
| CAP-SUB-01 | proibicoes | LIMITACAO | L1818:580-891 | L1814:43-1130; L1816:0-598; L1818:0-579; L1820:0-1461 | CAP-CMP-01; CAP-ESP-02; CFG-VOC; CONCEPT:4.3.13; ENUM-Avaliabilidade; ENUM-Desfecho; MODELO:CausaOrigem; MODELO:ContextoDeMedida; MODELO:RefSaidaEsperada; RQ-CAP-08; RQ-GOV-31; RQ-RES-01; S:4.4.9 |
| CAP-SUB-01 | avaliabilidade | AVALIABILIDADE | L1820:0-1461 | L1814:43-1130; L1816:0-598; L1818:0-579; L1820:0-1461 | CAP-CMP-01; CAP-ESP-02; CFG-VOC; ENUM-Avaliabilidade; ENUM-Desfecho; MODELO:CausaOrigem; MODELO:ContextoDeMedida; MODELO:RefSaidaEsperada; RQ-CAP-08; RQ-GOV-31; RQ-RES-01; S:4.4.9 |
| CAP-SUB-01 | saida | REPRESENTACAO | L1822:0-596 | L1814:43-1130; L1816:0-598; L1818:0-579; L1820:0-1461 | CAP-CMP-01; CAP-ESP-02; CFG-DOC; CFG-VOC; ENUM-Avaliabilidade; ENUM-CondicaoCriterio; ENUM-Desfecho; MODELO:CausaOrigem; MODELO:ContextoDeMedida; MODELO:RefSaidaEsperada; RQ-CAP-08; RQ-GOV-31; RQ-RES-01; RQ-RES-10; RQ-SIN-10; S:4.4.9 |
| CAP-SUB-02 | definicao | IDENTIDADE | L1720:15-24 | — | — |
| CAP-SUB-02 | natureza | CAPACIDADE | L1720:27-33; L1720:36-50; L1720:53-58 | — | FAM-11 |
| CAP-SUB-02 | parametros | OPERACIONAL | L1824:28-468 | =texto | CAP-ESP-02 |
| CAP-SUB-03 | definicao | IDENTIDADE | L1721:15-34 | — | — |
| CAP-SUB-03 | natureza | CAPACIDADE | L1721:37-43; L1721:46-60; L1721:63-68 | — | FAM-11 |
| CAP-SUB-03 | parametros | OPERACIONAL | L1826:38-560 | =texto | CFG-MET |
| CAP-REP-01 | definicao | IDENTIDADE | L1722:15-21 | — | — |
| CAP-REP-01 | natureza | CAPACIDADE | L1722:24-30; L1722:33-45; L1722:48-53 | — | FAM-13 |
| CAP-REP-01 | representacao | REPRESENTACAO | L1828:46-130 | L1828:131-208 | PARTE:13 |
| CAP-REP-01 | entradas | DADOS | L1828:131-208 | =texto | PARTE:13 |
| CAP-REP-02 | definicao | IDENTIDADE | L1723:15-68 | — | — |
| CAP-REP-02 | natureza | CAPACIDADE | L1723:71-77; L1723:80-92; L1723:95-100 | — | FAM-13 |
| CAP-REP-02 | representacao | REPRESENTACAO | L1828:46-130 | L1828:131-208 | PARTE:13 |
| CAP-REP-02 | entradas | DADOS | L1828:131-208 | =texto | PARTE:13 |
| CAP-REP-03 | definicao | IDENTIDADE | L1724:15-19 | — | — |
| CAP-REP-03 | natureza | CAPACIDADE | L1724:22-28; L1724:31-43; L1724:46-83 | L1724:46-83 | FAM-13 |
| CAP-REP-03 | representacao | REPRESENTACAO | L1828:46-130 | L1828:131-208 | PARTE:13 |
| CAP-REP-03 | entradas | DADOS | L1828:131-208 | =texto | PARTE:13 |
| CAP-REP-04 | definicao | IDENTIDADE | L1725:15-29 | — | — |
| CAP-REP-04 | natureza | CAPACIDADE | L1725:32-38; L1725:41-53; L1725:56-107 | — | CAP-REP-01; CAP-REP-02; CAP-REP-03; FAM-13 |
| CAP-REP-04 | representacao | REPRESENTACAO | L1828:46-130 | L1828:131-208 | PARTE:13 |
| CAP-REP-04 | entradas | DADOS | L1828:131-208 | =texto | PARTE:13 |
| CAP-REP-05 | definicao | IDENTIDADE | L1726:15-58 | — | — |
| CAP-REP-05 | natureza | CAPACIDADE | L1726:61-67; L1726:70-82; L1726:85-90 | — | FAM-13 |
| CAP-REP-05 | representacao | REPRESENTACAO | L1830:62-420 | — | RQ-REP-12 |
| CAP-REP-06 | definicao | IDENTIDADE | L1727:15-37 | — | — |
| CAP-REP-06 | natureza | CAPACIDADE | L1727:40-46; L1727:49-61; L1727:64-69 | — | FAM-13 |
| CAP-REP-06 | representacao | REPRESENTACAO | L1832:41-273 | — | RQ-REP-12 |
| CAP-SIN-01 | definicao | IDENTIDADE | L1728:15-32 | — | — |
| CAP-SIN-01 | natureza | CAPACIDADE | L1728:35-41; L1728:44-61; L1728:64-69 | — | FAM-14 |
| CAP-SIN-01 | representacao | REPRESENTACAO | L1834:36-74 | — | C-12; PARTE:14 |
| CFG-DOM | — | IDENTIDADE | L871:0-848; L872:0-1716; L873:0-726; L874:0-594; L875:0-248; L877:0-68; L879:0-42; L881:0-166; L882:0-102; L883:0-166; L884:0-117; L885:0-174; L886:0-165; L887:0-237; L888:0-95; L889:0-133; L890:0-159; L891:0-114; L892:0-212; L893:0-158; L894:0-172; L895:0-115; L897:0-115; L899:0-42; L901:0-120; L902:0-192; L903:0-143; L905:0-629; L907:0-282; L918:0-830 | L871:0-848; L872:0-1716; L873:0-726; L875:0-248; L897:0-115; L905:0-629; L907:0-282; L918:0-830 | C-04; CFG-PRV; CFG-TER; CFG-VOC; CONCEPT:3.1; RQ-CFG-01; RQ-CFG-05; RQ-CFG-08; RQ-CFG-09; RQ-CFG-10; RQ-CFG-11; RQ-CFG-13; RQ-DAD-19; RQ-ESC-01; RQ-ESC-04; RQ-ESC-05; RQ-FLX-20; S:4.3 |
| CFG-FAM | — | CAPACIDADE | L922:0-206 | — | CAP-ROT-01; FAM-01; FAM-02; FAM-03; FAM-04; FAM-05; FAM-06; FAM-07; FAM-08; FAM-09; FAM-10; FAM-11; FAM-12; FAM-13; FAM-14; S:1.3 |
| CFG-EXC | — | LIMITACAO | L926:0-241; L928:0-33; L930:0-323; L931:0-321; L932:0-250; L933:0-308; L934:0-267; L935:0-268; L936:0-250; L937:0-212; L938:0-335; L939:0-212; L941:0-1097 | L941:0-1097 | C-04; EXC-01; EXC-02; EXC-03; EXC-04; EXC-05; EXC-06; EXC-07; EXC-08; EXC-09; EXC-10; EXC-11; RQ-ESC-13; RQ-GOV-08; RQ-GOV-09; S:1.4 |
| CFG-CAP | — | CAPACIDADE | L945:0-152 | — | CAP-ROT-01; PARTE:8; RQ-CAP-10 |
| CFG-MET | metodo | METODO | L949:0-642; L951:0-1817 | L951:0-1817; L953:0-342 | C-04; CAP-AGR-01; CAP-CMP-01; CAP-DIS-01; CAP-DIS-02; CAP-DIS-03; CAP-ESP-01; CAP-ESP-03; CAP-ROT-01; CAP-SUB-01; CAP-SUB-02; CAP-SUB-03; CAP-TEN-01; CAP-TMP-01; CFG-AUS; PARTE:8; RQ-CAP-13; RQ-DAD-26; RQ-DAD-27; RQ-DOC-06 |
| CFG-MET | limitacoes | LIMITACAO | L953:0-342 | L951:0-1817; L953:0-342 | C-04; CAP-DIS-01; CAP-DIS-03; CAP-ESP-01; CAP-ESP-03; CAP-SUB-03; CFG-AUS; RQ-DAD-26; RQ-DAD-27; RQ-DOC-06 |
| CFG-IND | definicao | IDENTIDADE | L957:0-50; L959:0-207; L960:0-404; L961:0-220; L962:0-154 | L960:0-404; L962:0-154; L964:0-416 | CAP-AGR-01; CAP-IND-01; CAP-IND-02; CAP-ROT-01; RQ-DAD-18; RQ-DAD-35; RQ-DAD-36; S:8.6 |
| CFG-IND | precondicoes | PRECONDICAO | L964:0-416 | L960:0-404; L962:0-154; L964:0-416 | CAP-AGR-01; CAP-IND-02; CAP-ROT-01; RQ-DAD-36; S:8.6 |
| CFG-TER | — | GOVERNANCA | L968:0-1758 | =texto | CAP-AGR-01; CAP-TEN-01; CAP-TMP-01; ENUM-StatusSignificado; RQ-CAP-08; RQ-DAD-05; RQ-DAD-06; RQ-DAD-30; RQ-DAD-35; RQ-DAD-38 |
| CFG-REF | — | DADOS | L972:0-332 | — | CAP-REF-01; CAP-SUB-01 |
| CFG-VOC | — | OPERACIONAL | L976:0-353; L978:0-36; L980:0-275; L981:0-108; L982:0-107; L983:0-180; L984:0-121; L985:0-381; L986:0-68; L987:0-173; L988:0-173; L989:0-174; L990:0-335; L992:0-66; L994:0-54; L996:0-74; L997:0-60; L998:0-61; L999:0-70; L1000:0-68; L1001:0-62; L1002:0-81; L1003:0-85; L1004:0-88; L1005:0-91; L1006:0-84; L1008:0-882; L1010:0-1294; L1012:0-364; L1014:0-151; L1016:0-598; L1018:0-374; L1020:0-999 | =texto | AMB-04; CAP-AGR-01; CAP-CMP-01; CAP-ROT-01; CAP-SUB-01; CAP-SUB-02; CAP-SUB-03; CFG-AMB; CFG-CAP; CFG-IND; CFG-LEX; CFG-PRV; RQ-CFG-14; RQ-CFG-15; RQ-DAD-20; RQ-DAD-25; RQ-DAD-29; RQ-DAD-33; RQ-DAD-38; RQ-DAD-41; RQ-FLX-20; RQ-GOV-17; RQ-GOV-20; S:4.3; S:4.4.15 |
| CFG-AMB | — | PRECONDICAO | L1024:0-115; L1026:0-27; L1028:0-89; L1029:0-47; L1030:0-175; L1031:0-93; L1032:0-114; L1033:0-116 | — | AMB-01; AMB-02; AMB-03; AMB-04; AMB-05; AMB-06; CFG-VOC; RQ-GOV-18; S:7.5 |
| CFG-OPC | — | OPERACIONAL | L1037:0-599; L1039:0-1214; L1041:0-67; L1043:0-125; L1044:0-116; L1045:0-126; L1046:0-176; L1047:0-102; L1048:0-176; L1049:0-110; L1050:0-124; L1051:0-137; L1052:0-136; L1053:0-110; L1054:0-112; L1055:0-139; L1056:0-123; L1057:0-113; L1058:0-147; L1059:0-155; L1060:0-293 | =texto | AMB-01; AMB-02; AMB-03; AMB-04; AMB-05; C-02; C-11; CAP-CMP-01; CFG-AMB; CFG-DOC; CFG-IND; CFG-PRV; CFG-TPL; CFG-VOC; ENUM-DimensaoRecorte; ENUM-ModoTerritorial; FN-INT-03; MODELO:ConjuntoOpcoesAutorizadas; MODELO:InterpretacaoAlternativa; MODELO:OpcaoAutorizada; MODELO:RefEscopo; RQ-CFG-06; RQ-DAD-10; RQ-DAD-22; RQ-DAD-43; RQ-FLX-10; RQ-GOV-17; RQ-GOV-18; RQ-LIN-02; RQ-LIN-12; RQ-ORQ-11; S:3.2; S:4.4.22; TPL-04 |
| CFG-PRE | — | GOVERNANCA | L1064:0-377 | =texto | RQ-GOV-21 |
| CFG-AUS | — | AVALIABILIDADE | L1068:0-476 | =texto | INV-04; RQ-DAD-07; RQ-GOV-22; S:8.6 |
| CFG-REP | — | REPRESENTACAO | L1072:0-767 | =texto | PARTE:13; RQ-REP-05; RQ-REP-15; RQ-RES-11 |
| CFG-LEX | — | OPERACIONAL | L1076:0-38; L1078:0-295; L1079:0-193; L1080:0-213; L1081:0-182; L1082:0-269; L1083:0-155; L1084:0-111; L1086:0-831 | L1083:0-155; L1086:0-831 | CFG-VOC; RQ-SIN-06; RQ-SIN-10; S:4.4.9; V-03; V-04; V-05; V-06; V-07; V-12; V-13 |
| CFG-TPL | — | REPRESENTACAO | L1090:0-154; L1094:2-8; L1094:11-42; L1094:45-313; L1095:2-8; L1095:11-46; L1095:49-190; L1096:2-8; L1096:11-37; L1096:40-157; L1097:2-8; L1097:11-53; L1097:56-269; L1098:2-8; L1098:11-17; L1098:20-148; L1099:2-8; L1099:11-17; L1099:20-150; L1100:2-8; L1100:11-17; L1100:20-209; L1101:2-8; L1101:11-44; L1101:47-194; L1102:2-8; L1102:11-43; L1102:46-348; L1103:2-8; L1103:11-40; L1103:43-436; L1104:2-8; L1104:11-37; L1104:40-163; L1105:2-8; L1105:11-76; L1105:79-303; L1106:2-8; L1106:11-73; L1106:76-344; L1108:0-2942 | =texto | CFG-DOC; CFG-OPC; CFG-PRV; MODELO:ConjuntoOpcoesAutorizadas; MODELO:OpcaoAutorizada; MODELO:RefEscopo; RQ-DAD-22; RQ-DAD-43; RQ-DEG-02; RQ-DEG-04; RQ-DEG-06; RQ-FLX-17; RQ-FLX-19; RQ-GOV-19; RQ-ORQ-14; RQ-RES-04; RQ-SIN-05; S:4.4.11; S:4.4.22; S:4.4.23.6; TPL-01; TPL-02; TPL-03; TPL-04; TPL-05; TPL-06; TPL-07; TPL-08; TPL-09; TPL-10; TPL-11; TPL-12; TPL-13; V-06; V-16 |
| CFG-REC | — | OPERACIONAL | L1112:0-363 | =texto | RQ-LIN-15 |
| CFG-ESC | — | GOVERNANCA | L1116:0-1443 | =texto | MODELO:EscopoSolicitacao; RQ-FLX-02; RQ-FLX-16; RQ-LIN-07; RQ-LIN-19; RQ-LIN-21 |
| CFG-NOR | — | PRECONDICAO | L1120:0-467 | =texto | RQ-GOV-31; V-03 |
| CFG-LIM | — | LIMITACAO | L1124:0-761 | =texto | RQ-RES-06 |
| CFG-FON | — | DADOS | L1128:0-1174 | =texto | ENUM-PapelPlanilha; RQ-DAD-30; RQ-DAD-43; TPL-13 |
| CFG-PRV | privacidade | PRIVACIDADE | L1132:0-1714; L1134:0-33; L1136:0-19; L1137:0-34; L1138:0-70; L1139:0-19; L1140:0-25; L1141:0-19; L1142:0-87; L1143:0-122; L1144:0-127; L1145:0-96; L1146:0-77; L1147:0-50; L1148:0-80; L1150:0-134; L1152:0-877; L1159:0-976 | L1152:0-877; L1159:0-976 | C-02; C-10; CFG-VOC; MODELO:CampoProtegido; RQ-CFG-14; RQ-DAD-20; RQ-DAD-33; RQ-DAD-37; RQ-DAD-38; RQ-DAD-39; RQ-PRV-09; RQ-REP-13; TPL-04 |
| CFG-PRV | comportamento | OPERACIONAL | L1154:0-140; L1156:0-414 | L1152:0-877; L1159:0-976 | C-02; C-10; CFG-VOC; MODELO:CampoProtegido; RQ-DAD-20; RQ-DAD-33; RQ-DAD-38; RQ-DAD-39; RQ-PRV-09; RQ-REP-13; TPL-04 |
| CFG-DOC | definicao | IDENTIDADE | L1168:0-20; L1169:0-78; L1170:0-69; L1171:0-103; L1172:0-95; L1173:0-60; L1174:0-49; L1175:0-129; L1176:0-128; L1177:0-80; L1178:0-97; L1179:0-88; L1180:0-120; L1182:0-17; L1183:0-61; L1184:0-15; L1185:0-166; L1186:0-78; L1187:0-185; L1188:0-125; L1190:0-13; L1191:0-29; L1192:0-22; L1193:0-37; L1194:0-70; L1195:0-114; L1197:0-20; L1198:0-65; L1199:0-105; L1201:0-19; L1202:0-67; L1203:0-113; L1206:0-552; L1208:0-689; L1210:0-715; L1214:0-33; L1216:0-237; L1217:0-39; L1218:0-183; L1220:0-1557; L1222:0-834; L1224:0-461 | =texto | CAP-AGR-01; CAP-REP-01; CAP-REP-02; CAP-REP-03; CAP-REP-04; CAP-ROT-01; CFG-PRV; CFG-TPL; ENUM-CaminhoProposicaoDocumental; ENUM-Idioma; ENUM-IdiomaProposicaoDocumental; ENUM-TipoProposicaoDocumental; INV-16; MODELO:Ancora; RQ-DAD-07; RQ-RES-06; S:0.7; S:1.3; S:1.4; S:1.7; S:14.2; S:15.1; S:3.1; S:4.4.11; S:4.4.16 |
| CFG-DOC | metodo | METODO | L1228:0-584; L1230:0-863; L1232:0-1293; L1234:0-349; L1238:0-153; L1239:0-124; L1240:0-232; L1241:0-162; L1242:0-125; L1243:0-78; L1244:0-91; L1245:0-154; L1246:0-174; L1247:0-577; L1248:0-126; L1249:0-127; L1251:0-349 | =texto | C-09; RQ-CFG-05; RQ-SIN-10; S:2.2; S:3.2; V-16 |
| CFG-DOC | comportamento | OPERACIONAL | L1255:0-474; L1257:0-1680; L1259:0-758; L1261:0-1216; L1263:0-298 | =texto | C-02; C-04; C-11; EV-REPRESENTACAO; FN-INT-03; RQ-RAS-05; RQ-REP-01; RQ-SIN-05; S:4.4.23.6; TPL-04; TPL-08; TPL-12; V-16 |
| CFG-OPR | — | OPERACIONAL | L1308:0-2265 | =texto | ENUM-TipoInteracaoUsuario; EV-INTERACAO_USUARIO; RQ-FLX-17; RQ-GOV-23; RQ-ORQ-14; TPL-01; TPL-02; TPL-03 |
| DESFECHO-ADM-NP | — | DESFECHO | L2066:11-19; L2066:22-47; L2066:50-124 | L2066:22-47 | — |
| DESFECHO-ADM-FE | — | DESFECHO | L2067:11-19; L2067:22-54; L2067:57-133 | L2067:22-54 | — |
| DESFECHO-ADM-SC | — | DESFECHO | L2068:11-19; L2068:22-166; L2068:169-240 | L2068:22-166 | — |
| DESFECHO-BLQ-INF | — | DESFECHO | L2069:12-20; L2069:23-60; L2069:63-131 | L2069:23-60 | — |
| DESFECHO-BLQ-DEC | — | DESFECHO | L2070:12-20; L2070:23-80; L2070:83-103 | L2070:23-80 | — |
| DESFECHO-BLQ-DAD | — | DESFECHO | L2071:12-20; L2071:23-170; L2071:173-245 | L2071:23-170 | RQ-CAP-08 |
| DESFECHO-BLQ-SIG | — | DESFECHO | L2072:12-20; L2072:23-61; L2072:64-104 | L2072:23-61 | — |
| DESFECHO-BLQ-MET | — | DESFECHO | L2073:12-20; L2073:23-154; L2073:157-226 | L2073:23-154 | — |
| DESFECHO-BLQ-DEP | — | DESFECHO | L2074:12-20; L2074:23-58; L2074:61-86 | L2074:23-58 | — |
| DESFECHO-OPR-FAL | — | DESFECHO | L2075:12-23; L2075:26-115; L2075:118-133 | L2075:26-115 | — |
| DESFECHO-OPR-IND | — | DESFECHO | L2076:12-23; L2076:26-197; L2076:200-327 | L2076:26-197 | RQ-DEG-04 |
| DESFECHO-RES-VAL | — | DESFECHO | L2077:12-21; L2077:24-40; L2077:43-44 | L2077:24-40 | — |
| DESFECHO-RES-LIM | — | DESFECHO | L2078:12-21; L2078:24-55; L2078:58-68 | L2078:24-55 | — |
| DESFECHO-RES-SCL | — | DESFECHO | L2079:12-21; L2079:24-67; L2079:70-109 | L2079:24-67 | — |
| DESFECHO-RES-VAZ | — | DESFECHO | L2080:12-21; L2080:24-64; L2080:67-98 | L2080:24-64 | — |
| LIMITACAO-COBERTURA_PARCIAL | — | LIMITACAO | L1924:18-1381 | =texto | CONCEPT:9.8; ENUM-CategoriaLimitacao; RQ-DAD-43; RQ-RES-04; TPL-13 |
| LIMITACAO-UNIDADES_NAO_AVALIAVEIS | — | LIMITACAO | L1924:18-1381 | =texto | CONCEPT:9.8; ENUM-CategoriaLimitacao; RQ-DAD-43; RQ-RES-04; TPL-13 |
| LIMITACAO-UNIVERSO_OBSERVADO_NAO_EXAUSTIVO | — | LIMITACAO | L1924:18-1381 | =texto | CONCEPT:9.8; ENUM-CategoriaLimitacao; RQ-DAD-43; RQ-RES-04; TPL-13 |
| LIMITACAO-AGREGADO_PARCIAL | — | LIMITACAO | L1924:18-1381 | =texto | CONCEPT:9.8; ENUM-CategoriaLimitacao; RQ-DAD-43; RQ-RES-04; TPL-13 |
| LIMITACAO-SOMA_COM_POSSIVEL_DUPLA_CONTAGEM | — | LIMITACAO | L1924:18-1381 | =texto | CONCEPT:9.8; ENUM-CategoriaLimitacao; RQ-DAD-43; RQ-RES-04; TPL-13 |
| LIMITACAO-ADITIVIDADE_POR_PREMISSA_DO_USUARIO | — | LIMITACAO | L1924:18-1381 | =texto | CONCEPT:9.8; ENUM-CategoriaLimitacao; RQ-DAD-43; RQ-RES-04; TPL-13 |
| LIMITACAO-COMPARABILIDADE | — | LIMITACAO | L1924:18-1381 | =texto | CONCEPT:9.8; ENUM-CategoriaLimitacao; RQ-DAD-43; RQ-RES-04; TPL-13 |
| LIMITACAO-NIVEIS_TERRITORIAIS_DIFERENTES | — | LIMITACAO | L1924:18-1381 | =texto | CONCEPT:9.8; ENUM-CategoriaLimitacao; RQ-DAD-43; RQ-RES-04; TPL-13 |
| LIMITACAO-COBERTURA_DESIGUAL_ENTRE_PERIODOS | — | LIMITACAO | L1924:18-1381 | =texto | CONCEPT:9.8; ENUM-CategoriaLimitacao; RQ-DAD-43; RQ-RES-04; TPL-13 |
| LIMITACAO-CATEGORIAS_NAO_COMPARAVEIS | — | LIMITACAO | L1924:18-1381 | =texto | CONCEPT:9.8; ENUM-CategoriaLimitacao; RQ-DAD-43; RQ-RES-04; TPL-13 |
| LIMITACAO-DIFERENCA_DE_DEFINICAO | — | LIMITACAO | L1924:18-1381 | =texto | CONCEPT:9.8; ENUM-CategoriaLimitacao; RQ-DAD-43; RQ-RES-04; TPL-13 |
| LIMITACAO-VALOR_FORNECIDO_PELO_USUARIO | — | LIMITACAO | L1924:18-1381 | =texto | CONCEPT:9.8; ENUM-CategoriaLimitacao; RQ-DAD-43; RQ-RES-04; TPL-13 |
| LIMITACAO-VALOR_SUBSTITUIDO_PELO_USUARIO | — | LIMITACAO | L1924:18-1381 | =texto | CONCEPT:9.8; ENUM-CategoriaLimitacao; RQ-DAD-43; RQ-RES-04; TPL-13 |
| LIMITACAO-DENOMINADOR_ALTERNATIVO | — | LIMITACAO | L1924:18-1381 | =texto | CONCEPT:9.8; ENUM-CategoriaLimitacao; RQ-DAD-43; RQ-RES-04; TPL-13 |
| LIMITACAO-CRITERIO_NORMATIVO_DO_USUARIO | — | LIMITACAO | L1924:18-1381 | =texto | CONCEPT:9.8; ENUM-CategoriaLimitacao; RQ-DAD-43; RQ-RES-04; TPL-13 |
| LIMITACAO-DISTANCIA_GEODESICA_DIRETA | — | LIMITACAO | L1924:18-1381 | =texto | CONCEPT:9.8; ENUM-CategoriaLimitacao; RQ-DAD-43; RQ-RES-04; TPL-13 |
| LIMITACAO-EMPATE_NO_CORTE | — | LIMITACAO | L1924:18-1381 | =texto | CONCEPT:9.8; ENUM-CategoriaLimitacao; RQ-DAD-43; RQ-RES-04; TPL-13 |
| LIMITACAO-CONJUNTO_VAZIO_ANTERIOR | — | LIMITACAO | L1924:18-1381 | =texto | CONCEPT:9.8; ENUM-CategoriaLimitacao; RQ-DAD-43; RQ-RES-04; TPL-13 |
| LIMITACAO-ORIGEM_INDISPONIVEL | — | LIMITACAO | L1924:18-1381 | =texto | CONCEPT:9.8; ENUM-CategoriaLimitacao; RQ-DAD-43; RQ-RES-04; TPL-13 |
| ENUM-DisposicaoSinalExclusao | — | IDENTIDADE | L430:28-73; L430:76-148 | =texto | CFG-EXC; RQ-GOV-09 |
| ENUM-MotivoBloqueioBase | — | IDENTIDADE | L431:23-96; L431:99-301 | =texto | RQ-DAD-42 |
| ENUM-PapelPlanilha | — | IDENTIDADE | L432:18-63; L432:66-143 | =texto | — |
| ENUM-MotivoEncerramentoSessao | — | IDENTIDADE | L433:29-64; L433:67-152 | =texto | — |
| ENUM-DetalheBloqueio | — | IDENTIDADE | L434:20-43; L434:46-135 | =texto | ENUM-DetalheMotivo; ENUM-MotivoNaoAvaliavel |
| ENUM-TipoOcorrenciaEntregavel | — | IDENTIDADE | L435:29-50; L435:53-128 | =texto | ENUM-StatusEntregavel |
| TPL-13 | — | REPRESENTACAO | L1106:11-73; L1106:76-344 | =texto | RQ-DAD-43 |
| ENUM-StatusExecucaoElemento | — | IDENTIDADE | L436:27-66; L436:69-369 | =texto | MODELO:ResultadoElemento; RQ-ORQ-14; RQ-RES-04 |
| ENUM-TipoInteracaoUsuario | — | IDENTIDADE | L437:25-255; L437:258-398 | =texto | CFG-OPR; EV-INTERACAO_USUARIO; RQ-FLX-17 |
| ENUM-ConsequenciaExclusao | — | IDENTIDADE | L438:25-137; L438:140-313 | =texto | CFG-EXC; RQ-GOV-09 |
