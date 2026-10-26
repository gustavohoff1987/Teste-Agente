"""Gestor de diálogo da página única (dialogo.py) e explicação verificada do resultado (explicacao.py), 26/10/2026.

Catálogo sintético instalado como versão governada (como em test_painel_pagina.py), com valores fictícios em cinco
competências (junho de 2021 a 2023, janeiro e junho de 2024):
- AMAZONAS é estado (AM) e também um município fictício do Pará: ambiguidade estado × município;
- BELEM existe no Pará e na Paraíba: homônimos;
- 2024 tem duas competências: ambiguidade de período;
- nos últimos 4 junhos, MANAUS fica em Aceleração do crescimento, PARINTINS em Desaceleração de declínio e TEFE em
  Crescimento.
A conversa roda pelo simulador da tela (conversa_simulada.py): o mesmo caminho da página única, sem o provedor de IA,
salvo onde o provedor é simulado. Nada é calculado pela conversa; os números conferidos são os do motor.
"""
import hashlib
import json
import re

import pytest
from fastapi.testclient import TestClient
from openpyxl import Workbook

import brazil_data
import dialogo
import explicacao
import llm_bridge
import main
import redacao
from brazil_data import FILES, GOVERNED_MANIFEST, manifest_from_repository
from catalog_support import write_state_source
from conversa_simulada import Tela, dobra
from document_catalog import materialize
from resumo_painel import number

client = TestClient(main.app)
PERIODS = ["202106", "202206", "202306", "202401", "202406"]
JUNES = ["202106", "202206", "202306", "202406"]
HEADER = ("regiao_geografica;uf;municipio;cod_ibge;latitude;longitude;categoria_profissional;periodo_ano;periodo_mes;"
          "quantidade;população_estimada")
UNITS = {
    "130260": ("MANAUS", "AM", ("-3", "-60"), [30, 34, 40, 41, 47], 2000),
    "130420": ("TEFE", "AM", ("-3,5", "-64,7"), [5, 5, 6, 6, 6], 600),
    "130340": ("PARINTINS", "AM", ("-3", "-61"), [20, 16, 14, 13, 12], 1000),
    "150990": ("AMAZONAS", "PA", ("-2", "-55"), [8, 8, 9, 9, 10], 1000),
    "150140": ("BELEM", "PA", ("-1,4", "-48,5"), [50, 52, 54, 55, 56], 3000),
    "250190": ("BELEM", "PB", ("-6,7", "-35,5"), [2, 2, 3, 3, 3], 400),
}
MANAUS, TEFE, PARINTINS, AMAZONAS_PA, BELEM_PA, BELEM_PB = ("code:" + code for code in UNITS)


@pytest.fixture
def repo(tmp_path, monkeypatch):
    root = tmp_path / "repositorio"
    root.mkdir()
    book = Workbook()
    book.active.append(["pais", "periodo_ano", "periodo_mes", "categoria_profissional", "contagem"])
    for period in PERIODS:
        book.active.append(["Brasil", int(period[:4]), int(period[4:]), "MEDICINA", 1000])
    book.save(root / FILES["national"])
    lines = [HEADER]
    for i, period in enumerate(PERIODS):
        for code, (name, uf, (lat, lon), counts, population) in UNITS.items():
            lines.append(";".join(["NORTE", uf, name, code, lat, lon, "MEDICINA", period[:4], str(int(period[4:])),
                                   str(counts[i]), str(population)]))
    (root / FILES["municipal"]).write_text("\n".join(lines) + "\n", encoding="utf-8")
    write_state_source(root, {(uf, period): count for period in PERIODS for uf, count in (("AM", 90), ("PA", 60),
                                                                                          ("PB", 3))})
    (root / GOVERNED_MANIFEST).parent.mkdir(parents=True, exist_ok=True)
    (root / GOVERNED_MANIFEST).write_text(json.dumps(manifest_from_repository(root)), encoding="utf-8")
    monkeypatch.setattr(brazil_data, "REPO_ROOT", root)
    monkeypatch.delenv("ADT_BRASIL_DATA_DIR", raising=False)
    monkeypatch.delenv("ADT_BRASIL_DATA_VERSION", raising=False)
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    monkeypatch.delenv("ADT_DIALOGO", raising=False)
    main._BRAZIL_FRAMES.clear()
    originals = {name: hashlib.sha256((root / name).read_bytes()).hexdigest() for name in FILES.values()}
    yield root
    assert originals == {name: hashlib.sha256((root / name).read_bytes()).hexdigest() for name in FILES.values()}
    main._BRAZIL_FRAMES.clear()


@pytest.fixture
def tela(repo):
    info = client.post("/api/inspect", data={"dataset": "brazil", "scope": "municipal"}).json()
    return Tela(client, info)


@pytest.fixture
def sem_provedor(monkeypatch):
    """Nada destes testes pode chegar ao provedor de IA."""
    async def proibido(*_args, **_kwargs):
        raise AssertionError("o provedor de IA não pode ser chamado")
    monkeypatch.setattr(llm_bridge, "_call_gemini", proibido)
    monkeypatch.setattr(llm_bridge, "generate_structured", proibido)


