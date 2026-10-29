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


def test_sem_o_provedor_o_pedido_desconhecido_recebe_a_mensagem_cordial(tela, monkeypatch):
    tela.seleciona(ids=[MANAUS])
    turno = tela.diga("faz aquilo lá")
    assert turno.status == 200 and turno.corpo.get("degradado") is True
    assert turno.corpo["indisponibilidade"] == {"tipo": "indisponivel", "titulo": llm_bridge.TITULO_INDISPONIVEL,
                                                "texto": llm_bridge.TEXTO_INDISPONIVEL}
    assert turno.texto == llm_bridge.TEXTO_INDISPONIVEL and not re.search(r"HTTP|\b50[0-9]\b|GEMINI_API_KEY", turno.texto)


def _gemini_simulado(monkeypatch, *respostas, interpretacao=None):
    """Provedor configurado com chave fictícia e sem rede: a redação devolve as respostas na ordem (dict ou função das
    entradas); a interpretação, a dada (sem ela, chamá-la é falha do teste)."""
    monkeypatch.setenv("GEMINI_API_KEY", "teste-sem-chave-real")
    monkeypatch.delenv("ADT_CONVERSA_GEMINI", raising=False)
    enviados = {"redacao": [], "interpretacao": []}

    async def gera(sistema, mensagens, esquema, max_tokens=1200):
        enviados["redacao"].append({"sistema": sistema, "mensagens": list(mensagens)})
        resposta = respostas[min(len(enviados["redacao"]), len(respostas)) - 1]
        return resposta(mensagens) if callable(resposta) else resposta

    async def interprete(mensagens, *_args):
        enviados["interpretacao"].append(list(mensagens))
        if interpretacao is None:
            raise AssertionError("o intérprete não devia ser chamado")
        return interpretacao(mensagens) if callable(interpretacao) else interpretacao
    monkeypatch.setattr(llm_bridge, "generate_structured", gera)
    monkeypatch.setattr(llm_bridge, "_call_gemini", interprete)
    return enviados


def _cartao(enviados) -> dict:
    """O cartão do contexto da última redação, como o provedor o recebeu."""
    entrada = next(m for m in enviados["redacao"][-1]["mensagens"] if m.startswith("CONTEXTO_DA_CONVERSA: "))
    return json.loads(entrada[len("CONTEXTO_DA_CONVERSA: "):])


def test_ato_do_interprete_com_provedor_simulado_e_executado_pelo_gestor_e_redigido(tela, monkeypatch):
    tela.seleciona(ids=[MANAUS, TEFE])
    itens = {item["id"]: item for item in tela.resposta["itens"]}
    populacao = number(itens[MANAUS]["populacao"])
    enviados = _gemini_simulado(
        monkeypatch, interpretacao={
            "operation": "none", "indicator": "none", "period": "", "category": "", "territory": "",
            "intent": "CONVERSACIONAL", "topic": "none", "dialogue": "compare_result", "social_reply": "",
            "candidates": [], "attribute": "populacao", "direction": "maior",
            "resposta": "Dos dois, quem tem mais habitantes é MANAUS (AM), com " + populacao + " habitantes."})
    turno = tela.diga("dos dois, onde mora mais gente afinal")
    assert turno.canal == "CONTEXTUAL" and turno.status == 200
    # O texto do Gemini veio com a interpretação, passou na conferência (a ordem e o valor são os do motor) e aparece.
    assert turno.texto == "Dos dois, quem tem mais habitantes é MANAUS (AM), com " + populacao + " habitantes."
    assert turno.corpo["redacao"] == {"origem": "GEMINI_VALIDADO", "tentativas": 1} and enviados["redacao"] == []
    # Ao provedor foram o pedido triado e o cartão com o resultado agregado em exibição (autorização D de 26/10/2026):
    # os nomes e os valores como na tela; nenhum código territorial, nome de coluna ou de arquivo.
    corpo = json.dumps(enviados["interpretacao"], ensure_ascii=False)
    assert "MANAUS (AM)" in corpo and populacao in corpo
    for proibido in ("130260", "130420", "cod_ibge", "população_estimada", "Dados_Municipios_Brasil"):
        assert proibido not in corpo


def test_texto_do_gemini_com_ordem_errada_e_regenerado_e_o_fiel_aparece(tela, monkeypatch):
    tela.seleciona(ids=[MANAUS, TEFE])
    enviados = _gemini_simulado(
        monkeypatch,
        {"resposta": "A maior densidade é a de MANAUS (AM): 23,50 por 1.000 habitantes; TEFE (AM) fica com 10."},
        interpretacao={
            "operation": "none", "indicator": "none", "period": "", "category": "", "territory": "",
            "intent": "CONVERSACIONAL", "topic": "none", "dialogue": "compare_result", "social_reply": "",
            "candidates": [], "attribute": "densidade", "direction": "maior",
            "resposta": "TEFE (AM) tem a maior densidade dos dois."})
    turno = tela.diga("e entre eles, qual se destaca na densidade?")
    assert turno.corpo["redacao"] == {"origem": "GEMINI_VALIDADO", "tentativas": 2}
    assert turno.texto.startswith("A maior densidade é a de MANAUS (AM)")
    # A nova tentativa leva a violação da primeira, e o texto rejeitado nunca aparece.
    violacoes = next(m for m in enviados["redacao"][0]["mensagens"] if m.startswith("VIOLACOES_DA_TENTATIVA_ANTERIOR"))
    assert "V-07" in violacoes and "TEFE (AM) tem a maior" not in turno.texto


