"""Tempo da conversa e o começo sem base (pedido do responsável, 26/10/2026).

- Orçamento do pedido: depois de 20 s de conversa no mesmo pedido, nenhuma chamada nova ao provedor começa, nem regeneração
  nem redação; a resposta verificada responde (com TPL-08 só quando um texto do Gemini foi recusado). A chamada em curso
  continua com o prazo de 75 s por operação (decisão de 21/10/2026).
- Começo sem base, na página única: o pedido de análise feito antes da escolha dos dados recebe na hora o lembrete de escolher
  a base, sem o provedor; perguntas de conceito e conversa continuam pelo caminho de sempre.
Nenhuma chamada externa real: o provedor é simulado, e o relógio do pedido é ajustado direto na variável de contexto.
"""
import asyncio
import time

import pytest
from fastapi.testclient import TestClient

import conversa_gemini
import llm_bridge
import main
from document_catalog import materialize

client = TestClient(main.app)


@pytest.fixture(autouse=True)
def sem_chave_real(monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "teste-sem-chave-real")
    monkeypatch.delenv("ADT_CONVERSA_GEMINI", raising=False)
    monkeypatch.delenv("ADT_GEMINI_MODEL", raising=False)


@pytest.fixture
def proibido(monkeypatch):
    """O provedor não pode ser chamado."""
    async def falha(*_args, **_kwargs):
        raise AssertionError("o provedor de IA não pode ser chamado")
    monkeypatch.setattr(llm_bridge, "_call_gemini", falha)
    monkeypatch.setattr(llm_bridge, "generate_structured", falha)


def test_relogio_do_pedido_marca_o_orcamento():
    assert llm_bridge.sem_tempo_para_regenerar() is False  # sem relógio (fora de uma rota da conversa), nunca esgota
    marca = llm_bridge._INICIO_DO_PEDIDO.set(time.monotonic())
    try:
        assert llm_bridge.sem_tempo_para_regenerar() is False
        llm_bridge._INICIO_DO_PEDIDO.set(time.monotonic() - llm_bridge.ORCAMENTO_DE_REGENERACAO - 1)
        assert llm_bridge.sem_tempo_para_regenerar() is True
        llm_bridge.iniciar_relogio()
        assert llm_bridge.sem_tempo_para_regenerar() is False
    finally:
        llm_bridge._INICIO_DO_PEDIDO.reset(marca)
    assert llm_bridge.ORCAMENTO_DE_REGENERACAO == 20.0 and llm_bridge.TIMEOUT_SEGUNDOS == 75.0


def test_interpretacao_fora_do_contrato_nao_regenera_depois_do_orcamento(monkeypatch):
    chamadas = []

    async def fora_do_contrato(_enviado, _modelo, _chave):
        chamadas.append(1)
        return {"intent": "ANALITICO", "topic": "none", "operation": "operacao_inventada", "indicator": "density"}
    monkeypatch.setattr(llm_bridge, "_call_gemini", fora_do_contrato)
    monkeypatch.setattr(llm_bridge, "sem_tempo_para_regenerar", lambda: True)
    resposta = client.post("/api/llm/interpret", json={"message": "Quero analisar médicos em 2024"})
    # Sem o orçamento, seriam a primeira e mais 2 regenerações (test_llm_bridge); depois dele, só a primeira e a reserva.
    assert resposta.status_code == 200 and resposta.json()["reserva"] is True and len(chamadas) == 1
    assert resposta.json()["proposal"]["operation"] is None


def test_redacao_nao_comeca_depois_do_orcamento_e_a_resposta_verificada_responde(monkeypatch, proibido):
    monkeypatch.setattr(conversa_gemini, "ativa", lambda: True)
    monkeypatch.setattr(llm_bridge, "sem_tempo_para_regenerar", lambda: True)
    redigida = asyncio.run(conversa_gemini.redigir(contexto={}, refs=None, reserva="Resposta verificada do motor."))
    assert redigida == {"texto": "Resposta verificada do motor.", "origem": "DETERMINISTICA", "tentativas": 0,
                        "motivo": "tempo"}


