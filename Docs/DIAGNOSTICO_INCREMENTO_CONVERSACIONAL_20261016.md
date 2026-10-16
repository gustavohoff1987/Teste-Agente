# Diagnóstico prévio do incremento conversacional — 16/10/2026

## Situação e decisão de execução

Diagnóstico da branch `feat/novos-blocos-incrementais`, commit
`1f416825a57bead166e1a207f975dc359c02eed7`. O diretório de trabalho estava limpo.
`git ls-remote` confirmou a mesma revisão no remoto `origin`; a referência remota
`main` estava em `6284151df186fb76786a415d805e54a109a23ae6`.
A primeira consulta falhou por credenciais Schannel no ambiente restrito; a
repetição com acesso ampliado, somente para leitura das referências, funcionou.

**A implementação do incremento está interrompida antes de alterações no produto.**
Esta decisão aplica as seções 7 e 9 do pedido: apresentar diagnóstico antes de
prosseguir quando forem necessárias alterações estruturais relevantes ou houver
incompatibilidade com a SPEC. Nenhuma alteração normativa é proposta aqui.

O objetivo pode ser perseguido dentro da SPEC, mas a entrega integral não se
resolve apenas com prompt, temperatura ou mais mensagens de histórico. Faltam
recursos de validação e ancoragem exigidos para exibir explicações e sínteses
produzidas pelo modelo. A recuperação do catálogo autorizado e a implementação
desses recursos precisam ter seu escopo decidido antes da continuação.

Este documento é um diagnóstico de implementação, não um contrato de governança,
aprovação de novas formas documentais ou declaração de conformidade integral.

## 1. Limitações identificadas e suas evidências

| Componente | Situação observada | Consequência |
|---|---|---|
| `backend/llm_bridge.py`, `ModelInterpretation`, `_schema`, `_SYSTEM` | Gemini fornece operação, indicador, slots, intenção, tópico e candidatas. Não há contrato de resposta explicativa ou síntese. O prompt explicitamente proíbe afirmações factuais, metodológicas, estatísticas e normativas. | As capacidades linguísticas do modelo estão restritas à interpretação. Abrir um campo de texto livre sem validador não é uma correção suficiente. |
| `backend/llm_bridge.py`, `_validate`, `_GUIDANCE` | O tópico interpretado escolhe uma resposta fixa. A intenção `CONVERSACIONAL` retorna a saudação genérica. | Pedidos de simplificação ou aprofundamento não têm representação própria; diferentes formulações podem produzir o mesmo texto. |
| `frontend/src/AnalysisAssistant.tsx`, `send` | Expressões como “e agora”, “continue” e “quantos tem” retornam orientação de preparação quando existe análise ativa, antes de consultar o backend, sem considerar o resultado mostrado. | Uma pergunta espontânea sobre o resultado pode ser tratada como instrução de navegação. |
| `AnalysisAssistant.tsx` e `ChatRequest` | Histórico limitado às últimas quatro mensagens do usuário. Respostas do agente, perguntas pendentes completas, ações da interface e resultado em exibição não compõem esse histórico. | O LLM não acompanha toda a continuidade da interação. Aumentar o histórico bruto também poderia ampliar exposição de conteúdo e custo. |
| `backend/llm_bridge.py`, `_anchors_for_turn` | Recuperação de slots depende de anáforas enumeradas e da mensagem imediatamente anterior. | Uma pergunta conceitual intermediária pode afastar a referência útil; correções e reformulações precisam de estado explícito. |
| `backend/llm_context.py`, `provider_snapshot` | O provedor recebe `has_dataset`, papéis reconhecidos e estados das dez capacidades do contrato. | Não recebe identidade verificável do resultado atual, seleção territorial, parâmetros completos, explicações de pendências ou histórico de análises. |
| `backend/analysis_catalog.py` | Referência mais próxima e critérios combinados existem no motor, mas ficam fora do contrato de interpretação do LLM. | O catálogo mencionado nas orientações é mais amplo que as operações que o modelo consegue propor. |
| `frontend/src/App.tsx` | Resultados, preparação salva e vigência são mantidos na memória da aba; `resultContent` é passado ao assistente como apresentação React. | Exibir o resultado ao lado do chat não o transforma em contexto do modelo. |
| `backend/main.py`, `/api/analyze` | A API calcula, registra ID, metadados e chave de execução e devolve o resultado. O fluxo conversacional não resolve esse ID para um resultado autorizado guardado no servidor. | Um resultado reenviado pelo cliente precisaria de verificação de origem e vínculo; não pode ser aceito como fato apenas por chegar em JSON. |

