"""Medição reproduzível da latência da API; nunca registra linhas da base.

Uso, na raiz do repositório:
    python backend/tests/bench_latency.py --profile small
    python backend/tests/bench_latency.py --profile national
    python backend/tests/bench_latency.py --profile real --real-dir <pasta com as duas fontes>
Opções: --repeat N, --json saida.json, --cold (primeira requisição de cada operação
em processo novo), --backend <pasta backend> para medir outra versão do código.

Perfis sintéticos são gerados em pastas temporárias. O perfil real instala cópias
temporárias com o instalador do projeto (originais preservados) e as remove ao final.
Somente tempos, tamanhos, memória e contagens são impressos.
"""
import argparse
import csv
import hashlib
import json
import os
import platform
import random
import resource
import shutil
import statistics
import subprocess
import sys
import tempfile
import time
import tracemalloc
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
PERIOD = "202406"
TRIO = ["code:130260", "code:130420", "code:130340"]
MESSAGE = "Mostre a densidade médica dos municípios do Amazonas em junho de 2024."
UF = {"11": ("RO", "Norte"), "12": ("AC", "Norte"), "13": ("AM", "Norte"), "14": ("RR", "Norte"),
      "15": ("PA", "Norte"), "16": ("AP", "Norte"), "17": ("TO", "Norte"), "21": ("MA", "Nordeste"),
      "22": ("PI", "Nordeste"), "23": ("CE", "Nordeste"), "24": ("RN", "Nordeste"), "25": ("PB", "Nordeste"),
      "26": ("PE", "Nordeste"), "27": ("AL", "Nordeste"), "28": ("SE", "Nordeste"), "29": ("BA", "Nordeste"),
      "31": ("MG", "Sudeste"), "32": ("ES", "Sudeste"), "33": ("RJ", "Sudeste"), "35": ("SP", "Sudeste"),
      "41": ("PR", "Sul"), "42": ("SC", "Sul"), "43": ("RS", "Sul"), "50": ("MS", "Centro-Oeste"),
      "51": ("MT", "Centro-Oeste"), "52": ("GO", "Centro-Oeste"), "53": ("DF", "Centro-Oeste")}


