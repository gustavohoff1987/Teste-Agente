"""Conversa no gráfico da página única (contrato de 22/10/2026, seção 4; Docs/CONVERSACAO_INCREMENTO_FN.md).

O pedido vira o comando `painel` (família, indicador, nível, municípios, competência, janela, visão, referência, função,
seleção, ordenação, condições e grupos), sem cálculo e sem o provedor de IA no caminho local. Os nomes são resolvidos
pelo catálogo da base; ambiguidade vira pergunta com alternativas em botões, e nada muda no gráfico. Fontes sintéticas
(o perfil oficial da base do Brasil e uma planilha de distritos e províncias, sem código IBGE); no fim, a base versionada
no job dados-reais (ADT_REAL_DATA_DIR), somente em leitura.
"""
import hashlib
import json
import os
from pathlib import Path

import pandas as pd
import pytest
from fastapi.testclient import TestClient
from openpyxl import Workbook

import brazil_data
import conversa_grafico
import llm_bridge
import main
from brazil_catalog_profile import FIELDS, apply_curated_options
from brazil_data import FILES, GOVERNED_MANIFEST, manifest_from_repository
from catalog_support import write_state_source
from install_brazil_data import install
from territorial_selection import STATES

client = TestClient(main.app)
# Municípios sintéticos com os códigos IBGE reais: homônimos (SANTAREM no PA e na PB), estado com nome de município
# (São Paulo; Paraná, estado, e PARANA, município do RN) e o Amazonas no gráfico.
UNIDADES = {"130260": "MANAUS", "130420": "TEFE", "130340": "PARINTINS", "130185": "IRANDUBA", "130250": "MANACAPURU",
            "150140": "BELEM", "150680": "SANTAREM", "251365": "SANTAREM", "355030": "SAO PAULO", "350950": "CAMPINAS",
            "410690": "CURITIBA", "240860": "PARANA"}
PERIODOS = [str(ano) + mes for ano in range(2021, 2025) for mes in ("01", "06")]
AM = ["code:130185", "code:130250", "code:130260", "code:130340", "code:130420"]
# Estado do gráfico que a tela envia (contrato, seção 4): os municípios do Amazonas, densidade, junho de 2024.
CONTEXTO = {"painel_familia": "distribuicao", "painel_indicador": "densidade", "painel_nivel": "municipios",
            "painel_municipios": {"todos": False, "estados": ["13"], "ids": []}, "territory_ids": AM,
            "period_filter": "202406", "conversation_today": "2024-10-22"}


def painel(**campos):
    """O comando completo: as chaves não citadas ficam nulas (o gráfico mantém o que tem)."""
    return {**dict.fromkeys(conversa_grafico.CHAVES), **campos}


def brasil():
    """Fonte municipal com o perfil oficial: os estados vêm do prefixo do código IBGE."""
    frame = pd.DataFrame([{"municipio": nome, "cod_ibge": codigo, "Período (ano e mês)": periodo,
                           "categoria_profissional": "MEDICINA", "quantidade": "10", "população_estimada": "1000",
                           "latitude": "-3", "longitude": "-60"}
                          for periodo in PERIODOS for codigo, nome in UNIDADES.items()])
    frame.attrs["source"] = {"dataset": "brazil", "scope": "municipal"}
    campos = dict(FIELDS["municipal"])
    return frame, campos, apply_curated_options(frame, campos, {})


def pedir(mensagem, **extra):
    """Interpretação local da página única, com o contexto do gráfico (None tira a chave do contexto)."""
    frame, campos, ajustes = brasil()
    opcoes = {chave: valor for chave, valor in {**CONTEXTO, **extra}.items() if valor is not None}
    ctx = conversa_grafico.contexto(opcoes)
    return conversa_grafico.interpretar(mensagem, frame, campos, ajustes, ctx, brasil=True,
                                        opcoes=conversa_grafico.opcoes_do_interprete(opcoes, ctx))


# ----------------------------------------------------------------------------------- mapeamento das operações atuais
@pytest.mark.parametrize("operacao,esperado", [
    ("density", {"familia": "distribuicao", "indicador": "densidade"}),
    ("counts", {"familia": "distribuicao", "indicador": "quantidade"}),
    ("distribution", {"familia": "distribuicao"}),
    ("temporal", {"familia": "tendencia"}),
    ("spatial", {"familia": "espacial"}),
    ("nearest", {"familia": "espacial"}),
    ("comparisons", {"funcao": "comparar"}),
    ("aggregate", {"funcao": "juntar"}),
    ("ranking", {"funcao": "ordenar"}),
    ("criteria", {"funcao": "condicoes"}),
    ("rotation", {"familia": "rotatividade"}),
    ("report", {"funcao": "exportar"}),
])
def test_cada_operacao_atual_vira_familia_ou_funcao(operacao, esperado):
    assert conversa_grafico.painel_da_operacao(operacao) == painel(**esperado)


def test_indicador_e_grupos_da_operacao_proposta():
    assert conversa_grafico.painel_da_operacao("temporal", "density") == painel(familia="tendencia", indicador="densidade")
    assert conversa_grafico.painel_da_operacao("distribution", "quantity", "Quero a distribuição em quintis") == painel(
        familia="distribuicao", indicador="quantidade", grupos={"tipo": "quintis"})
    assert conversa_grafico.painel_da_operacao("none") is None and conversa_grafico.painel_da_operacao(None) is None


def test_respostas_locais_anteriores_viram_o_mesmo_comando():
    """Fora da página única, a resposta de sempre ganha o painel equivalente (mapeamento das operações atuais)."""
    legado = conversa_grafico.painel_do_legado
    assert legado({"handled": True, "operation": "comparisons", "territory_ids": ["code:1", "code:2"],
                   "options_patch": {"comparison_indicator": "density", "period_filter": "202406"}}) == painel(
        funcao="comparar", selecao=["code:1", "code:2"], indicador="densidade", competencia="202406")
    assert legado({"handled": True, "operation": "temporal", "territory_ids": [], "estados": ["43"],
                   "options_patch": {"period_filter": "", "period_filters": ["202301", "202406"],
                                     "temporal_indicator": "quantity"}}) == painel(
        familia="tendencia", indicador="quantidade", janela=["202301", "202406"], nivel="estados")
    assert legado({"handled": True, "operation": "criteria", "criteria_patch": {"mode": "replace", "leaf": {
        "attribute": "densidade", "operator": "<", "value": "2", "unit": "por_1000_habitantes"}}}) == painel(
        funcao="condicoes", condicoes=[{"atributo": "densidade", "operador": "<", "valor": 2}])
    assert legado({"handled": True, "operation": "criteria", "criteria_patch": {
        "ranking": {"attribute": "distancia", "direction": "desc"}}}) == painel(
        funcao="ordenar", ordenar={"atributo": "distancia_km", "ordem": "desc", "primeiros": None})
    # Pergunta pendente ou pedido não tratado: nada muda no gráfico.
    assert legado({"handled": True, "operation": "comparisons", "clarification": "Com qual outro?"}) is None
    assert legado({"handled": False}) is None