A configuração usa `gemini-3.5-flash-lite`, temperatura zero, até 600 tokens de
saída e limite local de 20 solicitações por dia. Esses valores não são a causa
principal da rigidez: o esquema e a materialização das respostas já impedem a
produção de prosa explicativa. Não houve troca de modelo, aumento de cotas ou
chamada ao provedor real durante este diagnóstico.

## 2. Funcionalidades analíticas efetivamente implementadas

O motor e o pré-exame compartilham doze operações. Disponibilidade na interface
não equivale a autorização para qualquer configuração: `/api/analyze` reavalia o
pré-exame antes do cálculo.

| Operação | Implementação e condições relevantes observadas |
|---|---|
| Densidade | Quantidade/população × 1.000; exige denominador e significados compatíveis. |
| Quantitativos | Contagens conforme unidade declarada; não dependem necessariamente de população ou geografia. |
| Distribuição | Indicador explícito, quantis e posições; cortes Hyndman–Fan tipo 7, preservando empates. |
| Comparações | Quantidade ou densidade no motor; dois objetos produzem relação e diferença; conjuntos maiores têm relações estruturadas próprias. O esquema principal do LLM ainda restringe comparação a densidade/indicador não definido. |
| Evolução temporal | Mudanças entre períodos e tendência determinística com ao menos quatro observações; depende de comparabilidade e identidade territorial. Não produz previsão. |
| Agregações | Combina territórios em um período/categoria; conserva distinção entre soma de componentes e unidades distintas. |
| Análise espacial | Distância geodésica a uma referência, com coordenadas e referencial compatíveis; não mede deslocamento viário ou acesso efetivo. |
| Recortes e rankings | Ordenação por densidade e posições com empates; não estabelece adequação normativa. |
| Rotatividade | Coorte e identidade longitudinal; não é calculável a partir de meras contagens sem identificadores. |
| Relatórios | Resultados estruturados de quantidade ou densidade, exportação e impressão. |
| Referência mais próxima | Busca geodésica entre referências avaliáveis, com cobertura e motivos de não avaliabilidade. |
| Critérios combinados | Condições estruturadas, combinações, classificações, ordenações e referências autorizadas; não permite fórmula livre criada pelo modelo. |

Referências de código: `backend/main.py`, `backend/semantic_bridge.py`,
`backend/data_contract.py`, `backend/nearest_reference.py`,
`backend/combined_criteria.py` e `backend/analysis_catalog.py`.

## 3. Limites normativos e impedimentos

Foram consultados a SPEC v1.2.4, o AGENTS.md, o README e os documentos de
conversação, ponte semântica e blocos analíticos. A implementação atual já se
declara parcial em `Docs/CONVERSACAO_INCREMENTO_FN.md` e no README.

1. **Liberdade de formulação não inclui paráfrase metodológica livre.**
   A SPEC, §4.4.23.5, V-16 e RQ-SIN-07/10, permite seleção e organização de formas
   autorizadas e conectores não substantivos. V-16 exige correspondência literal
   à forma materializada, versões, condições, tipos, origens e âncoras. Aumentar
   a liberdade do prompt e filtrar somente palavras ou números não satisfaria
   esse contrato. Essa restrição não impede melhorias de continuidade ou de
   interpretação linguística; delimita como explicações podem ser apresentadas.
2. **O catálogo autorizado está ausente.** `Docs/CFG_DOC_CATALOG.yaml`, exigido
   pelo §4.4.23.6, não existe no diretório de trabalho nem está listado no Git.
   A consulta ao histórico local alcançável por `git log --all --` também não
   encontrou esse caminho. Isso não prova inexistência em outra cópia externa.
   Não cabe inventar variantes e apresentá-las como previamente autorizadas.
3. **O validador de saída ainda não existe na extensão requerida.** A validação
   atual controla o JSON de interpretação, operações, indicadores e âncoras de
   slots. Não implementa segmentos de síntese, usos documentais V-16 e validação
   integral V-01 a V-15. A documentação atual confirma essas lacunas. RQ-SIN-04
   exige validação de todo texto de LLM exibido.
