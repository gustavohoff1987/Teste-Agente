# Conversação experimental — incrementos FN (atualizado em 22/10/2026)

Esta implementação é **parcial** e incremental. A referência normativa continua
sendo `IMPLEMENTATION_SPEC.md` v1.2.4, especialmente §8.5, Parte 6 e Parte 14.
Nenhum dos contratos FN abaixo foi declarado integralmente atendido.

## O que foi incorporado

| Contrato | Incremento executado | Ainda não implementado |
|---|---|---|
| FN-INT-01 | Distingue conversa, pergunta sobre o agente e proposta analítica; identifica capacidades explicitamente coordenadas e admite candidatas ancoradas para leituras concorrentes, sem escolher arbitrariamente uma delas | LeituraMinima integral com funções coexistentes, dados conversacionais, triagem nominal completa, tipagem de todos os trechos |
| FN-INT-02 | Modelo propõe capacidade/indicador ou até cinco candidatas; cada alternativa exige âncora literal no pedido atual. Slots de período, categoria e território continuam ancorados; nomes municipais são resolvidos localmente após validar a capacidade. Pendência simples de nomes admite continuação na mesma fonte | InterpretaçãoOperacional completa, múltiplos entregáveis, todas as associações de pendências/linhas e regras de admissibilidade |
| FN-INT-03 | Perguntas padronizadas para capacidades concorrentes, indicador da distribuição, período/categoria não confirmados e município faltante. Escolha estruturada prepara a análise localmente quando há base; demais escolhas preparam rascunho | Seleção completa de formas CFG-DOC/TPL-04, cobertura integral CFG-AMB/CFG-OPC e validação V-16 |
| FN-META-01 | Formas PT literais com âncoras DOC: para densidade, distância e agregação; catálogo conferido contra o Anexo A; EN bloqueado pela autorização APT-20261016. Orientações legadas continuam locais | Seleção contextual de todas as formas, consultas integrais a C-13 e V-16 integral |
| FN-INT-04 / CAP-SIN-01 (parciais) | Seleção e parâmetros verificados por sessão; leitura de densidade, quantitativos e comparação por referência ao resultado do backend; segmentos copiados com caminhos e relações já calculadas; preparação explícita de comparação faltante; desde 26/10/2026, na página única, o gestor de diálogo com explicação verificada do resultado do gráfico e a redação pelo Gemini com marcadores e validador de saída ([diálogo governado](DIALOGO_GOVERNADO.md)) | Síntese analítica abrangente das demais capacidades, múltiplos entregáveis, livre paráfrase metodológica (não autorizada; proposta P-B) |

## Fronteiras preservadas

- O Gemini **não executa** operações e não recebe arquivos, linhas ou nomes de
  colunas; a proposta continua preliminar e sujeita ao pré-exame Python.
- Diante de pedido explicitamente duplo como “densidade e quantitativos”, o
  sistema pede uma decisão, sem iniciar análise múltipla automaticamente.
- Perguntas e rótulos são oriundos de um catálogo do backend. Escolher uma
  alternativa estruturada com base disponível envia a escolha explícita ao
  resolvedor Python e **apenas prepara** a análise. Sem base, ou em perguntas
  legadas sem operação estruturada, preenche o rascunho da mensagem. Nenhuma
  alternativa calcula resultados ou confirma premissas metodológicas.
- O histórico textual enviado continua limitado aos textos escritos pelo usuário; a sessão guarda também intenção, referente documental e resultados verificados, sem enviar seus dados ao provedor.
  Períodos e categorias retomados passam novamente pela validação de valores
  da base. Solicitações novas sem anáfora explícita não herdam esses valores.
- Perguntas diretas sobre o funcionamento do agente são respondidas localmente,
  sem consumir quota da API Gemini, inclusive em modo degradado ou durante uma
  pendência de nomes de municípios. A pergunta de orientação não apaga essa pendência.
- Não foram adicionados planejamento de várias análises (FN-ORQ-01), execução automática nem alterações ao motor de cálculo. A leitura de resultados e sugestões têm o escopo parcial registrado em [Evolução conversacional](EVOLUCAO_CONVERSACIONAL_20261016.md); não equivalem à implementação integral de FN-INT-04/CAP-SIN-01.

