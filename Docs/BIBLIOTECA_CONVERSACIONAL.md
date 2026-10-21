# Biblioteca de Inteligência Conversacional

Componente interno que ajuda o intérprete de linguagem (hoje o Gemini) a reconhecer intenções, continuidade e
alterações de parâmetros. Não aparece na interface e não é uma ferramenta do usuário. Os números da biblioteca
(trajetórias, turnos, cobertura) saem de `python scripts/biblioteca_conversacional.py estatisticas`.

## Onde está

| Parte | Arquivo |
|---|---|
| Trajetórias (JSONL, uma por linha, por dimensão A–J) | `backend/biblioteca_conversacional/trajetorias/` |
| Carga, validação, recuperação e montagem do bloco de exemplos (sem dependência de provedor) | `backend/conversation_library.py` |
| Integração com o provedor: máscara, envio na instrução de sistema e rastreio | `backend/llm_bridge.py` (`_library_examples`, `_system_instruction`, `library_contract`) |
| Trajetórias inéditas, só para avaliação (nunca recuperadas) | `backend/tests/biblioteca_ineditas/` |
| Avaliação de pertinência e testes | `backend/tests/library_evaluation.py`, `backend/tests/test_conversation_library.py` |
| Ferramenta de manutenção | `scripts/biblioteca_conversacional.py` |

## Como funciona na conversa

1. A mensagem chega a `/api/llm/interpret` ou `/api/llm/interpret-context` e passa pelos canais determinísticos de
   sempre. Só as que vão ao provedor usam a biblioteca.
2. `Library.select` escolhe até `ADT_BIBLIOTECA_EXEMPLOS` turnos (padrão 5), no máximo um por trajetória e dois por
   decisão, por recuperação lexical local (BM25 sobre palavras, prefixos de cinco letras e 4-gramas, sem serviço
   externo) com a mensagem, a mensagem anterior e o estado verificado (resultado apresentado, seleção, análise
   ativa, documento anterior). Só entram turnos do mesmo modo do pedido (com ou sem base carregada).
3. `render` monta o bloco: cada exemplo traz a projeção de continuidade (quando o pedido real a leva), as mensagens
   anteriores, a mensagem atual e a saída esperada no contrato do intérprete. Os textos passam pela **mesma
   minimização das mensagens do usuário** naquele pedido (valores, campos e arquivo da base em uso viram
   `[DADO_LOCAL]`, números `[VALOR_LOCAL]`, nomes `[ENTIDADE_PROTEGIDA]`). Valores que deixam de ser literais depois
   da máscara saem da saída; um exemplo de leituras concorrentes cujas âncoras somem fica de fora. Bloco de até 3.600
   caracteres.
4. O bloco vai na instrução de sistema, depois das regras de sempre (`_SYSTEM`). A resposta da API traz
   `biblioteca: {versao, exemplos}` com os ids usados. A resposta do provedor passa pelas mesmas validações de antes;
   a biblioteca não muda o que o backend aceita.

`ADT_BIBLIOTECA_CONVERSACIONAL=0` desliga a biblioteca: o pedido ao provedor volta a ser exatamente o anterior
(conferido em teste). A biblioteca é lida uma vez por processo, na primeira mensagem que chega ao provedor.

Na medição de 21/10/2026, carga, seleção e máscara iniciais levaram 0,83 s; com o índice carregado,
a mediana de seleção e máscara foi 4,89 ms. Cinco exemplos adicionaram 546 tokens de entrada ao pedido
sintético medido (708 → 1.254). A comparação de seis chamadas não isolou uma piora consistente de latência
causada pelos exemplos; houve variação na espera remota e um HTTP 503 do provedor. Isso não demonstra
ausência de impacto em outros pedidos. Método, resultados, limitações e ferramenta de reprodução em
[diagnóstico de latência do Gemini](DIAGNOSTICO_LATENCIA_GEMINI_20261021.md).

## Formato de uma trajetória

```json
{"id":"G-0123","dimensao":"G","tema":"…","perfil":"gestor","idioma":"pt","registro":"informal","fonte":"brasil",
 "passos":[{"usuario":"…","interpretacao":{…},"acao":"LE_RESULTADO","altera":[…],"preserva":[…],"restricoes":[…],
            "doc":[…],"contrato":[…],"nota":"…"}, {"evento":"CALCULO"}, …]}
```

