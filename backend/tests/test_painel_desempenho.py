"""Desempenho do gráfico da página única sem mudar número nenhum (Docs/PAINEL_INTEGRADO.md, seção "Desempenho").

Cada atalho é conferido contra o caminho que ele substitui:
- variação em inteiros (painel._percent) = temporal_change.change sobre os Fraction, inclusive o float publicado;
- ordenação com os avaliáveis já na ordem (painel._ranked) = combined_criteria.ranking_of;
- linhas da competência pelas posições guardadas (painel._rows) = o filtro por máscara;
- distribuição em bloco (main._compute, operação distribution) = a montagem linha a linha de antes;
- reaproveitamento entre pedidos (painel._reaproveitar) = a mesma resposta calculada sem memória;
- compressão gzip e serialização da resposta: o mesmo corpo, byte a byte.
"""
import gzip
import json
import random
from fractions import Fraction

import numpy as np
import pandas as pd
from fastapi.responses import JSONResponse
from fastapi.testclient import TestClient

import main
import painel
import request_memo
from combined_criteria import ranking_of
from temporal_change import change
from test_painel_pagina import (BELEM, MANAUS, PARINTINS, PERIODS, TEFE, inspection, ok, page)
from test_painel_pagina import repo  # noqa: F401 (fixture)

client = TestClient(main.app)


def record(quantity, population):
    return {"valores": {"quantidade": quantity, "populacao": population,
                        "densidade": None if population in (None, 0) else quantity / population * 1000}}


def test_variation_in_integers_is_the_change_of_temporal_change():
    cases = [(30, 2000, 50, 2000), (0, 600, 6, 600), (20, 1000, 12, 1000), (4730, 2279686, 4511, 2251235),
             (3, 500, 0, 500), (2.5, 1000.0, 7.25, 1500.5), (10 ** 15 + 1, 10 ** 9, 10 ** 15 + 7, 10 ** 9 + 3),
             (1, 3, 2, 7), (5.0, 3.0, 5.0, 3.0)]
    for q0, p0, q1, p1 in cases:
        before, after = record(q0, p0), record(q1, p1)
        variation, ok_, motives, exact = painel._percentages(None, before, after)
        for field in painel.FIELDS3:
            a = Fraction(before["valores"][field]) if field != "densidade" else Fraction(q0) * 1000 / Fraction(p0)
            b = Fraction(after["valores"][field]) if field != "densidade" else Fraction(q1) * 1000 / Fraction(p1)
            expected = change(a, b)["variacao_percentual"]
            if expected is None:
                assert exact[field] is None and variation[field] is None
                assert any("(BASE_ZERO)" in motive for motive in motives)
                continue
            assert Fraction(*exact[field]) == expected  # o valor exato lido pela ordenação
            published = painel._num(float(expected))
            assert variation[field] == published and type(variation[field]) is type(published)
        assert painel._exact(before, "densidade") == Fraction(q0) * 1000 / Fraction(p0)


def test_presorted_ranking_is_ranking_of():
    rng = random.Random(23)
    third = Fraction(1, 3)
    pool = [Fraction(0), third, third + Fraction(1, 10 ** 30), third, Fraction(2), Fraction(-1, 7), Fraction(5, 2),
            Fraction(1, 10 ** 25), Fraction(0), Fraction(7, 3)]
    assert float(pool[1]) == float(pool[2]) and pool[1] != pool[2]  # mesmo float, frações diferentes
    for trial in range(60):
        members = ["k" + str(index) for index in range(40)]
        rng.shuffle(members)
        values, names = {}, {}
        for key in members:
            names[key] = {"name": rng.choice(["A", "B", "C"])}
            if rng.random() < 0.15:
                values[key] = {"avaliavel": False, "motivos": ["SEM_REGISTRO_OBSERVADO"]}
            else:
                exact = rng.choice(pool) + rng.choice([0, 0, Fraction(rng.randint(-9, 9), 4)])
                values[key] = {"avaliavel": True, "valor": float(exact), "exato": exact}
        for order in ("desc", "asc"):
            assert painel._ranked(values, members, names, order) == ranking_of(values, members, names, order)


