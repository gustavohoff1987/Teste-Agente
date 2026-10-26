"""Contexto estruturado da conversa enviado ao Gemini (Frentes II e IV; Adendo PAR-20261026 da SPEC), 26/10/2026.

O cartão reúne, já verificado e montado pelo backend, o que o modelo precisa para conversar sobre a tela:
- a tela: a análise aberta (família), o nível, o indicador, a competência ou a janela, a vista, o mapa e os territórios;
- o resultado em exibição, lido da sessão com a integridade conferida (nunca valores do navegador): a frase-resumo do
  motor, os territórios com os valores formatados como na tela e as unidades, a comparação, as classes, os grupos, as
  ordens (maior e menor por atributo, contadas no motor), a referência de contexto, as notas e limitações e a
  disponibilidade de cada análise; com muitos territórios, os extremos e a contagem, nunca a base inteira;
- o resultado anterior, só a frase-resumo;
- a conversa: as últimas mensagens da pessoa e do agente (a janela, não todo o histórico da tela), a pendência de
  esclarecimento com as alternativas, o último ato, o tópico e o registro em curso;
- as funcionalidades da página e o que cada uma faz, para o agente saber o que existe e não anunciar o que não existe.
Tudo passa pela triagem (triagem.py): o texto montado aqui troca só identificadores, valores protegidos e nomes de campo e
arquivo (classes A e C); as mensagens da conversa passam pela triagem completa. Nenhum registro individual, arquivo,
nome de coluna ou credencial entra no cartão.

`referencias_de_fidelidade` devolve, do mesmo material, o que a conferência (fidelidade.py) usa para aceitar ou recusar o
texto do modelo: números, nomes, valores por território, ordens, classes e ressalvas obrigatórias.
"""
from __future__ import annotations

import json

import definicoes
import fidelidade
import painel
import triagem
from resumo_painel import DENSITY_UNIT, number, places_for
from territorial_levels import human_period

MAX_ITENS = 25
MAX_TURNOS = 8
MAX_CARACTERES_POR_TURNO = 700
FAMILIAS = {"distribuicao": "Análise de Distribuição", "espacial": "Análise Espacial", "tendencia": "Análise de Tendência",
            "rotatividade": "Análise de Rotatividade"}
INDICADORES = {"densidade": "densidade por 1.000 habitantes", "quantidade": "quantidade de profissionais"}
VISTAS = {"grafico": "gráfico de bolhas", "mapa": "mapa", "lado": "gráfico e mapa lado a lado"}
# O que a página faz (Docs/PAINEL_INTEGRADO_INTERFACE.md e README): para o agente orientar sem prometer o que não existe.
FUNCIONALIDADES = (
    "Dados: “Dados do Brasil” (médicos por município, estado e Brasil, com população) ou “Enviar meus dados” (CSV, XLS ou "
    "XLSX, com o painel Colunas para as escolhas que faltam).",
    "Seleção de Territórios: escolhe os territórios analisados (estados, municípios, Brasil); vale para todas as análises.",
    "Análise de Distribuição: o indicador de cada território numa competência, em bolhas (tamanho = população) ou no mapa; "
    "grupos por posição (quartis, quintis, decis) e a mudança entre duas competências.",
    "Análise Espacial: a distância geográfica direta até um território de referência e a referência mais próxima.",
    "Análise de Tendência: a classe de tendência de cada território em 4 competências, com as visões Tendência, "
    "Trajetória e Série temporal.",
    "Análise de Rotatividade: a permanência e a saída da coorte inicial; exige um identificador da mesma pessoa.",
    "Indicador: densidade por 1.000 habitantes ou quantidade de profissionais.",
    "Funções: Régua (filtro visual entre dois valores), Condições (quem atende, não atende ou não tem dado), Ordenar "
    "(posições do motor), Comparar (2 ou 3 itens lado a lado, com maior, menor e diferença), Juntar (soma das contagens, "
    "com possível dupla contagem) e Exportar (CSV e Imprimir / PDF).",
    "Vista: Gráfico, Mapa ou Lado a lado. Detalhes: Tabela, Não avaliáveis e Método e procedência.",
    "Desfazer e Limpar seleção, no alto da área; Histórico, no alto da página, reabre análises guardadas sem recalcular.",
    "“Entenda esta análise”, em cada aba, explica a análise com exemplo.",
    "A conversa muda o gráfico com pedidos (“compare Manaus e Tefé”, “mostre a tendência”, “ver no mapa”), explica o "
    "resultado em exibição e os conceitos, e responde sobre a tela; não calcula nada por conta própria.",
)


