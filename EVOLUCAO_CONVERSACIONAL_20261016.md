# Evolução conversacional — execução autorizada em 16/10/2026

## Incremento 1 — fluidez e catálogo PT

A integração passa a materializar explicações de densidade, distância e agregação diretamente do catálogo PT, com identidade, versão, uso e autorização APT-20261016 retornados na resposta. O carregador verifica o catálogo íntegro e as 703 formas-base contra o Anexo A. EN está bloqueado; as formas não foram alteradas. Ver `DECISAO_CATALOGO_PT_20261016.md` e o adendo restrito ao final da SPEC.

O Gemini continua no mesmo modelo, temperatura, tokens, timeout e cota. Seu contrato distingue pedidos de explicação, simplificação, próximos passos e alterações de seleção/período. Cortesia admite composições linguísticas limitadas sem fatos, números ou alegações de ação; conteúdo fora desse domínio não é exibido. Nenhum segundo LLM ou validador universal foi acrescentado.

Uma saudação repetida não reinicia a apresentação. Referência explícita a um parâmetro pode alcançar mensagens anteriores, atravessando pergunta conceitual. Pedido de simplificação retoma o tópico documentado recente e reorganiza aspectos, sem inventar paráfrase ou omitir condições. As formas disponíveis limitam a simplificação: esta versão não acrescenta versões didáticas ao catálogo.

Textos operacionais legados não migrados continuam identificados como implementação parcial. A autorização PT não resolve a divergência de canal RQ-FLX-14 nem completa a classificação de tendência do motor.

> Atualização de 19/10/2026: CAP-TEN-01 implementada no motor da evolução temporal (as sete classes da DA-15, o motivo de Sem classificação e a aritmética exata); ver [EVOLUCAO_TEMPORAL_E_TENDENCIA.md](Docs/EVOLUCAO_TEMPORAL_E_TENDENCIA.md). O texto acima registra o estado de 16/10/2026 e não foi reescrito.

Testes novos: `test_document_conversation.py`. A expectativa antiga de “multiplicada por 1.000” foi substituída no teste de orientação pela fórmula canônica agora apresentada; o produto mudou deliberadamente para materialização literal, mantendo a cobertura de orientação sem provedor. Os testes novos conferem todas as formas-base, bloqueio EN, adulteração, condições, metadados e continuidade.

Validação inicial: 76 testes automatizados aprovados, sem chamadas externas. A primeira jornada de navegador identificou a mesma expectativa textual antiga em `ui_conversational_smoke.py`; o teste foi ajustado para conferir a fórmula canônica, sem remover a verificação de resposta na interface. Essa falha era uma expectativa desatualizada pela mudança deliberada, não um defeito de cálculo. A repetição da jornada foi aprovada.

## Incremento 2 — consciência de tela e sessão

O backend captura seleção, parâmetros, fonte e revisão após o pré-exame local. A interface envia uma referência ao resultado apresentado; o backend resolve somente IDs registrados por `/api/analyze` na mesma sessão. Valores reenviados pelo cliente não são evidência. A chave de execução continua sendo identidade, nunca assinatura de autenticidade.

“Compare esses municípios” usa a seleção verificada; “Não, quantidade” corrige o indicador da operação em preparação; “Acrescente [município]” preserva a seleção anterior e inclui o nome resolvido localmente. “E agora?” apresenta seleção e possibilidades do pré-exame, sem calcular. Alteração de revisão durante o provedor rejeita a resposta tardia. Intenções e referências documentais são guardadas como estado técnico, sem transcrição no servidor.

O token fica somente na memória da aba. A sessão expira em 1.800 segundos de inatividade ou pelo controle Encerrar sessão, que limpa também o estado da interface. Polling e revisão automática não renovam a sessão. Encerrar a aba não apaga imediatamente a memória do servidor, eliminada pela expiração; reabrir a aplicação cria nova sessão. Não há retomada persistente. A solução usa um único processo; múltiplos workers não compartilham contexto e exigiriam projeto específico antes de uso.

