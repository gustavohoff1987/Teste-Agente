"""Contexto e resultados locais: isolamento, prazo, concorrência e minimização."""
import json
import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient
from main import app
from conversation_session import SessionStore, sessions, TIMEOUT
import llm_bridge

client = TestClient(app)
RAW = ("Municipio;Codigo;Periodo;Categoria;Quantidade;Populacao\n"
       "Vila Secreta;001;202406;MEDICINA;10;1000\n"
       "Outra Vila;002;202406;MEDICINA;20;1000\n"
       "Nova Vila;003;202406;MEDICINA;30;1000\n").encode()
MAP = dict(territory="Municipio",territory_id="Codigo",period="Periodo",category="Categoria",
           count="Quantidade",population="Populacao")
OPTIONS = dict(confirmed_roles=list(MAP), count_unit="pessoas", population_denominator_confirmed=True,
               comparison_confirmed=True, period_filter="202406", exploration_operation="comparisons",
               territory_ids=["code:001","code:002"])


@pytest.fixture(autouse=True)
def isolated(monkeypatch):
    sessions.sessions.clear()
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    monkeypatch.setattr(llm_bridge, "_counter", 0)
    yield
    sessions.sessions.clear()


def session():
    return {"X-ADT-Session": client.post("/api/session").json()["token"]}


def request(headers, message="E agora?", *, route="llm/interpret-context", **extra):
    opts = extra.pop("settings", OPTIONS)
    return client.post("/api/"+route, headers=headers, files={"file":("private.csv", RAW)},
        data={"message":message,"mapping":json.dumps(MAP),"options":json.dumps(opts), **extra})


def test_context_names_and_current_selection_are_resolved_locally():
    headers = session()
    response = request(headers)
    assert response.status_code == 200, response.text
    body = response.json()
    assert "Vila Secreta" in body["reply"] and "Outra Vila" in body["reply"]
    assert "Nova Vila" not in body["reply"]
    assert body["context_reference"]["origin"] == "BACKEND_VERIFIED_STATE"
    assert body["executed"] is False
    changed = request(headers, context_revision=1, settings={**OPTIONS,"territory_ids":["code:003"]}).json()
    assert "Nova Vila" in changed["reply"] and "Vila Secreta" not in changed["reply"]


def test_deictic_selection_correction_and_addition_do_not_calculate():
    headers = session()
    for message, ids, indicator in [("Compare esses municípios", ["code:001","code:002"],"density"),
                                    ("Não, quantidade", ["code:001","code:002"],"quantity"),
                                    ("Acrescente Nova Vila", ["code:001","code:002","code:003"],"density")]:
        r=request(headers,message,route="exploration/interpret")
        assert r.status_code == 200, r.text
        body=r.json()
        assert body["territory_ids"] == ids and not body["executed"]
        assert body["options_patch"]["comparison_indicator"] == indicator


def test_result_reference_is_server_owned_and_session_scoped():
    one, two = session(), session()
    computed = request(one, route="analyze", operation="comparisons")
    assert computed.status_code == 200, computed.text
    result = computed.json()
    assert result["conversation_reference"]["available"] is True
    identity = result["result_id"]
    original = client.get("/api/session/result/"+identity, headers=one).json()
    assert original["result"]["rows"] == result["rows"]
    result["rows"][0]["Diferença A − B"] = 999999
    assert client.get("/api/session/result/"+identity, headers=one).json() == original
    assert client.get("/api/session/result/"+identity, headers=two).status_code == 404
    assert request(two, displayed_result_id=identity).status_code == 404
    assert request(one, displayed_result_id="fabricado").status_code == 404


def test_expiry_is_not_renewed_by_read_or_revision_and_close_discards_everything():
    now = [0.0]
    store = SessionStore(lambda: now[0])
    token = store.create()["token"]
    capture = store.capture(token, 0, {"selection":["private"]})
    capture["context"]["selection"].append("forged")
    assert store.sessions[token].context["selection"] == ["private"]
    now[0] = TIMEOUT - 1
    store.status(token)
    store.revision(token, 2)
    now[0] = TIMEOUT
    with pytest.raises(HTTPException) as exc:
        store.status(token)
    assert exc.value.status_code == 410 and token not in store.sessions
    token = store.create()["token"]
    now[0] += 100
    store.event(token,"MUDANCA_PARAMETRO")
    assert store.status(token)["expires_in"] == TIMEOUT
    with pytest.raises(HTTPException):
        store.event(token,"POLLING")
    store.close(token)
    with pytest.raises(HTTPException):
        store.remember(token,0,{})


@pytest.mark.parametrize("close",[False,True])
def test_changed_or_closed_context_rejects_late_provider_response(monkeypatch,close):
    headers=session()
    token=headers["X-ADT-Session"]
    async def provider(*args):
        if close: sessions.close(token)
        else: sessions.revision(token,1)
        return dict(operation="none",indicator="none",period="",category="",territory="",
                    intent="CONVERSACIONAL",topic="none",social_reply="Olá!")
    monkeypatch.setenv("GEMINI_API_KEY","offline")
    monkeypatch.setattr(llm_bridge,"_call_gemini",provider)
    response=request(headers,"Tudo certo por aí?")
    assert response.status_code == (410 if close else 409), response.text
    if close: assert token not in sessions.sessions


def test_protected_dataset_literals_and_dialogue_context_never_leave_backend(monkeypatch):
    headers=session()
    sent=[]
    async def provider(messages,*_):
        sent.extend(messages)
        return dict(operation="none",indicator="none",period="",category="",territory="",
                    intent="CONVERSACIONAL",topic="none",social_reply="Entendi.")
    monkeypatch.setenv("GEMINI_API_KEY","offline")
    monkeypatch.setattr(llm_bridge,"_call_gemini",provider)
    response=request(headers,"Me ajude a estudar Vila Secreta em 202406, MEDICINA, Populacao 1000")
    assert response.status_code == 200, response.text
    content=" ".join(sent)
    for value in ("Vila Secreta","202406","MEDICINA","Populacao","1000",headers["X-ADT-Session"]):
        assert value not in content
    assert "CONTINUIDADE_VERIFICADA" in content
