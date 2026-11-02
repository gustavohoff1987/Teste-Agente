"""Medições do contêiner nas condições do Cloud Run (seção 8 do comando de implantação de 01/11/2026; job "conteiner" do ci.yml).

Usa a imagem já construída (--imagem), sem enviá-la a registro. Cada contêiner roda com --cpus=1 --memory=2g --memory-swap=2g
(sem swap) e /tmp em tmpfs dentro do limite de memória (no Cloud Run, o sistema de arquivos gravável fica na memória), na
rede do runner, com o Gemini simulado por HTTP (backend/tests/serve_gemini_http.py) na mesma máquina e uma chave de teste.

Mede e confere:
- partida: limites lidos no cgroup (cpu.max, memory.max, swap), /tmp em memória, tempo até a porta abrir e até /api/health,
  o aquecimento (base do Brasil e biblioteca conversacional, pelo log), a carga de cada componente e a memória;
- análises: cada família pelo HTTP do contêiner, idêntica à referência em processo (o mesmo código e as mesmas versões fixadas
  que os testes com dados reais conferem), com tempo, memória, pico e tamanho das respostas (limite de 32 MiB do HTTP/1);
- planilhas: CSV e XLSX pequenos, médios, de 14,9 MB, de 15.000.000 e de 15.000.001 bytes e maiores; XLSX malformado,
  truncado e com expansão desproporcional; dois envios simultâneos de 14,9 MB; memória na leitura, na interpretação
  (/api/inspect) e no processamento com a geração do resultado (/api/painel);
- sessões pela API: a consulta não renova, a interação renova, o encerramento é imediato, o reinício perde as sessões; o tempo
  de cada consulta e de cada pré-verificação do CORS (base do custo faturável);
- memória das sessões: os resultados do gráfico guardados até o teto total (256 MiB em JSON; cada sessão guarda os 8 mais
  recentes, abaixo dos 32 MiB por sessão), a memória real e, com as sessões cheias, os envios de planilha (CSV de 14,9 MB,
  XLSX de 15.000.000 bytes e dois desses XLSX ao mesmo tempo);
- Gemini simulado: sucesso, demora, tempo esgotado (75 s), 5xx, 401/403, chave inválida, 429 por minuto e por dia no formato
  real (RetryInfo e QuotaFailure), saída fora do contrato (regeneração) e o motor funcionando sem o Gemini; chamadas contadas
  por /api/llm/status;
- concorrência: 1, 5, 10 e 20 usuários simulados (abertura, análises leves e pesadas, planilha e conversa com o Gemini
  simulado de 2 a 20 s; a abertura em paralelo e a consulta da sessão a cada 30 s, como na página), com as vagas padrão (2) e
  com 1 vaga; latência, fila, ocupados, pedidos simultâneos (base da concorrência do Cloud Run), latência de /api/health
  durante as operações pesadas e memória;
- gravações fora de /tmp (docker diff) e o encerramento limpo com SIGTERM.

Saída: medicoes.json e medicoes.md em --saida (artefato do job). Sai com 1 se algum requisito falhou.
Limitações: a CPU do runner não é a vCPU do Google; não reproduz a restrição de CPU entre requisições, a partida a frio real,
a rede nem o escalonamento do Cloud Run. Nada medido aqui é confirmação na nuvem.
"""
import argparse
import concurrent.futures
import json
import os
import platform
import random
import re
import socket
import statistics
import subprocess
import sys
import tempfile
import threading
import time
from datetime import datetime, timezone
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(RAIZ / "backend"), str(RAIZ / "backend" / "tests"), str(Path(__file__).resolve().parent)]
os.environ["GEMINI_API_KEY"] = ""  # a referência em processo nunca chama o provedor nem lê backend/.env
os.environ["ADT_AQUECIMENTO"] = "0"

import httpx  # noqa: E402
import planilhas_de_teste as P  # noqa: E402
import serve_gemini_http  # noqa: E402

PORTA = 18090
PORTA_GEMINI = 18300
URL = f"http://127.0.0.1:{PORTA}"
ORIGEM = "http://127.0.0.1:18101"
MIB = 1024 * 1024
LIMITE_HTTP1 = 32 * MIB
LIMITE_MEMORIA = 2 * 1024 ** 3
VOLATEIS = {"result_id", "created_at"}
ROTULOS = {"unidade": {"singular": "território", "plural": "territórios"}, "grupo": {"singular": "grupo", "plural": "grupos"}}
LIMITACOES = ("A CPU do runner do GitHub não é a vCPU do Google; o teste não reproduz a restrição de CPU entre requisições "
              "(cobrança por requisição), a partida a frio real, a rede, o balanceador nem o escalonamento do Cloud Run. Nada "
              "medido aqui é apresentado como confirmado na nuvem.")


def docker(*args, check=True, timeout=600) -> str:
    feito = subprocess.run(["docker", *args], capture_output=True, text=True, timeout=timeout)
    if check and feito.returncode != 0:
        raise RuntimeError("docker " + " ".join(args[:3]) + ": " + (feito.stderr or feito.stdout)[-1500:])
    return feito.stdout


def porta_aberta() -> bool:
    with socket.socket() as sock:
        sock.settimeout(0.5)
        return sock.connect_ex(("127.0.0.1", PORTA)) == 0


def mb(valor) -> float | None:
    return None if valor is None else round(valor / MIB, 1)


def percentis(valores: list[float]) -> dict:
    if not valores:
        return {"n": 0}
    ordenados = sorted(valores)
    def p(q):
        return round(ordenados[min(len(ordenados) - 1, int(q * (len(ordenados) - 1) + 0.5))], 3)
    return {"n": len(valores), "p50": p(0.5), "p95": p(0.95), "max": round(ordenados[-1], 3),
            "media": round(statistics.fmean(valores), 3)}


class Conteiner:
    def __init__(self, imagem: str, nome: str, **ambiente):
        self.imagem, self.nome = imagem, nome
        self.ambiente = {"PORT": str(PORTA), "ADT_ALLOWED_ORIGINS": ORIGEM, "GEMINI_API_KEY": "chave-de-teste",
                         "ADT_GEMINI_ENDERECO_DE_TESTE": f"http://127.0.0.1:{PORTA_GEMINI}",
                         **{chave: str(valor) for chave, valor in ambiente.items()}}
        self.cgroup: Path | None = None

    def subir(self, prazo: float = 300) -> dict:
        docker("rm", "-f", self.nome, check=False)
        argumentos = ["run", "-d", "--name", self.nome, "--network", "host", "--cpus=1", "--memory=2g", "--memory-swap=2g",
                      "--tmpfs", "/tmp:rw,size=1g,mode=1777"]
        for chave, valor in self.ambiente.items():
            argumentos += ["-e", f"{chave}={valor}"]
        inicio = time.monotonic()
        docker(*argumentos, self.imagem)
        identificador = docker("inspect", "-f", "{{.Id}}", self.nome).strip()
        self.cgroup = next((Path(c) for c in (f"/sys/fs/cgroup/system.slice/docker-{identificador}.scope",
                                               f"/sys/fs/cgroup/docker/{identificador}") if Path(c, "memory.current").exists()), None)
        porta = None
        while time.monotonic() - inicio < prazo:
            if porta is None and porta_aberta():
                porta = time.monotonic() - inicio
            if porta is not None:
                try:
                    if httpx.get(URL + "/api/health", timeout=3).status_code == 200:
                        return {"porta_aberta_s": round(porta, 2), "saude_s": round(time.monotonic() - inicio, 2)}
                except httpx.HTTPError:
                    pass
            if not self.rodando():
                raise RuntimeError("o contêiner encerrou na partida: " + self.logs()[-3000:])
            time.sleep(0.05)
        raise RuntimeError(f"o contêiner não respondeu em {prazo} s: " + self.logs()[-3000:])

    def rodando(self) -> bool:
        return docker("inspect", "-f", "{{.State.Running}}", self.nome, check=False).strip() == "true"

    def oom(self) -> bool:
        return docker("inspect", "-f", "{{.State.OOMKilled}}", self.nome, check=False).strip() == "true"

    def ler(self, arquivo: str) -> str:
        if self.cgroup is not None and (self.cgroup / arquivo).exists():
            return (self.cgroup / arquivo).read_text().strip()
        return docker("exec", self.nome, "cat", "/sys/fs/cgroup/" + arquivo, check=False).strip()

    def memoria(self) -> dict:
        def numero(texto):
            return int(texto) if texto.isdigit() else None
        return {"atual": numero(self.ler("memory.current")), "pico": numero(self.ler("memory.peak"))}

    def limites(self) -> dict:
        def dentro(arquivo):
            return docker("exec", self.nome, "cat", "/sys/fs/cgroup/" + arquivo, check=False).strip()
        montagens = docker("exec", self.nome, "cat", "/proc/mounts", check=False)
        tmp = next((linha.split()[2] for linha in montagens.splitlines() if linha.split()[1:2] == ["/tmp"]), None)
        return {"cpu.max": dentro("cpu.max"), "memory.max": dentro("memory.max"), "memory.swap.max": dentro("memory.swap.max"),
                "tmp": tmp, "usuario": docker("exec", self.nome, "id", "-u", check=False).strip()}

    def logs(self) -> str:
        feito = subprocess.run(["docker", "logs", self.nome], capture_output=True, text=True)
        return feito.stdout + feito.stderr

    def diff(self) -> list[str]:
        return [linha for linha in docker("diff", self.nome, check=False).splitlines() if linha.strip()]

    def parar(self) -> dict:
        inicio = time.monotonic()
        docker("stop", "-t", "10", self.nome, check=False)
        duracao = time.monotonic() - inicio
        codigo = docker("inspect", "-f", "{{.State.ExitCode}}", self.nome, check=False).strip()
        registro = self.logs()
        return {"duracao_s": round(duracao, 2), "codigo_de_saida": codigo,
                "encerramento_no_log": bool(re.search(r"Shutting down|Finished server process", registro))}

    def remover(self):
        docker("rm", "-f", self.nome, check=False)


