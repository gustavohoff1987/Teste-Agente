"""Conversa no gráfico da página única (contrato de 22/10/2026, seção 4): o pedido vira o comando `painel`.

Interpreta, nunca calcula. Na página única, a tela envia o estado do gráfico em `options` (a chave `painel_familia`,
mesmo nula, identifica a página única) e recebe, quando o pedido mexe no gráfico, o campo `painel`: família, indicador,
nível, municípios, competência, janela, visão da tendência, referência, função, seleção, ordenação, condições e grupos.
Chave nula: o gráfico mantém o que tem. Nomes e códigos são resolvidos só aqui, pelo catálogo territorial local; nada
da base vai ao provedor de IA. Ambiguidade vira pergunta com alternativas em botões, sem mudar o gráfico. As respostas
dizem o que muda no gráfico, sem valores da base: os números vêm do motor depois (/api/painel).

Planilhas enviadas usam os rótulos da tela (`options.rotulos`: distrito, província...) e o grupo da coluna-mãe (papel
`grupo_territorial` do mapeamento). Detalhes em Docs/CONVERSACAO_INCREMENTO_FN.md, seção "Conversa no gráfico".
"""
import re
import unicodedata

import pandas as pd

from criteria_conversation import CLAUSE, OPERATORS, SYMBOL, _value
from exploration import MONTHS, NUMBER_WORDS, RELATIVE_YEARS, WORDS, _human, _listed, normalize, relative_years
from semantic_bridge import ROLES
from territorial_selection import REGIONS, STATES, territory_catalog, texts

CHAVES = ("familia", "indicador", "nivel", "municipios", "competencia", "janela", "visao_tendencia", "referencia",
          "funcao", "selecao", "ordenar", "condicoes", "grupos")
FAMILIAS = ("distribuicao", "espacial", "tendencia", "rotatividade")
# Estado do gráfico enviado pela tela (contrato, seção 4, e extensões documentadas); sai das opções do intérprete.
CONTEXTO = ("painel_familia", "painel_indicador", "painel_nivel", "painel_municipios", "painel_competencia",
            "painel_janela", "painel_referencia", "painel_condicoes", "rotulos", "conversation_pending_ids")
# Operações atuais → família, indicador e função do gráfico (contrato, seção 4).
OPERACOES = {
    "density": {"familia": "distribuicao", "indicador": "densidade"},
    "counts": {"familia": "distribuicao", "indicador": "quantidade"},
    "distribution": {"familia": "distribuicao"},
    "temporal": {"familia": "tendencia"},
    "spatial": {"familia": "espacial"},
    "nearest": {"familia": "espacial"},
    "comparisons": {"funcao": "comparar"},
    "aggregate": {"funcao": "juntar"},
    "ranking": {"funcao": "ordenar"},
    "criteria": {"funcao": "condicoes"},
    "rotation": {"familia": "rotatividade"},
    "report": {"funcao": "exportar"},
}
INDICADORES = {"density": "densidade", "quantity": "quantidade", "densidade": "densidade", "quantidade": "quantidade"}
ANTIGOS = {"densidade": "density", "quantidade": "quantity"}
CONTINUIDADE = {"tendencia": "temporal", "espacial": "spatial", "rotatividade": "rotation"}
TIPOS_GRUPO = {"quart": "quartis", "quint": "quintis", "dec": "decis"}
VISOES = {"mudanca": "Mudança", "classes": "Classes", "series": "Séries"}
ATRIBUTO_TEXTO = {"densidade": "pela densidade", "quantidade": "pela quantidade", "populacao": "pela população",
                  "distancia_km": "pela distância até a referência", "variacao": "pela variação"}
ORDEM_TEXTO = {"desc": "do maior para o menor", "asc": "do menor para o maior"}
OPERADOR_TEXTO = {"<": "menor que", "<=": "no máximo", ">": "maior que", ">=": "no mínimo", "=": "igual a",
                  "!=": "diferente de"}
NADA_MUDOU = " Nada mudou no gráfico."
SEM_PONTO_UNICO = ("A referência é um município ou um conjunto de municípios: estados não têm um ponto único. Diga os "
                   "municípios, por exemplo, “use Manaus como referência”." + NADA_MUDOU)

# Palavras que acompanham os pedidos sem mudar o que eles pedem.
NEUTRAS = frozenset("""
a o as os um uma uns umas de do da dos das em no na nos nas ao aos por pelo pela pelos pelas para pra pro pros pras com
e que qual quais quanto quantos quantas onde como isso isto esse essa esses essas este esta estes estas aquele aquela
me mim eu voce voces meu minha meus minhas seu sua seus suas ele ela eles elas lhe tudo todo toda todos todas cada mais
menos apenas so somente tambem agora entao ok certo sim favor obrigado obrigada ai la aqui ja ainda tem tinha ha existe
existem possui possuem
mostre mostrar mostra mostrando exiba exibir exibe abra abrir abre veja ver vejo visualize visualizar foque focar foca
apresente apresentar traga trazer quero queria gostaria preciso desejo pode poderia podemos vamos va vai ir faca faz
fazer facamos coloque colocar coloca ponha bote use usar usa usando troque trocar troca mude mudar muda passe passar
passa volte voltar volta retorne retornar selecione selecionar escolha escolher deixe deixar fique ficar fica considere
considerar analise analisar analisa examine examinar
grafico graficos tela bolha bolhas painel eixo valor valores dado dados indicador indicadores visao tabela arquivo
municipio municipios cidade cidades estado estados uf ufs territorio territorios unidade unidades brasil referencia
referencias conjunto km
densidade quantidade quantitativo quantitativos medico medicos medica medicas medicina profissional profissionais saude
habitantes populacao numero total
""".split())
# Nomes de município que são também palavras do domínio ("profissionais de saúde" não é o município de Saúde, BA).
COMUNS = frozenset({"saude"})

NUM_ALT = r"\d{1,5}|" + "|".join(sorted(NUMBER_WORDS, key=len, reverse=True))
ATRIBUTO_ALT = (r"densidade|quantidade|populacao|distancia|variacao|aumento|reducao|queda|populos[oa]s?|distantes?|"
                r"proxim[oa]s?|medic[oa]s|profissionais")
TOPO = re.compile(r"\b(?:(?:os|as)\s+)?(?P<n>" + NUM_ALT + r")\s+(?:[a-z']+\s+){0,5}?"
                  r"(?P<dir>maior(?:es)?|menor(?:es)?|mais|menos)\s+(?P<attr>" + ATRIBUTO_ALT + r")\b")
QUAL = re.compile(r"\b(?P<qual>qual|quais)\s+(?:[a-z']+\s+){0,5}?(?P<dir>maior(?:es)?|menor(?:es)?|mais|menos)\s+"
                  r"(?P<attr>" + ATRIBUTO_ALT + r")\b")
PRIMEIROS = re.compile(r"\b(?:(?:os|as)\s+)?(?P<n>" + NUM_ALT + r")\s+primeir[oa]s\b")
TOP = re.compile(r"\btop\s*(?P<n>" + NUM_ALT + r")\b")
ORDENAR = re.compile(r"\b(?:ordene|ordenar|ordena|ordenad[oa]s?|ordenacao|classifique|classificar|classifica|ranking|"
                     r"ranqueie|ranquear|rankeie|rankear)\b|\b(?:em|por)\s+ordem\b")
ATRIBUTO_SIMPLES = re.compile(r"\b(densidade|quantidade|populacao|distancia|variacao)\b")
DECRESCENTE = re.compile(r"\b(?:decrescente|(?:do\s+)?maior(?:es)?\s+(?:para|ao|pro)\s+(?:o\s+)?menor(?:es)?|"
                         r"maiores\s+primeiro|mais\s+distantes?\s+primeiro)\b")
CRESCENTE = re.compile(r"\b(?:crescente|(?:do\s+)?menor(?:es)?\s+(?:para|ao|pro)\s+(?:o\s+)?maior(?:es)?|"
                       r"menores\s+primeiro|mais\s+proxim[oa]s?\s+primeiro)\b")
ALVO_ORDEM = re.compile(r"\s*(?:de|da|do|ate|a|ao|em\s+relacao\s+(?:a|ao))\s+")

COMPARAR = re.compile(r"\b(?:compare|comparar|compara|comparacao|comparando|confronte|confrontar)\b|\blado\s+a\s+lado\b")
JUNTAR = re.compile(r"\b(?:junte|juntar|junta|juntando|juncao|agrupe|agrupar|agrupa|agregue|agregar|agrega|agregacao|"
                    r"some|somar)\b|\b(?:faca|faz|crie|cria|monte|forme|gere)\s+(?:um\s+)?conjunto\b|"
                    r"\b(?:num|em\s+um)\s+(?:so\s+)?conjunto\b")
DEIXIS = re.compile(r"\b(?:esses|estes|essas|estas|selecionad[oa]s|marcad[oa]s)\b")
EXPORTAR = re.compile(r"\b(?:exporte|exportar|exporta|exportacao|baixe|baixar|baixa|download|csv|imprima|imprimir|"
                      r"impressao|pdf|relatorio)\b")

COMO_REFERENCIA = re.compile(r"\bcomo\s+(?:(?:a|o|minha|meu|nova|novo)\s+){0,2}(?:referencias?|conjunto\s+de\s+referencia|"
                             r"ponto\s+de\s+referencia)\b")
REFERENCIA_E = re.compile(r"\b(?:a\s+)?(?:nova\s+)?referencias?(?:\s*[:=]\s*|\s+(?:e|sera|seja|fica|vai\s+ser|passa\s+a\s+ser|"
                          r"agora\s+e)\s+)")
REFERENCIA_EM = re.compile(r"\b(?:com\s+)?(?:a\s+)?referencias?\s+(?:em|no|na|nos|nas)\s+")
DISTANCIA_ATE = re.compile(r"\bdistancias?\s+(?:(?:em\s+linha\s+reta|geodesicas?|em\s+km)\s+)?(?:ate|a|ao|aos|as|de|do|da|"
                           r"dos|das|desde|para|em\s+relacao\s+(?:a|ao|aos|as))\s+")
DIVISOR = re.compile(r"\b(?:com|usando|use|usar|coloque|ponha|defina|deixe|tome|considere|escolha)\b")
CRITERIO = re.compile(r"\b(maior|menor)\s+(densidade|quantidade|populacao)\b|\b(mais|menos)\s+(populos[oa]s?|medic[oa]s|"
                      r"profissionais)\b")

TENDENCIA = re.compile(r"\b(?:tendencias?|evolucao|evolucoes|evoluir|evoluiu|serie\s+temporal|series\s+temporais|"
                       r"ao\s+longo\s+do\s+tempo)\b")
FAMILIAS_PADROES = ((re.compile(r"\bdistribuic(?:ao|oes)\b"), "distribuicao"), (TENDENCIA, "tendencia"),
                    (re.compile(r"\b(?:analise\s+espacial|espacial|eixo\s+x|distancias?)\b"), "espacial"),
                    (re.compile(r"\b(?:rotatividade|permanencia|coorte)\b"), "rotatividade"))
VISOES_PADROES = (("classes", re.compile(r"\bclasses\b(?!\s+de\s+posicao)")),
                  ("series", re.compile(r"\b(?:series|linhas)\b")),
                  ("mudanca", re.compile(r"\b(?:mudanca|cometas?)\b")))
GRUPOS_VISTA = re.compile(r"\b(?:(?:em|por|nos|nas|com)\s+)?(quart|quint|dec)(?:is|il)\b")
SEM_GRUPOS = re.compile(r"\bsem\s+(?:os\s+)?(?:grupos|quartis|quintis|decis|classes\s+de\s+posicao)\b|"
                        r"\b(?:tire|retire|remova)\s+(?:os\s+)?(?:grupos|quartis|quintis|decis)\b")
GRUPOS_SEM_TIPO = re.compile(r"\b(?:classes\s+de\s+posicao|grupos\s+(?:por|de)\s+posicao)\b")
DENSIDADE = re.compile(r"\bdensidade\b|\bpor\s+(?:mil|1\.?000)\s+habitantes\b")
QUANTIDADE = re.compile(r"\b(?:quantidade|quantitativos?|numero\s+de\s+(?:medic[oa]s|profissionais)|"
                        r"quant[oa]s\s+(?:medic[oa]s|profissionais)|total\s+de\s+(?:medic[oa]s|profissionais))\b")
ACRESCENTAR = re.compile(r"\b(?:acrescente|acrescentar|acrescenta|adicione|adicionar|adiciona|inclua|incluir|inclui)\b")
RETIRAR = re.compile(r"\b(?:tire|tirar|tira|retire|retirar|retira|remova|remover|remove|exclua|excluir|exclui|esconda|"
                     r"esconder)\b")
