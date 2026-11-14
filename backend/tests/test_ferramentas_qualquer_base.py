"""Qualquer base nas ferramentas (comando V23, seção 2; Proposta V3, Parte A, seção A.3): o calendário lido da própria base
(backend/series_brasil.py), a base montada de uma planilha enviada (backend/series_da_planilha.py), o perfil da base com o
resumo "dá para / não dá para" (backend/perfil_da_base.py) e o Detector de Sinais com uma planilha (backend/detector.py e a
rota POST /api/detector, que passou a aceitar o arquivo, a aba e o mapeamento de colunas, como /api/painel).

Quatro grupos de testes:
- **calendário:** o mês âncora da série anual, os meses de registro e os tipos de intervalo, na base do Brasil (janeiro e junho),
  numa base de seis em seis meses, numa base com um registro por ano e em bases irregulares;
- **planilha:** a planilha de teste da pausa 2 (`planilha_das_ferramentas.csv`: 20 distritos fictícios, registros de seis em seis
  meses durante 10 anos, sem grupo de cima e sem população), uma planilha com código, grupo, população e coordenadas, as datas
  aceitas (AAAAMM, AAAA-MM, AAAA-MM-DD e só o ano) e as recusas;
- **Detector e perfil:** os níveis que a planilha sustenta e os motivos dos que ela não sustenta ("Indisponível nesta base",
  "eles pedem 999 comparações, e esta base chega a 360"), com os nomes dela e sem os da base do Brasil; a rota com o arquivo;
- **base versionada** (job dados-reais, ADT_REAL_DATA_DIR, somente leitura): o perfil da base do Brasil.
Nenhum valor sintético representa quantitativos reais.
"""
import hashlib
import json
import os
import re
from pathlib import Path

import numpy as np
import pandas as pd
import pytest
from fastapi.testclient import TestClient

import detector
import main
import perfil_da_base
import series_brasil
import series_da_planilha
from install_brazil_data import install

client = TestClient(main.app)
PLANILHA = Path(__file__).with_name("planilha_das_ferramentas.csv")
MAPA = {"territory": "distrito", "period": "periodo", "count": "profissionais"}
PREMISSAS = {"count_unit": "pessoas", "confirmed_roles": ["territory", "period", "count"], "object_declaration": "Enfermeiros"}
ROTULOS = {"unidade": {"singular": "distrito", "plural": "distritos"}, "todo": {"nome": "Solária", "artigo": "a"}}
DA_PLANILHA = {"premissas": PREMISSAS, "rotulos": ROTULOS}
SEM_POPULACAO = "A base não tem população: sem ela, não há taxa por habitante."
# O vocabulário da base do Brasil, que não pode aparecer nos textos de uma planilha (critério de aceitação da estrutura comum).
DO_BRASIL = re.compile(r"\bjunho\b|\bBrasil\b|\bUFs?\b|\bestados?\b|médic|municíp")


def quadro():
    return main.read_dataset(PLANILHA.read_bytes(), PLANILHA.name, "")[0]


def base_da_planilha():
    return series_da_planilha.base_da_planilha(quadro(), MAPA, DA_PLANILHA)


def tabela(linhas):
    return pd.DataFrame(linhas, columns=["distrito", "periodo", "profissionais"])


def textos(valor):
    """Os textos de uma resposta (os valores, não os nomes dos campos)."""
    if isinstance(valor, str):
        yield valor
    elif isinstance(valor, dict):
        for item in valor.values():
            yield from textos(item)
    elif isinstance(valor, (list, tuple)):
        for item in valor:
            yield from textos(item)


# --------------------------------------------------------------------------------------------- calendário
def test_calendario_lido_da_base_ancora_meses_de_registro_e_tipos_de_intervalo():
    def lido(periodos):
        tipo, tipos = series_brasil.tipos_de_intervalo([series_brasil.mes_da_competencia(p) for p in periodos])
        return series_brasil.mes_ancora(tuple(periodos)), series_brasil.meses_de_registro(tuple(periodos)), tipos, tipo.tolist()
    # A base do Brasil: janeiro e junho de 2014 a 2024. A série anual é a de junho; 5 e 7 meses são dois tipos de intervalo.
    ancora, meses, tipos, tipo = lido([str(ano) + mes for ano in range(2014, 2025) for mes in ("01", "06")])
    assert (ancora, meses, tipos) == ("06", ("01", "06"), ((5.0, 5.0), (7.0, 7.0))) and tipo[:5] == [-1, 0, 1, 0, 1]
    # De seis em seis meses (janeiro e julho): um tipo só; a âncora é o mês do último registro.
    ancora, meses, tipos, tipo = lido([str(ano) + mes for ano in range(2014, 2024) for mes in ("01", "07")])
    assert (ancora, meses, tipos) == ("07", ("01", "07"), ((6.0, 6.0),)) and set(tipo[1:]) == {0}
    # Um registro por ano ("AAAA00"): a âncora é o próprio ano.
    assert lido([str(ano) + "00" for ano in range(2014, 2024)])[:3] == ("00", ("00",), ((12.0, 12.0),))
    # A base começa em junho e termina em janeiro: junho falta no último ano, e vale janeiro, o mês do último registro.
    assert lido(["201406", "201501", "201506", "201601", "201606", "201701"])[:2] == ("01", ("01", "06"))
    # Durações parecidas (até 1 mês da menor do grupo) ficam juntas: 5 e 6 meses num tipo, 7 em outro, 12 em outro.
    ancora, meses, tipos, tipo = lido(["201401", "201406", "201412", "201507", "201607"])
    assert (ancora, meses, tipos, tipo) == ("07", ("07",), ((5.0, 6.0), (7.0, 7.0), (12.0, 12.0)), [-1, 0, 0, 1, 2])
    # Nenhum mês se repete em todos os anos: a base não tem série anual. Um registro só não tem intervalo.
    assert lido(["201401", "201505", "201609", "201802"])[:3] == (None, (), ((16.0, 17.0),))
    assert lido(["202001"]) == (None, (), (), [-1])


