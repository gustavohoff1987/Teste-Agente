# Proposta conceitual e metodológica — Versão 2.2
## Simulador de Cenários Territoriais e Detector de Sinais Territoriais

**Projeto:** Agente Diagnóstico Territorial da Força de Trabalho na Saúde  
**Data:** 9 de novembro de 2026  
**Estado:** proposta metodológica **aprovada pelo responsável para implementação** pelo comando integrado V22 (9/11/2026), com o Simulador como exceção aprovada à exclusão de projeção da SPEC (seção 2.5); limiares e métodos marcados como candidatos continuam sujeitos à calibração  
**Base de elaboração:** discussão conceitual com o responsável pelo projeto; proposta inicial em Markdown (v1); parecer “Avaliação crítica — Simulador de Cenários e Detector de Fragilidades Territoriais” (Claude Opus, 9/11/2026); análise crítica subsequente desse parecer; e “Avaliação crítica da Proposta V2”, feita com consulta somente leitura à base real do repositório Teste-Agente (9/11/2026), cujos quatro ajustes esta versão incorpora; e o documento “Métodos estatísticos do Detector e do Simulador — explicação e amparo científico” (9/11/2026), de onde vem o quinto ajuste; e a “Avaliação do Comando Integrado V2.1 para o Claude Code” (9/11/2026), com revisão estatística dos parâmetros na base real, de onde vêm as definições operacionais da v2.2.  
**Escopo informacional:** a base histórica discutida contém **exclusivamente médicos**, com observações em **janeiro e junho de 2014 a 2024**. A disponibilidade efetiva de cada variável, a unidade de contagem e as lacunas devem ser verificadas na base e no código.

> **Finalidade desta versão.** Incorporar as contribuições metodológicas aproveitáveis do parecer sem descaracterizar as duas ferramentas. O Detector deve continuar capaz de **descrever sinais e tendências**, mesmo quando não constituam alterações estatisticamente raras. O Simulador deve continuar **configurável pelo usuário**, mas com métodos matematicamente consistentes, intervenções separadas das tendências históricas e comunicação explícita da incerteza.

> **Versão 2.1.** Incorpora os quatro ajustes que a avaliação da v2 com a base real (2014–2024) indicou como condição para seguir à especificação: (a) afastamento de 15% no indicador 7 como atenção, alerta só com excepcionalidade e indicador descritivo abaixo de 20 médicos; (b) estado “descontinuidade de registro” restrito a picos que voltam e a quebras de fonte, com as quedas que persistem mantidas alertáveis; (c) desaceleração unificada com a classe que o Agente já calcula; (d) persistência com deriva do estado (M0d) como método padrão candidato, com faixas empíricas por porte. Inclui ainda um quinto ajuste, vindo da revisão dos métodos estatísticos e também verificado na base: (e) a média aritmética das taxas fica só como estatística descritiva, e o “percentual médio” para projetar passa a ser a taxa composta (M1). As demais partes da v2 só mudaram onde era preciso para manter a coerência com esses ajustes (seção 18.2).

> **Versão 2.2.** Decisões do responsável de 9/11/2026, depois da avaliação do comando integrado: (1) o Detector passa a se chamar **Detector de Sinais Territoriais**; a terceira camada passa a ser **sinal analítico** e as classes, **intensidade do sinal** (atenção, alta, crítica); (2) o Simulador é **exceção aprovada** à exclusão de projeção da SPEC (seção 2.5); (3) entram as **definições operacionais** da revisão estatística (seções 4.2 e 8.8), que prevalecem sobre o texto anterior quando houver divergência; (4) ficam definidos padrões provisórios para estados, Brasil e conjuntos no Simulador e a regra do estado como unidade na seleção (seções 8.8 e 13). Mudanças na seção 18.1.
>
> **Seções normativas:** 2 a 14 e 16. As seções 1.1, 17, 18 e 19 são registro histórico.

---

## 1. Síntese executiva e decisões das versões 2, 2.1 e 2.2

Esta revisão adota uma separação essencial entre três camadas, que **não são equivalentes**:

1. **Fato observado:** mudança nos registros de médicos (ex.: 10 → 7, −3 médicos, −30%). Independe de um teste estatístico para ser exibido.
2. **Excepcionalidade estatística:** verifica se a mudança excede a oscilação habitual estimada para territórios comparáveis, considerando o porte, o intervalo temporal e as propriedades reais da base.
3. **Sinal analítico:** caracteriza baixa redundância, deterioração persistente, deterioração relativa ou outra condição definida por critérios transparentes. Não é juízo de desassistência ou prioridade de alocação.

**Encaminhamentos adotados (v2, com os ajustes da v2.1 e da v2.2):**

- Preservar o **catálogo dos 12 fenômenos originais**, ainda que os indicadores 1 e 2 sejam operacionalmente fundidos e alguns fenômenos permaneçam descritivos, condicionais ou derivados, em vez de gerar automaticamente alertas.
- Fundir *dependência de poucos médicos* e *ausência de médicos registrados* na **escala estrutural**, distinguindo zero verdadeiro de registro ausente; preservar a duração da ausência como atributo.
- Incorporar **magnitude + excepcionalidade** como regra candidata para alertas de mudança extraordinária, sem ocultar eventos observados que não atinjam essa condição.
- Preservar **desaceleração** e **instabilidade** como fenômenos analíticos. Desaceleração usa a **mesma definição da classe “Desaceleração do crescimento”** que o Agente já calcula na Análise de Tendência e pode gerar atenção condicionada à persistência, mas não intensidade extrema isoladamente; instabilidade começa descritiva.
- Não construir **índice geral único de criticidade**. Exibir perfis por dimensão e sinais combinados com regras explícitas e sem contagem duplicada do mesmo evento.
- **Nome (v2.2):** Detector de Sinais Territoriais. “Alerta” fica reservado ao que passa em magnitude e excepcionalidade; os demais achados são sinais, e o fato observado continua sempre visível.
- **Exceção da SPEC (v2.2):** o Simulador projeta cenários por ser exceção aprovada à exclusão de projeção (FAM-08, Caso 4), só na ferramenta determinística; o assistente de conversa continua recusando previsões livres (seção 2.5).
- Preservar a **seleção territorial principal**, herdada pelo Simulador como cópia local; permitir edição e seleção de referências dentro dele.
- Preservar seleção livre de **datas históricas efetivamente disponíveis**, métodos, intervenções, referências e horizonte de simulação; sem listas rígidas de 3, 5 ou 10 anos.
- Adotar como **método padrão candidato** a **persistência com deriva do estado (M0d)**, indicada pela retroprojeção na base real; manter **M0 persistência** como referência obrigatória e **M1 taxa composta**, **M2 tendência linear robusta** e **M3 tendência log-linear** como alternativas; a confirmação do padrão segue a avaliação retrospectiva. Manter a **média aritmética das taxas só como estatística histórica descritiva**, ao lado da taxa composta: ela não é usada para projetar, nem como cenário exploratório, porque superestima o crescimento quando as taxas oscilam. O “percentual médio” pedido para as simulações é a **taxa composta (M1)**.
- Separar matematicamente **trajetória-base** e **intervenções hipotéticas**; explicitar hipóteses de permanência dos médicos adicionados.
- Mostrar incerteza quando houver calibração suficiente e indicar **“faixa indisponível”** quando não houver evidência para estimá-la adequadamente; não inventar intervalos.
- Tratar dados observados até **junho de 2024** como históricos. Projeções após essa data não representam observações atuais de novembro de 2026.
- A implementação foi autorizada pelo comando integrado V22 (9/11/2026). O documento não autoriza mudanças em CI/CD, Cloud Run, GitHub Pages, infraestrutura ou custos.

### 1.1. Quadro de acolhimento do parecer do Opus

| Tema | Tratamento na v2 | Fundamentação resumida |
|---|---|---|
| Limiares percentuais uniformes | **Reformular** | Um mesmo percentual tem comportamento estatístico diferente conforme o quantitativo inicial. |
| Regra de magnitude + excepcionalidade | **Acolher parcialmente** | Apropriada a alertas extraordinários; não deve silenciar perdas observadas ou a condição estrutural. |
| Unificação de 1 + 2 | **Acolher** | Zero confirmado não pode ficar sem classificação enquanto um médico é classificado. |
| Redução do Detector a quatro indicadores | **Não acolher integralmente** | Diferenciar indicador exploratório de indicador classificatório; manter catálogo mais amplo. |
| Desaceleração e instabilidade | **Preservar, com cautela** | São sinais interpretativamente úteis, ainda que não justifiquem alerta crítico automático. |
| Índice global de criticidade | **Não adotar na v2** | Evitar somar manifestações do mesmo evento e induzir ranking assistencial indevido. |
| Substituição da média aritmética como projeção padrão | **Acolher** | A média de percentuais não recompõe corretamente a taxa acumulada. |
| Métodos M0–M3 | **Acolher como candidatos** | Comparar desempenho retrospectivo e transparência, sem presumir superioridade. |
| Faixas de incerteza | **Acolher condicionadamente** | Exibir apenas quando sustentadas por validação retrospectiva suficiente. |
| Validação populacional prévia | **Acolher por operação** | Permitir cálculos válidos em períodos comparáveis; bloquear apenas inferências inválidas. |
| Implementação por fases | **Acolher com integração desde o desenho** | Definir contratos comuns de seleção, agregação, referência e cenários previamente. |

### 1.2. Ajustes da versão 2.1 — avaliação com a base real

A avaliação da v2 aplicou as regras propostas à base municipal de 2014–2024 (5.570 municípios, 22 registros), com consulta somente leitura ao repositório. A v2 pode seguir para a especificação com quatro ajustes, de (a) a (d). O ajuste (e) veio depois, da revisão dos métodos estatísticos, e foi verificado na mesma base:

