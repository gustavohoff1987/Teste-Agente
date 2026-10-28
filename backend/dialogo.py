"""Gestor de diálogo da página única (desafio adversarial, 26/10/2026): memória operacional, continuidade, verificação,
explicação e governança da conversa, antes da gramática local (conversa_grafico.py) e do intérprete com o provedor.

Interpreta e explica; nunca calcula. A conversa da tela manda, em `conversa`, a memória que ela guarda: a pendência de
esclarecimento (a pergunta, o pedido original e as alternativas), os estados anteriores do gráfico aplicados pela conversa
e a memória que a resposta anterior devolveu (o último ato, a explicação em curso, a escolha já feita e as alternativas
restantes). Com ela, o gestor reconhece, sem o provedor:
- a resposta digitada a um esclarecimento ("Município.", "a do Paraná", "o primeiro", "junho"), que retoma o pedido
  original com a alternativa escolhida, e a correção da escolha ("Não, o estado.");
- atos de continuidade: desfazer ("não era isso"), voltar a um estado anterior ("volta para a comparação anterior"),
  trocar ("troca o primeiro pelo segundo", "troca X por Y"), incluir ("inclui mais um", que pergunta qual), tirar,
  ampliar a todos ("e se considerarmos todos?");
- perguntas sobre o resultado em exibição ("qual deles tem densidade maior?", "e a população?", "qual a diferença?",
  "quantos municípios?"), respondidas com os valores e as ordens do motor (explicacao.py);
- a comparação pelos extremos ("compare o de maior e o de menor densidade", "compare os dois maiores", "os extremos lado a
  lado", "qual a diferença entre o maior e o menor?", 26/10/2026): quem entra vem das ordens do motor
  (painel.conversation_facts e conversation_top), com os empates; com um estado citado que não está no gráfico, a resposta
  mostra os municípios dele e a tela segue com a comparação (`continuar`) quando o motor calcula; na pergunta da diferença, a
  tela pede a leitura dela quando o motor calcula; no plural sem quantidade ("compare os mais populosos"), a conversa
  pergunta se são os dois ou os três;
- pedidos de explicação progressiva (o resultado, um território, um termo; objetivo, simples, didático ou técnico);
- verificações (causa, juízo normativo, melhora, acesso, procedência) e perguntas sobre o estado da tela (dados,
  territórios, seleção, mapa, relatório, análise anterior, o que mudou, por que algo não aparece);
- tentativas de induzir respostas indevidas (mudar um valor, criar classe ou método, reconhecer outra ocupação, afirmar
  carência, recomendar política, correlacionar, projetar, listar pessoas, ignorar parâmetro, delegar a escolha).
O intérprete com o provedor (llm_bridge) devolve os mesmos atos para as formulações que o reconhecimento local não cobre.
Os comandos do gráfico continuam com a gramática local; os números vêm do motor. Desde 26/10/2026, nas perguntas de
conversa (o resultado, um conceito, a tela, uma verificação), a resposta daqui é a resposta verificada e a reserva: com o
provedor disponível, o Gemini a recebe no cartão do contexto e redige com as palavras dele, sob a conferência de
fidelidade (main._turno_do_dialogo, conversa_gemini.py). A memória da conversa e o resultado completo ficam no backend;
ao provedor vão o cartão triado e a janela da conversa (contexto_conversa.py).
"""
from __future__ import annotations

import os
import re
import unicodedata

import explicacao
from document_catalog import materialize
from territorial_selection import STATES

VERSAO = 1
ESTADOS_POR_NOME = {}
for _codigo, (_sigla, _nome) in STATES.items():
    ESTADOS_POR_NOME["".join(c for c in unicodedata.normalize("NFD", _nome.lower()) if not unicodedata.combining(c))] = \
        _codigo
SIGLAS = {sigla.lower(): codigo for codigo, (sigla, _) in STATES.items()}
MESES = ("janeiro", "fevereiro", "marco", "abril", "maio", "junho", "julho", "agosto", "setembro", "outubro", "novembro",
         "dezembro")
ORDINAIS = {"primeir": 0, "segund": 1, "terceir": 2, "quart": 3, "quint": 4, "sext": 5, "1": 0, "2": 1, "3": 2, "4": 3,
            "5": 4, "6": 5, "um": 0, "dois": 1, "tres": 2}
VAZIAS = frozenset("o a os as um uma de do da dos das no na nos nas e em por para pra pro com que eu quero queria prefiro "
                   "esse essa este esta isso aquele aquela era foi sim nao opcao alternativa favor ai la entao mesmo "
                   "acho seria".split())


def ativo() -> bool:
    """ADT_DIALOGO=0 desliga o gestor: a conversa volta a ser exatamente a anterior (gramática e intérprete)."""
    return os.getenv("ADT_DIALOGO", "1").strip() != "0"


def dobra(texto: str) -> str:
    simples = "".join(c for c in unicodedata.normalize("NFD", str(texto).lower()) if not unicodedata.combining(c))
    return " ".join(re.sub(r"[^\w%,.:/()\-]+", " ", simples).replace("_", " ").split())


def palavras(texto: str) -> list[str]:
    return re.findall(r"[a-z0-9]+", dobra(texto))


# --------------------------------------------------------------------------------------------- padrões
NEGACAO_INICIAL = re.compile(r"^(?:nao|na verdade|errado|negativo|nada disso|eu quis dizer|quis dizer|me referia|"
                             r"era|eu queria|queria)\b")
DESFAZER = re.compile(r"\b(?:nao (?:e|era|foi) (?:isso|bem isso|o que eu (?:queria|pedi))|nao era isso que eu queria|"
                      r"nao foi isso que (?:eu )?pedi|nao e isso|errou|esta errado|ta errado|nao quero isso|"
                      r"desfaz(?:er)?|desfaca)\b")
VOLTA = re.compile(r"\b(?:volt[ae]r?|volta|retorn[ae]r?|retorna|regress[ae])\b")
ANTES = re.compile(r"\b(?:anterior|antes|estava|de novo como)\b")
ALVO_DA_VOLTA = re.compile(r"\b(?:comparac(?:ao|oes)|analise|selecao|grafico|tendencia|distribuicao|recorte|mapa|estado|"
                           r"como estava)\b")
TROCA = re.compile(r"\b(?:troc[ae]r?|troca|substitu(?:i|a|ir|ia)|permut[ae]|inverte|inverta|inverter)\b|\bem vez de\b|"
                   r"\bno lugar de\b")
INCLUI = re.compile(r"\b(?:inclu(?:i|a|ir)|acrescent(?:a|e|ar)|adicion(?:a|e|ar)|poe|ponha|bota|coloca|coloque|junta)\b")
MAIS_UM = re.compile(r"\b(?:mais|outro|outra) (?:um|uma|municipio|cidade|territorio|estado)?\b|\bmais um\b|\boutro\b")
TIRA = re.compile(r"\b(?:tir[ae]r?|tira|retir[ae]r?|remov[ae]r?|exclu(?:i|a|ir)|apag[ae]r?|apaga|elimin\w*|"
                  r"deix[ae] de fora|some com|descart\w*)\b")
TODOS = re.compile(r"\b(?:tod[oa]s|considerarmos todos|considerando todos|com todos|pra todos|para todos)\b")
DEIXIS = re.compile(r"\b(?:deles|delas|dos dois|das duas|dos tres|entre eles|entre elas|desses|destes|dessas|destas|"
                    r"os dois|as duas|esses dois|essas duas|desse|deste|dessa|desta|nesse|neste|um do lado do outro)\b")
PERGUNTA = re.compile(r"^(?:e |mas |entao |agora |afinal )*(?:qual|quais|quem|onde|que municipio|que cidade|que estado|"
                      r"quanto|quantos|quantas|em qual|o que|por que|porque|pq|como|sera)\b|\?\s*$")
MAIOR = re.compile(r"\b(?:maior(?:es)?|mais alt[oa]s?|mais (?:medicos|profissionais|gente|populos[oa]|habitantes|longe|"
                   r"distante)|lidera|na frente|ganha|supera|primeiro lugar|topo)\b|\bmais\b")
MENOR = re.compile(r"\b(?:menor(?:es)?|mais baix[oa]s?|menos|fica atras|perde|ultimo lugar|mais perto|mais proxim[oa])\b")
ATRIBUTOS = (("densidade", re.compile(r"\b(?:densidades?|por habitante|por mil|por cada mil|a cada mil|por 1\.?000|"
                                      r"per capita|proporcional|proporcionalmente)\b")),
             ("populacao", re.compile(r"\b(?:populac(?:ao|oes)|habitantes|populos[oa]s?|gente|moradores)\b")),
             ("distancia_km", re.compile(r"\b(?:distancias?|longe|perto|distante|proxim[oa])\b")),
             ("variacao", re.compile(r"\b(?:variac(?:ao|oes)|cresceu mais|caiu mais|mudou mais)\b")),
             ("permanencia", re.compile(r"\b(?:permanencia|rotatividade|ficaram|sairam)\b")),
             ("quantidade", re.compile(r"\b(?:quantidades?|quantitativos?|numero de (?:medicos|profissionais)|"
                                       r"profissionais|medicos|total de)\b")))
# Comparação pelos extremos do gráfico (26/10/2026): o verbo de comparar e "o de maior e o de menor", "os extremos", "o
# primeiro e o último" ou "os dois/três maiores (menores)", sem nomes de território.
COMPARA = re.compile(r"\b(?:compare|comparar|compara|comparacao|comparando|confronte|confrontar|contraste|contrastar|"
                     r"versus|vs)\b|\blado a lado\b|\bum (?:do|ao) lado do outro\b|\bfrente a frente\b")
EXTREMO_ALTO = re.compile(r"\bmaior(?:es)?\b|\bmais (?:alt|populos|distant|longe|medic|profission|habitant)\w*")
EXTREMO_BAIXO = re.compile(r"\bmenor(?:es)?\b|\bmenos (?:populos|distant|medic|profission|habitant)\w*|"
                           r"\bmais (?:baix|proxim|perto)\w*")
EXTREMOS = re.compile(r"\bextremos\b|\bprimeir[oa] e (?:o |a )?ultim[oa]\b")
PRIMEIROS_N = re.compile(r"\b(?:os|as) (dois|duas|2|tres|3) (?:\w+ ){0,3}?(maior(?:es)?|menor(?:es)?|mais|menos|primeir[oa]s|"
                         r"ultim[oa]s)\b")
QUANTOS_N = {"dois": 2, "duas": 2, "2": 2, "tres": 3, "3": 3}
# No plural, sem quantidade ("compare os mais populosos", "compare os municípios de maior densidade"): a conversa pergunta se
# são os dois ou os três, com as duas alternativas em botão.
EXTREMOS_NO_PLURAL = re.compile(r"\b(?:os|as) (?:\w+ ){0,2}?(?:maiores|menores|(?:mais|menos) \w+s|(?:de|com) (?:maior|menor))\b")
DIFERENCA = re.compile(r"\b(?:diferenca|quanto a mais|quanto maior|quanto menor|distancia entre os valores)\b")
CONTAGEM = re.compile(r"\bquant[oa]s (?:municipios|territorios|estados|cidades|itens|unidades|bolhas|lugares)\b")
EXPLICA = re.compile(r"\b(?:explique|explica|explicar|explicacao|me explica|entender|entendi|compreend\w*|"
                     r"nao ficou claro|como assim|o que (?:e|sao|significa|significam|quer dizer|querem dizer)|"
                     r"que significa|significado|traduz\w*|simplific\w*|reformul\w*|outras palavras|outro jeito|"
                     r"outra forma|outra maneira|mais simples|mais tecnic\w*|tecnicamente|didatic\w*|passo a passo|"
                     r"por partes|leigo|dia a dia|cotidian\w*|sem termos tecnicos|detalh\w*|aprofund\w*|"
                     r"como (?:isso |ele |ela |esse valor |essa classe )?(?:e|foi|sao|foram) (?:calculad\w*|feit\w*|definid\w*)|"
                     r"como se calcula|como (?:e que )?(?:o motor |o sistema |voce )?calcula|como funciona|resum\w*|"
                     r"sintetiz\w*|me ajuda a entender)\b")
REGISTRO_SIMPLES = re.compile(r"\b(?:simples|simplific\w*|leigo|dia a dia|cotidian\w*|sem termos tecnicos|facil|claro|"
                              r"crianca|nao entendi|nao ficou claro|como assim|qualquer pessoa|todo mundo entenda|"
                              r"linguagem comum|sem jargao)\b")
