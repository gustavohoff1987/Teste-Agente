"""D1 (19/10/2026): nenhuma confirmação de colunas e campos, em nenhum nível, nas bases oficial e importada.

O usuário só escolhe colunas e parâmetros; regra conclusiva estabelece o papel; sugestão nunca é seleção; as
antigas declarações são premissas aplicadas pelo backend, com nota, e um false explícito na API continua
recusando a premissa. Bases sintéticas (sem dados reais).
"""
import json
import re

import pandas as pd
import pytest
from fastapi.testclient import TestClient

from analysis_premises import apply_premises
from brazil_catalog_profile import FIELDS, apply_curated_options, curated_profile
from catalog_support import use_external_catalog
from main import app
from prepare_block1_catalog import prepare
from semantic_bridge import OPERATIONS, candidates, coordinate_roles, established_roles, preflight, verified_separator

client = TestClient(app)
FORBIDDEN = re.compile(r"Confirm|confirmad|Declar")
# nome, código, quantidade, população, latitude, longitude (pontos sintéticos, vírgula decimal)
UNITS = [("MANAUS", "130260", 10, 1000, "-3,1", "-60,0"), ("TEFE", "130420", 5, 2000, "-3,3", "-64,7"),
         ("PARINTINS", "130340", 7, 4000, "-2,6", "-56,7"), ("SANTAREM", "150680", 9, 3000, "-2,4", "-54,7")]
HEADER = "municipio;cod_ibge;periodo_ano;periodo_mes;categoria_profissional;quantidade;populacao;latitude;longitude;id_profissional"


def imported_csv(units=UNITS, periods=((2023, 6), (2024, 6)), skip=()):
    rows = [HEADER]
    for year, month in periods:
        for name, code, count, population, lat, lon in units:
            if (name, year) not in skip:
                rows.append(f"{name};{code};{year};{month};MEDICINA;{count};{population};{lat};{lon};p-{code}-{year % 2}")
    return ("\n".join(rows) + "\n").encode()


def post(path, raw, mapping, operation="density", **options):
    return client.post(path, files={"file": ("importada.csv", raw)},
                       data={"operation": operation, "mapping": json.dumps(mapping), "options": json.dumps(options)})


def texts(eligibility):
    """Todos os textos de motivo, requisito e estado de campo do pré-exame."""
    for capability in eligibility["capabilities"].values():
        yield from capability["reasons"]
        for item in capability["requirements"]:
            yield item["title"]
            yield item["detail"]
    for state in eligibility["field_states"].values():
        yield state["message"]
        yield state.get("evidence", "")


def assert_no_confirmation(eligibility):
    found = [text for text in texts(eligibility) if FORBIDDEN.search(text)]
    assert not found, found
    for operation, capability in eligibility["capabilities"].items():
        for item in capability["requirements"]:
            if item["status"] == "needs_confirmation":
                assert item["kind"] == "escolha", (operation, item)  # caso 2: escolha pendente, nunca confirmação
            if item["status"] != "met":
                assert item["kind"] in ("escolha", "dados") and item["step"] in (0, 1), item


@pytest.fixture
def official(tmp_path, monkeypatch):
    destination = tmp_path / "catalogo"
    prepare(destination)
    use_external_catalog(monkeypatch, destination)
    return destination


def test_no_confirmation_text_in_the_twelve_analyses_of_both_sources(official):
    """Caso 1 e 2: base importada e catálogo do Bloco 1, nas 12 análises."""
    raw = imported_csv()
    info = client.post("/api/inspect", files={"file": ("importada.csv", raw)}).json()
    assert_no_confirmation(info["preflight"])
    chosen = {**info["suggested_mapping"], "territory_id": "cod_ibge"}
    for options in ({}, {"confirmed_roles": ["territory_id"], "count_unit": "pessoas", "period_filter": "202406"}):
        assert_no_confirmation(post("/api/preflight", raw, chosen, **options).json())
    for operation in OPERATIONS:
        resident = client.post("/api/inspect", data={"dataset": "brazil", "operation": operation}).json()
        assert_no_confirmation(resident["preflight"])
        gate = client.post("/api/preflight", data={"dataset": "brazil", "scope": resident["source"]["scope"],
                                                  "operation": operation, "mapping": json.dumps(resident["suggested_mapping"]),
                                                  "options": "{}"}).json()
        assert_no_confirmation(gate)