def numeros(texto):
    return re.findall(r"(?<![\w,.-])-?\d+(?:\.\d{3})*(?:,\d+)?(?!\w)", texto)


# --------------------------------------------------------------------------------------------- reconhecimento (sem dados)
PENDENTE = {"pergunta": "“Rio de Janeiro” identifica um estado e também um município. Qual você quer?",
            "pedido": "Compare Rio de Janeiro com Porto Alegre.",
            "alternativas": [{"rotulo": "Estado do Rio de Janeiro", "rascunho": "Compare o estado RJ Rio de Janeiro com Porto Alegre"},
                             {"rotulo": "RIO DE JANEIRO (RJ)", "rascunho": "Compare RIO DE JANEIRO (RJ) com Porto Alegre"}]}
HOMONIMOS = {"pergunta": "Há 3 municípios com o nome “Belém”. Qual deles?", "pedido": "Compare Belém e Manaus",
             "alternativas": [{"rotulo": "BELEM (AL)", "rascunho": "Compare BELEM (AL) e Manaus"},
                              {"rotulo": "BELEM (PA)", "rascunho": "Compare BELEM (PA) e Manaus"},
                              {"rotulo": "BELEM (PB)", "rascunho": "Compare BELEM (PB) e Manaus"}]}
PERIODO = {"pergunta": "Em 2024, a base tem 2 competências. Qual delas?", "pedido": "Compare Belém e Manaus em 2024",
           "alternativas": [{"rotulo": "Junho de 2024", "rascunho": "Compare Belém e Manaus em junho de 2024"},
                            {"rotulo": "Janeiro de 2024", "rascunho": "Compare Belém e Manaus em janeiro de 2024"}]}


@pytest.mark.parametrize("mensagem,pendente,indice", [
    ("Município.", PENDENTE, 1), ("a cidade", PENDENTE, 1), ("o estado", PENDENTE, 0), ("quero o estado mesmo", PENDENTE, 0),
    ("o município, não o estado", PENDENTE, 1), ("a capital", PENDENTE, 1),
    ("a do Pará", HOMONIMOS, 1), ("o da Paraíba", HOMONIMOS, 2), ("PB", HOMONIMOS, 2), ("o primeiro", HOMONIMOS, 0),
    ("a última opção", HOMONIMOS, 2), ("junho", PERIODO, 0), ("a de janeiro", PERIODO, 1), ("jan", PERIODO, 1),
])
def test_resposta_digitada_escolhe_a_alternativa_do_esclarecimento(mensagem, pendente, indice):
    ato = dialogo.reconhecer(mensagem, {"pendente": pendente}, False)
    assert ato == {"ato": "responde_pendente", "alternativa": indice}


def test_resposta_que_nao_escolhe_repergunta_e_pedido_novo_segue_adiante():
    assert dialogo.reconhecer("hmm, sei lá", {"pendente": PENDENTE}, False) == {"ato": "repergunta"}
    assert dialogo.reconhecer("deixa pra lá", {"pendente": PENDENTE}, False) == {"ato": "cancela_pendente"}
    # Um pedido novo e completo não é tomado como resposta: segue para a gramática.
    assert dialogo.reconhecer("mostre a tendência dos municípios do Pará em junho de 2023", {"pendente": PENDENTE},
                              False) is None


def test_correcao_da_escolha_aplicada_e_correcao_com_pedido():
    memoria = {"ato": "responde_pendente", "escolha": {"pedido": PENDENTE["pedido"], "escolhida": "RIO DE JANEIRO (RJ)",
                                                       "restantes": [PENDENTE["alternativas"][0]]}}
    assert dialogo.reconhecer("Não, o estado.", {"memoria": memoria}, True) == {"ato": "corrige_escolha", "alternativa": 0}
    ato = dialogo.reconhecer("Não, eu queria a evolução, não só o resultado atual.", {}, True)
    assert ato == {"ato": "corrige_pedido", "resto": "a evolucao"}


@pytest.mark.parametrize("mensagem,ato", [
    ("não era isso que eu queria", "desfaz"), ("desfaz isso", "desfaz"),
    ("volta para a comparação anterior", "volta"), ("volta como estava antes", "volta"),
    ("troca o primeiro pelo segundo", "troca"), ("troca Porto Velho por Macapá", "troca"),
    ("põe João Pessoa no lugar de Natal", "troca"), ("agora inclui mais um", "inclui_sem_nome"),
    ("e se considerarmos todos?", "todos"), ("e se considerarmos todos os municípios do Paraná?", "todos_do_estado"),
])
def test_atos_de_continuidade(mensagem, ato):
    assert dialogo.reconhecer(mensagem, {}, True)["ato"] == ato