REGISTRO_DIDATICO = re.compile(r"\b(?:didatic\w*|passo a passo|por partes|com calma|com exemplo|exemplo|melhor)\b")
REGISTRO_TECNICO = re.compile(r"\b(?:tecnic\w*|metodolog\w*|rigor\w*|formal|aprofund\w*|preciso|precisao|detalh\w*)\b")
REGISTRO_OUTRO = re.compile(r"\b(?:outro jeito|outras palavras|outra forma|outra maneira|reformul\w*|de novo)\b")
TERMOS = (("aceleracao", re.compile(r"\b(?:aceleracao|acelera\w*|ganhou ritmo|ganhar ritmo)\b")),
          ("desaceleracao", re.compile(r"\b(?:desaceleracao|desacelera\w*|perdeu ritmo|perder ritmo)\b")),
          ("crescimento", re.compile(r"\b(?:crescimento|crescer|cresceu|crescendo)\b")),
          ("declinio", re.compile(r"\bdeclinio\b")),
          ("sem_classificacao", re.compile(r"\bsem classificacao\b")),
          ("velocidade", re.compile(r"\bvelocidades?\b")),
          ("quintil", re.compile(r"\b(?:quintis|quintil|quartis|quartil|decis|decil|grupos? por posicao|classes? de posicao|"
                                 r"pontos? de corte)\b")),
          ("densidade", re.compile(r"\bdensidade\b")),
          ("distancia", re.compile(r"\b(?:distancia|geodesica|linha reta)\b")),
          ("referencia", re.compile(r"\breferencia mais proxima\b")),
          ("agregacao", re.compile(r"\b(?:agregacao|conjunto|juntar|soma dos componentes)\b")))
CLASSIFICACAO = re.compile(r"\b(?:classificac(?:ao|oes)|classe|classes|categoria do grafico|cores?)\b")
RESULTADO = re.compile(r"\b(?:resultado|resultados|isso|esse grafico|este grafico|essa analise|esta analise|grafico|"
                       r"o que aparece|ultimo resultado)\b")
TERRITORIO_DEIXIS = re.compile(r"\b(?:para (?:esse|este|o) (?:municipio|territorio|estado|lugar)|pra (?:esse|este) "
                               r"(?:municipio|territorio)|nesse municipio|neste municipio|desse municipio|"
                               r"deste municipio|para ele|pra ele|no caso dele|para essa cidade|pra essa cidade)\b")
CAUSA = re.compile(r"\b(?:por que|porque|pq|por qual motivo|qual (?:foi |e )?(?:a )?(?:causa|razao|motivo)|causa|causou|"
                   r"causar|motivo|razao|devido|por causa|culpa|o que levou|o que fez|o que explica|efeito de|"
                   r"impacto)\b")
FENOMENO = re.compile(r"\b(?:subiu|subida|caiu|queda|aumento|aumentou|alta|reducao|reduziu|cresceu|crescimento|diminuiu|"
                      r"mudou|piorou|melhorou|tem mais|tem menos|e maior|e menor|ficou|declinio|acelerou|desacelerou|"
                      r"pandemia)\b")
NORMATIVO = re.compile(r"\b(?:suficientes?|insuficientes?|falta(?:m)? (?:de )?(?:medicos|profissionais)|faltam|"
                       r"excesso|sobra(?:m)?|carencia|deficit\w*|adequad[oa]s?|inadequad[oa]s?|ideal|critic[oa]s?|"
                       r"bom ou ruim|e bom|e ruim|ta bom|esta bom|preocupante|grave|precisa de mais)\b")
MELHORA = re.compile(r"\b(?:melhorou|piorou|melhora|piora|ficou melhor|ficou pior|e positivo|e negativo|evoluiu bem|"
                     r"melhor|pior|melhores|piores|mais bem|mais mal)\b")
JULGAMENTO = re.compile(r"\b(?:significa|quer dizer|mostra|indica|prova|entao|melhorou|piorou|da pra dizer|da para dizer|"
                        r"pode(?:mos)? dizer|posso dizer|e correto dizer|e certo dizer|esta (?:melhor|pior)|e (?:melhor|pior)|"
                        r"ta (?:melhor|pior)|fica (?:melhor|pior)|sai (?:melhor|pior))\b")
ACESSO = re.compile(r"\b(?:tempo de (?:viagem|deslocamento)|quanto tempo|leva (?:pra|para) chegar|chegar la|estradas?|"
                    r"rodovi\w*|de carro|a pe|acesso|acessibilidade|percurso|trajeto|(?:facil|dificil) (?:de )?chegar|"
                    r"chegar (?:de|ate|em|a)|ir de|se deslocar|deslocamento|perto de verdade)\b")
PROCEDENCIA = re.compile(r"\b(?:de onde (?:vem|veio|vieram|sai|saem|sao)|da onde vem|fonte d(?:esse|este|esses|estes|"
                         r"essa|esta|essas|estas|o|os|a|as) (?:numeros?|valores?|dados?|resultados?)|tem certeza|confiave(?:l|is)|"
                         r"posso confiar|da pra confiar|esta certo|ta certo|confere|como (?:voce )?sabe|quem calculou|"
                         r"como chegou)\b")
ANTERIOR_REFERENCIA = re.compile(r"\b(?:falando d[ao]|me referia|referindo|falava d[ao]|era sobre|perguntei sobre|"
                                 r"estava perguntando)\b.*\b(?:anterior|antes|outr[ao]|primeir[ao])\b")
DADOS = re.compile(r"\b(?:(?:que|quais) (?:dados|base|fonte)|dados (?:estao )?carregados|(?:que|qual) base|"
                   r"de onde (?:vem|sao) os dados|estou usando (?:que|quais) dados|fonte dos dados)\b")
TERRITORIOS = re.compile(r"\b(?:quais|que) (?:territorios|municipios|estados|cidades|lugares|unidades) (?:estou|estao|"
                         r"tem|ha|aparecem|vejo|eu estou|foram)\b|\bquem (?:esta|aparece) no grafico\b|"
                         r"\b(?:territorios|municipios) (?:selecionados|no grafico|em analise)\b")
SELECAO = re.compile(r"\b(?:essa|esta|a|minha) selecao\b|\bselecao (?:significa|quer dizer)\b")
MAPA = re.compile(r"\b(?:mapa|cores|pontos|bolinhas)\b")
RELATORIO = re.compile(r"\b(?:relatorio|csv|exporta\w*|pdf|imprimir|impressao|baixar|download)\b")
ANALISE_ANTERIOR = re.compile(r"\b(?:analise|resultado|grafico) (?:que (?:eu )?fiz|anterior|de antes|passad[ao])\b|"
                              r"\bo que (?:eu )?fiz antes\b")
MUDOU = re.compile(r"\bo que mudou\b|\bmudou o que\b|\bque diferenca fez\b")
NAO_APARECE = re.compile(r"\b(?:nao aparece|nao apareceu|nao esta|nao ta|sumiu|ficou de fora|nao entrou|nao tem|"
                         r"nao mostra|nao veio|nao esta disponivel|nao funciona|desabilitad\w*|nao abre|nao da)\b")
FAMILIAS_DISPONIVEIS = (("rotatividade", re.compile(r"\brotatividade\b")),
                        ("espacial", re.compile(r"\b(?:analise espacial|espacial|distancia)\b")),
                        ("tendencia", re.compile(r"\btendencia\b")), ("estados", re.compile(r"\bnivel (?:dos )?estados\b")))
# Governança (CFG-EXC e regras de autoridade): sinais que levam à recusa governada com alternativa útil.
GOV = (
    ("alterar_valor", re.compile(r"\b(?:mud[ae]r?|alter[ae]r?|troc[ae]r?|coloc[ae]r?|bot[ae]|corrig[ei]r?|ajust[ae]r?|"
                                 r"substitu\w*|consider[ae]r?|ponha|poe|edit[ae]r?)\b.*\b(?:valor|numero|resultado|densidade|"
                                 r"quantidade|populacao|total|taxa)\b.*\b(?:para|pra|como|em|por|=)\s*\d")),
    ("valor_do_usuario", re.compile(r"\b(?:consider\w*|supo\w*|assum\w*|imagin\w*|faz de conta|digamos)\b.*\b(?:populacao|"
                                    r"quantidade|valor|densidade|numero|total)\b.*\b(?:e|eh|seja|fosse|vale|igual a|de)\s+\d")),
    ("ranking_de_juizo", re.compile(r"\b(?:qual|quais|que) (?:e |sao )?(?:o |a |os |as )?(?:melhor(?:es)?|pior(?:es)?) "
                                    r"(?:municipios?|cidades?|estados?|lugar(?:es)?|regi(?:ao|oes)|territorios?)\b|"
                                    r"\b(?:qual|quais|que) (?:municipios?|cidades?|estados?|lugar(?:es)?|territorios?)\b.*"
                                    r"\b(?:o |a )?(?:melhor|pior)(?:es)?\b|\b(?:melhor|pior)(?:es)?\b.*\b(?:para|pra) (?:morar|viver|"
                                    r"trabalhar|investir|estudar|se mudar)\b|\b(?:ranking|lista|top|classifica\w*|ordem) "
                                    r"(?:d[oa]s )?(?:melhores|piores)\b")),
    ("criar_classe", re.compile(r"\b(?:cri[ae]r?|invent[ae]r?|defin[ae]r?|faz|faca|mont[ae]r?)\b.*\b(?:uma |um )?"
                                r"(?:classificacao|classe|categoria|rotulo|indice|indicador novo|novo indicador|"
                                r"ranking proprio|selo)\b")),
    ("outro_metodo", re.compile(r"\b(?:media movel|regressao|mediana|outra formula|outro metodo|metodo diferente|seu metodo|"
                                r"interpol\w*|imput\w*|suaviz\w*|ajuste linear|ponderad\w*|em vez desse metodo|"
                                r"ao inves (?:desse|do) metodo|logaritm\w*)\b")),
    ("ocupacao", re.compile(r"\b(?:conta|conte|contar|inclu\w*|consider\w*|som[ae]r?|junt[ae]r?)\b.*\b(?:enfermeir\w*|"
                            r"tecnic\w* de enfermagem|dentist\w*|agentes? comunitari\w*|fisioterap\w*|farmac\w*|"
                            r"psicolog\w*|nutricion\w*|outras profissoes|outras categorias|outras ocupacoes)\b")),
    ("afirmar_juizo", re.compile(r"\b(?:diz|diga|dizer|afirm\w*|escrev\w*|confirm\w*|declar\w*|conclu\w*|fala|fale)\b"
                                 r".*\b(?:carencia|deficit\w*|excesso|suficiente|insuficiente|falta de (?:medicos|"
                                 r"profissionais)|adequad\w*|inadequad\w*|critic\w*|prioritari\w*|ideal)\b")),
    ("politica", re.compile(r"\b(?:qual|que|quais) (?:politica|politicas|programa|intervenc\w*|acao|acoes|medida|medidas)\b"
                            r"|\b(?:recomend\w*|sugir\w*|suger\w*|indic[ae]) (?:uma |alguma )?(?:politica|intervenc\w*|"
                            r"acao|medida|solucao)\b|\bo que (?:o |a )?\w+ (?:deveria|deve) fazer\b")),
    ("correlacao", re.compile(r"\b(?:correlac\w*|correlacion\w*|regressao|associacao estatistica|moran|autocorrelac\w*|"
                              r"cluster(?:s)? espacia\w*|padrao espacial|padroes espaciais)\b")),
    ("projecao", re.compile(r"\b(?:projec\w*|projet[ae]r?|previs\w*|prev[eê]|preveja|prever|futuro|daqui a \d+ anos|"
                            r"vai ser em 20\d\d|ate 20[3-9]\d|em 20[3-9]\d)\b")),
    ("pessoas", re.compile(r"\b(?:list[ae]r?|listagem|quem sao|quais sao os nomes)\b.*\b(?:os |as )?(?:nomes?|"
                           r"medicos|profissionais|trabalhadores|pessoas)\b|\branking de (?:pessoas|profissionais|medicos)\b|"
                           r"\b(?:quais|quem) (?:sao )?(?:os |as )?(?:profissionais|medicos|pessoas|trabalhadores)? ?"
                           r"(?:que )?(?:trabalham|atuam|estao lotad\w*|trabalha|atua)\b|"
                           r"\bnomes? d[oa]s (?:medicos|profissionais|pessoas|trabalhadores)\b")),
    ("fontes_externas", re.compile(r"\b(?:busc\w*|pesquis\w*|procur\w*|consult\w*) (?:na |em )?(?:internet|web|google|"
                                   r"fontes externas|artigos|evidencias|literatura)\b|\b(?:pib|renda per capita|pobreza|"
                                   r"idh|clima|temperatura)\b")),
    ("ignorar_parametro", re.compile(r"\b(?:ignor\w*|desconsider\w*|pul[ae]r?|esquec\w*|sem)\b (?:o |a )?(?:periodo|"
                                     r"competencia|populacao|parametro|categoria|denominador)\b")),
    ("delegar", re.compile(r"\b(?:voce decide|decid[ae] (?:voce|por mim)|escolh[ae] (?:voce|por mim)|o que (?:voce )?achar "
                           r"melhor|tanto faz|a seu criterio|fica a seu criterio|defina o criterio por mim|"
                           r"use o que achar melhor|voce que sabe)\b")),
)
JUIZO = ("carencia", "deficit", "excesso", "suficiente", "insuficiente", "falta de medicos", "adequado", "inadequado",
         "critico", "prioritario", "ideal")


