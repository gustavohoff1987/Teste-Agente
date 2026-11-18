"""Ajustes pré-publicação (comando do responsável de 18/11/2026, versão 6): o que o motor escreve para a tela.

AJ-05 — os termos na tela, sem "por convenção" e com "forma" no lugar de "jeito" (decisão do responsável de 18/11/2026: na tela, o
tipo de critério se chama "limite fixo" ou "comparado com a base"):
- o Detector escreve "limite fixo" nos textos que a tela mostra (os sete campos da explicação completa, o "Entenda" de cada sinal e
  o da primeira tela) e nunca "convenção"; o campo `criterio` (no alerta, em cada sinal com nível e em `criterio_do_nivel`) continua
  com o valor do motor, "por convenção", e as notas, que vão em "Exportar o método (JSON)", continuam iguais;
- o Simulador e o perfil da base escrevem "forma de projetar", no feminino ("a forma escolhida pela base"), e nunca "jeito"; o
  campo `entenda.jeito` da resposta continua com esse nome.
Numa base sintética (o calendário real, de janeiro e junho de 2014 a 2024), com os quatro sinais de limite fixo com nível: poucos
profissionais, nenhum registrado, declínio persistente, desaceleração e o moderado do sinal 7. Só palavras mudaram: os números, os
níveis e os campos são os de antes (os demais testes do Detector e do Simulador conferem os valores).
"""
import hashlib

import numpy as np

import detector
import series_brasil
import simulador

PERIODOS = tuple(str(ano) + mes for ano in range(2014, 2025) for mes in ("01", "06"))
T = len(PERIODOS)


def _serie(*trechos):
    """Série de 22 registros: cada trecho é (valor, quantos); o último vale até o fim."""
    valores = []
    for valor, quantos in trechos[:-1]:
        valores += [valor] * quantos
    return valores + [trechos[-1][0]] * (T - len(valores))


def _junhos(valores):
    """Os valores de junho, ano a ano, com janeiro igual a junho (dois registros por ano)."""
    return [valor for junho in valores for valor in (junho, junho)]


def _base(series: dict) -> series_brasil.Base:
    codigos = tuple(sorted(series))
    quantidade = np.array([[float(v) for v in series[codigo]] for codigo in codigos])
    prefixos = tuple(codigo[:2] for codigo in codigos)
    do_estado = {}
    for linha, prefixo in enumerate(prefixos):
        do_estado.setdefault(prefixo, []).append(linha)
    vazio = np.full(quantidade.shape, np.nan)
    return series_brasil.Base(
        versao="sintetica-aj05-" + hashlib.sha256(quantidade.tobytes()).hexdigest()[:12], periodos=PERIODOS,
        meses=np.array([series_brasil.mes_da_competencia(p) for p in PERIODOS]), codigos=codigos,
        nomes=tuple("M" + codigo for codigo in codigos), prefixos=prefixos, quantidade=quantidade, populacao=vazio,
        latitude=vazio, longitude=vazio, estados={}, brasil=np.full(T, np.nan),
        indice={codigo: linha for linha, codigo in enumerate(codigos)},
        do_estado={prefixo: tuple(linhas) for prefixo, linhas in do_estado.items()})


# Os territórios dos sinais de limite fixo, ao lado de 30 territórios parecidos (40 profissionais, sem mudança).
DECLINIO, DESACELERACAO, PATAMAR, POUCOS, ZERO = "110200", "110201", "110202", "110203", "110204"
SERIES = {**{"11" + str(1000 + i): _serie((40, T)) for i in range(30)},
          DECLINIO: [50] * 12 + _junhos([50, 45, 40, 34, 30]),          # de 2020 a 2024: 4 quedas anuais seguidas e perda de 40%: crítico
          DESACELERACAO: _junhos([10] * 7 + [22, 32, 40, 46]),           # a classe da tendência em 2 anos seguidos: moderado
          PATAMAR: _serie((40, 8), (30, 1)),                             # os 2 últimos registros 25% abaixo do patamar: moderado
          POUCOS: _serie((2, T)),                                        # 2 profissionais: elevado
          ZERO: _serie((5, 10), (0, 1))}                                 # zero confirmado: crítico
TODOS = {"base": {"municipios": {"todos": True}}}
CAMPOS_DA_TELA = ("situacao", "observado", "criterio", "habitual", "significa", "nao_significa", "limitacoes", "qualidade")


def _textos(valor):
    """Todos os textos (os valores, não as chaves) de uma resposta do motor."""
    if isinstance(valor, str):
        return [valor]
    if isinstance(valor, dict):
        return [texto for item in valor.values() for texto in _textos(item)]
    if isinstance(valor, (list, tuple)):
        return [texto for item in valor for texto in _textos(item)]
    return []


def _textos_da_tela_do_sinal(sinal: dict) -> list[str]:
    """Os textos de um sinal que a tela mostra: a frase, o "Entenda", os sete campos e o "sem comparações suficientes"."""
    textos = [sinal[campo] for campo in CAMPOS_DA_TELA] + [sinal["entenda"]["texto"], sinal["entenda"]["exemplo"]]
    return textos + ([sinal["sem_comparacoes"]["texto"]] if sinal.get("sem_comparacoes") else [])