# ----------------------------------------------------------------------------------- frases novas
def test_um_estado_inteiro_vira_os_municipios_dele():
    body = pedir("Mostre o Pará")
    assert body == {"handled": True, "executed": False, "reply": "Mostrei a densidade nos 2 municípios do Pará.",
                    "painel": painel(nivel="municipios", municipios={"todos": False, "estados": ["15"], "ids": []})}
    assert pedir("os municípios do Pará")["painel"] == body["painel"]
    # "para" sem acento é a preposição; depois do artigo, é o estado.
    assert pedir("mostre o Para")["painel"] == body["painel"]
    todos = pedir("mostre todos os municípios")
    assert todos["painel"]["municipios"] == {"todos": True, "estados": [], "ids": []}
    assert todos["reply"] == "Mostrei a densidade em todos os 12 municípios."


def test_referencia_por_nome_por_conjunto_ou_por_criterio():
    esperado = painel(familia="espacial", referencia={"membros": ["code:150140"]})
    body = pedir("use Belém como referência")
    assert body["painel"] == esperado and body["executed"] is False
    assert body["reply"] == ("Usei BELEM (PA) como referência: o eixo X passa a mostrar a distância em linha reta (km) até "
                             "ela.")
    assert pedir("distância até Belém")["painel"] == esperado
    assert pedir("A referência é Belém")["painel"] == esperado
    conjunto = pedir("use Manaus e Belém como conjunto de referência")
    assert conjunto["painel"] == painel(familia="espacial", referencia={"membros": ["code:130260", "code:150140"]})
    assert conjunto["reply"].endswith("como conjunto de referência: o eixo X mostra a distância em linha reta (km) até o "
                                      "membro mais próximo.")
    criterio = pedir("use como referência o município de maior densidade")
    assert criterio["painel"] == painel(familia="espacial", referencia={
        "membros": [], "criterio": {"atributo": "densidade", "ordem": "desc"}})
    # O critério abre o Território de referência com o atributo citado e, desde 25/10/2026 (decisão 4), o operador do "maior"
    # ou "menor"; a relação, a delimitação e o valor de corte são da pessoa (antes de 24/10, a lista de candidatos abria na
    # ordem para "usar o primeiro", que saiu; de 24 a 25/10, o "maior/menor" ficava sem efeito).
    assert criterio["reply"] == ("Abri o Território de referência com a condição Densidade “Maior que”: escolha a relação (mais "
                                 "próximo ou mais distante), a delimitação e o valor de corte, e o eixo X mostra a distância em "
                                 "linha reta (km) até o território de referência de cada município.")
    menor = pedir("use como referência o município de menor densidade")
    assert menor["painel"]["referencia"] == {"membros": [], "criterio": {"atributo": "densidade", "ordem": "asc"}}
    assert menor["reply"].startswith("Abri o Território de referência com a condição Densidade “Menor que”: ")
    populosos = pedir("use como referência o município mais populoso")
    assert populosos["painel"]["referencia"] == {"membros": [], "criterio": {"atributo": "populacao", "ordem": "desc"}}
    assert populosos["reply"].startswith("Abri o Território de referência com a condição População “Maior que”: ")
    assert pedir("abra a análise espacial")["reply"] == (
        "Abri a análise espacial: defina o Território de referência (a relação, a delimitação e a condição) ou diga o nome "
        "dele, e o eixo X mostra a distância em linha reta (km) até ele.")
    # Estado não é referência (não tem um ponto único); nome desconhecido é perguntado.
    assert pedir("use o Amazonas como referência") == {"handled": True, "executed": False,
                                                       "clarification": conversa_grafico.SEM_PONTO_UNICO}
    desconhecido = pedir("use Belen como referência")
    assert "painel" not in desconhecido and desconhecido["clarification"].startswith("Não encontrei “Belen”")


def test_os_n_com_maior_ou_menor_viram_ordenar():
    body = pedir("os 5 municípios com maior densidade")
    assert body["painel"] == painel(funcao="ordenar", ordenar={"atributo": "densidade", "ordem": "desc", "primeiros": 5})
    assert body["reply"] == ("Ordenei os municípios pela densidade, do maior para o menor, e destaquei os 5 primeiros; "
                             "empates na posição de corte também entram.")
    assert pedir("os 3 com menor quantidade")["painel"]["ordenar"] == {"atributo": "quantidade", "ordem": "asc",
                                                                       "primeiros": 3}
    assert pedir("quais os dez mais populosos?")["painel"]["ordenar"] == {"atributo": "populacao", "ordem": "desc",
                                                                          "primeiros": 10}
    # Sem a direção, a pergunta oferece as duas; cada botão envia o pedido completo.
    pergunta = pedir("ordene pela densidade")
    assert "painel" not in pergunta and pergunta["clarification"].startswith(
        "Ordenar pela densidade do maior para o menor ou do menor para o maior?")
    assert [escolha["label"] for escolha in pergunta["choices"]] == ["Do maior para o menor", "Do menor para o maior"]
    assert pedir(pergunta["choices"][0]["draft"])["painel"]["ordenar"] == {"atributo": "densidade", "ordem": "desc",
                                                                           "primeiros": None}
    # A distância precisa de uma referência.
    assert "escolha antes a referência" in pedir("os 5 mais distantes")["clarification"]


def test_condicoes_combinadas_com_a_referencia_da_distancia():
    body = pedir("municípios com menos de 1 médico por mil e a mais de 150 km de Manaus")
    assert body["painel"] == painel(funcao="condicoes", familia="espacial", referencia={"membros": ["code:130260"]},
                                    condicoes=[{"atributo": "densidade", "operador": "<", "valor": 1},
                                               {"atributo": "distancia_km", "operador": ">", "valor": 150}])
    assert body["reply"] == ("Apliquei as condições densidade < 1 por mil habitantes e distância > 150 km até MANAUS (AM): "
                             "o gráfico separa quem atende a todas, quem não atende e quem não tem dado.")
    # "2 médicos" pode ser quantidade ou densidade: botões, e cada um é um pedido sem ambiguidade.
    duvida = pedir("municípios com menos de 2 médicos")
    assert "painel" not in duvida and duvida["ambiguity"] == "AMBIGUIDADE_MATERIAL"
    assert [(escolha["label"], escolha["draft"]) for escolha in duvida["choices"]] == [
        ("Densidade < 2 por mil habitantes", "municípios com menos de 2 médicos por mil habitantes"),
        ("Quantidade < 2", "municípios com quantidade de médicos menor que 2")]
    assert pedir(duvida["choices"][1]["draft"])["painel"]["condicoes"] == [
        {"atributo": "quantidade", "operador": "<", "valor": 2}]
    assert "combinam com “e”" in pedir("municípios com densidade abaixo de 1 ou população acima de 50 mil habitantes")[
        "clarification"]
    # Distância sem referência: com a análise espacial ativa, vale a referência do gráfico; sem ela, a conversa pergunta.
    assert "A distância é medida até a referência" in pedir("municípios a mais de 150 km")["clarification"]
    espacial = pedir("municípios a mais de 150 km", painel_familia="espacial", painel_referencia=["code:150140"])
    assert espacial["painel"] == painel(funcao="condicoes", condicoes=[
        {"atributo": "distancia_km", "operador": ">", "valor": 150}])
    tambem = pedir("agora também população acima de 10000 habitantes",
                   painel_condicoes=[{"atributo": "densidade", "operador": "<", "valor": 1}])
    assert tambem["painel"]["condicoes"] == [{"atributo": "densidade", "operador": "<", "valor": 1},
                                             {"atributo": "populacao", "operador": ">", "valor": 10000}]