VERBO_VISTA = re.compile(r"\b(?:mostre|mostrar|mostra|exiba|exibir|exibe|abra|abrir|abre|veja|ver|visualize|visualizar|"
                         r"foque|focar|apresente|apresentar|traga|trazer|quero|queria|gostaria)\b")
EXPLICACAO = re.compile(r"\b(?:entender|explique|explica|explicar|significa|significado|conceito|definicao|calcula|"
                        r"calculada|calculado|calculo|metodo|formula)\b")
TAMBEM = re.compile(r"\b(?:tambem|alem\s+disso|adicionalmente|mais\s+uma\s+condicao)\b")
PERGUNTA = re.compile(r"\s*(?:o\s+que|por\s*que|porque|como|qual|quais|quanto|quantos|quantas|onde|quando)\b")

MESES = MONTHS + [mes[:3] for mes in MONTHS]
MES = re.compile(r"\b(" + "|".join(MESES) + r")\.?\s*(?:de\s+|/|-)?\s*((?:19|20)\d{2})\b")
AAAAMM = re.compile(r"\b((?:19|20)\d{2})-?(0[1-9]|1[0-2])\b")
SERIE_ANUAL = re.compile(r"\bseries?\s+anua(?:l|is)(?:\s+de\s+junho)?\b|\b(?:so|somente|apenas)\s+(?:(?:os|as)\s+)?"
                         r"(?:junhos|competencias\s+de\s+junho)\b")
JUNHOS = re.compile(r"\bultim[oa]s\s+(" + NUM_ALT + r")\s+junhos\b")
TODAS = re.compile(r"\btod[oa]s\s+(?:[oa]s\s+)?(?:competencias|periodos)\b")
FAIXA = re.compile(r"\b(?:entre|de|desde|do\s+ano\s+de)\s+((?:19|20)\d{2})\s+(?:e|a|ate|para)\s+((?:19|20)\d{2})\b")
DESDE = re.compile(r"\b(?:a\s+partir\s+de|desde)\s+((?:19|20)\d{2})\b")
ATE = re.compile(r"\bate\s+((?:19|20)\d{2})\b")
ANO = re.compile(r"\b(?:em|de|no|do|para|ano\s+de|ano)\s+((?:19|20)\d{2})\b")
PREFIXO_RELATIVO = re.compile(r"\b(?:(?:n|d)?[oa]s|em|nest[ea]s|ness[ea]s)\s+$")

REGIAO = re.compile(r"\b(?:(?P<unidades>municipios|cidades)\s+(?:da|de|do|na|no)\s+(?:regiao\s+)?|(?:estados|ufs)\s+"
                    r"(?:da|do|de)\s+(?:regiao\s+)?|regiao\s+)(?P<regiao>norte|nordeste|sudeste|sul|centro[\s-]oeste)\b")
SUFIXO = re.compile(r"\s*(?:\(\s*([a-z]{2})\s*\)|[-/]\s*([a-z]{2})(?![a-z0-9])|\[\s*([^\]]+?)\s*\])")

UNIDADE_OUTRA_ESCALA = re.compile(r"\s*(?:(?:medic[oa]s?|profissionais?|trabalhadore?s?)\s+)?(?:por|a\s+cada|/)\s*"
                                  r"(?:10|100)\s*(?:mil|\.?000)")
UNIDADE_POR_MIL = re.compile(r"\s*(?:(?:medic[oa]s?|profissionais?|trabalhadore?s?)\s+)?(?:por|a\s+cada|/)\s*"
                             r"(?:1\.?000|mil)(?:\s+(?:habitantes|hab|pessoas))?\b")
UNIDADE_KM = re.compile(r"\s*(?:km|quilometros?)\b")
UNIDADE_METROS = re.compile(r"\s*(?:m|metros?)\b")
UNIDADE_MIL_HABITANTES = re.compile(r"\s*mil\s+(?:habitantes|pessoas)\b")
UNIDADE_HABITANTES = re.compile(r"\s*(?:habitantes|pessoas)\b")
UNIDADE_PROFISSIONAIS = re.compile(r"\s*(?:medic[oa]s?|profissionais?|trabalhadore?s?)\b")
ATRIBUTO_ANTES = re.compile(r"\b(densidade|distancia|populacao|quantidade|quantitativo)\b")
ALVO_DISTANCIA = re.compile(r"\s*(?:de|da|do|ate|a\s+partir\s+de|em\s+relacao\s+(?:a|ao|aos|as))\s+")


# --------------------------------------------------------------------------------------------- formas de texto
def _milhar(numero):
    return f"{int(numero):,}".replace(",", ".")


def _e(itens):
    itens = list(itens)
    if not itens:
        return ""
    return itens[0] if len(itens) == 1 else ", ".join(itens[:-1]) + " e " + itens[-1]


def _maiuscula(texto):
    return texto[:1].upper() + texto[1:]


def _quantos(texto):
    return int(texto) if texto.isdigit() else NUMBER_WORDS.get(texto, 0)


def _numero(valor):
    """Valor escrito pelo usuário ("2.36", "150") como número JSON, sem arredondar."""
    numero = float(valor)
    return int(numero) if numero.is_integer() and "." not in valor else numero


def _painel(**campos):
    painel = dict.fromkeys(CHAVES)
    painel.update(campos)
    return painel


def _resposta(painel, texto):
    return {"handled": True, "executed": False, "painel": painel, "reply": texto}


def _so_texto(texto):
    return {"handled": True, "executed": False, "reply": texto}


def _pergunta(texto, escolhas=None, ambiguidade=None):
    resposta = {"handled": True, "executed": False, "clarification": texto}
    if escolhas:
        resposta["choices"] = escolhas
    if ambiguidade:
        resposta["ambiguity"] = ambiguidade
    return resposta


def _escolha(rotulo, rascunho):
    return {"label": rotulo, "draft": rascunho, "send": True}


# --------------------------------------------------------------------------------------------- mapeamento atual
def painel_da_operacao(operacao, indicador=None, mensagem=""):
    """Operação atual (proposta do intérprete ou escolha em botão) → família, indicador e função do gráfico."""
    if not isinstance(operacao, str) or operacao not in OPERACOES:
        return None
    painel = _painel(**OPERACOES[operacao])
    if painel["indicador"] is None and isinstance(indicador, str) and indicador in INDICADORES:
        painel["indicador"] = INDICADORES[indicador]
    if operacao == "distribution":
        tipo = GRUPOS_VISTA.search(normalize(mensagem or ""))
        painel["grupos"] = {"tipo": TIPOS_GRUPO[tipo[1]]} if tipo else None
    return painel


def _condicao_do_criterio(folha):
    atributo = {"densidade": "densidade", "distancia": "distancia_km", "populacao": "populacao",
                "quantidade": "quantidade"}.get(folha.get("attribute"))
    if atributo is None or folha.get("unit") not in (None, "por_1000_habitantes", "km", "habitantes"):
        return None  # outra escala (por 100 mil, metros): o gráfico usa por mil habitantes e km
    try:
        valor = _numero(str(folha.get("value")))
    except ValueError:
        return None
    return {"atributo": atributo, "operador": folha.get("operator"), "valor": valor}


def painel_do_legado(resposta):
    """Resposta da interpretação local anterior à página única → painel (mapeamento das operações atuais)."""
    if not isinstance(resposta, dict) or not resposta.get("handled") or resposta.get("clarification"):
        return None
    patch = resposta.get("criteria_patch")
    if isinstance(patch, dict):
        folha = patch.get("leaf")
        if isinstance(folha, dict) and patch.get("mode") in ("replace", "and"):
            item = _condicao_do_criterio(folha)
            if item is None:
                return None
            return _painel(funcao="condicoes", condicoes=[item],
                           familia="espacial" if item["atributo"] == "distancia_km" else None)
        ranking = patch.get("ranking") if isinstance(patch.get("ranking"), dict) else {}
        if ranking.get("attribute") or patch.get("top_n"):
            atributo = {"distancia": "distancia_km"}.get(ranking.get("attribute"), ranking.get("attribute"))
            return _painel(funcao="ordenar", ordenar={"atributo": atributo, "ordem": ranking.get("direction"),
                                                      "primeiros": patch.get("top_n")})
        return None
    painel = painel_da_operacao(resposta.get("operation"))
    if painel is None:
        return None
    opcoes = resposta.get("options_patch") or {}
    for chave in ("comparison_indicator", "temporal_indicator"):
        if painel["indicador"] is None and isinstance(opcoes.get(chave), str) and opcoes[chave] in INDICADORES:
            painel["indicador"] = INDICADORES[opcoes[chave]]
    if opcoes.get("period_filter"):
        painel["competencia"] = opcoes["period_filter"]
    elif opcoes.get("period_filters"):
        painel["janela"] = list(opcoes["period_filters"])
    ids = list(resposta.get("territory_ids") or [])
    estados = list(resposta.get("estados") or [])
    if painel["funcao"] in ("comparar", "juntar"):
        if estados and not ids:
            painel.update(nivel="estados", selecao=["uf:" + uf for uf in estados])
        elif ids and not estados:
            painel["selecao"] = ids
    elif estados and not ids:
        painel["nivel"] = "estados"
    elif ids and not estados:
        painel.update(nivel="municipios", municipios={"todos": False, "estados": [], "ids": ids})
    return painel


def com_painel(resposta):
    """A resposta da interpretação local anterior, com o painel equivalente quando ele existe."""
    painel = painel_do_legado(resposta)
    return {**resposta, "painel": painel} if painel else resposta


# --------------------------------------------------------------------------------------------- contexto da tela
def _textos(valor, limite=10000):
    if not isinstance(valor, list):
        return []
    return list(dict.fromkeys(item for item in valor[:limite] if isinstance(item, str) and item))


def _base_valida(valor):
    if not isinstance(valor, dict) or not isinstance(valor.get("todos", False), bool):
        return None
    return {"todos": bool(valor.get("todos")), "estados": _textos(valor.get("estados")), "ids": _textos(valor.get("ids"))}


def contexto(options):
    """Estado do gráfico enviado pela tela da página única; None nas demais telas (sem a chave painel_familia)."""
    if not isinstance(options, dict) or "painel_familia" not in options:
        return None
    operacao = options.get("exploration_operation") if isinstance(options.get("exploration_operation"), str) else None
    familia = next((valor for valor in (options.get("painel_familia"), operacao) if valor in FAMILIAS), None) or \
        OPERACOES.get(operacao or "", {}).get("familia")
    indicador = None
    ordem = ("temporal_indicator", "comparison_indicator") if familia == "tendencia" else \
        ("comparison_indicator", "temporal_indicator")
    for chave in ("painel_indicador", *ordem, "exploration_indicator"):
        valor = options.get(chave)
        if indicador is None and isinstance(valor, str) and valor in INDICADORES:
            indicador = INDICADORES[valor]
    brutos = _textos(options.get("territory_ids"))
    ids = [item for item in brutos if item.startswith(("code:", "name:"))]
    ufs = [item for item in brutos if item.startswith("uf:")]
    nivel = options.get("painel_nivel") if options.get("painel_nivel") in ("estados", "municipios") else \
        ("municipios" if ids else "estados" if ufs else None)
    competencia = next((valor for valor in (options.get("painel_competencia"), options.get("period_filter"))
                        if isinstance(valor, str) and valor), None)
    janela = _textos(options.get("painel_janela")) or _textos(options.get("period_filters"))
    condicoes = options.get("painel_condicoes")
    rotulos = options.get("rotulos")
    return {"familia": familia, "indicador": indicador, "nivel": nivel,
            "municipios": _base_valida(options.get("painel_municipios")), "ids": ids, "competencia": competencia,
            "janela": janela, "referencia": _textos(options.get("painel_referencia")),
            "condicoes": [item for item in condicoes if isinstance(item, dict)] if isinstance(condicoes, list) else [],
            "rotulos": rotulos if isinstance(rotulos, dict) else {},
            # Unidade já identificada numa comparação pendente ("compare Manaus" → "com qual outro?").
            "pendentes": [item for item in _textos(options.get("conversation_pending_ids"))
                          if item.startswith(("code:", "name:"))]}


