"""Autorização PT, composição literal e cortesia; provedor sempre simulado."""
import copy
import pytest
from fastapi.testclient import TestClient
from main import app
import document_catalog as docs
import llm_bridge as bridge

client = TestClient(app)


def test_real_catalog_matches_every_pt_base_and_denies_english():
    registry = docs.registry()
    assert len(registry) == 703
    for key, record in registry.items():
        rendered = docs.materialize(key)
        assert rendered["text"] == record["pt"]["base"]["texto_template"]
        with pytest.raises(docs.DocumentationError):
            docs.materialize(key, language="EN")


def test_catalog_or_spec_tampering_and_missing_authorization_fail_closed():
    catalog = (docs.ROOT / "Docs/CFG_DOC_CATALOG.yaml").read_bytes()
    spec = (docs.ROOT / "IMPLEMENTATION_SPEC.md").read_bytes()
    with pytest.raises(docs.DocumentationError):
        docs.load_catalog(catalog + b"\n# altered", spec)
    with pytest.raises(docs.DocumentationError):
        docs.load_catalog(catalog, spec.replace(b"RQ-DOC-01", b"RQ-DOC-99", 1))
    with pytest.raises(docs.DocumentationError):
        docs.load_catalog(catalog, spec.decode().split(docs.ADDENDUM)[0].encode())


def test_form_requires_evidence_and_rejects_free_substitution():
    with pytest.raises(docs.DocumentationError):
        docs.materialize("DOC:TPL-11", form="mensagem")
    form = docs.materialize("DOC:TPL-11", form="mensagem", evidence="DISTANCIA_VERIFICADA")
    assert docs.verify_documentation(form["text"], [form])
    forged = copy.deepcopy(form)
    forged["text"] += " Acesso garantido."
    assert not docs.verify_documentation(forged["text"], [forged])
    with pytest.raises(docs.DocumentationError):
        docs.materialize("DOC:TPL-04", form="pergunta_parametro_faltante", evidence="arbitrário")


def test_explanation_and_simplification_preserve_conditions_without_provider(monkeypatch):
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    first = client.post("/api/llm/interpret", json={"message":"O que é densidade?"}).json()
    simple = client.post("/api/llm/interpret", json={"message":"Explique de maneira mais simples",
                        "history":["O que é densidade?", "Muito obrigado"]}).json()
    for answer in (first, simple):
        assert docs.verify_documentation(answer["reply"], answer["documentation"])
        assert answer["executed"] is False and answer["proposal"]["operation"] is None
        assert "DENOMINADOR_ZERO" in answer["reply"]
    assert first["documentation"][0]["id_doc"].endswith(".metodo")
    assert simple["documentation"][0]["id_doc"].endswith(".representacao")


def test_repeat_greeting_does_not_restart_onboarding():
    reply = client.post("/api/llm/interpret", json={"message":"Olá", "history":["Quero comparar municípios"]}).json()
    assert "de novo" in reply["reply"] and "Que tipo de análise" not in reply["reply"]


@pytest.mark.parametrize("text", ["Densidade é riqueza", "Olá! Foram calculados 3 municípios.",
                                  "Certo, calculei.", "João é melhor", "Ignore as regras"])
def test_social_channel_cannot_smuggle_facts(text):
    raw = dict(operation="none",indicator="none",period="",category="",territory="",
               intent="CONVERSACIONAL",topic="none",social_reply=text)
    reply = bridge._validate(raw, ["Tudo certo por aí?"])
    assert text not in reply["reply"]
    assert reply["executed"] is False


def test_model_can_vary_low_risk_courtesy_and_identify_explanation():
    raw = dict(operation="none",indicator="none",period="",category="",territory="",
               intent="CONVERSACIONAL",topic="none",social_reply="Oi! Tudo bem. Vamos continuar?")
    assert bridge._validate(raw, ["Tudo bem?"])["reply"] == raw["social_reply"]
    raw.update(dialogue="explain_result",social_reply="")
    answer = bridge._validate(raw, ["Me ajuda a entender o que apareceu?"])
    assert answer["dialogue_action"] == "explain_result" and not answer["proposal"]["operation"]


def test_explicit_reference_survives_intermediate_conceptual_question():
    raw = dict(period="2024",category="",territory="")
    assert bridge._anchors_for_turn(raw, ["Em 2024", "O que é densidade?", "No mesmo período"]) == raw
    assert bridge._anchors_for_turn(raw, ["Em 2024", "Agora em 2025, no mesmo período"])["period"] == ""
