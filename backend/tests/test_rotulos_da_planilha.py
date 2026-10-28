"""Respostas da conversa com os nomes de uma planilha enviada (28/10/2026, navegação simulada com dados fictícios).

Uma planilha fictícia de comunas agrupadas em condados (nenhum nome do Brasil) vai ao motor da página única com os rótulos
da tela; as respostas verificadas da conversa (explicacao.py) usam esses nomes, com a concordância da unidade (comuna,
feminino; distrito, masculino), e não trazem o que é próprio da base do Brasil (município, estado, sede municipal). Sem
gráfico, os exemplos usam os nomes da tela; sem eles, os da base do Brasil, como antes.
"""
import json

from fastapi.testclient import TestClient

import dialogo
import explicacao
import main

client = TestClient(main.app)
COMUNAS = {"unidade": {"singular": "comuna", "plural": "comunas"}, "grupo": {"singular": "condado", "plural": "condados"}}
DISTRITOS = {"unidade": {"singular": "distrito", "plural": "distritos"},
             "grupo": {"singular": "província", "plural": "províncias"}}
BRASIL = {"unidade": {"singular": "município", "plural": "municípios"}, "grupo": {"singular": "estado", "plural": "estados"}}
# Densidades de 2024: Vesperina e Rocaclara 3 (empatadas no maior valor), Ondaflor 2, Quiralto 1 e Lumbral 0,44.
LINHAS = [("Vesperina", "Alto Vésper", 30, 10000, "-38.80", "-20.60"), ("Rocaclara", "Alto Vésper", 24, 8000, "-38.90", "-20.50"),
          ("Lumbral", "Baixo Lúmen", 4, 9000, "-39.60", "-19.40"), ("Ondaflor", "Baixo Lúmen", 20, 10000, "-39.70", "-19.50"),
          ("Quiralto", "Baixo Lúmen", 3, 3000, "-39.20", "-17.60")]
MAPEAMENTO = {"territory": "comuna", "grupo_territorial": "condado", "period": "ano", "category": "categoria",
              "count": "quantidade", "population": "populacao", "latitude": "latitude", "longitude": "longitude"}
SEM_BRASIL = ("munic", "sede municipal", " estado", "Brasil", " UF")


def planilha():
    linhas = ["comuna;condado;ano;categoria;quantidade;populacao;latitude;longitude"]
    linhas += [";".join([nome, condado, "2024", "Medicina", str(quantidade), str(populacao), lat, lon])
               for nome, condado, quantidade, populacao, lat, lon in LINHAS]
    return ("\n".join(linhas) + "\n").encode()


def resposta(rotulos, base=None):
    opcoes = {"nivel": "municipios", "indicador": "densidade", "competencia": "2024", "rotulos": rotulos,
              "premissas": {"count_unit": "pessoas", "confirmed_roles": ["territory"]},
              "base": {"municipios": base or {"todos": True}}}
    enviada = client.post("/api/painel", files={"file": ("solaria.csv", planilha())},
                          data={"mapping": json.dumps(MAPEAMENTO), "options": json.dumps(opcoes)})
    assert enviada.status_code == 200, enviada.text[:2000]
    return enviada.json()


def sem_o_brasil(texto):
    assert not [termo for termo in SEM_BRASIL if termo in texto], texto
    return texto


