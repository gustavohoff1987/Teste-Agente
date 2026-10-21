"""Gramática local limitada às jornadas do Bloco 1; interpreta, nunca calcula.

Na base oficial, os estados também são objetos de análise (fonte estadual de médicos únicos): "em Minas Gerais",
"estado de São Paulo" e "estados da Região Norte" marcam estados na abrangência territorial, e "municípios de Minas
Gerais" continua marcando os municípios do estado. O nome de estado que também é de município ("São Paulo", "Paraná")
só vira o estado com "estado de" ou com a palavra "estado" no pedido; com preposição e sem essa indicação, a conversa
pergunta; sem preposição, continua sendo o município. Anos ("em 2024") e intervalos ("entre 2014 e 2024") viram as
competências da base nesses anos; nada é escolhido entre elas quando a análise usa uma competência só.
"""
import functools
import re
import unicodedata

from territorial_selection import REGIONS, STATES, territory_catalog

MONTHS = ["janeiro", "fevereiro", "marco", "abril", "maio", "junho", "julho", "agosto", "setembro", "outubro", "novembro",
          "dezembro"]
MONTH_NAMES = ["janeiro", "fevereiro", "março", "abril", "maio", "junho", "julho", "agosto", "setembro", "outubro",
               "novembro", "dezembro"]
# Análises cuja preparação aceita várias competências; as demais usam uma competência.
MULTIPLE_PERIODS = ("counts", "temporal", "report", "comparisons")
QUANTITY = r"\b(?:quantidade|quantitativos|quant[oa]s|numero\s+de)\b"
# Nomes de estado que, sem acento, são palavras comuns ("para"): o estado só é reconhecido escrito com acento ("Pará").
WORDS = {"para"}
# "estados da Região Norte", "estados do Nordeste", "UFs da região Sul" (Grandes Regiões pelo código IBGE da UF).
REGION = re.compile(r"\b(?:(?:os|as)\s+)?(?:estados|ufs)\s+(?:da\s+regiao|do|da)\s+(norte|nordeste|sudeste|sul|centro[\s-]oeste)\b")


@functools.lru_cache(maxsize=65536)  # os nomes do catálogo territorial se repetem a cada mensagem
def normalize(value):
    return "".join(c for c in unicodedata.normalize("NFD", value.lower()) if not unicodedata.combining(c)).strip()


def operation_for(message):
    text = normalize(message)
    # Referência mais próxima antes de "densidade": o comando prepara a operação e os alvos, sem criar referências.
    for pattern, operation in ((r"\b(?:referencias?|municipios?) (?:de referencia )?mais proxim[ao]s?\b", "nearest"),
                               (r"\b(?:compare|comparar|comparacao)\b", "comparisons"),
                               (r"\b(?:evolucao|evoluir|serie temporal)\b", "temporal"),
                               (r"\b(?:agregue|agregar|agregacao|some|somar)\b", "aggregate"),
                               (r"\bdensidade\b", "density"),
                               (r"\b(?:quantitativos|quantidade|quant[oa]s\s+(?:medic[oa]s|profissionais)|"
                                r"numero\s+de\s+(?:medic[oa]s|profissionais))\b", "counts")):
        if re.search(pattern, text):
            return operation
    return None


def prepare_nearest(step):
    # O canal do LLM não conhece esta capacidade: o comando só prepara a operação, sem referências.
    return {"handled": True, "operation": "nearest", "options_patch": {}, "executed": False,
            "reply": "Preparei a análise de referência mais próxima. " + step +
                     " Depois defina as referências pela lista ou pelo critério. Nada foi calculado."}


def _human(period):
    return MONTH_NAMES[int(period[4:]) - 1] + " de " + period[:4] if re.fullmatch(r"\d{4}(0[1-9]|1[0-2])", period) else period


def _state_label(prefix):
    return STATES[prefix][1] + " (" + STATES[prefix][0] + ")"