def test_explicacao_redigida_pelo_gemini_e_conferida_e_esgotada_cai_na_reserva(tela, monkeypatch):
    tela.seleciona(ids=[MANAUS, TEFE, PARINTINS])
    deterministico = tela.diga("Explique esse resultado.")  # sem o provedor: a resposta verificada do gestor
    assert "redacao" not in deterministico.corpo and deterministico.canal == "LOCAL"
    enviados = _gemini_simulado(monkeypatch, {"resposta": "Esse resultado mostra que MANAUS (AM) tem médicos suficientes."},
                                {"resposta": "MANAUS (AM) tem cerca de 24 por 1.000 habitantes."},
                                {"resposta": "A densidade de Recife é maior."})
    turno = tela.diga("Explique esse resultado.")
    assert turno.canal == "CONTEXTUAL" and turno.corpo["redacao"] == {"origem": "DETERMINISTICA", "tentativas": 3}
    assert turno.texto.startswith(deterministico.texto) and turno.texto.endswith(
        materialize("DOC:TPL-08", form="mensagem", evidence="REGENERACAO_ESGOTADA")["text"])
    assert "suficientes" not in turno.texto and "Recife" not in turno.texto
    assert len(enviados["redacao"]) == 3  # a primeira e só 2 regenerações (RQ-SIN-05)
    cartao = _cartao(enviados)
    assert cartao["resultado_em_exibicao"]["frase_resumo_do_motor"] == tela.resposta["resumo"]["texto"]
    assert cartao["resposta_verificada_do_sistema"] == deterministico.texto


def test_explicacao_fiel_redigida_pelo_gemini_aparece_com_uma_so_chamada(tela, monkeypatch):
    tela.seleciona(ids=[MANAUS, TEFE, PARINTINS])
    texto = ("Em junho de 2024 o gráfico tem 3 municípios. A maior densidade é a de MANAUS (AM), com 23,50 por 1.000 "
             "habitantes, e a menor, a de TEFE (AM), com 10 por 1.000 habitantes. A densidade compara profissionais e "
             "população; sozinha, não diz se há médicos suficientes.")
    enviados = _gemini_simulado(monkeypatch, {"resposta": "não devia ser chamado"}, interpretacao={
        "operation": "none", "indicator": "none", "period": "", "category": "", "territory": "",
        "intent": "CONVERSACIONAL", "topic": "none", "dialogue": "reformulate", "style": "simples", "social_reply": "",
        "candidates": [], "resposta": texto})
    turno = tela.diga("Me conta o que esse gráfico está dizendo, sem complicar")
    # A formulação que a leitura local não cobre vai ao intérprete, que já devolve o texto; conferido, ele aparece.
    assert turno.canal == "CONTEXTUAL" and turno.corpo["redacao"] == {"origem": "GEMINI_VALIDADO", "tentativas": 1}
    assert turno.texto == texto and len(enviados["interpretacao"]) == 1 and enviados["redacao"] == []


def test_paráfrase_da_classe_conserva_o_criterio_do_motor(tela, monkeypatch):
    tela.seleciona(ids=[MANAUS], familia="tendencia")
    _gemini_simulado(monkeypatch,
                     {"resposta": "Aceleração do crescimento quer dizer que o indicador cresceu mais de 10% ao ano."},
                     {"resposta": "Aceleração do crescimento quer dizer que o indicador subiu em todos os períodos e cada "
                                  "alta foi do mesmo tamanho ou maior que a anterior: o crescimento ganhou ritmo. Em "
                                  "MANAUS (AM), os valores foram 15, 17, 20 e 23,50."})
    turno = tela.diga("Não entendi a aceleração.")
    assert turno.canal == "CONTEXTUAL" and turno.corpo["redacao"] == {"origem": "GEMINI_VALIDADO", "tentativas": 2}
    assert "10%" not in turno.texto and "ganhou ritmo" in turno.texto
    assert turno.corpo.get("acoes")  # a tela continua abrindo "Entenda esta análise" com a classe destacada