class Amostrador:
    """A maior memória do contêiner (memory.current) enquanto o bloco roda."""

    def __init__(self, conteiner: Conteiner, intervalo: float = 0.05):
        self.c, self.intervalo, self.maximo, self._parar = conteiner, intervalo, 0, threading.Event()

    def _rodar(self):
        while not self._parar.is_set():
            atual = self.c.memoria()["atual"] or 0
            self.maximo = max(self.maximo, atual)
            self._parar.wait(self.intervalo if self.c.cgroup is not None else 0.5)

    def __enter__(self):
        self._fio = threading.Thread(target=self._rodar, daemon=True)
        self._fio.start()
        return self

    def __exit__(self, *args):
        self._parar.set()
        self._fio.join(5)


def normalizar(valor):
    if isinstance(valor, dict):
        return {chave: normalizar(item) for chave, item in valor.items() if chave not in VOLATEIS}
    if isinstance(valor, list):
        return [normalizar(item) for item in valor]
    return valor


def cliente() -> httpx.Client:
    return httpx.Client(base_url=URL, timeout=httpx.Timeout(300.0), headers={"Accept-Encoding": "gzip"})


def medir_pedido(c: Conteiner, http: httpx.Client, metodo: str, rota: str, **kwargs) -> tuple[httpx.Response, dict]:
    with Amostrador(c) as amostra:
        inicio = time.monotonic()
        resposta = http.request(metodo, rota, **kwargs)
        tempo = time.monotonic() - inicio
    memoria = c.memoria()
    return resposta, {"status": resposta.status_code, "tempo_s": round(tempo, 3), "bytes": len(resposta.content),
                      "bytes_transferidos": resposta.num_bytes_downloaded, "memoria_max_mb": mb(amostra.maximo),
                      "memoria_depois_mb": mb(memoria["atual"]), "pico_mb": mb(memoria["pico"])}


# ------------------------------------------------------------------------------------------------ partida

COMPONENTES = r"""
import json, os, time
os.environ["GEMINI_API_KEY"] = ""
t = {}
inicio = time.monotonic(); import main; t["importacao_s"] = time.monotonic() - inicio
from brazil_data import load_brazil_sources
inicio = time.monotonic(); conteudos, integridade = load_brazil_sources(); t["fontes_conferidas_s"] = time.monotonic() - inicio
inicio = time.monotonic(); raw, nome, _ = conteudos["municipal"]; quadro, _ = main.read_dataset(raw, nome, limite_de_bytes=len(raw))
t["fonte_municipal_lida_s"] = time.monotonic() - inicio; t["linhas_municipais"] = len(quadro)
t["quadro_municipal_mb"] = round(quadro.memory_usage(deep=True).sum() / 1048576, 1)
import conversation_library
inicio = time.monotonic(); conversation_library.library(); t["biblioteca_s"] = time.monotonic() - inicio
import document_catalog
inicio = time.monotonic(); document_catalog.registry(); t["catalogo_documental_s"] = time.monotonic() - inicio
t["integridade"] = integridade.get("integridade")
print(json.dumps({k: (round(v, 3) if isinstance(v, float) else v) for k, v in t.items()}))
"""


def tamanho_da_imagem(imagem: str) -> dict:
    """O tamanho da imagem descompactada e uma estimativa do tamanho comprimido (o que o Artifact Registry guarda)."""
    descompactada = int(docker("image", "inspect", "-f", "{{.Size}}", imagem).strip() or 0)
    salvar = subprocess.Popen(["docker", "save", imagem], stdout=subprocess.PIPE)
    comprimir = subprocess.run(["gzip", "-1"], stdin=salvar.stdout, stdout=subprocess.PIPE, timeout=600)
    salvar.wait()
    return {"descompactada_mb": mb(descompactada), "comprimida_estimada_mb": mb(len(comprimir.stdout))}


def medir_partida(c: Conteiner, problemas: list) -> dict:
    tamanho = tamanho_da_imagem(c.imagem)
    tempos = c.subir()
    limites = c.limites()
    memoria = c.memoria()
    registro = c.logs()
    achado = re.search(r"Aquecimento concluído em ([\d.]+) s \(base do Brasil ([\d.]+) s; biblioteca conversacional ([\d.]+) s\)",
                       registro)
    aquecimento = ({"total_s": float(achado.group(1)), "base_s": float(achado.group(2)), "biblioteca_s": float(achado.group(3))}
                   if achado else None)
    if limites["cpu.max"].split()[:2] != ["100000", "100000"]:
        problemas.append("cpu.max diferente de 1 CPU: " + limites["cpu.max"])
    if limites["memory.max"] != str(LIMITE_MEMORIA):
        problemas.append("memory.max diferente de 2 GiB: " + limites["memory.max"])
    if limites["memory.swap.max"] not in ("0", ""):
        problemas.append("swap disponível no contêiner: " + limites["memory.swap.max"])
    if limites["tmp"] != "tmpfs":
        problemas.append("/tmp não está em memória: " + str(limites["tmp"]))
    if limites["usuario"] in ("0", ""):
        problemas.append("o processo roda como root")
    if aquecimento is None:
        problemas.append("o log não traz a linha do aquecimento")
    componentes = {}
    feito = subprocess.run(["docker", "exec", "-w", "/app/backend", c.nome, "python", "-c", COMPONENTES],
                           capture_output=True, text=True, timeout=600)
    if feito.returncode == 0:
        componentes = json.loads(feito.stdout.strip().splitlines()[-1])
    else:
        problemas.append("componentes da partida: " + feito.stderr[-800:])
    return {**tempos, "imagem": tamanho, "limites": limites, "aquecimento": aquecimento,
            "memoria_depois_da_partida_mb": mb(memoria["atual"]), "pico_na_partida_mb": mb(memoria["pico"]),
            "componentes_em_outro_processo": componentes}


# ------------------------------------------------------------------------------------------------ análises

