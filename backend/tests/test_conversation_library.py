"""Biblioteca de Inteligência Conversacional: integridade, governança, consumo pelo provedor e pertinência.

Nenhuma chamada externa: o transporte HTTP do Gemini é simulado e só se confere o pedido que seria enviado. A
comparação com o comportamento anterior usa trajetórias inéditas (backend/tests/biblioteca_ineditas/), fora da
biblioteca; o quadro vai também para o resumo do CI (GITHUB_STEP_SUMMARY).
"""
from collections import Counter
import hashlib
import io
import json as jsonlib
import os
from pathlib import Path
import random
import re
import time

import httpx
import pytest
from fastapi.testclient import TestClient

import conversation_library as library
import library_evaluation
import llm_bridge
from document_catalog import ROOT
from main import app

client = TestClient(app)
HELD_OUT = Path(__file__).resolve().parent / "biblioteca_ineditas"
SPEC = (ROOT / "IMPLEMENTATION_SPEC.md").read_text(encoding="utf-8")
NONE = {"operation": "none", "indicator": "none", "period": "", "category": "", "territory": "",
        "intent": "ANALITICO", "topic": "none", "dialogue": "none", "social_reply": "", "candidates": []}
# Base sintética com valores que coincidem com palavras comuns dos exemplos: a máscara precisa retirá-los.
DATASET = ("municipio;periodo;categoria;quantidade;populacao\n"
           "Manaus;202406;Medicos;10;10000\nSaúde;202406;Medicos;20;10000\nNorte;202406;Medicos;5;3000\n").encode()
MAPPING = {"territory": "municipio", "period": "periodo", "category": "categoria", "count": "quantidade",
           "population": "populacao"}
PROTECTED = ("Manaus", "Saúde", "Norte", "Medicos", "municipio", "periodo", "categoria", "quantidade", "populacao",
             "202406", "10000", "base_sintetica.csv")
STATE = {"fonte": "brasil", "has_selection": False, "has_verified_result": False, "active_operation": None,
         "previous_operation": None, "previous_indicator": None, "previous_document": None}
RESULT = {**STATE, "has_selection": True, "has_verified_result": True, "active_operation": "density",
          "previous_operation": "density", "previous_indicator": "density"}


@pytest.fixture(scope="module")
def collection():
    return library.library()


@pytest.fixture(scope="module")
def held_out():
    records, _ = library.read(HELD_OUT)
    return records


class Transport:
    """Cliente HTTP simulado: guarda o corpo que iria ao provedor e devolve uma interpretação fixa."""

    def __init__(self, bodies, answer):
        self.bodies, self.answer = bodies, answer

    def __call__(self, *args, **kwargs):
        return self

    async def __aenter__(self):
        return self

    async def __aexit__(self, *args):
        return None

    async def post(self, url, headers, json):
        self.bodies.append(json)
        text = jsonlib.dumps(self.answer, ensure_ascii=False)
        return httpx.Response(200, json={"candidates": [{"content": {"parts": [{"text": text}]}}]})


def ask(monkeypatch, message, *, answer=None, base=True, history=(), headers=None):
    bodies = []
    monkeypatch.setenv("GEMINI_API_KEY", "test-only-not-real")
    monkeypatch.setattr(llm_bridge, "_counter", 0)
    monkeypatch.setattr(llm_bridge, "_counter_day", "")
    monkeypatch.setattr(llm_bridge.httpx, "AsyncClient", Transport(bodies, answer or NONE))
    if base:
        response = client.post("/api/llm/interpret-context", headers=headers or {}, files={
            "file": ("base_sintetica.csv", io.BytesIO(DATASET), "text/csv")}, data={
            "message": message, "history": jsonlib.dumps(list(history)), "mapping": jsonlib.dumps(MAPPING),
            "options": jsonlib.dumps({"count_unit": "pessoas", "period_filter": "202406"})})
    else:
        response = client.post("/api/llm/interpret", json={"message": message, "history": list(history)})
    assert response.status_code == 200, response.text
    assert len(bodies) == 1
    return response.json(), bodies[0]


def block_of(body):
    text = body["systemInstruction"]["parts"][0]["text"]
    assert text.startswith(llm_bridge._SYSTEM)
    return text[len(llm_bridge._SYSTEM):]