def test_comparar_e_juntar_municipios_nomeados():
    body = pedir("compare Manaus e Tefé")
    assert body["painel"] == painel(funcao="comparar", selecao=["code:130260", "code:130420"])
    # Sem nome de bastidor na resposta (24/10/2026; antes, "vêm do motor").
    assert body["reply"] == "Abri a comparação lado a lado de MANAUS (AM) e TEFE (AM), com o maior, o menor e a diferença."
    # Município fora do gráfico entra nele para a comparação.
    fora = pedir("compare Manaus e Belém")
    assert fora["painel"] == painel(funcao="comparar", selecao=["code:130260", "code:150140"], nivel="municipios",
                                    municipios={"todos": False, "estados": ["13"], "ids": ["code:150140"]})
    assert fora["reply"].endswith("Acrescentei BELEM (PA) ao gráfico.")
    junte = pedir("junte Manaus, Iranduba e Manacapuru")
    assert junte["painel"] == painel(funcao="juntar", selecao=["code:130260", "code:130185", "code:130250"])
    assert junte["reply"] == ("Juntei MANAUS (AM), IRANDUBA (AM) e MANACAPURU (AM) num conjunto: a bolha soma as contagens "
                              "dos componentes, com possível dupla contagem (quem atua em mais de um município conta em "
                              "cada um).")
    # Estados se comparam no nível dos estados, na ordem do pedido; nunca junto com municípios.
    estados = pedir("compare o Pará e o Amazonas")
    assert estados["painel"] == painel(funcao="comparar", selecao=["uf:15", "uf:13"], nivel="estados")
    assert estados["reply"].startswith("Mostrei os estados e abri a comparação lado a lado de Pará (PA) e Amazonas (AM)")
    assert "não ficam no mesmo gráfico" in pedir("compare Manaus e o Pará")["clarification"]
    assert "o pedido tem 4" in pedir("compare Manaus, Tefé, Parintins e Iranduba")["clarification"]
    # Um nome só: a conversa pergunta o outro e guarda a pendência; a mensagem seguinte, só com nomes, completa o pedido.
    pendente = pedir("compare Manaus")
    assert pendente["clarification"] == ("Identifiquei MANAUS (AM). Com qual outro município você quer comparar? Diga um ou "
                                         "dois nomes. Nada mudou no gráfico.")
    assert pendente["pending_operation"] == "comparisons" and pendente["pending_ids"] == ["code:130260"]
    assert "painel" not in pendente
    seguinte = {"conversation_pending_operation": "comparisons", "conversation_pending_ids": ["code:130260"]}
    completa = pedir("Tefé e Parintins", **seguinte)
    assert completa["painel"] == painel(funcao="comparar", selecao=["code:130260", "code:130420", "code:130340"])
    # Outro comando ou uma pergunta não completam a pendência: a mensagem segue o seu próprio sentido.
    assert pedir("mostre Tefé", **seguinte)["painel"]["funcao"] is None
    assert pedir("compare Tefé e Parintins", **seguinte)["painel"]["selecao"] == ["code:130420", "code:130340"]


def test_periodo_da_tendencia_anual_ou_semestral_com_os_ultimos_4_periodos():
    """Tendência (24/10/2026): os períodos são sempre os últimos 4 do ritmo escolhido, anual ou semestral, sem janela longa.
    O ritmo citado dá a janela (a mesma da tela, painelModel.janelaDoRitmo); um período sem ritmo (anos, datas, "todas as
    competências"), mesmo ambíguo, vira a pergunta do ritmo, com um botão por ritmo que reescreve o pedido. Antes, "tendência nos
    últimos 4 anos" abria as 8 competências; a cobertura dos atalhos de janela passou para estas conferências."""
    anuais, semestrais = ["202106", "202206", "202306", "202406"], ["202301", "202306", "202401", "202406"]
    anual = pedir("tendência anual")
    assert anual["painel"] == painel(familia="tendencia", janela=anuais)
    assert anual["reply"] == ("Abri a tendência da densidade, com os últimos 4 períodos anuais (junho de 2021, junho de 2022, "
                              "junho de 2023 e junho de 2024).")
    assert pedir("mostre a tendência semestral")["painel"] == painel(familia="tendencia", janela=semestrais)
    serie = pedir("use a série anual de junho", painel_familia="tendencia")
    assert serie["painel"] == painel(janela=anuais)
    assert serie["reply"] == ("Período da tendência: anual, com os últimos 4 períodos (junho de 2021, junho de 2022, junho de "
                              "2023 e junho de 2024).")
    assert pedir("os últimos 6 junhos", painel_familia="tendencia")["painel"] == painel(janela=anuais)  # sempre 4
    # Um período sem ritmo não escolhe a janela: a pergunta do ritmo, com os 4 períodos de cada um; nada muda no gráfico.
    anos = pedir("tendência nos últimos 4 anos")
    assert "painel" not in anos
    assert anos["clarification"] == ("Na tendência, os períodos são sempre os últimos 4 do ritmo escolhido: anual, de junho de "
                                     "2021 a junho de 2024; semestral, de janeiro de 2023 a junho de 2024. Qual ritmo?" +
                                     conversa_grafico.NADA_MUDOU)
    assert [(escolha["label"], escolha["draft"]) for escolha in anos["choices"]] == [
        ("Anual", "tendência anual"), ("Semestral", "tendência semestral")]
    # Mesmo ambíguo (AT-34: as duas âncoras divergem), o período não decide nada na tendência: a pergunta é a do ritmo.
    assert pedir("tendência nos últimos 4 anos", conversation_today="2026-10-22")["choices"] == anos["choices"]
    assert [escolha["draft"] for escolha in pedir("tendência de 2015 a 2020 no Pará")["choices"]] == [
        "tendência anual no Pará", "tendência semestral no Pará"]
    assert [escolha["draft"] for escolha in pedir("tendência em todas as competências")["choices"]] == [
        "tendência anual", "tendência semestral"]
    # A mudança da tendência é entre o primeiro e o último dos 4 períodos: a mudança entre duas datas também pergunta o ritmo.
    mudanca = pedir("mostre a mudança entre junho de 2023 e junho de 2024")
    assert "painel" not in mudanca
    assert [escolha["draft"] for escolha in mudanca["choices"]] == ["mostre a mudança anual", "mostre a mudança semestral"]
    escolhida = pedir("mostre a mudança anual")
    assert escolhida["painel"] == painel(familia="tendencia", visao_tendencia="mudanca", janela=anuais)
    assert escolhida["reply"] == ("Abri a tendência da densidade, com os últimos 4 períodos anuais (junho de 2021, junho de 2022, "
                                  "junho de 2023 e junho de 2024). Visão da tendência: Trajetória.")
    # As visões com os nomes da tela (24/10/2026): "trajetória" abre a antiga Mudança, e "série temporal", a série histórica.
    trajetoria = pedir("mostre a trajetória anual")
    assert trajetoria["painel"] == escolhida["painel"] and trajetoria["reply"] == escolhida["reply"]
    serie_temporal = pedir("mostre a série temporal")
    assert serie_temporal["painel"] == painel(familia="tendencia", visao_tendencia="series")
    assert serie_temporal["reply"] == "Abri a tendência da densidade. Visão da tendência: Série temporal."
    assert pedir("quero ver as séries históricas")["painel"]["visao_tendencia"] == "series"
    # A janela da tela, em Python, é a mesma do modelo da tela: anos sozinhos só no anual; sem 4 períodos, nenhuma.
    assert conversa_grafico.janela_do_ritmo("anual", ["2019", "2020", "2021", "2022", "2023"]) == ["2020", "2021", "2022", "2023"]
    assert conversa_grafico.janela_do_ritmo("semestral", ["202106", "202206", "202306", "202406"]) == []
    assert conversa_grafico.janela_do_ritmo("anual", ["202006", "202106", "202306", "202406"]) == []  # sem 2022


