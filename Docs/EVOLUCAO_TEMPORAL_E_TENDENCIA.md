# Evolução temporal: mudança (CAP-TMP-01) e tendência (CAP-TEN-01)

Vigência: 19/10/2026 (decisão D6 do responsável pelo produto). Código: `backend/trend.py`,
`backend/temporal_change.py`, o ramo `temporal` de `backend/main.py` e `backend/representation.py`; na
tela, `frontend/src/trend.ts`, `frontend/src/TrendVisuals.tsx`, `ResultWorkspace.tsx` e a caixa Período
(`PeriodSelection.tsx`, `periods.ts`). Referência normativa: `IMPLEMENTATION_SPEC.md`, CAP-TMP-01 (DA-14),
CAP-TEN-01 (DA-15), enums `CategoriaTendencia` (L415) e `MotivoSemClassificacao` (L390), e os textos do
catálogo `DOC:CAP-TEN-01.precondicoes` (`Docs/CFG_DOC_CATALOG.yaml`). Não há divergência com a SPEC.

## 1. O que a evolução temporal entrega

Uma linha por território e categoria, nesta ordem de colunas:

| Coluna | Conteúdo |
|---|---|
| Território, Categoria | a unidade |
| Período inicial, Período final | a primeira e a última competência da janela escolhida |
| Inicial, Final | valores do indicador nessas competências (float, como antes) |
| Variação absoluta, Variação (%) | Final − Inicial e (Final − Inicial) / Inicial × 100 (float, como antes) |
| Direção da mudança | Aumento, Redução ou Sem mudança, pela comparação **exata** dos extremos (CAP-TMP-01, sem tolerância) |
| Condição da mudança | "Avaliável"; "Avaliável; variação percentual não avaliável: base zero"; ou "Não avaliável: observação ausente em um dos extremos" |
| Tendência | classe da DA-15 ou "Não avaliável: série insuficiente" / "Não avaliável: série não comparável" |
| Motivo da tendência | "Mudança de direção" ou "Série estável" (Sem classificação); "N de 4 observações necessárias" (série insuficiente); o componente divergente (série não comparável); com a classe atribuída não há motivo: vazio no CSV e "Não se aplica" na tabela da tela |
| Observações da tendência | número de observações válidas usadas |

`detail_rows` continua com a série (Território, Período, Categoria e o valor de cada competência).

**Base zero (BASE_ZERO).** Com Inicial = 0, a direção e a variação absoluta são calculadas e a
variação percentual fica vazia, com a condição e uma nota explicando. A avaliabilidade estruturada
do resultado continua a mesma de antes (a condição não aciona a limitação do resultado).

## 2. Método da tendência (CAP-TEN-01, DA-15)

1. **Pré-condição da etapa:** pelo menos quatro competências distintas na janela. Com menos, a
   etapa recebe `BLQ-MET` (SERIE_INSUFICIENTE) com os textos do catálogo: "Não foi possível analisar a
   tendência porque há apenas {quantidade} observações válidas." e "A análise de tendência exige
   quatro observações válidas.". A mudança entre o primeiro e o último período continua disponível
   (AT-09).
2. **Por unidade:** observações válidas, sem imputar competências ausentes; o tempo transcorrido
   entre observações entra na velocidade. Menos de quatro observações: NAO_AVALIAVEL
   (SERIE_INSUFICIENTE). Série de agregado com membros diferentes entre competências (informada por
   quem chama, `evolution(..., incomparable=)`): NAO_AVALIAVEL (INCOMPARABILIDADE), sem velocidades e
   sem linha de trajetória, com os valores de cada competência preservados (AT-69, AT-80).
3. **Velocidade:** vᵢ = (yᵢ₊₁ − yᵢ) / (tᵢ₊₁ − tᵢ), variação absoluta por unidade de tempo (mês nas
   competências AAAAMM, dia nas datas, unidade do período nas numéricas).
4. **Classes** (rótulos de apresentação da DA-15), na ordem do enum:
   - todas as velocidades nulas: **Sem classificação** (Série estável);
   - velocidades positivas e negativas: **Sem classificação** (Mudança de direção);
   - todas ≥ 0 e ao menos uma > 0: **Crescimento**; com todas > 0, magnitudes não decrescentes com
     um aumento estrito: **Aceleração do crescimento**; não crescentes com uma redução estrita:
     **Desaceleração do crescimento**; constantes ou sem monotonicidade: Crescimento;
   - declínio simétrico (todas ≤ 0 e ao menos uma < 0) sobre as magnitudes: **Declínio**,
     **Aceleração do declínio**, **Desaceleração do declínio**.
   - Família derivada: Crescimento (três primeiras), Declínio (três seguintes) e nenhuma (Sem
     classificação). "Sem classificação" é resultado do método, não falta de dados.