def test_provedor_indisponivel_na_redacao_mantem_a_resposta_verificada(tela, monkeypatch):
    tela.seleciona(ids=[MANAUS, TEFE])
    deterministico = tela.diga("Explique esse resultado.").texto
    monkeypatch.setenv("GEMINI_API_KEY", "teste-sem-chave-real")

    async def fora(*_args, **_kwargs):
        raise llm_bridge.LLMError(503, "Não foi possível alcançar a API Gemini. Tente novamente.", "indisponivel")
    monkeypatch.setattr(llm_bridge, "generate_structured", fora)
    turno = tela.diga("Explique esse resultado.")
    assert turno.status == 200 and turno.texto == deterministico
    assert turno.corpo["redacao"] == {"origem": "DETERMINISTICA", "tentativas": 1}


@pytest.mark.parametrize("mensagem,reformula", [
    ("explica de um jeito mais simples", True), ("de outro jeito", True), ("Explique melhor o último resultado.", True),
    ("não entendi", True), ("Não entendi a aceleração.", False), ("Mas por que isso é diferente de crescimento?", False),
    ("Explique esse resultado.", False),
])
def test_pedido_de_outra_formulacao_e_reconhecido(mensagem, reformula):
    assert dialogo.pede_reformulacao(mensagem) is reformula


def test_comandos_e_governanca_continuam_deterministicos_com_o_provedor(tela, monkeypatch):
    tela.seleciona(ids=[MANAUS, TEFE])
    _gemini_simulado(monkeypatch, {"resposta": "não devia ser chamado"})
    recusa = tela.diga("Muda o valor de Manaus para 50.")
    assert recusa.canal == "LOCAL" and "redacao" not in recusa.corpo
    desfaz = tela.diga("Compare Manaus e Tefé")
    assert desfaz.canal == "LOCAL" and "redacao" not in desfaz.corpo


def test_defeito_do_gestor_nao_bloqueia_o_pedido(tela, sem_provedor, monkeypatch, caplog):
    tela.seleciona(ids=[MANAUS, TEFE])

    def defeito(*_args):
        raise KeyError("defeito simulado")
    monkeypatch.setattr(dialogo, "executar", defeito)
    turno = tela.diga("Qual deles apresenta densidade maior?")
    assert turno.status == 200 and turno.corpo.get("degradado") is True  # o caminho anterior, sem o gestor
    assert "Falha no gestor de diálogo" in caplog.text


# --------------------------------------------------------------------------------------------- comparação pelos extremos
# Pedido do responsável (26/10/2026): "compare os municípios de maior e menor densidade" identifica quem tem o maior e o menor
# valor e abre a comparação no gráfico, sem pedir os nomes; quem entra vem das ordens do motor, com os empates.
@pytest.mark.parametrize("mensagem", ["compare o de maior e o de menor densidade",
                                      "Comparar os municípios de maior e menor densidade", "compare os extremos",
                                      "compare o maior e o menor", "compare o primeiro e o último", "compare os dois maiores",
                                      "qual a diferença entre o de maior e o de menor densidade?"])
def test_comparacao_pelos_extremos_e_reconhecida_sem_nomes(mensagem):
    assert dialogo.reconhecer(mensagem, {}, True) == {"ato": "compara_extremos"}


def test_extremos_no_plural_sem_quantidade_e_com_nome_do_grafico():
    assert dialogo.reconhecer("compare os municípios mais populosos", {}, True) == {"ato": "compara_extremos", "quantos": None}
    assert dialogo.reconhecer("compare os municípios de menor densidade", {}, True) == {"ato": "compara_extremos",
                                                                                      "quantos": None}
    # Com o nome de um território do gráfico, a comparação segue pelos nomes; a diferença sem extremos lê a comparação
    # aberta.
    assert dialogo.reconhecer("compare Manaus com o de menor densidade", {}, True, nomes_no_resultado=["MANAUS (AM)"]) is None
    assert dialogo.reconhecer("qual a diferença entre eles?", {}, True) == {"ato": "diferenca"}


def _unidades(tela):
    return {item["id"]: item for item in tela.resposta["itens"] if item["tipo"] == "municipio"}


def test_comparacao_pelos_extremos_abre_a_comparacao_com_as_ordens_do_motor(tela, sem_provedor):
    tela.seleciona(ids=[MANAUS, TEFE, PARINTINS])
    itens = _unidades(tela)
    ordem = sorted(itens, key=lambda i: -itens[i]["densidade"])
    turno = tela.diga("Comparar os municípios de maior e menor densidade")
    assert turno.aplicado and tela.comparar == [ordem[0], ordem[-1]]
    assert turno.texto.startswith("Abri a comparação lado a lado com o de maior e o de menor densidade em junho de 2024: ")
    for unidade in (ordem[0], ordem[-1]):
        assert itens[unidade]["rotulo"] in turno.texto and number(itens[unidade]["densidade"]) in turno.texto
    assert "continuar" not in turno.corpo and not set(numeros(turno.texto)) - {
        number(itens[i]["densidade"]) for i in itens} - {"1.000", "2024"}
    dois = tela.diga("compare os dois maiores")
    assert dois.aplicado and tela.comparar == ordem[:2] and "os dois maiores em densidade" in dois.texto