def opcoes_do_interprete(options, ctx):
    """Opções do intérprete e do pré-exame a partir do estado do gráfico: só municípios em territory_ids (lista vazia
    sai), competência ou janela (nunca as duas), a família como operação ativa e o indicador no formato antigo."""
    opcoes = {chave: valor for chave, valor in options.items() if chave not in CONTEXTO}
    if ctx["ids"]:
        opcoes["territory_ids"] = list(ctx["ids"])
    else:
        opcoes.pop("territory_ids", None)
    if opcoes.get("period_filter") and opcoes.get("period_filters"):
        if ctx["familia"] == "tendencia":
            opcoes["period_filter"] = ""
        else:
            opcoes["period_filters"] = []
    operacao = opcoes.get("exploration_operation")
    if not isinstance(operacao, str) or operacao not in OPERACOES:
        antiga = CONTINUIDADE.get(ctx["familia"]) or (
            ("counts" if ctx["indicador"] == "quantidade" else "density") if ctx["familia"] == "distribuicao" else None)
        if antiga:
            opcoes["exploration_operation"] = antiga
        else:
            opcoes.pop("exploration_operation", None)
    for chave in ("comparison_indicator", "temporal_indicator", "exploration_indicator", "distribution_indicator"):
        if isinstance(opcoes.get(chave), str) and opcoes[chave] in ANTIGOS:
            opcoes[chave] = ANTIGOS[opcoes[chave]]
    if ctx["indicador"] and not opcoes.get("exploration_indicator"):
        opcoes["exploration_indicator"] = ANTIGOS[ctx["indicador"]]
    return opcoes


def campos_do_mapeamento(fields):
    """O papel grupo_territorial (coluna-mãe das planilhas) sai do mapeamento do pré-exame e vale só para a conversa."""
    campos = dict(fields)
    grupo = campos.pop("grupo_territorial", None)
    return campos, grupo if isinstance(grupo, str) and grupo else None


def papeis_escolhidos(options, fields):
    """Planilha enviada: o mapeamento que a tela envia é a escolha da pessoa (decisão D1), inclusive o código."""
    atuais = options.get("confirmed_roles") if isinstance(options.get("confirmed_roles"), list) else []
    escolhidos = [papel for papel, coluna in fields.items() if papel in ROLES and isinstance(coluna, str) and coluna]
    return {**options, "confirmed_roles": list(dict.fromkeys([*atuais, *escolhidos]))}


def comando_do_grafico(mensagem):
    """Ordenação pedida como pergunta ("quais os 5 com maior densidade?"): é comando do gráfico, não explicação."""
    texto = normalize(mensagem)
    return bool(TOPO.search(texto) or QUAL.search(texto) or ORDENAR.search(texto) or PRIMEIROS.search(texto) or
                TOP.search(texto))


def aplicar(resposta, resolvido):
    """Rota com o provedor de IA, na página única: o comando do gráfico e a resposta da conversa local entram no lugar
    da proposta textual; a verificação do pré-exame continua na resposta."""
    if not isinstance(resolvido, dict) or not resolvido.get("handled"):
        return resposta
    resposta.pop("exploration", None)
    if resolvido.get("painel"):
        resposta["painel"] = resolvido["painel"]
    if resolvido.get("clarification"):
        resposta["reply"] = resolvido["clarification"]
        resposta["clarification"] = {"code": resolvido.get("ambiguity") or "ESCOLHA_NO_GRAFICO",
                                     "prompt": resolvido["clarification"], "choices": resolvido.get("choices") or [],
                                     "reason": "O pedido precisa de uma escolha antes de mudar o gráfico.",
                                     "source": "CATALOGO_LOCAL", "answered": False}
    else:
        resposta["reply"] = resolvido.get("reply") or resposta.get("reply")
        resposta.pop("clarification", None)
    return resposta


# --------------------------------------------------------------------------------------------- pedido e catálogo
class _Pedido:
    """O pedido dobrado (minúsculas, sem acentos), com a posição de cada caractere no original. Os trechos reconhecidos
    viram espaços em `resto`, sem mudar as posições."""

    def __init__(self, mensagem):
        self.original = unicodedata.normalize("NFC", mensagem)
        partes, self.posicoes = [], []
        for indice, caractere in enumerate(self.original):
            dobrado = "".join(c for c in unicodedata.normalize("NFD", caractere.lower()) if not unicodedata.combining(c))
            partes.append(dobrado)
            self.posicoes.extend([indice] * len(dobrado))
        self.texto = "".join(partes)
        self.resto = self.texto

    def consome(self, inicio, fim):
        self.resto = self.resto[:inicio] + " " * (fim - inicio) + self.resto[fim:]

    def trecho(self, inicio, fim):
        """O trecho [inicio, fim) do texto dobrado, como foi escrito."""
        return self.original[self.posicoes[inicio]:self.posicoes[fim - 1] + 1] if fim > inicio else ""

    def reescreve(self, inicio, fim, novo):
        """O pedido original com o trecho [inicio, fim) trocado: rascunho de uma alternativa em botão."""
        antes, depois = self.original[:self.posicoes[inicio]], self.original[self.posicoes[fim - 1] + 1:]
        return " ".join((antes + novo + depois).split())


class _Catalogo:
    """Unidades e grupos da base, só para resolver os nomes do pedido (nada daqui vai ao provedor)."""

    def __init__(self, itens, brasil, grupos_planilha=None):
        self.brasil = brasil
        self.itens = {item["id"]: item for item in itens}
        self.nomes = {}
        for item in itens:
            chave = normalize(str(item["name"]))
            if chave:
                self.nomes.setdefault(chave, []).append(item["id"])
        self.grupos = {}
        if brasil:
            for item in itens:
                if item.get("state_code"):
                    self.grupos.setdefault(item["state_code"], {"nome": item["state_name"], "membros": []})[
                        "membros"].append(item["id"])
        else:
            for valor, membros in (grupos_planilha or {}).items():
                self.grupos[valor] = {"nome": valor, "membros": [membro for membro in membros if membro in self.itens]}
        self.por_grupo = {}
        for chave, grupo in self.grupos.items():
            nome = normalize(str(grupo["nome"]))
            if nome:
                self.por_grupo.setdefault(nome, chave)
        self.expressoes = sorted(set(self.nomes) | set(self.por_grupo), key=lambda valor: (-len(valor), valor))

    def rotulo(self, identificador):
        item = self.itens.get(identificador)
        if item is None:
            return identificador
        if self.brasil and item.get("state"):
            return item["name"] + " (" + item["state"] + ")"
        return item["label"]

    def membros(self, base):
        if base["todos"]:
            return set(self.itens)
        return {membro for chave in base["estados"] for membro in self.grupos.get(chave, {}).get("membros", [])} | \
            {identificador for identificador in base["ids"] if identificador in self.itens}


def _grupos_planilha(frame, fields, coluna):
    """Planilha enviada: unidades de cada valor da coluna-mãe (papel grupo_territorial), com os ids do catálogo."""
    if coluna not in frame.columns or coluna in (fields.get("territory"), fields.get("territory_id")):
        return None
    codigo = fields.get("territory_id")
    prefixo = "code:" if codigo else "name:"
    pares = pd.DataFrame({"id": texts(frame[codigo or fields["territory"]]),
                          "grupo": texts(frame[coluna])}).dropna().drop_duplicates()
    grupos = {}
    for unidade, grupo in zip(pares["id"], pares["grupo"]):
        grupos.setdefault(str(grupo), []).append(prefixo + str(unidade))
    return grupos


def _periodos(frame, fields):
    coluna = fields.get("period")
    if frame is None or not coluna or coluna not in frame.columns:
        return []
    return sorted(set(texts(frame[coluna]).dropna().astype(str)))


class _Rotulos:
    def __init__(self, singular, plural, feminino, grupo_singular, grupo_plural, grupo_feminino):
        self.singular, self.plural, self.feminino = singular, plural, feminino
        self.grupo_singular, self.grupo_plural, self.grupo_feminino = grupo_singular, grupo_plural, grupo_feminino

    def unidades(self, quantidade):
        """“144 municípios”, “1 distrito”."""
        return _milhar(quantidade) + " " + (self.singular if quantidade == 1 else self.plural)

    def nas(self, quantidade):
        """“nos 144 municípios”, “nas 12 comunas”, “em 1 município”."""
        if quantidade == 1:
            return "em " + self.unidades(1)
        return ("nas " if self.feminino else "nos ") + self.unidades(quantidade)

    def um(self):
        return ("uma " if self.feminino else "um ") + self.singular

    def os(self):
        return ("as " if self.feminino else "os ") + self.plural


def _palavra(valor):
    return " ".join(valor.split())[:40] if isinstance(valor, str) else ""


def _feminino(dados, palavra):
    """Gênero do rótulo: o informado pela tela ("genero") ou o da terminação da primeira palavra."""
    genero = dados.get("genero")
    if isinstance(genero, str) and genero.strip():
        return normalize(genero).startswith("f")
    primeira = normalize(palavra).split()
    return bool(primeira) and primeira[0].endswith(("a", "ade", "cao", "sao", "giao", "gem", "ie"))


def _rotulos(ctx, brasil):
    if brasil:
        return _Rotulos("município", "municípios", False, "estado", "estados", False)
    dados = ctx.get("rotulos") or {}
    unidade = dados.get("unidade") if isinstance(dados.get("unidade"), dict) else {}
    grupo = dados.get("grupo") if isinstance(dados.get("grupo"), dict) else {}
    singular = _palavra(unidade.get("singular")) or "município"
    plural = _palavra(unidade.get("plural")) or ("municípios" if singular == "município" else singular + "s")
    grupo_singular = _palavra(grupo.get("singular")) or "grupo"
    grupo_plural = _palavra(grupo.get("plural")) or ("grupos" if grupo_singular == "grupo" else grupo_singular + "s")
    return _Rotulos(singular, plural, _feminino(unidade, singular), grupo_singular, grupo_plural,
                    _feminino(grupo, grupo_singular))


def _alternativas(*palavras):
    unicas = {normalize(palavra) for palavra in palavras if palavra}
    return "|".join(re.escape(palavra) for palavra in sorted(unicas, key=len, reverse=True))


def _nivel(palavras, todos):
    """Pedido só de nível ("volte aos estados", "mostre os municípios"), para conferir o pedido inteiro."""
    return re.compile(r"(?:(?:agora|entao|ok|certo|pode|por\s+favor)\s+)?(?:(?:quero|queria|gostaria\s+de|vamos|pode|"
                      r"podemos)\s+)?(?:volte|voltar|volta|retorne|retornar|retorna|mostre|mostrar|mostra|exiba|exibir|"
                      r"veja|ver|abra|abrir)?\s*(?:a|ao|aos|as|para|pra|pros|pras|para\s+os|para\s+as|os" +
                      (r"|todos\s+os|todas\s+as" if todos else "") + r"|o\s+nivel\s+d[oa]s|ao\s+nivel\s+d[oa]s|"
                      r"nivel\s+d[oa]s)?\s*(?:\d+\s+)?(?:" + palavras + r")(?:\s+(?:de\s+novo|novamente|do\s+brasil|"
                      r"brasileir[oa]s))?(?:\s+por\s+favor)?")


class _Conversa:
    """Pedido, contexto do gráfico, catálogo, competências e vocabulário de uma requisição."""

    def __init__(self, mensagem, frame, fields, settings, ctx, brasil, opcoes, grupo_coluna):
        self.pedido = _Pedido(mensagem)
        self.ctx = ctx if isinstance(ctx, dict) else contexto({"painel_familia": None})
        self.fields = fields if isinstance(fields, dict) else {}
        self.opcoes = opcoes if isinstance(opcoes, dict) else {}
        self.erro = ""
        self.cat = None
        if frame is not None and self.fields.get("territory"):
            try:
                itens = territory_catalog(frame, self.fields, settings)
            except ValueError as exc:
                self.erro = str(exc)
            else:
                brasil = brasil and any(item.get("state_code") for item in itens)
                grupos = _grupos_planilha(frame, self.fields, grupo_coluna) if grupo_coluna and not brasil else None
                self.cat = _Catalogo(itens, brasil, grupos)
        self.brasil = bool(brasil)
        self.rot = rot = _rotulos(self.ctx, self.brasil)
        self.periodos = _periodos(frame, self.fields)
        unidade = _alternativas("municipio", "cidade", rot.singular)
        unidades = _alternativas("municipios", "cidades", rot.plural)
        grupo = _alternativas(*(("estado", "uf") if self.brasil else ()), rot.grupo_singular)
        grupos = _alternativas(*(("estados", "ufs") if self.brasil else ()), rot.grupo_plural)
        preposicao = r"\s+(?:de|do|da|dos|das|no|na|nos|nas|em)\s+"
        self.grupo_antes = re.compile(r"(?:\b(?:" + grupo + r"|" + grupos + r")\s+(?:(?:de|do|da|dos|das)\s+)?|\b(?:" +
                                      unidades + r")" + preposicao + r"(?:(?:" + grupo + r")\s+(?:de|do|da)\s+)?)$")
        self.unidade_antes = re.compile(r"\b(?:" + unidade + r")\s+(?:(?:de|do|da)\s+)?$")
        self.sabor_municipios = re.compile(r"\b(?:" + unidades + r")" + preposicao + r"(?:(?:" + grupo +
                                           r")\s+(?:de|do|da)\s+)?$")
        self.todos = re.compile(r"\btod[oa]s\s+(?:[oa]s\s+)?(?:" + unidades + r")\b(?:\s+d[oa]\s+brasil\b)?|\b(?:" +
                                unidades + r")\s+do\s+brasil\b")
        self.voltar_estados = _nivel(_alternativas("estados", "ufs", *(() if self.brasil else (rot.grupo_plural,))), True)
        self.voltar_unidades = _nivel(unidades, False)
        self.neutras = NEUTRAS | {palavra for rotulo in (rot.singular, rot.plural, rot.grupo_singular, rot.grupo_plural)
                                  for palavra in re.findall(r"[a-z0-9]+", normalize(rotulo))}

    def base_atual(self):
        if self.ctx["municipios"] is not None:
            return self.ctx["municipios"]
        if self.ctx["ids"]:
            return {"todos": False, "estados": [], "ids": list(self.ctx["ids"])}
        return None

    def membros_do_grupo(self, chave):
        return list(self.cat.grupos[chave]["membros"]) if self.cat is not None and chave in self.cat.grupos else []

    def rotulo_do_estado(self, chave):
        return STATES[chave][1] + " (" + STATES[chave][0] + ")" if chave in STATES else chave