def test_periodo_nos_pedidos_de_funcao_segue_o_ritmo_da_tendencia():
    """Condições, ordenação, comparar e juntar (24/10/2026): a janela é da tendência, que não tem janela longa. O ritmo citado
    dá os últimos 4 períodos dele, e a resposta diz quais; outro período com várias competências vira a pergunta do ritmo
    (nada muda no gráfico), com botões que reescrevem o pedido. Na referência da análise espacial, que usa uma competência por
    vez, a janela vira a pergunta da competência. Antes, o período citado ia como veio (as 8 competências de 2021 a 2024)."""
    anuais, semestrais = ["202106", "202206", "202306", "202406"], ["202301", "202306", "202401", "202406"]
    condicao = pedir("municípios com menos de 1 médico por mil, semestral")
    assert condicao["painel"] == painel(funcao="condicoes", condicoes=[{"atributo": "densidade", "operador": "<", "valor": 1}],
                                        janela=semestrais)
    assert condicao["reply"] == ("Apliquei a condição densidade < 1 por mil habitantes, com os últimos 4 períodos semestrais "
                                 "(janeiro de 2023, junho de 2023, janeiro de 2024 e junho de 2024): o gráfico separa quem "
                                 "atende a ela, quem não atende e quem não tem dado.")
    faixa = pedir("municípios com menos de 1 médico por mil de 2021 a 2024")
    assert "painel" not in faixa and faixa["clarification"].startswith("Na tendência, os períodos são sempre os últimos 4 do "
                                                                       "ritmo escolhido: anual, de junho de 2021")
    assert [(escolha["label"], escolha["draft"]) for escolha in faixa["choices"]] == [
        ("Anual", "municípios com menos de 1 médico por mil anual"),
        ("Semestral", "municípios com menos de 1 médico por mil semestral")]
    assert pedir(faixa["choices"][0]["draft"])["painel"]["janela"] == anuais
    ordena = pedir("os 5 municípios com maior densidade de 2021 a 2024")
    assert "painel" not in ordena
    assert [escolha["draft"] for escolha in ordena["choices"]] == [
        "os 5 municípios com maior densidade anual", "os 5 municípios com maior densidade semestral"]
    anual = pedir(ordena["choices"][0]["draft"])
    assert anual["painel"] == painel(funcao="ordenar", ordenar={"atributo": "densidade", "ordem": "desc", "primeiros": 5},
                                     janela=anuais)
    assert anual["reply"] == ("Ordenei os municípios pela densidade, do maior para o menor, e destaquei os 5 primeiros; "
                              "empates na posição de corte também entram, com os últimos 4 períodos anuais (junho de 2021, "
                              "junho de 2022, junho de 2023 e junho de 2024).")
    compara = pedir("compare Manaus e Tefé ano a ano")
    assert compara["painel"] == painel(funcao="comparar", selecao=["code:130260", "code:130420"], janela=anuais)
    assert compara["reply"] == ("Abri a comparação lado a lado de MANAUS (AM) e TEFE (AM), com os últimos 4 períodos anuais "
                                "(junho de 2021, junho de 2022, junho de 2023 e junho de 2024), com o maior, o menor e a "
                                "diferença.")
    # "em todas as competências" sai com a preposição: o botão pede o ritmo no lugar dele.
    junta = pedir("junte Manaus e Tefé em todas as competências")
    assert "painel" not in junta
    assert [escolha["draft"] for escolha in junta["choices"]] == ["junte Manaus e Tefé anual", "junte Manaus e Tefé semestral"]
    # A análise espacial usa uma competência por vez: a janela citada na referência vira a pergunta da competência.
    assert pedir("use Belém como referência de 2021 a 2024") == {"handled": True, "executed": False, "clarification": (
        "A análise espacial usa uma competência por vez, e a tendência usa os últimos 4 períodos, anuais ou semestrais. Diga "
        "uma competência, por exemplo, “em junho de 2024”, ou peça a tendência anual ou semestral." + conversa_grafico.NADA_MUDOU)}
    # A variação é da tendência: o exemplo da pergunta pede a Trajetória pelo ritmo, sem janela longa.
    assert pedir("ordene pela variação do maior para o menor") == {"handled": True, "executed": False, "clarification": (
        "A variação aparece na tendência, na visão Trajetória. Peça antes, por exemplo, “mostre a mudança anual”." +
        conversa_grafico.NADA_MUDOU)}
    # Fora da tendência, "últimos N anos" com as âncoras divergentes continua na AMB-04 (AT-34), com os anos em botões (a
    # cobertura que estava no teste antigo da janela da tendência).
    relativo = pedir("mostre a densidade nos últimos 4 anos", conversation_today="2026-10-22")
    assert "painel" not in relativo and relativo["ambiguity"] == "AMB-04"
    assert relativo["clarification"].startswith("“Últimos 4 anos” pode ser contado de duas formas")
    assert [escolha["draft"] for escolha in relativo["choices"]] == ["mostre a densidade de 2021 a 2024",
                                                                     "mostre a densidade de 2023 a 2024"]


def test_volte_aos_estados():
    assert pedir("volte aos estados") == {"handled": True, "executed": False, "painel": painel(nivel="estados"),
                                          "reply": "Voltei aos estados: cada bolha é um estado, com a densidade."}
    assert pedir("Pode voltar para os estados, por favor?")["painel"] == painel(nivel="estados")


def test_o_pedido_seguinte_usa_o_estado_do_grafico():
    # Um ano com duas competências: o gráfico mostra uma por vez, e a escolha fica com a pessoa.
    ano = pedir("e em 2023?")
    assert "painel" not in ano and ano["clarification"].startswith("Em 2023, a base tem 2 competências")
    assert [(escolha["label"], escolha["draft"]) for escolha in ano["choices"]] == [
        ("Junho de 2023", "e em junho de 2023?"), ("Janeiro de 2023", "e em janeiro de 2023?")]
    assert pedir("e em junho de 2023?") == {"handled": True, "executed": False, "painel": painel(competencia="202306"),
                                            "reply": "Mudei a competência para junho de 2023."}
    assert pedir("mostre a quantidade") == {"handled": True, "executed": False, "painel": painel(indicador="quantidade"),
                                            "reply": "Troquei o indicador para a quantidade."}
    acrescenta = pedir("acrescente Belém")
    assert acrescenta["painel"] == painel(nivel="municipios", municipios={"todos": False, "estados": ["13"],
                                                                          "ids": ["code:150140"]})
    assert acrescenta["reply"] == "Acrescentei BELEM (PA) ao gráfico; agora são 6 municípios."
    tira = pedir("tire Tefé")
    assert tira["painel"]["municipios"] == {"todos": False, "estados": [],
                                            "ids": ["code:130185", "code:130250", "code:130260", "code:130340"]}
    assert tira["reply"] == "Tirei TEFE (AM) do gráfico; ficaram 4 municípios."
    # "Esses" são os municípios do gráfico; a comparação mostra no máximo 3.
    assert "o pedido tem 5" in pedir("compare esses municípios")["clarification"]
    # O homônimo que já está no gráfico vale; a resposta diz qual.
    assert pedir("mostre Santarém", painel_municipios={"todos": False, "estados": ["15"], "ids": []})["painel"][
        "municipios"] == {"todos": False, "estados": [], "ids": ["code:150680"]}


