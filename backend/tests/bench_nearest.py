"""Desempenho da referência mais próxima (Bloco 2, Etapa 1); nunca registra linhas da base.

Uso, na raiz do repositório:
    python backend/tests/bench_nearest.py --real-dir <pasta com as duas fontes>
    python backend/tests/bench_nearest.py            # coordenadas sintéticas espalhadas pelo Brasil
Para 3, 100, 1.000 e todos os alvos, contra 3 referências, as do critério (densidade ≥ 2,36 em
202406) e todas as avaliáveis: busca exata × exaustiva (mesmo resultado exigido), geodésicas
calculadas, tempo e pico de memória; depois a requisição completa pela API. O perfil real usa
cópias temporárias instaladas pelo instalador do projeto, removidas ao final.
"""
import argparse
import json
import os
import random
import resource
import sys
import tempfile
import time
import tracemalloc
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "backend"))
sys.path.insert(0, str(ROOT / "backend" / "tests"))
PERIOD = "202406"
SIZES = [3, 100, 1000, None]


def synthetic_catalog(destination):
    """5.570 municípios fictícios com coordenadas aleatórias no Brasil; valores sem significado real."""
    from openpyxl import Workbook
    from brazil_data import FILES
    from install_brazil_data import install
    rng = random.Random(11)
    rows = ["regiao_geografica;uf;municipio;cod_ibge;latitude;longitude;categoria_profissional;"
            "periodo_ano;periodo_mes;quantidade;população_estimada"]
    for n in range(5570):
        lat, lon = f"{rng.uniform(-33.7, 5.2):.6f}", f"{rng.uniform(-73.9, -34.8):.6f}"
        rows.append(f"Norte;AM;MUNICIPIO {n:04d};{130000 + n};{lat.replace('.', ',')};{lon.replace('.', ',')};"
                    f"MEDICINA;2024;6;{rng.randint(0, 60)};{rng.randint(800, 20000)}")
    with tempfile.TemporaryDirectory() as folder:
        book = Workbook()
        book.active.append(["pais", "periodo_ano", "periodo_mes", "categoria_profissional", "contagem"])
        book.active.append(["Brasil", 2024, 6, "MEDICINA", 500000])
        book.save(Path(folder) / FILES["national"])
        (Path(folder) / FILES["municipal"]).write_text("\n".join(rows) + "\n", encoding="utf-8")
        if "state" in FILES:  # fonte estadual (médicos únicos por UF), exigida desde 19/10/2026
            (Path(folder) / FILES["state"]).write_text("uf;periodo_ano;periodo_mes;categoria_profissional;contagem\r\n"
                                                       "AM;2024;6;MEDICINA;150000\r\n", encoding="utf-8")
        install(folder, destination, governed=False)  # fixture sintética


def measure(function, *args):
    tracemalloc.start()
    start = time.perf_counter()
    value = function(*args)
    elapsed = time.perf_counter() - start
    peak = tracemalloc.get_traced_memory()[1] / 2**20
    tracemalloc.stop()
    return value, elapsed, peak


