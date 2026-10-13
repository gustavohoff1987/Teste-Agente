"""Bloco 2, Etapa 2: critérios combinados (CAP-SUB-01), ordenação, seleção por posição e faixas.

Base sintética gerada em tempo de teste (nomes, coordenadas e valores fictícios, não oficiais).
"""
import itertools
import json
from fractions import Fraction

import pandas as pd
import pytest
from fastapi.testclient import TestClient

import main
from combined_criteria import _and, _not, _or
from llm_bridge import OPERATIONS as LLM_OPERATIONS
from nearest_reference import GEOD

client = TestClient(main.app)
MAP = {"territory": "municipio", "territory_id": "codigo", "period": "periodo", "category": "categoria",
       "count": "quantidade", "population": "populacao", "latitude": "latitude", "longitude": "longitude"}
BASE = {"confirmed_roles": list(MAP), "count_unit": "pessoas", "population_denominator_confirmed": True,
        "fts_scope_confirmed": True, "object_confirmed": True, "crs": "SIRGAS2000", "period_filter": "2024",
        "category_filter": "MEDICINA"}
# nome, código, latitude, longitude, quantidade, população
UNITS = [("Alfa", "100001", -3.0, -60.0, 10, 10000),       # densidade 1
         ("Beta", "100002", -3.5, -61.0, 59, 25000),       # densidade 2,36 exata (2.3600000000000003 em ponto flutuante)
         ("Gama", "100003", -2.5, -56.7, 30, 10000),       # densidade 3
         ("Delta", "100004", -2.4, -54.7, 40, 10000),      # densidade 4
         ("Epsilon", "100005", -4.0, -63.0, 5, 0),         # população zero
         ("Zeta", "100006", -5.0, -62.0, None, 10000),     # quantidade ausente
         ("Eta", "100007", 63741, -60.0, 15, 10000),       # coordenada inválida; densidade 1,5
         ("Teta", "100008", -3.2, -59.0, 10, None)]        # população ausente
POINTS = {code: (lat, lon) for _, code, lat, lon, _, _ in UNITS}
REFS = ["code:100003", "code:100004"]


def frame(units=UNITS):
    return pd.DataFrame([{"municipio": n, "codigo": c, "periodo": period, "categoria": "MEDICINA", "quantidade": q,
                          "populacao": p, "latitude": lat, "longitude": lon}
                         for period in ("2023", "2024") for n, c, lat, lon, q, p in units])


def post(df=None, tree=None, mapping=MAP, path="/api/analyze", **options):
    opts = {**BASE, **options}
    if tree is not None:
        opts["criteria"] = tree
    df = frame() if df is None else df
    return client.post(path, files={"file": ("sintetico.csv", df.to_csv(index=False).encode())},
                       data={"mapping": json.dumps(mapping), "options": json.dumps(opts), "operation": "criteria"})


def ok(tree=None, df=None, **options):
    response = post(df, tree, **options)
    assert response.status_code == 200, response.text
    body = response.json()
    structured = body["metadata"]["criterios"]
    return body, structured, {item["elemento"]: item for item in structured["avaliacoes"]}


def leaf(attribute, operator, value, **extra):
    return {"attribute": attribute, "operator": operator, "value": value, **extra}


def both(*operands):
    return {"logic": "and", "operands": list(operands)}


def either(*operands):
    return {"logic": "or", "operands": list(operands)}


def negate(operand):
    return {"logic": "not", "operands": [operand]}


def km(a, b):
    return GEOD.inv(POINTS[a][1], POINTS[a][0], POINTS[b][1], POINTS[b][0])[2] / 1000


def nearest_km(code, refs=("100003", "100004")):
    return min(km(code, ref) for ref in refs)


def states(evaluations, node=None):
    return {key[5:]: (item["estado"] if node is None else item["nos"][node]["estado"]) for key, item in evaluations.items()}