# --------------------------------------------------------------------------------------------- nomes do pedido
def _sufixo(conv, fim, ids):
    """Unidade homônima escolhida pela sigla do estado ("PARANA (TO)") ou pelo código ("Central [123]")."""
    encontrado = SUFIXO.match(conv.pedido.resto, fim)
    if encontrado is None or not ids:
        return ids, fim
    sigla, codigo = encontrado[1] or encontrado[2], encontrado[3]
    if sigla:
        filtrados = [i for i in ids if str(conv.cat.itens[i].get("state") or "").lower() == sigla]
    else:
        filtrados = [i for i in ids if str(conv.cat.itens[i].get("code") or "").lower() == codigo.lower()]
    return (filtrados, encontrado.end()) if filtrados else (ids, fim)


def _preposicao(pedido, inicio):
    encontrada = re.search(r"\b(de|do|da|em|no|na|o|a)\s+$", pedido.resto[:inicio])
    return (encontrada.start(), encontrada[1]) if encontrada else (inicio, None)


def _artigo(preposicao, feminino):
    if preposicao in ("de", "do", "da"):
        return "da " if feminino else "do "
    if preposicao in ("em", "no", "na"):
        return "na " if feminino else "no "
    return "a " if feminino else "o "


def _ambiguidade(conv, inicio, fim, grupo, ids):
    """O nome é de um grupo (estado, província) e também de unidade: pergunta, sem escolher em silêncio."""
    pedido, rot, cat = conv.pedido, conv.rot, conv.cat
    nome = pedido.trecho(inicio, fim)
    antes, preposicao = _preposicao(pedido, inicio)
    if conv.brasil:
        from territorial_levels import group_label  # importação tardia: o módulo de níveis é mais pesado
        do_estado = group_label(grupo)[len("Municípios "):]
        escolhas = [_escolha("Estado " + do_estado, pedido.reescreve(antes, fim, _artigo(preposicao, False) + "estado " +
                                                                    do_estado.split(" ", 1)[0] + " " + nome))]
    else:
        escolhas = [_escolha(_maiuscula(rot.grupo_singular) + " " + nome,
                             pedido.reescreve(antes, fim, _artigo(preposicao, rot.grupo_feminino) + rot.grupo_singular +
                                              " " + nome))]
    for identificador in sorted(ids, key=cat.rotulo):
        rotulo = cat.rotulo(identificador)
        if len(ids) > 1 or conv.brasil:  # a sigla do estado ou o código separa a unidade do grupo
            escolhas.append(_escolha(rotulo, pedido.reescreve(inicio, fim, rotulo)))
        else:
            escolhas.append(_escolha(_maiuscula(rot.singular) + " " + rotulo, pedido.reescreve(
                antes, fim, _artigo(preposicao, rot.feminino) + rot.singular + " " + nome)))
    um_grupo = ("uma " if rot.grupo_feminino else "um ") + rot.grupo_singular
    texto = ("“" + nome + "” identifica " + um_grupo + " e também " + (rot.um() if len(ids) == 1 else rot.plural) +
             ". Qual você quer?" + NADA_MUDOU)
    return _pergunta(texto, escolhas, "AMBIGUIDADE_MATERIAL")


def _homonimos(conv, inicio, fim, ids):
    nome = conv.pedido.trecho(inicio, fim)
    escolhas = [_escolha(conv.cat.rotulo(i), conv.pedido.reescreve(inicio, fim, conv.cat.rotulo(i)))
                for i in sorted(ids, key=conv.cat.rotulo)]
    texto = ("Há " + str(len(ids)) + " " + conv.rot.plural + " com o nome “" + nome + "”. Qual " +
             ("delas" if conv.rot.feminino else "deles") + "?" + NADA_MUDOU)
    return _pergunta(texto, escolhas, "AMBIGUIDADE_MATERIAL")


def _escolhe(conv, achado, inicio, fim, expressao):
    """Uma ocorrência de nome da base no pedido: unidade, grupo ou pergunta (None quando nada foi reconhecido)."""
    pedido, cat = conv.pedido, conv.cat
    antes = pedido.resto[:inicio]
    grupo = cat.por_grupo.get(expressao)
    ids = list(cat.nomes.get(expressao, []))
    if len(expressao) <= 2:  # nome curto só vale escrito como na base ("A" não é o artigo)
        bruto = pedido.trecho(inicio, fim)
        ids = [i for i in ids if str(cat.itens[i]["name"]).strip() == bruto]
        if grupo is not None and str(cat.grupos[grupo]["nome"]).strip() != bruto:
            grupo = None
    if grupo is not None and cat.brasil and expressao in WORDS and not (
            any(ord(c) > 127 for c in pedido.trecho(inicio, fim)) or re.search(r"\b(?:o|do|no|ao|pelo)\s+$", antes)):
        grupo = None  # "para" sem acento é a preposição; o estado é "Pará"
    if expressao in COMUNS and ids and not (conv.unidade_antes.search(antes) or SUFIXO.match(pedido.resto, fim)):
        ids = []
    if grupo is None and not ids:
        return None
    escolhidos, fim_sufixo = _sufixo(conv, fim, ids)
    if grupo is not None and ids:
        if conv.grupo_antes.search(antes):
            ids = []
        elif conv.unidade_antes.search(antes) or fim_sufixo > fim:
            grupo = None
        else:
            return _ambiguidade(conv, inicio, fim, grupo, ids)
    if grupo is not None:
        achado["grupos"].append((inicio, grupo, "municipios" if conv.sabor_municipios.search(antes) else "objeto"))
        pedido.consome(inicio, fim)
        return None
    if len(ids) > 1:
        if fim_sufixo > fim and len(escolhidos) == 1:
            ids = escolhidos
        else:
            # Homônimos: vale o único que já está no gráfico (a resposta diz qual, com a sigla); senão, a pergunta.
            atual = conv.base_atual()
            presentes = cat.membros(atual) if atual is not None else set()
            no_grafico = [i for i in ids if i in presentes]
            if len(no_grafico) != 1:
                return _homonimos(conv, inicio, fim, ids)
            ids = no_grafico
    achado["ids"].append((inicio, ids[0]))
    pedido.consome(inicio, fim_sufixo)
    return None


def _resolve(conv, inicio=0, fim=None):
    """Unidades e grupos citados em [inicio, fim) do pedido (consumidos): {"ids", "grupos", "todos"} ou {"pergunta"}.
    Maior expressão primeiro: o município Rio Grande não é achado dentro do estado do Rio Grande do Sul."""
    pedido, cat = conv.pedido, conv.cat
    fim = len(pedido.texto) if fim is None else fim
    achado = {"ids": [], "grupos": [], "todos": False}
    for encontrado in list(conv.todos.finditer(pedido.resto, inicio, fim)):
        achado["todos"] = True
        pedido.consome(*encontrado.span())
    if cat is None:
        return achado
    for expressao in cat.expressoes:
        if expressao not in pedido.resto[inicio:fim]:
            continue  # condição necessária, sem compilar uma expressão por nome da base
        padrao = re.compile(r"(?<!\w)" + re.escape(expressao) + r"(?!\w)")
        for encontrado in list(padrao.finditer(pedido.resto, inicio, fim)):
            if pedido.resto[encontrado.start():encontrado.end()] != expressao:
                continue
            problema = _escolhe(conv, achado, encontrado.start(), encontrado.end(), expressao)
            if problema is not None:
                return {"pergunta": problema}
    if cat.brasil:  # depois dos nomes: "Rio Grande do Norte" é estado, não a região Norte
        for encontrado in list(REGIAO.finditer(pedido.resto, inicio, fim)):
            alvo = re.sub(r"[\s-]+", " ", encontrado["regiao"])
            digito = next(chave for chave, nome in REGIONS.items() if normalize(nome).replace("-", " ") == alvo)
            estados = sorted(chave for chave in cat.grupos if chave.startswith(digito))
            if not estados:
                return {"pergunta": _pergunta("Nenhum estado da Região " + REGIONS[digito] + " nesta base." + NADA_MUDOU)}
            sabor = "municipios" if encontrado["unidades"] else "objeto"
            achado["grupos"] += [(encontrado.start(), chave, sabor) for chave in estados]
            pedido.consome(*encontrado.span())
    # Na ordem do pedido (na comparação, a ordem dá o A e o B), sem repetir.
    achado["ids"] = list(dict.fromkeys(identificador for _, identificador in sorted(achado["ids"])))
    achado["grupos"] = list(dict.fromkeys((chave, sabor) for _, chave, sabor in sorted(achado["grupos"])))
    return achado


def _membros(conv, achado):
    """Municípios citados, com os dos grupos: (ids, há estado como objeto na base do Brasil)."""
    ids = list(achado["ids"])
    objeto = False
    for chave, sabor in achado["grupos"]:
        if conv.brasil and sabor == "objeto":
            objeto = True
        else:
            ids += conv.membros_do_grupo(chave)
    return list(dict.fromkeys(ids)), objeto


def _desconhecidas(conv):
    """Palavras que nada reconheceu: (com inicial maiúscula fora do começo, provável nome; as demais)."""
    nomes, outras = [], []
    primeira = re.search(r"[a-z0-9]+", conv.pedido.texto)
    for palavra in re.finditer(r"[a-z0-9]+", conv.pedido.resto):
        if palavra[0] in conv.neutras:
            continue
        escrita = conv.pedido.trecho(palavra.start(), palavra.end())
        if primeira is not None and palavra.start() != primeira.start() and escrita[:1].isupper():
            nomes.append(escrita)
        else:
            outras.append(palavra[0])
    return nomes, outras


def _nao_encontrado(conv, nomes):
    rot = conv.rot
    if conv.erro:
        return _pergunta("Não consegui identificar os nomes do pedido: " + conv.erro + NADA_MUDOU)
    return _pergunta("Não encontrei “" + _e(nomes) + "” entre " + rot.os() + (" e os estados" if conv.brasil else "") +
                     " da base. Confira o nome ou use a busca de " + rot.plural + "." + NADA_MUDOU)


def _dos_grupos(conv, grupos):
    """“do Pará e do Amazonas”, “da província Nampula”."""
    if conv.brasil:
        from territorial_levels import group_label  # importação tardia: o módulo de níveis é mais pesado
        return _e(group_label(chave)[len("Municípios "):] if chave in STATES else chave for chave in grupos)
    rot = conv.rot
    nomes = [str(conv.cat.grupos.get(chave, {}).get("nome", chave)) for chave in grupos]
    if len(nomes) == 1:
        return ("da " if rot.grupo_feminino else "do ") + rot.grupo_singular + " " + nomes[0]
    return ("das " if rot.grupo_feminino else "dos ") + rot.grupo_plural + " " + _e(nomes)


