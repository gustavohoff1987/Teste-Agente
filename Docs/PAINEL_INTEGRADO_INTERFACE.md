# Painel integrado de bolhas: a tela

Decisões do responsável pelo produto de 21/10/2026: a experiência analítica acontece dentro de um gráfico grande, ao qual o
usuário acrescenta municípios; a população aparece sempre no tamanho da bolha; os eixos dependem das análises escolhidas; a
taxa de crescimento em percentuais se integra ao desenho; o chat vira uma caixa com o rosto do agente que pode ser arrastada.
Este documento descreve a tela. O motor e as rotas (`/api/painel` e `/api/painel/referencias`) estão em
[Painel integrado de bolhas](PAINEL_INTEGRADO.md).

Nesta primeira entrega, o painel é aberto por um botão. A tela inicial e os fluxos atuais continuam como estavam; tornar o
painel a tela inicial fica para quando o responsável validar, porque mexe em todos os fluxos testados.

Código: `frontend/src/PainelIntegrado.tsx` (painel e barra das análises), `PainelChart.tsx` (gráfico, dica e legendas),
`PainelRuler.tsx` (régua), `PainelBase.tsx` (municípios base), `PainelGavetas.tsx` (distância, crescimento e conjuntos),
`ChatFloatingBox.tsx` (caixa da conversa), `painelModel.ts` (modelo puro) e `painelApi.ts` (cliente das rotas).

## Acesso

- **Botões:** "Abrir o painel integrado", junto da fonte atual na conversa, e "Painel integrado", na navegação principal.
  Os dois só aparecem com a base do Brasil pronta (abrangência oficial). Com um arquivo importado, vale o fluxo clássico.
- **Tela grande:** o painel ocupa a área principal, e o banner sai de cena enquanto ele está aberto.
- **Voltar:** "Voltar à preparação clássica" fecha o painel; a preparação, os resultados e a conversa estão como estavam.
  Início, Resultados, Nova análise, o Histórico e os pedidos da conversa que preparam uma análise clássica também fecham o
  painel.
- **Reabrir:** depois de aberto uma vez, o painel fica montado. Reabrir não recalcula e conserva o universo, os conjuntos,
  a referência e o crescimento.
- **Universo inicial:** o da abrangência clássica (todos os municípios, estados inteiros e municípios marcados). Sem
  escolha, todos os municípios quando a base tem até 300; acima disso, o painel pede a escolha.

## O que pede ao motor e o que é só estado visual

| Controle | Efeito |
|---|---|
| Densidade, Quantidade | Troca o indicador do eixo. Os dois valores já vieram do motor: nenhum pedido. |
| Escala do eixo (linear ou logarítmica) | Estado visual. A logarítmica só existe com todos os valores positivos, como no mapa. |
| Régua "acima de / abaixo de" | Filtro visual (RQ-REP-06). |
| Destacar (clique, Enter ou caixa na tabela) | Estado visual: os demais itens esmaecem. |
| Vista da competência inicial ou final, Reproduzir | Estado visual. |
| Ordenar a tabela pelo cabeçalho | Estado visual, sem posições (RQ-REP-03). |
| Municípios base, competência, categoria | Pedido a `/api/painel`. |
| Agregar selecionados, Desfazer conjunto | Pedido a `/api/painel`. |
| Listar candidatos (Distância) | Pedido a `/api/painel/referencias`, que só lista. |
| Usar o primeiro, Aplicar referência, Remover a distância | Pedido a `/api/painel`. |
| Mostrar crescimento, Remover crescimento | Pedido a `/api/painel`. |

- **Formulário:** o da base oficial (`dataset=brazil`, `scope=municipal`, `dataset_version`), com o mapeamento do perfil
  oficial (`mapping` vazio). As opções seguem o contrato à risca; o motor recusa chave desconhecida.
- **Sessão:** o pedido leva o cabeçalho da sessão, que registra o evento de confirmação. O resultado do painel ainda não
  entra na sessão da conversa.
- **Recusa do motor (422):** a mensagem aparece como veio, acima do gráfico, com "Voltar ao último painel calculado" (volta
  ao universo, aos conjuntos, à referência e às competências do painel em exibição, sem novo pedido) e "Tentar novamente".
  Exemplo: numa versão da base sem o referencial SIRGAS 2000 como premissa, o motor recusa a distância.
- **Atualização:** enquanto o motor responde, o gráfico anterior fica à vista, mais claro, e um aviso diz "Atualizando o
  painel no motor…".

## Barra das análises

- **Densidade e Quantidade:** escolhem o indicador do eixo.
- **Distância:** abre a escolha da referência por critério e acrescenta o eixo da distância.
- **Crescimento:** pede a competência inicial e mostra a variação em percentual.
- **Comparar / Conjuntos:** destaca dois ou três itens e cria conjuntos agregados.
- **Na preparação clássica:** Distribuição, Rankings, Critérios combinados, Rotatividade e Relatórios fecham o painel e abrem a
  preparação clássica daquela análise.