CORRECAO_COM_PEDIDO = re.compile(r"^(?:nao|na verdade|errado)\b[, ]*(?:eu )?(?:queria|quero|prefiro|pedi|era|seria|"
                                 r"gostaria de ver|gostaria|preferia)?\b[, ]*(?P<resto>.+)$")
INDIRETO_TENDENCIA = re.compile(r"\b(?:mudou ao longo do tempo|ao longo do tempo|com o tempo|evolui\w*|evolucao|trajetoria|"
                                r"historico|nos ultimos anos|mudou nos ultimos)\b")


# --------------------------------------------------------------------------------------------- reconhecimento
def _alternativas(pendente) -> list[dict]:
    if not isinstance(pendente, dict):
        return []
    return [a for a in pendente.get("alternativas") or [] if isinstance(a, dict) and isinstance(a.get("rotulo"), str)]


def _pontua(mensagem: str, alternativas: list[dict], rotulos: dict | None = None) -> list[int]:
    """Pontos de cada alternativa para uma resposta digitada; [] quando nenhuma é citada."""
    texto = dobra(mensagem)
    tokens = [p for p in palavras(texto) if p not in VAZIAS]
    unidade = {"municipio", "cidade", "capital", "municipios", "cidades"} | set((rotulos or {}).get("unidade", ()))
    grupo = {"estado", "uf", "estados"} | set((rotulos or {}).get("grupo", ()))
    pontos = [0] * len(alternativas)
    negados = set(re.findall(r"\bnao (?:e |eh |era )?(?:o |a |do |da )?(\w+)", texto))
    citou_unidade = any(t in unidade for t in palavras(texto)) and not (negados & unidade)
    citou_grupo = any(t in grupo for t in palavras(texto)) and not (negados & grupo)
    estados_citados = {codigo for nome, codigo in ESTADOS_POR_NOME.items() if re.search(r"\b" + re.escape(nome) + r"\b",
                                                                                         texto)}
    estados_citados |= {SIGLAS[t] for t in palavras(texto) if t in SIGLAS and len(texto) <= 40}
    meses = {i for i, mes in enumerate(MESES) if re.search(r"\b" + mes[:3], texto)}
    for indice, alternativa in enumerate(alternativas):
        rotulo = dobra(alternativa["rotulo"])
        e_grupo = bool(re.match(r"^(?:estado|uf|provincia|distrito|regiao|grupo)\b", rotulo)) or \
            any(rotulo.startswith(g) for g in grupo)
        if citou_grupo and e_grupo:
            pontos[indice] += 3
        if citou_unidade and not e_grupo:
            pontos[indice] += 3
        for codigo in estados_citados:
            sigla = STATES[codigo][0].lower()
            if "(" + sigla + ")" in rotulo or rotulo.endswith(" " + sigla):
                pontos[indice] += 4
            if e_grupo and dobra(STATES[codigo][1]) in rotulo:
                pontos[indice] += 2
        for mes in meses:
            if MESES[mes][:3] in rotulo:
                pontos[indice] += 4
        if texto and len(texto) >= 4 and texto in rotulo:
            pontos[indice] += 5
        pontos[indice] += sum(1 for t in tokens if len(t) >= 3 and re.search(r"\b" + re.escape(t) + r"\b", rotulo) and
                              t not in unidade and t not in grupo)
    for chave, posicao in ORDINAIS.items():
        if re.search(r"\b" + chave + (r"\w*" if chave.isalpha() and len(chave) > 3 else r"\b"), texto) and \
                (chave.isalpha() or re.search(r"\b(?:opcao|numero|alternativa|o|a)\s*" + chave + r"\b", texto) or
                 texto == chave):
            if chave in ("um", "dois", "tres") and not re.search(r"\b(?:opcao|numero|alternativa)\s+" + chave, texto):
                continue
            if posicao < len(pontos):
                pontos[posicao] += 6
    if re.search(r"\bultim[oa]\b", texto) and pontos:
        pontos[-1] += 6
    return pontos


def _escolhida(mensagem: str, alternativas: list[dict], rotulos=None) -> int | None:
    pontos = _pontua(mensagem, alternativas, rotulos)
    if not pontos or max(pontos) <= 0:
        return None
    melhores = [i for i, p in enumerate(pontos) if p == max(pontos)]
    return melhores[0] if len(melhores) == 1 else None


def _parece_pedido_novo(texto: str) -> bool:
    from conversa_grafico import COMPARAR, TENDENCIA, VERBO_VISTA
    return bool(COMPARAR.search(texto) or TENDENCIA.search(texto) or VERBO_VISTA.search(texto) or
                re.search(r"\b(?:ordene|ordena|junte|junta|referencia|distribuicao|quintis|quartis|decis|exporte)\b", texto)
                or len(palavras(texto)) > 7)


def _atributo(texto: str) -> str | None:
    for nome, padrao in ATRIBUTOS:
        if padrao.search(texto):
            return nome
    return None


def _termos(texto: str) -> list[str]:
    return [nome for nome, padrao in TERMOS if padrao.search(texto)]


def _registro(texto: str, anterior: str | None = None) -> str:
    if REGISTRO_TECNICO.search(texto):
        return "tecnico"
    if REGISTRO_SIMPLES.search(texto):
        return "simples"
    if REGISTRO_DIDATICO.search(texto):
        return "didatico"
    if REGISTRO_OUTRO.search(texto):
        ordem = ["objetivo", "didatico", "simples", "tecnico"]
        return ordem[(ordem.index(anterior) + 1) % len(ordem)] if anterior in ordem else "didatico"
    return anterior if anterior in explicacao.REGISTROS else "objetivo"


def reconhecer(mensagem: str, conversa: dict | None, tem_resultado: bool, resultado_tendencia: bool | None = None,
               nomes_no_resultado: list[str] | None = None) -> dict | None:
    """O ato do diálogo, reconhecido sem o provedor, ou None (a mensagem segue para a gramática e o intérprete).
    resultado_tendencia: se o resultado em exibição já é a tendência (None quando não se sabe)."""
    conversa = conversa if isinstance(conversa, dict) else {}
    interrogativa = mensagem.strip().endswith("?")
    texto = dobra(mensagem).strip(" .!?")
    if not texto:
        return None
    memoria = conversa.get("memoria") if isinstance(conversa.get("memoria"), dict) else {}
    pendente = conversa.get("pendente") if isinstance(conversa.get("pendente"), dict) else None
    alternativas = _alternativas(pendente)
    # 1. Resposta a esclarecimento pendente (alternativas ou modelo de resposta). "Não era isso que eu queria" logo depois de
    # uma pergunta rejeita a pergunta: nada mudou no gráfico desde a mudança anterior, que só é desfeita se a pessoa pedir.
    if pendente and (alternativas or "{resposta}" in str(pendente.get("modelo") or "")) and DESFAZER.search(texto) and \
            not re.search(r"\bdesfa(?:z|zer|ca)\b", texto):
        return {"ato": "cancela_pendente", "rejeita": True}
    if pendente and alternativas:
        escolhida = _escolhida(mensagem, alternativas)
        pontos = _pontua(mensagem, alternativas)
        forte = escolhida is not None and pontos[escolhida] >= 4
        if escolhida is not None and (forte or not (len(palavras(texto)) > 6 and _parece_pedido_novo(texto))):
            return {"ato": "responde_pendente", "alternativa": escolhida}
        if re.fullmatch(r"(?:nenhum[ao]?(?: d[ao]s (?:duas|dois|opcoes))?|deixa (?:pra|para) la|esquece|cancela|"
                        r"nao quero mais|nenhuma delas)", texto):
            return {"ato": "cancela_pendente"}
        if not _parece_pedido_novo(texto) and not PERGUNTA.search(texto) and len(palavras(texto)) <= 5 and \
                not _governanca(texto):
            return {"ato": "repergunta"}
    if pendente and isinstance(pendente.get("modelo"), str) and "{resposta}" in pendente["modelo"] and \
            not PERGUNTA.search(texto) and not _governanca(texto) and len(palavras(texto)) <= 8:
        return {"ato": "completa_pendente"}
    # 2. Governança: antes dos atos que mudam o gráfico ("muda o valor de X para 10" não é uma troca).
    governanca = _governanca(texto)
    if governanca:
        return {"ato": "governanca", "tipo": governanca}
    # 3. Correção de uma escolha já aplicada ("Não, o estado.").
    escolha = memoria.get("escolha") if isinstance(memoria.get("escolha"), dict) else None
    if escolha and NEGACAO_INICIAL.search(texto):
        restantes = _alternativas({"alternativas": escolha.get("restantes")})
        indice = _escolhida(re.sub(r"^(?:nao|na verdade|errado)\b[, ]*", "", texto), restantes)
        if indice is not None:
            return {"ato": "corrige_escolha", "alternativa": indice}
    # 3b. Correção com um novo pedido ("Não, eu queria a evolução, não só o resultado atual.").
    corrigido = CORRECAO_COM_PEDIDO.match(texto)
    if corrigido and not DESFAZER.search(texto):
        resto = re.split(r",? (?:e )?(?:nao|nem) (?:so|apenas|somente)\b", corrigido.group("resto"))[0].strip(" ,.")
        if resto and (_parece_pedido_novo(resto) or _atributo(resto) or INDIRETO_TENDENCIA.search(resto) or
                      re.search(r"\b(?:densidade|quantidade|tendencia|distribuicao|mapa|grafico|estado|municipio)\b", resto)):
            return {"ato": "corrige_pedido", "resto": resto}
    # 4. Desfazer e voltar.
    if DESFAZER.search(texto) and not ALVO_DA_VOLTA.search(texto.replace("como estava", "")):
        return {"ato": "desfaz"}
    if VOLTA.search(texto) and (ANTES.search(texto) or "como estava" in texto) and \
            not re.search(r"\b(?:resultado anterior|analise anterior)\b", texto) or \
            re.search(r"\bcomo estava antes\b", texto):
        alvo = ALVO_DA_VOLTA.search(texto)
        return {"ato": "volta", "alvo": alvo.group(0) if alvo else "antes"}
    # 5. Referência ao resultado anterior numa pergunta ("não, eu estava falando da análise anterior").
    if ANTERIOR_REFERENCIA.search(texto):
        return {"ato": "refere_anterior"}
    # 5b. Comparação pelos extremos do gráfico, sem nomes ("compare o de maior e o de menor densidade", "qual a diferença
    # entre o maior e o menor?"); no plural sem quantidade ("compare os mais populosos"), a pergunta de quantos.
    compara, diferenca = COMPARA.search(texto), DIFERENCA.search(texto)
    if (compara or diferenca) and not _cita_territorio(texto, nomes_no_resultado or []):
        alto, baixo = EXTREMO_ALTO.search(texto), EXTREMO_BAIXO.search(texto)
        if EXTREMOS.search(texto) or PRIMEIROS_N.search(texto) or (alto and baixo):
            return {"ato": "compara_extremos"}
        if compara and EXTREMOS_NO_PLURAL.search(texto) and bool(alto) != bool(baixo):
            return {"ato": "compara_extremos", "quantos": None}
    # 6. Troca, inclusão sem nome, todos.
    if TROCA.search(texto):
        return {"ato": "troca"}
    if INCLUI.search(texto) and MAIS_UM.search(texto) and not re.search(r"[A-Z]", mensagem[1:]) and \
            len(palavras(texto)) <= 7:
        return {"ato": "inclui_sem_nome"}
    if INCLUI.search(texto) and tem_resultado:
        return {"ato": "inclui", "condicional": True}
    if TIRA.search(texto) and tem_resultado:
        return {"ato": "tira", "condicional": True}
    estado_citado = re.search(r"\btod[oa]s (?:os |as )?(?:municipios|cidades) d[eoa]s? (?:estado d[eoa] )?([a-z ]+?)\s*$",
                              texto)
    if estado_citado and dobra(estado_citado.group(1)).strip() in ESTADOS_POR_NOME:
        return {"ato": "todos_do_estado", "estado": ESTADOS_POR_NOME[dobra(estado_citado.group(1)).strip()]}
    if TODOS.search(texto) and re.fullmatch(r"(?:e |entao |agora |mas )*(?:se )?(?:considerarmos|considerando|com|mostra|"
                                            r"mostre|pra|para|incluindo|e)? ?(?:tod[oa]s)(?: os municipios| as cidades| eles)?"
                                            r"(?: entao| tambem| de uma vez)?", texto):
        return {"ato": "todos"}
    if not tem_resultado:
        if DADOS.search(texto):
            return {"ato": "estado", "assunto": "dados"}
        if EXPLICA.search(texto) and (_termos(texto) or CLASSIFICACAO.search(texto)):
            return {"ato": "explica", "topico": "conceito", "termos": _termos(texto), "registro": _registro(texto)}
        return None
    # 6b. Pedido em forma de pergunta ("como isso mudou ao longo do tempo?"): é a tendência dos mesmos territórios.
    if INDIRETO_TENDENCIA.search(texto) and (PERGUNTA.search(texto) or interrogativa) and not CAUSA.search(texto) and \
            not EXPLICA.search(texto) and (resultado_tendencia is False):
        return {"ato": "pedido_indireto", "pedido": "mostre a tendência desses"}
    # 7. Perguntas sobre o estado da tela.
    assunto = _assunto_de_estado(texto)
    if assunto:
        return {"ato": "estado", **assunto}
    if re.search(r"\bo que (?:ta|esta|tem|aparece|aparecendo|ficou|e isso)\b.*\b(?:tela|grafico|aparecendo|aqui)\b|"
                 r"\bo que (?:ta|esta) aparecendo\b|\bo que (?:tem|ha) (?:na tela|no grafico|aqui)\b", texto):
        return {"ato": "explica", "topico": "resultado", "registro": "objetivo"}
    citado = _cita_territorio(texto, nomes_no_resultado or [])
    if citado and re.search(r"\b(?:leitura|o que (?:diz|significa|quer dizer|mostra)|como (?:fica|esta|ficou|foi)|"
                            r"e (?:para|pra|quanto a|sobre)|qual (?:e )?a situacao|e (?:o|a) \w+\?*$)\b|^e (?:o |a )?\w+",
                            texto) and not CAUSA.search(texto) and not NORMATIVO.search(texto) and \
            not (MAIOR.search(texto) or MENOR.search(texto)):
        return {"ato": "explica", "topico": "territorio", "registro": _registro(texto, memoria.get("registro"))}
    # 8. Verificações e limites.
    verificacao = _verificacao(texto, memoria, interrogativa)
    if verificacao:
        return verificacao
    # 9. Explicação progressiva.
    explicar = _explicacao(texto, memoria)
    if explicar:
        return explicar
    # 10. Perguntas sobre o resultado em exibição.
    return _pergunta_sobre_resultado(texto, memoria, interrogativa)


