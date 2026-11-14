# Simulador de Cenários Territoriais

Ferramenta do comando V22 (Eixo II, etapas 4 e 5: o núcleo, de 10/11/2026; e as referências, o planejamento inverso e a ligação
com o Detector, de 11/11/2026). A referência metodológica é [Detector e Simulador V2.2](DETECTOR_E_SIMULADOR_V2_2.md) (seções
2.5, 3.3, 7, 8, 8.8, que prevalece, 9, 10 e 11, com as decisões D-A a D-C de 10/11/2026), e o perfil da base está em
[Perfil da base](PERFIL_DA_BASE_DETECTOR_SIMULADOR.md). Este documento descreve o que o sistema faz hoje.

## O que é

O Simulador mostra, para os territórios escolhidos, **cenários hipotéticos e condicionais**: quantos médicos o território teria
numa data final, dado um método para a base do cenário e as intervenções que a pessoa declarar. Nenhum resultado é previsão,
observação atual, conclusão sobre o atendimento ou recomendação de provimento.

O Simulador é a **exceção aprovada** à exclusão de projeção da SPEC ("projeção ou previsão (Caso 4)" fora da FAM-08; critério
AT-04), decidida pelo responsável em 9/11/2026 (decisão 2 do comando V22; seção 2.5 do anexo) e restrita a esta ferramenta
determinística. Fora dela nada muda: o assistente de conversa continua recusando pedidos livres de projeção ou previsão, e a guarda
de fidelidade continua recusando previsões em qualquer outro texto. A SPEC não foi editada.

O Simulador calcula no motor (`backend/simulador.py`, sobre `backend/series_brasil.py` e a calibração de `backend/detector.py`),
sem o provedor de IA, e funciona com ele indisponível. Só existe na **base do Brasil** (médicos, registros de janeiro e junho de
2014 a 2024); com uma planilha enviada, o botão fica desligado, com o motivo.

Três coisas ficam sempre separadas, no cálculo e na tela:

1. **o observado:** os registros reais, só nas datas com registro (linha contínua e marcadores);
2. **a base do cenário:** o que o método escolhido dá para as datas depois da origem (linha tracejada);
3. **a intervenção:** os acréscimos e as retiradas declarados pela pessoa, somados à base, com um marcador em cada evento.

## Na tela

- **Onde:** o botão **Simulador de Cenários** (`analise-ferramenta-simulador`), na linha "Ferramentas" da navegação principal, ao
  lado do Detector de Sinais. A ferramenta abre no lugar do painel da aba e do desenho da análise (`area-de-analise` leva
  `data-ferramenta="simulador"`). A seleção local e os cenários ficam guardados enquanto a fonte de dados for a mesma: sair da
  ferramenta e voltar não os perde.
- **A data, sempre à vista** (`simulador-data`): "O registro mais recente da base é jun/2024 (há … anos e … meses): é histórico.
  Tudo o que vem depois dele é simulado, nunca observado". A distância até hoje usa a data do aparelho.
- **Nada é calculado sem comando:** o motor só é chamado por "Calcular os cenários" (ou "Calcular com o que está escolhido").
  Depois de uma mudança nas escolhas, os resultados à vista ficam marcados como desatualizados, com "Calcular de novo".
- **Modo simples** (um cenário) e **modo avançado** (até 5 cenários, cada um com nome, método, janela própria e intervenções). A
  persistência entra sempre como referência de comparação, numa coluna à parte.

### As quatro etapas

1. **Territórios em análise** (`simulador-territorios`): a **seleção local** do Simulador.
   - Ela nasce como **cópia da seleção principal**: os municípios um a um, os estados como unidade e os conjuntos, com o nome, a
     composição e a versão. "Ver a composição dos conjuntos" lista os componentes de cada conjunto.
   - Enquanto não for alterada no Simulador, a cópia **acompanha** a seleção principal. Depois da primeira alteração feita aqui (ou
     de um cenário importado), ela é só do Simulador e só muda aqui dentro ou por "Copiar de novo a seleção principal". A tela diz
     isso duas vezes: no alto da etapa e, junto do botão "Copiar de novo a seleção principal", o aviso de que a cópia **deixou de
     acompanhar** a seleção principal (`simulador-nao-acompanha`).
   - A busca acrescenta um município, um estado como unidade ou **o Brasil** **só no Simulador**; o "×" de cada território o
     tira. O estado inteiro e os municípios dele não entram juntos, como na Seleção de Territórios (RQ-DAD-30): a tela recusa,
     com o motivo. O Brasil é a contagem nacional de médicos únicos: é simulado à parte e nunca é somado aos demais.
   - **"Aplicar à seleção principal"** é o único caminho pelo qual o Simulador muda a seleção principal. É um comando separado e
     um passo do Desfazer. O Brasil não vai (a seleção principal não o tem como unidade), e a tela diz isso.
   - O Simulador compara até **100 territórios** de cada vez; acima disso, a tela pede para reduzir a seleção local.
   - **Referências de comparação (opcional)** (`simulador-referencias`): até 5. Uma referência é um município, um estado como
     unidade, o Brasil, um conjunto da seleção local ou **um valor da pessoa**; pode ficar fora da seleção do Simulador e não
     muda a seleção principal. Cada uma é **fixa** (o último valor registrado se mantém) ou **dinâmica** (segue o método padrão
     provisório dela, sem intervenções). A métrica da comparação é escolhida à vista (`simulador-metrica`): a **quantidade de
     médicos** ou a **taxa por 1.000 habitantes, com a população constante** (a do último registro, como hipótese declarada).
   - Quando o Simulador é aberto pelo **Detector de Sinais** ("Abrir no Simulador" ou "Simular recuperação"), a seleção local
     fica só com aquele território e não acompanha a principal; o aviso `simulador-do-detector` diz de onde ela veio, a data
     avaliada e os sinais com nível lá ("Sinais com nível lá: Queda recente (elevado)"), e pode ser dispensado.