## Eixos e marcas

- **Sem distância:** eixo único horizontal do indicador. A altura das bolhas é só arranjo visual, e a tela diz isso abaixo
  do gráfico. O arranjo é determinístico: na ordem da posição, do raio e do código, cada bolha fica na menor distância da
  linha central sem se sobrepor às já colocadas.
- **Com distância:** X é a distância até a referência (km) e Y, o indicador. Com um conjunto de referência, o eixo diz "até o
  membro mais próximo da referência".
- **Tamanho:** população, com área proporcional (raio pela raiz quadrada) e diâmetro mínimo visível de 8 px. A legenda de tamanho traz
  três populações redondas (1, 2 ou 5 × 10ⁿ), desenhadas com o mesmo raio do gráfico.
- **Domínios:** os do motor, que já incluem os valores iniciais e a distância do membro mais distante dos conjuntos,
  enquadrados em números redondos; a escala linear começa no zero. Um domínio não é média nem classe: só enquadra o desenho.
- **Marcas finas:** anel de 2 px na cor da superfície, grade fina e sólida, alvo de pelo menos 24 px e as bolhas mais populosas
  atrás. A ordem de desenho não muda com o mouse, o foco ou o destaque, para nenhuma bolha saltar nem reiniciar o rastro.
- **Cores:** sem crescimento, a série única fica em azul-petróleo (`#008b9e`), conferido pela skill de visualização (faixa de
  luminosidade, croma e contraste). Com crescimento, só o divergente azul e laranja das tendências, conferido em todos os
  pares. O azul-petróleo e o azul nunca aparecem juntos, porque são próximos demais.
- **Conjunto:** anel escuro em volta e "(soma)" no rótulo. A dica e a tabela dizem "soma das contagens dos componentes, com
  possível dupla contagem" (RQ-REP-14). Com a distância, um traço horizontal vai do membro mais próximo ao mais distante.
- **Referência:** mira em volta das bolhas da referência, que ficam sempre à vista.
- **Rótulos diretos seletivos:** só nos itens destacados, nos conjuntos, na referência e na bolha sob o mouse ou em foco.
  O texto fica em tinta, nunca na cor da série, com contorno da superfície e afastado na vertical quando dois colidem, numa
  camada por cima de todas as bolhas.
- **Transições:** posição, raio e cor mudam em 0,6 s; com `prefers-reduced-motion`, nada se move.

## Régua dos municípios base

- **Cursores:** "acima de" e "abaixo de", sobre o indicador ativo, no domínio devolvido pelo motor. Aparecem só os municípios
  base dentro do corte, com os limites incluídos; conjuntos e membros da referência continuam à vista.
- **Mouse:** arrastar um cursor, ou clicar no trilho, que leva o cursor mais próximo até o ponto.
- **Teclado:** setas (um passo), Page Up e Page Down (dez passos), Home e End.
- **Passos redondos:** 1, 2 ou 5 × 10ⁿ perto de 1% do domínio, inteiros na quantidade e de pelo menos 0,01 nas medidas
  contínuas. Assim, o limite exibido com duas casas é o limite exato. Nas pontas, o cursor fica no valor exato do domínio.
- **Valores perto de um limite:** na dica e na tabela, ganham casas até não parecerem iguais a ele (RQ-REP-05).
- **"Mostrar todos":** desfaz o corte. Trocar o indicador, a competência ou o universo também desfaz.

## Municípios base

- **Universo:** "Todos os municípios", estados inteiros (seletor e etiquetas removíveis) e municípios acrescentados, na mesma
  forma da abrangência. Um estado inteiro absorve os municípios avulsos dele, e "Todos" absorve tudo.
- **Acrescentar:** pela busca (nome ou código) ou pela lista de um estado, com um clique; ou arrastando o item da lista para
  dentro do gráfico. A seleção acumula, e cada acréscimo é um pedido ao motor.
- **Universo vazio:** sem municípios base e sem conjuntos, não há pedido, e a tela pede a escolha. Com um conjunto, a base pode
  ficar vazia.

## Distância

- **Critério:** densidade, quantidade ou população, na ordem escolhida (maior para menor ou o contrário), entre os municípios
  base ou em todos os municípios. "Listar candidatos" mostra a lista do motor (CAP-SUB-02): valor, posição e empates na mesma
  posição (1, 2, 2, 4). Os não avaliáveis vêm à parte, com os motivos.
- **Escolha:** um município ou vários; vários formam um conjunto de referência, e a distância vai até o membro mais próximo.
  "Marcar os membros de um conjunto" marca os membros de um conjunto do painel.