# --------------------------------------------------------------------------------------------- a base de uma planilha
def test_planilha_de_teste_vira_a_mesma_estrutura_da_base_do_brasil():
    b = base_da_planilha()
    assert (b.origem, b.do_brasil, b.ancora, b.prefixo_do_id) == ("planilha", False, "07", "name:")
    assert len(b.periodos) == 20 and (b.periodos[0], b.periodos[1], b.periodos[-1]) == ("201401", "201407", "202307")
    assert np.diff(b.meses).tolist() == [6] * 19
    assert len(b.codigos) == 20 and b.codigos[:2] == b.nomes[:2] == ("Distrito 01", "Distrito 02")
    assert b.quantidade.shape == (20, 20) and b.quantidade[0][:4].tolist() == [17.0, 17.0, 15.0, 16.0]
    # O todo é a soma das unidades com registro em cada data ("a base toda"), com o nome que a pessoa deu.
    assert (b.brasil[0], b.brasil[1], b.brasil[-1]) == (664.0, 671.0, 741.0) and b.brasil[0] == b.quantidade[:, 0].sum()
    # Sem população, sem coordenadas e sem grupo de cima: nada é inventado.
    assert np.isnan(b.populacao).all() and np.isnan(b.latitude).all() and b.do_estado == {} and b.estados == {} and set(b.prefixos) == {""}
    assert series_brasil.rotulos(b) == {
        "profissional": "profissional", "profissionais": "profissionais", "unidade": "distrito", "unidades": "distritos", "grupo": "grupo",
        "grupos": "grupos", "todo": "Solária", "o_unidade": "o distrito", "os_unidades": "os distritos", "o_grupo": "o grupo",
        "os_grupos": "os grupos", "dos_grupos": "dos grupos", "do_todo": "da Solária", "no_todo": "na Solária", "o_todo": "a Solária"}
    assert series_brasil.rotulos_publicos(b) == {"profissional": "profissional", "profissionais": "profissionais", "unidade": "distrito",
                                                 "unidades": "distritos", "grupo": "grupo", "grupos": "grupos", "todo": "Solária"}
    assert b.contagens == {
        "municipio": "pessoas registradas em cada distrito (quem aparece em mais de um conta em cada um)",
        "conjunto": "soma das contagens dos componentes (não é o número de pessoas diferentes do conjunto)",
        "brasil": "soma das contagens de todos os distritos com registro na data"}
    descricao = dict(b.descricao)
    assert descricao.pop("periodos_da_planilha")["202307"] == "202307"
    assert descricao == {"base": "planilha enviada", "categoria": "Enfermeiros", "tem_populacao": False, "tem_coordenadas": False,
                         "tem_grupo": False}
    assert b.avisos == () and b.versao.startswith("planilha:")
    # A base é montada uma vez por conteúdo, mapeamento e opções; outros nomes são outra base.
    assert base_da_planilha() is b
    outra = series_da_planilha.base_da_planilha(quadro(), MAPA, {"premissas": PREMISSAS})
    assert outra is not b and outra.versao != b.versao and series_brasil.rotulos(outra)["o_todo"] == "a base toda"
    # A seleção: o mesmo contrato da base do Brasil, com os identificadores da planilha.
    escolhidos = series_brasil.selecao(b, {"base": {"municipios": {"ids": ["name:Distrito 02"]}},
                                           "conjuntos": [{"id": "c1", "rotulo": "Par", "membros": ["name:Distrito 01", "name:Distrito 03"]}]})
    assert [(t.id, t.tipo, t.rotulo, t.uf) for t in escolhidos] == [("name:Distrito 02", "municipio", "Distrito 02", None),
                                                                    ("c1", "conjunto", "Par", None)]
    assert escolhidos[1].serie[0] == b.quantidade[0, 0] + b.quantidade[2, 0] and escolhidos[1].unidade == b.contagens["conjunto"]
    with pytest.raises(ValueError, match="Território fora da base: code:1."):
        series_brasil.selecao(b, {"base": {"municipios": {"ids": ["code:1"]}}})
    with pytest.raises(ValueError, match="Grupo sem registro na base: x."):
        series_brasil.selecao(b, {"estados_unidade": ["x"]})