def _fmt(valor, casas=2) -> str | None:
    if isinstance(valor, bool) or not isinstance(valor, (int, float)):
        return None
    return number(valor, casas)


def _com_unidade(atributo: str, valor, casas=2) -> str | None:
    texto = _fmt(valor, casas)
    if texto is None:
        return None
    return texto + {"densidade": " " + DENSITY_UNIT, "populacao": " habitantes", "distancia_km": " km",
                    "variacao": "%", "permanencia": "%", "quantidade": " profissionais"}.get(atributo, "")


def _casas(itens: list[dict], chave: str) -> int:
    valores = [item.get(chave) for item in itens if isinstance(item.get(chave), (int, float))]
    return places_for(valores) if valores else 2


def _item(body: dict, item: dict, casas: dict) -> dict:
    indicador = body.get("indicador") or "densidade"
    saida = {"nome": item.get("rotulo"), "tipo": item.get("tipo")}
    for chave in ("densidade", "quantidade", "populacao"):
        texto = _com_unidade(chave, item.get(chave), casas.get(chave, 2))
        if texto is not None:
            saida[chave] = texto
    variacao = (item.get("variacao_percentual") or {}).get(indicador)
    if body.get("competencia_inicial") and isinstance(variacao, (int, float)):
        saida["variacao_desde_" + str(body["competencia_inicial"])] = _com_unidade("variacao", variacao)
    if body.get("referencia") is not None:
        if item.get("referencia"):
            saida["papel"] = "território de referência"
        elif isinstance(item.get("distancia_km"), (int, float)):
            saida["distancia_geografica_direta"] = _com_unidade("distancia_km", item["distancia_km"])
            proxima = (item.get("referencia_mais_proxima") or {}).get("rotulo")
            if proxima:
                saida["referencia_mais_proxima"] = proxima
    tendencia = item.get("tendencia")
    if isinstance(tendencia, dict) and body.get("tendencia") is not None:
        if tendencia.get("avaliavel"):
            saida["classe_de_tendencia"] = tendencia.get("rotulo")
            if tendencia.get("motivo_texto"):
                saida["motivo_da_classe"] = tendencia["motivo_texto"]
            valores = [p.get("valor") for p in tendencia.get("observacoes") or [] if isinstance(p.get("valor"), (int, float))]
            casas_obs = places_for(valores) if valores else 2
            saida["valores_observados"] = [
                {"competencia": human_period(str(p.get("competencia"))), "valor": _fmt(p.get("valor"), casas_obs)}
                for p in tendencia.get("observacoes") or []]
        else:
            saida["classe_de_tendencia"] = "não avaliável" + (": " + tendencia["motivo_texto"]
                                                              if tendencia.get("motivo_texto") else "")
    grupo = item.get("grupo")
    if isinstance(grupo, dict) and grupo.get("rotulo"):
        saida["grupo"] = grupo["rotulo"]
    condicoes = item.get("condicoes")
    if isinstance(condicoes, dict) and condicoes.get("situacao"):
        saida["condicoes"] = {"ATENDE": "atende", "NAO_ATENDE": "não atende",
                              "NAO_AVALIAVEL": "sem dado para avaliar"}.get(condicoes["situacao"], condicoes["situacao"])
    ordem = item.get("ordem")
    if isinstance(ordem, dict) and isinstance(ordem.get("posicao"), int):
        saida["posicao_na_ordenacao"] = ordem["posicao"]
    rotatividade = item.get("rotatividade")
    if isinstance(rotatividade, dict) and body.get("rotatividade") is not None:
        if rotatividade.get("avaliavel"):
            saida["permanencia_da_coorte_inicial"] = _com_unidade("permanencia", rotatividade.get("permanencia_percentual"))
            saida["saida_da_coorte_inicial"] = _com_unidade("permanencia", rotatividade.get("saida_percentual"))
        else:
            saida["rotatividade"] = "não avaliável"
    if item.get("motivos"):
        saida["motivo_sem_valor"] = item["motivos"][0]
    return saida