def present(value, text):
    return bool(re.search(r"(?<!\w)" + re.escape(library.fold(value)) + r"(?!\w)", library.fold(text)))


# ------------------------------------------------------------------------------ biblioteca íntegra e abrangente

def test_library_is_valid_diverse_and_covers_the_interpreter_contract(collection):
    problems = library.validate(collection.records, llm_bridge.library_contract(), SPEC)
    assert not problems, problems[:20]
    records, turns = collection.records, collection.turns
    assert len(records) >= 2000
    dimensions = Counter(record["dimensao"] for record in records)
    assert set(dimensions) == set(library.DIMENSIONS) and min(dimensions.values()) >= 140, dimensions
    languages = Counter(record["idioma"] for record in records)
    assert all(languages[language] >= 0.08 * len(records) for language in library.LANGUAGES), languages
    assert {record["registro"] for record in records} == set(library.REGISTERS)
    assert {record["perfil"] for record in records} == set(library.PROFILES)
    assert len(turns) >= 3.5 * len(records)
    assert sum(1 for record in records if sum("usuario" in step for step in record["passos"]) >= 6) >= 150
    contract = llm_bridge.library_contract()
    for key, values in (("operation", contract.operations), ("intent", contract.intents), ("topic", contract.topics),
                        ("dialogue", contract.dialogue)):
        assert {item["turn"]["interpretacao"][key] for item in turns} == set(values), key
    assert {item["turn"]["acao"] for item in turns} == set(library.ACTIONS)
    assert sum(1 for item in turns if item["turn"]["interpretacao"]["candidates"]) >= 50


def test_library_rejects_what_the_interpreter_contract_rejects():
    good = {"id": "A-9999", "dimensao": "A", "tema": "Trajetória de conferência do validador",
            "perfil": "iniciante", "idioma": "pt", "registro": "informal", "fonte": "brasil",
            "passos": [{"usuario": "quero a densidade dos municípios", "acao": "PROPOE_ANALISE", "interpretacao": {
                **NONE, "operation": "density", "indicator": "density", "territory": "municípios"}},
                {"usuario": "mostra no mapa", "acao": "MUDA_VISUALIZACAO", "interpretacao": {
                    **NONE, "intent": "CONVERSACIONAL", "dialogue": "show_map"}}]}
    contract = llm_bridge.library_contract()
    assert library.validate([good], contract, SPEC) == []

    def broken(**changes):
        record = jsonlib.loads(jsonlib.dumps(good))
        record["passos"][0]["interpretacao"].update(changes)
        return library.validate([record], contract, SPEC)
    assert broken(operation="nearest")  # capacidade só do motor
    assert broken(indicator="quantity")  # densidade não aceita quantidade
    assert broken(period="2024")  # valor que a mensagem não traz
    assert broken(social_reply="Calculei para você!")  # cortesia fora da lista fechada
    assert broken(candidates=[{"operation": "density", "indicator": "density", "anchor": "densidade dos municípios"},
                              {"operation": "ranking", "indicator": "density", "anchor": "Quero tudo"}])


# ------------------------------------------------------------------------------ consumo pelo provedor

def test_examples_reach_the_provider_masked_like_the_user_message(monkeypatch, collection):
    answer, body = ask(monkeypatch, "quero comparar a densidade de dois municípios do meu estado")
    block = block_of(body)
    assert block.startswith("\n\n" + library.HEADER)
    assert "Exemplo 1" in block and "Saída: {" in block
    trace = answer["biblioteca"]
    assert trace["versao"] == collection.version and 1 <= len(trace["exemplos"]) <= library.examples_per_request()
    chosen = {item["id"]: item for item in collection.turns}
    assert all(example in chosen for example in trace["exemplos"])
    # Exemplos pertinentes: ao menos um mostra a comparação pedida.
    assert any(chosen[example]["turn"]["interpretacao"]["operation"] == "comparisons" for example in trace["exemplos"])
    # A máscara do pedido vale para os exemplos: nenhum valor, campo ou arquivo da base sai do backend.
    for value in PROTECTED:
        assert not present(value, block), value
    assert len(block) <= library.MAX_BLOCK + 2
    assert answer["executed"] is False and answer["verification"]["ready_to_execute"] is False