def test_three_valued_logic_tables_follow_cap_sub_01():
    values = ("ATENDE", "NAO_ATENDE", "NAO_AVALIAVEL")
    for a, b in itertools.product(values, repeat=2):
        expected_and = "ATENDE" if a == b == "ATENDE" else "NAO_ATENDE" if "NAO_ATENDE" in (a, b) else "NAO_AVALIAVEL"
        expected_or = "ATENDE" if "ATENDE" in (a, b) else "NAO_ATENDE" if a == b == "NAO_ATENDE" else "NAO_AVALIAVEL"
        assert _and([a, b]) == _and([b, a]) == expected_and
        assert _or([a, b]) == _or([b, a]) == expected_or
    assert _or(["ATENDE", "NAO_AVALIAVEL"]) == "ATENDE"
    assert _and(["NAO_ATENDE", "NAO_AVALIAVEL"]) == "NAO_ATENDE"
    assert _and(["ATENDE", "NAO_AVALIAVEL"]) == "NAO_AVALIAVEL"
    assert [_not(v) for v in values] == ["NAO_ATENDE", "ATENDE", "NAO_AVALIAVEL"]


def test_single_density_criterion_with_exact_values_and_specific_motives():
    body, structured, evaluations = ok(leaf("densidade", "<", "2,36"))
    assert states(evaluations) == {"100001": "ATENDE", "100002": "NAO_ATENDE", "100003": "NAO_ATENDE", "100004": "NAO_ATENDE",
                                   "100005": "NAO_AVALIAVEL", "100006": "NAO_AVALIAVEL", "100007": "ATENDE",
                                   "100008": "NAO_AVALIAVEL"}
    motives = {key[5:]: item["nos"]["c1"].get("motivos") for key, item in evaluations.items() if item["estado"] == "NAO_AVALIAVEL"}
    assert motives == {"100005": ["DENOMINADOR_ZERO"], "100006": ["DADO_AUSENTE"], "100008": ["DENOMINADOR_AUSENTE"]}
    assert structured["contagens"] == {"ATENDE": 2, "NAO_ATENDE": 3, "NAO_AVALIAVEL": 3, "universo": 8}
    assert structured["arvore"]["nos"][0]["parametros"]["contexto"].startswith("valor sem unidade")
    assert structured["desfecho"] == "RES-LIM"  # unidades não avaliáveis são limitação analítica
    assert evaluations["code:100001"]["nos"]["c1"]["valor"] == 1.0
    assert "não constituem critério legal, sanitário ou científico universal" in body["notes"][0]
    assert body["metadata"]["evaluability"]["status"] == "AVALIAVEL_COM_LIMITACOES"


@pytest.mark.parametrize("operator,expected", [("<", "NAO_ATENDE"), ("<=", "ATENDE"), ("=", "ATENDE"),
                                               ("!=", "NAO_ATENDE"), (">=", "ATENDE"), (">", "NAO_ATENDE")])
def test_exact_threshold_is_not_disturbed_by_floating_point(operator, expected):
    assert 59 / 25000 * 1000 != 2.36  # o valor em ponto flutuante não é 2,36; a fração exata é
    _, _, evaluations = ok(leaf("densidade", operator, "2.36"))
    assert evaluations["code:100002"]["estado"] == expected


def test_density_agrees_with_the_stage_1_reference_criterion():
    """Mesma densidade e mesma comparação exata do critério de referências da Etapa 1, pela própria API."""
    for operator, value in (("<", "2.36"), (">=", "2.36"), ("=", "3")):
        _, _, evaluations = ok(leaf("densidade", operator, value))
        nearest = client.post("/api/analyze", files={"file": ("sintetico.csv", frame().to_csv(index=False).encode())}, data={
            "mapping": json.dumps(MAP), "operation": "nearest", "options": json.dumps({
                **BASE, "reference_mode": "criterion", "reference_criterion": {"operator": operator, "value": value}})})
        refs = nearest.json()["metadata"]["nearest_reference"]["conjunto_referencias"]
        assert {key for key, item in evaluations.items() if item["estado"] == "ATENDE"} == {m["id"] for m in refs["membros"]}
        unknown = {item["id"]: item["motivo"] for item in refs["avaliacao_criterio"]["NAO_AVALIAVEL"]}
        assert {key: item["nos"]["c1"]["motivos"][0] for key, item in evaluations.items() if item["estado"] == "NAO_AVALIAVEL"} == unknown
        assert sum(item["estado"] == "NAO_ATENDE" for item in evaluations.values()) == refs["avaliacao_criterio"]["NAO_ATENDE"]


