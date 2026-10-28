# Registro de mudanças de comportamento

Este registro guarda, em ordem cronológica, **toda mudança no que o usuário ou um consumidor da API
observa**. Isso inclui telas, fluxos, mensagens, cálculos, valores padrão, validações, exportações,
contratos da API e dados versionados. **Remoções de funções também entram.** Vale para qualquer autor:
pessoas, Claude, Codex ou envio de arquivos pela web do GitHub.

Vigência: commits posteriores a `dbaa0bd` (15/10/2026). O comportamento anterior está descrito no
`README.md` e nos documentos temáticos de `Docs/`.

## Como cumprir a regra

1. **Mudou comportamento:** no **mesmo commit**, acrescente uma entrada abaixo (a mais recente
   primeiro) e atualize o documento temático correspondente (`README.md` ou `Docs/...`).
2. **Alterou arquivos do produto sem mudar comportamento** (refatoração, ganho de desempenho sem
   efeito visível, atributo usado só por testes): escreva na mensagem do commit a linha
   `Comportamento: sem alteração — <motivo>`. Pela web do GitHub, use o campo de descrição do commit.
3. **Commit já publicado sem registro:** acrescente aqui uma entrada que cite o hash curto dele.
   O histórico não precisa ser reescrito.

O job `governanca` do CI (`.github/scripts/verificar_governanca.py`) recusa commits que alterem
`frontend/`, `backend/` (fora de `backend/tests/`), `dados/` ou os arquivos de dados da raiz sem
cumprir uma das três opções. Para conferir antes do push: `python .github/scripts/verificar_governanca.py`.

### Modelo de entrada

```markdown
### AAAA-MM-DD · `hash curto` · título curto
- **Antes:** como funcionava.
- **Agora:** como passa a funcionar.
- **Permanece:** o que continua igual e poderia parecer afetado.
- **Motivo:** decisão ou defeito que levou à mudança.
- **Documentação e testes:** o que foi atualizado junto.
```

## Entradas

### 2026-10-28 · Tipografia: a Inter embutida, a escala com piso, a marca em destaque e os balões do agente inteiros
- **Classificação (regra 1), pela leitura, antes de codar:** pedido do responsável (28/10/2026): "da Força de Trabalho na Saúde"
  muito miúdo, que pode aumentar "um pouquinho", continuar menor que "Agente Diagnóstico Territorial" e ganhar uma estética
  diferenciada ("parecendo uma simples digitação de máquina de escrever"); o mesmo para as letras pequenas em geral, em todas as
  camadas, inclusive a conversa, sem prejuízo ao motor nem às funcionalidades e sem latência nova. Itens (todos mudança de
  comportamento, o que se vê na tela, e previstos: decorrem do pedido, escopo, e não contrariam a SPEC nem divergência aprovada,
  compatibilidade): a fonte; a escala; a marca; a conversa; e, achados na auditoria independente de um agente especialista em
  interface, os balões do agente cortados e os textos pequenos abaixo de 4,5:1 no modo claro, que a legibilidade pedida inclui. A
  SPEC não fixa tipografia; a "ampliação experimental da tipografia operacional" de 18/10/2026 (`3575484`) saiu na reversão em bloco
  da tentativa de simplificação, não por decisão sobre a letra; a letra das mensagens da conversa (15/14 px, 26/10/2026) continua e
  passa a valer também nos balões do agente. Nenhum texto, valor, cálculo, fluxo ou contrato muda.
- **Antes:** as folhas pediam a fonte "Inter" sem carregá-la: cada aparelho mostrava a fonte do sistema (no Windows, a Segoe UI), e
  os pesos 650 e 750 viravam 600, 700 ou 900. Cerca de 150 declarações de tamanho de letra entre 9 e 12 px (sobretítulo do banner a
  10 px, "Privacidade da conversa" a 10 px, notas, legendas, rótulos de campos, aviso de serviço e cabeçalho da conversa a 11 e
  11,5 px; `text-xs` a 12 px). A marca: "Agente Diagnóstico Territorial" a 19 px e "da Força de Trabalho na Saúde" a 12 px, em cinza.
  Os balões do agente herdavam a classe da antiga "última resposta" (`latest-reply`): letra de 13 px (a da pessoa, 15 px), resposta
  longa cortada em 140 px (90 px no celular), com rolagem dentro do balão, e a hora numa coluna ao lado do texto. No claro, textos em
  turquesa a 4,3:1 no branco, cabeçalhos de tabela em #6b8494 (3,9:1), rodapé em slate-400 (2,4:1) e texto de exemplo dos campos a
  2,5:1.
- **Agora:** a Inter 4 variável (peso e tamanho óptico) vem embutida no app (`frontend/src/tipografia/`, subconjuntos latino e
  latino estendido, licença OFL), com `font-display: swap` e nenhuma requisição externa; sem a suavização que afina o texto no Mac.
  Escala por papéis, em pixels inteiros: legenda 12 px, apoio 13, corpo 14, leitura 15 (a frase-resumo); piso de 12 px, com 11,5 px só
  em rótulos em caixa alta e nos números dos eixos e da rampa do mapa; rótulos de campos em 13 px seminegrito; `text-xs` do Tailwind
  12 → 13 px. A marca: o nome em 20 px e "da Força de Trabalho na Saúde" em 14 px, seminegrito, no turquesa de texto da identidade,
  com o "da" mais leve, no tom de apoio (17 e 13 px no celular); o rosto do agente em 44 px. No desenho, rótulos das bolhas e títulos
  dos eixos em 12,5 px, com a largura estimada dos rótulos ajustada; nomes no mapa em 12 px na Inter, medidos de novo quando a fonte
  chega. Na conversa, os balões do agente mostram a resposta inteira, em 15 px, com a hora embaixo; sobem o cabeçalho da caixa
  (15 px), a linha de apoio (12 px), o aviso de serviço (13 px; 12 no celular), a hora (12 px), "Enter para enviar" e "Privacidade da
  conversa" (12 px) e o campo de mensagem (15 px; 16 no celular, sem zoom ao focar). No claro, os textos pequenos em turquesa usam o
  turquesa de texto (`text-teal-texto`), o cinza de apoio passa a #587080, o rodapé usa o tom de apoio e o texto de exemplo dos
  campos, esse cinza.
- **Permanece:** os textos, os valores, os cálculos do motor, os fluxos, as cores da identidade nas bordas e fundos, o modo escuro
  (variáveis e contraste), a letra das mensagens da conversa, a impressão clara, o celular sem rolagem horizontal e os contratos da
  API.
- **Motivo:** pedido do responsável (28/10/2026), com a preocupação de não perder desempenho: só CSS e um arquivo de fonte do próprio
  app, carregado uma vez.
- **Documentação e testes:** `README.md` (interface), `Docs/PAINEL_INTEGRADO_INTERFACE.md` (seção nova "Tipografia" e os testes) e
  `Docs/INTERFACE_CONVERSACIONAL_INTEGRADA.md` (a tipografia da conversa e os balões). Testes novos:
  `frontend/tests/tipografia.test.mjs` (a fonte embutida e sem URL externa, o piso e os inteiros nas folhas e no Tailwind, a marca, a
  conversa, os balões, a largura estimada dos rótulos, a nova medida dos nomes do mapa e o contraste no claro dos textos pequenos) e,
  em `backend/tests/ui_pagina_unica.py`, a Inter carregada do próprio servidor, a marca e nenhuma letra à vista abaixo do piso
  (auxiliares `fonte_embutida_carregada` e `letras_miudas` em `ui_support.py`). Nenhum teste afrouxado.

### 2026-10-28 · Planilha enviada: os nomes dela em todos os lugares, com a concordância, e o grupo reconhecido na conversa
- **Classificação (regra 1), pela leitura, antes de codar:** pedido do responsável (28/10/2026): testar com dados fictícios,
  preenchendo o modelo de planilha, enviando-o e navegando como usuário, se onde a base do Brasil diz município, estado e
  Brasil a planilha mostra os nomes dela, "mantendo a organização natural semântica das frases". A navegação simulada
  (16 comunas inventadas em 4 condados, nenhum nome do Brasil) achou textos que não seguiam os nomes ou a concordância da
  planilha, um recurso da conversa que não funcionava numa planilha enviada pela página e textos próprios da base do Brasil.
  Todas as correções são mudanças previstas: decorrem do pedido (escopo) e não contrariam a SPEC nem divergência aprovada
  (compatibilidade): a SPEC não fixa esses textos, a CAP-REP-06 não exige uma coluna "UF" e o reconhecimento do grupo pelo
  nome já estava descrito em `Docs/CONVERSACAO_INCREMENTO_FN.md` ("mostre a província X"). Ficaram como estão, de propósito:
  os exemplos explicativos do painel "Colunas", a escolha "Usar dados do Brasil", as chaves do contrato da API no JSON dos
  parâmetros (agora explicadas por uma linha), os "três estados" da CAP-SUB-01, o "estado atual do gráfico" e o masculino
  genérico de "os dois" e "os três" dos itens.
- **Antes:** numa planilha de comunas (feminino), a ajuda das Condições dizia "os que não atendem"; a Escolha dos territórios,
  "Todos que atendem (N)" e "Só os que eu marcar"; a linha da base, "cada um ligado à sua referência mais próxima"; "Entenda
  esta análise" da Análise Espacial, "a referência mais próxima delea" e "todos os que atendem"; os títulos, "· Planilha ·"; o
  CSV tinha a coluna "UF", vazia; o método mostrava as chaves "municipios" e "estados" sem explicação. Na conversa, a
  orientação oferecia "voltar ao nível de condados", que a conversa recusa; "Mostre só o condado Costa Ondina" respondia
  "Não encontrei “Costa e Ondina” entre as comunas da base.", porque a página não mandava o papel `grupo_territorial` no
  mapeamento da conversa; as respostas verificadas diziam "Empatados", "Os demais", "Todos os comunas com valor", "todos os
  comunas da base", "os comunas de Alto Vésper" e "2 comunas escolhidas um a um"; no mapa, "cada ponto é um município, na coordenada da sede municipal"; sem gráfico, o exemplo "o nome de um estado ou de
  municípios"; nos exemplos, "o município de maior densidade", "desses municípios", "os municípios com densidade menor que 1"
  e, nas recusas de juízo, de classe nova e de escolha delegada e no "desfaz" sem mudança, "os municípios"/"os 5 municípios";
  a pergunta de volta de uma escolha pedia "a sigla do estado".
- **Agora:** a ajuda das Condições diz "Separa as comunas que atendem a todas as condições escolhidas, as que não atendem e as
  que não têm dado para avaliar."; a Escolha dos territórios, "Todas que atendem (N)" e "Só as que eu marcar"; a linha da
  base, "cada uma ligada"; "Entenda esta análise", "a referência mais próxima dela" e "a escolha de todas as que atendem ou só
  das marcadas"; o lugar de uma planilha inteira é "Toda a planilha" ("Tendência da densidade de médicos · Toda a planilha ·
  …"); o CSV tem a coluna do grupo com o nome dele ("Condado") e o valor da coluna-mãe (o motor já devolvia
  `grupo_territorial`), sem coluna quando a planilha não tem grupo; o método traz, antes dos parâmetros, "Os nomes das chaves
  abaixo são os do contrato da API, iguais em toda fonte: nesta planilha, “municipios” são as comunas, e “estados”, os
  condados.". Na conversa, a orientação diz "… ou mostrar as comunas de um condado."; a página manda `grupo_territorial` no
  mapeamento da conversa (`mapeamentoDaConversa`), e "mostre só o condado Costa Ondina" mostra as 4 comunas dele; as respostas
  usam os nomes e o gênero da planilha ("Empatadas", "As demais", "Todas as comunas com valor", "todas as comunas da base",
  "as comunas de Alto Vésper", "2 comunas escolhidas uma a uma"); no mapa, "cada ponto é uma comuna, na coordenada informada na planilha"; sem gráfico, "o nome de um
  condado ou de comunas, ou “todas as comunas”."; os exemplos, "a comuna de maior densidade", "dessas comunas", "as comunas
  com densidade menor que 1" e "as 5 comunas com maior densidade"; a pergunta de volta pede "o nome ou “o primeiro”, “o
  segundo”".
- **Permanece:** a base do Brasil (os mesmos textos, "UF" no CSV e a sede municipal no mapa); os cálculos, as contagens e as
  respostas do motor; o pré-exame (o grupo continua em `hierarchy_columns`, fora do mapeamento); o contrato da API; os dados e
  a SPEC.
- **Motivo:** pedido do responsável (28/10/2026): numa planilha de outro lugar, município, estado e Brasil são nomes da
  organização brasileira e devem dar lugar aos nomes da planilha, com o mesmo sentido das frases.
- **Documentação e testes:** `README.md` (os nomes da planilha em todos os lugares, o CSV e o job `ui-block1`),
  `Docs/PAINEL_INTEGRADO_INTERFACE.md` (a Escolha dos territórios, a linha da base, o título, a exportação, a seção nova "Os
  nomes de uma planilha" e o roteiro novo) e `Docs/CONVERSACAO_INCREMENTO_FN.md` (o grupo no mapeamento da conversa, a
  orientação e as respostas). Testes novos: `backend/tests/test_rotulos_da_planilha.py` (uma planilha fictícia de comunas e
  condados no motor: os extremos, a seleção e o mapa, os exemplos sem gráfico e com ele, as recusas e a pergunta de volta, com
  comunas, distritos e a base do Brasil) e o roteiro de navegador `backend/tests/ui_planilha_ficticia.py`, registrado na suíte
  `bloco1` (baixa o modelo pela tela, preenche-o com 16 comunas inventadas, envia e percorre a página, conferindo que nada à
  vista traz município, UF, IBGE, Brasil ou as concordâncias de antes). No frontend, testes novos em
  `areaDeAnalise.test.mjs` (a nota das chaves no método, "dela" e "todas as que atendem", "cada uma ligada", a coluna
  "Condado" no CSV e nenhuma coluna sem grupo), em `conversaGrafico.test.mjs` (a orientação de uma planilha) e em
  `paginaUnica.test.mjs` (`mapeamentoDaConversa`). Alterados por mudança intencional de texto, nenhum afrouxado:
  `painel.test.mjs` ("Planilha" passou a "Toda a planilha") e `conversaGrafico.test.mjs` (a orientação de uma planilha de
  distritos: "… ou mostrar os distritos de uma província.").

### 2026-10-27 · Escolha dos territórios: a referência diz de quem é a mais próxima, e a Referência mostra candidatos e usadas
- **Classificação (regra 1), pela leitura, antes de codar:** relato do responsável na navegação (27/10/2026): base "municípios
  da Bahia com densidade abaixo de 0,5 e população acima de 10 mil" (só PILAO ARCADO (BA)) e referência "densidade acima de 1,5"
  na Bahia. A frase "o mais próximo da Bahia com densidade acima de 1,5" deixou a dúvida "é o mais próximo da Bahia ou do
  município base?", e a aba Referência dizia "175 municípios" quando só um (ITAGUACU DA BAHIA (BA), a 112,20 km) é a
  referência. Duas mudanças de texto, previstas: decorrem do relato (escopo) e não contrariam a SPEC (compatibilidade): a SPEC
  não fixa a frase (o exemplo "o mais próximo do Acre com densidade acima de 2" veio do comando do próprio responsável) e
  distingue o conjunto de referência (CAP-REF-01) da referência mais próxima de cada unidade-alvo (CAP-ESP-02), que a tela
  passa a mostrar separados. O motor já calculava certo (um só membro usado); nenhum cálculo muda. Terceiro ponto do relato, a
  bolha de PILAO ARCADO esmaecida: a leitura do código não achou regra que esmaeça a única bolha da base sem Condições
  ("não atende"), Ordenação ("demais") ou, no mapa, a régua ou os filtros visuais; fica em consulta ao responsável, sem
  mudança neste commit.
- **Antes:** na referência, "o mais próximo do Acre com densidade acima de 2" (território fixo), "o mais próximo com densidade
  acima de 1,5, na mesma UF", "o mais próximo, na mesma região", "o mais próximo, em qualquer estado" (numa planilha, "em toda
  a planilha" e "na mesma {grupo}") e, com marcados, "o mais próximo entre MANAUS (AM) e BELEM (PA)" ou "MANAUS (AM), na mesma
  UF". Na aba Referência, o status "175 municípios" e a prévia "175 municípios podem ser referência: …".
- **Agora:** a referência diz de quem é a mais próxima e entre quais: "o mais próximo de cada um, entre os municípios da Bahia
  com densidade acima de 1,5"; "… entre os municípios de todo o país" (numa planilha, "de toda a planilha"); conforme a base,
  "… entre os municípios do mesmo estado …" ou "da mesma região" (numa planilha, "da mesma {grupo}"); com marcados, "o mais
  próximo de cada um, entre MANAUS (AM) e BELEM (PA)" (conforme a base, com ", no mesmo estado" ou ", na mesma região") e, com
  um só, "MANAUS (AM)" ou "MANAUS (AM), para os municípios do mesmo estado". Na aba Referência, o conjunto é dito como
  candidatos: o status "175 candidatos" e a prévia "175 candidatos a referência: …"; embaixo da prévia, a linha
  `territorios-referencia-usadas` diz a regra antes do cálculo ("Para cada município da base, só o candidato mais próximo fica
  como referência.") e, com o resultado em dia, quais o motor usou (`referencia.membros`): "Ficou como referência 1 dos 175
  candidatos: ITAGUACU DA BAHIA (BA), o mais próximo de PILAO ARCADO (BA)." ou, no exemplo do comando, "Ficaram como
  referência 2 dos 3 candidatos: CRUZEIRO DO SUL (AC) e RIO BRANCO (AC), cada um o mais próximo de algum município da base."
  (sem candidatos, "Sem candidatos, nenhum município da base tem referência."). A frase nova aparece também no resumo dos ajustes
  (`analise-referencia-resumo`).
- **Permanece:** o cálculo (a referência mais próxima de cada município da base, nunca ele mesmo, com os empates), as
  contagens do motor em cada etapa ("22 municípios", "3 municípios restam"), a base na frase, o resultado, a linha da base e da
  referência acima do desenho, as notas do motor nos Detalhes, os dados e a SPEC.
- **Motivo:** relato do responsável (27/10/2026): a frase e a contagem da Referência levavam a ler o conjunto de candidatos
  como a referência.
- **Documentação e testes:** `README.md` (referência geográfica mais próxima) e `Docs/PAINEL_INTEGRADO_INTERFACE.md` (a frase,
  o status das abas, a prévia, candidatos e referências usadas). Testes alterados por mudança intencional de texto (nenhum
  afrouxado): no frontend, o teste "escolha dos territórios" (as frases novas, o caso da Bahia, os marcados conforme a base,
  `quantosCandidatos` e `textoDasReferenciasUsadas` em todos os casos); no navegador, `ui_area_de_analise.py` (as frases, o
  status e a prévia da Referência como candidatos, a regra antes do cálculo, as referências usadas depois dele e "Sem
  candidatos" na referência vazia) e `ui_mapa.py` (as frases conforme a base e de todo o país).

### 2026-10-27 · Análise Espacial: sai o filtro de distância da Escolha dos territórios
- **Classificação (regra 1), pela leitura, antes de codar:** remoção de função pedida pelo responsável (27/10/2026: a distância
  maior ou menor "a gente vai acabar vendo no próprio gráfico", no eixo X). Mudança prevista: decorre do pedido (escopo) e não
  contraria a SPEC (compatibilidade). A SPEC não exige o filtro na janela; a distância até a referência mais próxima continua
  calculada para cada município da base (CAP-ESP-02), à vista no eixo X, e filtrável pelas Condições (CAP-SUB-01, `distancia_km`),
  pela Ordenação e pelas faixas de distância (CAP-ESP-03). A decisão "seguir a SPEC" de 27/10/2026, sobre o município sem
  referência no recorte com o filtro (fora da base, listado), perde o objeto; vale a regra sem filtro: ele entra com a distância
  não avaliável e o motivo.
- **Antes** (desde `63d492c`): a aba Base tinha "+ Distância" ("Distância até a referência mais próxima", "acima de" ou "até", em
  km, com o aviso "depende da Referência"); com a referência incompleta, a base ficava pendente ("complete a referência para usar
  o filtro de distância"); a frase dizia "a mais de N km da referência" ou "a até N km da referência". O motor aceitava
  `indicador: "distancia"` na base, cortava a base pela distância nas contagens da janela (`/api/painel/territorios`, onde o
  referencial que faltava virava pendência da base) e no cálculo, e listava em `referencia.sem_referencia` quem ficava de fora
  porque a distância não era avaliável (na tela, o aviso `analise-sem-referencia-no-recorte`; nas notas, "N municípios ficaram
  fora da base porque o filtro de distância não é avaliável …"); as contagens da base traziam `sem_referencia`.
- **Agora:** a aba Base tem os mesmos filtros da Referência (densidade, população e quantidade), e a frase da base não fala de
  distância; cada lado depende só das próprias etapas. O motor recusa `indicador: "distancia"` com "O filtro de distância saiu da
  Escolha dos territórios: a distância até a referência mais próxima de cada município da base aparece no eixo X do resultado;
  para filtrar por ela, use as Condições."; as contagens da janela não medem distância (sem `sem_referencia` e sem a pendência do
  referencial, que continua pedido no cálculo); a resposta não traz `sem_referencia`; o aviso e a nota de quem ficava fora da
  base saíram. O município sem referência no próprio recorte continua na base, com a distância não avaliável e o motivo ("Sem
  referência no recorte: …"), fora do gráfico e no mapa. "Entenda esta análise" não cita mais o filtro.
- **Permanece:** a distância de cada município da base até a referência mais próxima (geodésica, nunca ele mesmo, com os empates),
  o eixo X, a dica, a tabela, o CSV, o mapa e as ligações; as Condições com a distância (no exemplo do comando, com a base
  versionada: dos 40 municípios do Norte com densidade abaixo de 0,5, os 38 a mais de 300 km da referência do Acre atendem a
  "distância à referência mais próxima > 300 km"); a Ordenação e as faixas de distância; o resto da janela; os dados; a SPEC.
- **Motivo:** pedido do responsável (27/10/2026): a distância maior ou menor aparece no próprio gráfico, no eixo X, e o filtro
  na janela não tinha por que existir.
- **Documentação e testes:** `README.md` (referência geográfica mais próxima), `Docs/PAINEL_INTEGRADO_INTERFACE.md` (o seletor,
  a frase, o que a janela não tem, o município sem referência no recorte, o pedido e os testes) e `Docs/PAINEL_INTEGRADO.md`
  (os filtros, as pendências, a seleção, a distância, a resposta e a rota 4). Testes alterados por mudança intencional (o
  comportamento mudou de propósito; nenhum foi afrouxado): em `test_painel_pagina.py`, as conferências do filtro de distância
  deram lugar à recusa com a mensagem nova (na validação, na rota das contagens e no teste da referência conforme a base), às
  Condições com `distancia_km` sobre a consulta (os três estados: quem não tem distância fica `NAO_AVALIAVEL`) e às contagens sem
  `sem_referencia`; `test_consulta_reference_follows_the_base_and_the_distance_filter_never_hides_a_municipality` passou a se
  chamar `test_consulta_reference_follows_the_base_and_never_hides_a_municipality` (a mesma cobertura da referência conforme a
  base, com as Condições no lugar do filtro); o teste do exemplo do comando com a base versionada confere, sem o filtro, que os
  de mais de 300 km aparecem pela distância do resultado e pelas Condições; o da planilha confere que as contagens não dependem
  do referencial. No frontend, o teste "escolha dos territórios" (o exemplo sem o filtro, a distância recusada nos dois lados,
  os filtros só de densidade, população e quantidade, as respostas sem `semReferencia`). No navegador, o passo 9 de
  `ui_area_de_analise.py` (sem o botão "+ Distância"; a referência incompleta sem prender a base; a referência vazia com todos
  os da base sem distância e o aviso `analise-ref-sem-resultado`).

### 2026-10-27 · Conversa: o pedido guardado antes dos dados sai com a revisão de contexto da fonte nova
- **Classificação (regra 1):** correção de um defeito achado pelo CI (execução 409, roteiro `ui_conversa_grafico.py` nas suítes
  `conversa` e `gemini-simulado`). Mudança prevista: o que o sistema deve fazer continua o documentado em 26/10/2026 (o pedido
  feito antes dos dados segue sozinho quando a base fica pronta; AT-64, pedido preservado sem repetição); a correção faz a tela
  cumpri-lo sempre.
- **Antes:** a revisão de contexto da sessão mudava num efeito da página, que o React roda depois dos efeitos da conversa e da
  área. O pedido guardado, retomado no mesmo ciclo em que a fonte ficava pronta, saía com a revisão antiga, e a nova revisão
  chegava antes ao servidor: a conversa respondia "A seleção mudou. Envie o pedido no contexto atual." em vez de seguir com o
  pedido (dependia da ordem de chegada dos dois pedidos; em 26/10/2026 passou no CI, em 27/10/2026 falhou nas duas suítes).
- **Agora:** a revisão muda no momento em que a fonte é aplicada (`ativar`, em `App.tsx`), antes de a página desenhar a nova
  fonte: o pedido guardado e os primeiros pedidos com a fonte já saem com a revisão nova, e as respostas em trânsito da fonte
  anterior continuam descartadas.
- **Permanece:** a regra da revisão (uma por fonte em uso), o descarte das respostas tardias, os textos da conversa, o
  lembrete da base e a sessão temporária.
- **Motivo:** o CI da execução 409 (passo 3 de `ui_conversa_grafico.py`: "Com os dados prontos, sigo com o seu pedido." não
  aparecia).
- **Documentação e testes:** a regra documentada não mudou (`README.md`, ajustes da conversa de 26/10/2026); o roteiro
  `ui_conversa_grafico.py` (passo 3), sem alteração, confere a retomada nas duas suítes.

### 2026-10-27 · Análise Espacial: Escolha dos territórios (base e referência irmãs, seletor em três etapas, contagens do motor) no lugar do Território de referência e dos territórios base
- **Classificação (regra 1), pela leitura, antes de codar:** os itens decorrem do comando do responsável "Seleção de
  Territórios" (27/10/2026).
  - **Janela, frase-resumo, abas e rodapé (mudança 1):** mudança prevista. A referência continua definida pelo usuário, por
    lista ou por critério (CAP-REF-01), e a distância continua a geodésica até a referência mais próxima do conjunto completo
    (CAP-ESP-01 e CAP-ESP-02), com a nota TPL-11; a SPEC não fixa a forma da janela.
  - **Seletor em três etapas com contagens do motor (mudança 2):** mudança prevista. Partir de é o recorte do universo
    (CAP-UNI-01); os filtros são condições atômicas combinadas por E, em três estados (CAP-SUB-01); toda contagem vem do motor
    (RQ-REP-09); a escolha pelos marcados é a lista de CAP-REF-01.
  - **"Conforme a base" só na referência, sem ranking, sem OU/NÃO, só a geodésica (mudança 3):** mudança prevista (a regra
    "no mesmo estado de cada município" de 24/10/2026 continua, com o rótulo novo).
  - **Duas dúvidas levadas ao responsável antes de implementar:** (1) o comando dizia que o município sem referência no
    próprio recorte "atende a 'acima de' e não atende a 'até'" no filtro de distância, o que contraria CAP-ESP-02 e CAP-SUB-01
    (conjunto de referências vazio é `NAO_AVALIAVEL`, e o não avaliável nunca vira "atende" nem "não atende"). Decisão:
    **seguir a SPEC**: com o filtro de distância, o município fica fora da base (o filtro não é avaliável para ele) e aparece
    no resultado, pelo nome, como "sem referência no recorte", com o motivo; sem o filtro, entra com a distância não
    avaliável. A SPEC não mudou. (2) A distância vai sempre até a referência mais próxima, e o "mais distante" de 24/10/2026
    não cabia na janela. Decisão: **tirar o "mais distante"** da janela e do contrato da página (remoção registrada aqui).
  - **Consequências classificadas junto:** a escolha dos territórios base um a um (só estado visual, 25/10/2026) dá lugar à
    etapa Escolher da base, que o motor calcula; o esmaecimento das bolhas fora deles (26/10/2026) sai com eles; a referência
    pelo nome vinda da conversa vira os marcados da Referência; o critério da conversa vira o filtro da Referência (decisão 4
    de 25/10/2026, mantida). Todas previstas: decorrem do comando e não contrariam a SPEC nem as decisões aprovadas.
- **Antes:**
  - **Tela:** o painel "Território de referência" (`GavetaReferencia`): a relação (mais próximo ou mais distante), a
    delimitação ("No mesmo estado de cada município", estados ou regiões escolhidos, Brasil inteiro), uma condição (um
    atributo, "Maior que" ou "Menor que" e o valor de corte), o que faltava escolher, a prévia em palavras e "Aplicar o
    território de referência"; no início do painel, os **Territórios base** ("Todos os selecionados" ou alguns, cumulativos,
    só estado visual), com o anel "· território base" e, com alguns escolhidos, as demais bolhas esmaecidas. A base era
    sempre a Seleção de Territórios; sem territórios selecionados, a análise espacial esperava a seleção.
  - **Motor:** `referencia` com `{relacao, delimitacao, condicao}` (resposta `tipo: "elegiveis"`): os elegíveis eram as
    unidades da base que atendiam à condição; para cada município, o mais próximo ou o mais distante deles.
  - **Conversa:** o critério ("use como referência o município de maior densidade") abria o painel com o atributo e "Maior
    que"/"Menor que" ("Abri o Território de referência com a condição Densidade “Maior que”: escolha a relação …"); a
    referência pelo nome era a referência por membros (o membro entrava no gráfico, com distância zero e a mira).
  - **Textos:** título "Densidade de médicos e distância até o território de referência · …"; CSV com "Distância até o
    território de referência (km)"; frase-resumo "Distância em linha reta até o território de referência de cada município
    (o mais próximo entre os municípios …)"; "Abri a análise espacial: defina o Território de referência (a relação, a
    delimitação e a condição) ou diga o nome dele, …".
- **Agora:**
  - **Janela "Escolha dos territórios"** (`EscolhaDosTerritorios.tsx`; o botão dos ajustes tem o mesmo nome e, ao lado, a
    frase da consulta calculada ou "nenhuma ainda"): abre sozinha ao entrar na análise sem consulta calculada; embaixo do
    título, o contexto ("Categoria profissional: Médicos · Competência: junho de 2024"); a frase-resumo fixa "{Base} →
    referência: {Referência}", montada por modelo (cada trecho abre a aba dele; o incompleto vira "base incompleta" ou
    "referência incompleta", destacado); as abas "1 Base" e "2 Referência", com o status curto (a contagem do motor ou
    "incompleta"), só a ativa à vista, sem aba Distância; o rodapé com "Calcular" e a linha de estado ("A consulta mudou.
    Calcule para atualizar.", o motivo da pendência com "Calcular" desligado ou "Resultado em dia com a consulta."). Na aba
    Referência, "Distância em linha reta (geodésica) até a referência mais próxima de cada município da base.", a nota TPL-11
    e as faixas de distância.
  - **Seletor igual nos dois lados:** Partir de (Todo o país; uma ou mais regiões; um ou mais estados, com botões; Seleção
    prévia, com a quantidade e os nomes; só na referência, "Conforme a base": "Mesma UF de cada município da base" e "Mesma
    região de cada município da base", com a explicação); Filtrar por (opcional, E: "+ Densidade", "+ População", "+
    Quantidade" e, só na base, "+ Distância", "Distância até a referência mais próxima", "acima de" ou "até", em km, com
    "depende da Referência"; operadores "abaixo de", "até", "acima de" e "a partir de"; faixas repetindo o indicador; o texto
    "Densidade é profissionais por 1.000 habitantes. Os filtros valem juntos (E); OU e NÃO ficam em Critérios combinados.");
    Escolher ("Todos que atendem (N)" ou "Só os que eu marcar", com a busca pelo nome e a lista só de quem passou pelas etapas
    1 e 2, com o estado e a densidade; os marcados viram botões removíveis); a contagem do motor depois de cada etapa e a
    prévia ("N municípios entram na base" ou "N municípios podem ser referência", com os primeiros nomes). As pendências usam
    os textos do comando: "escolha ao menos uma região", "escolha ao menos um estado", "preencha o valor do filtro", "marque
    ao menos um município", "complete a referência para usar o filtro de distância".
  - **Motor:** `options.consulta` (`{base, referencia, distancia}`, um objeto serializável, a fonte de verdade da janela e do
    estado salvo) no lugar de `referencia` na página; a base pode partir do país, de regiões ou de estados, sem depender da
    Seleção de Territórios (que vai em `base`, como a seleção prévia). Os itens são só os municípios da base; cada um com a
    distância até a referência mais próxima, nunca ele mesmo, com os empates (`referencia_do_item`); `referencia` com
    `tipo: "consulta"` (a consulta normalizada, os textos, as contagens, `sem_referencia`, os `membros` usados e a origem).
    Com "Conforme a base", só contam as referências do estado (ou da região) de cada município. Sem referência no recorte: o
    motivo "Sem referência no recorte: nenhum outro município da referência no mesmo estado (Roraima) em junho de 2024
    (DEPENDENCIA_NAO_AVALIAVEL, CONJUNTO_REFERENCIAS_VAZIO)"; com o filtro de distância, fora da base e listado (na tela,
    `analise-sem-referencia-no-recorte`, pelo nome). Rota nova `POST /api/painel/territorios`: as contagens de cada etapa, as
    pendências, as prévias, os marcados e a lista para marcar, sem iniciar a análise. Validações com mensagem ("Consulta
    inválida: …", "A base não tem as opções relativas …", "A referência não tem o filtro de distância …", "Base incompleta:
    …", "Com a Escolha dos territórios, a referência vem da consulta: …"); o pedido antigo por elegibilidade recebe 422 "O
    território de referência por elegibilidade foi substituído pela Escolha dos territórios: …". O **"mais distante" saiu**.
  - **Conversa:** o critério abre a janela na aba Referência com o filtro do atributo e "acima de" ou "abaixo de", sem valor
    ("Abri a Escolha dos territórios com o filtro Densidade “acima de” na Referência: preencha o valor e calcule, …"); a
    referência pelo nome vira os marcados da Referência, a partir do país (a referência não é mais item do gráfico; um
    município da base que também é marcado na Referência fica com o mais próximo entre os demais, nunca ele mesmo); "Abri a
    análise espacial: faça a Escolha dos territórios (a base e a referência) ou diga o nome da referência, …". A explicação
    sem referência diz "Faça a Escolha dos territórios na Análise Espacial …"; a descrição da plataforma no contexto da
    conversa fala da distância de cada município da base até a referência mais próxima.
  - **Textos e desenho:** título "Densidade de médicos e distância até a referência mais próxima · {lugar da base} · …"; CSV
    com "Distância até a referência mais próxima (km)" e "Referência mais próxima"; frase-resumo "Distância em linha reta até
    a referência mais próxima de cada município (o mais próximo entre os municípios {referência em palavras}): …" e, com a
    base vazia, "nenhum município na base."; acima do desenho, "Base: 15 · cada um ligado à sua referência mais próxima por
    linha tracejada: …" ou "Base: BOA VISTA (RR) · referência mais próxima: …, a … km em linha reta."; legendas "círculo claro
    com mira: referência fora da base, no início do eixo (0 km)", "mira: referência mais próxima". "Calcular" é um passo do
    Desfazer ("Calcular a escolha dos territórios") e tira a comparação de antes. O estado salvo de antes vira a consulta
    equivalente (a referência por elegibilidade, a por membros e os territórios base como marcados da base); com o "mais
    distante", fica sem consulta. Destaque da análise: só a comparação esmaece as demais bolhas.
- **Permanece:** as geodésicas de Karney no elipsoide do referencial (`extreme_exact`, empates exatos); o próprio município
  nunca é a sua referência (24/10/2026); a referência do recorte sem coordenada válida deixa a distância não avaliável, sem
  trocar pela mais próxima entre as demais; nenhuma distância vira zero; as faixas de distância (CAP-ESP-03), as Condições e a
  Ordenação pela distância; a referência como bolha de contexto no 0 km, as linhas tracejadas (até 30) e a referência no
  quadro do mapa, com o nome; a rota 2 (`/api/painel/referencias`) e a referência por membros no contrato da API; a análise
  espacial de `/api/analyze`; os dados versionados; nada da base vai ao provedor de IA; a SPEC.
- **Motivo:** comando do responsável "Seleção de Territórios" (27/10/2026): a base aceitava só a escolha por nome, e a
  referência, só por delimitação e condição; base e referência passam a ser escolhidas do mesmo jeito. Decisões do responsável
  na consulta de 27/10/2026: seguir a SPEC para o município sem referência no recorte e tirar o "mais distante".
- **Documentação e testes:** `README.md` (referência geográfica mais próxima, destaque, mapa), `Docs/PAINEL_INTEGRADO_INTERFACE.md`
  (a análise espacial reescrita, a seção da Seleção de Territórios com o nome dela, os ajustes, o Desfazer, o mapa, o destaque,
  o título, o pedido e os testes), `Docs/PAINEL_INTEGRADO.md` (seção "Escolha dos territórios" no lugar da referência por
  elegibilidade, a rota 4, as chaves e a resposta), `Docs/MAPA_DA_PAGINA_UNICA.md` (mira, ligações, anéis, nomes, testes),
  `Docs/CONVERSACAO_INCREMENTO_FN.md` e `Docs/INTERFACE_CONVERSACIONAL_INTEGRADA.md` (a referência pela conversa). Testes
  novos: em `test_painel_pagina.py`, `test_consulta_steps_start_from_filters_and_choice_as_in_the_command`,
  `test_consulta_reference_follows_the_base_and_the_distance_filter_never_hides_a_municipality`,
  `test_consulta_is_validated_and_incomplete_parts_block_the_calculation`,
  `test_territories_route_counts_each_step_for_the_window_without_starting_the_analysis` e, com a base versionada,
  `test_real_consulta_of_the_command_north_far_from_acre`. Testes substituídos, com a cobertura transferida:
  `test_eligible_reference_filters_first_then_takes_the_nearest_without_the_territory_itself` →
  `test_consulta_selects_the_base_and_measures_the_nearest_reference_without_the_territory_itself`;
  `test_eligible_reference_takes_the_farthest_and_follows_the_delimitation` → o recorte em
  `test_consulta_reference_follows_the_base_…` e em `test_consulta_steps_…` (o "mais distante" saiu do produto, e com ele a
  conferência dele; a recusa do pedido antigo, também com `mais_distante`, fica em `test_consulta_is_validated_…`);
  `test_eligible_reference_without_eligibles_or_with_an_eligible_without_coordinates` → `test_consulta_reference_follows_the_base_…`
  (sem referência no recorte e a referência sem coordenada válida); `test_eligible_reference_is_validated_and_has_no_default` →
  `test_consulta_is_validated_…`; `test_uploaded_eligible_reference_uses_the_spreadsheet_levels` →
  `test_uploaded_consulta_uses_the_spreadsheet_levels`; `test_real_eligible_reference_matches_every_geodesic_…` →
  `test_real_consulta_matches_every_geodesic_…`. Nos testes do frontend, "território de referência" →
  "escolha dos territórios (27/10/2026)" (a consulta inicial, a leitura sem perda, as pendências, a frase por modelo, o pedido
  e a migração), "territórios base" → "base e referência" (os pares e os textos novos) e o destaque só da comparação.
  Alterados por mudança intencional (o comportamento mudou de propósito; nenhum teste foi afrouxado): os textos da conversa
  em `test_conversa_grafico.py`; nos roteiros de navegador, o passo 9 de `ui_area_de_analise.py` (a janela nova, com as
  contagens conferidas com o motor), os passos 11, 11b e 11c de `ui_mapa.py` (a janela nova; só BOA VISTA na base pela etapa
  Escolher, agora um novo cálculo, e o Desfazer sem recalcular, no lugar da escolha visual sem pedido) e o passo 7b de
  `ui_conversa_grafico.py` (o filtro da Referência no lugar do painel antigo).

### 2026-10-26 · Conversa: lembrete da base sem esperar o provedor, comparação indireta pelos extremos, exemplos sem lugares, histórico legível com o novo visual, destaque da comparação no gráfico e menos latência
- **Classificação (regra 1), pela leitura, antes de codar:** todos os itens decorrem do pedido do responsável de 26/10/2026
  (ajustes depois da navegação com o Gemini) e passaram nos dois testes.
  - **Lembrete da base:** mudança prevista. A SPEC pede o pedido preservado sem repetição pela pessoa (AT-64): ele fica
    guardado e segue quando a base fica pronta; nada na SPEC exige interpretar pelo provedor um pedido de análise feito antes
    dos dados. O lembrete é da página única (campo `lembrar_base`); sem o campo, a rota responde como antes.
  - **Comparação indireta:** mudança prevista. A comparação continua CAP-CMP-01 (2 ou 3 itens, maior, menor e diferença do
    motor); quem entra vem das ordens do motor, com os empates (CAP-SUB-02, DA-18), a pedido explícito da pessoa e dito na
    resposta, com os valores. A regra de CAP-REF-01 (nada escolhido em silêncio pela posição na ordem) é da referência, que
    continua por critério, com a relação, a delimitação e o corte escolhidos pela pessoa.
  - **Exemplos sem lugares, histórico e visual, prazos da tela:** mudanças previstas (textos e apresentação; nenhuma regra
    da SPEC fixa esses textos; o histórico continua sem armazenamento persistente).
  - **Destaque da comparação:** mudança prevista. É estado visual (RQ-REP-06); a decisão de 25/10/2026 (marcar não esmaece)
    continua para a marcação sozinha; o esmaecimento passa a valer só para a análise em foco (comparação em exibição ou
    territórios base escolhidos), como o responsável pediu.
  - **Orçamento de 20 s:** mudança prevista. RQ-SIN-05 admite até 2 regenerações; menos chamadas, com a resposta verificada
    (e TPL-08 quando um texto foi recusado), continuam dentro da regra; o prazo de 75 s por chamada (21/10/2026) não mudou.
  - **Ganho de desempenho** (casas decimais, triagem, proteção, contexto e competências guardados): sem mudança de
    comportamento, com equivalência conferida.
- **Antes:**
  - **Começo sem base:** "Quero analisar a densidade" ou "compare os municípios do Pará" iam ao intérprete com o provedor,
    seguido da redação, cada chamada com até 75 s e até 3 tentativas de cada; a caixa podia ficar em "Interpretando o pedido…"
    por minutos. Quando a base ficava pronta, o pedido guardado ia só ao intérprete local; sem resposta local, se perdia.
  - **Comparação indireta:** "comparar os municípios de maior e menor densidade" e "qual a diferença entre o de maior e o de
    menor?" pediam os nomes ("Diga quais, por exemplo “compare Manaus e Tefé”"); "compare os mais populosos" também.
  - **Exemplos:** a orientação da caixa trazia exemplos fixos com lugares ("mostre o Pará", "use Belém como referência",
    "compare Manaus e Tefé"), e as respostas do gestor e da gramática citavam Manaus, Tefé, Belém, Anápolis e o Pará.
  - **Histórico e visual:** letra de 13 px, a resposta do agente sem balão, um parágrafo corrido; a chegada de uma resposta
    longa levava a rolagem ao fim, e a pergunta da pessoa sumia acima da área visível; caixa de até 400 px e 74% da altura.
  - **Gráfico:** com uma comparação em exibição ou territórios base escolhidos, todas as bolhas ficavam com a cor inteira; o
    painel Comparar ainda dizia "os demais esmaecem" ao marcar.
  - **Tempo:** a parte local de uma pergunta levava 130–800 ms (com 144 municípios, até 800 ms).
- **Agora:**
  - **Começo sem base:** o pedido de análise antes da escolha dos dados recebe na hora, sem o provedor, "Para fazer essa
    análise, primeiro escolha os dados: use os dados do Brasil ou envie os seus, em CSV ou Excel. Assim que a base estiver
    pronta, sigo com o seu pedido." (`aguarda_base`), e os dois botões da escolha ficam em destaque. Perguntas de conceito,
    agradecimentos e conversa seguem como antes. Com a base pronta, o pedido guardado segue pelo caminho completo, com "Com os
    dados prontos, sigo com o seu pedido.".
  - **Comparação indireta** (`dialogo.py`, ato `compara_extremos`; `painel.conversation_top`): o maior e o menor, os
    extremos, os dois ou três maiores ou menores, pelas ordens do motor sobre o gráfico em exibição, com os empates; com um
    estado citado fora do gráfico, primeiro os municípios dele e a continuação (`continuar`), que a tela envia sozinha quando
    o motor calcula; na pergunta da diferença, a leitura da diferença do motor depois do cálculo; no plural sem quantidade,
    "Quer comparar os dois ou os três …?", com as alternativas em botões.
  - **Exemplos:** três exemplos do que a análise aberta faz, sem lugares, com o indicador em uso, alternados conforme a
    conversa avança (`exemplosDaAnalise`); as respostas dão exemplos pela função ("compare o de maior e o de menor
    densidade", "use como referência o município de maior densidade", "a mais de 150 km").
  - **Histórico e visual:** letra de 15 px (14 px no celular), balões com contorno e sombra, a hora em cada mensagem,
    parágrafos separados, o rótulo do começo em negrito e os exemplos em destaque, sem mudar o texto; numa resposta longa, a
    pergunta curta fica no alto e o começo da resposta abaixo; caixa de até 440 px e 84% da altura (800 px); orientação
    compacta depois da primeira mensagem; barra de rolagem visível.
  - **Gráfico:** com uma comparação em exibição, só os comparados ficam inteiros no gráfico de bolhas, e as demais bolhas
    esmaecem a 25% (no modo leve, a camada a 30%); com territórios base escolhidos um a um, as bases e as referências delas.
    O texto do painel Comparar diz isso.
  - **Tempo:** a parte local de uma pergunta leva 27–63 ms (287 ms numa comparação por nomes, com o gráfico novo); nenhuma
    chamada nova ao provedor começa depois de 20 s do pedido; a tela avisa aos 12 s e aos 45 s e interrompe a espera aos 100 s
    ("A resposta demorou mais que o esperado").
- **Permanece:** cálculos, métodos e resultados do motor; a gramática local e o reconhecimento dos demais atos (as mensagens
  dos casos versionados, em 330 combinações de mensagem e contexto, com o mesmo ato de antes); a referência por critério
  (CAP-REF-01); marcar sem esmaecer; o mapa; o modelo
  `gemini-3.5-flash-lite` e o prazo de 75 s por chamada; nenhum arquivo, registro, identificador ou nome de campo ao
  provedor; o histórico sem armazenamento persistente (quando a sessão termina, pela Nova sessão, pela expiração ou com o
  servidor reiniciado, a página recomeça limpa, como antes); os dados versionados.
- **Motivo:** pedido do responsável de 26/10/2026, depois da navegação com o Gemini: o começo sem base lento ("rodando
  estático"); a comparação de "maior e menor densidade" que ordenava ou pedia os nomes; exemplos com municípios reais que
  confundem; a conversa que não ficava à vista como num aplicativo de mensagens; letra miúda e sem contornos; as bolhas da
  comparação misturadas às demais; e a latência maior depois das últimas mudanças.
- **Documentação e testes:** `README.md` (ajustes da conversa, começo sem base, orçamento de tempo),
  `Docs/INTERFACE_CONVERSACIONAL_INTEGRADA.md` (histórico, visual, estados, prazos, orientações, começo sem base, comparação
  indireta), `Docs/DIALOGO_GOVERNADO.md` (orçamento do pedido, comparação pelos extremos), `Docs/PAINEL_INTEGRADO_INTERFACE.md`
  (destaque da análise, texto do Comparar) e `Docs/OTIMIZACAO_LATENCIA.md` (seção 4.10). Testes novos: em `test_dialogo.py`,
  a comparação pelos extremos (reconhecimento, ordens do motor, empates, estado fora do gráfico com a continuação, diferença,
  plural com alternativas e exemplos sem lugares); `test_conversa_tempo.py` (orçamento de 20 s na interpretação e na
  redação, lembrete sem base sem o provedor, conceito sem lembrete e a rota sem o campo); em `test_painel_resumo.py`, a
  equivalência de `places_for` com a comparação par a par e `conversation_top` com empates; nos testes do frontend, a hora,
  os blocos de leitura, a rolagem, o aviso de demora, os exemplos e o destaque da análise; `conversa_simulada.py` ganhou
  `continua` (a continuação enviada pela tela); `ui_conversa_grafico.py` (lembrete e botões em destaque com e sem o
  provedor, a hora no balão, o pedido guardado seguindo nos dois modos e a comparação pelos extremos com o esmaecimento),
  `ui_area_de_analise.py` (Comparar esmaece as demais) e `ui_mapa.py` (base escolhida esmaece as demais). Testes alterados
  por mudança intencional (o comportamento mudou de propósito; nenhum teste foi afrouxado): os textos esperados das
  orientações com lugares (`test_conversa_grafico.py`, `conversaGrafico.test.mjs`, a orientação da Seleção em
  `ui_conversa_grafico.py`); e, em `ui_conversa_grafico.py`, o passo do pedido antes dos dados, que agora recebe o lembrete
  nos dois modos (o aviso de indisponibilidade sem o provedor passou a ser conferido com uma conversa livre, "Me conte uma
  curiosidade"), e a conferência "sem territórios, nada é pedido ao motor", que passou a valer nos dois modos.

### 2026-10-26 · Conversa: Gemini conversa e explica sob conferência de fidelidade, triagem nova, resultados exibidos no contexto, sem teto local de chamadas, indisponibilidade cordial e histórico visível
- **Classificação (regra 1):** todas as mudanças decorrem do pedido do responsável (missão "Evolução integrada da
  inteligência conversacional", 26/10/2026, autorizações A a H) e passaram no teste de escopo. Compatibilidade: a paráfrase
  metodológica, a redação da conversa pelo LLM, o alcance dos resultados agregados no contexto e o texto da indisponibilidade
  contrariavam a letra de V-16, RQ-SIN-02/07/10, FN-META-01 e RQ-DEG-02 (TPL-01); o responsável os autorizou expressamente,
  e a SPEC ganhou o Adendo PAR-20261026 (divergência aprovada). A política dos dados ("nada da base ao provedor") foi
  ajustada pela autorização D, nos limites de RQ-DAD-23. Nenhuma metodologia, fórmula, indicador, critério ou classe mudou.
- **Antes:**
  - **Triagem:** `_sanitize` mascarava toda palavra com inicial maiúscula fora de uma lista curta ("Não era isso que eu
    queria." perdia o "Não"; "Município." virava marcador), números viravam `[VALOR_LOCAL]` ("Caiu em 2023?" perdia o ano) e
    valores, nomes de campo e palavras comuns que coincidiam com eles viravam `[DADO_LOCAL]`, inclusive territórios citados.
  - **Gemini:** só classificava atos (enumerações) e, a pedido de outra formulação, reescrevia um esqueleto com marcadores
    opacos (`backend/redacao.py`); não via o resultado em exibição nem a conversa; explicações de método só literais.
  - **Contexto:** a janela eram as 4 últimas mensagens da pessoa; nenhuma resposta do agente, nenhum valor da tela.
  - **Limite:** `MAX_REQUESTS_PER_DAY = 20` bloqueava a 21ª chamada do dia (HTTP 429 local).
  - **Falhas:** HTTP 429, 502 e 503 nas rotas da conversa e o texto técnico na caixa ("Gemini não configurado. Defina
    GEMINI_API_KEY…", "… (HTTP 503)"); saída fora do contrato era HTTP 502; na página única, sem provedor, TPL-01.
  - **Tela:** só a última resposta do agente aparecia; as mensagens da pessoa sumiam depois do envio.
- **Agora:**
  - **Triagem** (`backend/triagem.py`): as quatro classes de RQ-DAD-20; identificadores (CPF, e-mail, telefone com marcador
    ou formato inequívoco, sequências de 10 ou mais dígitos, valores de colunas sem papel autorizado) e nomes sem evidência
    viram marcadores numerados por tipo (RQ-DAD-39); nomes de campo e de arquivo, `[CAMPO_n]` e `[ARQUIVO_n]`; negação,
    verbos, operadores, períodos, quantidades, comparações, territórios, grupos, regiões e categorias da base, unidades
    federativas, nomes após marcador territorial, títulos ("Dr.", "Sra.") e letras isoladas (símbolos de fórmula) ficam. O
    que já virou marcador num envio continua marcador, com o mesmo número, em todos os textos dele. A mensagem da tela nunca
    muda.
  - **Contexto** (`backend/contexto_conversa.py`): cartão com a tela, o resultado agregado em exibição (valores formatados
    como na tela, ordens do motor, classes, notas, disponibilidade), o resultado anterior, a janela das 8 mensagens recentes
    da pessoa e do agente (campo `turnos`), a pendência e as funcionalidades da página; com muitos itens, os extremos. O
    texto da pessoa passa pela triagem completa; o do sistema (resultado, resposta verificada, fichas), pelas classes A e C,
    sem transformar fórmulas e códigos de método em marcadores; o nome escrito pela pessoa que a resposta verificada repete
    continua marcador.
  - **Gemini conversa, motor decide** (`backend/conversa_gemini.py`, `backend/fidelidade.py`, `backend/definicoes.py`): com
    o provedor disponível, perguntas de conversa e orientações do catálogo vão a ele com o cartão e a resposta verificada; o
    texto aparece só se passar na conferência (números, nomes, ordens e classes do motor; nenhuma relação calculada pelo
    modelo nem número de exemplo documentado usado como valor; juízo, causa, acesso, destaque e previsão só como ressalva;
    ressalvas obrigatórias; elementos essenciais e proibições das fichas de método; a frase copiada da resposta
    verificada não conta como afirmação nova); até 2 regenerações;
    depois, a resposta verificada com TPL-08. O contrato do intérprete ganhou `resposta`. Comandos do gráfico,
    esclarecimentos, desfazer, voltar e recusas de governança continuam determinísticos. A explicação de uma classe de
    tendência passa a trazer a regra em palavras (a ficha, o texto da tela). `redacao.py` saiu.
  - **Sem teto local:** o consumo é monitorado (`/api/llm/status`: `requests_used_today`, `monitoramento`, `disponivel`,
    `espera`, `indisponibilidade`; `local_daily_limit` saiu). Um 429 põe a espera informada pelo provedor (RetryInfo;
    minuto ou tokens) ou, na cota diária, até a virada do dia no Pacífico; 5xx, tempo esgotado e rede, 20 s; chave recusada,
    5 min. Durante a espera nada é chamado.
  - **Falhas:** as rotas da conversa respondem 200 com `indisponibilidade` (tipo `cota` só com limite confirmado pelo
    provedor; senão `indisponivel`), e a tela mostra no histórico "Assistente conversacional temporariamente indisponível"
    com o texto aprovado de cada caso, sem código. Saída fora do contrato: 2 regenerações e a resposta de reserva (200,
    `reserva: true`). Pedido inválido continua 422.
  - **Tela** (`frontend/src/historicoConversa.ts`, `AnalysisAssistant.tsx`): o histórico completo, em ordem, com as mensagens
    da pessoa como ela escreveu, as respostas do agente e os avisos; rolagem que não puxa quem lê mensagens antigas
    (`chat-ir-ao-fim`); caixa maior (até 400 px e 74% da altura; 72% no celular); faixa de situação do serviço.
- **Permanece:** cálculos, métodos e resultados do motor; a gramática local e o gestor de diálogo; a biblioteca
  conversacional; o modelo `gemini-3.5-flash-lite`; nenhum faturamento; nenhum arquivo, registro, identificador ou nome
  de campo ao provedor; os controles e análises com o provedor indisponível; a CI sem chamadas reais.
- **Motivo:** missão do responsável de 26/10/2026, a partir de `DIAGNOSTICO_LIBERDADE_CONVERSACIONAL.md`.
- **Documentação e testes:** SPEC (Adendo PAR-20261026), `README.md` (política dos dados, conversa, disponibilidade),
  `AGENTS.md` (regra 2), `Docs/DIALOGO_GOVERNADO.md`, `Docs/INTERFACE_CONVERSACIONAL_INTEGRADA.md` (histórico da conversa),
  `Docs/CONVERSACAO_INCREMENTO_FN.md` e `Docs/BIBLIOTECA_CONVERSACIONAL.md`. Testes novos: `test_triagem.py`,
  `test_fidelidade.py`, `test_contexto_conversa.py`, `frontend/tests/historicoConversa.test.mjs` e, em `test_llm_bridge.py`,
  sem teto, cotas, espera e recuperação; em `test_dialogo_adversarial.py`, a redação fiel simulada sem reserva por falso
  positivo da conferência, com a base versionada; `ui_conversa_grafico.py` ganhou o histórico, os avisos cordiais, a redação
  conferida, a reserva de contrato e o limite e a queda simulados. Testes alterados por mudança intencional (o defeito
  estava no comportamento antigo, não nos testes): os que esperavam 502/503/429 nas rotas da conversa, o limite local, a
  máscara de territórios, períodos e categorias da própria mensagem, a redação por marcadores e o "Dr." mascarado; e o
  verificador de números de `test_dialogo_adversarial.py`, que aceita os números do exemplo documentado de uma ficha
  autorizada só quando a formulação inteira aparece literalmente na resposta (a explicação de uma classe agora traz a regra
  em palavras, com o exemplo da tela).

### 2026-10-26 · Página única: gestor de diálogo governado, explicação verificada do resultado, redação pelo Gemini sob validador e o resultado em exibição enviado à conversa
- **Classificação (regra 1):** todas as mudanças abaixo decorrem do pedido do responsável (desafio adversarial de engenharia
  conversacional, 26/10/2026) ou de defeito encontrado ao cumpri-lo, e passaram nos dois testes. Compatibilidade: a conversa
  só interpreta e organiza (INV-02, INV-03); números, classes e relações são segmentos copiados do motor e conferidos (C-04,
  RQ-SIN-02, RQ-SIN-10); explicação de método só com formas literais do catálogo (V-16, RQ-SIN-07); a redação pelo Gemini
  muda organização e tom, nunca valores, formas ou significado (CAP-SIN-01 "LLM com validação", INV-13, RQ-SIN-04,
  RQ-SIN-05, RQ-SIN-08); o modo sem provedor usa TPL-01. O que contrariaria a SPEC ou a decisão de 20/10/2026 não foi
  implementado e ficou como proposta (P-A, P-B e P-C em `Docs/DIALOGO_GOVERNADO.md`).
- **Antes:**
  - **Resposta a esclarecimento:** só pelo botão. "Município." depois de "estado ou município?" ia ao intérprete com o
    provedor; sem ele, "Gemini não configurado".
  - **Continuidade:** "não era isso que eu queria", "desfaz", "volta para a comparação anterior", "troca o primeiro pelo
    segundo", "agora inclui mais um", "Não, o estado." e "Não, eu queria a evolução" não tinham tratamento local.
  - **Perguntas sobre o resultado** ("qual deles tem a maior densidade?", "e em relação à população?"), explicações
    ("Não entendi a aceleração."), verificações ("isso significa que melhorou?", "qual foi a causa?"), perguntas sobre a tela
    e tentativas de indução ("muda o valor de X para 10") iam ao provedor; sem ele, erro.
  - **Resultado em exibição:** a tela enviava `displayed_result_id` vazio, porque lia `sessao.result_id` na resposta guardada,
    que a normalização da área traz como `sessao.resultId`. A conversa nunca recebia o resultado do gráfico.
  - **"Explique o resultado"** e as formas com explique, explica, explicar, descreva, descreve ou descrever eram respondidas
    na tela com a frase-resumo do motor, sem mais fatos e sem memória para as perguntas seguintes.
  - **Sem o provedor, com o gráfico na tela:** HTTP 503 e o aviso de erro na caixa.
  - **Intérprete com o provedor:** 12 atos de diálogo, sem os campos `style`, `subject`, `attribute` e `direction`.
    `dialogue_action` tomava "que" dentro de palavras ("queria") como pergunta sobre o resultado.
  - **Gramática local:** não reconhecia "contraste", "coteje", "versus", "vs", "um do lado do outro", "frente a frente",
    "se diferenciam" e "a diferença entre" como comparação; "desses", "destes", "dessas", "destas", "os dois", "as duas", "os
    três" e "ambos" como os territórios na tela; "compare" sem nomes com 2 ou 3 unidades na tela; "só 2024" (e "somente",
    "apenas"); "traz", "joga", "bota", "põe", "coloca", "plota" e "desenha" como pedidos de vista. "por" estava entre os
    verbos de vista.
  - **Catálogo governado:** a forma "mensagem" de TPL-06 (ADM-FE), TPL-07 (ADM-SC), TPL-01 (LLM_INDISPONIVEL) e TPL-08
    (REGENERACAO_ESGOTADA) não era materializável.
  - **Mapa sem disponibilidade:** o motivo ficava só na tela. "Entenda esta análise" não abria pela conversa.
- **Agora:**
  - **Gestor de diálogo** (`backend/dialogo.py`), na página única, antes da gramática e do provedor e sem calcular:
    - resposta escrita a esclarecimentos, como o clique ("Entendi: RIO DE JANEIRO (RJ). …"), com a informação de uma
      pergunta encadeada lembrada ("Anotei “a do Pará” para quando essa escolha aparecer"); correção da escolha ("Não, o
      estado.": estado e município não ficam no mesmo gráfico, e a conversa oferece comparar os estados);
    - continuidade: correção com novo pedido, desfazer (a tela volta ao estado do gráfico de antes da última mudança feita
      pela conversa; logo depois de uma pergunta, "não era isso" deixa a pergunta de lado e oferece desfazer), voltar (uma
      mudança como as outras, que "desfaz" reverte), trocar, incluir ("inclui mais um" pergunta qual), tirar e todos;
    - perguntas sobre o resultado em exibição, com os valores e a ordem do motor (`painel.conversation_facts`, empates
      preservados) e a diferença da comparação do motor, sem mudar o gráfico;
    - explicação em quatro registros, com memória do tópico (`backend/explicacao.py`): a frase-resumo e os fatos de cada
      território; termos da Tendência com as classes, contagens, valores observados e, no técnico, velocidades e a nota do
      método, e a ação que abre "Entenda esta análise" com a classe destacada (`analise-apresentacao-destaque`); temas com
      formas liberadas do catálogo (densidade, distância, referência, agregação, quintis) com as formas literais;
    - verificações com os fatos e as regras governadas (CFG-NOR; TPL-06 com EXC-03, conferindo antes a premissa: "o
      resultado não mostra queda para …"; TPL-11; notas de procedência do motor);
    - perguntas sobre a tela (dados, territórios, seleção, mapa, relatório, análise anterior, o que mudou, ausência,
      disponibilidade) e recusas naturais, com a forma governada e uma alternativa, às tentativas de indução (valores,
      classificações, método, ocupações, juízos, política, correlação, projeção, pessoas, fontes externas, parâmetros
      ignorados e escolhas delegadas). `ADT_DIALOGO=0` restaura o caminho anterior.
  - **API:** `/api/exploration/interpret` aceita `conversa` e `displayed_result_id`; `/api/llm/interpret-context`, `conversa`.
    As respostas do gestor trazem `memoria`, `dialogo`, `explicacao`, `acoes`, `desfazer`, `modelo_de_resposta`,
    `pedido_original` e, com a redação pelo Gemini, `redacao`.
  - **Resultado em exibição:** `resultadoDaSessao` lê `sessao.resultId` (e ainda `result_id`), e a conversa recebe o
    resultado do gráfico guardado na sessão. Com ele, o intérprete com o provedor passa a receber `has_verified_result`
    verdadeiro quando há gráfico (só o estado enumerado; nenhum valor).
  - **"Explique o resultado"** e as formas com explique, explica, explicar, descreva, descreve ou descrever vão ao gestor de
    diálogo, que responde com a frase-resumo e os fatos de cada território, copiados do motor. "O que esse gráfico mostra?",
    "resuma o gráfico" e "o que estou vendo?" continuam respondidos na tela.
  - **Sem o provedor, com o gráfico na tela:** os casos de HTTP 503 viram resposta (HTTP 200, `degradado: true`) com a forma
    de TPL-01, o motivo (salvo chave ausente), exemplos do que continua disponível e "O que você quer ver?".
  - **Intérprete com o provedor:** 16 atos novos (`answer_choice`, `correction`, `undo`, `previous_state`, `compare_result`,
    `concept`, `technical`, `reformulate`, `verify`, `cause`, `screen_state`, `out_of_scope`, `include`, `replace`, `remove`,
    `all_units`) e os campos `style`, `subject`, `attribute` e `direction`, todos enumerações; o gestor executa o ato. A
    biblioteca conversacional ganhou 10 trajetórias (`K_dialogo_governado.jsonl`) e as ações `DESFAZ` e `VOLTA_ESTADO`, o
    que muda os exemplos enviados ao provedor. `dialogue_action` usa limites de palavra.
  - **Redação pelo Gemini** (`backend/redacao.py`), só a pedido de outra formulação ("de outro jeito", "mais simples", "de
    forma didática", "explique melhor") e com o provedor configurado: vai o esqueleto com marcadores opacos; o texto volta
    pelo validador (marcadores exatos, nenhum número, termo de juízo, causa, tendência, acesso, relação, destaque ou
    heterogeneidade novo, nenhum nome próprio novo); até 2 regenerações; esgotadas, o texto verificado com a mensagem de
    TPL-08. A pergunta sobre um termo é composta localmente. `ADT_REDACAO_GEMINI=0` desliga.
  - **Gramática local:** reconhece as formas de comparação, dêixis, "só 2024" e verbos de vista listados acima; "por" saiu
    dos verbos de vista.
  - **Catálogo governado:** materializa a forma "mensagem" de TPL-06, TPL-07, TPL-01 e TPL-08 com aquelas evidências.
  - **Mapa sem disponibilidade:** a tela envia o motivo (`painel_motivo_sem_mapa`) ao backend local, que o usa na resposta.
- **Permanece:** nenhum cálculo pela conversa; nada da base, nem a memória da conversa, vai ao provedor; as alternativas em
  botões; as frases-resumo respondidas na tela; "volte ao resultado anterior" pelo Histórico; o caminho fora da página única
  e antes dos dados (inclusive o HTTP 503 ali); o tratamento de cota, autorização e falhas 429 e 502 do provedor; a lista de
  temas metodológicos liberados na conversa (a regra das classes da Tendência continua fora, na tela).
- **Motivo:** pedido do responsável pelo produto (26/10/2026): ampliar a inteligência conversacional sem dar autoridade
  analítica ao Gemini. O defeito do resultado em exibição foi encontrado pelo roteiro de navegador desta mudança.
- **Documentação e testes:** `Docs/DIALOGO_GOVERNADO.md` (novo: arquitetura, atos, matriz de cobertura, avaliação antes e
  depois, propostas), `README.md`, `Docs/INTERFACE_CONVERSACIONAL_INTEGRADA.md`, `Docs/CONVERSACAO_INCREMENTO_FN.md` e
  `Docs/BIBLIOTECA_CONVERSACIONAL.md`. Testes: `backend/tests/test_dialogo.py` (novo), `backend/tests/test_dialogo_adversarial.py`
  (novo, com a base versionada, job `dados-reais`, sobre os conjuntos de `backend/tests/dialogo_adversarial/` e o simulador
  `backend/tests/conversa_simulada.py`), `backend/tests/ui_conversa_grafico.py` (passos 6b a 6d e a memória da conversa entre
  os itens protegidos), `frontend/tests/conversaGrafico.test.mjs` ("Explique o resultado." e "me explica esse gráfico" saíram
  das frases-resumo da tela, de propósito; o motivo do mapa vai em `painel_motivo_sem_mapa`; memória da conversa) e
  `frontend/tests/paginaUnica.test.mjs` (`resultadoDaSessao` com a resposta normalizada).

### 2026-10-25 · Análise Espacial: territórios base cumulativos, cada um ligado à sua referência no gráfico; "Entenda esta análise" recolhido por padrão
- **Antes:**
  - **Território base único:** um `<select>` (`analise-ref-base`) com "Todos os selecionados (cada um com a sua referência)",
    o padrão, ou uma das unidades em análise. No padrão, o gráfico não mostrava nenhuma referência nem ligação: só com uma base
    escolhida aparecia a bolha de contexto dela, no 0 km, ligada à base por uma linha tracejada. No relato do responsável (ALTO
    ALEGRE DOS PARECIS e ALTO PARAISO, de Rondônia; RODRIGUES ALVES e SANTA ROSA DO PURUS, do Acre; referência mais próxima
    no Brasil inteiro com densidade acima de 2), o gráfico ficava só com os quatro, de 0 a 300 km, e a referência de cada um
    aparecia só na tabela.
  - **Empate:** a bolha de contexto e a ligação iam só até a primeira referência empatada (as outras ficavam no texto).
  - **Mapa:** as ligações eram as dos municípios marcados (até 30) e a do território base escolhido, que vinha primeiro.
  - **"Entenda esta análise":** abria na primeira visita de cada análise na sessão (menos na Tendência, que já começava
    recolhida) e ficava como a pessoa deixou.
- **Agora:**
  - **Territórios base cumulativos** (`analise-ref-base-passo`, no início do painel do Território de referência): "Todos os
    selecionados" (`analise-ref-base-todos`, o padrão, que vale também para quem entrar depois) ou alguns, marcados um a um na
    lista das unidades em análise (`analise-ref-base`, caixas `analise-ref-base-opcao`; com a referência pelo nome, sem os
    membros dela, que são a referência). Com algumas marcadas, "Todos" fica indeterminado; marcar todas volta a "Todos"; tirar
    "Todos" deixa nenhuma.
  - **Gráfico:** com o território de referência aplicado, cada território base aparece ligado ao seu território de referência.
    - Uma linha tracejada por par (`analise-ligacao-base`, com `data-base` e `data-referencia`), até 30 ligações, das bases à
      vista (dentro da régua e dos filtros), as marcadas primeiro. No empate, uma linha até cada referência empatada
      (CAP-ESP-02).
    - Cada referência que o gráfico não desenha entra uma vez como bolha de contexto (`analise-referencia-da-base`, com
      `data-bases`): círculo claro com a mira, no 0 km, os valores do motor. As mais populosas ficam atrás, e o círculo deixa ver
      as que se cobrem.
    - A dica da referência traz a população, os profissionais, a densidade e a distância até cada base ligada a ela (até 4; as
      outras, na tabela).
    - Nomes à vista: até 12 bases e até 12 referências; com mais, a dica.
    - Só as bases escolhidas uma a uma ganham o anel e "· território base"; com todos os selecionados, as bases ficam com o nome
      de sempre.
    - A legenda de símbolos diz "círculo claro com mira: território de referência fora da seleção, no início do eixo (0 km)" e
      "linha tracejada: do território base até o seu território de referência".
  - **Acima do desenho** (`analise-par-base`, sempre que há bases possíveis):
    - **Uma base:** o par dela, como antes.
    - **Mais de uma:** "Territórios base: 4 (todos os selecionados) · cada um ligado ao seu território de referência (o mais
      próximo) por linha tracejada: …", com os quatro primeiros pares (base → referência, distância do motor) e quantos faltam.
    - **Menos ligações que pares:** quando o gráfico liga menos do que os pares com referência, quantas ligações ele desenha.
    - **Sem bases:** "Nenhum território base: …".
    - **Nenhuma referência:** com várias bases e nenhuma com referência, a linha sai, e o aviso `analise-ref-sem-resultado` diz
      o motivo.
    - **Botão:** "Mudar os territórios base" (ou "Mudar o território base", ou "Escolher os territórios base").
  - **Resumo do Território de referência:** cita as bases só quando escolhidas uma a uma.
  - **Mapa:** ligações até 30, na ordem: as bases escolhidas uma a uma, depois as unidades marcadas e, com todos os
    selecionados como base, as demais, na ordem dos nomes. O aviso diz "um território base ou um município marcado".
  - **Desfazer:** cada escolha é um passo ("Incluir BOA VISTA (RR) nos territórios base", "Tirar … dos territórios base",
    "Todos os selecionados como territórios base", "Nenhum território base"). O estado salvo guarda a lista, e um território base
    guardado antes vira a lista com ele.
  - **"Entenda esta análise":** começa recolhido em todas as análises, desde a primeira visita; se a pessoa o abre ou fecha, a aba
    guarda a escolha na sessão.
- **Permanece:**
  - **Motor e cálculo:** o pedido ao motor (os territórios base não entram nele, RQ-REP-06) e o cálculo (os elegíveis, a relação,
    as distâncias, nunca o próprio município).
  - **Contagens e exportações:** a frase-resumo, os grupos, a régua, os filtros, a tabela e o CSV, nos quais as bolhas de contexto
    não entram.
  - **Referência pelo nome:** o membro continua como item, a distância zero, com a mira, e a ligação vai até ele.
  - **Clique na bolha:** continua só marcando (Comparar e as ligações do mapa).
  - **Explicações:** o conteúdo das explicações e a orientação da Seleção, sempre à vista.
  - **Dados:** nada da base vai ao provedor de IA.
- **Motivo:** pedido do responsável em 25/10/2026, ao conferir a versão mais atual:
  - Pedidos:
    - "a caixa seletora deveria ser cumulativa […] Todos ou alguns. Como território base";
    - "quando aplica território de referência, precisa aparecer no gráfico com linha tracejada cada território base e o seu
      território de referência […] e no eixo X os quilômetros";
    - "toda a explicação, tipo, entenda esta análise, ela sempre deve ficar com o botão recolhido por padrão, para não ocupar
      muito espaço".
  - Conferido na base: SANTA ROSA DO PURUS → BRASILEIA (AC), a 257,98 km; BRASILEIA, com 65 profissionais e 27.841 habitantes em
    junho de 2024, tem densidade de 2,33 por 1.000 e atende à condição.
  - **Classificação, pela leitura, antes de codar:** mudanças previstas; decorrem do pedido e não contrariam a SPEC.
    - A escolha das bases é estado visual (RQ-REP-06).
    - As ligações e as referências de contexto só mostram resultados do motor (Adendo BOL e RQ-REP-09: a posição pela distância,
      todo número do motor) e não criam operação comparativa (CAP-REF-01).
    - O empate preserva todas as referências empatadas (CAP-ESP-02).
    - O mapa só lê as coordenadas autorizadas (RQ-REP-07).
    - "Entenda esta análise" recolhido é decisão de apresentação do próprio responsável e muda a de 24/10/2026, sem SPEC que a
      regule.
- **Documentação e testes:**
  - **Documentação:**
    - `Docs/PAINEL_INTEGRADO_INTERFACE.md`: os territórios base, "Entenda esta análise", o que a área entrega ao mapa e os testes.
    - `Docs/MAPA_DA_PAGINA_UNICA.md`: as props, as linhas tracejadas, os anéis, os nomes, a decisão 3 de 25/10/2026 e os testes.
    - `Docs/PAINEL_INTEGRADO.md`, na linha de `referencia.membros`.
    - `README.md`.
  - **Testes mudados de propósito** (o comportamento mudou por este pedido; os testes estavam certos):
    - Node, `areaDeAnalise.test.mjs` (os territórios base). Cobre:
      - todos ou alguns (`basesEmUso`, `normalizarBases`);
      - os pares, com todas as empatadas, e as opções sem os membros da referência pelo nome;
      - as referências de contexto com as bases ligadas e a dica delas;
      - a linha acima do desenho com uma base, com várias, com menos ligações e sem bases;
      - o resumo;
      - o pedido igual com e sem bases;
      - o estado salvo, também o de antes;
      - a escala do gráfico.
    - Roteiro `ui_mapa.py`, passo 11c, na base versionada, com Roraima inteira:
      - todos os selecionados como padrão, com as 15 caixas marcadas e a frase dos pares;
      - uma ligação por par, igual às referências do motor;
      - as referências de contexto com os valores do motor, à esquerda de todas as bolhas;
      - depois, nenhuma base e só BOA VISTA, com o passo do Desfazer, o resumo, o anel e a ligação;
      - no mapa, a referência à vista e com o nome;
      - nenhum pedido novo ao motor.
    - Roteiro `ui_area_de_analise.py`: "Entenda esta análise" recolhido na primeira visita da Espacial e da Distribuição; ao abrir,
      fica como a pessoa deixou.

### 2026-10-25 · Análise Espacial: o território base e a referência à vista no gráfico e no mapa
- **Antes:**
  - O motor achava a referência de cada município (por elegibilidade, o mais próximo ou o mais distante dos elegíveis), mas a
    tela não a mostrava: o gráfico desenha só as unidades em análise, e a referência de fora da seleção aparecia só em palavras,
    na dica e na coluna dos Detalhes; nem a unidade em análise que é a referência de outra ganhava a mira. Marcar uma bolha só
    dava o anel e o nome; as ligações ficavam no mapa.
  - No mapa, a mira e a linha tracejada até a referência de fora da seleção ficavam na borda, cortadas e sem nome: o
    enquadramento inicial e o "Ver tudo" usavam só os itens, e os nomes só eram pedidos para eles. No relato do responsável
    (AMAJARI, BOA VISTA e BONFIM, de Roraima; referência no Brasil inteiro com densidade acima de 2; BOA VISTA marcada), a
    referência de BOA VISTA, PRESIDENTE FIGUEIREDO (AM), a 543,82 km, não aparecia.
  - Não havia território base: a escolha implícita era marcar no gráfico.
  - Na resposta, por elegibilidade, `referencia.membros` trazia só `id` e `rotulo`.
- **Agora:**
  - **Território base** (`analise-ref-base`), no início do painel do Território de referência: "Todos os selecionados (cada um
    com a sua referência)", o padrão e o comportamento de antes, ou uma das unidades em análise. Com uma base:
    - no gráfico, a referência dela, quando o gráfico não a desenha (por elegibilidade), entra como bolha de contexto
      (`analise-referencia-da-base`): círculo claro com a mira, no início do eixo (0 km), na altura do indicador e com o tamanho
      pela população dela, os valores do motor, com o nome "· referência" e uma dica própria (população, profissionais,
      densidade e a distância até a base); a base ganha o anel e o nome "· território base", e uma linha tracejada
      (`analise-ligacao-base`) liga as duas, a distância no eixo horizontal; com a referência pelo nome, a linha vai até o
      membro, que já está no gráfico com a mira. A legenda de símbolos diz o que são a bolha clara e a linha;
    - acima do desenho, `analise-par-base`: "Território base: BOA VISTA (RR) · Território de referência (o mais próximo):
      PRESIDENTE FIGUEIREDO (AM), a 543,82 km em linha reta." (sem referência, o motivo do motor), com "Mudar o território
      base"; o resumo do Território de referência ganha "· território base: …";
    - no mapa, a ligação da base vem sempre (mesmo com 30 marcadas), com o anel, e o aviso `mapa-ligacoes` diz "o território
      base ou um município marcado".
    A escolha é só estado visual: um passo do Desfazer ("Escolher BOA VISTA (RR) como território base"; "Voltar a todos os
    selecionados, sem território base"), guardada no estado salvo, sem nenhum pedido novo ao motor.
  - **Mapa, com ou sem base:** o enquadramento inicial e o "Ver tudo" cobrem também as referências desenhadas
    (`limitesComReferencias`), e a de fora do resultado ganha o nome "· referência" quando uma ligação chega até ela.
  - **Motor** (`/api/painel`, por elegibilidade): cada membro da referência leva também `uf`, `populacao`, `quantidade` e
    `densidade` na competência, lidos das mesmas medidas dos itens.
- **Permanece:** o cálculo (os elegíveis, a relação, as distâncias, nunca o próprio município) e o pedido ao motor, igual com ou
  sem base; a referência pelo nome (o membro continua como item, a distância zero, com a mira); a frase-resumo, os grupos, a
  régua, os filtros, a tabela e o CSV, nos quais a bolha de contexto não entra (a mesma unidade em análise continua com a sua
  bolha); o clique na bolha, que continua só marcando (Comparar e as ligações); a aba Seleção, só da seleção (decisão de
  24/10/2026); e nada da base vai ao provedor de IA.
- **Motivo:** relato e pedido do responsável em 25/10/2026 ("não aparece o território de referência no gráfico […] ele tem que
  trazer o território de referência para olhar"; "só selecionar no gráfico […] não fica tão intuitivo"; "território base,
  território de referência", no painel do lado). Diagnóstico: o motor estava certo; o gráfico só desenha as unidades em análise;
  no mapa, o quadro e os nomes só consideravam os itens. O responsável escolheu, entre as opções apresentadas: o território base
  no início do painel da Análise Espacial (e não na aba Seleção, o que mudaria a decisão de 24/10/2026); no gráfico, os
  selecionados com a referência da base como bolha de contexto ligada a ela; e o clique na bolha só marcando.
  - **Classificação, pela leitura, antes de codar:** mudanças previstas: decorrem do pedido e não contrariam a SPEC. A base é
    estado visual (RQ-REP-06); mostrar a referência não cria operação comparativa (CAP-REF-01: nada é calculado entre as duas);
    todo número vem do motor (Adendo BOL e RQ-REP-09: a densidade, a população e a distância); a posição no 0 km é a mesma da
    referência escolhida pelo nome, que o gráfico já desenha a distância zero com a mira; o mapa só lê as coordenadas
    autorizadas do motor (RQ-REP-07).
- **Documentação e testes:**
  - **Documentação:** `Docs/PAINEL_INTEGRADO_INTERFACE.md` (o Território base na análise espacial, o que a área entrega ao mapa
    e os testes), `Docs/MAPA_DA_PAGINA_UNICA.md` (as codificações, a decisão 3 de 25/10/2026, o gancho `referencias` e os testes),
    `Docs/PAINEL_INTEGRADO.md` (o contrato de `referencia.membros`) e `README.md`.
  - **Testes novos:** Node, `areaDeAnalise.test.mjs` (as opções da base; o par por elegibilidade, com a referência fora e dentro
    da análise, pelo nome, no empate e sem referência; os textos e a dica; o pedido igual com e sem base; o estado salvo; a escala
    do gráfico com a referência de contexto) e `mapa.test.mjs` (`limitesComReferencias`); roteiro `ui_mapa.py`, passo 11c (base
    versionada: BOA VISTA como base com a referência no Brasil inteiro e densidade acima de 2; a bolha de contexto com o id, a
    densidade e a população do motor, à esquerda de todas as bolhas; a ligação, o anel da base e a legenda; no mapa, a
    referência à vista e com o nome; nenhum pedido novo ao motor).
  - **Teste mudado de propósito** (o motor mudou por este pedido; o teste estava certo): `test_painel_pagina.py`
    (`test_eligible_reference_filters_first_then_takes_the_nearest_without_the_territory_itself`), que continua conferindo o bloco
    `referencia` inteiro, agora com a UF e os valores de cada membro, contra o catálogo sintético e contra os itens.

### 2026-10-25 · Base municipal: a linha de SANTAREM (PB) em junho de 2016 com a UF, a região, a coordenada e a população certas
- **Antes:** a linha 21 de `Dados_Municipios_Brasil.csv` (`Norte;PA;SANTAREM;251365;-2,43;-54,72;MEDICINA;2016;6;0;331942`)
  trazia o código de SANTAREM (PB) com a região, a UF e a coordenada de SANTAREM (PA) e 331.942 habitantes (a população de
  SANTAREM (PA) no Censo 2022). Em junho de 2016:
  - SANTAREM (PB) ficava no Pará, no mapa e nas distâncias (análise espacial, referência mais próxima e critérios com
    distância), com 331.942 habitantes e densidade 0 (nenhum médico na linha);
  - a população da Paraíba (a soma dos seus municípios, UF-POP-MUNICIPIOS-1) ficava em 4.328.672 (3.999.415 em janeiro), e a
    densidade do estado, em 1,2750 por 1.000 habitantes;
  - a população do Brasil de 2016 (BR-POP-JUNHO-1: a de junho, usada também em janeiro) somava 206.413.387, com a densidade do
    Brasil em 1,6327 em janeiro e 1,6604 em junho;
  - as análises com o Brasil, a Paraíba ou os municípios nessa competência traziam a nota "Em junho de 2016, 1 registro(s) da
    fonte municipal trazem na coluna uf um estado diferente do indicado pelo código IBGE (251365); …"
    (`UF_DECLARADA_DIVERGENTE`), e o pré-exame dava ao 251365 a nota de hierarquia (`hierarchy_note`, só na API);
  - nove municípios tinham coordenadas válidas que mudam entre competências (o 251365, entre eles).
- **Agora:** a linha passa a `Nordeste;PB;SANTAREM;251365;-6,484055297;-38,47915221;MEDICINA;2016;6;0;2685`:
  - **região, UF e coordenada:** as das outras 21 linhas do 251365 (a sede de SANTAREM, PB);
  - **população:** 2.685, a estimativa do IBGE para 1º de julho de 2016 (na tabela enviada ao TCU, o código 2513653 aparece
    como Joca Claudino, o nome atual do antigo Santarém da Paraíba), a mesma da linha de janeiro de 2016;
  - **quantidade:** 0, sem mudança (o responsável confirmou os dados de médicos);
  - **efeitos em junho de 2016:** SANTAREM (PB) fica na Paraíba, com 2.685 habitantes (densidade 0, como antes); a população da
    Paraíba volta a 3.999.415, a mesma de janeiro, e a densidade do estado passa a 1,3800; a do Brasil de 2016 passa a
    206.084.130, com a densidade em 1,6353 em janeiro e 1,6631 em junho. A nota de UF divergente e a nota de hierarquia deixam
    de aparecer: nenhuma linha da base tem UF ou região diferente das do código IBGE. Os municípios com coordenadas que mudam
    entre competências passam a oito;
  - **tendência dos estados com as 22 competências:** a Paraíba passa de Sem classificação (mudança de direção: a densidade
    caía em junho de 2016 e voltava a subir) a Crescimento; os 27 estados ficam com 6 em Crescimento e 21 sem classificação,
    todos por mudança de direção (eram 5 e 22);
  - **nova versão da base:** a fonte municipal tem 9.968.238 bytes e SHA-256 `d244906e6d09…` (antes, 9.968.224 e
    `89c027c90a2d…`); o manifesto foi regravado (versão `c4d82eeee4e4…`; antes, `68944004901c…`). A camada de coordenadas
    (`dados/brasil/complemento_coordenadas.json`) passa a se referir a essa versão (`aplica_se_a`), com os mesmos seis pontos
    (SHA-256 da camada, `4fac87444778…`; antes, `5db726905a91…`): sem isso, ela ficaria `incompativel`, e os seis municípios de
    ponto inválido na fonte perderiam a coordenada.
- **Permanece:** as fontes nacional e estadual e os seus SHA-256; as outras 122.533 linhas da fonte municipal; o nome SANTAREM
  nas 22 linhas do código (o IBGE usa Joca Claudino; a base mantém o nome da fonte); as regras BR-POP-JUNHO-1,
  UF-POP-MUNICIPIOS-1 e `brasil-cod-uf-prefix-1` e o tratamento de uma linha com UF divergente (entra como está, com a nota;
  `UF_DIVERGENTE_EXCLUI` continua falso), coberto pelos testes sintéticos de `test_territorial_levels.py`; os 223 municípios
  da Paraíba; as tendências do Brasil (Crescimento, com 22 e 11 observações) e as dos municípios (a densidade do 251365 em
  junho de 2016 continua 0); os textos da interface (a `hierarchy_note` não é exibida na tela); nada da base vai ao provedor
  de IA.
- **Motivo:** pedido explícito do responsável pelo produto em 25/10/2026, sobre o defeito relatado na entrada seguinte ("trocar
  pelos valores corretos, se você tiver a fonte. Busque os valores corretos"; "os dados de médicos acredito que estejam
  corretos").
  - **Classificação, pela leitura, antes de alterar:** mudança de comportamento (dados versionados), prevista: decorre do pedido
    e não contraria a SPEC (RQ-DAD-03: conteúdo alterado é uma nova versão, que o manifesto identifica) nem a decisão sobre a
    UF divergente, que continua valendo para qualquer linha que a tenha.
  - **Procedimento (AGENTS.md, regra 2):** só a linha 21 substituída (fim de linha CRLF e codificação preservados); manifesto
    regravado (`python backend/brazil_data.py manifesto --gravar`); diff revisado; `python backend/brazil_data.py diagnostico`
    com `"integridade": "verificada"`; camada de coordenadas `valido` para a nova versão.
  - **Fonte dos valores:** a estimativa do IBGE foi conferida por busca na web, sem enviar valor da base (o proxy deste ambiente
    recusa `*.ibge.gov.br`); a região, a UF e a coordenada vêm das demais linhas do próprio código na base.
- **Documentação e testes:**
  - **Documentação:** `README.md` (política dos dados, origem e cobertura e os dez pontos), `Docs/DADOS_BRASIL_VALIDACAO.md`,
    `Docs/ABRANGENCIA_TERRITORIAL.md`, `Docs/MODELO_TERRITORIAL.md`, `Docs/BLOCO1_RESULTADOS_EXPLORAVEIS.md`,
    `Docs/BLOCO2_ETAPA2_CRITERIOS_INTEGRACAO.md`, `Docs/MAPA_DA_PAGINA_UNICA.md`, `Docs/PAINEL_INTEGRADO.md` (o diagnóstico
    de 23/10/2026, com os estados) e o comentário de `UF_DIVERGENTE_EXCLUI` em `backend/territorial_levels.py`.
  - **Testes mudados de propósito** (os dados mudaram; o defeito estava na base, e não nos testes), em
    `test_levels_real_data.py` (job `dados-reais`): a densidade do Brasil em janeiro de 2016 (1,6353) e a população de junho de
    2016 (206.084.130), com a de janeiro conferida à parte (206.084.128, nunca usada); a linha do 251365 em 2016/6 (PB, 2.685);
    a PB em 2016/6 (3.999.415, a mesma de janeiro); a ausência da nota de UF divergente no Brasil e nos estados e da nota de
    hierarquia em todos os municípios; as regiões e as UFs da fonte municipal iguais às do código IBGE, sem exceção. Em
    `test_painel_tendencia.py` (job `dados-reais`): os estados com as 22 competências passam a 6 em Crescimento e 21 sem
    classificação, com a PB em Crescimento (classe conferida por leitura independente da DA-15, antes e depois).

### 2026-10-25 · Página única: Desfazer no lugar de Voltar, todas as unidades em análise no mapa, o aviso "Fora do gráfico", bolhas sem esmaecer e legenda de tamanho na proporção exata
- **Antes:**
  - **Voltar (item 4 do pedido):** o controle global do alto se chamava "Voltar" (`analise-voltar`), com a seta ← (`ArrowLeft`).
    O `title` dizia "Voltar: desfaz abrir a Análise de Tendência" (sem passos, "Voltar: nenhuma ação para desfazer ainda"), e o
    aviso, "Voltar: Abrir a Análise de Tendência desfeito.". Os avisos da Seleção, de Limpar seleção e de Limpar filtros diziam
    "Para desfazer, use Voltar[, no alto]."; os da navegação pela bolha e pelo atalho do mapa, "Para voltar aos estados, use
    Voltar, no alto.". A barra dos dois controles tinha o nome acessível "Voltar e limpar seleção".
  - **Mapa (item 1):** recebia os mesmos itens do gráfico. A unidade sem o valor que a posiciona no gráfico (a distância até o
    território de referência, o indicador ou a coorte) sumia também do mapa, embora tivesse coordenada. Em Roraima, na Análise
    Espacial com o território de referência no mesmo estado e densidade acima de 2,36 (ou população acima de 100.000), só BOA
    VISTA atende à condição, e ela nunca é a sua própria referência: ficava fora do gráfico, do mapa e da tabela, só em Não
    avaliáveis, com o motivo. Nada avisava junto do desenho, além da contagem da frase-resumo ("1 município sem distância.").
  - **Bolhas (item 2):** marcar bolhas (clique, Enter ou a caixa da tabela dos Detalhes, como para ver as ligações da análise
    espacial ou para Comparar) esmaecia as demais a 22% de opacidade; no modo leve (mais de 400 bolhas), a camada inteira ficava
    a 30%.
  - **Legenda de tamanho (item 3):** das três referências redondas (1, 2 ou 5 × 10ⁿ), a menor podia ficar abaixo do raio mínimo
    visível e ser desenhada no mínimo, maior do que a área dela: no gráfico de Roraima, "5 mil hab." a 4 px, no lugar de 3,5 px;
    no mapa de PORTO ALEGRE (RS) e PORTO ALEGRE DO NORTE (MT), "20 mil" a 2,5 px, no lugar de 1,9 px.
- **Agora:**
  - **Desfazer:** o controle se chama "Desfazer" (`analise-desfazer`), com a seta curva do desfazer (↶, `Undo` do lucide, o
    símbolo do Ctrl+Z), no lugar de "Voltar", que parecia levar ao começo da sessão. O `title` e o nome acessível dizem o que o
    próximo clique desfaz ("Desfazer: abrir a Análise de Tendência", o passo sem o ponto final; sem passos, "Nada para desfazer
    ainda"), e o aviso, o que foi desfeito ("Desfeito: abrir a Análise de Tendência."). Os avisos passam a "Para desfazer, use o
    botão Desfazer, no alto.", "… Para desfazer, use o botão Desfazer." e "Para voltar aos estados, use Desfazer, no alto."; a
    barra, "Desfazer e limpar seleção". O que o controle faz não mudou (os mesmos passos, até 80, sem Refazer).
  - **Mapa:** todas as unidades em análise (`itensParaOMapa`), também as que o gráfico deixa de fora, cada uma no lugar dela:
    com a pintura da camada (na análise espacial, o quintil do indicador do motor; BOA VISTA fica no 5º) ou, sem valor nela,
    vazada; a cor única, sem camada, fica vazada para a unidade sem o valor do indicador (`pintar`). A dica traz o motivo
    ("Distância: Não avaliável", com o texto do motor). A régua e os filtros esmaecem pelos mesmos critérios do gráfico
    (`dentroDosFiltros`); sem o valor do indicador e com a régua em uso, a unidade esmaece, nunca some.
  - **Fora do gráfico:** com o gráfico à vista, acima do desenho, `analise-fora-do-grafico` (`textoForaDoDesenho`) diz quem ficou
    de fora e por quê, pelo nome: "Fora do gráfico, sem distância até a referência: BOA VISTA (RR). O motivo está em Não
    avaliáveis, nos Detalhes; no mapa, o município aparece no lugar dele." Três motivos (sem valor do indicador na competência,
    sem distância até a referência, sem coorte inicial avaliável), até cinco nomes por motivo, com "e mais N"; nas planilhas,
    com os nomes delas. Não aparece quando nenhum território ficou com referência (vale o aviso `analise-ref-sem-resultado`), na
    Série temporal nem com só o mapa à vista.
  - **Bolhas:** marcar não esmaece as demais (`opacidadeDaBolha`): as marcadas ganham o anel escuro e o nome, como no mapa. A
    pintura apagada (não atende, fora dos primeiros) continua mais clara (45%), e o modo leve continua semitransparente (62%),
    pela sobreposição de milhares de bolhas.
  - **Legenda de tamanho:** todas as referências na proporção exata (`valoresDaLegendaDeTamanho` no gráfico e `marcasDeTamanho`
    no mapa): a que ficaria abaixo do mínimo visível dá lugar ao menor número redondo que já o alcança, ou sai, se repetiria a
    anterior. Em Roraima: 200 mil, 50 mil e 10 mil habitantes no gráfico; 200 mil, 50 mil e 20 mil no mapa.
- **Permanece:**
  - Os números e os métodos: as distâncias (CAP-ESP-01 e CAP-ESP-02), o território de referência por elegibilidade, os quintis do
    mapa (CAP-DIS-02), a fórmula do tamanho (área proporcional à população, com o raio pela raiz quadrada; o raio máximo, de 12 a
    34 px no gráfico e de 16 px no mapa, vai para o maior valor do resultado; os mínimos visíveis de 4 e 2,5 px), a régua, as
    condições, a ordenação, Comparar, Juntar e as rotas do motor (nada mudou no backend).
  - O gráfico continua sem desenhar quem não tem a distância ou o indicador (à parte, com o motivo: RQ-REP-04 e Adendo BOL); a
    tabela dos Detalhes continua com os mesmos itens do gráfico, e Não avaliáveis, com o motivo de cada um.
  - "Voltar aos estados" (`analise-grupo-voltar`), "Voltar ao gráfico" e "Voltar ao último gráfico calculado" continuam: são
    navegação, não o desfazer.
  - O nome de Porto Alegre (item 5): conferido, sem mudança. A base escreve "PORTO ALEGRE" (431490, RS) nas 22 linhas, e a tela
    mostra "PORTO ALEGRE (RS)" na Seleção, no título, na frase-resumo, na dica, na tabela e no mapa. Os nomes da base vêm em
    maiúsculas e sem acento ("SAO PAULO", "UIRAMUTA"); Porto Alegre não tem acento.
  - Os dados versionados não mudaram nesta entrada (a linha 21 foi corrigida depois, na entrada acima), e nada da base vai ao
    provedor de IA.
- **Motivo:** pedido do responsável pelo produto em 25/10/2026 (cinco pontos, na branch de ajustes de UX): municípios de
  Roraima que "não apareciam na análise espacial, na análise de tendência, como se tivesse algum problema nas coordenadas
  geográficas", com a revisão geral das coordenadas ("todos os municípios precisam estar representados ao serem selecionados");
  as bolhas "esmaecidas, com pouca cor" no gráfico da análise espacial; a verificação da proporcionalidade das bolhas; "Desfazer",
  com a seta redonda do desfazer, no lugar de "Voltar"; e o nome de Porto Alegre.
  - **Classificação, pela leitura, antes de codar:**
    - **Mapa com todas as unidades e o aviso "Fora do gráfico":** mudança prevista. Decorre do pedido e não contraria a SPEC:
      RQ-REP-04 (não avaliável distinto de zero, com legenda: o anel tracejado), RQ-REP-07 e RQ-REP-09 (o mapa só lê as
      coordenadas autorizadas do motor; nada é calculado) e o Adendo BOL (no gráfico, os não avaliáveis ficam à parte, com o
      motivo: o aviso os nomeia).
    - **Bolhas sem esmaecer:** mudança prevista. A seleção é estado visual (RQ-REP-06), e nada na SPEC pede o esmaecimento.
    - **Legenda de tamanho:** mudança prevista. A verificação pedida achou a imprecisão, e o Adendo BOL pede área proporcional e
      legenda.
    - **Desfazer:** mudança prevista. Decorre do pedido; a decisão de 24/10/2026 já descrevia o controle como "um desfazer
      sequencial, como o Ctrl+Z".
    - **Revisão das coordenadas e o nome de Porto Alegre:** conferências, sem mudança de comportamento.
  - **Diagnóstico de Roraima:** o motor devolve os 15 municípios de Roraima com coordenada e valores (`/api/painel/mapa` e
    `/api/painel`), e a tela desenha todos eles na Distribuição e na Tendência (no gráfico e no mapa das visões Tendência e
    Trajetória; a Série temporal é só do gráfico e, com mais de 12 unidades, pede a escolha de até 12, pela decisão 6 verificada
    em 25/10/2026). O que sumia era a unidade sem
    distância na Análise Espacial: Roraima tem 15 municípios, e só BOA VISTA passa das condições comuns (densidade acima da
    taxa do Brasil, população acima de 100.000); no mesmo estado, ela fica sem território de referência e saía do gráfico, do
    mapa e da tabela. Com "No Brasil inteiro" e população acima de 100.000, a referência dela é MANAUS (AM), a 662 km.
  - **Revisão das coordenadas (só leitura, pela rota do mapa, nas 22 competências):** as 5.570 sedes municipais têm coordenada
    válida em todas as competências em que o município tem registro (os sem registro numa competência, como CRISTAL DO SUL (RS)
    em 2015, ficam sem ponto nela, com o motivo); todas dentro do Brasil e perto dos demais municípios do estado (as duas mais
    afastadas, AFRANIO e FERNANDO DE NORONHA (PE), estão certas: o extremo oeste do estado e a ilha), nenhuma com latitude e
    longitude trocadas, nenhuma duas no mesmo ponto; os seis pontos inválidos da fonte seguem complementados pela camada governada. Oito municípios têm
    pequenas diferenças de coordenada entre as competências (até 6,5 km, em SUCUPIRA (TO)), cada competência com um ponto só.
    **Um defeito na base, fora das coordenadas da sede:** a linha 21 de `Dados_Municipios_Brasil.csv`
    (`Norte;PA;SANTAREM;251365;-2,43;-54,72;MEDICINA;2016;6;0;331942`) traz o código de SANTAREM (PB) com a UF, a coordenada e a
    população de SANTAREM (PA), que tem a sua própria linha em junho de 2016 (código 150680). Em junho de 2016, SANTAREM (PB) fica
    no Pará, com 331.942 habitantes e nenhum profissional (densidade 0); a população da Paraíba nessa competência fica em
    4.328.672 (3.999.415 em janeiro), e a do Brasil de 2016, que segue junho (BR-POP-JUNHO-1), também a inclui. A correção muda
    dados versionados e depende de pedido explícito do responsável (AGENTS.md, regra 2): ficou pendente, com duas propostas
    (tirar a linha, e SANTAREM (PB) fica sem registro em junho de 2016, como os demais municípios sem registro numa competência;
    ou trocá-la pelos valores certos, com a fonte). O responsável escolheu a segunda: a correção está na entrada acima ("Base
    municipal: a linha de SANTAREM (PB) em junho de 2016…").
  - **Verificação da proporcionalidade:** com os 15 municípios de Roraima no gráfico, o raio de cada bolha é igual, com duas
    casas, ao da área proporcional à população (BOA VISTA, a maior, no raio máximo; SAO LUIZ, a menor, a 4,37 px). A impressão de
    bolhas maiores tem duas origens: a escala é relativa à maior população do resultado (com só municípios pequenos, o maior
    deles fica no raio máximo, como São Paulo numa seleção que o tenha), e o mínimo visível iguala os muito pequenos (dito na
    legenda). O único desvio era a menor referência da legenda, corrigido aqui.
- **Documentação e testes:**
  - **Documentação:** `Docs/PAINEL_INTEGRADO_INTERFACE.md` (a seção "Desfazer e Limpar seleção", o que a área entrega ao mapa,
    "Fora do gráfico", o tamanho e a legenda, a seleção sem esmaecer e os testes), `Docs/MAPA_DA_PAGINA_UNICA.md` (os itens do
    mapa, a legenda, as decisões de 25/10/2026 com a revisão das coordenadas e os testes),
    `Docs/INTERFACE_CONVERSACIONAL_INTEGRADA.md` (o Desfazer do pedido da conversa), `README.md` e a tabela de cobertura de
    `backend/tests/legado/README.md`.
  - **Testes novos:**
    - **Node:** `areaDeAnalise.test.mjs` (o mapa com todas as unidades em análise e a ordem; os filtros que esmaecem nele, com
      a régua, "Mostrar só quem atende" e a classe; a cor única vazada sem o indicador; o aviso "Fora do gráfico", com um e dois
      motivos, a contagem, a planilha no feminino, o conjunto e a rotatividade; a opacidade que não depende da seleção; os textos
      do Desfazer e do Desfeito); `painel.test.mjs` (a legenda de tamanho de Roraima na proporção exata e o gráfico estreito);
      `mapa.test.mjs` (as marcas do mapa na proporção exata).
    - **Roteiros:** `ui_mapa.py` (Roraima inteira com o território de referência no mesmo estado e densidade acima de 2,36: BOA
      VISTA sem distância, fora do gráfico com o aviso pelo nome e no mapa, no lugar dela, com a cor do quintil, junto dos outros
      14; os quintis do mapa; as legendas de tamanho do gráfico e do mapa na proporção exata); `ui_area_de_analise.py` (as
      bolhas marcadas para Comparar sem esmaecer as demais; o Desfazer com a seta curva, `lucide-undo`, o único
      `analise-desfazer` da área).
  - **Testes mudados de propósito** (o comportamento mudou por este pedido; os defeitos estavam no produto, e não nos testes):
    - **O nome e os textos do Desfazer:** `ui_area_de_analise.py`, `ui_conversa_grafico.py` e `ui_modo_escuro.py` (o seletor
      `analise-desfazer`, o nome do botão, o `title`, o aviso "Desfeito: …" e "use o botão Desfazer"; a ausência de
      `analise-desfazer`, que valia para o Desfazer antigo da Seleção, passa a "um só, o do alto"); `areaDeAnalise.test.mjs`
      (`textoDoVoltar` deu lugar a `textoDoDesfazer` e `textoDoDesfeito`).
    - **`ui_mapa.py`:** `com_ponto` (o que o mapa desenha) passa a ser as unidades com coordenada, também sem o indicador; a
      régua conta como fora do corte quem não tem o indicador.
    - **`mapa.test.mjs`:** as marcas da legenda com 12 milhões no máximo passam de 10 mi, 2 mi e 200 mil (esta desenhada no
      mínimo visível, maior do que a área dela) a 10 mi, 2 mi e 500 mil, todas na proporção exata.

### 2026-10-24 · Página única: nome da plataforma, Voltar e Limpar seleção globais, Seleção em duas áreas, Território de referência por elegibilidade e as visões Tendência, Trajetória e Série temporal
- **Antes:**
  - **Nome (item 1):** a abertura (E0) dizia "Diagnóstico Territorial da Força de Trabalho em Saúde".
  - **Voltar e Limpar (itens 2 e 3):**
    - O Voltar, acima do título, desfazia só navegações (a bolha de um estado, o atalho do mapa e uma mudança de territórios
      pedida na conversa) e sumia sem navegação. Uma mudança à mão esvaziava a pilha.
    - Na Seleção, "Limpar a seleção de municípios" (ou "de estados") e o "Desfazer" depois de uma mudança coletiva
      (`analise-desfazer`, com o aviso `analise-desfazer-aviso`); nas análises, "Desfazer a limpeza"
      (`analise-desfazer-filtros`).
    - "← Voltar aos estados", na lista aberta de um estado, era um botão secundário pequeno.
  - **Seleção (item 4):** a lista, com a busca no alto, e "Na análise" presa à base da tela (no celular, no fim da lista),
    estado a estado, só com o × do estado inteiro; os municípios marcados apareciam como texto, e a lista se recolhia acima de 6
    linhas ("Ver quais (N)").
  - **Abas (item 5):** os botões das análises tinham uma linha de apoio ("Indicador de cada território", "Distância até uma
    referência", "Mudança e tendência no tempo", "Só com os dados enviados").
  - **Análise Espacial (item 6):** o painel "Referência da distância" tinha três caminhos: por critério (a lista de candidatos
    de `/api/painel/referencias`, na ordem do motor, com "Usar o primeiro" e a escolha no empate), pelo nome (a busca) ou por
    um conjunto (a distância até o membro mais próximo). O mesmo município podia ser a referência de todos, inclusive dele
    mesmo (distância zero).
  - **Comparar e Juntar (item 7):** os painéis repetiam os itens escolhidos em retângulos grandes, com os dados de cada um.
  - **Tendência (itens 8, 9, 10 e 12):**
    - "Entenda esta análise" abria na primeira visita também na Tendência.
    - O Período começava sem escolha (decisão 5a), e nada de tendência era pedido até a escolha; a vista do desenho era a que
      estivesse em uso.
    - O desenho ficava abaixo do título, com a legenda e as contagens acima dele, como nas outras análises.
    - As visões se chamavam Classes (o quadro de setas), Mudança e Séries; as Séries mostravam só os 4 períodos da janela, com
      as velocidades da unidade em foco.
  - **Termos de bastidor (item 11):** a coluna do quadro de setas era "Classe (do motor)", e textos da tela e da conversa
    falavam em "motor" ("Limitação registrada pelo motor: …", "Parâmetros enviados ao motor", "maior, menor e diferença vêm do
    motor", "Percentuais e contagens do motor", "O CSV traz os valores do motor…", "o motor Python e os controles continuam
    funcionando", "aplicada pelo motor", "suportado pelo motor experimental").
  - **Motor (`/api/painel`):** a referência era só por membros (`{membros, criterio}`), e não havia a série temporal. A recusa
    da ordenação pela variação sem a competência inicial citava a "visão Mudança".
- **Agora:**
  - **Nome (item 1):** "Diagnóstico Territorial da Força de Trabalho na Saúde", o nome da plataforma (o do cabeçalho e da
    SPEC), no título central de E0; o cabeçalho no alto à esquerda continua como estava.
  - **Voltar e Limpar seleção (item 2):** dois controles globais, lado a lado, fixos no alto da área ao rolar, em todas as abas
    (`analise-controles-globais`):
    - **Voltar** (`analise-voltar`, a seta ←) é um desfazer sequencial, como o Ctrl+Z, de toda a interação na área: a
      seleção (uma a uma, coletiva, o × da lista da direita, o nível, a lista aberta), os conjuntos, as abas, os ajustes (o
      período, a visão, o intervalo da série, o território de referência…), os filtros, a régua (o arraste vira um passo só),
      a escala, a vista, um pedido da conversa e a reabertura do Histórico. Cada Voltar desfaz um passo, até 80; o botão diz o
      que vai desfazer ("Voltar: desfaz abrir a Análise de Tendência") e, sem nada a desfazer, fica desligado, com "Voltar:
      nenhuma ação para desfazer ainda". Não é o voltar do navegador.
    - **Limpar seleção** (`analise-limpar-selecao`, a vassoura) tira os territórios do nível em uso, porque cada nível guarda
      a sua escolha (em Municípios, os municípios e os conjuntos; em Estados, os estados), sem apagar os dados carregados, os
      ajustes nem a escolha dos outros níveis. Fica desligado sem nada marcado no nível em uso e no nível Brasil, em que o país é
      a própria unidade ("No nível Brasil, o país inteiro é a unidade em análise: não há seleção para limpar."). É o único
      "limpar a seleção": o da Seleção saiu.
    - Saíram o "Desfazer" da Seleção (`analise-desfazer`, `analise-desfazer-aviso`) e o "Desfazer a limpeza"
      (`analise-desfazer-filtros`): o Voltar faz o mesmo. O aviso de uma mudança coletiva continua por escrito
      (`analise-selecao-aviso`, "… Para desfazer, use Voltar, no alto."). "Limpar filtros" continua.
  - **Voltar aos estados (item 3):** maior e preenchido, com a seta à esquerda, distinto do Voltar do alto; só fecha a lista.
  - **Seleção em duas áreas (item 4):** à esquerda, a busca no alto e a lista (`analise-territorios-lista`); à direita, sempre
    à vista e em tempo real, o que está marcado, agrupado por estado (`analise-selecionados-itens`), com o × de cada município
    (`analise-selecionado-unidade`), de cada estado (`analise-selecionado-tirar-grupo`) e de cada conjunto
    (`analise-selecionado-conjunto`), sem recolher. Abaixo de 900 px, uma sobre a outra, com o que está marcado antes da lista.
  - **Abas (item 5):** só os nomes das análises.
  - **Território de referência (item 6):** o painel "Território de referência" (o título "Referência da distância" saiu) é um
    fluxo só: a relação (Mais próximo ou Mais distante), a delimitação geográfica (no Brasil, o mesmo estado, estados
    escolhidos, a mesma região, regiões escolhidas ou o Brasil inteiro; numa planilha, a província da coluna-mãe ou a planilha
    inteira), o atributo (Densidade, Quantidade ou População), o operador (Maior que ou Menor que) e o valor de corte, com a
    unidade e a validação do atributo. Nenhum campo tem valor padrão; a prévia diz a definição em palavras. O motor primeiro
    filtra os elegíveis e depois escolhe, para cada município, o mais próximo ou o mais distante deles, nunca ele mesmo, com os
    empates, pelas mesmas geodésicas; sem elegível ou com coordenada faltando, a distância fica não avaliável, com o motivo,
    nunca zero. Quando nenhum município em análise fica com referência, um aviso acima do desenho diz o que aconteceu
    (`analise-ref-sem-resultado`: "Nenhum município da base atende à condição …: não há território de referência. Mude o
    atributo, o operador ou o valor de corte." ou as causas possíveis), com "Mudar o território de referência". A seleção e o
    território de referência se mantêm um sem o outro, e o painel reabre com a definição em uso. A
    lista de candidatos ("Usar o primeiro") e a escolha pelo nome ou por um conjunto saíram da tela (a referência pelo nome,
    pedida na conversa, continua valendo).
  - **Comparar e Juntar (item 7):** sem os retângulos; o botão, o título do painel, uma orientação objetiva
    (`analise-comparar-orientacao`, `analise-juntar-orientacao`), os itens escolhidos numa lista curta e o resultado.
  - **Tendência (itens 8, 9, 10 e 12):**
    - "Entenda esta análise" começa recolhido na Tendência desde a primeira visita (nas outras análises, como antes).
    - A aba abre no Período **Anual** (sem ele na base, no único ritmo que ela tem) e na vista **Gráfico**; o mapa continua
      como alternativa.
    - Os ajustes em cima; abaixo, as ferramentas e o desenho em destaque; à direita, o painel "Como ler"
      (`analise-explicacao`), com o subtítulo, a frase-resumo, as contagens, a legenda e as velocidades da linha escolhida,
      separado do desenho por uma divisória arrastável e ajustável pelo teclado (`analise-divisoria`), entre 240 px e a metade
      da área.
    - As visões **Tendência** (o quadro de setas), **Trajetória** (a mudança, agora com os períodos do meio no caminho do
      rastro e na dica) e **Série temporal** (a série histórica completa, lida dos dados, ou o intervalo escolhido em "De" e
      "Até", com "Toda a série"; sem classificação, sem linha ajustada e sem preencher lacunas; o conjunto não comparável fica
      só com os pontos). Trocar de visão não refaz a seleção.
  - **Termos de bastidor (item 11):** a coluna é "Tendência"; os textos da tela e da conversa não falam em "motor" ("Limitação
    registrada no cálculo: …", "Parâmetros da análise", "com o maior, o menor e a diferença", "Percentuais e contagens da
    análise"…). Os nomes internos (código, chaves do contrato, `visao: "classes" | "mudanca" | "series"`) não mudaram.
  - **Motor (`/api/painel`):**
    - `referencia: {relacao, delimitacao: {tipo, valores?}, condicao: {atributo, operador, valor}}`, só na página única e
      no nível municípios, com a validação e os textos descritos em `Docs/PAINEL_INTEGRADO.md`; a resposta traz
      `referencia.tipo: "elegiveis"` (a definição, os textos, as contagens da condição e os territórios usados) e, por item,
      `referencia_do_item`. A busca do extremo é exata (`nearest_reference.extreme_exact`): só geodésicas de Karney decidem;
      os limites (a corda 3D e, na mais distante, o arco na esfera de raio a) só poupam geodésicas que não podem decidir.
    - `serie: {competencias}` devolve o valor observado de cada item em cada competência do intervalo (municípios,
      conjuntos, estados e Brasil), pelas mesmas funções da tendência, com o topo `serie`, `dominios.serie`, a nota e o trecho
      da frase-resumo.
    - A recusa da ordenação pela variação cita a "visão Trajetória".
  - **Conversa:** "trajetória" abre a visão Trajetória; "série temporal" ou "séries históricas", a Série temporal; as respostas
    usam os nomes novos ("Visão da tendência: Trajetória."); o critério de referência ("use como referência o município de
    maior densidade") abre o Território de referência com o atributo citado e o operador do "maior" ou "menor" ("Maior que"
    ou "Menor que", com o aviso `analise-ref-da-conversa`), e a relação, a delimitação e o valor de corte ficam com a pessoa.
- **Permanece:**
  - Os métodos e os números: CAP-ESP-01 e CAP-ESP-02 (Karney, `minimo_completo`, empates), CAP-TEN-01 e DA-15, CAP-TMP-01,
    CAP-SUB-01/02/03, CAP-AGR-01; nenhum método novo.
  - A referência por membros (`{membros}`, como pede a conversa pelo nome), a rota `/api/painel/referencias` (a tela não a usa
    mais), o contrato sem `nivel`, o Histórico, Nova análise e Nova sessão, o mapa e as vistas, "Limpar filtros", a Seleção
    por níveis e cumulativa, o cabeçalho.
  - Os dados versionados não mudam, e nada da base vai ao provedor de IA.
- **Motivo:** pedido do responsável pelo produto em 24/10/2026, "Implementação integral de ajustes de interface, navegação e
  experiência do usuário no Agente Diagnóstico Territorial da Força de Trabalho na Saúde" (12 requisitos).
  - **Classificação, pela leitura, antes de codar:** todos os itens são mudança de comportamento prevista: decorrem do pedido
    e não contrariam a SPEC nem as divergências aprovadas.
    - **Território de referência (item 6):** CAP-REF-01 admite o conjunto produzido por critério autorizado aplicado aos dados
      (CAP-SUB-01); para cada município, o conjunto é a delimitação E a condição E "não pertence a [ele mesmo]" (a pertença a
      uma lista é atributo de CAP-SUB-01). O mais próximo é CAP-ESP-02 (`minimo_completo`); o mais distante, as distâncias de
      CAP-ESP-01 ordenadas (CAP-SUB-02) com a 1ª posição (CAP-SUB-03). As regiões seguem o primeiro dígito do código IBGE, a
      regra já usada na conversa. Nada é presumido: sem a definição completa, nenhum pedido sai.
    - **Período anual ao abrir (item 9):** a tabela de autoridade (C §5.5) admite a definição do período "quando por regra";
      a regra é a decisão do responsável, à vista e trocável, e o pedido ao motor continua explícito
      (`tendencia.competencias`). Com um só ritmo aplicável, RQ-GOV-14. Substitui a decisão 5a da rodada anterior.
    - **Série temporal (item 12):** CAP-REP-02 e Parte 13 (sem linha ajustada), RQ-REP-15 (agregados incomparáveis sem
      linha); os valores são os observados, sem método novo.
    - **Os demais (1 a 5, 7, 8, 10 e 11):** apresentação, navegação e textos, sem regra da SPEC em contrário.
    - **Correções de 25/10/2026 (decisões 4 e 5):** mudança prevista. Decorrem das diretrizes 4 e 5 do responsável e dos
      itens 2 e 6; a condição continua a de CAP-SUB-01, com o valor de corte decidido pela pessoa, e a limpeza por nível
      restabelece a regra já aprovada ("Cada nível guarda a sua escolha").
  - **Decisões verificadas em 25/10/2026** (as sete diretrizes do responsável, conferidas com o pedido original, o
    AGENTS.md, a SPEC e o contrato):
    1. **Território de referência:** o fluxo único é exigência do pedido ("Elimine controles redundantes e substitua a
       configuração fragmentada por um fluxo único"); por isso saíram do painel a lista de candidatos, a busca pelo nome e a
       escolha por conjunto. A conversa ainda aceita a referência pelo nome ou por um grupo (CAP-REF-01, lista explícita da
       pessoa), que aparece como "Referência em uso".
    2. **Período da tendência:** o Anual é o preferido (item 9). Sem 4 períodos anuais, abre no único ritmo com 4 períodos
       (RQ-GOV-14: um único valor aplicável resolve o parâmetro, sem substituir o pedido explícito; DA-15; a matriz de
       autoridade da SPEC admite a definição "quando por regra"); sem nenhum, nada é escolhido e um aviso pede a escolha.
    3. **Velocidades:** no painel "Como ler" da visão Tendência (itens 10 e 12), com as barras, os valores e a interpretação;
       continuam nas setas do quadro, na dica e no CSV.
    4. **Conversa (corrigida em 25/10/2026):** o "maior" ou "menor" ficava sem efeito; agora vira o operador da condição.
       Escolher sozinho o primeiro colocado não é operação autorizada: CAP-REF-01 pede uma condição de CAP-SUB-01, e o valor de
       corte é da pessoa.
    5. **Voltar e Limpar seleção (corrigida em 25/10/2026):** o Voltar desfaz até 80 passos e não há "Refazer". Limpar
       seleção apagava a escolha de todos os níveis e, no Brasil, trocava para Municípios; agora limpa só o nível em uso e fica
       desligado no nível Brasil, com o motivo.
    6. **Série temporal:** abre com a série inteira; o desenho mostra até 12 unidades (as marcadas ou, sem marcação, todas
       quando são até 12), e o cálculo e o CSV cobrem todas as unidades da seleção.
    7. **Rota `/api/painel/referencias`:** continua no contrato, com os testes, embora a tela não a use.
- **Documentação e testes:**
  - **Documentação:** `Docs/PAINEL_INTEGRADO_INTERFACE.md` (E0, Seleção em duas áreas, "Voltar e Limpar seleção", ajustes,
    Território de referência, Tendência com o layout e as três visões, títulos, pedido e testes), `Docs/PAINEL_INTEGRADO.md`
    (`referencia` por elegibilidade, `referencia_do_item`, `serie`), `Docs/MAPA_DA_PAGINA_UNICA.md`,
    `Docs/CONVERSACAO_INCREMENTO_FN.md`, `Docs/INTERFACE_CONVERSACIONAL_INTEGRADA.md`, `Docs/EVOLUCAO_TEMPORAL_E_TENDENCIA.md`,
    `README.md` e a tabela de cobertura de `backend/tests/legado/README.md` (o passo 9 com o Território de referência, a visão
    Trajetória e o celular no passo 16, que a tabela ainda dava como 15).
  - **Testes novos:**
    - **Motor:** `test_nearest_reference.py::test_extreme_search_equals_exhaustive_search_without_the_territory_itself` (o
      mais próximo e o mais distante, com e sem a exclusão, contra todas as geodésicas, inclusive polos, antípodas e
      empates); em `test_painel_pagina.py`, o território de referência (o mais próximo sem o próprio município, conferido
      com o critério de densidade da análise existente; o mais distante; as cinco delimitações; sem elegível; um elegível
      sem coordenada; conjuntos; quantidade e população; a validação; a planilha com e sem a coluna-mãe) e a série temporal
      (os mesmos valores das observações da tendência, nos municípios, conjuntos, estados e Brasil, e a validação); com a
      base versionada, `test_real_eligible_reference_matches_every_geodesic_and_the_series_matches_the_trend`.
    - **Conversa (`test_conversa_grafico.py`):** "trajetória", "série temporal" e "séries históricas"; o critério de
      referência com "maior", "menor" e "mais populoso", e o operador na resposta.
    - **Node (`areaDeAnalise.test.mjs`):** o histórico do Voltar, o período com que a tendência abre, as visões e os
      ajustes, a Série temporal (o intervalo, a resposta, o CSV, o método e o desenho), a Trajetória (os períodos do meio no
      rastro e na dica) e o território de referência (a guarda, as delimitações, o valor de corte, a resposta, a dica, o CSV,
      as ligações do mapa e a apresentação); o operador que vem do "maior" ou "menor" da conversa (`operadorDoCriterio`) e a
      limpeza por nível (`limparNivel`).
    - **Roteiros:**
      - `ui_area_de_analise.py`:
        - o nome da plataforma;
        - Voltar e Limpar seleção no alto, fixos ao rolar: o Voltar desligado sem passos, com o texto dele, e o `title` de
          cada passo (uma aba, marcar e desmarcar, o × de um município e de um estado, a bolha, Limpar seleção, a régua, o
          território de referência, o período, a visão, Limpar filtros), com a volta ao estado de antes, um passo por vez;
        - Limpar seleção sem apagar os dados, só no nível em uso (a escolha dos estados continua) e desligado no nível
          Brasil, com o motivo;
        - "Voltar aos estados" preenchido, maior e diferente do Voltar do alto (pelo estilo calculado);
        - as duas áreas da Seleção, com o × de município e de estado;
        - as abas só com o nome;
        - o Território de referência: sem valor padrão; a prévia; o pedido; as distâncias iguais às do motor, nunca até o
          próprio município; o mais distante nunca mais perto que o mais próximo; sem elegíveis, a mensagem
          `analise-ref-sem-resultado` e "Mudar o território de referência"; o Voltar;
        - Comparar e Juntar com a orientação;
        - a Tendência: o Anual (ou o único ritmo) e o Gráfico ao abrir, mesmo com o mapa antes; "Entenda esta análise"
          recolhido; o painel "Como ler" e a divisória pelo teclado, com os limites; a Trajetória com os pontos do meio;
          a Série temporal com toda a série, o intervalo escolhido, o pedido `serie` e o Método;
        - nenhum "motor" nos textos da área, também nos rótulos acessíveis e nos `title`;
        - no celular, os controles do alto e as duas áreas da Seleção.
      - `ui_conversa_grafico.py`: o critério de referência pela conversa ("menor densidade"): o painel com o atributo e o
        operador já escolhidos, a relação, a delimitação e o valor de corte em aberto, e o Voltar que desfaz o pedido.
      - `ui_mapa.py`: o Território de referência no mapa (os elegíveis do mesmo estado acima da mediana da população,
        cada município com a referência entre eles e nunca ele mesmo, as ligações e a mira do território de referência).
      - `ui_modo_escuro.py`: Voltar e Limpar seleção, o aviso da mudança coletiva e o "Voltar aos estados" preenchido,
        legíveis no escuro.
      - `ui_pagina_unica.py`: o nome da plataforma.
  - **Testes mudados de propósito** (o comportamento mudou por este pedido; os defeitos estavam no produto, e não nos testes):
    - **`test_conversa_grafico.py`:** as respostas com os nomes novos das visões, sem "vêm do motor", e o critério de
      referência (antes, "usar o primeiro"). Um texto antigo que restava no produto ("abra a análise espacial" ainda dizia
      "escolha a referência pelo nome, por um critério ou por um conjunto") foi corrigido.
    - **`painel.test.mjs`:** os títulos da Trajetória e da Série temporal, o nome da plataforma, os textos sem "motor", os
      avisos da família, o pedido da Série temporal e `referenciaDoItem` (no lugar de `referencia_mais_proxima` no cliente).
      O teste de "Usar o primeiro" (`primeirosColocados`, que saiu com a lista de candidatos) deu lugar ao das competências; a
      cobertura do território de referência está nos testes novos acima. Os testes de `apoioDaFamilia` (os apoios das abas, que
      saíram) foram retirados.
    - **`areaDeAnalise.test.mjs`:** o nome da plataforma, o motivo do mapa na Série temporal e `referenciaDoItem`.
    - **`conversaGrafico.test.mjs`:** a resposta sobre a tabela, sem "do motor".
    - **Roteiros:** as conferências das funções que saíram passaram às do comportamento novo, com as mesmas checagens
      contra o motor:
      - "Desfazer" e "Desfazer a limpeza" (`analise-desfazer`, `analise-desfazer-aviso` e `analise-desfazer-filtros`) e o
        Voltar só das navegações (que sumia sem navegação): agora, o Voltar do alto, que devolve as mesmas escolhas, e a
        ausência dos botões antigos.
      - "Limpar a seleção (vassoura)" da Seleção, no modo escuro: agora, o Limpar seleção do alto.
      - Limpar seleção de todos os níveis (`ui_area_de_analise.py`, que conferia os estados desmarcados): agora, só o nível em
        uso, com a escolha dos estados guardada.
      - A referência por critério com a lista de candidatos (as posições, o empate, "Usar o primeiro" e os controles
        `analise-ref-*` da lista), em `ui_area_de_analise.py` e `ui_mapa.py`: agora, o fluxo do Território de referência. A
        rota `/api/painel/referencias`, que a tela não usa mais, continua coberta no pytest
        (`test_uploaded_trend_conditions_and_reference_candidates`).
      - O Período sem escolha ao abrir (o aviso "Escolha o período…" e os dois ritmos desmarcados): agora, o Anual (ou o
        único ritmo) já escolhido.
      - A visão Séries (as velocidades nela e o motivo do mapa "Na visão Séries"): agora, a Série temporal, com as
        velocidades no painel "Como ler" da visão Tendência.
      - A legenda e as contagens acima do quadro de setas: agora, no painel "Como ler", com as mesmas conferências.
      - Os nomes das abas: o texto exato, no lugar de "contém", e a ausência dos apoios.
      - O título de E0.
  - Nenhum teste foi enfraquecido, pulado ou apagado sem a cobertura registrada acima.

### 2026-10-24 · Página única: correções da revisão da rodada de interface (Desfazer, Voltar, conjuntos, filtro de classe e textos)
- **Antes** (desde `0874349`):
  - "Desfazer a limpeza" continuava valendo depois de outra escolha de territórios e devolvia a comparação antiga, que o motor
    recusava ("Itens da comparação fora do gráfico").
  - Um pedido da conversa feito com o nível em análise vazio (por exemplo, Estados sem nenhum marcado) trocava a escolha dos
    municípios sem guardar o Voltar, e a escolha de antes se perdia.
  - Juntar ou desfazer um conjunto não invalidava o Voltar e o Desfazer, que depois apagavam o conjunto novo.
  - Desfazer um conjunto comparado deixava-o na comparação, e o motor recusava o pedido.
  - O filtro de classe da tendência podia ficar em uso sem a contagem dele à vista (com um território só ou com zero na classe),
    com o quadro vazio.
  - Um painel de função aberto continuava à vista no nível Brasil, sem efeito.
  - Uma unidade marcada sem grupo da lista não aparecia em "Na análise", e "Ver a análise" e "Limpar" ficavam desligados.
  - Os textos das análises não concordavam com uma unidade feminina da planilha ("cada comuna escolhido", "um comuna").
- **Agora:**
  - "Desfazer a limpeza" vale até a mudança seguinte (um filtro novo ou outra escolha de territórios), e a comparação devolvida
    só continua com os itens na análise.
  - O pedido da conversa guarda o Voltar sempre que havia alguma escolha, em qualquer nível.
  - Juntar ou desfazer um conjunto é uma mudança à mão: esvazia o Voltar e o Desfazer e tira o conjunto desfeito da comparação.
  - A classe do filtro em uso fica sempre à vista, para o filtro poder ser desligado.
  - No nível Brasil, um painel de função aberto fecha.
  - Em "Na análise", as unidades sem grupo da lista ficam numa linha à parte.
  - Os textos concordam com o gênero da unidade ("cada comuna escolhida", "Cada bolha é uma comuna", "Com várias comunas, você
    pode dividi-las").
- **Permanece:** o resto da rodada de `0874349`, os cálculos e os pedidos ao motor (só sem a comparação inválida).
- **Motivo:** defeitos achados na revisão independente do código da rodada, antes do segundo envio. Classificação: correções
  previstas, que fazem o código cumprir o que a entrada de `0874349` e os documentos descrevem, sem contrariar a SPEC.
- **Documentação e testes:**
  - **Documentação:** `Docs/PAINEL_INTEGRADO_INTERFACE.md` (Desfazer, Voltar, "Na análise", contagens por classe e o nível
    Brasil).
  - **Testes:**
    - `painel.test.mjs`: a unidade sem grupo em `marcadasPorGrupo` e a concordância dos textos com "comunas".
    - `ui_area_de_analise.py`: "Desfazer a limpeza" some com outra escolha de territórios.
  - Os testes só ganharam conferências; nenhum foi enfraquecido, pulado ou apagado.

### 2026-10-24 · Página única: duas entradas dos dados, Seleção de Territórios por níveis e cumulativa, Voltar e Limpar, explicações recolhíveis e frase-resumo individual
- **Antes:**
  - **Abertura (E0):** "Diagnóstico territorial da força de trabalho em saúde" e "Escolha os dados para começar", com três
    entradas ("Dados do Brasil", "Enviar meus dados" e "Modelo de planilha XLSX") e o texto "… O aceite de privacidade vem
    antes.". As abas das análises ficavam à vista antes dos dados, e clicar numa delas registrava a intenção ("Você escolheu
    Análise de Tendência. Agora escolha os dados."). Nova sessão, Nova análise (desabilitada) e Histórico ficavam à vista desde
    o início.
  - **Envio:** "Enviar meus dados" abria direto o seletor de arquivos; o modelo de planilha era um botão à parte, na área e na
    conversa (`analise-fonte-modelo`, `chat-fonte-modelo`); "Trocar" trazia as três entradas. A conversa perguntava "… Prefere
    começar com os dados do Brasil, enviar os seus ou baixar o modelo de planilha?".
  - **Seleção de Territórios:**
    - "Territórios disponíveis", com as opções "Todos os estados (27)" e "Todos os municípios do Brasil (5.570)", a lista dos
      estados e, no fim, a busca ("Procurar pelo nome ou código (opcional)"), com instruções sobre as caixas.
    - **Defeito:** "Ver os N municípios" abria a lista e punha só aquele estado na análise. Marcar municípios da Bahia e depois
      abrir Santa Catarina trocava a seleção, e a da Bahia se perdia.
    - A aba mostrava também o desenho, a frase-resumo e os Detalhes.
    - Não havia o Brasil como unidade nem a escolha de alguns estados; a Tendência nos estados esperava os municípios.
  - **Voltar:** a trilha "Brasil › Amazonas (62 municípios)": "Brasil" voltava aos estados, e o nome do estado, ao estado
    inteiro. Não havia Limpar nem Desfazer.
  - **Explicações:** a apresentação de cada análise ficava sempre aberta no alto da aba. A das classes da tendência falava de
    "avanços" e terminava com "Método de classificação: CAP-TEN-01 (DA-15).".
  - **Frase-resumo:** sempre coletiva, também com um território só ("o gráfico tem 1 município. Entre os municípios, a
    densidade vai de 9,40 a 9,40 …; 0 municípios sem valor."), e com as contagens zeradas ("família do declínio, 0; …; não
    avaliável, 0").
  - **Nomes da planilha (defeito):** o pedido ao `/api/painel` não levava os rótulos confirmados no painel Colunas (só o pedido
    do mapa levava). O motor respondia com "unidade/unidades", e a área e a frase-resumo trocavam os nomes da planilha pelos
    genéricos depois do primeiro cálculo ("Em 2024, o gráfico tem 3 unidades.").
- **Agora:**
  - **Abertura e envio (itens 1 e 2 do pedido):**
    - **Abertura (E0):** mais acima e centrada, só "Diagnóstico Territorial da Força de Trabalho em Saúde", "Escolha seus dados
      para começar", uma frase ("Use os dados do Brasil, já preparados, ou envie a sua planilha em CSV ou Excel.") e dois
      botões, "Usar dados do Brasil" e "Enviar meus dados". O texto sobre o aceite de privacidade saiu (o aceite continua antes
      de tudo).
    - **Abas e navegação:** as abas e Nova sessão, Nova análise e Histórico aparecem quando a base fica pronta. A escolha da
      análise antes dos dados (a "intenção") saiu.
    - **Janela de envio:** "Enviar meus dados" abre a mesma janela em todas as entradas (a abertura, a conversa, o "Trocar" e
      o "Enviar meus dados" da Rotatividade): o que enviar, "Escolher o arquivo" e o modelo de planilha, com as colunas
      descritas e "Baixar o modelo de planilha (XLSX)". Os botões do modelo na área e na conversa saíram.
    - **Conversa:** "O que você quer analisar? Prefere usar os dados do Brasil ou enviar os seus?", com "Usar dados do Brasil"
      e "Enviar meus dados".
    - **Trocar:** as mesmas duas entradas, com "Cancelar"; a análise em uso continua à vista até a nova fonte ficar pronta, e
      um cancelamento ou um arquivo recusado não a tiram da tela.
  - **Seleção de Territórios (item 3):**
    - **Níveis,** um em análise por vez, cada um com a sua escolha: o **Brasil** como unidade (o total da fonte nacional, que
      não é a soma dos estados nem a seleção de todos os municípios), os **estados** (um, vários ou todos, com "Marcar todos os
      estados (27)" e "Desmarcar todos os estados") e os **municípios**, navegados por estado e cumulativos.
    - **Defeito corrigido na causa:** abrir a lista de um estado ("Ver os N municípios ›") só mostra a lista e não muda a
      seleção; marcar na Bahia e depois em Santa Catarina mantém os dois.
    - **Comandos coletivos** que dizem sobre qual conjunto agem: "Marcar todos os municípios do Brasil (5.570)" (no lugar de
      "Todos os municípios do Brasil"), "Desmarcar todos os municípios", "Marcar todos os municípios da Bahia", "Desmarcar os
      municípios da Bahia" e a caixa do estado inteiro.
    - **Busca no alto,** por nome ou código, com os estados e os municípios encontrados.
    - **Na análise:** o resumo do que está marcado ("3 municípios de 2 estados", "Bahia e Santa Catarina", "PORTO ALEGRE
      (RS)"), estado a estado, cada um com um × para tirá-lo, "Ver a <análise>" e "Limpar a seleção". A aba fica só com a
      seleção: o desenho, a frase-resumo e os Detalhes ficam nas análises. Os textos técnicos e as instruções das caixas saíram;
      fica a orientação curta.
    - **Planilhas:** os mesmos passos, sem os níveis; sem a lista das unidades no catálogo, "Marcar todos" continua valendo
      para a planilha inteira, e o resumo fica sem um "(0)".
    - **Tendência dos estados:** a Análise de Tendência vale para os estados escolhidos (o motor já a calculava no nível
      estados); a espacial continua esperando os municípios.
  - **Voltar, Limpar e Desfazer (item 4):**
    - **Voltar** (a seta ←, no alto da análise) desfaz a última navegação, com o nome dela: abrir um estado pela bolha e o
      atalho do mapa ("Voltar aos estados") e uma mudança de territórios pedida na conversa ("Voltar à seleção anterior"). Uma
      mudança à mão na Seleção esvazia a pilha. A trilha saiu.
    - **Limpar** (a vassoura): "Limpar a seleção de municípios" (ou "de estados"), na Seleção, e "Limpar filtros", nas
      análises (a régua, as condições, a ordenação, a comparação, o filtro da classe e os itens marcados, sem mexer nos
      territórios nem nos ajustes).
    - **Desfazer** depois de marcar ou desmarcar muitos de uma vez, de limpar a seleção e de limpar os filtros.
  - **Explicações (itens 5, 7 e 8):**
    - **Classes da tendência** em linguagem simples, com um exemplo curto cada ("Aceleração do crescimento: o indicador subiu em
      todos os períodos, e cada alta foi do mesmo tamanho ou maior que a anterior, com pelo menos uma maior: o crescimento
      ganhou ritmo. Exemplo: 10, 11, 13 e 16 (altas de 1, 2 e 3)."). A nota termina com "A referência do método fica em
      Detalhes, na aba Método e procedência.", onde está "CAP-TEN-01, rótulos de DA-15".
    - **"Entenda esta análise":** nas quatro análises, a apresentação fica num bloco recolhível, aberto na primeira visita de
      cada aba e recolhido nas seguintes, para os resultados ficarem no alto.
  - **Frase-resumo e significado (item 6):**
    - **Um território só:** a frase é individual: "PORTO ALEGRE (RS), em junho de 2024: densidade de 9,40 por 1.000
      habitantes. Entre junho de 2021 e junho de 2024, a variação da densidade foi de 25,96% (aumento). Tendência de junho de
      2021 a junho de 2024: Aceleração do crescimento. Referência de contexto: a taxa do Brasil (total nacional) é de 2,36 por
      1.000 habitantes."; abaixo dela, o que a classe quer dizer ("Aceleração do crescimento: o indicador subiu em todos os
      períodos…"). Sem contagens por classe na tela com um território só.
    - **Vários territórios:** sem "de X a X" com valores iguais e sem as contagens que são zero.
  - **Motor (`/api/painel`):**
    - **`nivel: "brasil"`:** um item `tipo: "brasil"`, `id: "br"`, com a contagem da fonte nacional e a população
      BR-POP-JUNHO-1, a mudança e a tendência; grupos, faixas, condições, ordenação, comparação, conjuntos, referência e
      rotatividade recusados com o motivo; sem a linha de contexto.
    - **`estados`:** no nível estados, a lista dos estados escolhidos (sem ela, todos, como antes).
    - **Frase-resumo:** individual com um território só; coletiva sem faixas artificiais nem contagens zeradas; a linha de
      contexto como "Referência de contexto: a taxa do Brasil (total nacional) é de …".
  - **Nomes da planilha:** os rótulos confirmados vão em todo pedido de planilha ao `/api/painel`, e a resposta, a área e a
    frase falam deles ("Em 2024, o gráfico tem 3 condados.").
  - **Comparação que continua:** na verificação desta rodada, trocar o nível ou tirar da seleção um item comparado deixava a
    comparação no pedido, e o motor o recusava ("Itens da comparação fora do gráfico"). Agora, a comparação só continua
    enquanto os itens dela estão na análise.
- **Permanece:**
  - **Métodos e valores:** os cálculos, os métodos e as classes (CAP-TEN-01, DA-15, CAP-TMP-01, CAP-DIS-02), os rótulos, a
    população BR-POP-JUNHO-1, a linha de contexto do Brasil (D5) nos municípios e nos estados e todos os números do motor.
  - **Regras de leitura:** nenhum nível somado a outro (RQ-DAD-30) e as decisões D3, D4 e D5.
  - **Contrato sem `nivel`:** o contrato de `/api/painel` sem `nivel` e o nível estados sem a lista `estados` (todos).
  - **Planilha:** o aceite de privacidade antes de tudo; a preparação da planilha (formatos, tamanho, aba, painel Colunas);
    o Histórico, Nova análise e Nova sessão (com o diálogo de sempre); o mapa e as vistas.
  - **Dados e provedor:** os dados versionados não mudam, e nada da base vai ao provedor de IA.
- **Motivo:** pedido do responsável pelo produto em 24/10/2026, "Comando para o Opus — rodada de ajustes de interface,
  navegação e análises" (itens 1 a 10), com o defeito prioritário da seleção cumulativa ("ao selecionar municípios da Bahia
  e, em seguida, municípios de Santa Catarina, a seleção da Bahia é perdida").
  - **Classificação:** todos os itens são mudança de comportamento prevista. Decorrem do pedido e não contrariam a SPEC nem
    as divergências aprovadas. Classificados pela leitura, antes de codar:
    - **Brasil como unidade:** previsto na D3 (abrangência vertical com Brasil), na D4 (população nacional) e na matriz
      por análise ([abrangência territorial](ABRANGENCIA_TERRITORIAL.md)). Com o Brasil, valem os valores, a mudança e a
      evolução temporal; o que agrupa, ordena, filtra ou compara vários territórios "não se aplica". A linha de contexto (D5)
      não aparece quando o item é o próprio total nacional.
    - **Estados escolhidos e tendência dos estados:** a D3 admite a distribuição só entre estados e a evolução temporal nos
      estados.
    - **Navegação só com os dados:** o controle "Encerrar sessão" (RQ-FLX-17, AT-152) continua em "Nova sessão" assim que a
      base fica pronta. Antes dos dados não há base nem resultado a descartar, e a inatividade continua encerrando a sessão.
    - **Modelo de planilha:** só na janela de envio; a SPEC não tem regra sobre onde fica o modelo.
    - **Texto sobre o aceite:** sai só a frase; a declaração continua antes de tudo, como na divergência de 19/10/2026
      (RQ-FLX-19, TPL-09).
    - **Classes e âncora do método:** as classes descritas sem mudar critério nem classe. A âncora do método (CAP-TEN-01, DA-15)
      fica no bloco de método (TPL-12, "Método e documentação"), e a apresentação aponta para ele (V-05, RQ-SIN-10).
    - **Frase-resumo:** só cópias verificadas (D7), com a direção da mudança de CAP-TMP-01 (aumento, redução, sem mudança) e
      LEX-TEN só com a tendência.
    - **Nomes da planilha e comparação:** defeitos encontrados na verificação desta rodada. As correções fazem o código cumprir
      o que os documentos já diziam (a nomenclatura da planilha nos textos da área; a comparação só entre itens da análise) e
      usam chaves que o motor já aceitava (`rotulos`, `comparar`).
- **Documentação e testes:**
  - **Documentação:**
    - `Docs/PAINEL_INTEGRADO_INTERFACE.md`: entradas dos dados, estados da tela, Seleção por níveis, Voltar, Limpar e
      Desfazer, Brasil como unidade, "Entenda esta análise", classes, significado, pedido e testes.
    - `Docs/PAINEL_INTEGRADO.md`: o nível `brasil`, a lista `estados` e a frase-resumo individual e coletiva.
    - `Docs/INTERFACE_CONVERSACIONAL_INTEGRADA.md`: estrutura, envio, Trocar e conversa.
    - `Docs/MAPA_DA_PAGINA_UNICA.md`, `Docs/CONVERSACAO_INCREMENTO_FN.md`, `Docs/ABRANGENCIA_TERRITORIAL.md` (a nota da
      página única) e `README.md`.
  - **Testes novos:**
    - **Motor (`test_painel_pagina.py`):** `test_states_level_with_the_chosen_states`,
      `test_brazil_level_is_the_national_total_as_one_unit` e, com a base versionada,
      `test_real_brazil_level_is_the_national_reference_and_the_national_trend`.
    - **Frase (`test_painel_resumo.py`):** `test_one_territory_gets_its_own_sentence_without_ranges_or_zero_counts`.
    - **`painel.test.mjs`:** a seleção cumulativa entre estados (Bahia e Santa Catarina), o resumo do que está na análise
      (inclusive a planilha sem a lista das unidades), as opções do pedido no nível Brasil, com os estados escolhidos e com os
      nomes da planilha, os títulos e a comparação que sai com os itens.
    - **`areaDeAnalise.test.mjs`:** as classes em palavras simples, com os exemplos conferidos pela mesma regra do motor
      (`classify_speeds`); `significadoDaClasse`; os ajustes no nível Brasil.
    - **Roteiros:**
      - `ui_area_de_analise.py`: E0 sem abas, os níveis, "Entenda esta análise", a seleção cumulativa, o ×, Limpar e
        Desfazer, a busca no alto, Voltar, o Brasil como unidade, os estados escolhidos e "Limpar filtros".
      - `ui_pagina_unica.py`: a janela de envio por todas as entradas, os nomes da planilha no pedido e na Seleção depois da
        resposta e a análise que continua com o cancelamento e o arquivo recusado.
      - `ui_conversa_grafico.py`: os nomes da planilha de condados no pedido, na resposta e na Seleção.
      - `ui_conversa_grafico.py`, `ui_mapa.py` e `ui_modo_escuro.py`: também atualizados para a nova abertura, os níveis da
        Seleção e a janela de envio (no modo escuro, a janela também é conferida no escuro).
  - **Testes mudados de propósito:** o comportamento mudou por este pedido; os defeitos da seleção, dos nomes da planilha e da
    comparação estavam no produto, e não nos testes.
    - **Frase (`test_painel_resumo.py`):** as frases esperadas sem "Entre os municípios", sem as contagens zero e com a nova
      forma da linha de contexto e da tendência.
    - **`painel.test.mjs`:**
      - o teste da trilha (`trilhaDoUniverso`, que saiu) virou o do resumo e do lugar no título;
      - o título de E0;
      - a disponibilidade da tendência nos estados.
    - **`areaDeAnalise.test.mjs`:** os textos da Seleção e das classes.
    - **`conversaGrafico.test.mjs`:** a pergunta da abertura.
    - **Roteiros:** os passos que usavam os botões e as opções que saíram (`analise-territorios-estados`,
      `analise-territorios-todos`, `analise-fonte-modelo`, `chat-fonte-modelo`, a trilha) passaram aos controles novos, com as
      mesmas conferências contra o motor.
  - Nenhum teste foi enfraquecido, pulado ou apagado sem a cobertura registrada acima.

### 2026-10-24 · Tendência sem janela longa e os rótulos "Aceleração de declínio" e "Desaceleração de declínio"
- **Antes:**
  - Uma janela pedida na conversa valia como veio na tela, até a escolha de um ritmo no campo Período. Por exemplo, "tendência
    nos últimos 4 anos" abria as 8 competências de 2021 a 2024, e "todas as competências", as 22 da base do Brasil.
  - Na conversa, "série anual de junho", "últimos N junhos", anos, datas e "últimos N anos" davam janelas com todas as
    competências citadas, também nas condições, na ordenação, em comparar, em juntar e na referência da análise espacial.
  - O quadro de setas tinha um arranjo para janelas longas: sem a ponta da seta nos avanços curtos e, no eixo, só o primeiro e
    o último período.
  - Dois rótulos do declínio eram "Aceleração do declínio" e "Desaceleração do declínio".
- **Agora:**
  - **Sem janela longa:** a tendência usa sempre os últimos 4 períodos do ritmo escolhido, anual ou semestral, também pela
    conversa.
    - **Ritmo citado na conversa:** "tendência anual", "semestral", "ano a ano", "por semestre", "série anual de junho" e
      "últimos N junhos" dão os últimos 4 períodos do ritmo, e a resposta diz quais ("Abri a tendência da densidade, com os
      últimos 4 períodos anuais (junho de 2021, junho de 2022, junho de 2023 e junho de 2024).").
    - **Período sem ritmo:** um período com várias competências (anos, datas, "últimos N anos", mesmo com as âncoras
      divergentes da AT-34, "todas as competências", "mudança entre junho de 2023 e junho de 2024") vira a pergunta do ritmo.
      A pergunta traz um botão por ritmo que a base tem, e cada botão reescreve o pedido com o ritmo no lugar do período.
      Nada muda no gráfico enquanto isso.
    - **Pedidos de função:** o mesmo vale nas condições, na ordenação, em comparar e em juntar. A distribuição e a análise
      espacial (também a referência e a ordenação pela distância) usam uma competência por vez: com um período assim, a
      conversa pede uma competência ou a tendência anual ou semestral.
    - **Exemplo da variação:** a pergunta da variação fora da tendência passa a sugerir "mostre a mudança anual".
    - **Janela de outra rota na tela:** ela vale pelo ritmo dos intervalos dela (cerca de 12 meses, o anual; cerca de 6, o
      semestral, com a folga de 2 meses) e passa a ser os últimos 4 períodos desse ritmo, com o aviso "A tendência usa os
      últimos 4 períodos …". Sem ritmo, ou sem 4 períodos nele, a janela não muda, e o aviso pede a escolha. A janela só vale
      para a tendência: a rotatividade e a análise espacial não a recebem.
    - **Campo Período e quadro:** o texto do campo deixa de ter a forma "Janela de N períodos…", e o quadro de setas sempre
      desenha a ponta da seta e os 4 períodos no eixo.
  - **Rótulos:** "Aceleração de declínio" e "Desaceleração de declínio" valem em todo o sistema.
    - Valem na tela e no motor: o `rotulo` da tendência na API, a coluna "Tendência" das tabelas e do CSV e os textos que
      listam as classes.
    - Os do crescimento continuam "Aceleração do crescimento" e "Desaceleração do crescimento".
- **Permanece:**
  - O método (CAP-TEN-01, DA-15), os códigos das classes (`DECLINIO_ACELERADO`, `DECLINIO_DESACELERADO`) e os nomes das
    famílias ("Família do declínio").
  - O motor e o contrato de `/api/painel`: `tendencia.competencias` aceita de 2 a 80 competências. Quem limita a janela aos
    últimos 4 períodos do ritmo são a tela e a conversa.
  - Fora da tendência, a AMB-04 nas leituras de "últimos N anos" e a pergunta da competência de um ano com várias.
  - Na rotatividade, as duas pontas citadas na conversa.
  - O catálogo documental (`Docs/CFG_DOC_CATALOG.yaml`), que cita a SPEC e é conferido com ela, continua com "do declínio".
  - O campo Período, o quadro de setas, o mapa e o CSV continuam como estavam, fora o rótulo.
- **Motivo:** pedido do responsável pelo produto em 24/10/2026: "Mas não tem janela longa agora. Quando o usuário escolhe o
  período (semestral ou anual) a análise olha os últimos 4 períodos. E o nome adequado é aceleração de declínio, e
  desaceleração de declínio e não "do" declínio."
  - **Classificação, sem janela longa:** prevista. Decorre do pedido e não contraria a SPEC.
    - CAP-TEN-01 vale para qualquer janela com 4 observações ou mais.
    - A pessoa continua escolhendo: pela decisão 5a, ela escolhe o ritmo.
    - A AT-34 é respeitada: nada é escolhido em silêncio, porque a pergunta do ritmo mostra os 4 períodos de cada ritmo.
  - **Classificação, rótulos:** contraria a SPEC: na L415, os rótulos de apresentação de DA-15; na L1776, "classe com o
    rótulo de DA-15". O responsável foi consultado e aprovou em 24/10/2026:
    - os rótulos novos em todo o sistema;
    - os do crescimento sem mudança;
    - a divergência registrada aqui, sem alterar a SPEC.
  - **Divergência da SPEC registrada, sem alterar a SPEC:** DA-15 (L415, CategoriaTendencia) e a saída de CAP-TEN-01 (L1776).
    Os rótulos de `DECLINIO_ACELERADO` e `DECLINIO_DESACELERADO` são "Aceleração de declínio" e "Desaceleração de declínio".
- **Documentação e testes:**
  - **Documentação:**
    - `Docs/CONVERSACAO_INCREMENTO_FN.md`: o período da tendência na conversa, as perguntas, as respostas e os testes.
    - `Docs/PAINEL_INTEGRADO_INTERFACE.md`: a janela que chega à tela, o quadro sem o arranjo das janelas longas, os rótulos e
      os testes.
    - `Docs/EVOLUCAO_TEMPORAL_E_TENDENCIA.md`: os rótulos, com a divergência.
    - `Docs/PAINEL_INTEGRADO.md` e `README.md`.
  - **Testes novos:**
    - `test_conversa_grafico.py`:
      - `test_periodo_da_tendencia_anual_ou_semestral_com_os_ultimos_4_periodos`: o ritmo citado, a pergunta do ritmo, a
        Mudança e `janela_do_ritmo`.
      - `test_periodo_nos_pedidos_de_funcao_segue_o_ritmo_da_tendencia`: condições, ordenação, comparar, juntar e
        referência, o exemplo da variação e a AMB-04 fora da tendência.
    - `painel.test.mjs`: o ritmo pelos intervalos, `janelaPeloRitmo` e a guarda de `aplicarPedido` (nada na rotatividade
      nem na análise espacial).
  - **Testes mudados de propósito:** o comportamento mudou por este pedido, e o defeito não estava no produto nem no teste.
    - **Rótulos:** `test_painel_tendencia.py`, `test_real_data.py`, `test_levels_real_data.py`, `test_representation.py`,
      `painel.test.mjs`, `areaDeAnalise.test.mjs` e `ui_area_de_analise.py` passam a esperar "de declínio".
    - **Janela, em `painel.test.mjs`:** a janela de duas competências pedida pela conversa deixa de valer como veio; a base do
      teste, com dois junhos, não tem 4 períodos anuais.
    - **Janela, em `test_conversa_grafico.py`:** o teste antigo da janela da tendência com os últimos anos e os atalhos foi
      substituído pelos dois testes novos. A cobertura do ritmo e da pergunta está neles, e a da AMB-04 (AT-34) fora da
      tendência, no segundo.
  - Nenhum teste foi enfraquecido, pulado ou apagado sem a cobertura registrada acima.

### 2026-10-24 · Página única: o campo Período (anual ou semestral, os últimos 4 períodos) e o quadro de setas da Análise de Tendência
- **Antes:**
  - A janela da tendência era escolhida pelos atalhos "Últimos 4 junhos", "Série anual de junho" e "Todas as competências"
    ou pelas competências marcadas uma a uma, num painel que abria sozinho ao entrar na aba.
  - Com janelas longas (as 22 competências da base do Brasil), quase nenhuma unidade recebia classe.
  - Na visão Classes, as unidades eram bolhas com o cometa, pintadas pela família da classe.
  - Os textos da aba falavam em "trechos" e diziam que janelas longas têm menos classes.
- **Agora:**
  - **Campo Período:** a aba traz o campo Período, com o seletor Anual ou Semestral, e a análise usa os últimos 4 períodos do
    ritmo escolhido, contados da competência mais recente.
    - Na base do Brasil, o anual dá 06/2021, 06/2022, 06/2023 e 06/2024, e o semestral, 01/2023, 06/2023, 01/2024 e 06/2024.
    - A cada passo, vale a competência mais perto de 12 ou 6 meses antes, com folga de 2 meses (de janeiro a junho são 5
      meses).
    - Não há ritmo padrão: nada de tendência é pedido até a escolha, e o aviso diz "Escolha o período da tendência, anual ou
      semestral: a análise usa os últimos 4 períodos.".
    - O ritmo que a base não tem fica desligado, com o motivo à vista ("Esta base não tem 4 períodos anuais seguidos (um por
      ano) até a competência mais recente.").
    - O texto do campo lista as 4 competências usadas.
    - Os atalhos antigos e o painel da janela saíram.
    - Uma janela pedida na conversa, ou de um estado salvo antes, continua valendo como veio, até a escolha de um ritmo.
  - **Quadro de setas:** a visão Classes passa a ser um quadro de setas, como um painel de cotações.
    - Cada linha é uma unidade, com o nome, um ponto por período e uma seta por avanço: para cima é alta, em azul; para baixo,
      queda, em laranja; para o lado, pausa, em cinza, pelo sinal da velocidade do motor.
    - Ao lado, o último valor, a variação entre o primeiro e o último período, do motor, e a classe do motor, com um ícone.
    - Cada linha tem a própria escala vertical.
    - As linhas vêm agrupadas pela classe e, dentro dela, pela variação, 50 por página, ou pela posição da Ordenação.
    - A dica, no mouse e no foco, lista os períodos com o valor e o avanço.
    - Clicar na linha escolhe a unidade para Séries e Comparar.
    - A contagem por classe filtra o quadro.
    - O cometa e "Primeira", "Última" e "Reproduzir" ficam só na visão Mudança, e a escala não se aplica ao quadro.
  - **Textos da aba:** usam períodos e avanços, como nas regrinhas.
    - Uma alta sozinha é só uma alta, e duas ainda não são tendência: são precisos 4 períodos, ou seja, 3 avanços.
    - "Sem classificação: entre os períodos, houve alta e queda (mudança de direção)."
    - A nota das sem classificação já não fala de janelas longas.
- **Permanece:**
  - O método e as classes: CAP-TEN-01 com DA-15, o mínimo de 4 observações e a velocidade por mês. A tela não classifica nada:
    a classe e o sinal de cada seta são do motor (RQ-REP-02).
  - O motor e o contrato: a janela continua indo em `tendencia.competencias`.
  - As visões Mudança e Séries, o mapa pintado pela família da classe, a contagem por classe, a nota das sem classificação por
    motivo, a âncora "Método de classificação: CAP-TEN-01 (DA-15)." (V-05), a conversa e o CSV.
- **Motivo:** pedido do responsável pelo produto em 24/10/2026: o campo Período com o seletor anual ou semestral, a regra
  considerando os últimos 4 períodos e um gráfico diferente para a tendência, com setas, como na bolsa de valores.
  - **Classificação:** prevista. Decorre do pedido e não contraria a SPEC: o mínimo de 4 observações é o de DA-15, a janela
    continua escolha da pessoa (decisão 5a: a pessoa escolhe o ritmo) e a classe continua a do motor.
  - **Cores das setas:** conferidas no validador da skill de visualização. Alta e queda (`#2a78d6` e `#eb6834` no claro;
    `#3987e5` e `#d95926` no escuro) passam em todos os pares: CVD ΔE 24,7 e 26,8; visão normal 33,6 e 31,8; contraste de 3:1 ou
    mais. A pausa, `#898781`, fica a 3,50:1 no claro e 4,85:1 no escuro, e a forma da seta também diz a direção.
- **Documentação e testes:**
  - **Documentação:** `Docs/PAINEL_INTEGRADO_INTERFACE.md` (Período, quadro de setas, eixos, cores e testes),
    `Docs/PAINEL_INTEGRADO.md` (a janela que a tela pede) e `README.md`.
  - **Testes de Node:**
    - `painel.test.mjs`: o teste da janela cobre os ritmos (anual, semestral, base mensal, anos), o ritmo indisponível com o
      motivo e o ritmo de uma janela; a cobertura dos atalhos removidos passou para essas conferências.
    - `areaDeAnalise.test.mjs`: o quadro de setas (pontos, sinal do motor, escala, lacuna e ordem) e os textos novos.
  - **Roteiro de navegador:** `ui_area_de_analise.py` cobre o Período, sem ritmo padrão e com o anual desligado no catálogo
    sintético, e o quadro de setas, conferido linha a linha com a resposta do motor.
  - **Testes mudados de propósito:** os textos esperados da apresentação, do motivo e da nota, e o aviso da família. O
    comportamento mudou por este pedido, e o defeito não estava no produto nem no teste.
  - Nenhum teste foi enfraquecido, pulado ou apagado.

### 2026-10-23 · Página única: as províncias (ou outros grupos) da planilha na Seleção de Territórios
- **Antes:** numa planilha com a coluna-mãe (papel `grupo_territorial`, por exemplo a província de cada distrito), a lista de
  territórios mostrava só as unidades, sem os grupos: o catálogo da planilha trazia o grupo de cada unidade em `parents`, mas a
  tela só lia o estado da base do Brasil. A documentação já dizia que os grupos apareciam.
- **Agora:** a Seleção de Territórios lista os grupos da planilha (as províncias), cada um com "Ver os N distritos" e a caixa
  do grupo inteiro, como os estados na base do Brasil; o grupo marcado inteiro vai ao motor pelo valor dele
  (`base.municipios.estados`), como a conversa já fazia.
- **Permanece:** na base do Brasil, o estado pelo código IBGE; numa planilha sem a coluna-mãe, a lista das unidades; as regras
  do motor para os grupos da planilha.
- **Motivo:** pedido do responsável pelo produto de 23/10/2026 (itens 2 e 4: a seleção segue a estrutura territorial
  reconhecida).
- **Classificação:** mudança prevista. Escopo: decorre do pedido. Compatibilidade: o motor já aceitava os grupos da planilha.
- **Documentação e testes:** `Docs/PAINEL_INTEGRADO_INTERFACE.md` ("Escolha dos territórios"); `frontend/tests/areaDeAnalise.test.mjs`
  e `backend/tests/ui_pagina_unica.py` (as províncias Norte e Sul na Seleção).

### 2026-10-23 · Página única: mapa com os quintis do motor, sem a pergunta, e enquadramento inicial com contexto
- **Antes:** sem cor própria da análise, o mapa mostrava os pontos na cor única e perguntava "Como pintar o mapa?" (5 grupos
  iguais, faixas, cor contínua ou condições); a cor contínua do indicador era escolha visual, com a escala linear ou
  logarítmica na barra; o enquadramento inicial era justo nos pontos dos itens; o CSV da sessão trazia todos os campos dos
  itens.
- **Agora:**
  - sem cor própria da análise (a distribuição sem grupos nem faixas e a análise espacial, sem condições nem ordenação), o
    mapa pinta os 5 grupos iguais (quintis) do indicador, pelo método existente (CAP-DIS-02): o pedido leva
    `grupos_mapa: {tipo: "quintis"}` junto com a análise, e a legenda mostra cada grupo com o rótulo e a contagem do motor;
    sem os grupos na resposta, a cor única;
  - a pergunta e a cor contínua escolhida saíram; a cor contínua fica só na rotatividade (permanência de 0 a 100%), e o mapa
    não tem escala própria;
  - com os quintis no pedido, trocar o indicador pede de novo ao motor (os quintis seguem o indicador); a volta a um indicador
    já calculado vem da memória da tela;
  - o enquadramento inicial ganha contexto: margem de 25% do vão de cada lado, ao menos um quarto da extensão de todos os
    pontos da fonte e nunca mais que ela, sem escala fixa do Brasil; "Ver tudo" volta a ele, e o zoom continua livre;
  - a nota do mapa diz a origem pela fonte: "Cada ponto é a sede do município (IBGE) na base do Brasil." ou "Cada ponto é a
    coordenada do distrito informada na planilha.";
  - o CSV da sessão (Nova sessão → Exportar CSV) deixa de fora os grupos do mapa, que não são valores da análise.
- **Permanece:** as camadas do gráfico (grupos, faixas, condições, ordem, classes, variação) pintam o mapa como antes; a
  troca de vista não pede nada ao motor (RQ-REP-06); o gráfico, a frase-resumo, a tabela e o CSV da área não mudam com os
  quintis; as legendas de tamanho e de cor; as faixas de distância continuam fora da cor (RQ-REP-02).
- **Motivo:** pedido do responsável pelo produto de 23/10/2026 (itens 10 e 11: retirar o painel "Como pintar o mapa?",
  aplicar os quintis automaticamente e abrir o mapa mais afastado, com geografia reconhecível).
- **Classificação:** mudança prevista. Escopo: decorre do pedido. Compatibilidade: os quintis são classes de CAP-DIS-02
  (RQ-REP-02), calculadas pelo motor com a análise (RQ-REP-06); o enquadramento é só visual.
- **Documentação e testes:** `Docs/MAPA_DA_PAGINA_UNICA.md`, `Docs/PAINEL_INTEGRADO_INTERFACE.md` e `README.md`;
  `frontend/tests/areaDeAnalise.test.mjs`, `mapa.test.mjs`, `modoEscuro.test.mjs` e `paginaUnica.test.mjs`;
  `backend/tests/ui_mapa.py` (os quintis do motor sem pergunta, com a mesma contagem por cor, o enquadramento com contexto e
  os quintis do gráfico iguais aos do mapa), `ui_area_de_analise.py` e `ui_modo_escuro.py`.

### 2026-10-23 · Página única: Análise de Tendência com as classes explicadas e o motivo das sem classificação
- **Antes:** a aba mostrava as classes só pelo rótulo; a dica e os Não avaliáveis traziam o motivo com o código ("Mudança de
  direção (MUDANCA_DE_DIRECAO)"); com janelas longas, quase todas as unidades ficavam "Sem classificação", sem explicação.
- **Agora:**
  - a apresentação da aba diz, em palavras, a regra de cada classe de DA-15 (crescimento, aceleração e desaceleração do
    crescimento, declínio, aceleração e desaceleração do declínio, sem classificação e não avaliável), com a âncora do método
    (CAP-TEN-01, DA-15) exigida pela SPEC (V-05) para descrever as classes; as contagens trazem a descrição no `title`;
  - a dica e os Não avaliáveis dizem o motivo em palavras, sem o código ("Sem classificação: na janela, o indicador subiu em
    alguns trechos e caiu em outros (mudança de direção).");
  - abaixo das contagens, uma nota conta as unidades sem classificação por motivo, com os números do motor
    (`sem_classificacao_por_motivo`) e, quando nenhuma unidade recebeu classe, explica que uma única mudança de direção basta,
    que janelas com menos competências (como os últimos 4 junhos) têm mais chance de classe e que isso é o resultado do
    método, não falta de dados.
- **Permanece:** o método (CAP-TEN-01, DA-15), as classes, as contagens e as velocidades, todas do motor; nenhuma classe,
  regra ou critério novo; a cor da bolha pela família; o código do motivo no CSV.
- **Motivo:** pedido do responsável pelo produto de 23/10/2026 (item 9). Diagnóstico da cadeia inteira (dados, janela,
  motor, resposta e tela), com a base versionada: o motor aplica DA-15 sem defeito, e a tela mostra as classes do motor; nas
  22 competências (janeiro e junho de 2014 a 2024), as 62 séries do Amazonas sobem e descem na janela, e todas ficam sem
  classificação por mudança de direção, como a regra manda (no Brasil, 5.563 sem classificação e 7 em crescimento; nos
  últimos 4 junhos, no Amazonas, 24 classificadas e 38 sem classificação). O defeito real era a comunicação: a tela não dizia
  por quê. A correção explica o resultado sem mexer no método.
- **Classificação:** mudança prevista, de texto e de apresentação. Escopo: decorre do pedido. Compatibilidade: V-05 (menção
  metodológica com âncora, sem afirmar tendência) e CAP-TEN-01 ("tratar SEM_CLASSIFICACAO como falta de dados" é proibido: a
  nota diz o contrário).
- **Documentação e testes:** `Docs/PAINEL_INTEGRADO_INTERFACE.md` e `README.md` (o diagnóstico está em
  `Docs/PAINEL_INTEGRADO.md`); `frontend/tests/areaDeAnalise.test.mjs` (as classes, o motivo em palavras e a nota, com o
  cenário real das 22 competências); `backend/tests/ui_area_de_analise.py` (a nota com as contagens do motor e a dica sem
  código); `backend/tests/test_painel_tendencia.py`, no commit anterior (séries controladas de AT-53 e a base versionada).

### 2026-10-23 · Página única: Seleção de Territórios, abertura sem seleção automática, abas com apresentação e nomes padronizados
- **Antes:** a base do Brasil abria nos 27 estados (um pedido ao motor logo de início) e a planilha, com todas as unidades
  marcadas; a lista de territórios ficava numa coluna ao lado do gráfico, com o botão "Territórios" na barra de funções; as
  abas eram "Distribuição", "Análise espacial", "Tendência" e "Rotatividade"; a aba de uma análise que não se executava com os
  dados ficava desabilitada; a Nova análise voltava aos estados; o motivo da rotatividade trazia o código (CAP-ROT-01).
- **Agora:**
  - a base carregada, do Brasil ou de uma planilha, abre sem territórios escolhidos: a área diz "Os dados do Brasil foram
    carregados e estão prontos para a análise." (ou "A planilha foi carregada…") e "Selecione os territórios que deseja
    analisar.", abre a Seleção de Territórios e espera; nada é pedido ao motor até a escolha. A conversa orienta do mesmo jeito
    ("Os dados estão prontos. Escolha os territórios na Seleção de Territórios ou me diga quais quer ver, por exemplo “mostre o
    Pará” ou “todos os estados”."). A Nova análise recomeça assim, com os mesmos dados;
  - sem territórios escolhidos (também depois de desmarcar tudo), o gráfico, o mapa e a frase-resumo da seleção anterior saem
    da tela;
  - uma linha de abas reúne a "Seleção de Territórios" (primeira) e as análises com os nomes padronizados: "Análise de
    Distribuição", "Análise Espacial", "Análise de Tendência" e "Análise de Rotatividade" (os mesmos nomes no painel Colunas e
    nos avisos). A Seleção traz o texto "Selecione os territórios que deseja incluir em suas análises. Você poderá acrescentar
    ou retirar territórios a qualquer momento, e as análises serão atualizadas conforme a seleção realizada." e a lista; cada
    análise mostra o resumo da seleção, com "Alterar a seleção"; o botão "Territórios" saiu da barra de funções;
  - toda aba abre com a apresentação do que faz, em linguagem simples, com os nomes territoriais da fonte; a aba de uma
    análise que não se executa com os dados abre também, com a apresentação e o motivo ("Indisponível com estes dados: …"), sem
    os ajustes, e o desenho continua com a última análise (sem pedido ao motor);
  - o motivo da rotatividade sai sem o código: "A base do Brasil tem contagens, não pessoas: a rotatividade exige dados
    enviados com o identificador individual.".
- **Permanece:** a seleção é uma só para todas as análises; a referência da Análise Espacial e a janela da Análise de
  Tendência continuam escolhas de cada análise, separadas dos territórios analisados; os métodos, os pedidos de cada análise e
  as condições de execução; a trilha, a busca e a lista em grupos; os `data-testid` das análises (`analise-familia-<família>`).
- **Motivo:** pedido do responsável pelo produto de 23/10/2026 (itens 3 a 8 e 12).
- **Classificação:** mudança prevista. Escopo: decorre do pedido. Compatibilidade: a SPEC não fixa a abertura nem os nomes da
  interface (README: a interface é independente das diretrizes de UX da SPEC); a separação entre os territórios analisados
  (as unidades-alvo) e a referência é a de CAP-ESP-02 e CAP-REF-01.
- **Documentação e testes:** `Docs/PAINEL_INTEGRADO_INTERFACE.md`, `Docs/INTERFACE_CONVERSACIONAL_INTEGRADA.md` e
  `README.md`; `frontend/tests/areaDeAnalise.test.mjs`, `painel.test.mjs`, `conversaGrafico.test.mjs` e
  `paginaUnica.test.mjs`; os roteiros `ui_pagina_unica.py`, `ui_area_de_analise.py`, `ui_mapa.py`, `ui_conversa_grafico.py` e
  `ui_modo_escuro.py`.

### 2026-10-23 · Página única: banner de volta e entradas dos dados na área central e na conversa
- **Antes:** no alto, o nome do agente com Nova sessão, Nova análise e Histórico ao lado, e a barra da fonte com "Dados do
  Brasil", "Enviar meus dados" e o modelo de planilha; a área central tinha só "Dados do Brasil" e "Enviar meus dados"; a
  conversa, os dois botões.
- **Agora:** o banner de apresentação volta ao cabeçalho ("FORÇA DE TRABALHO NA SAÚDE", "Transforme dados em diagnósticos
  territoriais." e "Um novo olhar sobre seus dados. Explore territórios, conecte informações e compreenda cenários."), com
  Nova sessão, Nova análise e Histórico abaixo dele, à esquerda. As entradas saíram do alto: "Dados do Brasil", "Enviar meus
  dados" e "Modelo de planilha XLSX" ficam na área central e na conversa, com as mesmas ações; a barra da fonte aparece só com
  dados em uso ou em preparo, com o resumo e "Trocar", que traz as três entradas de volta à área central, com "Cancelar". A
  conversa pergunta "O que você quer analisar? Prefere começar com os dados do Brasil, enviar os seus ou baixar o modelo de
  planilha?".
- **Permanece:** o aceite de privacidade antes de tudo; a preparação, o painel Colunas, a escolha da aba e os erros da
  leitura na barra da fonte; a troca só vale quando a nova fonte fica pronta; o Diagnóstico técnico da fonte.
- **Motivo:** pedido do responsável pelo produto de 23/10/2026 (item 1).
- **Classificação:** mudança prevista, de interface. Escopo: decorre do pedido. Compatibilidade: a SPEC não fixa o leiaute.
- **Documentação e testes:** `README.md`, `Docs/INTERFACE_CONVERSACIONAL_INTEGRADA.md` e `Docs/PAINEL_INTEGRADO_INTERFACE.md`;
  `frontend/tests/conversaGrafico.test.mjs`; `backend/tests/ui_pagina_unica.py` (o banner, a navegação abaixo dele, as
  entradas na área e na conversa e o download do modelo) e `ui_modo_escuro.py`.

### 2026-10-23 · Página única: textos territoriais pela estrutura reconhecida (motor e conversa)
- **Antes:**
  - no nível estados, `disponibilidade.espacial.motivo` era fixo: "No nível estados, a distância não se aplica: estados não
    têm um ponto único. Abra os municípios de um estado para usar a análise espacial.";
  - numa planilha com a coluna do grupo igual à das unidades, a recusa dizia "A coluna do província (grupo_territorial)…";
  - na conversa, com uma planilha, algumas orientações citavam a base do Brasil: "“municípios com menos de 1 médico por mil
    habitantes”", "cada município precisa atender a todas", "“a mais de 150 km de Manaus”", "“use Manaus como
    referência”", "“mostre o Pará”" e, na referência que pede a base inteira, "A referência é um município ou um conjunto
    de municípios…".
- **Agora:**
  - o motivo usa os rótulos e o gênero da fonte: "No nível dos estados, a distância não se aplica: os estados não têm um
    ponto único. Abra os municípios de um estado para usar a análise espacial." (numa planilha: "No nível das províncias,
    … Abra os distritos de uma província …");
  - a recusa diz "A coluna da província (grupo_territorial) precisa ser diferente da coluna de distritos e do código.";
  - na conversa, com uma planilha, as orientações usam os nomes dela ("“distritos com menos de 1 médico por mil
    habitantes”", "cada distrito precisa atender a todas", "A referência é um distrito ou um conjunto de distritos: a
    referência não pode ser a base inteira. Diga os distritos pelo nome, por exemplo, “use … como referência”."), e os
    exemplos com nomes da base do Brasil dão lugar às reticências ou a "“mostre todos os distritos”".
- **Permanece:** as regras e as condições de aplicabilidade; na base do Brasil, os textos da conversa são os de sempre; os
  textos do nível `estados`, que nomeiam o nível que só existe na base do Brasil; nada vai ao provedor de IA.
- **Motivo:** pedido do responsável pelo produto de 23/10/2026 (item 2: os textos acompanham a estrutura territorial
  reconhecida, sem texto fixo do Brasil).
- **Classificação:** mudança prevista, só de texto. Escopo: decorre do pedido. Compatibilidade: a SPEC não fixa esses
  textos.
- **Documentação e testes:** `Docs/PAINEL_INTEGRADO.md` ("Planilhas enviadas", `rotulos`) e
  `Docs/CONVERSACAO_INCREMENTO_FN.md` ("Planilhas de outros países"); em `test_painel_pagina.py`, a disponibilidade no
  nível estados confere o texto novo (mudou de propósito) e há o teste com distritos, províncias e comunas; em
  `test_conversa_grafico.py`, o teste das orientações com os rótulos da planilha e "todos os estados" (o exemplo da
  orientação da base sem seleção) pondo os estados no gráfico.

### 2026-10-23 · Página única: grupos do mapa (`grupos_mapa`) pedidos junto com a análise
- **Antes:** os grupos por posição (CAP-DIS-02) só vinham com `grupos`, que entram nas notas e na frase-resumo. Não havia como
  pedir os grupos que pintam o mapa sem mudar o que o gráfico e a frase mostram.
- **Agora:** `POST /api/painel` (com `nivel`) aceita `grupos_mapa: {"tipo": "quartis" | "quintis" | "decis"}`, nos dois
  níveis e junto com qualquer chave, inclusive `grupos`:
  - a resposta traz `grupos_mapa` no topo, com a estrutura de `grupos`, e `grupo_mapa` em cada item, com a forma de `grupo`;
  - o cálculo e a memória são os de `grupos` (com as mesmas entradas, um só cálculo);
  - tipo inválido → 422 "Grupos por posição inválidos (grupos_mapa): use {…}.";
  - com menos de duas unidades com valor do indicador, `grupos_mapa` vem `null`, sem recusar o pedido;
  - a chave de execução muda com a opção.
- **Permanece:** sem a opção, a resposta é a de antes (corpos iguais aos do código anterior, conferidos com a base
  versionada); com ela, as notas, as limitações, os domínios, a frase-resumo e a sessão não mudam; `grupos` mantém as regras
  e as mensagens, inclusive a recusa com menos de duas unidades; sem `nivel`, a chave é recusada como as demais da página
  única; nada vai ao provedor de IA.
- **Motivo:** pedido do responsável pelo produto de 23/10/2026: o mapa pinta, sem pergunta, os 5 grupos iguais (quintis), e
  a troca de vista continua sem pedir cálculo novo (RQ-REP-06), por isso os grupos do mapa vêm com a análise.
- **Classificação:** mudança prevista. Escopo: decorre do pedido. Compatibilidade: é o método de CAP-DIS-02, sem método
  novo (Hyndman–Fan tipo 7, mesmos empates e não avaliáveis); o nulo com menos de duas unidades evita derrubar a análise por
  causa da cor do mapa.
- **Documentação e testes:** `Docs/PAINEL_INTEGRADO.md` (options, resposta, "Grupos do mapa", frase-resumo, desvios,
  desempenho e "Tendência na janela", com o diagnóstico da tendência); `backend/tests/test_painel_grupos_mapa.py` (novo, com
  a base versionada no job `dados-reais`) e `backend/tests/test_painel_tendencia.py` (novo: cada desfecho de AT-53 conferido
  contra DA-15 e o diagnóstico com a base versionada; o método não muda).

### 2026-10-23 · Página única: modo escuro que segue o aparelho, com a impressão sempre clara
- **Antes:** a página era só clara, em qualquer esquema de cor do aparelho (o documento da interface dizia "A aplicação é
  toda clara; não há modo escuro.").
- **Agora:**
  - com o aparelho no escuro (`prefers-color-scheme: dark`), sem botão, a página inteira fica escura: o aviso de
    privacidade, a estrutura, a fonte dos dados, a área de análise, o gráfico, o mapa e o mapinha, a dica, os painéis, os
    Detalhes, a conversa flutuante, o Histórico e os diálogos; os campos, as listas e as barras de rolagem nativas acompanham
    (`color-scheme`). A troca do esquema no aparelho vale na hora, sem recarregar;
  - superfícies do escuro: página #0d0d0d, cartões #171716, gráfico e mapa #1a1a19 e elevados #232321 (dica, painel das
    funções, conversa, diálogos, menu do Histórico, controles do mapa). Textos, links, avisos (âmbar e rosa) e botões ficam a
    4,5:1 ou mais nas superfícies em que aparecem; o foco visível, a 3:1 ou mais. Os preenchimentos que no claro levam texto
    branco (aba e segmento escolhidos, botões primários, "Li e concordo") ficam claros, com texto escuro;
  - o desenho usa a paleta do escuro, conferida no validador de paletas: série única #1ba3b5; tendência #3987e5, #d95926 e
    #199e70; grupos, faixas e a cor contínua do mapa do escuro (menor) ao claro (maior), de #184f95 a #9ec5f4; a variação com
    o aumento de #1c5cab a #9ec5f4, a redução de #a8431b a #f2ad8c e o zero #45443f; o neutro #5f5e5a nas condições; o anel do
    não avaliável #898781;
  - a impressão é sempre clara, também o gráfico e o mapa, que voltam ao claro no começo da impressão.
- **Permanece:** o modo claro com as cores de antes (alguns tons quase iguais passaram a dividir uma variável, e as sombras
  ficaram em 3 níveis, sem diferença visível); os valores, os pedidos ao motor, os textos, o CSV e todos os `data-testid`; as
  cores continuam só mapeamento visual dos valores do motor; nada vai ao provedor de IA.
- **Motivo:** bloco 5 do plano da rodada de 23/10/2026, com a decisão do responsável pelo produto de 23/10: o modo escuro
  segue o aparelho, sem botão.
- **Classificação:** mudança prevista, só visual. Escopo: decorre do pedido. Compatibilidade: a SPEC não trata do esquema de
  cor, e nenhuma divergência aprovada é contrariada.
- **Documentação e testes:** README (interface e o job `ui-block1`); `Docs/PAINEL_INTEGRADO_INTERFACE.md` e
  `Docs/MAPA_DA_PAGINA_UNICA.md` (seções "Modo escuro"); `frontend/tests/modoEscuro.test.mjs` (novo);
  `backend/tests/ui_modo_escuro.py` (novo, suíte `bloco1`, com o navegador no escuro); ganchos de teste novos: `data-esquema`
  em `mapa-analise` e `esquema` e `superficie` em `window.__adtMapa`.

### 2026-10-23 · Conversa: "ver no mapa" troca a vista do desenho, e "o que esse gráfico mostra?" responde com a frase-resumo do motor
- **Antes:**
  - "ver no mapa" (e o ato `show_map` do intérprete) respondia "Nesta página, a análise acontece no gráfico; o mapa não faz
    parte dela. A distância até uma referência fica na Análise espacial."; "volte ao gráfico" não era reconhecido na tela;
  - o comando `painel` não tinha vista: "mostre o Pará no mapa" mostrava o Pará e ignorava "no mapa";
  - "o que esse gráfico mostra?", "resuma o gráfico", "explique o resultado" e "o que estou vendo?" seguiam para o intérprete
    (local, contextual e, sem resposta local, o provedor de IA); "explique o resultado" usava a explicação do resultado do
    backend;
  - o contexto da conversa não levava a vista, a disponibilidade do mapa nem a frase-resumo.
- **Agora:**
  - "ver no mapa", "mostre no mapa", "abra o mapa" e "agora o mapa" mandam à área o pedido `{ vista: "mapa" }` ("Mostrei o
    mapa no lugar do gráfico. Para voltar, peça “volte ao gráfico”."); "volte ao gráfico", "mostre no gráfico" e "agora o
    gráfico", `{ vista: "grafico" }` ("Voltei ao gráfico. …"). Com o mapa indisponível segundo a área (estados, planilha sem
    coordenadas, visão Séries), nenhum pedido sai, e a resposta é o motivo da área seguido de "Nada mudou no gráfico.";
    `show_map` e `show_chart` têm o mesmo tratamento; "agora a tabela" aponta os Detalhes, abaixo do gráfico ou do mapa;
  - o comando `painel` ganha `vista` (`mapa` ou `grafico`; nula quando não citada): "mostre o Pará no mapa", "onde ficam os
    municípios com menos de 1 médico por mil?", "volte aos municípios no mapa", "a quantidade no gráfico"; a resposta
    acrescenta "Passei para o mapa." (ou "O mapa continua na tela.", "Deixei só o mapa.", "Voltei ao gráfico.", "Deixei só o
    gráfico."). Onde o pedido já decide que o mapa não mostra a análise (estados ou grupos, planilha sem latitude e
    longitude, rotatividade sem coordenadas, visão Séries, ou mapa indisponível segundo a área sem mudança de nível,
    unidades, análise ou visão), a vista não entra, e a resposta diz por quê;
  - "o que esse gráfico mostra?", "resuma o gráfico", "explique o resultado", "o que estou vendo?" e variações próximas, sem
    outro pedido junto, são respondidos na tela com a frase-resumo verificada do motor, como veio; sem ela, "Ainda não há um
    gráfico calculado para resumir."; nada vai ao intérprete nem ao provedor. "Por que…", perguntas de método e "explique de
    forma mais simples" seguem para o backend como antes;
  - o contexto leva `painel_vista`, `painel_mapa_disponivel` e `painel_resumo`; o backend os tira das opções antes do
    pré-exame, do intérprete e do provedor (`CONTEXTO`).
- **Permanece:** trocar de vista é estado visual e não recalcula (RQ-REP-06); a conversa não calcula nada; "volte ao
  resultado anterior" segue como antes; nada da base vai ao provedor de IA.
- **Motivo:** plano da rodada de 23/10/2026, blocos 2 (mapa como segunda vista do gráfico) e 3 (explicação do resultado
  em palavras).
- **Classificação:** mudança prevista. Escopo: decorre do pedido e dos itens do plano. Compatibilidade: a SPEC prevê o mapa
  com coordenadas autorizadas e a síntese ancorada; a frase repetida é a do motor, ancorada no resultado (RQ-QUA-07,
  RQ-REP-09); a troca de vista é estado visual (RQ-REP-06). Desfaz em parte a resposta de 22/10/2026 ("o mapa não faz parte
  da página").
- **Documentação e testes:** README (conversa); `Docs/INTERFACE_CONVERSACIONAL_INTEGRADA.md` e
  `Docs/CONVERSACAO_INCREMENTO_FN.md`; `frontend/tests/conversaGrafico.test.mjs` (a asserção "o mapa não faz parte dela" muda
  de propósito); `backend/tests/test_conversa_grafico.py` (vista nos comandos compostos, sem mapa, chaves fora do pré-exame,
  do intérprete e do provedor nas duas rotas); `backend/tests/ui_conversa_grafico.py` (suítes `conversa` e
  `gemini-simulado`; o passo "Quero ver no mapa." nos estados muda de propósito).

### 2026-10-23 · Área de análise: ajustes dentro de cada análise, o mapa como segunda vista do gráfico (com o lado a lado e o mapinha) e a frase-resumo do motor
- **Antes:**
  - indicador, competência, categoria, as opções da família e a escala ficavam numa linha solta abaixo das abas, igual para
    todas as análises (o indicador aparecia até na rotatividade, onde não tem efeito); numa planilha sem população, Densidade
    continuava clicável;
  - desde 22/10/2026, a página única não tinha mapa: a análise era só o gráfico de bolhas; a dica da bolha não mostrava onde
    fica a unidade;
  - não havia frase-resumo na tela, e o arquivo de método começava pelo título.
- **Agora:**
  - **Ajustes dentro da análise:** cada aba se liga a um painel de ajustes (`analise-ajustes`) com só o que vale para ela:
    Distribuição (indicador, categoria, competência, grupos e faixas), Análise espacial (indicador, categoria, competência,
    referência), Tendência (indicador, categoria, janela e a visão Classes | Mudança | Séries), Rotatividade (períodos e
    categoria, sem indicador) e, nos estados, indicador, competência, grupos e faixas. O indicador é um só e acompanha a troca
    de aba; numa planilha sem população, Densidade fica desligada, com o motivo, e um pedido da conversa por densidade fica na
    quantidade. A Escala foi para a barra junto do desenho, só quando se aplica.
  - **Vista do desenho:** Gráfico | Mapa | Lado a lado (este só com a janela de 1.600 px ou mais; ao estreitar, volta ao
    mapa), em `data-desenho` da área; o gráfico é a vista inicial; a escolha vale para a sessão e entra no Histórico, que
    reabre a análise na vista em que foi guardada. O mapa fica desligado, com o motivo, nos estados (os estados não têm um
    ponto; atalho "Ver os municípios no mapa"; os ladrilhos dos estados não foram aprovados), numa planilha sem latitude e
    longitude e na visão Séries. Convite "Ver onde ficam no mapa" depois das Condições e na Análise espacial. A troca entre o
    gráfico e o mapa desloca as bolhas até os pontos (sem movimento reduzido e com até 400 itens; senão, é direta).
  - **Mapa** (`MapaAnalise.tsx`, sobre o desenho do mapa antigo): os pontos são as coordenadas autorizadas de
    `POST /api/painel/mapa` (sede municipal do IBGE na base do Brasil; latitude e longitude da planilha, no referencial
    informado), e a nota diz que a posição é só para o desenho; as demais unidades da fonte ficam ao fundo, em cinza claro;
    tamanho com área proporcional (população na densidade, quantidade na quantidade, coorte inicial na rotatividade); cor da
    camada do gráfico (grupos, faixas, condições, ordem, classes ou variação), contínua (linear por padrão; logarítmica só por
    escolha e com valores positivos; a legenda diz que a cor não é classe nem limiar e marca o Brasil só como contexto) ou,
    sem cor escolhida, neutra, com a pergunta "Como pintar o mapa?" (quintis do motor como recomendação, faixas, cor contínua
    ou condições, conforme a análise); a régua e os filtros esmaecem o que fica fora, sem esconder; membros de conjuntos com
    anel escuro; a referência com a mira do gráfico; ligações tracejadas dos marcados (até 30) até a referência mais próxima,
    "ligação ilustrativa, não é trajeto"; faixas de distância não viram cor (RQ-REP-02 não lista CAP-ESP-03) e não há círculos
    de distância; navegação do mapa antigo (botões, arrasto, Ctrl + roda, pinça, duplo clique, teclado e busca por nome),
    mapinha no canto com zoom e a mesma dica do gráfico; unidades sem coordenada válida entram em Não avaliáveis (aspecto
    "mapa"), com o motivo do motor.
  - **Etapa 2 do mapa:** com o mapa disponível, a dica da bolha de um município mostra o mapinha com o destaque ("onde
    fica?"); no lado a lado, o item sob o mouse num desenho ganha o anel no outro; na rotatividade de uma planilha com
    coordenadas, o mapa pinta a permanência da coorte inicial (0 a 100%).
  - **Frase-resumo do motor** (`analise-resumo`, `aria-live`) logo abaixo do subtítulo, só quando fala do indicador à vista;
    entra na impressão (que sai com a vista em exibição; no lado a lado, as duas) e no arquivo de método. O contexto da
    conversa leva a vista, a frase e a disponibilidade do mapa.
- **Permanece:** todo número vem do motor; trocar a vista ou a cor do mapa não pede nada novo (RQ-REP-06); nenhuma classe,
  quantil, contagem ou posição é criada na tela; logarítmica só por escolha; estados não têm ponto; todos os `data-testid`
  de antes e o CSV não mudam; a tabela dos Detalhes continua o caminho acessível; nada da base vai ao provedor de IA.
- **Motivo:** plano da rodada de 23/10/2026 (blocos 1, 2 e 3 e a etapa 2 do mapa), aprovado pelo responsável pelo produto,
  com as decisões de 23/10: o mapa pergunta como pintar; a régua esmaece no mapa; sem ladrilhos dos estados (o adendo não
  foi aprovado).
- **Classificação:** mudança prevista. Escopo: decorre do pedido. Compatibilidade: a SPEC prevê o mapa com geometria
  autorizada (CAP-REP-03, RQ-REP-07, RQ-REP-10), o painel simples (RQ-REP-08) e a síntese ancorada; cor contínua e tamanho
  são mapeamento visual contínuo de valores existentes (Parte 13). Desfaz em parte a remoção do mapa de 22/10/2026.
- **Documentação e testes:** README; `Docs/PAINEL_INTEGRADO_INTERFACE.md`; `Docs/MAPA_DA_PAGINA_UNICA.md` (novo); a nota
  inicial de `Docs/BLOCO3_MAPAS_VISUALIZACOES.md`; `frontend/tests/areaDeAnalise.test.mjs` e `frontend/tests/mapa.test.mjs`
  (novos); `backend/tests/ui_area_de_analise.py`; `backend/tests/ui_mapa.py` (novo, na suíte `base-versionada`).

### 2026-10-23 · Página única: desempenho sem mudar números; respostas grandes comprimidas
- **Antes:** no ambiente de medição desta rodada, "com tudo" sobre os 5.570 municípios levava 1,98 s; a tendência de 11 junhos
  com condições, 1,03 s; as respostas grandes (até 13,4 MB) iam sem compressão.
- **Agora:** 0,76 s e 0,53 s no mesmo ambiente (mediana de 10 pedidos depois do primeiro; tabela em `Docs/PAINEL_INTEGRADO.md`).
  O motor reaproveita entre pedidos o que não mudou (distâncias, condições, grupos, faixas, ordenação, tendência por item e a
  linha de contexto, pela memória da versão); a distribuição é montada em bloco; a variação exata usa inteiros, com o mesmo
  valor de `temporal_change.change`; respostas a partir de 64 KB vão com gzip para quem aceita (10,7 MB → 2,2 MB).
- **Permanece:** números, textos e chaves de execução (corpos idênticos ao do código anterior, conferidos por SHA-256 nos
  casos medidos e em outras 76 respostas); o contrato (nenhum campo saiu); a integridade conferida a cada pedido; planilhas
  nunca guardadas. Ficam acima da meta o primeiro pedido com tendência de todos os municípios (cálculo frio) e o tamanho das
  respostas com tendência.
- **Motivo:** bloco 4 do plano da rodada de 23/10/2026 (meta de 0,4 a 0,8 s).
- **Classificação:** os resultados não mudam; muda o transporte (`Content-Encoding: gzip`), e o corpo descomprimido é o mesmo.
- **Documentação e testes:** `Docs/PAINEL_INTEGRADO.md` (Desempenho); `test_painel_desempenho.py` (novo); `bench_painel.py`
  (medição, fora do CI).

### 2026-10-23 · Página única: frase-resumo do motor (`resumo`)
- **Antes:** a resposta da página única não dizia em palavras o que o gráfico mostra; a frase verificada existia só em
  `/api/analyze` (decisão D7).
- **Agora:** toda resposta com `nivel` traz `resumo` (`texto`, `partes`, `segmentos`, `contagens`, `nota`). A frase usa só
  cópias conferidas da própria resposta (contagens e extremos vêm do motor) e cobre as análises pedidas: distribuição, grupos
  e faixas, mudança, análise espacial (com a nota da linha reta), tendência ou o bloqueio, condições, comparação,
  rotatividade (em %), a ressalva dos conjuntos, a nota da fonte estadual e a taxa do Brasil só como contexto. Exemplo: "Em
  junho de 2024, o gráfico tem 62 municípios. Entre os municípios, a densidade vai de 0,36 a 2,15 por 1.000 habitantes; …".
- **Permanece:** nenhum número muda nem é calculado na frase; as regras de léxico da D7 (nunca "acima" ou "abaixo"); nada vai
  ao provedor; uma falha omite o campo sem derrubar a resposta; o contrato de 21/10 (sem `nivel`) não muda.
- **Motivo:** bloco 3 do plano da rodada de 23/10/2026.
- **Classificação:** mudança prevista; a SPEC prevê a síntese ancorada.
- **Documentação e testes:** `Docs/PAINEL_INTEGRADO.md` (Frase-resumo); `test_painel_resumo.py` (novo); o conjunto `TOP` de
  `test_painel_pagina.py` ganha `resumo` (muda de propósito).

### 2026-10-23 · Página única: coordenadas do mapa (`POST /api/painel/mapa`)
- **Antes:** as coordenadas autorizadas só eram usadas por dentro, nas distâncias da análise espacial; não havia rota de mapa.
- **Agora:** `POST /api/painel/mapa` (mesmo formulário de `/api/painel/referencias`; opções `competencia`, `categoria`,
  `premissas` e `rotulos`) devolve `{competencia, referencial, pontos, sem_coordenada}` com todas as unidades do catálogo na
  competência, na ordem do código e com os mesmos ids de `/api/painel`. Base do Brasil: a sede municipal em SIRGAS 2000, com
  a camada complementar governada. Planilhas: latitude e longitude no `crs` confirmado (SIRGAS 2000 ou WGS 84); sem `crs`, a
  pendência da análise espacial; sem colunas de coordenadas, 422 com o motivo. Sem coordenada válida (ou sem registro na
  competência), a unidade vai em `sem_coordenada`, com o motivo e o código.
- **Permanece:** as coordenadas, as premissas e a camada são as da análise espacial, sem cálculo novo; estados não têm ponto;
  nada vai à sessão nem ao provedor; `/api/painel` e `/api/painel/referencias` não mudam.
- **Motivo:** bloco 2 do plano da rodada de 23/10/2026 (o mapa como segunda vista do gráfico).
- **Classificação:** mudança prevista; a SPEC prevê o mapa com geometria autorizada (CAP-REP-03, RQ-REP-07). Desfaz em parte
  a remoção de 22/10/2026.
- **Documentação e testes:** `Docs/PAINEL_INTEGRADO.md` (Rota 3); `test_painel_mapa.py` (novo, com a base versionada no job
  `dados-reais`).

### 2026-10-22 · Página única: o painel Colunas pergunta quem são os trabalhadores, e a troca do indicador redesenha o eixo
- **Antes** (commits `ef58a33` e `6ec1ef4`, ainda não aprovados no CI):
  - o painel Colunas não tinha o objeto da análise (ele saiu com a preparação): numa planilha sem coluna de categoria, o
    gráfico recusava com "Informe o objeto de análise: a profissão ou o conjunto de trabalhadores da força de trabalho em
    saúde.", sem campo para responder;
  - com a memória da tela sem o indicador, trocar densidade e quantidade não pedia nada ao motor, mas o eixo Y continuava no
    indicador do último pedido.
- **Agora:**
  - sem coluna de categoria, o painel Colunas pergunta "Quem são os trabalhadores contados?" (por exemplo, médicos); o texto
    vai como objeto da análise (`category_constant`) ao pré-exame, à conversa e ao gráfico, como na preparação de antes, e
    dá nome à categoria no título; sem ele, "Começar a análise" lista "Diga quem são os trabalhadores contados, por exemplo,
    médicos ou enfermeiros.";
  - o eixo e as bolhas seguem o indicador escolhido, salvo quando o pedido depende dele (grupos, faixas, tendência,
    comparação ou ordenação pela variação), em que o novo indicador pede o gráfico de novo.
- **Permanece:** com coluna de categoria, nada é perguntado; o objeto reconhecido pelo catálogo (médicos, enfermagem…)
  continua registrado como `fts_scope_recognized`; nada vai ao provedor de IA.
- **Motivo:** a quarta execução do CI (roteiros `ui_conversa_grafico.py`, planilha "condados.csv", e `ui_area_de_analise.py`,
  troca do indicador) mostrou os dois pontos. O defeito estava no produto: faltava o campo que o motor exige, e o desenho
  usava a presença do indicador no pedido, que agora vai sempre. Classificação: correção dentro do escopo da página única,
  compatível com a SPEC (o objeto da análise é sempre informado, nunca presumido).
- **Documentação e testes:**
  - **Documentação:** README e `Docs/INTERFACE_CONVERSACIONAL_INTEGRADA.md` (painel Colunas).
  - **Testes:**
    - `paginaUnica.test.mjs`: a pendência e a premissa do objeto, com e sem coluna de categoria; o teste das pendências muda
      de propósito (a planilha sem categoria passa a pedir o objeto);
    - `painel.test.mjs`: quando o pedido depende do indicador;
    - `ui_conversa_grafico.py` muda de propósito: a planilha de condados, sem categoria, informa "médicos" antes de começar.

### 2026-10-22 · Página única: as colunas escolhidas da planilha chegam ao gráfico, e trocar o indicador não recalcula
- **Antes** (commits `ef58a33` e `75a893c`, ainda não aprovados no CI):
  - numa planilha, as colunas escolhidas pela pessoa no painel Colunas iam ao pré-exame (`confirmed_roles`), mas não ao gráfico:
    com uma coluna que o motor não reconhece pelo nome ("condado"), o gráfico recusava com "Escolha a coluna de Território no
    seletor…";
  - com `indicador` em todo pedido, trocar densidade e quantidade pedia o gráfico de novo, mesmo quando a resposta já trazia os
    dois valores; uma pendência de papel confirmado gravava um texto em `confirmed_roles`, que é uma lista.
- **Agora:**
  - as colunas escolhidas no seletor vão em `premissas.confirmed_roles` em todo pedido da planilha, como no pré-exame (D1: a
    escolha no seletor substitui a confirmação); o papel confirmado numa pendência entra nessa lista;
  - sem grupos, faixas, tendência, comparação ou ordenação pela variação, trocar o indicador usa a resposta já recebida, sem
    pedir nada ao motor; o pedido enviado continua com o indicador em exibição.
- **Permanece:** o grupo territorial não é papel do motor comum (vai no mapeamento do gráfico e, no pré-exame, em
  `hierarchy_columns`); nada vai ao provedor de IA.
- **Motivo:** a terceira execução do CI (roteiros `ui_conversa_grafico.py`, planilha "condados.csv", e `ui_area_de_analise.py`,
  troca do indicador) mostrou os dois pontos. O defeito estava no produto: a tela não mandava as escolhas da pessoa ao gráfico,
  e a memória da tela tratava o indicador como parte de todo pedido. Classificação: correção dentro do escopo da página única,
  compatível com a SPEC e com a divergência aprovada D1.
- **Documentação e testes:**
  - **Documentação:** `Docs/PAINEL_INTEGRADO_INTERFACE.md` e `Docs/INTERFACE_CONVERSACIONAL_INTEGRADA.md`.
  - **Testes:**
    - `ui_pagina_unica.py` muda de propósito: as premissas da planilha de distritos passam a trazer `confirmed_roles:
      ["territory"]`, a coluna escolhida pela pessoa;
    - `paginaUnica.test.mjs` ganha as colunas escolhidas nas premissas;
    - `painel.test.mjs` ganha a chave da memória sem o indicador quando ele não muda a resposta.

### 2026-10-22 · Página única: a planilha enviada abre com todas as unidades no gráfico
- **Antes** (commit `ef58a33`, ainda não aprovado no CI): depois de "Começar a análise", a área de uma planilha abria sem
  nenhuma unidade marcada ("Marque os distritos na lista de territórios para ver o gráfico."), e nada era pedido ao motor.
- **Agora:** a planilha abre com todas as unidades marcadas, e o gráfico aparece logo depois de "Começar a análise"; a lista
  das unidades (e dos grupos, com a coluna-mãe) continua à vista para restringir. Na base do Brasil, a porta de entrada
  continua os 27 estados.
- **Permanece:** sem nenhuma unidade marcada, nada é pedido ao motor; as planilhas não têm bolhas de grupo; o modo leve vale
  para planilhas grandes.
- **Motivo:** a segunda execução do CI (roteiro `ui_conversa_grafico.py`, passo da planilha "condados.csv") mostrou a
  diferença entre as frentes: a estrutura da página (roteiros `ui_pagina_unica.py` e `ui_conversa_grafico.py`) espera o gráfico
  logo após "Começar a análise", e a área esperava a escolha das unidades. Sem estados nem bolhas de grupo, a visão geral da
  planilha são todas as unidades, como os estados na base do Brasil ("a mesma lógica", decisão do responsável de 22/10/2026).
  Classificação: correção dentro do escopo da página única, compatível com a SPEC.
- **Documentação e testes:** `Docs/PAINEL_INTEGRADO_INTERFACE.md` (abertura da planilha); `painel.test.mjs` (a planilha abre
  com todas as unidades e a base do Brasil sem nenhuma); os roteiros de navegador não mudam.

### 2026-10-22 · Página única: a comparação pendente volta na conversa, e o Histórico reabre sem recalcular
- **Antes** (commits `22e0e28` e `ef58a33`, ainda não aprovados no CI):
  - "compare Manaus" (um nome só) respondia "Identifiquei MANAUS (AM). Para comparar, diga dois ou três nomes no mesmo
    pedido…", sem guardar a pendência: a mensagem seguinte ("Tefé e Parintins") só mostrava esses municípios;
  - reabrir pelo Histórico uma análise igual ao estado inicial da área (os estados) pedia o gráfico de novo ao motor.
- **Agora:**
  - "compare Manaus" pergunta "Identifiquei MANAUS (AM). Com qual outro município você quer comparar? Diga um ou dois nomes.
    Nada mudou no gráfico.", com `pending_operation: "comparisons"` e `pending_ids`; a tela devolve a pendência na mensagem
    seguinte (`conversation_pending_ids`, que não vai ao provedor de IA), e "Tefé e Parintins" completa a comparação com
    Manaus. Outro comando ou uma pergunta não completam a pendência, e um pedido aplicado ao gráfico a encerra;
  - o Histórico reabre a análise como estava, sem pedir nada ao motor, também quando ela é igual ao estado inicial.
- **Permanece:** a comparação de 2 ou 3 itens; nada da base vai ao provedor de IA; o Histórico guarda a resposta do motor.
- **Motivo:** a primeira execução do CI da página única (roteiros `ui_conversa_grafico.py` e `ui_pagina_unica.py`) mostrou que
  a continuação da conversa, que já existia antes da página única ("pendências da conversa continuam",
  `Docs/INTERFACE_CONVERSACIONAL_INTEGRADA.md`), e a reabertura sem recálculo não funcionavam. O defeito estava no produto: a
  conversa nova não guardava a pendência, e a área agendava o pedido inicial antes de restaurar o estado salvo. Classificação:
  correção dentro do escopo da página única, compatível com a SPEC.
- **Documentação e testes:**
  - **Documentação:** `Docs/CONVERSACAO_INCREMENTO_FN.md` (comparar com um nome só).
  - **Testes:**
    - `test_conversa_grafico.py` muda de propósito (a resposta de "compare Manaus" passou a ser a pergunta com a pendência) e
      ganha a continuação, a recusa da pendência com outro comando e a comparação explícita que a substitui;
    - `ui_area_de_analise.py` passa a esperar `nivel` e `indicador` em todo pedido (mudança de propósito da integração);
    - os roteiros `ui_conversa_grafico.py` e `ui_pagina_unica.py` não mudam.

### 2026-10-22 · WGS 84 como segundo referencial das coordenadas, além do SIRGAS 2000 (Adendo REF-20261022 da SPEC)
- **Antes:**
  - o motor só aceitava o SIRGAS 2000 (`SIRGAS2000` e os apelidos de D24); `WGS84` era "não suportado" (422 na distância e na
    referência mais próxima; mapa com a pendência `REFERENCIAL_NAO_SUPORTADO`; pendência do gráfico com as opções
    `["SIRGAS2000"]`);
  - no painel "Colunas", o referencial das coordenadas tinha "SIRGAS 2000", "Outro referencial" e "Não sei"; só o SIRGAS 2000
    virava a premissa `crs`.
- **Agora:**
  - **Motor:** o conjunto de referenciais aceitos é {SIRGAS2000, WGS84}. `WGS84`, `WGS 84`, `WGS-84` e `WGS_84` (só variação
    de caixa e espaços nas pontas) viram `WGS84`; "WGS 1984", "EPSG:4326" e outros nomes continuam não suportados. A distância
    (análise espacial, referência mais próxima, critérios com distância e o gráfico) é calculada no elipsoide do referencial
    informado: GRS80 no SIRGAS 2000 e WGS 84 no WGS 84 (a = 6.378.137 m, 1/f = 298,257223563), sem converter coordenadas de
    um no outro. O método e a nota do resultado citam o referencial e o elipsoide usados. As mensagens de referencial não
    suportado e a pendência do gráfico passam a citar os dois (`opcoes: ["SIRGAS2000", "WGS84"]`).
  - **Base do Brasil:** continua em SIRGAS 2000 (premissa do perfil oficial, com a camada complementar no mesmo
    referencial). Outro referencial informado para ela não é usado, pois exigiria transformação: 422 com "As coordenadas da
    base do Brasil estão no referencial SIRGAS 2000, e o sistema não converte um referencial em outro. Use SIRGAS 2000 nesta
    base."; no mapa, a pendência nova `REFERENCIAL_INCOMPATIVEL`.
  - **Painel "Colunas":** o seletor oferece "SIRGAS 2000" (`SIRGAS2000`) e "WGS 84" (`WGS84`), além de "Outro referencial" e
    "Não sei", com a explicação: "Informe o referencial em que as coordenadas foram coletadas: SIRGAS 2000 ou WGS 84. O
    sistema não converte um no outro. Com outro referencial, ou sem saber qual é, a análise espacial fica indisponível: nada é
    presumido."; o referencial informado segue como está na premissa `crs`; com outro, ou "Não sei", o motivo passa a "Só os
    referenciais SIRGAS 2000 e WGS 84 são admitidos; com outro, ou sem saber qual é, nada é presumido.".
- **Permanece:** nenhum referencial é presumido (sem referencial, a pendência `REFERENCIAL_GEODESICO`); nenhuma transformação
  entre referenciais (RQ-DAD-27); a limitação DISTANCIA_GEODESICA_DIRETA; a camada geográfica complementar só em SIRGAS 2000;
  nada vai ao provedor de IA. Para o SIRGAS 2000, distâncias, notas e chaves de execução não mudam.
- **Motivo:** decisão do responsável pelo produto em 22/10/2026, para planilhas de outros países: à pergunta "quer que eu
  inclua o WGS 84 como referencial aceito no adendo da SPEC?", respondeu "certo. aceito wgs 84". Classificação: mudança
  prevista, incorporada à SPEC pelo Adendo REF-20261022 (CFG-MET, seção 4.4.5; RQ-DAD-26; CAP-ESP-01; AT-51, AT-108 e AT-143),
  no fim de `IMPLEMENTATION_SPEC.md`, sem mexer no corpo (conferido pelo catálogo CFG-DOC). As formas literais do catálogo
  CFG-DOC que enumeram {SIRGAS2000} continuam as do corpo, como no Adendo BOL-20261021.
- **Documentação e testes:**
  - **Documentação:** README, `Docs/INTERFACE_CONVERSACIONAL_INTEGRADA.md`, `Docs/BLOCO2_ETAPA1_REFERENCIAS_PROXIMIDADE.md`,
    `Docs/BLOCO3_MAPAS_VISUALIZACOES.md`, `Docs/DADOS_BRASIL_VALIDACAO.md`, `Docs/PAINEL_INTEGRADO.md` e
    `Docs/PAINEL_INTEGRADO_INTERFACE.md`.
  - **Testes mudados de propósito** (o comportamento mudou; o defeito não está no produto nem no teste): nos testes que usavam
    `WGS84` como exemplo de referencial não suportado, o exemplo passa a `SAD69`, que continua recusado com a mesma verificação
    (`test_audit_integrity.py`, `test_nearest_reference.py`, `test_representation.py`, `test_geo_complement.py` e
    `test_painel_pagina.py`, que também espera as duas opções na pendência); `nearest_exact` e `nearest_exhaustive` recebem o
    referencial (`crs`), e a busca exata é conferida contra a exaustiva nos dois elipsoides.
  - **Testes novos:** elipsoide WGS 84 conferido com Vincenty independente; apelidos de `WGS84` na referência mais próxima e na
    análise espacial, com a distância do elipsoide WGS 84; mapa de planilha em WGS 84; base do Brasil com `WGS84` recusada (422
    e `REFERENCIAL_INCOMPATIVEL`); gráfico de planilha em WGS 84 igual a `/api/analyze`; nomes fora dos apelidos ("WGS 1984",
    "EPSG:4326") recusados. Frontend: `paginaUnica.test.mjs` (os quatro valores do seletor, a premissa `crs: "WGS84"`, a análise
    espacial disponível com o WGS 84 e o motivo novo) e o roteiro `ui_pagina_unica.py`.

### 2026-10-22 · Página única: a tela, o motor e a conversa ligados (integração das quatro frentes)
- **Antes:** as quatro partes da página única (motor do gráfico, área de análise, estrutura da página e conversa) foram feitas
  em paralelo, cada uma sobre o contrato comum, e não se falavam em alguns pontos.
- **Agora:**
  - **Pedido ao motor:** a área manda `nivel` e `indicador` em todo pedido (sem `nivel`, o motor responde no formato de 21/10,
    que não conhece as chaves da página única). Nas planilhas, as premissas do painel Colunas vão em todo pedido; sem população
    associada, o indicador começa na quantidade. Na base do Brasil, nenhuma premissa vai ao motor.
  - **Leitura da resposta:** o membro mais próximo com empate (`empate`), o estado de cada condição com o texto da definição do
    topo, os limites das faixas em texto decimal, a comparação com `maior` e `menor` em ids e a diferença `{a, b, relacao,
    diferenca}`, e o motivo da tendência em texto com o código entre parênteses.
  - **Conversa:** cada pedido leva o estado do gráfico (`painel_indicador`, `painel_nivel`, `painel_municipios`,
    `painel_competencia`, `painel_janela` e `painel_referencia`); antes de o gráfico informar o contexto, `painel_familia` vai
    nulo, e a conversa responde no formato do gráfico. Numa planilha, os nomes da unidade e do grupo (`rotulos`) vão à conversa,
    não ao pré-exame. Os comandos de grupos ("divida em quintis") e de referência por critério ("a de maior densidade como
    referência", que abre a lista de candidatos nessa ordem, com a escolha da pessoa) passam a mudar o gráfico.
  - **Textos que citavam telas que saíram:** a pergunta do período não confirmado ("Deseja revisar o período?", antes "…na
    preparação?"); as linhas idênticas ("Escolha remover as cópias nesta análise ou corrija a base.", antes "Em «Linhas
    idênticas», escolha…"); a leitura de resultado ("Recorte do resultado diferente da análise atual.", antes "…da preparação
    atual."); a pendência de recorte da conversa ("…escolha o recorte.", antes "…escolha o recorte na preparação."); e a recusa
    de planilha no formato de 21/10 do gráfico, que passa a indicar o formato da página única, com `nivel`.
  - **Saem, sem uso:** o invólucro de transição `PainelIntegrado.tsx` e o catálogo das 12 análises (`analysisCatalog.ts`), com o
    seu teste unitário.
- **Permanece:** todo número vem do motor; nada da base nem as chaves do contexto do gráfico vão ao provedor de IA; o formato de
  21/10 de `/api/painel` continua para quem o usa.
- **Motivo:** integração da página única de análise, decidida pelo responsável pelo produto em 22/10/2026. Classificação:
  mudança prevista, no escopo do contrato da página única e compatível com a SPEC e com as divergências aprovadas.
- **Documentação e testes:**
  - **Documentação:** `Docs/PAINEL_INTEGRADO_INTERFACE.md` (opções enviadas, planilhas e campos da resposta),
    `Docs/INTERFACE_CONVERSACIONAL_INTEGRADA.md` (contexto da conversa e comandos novos) e `backend/tests/legado/README.md`.
  - **Testes unitários:** `painel.test.mjs` (`nivel` e `indicador` em todo pedido, mudados de propósito porque o pedido mudou;
    planilha sem população; premissas da fonte; grupos e referência por critério vindos da conversa; resposta no formato do
    motor), `conversaGrafico.test.mjs` (o estado do gráfico nas opções da conversa e `painel_familia` nulo, mudados de propósito;
    grupos no comando) e `paginaUnica.test.mjs`. Sai `analysisCatalog.test.mjs`, com o módulo, sem uso na página única.
  - **Roteiros de navegador:** `ui_pagina_unica.py`, `ui_area_de_analise.py` e `ui_conversa_grafico.py`, nas suítes de sempre.

### 2026-10-22 · Página única de análise: estrutura, fonte dos dados e conversa; saem as telas clássicas
- **Antes:**
  - a navegação tinha cinco ações (Início, Nova sessão, Nova análise, Histórico e Resultados). Com a base do Brasil, a página
    principal era o gráfico de bolhas, e "Todas as análises" e "Outras análises" levavam ao fluxo clássico: o catálogo de 12
    análises, a preparação (Categoria, Período, Abrangência territorial, Indicador e condições), os resultados em abas (Mapa,
    Gráficos e Tabela), a investigação progressiva e os diagnósticos compostos;
  - a escolha dos dados ficava no início ("Usar dados do Brasil" e "Importar seus dados"), e no chat só depois da primeira
    mensagem; as colunas de uma planilha eram escolhidas na preparação de cada análise;
  - "Nova análise" abria as modalidades ou a escolha entre análise independente e composição;
  - a conversa preparava a análise, e o cálculo dependia de uma ação na preparação; "agora a tabela" e "ver no mapa" abriam as
    abas do resultado.
- **Agora:**
  - **Página única.** Primeiro, o aceite de privacidade. No alto, o nome do agente e a navegação: Nova sessão, Nova análise e
    Histórico (saem "Início" e "Resultados"). Logo abaixo, a fonte dos dados: "Dados do Brasil" ou "Enviar meus dados", com o
    resumo da fonte em uso (por exemplo, "Dados do Brasil · Medicina · jan/2014 a jun/2024") e "Trocar". Depois, a área de
    análise, registrada à parte com o motor do gráfico e a conversa no motor (mesmo pedido).
  - **Fonte dos dados.** A base do Brasil e as planilhas passam por `/api/inspect`; com a base pronta, o gráfico começa pelos
    estados. Arquivo com várias abas: a escolha da aba. Planilha: o painel curto "Colunas" pede só o que falta, com a sugestão
    no topo, marcada "(sugerida)", nunca usada sem escolha (D1):
    - papéis: unidade territorial, código, grupo territorial (`grupo_territorial` no `mapping` da área; ao pré-exame e à
      conversa, em `hierarchy_columns`), período, categoria, quantidade, população, latitude, longitude e identificador
      individual; unidade territorial, período e quantidade são obrigatórios;
    - o que a quantidade conta (pessoas, vínculos, postos ou outra unidade, descrita);
    - os nomes da unidade e do grupo, no singular e no plural, sugeridos pelo nome da coluna ("distrito" e "distritos",
      "província" e "províncias"; `FonteDados.rotulos`). Com uma planilha, nenhum texto da estrutura e da conversa diz
      "município"; na base do Brasil, município/municípios e estado/estados;
    - com coordenadas, o referencial: só o SIRGAS 2000 é admitido; outro, ou "Não sei", deixa a análise espacial
      indisponível, com o motivo, sem presumir;
    - o que a planilha permite: cada análise sem os dados de que precisa fica indisponível, com o motivo.
  - **Histórico e sessão.** "Nova análise" guarda a análise em exibição no Histórico e volta ao começo do gráfico com os
    mesmos dados. O Histórico lista as análises da sessão e reabre cada uma como estava, sem recalcular; as de outra fonte
    ficam listadas, desabilitadas, com o motivo. "Nova sessão" pede confirmação e oferece o CSV (valores do motor, em
    precisão integral) e a impressão da análise em exibição.
  - **Conversa.** A caixa flutuante com o rosto do agente fica sempre na página. Na abertura, aberta e mais larga, ela pergunta
    o que analisar e mostra "Dados do Brasil" e "Enviar meus dados"; a escolha também vale por mensagem. Cada pedido leva em
    `options` o contexto do gráfico (territórios na tela, família, indicador e competência). O campo `painel` da resposta vira
    um pedido para a área, com um identificador novo a cada comando; antes dos dados, o pedido fica guardado e segue quando o
    gráfico fica pronto. Ambiguidades: alternativas em botões. "Agora a tabela" aponta os Detalhes, abaixo do gráfico; "ver no
    mapa" explica que o mapa não faz parte da página; "volte ao resultado anterior" reabre a análise anterior do Histórico, sem
    recalcular.
  - **Saem do produto** (remoções de funções):
    - o catálogo de 12 análises, "Todas as análises" e "Outras análises";
    - a preparação: as caixas Categoria, Período, Abrangência territorial e Indicador, as condições específicas, o construtor
      de critérios, a Hierarquia territorial, "Linhas idênticas", os componentes desagregados, o objeto de análise, "Retomar
      parâmetros" e "Usar como municípios-alvo";
    - os resultados em abas (Mapa, Gráficos e Tabela): o cabeçalho do resultado, os cartões de destaque, o mapa de pontos, as
      barras e linhas, o pirulito do ranking, a faixa da distribuição, os halteres, os pequenos múltiplos, os selos e o filtro
      por família da tendência e "Baixar registro técnico (JSON)";
    - a investigação progressiva: diagnósticos compostos, análise independente e composição, "Destacar seleção nesta análise",
      "Usar seleção na próxima análise" e os controles lembrados por resultado;
    - os componentes e modelos usados só por essas telas: `ChatAnalysisCarousel`, `ContextConfig`,
      `ConversationalPreparation`, `CriteriaBuilder`, `CriteriaResults`, `DataResolution`, `DistributionResults`,
      `InvestigationOverview`, `InvestigationViewState`, `PeriodSelection`, `PreparationPanel`, `PreviousAnalyses`,
      `ReferenceSetup`, `RequirementChecklist`, `ResultCharts`, `ResultHeader`, `ResultTable`, `ResultVisuals`,
      `ResultWorkspace`, `TerritorialScopeSelector`, `TerritoryMap`, `TrendVisuals` e `WelcomeHero` (`.tsx`); `criteriaTree`,
      `curatedPreparation`, `diagnostics`, `headerModel`, `investigation`, `preparationReadiness`, `representation`, `trend`,
      `visualModels`, `workspaceNavigation` e `analysisCatalog` (o catálogo das 12 análises) (`.ts`).
- **Permanece:**
  - o motor e a API: `/api/analyze` e as capacidades, `/api/inspect`, `/api/preflight`, `options.abrangencia` e
    `metadata.representacao`; todos os números vêm do motor;
  - a conversa local e com o Gemini (`/api/exploration/interpret`, `/api/llm/interpret-context`, `/api/llm/interpret` e
    `/api/brazil/description`), os esclarecimentos, a sessão de 1.800 s e a privacidade; nada da base vai ao provedor de IA;
  - o aceite de privacidade, "Nova sessão" com confirmação, a falha ao encerrar, que mantém a tela, e a revogação da sessão;
  - a caixa da conversa arrastável (mouse, teclado, posição guardada e minimizar), agora com a abertura mais larga;
  - `territorialScope.ts`, `TerritorialSelection.tsx`, `useNarrow.ts`, `conversationSession.ts`, `BrandAvatar.tsx`,
    `periods.ts` e `fieldChoices.ts`, com os seus testes;
  - os dados versionados.
- **Motivo:** decisão do responsável pelo produto em 22/10/2026: "Eu só quero entrar por aquela linha, por aquele gráfico" e
  "Aproveitar a tela, funcionalidades antigas, se elas não vão contribuir para esse tipo de processo de análise e de
  visualização, eu não quero. Aí a gente precisa reestruturar." No mesmo dia, ele pediu que as planilhas de outros países
  (distritos, condados, províncias) funcionem com os nomes delas e com a pergunta do referencial das coordenadas.
  Classificação: mudança grande e prevista, aprovada pelo responsável em 22/10/2026, com as remoções listadas acima.
  - Escopo: o pedido.
  - Compatibilidade:
    - a interface é independente das diretrizes de UX da SPEC (README), e o gráfico segue o Adendo BOL-20261021;
    - a SPEC só admite o SIRGAS 2000: outro referencial deixa a análise espacial indisponível, sem presumir;
    - a decisão D1 (nenhuma confirmação de colunas) continua valendo no painel "Colunas";
    - nenhuma divergência aprovada é contrariada.
- **Documentação e testes:**
  - **Documentação:** README (interface, fonte dos dados, planilhas, conversa, testes e os trechos das capacidades que
    descreviam a tela clássica), `Docs/INTERFACE_CONVERSACIONAL_INTEGRADA.md` (reescrito para a página única),
    `Docs/SEMANTIC_BRIDGE_ADAPTACOES.md`, `Docs/CONVERSACAO_INCREMENTO_FN.md`, `Docs/DADOS_BRASIL_VALIDACAO.md`,
    `Docs/MODELO_TERRITORIAL.md`, `Docs/OTIMIZACAO_LATENCIA.md` e a nota da página única nos documentos que descreviam as
    telas clássicas (`ABRANGENCIA_TERRITORIAL`, `ANALISE_EXPLORATORIA_INTEGRADA`, `BLOCO1_RESULTADOS_EXPLORAVEIS`,
    `BLOCO2_ETAPA1_REFERENCIAS_PROXIMIDADE`, `BLOCO2_ETAPA2_CRITERIOS_INTEGRACAO`, `BLOCO3_MAPAS_VISUALIZACOES`,
    `EVOLUCAO_TEMPORAL_E_TENDENCIA`, `PREPARACAO_GUIADA` e os relatórios datados de 15 a 18/10/2026).
  - **Roteiros de navegador novos**, registrados em `run_ui_checks.py`, sem mudar os nomes das suítes nem o `ci.yml`:
    - `ui_pagina_unica.py` (suítes `bloco1` e `base-versionada`): a estrutura da página, a base do Brasil, o Histórico, Nova
      análise, Nova sessão, a caixa da conversa, uma planilha de distritos e províncias sem código IBGE pelo painel "Colunas"
      (criada no próprio roteiro, numa pasta temporária), duas abas, formato recusado, 390 px e o fim da sessão;
    - `ui_conversa_grafico.py` (suítes `conversa` e `gemini-simulado`): a conversa mudando o gráfico, com o contexto do
      gráfico nos pedidos, esclarecimentos, botões de ambiguidade, pedidos de apresentação, análise anterior, uma planilha de
      condados pela conversa e nada da base ao provedor. A suíte `conversa` passou ao catálogo sintético do Bloco 1.
  - **Roteiros que saíram com o fluxo clássico (16):** `ui_block1_smoke.py`, `ui_block1_regression.py`,
    `ui_nearest_smoke.py`, `ui_criteria_smoke.py`, `ui_map_smoke.py`, `ui_visibility_diagnostic.py`, `ui_investigation.py`,
    `ui_integrated_workspace.py`, `ui_sem_confirmacoes.py`, `ui_territorial_scope.py`, `ui_result_visuals.py`,
    `ui_conversational_smoke.py`, `ui_block1_integration.py`, `ui_semantic_continuity.py`, `ui_stabilization.py` e
    `ui_painel_integrado.py`; também `bench_ui_criteria.py`, `bench_ui_journey.py`, `bench_ui_map.py`,
    `bench_ui_nearest.py` e `prepare_ui_brazil_catalog.py`. O que cada um cobria, onde a cobertura está hoje e as lacunas:
    `backend/tests/legado/README.md`. `ui_support.py` foi reescrito para a página única (saem `select`, `stage` e `card`).
  - **Testes unitários do frontend:** novos `paginaUnica.test.mjs` e `conversaGrafico.test.mjs`. Saíram com os seus módulos
    `diagnostics`, `headerModel`, `investigation`, `preparationReadiness`, `representation`, `trend`, `visualModels` e
    `workspace` (`.test.mjs`); de `workspace.test.mjs`, os testes de `normalizeCommand`, `viewCommand` e
    `previousResultCommand` foram para `conversaGrafico.test.mjs`. Nenhuma verificação de comportamento mantido foi afrouxada.
  - **Capturas:** `scripts/capturar_telas.py` percorre a página única.

### 2026-10-22 · Área de análise da página única: famílias de análise, eixo Y do indicador e territórios em lista à vista
- **Antes:**
  - o gráfico de bolhas da página principal tinha a barra das análises: Densidade, Quantidade, Distância, Crescimento,
    Comparar / Conjuntos e "Outras análises", que abria a preparação clássica de Distribuição, Rankings, Critérios combinados,
    Rotatividade e Relatórios;
  - abria com todos os municípios da base; o universo se montava em "Municípios base": todos, estados inteiros, a busca, a
    lista ou municípios arrastados para o gráfico;
  - sem distância, o eixo único do indicador era horizontal, e a altura era só arranjo;
  - acima de 400 bolhas, com um valor ao menos 100 vezes maior que outro, o eixo começava na escala logarítmica automática;
  - "Crescimento" pedia a competência inicial e desenhava a variação percentual do motor como cometa;
  - só com a base do Brasil, sem título dinâmico nem exportação.
- **Agora:** a área de análise da página única (`frontend/src/AreaDeAnalise.tsx`), que a estrutura da página monta com a fonte,
  o pedido da conversa, o estado a restaurar e os avisos de contexto e de cálculo.
  - **Estados da tela:**
    - E0, antes dos dados: a moldura limpa, "Escolha os dados para começar", com "Dados do Brasil" e "Enviar meus dados", sem
      números; a família clicada vira intenção;
    - E1, com a base do Brasil: os 27 estados em bolhas (`nivel: "estados"`), com a linha de contexto do Brasil e a instrução
      "Clique num estado para ver os municípios dele"; nunca os 5.570 municípios de início;
    - E2 a E4: as unidades escolhidas, outra família e uma função em uso.
  - **Territórios sempre à vista, em lista** (pedido do responsável):
    - "Todos os estados (27)" e "Todos os municípios do Brasil (5.570)";
    - os 27 estados, cada um com a caixa "Todos os municípios de <estado>" e a ação "Ver os N municípios";
    - os municípios do estado aberto em caixas de marcar, com "Marcar todos" e "Desmarcar todos";
    - a busca só como complemento ("Procurar pelo nome ou código (opcional)");
    - clicar (ou Enter) na bolha de um estado abre os municípios dele, e a dica mostra "Ver os N municípios";
    - a trilha ("Brasil › Amazonas › 3 municípios") leva de volta;
    - **sai o arrastar municípios para o gráfico.**
  - **Famílias de análise,** com um só seletor de indicador (Densidade ou Quantidade):
    - Distribuição: grupos por quartis, quintis ou decis e faixas digitadas, com grupos, cortes e contagens do motor;
    - Análise espacial (no lugar de "Distância"): X = distância até a referência (por critério, nome ou conjunto), faixas de
      distância e a nota TPL-11;
    - Tendência: a janela escolhida pela pessoa, com atalhos, e as visões Mudança (no lugar de "Crescimento"), Classes e
      Séries, com as classes e as velocidades do motor (pelo menos quatro competências);
    - Rotatividade: barras de 100% da coorte inicial; com a base do Brasil, desabilitada, com o motivo e "Enviar meus dados".
  - **Eixos:** Y é o indicador em todas as famílias. No eixo único, as bolhas se espalham na horizontal só como arranjo, com a
    nota "a posição horizontal é só arranjo"; na Análise espacial, X = distância.
  - **Escala:** linear, a partir do zero; a logarítmica só por escolha da pessoa. **Sai a escala logarítmica automática.**
  - **Funções comuns** em painéis laterais: Territórios, Régua, Condições, Ordenar, Comparar, Juntar e Exportar (no celular,
    no botão "Ferramentas"). Condições, Ordenar e Comparar pedem ao motor e mostram as situações, as posições e as diferenças
    dele.
  - **Título dinâmico** ("Densidade de médicos nos municípios do Amazonas · junho de 2024") e **Detalhes** em abas: Tabela
    (100 linhas por página), Não avaliáveis e Método e procedência.
  - **Exportar:** CSV com todos os itens, em precisão integral, com a avaliabilidade e o motivo; Imprimir / PDF; o método em
    texto.
  - **Nomenclatura territorial:** os textos saem dos rótulos da fonte ou do motor (`rotulos`). Na base do Brasil, os de sempre
    (municípios e estados); numa planilha, os confirmados (distritos, províncias…), com concordância simples. Nas planilhas,
    não há bolhas de grupo: a lista dos grupos ou a das unidades.
  - **Pedido ao motor** (`frontend/src/painelApi.ts`, o único lugar com os nomes dos campos):
    - as opções do contrato de 22/10/2026: `nivel`, `grupos`, `faixas`, `faixas_distancia`, `tendencia`, `condicoes`,
      `ordenar`, `comparar`, `rotatividade` e `premissas`; e `indicador`, só com grupos, faixas ou tendência;
    - a disponibilidade das famílias e as pendências de premissa vêm do motor (`disponibilidade` e `pendencia`), com as
      opções que ele mandar (por exemplo, o referencial: SIRGAS 2000 ou WGS 84);
    - 150 ms de espera, o pedido anterior cancelado e as últimas seis respostas na memória da tela.
  - **Conversa e Histórico:** a área aplica o pedido da conversa (cada `id` uma vez), avisa o que está na tela a cada mudança
    e entrega o estado salvo a cada cálculo; o estado restaurado reabre sem recalcular.
  - **Montagem:** a estrutura da página monta a área direto; "Todas as análises" e "Outras análises" saem com as telas
    clássicas.
- **Permanece:**
  - todos os números vêm do motor: valores, grupos, faixas, classes, contagens, posições, comparações, distâncias, variações e
    motivos; a tela não soma, não ordena nem classifica nada por conta própria (RQ-REP-01 e RQ-REP-02);
  - estados e municípios nunca no mesmo eixo nem somados; o conjunto é a soma das contagens dos componentes, com possível
    dupla contagem (RQ-REP-14);
  - a régua só esconde (RQ-REP-06); a tabela equivalente tem todos os itens, em páginas de 100;
  - o modo leve acima de 400 bolhas e o arranjo exato até 400; o cometa só com a variação do motor (RQ-REP-15);
  - as cores da bolha e da mudança (azul e laranja, contínuas, com o zero cinza);
  - as telas clássicas, por "Todas as análises", enquanto a estrutura da página não as retirar;
  - nada vai ao provedor de IA; os dados não mudam.
- **Motivo:** decisões do responsável pelo produto de 22/10/2026 para a página única: uma análise integrada, sem duas telas; o
  eixo Y é o indicador; a escala logarítmica só por escolha; a escolha dos territórios visível e didática ("ele não pode ter
  que adivinhar que ele precisa clicar num estado para poder abrir a caixa de municípios. E não pode ser só por digitar");
  as planilhas de outros países com a nomenclatura delas. Classificação: mudança prevista e aprovada pelo responsável em
  22/10/2026.
  - Escopo: o pedido.
  - Compatibilidade:
    - o gráfico de bolhas segue o Adendo BOL-20261021 e a Parte 13 (RQ-REP-01 a 06, 11, 14 e 15; nenhuma mudança automática
      de escala);
    - as famílias seguem as capacidades da SPEC: CAP-DIS-02 e 03, CAP-ESP-01 a 03 (com TPL-11), CAP-TMP-01, CAP-TEN-01 (com
      os rótulos de DA-15), CAP-ROT-01, CAP-SUB-01 a 03, CAP-CMP-01 e CAP-AGR-01;
    - nenhuma divergência aprovada é contrariada.
  - A escala logarítmica automática da entrada anterior podia ser revertida pelo responsável; a página única a retira.
- **Documentação e testes:**
  - **Documentação:** `Docs/PAINEL_INTEGRADO_INTERFACE.md` passa a descrever a área de análise da página única: estados da
    tela, escolha dos territórios, famílias, eixos e cores, funções, Detalhes, pedido ao motor, acessibilidade e testes.
  - **Roteiro novo:** `backend/tests/ui_area_de_analise.py`, nas suítes `bloco1` e `base-versionada` (`ADT_BLOCK1_REAL=1`),
    registrado em `run_ui_checks.py`. Confere E0 e E1, a lista de territórios sem digitar, abrir um estado pela bolha e pela
    lista, marcar e desmarcar, a busca, a trilha de volta, Quantidade sem pedido, a régua, quartis, a análise espacial conforme
    a disponibilidade do motor, a tendência nas três visões, a rotatividade desabilitada, Condições, Ordenar, Comparar, Juntar,
    o CSV, os Detalhes, os 5.570 municípios no modo leve (base versionada) e o celular.
  - **Roteiro apagado:** `backend/tests/ui_painel_integrado.py`, porque a tela que ele percorria mudou. Onde cada verificação
    passou a existir está em `backend/tests/legado/README.md`. Saem, com o comportamento, as verificações da escala
    automática, do arrastar e da abertura com todos os municípios.
  - **Testes do modelo** (`frontend/tests/painel.test.mjs`), reescritos com o modelo; cada teste anterior tem o seu
    correspondente.
    - Mudados de propósito, porque o comportamento mudou (o defeito não está no produto nem no teste): o eixo Y do indicador
      com o arranjo horizontal, a ausência de escala automática, o cometa vertical e a abertura nos estados.
    - Novos: nomenclatura (distritos, províncias, comunas), escolha dos territórios, trilha, título, opções do pedido,
      disponibilidade das famílias, comando da conversa, janela e séries, camadas de cor, tabela, CSV, estado salvo, contexto
      e leitura da resposta.

### 2026-10-22 · Conversa no gráfico: o pedido vira o comando `painel` da página única
- **Antes:**
  - a conversa só preparava análises da preparação clássica: `/api/exploration/interpret` devolvia `operation`,
    `territory_ids` e `options_patch`; `/api/llm/interpret-context`, a proposta do intérprete (com a interpretação local
    em `exploration`); `/api/llm/interpret`, a proposta;
  - nenhuma resposta dizia ao gráfico de bolhas o que mostrar, e o gráfico só mudava pelos controles;
  - pedidos como "mostre o Pará", "use Belém como referência", "os 5 municípios com maior densidade" e "volte aos
    estados" não eram comandos locais: iam ao provedor ou recebiam "não consegui confirmar todo o recorte".
- **Agora:**
  - **Página única:** a tela envia em `options` a chave `painel_familia` (mesmo nula) e o estado do gráfico. Quando o
    pedido toca o gráfico, as três rotas devolvem `painel`, com família, indicador, nível, municípios, competência,
    janela, visão da tendência, referência, função, seleção, ordenação, condições e grupos. Chave nula mantém o que o
    gráfico tem.
    - A resposta diz o que muda no gráfico, sem valores da base: "Mostrei a densidade nos 144 municípios do Pará.".
    - A conversa só interpreta: os números vêm do motor quando a tela aplica o comando.
  - **Frases:** estado inteiro; referência por nome, por conjunto ou por critério; os N com maior ou menor; condições
    combinadas com "e" (com a distância até um município citado); comparar e juntar; janela da tendência com os "últimos
    N anos" (AT-34); volte aos estados; acrescentar e tirar municípios; competência, indicador, grupos e visões.
  - **Contexto:** o pedido seguinte parte do que está no gráfico (municípios, competência, indicador, referência e
    condições). Entre homônimos, vale o único que já está no gráfico, e a resposta diz qual, com a sigla.
  - **Ambiguidades:** estado e município com o mesmo nome, homônimos, densidade ou quantidade, direção da ordenação,
    competência de um ano com várias e as leituras AMB-04 viram pergunta com alternativas em botões do catálogo local.
    Cada botão envia o pedido completo. Nada muda no gráfico até a escolha.
  - **Planilhas de outros países:** as respostas usam os rótulos da tela (`options.rotulos`): "Mostrei a densidade nos 12
    distritos da província X". O grupo é o valor da coluna-mãe (papel `grupo_territorial` do mapeamento, que vale só para
    a conversa): "mostre a província X" vira `municipios.estados: ["X"]`. As unidades citadas pelo nome se resolvem pelo
    catálogo da planilha (`name:` ou `code:`), sem código IBGE.
  - **Rota com o provedor, na página única:** a operação proposta vira o comando do gráfico. Nomes e competências do
    pedido original são resolvidos localmente, `painel` e `reply` entram no lugar da proposta textual (sem `exploration`),
    e uma escolha pendente vem em `clarification`, com `source: "CATALOGO_LOCAL"`.
  - **Fora da página única:** as respostas anteriores ganham o `painel` equivalente, pelo mapeamento das operações atuais
    (por exemplo, `comparisons` → `funcao: "comparar"`). Pedidos de explicação do resultado não o trazem.
- **Permanece:**
  - nada é calculado na conversa;
  - o caminho local vem primeiro, nada da base vai ao provedor e os identificadores continuam protegidos;
  - fora da página única, os campos e os textos das respostas não mudam (só ganham `painel`);
  - os critérios combinados fora da página única ("uma condição por mensagem"), as leituras AT-34 e as perguntas de
    homônimos e de estados continuam como antes;
  - o motor, as rotas do painel, a interface e os dados não mudam neste commit.
- **Motivo:** pedido do responsável pelo produto em 22/10/2026: "A conversa mexendo no gráfico, eu já quero para agora
  também [...] o chat, ele tem que ser cada vez mais integrado ao contexto da tela e das análises". No mesmo dia, ele
  pediu que planilhas de outros países, com outra nomenclatura territorial (distrito, condado, província), tenham os
  nomes adaptados. Classificação: mudança prevista.
  - Escopo: o pedido (seção 4 do contrato da reestruturação da página única).
  - Compatibilidade:
    - a conversa interpreta e não calcula (Parte 6), e a ambiguidade material vira escolha explícita (CFG-AMB e AMB-04);
    - comparar 2 ou 3 itens (CAP-CMP-01), juntar pela soma dos componentes (CAP-AGR-01), condições e ordenação com empates
      (CAP-SUB-01 a CAP-SUB-03) e a tendência (CAP-TEN-01) seguem a SPEC, e o gráfico segue o Adendo BOL-20261021;
    - nenhuma divergência aprovada é contrariada.
- **Documentação e testes:**
  - **Documentação:** `Docs/CONVERSACAO_INCREMENTO_FN.md` (seção nova "Conversa no gráfico": formato do `painel`, contexto,
    frases, ambiguidades, planilhas e rotas) e README (conversação).
  - **Pytest novo:** `test_conversa_grafico.py`, com:
    - o mapeamento das operações atuais;
    - cada frase do contrato, as respostas e o contexto do gráfico;
    - as ambiguidades com os botões e o pedido de cada botão;
    - uma planilha sintética de distritos e províncias, sem código IBGE;
    - as três rotas, com o provedor de IA proibido no caminho local e sem dados da base no caminho com o provedor;
    - no job `dados-reais`, as frases com a base versionada (144 municípios do Pará, três Belém, dois Paraná).
  - Nenhum teste existente foi alterado.

### 2026-10-22 · Página única de análise: o motor do gráfico com estados, planilhas e as análises integradas
- **Antes:**
  - `POST /api/painel` e `POST /api/painel/referencias` aceitavam só a base Brasil oficial; uma planilha enviada era
    recusada;
  - o gráfico trazia só municípios e conjuntos: quantidade, população, densidade, distância até a referência e variação;
  - o resultado do gráfico não entrava na sessão;
  - a escolha pendente (422) vinha só com o texto em `detail`.
- **Agora:**
  - **Dois formatos de pedido em `POST /api/painel`:**
    - sem `nivel`, o contrato de 21/10, com as mesmas chaves e a mesma resposta (conferido item a item com a versão
      anterior em 27 pedidos); a chave da página única nesse formato continua desconhecida, e a mensagem ganha a dica
      "As chaves da página única valem com nivel (\"municipios\" ou \"estados\").";
    - com `nivel` (`"municipios"` ou `"estados"`) e `indicador` (`"densidade"` ou `"quantidade"`), a página única.
  - **Página única:**
    - **nível estados**, só na base do Brasil: os estados da fonte estadual, com a população do estado, como na
      abrangência por estados;
    - **planilhas enviadas** nas duas rotas, de qualquer país: o mapeamento de `/api/inspect`, o papel `grupo_territorial`
      (coluna-mãe opcional), `options.premissas` com os nomes das opções de `/api/analyze`, o mesmo portão do pré-exame
      (D1, sem afrouxar) e `options.rotulos` (distrito, província…) em todas as mensagens. A distância exige latitude,
      longitude e o SIRGAS 2000 confirmado; outro referencial fica indisponível, com o motivo. Sem população, só a
      quantidade. As planilhas não têm bolha de grupo nem nível estados;
    - **análises**, pelas funções do motor de `/api/analyze`: tendência CAP-TEN-01 por item na janela escolhida, grupos
      por posição (CAP-DIS-02), faixas (CAP-DIS-03) e faixas de distância (CAP-ESP-03), condições (CAP-SUB-01),
      ordenação e N primeiros (CAP-SUB-02 e CAP-SUB-03), comparação de 2 ou 3 itens (CAP-CMP-01), membro mais próximo da
      referência com os empates exatos e rotatividade (CAP-ROT-01, só na planilha com identificador individual);
    - **sempre no topo:** `rotulos`, `disponibilidade` (cada análise com o motivo e a pendência), `contexto` (a linha do
      Brasil, taxa nacional da decisão D5) e `sessao`;
    - **sessão:** com o cabeçalho `X-ADT-Session`, o resultado entra na sessão para o Histórico e a conversa, com contexto
      próprio, sem substituir o contexto da conversa; ficam os 8 resultados mais recentes do gráfico.
  - **Escolha pendente nas duas rotas e nos dois formatos:** o 422 traz também `pendencia: {chave, opcoes, texto}`; o
    `detail` não muda.
- **Permanece:**
  - todo número vem do motor, sem fórmula nova; `/api/analyze`, os resultados das análises e o contexto da conversa;
  - a tela atual, que usa o formato de 21/10, até a tela da página única;
  - nada vai ao provedor de IA; os dados não mudam.
- **Motivo:** decisões do responsável pelo produto de 22/10/2026 (página única de análise; item 1.12 aprovado: a cor da
  bolha pela família da classe de tendência de CAP-TEN-01 e a rotatividade em barras de 100%) e o requisito de 22/10 sobre
  planilhas de outros países (rótulos, grupo territorial, referencial confirmado). Classificação: mudança prevista e
  aprovada.
  - Escopo: o contrato da página única (motor, seção 3) e o requisito das planilhas.
  - Compatibilidade:
    - as capacidades são as da SPEC, pelas mesmas funções de `/api/analyze`;
    - a cor por família e as barras de 100% entram pelo complemento de 22/10/2026 do Adendo BOL-20261021, aprovado pelo
      responsável; o corpo da SPEC não muda;
    - nenhuma divergência aprovada é contrariada.
  - Refatoração sem efeito: `main.distribution_cuts` reúne os pontos de corte que `_compute` já usava, para o gráfico
    devolver os mesmos.
- **Documentação e testes:**
  - **Documentação:** `Docs/PAINEL_INTEGRADO.md` (contrato real, desvios do contrato entre as frentes, pendências,
    sessão e desempenho), README, `Docs/BLOCO3_MAPAS_VISUALIZACOES.md` (seção 7), `Docs/PAINEL_INTEGRADO_INTERFACE.md`
    (a tela atual usa o formato de 21/10) e o complemento do Adendo BOL-20261021 no fim de `IMPLEMENTATION_SPEC.md` (corpo
    conferido pelo catálogo CFG-DOC).
  - **Testes novos:** `backend/tests/test_painel_pagina.py`, com cada extensão conferida contra `/api/analyze` no catálogo
    sintético, uma planilha de distritos e províncias sem código IBGE e os testes com a base versionada (job
    `dados-reais`). Nenhum teste existente foi alterado.

### 2026-10-22 · Página principal com a base do Brasil: o gráfico de bolhas, sem travar com milhares de municípios
- **Antes:**
  - o gráfico de bolhas abria por um botão ("Abrir o painel integrado", junto da fonte atual, e "Painel integrado", na
    navegação); a abertura com a base do Brasil mostrava o catálogo de análises;
  - sem escolha na abrangência, o universo inicial era "todos" só até 300 municípios; acima disso, o gráfico esperava a escolha;
  - com muitos municípios, a página travava: com os 5.570, 193 s sem responder ao marcar "Todos os municípios" e 54 s a cada
    passo da régua; o arranjo do eixo único empilhava as bolhas numa faixa de mais de 21.000 px, e a tabela desenhava todas as
    linhas;
  - a cor do crescimento era proporcional à variação: com uma variação extrema, as comuns ficavam quase sem cor;
  - a caixa da conversa tinha 400 px de largura e a última resposta ia até 180 px de altura.
- **Agora:**
  - **Página principal:** com a base do Brasil pronta, o gráfico abre sozinho no lugar do catálogo, uma vez por fonte, se
    nenhuma análise foi pedida antes (com uma análise pedida, segue a preparação dela, como antes).
    - Sem botão nem nome próprio: saem "Painel integrado" da navegação, "Abrir o painel integrado" e o rótulo "Painel integrado"
      do cabeçalho do gráfico. "Início" leva à página principal.
    - No alto do gráfico, "Todas as análises" (no lugar de "Voltar à preparação clássica") leva ao fluxo clássico, e "Outras
      análises" (no lugar de "Na preparação clássica") abre a preparação de Distribuição, Rankings, Critérios combinados,
      Rotatividade e Relatórios.
    - Os textos da tela falam em "gráfico" no lugar de "painel". No commit seguinte ao `11ee152`, o mesmo vale para os últimos
      textos que ainda diziam "painel": a lista de não avaliáveis, o limite de conjuntos, os rótulos de acessibilidade dos
      conjuntos e dos estados e o subtítulo da caixa da conversa no celular.
  - **Conversa na página principal:** a caixa arrastável traz também a orientação inicial ("Os dados do Brasil já estão
    disponíveis. Explore os municípios no gráfico, use os botões das análises ou converse comigo.") e a fonte atual, com "Trocar
    fonte de dados". Ela abre compacta no canto inferior direito, com 380 px de largura, e a última resposta rola acima de
    120 px.
  - **Universo inicial:** sem escolha na abrangência, todos os municípios da base, também com milhares.
  - **Modo leve, acima de 400 bolhas:**
    - Arranjo do eixo único numa faixa de altura limitada, com sobreposição semitransparente quando a faixa enche, e a nota
      dizendo isso.
    - Posições estáveis: a régua só esconde.
    - Desenho simplificado, sem animação; "Reproduzir" vira "Ir para a competência final".
    - Escala logarítmica automática quando os valores são todos positivos e um é ao menos 100 vezes maior que outro; a escolha
      da pessoa prevalece.
    - Medição local com os 5.570 municípios: a maior trava da página passou a 0,26 s, um passo da régua a 0,3 s e a dica a
      0,06 s.
  - **Tabela equivalente:** 100 linhas por vez, com "Anteriores" e "Próximas".
  - **Arranjo exato, até 400 bolhas:** compara cada bolha só com as que podem alcançá-la; o resultado é idêntico ao anterior,
    conferido com os dados reais em 62, 200 e 400 municípios.
  - **Cor do crescimento:** a intensidade segue a raiz quadrada da proporção da maior variação; o tom do meio de cada braço vale
    um quarto da maior. A legenda marca as pontas, os meios e o zero. Continua contínua, sem classes.
- **Permanece:**
  - o motor e as rotas (`/api/painel` e `/api/painel/referencias`) e todos os números, que vêm do motor;
  - as telas clássicas (preparação, resultados, histórico) e o fluxo com arquivos importados;
  - o arranjo exato e as animações até 400 bolhas;
  - nada vai ao provedor de IA; os dados não mudam.
- **Motivo:** pedido do responsável pelo produto em 22/10/2026: "promova todos os ajustes, então, né, corrigindo o desempenho e
  [reestruture] a abertura, como nós tínhamos orientado já. Com os botões das análises, sem o painel integrado, [...] na página
  principal, com o chat assim arrastando". Também havia o diagnóstico do travamento com "Todos os municípios" e a ideia de
  21/10/2026: "a tela abrir em um gráfico grande e com botões das análises". Classificação: mudança prevista.
  - Escopo: o pedido.
  - Compatibilidade:
    - a interface é independente das diretrizes de UX da SPEC (README);
    - o gráfico segue o Adendo BOL-20261021 e a Parte 13: a régua continua filtro visual (RQ-REP-06), a tabela equivalente
      continua com todos os itens, em páginas, e a cor continua contínua, sem classes (RQ-REP-02);
    - nenhuma divergência aprovada é contrariada.
  - A escala logarítmica automática e a abertura com todos os municípios decorrem da correção do desempenho; o responsável pode
    revertê-las.
- **Documentação e testes:**
  - **Documentação:** `Docs/PAINEL_INTEGRADO_INTERFACE.md` (página principal, modo leve, cores, tabela e conversa), README,
    `Docs/INTERFACE_CONVERSACIONAL_INTEGRADA.md` e `Docs/BLOCO1_RESULTADOS_EXPLORAVEIS.md` (navegação).
  - **Testes de navegador mudados de propósito**, porque o comportamento mudou; o defeito não está no produto nem no teste, e
    nenhuma verificação de comportamento mantido foi retirada:
    - `ui_painel_integrado.py`: a abertura sozinha, sem botão, com todos os municípios. Na base versionada, o modo leve com os
      5.570 municípios: desenho, tabela em páginas, escala automática, régua sem travar e sem pedido, dica. Depois, "Todas as
      análises" e a volta pelo "Início".
    - `ui_block1_smoke.py`: quatro botões na navegação, sem "Painel integrado".
    - `ui_integrated_workspace.py`: "Início" leva ao gráfico, e o resultado continua em Resultados, sem recálculo.
    - `ui_conversational_smoke.py`: "Todas as análises" antes do catálogo.
    - `ui_support.select`: passa por "Todas as análises" quando o gráfico está à vista.
  - **Testes do modelo** (`frontend/tests/painel.test.mjs`):
    - novos: o arranjo do modo leve;
    - mudados de propósito: a cor pela raiz quadrada e o universo inicial com milhares.
  - **Capturas:** `scripts/capturar_telas.py` ganhou a captura da página principal.

### 2026-10-21 · Painel integrado de bolhas: a tela, com a conversa numa caixa arrastável
- **Antes:**
  - com a base do Brasil pronta, havia só o fluxo clássico: conversa, preparação em abas e resultados;
  - a navegação principal tinha quatro botões e o Histórico (Início, Nova sessão, Nova análise, Histórico e Resultados);
  - as rotas `/api/painel` e `/api/painel/referencias` não tinham tela;
  - a conversa ficava sempre na faixa ancorada da investigação, sem janela arrastável.
- **Agora:**
  - **Acesso:** só com a base do Brasil pronta (abrangência oficial).
    - "Abrir o painel integrado" aparece junto da fonte atual na conversa, e "Painel integrado" entra na navegação principal.
    - "Voltar à preparação clássica" fecha o painel. Início, Resultados, Nova análise, o Histórico e os pedidos da conversa
      que preparam uma análise também fecham.
    - Reabrir não recalcula: o painel conserva o universo, os conjuntos, a referência e o crescimento.
  - **Gráfico:** bolhas com os valores de `/api/painel`; o tamanho é a população (área proporcional), com legenda de três
    tamanhos.
    - Sem distância, eixo único do indicador, com a nota de que a altura é só arranjo. Com a distância, X em km e Y no
      indicador.
    - Embaixo, a tabela equivalente e os não avaliáveis à parte, com o motivo do motor.
    - A dica aparece ao passar o mouse e ao focar.
  - **Barra das análises:**
    - Densidade e Quantidade trocam o indicador, sem novo pedido.
    - Distância escolhe a referência por critério (`/api/painel/referencias`, "Usar o primeiro" e a escolha no empate).
    - Crescimento pede a competência inicial e mostra a variação percentual do motor como cometa.
    - Comparar / Conjuntos destaca até três itens e agrega os selecionados num conjunto: uma bolha com a soma das
      contagens dos componentes, com possível dupla contagem.
    - Distribuição, Rankings, Critérios combinados, Rotatividade e Relatórios abrem a preparação clássica.
  - **Municípios base:**
    - o universo: todos os municípios, estados inteiros e municípios acrescentados pela busca, pela lista ou arrastando
      para o gráfico;
    - o universo inicial é o da abrangência clássica. Sem escolha, ficam todos os municípios até 300; acima disso, o
      painel espera a escolha, sem pedido ao motor;
    - a régua "acima de / abaixo de", com dois cursores, é filtro visual.
  - **Recusa do motor (422):** a mensagem aparece como veio, com "Voltar ao último painel calculado" e "Tentar novamente".
  - **Conversa no painel:** caixa flutuante com o rosto do agente.
    - Arrastável pelo cabeçalho (mouse, toque e teclado) e minimizável; fica sempre dentro da janela.
    - A posição fica no `localStorage`. No celular, a caixa fica ancorada embaixo.
    - É a mesma conversa, com os mesmos identificadores e textos.
  - **Sessão:** os pedidos do painel levam o cabeçalho da sessão, que só registra o evento de confirmação. O resultado do
    painel não entra na sessão da conversa.
- **Permanece:**
  - a tela inicial, a preparação clássica e os resultados; com um arquivo importado, nada muda;
  - fora do painel, o layout da conversa é o de sempre;
  - nada é calculado na tela: valores, variações, distâncias, domínios, posições dos candidatos e motivos vêm do motor;
  - não há totais, médias, rankings nem destaque automático de quem mais cresceu (RQ-REP-01), nem classes inventadas
    (RQ-REP-02);
  - nada vai ao provedor de IA, e os dados não mudam.
- **Motivo:** decisões do responsável pelo produto de 21/10/2026: a análise acontece dentro de um gráfico grande, ao qual o
  usuário acrescenta municípios; a população fica sempre no tamanho da bolha; os eixos dependem das análises escolhidas; a
  taxa de crescimento se integra ao desenho; e o chat vira uma caixa arrastável com o rosto do agente. Classificação:
  mudança prevista.
  - Escopo: o pedido.
  - Compatibilidade:
    - o gráfico de bolhas é admitido pelo Adendo BOL-20261021 (RQ-REP-10);
    - a tela segue a Parte 13 (RQ-REP-01 a 06, 11, 14 e 15) e o contrato das rotas em `Docs/PAINEL_INTEGRADO.md`;
    - nenhuma divergência aprovada é contrariada.
  - Tornar o painel a tela inicial fica para a validação do responsável.
- **Documentação e testes:**
  - **Documentação:** `Docs/PAINEL_INTEGRADO_INTERFACE.md` (novo), `Docs/INTERFACE_CONVERSACIONAL_INTEGRADA.md` (navegação e
    caixa da conversa no painel) e `Docs/BLOCO1_RESULTADOS_EXPLORAVEIS.md` (navegação).
  - **Testes novos:**
    - `frontend/tests/painel.test.mjs`, do modelo puro;
    - `backend/tests/ui_painel_integrado.py`, registrado nas suítes `bloco1` e `base-versionada` (`ADT_BLOCK1_REAL=1`).
  - **Roteiro mudado de propósito:** `ui_block1_smoke.py` passa a contar cinco botões na navegação e confere "Painel
    integrado". O comportamento mudou; o defeito não está no produto nem no teste. Nenhuma verificação foi removida.

### 2026-10-21 · Painel integrado: rotas do motor e gráfico de bolhas admitido na SPEC (Adendo BOL-20261021)
- **Antes:**
  - não havia rota que servisse um gráfico de bolhas;
  - RQ-REP-10 não admitia bolhas, e `Docs/BLOCO3_MAPAS_VISUALIZACOES.md` (seção 7) dizia "Dispersão e bolhas: não
    implementados", com a proposta "pendente de aprovação".
- **Agora:**
  - **SPEC:** o Adendo BOL-20261021, no fim de `IMPLEMENTATION_SPEC.md`, traz:
    - a redação vigente de RQ-REP-10, com o gráfico de bolhas e as suas regras;
    - o nome vigente de CAP-REP-02: "Gráfico de barras, gráfico de linhas, série temporal e gráfico de bolhas";
    - o registro da decisão como complemento de DA-23 (Parte 22).

    A versão continua 1.2.4.
  - **`POST /api/painel`:** só com a base Brasil oficial (fonte municipal), numa competência e numa categoria. Devolve
    população, quantidade e densidade de cada município base e dos membros da referência, na ordem do código IBGE.
    - **Conjuntos:** cada um vira um item agregado (`SOMA_DOS_COMPONENTES`; agregado parcial com `AGREGADO_PARCIAL`).
    - **Distância:** até a referência ou até o membro mais próximo do conjunto de referência, pelo mínimo do conjunto
      completo. Nos conjuntos base, a do membro mais próximo e a do mais distante (`distancia_km_max`).
    - **Variação percentual:** desde a `competencia_inicial` (CAP-TMP-01; base zero e falta de registro ficam nulas,
      com o motivo).
    - **Também na resposta:** `inicial`, `avaliavel`, `motivos`, `dominios`, `notas`, `limitacoes`, `versao_base` e
      `chave_execucao`. Os não avaliáveis seguem com o motivo, nunca como zero.
  - **`POST /api/painel/referencias`:** candidatos do universo na ordem do critério (densidade, quantidade ou população;
    maior para menor ou o inverso), com empates na mesma posição (1, 2, 2, 4) e os não avaliáveis numa lista separada,
    sem posição.
  - **Recusas (422, em português):** base importada; versão divergente; competência ou categoria inexistente;
    competência inicial que não é anterior; ids inexistentes; conjunto sem membros ou com um só; chave desconhecida em
    `options`.
  - **Sessão:** o resultado do painel não entra na sessão da conversa. Com o cabeçalho de sessão, só se registra o
    evento `CONFIRMACAO`, como em `/api/analyze`; a gravação do resultado fica como próximo passo.
- **Permanece:**
  - as análises existentes, `/api/analyze`, as suas chaves de execução e a tela atual (a tela do painel chega em entrega
    própria);
  - o corpo v1.2.4 da SPEC e o Anexo A, literais. O catálogo CFG-DOC confere o corpo pelo SHA-256
    (`document_catalog.SPEC_SHA`) e pelos localizadores (RQ-REP-10 em L2010; o nome de CAP-REP-02 em L1723). Por isso o
    ajuste foi feito por adendo, como o APT-20261016. O snapshot das sessões continua `SPEC-1.2.4/APT-20261016`, e as
    formas literais PT/EN do catálogo não mudam;
  - nada vai ao provedor de IA; os dados não mudam.
- **Motivo:** decisões do responsável pelo produto de 21/10/2026 ("Autorizo a inserção de gráfico de bolhas, pode
  ajustar a Spec nesse sentido.") e o contrato do painel entre o motor e a tela. Classificação: mudança prevista.
  - Escopo: o pedido.
  - Compatibilidade: prevista na SPEC ajustada pelo Adendo BOL-20261021. Os valores seguem os contratos existentes
    (CAP-IND-01/02, CAP-AGR-01, CAP-ESP-01/02, CAP-TMP-01, CAP-REF-01 e CAP-SUB-02), pelas mesmas funções do motor, sem
    fórmula nova.
  - Extensões compatíveis ao contrato, descritas em `Docs/PAINEL_INTEGRADO.md`:
    - `referencia.criterio.universo`, opcional;
    - `dominios.variacao_quantidade` e `dominios.variacao_populacao`;
    - na rota 2, `categoria` e o nome `nao_avaliaveis`;
    - `referencia` (booleano) em todos os itens.
- **Documentação e testes:**
  - **Documentação:** `Docs/PAINEL_INTEGRADO.md` (novo, seção "Motor e rotas"), README,
    `Docs/BLOCO3_MAPAS_VISUALIZACOES.md` (seções 7, 15 e 16) e o adendo da SPEC.
  - **Testes:** `backend/tests/test_painel.py`.
    - Dez testes com catálogo sintético: chaves exatas do contrato; coerência com a análise de densidade e com a
      agregação; distância até a referência e até o conjunto de referência, coerente com `compute_nearest`; mínimo e
      máximo do conjunto base; ausência de coordenada; variação com base zero e `INCOMPARABILIDADE`; ordem com empates
      1, 2, 2, 4; recusas; nenhuma chamada ao provedor.
    - Dois testes com a base versionada, no job `dados-reais`.

    Nenhum teste existente foi alterado.

### 2026-10-21 · Abrangência territorial: municípios do estado escolhido à vista, sem grupo recolhível
- **Antes:** na base oficial, a seção Municípios da lista vertical tinha um grupo recolhível por estado, no fim da lista
  (depois de Brasil e dos 27 estados), com a caixa do grupo e o botão do estado. Os municípios só apareciam ao abrir o
  grupo, numa caixa dentro do estado, e a lista inteira rolava dentro de uma caixa de até 460 px.
- **Agora:**
  - **Seção Municípios:** traz "Todos os municípios" e o seletor nativo **"Estado dos municípios"**
    (`territory-municipal-state`; cada estado com "k de N marcados"). A lista do estado escolhido fica à vista, logo
    abaixo, com a caixa "Todos os N municípios de …" e cada município.
  - **Estado sem escolha:** vale o do primeiro município marcado.
  - **"Marcados em: AM (2) · …":** leva a cada estado com municípios marcados.
  - **Seção Estados:** avisa que cada caixa marca o estado inteiro e que os municípios ficam na seção Municípios.
  - **Rolagem:** os estados e os municípios do estado escolhido rolam por dentro, e os títulos das seções ficam à vista.
  - **Com "Todos os municípios" marcado:** o seletor e a lista saem, e a seção diz como voltar a escolher municípios.
- **Permanece:**
  - a ordem vertical Brasil, estados, todos os municípios e municípios;
  - as caixas de marcar nativas, com os mesmos identificadores (`territory-option-code-…`, `territory-group-check-NN`,
    com o rótulo acessível "Municípios de … (N)");
  - as regras de cada análise, o padrão, a escolha pendente, "Limpar seleção", o resumo ao lado e o que é enviado em
    `options.abrangencia`;
  - nenhum filtro de texto e nenhum item "fora desta análise";
  - nada é calculado na tela.
- **Motivo:** pedido do responsável pelo produto de 21/10/2026. Não ficava claro que, ao clicar num estado, os
  municípios ficavam numa caixa dentro dele; o desenho não devia esconder os municípios do usuário. Classificação:
  mudança prevista.
  - Escopo: o pedido.
  - Compatibilidade: a decisão D3 (abrangência vertical) e a lista enxuta de 19/10/2026 continuam valendo. O seletor do
    estado é um controle de formulário comum, não a navegação avançada nem o filtro de texto deixados de fora da
    lista, e a SPEC não trata da forma da lista.
- **Documentação e testes:**
  - **Documentação:** README (abrangência), `Docs/ABRANGENCIA_TERRITORIAL.md` (tela), `Docs/INTERFACE_CONVERSACIONAL_INTEGRADA.md`
    e `Docs/PREPARACAO_GUIADA.md`.
  - **Roteiros mudados de propósito:** o comportamento mudou, e o defeito não está no produto nem no teste. O botão do
    grupo deixa de existir e o estado passa a ser escolhido no seletor.
    - `ui_support.py`: `municipality()` escolhe o estado no seletor, e o novo `municipal_group()` devolve a caixa do grupo
      do estado.
    - `ui_territorial_scope.py` (MG com os 853 municípios à vista, "Todos os 853 municípios de Minas Gerais" e seletor
      vazio sem marcação), `ui_result_visuals.py` e `ui_block1_smoke.py` (teclado no seletor nativo).
    - `scripts/capturar_telas.py` (os municípios do Amazonas à vista).
  - Nenhuma verificação foi removida.

### 2026-10-21 · Continuidade da conversa: territórios mantidos e "últimos N anos" com as duas âncoras
- **Antes:**
  - "Quero fazer a comparação dos últimos 5 anos", depois de citar municípios, caía na gramática local, que reconhecia
    a comparação mas recusava o resto da frase. As palavras "fazer", "últimos", "5" e "anos" não eram conhecidas, e
    nenhum código tratava períodos relativos. A conversa respondia "Identifiquei o tipo de análise, mas não consegui
    confirmar todo o recorte. Quais estados ou municípios você quer usar? …", mesmo com os municípios na abrangência,
    e o período se perdia.
  - "E nos últimos 5 anos?", sem palavra de análise, ia ao provedor de IA.
  - Os municípios citados antes da escolha dos dados não chegavam à abrangência.
  - A resposta de uma continuação dizia só "Recorte identificado com N territórios.".
- **Agora:**
  - **Territórios mantidos:** um pedido sem territórios usa os já escolhidos, e a resposta diz quais ("Mantive os 3
    territórios já escolhidos na conversa: …").
  - **Período sozinho:** um pedido só com o período ("E nos últimos 5 anos?") continua a análise ativa, na gramática
    local, sem o provedor de IA.
  - **"Últimos N anos" e "último ano":** são contados até o último ano da base e até o ano corrente, pela data local
    do navegador (`options.conversation_today`, fora da assinatura do contexto).
    - Mesmas competências da base nas duas contagens: o período é aplicado e dito na resposta ("“Últimos 3 anos”: de
      2022 a 2024 …").
    - Contagens diferentes (AMB-04): a conversa apresenta as duas leituras ("até o último período da base (de 2020 a
      2024) ou até hoje (de 2022 a 2026; a base vai até 2024, então ficariam de 2022 a 2024)"), sem escolher nem
      trocar os períodos. Cada leitura com competências na base vira uma alternativa clicável, que envia o pedido com os
      anos explícitos ("Comparação de 2020 a 2024").
    - Sem o número ("últimos anos"), a conversa pergunta quantos anos.
    - Na virada do ano, sem a data local, a conversa pede os anos (AMBIGUIDADE_MATERIAL).
  - **Verbos comuns:** "fazer", "faça", "façamos", "veja", "vejamos" e "saber" não impedem a interpretação local.
  - **Pedido anterior à escolha dos dados:** é interpretado de novo quando a base fica pronta, e os municípios citados
    nele vão para a abrangência. Sem interpretação local, vale a análise proposta, como antes.
  - **Leituras pendentes pelo canal do provedor:** as alternativas também aparecem quando as leituras chegam pela
    interpretação local refeita no canal do provedor.
- **Permanece:**
  - nada é calculado na conversa;
  - nomes citados no pedido substituem a seleção, como antes;
  - a conversa continua recebendo só os municípios marcados (`territory_ids`), sem a abrangência, e nada vai ao provedor
    de IA além do que já ia;
  - anos e intervalos explícitos, competências e as perguntas de homônimos, de estados e de municípios faltantes não
    mudam;
  - os outros marcadores relativos ("este ano", "ano passado", "recente") seguem o caminho anterior.
- **Motivo:** pedido do responsável pelo produto de 21/10/2026. Ao longo da conversa, o agente não associava "quero
  fazer a comparação dos últimos 5 anos" aos municípios citados no início, e a preservação do estado estruturado da
  conversa devia ser verificada. A causa foi conferida no código: a gramática recusava a frase e os períodos relativos
  não eram tratados. Classificação: mudança prevista.
  - Escopo: o pedido.
  - Compatibilidade: segue a AT-34, a RQ-GOV-23 e a RQ-GOV-18. AMB-04 só se aplica quando as âncoras produzem leituras
    materialmente diferentes (L1014 e L1631); por isso, contagens com as mesmas competências da base prosseguem com a
    interpretação explicitada. O território mantido é dito na resposta, sem escolha silenciosa, e nenhuma divergência
    aprovada é contrariada.
- **Documentação e testes:**
  - **Documentação:** README (continuidade da conversa), `Docs/INTERFACE_CONVERSACIONAL_INTEGRADA.md` (seção nova) e
    `Docs/ABRANGENCIA_TERRITORIAL.md` (gramática da conversa).
  - **Pytest novo:** `test_conversation_followup.py`, com:
    - leituras divergentes com as alternativas e os territórios mantidos;
    - leituras coincidentes com a nota;
    - período sozinho continuando a análise ativa, sem trocar os períodos com a leitura em aberto;
    - pergunta do número de anos;
    - ano corrente pela data local e virada do ano (AMBIGUIDADE_MATERIAL);
    - leitura sem anos na base;
    - verbos comuns;
    - a rota `/api/exploration/interpret`.
  - **Roteiro ampliado:** `ui_stabilization.py` ganha "Quero fazer a comparação dos últimos 5 anos." depois de "Inclua
    Parintins.". O roteiro confere os três municípios mantidos, nenhuma chamada ao provedor e a comparação com as
    competências de 2023 e 2024. Nenhum teste existente foi alterado.

### 2026-10-21 · Base oficial: o cálculo só fica retido pelas escolhas da análise; competência dos valores explicada
- **Antes:** na base oficial, o botão "Calcular e mostrar resultado" ficava desabilitado até o pré-exame liberar a
  análise. Abaixo dele aparecia "Ainda faltam condições específicas para esta análise. Você pode ajustá-las acima ou
  consultar as opções adicionais.", sem dizer o que faltava. "Ver outras condições da análise" abria as três etapas da
  preparação guiada: associação de colunas, código IBGE, resoluções e revisão. Uma falha do pré-exame só aparecia
  ali dentro. Na comparação, a caixa "Competência dos valores" ficava na grade em qualquer caso, inclusive com um
  período só, e repetia os períodos já escolhidos.
- **Agora:** o botão fica disponível o tempo todo, menos durante a conferência da análise e o cálculo.
  - **Clique com escolhas faltando:** a tela diz quais faltam, pelo título das caixas e na ordem delas (`missing-choices`,
    por exemplo "Falta escolher: Período e Indicador."). Ela abre a lista do Período ou da Abrangência territorial quando
    é essa a primeira que falta, e nada é calculado.
  - **O que retém o cálculo:** só a Categoria, o Período, a Abrangência territorial (escolha pendente), o Indicador e,
    quando a análise os usa, o Território de referência e o Referencial geodésico. Com essas escolhas feitas, o que ainda
    impedir o cálculo aparece com o texto do pré-exame.
  - **O que saiu:** "Ver outras condições da análise" e o aviso genérico. A falha do pré-exame aparece na própria
    preparação, com "Verificar novamente".
  - **Comparação:** com um período só, não há escolha de competência. Com dois ou mais, a frase "Valores lado a lado em
    [competência] (a última competência do período). As demais competências do período mostram a mudança e a tendência de
    cada território." fica abaixo das configurações (`comparison-values-period`). O seletor dela (`comparison-values-choice`)
    traz só as competências do período, e a nota da lista do Período foi reescrita.
- **Permanece:**
  - o backend decide a disponibilidade e confere o pedido;
  - as opções enviadas não mudam, inclusive `comparison_values_period` (a competência única, a escolhida ou a última da
    janela);
  - as premissas internas seguem em "Método e limitações";
  - a escolha pendente da abrangência e os motivos da análise espacial seguem com os textos do backend;
  - nas bases importadas ficam "Ajustar condições específicas ou situações excepcionais", "Executar análise"
    desabilitado até a análise ficar pronta e o seletor na frase da janela.
- **Motivo:** pedido do responsável pelo produto de 21/10/2026. A base oficial já dá todas as condições da análise, e o
  usuário não precisa conhecê-la. A etapa só fica retida por falta de categoria, período, abrangência ou indicador,
  informada ao clicar, sem pedir código IBGE nem confirmação de informação da base. A "competência dos valores"
  repetia os períodos sem explicar o que era. Classificação: mudança prevista.
  - Escopo: o pedido.
  - Compatibilidade: a SPEC não exige o botão desabilitado nem o painel de condições avançadas na base oficial; ela
    pede não executar o que está retido e apresentar os motivos, o que continua. D1 (sem confirmações) e D6 (competência
    dos valores na comparação com janela, escolhida pelo usuário) continuam valendo.
- **Documentação e testes:**
  - **Documentação:** `Docs/INTERFACE_CONVERSACIONAL_INTEGRADA.md` (escolhas que retêm o cálculo; comparação com janela),
    `Docs/PREPARACAO_GUIADA.md` (etapas só nas bases importadas), README (comparação e capturas) e
    `Docs/BLOCO3_MAPAS_VISUALIZACOES.md`.
  - **Node:** `preparationReadiness.test.mjs` (escolhas nomeadas na ordem das caixas, parâmetros da análise espacial,
    mensagem sem pedido sobre a base).
  - **Roteiros mudados de propósito:** o comportamento mudou, e o defeito não está no produto nem no teste.
    - `ui_conversational_smoke.py`, `ui_nearest_smoke.py` e `ui_territorial_scope.py`: "botão desabilitado" passa a
      "clique nomeia o que falta e nada é calculado".
    - `ui_sem_confirmacoes.py`, `ui_block1_smoke.py` e `ui_stabilization.py`: as condições avançadas da base oficial
      passam de "visíveis, sem confirmação" a "inexistentes", e a Distribuição sem indicador diz "Indicador" no clique.
    - `ui_result_visuals.py`: a competência dos valores passa a ser conferida pelo valor do seletor (202406) e pela
      indicação da última competência.
    - `scripts/capturar_telas.py`: a tela 09 passa a ser o aviso das escolhas que faltam.
  - Nenhuma verificação foi removida sem a equivalente do comportamento novo.

### 2026-10-21 · Timeout do Gemini de 75 segundos e mensagem específica de tempo limite
- **Antes:** o cliente HTTP aguardava 22 segundos por operação. Tempo limite e demais falhas de transporte
  retornavam HTTP 503 com a mesma mensagem: "Não foi possível alcançar a API Gemini. Tente novamente.".
- **Agora:** o timeout técnico é de 75 segundos. `httpx.TimeoutException` e suas subclasses retornam HTTP 503
  com "Tempo limite de 75 segundos excedido na comunicação com a API Gemini. Tente novamente."; os demais
  `httpx.RequestError` mantêm a mensagem de conexão. A interface já apresenta o detalhe devolvido pela API.
- **Permanece:** códigos HTTP, tratamento de cota/autorização/erros HTTP do provedor, nenhuma nova tentativa
  automática, modelo, limite local de chamadas, biblioteca e seus exemplos, minimização, motor e prazo da sessão.
  Nenhuma base foi alterada ou enviada ao provedor. A SPEC e o workflow de CI não foram alterados.
- **Motivo:** pedido explícito do responsável em 21/10/2026 após reprodução de `ReadTimeout` em 22,74 s e
  conclusão de uma chamada com espera ampliada em 47,27 s. Classificação prévia: mudança prevista nos dois
  itens (prazo e mensagem). Escopo: o pedido; compatibilidade: CFG-OPR, seção 4.4.24 e RQ-DEG-10 deixam o
  prazo técnico a cargo do componente, separado da sessão; não há divergência aprovada contrariada.
  A investigação de latência, com frase sintética e sem base, não muda o comportamento da biblioteca.
- **Documentação e testes:** README, [diagnóstico de latência](DIAGNOSTICO_LATENCIA_GEMINI_20261021.md) e
  [biblioteca conversacional](BIBLIOTECA_CONVERSACIONAL.md). `test_http_transport_uses_json_schema_header_and_no_dataset`
  em `backend/tests/test_llm_bridge.py` passa de `timeout <= 30` para `timeout == 75.0`: a expectativa anterior
  ficou incompatível com a mudança intencional, não se trata de falha a contornar. O novo teste parametrizado
  cobre os quatro tipos de timeout e quatro outros erros de transporte através da API, mensagens exatas,
  status 503, ausência de detalhes privados, uma única tentativa, limpeza dos exemplos e saúde do backend.
  Os testes de erros HTTP também cobrem 503 e 504 do provedor, que não são confundidos com timeout local.
  A ferramenta manual `scripts/diagnosticar_latencia_gemini.py` mede seis chamadas reais somente quando
  solicitada; não é teste do CI. As suítes de verificação rodam exclusivamente no GitHub Actions.

### 2026-10-20 · Biblioteca de Inteligência Conversacional consumida pelo intérprete
- **Antes:** o Gemini recebia só as regras fixas (`_SYSTEM`), a mensagem minimizada, até quatro mensagens
  anteriores e os estados técnicos, sem nenhum exemplo de interpretação.
- **Agora:** a cada mensagem que chega ao provedor, `backend/llm_bridge.py` acrescenta à instrução de sistema um
  bloco com até cinco turnos de trajetórias da biblioteca (`backend/biblioteca_conversacional/trajetorias/`),
  escolhidos por `backend/conversation_library.py` (recuperação lexical local pela mensagem, pela mensagem anterior
  e pelo estado verificado) e mascarados pela mesma minimização das mensagens do usuário naquele pedido (valores,
  campos e arquivo da base em uso, números e nomes). A resposta de `/api/llm/interpret` e
  `/api/llm/interpret-context` traz `biblioteca: {versao, exemplos}` quando houve exemplos.
  `ADT_BIBLIOTECA_CONVERSACIONAL=0` desliga a biblioteca e restaura o pedido anterior; `ADT_BIBLIOTECA_EXEMPLOS`
  (1 a 8, padrão 5) limita os exemplos.
- **Permanece:** a conversa não calcula; a resposta do provedor passa pelas mesmas validações (enumerações, âncoras
  literais, cortesia da lista fechada, pré-exame) e nenhum valor da base vai ao provedor (a minimização foi separada
  em funções, com o mesmo resultado); referência mais próxima e critérios combinados continuam só no canal
  determinístico; EN continua não autorizado (mensagens em inglês e espanhol são interpretadas e a apresentação segue
  em português). Os testes existentes não mudaram de expectativa.
- **Motivo:** pedido do responsável pelo produto (20/10/2026): biblioteca de trajetórias conversacionais integrada e
  consumida pelo intérprete, para reconhecer intenções, continuidade e alterações de parâmetros sem perguntas
  desnecessárias. Classificação (regra 1): mudança prevista. Escopo: o pedido. Compatibilidade: a SPEC não regula
  exemplos ao intérprete; os exemplos não levam dado da base ao provedor (RQ-ARQ-06, RQ-DAD-20) nem autoridade
  factual (INV-02), e não têm texto de resposta (as explicações continuam no catálogo governado).
- **Documentação e testes:** [Biblioteca conversacional](BIBLIOTECA_CONVERSACIONAL.md) (novo) e README (conversa com
  Gemini). Testes novos: `backend/tests/test_conversation_library.py` (biblioteca íntegra e abrangente, consumo
  mascarado pelo provedor, pedido idêntico ao anterior com a biblioteca desligada, pertinência em trajetórias
  inéditas de `backend/tests/biblioteca_ineditas/` contra exemplos fixos e aleatórios, desempenho e, com a base
  versionada, nenhum valor da base nos exemplos), `backend/tests/test_conversation_library_readings.py` (as formas
  governadas esperadas na leitura do resultado são as que o sistema apresenta) e exemplos registrados pelo Gemini
  simulado em `ui_block1_integration.py`. Ferramenta de manutenção: `scripts/biblioteca_conversacional.py`. A
  comparação com um modelo real (`comparar`, Gemini ou servidor compatível) não foi executada: o ambiente de
  desenvolvimento não tinha `GEMINI_API_KEY` nem acesso a modelos abertos; a melhoria medida é a pertinência dos
  exemplos.

### 2026-10-20 · Competência por extenso e ano reconhecidos na proposta do intérprete
- **Antes:** no caminho do intérprete, o Python só reconhecia competências escritas como na base (AAAAMM) e anos
  soltos: "densidade em junho de 2024" virava o ano "2024", que não é uma competência literal da base, e a conversa
  respondia "O período mencionado não foi encontrado na base. Deseja revisar o período na preparação?", mesmo com
  junho de 2024 na base; "em 2023" recebia a mesma resposta.
- **Agora:** o mês por extenso com ano vira a competência AAAAMM ("junho de 2024" → 202406), como na gramática local;
  o ano sozinho vira as competências da base nesse ano: uma só é usada, e várias ficam em escolha ("Há mais de um
  período ou categoria no pedido; escolha o recorte na preparação."), sem a pergunta de período inexistente. Com mês
  sem ano ("de janeiro a junho de 2024"), nada é convertido, como antes.
- **Permanece:** competência que não existe na base continua com a pergunta ("junho de 2030", 203001); nenhuma
  competência é escolhida em silêncio entre várias; categorias continuam com correspondência literal; nada é
  calculado.
- **Motivo:** pedido do responsável pelo produto (20/10/2026) para a biblioteca conversacional: reduzir perguntas e
  confirmações desnecessárias e reconhecer alterações de parâmetros. Classificação (regra 1): mudança prevista.
  Escopo: o pedido. Compatibilidade: não perguntar quando há valor único ancorado (RQ-GOV-14), com a mesma conversão
  determinística que a gramática local já fazia; sem equivalência semântica.
- **Documentação e testes:** README (conversa com Gemini); `backend/tests/test_conversation_periods.py` (novo).

### 2026-10-20 · Abas do resultado e resultado anterior pela conversa; métodos da distribuição e da referência mais próxima pelo catálogo
- **Antes:** o contrato do intérprete não tinha atos para ver o resultado em mapa, gráfico ou tabela nem para voltar
  ao resultado anterior: "mostra num gráfico" e "volta pro resultado anterior" recebiam orientação genérica ou a
  pergunta "A qual parte da investigação você se refere?". Perguntas conceituais sobre os pontos de corte e as classes
  da distribuição e sobre a referência mais próxima terminavam em "Não identifiquei uma análise inequívoca"; só
  densidade, distância e agregação tinham formas governadas na conversa.
- **Agora:** o contrato do intérprete ganhou os atos `show_map`, `show_chart`, `show_table` e `previous_result`
  (resposta com `dialogue_action`, sem proposta e sem cálculo), descritos na instrução de sistema, e os tópicos
  `distribution` (DOC:CAP-DIS-02.metodo) e `nearest` (DOC:CAP-ESP-02.metodo, .saida e .avaliabilidade), respondidos
  com as formas PT do catálogo. Na interface, com resultado apresentado, as formas diretas ("mostre no gráfico",
  "agora a tabela", "ver no mapa", "volte ao resultado anterior"; `viewCommand` e `previousResultCommand` em
  `workspaceNavigation.ts`) e os atos devolvidos pelo intérprete abrem a aba ("Resultado aberto na aba Gráficos. Nada
  foi recalculado.") ou reabrem o resultado anterior da sessão ("Resultado anterior reaberto, sem recalcular.");
  sem resultado, a conversa avisa ("Ainda não há resultado calculado…" e "Ainda não há resultado anterior nesta
  sessão.").
- **Permanece:** a conversa não calcula; a resposta do provedor passa pelas mesmas validações; formas que não são
  ditas exatamente não mudam a tela. Tendência, mudança temporal, comparação, contagem, ranking, critérios e
  rotatividade continuam sem explicação metodológica na conversa: na conferência de 20/10/2026, suas formas descrevem
  etapas que o protótipo não implementa (a tendência depende de decisão do responsável sobre
  CAP-TEN-01.avaliabilidade). Os testes existentes não mudaram de expectativa.
- **Motivo:** pedido do responsável pelo produto (20/10/2026) para a biblioteca conversacional: o intérprete precisa
  de atos para as ferramentas que já existem, e as explicações só podem vir do catálogo governado. Classificação
  (regra 1): mudança prevista. Escopo: o pedido. Compatibilidade: voltar ao resultado anterior sem recalcular segue
  RQ-LIN-20; as explicações são formas PT existentes, sem paráfrase (CFG-DOC, FN-META-01, APT-20261016), conferidas
  contra o motor.
- **Documentação e testes:** README (conversa com Gemini) e
  [interface conversacional integrada](INTERFACE_CONVERSACIONAL_INTEGRADA.md). Testes novos:
  `backend/tests/test_conversation_actions.py`, casos Node em `frontend/tests/workspace.test.mjs` e passos de conversa
  em `ui_result_visuals.py` (abas e resultado anterior, sem recalcular).

### 2026-10-19 · Estados pela fonte estadual de médicos únicos, com a população dos seus municípios na competência; agregação de estados; conversa com estados, regiões e anos

- **Antes:** a base tinha duas fontes (nacional e municipal), e o estado era a soma dos seus municípios pelo prefixo do código IBGE: nível "Estado (soma dos municípios)", tipo "Soma dos componentes (possível dupla contagem)", AGREGADO_PARCIAL com o valor dos municípios presentes quando faltava algum, `metadata.suporte_agregado`, INCOMPARABILIDADE na evolução quando os municípios presentes mudavam, `metodos.estado` = `brasil-cod-uf-prefix-1` e a nota de que a dupla contagem variava entre os estados no ranking; na agregação, o estado marcado entrava pelos seus municípios (rota municipal). A lista da tela mostrava cada estado como "soma de N municípios", com o aviso de que o mesmo médico podia ser contado em mais de um município, e os gráficos e cartões do estado tinham textura listrada, "possível dupla contagem" e "na soma das contagens dos municípios". A conversa só marcava municípios ("no Amazonas" virava os municípios do estado), não entendia anos soltos ("em 2024") nem intervalos de anos, não reconhecia "quantos médicos …" como quantitativos e respondia "Recorte identificado com 1 territórios". Na comparação com janela, o extremo sem densidade podia levar NaN às colunas da janela.
- **Agora:** **Fonte estadual:** `Dados_Estados_Brasil.csv` (594 registros: 27 UFs × 22 competências, SHA-256 `7f64a828389d…`), gravado sem alterar valores por `backend/build_state_source.py` a partir da planilha de médicos únicos por estado entregue pelo responsável pelo produto (SHA-256 `51aa58879efc…`, não versionada), é a terceira fonte da base, conferida no manifesto e na identidade da versão (`68944004901c…`); `scope=state` não é recorte (422) e `available_scopes` continua nacional e municipal. **Estado (UF-CONTAGEM-ESTADUAL-1):** a contagem da fonte estadual, nunca a soma dos municípios; nível "Estado", tipo "Unidades distintas: contagem estadual (não é a soma dos municípios)"; competência sem registro do estado: "Não avaliável: sem registro nesta competência na fonte estadual". **População (UF-POP-MUNICIPIOS-1):** soma dos municípios do estado na própria competência, só com todos registrados; sem algum, a densidade do estado fica "Não avaliável: população estadual incompleta nesta competência (DENOMINADOR_AUSENTE)", com a contagem preservada, a cobertura ("População: 644 de 645 municípios; sem registro: 353286") e a nota (RO, MG e SP em 2015/1, SC em 2017/1 e RS em 2015/6 e 2020/1); `metadata.populacao_estadual` na densidade (e `metadata.suporte_agregado` só na agregação de estados); `metodos.estado` = `UF-CONTAGEM-ESTADUAL-1` e `metodos.populacao_estadual` = `UF-POP-MUNICIPIOS-1`; SP em junho de 2024: 148.909 ÷ 45.973.194 × 1.000 = 3,2390. Contagem estadual acima da soma completa dos municípios (DF de 2014/1 a 2017/6) entra como está, com nota. **Análises:** evolução com lacunas onde a população está incompleta (sem INCOMPARABILIDADE de estado); comparação, ranking e distribuição com o estado sem valor fora da relação, com a condição; universos "estados selecionados (contagem estadual de médicos únicos)"; **agregação de estados** pela rota de níveis: soma das contagens estaduais e das populações, tipo "Soma dos componentes (possível dupla contagem)", limitação SOMA_COM_POSSIVEL_DUPLA_CONTAGEM e a nota "Agregação de estados: …"; mínimo de dois estados; estados com municípios na agregação é escolha pendente; "unidades sem sobreposição" e "pessoas distintas" recusadas ("A agregação de estados é sempre a soma das contagens estaduais …"); estado sem contagem ou sem a população completa na competência fica fora, e o agregado é parcial sobre os avaliáveis (AGREGADO_PARCIAL, nota e `metadata.suporte_agregado` com previstos, incluídos e não avaliáveis), como pede a CAP-AGR-01; sem nenhum avaliável, não há resultado. **Inspeção:** `niveis` com `regra_estado`, `regra_populacao_estadual`, `regra_membros_estado`, `fonte_estadual` e `estados[].objeto`; sem a fonte estadual no perfil, "estado" sai da matriz com o motivo. **Tela:** selo "médicos únicos", aviso "Cada estado conta os médicos diferentes do estado (fonte estadual): …", "população de N municípios" e só as UFs da fonte estadual como estado; `uf-warning` "Fonte estadual: médicos únicos de cada estado · a soma dos estados não é o total do Brasil.", sem textura; painéis "· Estados"; procedência com "fontes nacional, estadual e municipal" e "População dos estados"; descrição da base com a origem do Brasil e dos estados. **Conversa (gramática local da base oficial):** marca estados como objeto (campo `estados` da proposta, que substitui a seleção na tela): o nome do estado, "estado de …" e "estados da Região …" (primeiro dígito do código IBGE); anos e intervalos de anos viram as competências da base (numa análise de uma competência, com várias no ano, a conversa pede a escolha); "quantos médicos" e "número de médicos" preparam quantitativos ou o indicador quantidade, e as palavras do pedido prevalecem sobre o indicador anterior na evolução e na comparação; nome de estado que também é de município pergunta "estado de …" ou "município de …", com a análise pendente; "Pará" só com acento; estado como alvo da referência mais próxima é explicado; "1 território" no singular. Anos, intervalos de anos e a precedência das palavras do pedido valem também nas bases importadas (competências AAAAMM do ano ou, num período anual, o próprio ano); antes, "em 2024" ficava como recorte não reconhecido. **Correção:** o extremo sem valor na comparação com janela é lacuna (None), nunca NaN.
- **Permanece:** o Brasil (contagem nacional, BR-POP-JUNHO-1), os municípios (linhas, chaves e notas do caminho municipal), os grupos "Municípios de um estado" (expansão pelos códigos IBGE, com o 251365 na PB), níveis nunca somados entre si, a taxa nacional só de contexto, o mapa só de municípios, uploads sem abrangência; as fontes nacional e municipal e seus SHA-256; nenhuma fonte é somada a outra; nada da fonte estadual, das regras ou dos valores vai ao provedor de IA; "municípios de …" na conversa continua marcando municípios.
- **Motivo:** pedido do responsável pelo produto de 19/10/2026: integrar a contagem de médicos únicos por estado à base existente, com a regra metodológica de que o estado é a contagem única da planilha (nunca a soma dos municípios), o Brasil é a contagem nacional, a população do estado é a soma dos municípios na referência temporal, sem estimar, e a agregação interestadual não autoriza afirmar pessoas únicas no conjunto; as análises e a conversa existentes devem funcionar para estados. Classificação (regra 1): todos os itens decorrem do pedido e passam na compatibilidade com a SPEC: contagem de pessoas distintas no território vinda de fonte autorizada (CAP-IND-01; RQ-DAD-12), população incompleta com DENOMINADOR_AUSENTE, sem imputação nem exclusão (CAP-IND-02; DA-10; INV-04), agregação de estados como SOMA_DOS_COMPONENTES (CAP-AGR-01), recusa de "sem sobreposição" pela regra do responsável e pela coerência da premissa (DA-07: a soma dos estados supera o total do Brasil em todas as competências). Nenhuma divergência da SPEC; a SPEC não foi alterada.
- **Documentação e testes:** README (três fontes, abrangência, origem da base e conversor, limitações, política dos dados e testes reais), `Docs/ABRANGENCIA_TERRITORIAL.md` (princípios, matriz, regras do estado, análises, tela, API, conversa, chaves, residuais e testes), `Docs/DADOS_BRASIL_VALIDACAO.md` (fonte estadual: procedência, conversão, validação e limitações), `Docs/MODELO_TERRITORIAL.md`, `Docs/BLOCO3_MAPAS_VISUALIZACOES.md`, `Docs/EVOLUCAO_TEMPORAL_E_TENDENCIA.md`, `Docs/INTERFACE_CONVERSACIONAL_INTEGRADA.md`, `Docs/CONVERSACAO_INCREMENTO_FN.md` e `Docs/BLOCO2_ETAPA2_CRITERIOS_INTEGRACAO.md`; `AGENTS.md` (regra 2), a governança e `scripts/verificar_tudo.py` com o arquivo novo. Pytest: novo `test_build_state_source.py`; `test_territorial_levels.py` com fonte estadual sintética (contagem, população completa e incompleta, competência sem registro, divergência, agregação e recusas, evolução e comparação com lacunas, inspeção, fonte sem uma UF ou fora do perfil, conversa com estados, regiões e anos); `test_levels_real_data.py` (594 contagens e densidades contra leitura independente, Brasil ≤ Σ estados ≤ Σ municípios, ranking, agregações, tendências, regiões e as quatro perguntas do pedido com o cálculo); `test_brazil_catalog.py` (recorte `state` recusado), `test_brazil_source.py` (fonte estadual alterada recusada), `test_result_summary.py`, catálogos sintéticos com a fonte estadual (`catalog_support.write_state_source`) e arquivos reais escolhidos pelo nome; roteiros `ui_territorial_scope.py` e `ui_result_visuals.py`; `frontend/tests/visualModels.test.mjs`.

### 2026-10-19 · Comparação com janela, mudança e tendência por território; resultados com frase-resumo, indicadores, procedência e visual completo

- **Antes:** a comparação aceitava só uma competência na tela (`comparisons` fora dos vários períodos) e, sem competência escolhida, as relações saíam em cada competência do recorte; não havia mudança nem tendência por território, e o par de comparação aparecia com "Mapa indisponível" (as linhas só tinham "Valor A" e "Valor B"). Na conversa sobre o resultado, a relação de valores iguais sumia da resposta: o motor emite `IGUALDADE` e a conversa só reconhecia "IGUAL". O resultado mostrava, abaixo da descrição, uma grade genérica com as `metrics`; a API só tinha métricas na densidade, nos quantitativos e nos relatórios, e, na rota de níveis, "Unidades avaliáveis" e "Não avaliáveis" contavam só os municípios. A descrição da densidade era a frase solta "pessoas por 1.000 habitantes." (na rota de níveis, também). A "Situação do resultado" aparecia sem acentos ("avaliavel com limitacoes"), e a fonte de um arquivo importado, como "[object Object]". A distribuição somava no frontend as unidades das classes para o total ("N unidades territoriais avaliadas") e desenhava duas vezes o gráfico de contagens. O ranking usava barras; a agregação e a rotatividade não tinham visual próprio; a evolução temporal só tinha o gráfico de linhas; os cartões de destaque não diziam o nível, e o do estado dizia "profissionais". No mapa, a escala de cor era linear entre o mínimo e o máximo: com os 5.570 municípios (0,23 a 81,07 por 1.000 habitantes), quase todos os pontos ficavam claros. A taxa nacional aparecia só na legenda do mapa e nas barras dos municípios.
- **Agora:** **Comparação com janela (API, D6):** a opção nova `comparison_values_period` (a competência dos valores, dentro da janela de `period_filters` ou igual ao `period_filter`) faz as relações da CAP-CMP-01 usarem só essa competência, no formato de sempre em `rows` e com a cardinalidade do conjunto pedido (AT-84); `detail_rows` traz um registro por território com quantidade, população, densidade (só a quantidade no indicador quantidade), unidade ou tipo de contagem, cobertura e condição ("Não avaliável: sem registro na competência dos valores" quando falta) e, com duas ou mais competências, Período inicial e final, Inicial, Final, Variação absoluta, Direção e Condição da mudança, Tendência, Motivo e Observações da tendência, pela mesma `temporal_change.evolution` da evolução temporal, **sem "Variação (%)", razão ou diferença percentual automáticas**; `metadata.comparacao` (competência dos valores, janela, grupos por nível, objetos sem relação), `metadata.tendencia` e `metadata.mudanca`; notas da competência dos valores, da janela e "Classes de tendência lado a lado: entre territórios, só se lê se a classe é a mesma; as classes não têm ordem entre si."; a janela exige as premissas temporais da evolução (aplicadas pelo backend e conferidas no pré-exame) e a competência fora dela é recusada (422, "A competência dos valores precisa estar entre os períodos escolhidos para a comparação."). Na rota de níveis, as relações ficam dentro do mesmo nível, o Brasil lado a lado sem relação, o estado parcial fora das relações com o valor preservado no registro e o estado com suporte variável na janela sem tendência (INCOMPARABILIDADE pela entrada). **A chave de execução das comparações muda** quando a opção é enviada (ela entra em `options`, e `metodos.tendencia` com a janela); sem a opção, o caminho e a chave são os de antes. Com `detail_rows`, a representação usa `tabela = detail_rows` e a coordenada da competência dos valores: **o par passa a ter mapa**. **Na tela:** a comparação aceita vários períodos e, sem período escolhido, começa na **série anual de junho** (11 competências na base versionada) com os valores na última (06/2024); um período único já escolhido é mantido; a caixa "Competência dos valores" (`comparison-values-period`) troca a competência dentro da janela; a interface envia `comparison_values_period` (a competência única, a escolhida ou a última da janela; sem competência escolhida, não envia), e a conversa não recebe a opção. **Conversa:** a relação `IGUALDADE` vira "O valor de A é igual ao de B." (correção). **Frase-resumo, indicadores e procedência (D7):** `metadata.representacao.resumo` (`backend/result_summary.py`), composto só com cópias verificadas de caminhos do resultado (os mesmos verificadores da conversa), sem LEX-DES, LEX-NORM e LEX-CAU, LEX-CMP só nas relações do motor e LEX-TEN só com `metadata.tendencia`; a taxa nacional é "Referência de contexto: … não classifica nem colore os territórios.", nunca "acima" ou "abaixo"; até quatro KPIs (a taxa nacional, só na densidade e no relatório com densidade, como cartão de contexto com minigráfico) e a procedência (fonte e versão, fórmula, população do Brasil, tendência, níveis, tipo de contagem, chave de execução). Fica fora de `llm_context` e de `provider_snapshot`; uma falha ao compô-lo só deixa o resultado sem resumo. Na tela, o cabeçalho `result-header` (`result-summary`, `result-kpis`/`result-kpi`, `kpi-sparkline`, `result-provenance`) substitui a grade de métricas (resultados sem resumo mantêm a grade, `result-metrics`). **Métricas novas da API:** evolução temporal ("Séries territoriais", "Aumento entre os extremos", "Redução entre os extremos", "Sem mudança entre os extremos", "Mudança não avaliável"), comparações ("Territórios comparados" e, com a opção, "Competências na janela"), agregação ("Territórios agregados"), distribuição ("Unidades classificadas", "Classes" e, na rota de níveis, "Estados fora da distribuição"), ranking ("Territórios ordenados", "Não avaliáveis"; estado parcial conta como não avaliável), rotatividade ("Coortes avaliáveis", "Coortes não avaliáveis (sem registro em um dos períodos)") e relatório de quantidade ("Registros territoriais"); na rota de níveis, métricas por nível com a chave `nivel` ("Brasil (total nacional): registros avaliáveis", "Estados (soma dos municípios): …", "Municípios: …", avaliáveis e não avaliáveis). **Descrição:** "Densidade de {unidade} por 1.000 habitantes." e, na rota de níveis, "Densidade de pessoas por 1.000 habitantes por nível territorial (…), em blocos separados; nenhum nível é somado a outro." e "Quantitativos de pessoas por nível territorial (…)". **Série nacional:** `metadata.referencia_nacional.serie` e `representacao.referencias[].serie`, a taxa de todas as competências da fonte nacional (lacuna sem população de junho), só para o minigráfico. **Visual completo:** "Situação do resultado" com acentos ("avaliável com limitações") e a fonte importada pelo nome do arquivo; descrição com competências como mês/ano; níveis em blocos (`levels-panel` com `level-panel-br|uf|mun`; estado com textura, `uf-warning`, "na soma das contagens dos municípios" e "por 1.000 habitantes (soma dos municípios)", RQ-REP-14; separadores por estado nas barras dos municípios); comparação com valores lado a lado por nível (`comparison-panel`, `comparison-side-by-side`, `comparison-object`, `comparison-pair-relation` com a relação e a diferença do motor), halteres com o selo da tendência (`comparison-dumbbell`) e o bloco `comparison-card-extra` nos cartões da tabela; evolução temporal com pequenos múltiplos na mesma escala (`trend-small-multiples`, 12 por página) e halteres (`temporal-dumbbells`), além dos selos e da contagem por classe; ranking em pirulito (`ranking-lollipop`, posição do motor); distribuição **sem a soma do frontend** (total = métrica "Unidades classificadas", `distribution-total`, "N unidades territoriais classificadas (total do motor)"), sem o gráfico repetido e com a faixa de pontos por classe (`distribution-strip`); cartão da agregação (`aggregate-card`, tipo de contagem como selo, membros e ausentes); barras da coorte da rotatividade (`rotation-cohort-bars`); taxa nacional também no cartão de contexto, na dica do ponto, no detalhe do território (`detail-national-reference`) e como linha tracejada nas séries de densidade (K10: nunca em ranking, distribuição, comparação ou agregação, nunca no painel dos estados); Brasil marcado tracejado nas séries. **Escala de cor do mapa:** contínua e **logarítmica por padrão** quando todos os valores são positivos (posição = ln(valor ÷ mínimo) ÷ ln(máximo ÷ mínimo)); linear à escolha ("Escala de cor do mapa": Logarítmica | Linear) ou com zero e negativos; domínio [mínimo, máximo]; extremos (`legend-extreme`) e marcas de leitura 1, 2 e 5 × 10ⁿ (`legend-tick`) na legenda, com o texto `legend-scale`; `__adtMapModel.scale` e `representacao_aplicada.escala` (`tipo`, `transformacao`, `escolha`, `dominio`, `classificacao: false`). Nenhuma classe, quebra ou quantil criada na tela. **Revisão visual do fim do bloco:** na frase-resumo do par, a "Diferença A − B" leva a unidade ("… −3,67 por 1.000 habitantes."); os cartões de indicadores não se esticam à altura do maior; a legenda escreve as marcas sem zeros à direita (0,5) e, com um só valor, diz "Um só valor no resultado: a cor fica no meio da rampa; a cor não é classe nem limiar." sem a escolha da escala; nomes de pontos próximos no mapa não se sobrepõem nem cobrem outros pontos, os botões e as coordenadas da borda (só o texto muda de lugar); as barras com eixo (até 40) trazem o valor do motor no fim, e o número das barras com rolagem tem fundo opaco sobre a linha da taxa nacional; os valores lado a lado da comparação dizem a unidade; nos cartões da comparação, cada formato de linha mostra só as suas colunas (o Brasil e os municípios deixam de listar "Relação A/B: Não avaliável", o maior do nível e o Brasil, "Próximo valor maior: Não avaliável", e o resumo do par, "Território: Não avaliável"; tabela, CSV e filtros sem mudança); no pirulito, vizinhos que o arredondamento igualaria ganham as casas que os distinguem (RQ-REP-05); a faixa da distribuição é desenhada na largura do contêiner e, com valores positivos, num eixo logarítmico com extremos e marcas 1, 2 e 5 × 10ⁿ (antes, os quatro primeiros quintis ficavam espremidos junto ao mínimo); abaixo de 640 px, as barras com rolagem, as listas de valores, os halteres e o pirulito põem o nome numa linha própria, inteiro; os selos da contagem por classe da tendência mostram o rótulo inteiro (antes, "Sem classificação (mudança de …").
- **Permanece:** sem `comparison_values_period`, as `rows` e a chave da comparação são as de antes (`test_audit_integrity.py:143-173` sem mudança); `rows` continua sendo a tabela principal da comparação (`comparison-territory-row`, `comparison-pair-summary`, "Valor integral" uma vez por cartão); a evolução temporal continua com todas as competências por padrão; nada é calculado na tela além do desenho (totais, contagens, classes, diferenças, relações, variações e frases vêm do motor); a taxa nacional continua só de contexto e calculada no backend, fora de `metrics`, ranking, distribuição, comparação e agregação; estados continuam "soma dos municípios", nunca comparados com o Brasil; contratos de teste (`result-title`, `result-status`, `result-highlights` com um `article` por linha, `change-delta`, "Territórios das séries", "Quantas unidades pertencem a cada quintil?", "Territórios por grupo da distribuição", `#tabela-resultado .data-table tbody tr`, `__adtMapModel.fills` nulo só para valor nulo, legenda com mínimo e máximo, `national-reference`, `bars-reference-line`, `level-panel-*`); CSV, JSON e impressão; nada da base, do resumo, da tendência, da abrangência, da comparação ou da taxa nacional vai ao provedor de IA; dados, manifesto, SPEC e `ci.yml`; nenhuma dependência nova no frontend.
- **Motivo:** decisões do responsável pelo produto de 19/10/2026: D6 (comparação com janela, mudança e tendência por território, padrão na série anual de junho) e D7 (cabeçalho com frase-resumo, indicadores e procedência; visual completo dos resultados, nada para depois, ajustes da mesma data); pendências das prévias do Bloco B (métricas que contavam só municípios num resultado com níveis, a frase solta "pessoas por 1.000 habitantes.", a situação sem acentos, o mapa quase todo claro e o par com "Mapa indisponível"); defeito do chat com `IGUALDADE`; a soma do frontend na distribuição (pendência do Bloco 3, RQ-REP-08). **Divergências da SPEC: nenhuma nova.** A escala logarítmica é transformação formal contínua da apresentação (RQ-REP-02: "Escala visual contínua é transformação formal e não constitui classificação"), não muda a escala do indicador (RQ-REP-11) e depende só do sinal dos valores e da escolha do usuário.
- **Documentação e testes:** README (comparação com competência dos valores, taxa nacional, evolução e Bloco 3), `Docs/BLOCO3_MAPAS_VISUALIZACOES.md` (contrato com `resumo`, escala de cor, mapa do par, gráficos, cabeçalho, acessibilidade, testes, RQ-REP-14 e a pendência da soma da distribuição resolvida), `Docs/EVOLUCAO_TEMPORAL_E_TENDENCIA.md` (pequenos múltiplos e halteres; seção nova da comparação com janela, com o exemplo real), `Docs/ABRANGENCIA_TERRITORIAL.md` (métricas e descrição por nível, comparações com janela por nível, série nacional, visual dos níveis, chave e privacidade) e `Docs/INTERFACE_CONVERSACIONAL_INTEGRADA.md` (vários períodos na comparação, caixa "Competência dos valores", padrão de junho, a conversa sem a opção e a correção da IGUALDADE). Pytest novos: `test_comparison_window.py`, `test_result_summary.py` (todo segmento verificado, léxico, taxa como contexto, níveis, nada ao provedor, falha controlada), casos novos em `test_territorial_levels.py`, `test_representation.py` (mapa do par DISPONIVEL) e `test_result_conversation.py` (IGUALDADE) e, com dados reais, em `test_levels_real_data.py` (série anual de junho com valores em 06/2024: Brasil 2,3638 em Crescimento com 11 observações, SP 5,2032 em Crescimento, RS não comparável, AM, Manaus, Tefé e Parintins sem classificação, desfecho RES-LIM; resumo e série nacional). Teste mudado de propósito: `test_audit_integrity.py::test_a08_declared_unit_in_aggregate_label_density_description_and_notes` (a descrição esperada passa a "Densidade de {unidade} por 1.000 habitantes."; o defeito não está no produto nem no teste: o comportamento mudou de propósito por D7, fim da frase solta, e a unidade declarada continua conferida). Node novos: `headerModel.test.mjs` e `visualModels.test.mjs`; casos novos em `periods.test.mjs` (competência dos valores e janela padrão) e `investigation.test.mjs` (situação com acentos e fonte importada). Roteiro novo `ui_result_visuals.py` nas suítes `bloco1` e `base-versionada`. Nenhum teste enfraquecido, pulado ou apagado.

### 2026-10-19 · CI como único ambiente de verificação e classificação das mudanças por escopo e compatibilidade com a SPEC

- **Antes:** a seção 4 do `AGENTS.md` pedia, antes de cada push, a verificação local proporcional à mudança: os testes dos módulos alterados, o build do frontend, os roteiros de navegador afetados, a governança e, quando a mudança tocava o motor, a API ou os dados, os testes com dados reais. A regra 1 não dizia como classificar a mudança antes de codar nem quando consultar a SPEC.
- **Agora:** o CI é o único ambiente de verificação. Antes do push rodam só checagens de segundos: `py_compile` do Python alterado, `tsc --noEmit` quando `frontend/node_modules` já existe e, depois do commit, a governança. Suíte pytest, testes com dados reais, roteiros de navegador, `npm run build`, `scripts/verificar_tudo.py` e capturas de tela só rodam localmente por pedido explícito do responsável; a única exceção é rodar o teste que falhou no CI quando o log não explica a falha. Os testes do comportamento alterado continuam no mesmo commit, sem execução local. Antes de codar, cada item do pedido é classificado pela leitura, todos de uma vez. Sem mudança de comportamento, o agente segue para o código sem consultar a SPEC. Com mudança, ele lê a SPEC e as divergências aprovadas e aplica dois testes, numa leitura não literal: escopo (a mudança decorre do pedido ou do item da SPEC em implementação) e compatibilidade (não contraria a SPEC nem uma divergência aprovada). Se falhar em um deles, mesmo num pedido do responsável, o agente para antes de implementar e o consulta, juntando as dúvidas do lote; aprovada, a mudança entra no registro, como divergência aprovada quando contrariar a SPEC. Vale também para mudanças que surgem durante a implementação ou na correção de uma falha do CI. Implementar um item da SPEC também é mudança de comportamento e vai para o registro. A correção do CI tem no máximo 3 rodadas para a mesma falha; uma falha sem relação com a mudança é reexecutada uma vez e, se persistir, relatada ao responsável.
- **Permanece:** o CI roda todos os jobs em todo push, e o trabalho só termina com o CI em PASS em todos os jobs obrigatórios; nenhum job do CI foi alterado. O registro no mesmo commit (regra 1), a integridade e a ordem de atualização da base (regra 2), as regras de testes (regra 3) e a SPEC não mudam. Nenhum comportamento do produto muda.
- **Motivo:** decisão do responsável pelo produto (19/10/2026): as tarefas chegavam a durar cerca de 10 horas com verificações locais que o CI refaz em todo push. O CI passa a ser o único ambiente de verificação; a SPEC só é consultada quando há mudança de comportamento, e o que falha nos testes de escopo ou compatibilidade volta ao responsável antes de virar código. **Substitui** a entrada "Verificação local proporcional ao risco e ao alcance da mudança" (18/10/2026).
- **Documentação e testes:** `AGENTS.md` (regras 1 a 5 e mapa rápido), README (seção Testes) e descrição de `scripts/verificar_tudo.py`. O `CLAUDE.md` continua só importando o `AGENTS.md`. Regra de processo, sem teste do produto.

### 2026-10-19 · Abrangência territorial em lista vertical com Brasil, estados e municípios; taxa nacional no mapa e nas barras; análise espacial com competência e coordenada inválida só no território

- **Antes:** na base oficial, a caixa "Abrangência territorial" oferecia só em quantitativos, evolução temporal e relatórios a escolha por rádios entre "Brasil (total nacional)" e "Municípios"; nas demais análises, informava "Esta análise usa somente a fonte municipal; o total nacional está disponível em Quantitativos, Evolução temporal e Relatórios.". A lista de municípios era uma pesquisa por nome ou código ("Pesquisar por nome ou código", "Estado derivado do código", "Adicionar todas as correspondências válidas"). Trocar de análise ou de abrangência recarregava a base no outro recorte (`/api/inspect`), com a preparação bloqueada ("Carregando o total nacional…"), memória da preparação de cada recorte e a opção "Abrangência da análise" nas condições avançadas; marcar municípios com o total nacional levava a análise ao recorte municipal. Estados não eram selecionáveis; no total nacional, "Densidade por 1.000 habitantes (somente municípios)" aparecia indisponível. A taxa nacional da API não aparecia na tela. Nas barras com rolagem (mais de 40 territórios), o número de cada barra ficava no começo da faixa, por cima da barra. Na análise espacial, a caixa Período informava "Não se aplica" e a análise usava todas as competências; uma coordenada ausente ou fora dos intervalos recusava o pedido inteiro ("Coordenadas ausentes ou fora dos intervalos geográficos válidos."), também nas bases importadas, e coordenadas diferentes entre competências davam "Coordenadas conflitantes para o mesmo território. Verifique o identificador ou selecione um período consistente.". Com estados e municípios misturados, ou territórios de menos, o `/api/preflight` com abrangência era recusado (422).
- **Agora:** a base oficial é examinada uma vez, no recorte municipal, com o bloco `niveis`; trocar de análise não chama `/api/inspect` nem troca de fonte. A caixa "Abrangência territorial" é uma lista vertical com caixas de marcar nativas (`TerritorialScopeSelector.tsx`, região "Seleção territorial compartilhada"): **Brasil** ("Brasil (total nacional)", "Total da fonte nacional; não é a soma dos municípios."), **Estados** (selo "soma dos municípios", o aviso "Cada estado é a soma dos seus municípios: o mesmo médico pode ser contado em mais de um município. Por isso, o valor do estado não é o número de médicos diferentes e a soma dos estados não é o total do Brasil.", "Todos os estados (N)" e cada estado com "soma de N municípios") e **Municípios** ("Todos os municípios" e um grupo recolhível por estado, com a caixa do grupo, "k de N municípios" e os municípios dentro; sem estados identificados pelos códigos, uma lista simples). Ao lado: "{n} selecionados", a composição ("Brasil · 1 estado · 1 município") ou "Padrão desta análise: …", a escolha pendente e "Limpar seleção". Sem nada marcado vale o padrão da análise, com o selo "padrão desta análise" e a caixa desmarcada (Brasil em quantitativos, evolução temporal e relatórios; todos os municípios nas demais); a primeira marcação substitui o padrão. Os municípios marcados continuam valendo entre as análises (a conversa, "Usar seleção na próxima análise", "Usar os que atendem…" e "Usar como municípios-alvo" substituem a seleção pelos municípios; a transferência de um resultado com níveis devolve o Brasil e os estados como tais); o Brasil e os estados só valem nas análises que os aceitam, e nas demais a seção fica desabilitada com o motivo em uma linha. Resumo da caixa na ordem Brasil → estados → municípios ("Brasil (total nacional), Amazonas (estado) e MANAUS (AM)", "Amazonas e Pará (estados)", "Municípios do Amazonas (62)"). A interface envia `options.abrangencia` (só a parte que vale na análise, ou o padrão dela; a rotatividade segue sem) e manda a análise no pré-exame; a conversa continua recebendo só os municípios marcados. Um pedido explícito pelo país inteiro marca só o Brasil; "nos municípios", sem municípios marcados, marca "Todos os municípios". A densidade do Brasil fica disponível no Indicador. **API:** o `/api/preflight` com abrangência e escolha pendente (estados e municípios juntos na distribuição ou no ranking, ou territórios de menos) devolve o pré-exame da fonte municipal com a análise em escolha pendente, o motivo em `reasons` e em `capabilities[op].niveis.selecao`, e `abrangencia_pendente`; a tela mostra o motivo (`territory-rule-message`), destaca a caixa, diz "Ajuste a abrangência territorial para continuar." e bloqueia o cálculo; o `/api/analyze` continua recusando com o mesmo texto. **Taxa nacional na tela (D5):** na densidade de uma competência, a legenda do mapa traz uma marca tracejada sobre a escala e "Brasil (total nacional): 2,36 por 1.000 habitantes · referência de contexto; a cor dos municípios não é classificada em relação a ela." (`national-reference`; "(fora da escala dos municípios)" quando cabe; em janeiro, a nota da população de junho), sem mudar cores nem o domínio (gancho de teste `__adtMapModel.reference`); as barras dos municípios ganham a linha tracejada "Brasil 2,36" e a legenda "… referência de contexto; a linha não classifica os municípios." (`bars-reference-line`), também na janela com rolagem; nessa janela, o número de cada barra passa a ficar logo depois do fim dela (perto da borda direita, dentro da barra), num fundo claro por cima da linha tracejada, para que nem a barra nem a linha o cubram. Com níveis, municípios e estados ficam em figuras de barras separadas (`level-panel-mun`, `level-panel-uf`) e a série, um gráfico por painel (`level-panel-{id}`); nunca há barra do Brasil entre municípios. **Análise espacial:** a caixa Período pede uma competência ("Escolher período"), com a nota "As distâncias usam as coordenadas da competência escolhida; em algumas competências, a fonte traz coordenadas diferentes para o mesmo município."; os motivos do pré-exame dessa análise aparecem abaixo das caixas (`spatial-reasons`). Coordenada ausente, não numérica ou fora dos intervalos deixa só aquele território não avaliável (RQ-DAD-25): distância vazia, nunca zero, "Condição" "Não avaliável: coordenada inválida" ou "… ausente" (coluna presente só nesse caso), no fim da ordem, fora do mapa, com a nota "{n} território(s) sem coordenada válida no recorte ficam não avaliáveis (COORDENADA_INVALIDA), sem distância e fora do mapa; os demais foram calculados." e o resultado avaliável com limitações; vale na base oficial (depois da camada complementar) e nas importadas. Referência sem coordenada válida: "O território de referência não tem coordenada válida na competência escolhida. Escolha outro território de referência.". Coordenadas válidas diferentes entre competências: "Coordenadas conflitantes para o mesmo território entre competências. Escolha uma competência no período da análise." (escolha pendente); na mesma competência, "… na mesma competência. Verifique o identificador territorial.". As chaves de execução da base oficial passam a levar a abrangência (os municípios marcados em ordem de código): mudam de propósito; `options.territory_ids` dos resultados passa a vir na ordem do código.
- **Permanece:** cálculos, rotas e regras do backend da entrada anterior (BR-POP-JUNHO-1, estados pelo prefixo IBGE, níveis nunca somados, taxa nacional só de contexto e calculada no backend); nada é calculado na tela; os uploads e a "Seleção de referências" com a seleção por pesquisa; a escolha de períodos entre análises de mesmo modo; a vírgula decimal com o ponto escolhido como erro de formato; a referência mais próxima e os critérios com a regra por elemento que já tinham; dados, manifesto e SPEC. Na base Brasil sem o perfil oficial, a escolha entre o total nacional e os municípios continua no texto da preparação.
- **Motivo:** decisões do responsável pelo produto de 19/10/2026: D3 (abrangência vertical Brasil/estados/todos os municípios/municípios), D5 (taxa nacional como referência de contexto, na legenda e nas barras) e os ajustes da mesma data (lista enxuta: sem filtro de texto, sem foco único com busca por letra e sem itens "fora desta análise"; municípios marcados valem entre análises; Brasil e estados só onde são aceitos). **Substitui** as decisões das entradas "Preparação: abrangência, resumo visual e intervalo de períodos" (18/10: escolha por rádios em três análises, recarga ao trocar de recorte, "Abrangência da análise" nas condições avançadas e memória da preparação de cada recorte) e "Preparação em abas com contorno e configurações em caixas seletoras" (19/10, `deb3882`: rádios Brasil/Municípios, consulta da lista municipal ao abrir a caixa, densidade indisponível no total nacional) e a parte da análise espacial da entrada "As quatro caixas das configurações em todas as análises" (Período "Não se aplica"). **Não é divergência da SPEC:** a validade por elemento segue a RQ-DAD-25 (L1386; a divergência registrada na entrada "Sem confirmações…" continua só na parte "requer confirmação do usuário").
- **Documentação e testes:** README (duas formas de carregar dados, ponte semântica, chat, validação da base e limitações), `Docs/ABRANGENCIA_TERRITORIAL.md` (tela, taxa nacional na tela, pré-exame com escolha pendente e análise espacial), guia da interface, preparação guiada, validação da base Brasil e Bloco 3. Pytest novos: `test_spatial_por_territorio.py` (território inválido, não numérico ou ausente não avaliável; referência inválida; coordenadas entre competências; formato) e, em `test_territorial_levels.py`, o pré-exame com escolha pendente. Testes mudados de propósito (o defeito não está no produto nem no teste; o comportamento mudou por D3, D5 e RQ-DAD-25): `test_semantic_bridge.py::test_out_of_range_coordinate_does_not_demote_the_column` (referência inválida recusada com o motivo novo; outra referência fica disponível), `test_geo_complement.py::test_existing_spatial_analysis_uses_the_layer_with_traceability` (sem a camada, 200 com os territórios inválidos não avaliáveis em vez de 422) e, com dados reais, `test_real_data.py::test_real_resident_spatial_comma_and_coordinate_changes` (sem a camada, junho de 2024 dá 200 com os seis municípios não avaliáveis e as mesmas distâncias do subconjunto válido; todas as competências pedem uma competência) e o fim de `test_real_resident_spatial_with_the_official_layer` (upload sem complemento: 200 com os seis não avaliáveis em vez de 422). Node: `territorialScope.test.mjs` reescrito (o que vale em cada análise, padrão, marcar e desmarcar, grupos, contagem, resumo, transferência e competências; os cinco resumos de antes continuam) e `representation.test.mjs` ampliado (taxa nacional e nível dos itens). Roteiro novo `ui_territorial_scope.py` nas suítes `bloco1` e `base-versionada` (lista, espacial com competência, Brasil + estado + município na densidade, taxa nacional na legenda e nas barras sem mudar o domínio, ranking só de estados, escolha pendente, "Limpar seleção", conversa sem abrangência, nenhum `/api/inspect` ao trocar de análise, 390 e 768 px; na base versionada, 27 estados, MG com 853 municípios, "2,36 por 1.000 habitantes" e, nas barras com rolagem dos 5.570 municípios, o número de cada barra fora da borda dela e por cima da linha da referência). Roteiros mudados de propósito: `ui_stabilization.py` (rádios → caixas de marcar com selo de padrão; densidade do Brasil disponível; nenhum `/api/inspect` ao trocar de análise; espacial "Escolher período"), `ui_conversational_smoke.py` (caixas de marcar, base sem estados, `options.abrangencia` e a rota municipal; os valores do município B continuam), `ui_criteria_smoke.py` (Brasil marcado fica desabilitado com o motivo nos critérios, sem troca de fonte), `ui_block1_smoke.py` (municípios marcados no grupo do estado; teclado no botão do grupo e na caixa; `territory_ids` na ordem do código, com a abrangência; espacial com a competência), `ui_investigation.py` (lista bloqueada durante o cálculo pela caixa "Todos os municípios"; o reenvio pela API repete o pedido com a abrangência, sem os municípios derivados) e `ui_sem_confirmacoes.py` (município marcado no grupo); `ui_support.py` ganha `municipality()`; `scripts/capturar_telas.py` abre o grupo do Amazonas. Nenhuma verificação foi removida.

### 2026-10-19 · Brasil, estados e municípios como níveis da base oficial; população nacional de junho e taxa nacional de referência (API)

- **Antes:** a API só conhecia a fonte nacional (`scope=national`, sem população e sem densidade) e a municipal; não havia estado como objeto de análise, nem densidade do Brasil, nem "Todos os municípios" ou "Municípios de um estado" como escolha. Grupos de municípios eram listas de códigos montadas na tela, e um membro sem registro no recorte derrubava o pedido inteiro. O 251365, com a coluna `uf` divergente na fonte (PA em 2016/6), ficava bloqueado para seleção também na base oficial, e "municípios da Paraíba" na conversa trazia 222 municípios. A densidade da base oficial não trazia nenhuma referência nacional. A descrição da base dizia "recortes do país e dos municípios" e "Os resultados nacionais e municipais são fontes do mesmo catálogo, mas não são somados automaticamente entre si.". A dúvida estado/município homônimo na conversa terminava com "Selecione os municípios na pesquisa territorial ou pelo filtro de estado.".
- **Agora:** contrato novo `options.abrangencia` = `{brasil, estados, municipios: {todos, estados, ids}}` em `/api/analyze` e `/api/preflight` (`dataset=brazil`, `scope=auto` ou `municipal`), com erros em português (upload, junto de `territory_ids`, `scope=national`, nada marcado, estado não reconhecido, identificadores repetidos, nível fora da análise, mistura e mínimo conferidos no backend) e absorções explícitas (`metadata.selecao_territorial.absorvidos`). Roteamento (`backend/territorial_levels.py`): só municípios (ou estados na agregação) seguem o caminho municipal, com os grupos expandidos nos municípios presentes depois dos filtros e nota de cobertura; só o Brasil em quantitativos (ou na evolução e no relatório por quantidade) segue o caminho nacional; o resto vai para a rota de níveis, que calcula cada universo pelo mesmo motor (`_compute` com o quadro já preparado e `evolution`) e apresenta Brasil → estados → municípios em blocos, com as colunas "Nível", "Tipo de contagem", "Cobertura", "Competência da população" e "Condição", sem nunca somar um nível a outro. **Regra BR-POP-JUNHO-1 (D4):** população do Brasil = soma da população estimada dos municípios em junho do ano, uma vez por município, usada em janeiro e junho (jun/2024 = 212.583.750; densidade 502.495 ÷ 212.583.750 × 1.000 = 2,3638); em 2015 falta o 430607 em junho, e a população soma os 5.569 municípios com registro, avaliável com limitações (`POPULACAO_NACIONAL_PARCIAL`), com a nota "Em junho de 2015, a base municipal não tem registro de 1 município (CRISTAL DO SUL, RS, 430607); a população do Brasil desse ano soma os 5.569 municípios com registro."; a série nacional continua comparável (22 observações na série completa e 11 na de junho, ambas Crescimento); ano sem junho fica não avaliável (`SEM_COMPETENCIA_DE_JUNHO`), lacuna e nunca zero; numa série de vários anos, a nota de procedência diz "dos {N} municípios em junho de cada ano" só quando todos os anos somam o mesmo número de municípios, e "dos municípios com registro em junho de cada ano" quando algum ano é parcial (como a série que inclui 2015). **Estados:** soma dos municípios pelo prefixo do código IBGE (regra `brasil-cod-uf-prefix-1`, não a coluna `uf`), "Soma dos componentes (possível dupla contagem)", com `metadata.suporte_agregado` e AGREGADO_PARCIAL quando falta membro; ranking e distribuição só entre estados, com o parcial fora da ordem; na evolução, estado com municípios presentes diferentes na janela fica com a tendência não comparável (INCOMPARABILIDADE pela entrada de `evolution`, que ganha `change_incomparable` para a mudança entre extremos com membros diferentes) e entra em `serie.quebras`. **Comparações:** relações só dentro do mesmo nível; Brasil e objetos isolados lado a lado. Notas novas (procedência do Brasil, janeiro com outro nível, estados com dupla contagem, ordem dos estados, agregado parcial, níveis separados e `UF_DECLARADA_DIVERGENTE`) e limitações em `metadata.evaluability.limitacoes`. **Taxa nacional (D5):** `metadata.referencia_nacional` e `metadata.representacao.referencias` em toda densidade e todo relatório com densidade da base oficial com municípios, **inclusive pela rota antiga, sem abrangência**, como referência de contexto que não classifica nem colore os municípios; falha vira `{"estado": "INDISPONIVEL"}` sem derrubar a análise. `/api/inspect` da base oficial no recorte municipal ganha o bloco `niveis` (estados com `rotulo_grupo`, Brasil, matriz por análise com textos e motivos); `/api/preflight` com abrangência devolve `capabilities[op].niveis`. A representação desenha só municípios no mapa ("Mapa não aplicável: Brasil e estados são agregados sem ponto; marque municípios para ver o mapa.") e declara `niveis` e `serie.paineis`. **251365:** na base oficial, selecionável como PB pelo prefixo, com `hierarchy_note`; toda opção territorial ganha `state_code`; a Paraíba passa a 223 municípios na conversa. Chaves de execução: `metodos` ganha `populacao_nacional`, `niveis` e `estado` quando usados e `options` guarda a abrangência normalizada, o que **muda de propósito as chaves das densidades e dos relatórios com densidade da base oficial** e as da rota de níveis. Textos: a descrição da base passa a "em recortes do país, dos estados e dos municípios" e "O total do Brasil vem da fonte nacional; a densidade do Brasil usa a população municipal de junho (regra governada); estados são somas dos municípios. As fontes não são somadas entre si."; a dúvida estado/município homônimo termina com "Marque os municípios na abrangência territorial.".
- **Permanece:** a interface não envia abrangência (a lista vertical é a entrada seguinte), então as telas e os resultados atuais continuam iguais, exceto o 251365 selecionável como PB, a descrição da base e a frase da conversa acima; `scope=national` continua sem densidade (422); `DEFAULT_SCOPES`; os pedidos sem abrangência dão as mesmas linhas, notas e métricas; o total nacional nunca vem da soma municipal; uploads continuam bloqueando a unidade com hierarquia divergente e não recebem abrangência nem referência nacional; as chaves das demais análises; dados, manifesto e SPEC. Refatoração preparatória no mesmo commit, sem efeito próprio: `main._finish` (metadados, notas e representação extraídos de `compute`), `_compute(..., prepared=)` e `brazil_data.load_brazil_sources` (as duas fontes numa leitura verificada).
- **Motivo:** decisões do responsável pelo produto de 19/10/2026: D3 (abrangência vertical Brasil/estados/todos os municípios/municípios), D4 (população do Brasil pela soma municipal de junho, com o ajuste de 2015: soma parcial com nota, no lugar de não avaliável) e D5 (taxa nacional como referência de contexto na densidade). **Não são divergências da SPEC:** BR-POP-JUNHO-1 é regra autorizada da CAP-IND-02 (L1742), com DENOMINADOR_ALTERNATIVO; `brasil-cod-uf-prefix-1` é a correspondência autorizada para a soma por estado (CFG-TER L968; RQ-DAD-12 L1349), sempre SOMA_DOS_COMPONENTES (L1747, L1751); NIVEIS-BR-UF-MUN-1 segue a RQ-DAD-30 (L1394); nada é imputado. **Divergência da SPEC decidida pelo responsável (D4, ajuste de 2015):** a SPEC pede NAO_AVALIAVEL com DENOMINADOR_AUSENTE quando falta a população e não admite tratar a ausência por exclusão (CAP-IND-02 L1742; DA-10 L2838; INV-04 L292; AT-08 L2252), e a densidade parcial que ela autoriza exige numerador e denominador no mesmo suporte (CAP-AGR-01 L1751); no Brasil de 2015, o 430607 fica fora do denominador e o numerador continua sendo a contagem nacional inteira. Por decisão do responsável, o valor é avaliável com limitações (`POPULACAO_NACIONAL_PARCIAL`), com a nota e a lista dos ausentes; a divergência também está no README, e a SPEC não foi alterada.
- **Documentação e testes:** novo `Docs/ABRANGENCIA_TERRITORIAL.md`; README (base Brasil, limitações das fontes e "seleção territorial avançada" parcialmente atendida), validação da base Brasil (fontes, regras governadas e capacidades), modelo territorial, Bloco 1 (251365) e Bloco 3 (contrato `niveis`, `referencias`, `paineis` e mapa só de municípios). Pytest novos: `test_territorial_levels.py` (31 casos sintéticos: contrato e erros, absorções, roteamento e paridade, matriz das 12 análises, BR-POP-JUNHO-1, Brasil, estados e 251365, blocos sem soma, ranking, distribuição, comparações, evolução com INCOMPARABILIDADE e lacuna, `change_incomparable`, agregação, análises de distância, D5 nas rotas antiga e nova e com falha controlada, chaves, inspeção e pré-exame, conversa e provedor sem níveis, representação) e `test_levels_real_data.py` (7 casos com a base versionada, SHA-256 conferido antes e depois: as 22 densidades do Brasil contra leitura independente, 2015 com [430607], taxa nacional nas duas rotas, Σ estados = Σ municípios e Brasil menor que a soma municipal, os seis agregados parciais, ranking dos estados, agregação de todos os municípios, 251365 na PB com 223 municípios, análise espacial com todos os municípios e as âncoras da tendência). `bench_latency.py` ganha o perfil da rota de níveis (fora do CI). Nenhum teste existente foi alterado, pulado ou removido.

### 2026-10-19 · Evolução temporal com a tendência da SPEC (CAP-TEN-01) e a direção da mudança

- **Antes:** a coluna Tendência da evolução temporal tinha quatro rótulos calculados em float ("Estável", "Mudança de direção", "Crescimento", "Declínio") ou "Não avaliável (< 4 observações)", sem aceleração nem desaceleração, sem motivo e sem o número de observações; a densidade entrava na classificação em float. Não havia direção da mudança; com o valor inicial zero, a Variação (%) ficava vazia e a condição continuava "Avaliável". Com menos de quatro competências não havia bloqueio da etapa. Os cartões mostravam "Tendência do motor: <texto>"; não havia contagem por classe, filtro por família, velocidades nem atalho de série anual. A representação da evolução não declarava indicadores, e a série não tinha `quebras`.
- **Agora:** a tendência segue CAP-TEN-01 (DA-15) em aritmética exata (`backend/trend.py`, `backend/temporal_change.py`): sete classes (Crescimento, Aceleração do crescimento, Desaceleração do crescimento, Declínio, Aceleração do declínio, Desaceleração do declínio, Sem classificação), "Não avaliável: série insuficiente" e "Não avaliável: série não comparável", com as colunas novas "Motivo da tendência" (Mudança de direção, Série estável, "N de 4 observações necessárias" ou o componente divergente; com a classe atribuída não há motivo: vazio no CSV e "Não se aplica" na tabela da tela, nunca "Não avaliável") e "Observações da tendência". A densidade é recalculada exata (quantidade × 1.000 / população); velocidades por mês (AAAAMM), dia (datas) ou unidade do período, sem imputar ausências. A coluna "Direção da mudança" (Aumento, Redução, Sem mudança, por igualdade exata, CAP-TMP-01) entra antes de "Condição da mudança", que ganha "Avaliável; variação percentual não avaliável: base zero" (BASE_ZERO). Com menos de quatro competências, a etapa recebe BLQ-MET com os textos do catálogo ("Não foi possível analisar a tendência porque há apenas {quantidade} observações válidas." e "A análise de tendência exige quatro observações válidas."), e a mudança continua disponível. Contrato novo da API: `metadata.tendencia` (desfecho RES-VAL, RES-LIM, RES-SCL ou BLQ-MET; bloqueio; contagens por classe, motivo e família; janela com intervalos e série anual; velocidades em float por unidade), `metadata.mudanca` (direções, extremos ausentes e base zero) e `metadata.metodos` (`{"tendencia": "CAP-TEN-01/DA-15/1"}`), que também entra na chave de execução da evolução temporal — a chave dessa análise muda; as demais não. A representação declara Tendência (CLASSE, CAP-TEN-01), Direção da mudança (ESTADO, CAP-TMP-01), Variação absoluta e Variação percentual (CONTINUO), e toda série ganha `quebras` (unidades sem trajetória, desenhadas só como pontos). Notas novas: o método da tendência, o bloqueio, os intervalos desiguais ("As competências desta série estão separadas por 5 e 7 meses; …") e a base zero; a descrição passa a "…; tendência (CAP-TEN-01) somente com quatro ou mais observações válidas.". Na tela: selo da classe (`trend-badge`, com `data-class`) nos cartões, na tabela e no detalhe; motivo, número de observações e minigráfico das velocidades (`trend-velocities`); contagem por classe na ordem da SPEC em Gráficos (`trend-counts`), com os não avaliáveis à parte; filtro por família (`trend-family-filter`); aviso da etapa (`trend-stage-note`) com o BLQ-MET ou o RES-SCL; atalho "Série anual (junho) · N competências" na caixa Período (`period-annual-june`), com o resumo "série anual de junho: …" e, na evolução da base oficial, um texto explicativo; no resultado, o botão "Usar a série anual (junho)", que só leva as competências de junho à caixa Período.
- **Permanece:** Inicial, Final, Variação absoluta e Variação (%) em float, com a mesma aritmética e os mesmos valores; `detail_rows`; o CSV com o texto do motor; o padrão "todas as competências" da evolução temporal; o mapa não aplicável; a regra de avaliabilidade do resultado (Sem classificação e a base zero não viram limitação); nenhuma classificação pela IA e nada da tendência no contexto enviado ao provedor (`provider_snapshot`); dados, manifesto e SPEC. Na base real, as classes conferidas: série completa em quantidade com 53 Crescimento, 5 Declínio, 5.505 Sem classificação (mudança de direção) e 7 (série estável); série anual de junho com 276, 19, 5.257 e 18; Brasil (contagem nacional) Crescimento.
- **Motivo:** decisão do responsável pelo produto (19/10/2026, D6): comparação e evolução com a tendência CAP-TEN-01 da SPEC. Esta entrada cobre a evolução temporal; a comparação com janela e os níveis Brasil e estados vêm nas entradas seguintes. **Não é divergência da SPEC:** implementa CAP-TEN-01 (DA-15, L1767-1776), CAP-TMP-01 (DA-14, L1765) e os enums `CategoriaTendencia` (L415) e `MotivoSemClassificacao` (L390).
- **Documentação e testes:** novo `Docs/EVOLUCAO_TEMPORAL_E_TENDENCIA.md`; README (seção nova, Bloco 3 e limitações: sai "todas as subclasses de tendência"), Bloco 1, Bloco 3, guia da interface, validação da base Brasil e notas datadas nos relatórios de 16/10/2026 (`REAVALIACAO_INCREMENTO_CONVERSACIONAL_20261016.md`, `DECISAO_CATALOGO_PT_20261016.md`, `EVOLUCAO_CONVERSACIONAL_20261016.md` em `Docs/` e na raiz). Pytest novo `test_trend.py` (AT-53, AT-09, AT-10, AT-18, AT-69/AT-80, regressão do float, janela e série anual, equivalência de `classify_frame` com `classify`); `test_real_data.py` ampliado (classes iguais a uma classificação independente nas séries completa e de junho, em quantidade e densidade; âncoras Brasil e ANAMÃ 130008); `test_territorial_selection.py` ampliado (direção, desfecho e BLQ-MET com dois períodos); `test_llm_context.py` ganha a guarda de privacidade da tendência. Teste mudado de propósito (o defeito não está no produto nem no teste; o comportamento mudou por D6): `test_representation.py`, cujo contrato da série passa a ter `quebras` e que agora confere os indicadores da evolução. Node: `trend.test.mjs` novo (inclui o texto do motivo na tabela) e `periods.test.mjs` ampliado. Roteiro `ui_block1_smoke.py` ampliado (selos iguais às linhas, motivo da tendência igual ao do motor ou "Não se aplica", contagens iguais à metadata, RES-SCL na base real e o atalho da série anual: BLQ-MET no catálogo sintético e 33 linhas de série na base real). Nenhuma verificação foi removida.

### 2026-10-19 · Sem confirmações de colunas e campos: escolha nos seletores e premissas no resultado

- **Antes:** em bases importadas e na base oficial com significados alterados, a preparação pedia "Confirmar correspondências", "Confirmar associação", "Confirmar identificador territorial", "Confirmar objeto de análise", "Confirmar as colunas de latitude e longitude selecionadas", botões de confirmação de quantitativo, população e identificação individual, e caixas "Confirmo…/Declaro…/Autorizo…" (força de trabalho em saúde, população, período único, comparabilidade, identidade territorial, populações sem sobreposição, ausência de sobreposição das pessoas entre territórios na agregação, soma dos componentes, identidade e cobertura da rotatividade, partes da contagem, contagem por identificador). Escolher uma coluna zerava a confirmação. O código territorial, as coordenadas com vírgula (ou com algum valor fora da faixa) e o período composto ficavam sempre "propostos", e o seletor já vinha preenchido com propostas. A etapa 2 se chamava "Parâmetros e confirmações" e contava confirmações; o selo dizia "Confirmação necessária"; a base oficial mostrava "Código confirmado" e "Objeto confirmado". Mudar uma única coluna da base oficial desligava o perfil inteiro. No chat, todo território citado gerava "Confirme a unidade territorial". Na rotatividade, unidade sem registro no período final contava como 100% de saída. O mapa sem papéis de coordenada pedia "Confirme que latitude e longitude estão em graus decimais" e a pendência genérica era `CONFIRMACAO`.
- **Agora:** o usuário só escolhe colunas e parâmetros. Regra conclusiva estabelece o papel (alias governado; período AAAAMM composto e validado, que só fica como sugestão se a base já tiver outra coluna de período reconhecida; latitude e longitude com nome do vocabulário e valores numéricos num formato decimal único, sendo que valor fora da faixa não impede o reconhecimento da coluna (o tratamento por território na análise espacial está na entrada seguinte de análise espacial)); sugestão não conclusiva (código territorial, UF, região, padrão de contagem, categoria sugerida pelo cabeçalho) deixa o seletor vazio, com a sugestão no topo marcada "(sugerida)" (`suggested_columns` no `/api/inspect`); escolher a coluna a estabelece, e sugestão nunca é seleção. O objeto de análise é o texto informado (`category_constant` ou, com coluna de categoria, `object_declaration`), com botão "Usar sugestão"; o período único é uma opção do seletor de período; o separador decimal das coordenadas é verificado nos dados (escolha só quando o formato é misto); o referencial continua um parâmetro. As antigas declarações viram premissas aplicadas pelo backend (`backend/analysis_premises.py`, gravadas em `analysis_premises` só quando há itens), com origem (`PERFIL_GOVERNADO`, `VERIFICADA_NOS_DADOS`, `PREMISSA_DA_ANALISE`, `DECLARADA_PELO_USUARIO`; o objeto reconhecido pelo catálogo é registrado como `fts_scope_recognized`, o que mantém o rótulo "profissionais"), nota em "Método e limitações" e limitação SOMA_COM_POSSIVEL_DUPLA_CONTAGEM quando cabível (`metadata.evaluability.limitacoes`); escolher as colunas dos componentes aplica a premissa de soma das partes; a coluna de identificador individual associada (reconhecida pelo nome do vocabulário ou escolhida) aplica as premissas de contagem de pessoas distintas e, na rotatividade, de identidade longitudinal e cobertura da coorte; na agregação, a tela deixa de oferecer a declaração de ausência de sobreposição das pessoas entre territórios (total como unidades distintas): o padrão é a soma dos componentes e, com identificador e sem quantidade, a caixa "Total da agregação" oferece pessoas distintas pelo identificador (a API continua aceitando `no_overlap_confirmed`); a identidade territorial ao longo do tempo é verificada nos dados e, se falhar, impede a evolução temporal com o motivo. Na rotatividade, unidade sem registro em um dos períodos fica não avaliável (SEM_REGISTRO_OBSERVADO). O perfil oficial vale campo a campo (`governed_roles`); a base oficial nunca cai no fluxo das importadas. A etapa passa a "Parâmetros", "pend." conta só escolhas (`requirements[].kind` = `escolha` ou `dados` e `requirements[].step`, classificados pelo backend; impedimentos nos dados aparecem sem contador) e o selo diz "Escolha pendente". Cada estado de campo traz `origin`; o pré-exame devolve também `object`, `premises` e `coordinate_separator`. O botão "Executar análise" fica sempre visível, desabilitado até a análise estar pronta. O chat registra o território como "Definido na abrangência territorial" (`set_in_scope`), sem bloqueio. Mudança de contrato no mapa: a pendência `CONFIRMACAO` passa a `ESCOLHA_PENDENTE`. A chave de execução das análises muda (as opções levam `governed_roles` e, quando aplicadas, as premissas da análise), e o comando "some os componentes" da conversa deixa de gravar premissas.
- **Permanece:** cálculos, fórmulas, dados e manifesto; a recusa de coluna não reconhecida e não escolhida (sugestão não é seleção; `test_remediation.py` sem mudança); valor explícito da API prevalece (premissa recusada com `false` continua bloqueando, com o texto "A premissa … foi recusada nas opções desta solicitação."); campos e enums da API (`confirmed_roles`, `needs_confirmation`, `confirmed`) com o significado de escolha; `ConfirmationRequired` como nome alternativo de `ChoiceRequired`; unidade de contagem, indicador, período, referencial e critérios como escolhas; o rótulo "Soma dos componentes (possível dupla contagem)"; a garantia "Total da fonte nacional; não é a soma dos municípios"; o conteúdo e a ordem de `governed_premises`; a análise espacial sem a camada complementar continua recusando o pedido inteiro quando há coordenada inválida.
- **Motivo:** decisão do responsável pelo produto (19/10/2026, D1): nenhuma confirmação de colunas e campos, em nenhum nível de análise, nas bases oficial e importada. **Substitui** as decisões registradas em "As quatro caixas das configurações em todas as análises" (que mantinha as confirmações da rotatividade e a preparação das bases importadas), "Referencial e separador decimal internos nas distâncias da base oficial" (que mantinha as caixas das bases importadas) e "Premissas de comparabilidade internas na base oficial" (que mantinha todas as declarações nas importações). **Divergências da SPEC registradas, sem alterar a SPEC:** RQ-DAD-05 (L1336: a proposta não é apresentada para confirmação; o seletor fica vazio e a escolha substitui a confirmação); RQ-DAD-06 (L1337: "confirmação incide sobre candidato já ancorado" passa a escolha pelo seletor); RQ-DAD-25 (L1386), na parte "requer confirmação do usuário" (a validade por elemento segue a SPEC); RQ-DAD-35 (L1408) e CAP-ROT-01 (L1778-1786: a identidade da pessoa, na contagem de pessoas distintas e na rotatividade, é estabelecida pela coluna de identificador individual, escolhida no seletor ou reconhecida pelo nome do vocabulário, e não por regra de identidade autorizada nem por declaração); RQ-DAD-36 (L1341, item b e última frase) e CFG-TER (L968: aditividade e comparabilidade viram premissas com nota e limitação; na base importada, o significado longitudinal da chave territorial é verificado nos dados, e não estabelecido por regra, metadado ou confirmação); tabela de interação, L274 ("Confirmar significado de campo").
- **Documentação e testes:** README (ponte semântica, base Brasil, chat, divergências da SPEC), adaptações da ponte semântica, validação da base Brasil, preparação guiada, guia da interface, Blocos 1, 2 e 3, modelo territorial e análise exploratória. Pytest novos: `test_sem_confirmacoes.py` (nenhum texto de confirmação nas 12 análises das bases importada e oficial, escolha pendente com `kind`, premissas com nota, recusa explícita, perfil campo a campo, sugestão do cabeçalho não aplicada, período único, separador verificado e misto, coordenada fora da faixa, rotatividade com SEM_REGISTRO_OBSERVADO) e, em `test_real_data.py`, a cópia importada da base municipal (31 testes reais). Pytest mudados de propósito (o defeito não está no produto nem no teste; o comportamento mudou por D1): `test_semantic_bridge.py` (mapeamento sem a proposta de contagem, região como sugestão, latitude fora da faixa reconhecida, objeto informado sem confirmação), `test_split_period.py` (período composto reconhecido; código só sugestão), `test_audit_conversation.py` (escolha pendente com cabeçalho de período não reconhecido), `test_llm_context.py` (`set_in_scope`), `test_representation.py` (vírgula verificada; formato misto mantém SEPARADOR_DECIMAL), `test_brazil_catalog.py` (premissas da análise na importação), `test_recommended_template.py` (código escolhido), `test_remediation.py::test_authorized_disaggregation_keeps_population_once` (componentes escolhidos aplicam a premissa; `false` explícito recusa), `test_nearest_reference.py` (vírgula verificada; formato misto pede a escolha) e o primeiro teste de `test_real_data.py` (código escolhido). Node: `fieldChoices.test.mjs` novo; `workspace.test.mjs` passa a testar o perfil campo a campo. Roteiros: as jornadas importadas passam a escolher o código e deixam de clicar em confirmações (`ui_conversational_smoke.py`, `ui_block1_regression.py`, `ui_criteria_smoke.py`, `ui_map_smoke.py`, `ui_nearest_smoke.py`, `ui_stabilization.py`, `ui_visibility_diagnostic.py`); "2. Parâmetros" (`ui_block1_smoke.py`, `ui_support.py`, `scripts/capturar_telas.py`); `ui_support.py` ganha `choose()`; roteiro novo `ui_sem_confirmacoes.py` na suíte `bloco1`, que também confere que nenhuma requisição leva premissa com `false`. Nenhuma verificação de segurança removida.

### 2026-10-19 · Pop-up de início só com a declaração de privacidade

- **Antes:** o pop-up de início tinha um ícone, o título "Antes de começar", a declaração de privacidade e um parágrafo sobre o prazo da sessão: "Esta sessão e seu conteúdo são eliminados ao acionar Encerrar sessão ou após 30 minutos (1800 segundos) sem interação efetiva sua…" (texto TPL-09 da SPEC). Depois de uma sessão encerrada, esse parágrafo aparecia também junto do aviso de descarte.
- **Agora:** o pop-up mostra só a declaração "Declaro que não compartilharei dados pessoais ou sensíveis, seja por meio dos arquivos enviados ou das mensagens inseridas no chat." e o botão "Li e concordo". A declaração passa a dar nome ao diálogo para leitores de tela. Depois de uma sessão encerrada, o aviso de descarte continua acima da declaração.
- **Permanece:** o aceite por aba, o aviso de descarte ("A sessão anterior foi encerrada." ou "A sessão anterior expirou ou ficou indisponível no servidor.", seguido de "Os resultados e a investigação temporária foram descartados. Eles não podem ser reabertos nesta nova sessão."), o encerramento da sessão no servidor após 1.800 segundos sem interação efetiva e o descarte do conteúdo. Só o texto sobre o prazo deixa de aparecer.
- **Motivo:** decisão do responsável pelo produto (19/10/2026): "Pop-up de início é só precisa ter declarado que não compartilharei dados pessoais ou sensíveis, seja por meio dos arquivos enviados ou das mensagens inseridas no chat. Só isso." e a informação sobre conteúdos eliminados e 1.800 segundos "não tem sentido". **Divergência da SPEC registrada:** RQ-FLX-19 e TPL-09 pedem esse aviso no início da sessão (AT-44); a SPEC não foi alterada.
- **Documentação e testes:** README (sessão e fronteira da SPEC) e análise exploratória integrada. `ui_integrated_workspace.py` passa a conferir que o diálogo tem a declaração como nome e não mostra o prazo, "eliminados" nem o título antigo. Nenhuma verificação foi removida.

### 2026-10-19 · As quatro caixas das configurações em todas as análises

- **Antes:** depois de `deb3882`, as caixas Categoria, Período, Abrangência territorial e Indicador apareciam completas só em densidade, quantitativos, distribuição, comparações, evolução temporal e relatórios. Agregações, recortes e rankings, referência mais próxima e critérios combinados não tinham a caixa Indicador; a análise espacial não tinha Período nem Indicador; a rotatividade não tinha Período nem Indicador e pedia o período inicial e o final em seletores soltos no texto, com os códigos das competências (201401). Valores longos nas caixas de escolha eram cortados com reticências.
- **Agora:** todas as análises da base oficial mostram as mesmas quatro caixas, na mesma ordem. Sem escolha entre quantidade e densidade, a caixa Indicador mostra, numa opção só, o indicador que o motor calcula: Quantidade e densidade por 1.000 habitantes (agregações), Densidade por 1.000 habitantes (recortes e rankings), Distância geodésica (km) (análise espacial), Permanência e rotatividade da coorte (%) (rotatividade), Distância à referência mais próxima (km) (referência mais próxima) e, nos critérios combinados, os atributos usados nas condições, na ordenação e nas faixas ("Definido nos critérios" enquanto não há nenhum). Na análise espacial, a caixa Período informa "Não se aplica: as distâncias não dependem do período". Na rotatividade, a caixa Período mostra a coorte ("de janeiro de 2014 a junho de 2024") e abre o período inicial e o final, com as competências por extenso; sem escolha, valem a primeira e a última, como já fazia o motor. As caixas de escolha mostram o valor inteiro, com quebra de linha.
- **Permanece:** cálculos, pré-exame, contratos e dados; as escolhas e os padrões de cada análise; os quadros "Referências territoriais" e "Critérios do usuário" abaixo das caixas; as confirmações da rotatividade; a preparação das bases importadas e da base oficial com significados alterados, inclusive os seletores de período da rotatividade no texto.
- **Motivo:** orientação do responsável pelo produto (19/10/2026): "Esses mesmos ajustes precisam ocorrer ao acionar as demais análises".
- **Documentação e testes:** README e guia da interface. Testes Node novos do indicador próprio de cada análise (`ownIndicator`) e do período da coorte (`rotationPeriods`). `ui_support.py` passa a navegar também até referência mais próxima e critérios combinados; `ui_stabilization.py` percorre as doze análises e confere as quatro caixas, o indicador próprio de cada uma, o período não aplicável da análise espacial e a escolha do período inicial da rotatividade. Nenhuma verificação foi removida.

### 2026-10-19 · Preparação em abas com contorno e configurações em caixas seletoras

- **Antes:** "1. Preparação" e "2. Resultados" eram dois botões pequenos acima do conteúdo, sem ligação visual com ele. A preparação começava com "Defina territórios, período e parâmetros. O motor valida as condições antes de habilitar o cálculo.". Na base oficial, o "Resumo da análise" mostrava cartões só informativos de fonte, categoria, períodos e indicador. O período era escolhido numa etapa separada ("Escolha o período da análise", com "Avançar" e "Voltar à escolha do período"), o indicador numa frase ("Deseja trabalhar com …?"), a abrangência na escolha "Abrangência dos dados" entre Municípios e Brasil (total nacional), e os municípios num bloco "Territórios" acima da preparação, disponível só no recorte municipal. No total nacional, a densidade podia ser escolhida e deixava o cálculo bloqueado.
- **Agora:** as duas áreas são abas, e um contorno desce da aba ativa e envolve todo o conteúdo da etapa. A orientação passa a ser "Realize as configurações conforme a sua escolha.". Na base oficial, "Configurações" reúne caixas seletoras: Categoria (MEDICINA, a única da base), Período (no singular), Abrangência territorial e Indicador (Quantidade ou Densidade por 1.000 habitantes; fixo em Densidade e Quantitativos). Agrupamento, Território de referência e, fora da versão governada, Referencial geodésico entram na mesma grade; o cartão "Fonte" deixa de existir. Uma caixa sem escolha fica destacada, e o cálculo continua bloqueado até ela ser preenchida. A caixa Período abre a lista de competências abaixo das configurações, com um ou vários períodos conforme a análise (vários só em quantitativos, evolução temporal e relatórios), e "Concluir" a recolhe; a etapa separada de período deixa de existir. A caixa Abrangência territorial reúne Brasil (total nacional) e a lista de municípios, com busca e escolha de um ou mais. Marcar municípios com o total nacional escolhido leva a análise ao recorte municipal, já com os municípios marcados; para isso, a lista municipal é consultada ao abrir a caixa (`POST /api/inspect` do recorte municipal, só leitura), quando o último pré-exame municipal não a deixou guardada. Desmarcar ou limpar no total nacional só altera a seleção guardada. Nas análises só municipais, a caixa informa que só a fonte municipal se aplica. No total nacional, "Densidade por 1.000 habitantes" aparece indisponível. Na base oficial, o bloco "Territórios" acima da preparação deixa de aparecer: a caixa Abrangência territorial o substitui.
- **Permanece:** cálculos, pré-exame, contratos da API e dados; os padrões de abrangência por análise; a seleção guardada ao escolher o total nacional; a lista de vários períodos (intervalo, todos, limpar e clique que escolhe); os comandos de navegação ("Volte para a seleção de territórios." abre a caixa Abrangência territorial); a preparação das bases importadas e da base oficial com significados alterados, inclusive o bloco "Territórios"; as condições avançadas.
- **Motivo:** orientação do responsável pelo produto (19/10/2026): deixar claro que todo o conteúdo abaixo da aba pertence à preparação, trocar a orientação, chamar o resumo de configurações e transformar os cartões em caixas seletoras de categoria, período, abrangência territorial (Brasil e municípios) e indicador, sem a fonte. A densidade indisponível no total nacional segue a regra de não oferecer escolha que leve a um bloqueio (entrada "Preparação: abrangência, resumo visual e intervalo de períodos").
- **Documentação e testes:** README, guia da interface, preparação guiada e validação da base Brasil. Teste Node novo de `territorialScope.ts` (texto da caixa e regra de marcar ou desmarcar no total nacional). `ui_support.py` ganha `expand()`, que abre a lista de uma caixa. `ui_stabilization.py`, `ui_conversational_smoke.py`, `ui_block1_smoke.py`, `ui_block1_integration.py` e `ui_criteria_smoke.py` deixam de usar "Voltar à escolha do período", "Avançar", o texto "Escolha o período da análise" e a informação "municípios brasileiros", que deixaram de existir, e passam a abrir as caixas Período e Abrangência territorial. As verificações de valores, períodos, recorte e bloqueio continuam; o cálculo sem período, antes oculto, agora é conferido desabilitado. Novas verificações: marcar um município no total nacional leva ao recorte municipal e o cálculo usa só ele (`ui_conversational_smoke.py`); a densidade fica indisponível no total nacional e volta nos municípios, e a aba ativa se liga ao contorno da etapa nas quatro larguras (`ui_stabilization.py`). `scripts/capturar_telas.py` ganha a captura da abrangência territorial. Nenhuma verificação foi removida.

### 2026-10-18 · Verificação local proporcional ao risco e ao alcance da mudança

- **Antes:** a seção 4 do `AGENTS.md` exigia, antes de cada push, a verificação local completa: pytest do backend, build do frontend, todas as jornadas de navegador e governança, além dos testes com dados reais quando a mudança tocava o motor, a API ou os dados.
- **Agora:** a verificação local é proporcional à natureza, ao alcance e ao risco da mudança. Uma tabela indica o que rodar conforme o que mudou: os testes dos módulos alterados, o build e os roteiros de navegador afetados, a governança depois do commit e, quando a mudança toca o motor, a API ou os dados, também os testes com dados reais. Microajustes não pedem a verificação completa, e o escopo cresce quando há risco concreto de integração, regressão ou violação de governança. `run_ui_checks.py --roteiro` roda só os roteiros indicados.
- **Permanece:** o CI roda todas as verificações em todo push, e o trabalho só termina com o CI em PASS em todos os jobs obrigatórios. Os testes com dados reais continuam obrigatórios quando a mudança toca o motor, a API ou os dados, a integridade e a ordem de atualização da base (regra 2) não mudam, e a governança continua obrigatória. Nenhum job do CI foi alterado, e nenhum comportamento do produto muda.
- **Motivo:** decisão do responsável pelo produto (18/10/2026), que adotou o princípio de proporcionalidade operacional: evitar verificações redundantes e ciclos longos sem reduzir as garantias exigidas na entrega.
- **Documentação e testes:** `AGENTS.md` (seções 4 e 5 e mapa rápido), README (seção Testes), descrição de `scripts/verificar_tudo.py` e a opção `--roteiro` do executor de navegador. Regra de processo, sem teste do produto.

### 2026-10-18 · Resumo de períodos: poucas competências fora de sequência pelo nome

- **Antes:** duas ou três competências fora de sequência eram descritas como intervalo com exceções, por exemplo "2 competências, de janeiro de 2014 a junho de 2015, exceto junho de 2014, janeiro de 2015".
- **Agora:** até três competências fora de sequência aparecem pelo nome: "janeiro de 2014 e junho de 2015" ou "janeiro de 2014, junho de 2015 e junho de 2024". Vale para o cartão "Períodos" do resumo da análise e para a linha "Selecionadas" do seletor.
- **Permanece:** competência única, intervalos contínuos ("2 competências, de janeiro de 2024 a junho de 2024"), todas as competências e seleções maiores com lacunas nomeadas ou contadas; a ordem cronológica; cálculos e contratos.
- **Motivo:** proposta da rodada anterior, autorizada pelo responsável pelo produto em 18/10/2026. A forma com exceções era difícil de ler em seleções pequenas, como a do vídeo de orientação.
- **Documentação e testes:** guia da interface. Teste Node de `describePeriods` com duas e três competências fora de sequência; o intervalo contínuo e a contagem de lacunas continuam cobertos. `ui_stabilization.py` passa a esperar "janeiro de 2023 e junho de 2024" no cenário do vídeo.

### 2026-10-18 · Verificação local: npm ci dispensado quando as dependências não mudam

- **Antes:** a seção 4 do `AGENTS.md` exigia `npm ci` antes de cada build da verificação local, mesmo sem nenhuma mudança nas dependências do frontend.
- **Agora:** na verificação local, o `npm ci` pode ser dispensado quando `package.json` e `package-lock.json` não mudaram desde o último `npm ci` bem-sucedido; nesse caso, basta `npm run build`.
- **Permanece:** o CI roda `npm ci` em todo push, e os jobs e verificações obrigatórios não mudam. Quando as dependências mudam, o `npm ci` continua obrigatório também localmente. Nenhum comportamento do produto muda.
- **Motivo:** decisão do responsável pelo produto (18/10/2026), para simplificar a verificação local sem reduzir as garantias do CI. Localmente, o `npm ci` repetia uma instalação idêntica e, no Windows, falhava quando um servidor Vite aberto travava arquivos de `node_modules`.
- **Documentação e testes:** `AGENTS.md` (seção 4) e README (seção Testes). Regra de processo, sem teste do produto.

### 2026-10-18 · Escolha de vários períodos: clicar escolhe a competência

- **Antes:** quando a lista de vários períodos vinha com todas as competências incluídas por padrão, como na evolução temporal, todas apareciam marcadas e clicar numa delas a retirava. Quem clicava para escolher competências acabava tirando justamente as que queria analisar. Durante o carregamento de outro recorte, a lista continuava clicável, mas a escolha se perdia quando o recorte chegava.
- **Agora:** nesse estado padrão, as competências aparecem sem marca, com o aviso "Todos os períodos estão incluídos. Para analisar só alguns, clique neles:", e o primeiro clique escolhe só a competência clicada; os cliques seguintes acrescentam ou retiram. Depois de "Todos os períodos disponíveis", as competências aparecem marcadas e o clique retira, como antes. O resumo descreve a escolha, por exemplo "2 competências, de janeiro de 2023 a junho de 2024, exceto junho de 2023, janeiro de 2024". Enquanto outro recorte carrega, a lista de períodos fica bloqueada, porque a escolha feita nesse intervalo era descartada quando o recorte chegava.
- **Permanece:** a evolução temporal continua começando com todas as competências; intervalo, "Todos os períodos disponíveis", "Limpar", a exigência de ao menos uma competência para avançar, cálculos e contratos.
- **Motivo:** o responsável pelo produto confirmou (18/10/2026) que, no vídeo de orientação (06:04), os cliques em janeiro de 2014 e junho de 2015 eram para escolher esses períodos. A entrada "Preparação: abrangência, resumo visual e intervalo de períodos" tinha deixado essa parte à espera da confirmação. A perda da escolha durante o carregamento apareceu na verificação desta mudança.
- **Documentação e testes:** guia da interface. Teste Node da regra do clique (`clickPeriod`). `ui_stabilization.py` ganha o cenário do vídeo na evolução temporal (dois cliques escolhem as duas competências) e confere a lista bloqueada enquanto o recorte nacional carrega. Na importação, o primeiro clique escolhe a competência e retirá-la deixa a confirmação bloqueada; antes, dois cliques esvaziavam a seleção a partir de todas marcadas, o que deixou de ser o comportamento.

### 2026-10-18 · Referencial e separador decimal internos nas distâncias da base oficial

- **Antes:** na base Brasil oficial, a análise espacial, a referência mais próxima e os critérios com distância pediam na preparação o referencial geodésico (SIRGAS2000). A referência mais próxima e os critérios também pediam o separador decimal das coordenadas, e a análise espacial ficava bloqueada ("Há valores não numéricos ou não finitos em latitude…") até o usuário escolher "Vírgula decimal" em "Formato dos valores numéricos", nas condições avançadas. Essas condições avançadas também exibiam, na base oficial, a caixa de comparabilidade entre territórios e as declarações da agregação, embora essas premissas já fossem internas e marcá-las ou desmarcá-las não mudasse o cálculo.
- **Agora:** na versão governada da base (integridade verificada e versão do manifesto), o referencial SIRGAS 2000 é regra do perfil, porque a fonte não o declara, e a vírgula decimal é verificada nos dados (coordenadas com vírgula decimal ou inteiras; quantidades e populações sem vírgula). As duas premissas entram só nas análises que usam coordenadas, com nota em "Método e limitações", registro em `governed_premises` e, no mapa, `premissa_referencial` e a legenda "Referencial SIRGAS 2000: premissa da base oficial…". A preparação mostra "Referencial: SIRGAS 2000 (premissa da base oficial)" e não exibe os seletores de referencial e de separador; o pré-exame descreve o requisito como premissa governada. Nas condições avançadas da base oficial, "Formato dos valores numéricos" passa a ser uma informação ("vírgula decimal nas coordenadas, verificada na base oficial"), e as caixas de premissas internas não aparecem.
- **Permanece:** distâncias, método geodésico e camada complementar; nenhuma transformação de referencial. Análises sem distância não recebem as duas opções (mesmas opções e chave de execução), e o mapa delas continua com a configuração só de apresentação. Bases importadas, versões externas fixadas e significados alterados continuam pedindo referencial, separador e declarações. Valor informado explicitamente pela API prevalece: referencial não suportado e ponto decimal com coordenadas com vírgula continuam recusados. A declaração de ausência de sobreposição, nas condições avançadas, continua disponível e prevalece sobre a soma dos componentes.
- **Motivo:** decisão do responsável pelo produto (18/10/2026), em resposta à pergunta deixada pela análise do vídeo de orientação: "pode deixar interno"; as caixas de confirmação das bases importadas são mantidas. As caixas que restavam nas condições avançadas eram uma lacuna da entrada "Premissas de comparabilidade internas na base oficial".
- **Documentação e testes:** README, validação da base Brasil (tabela de premissas internas), Blocos 2 e 3 e guia da interface. Novos testes do perfil (verificação do separador e restrição à versão governada) e da API na versão governada (pré-exame, resultados iguais aos declarados, notas, contrato do mapa, densidade sem as opções, conversa sobre o resultado na mesma preparação e prevalência do valor explícito). Testes reais: a lista de premissas da versão governada ganha as duas novas (mudança intencional), e espacial, mais próxima e critérios sem declaração dão o mesmo resultado que com declaração. `ui_block1_smoke.py`: na base real, a análise espacial calcula sem pedir referencial, com nota e legenda da premissa, e as condições avançadas não mostram seletores nem caixas de premissas internas; no catálogo sintético, o seletor de referencial continua.

### 2026-10-18 · Resultados mais legíveis: destaques, mapa com nomes e série temporal

- **Antes:** um resultado com um único município mostrava no mapa só um ponto numa área vazia, sem destaque do valor principal. O gráfico de linhas começava o eixo em zero, achatando variações pequenas, e sempre mostrava a caixa de legenda, mesmo com uma série. As tabelas exibiam competências como 201406. A aba "Mapa (não aplicável)" abria com o título "Mapa indisponível para este resultado". A identidade do resultado listava todas as competências.
- **Agora:** densidade, quantitativos, relatório e evolução com até três registros mostram cartões de destaque com os valores do motor; na evolução, inicial → final, variação absoluta e percentual e a tendência do motor. O mapa nomeia os territórios quando há até 12 pontos (até três, também com o valor) e mostra grade de coordenadas em zoom alto. O gráfico de linhas enquadra o eixo vertical nos valores observados, informa quando ele não começa em zero, usa marcadores de 8 px, dispensa a caixa de legenda numa série única e rotula só o último valor de cada série (até quatro). As tabelas exibem competências como 06/2024, e a busca aceita 06/2024 ou 202406. "Mapa não aplicável a este resultado" tem título próprio e, na evolução, orienta como ver os territórios no mapa. A identidade do resultado resume mais de três competências por quantidade e extremos.
- **Permanece:** valores, cálculos, CSV (com as competências originais), contrato de representação, regra de não desenhar a evolução no mapa, ordem neutra e ausência de totais, médias, posições, classes e linhas de tendência. A escala de apresentação continua por 1.000 habitantes.
- **Motivo:** orientação em vídeo do responsável pelo produto (18/10/2026, 03:47–04:14 e 07:05–08:04): mapa só com um ponto, mapa considerado não aplicável e pedido de visualização mais inteligível, dentro das transformações admitidas pela Parte 13 da SPEC.
- **Documentação e testes:** Bloco 3 e README. Testes Node de `niceDomain`, `tableColumns` e `compactPeriods`. `ui_block1_smoke.py` (sintético e base real) exige três cartões na evolução e competência legível na tabela; `ui_conversational_smoke.py` exige o cartão do quantitativo nacional.

### 2026-10-18 · Preparação: abrangência, resumo visual e intervalo de períodos

- **Antes:** a abrangência ficava num recolhível "Alterar a abrangência territorial" em todas as análises, inclusive nas que só existem na fonte municipal. Trocar de recorte apagava a preparação e mostrava a escolha da fonte ("Preparando seus dados...") até o novo recorte chegar. "Parâmetros da análise" era um parágrafo com todas as competências na ordem do arquivo. A seleção de vários períodos começava com todos marcados e só aceitava cliques competência por competência, com pouca diferença visual entre marcadas e desmarcadas. Na troca de recorte entre análises, o período único de uma densidade podia ser copiado para a evolução temporal, que ficava com uma só competência.
- **Agora:** "Abrangência dos dados" é uma escolha visível entre Municípios e Brasil (total nacional) em quantitativos, evolução temporal e relatórios; nas demais análises, a preparação informa que usa somente a fonte municipal. Durante a troca, a preparação continua na tela, bloqueada, com aviso de carregamento; se o novo recorte falhar, ela é mantida com o motivo. "Resumo da análise" mostra cartões de fonte, categoria, períodos e indicador, com os períodos em ordem cronológica e resumidos por intervalo. O seletor de vários períodos tem "Intervalo: de … até …", "Todos os períodos disponíveis", "Limpar", chips marcados com ✓ e a descrição da escolha. Períodos só atravessam a troca de recorte, ou a restauração do rascunho do recorte, quando a análise de destino aceita o mesmo modo (único ou vários).
- **Permanece:** cálculos, pré-exame, contratos e dados; os padrões de abrangência por análise; a opção "Abrangência da análise" nas condições avançadas; a memória da preparação de cada recorte na aba.
- **Motivo:** orientação em vídeo do responsável pelo produto (18/10/2026): dúvida sobre a abrangência (02:17–03:12), troca de recorte que voltou à tela inicial (03:12–03:35), parâmetros em texto corrido e fora de ordem (05:21–05:50) e escolha de períodos que desmarcou o intervalo pretendido (05:59–06:17). O defeito da troca entre análises apareceu na verificação visual desta mudança.
- **Documentação e testes:** README, guia da interface, validação da base Brasil e preparação guiada. Testes Node de `periods.ts` (descrição e intervalo). `ui_conversational_smoke.py` passa a trocar a abrangência em Quantitativos e confere a informação fixa na Densidade e o resumo. `ui_criteria_smoke.py` escolhe o recorte nacional em Quantitativos antes do comando de critérios. `ui_stabilization.py` usa o intervalo de períodos e ganha uma regressão da troca de recorte entre análises. Nenhuma verificação existente foi removida.

### 2026-10-18 · Territórios dentro da preparação

- **Antes:** cada análise tinha três etapas, "1. Territórios", "2. Preparação" e "3. Resultados". A seleção territorial ocupava uma etapa própria, com "Avançar para preparação" e "Voltar aos territórios".
- **Agora:** duas áreas, "1. Preparação" e "2. Resultados". A seleção territorial é um bloco da preparação, com resumo de uma linha ("Territórios: todos os territórios do recorte" ou "1 selecionado: ABREU E LIMA (PE)") e os botões "Escolher territórios", "Alterar territórios" e "Concluir seleção". O bloco começa recolhido. Comandos como "Volte para a seleção de territórios.", "Usar seleção na próxima análise" e "Usar como municípios-alvo" abrem a preparação com o bloco expandido. Em referência mais próxima e critérios, o bloco se chama "Municípios-alvo" e "Universo dos critérios". No recorte nacional, o bloco só informa o território único (Brasil), e o comando de territórios explica que a escolha de municípios vale para a abrangência Municípios.
- **Permanece:** o componente de seleção (busca, estado, limpar, adicionar correspondências e atalhos de análise), a preservação da seleção ao navegar, os cálculos e os contratos. Nenhum controle volta a ser empilhado numa página longa.
- **Motivo:** orientação em vídeo do responsável pelo produto (18/10/2026, 00:45–01:47 e 04:19–04:36): a etapa de territórios é desnecessária e a segmentação incomoda, sem voltar à rolagem longa que motivou as etapas.
- **Documentação e testes:** guia da interface, README e nota na auditoria de estabilização. O auxiliar `workspace()` de `ui_support.py` abre o bloco quando a jornada pede territórios, e os roteiros usam o auxiliar em vez dos rótulos antigos. As verificações de seleção, valores e exportações não mudaram.

### 2026-10-18 · Premissas de comparabilidade internas na base oficial

- **Antes:** na base Brasil governada, a evolução temporal exigia as caixas "Confirmo que os quantitativos e os períodos são comparáveis." e "Os territórios correspondem às mesmas unidades ao longo do tempo.". Comparações e rankings só dispensavam a confirmação numa competência municipal identificada, por inferência do navegador. A agregação exigia declarar populações sem sobreposição e a forma de contagem. O resultado temporal dizia que as premissas tinham sido declaradas pelo usuário.
- **Agora:** com o perfil governado reconhecido, `brazil_catalog_profile.py` aplica no backend a comparabilidade temporal, a comparabilidade entre municípios, as populações sem sobreposição e a soma dos componentes (regras do perfil). A identidade territorial ao longo do tempo só é aplicada depois de verificar nos dados que cada código mantém o mesmo nome em todas as competências. A interface não mostra essas caixas na base oficial, nem nas opções avançadas. `curated_defaults.premises` lista as premissas do recorte; `governed_premises`, nas opções do resultado, registra as aplicadas; "Método e limitações" informa a origem de cada uma.
- **Permanece:** cálculos, fórmulas, valores e o rótulo "Soma dos componentes (possível dupla contagem)". Bases importadas e significados alterados continuam com todas as declarações. A declaração explícita de ausência de sobreposição, nas opções avançadas, prevalece sobre a soma. Nada novo vai ao provedor de IA: a conversa lê só uma lista fixa de opções. Dados, manifesto e SPEC inalterados.
- **Motivo:** orientação em vídeo do responsável pelo produto (18/10/2026, 06:17–07:01): na base disponibilizada, o usuário não tem como confirmar essas premissas; a verificação deve ser interna e sem regressão. A tentativa anterior (`9d3c7cf`, revertida) só escondia as caixas e deixava a evolução bloqueada.
- **Documentação e testes:** README, validação da base Brasil (seção nova), guia da interface, Bloco 1 e nota na auditoria de estabilização. Testes novos de backend (catálogo sintético, evidência da identidade territorial, importações) e com dados reais. Em `test_real_resident_aggregation_is_not_national_unique_count`, a expectativa de 422 sem declaração mudou de propósito; continuam conferidos o rótulo de dupla contagem, as somas e a diferença para a contagem nacional, agora sem declarações. `ui_block1_smoke.py` e `ui_stabilization.py` passam a exigir a ausência das caixas e a origem nas notas, mantendo os valores conferidos.

### 2026-10-18 · Estabilização de navegação, períodos e comparações

- **Antes:** etapas controladas em dois componentes e uma regra CSS podiam ocultar a preparação; navegação atrasada após o cálculo podia desfazer o retorno do usuário. O seletor mantinha um modo local divergente dos períodos da análise. Configurações disponíveis desapareciam quando o pré-exame era aprovado; a atualização do pré-exame também podia reiniciar a navegação pelo carrossel. A comparação A/B era apresentada como um único território e perdia filtros. A proteção nominal removia o interrogativo “Quantos” do pedido ao intérprete.
- **Agora:** `App` controla a etapa única; botões, chat, retomada e reutilização abrem a etapa correspondente sem apagar escolhas. Os painéis inativos preservam estado e ficam ocultos; impressão continua incluindo o resultado. Período único e conjunto de períodos mudam atomicamente; seleção vazia não equivale a todos. A preparação oficial permite editar períodos e condições disponíveis; comparabilidade automática só vale com os significados reconhecidos preservados, em uma competência municipal identificada. O carrossel conserva a opção em exploração quando apenas a disponibilidade é atualizada. Comparações A/B exibem dois registros e as diferenças originais, com filtros, ordenação e exportação. A última resposta do agente permanece junto ao compositor. “Quantos/Quantas” são reconhecidos como interrogativos, mantendo a proteção de identificadores e dados.
- **Permanece:** dados, manifesto, SPEC, SVG do avatar, métodos, fórmulas, resultados numéricos e contratos analíticos. Importações e comparabilidade temporal conservam declarações necessárias. Mensagens preparam, nunca executam cálculos. CSV mantém as linhas originais do motor, inclusive a relação A/B.
- **Motivo:** auditoria da branch a partir de `7dd5d2c`, CI #330 reprovado e reprodução local da preparação oculta; falhas de produto distinguidas de roteiros que ainda interagiam com etapas simultâneas.
- **Documentação e testes:** guia da interface e README atualizados; relatório `AUDITORIA_ESTABILIZACAO_20261018.md`; nova jornada `ui_stabilization.py` registrada no executor, testes de comandos/validade do reconhecimento oficial e integração de proteção de identificadores. Roteiros existentes percorrem etapas sem remover asserções analíticas, de privacidade, exportação ou integridade. Nenhum teste foi removido ou enfraquecido.

### 2026-10-17 · Interface conversacional integrada, sessões e diagnósticos

- **Antes:** menu lateral permanente e chat em coluna separada; a investigação reunia todos os resultados sem distinguir diagnósticos; encerramento imediato por um controle separado.
- **Agora:** banner horizontal e cinco ações únicas (Início, Nova sessão, Nova análise, Histórico e Resultados); conversa expansível e campo contextual; personagem original junto à condução e aos resultados. Nova sessão exige confirmação, oferece exportação com limitação explícita por análise e revoga a sessão no servidor. Nova análise distingue criação independente e composição ordenada; intenção explícita na conversa evita a escolha redundante. O histórico reabre resultados e diagnósticos sem recálculo.
- **Permanece:** cálculos, fórmulas, validações, contratos analíticos/conversacionais, isolamento e limites de sessão, fontes nacional e municipal, manifesto, SPEC, personagem, visualizações, filtros e exportação técnica. Composição não harmoniza nem combina valores. Não há persistência nem exportação consolidada de múltiplas análises.
- **Motivo:** conduzir toda a investigação no mesmo ambiente, com distinção clara entre sessão, análise e diagnóstico, preservando identidade e rastreabilidade.
- **Documentação e testes:** guia da interface, relatório de rastreabilidade, README e guias temáticos atualizados. Jornadas preservam asserções funcionais e adotam a nova navegação; novo roteiro integrado registrado no executor. Teste de autorização PT corrigido para remover efetivamente o adendo em arquivos CRLF antes de exigir rejeição; nenhuma verificação de segurança foi relaxada.

### 2026-10-17 · Disponibilidade da investigação e encerramento visível

- **Antes:** expiração, reinício do servidor ou encerramento descartavam a investigação e recarregavam a página sem informar o motivo ao retornar.
- **Agora:** a abertura de uma nova sessão informa descarte por encerramento ou indisponibilidade/expiração, sem oferecer reabertura inexistente. A visão geral descreve apenas a página visível para evitar retenção de listas territoriais de todas as etapas.
- **Permanece:** prazo, isolamento, limites, descarte, memória temporária, contratos de API e proteções conversacionais. Guarda-se apenas um marcador de motivo no armazenamento da aba, removido no próximo aceite; nenhum resultado, token ou dado é persistido.
- **Motivo:** tornar a disponibilidade dos resultados compreensível e verificar as jornadas de maior volume e falhas.
- **Documentação e testes:** guia da investigação e relatório técnico; ampliação de `ui_investigation.py` com distância, paginação, limite real de referências, falha de rede e perda de sessão pelo backend.

### 2026-10-17 · Investigação progressiva e destaque territorial coordenado

- **Antes:** resultados podiam ser reabertos pelo histórico, mas faltava visão acumulada da investigação e controles visuais eram reiniciados ao navegar.
- **Agora:** etapas paginadas identificam operações, fontes, recortes, períodos, unidades e situação; cada resultado pode ser expandido/recolhido. Filtros, seleção, indicadores e páginas são lembrados por resultado. Destaque explícito entre etapas exige identidade compatível e informa diferenças; não transfere valores, classes ou relações. Resultados sem linhas e sem referência conversacional têm estados visíveis.
- **Permanece:** operações, motores, métodos, dados, SPEC, validações, exportações e histórico anterior; parâmetros só são retomados explicitamente, cálculos exigem execução, conversa usa referências verificadas e a retenção continua temporária.
- **Motivo:** permitir investigação contínua sem misturar resultados metodologicamente distintos.
- **Documentação e testes:** `ANALISE_EXPLORATORIA_INTEGRADA.md`, testes de compatibilidade do frontend e `ui_investigation.py` registrado no executor, com catálogo sintético e base versionada.

### 2026-10-17 · Incremento 3 — leitura ancorada de resultados

- **Antes:** a conversa não recuperava o resultado apresentado por referência verificada e não distinguia explicação de novo cálculo.
- **Agora:** densidade, quantitativos e comparação territorial admitem leitura do resultado da sessão, segmentos com caminhos verificáveis, relações já produzidas pelo motor, documentação PT e simplificação sem retirar fatos ou limitações. Relação ausente oferece preparação explícita de comparação, sem executá-la. A preparação atual e o recorte do resultado permanecem distintos. Alteração de dados, referência forjada ou conteúdo adulterado não sustentam resposta. Cortesia e descrição geral não dependem de base pronta. A minimização no caminho de sessão também reconhece variações de acento/caixa e protege o nome do arquivo.
- **Permanece:** cálculos, validações analíticas, limites/modelo do Gemini, catálogo literal e bloqueio EN. As demais operações continuam acessíveis diretamente; sua leitura analítica conversacional recebe insuficiência documental até haver composição específica validada. Não há explicação causal nem novo ranking derivado pelo chat.
- **Motivo:** tornar resultados exploráveis com controles proporcionais por construção, sem LLM auditor ou interpretação analítica livre.
- **Documentação e testes:** README, `CONVERSACAO_INCREMENTO_FN.md`, `EVOLUCAO_CONVERSACIONAL_20261016.md`, `test_result_conversation.py`, ampliação de testes de sessão e da jornada `ui_semantic_continuity.py` já registrada.

### 2026-10-16 · Incremento 2 — seleção contextual e sessão temporária

- **Antes:** resultados existiam apenas no navegador; não havia vínculo de sessão no servidor, expiração efetiva ou controle de encerramento. “Esses municípios” e correções de indicador podiam perder o contexto.
- **Agora:** sessão opaca em memória com expiração de 1.800 segundos e encerramento; captura verificada da seleção/parametrização; IDs de resultados resolvidos somente na sessão de origem; respostas tardias rejeitadas por revisão. Referências dêiticas, correção de quantidade/densidade e inclusão de município reaproveitam preparação. A conversa informa possibilidades atuais sem executar.
- **Permanece:** métodos e motor, manipulação direta da interface, ausência de persistência de arquivos e limites do Gemini. API sem sessão conserva compatibilidade; a interface utiliza sessão.
- **Motivo:** consciência de tela sem confiar em resultados enviados pelo navegador nem criar banco de dados.
- **Documentação e testes:** README, `EVOLUCAO_CONVERSACIONAL_20261016.md`, `test_conversation_session.py` e ampliação de `ui_semantic_continuity.py`, já registrada no executor.

### 2026-10-16 · Incremento 1 — catálogo PT e continuidade conversacional

- **Antes:** explicações metodológicas usavam textos locais não materializados do catálogo; saudações podiam reiniciar a apresentação e referências explícitas só alcançavam a última mensagem.
- **Agora:** densidade, distância e agregação usam formas PT literais verificadas contra o Anexo A; EN bloqueado. O contrato reconhece intenção de esclarecimento, simplificação, próximos passos e alteração contextual. Cortesia do modelo é limitada por construção; saudação repetida é breve; referências explícitas atravessam perguntas intermediárias. Simplificação reorganiza formas existentes, sem paráfrase metodológica.
- **Permanece:** cálculos, dependências externas, modelo, cota e controles de execução. Nenhuma forma do catálogo foi reescrita.
- **Motivo:** autorização expressa de implementação e uso delimitado PT. Adendo APT-20261016 excepciona somente a dependência de aprovação EN para uso PT local.
- **Documentação e testes:** `DECISAO_CATALOGO_PT_20261016.md`, `EVOLUCAO_CONVERSACIONAL_20261016.md`, adendo da SPEC e `test_document_conversation.py`. Expectativa textual de densidade atualizada para a fórmula canônica; motivo documentado no relatório de execução.

### 2026-10-16 · Interpretações concorrentes, continuidade municipal e painéis de conversa/resultados

- **Antes:** o prompt limitava o modelo a uma capacidade; a interpretação não se ligava à seleção municipal local e pedidos subsequentes voltavam a orientações genéricas. A fonte e o carrossel repetiam-se após cada interação. O histórico só aparecia a partir do segundo cálculo, dentro do resultado; preparação e resultado longos afastavam o campo de mensagem.
- **Agora:** o contrato aceita até cinco candidatas de operação/indicador com âncoras literais no pedido sanitizado atual. Leituras materialmente diferentes apresentam escolhas; sem base, a escolha prepara rascunho e, com base, prepara a análise localmente. A capacidade validada pode ser ligada aos nomes municipais pelo Python, sem enviar o catálogo ao provedor. Comparações com um município perguntam qual outro; pedidos de dois ou três sem nomes pedem os nomes e aproveitam a próxima mensagem na mesma fonte. Não há seleção arbitrária de municípios. Orientação e agradecimento são atendidos inclusive durante essa pendência, sem apagá-la. A resposta do backend é preservada na conversa.
- **Interface:** conversa à esquerda e preparação/resultados à direita a partir de 1.024 px, com rolagens independentes e compositor visível; em telas estreitas, painéis empilhados. Botões levam à preparação ou ao resultado dentro da área de análise. A fonte atual tem identificação compacta; o carrossel fica recolhido depois da escolha. “Histórico de análises” permanece acessível desde zero ou um resultado e reabre cálculos em memória sem recalcular. A legenda do mapa acompanha a largura do painel, sem estreitar o canvas por causa da largura total da janela.
- **Permanece:** motor determinístico, confirmação e cálculo explícitos, dados e SPEC intactos, proteção do conteúdo enviado ao provedor, validação de homônimos/períodos e parâmetros metodológicos. Histórico temporário em memória; consultar resultado anterior não restaura opções silenciosamente. A cobertura da arquitetura FN/CFG da SPEC continua parcial.
- **Motivo:** permitir continuação natural após resultados e esclarecer ambiguidades reais, preservando a visibilidade da conversa e o acesso aos cálculos anteriores.
- **Documentação e testes:** README, `CONVERSACAO_INCREMENTO_FN.md`, `SEMANTIC_BRIDGE_ADAPTACOES.md` e Blocos 1/3. Testes de alternativas ancoradas/rejeitadas, municípios pendentes, privacidade e orientação durante pendência; nova jornada `ui_semantic_continuity.py` registrada no executor e CI com provedor simulado. As jornadas existentes mantêm cobertura: histórico passa a ser localizado no topo do painel e a fonte pelo identificador compacto; não dependem mais da apresentação repetida. No teste de resize do mapa, a falha era medir o canvas no tamanho de impressão antes de o `ResizeObserver` retornar à tela; a sincronização agora espera a largura efetiva do canvas, mantendo a tolerância e as verificações anteriores.


### 2026-10-15 · Conversa contextual e resultados com mapas, gráficos e filtros acessíveis

- **Antes:** respostas explicativas antes da escolha da fonte eram substituídas pela apresentação inicial; barras desapareciam acima de 40 territórios e linhas acima de oito. O mapa da base Brasil aguardava um formulário técnico na aba de resultados. Tabelas truncavam em 150 linhas; JSON embutido, checklist territorial duplicado e botões PNG sobrecarregavam a exploração.
- **Agora:** perguntas sobre capacidades, conceitos e agradecimentos recebem o conteúdo correspondente, inclusive antes da fonte e sem consumo do provedor nos casos locais. Barras com rolagem incluem todos os territórios; séries têm páginas de oito, preservando lacunas. Quantitativos de pessoas com FTS confirmado são apresentados como “profissionais”. Tabelas têm filtros por coluna, comparações numéricas, ordenação visual, páginas de 150 e CSV de todo o filtro. A seleção pela tabela só vai à preparação por ação explícita. Retomada de parâmetros continua direta; metadados técnicos ficam no JSON. Removidos formulário da aba Mapa e botões PNG.
- **Mapa Brasil:** a versão íntegra correspondente ao manifesto governado recebe configuração contextual **somente de apresentação**, com SIRGAS2000 e formato decimal da fonte; a premissa ilustrativa e sua origem ficam visíveis e no JSON. O datum original continua não declarado pela fonte. Não se aplica a uploads nem a versões externas diferentes; dados, pré-exame, métodos de distância e opções analíticas não são alterados. Em uploads, a origem pode ser configurada nas opções avançadas da preparação.
- **Permanece:** resultados integrais, valores nulos e precisão original, CSV superior, JSON, impressão e histórico temporário recolhido em “Análises anteriores”. Nenhum arquivo da base ou SPEC foi alterado; nenhum dado é enviado ao provedor de IA. Os controles de invalidação e as notas técnicas já retiradas continuam ausentes.
- **Motivo:** corrigir os fluxos apontados na navegação local e tornar as visualizações previstas no Bloco 3 acessíveis sem parâmetros técnicos nos resultados.
- **Documentação e testes:** README, Blocos 1 e 3; testes de conversa e representação (incluindo mapa automático, restrição de versão e invariância dos cálculos). As jornadas existentes mantêm a cobertura: retomada direta substitui a abertura do antigo painel; JSON exportado substitui o JSON em tela; tabela + reutilização explícita substituem o checklist; ausência dos PNG, impressão e exportações substituem a antiga expectativa de download de imagem. `ui_visibility_diagnostic.py` passa de diagnóstico do defeito a regressão com 180 territórios, filtros, paginação e séries. O manifesto permanece somente leitura.

### 2026-10-15 · Análises anteriores acessíveis na sessão

- **Antes:** o histórico existia apenas internamente; não havia acesso à lista de resultados já obtidos.
- **Agora:** após a segunda análise, o usuário dispõe de **“Análises anteriores”**, painel recolhido por padrão, com títulos, solicitação, período e indicação de qual resultado está em exibição. Pode reabrir um resultado desta sessão diretamente, sem nova chamada ao motor.
- **Permanece:** resultados e parâmetros continuam temporários e apenas em memória; nenhum login ou salvamento persistente. Reabrir não modifica automaticamente os parâmetros, a fonte ou a seleção atual. Resultados de outra fonte podem ser consultados, mas não reutilizados para novas análises. O controle de invalidação **não** foi restaurado.
- **Motivo:** disponibilizar ao usuário a consulta a análises anteriores, sem expor controles internos e sem sobrecarregar a interface.
- **Documentação e testes:** atualização de `Docs/BLOCO1_RESULTADOS_EXPLORAVEIS.md`; jornada `ui_block1_smoke.py` verifica quatro resultados, ida e volta entre eles, ausência de nova requisição e regressão com base sintética e Brasil real.

### 2026-10-15 · `dbaa0bd` · Histórico de resultados e invalidação retirados da interface

*Registro tardio: a mudança foi publicada sem registro. Ela foi confirmada pelo responsável pelo
produto em 15/10/2026, que decidiu mantê-la.*

- **Antes:** a página de resultados exibia o painel "Histórico de resultados", uma lista numerada dos
  resultados da sessão com a situação de cada um ("Válido · vigente", "Válido · histórico não vigente"
  ou "Invalidado") e o botão "Voltar ao resultado anterior". Na distribuição, o painel só aparecia a
  partir do segundo resultado. Cada resultado oferecia "Registrar correção que invalida este
  resultado": com um motivo factual, o resultado ficava INVALIDADO, perdia o CSV e a retomada de
  parâmetros e deixava de ser reaproveitado. Em "Método e limitações" apareciam, entre outras, as
  notas técnicas "Período AAAAMM composto em memória…" e "Identificação territorial: …".
- **Agora:**
  - A página mostra só o resultado atual. Não há lista de resultados nem botão para voltar ao anterior.
  - Não é possível invalidar um resultado pela interface. O JSON de "Método e parâmetros" traz sempre
    `validity: "VALIDO"` e `invalidation_reason: ""`. Os campos continuam no contrato por
    compatibilidade.
  - As duas notas técnicas citadas deixaram de aparecer na tela, mas continuam no JSON exportado.
- **Permanece:** o histórico em memória da sessão continua existindo internamente, e nada é gravado
  de forma permanente. Ele sustenta:
  - o reaproveitamento de cálculo idêntico ("Resultado existente recuperado, sem recalcular.");
  - a ação "Retomar parâmetros deste resultado";
  - a navegação entre competências já calculadas do mesmo pedido;
  - a recuperação de critérios combinados;
  - a indicação de situação do resultado ("válido e vigente" ou "histórico válido · não vigente").
- **Motivo:** simplificação da interface, por decisão do responsável pelo produto.
- **Documentação e testes:**
  - Documentos corrigidos junto com este registro: `Docs/MICROITERACAO_INTERFACE_DISTRIBUICAO_20261015.md`,
    `Docs/BLOCO3_MAPAS_VISUALIZACOES.md` (seção 9) e `Docs/BLOCO1_RESULTADOS_EXPLORAVEIS.md` (atualização final).
  - `ui_conversational_smoke.py` e `ui_block1_regression.py` verificam a ausência do painel, do controle
    de invalidação e das duas notas.
  - Os testes de invalidação pela interface foram retirados em `dbaa0bd`.


### 2026-10-17 · Regularização retrospectiva da iteração visual e do recorte Brasil

Registro retrospectivo dos commits publicados na mesma branch sem atualização simultânea deste documento. Esta regularização não equivale a homologação funcional; os testes de interface e o CI continuam sendo a evidência necessária.

- **cd3b554, 9ed4bd8, eba9952:** simplificação do banner inicial, preservação do contrato de propriedades do componente, redução da altura e ajuste de legibilidade. Permanece a possibilidade de iniciar análise pela conversa e importar dados no fluxo existente.
- **c6acac3, a0ea2d4:** simplificação da identificação visível do resultado e supressão de estado técnico redundante; metadados técnicos permanecem disponíveis para exportação. Não há alteração pretendida de cálculo.
- **b5fa0a6, fd34839:** modo de resultados em largura ampliada com conversa abaixo, retirada de atalhos redundantes e limpeza de importação não utilizada. A navegação do histórico e a execução de análises devem permanecer disponíveis.
- **92863b3, 8a4d631, d7cfa00:** navegação com Início, Tipos de análise expansíveis e Resultados; uso do identificador declarado de cada análise e limpeza de importações. Não se pretende alterar o catálogo de análises nem os contratos analíticos.
- **78b7313, 9e9fd9d:** encaminhamento de pedidos explícitos pelo Brasil inteiro ao recorte nacional governado, com serialização da seleção após proposta conversacional. O objetivo é utilizar os registros nacionais próprios, e não somar registros municipais. A efetividade deste fluxo depende de validação específica com dados reais e jornadas de navegador.
- **911c7f7:** fechamento das duas expressões JSX condicionais do menu de análises (desktop e móvel) que impediam a compilação TypeScript, identificado na execução CI #235.

**Escopo preservado:** sem alteração deliberada dos arquivos de dados, motor determinístico, regras de cálculo ou especificação de implementação. **Pendências de validação:** build frontend, governança, jornadas de navegador e seleção do agregado nacional na interface. A regularização documental não substitui essas verificações.


### 2026-10-17 · Refinamento de navegação e persistência explícita da sessão

- **4d8fc5f:** menu Histórico de análises recolhe ao clicar fora, pressionar Escape ou selecionar análise anterior; preserva a consulta sem recálculo.
- **0b7d93f:** bordas azuis e contraste reforçado no painel de conversa, cabeçalho, barra de ferramentas e histórico; somente apresentação.
- **a709296, ca13784:** opção Nova análise restaurada nos menus desktop e móvel, com confirmação e aviso de que o histórico existe apenas na sessão. Nova análise limpa a seleção e o resultado em exibição, preservando fonte e histórico da sessão; não encerra sessão nem altera cálculos.
- **df0e491:** exportação CSV e impressão/PDF em evidência, aviso de que o histórico é temporário; o botão JSON foi removido da barra principal e sua função técnica deslocada para opções avançadas, preservando rastreabilidade e testes existentes.
- **bf1def0:** roteiro de navegador atualizado para acessar a exportação técnica na área avançada; preserva conferências de seleção visual e identificadores do resultado.

**Validação:** sujeita ao GitHub Actions no HEAD posterior a este registro. Nenhuma alteração deliberada no motor determinístico, nos arquivos nacionais/municipais ou nos contratos de cálculo.

### 2026-10-17 · CI #252 — manutenção das jornadas após recolhimento do histórico

- **d4ae485:** no teste de Bloco 1, reabre o histórico após a seleção anterior, preservando a asserção de que o item em exibição fica desabilitado, a contagem de resultados e a ausência de recálculo. O fechamento automático do menu permanece funcional.
- **ea230b0:** no teste de regressão, corrige a referência inexistente `board` para o localizador `result` já definido; mantém o teste da exportação técnica JSON e dos metadados.
- **Diagnóstico:** CI #252 (run 39074064405) apresentou duas falhas de histórico no mesmo roteiro (dados sintéticos e Brasil real) e uma falha por `NameError` em roteiro de regressão. Backend, dados reais, frontend, interface conversacional e governança haviam passado.
- **Escopo:** somente testes de navegador e este registro; nenhum cálculo, dado, contrato ou código de interface foi modificado. **Resultado:** pendente de aprovação do CI subsequente.

### 2026-10-17 · Contrato de testes de interface por comportamento

- **63365ba, 1977f2d:** adicionados identificadores estáveis (`data-testid`) aos controles de nova análise, confirmação, exportação CSV, impressão/PDF, opções técnicas e histórico. Os rótulos acessíveis permanecem disponíveis e a lógica de produção não foi alterada.
- **8a62496, 2486b14:** jornada Playwright estendida para confirmar fechamento do histórico por clique externo e cancelamento de nova análise sem recálculo nem perda do resultado; o botão é localizado dentro da navegação desktop. Permanecem as asserções de reabertura, contagem de linhas e não recálculo.
- **Diretriz permanente:** alterações de interface exigem identificar roteiros Playwright afetados, preservar asserções funcionais e acrescentar cobertura para novos comportamentos. Preferir seletores acessíveis e identificadores estáveis, sem afrouxar os critérios de aceite apenas para obter CI verde.
- **Validação:** aguarda execução do CI no HEAD desta iteração; não declarar aprovação antes de verificar os jobs.


### 2026-10-17 · CI #263 — contenção de largura intrínseca na interface integrada

- **7bde790:** CSS da área integrada ajustado para permitir encolhimento de componentes flexíveis, cartões e textos extensos, sem ocultação global de conteúdo.
- **Comportamento: sem alteração —** correção exclusivamente de apresentação responsiva; não modifica navegação, cálculos, contratos analíticos, dados, sessão ou personagem.
- **Evidência:** CI #263 (run 39084993288) aprovou backend, dados-reais, frontend e ui-conversational, mas ainda reprovou ui-block1 por transbordamento horizontal em quatro roteiros. A correção CSS foi insuficiente e exige diagnóstico de elemento excedente antes de nova intervenção.
- **Governança:** o job reprovou pela ausência deste registro no commit 7bde790; esta entrada regulariza a rastreabilidade documental sem afirmar que a regressão visual foi resolvida.


### 2026-10-17 · Diagnóstico dirigido de transbordamento no CI #264

- **2a57a06:** instrumenta a asserção já existente de largura em `ui_integrated_workspace.py` para incluir no erro o tamanho da página e os primeiros elementos que ultrapassam a janela, com coordenadas e dimensões. A condição de aprovação permanece exatamente a mesma.
- **Comportamento: sem alteração —** somente diagnóstico de teste Playwright; nenhum componente de produto, regra, dado ou cálculo foi modificado.
- **Motivo:** CI #264 manteve as quatro falhas de largura em `ui-block1`, apesar da correção CSS anterior. A evidência de qual elemento transborda é necessária para uma correção direcionada.
- **Validação:** aguardando logs do CI do novo commit; não declarar correção visual antes da nova evidência.


### 2026-10-17 · CI #266 — correção localizada da barra de visualizações

- **863d178:** o Playwright identificou viewport 390 px, largura da página 403 px e botão `Tabela` até x=403; a barra de abas `Mapa / Gráficos / Tabela` era `inline-flex` sem quebra. Passou a usar largura disponível e quebra de linha, preservando rótulos, seleção, papéis acessíveis e conteúdo das visualizações.
- **Comportamento:** a barra de visualizações passa a quebrar linhas em telas estreitas; não altera o cálculo, as representações, os dados, os contratos analíticos nem o personagem.
- **Limite:** SVGs e tabelas largas são conteúdo interno a examinar nos testes; não foram escondidos por `overflow-x:hidden` global nem houve redução das asserções.
- **Validação:** pendente de CI no commit que inclui esta entrada.


### 2026-10-17 · Respostas textuais na etapa de seleção de fonte

- **563af9d, 8152ff0:** a escolha explícita `Dados do Brasil` e equivalentes restritos passa a acionar o mesmo `chooseBrazil` utilizado pelo botão; pedidos explícitos de importação acionam o seletor existente. O roteamento ocorre somente enquanto não há fonte escolhida. O texto original permanece no contexto da sessão.
- **Comportamento:** respostas diretas à pergunta sobre a fonte deixam de ser tratadas como solicitações analíticas ambíguas. Solicitações de análise abertas continuam submetidas ao interpretador existente.
- **Escopo:** nenhum motor, regra analítica, base, SPEC ou SVG alterado. As demais simplificações da jornada (comparabilidade governada, etapas e apresentação de comparações) não foram implementadas por estes commits e exigem verificação específica.
- **Validação:** aguardando TypeScript, testes e CI do HEAD que inclui este registro; não declarar conclusão integral da iteração.


### 2026-10-17 · CI #271 — corrida do diálogo de privacidade após revogação de sessão

- **921c113:** em `ui_investigation.py`, após o encerramento da sessão pela API, o diálogo de privacidade pode surgir entre a consulta `is_visible()` e o clique em Resultados. O teste agora limita a tentativa de clique a 2,5 s e só tolera seu timeout quando o diálogo obrigatório realmente está visível; caso contrário, propaga a falha original.
- **Comportamento de produto: inalterado.** A privacidade continua bloqueando cliques no conteúdo de fundo; o teste exige aviso de sessão expirada, aceite explícito e limpeza dos resultados anteriores. Não usa `force=True`, não desabilita o diálogo nem remove asserções.
- **Validação:** aguardar o CI do HEAD; a correção elimina somente a corrida do roteiro e não implica aprovação antecipada da suíte.


### 2026-10-17 · Conversa contextual e compositor inferior

- **30b728a:** remove da apresentação a transcrição expansível da conversa; preserva mensagens na memória da sessão e move alternativas de esclarecimento da resposta atual para o contexto visível, sem depender da transcrição. O histórico de análises permanece separado e acessível.
- **d1bce10:** a investigação ocupa ao menos a altura disponível, com compositor ancorado na parte inferior quando há pouco conteúdo, e caixa de digitação contornada em verde alinhado à identidade do banner. A posição sticky existente é preservada na exploração de resultados.
- **Escopo:** interface conversacional e CSS; motor, dados, SPEC, personagem e API analítica inalterados.
- **Limites:** não automatiza confirmações metodológicas nem substitui a preparação por um novo fluxo progressivo; essas mudanças exigem implementação e testes específicos. Validação de CI pendente.

- **d53bfc1, c5ade11:** roteiros de navegador atualizados para exigir ausência do histórico conversacional visível e continuar testando a continuidade semântica, escolhas contextuais, resultados e limpeza de sessão. Nenhuma asserção analítica foi retirada.


### 2026-10-17 · Preparação governada e etapa focalizada

- **b0f9044:** a confirmação de comparabilidade para comparação/ranking é inferida apenas quando a base brasileira é curada, municipal, com período único selecionado, unidade de contagem, quantitativo, população e território associados e denominador certificado pelo perfil curado. Em outros recortes ou arquivos importados, permanece a confirmação explícita. O motor continua validando o pedido.
- **64e0b29:** a seleção de período em operações de competência única é uma etapa focalizada na preparação conversacional da base curada, com retorno explícito à escolha. Os parâmetros e execução só aparecem após essa escolha; não são empilhados junto ao seletor.
- **Comportamento:** redução de confirmações redundantes apenas sob metadados governados e redução da rolagem acumulativa na etapa de período; nenhuma operação estatística, arquivo de dados, SVG, API ou SPEC alterados.
- **Limitações:** ainda falta simplificar integralmente todas as etapas e a apresentação comparativa em linhas distintas. O CI e a inspeção visual do HEAD são necessários antes de considerar estes ajustes aprovados.


### 2026-10-17 · Etapas ativas navegáveis na investigação

- **beb0412:** a área principal da investigação passa a exibir uma etapa por vez: seleção de territórios, preparação ou resultados. As etapas são acessíveis por botões com `aria-current="step"`; a etapa de resultados fica indisponível antes de haver resultado ou execução. O estado de parâmetros e seleção continua no componente pai, sem descarte ao navegar.
- **288f5da:** os comandos conversacionais restritos de navegação ("territórios", "preparação", "resultados", "voltar", "avançar") usam o mesmo estado dos botões, sem reinterpretar os comandos como análises ou recalcular dados.
- **d31f32c:** a navegação global para Resultados e a chegada de um resultado sincronizam a etapa ativa; a última resposta do agente acompanha preparação ou resultados.
- **Governança:** nenhuma alteração em algoritmos, bases, APIs, regras de validação ou exportação. A UI deixa de renderizar simultaneamente os três painéis; isso pode exigir atualização de testes de navegação que pressupunham o empilhamento anterior. Testes de CI e inspeção visual ainda pendentes.


### 2026-10-17 · Rastreabilidade complementar exigida pelo CI #290

- **648fb62** — Comportamento: a escolha do período na base curada torna-se uma etapa focalizada; informações de outras etapas deixam de ser exibidas simultaneamente.
- **f2595cf** — Comportamento: a tabela passa a admitir apresentação vertical dos registros comparados, sem alterar os dados exportados.
- **eef02d6** — Comportamento: a apresentação vertical é habilitada para a operação de comparação territorial.
- **b99948a** — Comportamento: a resposta atual do agente acompanha a preparação ativa, sem exigir rolagem até o rodapé.
- **82bc86e** — Comportamento: sem alteração — correção de fechamento JSX da resposta atual para restabelecer compilação.
- **Validação:** o CI #290 revelou erro de compilação JSX e quatro commits sem registro. As correções foram publicadas; aprovação depende da nova execução do CI.

- **2190e59** — Comportamento: sem alteração — remoção de efeito de rolagem que ainda referenciava o histórico visual já retirado; corrige erro TS2304 identificado no CI #292.

### 2026-10-18 · Inicialização da interface após CI #294

- **280f89d** — Comportamento: sem alteração — corrige a ordem de inicialização de `curatedComparisonReady` em `App.tsx`, posicionando-a antes do uso de `semanticOptions()` nas dependências de efeito avaliadas durante a renderização. Evita acesso à variável antes da inicialização e permite que o diálogo inicial de privacidade seja montado.
- **Diagnóstico:** no CI #294, backend, dados reais, compilação frontend e governança passaram; todos os roteiros Playwright falharam antes de começar, aguardando `Li e concordo`. A falha de renderização é consistente com a referência antecipada observada no código. A correção deve ser confirmada por nova execução de navegador; não se alteraram testes para contornar a falha.

### 2026-10-18 · Bateria de estabilização da navegação progressiva

- **0be6576** — Comportamento: a última resposta do agente permanece visível também na etapa Territórios. Preserva o contexto conversacional quando o usuário alterna entre as etapas, sem reintroduzir o histórico acumulado.
- **64db942, 42d4009, 666ba63, 0481a62, 29ed5a2** — Testes: adequação inicial dos roteiros Playwright para seleção territorial em etapa própria e histórico visual removido. As asserções de seleção e dados continuam.
- **aec647d, 223e393, 7c7d0e, a29a7e4, 08e84d3** — Testes: retorno explícito à etapa Preparação antes de configurar ou executar; substituição de navegação legada pela etapa numerada.
- **bb94ef8, 5417716, 7a33cd8, 14f39e8** — Testes: controles técnicos de dados importados e critérios são acessados pela etapa Preparação; a seleção compartilhada é verificada na etapa Territórios.
- **c9ceb01** — Testes: em base brasileira governada, a confirmação manual de comparabilidade não deve aparecer; a execução continua exigindo resposta analítica válida.
- **402c690** — Testes: comentário esclarece que bases importadas continuam exigindo declaração explícita de comparabilidade.
- **Garantias:** nenhum motor analítico, dado original, regra de pré-exame, API ou SPEC foi alterado. Os testes mantêm verificações de valores, quantidade, seleção, execução e identidade de resultados. A aprovação depende de execução CI completa, inclusive testes de navegador.

- **1fccd12** — Teste: valida reseleção territorial após abrir explicitamente a etapa Territórios e ausência da confirmação manual na base oficial governada.
- **c1bbc5c** — Comportamento: sem alteração — inclui `data-testid="comparison-territory-row"` nas linhas verticais da comparação, permitindo testes sem dependência da estrutura HTML visual.

- **8d52c50, 6e58f4b** — Testes: preservam o rótulo específico das condições avançadas para arquivos importados; a navegação até a etapa Preparação continua explícita. Não se altera o requisito de confirmar coordenadas importadas.

- **79e7daa** — Teste: verifica explicitamente três territórios em registros visuais separados na comparação, além da identidade e dos valores retornados pelo motor.

- **387c746** — Comportamento: a abrangência territorial, parâmetro contextual de fonte, permanece acessível durante a etapa de escolha de período. Corrige o bloqueio de navegação ao alternar base municipal/nacional identificado no teste conversacional do CI #322, sem exibir os demais parâmetros técnicos antecipadamente.

- **60d596d** — Teste: confirma que a descrição curada e o botão de cálculo surgem após a seleção de competência; a escolha de múltiplos períodos usa a navegação explícita de volta e avanço. Corrige expectativa de empilhamento no teste conversacional identificada no CI #324.

- **bc49fa3** — Comportamento: ao trocar de período único para múltiplos períodos, o seletor envia uma única transição `onMultiple(periods)`; o pai já limpa o período único. Evita callbacks conflitantes que poderiam esvaziar a seleção e bloquear Avançar. Detectado na execução conversacional do CI #326; requer validação posterior.

- **d7ff52d** — Teste: após HTTP 200 de análise, aguarda a renderização assíncrona da tabela antes de verificar uma linha; não altera o valor esperado nem o critério de aceitação. Falha de sincronização detectada no CI #328.

### 2026-10-18 — Regularização histórica da tentativa de simplificação revertida

Os commits abaixo foram publicados durante uma tentativa de simplificação da interface, posteriormente **integralmente revertida** pelo commit `40504a3761e739b6d4cf61c656fe4b95ed9c8c92`. Esta entrada registra o histórico exigido pela governança, **não reintroduz as mudanças**. O estado dos arquivos de produto e testes após a reversão corresponde exatamente à árvore da versão estável `5c40232fabbb4e266fdb5911e5aee0afe3a5f08d` (CI #331 aprovado).

- `ff7d023`: unificação experimental das etapas Territórios e Preparação; revertida.
- `68f69be`: redirecionamento experimental dos comandos territoriais; revertido.
- `9d3c7cf`: remoção experimental de confirmações de comparabilidade da interface; revertida.
- `15fba0d`: reformulação experimental de textos e abrangência territorial; revertida.
- `3575484`: ampliação experimental da tipografia operacional; revertida.
- `9678d22`: exibição condicional experimental do formato numérico; revertida.

**Situação atual:** nenhuma dessas alterações permanece no produto. A reversão mantém as regras analíticas, os testes e os dados do baseline aprovado. O presente commit altera exclusivamente este registro documental.
