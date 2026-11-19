# Simulador de Cenários Territoriais

Ferramenta do comando V22 (Eixo II, etapas 4 e 5: o núcleo, de 10/11/2026; e as referências, o planejamento inverso e a ligação
com o Detector, de 11/11/2026), refeita pela [Proposta V3](DETECTOR_E_SIMULADOR_V3.md) (comando V23, Parte C, de 14/11/2026): o
modo simples numa tela só, a forma de projetar escolhida pela própria base, a faixa "8 em cada 10" conferida no tempo e o uso com
qualquer base (a do Brasil ou uma planilha enviada). No que a Proposta V3 não muda (as fórmulas dos métodos, as intervenções, as
referências e o planejamento inverso), a referência continua sendo [Detector e Simulador V2.2](DETECTOR_E_SIMULADOR_V2_2.md)
(seções 2.5, 8, 8.8, que prevalece, 9 e 10, com as decisões D-A a D-C de 10/11/2026); onde as duas divergem, vale a V3. O perfil
da base está em [Perfil da base](PERFIL_DA_BASE_DETECTOR_SIMULADOR.md). Este documento descreve o que o sistema faz hoje.

## O que é

O Simulador mostra, para os territórios escolhidos, **cenários hipotéticos e condicionais**: quantos profissionais o território
teria numa data final, dada uma forma de projetar a base do cenário e as intervenções que a pessoa declarar. Nenhum resultado é previsão,
observação atual, conclusão sobre o atendimento ou recomendação de provimento.

O Simulador é a **exceção aprovada** à exclusão de projeção da SPEC ("projeção ou previsão (Caso 4)" fora da FAM-08; critério
AT-04), decidida pelo responsável em 9/11/2026 (decisão 2 do comando V22; seção 2.5 do anexo) e restrita a esta ferramenta
determinística. Fora dela nada muda: o assistente de conversa continua recusando pedidos livres de projeção ou previsão, e a guarda
de fidelidade continua recusando previsões em qualquer outro texto. A SPEC não foi editada.

O Simulador calcula no motor (`backend/simulador.py`, sobre `backend/series_brasil.py` e a calibração de `backend/detector.py`),
sem o provedor de IA, e funciona com ele indisponível. Vale para **qualquer base** desde o comando V23: a do Brasil (médicos,
registros de janeiro e junho de 2014 a 2024) ou uma planilha enviada, com os nomes, o mês da série anual e o grupo de cima lidos
dela (seção "Qualquer base"). Os exemplos deste documento usam os nomes da base do Brasil.

Três coisas ficam sempre separadas, no cálculo e na tela:

1. **o observado:** os registros reais, só nas datas com registro (linha contínua e marcadores);
2. **a base do cenário:** o que o método escolhido dá para as datas depois da origem (linha tracejada);
3. **a intervenção:** os acréscimos e as retiradas declarados pela pessoa, somados à base, com um marcador em cada evento.

## Na tela

- **Onde:** o botão **Simulador de Cenários** (`analise-ferramenta-simulador`), na linha "Ferramentas" da navegação principal, ao
  lado do Detector de Sinais. A ferramenta abre no lugar do painel da aba e do desenho da análise (`area-de-analise` leva
  `data-ferramenta="simulador"`), depois do perfil da base (fechado, até a pessoa pedir). A seleção local e os cenários ficam
  guardados enquanto a fonte de dados for a mesma: sair da ferramenta e voltar não os perde.
- **Título e "(Entenda)"** (`simulador-entenda-ferramenta`; desde 15/11/2026, etapa 7 do comando V23): ao lado do título, como
  no Detector de Sinais, o "(Entenda)" geral traz três frases simples e um exemplo, com o nome que a base dá à contagem —
  "Mostra para onde o território iria se continuasse como vinha, e o efeito das mudanças que você quer testar. O “como vinha” e
  a margem de erro vêm da própria base: o Agente refaz no passado a projeção que teria feito e confere com o que aconteceu
  depois. Todo resultado é um cenário hipotético, nunca uma previsão." (o exemplo usa números ilustrativos e diz isso). "Ver
  explicação completa" abre a ficha metodológica em PDF, numa nova aba (desde 18/11/2026, AJ-03; antes, depois de um cálculo,
  "Como os métodos se saíram no passado").
- **Ficha metodológica (PDF) e a avaliação dos métodos** (desde 18/11/2026, AJ-03), no alto, nos dois modos, ao lado de
  "Exportar o cenário (JSON)" e "Importar cenário (JSON)":
  - **"Ficha metodológica (PDF)"** (`simulador-ficha`) abre numa nova aba a **Ficha B** (fonte em
    [`Docs/fichas/ficha_simulador.html`](fichas/ficha_simulador.html); o PDF, `frontend/public/fichas/ficha-simulador.pdf`, sai
    com os arquivos estáticos da interface, e o link respeita a base da página, `ADT_BASE_DA_PAGINA`): os modos, cada forma de
    projetar (M0, M0d, M0g, M1, M2 e M3), as premissas, as intervenções, a meta, as referências, os conjuntos, o Brasil como
    território, a hipótese do cenário, os avisos de horizonte, os limites e a avaliação dos métodos no histórico da base, com
    os números da base do Brasil. Desde 18/11/2026 (AJ-06, comando de correção das fichas), ela é **só metodológica, para quem
    usa o Agente**: abre com uma **leitura rápida** (o que o Simulador faz, como ler o resultado e o que ele não diz), traz a
    versão do método na abertura e deixou de fora o bastidor do desenvolvimento (as marcas de estado, os caminhos de arquivo, as
    rotas e os campos da API, os códigos da SPEC, das decisões e dos avisos, os hashes, as exportações e as versões), que
    continua neste documento. A letra é a Inter estática das fichas (`Docs/fichas/fontes/`), embutida como TrueType;
  - **"Exportar a avaliação dos métodos (JSON)"** (`simulador-exportar-avaliacao`; desligado até haver um cálculo; arquivo
    `simulador_avaliacao_dos_metodos_<último registro>.json`) leva a retroprojeção da base em uso **tal como o motor a mandou**
    (`retroprojecao`: a escolha de cada nível, com os candidatos e os erros, as faixas por porte e prazo e a tabela dos erros de
    cada método), com a versão do método e a da base, o último registro, a janela, as notas e as limitações. É a avaliação dos
    métodos no histórico da base, e não uma análise do território escolhido; o conteúdo dela saiu da tela com "Como os métodos se
    saíram no passado".
- **"Voltar ao padrão"** (`simulador-voltar-ao-padrao`; desde 15/11/2026): **um botão só**, sempre à vista nos dois modos, ao
  lado dos botões de modo. Devolve de uma vez todas as premissas ao padrão — a forma de projetar e a janela que a base escolheu
  (também a janela trazida do Detector de Sinais), a faixa de 8 em cada 10, a permanência total e a comparação pela diferença — e
  fica desligado enquanto elas são as do padrão. O território, o que testar (as quantidades, as datas e a meta), a data final e
  as referências não são premissas: ficam como estão. Os atalhos de volta de antes ("Janela padrão (3 anos)", na etapa 2, e
  "Voltar ao jeito escolhido pela base", no aviso do modo simples) saíram.
- **A data, sempre à vista** (`simulador-data`): "O registro mais recente da base é jun/2024 (há … anos e … meses): é histórico.
  Tudo o que vem depois dele é simulado, nunca observado". A distância até hoje usa a data do aparelho.