def test_and_or_not_combine_density_and_distance_with_preserved_causes():
    threshold = "300"
    tree = both(leaf("densidade", "<", "2.36"), leaf("distancia", ">", threshold))
    body, structured, evaluations = ok(tree, reference_mode="list", reference_ids=REFS)
    distance = states(evaluations, "c2")
    for code in ("100001", "100002", "100005", "100006", "100008"):
        assert distance[code] == ("ATENDE" if nearest_km(code) > 300 else "NAO_ATENDE")
        assert evaluations["code:" + code]["nos"]["c2"]["valor"] == nearest_km(code)
    assert distance["100007"] == "NAO_AVALIAVEL" and evaluations["code:100007"]["nos"]["c2"]["motivos"] == ["COORDENADA_INVALIDA"]
    result = states(evaluations)
    assert result["100001"] == "ATENDE"                     # ATENDE E ATENDE
    assert result["100007"] == "NAO_AVALIAVEL"              # ATENDE E NAO_AVALIAVEL
    assert evaluations["code:100007"]["causas"] == [{"no": "c2", "motivos": ["COORDENADA_INVALIDA"]}]
    assert evaluations["code:100007"]["nos"]["n1"]["motivos"] == ["DEPENDENCIA_NAO_AVALIAVEL"]
    assert result["100008"] == "NAO_ATENDE" and distance["100008"] == "NAO_ATENDE"  # NAO_AVALIAVEL E NAO_ATENDE
    assert "causas" not in evaluations["code:100008"]  # composto decidido não recebe motivo de não avaliabilidade
    assert evaluations["code:100008"]["nos"]["c1"]["motivos"] == ["DENOMINADOR_AUSENTE"]  # avaliação do operando conservada
    assert result["100005"] == "NAO_AVALIAVEL"              # NAO_AVALIAVEL E ATENDE
    assert set(c["no"] for c in evaluations["code:100005"]["causas"]) == {"c1"}
    _, _, alternatives = ok(either(leaf("densidade", "<", "2.36"), leaf("distancia", ">", threshold)),
                            reference_mode="list", reference_ids=REFS)
    assert states(alternatives)["100007"] == "ATENDE"       # ATENDE OU NAO_AVALIAVEL
    assert states(alternatives)["100002"] == "ATENDE"       # NAO_ATENDE OU ATENDE (a 480 km)
    assert states(alternatives)["100008"] == "NAO_AVALIAVEL"  # NAO_AVALIAVEL OU NAO_ATENDE
    _, _, negated = ok(negate(leaf("densidade", "<", "2.36")))
    assert states(negated) == {key: _not(value) for key, value in states(ok(leaf("densidade", "<", "2.36"))[2]).items()}
    assert any("DISTANCIA_GEODESICA_DIRETA" == item["tipo"] for item in structured["limitacoes"])


def test_order_of_conditions_does_not_change_the_result():
    a, b, c = leaf("densidade", "<", "3"), leaf("distancia", ">", "250"), leaf("populacao", ">=", "10000")
    shapes = [both(a, b, c), both(c, b, a), both(both(b, a), c), both(c, both(a, b))]
    results = [states(ok(shape, reference_mode="list", reference_ids=REFS)[2]) for shape in shapes]
    assert all(result == results[0] for result in results)


def test_unknown_eligibility_is_never_treated_as_proven_ineligible():
    criterion = {"reference_mode": "criterion", "reference_criterion": {"operator": ">=", "value": "2.36"}}
    tree = both(leaf("densidade", "<", "2.36"), leaf("distancia", ">", "300"))
    _, structured, evaluations = ok(tree, **criterion)
    refs = structured["referencias"]
    assert refs["cobertura_avaliacao_elegibilidade"] == {"candidatos": 8, "ATENDE": 3, "NAO_ATENDE": 2, "NAO_AVALIAVEL": 3,
                                                         "completa": False}
    assert refs["cobertura_geografica_elegiveis"] == {"elegiveis_confirmados": 3, "com_coordenadas_avaliaveis": 3,
                                                      "sem_coordenadas_avaliaveis": 0}
    assert refs["alcance_afirmacao"].startswith("não afirmada: 3 candidato(s) de elegibilidade desconhecida")
    assert refs["aceitacoes_disponiveis"]["elegibilidade_confirmada"] == 3
    assert all(item["nos"]["c2"]["estado"] == "NAO_AVALIAVEL" for item in evaluations.values())
    assert evaluations["code:100001"]["estado"] == "NAO_AVALIAVEL"  # ATENDE E (distância indeterminada)
    assert evaluations["code:100002"]["estado"] == "NAO_ATENDE"     # NAO_ATENDE decide sem a distância
    accepted = ok(tree, eligibility_scope="confirmed_eligible", **criterion)
    alfa, expected = accepted[2]["code:100001"]["nos"]["c2"], nearest_km("100001", ("100002", "100003", "100004"))
    assert alfa["valor"] == expected and alfa["estado"] == ("ATENDE" if expected > 300 else "NAO_ATENDE")
    assert alfa["alcance"] == "conjunto completo das referências de elegibilidade confirmada"
    assert any(item["tipo"] == "COBERTURA_PARCIAL" for item in accepted[1]["limitacoes"])
    assert accepted[1]["referencias"]["alcance_afirmacao"].startswith("referência mais próxima entre as referências de elegibilidade confirmada")


