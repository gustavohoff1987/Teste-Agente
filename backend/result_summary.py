"""Frase-resumo determinística, indicadores (KPIs) e procedência do resultado (decisão D7 do responsável pelo
produto, 19/10/2026; pacote visual V1).

A frase é composta só por cópias literais do resultado, com os mesmos verificadores da conversa sobre resultados
(result_conversation.value_text, relation_text e verify_segment): cada valor é um segmento com caminho no próprio
resultado (VALOR, PARAMETRO ou RELACAO), e o texto fixo vem de modelos fechados por análise. Nada é calculado aqui:
totais, contagens, relações, classes e a taxa nacional vêm do motor (metrics, rows, detail_rows e metadata).

Regras de redação (SPEC, CFG-LEX e Parte 13):
- sem LEX-DES, LEX-NORM e LEX-CAU; LEX-CMP só nas relações do motor (relation_text);
- termos de LEX-TEN só quando o resultado traz metadata.tendencia (CAP-TEN-01); a mudança entre períodos é aumento,
  redução ou sem mudança (CAP-TMP-01);
- a taxa nacional é "referência de contexto": nunca "acima" ou "abaixo", nunca classifica nem colore os territórios;
- estados são "soma dos municípios" (possível dupla contagem) e nunca são comparados com o total do Brasil.

O resumo fica em metadata.representacao.resumo, só para a interface: não entra em llm_context nem em provider_snapshot,
e nada dele vai ao provedor de IA. Uma falha ao compô-lo nunca derruba a análise (como a representação).
"""
from __future__ import annotations

from result_conversation import relation_text, resolve, segment_type, value_text, verify_segment

VERSION = 1
DENSITY_UNIT = "por 1.000 habitantes"
MAX_KPIS = 4
LEVEL_NAMES = {"BR": "Brasil (total nacional)", "UF": "Estados (soma dos municípios)", "MUN": "Municípios"}
LEVEL_ROWS = {"BR": "Brasil (total nacional)", "UF": "Estado (soma dos municípios)", "MUN": "Município"}
FORMULAS = {
    "density": "Densidade = quantidade ÷ população × 1.000 (CAP-IND-02)",
    "aggregate": "Soma das quantidades ÷ soma das populações × 1.000 (CAP-AGR-01)",
    "temporal": "Mudança entre a competência inicial e a final (CAP-TMP-01) e tendência (CAP-TEN-01)",
    "comparisons": "Relações entre territórios do mesmo nível (CAP-CMP-01)",
    "ranking": "Ordem por densidade (CAP-SUB-02)",
    "distribution": "Classes por pontos de corte do motor (CAP-DIS-02)",
    "rotation": "Coorte inicial e permanência (CAP-ROT-01)",
    "spatial": "Distância geodésica (CAP-ESP-01)",
    "nearest": "Referência mais próxima (CAP-ESP-02)",
    "criteria": "Critérios combinados (CAP-SUB-01)",
}


class Composer:
    """Monta a frase em partes: texto fixo do modelo e segmentos copiados de caminhos do resultado."""

    def __init__(self, result: dict):
        self.result = result
        self.parts: list[dict] = []
        self.segments: list[dict] = []

    def text(self, value: str) -> "Composer":
        if value:
            self.parts.append({"texto": value})
        return self

    def value(self, *path) -> "Composer":
        path = list(path)
        segment = {"type": segment_type(path), "function": "AFIRMACAO_ANALITICA", "path": path,
                   "result_id": self.result["result_id"], "text": value_text(self.result, path)}
        self._add(segment)
        return self

    def count(self, singular: str, plural: str, *path) -> "Composer":
        """Número copiado do resultado seguido do substantivo no singular ou no plural (concordância, não cálculo)."""
        self.value(*path)
        return self.text(" " + (singular if resolve(self.result, list(path)) == 1 else plural))

    def relation(self, index: int) -> "Composer":
        text = relation_text(self.result["rows"][index])
        if text is None:
            return self
        self._add({"type": "RELACAO", "function": "AFIRMACAO_ANALITICA", "path": ["rows", index],
                   "result_id": self.result["result_id"], "text": text})
        return self

    def _add(self, segment: dict):
        self.segments.append(segment)
        self.parts.append({"texto": segment["text"], "segmento": len(self.segments) - 1, "tipo": segment["type"],
                           "caminho": segment["path"]})

    @property
    def sentence(self) -> str:
        return "".join(part["texto"] for part in self.parts)