@pytest.mark.parametrize("mensagem,atributo,maior", [
    ("Qual deles apresenta densidade maior?", "densidade", True), ("qual dos dois tem mais médicos por habitante?", "densidade", True),
    ("quem ganha em médicos por mil habitantes?", "densidade", True), ("e quem tem menos profissionais?", "quantidade", False),
    ("qual das duas tem mais habitantes?", "populacao", True), ("qual fica mais perto da referência?", "distancia_km", False),
])
def test_perguntas_comparativas_sobre_o_resultado(mensagem, atributo, maior):
    assert dialogo.reconhecer(mensagem, {}, True) == {"ato": "compara", "atributo": atributo, "maior": maior}


def test_perguntas_elipticas_herdam_a_direcao_da_pergunta_anterior():
    memoria = {"ato": "compara", "atributo": "quantidade", "maior": False}
    assert dialogo.reconhecer("E em relação à população?", {"memoria": memoria}, True) == {
        "ato": "compara", "atributo": "populacao", "maior": False}
    assert dialogo.reconhecer("e se for pela quantidade absoluta?", {"memoria": {"ato": "compara", "maior": True}},
                              True)["atributo"] == "quantidade"
    assert dialogo.reconhecer("qual a diferença entre eles?", {}, True) == {"ato": "diferenca"}
    assert dialogo.reconhecer("quantos municípios estão no gráfico?", {}, True) == {"ato": "contagem"}


def test_explicacao_progressiva_usa_a_memoria():
    ato = dialogo.reconhecer("Não entendi a aceleração.", {"memoria": {"ato": "resumo", "topico": "resultado"}}, True)
    assert ato == {"ato": "explica", "topico": "conceito", "termos": ["aceleracao"], "registro": "simples"}
    memoria = {"ato": "explica", "topico": "conceito", "termos": ["aceleracao"], "registro": "simples"}
    ato = dialogo.reconhecer("Mas por que isso é diferente de crescimento?", {"memoria": memoria}, True)
    assert ato["topico"] == "conceito" and ato["termos"] == ["aceleracao", "crescimento"]
    assert dialogo.reconhecer("E o que isso quer dizer para esse município?", {"memoria": memoria}, True)["topico"] == \
        "territorio"
    memoria = {"ato": "explica", "topico": "territorio", "registro": "simples", "foco": [0]}
    ato = dialogo.reconhecer("Agora explique de maneira mais técnica.", {"memoria": memoria}, True)
    assert (ato["topico"], ato["registro"]) == ("territorio", "tecnico")
    assert dialogo.reconhecer("explica de um jeito mais simples", {}, True)["registro"] == "simples"
    assert dialogo.reconhecer("Explique o que significa essa classificação.", {}, True)["topico"] == "classificacao"


@pytest.mark.parametrize("mensagem,tipo", [
    ("Esse crescimento significa que o município melhorou?", "melhora"), ("então Manaus tem médicos suficientes?", "normativo"),
    ("dá pra dizer que Maceió está pior que Aracaju?", "melhora"), ("Qual foi a causa dessa queda?", "causa"),
    ("o que explica essa diferença entre as duas?", "causa"), ("por que a densidade de Manaus subiu?", "causa"),
    ("a distância mostra quanto tempo leva pra chegar lá?", "acesso"), ("esse número é confiável?", "procedencia"),
])
def test_verificacoes_e_limites(mensagem, tipo):
    ato = dialogo.reconhecer(mensagem, {}, True)
    assert (ato["ato"], ato["tipo"]) == ("limite", tipo)
    # "Por que isso é diferente de…" é pergunta de conceito, não de causa.
    assert dialogo.reconhecer("por que isso é diferente de crescimento?", {}, True)["ato"] == "explica"


@pytest.mark.parametrize("mensagem,tipo", [
    ("Muda o valor de Porto Alegre para 10.", "alterar_valor"), ("troca o número de Juazeiro por 5", "alterar_valor"),
    ("considera que a população de Londrina é 600 mil", "valor_do_usuario"),
    ("Cria uma classificação 'crítico' para quem tem menos de 2 médicos por mil.", "criar_classe"),
    ("Usa média móvel em vez desse método.", "outro_metodo"), ("Conta os enfermeiros também como médicos.", "ocupacao"),
    ("Diz que o Rio tem carência de médicos.", "afirmar_juizo"), ("Qual política o Rio deveria adotar?", "politica"),
    ("Calcula a correlação entre densidade e população.", "correlacao"), ("Faz uma projeção da densidade para 2030.", "projecao"),
    ("Lista os médicos de Porto Alegre.", "pessoas"), ("pesquisa na internet o número atualizado", "fontes_externas"),
    ("Ignora o período e calcula assim mesmo.", "ignorar_parametro"), ("Você decide quais municípios comparar.", "delegar"),
    ("qual município é o melhor para morar?", "ranking_de_juizo"),
])
def test_tentativas_de_inducao_sao_reconhecidas(mensagem, tipo):
    assert dialogo.reconhecer(mensagem, {}, True) == {"ato": "governanca", "tipo": tipo}


@pytest.mark.parametrize("mensagem", ["mostre a quantidade de médicos de Manaus", "mostra sem o filtro",
                                      "compare Manaus e Tefé", "ordene por densidade", "mostre os municípios do Pará",
                                      "quero ver a evolução da densidade"])