def test_partial_coverage_requires_explicit_acceptance():
    tree = leaf("distancia", "<=", "400")
    refs = ["code:100003", "code:100007"]  # Eta tem coordenada inválida
    _, structured, evaluations = ok(tree, reference_mode="list", reference_ids=refs)
    assert all(item["estado"] == "NAO_AVALIAVEL" for item in evaluations.values())
    assert structured["desfecho"] == "BLQ-DAD"  # nenhum avaliável: coordenada de referência inválida (como na Etapa 1)
    assert structured["referencias"]["aceitacoes_disponiveis"]["cobertura_parcial"] == 7
    _, accepted, partial = ok(tree, reference_mode="list", reference_ids=refs, distance_scope="evaluable_references")
    alfa = partial["code:100001"]["nos"]["c1"]
    assert alfa["alcance"] == "entre as referências avaliáveis (cobertura parcial)" and alfa["valor"] == km("100001", "100003")
    assert partial["code:100007"]["estado"] == "NAO_AVALIAVEL"  # o próprio alvo continua sem coordenada válida
    assert any(item["tipo"] == "COBERTURA_PARCIAL" for item in accepted["limitacoes"])


def test_empty_reference_set_keeps_every_target_with_dependency_detail():
    no_unknown = [u for u in UNITS if u[1] not in ("100005", "100006", "100008")]
    criterion = {"reference_mode": "criterion", "reference_criterion": {"operator": ">=", "value": "100"}}
    tree = both(leaf("densidade", "<", "2.36"), leaf("distancia", ">", "100"))
    _, structured, evaluations = ok(tree, df=frame(no_unknown), **criterion)
    assert structured["referencias"]["n"] == 0
    assert evaluations["code:100001"]["estado"] == "NAO_AVALIAVEL"
    assert evaluations["code:100001"]["nos"]["c2"]["causas"] == [{"origem": "referências", "detalhe": "CONJUNTO_REFERENCIAS_VAZIO"}]
    assert evaluations["code:100007"]["nos"]["c2"]["motivos"] == ["COORDENADA_INVALIDA", "DEPENDENCIA_NAO_AVALIAVEL"]
    assert evaluations["code:100002"]["estado"] == "NAO_ATENDE"
    assert structured["contagens"]["universo"] == 5
    only_distance = ok(leaf("distancia", ">", "100"), df=frame(no_unknown), **criterion)[1]
    assert only_distance["desfecho"] == "BLQ-DEP" and only_distance["contagens"]["NAO_AVALIAVEL"] == 5


def test_targets_selection_does_not_reduce_the_reference_universe():
    criterion = {"reference_mode": "criterion", "reference_criterion": {"operator": ">=", "value": "3"}}
    tree = leaf("distancia", ">", "0")
    _, full, _ = ok(tree, **criterion)
    _, subset, evaluations = ok(tree, territory_ids=["code:100001"], **criterion)
    assert subset["referencias"]["membros"] == full["referencias"]["membros"]
    assert list(evaluations) == ["code:100001"] and subset["universo"]["definicao"] == "subconjunto selecionado"


def test_membership_and_uf_conditions():
    _, _, evaluations = ok(leaf("territorio", "in", ["code:100001", "code:100002"]))
    assert states(evaluations)["100001"] == "ATENDE" and states(evaluations)["100003"] == "NAO_ATENDE"
    _, _, outside = ok(leaf("territorio", "not_in", ["code:100001"]))
    assert states(outside)["100001"] == "NAO_ATENDE" and states(outside)["100002"] == "ATENDE"
    # Base importada: a regra governada de UF não se aplica; a condição fica não avaliável, sem presumir.
    _, _, uf = ok(leaf("uf", "=", "AM"))
    assert all(item["nos"]["c1"]["motivos"] == ["SIGNIFICADO_NAO_ESTABELECIDO"] for item in uf.values())


