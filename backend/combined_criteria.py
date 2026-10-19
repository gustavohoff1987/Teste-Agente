"""Critérios combinados (CAP-SUB-01) sobre os territórios de uma competência (Bloco 2, Etapa 2).

Atributos por território, no período e na categoria escolhidos: densidade por 1.000 habitantes,
quantidade, população, distância à referência mais próxima (resultado de CAP-ESP-02, sem refazer o
mecanismo geográfico) e pertença a uma lista de territórios ou a uma UF (regra governada da base
Brasil). Operadores <, ≤, >, ≥, =, ≠ e pertença; composição E, OU e NÃO em três estados (ATENDE,
NAO_ATENDE, NAO_AVALIAVEL). Comparações exatas, em frações racionais sobre os valores completos.

Os valores dos critérios são escolhas do usuário, não pontos de corte normativos. O motor avalia; a
conversa, quando usada, apenas estrutura critérios ancorados no pedido. Ordenação (CAP-SUB-02),
seleção por posição (CAP-SUB-03), faixas (CAP-DIS-03/CAP-ESP-03) e comparação entre conjuntos usam
os mesmos valores por território, calculados uma vez por requisição.
"""
import re
from collections import Counter
from decimal import Decimal, InvalidOperation
from fractions import Fraction

import numpy as np
import pandas as pd

from data_contract import ChoiceRequired, numbers, scoped, text_values
from nearest_reference import MOTIVES, TPL_11, _compare, _in_period, analysis_period, compute_nearest, nearest_inputs, row_ids
from territorial_selection import STATES, territory_catalog

METHOD = {"capacidades": ["CAP-SUB-01", "CAP-SUB-02", "CAP-SUB-03", "CAP-DIS-03", "CAP-ESP-03"], "versao": "1.0",
          "logica": "três estados (ATENDE, NAO_ATENDE, NAO_AVALIAVEL) com as regras de E, OU e NÃO de CAP-SUB-01",
          "comparacao": "exata, em frações racionais sobre os valores completos; sem arredondamento nem tolerância"}
NUMERIC = {"densidade": "densidade", "quantidade": "quantidade", "populacao": "população",
           "distancia": "distância à referência mais próxima"}
SCALES = {"densidade": {None: 1, "por_1000_habitantes": 1, "por_10000_habitantes": Fraction(1, 10),
                        "por_100000_habitantes": Fraction(1, 100)},
          "distancia": {None: 1, "km": 1, "m": Fraction(1, 1000)}}
UNIT_TEXT = {"por_1000_habitantes": "por 1.000 habitantes", "por_10000_habitantes": "por 10.000 habitantes",
             "por_100000_habitantes": "por 100.000 habitantes", "km": "km", "m": "m", "habitantes": "habitantes"}
OPERATORS = {"<": "<", "<=": "≤", ">": ">", ">=": "≥", "=": "=", "!=": "≠"}
MEMBERSHIP = {"in": "pertence a", "not_in": "não pertence a"}
LOGIC = {"and": "E", "or": "OU", "not": "NAO"}
LEAF_KEYS = {"id", "attribute", "operator", "value", "unit", "category"}
NODE_ID = re.compile(r"[A-Za-z0-9_-]{1,24}")
MAX_LEAVES, MAX_DEPTH = 12, 4
UFS = {sigla for sigla, _ in STATES.values()}


def _and(states):
    return "ATENDE" if all(s == "ATENDE" for s in states) else "NAO_ATENDE" if "NAO_ATENDE" in states else "NAO_AVALIAVEL"


def _or(states):
    return "ATENDE" if "ATENDE" in states else "NAO_ATENDE" if all(s == "NAO_ATENDE" for s in states) else "NAO_AVALIAVEL"


def _not(state):
    return {"ATENDE": "NAO_ATENDE", "NAO_ATENDE": "ATENDE"}.get(state, "NAO_AVALIAVEL")


COMBINE = {"E": _and, "OU": _or, "NAO": lambda states: _not(states[0])}


def decimal_value(value, label="valor do critério"):
    """Número não negativo escrito pelo usuário (vírgula ou ponto decimal, sem separador de milhares)."""
    if isinstance(value, bool) or not isinstance(value, (str, int, float)):
        raise ValueError("Informe o " + label + " como número.")
    text = str(value).strip()
    if ("," in text and "." in text) or len(text) > 32:
        raise ValueError("Valor numérico ambíguo ou longo demais em " + label + ": use só a vírgula ou só o ponto decimal.")
    try:
        number = Decimal(text.replace(",", "."))
    except InvalidOperation:
        number = None
    if number is None or not number.is_finite() or number < 0:
        raise ValueError("O " + label + " deve ser um número não negativo.")
    return number


def _number_text(number):
    return format(number, "f").replace(".", ",")


def parse_tree(tree, options):
    """Árvore autorizada: folhas estruturadas e compostos E/OU/NÃO; expressões livres são recusadas."""
    nodes, leaves, used = {}, [], set()

    def node_id(node, prefix):
        given = node.get("id")
        if given is not None and (not isinstance(given, str) or not NODE_ID.fullmatch(given)):
            raise ValueError("Identificador de condição inválido.")
        if given is None:
            count = len(nodes) + 1
            while prefix + str(count) in used:
                count += 1
            given = prefix + str(count)
        if given in used:
            raise ValueError("Identificadores de condição repetidos: " + given)
        used.add(given)
        return given

    def visit(node, depth):
        if not isinstance(node, dict):
            raise ValueError("Expressões livres não são aceitas: descreva cada condição com indicador, operador e valor.")
        if depth > MAX_DEPTH:
            raise ValueError("A combinação de critérios excede a profundidade permitida (" + str(MAX_DEPTH) + " níveis).")
        if "logic" in node:
            if set(node) - {"id", "logic", "operands"} or node["logic"] not in LOGIC:
                raise ValueError("Combinação não autorizada: use E, OU ou NÃO sobre condições estruturadas.")
            operands = node.get("operands")
            if not isinstance(operands, list) or (len(operands) != 1 if node["logic"] == "not" else len(operands) < 2):
                raise ValueError("NÃO exige uma condição; E e OU exigem ao menos duas.")
            own = node_id(node, "n")
            nodes[own] = {"no": own, "tipo": "COMPOSTO", "operador_logico": LOGIC[node["logic"]],
                          "operandos": [visit(child, depth + 1) for child in operands]}
            return own
        if set(node) - LEAF_KEYS:
            raise ValueError("Campo não reconhecido na condição: " + ", ".join(sorted(set(node) - LEAF_KEYS)))
        if len(leaves) >= MAX_LEAVES:
            raise ValueError("Use no máximo " + str(MAX_LEAVES) + " condições.")
        own = node_id(node, "c")
        nodes[own] = _leaf(node, own, options)
        leaves.append(own)
        return own

    root = visit(tree, 1)
    return nodes, leaves, root