Limites técnicos de memória: até 128 sessões, 64 referências/32 MiB por sessão e 256 MiB de resultados no processo. Ao atingir o limite de referências, o cálculo ainda é devolvido à interface, com `conversation_reference.available=false`; não se apagam resultados silenciosamente para abrir espaço. Eventos técnicos recentes têm encadeamento de hashes em memória e não contêm mensagens, arquivos ou valores.

A nova projeção externa contém somente enums e presença de seleção/resultado. Conteúdos da base mencionados no texto são removidos localmente no caminho de sessão antes do Gemini. A minimização conservadora de mensagens livres continua sem equivaler à triagem nominal integral da SPEC; dados pessoais não devem ser inseridos na conversa. A base e seus valores jamais são acrescentados ao prompt como contexto.

Validação: 39 testes de sessão/seleção/contexto aprovados; 66 testes de conversa/regressão aprovados. O build passou com acesso ampliado necessário ao esbuild neste ambiente. Jornadas reais de navegador usam transporte offline/simulado; não houve chamada real nem paga ao Gemini.

As duas jornadas `gemini-simulado` passaram novamente, incluindo seleção contextual e encerramento explícito. A nova asserção de seleção foi corrigida para os rótulos efetivamente presentes no catálogo sintético (`MANAUS [130260]`, `TEFE [130420]`); não houve alteração dos dados nem remoção da conferência territorial. A expiração da interface consulta o prazo vigente antes de descartar a aba, evitando encerrar uma sessão renovada por requisição recente.


## Incremento 3 — conversa sobre resultados verificados

Implementado em 17/10/2026. A leitura conversacional está habilitada para resultados de **densidade, quantitativos e comparação territorial**. O backend recupera a execução pelo ID opaco da mesma sessão, verifica sua integridade e a identidade da fonte (conteúdo, versão, arquivo/planilha e colunas), e distingue o recorte original da preparação atual. Uma mudança de foco ou de parâmetros não reescreve o resultado nem transforma seus valores em valores do novo recorte. Outra fonte impede a leitura contextual desse resultado. Resultado inexistente/adulterado ou de outra sessão não é apresentado.

O compositor copia caminhos de valores, parâmetros, métricas e notas do resultado. Relações verbais só são construídas quando o motor já retornou a relação A/B e a condição Comparável. Não compara números para descobrir uma relação nova. O controle confere conteúdo, tipo, origem, caminhos e a presença de todas as notas; conteúdo metodológico adicional é materializado pelo catálogo PT. O retorno declara os segmentos e a referência de execução. As notas originais do motor são conservadas, inclusive suas limitações; o incremento não revisa nem declara integralmente conformes todos os textos legados do produto.

A apresentação usa arredondamento decimal convencional; aumenta casas para não exibir valor não nulo como zero ou valores distintos como iguais. Isso não altera os números armazenados nem os cálculos. Até oito linhas são transcritas integralmente. Acima desse limite de apresentação, a conversa informa a quantidade de linhas e pergunta qual território examinar; não escolhe exemplos ou destaques. Uma menção inequívoca a um território existente restringe a leitura das linhas, sem recalcular nem retirar notas gerais.

“O que esse resultado significa?” recupera os fatos e, para densidade, as formas metodológicas pertinentes. “Explique de maneira mais simples” conserva os fatos e limitações, mas retira a expansão metodológica não solicitada. Depois de uma pergunta conceitual, a simplificação retoma o documento efetivamente usado, inclusive quando o histórico textual não é reenviado. Não foi criada uma nova explicação didática de método.