- **"Usar o primeiro":** aplica a seleção por posição (CAP-SUB-03). Com empate na 1ª posição, a lista mostra só os empatados e
  pede a escolha.
- **Pedido:** a referência vai com o critério e o universo da lista, e a origem devolvida pelo motor cita a posição exata
  ("Escolhida pelo critério densidade (maior para menor), 1ª posição …"). A gaveta mostra a referência atual e "Remover a
  distância".

## Crescimento: o cometa

Opções consideradas:
1. halo colorido em volta de cada bolha;
2. rótulo de percentual em todas as bolhas;
3. cometa (rastro desde a posição na competência inicial);
4. destaque automático de quem mais cresceu ou caiu.

**Escolhas:** cometa, cor divergente contínua, rótulos seletivos e alternância animada entre as competências. Ficou de fora o
destaque automático.

- **Rastro:** mostra a mudança na própria escala do indicador. O comprimento é a diferença entre os dois valores observados e a
  direção é o sinal, enquanto a bolha continua no valor atual.
  - Liga só os dois valores observados da mesma unidade: um círculo vazado na competência inicial e a bolha na atual.
  - Não é reta de ajuste, projeção nem tendência.
  - A cauda é fina na origem e alarga até a bolha, com degradê de transparente a 60%.
- **Só com a variação do motor:** variação não avaliável não tem rastro.
  - A bolha fica vazada, com contorno tracejado, e o motivo vai para a lista à parte (RQ-REP-04).
  - Conjunto com membros diferentes entre as competências (`INCOMPARABILIDADE`) nunca ganha linha de trajetória (RQ-REP-15).
- **Arranjo pelos cometas:** no eixo único, cada cometa ocupa a faixa do valor inicial ao atual, e o arranjo evita a
  sobreposição dos cometas inteiros. A faixa é a mesma nas duas vistas, então alternar entre elas só desliza as bolhas na
  horizontal.
- **Cor:** divergente contínua pela variação do motor, azul para crescimento e laranja para queda (as cores das tendências; sem
  verde para "bom" nem vermelho para "ruim").
  - A intensidade é |variação| ÷ maior |variação| do domínio do motor.
  - Cada braço começa num tom claro já com matiz, para que o sinal de uma variação pequena continue visível (RQ-REP-05); só o
    zero é cinza.
  - É mapeamento contínuo, não classe (RQ-REP-02). A legenda mostra a escala do menor ao maior valor, simétrica no zero.
- **Rótulos:** "+12,40%" só nos destacados, nos conjuntos, na referência e na bolha em foco. Todos os valores ficam na dica e na
  tabela.
  - Duas casas, como toda medida contínua (RQ-REP-05): por isso "+12,40%", e não "+12,4%".
  - Sinal de menos tipográfico ("−3,00%"); um valor não nulo nunca aparece como zero.
- **Alternância:** "Competência inicial" põe cada bolha no valor observado na competência inicial, com o raio pela população de
  então. Os itens sem variação avaliável somem nessa vista, porque não têm posição observada a mostrar.
  - "Reproduzir do inicial ao final" desliza tudo em 1,4 s, e os rastros aparecem na chegada.
  - Com movimento reduzido, o botão vai direto à competência final.
- **Sem destaque automático:** apontar quem mais cresceu seria uma posição criada na tela (RQ-REP-01 proíbe rankings e destaques
  não estruturados). O usuário pode ordenar a tabela pela variação, que é estado visual sem posições (RQ-REP-03).
- **Competência inicial:** só as anteriores à competência do painel; a sugestão é o mesmo mês do ano anterior e, sem ele, a
  mais antiga.

## Dica, comparação, tabela e não avaliáveis

- **Dica:** ao passar o mouse e ao focar. Traz nome, município ou conjunto com a UF, população, profissionais, densidade (com a
  unidade, RQ-REP-11), distância e variação. O valor vem primeiro e o rótulo depois. Também traz os motivos e os avisos do
  motor, como o agregado parcial.
- **Comparar:** com até três itens destacados, cartões lado a lado mostram só os valores do motor, sem diferenças nem razões.
- **Tabela equivalente:** abaixo do gráfico, com os mesmos itens e os valores do motor. A ordem padrão é a do código
  territorial, e o clique no cabeçalho só reordena, sem criar posições. Cada linha tem a caixa de destacar.
- **Não avaliáveis:** lista à parte, por aspecto (indicador, distância, variação), com o motivo do motor. Os motivos são
  classificados pelo começo do texto, nunca pela posição na lista. "Sem registro em …" e "Nenhum membro do conjunto …" valem
  para todos os aspectos; o agregado parcial é aviso, porque o valor existe.
- **Notas, limitações e procedência:** as notas do motor, as limitações em texto (soma com possível dupla contagem, agregado
  parcial, distância geodésica direta, itens não avaliáveis), a origem da referência, as competências, a versão da base e a
  chave de execução.