def _resultado(body: dict | None) -> dict | None:
    """O resultado em exibição como o cartão o mostra: só o que a tela mostra, formatado como na tela."""
    if not body:
        return None
    itens = body.get("itens") or []
    casas = {chave: _casas(itens, chave) for chave in ("densidade", "quantidade", "populacao")}
    unidades = [i for i, item in enumerate(itens) if item.get("tipo") in ("municipio", "estado", "brasil")]
    saida = {"frase_resumo_do_motor": (body.get("resumo") or {}).get("texto") or "",
             "nivel": body.get("nivel"), "indicador": INDICADORES.get(body.get("indicador"), body.get("indicador")),
             "competencia": human_period(str(body["competencia"])) if body.get("competencia") else None,
             "categoria": body.get("categoria"), "quantidade_de_itens": len(itens)}
    if body.get("competencia_inicial"):
        saida["competencia_inicial"] = human_period(str(body["competencia_inicial"]))
    tendencia = body.get("tendencia")
    if isinstance(tendencia, dict):
        janela = tendencia.get("janela") or {}
        saida["tendencia"] = {
            "janela": (human_period(str(janela.get("inicio"))) + " a " + human_period(str(janela.get("fim"))))
            if janela.get("inicio") else None,
            "contagens_por_classe": {classe.get("rotulo"): (tendencia.get("contagens") or {}).get(classe.get("codigo"), 0)
                                     for classe in tendencia.get("classes") or []}}
    if len(itens) <= MAX_ITENS:
        saida["itens"] = [_item(body, item, casas) for item in itens]
    else:
        conversa = painel.conversation_facts(body)
        extremos = {}
        for atributo, ordem in conversa["ordem"].items():
            if ordem.get("maior"):
                extremos[atributo] = {"maior": [_item(body, itens[i], casas) for i in ordem["maior"][:3]],
                                      "menor": [_item(body, itens[i], casas) for i in ordem["menor"][:3]],
                                      "com_valor": ordem["com_valor"], "sem_valor": ordem["sem_valor"]}
        saida["extremos_por_atributo"] = extremos
        saida["observacao"] = ("O resultado tem " + str(len(itens)) + " itens; o cartão traz os extremos contados pelo "
                               "motor. Os demais valores estão na tabela dos Detalhes.")
    comparacao = body.get("comparacao")
    if isinstance(comparacao, dict) and comparacao.get("itens"):
        nomes = {item.get("id"): item.get("rotulo") for item in comparacao["itens"]}
        saida["comparacao"] = {"maior": [nomes.get(i) for i in comparacao.get("maior") or []],
                               "menor": [nomes.get(i) for i in comparacao.get("menor") or []],
                               "diferencas": [{"a": nomes.get(d.get("a")), "b": nomes.get(d.get("b")),
                                               "diferenca_a_menos_b": _fmt(d.get("diferenca")),
                                               "relacao_a_sobre_b": _fmt(d.get("relacao"))}
                                              for d in comparacao.get("diferencas") or [] if isinstance(d, dict)]}
    brasil = (body.get("contexto") or {}).get("brasil")
    if isinstance(brasil, dict) and isinstance(brasil.get("densidade"), (int, float)):
        saida["referencia_de_contexto"] = {"nome": brasil.get("rotulo"), "densidade": _com_unidade(
            "densidade", brasil["densidade"]), "nota": brasil.get("nota")}
    if body.get("referencia") is not None:
        saida["ressalva_da_distancia"] = ("A distância é geográfica direta (linha reta); não é distância por estrada, tempo "
                                          "de deslocamento nem acessibilidade real.")
    saida["notas_do_metodo"] = list(body.get("notas") or [])
    if body.get("limitacoes"):
        saida["limitacoes"] = [l if isinstance(l, str) else json.dumps(l, ensure_ascii=False) for l in body["limitacoes"]]
    disponibilidade = body.get("disponibilidade") or {}
    saida["disponibilidade_das_analises"] = {nome: ("disponível" if valor.get("disponivel") else
                                                    "indisponível: " + (valor.get("motivo") or "sem motivo informado"))
                                             for nome, valor in disponibilidade.items() if isinstance(valor, dict)}
    if unidades and len(unidades) <= MAX_ITENS:
        conversa = painel.conversation_facts(body)
        saida["ordens_do_motor"] = {atributo: {"maior": [itens[i]["rotulo"] for i in ordem["maior"]],
                                               "menor": [itens[i]["rotulo"] for i in ordem["menor"]]}
                                    for atributo, ordem in conversa["ordem"].items() if ordem.get("maior")}
    return saida