- **Nada é calculado sem comando:** o motor só é chamado por "Calcular" (no modo avançado, "Calcular os cenários" ou "Calcular com
  o que está escolhido"). Depois de uma mudança nas escolhas, os resultados à vista ficam marcados como desatualizados, com
  "Calcular de novo".
- **Dois modos** (`simulador-modo-simples` e `simulador-modo-avancado`; a seção leva `data-modo`): o Simulador abre no **modo
  simples**, numa tela só; o **modo avançado** guarda as quatro etapas de antes. A configuração é a mesma nos dois: trocar de modo
  não perde o que foi escolhido. A persistência entra sempre no pedido como referência de comparação. **O pedido do modo simples
  não leva o que só o modo avançado escolhe:** a janela geral, as referências de comparação, o calendário dos acréscimos, a
  permanência e as outras intervenções ficam guardados e voltam a valer no modo avançado. O pedido leva o que a tela simples
  mostra: o que testar, com uma quantidade (ou uma meta) e uma data, com permanência total. Da janela, vai só aquela com que o
  Detector de Sinais abriu o Simulador, quando a pessoa a escolheu lá. Uma referência incompleta ou um calendário incompleto do
  modo avançado não impedem o cálculo no modo simples. A meta por
  referência é do modo avançado: no modo simples, a tela pede um número ("No modo simples, a meta é um número: informe a meta em
  “O que testar”.").

### Modo simples (uma tela só)

`simulador-simples`, como no esboço da seção C.7 da Proposta V3:

- **Território** (`simulador-territorio`): um território por vez, entre os da seleção local (a cópia da seleção principal; ver a
  etapa 1 do modo avançado). Sem escolha, o primeiro. O pedido leva só esse território. **Trocar o território tira a meta** de
  "Chegar a uma meta": ela era do território de antes (o patamar dele, ou um número pensado para ele). O campo fica em branco, à
  espera de outra, e a data do acréscimo continua. **O resultado anterior também sai da tela** (desde 15/11/2026): ele era do
  outro território, e o aviso "As escolhas mudaram depois deste cálculo" fica só para as mudanças feitas no mesmo território.
- **O que testar** (`simulador-o-que-testar`), uma opção de cada vez:
  - "Só continuar como vinha" (`simulador-teste-continuar`): sem intervenção;
  - "Acrescentar" e "Retirar" (`simulador-teste-acrescentar`, `simulador-teste-retirar`): a frase "Acrescentar [N] médicos em
    [data]" (`simulador-frase-do-teste`, com `simulador-teste-quantidade` e `simulador-teste-em`), uma intervenção numa data, com
    permanência total. O nome concorda com o número digitado ("Acrescentar 1 médico", "5 médicos"). A frase diz que é uma
    hipótese da pessoa e que o crescimento histórico não é aplicado a quem entra;
  - "Chegar a uma meta" (`simulador-teste-meta`; o valor, em `simulador-teste-meta-valor`): "Chegar a [meta] médicos na data
    final, com um acréscimo em [data]" — o
    planejamento inverso com um acréscimo numa data. A meta é uma hipótese da pessoa (ou o patamar anterior, quando o Simulador é
    aberto por "Simular recuperação"), e o Agente calcula quantos faltariam, com o menor número inteiro. A meta que vem do
    Detector é um **número inteiro**: o patamar, que é uma média e pode ter decimal, arredondado para cima (79 médicos para um
    patamar de 78,25), para o resultado do cenário não parecer abaixo da meta. A frase ao lado do campo diz de onde ela veio
    (`simulador-teste-meta-origem`: "A meta veio do Detector de Sinais: o patamar anterior, de 78,25 médicos (a maior média de
    dois anos seguidos), arredondado para cima. É uma hipótese que você pode trocar."). Digitar outro número troca a meta por um
    número da pessoa ("A meta é uma hipótese sua.").

  Trocar de opção volta à forma de projetar escolhida pela base; a quantidade, a meta e a data digitadas ficam. Quando o
  cenário traz uma forma de projetar escolhida no modo avançado, o modo simples avisa (`simulador-metodo-do-avancado`) e diz que
  "Voltar ao padrão", no alto, desfaz essa escolha. A faixa escolhida no modo avançado (5 ou 9 em cada 10) também vale no modo
  simples, e, desde 18/11/2026 (AJ-17), o modo simples avisa logo depois, no mesmo estilo (`simulador-faixa-do-avancado`): "Este
  cenário usa a faixa de 9 em cada 10, escolhida no modo avançado, e não a de 8 em cada 10. “Voltar ao padrão”, no alto, desfaz
  essa escolha." Com a de 8, sem aviso; com a forma e a faixa trocadas, os dois avisos. O pedido é o de antes: a faixa vai nos
  dois modos, e "Voltar ao padrão" devolve a de 8. Antes do primeiro cálculo com uma planilha, as frases já usam o nome da contagem dela:
  o nome dos trabalhadores informado no envio ("Acrescentar … enfermeiros"), quando ele serve aos textos, ou "profissionais",
  "vínculos" ou "postos" (`simuladorModel.nomeDosTrabalhadores`, a mesma regra do motor).
- **Até quando** (`simulador-horizonte`): qualquer mês depois do último registro; os atalhos de 1, 2 e 4 anos
  (`simulador-atalho-1`, `-2`, `-4`) são só atalhos.
- **Calcular** (`simulador-calcular`). O resultado (`simulador-resultado`, com `data-estado`, `data-metodo`, `data-faixa` e
  `data-conferencia`) traz, nesta ordem:
  - o **gráfico** (`simulador-grafico`): o observado, a base do cenário, a linha com a intervenção e os marcadores dos eventos, a
    faixa quando existe ("banda: faixa de 8 em cada 10"), a fronteira "observado | simulado (hipótese)" e a fonte
    (`simulador-grafico-fonte`), com os nomes da base em uso. O gráfico é **desenhado na largura que tem na tela**
    (`data-largura`; desde 15/11/2026), em vez de ser encolhido: o texto dos eixos mantém 12 px também no celular, onde o
    gráfico fica mais alto (340 px, em vez de 300), mostra menos anos no eixo e escreve só "simulado" (ou nada) quando o
    trecho simulado é curto. Em "Chegar a uma meta" (`simulador-plano-no-grafico`), o desenho
    mostra também **a meta** (uma linha pontilhada na altura dela, com "meta: N"; `simulador-meta-linha`), **o caminho do cenário
    com o acréscimo** calculado (linha contínua, `simulador-plano-curva`) e **a marca na data de cada acréscimo**
    (`simulador-plano-evento`); a legenda diz o que é cada um (`simulador-meta-legenda`). Quando o cenário já chega à meta, fica
    só a linha dela ("o cenário já chega a ela, sem acréscimo");
  - a **frase fixa** do cenário (`simulador-texto`), que vem pronta do motor;
  - **três números** (`simulador-tres-numeros`): no último registro, na data final e a diferença (na meta, "precisaria
    acrescentar N" ou "nada a acrescentar");
  - a **forma de projetar** em uso, com a marca "(escolhida pela base)" quando é o caso, e o estado da **faixa**
    (`simulador-faixa-estado`: "Faixa de 8 em cada 10: conferida", "provisória" ou "indisponível"), cada um com o seu **"Entenda"**
    (`simulador-entenda-jeito`, `simulador-entenda-faixa`): duas ou três frases simples e um exemplo com os números do cenário,
    que vêm do motor. "Ver explicação completa" abre a seção da ficha metodológica (a forma escolhida e a faixa), numa nova aba;
  - a faixa em palavras (`simulador-faixa-texto`), o resultado da meta (`simulador-planejamento`), a hipótese do cenário
    (`simulador-hipotetico`) e os avisos (`simulador-avisos`), quando há;
  - até 18/11/2026, também "Como os métodos se saíram no passado" (`simulador-validacao`, com a frase da escolha de cada nível,
    o erro de cada candidato e as notas) e a linha das versões (`simulador-versoes`): desde o AJ-03, o conteúdo delas está na
    ficha e em "Exportar a avaliação dos métodos (JSON)", e as versões, nas exportações. O último registro da base continua no
    aviso do alto da página.
- **"Avançado ▸"** (`simulador-avancado`) leva às quatro etapas, com o que elas têm a mais (seção C.8): vários cenários, outras
  formas de projetar e outras janelas, referências, calendário de acréscimos e permanência, conjuntos e vários territórios,
  exportar e importar.

### Modo avançado: as quatro etapas

As quatro etapas aparecem só no modo avançado: até 5 cenários, cada um com nome, método, janela própria e intervenções. Valem
também com uma planilha enviada, com os nomes dela (seção "Qualquer base"); os exemplos abaixo usam os nomes da base do Brasil.

**As premissas ficam em frases, com os campos dentro delas** (Proposta V3, seção C.5; completa desde 15/11/2026, etapa 7 do
comando V23), como os critérios do Detector:

- a janela (`simulador-frase-da-janela`): "Janela histórica: o crescimento é medido em [3 anos (desde jun/2021)] antes de
  [jun/2024], a origem do cenário.";
- a forma de projetar de cada cenário (`simulador-frase-do-jeito`): "Forma de projetar: [Continuar como vinha (a forma
  escolhida pela base)], com [a janela geral]." — com a taxa da pessoa, "…, de [x]% ao ano (uma hipótese sua)"; com uma janela
  própria, "…, com [uma janela própria, desde jun/2019] até [jun/2024].";
- a faixa (`simulador-faixa-em-10`): "Mostrar a faixa onde o valor real ficou em [8] de cada 10 retroprojeções de territórios
  do mesmo porte.";
- a permanência de cada intervenção (`simulador-frase-da-permanencia`) e do planejamento inverso
  (`simulador-frase-da-permanencia-do-plano`): "Dos médicos acrescentados, a cada ano permanecem [100]%." (numa retirada, "Do
  efeito da retirada, a cada ano permanecem [100]%.");
- a comparação com as referências (`simulador-frase-da-comparacao`): "Comparar cada cenário com as referências por [diferença
  (em médicos) / razão (quantas vezes o valor da referência) / taxa por 1.000 habitantes]" e, na taxa, ", com a população [igual
  à do último registro (jun/2024) / crescendo] [x]% ao ano depois dele (uma hipótese sua).".

Os campos mantêm os identificadores de antes (`simulador-janela-inicio`, `simulador-janela-fim`, `simulador-metodo`,
`simulador-taxa-manual`, `simulador-cenario-janela-inicio`, `simulador-cenario-janela-fim`, `simulador-intervencao-permanencia`,
`simulador-plano-permanencia` e `simulador-metrica`); os novos são `simulador-populacao` e `simulador-populacao-pct`.

1. **Territórios em análise** (`simulador-territorios`): a **seleção local** do Simulador.
   - Ela nasce como **cópia da seleção principal**: os municípios um a um, os estados como unidade e os conjuntos, com o nome, a
     composição e a versão. "Ver a composição dos conjuntos" lista os componentes de cada conjunto.
   - Enquanto não for alterada no Simulador, a cópia **acompanha** a seleção principal. Depois da primeira alteração feita aqui (ou
     de um cenário importado), ela é só do Simulador e só muda aqui dentro ou por "Copiar de novo a seleção principal". A tela diz
     isso **numa mensagem só**, no alto da etapa (`simulador-origem-da-selecao`; desde 15/11/2026, sem o segundo aviso, que
     repetia a frase de cima): enquanto a cópia acompanha a seleção principal, é uma frase de apoio; quando deixa de acompanhar,
     a própria frase vira o aviso, com o trecho `simulador-nao-acompanha` ("a cópia **deixou de acompanhar** a seleção principal
     … O que mudar na Seleção de Territórios não chega mais ao Simulador … “Copiar de novo a seleção principal” traz a seleção
     principal de volta").
   - A busca acrescenta um município, um estado como unidade ou **o Brasil** **só no Simulador**; o "×" de cada território o
     tira. O estado inteiro e os municípios dele não entram juntos, como na Seleção de Territórios (RQ-DAD-30): a tela recusa,
     com o motivo. O Brasil é a contagem nacional de médicos únicos: é simulado à parte e nunca é somado aos demais.
   - **"Aplicar à seleção principal"** é o único caminho pelo qual o Simulador muda a seleção principal. É um comando separado e
     um passo do Desfazer. O Brasil não vai (a seleção principal não o tem como unidade), e a tela diz isso.
   - O Simulador compara até **100 territórios** de cada vez; acima disso, a tela pede para reduzir a seleção local.
   - **Referências de comparação (opcional)** (`simulador-referencias`): até 5. Uma referência é um município, um estado como
     unidade, o Brasil, um conjunto da seleção local ou **um valor da pessoa**; pode ficar fora da seleção do Simulador e não
     muda a seleção principal. Cada uma é **fixa** (o último valor registrado se mantém) ou **dinâmica** (segue a forma de
     projetar que a base escolheu para o nível dela, sem intervenções). A forma de comparar é escolhida à vista, na frase da
     comparação (`simulador-metrica`): pela **diferença** em médicos (o padrão), pela **razão** (quantas vezes o valor da
     referência) ou pela **taxa por 1.000 habitantes**. Na taxa, a população é **igual à do último registro** (o padrão, como
     hipótese declarada) ou **cresce x% ao ano depois dele** (`simulador-populacao` e `simulador-populacao-pct`), uma hipótese
     da pessoa: de −20% a +20% ao ano, a mesma taxa no território e na referência; sem o número, a tela diz o que falta e não
     pede nada ao motor.
   - Quando o Simulador é aberto pelo **Detector de Sinais** ("Abrir no Simulador" ou "Simular recuperação"), a seleção local
     fica só com aquele território e não acompanha a principal; o aviso `simulador-do-detector` diz de onde ela veio, a data
     avaliada e os sinais com nível lá ("Sinais com nível lá: Queda recente (elevado)"), e pode ser dispensado.
2. **Base histórica e método** (`simulador-base`):
   - a **janela histórica**, em frase, com início e fim livres entre as competências reais (o fim é a origem do cenário): a
     lista do início mostra quanto tempo antes da origem cada registro fica ("3 anos (desde jun/2021)", "10 anos e 5 meses (desde
     jan/2014)"). Os atalhos (últimos 5 anos e série completa) são só atalhos. A janela igual à que a base escolheu vale como o
     padrão (`data-padrao="true"` na frase), e a volta a ela é pelo "Voltar ao padrão". Sem janela escolhida, a frase mostra a
     janela padrão, que é a do próximo cálculo, mesmo quando o cálculo à vista foi feito com outra. Com a origem antes do último registro, o
     trecho até ele é **retroprojeção**, ao lado do observado;
   - a **forma de projetar** de cada cenário (o método da base do cenário, lista abaixo), em frase, com uma explicação simples
     de cada um. "Continuar como vinha (a forma escolhida pela base)" é o padrão; os demais ficam à escolha da pessoa. Cada
     cenário pode ter a sua janela;
   - as **estatísticas históricas** do território (depois do primeiro cálculo): registros usáveis, lacunas, taxas de junho a junho,
     taxa composta, média aritmética, mediana e dispersão. A média aritmética é **só descrição do passado**.
3. **Intervenções e horizonte** (`simulador-intervencoes-etapa`):
   - a **data final**, em qualquer mês depois do último registro; os atalhos de 1, 2, 4 e 10 anos são só atalhos, nunca limites;
   - a **faixa a mostrar** (`simulador-faixa-em-10`; seção C.5): "Mostrar a faixa onde o valor real ficou em [8] de cada 10
     retroprojeções de territórios do mesmo porte", com as opções 5, 8 (o padrão) e 9. A frase lembra que a faixa só existe para a
     forma de projetar e a janela que a própria base escolheu, até o maior prazo com casos suficientes;
   - as **intervenções hipotéticas** de cada cenário: acréscimo ou retirada de X médicos, numa data ou num calendário (a cada
     tantos meses, de uma data a outra), com a **permanência** em frase, em % ao ano (100, todos ficam, é a hipótese padrão);
   - o aviso de que cada intervenção vale para **cada território** do cenário, não para o total (`simulador-por-territorio`):
     com 49 territórios, um acréscimo de 5 médicos soma 5 a cada um deles, inclusive aos estados como unidade e aos conjuntos;
   - o **planejamento inverso** de cada cenário (`simulador-plano`, por "Calcular o acréscimo que alcança uma meta"): a **meta
     hipotética** (chegar a um número de médicos, voltar ao patamar anterior ou alcançar uma referência) e o calendário dos
     acréscimos (uma data, ou de uma data a outra a cada tantos meses, com a permanência). A meta é uma hipótese da pessoa, e ela
     pode trocá-la. Em "Simular recuperação", o Simulador abre nesta etapa, com a meta de voltar ao patamar já preenchida.
4. **Comparações e resultados** (`simulador-resultados`):
   - o **gráfico** de um território por vez (`simulador-grafico`): o observado, a base de cada cenário, a linha com a intervenção
     e os marcadores dos eventos, a faixa quando existe, a fronteira "observado | simulado (hipótese)" e a fonte;
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
     médicos" (sinais 1 e 2 do Detector, de limite fixo), por exemplo "o território seria Crítico em “Poucos médicos”"; quando a
     faixa cruza um limite, "pode ficar entre elevado e crítico", sem escolher um só. Só para municípios, e só quando é pertinente
     (há nível no valor do cenário ou num dos limites da faixa, ou o território teria até 20 médicos);
   - a **tabela** de todos os territórios (`simulador-tabela`): o último registro usável e, por cenário, o valor na data final, a
     faixa e o método usado em palavras. Num **conjunto**, o método aparece como "soma das projeções dos membros (cada um com o
     crescimento do seu estado)" (ou "cada um no último valor", na persistência; nos demais métodos, "soma das contagens dos
     componentes · …"), e a faixa leva o rótulo "**aproximação**" na tabela, no texto da faixa e na legenda do gráfico;
   - a **janela deste cálculo** (`simulador-janela-do-calculo`, desde o AJ-03): "Janela deste cálculo: de jun/2021 a jun/2024 (a
     janela padrão). Cada cenário parte do último registro usável do território nessa janela." Até 18/11/2026, a janela ficava na
     linha das versões (`simulador-versoes`), e as faixas por porte e prazo e o erro de cada método frente à persistência, em
     "Como os métodos se saíram no passado" (`simulador-validacao`); desde o AJ-03, os dois saíram da tela, e esses números vão
     em "Exportar a avaliação dos métodos (JSON)".

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