def _com_tudo():
    """Seis áreas em duas zonas, de seis em seis meses de 2019 a 2024, com código, população e coordenadas (valores fictícios)."""
    linhas = []
    for g, zona in enumerate(("Norte", "Sul")):
        for u in range(3):
            for k, (ano, mes) in enumerate((ano, mes) for ano in range(2019, 2025) for mes in (1, 7)):
                linhas.append({"area": f"Área {g}{u}", "cod": f"A{g}{u}", "zona": zona, "quando": f"{ano}-{mes:02d}", "postos": 30 + 5 * g + u + (k % 3),
                               "hab": 10000 + 100 * k, "lat": -10.0 - g - 0.1 * u, "lon": -50.0 - 0.2 * u})
    mapa = {"territory": "area", "territory_id": "cod", "grupo_territorial": "zona", "period": "quando", "count": "postos", "population": "hab",
            "latitude": "lat", "longitude": "lon"}
    opcoes = {"premissas": {"count_unit": "postos", "crs": "SIRGAS 2000", "object_declaration": "Postos de enfermagem",
                            "confirmed_roles": ["territory", "territory_id", "period", "count", "population", "latitude", "longitude"]},
              "rotulos": {"unidade": {"singular": "área", "plural": "áreas", "genero": "f"}, "grupo": {"singular": "zona", "plural": "zonas", "genero": "f"}}}
    return pd.DataFrame(linhas), mapa, opcoes


def test_planilha_com_codigo_grupo_populacao_e_coordenadas():
    b = series_da_planilha.base_da_planilha(*_com_tudo())
    assert (b.periodos[0], b.periodos[1], b.periodos[-1], b.ancora, b.prefixo_do_id) == ("201901", "201907", "202407", "07", "code:")
    assert b.codigos[:2] == ("A00", "A01") and b.nomes[:2] == ("Área 00", "Área 01")
    # O grupo de cima é o valor da coluna escolhida; a planilha não tem contagem própria do grupo.
    assert b.do_estado == {"Norte": (0, 1, 2), "Sul": (3, 4, 5)} and b.grupos == {"Norte": ("Norte", "Norte"), "Sul": ("Sul", "Sul")}
    assert b.estados == {} and series_brasil.nome_do_grupo(b, "Sul") == ("Sul", "Sul")
    assert b.populacao[0][:2].tolist() == [10000.0, 10100.0] and (b.latitude[0][0], b.longitude[1][0]) == (-10.0, -50.2)
    # A concordância vem dos nomes do painel "Colunas" (área e zona são femininos); sem o nome do todo, "a base toda".
    r = series_brasil.rotulos(b)
    assert (r["profissional"], r["profissionais"], r["o_unidade"], r["os_unidades"], r["o_grupo"], r["dos_grupos"]) == (
        "posto", "postos", "a área", "as áreas", "a zona", "das zonas")
    assert (r["todo"], r["o_todo"], r["do_todo"], r["no_todo"]) == ("a base toda", "a base toda", "de toda a base", "em toda a base")
    assert b.contagens["municipio"] == "postos registrados em cada área"
    assert b.avisos == ({"codigo": "DUPLA_CONTAGEM",
                         "texto": "A contagem é de postos, não de pessoas: uma pessoa com mais de um conta mais de uma vez."},)
    assert {chave: b.descricao[chave] for chave in ("categoria", "tem_populacao", "tem_coordenadas", "tem_grupo")} == {
        "categoria": "Postos de enfermagem", "tem_populacao": True, "tem_coordenadas": True, "tem_grupo": True}
    # Com tudo isso, nenhum sinal fica indisponível, e a população é comparável na base inteira.
    lista = detector.compute(None, {"base": {"municipios": {"todos": True}}}, base=b)
    assert lista["indisponiveis"] == {} and lista["fonte"]["tem"] == {"populacao": True, "coordenadas": True, "grupo": True, "serie_anual": True}
    assert (lista["comparacao"]["estado"], lista["comparacao"]["trechos"]) == ("comparavel", [[2019, 2024]])
    assert lista["fonte"]["formas"]["o_unidade"] == "a área" and lista["fonte"]["rotulos"]["grupos"] == "zonas"
    # O grupo de cima não entra como unidade: a planilha não tem a contagem dele.
    with pytest.raises(ValueError, match="Esta base não tem uma contagem própria da zona: a zona não entra como unidade. Use um conjunto "
                                         "com as áreas desse grupo."):
        detector.compute(None, {"estados_unidade": ["Norte"]}, base=b)


def test_datas_aceitas_e_recusas_da_planilha():
    opcoes = {"premissas": PREMISSAS}

    def montar(linhas, mapa=MAPA, da_base=opcoes):
        return series_da_planilha.base_da_planilha(tabela(linhas), mapa, da_base)
    # AAAA-MM-DD, AAAA-MM e AAAAMM viram "AAAAMM"; os registros ficam na ordem do tempo, e o registro ausente não é zero.
    datas = montar([["A", "2020-07-01", 4], ["A", "2020-01-15", 3], ["B", "2020-07-01", 6], ["B", "2020-01-15", 5]])
    assert datas.periodos == ("202001", "202007") and datas.quantidade.tolist() == [[3.0, 4.0], [5.0, 6.0]] and datas.ancora is None
    meses = montar([["A", "2020-01", 3], ["A", "2020-07", 4], ["B", "2020-01", 5]])
    assert meses.periodos == ("202001", "202007") and meses.quantidade[0].tolist() == [3.0, 4.0]
    assert meses.quantidade[1][0] == 5.0 and np.isnan(meses.quantidade[1][1])
    # Só o ano: um registro por ano ("AAAA00"), com 12 meses entre eles.
    anos = montar([["A", "2020", 3], ["A", "2021", 4], ["B", "2020", 5], ["B", "2021", 5]])
    assert anos.periodos == ("202000", "202100") and anos.ancora == "00" and np.diff(anos.meses).tolist() == [12]
    # Vínculos e postos: o nome da contagem e o aviso de dupla contagem.
    vinculos = montar([["A", "202001", 3], ["A", "202007", 4]], da_base={"premissas": {**PREMISSAS, "count_unit": "vinculos"}})
    assert series_brasil.rotulos(vinculos)["profissionais"] == "vínculos" and vinculos.avisos[0]["codigo"] == "DUPLA_CONTAGEM"
    # Recusas, em português, com o que fazer.
    for linhas, trecho in (
            ([["A", "primeiro", 3], ["A", "segundo", 4]], "não traz datas que o Agente reconheça: use AAAAMM, AAAA-MM, AAAA-MM-DD ou o ano."),
            ([["A", "1", 3], ["A", "2", 4]], "As ferramentas precisam de datas"),
            ([["A", "2020-01-05", 3], ["A", "2020-01-20", 4], ["A", "2020-07-01", 4]], "mais de um registro no mesmo mês"),
            ([["A", "202001", 3], ["B", "202001", 4]], "A planilha tem um registro só no tempo"),
            ([["A", "202001", 3.5], ["A", "202007", 4]], "devem ser inteiras"),
            ([["A", "202001", -1], ["A", "202007", 4]], "valores negativos")):
        with pytest.raises(ValueError, match=trecho):
            montar(linhas)
    with pytest.raises(ValueError, match="Escolha a coluna territorial"):
        montar([["A", "202001", 3], ["A", "202007", 4]], mapa={})
    with pytest.raises(ValueError, match='Envie a planilha e o mapeamento de colunas escolhido no painel "Colunas".'):
        series_da_planilha.base_da_planilha(None, MAPA, {})


