"""Frase-resumo, indicadores e procedência do resultado (result_summary.py; decisão D7, 19/10/2026).

A frase é composta só por cópias literais do resultado, verificadas pelos mesmos verificadores da conversa sobre
resultados; o texto fixo dos modelos não usa LEX-DES, LEX-NORM nem LEX-CAU, usa LEX-CMP só nas relações do motor e
LEX-TEN só quando o resultado traz metadata.tendencia; a taxa nacional é referência de contexto, nunca "acima" ou
"abaixo". O resumo não vai ao provedor de IA, e uma falha ao compô-lo não derruba a análise.
"""
import json
import re
import unicodedata

import pytest
from fastapi.testclient import TestClient

import llm_bridge
import main
import result_summary
from llm_context import provider_snapshot
from result_conversation import verify_segment, verify_segments
from test_representation import BASE, GEO, MAP, frame
from test_territorial_levels import PERIODS, catalog, inspected, ok  # noqa: F401 (fixture)
from test_territorial_levels import analyze as level_analyze

client = TestClient(main.app)
# CFG-LEX (SPEC, seção 4.4.15), em português.
LEX_NORM = ["adequado", "inadequado", "suficiente", "insuficiente", "deficitario", "deficit", "prioritario", "critico",
            "problematico", "ideal", "excesso", "carencia"]
LEX_CAU = ["causa", "explica", "devido a", "em razao de", "leva a", "impacto", "efeito de", "resulta de"]
LEX_DES = ["destaca-se", "chama atencao", "notavel", "principal", "mais importante"]
LEX_TEN = ["tendencia", "aceleracao", "desaceleracao", "crescimento acelerado", "crescimento desacelerado", "declinio"]
LEX_CMP = ["maioria", "a maior parte", "dobro", "metade", "maior", "menor", "percentual", "porcentagem", "proporcao",
           "razao", "primeiro", "segundo", "terceiro"]
TEMPORAL = {"period_filter": "", "temporal_comparability_confirmed": True, "territory_longitudinal_confirmed": True}
CASES = {
    "density": ("density", {}),
    "counts": ("counts", {}),
    "report-quantity": ("report", {"report_indicator": "quantity"}),
    "report-density": ("report", {"report_indicator": "density"}),
    "pair": ("comparisons", {"territory_ids": ["code:130260", "code:130420"]}),
    "three": ("comparisons", {"territory_ids": ["code:130260", "code:130420", "code:150680"]}),
    "window": ("comparisons", {**TEMPORAL, "territory_ids": ["code:130260", "code:130420"], "period_filters": ["2023", "2024"],
                               "comparison_values_period": "2024"}),
    "temporal": ("temporal", {**TEMPORAL, "temporal_indicator": "density"}),
    "aggregate": ("aggregate", {"population_additive_confirmed": True, "component_sum_confirmed": True,
                                "territory_ids": ["code:130260", "code:130420"]}),
    "distribution": ("distribution", {"distribution_indicator": "density"}),
    "ranking": ("ranking", {}),
    "spatial": ("spatial", {"reference_territory": "Manaus [130260]", **GEO}),
    "nearest": ("nearest", {"reference_mode": "list", "reference_ids": ["code:130260", "code:150680"],
                            "territory_ids": ["code:130260", "code:130420", "code:130340"], **GEO}),
    "criteria": ("criteria", {"criteria": {"logic": "and", "operands": [
        {"attribute": "densidade", "operator": "<", "value": "5"},
        {"attribute": "distancia", "operator": ">", "value": "100"}]},
        "reference_mode": "list", "reference_ids": ["code:130260"], **GEO}),
}


def plain(text):
    return "".join(c for c in unicodedata.normalize("NFKD", str(text).casefold()) if not unicodedata.combining(c))


def found(words, text):
    return [word for word in words if re.search(r"(?<!\w)" + re.escape(word) + r"(?!\w)", plain(text))]


def analyze(operation, **options):
    response = client.post("/api/analyze", files={"file": ("sintetico.csv", frame().to_csv(index=False).encode())},
                           data={"mapping": json.dumps(MAP), "options": json.dumps({**BASE, **options}),
                                 "operation": operation})
    assert response.status_code == 200, response.text
    return response.json()


def anchored(resumo, body):
    """Segmentos do resumo no formato do verificador da conversa (com o result_id do próprio resultado)."""
    return [{"type": item["tipo"], "function": "AFIRMACAO_ANALITICA", "path": item["caminho"],
             "result_id": body["result_id"], "text": item["texto"]} for item in resumo["segmentos"]]