| Ajuste | O que muda | Evidência na base real |
|---|---|---|
| **(a) Indicador 7** | Afastamento ≥15% do patamar passa a ser **atenção**; alerta alto ou crítico exige também **excepcionalidade** para o porte; abaixo de **20 médicos** no patamar, o indicador fica **descritivo** enquanto a calibração não mostrar que o teste discrimina nessa faixa (seção 4.1, item 7) | Com 15% como alerta alto, 691 municípios (12%) teriam alerta alto ou crítico de trajetória em jun/2024, entre eles 47% dos que têm até 3 médicos; com 15% como atenção, 401. Dos sinalizados pelo indicador 7 em jun/2022, 64% já não estavam 15% abaixo do patamar dois anos depois |
| **(b) Descontinuidade de registro** | Novo estado, restrito a **picos que voltam** e **quebras de fonte**: essas transições não geram alerta e saem da calibração. Quedas grandes que persistem continuam alertáveis, com a nota **“verificar registro”** (seção 2.4) | Na definição ampla (salto ou queda de 10 ou mais médicos que dobra a contagem ou a corta à metade), são 203 municípios, mas só 10 têm pico que volta em até dois registros, como Rio Rufino (SC): 4 → 87 → 5 médicos entre jan/2023 e jan/2024. Tratar toda queda grande como descontinuidade retiraria 42% dos alertas críticos de perda abrupta de 2014–2024 |
| **(c) Desaceleração** | O indicador 4 passa a usar a classe **“Desaceleração do crescimento”** da Análise de Tendência (CAP-TEN-01), na mesma série e janela; a atenção deriva dessa classe, sem regra paralela (seção 4.1, item 4) | A regra separada da v2 marcava 263 municípios e a classe do Agente, 182; só 17 coincidiam (114 sem a confirmação exigida pela v2) |
| **(d) Método padrão do Simulador** | **M0d, persistência com deriva do estado**, passa a ser o padrão candidato, com **faixas empíricas por porte e horizonte**; M0 segue como referência e M1–M3 como alternativas (seções 8.2 e 11.2) | Nas retroprojeções (origens de jun/2017 a jun/2023), M0d errou de 13% a 44% menos que M0 em 4 anos e menos que M1–M3 em todos os portes e horizontes; em 1 ano, abaixo de 20 médicos, empatou com M0 |
| **(e) Média aritmética das taxas** | Passa a ser **só estatística descritiva**, ao lado da taxa composta; sai o cenário exploratório que a usava como taxa hipotética. O “percentual médio” para projetar é a **taxa composta (M1)** (seção 8.6) | Nas retroprojeções (origens de jun/2017 a jun/2023, janela de 3 anos), a média aritmética nunca ficou abaixo da taxa composta e errou mais que ela em todos os portes e horizontes: de 3% a 5% mais em 1 ano e de 4% a 29% mais em 4 anos. Na janela de jun/2020 a jun/2024, aumentaria a projeção de 4 anos em 9% na mediana dos municípios com 1 a 9 médicos (50% no percentil 90) |

Os números vêm da avaliação de 9/11/2026 e, no ajuste (e), do script `media_aritmetica.py` do mesmo anexo. Eles justificam os ajustes; os parâmetros finais continuam sujeitos à calibração da seção 6.

---

## 2. Escopo, dados e limites das inferências

### 2.1. Dados de referência

- **População profissional analisada:** médicos, exclusivamente. Nenhum indicador será definido sobre enfermeiros, fisioterapeutas ou múltiplas categorias profissionais nesta base.
- **Período informado:** janeiro e junho de cada ano de **2014 a 2024**; potencial de **22 registros** quando não houver lacunas, do início de jan/2014 ao início de jun/2024, ou seja, aproximadamente **10 anos e 5 meses** entre datas nominais.
- **Unidade territorial central:** município; a aplicação também admite seleções de estados e conjuntos territoriais, cuja semântica de agregação deve ser preservada.
- **Unidade do quantitativo:** **a conferir** se corresponde a médicos distintos por município, vínculos, registros ou outra medida da extração. Enquanto isso, rótulos públicos devem evitar afirmar mais do que a definição confirmada.
- **Variáveis auxiliares:** taxas por população, posições relativas e geografia são condicionadas à efetiva disponibilidade de denominadores populacionais temporalmente comparáveis, coordenadas apropriadas e definição estável do universo de comparação.

### 2.2. Datas: não confundir observações com semestres de seis meses

- Janeiro → junho: intervalo nominal de **5 meses**.
- Junho → janeiro seguinte: intervalo nominal de **7 meses**.
- Séries anuais por **média de janeiro e junho** podem ser úteis para tendências, mas só devem ser construídas quando ambas as observações existirem e após testar a presença de efeito sazonal ou de calendário. Essa média é uma **transformação analítica**, não um novo dado original.
- Eventos abruptos devem ser avaliados entre observações consecutivas com critérios específicos por duração da transição; não anualizar automaticamente perdas de um único evento.
- Para taxas equivalentes e modelos temporais, utilizar duração real ou convencionada de modo explícito entre as datas de referência; datas não existentes jamais devem aparecer como valores observados.
- “Últimos quatro semestres” é ambíguo na linguagem dos dados; a interface deve preferir **“últimos quatro registros”**, informar as datas e, quando solicitados anos-calendário, explicitar quantos registros foram incluídos.
- Seleção de **qualquer registro inicial e final existentes** na base, sem janelas arbitrariamente pré-fixadas. Presets são apenas atalhos.

### 2.3. Restrições interpretativas obrigatórias

Não inferir automaticamente: desassistência; insuficiência assistencial; qualidade ou cobertura efetiva dos serviços; *isolamento territorial/assistencial*; capacidade de atendimento ou fluxos de referência; rotatividade de pessoas a partir de contagens agregadas; quantidade de médicos únicos em conjuntos pela soma simples de municípios; necessidade normativa de provimento; causalidade de eventos históricos identificados como coincidências temporais.

Distância geodésica não equivale a tempo de deslocamento, integração em rede regionalizada ou disponibilidade real de atendimento. Municípios com poucos registros de médicos não podem ser rotulados como “sem cobertura assistencial”.

### 2.4. Lacunas e estados de avaliação

Cada resultado deve distinguir: **valor observado**, **zero confirmado**, **ausência de dado**, **descontinuidade de registro**, **não aplicável**, **não calculável**, **janela insuficiente**, **denominador não comparável**, **referência inválida** e **não classificado por falta de calibração**. Nenhuma dessas situações deve virar silenciosamente “sem sinal”.

**Descontinuidade de registro (v2.1).** Estado restrito a dois casos:

- **Pico que volta:** salto de 10 ou mais médicos que ao menos dobra a contagem e se desfaz em até dois registros, voltando a até 125% do valor anterior ao salto (critério candidato). Quando o salto ocorre, recebe a nota **“verificar registro”**; se a volta se confirma, o par salto–volta passa a esse estado. Na base, são 10 municípios; exemplo: Rio Rufino (SC), 4 → 87 → 5 médicos entre jan/2023 e jan/2024.
- **Quebra de fonte:** série municipal incompatível com a fonte estadual ou mudança de fonte documentada. Critério objetivo inicial: soma municipal da UF abaixo do total de médicos únicos da própria UF. Na base, só o Distrito Federal em 2014–2017: Brasília somava de 4.070 a 5.044 médicos, contra 7.764 a 8.385 únicos na fonte estadual, e saltou para 8.851 em jan/2018.

Efeitos: o fato continua exibido, com a marca; a volta do pico não gera alerta de perda; as transições marcadas saem da calibração; o registro do pico fica fora dos ajustes de tendência e projeção; e a janela padrão começa depois de uma quebra de fonte. **Quedas grandes que persistem não recebem esse estado:** uma queda de 10 ou mais médicos que leva a contagem à metade ou menos e não se desfaz recebe só a nota “verificar registro” e continua alertável. Tratar toda queda grande como descontinuidade retiraria 42% dos alertas críticos de perda abrupta de 2014–2024; além disso, 86% das transições da definição ampla não se desfazem em dois anos.

### 2.5. Exceção da SPEC para projeção (v2.2)

A SPEC exclui “projeção ou previsão (Caso 4)” da família FAM-08, e o critério AT-04 manda não projetar. Em 9/11/2026, o responsável aprovou o Simulador como **exceção**, com estes limites:

- vale só para a ferramenta determinística do Simulador, com cenários rotulados como hipotéticos e condicionais (seção 11.3);
- o assistente de conversa continua recusando pedidos livres de projeção ou previsão (AT-04) e pode indicar o Simulador como caminho;
- o texto de cada cenário segue um modelo fixo, por exemplo: “Cenário hipotético, não é previsão: com o método [método] e as premissas [premissas], [território] teria [N] médicos em [data]. Base: registros até [última competência].” Só os textos gerados por esse modelo, dentro do Simulador, passam pela guarda de fidelidade como cenário; a guarda continua recusando previsões em qualquer outro texto;
- a exceção é registrada como divergência aprovada; a SPEC não é editada.

---

## 3. Arquitetura funcional das duas ferramentas

### 3.1. Detector de Sinais Territoriais

**Função:** revelar a disponibilidade numérica, os processos de deterioração, a posição relativa e sinais contextuais da distribuição territorial de médicos. Produzir explicações reproduzíveis para fatos observados e, quando calibrado, níveis de intensidade por fenômeno ou dimensão.

### 3.2. Simulador de Cenários Territoriais

**Função:** criar trajetórias futuras condicionais a métodos históricos, janelas configuráveis, hipóteses explícitas de alteração da tendência, acréscimo e retirada de médicos, bem como referências territoriais fixas ou dinâmicas. Comparar cenários dentro do mesmo território e entre territórios.

### 3.3. Integração bidirecional

- **Detector → Simulador:** transportar território/conjunto, versão da seleção, janela histórica, quantitativos, indicadores acionados e suas regras; permitir o botão **“Simular cenários”** ou **“Simular recuperação”**.
- **Simulador → Detector:** recalcular apenas métricas pertinentes à trajetória **hipotética** (ex.: quantitativo, dependência de um profissional, diferença para referência). Não aplicar mecanicamente critérios de *eventos observados* ou de flutuação estatística a curvas suavizadas projetadas.
- **Rastreabilidade:** referência de fonte, período, versão de limiares, métodos, intervenções, composição de conjuntos e premissas devem acompanhar tabelas e exportações.

---

## 4. Detector: catálogo dos 12 fenômenos e posição metodológica

> Os números 1–12 são mantidos para rastreabilidade com a versão inicial. **Indicadores 1 e 2 formam uma única escala estrutural**, mas ambos permanecem identificáveis no catálogo conceitual.

| Nº | Fenômeno | Produto analítico v2.1 | Classificação na v2.1 | Dependência principal |
|---:|---|---|---|---|
| 1 | Dependência de poucos médicos | Percentual potencial `100/N` e escala por `N` | **Estrutural**, com classe convencional explícita | Quantitativo atual válido |
| 2 | Ausência persistente de médicos registrados | Zero atual e duração da sequência em zero | **Fundido ao 1**, persistência como atributo | Distinguir zero e ausente |
| 3 | Declínio persistente | Quedas sucessivas e inclinação negativa sustentada | **Candidato a alerta**; mudanças sempre descritas | Série válida e calibração por porte |
| 4 | Desaceleração do crescimento | Classe “Desaceleração do crescimento” da Análise de Tendência (CAP-TEN-01), na mesma série e janela | **Descritivo + atenção condicionada à persistência da classe** | Quatro observações anuais válidas (série de junho) |
| 5 | Instabilidade temporal | Dispersão e alternância ajustadas ao porte | **Descritivo**, sem intensidade alta/crítica automática | Dispersão empírica por porte |
| 6 | Perda abrupta de médicos | Evento de redução entre registros | **Candidato a alerta** por magnitude + excepcionalidade | 5/7 meses e porte |
| 7 | Afastamento de patamar anterior | Distância ao patamar robusto histórico | **Atenção** por magnitude; **alerta** só com excepcionalidade; **descritivo** abaixo de 20 médicos no patamar; não usar pico isolado | Série histórica suficiente e calibração por porte |
| 8 | Deterioração da disponibilidade relativa | Redução na taxa médicos/população | **Condicional** | Série populacional compatível |
| 9 | Deterioração da posição relativa | Queda de posição percentílica em universo estável | **Condicional** | Denominador; universo estável |
| 10 | Ampliação da defasagem ante referência | Queda no índice relativo ao comparador | **Condicional / preferencialmente comparativo** | Referência e denominador válidos |
| 11 | Distância geográfica a territórios com maior disponibilidade médica | Distância geodésica e percentil contextual | **Somente contexto; sem classe assistencial** | Coordenadas e critério explícito |
| 12 | Coexistência de sinais | Perfil por dimensão + sinais combinados rastreáveis | **Derivado; sem escore geral** | Evitar dupla contagem |