# --------------------------------------------------------------------------------------------- acesso ao resultado
def _metric(result: dict, label: str) -> int | None:
    for index, item in enumerate(result.get("metrics") or []):
        if item.get("label") == label:
            return index
    return None


def _periods(result: dict) -> list:
    periods = (result.get("metadata") or {}).get("periods") or []
    return [] if periods == ["Período declarado"] else periods


def _single(result: dict) -> bool:
    return len(_periods(result)) == 1 and len((result.get("metadata") or {}).get("categories") or []) == 1


def _when(c: Composer, result: dict, lead: str) -> Composer:
    """"Na competência P, {lead}" ou "Nas competências de P0 a Pn, {lead}" (cópias de metadata.periods); sem
    competência, só o texto inicial com maiúscula."""
    periods = _periods(result)
    if len(periods) == 1:
        return c.text("Na competência ").value("metadata", "periods", 0).text(", " + lead)
    if len(periods) > 1:
        return c.text("Nas competências de ").value("metadata", "periods", 0).text(" a ") \
            .value("metadata", "periods", len(periods) - 1).text(", " + lead)
    return c.text(lead[:1].upper() + lead[1:])


def _unit(result: dict) -> str:
    return DENSITY_UNIT if (result.get("metadata") or {}).get("indicator") == "density" else ""


def _reference_index(result: dict) -> int | None:
    """Valor da taxa nacional na competência e categoria únicas do resultado (seleção, nunca cálculo)."""
    reference = (result.get("metadata") or {}).get("referencia_nacional") or {}
    periods = _periods(result)
    categories = (result.get("metadata") or {}).get("categories") or []
    if reference.get("estado") == "INDISPONIVEL" or len(periods) != 1 or len(categories) != 1:
        return None
    for index, item in enumerate(reference.get("valores") or []):
        if item.get("competencia") == str(periods[0]) and item.get("categoria") == categories[0] and \
                item.get("valor") is not None:
            return index
    return None


def _row_index(result: dict, **match) -> int | None:
    for index, row in enumerate(result.get("rows") or []):
        if all(row.get(key) == value for key, value in match.items()):
            return index
    return None


def _levels(result: dict) -> bool:
    return bool(((result.get("metadata") or {}).get("representacao") or {}).get("niveis"))


# --------------------------------------------------------------------------------------------- modelos por análise
def _evaluable(c: Composer, valid: int, invalid: int) -> Composer:
    c.count("registro avaliável", "registros avaliáveis", "metrics", valid, "value").text(" e ")
    return c.count("não avaliável", "não avaliáveis", "metrics", invalid, "value")


def _reference(c: Composer, result: dict):
    index = _reference_index(result)
    if index is not None:
        c.text(" Referência de contexto: taxa nacional de ").value("metadata", "referencia_nacional", "valores", index, "valor") \
            .text(" " + DENSITY_UNIT + " (Brasil, total nacional); não classifica nem colore os territórios.")
    elif ((result.get("metadata") or {}).get("referencia_nacional") or {}).get("valores"):
        c.text(" Referência de contexto: taxa nacional de cada competência no cartão do Brasil; não classifica nem colore "
               "os territórios.")


def _by_level(c: Composer, result: dict, column: str):
    """Blocos por nível, sem somar níveis: o valor do Brasil (uma competência) e os registros de cada nível."""
    pieces = 0
    for level in ("BR", "UF", "MUN"):
        valid = _metric(result, LEVEL_NAMES[level] + ": registros avaliáveis")
        invalid = _metric(result, LEVEL_NAMES[level] + ": registros não avaliáveis")
        if valid is None or invalid is None:
            continue
        c.text("; " if pieces else "").text(LEVEL_NAMES[level] + ", ")
        row = _row_index(result, **{"Nível": LEVEL_ROWS["BR"]}) if level == "BR" and _single(result) else None
        if row is not None:
            if column.startswith("Densidade"):
                c.value("rows", row, column).text(" " + DENSITY_UNIT)
            else:
                c.text("quantidade ").value("rows", row, column)
        else:
            _evaluable(c, valid, invalid)
        pieces += 1
    c.text(".")


