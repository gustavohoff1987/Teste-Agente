# Detector de Sinais Territoriais

Ferramenta do comando V22 (Eixo II, etapa 3: o núcleo). A referência metodológica é
[Detector e Simulador V2.2](DETECTOR_E_SIMULADOR_V2_2.md) (seções 2.4, 4, 4.2 e 5, com as decisões D-A a D-C de 10/11/2026), e o
perfil da base está em [Perfil da base](PERFIL_DA_BASE_DETECTOR_SIMULADOR.md). Este documento descreve o que o sistema faz hoje.

## O que é

O Detector mostra, para cada território da seleção em uso, a **situação mais recente da janela** e, à parte, o **histórico de
sinais**. Ele separa três coisas que não se confundem:

1. **fato observado:** a contagem e a mudança entre registros (por exemplo, "−3 médicos, −30%, de jan/2024 a jun/2024"). Sempre
   aparece;
2. **excepcionalidade:** se a mudança é incomum para municípios do mesmo porte, no mesmo tipo de intervalo (5 ou 7 meses), medida
   só com o que aconteceu antes da data avaliada;
3. **sinal analítico:** a **intensidade do sinal** (atenção, alta, crítica), por fenômeno, com **limites provisórios**.

A intensidade do sinal descreve o indicador. Não é juízo de desassistência, de suficiência do atendimento nem de prioridade de
provimento. Ela é uma **divergência aprovada da SPEC** (CFG-NOR, 4.4.19: nenhum critério normativo pré-configurado), válida só no
Detector (decisão D-A do responsável, 10/11/2026); fora dele, o assistente continua recusando "crítico" sem critério.

O Detector calcula no motor (`backend/detector.py`, sobre `backend/series_brasil.py`), sem o provedor de IA, e funciona com ele
indisponível. Só existe na **base do Brasil** (médicos, registros de janeiro e junho de 2014 a 2024); com uma planilha enviada, o
botão fica desligado, com o motivo.

## Na tela

- **Onde:** o botão **Detector de Sinais** (`analise-ferramenta-detector`), na linha "Ferramentas" da navegação principal, acima
  das abas. A ferramenta abre no lugar do painel da aba e do desenho da análise, que continuam como estavam ao voltar para uma aba
  (`area-de-analise` leva `data-ferramenta`). Ela usa a **seleção em uso**: os municípios, os estados como unidade e os conjuntos.
  Sem territórios, diz "Nenhum território selecionado" e não pede nada ao motor.
- **Aviso da data** (`detector-data`): "Registro mais recente da base: jun/2024. Os sinais descrevem a situação até jun/2024, não
  a de hoje."
- **Janela:** início e fim entre as competências reais da base (`detector-janela-inicio` e `detector-janela-fim`). A situação é a
  do fim da janela; o histórico e a série de junho começam no início dela. Para um município com quebra de fonte, os indicadores
  começam depois da quebra.
- **Tabela** (`detector-tabela`, 50 linhas por página, `detector-linha`): território; condição estrutural; trajetória; ritmo e
  instabilidade; qualidade do registro; última observação. A intensidade aparece com o nome por extenso (`detector-intensidade`:
  Atenção, Alta, Crítica), nunca só pela cor. As colunas da posição relativa, do contexto geográfico e dos sinais combinados
  (fenômenos 8 a 12) entram na etapa 5 do comando.
- **Filtros:** por fenômeno (poucos médicos; nenhum médico registrado; perda no último registro; perda com alerta; abaixo do
  patamar anterior; declínio em junhos seguidos; desaceleração do crescimento; registro a verificar ou com descontinuidade), por
  porte (os médicos do último registro) e pelo nome; a ordem é por intensidade (só ordena a lista: não há índice geral), por nome
  ou por número de médicos.
- **Detalhes** (a seta de cada linha, `detector-detalhe`): a série observada, só com os registros reais e as marcas de registro;
  os seis fenômenos do núcleo, cada um com sete campos — **o que foi observado**, **qual critério**, **quanto difere do habitual**,
  **o que significa**, **o que não significa**, **limitações do dado** e **qualidade do registro** —; e o **histórico de sinais**
  (`detector-historico`), em que cada data é avaliada só com o que era conhecido nela.
- **Parâmetros** (`detector-parametros`): os limites da escala estrutural, da perda entre registros, do patamar e do declínio
  podem ser trocados. Qualquer valor diferente do padrão vira uma **configuração personalizada — exploratória**
  (`detector-exploratorio`), com "Voltar aos padrões"; os padrões nunca são trocados em silêncio.