def national_fixture(destination):
    """5.570 municípios fictícios x 22 competências, com uf e região; valores sem significado real."""
    from openpyxl import Workbook
    from brazil_data import FILES
    from install_brazil_data import install
    rng = random.Random(7)
    units = [("MANAUS", "130260"), ("TEFE", "130420"), ("PARINTINS", "130340")]
    used, n = {code for _, code in units}, 0
    while len(units) < 5570:
        code = list(UF)[n % len(UF)] + str(1000 + n).zfill(4)
        n += 1
        if code not in used:
            used.add(code)
            units.append(("MUNICIPIO " + str(n).zfill(4), code))
    periods = [(2023 + m // 12, m % 12 + 1) for m in range(22)]
    rows = ["regiao_geografica;uf;municipio;cod_ibge;latitude;longitude;categoria_profissional;"
            "periodo_ano;periodo_mes;quantidade;população_estimada"]
    for name, code in units:
        uf, region = UF[code[:2]]
        population, base = rng.randint(800, 900000), rng.randint(0, 900)
        rows += [f"{region};{uf};{name};{code};-10;-50;MEDICINA;{y};{m};{base + m};{population}" for y, m in periods]
    with tempfile.TemporaryDirectory() as folder:
        book = Workbook()
        book.active.append(["pais", "periodo_ano", "periodo_mes", "categoria_profissional", "contagem"])
        for y, m in periods:
            book.active.append(["Brasil", y, m, "MEDICINA", 500000 + m])
        book.save(Path(folder) / FILES["national"])
        (Path(folder) / FILES["municipal"]).write_text("\n".join(rows) + "\n", encoding="utf-8")
        if "state" in FILES:  # fonte estadual (médicos únicos por UF), exigida desde 19/10/2026
            lines = ["uf;periodo_ano;periodo_mes;categoria_profissional;contagem"] + [
                f"{uf};{y};{m};MEDICINA;{1000 + m}" for uf, _ in sorted(set(UF.values())) for y, m in periods]
            (Path(folder) / FILES["state"]).write_text("\r\n".join(lines) + "\r\n", encoding="utf-8")
        install(folder, destination, governed=False)  # fixture sintética


def build_catalog(profile, real_dir, destination):
    if profile == "small":
        sys.path.insert(0, str(ROOT / "backend" / "tests"))
        from prepare_block1_catalog import prepare
        prepare(destination)
    elif profile == "national":
        national_fixture(destination)
    else:
        from install_brazil_data import install
        install(real_dir, destination)


def percentile(values, q):
    ordered = sorted(values)
    return ordered[max(0, min(len(ordered) - 1, -(-len(ordered) * q // 100) - 1))]


class Bench:
    def __init__(self, catalog, cold=False):
        from fastapi.testclient import TestClient
        import main
        self.client = TestClient(main.app)
        if cold:
            # A operação medida deve ser a primeira requisição do processo.
            from brazil_catalog_profile import FIELDS
            manifest = json.loads((catalog / "manifest.json").read_text(encoding="utf-8"))
            self.version = hashlib.sha256(json.dumps(manifest["sha256"], sort_keys=True).encode()).hexdigest()
            self.mapping = json.dumps(FIELDS["municipal"])
            self.national = json.dumps(FIELDS["national"])
            with open(catalog / "Dados_Municipios_Brasil.csv", encoding="utf-8", newline="") as handle:
                self.state = sorted({"code:" + row["cod_ibge"].strip() for row in csv.DictReader(handle, delimiter=";")
                                     if row["cod_ibge"].strip().startswith("13")})
            self.counts = {}
            return
        inspection = self.post("/api/inspect", {"dataset": "brazil", "scope": "municipal"})[1].json()
        self.version = inspection["source"]["version"]
        self.mapping = json.dumps(inspection["suggested_mapping"])
        self.national = json.dumps(self.post("/api/inspect", {"dataset": "brazil", "scope": "national"})[1].json()["suggested_mapping"])
        self.state = [item["id"] for item in inspection["preflight"]["territory_choices"] if item["state"] == "AM"]
        self.counts = {"territórios": len(inspection["preflight"]["territory_choices"]), "AM": len(self.state),
                       "linhas": inspection["row_count"]}

    def post(self, path, data):
        start = time.perf_counter()
        response = self.client.post(path, data=data)
        return time.perf_counter() - start, response

    def operations(self):
        base = {"dataset": "brazil", "scope": "municipal", "dataset_version": self.version, "mapping": self.mapping}
        period = {"period_filter": PERIOD}
        three = {**period, "territory_ids": TRIO}

        def analyze(operation, options):
            return "/api/analyze", {**base, "operation": operation, "options": json.dumps(options)}
        return {
            "inspect_municipal": ("/api/inspect", {"dataset": "brazil", "scope": "municipal"}),
            "inspect_national": ("/api/inspect", {"dataset": "brazil", "scope": "national"}),
            # Primeiro pré-exame da interface após o inspect: sem período, sobre todas as competências.
            "preflight_sem_periodo": ("/api/preflight", {**base, "options": json.dumps({"category_filter": "MEDICINA"})}),
            "preflight_sem_selecao": ("/api/preflight", {**base, "options": json.dumps(period)}),
            "preflight_selecao_AM": ("/api/preflight", {**base, "options": json.dumps({**period, "territory_ids": self.state})}),
            "preflight_selecao_3": ("/api/preflight", {**base, "options": json.dumps(three)}),
            "exploracao_AM": ("/api/exploration/interpret", {**base, "message": MESSAGE, "options": json.dumps(period)}),
            "densidade_sem_selecao": analyze("density", period),
            "densidade_selecao_AM": analyze("density", {**period, "territory_ids": self.state}),
            "comparacao_3": analyze("comparisons", {**three, "comparison_confirmed": True}),
            "evolucao_3": analyze("temporal", {"territory_ids": TRIO, "temporal_indicator": "density",
                                               "temporal_comparability_confirmed": True,
                                               "territory_longitudinal_confirmed": True}),
            "agregacao_3": analyze("aggregate", {**three, "population_additive_confirmed": True,
                                                 "component_sum_confirmed": True}),
            "quantitativos_nacional": ("/api/analyze", {"dataset": "brazil", "scope": "national",
                                                        "dataset_version": self.version, "operation": "counts",
                                                        "mapping": self.national, "options": json.dumps(period)}),
            # Rota de níveis (Abr §7.3): Brasil (BR-POP-JUNHO-1), um estado (fonte estadual, população UF-POP-MUNICIPIOS-1)
            # e todos os municípios.
            "niveis_densidade_br_sp_todos": ("/api/analyze", {
                **base, "scope": "auto", "operation": "density", "options": json.dumps({
                    **period, "abrangencia": {"brasil": True, "estados": ["35"], "municipios": {"todos": True}}})}),
        }


def components(repeat):
    """Componentes internos do caminho Brasil municipal, medidos sem HTTP."""
    import pandas as pd
    from fastapi.encoders import jsonable_encoder
    from brazil_data import load_brazil
    from main import read_dataset, compute
    from semantic_bridge import candidates, preflight
    from brazil_catalog_profile import apply_curated_options
    from territorial_selection import territory_catalog
    raw, name, source = load_brazil("municipal")
    frame, _ = read_dataset(raw, name)
    frame.attrs["source"] = source
    mapping, _ = candidates(frame)
    options = apply_curated_options(frame, mapping, {"period_filter": PERIOD})
    report = preflight(frame, mapping, options)
    steps = {
        "load_brazil (leitura + SHA-256 das duas fontes)": lambda: load_brazil("municipal"),
        "read_dataset (CSV municipal)": lambda: read_dataset(raw, name),
        "candidates (perfil das colunas)": lambda: candidates(frame),
        "territory_catalog (quadro completo)": lambda: territory_catalog(frame, mapping, options),
        "preflight (função)": lambda: preflight(frame, mapping, options),
        "compute densidade (função)": lambda: compute(frame, mapping, "density", options),
        "hash_pandas_object (data_sha256)": lambda: pd.util.hash_pandas_object(frame, index=True).values.tobytes(),
        "jsonable_encoder + json (resposta do preflight)": lambda: json.dumps(jsonable_encoder(report)),
    }
    out = {}
    for label, step in steps.items():
        samples = []
        for _ in range(repeat):
            start = time.perf_counter()
            step()
            samples.append(time.perf_counter() - start)
        out[label] = {"median": statistics.median(samples), "p95": percentile(samples, 95)}
    out["memória do DataFrame municipal (MiB)"] = {"value": frame.memory_usage(deep=True).sum() / 2**20}
    return out


def run(args):
    bench = Bench(Path(os.environ["ADT_BRASIL_DATA_DIR"]), cold=bool(args.single))
    ops = bench.operations()
    if args.single:
        path, data = ops[args.single]
        elapsed, response = bench.post(path, data)
        print(json.dumps({"op": args.single, "first": elapsed, "status": response.status_code}))
        return
    results = {}
    for name, (path, data) in ops.items():
        if args.only and name not in args.only.split(","):
            continue
        samples, size, status = [], 0, None
        for _ in range(args.repeat):
            elapsed, response = bench.post(path, data)
            samples.append(elapsed)
            size, status = len(response.content), response.status_code
        peak = float("nan")
        if not args.no_memory:
            tracemalloc.start()
            bench.post(path, data)
            peak = tracemalloc.get_traced_memory()[1] / 2**20
            tracemalloc.stop()
        results[name] = {"first": samples[0], "median": statistics.median(samples), "p95": percentile(samples, 95),
                         "kib": size / 1024, "peak_mib": peak, "status": status}
        print(f"{name:<24} {status} primeiro={samples[0]:6.3f}s mediana={results[name]['median']:6.3f}s "
              f"p95={results[name]['p95']:6.3f}s resposta={size / 1024:8.1f} KiB pico={peak:7.1f} MiB", flush=True)
    comp = {} if args.only else components(max(3, min(args.repeat, 7)))
    for label, value in comp.items():
        print(f"  {label:<52} " + (f"mediana={value['median']:6.3f}s p95={value['p95']:6.3f}s" if "median" in value
                                    else f"{value['value']:8.1f}"), flush=True)
    rss = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024
    print(f"RSS máximo do processo: {rss:.0f} MiB | contagens: {bench.counts}")
    return {"operations": results, "components": comp, "rss_max_mib": rss, "counts": bench.counts}


def child(args, catalog, *extra):
    """Mede num processo novo que só importa o backend indicado (sem contaminação de módulos)."""
    command = [sys.executable, __file__, "--profile", args.profile, "--backend", str(args.backend),
               "--catalog", str(catalog), "--repeat", str(args.repeat), *(["--no-memory"] if args.no_memory else []),
               *(["--only", args.only] if args.only else []), *extra]
    return subprocess.run(command, capture_output=True, text=True, check=True).stdout


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--profile", choices=["small", "national", "real"], required=True)
    parser.add_argument("--real-dir", type=Path)
    parser.add_argument("--repeat", type=int)
    parser.add_argument("--json", type=Path)
    parser.add_argument("--cold", action="store_true")
    parser.add_argument("--no-memory", action="store_true", help="omite a passada de tracemalloc (mais rápida)")
    parser.add_argument("--only", help="operações separadas por vírgula (omite componentes)")
    parser.add_argument("--backend", type=Path, default=ROOT / "backend")
    parser.add_argument("--catalog", type=Path, help=argparse.SUPPRESS)
    parser.add_argument("--single", help=argparse.SUPPRESS)
    parser.add_argument("--report", type=Path, help=argparse.SUPPRESS)
    args = parser.parse_args()
    args.repeat = args.repeat or (25 if args.profile == "small" else 7)
    args.backend = args.backend.resolve()
    os.environ["GEMINI_API_KEY"] = ""  # somente neste processo
    if args.catalog:
        sys.path.insert(0, str(args.backend))
        os.environ["ADT_BRASIL_DATA_DIR"] = str(args.catalog)
        from brazil_data import catalog_version
        os.environ["ADT_BRASIL_DATA_VERSION"] = catalog_version(args.catalog)  # catálogo escolhido explicitamente
        result = run(args)
        if args.report and result:
            args.report.write_text(json.dumps(result, ensure_ascii=False), encoding="utf-8")
        return
    if args.profile == "real" and not args.real_dir:
        parser.error("--real-dir é obrigatório no perfil real")
    folder = Path(tempfile.mkdtemp(prefix="adt-bench-"))
    try:
        sys.path.insert(0, str(args.backend))
        build_catalog(args.profile, args.real_dir, folder / "catalogo")
        meta = {"profile": args.profile, "repeat": args.repeat, "python": platform.python_version(),
                "cpus": os.cpu_count(), "backend": str(args.backend)}
        print(json.dumps(meta, ensure_ascii=False), flush=True)
        if args.cold:
            cold = {}
            for name in ["inspect_municipal", "preflight_sem_periodo", "preflight_sem_selecao", "preflight_selecao_AM", "exploracao_AM",
                         "densidade_selecao_AM", "comparacao_3", "evolucao_3", "agregacao_3", "quantitativos_nacional"]:
                cold[name] = json.loads(child(args, folder / "catalogo", "--single", name).strip().splitlines()[-1])
                print(f"frio {name:<24} {cold[name]['status']} {cold[name]['first']:6.3f}s", flush=True)
            report = {"meta": meta, "cold": cold}
        else:
            print(child(args, folder / "catalogo", "--report", str(folder / "report.json")), end="", flush=True)
            report = {"meta": meta, **json.loads((folder / "report.json").read_text(encoding="utf-8"))}
        if args.json:
            args.json.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
    finally:
        shutil.rmtree(folder, ignore_errors=True)


if __name__ == "__main__":
    main()