“Qual desses apresenta maior densidade?” lê a relação já calculada em Comparações. Se ela não existe, informa a necessidade e oferece **Preparar comparação**, condicionado ao pré-exame; a escolha prepara a operação existente e preserva a confirmação de execução. Pedido causal recebe a proposição documental de exclusão; não atribui motivo ao fenômeno. Texto analítico inventado no campo de cortesia do provedor nunca é usado.

### Delimitação da entrega

O resultado já pode ser explorado conversacionalmente nas três operações acima. A leitura analítica das demais operações retorna a forma autorizada de insuficiência, conservando o resultado na interface. Isso é uma **limitação desta implementação**, não ausência dessas funcionalidades no motor nem ausência de todo seu conteúdo documental no catálogo. Agregação, rotatividade, referência mais próxima, critérios e outras composições precisam de validação específica de seus qualificadores/alcances antes de habilitar a leitura pelo chat; a alternativa simples nesta entrega é a apresentação determinística existente. Para tendência temporal, permanece também a incompatibilidade anterior de classificação parcial com CAP-TEN-01, sem alteração do motor.

> Atualização de 19/10/2026: CAP-TEN-01 implementada no motor da evolução temporal (as sete classes da DA-15, o motivo de Sem classificação e a aritmética exata); ver [EVOLUCAO_TEMPORAL_E_TENDENCIA.md](Docs/EVOLUCAO_TEMPORAL_E_TENDENCIA.md). O texto acima registra o estado de 16/10/2026 e não foi reescrito.

A evolução não implementa a síntese geral de múltiplos entregáveis ou todos os contratos C/FN/CFG/V da SPEC. Não há segundo LLM, novo método, banco de dados ou dependência externa. As funções `_compute`, `compute`, regras de pré-exame, arquivos da base e configurações do Gemini não foram modificadas.

### Minimização e continuidade

No endpoint contextual, inclusive para clientes sem sessão, campos, valores e nome de arquivo/planilha identificados localmente são removidos do texto antes do provedor. A comparação reconhece caixa e acentos. Literais numéricos digitados também são substituídos, pois podem ter vindo de um resultado. Período e categoria explicitamente mencionados são recuperados **localmente** e novamente examinados; múltiplos candidatos exigem confirmação e nenhum é escolhido silenciosamente. O teste anterior de slots foi reforçado para verificar que seus valores não aparecem em nenhuma parte do payload externo, mantendo a conferência de recuperação dos parâmetros.

Os dados estruturados novos enviados ao provedor são apenas enums/estados de presença, operação anterior e referência documental. Não incluem nomes territoriais, IDs de resultado, tokens de sessão, hashes, linhas ou valores. A triagem nominal integral prevista na SPEC continua uma pendência do protótipo; esta minimização não é certificação de anonimização de texto livre. O contexto não permite perguntas sobre elementos visuais que não tenham representação estruturada.

## Comparação de comportamentos e evidências

A coluna “antes” resume a implementação diagnosticada, não transcrições de chamadas reais ao Gemini. A coluna “depois” descreve verificações automatizadas efetivamente executadas, com dados sintéticos, salvo a jornada geral da base Brasil expressamente indicada.

| Interação | Antes | Depois e evidência |
|---|---|---|
| Saudação repetida | Podia repetir apresentação e roteiro inicial | Resposta breve de continuidade; teste local de conversa |
| “Compare esses municípios” | Referente podia não ser reconhecido | Usa IDs da seleção atual sem calcular; API de exploração |
| “Não, quantidade” | Podia trocar indevidamente a capacidade | Mantém comparação e corrige indicador; API |
| “Acrescente Nova Vila” | Podia substituir o conjunto anterior | Preserva seleção e inclui município resolvido localmente; API |
| “E agora?” | Orientação genérica | Exibe seleção verificada e possibilidades do pré-exame; navegador com MANAUS/TEFE |
| “O que esse resultado significa?” | Sem recuperação do resultado apresentado | Referência do servidor, segmentos e formas PT; API e navegador |
| “Explique de maneira mais simples” | Sem referente confiável | Reduz expansão documental preservando fatos/notas; API e navegador; retomada documental testada sem histórico reenviado |
| “Qual desses apresenta maior densidade?” | Não havia leitura da relação produzida | Com comparação existente, verbaliza a relação A/B; sem relação, oferece preparação sem calcular; API |
| “Por que esse município apresenta densidade maior?” | Sem resposta ancorada no resultado | Mantém fatos, não inventa causalidade e apresenta exclusão documental; API |
| “Me traduz isso aí?” / “Pode destrinchar esse quadro?” | Sem caminho de intenção contextual de resultado | Transporte simulado identifica intenção e backend recupera fatos; **não é avaliação de compreensão pelo Gemini real** |

