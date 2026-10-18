# Conversação experimental — incrementos FN (atualizado em 17/10/2026)

Esta implementação é **parcial** e incremental. A referência normativa continua
sendo `IMPLEMENTATION_SPEC.md` v1.2.4, especialmente §8.5, Parte 6 e Parte 14.
Nenhum dos contratos FN abaixo foi declarado integralmente atendido.

## O que foi incorporado

| Contrato | Incremento executado | Ainda não implementado |
|---|---|---|
| FN-INT-01 | Distingue conversa, pergunta sobre o agente e proposta analítica; identifica capacidades explicitamente coordenadas e admite candidatas ancoradas para leituras concorrentes, sem escolher arbitrariamente uma delas | LeituraMinima integral com funções coexistentes, dados conversacionais, triagem nominal completa, tipagem de todos os trechos |
| FN-INT-02 | Modelo propõe capacidade/indicador ou até cinco candidatas; cada alternativa exige âncora literal no pedido atual. Slots de período, categoria e território continuam ancorados; nomes municipais são resolvidos localmente após validar a capacidade. Pendência simples de nomes admite continuação na mesma fonte | InterpretaçãoOperacional completa, múltiplos entregáveis, todas as associações de pendências/linhas e regras de admissibilidade |
| FN-INT-03 | Perguntas padronizadas para capacidades concorrentes, indicador da distribuição, período/categoria não confirmados e município faltante. Escolha estruturada prepara a análise localmente quando há base; demais escolhas preparam rascunho | Seleção completa de formas CFG-DOC/TPL-04, cobertura integral CFG-AMB/CFG-OPC e validação V-16 |
| FN-META-01 | Formas PT literais com âncoras DOC: para densidade, distância e agregação; catálogo conferido contra o Anexo A; EN bloqueado pela autorização APT-20261016. Orientações legadas continuam locais | Seleção contextual de todas as formas, consultas integrais a C-13 e V-16 integral |
| FN-INT-04 / CAP-SIN-01 (parciais) | Seleção e parâmetros verificados por sessão; leitura de densidade, quantitativos e comparação por referência ao resultado do backend; segmentos copiados com caminhos e relações já calculadas; preparação explícita de comparação faltante | Síntese analítica abrangente das demais capacidades, múltiplos entregáveis, livre paráfrase metodológica (não autorizada) |

## Fronteiras preservadas

- O Gemini **não executa** operações e não recebe arquivos, linhas ou nomes de
  colunas; a proposta continua preliminar e sujeita ao pré-exame Python.
- Diante de pedido explicitamente duplo como “densidade e quantitativos”, o
  sistema pede uma decisão, sem iniciar análise múltipla automaticamente.
- Perguntas e rótulos são oriundos de um catálogo do backend. Escolher uma
  alternativa estruturada com base disponível envia a escolha explícita ao
  resolvedor Python e **apenas prepara** a análise. Sem base, ou em perguntas
  legadas sem operação estruturada, preenche o rascunho da mensagem. Nenhuma
  alternativa calcula resultados ou confirma premissas metodológicas.
- O histórico textual enviado continua limitado aos textos escritos pelo usuário; a sessão guarda também intenção, referente documental e resultados verificados, sem enviar seus dados ao provedor.
  Períodos e categorias retomados passam novamente pela validação de valores
  da base. Solicitações novas sem anáfora explícita não herdam esses valores.
- Perguntas diretas sobre o funcionamento do agente são respondidas localmente,
  sem consumir quota da API Gemini, inclusive em modo degradado ou durante uma
  pendência de nomes de municípios. A pergunta de orientação não apaga essa pendência.
- Não foram adicionados planejamento de várias análises (FN-ORQ-01), execução automática nem alterações ao motor de cálculo. A leitura de resultados e sugestões têm o escopo parcial registrado em [Evolução conversacional](EVOLUCAO_CONVERSACIONAL_20261016.md); não equivalem à implementação integral de FN-INT-04/CAP-SIN-01.