def _leaf(node, own, options):
    attribute, operator, value, unit = node.get("attribute"), node.get("operator"), node.get("value"), node.get("unit")
    leaf = {"no": own, "tipo": "ATOMICO", "atributo": attribute, "operador": operator, "origem": "escolha do usuário"}
    if attribute in NUMERIC:
        if operator not in OPERATORS:
            raise ValueError("Operador não autorizado para " + NUMERIC[attribute] + ": use <, ≤, >, ≥, = ou ≠.")
        number = decimal_value(value, "valor de " + NUMERIC[attribute])
        if attribute in SCALES:
            if unit not in SCALES[attribute]:
                raise ValueError("Unidade não suportada para " + NUMERIC[attribute] + ".")
            threshold = Fraction(number) * SCALES[attribute][unit]
            context = UNIT_TEXT[unit] if unit else ("por 1.000 habitantes" if attribute == "densidade" else "km")
        elif attribute == "quantidade":
            if unit not in (None, options.get("count_unit")):
                raise ValueError("A unidade informada difere da unidade de contagem da base; não há conversão entre pessoas, vínculos e postos.")
            threshold, context = Fraction(number), str(options.get("count_unit") or "unidade de contagem da base")
        else:
            if unit not in (None, "habitantes"):
                raise ValueError("População é comparada em habitantes.")
            threshold, context = Fraction(number), "habitantes"
        category = node.get("category")
        if category is not None and (attribute not in ("densidade", "quantidade") or not isinstance(category, str) or not category.strip()):
            raise ValueError("Categoria só pode ser escolhida para densidade e quantidade.")
        value_unit = {"densidade": "por 1.000 habitantes", "distancia": "km", "populacao": "habitantes"}.get(attribute, context)
        leaf.update({"simbolo": OPERATORS[operator], "limiar": threshold, "unidade_valor": value_unit,
                     "parametros": {"valor": format(number, "f"), "unidade": context, "unidade_informada": unit,
                                    "contexto": "unidade informada pelo usuário" if unit else
                                    "valor sem unidade interpretado no único contexto do atributo (" + context + ")",
                                    **({"categoria": category.strip()} if category else {})},
                     "condicao": NUMERIC[attribute] + " " + OPERATORS[operator] + " " + _number_text(number) + " " + (UNIT_TEXT.get(unit) or context)})
        return leaf
    if attribute == "territorio":
        if operator not in MEMBERSHIP:
            raise ValueError("Pertença territorial usa 'pertence a' ou 'não pertence a' uma lista.")
        if (not isinstance(value, list) or not value or len(value) > 10000 or len(set(value)) != len(value)
                or any(not isinstance(v, str) or not v or len(v) > 512 for v in value)):
            raise ValueError("A lista de territórios do critério deve conter identificadores distintos.")
        leaf.update({"simbolo": MEMBERSHIP[operator], "membros": list(value), "parametros": {"lista": list(value)},
                     "condicao": "território " + MEMBERSHIP[operator] + " uma lista de " + str(len(value)) + " território(s)"})
        return leaf
    if attribute == "uf":
        values = [value] if isinstance(value, str) and operator in ("=", "!=") else value
        if operator not in ("=", "!=", "in", "not_in") or not isinstance(values, list) or not values or (
                operator in ("=", "!=") and len(values) != 1):
            raise ValueError("UF usa =, ≠ ou pertença a uma lista de siglas.")
        values = [str(v).strip().upper() for v in values]
        if any(v not in UFS for v in values) or len(set(values)) != len(values):
            raise ValueError("UF não reconhecida: use siglas como TO, SC ou SP.")
        symbol = MEMBERSHIP.get(operator) or OPERATORS[operator]
        leaf.update({"simbolo": symbol, "membros": values, "parametros": {"siglas": values},
                     "condicao": "UF " + symbol + " " + ", ".join(values)})
        return leaf
    raise ValueError("Atributo de critério não autorizado: use densidade, quantidade, população, distância, território ou UF.")


def tree_attributes(tree):
    """Atributos das folhas, sem validar (usado pelo pré-exame para saber quais papéis serão consumidos)."""
    found, stack = [], [tree]
    while stack:
        node = stack.pop()
        if isinstance(node, dict):
            if isinstance(node.get("operands"), list):
                stack.extend(node["operands"])
            elif isinstance(node.get("attribute"), str):
                found.append(node["attribute"])
    return found


def needs(options):
    """Papéis exigidos pela definição: medidas (quantitativo/população) e coordenadas."""
    attributes = set(tree_attributes(options.get("criteria")))
    for key in ("ranking", "bands"):
        if isinstance(options.get(key), dict) and isinstance(options[key].get("attribute"), str):
            attributes.add(options[key]["attribute"])
    comparison = options.get("comparison")
    if isinstance(comparison, dict):
        attributes.update(tree_attributes(comparison.get("criteria")))
    spatial = "distancia" in attributes
    criterion_refs = spatial and options.get("reference_mode") == "criterion"
    return {"spatial": spatial, "count": bool(attributes & {"densidade", "quantidade"}) or criterion_refs,
            "population": bool(attributes & {"densidade", "populacao"}) or criterion_refs}


def _category(frame, mapping, options, period, requested):
    rows = _in_period(frame, mapping, period)
    if not mapping.get("category"):
        if not (options.get("category_constant") or options.get("fts_scope_confirmed")):
            raise ChoiceRequired("Informe o objeto de análise: a profissão ou o conjunto de trabalhadores da força de "
                                 "trabalho em saúde.")
        return None
    available = set(text_values(rows[mapping["category"]]).dropna().tolist())
    category = str(requested or options.get("category_filter") or "").strip()
    if not category:
        if len(available) != 1:
            raise ChoiceRequired("Escolha a categoria profissional dos critérios.")
        category = next(iter(available))
    if category not in available:
        raise ValueError("A categoria " + category + " não existe no período dos critérios.")
    return category