PESSOAS = ("distrito;provincia;ano;categoria;id_pessoa;populacao\n" + "".join(
    f"{nome};{provincia};{ano};Enfermeiros;{pessoa};1000\n"
    for ano, unidades in (("2023", {"Alto Rio": ["p1", "p2", "p3", "p4"], "Campina": ["p5", "p6"]}),
                          ("2024", {"Alto Rio": ["p1", "p2", "p9"], "Campina": ["p5", "p6", "p7"], "Serra": ["p8"]}))
    for nome, pessoas in unidades.items() for pessoa in pessoas
    for provincia in [{"Alto Rio": "Norte", "Campina": "Sul", "Serra": "Sul"}[nome]])).encode()


def lado(tipo="pais", filtros=()):
    return {"partir_de": {"tipo": tipo, "regioes": [], "ufs": []}, "filtros": list(filtros),
            "escolha": {"modo": "todos", "municipios": []}}


def primeiro_municipio() -> str:
    """O rótulo do primeiro município da fonte municipal versionada ("NOME [código IBGE]"), como nos testes com dados reais."""
    import csv
    with (RAIZ / "Dados_Municipios_Brasil.csv").open(encoding="utf-8-sig", newline="") as arquivo:
        linha = next(csv.DictReader(arquivo, delimiter=";"))
    return linha["municipio"] + " [" + linha["cod_ibge"] + "]"


def pedidos_das_analises(info: dict) -> list[tuple[str, str, dict, dict | None, bool]]:
    """(família, rota, formulário, arquivos, usada pela página) de cada análise."""
    mapa, versao = json.dumps(info["suggested_mapping"]), info["source"]["version"]
    curado = info["curated_defaults"]
    base = {"confirmed_roles": ["period", "territory_id"], "count_unit": "pessoas", "population_denominator_confirmed": True,
            "report_indicator": "density"}
    espacial = {"confirmed_roles": curado["confirmed_roles"], "count_unit": curado["count_unit"], "fts_scope_confirmed": True,
                "object_confirmed": True, "population_denominator_confirmed": True, "category_filter": curado["category"],
                "period_filter": "202406", "number_format": "decimal_comma", "crs": "SIRGAS2000"}
    referencias = {"reference_mode": "criterion", "reference_criterion": {"operator": ">=", "value": "2,36"}}
    arvore = {"logic": "and", "operands": [{"attribute": "densidade", "operator": "<", "value": "2,36"},
                                           {"attribute": "distancia", "operator": ">", "value": "155"}]}

    def analise(operacao, opcoes):
        return {"dataset": "brazil", "scope": "municipal", "dataset_version": versao, "operation": operacao, "mapping": mapa,
                "options": json.dumps(opcoes)}

    def painel(**opcoes):
        return {"dataset": "brazil", "scope": "municipal", "dataset_version": versao, "context_revision": "0",
                "mapping": mapa, "options": json.dumps(opcoes)}
    municipios = {"nivel": "municipios", "indicador": "densidade", "competencia": "202406"}
    amazonas = {"municipios": {"estados": ["13"]}}
    consulta = {"base": lado("selecao_previa"), "referencia": lado(filtros=[{"indicador": "densidade", "operador": ">",
                                                                              "valor": 3}]),
                "distancia": {"medida": "geodesica", "ate": "referencia_mais_proxima"}}
    a = "/api/analyze"
    return [
        ("densidade", a, analise("density", {**base, "period_filter": "202406"}), None, False),
        ("quantitativos", a, analise("counts", {**base, "comparison_confirmed": True, "period_filter": "202406"}), None, False),
        ("quantitativos, todas as competências", a, analise("counts", {**base, "comparison_confirmed": True}), None, False),
        ("relatório", a, analise("report", {**base, "comparison_confirmed": True, "period_filter": "202406"}), None, False),
        ("distribuição", a, analise("distribution", {**base, "period_filter": "202406", "distribution_indicator": "density"}),
         None, False),
        ("comparações", a, analise("comparisons", {**base, "comparison_confirmed": True, "period_filter": "202406"}), None, False),
        ("evolução e tendência", a, analise("temporal", {**base, "temporal_indicator": "density"}), None, False),
        ("agregação", a, analise("aggregate", {**base, "period_filter": "202406"}), None, False),
        ("ranking", a, analise("ranking", {**base, "comparison_confirmed": True, "period_filter": "202406"}), None, False),
        ("espacial", a, analise("spatial", {**base, "confirmed_roles": ["period", "territory_id", "latitude", "longitude"],
                                            "number_format": "decimal_comma", "crs": "SIRGAS2000", "period_filter": "202406",
                                            "reference_territory": primeiro_municipio()}), None, False),
        ("referência mais próxima", a, analise("nearest", {**espacial, **referencias}), None, False),
        ("critérios combinados", a, analise("criteria", {**espacial, **referencias, "criteria": arvore}), None, False),
        ("rotatividade (planilha com identificador)", a, {"operation": "rotation", "mapping": json.dumps(
            {"territory": "distrito", "period": "ano", "category": "categoria", "identity": "id_pessoa",
             "population": "populacao"}), "options": json.dumps({"initial_period": "2023", "final_period": "2024",
                                                                  "category_filter": "Enfermeiros"})},
         {"file": ("pessoas.csv", PESSOAS)}, False),
        ("página única: estados", "/api/painel", painel(nivel="estados", indicador="densidade", competencia="202406"), None, True),
        ("página única: municípios do Amazonas", "/api/painel", painel(**municipios, base=amazonas), None, True),
        ("página única: todos os municípios", "/api/painel", painel(**municipios, base={"municipios": {"todos": True}}), None,
         True),
        ("página única: tendência", "/api/painel", painel(**municipios, base=amazonas, tendencia={
            "competencias": ["202106", "202206", "202306", "202406"]}), None, True),
        ("página única: espacial (escolha dos territórios)", "/api/painel", painel(**municipios, base=amazonas,
                                                                                   consulta=consulta), None, True),
        ("página única: mapa de todos os municípios", "/api/painel/mapa", painel(competencia="202406"), None, True),
        ("página única: contagens da escolha dos territórios", "/api/painel/territorios", painel(
            competencia="202406", base=amazonas, consulta=consulta), None, True),
    ]


def medir_analises(c: Conteiner, problemas: list) -> list[dict]:
    from fastapi.testclient import TestClient
    import main
    referencia = TestClient(main.app)
    resultados = []
    with cliente() as http:
        inspecao, linha = medir_pedido(c, http, "POST", "/api/inspect", data={"dataset": "brazil", "scope": "municipal"})
        esperada = referencia.post("/api/inspect", data={"dataset": "brazil", "scope": "municipal"})
        igual = normalizar(inspecao.json()) == normalizar(esperada.json())
        resultados.append({"familia": "exame da base do Brasil", "rota": "/api/inspect", "identica": igual, **linha})
        if inspecao.status_code != 200 or not igual:
            problemas.append("o exame da base no contêiner difere da referência")
            return resultados
        for familia, rota, formulario, arquivos, pagina in pedidos_das_analises(inspecao.json()):
            resposta, linha = medir_pedido(c, http, "POST", rota, data=formulario, files=arquivos)
            esperada = referencia.post(rota, data=formulario, files=arquivos)
            igual = (resposta.status_code == esperada.status_code and
                     normalizar(resposta.json()) == normalizar(esperada.json()))
            resultados.append({"familia": familia, "rota": rota, "usada_pela_pagina": pagina, "identica": igual,
                               "status_da_referencia": esperada.status_code, **linha})
            if resposta.status_code != 200:
                problemas.append(f"análise sem resultado no contêiner ({familia}): {resposta.status_code} "
                                 f"{resposta.text[:300]}")
            elif not igual:
                problemas.append(f"análise diferente da referência ({familia})")
            if resposta.num_bytes_downloaded > LIMITE_HTTP1 and pagina:
                problemas.append(f"resposta acima de 32 MiB numa rota da página ({familia})")
    return resultados


# ------------------------------------------------------------------------------------------------ planilhas

PAPEIS = {"territory": "territorio_analise", "territory_id": "codigo_identificador", "grupo_territorial": "territorio_superior_1",
          "category": "categoria_profissional", "count": "quantidade", "population": "populacao_estimada",
          "latitude": "latitude", "longitude": "longitude"}


