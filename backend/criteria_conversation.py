"""Comandos conversacionais dos critérios combinados (Bloco 2, Etapa 2): estrutura, nunca calcula.

Reconhece condições com operador do vocabulário de CFG-VOC e valor escrito no pedido (densidade por
mil habitantes, distância em km ou metros, população em habitantes), critérios sucessivos ("agora
considere também"), ordenação, seleção dos N primeiros e comparação com o conjunto anterior. Nenhum
valor, unidade, referência ou categoria é inventado; ambiguidade material vira pergunta. O canal do
LLM não recebe esta capacidade.
"""
import re

from exploration import normalize

# Vocabulário de operadores (CFG-VOC), expressões mais longas primeiro.
OPERATORS = [("maior ou igual a", ">="), ("menor ou igual a", "<="), ("diferente de", "!="), ("igual a", "="),
             ("no maximo", "<="), ("no minimo", ">="), ("a partir de", ">="), ("ate", "<="),
             ("abaixo de", "<"), ("menos de", "<"), ("inferior a", "<"), ("menor do que", "<"), ("menor que", "<"),
             ("acima de", ">"), ("mais de", ">"), ("superior a", ">"), ("maior do que", ">"), ("maior que", ">")]
SYMBOL = {"<": "<", "<=": "≤", ">": ">", ">=": "≥", "=": "=", "!=": "≠"}
NUMBER = r"(\d+(?:[.,]\d+)*)"
CLAUSE = re.compile(r"\b(" + "|".join(re.escape(words) for words, _ in OPERATORS) + r")\s+" + NUMBER + r"(?!\d)")
PER_CAPITA = re.compile(r"^\s*(?:\w+\s+){0,2}?(?:por|a cada|/)\s*(100 mil|100\.000|100000|10 mil|10\.000|10000|mil|1\.000|1000)\s+hab")
SCALE = {"mil": "por_1000_habitantes", "1.000": "por_1000_habitantes", "1000": "por_1000_habitantes",
         "10 mil": "por_10000_habitantes", "10.000": "por_10000_habitantes", "10000": "por_10000_habitantes",
         "100 mil": "por_100000_habitantes", "100.000": "por_100000_habitantes", "100000": "por_100000_habitantes"}
PROFESSIONS = r"(?:medic[oa]s?|profissiona(?:l|is)|enfermeir[oa]s?|dentistas?|trabalhadore?s?)"
ATTRIBUTE_WORDS = {"distancia": "distancia", "densidade": "densidade", "populacao": "populacao",
                   "quantidade": "quantidade", "quantitativo": "quantidade"}
LABEL = {"densidade": "densidade", "distancia": "distância à referência mais próxima", "populacao": "população",
         "quantidade": "quantidade"}
DESC = r"\b(?:decrescente|do maior para o menor|maior para menor|mais distantes? primeiro|maiores? primeiro|do mais distante)"
ASC = r"\b(?:crescente|do menor para o maior|menor para maior|mais proxim[oa]s? primeiro|menores? primeiro|do mais proxim[oa])"
NOT_CALCULATED = " Nada foi calculado; confira os controles e execute a análise."


def _value(text):
    """Número escrito pelo usuário; ponto seguido de três dígitos é separador de milhar ambíguo."""
    if re.fullmatch(r"\d+(?:\.\d{3})+", text) or text.count(",") > 1 or ("," in text and "." in text):
        return None
    return text.replace(",", ".")