def test_extremos_com_empate_entram_juntos(tela, sem_provedor):
    tela.seleciona(ids=[MANAUS, TEFE, AMAZONAS_PA])
    itens = _unidades(tela)
    assert itens[TEFE]["densidade"] == itens[AMAZONAS_PA]["densidade"]  # 10 por 1.000 habitantes nos dois
    turno = tela.diga("compare o de maior e o de menor densidade")
    assert turno.aplicado and set(tela.comparar) == {MANAUS, TEFE, AMAZONAS_PA}
    assert "Há empate na posição, e os empatados entram juntos." in turno.texto


def test_extremos_de_um_estado_fora_do_grafico_mostram_os_municipios_e_continuam(tela, sem_provedor):
    tela.seleciona(ids=[MANAUS])
    primeiro = tela.diga("compare o de maior e o de menor densidade do Pará")
    assert primeiro.aplicado and tela.municipios == {"todos": False, "estados": ["15"], "ids": []}
    assert primeiro.corpo["continuar"] == "compare o de maior e o de menor densidade"
    assert primeiro.texto == ("Mostrei os municípios do Pará; assim que o gráfico estiver pronto, comparo o de maior e o de "
                              "menor densidade.")
    segundo = tela.continua(primeiro)
    assert set(_unidades(tela)) == {AMAZONAS_PA, BELEM_PA}
    assert segundo.aplicado and tela.comparar == [BELEM_PA, AMAZONAS_PA]
    # A continuação é enviada pela tela: não vira mensagem da pessoa no histórico.
    assert tela.historico[-1] == "compare o de maior e o de menor densidade do Pará"


def test_diferenca_entre_o_maior_e_o_menor_e_lida_quando_o_motor_calcula(tela, sem_provedor):
    tela.seleciona(ids=[MANAUS, TEFE, PARINTINS])
    pedido = tela.diga("qual a diferença entre o de maior e o de menor densidade?")
    assert pedido.aplicado and set(tela.comparar) == {MANAUS, TEFE}
    assert pedido.corpo["continuar"] == "qual a diferença entre eles?"
    assert pedido.texto.endswith("Assim que o motor calcular a diferença, eu leio para você.")
    leitura = tela.continua(pedido)
    assert not leitura.aplicado and set(tela.comparar) == {MANAUS, TEFE}
    assert number(tela.resposta["comparacao"]["diferencas"][0]["diferenca"]) in leitura.texto


def test_extremos_no_plural_perguntam_quantos_e_a_resposta_digitada_compara(tela, sem_provedor):
    tela.seleciona(ids=[MANAUS, TEFE, PARINTINS, BELEM_PA])
    itens = _unidades(tela)
    ordem = sorted(itens, key=lambda i: -itens[i]["populacao"])
    pergunta = tela.diga("compare os municípios mais populosos")
    assert not pergunta.aplicado and tela.comparar is None
    assert pergunta.texto == ("A comparação lado a lado mostra 2 ou 3 itens. Quer comparar os dois ou os três maiores em "
                              "população?")
    assert [(c["label"], c["draft"], c["send"]) for c in pergunta.alternativas] == [
        ("Os dois maiores em população", "compare os dois maiores em população", True),
        ("Os três maiores em população", "compare os três maiores em população", True)]
    resposta = tela.diga("os três")
    assert resposta.aplicado and tela.comparar == ordem[:3]
    assert resposta.texto.startswith("Entendi: Os três maiores em população. Abri a comparação lado a lado")


# --------------------------------------------------------------------------------------------- proximidade pela conversa
# Pedido do responsável (28/10/2026): "quero identificar o município de menor densidade e o mais próximo a ele com densidade de
# no mínimo 1,5 médicos por mil habitantes" ia às Condições do gráfico. O extremo vem das ordens do motor sobre o gráfico em
# exibição (com os empates, como na comparação pelos extremos), a condição é da referência (CAP-REF-01, por critério de
# CAP-SUB-01) e o pedido vira a Escolha dos territórios da Análise Espacial; quando o motor calcula, a conversa lê a referência
# mais próxima e a distância, copiadas da resposta.
@pytest.mark.parametrize("mensagem", [
    "quero identificar o município de menor densidade e o mais próximo a ele com densidade de no mínimo 1,5 médicos por mil "
    "habitantes", "o mais populoso e o mais próximo dele com densidade acima de 3",
    "a cidade com a densidade mais baixa e a mais próxima dela com mais de 50 mil habitantes"])
def test_proximidade_a_partir_do_extremo_e_reconhecida(mensagem):
    assert dialogo.reconhecer(mensagem, {}, True) == {"ato": "proximidade"}
    assert dialogo.reconhecer(mensagem, {}, False) is None  # sem gráfico calculado, a gramática explica