## Arquivos e decisões

| Grupo | Arquivos alterados/criados |
|---|---|
| Conversação e autoridade documental | `backend/llm_bridge.py`, `backend/document_catalog.py` |
| Sessão e integração | `backend/conversation_session.py`, `backend/llm_context.py`, `backend/main.py`, `backend/exploration.py` |
| Leitura de resultados | `backend/result_conversation.py` |
| Interface, sem redesenho | `frontend/src/conversationSession.ts`, `frontend/src/AnalysisAssistant.tsx`, `frontend/src/App.tsx`, `frontend/src/SessionPrivacy.tsx` |
| Testes | `backend/tests/test_document_conversation.py`, `test_conversation_guidance.py`, `test_conversation_session.py`, `test_result_conversation.py`, `test_llm_context.py`, `ui_conversational_smoke.py`, `ui_semantic_continuity.py` |
| Documentação | `README.md`, `Docs/REGISTRO_DE_COMPORTAMENTO.md`, `Docs/CONVERSACAO_INCREMENTO_FN.md`, este relatório e `Docs/DECISAO_CATALOGO_PT_20261016.md` |
| Autorização normativa delimitada | Oito linhas acrescentadas ao final de `IMPLEMENTATION_SPEC.md`; corpo original e catálogo preservados |

A decisão APT-20261016 autoriza apenas PT comprovado e resolve a dependência de aprovação EN para esta integração local. Todas as 703 formas-base PT foram comparadas com suas extrações normativas. O catálogo completo permanece byte a byte equivalente após normalização de fim de linha. EN continua bloqueado, inclusive traduções aparentemente atuais, pois a equivalência semântica não foi aprovada. A classificação geral de capacidades implementadas permanece no catálogo existente de operações, não é deduzida da existência de proposições normativas.

## Avaliação com Gemini real — ainda não executada

Nenhuma chamada externa ou paga foi realizada. Os testes simulados demonstram tratamento do contrato, referências, rejeição de conteúdo e recuperação; não demonstram a taxa de acerto ou diversidade linguística do provedor real. Uma avaliação posterior deve confirmar previamente disponibilidade gratuita e cota remanescente do provedor, sem presumir que a guarda local controla faturamento. Preservar modelo `gemini-3.5-flash-lite`, temperatura 0, 600 tokens, timeout de 22 segundos e limite local de 20 chamadas/dia; não reiniciar o processo para ampliar a cota.

Amostra pequena, com dados sintéticos: cortesia coloquial, explicação espontânea do resultado, correção de intenção e reformulação ambígua. Avaliar se a intenção foi reconhecida, se perguntou apenas quando necessário, se retomou o referente correto e se a resposta foi clara e sem repetição. Exigir zero fatos/valores novos, nenhuma perda de qualificadores e nenhum dado protegido no payload. Se o modelo falhar, manter os caminhos determinísticos, sem transformar o resultado simulado em aprovação de qualidade linguística real.

## Riscos residuais e continuidade

