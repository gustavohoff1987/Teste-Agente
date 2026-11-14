# Perfil empírico da base para o Detector e o Simulador

Etapa 1 do comando V22 (9/11/2026, seções 8 e 12): o perfil da base versionada antes de qualquer classificação ou projeção
exibida, como pedem as seções 2, 6 e 16 de [Detector e Simulador V2.2](DETECTOR_E_SIMULADOR_V2_2.md) (o Anexo A, versão de
referência). Este documento registra o que a base tem e os bloqueios reais; não muda nenhum comportamento do sistema.

**Como foi feito.** Leitura somente de `Dados_Municipios_Brasil.csv`, `Dados_Estados_Brasil.csv` e `Dados_Brasil.xlsx`, a
versão governada de `dados/brasil/manifesto.json`, com o tamanho e o SHA-256 dos três arquivos conferidos antes e depois da
leitura (iguais). Nenhum dado foi alterado, e nada foi enviado ao provedor de IA. As contagens abaixo são as da leitura de
9/11/2026.

## 1. Escopo, calendário e granularidade

- **Categoria:** só `MEDICINA` nas três fontes. Nenhuma outra profissão existe na base, e nenhuma pode ser inventada.
- **Competências:** 22, de jan/2014 a jun/2024, só janeiro e junho (201401, 201406, …, 202401, 202406), sem lacuna de
  competência inteira.
- **Intervalos reais:** janeiro → junho, 5 meses (11 transições do calendário); junho → janeiro, 7 meses (10 transições). As
  taxas usam o tempo real, e uma data simulada nunca é observação.
- **Linhas:** fonte municipal, 122.534 (5.570 municípios); estadual, 594 (27 UFs × 22); nacional, 22.
- **Registros ausentes (município × competência):** 6 pares, sem linha na fonte municipal: 110110, 313000 e 353286 em jan/2015;
  430607 em jun/2015; 420555 em jan/2017; 431973 em jan/2020. Ausência não é zero: esses pares ficam "ausência de dado".
- **Sem** células vazias, linhas duplicadas (município × competência) ou contagens negativas.

## 2. Fontes e unidade de contagem

| Fonte | Coluna | Unidade (documentada) | Base documental |
|---|---|---|---|
| Municipal | `quantidade` | pessoas por município e competência: quem atua em mais de um município conta em cada um | perfil governado (`brazil_catalog_profile.py`: "unidade pessoas por território e competência") |
| Estadual | `contagem` | médicos únicos na UF e na competência (UF-CONTAGEM-ESTADUAL-1) | decisões D3 a D5 do responsável, 19/10/2026 (`territorial_levels.py`) |
| Nacional | `contagem` | médicos únicos no Brasil na competência | decisões D3 a D5 do responsável, 19/10/2026 |

Os arquivos não declaram a unidade no cabeçalho; ela vem da documentação do responsável e do perfil governado. Os dados são
compatíveis com essa leitura: a soma municipal passa da contagem nacional e cresce com o tempo (razão soma municipal / nacional
de 1,4389 em jan/2014 a 1,6267 em jun/2024), e a soma dos estados passa pouco da nacional (de 1,044 a 1,073), como esperado
quando quem atua em mais de um lugar conta em cada um. Nenhum município passa da contagem do próprio estado na mesma
competência.

**Consequência para os textos:** o N de um município é "médicos registrados no município" (a contagem municipal); uma soma de
municípios ou um conjunto é "soma das contagens dos componentes", nunca "médicos únicos". Só a fonte estadual e a nacional são
pessoas distintas, cada uma no seu nível.

## 3. Zero, ausente e escala

- **Zero confirmado:** 36 municípios tiveram contagem zero em alguma competência (até 9 numa mesma competência); nenhum em
  jun/2024. O zero é registro observado; a ausência (seção 1) não.
- **Escala em jun/2024 (escala estrutural candidata da seção 4.2):** N = 0: nenhum; N = 1: 17 municípios; N = 2–3: 279;
  N = 4–5: 411; N ≥ 6: 4.863.
- **Porte em jun/2024, nas faixas da calibração da perda abrupta:** 1–3: 296; 4–9: 1.238; 10–19: 1.327; 20–49: 1.284;
  50–99: 531; 100–299: 500; 300 ou mais: 394. Quantis da contagem: p10 = 5, p25 = 9, mediana = 19, p75 = 51, p90 = 195.