def _como_escrito(mensagem: str, termo: str) -> str:
    """O termo (já dobrado) como a pessoa o escreveu, com acentos e maiúsculas (“carência”, não “carencia”)."""
    dobrada, origem = [], []
    for posicao, caractere in enumerate(mensagem):
        for simples in "".join(c for c in unicodedata.normalize("NFD", caractere.lower()) if not unicodedata.combining(c)):
            dobrada.append(simples)
            origem.append(posicao)
    inicio = "".join(dobrada).find(termo)
    if inicio < 0:
        return termo
    return mensagem[origem[inicio]:origem[inicio + len(termo) - 1] + 1]


def _cita_territorio(texto: str, nomes: list[str]) -> bool:
    for nome in nomes:
        simples = dobra(str(nome).split(" (")[0].split(" [")[0])
        if len(simples) >= 3 and re.search(r"\b" + re.escape(simples) + r"\b", texto):
            return True
    return False


def _governanca(texto: str) -> str | None:
    for tipo, padrao in GOV:
        if padrao.search(texto):
            if tipo == "ignorar_parametro" and not re.search(r"\b(?:calcul\w*|mostr\w*|faz|faca|assim mesmo|mesmo assim|"
                                                             r"ignor\w*|desconsider\w*)\b", texto):
                continue
            if tipo == "projecao" and re.search(r"\b(?:projecao (?:geodesica|cartografica)|previsto)\b", texto):
                continue
            return tipo
    return None


def _assunto_de_estado(texto: str) -> dict | None:
    if DADOS.search(texto):
        return {"assunto": "dados"}
    if MUDOU.search(texto):
        return {"assunto": "mudou"}
    if TERRITORIOS.search(texto):
        return {"assunto": "territorios"}
    if SELECAO.search(texto) and re.search(r"\b(?:significa|quer dizer|e o que|o que e|como funciona|serve)\b", texto):
        return {"assunto": "selecao"}
    if RELATORIO.search(texto) and re.search(r"\b(?:contem|tem|traz|vem|sai|mostra|o que|qual|quais|inclui)\b", texto):
        return {"assunto": "relatorio"}
    if ANALISE_ANTERIOR.search(texto) and PERGUNTA.search(texto):
        return {"assunto": "anterior"}
    if re.search(r"\b(?:por que|porque|pq)\b", texto) and NAO_APARECE.search(texto):
        for familia, padrao in FAMILIAS_DISPONIVEIS:
            if padrao.search(texto):
                return {"assunto": familia}
        if re.search(r"\bmapa\b", texto):
            return {"assunto": "mapa"}
        return {"assunto": "ausente"}
    if MAPA.search(texto) and re.search(r"\b(?:vendo|significa|significam|mostra|quer dizer|representa|representam|"
                                        r"o que sao|o que e|cada)\b", texto) and not EXPLICA.search(
            texto.replace("o que e", "").replace("significa", "").replace("quer dizer", "")):
        return {"assunto": "mapa"}
    return None


def _verificacao(texto: str, memoria: dict, interrogativa: bool = False) -> dict | None:
    if ACESSO.search(texto) and (re.search(r"\b(?:distancia|km|longe|perto|chegar)\b", texto) or
                                 memoria.get("atributo") == "distancia_km"):
        return {"ato": "limite", "tipo": "acesso"}
    if PROCEDENCIA.search(texto):
        return {"ato": "limite", "tipo": "procedencia"}
    pergunta = interrogativa or bool(PERGUNTA.search(texto)) or \
        texto.startswith(("entao", "isso", "esse", "essa", "quer dizer", "significa"))
    if NORMATIVO.search(texto) and (pergunta or re.search(r"\b(?:entao|logo|portanto)\b", texto)):
        return {"ato": "limite", "tipo": "normativo"}
    if MELHORA.search(texto) and pergunta and JULGAMENTO.search(texto):
        return {"ato": "limite", "tipo": "melhora"}
    forte = re.search(r"\b(?:o que explica|qual (?:foi |e )?(?:a )?(?:causa|razao|motivo)|causou|causaram|por causa|"
                      r"o que levou|o que fez|devido a|responsavel por|culpa)\b", texto)
    if CAUSA.search(texto) and (forte or not re.search(r"\b(?:diferente|diferenca|significa|quer dizer|nao aparece)\b",
                                                        texto)) and \
            (forte or FENOMENO.search(texto) or re.search(r"\b(?:causa|causou|motivo|razao|devido|por causa|o que levou)\b",
                                                          texto)):
        comparativo = _atributo(texto) and (MAIOR.search(texto) or MENOR.search(texto)) and \
            re.search(r"\b(?:tem|e|esta|ficou) (?:mais|menos|maior|menor)\b", texto)
        return {"ato": "limite", "tipo": "causa", **({"comparativo": True, "atributo": _atributo(texto),
                                                      "maior": not MENOR.search(texto)} if comparativo else {})}
    return None


def _explicacao(texto: str, memoria: dict) -> dict | None:
    termos = _termos(texto)
    anterior = memoria.get("registro") if memoria.get("ato") == "explica" else None
    em_explicacao = memoria.get("ato") in ("explica", "resumo", "compara")
    if TERRITORIO_DEIXIS.search(texto) and (EXPLICA.search(texto) or re.search(r"\b(?:quer dizer|significa|o que isso)\b",
                                                                            texto)):
        return {"ato": "explica", "topico": "territorio", "registro": _registro(texto, anterior)}
    conceituais = [t for t in termos if t not in ("densidade", "distancia")]
    diferente = re.search(r"\b(?:diferente|difere|nao e a mesma coisa|mesma coisa)\b", texto) or (
        re.search(r"\bdiferenca\b", texto) and (len(termos) >= 2 or (conceituais and re.search(r"\bentre\b", texto))))
    if diferente and (conceituais or (em_explicacao and memoria.get("termos"))):
        lista = list(dict.fromkeys((memoria.get("termos") or [] if re.search(r"\b(?:isso|esse|essa|ela|ele)\b", texto)
                                    else []) + termos))
        return {"ato": "explica", "topico": "conceito", "termos": lista, "registro": _registro(texto, anterior)}
    if termos and re.search(r"\b(?:quer dizer|significa|e o mesmo que|e igual a|tem a ver com)\b", texto):
        return {"ato": "explica", "topico": "conceito", "termos": termos, "registro": _registro(texto, anterior)}
    if not (EXPLICA.search(texto) or (em_explicacao and REGISTRO_OUTRO.search(texto))):
        return None
    if termos:
        registro = _registro(texto, anterior)
        if re.search(r"\b(?:nao entendi|nao ficou claro|como assim)\b", texto) and not REGISTRO_TECNICO.search(texto):
            registro = "simples"
        return {"ato": "explica", "topico": "conceito", "termos": termos, "registro": registro}
    if CLASSIFICACAO.search(texto):
        return {"ato": "explica", "topico": "classificacao", "registro": _registro(texto, anterior)}
    registro = _registro(texto, anterior)
    if em_explicacao and not RESULTADO.search(texto) and memoria.get("topico") in ("conceito", "territorio"):
        return {"ato": "explica", "topico": memoria["topico"], "termos": memoria.get("termos") or [],
                "registro": registro, "foco": memoria.get("foco")}
    return {"ato": "explica", "topico": "resultado", "registro": registro if registro != "objetivo" or not
            re.search(r"\bmelhor\b", texto) else "didatico"}


def _pergunta_sobre_resultado(texto: str, memoria: dict, interrogativa: bool = False) -> dict | None:
    if CONTAGEM.search(texto) and (re.search(r"\b(?:grafico|tela|analise|aqui|selecionad\w*|tem|ha|estao|aparecem|"
                                            r"existem|sao|ficaram|entraram)\b", texto) or texto.startswith("quant")):
        return {"ato": "contagem"}
    if DIFERENCA.search(texto) and (DEIXIS.search(texto) or PERGUNTA.search(texto)) and \
            not [t for t in _termos(texto) if t not in ("densidade", "distancia")]:
        return {"ato": "diferenca"}
    atributo = _atributo(texto)
    comparativo = MAIOR.search(texto) or MENOR.search(texto)
    eliptica = re.match(r"^(?:e |mas |entao |agora |ja )+(?:se (?:for|fosse|olhar|olharmos|considerar|considerarmos|"
                        r"ver|vermos|usar|usarmos) |olhando |pensando |falando |considerando )?(?:em relacao (?:a|ao|aos|as) |"
                        r"quanto (?:a|ao) |sobre (?:a|o) |pel[ao] |em |n[ao] |(?:a|o) )?(?:populacao|quantidade|densidade|"
                        r"distancia|variacao|numero de \w+|habitantes|profissionais|medicos|tamanho)\b", texto) and \
        len(palavras(texto)) <= 9
    if eliptica and atributo:
        maior = memoria.get("maior", True) if memoria.get("ato") == "compara" else True
        if comparativo:
            maior = not MENOR.search(texto) or bool(re.search(r"\bmaior\b", texto))
        return {"ato": "compara", "atributo": atributo, "maior": maior}
    pergunta = interrogativa or bool(PERGUNTA.search(texto))
    if comparativo and pergunta and (atributo or DEIXIS.search(texto)) and \
            not re.search(r"\b(?:os|as) \d+\b|\btop\b|\bmunicipios com\b|\bque tem (?:densidade|quantidade)\b", texto):
        maior = bool(MAIOR.search(texto)) and not (MENOR.search(texto) and not re.search(r"\bmaior\b", texto))
        if re.search(r"\bmais (?:perto|proxim)", texto):
            maior = False
        return {"ato": "compara", "atributo": atributo or memoria.get("atributo") or None, "maior": maior}
    return None


# --------------------------------------------------------------------------------------------- execução
def _resposta(texto: str, **campos) -> dict:
    return {"handled": True, "executed": False, "reply": texto, **campos}


def _explicada(composicao: dict, memoria: dict, **campos) -> dict:
    resposta = _resposta(composicao["texto"], memoria=memoria, explicacao={
        "segmentos": composicao["segmentos"], "documentacao": composicao["documentacao"],
        "origem": "MOTOR_E_CATALOGO_GOVERNADO"}, **campos)
    if composicao.get("acoes"):
        resposta["acoes"] = composicao["acoes"]
    resposta["_composicao"] = composicao  # composição verificada; sai antes da resposta da API
    return resposta


def pede_reformulacao(mensagem: str) -> bool:
    """Outra formulação pedida ("de outro jeito", "mais simples", "didático"), não a pergunta sobre um termo ("não entendi
    a aceleração"), que é explicação de conceito."""
    texto = dobra(mensagem)
    if _termos(texto):
        return False
    return bool(REGISTRO_OUTRO.search(texto) or REGISTRO_SIMPLES.search(texto) or REGISTRO_DIDATICO.search(texto))