4. **Falta vínculo confiável entre conversa e resultado exibido.** O backend
   precisaria verificar identidade, origem, recorte e validade do resultado
   referido; mudanças de seleção não podem requalificar silenciosamente um
   resultado anterior. A memoização existente é restrita a uma requisição HTTP
   e não constitui repositório de resultados da sessão.
5. **A política local de privacidade é mais restritiva que enviar resultados
   completos ao modelo.** O README permite apenas pedido sanitizado e estados
   técnicos enumerados; proíbe arquivos, linhas, nomes de campos e valores da
   base. O incremento deve manter valores e nomes localmente e usar referências
   opacas/estados mínimos cuja origem seja validada. Transmitir tabelas,
   metadados originais ou histórico bruto de respostas seria inadequado.

Conclusão: não é necessário alterar a SPEC para evoluir a conversa dentro das
formas autorizadas, mas a entrega integral requer trabalho relevante de
integração e governança hoje ausente. Isso aciona a salvaguarda expressa do pedido.

## 4. Alternativas para decisão do responsável

### A. Incremento restrito aos mecanismos existentes

Revisar interceptações do frontend; organizar histórico de intenções, pendências
e correções; melhorar resolução de referências e revalidação da seleção atual;
ampliar estados técnicos do catálogo de capacidades sem enviar conteúdo da base.
Manter a apresentação substantiva no canal local já existente.

Vantagem: alterações concentradas nos componentes atuais. Limitação: não entrega
a síntese conversacional integral nem liberdade de explicação; conserva as
lacunas normativas já documentadas. Não deve ser apresentado como atendimento
completo deste incremento.

### B. Evolução completa em etapas, preservando a SPEC — recomendada para o objetivo integral

Obter a versão autorizada de `CFG_DOC_CATALOG.yaml` compatível com a SPEC 1.2.4;
definir e implementar o vínculo verificável entre estado da interface, sessão e
resultados; implementar seleção/materialização de formas e validação de saída;
integrar interpretação, explicação e sugestões ao Gemini existente.

O desenho deve manter resultados originais e nomes no backend, expor ao provedor
somente contexto minimizado permitido, validar referências e recompor conteúdo
localmente. Não deve recalcular para responder uma explicação nem aceitar
afirmações factuais do navegador como resultado autenticado. Escopo, descarte,
isolamento e expiração desse vínculo precisam ser definidos antes da execução.

Essa alternativa envolve implementação relevante de capacidades conversacionais
e governança previstas, sem acrescentar métodos analíticos, dependências externas
ou redesenho visual. Exige confirmação desse escopo estrutural e acesso ao
catálogo autorizado. Não se propõe revisar a SPEC para permitir prosa irrestrita.

## 5. Exemplos: comportamento atual e alvo de uma implementação futura

**Não são exemplos de capacidades entregues.** A coluna futura descreve critérios
de aceite; qualquer texto substantivo dependerá das formas autorizadas.

| Interação | Evidência atual | Comportamento futuro a validar |
|---|---|---|
| “O que significa densidade?” → “Explique de um jeito mais simples” | Uma reprodução local de `_validate`, fornecendo o mesmo tópico `density`, devolveu exatamente a mesma resposta nos dois turnos. Não houve chamada real ao LLM. | Reconhecer o pedido de simplificação e selecionar uma forma autorizada adequada, sem alterar fórmula, condições ou significado. |
| Após um resultado: “e agora?” | O caminho de `send` com fonte e análise ativas produz orientação fixa de preparação, sem consultar o resultado. Evidência por inspeção de código. | Distinguir resultado exibido de preparação atual; oferecer aprofundamento suportado pela matriz e aguardar escolha. |
| Seleção alterada de municípios: “compare esses” | A resolução local já pode usar seleções; o snapshot externo contém somente papéis e disponibilidade. | Usar a seleção atual revalidada, não nomes antigos do histórico; perguntar apenas se existir ambiguidade material. |
| Histórico reaberto: “o que este resultado mostra?” | A conversa não recebe referência estruturada ao resultado reaberto. | Resolver o ID mostrado, conferir origem, método, validade e recorte; manter rótulos e limitações do resultado original. |
| “Por que a densidade aqui é maior?” | Não existe síntese ancorada nas relações calculadas. | Separar uma relação descritiva já calculada de explicação causal; só citar valores/relações existentes e explicitar a limitação causal. |