def test_proximidade_com_condicao_e_sem_extremo_passa_pelo_gestor_so_com_o_grafico_calculado():
    # "Qual o mais próximo de Manaus com densidade acima de 2?" não é pergunta sobre o resultado em exibição: com o gráfico
    # calculado, o gestor confere se a Análise Espacial existe e passa à gramática; sem ele, a gramática direto.
    assert dialogo.reconhecer("qual o município mais próximo de Manaus com densidade acima de 2?", {}, True) == {
        "ato": "proximidade", "extremo": False}
    assert dialogo.reconhecer("qual o município mais próximo de Manaus com densidade acima de 2?", {}, False) is None
    # A pergunta pela referência mais próxima, com a Escolha dos territórios em exibição, é a leitura; sem ela, como antes.
    assert dialogo.reconhecer("qual o mais próximo?", {}, True, resultado_consulta=True) == {"ato": "referencia_proxima"}
    assert dialogo.reconhecer("qual a referência mais próxima?", {}, True, resultado_consulta=True) == {
        "ato": "referencia_proxima"}
    assert dialogo.reconhecer("qual o mais próximo?", {}, True)["ato"] == "compara"
    # O intérprete com o provedor também pode classificar (enumeração nearest_reference); nomes e valores ficam aqui.
    assert dialogo.do_interprete({"dialogue": "nearest_reference"}, "o de menor densidade e o mais perto dele com densidade "
                                 "acima de 2", {}) == {"ato": "proximidade"}
    assert dialogo.do_interprete({"dialogue": "nearest_reference"}, "e qual é a mais próxima?", {}) == {
        "ato": "referencia_proxima"}
    assert dialogo.do_interprete({"dialogue": "nearest_reference"}, "a mais perto de Manaus com densidade acima de 2",
                                 {}) == {"ato": "proximidade", "extremo": False}


def test_proximidade_a_partir_do_extremo_abre_a_escolha_e_le_a_referencia_mais_proxima(tela, sem_provedor):
    tela.seleciona(estados=["13"])
    itens = _unidades(tela)
    assert min(itens, key=lambda i: itens[i]["densidade"]) == TEFE  # 10 por 1.000 habitantes
    pedido = tela.diga("o município de menor densidade e o mais próximo dele com densidade de no mínimo 11 médicos por mil "
                       "habitantes")
    assert pedido.aplicado and tela.familia == "espacial"
    assert tela.consulta == {
        "base": {"partir_de": {"tipo": "selecao_previa", "regioes": [], "ufs": []}, "filtros": [],
                 "escolha": {"modo": "marcados", "municipios": [TEFE]}},
        "referencia": {"partir_de": {"tipo": "selecao_previa", "regioes": [], "ufs": []},
                       "filtros": [{"indicador": "densidade", "operador": ">=", "valor": 11}],
                       "escolha": {"modo": "todos", "municipios": []}},
        "distancia": {"medida": "geodesica", "ate": "referencia_mais_proxima"}}
    assert pedido.texto == ("Entre os 3 municípios do gráfico, em junho de 2024, o de menor densidade é TEFE (AM), com 10 por "
                            "1.000 habitantes. Abri a Análise Espacial com TEFE (AM) na base e, na referência, os municípios da "
                            "seleção (Amazonas) com densidade ≥ 11 por mil habitantes: o eixo X mostra a distância em linha "
                            "reta (km) até o mais próximo deles, sem contar o próprio município. Assim que o motor calcular, "
                            "digo qual é o mais próximo e a distância.")
    assert pedido.corpo["continuar"] == "qual a referência mais próxima?"
    # O motor calculou: a base é TEFE, e a referência mais próxima dele entre os do Amazonas com densidade ≥ 11 é PARINTINS.
    assert tela.ids_no_grafico() == [TEFE]
    item = tela.resposta["itens"][0]
    assert item["referencia_do_item"]["id"] == PARINTINS and item["referencia_do_item"]["empate"] == []
    leitura = tela.continua(pedido)
    distancia = number(item["distancia_km"])
    densidade = number(next(m for m in tela.resposta["referencia"]["membros"] if m["id"] == PARINTINS)["densidade"])
    assert leitura.texto == ("O município mais próximo de TEFE (AM) entre os municípios da seleção prévia com densidade ≥ 11 "
                             "por 1.000 habitantes, em junho de 2024, é PARINTINS (AM), a " + distancia + " km em linha reta "
                             "(densidade de " + densidade + " por 1.000 habitantes). A distância apresentada é geográfica "
                             "direta. Não representa distância viária, tempo de deslocamento ou acessibilidade real.")
    assert not set(numeros(leitura.texto)) - {distancia, densidade, "11", "1.000", "2024"}
    assert [(c["label"], c["draft"]) for c in leitura.alternativas] == [
        ("Procurar em todo o país", "procure a referência em todo o país"),
        ("Só no mesmo estado de cada um", "procure a referência no mesmo estado")]
    assert tela.historico[-1].startswith("o município de menor densidade")  # a continuação não vira mensagem da pessoa
    # A troca do recorte mantém a base e a condição; a leitura vem de novo, com a outra troca em botão.
    pais = tela.diga("procure a referência em todo o país")
    assert pais.aplicado and tela.consulta["referencia"]["partir_de"]["tipo"] == "pais"
    assert tela.consulta["base"]["escolha"]["municipios"] == [TEFE]
    assert tela.consulta["referencia"]["filtros"] == [{"indicador": "densidade", "operador": ">=", "valor": 11}]
    nova = tela.continua(pais)
    assert "entre os municípios de todo o país com densidade ≥ 11 por 1.000 habitantes" in nova.texto
    assert [c["label"] for c in nova.alternativas] == ["Só no mesmo estado de cada um"]
    assert tela.diga("qual o mais próximo?").texto == nova.texto
    # A explicação do território também diz a referência mais próxima da Escolha dos territórios (antes, ficava de fora).
    assert ("distância geográfica direta até a referência: " + number(tela.resposta["itens"][0]["distancia_km"]) +
            " km (PARINTINS (AM))") in tela.diga("como está Tefé?").texto