def test_disabling_the_library_restores_the_previous_request(monkeypatch):
    message = "quero ver a distribuição dos médicos"
    enabled, with_library = ask(monkeypatch, message)
    monkeypatch.setenv("ADT_BIBLIOTECA_CONVERSACIONAL", "0")
    disabled, without_library = ask(monkeypatch, message)
    assert without_library["systemInstruction"]["parts"][0]["text"] == llm_bridge._SYSTEM
    assert with_library["contents"] == without_library["contents"]
    assert with_library["generationConfig"] == without_library["generationConfig"]
    assert "biblioteca" in enabled and "biblioteca" not in disabled
    assert {key: value for key, value in enabled.items() if key != "biblioteca"} == disabled


def test_examples_without_a_base_follow_the_same_sanitization(monkeypatch, collection):
    answer, body = ask(monkeypatch, "hola, ¿qué puedo analizar aquí?", base=False)
    block = block_of(body)
    assert "CONTINUIDADE_VERIFICADA" not in block  # sem base não há projeção de continuidade no pedido real
    by_id = {item["id"]: item for item in collection.turns}
    assert all(library.mode(by_id[example]["state"]) == "sem_base" for example in answer["biblioteca"]["exemplos"])
    for line in block.splitlines():
        if line.startswith("Mensagem atual:"):
            assert line == "Mensagem atual: «" + llm_bridge._sanitize(line[len("Mensagem atual: «"):-1]) + "»"


def test_session_context_selects_examples_of_the_same_moment(monkeypatch, collection):
    token = client.post("/api/session").json()["token"]
    # A mensagem precisa chegar ao provedor: "quero ver esse resultado…" é lida antes, pelo canal determinístico.
    answer, body = ask(monkeypatch, "dá pra ver isso num gráfico de barras?", headers={"X-ADT-Session": token},
                       answer={**NONE, "intent": "CONVERSACIONAL", "dialogue": "show_chart"})
    assert body["contents"][0]["parts"][0]["text"].startswith("CONTINUIDADE_VERIFICADA: ")
    assert "CONTINUIDADE_VERIFICADA: {" in block_of(body)
    assert answer["dialogue_action"] == "show_chart" and answer["proposal"]["operation"] is None
    by_id = {item["id"]: item for item in collection.turns}
    assert any(by_id[example]["turn"]["interpretacao"]["dialogue"] == "show_chart"
               for example in answer["biblioteca"]["exemplos"])


def test_the_library_never_changes_what_the_backend_accepts(monkeypatch):
    # O provedor continua sem autoridade: valores não ancorados saem, mesmo com exemplos no pedido.
    answer, _ = ask(monkeypatch, "quero a densidade dos municípios", answer={
        **NONE, "operation": "density", "indicator": "density", "period": "2031", "territory": "municípios"})
    assert answer["proposal"]["operation"] == "density" and answer["proposal"]["period"] == ""
    assert answer["requires_confirmation"] is True and answer["executed"] is False


# ------------------------------------------------------------------------------ minimização

def test_masking_many_texts_at_once_equals_masking_each_text():
    rng = random.Random(20261020)
    words = ["Saúde", "saude", "norte", "Manaus", "médicos", "2024", "a-b", "quantidade", "x", "São Paulo", "1,5",
             "12.345", "SÃO PAULO", "e", "de", "Belém", "belem", "CPF: 123.456.789-09", "joao@example.com"]
    protected = llm_bridge._protected(["Saúde", "norte", "São Paulo", "a-b", "x", "quantidade", "BELÉM"])
    for _ in range(300):
        texts = [" ".join(rng.choice(words) for _ in range(rng.randint(1, 8))) for _ in range(rng.randint(1, 6))]
        assert llm_bridge._minimize_many(texts, protected) == [llm_bridge._minimize(text, protected) for text in texts]


# ------------------------------------------------------------------------------ pertinência e desempenho