def _clause(text, match):
    """Atributo, unidade e valor de uma condição; None com pergunta quando há ambiguidade material."""
    words, raw = match[1], match[2]
    operator = dict(OPERATORS)[words]
    value = _value(raw)
    if value is None:
        return None, "Não identifiquei o valor de “" + raw + "” com segurança: use vírgula para decimais e escreva o número sem separador de milhar."
    rest, before = text[match.end():], text[:match.start()]
    per_capita = PER_CAPITA.match(rest)
    if per_capita:
        leaf = {"attribute": "densidade", "operator": operator, "value": value, "unit": SCALE[per_capita[1]]}
        unit_text = "por " + {"1.000": "mil", "1000": "mil", "10.000": "10 mil", "10000": "10 mil",
                              "100.000": "100 mil", "100000": "100 mil"}.get(per_capita[1], per_capita[1]) + " habitantes"
    elif re.match(r"\s*(?:km|quilometros?)\b", rest):
        leaf = {"attribute": "distancia", "operator": operator, "value": value, "unit": "km"}
        unit_text = "km"
    elif re.match(r"\s*(?:m|metros?)\b", rest):
        leaf = {"attribute": "distancia", "operator": operator, "value": value, "unit": "m"}
        unit_text = "m"
    elif re.search(r"\bdistancia\b", before):
        leaf = {"attribute": "distancia", "operator": operator, "value": value}
        unit_text = "km (único contexto da distância)"
    elif re.match(r"\s*mil\s+habitantes\b", rest) or (re.search(r"\bpopulacao\b", before) and re.match(r"\s*mil\b", rest)):
        if "." in value:
            return None, "Escreva a população em habitantes, sem decimais em milhares (por exemplo, 20000)."
        leaf = {"attribute": "populacao", "operator": operator, "value": str(int(value) * 1000), "unit": "habitantes"}
        unit_text = "habitantes"
    elif re.match(r"\s*habitantes\b", rest) or re.search(r"\bpopulacao\b", before):
        leaf = {"attribute": "populacao", "operator": operator, "value": value, "unit": "habitantes"}
        unit_text = "habitantes"
    elif re.search(r"\bdensidade\b", before):
        leaf = {"attribute": "densidade", "operator": operator, "value": value}
        unit_text = "por mil habitantes (único contexto da densidade)"
    elif re.search(r"\b(?:quantidade|quantitativo)\b", before):
        leaf = {"attribute": "quantidade", "operator": operator, "value": value}
        unit_text = "na unidade de contagem da base"
    elif re.match(r"\s*" + PROFESSIONS + r"\b", rest):
        return None, ("“" + words + " " + raw + "” pode indicar a quantidade de profissionais ou a densidade por 1.000 "
                      "habitantes. Diga, por exemplo, “menos de " + raw + " médicos por mil habitantes” ou "
                      "“quantidade de médicos menor que " + raw + "”.")
    else:
        return None, ""  # sem indicador identificável: a mensagem pode pertencer a outro canal
    phrase = words.replace("ate", "até").replace("no maximo", "no máximo").replace("no minimo", "no mínimo")
    described = (LABEL[leaf["attribute"]] + " " + SYMBOL[operator] + " " + leaf["value"].replace(".", ",") +
                 (" " + unit_text if unit_text else "") + " (“" + phrase + "” → " + SYMBOL[operator] + ")")
    return (leaf, described), None


