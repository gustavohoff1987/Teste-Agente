"""Medição do gráfico da página única (POST /api/painel e /api/painel/mapa) com a base versionada; não é teste.

Uso, na raiz do repositório (somente leitura da base versionada; nenhuma linha da base é impressa):
    ADT_AQUECIMENTO=0 python backend/tests/bench_painel.py [--repeat 3] [--json saida.json] [--comparar antes.json]

Os casos são os da tabela "Desempenho" de Docs/PAINEL_INTEGRADO.md. Para cada caso: o tempo do primeiro pedido no
processo e a mediana de `--repeat` pedidos seguintes, pelo servidor de teste (TestClient, como o navegador: aceita gzip),
sem o aquecimento da base; o tamanho da resposta (JSON) e o tamanho transferido (comprimido, quando há gzip).

Nenhum número pode mudar entre versões do código: cada corpo vira um SHA-256 canônico (JSON com as chaves ordenadas), sem
os campos voláteis (sessao.result_id) e sem os campos acrescentados depois da medição de referência (`resumo`, que não muda
número nenhum). `--comparar` confere esses SHA-256 com os de uma medição anterior e falha se algum mudou. Os arquivos da base
são conferidos (SHA-256) antes e depois.
"""
import argparse
import hashlib
import json
import os
import statistics
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "backend"))
os.environ.setdefault("ADT_AQUECIMENTO", "0")
PERIOD = "202406"
INITIAL = "202306"
MANAUS, TEFE = "code:130260", "code:130420"
JUNE = [str(year) + "06" for year in range(2014, 2025)]
ALL = [str(year) + month for year in range(2014, 2025) for month in ("01", "06")]
TODOS = {"municipios": {"todos": True}}
CONDICOES = [{"atributo": "densidade", "operador": "<", "valor": 1},
             {"atributo": "distancia_km", "operador": ">", "valor": 150}]
PAGE = {"nivel": "municipios", "indicador": "densidade", "competencia": PERIOD}
# Campos que não entram no SHA-256 canônico: voláteis e acrescentados depois da medição de referência.
NEW_FIELDS = ("resumo",)
CASES = {
    "Contrato de 21/10: todos os municípios, variação e referência":
        ("/api/painel", {"competencia": PERIOD, "competencia_inicial": INITIAL, "base": TODOS,
                         "referencia": {"membros": [MANAUS]}}, False),
    "Página única: todos os municípios, distribuição": ("/api/painel", {**PAGE, "base": TODOS}, False),
    "Página única: 27 estados (E1)": ("/api/painel", {**PAGE, "nivel": "estados"}, False),
    "Página única: 27 estados, tendência de 11 junhos e quartis":
        ("/api/painel", {**PAGE, "nivel": "estados", "tendencia": {"competencias": JUNE}, "grupos": {"tipo": "quartis"}},
         False),
    "Página única: Amazonas (62), tendência de 11 junhos e condições":
        ("/api/painel", {**PAGE, "base": {"municipios": {"estados": ["13"]}}, "referencia": {"membros": [MANAUS]},
                         "tendencia": {"competencias": JUNE}, "condicoes": CONDICOES}, False),
    "Página única: todos, tendência de 11 junhos e condições":
        ("/api/painel", {**PAGE, "base": TODOS, "referencia": {"membros": [MANAUS]}, "tendencia": {"competencias": JUNE},
                         "condicoes": CONDICOES}, False),
    "Página única: todos, tendência de 22 competências e condições":
        ("/api/painel", {**PAGE, "base": TODOS, "referencia": {"membros": [MANAUS]}, "tendencia": {"competencias": ALL},
                         "condicoes": CONDICOES}, False),
    "Página única: todos, com tudo (variação, tendência, quintis, faixas, faixas de distância, condições, ordenação e "
    "comparação)":
        ("/api/painel", {**PAGE, "base": TODOS, "competencia_inicial": INITIAL, "referencia": {"membros": [MANAUS]},
                         "tendencia": {"competencias": JUNE}, "grupos": {"tipo": "quintis"}, "faixas": [0, 1, 2, 5, 50],
                         "faixas_distancia": [0, 100, 500, 1000, 5000], "condicoes": CONDICOES,
                         "ordenar": {"atributo": "densidade", "ordem": "desc", "primeiros": 10},
                         "comparar": [MANAUS, TEFE]}, False),
    "Página única: todos, tendência de 11 junhos e condições, com sessão":
        ("/api/painel", {**PAGE, "base": TODOS, "referencia": {"membros": [MANAUS]}, "tendencia": {"competencias": JUNE},
                         "condicoes": CONDICOES}, True),
    "Mapa: coordenadas de todos os municípios": ("/api/painel/mapa", {"competencia": PERIOD}, False),
}