# --------------------------------------------------------------------------------------------- Detector e perfil
def test_detector_na_planilha_mostra_o_que_ela_sustenta_e_os_motivos_do_que_nao_sustenta():
    b = base_da_planilha()
    lista = detector.compute(None, {"base": {"municipios": {"todos": True}}}, base=b)
    assert lista["versao"] == detector.VERSION and lista["janela"]["fim"] == "202307" and lista["calibracao"]["intervalo_meses"] == 6
    fonte = dict(lista["fonte"])
    assert fonte.pop("versao") == b.versao
    assert fonte == {
        "base": "planilha enviada", "categoria": "Enfermeiros", "primeira": "201401", "ultima": "202307", "competencias": 20,
        "rotulos": series_brasil.rotulos_publicos(b), "origem": "planilha", "ancora": "07",
        "formas": {"o_unidade": "o distrito", "os_unidades": "os distritos", "o_grupo": "o grupo", "os_grupos": "os grupos",
                   "dos_grupos": "dos grupos", "do_todo": "da Solária", "no_todo": "na Solária", "o_todo": "a Solária"},
        "tem": {"populacao": False, "coordenadas": False, "grupo": False, "serie_anual": True},
        "unidades": {"municipio": b.contagens["municipio"], "conjunto": b.contagens["conjunto"]}}
    # Os níveis que a base sustenta: moderado e elevado; o crítico pede 999 comparações, e a base chega a 360.
    assert lista["resumo"]["niveis"] == {"critico": 0, "elevado": 1, "moderado": 4, "sem_alerta": 15, "sem_comparacoes": 0, "sem_nivel": 0}
    assert {chave: quantos for chave, quantos in lista["resumo"]["com_nivel"].items() if quantos} == {"declinio": 2, "perda": 2, "patamar": 2}
    assert [(linha["id"], linha["alerta"]["nivel"], linha["alerta"]["sinal"], linha["alerta"]["criterio"], linha["alerta"]["por_que"])
            for linha in lista["linhas"] if linha["alerta"]["nivel"]] == [
        ("name:Distrito 02", "moderado", "perda", "comparado com a base", "Caiu de 38 para 32 (−15,8%) (+1 sinal)"),
        ("name:Distrito 03", "moderado", "patamar", "por convenção", "18% abaixo do que já teve (patamar de 58)"),
        ("name:Distrito 11", "moderado", "declinio", "por convenção", "2 quedas anuais seguidas: −11,1% desde jul/2021"),
        ("name:Distrito 13", "elevado", "declinio", "por convenção", "3 quedas anuais seguidas: −20,8% desde jul/2020"),
        ("name:Distrito 16", "moderado", "perda", "comparado com a base", "Caiu de 15 para 13 (−13,3%)")]
    regua = [(celula["porte"], celula["comparacoes"], celula["moderado"]["queda_pct"] is not None, celula["elevado"]["queda_pct"] is not None,
              celula["critico"]["queda_pct"] is not None) for celula in lista["calibracao"]["perda"] if celula["comparacoes"]]
    assert regua == [("10 a 19", 80, True, False, False), ("20 a 49", 182, True, True, False), ("50 a 99", 98, True, False, False)]
    # O que a base não tem: os sinais por habitante e a distância ficam indisponíveis, com o motivo; nada é inventado.
    assert lista["indisponiveis"] == {chave: SEM_POPULACAO for chave in ("disponibilidade", "posicao", "defasagem", "contexto")}
    assert (lista["comparacao"]["estado"], lista["comparacao"]["motivo"], lista["comparacao"]["trechos"]) == ("indisponivel", SEM_POPULACAO, [])
    assert lista["coordenadas"] == {} and "calibracao_dos_estados" not in lista
    assert lista["entenda"]["ferramenta"]["exemplo"] == ("Uma queda de 18 para 11 profissionais é rara quando, entre as mudanças anteriores de "
                                                       "distritos de 10 a 19 profissionais, só 1 em cada 100 foi igual ou pior: alerta elevado.")
    assert lista["notas"][0] == "O registro mais recente da base é jul/2023: os sinais descrevem a situação até essa data, não a de hoje."
    # O detalhe de um território: os sinais 8 a 11 dizem "Indisponível nesta base", com o motivo, e não "não calculável".
    detalhe = detector.compute(None, {"base": {"municipios": {"todos": True}}, "detalhe": "name:Distrito 13"}, base=b)
    assert detalhe["territorio"]["rotulo"] == "Distrito 13" and detalhe["territorio"]["unidade"] == b.contagens["municipio"]
    assert [(item["numero"], item["nivel"], item["estado_do_nivel"]) for item in detalhe["fenomenos"]] == [
        ("1–2", None, "sem_alerta"), ("3", "elevado", "alerta"), ("4", None, "sem_alerta"), ("5", None, "sem_alerta"), ("6", None, "sem_alerta"),
        ("7", None, "sem_alerta"), ("8", None, "indisponivel"), ("9", None, "indisponivel"), ("10", None, "indisponivel"),
        ("11", None, "indisponivel"), ("12", None, "juntos")]
    do_sinal = {item["chave"]: item for item in detalhe["fenomenos"]}
    for chave in ("disponibilidade", "posicao", "defasagem", "contexto"):
        assert (do_sinal[chave]["situacao"], do_sinal[chave]["observado"], do_sinal[chave]["sem_comparacoes"]) == (
            "Indisponível nesta base", SEM_POPULACAO, None)
        assert do_sinal[chave]["habitual"] == "Não avaliado: a base não tem população: sem ela, não há taxa por habitante."
    assert do_sinal["estrutural"]["observado"] == ("Em jul/2023, o distrito tinha 19 profissionais; em jan/2023, 20. Contagem: pessoas "
                                                  "registradas em cada distrito (quem aparece em mais de um conta em cada um).")
    assert do_sinal["perda"]["sem_comparacoes"] == {"niveis": ["critico"], "nivel": "critico", "comparacoes": 360, "pede": 999,
                                                    "texto": "Sem comparações suficientes para o crítico: há 360, e ele pede 999."}
    assert do_sinal["coexistencia"]["situacao"] == "Um sinal com nível: declínio persistente (elevado)"
    assert detalhe["comparativo"]["trechos"] == [] and set(detalhe["comparativo"]["taxa"]) == {None}
    # Nenhum texto traz o vocabulário da base do Brasil (os nomes dos campos da resposta não são textos).
    for resposta in (lista, detalhe):
        achados = sorted({texto for texto in textos(resposta) if DO_BRASIL.search(texto)})
        assert not achados, achados[:3]
    # Antes de haver comparações, a queda fica "sem comparações suficientes"; os sinais por convenção continuam valendo.
    cedo = detector.compute(None, {"base": {"municipios": {"todos": True}}, "janela": {"fim": "201407"}}, base=b)
    assert cedo["resumo"]["niveis"] == {"critico": 0, "elevado": 0, "moderado": 0, "sem_alerta": 17, "sem_comparacoes": 3, "sem_nivel": 0}


