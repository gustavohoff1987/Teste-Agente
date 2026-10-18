# Interface conversacional integrada

A investigação ocupa toda a largura disponível, até 1.920 px. O banner conserva o texto, as cores
e as proporções compactas. O personagem é o SVG original de `BrandAvatar.tsx`, reutilizado sem
alterar rosto, vestimentas, proporções ou cores. Não há personagem novo nem imagem gerada.

## Navegação e sessão

| Ação | Comportamento |
|---|---|
| Início | Volta ao banner e à apresentação do agente. Preserva sessão, conversa, preparação e resultados. |
| Nova sessão | Abre diálogo com exportação CSV, Imprimir / PDF, Continuar nesta sessão e Iniciar nova sessão. A confirmação revoga a sessão no servidor e recarrega a aplicação. |
| Nova análise | Abre o catálogo diretamente no primeiro uso; com análise em andamento, oferece análise independente ou acréscimo ao diagnóstico. |
| Histórico | Reabre resultados existentes, sem recálculo e sem restaurar parâmetros implicitamente. Identifica análise independente e componentes. Fecha por clique externo ou Escape. |
| Resultados | Oculta a preparação, expande e navega diretamente para o conteúdo calculado. Mantém conversa acessível e não altera dados nem executa análises. |

“Alterar a preparação” e “Voltar às opções” tornam os controles visíveis novamente. Os cinco
controles se distribuem em mais de uma linha em telas pequenas, sem menu lateral.
Diálogos nativos contêm o foco e devolvem-no ao controle acionador; Escape cancela. O encerramento
em andamento bloqueia novas confirmações. Falha de rede no encerramento mantém o diálogo e o
conteúdo da sessão, permitindo nova tentativa ou cancelamento.

Uma sessão pode conter diversas análises e diagnósticos. A transcrição, os arquivos importados,
as seleções, os parâmetros e os resultados ficam na memória da aba. Recarregar descarta o
histórico local. Encerramento e expiração continuam usando os limites e mecanismos existentes.
Nenhum grupo ou resultado é salvo no armazenamento persistente do navegador.

## Condução da investigação

O agente apresenta a escolha da fonte desde a entrada. Depois acompanha o reconhecimento,
associações e confirmações, escolha de modalidade, recortes, períodos e execução. A preparação
existente continua verificando requisitos no backend. O catálogo apresenta a disponibilidade
informada pelo pré-exame; requisitos ausentes podem ser examinados e resolvidos na preparação.

A conversa completa é expansível. Com ela recolhida, a mensagem recente fica junto ao campo de
digitação, em uma faixa contextual ancorada à base da janela dentro da investigação. O usuário
pode continuar perguntando durante a exploração de gráficos, mapas e tabelas. Alternativas de
interpretação permanecem acessíveis na conversa. Não há coluna reservada nem janela arrastável.

Os resultados indicam que os cálculos pertencem ao motor determinístico. O agente não altera
valores e o canal LLM continua recebendo apenas o conteúdo autorizado pelos contratos existentes.
Métodos, fontes e limitações permanecem nos componentes analíticos e no registro técnico avançado.
As preferências de movimento reduzido desativam transições, animações e rolagem suave.

## Análises independentes e diagnósticos

1. Executar a primeira análise cria uma análise independente identificada.
2. Nova análise → Iniciar uma análise independente preserva o resultado anterior no Histórico
   e abre uma preparação para outro grupo.
3. Nova análise → Acrescentar ao diagnóstico atual mantém o grupo atual; a próxima execução
   acrescenta um componente identificado, em ordem, com resultados e parâmetros próprios.
4. Abrir um componente conserva filtros e seleção visual desse resultado; o Histórico permite
   voltar a outro diagnóstico. O destaque territorial entre componentes continua condicionado à
   política já existente em `investigation.ts`.
5. Uma solicitação idêntica recupera o resultado existente. A organização pode referenciar esse
   resultado em outro grupo sem novo cálculo, sem duplicar linhas e sem mudar a identidade original.

Pedidos explícitos como “análise independente” ou “acrescente ao diagnóstico” definem somente a
intenção de apresentação no navegador. Prefixos explícitos como “Faça uma análise independente da”
e “Acrescente ao diagnóstico atual” são separados do pedido enviado ao interpretador local;
territórios, períodos e demais termos permanecem sujeitos às validações existentes. A mensagem
original permanece na conversa e no registro do pedido. A interpretação analítica mantém seus contratos. Se outra
execução puder modificar um diagnóstico e a intenção estiver indefinida, o diálogo pede apenas
essa escolha antes de calcular. Nenhuma interpretação executa cálculos automaticamente.

Compor não soma, combina, interpola, deduplica nem harmoniza valores. Cada componente conserva
fonte, recorte, categorias, períodos, unidades, método, limitações e parâmetros. Diferenças que
bloqueiam a coordenação territorial são indicadas nos cartões. Mesmo quando o destaque é
compatível, isso não certifica comparabilidade de valores. Resultados de fontes diferentes
continuam consultáveis individualmente; não há reinterpretação de unidades ou denominadores.

## Exportação

CSV exporta a tabela principal da análise em exibição. As tabelas de detalhe e as séries mantêm
seus controles próprios. O CSV filtrado continua exportando todo o filtro, conforme a tabela.
Imprimir / PDF usa a impressão do navegador e inclui a representação e a página da tabela em
exibição, mesmo quando o resultado está recolhido. O diálogo de Nova sessão não integra a impressão.

**Não existe exportação consolidada de todos os componentes por esses botões.** Para conservar
um diagnóstico ou sessão, reabra e exporte cada análise pelo Histórico. O diálogo explica essa
limitação antes do descarte. O JSON técnico mantém identidade, método, parâmetros e registro de
representação da análise e associação aos diagnósticos; fica somente em Opções técnicas avançadas.

## Componentes e fronteiras

- `App.tsx`: navegação, preparação existente, histórico e associação a diagnósticos.
- `diagnostics.ts`: referências ordenadas a resultados e intenção explícita de apresentação.
- `AnalysisAssistant.tsx`: transcrição expansível, escolhas, orientações e compositor contextual.
- `WorkspaceDialog.tsx`: confirmação acessível de análises e sessões.
- `PreviousAnalyses.tsx` e `InvestigationOverview.tsx`: consulta do histórico e componentes.
- `conversationSession.ts`: fechamento no servidor, incluindo criação de sessão ainda pendente.
- `workspaceNavigation.ts` e `styles.css`: fluxo único, responsividade, impressão e movimento reduzido.

Motor, API analítica, ponte semântica, manifesto, dados originais, SPEC e SVG do personagem não são
alterados. Testes e evidências estão no [relatório de rastreabilidade](RASTREABILIDADE_INTERFACE_INTEGRADA_20261017.md).
