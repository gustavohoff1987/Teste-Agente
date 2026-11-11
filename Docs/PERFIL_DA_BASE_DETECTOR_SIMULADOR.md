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
  alcançá-los (só transições anteriores, sem dados futuros).
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

- **Janeiro igual a junho** no mesmo ano, em praticamente todos os municípios (99,8% a 100%).
- **Muda todo ano de 2014 a 2021**; de 2017 para 2018 a mudança total é pequena (+0,40%), com quase todos os municípios
  revistos; **2021, 2022 e 2023 são idênticas** (213.318.141 habitantes); **2024 é uma base nova** (212.583.750, −0,34%).
- **Consequência:** os trechos com população comparável são 2014–2017 e 2018–2021, como diz o anexo (indicadores 8 e 9); uma
  janela que cruze 2023 → 2024 recebe "comparação não habilitada". Nenhum município tem população ausente ou zero.

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
   "sem classificação" (com o motivo) onde faltar calibração.
3. **Calibração por porte e intervalo:** possível em jun/2024 em todas as células (seção 4); nas primeiras competências,
   "não calibrado". A crítica do indicador 7 fica "não calibrável" enquanto não houver casos para estimar a cauda (seção 4.2).
4. **População comparável:** só nos trechos da seção 6; fora deles, os indicadores 8 e 9 ficam "comparação não habilitada".
   **Implementado em 11/11/2026** (etapa 5 do comando): a janela de 2 anos só é habilitada inteira dentro de 2014–2017 ou de
   2018–2021; por decisão conservadora, a mesma regra vale para a variação do indicador 10, e o nível da data (taxa, percentil
   e índice) continua à vista ([Detector de Sinais](DETECTOR_DE_SINAIS.md)).
5. **Estados como unidade e conjuntos:** sem calibração própria (a da V2.2 é municipal); o Detector mostra os fatos e os
   indicadores descritivos, sem intensidade calibrada.
6. **Faixas de 80% do Simulador:** a tabela da seção 11.2 do anexo traz valores iniciais, a recalcular na base (retroprojeções
   com origens móveis) antes de exibir; sem o recálculo, "indisponível".
7. **"Simular recuperação"** (meta = patamar do indicador 7, por planejamento inverso; etapa 5). **Resolvido em 10/11/2026**
   (decisão D-B do [anexo](DETECTOR_E_SIMULADOR_V2_2.md)): a meta é hipótese editável ("meta hipotética: voltar ao patamar de
   X médicos"), com o texto fixo de cenário e sem palavras de recomendação.
