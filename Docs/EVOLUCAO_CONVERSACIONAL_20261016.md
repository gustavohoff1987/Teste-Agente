# Evolução conversacional — execução autorizada em 16/10/2026

## Incremento 1 — fluidez e catálogo PT

A integração passa a materializar explicações de densidade, distância e agregação diretamente do catálogo PT, com identidade, versão, uso e autorização APT-20261016 retornados na resposta. O carregador verifica o catálogo íntegro e as 703 formas-base contra o Anexo A. EN está bloqueado; as formas não foram alteradas. Ver `DECISAO_CATALOGO_PT_20261016.md` e o adendo restrito ao final da SPEC.

O Gemini continua no mesmo modelo, temperatura, tokens, timeout e cota. Seu contrato distingue pedidos de explicação, simplificação, próximos passos e alterações de seleção/período. Cortesia admite composições linguísticas limitadas sem fatos, números ou alegações de ação; conteúdo fora desse domínio não é exibido. Nenhum segundo LLM ou validador universal foi acrescentado.

Uma saudação repetida não reinicia a apresentação. Referência explícita a um parâmetro pode alcançar mensagens anteriores, atravessando pergunta conceitual. Pedido de simplificação retoma o tópico documentado recente e reorganiza aspectos, sem inventar paráfrase ou omitir condições. As formas disponíveis limitam a simplificação: esta versão não acrescenta versões didáticas ao catálogo.

Textos operacionais legados não migrados continuam identificados como implementação parcial. A autorização PT não resolve a divergência de canal RQ-FLX-14 nem completa a classificação de tendência do motor.

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
