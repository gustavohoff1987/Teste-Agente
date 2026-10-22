# Interface conversacional integrada: a página única de análise

Desde 22/10/2026, a interface é uma página única: uma análise integrada, sem duas telas (decisão do responsável pelo produto
em 22/10/2026: "Eu só quero entrar por aquela linha, por aquele gráfico"). Este documento descreve a estrutura da página, a
fonte de dados, o Histórico, a sessão e a conversa. A área de análise (o gráfico, as famílias, as funções e os Detalhes) é
descrita no documento da área ([página principal: o gráfico de bolhas](PAINEL_INTEGRADO_INTERFACE.md)); o motor do gráfico,
em [painel integrado](PAINEL_INTEGRADO.md).

As telas clássicas saíram do produto: o catálogo de 12 análises, a preparação (categoria, período, abrangência e condições),
os resultados em abas (mapa, gráficos e tabelas), a investigação progressiva e os diagnósticos compostos. O motor
(`/api/analyze` e as capacidades) continua; a página usa `/api/painel`. A seção [O que saiu](#o-que-saiu-em-22102026)
resume a mudança.

## Estrutura da página

1. **Aceite de privacidade primeiro.** O pop-up traz só a declaração ("Declaro que não compartilharei dados pessoais ou
   sensíveis, seja por meio dos arquivos enviados ou das mensagens inseridas no chat.") e "Li e concordo"; depois de uma
   sessão encerrada, o aviso do descarte aparece acima dela. Até o aceite, os botões da fonte e o envio de arquivos ficam
   desabilitados.
2. **Cabeçalho.** O nome do agente ("Agente Diagnóstico Territorial", com o rosto do agente) volta ao topo da página. Ao
   lado, a navegação: **Nova sessão**, **Nova análise** e **Histórico**. Não há "Início" nem "Resultados": a página é
   sempre o gráfico.
3. **Fonte dos dados**, logo abaixo:
   - antes dos dados: **Dados do Brasil** e **Enviar meus dados**, com o modelo de planilha (.xlsx) para baixar;
   - depois: o resumo da fonte, por exemplo "Dados do Brasil · Medicina · jan/2014 a jun/2024" ou, numa planilha,
     "distritos.csv · distritos e províncias · Medicina · 2021 a 2024", com **Trocar** (e **Colunas**, na planilha);
   - "Trocar" mostra de novo as duas fontes. A troca só vale quando a nova fonte fica pronta: até lá, o gráfico continua com
     a fonte em uso, e "Cancelar" desiste;
   - na base do Brasil, "Diagnóstico técnico da fonte" mostra a origem, a versão e a integridade (sem conteúdo).
4. **Área de análise**: o gráfico com os valores do motor, nos estados E0 (antes dos dados) a E4 (funções em uso). Ver o
   documento da área.
5. **Conversa**: a caixa flutuante com o rosto do agente, sempre na página (ver [Conversa](#conversa)).

Uma linha de aviso abaixo da fonte confirma as ações da página ("Dados do Brasil prontos.", "Análise guardada no Histórico.
Nova análise com os mesmos dados.", "Análise reaberta como estava, sem recalcular: …") e some depois de alguns segundos.
No celular (abaixo de 640 px), o cabeçalho e a navegação quebram em linhas, a lista do Histórico ocupa a largura da tela e
a conversa fica ancorada embaixo, sem rolagem horizontal.

## Fonte de dados

### Base do Brasil

"Dados do Brasil" examina a base versionada uma vez, no recorte municipal, com o bloco dos níveis (Brasil e estados), por
`/api/inspect`, como antes. A área recebe a fonte (`FonteDados`: `tipo: "brasil"`, a versão da base, o token da camada
geográfica complementar e os rótulos fixos município/municípios e estado/estados), as competências, a categoria, os níveis e
o catálogo de municípios para a busca. Depois de escolher a base, o gráfico abre nos **27 estados** (E1); nunca nos 5.570
municípios de início.

### Planilha enviada: o painel "Colunas"

"Enviar meus dados" aceita CSV, XLS e XLSX de até 30 MB, de qualquer país. Outro formato é recusado com "Formato não
reconhecido. Selecione um arquivo CSV, XLS ou XLSX.". Um arquivo Excel com várias abas pergunta "Qual aba deseja
utilizar?" antes das colunas. A estrutura é a mesma da base do Brasil; só os nomes se adaptam (distrito, condado, província).

O painel **Colunas** mostra a coluna de cada papel:
- **unidade territorial** (necessária), **código da unidade**, **grupo territorial** (a coluna-mãe: estado, província,
  região), **período** (necessário), **categoria**, **quantidade** (necessária), **população** (para a densidade),
  **latitude** e **longitude** (para a análise espacial) e **identificador individual** (para a rotatividade);
- as colunas reconhecidas por regra conclusiva já vêm escolhidas; as sugestões do `/api/inspect` aparecem no topo de cada
  lista, marcadas "(sugerida)", e nunca são usadas sem a escolha da pessoa (decisão D1 de 19/10/2026). Duas candidatas para a
  unidade (por exemplo, "distrito" e "provincia") deixam a lista vazia até a escolha;
- o grupo territorial é sugerido pelas colunas que o backend reconhece como nível superior (estado, província,
  departamento) depois da escolha da unidade;
- uma coluna representa um papel só: escolhida num papel, ela sai do anterior;
- **O que a quantidade conta?** (pessoas, vínculos de trabalho, postos de trabalho ou outra unidade, descrita);
- **Referencial das coordenadas**, com latitude e longitude: a pessoa informa o referencial em que as coordenadas foram
  coletadas, **SIRGAS 2000** ou **WGS 84** (o WGS 84 desde 22/10/2026, pelo Adendo REF-20261022 da SPEC), e o sistema não
  converte um no outro. "Outro referencial" ou "Não sei" deixam a análise espacial indisponível, com o motivo ("Só os
  referenciais SIRGAS 2000 e WGS 84 são admitidos; com outro, ou sem saber qual é, nada é presumido."). O separador decimal
  das coordenadas só é pedido quando o formato é misto;
- **Nomes**: como se chamam as unidades e os grupos, no singular e no plural, com a sugestão a partir do nome da coluna
  ("distrito" sugere distrito e distritos; "provincia", província e províncias). Os nomes aparecem nos textos da página e da
  conversa: nenhum texto da estrutura diz "município" quando a fonte é uma planilha;
- **O que esta planilha permite**: Distribuição, Análise espacial, Tendência e Rotatividade, cada uma disponível ou
  indisponível com o motivo, pelo pré-exame do backend (`/api/preflight`), refeito a cada escolha. A escolha que se faz no
  gráfico (por exemplo, a referência da análise espacial) não torna a análise indisponível.

**Começar a análise** (ou **Aplicar as colunas**, ao reabrir o painel de uma planilha em uso) passa a planilha à área. Sem a
unidade territorial, o período, a quantidade, o que ela conta ou os nomes, o clique lista o que falta, e nada é pedido ao
motor. A área recebe `FonteDados` com o arquivo (reenviado só ao backend local), o mapeamento confirmado na tela (com o papel
`grupo_territorial`), as premissas escolhidas (`confirmed_roles` com as colunas escolhidas no seletor, `count_unit`,
`custom_count_unit`, `crs` só com `SIRGAS2000` ou `WGS84`, como informado, e `number_format`) e os rótulos (`rotulos: {unidade, grupo}`). No pré-exame e na conversa, que usam os papéis atuais do
backend, o grupo segue em `hierarchy_columns` (nível superior 1), e as colunas escolhidas pela pessoa seguem em
`confirmed_roles`.

## Histórico e sessão

- **Histórico.** Cada análise da sessão guarda o último estado informado pela área ao calcular (`EstadoSalvo`: título,
  definição, resposta do motor e hora). A lista mostra a mais recente primeiro, com "Em exibição" na atual. Reabrir uma
  análise devolve o gráfico como estava, **sem recalcular** (a área recebe o estado em `restaurar`). Uma análise feita com
  outra fonte de dados fica na lista, desabilitada, até a pessoa voltar àquela fonte. O menu fecha com clique fora ou
  Escape, devolvendo o foco ao botão.
- **Nova análise** guarda a análise atual no Histórico e volta a E1 com os mesmos dados. Fica desabilitada antes dos dados.
- **Trocar de fonte** também guarda a análise atual; a área recomeça com a nova fonte.
- **Nova sessão** pede confirmação num diálogo com: **Exportar CSV** (a análise em exibição: um registro por item da resposta
  do motor, com todos os campos em precisão integral; objetos viram colunas "campo.subcampo", e texto que começaria uma
  fórmula leva um apóstrofo), **Imprimir / PDF**, **Continuar nesta sessão** e **Iniciar nova sessão**. Confirmar encerra a
  sessão no servidor e recarrega a página, descartando arquivos, conversa, Histórico e resultados em memória; se o
  encerramento falhar, o diálogo mostra o erro e mantém tudo. Para guardar outra análise, reabra-a pelo Histórico e exporte.
  Nada fica salvo entre sessões.

A sessão temporária, os limites e a revogação continuam como antes (`conversationSession.ts`). O resultado de cada gráfico
entra na sessão do backend (`/api/painel`), para o Histórico e para a conversa saberem o que está na tela. A revisão de
contexto da sessão muda com a fonte em uso.

## Conversa

A conversa fica na caixa flutuante com o rosto do agente, sempre na página: arrastável pelo cabeçalho (mouse, toque e
teclado: setas, Shift acelera e Home volta ao canto), minimizável e sempre dentro da janela; no celular, ancorada embaixo.
Ela mantém os identificadores de sempre (`#assistente`, `#assistant-input`, `latest-reply`). A transcrição fica em memória,
e a última resposta aparece junto do campo de mensagem.

**Abertura.** Antes dos dados, a caixa fica aberta e mais larga, perguntando "O que você quer analisar? Prefere começar com
os dados do Brasil ou enviar os seus?", com os botões **Dados do Brasil** e **Enviar meus dados**. Depois, ela fica compacta,
com uma orientação curta para cada etapa: "Escolha no gráfico quais estados abrir, ou me diga quais municípios quer ver."
(na planilha, com os nomes escolhidos, por exemplo "quais províncias abrir, ou … quais distritos"), e, com as unidades na
tela, exemplos de pedidos ("mostre o Pará", "use Belém como referência", "compare Manaus e Tefé").

**Escolha da fonte pela conversa.** "Usar dados do Brasil" e "enviar meus dados" fazem o mesmo que os botões, sem o provedor
de IA.

**Antes dos dados.** Perguntas sobre o agente, a privacidade e os conceitos ("Como se calcula a densidade?") e sobre o
conteúdo da base do Brasil continuam respondidas localmente. Um pedido analítico feito antes da escolha fica guardado: quando
a base fica pronta, ele é interpretado de novo, já com a base, e os municípios citados nele vão para o gráfico.

**Com os dados.** Cada pedido vai primeiro ao intérprete local (`POST /api/exploration/interpret`); sem resposta local, ao
intérprete contextual (`POST /api/llm/interpret-context`). A conversa não calcula nada:
- quando a resposta traz o campo **`painel`** (família, indicador, nível, municípios, competência, janela, visão da tendência,
  referência, função, seleção, ordenação e condições), ele vira um **pedido para a área**, com um id novo a cada comando. Só os
  campos válidos entram, e os não citados (`null`) ficam de fora;
- "Mostre o Pará", "use Belém como referência", "compare Manaus e Tefé", "volte aos estados" e os demais comandos mudam o
  gráfico; os números vêm do motor, pedidos pela área;
- o **contexto** de cada pedido sai do que está no gráfico (`ContextoDoGrafico`): em `options` vão `territory_ids` (as
  unidades na tela, só as do catálogo territorial; com todos os municípios ou nos estados, nenhuma), `exploration_operation`
  (a família: distribuição → `density` ou `counts`, conforme o indicador; espacial → `spatial`; tendência → `temporal`;
  rotatividade → `rotation`), `exploration_indicator`, `comparison_indicator` e `temporal_indicator` (o indicador),
  `period_filter` (a competência) ou `period_filters` (a janela da tendência), `painel_familia` e a data local do navegador
  (`conversation_today`, para "últimos N anos"). O estado do gráfico vai também como está: `painel_indicador`,
  `painel_nivel`, `painel_municipios` (a escolha das unidades, inclusive "Todos"), `painel_competencia`, `painel_janela` e
  `painel_referencia`. Antes de o gráfico informar o contexto, `painel_familia` vai nulo: a conversa responde no formato
  do gráfico, nunca com orientações das telas que saíram. Numa planilha, vão também as escolhas das colunas e os nomes da
  unidade e do grupo (`rotulos`); essas chaves ficam fora do que vai ao provedor de IA;
- os comandos da conversa incluem os grupos da distribuição ("divida em quintis", "sem os grupos") e a referência por
  critério ("a de maior densidade como referência"): a lista de candidatos abre nessa ordem, e usar o primeiro ou outro é
  escolha da pessoa;
- **ambiguidades** continuam com alternativas em botões (`CATALOGO_LOCAL`), e nada é calculado. Escolher uma alternativa
  reinterpreta o pedido com a escolha; se a resposta não trouxer o campo `painel`, a operação escolhida vira a família ou a
  função equivalente (densidade e quantitativos → Distribuição com o indicador; evolução → Tendência; espacial e referência
  mais próxima → Análise espacial; comparação → Comparar; agregação → Juntar; ranking → Ordenar; critérios → Condições;
  relatório → Exportar);
- pendências da conversa continuam: "Compare Manaus" pergunta o outro município, e a resposta seguinte completa o pedido;
  a direção de uma ordenação é perguntada, nunca presumida;
- "agora a tabela" responde que a tabela fica em Detalhes, abaixo do gráfico; "mostre no mapa" responde que o mapa não faz
  parte da página; nada é recalculado;
- "volte ao resultado anterior" reabre a análise anterior do Histórico, da mesma fonte, sem recalcular;
- perguntas sobre o que está na tela usam o resultado do gráfico guardado na sessão (`displayed_result_id`).

**Continuidade (desde 21/10/2026).** Um pedido sem territórios usa os que estão no gráfico, e a resposta diz quais. Um
pedido só com o período ("E nos últimos 5 anos?") continua a análise. "Últimos N anos" e "último ano" (AT-34) são contados
até o último período da base e até hoje, pela data local do navegador: quando as duas contagens dão as mesmas competências,
o período é aplicado; quando divergem, a conversa oferece as duas leituras como alternativas, sem escolher. Essas
continuações são resolvidas no backend, sem o provedor de IA. A interpretação conta com exemplos da
[biblioteca conversacional](BIBLIOTECA_CONVERSACIONAL.md), internos e invisíveis na tela.

**Privacidade.** Nenhum dado, arquivo, nome de campo ou valor da base vai ao provedor de IA. A planilha é reenviada só ao
backend local; o contexto do gráfico vai ao intérprete local, e o provedor recebe apenas o pedido sanitizado e estados
enumerados. Sem o provedor, os pedidos sobre o gráfico, a escolha dos dados e as respostas locais continuam disponíveis; a
caixa avisa que as perguntas livres estão indisponíveis.

## Exportação

As exportações da análise ficam na função **Exportar** da área (CSV com precisão integral, avaliabilidade e motivo;
Imprimir/PDF; método e parâmetros). O diálogo de Nova sessão oferece o CSV da análise em exibição e Imprimir / PDF. Não há
exportação consolidada de todas as análises da sessão.

## O que saiu em 22/10/2026

| Saiu | Onde fica agora |
|---|---|
| Catálogo de 12 análises (carrossel) | Famílias e funções da área; a conversa continua aceitando os pedidos |
| Preparação (categoria, período, abrangência territorial, condições, "Calcular e mostrar resultado") | Escolhas dentro da área (indicador, competência, municípios, funções); colunas da planilha no painel "Colunas" |
| Resultados em abas (Mapa, Gráficos, Tabela), cabeçalho do resultado e visuais por análise | Gráfico de bolhas e Detalhes (Tabela, Não avaliáveis, Método e procedência) da área |
| Mapa de pontos | Não faz parte da página; a distância fica na Análise espacial |
| Investigação progressiva e diagnósticos compostos ("Acrescentar ao diagnóstico") | Histórico de análises |
| Navegação "Início" e "Resultados"; abas "1. Preparação" e "2. Resultados" | A página é sempre o gráfico |
| Comandos "volte para a seleção de territórios", "voltar à preparação", "mostre os resultados" e "quero analisar vários períodos" | Pedidos ao gráfico pela conversa |

A API não mudou com essa saída: `/api/analyze`, `/api/preflight` e as capacidades continuam, com os mesmos contratos.

## Componentes e fronteiras

- `App.tsx`: estrutura da página, fonte de dados, Histórico, Nova análise e Nova sessão; monta a área de análise.
- `BarraDaFonte.tsx`, `ColunasDaPlanilha.tsx` e `HistoricoDeAnalises.tsx`: fonte, painel "Colunas" e Histórico.
- `AnalysisAssistant.tsx` e `ChatFloatingBox.tsx`: a conversa e a caixa flutuante.
- `conversaGrafico.ts` e `paginaUnica.ts`: funções puras da conversa (campo `painel` → pedido, contexto → opções, comandos) e
  da estrutura (resumo da fonte, rótulos, colunas, Histórico, CSV da sessão), com os tipos do contrato da área.
- `conversationSession.ts`, `SessionPrivacy.tsx` e `WorkspaceDialog.tsx`: sessão, aceite e diálogos acessíveis.
- `AreaDeAnalise.tsx` e os `Painel*`: a área de análise.

Testes: `frontend/tests/paginaUnica.test.mjs` e `frontend/tests/conversaGrafico.test.mjs` (unitários); os roteiros de
navegador `backend/tests/ui_pagina_unica.py` (suítes `bloco1` e `base-versionada`) e `backend/tests/ui_conversa_grafico.py`
(suítes `conversa`, só com os canais locais, e `gemini-simulado`, com o provedor simulado e a conferência de que nada da base
chega a ele). O que cobriam os roteiros do fluxo clássico, e onde essa cobertura está agora, fica em
[`backend/tests/legado/README.md`](../backend/tests/legado/README.md).
