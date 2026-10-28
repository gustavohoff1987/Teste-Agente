"""Tempo da conversa e o começo sem base (pedido do responsável, 26/10/2026).

- Orçamento do pedido: depois de 20 s de conversa no mesmo pedido, nenhuma chamada nova ao provedor começa, nem regeneração
  nem redação; a resposta verificada responde (com TPL-08 só quando um texto do Gemini foi recusado). A chamada em curso
  continua com o prazo de 75 s por operação (decisão de 21/10/2026).
- Começo sem base, na página única: o pedido de análise feito antes da escolha dos dados recebe na hora o lembrete de escolher
  a base, sem o provedor; perguntas de conceito e conversa continuam pelo caminho de sempre. Desde 28/10/2026, com um estado,
  uma região ou o próprio Brasil citados, a oferta dos dados do Brasil; com os dados da pessoa citados, a oferta do envio; com
  os dados do Brasil citados como fonte, a escolha deles.
Nenhuma chamada externa real: o provedor é simulado, e o relógio do pedido é ajustado direto na variável de contexto.
"""
import asyncio
import time

import pytest
from fastapi.testclient import TestClient

import conversa_gemini
import conversa_grafico
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
# Desde 28/10/2026, os pedidos com um estado do Brasil ("Compare os municípios do Pará pela densidade", "mostre a tendência
# em Minas Gerais", que estavam aqui) recebem a oferta dos dados do Brasil (teste seguinte); "quero analisar X" vale com
# qualquer objeto, inclusive um município, que sem a base não é reconhecido como lugar do Brasil (CFG-TER).
@pytest.mark.parametrize("mensagem", ["Quero analisar a densidade", "quais os 5 municípios com maior densidade?",
                                      "compare o de maior e o de menor densidade", "quero analisar Recife",
                                      "quero analisar"])
def test_pedido_de_analise_sem_base_recebe_na_hora_o_lembrete_de_escolher_os_dados(proibido, mensagem):
    inicio = time.perf_counter()
    resposta = client.post("/api/llm/interpret", json={"message": mensagem, "lembrar_base": True})
    assert resposta.status_code == 200, resposta.text
    corpo = resposta.json()
    assert corpo["aguarda_base"] is True and corpo["reply"] == main.ESCOLHA_DOS_DADOS
    assert "fonte_sugerida" not in corpo and "fonte_escolhida" not in corpo
    assert corpo["reply"].startswith("Para fazer essa análise, primeiro escolha os dados: use os dados do Brasil ou envie "
                                     "os seus")
    assert corpo["proposal"]["operation"] is None and corpo["executed"] is False and "painel" not in corpo
    assert corpo["origin"] == "CANAL_SISTEMICO" and time.perf_counter() - inicio < 5


@pytest.mark.parametrize("mensagem,quem", [
    ("quero analisar o acre", "Para analisar o Acre"), ("quero analisar pernambuco", "Para analisar Pernambuco"),
    ("Compare os municípios do Pará pela densidade", "Para analisar o Pará"),
    ("mostre a tendência em Minas Gerais", "Para analisar Minas Gerais"), ("e a Bahia?", "Para analisar a Bahia"),
    ("olá, quero analisar pernambuco", "Para analisar Pernambuco"),
    ("como está a região Nordeste e o Distrito Federal?", "Para analisar o Nordeste e o Distrito Federal"),
    ("quero ver SP e RJ", "Para esse pedido"),
    ("você consegue analisar Pernambuco?", "Para analisar Pernambuco"), ("qual a densidade no Brasil?", "Para esse pedido")])