def test_proximidade_com_empate_no_extremo_e_estado_fora_do_grafico(tela, sem_provedor):
    tela.seleciona(ids=[MANAUS, TEFE, AMAZONAS_PA])
    empate = tela.diga("o de menor densidade e o mais próximo dele com densidade acima de 20")
    assert tela.consulta["base"]["escolha"]["municipios"] == [TEFE, AMAZONAS_PA]
    assert empate.texto.startswith("Entre os 3 municípios do gráfico, em junho de 2024, há empate na menor densidade: TEFE "
                                   "(AM), com 10 por 1.000 habitantes e AMAZONAS (PA), com 10 por 1.000 habitantes. Os dois "
                                   "entram na base. Abri a Análise Espacial com TEFE (AM) e AMAZONAS (PA) na base")
    leitura = tela.continua(empate)
    assert leitura.texto.startswith("Referência mais próxima de cada município da base, em junho de 2024, entre os "
                                    "municípios da seleção prévia com densidade > 20 por 1.000 habitantes:\n• TEFE (AM): MANAUS "
                                    "(AM), a ")
    assert "\n• AMAZONAS (PA): MANAUS (AM), a " in leitura.texto
    # O estado citado que não está no gráfico: primeiro os municípios dele; a continuação refaz o pedido no gráfico novo.
    tela.seleciona(estados=["13"], familia="distribuicao")
    estado = tela.diga("o município de menor densidade do Pará e o mais próximo dele com densidade acima de 15")
    assert estado.texto == ("Mostrei os municípios do Pará; assim que o gráfico estiver pronto, procuro o de menor densidade e "
                            "o mais próximo dele.")
    assert tela.municipios == {"todos": False, "estados": ["15"], "ids": []} and tela.familia == "distribuicao"
    refeito = tela.continua(estado)
    assert tela.consulta["base"]["escolha"]["municipios"] == [AMAZONAS_PA]
    assert tela.consulta["referencia"]["partir_de"] == {"tipo": "ufs", "regioes": [], "ufs": ["15"]}
    leitura = tela.continua(refeito)
    assert "é BELEM (PA), a " in leitura.texto


def test_proximidade_pelo_nome_com_o_grafico_calculado(tela, sem_provedor):
    tela.seleciona(estados=["13"])
    pedido = tela.diga("qual o município mais próximo de Manaus com densidade acima de 11?")
    assert pedido.aplicado and pedido.corpo["dialogo"]["ato"] == "proximidade"
    assert tela.consulta["base"]["escolha"] == {"modo": "marcados", "municipios": [MANAUS]}
    assert tela.consulta["referencia"]["filtros"] == [{"indicador": "densidade", "operador": ">", "valor": 11}]
    leitura = tela.continua(pedido)
    assert leitura.texto.startswith("O município mais próximo de MANAUS (AM) entre os municípios da seleção prévia com "
                                    "densidade > 11 por 1.000 habitantes, em junho de 2024, é PARINTINS (AM), a ")


def test_proximidade_sem_a_analise_espacial_na_base_diz_o_motivo():
    """Sem a Análise Espacial na base (aqui, sem o referencial geodésico), a conversa diz o motivo que o motor informou no
    resultado em exibição, sem prometer a análise nem mudar o gráfico (28/10/2026)."""
    motivo = ("A distância do painel precisa do referencial geodésico SIRGAS 2000, premissa governada da versão oficial da "
              "base Brasil; nesta versão da base ele não está estabelecido, e nenhum referencial é presumido.")
    body = {"nivel": "municipios", "indicador": "densidade", "competencia": "202406", "referencia": None,
            "disponibilidade": {"espacial": {"disponivel": False, "motivo": motivo, "pendencia": None}},
            "itens": [{"id": "code:1", "tipo": "municipio", "rotulo": "ALFA (AM)", "densidade": 0.5},
                      {"id": "code:2", "tipo": "municipio", "rotulo": "BETA (AM)", "densidade": 2.5}]}

    def interpretar(*_args, **_kwargs):
        raise AssertionError("sem a Análise Espacial, nada vai à gramática")
    esperado = "A Análise Espacial não está disponível nesta base: " + motivo[:-1] + ". Nada mudou no gráfico."
    for mensagem, ato in (("o de menor densidade e o mais próximo dele com densidade acima de 1", {"ato": "proximidade"}),
                          ("o mais próximo de Alfa com densidade acima de 1", {"ato": "proximidade", "extremo": False})):
        amb = dialogo.Ambiente(mensagem, {}, {}, body, None, {"tipo": "brasil"}, interpretar, None, {})
        resposta = dialogo._proximidade(ato, amb)
        assert resposta["reply"] == esperado and "painel" not in resposta, mensagem
    leitura = dialogo._referencia_proxima({"ato": "referencia_proxima"}, dialogo.Ambiente(
        "qual o mais próximo?", {}, {}, body, None, {"tipo": "brasil"}, None, None, {}))
    assert leitura["reply"] == esperado