@pytest.mark.parametrize("message,state,key,value", [
    ("e no mapa, como fica?", RESULT, "dialogue", "show_map"),
    ("volta pro que eu tinha antes", RESULT, "dialogue", "previous_result"),
    ("como é calculada essa densidade?", STATE, "topic", "density"),
    ("como os quintis são definidos?", STATE, "topic", "distribution"),
    ("quero ver a distribuição dos médicos", STATE, "operation", "distribution"),
    ("show me how the number of doctors changed over the years", STATE, "operation", "temporal"),
    ("¿la distancia es por carretera?", STATE, "topic", "spatial"),
    ("explica de um jeito mais simples", RESULT, "dialogue", "simplify"),
])
def test_selection_brings_examples_of_the_same_intention(collection, message, state, key, value):
    chosen = collection.select(message, [], state)
    assert any(item["turn"]["interpretacao"][key] == value for item in chosen), [item["id"] for item in chosen]


def test_examples_are_pertinent_on_unseen_conversations(collection, held_out):
    """Antes da biblioteca, o modelo não recebia exemplos; agora recebe os pertinentes à mensagem e ao contexto."""
    assert not library.validate(held_out, llm_bridge.library_contract(), SPEC)
    assert len(held_out) >= 200 and {record["dimensao"] for record in held_out} == set(library.DIMENSIONS)
    report = library_evaluation.evaluate(collection, held_out)
    # Só comandos canônicos coincidem com a biblioteca; o resto foi escrito sem acesso a ela.
    assert report["repetidos"] <= 0.05 * (report["turnos"] + report["repetidos"])
    table = library_evaluation.table(report)
    print(table)
    if os.environ.get("GITHUB_STEP_SUMMARY"):
        with open(os.environ["GITHUB_STEP_SUMMARY"], "a", encoding="utf-8") as fh:
            fh.write("### Biblioteca conversacional: exemplos entregues ao modelo em conversas inéditas\n\n" + table + "\n")
    ours, fixed, drawn = (report["estrategias"][name] for name in ("biblioteca", "fixos", "aleatorios"))
    assert ours["com_exemplos"] >= 0.98
    assert ours["acerto_em_k"] >= 0.80 and ours["voto"] >= 0.55
    assert ours["acerto_em_k"] >= fixed["acerto_em_k"] + 0.15 and ours["voto"] >= drawn["voto"] + 0.25
    # Nenhuma dimensão nem idioma fica sem exemplos pertinentes.
    assert all(group["acerto_em_k"] >= 0.75 for group in report["grupos"].values()), report["grupos"]
    assert report["latencia_ms"]["p95"] < 50


def test_loading_and_selecting_are_fast():
    start = time.perf_counter()
    records, version = library.read()
    fresh = library.Library(records, version)
    assert time.perf_counter() - start < 6
    start = time.perf_counter()
    for message in ("quero a densidade de médicos no Pará", "e em 2019?", "mostra no mapa", "o que é quintil?"):
        fresh.select(message, ["quero a densidade de médicos no Pará"], RESULT)
    assert (time.perf_counter() - start) / 4 < 0.05


# ------------------------------------------------------------------------------ base versionada (somente leitura)

@pytest.fixture(scope="module")
def official():
    folder = os.getenv("ADT_REAL_DATA_DIR")
    if not folder:
        pytest.skip("Defina ADT_REAL_DATA_DIR para testar as bases locais somente em leitura")
    paths = [path for path in Path(folder).iterdir() if path.suffix.lower() in (".csv", ".xlsx")]
    before = {path: hashlib.sha256(path.read_bytes()).hexdigest() for path in paths}
    import main
    frame = main._brazil_sources().frame("municipal")
    yield llm_bridge._protected(main.protected_values(frame, ""))
    assert before == {path: hashlib.sha256(path.read_bytes()).hexdigest() for path in paths}


def test_examples_with_the_official_base_carry_no_base_value(collection, official):
    items = [item for item in collection.turns if library.mode(item["state"]) == "base"]
    texts = [item["turn"]["usuario"] for item in items]
    masked = []
    for start in range(0, len(texts), 64):
        masked += llm_bridge._minimize_many(texts[start:start + 64], official)
    assert [text for text in masked if llm_bridge._mask_values(text, official) != text] == []
    anchor = lambda value, text: bool(llm_bridge._anchor(value, text))  # noqa: E731
    usable = sum(library._output(item["turn"]["interpretacao"], text, anchor) is not None
                 for item, text in zip(items, masked))
    assert usable >= 0.97 * len(items)