def measures(frame, mapping, options, period, category, count, population):
    """Quantidade e/ou população por território no período e na categoria; uma linha por território.

    A associação das colunas (reconhecida por regra configurada, pelo perfil oficial ou escolhida) é exigida pelo pré-exame."""
    if count:
        if not mapping.get("count"):
            raise ValueError("Critérios de densidade e quantidade usam a coluna de quantitativos; associe-a.")
        if not options.get("count_unit"):
            raise ChoiceRequired("Escolha a unidade de contagem dos quantitativos usados nos critérios.")
    if population and not mapping.get("population"):
        raise ValueError("Critérios de densidade e de população exigem uma coluna de população associada.")
    rows = _in_period(frame, mapping, period)
    if category is not None:
        rows = rows[text_values(rows[mapping["category"]]) == category]
    if rows.empty:
        raise ValueError("Não há registros no período e na categoria dos critérios.")
    ids = row_ids(rows, mapping)
    if ids.duplicated().any():
        raise ValueError("Há territórios homônimos ou várias linhas por território no período e na categoria dos "
                         "critérios. Associe o código territorial ou resolva as multiplicidades antes de aplicar critérios.")
    quantity = numbers(rows[mapping["count"]], "quantidade", options) if count else pd.Series(np.nan, index=rows.index)
    if count and options.get("count_unit") in ("pessoas", "vinculos", "postos") and quantity.dropna().mod(1).ne(0).any():
        raise ValueError("Contagens de pessoas, vínculos e postos devem ser inteiras; confira a unidade e o formato numérico.")
    people = numbers(rows[mapping["population"]], "população", options) if population else pd.Series(np.nan, index=rows.index)
    return {key: (None if pd.isna(q) else q, None if pd.isna(p) else p)
            for key, q, p in zip(ids.tolist(), quantity.tolist(), people.tolist())}


def criteria_inputs(frame, mapping, options):
    """Validações e insumos sem distâncias (usadas também pelo pré-exame)."""
    tree, ranking, bands = options.get("criteria"), options.get("ranking"), options.get("bands")
    if tree is None and not ranking and not bands:
        raise ChoiceRequired("Defina ao menos um critério (indicador, operador e valor escolhidos por você) "
                                   "ou uma ordenação.")
    if not mapping.get("territory"):
        raise ValueError("Associe o território para aplicar critérios.")
    for key, allowed in (("distance_scope", ("complete", "evaluable_references")),
                         ("eligibility_scope", ("potentially_eligible", "confirmed_eligible"))):
        if options.get(key) not in (None, *allowed):
            raise ValueError("Alcance não reconhecido: " + key + ".")
    nodes, leaves, root = parse_tree(tree, options) if tree is not None else ({}, [], None)
    if ranking:
        _numeric_spec(ranking, "Ordenação")
        _direction(ranking)
        if ranking.get("top_n") is not None:
            _top_n(ranking)
    if bands:
        _numeric_spec(bands, "Faixas")
        band_edges(bands.get("limits"))
    need = needs(options)
    if need["count"] and not mapping.get("count"):
        raise ValueError("Critérios de densidade e quantidade usam a coluna de quantitativos; associe-a.")
    if need["count"] and not options.get("count_unit"):
        raise ChoiceRequired("Escolha a unidade de contagem dos quantitativos usados nos critérios.")
    if need["population"] and not mapping.get("population"):
        raise ValueError("Critérios de densidade e de população exigem uma coluna de população associada.")
    period = analysis_period(frame, mapping, options)
    spatial = nearest_inputs(frame, mapping, {**options, "period_filter": period} if period else options) if need["spatial"] else None
    if spatial is not None:
        targets, catalog = spatial["targets"], spatial["references"]["catalogo"]
    else:
        catalog = {item["id"]: item for item in territory_catalog(frame, mapping, options)}
        universe = scoped(frame, mapping, {**options, "period_filter": period} if period else options)
        targets = sorted(set(row_ids(universe, mapping).tolist()), key=lambda key: (catalog[key]["name"], key))
    categories = {}
    for own in leaves:
        leaf = nodes[own]
        if leaf["atributo"] in ("densidade", "quantidade", "populacao"):
            categories[own] = _category(frame, mapping, options, period, leaf["parametros"].get("categoria"))
        elif leaf["atributo"] == "territorio":
            unknown = [v for v in leaf["membros"] if v not in catalog]
            if unknown:
                raise ValueError("Territórios do critério inexistentes na base: " + ", ".join(unknown[:8]))
    if any(nodes[own]["atributo"] == "densidade" for own in leaves) and not options.get("population_denominator_confirmed"):
        from semantic_bridge import premise_reason  # importação tardia: a ponte usa este módulo
        raise ChoiceRequired(premise_reason(options, "population_denominator_confirmed"))
    return {"period": period, "nodes": nodes, "leaves": leaves, "root": root, "targets": targets, "catalog": catalog,
            "categories": categories, "spatial": need["spatial"]}


def distance_values(structured, options):
    """Distância por alvo a partir de CAP-ESP-02: campo completo, ou entre avaliáveis só com aceitação explícita.

    Candidatos de elegibilidade desconhecida (critério de referência não avaliável) não são tratados como
    inelegíveis: sem aceitação do alcance restrito às referências confirmadas, a distância fica não avaliável.
    """
    refs = structured["conjunto_referencias"]
    unknown = (refs.get("avaliacao_criterio") or {}).get("NAO_AVALIAVEL") or []
    confirmed_only = options.get("eligibility_scope") == "confirmed_eligible"
    partial_ok = options.get("distance_scope") == "evaluable_references"
    invalid_refs = len(structured["referencias_nao_avaliaveis"])
    full_scope = "conjunto completo das referências de elegibilidade confirmada" if unknown else "conjunto completo de referências"
    empty = refs["n"] == 0
    values = {}
    for record in structured["cobertura_referencias"]:
        own_state, motives, causes = record["condicao_espacial"], [], []
        if own_state != "VALIDA":
            motives.append(MOTIVES[own_state])
            causes.append({"origem": "coordenada do alvo", "motivo": MOTIVES[own_state]})
        if empty:  # causas do lado das referências são registradas mesmo com o alvo inválido
            motives.append("DEPENDENCIA_NAO_AVALIAVEL")
            causes.append({"origem": "referências", "detalhe": "CONJUNTO_REFERENCIAS_VAZIO"})
        if unknown and not confirmed_only:
            motives.append("DEPENDENCIA_NAO_AVALIAVEL")
            causes.append({"origem": "elegibilidade das referências", "candidatos_elegibilidade_desconhecida": len(unknown)})
        chosen = None
        if not motives:
            full, partial = record["minimo_completo"], record["minimo_avaliaveis"]
            if full["avaliabilidade"] == "AVALIAVEL":
                chosen, scope = full, full_scope
            elif partial_ok and partial["avaliabilidade"] == "AVALIAVEL":
                chosen, scope = partial, "entre as referências avaliáveis (cobertura parcial)"
            else:
                motives.append("DEPENDENCIA_NAO_AVALIAVEL")
                causes.append({"origem": "referências", "referencias_sem_coordenadas_avaliaveis": invalid_refs})
        if chosen is None:
            values[record["unidade"]] = {"avaliavel": False, "motivos": list(dict.fromkeys(motives)), "causas": causes}
        else:
            values[record["unidade"]] = {"avaliavel": True, "valor": chosen["distancia_km"],
                                         "exato": Fraction(chosen["distancia_km"]), "referencias": chosen["referencias"],
                                         "alcance": scope}
    return values