def check(body):
    """Contrato comum: partes = texto, segmentos verificados, léxico controlado, sem cálculo nem juízo."""
    resumo = body["metadata"]["representacao"]["resumo"]
    assert resumo["versao"] == result_summary.VERSION and resumo["modelo"] == body["metadata"]["operation"]
    assert resumo["texto"] == "".join(part["texto"] for part in resumo["partes"])
    segments = anchored(resumo, body)
    assert segments and all(verify_segment(segment, body) for segment in segments)
    assert body["result_id"] not in json.dumps(resumo)  # a resposta só muda em result_id e created_at
    for part in resumo["partes"]:
        if "segmento" in part:
            assert segments[part["segmento"]]["text"] == part["texto"]
            assert segments[part["segmento"]]["path"] == part["caminho"]
    # Também pelo verificador completo da conversa (que exige todas as notas do resultado).
    notes = [{"type": "LIMITACAO", "function": "AFIRMACAO_ANALITICA", "path": ["notes", i], "result_id": body["result_id"],
              "text": note} for i, note in enumerate(body["notes"])]
    assert verify_segments(segments + notes, body)
    text = resumo["texto"]
    assert not found(LEX_NORM + LEX_CAU + LEX_DES, text), found(LEX_NORM + LEX_CAU + LEX_DES, text)
    assert not found(["acima", "abaixo"], text)
    template = " ".join(part["texto"] for part in resumo["partes"] if "segmento" not in part)
    assert not found(LEX_CMP, template), found(LEX_CMP, template)  # LEX-CMP só nas relações copiadas do motor
    if not body["metadata"].get("tendencia"):
        assert not found(LEX_TEN, text), found(LEX_TEN, text)
    assert 1 <= len(resumo["indicadores"]) <= result_summary.MAX_KPIS
    for item in resumo["indicadores"]:
        if "caminho" in item:  # cada indicador é um valor do resultado, nunca calculado
            value = body
            for key in item["caminho"]:
                value = value[key]
            assert value == item["valor"]
    assert any(item["rotulo"] == "Chave de execução" for item in resumo["procedencia"])
    return resumo


@pytest.mark.parametrize("case", list(CASES))
def test_every_analysis_has_a_verified_summary_without_forbidden_lexicon(case):
    operation, options = CASES[case]
    body = analyze(operation, **options)
    resumo = check(body)
    text = resumo["texto"]
    if case == "pair":
        assert "O valor de Manaus [130260] é maior que o de Tefe [130420]." in text
        assert any(segment["tipo"] == "RELACAO" for segment in resumo["segmentos"])
        assert "Diferença A − B: 9,50" in text
        assert "Diferença A − B: 9,50 por 1.000 habitantes." in text  # a diferença do par leva a unidade do indicador
    if case == "window":
        assert text.startswith("Na competência dos valores 2024:")
        assert "Não foi possível analisar a tendência porque há apenas 2 observações válidas." in text  # BLQ-MET do motor
    if case == "temporal":
        assert "Tendência (CAP-TEN-01)" in text and "(CAP-TMP-01)" in text
    if case == "aggregate":
        assert "Soma dos componentes (possível dupla contagem)" in text  # RQ-REP-14
        assert [item["rotulo"] for item in resumo["indicadores"]] == ["Territórios agregados", "Quantidade", "População",
                                                                      "Densidade"]
    if case == "distribution":
        assert "8 unidades classificadas em 5 classes" in text  # total do motor, nunca somado na tela
    if case == "nearest":
        assert text.startswith("Referência mais próxima: Territórios-alvo: 3; Referências autorizadas: 2;")
    if case == "criteria":
        assert "Atendem: " in text and "Não atendem: " in text
    if case in ("density", "report-density"):
        assert text == "Na competência 2024, densidade por 1.000 habitantes: 8 registros avaliáveis e 0 não avaliáveis."


def test_rotation_summary_reads_the_cohort_counts_of_the_engine():
    import pandas as pd
    df = pd.DataFrame({"Municipality": ["A", "A", "B", "A", "B", "C"], "Year": [2, 2, 2, 10, 10, 2],
                       "Profession": ["Nurses"] * 6, "Identity": ["x", "x", "x", "y", "x", "z"], "Population": [1000] * 6})
    mapping = {"territory": "Municipality", "period": "Year", "category": "Profession", "identity": "Identity"}
    options = {"longitudinal_identity_confirmed": True, "territory_longitudinal_confirmed": True,
               "cohort_coverage_confirmed": True}
    response = client.post("/api/analyze", files={"file": ("coorte.csv", df.to_csv(index=False).encode())},
                           data={"mapping": json.dumps(mapping), "options": json.dumps(options), "operation": "rotation"})
    assert response.status_code == 200, response.text
    body = response.json()
    assert [(item["label"], item["value"]) for item in body["metrics"]] == [
        ("Coortes avaliáveis", 2), ("Coortes não avaliáveis (sem registro em um dos períodos)", 1)]
    resumo = check(body)
    assert resumo["texto"] == ("Coorte de 2 a 10: 2 coortes avaliáveis e 1 sem registro em um dos períodos; permanência "
                               "e rotatividade em % da coorte inicial.")