- `passos` alterna turnos do usuário e eventos da interface (`FONTE_BRASIL`, `FONTE_IMPORTADA`, `ANALISE_ESCOLHIDA`
  com `operacao`, `SELECAO_TERRITORIAL`, `LIMPA_SELECAO`, `CALCULO`, `HISTORICO`, `NOVA_ANALISE`, `NOVA_SESSAO`).
  O estado mostrado ao modelo antes de cada turno é derivado desses passos (`conversation_library.turns`).
- `interpretacao` é a saída esperada do intérprete, com os campos do contrato (`operation`, `indicator`, `period`,
  `category`, `territory`, `intent`, `topic`, `dialogue`, `social_reply`, `candidates`). Período, categoria,
  território e âncoras são trechos literais da mensagem.
- `acao` diz o que o sistema faz com o turno (lista fechada em `ACTIONS`); `altera`/`preserva` são as transições
  de contexto; `restricoes` e `contrato` citam as regras aplicáveis (listas fechadas); `doc` cita ids do catálogo
  governado. **Não há campo de resposta**: as trajetórias não trazem prosa do sistema, fórmulas, limiares nem
  números de resultado. Explicações metodológicas vêm só das formas de `document_catalog.TOPICS`. Na leitura do
  resultado (`LE_RESULTADO`), `doc` traz exatamente as formas que `result_conversation` apresenta: `DOC:EXC-03`
  com "por que", "porque", "causa" ou "motivo"; a explicação da densidade num resultado de densidade sem palavra
  comparativa; `DOC:CFG-DOC.comportamento` nas análises sem leitura pela conversa.

## Como acrescentar ou corrigir trajetórias

1. Escreva as trajetórias novas num arquivo `.jsonl` (uma por linha, ids `<dimensão>-NNNN` ainda não usados).
2. Valide: `python scripts/biblioteca_conversacional.py validar --arquivo novo.jsonl`. O validador usa o mesmo
   contrato do intérprete (`llm_bridge.library_contract`): enumerações, compatibilidade operação/indicador, âncoras
   literais, cortesia da lista fechada, coerência entre interpretação e ação, ids do catálogo e da SPEC, repetição.
3. Mova o arquivo para `backend/biblioteca_conversacional/trajetorias/` e valide a biblioteca inteira
   (`validar` sem argumentos). A versão (`biblioteca.versao`) muda com o conteúdo.
4. Confira o efeito: `python scripts/biblioteca_conversacional.py consultar "mensagem" [--resultado] [--base]`
   mostra os exemplos escolhidos e o bloco que iria ao modelo (com `--base`, mascarado pela base Brasil versionada,
   somente em leitura). `avaliar` mede a pertinência nas trajetórias inéditas. `comparar` interpreta turnos
   inéditos sem e com os exemplos num modelo real: o Gemini (com `GEMINI_API_KEY`, dentro do limite local de
   chamadas) ou Qwen, DeepSeek e Llama num servidor compatível com a API de chat da OpenAI (`--provedor
   compativel --url … --modelo …`, por exemplo Ollama ou llama.cpp).
5. Uma mudança na biblioteca muda o pedido ao provedor: registre-a em `Docs/REGISTRO_DE_COMPORTAMENTO.md` (regra 1
   do `AGENTS.md`). Não copie trajetórias inéditas para a biblioteca: elas medem a generalização.

Quando o contrato do intérprete mudar (operações, tópicos, atos de diálogo), atualize as trajetórias afetadas; o
teste `test_library_is_valid_diverse_and_covers_the_interpreter_contract` falha enquanto houver turnos fora do
contrato ou valores do contrato sem exemplo.

## Limites

- A biblioteca orienta a interpretação; não calcula, não escolhe territórios, não autoriza execução e não amplia o
  contrato do provedor. Referência mais próxima e critérios combinados continuam só no canal determinístico.
- Mensagens em inglês e espanhol são interpretadas; a apresentação continua em português (EN não autorizado).
- A biblioteca não depende do Gemini: o bloco é texto na instrução de sistema (`_system_instruction`) e serve a
  qualquer modelo que receba as mesmas instruções.
- A avaliação automática mede a pertinência dos exemplos entregues ao modelo, não a qualidade das respostas de
  um modelo real, que não é chamado nos testes; para isso serve o comando `comparar`.