def algorithm(report):
    import numpy as np
    from brazil_data import load_brazil
    from main import read_dataset
    from semantic_bridge import candidates
    from brazil_catalog_profile import apply_curated_options
    from nearest_reference import density_criterion, nearest_exact, nearest_exhaustive, territory_coordinates, _in_period
    raw, name, source = load_brazil("municipal")
    frame, _ = read_dataset(raw, name)
    frame.attrs["source"] = source
    mapping, _ = candidates(frame)
    options = {**apply_curated_options(frame, mapping, {}), "number_format": "decimal_comma", "category_filter": "MEDICINA"}
    coords = territory_coordinates(_in_period(frame, mapping, PERIOD), mapping, options)
    valid = coords[coords.condicao == "VALIDA"]
    from decimal import Decimal
    _, evaluation = density_criterion(frame, mapping, options, PERIOD, ">=", Decimal("2.36"))
    criterion = [item["id"] for item in evaluation if item["condicao"] == "ATENDE" and item["id"] in valid.index]
    reference_sets = {"3 referências": list(valid.index[:3]), f"critério ({len(criterion)})": criterion,
                      f"todas ({len(valid)})": list(valid.index)}
    print(f"territórios avaliáveis: {len(valid)} de {len(coords)}")
    for label, refs in reference_sets.items():
        r = valid.loc[refs]
        for size in SIZES:
            t = valid if size is None else valid.iloc[:size]
            (best, ties, evaluated), seconds, peak = measure(nearest_exact, t.lat, t.lon, r.lat, r.lon)
            pairs = len(t) * len(r)
            line = {"referencias": label, "alvos": len(t), "pares": pairs, "geodesicas": evaluated,
                    "exata_s": round(seconds, 4), "exata_pico_mib": round(peak, 1)}
            if pairs <= 12_000_000:
                (best2, ties2), seconds2, peak2 = measure(nearest_exhaustive, t.lat, t.lon, r.lat, r.lon)
                line.update(exaustiva_s=round(seconds2, 3), exaustiva_pico_mib=round(peak2, 1),
                            iguais=bool(np.array_equal(best, best2) and [sorted(x) for x in ties] == [sorted(x) for x in ties2]))
            report["algoritmo"].append(line)
            print(json.dumps(line, ensure_ascii=False), flush=True)


def api(report, repeat):
    from fastapi.testclient import TestClient
    import main
    client = TestClient(main.app)
    inspection = client.post("/api/inspect", data={"dataset": "brazil", "scope": "municipal"}).json()
    curated = inspection["curated_defaults"]
    ids = [item["id"] for item in inspection["preflight"]["territory_choices"]]
    base = {"dataset": "brazil", "scope": "municipal", "dataset_version": inspection["source"]["version"],
            "mapping": json.dumps(inspection["suggested_mapping"]), "operation": "nearest"}
    options = {"confirmed_roles": curated["confirmed_roles"], "count_unit": curated["count_unit"], "fts_scope_confirmed": True,
               "object_confirmed": True, "population_denominator_confirmed": True, "category_filter": curated["category"],
               "period_filter": PERIOD, "number_format": "decimal_comma", "crs": "SIRGAS2000",
               "reference_mode": "criterion", "reference_criterion": {"operator": ">=", "value": "2.36"}}
    for size in SIZES:
        settings = options if size is None else {**options, "territory_ids": ids[:size]}
        times, length = [], 0
        for _ in range(repeat):
            start = time.perf_counter()
            response = client.post("/api/analyze", data={**base, "options": json.dumps(settings)})
            times.append(time.perf_counter() - start)
            assert response.status_code == 200, response.text[:300]
            length = len(response.content)
        line = {"alvos": size or len(ids), "mediana_s": round(sorted(times)[len(times) // 2], 3),
                "max_s": round(max(times), 3), "resposta_kib": length // 1024}
        report["api"].append(line)
        print(json.dumps(line, ensure_ascii=False), flush=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--real-dir", type=Path)
    parser.add_argument("--repeat", type=int, default=3)
    parser.add_argument("--json", type=Path)
    args = parser.parse_args()
    os.environ["GEMINI_API_KEY"] = ""
    report = {"perfil": "real" if args.real_dir else "sintético", "algoritmo": [], "api": []}
    with tempfile.TemporaryDirectory(prefix="adt-nearest-") as folder:
        catalog = Path(folder) / "catalogo"
        if args.real_dir:
            from install_brazil_data import install
            install(args.real_dir, catalog)
        else:
            synthetic_catalog(catalog)
        os.environ["ADT_BRASIL_DATA_DIR"] = str(catalog)
        from brazil_data import catalog_version
        os.environ["ADT_BRASIL_DATA_VERSION"] = catalog_version(catalog)  # catálogo escolhido explicitamente
        algorithm(report)
        api(report, args.repeat)
    report["rss_max_mib"] = round(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024)
    print("RSS máximo do processo:", report["rss_max_mib"], "MiB")
    if args.json:
        args.json.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")


if __name__ == "__main__":
    main()