- Estado em memória de um processo: reiniciar o backend encerra as referências; múltiplos workers não estão suportados por este armazenamento.
- Limites de memória podem deixar um cálculo sem referência conversacional; a interface conserva o resultado e não encaminha um ID sem registro.
- Cota local é controle por processo, sem certificação de gratuidade do provedor. Configuração de produção não foi alterada.
- A geração de linguagem cotidiana é limitada a composições de cortesia sem conteúdo substantivo. O catálogo atual não contém todas as formas didáticas desejadas; naturalidade metodológica fica limitada à seleção/organização autorizada.
- Permanecem os desvios normativos preexistentes de canal de interação, classificação temporal, triagem nominal e cobertura integral dos contratos. Não foram resolvidos por afrouxamento da SPEC ou dos testes.
- O relatório de reavaliação já existente e não rastreado foi preservado, sem incorporá-lo automaticamente aos commits de produto.


## Validação final — 17/10/2026

| Verificação efetivamente executada | Resultado |
|---|---|
| Backend completo, `PYTHONUTF8=1`, `ADT_REAL_DATA_DIR` apontando à raiz, `python -m pytest -q -rs` | **481 aprovados; zero falhas; zero pulos**, 385,21 s. Saída final em `.local/conversacao-pytest-final.log` e código de saída 0 |
| Primeira regressão completa, antes dos últimos reforços e três testes adicionais | 478 aprovados, zero pulos, 485,36 s |
| Regressão direcionada depois do reforço de minimização e recuperação local | 85 aprovados; os ajustes posteriores também estão cobertos pela execução completa final de 481 |
| `npm run build` (TypeScript + Vite) | Aprovado; bundle principal acima do limiar de aviso do Vite, sem erro de build. Não foi executado novo `npm ci`; dependências não foram alteradas |
| `python backend/tests/run_ui_checks.py` | **10 jornadas aprovadas**, incluindo base Brasil versionada, exportação, seleção, critérios, mapas, histórico e continuidade; Chrome instalado |
| Repetição das suítes `gemini-simulado` e `conversa` após reforçar a minimização | **3 jornadas aprovadas**, sem chamadas externas |
| `python .github/scripts/verificar_governanca.py`, com `PYTHONUTF8=1` | Aprovado: registros de comportamento e todos os roteiros de navegador registrados |
| `python backend/brazil_data.py diagnostico` e comparação de hashes com o estado inicial | Integridade verificada; catálogo, dados e manifesto preservados |
| Comparação da AST de `compute`, `_compute` e `_result` com `f0c152d` | Implementações idênticas; nenhuma regra de cálculo alterada |
| `git diff --check` | Sem erros de whitespace |
| Gemini real | **Não executado**; nenhuma aprovação de qualidade linguística real ou de cota gratuita foi presumida |

Condições de ambiente: o build e os roteiros de navegador precisaram de execução com acesso ampliado para o esbuild e os processos locais do Chrome. Uma execução do verificador sem `PYTHONUTF8=1` falhou na decodificação cp1252; a execução em UTF-8 passou, sem alterar o verificador. Permaneceram dois avisos no pytest: depreciação do cliente Starlette/httpx e falta de permissão para gravar o cache do pytest no sandbox. Nenhum teste foi pulado ou relaxado por isso. Uma tentativa intermediária da última regressão foi interrompida antes de retornar o resultado; não foi contada como aprovação e foi substituída pela execução final registrada em arquivo.

## Registro Git

Branch de trabalho: `feat/novos-blocos-incrementais`. Referência remota conferida por `git ls-remote`: `f0c152d7222f6d8d53a5b1b7b2a2758ac0382dfe`. Commits locais dos incrementos 1 e 2: `94b8c59` e `8457f41`. Este relatório integra o commit do incremento 3, **feat: conversar sobre resultados verificados**; seu hash final consta na entrega e no `git log`. Não houve push, merge, reset ou alteração de outra branch. O relatório preexistente `Docs/REAVALIACAO_INCREMENTO_CONVERSACIONAL_20261016.md` permanece fora dos commits, preservado.