2. **Base histórica e método** (`simulador-base`):
   - a **janela histórica**, com início e fim livres entre as competências reais (o fim é a origem do cenário). Os atalhos (janela
     padrão de 3 anos, últimos 5 anos, série completa) são só atalhos. Com a origem antes do último registro, o trecho até ele é
     **retroprojeção**, ao lado do observado;
   - o **método da base do cenário** (lista abaixo), com uma frase simples sobre cada um; no modo avançado, cada cenário pode ter a
     sua janela;
   - as **estatísticas históricas** do território (depois do primeiro cálculo): registros usáveis, lacunas, taxas de junho a junho,
     taxa composta, média aritmética, mediana e dispersão. A média aritmética é **só descrição do passado**.
3. **Intervenções e horizonte** (`simulador-intervencoes-etapa`):
   - a **data final**, em qualquer mês depois do último registro; os atalhos de 1, 2, 4 e 10 anos são só atalhos, nunca limites;
   - as **intervenções hipotéticas** de cada cenário: acréscimo ou retirada de X médicos, numa data ou num calendário (a cada
     tantos meses, de uma data a outra), com a **permanência** em % ao ano (100, todos ficam, é a hipótese padrão);
   - o aviso de que cada intervenção vale para **cada território** do cenário, não para o total (`simulador-por-territorio`):
     com 49 territórios, um acréscimo de 5 médicos soma 5 a cada um deles, inclusive aos estados como unidade e aos conjuntos;
   - o **planejamento inverso** de cada cenário (`simulador-plano`, por "Calcular o acréscimo que alcança uma meta"): a **meta
     hipotética** (chegar a um número de médicos, voltar ao patamar anterior ou alcançar uma referência) e o calendário dos
     acréscimos (uma data, ou de uma data a outra a cada tantos meses, com a permanência). A meta é uma hipótese da pessoa, e ela
     pode trocá-la. Em "Simular recuperação", o Simulador abre nesta etapa, com a meta de voltar ao patamar já preenchida.
4. **Comparações e resultados** (`simulador-resultados`):
   - o **gráfico** de um território por vez (`simulador-grafico`): o observado, a base de cada cenário, a linha com a intervenção
     e os marcadores dos eventos, a faixa de 80% quando existe, a fronteira "observado | simulado (hipótese)" e a fonte;
   - o **texto de cada cenário** (`simulador-texto`), que vem pronto do motor, pelo modelo fixo; as contas da data final (base,
     intervenção e total), a faixa em linguagem simples e os avisos;
   - as **comparações** de cada cenário com as referências (`simulador-comparacao`): o texto do motor, com o valor do território e
     o da referência na data final, a diferença, o índice (100 é a referência) e o alcance — "No cenário, alcança a referência
     em…" (a primeira data avaliada em que isso ocorre), "Na origem, o território já está no nível da referência ou acima dele"
     ou **"Não alcança no horizonte simulado"**, sem data inventada — e os avisos de sobreposição e de unidade. No gráfico, a
     curva de cada referência (traço e ponto, com as marcas R1, R2…); a referência muito acima do território fica "fora da
     escala deste gráfico", na legenda; por taxa, as referências ficam só nos textos;
   - o resultado do **planejamento inverso** (`simulador-planejamento`, com a marca "conta condicional"): a meta, o menor
     acréscimo inteiro por evento, a conta sem arredondar e o texto do cenário com esse acréscimo. O cenário à vista continua
     sendo o do pedido: o acréscimo só entra nele por **"Usar como intervenção deste cenário"** (com um território só na
     seleção; com mais de um, o número é de cada território);
   - a **hipótese do cenário** (`simulador-hipotetico`), num painel à parte: o nível que o valor do cenário teria em "Poucos
     médicos" (sinais 1 e 2 do Detector, por convenção), por exemplo "o território seria Crítico em “Poucos médicos”"; quando a
     faixa cruza um limite, "pode ficar entre elevado e crítico", sem escolher um só. Só para municípios, e só quando é pertinente
     (há nível no valor do cenário ou num dos limites da faixa, ou o território teria até 20 médicos);
   - a **tabela** de todos os territórios (`simulador-tabela`): o último registro usável e, por cenário, o valor na data final, a
     faixa e o método usado em palavras. Num **conjunto**, o método aparece como "soma das projeções dos membros (cada um com o
     crescimento do seu estado)" (ou "cada um no último valor", na persistência; nos demais métodos, "soma das contagens dos
     componentes · …"), e a faixa leva o rótulo "**aproximação**" na tabela, no texto da faixa e na legenda do gráfico;
   - **"Como os métodos se saíram no passado"** (`simulador-validacao`): as notas, as faixas por porte e horizonte (com o número
     de origens e de casos) e o erro de cada método frente à persistência;
   - a linha das **versões** (`simulador-versoes`): o método, a versão da base, a janela e o último registro.