def test_texto_recusado_nao_e_regenerado_depois_do_orcamento(monkeypatch, proibido):
    monkeypatch.setattr(conversa_gemini, "ativa", lambda: True)
    monkeypatch.setattr(llm_bridge, "sem_tempo_para_regenerar", lambda: True)
    monkeypatch.setattr(conversa_gemini.fidelidade, "conferir", lambda texto, refs: ["V-07: ordem diferente da do motor"])
    redigida = asyncio.run(conversa_gemini.redigir(contexto={}, refs=None, reserva="Resposta verificada do motor.",
                                                   rascunho="TEFE (AM) tem a maior densidade."))
    aviso = materialize("DOC:TPL-08", form="mensagem", evidence="REGENERACAO_ESGOTADA")["text"]
    assert redigida["texto"] == "Resposta verificada do motor.\n\n" + aviso and "TEFE" not in redigida["texto"]
    assert (redigida["origem"], redigida["tentativas"], redigida["motivo"]) == ("DETERMINISTICA", 1, "conferencia")


# --------------------------------------------------------------------------------------------- começo sem base
@pytest.mark.parametrize("mensagem", ["Compare os municípios do Pará pela densidade", "Quero analisar a densidade",
                                      "quais os 5 municípios com maior densidade?", "mostre a tendência em Minas Gerais",
                                      "compare o de maior e o de menor densidade"])
def test_pedido_de_analise_sem_base_recebe_na_hora_o_lembrete_de_escolher_os_dados(proibido, mensagem):
    inicio = time.perf_counter()
    resposta = client.post("/api/llm/interpret", json={"message": mensagem, "lembrar_base": True})
    assert resposta.status_code == 200, resposta.text
    corpo = resposta.json()
    assert corpo["aguarda_base"] is True and corpo["reply"] == main.ESCOLHA_DOS_DADOS
    assert corpo["reply"].startswith("Para fazer essa análise, primeiro escolha os dados: use os dados do Brasil ou envie "
                                     "os seus")
    assert corpo["proposal"]["operation"] is None and corpo["executed"] is False and "painel" not in corpo
    assert corpo["origin"] == "CANAL_SISTEMICO" and time.perf_counter() - inicio < 5


@pytest.mark.parametrize("mensagem,trecho", [("O que é densidade?", "Fórmula: D(u, p, c)"),
                                             ("Muito obrigada pela ajuda!", "De nada"),
                                             ("O que o agente é capaz de fazer?", "critérios combinados")])
def test_conceito_e_conversa_sem_base_nao_recebem_o_lembrete(monkeypatch, proibido, mensagem, trecho):
    monkeypatch.setenv("ADT_CONVERSA_GEMINI", "0")  # o texto do catálogo, sem redação
    corpo = client.post("/api/llm/interpret", json={"message": mensagem, "lembrar_base": True}).json()
    assert "aguarda_base" not in corpo and trecho.lower() in corpo["reply"].lower()


def test_sem_o_campo_da_pagina_a_interpretacao_preliminar_continua(monkeypatch):
    """O lembrete é da página única (campo `lembrar_base`); sem ele, a rota interpreta o pedido como antes."""
    chamadas = []

    async def modelo(_enviado, _modelo, _chave):
        chamadas.append(1)
        return {"intent": "ANALITICO", "topic": "none", "operation": "distribution", "indicator": "density", "period": "",
                "category": "", "territory": ""}
    monkeypatch.setattr(llm_bridge, "_call_gemini", modelo)
    monkeypatch.setenv("ADT_CONVERSA_GEMINI", "0")
    resposta = client.post("/api/llm/interpret", json={"message": "Quero analisar a densidade"})
    assert resposta.status_code == 200 and len(chamadas) == 1 and "aguarda_base" not in resposta.json()