def test_proximidade_mostra_as_casas_que_separam_o_extremo_do_vizinho():
    """O valor do extremo leva as casas que o separam do seguinte na ordem do motor (RQ-REP-05): na base versionada,
    0,367 e 0,375 por 1.000 habitantes no Tocantins apareciam os dois como "0,37"."""
    def unidade(codigo, rotulo, densidade):
        return {"id": "code:" + codigo, "tipo": "municipio", "rotulo": rotulo, "densidade": densidade, "populacao": 1000,
                "quantidade": 1}
    body = {"nivel": "municipios", "indicador": "densidade", "competencia": "202406",
            "itens": [unidade("1", "ALFA (TO)", 0.36683785766691124), unidade("2", "BETA (TO)", 0.3748125937031484),
                      unidade("3", "GAMA (TO)", 1.2)]}
    pedidos = []

    def interpretar(texto, dica=None, dica_indicador=None, base_marcada=None):
        pedidos.append(base_marcada)
        return {"handled": True, "painel": {"consulta": {"base": {}, "referencia": {}}}, "reply": "Abri a Análise Espacial."}
    amb = dialogo.Ambiente("o de menor densidade e o mais próximo dele com densidade acima de 1", {}, {}, body, None,
                           {"tipo": "brasil"}, interpretar, None, {})
    resposta = dialogo._proximidade({"ato": "proximidade"}, amb)
    assert pedidos == [["code:1"]]
    assert resposta["reply"] == ("Entre os 3 municípios do gráfico, em junho de 2024, o de menor densidade é ALFA (TO), com "
                                 "0,367 por 1.000 habitantes. Abri a Análise Espacial.")


# Correção de 29/10/2026 (revisão dos commits de 28/10): com "o mais próximo" e uma condição, os limites, a explicação, o
# estado da tela e incluir viravam pedido de proximidade e abriam a Escolha dos territórios; cada um volta à sua resposta.
@pytest.mark.parametrize("mensagem,ato", [
    ("o mais próximo com densidade acima de 20 é suficiente?", {"ato": "limite", "tipo": "normativo"}),
    ("qual a distância de carro até o mais próximo com pelo menos 20 médicos por mil habitantes?",
     {"ato": "limite", "tipo": "acesso"}),
    ("de onde vem a distância até o mais próximo com mais de 900 habitantes?", {"ato": "limite", "tipo": "procedencia"}),
    ("como é calculada a distância até o mais próximo com densidade acima de 5?",
     {"ato": "explica", "topico": "conceito", "termos": ["densidade", "distancia"], "registro": "objetivo"}),
    ("por que o mais próximo com densidade acima de 20 não aparece?", {"ato": "estado", "assunto": "ausente"}),
    ("inclua o mais próximo com densidade acima de 2", {"ato": "inclui", "condicional": True})])
def test_perguntas_governadas_com_o_mais_proximo_e_uma_condicao_nao_viram_proximidade(mensagem, ato):
    assert dialogo.reconhecer(mensagem, {}, True, resultado_consulta=True) == ato


def test_quantos_mais_proximos_e_a_ordenacao_e_o_para_sem_acento_e_a_preposicao():
    # "Os 3 mais próximos de Tefé" é a ordenação pela distância até Tefé, não a leitura da referência de cada um.
    assert dialogo.reconhecer("quais os 3 mais próximos de Tefé?", {}, True, nomes_no_resultado=["TEFE (AM)"],
                              resultado_consulta=True) is None
    assert dialogo.reconhecer("qual o mais próximo de Tefé?", {}, True, nomes_no_resultado=["TEFE (AM)"],
                              resultado_consulta=True) == {"ato": "referencia_proxima"}
    # Sem acento, "para" é a preposição; o Pará, com o acento ou depois de "do" ou "no".
    for mensagem, codigo in (("o de menor densidade do Pará", "15"), ("o de menor densidade do Para", "15"),
                             ("para o município de menor densidade, qual o mais próximo com densidade acima de 5?", None),
                             ("compare o de maior e o de menor densidade para mim", None)):
        assert dialogo._estado_citado(mensagem, dialogo.dobra(mensagem)) == codigo, mensagem
    # A referência escolhida pelo nome não depende de onde se procura: sem as trocas do recorte em botões.
    itens = [{"id": TEFE, "tipo": "municipio", "grupo_territorial": "13"}]
    pelo_nome = {"itens": itens, "referencia": {"tipo": "consulta", "consulta": {"referencia": {
        "partir_de": {"tipo": "selecao_previa", "regioes": [], "ufs": []},
        "escolha": {"modo": "marcados", "municipios": [MANAUS]}}}}}
    assert dialogo._trocas_do_recorte(pelo_nome, True) == []
    por_criterio = {"itens": itens, "referencia": {"tipo": "consulta", "consulta": {"referencia": {
        "partir_de": {"tipo": "selecao_previa", "regioes": [], "ufs": []}, "escolha": {"modo": "todos", "municipios": []}}}}}
    assert [troca["label"] for troca in dialogo._trocas_do_recorte(por_criterio, True)] == [
        "Procurar em todo o país", "Só no mesmo estado de cada um"]