def test_rows_of_the_competence_are_the_mask_filter():
    frame = pd.DataFrame({"periodo": ["202406", " 202406", None, "202306", "202406", "202306", ""],
                          "categoria": ["MEDICINA", "ENFERMAGEM", "MEDICINA", "MEDICINA", " MEDICINA", None, "MEDICINA"],
                          "valor": list(range(7))}, index=[10, 11, 12, 13, 14, 15, 16])
    mapping = {"period": "periodo", "category": "categoria"}

    def by_mask(periods, category, mapping):
        mask = painel.text_values(frame[mapping["period"]]).isin(list(periods))
        if mapping.get("category"):
            mask &= painel.text_values(frame[mapping["category"]]).isin([category])
        return frame.loc[mask.to_numpy(dtype=bool)]

    for periods in (["202406"], ["202306", "202406"], ["209912"], ["202406", "202406"]):
        for category in ("MEDICINA", "ENFERMAGEM", "OUTRA"):
            for fields in (mapping, {"period": "periodo"}):
                pd.testing.assert_frame_equal(painel._rows(frame, fields, periods, category),
                                              by_mask(periods, category, fields))


def test_distribution_in_block_is_the_row_by_row_assembly():
    data = pd.DataFrame({"territory": ["A [1]", "B [2]", "C [3]", "D [4]", "E [5]", "F [6]"],
                         "period": ["2024"] * 6, "category": ["X"] * 6,
                         "quantity": [5.0, 0.0, 12.0, 5.0, 7.0, 30.0],
                         "population": [1000.0, 800.0, np.nan, 1000.0, 350.0, 2000.0]})
    data["density"] = data["quantity"] / data["population"] * 1000
    options = {"distribution_indicator": "quantity", "quantile_count": 4, "population_denominator_confirmed": True}
    mapping = {"territory": "territorio", "period": "periodo", "category": "categoria", "count": "quantidade"}
    computed = main._compute(data, mapping, "distribution", options, prepared=data)
    # A montagem de antes, linha a linha (iterrows), com os mesmos cortes e posições.
    series = data["quantity"]
    cuts = main.distribution_cuts(series, 4)
    classes = np.searchsorted(cuts, series.to_numpy(), side="left") + 1
    overall = series.rank(method="min", ascending=True).astype(int).to_numpy()
    inside = series.groupby(classes).rank(method="min", ascending=True).astype(int).to_numpy()
    unit = main.count_unit_label(mapping, options)
    expected = []
    for pos, (_, row) in enumerate(data.iterrows()):
        expected.append({"Território": row["territory"], "Período": "2024", "Categoria": "X",
                         "Quintil": str(int(classes[pos])) + "º quartil", "Posição no quartil": int(inside[pos]),
                         "Posição geral": int(overall[pos]), "Quantidade de " + unit: float(row["quantity"]),
                         "Unidade de contagem": unit, "Quantidade": float(row["quantity"]),
                         "População": float(row["population"]) if pd.notna(row["population"]) else None})
    assert computed["detail_rows"] == expected
    assert [list(row) for row in computed["detail_rows"]] == [list(row) for row in expected]  # mesma ordem das colunas


