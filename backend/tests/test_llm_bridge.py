"""Testes offline da primeira iteração Gemini: nenhuma chamada externa real."""
import pytest
import httpx
from fastapi.testclient import TestClient

import llm_bridge
from main import app


client = TestClient(app)


@pytest.fixture(autouse=True)
def reset_local_limits(monkeypatch):
    monkeypatch.setattr(llm_bridge, "_counter", 0)
    monkeypatch.setattr(llm_bridge, "_counter_day", "")
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    monkeypatch.delenv("ADT_GEMINI_MODEL", raising=False)


def test_without_key_is_degraded_and_keeps_analytical_engine_available():
    status = client.get("/api/llm/status")
    assert status.status_code == 200
    assert status.json()["configured"] is False and status.json()["disponivel"] is False
    assert status.json()["executes_analyses"] is False
    assert status.json()["indisponibilidade"]["tipo"] == "indisponivel"
    # Sem o provedor, a conversa responde com a comunicação cordial (seção 11.4), sem código nem mensagem técnica.
    response = client.post("/api/llm/interpret", json={"message": "Densidade de médicos"})
    assert response.status_code == 200
    assert response.json()["indisponibilidade"] == {"tipo": "indisponivel", "titulo": llm_bridge.TITULO_INDISPONIVEL,
                                                    "texto": llm_bridge.TEXTO_INDISPONIVEL}
    assert response.json()["reply"] == llm_bridge.TEXTO_INDISPONIVEL and "GEMINI_API_KEY" not in response.text
    assert client.get("/api/health").status_code == 200


def test_interpretation_is_structured_sanitized_and_does_not_execute(monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "test-private-key")
    captured = {}

    async def fake_model(sent, model, api_key):
        captured.update(sent=sent, model=model, api_key=api_key)
        return {"intent": "ANALITICO", "topic": "none", "operation": "distribution", "indicator": "density",
                "period": "202406", "category": "médicos", "territory": "municípios"}

    monkeypatch.setattr(llm_bridge, "_call_gemini", fake_model)
    question = "Quero distribuição da densidade de médicos por municípios em 202406"
    response = client.post("/api/llm/interpret", json={"message": question})
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["executed"] is False
    assert body["origin"] == "INTERPRETACAO_LLM"
    assert body["proposal"]["operation"] == "distribution"
    assert body["proposal"]["indicator"] == "density"
    assert body["proposal"]["period"] == "202406"
    assert body["proposal"]["category"] == "médicos"
    assert captured["model"] == "gemini-3.5-flash-lite"
    assert captured["api_key"] == "test-private-key"
    assert "test-private-key" not in response.text
    assert "file" not in captured
    assert client.get("/api/llm/status").json()["requests_used_today"] == 1


def test_redaction_occurs_before_external_call(monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "secret")
    seen = []

    async def fake_model(sent, _model, _key):
        seen.extend(sent)
        return {"intent": "ANALITICO", "topic": "none", "operation": "density", "indicator": "density",
                "period": "2024", "category": "médicos", "territory": ""}
    monkeypatch.setattr(llm_bridge, "_call_gemini", fake_model)
    response = client.post("/api/llm/interpret", json={
        "message": "Quero densidade de médicos em 2024. CPF: 123.456.789-09, João Silva, joao@example.com."
    })
    assert response.status_code == 200, response.text
    joined = " ".join(seen)
    for forbidden in ("123.456.789-09", "João", "Silva", "joao@example.com"):
        assert forbidden not in joined
    assert "PROTEGID" in joined


@pytest.mark.parametrize("question", ["Quantos médicos existem no Brasil?", "Quantas médicas existem no Brasil?"])
def test_quantity_question_preserves_interrogative_without_exposing_identifiers(monkeypatch, question):
    monkeypatch.setenv("GEMINI_API_KEY", "test-only")
    captured = []

    async def provider(sent, _model, _key):
        captured.extend(sent)
        return {"intent": "ANALITICO", "topic": "none", "operation": "counts", "indicator": "quantity",
                "period": "", "category": "", "territory": "Brasil"}

    monkeypatch.setattr(llm_bridge, "_call_gemini", provider)
    response = client.post("/api/llm/interpret", json={
        "message": question + " Contato: João Silva, joao@example.com, CPF 123.456.789-09."})
    assert response.status_code == 200, response.text
    assert response.json()["proposal"]["operation"] == "counts"
    assert response.json()["executed"] is False
    sent = " ".join(captured)
    assert question in sent
    for identifier in ("João Silva", "joao@example.com", "123.456.789-09"):
        assert identifier not in sent