def test_planilha_so_com_anos_tem_as_datas_e_os_textos_sem_mes():
    linhas = PLANILHA.read_text(encoding="utf-8").splitlines()
    anual = pd.DataFrame([[nome, periodo[:4], int(valor)] for nome, periodo, valor in (linha.split(";") for linha in linhas[1:])
                          if periodo.endswith("07")], columns=["distrito", "ano", "profissionais"])
    b = series_da_planilha.base_da_planilha(anual, {"territory": "distrito", "period": "ano", "count": "profissionais"}, {"premissas": PREMISSAS})
    assert (b.periodos[0], b.periodos[-1], b.ancora, len(b.periodos)) == ("201400", "202300", "00", 10) and np.diff(b.meses).tolist() == [12] * 9
    lista = detector.compute(None, {"base": {"municipios": {"todos": True}}}, base=b)
    assert lista["janela"] == {"inicio": "201400", "fim": "202300", "registros": 10, "meses": 108, "padrao": True,
                               "ultimo_registro_da_base": "202300", "e_o_ultimo": True}
    assert lista["notas"][0] == "O registro mais recente da base é 2023: os sinais descrevem a situação até essa data, não a de hoje."
    assert {linha["id"]: linha["alerta"]["por_que"] for linha in lista["linhas"] if linha["alerta"]["sinal"] == "declinio"} == {
        "name:Distrito 11": "2 quedas anuais seguidas: −11,1% desde 2021", "name:Distrito 13": "3 quedas anuais seguidas: −20,8% desde 2020"}
    detalhe = detector.compute(None, {"base": {"municipios": {"todos": True}}, "detalhe": "name:Distrito 02"}, base=b)
    do_sinal = {item["chave"]: item for item in detalhe["fenomenos"]}
    assert do_sinal["estrutural"]["observado"].startswith("Em 2023, a unidade tinha 32 profissionais; em 2022, 40.")
    assert "na série anual (de um ano para o outro)" in do_sinal["declinio"]["criterio"]
    assert do_sinal["declinio"]["entenda"]["texto"].startswith("Olha o registro de cada ano e conta quantos anos seguidos o número caiu.")
    assert "nos 4 registros anuais até o último" in do_sinal["desaceleracao"]["criterio"]
    assert do_sinal["desaceleracao"]["observado"].startswith("De 2020 a 2023, os valores anuais foram 41 → 39 → 40 → 32.")
    assert do_sinal["perda"]["observado"] == "De 2022 a 2023 (12 meses), passou de 40 para 32 profissionais (−8, −20,0%)."
    # Nenhuma data vira mês: "202300" é 2023, nunca "dez/2023".
    meses = re.compile(r"\b(?:jan|fev|mar|abr|mai|jun|jul|ago|set|out|nov|dez)/\d{4}|janeiro|fevereiro|março|abril|junho|julho|agosto|setembro|"
                       r"outubro|novembro|dezembro")
    perfil = perfil_da_base.perfil(b)
    assert not [texto for resposta in (lista, detalhe, perfil) for texto in textos(resposta) if meses.search(texto)]
    assert perfil["itens"][0]["lido"] == ("10 registros, de 2014 a 2023, com 12 meses entre eles. Só se comparam mudanças com o mesmo tempo "
                                          "entre registros.")
    assert perfil["itens"][1]["lido"] == "A base tem um registro por ano (10 anos, de 2014 a 2023)."
    assert perfil["da_para"] == ["Alertas moderados desde 2016 (o 3º ano da base).", "Alertas elevados desde 2020 (o 7º ano da base).",
                                 "Sinais anuais (declínio persistente e desaceleração), pela série de cada ano."]
    assert perfil["nao_da_para"][0] == {"o_que": "Alertas críticos", "motivo": "eles pedem 999 comparações, e esta base chega a 160."}