> Meta hipotética: [voltar ao patamar de X médicos em [data] (patamar de X,XX, média de N registros, arredondado para cima) | X
> médicos | alcançar a referência …] em [data]. Menor acréscimo inteiro que
> alcança a meta, nas hipóteses deste cenário: [x] médicos [em … | em cada um dos k eventos, de … a … (total)]. Pela conta sem
> arredondar, seriam [x,xx] por evento. [O texto do cenário com esse acréscimo.] É uma conta condicional às hipóteses do
> cenário, não um plano.

Nenhum deles usa palavras de recomendação ("recomenda-se", "é preciso prover", "deveria"): decisão D-B de 10/11/2026.

Numa planilha enviada, "médicos" dá lugar ao nome da contagem dela — o nome dos trabalhadores informado no envio ("enfermeiros"),
quando ele é um plural que os textos podem usar, ou "profissionais", "vínculos" ou "postos" —, e o nome do grupo de cima e o do
todo vêm do painel "Colunas". Uma janela com um registro só (numa base com registros espaçados) aparece nas premissas como
"janela com um registro só (jun/2024)", e não "janela de jun/2024 a jun/2024".

A tela e os textos de cenário usam linguagem simples (decisão D-C): "continuar como vinha", "faixa provisória", "sem intervenção",
"indisponível", com o motivo. A **deriva do estado** do M0d aparece como "o crescimento recente do estado" (o método, como
"persistência com o crescimento recente do estado"), e a retroprojeção, como o cenário "calculado sobre datas que já têm
registro". Os códigos dos métodos (M0, M0d, M0g, M1, M2, M3) e os termos técnicos ficam na lista de métodos do modo avançado, na
ficha metodológica (PDF), neste documento e nas exportações.

Os **"Entenda"** do resultado (campo `entenda` de cada cenário calculado) também vêm prontos do motor, com os números do cenário
e da retroprojeção da própria base:

> **Forma de projetar:** O cenário parte do último registro usado (jun/2024) e soma o crescimento recente do estado: +3,06% ao
> ano nos 3 anos anteriores. Usamos esta forma porque, nesta base, ela errou menos que simplesmente manter o último valor, quando
> refeita no passado. *Exemplo:* De 52 médicos em jun/2024, a base do cenário vai a 53,6 um ano depois, sem contar intervenções.

> **Faixa:** Refizemos este tipo de projeção em datas passadas, para territórios do mesmo porte. Em 8 de cada 10 vezes, o valor
> real ficou dentro desta faixa. Não é garantia: o passado testado (2017–2024) pode não se repetir. *Exemplo:* Entre 44 e 68
> médicos na data final.

(Os números dos dois exemplos são ilustrativos.) Sem faixa, o "Entenda" traz o motivo e a frase "Sem a faixa, o cenário mostra
só a linha: ela não diz quanto o valor real costuma se afastar." Numa faixa provisória, acrescenta "Faixa provisória: ainda não
deu para conferi-la com dados que vieram depois, ou a conferência ficou um pouco abaixo do esperado."

## O que é calculado

A base e a intervenção ficam separadas (seção 9 do anexo):

    N(t) = máx(0, B(t) + I(t))        I(t) = Σ a_j · S(t − t_j),   S(u) = 0 para u < 0

com `t` em **anos reais** desde a origem (o último registro usável da janela; entre os registros há 5 e 7 meses, não meio ano).

### Métodos da base do cenário

| Método | Regra | Quando não vale |
|---|---|---|
| **Continuar como vinha (padrão)** | A forma de projetar que **a própria base escolheu** para o nível do território, pela retroprojeção (regra abaixo). Na base do Brasil: municípios e conjuntos de municípios, M0d; estados como unidade e conjuntos de estados, M1 nos 3 anos até a origem | sem retroprojeção bastante, ou quando nenhuma forma errou menos que manter o último valor: vale o M0, com aviso. Também volta ao M0, com aviso, quando a forma escolhida não se aplica ao território (sem o crescimento do grupo ou da base; ou, na taxa composta, sem o registro de 3 anos antes ou com o início ou o fim em zero) |
| **M0, persistência** | `B(t) = N0`: o último valor se mantém. É a referência de comparação, sempre calculada | sem registro usável na janela |
| **M0d, persistência com o crescimento recente do grupo de cima** | `B(t) = N0 × (1 + g)^t`, com `g` = o crescimento anual composto da soma das unidades do grupo de cima (na base do Brasil, o estado) nos 3 anos antes da origem. Zero continua zero | sem os 3 anos, com soma zero ou com quebra de fonte nesses 3 anos: **volta ao M0, com aviso**; não se aplica aos grupos como unidade nem a uma base sem grupo de cima |
| **M0g, persistência com o crescimento recente da base toda** (novo) | o mesmo, com a soma de todos os territórios do nível. É o candidato das bases sem grupo de cima | sem os 3 anos ou com soma zero: **volta ao M0, com aviso**; não se aplica ao todo (é a própria série dele) |
| **M1, taxa composta** | `r = (Nf/Ni)^(1/T) − 1`, com `T` real em anos; `B(t) = N0 × (1 + r)^t`. É o percentual médio que reproduz o crescimento ocorrido | menos de dois registros, ou o primeiro ou o último em zero: "não se aplica" (a taxa com início em zero não é definida) |
| **M2, tendência linear robusta (Theil–Sen)** | inclinação = mediana das inclinações entre os pares de registros; intercepto = mediana(y) − b · mediana(t). A diferença entre a tendência e o último registro fica à vista | menos de três registros; a base negativa para em zero, com aviso |
| **M3, tendência log-linear** | Poisson com ligação log (IRLS); a dispersão quase-Poisson é só diagnóstico | menos de três registros; série toda em zero: "não calculável" |
| **Taxa informada pela pessoa** | `B(t) = N0 × (1 + taxa)^t`, com a taxa anual digitada, rotulada como hipótese dela | sem a taxa, o cenário não é pedido. **O sistema nunca sugere uma taxa** |

**A regra de escolha** (Proposta V3, seção C.3), aplicada a cada nível de território (as unidades da base e, quando a base tem a
contagem própria deles, os grupos de cima como unidade), uma vez por versão da base:

1. Na retroprojeção da própria base, três candidatos são comparados com "manter o último valor": o crescimento do próprio
   território (M1), o do grupo de cima (M0d) e o da base toda (M0g). A medida é o erro absoluto médio; cada porte tem o mesmo
   peso, e os portes com menos de 30 casos juntam-se a um vizinho; entram todos os prazos, de 1 a 4 anos.
2. **Só vale** uma forma que errou menos que manter o último valor no total e em pelo menos metade das combinações de origem e
   prazo.
3. **Entre os que valem, fica o mais próximo do território** cujo erro esteja a até 5% do melhor, na ordem: o próprio
   território, o grupo de cima, a base toda.
4. **Exceção por porte:** se, num porte, o escolhido errou mais que manter o último valor em todos os prazos conferidos, os
   territórios desse porte usam o último valor, com aviso (`PORTE_USA_O_ULTIMO_VALOR`).
5. **Sem retroprojeção bastante** (menos de 3 origens com 3 anos antes e 1 ano depois, ou base sem série anual), ou quando
   **nenhum candidato vale**, o padrão é manter o último valor, com aviso (`SEM_RETROPROJECAO` ou `PADRAO_E_O_ULTIMO_VALOR`).

Na base do Brasil, a regra reproduz o padrão de antes: M0d nos municípios e M1 nos estados (tabelas em "Retroprojeção"). O
resultado da escolha vem na resposta (`retroprojecao.escolha` e `retroprojecao.niveis`), e cada cenário diz a forma escolhida
pela base e se é o que está em uso (`metodo.escolhido_pela_base`, `metodo.e_o_escolhido`).

- **O todo** (na base do Brasil, a contagem nacional) é uma série só e não tem retroprojeção própria: usa a forma escolhida para
  o nível de baixo (os grupos como unidade ou, sem eles, as unidades), marcado como provisório, com aviso
  (`PADRAO_PROVISORIO_DO_NIVEL`).
- **Janela padrão:** os 3 anos até o último registro, pelo tempo e não pela contagem de registros (na base do Brasil, 7
  registros; numa base com um registro por ano, 4; numa base com registros mais espaçados que isso, os dois últimos). No "continuar como vinha" com o M1, vale sempre a janela de 3 anos até a
  origem, como na retroprojeção.
- **Conjuntos:** no M0 e no M0d, a soma das projeções dos membros, cada um com o crescimento do seu grupo de cima (sem ele, o
  membro fica na persistência, com aviso). Nos demais métodos, o ajuste é feito na série da soma das contagens. Sempre com o
  rótulo.
- **Registros fora do ajuste:** o registro de um **pico que volta** e os registros de uma **quebra de fonte** (as marcas do
  Detector) não entram na base do cenário; a janela começa depois da quebra. A tela avisa.
- **Ausência de dado não é zero:** um registro ausente é lacuna; a origem é o último registro que existe na janela.
- **A média aritmética das taxas** nunca alimenta uma projeção, não é método, cenário nem sugestão de taxa.
- Comparar métodos e janelas é **sensibilidade a método e janela**, não faixa de confiança.
- No M1 pedido pela pessoa, a tela avisa quando, no porte do território, esse método errou mais que manter o último valor na
  retroprojeção da base (antes, o aviso valia para municípios com menos de 100 médicos; o código do aviso continua
  `M1_ABAIXO_DE_100`).

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

O Brasil entra só no Simulador, pela **contagem nacional de médicos únicos** (`brasil: true` no pedido; `id` "br"). O padrão é
provisório: a taxa composta (M1) dos 3 anos até a origem, na série nacional — a forma que a base escolheu para os estados —, com
aviso; não há faixa nem hipótese do cenário. O Brasil nunca é somado aos demais territórios, e não é uma unidade da seleção
principal nem do Detector. Numa planilha enviada, a rota aceita o todo (a soma das unidades com registro, com o nome que a pessoa
deu), com a forma escolhida para as unidades, como provisória — quando essa forma é o crescimento do grupo ou o da base toda,
vale a taxa composta da série dele, que é a própria base toda. Ele entra pela busca do modo avançado, pelo nome.

### Referências e comparação

- A referência **fixa** mantém o valor do último registro usável dela na janela. A **dinâmica** segue a forma de projetar que a
  base escolheu para o nível dela (na base do Brasil, municípios e conjuntos de municípios: a persistência com o crescimento
  recente do estado; estados e Brasil: a taxa composta de 3 anos), sem intervenções, com os avisos desse método. O **valor da pessoa** se mantém e é lido na métrica
  escolhida.
- Em cada data do cenário (a origem e as datas da trajetória), a comparação traz a **diferença** (referência − território), a
  **razão** (território ÷ referência) e o **índice** (100 × a razão). Nenhuma variação é chamada de "convergência".