@pytest.mark.parametrize("tree,message", [
    ("densidade < 2", "Expressões livres"),
    (leaf("densidade", "≈", "2"), "Operador não autorizado"),
    (leaf("idade", "<", "2"), "Atributo de critério não autorizado"),
    (leaf("densidade", "<", "-1"), "não negativo"),
    (leaf("densidade", "<", "1.000,5"), "ambíguo"),
    (leaf("quantidade", "<", "2", unit="vinculos"), "não há conversão"),
    (leaf("populacao", "<", "2", category="MEDICINA"), "Categoria só pode"),
    (leaf("territorio", "<", ["code:100001"]), "Pertença territorial"),
    (leaf("territorio", "in", ["code:999"]), "inexistentes"),
    (leaf("uf", "=", "XX"), "UF não reconhecida"),
    ({"logic": "and", "operands": [leaf("densidade", "<", "2")]}, "ao menos duas"),
    ({"logic": "xor", "operands": [leaf("densidade", "<", "2"), leaf("densidade", ">", "1")]}, "Combinação não autorizada"),
    ({**leaf("densidade", "<", "2"), "formula": "q/p"}, "Campo não reconhecido"),
])
def test_incompatible_or_free_criteria_are_refused(tree, message):
    response = post(tree=tree)
    assert response.status_code == 422 and message in response.json()["detail"], response.text


def test_missing_population_or_quantity_columns_block_with_reason():
    without_population = {k: v for k, v in MAP.items() if k != "population"}
    response = post(tree=leaf("densidade", "<", "2"), mapping=without_population,
                    confirmed_roles=list(without_population))
    assert response.status_code == 422 and "população" in response.json()["detail"]
    gate = post(tree=leaf("densidade", "<", "2"), mapping=without_population, path="/api/preflight",
                confirmed_roles=list(without_population)).json()["capabilities"]["criteria"]
    assert gate["status"] == "unavailable" and any("população" in r for r in gate["reasons"])
    without_count = {k: v for k, v in MAP.items() if k != "count"}
    response = post(tree=leaf("quantidade", ">", "2"), mapping=without_count, confirmed_roles=list(without_count))
    assert response.status_code == 422 and "quantitativos" in response.json()["detail"]
    # População sozinha não exige quantitativos.
    assert post(tree=leaf("populacao", ">=", "10000"), mapping=without_count, confirmed_roles=list(without_count)).status_code == 200


def test_preflight_gate_needs_a_criterion_and_the_llm_never_receives_the_operation():
    gate = post(path="/api/preflight").json()["capabilities"]["criteria"]
    assert gate["status"] == "needs_confirmation" and any("critério" in r for r in gate["reasons"])
    assert post(tree=leaf("densidade", "<", "2"), path="/api/preflight").json()["capabilities"]["criteria"]["status"] == "available"
    assert "criteria" not in LLM_OPERATIONS


def test_ranking_shares_positions_on_exact_ties_and_top_n_includes_ties():
    extra = [("Iota", "100009", -3.3, -60.5, 30, 10000), ("Kapa", "100010", -3.4, -60.6, 60, 20000),   # densidade 3 (como Gama)
             ("Lambda", "100011", -3.6, -60.7, 7, 100000), ("Mu", "100012", -3.7, -60.8, 21, 300000)]  # 0,07 exata (ponto flutuante: 0.06999999999999999)
    df = frame(UNITS + extra)
    _, structured, _ = ok(df=df, ranking={"attribute": "densidade", "direction": "desc", "top_n": 2})
    positions = {item["id"][5:]: item["posicao"] for item in structured["ordenacao"]["posicoes"]}
    assert positions == {"100004": 1, "100003": 2, "100009": 2, "100010": 2, "100002": 5, "100007": 6, "100001": 7,
                         "100011": 8, "100012": 8}
    assert {item["id"][5:] for item in structured["ordenacao"]["nao_avaliaveis"]} == {"100005", "100006", "100008"}
    selection = structured["selecao"]
    assert selection["n_solicitado"] == 2 and selection["n_efetivo"] == 4
    assert any(item["tipo"] == "EMPATE_NO_CORTE" for item in structured["limitacoes"])
    exact = ok(df=df, ranking={"attribute": "densidade", "direction": "desc", "top_n": 2, "exact_n": True})[1]
    assert exact["selecao"]["membros"] is None and exact["pendencias"][0]["tipo"] == "EMPATE_NO_CORTE"
    assert "Não há regra de desempate autorizada" in exact["pendencias"][0]["pergunta"]
    ascending = ok(df=df, ranking={"attribute": "densidade", "direction": "asc", "top_n": 1})[1]
    assert [item["id"][5:] for item in ascending["selecao"]["membros"]] == ["100011", "100012"]