def _frase_da_base(conv, base):
    """“nos 144 municípios do Pará”, “em 2 municípios: A e B”, “em todos os 5.570 municípios”."""
    rot, cat = conv.rot, conv.cat
    quantidade = len(cat.membros(base))
    if base["todos"]:
        return ("em todas as " if rot.feminino else "em todos os ") + rot.unidades(quantidade)
    if not base["ids"]:
        return rot.nas(quantidade) + " " + _dos_grupos(conv, base["estados"])
    rotulos = _listed([cat.rotulo(i) for i in base["ids"]])
    if not base["estados"]:
        return "em " + rot.unidades(quantidade) + ": " + rotulos
    return "em " + rot.unidades(quantidade) + ": " + ("as " if rot.feminino else "os ") + \
        _dos_grupos(conv, base["estados"]) + " e " + rotulos


def _nova_base(conv, achado, modo):
    """(base, citados, resposta): a nova base do gráfico ou a resposta que a substitui."""
    cat, rot = conv.cat, conv.rot
    grupos = list(dict.fromkeys(chave for chave, _ in achado["grupos"]))
    ids = achado["ids"]
    citados = [cat.rotulo(i) for i in ids] + [rot.os() + " " + _dos_grupos(conv, [chave]) for chave in grupos]
    todos = {"todos": True, "estados": [], "ids": []}
    if achado["todos"]:
        citados = [("todas as " if rot.feminino else "todos os ") + rot.plural]
    atual = conv.base_atual()
    if modo == "trocar" or (modo == "acrescentar" and atual is None):
        return (todos if achado["todos"] else {"todos": False, "estados": sorted(grupos), "ids": ids}), citados, None
    if modo == "acrescentar":
        if atual["todos"]:
            return None, citados, _so_texto(_maiuscula(("todas as " if rot.feminino else "todos os ") + rot.plural) +
                                            " já estão no gráfico.")
        if achado["todos"]:
            return todos, citados, None
        return {"todos": False, "estados": sorted(set(atual["estados"]) | set(grupos)),
                "ids": sorted(set(atual["ids"]) | set(ids))}, citados, None
    if atual is None:
        return None, citados, _pergunta("Não sei quais " + rot.plural + " estão no gráfico agora. Diga quais mostrar, por "
                                        "exemplo, “mostre o Pará”." + NADA_MUDOU)
    if achado["todos"]:
        return None, citados, _pergunta("O gráfico precisa de pelo menos " + rot.um() + "." + NADA_MUDOU)
    tirar = set(ids) | {membro for chave in grupos for membro in conv.membros_do_grupo(chave)}
    if atual["todos"]:
        estados = list(cat.grupos)
        soltos = set(cat.itens) - {membro for grupo in cat.grupos.values() for membro in grupo["membros"]}
    else:
        estados, soltos = list(atual["estados"]), set(atual["ids"])
    manter = [chave for chave in estados if chave in cat.grupos and chave not in grupos and
              not set(cat.grupos[chave]["membros"]) & tirar]
    parciais = [chave for chave in estados if chave in cat.grupos and chave not in grupos and chave not in manter]
    restantes = (soltos | {membro for chave in parciais for membro in cat.grupos[chave]["membros"]}) - tirar
    base = {"todos": False, "estados": sorted(manter), "ids": sorted(restantes)}
    if not cat.membros(base):
        return None, citados, _pergunta("Sem " + _e(citados) + ", o gráfico ficaria vazio." + NADA_MUDOU)
    return base, citados, None


# --------------------------------------------------------------------------------------------- competências
def _anos(conv, anos, varias, trecho, nota=None):
    """Competências da base nos anos citados: a competência, a janela ou a pergunta (uma análise de uma competência,
    com várias no ano, não escolhe em silêncio)."""
    periodos = conv.periodos
    lista = [periodo for periodo in periodos if re.fullmatch(r"\d{6}|\d{4}", periodo) and
             anos[0] <= int(periodo[:4]) <= anos[1]]
    if not lista:
        quando = "em " + str(anos[0]) if anos[0] == anos[1] else "entre " + str(anos[0]) + " e " + str(anos[1])
        return None, _pergunta("A base não tem competências " + quando + "." + _exemplo(periodos) + NADA_MUDOU)
    if len(lista) == 1:
        return {"competencia": lista[0], "nota": nota}, None
    if varias or anos[0] != anos[1]:
        return {"janela": lista, "nota": nota}, None
    escolhas = [_escolha(_maiuscula(_human(periodo)), conv.pedido.reescreve(trecho[0], trecho[1], "em " + _human(periodo)))
                for periodo in reversed(lista)]
    citadas = " e ".join(_human(p) for p in lista) if len(lista) <= 3 else \
        "de " + _human(lista[0]) + " a " + _human(lista[-1])
    return None, _pergunta("Em " + str(anos[0]) + ", a base tem " + str(len(lista)) + " competências (" + citadas +
                           "). O gráfico mostra uma competência por vez: qual delas?" + NADA_MUDOU, escolhas)


def _exemplo(periodos):
    return " Escolha uma das competências da base, por exemplo, “" + _human(periodos[-1]) + "”." if periodos else ""


def _pergunta_relativa(conv, inicio, fim, achado):
    """As leituras de "últimos N anos" (AT-34) em botões: o pedido original, com os anos explícitos."""
    escolhas = []
    for alternativa in achado.get("choices") or []:
        anos = re.search(r"(?:de (\d{4}) a (\d{4})|(\d{4}))$", alternativa["draft"])
        if anos:
            novo = "de " + anos[1] + " a " + anos[2] if anos[1] else "em " + anos[3]
            escolhas.append(_escolha(alternativa["label"], conv.pedido.reescreve(inicio, fim, novo)))
    return _pergunta(achado["clarification"] + ("" if "Nada foi calculado" in achado["clarification"] else NADA_MUDOU),
                     escolhas, achado.get("ambiguity"))


def _periodo(conv, varias):
    """Competência ou janela citada no pedido (o trecho é consumido): (resultado, None), (None, pergunta) ou
    (None, None). varias: a análise do gráfico aceita uma janela (tendência, rotatividade)."""
    pedido, periodos = conv.pedido, conv.periodos
    junhos = [periodo for periodo in periodos if re.fullmatch(r"\d{4}06", periodo)]
    for padrao, janela in ((SERIE_ANUAL, lambda m: junhos), (JUNHOS, lambda m: junhos[-max(_quantos(m[1]), 1):]),
                           (TODAS, lambda m: list(periodos))):
        encontrado = padrao.search(pedido.resto)
        if encontrado:
            escolhidas = janela(encontrado)
            if len(escolhidas) < 2:
                return None, _pergunta("A base não tem competências suficientes para essa janela." + _exemplo(periodos) +
                                       NADA_MUDOU)
            pedido.consome(*encontrado.span())
            return {"janela": escolhidas}, None
    datas = []
    for encontrado in MES.finditer(pedido.resto):
        mes = encontrado[1]
        indice = MONTHS.index(mes) if mes in MONTHS else [nome[:3] for nome in MONTHS].index(mes)
        datas.append((encontrado.start(), encontrado.end(), encontrado[2] + str(indice + 1).zfill(2)))
    for encontrado in AAAAMM.finditer(pedido.resto):
        datas.append((encontrado.start(), encontrado.end(), encontrado[1] + encontrado[2]))
    if datas:
        fora = [data for data in sorted(datas) if data[2] not in periodos]
        if fora:
            return None, _pergunta("A competência " + _human(fora[0][2]) + " não está nesta base." + _exemplo(periodos) +
                                   NADA_MUDOU)
        for inicio, fim, _ in datas:
            pedido.consome(inicio, fim)
        escolhidas = sorted({data[2] for data in datas})
        if len(escolhidas) == 1:
            return {"competencia": escolhidas[0]}, None
        return {"janela": [p for p in periodos if escolhidas[0] <= p <= escolhidas[-1]], "pontas": escolhidas}, None
    encontrado = RELATIVE_YEARS.search(pedido.resto)
    if encontrado:
        inicio = encontrado.start()
        prefixo = PREFIXO_RELATIVO.search(pedido.resto[:inicio])
        if prefixo:
            inicio = prefixo.start()
        anos, achado = relative_years(encontrado, periodos, conv.opcoes, "temporal")
        if anos is None:
            return None, _pergunta_relativa(conv, inicio, encontrado.end(), achado)
        pedido.consome(inicio, encontrado.end())
        return _anos(conv, anos, varias, (inicio, encontrado.end()), nota=achado)
    for padrao in (FAIXA, DESDE, ATE, ANO):
        encontrado = padrao.search(pedido.resto)
        if encontrado:
            ano = int(encontrado[1])
            primeiro = int(periodos[0][:4]) if periodos and periodos[0][:4].isdigit() else ano
            ultimo = int(periodos[-1][:4]) if periodos and periodos[-1][:4].isdigit() else ano
            anos = {FAIXA: lambda: sorted((ano, int(encontrado[2]))), DESDE: lambda: [ano, max(ano, ultimo)],
                    ATE: lambda: [min(ano, primeiro), ano], ANO: lambda: [ano, ano]}[padrao]()
            pedido.consome(*encontrado.span())
            return _anos(conv, anos, varias, encontrado.span())
    return None, None


def _quando(painel):
    if painel.get("competencia"):
        return ", em " + _human(painel["competencia"])
    janela = painel.get("janela") or []
    if len(janela) == 2:
        return ", entre " + _human(janela[0]) + " e " + _human(janela[1])
    if len(janela) > 2:
        return ", de " + _human(janela[0]) + " a " + _human(janela[-1]) + " (" + str(len(janela)) + " competências)"
    return ""


def _aplica_periodo(painel, periodo):
    if periodo and periodo.get("competencia"):
        painel["competencia"] = periodo["competencia"]
    elif periodo and periodo.get("janela"):
        painel["janela"] = periodo["janela"]


def _o_que(familia, indicador):
    valor = {"densidade": "a densidade", "quantidade": "a quantidade"}.get(indicador)
    if familia == "tendencia":
        return "a tendência" + (" da " + indicador if indicador else "")
    if familia == "espacial":
        return (valor or "os valores") + " e a distância até a referência"
    if familia == "rotatividade":
        return "a rotatividade"
    return valor or "os valores"


def _frase_de_base(conv, painel, base, quando=""):
    familia = painel["familia"] or conv.ctx["familia"]
    indicador = painel["indicador"] or conv.ctx["indicador"]
    return "Mostrei " + _o_que(familia, indicador) + " " + _frase_da_base(conv, base) + quando + "."


# --------------------------------------------------------------------------------------------- comandos
def _voltar(conv, dica, dica_indicador):
    """"Volte aos estados" e "volte aos municípios": só o nível muda."""
    texto = " ".join(re.findall(r"[a-z0-9]+", conv.pedido.texto))
    rot = conv.rot
    if conv.voltar_estados.fullmatch(texto):
        if not conv.brasil:
            return _pergunta("Esta base não tem um nível acima " + ("das " if rot.feminino else "dos ") + rot.plural +
                             " no gráfico: cada bolha é " + rot.um() + ". Para ver " + rot.os() + " de " +
                             ("uma " if rot.grupo_feminino else "um ") + rot.grupo_singular + ", diga, por exemplo, “mostre " +
                             ("a " if rot.grupo_feminino else "o ") + rot.grupo_singular + " …”." + NADA_MUDOU)
        texto_estados = "Voltei aos estados: cada bolha é um estado"
        if conv.ctx["familia"] == "espacial":
            texto_estados += "; nos estados não há distância, porque estados não têm um ponto único"
        elif conv.ctx["indicador"]:
            texto_estados += ", com " + _o_que(None, conv.ctx["indicador"])
        return _resposta(_painel(nivel="estados"), texto_estados + ".")
    if conv.voltar_unidades.fullmatch(texto) and conv.cat is not None:
        atual = conv.base_atual()
        if atual is not None and conv.cat.membros(atual):
            painel = _painel(nivel="municipios", municipios=atual)
            return _resposta(painel, _frase_de_base(conv, painel, atual))
        if not conv.brasil:
            base = {"todos": True, "estados": [], "ids": []}
            painel = _painel(nivel="municipios", municipios=base)
            return _resposta(painel, _frase_de_base(conv, painel, base))
        return _pergunta("De qual estado? Diga, por exemplo, “mostre o Pará”, ou peça “todos os municípios”." + NADA_MUDOU)
    return None


