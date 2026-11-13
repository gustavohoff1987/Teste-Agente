# Proposta V3 — Detector de Sinais e Simulador de Cenários

## A mesma estrutura nas duas ferramentas: simples para quem usa, válida para qualquer base

13/11/2026 · Atualiza a V2.2 (Anexo A do comando V22) nos pontos indicados.

> **Sobre este arquivo.** É o Anexo A do comando V23, salvo aqui por decisão do responsável (decisão 7 do comando). Onde ele
> divergir da [V2.2](DETECTOR_E_SIMULADOR_V2_2.md), vale este. Em caso de conflito sobre autorização, vale a seção 0 do comando.
> **Correção de 13/11/2026** (decisão do responsável na pausa 1): a fonte da população, no item 6 da seção 0 e na Parte D, que
> falavam em "2000–2024, publicada em jan/2025"; a Parte D ganhou a nota "O que foi feito na troca".

O que não for tratado aqui continua como na V2.2:
- a histerese;
- as marcas de descontinuidade (pico que volta e quebra de fonte);
- a separação entre observado e simulado;
- o texto fixo de cenário;
- a exceção da SPEC para o Simulador.

---

## 0. Decisões do responsável (13/11/2026)

1. **Os 12 sinais do Detector continuam**, com critérios e limites que a pessoa pode ajustar.
2. **Três níveis de alerta: moderado → elevado → crítico.** Além deles, existem "sem alerta" e "sem comparações suficientes".
3. **Telas simples e limpas nas duas ferramentas.** As explicações ficam num "Entenda", escondido até a pessoa pedir: com o mouse, com um toque (no celular) ou pelo teclado.
4. **As duas ferramentas funcionam com qualquer base**, como as análises.
5. **O Simulador segue a mesma estrutura do Detector:**
   - aprende com a própria base;
   - usa só o passado;
   - mostra só o que a base sustenta;
   - tem premissas ajustáveis, com "Entenda".