## 4. Transições e calibração

- **Transições municipais** (competência a competência, com as duas observações): 116.958, sendo 61.264 de 5 meses e 55.694 de
  7 meses.
- **Células da calibração** (porte × intervalo): antes de jun/2024, toda célula tem de 2.769 (300 ou mais, 5 meses) a 16.652
  (4–9, 5 meses) transições anteriores, acima dos mínimos da seção 4.2 (100 transições para α = 1% e 1.000 para α = 0,1%). Nas
  primeiras competências da série, as células ainda não têm esses mínimos: o Detector mostra "não calibrado" até a célula
  alcançá-los (só transições anteriores, sem dados futuros). **Desde 13/11/2026** (comando V23, Proposta V3), a régua do
  Detector usa dez faixas de porte (as quatro acima de 300 no lugar de "300 ou mais"), a raridade com o "+1" e os mínimos de 19,
  99 e 999 comparações; o que a base não sustenta aparece como "sem comparações suficientes", com os números
  ([Detector de Sinais](DETECTOR_DE_SINAIS.md), "Calibração").
- **O movimento de fundo:** a soma municipal sobe em todas as 21 transições (de +0,77% a +4,86%), e, em cada transição, de 18% a
  33% dos municípios caem. A variação relativa mediana, nos municípios com N ≥ 10, é +1,49% nas transições de 5 meses e +2,26%
  nas de 7 meses (médias de +2,77% e +3,74%). As transições de 5 e 7 meses diferem e não se misturam na calibração.

## 5. Descontinuidade de registro

- **Picos que voltam** (salto que se desfaz em até dois registros): 10 municípios, entre eles Rio Rufino (SC, 421505): 4 → 87 → 5
  médicos (jan/2023 → jun/2023 → jan/2024); os demais: Guaiúba (CE), Baixa Grande (BA), Alfredo Chaves (ES), Américo de Campos,
  Palmares Paulista, Sales e Vera Cruz (SP), São Miguel do Iguaçu (PR) e Brochier (RS).
- **Definição ampla** (salto ou queda de 10 ou mais médicos que dobra a contagem ou a corta à metade): 203 municípios, como diz
  o anexo.
- **Quedas grandes** (10 ou mais médicos, até a metade ou menos): 91; 38 persistem. Elas não viram descontinuidade: continuam
  alertáveis, com a nota "verificar registro".
- **Quebra de fonte:** só no Distrito Federal, de jan/2014 a jun/2017: a soma municipal (4.070 a 5.044) fica bem abaixo da contagem
  estadual (7.764 a 8.385); de jan/2018 em diante, as duas coincidem. A janela padrão do DF começa depois da quebra.

## 6. População