### Textos

O texto de um cenário segue só o **modelo fixo** da seção 2.5 do anexo, montado no motor:

> Cenário hipotético, não é previsão: com o método [método] e as premissas [premissas], [território] teria [N] médicos em [data].
> Base: registros até [última competência usada].

As premissas trazem a janela, o parâmetro do método (a deriva e o estado dela, a taxa ou a variação por ano) e cada intervenção,
com a permanência rotulada como hipótese. Com mais de um território no pedido, a premissa diz para quem a intervenção vale:
"acréscimo de 5 médicos **em cada território do cenário**, em jun/2025, …" (ou "só nos territórios indicados"). N é o inteiro mais
próximo; a precisão integral fica na resposta e nas exportações. Um
conjunto é rotulado como "soma das projeções dos membros" (M0 e M0d) ou "soma das contagens dos componentes" (demais métodos).

Os textos da etapa 5 também vêm prontos do motor:

> Em [data], [território] teria [N] médicos, e a referência [nome] ([fixa: o valor de … mantido | dinâmica: método, com registros
> até … | valor informado por você, mantido]), [M]: [X abaixo | acima da referência | o mesmo valor] (índice [I]; 100 é a
> referência). [Alcance.]

> Meta hipotética: [voltar ao patamar de X médicos | X médicos | alcançar a referência …] em [data]. Menor acréscimo inteiro que
> alcança a meta, nas hipóteses deste cenário: [x] médicos [em … | em cada um dos k eventos, de … a … (total)]. Pela conta sem
> arredondar, seriam [x,xx] por evento. [O texto do cenário com esse acréscimo.] É uma conta condicional às hipóteses do
> cenário, não um plano.

Nenhum deles usa palavras de recomendação ("recomenda-se", "é preciso prover", "deveria"): decisão D-B de 10/11/2026.

A tela e os textos de cenário usam linguagem simples (decisão D-C): "método provisório", "limite provisório", "sem intervenção",
"indisponível", com o motivo. A **deriva do estado** do M0d aparece como "o crescimento recente do estado" (o método, como
"persistência com o crescimento recente do estado"), e a retroprojeção, como o cenário "calculado sobre datas que já têm
registro". Os códigos dos métodos (M0, M0d, M1, M2, M3) e os termos técnicos ficam na lista de métodos, em "Como os métodos se
saíram no passado", neste documento e nas exportações.

## O que é calculado

A base e a intervenção ficam separadas (seção 9 do anexo):

    N(t) = máx(0, B(t) + I(t))        I(t) = Σ a_j · S(t − t_j),   S(u) = 0 para u < 0

com `t` em **anos reais** desde a origem (o último registro usável da janela; entre os registros há 5 e 7 meses, não meio ano).

### Métodos da base do cenário

| Método | Regra | Quando não vale |
|---|---|---|
| **Padrão provisório** | Municípios e conjuntos de municípios: M0d. Estados como unidade (e conjuntos de estados): M1 nos 3 anos até a origem, na série do próprio nível, com aviso | — |
| **M0, persistência** | `B(t) = N0`: o último valor se mantém. É a referência de comparação, sempre calculada | sem registro usável na janela |
| **M0d, persistência com a deriva do estado** | `B(t) = N0 × (1 + g_UF)^t`, com `g_UF` = o crescimento anual composto da soma municipal da UF nos 3 anos antes da origem. Zero continua zero | sem os 3 anos, com soma zero ou com quebra de fonte na janela da deriva: **volta ao M0, com aviso**; não se aplica a estados como unidade |
| **M1, taxa composta** | `r = (Nf/Ni)^(1/T) − 1`, com `T` real em anos; `B(t) = N0 × (1 + r)^t`. É o percentual médio que reproduz o crescimento ocorrido | menos de dois registros, ou o primeiro ou o último em zero: "não se aplica" (a taxa com início em zero não é definida) |
| **M2, tendência linear robusta (Theil–Sen)** | inclinação = mediana das inclinações entre os pares de registros; intercepto = mediana(y) − b · mediana(t). A diferença entre a tendência e o último registro fica à vista | menos de três registros; a base negativa para em zero, com aviso |
| **M3, tendência log-linear** | Poisson com ligação log (IRLS); a dispersão quase-Poisson é só diagnóstico | menos de três registros; série toda em zero: "não calculável" |
| **Taxa informada pela pessoa** | `B(t) = N0 × (1 + taxa)^t`, com a taxa anual digitada, rotulada como hipótese dela | sem a taxa, o cenário não é pedido. **O sistema nunca sugere uma taxa** |