class Ambiente:
    """O que o gestor recebe da requisição: a memória da conversa, o contexto do gráfico, o resultado em exibição e o
    anterior (da sessão, com a integridade conferida), a fonte e os acessos à gramática local (interpretar um rascunho e
    resolver nomes), carregados só quando o ato precisa."""

    def __init__(self, mensagem, conversa, ctx, resultado=None, anterior=None, fonte=None, interpretar=None, nomes=None,
                 rotulos=None):
        self.mensagem = mensagem
        self.conversa = conversa if isinstance(conversa, dict) else {}
        self.memoria = self.conversa.get("memoria") if isinstance(self.conversa.get("memoria"), dict) else {}
        self.pendente = self.conversa.get("pendente") if isinstance(self.conversa.get("pendente"), dict) else None
        self.anteriores = [item for item in self.conversa.get("anteriores") or []
                           if isinstance(item, dict) and isinstance(item.get("pedido"), dict)]
        self.ctx = ctx or {}
        self.resultado = resultado
        self.anterior = anterior
        self.fonte = fonte or {}
        self.interpretar = interpretar
        self.nomes = nomes
        self.rotulos = rotulos or {}


PRECISA_DA_BASE = frozenset(("responde_pendente", "corrige_escolha", "completa_pendente", "troca", "inclui", "tira",
                             "corrige_pedido", "pedido_indireto"))


def executar(ato: dict, amb: Ambiente) -> dict | None:
    """Executa o ato reconhecido (aqui ou pelo intérprete com o provedor). None devolve a mensagem ao caminho anterior."""
    tipo = ato.get("ato")
    funcao = EXECUTORES.get(tipo)
    if funcao is None:
        return None
    resposta = funcao(ato, amb)
    if resposta is not None:
        resposta.setdefault("memoria", {"ato": tipo})
        resposta["dialogo"] = {"versao": VERSAO, "ato": tipo, **{k: v for k, v in ato.items() if k in (
            "tipo", "assunto", "topico", "registro", "atributo", "termos", "alvo")}}
    return resposta


def _rotulo_alternativa(alternativa: dict) -> str:
    return alternativa.get("rotulo") or alternativa.get("label") or ""


def _aplica_rascunho(amb: Ambiente, alternativa: dict, original: str) -> dict | None:
    if amb.interpretar is None:
        return None
    if alternativa.get("operacao"):
        return amb.interpretar(original, dica=alternativa["operacao"], dica_indicador=alternativa.get("indicador"))
    rascunho = alternativa.get("rascunho") or alternativa.get("draft")
    if not isinstance(rascunho, str) or not rascunho.strip():
        return None
    # A alternativa que é uma comparação pelos extremos ("compare os três maiores em população") volta ao próprio gestor.
    ato = reconhecer(rascunho, None, amb.resultado is not None)
    if ato and ato.get("ato") == "compara_extremos":
        return _compara_extremos(ato, Ambiente(rascunho, {}, amb.ctx, amb.resultado, amb.anterior, amb.fonte,
                                               amb.interpretar, amb.nomes, amb.rotulos))
    return amb.interpretar(rascunho)


def _com_prefixo(resposta: dict, prefixo: str) -> dict:
    chave = "clarification" if resposta.get("clarification") else "reply"
    resposta[chave] = prefixo + (resposta.get(chave) or "")
    return resposta


def _alternativas_da_resposta(resposta: dict) -> list[dict]:
    return [{"rotulo": c.get("label", ""), "rascunho": c.get("draft", ""),
             **({"operacao": c["operation"]} if c.get("operation") else {})}
            for c in resposta.get("choices") or [] if isinstance(c, dict)]


def _responde_pendente(ato: dict, amb: Ambiente) -> dict | None:
    """Retoma o pedido original com a alternativa escolhida. Se a retomada traz outra pergunta (o período depois do
    território, por exemplo), as informações que a pessoa já deu e que ainda não tinham uso (`dicas`) respondem a ela,
    sem pedir de novo."""
    alternativas = _alternativas(amb.pendente)
    indice = ato["alternativa"]
    if not 0 <= indice < len(alternativas):
        return None
    escolhida = alternativas[indice]
    original = str((amb.pendente or {}).get("pedido") or "")
    resposta = _aplica_rascunho(amb, escolhida, original)
    if not resposta or not resposta.get("handled"):
        return _resposta("Entendi: " + _rotulo_alternativa(escolhida) + ". Não consegui retomar o pedido original; "
                         "pode repeti-lo com essa escolha?", memoria={"ato": "responde_pendente"})
    restantes = [a for i, a in enumerate(alternativas) if i != indice]
    prefixo = "Entendi: " + _rotulo_alternativa(escolhida) + ". "
    dicas = [d for d in amb.memoria.get("dicas") or [] if isinstance(d, str)]
    for _ in range(3):
        novas = _alternativas_da_resposta(resposta)
        uso = next(((dica, i) for dica in dicas for i in [_escolhida(dica, novas)] if i is not None), None) if novas else None
        if uso is None:
            break
        dica, i = uso
        seguinte = _aplica_rascunho(amb, novas[i], original)
        if not seguinte or not seguinte.get("handled"):
            break
        prefixo += "Usei também o que você disse antes (“" + dica.strip(" .!?") + "”): " + novas[i]["rotulo"] + ". "
        dicas.remove(dica)
        restantes, resposta = [a for j, a in enumerate(novas) if j != i], seguinte
    resposta = _com_prefixo(dict(resposta), prefixo)
    memoria = {"ato": "responde_pendente", "escolha": {"pedido": original, "escolhida": _rotulo_alternativa(escolhida),
                                                        "restantes": restantes}}
    if dicas:
        memoria["dicas"] = dicas
    if resposta.get("choices"):
        resposta["pedido_original"] = original
    resposta["memoria"] = memoria
    return resposta


def _corrige_escolha(ato: dict, amb: Ambiente) -> dict | None:
    escolha = amb.memoria.get("escolha") or {}
    restantes = _alternativas({"alternativas": escolha.get("restantes")})
    indice = ato["alternativa"]
    if not 0 <= indice < len(restantes):
        return None
    nova = restantes[indice]
    resposta = _aplica_rascunho(amb, nova, str(escolha.get("pedido") or ""))
    if not resposta or not resposta.get("handled"):
        return None
    texto = resposta.get("clarification") or resposta.get("reply") or ""
    outras = [a for i, a in enumerate(restantes) if i != indice] + [{"rotulo": escolha.get("escolhida", ""),
                                                                     "rascunho": ""}]
    if "não ficam no mesmo gráfico" in texto and not resposta.get("painel"):
        mantida = escolha.get("escolhida", "")
        sugestao = _estados_para_comparar(amb, nova)
        escolhas = []
        if sugestao:
            escolhas.append({"label": sugestao["rotulo"], "draft": sugestao["rascunho"], "send": True})
        texto = ("Entendi: " + _rotulo_alternativa(nova) + ". Só que " + texto[0].lower() + texto[1:].replace(
            " Nada mudou no gráfico.", "") + (" Posso comparar " + sugestao["frase"] + "." if sugestao else "") +
            " Por enquanto, mantive " + mantida + " na comparação.")
        return _resposta(texto, choices=escolhas, memoria={"ato": "corrige_escolha"})
    resposta = _com_prefixo(dict(resposta), "Troquei: " + _rotulo_alternativa(nova) + ". ")
    resposta["memoria"] = {"ato": "corrige_escolha", "escolha": {"pedido": escolha.get("pedido"),
                                                                 "escolhida": _rotulo_alternativa(nova),
                                                                 "restantes": [a for a in outras if a.get("rascunho")]}}
    return resposta


def _estados_para_comparar(amb: Ambiente, nova: dict) -> dict | None:
    """Estado escolhido na correção + os estados dos outros municípios do gráfico: a comparação possível entre estados."""
    rotulo = dobra(_rotulo_alternativa(nova))
    escolhido = next((codigo for nome, codigo in ESTADOS_POR_NOME.items() if nome in rotulo), None)
    body = amb.resultado or {}
    outros = []
    for item in body.get("itens") or []:
        codigo = str(item.get("grupo_territorial") or "")
        if item.get("tipo") == "municipio" and codigo in STATES and codigo != escolhido and codigo not in outros:
            outros.append(codigo)
    if not escolhido or not outros:
        return None
    codigos = [escolhido] + outros[:2]
    nomes = [STATES[c][1] for c in codigos]
    frase = "os estados " + (", ".join(nomes[:-1]) + " e " + nomes[-1])
    return {"rotulo": "Comparar " + frase, "frase": frase,
            "rascunho": "compare os estados " + ", ".join(nomes[:-1]) + " e " + nomes[-1]}


def _tem_pista(mensagem: str) -> bool:
    """A mensagem traz uma informação que serve a uma escolha futura (estado, sigla, tipo de território)."""
    texto = dobra(mensagem)
    return bool(any(re.search(r"\b" + re.escape(nome) + r"\b", texto) for nome in ESTADOS_POR_NOME) or
                re.search(r"\b(?:municipio|cidade|estado|uf|capital)\b", texto))


def _repergunta(ato: dict, amb: Ambiente) -> dict:
    alternativas = _alternativas(amb.pendente)
    nomes = [_rotulo_alternativa(a) for a in alternativas]
    lista = ", ".join(nomes[:-1]) + " ou " + nomes[-1] if len(nomes) > 1 else (nomes[0] if nomes else "")
    periodos = all(re.search(r"\b(?:" + "|".join(MESES) + r")\b", dobra(nome)) for nome in nomes) and nomes
    memoria = {"ato": "repergunta"}
    if _tem_pista(amb.mensagem):
        memoria["dicas"] = ([d for d in amb.memoria.get("dicas") or [] if isinstance(d, str)] + [amb.mensagem])[-3:]
        texto = ("Anotei “" + amb.mensagem.strip(" .!?") + "” para quando essa escolha aparecer. Antes, preciso saber: " +
                 lista + "?")
    else:
        texto = ("Não consegui ligar “" + amb.mensagem.strip() + "” a uma das opções. Qual você quer: " + lista + "? " +
                 ("Pode responder com o mês, por exemplo “junho”." if periodos else
                  # Numa planilha (28/10/2026), os grupos não têm sigla: a resposta é o nome ou a posição.
                  "Pode responder com o nome, a sigla do estado ou “o primeiro”, “o segundo”."
                  if amb.fonte.get("tipo", "brasil") == "brasil" else "Pode responder com o nome ou “o primeiro”, “o segundo”."))
    return _resposta(texto, choices=[{"label": _rotulo_alternativa(a), "draft": a.get("rascunho") or "", "send": True,
                                      **({"operation": a["operacao"]} if a.get("operacao") else {})}
                                     for a in alternativas], memoria=memoria, clarification=texto,
                     pedido_original=str((amb.pendente or {}).get("pedido") or ""))


def _cancela_pendente(ato: dict, amb: Ambiente) -> dict:
    texto = "Tudo bem, deixei a pergunta de lado. Nada mudou no gráfico."
    if ato.get("rejeita") and amb.anteriores:
        texto += " Se o que não era o que você queria foi a mudança anterior, diga “desfaz” que eu volto ao que estava antes" + \
            _rotulo_do_estado(amb.anteriores[-1]) + "."
    return _resposta(texto + " O que você quer ver?", memoria={"ato": "cancela_pendente"})


def _completa_pendente(ato: dict, amb: Ambiente) -> dict | None:
    """A resposta a uma pergunta sem alternativas ("Qual município você quer incluir?" → "Anápolis"): o modelo da pergunta
    completado vira o pedido, pelo próprio gestor (com uma comparação aberta, incluir é comparar também) e, sem ato,
    pela gramática."""
    modelo = str((amb.pendente or {}).get("modelo") or "")
    if amb.interpretar is None or "{resposta}" not in modelo:
        return None
    completo = modelo.replace("{resposta}", amb.mensagem.strip().rstrip(".!?"))
    novo = Ambiente(completo, {**amb.conversa, "pendente": None}, amb.ctx, amb.resultado, amb.anterior, amb.fonte,
                    amb.interpretar, amb.nomes, amb.rotulos)
    seguinte = reconhecer(completo, novo.conversa, amb.resultado is not None)
    if seguinte and seguinte.get("ato") in ("inclui", "troca", "tira"):
        resposta = executar(seguinte, novo)
        if resposta is not None:
            return resposta
    resposta = amb.interpretar(completo)
    if not resposta or not resposta.get("handled"):
        return None
    return resposta


def _corrige_pedido(ato: dict, amb: Ambiente) -> dict | None:
    if amb.interpretar is None:
        return None
    resposta = amb.interpretar(ato["resto"])
    if not resposta or not resposta.get("handled"):
        return None
    return _com_prefixo(dict(resposta), "Entendi a correção. ")


def _pedido_indireto(ato: dict, amb: Ambiente) -> dict | None:
    if amb.interpretar is None:
        return None
    resposta = amb.interpretar(ato["pedido"])
    if not resposta or not resposta.get("handled"):
        return None
    return resposta