def _clausula(conv, encontrado, inicio_local):
    """Uma condição do pedido: {"item", "texto", "fim", "alvo"}, {"pergunta"} ou None (sem indicador: pode ser período,
    como em "de 2014 até 2024")."""
    pedido = conv.pedido
    resto = pedido.resto
    palavras, bruto = encontrado[1], encontrado[2]
    operador = dict(OPERATORS)[palavras]
    simbolo = SYMBOL[operador]
    depois = encontrado.end()
    antes = resto[inicio_local:encontrado.start()]
    escrito = pedido.trecho(encontrado.start(), encontrado.end())
    valor = _value(bruto)
    if valor is None:
        return {"pergunta": _pergunta("Não identifiquei o valor de “" + bruto + "” com segurança: use vírgula para "
                                      "decimais e escreva o número sem separador de milhar." + NADA_MUDOU)}
    numero = bruto.replace(".", ",")
    if UNIDADE_OUTRA_ESCALA.match(resto, depois):
        return {"pergunta": _pergunta("No gráfico, a densidade é por 1.000 habitantes. Diga o valor por mil habitantes, "
                                      "por exemplo, “menos de 1 médico por mil habitantes”." + NADA_MUDOU)}
    unidade = UNIDADE_POR_MIL.match(resto, depois)
    if unidade:
        return {"item": {"atributo": "densidade", "operador": operador, "valor": _numero(valor)},
                "texto": "densidade " + simbolo + " " + numero + " por mil habitantes", "fim": unidade.end(), "alvo": None}
    unidade = UNIDADE_KM.match(resto, depois)
    if unidade:
        alvo = ALVO_DISTANCIA.match(resto, unidade.end())
        return {"item": {"atributo": "distancia_km", "operador": operador, "valor": _numero(valor)},
                "texto": "distância " + simbolo + " " + numero + " km", "fim": alvo.end() if alvo else unidade.end(),
                "alvo": alvo.end() if alvo else None}
    if UNIDADE_METROS.match(resto, depois):
        return {"pergunta": _pergunta("No gráfico, a distância é em km. Diga o valor em quilômetros, por exemplo, “a mais "
                                      "de 150 km de Manaus”." + NADA_MUDOU)}
    unidade = UNIDADE_MIL_HABITANTES.match(resto, depois)
    if unidade or (re.search(r"\bpopulacao\b", antes) and re.match(r"\s*mil\b", resto[depois:])):
        if "." in valor:
            return {"pergunta": _pergunta("Escreva a população em habitantes, sem decimais em milhares (por exemplo, "
                                          "20000)." + NADA_MUDOU)}
        fim = unidade.end() if unidade else depois + re.match(r"\s*mil\b", resto[depois:]).end()
        return {"item": {"atributo": "populacao", "operador": operador, "valor": int(valor) * 1000},
                "texto": "população " + simbolo + " " + _milhar(int(valor) * 1000) + " habitantes", "fim": fim,
                "alvo": None}
    unidade = UNIDADE_HABITANTES.match(resto, depois)
    if unidade:
        return {"item": {"atributo": "populacao", "operador": operador, "valor": _numero(valor)},
                "texto": "população " + simbolo + " " + numero + " habitantes", "fim": unidade.end(), "alvo": None}
    citado = ATRIBUTO_ANTES.findall(antes)
    unidade = UNIDADE_PROFISSIONAIS.match(resto, depois)
    if unidade and not citado:
        profissionais = pedido.trecho(depois, unidade.end()).strip()
        escolhas = [_escolha("Densidade " + simbolo + " " + numero + " por mil habitantes",
                             pedido.reescreve(encontrado.start(), unidade.end(), escrito + " " + profissionais +
                                              " por mil habitantes")),
                    _escolha("Quantidade " + simbolo + " " + numero,
                             pedido.reescreve(encontrado.start(), unidade.end(), "quantidade de " + profissionais + " " +
                                              OPERADOR_TEXTO[operador] + " " + bruto))]
        return {"pergunta": _pergunta("“" + escrito + " " + profissionais + "” pode ser a quantidade de profissionais ou a "
                                      "densidade por mil habitantes. Qual você quer?" + NADA_MUDOU, escolhas,
                                      "AMBIGUIDADE_MATERIAL")}
    if not citado or (re.fullmatch(r"(?:19|20)\d{2}", bruto) and palavras in ("a partir de", "ate")):
        return None
    atributo = {"distancia": "distancia_km", "quantitativo": "quantidade"}.get(citado[-1], citado[-1])
    texto = {"densidade": "densidade " + simbolo + " " + numero + " por mil habitantes",
             "distancia_km": "distância " + simbolo + " " + numero + " km",
             "populacao": "população " + simbolo + " " + numero + " habitantes",
             "quantidade": "quantidade " + simbolo + " " + numero}[atributo]
    fim = unidade.end() if unidade else depois
    alvo = ALVO_DISTANCIA.match(resto, fim) if atributo == "distancia_km" else None
    return {"item": {"atributo": atributo, "operador": operador, "valor": _numero(valor)}, "texto": texto,
            "fim": alvo.end() if alvo else fim, "alvo": alvo.end() if alvo else None}


def _condicoes(conv, dica, dica_indicador):
    """Condições (CAP-SUB-01), combinadas com "e": quem atende a todas, quem não atende e quem não tem dado."""
    pedido = conv.pedido
    achadas, inicio_local = [], 0
    for encontrado in list(CLAUSE.finditer(pedido.resto)):
        clausula = _clausula(conv, encontrado, inicio_local)
        if clausula is None:
            continue
        if "pergunta" in clausula:
            return clausula["pergunta"]
        achadas.append((encontrado, clausula))
        inicio_local = clausula["fim"]
    if not achadas:
        if dica == "criteria":
            return _resposta(_painel(funcao="condicoes"), "Abri Condições: diga a condição, por exemplo, “municípios com "
                                                          "menos de 1 médico por mil habitantes”.")
        return None
    if re.search(r"\bou\b", pedido.resto[achadas[0][0].start():achadas[-1][1]["fim"]]):
        return _pergunta("No gráfico, as condições se combinam com “e”: cada município precisa atender a todas. Peça só com "
                         "“e” ou uma condição de cada vez." + NADA_MUDOU)
    for encontrado, clausula in achadas:
        pedido.consome(encontrado.start(), clausula["fim"])
    alvos = [(indice, clausula["alvo"], achadas[indice + 1][0].start() if indice + 1 < len(achadas) else len(pedido.texto))
             for indice, (_, clausula) in enumerate(achadas) if clausula["alvo"] is not None]
    periodo, pergunta = _periodo(conv, False)
    if pergunta:
        return pergunta
    membros = []
    for indice, inicio, fim in alvos:
        achado = _resolve(conv, inicio, fim)
        if "pergunta" in achado:
            return achado["pergunta"]
        ids, objeto = _membros(conv, achado)
        if objeto:
            return _pergunta(SEM_PONTO_UNICO)
        if ids:
            achadas[indice][1]["texto"] += " até " + _listed([conv.cat.rotulo(i) for i in ids])
        membros += ids
    membros = list(dict.fromkeys(membros))
    distancia = any(clausula["item"]["atributo"] == "distancia_km" for _, clausula in achadas)
    if distancia and not membros and conv.ctx["familia"] != "espacial" and not conv.ctx["referencia"]:
        return _pergunta("A distância é medida até a referência. Diga até onde, por exemplo, “a mais de 150 km de Manaus”, "
                         "ou escolha a referência antes (por exemplo, “use Manaus como referência”)." + NADA_MUDOU)
    achado = _resolve(conv)
    if "pergunta" in achado:
        return achado["pergunta"]
    nomes, _ = _desconhecidas(conv)
    if nomes and dica is None:
        return _nao_encontrado(conv, nomes)
    itens = [clausula["item"] for _, clausula in achadas]
    if TAMBEM.search(pedido.texto) and conv.ctx["condicoes"]:
        itens = [*conv.ctx["condicoes"], *itens]
    painel = _painel(funcao="condicoes", condicoes=itens)
    _aplica_periodo(painel, periodo)
    frases = []
    if conv.cat is not None and (achado["ids"] or achado["grupos"] or achado["todos"]):
        base, _, _ = _nova_base(conv, achado, "trocar")
        painel.update(nivel="municipios", municipios=base)
        frases.append(_frase_de_base(conv, painel, base))
    if membros:
        painel.update(familia="espacial", referencia={"membros": membros})
    if distancia and conv.ctx["nivel"] == "estados":
        painel["nivel"] = "municipios"
    textos = [clausula["texto"] for _, clausula in achadas]
    frases.append("Apliquei " + ("a condição " if len(textos) == 1 else "as condições ") + _e(textos) + _quando(painel) +
                  ": o gráfico separa quem atende a " + ("ela" if len(textos) == 1 else "todas") +
                  ", quem não atende e quem não tem dado.")
    if len(itens) > len(textos):
        frases.append("As condições anteriores continuam.")
    return _resposta(painel, " ".join(frases))


def _atributo_e_ordem(palavra, direcao):
    mais = direcao.startswith(("maior", "mais"))
    if palavra.startswith("populos"):
        return "populacao", "desc" if mais else "asc"
    if palavra.startswith("distante"):
        return "distancia_km", "desc" if mais else "asc"
    if palavra.startswith("proxim"):
        return "distancia_km", "asc" if mais else "desc"
    if palavra in ("medicos", "medicas", "profissionais"):
        return "quantidade", "desc" if mais else "asc"
    if palavra == "aumento":
        return "variacao", "desc" if mais else "asc"
    if palavra in ("reducao", "queda"):
        return "variacao", "asc" if mais else "desc"
    return {"distancia": "distancia_km"}.get(palavra, palavra), "desc" if mais else "asc"


def _ordenar(conv, dica, dica_indicador):
    """Ordenar (CAP-SUB-02 e CAP-SUB-03): empates na mesma posição e os N primeiros."""
    pedido = conv.pedido
    posicao = TOPO.search(pedido.resto) or QUAL.search(pedido.resto) or PRIMEIROS.search(pedido.resto) or \
        TOP.search(pedido.resto)
    sentido = (DECRESCENTE.search(pedido.resto) or CRESCENTE.search(pedido.resto)) and ATRIBUTO_SIMPLES.search(pedido.resto)
    if not (posicao or sentido or ORDENAR.search(pedido.resto) or dica == "ranking"):
        return None
    if not posicao and GRUPOS_VISTA.search(pedido.resto):
        return None  # "classifique em quintis": grupos por posição da distribuição
    periodo, pergunta = _periodo(conv, False)
    if pergunta:
        return pergunta
    quantos = atributo = ordem = alvo = None
    topo = TOPO.search(pedido.resto)
    achado = topo or QUAL.search(pedido.resto)
    if achado:
        atributo, ordem = _atributo_e_ordem(achado["attr"], achado["dir"])
        if topo:
            quantos = _quantos(topo["n"])
            pedido.consome(topo.start(), topo.end("n"))
        else:
            quantos = 1 if achado["qual"] == "qual" else None
            pedido.consome(*achado.span("qual"))
        pedido.consome(achado.start("dir"), achado.end("attr"))
        if atributo == "distancia_km":
            alvo = ALVO_ORDEM.match(pedido.resto, achado.end("attr"))
    for encontrado in list(ORDENAR.finditer(pedido.resto)):
        pedido.consome(*encontrado.span())
    for padrao in (PRIMEIROS, TOP):
        encontrado = padrao.search(pedido.resto)
        if encontrado:
            quantos = _quantos(encontrado["n"]) if quantos is None else quantos
            pedido.consome(*encontrado.span())
            if padrao is TOP and ordem is None:
                ordem = "desc"
    if atributo is None:
        encontrado = ATRIBUTO_SIMPLES.search(pedido.resto)
        if encontrado:
            atributo = {"distancia": "distancia_km"}.get(encontrado[1], encontrado[1])
            pedido.consome(*encontrado.span())
            if atributo == "distancia_km":
                alvo = ALVO_ORDEM.match(pedido.resto, encontrado.end())
    if ordem is None:
        encontrado = DECRESCENTE.search(pedido.resto) or CRESCENTE.search(pedido.resto)
        if encontrado:
            ordem = "desc" if encontrado.re is DECRESCENTE else "asc"
            pedido.consome(*encontrado.span())
        elif atributo:
            encontrado = re.search(r"\b(maior(?:es)?|menor(?:es)?)\b", pedido.resto)
            if encontrado:
                ordem = "desc" if encontrado[1].startswith("maior") else "asc"
                pedido.consome(*encontrado.span())
    if atributo is None and isinstance(dica_indicador, str):
        atributo = INDICADORES.get(dica_indicador)
    pedido_escrito = conv.pedido.original.strip().rstrip(".!?")
    if atributo is None:
        return _pergunta("Ordenar por qual indicador? Escolha abaixo ou diga, por exemplo, “os 5 com menor densidade”." +
                         NADA_MUDOU, [_escolha("Maior " + nome, pedido_escrito + " com maior " + nome)
                                      for nome in ("densidade", "quantidade", "população")])
    if ordem is None:
        return _pergunta("Ordenar " + ATRIBUTO_TEXTO[atributo] + " do maior para o menor ou do menor para o maior? A ordem "
                         "define quem aparece primeiro." + NADA_MUDOU,
                         [_escolha(rotulo, pedido_escrito + ", " + ATRIBUTO_TEXTO[atributo] + " em ordem " + direcao)
                          for rotulo, direcao in (("Do maior para o menor", "decrescente"),
                                                  ("Do menor para o maior", "crescente"))])
    membros = []
    if alvo is not None:
        pedido.consome(*alvo.span())
        achado_alvo = _resolve(conv, alvo.end(), len(pedido.texto))
        if "pergunta" in achado_alvo:
            return achado_alvo["pergunta"]
        membros, objeto = _membros(conv, achado_alvo)
        if objeto:
            return _pergunta(SEM_PONTO_UNICO)
    if atributo == "distancia_km" and not membros and conv.ctx["familia"] != "espacial" and not conv.ctx["referencia"]:
        return _pergunta("Para ordenar pela distância, escolha antes a referência: diga, por exemplo, “use Manaus como "
                         "referência”." + NADA_MUDOU)
    if atributo == "variacao" and conv.ctx["familia"] != "tendencia":
        return _pergunta("A variação aparece na tendência, na visão Mudança. Peça antes, por exemplo, “mostre a mudança "
                         "entre junho de 2023 e junho de 2024”." + NADA_MUDOU)
    if quantos is not None and not 1 <= quantos <= 10000:
        return _pergunta("Escolha quantos destacar, entre 1 e 10.000." + NADA_MUDOU)
    achado = _resolve(conv)
    if "pergunta" in achado:
        return achado["pergunta"]
    nomes, _ = _desconhecidas(conv)
    if nomes and dica is None:
        return _nao_encontrado(conv, nomes)
    painel = _painel(funcao="ordenar", ordenar={"atributo": atributo, "ordem": ordem, "primeiros": quantos})
    _aplica_periodo(painel, periodo)
    frases = []
    base = None
    if conv.cat is not None and (achado["ids"] or achado["grupos"] or achado["todos"]):
        base, _, _ = _nova_base(conv, achado, "trocar")
        painel.update(nivel="municipios", municipios=base)
        frases.append(_frase_de_base(conv, painel, base))
    if membros:
        painel.update(familia="espacial", referencia={"membros": membros})
        frases.append("Usei " + _listed([conv.cat.rotulo(i) for i in membros]) + " como referência da distância.")
    quem = "os estados" if conv.ctx["nivel"] == "estados" and base is None and not membros else conv.rot.os()
    texto = "Ordenei " + quem + " " + ATRIBUTO_TEXTO[atributo] + ", " + ORDEM_TEXTO[ordem]
    if quantos == 1:
        texto += ", e destaquei o primeiro; empates na 1ª posição também entram"
    elif quantos:
        texto += ", e destaquei os " + str(quantos) + " primeiros; empates na posição de corte também entram"
    else:
        texto += "; empates ficam na mesma posição"
    frases.append(texto + _quando(painel) + ".")
    return _resposta(painel, " ".join(frases))