- **Conjuntos:** no M0 e no M0d, a soma das projeções dos membros, cada um com a deriva da sua UF (sem a deriva de uma UF, o
  membro dela fica na persistência, com aviso). Nos demais métodos, o ajuste é feito na série da soma das contagens. Sempre com
  o rótulo.
- **Registros fora do ajuste** (municípios): o registro de um **pico que volta** e os registros de uma **quebra de fonte** (as
  marcas do Detector) não entram na base do cenário; a janela começa depois da quebra. A tela avisa.
- **Ausência de dado não é zero:** um registro ausente é lacuna; a origem é o último registro que existe na janela.
- **A média aritmética das taxas** nunca alimenta uma projeção, não é método, cenário nem sugestão de taxa.
- Comparar métodos e janelas é **sensibilidade a método e janela**, não faixa de confiança.

### Intervenções

- Acréscimo ou retirada de `X` médicos numa data (pontual) ou em eventos periódicos (de… até…, a cada `n` meses). Um acréscimo
  anual acontece **uma vez por ano**, não a cada registro.
- **Permanência:** `S(u) = (p/100)^u`, com `p` em % ao ano. O padrão é 100 (todos permanecem), rotulado como hipótese.
- O crescimento histórico **não** é aplicado aos médicos acrescentados: eles se somam à base.
- Cada intervenção vale para **cada território** do cenário: cada município, estado como unidade e conjunto recebe a quantidade
  inteira, não uma parte de um total. A tela, o texto do cenário e as notas dizem isso. Na rota, uma intervenção pode valer só
  para parte dos territórios (`territorios`); a tela ainda não oferece essa escolha.
- **Retirada acima do estoque:** quando as retiradas passam do número de médicos do cenário, o cenário volta com o estado
  `retirada_acima_do_estoque` e o pedido de revisão; o zero matemático não esconde a intervenção impossível, e nenhum valor é
  mostrado.
- Uma intervenção com data até a origem não é aceita: ela já está nos registros.

### O Brasil como território

O Brasil entra só no Simulador, pela **contagem nacional de médicos únicos** (`brasil: true` no pedido; `id` "br"). O método
padrão é provisório: a taxa composta (M1) dos 3 anos até a origem, na série nacional, com aviso; não há faixa de 80% nem
hipótese do cenário. O Brasil nunca é somado aos demais territórios, e não é uma unidade da seleção principal nem do Detector.

### Referências e comparação

- A referência **fixa** mantém o valor do último registro usável dela na janela. A **dinâmica** segue o método padrão provisório
  do nível dela (municípios e conjuntos de municípios: a persistência com o crescimento recente do estado; estados e Brasil: a
  taxa composta de 3 anos), sem intervenções, com os avisos desse método. O **valor da pessoa** se mantém e é lido na métrica
  escolhida.
- Em cada data do cenário (a origem e as datas da trajetória), a comparação traz a **diferença** (referência − território), a
  **razão** (território ÷ referência) e o **índice** (100 × a razão). Nenhuma variação é chamada de "convergência".
- **Alcance:** `ja_acima` (na origem, o território já está no nível da referência ou acima), `alcanca` (com a primeira data
  avaliada em que isso ocorre) ou `nao_alcanca` ("Não alcança no horizonte simulado"). Nenhuma data é inventada ou extrapolada.
- **Sobreposição e unidades:** a comparação avisa quando a referência é o próprio território, quando um contém o outro (o Brasil
  ou o estado do município; o conjunto com um município em comum; estados em comum) e quando as contagens têm unidades diferentes
  (a contagem municipal, a estadual de médicos únicos, a nacional, ou a soma dos componentes). Nunca se declara uma independência
  que não há.
- **Nomes nos textos** (revisão de 13/11/2026): o estado como unidade aparece como "Paraná (estado)", como no resto do Agente; o
  conjunto leva a palavra "Conjunto" uma vez só ("Conjunto A"); nas premissas do texto de cenário, o crescimento recente traz o
  estado com a preposição certa ("crescimento do Amazonas de +6,21% ao ano"); e nenhum texto põe parênteses dentro de parênteses
  (a unidade da contagem de cada referência vem depois de "Contagem:").
- **Por taxa:** médicos por 1.000 habitantes, com a **população do último registro em todas as datas simuladas** (hipótese
  declarada na tela, no texto e nas exportações; a base não traz população futura). O estado e o Brasil usam a soma das
  populações municipais; sem população válida, a comparação é "não calculável".
- Comparar quantitativos de territórios de portes diferentes não é comparar a suficiência do atendimento.

### Planejamento inverso

O menor número **inteiro** de médicos por evento com que o cenário alcança a meta na data final `T`, com a base `B(T)` **sem
arredondar** (seção 8.8 do anexo). Com `k` eventos iguais e permanência total, `x = ⌈(meta − N(T)) ÷ k⌉`, onde `N(T)` já conta
as outras intervenções do cenário; com permanência menor, cada evento pesa `(p/100)^anos até T`, e o motor procura o menor
inteiro. A resposta traz também a conta sem arredondar (o incremento médio teórico) e o cenário **simulado de novo** com o
acréscimo: reaplicado como intervenção, ele alcança a meta, e com um médico a menos por evento, não.