def _density(c: Composer, result: dict):
    if _levels(result):
        _when(c, result, "densidade " + DENSITY_UNIT + " em blocos por nível, sem somar níveis: ")
        _by_level(c, result, "Densidade por 1.000")
        if _row_index(result, **{"Nível": LEVEL_ROWS["BR"]}) is not None:
            return  # o Brasil já está no próprio bloco (mesma regra da taxa nacional): sem repetir o valor
    else:
        valid, invalid = _metric(result, "Unidades avaliáveis"), _metric(result, "Não avaliáveis")
        _when(c, result, "densidade " + DENSITY_UNIT + (": " if valid is not None and invalid is not None else "."))
        if valid is not None and invalid is not None:
            _evaluable(c, valid, invalid).text(".")
    _reference(c, result)


def _counts(c: Composer, result: dict):
    if _levels(result):
        _when(c, result, "quantitativos em blocos por nível, sem somar níveis: ")
        _by_level(c, result, "Quantidade")
        return
    records = _metric(result, "Registros territoriais")
    _when(c, result, "quantitativos: ")
    if records is not None:
        c.count("registro territorial", "registros territoriais", "metrics", records, "value").text(".")
    else:
        c.count("registro", "registros", "total_rows").text(".")


def _trend_counts(c: Composer, tendencia: dict):
    """Contagens do motor por família (CAP-TEN-01); só chamada com metadata.tendencia presente."""
    if tendencia.get("bloqueio"):
        c.value("metadata", "tendencia", "bloqueio", "texto")
        return
    c.text("família do crescimento: ").value("metadata", "tendencia", "familias", "CRESCIMENTO") \
        .text("; família do declínio: ").value("metadata", "tendencia", "familias", "DECLINIO") \
        .text("; sem classificação: ").value("metadata", "tendencia", "familias", "NENHUMA") \
        .text("; não avaliável: ").value("metadata", "tendencia", "nao_avaliaveis").text(".")


def _comparisons(c: Composer, result: dict):
    comparison = (result.get("metadata") or {}).get("comparacao")
    rows = result.get("rows") or []
    unit = _unit(result)
    suffix = " " + unit if unit else ""
    pairs = [index for index, row in enumerate(rows) if row.get("Relação A/B")]
    single = bool(comparison) or len(_periods(result)) == 1
    if comparison:
        c.text("Na competência dos valores ").value("metadata", "comparacao", "competencia_valores").text(": ")
    else:
        _when(c, result, "comparação: ")
    if pairs and single and len(pairs) <= 2:
        for position, index in enumerate(pairs):
            c.text(" " if position else "")
            c.value("rows", index, "Objeto A").text(", ").value("rows", index, "Valor A").text(suffix + "; ") \
                .value("rows", index, "Objeto B").text(", ").value("rows", index, "Valor B").text(suffix + ". ")
            c.relation(index).text(" Diferença A − B: ").value("rows", index, "Diferença A − B").text(suffix + ".")
    else:
        compared = _metric(result, "Territórios comparados")
        if compared is not None:
            c.count("território comparado", "territórios comparados", "metrics", compared, "value") \
                .text("; relações na tabela, sem diferenças automáticas entre pares.")
    brazil = _row_index(result, **{"Nível": LEVEL_ROWS["BR"]})
    column = "Densidade por 1.000" if unit else "Quantidade"
    if brazil is not None and single and column in rows[brazil]:
        c.text(" Brasil (total nacional) lado a lado, sem relação: ").value("rows", brazil, column).text(suffix + ".")
    tendencia = (result.get("metadata") or {}).get("tendencia")
    if comparison and comparison.get("mudanca_e_tendencia") and tendencia:
        c.text(" Tendência (CAP-TEN-01) na janela de ").value("metadata", "comparacao", "janela", "inicio").text(" a ") \
            .value("metadata", "comparacao", "janela", "fim").text(" — ")
        _trend_counts(c, tendencia)