### 4.1. Critérios operacionais sugeridos — parâmetros **não validados**

Esta seção propõe valores testáveis, não parâmetros definitivos. Em cada indicador, separar **critério de exibição do fato**, **critério de atenção** e **critério de alerta de mudança extraordinária**, quando aplicável.

#### 1–2. Escala estrutural unificada

- `N = 0` **confirmado**: classe estrutural **crítica**, com atributo “ausência de médicos registrados” e duração da sequência de zeros (em observações e meses).
- `N = 1`: **crítica**; perda hipotética de um médico representa 100% do quantitativo.
- `N = 2–3`: **alta**; impacto potencial de 50% ou 33,3%.
- `N = 4–5`: **atenção**; impacto potencial de 25% ou 20%.
- `N ≥ 6`: **sem sinal estrutural pelas faixas acima**, não significa suficiência assistencial.
- **Histerese candidata:** agravo imediato; melhora de classe consolidada somente após **duas observações válidas consecutivas**, mas mostrar imediatamente a melhora do valor observado.
- A interpretação `100/N` descreve perda *numérica hipotética* de um registro/profissional, não percentual da população que ficaria sem atendimento. A denominação pública deve respeitar a unidade efetiva da extração.

#### 3. Declínio persistente

- **Exibição:** qualquer perda observada e sua magnitude absoluta/relativa, com datas.
- **Duas formas de detecção:** (a) sequência de reduções em observações anuais comparáveis; (b) **tendência negativa sustentada** que tolere pequenas recuperações intermediárias.
- **Parâmetros candidatos:** duas reduções anuais e perda acumulada ≥10% para sinal forte; três reduções anuais e perda ≥20% para sinal muito forte. Para a alternativa por tendência, exigir inclinação negativa, magnitude acumulada equivalente e duração mínima definida em calibração.
- **Excepcionalidade:** avaliar dispersão de quedas ou inclinações em territórios de porte semelhante; não fazer depender a descrição da queda do teste de excepcionalidade.
- Preferir registros anuais homólogos ou série anual construída validamente; janelas curtas retornam “série insuficiente”.

#### 4. Desaceleração do crescimento

- **Definição unificada (v2.1):** o fato descritivo é a classe **“Desaceleração do crescimento”** que o Agente já calcula na Análise de Tendência (CAP-TEN-01, DA-15): pelo menos quatro observações válidas; velocidades `vᵢ = (yᵢ₊₁ − yᵢ) / (tᵢ₊₁ − tᵢ)`, com o tempo real entre registros; todas as velocidades positivas e não crescentes, com ao menos uma redução estrita; comparação em aritmética racional exata. Usa a mesma série (anual de junho, por padrão) e a mesma janela da Análise de Tendência, para que as duas telas nunca mostrem rótulos diferentes para o mesmo território.
- **Leitura da família:** se alguma velocidade for negativa, a leitura deixa de ser desaceleração do crescimento e passa a declínio ou a mudança de direção, conforme as classes existentes; “Desaceleração de declínio” pertence à família do declínio e não alimenta este indicador.
- **Atenção condicionada (candidata):** a classe se repete em **duas avaliações anuais consecutivas** (janela atual e janela deslocada um ano para trás). Se também for exigida magnitude, como a queda de ritmo ≥30% e ≥2 pontos percentuais anuais proposta na v2, ela é medida dentro da própria classe, sobre as mesmas velocidades, e nunca como regra paralela.
- **Sem classe crítica isolada**; mostrar as velocidades, a persistência e a possível associação com declínio ou dependência estrutural.
- **Motivo do ajuste:** na base real, a regra separada da v2 marcava 263 municípios e a classe do Agente, 182, com só 17 em comum (114 sem a confirmação exigida pela v2). O critério de persistência ainda precisa de avaliação de sensibilidade na base real antes de virar padrão.

#### 5. Instabilidade temporal

- **Exibição:** alternância entre mudanças positivas/negativas e uma medida de dispersão relativa à esperada para porte e intervalo.
- Não utilizar a simples regra de “duas inversões em quatro registros” para gerar intensidade alta: pode ocorrer com frequência por oscilação aleatória.
- **Candidato estatístico:** razão entre dispersão observada e dispersão esperada, estimada de forma robusta por faixa de porte; definir limiares apenas depois do perfil real.
- **Finalidade adicional:** avisar que projeções para aquele território podem ser menos estáveis. Não chamar isso de rotatividade individual.

#### 6. Perda abrupta

- **Exibição:** toda perda entre observações consecutivas, sempre como `−X médicos (−Y%)` e datas reais.
- **Regra dupla candidata para alerta alto:** redução ≥ `máx(2 médicos; 20% do N anterior)` **e** alteração incomum para o porte/tipo de intervalo.
- **Regra dupla candidata para crítico:** redução ≥ `máx(3 médicos; 30% do N anterior)` **e** alteração muito incomum, com critério calibrado.
- **Excepcionalidade inicial para teste:** caudas unilaterais da distribuição de redução por grupos de porte e duração (5 ou 7 meses), com metas exploratórias de 1% e 0,1% por avaliação. Não tratar estes percentuais-alvo como decisão fechada nem pressupor normalidade.
- Não excluir automaticamente `N < 10`; apenas explicitar baixa capacidade de distinguir flutuação habitual de alteração extraordinária. Para pequenos quantitativos, a escala estrutural continua informativa.
- **Registro (v2.1):** a volta de um pico em **descontinuidade de registro** (seção 2.4) não gera alerta de perda. Uma queda de 10 ou mais médicos que leva a contagem à metade ou menos recebe a nota **“verificar registro”**, mas continua sujeita à regra dupla.

#### 7. Afastamento de patamar anterior

- Substituir “recuperação insuficiente”, que pressupõe trajetória de recuperação, por **“afastamento de patamar anterior”**.
- **Patamar candidato:** maior **média de dois anos consecutivos** completos dentro da janela histórica escolhida, evitando máximos pontuais isolados. Deve ser anterior ao período corrente e ter composição/definição comparáveis.
- **Exibição:** diferença absoluta, diferença percentual, duração abaixo do patamar e, quando houver recuperação identificável, fração recuperada desde o vale.
- **Níveis (v2.1):**
  - **Atenção:** afastamento ≥15% do patamar, persistente por duas observações. Esse afastamento, sozinho, não gera mais alerta alto.
  - **Alta:** afastamento ≥15% por duas observações **e** incomum para o porte (cauda unilateral da distribuição empírica do afastamento por faixa de porte; meta inicial de 1% por avaliação, calibrada com origens móveis).
  - **Crítica:** afastamento ≥30% por quatro observações **e** muito incomum (meta inicial de 0,1%, com faixas de porte agrupadas quando faltarem casos para estimar a cauda).
  - **Abaixo de 20 médicos no patamar:** indicador **descritivo** (fato exibido, sem nível de intensidade), salvo se a calibração mostrar que o teste de excepcionalidade distingue flutuação de mudança nessa faixa. Com poucos médicos, o patamar é fácil de perder: passar de uma média de 4 para 3 já é 25% abaixo. A escala estrutural continua informativa.
- Não reutilizar o máximo histórico bruto como padrão, devido à seleção de picos por flutuação.
- **Motivo do ajuste:** na base real (jun/2024), contar o afastamento de 15% como alto daria alerta alto ou crítico de trajetória a 691 municípios (12%), entre eles 47% dos que têm até 3 médicos; como atenção, seriam 401. Dos 658 municípios sinalizados pelo indicador 7 em jun/2022, 64% já não estavam 15% abaixo do patamar dois anos depois.

#### 8. Deterioração da disponibilidade relativa

- `taxa = médicos registrados / população × base` (ex.: por 10 mil ou 100 mil habitantes, sempre identificada).
- **Convenções candidatas:** queda ≥10% no intervalo validado de pelo menos dois anos (alta) e ≥20% (crítica), sujeitas à calibração e a condições complementares.
- Diferenciar decomposição da mudança: variação de médicos, de população e da taxa. Havendo quebra de método populacional, marcar **“comparação não habilitada”** para esse cruzamento; não interpolar silenciosamente.
- Comparações pontuais em datas válidas podem continuar disponíveis mesmo se a série histórica completa não estiver harmonizada.

#### 9. Deterioração da posição relativa

- Computar **posição percentílica** em universo comparável fixo e identificável (ex.: municípios de uma UF, do Brasil ou de determinado grupo); definir regra estável para empates.
- Posição por **taxa de médicos por população** é a opção prioritária para leitura de disponibilidade relativa; posição por **quantitativo absoluto** é outra análise e deve permanecer opcional e explicitamente rotulada.
- **Convenções candidatas:** atenção para queda de 10 a <15 pontos percentílicos; alta se queda ≥15 p.p. e posição final ≤P50; crítica se queda ≥25 p.p. e posição final ≤P25, confirmada em duas avaliações anuais.
- Não misturar conjuntos territoriais e municípios no mesmo universo de percentis. Suavização estatística de taxas em pequenos municípios pode ser oferecida como **medida ajustada paralela**, nunca substituindo silenciosamente o valor observado.

#### 10. Ampliação da defasagem ante referência

- `indice_relativo(t) = 100 × indicador_territorio(t) / indicador_referencia(t)` quando a referência é positiva e comparável.
- **Convenções candidatas:** alta se queda no índice ≥15 pontos e índice final <80; crítica se queda ≥25 pontos e final <60, respeitada janela de comparação definida (inicialmente dois anos para teste).
- Disponibilizar referências fixas e dinâmicas; as referências escolhidas pelo usuário podem gerar **comparações exploratórias personalizadas**, não classificação automática de intensidade oficial.
- Quando o comparador for um agregado que contém o próprio município, explicitar esse fato; para comparação independente, oferecer cálculo do agregado **excluindo o município analisado**, quando tecnicamente possível. Nunca declarar independência inexistente.

#### 11. Distância geográfica a territórios com maior disponibilidade médica