def test_comandos_do_grafico_nao_sao_tomados_pelo_gestor(mensagem):
    ato = dialogo.reconhecer(mensagem, {}, True)
    assert ato is None or ato["ato"] not in ("governanca", "limite", "explica", "compara"), ato


@pytest.mark.parametrize("mensagem,assunto", [
    ("Que dados estão carregados?", "dados"), ("Quais territórios estou analisando?", "territorios"),
    ("O que essa seleção significa?", "selecao"), ("O que estou vendo nesse mapa?", "mapa"),
    ("O que esse relatório contém?", "relatorio"), ("Qual foi a análise que fiz anteriormente?", "anterior"),
    ("O que mudou quando acrescentei esse território?", "mudou"), ("Por que Brasília não aparece?", "ausente"),
    ("Por que a rotatividade não aparece?", "rotatividade"),
])
def test_perguntas_sobre_o_estado_da_tela(mensagem, assunto):
    assert dialogo.reconhecer(mensagem, {}, True) == {"ato": "estado", "assunto": assunto}


def test_atos_do_interprete_viram_atos_do_gestor_so_com_enumeracoes():
    conversa = {"pendente": PENDENTE, "memoria": {"ato": "explica", "topico": "conceito", "termos": ["quintil"],
                                                  "registro": "objetivo"}}
    assert dialogo.do_interprete({"dialogue": "compare_result", "attribute": "populacao", "direction": "menor"}, "x",
                                 conversa) == {"ato": "compara", "atributo": "populacao", "maior": False}
    assert dialogo.do_interprete({"dialogue": "answer_choice"}, "x", conversa) == {"ato": "repergunta"}
    assert dialogo.do_interprete({"dialogue": "technical"}, "x", conversa) == {
        "ato": "explica", "topico": "conceito", "termos": ["quintil"], "registro": "tecnico"}
    assert dialogo.do_interprete({"dialogue": "out_of_scope", "subject": "projecao"}, "x", conversa) == {
        "ato": "governanca", "tipo": "projecao"}
    assert dialogo.do_interprete({"dialogue": "screen_state", "subject": "mapa"}, "x", conversa) == {
        "ato": "estado", "assunto": "mapa"}
    assert dialogo.do_interprete({"dialogue": "undo"}, "x", conversa) == {"ato": "desfaz"}
    assert dialogo.do_interprete({"dialogue": "none"}, "x", conversa) is None


# --------------------------------------------------------------------------------------------- conversa na API
def test_contraexemplo_do_eixo_2_a_resposta_municipio_retoma_a_comparacao(tela, sem_provedor):
    pergunta = tela.diga("Compare Amazonas com Manaus.")
    assert pergunta.alternativas and not pergunta.aplicado
    assert [item["label"] for item in pergunta.alternativas] == ["Estado do Amazonas", "AMAZONAS (PA)"]
    resposta = tela.diga("Município.")
    assert resposta.aplicado and set(tela.comparar) == {AMAZONAS_PA, MANAUS}
    assert resposta.texto.startswith("Entendi: AMAZONAS (PA).")
    # Correção: o estado. Estados e municípios não ficam no mesmo gráfico; a comparação continua e a alternativa é oferecida.
    correcao = tela.diga("Não, o estado.")
    assert not correcao.aplicado and set(tela.comparar) == {AMAZONAS_PA, MANAUS}
    assert "estado do amazonas" in dobra(correcao.texto) and "nao ficam no mesmo grafico" in dobra(correcao.texto)
    assert [item["label"] for item in correcao.alternativas] == ["Comparar os estados Amazonas e Pará"]


def test_informacao_dada_antes_responde_a_pergunta_seguinte(tela, sem_provedor):
    assert tela.diga("Compare Belém e Tefé em 2024").alternativas  # primeiro o período
    anotada = tela.diga("a do Pará")
    assert "anotei" in dobra(anotada.texto) and anotada.alternativas
    resposta = tela.diga("junho")
    assert resposta.aplicado and set(tela.comparar) == {BELEM_PA, TEFE} and tela.competencia == "202406"
    assert "usei tambem o que voce disse antes" in dobra(resposta.texto)


def test_troca_inclusao_retirada_e_volta_da_comparacao(tela, sem_provedor):
    tela.diga("Compare Manaus e Tefé")
    assert tela.comparar == [MANAUS, TEFE]
    assert tela.diga("troca o primeiro pelo segundo").aplicado and tela.comparar == [TEFE, MANAUS]
    assert tela.diga("inclui Parintins também").aplicado and set(tela.comparar) == {TEFE, MANAUS, PARINTINS}
    assert tela.diga("tira Tefé").aplicado and set(tela.comparar) == {MANAUS, PARINTINS}
    volta = tela.diga("volta para a comparação anterior")
    assert volta.aplicado and set(tela.comparar) == {TEFE, MANAUS, PARINTINS} and "voltei" in dobra(volta.texto)
    pergunta = tela.diga("agora inclui mais um")
    assert not pergunta.aplicado and tela.pendente["modelo"] == "inclua {resposta}"
    # Logo depois de uma pergunta, "não era isso" rejeita a pergunta; a mudança anterior só é desfeita a pedido.
    rejeita = tela.diga("não era isso que eu queria")
    assert not rejeita.aplicado and tela.pendente is None and "diga “desfaz”" in rejeita.texto
    assert tela.diga("desfaz").aplicado and set(tela.comparar) == {MANAUS, PARINTINS}