def test_ambiguidades_viram_alternativas_em_botoes_sem_mudar_o_grafico():
    sp = pedir("mostre São Paulo")
    assert "painel" not in sp and sp["ambiguity"] == "AMBIGUIDADE_MATERIAL"
    assert sp["clarification"] == ("“São Paulo” identifica um estado e também um município. Qual você quer? Nada mudou no "
                                   "gráfico.")
    assert [(escolha["label"], escolha["draft"], escolha["send"]) for escolha in sp["choices"]] == [
        ("Estado de São Paulo", "mostre o estado de São Paulo", True), ("SAO PAULO (SP)", "mostre SAO PAULO (SP)", True)]
    assert pedir(sp["choices"][0]["draft"])["painel"]["municipios"] == {"todos": False, "estados": ["35"], "ids": []}
    assert pedir(sp["choices"][1]["draft"])["painel"]["municipios"] == {"todos": False, "estados": [],
                                                                        "ids": ["code:355030"]}
    homonimos = pedir("mostre Santarém")
    assert homonimos["clarification"] == "Há 2 municípios com o nome “Santarém”. Qual deles? Nada mudou no gráfico."
    assert [escolha["draft"] for escolha in homonimos["choices"]] == ["mostre SANTAREM (PA)", "mostre SANTAREM (PB)"]
    assert pedir("mostre SANTAREM (PB)")["painel"]["municipios"]["ids"] == ["code:251365"]
    parana = pedir("mostre o Paraná")
    assert [(escolha["label"], escolha["draft"]) for escolha in parana["choices"]] == [
        ("Estado do Paraná", "mostre o estado do Paraná"), ("PARANA (RN)", "mostre o PARANA (RN)")]
    assert pedir("mostre o estado do Paraná")["painel"]["municipios"]["estados"] == ["41"]
    assert "uma análise por vez" in pedir("mostre a distribuição e a tendência")["clarification"]
    assert "um indicador por vez" in pedir("mostre a densidade e a quantidade")["clarification"]


def test_rotatividade_exportar_e_pedidos_que_seguem_para_o_interprete():
    rotatividade = pedir("mostre a rotatividade")
    assert "painel" not in rotatividade and "a base do Brasil não tem esse identificador" in rotatividade["reply"]
    assert pedir("exporte em CSV") == {"handled": True, "executed": False, "painel": painel(funcao="exportar"),
                                       "reply": "Abri Exportar: CSV com precisão integral, Imprimir/PDF e o método com os "
                                                "parâmetros."}
    # Sem comando do gráfico, o pedido segue para o intérprete com o provedor, como antes.
    for mensagem in ("qual a capital do Amazonas?", "o que significa densidade?", "ok"):
        assert pedir(mensagem) == {"handled": False}, mensagem


# ----------------------------------------------------------------------------------- vista do desenho (23/10/2026)
def test_no_mapa_e_onde_ficam_acompanham_o_comando_com_a_vista_do_mapa():
    """"No mapa" e "onde ficam …?" junto com outro pedido: o comando leva `vista: "mapa"`, estado visual que a área aplica
    sem recalcular (RQ-REP-06), e a resposta diz que a vista mudou. Sozinho ("ver no mapa"), o pedido é atendido na tela."""
    para = pedir("mostre o Pará no mapa")
    assert para == {"handled": True, "executed": False,
                    "painel": painel(nivel="municipios", municipios={"todos": False, "estados": ["15"], "ids": []},
                                     vista="mapa"),
                    "reply": "Mostrei a densidade nos 2 municípios do Pará. Passei para o mapa."}
    onde = pedir("onde ficam os municípios com menos de 1 médico por mil?")
    assert onde["painel"] == painel(funcao="condicoes", condicoes=[{"atributo": "densidade", "operador": "<", "valor": 1}],
                                    vista="mapa")
    assert onde["reply"] == ("Apliquei a condição densidade < 1 por mil habitantes: o gráfico separa quem atende a ela, quem "
                             "não atende e quem não tem dado. Passei para o mapa.")
    # Dos estados, "o Pará no mapa" abre os municípios, que têm ponto: a vista muda.
    assert pedir("mostre o Pará no mapa", painel_nivel="estados", painel_mapa_disponivel=False)["painel"]["vista"] == "mapa"
    # Já no mapa, ele continua; "no gráfico" volta ao gráfico.
    no_mapa = pedir("mostre a quantidade no mapa", painel_vista="mapa")
    assert no_mapa["painel"] == painel(indicador="quantidade", vista="mapa")
    assert no_mapa["reply"] == "Troquei o indicador para a quantidade. O mapa continua na tela."
    grafico = pedir("mostre a quantidade no gráfico", painel_vista="mapa")
    assert grafico["painel"] == painel(indicador="quantidade", vista="grafico")
    assert grafico["reply"] == "Troquei o indicador para a quantidade. Voltei ao gráfico."
    assert pedir("mostre a quantidade no gráfico")["reply"] == "Troquei o indicador para a quantidade."
    # Sem a vista no pedido, ou com ela negada, a vista não muda; "Amapá" não é o mapa.
    assert pedir("mostre o Pará")["painel"]["vista"] is None
    negada = pedir("mostre o Pará, não no mapa")
    assert negada["painel"]["vista"] is None and negada["reply"] == "Mostrei a densidade nos 2 municípios do Pará."
    assert pedir("mostre o Amapá")["clarification"].startswith("Não encontrei “Amapá”")
    # Sozinha, a vista não é comando do gráfico aqui: a tela já a atendeu, e o resto segue para a interpretação.
    assert pedir("quero ver isso no mapa agora mesmo") == {"handled": False}


def test_onde_o_mapa_nao_mostra_a_analise_a_vista_fica_no_grafico():
    """Os estados não têm um ponto; a visão Série temporal fica só no gráfico; a área já disse que o mapa não está disponível:
    o comando segue sem a vista, e a resposta diz por quê."""
    estados = pedir("volte aos estados no mapa")
    assert estados["painel"] == painel(nivel="estados")
    assert estados["reply"] == ("Voltei aos estados: cada bolha é um estado, com a densidade. Os estados não têm um ponto no "
                                "mapa; a análise fica no gráfico. Para ver no mapa, abra os municípios de um estado.")
    nos_estados = pedir("mostre a quantidade no mapa", painel_nivel="estados", painel_mapa_disponivel=False)
    assert nos_estados["painel"] == painel(indicador="quantidade")
    assert nos_estados["reply"].endswith("Os estados não têm um ponto no mapa; a análise fica no gráfico. Para ver no mapa, "
                                         "abra os municípios de um estado.")
    series = pedir("mostre a visão séries no mapa")
    assert series["painel"] == painel(familia="tendencia", visao_tendencia="series")
    assert series["reply"] == ("Abri a tendência da densidade. Visão da tendência: Série temporal. A visão Série temporal fica "
                               "só no gráfico.")
    indisponivel = pedir("mostre a quantidade no mapa", painel_mapa_disponivel=False)
    assert indisponivel["painel"] == painel(indicador="quantidade")
    assert indisponivel["reply"] == ("Troquei o indicador para a quantidade. O mapa não está disponível nesta análise; ela "
                                     "fica no gráfico.")


