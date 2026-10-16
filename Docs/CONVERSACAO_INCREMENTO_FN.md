# Conversação experimental — incrementos FN (atualizado em 16/10/2026)

Esta implementação é **parcial** e incremental. A referência normativa continua
sendo `IMPLEMENTATION_SPEC.md` v1.2.4, especialmente §8.5, Parte 6 e Parte 14.
Nenhum dos contratos FN abaixo foi declarado integralmente atendido.

## O que foi incorporado

| Contrato | Incremento executado | Ainda não implementado |
|---|---|---|
| FN-INT-01 | Distingue conversa, pergunta sobre o agente e proposta analítica; identifica capacidades explicitamente coordenadas e admite candidatas ancoradas para leituras concorrentes, sem escolher arbitrariamente uma delas | LeituraMinima integral com funções coexistentes, dados conversacionais, triagem nominal completa, tipagem de todos os trechos |
| FN-INT-02 | Modelo propõe capacidade/indicador ou até cinco candidatas; cada alternativa exige âncora literal no pedido atual. Slots de período, categoria e território continuam ancorados; nomes municipais são resolvidos localmente após validar a capacidade. Pendência simples de nomes admite continuação na mesma fonte | InterpretaçãoOperacional completa, múltiplos entregáveis, todas as associações de pendências/linhas e regras de admissibilidade |
| FN-INT-03 | Perguntas padronizadas para capacidades concorrentes, indicador da distribuição, período/categoria não confirmados e município faltante. Escolha estruturada prepara a análise localmente quando há base; demais escolhas preparam rascunho | Seleção completa de formas CFG-DOC/TPL-04, cobertura integral CFG-AMB/CFG-OPC e validação V-16 |
| FN-META-01 | Catálogo local controlado de explicações sobre o agente, importação, limites, privacidade, densidade, distâncias e sobreposição; classificações de assunto produzidas pelo Gemini não são exibidas como texto livre | Catálogo documental CFG-DOC integral, âncoras DOC: materializadas, consultas a eventos C-13 e V-16 integral |

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
- As menções ao histórico são limitadas aos textos já escritos pelo usuário.
  Períodos e categorias retomados passam novamente pela validação de valores
  da base. Solicitações novas sem anáfora explícita não herdam esses valores.
- Perguntas diretas sobre o funcionamento do agente são respondidas localmente,
  sem consumir quota da API Gemini, inclusive em modo degradado ou durante uma
  pendência de nomes de municípios. A pergunta de orientação não apaga essa pendência.
- Não foram adicionados planejamento de várias análises (FN-ORQ-01),
  sugestões derivadas dos resultados (FN-INT-04), sínteses (CAP-SIN-01),
  execução automática nem alterações ao motor de cálculo.

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

Em telas a partir de 1.024 px, a conversa fica à esquerda e seleção, preparação e
resultados à direita. As áreas têm rolagem independente e o compositor permanece
visível. Em telas estreitas, os painéis se empilham dentro da altura disponível.
Novas respostas acompanham a rolagem da conversa, sem levar a página ao topo.
O histórico de análises fica acessível desde o início e reabre cálculos existentes
no painel de resultados, sem recalcular nem restaurar parâmetros implicitamente.
Reabrir resultados, alternar preparação/resultado ou usar o atalho “Resultados”
desloca somente a área de análise; a barra do histórico e o compositor permanecem
visíveis. A atualização do fragmento da URL não dispara rolagem nativa da página.
Após selecionar uma análise, a identificação compacta da fonte substitui a
apresentação repetida dos dados; o carrossel continua acessível em “Escolher outra análise”.

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