5. **Desfecho da etapa** (`metadata.tendencia.desfecho`): RES-VAL (todas avaliáveis, com ao menos uma
   classe), RES-LIM (com não avaliáveis), RES-SCL (método executado e nenhuma unidade com classe) e
   BLQ-MET (bloqueio da etapa ou nenhuma unidade avaliável).

**Aritmética exata.** A classificação usa racionais exatos. Na densidade, o valor é recalculado como
quantidade × 1.000 / população, sem passar pela coluna float do motor: o arredondamento binário
separaria velocidades exatamente iguais. Exemplo real: ANAMÃ (130008), densidade de junho de 2021 a
2024, quantidades 5, 6, 7 e 11 com população 14.292, 14.292, 14.292 e 10.318. As duas primeiras
velocidades são iguais (125/21438 por mês) e a terceira é maior: **Aceleração do crescimento**. Em
float, a classe seria "Crescimento". Na série de junho de 2021 a 2024, 63 municípios mudariam de
classe em float. O caminho em massa (`classify_frame`) compara as velocidades como pares de inteiros
por produto cruzado, com o mesmo resultado do caminho com `Fraction` (`classify`), conferido em
`backend/tests/test_trend.py`. As velocidades são entregues em float (arredondamento correto do
racional) em `metadata.tendencia.unidades[].velocidades`.

**Versão do método:** `CAP-TEN-01/DA-15/1`, registrada em `metadata.metodos.tendencia` e na chave de
execução da evolução temporal (as chaves das demais análises não mudam).

## 3. Metadados estruturados

- `metadata.tendencia`: `capacidade`, `versao_metodo`, `desfecho`, `bloqueio`, `indicador`,
  `unidade_valor`, `unidade_tempo`, `janela` (`periodos`, `inicio`, `fim`, `intervalos` entre
  competências vizinhas, `intervalo_constante`, `serie_anual`, `serie_anual_disponivel`,
  `competencias_serie_anual`), `unidades_total`, `avaliaveis`, `nao_avaliaveis`, `contagens` (7
  classes), `sem_classificacao_por_motivo`, `nao_avaliaveis_por_motivo`, `familias`, `classes`
  (código, rótulo, família), `rotulos_familia`, `rotulos_nao_avaliavel`, `rotulos_motivo` e
  `unidades` (território, categoria, velocidades e competências ausentes).
- `metadata.mudanca`: `capacidade` (CAP-TMP-01), `periodo_inicial`, `periodo_final`, `direcoes`
  (AUMENTO, REDUCAO, SEM_MUDANCA), `nao_avaliaveis` (SEM_REGISTRO_OBSERVADO) e
  `percentual_nao_avaliavel` (BASE_ZERO).
- `metadata.representacao`: os indicadores Tendência (CLASSE, CAP-TEN-01, com os sete rótulos e os
  dois de não avaliável), Direção da mudança (ESTADO, CAP-TMP-01), Variação absoluta e Variação percentual
  (coluna Variação (%); CONTINUO); `serie.quebras` lista as unidades sem trajetória. O mapa continua não aplicável.
- Nada disso vai ao provedor de IA: o contexto enviado continua sendo o pedido minimizado e os
  estados do pré-exame (`provider_snapshot`).

## 4. Janela e série anual de junho

A base Brasil tem duas competências por ano, janeiro e junho, com intervalos alternados de 5 e 7
meses. A tendência considera o tempo transcorrido, mas, com 22 competências, qualquer queda entre
duas vizinhas leva a "Sem classificação (mudança de direção)". A **série anual de junho** usa só
junho: uma competência por ano, 12 meses entre elas, no mesmo mês da população estimada.

- O padrão da evolução temporal continua sendo **todas as competências**.
- Na caixa **Período**, o atalho **"Série anual (junho) · N competências"** (`period-annual-june`,
  com `aria-pressed`) escolhe só as competências de junho. A linha de resumo passa a "série anual de
  junho: 11 competências, de junho de 2014 a junho de 2024". Na evolução temporal da base oficial, um
  texto explica a diferença.