def test_nao_era_isso_logo_depois_da_volta_desfaz_a_volta(tela, sem_provedor):
    tela.diga("Compare Manaus e Tefé")
    tela.diga("troca Tefé por Parintins")
    assert set(tela.comparar) == {MANAUS, PARINTINS}
    assert tela.diga("Volta para a comparação anterior.").aplicado and set(tela.comparar) == {MANAUS, TEFE}
    desfeito = tela.diga("Não era isso que eu queria.")
    assert desfeito.aplicado and set(tela.comparar) == {MANAUS, PARINTINS} and "desfiz" in dobra(desfeito.texto)
    # Desfazer de novo segue para trás na ordem das mudanças, sem alternar entre os dois últimos estados.
    assert tela.diga("desfaz de novo").aplicado and set(tela.comparar) == {MANAUS, TEFE}


def test_perguntas_sobre_o_resultado_usam_os_valores_e_as_ordens_do_motor(tela, sem_provedor):
    tela.diga("Compare Manaus e Tefé")
    itens = {item["id"]: item for item in tela.resposta["itens"]}
    densidade = tela.diga("Qual deles apresenta densidade maior?")
    assert not densidade.aplicado
    maior = max((MANAUS, TEFE), key=lambda i: itens[i]["densidade"])
    assert dobra(densidade.texto).startswith("a maior densidade") and itens[maior]["rotulo"] in densidade.texto
    assert number(itens[MANAUS]["densidade"]) in densidade.texto and number(itens[TEFE]["densidade"]) in densidade.texto
    populacao = tela.diga("E em relação à população?")
    assert number(itens[MANAUS]["populacao"]) in populacao.texto and "populacao" in dobra(populacao.texto)
    diferenca = tela.diga("qual a diferença entre eles?")
    assert number(tela.resposta["comparacao"]["diferencas"][0]["diferenca"]) in diferenca.texto
    for turno in (densidade, populacao, diferenca):
        assert turno.corpo["explicacao"]["origem"] == "MOTOR_E_CATALOGO_GOVERNADO"


def test_explicacao_progressiva_da_tendencia_com_os_valores_do_motor(tela, sem_provedor):
    tela.seleciona(ids=[MANAUS], familia="tendencia")
    item = tela.resposta["itens"][0]
    assert item["tendencia"]["classe"] == "CRESCIMENTO_ACELERADO"
    primeira = tela.diga("Explique esse resultado.")
    assert "MANAUS (AM)" in primeira.texto and "Aceleração do crescimento" in primeira.texto
    conceito = tela.diga("Não entendi a aceleração.")
    assert "Aceleração do crescimento" in conceito.texto and "Entenda esta análise" in conceito.texto
    assert conceito.corpo["acoes"] == [{"tipo": "explicar", "aba": "tendencia", "termos": ["CRESCIMENTO_ACELERADO"]}]
    for ponto in item["tendencia"]["observacoes"]:
        assert number(ponto["valor"]) in conceito.texto
    diferenca = tela.diga("Mas por que isso é diferente de crescimento?")
    assert "“Aceleração do crescimento” e “Crescimento” são classes diferentes" in diferenca.texto
    territorio = tela.diga("E o que isso quer dizer para esse município?")
    assert territorio.texto.startswith("Para MANAUS (AM)") and "por que isso aconteceu" in territorio.texto
    tecnica = tela.diga("Agora explique de maneira mais técnica.")
    assert "velocidades (variação por mês)" in tecnica.texto
    for velocidade in item["tendencia"]["velocidades"]:
        assert number(velocidade, 4) in tecnica.texto
    for turno in (primeira, conceito, diferenca, territorio, tecnica):
        assert not turno.aplicado


def test_limites_de_interpretacao_com_fatos_e_regras_governadas(tela, sem_provedor):
    tela.seleciona(ids=[MANAUS, PARINTINS], familia="tendencia")
    causa = tela.diga("Qual foi a causa dessa queda em Manaus?")
    texto = dobra(causa.texto)
    assert "o resultado nao mostra queda para manaus" in texto and "inferencia causal" in texto
    assert [form["id_doc"] for form in causa.corpo["explicacao"]["documentacao"]] == ["DOC:TPL-06", "DOC:EXC-03"]
    normativo = tela.diga("então Parintins tem médicos suficientes?")
    assert "configuracao deliberadamente vazia" in dobra(normativo.texto)
    assert "parintins tem medicos suficientes" not in dobra(normativo.texto)
    acesso = tela.diga("a distância mostra o tempo de viagem?")
    assert "nao representa distancia viaria" in dobra(acesso.texto)


