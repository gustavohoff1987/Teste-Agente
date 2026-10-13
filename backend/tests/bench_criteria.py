"""Tempos por fase dos critérios combinados com a base Brasil (arquivos versionados ou ADT_BRASIL_DATA_DIR).

Uso (raiz do repositório): python backend/tests/bench_criteria.py [--period 202406] [--json saida.json]
Cenário do pedido do usuário (valores não normativos): referências com densidade ≥ 2,36; critérios
densidade < 2,36 E distância > 155 km, com a cobertura parcial aceita explicitamente; ordenação por
distância decrescente e 20 primeiros. Fases medidas fora de uma requisição (sem memorização), com
mediana de 3 repetições: preparação (leitura e pré-exame), conjunto de referências, distâncias,
avaliação dos critérios, ranking e serialização; e a requisição completa pela API, inclusive a
repetição em que só um limiar derivado muda. Registra só tempos, tamanhos e contagens, nunca linhas.
"""
import argparse
import json
import statistics
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from fastapi.testclient import TestClient  # noqa: E402

import main  # noqa: E402
from brazil_catalog_profile import apply_curated_options  # noqa: E402
from brazil_data import load_brazil  # noqa: E402
from combined_criteria import Evaluator, criteria_inputs, evaluate, ranking_of, select_top  # noqa: E402
from nearest_reference import compute_nearest, nearest_inputs, reference_set  # noqa: E402
from semantic_bridge import preflight  # noqa: E402

DENSITY = {"attribute": "densidade", "operator": "<", "value": "2,36"}
DISTANCE = {"attribute": "distancia", "operator": ">", "value": "155"}


def median(function, repeat=3):
    times, value = [], None
    for _ in range(repeat):
        start = time.perf_counter()
        value = function()
        times.append(time.perf_counter() - start)
    return statistics.median(times), value


def main_(period, output):
    client = TestClient(main.app)
    info = client.post("/api/inspect", data={"dataset": "brazil", "scope": "municipal"}).json()
    curated, mapping = info["curated_defaults"], info["suggested_mapping"]
    options = {"confirmed_roles": curated["confirmed_roles"], "count_unit": curated["count_unit"], "fts_scope_confirmed": True,
               "object_confirmed": True, "population_denominator_confirmed": True, "category_filter": curated["category"],
               "period_filter": period, "number_format": "decimal_comma", "crs": "SIRGAS2000",
               "reference_mode": "criterion", "reference_criterion": {"operator": ">=", "value": "2,36"},
               "criteria": {"logic": "and", "operands": [DENSITY, DISTANCE]}, "distance_scope": "evaluable_references",
               "ranking": {"attribute": "distancia", "direction": "desc", "top_n": 20, "set": "atende"}}

    def frame():
        raw, filename, source = load_brazil("municipal", "criteria", info["source"]["version"])
        return main._brazil_frame(raw, filename, source)

    data = frame()
    settings = apply_curated_options(data, mapping, options)
    phases = {}
    phases["preparacao_leitura_s"], _ = median(frame)
    phases["preparacao_pre_exame_s"], _ = median(lambda: preflight(data, mapping, settings))
    phases["conjunto_referencias_s"], refs = median(lambda: reference_set(data, mapping, settings, period))
    inputs_time, _ = median(lambda: nearest_inputs(data, mapping, settings))
    nearest_time, nearest = median(lambda: compute_nearest(data, mapping, settings))
    phases["distancias_s"] = nearest_time - inputs_time  # busca exata e montagem do resultado de CAP-ESP-02
    inputs = criteria_inputs(data, mapping, settings)
    evaluator = Evaluator(data, mapping, settings, inputs)
    phases["avaliacao_criterios_s"], evaluations = median(lambda: evaluate(data, mapping, settings, inputs, evaluator))
    members = [item["elemento"] for item in evaluations if item["estado"] == "ATENDE"]
    values = evaluator.values("distancia")

    def rank():
        ordered, positions, _ = ranking_of(values, members, inputs["catalog"], "desc")
        return select_top(ordered, positions, 20, False)

    phases["ranking_s"], _ = median(rank)
    form = {"dataset": "brazil", "scope": "municipal", "dataset_version": info["source"]["version"],
            "mapping": json.dumps(mapping), "operation": "criteria"}
    request_time, response = median(lambda: client.post("/api/analyze", data={**form, "options": json.dumps(options)}))
    body = response.json()
    phases["serializacao_s"], text = median(lambda: json.dumps(body, ensure_ascii=False))
    changed = {**options, "criteria": {"logic": "and", "operands": [{**DENSITY, "value": "2"}, DISTANCE]}}
    changed_time, changed_response = median(lambda: client.post("/api/analyze", data={**form, "options": json.dumps(changed)}))
    structured = body["metadata"]["criterios"]
    report = {"periodo": period, "fases": {key: round(value, 4) for key, value in phases.items()},
              "requisicao_completa_s": round(request_time, 3), "requisicao_so_limiar_alterado_s": round(changed_time, 3),
              "resposta_mb": round(len(response.content) / 1e6, 2), "resposta_limiar_alterado_mb": round(len(changed_response.content) / 1e6, 2),
              "territorios": structured["universo"]["n"], "contagens": structured["contagens"],
              "referencias": len(refs["membros"]), "geodesicas_calculadas": nearest["structured"]["geodesicas_calculadas"],
              "pares_avaliaveis": nearest["structured"]["pares_avaliaveis"], "selecionados": len(structured["selecao"]["membros"]),
              "json_caracteres": len(text)}
    print(json.dumps(report, ensure_ascii=False, indent=2))
    if output:
        Path(output).write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--period", default="202406")
    parser.add_argument("--json")
    arguments = parser.parse_args()
    main_(arguments.period, arguments.json)