def test_reuse_between_requests_never_changes_the_answer(repo, monkeypatch):
    info = inspection()
    reference = {"membros": [PARINTINS, BELEM]}
    sequence = [dict(referencia=reference, tendencia={"competencias": PERIODS}, grupos={"tipo": "quartis"},
                     condicoes=[{"atributo": "densidade", "operador": "<", "valor": 15},
                                {"atributo": "distancia_km", "operador": ">", "valor": 100}]),
                dict(referencia=reference, tendencia={"competencias": PERIODS}, grupos={"tipo": "quartis"},
                     ordenar={"atributo": "distancia_km", "ordem": "asc", "primeiros": 2}),
                dict(referencia={"membros": [MANAUS]}, tendencia={"competencias": PERIODS[-4:]}, faixas=[0, 10, 20],
                     faixas_distancia=[0, 100, 1000]),
                dict(competencia_inicial="202006", ordenar={"atributo": "variacao", "ordem": "desc"},
                     comparar=[MANAUS, TEFE]),
                dict(competencia="202206", referencia=reference, condicoes=[
                    {"atributo": "distancia_km", "operador": ">", "valor": 100}], grupos={"tipo": "quintis"}),
                dict(indicador="quantidade", referencia=reference, tendencia={"competencias": PERIODS},
                     conjuntos=[{"id": "c1", "rotulo": "Manaus e Tefé", "membros": [MANAUS, TEFE]}])]
    with_reuse = [ok(page(info, **options)) for options in sequence * 2]  # a segunda volta lê o que ficou guardado
    assert any(key[1] == "_reaproveitado" for key in request_memo._SHARED)
    assert with_reuse[:len(sequence)] == with_reuse[len(sequence):]
    # Sem o reaproveitamento (a base não fica guardada nem marcada): as mesmas respostas.
    monkeypatch.setenv("ADT_BRASIL_CACHE_MAX_MB", "0")
    main._BRAZIL_FRAMES.clear()
    request_memo.clear_shared()
    without = [ok(page(info, **options)) for options in sequence]
    assert not any(key[1] == "_reaproveitado" for key in request_memo._SHARED)
    assert without == with_reuse[:len(sequence)]


def test_large_answers_are_gzip_compressed_with_the_same_body():
    # Planilha com 2.500 distritos: a resposta do gráfico passa do tamanho mínimo da compressão (64 KB).
    lines = ["distrito;ano;categoria;quantidade;populacao"] + [
        "Distrito " + str(index).zfill(4) + ";2024;Enfermeiros;" + str(index % 50) + ";" + str(1000 + index)
        for index in range(2500)]
    contents = ("\n".join(lines) + "\n").encode()
    mapping = {"territory": "distrito", "period": "ano", "category": "categoria", "count": "quantidade",
               "population": "populacao"}
    options = {"nivel": "municipios", "indicador": "densidade", "competencia": "2024",
               "premissas": {"count_unit": "pessoas"}, "base": {"municipios": {"todos": True}}}

    def send(encoding):
        return client.post("/api/painel", files={"file": ("grande.csv", contents)}, headers={"Accept-Encoding": encoding},
                           data={"mapping": json.dumps(mapping), "options": json.dumps(options)})

    plain, compressed = send("identity"), send("gzip")
    assert plain.status_code == compressed.status_code == 200, plain.text[:2000]
    assert len(plain.content) > 64 * 1024 and "content-encoding" not in plain.headers
    assert compressed.headers["content-encoding"] == "gzip"
    assert compressed.num_bytes_downloaded < len(plain.content) / 3
    assert compressed.content == plain.content  # descomprimido, o mesmo corpo, byte a byte
    assert len(compressed.json()["itens"]) == 2500
    small = client.get("/api/health", headers={"Accept-Encoding": "gzip"})
    assert "content-encoding" not in small.headers  # abaixo do tamanho mínimo, sem compressão
    assert gzip.decompress(gzip.compress(plain.content, compresslevel=1)) == plain.content


def test_panel_json_renders_the_same_bytes():
    body = {"itens": [{"id": "code:130260", "rotulo": "MANAUS (AM)", "densidade": 2.074847150002237, "nada": None,
                       "texto": "Ação — 1/3", "lista": [1, 2.5, "x"]}], "contagem": 5570}
    assert main._PanelJSON(body).body == JSONResponse(body).body