def test_premises_are_applied_without_declarations_and_reported():
    """Caso 3: premissas aplicadas pelo backend, com origem e nota em "Método e limitações"."""
    raw = imported_csv()
    info = client.post("/api/inspect", files={"file": ("importada.csv", raw)}).json()
    mapping = {**info["suggested_mapping"], "territory_id": "cod_ibge"}
    base = {"confirmed_roles": ["territory_id"], "count_unit": "pessoas", "period_filter": "202406"}
    density = post("/api/analyze", raw, mapping, **base)
    assert density.status_code == 200, density.text
    assert any(note.startswith("Denominador: população da mesma linha") for note in density.json()["notes"])
    comparisons = post("/api/analyze", raw, mapping, "comparisons", **base).json()
    assert any(note.startswith("Comparabilidade entre territórios") for note in comparisons["notes"])
    aggregate = post("/api/analyze", raw, mapping, "aggregate", **base).json()
    assert aggregate["rows"][0]["Tipo"] == "Soma dos componentes (possível dupla contagem)"
    assert aggregate["metadata"]["evaluability"] == {
        "status": "AVALIAVEL_COM_LIMITACOES", "limitacoes": ["SOMA_COM_POSSIVEL_DUPLA_CONTAGEM"],
        "policy": "Ausências não são convertidas em zero; condições por elemento preservadas nas linhas."}
    temporal = post("/api/analyze", raw, mapping, "temporal", confirmed_roles=["territory_id"], count_unit="pessoas",
                    temporal_indicator="density").json()
    assert {"temporal_comparability_confirmed", "territory_longitudinal_confirmed"} <= set(temporal["metadata"]["options"]["analysis_premises"])
    assert any("Identidade territorial: verificada nos dados" in note for note in temporal["notes"])
    assert not any("pelo usuário para esta execução" in note for note in temporal["notes"])


@pytest.mark.parametrize("operation,key", [("comparisons", "comparison_confirmed"), ("density", "population_denominator_confirmed"),
                                           ("aggregate", "population_additive_confirmed"),
                                           ("temporal", "temporal_comparability_confirmed")])
def test_explicit_false_still_refuses_the_premise(operation, key):
    """Caso 4: valor explícito da API prevalece; a premissa recusada bloqueia com texto neutro."""
    raw = imported_csv()
    mapping = {**client.post("/api/inspect", files={"file": ("importada.csv", raw)}).json()["suggested_mapping"],
               "territory_id": "cod_ibge"}
    options = {"confirmed_roles": ["territory_id"], "count_unit": "pessoas", "temporal_indicator": "quantity",
               **({} if operation == "temporal" else {"period_filter": "202406"})}
    assert post("/api/analyze", raw, mapping, operation, **options).status_code == 200
    refused = post("/api/analyze", raw, mapping, operation, **options, **{key: False})
    assert refused.status_code == 422
    assert "foi recusada nas opções desta solicitação" in refused.json()["detail"]


def official_frame():
    rows = [{"municipio": name, "cod_ibge": code, "Período (ano e mês)": period, "categoria_profissional": "MEDICINA",
             "quantidade": str(count), "quantidade_2": str(count + 1), "população_estimada": str(population),
             "latitude": lat, "longitude": lon}
            for period in ("202306", "202406") for name, code, count, population, lat, lon in UNITS]
    frame = pd.DataFrame(rows)
    frame.attrs["source"] = {"dataset": "brazil", "scope": "municipal"}
    return frame


def test_official_profile_is_field_by_field():
    """Caso 5: trocar a contagem mantém território e período do perfil e leva as premissas dependentes para a
    camada genérica (antes, mudar uma coluna desligava o perfil inteiro)."""
    frame = official_frame()
    canonical = dict(FIELDS["municipal"])
    assert curated_profile(frame, canonical)["governed_roles"] == list(canonical)
    changed = {**canonical, "count": "quantidade_2"}
    profile = curated_profile(frame, changed)
    assert profile is not None and "count" not in profile["governed_roles"]
    assert {"territory", "territory_id", "period"} <= set(profile["governed_roles"])
    official_premises = [item["option"] for item in profile["premises"]]
    assert official_premises == ["territory_longitudinal_confirmed", "population_additive_confirmed"]
    options = apply_premises(frame, changed, {"confirmed_roles": ["count"], "count_unit": "vinculos"})
    assert options["governed_premises"] == official_premises
    assert {"temporal_comparability_confirmed", "comparison_confirmed", "component_sum_confirmed"} <= set(options["analysis_premises"])
    assert options["count_unit"] == "vinculos"  # a unidade do perfil só vale com a contagem do perfil
    assert established_roles(frame, changed, options) == set(changed)
    assert apply_curated_options(frame, changed, {})["governed_roles"] == profile["governed_roles"]


def test_header_suggestion_is_never_applied_silently():
    """Caso 6: a categoria sugerida pelo cabeçalho não vira declaração; o usuário informa o objeto."""
    raw = b"Territorio;Ano;Total de medicos unicos\nA;2024;5\nB;2024;7\n"
    info = client.post("/api/inspect", files={"file": ("cabecalho.csv", raw)}).json()
    assert info["suggested_category_constant"] == "Médicos"
    assert "count" not in info["suggested_mapping"] and info["preflight"]["object"]["status"] == "ausente"
    mapping = {**info["suggested_mapping"], "count": "Total de medicos unicos"}
    options = {"confirmed_roles": ["count"], "count_unit": "pessoas"}
    gate = post("/api/preflight", raw, mapping, **options).json()["capabilities"]["counts"]
    assert gate["status"] == "needs_confirmation" and any("Informe o objeto de análise" in r for r in gate["reasons"])
    assert post("/api/preflight", raw, mapping, **options, category_constant="Médicos").json()["capabilities"]["counts"]["status"] == "available"