class Evaluator:
    """Valores por território e por atributo, calculados uma vez e compartilhados por critérios e ordenações."""

    def __init__(self, frame, mapping, options, inputs):
        self.frame, self.mapping, self.options, self.inputs = frame, mapping, options, inputs
        self._measures, self._values = {}, {}
        self.nearest = compute_nearest(frame, mapping, self._nearest_options()) if inputs["spatial"] else None
        self.distances = distance_values(self.nearest["structured"], options) if self.nearest else None

    def _nearest_options(self):
        period = self.inputs["period"]
        return {**self.options, "period_filter": period} if period else self.options

    def category(self, requested):
        return _category(self.frame, self.mapping, self.options, self.inputs["period"], requested)

    def values(self, attribute, category=None):
        """{território: {avaliavel, valor, exato, motivos}} para atributos numéricos."""
        key = (attribute, category)
        if key in self._values:
            return self._values[key]
        if attribute == "distancia":
            result = self.distances
        else:
            source = (category, attribute in ("densidade", "quantidade"), attribute in ("densidade", "populacao"))
            if source not in self._measures:
                self._measures[source] = measures(self.frame, self.mapping, self.options, self.inputs["period"], *source)
            data, result = self._measures[source], {}
            for key_id in self.inputs["targets"]:
                if key_id not in data:
                    result[key_id] = {"avaliavel": False, "motivos": ["SEM_REGISTRO_OBSERVADO"]}
                    continue
                q, p = data[key_id]
                if attribute == "quantidade":
                    result[key_id] = ({"avaliavel": False, "motivos": ["DADO_AUSENTE"]} if q is None else
                                      {"avaliavel": True, "valor": q, "exato": Fraction(q)})
                elif attribute == "populacao":
                    result[key_id] = ({"avaliavel": False, "motivos": ["DADO_AUSENTE"]} if p is None else
                                      {"avaliavel": True, "valor": p, "exato": Fraction(p)})
                else:
                    motives = ([] if q is not None else ["DADO_AUSENTE"]) + (
                        ["DENOMINADOR_AUSENTE"] if p is None else ["DENOMINADOR_ZERO"] if p == 0 else [])
                    # q/p × 1.000 em fração exata; o valor em ponto flutuante é só para apresentação.
                    result[key_id] = ({"avaliavel": False, "motivos": motives} if motives else
                                      {"avaliavel": True, "valor": q / p * 1000, "exato": Fraction(q) * 1000 / Fraction(p),
                                       "quantidade": q, "populacao": p})
        self._values[key] = result
        return result


def evaluate_tree(nodes, root, leaf_states):
    """Estados de todos os nós por elemento, em pós-ordem; NAO_AVALIAVEL nunca vira NAO_ATENDE."""
    states = dict(leaf_states)

    def visit(own):
        node = nodes[own]
        if node["tipo"] == "COMPOSTO":
            states[own] = COMBINE[node["operador_logico"]]([visit(child) for child in node["operandos"]])
        return states[own]

    visit(root)
    return states


def causes_of(nodes, own, states, leaf_detail):
    """Folhas não avaliáveis ligadas à raiz só por nós não avaliáveis: as causas da indeterminação."""
    if states[own] != "NAO_AVALIAVEL":
        return []
    node = nodes[own]
    if node["tipo"] == "ATOMICO":
        return [{"no": own, "motivos": leaf_detail[own].get("motivos", [])}]
    return [cause for child in node["operandos"] for cause in causes_of(nodes, child, states, leaf_detail)]


def _leaf_results(leaf, evaluator, category, catalog, targets):
    attribute = leaf["atributo"]
    results = {}
    if attribute in NUMERIC:
        values = evaluator.values(attribute, category)
        for key in targets:
            item = values[key]
            if not item["avaliavel"]:
                results[key] = {"estado": "NAO_AVALIAVEL", "motivos": item["motivos"],
                                **({"causas": item["causas"]} if item.get("causas") else {})}
                continue
            meets = _compare(leaf["operador"], item["exato"], leaf["limiar"])
            results[key] = {"estado": "ATENDE" if meets else "NAO_ATENDE", "valor": item["valor"],
                            **({"referencias": item["referencias"], "alcance": item["alcance"]} if attribute == "distancia" else {})}
        return results
    for key in targets:
        if attribute == "territorio":
            inside = key in leaf["membros"]
        else:
            state = catalog[key].get("state")
            if not state:
                results[key] = {"estado": "NAO_AVALIAVEL", "motivos": ["SIGNIFICADO_NAO_ESTABELECIDO"]}
                continue
            inside = state in leaf["membros"]
        meets = inside if leaf["operador"] in ("in", "=") else not inside
        results[key] = {"estado": "ATENDE" if meets else "NAO_ATENDE"}
    return results


def evaluate(frame, mapping, options, inputs, evaluator, tree_nodes=None, tree_root=None, tree_leaves=None):
    """Avaliação completa por elemento: folhas (com valores e causas), nós compostos e estado da raiz."""
    nodes = inputs["nodes"] if tree_nodes is None else tree_nodes
    root = inputs["root"] if tree_root is None else tree_root
    leaves = inputs["leaves"] if tree_leaves is None else tree_leaves
    targets, catalog = inputs["targets"], inputs["catalog"]
    per_leaf = {own: _leaf_results(nodes[own], evaluator, evaluator.category(nodes[own]["parametros"].get("categoria"))
                                   if nodes[own]["atributo"] in ("densidade", "quantidade", "populacao") else None,
                                   catalog, targets) for own in leaves}
    evaluations = []
    for key in targets:
        detail = {own: per_leaf[own][key] for own in leaves}
        states = evaluate_tree(nodes, root, {own: detail[own]["estado"] for own in leaves})
        record = {"elemento": key, "estado": states[root],
                  "nos": {own: ({**detail[own]} if own in detail else {"estado": states[own]}) for own in nodes}}
        for own in nodes:
            if own not in detail and states[own] == "NAO_AVALIAVEL":
                record["nos"][own]["motivos"] = ["DEPENDENCIA_NAO_AVALIAVEL"]
        if states[root] == "NAO_AVALIAVEL":
            record["causas"] = causes_of(nodes, root, states, detail)
        evaluations.append(record)
    return evaluations


def outcome_of(counts, evaluations, limitations):
    """RQ-CAP-08, depois da avaliação. Sem avaliáveis: BLQ-DEP quando o conjunto de referências vazio está entre as
    causas de todos os elementos (como na Etapa 1); dados ou coordenadas insuficientes, BLQ-DAD."""
    if not counts["ATENDE"] + counts["NAO_ATENDE"]:
        def empty_set(item):
            return any(c.get("detalhe") == "CONJUNTO_REFERENCIAS_VAZIO"
                       for cause in item.get("causas", []) for c in item["nos"][cause["no"]].get("causas", []))
        return "BLQ-DEP" if evaluations and all(empty_set(item) for item in evaluations) else "BLQ-DAD"
    if not counts["ATENDE"]:
        return "RES-VAZ"
    return "RES-LIM" if limitations else "RES-VAL"