def casos_de_planilha(pasta: Path) -> list[tuple[str, Path, str]]:
    """(caso, arquivo, desfecho esperado no /api/inspect: aceito, recusado pelo tamanho, inválido)."""
    casos = []
    for rotulo, tamanho, esperado in (("pequeno", 100_000, "aceito"), ("médio", 3_000_000, "aceito"),
                                      ("de 14,9 MB", 14_900_000, "aceito"), ("de 15.000.000 bytes", 15_000_000, "aceito"),
                                      ("de 15.000.001 bytes", 15_000_001, "tamanho"), ("de 20 MB", 20_000_000, "tamanho"),
                                      ("de 40 MB", 40_000_000, "tamanho")):
        casos.append(("CSV " + rotulo, P.csv_exato(pasta / f"planilha-{tamanho}.csv", tamanho), esperado))
        if tamanho <= 20_000_000:
            casos.append(("XLSX " + rotulo, P.xlsx_exato(pasta / f"planilha-{tamanho}.xlsx", tamanho), esperado))
    casos.append(("XLSX malformado", P.xlsx_malformado(pasta / "malformado.xlsx"), "invalido"))
    casos.append(("XLSX truncado", P.xlsx_truncado(pasta / "truncado.xlsx", pasta / "planilha-3000000.xlsx"), "invalido"))
    casos.append(("XLSX com expansão desproporcional (400 MB descompactados)", P.xlsx_expandido(pasta / "bomba.xlsx", 400),
                  "invalido"))
    return casos


def desfecho(status: int) -> str:
    return {200: "aceito", 413: "tamanho", 422: "invalido"}.get(status, f"status {status}")


def processar(c: Conteiner, http: httpx.Client, caminho: Path, inspecao: dict) -> dict:
    from semantic_bridge import ROLES
    sugerido = inspecao.get("suggested_mapping") or {}
    mapeamento = {**{k: v for k, v in sugerido.items() if k == "period"},
                  **{papel: coluna for papel, coluna in PAPEIS.items() if coluna in inspecao.get("columns", [])}}
    # Os papéis fora do mapeamento sugerido são os que a pessoa escolhe no seletor do painel Colunas (confirmed_roles), como o
    # código territorial, que o nome da coluna nunca estabelece.
    escolhidos = [papel for papel in mapeamento if papel in ROLES and papel not in sugerido]
    periodos = inspecao.get("periods") or []
    opcoes = {"nivel": "municipios", "indicador": "densidade", "competencia": periodos[-1] if periodos else "",
              "rotulos": ROTULOS, "premissas": {"count_unit": "pessoas", "confirmed_roles": escolhidos},
              "base": {"municipios": {"todos": True}}}
    resposta, linha = medir_pedido(c, http, "POST", "/api/painel", files={"file": (caminho.name, caminho.read_bytes())},
                                   data={"mapping": json.dumps(mapeamento), "options": json.dumps(opcoes),
                                         "context_revision": "0"})
    itens = len(resposta.json().get("itens", [])) if resposta.status_code == 200 else None
    return {**linha, "itens": itens, "detalhe": None if resposta.status_code == 200 else resposta.text[:300]}


def medir_planilhas(c: Conteiner, problemas: list) -> dict:
    resultados, simultaneos = [], {}
    with tempfile.TemporaryDirectory(prefix="adt-planilhas-") as temporaria, cliente() as http:
        pasta = Path(temporaria)
        inicio = time.monotonic()
        casos = casos_de_planilha(pasta)
        geracao = round(time.monotonic() - inicio, 1)
        for caso, caminho, esperado in casos:
            if not c.rodando():
                problemas.append("o contêiner parou antes do caso " + caso + (" (falta de memória)" if c.oom() else ""))
                c.subir()
            try:
                resposta, linha = medir_pedido(c, http, "POST", "/api/inspect",
                                               files={"file": (caminho.name, caminho.read_bytes())})
            except httpx.HTTPError as exc:
                # Acima do limite do pedido, o serviço responde 413 sem ler o corpo e fecha a conexão; o cliente que ainda
                # envia pode ver só o fim da conexão. É a recusa pelo tamanho, antes de qualquer leitura.
                obtido = "tamanho" if caminho.stat().st_size > 15_000_000 else "erro de conexão"
                resultados.append({"caso": caso, "bytes_do_arquivo": caminho.stat().st_size, "esperado": esperado,
                                   "obtido": obtido, "mensagem": "conexão encerrada pelo serviço durante o envio ("
                                   + type(exc).__name__ + ")", "exame": {"status": None, "tempo_s": None,
                                                                         "memoria_max_mb": mb(c.memoria()["atual"])}})
                if obtido != esperado:
                    problemas.append(f"planilha {caso}: {type(exc).__name__}")
                continue
            obtido = desfecho(resposta.status_code)
            registro = {"caso": caso, "bytes_do_arquivo": caminho.stat().st_size, "esperado": esperado, "obtido": obtido,
                        "mensagem": None if resposta.status_code == 200 else resposta.json().get("detail", "")[:240],
                        "exame": linha}
            if resposta.status_code == 200:
                registro["linhas"] = resposta.json().get("row_count")
                registro["processamento"] = processar(c, http, caminho, resposta.json())
                if registro["processamento"]["status"] != 200:
                    problemas.append(f"planilha aceita sem resultado no gráfico ({caso}): {registro['processamento']['detalhe']}")
            if obtido != esperado:
                problemas.append(f"planilha {caso}: esperado {esperado}, obtido {obtido}")
            if c.oom():
                problemas.append(f"falta de memória no caso {caso}")
            resultados.append(registro)
        # Dois envios simultâneos de 14,9 MB (CSV e XLSX), cada um no seu pedido.
        pares = [(pasta / "planilha-14900000.csv"), (pasta / "planilha-14900000.xlsx")]
        with Amostrador(c) as amostra, concurrent.futures.ThreadPoolExecutor(2) as executor:
            def enviar(caminho):
                with cliente() as proprio:
                    inicio = time.monotonic()
                    resposta = proprio.post("/api/inspect", files={"file": (caminho.name, caminho.read_bytes())})
                    return {"arquivo": caminho.name, "status": resposta.status_code, "tempo_s": round(time.monotonic() - inicio, 2)}
            simultaneos["envios"] = list(executor.map(enviar, pares))
        simultaneos["memoria_max_mb"] = mb(amostra.maximo)
        simultaneos["pico_mb"] = mb(c.memoria()["pico"])
        if any(item["status"] != 200 for item in simultaneos["envios"]) or c.oom():
            problemas.append("dois envios simultâneos de 14,9 MB: " + json.dumps(simultaneos["envios"]))
    return {"geracao_s": geracao, "casos": resultados, "dois_simultaneos": simultaneos}


# ------------------------------------------------------------------------------------------------ sessões pela API