def test_extremos_concordam_com_a_unidade_da_planilha():
    comunas = resposta(COMUNAS)
    assert comunas["rotulos"]["unidade"] == {"singular": "comuna", "plural": "comunas", "genero": "f"}
    maior = sem_o_brasil(explicacao.comparar_atributo(comunas, "densidade", True)["texto"])
    assert maior.startswith("Empatadas com a maior densidade em 2024: Vesperina, Rocaclara") or \
        maior.startswith("Empatadas com a maior densidade em 2024: Rocaclara, Vesperina"), maior
    assert " As demais: " in maior and "Os demais" not in maior and "Empatados" not in maior, maior
    menor = sem_o_brasil(explicacao.comparar_atributo(comunas, "densidade", False)["texto"])
    assert menor.startswith("A menor densidade em 2024 é a de Lumbral") and " As demais: " in menor, menor
    iguais = resposta(COMUNAS, {"todos": False, "estados": [], "ids": ["name:Vesperina", "name:Rocaclara"]})
    assert explicacao.comparar_atributo(iguais, "densidade", True)["texto"].startswith(
        "Todas as comunas com valor têm a mesma densidade: 3 por 1.000 habitantes.")
    # Com a unidade masculina, como antes.
    distritos = resposta(DISTRITOS)
    masculino = explicacao.comparar_atributo(distritos, "densidade", True)["texto"]
    assert masculino.startswith("Empatados com a maior densidade") and " Os demais: " in masculino, masculino
    assert explicacao.comparar_atributo(resposta(DISTRITOS, {"todos": False, "estados": [], "ids": [
        "name:Vesperina", "name:Rocaclara"]}), "densidade", True)["texto"].startswith("Todos os distritos com valor têm a mesma")


def test_selecao_e_mapa_com_os_nomes_da_planilha():
    comunas = resposta(COMUNAS)
    todos = explicacao.estado(comunas, "selecao", ctx={"nivel": "municipios", "municipios": {"todos": True}})["texto"]
    assert sem_o_brasil(todos).startswith("A seleção tem todas as comunas da base."), todos
    grupo = explicacao.estado(comunas, "selecao", ctx={"nivel": "municipios", "municipios": {
        "todos": False, "estados": ["Alto Vésper"], "ids": ["name:Lumbral", "name:Ondaflor"]}})["texto"]
    assert grupo.startswith("A seleção tem as comunas de Alto Vésper e 2 comunas escolhidas uma a uma."), grupo
    mapa = explicacao.estado(comunas, "mapa", ctx={"vista": "mapa"}, fonte={"tipo": "arquivo", "nome": "solaria.csv"})["texto"]
    assert sem_o_brasil(mapa).startswith("No mapa, cada ponto é uma comuna, na coordenada informada na planilha, e a cor"), mapa
    distritos = resposta(DISTRITOS)
    assert explicacao.estado(distritos, "selecao", ctx={"nivel": "municipios", "municipios": {"todos": True}})["texto"] \
        .startswith("A seleção tem todos os distritos da base.")
    assert "cada ponto é um distrito, na coordenada informada na planilha" in explicacao.estado(
        distritos, "mapa", ctx={"vista": "mapa"}, fonte={"tipo": "arquivo"})["texto"]
    # Na base do Brasil, a sede municipal, como antes.
    assert "cada ponto é um município, na coordenada da sede municipal" in explicacao.estado(
        resposta(BRASIL), "mapa", ctx={"vista": "mapa"}, fonte={"tipo": "brasil"})["texto"]


def test_sem_grafico_os_exemplos_usam_os_nomes_da_tela():
    assert explicacao.explicar_resultado(None, rotulos=COMUNAS)["texto"].endswith(
        "me diga quais quer ver: o nome de um condado ou de comunas, ou “todas as comunas”.")
    assert explicacao.contagem(None, rotulos=DISTRITOS)["texto"].endswith(
        "me diga quais quer ver: o nome de uma província ou de distritos, ou “todos os distritos”.")
    sem_grupo = {"unidade": COMUNAS["unidade"], "grupo": None}
    assert explicacao.estado(None, "territorios", rotulos=sem_grupo)["texto"].endswith(
        "me diga quais quer ver: o nome de comunas, ou “todas as comunas”.")
    brasil = "me diga quais quer ver: o nome de um estado ou de municípios, ou “todos os estados”."
    assert explicacao.explicar_resultado(None)["texto"].endswith(brasil)
    assert explicacao.comparar_atributo(None, "densidade", rotulos=BRASIL)["texto"].endswith(brasil)


