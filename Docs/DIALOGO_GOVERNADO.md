# Diálogo governado da página única

Desde 26/10/2026, a conversa da página única tem um **gestor de diálogo** no backend local (`backend/dialogo.py`). Ele
entende continuidade, correções, perguntas sobre o resultado em exibição, pedidos de explicação, verificações e tentativas
de induzir o agente a sair do que a SPEC autoriza. O princípio é **liberdade linguística, autoridade analítica governada**:

- a conversa interpreta e organiza; **nenhum número, classe, relação, ordem ou nota é produzido pela conversa**: tudo é
  copiado da resposta do motor e conferido antes de aparecer (INV-02, INV-03, C-04);
- explicação de método com as formas literais do catálogo governado ou com as formulações das fichas de método
  (`backend/definicoes.py`), que o Gemini pode parafrasear sob controle de fidelidade (Adendo PAR-20261026 da SPEC);
- desde 26/10/2026, **Gemini conversa, motor decide**: com o provedor disponível, as perguntas de conversa vão ao Gemini
  com o cartão do contexto e a resposta verificada do gestor, e ele redige a resposta; o texto só aparece depois da
  conferência de fidelidade (CAP-SIN-01, INV-13, RQ-SIN-04 a RQ-SIN-06). Comandos do gráfico, respostas a esclarecimentos,
  desfazer, voltar e recusas de governança continuam determinísticos. Ao provedor nunca vão arquivos, registros,
  identificadores ou nomes de campo; vão a mensagem triada, a janela da conversa triada e o resultado agregado em exibição.

`ADT_DIALOGO=0` desliga o gestor e restaura o caminho anterior. `ADT_CONVERSA_GEMINI=0` desliga só a redação pelo Gemini.

## Arquitetura

| Camada | Onde | O que faz |
|---|---|---|
| Memória da conversa | `frontend/src/conversaGrafico.ts`, `AnalysisAssistant.tsx` | A tela guarda a pergunta de esclarecimento sem resposta (com as alternativas ou o modelo da resposta), a memória da última resposta e os estados do gráfico antes de cada pedido aplicado pela conversa (até 8). Envia tudo no campo `conversa` (os 6 estados mais recentes) e o resultado em exibição em `displayed_result_id`. Aplica o pedido `painel`, o `desfazer` (volta aos estados guardados) e as `acoes` (abrir "Entenda esta análise" com termos destacados). |
| Gestor de diálogo | `backend/dialogo.py` | `reconhecer` identifica o ato sem o provedor; `executar` responde. Usa a gramática local (`conversa_grafico.py`) para transformar rascunhos em pedidos do gráfico. Nunca calcula. |
| Explicação verificada | `backend/explicacao.py` | Compõe o texto em partes: conectivos fixos e **segmentos** copiados de caminhos da resposta do motor (valores, rótulos, períodos, notas) ou formas do catálogo governado. `verificar` confere cada segmento contra a resposta antes da exibição; composição adulterada é recusada. |
| Ordens do motor | `painel.conversation_facts`, `painel.conversation_top` | O maior e o menor de cada atributo (densidade, quantidade, população, distância, variação, permanência), contados no motor, com os empates preservados; desde 26/10/2026, também os N primeiros (ou últimos) pela colocação de competição (1, 1, 3), com todos os empatados na posição de corte, para a comparação pelos extremos. |
| Intérprete com o provedor | `backend/llm_bridge.py` | Classifica 16 atos (`dialogue`) e os campos `style`, `subject`, `attribute` e `direction`, todos enumerações, e devolve no mesmo contrato o texto `resposta`, que só aparece depois da conferência. O gestor executa o ato com a memória e o resultado locais (`dialogo.do_interprete`). Sem teto local de chamadas; espera só por sinal do provedor (ver "Disponibilidade"). |
| Triagem | `backend/triagem.py` | As quatro classes de RQ-DAD-20 antes de qualquer envio: identificadores e nomes sem evidência viram marcadores numerados por tipo; territórios, grupos, regiões e categorias da base, os nomes após marcador territorial, a linguagem funcional, os títulos ("Dr.", "Sra.") e as letras isoladas (símbolos de fórmula, iniciais) ficam. O que já virou marcador num envio continua marcador, com o mesmo número, em todos os textos dele. A mensagem da tela não muda. |
| Cartão do contexto | `backend/contexto_conversa.py` | A tela, o resultado em exibição (valores formatados como na tela, ordens do motor, classes, notas, disponibilidade), o resultado anterior, a conversa (janela recente e pendência), as funcionalidades da página, a resposta verificada e as fichas pertinentes. Passa pela triagem: o texto da pessoa (mensagem, janela, pendência), completa; o texto do sistema (resultado, resposta verificada, fichas), pelas classes A e C, sem mexer em fórmulas e códigos de método; o nome escrito pela pessoa que a resposta verificada repete continua marcador. |
| Redação conferida | `backend/conversa_gemini.py` | O Gemini redige a resposta a partir do cartão; conferência; até 2 regenerações com a lista das violações; reserva verificada com TPL-08. Desde 26/10/2026, nenhuma chamada nova (redação ou regeneração) começa depois de 20 s do pedido (`llm_bridge.ORCAMENTO_DE_REGENERACAO`): vale a resposta verificada. |
| Conferência de fidelidade | `backend/fidelidade.py` | Números, nomes, ordens e classes do motor; nenhuma relação calculada pelo modelo ("o dobro", "três vezes maior"); nenhum número de exemplo documentado de uma ficha usado como valor; juízo, causa, acesso, heterogeneidade, destaque e previsão só como ressalva negativa; ressalvas obrigatórias; afirmação de ação; elementos essenciais e proibições das fichas. A frase copiada da resposta verificada ou de uma ficha não é afirmação nova; o texto da pessoa não é material verificado. |
| Fichas de método | `backend/definicoes.py` | Formulação autorizada em linguagem simples de cada conceito (densidade, quantidade, distância, referência, grupos, agregação, variação, tendência e as 7 classes, velocidade, comparação, régua, rotatividade), com os elementos essenciais e as afirmações proibidas. |