def _unidades_do_exemplo(amb: Ambiente, quantas: str = "") -> str:
    """A unidade nos exemplos das respostas, com o artigo (28/10/2026): os nomes da resposta ou da tela, com a concordância
    ("as 5 comunas"); sem eles, os da base do Brasil ("os 5 municípios")."""
    unidade = ((amb.resultado or {}).get("rotulos") or {}).get("unidade") or amb.rotulos.get("unidade") or {}
    artigo = "as" if unidade.get("plural") and explicacao._feminino(unidade) else "os"
    return " ".join(parte for parte in (artigo, quantas, unidade.get("plural") or "municípios") if parte)


def _desfaz(ato: dict, amb: Ambiente) -> dict:
    if not amb.anteriores:
        return _resposta("Ainda não mudei nada no gráfico nesta conversa. O que você queria ver? Pode dizer com outras "
                         "palavras, por exemplo “" + _unidades_do_exemplo(amb, "5") + " com maior densidade” ou “mostre a "
                         "tendência”.",
                         memoria={"ato": "desfaz"})
    anterior = amb.anteriores[-1]
    return _resposta("Desfiz a última mudança e voltei ao que estava antes" + _rotulo_do_estado(anterior) + ". O que você "
                     "queria? Pode dizer com outras palavras.", painel=_pedido_como_painel(anterior["pedido"]),
                     desfazer=1, memoria={"ato": "desfaz"})


def _rotulo_do_estado(anterior: dict) -> str:
    rotulo = str(anterior.get("rotulo") or "").strip()
    return (": " + rotulo.rstrip(".")) if rotulo else ""


def _pedido_como_painel(pedido: dict) -> dict:
    from conversa_grafico import CHAVES
    painel = dict.fromkeys(CHAVES)
    for chave in CHAVES:
        if chave in pedido:
            painel[chave] = pedido[chave]
    if pedido.get("visaoTendencia") and not painel.get("visao_tendencia"):
        painel["visao_tendencia"] = pedido["visaoTendencia"]
    return painel


def _volta(ato: dict, amb: Ambiente) -> dict:
    alvo = ato.get("alvo") or "antes"
    def combina(pedido: dict) -> bool:
        if alvo.startswith("comparac"):
            return pedido.get("funcao") == "comparar"
        if alvo in ("tendencia", "distribuicao"):
            return pedido.get("familia") == alvo
        return True
    for posicao in range(len(amb.anteriores) - 1, -1, -1):
        if combina(amb.anteriores[posicao]["pedido"]):
            anterior = amb.anteriores[posicao]
            nome = "à comparação anterior" if alvo.startswith("comparac") else \
                "à tendência anterior" if alvo == "tendencia" else "ao que estava antes"
            # A volta é uma mudança como as outras: a tela guarda o estado atual, e "desfaz" (ou "não era isso") logo depois
            # retorna a ele.
            return _resposta("Voltei " + nome + _rotulo_do_estado(anterior) + ".",
                             painel=_pedido_como_painel(anterior["pedido"]), memoria={"ato": "volta"})
    nome = "comparação anterior" if alvo.startswith("comparac") else "estado anterior do gráfico"
    return _resposta("Não encontrei uma " + nome + " nesta conversa. As análises guardadas ficam no Histórico, no alto da "
                     "página; “volte ao resultado anterior” reabre a última delas.", memoria={"ato": "volta"})


def _ids_da_comparacao(body: dict | None) -> list[str]:
    return [item["id"] for item in ((body or {}).get("comparacao") or {}).get("itens") or []]


def _troca(ato: dict, amb: Ambiente) -> dict | None:
    texto = dobra(amb.mensagem)
    body = amb.resultado or {}
    comparacao = _ids_da_comparacao(body)
    itens = [item["id"] for item in body.get("itens") or [] if item.get("tipo") in ("municipio", "estado")]
    base = comparacao or itens
    rotulo = {item["id"]: item["rotulo"] for item in body.get("itens") or []}
    ordinais = [posicao for chave, posicao in ORDINAIS.items() if chave.isalpha() and len(chave) > 3 and
                re.search(r"\b" + chave + r"\w*", texto)]
    if len(ordinais) >= 2 and len(base) >= 2 and max(ordinais) < len(base):
        a, b = ordinais[0], ordinais[1]
        nova = list(base)
        nova[a], nova[b] = nova[b], nova[a]
        if comparacao:
            painel = _painel(funcao="comparar", selecao=nova)
            return _resposta("Troquei a ordem: agora " + rotulo.get(nova[0], nova[0]) + " é o A e " +
                             rotulo.get(nova[1], nova[1]) + " é o B da comparação (a diferença é A − B).", painel=painel,
                             memoria={"ato": "troca"})
        return _resposta("A ordem dos territórios no gráfico segue o valor do indicador, não a ordem em que foram "
                         "escolhidos. Para trocar a ordem de uma comparação, abra a comparação primeiro (por exemplo, "
                         "“compare os dois”).", memoria={"ato": "troca"})
    marcador = re.search(r"(?i)\b(?:no lugar de|em vez de|ao inv[eé]s de)\b", amb.mensagem)
    if marcador and amb.nomes is not None:
        antes, depois = amb.mensagem[:marcador.start()], amb.mensagem[marcador.end():]
        if not antes.strip(" ,") or re.match(r"(?i)^\s*(?:e\s+)?$", antes):
            # "Em vez de Natal, João Pessoa": quem sai vem primeiro.
            partes_ = re.split(r",", depois, maxsplit=1)
            partes = [partes_[0], partes_[1] if len(partes_) > 1 else ""]
        else:
            partes = [depois, antes]  # "põe João Pessoa no lugar de Natal": quem entra vem primeiro
    else:
        partes = re.split(r"\b(?:por|pelo|pela|pelos|pelas)\b", amb.mensagem, maxsplit=1)
    if len(partes) == 2 and amb.nomes is not None:
        saem_texto = re.sub(r"(?i)\b(?:troc\w*|substitu\w*|em vez de|no lugar de)\b", "", partes[0])
        saem = [i for i in explicacao.localizar(body, saem_texto)]
        entra = amb.nomes(re.sub(r"(?i)\b(?:p[oõ]e|ponha|coloca|coloque|bota|bote|usa|use)\b", "", partes[1]))
        if "pergunta" in entra:
            return entra["pergunta"]
        novos = [i for i in entra.get("ids") or [] if i not in base]
        if saem and novos:
            sai_ids = [body["itens"][i]["id"] for i in saem]
            nova = [novos[0] if x == sai_ids[0] else x for x in base]
            nomes_novos = entra.get("rotulos") or {}
            frase = rotulo.get(sai_ids[0], sai_ids[0]) + " por " + nomes_novos.get(novos[0], novos[0])
            municipios = _base_com(amb, acrescentar=[novos[0]], tirar=[sai_ids[0]])
            if comparacao:
                painel = _painel(funcao="comparar", selecao=nova, municipios=municipios)
                return _resposta("Troquei " + frase + " na comparação.", painel=painel, memoria={"ato": "troca"})
            painel = _painel(municipios=municipios)
            return _resposta("Troquei " + frase + " no gráfico.", painel=painel, memoria={"ato": "troca"})
        if not saem:
            return _resposta("Não encontrei no gráfico o território que deve sair. Diga quem sai, pelo nome de um dos "
                             "territórios do gráfico, e quem entra, como em “troca A por B”.", memoria={"ato": "troca"})
    return None


def _base_com(amb: Ambiente, acrescentar=(), tirar=()) -> dict | None:
    municipios = amb.ctx.get("municipios")
    if not isinstance(municipios, dict):
        ids = [item["id"] for item in (amb.resultado or {}).get("itens") or [] if item.get("tipo") == "municipio"]
        municipios = {"todos": False, "estados": [], "ids": ids}
    if municipios.get("todos"):
        return None
    ids = [i for i in municipios.get("ids") or [] if i not in tirar]
    ids += [i for i in acrescentar if i not in ids]
    return {"todos": False, "estados": list(municipios.get("estados") or []), "ids": ids}


def _painel(**campos) -> dict:
    from conversa_grafico import _painel as painel_da_gramatica
    return painel_da_gramatica(**campos)


def _inclui_sem_nome(ato: dict, amb: Ambiente) -> dict:
    singular = (amb.rotulos.get("unidade") or {}).get("singular") or "município"
    return _resposta("Qual " + singular + " você quer incluir? Diga o nome.",
                     modelo_de_resposta="inclua {resposta}", memoria={"ato": "inclui_sem_nome"})


def _inclui(ato: dict, amb: Ambiente) -> dict | None:
    """Com uma comparação aberta, incluir é comparar também (até 3); sem ela, a gramática inclui no gráfico."""
    comparacao = _ids_da_comparacao(amb.resultado)
    if not comparacao or amb.nomes is None:
        return None
    entra = amb.nomes(re.sub(r"(?i)\b(?:inclu\w*|acrescent\w*|adicion\w*|tamb[eé]m|agora|ponha|poe|bota|coloca|"
                             r"coloque)\b", "", amb.mensagem))
    if "pergunta" in entra:
        return entra["pergunta"]
    novos = [i for i in entra.get("ids") or [] if i not in comparacao]
    if not novos:
        return None
    if len(comparacao) + len(novos) > 3:
        return _resposta("A comparação mostra até 3 itens lado a lado, e já há " + str(len(comparacao)) + ". Diga quem "
                         "sai, por exemplo “troca o primeiro por " + (entra.get("rotulos") or {}).get(novos[0], "…") +
                         "”.", memoria={"ato": "inclui"})
    selecao = comparacao + novos
    nomes = [(entra.get("rotulos") or {}).get(i, i) for i in novos]
    painel = _painel(funcao="comparar", selecao=selecao, municipios=_base_com(amb, acrescentar=novos))
    return _resposta("Incluí " + " e ".join(nomes) + " na comparação, que agora tem " + str(len(selecao)) + " itens.",
                     painel=painel, memoria={"ato": "inclui"})


def _tira(ato: dict, amb: Ambiente) -> dict | None:
    """Com uma comparação aberta, tirar um item também o tira da comparação. Sem ela, tira do gráfico as unidades
    escolhidas uma a uma; as que vieram de um estado inteiro ficam com a gramática."""
    body = amb.resultado or {}
    comparacao = _ids_da_comparacao(body)
    if not comparacao:
        municipios = amb.ctx.get("municipios") if isinstance(amb.ctx.get("municipios"), dict) else {}
        saem = [body["itens"][i]["id"] for i in explicacao.localizar(body, amb.mensagem)]
        if not saem or municipios.get("todos") or any(i not in (municipios.get("ids") or []) for i in saem):
            return None
        rotulo = {item["id"]: item["rotulo"] for item in body.get("itens") or []}
        painel = _painel(municipios=_base_com(amb, tirar=saem))
        return _resposta("Tirei " + " e ".join(rotulo.get(i, i) for i in saem) + " do gráfico.", painel=painel,
                         memoria={"ato": "tira"})
    saem = [body["itens"][i]["id"] for i in explicacao.localizar(body, amb.mensagem)]
    texto = dobra(amb.mensagem)
    for chave, posicao in ORDINAIS.items():
        if chave.isalpha() and len(chave) > 3 and re.search(r"\b" + chave + r"\w*", texto) and posicao < len(comparacao):
            saem.append(comparacao[posicao])
    saem = [i for i in dict.fromkeys(saem) if i in comparacao]
    if not saem:
        return None
    ficam = [i for i in comparacao if i not in saem]
    rotulo = {item["id"]: item["rotulo"] for item in body.get("itens") or []}
    municipios = _base_com(amb, tirar=saem)
    if len(ficam) >= 2:
        painel = _painel(funcao="comparar", selecao=ficam, municipios=municipios)
        return _resposta("Tirei " + " e ".join(rotulo.get(i, i) for i in saem) + "; a comparação continua com " +
                         " e ".join(rotulo.get(i, i) for i in ficam) + ".", painel=painel, memoria={"ato": "tira"})
    painel = _painel(municipios=municipios)
    return _resposta("Tirei " + " e ".join(rotulo.get(i, i) for i in saem) + " do gráfico. Com um item só, a comparação "
                     "saiu.", painel=painel, memoria={"ato": "tira"})


def _todos(ato: dict, amb: Ambiente) -> dict:
    plural = (amb.rotulos.get("unidade") or {}).get("plural") or "municípios"
    painel = _painel(municipios={"todos": True, "estados": [], "ids": []}, nivel="municipios")
    comparacao = " A comparação mostra só 2 ou 3 itens; com todos, ela sai do desenho." if \
        _ids_da_comparacao(amb.resultado) else ""
    return _resposta("Mostrei todos os " + plural + " da base, na mesma análise." + comparacao, painel=painel,
                     memoria={"ato": "todos"})


def _todos_do_estado(ato: dict, amb: Ambiente) -> dict:
    codigo = ato["estado"]
    painel = _painel(municipios={"todos": False, "estados": [codigo], "ids": []}, nivel="municipios")
    from territorial_levels import group_label
    return _resposta("Mostrei os " + group_label(codigo)[0].lower() + group_label(codigo)[1:] + ", na mesma análise.",
                     painel=painel, memoria={"ato": "todos_do_estado"})