def medir_sessoes_api(c: Conteiner, problemas: list) -> dict:
    resultado = {}
    with cliente() as http:
        token = http.post("/api/session").json()["token"]
        cabecalho = {"X-ADT-Session": token}
        inicial = http.get("/api/session", headers=cabecalho).json()["expires_in"]
        time.sleep(3)
        depois = http.get("/api/session", headers=cabecalho).json()["expires_in"]
        renovado = http.post("/api/session/interact", headers=cabecalho, json={"kind": "NAVEGACAO_CONTROLE_EFETIVO"}).json()
        resultado.update(prazo_inicial_s=round(inicial, 1), prazo_depois_de_consultar_s=round(depois, 1),
                         prazo_depois_da_interacao_s=round(renovado["expires_in"], 1))
        # O prazo restante vem em segundos com fração (1.800 menos o tempo desde a última interação).
        if not (inicial > 1799 and depois <= inicial - 2.5 and renovado["expires_in"] >= 1799):
            problemas.append("a consulta renovou o prazo ou a interação não renovou: " + json.dumps(resultado))
        consultas, preverificacoes = [], []
        for _ in range(30):
            inicio = time.monotonic()
            http.get("/api/session", headers=cabecalho)
            consultas.append((time.monotonic() - inicio) * 1000)
            inicio = time.monotonic()
            http.request("OPTIONS", "/api/session", headers={"Origin": ORIGEM, "Access-Control-Request-Method": "GET",
                                                              "Access-Control-Request-Headers": "x-adt-session"})
            preverificacoes.append((time.monotonic() - inicio) * 1000)
        resultado["consulta_ms"] = percentis(consultas)
        resultado["preverificacao_ms"] = percentis(preverificacoes)
        preverificacao = http.request("OPTIONS", "/api/session", headers={
            "Origin": ORIGEM, "Access-Control-Request-Method": "GET", "Access-Control-Request-Headers": "x-adt-session"})
        resultado["preverificacao_max_age"] = preverificacao.headers.get("access-control-max-age")
        http.post("/api/session/close", headers=cabecalho)
        resultado["encerrada_status"] = http.get("/api/session", headers=cabecalho).status_code
        if resultado["encerrada_status"] != 410:
            problemas.append("o encerramento explícito não revogou a sessão")
        outra = http.post("/api/session").json()["token"]
    c.parar()
    docker("start", c.nome)
    inicio = time.monotonic()
    while not porta_aberta() and time.monotonic() - inicio < 300:
        time.sleep(0.2)
    with cliente() as http:
        while time.monotonic() - inicio < 300:
            try:
                if http.get("/api/health").status_code == 200:
                    break
            except httpx.HTTPError:
                time.sleep(0.2)
        resultado["reinicio_s"] = round(time.monotonic() - inicio, 2)
        resultado["sessao_depois_do_reinicio"] = http.get("/api/session", headers={"X-ADT-Session": outra}).status_code
    if resultado["sessao_depois_do_reinicio"] != 410:
        problemas.append("a sessão sobreviveu ao reinício (esperado 410)")
    # Custo faturável das consultas: com cobrança por requisição, cada pedido isolado conta pelo menos 100 ms.
    faturavel_por_consulta = max(0.1, round(resultado["consulta_ms"]["p95"] / 1000 + 0.05, 1))
    por_hora = 120 * faturavel_por_consulta + 0.5 * 0.1  # 120 consultas e uma pré-verificação a cada 2 h
    resultado["faturavel"] = {"por_consulta_s": faturavel_por_consulta, "por_hora_de_aba_s": round(por_hora, 2),
                              "ate_expirar_30_min_s": round(por_hora / 2, 2)}
    return resultado


# ------------------------------------------------------------------------------------------------ memória das sessões

TETO_TOTAL_DAS_SESSOES = 256 * MIB


def medir_memoria_das_sessoes(imagem: str, problemas: list) -> dict:
    """Os resultados do gráfico guardados nas sessões até o teto total (256 MiB em JSON; cada sessão guarda os 8 mais recentes
    do gráfico, cerca de 20 MB, abaixo do teto de 32 MiB por sessão), a memória real ocupada e, com as sessões cheias, os
    envios de planilha: CSV de 14,9 MB, XLSX de 15.000.000 bytes e dois desses XLSX ao mesmo tempo (as duas vagas)."""
    from fastapi.testclient import TestClient
    import conversation_session
    import main
    import painel
    c = Conteiner(imagem, "adt-medicao-sessoes")
    try:
        c.subir()
        base = c.memoria()["atual"]
        guarda = conversation_session.PANEL_KEEP
        with cliente() as http:
            info = http.post("/api/inspect", data={"dataset": "brazil", "scope": "municipal"}).json()
            periodos = sorted(info["periods"])
            registrados, recusados, bytes_registrados, passos, teto_atingido = 0, 0, 0, [], False
            for numero in range(40):
                token = http.post("/api/session").json()["token"]
                for k in range(guarda):
                    competencia = periodos[(numero * guarda + k) % len(periodos)]
                    resposta = http.post("/api/painel", headers={"X-ADT-Session": token}, data={
                        "dataset": "brazil", "scope": "municipal", "dataset_version": info["source"]["version"],
                        "context_revision": "0", "mapping": json.dumps(info["suggested_mapping"]),
                        "options": json.dumps({"nivel": "municipios", "indicador": "densidade", "competencia": competencia,
                                               "base": {"municipios": {"todos": True}}})})
                    registrado = bool((resposta.json().get("sessao") or {}).get("registrado"))
                    passos.append({"sessao": numero + 1, "registrado": registrado, "memoria_mb": mb(c.memoria()["atual"])})
                    if not registrado:
                        recusados += 1
                        teto_atingido = teto_atingido or k == 0
                        break
                    registrados += 1
                    bytes_registrados += len(resposta.content)
                if teto_atingido:
                    break  # o teto total já não aceita nem o primeiro resultado de uma sessão nova
            # Calibração: o resultado guardado na sessão (painel.session_record) em proporção à resposta.
            amostra = TestClient(main.app).post("/api/painel", data={
                "dataset": "brazil", "scope": "municipal", "dataset_version": info["source"]["version"],
                "context_revision": "0", "mapping": json.dumps(info["suggested_mapping"]),
                "options": json.dumps({"nivel": "municipios", "indicador": "densidade", "competencia": periodos[-1],
                                       "base": {"municipios": {"todos": True}}})})
            guardado = len(json.dumps(painel.session_record(amostra.json(), "x"), sort_keys=True, ensure_ascii=False,
                                      default=str).encode())
            proporcao = guardado / len(amostra.content)
        cheia = c.memoria()
        envios = {}

        def enviar(caminho):
            with cliente() as proprio:
                inicio = time.monotonic()
                resposta = proprio.post("/api/inspect", files={"file": (caminho.name, caminho.read_bytes())})
                return {"arquivo": caminho.name, "status": resposta.status_code, "tempo_s": round(time.monotonic() - inicio, 2)}
        with tempfile.TemporaryDirectory(prefix="adt-sessoes-") as temporaria:
            csv = P.csv_exato(Path(temporaria) / "planilha.csv", 14_900_000)
            xlsx = P.xlsx_exato(Path(temporaria) / "planilha.xlsx", 15_000_000)
            for rotulo, arquivos in (("CSV de 14,9 MB", [csv]), ("XLSX de 15.000.000 bytes", [xlsx]),
                                     ("dois XLSX de 15.000.000 bytes ao mesmo tempo", [xlsx, xlsx])):
                with Amostrador(c) as amostra, concurrent.futures.ThreadPoolExecutor(len(arquivos)) as executor:
                    feitos = list(executor.map(enviar, arquivos))
                envios[rotulo] = {"envios": feitos, "memoria_max_mb": mb(amostra.maximo)}
                if any(item["status"] != 200 for item in feitos):
                    problemas.append(f"com as sessões cheias, o envio ({rotulo}) não foi aceito: " + json.dumps(feitos))
                if c.oom() or not c.rodando():
                    break
        # No teto, o gráfico de uma sessão abre espaço tirando os mais antigos dela: o guardado não passa do teto total.
        json_guardado = min(bytes_registrados * proporcao, TETO_TOTAL_DAS_SESSOES) if teto_atingido else \
            bytes_registrados * proporcao
        real = (cheia["atual"] or 0) - (base or 0)
        final = c.memoria() if c.rodando() else {"pico": None}  # memory.peak: o pico de verdade, desde a partida
        pico = max([cheia["pico"] or 0, final["pico"] or 0, *[(item["memoria_max_mb"] or 0) * MIB for item in envios.values()]])
        resultado = {"memoria_base_mb": mb(base), "memoria_com_as_sessoes_mb": mb(cheia["atual"]), "pico_mb": mb(cheia["pico"]),
                     "teto_total_atingido": teto_atingido, "resultados_registrados": registrados,
                     "resultados_recusados": recusados, "json_guardado_estimado_mb": mb(json_guardado),
                     "memoria_real_das_sessoes_mb": mb(real),
                     "memoria_por_mb_de_json": round(real / json_guardado, 2) if json_guardado else None,
                     "envios_com_as_sessoes_cheias": envios, "pico_com_os_envios_mb": mb(pico),
                     "pico_com_os_envios_pct_de_2_gib": round(100 * pico / LIMITE_MEMORIA, 1),
                     "oom": c.oom(), "passos": passos}
        if not teto_atingido:
            problemas.append("as sessões não chegaram ao teto total de 256 MiB (a medição não alcançou a condição pedida)")
        if c.oom() or not c.rodando():
            problemas.append("falta de memória com as sessões cheias e os envios de planilha")
        elif pico > 0.9 * LIMITE_MEMORIA:
            problemas.append(f"as sessões cheias com os envios de planilha chegam a {resultado['pico_com_os_envios_pct_de_2_gib']}% "
                             "dos 2 GiB (acima de 90%)")
        return resultado
    finally:
        c.remover()