def _referencia(conv, dica, dica_indicador):
    """Referência da análise espacial: por nome, por conjunto (o membro mais próximo) ou por critério."""
    pedido = conv.pedido
    encontrado = COMO_REFERENCIA.search(pedido.resto)
    if encontrado:
        divisores = list(DIVISOR.finditer(pedido.resto, 0, encontrado.start()))
        trecho = (divisores[-1].end() if divisores else 0, encontrado.start())
        if divisores:
            pedido.consome(*divisores[-1].span())
    else:
        encontrado = REFERENCIA_E.search(pedido.resto) or REFERENCIA_EM.search(pedido.resto) or \
            DISTANCIA_ATE.search(pedido.resto)
        if not encontrado:
            return None
        trecho = (encontrado.end(), len(pedido.texto))
    pedido.consome(*encontrado.span())
    periodo, pergunta = _periodo(conv, False)
    if pergunta:
        return pergunta
    achado = _resolve(conv, *trecho)
    if "pergunta" in achado:
        return achado["pergunta"]
    if achado["todos"]:
        return _pergunta(SEM_PONTO_UNICO.replace("estados não têm um ponto único", "a referência não pode ser a base "
                                                 "inteira"))
    membros, objeto = _membros(conv, achado)
    if objeto:
        return _pergunta(SEM_PONTO_UNICO)
    criterio = None
    if not membros:
        encontrado = CRITERIO.search(pedido.resto)
        if encontrado:
            if encontrado[1]:
                criterio = {"atributo": encontrado[2], "ordem": "desc" if encontrado[1] == "maior" else "asc"}
            else:
                criterio = {"atributo": "populacao" if encontrado[4].startswith("populos") else "quantidade",
                            "ordem": "desc" if encontrado[3] == "mais" else "asc"}
            pedido.consome(*encontrado.span())
    if not membros and not criterio and dica is None:
        # O trecho da referência tem palavras que não são nomes da base: provável nome escrito de outro jeito.
        soltas = [pedido.trecho(trecho[0] + palavra.start(), trecho[0] + palavra.end())
                  for palavra in re.finditer(r"[a-z0-9]+", pedido.resto[trecho[0]:trecho[1]])
                  if palavra[0] not in conv.neutras]
        if soltas:
            return _nao_encontrado(conv, soltas)
    base_achada = _resolve(conv)
    if "pergunta" in base_achada:
        return base_achada["pergunta"]
    nomes, _ = _desconhecidas(conv)
    if nomes and dica is None:
        return _nao_encontrado(conv, nomes)
    painel = _painel(familia="espacial")
    _aplica_periodo(painel, periodo)
    frases = []
    if conv.cat is not None and (base_achada["ids"] or base_achada["grupos"] or base_achada["todos"]):
        base, _, _ = _nova_base(conv, base_achada, "trocar")
        painel.update(nivel="municipios", municipios=base)
        frases.append(_frase_de_base(conv, painel, base))
    elif conv.ctx["nivel"] == "estados":
        painel["nivel"] = "municipios"
    quando = _quando(painel)
    rotulos = _listed([conv.cat.rotulo(i) for i in membros]) if membros else ""
    if len(membros) == 1:
        painel["referencia"] = {"membros": membros}
        frases.append("Usei " + rotulos + " como referência" + quando + ": o eixo X passa a mostrar a distância em linha "
                      "reta (km) até ela.")
    elif membros:
        painel["referencia"] = {"membros": membros}
        frases.append("Usei " + rotulos + " como conjunto de referência" + quando + ": o eixo X mostra a distância em "
                      "linha reta (km) até o membro mais próximo.")
    elif criterio:
        painel["referencia"] = {"membros": [], "criterio": criterio}
        frases.append("A referência segue o critério " + {"densidade": "densidade", "quantidade": "quantidade",
                                                          "populacao": "população"}[criterio["atributo"]] + " (" +
                      ("maior para menor" if criterio["ordem"] == "desc" else "menor para maior") + ")" + quando +
                      ": a lista de candidatos abre nessa ordem para você usar o primeiro ou escolher outro; com empate "
                      "na 1ª posição, a escolha é sua.")
    else:
        frases.append("Abri a análise espacial" + quando + ": escolha a referência pelo nome, por um critério ou por um "
                      "conjunto, e o eixo X mostra a distância em linha reta (km) até ela.")
    return _resposta(painel, " ".join(frases))


def _comparar_ou_juntar(conv, dica, dica_indicador):
    """Comparar (CAP-CMP-01, 2 ou 3 itens lado a lado) ou juntar num conjunto (CAP-AGR-01, soma dos componentes)."""
    pedido = conv.pedido
    comparar = COMPARAR.search(pedido.resto)
    juntar = JUNTAR.search(pedido.resto)
    if juntar and not comparar and GRUPOS_VISTA.search(pedido.resto):
        juntar = None  # "agrupe em quintis": grupos por posição da distribuição
    # Comparação pendente ("compare Manaus" → "com qual outro?"): a mensagem seguinte, só com nomes (sem outro comando nem
    # pergunta), completa o pedido com a unidade já identificada, que a tela devolve em conversation_pending_ids.
    pendentes = list(conv.ctx.get("pendentes") or [])
    pendente = bool(pendentes) and conv.opcoes.get("conversation_pending_operation") == "comparisons" and not (
        comparar or juntar or dica or VERBO_VISTA.search(pedido.texto) or PERGUNTA.match(pedido.texto))
    if not (comparar or juntar or dica in ("comparisons", "aggregate") or pendente):
        return None
    if comparar and juntar:
        return _pergunta("Uma função por vez: comparar lado a lado ou juntar num conjunto?" + NADA_MUDOU,
                         [_escolha("Comparar", pedido.reescreve(juntar.start(), juntar.end(), "").strip() or "compare"),
                          _escolha("Juntar", pedido.reescreve(comparar.start(), comparar.end(), "").strip() or "junte")])
    funcao = "comparar" if comparar or pendente or (not juntar and dica == "comparisons") else "juntar"
    for encontrado in list(COMPARAR.finditer(pedido.resto)) + list(JUNTAR.finditer(pedido.resto)):
        pedido.consome(*encontrado.span())
    periodo, pergunta = _periodo(conv, False)
    if pergunta:
        return pergunta
    indicador = "densidade" if DENSIDADE.search(pedido.resto) else "quantidade" if QUANTIDADE.search(pedido.resto) else \
        INDICADORES.get(dica_indicador) if isinstance(dica_indicador, str) else None
    for padrao in (DENSIDADE, QUANTIDADE):
        for encontrado in list(padrao.finditer(pedido.resto)):
            pedido.consome(*encontrado.span())
    deixis = DEIXIS.search(pedido.resto)
    achado = _resolve(conv)
    if "pergunta" in achado:
        return achado["pergunta"]
    nomes, _ = _desconhecidas(conv)
    if nomes and dica is None:
        return _nao_encontrado(conv, nomes)
    rot = conv.rot
    verbo = "comparar" if funcao == "comparar" else "juntar"
    if achado["todos"]:
        return _pergunta("Para " + verbo + ", diga os nomes; " + ("a comparação mostra 2 ou 3 itens lado a lado." if
                                                                funcao == "comparar" else "todos de uma vez não formam um "
                                                                "conjunto útil.") + NADA_MUDOU)
    ids, _ = _membros(conv, {"ids": achado["ids"], "grupos": [g for g in achado["grupos"] if g[1] != "objeto"]})
    objetos = [chave for chave, sabor in achado["grupos"] if sabor == "objeto" and conv.brasil]
    if not conv.brasil:
        ids, _ = _membros(conv, achado)
    if objetos and ids:
        return _pergunta("Estados e municípios não ficam no mesmo gráfico: escolha só estados ou só municípios para " +
                         verbo + "." + NADA_MUDOU)
    if not objetos and not ids and deixis:
        ids = list(conv.ctx["ids"])
    if pendente and not objetos:
        ids = list(dict.fromkeys(pendentes + ids))
    selecao = ["uf:" + chave for chave in objetos] if objetos else ids
    rotulos = [conv.rotulo_do_estado(chave) for chave in objetos] if objetos else [conv.cat.rotulo(i) for i in ids] \
        if conv.cat is not None else ids
    exemplo = "“compare MANAUS (AM) e TEFE (AM)”" if conv.brasil and funcao == "comparar" else \
        "“junte MANAUS (AM), IRANDUBA (AM) e MANACAPURU (AM)”" if conv.brasil else "os nomes no mesmo pedido"
    if len(selecao) < 2:
        if funcao == "comparar" and selecao and not objetos:
            # Uma unidade só: a conversa pergunta a outra e guarda a pendência para a mensagem seguinte.
            resposta = _pergunta("Identifiquei " + rotulos[0] + ". Com qual " + ("outra " if rot.feminino else "outro ") +
                                 rot.singular + " você quer comparar? Diga um ou dois nomes." + NADA_MUDOU)
            resposta.update(pending_operation="comparisons", pending_ids=list(selecao))
            return resposta
        inicio = ("Identifiquei " + rotulos[0] + ". ") if selecao else ""
        return _pergunta(inicio + "Para " + verbo + ", diga " + ("dois ou três nomes" if funcao == "comparar" else
                                                                "dois ou mais nomes") + " no mesmo pedido, por exemplo, " +
                         exemplo + "." + NADA_MUDOU)
    if funcao == "comparar" and len(selecao) > 3:
        return _pergunta("A comparação mostra 2 ou 3 itens lado a lado, e o pedido tem " + str(len(selecao)) + ". Diga até "
                         "3 nomes ou use Ordenar ou Condições para ver todos." + NADA_MUDOU)
    painel = _painel(funcao=funcao, selecao=selecao, indicador=indicador)
    _aplica_periodo(painel, periodo)
    quando = _quando(painel)
    frases = []
    if objetos:
        painel["nivel"] = "estados"
        if funcao == "comparar":
            frases.append("Mostrei os estados e abri a comparação lado a lado de " + _e(rotulos) + quando + ": maior, menor "
                          "e diferença vêm do motor.")
        else:
            frases.append("Juntei " + _e(rotulos) + " num conjunto" + quando + ": a bolha soma as contagens estaduais, com "
                          "possível dupla contagem (quem atua em mais de um estado conta em cada um).")
        return _resposta(painel, " ".join(frases))
    if conv.ctx["nivel"] == "estados":
        painel["nivel"] = "municipios"
    if funcao == "comparar":
        atual = conv.base_atual()
        faltam = [i for i in ids if atual is not None and conv.cat is not None and i not in conv.cat.membros(atual)]
        if faltam:
            painel.update(nivel="municipios", municipios={"todos": False, "estados": list(atual["estados"]),
                                                          "ids": sorted(set(atual["ids"]) | set(faltam))})
        frases.append("Abri a comparação lado a lado de " + _e(rotulos) + quando + ": maior, menor e diferença vêm do motor.")
        if faltam:
            frases.append("Acrescentei " + _e(conv.cat.rotulo(i) for i in faltam) + " ao gráfico.")
    else:
        frases.append("Juntei " + _listed(rotulos) + " num conjunto" + quando + ": a bolha soma as contagens dos "
                      "componentes, com possível dupla contagem (quem atua em mais de " + rot.um() + " conta em cada " +
                      ("uma" if rot.feminino else "um") + ").")
    return _resposta(painel, " ".join(frases))