def test_aj05_o_detector_escreve_limite_fixo_na_tela_e_o_campo_criterio_continua_por_convencao():
    b = _base(SERIES)
    lista = detector.compute(None, TODOS, base=b)
    linhas = {linha["id"]: linha for linha in lista["linhas"]}
    # Os alertas dos territórios de limite fixo: o campo `criterio` é o do motor, como antes.
    esperados = {DECLINIO: ("critico", "declinio"), DESACELERACAO: ("moderado", "desaceleracao"), PATAMAR: ("moderado", "patamar"),
                 POUCOS: ("elevado", "estrutural"), ZERO: ("critico", "ausencia")}
    for codigo, (nivel, sinal) in esperados.items():
        alerta = linhas["code:" + codigo]["alerta"]
        assert (alerta["estado"], alerta["nivel"], alerta["sinal"], alerta["criterio"]) == ("alerta", nivel, sinal, "por convenção"), alerta
        assert {"sinal": sinal, "nivel": nivel, "criterio": "por convenção"} in alerta["sinais"], alerta
        assert "convenç" not in (alerta["por_que"] or "").lower()
    assert detector.POR_CONVENCAO == "por convenção"
    # O "Entenda" da primeira tela diz "limite fixo"; as notas, que vão em "Exportar o método (JSON)", continuam com o valor do campo.
    da_tela = _textos(lista["entenda"])
    assert not [texto for texto in da_tela if "convenç" in texto.lower() or "jeito" in texto.lower()], da_tela
    assert "\"limite fixo\", o mesmo limite para todos os territórios" in lista["entenda"]["alerta"]["texto"], lista["entenda"]["alerta"]
    assert any("\"comparado com a base\" ou \"por convenção\"" in nota for nota in lista["notas"]), lista["notas"]

    def do_detalhe(codigo, chave):
        corpo = detector.compute(None, {**TODOS, "detalhe": "code:" + codigo}, base=b)
        textos = [texto for sinal in corpo["fenomenos"] for texto in _textos_da_tela_do_sinal(sinal)]
        assert not [texto for texto in textos if "convenç" in texto.lower() or "jeito" in texto.lower()], codigo
        return next(sinal for sinal in corpo["fenomenos"] if sinal["chave"] == chave)

    poucos = do_detalhe(POUCOS, "estrutural")
    assert (poucos["nivel"], poucos["criterio_do_nivel"]) == ("elevado", "por convenção")
    assert poucos["criterio"].startswith("Limite fixo, pelo número de médicos no último registro: 1 ou nenhum, crítico; até 3, elevado; "
                                         "até 5, moderado;"), poucos["criterio"]
    assert poucos["habitual"].startswith("Limite fixo: o mesmo para todos os territórios, e não uma comparação com a base. "), poucos["habitual"]
    assert poucos["entenda"]["texto"].endswith("Os limites são fixos, iguais para todos, e não uma comparação com a base."), poucos["entenda"]
    zero = do_detalhe(ZERO, "estrutural")
    assert (zero["nivel"], zero["criterio_do_nivel"]) == ("critico", "por convenção") and zero["criterio"] == poucos["criterio"]
    declinio = do_detalhe(DECLINIO, "declinio")
    assert (declinio["nivel"], declinio["criterio_do_nivel"]) == ("critico", "por convenção")
    assert declinio["criterio"].startswith("Limite fixo, pelas quedas seguidas na série anual (de junho a junho)"), declinio["criterio"]
    assert declinio["habitual"] == "Limite fixo: o mesmo para todos os territórios.", declinio["habitual"]
    ritmo = do_detalhe(DESACELERACAO, "desaceleracao")
    assert (ritmo["nivel"], ritmo["criterio_do_nivel"], ritmo["exploratorio"]) == ("moderado", "por convenção", True)
    assert ritmo["criterio"].endswith(" Moderado, por limite fixo e exploratório, quando a classe se repete em 2 anos seguidos."), ritmo["criterio"]
    assert ritmo["habitual"] == "Limite fixo e exploratório: a classe se repete há 2 anos.", ritmo["habitual"]
    patamar = do_detalhe(PATAMAR, "patamar")
    assert (patamar["nivel"], patamar["criterio_do_nivel"]) == ("moderado", "por convenção")
    assert "Moderado, por limite fixo: os 2 últimos registros 15% ou mais abaixo do patamar. Elevado: isso, e o afastamento raro" in (
        patamar["criterio"]), patamar["criterio"]
    assert patamar["habitual"].startswith("Limite fixo: os 2 últimos registros estão 15% ou mais abaixo do patamar."), patamar["habitual"]


def test_aj05_o_simulador_e_o_perfil_escrevem_forma_de_projetar_e_o_campo_entenda_jeito_continua():
    b = _base(SERIES)
    corpo = simulador.compute(None, {"base": {"municipios": {"ids": ["code:" + DECLINIO, "code:" + POUCOS, "code:" + PATAMAR]}},
                                     "cenarios": [{"metodo": "padrao"}, {"metodo": "M1"}, {"metodo": "M0"}]}, base=b)
    textos = _textos(corpo)
    assert not [texto for texto in textos if "jeito" in texto.lower() or "convenç" in texto.lower()], [
        texto for texto in textos if "jeito" in texto.lower() or "convenç" in texto.lower()]
    assert any("forma de projetar" in texto for texto in textos), "os textos do Simulador dizem \"forma de projetar\""
    calculados = [cenario for territorio in corpo["territorios"] for cenario in territorio["cenarios"] if cenario["estado"] == "calculado"]
    assert calculados and all(set(cenario["entenda"]) == {"jeito", "faixa"} for cenario in calculados), "o campo `entenda.jeito` continua"
    # O perfil da base (o "dá para" e o "não dá para" do Simulador) também diz "forma de projetar".
    perfil = detector.compute(None, {"perfil": True}, base=b)["perfil"]
    do_perfil = _textos(perfil)
    assert not [texto for texto in do_perfil if "jeito" in texto.lower() or "convenç" in texto.lower()], do_perfil
    assert any("forma de projetar" in texto for texto in do_perfil), do_perfil
