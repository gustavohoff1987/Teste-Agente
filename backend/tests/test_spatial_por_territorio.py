"""Análise espacial com validade por território (RQ-DAD-25): coordenada ausente ou inválida deixa só aquele território
não avaliável; a referência inválida é um erro claro; coordenadas diferentes entre competências pedem a escolha de uma
competência. Dados sintéticos de upload, sem a camada complementar (que só vale na base Brasil)."""
import json

from fastapi.testclient import TestClient

from main import app

client = TestClient(app)
MAPPING = {"territory": "municipio", "territory_id": "codigo", "period": "periodo", "latitude": "latitude", "longitude": "longitude"}
BASE = {"confirmed_roles": list(MAPPING), "crs": "SIRGAS2000", "reference_territory": "ALFA [100001]"}


def csv(rows):
    lines = ["municipio;codigo;periodo;latitude;longitude"] + [";".join(row) for row in rows]
    return ("\n".join(lines) + "\n").encode("utf-8")


ROWS = [("ALFA", "100001", "202406", "-3.1", "-60.0"), ("BETA", "100002", "202406", "110", "-48.0"),
        ("GAMA", "100003", "202406", "", ""), ("DELTA", "100004", "202406", "-3.3", "-64.7"),
        ("EPSILON", "100005", "202406", "abc", "-50.0")]


def spatial(rows, **options):
    return client.post("/api/analyze", files={"file": ("espacial.csv", csv(rows))},
                       data={"operation": "spatial", "mapping": json.dumps(MAPPING), "options": json.dumps({**BASE, **options})})


def test_invalid_or_missing_coordinate_leaves_only_that_territory_not_evaluable():
    response = spatial(ROWS)
    assert response.status_code == 200, response.text
    body = response.json()
    rows = body["rows"]
    assert [row["Território"] for row in rows][:2] == ["ALFA [100001]", "DELTA [100004]"]  # calculados primeiro
    by_name = {row["Território"]: row for row in rows}
    assert by_name["ALFA [100001]"] == {"Território": "ALFA [100001]", "Distância (km)": 0.0, "Condição": "Avaliável"}
    assert by_name["DELTA [100004]"]["Distância (km)"] > 0 and by_name["DELTA [100004]"]["Condição"] == "Avaliável"
    assert by_name["BETA [100002]"] == {"Território": "BETA [100002]", "Distância (km)": None,
                                        "Condição": "Não avaliável: coordenada inválida"}
    assert by_name["EPSILON [100005]"]["Condição"] == "Não avaliável: coordenada inválida"  # não numérica
    assert by_name["GAMA [100003]"] == {"Território": "GAMA [100003]", "Distância (km)": None,
                                        "Condição": "Não avaliável: coordenada ausente"}
    assert all(row["Distância (km)"] is None for row in rows[2:])  # nunca zero; no fim da ordem
    assert body["metadata"]["evaluability"]["status"] == "AVALIAVEL_COM_LIMITACOES"
    assert any("3 território(s) sem coordenada válida" in note and "COORDENADA_INVALIDA" in note for note in body["notes"])
    geometry = body["metadata"]["representacao"]["geometria"]
    assert geometry["estado"] == "DISPONIVEL" and sorted(geometry["ids"]) == ["code:100001", "code:100004"]
    assert {item["id"]: item["condicao"] for item in geometry["sem_geometria"]} == {
        "code:100002": "INVALIDA", "code:100003": "AUSENTE", "code:100005": "INVALIDA"}


def test_all_valid_keeps_the_previous_rows_without_condition_column():
    response = spatial([ROWS[0], ROWS[3]])
    assert response.status_code == 200, response.text
    rows = response.json()["rows"]
    assert rows[0] == {"Território": "ALFA [100001]", "Distância (km)": 0.0}
    assert set(rows[1]) == {"Território", "Distância (km)"}


def test_reference_without_valid_coordinate_is_a_clear_error():
    response = spatial(ROWS, reference_territory="BETA [100002]")
    assert response.status_code == 422
    assert "O território de referência não tem coordenada válida" in response.json()["detail"]
    check = client.post("/api/preflight", files={"file": ("espacial.csv", csv(ROWS))},
                        data={"mapping": json.dumps(MAPPING), "options": json.dumps({**BASE, "reference_territory": "GAMA [100003]"})})
    assert check.status_code == 200, check.text
    capability = check.json()["capabilities"]["spatial"]
    assert capability["status"] == "unavailable"
    assert any("referência não tem coordenada válida" in reason for reason in capability["reasons"])


def test_coordinates_that_change_between_periods_ask_for_one_period():
    rows = [("ALFA", "100001", "202401", "-3.1", "-60.0"), ("ALFA", "100001", "202406", "-3.2", "-60.0"),
            ("DELTA", "100004", "202401", "-3.3", "-64.7"), ("DELTA", "100004", "202406", "-3.3", "-64.7")]
    response = spatial(rows)
    assert response.status_code == 422
    assert response.json()["detail"].endswith("Coordenadas conflitantes para o mesmo território entre competências. Escolha "
                                              "uma competência no período da análise.")
    chosen = spatial(rows, period_filter="202406")
    assert chosen.status_code == 200, chosen.text
    assert [row["Distância (km)"] for row in chosen.json()["rows"]][0] == 0.0


def test_comma_coordinates_with_the_decimal_point_remain_a_format_error():
    rows = [("ALFA", "100001", "202406", "-3,1", "-60,0"), ("DELTA", "100004", "202406", "-3,3", "-64,7")]
    refused = spatial(rows, number_format="decimal_point")
    assert refused.status_code == 422 and "não numéricos ou não finitos em latitude" in refused.json()["detail"]
    accepted = spatial(rows, number_format="decimal_comma")
    assert accepted.status_code == 200, accepted.text