def test_discard_model_invented_entities_and_unknown_schema(monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "secret")
    async def fake_model(_sent, _model, _key):
        return {"intent": "ANALITICO", "topic": "none", "operation": "density", "indicator": "density",
                "period": "2035", "category": "Neurocirurgiões", "territory": "Fortaleza"}
    monkeypatch.setattr(llm_bridge, "_call_gemini", fake_model)
    response = client.post("/api/llm/interpret", json={"message": "Quero analisar médicos em 2024"})
    assert response.status_code == 200
    assert response.json()["proposal"]["period"] == ""
    assert response.json()["proposal"]["category"] == ""
    assert response.json()["proposal"]["territory"] == ""

    calls = []

    async def bad_model(_sent, _model, _key):
        calls.append(1)
        return {"intent": "ANALITICO", "topic": "none", "operation": "invented_operation", "indicator": "density"}
    monkeypatch.setattr(llm_bridge, "_call_gemini", bad_model)
    invalid = client.post("/api/llm/interpret", json={"message": "Quero analisar médicos em 2024"})
    # Operação inventada é violação do contrato: 2 regenerações e a resposta de reserva, sem operação proposta.
    assert invalid.status_code == 200 and invalid.json()["reserva"] is True and len(calls) == 3
    assert invalid.json()["proposal"]["operation"] is None


def test_unknown_model_is_blocked_before_api(monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "secret")
    monkeypatch.setenv("ADT_GEMINI_MODEL", "model-billing-unknown")

    async def unexpected(*_args):
        raise AssertionError("modelo não autorizado não chega ao provedor")
    monkeypatch.setattr(llm_bridge, "_call_gemini", unexpected)
    response = client.post("/api/llm/interpret", json={"message": "Comparar médicos"})
    assert response.status_code == 200 and response.json()["indisponibilidade"]["tipo"] == "indisponivel"
    assert "secret" not in response.text and "model-billing-unknown" not in response.text


# ---------------------------------------------------------------- sem teto local; cotas reais do provedor (seção 11)
def _modelo_simples(chamadas):
    async def modelo(_sent, _model, _key):
        chamadas.append(1)
        return {"intent": "ANALITICO", "topic": "none", "operation": "distribution", "indicator": "density",
                "period": "", "category": "", "territory": ""}
    return modelo


def test_no_local_daily_cap_after_the_old_mark_of_20_calls(monkeypatch):
    # O teto local de 20 chamadas saiu (26/10/2026): sem outro teto, o consumo só é monitorado. Instrumentado, sem rede.
    assert not hasattr(llm_bridge, "MAX_REQUESTS_PER_DAY")
    monkeypatch.setenv("GEMINI_API_KEY", "secret")
    chamadas = []
    monkeypatch.setattr(llm_bridge, "_call_gemini", _modelo_simples(chamadas))
    for _ in range(25):
        assert client.post("/api/llm/interpret", json={"message": "Analisar distribuição"}).status_code == 200
    from datetime import date
    monkeypatch.setattr(llm_bridge, "_counter_day", date.today().isoformat())
    monkeypatch.setattr(llm_bridge, "_counter", 5000)
    assert client.post("/api/llm/interpret", json={"message": "Analisar distribuição"}).json()["proposal"]["operation"] \
        == "distribution"
    assert len(chamadas) == 26
    status = client.get("/api/llm/status").json()
    assert status["requests_used_today"] == 5001 and "local_daily_limit" not in status and status["disponivel"] is True


class _Resposta429:
    """Resposta HTTP 429 do provedor, como a API do Gemini a devolve (RESOURCE_EXHAUSTED, QuotaFailure e RetryInfo)."""

    def __init__(self, quota_id, retry="37s"):
        import httpx as _httpx
        details = [{"@type": "type.googleapis.com/google.rpc.QuotaFailure",
                    "violations": [{"quotaMetric": "generativelanguage.googleapis.com/generate_content_free_tier_requests",
                                    "quotaId": quota_id}]}]
        if retry:
            details.append({"@type": "type.googleapis.com/google.rpc.RetryInfo", "retryDelay": retry})
        self.resposta = _httpx.Response(429, json={"error": {"code": 429, "status": "RESOURCE_EXHAUSTED",
                                                             "message": "Quota exceeded", "details": details}})


def _cliente_http(respostas, chamadas):
    class Cliente:
        def __init__(self, **kwargs):
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, *args):
            return None

        async def post(self, *args, **kwargs):
            chamadas.append(1)
            resposta = respostas[min(len(chamadas), len(respostas)) - 1]
            if isinstance(resposta, Exception):
                raise resposta
            return resposta
    return Cliente