Desde 13/11/2026, a população é a série do Ministério da Saúde ("Estudo de Estimativas Populacionais por Município, Idade e
Sexo 2000-2025"; ver [a validação da base](DADOS_BRASIL_VALIDACAO.md)).

- **Janeiro igual a junho** no mesmo ano, em todos os municípios.
- **Muda todo ano, de 2014 a 2024, sem saltos nem repetições na base inteira:** o Brasil cresce de +0,79% (2015) a +0,42% (2024)
  ao ano; de um ano para o outro, de 7 a 30 municípios variam mais de 5% (nenhum mais de 20%), e de 23 a 55 repetem o valor.
  Em 2024, soma 212.583.750 habitantes.
- **Consequência:** a base inteira é um trecho só de população comparável (2014–2024). O trecho é lido da própria base
  (`comparativos.populacao_comparavel`), que é olhada inteira em cada passagem de ano: alguns municípios parados ou com salto
  são normais e não desligam a comparação. Nenhum município tem população ausente ou zero.
- **Até 13/11/2026**, com a população anterior, janeiro e junho diferiam em 25 pares município × ano; 2021, 2022 e 2023 eram
  idênticas (213.318.141 habitantes), e 2024 era de outra base. A mesma leitura dava os trechos 2014–2017 e 2018–2021, e uma
  janela que cruzasse esses limites recebia "comparação não habilitada".

## 7. Coordenadas

- **Inválidas:** 132 linhas, de 6 municípios (170100, 350050, 421265, 422000, 430367 e 500490), ficam sem ponto, com o motivo,
  como hoje no mapa e na Análise Espacial.
- **Que mudam ao longo do tempo:** 8 municípios (110147, 160021, 172085, 221035, 221038, 312520, 350620 e 432035): o contexto
  geográfico (indicador 11) usa a coordenada da competência avaliada, como o motor já faz.

## 8. Bloqueios reais e decisões pendentes

Na interface, estes termos seguem a decisão D-C do anexo (linguagem simples: "sem classificação" no lugar de "não
calibrado", "limite provisório" no lugar de "candidato"); os termos técnicos ficam nos detalhes e no relatório.

1. **Unidade de contagem:** documentada pelo responsável e pelo perfil governado, não pelo CSV (seção 2). Não bloqueia: os textos
   seguem a seção 2, e nenhuma soma municipal é chamada de "médicos únicos".
2. **Intensidade do sinal com limiares candidatos** (decisão 1 do comando: atenção, alta e crítica): a SPEC (CFG-NOR, 4.4.19)
   não traz critério normativo pré-configurado, e o diálogo recusa "crítico" sem critério. **Resolvido em 10/11/2026**
   (decisão D-A do [anexo](DETECTOR_E_SIMULADOR_V2_2.md)): divergência aprovada, só no Detector, com "limite provisório" e
   "sem classificação" (com o motivo) onde faltar calibração. **Desde 13/11/2026** (comando V23, decisão 2), os níveis são
   moderado, elevado e crítico, "alerta" vale para os três, sempre com o tipo de critério, e a tela diz "sem comparações
   suficientes" no lugar de "sem classificação" e de "não calibrado".
3. **Calibração por porte e intervalo:** possível em jun/2024 em todas as células (seção 4); nas primeiras competências,
   "não calibrado". A crítica do indicador 7 fica "não calibrável" enquanto não houver casos para estimar a cauda (seção 4.2).
   **Desde 13/11/2026** (Proposta V3): com as faixas acima de 300 separadas, o crítico fica "sem comparações suficientes" de
   3.000 médicos para cima (a base não tem 999 comparações de tamanho parecido); o crítico do sinal 7 passa a valer onde há 999
   comparações (0,04% das avaliações, para uma meta de 0,1%).
4. **População comparável:** só nos trechos da seção 6; fora deles, os indicadores 8 e 9 ficam "comparação não habilitada".
   **Implementado em 11/11/2026** (etapa 5 do comando V22): a janela de 2 anos só é habilitada inteira dentro de um trecho
   de população comparável; por decisão conservadora, a mesma regra vale para a variação do indicador 10, e o nível da data
   (taxa, percentil e índice) continua à vista ([Detector de Sinais](DETECTOR_DE_SINAIS.md)). **Desde 13/11/2026** (comando
   V23), os trechos vêm da própria base, e não de anos fixos; com a população nova, é um trecho só (2014–2024).
5. **Estados como unidade e conjuntos:** sem calibração própria (a da V2.2 é municipal); o Detector mostra os fatos e os
   indicadores descritivos, sem intensidade calibrada. **Desde 13/11/2026** (Proposta V3): os estados como unidade têm régua
   própria, com a base dos estados (moderado desde jun/2015, elevado desde jun/2019 e crítico nunca: em jun/2024 há 270
   comparações, e o crítico pede 999); os conjuntos continuam sem nível, com os fatos e o motivo.
6. **Faixas de 80% do Simulador:** a tabela da seção 11.2 do anexo traz valores iniciais, a recalcular na base (retroprojeções
   com origens móveis) antes de exibir; sem o recálculo, "indisponível".
7. **"Simular recuperação"** (meta = patamar do indicador 7, por planejamento inverso; etapa 5). **Resolvido em 10/11/2026**
   (decisão D-B do [anexo](DETECTOR_E_SIMULADOR_V2_2.md)): a meta é hipótese editável ("meta hipotética: voltar ao patamar de
   X médicos"), com o texto fixo de cenário e sem palavras de recomendação.

## 9. O perfil que o Agente lê (qualquer base)

Desde o comando V23 (14/11/2026; Proposta V3, seção A.3), o que as seções acima registram à mão para a base do Brasil é **lido
pelo próprio Agente**, antes das ferramentas, em qualquer base: a do Brasil ou uma planilha enviada. O perfil sai do motor
(`backend/perfil_da_base.py`, por `POST /api/detector` com `{"perfil": true}`), sem o provedor de IA, e a tela o mostra antes da
ferramenta (`frontend/src/PerfilDaBase.tsx`): aberto numa planilha, que é uma base nova; fechado na base do Brasil, até a pessoa
pedir.

| O quê | Como o Agente lê | Se faltar |
|---|---|---|
| Datas e intervalos | Mede os meses entre registros e só compara mudanças com o mesmo tempo entre eles; durações com até 1 mês de diferença ficam juntas | — |
| Série anual | O mês presente em todos os anos (o mês do último registro, quando ele se repete em todos); numa planilha só com anos, um registro por ano | Ficam indisponíveis os sinais anuais (3, 4 e 8 a 10) |
| Portes | As 10 faixas pelo número de profissionais, no último registro de cada território; faltando casos, a faixa junta-se às vizinhas | — |
| Grupo de cima | Na base do Brasil, o estado (pelo prefixo do código IBGE); numa planilha, a coluna de grupo escolhida | O sinal 10 fica indisponível |
| População | Os trechos de população comparável, lidos da própria base | Ficam indisponíveis os sinais 8 a 11 |
| Coordenadas | Com o referencial informado (na base do Brasil, SIRGAS 2000, do perfil oficial) | O sinal 11 fica indisponível |
| O que a contagem conta | A unidade de contagem informada, como nas análises: pessoas, vínculos, postos ou outra | Aviso de dupla contagem |
| Nomes | Os do painel "Colunas" (a unidade, o grupo e o todo), com a concordância | — |

O resumo **"com esta base, dá para… / não dá para… (motivo)"** vem da régua do Detector: desde que data a maioria dos territórios
com registro pôde ser comparada em cada nível (19, 99 e 999 comparações, com a retaguarda das faixas vizinhas e, só no moderado,
de todas as faixas) e, do que a base não sustenta, quantas comparações ela tem e quantas o nível pede. As linhas do Simulador de
Cenários (a retroprojeção e as faixas) entram no perfil quando o Simulador ganhar a mesma estrutura (Parte C da Proposta V3).

**Base do Brasil** (5.570 municípios, 22 registros, de jan/2014 a jun/2024; 5 ou 7 meses entre eles; a série anual é a de junho):

- Dá para:
  - alertas moderados, elevados e críticos nos municípios desde jun/2015 (o 2º ano da base); no último registro, 43 de 5.570
    municípios ficam sem comparações suficientes para o crítico (os de 3.000 médicos ou mais);
  - sinais por habitante (8 a 10), de 2014 a 2024, e a distância (sinal 11, só contexto);
  - alertas moderados nos estados como unidade desde jun/2015 e elevados desde jun/2019;
  - sinais anuais (declínio persistente e desaceleração), pela série de junho.
- Não dá para:
  - alertas críticos nos estados como unidade: eles pedem 999 comparações, e esta base chega a 270.

**Planilha de teste** (`backend/tests/planilha_das_ferramentas.csv`: 20 distritos fictícios, registros de seis em seis meses
durante 10 anos, de jan/2014 a jul/2023, sem grupo de cima, sem população e sem coordenadas; a série anual é a de julho):

- Dá para:
  - alertas moderados desde jan/2015 (o 2º ano da base);
  - alertas elevados desde jan/2018 (o 5º ano da base);
  - sinais anuais (declínio persistente e desaceleração), pela série de julho.
- Não dá para:
  - alertas críticos: eles pedem 999 comparações, e esta base chega a 360;
  - "Mais longe da referência" (sinal 10): a base não tem grupo de cima;
  - sinais por habitante (8 a 11): a base não tem população.

Com essa planilha, o Detector mostra, em jul/2023, 1 território em elevado, 4 em moderado e 15 sem alerta; os sinais 8 a 11
aparecem como "Indisponível nesta base", com o motivo, e a queda recente diz "Sem comparações suficientes para o crítico: há 360,
e ele pede 999."