def test_referencia_pelo_nome_em_exibicao_segue_a_comparacao_das_distancias(tela, sem_provedor):
    """Correção de 29/10/2026: com a referência escolhida pelo nome (a tela leva "use Manaus como referência" à Escolha dos
    territórios, painelModel.consultaComReferenciaMarcada), "qual o mais próximo?" lia a referência mais próxima de cada um,
    que é sempre ela, e oferecia trocas do recorte que a deixariam vazia; volta a ser a comparação das distâncias até ela."""
    tela.seleciona(estados=["13"])
    tela.consulta = {"base": {"partir_de": {"tipo": "selecao_previa", "regioes": [], "ufs": []}, "filtros": [],
                              "escolha": {"modo": "todos", "municipios": []}},
                     "referencia": {"partir_de": {"tipo": "pais", "regioes": [], "ufs": []}, "filtros": [],
                                    "escolha": {"modo": "marcados", "municipios": [MANAUS]}},
                     "distancia": {"medida": "geodesica", "ate": "referencia_mais_proxima"}}
    tela.familia = "espacial"
    tela.calcula()
    assert tela.resposta["referencia"]["tipo"] == "consulta"
    distancia = number(next(i for i in tela.resposta["itens"] if i["id"] == PARINTINS)["distancia_km"])
    proximo = tela.diga("qual o mais próximo?")
    assert proximo.corpo["dialogo"]["ato"] == "compara" and not proximo.alternativas
    assert proximo.texto.startswith("A menor distância até a referência em junho de 2024 é a de PARINTINS (AM), com " +
                                    distancia + " km.")
    # Quantos é a ordenação pela distância até o nome dito, como antes de 28/10/2026.
    tres = tela.diga("quais os 2 mais próximos de Tefé?")
    assert tres.corpo["painel"]["referencia"] == {"membros": [TEFE]}
    assert tres.corpo["painel"]["ordenar"] == {"atributo": "distancia_km", "ordem": "asc", "primeiros": 2}


def test_desfazer_pela_conversa_devolve_a_escolha_dos_territorios_de_antes(tela, sem_provedor):
    """Correção de 29/10/2026: o estado guardado para desfazer não levava a Escolha dos territórios, e "desfaz" depois de
    "procure a referência em todo o país" deixava a referência no país."""
    tela.seleciona(estados=["13"])
    pedido = tela.diga("o município de menor densidade e o mais próximo dele com densidade de no mínimo 11 médicos por mil "
                       "habitantes")
    tela.continua(pedido)
    assert tela.diga("procure a referência em todo o país").aplicado
    assert tela.consulta["referencia"]["partir_de"]["tipo"] == "pais"
    volta = tela.diga("desfaz")
    assert volta.aplicado and volta.texto.startswith("Desfiz a última mudança")
    assert tela.consulta["referencia"]["partir_de"]["tipo"] == "selecao_previa"
    assert tela.consulta["base"]["escolha"]["municipios"] == [TEFE]


def test_exemplos_das_orientacoes_nao_citam_lugares(tela, sem_provedor):
    """Os exemplos das orientações mostram o que a função faz, sem nomes de lugar (26/10/2026): um nome fora da análise da
    pessoa confunde."""
    tela.seleciona(ids=[MANAUS])
    textos = {mensagem: tela.diga(mensagem).texto for mensagem in ("desfaz", "qual a diferença?", "inclui mais um")}
    assert "por exemplo “os 5 municípios com maior densidade” ou “mostre a tendência”" in textos["desfaz"]
    assert textos["qual a diferença?"].endswith("Diga quais, pelo nome, ou peça, por exemplo, “compare o de maior e o de menor "
                                                "densidade”.")
    assert textos["inclui mais um"] == "Qual município você quer incluir? Diga o nome."
    for texto in textos.values():
        assert not re.search(r"Manaus|Tefé|Belém|Pará|Anápolis|Porto Alegre", texto), texto