6. **Na base do Brasil, a população passa a ser a série do Ministério da Saúde** ("Estudo de Estimativas Populacionais por
   Município, Idade e Sexo 2000-2025", consultado no TabNet em 13/11/2026).
7. **O Simulador abre em modo simples.** O resto fica em "Avançado".

---

# Parte A — A estrutura comum

## A.1 A ideia

As duas ferramentas aprendem com a própria base. Elas olham para territórios de tamanho parecido e só para o que veio antes de cada data.

| | Detector | Simulador |
|---|---|---|
| Pergunta | Isto é comum nesta base? | Se continuar como vinha, onde chega? Quanto isso costuma errar aqui? |
| Aprende com | As mudanças anteriores de territórios do mesmo porte | As retroprojeções: o Agente refaz, em datas passadas, a projeção que teria feito e confere com o que aconteceu depois |
| Mostra | O nível de alerta: moderado, elevado ou crítico | O cenário e a faixa "8 em cada 10" |
| Quando a base não sustenta | "Sem comparações suficientes", com o motivo | "Faixa indisponível", com o motivo. Sem retroprojeção suficiente, o cenário usa o jeito mais simples (manter o último valor) |

## A.2 As regras comuns

1. **Só o passado.**
   - O Detector compara cada data só com as mudanças anteriores a ela.
   - O Simulador ajusta cada retroprojeção só com os registros até a origem e confere com o que veio depois.
2. **Territórios de tamanho parecido (porte).**
   - O porte é o número de profissionais no registro anterior (Detector; no sinal 7, o patamar) ou na origem (Simulador).
   - Faixas: 1–3, 4–9, 10–19, 20–49, 50–99, 100–299, 300–999, 1.000–2.999, 3.000–9.999 e 10.000 ou mais.
   - As quatro últimas substituem o antigo "300 ou mais". O motivo está na seção A.5.
3. **Só com casos suficientes.** Cada nível de alerta, cada faixa e cada escolha de método só aparece quando a base tem casos bastantes. Os números estão nas seções B.1 e C.4.
4. **Quando falta história, a mesma retaguarda nas duas ferramentas.**
   - Primeiro, junta a faixa de porte com as vizinhas, uma de cada lado.
   - No Detector, se ainda faltar, só o moderado pode juntar todas as faixas, com a mudança padronizada pelo tamanho.
   - No Simulador, se ainda faltar, a faixa pode juntar portes menores. Eles variam mais, então a faixa fica mais larga, e por isso mais cautelosa. A tela avisa.
   - Se nada bastar, a tela diz que a base não sustenta e por quê.
5. **Tudo dito na tela, em palavras simples:**
   - o tipo de critério ("comparado com a base" ou "por convenção");
   - com quem o território foi comparado ("territórios de 20 a 49 profissionais");
   - quantos casos havia.

   Os detalhes ficam no "Entenda".
6. **Nomes da base.** "Profissionais", "estado", "junho" e "Brasil" só aparecem quando vêm da base. Na base do Brasil, a tela diz "médicos", "estado", "junho" e "Brasil".

## A.3 O perfil da base

O Agente lê isto sozinho, antes de abrir as ferramentas.

| O quê | Como o Agente lê | Se faltar |
|---|---|---|
| Datas e intervalos | Mede os meses entre registros e compara só intervalos iguais | Com intervalos irregulares, agrupa os de duração parecida |
| Série anual | Usa o mês presente em todos os anos (na base do Brasil, junho) | Ficam indisponíveis os sinais anuais (3, 4, 7 e 8 a 10) e a retroprojeção do Simulador |
| Portes | Faixas da regra 2, juntando vizinhas quando faltam casos | — |
| Grupo de cima | A coluna de grupo da base (na base do Brasil, o estado) | O Simulador usa o crescimento da base toda; o sinal 10 fica indisponível |
| População | Detecta valores repetidos e saltos fora do comum e separa os trechos comparáveis | Ficam indisponíveis os sinais 8 a 11 e as comparações por habitante do Simulador |
| Coordenadas | Com o referencial informado | O sinal 11 fica indisponível |
| O que a contagem conta | Como nas análises: pessoas únicas ou soma | Aviso de dupla contagem |
| Nomes | O mecanismo de nomes da base | — |

**Resumo antes de abrir.** Numa base nova, o Agente mostra um resumo do que dá e do que não dá para fazer. Exemplo para uma base de 20 distritos de porte parecido, com registros a cada 6 meses durante 10 anos:

- **Dá para:**
  - alertas moderados desde o 2º ano;
  - alertas elevados a partir do 4º ano.
- **Não dá para:**
  - alertas críticos: eles pedem 999 comparações, e esta base chega a 360;
  - a faixa do Simulador: ela pede 200 casos por prazo, e esta base tem cerca de 120.

## A.4 Ajustes e "Entenda", do mesmo jeito nas duas ferramentas

- **Ajustes escritos em frases, com os campos dentro delas.**
  - Detector: "Alerta elevado quando a queda for de pelo menos [2] profissionais e [20]% do que havia, e for rara: em territórios do mesmo porte, só 1 em cada [100] mudanças anteriores foi uma queda igual ou maior."
  - Simulador: "Mostrar a faixa onde o valor real ficou em [8] de cada [10] retroprojeções de territórios do mesmo porte."
- **Configuração exploratória.** Trocar um valor torna a configuração "exploratória". O aviso aparece no alto, nos textos e nas exportações, e o botão "Voltar ao padrão" fica sempre à vista.
- **"Entenda".**
  - Traz duas ou três frases simples e um exemplo com números.
  - Abre com o mouse, com um toque ou pelo teclado, e fecha ao sair.
  - A explicação inteira fica em "Ver explicação completa".

## A.5 Por que mudar as faixas de porte acima de 300

A faixa "300 ou mais" junta municípios de 300 a mais de 10.000 médicos. Nas duas ferramentas, isso distorce o resultado:
- os de 300 a 999 recebem alertas demais;
- os maiores quase nunca recebem alerta;
- as faixas do Simulador ficam largas demais para os maiores.

Os testes abaixo usam a base do Brasil (municípios, 2014–2024). No Detector, entram só os dados anteriores a cada data. No Simulador, as retroprojeções de jun/2017 a jun/2023.

| Municípios com | Detector: alertas moderados (meta 5%), hoje → proposta | Simulador: faixa de 8 em 10 em 1 ano, quanto cobriu (meta 80%), hoje → proposta |
|---|---|---|
| 300 a 999 | 6,7% → 5,1% | 76% → 80% |
| 1.000 a 2.999 | 2,7% → 4,4% | 87% → 78% |
| 3.000 a 9.999 | 1,3% (3.000 ou mais, juntos) → 4,9% | 92% → 88% (junta as vizinhas) |
| 10.000 ou mais | (no 1,3% acima) → 3,2% (94 avaliações) | 94% → provisória (poucos casos) |

- **Como ler a coluna do Detector:** na proposta, a taxa de alertas fica perto da meta em todos os tamanhos.
- **Como ler a coluna do Simulador:**
  - "Hoje" é a faixa única de 300 ou mais, aplicada a cada grupo.
  - "Proposta" é a faixa de cada porte, conferida deixando cada origem de fora.
- **Abaixo de 300**, as faixas de porte são as de hoje. No Simulador, a faixa "1 a 9" passa a ser 1–3 e 4–9, como no Detector.

---

# Parte B — Detector de Sinais

## B.1 Os três níveis

| Nível | Raridade padrão | Comparações anteriores necessárias | Cor |
|---|---|---|---|
| Moderado | 1 em cada 20 | pelo menos 19 | amarelo |
| Elevado | 1 em cada 100 | pelo menos 99 | laranja |
| Crítico | 1 em cada 1.000 | pelo menos 999 | vermelho |

### Como se mede a raridade

- **Quem entra na comparação:** todas as mudanças anteriores à data avaliada, de todos os territórios do mesmo porte, com o mesmo tempo entre registros. Entram aumentos, estabilidade e quedas, de muitos territórios e de muitas datas.
- **A conta:** raridade = (mudanças anteriores iguais ou piores + 1) ÷ (total de mudanças anteriores + 1).
- **Por que o "+1":** a própria mudança entra na conta. Isso evita dizer "nunca aconteceu" quando a história é curta, e é a prática padrão para comparar um valor com o que foi observado.
- **Comparações mínimas:** é o "+1" que fixa os mínimos de 19, 99 e 999 comparações da tabela.

### Regras

- **Tamanho mínimo.** Além de rara, a mudança precisa ter um tamanho mínimo, para não gerar alerta por um único profissional. Os mínimos estão na seção B.2.
- **Nível sem base fica de fora.** A tela diz, por exemplo: "a base ainda não tem história para dizer se esta queda é elevada ou crítica: são 54 comparações, e o elevado pede 99".
- **O tipo de critério sempre aparece**: "comparado com a base" ou "por convenção".
- **Um nível por território, sem soma.** O alerta do território é o maior nível entre os seus sinais. Não há soma nem índice. Sinais que vêm da mesma queda contam como um evento só, e a tela diz isso.
- **"1 em cada 20" quer dizer "incomum nesta base".** Por construção, numa data qualquer, cerca de 1 em cada 20 territórios recebe moderado em cada sinal de raridade. Isso não é erro: o alerta diz "incomum nesta base", não "comprovadamente pior".
- **Aviso da base.** Se, numa mesma data, muitos territórios caem juntos (mais que o triplo do esperado), a tela avisa que pode ter havido mudança no registro da base, e não nos territórios.
- **Cor com texto.** O nível aparece sempre escrito, nunca só pela cor.

### Testes com a base do Brasil

Quedas de um registro para o seguinte, municípios, 2014–2024, 105.786 avaliações. O teste mede só a raridade, sem o tamanho mínimo; com o tamanho mínimo, há menos alertas.

| Régua | 1 em 20 (meta 5%) | 1 em 100 (meta 1%) | 1 em 1.000 (meta 0,1%) |
|---|---|---|---|
| Por porte (proposta) | 4,5% (de 2,5% a 6,0% por porte) | 0,88% (de 0,5% a 1,35%; 0 em 64 avaliações nos 10.000 ou mais) | 0,09% (de 0% a 0,20%) |
| Todos os portes juntos, sem padronizar | de 7,6% nos menores a 0,4% nos maiores | de 1,6% a 0,05% | de 0,16% a 0% |
| Todos os portes juntos, padronizando pelo tamanho | de 3,4% a 6,4% | de 0,35% a 2,5% | de 0% a 0,71% |

**O que os testes mostram**

- **Por porte, a régua acerta** nos três níveis.
- **Juntar portes sem padronizar erra muito:** os territórios pequenos recebem alerta demais, e os grandes, de menos.
- **Padronizando pelo tamanho, o moderado fica aceitável. O elevado e o crítico, não.** Por isso, na retaguarda, só o moderado junta todas as faixas.
- **Crítico nos maiores municípios:** de 3.000 médicos para cima, a base não tem 999 comparações de tamanho parecido, e a tela diz "sem comparações suficientes".
  - Hoje, esses municípios são comparados com os de 300 a 999, que variam muito mais.

**Base pequena: os 27 estados.** Usam a mesma regra, com a base dos estados:
- **moderado** desde jun/2015: saiu em 6,7% das avaliações (510 avaliações; meta 5%);
- **elevado** desde jun/2019: nenhum alerta em 275 avaliações;
- **crítico** nunca: em jun/2024 os estados têm 270 comparações, e o crítico pede 999.

## B.2 Os 12 sinais

Todos os limites são padrões e podem ser trocados (seção A.4).

| # | Sinal | O que mede | Moderado | Elevado | Crítico | Critério |
|---|---|---|---|---|---|---|
| 1 | Poucos profissionais | Número no último registro | 4 ou 5 | 2 ou 3 | 1 | Por convenção |
| 2 | Nenhum profissional registrado | Zero confirmado, e há quanto tempo | — | — | Zero, com a duração | Por convenção |
| 3 | Declínio persistente | Quedas anuais seguidas e perda acumulada | 2 quedas e perda de 10% ou mais | 3 quedas e 20% ou mais | 4 quedas e 30% ou mais | Por convenção |
| 4 | Desaceleração | A classe "Crescimento desacelerado" da Análise de Tendência | A classe em 2 anos seguidos | — | — | Por convenção (exploratório) |
| 5 | Instabilidade | Oscilação comparada com a típica do porte | 1 em 20 | — | — | Comparado com a base |
| 6 | Queda recente | Queda de um registro para o seguinte | 1 em 20, e queda de pelo menos 2 profissionais e 10% | 1 em 100, e pelo menos 2 e 20% | 1 em 1.000, e pelo menos 3 e 30% | Comparado com a base, com tamanho mínimo |
| 7 | Abaixo do que já teve | Distância ao patamar: a maior média de 2 anos completos | 2 últimos registros 15% ou mais abaixo | Isso, e 1 em 100 | 4 últimos registros 30% ou mais abaixo, e 1 em 1.000 | Por convenção e comparado com a base; patamar de pelo menos 20 |
| 8 | Menos profissionais por habitante | Variação da taxa em 2 anos | 1 em 20 | 1 em 100 | 1 em 1.000 | Comparado com a base; população comparável; pelo menos 20 no início |
| 9 | Perda de posição | Variação do percentil da taxa em 2 anos | 1 em 20 | 1 em 100 | 1 em 1.000 | Idem |
| 10 | Mais longe da referência | Variação do índice frente ao grupo de cima, sem o próprio território, em 2 anos | 1 em 20 | 1 em 100 | 1 em 1.000 | Idem; precisa de grupo de cima |
| 11 | Distância | Km em linha reta até o território mais próximo com taxa de pelo menos X% da taxa da base toda, e em que posição essa distância fica | Só contexto | — | — | X ajustável de 10% a 500%; o padrão é o de hoje |
| 12 | Sinais juntos | Quais sinais coincidem no território, agrupando os efeitos do mesmo evento | Mostra quais coincidem; não soma | — | — | — |

### Notas

- **Sinais 1 e 2:** os mesmos limites da V2.2, com a mesma histerese: a piora aparece na hora, e a melhora, depois de dois registros.
- **Uma queda de 2 para 1 profissional** não vira alerta de queda (sinal 6), porque é só 1 profissional. Ela aparece como crítico em "Poucos profissionais" (sinal 1). O "Entenda" do sinal 6 traz esse exemplo.
- **Sinal 3, por convenção.** Na base do Brasil, de jun/2018 a jun/2024:
  - frequência: moderado em 3,6% das avaliações, elevado em 0,6% e crítico em 0,14%, perto do que a raridade daria (5%, 1% e 0,1%);
  - por isso, o sinal não precisa de régua própria;
  - por porte: os mais frequentes ficam entre 10 e 49 médicos (moderado em cerca de 5%); de 1.000 para cima, quase nunca.
- **Sinal 4:** a V2.2 mostrou que a repetição da classe não antecipa o crescimento seguinte. O moderado fica rotulado como exploratório, e o "Entenda" diz: "mostra uma mudança de ritmo; não indica o que vem depois".
- **Sinal 7:** o crítico, hoje "não calibrável", passa a valer quando houver 999 comparações. O relatório de calibração precisa confirmar isso (seção F).
- **Sinal 8, ordem de grandeza.** Hoje, com o limite fixo de queda de 10%, ele marca de 9,5% a 20,6% dos municípios avaliados, conforme a janela.
  - Pela raridade, na base atual (todas as janelas com população comparável juntas, 7.730 avaliações), os níveis seriam: moderado com queda de 23% ou mais, elevado com 38% ou mais e crítico com 60% ou mais.
  - Esses valores serão refeitos depois da troca da população.
- **Estados como unidade:** passam a ter régua própria, com a base dos estados (seção B.1).
- **Conjuntos:** continuam sem nível. Um conjunto não tem outros iguais para comparar, então a tela mostra os fatos e o motivo.
- **Sinal 11:** nunca vira alerta e nunca usa as palavras "isolamento" ou "desassistência".

## B.3 A tela do Detector

```
Detector de Sinais                                               (Entenda)
Compara cada território com o que é comum na própria base.

Até [jun/2024 ▾]   Nível [Todos ▾]   Sinal [Todos ▾]   [Buscar território]   (Ajustar critérios)

[n] críticos · [n] elevados · [n] moderados · [n] sem alerta · [n] sem comparações suficientes
[ Lista ]  [ Mapa ]  [ Gráfico ]

Território            Alerta      Por quê                                   Último registro
Território A (UF)     Crítico     Só 1 profissional (+1 sinal)              jun/2024 · 1
Território B (UF)     Elevado     [x]% abaixo do que já teve                jun/2024 · [n]
```

Esboço ilustrativo: nomes e números são marcadores, não dados.

- **Primeira tela:** uma lista com 4 colunas. O resumo dos níveis, no alto, é clicável e funciona como filtro.
- **Visões:** Lista (padrão), Mapa (cores dos níveis, com divisas) e Gráfico.
- **Ajustar critérios:** os limites em frases, com os campos dentro delas (seção A.4).
- **Detalhe, ao clicar no território:**
  - a série, com os registros marcados;
  - os 12 sinais em quatro grupos: Quantos há (1–2), Como mudou (3 a 7), Comparado com outros (8 a 10) e Onde fica (11), mais Juntos (12);
  - em cada sinal, o nível, uma frase e o "Entenda".
- **Linguagem:** sem termos técnicos na tela principal. "Porte", "patamar", "percentil" e "1 em cada N" sempre com "Entenda".

---

# Parte C — Simulador de Cenários

## C.1 A ideia

O Simulador mostra para onde o território iria se continuasse como vinha, e o efeito das mudanças que a pessoa quer testar. O "como vinha" e a margem de erro vêm da própria base, pela retroprojeção: o Agente refaz no passado a projeção que teria feito e confere com o que aconteceu depois.

Todo resultado continua sendo cenário hipotético, nunca previsão, com o texto fixo da V2.2.

## C.2 O modo simples: três escolhas

1. **Território:** vem da seleção, e dá para trocar.
2. **O que testar:**
   - só continuar como vinha;
   - acrescentar [N] em [data];
   - retirar [N] em [data];
   - chegar a [meta] em [data]. O Agente calcula quantos faltariam: é o planejamento inverso, com o menor número inteiro.
3. **Até quando:** qualquer data depois do último registro. Os atalhos de 1, 2 e 4 anos são só atalhos.

**O resultado:**
- o gráfico, com o observado, o cenário, a faixa (quando houver) e os eventos;
- a frase fixa do cenário;
- três números: no último registro, na data final e a diferença (ou "precisaria acrescentar N").

O "Entenda" fica no jeito de projetar e na faixa.

O "Simular recuperação", que vem do Detector, abre este modo com a meta igual ao patamar do sinal 7. A meta continua editável e rotulada como hipótese.

## C.3 "Continuar como vinha": o jeito que a própria base escolhe

### Os candidatos

Todos já existem no motor, menos o terceiro.

| Jeito | Conta | Precisa de |
|---|---|---|
| Manter o último valor (M0) | O último registro | Um registro |
| Último valor com o crescimento recente do grupo de cima (M0d) | Último registro × (1 + crescimento anual do grupo nos 3 anos antes da origem) ^ anos | Grupo de cima com 3 anos de registros |
| Último valor com o crescimento recente da base toda (M0g, novo) | O mesmo, com a soma de todos os territórios | 3 anos de registros |
| Crescimento recente do próprio território (M1) | Taxa composta do território nos 3 anos antes da origem | Início e fim acima de zero |

### A regra de escolha, para cada nível de território (municípios, estados…)

1. Na retroprojeção da própria base, cada jeito é comparado com "manter o último valor":
   - a medida é o erro absoluto médio;
   - cada porte tem o mesmo peso, e os portes com menos de 30 casos juntam-se aos vizinhos;
   - entram todos os prazos, de 1 a 4 anos.
2. **Só vale** um jeito que errou menos que manter o último valor no total e em pelo menos metade das combinações de origem e prazo.
3. **Entre os que valem, fica o mais próximo do território** cujo erro esteja a até 5% do melhor. A ordem de proximidade é: o próprio território, o grupo de cima, a base toda.
   - Quando dois jeitos acertam quase igual, fica o que acompanha melhor o que acontece perto do território.
4. **Exceção por porte.** Se, num porte, o escolhido errar mais que manter o último valor em todos os prazos, esse porte usa o último valor.
5. **Sem retroprojeção:** com menos de 3 origens, o padrão é manter o último valor.

### Resultado na base do Brasil

Origens de jun/2017 a jun/2023. Erro frente a "manter o último valor" (1,00 = igual; abaixo de 1, erra menos).

| Nível | Grupo de cima | Base toda | Próprio território | Escolhido |
|---|---|---|---|---|
| Municípios | 0,714 (menos erro em 22 de 22) | 0,700 (22 de 22) | 1,016 (2 de 22) | Grupo de cima (o estado): 2% do melhor. É o padrão de hoje |
| Estados | — (é a base toda) | 0,410 (22 de 22) | 0,398 (22 de 22) | Próprio território. É o padrão de hoje |

- **A regra reproduz o que já está em uso.** Na base do Brasil, o padrão não muda.
- **Base sem grupo de cima:** o crescimento da base toda errou quase o mesmo que o do estado (0,700 contra 0,714). É uma boa retaguarda.
- **Municípios de 1 a 9 médicos:** o padrão erra um pouco mais que manter o último valor em 1 ano (1,04 e 1,02), mas menos em 2 a 4 anos. Não entra na exceção, como hoje.

## C.4 A faixa "8 em cada 10"

- **O que é.** Entre as retroprojeções de territórios do mesmo porte e com o mesmo prazo, 8 em cada 10 terminaram dentro da faixa. Tecnicamente, vai do 10º ao 90º percentil do erro relativo (observado ÷ cenário − 1).
- **Casos mínimos.** São pelo menos 20 casos fora da faixa de cada lado:
  - 200 casos para 8 em 10;
  - 80 casos para 5 em 10;
  - 400 casos para 9 em 10.
- **Retaguarda** (regra A.2.4): juntar as vizinhas; depois, portes menores, com a faixa mais larga e rotulada; se nada bastar, "indisponível".
- **Conferência no tempo.** A faixa é montada só com retroprojeções cujo resultado já era conhecido e testada nas origens seguintes. Para 8 em 10:
  - **conferida:** cobriu pelo menos 75%;
  - **provisória:** não deu para conferir (menos de 3 origens de teste ou menos de 50 casos de teste), ou cobriu de 70% a 75%;
  - **indisponível:** cobriu menos de 70%.
  - Para 5 em 10 e 9 em 10, valem as mesmas distâncias: até 5 pontos abaixo da meta, conferida; de 5 a 10 pontos abaixo, provisória.
- **Prazo:** a faixa vai só até o maior prazo com casos suficientes. O cenário continua até a data escolhida, com os avisos de horizonte de hoje.
- **Só para o jeito escolhido pela base.** Para os outros jeitos e para território em zero, a faixa fica "indisponível".
- **Continua como hoje:**
  - a faixa acompanha a intervenção;
  - nos conjuntos, a faixa é rotulada "aproximação".

### Resultado na base do Brasil (municípios, padrão M0d)

Faixa de 8 em 10. Os valores com "(p)" são provisórios; os demais, conferidos.

| Médicos na origem | 1 ano | 2 anos | 3 anos | 4 anos |
|---|---|---|---|---|
| 1–3 | −9% a +87% | −17% a +105% | −21% a +140% (p) | −21% a +153% (p) |
| 4–9 | −26% a +41% | −31% a +56% | −33% a +69% (p) | −34% a +82% (p) |
| 10–19 | −23% a +29% | −28% a +40% | −29% a +54% (p) | −30% a +62% (p) |
| 20–49 | −19% a +24% | −23% a +34% | −24% a +44% (p) | −25% a +55% (p) |
| 50–99 | −15% a +20% | −20% a +30% | −20% a +42% (p) | −19% a +55% (p) |
| 100–299 | −12% a +17% | −16% a +26% | −16% a +34% (p) | −17% a +42% (p) |
| 300–999 | −9% a +12% | −12% a +20% | −14% a +28% (p) | −12% a +37% (p) |
| 1.000–2.999 | −6% a +8% | −8% a +16% | −10% a +21% (p) | −10% a +28% (p) |
| 3.000–9.999 (com as vizinhas) | −6% a +7% | −8% a +14% | −10% a +19% (p) | −9% a +23% (p) |
| 10.000 ou mais (8 municípios) | −5% a +5% (p) | −8% a +14% (p, portes menores) | −10% a +19% (p, portes menores) | −9% a +23% (p, portes menores) |

- **A conferência no tempo cobriu:**
  - em 1 ano, de 75% a 79% (6 origens de teste);
  - em 2 anos, de 75% a 82% (4 origens de teste);
  - nos portes com faixas juntadas, de 84% a 90%: são faixas mais largas, mais cautelosas.
- **3 e 4 anos ficam provisórios, como hoje.** Em 3 anos só há duas origens de teste (a cobertura foi de 71% a 82%). Em 4 anos, não dá para conferir nesta base.
- **Até 300 médicos, as faixas são praticamente as de hoje**, com diferenças de até 1 ponto, por detalhes do teste. A única mudança é a separação de "1 a 9" em 1–3 e 4–9.
  - Com 1 a 3 médicos, a faixa é assimétrica: um médico a mais já é +33% a +100%.
- **Estados:** em 1 ano há 189 casos, e a faixa de 8 em 10 pede 200. A faixa continua indisponível, como hoje; a de 5 em 10 seria possível.

## C.5 Ajustar premissas ("Avançado"), em frases com campos

- "Continuar como vinha: [o jeito escolhido pela base ▾], com o crescimento dos [3] anos antes de [jun/2024]."
- "Mostrar a faixa onde o valor real ficou em [8] de cada [10] retroprojeções de territórios do mesmo porte." Opções: 5, 8 ou 9 em 10.
- "Dos [médicos] acrescentados, a cada ano permanecem [100]%."
- "Comparar com [referência ▾] por [diferença ▾ / razão / taxa por 1.000 habitantes], com a população [igual à do último ano ▾ / crescendo [x]% ao ano]."

A faixa existe só para o jeito e a janela escolhidos pela base. Trocar um dos dois tira a faixa, e a tela diz por quê.

**Exemplos de "Entenda"** (os números são ilustrativos):

- **Jeito de projetar:** "O cenário parte do último registro e soma o crescimento recente do estado: +[x]% ao ano nos últimos 3 anos. Usamos este jeito porque, nesta base, ele errou menos que simplesmente manter o último valor."
- **Faixa:** "Refizemos este tipo de projeção em datas passadas, para territórios do mesmo porte. Em 8 de cada 10 vezes, o valor real ficou dentro desta faixa. Não é garantia: o passado testado (2017–2024) foi de crescimento."
- **Faixa provisória:** "Ainda não deu para conferir esta faixa com dados que vieram depois, ou a conferência ficou um pouco abaixo do esperado."

## C.6 Níveis no cenário (hipótese)

- **Só os sinais 1 e 2** (contagem, por convenção) podem ser aplicados a um valor simulado. Exemplo: "No cenário, em jun/2026, o território teria 3 médicos: seria Elevado em 'Poucos profissionais' (hipótese do cenário)."
- **Faixa que cruza um limite:** a tela diz "pode ficar entre moderado e elevado", sem escolher um só.
- **Sinais de raridade (5 a 10) nunca são aplicados a valores simulados**, como manda o V22.

## C.7 A tela do Simulador (modo simples)

```
Simulador de Cenários                                            (Entenda)
Cenário hipotético, não é previsão. Último registro da base: jun/2024.

Território   [Território A (UF) ▾]
O que testar ( ) Só continuar como vinha     ( ) Acrescentar [ N ] em [data]
             ( ) Retirar [ N ] em [data]     ( ) Chegar a [ meta ] em [data]
Até quando   [jun/2028]   1 ano · 2 anos · 4 anos                     [ Calcular ]

[gráfico: observado ── · cenário - - - · faixa ░ · eventos ●]
Cenário hipotético, não é previsão: com o método [..] e as premissas [..], Território A teria [N] médicos em jun/2028.
No último registro: [N0] · Em jun/2028: [N] · Diferença: [±D]          (Entenda: jeito de projetar · faixa)
Avançado ▸
```

Esboço ilustrativo: nomes e números são marcadores.

## C.8 O que fica no "Avançado"

- até 5 cenários lado a lado;
- outros jeitos de projetar (M2, M3 e taxa digitada pela pessoa) e outras janelas;
- referências fixas ou dinâmicas, e a comparação com elas;
- calendário de acréscimos e permanência;
- conjuntos e vários territórios (até 100);
- exportar e importar;
- "Como os métodos se saíram no passado", com as tabelas das seções C.3 e C.4 para a base em uso.

## C.9 Qualquer base: o que muda no Simulador

- **Nada fixo da base do Brasil.** "Junho", "UF" e "médicos" deixam de estar escritos no motor. O mês âncora, o grupo de cima e os nomes vêm do perfil da base.
- **Recalculado para cada base.** A retroprojeção, a escolha do jeito e as faixas são recalculadas para cada base e versão, uma vez, automaticamente.
- **Sem grupo de cima:** o candidato é o crescimento da base toda.
- **Base sem história bastante:** só "manter o último valor" e faixa indisponível, com o motivo.
- **Planilhas enviadas:** as duas ferramentas passam a aceitar planilhas enviadas, que hoje ficam bloqueadas.

---

# Parte D — Troca da população na base do Brasil

**Fonte**
- **Edição usada:** "População Residente - Estudo de Estimativas Populacionais por Município, Idade e Sexo 2000-2025 - Brasil"
  (trabalho coordenado pela RIPSA; realização: CGI Demográfico/RIPSA e CGIAE/SVSA/Ministério da Saúde; dados básicos: IBGE),
  consultada no TabNet em 13/11/2026.
  - Arquivo exportado: `populacao_MS_2014_2024.csv`, 470.817 bytes, SHA-256
    `552841d5350ebe38b3628d23e2e3f2596e921056cf3d3c8190cad0e0f5b9ac4c`.
- **Onde.** Na página "Dados Populacionais" do Ministério da Saúde, o link "População municipal por sexo e idade - 2000 a 2025" abre o TabNet. Não há arquivo pronto para baixar: a tabela é montada no TabNet e exportada em CSV.
  - Linha: Município. Coluna: Ano.
  - Anos: só de 2014 a 2024.
  - Sexo e faixa etária: todas as categorias.
- **Não confundir** com "População municipal utilizada pelo TCU", que é outra série.
- Baixar só os totais por município e ano, de 2014 a 2024. É um arquivo pequeno.
- Registrar a fonte, a data de acesso e a nota de método.

**Antes de trocar, com relatório e pausa para o responsável**
1. Os mesmos 5.570 municípios, com os códigos casados: a base usa 6 dígitos, e a série pode vir com 7.
2. Nenhum valor faltando ou igual a zero. Os totais por ano e por estado são conferidos.
3. Variação de um ano para o outro sem os saltos de hoje (2018, 2021–2023 e 2024).
4. Comparação de 2024 com o valor atual. Se for igual, as telas de jun/2024 não mudam.
5. Quanto mudam as taxas em cada ano: no Brasil, por estado, e quantos municípios mudam mais de 5% e mais de 10%.

**Na troca**
- **Só a coluna de população muda.** Contagens, códigos, coordenadas e datas ficam idênticos, conferidos linha a linha.
- **Manifesto atualizado.** O manifesto da base (tamanho, SHA-256 e versão) é atualizado, e a mudança fica registrada no documento de validação da base.
- **A SPEC não muda.** Ela não fixa a fonte da população; só define a densidade como a contagem dividida pela população do mesmo território.

**Depois**
- **Revisar tudo que usa população:**
  - as densidades das análises e o "Desde jun/2021";
  - a Análise de Tendência por taxa;
  - os sinais 8 a 11;
  - as comparações por taxa do Simulador;
  - os números do assistente.
- **"Comparação não habilitada"** passa a vir da detecção automática do perfil (seção A.3), e não de anos fixos.
- **Testes:** os que têm valores anteriores a 2024 mudam de propósito, e a mudança fica registrada.

**O que muda para quem usa**
- As taxas de 2014 a 2023 mudam: pouco em 2014, mais perto de 2021–2023.
- As de 2024 ficam iguais, se a população de 2024 for a mesma.
- O que usa só a contagem não muda.

**O que foi feito na troca (13/11/2026)**
- As verificações da pausa 1 passaram: 5.570 municípios casados, nenhum valor faltando ou zero, sem os saltos de 2018, 2021–2023 e
  2024. A mudança das taxas foi maior que o previsto acima: em 2014, 1.105 municípios mudam mais de 5%; em 2023, 3.122.
- A população de 2024 é igual em 5.568 municípios. Em Canindé de São Francisco (33.491) e Poço Redondo (29.117), em Sergipe, vale
  a série nova: são os valores da tabela corrigida do IBGE de 30/12/2024; a base tinha os da tabela de 01/11/2024.
- Por decisão do responsável na pausa 1, a troca também corrigiu o nome de 19 municípios, pelo nome oficial do IBGE; a busca pelo
  nome antigo continua achando o município.
- Com a série nova, a base inteira é um trecho só de população comparável (2014–2024): nenhum ano fica com "comparação não
  habilitada".
- O registro completo (fonte, valores, lista dos nomes e nova versão da base) está em
  [DADOS_BRASIL_VALIDACAO.md](DADOS_BRASIL_VALIDACAO.md).

---

# Parte E — O que muda em relação à V2.2 e ao V22

## Nas duas ferramentas

- **Portes acima de 300** em quatro faixas (seção A.5), com a mesma retaguarda nas duas ferramentas.
- **Nomes da base** em tudo; "junho" e "Brasil" só quando vêm dela.
- **Ajustes** em frases, com o "Entenda".
- **Planilhas enviadas** deixam de ficar bloqueadas.

## No Detector

- **Nomes dos níveis:** "atenção, alta, crítica" passam a ser "moderado, elevado, crítico". "Alerta" vale para os três níveis, sempre com o tipo de critério dito. Isso substitui, nesse ponto, a decisão 1 do V22.
- **Raridade:** conta com o "+1", com os mínimos de 19, 99 e 999 comparações. Hoje são 100 e 1.000, sem o "+1".
- **Sinal 3:** hoje mostra "forte" e "muito forte", sem nível. Passa a ter moderado, elevado e um crítico novo, por convenção.
- **Sinal 4:** de "sinal observado" passa a moderado, por convenção (exploratório).
- **Sinal 5:** de descritivo passa a moderado, por raridade.
- **Sinal 6:** ganha o nível moderado.
- **Sinal 7:** o crítico deixa de ser "não calibrável" quando houver 999 comparações, sujeito à confirmação.
- **Sinais 8 a 10:** os limites fixos dão lugar à raridade na base.
- **Estados como unidade:** passam a ter régua própria. Os conjuntos continuam sem nível.

## No Simulador

- **Método padrão:** escolhido pela retroprojeção da própria base. Na base do Brasil, é o mesmo de hoje.
- **Novo candidato:** o crescimento da base toda, para bases sem grupo de cima.
- **Faixa:**
  - mínimo de 200 casos (hoje, 100);
  - conferência no tempo, com três estados: conferida, provisória e indisponível;
  - na base do Brasil, a faixa "1 a 9" separa-se em 1–3 e 4–9, e os maiores municípios ganham faixas próprias, mais estreitas e mais certas.
- **Modo simples em uma tela** e níveis no cenário (sinais 1 e 2, como hipótese).

---

# Parte F — Limites e o que o relatório de calibração precisa trazer

**Bases pequenas**
- Numa base pequena, o crítico não existe, o elevado só aparece depois de alguns anos e a faixa do Simulador fica indisponível. A tela diz isso, em vez de esconder.
- Nos estados, o moderado saiu um pouco acima da meta: 6,7% para 5%, em 510 avaliações. É preciso acompanhar.

**O que os testes ainda não cobrem**
- Os testes desta proposta não usaram as marcas de descontinuidade (pico que volta e quebra de fonte), que o motor exclui. O relatório de calibração refaz os testes com elas.
- O relatório de calibração precisa trazer, com a régua nova:
  - os sinais 5, 7 (inclusive o crítico), 9 e 10;
  - a proporção de territórios com algum moderado. Se passar de cerca de 20%, rever o padrão (por exemplo, para 1 em 50).
  - Se o crítico do sinal 7 sair longe da meta, ele continua "não calibrável", como hoje.

**Simulador**
- O passado testado (2017–2024) foi de crescimento em quase todo o país. As faixas e a escolha do jeito de projetar valem para esse período.
- As origens se sobrepõem no tempo, então os casos não são independentes.
- As faixas de 3 e 4 anos ficam provisórias nesta base, porque há poucas origens para conferir.

**Depois da troca da população**
- Refazer os testes dos sinais 8 a 10 e das comparações por taxa.

---

## Anexo — Como os testes foram feitos

**Dados**
- Cópia de leitura da base versionada do Brasil: `Dados_Municipios_Brasil.csv` e `Dados_Estados_Brasil.csv`, de jan/2014 a jun/2024.
- Nada foi gravado no repositório.

**Detector**
- **Mudança:** de um registro para o seguinte, com pelo menos 1 profissional no anterior. Os intervalos de 5 e de 7 meses foram comparados separadamente.
- **Raridade:** com "+1". Cada nível só foi avaliado com as comparações mínimas.
- **Padronização pelo tamanho:** mudança ÷ tamanho^(θ/2).
  - θ vem da relação entre o tamanho e a dispersão robusta (MAD).
  - Na retaguarda do moderado, θ é estimado só com o passado: deu 1,30 nos municípios e 1,54 nos estados, com poucos dados.
  - Na linha "padronizando pelo tamanho" da tabela B.1, θ = 1,31, com toda a série.
- **Sinal 3:** junho a junho, de 2018 a 2024, com o porte pelo valor do início da sequência.
- **Sinal 8:** taxa de junho a junho em 2 anos, municípios com pelo menos 20 profissionais no início, janelas 2014–2016, 2015–2017, 2018–2020 e 2019–2021.

**Simulador**
- **Retroprojeção:** origens em junho de 2017 a 2023, janela de 3 anos e prazos de 1 a 4 anos (junho a junho). Municípios com pelo menos 1 médico na origem e 3 anos antes; o DF ficou de fora, por causa da quebra de fonte até jun/2017.
- **Base toda:** a soma de todos os municípios (ou de todos os estados).
- **Conferência da faixa:** no tempo, com faixas montadas só com retroprojeções cujo resultado já era conhecido na origem testada. A tabela A.5 usa a conferência deixando cada origem de fora.

**Scripts** (área de trabalho, fora do repositório): `t_raridade.py` a `t_raridade4.py`, `t_declinio.py` e `t_simulador.py` a `t_simulador4.py`, com as saídas em JSON.