- **Meta:** um número de médicos; o **patamar anterior** (o do fenômeno 7 do Detector: a maior média de dois anos seguidos antes
  dos registros mais recentes; sem valor informado, o de cada território); ou o valor de uma **referência** na data final.
- **Estados:** `calculado`; `ja_alcancada` (o cenário já chega à meta: nenhum acréscimo); `nao_alcancavel` (com permanência zero,
  nenhum médico acrescentado está no território na data final); `nao_calculavel` (nenhum evento do calendário entre a origem e a
  data final; território sem patamar calculável; referência ausente ou sem valor).
- O resultado é uma **necessidade matemática condicional** às hipóteses do cenário. Não é plano de provimento, recomendação nem
  avaliação de suficiência.

### Níveis no cenário (hipótese do cenário)

Só os **sinais 1 e 2** do Detector (poucos médicos e nenhum médico registrado, por convenção) valem para uma trajetória simulada
([Proposta V3](DETECTOR_E_SIMULADOR_V3.md), seção C.6; desde 13/11/2026, com os níveis moderado, elevado e crítico). Eles são
aplicados ao valor do cenário na data final (e aos limites da faixa de 80%, quando há): quantos médicos o território teria, em
que nível ficaria e quanto a saída de um médico tiraria. Quando a faixa cruza um limite, a tela diz "pode ficar entre moderado e
elevado", sem escolher um só. Vale só para municípios e leva o rótulo "hipótese do cenário" (antes, "hipótese derivada da
simulação"). Os sinais comparados com a base e os de evento observado (queda, patamar, declínio) **nunca** são aplicados a curvas
simuladas.

### Faixa de 80%

- Só existe para o **M0d** de **municípios** com pelo menos 1 médico na origem, de **1 a 4 anos** depois da origem. É o intervalo
  de P10 a P90 da razão observado ÷ projetado − 1, por porte na origem e horizonte, medido na retroprojeção da própria base.
- A data intermediária usa a faixa do ano inteiro seguinte. A faixa é da base e **acompanha a intervenção** (os limites da base,
  mais o efeito da intervenção).
- As faixas de 1 e 2 anos foram conferidas fora da amostra; as de 3 e 4 anos são **limite provisório** (sem essa conferência).
- **Conjuntos de municípios:** a faixa do porte da soma, rotulada como aproximação.
- **Indisponível**, com o motivo e sem extrapolar: além de 4 anos; território em zero; estados como unidade; M0, M1, M2, M3 e a
  taxa da pessoa; porte sem retroprojeções bastantes (menos de 100 casos).

### Avisos de horizonte

Informativos, pela razão entre o tempo até a data final (H) e a janela do método (W; no M0 e no M0d, 3 anos): até W/2, normal;
até W, cautela; até 2W, extrapolação além da janela; acima, extrapolação extrema. O aviso diz os dois tempos.

### Estados de um cenário

`calculado`; `nao_aplicavel` (o método não vale para a série ou para o nível, com o motivo); `nao_calculavel` (sem registro usável,
série em zero no M3, data final ou intervenção até a origem); `retirada_acima_do_estoque`. Só o cenário calculado tem valor, texto
e curva.

## Rota

`POST /api/simulador` (formulário, como `/api/painel`): `dataset=brazil`, `dataset_version` e `options` (JSON). Só lê e calcula:
nada é registrado na sessão, e nada vai ao provedor de IA. Conta nas vagas das operações pesadas (`carga.PESADAS`).

| Opção | Conteúdo |
|---|---|
| `base`, `estados_unidade`, `conjuntos` | a seleção local, no contrato compartilhado das ferramentas (`series_brasil.selecao`), até 100 territórios |
| `brasil` | `true` acrescenta o Brasil (a contagem nacional), por último; só o Simulador aceita |
| `janela` | `{"inicio", "fim"}`, competências da base; sem ela, os 3 anos até o último registro |
| `horizonte` | a data final, `AAAAMM`, em qualquer mês depois do fim da janela (até 2100); sem ela, 2 anos depois do último registro |
| `cenarios` | até 6: `{"id", "nome", "metodo", "taxa_manual_pct"?, "janela"?, "intervencoes"?, "planejamento"?}`; `metodo` é `padrao`, `M0`, `M0d`, `M1`, `M2`, `M3` ou `manual`; sem a lista, um cenário sem intervenção no método padrão |
| `intervencoes` | até 12 por cenário: `{"tipo": "acrescimo" ou "retirada", "quantidade", "em", "ate"?, "a_cada_meses"?, "permanencia_pct_ao_ano"?, "territorios"?}` |
| `planejamento` | por cenário: `{"meta": {"tipo": "valor" ou "patamar" ou "referencia", "valor"?, "referencia"?}, "em", "ate"?, "a_cada_meses"?, "permanencia_pct_ao_ano"?}` |
| `referencias` | até 5: `{"id", "territorio": "code:…" ou "uf:…" ou "br" ou o id de um conjunto da seleção, "tipo": "fixa" ou "dinamica", "metodo"?, "taxa_manual_pct"?}` ou `{"id", "tipo": "valor", "valor", "rotulo"?}` |
| `comparacao` | `{"metrica": "quantidade" ou "taxa"}`; sem ela, a quantidade |

