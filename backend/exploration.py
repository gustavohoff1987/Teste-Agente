"""Gramática local limitada às jornadas do Bloco 1; interpreta, nunca calcula."""
import re
import unicodedata

from territorial_selection import territory_catalog


def normalize(value):
    return "".join(c for c in unicodedata.normalize("NFD", value.lower()) if not unicodedata.combining(c)).strip()


def operation_for(message):
    text = normalize(message)
    for pattern, operation in ((r"\b(?:compare|comparar|comparacao)\b", "comparisons"),
                               (r"\b(?:evolucao|evoluir|serie temporal)\b", "temporal"),
                               (r"\b(?:agregue|agregar|agregacao|some|somar)\b", "aggregate"),
                               (r"\bdensidade\b", "density"), (r"\b(?:quantitativos|quantidade)\b", "counts")):
        if re.search(pattern, text):
            return operation
    return None


def interpret_exploration(message, frame, mapping, options):
    operation = operation_for(message)
    if not operation:
        return {"handled": False}
    text = normalize(message).rstrip(".?!")
    catalog = territory_catalog(frame, mapping, options)
    selected = options.get("territory_ids", [])
    uses_selection = bool(re.search(r"\bselecionad[oa]s?\b", text))
    # Pedidos gerais continuam no canal conversacional já existente.
    if not uses_selection and not selected and not any(
        re.search(r"(?<!\w)" + re.escape(normalize(item["name"])) + r"(?!\w)", text)
        or item["state_name"] and normalize(item["state_name"]) in text for item in catalog):
        return {"handled": False}
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
    # Maior expressão primeiro evita reconhecer Rio dentro de Rio de Janeiro.
    names = sorted(set(normalize(item["name"]) for item in catalog), key=len, reverse=True)
    for name in names:
        pattern = r"(?<!\w)" + re.escape(name) + r"(?!\w)"
        if re.search(pattern, remaining):
            matches = [item for item in catalog if normalize(item["name"]) == name]
            if len(matches) != 1:
                return {"handled": True, "clarification": "Há municípios homônimos para “" + name + "”. Selecione os códigos desejados na pesquisa territorial."}
            explicit.append(matches[0]["id"])
            remaining = re.sub(pattern, " ", remaining)
    states = {normalize(item["state_name"]): item["state_name"] for item in catalog if item["state_name"]}
    state_ids = []
    for state in sorted(states, key=len, reverse=True):
        pattern = r"(?<!\w)" + re.escape(state) + r"(?!\w)"
        if re.search(pattern, remaining):
            state_ids += [item["id"] for item in catalog if normalize(item["state_name"]) == state]
            remaining = re.sub(pattern, " ", remaining)
    allowed = ("compare comparar comparacao mostre mostrar a o os as de da do das dos em e entre para por "
               "municipio municipios cidade cidades selecionado selecionados selecionada selecionadas "
               "densidade medica medico medicos medicina quantidade quantitativos evolucao temporal "
               "agregue agregar agregacao some somar soma componentes habitantes populacao dos das "
               "examine examinar analise quero solicito uma um ver selecionadas")
    residue = re.sub(r"\b(?:" + "|".join(allowed.split()) + r")\b|[,;:]", " ", remaining)
    if residue.strip():
        return {"handled": True, "clarification": "Não consegui resolver todo o recorte solicitado. Selecione os municípios pelos nomes/códigos e confira a categoria, o indicador e os períodos abaixo."}
    ids = list(dict.fromkeys(explicit or state_ids or selected))
    if explicit and state_ids and not set(explicit).issubset(state_ids):
        return {"handled": True, "clarification": "Os municípios mencionados não correspondem ao estado solicitado. Esclareça o recorte territorial."}
    if not ids:
        return {"handled": True, "clarification": "Selecione ao menos um município na pesquisa territorial antes de continuar."}
    patch = {}
    if period:
        patch.update(period_filter=period, period_filters=[])
    if operation == "temporal":
        patch.update(period_filter="", period_filters=[], temporal_indicator=options.get("temporal_indicator") or
                     ("density" if "densidade" in text else options.get("exploration_indicator", "quantity")))
    if operation == "comparisons":
        patch["comparison_indicator"] = "quantity" if "quantidade" in text or "quantitativos" in text else options.get("exploration_indicator", "density")
    if operation == "aggregate" and "componentes" in text:
        patch.update(component_sum_confirmed=True, no_overlap_confirmed=False, identity_union_confirmed=False)
    return {"handled": True, "operation": operation, "territory_ids": ids, "options_patch": patch,
            "reply": "Recorte identificado com " + str(len(ids)) + " territórios. Confira os parâmetros e as condições metodológicas e execute a análise na conversa.",
            "selection_changed": bool(selected and set(ids) != set(selected)), "executed": False}