RANKABLE = ("densidade", "quantidade", "populacao", "distancia")


def _numeric_spec(spec, label, allow_set=True):
    if not isinstance(spec, dict):
        raise ValueError(label + " inválida.")
    attribute = spec.get("attribute")
    if attribute not in RANKABLE:
        raise ValueError(label + ": use densidade, quantidade, população ou distância.")
    category = spec.get("category")
    if category is not None and (attribute not in ("densidade", "quantidade") or not isinstance(category, str) or not category.strip()):
        raise ValueError("Categoria só pode ser escolhida para densidade e quantidade.")
    member_set = spec.get("set")
    if member_set not in (None, "atende", "universo") or (member_set and not allow_set):
        raise ValueError(label + ": conjunto não reconhecido.")
    return attribute, (category or "").strip() or None, member_set


def ranking_of(values, members, catalog, direction):
    """CAP-SUB-02: valores exatos, empates com posição compartilhada (1, 2, 2, 4), não avaliáveis à parte."""
    evaluable = [key for key in members if values[key]["avaliavel"]]
    sign = -1 if direction == "desc" else 1
    ordered = sorted(evaluable, key=lambda key: (sign * values[key]["exato"], catalog[key]["name"], key))
    positions, previous, rank = {}, None, 0
    for index, key in enumerate(ordered, start=1):
        if previous is None or values[key]["exato"] != previous:
            rank = index
        positions[key], previous = rank, values[key]["exato"]
    return ordered, positions, [key for key in members if not values[key]["avaliavel"]]


def select_top(ordered, positions, n, exact):
    """CAP-SUB-03: N primeiras e todas as empatadas com a da posição N; N exato com empate vira pendência."""
    selected = [key for key in ordered if positions[key] <= n]
    if len(selected) > n and exact:
        return None, {"tipo": "EMPATE_NO_CORTE", "n_solicitado": n, "n_efetivo": len(selected),
                      "pergunta": f"Há empate na posição de corte: os {n} primeiros incluem {len(selected)} territórios. "
                                  "Não há regra de desempate autorizada; deseja incluir todos os empatados ou mudar o critério?"}
    return selected, None


def band_edges(limits):
    if not isinstance(limits, list) or not 2 <= len(limits) <= 21:
        raise ValueError("Informe de 2 a 21 limites para as faixas; nenhum intervalo é criado pelo sistema.")
    numbers_ = [decimal_value(value, "limite da faixa") for value in limits]
    if any(b <= a for a, b in zip(numbers_, numbers_[1:])):
        raise ValueError("Os limites das faixas devem ser crescentes e distintos.")
    return numbers_


def bands_of(values, members, limits):
    """Intervalos [a, b) e o último fechado [a, b] (CAP-DIS-03); fora de todos e não avaliáveis à parte."""
    edges = [Fraction(number) for number in limits]
    labels = [_number_text(a) + " a <" + _number_text(b) for a, b in zip(limits[:-2], limits[1:-1])]
    labels.append(_number_text(limits[-2]) + " a " + _number_text(limits[-1]))
    membership, outside, not_evaluable = {}, [], []
    for key in members:
        item = values[key]
        if not item["avaliavel"]:
            not_evaluable.append(key)
            continue
        value = item["exato"]
        index = next((i for i in range(len(edges) - 1)
                      if edges[i] <= value and (value < edges[i + 1] or (i == len(edges) - 2 and value == edges[-1]))), None)
        if index is None:
            outside.append(key)
        else:
            membership[key] = index
    counts = [sum(index == i for index in membership.values()) for i in range(len(labels))]
    return labels, membership, counts, outside, not_evaluable


def _membership(evaluations, selection):
    """Estado de cada elemento no conjunto resultante: DENTRO, FORA ou NAO_AVALIAVEL (nunca presumido FORA)."""
    states = {}
    for item in evaluations:
        state = item["estado"]
        if state == "NAO_ATENDE":
            states[item["elemento"]] = "FORA"
        elif state == "NAO_AVALIAVEL":
            states[item["elemento"]] = "NAO_AVALIAVEL"
        elif selection is None:
            states[item["elemento"]] = "DENTRO"
        else:
            states[item["elemento"]] = selection.get(item["elemento"], "FORA")
    return states


def _selection_states(definition, members, evaluator, catalog):
    """Pertença à seleção por posição de uma definição: DENTRO, FORA ou NAO_AVALIAVEL (valor de ordenação)."""
    ranking = definition.get("ranking") if isinstance(definition, dict) else None
    if not ranking or ranking.get("top_n") is None:
        return None, None
    attribute, category, _ = _numeric_spec(ranking, "Ordenação")
    values = evaluator.values(attribute, evaluator.category(category) if attribute in ("densidade", "quantidade") else None)
    ordered, positions, not_evaluable = ranking_of(values, members, catalog, _direction(ranking))
    top, pending = select_top(ordered, positions, _top_n(ranking), bool(ranking.get("exact_n")))
    if pending:
        return None, pending
    chosen = set(top)
    return {**{key: "DENTRO" if key in chosen else "FORA" for key in ordered}, **{key: "NAO_AVALIAVEL" for key in not_evaluable}}, None


def _direction(ranking):
    """A direção decide quais territórios vêm primeiro: é sempre escolha explícita do usuário."""
    direction = ranking.get("direction")
    if direction not in ("asc", "desc"):
        raise ChoiceRequired("Escolha a direção da ordenação: do maior para o menor ou do menor para o maior.")
    return direction


def _top_n(ranking):
    n = ranking.get("top_n")
    if isinstance(n, bool) or not isinstance(n, int) or not 1 <= n <= 10000:
        raise ValueError("N deve ser um inteiro entre 1 e 10.000.")
    _direction(ranking)
    return n