def _estado_citado(mensagem: str, texto: str) -> str | None:
    """O código do estado citado ("do Pará", "de SP"), para a comparação pelos extremos dentro dele."""
    for nome in sorted(ESTADOS_POR_NOME, key=len, reverse=True):
        if re.search(r"\b" + re.escape(nome) + r"\b", texto):
            return ESTADOS_POR_NOME[nome]
    sigla = re.search(r"\b(?:d[eoa]s?|em|no|na)\s+([A-Z]{2})\b", mensagem)
    return SIGLAS.get(sigla.group(1).lower()) if sigla else None


UNIDADES_DOS_ATRIBUTOS = {"densidade": " por 1.000 habitantes", "quantidade": " profissionais", "populacao": " habitantes",
                          "distancia_km": " km", "variacao": "%", "permanencia": "%"}


def _valor_do_atributo(item: dict, atributo: str, indicador: str):
    if atributo == "variacao":
        return (item.get("variacao_percentual") or {}).get(indicador)
    if atributo == "permanencia":
        return (item.get("rotatividade") or {}).get("permanencia_percentual")
    return item.get(atributo)


def _compara_extremos(ato: dict, amb: Ambiente) -> dict:
    """Compara, no gráfico, quem tem o maior e o menor valor (ou os dois ou três maiores ou menores), pelas ordens do motor
    sobre o resultado em exibição, com os empates. Nada é comparado aqui: as posições vêm de painel.conversation_facts e
    conversation_top; os valores, copiados da resposta do motor."""
    from painel import conversation_facts, conversation_top
    from resumo_painel import number, places_for
    from territorial_levels import group_label, human_period
    texto = dobra(amb.mensagem)
    body = amb.resultado or {}
    atributo = _atributo(texto) or body.get("indicador") or amb.ctx.get("indicador") or "densidade"
    nome = explicacao.NOMES_DOS_ATRIBUTOS.get(atributo, atributo)
    topo = PRIMEIROS_N.search(texto)
    quantos = QUANTOS_N[topo.group(1)] if topo else None
    maiores = bool(topo) and (topo.group(2).startswith(("maior", "mais", "primeir")) and
                              not re.search(r"\bmais (?:baix|proxim|perto)", texto))
    pedido = ((("os dois" if quantos == 2 else "os três") + (" maiores" if maiores else " menores") + " em " + nome)
              if quantos else "o de maior e o de menor " + nome)
    memoria = {"ato": "compara_extremos", "atributo": atributo}
    if "quantos" in ato and not quantos:
        # "Compare os mais populosos": quantos? A comparação mostra 2 ou 3; cada alternativa é o pedido completo.
        lado = ("maiores" if EXTREMO_ALTO.search(texto) else "menores") + " em " + nome
        return _resposta("A comparação lado a lado mostra 2 ou 3 itens. Quer comparar os dois ou os três " + lado + "?",
                         choices=[{"label": "Os " + quantidade + " " + lado, "draft": "compare os " + quantidade + " " + lado,
                                   "send": True} for quantidade in ("dois", "três")], memoria=memoria)
    # "Qual a diferença entre o maior e o menor?": a comparação abre e, quando o motor calcular, a conversa lê a diferença.
    diferenca = bool(DIFERENCA.search(texto)) and not COMPARA.search(texto)
    estado = _estado_citado(amb.mensagem, texto)
    itens = body.get("itens") or []
    unidades = [item for item in itens if item.get("tipo") in ("municipio", "estado")]
    if estado:
        sigla = STATES[estado][0]
        unidades = [item for item in unidades if item.get("uf") == sigla or str(item.get("rotulo", "")).endswith("(" + sigla + ")")]
        if len(unidades) < 2:
            # O estado não está no gráfico: primeiro os municípios dele; a tela segue com a comparação quando o motor
            # calcular (a continuação lê o gráfico novo, já sem o estado no pedido).
            painel = _painel(municipios={"todos": False, "estados": [estado], "ids": []}, nivel="municipios")
            grupo = group_label(estado)
            return _resposta("Mostrei os " + grupo[0].lower() + grupo[1:] + "; assim que o gráfico estiver pronto, comparo " +
                             pedido + ".", painel=painel, memoria=memoria,
                             continuar=("qual a diferença entre " if diferenca else "compare ") + pedido)
    if len(unidades) < 2:
        return _resposta("Para comparar " + pedido + ", preciso de pelo menos dois territórios no gráfico. Escolha-os na "
                         "Seleção de Territórios ou diga o nome de um estado, e eu comparo " + pedido + ".", memoria=memoria)
    recorte = {**body, "itens": unidades}
    if quantos:
        indices = conversation_top(recorte, atributo, maiores, quantos)
        empate = len(indices) > quantos
    else:
        ordem = conversation_facts(recorte)["ordem"].get(atributo) or {"maior": [], "menor": []}
        indices = list(dict.fromkeys(ordem["maior"] + ordem["menor"]))
        empate = len(ordem["maior"]) > 1 or len(ordem["menor"]) > 1
        if ordem["maior"] and ordem["maior"] == ordem["menor"]:
            indices = []
    rotulos = [unidades[i]["rotulo"] for i in indices]
    if len(indices) < 2:
        return _resposta("No gráfico, não há dois territórios com valores diferentes de " + nome + " para comparar " + pedido +
                         ". Os territórios sem valor ficam em Não avaliáveis, nos Detalhes.", memoria=memoria)
    if len(indices) > 3:
        return _resposta("Há empate: " + ", ".join(rotulos[:-1]) + " e " + rotulos[-1] + " entram em " + pedido +
                         ", e a comparação mostra até 3 itens lado a lado. Diga quais comparar, pelo nome.", memoria=memoria)
    indicador = body.get("indicador") or "densidade"
    valores = [_valor_do_atributo(unidades[i], atributo, indicador) for i in indices]
    casas = places_for([v for v in valores if isinstance(v, (int, float))])
    partes = [rotulo + (", com " + number(valor, casas) + UNIDADES_DOS_ATRIBUTOS.get(atributo, "")
                        if isinstance(valor, (int, float)) else "") for rotulo, valor in zip(rotulos, valores)]
    quando = (" em " + human_period(str(body["competencia"]))) if body.get("competencia") else ""
    onde = (" entre os " + group_label(estado)[0].lower() + group_label(estado)[1:]) if estado else ""
    texto_resposta = ("Abri a comparação lado a lado com " + pedido + onde + quando + ": " + "; ".join(partes) + "." +
                      (" Há empate na posição, e os empatados entram juntos." if empate else "") +
                      (" Assim que o motor calcular a diferença, eu leio para você." if diferenca else
                       " A comparação mostra também a diferença."))
    painel = _painel(funcao="comparar", selecao=[unidades[i]["id"] for i in indices],
                     indicador=atributo if atributo in ("densidade", "quantidade") else None)
    if diferenca:
        return _resposta(texto_resposta, painel=painel, memoria=memoria, continuar="qual a diferença entre eles?")
    return _resposta(texto_resposta, painel=painel, memoria=memoria)


def _compara(ato: dict, amb: Ambiente) -> dict | None:
    body = amb.resultado
    atributo = ato.get("atributo") or (body or {}).get("indicador") or "densidade"
    composicao = explicacao.comparar_atributo(body, atributo, ato.get("maior", True), rotulos=amb.rotulos)
    return _explicada(composicao, {"ato": "compara", "atributo": atributo, "maior": ato.get("maior", True)})


def _diferenca(ato: dict, amb: Ambiente) -> dict | None:
    composicao = explicacao.diferenca(amb.resultado)
    if composicao is not None:
        return _explicada(composicao, {"ato": "diferenca"})
    body = amb.resultado or {}
    unidades = [item["id"] for item in body.get("itens") or [] if item.get("tipo") in ("municipio", "estado")]
    if 2 <= len(unidades) <= 3:
        painel = _painel(funcao="comparar", selecao=unidades)
        return _resposta("A diferença é calculada pela comparação, que ainda não estava aberta: abri a comparação lado a "
                         "lado. O valor da diferença aparece no gráfico e no resumo assim que o motor calcular; depois, "
                         "pergunte de novo e eu leio para você.", painel=painel, memoria={"ato": "diferenca"})
    return _resposta("A diferença entre dois territórios sai da comparação lado a lado, com 2 ou 3 itens. Diga quais, pelo "
                     "nome, ou peça, por exemplo, “compare o de maior e o de menor densidade”.", memoria={"ato": "diferenca"})


def _contagem(ato: dict, amb: Ambiente) -> dict:
    return _explicada(explicacao.contagem(amb.resultado, rotulos=amb.rotulos), {"ato": "contagem"})


def _foco(amb: Ambiente) -> list[int]:
    body = amb.resultado or {}
    citados = explicacao.localizar(body, amb.mensagem)
    if citados:
        return citados
    anteriores = [i for i in amb.memoria.get("foco") or [] if isinstance(i, int)]
    unidades = explicacao.indices_das_unidades(body)
    return [i for i in anteriores if i in unidades] or (unidades if len(unidades) == 1 else [])


def _explica(ato: dict, amb: Ambiente) -> dict | None:
    body = amb.resultado
    registro = ato.get("registro") or "objetivo"
    topico = ato.get("topico") or "resultado"
    foco = _foco(amb)
    if topico == "classificacao":
        if body and body.get("grupos") is not None:
            topico, ato = "conceito", {**ato, "termos": ["quintil"]}
        elif body and body.get("tendencia") is not None:
            topico, ato = "conceito", {**ato, "termos": ["tendencia", "crescimento", "declinio", "sem_classificacao"]}
        elif body and body.get("condicoes") is not None:
            topico = "resultado"
        else:
            topico = "resultado"
    if topico == "territorio":
        unidades = explicacao.indices_das_unidades(body or {})
        alvo = foco or (unidades[:1] if len(unidades) == 1 else [])
        if not body:
            return _explicada(explicacao.explicar_resultado(None, rotulos=amb.rotulos), {"ato": "explica"})
        if not alvo:
            # O exemplo usa um território do próprio gráfico, nunca um nome fora da análise (26/10/2026).
            return _resposta("De qual território? Diga o nome" + (", por exemplo “e para " +
                             body["itens"][unidades[0]]["rotulo"].split(" (")[0].title() + "?”" if unidades else "") +
                             ".", memoria={"ato": "explica", "topico": "territorio", "registro": registro})
        composicao = explicacao.explicar_territorio(body, alvo[0], registro, rotulos=amb.rotulos)
        return _explicada(composicao, {"ato": "explica", "topico": "territorio", "registro": registro, "foco": alvo,
                                       "termos": amb.memoria.get("termos") or []})
    if topico == "conceito":
        termos = ato.get("termos") or []
        composicao = explicacao.explicar_conceito(body, termos, registro, foco)
        return _explicada(composicao, {"ato": "explica", "topico": "conceito", "registro": registro, "termos": termos,
                                       "foco": foco})
    composicao = explicacao.explicar_resultado(body, registro, foco or None, rotulos=amb.rotulos)
    return _explicada(composicao, {"ato": "explica", "topico": "resultado", "registro": registro, "foco": foco})


def _limite(ato: dict, amb: Ambiente) -> dict:
    body = amb.resultado
    foco = _foco(amb)
    if ato.get("tipo") == "causa" and ato.get("comparativo") and body:
        comparacao = explicacao.comparar_atributo(body, ato.get("atributo") or body["indicador"], True, rotulos=amb.rotulos)
        causa = explicacao.limite(body, "causa", amb.mensagem, foco, rotulos=amb.rotulos)
        texto = comparacao["texto"] + "\n\n" + causa["texto"]
        return _resposta(texto, memoria={"ato": "limite", "tipo": "causa"}, explicacao={
            "segmentos": comparacao["segmentos"] + causa["segmentos"],
            "documentacao": comparacao["documentacao"] + causa["documentacao"], "origem": "MOTOR_E_CATALOGO_GOVERNADO"})
    composicao = explicacao.limite(body, ato.get("tipo") or "procedencia", amb.mensagem, foco, rotulos=amb.rotulos)
    return _explicada(composicao, {"ato": "limite", "tipo": ato.get("tipo")})


def _refere_anterior(ato: dict, amb: Ambiente) -> dict:
    if amb.anterior is None:
        return _resposta("Não tenho uma análise anterior nesta conversa para retomar. As análises guardadas ficam no "
                         "Histórico, no alto da página.", memoria={"ato": "refere_anterior"})
    ultimo = amb.memoria.get("ato")
    if ultimo == "compara" and amb.memoria.get("atributo"):
        composicao = explicacao.comparar_atributo(amb.anterior, amb.memoria["atributo"], amb.memoria.get("maior", True))
    else:
        composicao = explicacao.explicar_resultado(amb.anterior, amb.memoria.get("registro") or "objetivo")
    texto = "Certo, sobre a análise anterior: " + composicao["texto"]
    return _resposta(texto, memoria={**amb.memoria, "ato": "refere_anterior"}, explicacao={
        "segmentos": composicao["segmentos"], "documentacao": composicao["documentacao"],
        "origem": "MOTOR_E_CATALOGO_GOVERNADO", "resultado": "anterior"})