def _tela(grafico: dict | None, fonte: dict | None, rotulos: dict | None) -> dict:
    grafico = grafico or {}
    unidade = ((rotulos or {}).get("unidade") or {}).get("plural") or "municípios"
    tela = {"analise_aberta": FAMILIAS.get(grafico.get("familia"), "nenhuma análise calculada ainda"),
            "indicador": INDICADORES.get(grafico.get("indicador"), grafico.get("indicador")),
            "nivel": grafico.get("nivel"), "nome_da_unidade": unidade,
            "vista": VISTAS.get(grafico.get("vista"), grafico.get("vista")),
            "mapa_disponivel": grafico.get("mapa_disponivel"),
            "fonte_dos_dados": {"brasil": "Dados do Brasil", "arquivo": "planilha enviada"}.get(
                (fonte or {}).get("tipo"), "nenhuma fonte escolhida ainda")}
    if grafico.get("competencia"):
        tela["competencia"] = human_period(str(grafico["competencia"]))
    if grafico.get("familia") == "tendencia" and grafico.get("janela"):
        tela["janela_da_tendencia"] = [human_period(str(p)) for p in grafico["janela"]]
    if grafico.get("motivo_sem_mapa"):
        tela["motivo_sem_mapa"] = grafico["motivo_sem_mapa"]
    return tela


def _conversa(memoria: dict | None, triar) -> dict:
    """A memória da conversa para o cartão. A pergunta pendente e o pedido original podem repetir o que a pessoa escreveu:
    passam pela triagem completa (`triar`)."""
    memoria = memoria if isinstance(memoria, dict) else {}
    saida = {}
    pendente = memoria.get("pendente")
    if isinstance(pendente, dict) and pendente.get("pergunta"):
        saida["pergunta_pendente_do_agente"] = {
            "pergunta": triar(str(pendente.get("pergunta"))), "pedido_original": triar(str(pendente.get("pedido") or "")),
            "alternativas": [a.get("rotulo") for a in pendente.get("alternativas") or [] if isinstance(a, dict)]}
    lembrada = memoria.get("memoria")
    if isinstance(lembrada, dict):
        saida["ultimo_ato"] = {chave: lembrada.get(chave) for chave in ("ato", "topico", "registro", "atributo", "termos",
                                                                        "tipo", "assunto") if lembrada.get(chave)}
    anteriores = [a.get("rotulo") for a in memoria.get("anteriores") or [] if isinstance(a, dict) and a.get("rotulo")]
    if anteriores:
        saida["estados_anteriores_do_grafico"] = anteriores[-3:]
    return saida


def _turnos(turnos) -> list[dict]:
    validos = []
    for turno in turnos or []:
        if not isinstance(turno, dict):
            continue
        papel = "pessoa" if turno.get("papel") in ("usuario", "user", "pessoa") else "agente"
        texto = turno.get("texto")
        if isinstance(texto, str) and texto.strip():
            validos.append({"papel": papel, "texto": texto.strip()[:MAX_CARACTERES_POR_TURNO]})
    return validos[-MAX_TURNOS:]


def montar(*, mensagem: str, turnos=None, memoria=None, grafico=None, resultado=None, anterior=None, fonte=None,
           rotulos=None, fatos: str | None = None, fichas=(), protecao: triagem.Protecao | None = None,
           numeracao: triagem.Numeracao | None = None) -> dict:
    """O cartão já preparado para o provedor (triagem aplicada) e a mensagem atual preparada."""
    numeracao = numeracao or triagem.Numeracao()
    protecao = protecao or triagem.Protecao()
    janela = _turnos(turnos)
    # A janela da conversa e a mensagem passam pela triagem completa; o texto montado aqui, pelas classes A e C.
    def triar(texto: str) -> str:
        return triagem.preparar(texto, protecao, numeracao)
    conversa_recente = [{"papel": t["papel"], "texto": triar(t["texto"])} for t in janela]
    mensagem_preparada = triar(mensagem)
    cartao = {"tela": _tela(grafico, fonte, rotulos), "resultado_em_exibicao": _resultado(resultado),
              "resultado_anterior": ({"frase_resumo_do_motor": (anterior.get("resumo") or {}).get("texto") or ""}
                                     if anterior else None),
              "conversa": _conversa(memoria, triar), "funcionalidades_da_pagina": list(FUNCIONALIDADES)}
    if fatos:
        # A resposta verificada é texto do sistema (catálogo, motor, gestor de diálogo): fórmulas e códigos de método
        # ("D(u, p, c) = Q(u, p, c) / P(u, p′)", DENOMINADOR_ALTERNATIVO) ficam como estão. Quando ela repete o que a pessoa
        # escreveu ("por que Fulano não aparece?"), o nome já virou marcador na mensagem e continua protegido, com o mesmo
        # número, porque a mensagem e a janela são triadas antes, na mesma numeração.
        cartao["resposta_verificada_do_sistema"] = triagem.preparar(fatos, protecao, numeracao, nominal=False)
    if fichas:
        cartao["fichas_de_metodo"] = definicoes.para_o_provedor(list(fichas))
    texto = json.dumps(cartao, ensure_ascii=False)
    preparado = triagem.preparar(texto, protecao, numeracao, nominal=False)
    try:
        cartao_preparado = json.loads(preparado)
    except json.JSONDecodeError:
        cartao_preparado = {"tela": cartao["tela"]}  # marcador dentro de uma chave quebraria o JSON: só a tela segue
    return {"cartao": cartao_preparado, "conversa_recente": conversa_recente, "mensagem": mensagem_preparada,
            "numeracao": numeracao}