def test_vista_e_resumo_da_tela_ficam_so_na_conversa_local():
    """painel_vista, painel_mapa_disponivel e painel_resumo (a frase-resumo do motor, com valores da base) entram no
    contexto da conversa e saem das opções do intérprete; a frase não entra nem no contexto."""
    frase = "Nos 5 municípios do Amazonas, em junho de 2024, a densidade vai de 4,321 a 9,876 por 1.000 habitantes."
    opcoes = {**CONTEXTO, "painel_vista": "mapa", "painel_mapa_disponivel": True, "painel_resumo": frase}
    ctx = conversa_grafico.contexto(opcoes)
    assert (ctx["vista"], ctx["mapa_disponivel"]) == ("mapa", True)
    assert frase not in json.dumps(ctx, ensure_ascii=False)
    limpas = conversa_grafico.opcoes_do_interprete(opcoes, ctx)
    assert not {"painel_vista", "painel_mapa_disponivel", "painel_resumo"} & set(limpas)
    assert frase not in json.dumps(limpas, ensure_ascii=False)
    # Valores fora do contrato ficam de fora.
    estranho = conversa_grafico.contexto({**CONTEXTO, "painel_vista": "satelite", "painel_mapa_disponivel": "sim"})
    assert (estranho["vista"], estranho["mapa_disponivel"]) == (None, None)


# ----------------------------------------------------------------------------------- rotas
HEADER = ("regiao_geografica;uf;municipio;cod_ibge;latitude;longitude;categoria_profissional;periodo_ano;periodo_mes;"
          "quantidade;população_estimada")


@pytest.fixture
def base_do_brasil(tmp_path, monkeypatch):
    """Repositório temporário com o catálogo sintético como versão governada (como em test_painel.py)."""
    root = tmp_path / "repositorio"
    root.mkdir()
    book = Workbook()
    book.active.append(["pais", "periodo_ano", "periodo_mes", "categoria_profissional", "contagem"])
    for periodo in PERIODOS:
        book.active.append(["Brasil", int(periodo[:4]), int(periodo[4:]), "MEDICINA", 1000])
    book.save(root / FILES["national"])
    linhas = [HEADER] + [";".join(["NORTE", STATES[codigo[:2]][0], nome, codigo, "-3,1", "-60,0", "MEDICINA", periodo[:4],
                                   str(int(periodo[4:])), "10", "1000"])
                         for periodo in PERIODOS for codigo, nome in UNIDADES.items()]
    (root / FILES["municipal"]).write_text("\n".join(linhas) + "\n", encoding="utf-8")
    write_state_source(root, {(STATES[codigo[:2]][0], periodo): 100 for codigo in UNIDADES for periodo in PERIODOS})
    (root / GOVERNED_MANIFEST).parent.mkdir(parents=True, exist_ok=True)
    (root / GOVERNED_MANIFEST).write_text(json.dumps(manifest_from_repository(root)), encoding="utf-8")
    monkeypatch.setattr(brazil_data, "REPO_ROOT", root)
    monkeypatch.delenv("ADT_BRASIL_DATA_DIR", raising=False)
    monkeypatch.delenv("ADT_BRASIL_DATA_VERSION", raising=False)
    main._BRAZIL_FRAMES.clear()
    yield root
    main._BRAZIL_FRAMES.clear()


@pytest.fixture
def sem_provedor(monkeypatch):
    """O caminho local nunca chama o provedor de IA."""
    async def proibido(*_args, **_kwargs):
        raise AssertionError("A conversa no gráfico não deve chamar o provedor.")
    monkeypatch.setattr(llm_bridge, "_call_gemini", proibido)


def local(mensagem, opcoes=None, **dados):
    """Rota da conversa local; sem `opcoes`, o contexto do gráfico com os municípios do Amazonas."""
    mapa, arquivos = dados.pop("mapping", "{}"), dados.pop("files", None)
    resposta = client.post("/api/exploration/interpret", files=arquivos, data={
        "message": mensagem, "mapping": mapa, "options": json.dumps(CONTEXTO if opcoes is None else opcoes), **dados})
    assert resposta.status_code == 200, resposta.text
    return resposta.json()


def test_rota_local_com_a_base_do_brasil(base_do_brasil, sem_provedor):
    body = local("Mostre o Pará", dataset="brazil")
    assert body["painel"] == painel(nivel="municipios", municipios={"todos": False, "estados": ["15"], "ids": []})
    assert body["reply"] == "Mostrei a densidade nos 2 municípios do Pará." and body["executed"] is False
    assert local("compare Manaus e Tefé", dataset="brazil")["painel"] == painel(
        funcao="comparar", selecao=["code:130260", "code:130420"])
    assert local("volte aos estados", dataset="brazil")["painel"] == painel(nivel="estados")
    # O exemplo da orientação da base sem seleção (23/10/2026): "todos os estados" põe os estados no gráfico.
    assert local("todos os estados", dataset="brazil")["painel"] == painel(nivel="estados")
    # Ordenação perguntada ("qual ... maior densidade") é comando do gráfico, não explicação de resultado.
    assert local("qual município tem a maior densidade?", dataset="brazil")["painel"]["ordenar"] == {
        "atributo": "densidade", "ordem": "desc", "primeiros": 1}
    # A vista citada vai no comando também pela rota (estado visual: a área não recalcula por ela).
    mapa = local("mostre o Pará no mapa", dataset="brazil")
    assert mapa["painel"] == painel(nivel="municipios", municipios={"todos": False, "estados": ["15"], "ids": []},
                                    vista="mapa")
    assert mapa["reply"] == "Mostrei a densidade nos 2 municípios do Pará. Passei para o mapa."


DISTRITOS = {"Nampula": "Nampula", "Angoche": "Nampula", "Mogovolas": "Nampula", "Quelimane": "Zambézia",
             "Mocuba": "Zambézia"}
PLANILHA = ("\n".join(["distrito;provincia;periodo;categoria;quantidade;populacao"] + [
    distrito + ";" + provincia + ";" + periodo + ";Enfermagem;5;1000" for periodo in ("2023", "2024")
    for distrito, provincia in DISTRITOS.items()]) + "\n").encode()
MAPA = {"territory": "distrito", "grupo_territorial": "provincia", "period": "periodo", "category": "categoria",
        "count": "quantidade", "population": "populacao"}
ROTULOS = {"unidade": {"singular": "distrito", "plural": "distritos"},
           "grupo": {"singular": "província", "plural": "províncias"}}
CONTEXTO_PLANILHA = {"painel_familia": "distribuicao", "painel_indicador": "densidade", "rotulos": ROTULOS}


def planilha(mensagem, opcoes=None, mapa=MAPA, **extra):
    return local(mensagem, CONTEXTO_PLANILHA if opcoes is None else opcoes, mapping=json.dumps(mapa),
                 files={"file": ("distritos.csv", PLANILHA)}, **extra)