def _exportar(conv, dica, dica_indicador):
    pedido = conv.pedido
    encontrados = list(EXPORTAR.finditer(pedido.resto))
    if not encontrados and dica != "report":
        return None
    for encontrado in encontrados:
        pedido.consome(*encontrado.span())
    return _vista(conv, None, None, funcao="exportar")


def _rotatividade_indisponivel(conv):
    if conv.brasil:
        return _so_texto("A rotatividade precisa de dados enviados com o identificador individual (a mesma pessoa em duas "
                         "competências, CAP-ROT-01), e a base do Brasil não tem esse identificador. Para usá-la, envie "
                         "seus dados." + NADA_MUDOU)
    if not conv.fields.get("identity"):
        return _so_texto("A rotatividade precisa da coluna do identificador individual (a mesma pessoa em duas "
                         "competências, CAP-ROT-01), e esta planilha não a tem." + NADA_MUDOU)
    return None


def _texto_da_vista(conv, painel, base, modo, citados, periodo):
    rot = conv.rot
    familia = painel["familia"] or conv.ctx["familia"]
    indicador = painel["indicador"] or conv.ctx["indicador"]
    quando = _quando(painel)
    frases = []
    if painel["funcao"] == "exportar":
        frases.append("Abri Exportar: CSV com precisão integral, Imprimir/PDF e o método com os parâmetros.")
    if base is not None:
        quantidade = len(conv.cat.membros(base))
        if modo == "acrescentar":
            frases.append("Acrescentei " + _listed(citados) + " ao gráfico; agora são " + rot.unidades(quantidade) +
                          quando + ".")
        elif modo == "retirar":
            frases.append("Tirei " + _listed(citados) + " do gráfico; " + ("ficou " if quantidade == 1 else "ficaram ") +
                          rot.unidades(quantidade) + quando + ".")
        else:
            frases.append(_frase_de_base(conv, painel, base, quando))
    elif painel["familia"] == "espacial":
        frases.append("Abri a análise espacial" + quando + ": escolha a referência pelo nome, por um critério ou por um "
                      "conjunto, e o eixo X mostra a distância em linha reta (km) até ela.")
    elif painel["familia"] == "rotatividade":
        frases.append("Abri a rotatividade" + quando + ": barras de 100% com a permanência e a saída da coorte inicial.")
    elif painel["familia"] in ("tendencia", "distribuicao"):
        frases.append(("Abri a tendência" if painel["familia"] == "tendencia" else "Mostrei a distribuição") +
                      (" da " + indicador if indicador else "") + quando + ".")
    elif painel["indicador"]:
        frases.append("Troquei o indicador para " + ("a densidade por 1.000 habitantes" if painel["indicador"] ==
                                                     "densidade" else "a quantidade") + quando + ".")
    elif painel["competencia"]:
        frases.append("Mudei a competência para " + _human(painel["competencia"]) + ".")
    elif painel["janela"]:
        frases.append("Janela " + ("da rotatividade" if familia == "rotatividade" else "da tendência") + ": " +
                      quando[2:] + ".")
    if painel["visao_tendencia"]:
        frases.append("Visão da tendência: " + VISOES[painel["visao_tendencia"]] + ".")
    if painel["grupos"]:
        frases.append("Tirei os grupos por posição." if painel["grupos"]["tipo"] == "nenhum" else
                      "Grupos por posição: " + painel["grupos"]["tipo"] + ".")
    if periodo and periodo.get("nota"):
        frases.append(periodo["nota"])
    janela = painel["janela"] or []
    if familia == "tendencia" and painel["visao_tendencia"] != "mudanca" and 2 <= len(janela) < 4:
        frases.append("A classificação da tendência exige pelo menos 4 competências; com " + str(len(janela)) + ", fica a "
                      "mudança entre a primeira e a última.")
    return " ".join(frases)


def _vista(conv, dica, dica_indicador, funcao=None):
    """O que o gráfico mostra: família, indicador, grupos, visão, competência ou janela e os municípios."""
    pedido = conv.pedido
    if dica is None and funcao is None and EXPLICACAO.search(pedido.texto):
        return None  # pedido de explicação: canal contextual (provedor ou formas documentais)
    painel = _painel(funcao=funcao)
    familias = []
    encontrado = SEM_GRUPOS.search(pedido.resto)
    if encontrado:
        painel["grupos"] = {"tipo": "nenhum"}
    else:
        encontrado = GRUPOS_VISTA.search(pedido.resto)
        if encontrado:
            painel["grupos"] = {"tipo": TIPOS_GRUPO[encontrado[1]]}
        elif GRUPOS_SEM_TIPO.search(pedido.resto):
            return _pergunta("Em quantos grupos por posição?" + NADA_MUDOU,
                             [_escolha(_maiuscula(tipo), "mostre a distribuição em " + tipo)
                              for tipo in ("quartis", "quintis", "decis")])
    if encontrado:
        familias.append("distribuicao")
        pedido.consome(*encontrado.span())
    for padrao, familia in FAMILIAS_PADROES:
        for encontrado in list(padrao.finditer(pedido.resto)):
            familias.append(familia)
            pedido.consome(*encontrado.span())
    for visao, padrao in VISOES_PADROES:
        encontrado = padrao.search(pedido.resto)
        if encontrado:
            painel["visao_tendencia"] = visao
            familias.append("tendencia")
            pedido.consome(*encontrado.span())
            break
    familias = list(dict.fromkeys(familias))
    if not familias and dica in OPERACOES and OPERACOES[dica].get("familia"):
        familias = [OPERACOES[dica]["familia"]]
    if len(familias) > 1:
        nomes = {"distribuicao": "a distribuição", "espacial": "a análise espacial", "tendencia": "a tendência",
                 "rotatividade": "a rotatividade"}
        rascunhos = {"distribuicao": "mostre a distribuição", "espacial": "abra a análise espacial",
                     "tendencia": "mostre a tendência", "rotatividade": "mostre a rotatividade"}
        return _pergunta("O gráfico mostra uma análise por vez: " + " ou ".join(nomes[f] for f in familias) + "?" +
                         NADA_MUDOU, [_escolha(_maiuscula(nomes[f][2:]), rascunhos[f]) for f in familias])
    familia = familias[0] if familias else None
    if familia == "rotatividade":
        indisponivel = _rotatividade_indisponivel(conv)
        if indisponivel is not None:
            return indisponivel
    densidade = list(DENSIDADE.finditer(pedido.resto))
    quantidade = list(QUANTIDADE.finditer(pedido.resto))
    if densidade and quantidade:
        return _pergunta("O gráfico mostra um indicador por vez: densidade ou quantidade?" + NADA_MUDOU,
                         [_escolha("Densidade por 1.000 habitantes", "mostre a densidade"),
                          _escolha("Quantidade", "mostre a quantidade")])
    for encontrado in densidade + quantidade:
        pedido.consome(*encontrado.span())
    indicador = "densidade" if densidade else "quantidade" if quantidade else None
    if indicador is None and dica in OPERACOES:
        indicador = OPERACOES[dica].get("indicador") or (INDICADORES.get(dica_indicador)
                                                         if isinstance(dica_indicador, str) else None)
    painel["indicador"] = indicador
    atual = familia or conv.ctx["familia"]
    periodo, pergunta = _periodo(conv, atual in ("tendencia", "rotatividade"))
    if pergunta:
        return pergunta
    if periodo and periodo.get("janela") and familia in ("distribuicao", "espacial"):
        return _pergunta(("A distribuição" if familia == "distribuicao" else "A análise espacial") + " usa uma competência "
                         "por vez; a janela vale para a tendência. Diga uma competência, por exemplo, “em " +
                         _human(periodo["janela"][-1]) + "”, ou peça a tendência nessa janela." + NADA_MUDOU)
    if periodo and periodo.get("janela"):
        janela = periodo["janela"]
        if atual == "rotatividade":
            janela = periodo.get("pontas") or [janela[0], janela[-1]]
        elif painel["visao_tendencia"] == "mudanca" and periodo.get("pontas"):
            janela = periodo["pontas"]
        elif familia is None and conv.ctx["familia"] != "tendencia":
            familia = "tendencia"  # uma janela de competências é a tendência
        painel["janela"] = janela
    elif periodo:
        painel["competencia"] = periodo["competencia"]
    painel["familia"] = familia
    if familia == "espacial" and conv.ctx["nivel"] == "estados":
        painel["nivel"] = "municipios"
    modo = "trocar"
    encontrado = ACRESCENTAR.search(pedido.resto)
    if encontrado:
        modo = "acrescentar"
    else:
        encontrado = RETIRAR.search(pedido.resto)
        if encontrado:
            modo = "retirar"
    if encontrado:
        pedido.consome(*encontrado.span())
    achado = _resolve(conv)
    if "pergunta" in achado:
        return achado["pergunta"]
    nomes, outras = _desconhecidas(conv)
    if nomes and dica is None:
        return _nao_encontrado(conv, nomes)
    citado = bool(achado["ids"] or achado["grupos"] or achado["todos"])
    forte = bool(VERBO_VISTA.search(pedido.texto) or familia or indicador or painel["grupos"] or
                 painel["visao_tendencia"] or periodo or funcao or modo != "trocar" or dica)
    if dica is None and outras and (not forte or (PERGUNTA.match(pedido.texto) or pedido.original.strip().endswith("?"))):
        return None  # pedido com palavras que a conversa no gráfico não reconhece: segue para o intérprete
    base, citados = None, []
    if citado and conv.cat is not None:
        base, citados, resposta = _nova_base(conv, achado, modo)
        if resposta is not None:
            return resposta
        painel.update(nivel="municipios", municipios=base)
    if base is None and not any(painel[chave] is not None for chave in CHAVES):
        return None
    return _resposta(painel, _texto_da_vista(conv, painel, base, modo, citados, periodo))


# --------------------------------------------------------------------------------------------- entrada
def interpretar(mensagem, frame, fields, settings, ctx, *, brasil, opcoes=None, grupo=None, dica=None,
                dica_indicador=None):
    """Pedido da página única → {"painel", "reply"}, pergunta com alternativas ou {"handled": False}. Nunca calcula.

    dica: operação já interpretada (proposta do intérprete ou alternativa escolhida em botão); sem palavra do gráfico no
    pedido, ela decide o comando."""
    conv = _Conversa(mensagem, frame, fields, settings, ctx, brasil, opcoes, grupo)
    dica = dica if isinstance(dica, str) and dica in OPERACOES else None
    for comando in (_voltar, _condicoes, _ordenar, _referencia, _comparar_ou_juntar, _exportar, _vista):
        resposta = comando(conv, dica, dica_indicador)
        if resposta is not None:
            return resposta
    if dica is not None:
        return _resposta(painel_da_operacao(dica, dica_indicador, mensagem), "Abri " + {
            "distribuicao": "a distribuição", "espacial": "a análise espacial", "tendencia": "a tendência",
            "rotatividade": "a rotatividade"}.get(OPERACOES[dica].get("familia"), "a função pedida") + " no gráfico.")
    return {"handled": False}
