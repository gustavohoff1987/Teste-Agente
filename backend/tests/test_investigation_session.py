"""Resultados acumulados: a apresentação nunca vira fonte de verdade do servidor."""
from concurrent.futures import ThreadPoolExecutor
from copy import deepcopy

import pytest
from fastapi import HTTPException
from conversation_session import sessions, SessionStore, TIMEOUT
from result_conversation import verify_segments
from test_conversation_session import client, session, request, isolated, OPTIONS


def calculate(headers, operation='density', **extra):
    response = request(headers, route='analyze', operation=operation, **extra)
    assert response.status_code == 200, response.text
    return response.json()


def test_active_result_switches_without_recalculating_or_trusting_visual_values(monkeypatch):
    headers = session()
    first = calculate(headers)
    second = calculate(headers, 'counts')
    third = calculate(headers, 'comparisons')
    def forbidden(*args, **kwargs):
        raise AssertionError('Navegar e ler resultados não autoriza cálculo nem envio ao provedor')
    monkeypatch.setattr('main.compute', forbidden)
    monkeypatch.setattr('llm_bridge._call_gemini', forbidden)
    for result in (first, second, third, first):
        response = request(headers, 'O que esse resultado significa?', displayed_result_id=result['result_id'])
        assert response.status_code == 200, response.text
        answer = response.json()
        assert answer['result_reference']['result_id'] == result['result_id']
        assert verify_segments(answer['segments'], result)
        assert not answer['executed']
    assert len(sessions.sessions[headers['X-ADT-Session']].results) == 3


def test_65_calculations_preserve_first_64_references_and_return_last_result():
    headers = session()
    results = [calculate(headers, 'counts') for _ in range(65)]
    assert len({r['result_id'] for r in results}) == 65
    assert all(r['conversation_reference']['available'] for r in results[:64])
    assert results[-1]['conversation_reference']['available'] is False
    assert results[0]['rows'] == results[-1]['rows']
    for result in (results[0], results[32], results[63]):
        response = client.get('/api/session/result/' + result['result_id'], headers=headers)
        assert response.status_code == 200
        assert response.json()['result']['rows'] == result['rows']
    missing = client.get('/api/session/result/' + results[-1]['result_id'], headers=headers)
    assert missing.status_code == 404
    assert len(sessions.sessions[headers['X-ADT-Session']].results) == 64


def test_simultaneous_results_have_distinct_verified_identity_and_isolation():
    headers = session()
    with ThreadPoolExecutor(max_workers=4) as pool:
        results = list(pool.map(lambda _: calculate(headers, 'counts'), range(8)))
    assert len({r['result_id'] for r in results}) == 8
    assert len({r['metadata']['execution_key'] for r in results}) == 1
    outsider = session()
    for result in results:
        route = '/api/session/result/' + result['result_id']
        assert client.get(route, headers=headers).json()['result']['rows'] == result['rows']
        assert client.get(route, headers=outsider).status_code == 404


def test_expired_result_cannot_be_reopened_and_read_does_not_extend_retention():
    now = [0.0]
    store = SessionStore(lambda: now[0])
    token = store.create()['token']
    # Resultado real do motor, copiado exclusivamente para testar o relógio da sessão.
    result = calculate(session())
    assert store.record_result(token, 0, result, {})
    now[0] = TIMEOUT - 1
    assert store.result(token, result['result_id'])['result']['rows'] == result['rows']
    now[0] = TIMEOUT
    with pytest.raises(HTTPException) as error:
        store.result(token, result['result_id'])
    assert error.value.status_code == 410
    assert not store.sessions


def test_modified_result_and_stale_revision_never_replace_verified_history():
    headers = session()
    original = calculate(headers)
    changed = deepcopy(original)
    changed['rows'][0]['Densidade por 1.000'] = -12345
    route = '/api/session/result/' + original['result_id']
    assert client.get(route, headers=headers).json()['result']['rows'] == original['rows']
    assert client.post('/api/session/revision', headers=headers, json={'revision': 5}).status_code == 200
    stale = request(headers, route='analyze', operation='counts', context_revision=4)
    assert stale.status_code == 409
    assert len(sessions.sessions[headers['X-ADT-Session']].results) == 1
    record = sessions.sessions[headers['X-ADT-Session']].results[original['result_id']]
    record['result']['rows'] = changed['rows']
    assert client.get(route, headers=headers).status_code == 409


def test_unavailable_relation_requires_preparation_and_cannot_be_induced_by_multiple_results():
    headers = session()
    first = calculate(headers)
    calculate(headers, 'counts', settings={**OPTIONS, 'territory_ids': ['code:003']})
    answer = request(headers, 'Qual desses territórios apresenta maior densidade?', displayed_result_id=first['result_id']).json()
    assert answer['needs_calculation'] and not answer['executed']
    assert answer['clarification']['choices'][0]['operation'] == 'comparisons'
    assert len(sessions.sessions[headers['X-ADT-Session']].results) == 2