# ------------------------------------------------------------------------------------------------ Gemini simulado

def medir_gemini(imagem: str, problemas: list) -> list[dict]:
    resultados = []
    c = Conteiner(imagem, "adt-medicao-gemini")

    def conversar(http, mensagem):
        antes = http.get("/api/llm/status").json()["requests_used_today"]
        inicio = time.monotonic()
        resposta = http.post("/api/llm/interpret", json={"message": mensagem})
        tempo = time.monotonic() - inicio
        status = http.get("/api/llm/status").json()
        return resposta, tempo, status, status["requests_used_today"] - antes

    cenarios = [
        # (cenário, mensagem, verificação, espera depois, reiniciar depois)
        ("sucesso", "analisar distribuição da densidade",
         lambda r, s: r.json()["proposal"]["operation"] == "distribution", 0, False),
        ("demora de 5 s", "simule demora 5 analisar distribuição da densidade",
         lambda r, s: r.json()["proposal"]["operation"] == "distribution", 0, False),
        ("saída fora do contrato (regeneração)", "simule fora do contrato agora",
         lambda r, s: r.json().get("reserva") is True, 0, False),
        ("tempo esgotado (75 s)", "simule tempo esgotado agora",
         lambda r, s: r.json()["indisponibilidade"]["tipo"] == "indisponivel" and s["espera"]["escopo"] == "tempo_esgotado",
         21, False),
        ("5xx do provedor (503)", "simule erro 503 agora",
         lambda r, s: s["espera"]["causa"] == "indisponivel" and s["espera"]["escopo"] == "provedor", 21, False),
        ("5xx do provedor (500)", "simule erro 500 agora",
         lambda r, s: s["espera"]["causa"] == "indisponivel" and s["espera"]["escopo"] == "provedor", 21, False),
        ("429 por minuto (RetryInfo 3 s)", "simule cota minuto agora",
         lambda r, s: r.json()["indisponibilidade"]["tipo"] == "cota" and s["espera"]["escopo"] == "minuto", 4, False),
        ("de volta depois da espera do 429", "analisar distribuição da densidade",
         lambda r, s: r.json()["proposal"]["operation"] == "distribution", 0, False),
        ("chave inválida (400 API_KEY_INVALID)", "simule chave invalida agora",
         lambda r, s: s["espera"]["causa"] == "configuracao", 0, True),
        ("chave recusada (403)", "simule chave recusada agora",
         lambda r, s: s["espera"]["causa"] == "configuracao", 0, True),
        ("429 por dia (QuotaFailure PerDay)", "simule cota dia agora",
         lambda r, s: r.json()["indisponibilidade"]["tipo"] == "cota" and s["espera"]["escopo"] == "dia", 0, False),
    ]
    try:
        c.subir()
        for cenario, mensagem, confere, espera, reiniciar in cenarios:
            with cliente() as http:
                resposta, tempo, status, chamadas = conversar(http, mensagem)
                try:
                    ok = resposta.status_code == 200 and confere(resposta, status)
                except (KeyError, TypeError, ValueError):
                    ok = False
                texto = resposta.text
                resultados.append({"cenario": cenario, "status": resposta.status_code, "tempo_s": round(tempo, 2),
                                   "chamadas": chamadas, "espera": status.get("espera"), "ok": ok,
                                   "sem_detalhe_tecnico": not re.search(r"\b429\b|RESOURCE_EXHAUSTED|API_KEY_INVALID|"
                                                                        r"PERMISSION_DENIED|chave-de-teste", texto)})
                if not ok or not resultados[-1]["sem_detalhe_tecnico"]:
                    problemas.append(f"Gemini simulado, {cenario}: {resposta.status_code} {texto[:300]}")
            if espera:
                time.sleep(espera)
            if reiniciar:
                c.subir()
        # Com o provedor em espera (cota do dia), o motor determinístico continua: o gráfico dos estados sai normalmente.
        with cliente() as http:
            info = http.post("/api/inspect", data={"dataset": "brazil", "scope": "municipal"}).json()
            grafico = http.post("/api/painel", data={"dataset": "brazil", "scope": "municipal",
                                                      "dataset_version": info["source"]["version"], "context_revision": "0",
                                                      "mapping": json.dumps(info["suggested_mapping"]),
                                                      "options": json.dumps({"nivel": "estados", "indicador": "densidade",
                                                                             "competencia": "202406"})})
            antes = http.get("/api/llm/status").json()["requests_used_today"]
            sem_chamada = http.post("/api/llm/interpret", json={"message": "analisar distribuição da densidade"})
            depois = http.get("/api/llm/status").json()["requests_used_today"]
        ok = grafico.status_code == 200 and "indisponibilidade" in sem_chamada.json() and depois == antes
        resultados.append({"cenario": "motor sem o Gemini (em espera pela cota do dia)", "status": grafico.status_code,
                           "chamadas": depois - antes, "ok": ok})
        if not ok:
            problemas.append("o motor ou a conversa não seguiram como esperado com o Gemini em espera")
        # Chamadas por mensagem numa conversa típica, com o provedor disponível (sem gatilhos).
        c.subir()
        with cliente() as http:
            tipicas = []
            for mensagem in ("Me conte uma curiosidade", "O que é densidade?", "Explique de maneira mais simples",
                             "analisar distribuição da densidade", "Obrigado!"):
                _, tempo, _, chamadas = conversar(http, mensagem)
                tipicas.append({"mensagem": mensagem, "chamadas": chamadas, "tempo_s": round(tempo, 2)})
        resultados.append({"cenario": "chamadas por mensagem (conversa típica, sem base)", "mensagens": tipicas, "ok": True})
        return resultados
    finally:
        c.remover()


# ------------------------------------------------------------------------------------------------ concorrência