## 6. Verificações do estado anterior ao incremento

As verificações abaixo avaliam a revisão existente. Não comprovam evolução
conversacional, validação V-16 ou conformidade integral com a SPEC.

- Integridade: `python backend/brazil_data.py diagnostico` retornou
  `"integridade": "verificada"` antes e depois das suítes, com os mesmos hashes
  dos dois arquivos originais e a mesma versão governada.
- Governança: a execução padrão falhou ao decodificar texto Git em CP1252 no
  Windows. Repetida com `PYTHONUTF8=1`, passou: quatro commits verificados e todos
  os roteiros de navegador registrados no CI. Nenhum teste ou verificador foi
  alterado para esse resultado.
- Backend, execução padrão: **416 passaram, um falhou e 29 foram pulados**.
  A falha foi `test_commit_de_produto_sem_registro_e_apontado_e_pode_ser_regularizado`;
  a leitura de mensagens Git com acentos depende da codificação do processo.
  Os testes reais são opt-in nessa execução. A repetição completa usa UTF-8 e
  `ADT_REAL_DATA_DIR` apontando para a raiz do repositório.
- Backend com `PYTHONUTF8=1` e `ADT_REAL_DATA_DIR` definido: **446 passaram,
  nenhum falhou e nenhum foi pulado**, em 463,05 segundos. Permaneceram avisos de
  depreciação do cliente de testes e de acesso ao cache do pytest no sandbox.
  A falha inicial de governança não se repetiu com UTF-8; o verificador continua
  dependente da codificação do ambiente na execução padrão do Windows.
- `npm ci`: concluído. Informou sete vulnerabilidades em dependências
  (duas moderadas e cinco altas); não houve atualização de versões.
- Build: a primeira tentativa falhou por acesso negado do esbuild a diretórios
  ancestrais no sandbox. A repetição com acesso ampliado passou (`tsc --noEmit`
  e Vite, 2.222 módulos), com aviso de tamanho do bundle.
- Jornadas: `PYTHONUTF8=1 python backend/tests/run_ui_checks.py`, usando o Chrome
  instalado, concluiu **dez roteiros aprovados**, incluindo conversa, seleção e
  regressão do Bloco 1, referência mais próxima, critérios, mapas, visibilidade,
  integração e continuidade semântica com Gemini simulado e base Brasil real.
- Reprodução determinística da repetição linguística: executada diretamente com
  duas saídas simuladas do mesmo tópico; respostas idênticas e `executed=False`.
- Chamadas reais ao Gemini: **não executadas**. Testes com transporte simulado
  verificam integração e rejeição de propostas, não naturalidade do modelo real.

## 7. Preservação e arquivos alterados

Somente este relatório foi acrescentado. Código, testes, SPEC, contratos de
governança, workflow, manifesto e arquivos da base não foram modificados.
Não há nova capacidade conversacional entregue nem novos testes implementados.
Instalação e build utilizam os arquivos de dependências já existentes.
Nenhum commit, push, merge ou reset foi realizado no repositório de trabalho.

## 8. Pendências e avaliação futura

- Decidir entre o incremento restrito (A) e o escopo completo em etapas (B).
- Para B, identificar a origem do catálogo autorizado e aprovar o desenho de
  vínculo de sessão/resultados e validação, mantendo a política de dados vigente.
- Após implementação: testes adversariais de âncoras falsas, resultado forjado,
  resultado de outra sessão/fonte, mudança de parâmetros durante requisição,
  histórico reaberto, ausência de dados, sugestões indisponíveis e prompt injection.
- Avaliação linguística separada com o modelo real: corpus de paráfrases,
  expressões coloquiais, perguntas sucessivas, correções e simplificação;
  critérios de pertinência, continuidade, concisão, variação e sustentação,
  sem igualdade obrigatória a frases exemplares. Medir também chamadas e tokens.
- Manter a regressão do motor, execução direta da interface e integridade por
  hashes antes/depois. Aprovação dos testes atuais não supre os recursos ausentes.