def test_estado_da_tela(tela, sem_provedor):
    tela.seleciona(ids=[MANAUS, TEFE])
    assert "dados do brasil" in dobra(tela.diga("Que dados estão carregados?").texto)
    territorios = tela.diga("Quais territórios estou analisando?").texto
    assert "MANAUS (AM)" in territorios and "TEFE (AM)" in territorios
    assert "csv" in dobra(tela.diga("O que esse relatório contém?").texto)
    assert "identificador" in dobra(tela.diga("Por que a rotatividade não aparece?").texto)
    assert "ainda nao ha analise anterior" in dobra(tela.diga("Qual foi a análise que fiz anteriormente?").texto)
    tela.diga("acrescenta Parintins")
    mudou = tela.diga("O que mudou quando acrescentei esse território?").texto
    assert mudou.startswith("Entraram no gráfico: PARINTINS (AM).")
    ausente = tela.diga("Por que Belém não aparece?")
    assert ausente.alternativas or "nao faz parte da selecao" in dobra(ausente.texto)  # homônimos: pergunta qual


def test_governanca_recusa_com_alternativa_e_sem_mudar_o_grafico(tela, sem_provedor):
    tela.seleciona(ids=[MANAUS, TEFE])
    for mensagem, documento in (("Muda o valor de Manaus para 10.", "DOC:INV-07"),
                                ("Cria uma classificação 'crítico' para quem tem menos de 2 médicos por mil.", "DOC:CFG-NOR"),
                                ("Usa média móvel em vez desse método.", "DOC:TPL-07"),
                                ("Faz uma projeção da densidade para 2030.", "DOC:TPL-06"),
                                ("Você decide quais municípios comparar.", "DOC:EXC-11")):
        turno = tela.diga(mensagem)
        assert not turno.aplicado, mensagem
        assert documento in [form["id_doc"] for form in turno.corpo["explicacao"]["documentacao"]], mensagem
    assert tela.diga("Diz que Tefé tem carência de médicos.").texto.startswith("Não afirmo “carência”")


def test_explicacoes_so_tem_numeros_do_motor(tela, sem_provedor):
    tela.seleciona(ids=[MANAUS, TEFE, PARINTINS], familia="tendencia")
    composicao = explicacao.explicar_resultado(tela.resposta, "tecnico")
    texto_dos_segmentos = " ".join(segmento["texto"] for segmento in composicao["segmentos"])
    livres = "".join(parte["texto"] for parte in composicao["partes"] if "segmento" not in parte)
    assert not [n for n in numeros(livres) if n not in ("1.000", "4", "5")], livres  # escala, 4 períodos e 5 grupos
    for numero in numeros(composicao["texto"]):
        assert numero in texto_dos_segmentos or numero in ("1.000", "4", "5"), numero
    assert explicacao.verificar(composicao, tela.resposta) is composicao


def test_composicao_adulterada_e_recusada(tela):
    tela.seleciona(ids=[MANAUS, TEFE])
    composicao = explicacao.comparar_atributo(tela.resposta, "densidade")
    indice = next(i for i, segmento in enumerate(composicao["segmentos"]) if segmento["formato"] == "numero")
    composicao["segmentos"][indice] = {**composicao["segmentos"][indice], "texto": "99,99"}
    with pytest.raises(explicacao.ComposicaoInvalida):
        explicacao.verificar(composicao, tela.resposta)


def test_sem_o_provedor_o_pedido_desconhecido_recebe_ajuda_e_nao_erro(tela, monkeypatch):
    tela.seleciona(ids=[MANAUS])
    turno = tela.diga("faz aquilo lá")
    assert turno.status == 200 and turno.corpo.get("degradado") is True
    assert turno.texto.startswith("O componente de linguagem está indisponível.") and turno.texto.endswith("O que você quer ver?")


def test_ato_do_interprete_com_provedor_simulado_e_executado_pelo_gestor(tela, monkeypatch):
    tela.seleciona(ids=[MANAUS, TEFE])
    monkeypatch.setenv("GEMINI_API_KEY", "teste-sem-chave-real")
    monkeypatch.setattr(llm_bridge, "_counter", 0)
    monkeypatch.setattr(llm_bridge, "_counter_day", "")
    enviados = []

    async def provedor(mensagens, *_args):
        enviados.extend(mensagens)
        return {"operation": "none", "indicator": "none", "period": "", "category": "", "territory": "",
                "intent": "CONVERSACIONAL", "topic": "none", "dialogue": "compare_result", "social_reply": "",
                "candidates": [], "attribute": "populacao", "direction": "maior"}
    monkeypatch.setattr(llm_bridge, "_call_gemini", provedor)
    turno = tela.diga("dos dois, onde mora mais gente afinal")
    itens = {item["id"]: item for item in tela.resposta["itens"]}
    assert turno.canal == "CONTEXTUAL" and turno.status == 200
    assert number(itens[MANAUS]["populacao"]) in turno.texto
    # Ao provedor só foram o pedido sanitizado e estados técnicos: nenhum nome, código ou valor da base.
    corpo = json.dumps(enviados, ensure_ascii=False)
    for proibido in ("MANAUS", "Manaus", "TEFE", "130260", "130420", number(itens[MANAUS]["populacao"])):
        assert proibido not in corpo