class Usuario:
    """Um usuário simulado: abre a página (os pedidos da abertura saem juntos, como no navegador), escolhe a base e percorre
    análises leves e pesadas, uma planilha e a conversa com o Gemini simulado (2 a 20 s), com pausas curtas, até o fim da
    janela; a consulta da sessão sai a cada 30 s, em paralelo, como na página. `voo` conta os pedidos em andamento de todos os
    usuários (o máximo é a base da concorrência do Cloud Run)."""

    def __init__(self, numero: int, info: dict, planilha: bytes, registros: list, lock: threading.Lock, voo: dict):
        self.n, self.info, self.planilha, self.registros, self.lock, self.voo = numero, info, planilha, registros, lock, voo
        self.sorteio = random.Random(numero)
        self.http = cliente()
        self.token = ""

    def registrar(self, passo: str, inicio: float, resposta: httpx.Response | None, erro: str = ""):
        ocupado = False
        if resposta is not None and resposta.status_code == 503:
            try:
                ocupado = resposta.json().get("ocupado") is True
            except ValueError:
                ocupado = False
        with self.lock:
            self.registros.append({"passo": passo, "tempo_s": time.monotonic() - inicio,
                                   "status": resposta.status_code if resposta is not None else None, "ocupado": ocupado,
                                   "erro": erro})

    def pedir(self, passo: str, metodo: str, rota: str, sessao: bool = False, http: httpx.Client | None = None, **kwargs):
        cabecalhos = {"X-ADT-Session": self.token} if sessao and self.token else {}
        with self.lock:
            self.voo["atual"] += 1
            self.voo["max"] = max(self.voo["max"], self.voo["atual"])
        inicio = time.monotonic()
        try:
            resposta = (http or self.http).request(metodo, rota, headers=cabecalhos, **kwargs)
        except httpx.HTTPError as exc:
            self.registrar(passo, inicio, None, type(exc).__name__)
            return None
        finally:
            with self.lock:
                self.voo["atual"] -= 1
        self.registrar(passo, inicio, resposta)
        return resposta

    def abrir(self):
        """A abertura da página: a saúde, a sessão, o estado do Gemini e a descrição da base saem juntos."""
        pedidos = (("abertura: saúde", "GET", "/api/health"), ("abertura: sessão", "POST", "/api/session"),
                   ("abertura: estado do Gemini", "GET", "/api/llm/status"),
                   ("abertura: descrição da base", "GET", "/api/brazil/description"))
        with concurrent.futures.ThreadPoolExecutor(len(pedidos)) as executor:
            def um(pedido):
                with cliente() as proprio:
                    return self.pedir(*pedido, http=proprio)
            respostas = list(executor.map(um, pedidos))
        sessao = respostas[1]
        self.token = sessao.json().get("token", "") if sessao is not None and sessao.status_code == 200 else ""

    def consultar_a_sessao(self, parar: threading.Event):
        with cliente() as proprio:
            while not parar.wait(30):
                self.pedir("consulta da sessão (a cada 30 s)", "GET", "/api/session", True, http=proprio)

    def painel(self, rota="/api/painel", **opcoes):
        return {"dataset": "brazil", "scope": "municipal", "dataset_version": self.info["source"]["version"],
                "context_revision": "0", "mapping": json.dumps(self.info["suggested_mapping"]), "options": json.dumps(opcoes)}

    def rodar(self, fim: float):
        self.abrir()
        parar = threading.Event()
        consulta = threading.Thread(target=self.consultar_a_sessao, args=(parar,), daemon=True)
        consulta.start()
        amazonas = {"municipios": {"estados": ["13"]}}
        passos = [
            ("base do Brasil (exame)", lambda: self.pedir("base do Brasil (exame)", "POST", "/api/inspect",
                                                         data={"dataset": "brazil", "scope": "municipal"})),
            ("leve: estados", lambda: self.pedir("leve: estados", "POST", "/api/painel", True, data=self.painel(
                nivel="estados", indicador="densidade", competencia="202406"))),
            ("leve: municípios do Amazonas", lambda: self.pedir("leve: municípios do Amazonas", "POST", "/api/painel", True,
                data=self.painel(nivel="municipios", indicador="densidade", competencia="202406", base=amazonas))),
            ("conversa (Gemini simulado de 2 a 20 s)", lambda: self.pedir(
                "conversa (Gemini simulado de 2 a 20 s)", "POST", "/api/llm/interpret", True,
                json={"message": f"simule demora {self.sorteio.randint(2, 20)} analisar distribuição da densidade"})),
            ("pesada: todos os municípios", lambda: self.pedir("pesada: todos os municípios", "POST", "/api/painel", True,
                data=self.painel(nivel="municipios", indicador="densidade", competencia="202406",
                                 base={"municipios": {"todos": True}}))),
            ("pesada: mapa de todos os municípios", lambda: self.pedir("pesada: mapa de todos os municípios", "POST",
                "/api/painel/mapa", True, data=self.painel(competencia="202406"))),
            ("leve: escolha dos territórios", lambda: self.pedir("leve: escolha dos territórios", "POST",
                "/api/painel/territorios", True, data=self.painel(competencia="202406", base=amazonas, consulta={
                    "base": lado("selecao_previa"), "referencia": lado(), "distancia": {"medida": "geodesica",
                                                                                         "ate": "referencia_mais_proxima"}}))),
            ("planilha de 3 MB (exame)", lambda: self.pedir("planilha de 3 MB (exame)", "POST", "/api/inspect",
                files={"file": ("planilha.csv", self.planilha)})),
            ("interação da sessão", lambda: self.pedir("interação da sessão", "POST", "/api/session/interact", True,
                json={"kind": "NAVEGACAO_CONTROLE_EFETIVO"})),
        ]
        indice = self.n % len(passos)
        while time.monotonic() < fim:
            passos[indice][1]()
            indice = (indice + 1) % len(passos)
            time.sleep(self.sorteio.uniform(0.2, 1.0))
        parar.set()
        consulta.join(60)
        self.http.close()


def rodada(c: Conteiner, usuarios: int, info: dict, planilha: bytes, duracao: float) -> dict:
    registros, lock, saude, voo = [], threading.Lock(), [], {"atual": 0, "max": 0}
    parar = threading.Event()

    def sondar():
        with httpx.Client(base_url=URL, timeout=30) as sonda:
            while not parar.is_set():
                inicio = time.monotonic()
                try:
                    sonda.get("/api/health")
                    saude.append(time.monotonic() - inicio)
                except httpx.HTTPError:
                    saude.append(30.0)
                parar.wait(0.25)
    sonda = threading.Thread(target=sondar, daemon=True)
    fim = time.monotonic() + duracao
    with Amostrador(c, 0.2) as memoria:
        sonda.start()
        with concurrent.futures.ThreadPoolExecutor(usuarios) as executor:
            futuros = []
            for numero in range(usuarios):
                futuros.append(executor.submit(Usuario(numero, info, planilha, registros, lock, voo).rodar, fim))
                time.sleep(min(0.1, 2.0 / usuarios))
            for futuro in futuros:
                futuro.result()
        parar.set()
        sonda.join(35)
    por_passo = {}
    for registro in registros:
        por_passo.setdefault(registro["passo"], []).append(registro)
    return {"usuarios": usuarios, "duracao_s": duracao, "pedidos": len(registros), "simultaneos_max": voo["max"],
            "ocupados_503": sum(r["ocupado"] for r in registros),
            "erros": sum(1 for r in registros if r["status"] is None or (r["status"] >= 500 and not r["ocupado"])),
            "status": {str(s): sum(1 for r in registros if r["status"] == s) for s in sorted({r["status"] for r in registros
                                                                                               if r["status"]})},
            "por_passo": {passo: {**percentis([r["tempo_s"] for r in itens]),
                                  "ocupados": sum(r["ocupado"] for r in itens)} for passo, itens in sorted(por_passo.items())},
            "saude_ms": {chave: (round(valor * 1000, 1) if isinstance(valor, float) and chave != "n" else valor)
                         for chave, valor in percentis(saude).items()},
            "memoria_max_mb": mb(memoria.maximo), "pico_mb": mb(c.memoria()["pico"]), "oom": c.oom()}


def medir_concorrencia(imagem: str, problemas: list, duracao: float = 45) -> list[dict]:
    resultados = []
    with tempfile.TemporaryDirectory(prefix="adt-carga-") as temporaria:
        planilha = P.csv_exato(Path(temporaria) / "planilha.csv", 3_000_000).read_bytes()
        for vagas, niveis in ((2, (1, 5, 10, 20)), (1, (10, 20))):
            c = Conteiner(imagem, f"adt-medicao-carga-{vagas}", ADT_PESADAS_SIMULTANEAS=vagas)
            try:
                c.subir()
                with cliente() as http:
                    info = http.post("/api/inspect", data={"dataset": "brazil", "scope": "municipal"}).json()
                for usuarios in niveis:
                    medicao = rodada(c, usuarios, info, planilha, duracao)
                    medicao["vagas"] = vagas
                    resultados.append(medicao)
                    if medicao["oom"] or not c.rodando():
                        problemas.append(f"falta de memória com {usuarios} usuários e {vagas} vaga(s)")
                        c.subir()
                    elif medicao["erros"]:
                        problemas.append(f"{medicao['erros']} erro(s) sem resposta legível com {usuarios} usuários e "
                                         f"{vagas} vaga(s)")
            finally:
                c.remover()
    return resultados


# ------------------------------------------------------------------------------------------------ relatório