- **A forma da comparação** (`comparacao.forma`; desde 15/11/2026): a frase de cada comparação destaca a **diferença** (o
  padrão: "28 abaixo da referência") ou a **razão** ("0,44 vezes o valor da referência"), sempre com o índice entre parênteses.
  Os três números de cada data são os mesmos nas duas formas. Diante de uma referência em zero, a razão não existe, e a frase
  diz isso ("a razão não pode ser calculada, porque a referência é zero").
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
- **População crescendo x% ao ano** (`comparacao.populacao_pct_ao_ano`; desde 15/11/2026, Proposta V3, seção C.5): em vez da
  população constante, a pessoa pode informar uma taxa de crescimento, de −20% a +20% ao ano (um número negativo é uma população
  que diminui). É **uma hipótese da pessoa**: o sistema não estima nem sugere a taxa. A população de cada data é a do último
  registro × (1 + x/100) elevado aos anos passados desde ele; **nas datas até o último registro, vale a população dele**. A
  mesma taxa vale para o território e para a referência (a razão e o índice entre dois territórios não mudam; as taxas e a
  diferença, sim); um valor informado como referência já é uma taxa e não muda. A frase termina com "Hipótese sua: população
  crescendo 2% ao ano depois de jun/2024, a mesma taxa no território e na referência." (ou "…; o valor informado não muda."), e
  a resposta, a nota das referências e a tela dizem a mesma hipótese. A hipótese só vale na comparação por taxa: com a métrica
  de quantidade, o pedido é recusado.
- Comparar quantitativos de territórios de portes diferentes não é comparar a suficiência do atendimento.

### Planejamento inverso

O menor número **inteiro** de médicos por evento com que o cenário alcança a meta na data final `T`, com a base `B(T)` **sem
arredondar** (seção 8.8 do anexo). Com `k` eventos iguais e permanência total, `x = ⌈(meta − N(T)) ÷ k⌉`, onde `N(T)` já conta
as outras intervenções do cenário; com permanência menor, cada evento pesa `(p/100)^anos até T`, e o motor procura o menor
inteiro. A resposta traz também a conta sem arredondar (o incremento médio teórico) e o cenário **simulado de novo** com o
acréscimo: reaplicado como intervenção, ele alcança a meta, e com um médico a menos por evento, não.

- **Meta:** um número de médicos; o **patamar anterior** (o do fenômeno 7 do Detector: a maior média de dois anos seguidos antes
  dos registros mais recentes; sem valor informado, o de cada território); ou o valor de uma **referência** na data final.
- **A meta do patamar é um número inteiro.** O patamar é uma média e pode ter decimal: a meta é o patamar **arredondado para
  cima** (78,25 vira 79; 1,75 vira 2), e o rótulo diz de onde ela veio — "voltar ao patamar de 79 médicos em jun/2026 (patamar de
  78,25, média de 4 registros, arredondado para cima)"; com patamar inteiro, "(média de 4 registros)". Quando o valor que vem no
  pedido não é o patamar do território, o rótulo diz "patamar informado" (com o valor, quando ele foi arredondado), sem a média
  que ele não é. Antes (até 14/11/2026), a meta era o patamar com decimal, e o texto "teria 78 médicos" parecia ficar abaixo de
  uma meta de 78,25.
- **Estados:** `calculado`; `ja_alcancada` (o cenário já chega à meta: nenhum acréscimo); `nao_alcancavel` (com permanência zero,
  nenhum médico acrescentado está no território na data final); `nao_calculavel` (nenhum evento do calendário entre a origem e a
  data final; território sem patamar calculável; referência ausente ou sem valor).
- O resultado é uma **necessidade matemática condicional** às hipóteses do cenário. Não é plano de provimento, recomendação nem
  avaliação de suficiência.

### Níveis no cenário (hipótese do cenário)

Só os **sinais 1 e 2** do Detector (poucos médicos e nenhum médico registrado, de limite fixo) valem para uma trajetória simulada
([Proposta V3](DETECTOR_E_SIMULADOR_V3.md), seção C.6; desde 13/11/2026, com os níveis moderado, elevado e crítico). Eles são
aplicados ao valor do cenário na data final (e aos limites da faixa, quando há): quantos médicos o território teria, em
que nível ficaria e quanto a saída de um médico tiraria. Quando a faixa cruza um limite, a tela diz "pode ficar entre moderado e
elevado", sem escolher um só. Vale só para municípios e leva o rótulo "hipótese do cenário" (antes, "hipótese derivada da
simulação"). Os sinais comparados com a base e os de evento observado (queda, patamar, declínio) **nunca** são aplicados a curvas
simuladas.

### Faixa de 8 em cada 10 (ou de 5, ou de 9)

- **O que é** (Proposta V3, seção C.4): entre as retroprojeções de territórios do mesmo porte e com o mesmo prazo, 8 em cada 10
  terminaram dentro da faixa — do 10º ao 90º percentil do erro relativo (observado ÷ cenário − 1), por porte na origem (as 10
  faixas da régua comum) e prazo (1 a 4 anos), medido na retroprojeção da **própria base**. A pessoa pode pedir 5 em cada 10 (do
  25º ao 75º) ou 9 em cada 10 (do 5º ao 95º); 8 é o padrão.
- **Só para a forma e a janela escolhidas pela base:** com outro método ou outra janela, não há faixa, e a tela diz por quê. Vale
  também quando o padrão é manter o último valor porque nenhum candidato errou menos (a faixa é a dele).
- **Casos mínimos por prazo:** 200 para 8 em cada 10, 80 para 5 e 400 para 9. Faltando casos no porte, a faixa é montada com as
  faixas vizinhas (uma de cada lado); ainda faltando, com portes menores, um a um (a faixa fica mais larga, e por isso mais
  cautelosa, com o aviso `FAIXA_COM_PORTES_MENORES`); se nada bastar, é indisponível, com os números ("A faixa de 8 em cada 10
  pede 200 casos por prazo, e esta base tem 88 em 1 ano para o porte deste território, mesmo juntando os portes vizinhos e os
  menores."). Os casos contados são os do porte do território, e não os da base toda, que o perfil da base mostra (120, na
  planilha de teste): a frase diz isso, para um número não parecer contradizer o outro.
- **O porte de um valor com casas** (uma média, ou o valor de um cenário) é o da parte inteira: 3,5 fica na faixa de 1 a 3, e
  nenhum valor a partir de 1 fica sem porte (`reguas.porte_de`; antes, 3,5 ou 9,5 caíam entre duas faixas). Com contagens
  inteiras, nada muda.
- **Conferência no tempo:** para cada origem de teste, a faixa é remontada só com as retroprojeções cujo resultado já era
  conhecido naquela data e conferida nos casos dela. Pela cobertura (arredondada em pontos inteiros) frente à meta (80%, 50% ou
  90%): até 5 pontos abaixo, **conferida**; de 6 a 10 pontos abaixo, **provisória**; mais que isso, **indisponível** (como a
  cobertura é comparada em pontos inteiros, não há caso entre 5 e 6; antes, este documento dizia "de 5 a 10"). Com menos
  de 3 origens de teste ou menos de 50 casos de teste, a faixa não pôde ser conferida e fica **provisória** (aviso
  `FAIXA_PROVISORIA`).
- A data intermediária usa a faixa do ano inteiro seguinte. A faixa é da base e **acompanha a intervenção** (os limites da base,
  mais o efeito da intervenção).
- **Sem "buracos" de prazo:** a faixa de um cenário vai do primeiro ano até o maior prazo **seguido** que a retroprojeção da base
  sustenta (aviso `FAIXA_ATE_4_ANOS`, o nome de antes, quando a data final passa dele). Um prazo sem faixa — por poucos casos ou
  por cobertura baixa na conferência — encerra a faixa ali; se o prazo de 1 ano não tem faixa, o cenário não tem faixa, com o
  motivo desse prazo. O resumo da faixa (a conferência, os casos e como ela foi montada) descreve a data final.
- **Conjuntos:** a faixa do porte da soma, rotulada como aproximação.
- **A faixa inteira de um lado da linha:** a faixa é montada com o erro observado no passado, e não em volta da linha do
  cenário. Ela pode ficar inteira acima (ou abaixo) da linha — por exemplo, a de 5 em cada 10 de um estado, em 4 anos. Não é erro
  da conta, e a frase da faixa na tela diz o que isso quer dizer: "A faixa fica inteira acima da linha do cenário: no passado da
  base, neste porte e neste prazo, o número observado ficou, na maior parte dos casos, acima do que esta forma de projetar dava."
- **Indisponível**, com o motivo e sem extrapolar: além do maior prazo com casos; território em zero; o todo (uma série só);
  outro método ou outra janela; base sem retroprojeção bastante; porte sem casos bastantes; cobertura baixa na conferência.
- Na base do Brasil: nos municípios, a faixa de 8 em cada 10 existe até 4 anos (conferida em 1 e 2 anos; provisória em 3 e 4, e
  nos municípios de 10.000 médicos ou mais); nos estados como unidade, é indisponível (189 casos em 1 ano, para 200 pedidos).

### Avisos de horizonte

Informativos, pela razão entre o tempo até a data final (H) e a janela do método (W; no M0, no M0d e no M0g, 3 anos): até W/2, normal;
até W, cautela; até 2W, extrapolação além da janela; acima, extrapolação extrema. O aviso diz os dois tempos. Quando o cenário
**mantém o último valor** (M0), que não usa a história, a frase é simples e não fala em referência nem em história (desde a
revisão final do comando V23, 15/11/2026; os níveis e os códigos são os mesmos): "Cautela: quanto mais longe a data final, mais
incerto o cenário (aqui, 2 anos à frente)."; mais longe, "Extrapolação: a data final fica longe do último registro, e o cenário
é muito incerto (aqui, 4 anos à frente)." e "Extrapolação extrema: a data final fica muito longe do último registro, e o
cenário é incerto demais para ser lido como um número (aqui, 7 anos à frente)." Antes, o texto dizia "… a mais da metade do tempo
de referência (2 anos à frente; a referência são 3 anos, porque manter o último valor não usa a história)", o que confundia —
e uma base pode nem ter 3 anos. Nos outros métodos, continua "… do tempo de história usado no cálculo (2 anos à frente, com 3 anos de história
usados no cálculo)."

### Estados de um cenário

`calculado`; `nao_aplicavel` (o método não vale para a série ou para o nível, com o motivo); `nao_calculavel` (sem registro usável,
série em zero no M3, data final ou intervenção até a origem); `retirada_acima_do_estoque`. Só o cenário calculado tem valor, texto
e curva.

## Qualquer base

Desde o comando V23 (Proposta V3, seção C.9), nada da base do Brasil fica escrito no motor: o mês da série anual, os meses de
registro, o grupo de cima e os nomes vêm da base em uso (`backend/series_brasil.py` e `backend/series_da_planilha.py`), e a
retroprojeção, a escolha da forma de projetar e as faixas são recalculadas para cada base e versão, uma vez.

- **Planilha enviada:** o Simulador abre com a planilha em uso, lida com o mesmo mapeamento de colunas, as mesmas premissas e os
  mesmos nomes das análises e do Detector. Nada é gravado, e nada vai ao provedor de IA.
- **Sem grupo de cima:** o candidato é o crescimento da base toda (M0g); o crescimento do grupo (M0d) "não se aplica", com o
  motivo.
- **Base sem história bastante** (menos de 3 origens com 3 anos antes e 1 ano depois) ou sem série anual: só "manter o último
  valor", com o aviso, e faixa indisponível, com o motivo.
- **O perfil da base** (antes da ferramenta) diz o que o Simulador sustenta: a forma escolhida, até quantos anos há faixa e até
  quantos ela foi conferida, ou o motivo de não haver ([Perfil da base](PERFIL_DA_BASE_DETECTOR_SIMULADOR.md), seção 9).
