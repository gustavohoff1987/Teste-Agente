# Preparação guiada — Teste-Agente

Na branch `feat/portal-uma-pagina-v1`, a preparação reúne a seleção vertical das dez
análises e um painel com rolagem própria. Em telas pequenas, a lista fica acima do
painel. O chat, a importação e os resultados continuam na interface.

As etapas são identificação dos dados, parâmetros/confirmações e revisão/execução.
Só a etapa ativa é exibida. As confirmações ficam no estado do aplicativo, e não no
componente de cada etapa. Associações atendidas têm resumo e opção de edição.
O código territorial pendente fica visível, separado da unidade territorial.
As duas mensagens conhecidas de confirmação do código são agrupadas apenas na
apresentação; os critérios, erros de dados e algoritmos do backend não mudaram.

As pendências são distribuídas por etapa. Na revisão, cada pendência oferece um
atalho para sua etapa. Os controles de preparação não se repetem na página de
resultados. Distribuição por densidade agora oferece associação e confirmação da
população na etapa de parâmetros. Falhas do pré-exame desabilitam a execução e
permitem tentar novamente.

## Troca de abrangência

- A memória da aba guarda a preparação de cada recorte pela versão lógica da base.
- Retornar ao mesmo recorte/versão restaura associações, confirmações e parâmetros,
  submetendo-os novamente ao backend.
- Na primeira troca de recorte, somente período derivado e categoria com associações
  e domínios equivalentes são transferidos. Listas truncadas não comprovam equivalência.
- Território, código, unicidade da contagem, população e comparabilidade são específicos
  de cada recorte. Quando ainda não preparados nele, exigem nova conferência, com aviso.
- Uma versão diferente invalida a preparação anterior. Novo upload, novo carregamento
  do Brasil e recarregamento da página não reutilizam confirmações de outra base.

## Verificações direcionadas

`python backend/tests/ui_preparation_smoke.py` usa o catálogo local, respostas de
status da conversa simuladas e bloqueia chamadas de interpretação. Confere seleção,
etapas, pendência única de código, execução de densidade (5.570 municípios no recorte
202406), quantitativos nacionais (22 períodos), restauração municipal, bloqueio por
ausência de população no recorte nacional, resolução da população na distribuição,
falha/recuperação do pré-exame, tela de 390 px e upload internacional independente.
Evidências e capturas ficam em `.local/ui-validation/`, ignorada pelo Git.

Também foram selecionados quatro testes existentes: confirmação de objeto,
recusa de cálculo não confirmado, confirmações do catálogo e rejeição de versão
desatualizada/origem inválida. Não foi executada a suíte completa.

O frontend foi compilado com TypeScript e Vite. Permanece o aviso não impeditivo
de bundle acima de 500 kB. A classificação visual das pendências utiliza as mensagens
atuais do backend; mudanças nesses textos devem atualizar essa classificação. A
autoridade de habilitação continua sendo a matriz retornada pelo backend.
