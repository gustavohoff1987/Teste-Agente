# Conversação experimental — incremento FN (10/10/2026)

Esta implementação é **parcial** e incremental. A referência normativa continua
sendo `IMPLEMENTATION_SPEC.md` v1.2.4, especialmente §8.5, Parte 6 e Parte 14.
Nenhum dos contratos FN abaixo foi declarado integralmente atendido.

## O que foi incorporado

| Contrato | Incremento executado | Ainda não implementado |
|---|---|---|
| FN-INT-01 | Distingue conversa, pergunta sobre o agente e proposta analítica; identifica duas capacidades explicitamente coordenadas sem escolher arbitrariamente uma delas | LeituraMinima integral com funções coexistentes, dados conversacionais, triagem nominal completa, tipagem de todos os trechos |
| FN-INT-02 | Modelo propõe uma capacidade estruturada; slots de período, categoria e território só retornam quando ancorados na mensagem; resgate limitado de valores do histórico exige referência explícita na mensagem atual | InterpretaçãoOperacional completa, múltiplos entregáveis, associações de pendências e linhas, todas as regras de admissibilidade |
| FN-INT-03 | Perguntas padronizadas para múltiplas capacidades, indicador da distribuição e desencontro de período/categoria ou confirmação territorial; alternativas só preparam texto no chat | Seleção completa de formas CFG-DOC/TPL-04, opções CFG-OPC, validação V-16 integral |
| FN-META-01 | Catálogo local controlado de explicações sobre o agente, importação, limites, privacidade, densidade, distâncias e sobreposição; classificações de assunto produzidas pelo Gemini não são exibidas como texto livre | Catálogo documental CFG-DOC integral, âncoras DOC: materializadas, consultas a eventos C-13 e V-16 integral |

## Fronteiras preservadas

- O Gemini **não executa** operações e não recebe arquivos, linhas ou nomes de
  colunas; a proposta continua preliminar e sujeita ao pré-exame Python.
- Diante de pedido explicitamente duplo como “densidade e quantitativos”, o
  sistema pede uma decisão, sem iniciar análise múltipla automaticamente.
- Perguntas padronizadas são oriundas de um catálogo do backend. Escolher uma
  alternativa **preenche apenas o rascunho da mensagem**: não envia, não executa
  análises e não confirma parâmetros sem manifestação do usuário.
- As menções ao histórico são limitadas aos textos já escritos pelo usuário.
  Períodos e categorias retomados passam novamente pela validação de valores
  da base. Solicitações novas sem anáfora explícita não herdam esses valores.
- Perguntas diretas sobre o funcionamento do agente são respondidas localmente,
  sem consumir quota da API Gemini, inclusive em modo degradado.
- Não foram adicionados planejamento de várias análises (FN-ORQ-01),
  sugestões derivadas dos resultados (FN-INT-04), sínteses (CAP-SIN-01),
  execução automática nem alterações ao motor de cálculo.

## Testes

Os testes `backend/tests/test_dialogue_guidance.py` verificam demandas
concomitantes, perguntas com alternativas fechadas, discriminação de período
não confirmado, FAQ offline, nenhuma execução e recuperação contextual ancorada.
A suíte de backend e o build TypeScript/Vite são executados pelo workflow
`.github/workflows/ci.yml` a cada push na branch de desenvolvimento.

A chamada externa real à API Gemini e os testes de interface em navegador
**não** são cobertos por esse workflow. Precisam de validação local distinta.