def test_trend_summary_uses_engine_counts_only_with_cap_ten_01():
    rows = frame()
    rows = rows.assign(periodo=rows.periodo.map({"2023": "2021", "2024": "2022"}))
    for period, factor in (("2023", 2), ("2024", 3)):
        extra = frame()
        extra = extra[extra.periodo == "2024"].assign(periodo=period, quantidade=lambda d: d.quantidade * factor)
        rows = rows._append(extra, ignore_index=True)
    response = client.post("/api/analyze", files={"file": ("serie.csv", rows.to_csv(index=False).encode())},
                           data={"mapping": json.dumps(MAP), "operation": "temporal", "options": json.dumps(
                               {**BASE, **TEMPORAL, "temporal_indicator": "quantity"})})
    assert response.status_code == 200, response.text
    body = response.json()
    resumo = check(body)
    families = body["metadata"]["tendencia"]["familias"]
    assert "família do crescimento: " + str(families["CRESCIMENTO"]) in resumo["texto"]
    assert "família do declínio: " + str(families["DECLINIO"]) in resumo["texto"]
    paths = [segment["caminho"] for segment in resumo["segmentos"]]
    assert ["metadata", "tendencia", "familias", "CRESCIMENTO"] in paths


def test_levels_summary_keeps_brazil_states_and_municipalities_apart_and_the_rate_as_context(catalog):
    info = inspected()
    request = {"brasil": True, "estados": ["13"], "municipios": {"ids": ["code:130260", "code:150140"]}}
    body = ok(level_analyze(info, "density", request, period_filter="202306"))
    resumo = check(body)
    text = resumo["texto"]
    reference = body["metadata"]["referencia_nacional"]["valores"][0]["valor"]
    assert text == ("Na competência 202306, densidade por 1.000 habitantes em blocos por nível, sem somar níveis: Brasil "
                    "(total nacional), " + f"{reference:.2f}".replace(".", ",") + " por 1.000 habitantes; Estados (soma "
                    "dos municípios), 1 registro avaliável e 0 não avaliáveis; Municípios, 2 registros avaliáveis e 0 não "
                    "avaliáveis.")  # o Brasil já é o próprio bloco: a taxa nacional não se repete como referência
    municipal = ok(level_analyze(info, "density", {"municipios": {"ids": ["code:130260", "code:150140"]}},
                                 period_filter="202306"))
    context = check(municipal)
    assert context["texto"].endswith(" Referência de contexto: taxa nacional de " + f"{reference:.2f}".replace(".", ",") +
                                     " por 1.000 habitantes (Brasil, total nacional); não classifica nem colore os "
                                     "territórios.")
    assert context["indicadores"][-1]["papel"] == "REFERENCIA_DE_CONTEXTO" and context["indicadores"][-1]["valor"] == reference
    # Métricas por nível (K13): nenhuma conta só municípios sob um rótulo genérico, nada somado entre níveis.
    assert [(item["label"], item["value"], item["nivel"]) for item in body["metrics"]] == [
        ("Brasil (total nacional): registros avaliáveis", 1, "BR"),
        ("Brasil (total nacional): registros não avaliáveis", 0, "BR"),
        ("Estados (soma dos municípios): registros avaliáveis", 1, "UF"),
        ("Estados (soma dos municípios): registros não avaliáveis", 0, "UF"),
        ("Municípios: registros avaliáveis", 2, "MUN"), ("Municípios: registros não avaliáveis", 0, "MUN")]
    assert body["description"] == ("Densidade de pessoas por 1.000 habitantes por nível territorial (Brasil (total "
                                   "nacional), estados (soma dos municípios) e municípios), em blocos separados; nenhum "
                                   "nível é somado a outro.")
    kpis = resumo["indicadores"]
    assert kpis[0]["rotulo"] == "Brasil (total nacional)" and kpis[0]["nivel"] == "BR" and kpis[0]["valor"] == reference
    assert kpis[0]["serie"]["caminho"] == ["metadata", "referencia_nacional", "serie"]
    assert [item["rotulo"] for item in kpis] == ["Brasil (total nacional)", "Estados (soma dos municípios): registros "
                                                 "avaliáveis", "Municípios: registros avaliáveis"]
    serie = body["metadata"]["referencia_nacional"]["serie"]
    assert [item["competencia"] for item in serie] == ["202206", *PERIODS]  # todas as competências da fonte nacional
    assert serie[0]["valor"] is None and serie[0]["motivo"] == "SEM_COMPETENCIA_DE_JUNHO"  # lacuna, nunca zero
    assert body["metadata"]["representacao"]["referencias"][0]["serie"] == serie
    chips = {item["rotulo"]: item["valor"] for item in resumo["procedencia"]}
    assert chips["Níveis"] == "Brasil (total nacional) · Estado (soma dos municípios) · Município"
    assert "Soma dos componentes (possível dupla contagem)" in chips["Tipo de contagem"]
    assert chips["População do Brasil"].startswith("regra BR-POP-JUNHO-1")
    # A comparação com janela: Brasil lado a lado, sem relação; contagens da tendência do motor.
    window = ok(level_analyze(info, "comparisons", request, period_filters=PERIODS, comparison_values_period="202306"))
    text = check(window)["texto"]
    assert "Brasil (total nacional) lado a lado, sem relação: " in text
    assert "Tendência (CAP-TEN-01) na janela de 202301 a 202406 — família do crescimento: " in text
    assert "O valor de BELEM [150140] é menor que o de MANAUS [130260]." in text