def _temporal(c: Composer, result: dict):
    series = _metric(result, "Séries territoriais")
    labels = ("Aumento entre os extremos", "Redução entre os extremos", "Sem mudança entre os extremos",
              "Mudança não avaliável")
    up, down, same, missing = (_metric(result, label) for label in labels)
    if None not in (series, up, down, same, missing):
        _when(c, result, "evolução temporal: ").count("série territorial", "séries territoriais", "metrics", series, "value")
        c.text("; entre a competência inicial e a final, aumento em ").value("metrics", up, "value") \
            .text(", redução em ").value("metrics", down, "value").text(", sem mudança em ").value("metrics", same, "value") \
            .text(" e mudança não avaliável em ").value("metrics", missing, "value").text(" (CAP-TMP-01).")
    tendencia = (result.get("metadata") or {}).get("tendencia")
    if tendencia:
        c.text(" Tendência (CAP-TEN-01) — ")
        _trend_counts(c, tendencia)


def _aggregate(c: Composer, result: dict):
    members = _metric(result, "Territórios agregados")
    _when(c, result, "agregação")
    if members is not None:
        c.text(" de ").count("território", "territórios", "metrics", members, "value")
    c.text(" — ").value("rows", 0, "Tipo").text(": quantidade ").value("rows", 0, "Quantidade").text(", população ") \
        .value("rows", 0, "População").text(" e densidade ").value("rows", 0, "Densidade por 1.000") \
        .text(" " + DENSITY_UNIT + ".")


def _distribution(c: Composer, result: dict):
    units, classes = _metric(result, "Unidades classificadas"), _metric(result, "Classes")
    if units is None or classes is None:
        return _generic(c, result)
    _when(c, result, "distribuição: ").count("unidade classificada", "unidades classificadas", "metrics", units, "value") \
        .text(" em ").count("classe", "classes", "metrics", classes, "value").text(" pelo indicador ") \
        .value("rows", 0, "Indicador").text(" (pontos de corte do motor, CAP-DIS-02).")


def _ranking(c: Composer, result: dict):
    ordered, invalid = _metric(result, "Territórios ordenados"), _metric(result, "Não avaliáveis")
    if ordered is None or invalid is None:
        return _generic(c, result)
    _when(c, result, "ordenação pela densidade " + DENSITY_UNIT + ": ") \
        .count("território ordenado", "territórios ordenados", "metrics", ordered, "value").text(" e ") \
        .count("não avaliável", "não avaliáveis", "metrics", invalid, "value") \
        .text("; ordem descritiva, sem julgamento normativo.")


def _rotation(c: Composer, result: dict):
    valid = _metric(result, "Coortes avaliáveis")
    invalid = _metric(result, "Coortes não avaliáveis (sem registro em um dos períodos)")
    if not result.get("rows") or valid is None or invalid is None:
        return _generic(c, result)
    c.text("Coorte de ").value("rows", 0, "Período inicial").text(" a ").value("rows", 0, "Período final").text(": ") \
        .count("coorte avaliável", "coortes avaliáveis", "metrics", valid, "value").text(" e ") \
        .count("sem registro", "sem registro", "metrics", invalid, "value") \
        .text(" em um dos períodos; permanência e rotatividade em % da coorte inicial.")


def _spatial(c: Composer, result: dict):
    c.text("Distâncias geodésicas")
    if ((result.get("metadata") or {}).get("options") or {}).get("reference_territory"):
        c.text(" até ").value("metadata", "options", "reference_territory")
    c.text(" para ").count("território", "territórios", "total_rows").text("; distância direta, sem tempo nem estrada.")


def _generic(c: Composer, result: dict):
    indexes = list(range(min(len(result.get("metrics") or []), MAX_KPIS)))
    c.value("title").text(": ")
    if not indexes:
        c.count("registro", "registros", "total_rows").text(".")
        return
    for position, index in enumerate(indexes):
        c.text("; " if position else "").value("metrics", index, "label").text(": ").value("metrics", index, "value")
    c.text(".")


MODELS = {"density": _density, "counts": _counts, "comparisons": _comparisons, "temporal": _temporal,
          "aggregate": _aggregate, "distribution": _distribution, "ranking": _ranking, "rotation": _rotation,
          "spatial": _spatial}


def _model(result: dict):
    metadata = result.get("metadata") or {}
    operation = metadata.get("operation")
    if operation == "report":
        return _density if metadata.get("indicator") == "density" else _counts
    return MODELS.get(operation, _generic)