def test_planilha_de_distritos_e_provincias_usa_os_rotulos_e_o_grupo(sem_provedor):
    body = planilha("mostre a província de Zambézia")
    assert body["painel"] == painel(nivel="municipios", municipios={"todos": False, "estados": ["Zambézia"], "ids": []})
    assert body["reply"] == "Mostrei a densidade nos 2 distritos da província Zambézia."
    duvida = planilha("mostre Nampula")
    assert duvida["clarification"] == ("“Nampula” identifica uma província e também um distrito. Qual você quer? Nada mudou "
                                       "no gráfico.")
    assert [(escolha["label"], escolha["draft"]) for escolha in duvida["choices"]] == [
        ("Província Nampula", "mostre a província Nampula"), ("Distrito Nampula", "mostre o distrito Nampula")]
    distrito = planilha("mostre o distrito Nampula")
    assert distrito["painel"]["municipios"] == {"todos": False, "estados": [], "ids": ["name:Nampula"]}
    assert distrito["reply"] == "Mostrei a densidade em 1 distrito: Nampula."
    assert planilha("compare Angoche e Mocuba")["painel"] == painel(funcao="comparar",
                                                                    selecao=["name:Angoche", "name:Mocuba"])
    junte = planilha("junte os distritos da província Nampula")
    assert junte["painel"] == painel(funcao="juntar", selecao=["name:Nampula", "name:Angoche", "name:Mogovolas"])
    assert junte["reply"].endswith("(quem atua em mais de um distrito conta em cada um).")
    todos = planilha("mostre todos os distritos")
    assert todos["painel"]["municipios"] == {"todos": True, "estados": [], "ids": []}
    assert todos["reply"] == "Mostrei a densidade em todos os 5 distritos."
    assert planilha("qual distrito tem a maior densidade?")["reply"].startswith("Ordenei os distritos pela densidade")
    assert planilha("volte aos estados")["clarification"].startswith("Esta base não tem um nível acima dos distritos")
    # Sem latitude e longitude na planilha, não há mapa: o comando segue sem a vista, e a resposta diz por quê.
    sem_mapa = planilha("mostre a província de Zambézia no mapa")
    assert sem_mapa["painel"] == painel(nivel="municipios", municipios={"todos": False, "estados": ["Zambézia"], "ids": []})
    assert sem_mapa["reply"] == ("Mostrei a densidade nos 2 distritos da província Zambézia. Sem latitude e longitude na "
                                 "planilha, não há mapa; a análise fica no gráfico.")


def test_orientacoes_da_conversa_seguem_os_rotulos_da_planilha():
    """Numa planilha, as orientações da conversa (referência, distância, condições) usam os nomes da estrutura reconhecida,
    sem "município" nem exemplos da base do Brasil; na base do Brasil, o texto de sempre (23/10/2026)."""
    from types import SimpleNamespace
    planilha_ = SimpleNamespace(brasil=False, rot=conversa_grafico._Rotulos("distrito", "distritos", False, "província",
                                                                            "províncias", True))
    brasil = SimpleNamespace(brasil=True, rot=conversa_grafico._Rotulos("município", "municípios", False, "estado", "estados",
                                                                        False))
    assert conversa_grafico._sem_ponto_unico(brasil) == conversa_grafico.SEM_PONTO_UNICO
    assert conversa_grafico._sem_ponto_unico(brasil, base_inteira=True) == (
        "A referência é um município ou um conjunto de municípios: a referência não pode ser a base inteira. Diga os "
        "municípios, por exemplo, “use Manaus como referência”." + conversa_grafico.NADA_MUDOU)
    assert conversa_grafico._sem_ponto_unico(planilha_) == (
        "A referência é um distrito ou um conjunto de distritos: as províncias não têm um ponto único. Diga os distritos pelo "
        "nome, por exemplo, “use … como referência”." + conversa_grafico.NADA_MUDOU)
    assert conversa_grafico._sem_ponto_unico(planilha_, base_inteira=True) == (
        "A referência é um distrito ou um conjunto de distritos: a referência não pode ser a base inteira. Diga os distritos "
        "pelo nome, por exemplo, “use … como referência”." + conversa_grafico.NADA_MUDOU)
    assert (conversa_grafico._nome_de_exemplo(brasil), conversa_grafico._nome_de_exemplo(planilha_)) == ("Manaus", "…")
    # Nenhuma orientação da planilha cita município, estado ou Manaus.
    for texto in (conversa_grafico._sem_ponto_unico(planilha_), conversa_grafico._sem_ponto_unico(planilha_, True)):
        assert not any(palavra in texto for palavra in ("munic", "estado", "Manaus")), texto


def test_contexto_completo_com_sessao_nao_quebra_o_pre_exame(sem_provedor):
    """Competência e janela juntas, estados em territory_ids e o papel grupo_territorial: o pré-exame da sessão recebe só
    as opções do intérprete."""
    sessao = {"X-ADT-Session": client.post("/api/session").json()["token"]}
    opcoes = {**CONTEXTO_PLANILHA, "period_filter": "2024", "period_filters": ["2023", "2024"],
              "territory_ids": ["name:Angoche", "name:Mocuba", "uf:13"]}
    resposta = client.post("/api/exploration/interpret", headers=sessao, files={"file": ("distritos.csv", PLANILHA)},
                           data={"message": "mostre a quantidade", "mapping": json.dumps(MAPA),
                                 "options": json.dumps(opcoes)})
    assert resposta.status_code == 200, resposta.text
    assert resposta.json()["painel"] == painel(indicador="quantidade")


def test_fora_da_pagina_unica_o_caminho_anterior_continua_com_o_painel():
    mapa = {papel: coluna for papel, coluna in MAPA.items() if papel != "grupo_territorial"}
    body = planilha("Compare Angoche e Mocuba", opcoes={}, mapa=mapa)
    assert body["operation"] == "comparisons" and body["territory_ids"] == ["name:Angoche", "name:Mocuba"]
    assert body["reply"].startswith("Recorte identificado com 2 territórios.")
    assert body["painel"] == painel(funcao="comparar", selecao=["name:Angoche", "name:Mocuba"], indicador="densidade")


def test_rota_com_o_provedor_devolve_o_painel_sem_enviar_dados_da_base(monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "test-only-not-real")
    monkeypatch.setattr(llm_bridge, "_counter", 0)
    monkeypatch.setattr(llm_bridge, "_counter_day", "")
    enviado = []

    async def provedor(mensagens, *_args):
        enviado.extend(mensagens)
        return {"operation": "comparisons", "indicator": "density", "period": "", "category": "", "territory": "",
                "intent": "ANALITICO", "topic": "none"}

    monkeypatch.setattr(llm_bridge, "_call_gemini", provedor)
    opcoes = {**CONTEXTO_PLANILHA, "territory_ids": ["name:Nampula"],
              "painel_municipios": {"todos": False, "estados": ["Nampula"], "ids": []}}
    resposta = client.post("/api/llm/interpret-context", files={"file": ("distritos.csv", PLANILHA)}, data={
        "message": "Coloque Angoche e Mocuba lado a lado", "history": "[]", "mapping": json.dumps(MAPA),
        "options": json.dumps(opcoes)})
    assert resposta.status_code == 200, resposta.text
    body = resposta.json()
    assert body["painel"] == painel(funcao="comparar", selecao=["name:Angoche", "name:Mocuba"], indicador="densidade",
                                    nivel="municipios", municipios={"todos": False, "estados": ["Nampula"],
                                                                    "ids": ["name:Mocuba"]})
    assert body["reply"].startswith("Abri a comparação lado a lado de Angoche e Mocuba")
    assert "exploration" not in body and body["executed"] is False
    assert body["verification"]["source"] == "BACKEND_PREFLIGHT"
    conteudo = " ".join(enviado)
    assert enviado and "CONTEXTO_VERIFICADO_PELO_BACKEND" in conteudo
    for proibido in ("Angoche", "Mocuba", "Nampula", "Zambézia", "name:", "painel", "distritos.csv"):
        assert proibido not in conteudo, proibido