def referencias_de_fidelidade(*, mensagem: str, turnos=None, resultado=None, anterior=None, fatos: str | None = None,
                              fichas=(), pedidas=(), acao: bool = False, marcadores=None, extras=()) -> fidelidade.Referencias:
    """O material verificado que sustenta o texto do modelo, para a conferência."""
    textos = [t["texto"] for t in _turnos(turnos)] + [fatos or ""] + list(extras)
    nomes, itens, ordens = set(), [], {}
    tem_distancia = tem_conjunto = tem_tendencia = False
    indicador = "densidade"
    for body in (resultado, anterior):
        if not body:
            continue
        textos.append(json.dumps(_resultado(body), ensure_ascii=False))
        textos.append((body.get("resumo") or {}).get("texto") or "")
        textos += [n for n in body.get("notas") or [] if isinstance(n, str)]
    if resultado:
        indicador = resultado.get("indicador") or "densidade"
        tem_distancia = resultado.get("referencia") is not None
        tem_tendencia = resultado.get("tendencia") is not None
        for item in resultado.get("itens") or []:
            rotulo = str(item.get("rotulo") or "")
            nomes.add(rotulo)
            nomes.add(rotulo.split(" (")[0])
            tem_conjunto = tem_conjunto or item.get("tipo") == "conjunto"
            proxima = (item.get("referencia_mais_proxima") or {}).get("rotulo")
            if proxima:
                nomes.add(str(proxima))
            valores = {chave: item.get(chave) for chave in ("densidade", "quantidade", "populacao")}
            valores["distancia_km"] = None if item.get("referencia") else item.get("distancia_km")
            valores["variacao"] = (item.get("variacao_percentual") or {}).get(indicador)
            valores["permanencia"] = (item.get("rotatividade") or {}).get("permanencia_percentual")
            itens.append({"nome": rotulo, "valores": {k: v for k, v in valores.items() if isinstance(v, (int, float))},
                          "classe": (item.get("tendencia") or {}).get("classe")
                          if (item.get("tendencia") or {}).get("avaliavel") else None})
        unidades = [i for i, item in enumerate(resultado.get("itens") or [])
                    if item.get("tipo") in ("municipio", "estado", "brasil")]
        if unidades:
            conversa = painel.conversation_facts(resultado)
            ordens = {atributo: {"maior": [resultado["itens"][i]["rotulo"] for i in ordem["maior"]],
                                 "menor": [resultado["itens"][i]["rotulo"] for i in ordem["menor"]]}
                      for atributo, ordem in conversa["ordem"].items()}
        brasil = (resultado.get("contexto") or {}).get("brasil")
        if isinstance(brasil, dict) and brasil.get("rotulo"):
            nomes.add(str(brasil["rotulo"]))
    if anterior:
        for item in anterior.get("itens") or []:
            nomes.add(str(item.get("rotulo") or ""))
            nomes.add(str(item.get("rotulo") or "").split(" (")[0])
    textos.append("\n".join(FUNCIONALIDADES))
    return fidelidade.Referencias(textos=[t for t in textos if t], nomes={n for n in nomes if n}, itens=itens,
                                  ordens=ordens, indicador=indicador, tem_distancia=tem_distancia,
                                  tem_conjunto=tem_conjunto, tem_tendencia=tem_tendencia, acao=acao,
                                  fichas=list(fichas), pedidas=list(pedidas), pergunta=mensagem,
                                  marcadores=dict(marcadores or {}), fatos=fatos or "")