## Continuidade e ambiguidade material

O prompt deixou de exigir “no máximo uma capacidade”. O campo opcional `candidates`
admite até cinco pares de operação/indicador, com âncoras na mensagem sanitizada
atual. A ausência do campo mantém compatibilidade com a resposta única. O Python
valida o esquema, as enumerações, a compatibilidade do indicador e as âncoras;
rejeita alternativas sem sustentação literal. Candidatas repetidas são deduplicadas.
Havendo duas ou mais leituras diferentes, `AMBIGUIDADE_MATERIAL` apresenta escolhas;
o aplicativo não escolhe uma silenciosamente. Isso implementa parte de FN-INT-01/02,
CFG-AMB e CFG-OPC, sem declarar cobertura integral desses contratos.

A escolha também funciona antes da primeira análise, sem seleção territorial
prévia. Na página única (22/10/2026), o indicador proposto ou escolhido vira um
pedido ao gráfico; antes dos dados, fica guardado até a escolha da fonte e não é
perdido durante a inspeção dela.

Após validar a capacidade, o Python cruza a mensagem original com o catálogo
territorial local. Os nomes e IDs resolvidos não são obtidos do provedor nem
enviados a ele. Por exemplo, “coloque Manaus e Tefé lado a lado” pode propor
comparação e preparar esses dois municípios. “Agora vamos analisar comparativamente
no município de São Paulo” distingue a cidade do estado homônimo e pergunta com
qual outro município comparar. A próxima mensagem pode completar os nomes.

Na base oficial, desde 19/10/2026 (fonte estadual de médicos únicos), a gramática local também marca estados
como objeto da análise: “Quantos médicos havia em Minas Gerais em junho de 2024?”, “estado de São Paulo” e
“estados da Região Norte”; anos (“em 2024”) e intervalos (“entre 2014 e 2024”) viram as competências da base
nesses anos, e “número de médicos” indica quantidade. “Municípios de Minas Gerais” continua marcando os
municípios do estado. O nome de estado que também é de município (“a densidade de São Paulo”) gera a pergunta
“estado de São Paulo” ou “município de São Paulo”, com a análise pendente para a resposta; nada é escolhido em
silêncio, e nada é calculado ([abrangência territorial](ABRANGENCIA_TERRITORIAL.md), seção 5.3). Anos e
intervalos de anos valem também nas bases importadas: as competências AAAAMM do ano ou, num período anual, o próprio
ano; sem competência no ano, a conversa pede outra.

“Analise dois municípios também”, com uma análise já selecionada, informa uma
quantidade, sem autorizar escolher quais municípios. O sistema pede os nomes e
prepara a seleção quando forem fornecidos. A pendência pertence à fonte/versão;
trocar entre recortes nacional e municipal da mesma base Brasil não a perde, mas
outra fonte não a reutiliza. Homônimos, termos de recorte não reconhecidos e
períodos indisponíveis continuam gerando esclarecimento. A gramática local é
limitada; isso não equivale a compreender qualquer formulação ou orquestrar vários
pedidos automaticamente.

## Conversa no gráfico (página única, desde 22/10/2026)

Na página única de análise, a conversa mexe no gráfico de bolhas: o pedido volta como o comando `painel`, que diz
à tela o que mostrar. A conversa **interpreta e nunca calcula**: os números vêm do motor, quando a tela aplica o
comando (`/api/painel`, [painel integrado](PAINEL_INTEGRADO.md)). O código está em `backend/conversa_grafico.py`.

### Quando vale

As três rotas da conversa (`POST /api/exploration/interpret`, `/api/llm/interpret-context` e `/api/llm/interpret`)
reconhecem a página única pela chave `painel_familia` em `options`, mesmo nula. Sem essa chave, o caminho anterior
continua igual, e a resposta só ganha o campo `painel` equivalente quando ele existe (veja "Fora da página única").

O estado do gráfico chega em `options`, e o pedido seguinte parte dele:

| Chave | Conteúdo |
|---|---|
| `painel_familia` | `distribuicao`, `espacial`, `tendencia`, `rotatividade` ou nula |
| `painel_indicador` | `densidade` ou `quantidade` (também valem `comparison_indicator`, `temporal_indicator` e `exploration_indicator`) |
| `painel_nivel` | `estados`, `municipios` ou, desde 24/10/2026, `brasil` (o Brasil como unidade) |
| `painel_municipios` | `{"todos", "estados", "ids"}`: os municípios no gráfico (sem ela, valem os `territory_ids`) |
| `painel_competencia` / `period_filter` | a competência à vista |
| `painel_janela` / `period_filters` | a janela da tendência |
| `painel_referencia` | ids da referência da análise espacial |
| `painel_condicoes` | condições em vigor, no formato de `painel.condicoes` |
| `painel_vista` | vista do desenho em exibição: `grafico`, `mapa` ou `lado` (desde 23/10/2026) |
| `painel_mapa_disponivel` | `true` ou `false`: se o mapa pode mostrar a análise agora, como a área informou (desde 23/10/2026) |
| `painel_motivo_sem_mapa` | o motivo informado pela área quando o mapa não está disponível (desde 26/10/2026), para o gestor de diálogo responder "o que estou vendo no mapa?" |
| `painel_resumo` | a frase-resumo verificada do motor, como a área a mostra (desde 23/10/2026); traz valores da base e não entra nem no contexto da conversa |
| `rotulos` | nomes das unidades nas planilhas: `{"unidade": {"singular", "plural", "genero"?}, "grupo": {...} ou null}` |
| `territory_ids`, `exploration_operation`, `conversation_today` | como antes |

Desde 26/10/2026, as rotas da página única recebem também, fora de `options`, a memória da conversa (`conversa`: a pergunta
de esclarecimento sem resposta, a memória da última resposta e os estados anteriores do gráfico) e o resultado em exibição
(`displayed_result_id`, lido da sessão com a integridade conferida). Elas servem ao gestor de diálogo
([diálogo governado](DIALOGO_GOVERNADO.md)), que responde antes da gramática; nada delas vai ao provedor de IA.

Antes do pré-exame e do intérprete, as chaves `painel_*` e `rotulos` saem das opções (`CONTEXTO` em
`conversa_grafico.py`), e nada delas vai ao provedor de IA; `territory_ids` fica só com municípios (`code:`/`name:`); com
competência e janela juntas, vale a da família à vista; a família vira a operação ativa (`distribuicao` → `density` ou
`counts`, `tendencia` → `temporal`, `espacial` → `spatial`).

### Resposta

- Pedido que mexe no gráfico: `{"handled": true, "executed": false, "painel": {...}, "reply": "..."}`.
- Escolha necessária: `{"handled": true, "executed": false, "clarification": "...", "choices": [{"label", "draft",
  "send": true}], "ambiguity"}`, sem `painel`. Cada alternativa envia o pedido completo, já sem a ambiguidade.
- Pedido que não muda o gráfico (por exemplo, rotatividade sem o identificador individual): só `reply`.
- Resposta do gestor de diálogo (desde 26/10/2026): os mesmos campos (`painel` quando o gráfico muda, `clarification` e
  `choices` quando há escolha, só `reply` quando não muda) e mais `memoria` (o que a tela devolve no pedido seguinte),
  `dialogo` (o ato reconhecido), `explicacao` (segmentos, formas documentais e origem), `acoes` (por exemplo, abrir "Entenda
  esta análise" com termos destacados), `desfazer` (quantos estados guardados a tela desfaz), `modelo_de_resposta` (pergunta
  sem alternativas, como "qual você quer incluir?"), `pedido_original` e, com a redação pelo Gemini, `redacao`
  (`origem`: `GEMINI_VALIDADO` ou `DETERMINISTICA`; `tentativas`).
- Sem comando do gráfico nem ato do diálogo, ou com pergunta de conversa e o Gemini disponível (26/10/2026):
  `{"handled": false}`, e o pedido segue para o intérprete contextual, com o provedor e o cartão do contexto. Sem o
  provedor, a resposta traz `indisponibilidade` (`tipo`, `titulo`, `texto`) e a comunicação cordial, com `degradado: true`,
  em vez de erro.