A resposta traz `versao`, `fonte`, `competencias`, `ultimo_registro`, `janela`, `horizonte`, `metodos`, `territorios`,
`retroprojecao` (`origens`, `faixas`, `tabela`), `notas` e `limitacoes`. Cada território traz `observado` (com o estado de cada
registro e as marcas de registro), `historico` (as estatísticas descritivas), `lacunas` e `cenarios`; cada cenário, `estado`,
`metodo` (`pedido`, `usado`, `provisorio`, `voltou_ao_m0`, `soma`), `parametros`, `avisos`, `horizonte`, `faixa`, `trajetoria`
(`data`, `anos`, `base`, `intervencao`, `total`, `retroprojecao`, `observado`, `faixa`), `final` e `texto`. Desde a etapa 5
(versão `SIMULADOR-CENARIOS/V2.2/2`), a resposta traz também `referencias` (o rótulo, o tipo, a unidade, o estado e a descrição
de cada uma) e `comparacao` (`metrica` e `hipotese_de_populacao`), e cada cenário pode trazer:

- `comparacoes` (com referências no pedido): por referência, `estado`, `descricao`, `avisos`, `pontos` (`data`, `territorio`,
  `referencia`, `diferenca`, `razao`, `indice`), `inicial`, `final`, `alcance` (`estado` e `data`) e `texto`;
- `planejamento` (com o pedido): `estado`, `meta` (`tipo`, `valor`, `rotulo`), `sem_o_plano`, `eventos`, `datas`, `por_evento`,
  `total`, `teorico_por_evento`, `resultado`, `intervencao` (pronta para voltar como intervenção) e `texto`;
- `hipotetico` (municípios): `rotulo`, `data`, `valor`, `inteiro`, `classe`, `impacto_pct` e `na_faixa`.

Erros de pedido vêm em 422, em português (seleção vazia ou acima de 100, território fora da base, competência fora da base, data
final até o fim da janela, método desconhecido, taxa manual ausente ou fora do método manual, intervenção inválida, referência
inválida, repetida ou acima de 5, métrica desconhecida, planejamento sem meta ou sem calendário, planilha enviada).

## Retroprojeção: como os métodos se saíram no passado

`scripts/calibrar_simulador.py` (fora do CI, somente leitura) refaz o estudo com a base versionada; o motor calcula a mesma
retroprojeção uma vez por versão da base. Em cada junho com 3 anos de história (jun/2017 a jun/2023, 7 origens), cada método é
ajustado **só com os registros até a origem** e confrontado com o observado 1, 2, 3 e 4 anos depois. Ficam fora os registros de
pico que volta e de quebra de fonte. Base versão `c4d82eeee4e4`, método `SIMULADOR-CENARIOS/V2.2/1`. A troca da população
de 13/11/2026 mudou a versão da base (`faa54169c5b6`) sem mudar as contagens: os números deste estudo, que só usa as contagens,
continuam valendo.

**Faixas de 80% do M0d** (P10 a P90 de observado ÷ projetado − 1), com as origens, os casos e a cobertura fora da amostra (a faixa
calculada sem uma origem, conferida nela):

| Médicos na origem | 1 ano | 2 anos | 3 anos | 4 anos |
|---|---|---|---|---|
| 1 a 9 | −26% a +48% (7 origens, 15.101 casos, 80,0%) | −31% a +72% (6, 13.362, 79,6%) | −32% a +85% (5, 11.480, 79,6%) | −31% a +104% (4, 9.395, 79,7%) |
| 10 a 19 | −23% a +29% (7, 8.727, 80,0%) | −28% a +40% (6, 7.426, 79,9%) | −29% a +53% (5, 6.147, 79,6%) | −30% a +62% (4, 4.870, 79,5%) |
| 20 a 49 | −19% a +24% (7, 7.213, 79,8%) | −23% a +34% (6, 5.999, 79,9%) | −24% a +44% (5, 4.852, 79,9%) | −25% a +55% (4, 3.824, 79,9%) |
| 50 a 99 | −15% a +20% (7, 3.000, 80,2%) | −19% a +30% (6, 2.523, 79,7%) | −20% a +42% (5, 2.054, 79,9%) | −19% a +55% (4, 1.606, 80,0%) |
| 100 a 299 | −12% a +17% (7, 2.765, 79,7%) | −16% a +26% (6, 2.296, 79,7%) | −16% a +34% (5, 1.859, 79,6%) | −17% a +42% (4, 1.452, 80,2%) |
| 300 ou mais | −7% a +10% (7, 2.133, 79,5%) | −10% a +18% (6, 1.771, 79,9%) | −12% a +25% (5, 1.422, 79,8%) | −11% a +34% (4, 1.101, 79,4%) |