# --------------------------------------------------------------------------------------------- KPIs e procedência
def _kpi(result: dict, label: str, path: list, kind: str, unit: str | None = None, **extra) -> dict:
    item = {"rotulo": label, "caminho": path, "valor": resolve(result, path), "texto": value_text(result, path),
            "tipo": kind, "unidade": unit}
    item.update(extra)
    return {key: value for key, value in item.items() if value is not None}


def _metric_kpis(result: dict, indexes: list[int]) -> list[dict]:
    out = []
    for index in indexes:
        item = result["metrics"][index]
        out.append(_kpi(result, str(item["label"]), ["metrics", index, "value"], "CONTAGEM", nivel=item.get("nivel")))
    return out


def kpis(result: dict) -> list[dict]:
    """Até quatro indicadores do motor (métricas, valores de linhas e a taxa nacional de contexto), só por seleção."""
    metadata = result.get("metadata") or {}
    operation = metadata.get("operation")
    metrics = result.get("metrics") or []
    out: list[dict] = []
    density = operation == "density" or (operation == "report" and metadata.get("indicator") == "density")
    if operation in ("density", "counts", "report") and _levels(result):
        column = "Densidade por 1.000" if density else "Quantidade"
        single = len(_periods(result)) == 1
        for level in ("BR", "UF", "MUN"):
            if level == "BR":
                rows = [i for i, row in enumerate(result.get("rows") or []) if row.get("Nível") == LEVEL_ROWS["BR"]]
                if rows and single:
                    out.append(_kpi(result, LEVEL_NAMES["BR"], ["rows", rows[0], column],
                                    "CONTINUO" if density else "CONTAGEM", DENSITY_UNIT if density else None, nivel="BR"))
                    continue
            valid = _metric(result, LEVEL_NAMES[level] + ": registros avaliáveis")
            out += _metric_kpis(result, [] if valid is None else [valid])
    elif operation == "counts" and (metadata.get("source") or {}).get("scope") == "national":
        rows = result.get("rows") or []
        if rows:
            last = max(range(len(rows)), key=lambda i: str(rows[i].get("Período")))
            out.append(_kpi(result, "Brasil (total nacional) em " + str(rows[last].get("Período")), ["rows", last, "Quantidade"],
                            "CONTAGEM", serie={"caminho": ["rows"], "periodo": "Período", "valor": "Quantidade"}))
        out += _metric_kpis(result, list(range(len(metrics))))
    elif operation == "aggregate" and result.get("rows"):
        out += _metric_kpis(result, list(range(len(metrics))))
        out += [_kpi(result, "Quantidade", ["rows", 0, "Quantidade"], "CONTAGEM"),
                _kpi(result, "População", ["rows", 0, "População"], "CONTAGEM", "habitantes"),
                _kpi(result, "Densidade", ["rows", 0, "Densidade por 1.000"], "CONTINUO", DENSITY_UNIT)]
    else:
        out += _metric_kpis(result, list(range(len(metrics))))
    reference = metadata.get("referencia_nacional") or {}
    national_serie = {"caminho": ["metadata", "referencia_nacional", "serie"], "periodo": "competencia", "valor": "valor"}
    brazil = next((item for item in out if item.get("nivel") == "BR" and item.get("tipo") == "CONTINUO"), None)
    if brazil is not None and density and reference.get("serie"):
        brazil["serie"] = national_serie  # o bloco do Brasil é a taxa nacional: o minigráfico usa a mesma série
    elif density and reference.get("valores") and reference.get("estado") != "INDISPONIVEL":
        index = _reference_index(result)
        item = {"rotulo": "Taxa nacional (referência de contexto)", "tipo": "CONTINUO", "unidade": DENSITY_UNIT,
                "papel": "REFERENCIA_DE_CONTEXTO",
                "serie": national_serie}
        if index is not None:
            item = {**_kpi(result, item["rotulo"], ["metadata", "referencia_nacional", "valores", index, "valor"], "CONTINUO",
                           DENSITY_UNIT), **item}
        out = out[:MAX_KPIS - 1] + [item]
    if not out:
        out.append(_kpi(result, "Registros no resultado", ["total_rows"], "CONTAGEM"))
    return out[:MAX_KPIS]