def criteria_command(message, options):
    """Proposta estruturada para a operação de critérios, pergunta, ou None (outros canais)."""
    text = normalize(message).rstrip(".?!")
    in_criteria = options.get("exploration_operation") == "criteria" or bool(options.get("criteria"))
    pending = options.get("criteria_pending_ranking")
    # Comparação com o conjunto anterior (o navegador resolve qual é o resultado anterior compatível).
    if in_criteria and re.search(r"\b(?:compare|comparar|comparacao|compara)\b", text) and re.search(r"\banterior\b", text):
        return {"handled": True, "operation": "criteria", "criteria_patch": {"compare": "previous"}, "executed": False,
                "reply": "Vou comparar o conjunto atual com o do resultado anterior compatível (mesma base, competência, "
                         "categoria, universo e referências). Territórios não avaliáveis em algum dos dois ficam à parte."
                         + NOT_CALCULATED}
    # N primeiros (com ou sem ordenação implícita).
    top = re.search(r"\b(?:os|as)?\s*(\d+)\s+(?:primeir[oa]s|mais distantes|mais proxim[oa]s)\b|\btop\s*(\d+)\b", text)
    if in_criteria and top:
        n = int(top[1] or top[2])
        if not 1 <= n <= 10000:
            return {"handled": True, "clarification": "Escolha N entre 1 e 10.000."}
        patch = {"top_n": n, "exact_n": bool(re.search(r"\bexatamente\b", text))}
        if "mais distantes" in text:
            patch["ranking"] = {"attribute": "distancia", "direction": "desc"}
        elif re.search(r"mais proxim[oa]s", text):
            patch["ranking"] = {"attribute": "distancia", "direction": "asc"}
        elif not (options.get("ranking") or {}).get("attribute"):
            return {"handled": True, "clarification": "Para mostrar os " + str(n) + " primeiros, diga por qual atributo ordenar "
                                                      "(densidade, distância, população ou quantidade) e em que direção."}
        return {"handled": True, "operation": "criteria", "criteria_patch": patch, "executed": False,
                "reply": "Seleção dos " + str(n) + " primeiros da ordenação" + (" exigindo exatamente " + str(n) if patch["exact_n"] else
                         "; empatados na posição de corte também entram (EMPATE_NO_CORTE)") + "." + NOT_CALCULATED}
    # Ordenação: a direção decide quais são os primeiros; sem ela, pergunta.
    ranking = re.search(r"\b(?:ordene|ordenar|ordenados?|ordenacao|classifique|classificar|ranking|ordem)\b", text)
    attribute = next((ATTRIBUTE_WORDS[w] for w in re.findall(r"\b(distancia|densidade|populacao|quantidade|quantitativo)\b", text)), None)
    desc, asc = re.search(DESC, text), re.search(ASC, text)
    if (in_criteria and ranking and attribute) or (pending and (desc or asc) and not CLAUSE.search(text)):
        chosen = attribute or pending
        if not (desc or asc) or (desc and asc):
            return {"handled": True, "criteria_pending_ranking": chosen,
                    "clarification": "Ordenar pela " + LABEL[chosen] + " do maior para o menor (decrescente) ou do menor para o "
                                     "maior (crescente)? A direção define quais territórios aparecem primeiro."}
        direction = "desc" if desc else "asc"
        return {"handled": True, "operation": "criteria", "executed": False,
                "criteria_patch": {"ranking": {"attribute": chosen, "direction": direction}},
                "reply": "Ordenação por " + LABEL[chosen] + " (" + ("decrescente" if direction == "desc" else "crescente") +
                         "), sobre os territórios que atendem aos critérios; empates compartilham posição e não avaliáveis "
                         "ficam à parte." + NOT_CALCULATED}
    # Condições com operador e valor explícitos.
    clauses = list(CLAUSE.finditer(text))
    if not clauses:
        return None
    if len(clauses) > 1:
        return {"handled": True, "clarification": "Envie uma condição por mensagem (por exemplo, a densidade e, depois, "
                                                  "“agora considere também distância superior a 150 km”), para que cada uma seja conferida."}
    parsed, question = _clause(text, clauses[0])
    if question == "":
        if not in_criteria and not re.search(r"\b(?:municipios?|territorios?) (?:com|cuja|cujo|que)\b", text):
            return None  # ex.: "de 2014 até 2024" em um pedido de evolução temporal
        return {"handled": True, "clarification": "Não identifiquei o indicador da condição: densidade (por mil habitantes), "
                                                  "distância (km), população (habitantes) ou quantidade?"}
    if question:
        return {"handled": True, "clarification": question}
    leaf, described = parsed
    successive = re.search(r"\b(?:agora|tambem|alem disso|adicionalmente)\b", text)
    alternative = re.match(r"\s*ou\b", text) or re.search(r"\bou (?:entao|com|que)\b", text)
    mode = "or" if alternative else "and" if successive else "replace"
    if mode != "replace" and not options.get("criteria"):
        mode = "replace"
    reply = ("Condição acrescentada com " + ("OU" if mode == "or" else "E") + " às anteriores: " if mode != "replace" else
             "Critério estruturado a partir do pedido: ") + described + ". O valor é escolha sua, sem caráter normativo; " \
            "categoria, competência e universo seguem os controles da análise."
    if leaf["attribute"] == "distancia":
        reply += (" A distância é medida até a referência mais próxima entre as referências que você definir "
                  "(lista ou critério); nenhuma referência foi escolhida pelo sistema.")
    return {"handled": True, "operation": "criteria", "criteria_patch": {"mode": mode, "leaf": leaf}, "executed": False,
            "reply": reply + NOT_CALCULATED}