def compute_criteria(frame, mapping, options):
    """Resultado completo: tabela por território e conteúdo estruturado de CAP-SUB-01/02/03 e faixas."""
    inputs = criteria_inputs(frame, mapping, options)
    evaluator = Evaluator(frame, mapping, options, inputs)
    nodes, leaves, root = inputs["nodes"], inputs["leaves"], inputs["root"]
    targets, catalog, period = inputs["targets"], inputs["catalog"], inputs["period"]
    evaluations = evaluate(frame, mapping, options, inputs, evaluator) if root else []
    by_id = {item["elemento"]: item for item in evaluations}
    counts = {state: sum(item["estado"] == state for item in evaluations) for state in ("ATENDE", "NAO_ATENDE", "NAO_AVALIAVEL")}
    limitations, notes, pendencies = [], [], []
    label = {key: catalog[key]["label"] for key in targets}

    # Ordenação, seleção por posição e faixas sobre o conjunto resultante (ATENDE) ou o universo.
    def members_for(spec):
        chosen = spec.get("set") or ("atende" if root else "universo")
        return chosen, ([key for key in targets if by_id[key]["estado"] == "ATENDE"] if chosen == "atende" and root else list(targets))

    ranking, selection, bands = None, None, None
    spec = options.get("ranking")
    if spec:
        attribute, category, _ = _numeric_spec(spec, "Ordenação")
        direction = _direction(spec)
        used_category = evaluator.category(category) if attribute in ("densidade", "quantidade") else None
        values = evaluator.values(attribute, used_category)
        chosen, members = members_for(spec)
        ordered, positions, not_evaluable = ranking_of(values, members, catalog, direction)
        ranking = {"atributo": attribute, "direcao": "decrescente" if direction == "desc" else "crescente",
                   "categoria": used_category, "conjunto": chosen, "n_membros": len(members),
                   "posicoes": [{"id": key, "territorio": label[key], "posicao": positions[key], "valor": values[key]["valor"],
                                 **({"alcance": values[key]["alcance"]} if attribute == "distancia" else {})} for key in ordered],
                   "nao_avaliaveis": [{"id": key, "territorio": label[key], "motivos": values[key]["motivos"]} for key in not_evaluable],
                   "territorios_empatados": sum(n for n in Counter(positions.values()).values() if n > 1)}
        if spec.get("top_n") is not None:
            n = _top_n(spec)
            top, pending = select_top(ordered, positions, n, bool(spec.get("exact_n")))
            selection = {"n_solicitado": n, "exato": bool(spec.get("exact_n")),
                         "membros": None if top is None else [{"id": key, "territorio": label[key], "posicao": positions[key]} for key in top],
                         "nao_avaliaveis_nao_selecionados": [{"id": key, "territorio": label[key]} for key in not_evaluable]}
            if pending:
                pendencies.append(pending)
            elif len(top) > n:
                selection["n_efetivo"] = len(top)
                limitations.append({"tipo": "EMPATE_NO_CORTE", "categoria": "ANALITICA",
                                    "dados_estruturados": {"n_solicitado": n, "n_efetivo": len(top)}})
            else:
                selection["n_efetivo"] = len(top)
    spec = options.get("bands")
    if spec:
        attribute, category, _ = _numeric_spec(spec, "Faixas")
        limits = band_edges(spec.get("limits"))
        used_category = evaluator.category(category) if attribute in ("densidade", "quantidade") else None
        values = evaluator.values(attribute, used_category)
        chosen, members = members_for(spec)
        labels, membership, band_counts, outside, not_evaluable = bands_of(values, members, limits)
        bands = {"atributo": attribute, "categoria": used_category, "conjunto": chosen,
                 "capacidade": "CAP-ESP-03" if attribute == "distancia" else "CAP-DIS-03",
                 "convencao": "[a, b); o último intervalo inclui o limite superior", "limites": [format(v, "f") for v in limits],
                 "origem_limites": "escolha do usuário",
                 "faixas": [{"faixa": text, "n": n} for text, n in zip(labels, band_counts)],
                 "pertenca": {key: labels[index] for key, index in membership.items()},
                 "fora_de_todas": [{"id": key, "territorio": label[key]} for key in outside],
                 "nao_avaliaveis": [{"id": key, "territorio": label[key], "motivos": values[key]["motivos"]} for key in not_evaluable]}

    comparison = None
    spec = options.get("comparison")
    if spec:
        comparison = _compare_sets(spec, options, inputs, evaluator, evaluations, catalog, frame, mapping)

    # Limitações analíticas (RQ-RES-06) e notas.
    if root and counts["NAO_AVALIAVEL"]:
        reasons = {}
        for item in evaluations:
            for cause in item.get("causas", []):
                for motive in cause["motivos"]:
                    reasons[motive] = reasons.get(motive, 0) + 1
        limitations.append({"tipo": "UNIDADES_NAO_AVALIAVEIS", "categoria": "ANALITICA", "elementos_afetados": counts["NAO_AVALIAVEL"],
                            "dados_estruturados": reasons})
    references = None
    if evaluator.nearest is not None:
        references = _references_summary(evaluator, options)
        used = [v for v in evaluator.distances.values() if v["avaliavel"]]
        if used:
            limitations.append({"tipo": "DISTANCIA_GEODESICA_DIRETA", "categoria": "ANALITICA", "texto": TPL_11})
            notes.append(TPL_11)
        partial = sum(v["alcance"].startswith("entre as referências avaliáveis") for v in used)
        if partial or (references["candidatos_elegibilidade_desconhecida"] and options.get("eligibility_scope") == "confirmed_eligible"):
            limitations.append({"tipo": "COBERTURA_PARCIAL", "categoria": "ANALITICA",
                                "dados_estruturados": {"alvos_entre_avaliaveis": partial,
                                                       "referencias_nao_avaliaveis": len(references["referencias_nao_avaliaveis"]),
                                                       "candidatos_elegibilidade_desconhecida": len(references["candidatos_elegibilidade_desconhecida"])}})
        notes.append("Distância: " + references["alcance_afirmacao"] + ".")
        notes.extend(n for n in evaluator.nearest["notes"] if n.startswith(("Referências:", "Candidatos não avaliáveis",
                                                                              "Coordenadas de ", "Camada geográfica")))
    outcome = outcome_of(counts, evaluations, limitations) if root else ("RES-LIM" if limitations else "RES-VAL")
    if root:
        notes.insert(0, "Critérios definidos pelo usuário: " + describe(nodes, root) + ". Os valores são escolhas do usuário e "
                     "não constituem critério legal, sanitário ou científico universal.")
        notes.insert(1, "Três estados por território e por condição: NAO_AVALIAVEL nunca é tratado como NAO_ATENDE; E, OU e NÃO "
                     "seguem CAP-SUB-01 e o resultado não depende da ordem das condições.")
        implicit = [nodes[own]["no"] + ": " + nodes[own]["parametros"]["contexto"] for own in leaves
                    if nodes[own]["atributo"] in NUMERIC and not nodes[own]["parametros"]["unidade_informada"]]
        if implicit:
            notes.append("Unidades: " + "; ".join(implicit) + ".")
        if counts["ATENDE"] == 0 and counts["NAO_ATENDE"]:
            notes.append("Nenhum território atende aos critérios entre os avaliáveis (resultado vazio, RES-VAZ).")
    if period:
        notes.append("Competência " + period + (". Categoria " + ", ".join(sorted({c for c in inputs["categories"].values() if c}))
                                                if any(inputs["categories"].values()) else "") + ".")
    if ranking:
        notes.append("Ordenação por " + NUMERIC[ranking["atributo"]] + " (" + ranking["direcao"] + "), sobre " +
                     ("o conjunto que atende aos critérios" if ranking["conjunto"] == "atende" else "o universo") +
                     ": valores iguais compartilham posição (1, 2, 2, 4) e não avaliáveis ficam fora da ordenação.")
    if selection and selection["membros"] is not None and selection["n_efetivo"] > selection["n_solicitado"]:
        notes.append(f"Seleção dos {selection['n_solicitado']} primeiros com empate no corte: {selection['n_efetivo']} territórios "
                     "selecionados (EMPATE_NO_CORTE).")
    if bands:
        notes.append("Faixas com limites escolhidos pelo usuário, intervalos [a, b) e o último fechado.")

    rows = _rows(targets, catalog, nodes, leaves, root, by_id, ranking, selection, bands, evaluator)
    structured = {
        "metodo": METHOD, "periodo": period, "categorias": inputs["categories"],
        "universo": {"definicao": "subconjunto selecionado" if "territory_ids" in options else "universo observado no período",
                     "n": len(targets)},
        "arvore": {"raiz": root, "nos": [_public(nodes[own]) for own in nodes]} if root else None,
        "avaliacoes": evaluations,
        "conjuntos": {"ATENDE": [key for key in targets if root and by_id[key]["estado"] == "ATENDE"],
                      "NAO_ATENDE": [key for key in targets if root and by_id[key]["estado"] == "NAO_ATENDE"],
                      "NAO_AVALIAVEL": [{"id": key, "causas": by_id[key].get("causas", [])} for key in targets
                                        if root and by_id[key]["estado"] == "NAO_AVALIAVEL"]} if root else None,
        "contagens": {**counts, "universo": len(targets)} if root else None,
        "referencias": references, "ordenacao": ranking, "selecao": selection, "faixas": bands, "comparacao": comparison,
        "pendencias": pendencies, "limitacoes": limitations, "desfecho": outcome}
    metrics = [{"label": "Territórios no universo", "value": len(targets)}]
    if root:
        metrics += [{"label": "Atendem", "value": counts["ATENDE"]}, {"label": "Não atendem", "value": counts["NAO_ATENDE"]},
                    {"label": "Não avaliáveis", "value": counts["NAO_AVALIAVEL"]}]
    if selection and selection["membros"] is not None:
        metrics.append({"label": "Selecionados", "value": len(selection["membros"])})
    evaluable = counts["ATENDE"] + counts["NAO_ATENDE"]
    evaluability = ("NAO_AVALIAVEL" if root and not evaluable else
                    "AVALIAVEL" if not limitations and not pendencies else "AVALIAVEL_COM_LIMITACOES")
    title = "Critérios combinados" if root else "Ordenação de territórios"
    if root and not evaluable:
        title += " — sem resultado analítico"
    description = ("Territórios que atendem, não atendem ou não são avaliáveis pelos critérios do usuário, com a condição "
                   "de cada critério por território." if root else "Territórios ordenados pelo atributo escolhido.")
    return {"title": title, "description": description, "rows": rows, "metrics": metrics, "notes": notes,
            "structured": _plain(structured), "evaluability": evaluability}