- **Somente contextual:** distância geodésica a um território que atenda ao critério de quantitativo ou taxa definido pelo usuário.
- Utilizar coordenadas adequadas e informar referência geográfica adotada (preferencialmente sede municipal quando disponível), universo de busca, distância e método.
- Pode-se mostrar o percentil da distância em um conjunto comparável, **sem converter distância em classe de intensidade nem em juízo assistencial**.
- Evitar “isolamento territorial”, “desassistência”, “sem cobertura” e inferências sobre organização da rede regionalizada.

#### 12. Coexistência de sinais

- Produzir **perfil** e **sinais combinados pré-definidos**, sem soma automática de pontos e sem classe geral única.
- Exemplos candidatos: (a) escala estrutural alta/crítica + perda abrupta observada; (b) escala estrutural alta/crítica + declínio persistente; (c) declínio sustentado + deterioração relativa comprovada, **sem tratá-los automaticamente como eventos independentes**; (d) afastamento de patamar com dependência estrutural.
- Um mesmo evento pode afetar quantitativo, densidade, percentil e defasagem. A interface deve agrupar os efeitos como **um evento com múltiplas repercussões**, não como quatro evidências independentes.
- Um sinal combinado só recebe nome e regra próprios após definição de elegibilidade e testes retrospectivos; não resulta automaticamente em recomendação de alocação.

### 4.2. Definições operacionais do Detector (v2.2)

Vêm da revisão estatística de 9/11/2026, feita na base real. Prevalecem sobre o texto das seções 2.4, 4.1, 5.3 e 6 quando houver divergência. Os números marcados como candidatos continuam sujeitos à calibração.

| Item | Definição operacional |
|---|---|
| Escala estrutural (1–2) | Faixas da seção 4.1. Com N = 0, o impacto `100/N` é “não calculável”. |
| Histerese | Classe exibida em t = a mais grave entre as duas últimas observações válidas: a piora aparece na hora; a melhora, só depois de duas observações. |
| Declínio persistente (3) | Série de junho; reduções **consecutivas**; perda medida desde o primeiro valor da sequência. Duas reduções e perda ≥ 10%: forte; três reduções e perda ≥ 20%: muito forte. Fica como “sinal observado” até a calibração. A alternativa “por tendência” sai até ganhar parâmetros. |
| Desaceleração (4) | Classe “Desaceleração do crescimento” do Agente (`classify_frame`, em `backend/trend.py`), calculada nos **4 junhos até o junho avaliado** e atualizada só em junho. Na última competência, coincide com a Análise de Tendência na série anual. A atenção por persistência (a classe se repete na janela de 4 junhos encerrada um ano antes) é **exploratória**: na base, dá 16 municípios em 2024, menos que o esperado ao acaso, e não prevê o crescimento seguinte. Aqui, “calibração” significa **análise de sensibilidade**; magnitude, se usada, em taxa relativa. |
| Instabilidade (5) | Descritiva. Candidato: desvio-padrão das variações entre registros ÷ c·N̄^(θ/2), com θ ≈ 1,35 (lei de Taylor estimada na base) e c estimado por tipo de intervalo (5 ou 7 meses), em 7 registros; “não calculável” se N̄ < 6. Sem calibração. |
| Perda abrupta (6): magnitude | Alta: queda ≥ máx(2; ⌈0,2·N⌉) médicos. Crítica: queda ≥ máx(3; ⌈0,3·N⌉) médicos. |
| Perda abrupta (6): excepcionalidade | Faixas de porte: 1–3, 4–9, 10–19, 20–49, 50–99, 100–299 e 300 ou mais. Excepcional se P(X ≤ x) ≤ α na distribuição das variações relativas da célula (porte × intervalo de 5 ou 7 meses), **contando empates** e só com transições anteriores à data avaliada. Mínimo de 100 transições anteriores para α = 1% e de 1.000 para α = 0,1%; abaixo disso, “não calibrado”. Não calibrar por período: a taxa de alertas por registro serve só como monitoramento (na base, de 0,53% a 1,76% para a meta de 1%). |
| Afastamento de patamar (7) | Patamar = maior média dos 4 registros de dois anos civis completos, em blocos que terminam antes dos 4 últimos registros, em toda a série até a data. Atenção: os 2 últimos registros ≤ 85% do patamar. Alta: atenção e cauda de 1% do afastamento na faixa de porte. Crítica: os 4 últimos registros ≤ 70% do patamar e cauda de 0,1%; enquanto não houver casos para estimar essa cauda (hoje, cerca de 2 por data entre 2.314 classificáveis), “não calibrável”, sem agrupar faixas. Patamar abaixo de 20 médicos: descritivo. |
| Pico que volta | Pico = os registros do salto até a volta. Até a volta se confirmar, o salto leva “verificar registro”. Na calibração com origens móveis, só contam como pico as voltas já observadas na data avaliada. |
| Quebra de fonte | Como na seção 2.4 (na base, só o DF até jun/2017). |
| Indicadores 8 e 9 | Só em trechos com população comparável: 2014–2017 e 2018–2021 (a população se repete em 2021–2023 e muda de base em 2024). Janela que cruze 2023→2024: “comparação não habilitada”. Descritivos abaixo de 20 médicos. No indicador 9, percentil = (posto médio − 0,5) ÷ n, com universo fixo na janela, de junho a junho em 2 anos. |
| Indicador 10 | Referência na mesma unidade do território (município contra UF: soma municipal da UF), sem o próprio município. |
| Modelo nulo | Séries sintéticas N(t+1) = N(t)·(1 + g) + ε, com Var(ε) = φ·N^θ, arredondadas para inteiros não negativos, e quedas injetadas de 20%, 30% e 50%. Falso alerta e perda não detectada se medem nelas; em dado real, a taxa de alertas fica perto da meta por construção. |
| Níveis territoriais | A calibração é municipal. Para estados como unidade e para conjuntos, o Detector mostra os fatos observados e os indicadores descritivos, sem intensidade calibrada, até haver calibração própria para esses níveis. |

---

## 5. Como classificar sem confundir observação, raridade e sinal analítico

### 5.1. Registro analítico por fenômeno

Cada ocorrência deve armazenar e apresentar, quando aplicável:

1. **Indicador** e unidade;
2. **Valor atual** e base de comparação;
3. **Mudança absoluta/percentual** e **datas extremas**;
4. **Janela** e transformação dos dados (registro original, anual homólogo, média anual etc.);
5. **Qualidade do registro**: normal, **“verificar registro”** ou **descontinuidade de registro** (seção 2.4);
6. **Sinal observacional**: melhora, estabilidade, desaceleração, redução, perda abrupta descritiva etc.;
7. **Excepcionalidade estatística**: comum/incomum/muito incomum/**não calibrada**, com método, universo e versão;
8. **Intensidade analítica** (quando houver regra validada): atenção, alta, crítica; ou **sem classe** por decisão metodológica;
9. **Interpretação permitida, limites e fonte**.

### 5.2. Intensidade por dimensão

| Dimensão | Conteúdo | Resultado recomendado |
|---|---|---|
| Estrutural | 1 + 2 | Classe convencional, com quantitativo e duração do zero |
| Trajetória observada | 3, 6, 7 | Sinais e alertas de mudança, com magnitude e excepcionalidade separadas; indicador 7 descritivo abaixo de 20 médicos no patamar |
| Ritmo e estabilidade | 4, 5 | Sinais descritivos; desaceleração pela classe da Análise de Tendência, com atenção só por persistência; instabilidade sem alta/crítica na v2 |
| Comparação relativa | 8, 9, 10 | Classe apenas onde dados e critérios forem validados |
| Contexto geográfico | 11 | Descrição sem classe |
| Coexistência | 12 | Perfil combinado, sem escore global |

**Regra semântica:** “crítica” designa a intensidade de determinado **indicador analítico** e **não** urgência assistencial, necessidade de médicos, adequação de oferta ou condição de acesso. Testar se “intensidade do sinal” é nome público mais claro; a decisão terminológica permanece aberta.

### 5.3. Regras de persistência e histerese

- Registrar deterioração observada imediatamente.
- Uma melhora de classificação estrutural pode requerer confirmação por duas observações válidas consecutivas, sem esconder o novo quantitativo.
- Para alertas temporais, exigir duração/recorrência conforme o indicador e comparar séries anuais ou homólogas quando adequado.
- **Persistência do evento** é diferente de **excepcionalidade da mudança**. Ambas podem ser mostradas sem serem somadas de forma opaca.

---

## 6. Calibração com a base real — necessária antes da versão definitiva dos limiares

### Fase diagnóstica (somente leitura)

1. **Conferir metadados da base:** origem; unidade de contagem; competência das observações; representatividade territorial; identificação de zero versus ausente; alterações de método; datas por território; consistência das somas; **descontinuidades de registro** (picos que voltam e quebras de fonte, seção 2.4).
2. **Mapear a distribuição de porte:** quantis de médicos por município e distribuição de registros zero, 1, 2, 3, 4–9, 10–49, 50+; revisar faixas conforme os dados.
3. **Verificar o calendário:** comportamento jan↔jun; diferenças nas transições de 5 e 7 meses; possíveis choques coletivos (não lhes atribuir causa sem evidência externa).
4. **Examinar população e coordenadas:** cobertura temporal, revisão metodológica, fonte, quebras, unidades e coordenadas disponíveis; não pressupor comparabilidade.
5. **Calcular todas as métricas descritivas** em toda a série e estudar seus histogramas, quantis, distribuição por porte, região e período.

### Método candidato para sinais de mudança extraordinária

- Definir previamente uma **magnitude substantiva mínima**, escolhida como convenção analítica documentada (ex.: 20% + dois médicos para evento alto).
- Estimar, com procedimentos robustos, a **variação habitual** por porte e tipo de intervalo, separando efeitos estruturais de sazonalidade e choques; modelos como Poisson, quase-Poisson ou alternativas são **hipóteses**, não verdades sobre a base.
- Avaliar níveis de excepcionalidade por quantis empíricos ou estatística padronizada calibrada; não presumir automaticamente uma cauda normal.
- Excluir da calibração as transições em **descontinuidade de registro**; manter as quedas grandes que persistem, que podem ser mudanças reais.
- Calibrar também a distribuição do **afastamento de patamar** por faixa de porte (indicador 7) e verificar se o teste discrimina abaixo de 20 médicos; onde não discriminar, o indicador permanece descritivo.
- Comparar diferentes metas de alertas sem mudança esperada (inclusive 1%/0,1% e alternativas menos estritas). **Raridade não equivale a gravidade assistencial.**
- Aplicar **validação retrospectiva com origens móveis**, sem calibrar com dados futuros relativamente à data avaliada; verificar taxa de alertas por indicador, porte, período e região.
- Avaliar **sensibilidade** a quedas conhecidas injetadas em séries sintéticas e a trajetórias plausíveis de declínio gradual; medir falsos alertas no modelo nulo e **perdas não detectadas** pela regra.
- Estudar efeito de histerese e de avaliação repetida ao longo de muitos municípios/janelas: metas por avaliação não equivalem a taxa total de territórios sinalizados alguma vez.
- Documentar limiares como **definição matemática**, **convenção substantiva** ou **estimativa calibrada**, com versão e fonte.

### Critérios de decisão

Uma regra **não** será confirmada por parecer ou simulação sintética isolados; deverá satisfazer transparência, estabilidade temporal, consistência em pequenos e grandes quantitativos e utilidade interpretativa. Mudanças reais que não atingirem alerta extraordinário continuarão **visíveis como fatos observados**.

---

## 7. Simulador: seleção de territórios, períodos e referências

### 7.1. Continuidade territorial

Ao abrir o Simulador:

1. **Importar cópia** da seleção territorial principal já constituída na plataforma, inclusive conjuntos e seus componentes.
2. Permitir **desmarcar**, **adicionar** e **substituir** territórios apenas na área local do Simulador.
3. Disponibilizar ação explícita, separada, caso o usuário queira **aplicar a seleção local à seleção principal**; sem essa ação, a principal permanece intacta.
4. Preservar nomes dos conjuntos, códigos e lista de **todos os municípios integrantes**; avisar sobre sobreposições quando uma unidade comparada for membro de um conjunto.
5. Em agregações, documentar se o valor representa **soma de registros territoriais**, **agregado oficial da fonte** ou outra medida; não supor equivalência entre somatórios e pessoas únicas.

### 7.2. Janela histórica

- Selecionar livremente **observação inicial e final** entre as datas realmente presentes no recorte territorial; permitir comparação de janelas diferentes como cenários distintos.
- Informar **quantidade de registros válidos**, **tempo real transcorrido**, lacunas e transformações usadas.
- Presets úteis: série completa; últimos `n` registros; últimos `n` anos-calendário; períodos homólogos por mês; intervalo personalizado. Presets não substituem datas livres.
- A **elegibilidade** dos métodos varia conforme quantidade de pontos e zeros; o sistema deve informar a razão de eventual indisponibilidade.
- **Janela padrão do método padrão (v2.1):** 3 anos até a origem (7 registros), a mesma usada na retroprojeção que indicou M0d. Em séries com **descontinuidade de registro**, a janela padrão começa depois da quebra de fonte e não usa o registro do pico nos ajustes; o usuário pode escolher outra janela, com aviso.

### 7.3. Horizonte futuro

- Configurar horizonte por **data final futura**, não apenas por três opções fixas; permitir janeiro/junho futuros como marcos de exibição compatíveis com a base, respeitadas as durações de cinco e sete meses.
- Alertas informativos conforme a razão `H/W` entre horizonte futuro e janela histórica (não são garantias estatísticas): `H ≤ W/2` aviso normal; `W/2 < H ≤ W` cautela; `W < H ≤ 2W` extrapolação além da janela; `H > 2W` extrapolação extrema. Esses cortes são candidatos sujeitos à revisão.
- **Data de origem:** junho de 2024, se for o último registro disponível. A interface deve destacar a distância entre última observação e data corrente do sistema; simulações de 2025 ou 2026 são **projeções retrospectivamente não verificadas**, não observações atualizadas.

### 7.4. Referências comparativas configuradas no próprio Simulador

- **Opcionais:** o usuário pode simular sem referência.
- **Uma ou muitas**, inclusive fora da seleção principal.
- **Fixas:** mantêm quantitativo/taxa da data base escolhida.
- **Dinâmicas:** também seguem método histórico e hipóteses próprias; pode haver intervenções explicitamente configuradas na referência, se o usuário desejar.
- **Métricas:** quantitativo absoluto ou taxa populacional válida. Comparações de quantidades entre municípios de portes diferentes não devem ser apresentadas como comparação de suficiência.
- **Universo:** município, conjunto, agregado comparativo ou valor definido pelo usuário; não declarar independência quando há sobreposição.
- **Condições por cenário:** default de mesma janela/método para comparabilidade, com modo avançado de configurações distintas e aviso contextual.

---

## 8. Métodos candidatos de projeção e papel da média percentual

### 8.1. M0 — Persistência

`B(t) = N_0`, em que `N_0` é a última observação válida ou média do último ano completo, de acordo com a opção declarada. Representa hipótese de quantitativo constante, não estabilidade garantida.

**Papel:** cenário de referência obrigatório para comparar o desempenho retrospectivo dos demais métodos e alternativa sempre visível ao método padrão. Suporta zeros.

### 8.2. M0d — Persistência com deriva do estado (método padrão candidato, v2.1)

`B(t) = N_0 × (1 + g_UF)^t`  
`g_UF = (S_UF(t_0) / S_UF(t_0 − 3 anos))^(1/3) − 1`

em que `t` é o tempo em anos desde a origem e `S_UF` é a soma dos registros municipais da UF do território, no mesmo mês da origem. É a persistência corrigida pelo crescimento recente do estado, na mesma unidade da série municipal.

- **Papel:** método padrão candidato para municípios, em todos os portes. M0 continua como referência obrigatória e alternativa visível; M1–M3 ficam como alternativas.
- **Evidência:** nas retroprojeções com a base real (origens em junho de 2017 a 2023, janela de 3 anos), M0d errou de 13% a 44% menos que M0 em 4 anos e menos que M1–M3 em todos os portes e horizontes; em 1 ano, abaixo de 20 médicos, empatou com M0. Também reduziu a subestimação: em 4 anos, o viés médio na faixa de 100 a 299 médicos caiu de −61 (M0) para −23 médicos.
- **Limites:** todas as origens testadas são de crescimento forte; se o crescimento desacelerar, M0d pode superestimar. A soma municipal inclui a superconta crescente entre municípios (de 1,44 para 1,63 vez o total nacional); a variante com médicos únicos da UF teve resultado parecido e serve de conferência.
- **Casos-limite:** território em zero permanece em zero (acréscimos são aditivos, seção 9.3); se a série da UF tiver quebra de fonte na janela, a deriva usa a janela posterior à quebra ou recai em M0, com aviso.
- **Outros níveis:** para conjuntos, a trajetória-base é a soma das projeções municipais, rotulada como soma; para estados e Brasil, que contam pessoas únicas, o padrão depende de retroprojeção própria nesses níveis.
- **Confirmação:** na calibração definitiva, testar janelas de 2 e 4 anos, o desempenho origem a origem e, quando houver, origens com crescimento fraco ou queda.

### 8.3. M1 — Crescimento composto equivalente

Se `N_i > 0` e `N_f > 0`, com duração real `T` em anos:

`r_anual = (N_f / N_i)^(1/T) − 1`  
`B(t) = N_0 × (1 + r_anual)^t`

- Exibir crescimento acumulado `N_f/N_i − 1` e taxa anual equivalente **separadamente**.
- Não aplicar o crescimento acumulado total a cada etapa futura.
- Opcional: reduzir sensibilidade a extremos comparando **médias anuais** do início e do fim da janela, quando o usuário selecionar esse tratamento.
- Se `N_i = 0`, taxa composta a partir dos extremos fica **indefinida**; não inventar pseudocontagem.

### 8.4. M2 — Tendência linear robusta

Usar todas as observações válidas e suas datas reais; método candidato **Theil–Sen** (mediana das inclinações entre pares de pontos). Produz hipótese de variação absoluta em médicos/ano, com truncamento de projeções abaixo de zero e sinalização da truncagem.

- Interessante para séries com zeros e quantitativos pequenos.
- Não resolve automaticamente degraus estruturais ou quebras; permitir selecionar janela posterior a mudança de patamar. Em **descontinuidade de registro**, a janela padrão já começa depois da quebra de fonte (seção 7.2).

### 8.5. M3 — Tendência log-linear

Regressão de contagem candidata com ligação log, como Poisson/quase-Poisson, sobre as datas reais. Taxa proporcional implícita: `r_anual = exp(β) − 1`, quando o modelo for aplicável.

- Avaliar sobredispersão e dependência temporal dos registros, além de possíveis diferenças sistemáticas entre janeiro e junho.
- **Não** utilizar intervalos de confiança ingênuos do ajuste como substitutos de validação preditiva.
- Nenhum modelo é garantidamente superior para determinado porte antes de backtests na base real.

### 8.6. Média aritmética das taxas — só como estatística descritiva

A discussão original pediu simulações baseadas no **percentual médio** dos últimos intervalos semestrais ou anuais. O percentual médio que reproduz o crescimento ocorrido é a **taxa composta (M1)**: a **média geométrica ponderada pelo tempo** das variações válidas da janela, que equivale à taxa composta calculada entre os mesmos extremos. O pedido é atendido por M1, e a média geométrica não aparece como método separado.

A **média aritmética das taxas** fica restrita a um uso:

- **Métrica descritiva:** mostrar média aritmética, mediana e dispersão das taxas anualizadas ou das taxas entre observações homólogas, com o intervalo escolhido, sempre ao lado da taxa composta e com nota curta sobre por que as duas diferem.

Ela **não é oferecida para projetar**: nem como método, nem como cenário exploratório, nem como valor sugerido de taxa hipotética (ajuste (e) da v2.1). A média aritmética das taxas nunca é menor que a taxa composta e a supera sempre que as taxas variam (desigualdade entre as médias aritmética e geométrica, caso particular da desigualdade de Jensen); usada para projetar, infla a trajetória. Exemplo: 3 → 5 → 3 médicos dá taxas de +66,7% e −40%; a média aritmética é +13,3% ao ano, embora a variação real seja zero, e em quatro anos levaria a quase 5 médicos. Na base, ela errou mais que a taxa composta em todos os portes e horizontes (seção 1.2).

Quem quiser testar outro ritmo de crescimento continua podendo informar uma **taxa manual**, como intervenção rotulada como hipótese do usuário (seção 9.2).

### 8.7. Comparação de métodos

- Permitir diferentes métodos e **diferentes janelas** do mesmo método para um território, visualizados em painéis legíveis.
- Classificar o contraste entre curvas como **sensibilidade ao método/janela**, não como “intervalo de confiança”.
- O método destacado como padrão deve ter desempenho retrospectivo demonstrável por porte e horizonte, em comparação com M0; disponibilizar os demais de forma explícita. Na v2.1, o padrão candidato é **M0d** (seção 8.2), até a confirmação na calibração definitiva.
- Não extrapolar indefinidamente aceleração por polinômios sem limitação ou validação.

### 8.8. Definições operacionais do Simulador (v2.2)

Vêm da mesma revisão estatística. Prevalecem sobre o texto das seções 7.3, 8.1 a 8.7, 9, 10.3, 11.2 e 13 quando houver divergência.

| Item | Definição operacional |
|---|---|
| M0d em municípios | `B(t) = N0 × (1 + g_UF)^t`, com N0 = última observação válida, t em anos reais desde a origem e g_UF = crescimento anual composto da soma municipal da UF nos 3 anos anteriores à origem (janelas de 2 a 4 anos dão praticamente o mesmo erro). Volta ao M0, com aviso, se houver quebra de fonte na janela da deriva (na base, só o DF com início antes de jan/2018). Origem = fim da janela escolhida; o trecho entre a origem e o último registro é retroprojeção rotulada. Zero continua zero sem intervenção. |
| Conjuntos | Soma das projeções dos membros, cada um com a deriva da sua UF (vale para conjuntos com membros de UFs diferentes), com o rótulo “soma das projeções”. Conjuntos reúnem territórios do mesmo nível. |
| Estados e Brasil | Padrão provisório: **M1 de 3 anos na série do próprio nível** (no estado, equivale ao M0d com a série estadual). Na base, errou 2,2%, 3,5% e 7,3% nos estados em 1, 2 e 4 anos, contra 5,8%, 10,8% e 20,7% do M0, mas só num período de crescimento forte; segue com aviso até nova validação. |
| M1 | Como na seção 8.3; alternativa. Abaixo de 100 médicos, erra mais que o M0 (de 1,09 a 1,44 vez). |
| M2 (Theil–Sen) | Inclinação b = mediana das inclinações entre pares de registros; intercepto = mediana(y) − b·mediana(t); projeção pela reta, com a diferença para N0 exibida. |
| M3 | Poisson com ligação log (IRLS); quase-Poisson só como diagnóstico de dispersão, porque dá a mesma projeção. Série toda em zero: “não calculável”. |
| Média aritmética das taxas | Só descritiva, com taxas homólogas de junho a junho. |
| Avisos H/W | W = janela do método; no M0, 3 anos. |
| Faixas de 80% | Só de 1 a 4 anos; além de 4 anos, “indisponível”, sem extrapolar. A coluna de 3 anos é calculada na calibração. Data intermediária usa a faixa do ano inteiro seguinte. A faixa é da base B(t) e se desloca com a intervenção I(t), com rótulo. N0 = 0, estados e Brasil: “indisponível”. Conjuntos: faixa do porte da soma, rotulada “aproximação”. Métodos M1 a M3: “indisponível” até terem faixas próprias. |
| Intervenções | `S(u) = 0` para u < 0; padrão `S = 1` (permanência total), rotulado como hipótese. |
| Meta inversa | Menor inteiro x com N(T) ≥ meta, com B(T) calculado sem arredondar; a meta vale na data final T. Com S = 1 e k eventos iguais, x = ⌈(meta − B(T)) ÷ k⌉; nos demais casos, busca entre inteiros. |
| Simular recuperação | Abre o Simulador com o território, a janela e, como meta, o patamar do indicador 7 (seção 4.2), pelo planejamento inverso; a pessoa pode trocar a meta. |

---

## 9. Intervenções e cenários combinados

### 9.1. Separação entre tendência e intervenção

A formulação preferencial é:

`N(t) = max(0, B(t) + I(t))`  
`I(t) = Σ_j a_j × S(t − t_j)`

- `B(t)`: trajetória de base pelo método escolhido.
- `a_j`: acréscimo positivo ou retirada negativa, configurado para uma data `t_j`.
- `S(u)`: hipótese de retenção/permanência do efeito da intervenção após `u` anos.

**Padrão inicial explícito:** permanência total dos acréscimos, rotulada como **hipótese**, não estimativa empírica. Alternativas de retenção só podem ser representadas se o usuário escolher a hipótese ou houver base confiável para estimá-la.

### 9.2. Operações disponíveis

- Sem intervenção (apenas `B(t)`).
- Acréscimo pontual de `X` médicos.
- Acréscimo periódico de `X` médicos por ano ou em calendário escolhido, com explicitação das datas exatas.
- Retirada pontual ou periódica, sem deixar estoques negativos silenciosamente.
- Substituição/ajuste da taxa manual de crescimento, que altera **B(t)** ou um componente explicitamente identificado da trajetória. A taxa é informada pelo usuário e rotulada como hipótese; o sistema não sugere a média aritmética das taxas (seção 8.6).
- Combinação de várias intervenções em um mesmo território, com ordem e datas rastreáveis.
- Configurações independentes por território e cenário.
- Planejamento inverso: calcular incremento necessário para meta definida em prazo e referência determinados.

### 9.3. Casos-limite

- **Zero:** métodos multiplicativos puros não recuperam um território que permanece em zero; permitir acréscimo aditivo e sinalizar a restrição do método.
- **Retirada acima do estoque:** alertar e solicitar revisão; o `max(0,·)` matemático não deve ocultar uma intervenção incompatível com os valores disponíveis.
- **Valores fracionários:** manter precisão interna para cálculo e arredondar **apenas na apresentação**, com regra documentada; para decisões sobre faixas `N=1,2,3`, mostrar incerteza/intervalos quando a projeção cruza o corte, evitando classificar um valor contínuo como indivíduo real.
- **Calendário:** acréscimos anuais devem ocorrer em datas anuais, não a cada registro de janeiro/junho como se os intervalos fossem iguais.
- **Intervenção versus tendência:** o crescimento histórico não deve ser aplicado automaticamente aos médicos adicionados; apenas se o usuário selecionar expressamente hipótese que justifique isso.

---

## 10. Referências, convergência/divergência e planejamento inverso

### 10.1. Métrica de comparação

Escolher explicitamente:

- Diferença absoluta `B(t) − A(t)` em médicos ou taxa;
- Razão `A(t)/B(t)` (quando referência positiva);
- Índice `100 × A(t)/B(t)`.

**Convergência pela razão e pela diferença podem produzir leituras diferentes.** Não usar “convergem” sem mostrar qual métrica fundamenta a afirmação.

### 10.2. Quando a referência também evolui

Uma referência dinâmica possui método, janela e hipóteses próprios. Um município pode crescer em quantidade absoluta e, simultaneamente, perder posição relativa se a referência crescer mais rapidamente.

O prazo estimado de alcance deve ser apresentado com horizonte e incerteza. Quando não houver cruzamento, indicar **“não alcança no horizonte simulado”** ou **“pode não alcançar sob as hipóteses atuais”**, sem fabricar data.

### 10.3. Meta inversa

Permitir definir: meta absoluta ou taxa-alvo, data de alcance, comparação fixa/dinâmica, método histórico e calendário de acréscimos. O cálculo oferece **uma necessidade matemática condicional**, não plano de provimento validado ou recomendação assistencial.

Os resultados devem ser transformados em alternativas com **médicos inteiros por evento**, destacando a diferença entre incremento médio teórico e programação executável de acréscimos discretos.

### 10.4. População nas referências

Para taxas, toda simulação futura deve definir a hipótese populacional: constante, série/projeção externa validada, ou taxa de variação explicitamente fornecida. Se o denominador futuro não estiver disponível, a **comparação por taxa futura** fica condicionada a uma hipótese clara; não pressupor que é observada.

---

## 11. Incerteza, validação retrospectiva e comunicação pública

### 11.1. Retroprojeções

- Executar **origens móveis**: ajustar modelos apenas com dados até uma data e confrontar previsões com observações posteriores.
- Avaliar por **faixas de porte**, horizontes e disponibilidade de registros; documentar quantidade de origens e de municípios efetivamente utilizados.
- Métricas candidatas: erro absoluto em médicos, viés, erro escalado frente a M0 quando definido e cobertura de faixas.
- Preservar a distinção entre erro de projeção, variabilidade do observado e incerteza sobre intervenções que **não** aconteceram.

### 11.2. Faixas de incerteza

- Priorizar faixas empíricas calibradas por erro de retroprojeção e por horizonte/porte; uma faixa P10–P90 pode ser meta **somente se a base suportar calibração adequada**.
- **Faixas do método padrão (v2.1):** P10–P90 da razão observado ÷ projetado − 1 de M0d, por faixa de porte e horizonte, sempre com o número de origens. Na base atual, as faixas de 1 e 2 anos cobriram de 74% a 80% dos casos fora da amostra, para meta de 80%: um pouco estreitas, mas validadas. As de 3 e 4 anos ficam **calibradas, sem validação**, e devem ser rotuladas assim; além de 4 anos, **“faixa indisponível”**. Valores iniciais, a recalcular na calibração definitiva:

| Médicos na origem | 1 ano (7 origens) | 2 anos (6 origens) | 4 anos (4 origens, sem validação) |
|---|---|---|---|
| 0–9 | −26% a +48% | −31% a +72% | −31% a +104% |
| 10–19 | −23% a +29% | −28% a +40% | −30% a +62% |
| 20–49 | −19% a +24% | −23% a +34% | −25% a +55% |
| 50–99 | −15% a +20% | −20% a +30% | −19% a +55% |
| 100–299 | −12% a +17% | −16% a +26% | −17% a +42% |
| 300 ou mais | −7% a +10% | −11% a +18% | −12% a +34% |

- Informar metodologia, número de origens, amplitude do horizonte validável e limitações de dependência temporal/choques.
- Além do horizonte testado (hoje, 4 anos), a faixa é **“indisponível”**: não há faixa extrapolada nem números arbitrários (v2.2; seção 8.8).
- A diferença entre métodos não deve ser chamada automaticamente de incerteza probabilística.

### 11.3. Separação visual obrigatória

- **Observado:** marcadores nas datas reais, linha contínua, fonte e última data.
- **Projeção-base:** linha distinta/tracejada, método e janela exibidos.
- **Intervenção:** eventos anotados no eixo temporal e efeito agregado rastreável.
- **Faixa:** banda só quando calculável; legenda específica.
- **Intensidade condicional:** painel separado, rotulado como *hipótese derivada da simulação*, nunca confundido com dado observado.

---

## 12. Interface e experiência do usuário

### 12.1. Fluxo do Simulador em quatro etapas

1. **Territórios em análise:** seleção herdada e editável localmente; composição integral dos conjuntos; referências externas adicionáveis sem alterar a seleção principal.
2. **Base histórica e método:** registros reais, janela livre, método padrão **M0d** pré-selecionado, M0–M3 como alternativas e estatísticas históricas, entre elas a média aritmética das taxas ao lado da taxa composta, só como descrição (seção 8.6).
3. **Intervenções e horizonte:** acréscimos, retiradas, taxas manuais e combinações por território; horizonte por data final.
4. **Comparações e resultados:** referências fixas/dinâmicas, curvas, faixas quando disponíveis, tabela de parâmetros, prazo de alcance e exportação.

**Modo simples:** uma janela/método por conjunto de cenários, poucas linhas por painel.  
**Modo avançado:** múltiplos métodos/janelas, referências e intervenções distintas; preservar legibilidade e avisos.

### 12.2. Detector

- Visão principal: **situação mais recente** da janela; visão temporal separada para histórico da intensidade/sinais.
- Tabela: território | situação estrutural | trajetória | ritmo/instabilidade | posição relativa (se válida) | contexto geográfico | sinais combinados | última observação.
- Detalhes expansíveis: `o que foi observado`, `qual critério`, `quanto difere do habitual`, `o que significa`, `o que não significa`, `limitações do dado` e `qualidade do registro` (“verificar registro” ou descontinuidade de registro).
- Filtros por fenômeno, porte e período; permitir parâmetros editáveis **sem sobrescrever os padrões**; identificar “configuração personalizada — exploratória”.
- Botão **“Abrir no Simulador”**, preservando contexto e série.

### 12.3. Textos determinísticos e LLM

Os fatos e os critérios que justificam resultados são gerados por **cálculos e textos determinísticos**, não por paráfrase improvisada do modelo conversacional. O LLM pode orientar navegação e selecionar funções permitidas, sem mudar regras metodológicas nem inventar interpretações assistenciais.

**Exemplo de texto público aceitável:**

> Entre jan/2019 e jun/2019, o quantitativo registrado passou de 12 para 7 médicos (−5; −41,7%). A redução observada é apresentada independentemente de sua excepcionalidade estatística. A avaliação de excepcionalidade depende da regra calibrada para o porte e esse intervalo. O dado não informa, isoladamente, alterações na qualidade ou no acesso à assistência.

### 12.4. Estado, exportação e privacidade

- Exportar/importar configurações dos cenários em formato legível (por exemplo, JSON), e resultados em CSV/relatório; registrar fonte, data, versão dos limiares, fórmulas, seleção e hipóteses.
- Considerar que sessões podem estar em memória e ser perdidas na infraestrutura; não pressupor banco persistente.
- Dados agregados não autorizam inferir identidade, trajetórias individuais ou vínculos não informados.

---

## 13. Compatibilidade de territórios, conjuntos e agregações

1. Preservar os códigos e nomes originais de territórios e o nome dado pelo usuário a cada conjunto.
2. Apresentar lista completa dos municípios componentes em detalhes/tooltip dos conjuntos, inclusive nas visualizações de distribuição, espacial e simulação.
3. **Agregados oficiais da fonte** e **somas municipais** podem divergir: manter ambos identificados, jamais igualá-los automaticamente.
4. Para taxas de conjuntos: quando a composição é válida, `soma das contagens territoriais ÷ soma das populações`, **não** média simples das taxas municipais; rotular claramente o que foi somado.
5. Conjuntos com sobreposição exigem avisos e regras explícitas de não independência; rankings percentílicos de municípios não devem incorporar conjuntos misturados ao universo.
6. A versão do conjunto deve acompanhar o cenário; alterar a composição não deve retroativamente mudar resultados anteriores sem registro.
7. Comparações município ↔ conjunto contendo esse município ou conjunto ↔ conjunto sobreposto devem expor os membros comuns.
8. **Estado como unidade (v2.2):** na seleção principal, o estado pode entrar como uma unidade (uma bolha, com a fonte estadual). Ele não se soma a municípios, e as medidas de posição (quantis, percentis, ordenações) não misturam estados e municípios: cada nível forma um grupo próprio, com legenda. Conjuntos reúnem territórios do mesmo nível; um conjunto de estados soma as fontes estaduais e diz isso no rótulo.

---

## 14. Testes e critérios de qualidade

### 14.1. Testes determinísticos de funções e dados

- Casos exatos no limiar, acima e abaixo; evitar comparações de ponto flutuante frágeis quando aritmética inteira for aplicável.
- Zeros antes, durante e ao fim da série; dados ausentes; apenas uma observação; janelas curtas e registros irregulares.
- Intervalos de 5 e 7 meses, diferenças entre “últimos n registros” e anos-calendário, presets sem datas fictícias.
- Crescimento positivo, declínio, desaceleração, aceleração, oscilação, perda abrupta e recuperação parcial; a desaceleração do indicador 4 coincide, território a território, com a classe da Análise de Tendência na mesma série e janela.
- Descontinuidade de registro: pico que volta (caso Rio Rufino), quebra de fonte (caso DF antes de 2018) e queda grande que persiste, que continua alertável com “verificar registro”.
- M0d: deriva calculada com a soma municipal da UF na mesma janela; território em zero permanece em zero; quebra de fonte na janela da UF.
- Percentual observado versus taxa equivalente; propriedade de que taxa geométrica ponderada corresponde à taxa composta para os mesmos extremos positivos.
- Projeções nunca produzem contagens negativas apresentadas como válidas; tratamentos de `N=0` e retiradas excessivas são explícitos.
- Planejamento inverso atinge a meta matematicamente quando reaplicado ao simulador, dentro das hipóteses e regras discretas definidas.

### 14.2. Validação empírica e segurança interpretativa

- Fotografias de alertas por porte × indicador × período, auditáveis entre versões.
- Simulações nulas com diferentes dispersões; testes de sensibilidade a mudanças injetadas; não confundir queda observada com alteração estrutural latente.
- Backtest por janela, porte, método e horizonte; M0 como referência e M0d como padrão candidato; avaliar também séries com quebras, sazonalidade e, quando houver, períodos de crescimento fraco.
- Avaliar regras de persistência/histerese e consequências de testes repetidos.
- Verificar sobreposição de territórios e referências, somatórios e fonte populacional.
- Bloquear expressões proibidas de inferência como “desassistido” ou “isolado” em saídas determinísticas e na camada conversacional, quando não suportadas.

### 14.3. Testes de UX e regressão

- Herança da seleção principal sem alterações inadvertidas; restauração e ações locais.
- Responsividade desktop/celular; legibilidade dos gráficos com várias curvas; distinção dos elementos observados/projetados.
- Acesso aos indicadores e parâmetros sem depender de chamadas ao LLM; falha da camada conversacional não impede cálculo determinístico.
- Preservar compatibilidade das análises já existentes e integridade do CI/CD, frontend GitHub Pages e backend Cloud Run **quando uma implementação futura for autorizada**.

---

## 15. Fases propostas

A execução foi autorizada pelo comando integrado V22 (9/11/2026), que organiza o trabalho em etapas próprias.

| Fase | Entrega conceitual/técnica futura | Critério de avanço |
|---|---|---|
| **0 — Perfil empírico da base (somente leitura)** | Unidade de contagem, zeros/ausentes, distribuição de porte, calendário, sazonalidade, choques, população, coordenadas, agregações | Relatório com limites e decisões metodológicas documentadas |
| **1 — Contratos compartilhados** | Seleção local, data, território/conjunto, agregação, cenário, referência, versão de regra, exportação | Testes de consistência e regressão sem mudanças funcionais indesejadas |
| **2 — Detector núcleo** | Escala estrutural 1+2; declínio, perda abrupta e afastamento de patamar (atenção por magnitude; alerta com excepcionalidade); estado de descontinuidade de registro; sinais observados e excepcionalidade separados; perfil por dimensão | Calibração de regras candidatas e testes de interpretação |
| **3 — Simulador núcleo** | M0d como padrão candidato e M0–M3, janelas livres, intervenções aditivas, persistência, faixas empíricas por porte e horizonte, referências básicas por quantitativo | Backtests, fórmulas, casos-limite e interface aprovados |
| **4 — Relativos e comparativos** | Densidade, posição percentílica, defasagem, convergência, planejamento inverso, referências dinâmicas | Denominador validado para cada operação; universos comparáveis definidos |
| **5 — Complementos integrados** | Atenção por desaceleração (persistência da classe da Análise de Tendência) calibrada, instabilidade contextual, distância, sinais combinados, intensidade condicional seletiva | Testes de sensibilidade, falsos alertas e compreensão do usuário |

**Nota:** as fases não implicam que as funções existentes de densidade, comparação ou geografia devam ser removidas; referem-se à **integração revisada** dessas funções com os novos módulos e às condições metodológicas para classificações adicionais.

---

## 16. Decisões ainda pendentes e ordem recomendada

### Decisões tomadas na versão 2.2

- **Nome:** Detector de Sinais Territoriais; terceira camada = sinal analítico; classes = intensidade do sinal (atenção, alta, crítica).
- **Projeção:** Simulador como exceção aprovada à SPEC (seção 2.5); o assistente de conversa continua recusando previsões livres.
- **Definições operacionais:** seções 4.2 (Detector) e 8.8 (Simulador).
- **Padrões provisórios:** estados e Brasil com M1 de 3 anos; conjuntos pela soma das projeções dos membros.
- **Estado como unidade:** escolhido na árvore de seleção; não se mistura com municípios nas medidas de posição (seção 13).

### Decisões tomadas na versão 2.1

- **Indicador 7:** afastamento ≥15% é atenção; alerta exige excepcionalidade; descritivo abaixo de 20 médicos no patamar, salvo calibração em contrário.
- **Descontinuidade de registro:** estado restrito a picos que voltam e quebras de fonte; quedas que persistem seguem alertáveis, com “verificar registro”.
- **Desaceleração:** definição única, a da classe “Desaceleração do crescimento” da Análise de Tendência.
- **Método padrão do Simulador:** M0d como candidato, com faixas empíricas por porte e horizonte.
- **Média aritmética das taxas:** só estatística descritiva; o percentual médio para projetar é a taxa composta (M1).

### Bloqueios metodológicos para implementação classificatória

1. Qual é a **unidade exata de contagem** no CSV (médicos distintos por município, vínculos ou outra unidade)?
2. Como a base distingue **zero real e valor ausente** em cada período e território?
3. Quais séries de **população** são disponíveis e comparáveis de 2014 a 2024? Há quebras metodológicas?
4. Quais coordenadas representam o território para cálculos de distância (sede, centroide ou outra referência)?
5. Que comportamento empírico de **dispersão, efeito jan/jun e choques coletivos** existe nos registros?

### Decisões de desenho metodológico após perfil da base

6. Qual será a **janela padrão** dos indicadores temporais, preservando sempre a seleção livre do usuário?
7. Quais **faixas de porte** produzem calibração estável?
8. Quais limiares de magnitude são convenções substantivas aceitáveis e quais dependem de validação externa?
9. Qual equilíbrio entre **sensibilidade e especificidade** se quer para alertas excepcionais? Testar metas alternativas em vez de fixar 1%/0,1% imediatamente.
10. **Decidido na v2.2:** a classificação é exibida como “intensidade do sinal” (atenção, alta, crítica), sem sugerir urgência assistencial.
11. Que condição de persistência (ou de magnitude, medida dentro da classe) transforma a classe “Desaceleração do crescimento” em **atenção**, com estabilidade em séries reais?
12. Quais operações relativas podem usar a população disponível e em que anos; quais ficam indisponíveis?
13. M0d se confirma como padrão fora do período de crescimento forte? Quando M0 deve prevalecer? (Janelas de 2 a 4 anos dão praticamente o mesmo erro; o padrão provisório de estados, Brasil e conjuntos foi decidido na v2.2, seção 8.8.)
14. Como comunicar faixas de incerteza insuficientemente calibradas (por ora, as de 3 e 4 anos) e o hiato entre junho de 2024 e a data da consulta?
15. Como tratar comparações com **conjuntos sobrepostos** e agregados com semânticas distintas?
16. Parâmetros introduzidos na v2.1, a confirmar no modelo nulo: o corte de 20 médicos do indicador 7; o critério do pico que volta (10 médicos, dobro, retorno a até 125% em até dois registros); e a janela de 3 anos da deriva do estado.

---

## 17. Critérios para apreciação crítica da versão 2.1

Para eventual nova rodada com Claude Opus ou outro revisor, solicitar **avaliação independente e adversarial**, sem execução de código, abordando:

1. A separação entre **evento observado**, **excepcionalidade** e **sinal analítico** está logicamente consistente e operacionalizável?
2. A revisão dos **12 fenômenos** preserva utilidade sem inflar alertas? Há fenômenos que continuam redundantes ou mal denominados?
3. Os limiares explícitos propostos permitem calibração transparente por porte, janela e tipo de intervalo, sem circularidade?
4. A unificação da **desaceleração** com a classe da Análise de Tendência, com atenção só por persistência, é metodologicamente defensável? Que critério mais robusto poderia substituí-la?
5. M0d como padrão candidato, M0–M3 como alternativas e a **taxa composta (M1)** como resposta ao pedido de percentual médio, com a média aritmética só descritiva, conciliam solicitação do usuário, matemática e transparência?
6. Como calibrar e reportar **incerteza** com apenas 22 observações potenciais e choques compartilhados entre municípios?
7. Os contratos de agregação, seleção e referência evitam conclusões equivocadas por sobreposição e diferenças de fonte?
8. Os textos e a apresentação pública evitam inferir desassistência, isolamento ou rotatividade individual?
9. Quais decisões podem ser tomadas agora por definição e quais **dependem de inspeção da base real**?
10. Quais melhorias proporcionam ganho inequívoco de confiabilidade sem inviabilizar a utilidade exploratória do Agente?
11. Os ajustes (a) a (d) da v2.1 (seção 1.2) resolvem o excesso de alertas e o risco de definições paralelas apontados pela avaliação com a base real?

A avaliação deve classificar cada recomendação como: **acolher**, **acolher com alteração**, **rejeitar com justificativa** ou **depende de dados reais**, explicando os impactos e a prioridade.

---

## 18. Registro de mudanças

### 18.1. Da versão 2.1 para a 2.2

| Aspecto | Versão 2.1 | Versão 2.2 |
|---|---|---|
| Nome e termos | Detector de Fragilidades; fragilidade analítica; criticidade | Detector de Sinais Territoriais; sinal analítico; intensidade do sinal (cabeçalho e seções 1, 2.4, 3.1, 4, 5, 11.3, 15, 16 e 17) |
| Projeção e SPEC | Proposta sem autorização de implementação | Simulador como exceção aprovada à exclusão de projeção da SPEC; assistente de conversa sem previsões livres (seção 2.5) |
| Definições operacionais | Regras descritas em texto, com pontos em aberto | Tabelas das seções 4.2 (Detector) e 8.8 (Simulador), que prevalecem em caso de divergência |
| Estados, Brasil e conjuntos no Simulador | Padrão a validar | M1 de 3 anos como padrão provisório para estados e Brasil; soma das projeções para conjuntos (seção 8.8) |
| Faixas além do testado | “Faixa extrapolada” ou “indisponível” | Só “indisponível” acima de 4 anos (seções 8.8 e 11.2) |
| Estado como unidade | — | Escolhido na árvore de seleção; sem mistura de níveis nas medidas de posição (seção 13) |
| Estado do documento | Apta a orientar a especificação | Aprovada para implementação pelo comando integrado V22 |

### 18.2. Da versão 2 para a 2.1

| Aspecto | Versão 2 | Versão 2.1 |
|---|---|---|
| Indicador 7 | Afastamento ≥15% como atenção ou alta, conforme a evidência | ≥15% é atenção; alerta alto ou crítico exige excepcionalidade para o porte; descritivo abaixo de 20 médicos no patamar (seções 4 e 4.1) |
| Descontinuidades | Sem estado próprio; janela posterior a degraus só citada no M2 | Estado “descontinuidade de registro” para picos que voltam e quebras de fonte; nota “verificar registro”; quedas que persistem seguem alertáveis (seções 2.4, 4.1, 5.1, 6, 7.2 e 14) |
| Indicador 4 | Regra própria de perda de ritmo, com confirmação na janela seguinte | Classe “Desaceleração do crescimento” da Análise de Tendência; atenção por persistência da classe (seções 4, 4.1, 5.2 e 16) |
| Método padrão | M0–M3 como candidatos, padrão a definir | M0d como padrão candidato; M0 como referência; M1–M3 como alternativas; faixas empíricas por porte e horizonte (seções 1, 7.2, 8.2, 11.2, 12.1 e 15) |
| Média aritmética das taxas | Estatística descritiva e cenário exploratório opcional como taxa hipotética | Só estatística descritiva, ao lado da taxa composta; o percentual médio para projetar é a taxa composta (M1) (seções 1, 1.2, 8.6, 9.2, 12.1, 16 e 17) |
| Estado e fontes | Proposta para avaliação, sem inspeção da base real | Apta a orientar a especificação; ajustes justificados com a base real (seções 1.2 e 19) |

### 18.3. Da versão 1 para a 2

| Aspecto | Versão 1 | Versão 2 |
|---|---|---|
| Objeto | Simulador + Detector, 12 indicadores e limiares iniciais | Mesmas duas ferramentas, com três camadas de interpretação separadas |
| Indicadores 1–2 | Classificações distintas | Escala estrutural única, com duração da ausência como atributo |
| Limiares | Predominância de percentuais fixos | Magnitude + excepcionalidade como regra candidata para alertas extraordinários, com calibração por porte |
| Indicadores 4–5 | Podiam gerar criticidade alta | Desaceleração com atenção condicionada; instabilidade inicialmente descritiva |
| Indicador 7 | Recuperação insuficiente em relação ao pico | Afastamento de patamar robusto, evitando máximo isolado |
| Indicador 12 | Possível classe combinada | Perfil dimensional e sinais combinados, sem escore geral |
| Método de projeção | Média de taxas, crescimento acumulado, tendência genérica | M0–M3; média aritmética preservada descritivamente e opcional como cenário exploratório |
| Intervenções | Acréscimos e perdas combinados à taxa | Trajetória-base + intervenções com permanência hipotética explícita |
| Incerteza | Pouco especificada | Retroprojeção, bandas condicionadas à calibração, aviso quando indisponíveis |
| Tempo | Datas de jan/jun e horizonte livre | Regras de 5/7 meses por tipo de análise e hiato entre 2024 e data atual |
| Comparações | Territórios/referências opcionais | Mesmo escopo, com contratos de agregação, sobreposição e população |
| Entrega | Documento conceitual para análise | Documento revisado para nova avaliação; **não autoriza implementação** |

---

## 19. Fontes utilizadas e limites de validação

1. **Discussões do responsável pelo projeto** sobre o Agente Diagnóstico Territorial da Força de Trabalho na Saúde e as duas funcionalidades, em novembro de 2026, incluindo correções sobre a base composta apenas por médicos, período de 2014–2024, seleção, referências, conjuntos, limiares e terminologia geográfica.
2. **“Proposta conceitual e metodológica para avaliação crítica — Simulador de Cenários Territoriais e Detector de Fragilidades Territoriais” (v1, 9/11/2026)**, arquivo Markdown fornecido na conversa anterior.
3. **“Avaliação crítica — Simulador de Cenários e Detector de Fragilidades Territoriais”**, Claude Opus, 9/11/2026, 22 páginas, documento DOCX fornecido pelo usuário; parecer baseado em texto e em séries sintéticas, **sem acesso à base real, ao código ou à interface**.
4. **Análise crítica do parecer realizada na conversa**, distinguindo contribuições aproveitáveis e restrições excessivas sobre a finalidade exploratória das ferramentas.
5. **“Avaliação crítica da Proposta V2 — Simulador de Cenários e Detector de Fragilidades”**, 9/11/2026, com consulta somente leitura ao repositório Teste-Agente (ramo `implantacao/cloud-run-pages`, commit `2dc48ab`): arquivos de dados municipal, estadual e nacional e documentação do Agente; análises feitas em scripts próprios sobre cópia local dos dados (anexo `analise_base_real_v2.zip`). É a fonte dos números citados nas seções 1.2, 2.4, 4.1, 8.2 e 11.2.
6. **“Métodos estatísticos do Detector e do Simulador — explicação e amparo científico”**, 9/11/2026: revisão do amparo científico de cada indicador e método, que motivou o ajuste (e). A verificação desse ajuste na base usou o script `media_aritmetica.py`, incluído no mesmo anexo (seções 1.2 e 8.6).
7. **“Avaliação do Comando Integrado V2.1 para o Claude Code”**, 9/11/2026, com revisão estatística dos parâmetros feita na base real (anexo `verificacao_estatistica_comando_v21.zip`); fonte das definições das seções 4.2 e 8.8.

**Não houve nesta elaboração:** execução dos scripts de simulação mencionados no parecer; validação das regras no código da aplicação; auditoria da unidade de contagem e do denominador populacional na origem; nem implementação de qualquer funcionalidade. A inspeção empírica do CSV real limitou-se às análises somente leitura das fontes 5, 6 e 7. Fórmulas, métodos e limiares aqui apresentados permanecem **propostas a validar**.

---

## 20. Conclusão

A versão 2 conserva a proposta original de um sistema integrado para **identificar, explicar e explorar** sinais e trajetórias da distribuição territorial de médicos. Ao mesmo tempo, incorpora salvaguardas contra superinterpretação de oscilações, uso inadequado de percentuais, projeções deterministas sem incerteza e classificações globais sem fundamento. A versão 2.1 acrescenta os quatro ajustes que a base real exigiu: menos alertas espúrios do indicador 7 nos municípios pequenos, tratamento próprio e restrito das descontinuidades de registro, uma só definição de desaceleração e um método padrão de projeção escolhido por desempenho retrospectivo. Também deixa a média aritmética das taxas só como descrição do passado, porque, usada para projetar, ela infla as trajetórias. A versão 2.2 adota o nome Detector de Sinais Territoriais, aprova o Simulador como exceção à SPEC e fixa as definições operacionais de que a implementação precisa.

O critério organizador é: **não ocultar o que foi observado; não confundir raridade estatística com gravidade assistencial; não apresentar hipóteses como fatos; preservar a escolha informada do usuário; e exigir calibração empírica antes de transformar convenções numéricas em alertas padrão.**

**Status:** proposta v2.2, aprovada para implementação pelo comando integrado V22, com as decisões pendentes da seção 16. Publicação, implantação e mudanças de infraestrutura ou de custos continuam fora desta autorização.