def test_pedido_sem_base_com_lugar_do_brasil_recebe_na_hora_a_oferta_dos_dados_do_brasil(proibido, mensagem, quem):
    """Antes da escolha dos dados (28/10/2026): um estado ou uma região do Brasil (os nomes da regra governada da fonte
    municipal) ou o próprio Brasil mostram que o pedido é sobre os dados do Brasil; a resposta os oferece na hora, sem o
    provedor, e o pedido fica guardado (antes, "quero analisar o acre" ia ao provedor e voltava "Não identifiquei uma análise
    inequívoca")."""
    inicio = time.perf_counter()
    resposta = client.post("/api/llm/interpret", json={"message": mensagem, "lembrar_base": True})
    assert resposta.status_code == 200, resposta.text
    corpo = resposta.json()
    assert corpo["aguarda_base"] is True and corpo["fonte_sugerida"] == "brasil" and "fonte_escolhida" not in corpo
    assert corpo["reply"] == quem + ", posso usar os dados do Brasil: escolha “Usar dados do Brasil” ou responda “sim”. Se " \
        "preferir, envie os seus, em CSV ou Excel. Assim que a base estiver pronta, sigo com o seu pedido."
    assert corpo["proposal"]["operation"] is None and corpo["executed"] is False and "painel" not in corpo
    assert corpo["origin"] == "CANAL_SISTEMICO" and time.perf_counter() - inicio < 5


def test_pedido_sem_base_com_a_fonte_citada_escolhe_os_dados_do_brasil_ou_oferece_o_envio(proibido):
    corpo = client.post("/api/llm/interpret", json={"message": "quero analisar pernambuco com os dados do Brasil",
                                                    "lembrar_base": True}).json()
    assert corpo["aguarda_base"] is True and corpo["fonte_escolhida"] == "brasil" and "fonte_sugerida" not in corpo
    assert corpo["reply"] == "Dados do Brasil escolhidos. Vou prepará-los e, em seguida, sigo com o seu pedido."
    corpo = client.post("/api/llm/interpret", json={"message": "quero analisar minha planilha de enfermeiros",
                                                    "lembrar_base": True}).json()
    assert corpo["aguarda_base"] is True and corpo["fonte_sugerida"] == "arquivo" and "fonte_escolhida" not in corpo
    assert corpo["reply"] == ("Para analisar os seus dados, escolha “Enviar meus dados” ou responda “sim”: a janela de envio "
                              "aceita CSV ou Excel e traz o modelo de planilha. Assim que a base estiver pronta, sigo com o seu "
                              "pedido.")
    # A fonte citada sem pedido de análise segue o caminho de antes (a descrição dos dados fica na tela).
    assert conversa_grafico.pedido_antes_dos_dados("Dados do Brasil em 2024") is None


def test_lugares_do_brasil_sem_catalogo_novo_e_sem_falsos_positivos():
    lugares = conversa_grafico.lugares_do_brasil
    assert lugares("quero analisar para entender a densidade")["lugares"] == []  # "para", a preposição
    assert lugares("estado do para")["lugares"] == lugares("o Pará")["lugares"] == [("estado", "15")]
    assert lugares("SE EU QUISER ANALISAR") == {"lugares": [], "brasil": False}  # tudo em maiúsculas: nenhuma sigla
    # A sigla só diz que o pedido é sobre o Brasil: com a base escolhida, a conversa procura os estados pelo nome.
    assert lugares("quero ver SP e RJ") == {"lugares": [], "brasil": True}
    assert lugares("o sul do país e o Rio Grande do Sul")["lugares"] == [("estado", "43")]  # "sul" sozinho não é a região
    assert lugares("região sul e Mato Grosso do Sul")["lugares"] == [("regiao", "Sul"), ("estado", "50")]
    # Nenhum catálogo de cidades (CFG-TER): sem a base escolhida, o nome de um município não é lugar do Brasil, e o pedido
    # recebe o lembrete de escolher os dados.
    assert lugares("quero analisar Recife") == {"lugares": [], "brasil": False}
    assert conversa_grafico.pedido_antes_dos_dados("quero analisar Recife") == {"fonte": None, "escolhida": False,
                                                                                 "texto": None}
    for conversa in ("você consegue analisar planilhas?", "o que você analisa?", "Me conte uma curiosidade",
                     "O que é densidade?", "me mostre como funciona o agente"):
        assert conversa_grafico.pedido_antes_dos_dados(conversa) is None, conversa


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