def provenance(result: dict) -> list[dict]:
    """Chips de procedência: fonte e versão, fórmula, tipo de contagem, níveis e chave de execução."""
    metadata = result.get("metadata") or {}
    operation = metadata.get("operation")
    out = []
    source = metadata.get("source") or {}
    if source.get("dataset") == "brazil":
        scope = {"national": "fonte nacional", "municipal": "fonte municipal", "niveis": "fontes nacional e municipal"}.get(
            source.get("scope"), "base oficial")
        if source.get("scope") == "niveis":
            used = source.get("fontes_usadas") or []
            scope = "fontes nacional e municipal" if len(used) == 2 else "fonte " + ("nacional" if used == ["national"]
                                                                                     else "municipal")
        out.append({"rotulo": "Fonte", "valor": "Dados do Brasil, " + scope + (
            " · versão " + str(source["version"])[:12] if source.get("version") else ""), "caminho": ["metadata", "source"]})
    elif metadata.get("input_file"):
        digest = str((metadata.get("input_file") or {}).get("sha256") or "")[:12]
        out.append({"rotulo": "Fonte", "valor": "Arquivo importado" + (" · SHA-256 " + digest if digest else ""),
                    "caminho": ["metadata", "input_file"]})
    density = metadata.get("indicator") == "density" and operation in ("density", "report", "comparisons", "temporal",
                                                                         "distribution")
    formula = FORMULAS["density"] if density and operation in ("density", "report") else FORMULAS.get(operation)
    if formula:
        out.append({"rotulo": "Fórmula", "valor": formula})
    methods = metadata.get("metodos") or {}
    if methods.get("populacao_nacional"):
        out.append({"rotulo": "População do Brasil", "valor": "regra " + str(methods["populacao_nacional"]) +
                    " (junho, soma dos municípios)", "caminho": ["metadata", "metodos", "populacao_nacional"]})
    if methods.get("tendencia"):
        out.append({"rotulo": "Tendência", "valor": "versão " + str(methods["tendencia"]),
                    "caminho": ["metadata", "metodos", "tendencia"]})
    levels = ((metadata.get("representacao") or {}).get("niveis") or {})
    if levels.get("ordem"):
        out.append({"rotulo": "Níveis", "valor": " · ".join(levels["ordem"]), "caminho": ["metadata", "representacao", "niveis"]})
        out.append({"rotulo": "Tipo de contagem", "valor": " · ".join(str(levels["tipos"][name]) for name in levels["ordem"]
                                                                      if name in (levels.get("tipos") or {}))})
    else:
        unit = next((row.get("Unidade de contagem") for row in (result.get("rows") or []) if row.get("Unidade de contagem")),
                    None)
        kind = next((row.get("Tipo") for row in (result.get("rows") or []) if row.get("Tipo")), None) \
            if operation == "aggregate" else None
        if kind:
            out.append({"rotulo": "Tipo de contagem", "valor": kind})
        elif unit:
            out.append({"rotulo": "Unidade de contagem", "valor": unit})
    if metadata.get("execution_key"):
        out.append({"rotulo": "Chave de execução", "valor": str(metadata["execution_key"])[:12],
                    "caminho": ["metadata", "execution_key"]})
    return out


def summary(result: dict) -> dict | None:
    """Resumo do resultado: frase em partes verificadas, KPIs e procedência. None quando um segmento não confere."""
    composer = Composer(result)
    _model(result)(composer, result)
    if not composer.segments or not all(verify_segment(segment, result) for segment in composer.segments):
        return None
    # Os segmentos guardam tipo, caminho e texto; o result_id fica fora (o resumo pertence ao próprio resultado, e a
    # resposta continua igual entre execuções salvo result_id e created_at).
    segments = [{"tipo": item["type"], "caminho": item["path"], "texto": item["text"]} for item in composer.segments]
    return {"versao": VERSION, "modelo": (result.get("metadata") or {}).get("operation"), "texto": composer.sentence,
            "partes": composer.parts, "segmentos": segments, "indicadores": kpis(result),
            "procedencia": provenance(result),
            "nota": "Frase composta só com valores, relações e contagens do motor; nada é calculado na tela."}