Ordem na página única: (1) frases-resumo respondidas na tela ("o que esse gráfico mostra?", "resuma o gráfico", "o que estou
vendo?"); (2) intérprete local (`/api/exploration/interpret`): gestor de diálogo e, sem ato, a gramática; com o Gemini
disponível, as perguntas de conversa e as orientações do catálogo cedem a vez (`handled: false`) ao canal contextual; (3)
intérprete contextual (`/api/llm/interpret-context`): de novo o gestor, agora com a redação pelo Gemini, e, sem ato, o
provedor, com o cartão do contexto. Sem o provedor, o pedido que dependeria dele recebe resposta (HTTP 200) com o campo
`indisponibilidade` e a comunicação cordial (ver "Disponibilidade"), em vez de erro.

## Atos do diálogo

| Ato | Exemplos | Resposta |
|---|---|---|
| Resposta a esclarecimento | "Município.", "a cidade", "o estado", "a do Pará", "PB", "o primeiro", "junho", "a de janeiro" | Escolhe a alternativa pendente e aplica o pedido original com ela ("Entendi: …"). Informação dada antes de uma pergunta encadeada é lembrada ("Anotei “a do Pará” para quando essa escolha aparecer"). Sem escolha clara, repete a pergunta; "deixa pra lá" cancela. |
| Correção da escolha | "Não, o estado." | Troca pela alternativa restante. Estado e município não ficam no mesmo gráfico: a comparação continua e a conversa oferece comparar os estados. |
| Correção com novo pedido | "Não, eu queria a evolução, não só o resultado atual." | Aplica o pedido corrigido ("Entendi a correção. Abri a tendência…"). |
| Desfazer | "Não era isso que eu queria.", "desfaz" | Volta ao estado do gráfico antes da última mudança feita pela conversa. Logo depois de uma pergunta (nada mudou), "não era isso" deixa a pergunta de lado e oferece desfazer a mudança anterior. |
| Voltar | "Volta para a comparação anterior.", "volta como estava antes" | Reaplica o estado anterior pedido. A volta é uma mudança como as outras: "desfaz" logo depois retorna ao estado de antes da volta. |
| Trocar, incluir, tirar | "Troca o primeiro pelo segundo.", "troca Porto Velho por Macapá", "põe João Pessoa no lugar de Natal", "inclui Parintins", "Agora inclui mais um." (pergunta qual), "tira Tefé" | Muda a comparação ou os territórios em análise. |
| Todos | "E se considerarmos todos?", "todos os municípios do Paraná" | Todos os municípios (ou os do estado citado). |
| Pedido em forma de pergunta | "e ao longo do tempo, como foi?" | A tendência dos mesmos territórios. |
| Proximidade a partir do extremo (28/10/2026) | "Quero identificar o município de menor densidade e o mais próximo a ele com densidade de no mínimo 1,5 médicos por mil habitantes", "o mais populoso e o mais próximo dele com densidade acima de 3" | O extremo vem das ordens do motor sobre o gráfico em exibição, com os empates, e vai para a base; a condição vai para a referência, e o pedido vira a Escolha dos territórios da Análise Espacial (ver "Proximidade pela conversa"). |
| Referência mais próxima (28/10/2026) | "Qual é o mais próximo?", "qual a referência mais próxima?" (também a continuação do pedido acima) | Com a Escolha dos territórios em exibição, a referência mais próxima de cada um da base, a distância em linha reta e a densidade da referência, copiadas do motor, com os empates e a ressalva TPL-11; botões trocam de onde a referência parte. Sem a Escolha dos territórios, a comparação das distâncias, como antes. |
| Pergunta sobre o resultado | "Qual deles apresenta densidade maior?", "E em relação à população?" (herda a direção), "quem tem menos profissionais?", "qual a diferença entre eles?", "quantos municípios estão no gráfico?" | Os valores e a ordem do motor; a diferença assinada que a comparação do motor calculou (sem comparação aberta, abre a comparação). Não muda o gráfico. |
| Explicação | "Explique esse resultado.", "Não entendi a aceleração.", "Mas por que isso é diferente de crescimento?", "E o que isso quer dizer para esse município?", "Agora explique de maneira mais técnica." | Registros objetivo, simples, didático e técnico, com memória do tópico. Ver "Explicação progressiva". |
| Verificação e limites | "Esse crescimento significa que o município melhorou?", "então Manaus tem médicos suficientes?", "Qual foi a causa dessa queda?", "a distância mostra o tempo de viagem?", "esse número é confiável?" | Os fatos do resultado e a regra governada: CFG-NOR (juízo normativo), TPL-06 com EXC-03 (causa), TPL-11 (acesso), notas do motor (procedência). Antes de tratar a causa, confere a premissa ("o resultado não mostra queda para …"). |
| Referência ao resultado anterior | "Não, eu estava falando da análise anterior." | Responde sobre o resultado anterior da sessão. |
| Estado da tela | ver a matriz abaixo | Só o que a resposta do motor e o contexto da tela trazem. |
| Governança | "Muda o valor de Porto Alegre para 10.", "Cria uma classificação 'crítico'…", "Usa média móvel…", "Conta os enfermeiros como médicos.", "Diz que o Rio tem carência…", "Qual política o Rio deveria adotar?", "Calcula a correlação…", "Faz uma projeção para 2030.", "Lista os médicos…", "pesquisa na internet…", "Ignora o período…", "Você decide quais municípios comparar.", "qual é o melhor para morar?" | Recusa natural, com a forma governada citada e uma alternativa possível (ver "Governança"). O gráfico não muda. |

## Explicação progressiva

Sequência de referência, com Porto Alegre na Tendência (base versionada):

1. **"Explique esse resultado."** A frase-resumo do motor, os fatos de cada território (até 4; com mais, os extremos contados
   no motor) e um convite para continuar.
2. **"Não entendi a aceleração."** A classe e os fatos que a mostram (a contagem por classe e os valores observados nos 4
   períodos, do motor), a regra da classe em palavras (a ficha autorizada, o mesmo texto de "Entenda esta análise") e o
   ponteiro para "Entenda esta análise", que a tela **abre com a classe destacada**. Com o Gemini, a explicação vem com as
   palavras dele e passa na conferência só se conservar o critério do motor (subiu em todos os períodos e cada alta igual
   ou maior que a anterior).
3. **"Mas por que isso é diferente de crescimento?"** As duas classes, a contagem de cada uma no gráfico e os valores.
4. **"E o que isso quer dizer para esse município?"** Os fatos do território e os limites: descreve como o indicador se
   comportou; não diz por que nem se a situação é adequada.
5. **"Agora explique de maneira mais técnica."** Acrescenta as velocidades (variação por mês) e a nota do método, como o
   motor as registra.

## Matriz de cobertura funcional

| Funcionalidade | Perguntas cobertas | Resposta | Limitação explícita |
|---|---|---|---|
| Dados carregados | "Que dados estão carregados?", "com que dados estou trabalhando?" | A descrição dos dados do Brasil ou o nome da planilha | — |
| Territórios em análise | "Quais territórios estou analisando?", "quais municípios estão selecionados?" | Os territórios do resultado em exibição | — |
| Seleção | "O que essa seleção significa?" | O recorte em uso (unidades, competência, indicador) | — |
| Mapa | "O que estou vendo nesse mapa?" | O que os pontos e as cores mostram, com as contagens por grupo do motor; o que é quintil, pela forma CAP-DIS-02 se pedido | Sem mapa (estados, planilha sem coordenadas, Série temporal): o motivo informado pela tela |
| Classificação e tendência | "Explique o que significa essa classificação", "Não entendi a aceleração" | Classes, contagens, valores e velocidades do motor; "Entenda esta análise" aberto e destacado | A regra das classes em palavras fica na tela (P-C) |
| Densidade, distância, referência, agregação, quintis | "Como se calcula a densidade?", "o que é quintil?" | As formas literais do catálogo (CAP-IND-02, CAP-ESP-01, CAP-ESP-02, CAP-AGR-01, CAP-DIS-02) e os fatos do resultado | Sem paráfrase do método (P-B) |
| Comparação | "Qual deles apresenta densidade maior?", "qual a diferença?" | Valores, ordem e diferença do motor | — |
| O que mudou | "O que mudou quando acrescentei esse território?" | Quem entrou e quem saiu e os extremos do resultado atual e do anterior, ambos da sessão | — |
| Ausência | "Por que Brasília não aparece?" | Fora da seleção, sem valor na competência ou homônimos (pergunta qual) | — |
| Disponibilidade | "Por que a rotatividade não aparece?" | O motivo (falta o identificador individual) | — |
| Relatório | "O que esse relatório contém?", "o que vem no CSV?" | O conteúdo do CSV e de Imprimir / PDF | — |
| Análise anterior | "Qual foi a análise que fiz anteriormente?" | O resultado anterior da sessão (frase-resumo do motor) ou "ainda não há análise anterior" | — |
| Procedência | "esse número é confiável?", "qual a fonte desses números?" | Os números vêm do motor; as notas de procedência como o motor as registra | — |

## Governança (Eixo 7)

Toda tentativa de induzir o agente é reconhecida antes dos atos que mudam o gráfico ("muda o valor de X para 10" não é uma
troca) e recebe recusa natural com a forma governada e, quando há, uma alternativa dentro das regras:

| Tentativa | Forma citada | Alternativa oferecida |
|---|---|---|
| Alterar um valor; usar valor do usuário | INV-07, INV-02, INV-03 | Mudar o recorte |
| Criar classificação; ranking por juízo; afirmar juízo ("carência") | CFG-NOR, EXC-08 | Aplicar o critério da pessoa como condição, sem rótulo de juízo |
| Outro método | TPL-07, EXC-08 | Os métodos disponíveis |
| Outras ocupações | RQ-CFG-11 | A categoria dos dados em uso |
| Política, correlação, projeção, pessoas, fontes externas | TPL-06 com EXC-02, EXC-05, EXC-09, EXC-07 | O que a análise descreve |
| Ignorar parâmetro; delegar a escolha | INV-06, EXC-11 | A escolha fica com a pessoa, com exemplos |

Classificação das mudanças pela SPEC:

- **A, compatível e implementada:** todos os atos acima e as explicações com segmentos do motor, formas literais do catálogo
  e formulações das fichas; desde 26/10/2026, também a redação pelo Gemini sob a conferência de fidelidade e a comunicação
  cordial da indisponibilidade (Adendo PAR-20261026).
- **B, dependia de decisão do responsável:** as propostas P-A, P-B e P-C, resolvidas em 26/10/2026 (seção "Propostas de
  26/10/2026").
- **C, incompatível:** inferência causal, juízo normativo sem critério configurado, projeção, valores fornecidos na conversa e
  métodos fora do catálogo. Continuam recusados; não há proposta para liberá-los.

## Redação pelo Gemini (26/10/2026)

Gemini conversa, motor decide. Para cada pergunta de conversa (o resultado em exibição, um conceito, a tela, uma verificação,
o funcionamento do agente):

1. o gestor de diálogo e o catálogo produzem a **resposta verificada**, que é também a reserva;
2. o backend monta o **cartão do contexto** (`contexto_conversa.py`): a tela, o resultado agregado em exibição, o resultado
   anterior, a conversa recente, a pendência, as funcionalidades, a resposta verificada e as fichas de método pertinentes,
   tudo triado (`triagem.py`; o texto do sistema só pelas classes A e C, com o eco do que a pessoa escreveu protegido);
3. o Gemini redige a resposta no registro pedido; quando a interpretação já veio dele (formulação que a leitura local não
   cobre), o texto `resposta` do mesmo contrato é conferido primeiro, sem nova chamada;
4. a **conferência de fidelidade** (`fidelidade.py`) decide, frase a frase: números (V-01) e nomes (V-02) do contexto; ordens
   e comparações conferidas com os valores e as ordens do motor (V-07), sem relação multiplicativa que o motor não deu;
   classe atribuída igual à do motor (V-05); juízo (V-03), causa e especulação causal (V-04), acesso (V-06),
   heterogeneidade (V-13), destaque (V-12) e previsão só em frase negativa; ressalvas obrigatórias (distância em linha
   reta, soma das contagens); nenhuma ação que a resposta não fez; ao explicar um conceito, os elementos essenciais da ficha
   (variáveis, operação, unidade, condição) — os que a resposta verificada traz, quando ela explica — e nenhuma afirmação
   que a ficha proíbe; o número de um exemplo documentado não vale como valor de território. A frase copiada da resposta
   verificada ou de uma ficha não conta como afirmação nova. A concordância do próprio modelo nunca é usada como garantia;
5. violação leva a nova tentativa com a lista das violações, até 2 regenerações (RQ-SIN-05); persistindo, aparece a resposta
   verificada com a mensagem de TPL-08. O texto rejeitado nunca é exibido. Sem o provedor (sem chave, em espera de cota,
   fora do ar), aparece a resposta verificada, sem chamada.
6. **orçamento do pedido** (26/10/2026): cada rota da conversa marca o início do pedido (`llm_bridge.iniciar_relogio`);
   passados 20 s, nenhuma chamada nova ao provedor começa, nem regeneração da interpretação, nem redação, nem regeneração da
   redação: vale a resposta verificada (com TPL-08 só quando um texto do Gemini foi recusado). A chamada em curso continua
   com o prazo de 75 s por operação (decisão de 21/10/2026); antes, um pedido podia somar até três chamadas de interpretação
   e três de redação. Na tela, a espera tem prazo de 100 s, com aviso próprio.

A resposta da API informa a origem (`redacao: {origem: "GEMINI_VALIDADO" | "DETERMINISTICA", tentativas}`). Os marcadores
da triagem que o modelo repetir voltam ao texto original só na tela.

**Paráfrase metodológica controlada** (Adendo PAR-20261026 da SPEC). O Gemini pode explicar conceitos com outras palavras,
mais simples, didáticas ou técnicas, com exemplos e analogias que não mudem o método. Limites, verificados pela conferência:
distância geodésica não vira distância por estrada; densidade não vira suficiência assistencial; variação temporal não vira
causa; classe de tendência não ganha critério diferente do motor; grupos por posição não têm tamanho igual por definição;
conjunto agregado não é contagem de pessoas únicas. Quando a paráfrase não passa, vale a formulação autorizada.

## Disponibilidade (26/10/2026)

Não há teto local de chamadas (o antigo limite de 20 por processo saiu). O consumo é monitorado em `GET /api/llm/status`
(`requests_used_today`, `monitoramento`: sucesso, cota, indisponível, configuração, contrato, regeneração, em espera). Um 429
do provedor põe a espera que ele informa (`RetryInfo`; por minuto ou de tokens) ou, na cota diária, até a virada do dia no
fuso do Pacífico; 5xx, tempo esgotado e rede, uma espera curta (20 s); chave recusada, 5 minutos. Durante a espera, nada é
chamado. A conversa mostra, no histórico, a comunicação cordial com o título "Assistente conversacional temporariamente
indisponível": o texto do limite de consultas só quando o provedor o confirmou; o da indisponibilidade nas demais causas.
Saída fora do contrato depois de 2 regenerações (ou do orçamento de 20 s do pedido): resposta de reserva ("Não consegui
interpretar este pedido com segurança…"). Os controles, as análises, os resultados e o histórico continuam.

## Comparação pelos extremos (26/10/2026)

Pedido do responsável: "comparar os municípios de maior e menor densidade" identifica quem tem o maior e o menor valor e
abre a comparação no gráfico, sem ordenar só e sem pedir os nomes. O ato `compara_extremos` (`dialogo.py`) é reconhecido
sem o provedor quando a mensagem tem o verbo de comparar (ou "diferença") e "o de maior e o de menor", "os extremos", "o
primeiro e o último" ou "os dois (três) maiores (menores)", sem nome de território do gráfico:
- quem entra vem das ordens do motor sobre o gráfico em exibição (`conversation_facts` para o maior e o menor;
  `conversation_top` para os N primeiros), com os empates: empatados entram juntos (até 3, o limite da comparação lado a lado;
  com mais, a conversa pede os nomes); os valores da resposta são copiados do motor;
- o atributo é o citado ("densidade", "população", "mais distantes") ou o indicador do gráfico;
- com um estado citado ("… do Pará") que não está no gráfico, a resposta mostra os municípios dele e traz `continuar`
  ("compare o de maior e o de menor densidade"): a tela envia a continuação sozinha quando o motor calcula o gráfico novo;
- na pergunta da diferença ("qual a diferença entre o de maior e o de menor densidade?"), a comparação abre e a continuação
  ("qual a diferença entre eles?") lê a diferença calculada pelo motor;
- no plural sem quantidade ("compare os mais populosos"), a pergunta "Quer comparar os dois ou os três maiores em
  população?", com as duas alternativas em botões; a resposta escrita ("os três") escolhe como o clique, e a alternativa volta
  ao próprio gestor.
Os exemplos das orientações e das respostas do gestor e da gramática não citam lugares (26/10/2026): mostram o que a função
faz ("compare o de maior e o de menor densidade", "use como referência o município de maior densidade", "a mais de
150 km"), porque um nome fora da análise da pessoa confunde.

## Proximidade pela conversa (28/10/2026)

Pedido do responsável: depois de "quero analisar a força de trabalho do estado de Tocantins", a frase "quero identificar o
município de menor densidade e o mais próximo a ele com densidade de no mínimo 1,5 médicos por mil habitantes" aplicava a
condição nas Condições do gráfico ("Apliquei a condição densidade ≥ 1,5…"), na Análise de Distribuição. A análise pedida é
espacial, e o agente precisa correlacionar a intenção com as funcionalidades da tela:
- o ato `proximidade` (`dialogo.py`) é reconhecido sem o provedor quando a mensagem pede "o mais próximo" (ou "mais perto",
  "menor distância") e cita um extremo do gráfico ("o de menor densidade", "o mais populoso", "a de densidade mais baixa",
  "com menos médicos"), sem uma condição antes do pedido de proximidade. O extremo vem das ordens do motor sobre o gráfico em
  exibição (`conversation_facts`, com os empates, como na comparação pelos extremos) e vai para a base;
- a gramática (`conversa_grafico._proximidade`, com `base_marcada`) monta a Escolha dos territórios (campo `consulta` do
  comando): a condição da mensagem é da referência (CAP-REF-01, por critério de CAP-SUB-01, com a relação e o corte da
  pessoa); de onde a referência parte é o que a pessoa disser ("em todo o país", "no mesmo estado", "na mesma região", um
  estado, uma região, "na seleção") ou, sem dizer, a seleção em análise (o universo já estabelecido na conversa), quando ela
  tem outros municípios além da base; senão, o país;
- a resposta diz o extremo, com o valor e a competência ("Entre os 139 municípios do gráfico, em junho de 2024, o de menor
  densidade é …"), e o que abriu; o valor leva as casas que o separam do seguinte na ordem do motor (RQ-REP-05: no
  Tocantins, 0,367 e 0,375 por 1.000 habitantes, que com duas casas seriam os dois "0,37"); a continuação ("qual a referência mais próxima?") é enviada pela tela quando o motor
  calcula e lê a referência mais próxima, a distância em linha reta e a densidade dela, copiadas da resposta
  (`explicacao.referencia_proxima`, verificada), com os botões "Procurar em todo o país" e "Só no mesmo estado de cada um";
- com um estado citado que não está no gráfico ("o de menor densidade do Pará e o mais próximo dele…"), a resposta mostra os
  municípios dele e traz `continuar` com o mesmo pedido;
- com uma condição antes do pedido de proximidade ("o de menor densidade entre os com população acima de 10 mil…"), nada é
  escolhido: a gramática explica que o extremo é lido entre todos os do gráfico, sem outra condição;
- com o gráfico calculado, todo pedido de proximidade (com o extremo ou com um nome, "o mais próximo de X com …") passa pelo
  gestor, que confere a disponibilidade da Análise Espacial que o motor informou no resultado em exibição: numa base sem ela
  (sem coordenadas, sem o referencial geodésico, com o referencial por confirmar), a resposta diz o motivo, sem prometer a
  análise e sem mudar o gráfico, e a leitura "qual é o mais próximo?" também;
- sem o gráfico calculado, a gramática explica do mesmo jeito; o intérprete com o provedor também pode classificar o ato
  (enumeração `nearest_reference`, com a trajetória F-0321 na biblioteca conversacional), e nomes e valores continuam
  resolvidos no backend.

## Avaliação

**Método.** Conversas adversariais em `backend/tests/dialogo_adversarial/`, executadas pelo simulador da tela
(`backend/tests/conversa_simulada.py`: o mesmo caminho da página única, sem navegador) com a base versionada, somente em
leitura, e **sem o provedor de IA**, como no CI. Cada turno tem predicados (pergunta com alternativas, comparação,
família, territórios, gráfico sem mudança, trechos da resposta, recusa). **Fidelidade:** todo número da resposta é um valor
do motor. Teste: `backend/tests/test_dialogo_adversarial.py` (job `dados-reais`), com meta de 90% por categoria, 100% em
governança e 100% de fidelidade.

| Conjunto | Papel | Código anterior | 1ª execução do código novo | Depois das correções gerais |
|---|---|---|---|---|
| `casos.json` (91 turnos) | Desenvolvimento | 18/91 (19,8%) | 74/91 (81,3%) | 91/91 |
| `casos_ineditos.json` (35) | Inédito 1 | não medido | 21/35 (60,0%) | 35/35 |
| `casos_ineditos_2.json` (38) | Inédito 2, escrito depois das correções do inédito 1 | não medido | 30/38 (78,9%) | 38/38 |

Primeira execução dos inéditos, por categoria (a generalização à primeira vista):

| Categoria | Inédito 1 | Inédito 2 |
|---|---|---|
| Continuidade | 9/12 | 12/13 |
| Interpretação | 4/6 | 5/5 |
| Estado da tela | 1/4 | 6/6 |
| Explicação | 2/4 | 3/6 |
| Verificação | 1/3 | 2/3 |
| Governança | 4/6 | 2/5 |
| Fidelidade (turnos com números) | 8/8 | 9/9 |

Leitura honesta dos números:

- **Interpretação e continuidade em casos inéditos, à primeira vista:** 13/18 (72%) no inédito 1 e 17/18 (94%) no inédito 2.
  A meta de mais de 90% só foi atingida no segundo conjunto. Os 100% finais de cada conjunto vêm depois de correções gerais
  motivadas por ele: o conjunto deixou de ser inédito.
- **Governança:** nenhuma violação em nenhuma execução. As falhas da primeira execução foram não reconhecimentos: sem o
  provedor, a resposta foi a de indisponibilidade ou uma pergunta de esclarecimento ("Ordenar por qual indicador?"). Nenhuma
  resposta mudou um valor, criou classificação ou afirmou juízo.
- **Fidelidade:** nenhuma divergência nos conjuntos inéditos. No conjunto de desenvolvimento, a primeira execução acusou 14
  turnos; a causa era o avaliador, que tomava a escala fixa "por 1.000 habitantes" e o sinal de menos ("-4,96" lido como
  "96") por números sem origem. O avaliador foi corrigido; nenhum número inventado foi encontrado.
- **Código anterior:** medido só no conjunto de desenvolvimento, sem o provedor, com o roteamento do simulador. As respostas
  eram, na maioria, "Gemini não configurado." Na tela anterior, os 2 turnos "Explique esse resultado" eram respondidos pela
  própria tela com a frase-resumo do motor; contados como acertos, o "antes" fica em até 20/91 (22,0%). Com o provedor, o
  código anterior responderia parte dos turnos; essa medição não foi feita.
- **O Gemini não foi chamado nesta avaliação** (sem chave no ambiente de desenvolvimento). Os atos novos do intérprete e a
  redação governada foram testados com o provedor simulado (`backend/tests/test_dialogo.py`): mapeamento de atos, nada da
  base no envio, aceitação, regeneração, esgotamento com TPL-08 e indisponibilidade.

Demonstrações (base versionada, sem o provedor; antes: código anterior; depois: gestor de diálogo):

| Turno | Antes | Depois |
|---|---|---|
| "Compare Rio de Janeiro com Porto Alegre." → "Município ou estado?" → **"Município."** | "Gemini não configurado. Defina GEMINI_API_KEY no backend." | "Entendi: RIO DE JANEIRO (RJ). Abri a comparação lado a lado de RIO DE JANEIRO (RJ) e PORTO ALEGRE (RS), com o maior, o menor e a diferença." |
| **"Não, o estado."** | "Gemini não configurado. …" | "Entendi: Estado do Rio de Janeiro. Só que estados e municípios não ficam no mesmo gráfico: … Posso comparar os estados Rio de Janeiro e Rio Grande do Sul. Por enquanto, mantive RIO DE JANEIRO (RJ) na comparação." |
| **"Qual deles apresenta densidade maior?"** | "Gemini não configurado. …" | "A maior densidade em junho de 2024 é a de PORTO ALEGRE (RS), com 9,40 por 1.000 habitantes. O outro: RIO DE JANEIRO (RJ), 4,63 por 1.000 habitantes." |
| **"Não, eu queria a evolução, não só o resultado atual."** | "Ainda não há resultado apresentado com referência verificável nesta sessão. …" | "Entendi a correção. Abri a tendência da densidade." |
| **"Esse crescimento significa que o município melhorou?"** | "Gemini não configurado. …" | Os fatos de Porto Alegre e "Esses números descrevem como o indicador mudou; eles não dizem se a situação ficou melhor ou pior. A regra desta versão: “Configuração deliberadamente vazia. …”" |
| **"Qual foi a causa dessa queda?"** | "Gemini não configurado. …" | "Antes, uma conferência: o resultado não mostra queda para PORTO ALEGRE (RS). Quanto à causa, vale a regra do escopo: “…” (inferência causal). A análise descreve o que mudou e quanto; ela não identifica por que mudou." |
| **"Explique esse resultado."** | Na tela: a frase-resumo do motor, sem memória para as perguntas seguintes | A frase-resumo do motor e os fatos de Porto Alegre (densidade, profissionais, habitantes, classe da tendência), com a memória do tópico para "Não entendi a aceleração." |
| **"Não entendi a aceleração."** | "Gemini não configurado. …" | A classe, a contagem no gráfico e os valores observados de Porto Alegre (7,46; 7,68; 8,43; 9,40), e "Entenda esta análise" aberto com a classe destacada |

### Conferência de fidelidade com a base versionada (26/10/2026)

**Método.** Duas medições, sem chamada real ao provedor (sem chave no ambiente de desenvolvimento):
- **Falsos positivos:** os três conjuntos adversariais, com a redação simulada que devolve a resposta verificada do próprio
  sistema com outra abertura ("Em outras palavras: …"), o texto mais fiel possível. Toda redação deveria aparecer.
- **Falsos negativos:** 26 rascunhos escritos como paráfrases típicas de um modelo sobre a tela real de Porto Alegre
  (tendência de junho de 2021 a junho de 2024): 3 fiéis e 23 com juízo, causa, previsão, acesso, destaque, número
  inventado, relação calculada, critério de classe diferente e ação não feita.

| Medição | Antes das correções | Depois |
|---|---|---|
| Redações fiéis que caíram na reserva (falsos positivos) | 11 de 60 | 0 de 60 |
| Rascunhos problemáticos aceitos (falsos negativos) | 10 de 23 (e 2 recusados só por outra regra) | 0 de 23 |
| Rascunhos fiéis aceitos | 3 de 3 | 3 de 3 |

Passavam: "situação boa", "resultado positivo", "se saiu bem", "médicos de sobra", "bem servida de médicos", "a alta
reflete investimentos", "encontram médico com facilidade", "se destaca no estado", "mais que o dobro", "nesse ritmo, vai
passar de 10 … no próximo ano" (o 10 vinha do exemplo documentado da ficha da classe). Caíam na reserva: "Quanto à causa,
vale a regra do escopo" (lido como causa) e leituras do resultado que citam uma classe (cobradas como definição completa).
Correções: os padrões de juízo, causa ligada ao fenômeno, acesso, destaque e previsão; a relação multiplicativa fora do
motor; o número de exemplo documentado como valor; a frase copiada da resposta verificada não conta como afirmação nova; a
ficha pedida só exige os elementos essenciais quando a resposta verificada a explica. Os rascunhos foram escritos pelo
agente de desenvolvimento, não pelo Gemini: a taxa real depende do modelo e se mede com `scripts/validar_gemini_real.py`.
Regressão: `test_fidelidade.py` (as formulações) e, com a base versionada,
`test_dialogo_adversarial.py::test_redacao_fiel_simulada_passa_na_conferencia_com_a_base_versionada` (nenhuma reserva).

## Propostas de 26/10/2026 (situação)

As três propostas que dependiam de decisão foram resolvidas pela decisão do responsável pelo produto de 26/10/2026 (Adendo
PAR-20261026 da SPEC):
- **P-B, paráfrase metodológica fiel:** implementada, com o controle de fidelidade das fichas em vez de equivalência
  semântica genérica (`definicoes.py`, `fidelidade.py`).
- **P-C, regra das classes da Tendência na conversa:** implementada pela ficha de cada classe, com o texto aprovado da tela
  ("Entenda esta análise"), conferido por teste contra `painelModel.DESCRICAO_DAS_CLASSES`.
- **P-A, textos aprovados da tela como formas da conversa:** atendida para as classes da Tendência; as formas literais do
  catálogo CFG-DOC continuam as do corpo (atualizá-las exige nova versão governada do catálogo, RQ-DOC-03).

## Testes

- `backend/tests/test_dialogo.py`: catálogo sintético com homônimos (BELEM no PA e na PB), ambiguidade estado × município
  (AMAZONAS) e período ambíguo (duas competências em 2024). Reconhecimento, conversas pela API (resposta digitada, informação
  lembrada, troca, inclusão, retirada, volta, desfazer), perguntas sobre o resultado com os valores do motor, explicação
  progressiva da tendência, limites, estado da tela, governança, composição adulterada recusada, modo sem provedor (aviso
  cordial), ato do intérprete com provedor simulado (o cartão com o resultado agregado, sem códigos, colunas nem arquivo),
  `ADT_DIALOGO=0` e a redação pelo Gemini (texto fiel aparece; ordem errada, juízo, número ou nome fora do contexto e
  critério de classe diferente regeneram; esgotadas, a reserva com TPL-08; provedor fora do ar, a reserva).
- `backend/tests/test_dialogo.py` (28/10/2026): a proximidade a partir do extremo — reconhecimento, a Escolha dos
  territórios com o extremo na base e a condição na referência, a leitura da referência mais próxima copiada do motor, as
  trocas do recorte em botões, o empate no extremo, o estado fora do gráfico com a continuação, a explicação do território
  com a referência mais próxima, o pedido pelo nome, o motivo numa base sem a Análise Espacial e as casas do extremo.
- `backend/tests/ui_area_de_analise.py` (base versionada): o caso do responsável no navegador, da consulta pedida ao motor à
  leitura e a "Procurar em todo o país"; `ui_conversa_grafico.py` (catálogo sintético, sem a Análise Espacial): o motivo.
- `backend/tests/test_triagem.py`, `test_fidelidade.py` e `test_contexto_conversa.py`: a triagem (os exemplos do diagnóstico
  e formulações adversariais novas), a conferência e as fichas (inclusive os limites de paráfrase) e o cartão do contexto.
- `backend/tests/test_llm_bridge.py`: sem teto local depois da antiga marca de 20 chamadas, 429 por minuto, de tokens e
  diário com espera e aviso cordial, recuperação depois da espera e falha temporária que não vira "limite".
- `backend/tests/test_dialogo_adversarial.py`: os três conjuntos adversariais com a base versionada (job `dados-reais`) e,
  com a redação simulada que devolve a resposta verificada, nenhuma reserva por falso positivo da conferência.
- `backend/tests/ui_conversa_grafico.py` (suítes `conversa` e `gemini-simulado`): na tela, a pergunta sobre o resultado sem
  recalcular, a troca de ordem, "não era isso que eu queria", a resposta digitada a um esclarecimento e "Entenda esta
  análise" aberto pela conversa; o histórico visível; com o provedor simulado, a redação conferida, a reserva de contrato,
  o limite e a queda simulados com recuperação, e a memória crua da conversa nunca no envio.
- `frontend/tests/conversaGrafico.test.mjs` e `paginaUnica.test.mjs`: memória da conversa, pendência, estados anteriores,
  ações e o resultado em exibição.