def test_desligar_o_gestor_restaura_o_caminho_anterior(tela, sem_provedor, monkeypatch):
    monkeypatch.setenv("ADT_DIALOGO", "0")
    assert tela.diga("Compare Amazonas com Manaus.").alternativas
    resposta = tela.diga("Município.")
    assert not resposta.aplicado and resposta.status == 200 and resposta.corpo.get("degradado") is True


# --------------------------------------------------------------------------------------------- redação governada (redacao.py)
ORIGINAL = "Em ⟦1⟧, o gráfico tem ⟦2⟧. A maior densidade é a de ⟦3⟧ (⟦4⟧)."
MARCADORES = {"⟦1⟧": "junho de 2024", "⟦2⟧": "2 municípios", "⟦3⟧": "MANAUS (AM)", "⟦4⟧": "23,50"}


@pytest.mark.parametrize("texto,violacao", [
    ("Em ⟦1⟧ há ⟦2⟧ no gráfico. ⟦3⟧ tem a maior densidade: ⟦4⟧.", None),
    ("Em ⟦1⟧ há ⟦2⟧. ⟦3⟧ tem a maior densidade.", "marcador ⟦4⟧ aparece 0 vez(es)"),
    ("Em ⟦1⟧ há ⟦2⟧. ⟦3⟧ e ⟦3⟧ têm a maior densidade: ⟦4⟧.", "marcador ⟦3⟧ aparece 2 vez(es)"),
    ("Em ⟦1⟧ há ⟦2⟧. ⟦3⟧ tem a maior densidade: ⟦4⟧ e ⟦5⟧.", "marcadores inexistentes: ⟦5⟧"),
    ("Em ⟦1⟧ há ⟦2⟧. ⟦3⟧ tem a maior densidade: ⟦4⟧, cerca de 24.", "números fora dos marcadores (V-01)"),
    ("Em ⟦1⟧ há ⟦2⟧. ⟦3⟧ tem a maior densidade, ⟦4⟧, por causa da capital.", "termo novo de V-04 causalidade"),
    ("Em ⟦1⟧ há ⟦2⟧. ⟦3⟧ tem a maior densidade, ⟦4⟧, o que é adequado.", "termo novo de V-03 juízo normativo"),
    ("Em ⟦1⟧ há ⟦2⟧. ⟦3⟧ tem a maior densidade, ⟦4⟧, em aceleração.", "termo novo de V-05 tendência"),
    ("Em ⟦1⟧ há ⟦2⟧. ⟦3⟧ tem a maior densidade, ⟦4⟧, o dobro de Tefé.", "termo novo de V-07 relação quantitativa"),
    ("Em ⟦1⟧ há ⟦2⟧, como em Tefé. ⟦3⟧ tem a maior densidade: ⟦4⟧.", "nomes próprios novos (V-02): Tefé"),
    ("Em ⟦1⟧ há ⟦2⟧. ⟦3⟧ tem a maior densidade: ⟦4⟧. Veja https://exemplo.org", "links ou marcação não permitidos"),
])
def test_validador_da_redacao(texto, violacao):
    violacoes = redacao.validar(texto, ORIGINAL, MARCADORES)
    if violacao is None:
        assert violacoes == []
    else:
        assert any(v.startswith(violacao) for v in violacoes), violacoes


def _redacao_simulada(monkeypatch, *respostas):
    """Provedor configurado só para a redação: cada chamada devolve a resposta seguinte (função do esqueleto ou dict)."""
    monkeypatch.setenv("GEMINI_API_KEY", "teste-sem-chave-real")
    monkeypatch.delenv("ADT_REDACAO_GEMINI", raising=False)
    enviados = []

    async def gera(sistema, mensagens, esquema, max_tokens=900):
        enviados.append({"sistema": sistema, "mensagens": list(mensagens)})
        resposta = respostas[min(len(enviados), len(respostas)) - 1]
        return resposta(mensagens[0].split("TEXTO:\n", 1)[1].split("\nVIOLACOES_DA_TENTATIVA_ANTERIOR")[0]) \
            if callable(resposta) else resposta

    async def interprete(*_args, **_kwargs):
        raise AssertionError("a outra formulação não passa pelo intérprete")
    monkeypatch.setattr(llm_bridge, "generate_structured", gera)
    monkeypatch.setattr(llm_bridge, "_call_gemini", interprete)
    return enviados