def resumo_markdown(relatorio: dict) -> str:
    linhas = ["# Medições do contêiner nas condições do Cloud Run", "",
              f"Commit `{relatorio.get('commit', '')[:7]}`, {relatorio['comeco']}. {LIMITACOES}", ""]
    partida = relatorio.get("partida") or {}
    if partida:
        linhas += ["## Partida", "", "| Medida | Valor |", "|---|---|",
                   f"| Limites no cgroup | cpu.max `{partida['limites']['cpu.max']}`, memory.max `{partida['limites']['memory.max']}`, "
                   f"swap `{partida['limites']['memory.swap.max']}`, /tmp `{partida['limites']['tmp']}`, usuário "
                   f"`{partida['limites']['usuario']}` |",
                   f"| Imagem | {partida['imagem']} |",
                   f"| Porta aberta | {partida['porta_aberta_s']} s |", f"| /api/health respondendo | {partida['saude_s']} s |",
                   f"| Aquecimento (log) | {partida['aquecimento']} |",
                   f"| Memória depois da partida | {partida['memoria_depois_da_partida_mb']} MB (pico "
                   f"{partida['pico_na_partida_mb']} MB) |",
                   f"| Componentes (outro processo) | {partida['componentes_em_outro_processo']} |", ""]
    if relatorio.get("analises"):
        linhas += ["## Análises (contêiner × referência)", "",
                   "| Família | Rota | Idêntica | Status | Tempo (s) | Resposta (MB) | Transferido (MB) | Memória máx. (MB) |",
                   "|---|---|---|---|---|---|---|---|"]
        for item in relatorio["analises"]:
            linhas.append(f"| {item['familia']} | `{item['rota']}` | {'sim' if item['identica'] else 'NÃO'} | {item['status']} | "
                          f"{item['tempo_s']} | {mb(item['bytes'])} | {mb(item['bytes_transferidos'])} | "
                          f"{item['memoria_max_mb']} |")
        linhas.append("")
    planilhas = relatorio.get("planilhas") or {}
    if planilhas:
        linhas += ["## Planilhas", "", "| Caso | Esperado | Obtido | Exame: tempo (s), memória máx. (MB) | Gráfico: tempo (s), "
                   "memória máx. (MB), itens |", "|---|---|---|---|---|"]
        for item in planilhas["casos"]:
            exame = item["exame"]
            proc = item.get("processamento") or {}
            linhas.append(f"| {item['caso']} | {item['esperado']} | {item['obtido']} | {exame['tempo_s']}, "
                          f"{exame['memoria_max_mb']} | {proc.get('tempo_s', '—')}, {proc.get('memoria_max_mb', '—')}, "
                          f"{proc.get('itens', '—')} |")
        linhas += ["", f"Dois envios simultâneos de 14,9 MB: {planilhas['dois_simultaneos']}", ""]
    if relatorio.get("sessoes_api"):
        linhas += ["## Sessões pela API", "", "```json", json.dumps(relatorio["sessoes_api"], ensure_ascii=False, indent=1), "```", ""]
    if relatorio.get("memoria_das_sessoes"):
        resumo = {k: v for k, v in relatorio["memoria_das_sessoes"].items() if k != "passos"}
        linhas += ["## Memória das sessões", "", "```json", json.dumps(resumo, ensure_ascii=False, indent=1), "```", ""]
    if relatorio.get("gemini"):
        linhas += ["## Gemini simulado", "", "| Cenário | Status | Tempo (s) | Chamadas | Espera | OK |", "|---|---|---|---|---|---|"]
        for item in relatorio["gemini"]:
            linhas.append(f"| {item['cenario']} | {item.get('status', '')} | {item.get('tempo_s', '')} | "
                          f"{item.get('chamadas', item.get('mensagens', ''))} | {item.get('espera', '')} | {item['ok']} |")
        linhas.append("")
    if relatorio.get("concorrencia"):
        linhas += ["## Concorrência", "", "| Vagas | Usuários | Pedidos | Simultâneos (máx.) | Ocupados (503) | Erros | "
                   "/api/health p50/p95/máx (ms) | Memória máx. (MB) | Pesada: todos os municípios p50/p95/máx (s) | "
                   "Conversa p95 (s) |", "|---|---|---|---|---|---|---|---|---|---|"]
        for item in relatorio["concorrencia"]:
            pesada = item["por_passo"].get("pesada: todos os municípios", {})
            conversa = item["por_passo"].get("conversa (Gemini simulado de 2 a 20 s)", {})
            saude = item["saude_ms"]
            linhas.append(f"| {item['vagas']} | {item['usuarios']} | {item['pedidos']} | {item.get('simultaneos_max')} | "
                          f"{item['ocupados_503']} | {item['erros']} | {saude.get('p50')}/{saude.get('p95')}/{saude.get('max')} | "
                          f"{item['memoria_max_mb']} | {pesada.get('p50')}/{pesada.get('p95')}/{pesada.get('max')} | "
                          f"{conversa.get('p95')} |")
        linhas.append("")
    linhas += ["## Gravações fora de /tmp (docker diff)", "", "```", "\n".join(relatorio.get("gravacoes_fora_de_tmp") or ["(nenhuma)"]),
               "```", "", f"Encerramento com SIGTERM: {relatorio.get('encerramento')}", "",
               "## Problemas", ""] + ([f"- {p}" for p in relatorio["problemas"]] or ["- nenhum"])
    return "\n".join(linhas) + "\n"


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--imagem", required=True)
    parser.add_argument("--saida", required=True, type=Path)
    parser.add_argument("--duracao-da-carga", type=float, default=45)
    argumentos = parser.parse_args()
    argumentos.saida.mkdir(parents=True, exist_ok=True)
    problemas: list[str] = []
    relatorio = {"comeco": datetime.now(timezone.utc).isoformat(timespec="seconds"), "commit": os.getenv("GITHUB_SHA", ""),
                 "limitacoes": LIMITACOES, "imagem": argumentos.imagem,
                 "runner": {"processador": platform.processor() or platform.machine(), "cpus": os.cpu_count(),
                            "sistema": platform.platform()}, "problemas": problemas}
    gemini = serve_gemini_http.iniciar(PORTA_GEMINI)
    principal = Conteiner(argumentos.imagem, "adt-medicao")
    etapas = (("partida", lambda: medir_partida(principal, problemas)),
              ("analises", lambda: medir_analises(principal, problemas)),
              ("planilhas", lambda: medir_planilhas(principal, problemas)),
              ("gravacoes_fora_de_tmp", lambda: principal.diff()),
              ("sessoes_api", lambda: medir_sessoes_api(principal, problemas)),
              ("encerramento", lambda: principal.parar()),
              ("memoria_das_sessoes", lambda: medir_memoria_das_sessoes(argumentos.imagem, problemas)),
              ("gemini", lambda: medir_gemini(argumentos.imagem, problemas)),
              ("concorrencia", lambda: medir_concorrencia(argumentos.imagem, problemas, argumentos.duracao_da_carga)))
    try:
        for nome, etapa in etapas:
            inicio = time.monotonic()
            print(f"::group::Medição: {nome}", flush=True)
            try:
                relatorio[nome] = etapa()
            except Exception as exc:  # noqa: BLE001 — a etapa falha sozinha; as seguintes continuam
                problemas.append(f"etapa {nome} falhou: {type(exc).__name__}: {str(exc)[:600]}")
                relatorio[nome] = None
            relatorio.setdefault("duracao_das_etapas_s", {})[nome] = round(time.monotonic() - inicio, 1)
            print(json.dumps(relatorio[nome], ensure_ascii=False, default=str)[:4000], flush=True)
            print("::endgroup::", flush=True)
        if relatorio.get("encerramento") and relatorio["encerramento"]["codigo_de_saida"] != "0":
            problemas.append("o encerramento com SIGTERM não foi limpo: " + json.dumps(relatorio["encerramento"]))
    finally:
        principal.remover()
        gemini.shutdown()
        relatorio["fim"] = datetime.now(timezone.utc).isoformat(timespec="seconds")
        (argumentos.saida / "medicoes.json").write_text(json.dumps(relatorio, ensure_ascii=False, indent=1, default=str),
                                                         encoding="utf-8")
        texto = resumo_markdown(relatorio)
        (argumentos.saida / "medicoes.md").write_text(texto, encoding="utf-8")
        print(texto, flush=True)
        if os.getenv("GITHUB_STEP_SUMMARY"):
            with open(os.environ["GITHUB_STEP_SUMMARY"], "a", encoding="utf-8") as resumo:
                resumo.write(texto)
    for problema in problemas:
        print(f"::error title=Medição do contêiner::{problema[:900]}", flush=True)
    return 1 if problemas else 0


if __name__ == "__main__":
    sys.exit(main())
