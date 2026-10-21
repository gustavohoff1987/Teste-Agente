# Preparação guiada — Teste-Agente

Na branch `feat/portal-uma-pagina-v1`, o chat é a área central do início.
O agente apresenta um carrossel compacto das dez análises, com setas de navegação.
Ao selecionar uma análise, a preparação guiada é aberta abaixo da conversa,
em um painel de largura integral e com rolagem própria. A seleção não executa
cálculos nem altera a matriz de aplicabilidade.

As etapas são **1. Identificar os dados**, **2. Parâmetros** e **3. Revisar e executar**.
Desde 21/10/2026, elas existem só nas bases importadas, em "Ajustar condições específicas ou situações excepcionais".
Na base oficial, a preparação tem apenas as Configurações. Nada sobre a estrutura da base é pedido, e o clique em
"Calcular e mostrar resultado" nomeia as escolhas da análise que faltam
([interface conversacional](INTERFACE_CONVERSACIONAL_INTEGRADA.md)). Só a etapa ativa é exibida. Não há confirmação de colunas e campos (decisão D1 do responsável
pelo produto, 19/10/2026): o usuário só escolhe. Cada campo mostra a origem do papel ("Reconhecida
pelo perfil oficial", "Reconhecida por regra" ou "Escolhida por você"); sem coluna, "Escolher
coluna"; com uma coluna indicada e não escolhida, "Escolha pendente". Os seletores trazem as
sugestões do backend no topo, marcadas "(sugerida)", e ficam vazios até a escolha. O código
territorial é opcional ("Sem código"), separado da unidade territorial; o período tem a opção "A base
tem um único período"; o objeto de análise é o texto informado, com o botão "Usar sugestão" quando o
cabeçalho sugere uma categoria. As escolhas ficam no estado do aplicativo, e não no componente de
cada etapa.

As pendências são distribuídas por etapa conforme a classificação do backend (`step` de cada
requisito; a interface não reescreve nem classifica textos). O contador "pend." conta só as escolhas
do usuário (`kind: "escolha"`); impedimentos nos dados (`kind: "dados"`) aparecem como "Impedimento
nos dados", sem contador. O selo dos requisitos diz "Escolha pendente". Na revisão, cada pendência
oferece um atalho para sua etapa. Os controles de preparação não se repetem na página de
resultados. Distribuição por densidade oferece a escolha da coluna de população na etapa de
parâmetros; o alinhamento do denominador é premissa aplicada pelo backend, com nota no resultado.
As antigas caixas "Confirmo…/Declaro…/Autorizo…" não existem mais: as premissas aparecem em
"Método e limitações". Falhas do pré-exame desabilitam a execução e permitem tentar novamente.

## Abrangência territorial e troca de análise

- Na base oficial (19/10/2026), não há troca de recorte: a base é examinada uma vez, no recorte
  municipal, com o bloco dos níveis (Brasil, estados e regras de cada análise). Trocar de análise não
  chama `/api/inspect`, não bloqueia a preparação e não troca de fonte; a opção "Abrangência da
  análise" das condições avançadas e a memória da preparação de cada recorte deixaram de existir.
- A caixa "Abrangência territorial" é uma lista vertical (Brasil, estados e municípios agrupados por
  estado). Os municípios marcados continuam valendo entre as análises; o Brasil e os estados só valem
  nas análises que os aceitam; sem nada aplicável, vale o padrão da análise. A interface envia a parte
  que vale em `options.abrangencia`, e o backend escolhe a rota e confere o pedido
  ([abrangência territorial](ABRANGENCIA_TERRITORIAL.md)).
- A escolha de períodos continua quando a análise de destino aceita o mesmo modo: o período único de
  uma densidade não substitui as competências de uma evolução temporal, que recebe todas as
  competências da abrangência (as da fonte nacional quando vale o Brasil).
- Na base Brasil sem o perfil oficial, a escolha entre o total nacional e os municípios continua no
  texto da preparação e recarrega a base no recorte escolhido, sem guardar a preparação anterior.
- Uma versão diferente invalida a preparação anterior. Novo upload, novo carregamento
  do Brasil e recarregamento da página não reutilizam escolhas de outra base.

## Verificações direcionadas

> **Atualização (15/10/2026):** `ui_preparation_smoke.py` usa a interface anterior ao redesenho
> conversacional e foi movido para `backend/tests/legado/`. A descrição abaixo registra o que ele
> verificava. A lacuna remanescente está listada no README daquela pasta.

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
de bundle acima de 500 kB. A classificação das pendências (`kind` e `step`) vem do backend
(19/10/2026); antes, a interface a deduzia dos textos. A autoridade de habilitação continua sendo a
matriz retornada pelo backend. O roteiro `ui_sem_confirmacoes.py` (suíte `bloco1`) percorre as 12
análises nas bases oficial e importada e confere que não há texto de confirmação nem premissa
enviada como `false`.