def test_perfil_da_planilha_de_teste_da_para_e_nao_da_para():
    perfil = perfil_da_base.perfil(base_da_planilha())
    assert {chave: perfil[chave] for chave in ("versao", "origem", "base", "categoria", "territorios", "registros", "primeira", "ultima", "ancora")} == {
        "versao": "PERFIL-DA-BASE/1", "origem": "planilha", "base": "planilha enviada", "categoria": "Enfermeiros", "territorios": 20,
        "registros": 20, "primeira": "201401", "ultima": "202307", "ancora": "07"}
    assert perfil["tem"] == {"populacao": False, "coordenadas": False, "grupo": False, "serie_anual": True} and perfil["avisos"] == []
    assert [(item["chave"], item["titulo"], item["lido"], item["falta"]) for item in perfil["itens"]] == [
        ("datas", "Datas e intervalos", "20 registros, de jan/2014 a jul/2023, com 6 meses entre eles. Só se comparam mudanças com o mesmo "
         "tempo entre registros.", None),
        ("serie_anual", "Série anual", "Usa os registros de julho, o mês presente em todos os anos (10 anos, de 2014 a 2023).", None),
        ("portes", "Portes", "20 distritos, em 3 faixas de porte pelo número de profissionais (2 de 10 a 19, 13 de 20 a 49 e 5 de 50 a 99). "
         "Quando faltam casos numa faixa, ela se junta às vizinhas.", None),
        ("grupo", "Grupo de cima", "A base não tem coluna de grupo.", "O Simulador usa o crescimento da base toda; o sinal 10 fica indisponível."),
        ("populacao", "População", "A base não tem coluna de população.",
         "Ficam indisponíveis os sinais 8 a 11 e as comparações por habitante do Simulador."),
        ("coordenadas", "Coordenadas", "A base não tem coordenadas com o referencial informado.", "O sinal 11 (distância) fica indisponível."),
        ("contagem", "O que a contagem conta", "Pessoas registradas em cada distrito (quem aparece em mais de um conta em cada um).", None),
        ("nomes", "Nomes", "A contagem é de profissionais; os territórios são os distritos; o todo, a Solária.", None)]
    # O resumo, como no exemplo da seção A.3 da Proposta V3: o que a base sustenta e, do que não sustenta, o motivo com os números.
    assert perfil["da_para"] == ["Alertas moderados desde jan/2015 (o 2º ano da base).", "Alertas elevados desde jan/2018 (o 5º ano da base).",
                                 "Sinais anuais (declínio persistente e desaceleração), pela série de julho."]
    assert perfil["nao_da_para"] == [
        {"o_que": "Alertas críticos", "motivo": "eles pedem 999 comparações, e esta base chega a 360."},
        {"o_que": "\"Mais longe da referência\" (sinal 10) e o crescimento do grupo no Simulador",
         "motivo": "a base não tem grupo de cima; o Simulador usa o crescimento da base toda."},
        {"o_que": "Sinais por habitante (8 a 11) e comparações por habitante no Simulador", "motivo": "a base não tem população."}]
    assert perfil["regua"] == {
        "moderado": {"desde": "201501", "pede": 19, "chega_a": 360, "sem_comparacoes_no_ultimo": 0, "com_registro_no_ultimo": 20},
        "elevado": {"desde": "201801", "pede": 99, "chega_a": 360, "sem_comparacoes_no_ultimo": 0, "com_registro_no_ultimo": 20},
        "critico": {"desde": None, "pede": 999, "chega_a": 360, "sem_comparacoes_no_ultimo": 20, "com_registro_no_ultimo": 20}}
    assert "regua_dos_estados" not in perfil and not [texto for texto in textos(perfil) if DO_BRASIL.search(texto)]


# --------------------------------------------------------------------------------------------- rota com a planilha
def pedir(opcoes, mapa=MAPA, **dados):
    return client.post("/api/detector", data={"mapping": json.dumps(mapa), "options": json.dumps(opcoes), **dados},
                       files={"file": (PLANILHA.name, PLANILHA.read_bytes(), "text/csv")})