def describe(nodes, own):
    node = nodes[own]
    if node["tipo"] == "ATOMICO":
        return node["condicao"] + (" (" + node["parametros"]["categoria"] + ")" if node["parametros"].get("categoria") else "")
    if node["operador_logico"] == "NAO":
        return "NÃO (" + describe(nodes, node["operandos"][0]) + ")"
    joiner = " E " if node["operador_logico"] == "E" else " OU "
    return "(" + joiner.join(describe(nodes, child) for child in node["operandos"]) + ")"


def _public(node):
    return {key: value for key, value in node.items() if key not in ("limiar", "membros")}


def _references_summary(evaluator, options):
    structured = evaluator.nearest["structured"]
    refs = structured["conjunto_referencias"]
    criterion = refs.get("avaliacao_criterio")
    unknown = (criterion or {}).get("NAO_AVALIAVEL") or []
    confirmed_only = options.get("eligibility_scope") == "confirmed_eligible"
    partial_ok = options.get("distance_scope") == "evaluable_references"
    invalid = structured["referencias_nao_avaliaveis"]
    if refs["forma"] == "LISTA_EXPLICITA":
        scope = "referência mais próxima entre as " + str(refs["n"]) + " referências da lista explícita do usuário"
    elif not unknown:
        scope = "referência mais próxima entre todas as referências elegíveis (critério avaliado em todos os candidatos)"
    elif confirmed_only:
        scope = ("referência mais próxima entre as referências de elegibilidade confirmada, por aceitação explícita; " +
                 str(len(unknown)) + " candidato(s) de elegibilidade desconhecida não foram tratados como inelegíveis")
    else:
        scope = ("não afirmada: " + str(len(unknown)) + " candidato(s) de elegibilidade desconhecida; a mais próxima entre as "
                 "referências confirmadas não equivale à mais próxima entre todas as potencialmente elegíveis")
    if invalid:
        scope += ("; para alvos sem mínimo completo, entre as referências avaliáveis (cobertura parcial aceita)" if partial_ok else
                  "; " + str(len(invalid)) + " referência(s) sem coordenadas avaliáveis tornam o mínimo completo não avaliável")
    partial_only = sum(1 for r in structured["cobertura_referencias"] if r["minimo_completo"]["avaliabilidade"] != "AVALIAVEL"
                       and r["minimo_avaliaveis"]["avaliabilidade"] == "AVALIAVEL")
    return {"forma": refs["forma"], "origem": refs["origem"], "criterio": refs["criterio"], "n": refs["n"],
            "n_coordenadas_avaliaveis": refs["n_coordenadas_avaliaveis"], "membros": refs["membros"],
            "referencias_nao_avaliaveis": invalid,
            "cobertura_avaliacao_elegibilidade": None if criterion is None else {
                "candidatos": refs["universo_candidatos"]["n"], "ATENDE": criterion["ATENDE"],
                "NAO_ATENDE": criterion["NAO_ATENDE"], "NAO_AVALIAVEL": len(unknown), "completa": not unknown},
            "candidatos_elegibilidade_desconhecida": unknown,
            "cobertura_geografica_elegiveis": {"elegiveis_confirmados": refs["n"],
                                               "com_coordenadas_avaliaveis": refs["n_coordenadas_avaliaveis"],
                                               "sem_coordenadas_avaliaveis": refs["n"] - refs["n_coordenadas_avaliaveis"]},
            "alcance_afirmacao": scope,
            "alcance_aceito": {"distance_scope": options.get("distance_scope") or "complete",
                               "eligibility_scope": options.get("eligibility_scope") or "potentially_eligible"},
            "aceitacoes_disponiveis": {"cobertura_parcial": 0 if partial_ok else partial_only,
                                       "elegibilidade_confirmada": 0 if confirmed_only else len(unknown)},
            "metodo_distancia": structured["metodo"], "periodo_geometria": structured["periodo_geometria"],
            "geodesicas_calculadas": structured["geodesicas_calculadas"],
            **({"complemento_geografico": structured["complemento_geografico"]} if "complemento_geografico" in structured else {})}