def _resposta_ok():
    return httpx.Response(200, json={"candidates": [{"content": {"parts": [{"text":
        '{"intent":"ANALITICO","topic":"none","operation":"distribution","indicator":"density","period":"",'
        '"category":"","territory":""}'}]}}]})


@pytest.mark.parametrize("quota_id,escopo,minimo,maximo", [
    ("GenerateRequestsPerMinutePerProjectPerModel-FreeTier", "minuto", 36, 38),
    ("GenerateContentInputTokensPerModelPerMinute-FreeTier", "tokens_por_minuto", 36, 38),
    ("GenerateRequestsPerDayPerProjectPerModel-FreeTier", "dia", 60, 25 * 3600),
])
def test_provider_429_puts_the_provider_on_hold_with_cordial_message_and_no_repeated_calls(monkeypatch, quota_id, escopo,
                                                                                           minimo, maximo):
    import time
    monkeypatch.setenv("GEMINI_API_KEY", "secret")
    chamadas = []
    monkeypatch.setattr(llm_bridge.httpx, "AsyncClient", _cliente_http([_Resposta429(quota_id).resposta], chamadas))
    antes = time.time()
    primeira = client.post("/api/llm/interpret", json={"message": "Analisar distribuição"})
    # Limite confirmado pelo provedor: a mensagem A, sem código, sem "quota", sem "429".
    assert primeira.status_code == 200 and primeira.json()["indisponibilidade"]["tipo"] == "cota"
    assert primeira.json()["reply"] == llm_bridge.TEXTO_COTA
    assert not any(t in primeira.text for t in ("429", "RESOURCE_EXHAUSTED", "Quota", "secret"))
    status = client.get("/api/llm/status").json()
    assert status["disponivel"] is False and status["espera"]["causa"] == "cota" and status["espera"]["escopo"] == escopo
    assert minimo <= llm_bridge.em_espera()["ate"] - antes <= maximo
    # Durante a espera, nenhuma chamada sai: a próxima mensagem recebe o mesmo aviso, sem tentativa repetida.
    for _ in range(3):
        assert client.post("/api/llm/interpret", json={"message": "Analisar distribuição"}).json()[
            "indisponibilidade"]["tipo"] == "cota"
    assert chamadas == [1] and status["monitoramento"]["cota"] == 1


def test_provider_recovers_after_the_hold_without_restarting_the_session(monkeypatch):
    import time
    monkeypatch.setenv("GEMINI_API_KEY", "secret")
    chamadas = []
    monkeypatch.setattr(llm_bridge.httpx, "AsyncClient", _cliente_http(
        [_Resposta429("GenerateRequestsPerMinutePerProjectPerModel-FreeTier", "2s").resposta, _resposta_ok()], chamadas))
    assert client.post("/api/llm/interpret", json={"message": "Analisar distribuição"}).json()["indisponibilidade"]
    agora = time.time()
    monkeypatch.setattr(llm_bridge.time, "time", lambda: agora + 5)  # passou a espera informada pelo provedor
    retomada = client.post("/api/llm/interpret", json={"message": "Analisar distribuição"})
    assert retomada.status_code == 200 and "indisponibilidade" not in retomada.json()
    assert retomada.json()["proposal"]["operation"] == "distribution" and chamadas == [1, 1]
    assert client.get("/api/llm/status").json()["disponivel"] is True


@pytest.mark.parametrize("falha,escopo", [(httpx.Response(503, text="overloaded"), "provedor"),
                                         (httpx.ReadTimeout("lento"), "tempo_esgotado"),
                                         (httpx.ConnectError("sem rota"), "rede")])
def test_temporary_unavailability_is_not_reported_as_quota(monkeypatch, falha, escopo):
    monkeypatch.setenv("GEMINI_API_KEY", "secret")
    chamadas = []
    monkeypatch.setattr(llm_bridge.httpx, "AsyncClient", _cliente_http([falha], chamadas))
    resposta = client.post("/api/llm/interpret", json={"message": "Analisar distribuição"})
    assert resposta.status_code == 200 and resposta.json()["indisponibilidade"]["tipo"] == "indisponivel"
    assert resposta.json()["reply"] == llm_bridge.TEXTO_INDISPONIVEL and "limite" not in resposta.json()["reply"]
    espera = client.get("/api/llm/status").json()["espera"]
    assert espera["causa"] == "indisponivel" and espera["escopo"] == escopo
    assert llm_bridge.em_espera()["ate"] - __import__("time").time() <= llm_bridge.ESPERA_FALHA_TEMPORARIA + 1
    client.post("/api/llm/interpret", json={"message": "Analisar distribuição"})
    assert chamadas == [1]  # sem repetição automática durante a espera curta