São os valores recalculados que a seção 11.2 do anexo pede. Frente aos valores iniciais de lá, três células mudam em 1 ponto
(50 a 99 em 2 anos: −19%, antes −20%; 300 ou mais em 2 anos: −10%, antes −11%; 300 ou mais em 4 anos: −11%, antes −12%), e a
coluna de 3 anos passa a existir. A cobertura fora da amostra ficou entre 79,4% e 80,2% em todas as células.

**Erro absoluto médio frente ao M0** (1,00 = igual à persistência; abaixo, o método erra menos):

| Método | Médicos na origem | 1 ano | 2 anos | 3 anos | 4 anos |
|---|---|---|---|---|---|
| M0d | 1 a 9 | 1,02 | 0,96 | 0,91 | 0,87 |
| M0d | 10 a 19 | 0,98 | 0,93 | 0,88 | 0,83 |
| M0d | 20 a 49 | 0,94 | 0,88 | 0,82 | 0,78 |
| M0d | 50 a 99 | 0,89 | 0,82 | 0,77 | 0,72 |
| M0d | 100 a 299 | 0,82 | 0,74 | 0,68 | 0,64 |
| M0d | 300 ou mais | 0,63 | 0,55 | 0,49 | 0,47 |
| M1 | 1 a 9 | 1,19 | 1,26 | 1,32 | 1,37 |
| M1 | 10 a 19 | 1,19 | 1,29 | 1,35 | 1,44 |
| M1 | 20 a 49 | 1,13 | 1,22 | 1,26 | 1,27 |
| M1 | 50 a 99 | 1,09 | 1,15 | 1,16 | 1,18 |
| M1 | 100 a 299 | 0,98 | 0,99 | 0,96 | 0,97 |
| M1 | 300 ou mais | 0,73 | 0,72 | 0,75 | 0,76 |
| M2 | 1 a 9 | 1,23 | 1,21 | 1,21 | 1,21 |
| M2 | 10 a 19 | 1,21 | 1,20 | 1,20 | 1,21 |
| M2 | 20 a 49 | 1,19 | 1,13 | 1,11 | 1,09 |
| M2 | 50 a 99 | 1,12 | 1,03 | 0,99 | 0,96 |
| M2 | 100 a 299 | 1,06 | 0,93 | 0,87 | 0,81 |
| M2 | 300 ou mais | 0,81 | 0,66 | 0,61 | 0,58 |
| M3 | 1 a 9 | 1,25 | 1,29 | 1,34 | 1,38 |
| M3 | 10 a 19 | 1,26 | 1,34 | 1,39 | 1,50 |
| M3 | 20 a 49 | 1,22 | 1,27 | 1,30 | 1,32 |
| M3 | 50 a 99 | 1,19 | 1,21 | 1,24 | 1,26 |
| M3 | 100 a 299 | 1,08 | 1,07 | 0,99 | 1,00 |
| M3 | 300 ou mais | 0,83 | 0,77 | 0,81 | 0,91 |

O que o estudo sustenta e o que não sustenta:

- **O M0d como padrão dos municípios é confirmado nesta base, com ressalva.** De 2 a 4 anos, ele erra menos que a persistência em
  todos os portes. Em 1 ano, nos municípios de 1 a 9 médicos, ele erra um pouco mais (1,02): ali, o padrão não ganha da
  persistência. Por isso o método segue rotulado como **provisório**, e a persistência fica sempre à vista como referência.
- **M1, M2 e M3 erram mais que a persistência abaixo de 100 médicos** (M1: de 1,09 a 1,44). A tela avisa no M1 de municípios com
  menos de 100 médicos.
- **Viés:** a persistência subestima o crescimento do período; a deriva reduz o viés, sem zerá-lo (observado − projetado, em 4
  anos, em médicos):

  | Médicos na origem | M0 | M0d |
  |---|---|---|
  | 1 a 9 | +2,6 | +1,4 |
  | 10 a 19 | +5,2 | +2,1 |
  | 20 a 49 | +11,2 | +4,3 |
  | 50 a 99 | +28,6 | +12,8 |
  | 100 a 299 | +61,3 | +22,6 |
  | 300 ou mais | +410,5 | +98,6 |

- **Estados como unidade** (M1 de 3 anos na série do próprio nível, contra o M0; erro relativo absoluto mediano):

  | Nível | Horizonte | Casos | M1 de 3 anos | M0 |
  |---|---|---|---|---|
  | Estados | 1 ano | 189 | 1,6% | 5,9% |
  | Estados | 2 anos | 162 | 2,4% | 11,0% |
  | Estados | 4 anos | 108 | 6,0% | 20,9% |
  | Brasil | 1 ano | 7 | 0,8% | 4,8% |
  | Brasil | 2 anos | 6 | 1,7% | 9,3% |
  | Brasil | 4 anos | 4 | 3,8% | 16,9% |

  O padrão dos estados foi conferido só num período de crescimento forte e contínuo: segue **provisório**, com aviso, e sem faixa.
