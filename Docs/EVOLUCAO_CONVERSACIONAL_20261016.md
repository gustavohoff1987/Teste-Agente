# Evolução conversacional — execução autorizada em 16/10/2026

## Incremento 1 — fluidez e catálogo PT

A integração passa a materializar explicações de densidade, distância e agregação diretamente do catálogo PT, com identidade, versão, uso e autorização APT-20261016 retornados na resposta. O carregador verifica o catálogo íntegro e as 703 formas-base contra o Anexo A. EN está bloqueado; as formas não foram alteradas. Ver `DECISAO_CATALOGO_PT_20261016.md` e o adendo restrito ao final da SPEC.

O Gemini continua no mesmo modelo, temperatura, tokens, timeout e cota. Seu contrato distingue pedidos de explicação, simplificação, próximos passos e alterações de seleção/período. Cortesia admite composições linguísticas limitadas sem fatos, números ou alegações de ação; conteúdo fora desse domínio não é exibido. Nenhum segundo LLM ou validador universal foi acrescentado.

Uma saudação repetida não reinicia a apresentação. Referência explícita a um parâmetro pode alcançar mensagens anteriores, atravessando pergunta conceitual. Pedido de simplificação retoma o tópico documentado recente e reorganiza aspectos, sem inventar paráfrase ou omitir condições. As formas disponíveis limitam a simplificação: esta versão não acrescenta versões didáticas ao catálogo.

Textos operacionais legados não migrados continuam identificados como implementação parcial. A autorização PT não resolve a divergência de canal RQ-FLX-14 nem completa a classificação de tendência do motor.

Testes novos: `test_document_conversation.py`. A expectativa antiga de “multiplicada por 1.000” foi substituída no teste de orientação pela fórmula canônica agora apresentada; o produto mudou deliberadamente para materialização literal, mantendo a cobertura de orientação sem provedor. Os testes novos conferem todas as formas-base, bloqueio EN, adulteração, condições, metadados e continuidade.

Validação inicial: 76 testes automatizados aprovados, sem chamadas externas. A primeira jornada de navegador identificou a mesma expectativa textual antiga em `ui_conversational_smoke.py`; o teste foi ajustado para conferir a fórmula canônica, sem remover a verificação de resposta na interface. Essa falha era uma expectativa desatualizada pela mudança deliberada, não um defeito de cálculo. A repetição da jornada foi aprovada.