def test_request_body_limits():
    response = client.post("/api/llm/interpret", json={"message": "a" * 801})
    assert response.status_code == 422


def test_history_is_limited_and_only_user_text_is_sent(monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "secret")
    seen = []

    async def fake_model(sent, _model, _key):
        seen.extend(sent)
        return {"intent": "ANALITICO", "topic": "none", "operation": "none", "indicator": "none",
                "period": "", "category": "", "territory": ""}
    monkeypatch.setattr(llm_bridge, "_call_gemini", fake_model)
    response = client.post("/api/llm/interpret",
                           json={"message": "E quanto à distribuição?", "history": [
                               "Quero analisar médicos", "Em municípios"]})
    assert response.status_code == 200
    assert len(seen) == 3
    assert response.json()["proposal"]["operation"] is None
    excessive = client.post("/api/llm/interpret",
                            json={"message": "E quanto à distribuição?", "history": ["Pergunta"] * 5})
    assert excessive.status_code == 422


def test_http_transport_uses_json_schema_header_and_no_dataset(monkeypatch):
    import asyncio
    import httpx
    captured = {}

    class FakeHTTPClient:
        def __init__(self, *args, **kwargs):
            captured["timeout"] = kwargs["timeout"]

        async def __aenter__(self):
            return self

        async def __aexit__(self, *_args):
            return None

        async def post(self, url, headers, json):
            captured.update(url=url, headers=headers, body=json)
            return httpx.Response(200, json={"candidates": [{"content": {"parts": [{
                "text": '{"operation":"distribution","indicator":"density","period":"2024",'
                        '"category":"médicos","territory":"municípios"}'
            }]}}]})

    monkeypatch.setattr(llm_bridge.httpx, "AsyncClient", FakeHTTPClient)
    response = asyncio.run(llm_bridge._call_gemini(
        ["Quero distribuição da densidade de médicos em municípios em 2024"],
        "gemini-3.5-flash-lite", "test-secret"))
    assert response["operation"] == "distribution"
    assert captured["url"].startswith("https://generativelanguage.googleapis.com/")
    assert captured["headers"]["x-goog-api-key"] == "test-secret"
    assert captured["timeout"] == 75.0
    assert captured["body"]["generationConfig"]["responseMimeType"] == "application/json"
    assert "responseSchema" in captured["body"]["generationConfig"]
    assert all(k not in captured["body"] for k in ("file", "mapping", "rows", "data"))
    assert "test-secret" not in str(captured["body"])


@pytest.mark.parametrize("failure", [
    httpx.ConnectTimeout, httpx.ReadTimeout, httpx.WriteTimeout, httpx.PoolTimeout,
    httpx.ConnectError, httpx.ReadError, httpx.WriteError, httpx.RemoteProtocolError,
])
def test_api_distinguishes_timeout_from_other_transport_errors(monkeypatch, failure):
    """A conversa responde com o aviso cordial (sem o detalhe privado do transporte), e o diagnóstico técnico distingue o
    tempo esgotado das demais falhas de transporte."""
    monkeypatch.setenv("GEMINI_API_KEY", "test-private-key")
    calls = []

    class FailingClient:
        def __init__(self, **kwargs):
            assert kwargs["timeout"] == 75.0

        async def __aenter__(self):
            return self

        async def __aexit__(self, *args):
            return None

        async def post(self, *args, **kwargs):
            calls.append(1)
            raise failure("detalhe privado do transporte: test-private-key")

    monkeypatch.setattr(llm_bridge.httpx, "AsyncClient", FailingClient)
    response = client.post("/api/llm/interpret", json={"message": "Comparar médicos"})
    assert response.status_code == 200
    assert response.json()["indisponibilidade"]["texto"] == llm_bridge.TEXTO_INDISPONIVEL
    expected = "tempo_esgotado" if issubclass(failure, httpx.TimeoutException) else "rede"
    assert client.get("/api/llm/status").json()["espera"]["escopo"] == expected
    assert "privado" not in response.text and "test-private-key" not in response.text
    assert calls == [1]  # Sem nova tentativa automática ou consumo duplicado.
    assert llm_bridge._EXAMPLES.get() == ""
    assert client.get("/api/health").status_code == 200