def test_ranking_by_distance_over_the_set_that_meets_the_criteria():
    tree = leaf("densidade", "<", "3")
    body, structured, _ = ok(tree, reference_mode="list", reference_ids=REFS,
                             ranking={"attribute": "distancia", "direction": "desc", "top_n": 2})
    ranking = structured["ordenacao"]
    assert ranking["conjunto"] == "atende" and ranking["n_membros"] == 3  # Alfa, Beta, Eta
    assert [item["id"] for item in ranking["posicoes"]] == sorted(["code:100001", "code:100002"], key=lambda k: -nearest_km(k[5:]))
    assert ranking["nao_avaliaveis"] == [{"id": "code:100007", "territorio": "Eta [100007]", "motivos": ["COORDENADA_INVALIDA"]}]
    assert [row["Território"] for row in body["rows"][:2]] == ["Beta", "Alfa"] and body["rows"][0]["Posição"] == 1
    assert body["rows"][0]["Selecionado"] == "Sim"


def test_distance_bands_use_half_open_intervals_with_the_last_closed():
    _, structured, _ = ok(reference_mode="list", reference_ids=REFS, bands={"attribute": "distancia", "limits": ["0", "300", "2000"]})
    bands = structured["faixas"]
    assert bands["capacidade"] == "CAP-ESP-03" and bands["origem_limites"] == "escolha do usuário"
    assert [b["faixa"] for b in bands["faixas"]] == ["0 a <300", "300 a 2000"]
    expected = {"code:" + code: ("0 a <300" if nearest_km(code) < 300 else "300 a 2000")
                for code in ("100001", "100002", "100003", "100004", "100005", "100006", "100008")}
    assert bands["pertenca"] == expected and bands["pertenca"]["code:100003"] == "0 a <300"  # distância zero: alvo é referência
    assert [item["id"] for item in bands["nao_avaliaveis"]] == ["code:100007"] and bands["fora_de_todas"] == []
    # Limite final abaixo do valor completo (truncado como numa apresentação): o território fica fora, sem arredondar.
    beta = nearest_km("100002")
    truncated = format(beta, ".6f")[:-1]
    assert Fraction(truncated) < Fraction(beta)
    narrow = ok(reference_mode="list", reference_ids=REFS, bands={"attribute": "distancia", "limits": ["0", truncated]})[1]["faixas"]
    assert "code:100002" in {item["id"] for item in narrow["fora_de_todas"]}
    response = post(reference_mode="list", reference_ids=REFS, bands={"attribute": "distancia", "limits": ["10"]})
    assert response.status_code == 422 and "nenhum intervalo é criado pelo sistema" in response.json()["detail"]
    response = post(reference_mode="list", reference_ids=REFS, bands={"attribute": "distancia", "limits": ["10", "5"]})
    assert response.status_code == 422 and "crescentes" in response.json()["detail"]


def test_last_band_includes_its_upper_limit_and_first_excludes_the_next():
    _, structured, _ = ok(bands={"attribute": "densidade", "limits": ["1", "2.36", "4"]})
    membership = structured["faixas"]["pertenca"]
    assert membership["code:100001"] == "1 a <2,36" and membership["code:100002"] == "2,36 a 4"
    assert membership["code:100004"] == "2,36 a 4"  # 4 = limite superior final, incluído


def test_comparison_with_previous_definition_never_treats_unknown_as_outside():
    previous = leaf("densidade", "<", "2.36")
    current = both(leaf("densidade", "<", "2.36"), leaf("distancia", ">", "300"))
    _, structured, _ = ok(current, reference_mode="list", reference_ids=REFS, comparison={"criteria": previous, "label": "anterior"})
    comparison = structured["comparacao"]
    assert {item["id"] for item in comparison["em_ambos"]} == {"code:100001"}
    assert {item["id"] for item in comparison["somente_anterior"]} == set()
    eta = next(item for item in comparison["indeterminados"] if item["id"] == "code:100007")
    assert eta == {"id": "code:100007", "territorio": "Eta [100007]", "anterior": "DENTRO", "atual": "NAO_AVALIAVEL"}
    assert comparison["transicoes"]["DENTRO→NAO_AVALIAVEL"] == 1