def _ambiguous(name, operation, group=False):
    """O nome é de um estado e também de um município: a conversa pergunta (nada é escolhido em silêncio) e a análise
    fica pendente para a resposta ("estado de São Paulo")."""
    return {"handled": True, "operation": operation, "pending_operation": operation,
            "clarification": "“" + name + "” identifica um estado e também um município. " + (
        "Para os municípios do estado, marque o grupo na abrangência territorial; para o município, diga “município de " +
        name + "”." if group else "Diga “estado de " + name + "” ou “município de " + name + "”.")}


def interpret_exploration(message, frame, mapping, options, *, operation_hint=None):
    # O hint vem de enumeração validada: proposta do LLM ou escolha explícita do usuário.
    pending = options.get("conversation_pending_operation")
    operation = operation_hint or operation_for(message)
    correction = bool(re.fullmatch(r"(?:nao[, ]+)?(?:quero |prefiro |use )?(?:quantidade|quantitativos|densidade)[.!?]*", normalize(message)))
    adding = bool(re.search(r"\b(?:acrescente|adicione|inclua)\b", normalize(message)))
    if correction or (adding and not operation):
        active = options.get("exploration_operation")
        if active in ("comparisons", "density", "counts", "temporal", "aggregate"):
            operation = active
            if correction and active in ("density", "counts"):
                operation = "density" if "densidade" in normalize(message) else "counts"
    if not operation and pending in ("comparisons", "density", "counts", "temporal", "aggregate"):
        operation = pending
    if not operation and re.search(r"\b(?:dois|duas|tres|2|3)\s+(?:municipios|cidades|territorios)\b", normalize(message)) and re.search(r"\b(?:analise|analisar)\b", normalize(message)):
        operation = options.get("exploration_operation")
    if not operation:
        return {"handled": False}
    text = normalize(message).rstrip(".?!")
    try:
        catalog = territory_catalog(frame, mapping, options)
    except ValueError:
        if operation == "nearest":
            return prepare_nearest("Escolha a coluna do código territorial antes de selecionar os municípios-alvo na pesquisa territorial.")
        if options.get("territory_ids") or "selecionad" in text:
            return {"handled": True, "clarification": "Escolha a coluna do código territorial antes de selecionar ou reutilizar unidades."}
        return {"handled": False}
    selected = options.get("territory_ids", [])
    requested = re.search(r"\b(dois|duas|tres|2|3)\s+(?:municipios|cidades|territorios)\b", text)
    requested_count = {"dois":2,"duas":2,"tres":3,"2":2,"3":3}.get(requested[1]) if requested else options.get("conversation_requested_count")
    if requested_count not in (2,3):
        requested_count = None
    uses_selection = bool(re.search(r"\b(?:selecionad[oa]s?|esses|estes|essas|estas)\b", text)) or correction or adding
    def named(item):
        # Uma unidade chamada A não transforma todo artigo "a" em recorte. O trecho precisa estar no texto para a
        # expressão casar: testá-lo antes evita compilar uma expressão por unidade do catálogo a cada mensagem.
        if len(item["name"]) <= 2:
            return item["name"] in message and bool(re.search(r"(?<!\w)" + re.escape(item["name"]) + r"(?!\w)", message))
        name = normalize(item["name"])
        return name in text and bool(re.search(r"(?<!\w)" + re.escape(name) + r"(?!\w)", text))
    # Estados da base oficial (código IBGE no catálogo): nome normalizado → (prefixo, nome). A região usa todos; o nome
    # citado, só os que não são palavras comuns sem acento.
    known = {}
    for item in catalog:
        if item.get("state_code"):
            known.setdefault(normalize(item["state_name"]), (item["state_code"], item["state_name"]))
    states = {key: value for key, value in known.items()
              if key not in WORDS or re.search(r"(?<!\w)" + re.escape(value[1]) + r"(?!\w)", message, re.IGNORECASE)}
    region = REGION.search(text) if known else None
    mentioned = any(re.search(r"(?<!\w)" + re.escape(name) + r"(?!\w)", text) for name in states)
    # Pedidos gerais continuam no canal conversacional já existente.
    if not uses_selection and not selected and not requested_count and not pending and not region and not mentioned and \
            not any(named(item) for item in catalog):
        if operation == "nearest":
            return prepare_nearest("Selecione os municípios-alvo na pesquisa territorial.")
        return {"handled": False}
    # Nomes citados são só alvos; "entre ..." poderia indicar candidatos a referência.
    if operation == "nearest" and re.search(r"\bentre\b", text):
        return {"handled": True, "clarification": "Na referência mais próxima, os municípios citados no pedido são tratados apenas como alvos. Defina as referências pela lista ou pelo critério nos controles da análise."}
    period, years = None, None
    month = re.search(r"\b(" + "|".join(MONTHS) + r")\s+(?:de\s+)?(\d{4})\b", text)
    numeric = re.search(r"\b(\d{4})-?(0[1-9]|1[0-2])\b", text)
    if month:
        period = month[2] + str(MONTHS.index(month[1]) + 1).zfill(2)
        text = text[:month.start()] + text[month.end():]
    elif numeric:
        period = numeric[1] + numeric[2]
        text = text[:numeric.start()] + text[numeric.end():]
    else:  # um ano ("em 2024") ou um intervalo de anos ("entre 2014 e 2024", "de 2014 a 2024")
        span = re.search(r"\b(?:entre|de)\s+(\d{4})\s+(?:e|a|ate)\s+(\d{4})\b", text)
        found = span or re.search(r"\b(?:em|de|no ano de|do ano de)\s+(\d{4})\b", text)
        if found:
            years = sorted((int(found[1]), int(found[2] if span else found[1])))
            text = text[:found.start()] + " " + text[found.end():]
    available = sorted(set(frame[mapping["period"]].astype(str).str.strip())) if mapping.get("period") else []
    if period and period not in available:
        return {"handled": True, "clarification": "A competência solicitada não está disponível. Escolha uma das competências da base."}
    year_periods = None
    if years is not None:
        # Competências AAAAMM do ano ou, numa base com período anual, o próprio ano.
        year_periods = [value for value in available if re.fullmatch(r"\d{6}|\d{4}", value) and
                        years[0] <= int(value[:4]) <= years[1]]
        if not year_periods:
            return {"handled": True, "clarification": "A base não tem competências " + (
                "em " + str(years[0]) if years[0] == years[1] else "entre " + str(years[0]) + " e " + str(years[1])) +
                ". Escolha uma das competências da base."}
    if operation == "temporal" and (period or (year_periods is not None and len(year_periods) < 2)):
        return {"handled": True, "clarification": "A evolução exige ao menos duas competências. Escolha os períodos no controle da análise temporal."}
    remaining = text
    explicit = []
    objects = []  # estados como objeto (prefixo IBGE), da fonte estadual
    match = REGION.search(remaining) if region else None  # posições depois de retirado o período
    if match:
        digit = next(key for key, name in REGIONS.items() if normalize(name).replace("-", " ") ==
                     re.sub(r"[\s-]+", " ", match[1]))
        found = sorted({prefix for prefix, _ in known.values() if prefix[0] == digit})
        if not found:
            return {"handled": True, "clarification": "Nenhum estado da Região " + REGIONS[digit] + " nesta base."}
        objects += found
        remaining = remaining[:match.start()] + " " + remaining[match.end():]
    names = set(normalize(item["name"]) for item in catalog
                if len(item["name"]) > 2 or (item["name"] in message and
                                             re.search(r"(?<!\w)" + re.escape(item["name"]) + r"(?!\w)", message)))
    statewide = bool(re.search(r"\bestados?\b", text)) and not re.search(r"\b(?:municipios?|cidades?)\b", text)
    # Pedido que já cita estados (nome só de estado ou região): o nome também de município não é escolhido em silêncio.
    with_states = bool(region) or any(name not in names and re.search(r"(?<!\w)" + re.escape(name) + r"(?!\w)", text)
                                      for name in states)
    state_ids = []
    # Maior expressão primeiro, entre municípios e estados: Rio não é reconhecido dentro de
    # Rio de Janeiro, nem o município Rio Grande dentro do estado Rio Grande do Sul.
    for expression in sorted(names | set(states), key=lambda value: (-len(value), value)):
        if expression not in remaining:
            continue  # condição necessária da expressão abaixo, sem compilá-la
        pattern = r"(?<!\w)" + re.escape(expression) + r"(?!\w)"
        found = re.search(pattern, remaining)
        if not found:
            continue
        before = remaining[:found.start()]
        if expression in states:
            prefix, name = states[expression]
            both = expression in names
            if re.search(r"\bmunicipios\s+(?:de|do|da|dos|das|no|na|nos|nas|em)\s+$", before):
                # "Municípios do Paraná" não pode virar o município Paraná (RN) sem esclarecimento.
                if both:
                    return _ambiguous(name, operation, group=True)
                state_ids += [item["id"] for item in catalog if item.get("state_code") == prefix]
                remaining = re.sub(pattern, " ", remaining)
                continue
            if not (both and re.search(r"\b(?:municipio|cidade)\s+(?:(?:de|do|da)\s+)?$", before)):
                if not both or statewide or re.search(r"\bestados?\s+(?:de|do|da)\s+$", before):
                    objects.append(prefix)
                    remaining = re.sub(pattern, " ", remaining)
                    continue
                if with_states or re.search(r"\b(?:de|do|da|no|na|em)\s+$", before):
                    return _ambiguous(name, operation)
        matches = [item for item in catalog if normalize(item["name"]) == expression]
        if len(matches) != 1:
            return {"handled": True, "clarification": "Há municípios homônimos para “" + expression + "”. Selecione os códigos desejados na pesquisa territorial."}
        explicit.append(matches[0]["id"])
        remaining = re.sub(pattern, " ", remaining)
    allowed = ("compare comparar comparacao mostre mostrar a o os as de da do das dos em e entre para por "
               "municipio municipios cidade cidades selecionado selecionados selecionada selecionadas "
               "densidade medica medico medicos medicina quantidade quantitativos evolucao temporal "
               "agregue agregar agregacao some somar soma componentes habitantes populacao dos das "
               "examine examinar analise quero solicito uma um ver selecionadas "
               "calcule calcular identifique identificar referencia referencias mais proxima proximas proximo proximos "
               "cada alvo alvos geografica geograficamente qual quais "
               "agora vamos analisar comparativamente comparativo comparativa no na nos nas tambem "
               "depois seguir continuar gostaria desejo preciso pode poderia favor por favor colocar coloque "
               "ponha bote lado lados a ao junto juntos duas dois tres 2 3 mesmo mesma mesmos mesmas "
               "periodo indicador categorias categoria analises ultima anterior com perfil "
               "esses estes essas estas nao prefiro use acrescente adicione inclua "
               "quantos quantas havia haviam existia existiam tinha tinham era eram numero estado estados uf ufs")
    residue = re.sub(r"\b(?:" + "|".join(allowed.split()) + r")\b|[,;:]", " ", remaining)
    if residue.strip():
        return {"handled": True, "operation": operation, "pending_operation": operation,
                "clarification": "Identifiquei o tipo de análise, mas não consegui confirmar todo o recorte. " + (
                    "Quais estados ou municípios você quer usar? Informe os nomes ou use a abrangência territorial; não "
                    "vou escolher territórios por conta própria." if known else
                    "Quais municípios você quer usar? Informe os nomes ou use a pesquisa territorial; não vou escolher "
                    "municípios por conta própria.")}
    objects = list(dict.fromkeys(objects))
    if objects and operation == "nearest":
        from territorial_levels import group_label  # importação tardia: o módulo de níveis é mais pesado
        example = group_label(objects[0])
        return {"handled": True, "clarification": "Na referência mais próxima, os alvos são municípios: estados não têm um "
                                                  "ponto único. Para usar os municípios de um estado, peça, por exemplo, "
                                                  "“" + example[0].lower() + example[1:] + "”."}
    # Quantidade solicitada sem nomes nunca autoriza escolher os primeiros N da base. Estados citados substituem a seleção
    # (a conversa recebe só os municípios marcados, não os estados).
    if objects and not explicit and not state_ids:
        targets = selected if uses_selection else []
    else:
        targets = explicit or state_ids or (selected if uses_selection or not requested_count else [])
    if (pending == operation or adding) and explicit:
        targets = [*selected, *explicit]
    ids = list(dict.fromkeys(targets))
    if explicit and state_ids and not set(explicit).issubset(state_ids):
        return {"handled": True, "clarification": "Os municípios mencionados não correspondem ao estado solicitado. Esclareça o recorte territorial."}
    if not ids and not objects:
        return {"handled": True, "operation": operation, "pending_operation": operation,
                "requested_count": requested_count, "reset_selection": bool(requested_count),
                "clarification": ("Quais " + str(requested_count) + " municípios você quer analisar? Informe os nomes ou use a pesquisa territorial." if requested_count else
                                  "Quais municípios você quer analisar? Informe os nomes ou selecione-os na pesquisa territorial.")}
    clarification, pending_choice = None, True
    if operation == "comparisons" and len(ids) + len(objects) < 2:
        if objects:  # a conversa não recebe os estados marcados: o pedido precisa nomear todos
            clarification, pending_choice = ("Identifiquei " + _state_label(objects[0]) + ". Para comparar estados, "
                                             "informe dois ou mais no mesmo pedido (por exemplo, “Compare " +
                                             STATES[objects[0]][1] + " e …”) ou marque-os na abrangência territorial."), False
        else:
            label = next(item["label"] for item in catalog if item["id"] == ids[0])
            clarification = "Identifiquei " + label + ". Com qual outro município você deseja comparar? Pode informar dois ou mais municípios."
    elif requested_count and len(ids) != requested_count:
        clarification = "Você pediu " + str(requested_count) + " municípios, mas identificamos " + str(len(ids)) + ". Quais nomes devem compor a análise?"
    patch = {}
    if period:
        patch.update(period_filter=period, period_filters=[])
    elif year_periods:
        if len(year_periods) == 1:
            patch.update(period_filter=year_periods[0], period_filters=[])
        elif operation in MULTIPLE_PERIODS:
            patch.update(period_filter="", period_filters=year_periods)
        elif clarification is None:  # análise de uma competência: a escolha entre as do ano fica com o usuário
            listed = (" e ".join(_human(value) for value in year_periods) if len(year_periods) <= 3 else
                      "de " + _human(year_periods[0]) + " a " + _human(year_periods[-1]))
            clarification, pending_choice = (("Em " + str(years[0]) if years[0] == years[1] else
                                              "Entre " + str(years[0]) + " e " + str(years[1])) + ", a base tem " +
                                             str(len(year_periods)) + " competências (" + listed + "). Esta análise usa "
                                             "uma competência: escolha uma na caixa Período ou peça, por exemplo, “em " +
                                             _human(year_periods[-1]) + "”."), False
    quantity = bool(re.search(QUANTITY, text))
    if operation == "temporal":
        patch.update(period_filter="", period_filters=year_periods or [], temporal_indicator=(
            "density" if "densidade" in text else "quantity" if quantity else
            options.get("temporal_indicator") or options.get("exploration_indicator", "quantity")))
    if operation == "comparisons":
        patch["comparison_indicator"] = "quantity" if quantity else "density" if "densidade" in text else \
            options.get("exploration_indicator", "density")
    if correction and "densidade" in text:
        patch["comparison_indicator"] = "density"
    total = len(ids) + len(objects)
    return {"handled": True, "operation": operation, "territory_ids": ids, **({"estados": objects} if objects else {}),
            "options_patch": patch,
            **({"clarification": clarification} if clarification else {}),
            **({"pending_operation": operation, "requested_count": requested_count} if clarification and pending_choice else {}),
            "reply": ("Alvos identificados: " + str(len(ids)) + " territórios. Defina as referências pela lista ou pelo critério e "
                      "escolha o período e o referencial na preparação; nenhuma referência foi escolhida e nada foi calculado."
                      if operation == "nearest" else
                      "Recorte identificado com " + str(total) + (" território" if total == 1 else " territórios") +
                      ". Confira os parâmetros e as condições metodológicas e execute a análise na preparação."),
            "selection_changed": bool(selected and set(ids) != set(selected)), "executed": False}