- **Exemplo, a planilha de teste** (`backend/tests/planilha_das_ferramentas.csv`: 20 distritos fictícios, de seis em seis meses,
  de jan/2014 a jul/2023, sem grupo de cima): 6 origens (jul/2017 a jul/2022); a taxa do próprio distrito errou 48% mais que
  manter o último valor, e o crescimento da base toda, 17% mais: nenhum vale, e "continuar como vinha" mantém o último valor,
  com o aviso. A faixa de 8 em cada 10 é indisponível ("pede 200 casos por prazo, e esta base tem 88 em 1 ano para o porte deste
  território", num distrito de 10 a 19 enfermeiros); a de 5 em cada 10 existe em 1 ano, com os portes vizinhos. A planilha
  informa que os trabalhadores contados são "Enfermeiros", e os textos dizem "enfermeiro" e "enfermeiros".

- **O grupo de cima como unidade** (desde 15/11/2026, etapa 7 do comando V23): numa planilha com a coluna de grupo, o grupo
  entra como território e como referência — a busca o oferece ("Costa Ondina como condado (unidade)"), a seleção local o mostra
  como "Costa Ondina (condado)", e o pedido o leva em `estados_unidade`. A série dele é a soma das unidades dele, nas datas em
  que todas têm registro, e a contagem diz isso. O grupo inteiro e as unidades dele não entram juntos (RQ-DAD-30): acrescentar o
  grupo tira da seleção local as unidades dele. A retroprojeção dos grupos é própria (poucos territórios: em geral, o cenário
  mantém o último valor, sem faixa, com o motivo). **O todo da planilha não muda**: continua sendo a soma das unidades com
  registro, com a forma escolhida para as unidades.

Com uma planilha, valem **os dois modos** (ajuste de 14/11/2026, antes da Pausa 2):

- o **modo avançado** usa os nomes dela em todos os textos (a contagem, a unidade, o todo), inclusive nas intervenções, no
  planejamento inverso, nas referências, nas tabelas e no CSV. A busca oferece as unidades e **o todo** (a soma das unidades com
  registro, com o nome que a pessoa deu: "A Solária (a soma das comunas com registro)"); as referências podem ser uma unidade, o
  todo, um conjunto ou um valor;
- numa planilha **só com anos** (um registro por ano), as datas do cenário são anos: os campos de data viram listas de anos
  (a partir do ano seguinte ao último registro), os atalhos somam anos, e os calendários se repetem "a cada (anos)" — o motor
  recusa um intervalo que não seja de 12 meses ou um múltiplo ("numa base com um registro por ano, o intervalo entre os eventos é
  de 12 meses ou um múltiplo de 12"). A distância até hoje é contada em anos inteiros.

O que **não** vale com uma planilha:

- sem datas que o Agente reconheça, o botão do Simulador fica desligado, com o motivo: "O Simulador de Cenários precisa de datas
  na planilha que o Agente reconheça (AAAAMM, AAAA-MM, AAAA-MM-DD ou só o ano).";
- o nível acima do grupo (o papel `grupo_territorial_superior`) não entra nas ferramentas, e não há conjuntos de grupos (numa
  planilha, os conjuntos são de unidades);
- a comparação por taxa pede população: sem ela, a comparação vem "não calculável", com o motivo ("Sem população válida no último
  registro para a hipótese de população constante.").

## Rota

`POST /api/simulador` (formulário, como `/api/painel`). Com a base do Brasil: `dataset=brazil`, `dataset_version` e `options`
(JSON). Com uma planilha (desde o comando V23): `file`, `sheet`, `mapping` e `options`, como em `/api/painel` e `/api/detector`;
as opções `rotulos`, `premissas` e `categoria` descrevem a planilha, e, sem as premissas que o portão das análises pede, a rota
devolve a mesma pendência do painel (422, com `pendencia`). O endereço e os campos de antes não mudaram. Só lê e calcula: nada é
registrado na sessão, e nada vai ao provedor de IA. Conta nas vagas das operações pesadas (`carga.PESADAS`).

| Opção | Conteúdo |
|---|---|
| `base`, `estados_unidade`, `conjuntos` | a seleção local, no contrato compartilhado das ferramentas (`series_brasil.selecao`), até 100 territórios |
| `brasil` | `true` acrescenta o todo, por último (na base do Brasil, a contagem nacional; numa planilha, a soma das unidades com registro); só o Simulador aceita |
| `janela` | `{"inicio", "fim"}`, competências da base; sem ela, os 3 anos até o último registro |
| `horizonte` | a data final, `AAAAMM`, em qualquer mês depois do fim da janela (até 2100); numa base só com anos, `AAAA00`; sem ela, 2 anos depois do último registro |
| `faixa` | 5, 8 ou 9 (em cada 10); sem ela, 8. Outro valor é recusado: "Faixa inválida: escolha 5, 8 ou 9 em cada 10." |
| `cenarios` | até 6: `{"id", "nome", "metodo", "taxa_manual_pct"?, "janela"?, "intervencoes"?, "planejamento"?}`; `metodo` é `padrao`, `M0`, `M0d`, `M0g`, `M1`, `M2`, `M3` ou `manual`; sem a lista, um cenário sem intervenção no método padrão |
| `intervencoes` | até 12 por cenário: `{"tipo": "acrescimo" ou "retirada", "quantidade", "em", "ate"?, "a_cada_meses"?, "permanencia_pct_ao_ano"?, "territorios"?}` |
| `planejamento` | por cenário: `{"meta": {"tipo": "valor" ou "patamar" ou "referencia", "valor"?, "referencia"?}, "em", "ate"?, "a_cada_meses"?, "permanencia_pct_ao_ano"?}` |
| `referencias` | até 5: `{"id", "territorio": "code:…" ou "uf:…" ou "br" ou o id de um conjunto da seleção, "tipo": "fixa" ou "dinamica", "metodo"?, "taxa_manual_pct"?}` ou `{"id", "tipo": "valor", "valor", "rotulo"?}` |
| `comparacao` | `{"metrica": "quantidade" ou "taxa", "forma": "diferenca" ou "razao", "populacao_pct_ao_ano": x}`; sem ela, a quantidade, pela diferença. `forma` e `populacao_pct_ao_ano` são de 15/11/2026 e opcionais; `populacao_pct_ao_ano` (de −20 a 20; zero é a população constante) só vale com a métrica `taxa` |

A resposta traz `versao` (`SIMULADOR-CENARIOS/V3/1`), `fonte` (como a do Detector: a base, a categoria, a origem — `brasil` ou
`planilha` —, o mês âncora, os nomes e o que a base tem), `competencias`, `ultimo_registro`, `janela`, `horizonte`, `faixa`
(`em_10`, `opcoes`, `padrao`), `metodos`, `territorios`, `retroprojecao`, `notas` e `limitacoes` (`CENARIO_HIPOTETICO`,
`PADRAO_ESCOLHIDO_PELA_BASE`, `FAIXA_SO_DO_METODO_PADRAO`).

- `retroprojecao`: `origens`, `faixas` e `tabela` das unidades da base (os campos de antes), `em_10`, `escolha` (a forma
  escolhida para as unidades: `metodo`, `rotulo`, `motivo` — `escolhido`, `nenhum_vale`, `poucas_origens` ou `sem_serie_anual` —,
  `origens`, `combinacoes`, `texto`, `candidatos` e `excecoes`) e `niveis` (o mesmo, por nível: `municipios` e, com contagem
  própria dos grupos, `estados`). Cada faixa traz `porte`, `anos`, `em_10`, `inferior_pct`, `superior_pct`, `casos`, `pede`,
  `origens`, `estado` (`conferida`, `provisoria` ou `indisponivel`), `como` (`propria`, `vizinhas` ou `portes_menores`),
  `cobertura_pct`, `origens_de_teste`, `casos_de_teste` e `rotulo`.
- Cada território traz `observado` (com o estado de cada registro e as marcas de registro), `historico` (as estatísticas
  descritivas), `lacunas` e `cenarios`; cada cenário, `estado`, `metodo` (`pedido`, `usado`, `rotulo`, `padrao`, `provisorio`,
  `voltou_ao_m0`, `soma`, `escolhido_pela_base`, `e_o_escolhido`), `parametros`, `avisos`, `horizonte`, `faixa` (`estado` —
  `disponivel` ou `indisponivel` —, `motivo`, `rotulo`, `em_10` e, quando há, `porte`, `ate_anos`, `como`, `conferencia`, `casos`,
  `cobertura_pct`, `origens_de_teste`), `trajetoria` (`data`, `anos`, `base`, `intervencao`, `total`, `retroprojecao`,
  `observado`, `faixa` — com `inferior`, `superior`, `anos`, `estado`, `como` e `validada`), `final`, `texto` e `entenda`
  (`jeito` e `faixa`, cada um com `texto` e `exemplo`).

Desde a etapa 5 do comando V22, a resposta traz também `referencias` (o rótulo, o tipo, a unidade, o estado e a descrição de
cada uma) e `comparacao` (`metrica` e `hipotese_de_populacao`; desde 15/11/2026, também `forma` e `populacao_pct_ao_ano` —
`null` com a população constante), e cada cenário pode trazer:

- `comparacoes` (com referências no pedido): por referência, `estado`, `forma`, `descricao`, `avisos`, `pontos` (`data`, `territorio`,
  `referencia`, `diferenca`, `razao`, `indice`), `inicial`, `final`, `alcance` (`estado` e `data`) e `texto`;
- `planejamento` (com o pedido): `estado`, `meta` (`tipo`, `valor`, `rotulo` e, quando ela é o patamar, `patamar` — o patamar sem
  arredondar —, `registros` — de quantos registros ele é a média; `null` quando o valor foi informado e não é o patamar do
  território — e `arredondado`), `sem_o_plano`, `eventos`, `datas`, `por_evento`, `total`, `teorico_por_evento`, `resultado`,
  `intervencao` (pronta para voltar como intervenção), `trajetoria` (o caminho do cenário com o acréscimo calculado, para o
  gráfico: `data`, `total` e `intervencao` em cada data; só no estado `calculado`) e `texto`;
- `hipotetico` (municípios): `rotulo`, `data`, `valor`, `inteiro`, `classe`, `impacto_pct` e `na_faixa`.

Erros de pedido vêm em 422, em português (seleção vazia ou acima de 100, território fora da base, competência fora da base, data
final até o fim da janela, método desconhecido, taxa manual ausente ou fora do método manual, intervenção inválida, referência
inválida, repetida ou acima de 5, métrica desconhecida, faixa inválida, planejamento sem meta ou sem calendário; sem base
nenhuma, "Escolha a base do Brasil ou envie uma planilha: a ferramenta lê a base que estiver em uso.").

## Retroprojeção: como os métodos se saíram no passado

`scripts/calibrar_simulador.py` (fora do CI, somente leitura) refaz o estudo com a base versionada e imprime as tabelas abaixo; o
motor calcula a mesma retroprojeção uma vez por versão da base e por nível de território (`simulador.retroprojetar`), em qualquer
base. Em cada registro do mês âncora com 3 anos de história e ao menos 1 ano à frente (na base do Brasil, jun/2017 a jun/2023, 7
origens), cada forma de projetar é ajustada **só com os registros até a origem** e confrontada com o observado 1, 2, 3 e 4 anos
depois. Entram os territórios com a janela de 3 anos inteira, com pelo menos 1 na origem e 3 anos antes; ficam fora os registros
de pico que volta e de quebra de fonte. Base versão `faa54169c5b6`, método `SIMULADOR-CENARIOS/V3/1`. Os portes são as 10 faixas
da régua comum (`backend/reguas.py`); até a V2.2, eram 6.

### A escolha da forma de projetar

**Municípios.** Origens: jun/2017, jun/2018, jun/2019, jun/2020, jun/2021, jun/2022, jun/2023 · 122.317 casos · 22 combinações de origem e prazo.

| Forma | Erro frente a manter o último valor | Errou menos em | Casos | Vale |
| --- | --- | --- | --- | --- |
| taxa composta da janela (M1) | 1,015 | 2 de 22 | 122.317 | não |
| persistência com o crescimento recente do estado (M0d) | 0,714 | 22 de 22 | 122.317 | sim |
| persistência com o crescimento recente da base toda (M0g) | 0,700 | 22 de 22 | 122.317 | sim |

Escolhido: persistência com o crescimento recente do estado (M0d; escolhido). Exceções por porte: nenhuma.

O escolhido frente a manter o último valor, por porte e prazo (com pelo menos 30 casos):

| Médicos na origem | Razões, do menor prazo ao maior |
| --- | --- |
| 1 a 3 | 1,04 · 0,99 · 0,93 · 0,90 |
| 4 a 9 | 1,02 · 0,96 · 0,90 · 0,87 |
| 10 a 19 | 0,98 · 0,93 · 0,88 · 0,83 |
| 20 a 49 | 0,94 · 0,88 · 0,82 · 0,78 |
| 50 a 99 | 0,89 · 0,82 · 0,77 · 0,72 |
| 100 a 299 | 0,82 · 0,74 · 0,68 · 0,64 |
| 300 a 999 | 0,72 · 0,65 · 0,60 · 0,57 |
| 1.000 a 2.999 | 0,65 · 0,60 · 0,55 · 0,53 |
| 3.000 a 9.999 | 0,53 · 0,39 · 0,35 · 0,29 |
| 10.000 ou mais | 0,54 |

**Estados como unidade.** Origens: jun/2017, jun/2018, jun/2019, jun/2020, jun/2021, jun/2022, jun/2023 · 594 casos · 22 combinações de origem e prazo.

| Forma | Erro frente a manter o último valor | Errou menos em | Casos | Vale |
| --- | --- | --- | --- | --- |
| taxa composta da janela (M1) | 0,398 | 22 de 22 | 594 | sim |
| persistência com o crescimento recente da base toda (M0g) | 0,410 | 22 de 22 | 594 | sim |

Escolhido: taxa composta da janela (M1; escolhido). Exceções por porte: nenhuma.

O escolhido frente a manter o último valor, por porte e prazo (com pelo menos 30 casos):

| Médicos na origem | Razões, do menor prazo ao maior |
| --- | --- |
| 300 a 999 | — |
| 1.000 a 2.999 | — |
| 3.000 a 9.999 | 0,36 · 0,33 · 0,36 · 0,39 |
| 10.000 ou mais | 0,28 · 0,24 · 0,24 · 0,26 |

- **A regra reproduz o padrão de antes:** nos municípios, o crescimento do estado (M0d) fica a 2% do melhor (o da base toda,
  0,700) e é o mais próximo do território; nos estados, a taxa composta do próprio estado (M1).
- **Municípios de 1 a 9 médicos:** o escolhido erra um pouco mais que manter o último valor em 1 ano (1,04 e 1,02), mas menos de
  2 a 4 anos. Não entra na exceção por porte, que pede errar mais em todos os prazos.
- **Base sem grupo de cima:** o crescimento da base toda errou quase o mesmo que o do estado (0,700 contra 0,714). É a retaguarda
  das planilhas sem coluna de grupo.

### As faixas dos municípios

**Faixa de 8 em cada 10** (o padrão). Do 10º ao 90º percentil de observado ÷ cenário − 1; pede 200 casos por prazo; meta de cobertura de 80%. "(p)" é provisória.

| Médicos na origem | 1 ano | 2 anos | 3 anos | 4 anos |
| --- | --- | --- | --- | --- |
| 1 a 3 | −9% a +87% | −18% a +105% | −21% a +140% (p) | −21% a +153% (p) |
| 4 a 9 | −26% a +40% | −31% a +56% | −33% a +69% (p) | −34% a +82% (p) |
| 10 a 19 | −23% a +29% | −28% a +40% | −29% a +53% (p) | −30% a +62% (p) |
| 20 a 49 | −19% a +24% | −23% a +34% | −24% a +44% (p) | −25% a +55% (p) |
| 50 a 99 | −15% a +20% | −19% a +30% | −20% a +42% (p) | −19% a +55% (p) |
| 100 a 299 | −12% a +17% | −16% a +26% | −16% a +34% (p) | −17% a +42% (p) |
| 300 a 999 | −9% a +12% | −12% a +20% | −14% a +28% (p) | −12% a +37% (p) |
| 1.000 a 2.999 | −6% a +8% | −8% a +16% | −10% a +21% (p) | −10% a +28% (p) |
| 3.000 a 9.999 | −6% a +7% | −8% a +14% | −10% a +19% (p) | −9% a +23% (p) |
| 10.000 ou mais | −5% a +5% (p) | −8% a +14% (p) | −10% a +19% (p) | −9% a +23% (p) |

Como cada faixa de 8 em cada 10 foi montada e conferida no tempo:

| Médicos na origem | Prazo | Estado | Montada | Casos | Origens | Cobertura na conferência | Origens de teste | Casos de teste |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 1 a 3 | 1 ano | conferida | o próprio porte | 4.039 | 7 | 75,0% | 6 | 3.310 |
| 1 a 3 | 2 anos | conferida | o próprio porte | 3.649 | 6 | 76,4% | 4 | 2.226 |
| 1 a 3 | 3 anos | provisória (sem conferência bastante) | o próprio porte | 3.216 | 5 | 75,5% | 2 | 1.100 |
| 1 a 3 | 4 anos | provisória (sem conferência bastante) | o próprio porte | 2.715 | 4 | — | 0 | 0 |
| 4 a 9 | 1 ano | conferida | o próprio porte | 11.047 | 7 | 78,0% | 6 | 9.315 |
| 4 a 9 | 2 anos | conferida | o próprio porte | 9.699 | 6 | 75,3% | 4 | 6.299 |
| 4 a 9 | 3 anos | provisória (sem conferência bastante) | o próprio porte | 8.253 | 5 | 75,1% | 2 | 3.208 |
| 4 a 9 | 4 anos | provisória (sem conferência bastante) | o próprio porte | 6.669 | 4 | — | 0 | 0 |
| 10 a 19 | 1 ano | conferida | o próprio porte | 8.725 | 7 | 79,4% | 6 | 7.520 |
| 10 a 19 | 2 anos | conferida | o próprio porte | 7.425 | 6 | 77,1% | 4 | 4.996 |
| 10 a 19 | 3 anos | provisória (sem conferência bastante) | o próprio porte | 6.146 | 5 | 74,7% | 2 | 2.510 |
| 10 a 19 | 4 anos | provisória (sem conferência bastante) | o próprio porte | 4.869 | 4 | — | 0 | 0 |
| 20 a 49 | 1 ano | conferida | o próprio porte | 7.211 | 7 | 77,7% | 6 | 6.302 |
| 20 a 49 | 2 anos | conferida | o próprio porte | 5.998 | 6 | 77,3% | 4 | 4.130 |
| 20 a 49 | 3 anos | provisória (sem conferência bastante) | o próprio porte | 4.851 | 5 | 77,5% | 2 | 2.018 |
| 20 a 49 | 4 anos | provisória (sem conferência bastante) | o próprio porte | 3.823 | 4 | — | 0 | 0 |
| 50 a 99 | 1 ano | conferida | o próprio porte | 3.000 | 7 | 76,6% | 6 | 2.626 |
| 50 a 99 | 2 anos | conferida | o próprio porte | 2.523 | 6 | 75,4% | 4 | 1.762 |
| 50 a 99 | 3 anos | provisória (sem conferência bastante) | o próprio porte | 2.054 | 5 | 71,5% | 2 | 888 |
| 50 a 99 | 4 anos | provisória (sem conferência bastante) | o próprio porte | 1.606 | 4 | — | 0 | 0 |
| 100 a 299 | 1 ano | conferida | o próprio porte | 2.765 | 7 | 77,6% | 6 | 2.411 |
| 100 a 299 | 2 anos | conferida | o próprio porte | 2.296 | 6 | 76,4% | 4 | 1.578 |
| 100 a 299 | 3 anos | provisória (sem conferência bastante) | o próprio porte | 1.859 | 5 | 74,3% | 2 | 783 |
| 100 a 299 | 4 anos | provisória (sem conferência bastante) | o próprio porte | 1.452 | 4 | — | 0 | 0 |
| 300 a 999 | 1 ano | conferida | o próprio porte | 1.454 | 7 | 78,7% | 6 | 1.276 |
| 300 a 999 | 2 anos | conferida | o próprio porte | 1.211 | 6 | 78,8% | 4 | 846 |
| 300 a 999 | 3 anos | provisória (sem conferência bastante) | o próprio porte | 976 | 5 | 79,4% | 2 | 417 |
| 300 a 999 | 4 anos | provisória (sem conferência bastante) | o próprio porte | 763 | 4 | — | 0 | 0 |
| 1.000 a 2.999 | 1 ano | conferida | o próprio porte | 476 | 7 | 77,1% | 6 | 420 |
| 1.000 a 2.999 | 2 anos | conferida | o próprio porte | 397 | 6 | 82,0% | 4 | 283 |
| 1.000 a 2.999 | 3 anos | provisória (sem conferência bastante) | o próprio porte | 318 | 5 | 81,6% | 2 | 141 |
| 1.000 a 2.999 | 4 anos | provisória (sem conferência bastante) | o próprio porte | 243 | 4 | — | 0 | 0 |
| 3.000 a 9.999 | 1 ano | conferida | com os vizinhos | 679 | 7 | 87,3% | 6 | 150 |
| 3.000 a 9.999 | 2 anos | conferida | com os vizinhos | 560 | 6 | 83,8% | 4 | 99 |
| 3.000 a 9.999 | 3 anos | provisória (sem conferência bastante) | com os vizinhos | 446 | 5 | 93,9% | 2 | 49 |
| 3.000 a 9.999 | 4 anos | provisória (sem conferência bastante) | com os vizinhos | 338 | 4 | — | 0 | 0 |
| 10.000 ou mais | 1 ano | provisória (sem conferência bastante) | com os vizinhos | 203 | 7 | 91,2% | 6 | 34 |
| 10.000 ou mais | 2 anos | provisória (sem conferência bastante) | com portes menores | 560 | 6 | 87,0% | 4 | 23 |
| 10.000 ou mais | 3 anos | provisória (sem conferência bastante) | com portes menores | 446 | 5 | 83,3% | 2 | 12 |
| 10.000 ou mais | 4 anos | provisória (sem conferência bastante) | com portes menores | 338 | 4 | — | 0 | 0 |

Frente à V2.2 (6 portes, P10 a P90 com as 7 origens e conferência "sem uma origem"): os limites dos portes que não mudaram
(10 a 19, 20 a 49, 50 a 99 e 100 a 299) são os mesmos; "1 a 9" virou "1 a 3" e "4 a 9", e "300 ou mais" virou quatro portes. A
conferência passou a ser **no tempo** (só com o que já era conhecido em cada origem de teste), mais exigente que a de antes: a
cobertura fica entre 75% e 87% em 1 e 2 anos (conferida) e não pode ser conferida em 4 anos (nenhuma origem de teste), nem com
origens bastantes em 3 anos (2 origens de teste). Por isso, 3 e 4 anos são provisórias em todos os portes.

**Faixa de 5 em cada 10.** Do 25º ao 75º percentil de observado ÷ cenário − 1; pede 80 casos por prazo; meta de cobertura de 50%. "(p)" é provisória.

| Médicos na origem | 1 ano | 2 anos | 3 anos | 4 anos |
| --- | --- | --- | --- | --- |
| 1 a 3 | −6% a +39% (indisponível) | −10% a +50% (indisponível) | −13% a +70% (p) | −13% a +75% (p) |
| 4 a 9 | −8% a +17% | −14% a +25% | −16% a +32% (p) | −17% a +39% (p) |
| 10 a 19 | −13% a +12% | −15% a +17% | −16% a +24% (p) | −15% a +29% (p) |
| 20 a 49 | −9% a +11% | −12% a +15% | −13% a +21% (p) | −12% a +26% (p) |
| 50 a 99 | −7% a +9% | −9% a +14% (p) | −9% a +21% (p) | −7% a +28% (p) |
| 100 a 299 | −5% a +8% | −6% a +13% | −6% a +18% (p) | −5% a +24% (p) |
| 300 a 999 | −3% a +6% | −5% a +10% | −5% a +15% (p) | −3% a +20% (p) |
| 1.000 a 2.999 | −3% a +4% (p) | −4% a +7% (p) | −3% a +10% (p) | −3% a +17% (p) |
| 3.000 a 9.999 | −3% a +2% | −4% a +3% | −4% a +6% (p) | −3% a +8% (p) |
| 10.000 ou mais | −3% a +2% (p) | −4% a +3% (p) | −4% a +5% (p) | −3% a +7% (p) |

Nos municípios de 1 a 3 médicos, em 1 e 2 anos, a faixa de 5 em cada 10 cobriu menos de 40% dos casos na conferência (a meta é
50%): fica indisponível, com o motivo. Como a faixa de um cenário não tem "buracos" de prazo, esses municípios ficam sem a faixa de
5 em cada 10 em todos os prazos, mesmo com os valores provisórios de 3 e 4 anos da tabela.

**Faixa de 9 em cada 10.** Do 5º ao 95º percentil de observado ÷ cenário − 1; pede 400 casos por prazo; meta de cobertura de 90%. "(p)" é provisória.

| Médicos na origem | 1 ano | 2 anos | 3 anos | 4 anos |
| --- | --- | --- | --- | --- |
| 1 a 3 | −37% a +116% | −40% a +164% | −43% a +190% (p) | −42% a +222% (p) |
| 4 a 9 | −32% a +61% | −39% a +81% | −41% a +99% (p) | −41% a +122% (p) |
| 10 a 19 | −30% a +42% | −35% a +61% | −37% a +75% (p) | −38% a +89% (p) |
| 20 a 49 | −25% a +36% | −30% a +50% | −32% a +64% (p) | −33% a +81% (p) |
| 50 a 99 | −21% a +29% | −29% a +47% | −27% a +61% (p) | −30% a +77% (p) |
| 100 a 299 | −19% a +23% | −23% a +36% | −23% a +48% (p) | −25% a +60% (p) |
| 300 a 999 | −13% a +17% | −17% a +28% | −19% a +38% (p) | −20% a +49% (p) |
| 1.000 a 2.999 | −8% a +12% | −15% a +25% | −17% a +34% (p) | −17% a +46% (p) |
| 3.000 a 9.999 | −8% a +11% | −10% a +19% | −13% a +26% (p) | −17% a +46% (p) |
| 10.000 ou mais | −8% a +11% (p) | −10% a +19% (p) | −13% a +26% (p) | −17% a +46% (p) |

### As faixas dos estados como unidade

**Faixa de 8 em cada 10.** Do 10º ao 90º percentil de observado ÷ cenário − 1; pede 200 casos por prazo; meta de cobertura de 80%. "(p)" é provisória.

| Médicos na origem | 1 ano | 2 anos | 3 anos | 4 anos |
| --- | --- | --- | --- | --- |
| 300 a 999 | indisponível (31 casos) | indisponível (28 casos) | indisponível (24 casos) | indisponível (20 casos) |
| 1.000 a 2.999 | indisponível (113 casos) | indisponível (98 casos) | indisponível (83 casos) | indisponível (67 casos) |
| 3.000 a 9.999 | indisponível (189 casos) | indisponível (162 casos) | indisponível (135 casos) | indisponível (108 casos) |
| 10.000 ou mais | indisponível (189 casos) | indisponível (162 casos) | indisponível (135 casos) | indisponível (108 casos) |

Em 1 ano há 189 casos, e a faixa de 8 em cada 10 pede 200: continua indisponível, como antes. A de 5 em cada 10 (80 casos) seria
possível, como provisória:

| Médicos na origem | 1 ano | 2 anos | 3 anos | 4 anos |
| --- | --- | --- | --- | --- |
| 300 a 999 | indisponível (31 casos) | indisponível (28 casos) | indisponível (24 casos) | indisponível (20 casos) |
| 1.000 a 2.999 | −1% a +3% (p) | −1% a +5% (p) | +1% a +8% (p) | indisponível (67 casos) |
| 3.000 a 9.999 | −1% a +2% (p) | 0% a +4% (p) | +1% a +7% (p) | +3% a +10% (p) |
| 10.000 ou mais | 0% a +2% (p) | 0% a +4% (p) | +1% a +7% (p) | +3% a +9% (p) |

### Erro de cada método frente à persistência

**Municípios** (erro absoluto médio frente ao M0: 1,00 = igual à persistência; abaixo, o método erra menos):

| Método | Médicos na origem | 1 ano | 2 anos | 3 anos | 4 anos |
| --- | --- | --- | --- | --- | --- |
| M0d | 1 a 3 | 1,04 | 0,99 | 0,93 | 0,90 |
| M0d | 4 a 9 | 1,02 | 0,96 | 0,90 | 0,87 |
| M0d | 10 a 19 | 0,98 | 0,93 | 0,88 | 0,83 |
| M0d | 20 a 49 | 0,94 | 0,88 | 0,82 | 0,78 |
| M0d | 50 a 99 | 0,89 | 0,82 | 0,77 | 0,72 |
| M0d | 100 a 299 | 0,82 | 0,74 | 0,68 | 0,64 |
| M0d | 300 a 999 | 0,72 | 0,65 | 0,60 | 0,57 |
| M0d | 1.000 a 2.999 | 0,65 | 0,60 | 0,55 | 0,53 |
| M0d | 3.000 a 9.999 | 0,53 | 0,39 | 0,35 | 0,29 |
| M0d | 10.000 ou mais | 0,54 | 0,47 | 0,40 | 0,41 |
| M0g | 1 a 3 | 1,04 | 0,99 | 0,94 | 0,90 |
| M0g | 4 a 9 | 1,02 | 0,96 | 0,90 | 0,86 |
| M0g | 10 a 19 | 0,98 | 0,93 | 0,88 | 0,83 |
| M0g | 20 a 49 | 0,94 | 0,88 | 0,82 | 0,78 |
| M0g | 50 a 99 | 0,89 | 0,83 | 0,77 | 0,73 |
| M0g | 100 a 299 | 0,82 | 0,74 | 0,68 | 0,65 |
| M0g | 300 a 999 | 0,73 | 0,65 | 0,60 | 0,58 |
| M0g | 1.000 a 2.999 | 0,63 | 0,56 | 0,50 | 0,47 |
| M0g | 3.000 a 9.999 | 0,49 | 0,37 | 0,33 | 0,29 |
| M0g | 10.000 ou mais | 0,49 | 0,40 | 0,29 | 0,30 |
| M1 | 1 a 3 | 1,21 | 1,24 | 1,26 | 1,29 |
| M1 | 4 a 9 | 1,19 | 1,27 | 1,33 | 1,39 |
| M1 | 10 a 19 | 1,19 | 1,29 | 1,35 | 1,44 |
| M1 | 20 a 49 | 1,13 | 1,22 | 1,26 | 1,27 |
| M1 | 50 a 99 | 1,09 | 1,15 | 1,16 | 1,18 |
| M1 | 100 a 299 | 0,98 | 0,99 | 0,96 | 0,97 |
| M1 | 300 a 999 | 0,84 | 0,80 | 0,75 | 0,74 |
| M1 | 1.000 a 2.999 | 0,69 | 0,67 | 0,65 | 0,61 |
| M1 | 3.000 a 9.999 | 0,80 | 0,87 | 1,12 | 1,21 |
| M1 | 10.000 ou mais | 0,52 | 0,48 | 0,42 | 0,42 |
| M2 | 1 a 3 | 1,22 | 1,19 | 1,16 | 1,16 |
| M2 | 4 a 9 | 1,23 | 1,22 | 1,22 | 1,22 |
| M2 | 10 a 19 | 1,21 | 1,20 | 1,20 | 1,21 |
| M2 | 20 a 49 | 1,19 | 1,13 | 1,11 | 1,09 |
| M2 | 50 a 99 | 1,12 | 1,03 | 0,99 | 0,96 |
| M2 | 100 a 299 | 1,06 | 0,93 | 0,87 | 0,81 |
| M2 | 300 a 999 | 0,94 | 0,78 | 0,72 | 0,69 |
| M2 | 1.000 a 2.999 | 0,83 | 0,67 | 0,63 | 0,59 |
| M2 | 3.000 a 9.999 | 0,83 | 0,63 | 0,58 | 0,55 |
| M2 | 10.000 ou mais | 0,57 | 0,47 | 0,42 | 0,38 |
| M3 | 1 a 3 | 1,22 | 1,24 | 1,24 | 1,26 |
| M3 | 4 a 9 | 1,25 | 1,30 | 1,36 | 1,41 |
| M3 | 10 a 19 | 1,26 | 1,34 | 1,38 | 1,50 |
| M3 | 20 a 49 | 1,22 | 1,27 | 1,30 | 1,32 |
| M3 | 50 a 99 | 1,19 | 1,21 | 1,24 | 1,26 |
| M3 | 100 a 299 | 1,08 | 1,07 | 0,99 | 1,00 |
| M3 | 300 a 999 | 0,93 | 0,84 | 0,78 | 0,76 |
| M3 | 1.000 a 2.999 | 0,79 | 0,70 | 0,67 | 0,62 |
| M3 | 3.000 a 9.999 | 0,94 | 1,00 | 1,26 | 1,80 |
| M3 | 10.000 ou mais | 0,58 | 0,51 | 0,48 | 0,43 |

**Estados como unidade:**

| Método | Médicos na origem | 1 ano | 2 anos | 3 anos | 4 anos |
| --- | --- | --- | --- | --- | --- |
| M0g | 300 a 999 | 0,81 | 0,64 | 0,47 | 0,47 |
| M0g | 1.000 a 2.999 | 0,47 | 0,40 | 0,43 | 0,47 |
| M0g | 3.000 a 9.999 | 0,37 | 0,34 | 0,37 | 0,40 |
| M0g | 10.000 ou mais | 0,28 | 0,26 | 0,28 | 0,31 |
| M1 | 300 a 999 | 0,87 | 0,76 | 0,63 | 0,58 |
| M1 | 1.000 a 2.999 | 0,48 | 0,31 | 0,29 | 0,28 |
| M1 | 3.000 a 9.999 | 0,36 | 0,33 | 0,36 | 0,39 |
| M1 | 10.000 ou mais | 0,28 | 0,24 | 0,24 | 0,26 |
| M2 | 300 a 999 | 0,99 | 0,72 | 0,60 | 0,62 |
| M2 | 1.000 a 2.999 | 0,71 | 0,45 | 0,46 | 0,48 |
| M2 | 3.000 a 9.999 | 0,45 | 0,40 | 0,45 | 0,48 |
| M2 | 10.000 ou mais | 0,40 | 0,33 | 0,36 | 0,37 |
| M3 | 300 a 999 | 0,99 | 0,69 | 0,55 | 0,58 |
| M3 | 1.000 a 2.999 | 0,65 | 0,35 | 0,35 | 0,34 |
| M3 | 3.000 a 9.999 | 0,39 | 0,34 | 0,37 | 0,40 |
| M3 | 10.000 ou mais | 0,31 | 0,25 | 0,27 | 0,27 |

**Viés em 4 anos** (observado − projetado, em médicos). A persistência subestima o crescimento do período; a forma escolhida
reduz o viés, sem zerá-lo.

Municípios:

| Médicos na origem | M0 | M0d |
| --- | --- | --- |
| 1 a 3 | +1,7 | +1,2 |
| 4 a 9 | +2,9 | +1,5 |
| 10 a 19 | +5,2 | +2,1 |
| 20 a 49 | +11,2 | +4,3 |
| 50 a 99 | +28,6 | +12,8 |
| 100 a 299 | +61,3 | +22,6 |
| 300 a 999 | +179,5 | +61,4 |
| 1.000 a 2.999 | +545,6 | +192,3 |
| 3.000 a 9.999 | +1283,5 | +148,1 |
| 10.000 ou mais | +5605,6 | +208,2 |

Estados como unidade:

| Médicos na origem | M0 | M1 |
| --- | --- | --- |
| 300 a 999 | +231,2 | +106,9 |
| 1.000 a 2.999 | +717,7 | +199,1 |
| 3.000 a 9.999 | +1567,2 | +602,1 |
| 10.000 ou mais | +7080,4 | +1703,7 |

**O Brasil** (uma série só, sem retroprojeção própria; a taxa composta de 3 anos contra manter o último valor, erro relativo
absoluto mediano):

| Prazo | Casos | Erro mediano da taxa composta de 3 anos | Erro mediano de manter o último valor |
| --- | --- | --- | --- |
| 1 ano | 7 | 0,8% | 4,8% |
| 2 anos | 6 | 1,7% | 9,3% |
| 3 anos | 5 | 2,9% | 13,4% |
| 4 anos | 4 | 3,8% | 16,9% |

O que o estudo sustenta e o que não sustenta:

- **O M0d como padrão dos municípios é confirmado nesta base, agora pela regra de escolha.** De 2 a 4 anos, ele erra menos que a
  persistência em todos os portes; em 1 ano, nos municípios de 1 a 9 médicos, erra um pouco mais. A persistência fica sempre à
  vista como referência.
- **M1, M2 e M3 erram mais que a persistência nos municípios pequenos** (M1: de 1,09 a 1,44 abaixo de 100 médicos). A tela avisa
  quando o método pedido errou mais que a persistência no porte do território.
- **O padrão dos estados e o do Brasil** foram conferidos só num período de crescimento forte e contínuo. O dos estados é o
  escolhido pela regra, sem faixa; o do Brasil segue **provisório**, com aviso.
- **Limite de toda a validação:** as origens são de 2017 a 2023, um período em que o número de médicos cresceu em quase todo o
  país. As faixas e os erros descrevem esse período; nada garante que valham noutro regime. As origens se sobrepõem no tempo, de
  modo que os casos não são independentes.

## Exportações

- **Cenário (JSON, formato `ADT-CENARIO/1`):** a seleção local (com a composição e a versão dos conjuntos, e o Brasil, quando
  está nela), a janela, a data final, o modo e os cenários (com o planejamento inverso de cada um), as referências e a métrica,
  com a versão do método, a base em uso (o nome e a categoria: "Brasil" e "MEDICINA" ou, com uma planilha, "planilha enviada" e a
  categoria dela), a versão da base, o último registro e a data da exportação. Desde o comando V23, o arquivo leva também o
  território em análise do modo simples (`territorio`), a faixa pedida, quando não é a de 8 em cada 10 (`faixa`), e a janela com
  que o Detector abriu o Simulador (`janela_do_detector`), e a importação os repõe. Desde 15/11/2026, leva também a comparação
  pela razão (`forma`) e a hipótese de população crescendo (`populacao` e `populacao_pct`), quando não são o padrão. **Importar** lê esse arquivo e repõe a
  configuração, sem calcular; se a base for outra versão, a tela avisa. A referência a um conjunto que não veio no arquivo fica
  de fora. O aviso de origem do Detector não é exportado.
- **Resultados (CSV, separador `;`, com BOM):** uma linha por território, cenário e data, com o observado, a base, a intervenção,
  o total e a faixa em precisão integral, e a rastreabilidade em cada linha (método pedido e usado, estado, origem, janela,
  avisos, o texto do cenário e as versões). Desde a etapa 5, também a meta do planejamento inverso, os médicos por evento (ou o
  estado, quando não há número), os eventos e o nível da hipótese do cenário em "Poucos médicos".
- No CSV dos resultados, as colunas da faixa levam o percentual pedido: "Faixa de 80%" (8 em cada 10, o padrão), "Faixa de 50%"
  ou "Faixa de 90%".
- **Avaliação dos métodos (JSON; desde 18/11/2026, AJ-03):** "Exportar a avaliação dos métodos (JSON)" leva a retroprojeção da
  base em uso como o motor a mandou (`retroprojecao`: `origens`, `em_10`, as `faixas` por porte e prazo, a `tabela` dos erros de
  cada método frente à persistência e, por nível, a `escolha` com os `candidatos`), com `ferramenta`, `conteudo` (o que o arquivo
  é: a avaliação dos métodos no histórico da base, e não uma análise do território escolhido), `versao_do_metodo`, `fonte` (a base
  e a versão), `ultimo_registro`, `janela`, `notas`, `limitacoes`, `exportado_em` e `referencia` (a Ficha B, com a seção pelo título, "A avaliação dos métodos no histórico da base", que não depende
  da numeração; desde o AJ-07, de 18/11/2026; antes, "seção 6"). São os
  números que a tela mostrava em "Como os métodos se saíram no passado".
- **Comparações (CSV, quando há referências):** uma linha por território, cenário, referência e data, com o valor do território,
  o da referência, a diferença, a razão e o índice, o alcance no horizonte simulado, os avisos e a hipótese de população (a do
  último registro ou, quando a pessoa a informou, a taxa de crescimento por ano).

## Limitações

- A base do Brasil só tem médicos, e o registro mais recente é jun/2024. Datas simuladas que já passaram não foram conferidas com
  registros.
- A contagem municipal é a de médicos registrados no município: quem atua em mais de um conta em cada um. Um conjunto é a soma das
  contagens dos componentes, nunca "médicos únicos".
- A base do cenário supõe que o passado recente continua: ela não conhece políticas, concursos, fechamentos ou choques.
- Comparar quantitativos absolutos de territórios de portes diferentes não é comparar suficiência do atendimento.
- A faixa só existe para a forma de projetar e a janela que a base escolheu, até o maior prazo com casos suficientes, e vem de um
  único período histórico. Em 3 e 4 anos, na base do Brasil, ela é provisória: ainda não há origens de teste bastantes para
  conferi-la.
- O padrão do Brasil (a taxa composta de 3 anos) é provisório e não tem faixa; os estados como unidade não têm faixa de 8 em cada
  10 (189 casos em 1 ano, para 200 pedidos).
- A escolha da forma de projetar compara só três candidatos (o próprio território, o grupo de cima e a base toda) com manter o
  último valor; M2, M3 e a taxa da pessoa ficam à escolha, sem faixa.
- A referência dinâmica usa a forma escolhida para o nível dela, com a janela geral do pedido; na tela, ela não tem método,
  janela nem intervenções próprios (a rota aceita outro método).
- A comparação por taxa vale com uma hipótese de população, sempre declarada: a do último registro em todas as datas ou, por
  escolha da pessoa, crescendo x% ao ano depois dele. A base não traz população futura, e o sistema não estima nem sugere a taxa
  de crescimento: é a mesma para o território e a referência, e não distingue territórios que crescem em ritmos diferentes.
- O planejamento inverso responde a uma conta, não a uma pergunta de política: ele não sabe se os médicos existem, se ficam, nem
  quanto custa.
- Uma intervenção vale para cada território do cenário; o número do planejamento inverso é próprio de cada território, e por
  isso só pode ser usado como intervenção com um território só na seleção local.
- Numa planilha enviada, o grupo de cima como unidade é a soma das unidades dele, nas datas em que todas têm registro (ela não
  tem a contagem própria do grupo), e a comparação por taxa pede população (seção "Qualquer base"). Numa planilha só com anos, os
  calendários se repetem em anos inteiros.
- A escolha de 5, 8 ou 9 em cada 10 fica no modo avançado; o modo simples usa a faixa escolhida lá e avisa quando ela não é a de 8.

**Assistente de conversa.** Ele continua recusando previsões e projeções livres (AT-04) e não monta cenários. Desde 11/11/2026,
a recusa indica o caminho: "Para montar cenários hipotéticos, que não são previsão, há o Simulador de Cenários, na linha
Ferramentas da área de análise: nele, você escolhe o método, as hipóteses e a data final." Desde 15/11/2026 (etapa 7 do comando
V23), a indicação aparece também com uma planilha enviada: o Simulador vale para qualquer base.

## Testes

- pytest: `backend/tests/test_simulador.py` — as fórmulas em séries sintéticas (M0, M0d e M0g; zero e ausência; a quebra de fonte e
  a volta ao M0; M1 com o tempo real e a recusa do início em zero; M2, M3 e os ajustes em lote; a taxa da pessoa; as intervenções
  somadas à base, a permanência e a retirada impossível; conjuntos e estados; a média aritmética só descritiva; os avisos de
  horizonte; o ajuste sem observações posteriores à janela); a retroprojeção da Proposta V3 (os casos, o erro frente ao último
  valor com cada porte pesando o mesmo, a regra de escolha em várias situações, a exceção por porte, o padrão sem retroprojeção
  bastante e o todo numa base sem a contagem dos grupos); as faixas de 5, 8 e 9 em cada 10 (os percentis e os casos mínimos, a
  retaguarda, a conferência no tempo, a faixa sem "buracos" de prazo e os motivos de não haver); a rota com um catálogo sintético
  (inclusive o Brasil como território, as referências com o alcance e a sobreposição, a comparação por taxa, o planejamento
  inverso reaplicado ao Simulador, a hipótese do cenário, a opção `faixa` e as recusas) e, no job `dados-reais`, a base versionada
  (a escolha da forma de projetar, as faixas e os erros acima, o Distrito Federal, Rio Rufino/SC, São Paulo como unidade, o limite
  de 100 territórios, o Brasil, as referências de Manaus, o planejamento inverso e "Simular recuperação" em Abreulândia/TO). Da
  revisão das capturas (14/11/2026): a meta do patamar inteira, arredondada para cima, com a origem no rótulo (o patamar do
  território, com a média de 4 registros, ou o "patamar informado"), e o caminho do cenário com o acréscimo (`trajetoria`). Da
  revisão de 15/11/2026: o aviso de horizonte de quem mantém o último valor, a janela com um registro só e o motivo da faixa
  indisponível com os casos do porte. `backend/tests/test_reguas.py` — o porte de um valor com casas.
- pytest: `backend/tests/test_ferramentas_qualquer_base.py` — o Simulador com uma planilha: a forma de projetar que ela escolhe, a
  faixa indisponível com o motivo, a rota com o arquivo, o pedido do modo avançado (o todo, o conjunto e as referências, com os
  nomes dela), a planilha só com anos (as datas em anos e o calendário de ano em ano), as linhas do Simulador no perfil da base
  e o nome dos trabalhadores informado no envio em todos os textos.
- pytest: `backend/tests/test_dialogo.py` — a recusa de projeção indica o Simulador, com a base do Brasil ou com uma planilha.
- pytest: `backend/tests/test_simulador.py` (etapa 7) — a comparação pela razão (a frase, os mesmos números e a referência em
  zero), a comparação por taxa com a população crescendo ou diminuindo (as taxas de cada data, a origem com a população do
  registro, o valor informado que não muda, a resposta, a nota e a frase com a hipótese) e as recusas (a forma desconhecida, a
  taxa fora de −20 a 20 e o crescimento sem a métrica de taxa).
- Node: `frontend/tests/simulador.test.mjs` — as datas (também as de uma base só com anos), a seleção local, o que falta para
  calcular, o pedido ao motor, a leitura da resposta, os textos da tabela e da faixa, a importação e a exportação do cenário e o
  CSV; o Brasil na seleção local, as referências e a métrica, o planejamento inverso, a configuração com que o Detector abre o
  Simulador, a hipótese do cenário e o CSV das comparações; o modo simples (o que testar, o território em análise e o pedido com um
  território só, sem a janela geral, as referências e o calendário do modo avançado); a resposta da V3 (a forma escolhida pela
  base, a faixa "N em cada 10", os "Entenda", os nomes e as formas da base); os três números; a avaliação dos métodos exportada
  com os números do motor, a ficha metodológica e a janela do cálculo (AJ-03); os textos com os nomes de outra
  base; e a tela (o modo simples numa tela só, as quatro etapas só no modo avançado e o campo de data). Da revisão das capturas:
  a meta que sai ao trocar de território, o campo com a meta inteira e a frase da origem dela, a leitura do caminho com o
  acréscimo e o desenho da meta, do caminho e da marca do acréscimo no gráfico. Da revisão de 15/11/2026: o resultado que sai ao
  trocar de território, o nome dos trabalhadores (a mesma regra do motor), o singular com 1, a faixa inteira de um lado da linha,
  o aviso único da seleção e o gráfico na largura da tela. Da etapa 7: a forma de comparar e a hipótese de população no pedido
  e na leitura da resposta, o que falta para calcular, as premissas no padrão e o "Voltar ao padrão", a janela igual à da base
  como o padrão, o tempo da janela em palavras, o cenário exportado e importado com as premissas novas, o "(Entenda)" geral e
  as premissas em frases na tela. Do AJ-17 (18/11/2026): no modo simples, o aviso da faixa escolhida no modo avançado, logo
  depois do aviso da forma.
- Navegador: `backend/tests/ui_simulador.py` (suíte `base-versionada`) — o modo simples (só continuar, acrescentar, retirar e chegar
  a uma meta; a faixa conferida e a provisória; os "Entenda", com o "Ver explicação completa" na seção da ficha; o link da ficha,
  com o PDF servido pela interface; a avaliação dos métodos exportada, igual à retroprojeção da resposta do motor; um estado como
  unidade sem faixa), o modo avançado (as quatro etapas, a janela do cálculo, a avaliação dos métodos exportada com as faixas por
  porte e os erros de cada método,
  o Brasil, as referências, o planejamento inverso e a escolha de 5, 8 ou 9 em cada 10), a passagem entre os dois modos (o que é
  do avançado não vai no pedido do simples; a forma e a faixa escolhidas lá vão, com os avisos no modo simples, desde o AJ-17, e
  "Voltar ao padrão" desfaz as duas), "Abrir no Simulador" e "Simular recuperação" (a meta de 79 médicos para o patamar de
  78,25 de Abelardo Luz/SC, com a origem; a meta trocada por um número da pessoa), a meta e o resultado que saem ao trocar de
  território, o gráfico de "Chegar a uma meta" (a linha da meta, o caminho com o acréscimo e a marca dele), "Acrescentar 1
  médico" e o gráfico desenhado na largura da tela, no computador e numa tela de celular (texto de 12 px); da etapa 7, o
  "(Entenda)" geral no título, o "Voltar ao padrão" único (desligado no padrão; desfaz a janela, a permanência, a comparação e a
  forma de projetar escolhida no modo avançado), as premissas em frases, a comparação pela razão e pela taxa com a população
  crescendo 1,5% ao ano. Também `backend/tests/ui_detector.py`
  ("Simular recuperação" e o perfil da base) e `backend/tests/ui_planilha_ficticia.py` (o Simulador com a planilha fictícia, nos
  dois modos, sem o vocabulário da base do Brasil).