### Formato do `painel`

Todas as chaves vêm sempre; **nula quer dizer "o gráfico mantém o que tem"**.

| Chave | Valores |
|---|---|
| `familia` | `distribuicao`, `espacial`, `tendencia`, `rotatividade` |
| `indicador` | `densidade` (por 1.000 habitantes) ou `quantidade` |
| `nivel` | `estados` ou `municipios` (a área aceita também `brasil`, o Brasil como unidade, desde 24/10/2026) |
| `municipios` | `{"todos": bool, "estados": [...], "ids": [...]}`; na base do Brasil, `estados` traz o prefixo IBGE da UF (`"15"`); nas planilhas, o valor da coluna-mãe (`"Zambézia"`) |
| `competencia` | `AAAAMM` (ou o período da planilha, como `2024`) |
| `janela` | na tendência, os últimos 4 períodos do ritmo, anual ou semestral, em ordem (desde 24/10/2026; não há janela longa); na rotatividade, os dois períodos da coorte |
| `visao_tendencia` | `mudanca`, `classes` ou `series` |
| `referencia` | `{"membros": [ids]}`; por critério, `{"membros": [], "criterio": {"atributo", "ordem"}}` |
| `funcao` | `comparar`, `juntar`, `ordenar`, `condicoes` ou `exportar` |
| `selecao` | ids de comparar e juntar; estados como `uf:15`, com `nivel` `estados` |
| `ordenar` | `{"atributo": densidade, quantidade, populacao, distancia_km ou variacao, "ordem": desc ou asc, "primeiros": N ou null}` |
| `condicoes` | a lista inteira, combinada com "e": `[{"atributo": densidade, distancia_km, populacao ou quantidade, "operador": <, <=, >, >=, = ou !=, "valor": número}]` |
| `grupos` | `{"tipo": quartis, quintis, decis ou nenhum}` (extensão do contrato: os grupos por posição da distribuição) |
| `vista` | `mapa` ou `grafico` (desde 23/10/2026): a vista do desenho citada junto com o comando; estado visual, que a área aplica sem recalcular (RQ-REP-06) |

Mapeamento das operações atuais: `density` → distribuição com densidade; `counts` → distribuição com quantidade;
`distribution` → distribuição (com `grupos` quando o pedido diz quartis, quintis ou decis); `temporal` → tendência;
`spatial` e `nearest` → espacial; `comparisons` → comparar; `aggregate` → juntar; `ranking` → ordenar; `criteria` →
condições; `rotation` → rotatividade; `report` → exportar.

### Frases reconhecidas

A gramática é local e limitada; frases parecidas também valem, mas não qualquer formulação.

- **Municípios e nível:** "mostre o Pará" e "os municípios do Pará" (nível municípios, `estados: ["15"]`); "mostre
  Manaus e Tefé"; "mostre todos os municípios"; "municípios da Região Norte"; "acrescente Belém" e "tire Tefé" (a partir
  dos municípios do gráfico); "volte aos estados" (`nivel: "estados"`) e "volte aos municípios".
- **Indicador, análise e grupos:** "mostre a quantidade", "a densidade"; "mostre a distribuição", "a tendência", "a
  análise espacial"; "em quintis", "sem os grupos"; "visão Mudança" ou "trajetória" (a visão Trajetória), "classes"
  (a visão Tendência), "séries" e, desde a segunda rodada de 24/10/2026, "série temporal" ou "séries históricas" (a visão
  Série temporal). A resposta usa os nomes da tela ("Visão da tendência: Trajetória.").