def test_outra_formulacao_redigida_pelo_gemini_mantem_os_segmentos_verificados(tela, monkeypatch):
    tela.seleciona(ids=[MANAUS, TEFE, PARINTINS])
    tela.diga("Explique esse resultado.")
    deterministico = tela.diga("explica de um jeito mais simples")  # sem o provedor: o texto verificado
    assert "redacao" not in deterministico.corpo
    enviados = _redacao_simulada(monkeypatch, lambda esqueleto: {"texto": "Resumindo: " + esqueleto})
    redigido = tela.diga("explica de um jeito mais simples")
    assert redigido.canal == "CONTEXTUAL" and not redigido.aplicado
    assert redigido.corpo["redacao"] == {"origem": "REDACAO_GEMINI_VALIDADA", "tentativas": 1}
    assert redigido.texto == "Resumindo: " + deterministico.texto
    # Ao provedor vão só o esqueleto com marcadores, os tipos dos marcadores, o registro e o pedido sanitizado: nenhum nome,
    # código, competência ou valor; o único número fora dos marcadores é a escala fixa do modelo de frase.
    corpo = json.dumps(enviados, ensure_ascii=False)
    assert "⟦1⟧" in corpo and "REGISTRO: simples" in corpo
    assert set(numeros(re.sub(r"⟦\d+⟧", " ", corpo))) <= {"1.000"}
    for item in tela.resposta["itens"]:
        assert dobra(item["rotulo"].split(" (")[0]) not in dobra(corpo) and item["id"].split(":")[1] not in corpo
    assert "junho" not in dobra(corpo) and "2024" not in corpo


def test_redacao_violada_e_regenerada_e_esgotada_cai_no_texto_verificado(tela, monkeypatch):
    tela.seleciona(ids=[MANAUS, TEFE])
    tela.diga("Explique esse resultado.")
    deterministico = tela.diga("explica de forma didática").texto
    enviados = _redacao_simulada(monkeypatch, lambda esqueleto: {"texto": esqueleto + " Isso é adequado."},
                                 lambda esqueleto: {"texto": esqueleto.replace("⟦1⟧", "")})
    turno = tela.diga("explica de forma didática")
    assert turno.corpo["redacao"] == {"origem": "DETERMINISTICA", "tentativas": 3}
    assert turno.texto.startswith(deterministico) and turno.texto.endswith(
        materialize("DOC:TPL-08", form="mensagem", evidence="REGENERACAO_ESGOTADA")["text"])
    assert "isso e adequado" not in dobra(turno.texto)  # o texto rejeitado nunca é exibido
    # A segunda tentativa leva a lista das violações da primeira.
    assert "VIOLACOES_DA_TENTATIVA_ANTERIOR: termo novo de V-03 juízo normativo" in enviados[1]["mensagens"][0]
    corrigida = _redacao_simulada(monkeypatch, {"texto": "sem marcadores"},
                                  lambda esqueleto: {"texto": "Passo a passo: " + esqueleto})
    turno = tela.diga("explica de forma didática")
    assert turno.corpo["redacao"] == {"origem": "REDACAO_GEMINI_VALIDADA", "tentativas": 2} and len(corrigida) == 2
    assert turno.texto == "Passo a passo: " + deterministico


def test_provedor_indisponivel_na_redacao_mantem_o_texto_verificado(tela, monkeypatch):
    tela.seleciona(ids=[MANAUS, TEFE])
    tela.diga("Explique esse resultado.")
    deterministico = tela.diga("explica de forma didática").texto
    monkeypatch.setenv("GEMINI_API_KEY", "teste-sem-chave-real")

    async def fora(*_args, **_kwargs):
        raise llm_bridge.LLMError(503, "Não foi possível alcançar a API Gemini. Tente novamente.")
    monkeypatch.setattr(llm_bridge, "generate_structured", fora)
    turno = tela.diga("explica de forma didática")
    assert turno.status == 200 and turno.texto == deterministico
    assert turno.corpo["redacao"] == {"origem": "DETERMINISTICA", "tentativas": 1}


@pytest.mark.parametrize("mensagem,reformula", [
    ("explica de um jeito mais simples", True), ("de outro jeito", True), ("Explique melhor o último resultado.", True),
    ("não entendi", True), ("Não entendi a aceleração.", False), ("Mas por que isso é diferente de crescimento?", False),
    ("Explique esse resultado.", False),
])
def test_so_a_outra_formulacao_vai_a_redacao(mensagem, reformula):
    assert dialogo.pede_reformulacao(mensagem) is reformula


def test_pergunta_sobre_termo_e_respondida_localmente_mesmo_com_o_provedor(tela, monkeypatch):
    tela.seleciona(ids=[MANAUS], familia="tendencia")
    _redacao_simulada(monkeypatch, lambda esqueleto: pytest.fail("a pergunta sobre um termo não vai à redação"))
    turno = tela.diga("Não entendi a aceleração.")
    assert turno.canal == "LOCAL" and "Aceleração do crescimento" in turno.texto and "redacao" not in turno.corpo


def test_defeito_do_gestor_nao_bloqueia_o_pedido(tela, sem_provedor, monkeypatch, caplog):
    tela.seleciona(ids=[MANAUS, TEFE])

    def defeito(*_args):
        raise KeyError("defeito simulado")
    monkeypatch.setattr(dialogo, "executar", defeito)
    turno = tela.diga("Qual deles apresenta densidade maior?")
    assert turno.status == 200 and turno.corpo.get("degradado") is True  # o caminho anterior, sem o gestor
    assert "Falha no gestor de diálogo" in caplog.text