def test_parameter_change_changes_identity_and_identical_request_restores_identical_result():
    tree = both(leaf("densidade", "<", "2.36"), leaf("distancia", ">", "300"))
    first = post(tree=tree, reference_mode="list", reference_ids=REFS).json()
    again = post(tree=tree, reference_mode="list", reference_ids=REFS).json()
    changed = post(tree=both(leaf("densidade", "<", "2.5"), leaf("distancia", ">", "300")), reference_mode="list",
                   reference_ids=REFS).json()
    assert first["metadata"]["execution_key"] == again["metadata"]["execution_key"] != changed["metadata"]["execution_key"]
    assert first["rows"] == again["rows"] and first["metadata"]["criterios"] == again["metadata"]["criterios"]
    assert first["result_id"] != again["result_id"]


def test_exported_rows_and_metadata_are_complete():
    tree = both(leaf("densidade", "<", "2.36"), leaf("distancia", ">", "300"))
    body, structured, _ = ok(tree, reference_mode="list", reference_ids=REFS)
    assert len(body["rows"]) == structured["universo"]["n"] == 8  # todos os territórios, inclusive não avaliáveis
    row = next(r for r in body["rows"] if r["Código"] == "100007")
    assert row["Resultado"] == "NAO_AVALIAVEL" and row["Motivos"] == "DEPENDENCIA_NAO_AVALIAVEL ← c2: COORDENADA_INVALIDA"
    assert row["c2 · distância à referência mais próxima > 300 km"] == "NAO_AVALIAVEL (COORDENADA_INVALIDA)"
    assert row["c1 · densidade < 2,36 por 1.000 habitantes"] == "ATENDE"
    assert [r["Resultado"] for r in body["rows"]] == sorted((r["Resultado"] for r in body["rows"]),
                                                            key=["ATENDE", "NAO_ATENDE", "NAO_AVALIAVEL"].index)
    assert structured["arvore"]["raiz"] == "n1" and {n["no"] for n in structured["arvore"]["nos"]} == {"n1", "c1", "c2"}
    assert set(structured["conjuntos"]) == {"ATENDE", "NAO_ATENDE", "NAO_AVALIAVEL"}
    json.dumps(body, allow_nan=False)  # JSON estrito: sem NaN, frações ou decimais crus
    assert body["metadata"]["options"]["criteria"] == tree


def test_threshold_unit_conversions_are_exact_and_values_stay_in_the_canonical_unit():
    tree_km, tree_m = leaf("distancia", ">", "300"), leaf("distancia", ">", "300000", unit="m")
    body_km, _, km_eval = ok(tree_km, reference_mode="list", reference_ids=REFS)
    body_m, _, m_eval = ok(tree_m, reference_mode="list", reference_ids=REFS)
    assert states(km_eval) == states(m_eval)
    assert "c1 · distância à referência mais próxima (km)" in body_m["rows"][0]
    per_100k = ok(leaf("densidade", "<", "236", unit="por_100000_habitantes"))[2]
    assert states(per_100k) == states(ok(leaf("densidade", "<", "2.36"))[2])  # 236 por 100 mil = 2,36 por mil, exato
    response = post(tree=leaf("distancia", ">", "1", unit="milhas"), reference_mode="list", reference_ids=REFS)
    assert response.status_code == 422 and "Unidade não suportada" in response.json()["detail"]


def test_ranking_direction_and_band_limits_are_never_assumed():
    gate = post(path="/api/preflight", ranking={"attribute": "densidade"}).json()["capabilities"]["criteria"]
    assert gate["status"] == "needs_confirmation" and any("direção da ordenação" in r for r in gate["reasons"])
    response = post(ranking={"attribute": "densidade", "top_n": 2})
    assert response.status_code == 422 and "direção da ordenação" in response.json()["detail"]
    gate = post(path="/api/preflight", bands={"attribute": "densidade", "limits": []}).json()["capabilities"]["criteria"]
    assert gate["status"] == "unavailable" and any("nenhum intervalo é criado pelo sistema" in r for r in gate["reasons"])
