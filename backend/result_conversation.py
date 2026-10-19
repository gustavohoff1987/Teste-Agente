"""Leitura de resultados já calculados; nenhum cálculo ou texto substantivo do LLM.

O pequeno compositor só copia caminhos de resultados registrados e formas PT.
Relações são as do motor. Não há inferência por comparação de valores pelo chat.
"""
import json
import re
import unicodedata
from decimal import Decimal, ROUND_HALF_UP, localcontext

from document_catalog import materialize, explanation, verify_documentation

SUPPORTED = frozenset(("density", "counts", "comparisons"))


def norm(text):
    return "".join(c for c in unicodedata.normalize("NFKD", str(text).casefold())
                   if not unicodedata.combining(c))


def display(value, digits=2):
    if value is None:
        return "Não avaliável"
    if isinstance(value, (list, dict)):
        return json.dumps(value, ensure_ascii=False, allow_nan=False)
    if isinstance(value, float):
        with localcontext() as context:
            context.prec = 400
            original = Decimal(str(value))
            while original and original.quantize(Decimal(1).scaleb(-digits), rounding=ROUND_HALF_UP) == 0:
                digits += 1
            return format(original.quantize(Decimal(1).scaleb(-digits), rounding=ROUND_HALF_UP), "f").replace(".", ",")
    return str(value)


def resolve(value, path):
    for key in path:
        value = value[key]
    return value


TABLES = ("rows", "detail_rows")  # tabelas do resultado; detail_rows só na frase-resumo (result_summary.py)
ROOTS = ("title", "rows", "notes", "metrics", "metadata", "total_rows", "detail_rows")


def value_text(result, path):
    value = resolve(result, path)
    if not isinstance(value, float) or path[0] not in TABLES:
        return display(value)
    column = path[-1]
    if column in ("Quantidade", "População") or (column in ("Valor A", "Valor B", "Diferença A − B") and
                                               result["metadata"].get("indicator") == "quantity"):
        return display(int(value)) if value.is_integer() else display(value)
    columns = ("Valor A", "Valor B") if column in ("Valor A", "Valor B") else (column,)
    peers = {r.get(key) for r in result[path[0]] for key in columns if isinstance(r.get(key), (int, float))}
    digits = 2
    while digits < 18 and any(other != value and display(float(other), digits) == display(value, digits) for other in peers):
        digits += 1
    return display(value, digits)


def relation_text(row):
    # O motor emite IGUALDADE (CAP-CMP-01, DA-13); "IGUAL" fica aceito por compatibilidade.
    relation = {"MAIOR": "maior que", "MENOR": "menor que", "IGUALDADE": "igual ao",
                "IGUAL": "igual ao"}.get(row.get("Relação A/B"))
    if not relation or row.get("Condição") != "Comparável":
        return None
    return "O valor de " + row["Objeto A"] + " é " + relation + " o de " + row["Objeto B"] + "." if relation != "igual ao" else (
        "O valor de " + row["Objeto A"] + " é igual ao de " + row["Objeto B"] + ".")


def segment_type(path):
    return "LIMITACAO" if path[0] == "notes" else "PARAMETRO" if path[0] == "metadata" else "VALOR"


def verify_segment(segment, result):
    """Um fragmento: cópia literal de um caminho do resultado (ou relação do motor) ou forma documental."""
    try:
        if segment["type"] == "EXPLICACAO_METODOLOGICA":
            return (segment["function"] == "METODOLOGICO_OPERACIONAL" and
                    set(segment) == {"type", "function", "text", "documentation"} and
                    bool(verify_documentation(segment["text"], [segment["documentation"]])))
        if set(segment) != {"type", "function", "text", "path", "result_id"}:
            return False
        if segment["result_id"] != result["result_id"]:
            return False
        path = segment["path"]
        if not path or path[0] not in ROOTS:
            return False
        value = resolve(result, path)
        if segment["type"] == "RELACAO":
            return (len(path) == 2 and path[0] == "rows" and segment["function"] == "AFIRMACAO_ANALITICA" and
                    segment["text"] is not None and segment["text"] == relation_text(value))
        if segment["text"] != value_text(result, path):
            return False
        return segment["type"] == segment_type(path) and segment["function"] == "AFIRMACAO_ANALITICA"
    except (KeyError, IndexError, TypeError, ValueError):
        return False


def verify_segments(segments, result):
    """Domínio fechado: cada fragmento é cópia literal ou forma documental materializada; todas as notas presentes."""
    try:
        if not all(verify_segment(segment, result) for segment in segments):
            return False
        paths = [s.get("path") for s in segments]
        return all(["notes", i] in paths for i in range(len(result.get("notes", []))))
    except (KeyError, IndexError, TypeError, ValueError):
        return False