- **Limite de toda a validação:** as origens são de 2017 a 2023, um período em que o número de médicos cresceu em quase todo o
  país. As faixas e os erros descrevem esse período; nada garante que valham noutro regime. As origens se sobrepõem no tempo, de
  modo que os casos não são independentes.

## Exportações

- **Cenário (JSON, formato `ADT-CENARIO/1`):** a seleção local (com a composição e a versão dos conjuntos, e o Brasil, quando
  está nela), a janela, a data final, o modo e os cenários (com o planejamento inverso de cada um), as referências e a métrica,
  com a versão do método, a versão da base, o último registro e a data da exportação. **Importar** lê esse arquivo e repõe a
  configuração, sem calcular; se a base for outra versão, a tela avisa. A referência a um conjunto que não veio no arquivo fica
  de fora. O aviso de origem do Detector não é exportado.
- **Resultados (CSV, separador `;`, com BOM):** uma linha por território, cenário e data, com o observado, a base, a intervenção,
  o total e a faixa em precisão integral, e a rastreabilidade em cada linha (método pedido e usado, estado, origem, janela,
  avisos, o texto do cenário e as versões). Desde a etapa 5, também a meta do planejamento inverso, os médicos por evento (ou o
  estado, quando não há número), os eventos e o nível da hipótese do cenário em "Poucos médicos".
- **Comparações (CSV, quando há referências):** uma linha por território, cenário, referência e data, com o valor do território,
  o da referência, a diferença, a razão e o índice, o alcance no horizonte simulado, os avisos e a hipótese de população.

## Limitações

- A base só tem médicos, e o registro mais recente é jun/2024. Datas simuladas que já passaram não foram conferidas com registros.
- A contagem municipal é a de médicos registrados no município: quem atua em mais de um conta em cada um. Um conjunto é a soma das
  contagens dos componentes, nunca "médicos únicos".
- A base do cenário supõe que o passado recente continua: ela não conhece políticas, concursos, fechamentos ou choques.
- Comparar quantitativos absolutos de territórios de portes diferentes não é comparar suficiência do atendimento.
- A faixa de 80% só existe para o método padrão dos municípios, até 4 anos, e vem de um único período histórico.
- O padrão do Brasil e o dos estados (a taxa composta de 3 anos) são provisórios e não têm faixa.
- A referência dinâmica usa o método padrão provisório do nível dela, com a janela geral do pedido; na tela, ela não tem método,
  janela nem intervenções próprios (a rota aceita outro método).
- A comparação por taxa vale só com a hipótese de população constante: a base não traz população futura.
- O planejamento inverso responde a uma conta, não a uma pergunta de política: ele não sabe se os médicos existem, se ficam, nem
  quanto custa.
- Uma intervenção vale para cada território do cenário; o número do planejamento inverso é próprio de cada território, e por
  isso só pode ser usado como intervenção com um território só na seleção local.

**Assistente de conversa.** Ele continua recusando previsões e projeções livres (AT-04) e não monta cenários. Desde 11/11/2026,
na base do Brasil, a recusa indica o caminho: "Para montar cenários hipotéticos, que não são previsão, há o Simulador de
Cenários, na linha Ferramentas da área de análise: nele, você escolhe o método, as hipóteses e a data final." Com uma planilha
enviada, em que o Simulador não existe, a recusa não o cita.

## Testes

- pytest: `backend/tests/test_simulador.py` — as fórmulas em séries sintéticas (M0 e M0d; zero e ausência; a quebra de fonte e a
  volta ao M0; M1 com o tempo real e a recusa do início em zero; M2, M3 e os ajustes em lote; a taxa da pessoa; as intervenções
  somadas à base, a permanência e a retirada impossível; conjuntos e estados; a média aritmética só descritiva; os avisos de
  horizonte; as faixas pela retroprojeção com origens móveis; o ajuste sem observações posteriores à janela), a rota com um
  catálogo sintético (inclusive o Brasil como território, as referências com o alcance e a sobreposição, a comparação por
  taxa, o planejamento inverso reaplicado ao Simulador, a hipótese do cenário e as recusas) e, no job `dados-reais`, a base
  versionada (as faixas e os erros acima, o Distrito Federal, Rio Rufino/SC, São Paulo como unidade, o limite de 100
  territórios, o Brasil, as referências de Manaus, o planejamento inverso e "Simular recuperação" em Abreulândia/TO).
- pytest: `backend/tests/test_dialogo.py` — a recusa de projeção indica o Simulador só na base do Brasil.
- Node: `frontend/tests/simulador.test.mjs` — as datas, a seleção local, o que falta para calcular, o pedido ao motor, a leitura
  da resposta, os textos da tabela e da faixa, a importação e a exportação do cenário e o CSV; o Brasil na seleção local, as
  referências e a métrica, o planejamento inverso, a configuração com que o Detector abre o Simulador, a hipótese do cenário e o
  CSV das comparações.
- Navegador: `backend/tests/ui_simulador.py` (suíte `base-versionada`), com "Abrir no Simulador", o Brasil, as referências e o
  planejamento inverso; "Simular recuperação" está em `backend/tests/ui_detector.py`.
