"""Gramática local limitada às jornadas do Bloco 1; interpreta, nunca calcula."""
import re
import unicodedata

from territorial_selection import territory_catalog


def normalize(value):
    return "".join(c for c in unicodedata.normalize("NFD", value.lower()) if not unicodedata.combining(c)).strip()


def operation_for(message):
    text = normalize(message)
    # Referência mais próxima antes de "densidade": o comando prepara a operação e os alvos, sem criar referências.
    for pattern, operation in ((r"\b(?:referencias?|municipios?) (?:de referencia )?mais proxim[ao]s?\b", "nearest"),
                               (r"\b(?:compare|comparar|comparacao)\b", "comparisons"),
                               (r"\b(?:evolucao|evoluir|serie temporal)\b", "temporal"),
                               (r"\b(?:agregue|agregar|agregacao|some|somar)\b", "aggregate"),
                               (r"\bdensidade\b", "density"), (r"\b(?:quantitativos|quantidade)\b", "counts")):
        if re.search(pattern, text):
            return operation
    return None


def prepare_nearest(step):
    # O canal do LLM não conhece esta capacidade: o comando só prepara a operação, sem referências.
    return {"handled": True, "operation": "nearest", "options_patch": {}, "executed": False,
            "reply": "Preparei a análise de referência mais próxima. " + step +
                     " Depois defina as referências pela lista ou pelo critério. Nada foi calculado."}


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
            return prepare_nearest("Confirme a identificação territorial e selecione os municípios-alvo na pesquisa territorial.")
        if options.get("territory_ids") or "selecionad" in text:
            return {"handled": True, "clarification": "Confirme a identificação territorial antes de reutilizar a seleção."}
        return {"handled": False}
    selected = options.get("territory_ids", [])
    requested = re.search(r"\b(dois|duas|tres|2|3)\s+(?:municipios|cidades|territorios)\b", text)
    requested_count = {"dois":2,"duas":2,"tres":3,"2":2,"3":3}.get(requested[1]) if requested else options.get("conversation_requested_count")
    if requested_count not in (2,3):
        requested_count = None
    uses_selection = bool(re.search(r"\b(?:selecionad[oa]s?|esses|estes|essas|estas)\b", text)) or correction or adding
    def named(item):
        # Uma unidade chamada A não transforma todo artigo "a" em recorte.
        if len(item["name"]) <= 2:
            return bool(re.search(r"(?<!\w)" + re.escape(item["name"]) + r"(?!\w)", message))
        return bool(re.search(r"(?<!\w)" + re.escape(normalize(item["name"])) + r"(?!\w)", text))
    def state_named(item):
        # "no município de São Paulo" já determina a unidade, não o estado homônimo.
        city = r"\b(?:municipio|cidade)\s+(?:(?:de|do|da)\s+)?" + re.escape(normalize(item["state_name"])) + r"\b"
        if item["state_name"] and re.search(city, text):
            return False
        return bool(item["state_name"] and re.search(r"\b(?:do|da|de|no|na)\s+" + re.escape(normalize(item["state_name"])) + r"\b", text))
    # Pedidos gerais continuam no canal conversacional já existente.
    if not uses_selection and not selected and not requested_count and not pending and not any(named(item) or state_named(item) for item in catalog):
        if operation == "nearest":
            return prepare_nearest("Selecione os municípios-alvo na pesquisa territorial.")
        return {"handled": False}
    # Nomes citados são só alvos; "entre ..." poderia indicar candidatos a referência.
    if operation == "nearest" and re.search(r"\bentre\b", text):
        return {"handled": True, "clarification": "Na referência mais próxima, os municípios citados no pedido são tratados apenas como alvos. Defina as referências pela lista ou pelo critério nos controles da análise."}
    months = ["janeiro", "fevereiro", "marco", "abril", "maio", "junho", "julho", "agosto", "setembro", "outubro", "novembro", "dezembro"]
    period = None
    month = re.search(r"\b(" + "|".join(months) + r")\s+(?:de\s+)?(\d{4})\b", text)
    numeric = re.search(r"\b(\d{4})-?(0[1-9]|1[0-2])\b", text)
    if month:
        period = month[2] + str(months.index(month[1]) + 1).zfill(2)
        text = text[:month.start()] + text[month.end():]
    elif numeric:
        period = numeric[1] + numeric[2]
        text = text[:numeric.start()] + text[numeric.end():]
    if period:
        available = set(frame[mapping["period"]].astype(str).str.strip()) if mapping.get("period") else set()
        if period not in available:
            return {"handled": True, "clarification": "A competência solicitada não está disponível. Escolha uma das competências da base."}
    if operation == "temporal" and period:
        return {"handled": True, "clarification": "A evolução exige ao menos duas competências. Escolha os períodos no controle da análise temporal."}
    remaining = text
    explicit = []
    names = set(normalize(item["name"]) for item in catalog
                if len(item["name"]) > 2 or re.search(r"(?<!\w)" + re.escape(item["name"]) + r"(?!\w)", message))
    states = {normalize(item["state_name"]): item["state_name"] for item in catalog if state_named(item)}
    state_ids = []
    # Maior expressão primeiro, entre municípios e estados: Rio não é reconhecido dentro de
    # Rio de Janeiro, nem o município Rio Grande dentro do estado Rio Grande do Sul.
    for expression in sorted(names | set(states), key=lambda value: (-len(value), value)):
        pattern = r"(?<!\w)" + re.escape(expression) + r"(?!\w)"
        if not re.search(pattern, remaining):
            continue
        # "Municípios do Paraná" não pode virar o município Paraná (RN) sem esclarecimento.
        if expression in states and expression in names:
            return {"handled": True, "clarification": "“" + states[expression] + "” identifica um estado e também um município. Selecione os municípios na pesquisa territorial ou pelo filtro de estado."}
        if expression in states:
            state_ids += [item["id"] for item in catalog if normalize(item["state_name"]) == expression]
        else:
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
               "esses estes essas estas nao prefiro use acrescente adicione inclua")
    residue = re.sub(r"\b(?:" + "|".join(allowed.split()) + r")\b|[,;:]", " ", remaining)
    if residue.strip():
        return {"handled": True, "operation": operation, "pending_operation": operation,
                "clarification": "Identifiquei o tipo de análise, mas não consegui confirmar todo o recorte. Quais municípios você quer usar? Informe os nomes ou use a pesquisa territorial; não vou escolher municípios por conta própria."}
    # Quantidade solicitada sem nomes nunca autoriza escolher os primeiros N da base.
    targets = explicit or state_ids or (selected if uses_selection or not requested_count else [])
    if (pending == operation or adding) and explicit:
        targets = [*selected, *explicit]
    ids = list(dict.fromkeys(targets))
    if explicit and state_ids and not set(explicit).issubset(state_ids):
        return {"handled": True, "clarification": "Os municípios mencionados não correspondem ao estado solicitado. Esclareça o recorte territorial."}
    if not ids:
        return {"handled": True, "operation": operation, "pending_operation": operation,
                "requested_count": requested_count, "reset_selection": bool(requested_count),
                "clarification": ("Quais " + str(requested_count) + " municípios você quer analisar? Informe os nomes ou use a pesquisa territorial." if requested_count else
                                  "Quais municípios você quer analisar? Informe os nomes ou selecione-os na pesquisa territorial.")}
    clarification = None
    if operation == "comparisons" and len(ids) < 2:
        label = next(item["label"] for item in catalog if item["id"] == ids[0])
        clarification = "Identifiquei " + label + ". Com qual outro município você deseja comparar? Pode informar dois ou mais municípios."
    elif requested_count and len(ids) != requested_count:
        clarification = "Você pediu " + str(requested_count) + " municípios, mas identificamos " + str(len(ids)) + ". Quais nomes devem compor a análise?"
    patch = {}
    if period:
        patch.update(period_filter=period, period_filters=[])
    if operation == "temporal":
        patch.update(period_filter="", period_filters=[], temporal_indicator=options.get("temporal_indicator") or
                     ("density" if "densidade" in text else options.get("exploration_indicator", "quantity")))
    if operation == "comparisons":
        patch["comparison_indicator"] = "quantity" if "quantidade" in text or "quantitativos" in text else options.get("exploration_indicator", "density")
    if correction and "densidade" in text:
        patch["comparison_indicator"] = "density"
    if operation == "aggregate" and "componentes" in text:
        patch.update(component_sum_confirmed=True, no_overlap_confirmed=False, identity_union_confirmed=False)
    return {"handled": True, "operation": operation, "territory_ids": ids, "options_patch": patch,
            **({"clarification": clarification, "pending_operation": operation, "requested_count": requested_count} if clarification else {}),
            "reply": ("Alvos identificados: " + str(len(ids)) + " territórios. Defina as referências pela lista ou pelo critério e "
                      "confirme o período e o referencial na preparação; nenhuma referência foi escolhida e nada foi calculado."
                      if operation == "nearest" else
                      "Recorte identificado com " + str(len(ids)) + " territórios. Confira os parâmetros e as condições metodológicas e execute a análise na preparação."),
            "selection_changed": bool(selected and set(ids) != set(selected)), "executed": False}