def _compare_sets(spec, options, inputs, evaluator, evaluations, catalog, frame, mapping):
    """Conjunto atual × conjunto de uma definição anterior, no mesmo contexto (período, categoria, universo, referências)."""
    if not isinstance(spec, dict) or (spec.get("criteria") is None and not spec.get("ranking")):
        raise ValueError("A comparação exige a definição do conjunto anterior (critérios ou seleção por posição).")
    targets = inputs["targets"]
    if spec.get("criteria") is not None:
        nodes, leaves, root = parse_tree(spec["criteria"], options)
        previous = evaluate(frame, mapping, options, inputs, evaluator, nodes, root, leaves)
    else:
        nodes, root = {}, None
        previous = [{"elemento": key, "estado": "ATENDE"} for key in targets]
    current = evaluations or [{"elemento": key, "estado": "ATENDE"} for key in targets]

    def states(items, definition):
        ranking = definition.get("ranking") or {}
        whole = ranking.get("set") == "universo"  # seleção sobre o universo: o conjunto é a própria seleção
        members = list(targets) if whole else [item["elemento"] for item in items if item["estado"] == "ATENDE"]
        selection, pending = _selection_states(definition, members, evaluator, catalog)
        if pending:
            raise ValueError("O conjunto de uma das definições depende de decisão sobre empate no corte; resolva antes de comparar.")
        if whole and selection is not None:
            return selection
        return _membership(items, selection)

    before, after = states(previous, spec), states(current, options)
    transitions = {}
    for key in targets:
        pair = before[key] + "→" + after[key]
        transitions[pair] = transitions.get(pair, 0) + 1
    label = {key: catalog[key]["label"] for key in targets}

    def pick(condition):
        return [{"id": key, "territorio": label[key]} for key in targets if condition(before[key], after[key])]

    return {"definicao_anterior": {"descricao": describe(nodes, root) if root else "universo", "rotulo": str(spec.get("label") or "")[:120],
                                   "selecao": spec.get("ranking")},
            "contexto": "mesmo período, categoria, universo e referências da execução atual",
            "transicoes": transitions,
            "em_ambos": pick(lambda b, a: b == "DENTRO" and a == "DENTRO"),
            "somente_atual": pick(lambda b, a: b == "FORA" and a == "DENTRO"),
            "somente_anterior": pick(lambda b, a: b == "DENTRO" and a == "FORA"),
            "indeterminados": [{"id": key, "territorio": label[key], "anterior": before[key], "atual": after[key]}
                               for key in targets if "NAO_AVALIAVEL" in (before[key], after[key])
                               and not (before[key] == "FORA" and after[key] == "FORA")]}


def _state_text(detail):
    if detail["estado"] != "NAO_AVALIAVEL":
        return detail["estado"]
    return "NAO_AVALIAVEL (" + ", ".join(detail.get("motivos", [])) + ")"


def _rows(targets, catalog, nodes, leaves, root, by_id, ranking, selection, bands, evaluator):
    positions = {item["id"]: item["posicao"] for item in ranking["posicoes"]} if ranking else {}
    rank_motives = {item["id"]: item["motivos"] for item in ranking["nao_avaliaveis"]} if ranking else {}
    rank_values = {item["id"]: item["valor"] for item in ranking["posicoes"]} if ranking else {}
    chosen = {item["id"] for item in selection["membros"]} if selection and selection["membros"] is not None else None
    band_missing = {item["id"] for item in bands["nao_avaliaveis"]} if bands else set()
    band_outside = {item["id"] for item in bands["fora_de_todas"]} if bands else set()
    order = {"ATENDE": 0, "NAO_ATENDE": 1, "NAO_AVALIAVEL": 2}

    def sort_key(key):
        if ranking:
            group = 0 if key in positions else 1 if key in rank_motives else 2
            return (group, positions.get(key, 0), catalog[key]["name"], key)
        return (order[by_id[key]["estado"]] if root else 0, catalog[key]["name"], key)

    rows = []
    for key in sorted(targets, key=sort_key):
        row = {}
        if ranking:
            row["Posição"] = positions.get(key)
        row["Território"] = catalog[key]["name"]
        row["Código"] = catalog[key]["code"] or None
        if root:
            item = by_id[key]
            row["Resultado"] = item["estado"]
            for own in leaves:
                leaf, detail = nodes[own], item["nos"][own]
                if leaf["atributo"] in NUMERIC:
                    row[own + " · " + NUMERIC[leaf["atributo"]] + " (" + leaf["unidade_valor"] + ")"] = detail.get("valor")
                if leaf["atributo"] == "distancia":
                    refs = detail.get("referencias") or []
                    row[own + " · referência mais próxima"] = "; ".join(catalog[r]["name"] for r in refs) or None
                    row[own + " · alcance"] = detail.get("alcance")
                row[own + " · " + leaf["condicao"]] = _state_text(detail)
            row["Motivos"] = ("DEPENDENCIA_NAO_AVALIAVEL ← " + "; ".join(c["no"] + ": " + ", ".join(c["motivos"]) for c in item["causas"])
                              if item["estado"] == "NAO_AVALIAVEL" else None)
        if ranking:
            row["Ordenação · " + NUMERIC[ranking["atributo"]]] = rank_values.get(key)
            if key in rank_motives:
                row["Ordenação · condição"] = "NAO_AVALIAVEL (" + ", ".join(rank_motives[key]) + ")"
            elif key in positions:
                row["Ordenação · condição"] = "AVALIAVEL"
            else:
                row["Ordenação · condição"] = "Fora do conjunto ordenado"
        if chosen is not None:
            row["Selecionado"] = "Sim" if key in chosen else "Não"
        if bands:
            row["Faixa · " + NUMERIC[bands["atributo"]]] = bands["pertenca"].get(key) or (
                "Não avaliável" if key in band_missing else "Fora das faixas" if key in band_outside else None)
        rows.append(row)
    return rows


def _plain(value):
    """Tipos JSON nativos; frações e decimais nunca aparecem crus na resposta."""
    if isinstance(value, dict):
        return {str(key): _plain(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_plain(item) for item in value]
    if isinstance(value, Fraction):
        return str(value)
    if isinstance(value, np.integer):
        return int(value)
    if isinstance(value, (float, np.floating)):
        return float(value) if np.isfinite(value) else None
    return value