def corpo(resposta):
    assert resposta.status_code == 200, resposta.text[:2000]
    body = resposta.json()
    json.dumps(body, allow_nan=False)
    return body


def recusa(resposta, trecho):
    assert resposta.status_code == 422, resposta.text[:500]
    assert trecho in resposta.json()["detail"], resposta.json()["detail"]


def test_rota_do_detector_aceita_a_planilha_com_o_mapeamento_das_analises(monkeypatch):
    monkeypatch.setattr(main, "llm_interpret", lambda *a, **k: (_ for _ in ()).throw(AssertionError("o Detector não usa o provedor de IA")))
    # A lista: a seleção no mesmo contrato, com os identificadores da planilha; o conjunto não tem nível.
    lista = corpo(pedir({"base": {"municipios": {"ids": ["name:Distrito 02", "name:Distrito 13"]}}, **DA_PLANILHA,
                         "conjuntos": [{"id": "c1", "rotulo": "Par", "membros": ["name:Distrito 01", "name:Distrito 02"]}]}))
    assert [(linha["id"], linha["tipo"], linha["alerta"]["estado"], linha["alerta"]["nivel"]) for linha in lista["linhas"]] == [
        ("name:Distrito 02", "municipio", "alerta", "moderado"), ("name:Distrito 13", "municipio", "alerta", "elevado"),
        ("c1", "conjunto", "sem_nivel", None)]
    assert lista["resumo"]["por_tipo"] == {"municipio": 2, "estado": 0, "conjunto": 1}
    assert (lista["fonte"]["origem"], lista["fonte"]["base"], lista["fonte"]["rotulos"]["unidades"]) == ("planilha", "planilha enviada", "distritos")
    assert lista["linhas"][2]["ids_dos_membros"] == ["name:Distrito 01", "name:Distrito 02"]
    assert lista["linhas"][2]["alerta"]["motivo"].startswith("Um conjunto não tem outros iguais para comparar")
    # As opções que descrevem a planilha (os nomes, as premissas e a categoria) não são opções do Detector: não viram recusa.
    assert "rotulos" not in lista and "premissas" not in lista
    # O detalhe e o perfil saem da mesma rota, sem endereço novo.
    detalhe = corpo(pedir({"base": {"municipios": {"todos": True}}, "detalhe": "name:Distrito 13", **DA_PLANILHA}))
    assert detalhe["territorio"]["id"] == "name:Distrito 13" and len(detalhe["serie"]) == 20
    assert detalhe["linha"]["alerta"]["por_que"] == "3 quedas anuais seguidas: −20,8% desde jul/2020"
    so_o_perfil = corpo(pedir({"perfil": True, **DA_PLANILHA}))
    assert sorted(so_o_perfil) == ["fonte", "perfil", "versao"] and so_o_perfil["perfil"]["da_para"][0] == "Alertas moderados desde jan/2015 (o 2º ano da base)."
    assert so_o_perfil["perfil"]["nao_da_para"][0]["motivo"] == "eles pedem 999 comparações, e esta base chega a 360."
    assert so_o_perfil["perfil"]["nomes"]["todo"] == "Solária"
    # Recusas, em português: o que falta na planilha ou no pedido.
    recusa(pedir({"base": {"municipios": {"todos": True}}, **DA_PLANILHA, "outra": 1}), "Opção desconhecida no pedido do Detector: outra.")
    recusa(pedir({"base": {"municipios": {"ids": ["name:Nada"]}}, **DA_PLANILHA}), "Território fora da base: name:Nada.")
    recusa(pedir({"estados_unidade": ["x"], **DA_PLANILHA}), "Grupo sem registro na base: x.")
    recusa(pedir({"base": {"municipios": {"todos": True}}, **DA_PLANILHA, "janela": {"fim": "202406"}}),
           "Competência fora da base: 202406. Escolha uma das competências com registro, de janeiro de 2014 a julho de 2023.")
    recusa(pedir({"perfil": True, **DA_PLANILHA}, dataset="brazil"), "Escolha uma base do catálogo ou importe um arquivo.")
    recusa(pedir({"perfil": True, **DA_PLANILHA}, mapa={}), "Escolha a coluna territorial")
    # Sem as premissas que o portão das análises pede, a rota devolve a mesma pendência do painel, para a tela perguntar.
    pendente = pedir({"base": {"municipios": {"todos": True}}})
    assert pendente.status_code == 422 and pendente.json()["pendencia"]["chave"] == "confirmed_roles"
    # Sem base nenhuma, a ferramenta diz o que fazer; o Simulador continua só com a base do Brasil.
    recusa(client.post("/api/detector", data={"options": "{}"}), "Escolha a base do Brasil ou envie uma planilha")
    recusa(client.post("/api/simulador", data={"options": "{}"}, files={"file": (PLANILHA.name, PLANILHA.read_bytes(), "text/csv")}),
           "O Simulador de Cenários Territoriais usa a base do Brasil")