def test_exemplos_da_conversa_usam_os_nomes_da_planilha():
    comunas = resposta(COMUNAS)
    distancia = explicacao.comparar_atributo(comunas, "distancia_km", True)["texto"]
    assert "“use como referência a comuna de maior densidade”" in sem_o_brasil(distancia), distancia
    conceito = explicacao.explicar_conceito(comunas, ["aceleracao"])["texto"]
    assert "“mostre a tendência dessas comunas”" in sem_o_brasil(conceito), conceito
    normativo = explicacao.limite(comunas, "normativo", "tem médicos suficientes?")["texto"]
    assert "“mostre as comunas com densidade menor que 1”" in normativo and "munic" not in normativo, normativo
    assert "“mostre as comunas com densidade menor que 1”" in explicacao.limite(None, "normativo", rotulos=COMUNAS)["texto"]
    assert "“mostre os municípios com densidade menor que 1”" in explicacao.limite(None, "normativo")["texto"]
    distritos = resposta(DISTRITOS)
    assert "“use como referência o distrito de maior densidade”" in explicacao.comparar_atributo(distritos, "distancia_km")["texto"]
    assert "“mostre a tendência desses distritos”" in explicacao.explicar_conceito(distritos, ["aceleracao"])["texto"]


def test_respostas_da_conversa_usam_a_unidade_da_planilha():
    """Recusas e orientações do gestor de diálogo (28/10/2026): os exemplos com a unidade da planilha e a concordância; a
    re-pergunta de uma escolha não pede a sigla do estado, que os grupos de uma planilha não têm."""
    comunas = resposta(COMUNAS)

    def responde(mensagem, ato, conversa=None, body=comunas, fonte=None):
        amb = dialogo.Ambiente(mensagem, conversa or {}, {}, body, fonte=fonte or {"tipo": "arquivo", "nome": "solaria.csv"},
                               rotulos=COMUNAS)
        return dialogo.executar(ato, amb)["reply"]

    assert "por exemplo “as 5 comunas com maior densidade” ou “mostre a tendência”" in responde("desfaz", {"ato": "desfaz"})
    juizo = responde("Lumbral está crítica?", {"ato": "governanca", "tipo": "afirmar_juizo"})
    assert "“mostre as comunas com densidade menor que 1”" in juizo and "munic" not in juizo, juizo
    assert "“mostre as comunas com densidade menor que 2”" in responde(
        "crie a classe “crítico”", {"ato": "governanca", "tipo": "criar_classe"})
    assert "(por exemplo, “as 5 comunas com maior densidade”)" in responde(
        "escolha você", {"ato": "governanca", "tipo": "delegar"})
    pendente = {"pergunta": "Há 2 comunas com o nome “Vesperina”. Qual delas?", "pedido": "Compare Vesperina e Lumbral",
                "alternativas": [{"rotulo": "Vesperina [SOL-0101]", "rascunho": "Compare Vesperina [SOL-0101] e Lumbral"},
                                 {"rotulo": "Vesperina [SOL-0201]", "rascunho": "Compare Vesperina [SOL-0201] e Lumbral"}]}
    repergunta = responde("hmm, sei lá", {"ato": "repergunta"}, {"pendente": pendente})
    assert repergunta.endswith("Pode responder com o nome ou “o primeiro”, “o segundo”."), repergunta
    # Na base do Brasil (ou sem a fonte), como antes.
    assert responde("hmm, sei lá", {"ato": "repergunta"}, {"pendente": pendente}, fonte={"tipo": "brasil"}).endswith(
        "Pode responder com o nome, a sigla do estado ou “o primeiro”, “o segundo”.")
    brasil = dialogo.Ambiente("desfaz", {}, {}, None, fonte={"tipo": "brasil"}, rotulos=BRASIL)
    assert "“os 5 municípios com maior densidade”" in dialogo.executar({"ato": "desfaz"}, brasil)["reply"]