def test_summary_and_its_inputs_never_reach_the_provider(catalog, monkeypatch):
    info = inspected()
    monkeypatch.setenv("GEMINI_API_KEY", "test-only-not-real")
    monkeypatch.setattr(llm_bridge, "_counter", 0)
    monkeypatch.setattr(llm_bridge, "_counter_day", "")
    headers = {"X-ADT-Session": client.post("/api/session").json()["token"]}
    request = {"brasil": True, "municipios": {"ids": ["code:130260", "code:150140"]}}
    result = ok(level_analyze(info, "comparisons", request, headers=headers, period_filters=PERIODS,
                              comparison_values_period="202406"))
    resumo = result["metadata"]["representacao"]["resumo"]
    sent = []

    async def provider(payload, *_args):
        sent.extend(payload)
        return {"intent": "ANALITICO", "topic": "none", "operation": "comparisons", "indicator": "density",
                "period": "", "category": "", "territory": ""}

    monkeypatch.setattr(llm_bridge, "_call_gemini", provider)
    form = {"dataset": "brazil", "dataset_version": info["source"]["version"], "mapping": json.dumps(info["suggested_mapping"])}
    response = client.post("/api/llm/interpret-context", headers=headers, data={
        **form, "scope": "municipal", "options": json.dumps({"abrangencia": request}), "history": "[]",
        "message": "Quero comparar de outro jeito", "displayed_result_id": result["result_id"]})
    assert response.status_code == 200, response.text
    assert sent, "o pedido analítico deveria chegar ao provedor minimizado"
    content = " ".join(sent)
    forbidden = ["resumo", "tendencia", "abrangencia", "referencia_nacional", "comparacao", "Referência de contexto",
                 "família do crescimento", "lado a lado", resumo["texto"][:40], result["result_id"]]
    for item in forbidden:
        assert item not in content, item
    # provider_snapshot só carrega estados enumerados do pré-exame.
    eligibility = {"field_states": {"period": {"status": "recognized"}},
                   "capabilities": {operation: {"status": "available"} for operation in main.OPERATIONS}}
    assert set(provider_snapshot(eligibility)) == {"source", "has_dataset", "recognized_roles", "capabilities"}


def test_a_failing_summary_never_breaks_the_analysis(monkeypatch):
    first = analyze("density")
    assert "resumo" in first["metadata"]["representacao"]

    def broken(_result):
        raise RuntimeError("falha simulada")
    monkeypatch.setattr(result_summary, "summary", broken)
    failed = analyze("density")
    assert failed["rows"] == first["rows"] and failed["metrics"] == first["metrics"]
    assert failed["metadata"]["execution_key"] == first["metadata"]["execution_key"]
    assert "resumo" not in failed["metadata"]["representacao"]
    assert failed["metadata"]["representacao"]["geometria"] == first["metadata"]["representacao"]["geometria"]


def test_a_segment_that_does_not_match_the_result_is_rejected():
    body = analyze("comparisons", territory_ids=["code:130260", "code:130420"])
    segments = anchored(body["metadata"]["representacao"]["resumo"], body)
    forged = dict(segments[0], text="99999")
    assert not verify_segment(forged, body)
    relation = next(segment for segment in segments if segment["type"] == "RELACAO")
    assert not verify_segment(dict(relation, text="O valor de Tefe [130420] é maior que o de Manaus [130260]."), body)