## Conversa em caixa arrastável

- **Mesma conversa:** só no painel, a conversa fica numa caixa flutuante com o rosto do agente (`BrandAvatar`) no cabeçalho:
  última resposta, alternativas de esclarecimento e campo de envio. São o mesmo estado e os mesmos identificadores (`#assistente`,
  `#assistant-input`, "Enviar mensagem", `latest-reply`).
- **Fora do painel:** o layout do chat não muda.
- **Mover:** pelo cabeçalho, com o mouse ou o toque (pointer events), ou pelo teclado com o cabeçalho focado: setas movem
  16 px, Shift + setas 64 px e Home volta ao canto.
- **Limites:** a caixa fica sempre dentro da janela, também depois de redimensionar ou minimizar.
- **Minimizar:** sobra só o cabeçalho com o rosto.
- **Posição guardada:** a posição e o estado minimizado ficam no `localStorage` (`adt:painel-chat:v1`), sempre com try/catch.
  Sem armazenamento, valem só na tela.
- **Celular:** até 639 px, a caixa fica ancorada embaixo, de ponta a ponta, e o painel ganha espaço no fim para não ficar coberto.
- **Pedidos de análise:** a conversa no painel é a da preparação clássica. Um pedido que prepara uma análise abre a preparação
  clássica; a conversa ainda não conhece o universo, os conjuntos e a referência do painel.

## Acessibilidade

- **Gráfico:** uma parada de tabulação; as setas percorrem as bolhas da esquerda para a direita, Enter ou Espaço destacam e Esc
  fecha a dica.
  - Cada bolha é um botão com `aria-pressed` e um rótulo com os valores; a dica no foco é a mesma do mouse.
  - Foco visível em anel azul-claro.
- **Régua:** dois controles `role="slider"`, com valor, texto, mínimo e máximo.
- **Caixa da conversa:** cabeçalho focável, anúncio discreto ao mover e botão de minimizar com `aria-expanded`.
- **Equivalentes em texto:** tabela equivalente, não avaliáveis e notas em texto. Identidade nunca só pela cor: anel e
  "(soma)" no conjunto, mira na referência, contorno tracejado no não avaliável e sinal no percentual.
- **Movimento:** com `prefers-reduced-motion`, nenhuma transição e nenhuma animação.
- **Impressão:** saem o gráfico, as legendas, a tabela, os não avaliáveis e as notas; a barra, as gavetas, a régua, os
  municípios base e a caixa da conversa ficam de fora.

## Limitações desta entrega e próximos passos

- **Base:** só a base Brasil oficial.
- **Sessão:** o resultado do painel ainda não entra na sessão da conversa (próximo passo do motor).
- **Tela inicial:** tornar o painel a tela inicial depende da validação do responsável.
- **Conversa:** passar à conversa o estado do painel (universo, conjuntos e referência), sem dados da base ao provedor de IA.
- **Desempenho:** não foi medido com milhares de bolhas. O universo inicial só é "todos" até 300 municípios.
- **Tema:** a aplicação é toda clara; não há modo escuro.

## Testes

- **Modelo puro (Node):** `frontend/tests/painel.test.mjs`. Cobre:
  - formatação pt-BR da variação ("+12,40%", "−3,00%");
  - raio pela raiz da população e a legenda de tamanho;
  - régua com passos redondos e teclado;
  - arranjo sem sobreposição, inclusive dos cometas;
  - eixos por estado, distância e faixa do conjunto;
  - cometa e vista da competência inicial;
  - cor divergente;
  - não avaliáveis e motivos classificados pelo texto, com o agregado parcial como aviso;
  - rótulo da soma das contagens dos componentes;
  - "Usar o primeiro" com empate;
  - opções do pedido com os nomes do contrato e a tabela.
- **Navegador:** `backend/tests/ui_painel_integrado.py`, nas suítes `bloco1` (catálogo sintético) e `base-versionada`
  (`ADT_BLOCK1_REAL=1`). Confere:
  - abrir o painel: com todos os municípios no catálogo sintético (quatro) e, na base versionada, sem universo e sem pedido ao
    motor até a escolha do Amazonas inteiro;
  - densidade com eixo único e bolhas iguais às da resposta;
  - dica no mouse e no foco;
  - Quantidade sem novo pedido;
  - régua no teclado e no mouse;
  - municípios por busca e por arrastar;
  - conjunto agregado como bolha;
  - Distância com "Usar o primeiro": o eixo X na base versionada e, no catálogo sintético, a recusa do motor e a volta ao
    último painel;
  - Crescimento com os percentuais;
  - caixa da conversa movida com o mouse e o teclado, com o envio de mensagem funcionando;
  - 390 px sem rolagem horizontal;
  - a volta à preparação clássica.