def _estado(ato: dict, amb: Ambiente) -> dict:
    assunto = ato.get("assunto")
    body = amb.resultado
    nome, indice = "", None
    if assunto == "ausente":
        citados = explicacao.localizar(body or {}, amb.mensagem)
        if citados:
            indice = citados[0]
        else:
            nome = _nome_citado(amb)
            if not nome:
                return _resposta("De qual território você fala? Diga o nome dele na pergunta.",
                                 memoria={"ato": "estado"})
    if assunto == "mapa" and amb.ctx.get("motivo_sem_mapa") is None and amb.ctx.get("mapa_disponivel") is None:
        pass
    composicao = explicacao.estado(body, assunto, ctx=amb.ctx, fonte=amb.fonte, anterior=amb.anterior, nome=nome,
                                   indice=indice, rotulos=amb.rotulos)
    return _explicada(composicao, {"ato": "estado", "assunto": assunto})


def _nome_citado(amb: Ambiente) -> str:
    """O nome que a pergunta cita ("por que Brasília não aparece?"), como foi escrito, ou resolvido pelo catálogo."""
    if amb.nomes is not None:
        achado = amb.nomes(amb.mensagem)
        if isinstance(achado, dict) and achado.get("rotulos"):
            return next(iter(achado["rotulos"].values()))
    encontrado = re.search(r"(?i)\b(?:por que|porque|pq)\s+(?:o |a |os |as )?(.+?)\s+(?:n[aã]o)\b", amb.mensagem)
    return encontrado.group(1).strip(" ?.,") if encontrado else ""


# --------------------------------------------------------------------------------------------- governança
SUGESTOES = {
    "outro_metodo": "Os métodos são os do motor: na Tendência, as classes dos 4 períodos; na Série temporal, os valores de "
                    "cada competência, sem classificação.",
    "politica": "O que posso fazer é mostrar os números e as análises disponíveis para apoiar a sua decisão.",
    "correlacao": "Posso pôr os territórios lado a lado, ordenar por um atributo ou aplicar condições.",
    "projecao": "Posso mostrar o que já aconteceu: a tendência dos últimos 4 períodos ou a série temporal completa.",
    "pessoas": "As análises usam só contagens agregadas por território.",
    "fontes_externas": "As análises usam só os dados em uso nesta sessão.",
}
DESCRICAO_EXC = {"politica": ("DOC:EXC-02", "recomendação de políticas ou intervenções"),
                 "correlacao": ("DOC:EXC-05", "associação, correlação ou padrão espacial"),
                 "projecao": (None, "projeção"),
                 "pessoas": ("DOC:EXC-09", "registros individualizados"),
                 "fontes_externas": ("DOC:EXC-07", "fontes externas")}


def _governanca_executa(ato: dict, amb: Ambiente) -> dict:
    tipo = ato.get("tipo")
    body = amb.resultado
    docs = []

    def doc(id_doc, forma="base", evidencia=None):
        form = materialize(id_doc, form=forma, evidence=evidencia)
        docs.append(form)
        return form["text"]

    if tipo == "alterar_valor":
        doc("DOC:INV-07")
        doc("DOC:INV-02")
        texto = ("Não altero valores calculados: cada número sai do motor, a partir dos dados em uso, e fica registrado como "
                 "foi calculado. O que muda os números é mudar o recorte: outros territórios, outra competência ou o "
                 "outro indicador (densidade ou quantidade).")
    elif tipo == "valor_do_usuario":
        doc("DOC:INV-02")
        doc("DOC:INV-03")
        texto = ("Não substituo valores da base por valores ditos na conversa: os cálculos usam só os dados em uso, e cada "
                 "número tem a origem registrada. Se você tem outra fonte, envie os dados numa planilha (“enviar meus "
                 "dados”) e eu os uso no gráfico, com a origem indicada.")
    elif tipo == "ranking_de_juizo":
        doc("DOC:CFG-NOR")
        texto = ("Não digo qual é o melhor ou o pior: esta versão não tem critério normativo, e o agente não substitui o seu "
                 "julgamento. Posso ordenar os territórios por um atributo, sem juízo, por exemplo “ordene por densidade, "
                 "do maior para o menor”.")
    elif tipo == "criar_classe":
        doc("DOC:CFG-NOR")
        doc("DOC:EXC-08")
        rotulo = re.search(r"[\"'“‘]([^\"'”’]{2,30})[\"'”’]", amb.mensagem)
        juizo = rotulo.group(1) if rotulo else None
        texto = ("Não crio classificações novas" + (" nem rótulos como “" + juizo + "”" if juizo else "") + ": as classes "
                 "saem só dos métodos do motor, e esta versão não tem critério normativo para dizer o que é adequado ou "
                 "crítico. Posso aplicar o que você descreveu como condição, sem rótulo de juízo: por exemplo, “mostre " +
                 _unidades_do_exemplo(amb) + " com densidade menor que 2”.")
    elif tipo == "outro_metodo":
        texto = ("Não troco o método por conta própria. “" + doc("DOC:TPL-07", "mensagem", "ADM-SC") + "” " +
                 SUGESTOES["outro_metodo"])
        doc("DOC:EXC-08")
    elif tipo == "ocupacao":
        doc("DOC:RQ-CFG-11")
        categoria = (body or {}).get("categoria")
        texto = ("Não incluo outras ocupações nem crio equivalências entre categorias: reconhecer uma categoria da força de "
                 "trabalho segue o vocabulário governado, não a conversa." +
                 (" Nestes dados, a categoria é " + str(categoria) + "." if categoria else ""))
    elif tipo == "afirmar_juizo":
        doc("DOC:CFG-NOR")
        termo = next((_como_escrito(amb.mensagem, t) for t in JUIZO if t in dobra(amb.mensagem)), "isso")
        texto = ("Não afirmo “" + termo + "”: esta versão não tem critério normativo, e sem ele nenhum resultado é "
                 "qualificado assim. Posso mostrar os valores e aplicar uma condição que você definir, por exemplo, "
                 "“mostre " + _unidades_do_exemplo(amb) + " com densidade menor que 1”.")
        if body:
            composicao = explicacao.limite(body, "normativo", amb.mensagem, _foco(amb), rotulos=amb.rotulos)
            texto += "\n\n" + composicao["texto"]
    elif tipo in DESCRICAO_EXC:
        id_doc, descricao = DESCRICAO_EXC[tipo]
        if id_doc:
            doc(id_doc)
        texto = ("Isso fica fora do que faço: “" + doc("DOC:TPL-06", "mensagem", "ADM-FE") + "” (" + descricao + "). " +
                 SUGESTOES[tipo])
    elif tipo == "ignorar_parametro":
        doc("DOC:INV-06")
        competencia = (body or {}).get("competencia")
        from territorial_levels import human_period
        texto = ("Não dá para calcular sem esse parâmetro: cada análise usa uma competência da base (ou os 4 períodos da "
                 "Tendência), e não decido isso por você." +
                 (" O gráfico segue em " + human_period(competencia) + "; diga outra competência, se quiser."
                  if competencia else " Diga qual competência usar."))
    elif tipo == "delegar":
        doc("DOC:EXC-11")
        doc("DOC:INV-06")
        texto = ("Essa escolha fica com você: eu não escolho territórios, critérios ou parâmetros no seu lugar. Diga quais "
                 "quer ver, pelo nome ou por um critério (por exemplo, “" + _unidades_do_exemplo(amb, "5") + " com maior "
                 "densidade”), ou marque na Seleção de Territórios.")
    else:
        texto = "Não posso fazer isso nesta versão."
    return _resposta(texto, memoria={"ato": "governanca", "tipo": tipo},
                     explicacao={"segmentos": [], "documentacao": docs, "origem": "CATALOGO_GOVERNADO"})


EXECUTORES = {
    "responde_pendente": _responde_pendente, "corrige_escolha": _corrige_escolha, "repergunta": _repergunta,
    "cancela_pendente": _cancela_pendente, "completa_pendente": _completa_pendente, "desfaz": _desfaz, "volta": _volta,
    "troca": _troca, "inclui_sem_nome": _inclui_sem_nome, "inclui": _inclui, "tira": _tira, "todos": _todos,
    "todos_do_estado": _todos_do_estado, "compara": _compara, "diferenca": _diferenca, "contagem": _contagem,
    "explica": _explica, "limite": _limite, "refere_anterior": _refere_anterior, "estado": _estado,
    "governanca": _governanca_executa, "corrige_pedido": _corrige_pedido, "pedido_indireto": _pedido_indireto,
    "compara_extremos": _compara_extremos,
}


# --------------------------------------------------------------------------------------------- atos do intérprete
ASSUNTOS_DE_ESTADO = ("dados", "territorios", "selecao", "mapa", "relatorio", "anterior", "mudou", "ausente",
                      "rotatividade", "espacial", "tendencia")
TERMOS_DO_INTERPRETE = {"aceleracao", "desaceleracao", "crescimento", "declinio", "sem_classificacao", "velocidade",
                        "quintil", "densidade", "distancia", "referencia", "agregacao"}
LIMITES_DO_INTERPRETE = {"normativo": "normativo", "melhora": "melhora", "acesso": "acesso", "procedencia": "procedencia"}
GOVERNANCA_DO_INTERPRETE = {"valor": "alterar_valor", "classe": "criar_classe", "metodo": "outro_metodo",
                            "ocupacao": "ocupacao", "juizo": "afirmar_juizo", "politica": "politica",
                            "correlacao": "correlacao", "projecao": "projecao", "pessoas": "pessoas",
                            "externas": "fontes_externas", "parametro": "ignorar_parametro", "delegar": "delegar"}


def do_interprete(ato: dict, mensagem: str, conversa: dict) -> dict | None:
    """O ato que o intérprete com o provedor devolveu (contrato de llm_bridge: dialogue, style, subject, attribute,
    direction), no formato do gestor. Só enumerações atravessam: nomes e valores continuam resolvidos aqui."""
    if not isinstance(ato, dict):
        return None
    tipo, assunto = ato.get("dialogue"), ato.get("subject") or "none"
    registro = ato.get("style") if ato.get("style") in explicacao.REGISTROS else None
    memoria = (conversa or {}).get("memoria") if isinstance((conversa or {}).get("memoria"), dict) else {}
    if tipo == "answer_choice":
        return {"ato": "repergunta"} if _alternativas((conversa or {}).get("pendente")) else None
    if tipo == "correction":
        texto = dobra(mensagem)
        resto = re.sub(r"^(?:nao|na verdade|errado)\b[, ]*(?:eu )?(?:queria|quero|prefiro|era)?\b[, ]*", "", texto)
        return {"ato": "corrige_pedido", "resto": resto or texto}
    if tipo == "undo":
        return {"ato": "desfaz"}
    if tipo == "previous_state":
        return {"ato": "volta", "alvo": "comparacao" if assunto == "comparacao" else "antes"}
    if tipo == "compare_result":
        atributo = ato.get("attribute") if ato.get("attribute") in explicacao.NOMES_DOS_ATRIBUTOS else None
        return {"ato": "compara", "atributo": atributo, "maior": ato.get("direction") != "menor"}
    if tipo in ("concept", "technical", "reformulate"):
        termos = [assunto] if assunto in TERMOS_DO_INTERPRETE else []
        if tipo == "technical":
            registro = "tecnico"
        elif tipo == "reformulate":
            registro = registro or _registro("outro jeito", memoria.get("registro"))
        if termos:
            return {"ato": "explica", "topico": "conceito", "termos": termos, "registro": registro or "objetivo"}
        topico = memoria.get("topico") if memoria.get("ato") == "explica" else "resultado"
        return {"ato": "explica", "topico": topico or "resultado", "termos": memoria.get("termos") or [],
                "registro": registro or "objetivo"}
    if tipo == "verify":
        return {"ato": "limite", "tipo": LIMITES_DO_INTERPRETE.get(assunto, "procedencia")}
    if tipo == "cause":
        return {"ato": "limite", "tipo": "causa"}
    if tipo == "screen_state" and assunto in ASSUNTOS_DE_ESTADO:
        return {"ato": "estado", "assunto": assunto}
    if tipo == "out_of_scope" and assunto in GOVERNANCA_DO_INTERPRETE:
        return {"ato": "governanca", "tipo": GOVERNANCA_DO_INTERPRETE[assunto]}
    if tipo == "include":
        return {"ato": "inclui_sem_nome"}
    if tipo == "replace":
        return {"ato": "troca"}
    if tipo == "remove":
        return {"ato": "tira"}
    if tipo == "all_units":
        return {"ato": "todos"}
    return None
