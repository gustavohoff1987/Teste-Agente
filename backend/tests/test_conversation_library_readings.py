"""Leitura do resultado na biblioteca conversacional: o `doc` esperado é exatamente o que o sistema apresenta.

Resultados reais calculados pela API (densidade, quantitativos e comparações) e a forma de "documentação
insuficiente" das demais análises, comparados com `conversation_library.reading_documents`, a regra que o validador
aplica às trajetórias. Sem provedor: as mensagens são reconhecidas pelo canal determinístico.
"""
import pytest

import conversation_library as library
import llm_bridge
from result_conversation import SUPPORTED, answer_result
from test_conversation_session import isolated, session  # noqa: F401 - isolated: sessões limpas e sem Gemini
from test_result_conversation import compute, talk

MESSAGES = ("O que esse resultado significa?", "Por que esse resultado apareceu?",
            "Por que o resultado mostra a menor densidade?", "Explique o motivo desse resultado")


def expected(message, operation):
    return library.reading_documents(message, {"has_verified_result": True, "result_operation": operation},
                                     llm_bridge.library_contract())


def test_the_library_reads_the_same_analyses_as_the_conversation():
    assert set(library.READABLE) == set(SUPPORTED)


@pytest.mark.parametrize("operation", ["density", "counts", "comparisons"])
def test_readings_cite_the_forms_the_result_conversation_presents(operation):
    h = session()
    result = compute(h, operation)
    for message in MESSAGES:
        reply = talk(h, result, message)
        assert reply["result_status"] == "VERIFICADO", reply
        assert [form["id_doc"] for form in reply.get("documentation", [])] == expected(message, operation), message


@pytest.mark.parametrize("operation", ["temporal", "aggregate", "distribution", "ranking", "spatial", "nearest"])
def test_analyses_without_conversational_reading_cite_the_insufficiency_form(operation):
    record = {"result": {"result_id": "r", "metadata": {"validity": "VALIDO", "operation": operation,
                                                        "execution_key": "k"}},
              "context": {"source": "s", "signature": "a"}}
    capture = {"context": {"source": "s", "signature": "a", "operation": None}, "revision": 0}
    for message in MESSAGES:
        answer = answer_result(message, "explain_result", record, capture)
        assert [form["id_doc"] for form in answer["documentation"]] == expected(message, operation), message