## Continuidade e ambiguidade material

O prompt deixou de exigir “no máximo uma capacidade”. O campo opcional `candidates`
admite até cinco pares de operação/indicador, com âncoras na mensagem sanitizada
atual. A ausência do campo mantém compatibilidade com a resposta única. O Python
valida o esquema, as enumerações, a compatibilidade do indicador e as âncoras;
rejeita alternativas sem sustentação literal. Candidatas repetidas são deduplicadas.
Havendo duas ou mais leituras diferentes, `AMBIGUIDADE_MATERIAL` apresenta escolhas;
o aplicativo não escolhe uma silenciosamente. Isso implementa parte de FN-INT-01/02,
CFG-AMB e CFG-OPC, sem declarar cobertura integral desses contratos.

A escolha também funciona antes da primeira análise, sem seleção territorial
prévia. O indicador proposto ou escolhido é levado à preparação após concluir
uma eventual mudança de recorte; não é perdido durante a inspeção da fonte.
Escolher outra capacidade pelos controles descarta uma pendência municipal de
capacidade diferente.

Após validar a capacidade, o Python cruza a mensagem original com o catálogo
territorial local. Os nomes e IDs resolvidos não são obtidos do provedor nem
enviados a ele. Por exemplo, “coloque Manaus e Tefé lado a lado” pode propor
comparação e preparar esses dois municípios. “Agora vamos analisar comparativamente
no município de São Paulo” distingue a cidade do estado homônimo e pergunta com
qual outro município comparar. A próxima mensagem pode completar os nomes.

“Analise dois municípios também”, com uma análise já selecionada, informa uma
quantidade, sem autorizar escolher quais municípios. O sistema pede os nomes e
prepara a seleção quando forem fornecidos. A pendência pertence à fonte/versão;
trocar entre recortes nacional e municipal da mesma base Brasil não a perde, mas
outra fonte não a reutiliza. Homônimos, termos de recorte não reconhecidos e
períodos indisponíveis continuam gerando esclarecimento. A gramática local é
limitada; isso não equivale a compreender qualquer formulação ou orquestrar vários
pedidos automaticamente.

## Espaço de trabalho

A interface atual tem um único fluxo de investigação: conversa expansível, preparação, resultados e campo de mensagem contextual. A barra horizontal reúne as cinco ações principais, sem navegação lateral permanente. Os contratos de interpretação descritos aqui permanecem iguais. A disposição visual vigente está no [guia da interface integrada](INTERFACE_CONVERSACIONAL_INTEGRADA.md).

## Testes

Os testes `test_dialogue_guidance.py`, `test_conversation_guidance.py`,
`test_llm_context.py` e `test_territorial_selection.py` verificam capacidades
concorrentes, alternativas ancoradas ou rejeitadas, período não confirmado, FAQ
offline durante pendências, resolução local, ausência de dados da base no payload
do provedor, nenhuma execução e recuperação contextual ancorada.

O workflow `.github/workflows/ci.yml` executa backend, build e jornadas de navegador
registradas em `backend/tests/run_ui_checks.py`. A jornada
`ui_semantic_continuity.py` usa provedor simulado para verificar paráfrases,
escolha de interpretação antes do primeiro cálculo e após resultados, nomes
pendentes, histórico sem recálculo e compositor visível em 1.280, 768 e 390 px.
Também confere a barra do histórico dentro da janela e a ausência de rolagem externa.
Nenhum desses testes faz chamada ao Gemini real; a qualidade e a disponibilidade
do provedor real exigem validação distinta.

Na validação local de 16/10/2026, o provedor configurado interpretou o pedido
comparativo sobre São Paulo; o resolvedor local perguntou qual outro município,
e a resposta “Campinas e Rio de Janeiro” preparou três municípios. É uma
verificação pontual do transporte real, sem comprovar interpretação de qualquer
formulação possível.