- No resultado, quando os intervalos não são constantes e há ao menos quatro competências de junho na
  janela, o botão **"Usar a série anual (junho)"** leva essas competências à caixa Período. Ele só
  muda a seleção; o cálculo continua sendo ação do usuário.

## 5. Na tela

- **Selo** (`trend-badge`, com `data-class` = código da classe ou `NAO_AVALIAVEL`): texto, cor e
  ícone, sem cor de juízo. Família do crescimento em azul (#2a78d6), do declínio em laranja
  (#eb6834), Sem classificação em verde-água (#1baf7a, sempre com texto) e não avaliável em cinza
  com contorno tracejado. O código vem de `metadata.tendencia.classes` pelo rótulo da linha; o
  navegador não classifica.
- Os **cartões de destaque** (até três registros) mostram o selo, o motivo, o número de observações e
  o **minigráfico de velocidades** (`trend-velocities`, `data-count`): barras a partir do zero, na cor
  da família, com a competência de cada intervalo na dica; velocidade zero é um traço na linha de
  base; não há linha ajustada. O mesmo aparece no detalhe do território selecionado.
- A **tabela** mostra o selo na coluna Tendência; o CSV continua com o texto do motor.
- Em **Gráficos**, a **contagem por classe** (`trend-counts`, uma linha `trend-count` por classe ou
  motivo) segue a ordem da SPEC, agrupada por família, com os não avaliáveis à parte (AT-18). Os
  números são os do motor.
- O **filtro por família** (`trend-family-filter`) reúne as três classes de cada família (L1776),
  mais Sem classificação e Não avaliável, com os números do motor.
- O **aviso da etapa** (`trend-stage-note`, `data-outcome`) mostra o bloqueio BLQ-MET com os textos do
  catálogo ou, no RES-SCL, "Método executado: nenhum território recebeu classe de tendência nesta
  série. Sem classificação não é falta de dados.".
- No gráfico de linhas, as unidades de `serie.quebras` aparecem só como pontos.

## 6. Contagens com os dados reais (municípios, 5.570)

| Janela | Indicador | Crescimento | Declínio | Sem classificação (mudança de direção) | Sem classificação (série estável) |
|---|---|---|---|---|---|
| Série completa (22) | quantidade | 53 | 5 | 5.505 | 7 |
| Série anual de junho (11) | quantidade | 276 | 19 | 5.257 | 18 |
| Série completa (22) | densidade | 7 | 0 | 5.563 | 0 |
| Série anual de junho (11) | densidade | 118 | 2 | 5.450 | 0 |

Nessas janelas não há classe acelerada nem desacelerada e nenhum município é não avaliável. Brasil
(contagem nacional, `Dados_Brasil.xlsx`): Crescimento na série completa (22 observações) e na de
junho (11). Direções da mudança na série completa, quantidade: 4.924 Aumento, 347 Redução e 299 Sem
mudança; 4 municípios com base zero.

## 7. Testes

- `backend/tests/test_trend.py`: AT-53 completo (classes, três observações, normalização pelo
  tempo), AT-09 e AT-10 pela análise, AT-69/AT-80, AT-18, regressão do float (quantidades 0, 1, 2, 3
  com população 3), janela e série anual, e equivalência de `classify_frame` com `classify` em séries
  aleatórias.
- `backend/tests/test_real_data.py`: classes do motor iguais a uma classificação independente
  (Fraction, CSV lido pelo teste) nas séries completa e de junho, em quantidade e densidade; âncoras
  Brasil (Crescimento) e ANAMÃ (Aceleração do crescimento).
- `test_territorial_selection.py`, `test_representation.py` e `test_llm_context.py` (nada da
  tendência vai ao provedor).
- Node: `frontend/tests/trend.test.mjs` e `periods.test.mjs` (série anual).
- Navegador: `ui_block1_smoke.py` confere os selos contra as linhas, as contagens contra a metadata,
  o aviso RES-SCL na base real e o atalho "Série anual (junho)" (BLQ-MET no catálogo sintético e 33
  linhas de série na base real).

## 8. Fora deste escopo

A comparação com janela (tendência por objeto) e os níveis Brasil e estados entram nas etapas
seguintes; elas reutilizam `temporal_change.evolution`. Ficam de fora o mapa da tendência, os
pequenos múltiplos e a pergunta "tendência" no chat.