def canonical(body):
    """SHA-256 do corpo sem os campos voláteis e os acrescentados depois da medição de referência."""
    if isinstance(body, dict):
        body = {key: value for key, value in body.items() if key not in NEW_FIELDS}
        if isinstance(body.get("sessao"), dict):
            body["sessao"] = {**body["sessao"], "result_id": None}
    text = json.dumps(body, sort_keys=True, ensure_ascii=False, separators=(",", ":"), allow_nan=False)
    return hashlib.sha256(text.encode()).hexdigest()


def megabytes(size):
    return "< 0,1 MB" if size < 100_000 else f"{size / 1e6:.1f} MB".replace(".", ",")


def seconds(value):
    return f"{value:.2f} s".replace(".", ",")


def run(args):
    data = [ROOT / name for name in ("Dados_Brasil.xlsx", "Dados_Estados_Brasil.csv", "Dados_Municipios_Brasil.csv")]
    data += sorted((ROOT / "dados" / "brasil").glob("*"))
    before = {str(path): hashlib.sha256(path.read_bytes()).hexdigest() for path in data if path.is_file()}
    from fastapi.testclient import TestClient
    import main
    client = TestClient(main.app)
    start = time.perf_counter()
    info = client.post("/api/inspect", data={"dataset": "brazil", "scope": "municipal"}).json()
    print("Inspeção da base (carga do processo): " + seconds(time.perf_counter() - start), flush=True)
    form = {"dataset": "brazil", "scope": "municipal", "dataset_version": info["source"]["version"],
            "context_revision": "0", "mapping": json.dumps(info["suggested_mapping"])}
    token = client.post("/api/session").json()["token"]
    out = {}
    for name, (path, options, session) in CASES.items():
        headers = {"X-ADT-Session": token} if session else {}
        samples, body, status, wire, size, encoding = [], None, None, None, None, None
        for _ in range(1 + args.repeat):
            begin = time.perf_counter()
            response = client.post(path, headers=headers, data={**form, "options": json.dumps(options)})
            samples.append(time.perf_counter() - begin)
            status, body = response.status_code, response.json()
            wire, size = response.num_bytes_downloaded, len(response.content)
            encoding = response.headers.get("content-encoding")
        if status != 200:
            print(name + ": HTTP " + str(status) + " " + json.dumps(body, ensure_ascii=False)[:300], flush=True)
        out[name] = {"status": status, "primeiro": samples[0], "mediana": statistics.median(samples[1:]),
                     "amostras": samples, "bytes": size, "transferidos": wire, "codificacao": encoding,
                     "sha256": canonical(body), "resumo": (body.get("resumo") or {}).get("texto")
                     if isinstance(body, dict) else None}
        print(f"{name[:100]:100} {seconds(out[name]['mediana'])} ({seconds(samples[0])})  {megabytes(size)}"
              f"  transferidos {megabytes(wire)} {encoding or ''}", flush=True)
    after = {str(path): hashlib.sha256(path.read_bytes()).hexdigest() for path in data if path.is_file()}
    print("Base intacta (SHA-256 antes e depois): " + ("sim" if before == after else "NÃO"), flush=True)
    if before != after:
        raise SystemExit(1)
    if args.json:
        Path(args.json).write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")
    if args.comparar:
        reference = json.loads(Path(args.comparar).read_text(encoding="utf-8"))
        # Rota que não existia na medição de referência (404): caso novo, sem corpo anterior a comparar.
        new = [name for name in out if name in reference and reference[name]["status"] == 404]
        changed = [name for name in out if name in reference and name not in new and
                   reference[name]["sha256"] != out[name]["sha256"]]
        for name in out:
            if name in reference:
                state = "NOVO" if name in new else "IGUAL" if name not in changed else "DIFERENTE"
                print(f"{name[:100]:100} antes {seconds(reference[name]['mediana'])} ({seconds(reference[name]['primeiro'])})"
                      f" depois {seconds(out[name]['mediana'])} ({seconds(out[name]['primeiro'])})  corpo {state}",
                      flush=True)
        if changed:
            print("Corpos diferentes da medição anterior: " + "; ".join(changed), flush=True)
            raise SystemExit(1)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--repeat", type=int, default=3)
    parser.add_argument("--json")
    parser.add_argument("--comparar")
    run(parser.parse_args())