def answer_result(message, action, record, capture):
    if record is None:
        return {"reply": "Ainda não há resultado apresentado com referência verificável nesta sessão. Qual análise deseja preparar?",
                "result_status": "AUSENTE", "dialogue_action": action}
    result, original = record["result"], record["context"]
    if original["source"] != capture["context"]["source"]:
        return {"reply": "O resultado apresentado pertence a outra base. Retome a base de origem para conversar sobre ele.",
                "result_status": "OUTRA_BASE", "dialogue_action": action}
    if result["metadata"].get("validity") != "VALIDO":
        return {"reply": "O resultado está invalidado. Revise a preparação e execute novamente.",
                "result_status": "INVALIDADO", "dialogue_action": action}
    op = result["metadata"]["operation"]
    reference = {"result_id": result["result_id"], "execution_key": result["metadata"]["execution_key"],
                 "revision": capture["revision"], "origin": "BACKEND_VERIFIED_RESULT",
                 "same_preparation": original["signature"] == capture["context"]["signature"] and
                                     capture["context"].get("operation") in (None, op)}
    if op not in SUPPORTED:
        form = materialize("DOC:CFG-DOC.comportamento", form="insuficiencia", evidence="DOCUMENTACAO_INSUFICIENTE")
        return {"reply": form["text"], "documentation": [form], "result_reference": reference,
                "result_status": "LEITURA_CONVERSACIONAL_NAO_IMPLEMENTADA", "dialogue_action": action}

    segments = []
    def copy(path):
        segment = {"type": "LIMITACAO" if path[0] == "notes" else "PARAMETRO" if path[0] == "metadata" else "VALOR",
                   "function": "AFIRMACAO_ANALITICA", "path": path, "result_id": result["result_id"],
                   "text": value_text(result, path)}
        segments.append(segment)
        return segment["text"]
    def document(form):
        segments.append({"type": "EXPLICACAO_METODOLOGICA", "function": "METODOLOGICO_OPERACIONAL",
                         "text": form["text"], "documentation": form})
        return form["text"]

    lines = ["Resultado apresentado: " + copy(["title"])]
    if not reference["same_preparation"]:
        lines.append("Recorte do resultado diferente da preparação atual.")
    for key, label in (("periods", "Períodos"), ("categories", "Categorias"), ("indicator", "Indicador")):
        if key in result["metadata"]:
            lines.append(label + ": " + copy(["metadata", key]))
    for i in range(len(result.get("metrics", []))):
        lines.append(copy(["metrics", i, "label"]) + ": " + copy(["metrics", i, "value"]))

    # Menção explícita restringe a apresentação, nunca os cálculos ou as limitações.
    text = norm(message)
    members = result["metadata"].get("universe", {}).get("members", [])
    named = [m for m in members if re.search(r"(?<!\w)" + re.escape(norm(m["name"])) + r"(?!\w)", text)]
    labels = {m["label"] for m in named}
    rows = [(i, row) for i, row in enumerate(result["rows"])
            if not labels or any(row.get(key) in labels for key in ("Território", "Objeto A", "Objeto B"))]
    if len(rows) > 8:
        lines.append("Linhas do resultado: " + copy(["total_rows"]) + ". Qual território deseja examinar?")
    else:
        for i, row in rows:
            relation = relation_text(row) if op == "comparisons" else None
            if relation:
                segments.append({"type": "RELACAO", "function": "AFIRMACAO_ANALITICA", "path": ["rows", i],
                                 "result_id": result["result_id"], "text": relation})
                lines.append(relation)
            # Inclusive unidade, condição, ausência e alcance. Nenhuma coluna substantiva omitida.
            lines.append("; ".join(key + ": " + copy(["rows", i, key]) for key in row))
    for i in range(len(result.get("notes", []))):
        lines.append(copy(["notes", i]))

    comparative = bool(re.search(r"\b(?:maior|menor|diferenca|dobro|metade)\b", text))
    needs_comparison = comparative and (op != "comparisons" or
        ("densidade" in text and result["metadata"].get("indicator") != "density"))
    if needs_comparison:
        lines.append("Relação comparativa: não calculada neste resultado. Deseja preparar uma comparação?")
    if re.search(r"\b(?:por que|porque|causa|motivo)\b", text):
        lines.append(document(materialize("DOC:EXC-03")))
    if action == "explain_result" and op == "density" and not needs_comparison:
        for form in explanation("density")["documentation"]:
            lines.append(document(form))
    # A simplificação privilegia a tabela com fatos, preservando TODAS as notas e qualificadores.
    if not verify_segments(segments, result):
        raise ValueError("Composição não corresponde às âncoras locais")
    answer = {"reply": "\n\n".join(lines), "segments": segments,
            "documentation": [s["documentation"] for s in segments if "documentation" in s],
            "result_reference": reference, "result_status": "VERIFICADO", "dialogue_action": action,
            "needs_calculation": needs_comparison}
    if needs_comparison and capture["context"].get("capabilities", {}).get("comparisons") in ("available", "needs_confirmation"):
        indicator = "density" if "densidade" in text else result["metadata"].get("indicator", "quantity")
        answer["clarification"] = {"code": "CALCULO_NECESSARIO", "prompt": "Deseja preparar uma comparação?",
            "reason": "Relação solicitada ausente do resultado.", "source": "CATALOGO_LOCAL", "answered": False,
            "choices": [{"label": "Preparar comparação", "draft": "Compare esses municípios",
                         "operation": "comparisons", "indicator": indicator}]}
    return answer