# --------------------------------------------------------------------------------------------- base versionada
@pytest.fixture(scope="module")
def real(tmp_path_factory):
    """Base versionada instalada numa pasta temporária (job dados-reais), somente em leitura."""
    pasta = os.getenv("ADT_REAL_DATA_DIR")
    if not pasta:
        pytest.skip("Defina ADT_REAL_DATA_DIR para testar as bases locais somente em leitura")
    arquivos = [p for p in Path(pasta).iterdir() if p.suffix.lower() in (".csv", ".xlsx")]
    antes = {p: hashlib.sha256(p.read_bytes()).hexdigest() for p in arquivos}
    destino = tmp_path_factory.mktemp("perfil-real") / "brasil"
    install(Path(pasta), destino)
    with pytest.MonkeyPatch.context() as patch:
        patch.setenv("ADT_BRASIL_DATA_DIR", str(destino))
        patch.delenv("ADT_BRASIL_DATA_VERSION", raising=False)
        main._BRAZIL_FRAMES.clear()
        yield series_brasil.base_de(main._brazil_sources(""))
        main._BRAZIL_FRAMES.clear()
    assert antes == {p: hashlib.sha256(p.read_bytes()).hexdigest() for p in arquivos}


def test_real_perfil_da_base_do_brasil(real):
    assert (real.origem, real.ancora, series_brasil.meses_de_registro(real.periodos)) == ("brasil", "06", ("01", "06"))
    resposta = client.post("/api/detector", data={"dataset": "brazil", "scope": "municipal", "options": json.dumps({"perfil": True})})
    assert resposta.status_code == 200, resposta.text[:2000]
    perfil = resposta.json()["perfil"]
    assert {chave: perfil[chave] for chave in ("origem", "base", "categoria", "territorios", "registros", "primeira", "ultima", "ancora")} == {
        "origem": "brasil", "base": "Brasil", "categoria": "MEDICINA", "territorios": 5570, "registros": 22, "primeira": "201401",
        "ultima": "202406", "ancora": "06"}
    assert perfil["tem"] == {"populacao": True, "coordenadas": True, "grupo": True, "serie_anual": True} and perfil["avisos"] == []
    assert perfil["nomes"] == {"profissional": "médico", "profissionais": "médicos", "unidade": "município", "unidades": "municípios",
                               "grupo": "estado", "grupos": "estados", "todo": "Brasil"}
    assert {item["chave"]: item["lido"] for item in perfil["itens"]} == {
        "datas": "22 registros, de jan/2014 a jun/2024, com 5 ou 7 meses entre eles. Só se comparam mudanças com o mesmo tempo entre registros.",
        "serie_anual": "Usa os registros de junho, o mês presente em todos os anos (11 anos, de 2014 a 2024).",
        "portes": "5.570 municípios, em 10 faixas de porte pelo número de médicos (296 de 1 a 3, 1.238 de 4 a 9, 1.327 de 10 a 19, 1.284 de 20 a "
                  "49, 531 de 50 a 99, 500 de 100 a 299, 268 de 300 a 999, 83 de 1.000 a 2.999, 35 de 3.000 a 9.999 e 8 de 10.000 ou mais). "
                  "Quando faltam casos numa faixa, ela se junta às vizinhas.",
        "grupo": "27 estados (pelo prefixo do código IBGE).",
        "populacao": "Com população. A variação por habitante é comparável de 2014 a 2024.",
        "coordenadas": "Com coordenadas (SIRGAS 2000, do perfil oficial).",
        "contagem": "Médicos registrados no município (fonte municipal; quem atua em mais de um município conta em cada um).",
        "nomes": "A contagem é de médicos; os territórios são os municípios; o grupo de cima, os estados; o todo, o Brasil."}
    assert all(item["falta"] is None for item in perfil["itens"])
    assert perfil["da_para"] == [
        "Alertas moderados desde jun/2015 (o 2º ano da base).", "Alertas elevados desde jun/2015 (o 2º ano da base).",
        "Alertas críticos desde jun/2015 (o 2º ano da base). No último registro, 43 de 5.570 territórios ficam sem comparações suficientes "
        "neste nível (os de porte com pouca história).",
        "Sinais por habitante (8 a 10) e comparações por habitante no Simulador, de 2014 a 2024.",
        "Distância até o município mais próximo com mais médicos por habitante (sinal 11, só contexto).",
        "Alertas moderados nos estados como unidade desde jun/2015 (o 2º ano da base).",
        "Alertas elevados nos estados como unidade desde jun/2019 (o 6º ano da base).",
        "Sinais anuais (declínio persistente e desaceleração), pela série de junho."]
    assert perfil["nao_da_para"] == [{"o_que": "Alertas críticos nos estados como unidade",
                                      "motivo": "eles pedem 999 comparações, e esta base chega a 270."}]
    assert perfil["regua_dos_estados"]["elevado"]["desde"] == "201906" and perfil["regua"]["critico"]["sem_comparacoes_no_ultimo"] == 43
    # A lista da base do Brasil diz o que a base tem, e nenhum sinal fica indisponível.
    lista = client.post("/api/detector", data={"dataset": "brazil", "scope": "municipal",
                                               "options": json.dumps({"base": {"municipios": {"estados": ["42"]}}})}).json()
    assert lista["indisponiveis"] == {} and lista["fonte"]["origem"] == "brasil" and lista["fonte"]["ancora"] == "06"
    assert lista["fonte"]["tem"] == {"populacao": True, "coordenadas": True, "grupo": True, "serie_anual": True}
    assert lista["fonte"]["formas"] == {"o_unidade": "o município", "os_unidades": "os municípios", "o_grupo": "o estado", "os_grupos": "os estados",
                                        "dos_grupos": "dos estados", "do_todo": "do Brasil", "no_todo": "no Brasil", "o_todo": "o Brasil"}