- **Como foi calculado** (`detector-metodo`): as notas e, para a data avaliada, a partir de que queda (e de que afastamento do
  patamar) a variação é incomum, por porte.
- **Exportações:** a tabela em CSV (uma linha por território, com a janela, a versão da base e do método e a configuração em
  cada linha) e o método em JSON (a fonte, a janela, os parâmetros padrão e em uso, a comparação da data e as notas).

**Linguagem simples (decisão D-C).** A tela diz "sem classificação", com o motivo ("poucos municípios parecidos na base para
dizer se esta queda é incomum"), no lugar de "não calibrado"; "limites provisórios", no lugar de "candidatos"; "incomum" e
"muito incomum", no lugar de "cauda de 1%" e "de 0,1%". Os termos técnicos ficam em "Qual critério", em "Como foi calculado" e
nas exportações. Dois textos da conferência de 10/11/2026 (pausa 2):

- no afastamento de patamar com intensidade alta, quando o afastamento também chega ao limite da crítica mas a base não permite
  avaliá-la, a linha da tabela diz "**crítica: sem base para avaliar**" (antes, "sem base para dizer se é muito incomum", que
  parecia contradizer a intensidade alta); o detalhe explica o porquê;
- no fenômeno 4 (desaceleração do crescimento), a situação diz "**Não se aplica: a série está em declínio**" ou "Não se aplica:
  a série não tem classificação de tendência" (antes, "Sem desaceleração do crescimento (declínio)"); em crescimento sem a
  classe, "Sem desaceleração: a série está em crescimento" ou "Sem desaceleração: o crescimento está acelerando".

## O que é calculado

Os números entre parênteses são os dos fenômenos do catálogo. Os limites são **provisórios** (candidatos da V2.2).

| Dimensão | Fenômeno | Regra | Resultado |
|---|---|---|---|
| Condição estrutural | Dependência de poucos médicos e ausência de médicos registrados (1–2) | Nenhum (zero confirmado) ou 1 médico: crítica; 2 ou 3: alta; 4 ou 5: atenção; 6 ou mais: sem sinal por esta escala. Vale a mais grave das duas últimas observações válidas. Impacto da saída de um médico: 100/N (com zero, não calculável). Duração do zero em registros e meses | Intensidade (convenção), com o número de médicos |
| Trajetória | Declínio persistente (3) | Série de junho, reduções em anos seguidos, perda desde o primeiro valor da sequência: 2 reduções e 10% ou mais (forte); 3 e 20% ou mais (muito forte) | Sinal observado, sem intensidade |
| Trajetória | Perda abrupta (6) | A perda entre dois registros sempre aparece. Alerta só com **magnitude** (alta: ≥ máx(2; ⌈0,2·N⌉) médicos; crítica: ≥ máx(3; ⌈0,3·N⌉)) **e excepcionalidade** (P(X ≤ x) ≤ 1% ou 0,1% entre as transições anteriores da célula porte × intervalo, contando empates; mínimo de 100 ou 1.000 transições) | Fato; alerta de intensidade alta ou crítica; ou sem classificação, com o motivo |
| Trajetória | Afastamento de patamar anterior (7) | Patamar: a maior média dos 4 registros de dois anos civis completos, em blocos que terminam antes dos 4 últimos registros. Os 2 últimos registros ≤ 85% do patamar: atenção. Com afastamento na cauda de 1% da faixa de porte do patamar: alta. Crítica (4 últimos ≤ 70% e cauda de 0,1%): não calibrável na base atual. Patamar abaixo de 20 médicos: descritivo | Atenção ou alta; descritivo; sem sinal |
| Ritmo e instabilidade | Desaceleração do crescimento (4) | A classe da Análise de Tendência (CAP-TEN-01, `trend.classify_pairs`) nos 4 junhos até o junho avaliado, com o número de médicos; atualizada só em junho. A repetição da classe um ano antes é exploratória | Sinal descritivo, sem intensidade |
| Ritmo e instabilidade | Instabilidade temporal (5) | Desvio-padrão das variações de 7 registros ÷ c·N̄^(θ/2), com θ = 1,35 e c por tipo de intervalo (só com transições anteriores); não calculável com média abaixo de 6 | Índice descritivo (1 = a oscilação típica do porte) |

**Qualidade do registro** (seção 2.4 do anexo):

- **descontinuidade de registro — pico que volta:** salto de 10 ou mais médicos que ao menos dobra a contagem e volta, em até dois
  registros, a até 125% do valor anterior. Até a volta ser observada, o salto leva "verificar registro". A volta não gera alerta, o
  trecho sai da comparação com territórios parecidos, e o registro do pico fica fora do patamar, da série de junho e da
  instabilidade;
- **descontinuidade de registro — quebra de fonte:** a soma municipal da UF abaixo da contagem estadual de médicos únicos, nas
  competências em que todos os municípios da UF têm registro (na base, só o Distrito Federal, de jan/2014 a jun/2017). O trecho
  sai da comparação, e a janela do município começa depois dele;
- **verificar registro:** o salto sem volta observada e a queda de 10 ou mais médicos que leva a contagem à metade ou menos. A
  queda grande que persiste **continua alertável**.

**Estados que nunca viram "sem sinal" em silêncio:** valor observado; zero confirmado; ausência de dado (o registro que falta não
é zero); não calculável; janela insuficiente; descontinuidade de registro; e sem classificação por falta de comparação (com o
motivo).

**Níveis.** A comparação com territórios parecidos é municipal. Para estados como unidade (a contagem estadual de médicos únicos)
e para conjuntos (a soma das contagens dos componentes, que só existe quando todos têm registro na competência), o Detector
mostra os fatos e os indicadores descritivos, sem intensidade.

## Rota

`POST /api/detector` (formulário, como `/api/painel`): `dataset=brazil`, `dataset_version` e `options` (JSON). Só lê e calcula:
nada é registrado na sessão, e nada vai ao provedor de IA. Conta nas vagas das operações pesadas (`carga.PESADAS`).

| Opção | Conteúdo |
|---|---|
| `base` | `{"municipios": {"todos", "estados", "ids"}}`, como no painel |
| `estados_unidade` | os estados como unidade (prefixos IBGE) |
| `conjuntos` | `[{"id", "rotulo", "membros", "versao"?}]`; membros do mesmo nível (`code:<IBGE>` ou `uf:<prefixo>`) |
| `janela` | `{"inicio", "fim"}`, competências da base; sem ela, a série inteira |
| `parametros` | os limites personalizados (`estrutural`, `perda`, `patamar`, `declinio`); a resposta vem com `exploratorio: true` |
| `detalhe` | o id de um território da seleção: a resposta traz `territorio`, `serie`, `historico` e `fenomenos`, no lugar da tabela |

A tabela responde com `versao`, `fonte`, `janela`, `competencias`, `parametros` (`padrao`, `em_uso`, `personalizados`,
`editaveis`), `linhas`, `resumo`, `calibracao` (por porte, as transições anteriores e a queda a partir da qual a variação é
incomum; no patamar, o afastamento; e o monitoramento da data), `notas` e `limitacoes`. Erros de pedido vêm em 422, com o texto
em português (seleção vazia, território fora da base, competência fora da base, parâmetro fora do intervalo, planilha enviada).

A seleção segue o contrato compartilhado das ferramentas (`series_brasil.selecao`): o estado como unidade (ou num conjunto de
estados) e os municípios dele não entram juntos (RQ-DAD-30); um conjunto reúne territórios do mesmo nível.

## Calibração

Estudo de 10/11/2026 com a base versionada (`scripts/calibrar_detector.py`, somente leitura; versão da base `c4d82eeee4e4`,
método `DETECTOR-SINAIS/V2.2/1`). Tudo respeita as origens móveis: cada data é avaliada só com as transições anteriores a ela.

**Células da perda abrupta em jun/2024** (intervalo de 5 meses):

| Médicos antes | Transições anteriores | Queda incomum (1%) a partir de | Queda muito incomum (0,1%) a partir de |
|---|---:|---:|---:|
| 1 a 3 | 6.572 | 66,7% | — |
| 4 a 9 | 16.650 | 44,4% | 77,8% |
| 10 a 19 | 12.035 | 36,8% | 58,8% |
| 20 a 49 | 9.958 | 31,2% | 56,4% |
| 50 a 99 | 3.969 | 29,4% | 64,8% |
| 100 a 299 | 3.708 | 26,3% | 52,4% |
| 300 ou mais | 2.765 | 15,6% | 44,4% |

Todas as células têm o mínimo para os dois limites em jun/2024. Nas duas primeiras datas da base (jun/2014 e jan/2015), não há
transições anteriores do mesmo tipo de intervalo: sem classificação. Na faixa de 1 a 3 médicos, nenhuma queda cabe na cauda de
0,1% (a maior queda possível é comum demais), e a magnitude mínima de 2 médicos quase nunca é alcançada: ali, quem informa é a
escala estrutural.

**Afastamento de patamar em jun/2024** (cauda de 1% por faixa do patamar): 20 a 49 médicos, 13.942 avaliações anteriores, incomum
a partir de 39,5%; 50 a 99, 5.321 e 38,3%; 100 a 299, 5.109 e 31,9%; 300 ou mais, 3.668 e 19,4%. Municípios classificáveis
(patamar de 20 médicos ou mais): 2.312; com atenção, 104; com alta, 32. A crítica é não calibrável (23 municípios cumprem a
condição de magnitude).

**Monitoramento (dado real).** A taxa de transições na cauda de 1%, por data, vai de 0,48% (jun/2024) a 1,44% (jun/2017): perto
da meta por construção, e por isso não mede acerto. Em jun/2024: 27 transições na cauda, 24 alertas de intensidade alta e 3 de
crítica; 1.153 municípios com perda no último registro (o fato, à vista em todos).

**Modelo nulo sintético** (seção 4.2 do anexo: N(t+1) = N(t)·(1 + g) + ε, Var(ε) = φ·N^θ, inteiros não negativos; g = 2,69% em 5
meses e 3,53% em 7; φ = 0,0982 e 0,1142; θ = 1,35; 5 repetições, semente 20261110):

| Médicos antes | Falso alerta (alta) | Falso alerta (crítica) | Queda de 20% não detectada | Queda de 30% não detectada | Queda de 50% não detectada |
|---|---:|---:|---:|---:|---:|
| 1 a 3 | 0,02% | 0,000% | 100,0% | 100,0% | 100,0% |
| 4 a 9 | 0,72% | 0,056% | 92,1% | 86,4% | 20,1% |
| 10 a 19 | 0,76% | 0,103% | 87,4% | 57,5% | 0,5% |
| 20 a 49 | 0,89% | 0,096% | 70,0% | 19,6% | 0,0% |
| 50 a 99 | 0,30% | 0,002% | 63,6% | 6,8% | 0,0% |
| 100 a 299 | 0,04% | 0,000% | 67,6% | 2,2% | 0,0% |
| 300 ou mais | 0,00% | 0,000% | 78,1% | 0,3% | 0,0% |
| Todos | 0,55% | 0,055% | 80,4% | 43,8% | 14,9% |

Leitura: sem nenhuma queda real, 0,60% das avaliações recebem algum alerta (abaixo da meta de 1%, porque a magnitude também é
exigida). A regra detecta bem quedas de 30% ou mais a partir de 20 médicos e quedas de 50% a partir de 10; não detecta quedas de
20% (pelo desenho: a magnitude da alta começa em 20%, e a variação precisa ser incomum) nem perdas em municípios com até 3 médicos.
Esses números valem para o modelo nulo, com os parâmetros estimados na base; não são uma taxa de acerto em dado real.

**O que continua provisório:** os limites da escala estrutural e do declínio (convenções); as metas de 1% e 0,1%; o corte de 20
médicos e os 15% do patamar; o critério do pico que volta; θ e a forma da instabilidade. A desaceleração repetida segue
exploratória (na base, 182 municípios com a classe em jun/2024, 16 com repetição).

## Limitações

- A base só tem médicos, e o registro mais recente é jun/2024: nenhum sinal descreve a situação de hoje.
- A contagem municipal é a de médicos registrados no município: quem atua em mais de um conta em cada um. Um conjunto é a soma das
  contagens dos componentes, nunca "médicos únicos".
- O Detector não infere rotatividade de pessoas, desassistência, isolamento assistencial, suficiência do cuidado nem causa.
- Estados como unidade e conjuntos não têm intensidade (a comparação é municipal).
- Os fenômenos 8 a 12 (disponibilidade e posição relativas, defasagem ante referência, contexto geográfico e sinais combinados) e
  a ligação com o Simulador ("Simular recuperação") entram na etapa 5 do comando V22.

## Testes

- pytest: `backend/tests/test_detector.py` — as regras em séries sintéticas (escala e histerese; zero e ausência; a magnitude
  arredondada para cima, os empates, só as transições anteriores e o mínimo de transições; o pico que volta, a quebra de fonte e a
  queda grande que persiste; o patamar; o declínio; a desaceleração igual à classe da Análise de Tendência; a instabilidade; os
  níveis; os parâmetros exploratórios; os textos), a rota com um catálogo sintético e, no job `dados-reais`, a base versionada
  (Rio Rufino/SC, o Distrito Federal antes de 2018, uma queda grande que persiste, a desaceleração igual à da Análise de Tendência
  e os números do perfil).
- Node: `frontend/tests/detector.test.mjs` — a leitura da resposta, os textos da tabela em linguagem simples, os filtros, a ordem,
  os parâmetros e as exportações; a seleção no contrato das ferramentas.
- Navegador: `backend/tests/ui_detector.py` (suíte `base-versionada`).