def test_single_period_is_an_option_of_the_period_selector():
    """Caso 7: período único é uma opção do seletor de período, não uma declaração."""
    frame = pd.DataFrame({"Territorio": ["A", "B"], "Categoria": ["Médicos"] * 2, "Quantidade": [3, 4]})
    mapping, _ = candidates(frame)
    gate = preflight(frame, mapping, {"count_unit": "pessoas"})["capabilities"]["counts"]
    assert gate["status"] == "needs_confirmation"
    assert "Escolha a coluna de Período ou a opção «A base tem um único período»." in gate["reasons"]
    item = next(r for r in gate["requirements"] if "único período" in r["detail"])
    assert (item["kind"], item["step"]) == ("escolha", 0)
    assert preflight(frame, mapping, {"count_unit": "pessoas", "single_period_confirmed": True})["capabilities"]["counts"]["status"] == "available"


@pytest.mark.parametrize("lat,lon,count,expected", [
    (["-3,1", "-3"], ["-60,5", "-61"], ["1", "2"], "decimal_comma"),
    (["-3.1", "-3"], ["-60.5", "-61"], ["1", "2"], "decimal_point"),
    (["-3,1", "-3.2"], ["-60,5", "-61"], ["1", "2"], None),        # vírgula e ponto misturados
    (["-3,1", "-3"], ["-60,5", "-61"], ["1,5", "2"], None),        # vírgula também nas quantidades
    (["-3,1", "x"], ["-60,5", "-61"], ["1", "2"], None),           # valor não numérico
])
def test_decimal_separator_is_verified_in_the_data(lat, lon, count, expected):
    """Caso 8: separador verificado nos dados; só o formato misto continua uma escolha."""
    frame = pd.DataFrame({"municipio": ["A", "B"], "latitude": lat, "longitude": lon, "quantidade": count})
    mapping = {"territory": "municipio", "latitude": "latitude", "longitude": "longitude", "count": "quantidade"}
    assert verified_separator(frame, mapping) == expected


def test_out_of_range_coordinate_does_not_demote_the_column():
    """Caso 9: valor fora da faixa não impede o reconhecimento da coluna (RQ-DAD-25)."""
    frame = pd.DataFrame({"municipio": ["A", "B"], "latitude": ["-3,1", "-63741"], "longitude": ["-60,0", "-60,1"]})
    mapping, profiles = candidates(frame)
    assert mapping["latitude"] == "latitude" and mapping["longitude"] == "longitude"
    assert "1 valor(es) fora do intervalo" in profiles[1]["proposal"][0]["evidence"]
    assert coordinate_roles(frame, mapping, {}) == {"latitude", "longitude"}
    renamed = frame.rename(columns={"latitude": "y"})
    assert coordinate_roles(renamed, {**mapping, "latitude": "y"}, {}) == {"longitude"}  # nome fora do CFG-VOC: escolha


def test_rotation_marks_units_without_records_as_not_evaluable():
    """Caso 10: unidade sem registro em um dos períodos fica não avaliável (SEM_REGISTRO_OBSERVADO; CAP-ROT-01)."""
    raw = imported_csv(skip={("TEFE", 2024)})
    info = client.post("/api/inspect", files={"file": ("importada.csv", raw)}).json()
    mapping = {**info["suggested_mapping"], "territory_id": "cod_ibge"}
    assert mapping["identity"] == "id_profissional"
    response = post("/api/analyze", raw, mapping, "rotation", confirmed_roles=["territory_id"])
    assert response.status_code == 200, response.text
    rows = {row["Território"]: row for row in response.json()["rows"]}
    tefe = rows["TEFE [130420]"]
    assert tefe["Condição"] == "Não avaliável: sem registro observado em um dos períodos (SEM_REGISTRO_OBSERVADO)"
    assert (tefe["Rotatividade (%)"], tefe["Permanência (%)"], tefe["Saíram"]) == (None, None, None)
    assert rows["MANAUS [130260]"]["Condição"] == "Avaliável"
    assert response.json()["metadata"]["evaluability"]["status"] == "AVALIAVEL_COM_LIMITACOES"
    assert {"longitudinal_identity_confirmed", "cohort_coverage_confirmed"} <= set(response.json()["metadata"]["options"]["analysis_premises"])
    refused = post("/api/analyze", raw, mapping, "rotation", confirmed_roles=["territory_id"], cohort_coverage_confirmed=False)
    assert refused.status_code == 422


def test_suggestion_is_never_selection_for_every_role():
    """Garantia de segurança (R2): coluna indicada pela API sem regra e sem escolha continua bloqueada."""
    raw = imported_csv()
    info = client.post("/api/inspect", files={"file": ("importada.csv", raw)}).json()
    mapping = {**info["suggested_mapping"], "territory_id": "cod_ibge"}
    blocked = post("/api/analyze", raw, mapping, count_unit="pessoas", period_filter="202406")
    assert blocked.status_code == 422 and "Escolha a coluna" in blocked.json()["detail"]
    allowed = post("/api/analyze", raw, mapping, confirmed_roles=["territory_id"], count_unit="pessoas", period_filter="202406")
    assert allowed.status_code == 200, allowed.text