- **Competência:** "em junho de 2023"; "em 2023" (com duas competências no ano, a pergunta qual).
- **Período da tendência** (desde 24/10/2026, sem janela longa): os períodos são sempre os últimos 4 do ritmo, anual ou
  semestral, como no campo Período da tela (`janela_do_ritmo`, o mesmo cálculo de `painelModel.janelaDoRitmo`). O ritmo vem
  de "tendência anual", "semestral", "ano a ano", "a cada ano", "por semestre", "a cada seis meses", "série anual de junho"
  e "últimos 3 junhos" (anual, e sempre com 4 períodos); "mostre a mudança anual" (ou "a trajetória anual") abre a visão
  Trajetória, entre o primeiro e o último dos 4. Um período com várias competências e sem ritmo ("de 2021 a 2024", "desde 2022", "nos últimos 4 anos",
  mesmo nas leituras divergentes da AT-34, "todas as competências", "mudança entre junho de 2023 e junho de 2024") vira a
  pergunta do ritmo, com um botão por ritmo que a base tem ("Anual" e "Semestral"); cada botão reescreve o pedido com o
  ritmo no lugar do período. O mesmo vale nas condições, na ordenação, em comparar e em juntar ("os 5 municípios com maior
  densidade anual", "compare Manaus e Tefé ano a ano"). A distribuição e a análise espacial (também a referência e a ordenação pela distância) usam uma
  competência por vez: com um período assim, a conversa pede uma competência ou a tendência anual ou semestral. Na
  rotatividade, as duas pontas citadas são os períodos da coorte.
- **Referência da análise espacial:** "use Belém como referência", "distância até Belém", "a referência é Belém"; "use
  Manaus e Belém como conjunto de referência" (o membro mais próximo). Desde 27/10/2026, a tela leva os nomes à Escolha dos
  territórios como os marcados da Referência, a partir do país, e a base continua a da consulta (sem ela, a seleção prévia);
  como em toda a janela, um município da base nunca é a sua própria referência. "Use como referência o município de maior
  densidade" (critério: abre a Escolha dos territórios na aba Referência com um filtro do atributo citado e, desde
  25/10/2026, o operador do "maior" ou "menor" — "acima de" ou "abaixo de" —, também em "mais/menos populosos" e
  "mais/menos profissionais"; o valor fica com a pessoa, sem valor sugerido: "Abri a Escolha dos territórios com o filtro
  Densidade “acima de” na Referência: preencha o valor e calcule, …"). Nada é escolhido pela posição na ordem: CAP-REF-01 pede
  uma condição de CAP-SUB-01. Antes de 24/10, a lista de candidatos abria nessa ordem; de 24 a 25/10, o "maior/menor" ficava
  sem efeito; de 24 a 26/10, o critério abria o painel Território de referência, com a relação e a delimitação para escolher.
  "Abra a análise espacial" responde "Abri a análise espacial: faça a Escolha dos territórios (a base e a referência) ou diga
  o nome da referência, …".
- **Ordenar:** "os 5 municípios com maior densidade", "os 3 com menor quantidade", "quais os dez mais populosos?",
  "qual município tem a maior densidade?" (o primeiro), "os 10 primeiros", "top 5", "os 5 mais distantes de Manaus".
  Sem o indicador ("os 10 primeiros") ou sem a direção ("ordene pela densidade"), a conversa pergunta. Empates na
  posição de corte também entram.
- **Condições:** "municípios com menos de 1 médico por mil e a mais de 150 km de Manaus" (densidade < 1 e distância >
  150 km, com Manaus como referência); "população acima de 50 mil habitantes"; "quantidade de médicos menor que 2";
  "agora também …" acrescenta às condições em vigor.
- **Comparar e juntar:** "compare Manaus e Tefé", "coloque … lado a lado" (2 ou 3 itens; o município fora do gráfico
  entra nele); "compare o Pará e o Amazonas" (estados, no nível dos estados); "compare esses municípios" (os do
  gráfico); "junte Manaus, Iranduba e Manacapuru", "junte os municípios do Amazonas" (soma dos componentes, com
  possível dupla contagem). Com um nome só ("compare Manaus"), a conversa pergunta o outro ("Com qual outro município
  você quer comparar?") e devolve `pending_operation: "comparisons"` e `pending_ids` com a unidade identificada; a tela
  manda os dois de volta (`conversation_pending_operation` e `conversation_pending_ids`, que não vão ao provedor), e a
  mensagem seguinte só com nomes ("Tefé e Parintins") completa a comparação. Outro comando ou uma pergunta seguem o seu
  próprio sentido.
- **Exportar:** "exporte em CSV", "imprimir", "relatório".
- **Vista do desenho** (desde 23/10/2026), junto com outro pedido: "mostre o Pará no mapa", "onde ficam os municípios
  com menos de 1 médico por mil?", "o mapa da quantidade" e "volte aos municípios no mapa" levam `vista: "mapa"`; "a
  quantidade no gráfico" e "volte ao gráfico com …", `vista: "grafico"`. Com negação ("não no mapa", "sem o mapa") ou
  com as duas vistas no mesmo pedido, a vista não muda. A vista sozinha ("ver no mapa", "volte ao gráfico") é atendida na
  tela, com o motivo da área quando o mapa não está disponível; aqui ela não vira comando, e o pedido segue para o
  intérprete com o provedor, que a devolve como `show_map` ou `show_chart`. "Amapá" não é o mapa.
- **Onde o mapa não mostra a análise** pedida, o comando segue sem a vista, e a resposta diz por quê: nos estados (ou nos
  grupos de uma planilha), que não têm um ponto; numa planilha sem latitude e longitude; na rotatividade e na visão
  Série temporal, que ficam no gráfico; e quando a área já informou que o mapa não está disponível (`painel_mapa_disponivel:
  false`) e o pedido não muda o nível, as unidades, a análise nem a visão. A área confere de novo e mostra o motivo dela.

### Ambiguidades e perguntas

Nada muda no gráfico enquanto há escolha a fazer, e a conversa não escolhe em silêncio. As alternativas vêm do
catálogo local (`CATALOGO_LOCAL`), cada uma com o pedido reescrito:

- nome de estado e de município ("mostre São Paulo": "Estado de São Paulo" ou "SAO PAULO (SP)"; "o Paraná": o estado
  ou cada município PARANA com a sigla);
- homônimos ("Santarém": "SANTAREM (PA)" ou "SANTAREM (PB)"); vale o único homônimo que já está no gráfico, e a
  resposta diz qual, com a sigla;
- "menos de 2 médicos": densidade por mil habitantes ou quantidade;
- direção da ordenação; competência de um ano com várias; leituras de "últimos N anos" (AMB-04), fora da tendência;
- na tendência (e nas funções que a pedem), o ritmo de um período citado sem ele: anual ou semestral (desde 24/10/2026);
- duas análises ou dois indicadores no mesmo pedido; comparar e juntar ao mesmo tempo; quantos grupos por posição.

Também viram pergunta: condições com "ou" (o gráfico combina com "e"); densidade por 10 ou 100 mil e distância em
metros; distância sem referência (fora da análise espacial); estados como referência (não têm um ponto único);
estados e municípios na mesma comparação; mais de 3 itens na comparação; variação fora da tendência; nome que não
está na base ("Não encontrei “Belen” …").

### Respostas

As respostas dizem o que muda no gráfico, sem valores da base: "Mostrei a densidade nos 144 municípios do Pará.",
"Usei BELEM (PA) como referência: o eixo X passa a mostrar a distância em linha reta (km) até ela.", "Ordenei os
municípios pela densidade, do maior para o menor, e destaquei os 5 primeiros; empates na posição de corte também
entram.", "Voltei aos estados: cada bolha é um estado, com a densidade.", "Abri a tendência da densidade, com os últimos 4
períodos anuais (junho de 2021, junho de 2022, junho de 2023 e junho de 2024).". Na base do Brasil, a rotatividade não está
disponível (não há identificador individual), e a resposta diz isso sem mudar o gráfico.

Com a vista citada, a resposta ganha uma frase, conforme a vista em exibição (`painel_vista`): "Passei para o mapa." (ou
"O mapa continua na tela."; lado a lado, "Deixei só o mapa."); "Voltei ao gráfico." quando o mapa estava na tela (lado a
lado, "Deixei só o gráfico."; já no gráfico, nada é acrescentado); sem o mapa, o motivo, por exemplo "Os estados não têm
um ponto no mapa; a análise fica no gráfico. Para ver no mapa, abra os municípios de um estado.", "Sem latitude e
longitude na planilha, não há mapa; a análise fica no gráfico." ou "A visão Série temporal fica só no gráfico.".

### Planilhas de outros países

Planilhas enviadas podem usar outra nomenclatura territorial (distrito, condado, província). A estrutura é a mesma:

- as respostas usam os rótulos da tela (`options.rotulos`): "Mostrei a densidade nos 12 distritos da província X";
  o gênero vem de `genero` ou da terminação da palavra; na base do Brasil, nada muda;
- o grupo é o valor da coluna-mãe, informada no mapeamento pelo papel `grupo_territorial`: "mostre a província X"
  vira `municipios.estados: ["X"]`; "junte os distritos da província X" junta as unidades do grupo. Esse papel vale
  só para a conversa: sai do mapeamento antes do pré-exame. Desde 28/10/2026, a página manda o papel no mapeamento da
  conversa (`mapeamentoDaConversa`, em `paginaUnica.ts`); antes, ele saía também dali, e a conversa não reconhecia o grupo
  pelo nome numa planilha enviada pela página ("Mostre só o condado Costa Ondina" recebia "Não encontrei “Costa e Ondina”
  entre as comunas da base."; agora, "Mostrei a densidade nas 4 comunas do condado Costa Ondina.");
- as unidades citadas pelo nome se resolvem pelo catálogo da planilha (`name:` ou `code:`), sem código IBGE;
- grupo e unidade com o mesmo nome viram pergunta ("Província Nampula" ou "Distrito Nampula");
- não há nível acima das unidades no gráfico: "volte às províncias" explica isso e sugere "mostre a província …". A
  orientação da caixa da conversa diz o mesmo desde 28/10/2026: "Peça mudanças no gráfico citando comunas pelo nome:
  comparar, juntar, usar como referência ou mostrar as comunas de um condado." (antes, "… ou voltar ao nível de condados",
  que a conversa recusava);
- as orientações também usam os nomes da planilha (23/10/2026): "“distritos com menos de 1 médico por mil habitantes”",
  "cada distrito precisa atender a todas", "A referência é um distrito ou um conjunto de distritos: a referência não pode
  ser a base inteira. …". Os exemplos com nomes da base do Brasil ("Manaus", "o Pará") ficam só nela; numa planilha, dão
  lugar às reticências ("“use … como referência”") ou a "“mostre todos os distritos”";
- desde 28/10/2026, também as respostas verificadas (`explicacao.py`) e as do gestor de diálogo (`dialogo.py`) usam os
  nomes e o gênero da planilha, depois da navegação simulada com uma planilha fictícia de comunas e condados: "Empatadas com a
  maior densidade em 2024: …", "As demais: …", "Todas as comunas com valor têm a mesma densidade", "A seleção tem as comunas
  de Alto Vésper e 2 comunas escolhidas uma a uma."; no mapa, "cada ponto é uma comuna, na coordenada informada na planilha"
  (a "sede municipal" fica na base do Brasil); sem gráfico, "me diga quais quer ver: o nome de um condado ou de comunas, ou
  “todas as comunas”."; nos exemplos, "“use como referência a comuna de maior densidade”", "“mostre a tendência dessas
  comunas”", "“mostre as comunas com densidade menor que 1”" e "“as 5 comunas com maior densidade”" (nas recusas de juízo,
  de classe nova e de escolha delegada e no "desfaz" sem mudança). A pergunta de volta, quando a resposta não escolhe uma
  das alternativas, pede "o nome ou “o primeiro”, “o segundo”" (a sigla do estado fica na base do Brasil). Na base do
  Brasil, nada muda.

### Rotas com o provedor

- `/api/llm/interpret-context` na página única: quando o intérprete propõe uma operação, a conversa local relê o
  pedido original com a operação proposta como dica, resolve nomes e competências pelo catálogo local e põe `painel`
  e `reply` no lugar da proposta textual (o campo `exploration` não vem). Uma escolha pendente vem em
  `clarification`, com `code` (`AMBIGUIDADE_MATERIAL`, `AMB-04` ou `ESCOLHA_NO_GRAFICO`), `prompt`, `choices`, `reason`,
  `source: "CATALOGO_LOCAL"` e `answered: false`. A verificação do pré-exame continua na resposta.
- `/api/llm/interpret` (sem base): o `painel` vem só da operação e do indicador propostos; nomes e competências são
  resolvidos depois, com a base.
- **Fora da página única**, as respostas anteriores ganham o `painel` equivalente pelo mapeamento acima (comando
  local, critérios combinados e proposta do intérprete). Pedidos de explicação do resultado não trazem `painel`.

**Privacidade:** a gramática da conversa no gráfico roda antes do provedor e não o chama. Nomes, códigos e competências
são resolvidos só no Python, e o estado do gráfico (`painel_*`, `rotulos`) não entra no resumo técnico. Desde 26/10/2026,
quando o pedido segue ao intérprete com o provedor, vão junto a mensagem triada (territórios da base e períodos ficam;
identificadores e nomes sem evidência viram marcadores) e o cartão do contexto, com a tela e o resultado agregado em
exibição; nunca arquivos, registros, códigos internos ou nomes de campo ([diálogo governado](DIALOGO_GOVERNADO.md)).

## Espaço de trabalho

Desde 22/10/2026, a interface é a página única de análise: no alto, o nome do agente, Nova sessão, Nova análise e Histórico e a fonte dos dados; abaixo, a área de análise com o gráfico; a conversa, numa caixa flutuante sempre na página, com o histórico completo da conversa e o campo de mensagem. Não há preparação nem tela de resultados. Os contratos de interpretação descritos aqui permanecem iguais; a resposta passou a levar também o pedido ao gráfico (campo `painel`). A disposição visual vigente está no [guia da interface integrada](INTERFACE_CONVERSACIONAL_INTEGRADA.md).

## Testes

`test_conversa_grafico.py` cobre a conversa no gráfico: o mapeamento das operações atuais, cada frase do contrato,
o contexto do gráfico, as ambiguidades com os botões (e o pedido de cada botão), uma planilha sintética de distritos
e províncias sem código IBGE, as três rotas e o provedor de IA sem dados da base; a vista do desenho nos comandos
compostos e onde o mapa não mostra a análise; as chaves `painel_vista`, `painel_mapa_disponivel` e `painel_resumo`
fora do pré-exame, do intérprete e do provedor, nas duas rotas; o período da tendência pelo ritmo, sem janela longa, na
tendência e nos pedidos de função (desde 24/10/2026); no job `dados-reais`, as frases com a base versionada.

Os testes `test_dialogue_guidance.py`, `test_conversation_guidance.py`,
`test_llm_context.py` e `test_territorial_selection.py` verificam capacidades
concorrentes, alternativas ancoradas ou rejeitadas, período não confirmado, FAQ
offline durante pendências, resolução local, ausência de dados da base no payload
do provedor, nenhuma execução e recuperação contextual ancorada.

O workflow `.github/workflows/ci.yml` executa backend, build e jornadas de navegador
registradas em `backend/tests/run_ui_checks.py`. Desde 22/10/2026, a jornada
`ui_conversa_grafico.py` usa provedor simulado (suíte `gemini-simulado`) para verificar
o pedido feito antes dos dados, a proposta fora do contrato (2 regenerações e a resposta de
reserva) e a recuperação, a redação conferida, o limite de consultas e a falha temporária
simulados, o histórico visível, a escolha de interpretação em botões, nomes pendentes e a
análise anterior reaberta sem recálculo;
`ui_pagina_unica.py` confere a página em 390 px sem rolagem horizontal. A jornada
`ui_semantic_continuity.py`, que fazia essas verificações nas telas clássicas, saiu
(ver [`backend/tests/legado/README.md`](../backend/tests/legado/README.md)).
Nenhum desses testes faz chamada ao Gemini real; a qualidade e a disponibilidade
do provedor real exigem validação distinta.

Na validação local de 16/10/2026, o provedor configurado interpretou o pedido
comparativo sobre São Paulo; o resolvedor local perguntou qual outro município,
e a resposta “Campinas e Rio de Janeiro” preparou três municípios. É uma
verificação pontual do transporte real, sem comprovar interpretação de qualquer
formulação possível.