def test_vista_e_resumo_nunca_chegam_ao_interprete_nem_ao_provedor(monkeypatch):
    """Nas duas rotas, a vista em exibição, a disponibilidade do mapa e a frase-resumo do motor (com valores da base) saem
    das opções antes do pré-exame e do intérprete, e nada delas chega ao provedor de IA."""
    monkeypatch.setenv("GEMINI_API_KEY", "test-only-not-real")
    monkeypatch.setattr(llm_bridge, "_counter", 0)
    monkeypatch.setattr(llm_bridge, "_counter_day", "")
    enviado, recebidas = [], []

    async def provedor(mensagens, *_args):
        enviado.extend(mensagens)
        return {"operation": "comparisons", "indicator": "density", "period": "", "category": "", "territory": "",
                "intent": "ANALITICO", "topic": "none"}

    pre_exame, interpretar = main.preflight, conversa_grafico.interpretar

    def pre_exame_registrado(frame, fields, settings):
        recebidas.append(dict(settings))
        return pre_exame(frame, fields, settings)

    def interpretar_registrado(mensagem, frame, fields, settings, ctx, **extra):
        recebidas.extend([dict(settings), dict(extra.get("opcoes") or {})])
        return interpretar(mensagem, frame, fields, settings, ctx, **extra)

    monkeypatch.setattr(llm_bridge, "_call_gemini", provedor)
    monkeypatch.setattr(main, "preflight", pre_exame_registrado)
    monkeypatch.setattr(conversa_grafico, "interpretar", interpretar_registrado)
    frase = "Nos 5 distritos, em 2024, a densidade vai de 4,321 a 9,876 por 1.000 habitantes."
    opcoes = {**CONTEXTO_PLANILHA, "painel_vista": "mapa", "painel_mapa_disponivel": True, "painel_resumo": frase}
    caminho_local = planilha("mostre a quantidade no mapa", opcoes)
    assert caminho_local["painel"] == painel(indicador="quantidade")
    assert caminho_local["reply"] == ("Troquei o indicador para a quantidade. Sem latitude e longitude na planilha, não há "
                                      "mapa; a análise fica no gráfico.")
    resposta = client.post("/api/llm/interpret-context", files={"file": ("distritos.csv", PLANILHA)}, data={
        "message": "Coloque Angoche e Mocuba lado a lado", "history": "[]", "mapping": json.dumps(MAPA),
        "options": json.dumps(opcoes)})
    assert resposta.status_code == 200, resposta.text
    assert resposta.json()["painel"]["funcao"] == "comparar"
    assert enviado and len(recebidas) >= 4, recebidas
    for registro in recebidas:
        assert not {"painel_vista", "painel_mapa_disponivel", "painel_resumo"} & set(registro), sorted(registro)
        assert frase not in json.dumps(registro, ensure_ascii=False, default=str)
    conteudo = " ".join(enviado)
    for proibido in (frase, "4,321", "9,876", "painel_resumo", "painel_vista", "painel_mapa_disponivel"):
        assert proibido not in conteudo, proibido


def test_rota_sem_base_devolve_o_painel_da_operacao_proposta(monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "test-only-not-real")
    monkeypatch.setattr(llm_bridge, "_counter", 0)
    monkeypatch.setattr(llm_bridge, "_counter_day", "")

    async def provedor(*_args):
        return {"operation": "ranking", "indicator": "density", "period": "", "category": "", "territory": "",
                "intent": "ANALITICO", "topic": "none"}

    monkeypatch.setattr(llm_bridge, "_call_gemini", provedor)
    resposta = client.post("/api/llm/interpret", json={"message": "quais lugares estão mais bem servidos?"})
    assert resposta.status_code == 200, resposta.text
    assert resposta.json()["painel"] == painel(funcao="ordenar", indicador="densidade")
    assert "painel" not in client.post("/api/llm/interpret", json={"message": "Olá"}).json()


# ----------------------------------------------------------------------------------- base versionada (somente leitura)
@pytest.fixture(scope="module")
def real(tmp_path_factory):
    """Base versionada instalada numa pasta temporária (job dados-reais), somente em leitura."""
    pasta = os.getenv("ADT_REAL_DATA_DIR")
    if not pasta:
        pytest.skip("Defina ADT_REAL_DATA_DIR para testar as bases locais somente em leitura")
    arquivos = [p for p in Path(pasta).iterdir() if p.suffix.lower() in (".csv", ".xlsx")]
    antes = {p: hashlib.sha256(p.read_bytes()).hexdigest() for p in arquivos}
    catalogo = tmp_path_factory.mktemp("conversa-real") / "brasil"
    install(Path(pasta), catalogo)
    with pytest.MonkeyPatch.context() as patch:
        patch.setenv("ADT_BRASIL_DATA_DIR", str(catalogo))
        patch.delenv("ADT_BRASIL_DATA_VERSION", raising=False)
        main._BRAZIL_FRAMES.clear()
        yield
        main._BRAZIL_FRAMES.clear()
    assert antes == {p: hashlib.sha256(p.read_bytes()).hexdigest() for p in arquivos}


def test_frases_do_contrato_com_a_base_versionada(real, sem_provedor):
    para = local("Mostre o Pará", dataset="brazil")
    assert para["reply"] == "Mostrei a densidade nos 144 municípios do Pará."
    assert para["painel"]["municipios"] == {"todos": False, "estados": ["15"], "ids": []}
    # Há três municípios chamados Belém (PA, PB e AL): com o Pará no gráfico vale o do Pará; sem ele, a pergunta.
    no_para = {**CONTEXTO, "painel_municipios": {"todos": False, "estados": ["15"], "ids": []}, "territory_ids": []}
    assert local("use Belém como referência", no_para, dataset="brazil")["painel"]["referencia"] == {
        "membros": ["code:150140"]}
    belem = local("use Belém como referência", dataset="brazil")
    assert [escolha["label"] for escolha in belem["choices"]] == ["BELEM (AL)", "BELEM (PA)", "BELEM (PB)"]
    assert local("junte Manaus, Iranduba e Manacapuru", dataset="brazil")["painel"]["selecao"] == [
        "code:130260", "code:130185", "code:130250"]
    assert local("compare Manaus e Tefé", dataset="brazil")["painel"]["selecao"] == ["code:130260", "code:130420"]
    condicoes = local("municípios com menos de 1 médico por mil e a mais de 150 km de Manaus", dataset="brazil")
    assert condicoes["painel"]["referencia"] == {"membros": ["code:130260"]}
    assert len(condicoes["painel"]["condicoes"]) == 2
    # O Paraná é estado e nome de dois municípios (TO e RN).
    assert [escolha["label"] for escolha in local("mostre o Paraná", dataset="brazil")["choices"]] == [
        "Estado do Paraná", "PARANA (RN)", "PARANA (TO)"]
