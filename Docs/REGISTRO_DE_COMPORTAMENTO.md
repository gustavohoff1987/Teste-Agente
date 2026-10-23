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
