"""Leitura e explicação, pela conversa, do resultado em exibição na página única (desafio adversarial, 26/10/2026).

Fundamentação (INV-02, INV-03, RQ-SIN-02/03/07/08):
- cada número, nome, competência, classe, relação e nota vem da resposta do motor guardada na sessão (o resultado em
  exibição, com a integridade conferida por conversation_session), copiado como segmento verificável, com a mesma regra de
  apresentação da frase-resumo (resumo_painel.Composer e verify_segment);
- "o maior" e "o menor" são as posições contadas no motor (painel.conversation_facts), com os empates preservados;
- afirmações metodológicas são formas literais do catálogo governado (document_catalog, CFG-DOC/APT-20261016), só dos
  temas já liberados na conversa, e as mensagens sistêmicas são os modelos de CFG-TPL;
- o texto fixo daqui só organiza, conecta e orienta (onde está cada coisa na tela, o que a conversa pode fazer): não define
  método, não compara valores por conta própria, não qualifica normativamente (V-03), não afirma causa (V-04) e não trata
  distância como acesso (V-06).
O registro (objetivo, simples, didático ou técnico) muda a organização e o nível de detalhe, nunca os valores, as classes
ou os limites. Toda composição é conferida por `verificar` antes de sair; uma que não confere não é apresentada.
Desde 26/10/2026 (Adendo PAR-20261026), a regra de cada classe de tendência em palavras entra como segmento da ficha
autorizada (definicoes.py, o mesmo texto de "Entenda esta análise"), conferido como as formas do catálogo. A composição é a
resposta verificada e a reserva: com o provedor disponível, o Gemini a recebe no cartão do contexto e redige a resposta
com as palavras dele, sob a conferência de fidelidade (conversa_gemini.py, fidelidade.py).
"""
from __future__ import annotations

import re

import definicoes
import painel
from document_catalog import DocumentationError, TOPICS, materialize
from resumo_painel import Composer, DENSITY_UNIT, number, places_for, relation_text, verify_segment
from result_conversation import resolve
from territorial_levels import human_period

REGISTROS = ("objetivo", "simples", "didatico", "tecnico")
NOMES_DOS_ATRIBUTOS = {"densidade": "densidade", "quantidade": "quantidade de profissionais", "populacao": "população",
                       "distancia_km": "distância até a referência", "variacao": "variação",
                       "permanencia": "permanência da coorte inicial"}
FAMILIAS = {"distribuicao": "Distribuição", "espacial": "Análise Espacial", "tendencia": "Análise de Tendência",
            "rotatividade": "Rotatividade"}
# Termos da Análise de Tendência que a tela explica em "Entenda esta análise" (classes de CAP-TEN-01, DA-15).
TERMOS_DA_TENDENCIA = {"aceleracao": ("CRESCIMENTO_ACELERADO", "DECLINIO_ACELERADO"),
                       "desaceleracao": ("CRESCIMENTO_DESACELERADO", "DECLINIO_DESACELERADO"),
                       "crescimento": ("CRESCIMENTO", "CRESCIMENTO_ACELERADO", "CRESCIMENTO_DESACELERADO"),
                       "declinio": ("DECLINIO", "DECLINIO_ACELERADO", "DECLINIO_DESACELERADO"),
                       "sem_classificacao": ("SEM_CLASSIFICACAO",), "velocidade": (), "tendencia": ()}
# Temas com formas do catálogo governado já liberadas na conversa (document_catalog.TOPICS, conferência de 20/10/2026).
TEMAS_DO_CATALOGO = {"densidade": "density", "distancia": "spatial", "agregacao": "aggregation",
                     "quintil": "distribution", "referencia": "nearest"}
SITUACOES = {"ATENDE": "atende", "NAO_ATENDE": "não atende", "NAO_AVALIAVEL": "sem dado para avaliar"}
EXPORTACAO = ("O CSV traz todos os itens do resultado (com ou sem a régua), com os valores em precisão integral, a "
              "avaliabilidade e o motivo de cada um. Imprimir / PDF leva o título, o gráfico, as legendas e os detalhes.")


class ComposicaoInvalida(ValueError):
    """Uma composição cujos segmentos não conferem com o resultado: nunca é apresentada."""


def vista(body: dict) -> dict:
    """A resposta do motor com as ordens da conversa (painel.conversation_facts), contadas de novo a cada leitura."""
    return {**body, "conversa": painel.conversation_facts(body)}


class Composicao(Composer):
    """Texto em partes: conectivos fixos e segmentos copiados da resposta (e formas do catálogo governado)."""

    def __init__(self, body: dict):
        super().__init__(vista(body))
        self.documentacao: list[dict] = []
        self.acoes: list[dict] = []

    # ------------------------------------------------------------------ segmentos novos
    def documento(self, id_doc: str, forma: str = "base", evidencia: str | None = None) -> "Composicao":
        form = materialize(id_doc, form=forma, evidence=evidencia)
        self.documentacao.append(form)
        return self._add({"tipo": "EXPLICACAO_METODOLOGICA", "formato": "documento",
                          "caminho": [id_doc, forma, evidencia], "texto": form["text"]})

    def ficha(self, id_ficha: str) -> "Composicao":
        """A formulação autorizada de uma ficha de método (definicoes.py), como segmento conferido."""
        return self._add({"tipo": "EXPLICACAO_METODOLOGICA", "formato": "ficha", "caminho": [id_ficha],
                          "texto": definicoes.FICHAS[id_ficha].texto})

    def item(self, atributo: str, qual: str, posicao: int) -> "Composicao":
        """O rótulo da unidade que o motor pôs na ordem (o maior ou o menor valor de um atributo)."""
        indice = self.body["conversa"]["ordem"][atributo][qual][posicao]
        return self._add({"tipo": "ORDENACAO", "formato": "item", "caminho": ["conversa", "ordem", atributo, qual, posicao],
                          "texto": self.body["itens"][indice]["rotulo"]})

    def nota_igual(self, texto: str) -> "Composicao":
        indice = next((i for i, nota in enumerate(self.body.get("notas") or []) if nota == texto), None)
        return self.note(indice) if indice is not None else self

    def notas_que_comecam(self, *inicios: str) -> int:
        quantas = 0
        for indice, nota in enumerate(self.body.get("notas") or []):
            if any(nota.startswith(inicio) for inicio in inicios):
                if self.parts and not self.parts[-1]["texto"][-1:].isspace():
                    self.text(" ")
                self.note(indice)
                quantas += 1
        return quantas

    def valor(self, indice: int, atributo: str, casas: int = 2) -> "Composicao":
        """O valor de uma unidade com a unidade de medida; sem valor, as palavras da tela ("sem valor")."""
        caminho = caminho_do_atributo(self.body, atributo)
        bruto = resolve(self.body, ["itens", indice] + caminho)
        if not isinstance(bruto, (int, float)) or isinstance(bruto, bool):
            return self.text("sem valor")
        self.number("itens", indice, *caminho, places=casas)
        return self.text(unidade_de_medida(atributo))

    def resultado(self) -> dict:
        return {"texto": self.sentence.strip(), "partes": self.parts, "segmentos": self.segments,
                "documentacao": self.documentacao, "acoes": self.acoes}


def caminho_do_atributo(body: dict, atributo: str) -> list:
    if atributo == "variacao":
        return ["variacao_percentual", body["indicador"]]
    if atributo == "permanencia":
        return ["rotatividade", "permanencia_percentual"]
    return [atributo]


def unidade_de_medida(atributo: str) -> str:
    return {"densidade": " " + DENSITY_UNIT, "populacao": " habitantes", "distancia_km": " km", "variacao": "%",
            "permanencia": "%"}.get(atributo, "")


# --------------------------------------------------------------------------------------------- verificação
def verificar(composicao: dict, body: dict) -> dict:
    """Confere cada segmento contra a resposta do motor (com as ordens contadas de novo) e as partes contra o texto.
    Devolve a composição; levanta ComposicaoInvalida se algo não confere."""
    view = vista(body)
    segmentos, partes = composicao["segmentos"], composicao["partes"]
    if "".join(parte["texto"] for parte in partes).strip() != composicao["texto"]:
        raise ComposicaoInvalida("Partes e texto divergem.")
    for parte in partes:
        if "segmento" in parte and parte["texto"] != segmentos[parte["segmento"]]["texto"]:
            raise ComposicaoInvalida("Parte diferente do segmento.")
    for segmento in segmentos:
        if not _segmento_confere(segmento, view):
            raise ComposicaoInvalida("Segmento sem correspondência no resultado: " + str(segmento.get("caminho")))
    return composicao


def _segmento_confere(segmento: dict, view: dict) -> bool:
    try:
        if segmento["formato"] == "documento":
            id_doc, forma, evidencia = segmento["caminho"]
            return materialize(id_doc, form=forma, evidence=evidencia)["text"] == segmento["texto"]
        if segmento["formato"] == "ficha":
            ficha = definicoes.FICHAS.get(segmento["caminho"][0])
            return ficha is not None and ficha.texto == segmento["texto"]
        if segmento["formato"] == "item":
            indice = resolve(view, segmento["caminho"])
            return isinstance(indice, int) and view["itens"][indice]["rotulo"] == segmento["texto"]
        return verify_segment(segmento, view)
    except (KeyError, IndexError, TypeError, ValueError, DocumentationError):
        return False


# --------------------------------------------------------------------------------------------- utilidades
def unidades(body: dict) -> tuple[str, str, bool]:
    rotulos = body.get("rotulos") or {}
    unidade = (rotulos.get("grupo") if body.get("nivel") == "estados" else rotulos.get("unidade")) or \
        {"singular": "unidade", "plural": "unidades", "genero": "f"}
    return unidade["singular"], unidade["plural"], unidade.get("genero") == "f"


def indices_das_unidades(body: dict) -> list[int]:
    return [i for i, item in enumerate(body.get("itens") or []) if item.get("tipo") in ("municipio", "estado", "brasil")]


def _simples(texto: str) -> str:
    import unicodedata
    return "".join(c for c in unicodedata.normalize("NFD", str(texto).lower()) if not unicodedata.combining(c))


def localizar(body: dict, mensagem: str) -> list[int]:
    """Índices dos itens cujo nome (sem a UF) aparece na mensagem, na ordem da mensagem."""
    texto = " " + re.sub(r"[^a-z0-9]+", " ", _simples(mensagem)) + " "
    achados = []
    for indice, item in enumerate(body.get("itens") or []):
        nome = re.sub(r"[^a-z0-9]+", " ", _simples(str(item.get("rotulo", "")).split(" (")[0].split(" [")[0])).strip()
        if len(nome) >= 3:
            posicao = texto.find(" " + nome + " ")
            if posicao >= 0:
                achados.append((posicao, indice))
    return [indice for _, indice in sorted(achados)]


def _lista(c: Composicao, indices: list[int]) -> Composicao:
    for ordem, indice in enumerate(indices):
        c.text("" if not ordem else " e " if ordem == len(indices) - 1 else ", ").label("itens", indice, "rotulo")
    return c


def _periodo_do_resultado(c: Composicao) -> Composicao:
    body = c.body
    if body.get("tendencia") is not None and body["tendencia"].get("janela"):
        return c.text("de ").period("tendencia", "janela", "inicio").text(" a ").period("tendencia", "janela", "fim")
    return c.text("em ").period("competencia")


# --------------------------------------------------------------------------------------------- fatos por unidade
def _fatos_da_unidade(c: Composicao, indice: int, registro: str, com_nome: bool = True) -> None:
    body = c.body
    item = body["itens"][indice]
    indicador = body["indicador"]
    if com_nome:
        c.label("itens", indice, "rotulo").text(": ")
    if indicador == "densidade":
        c.text("densidade de ").valor(indice, "densidade")
        if registro != "simples" and isinstance(item.get("quantidade"), (int, float)):
            c.text(" (").number("itens", indice, "quantidade").text(" profissionais")
            if isinstance(item.get("populacao"), (int, float)):
                c.text(" e ").number("itens", indice, "populacao").text(" habitantes")
            c.text(")")
    else:
        if isinstance(item.get("quantidade"), (int, float)):
            c.number("itens", indice, "quantidade").text(" profissionais")
        else:
            c.text("sem valor de quantidade")
        if registro != "simples" and isinstance(item.get("populacao"), (int, float)):
            c.text(" (população de ").number("itens", indice, "populacao").text(")")
    if body.get("competencia_inicial") and isinstance((item.get("variacao_percentual") or {}).get(indicador), (int, float)):
        c.text("; variação desde ").period("competencia_inicial").text(": ").valor(indice, "variacao")
    if body.get("referencia") is not None:
        if item.get("referencia"):
            c.text("; é a referência")
        elif isinstance(item.get("distancia_km"), (int, float)):
            c.text("; distância geográfica direta até a referência: ").valor(indice, "distancia_km")
            proxima = item.get("referencia_mais_proxima") or {}
            if proxima.get("rotulo") and registro != "simples":
                c.text(" (").label("itens", indice, "referencia_mais_proxima", "rotulo").text(")")
    tendencia = item.get("tendencia")
    if body.get("tendencia") is not None and isinstance(tendencia, dict):
        if tendencia.get("avaliavel"):
            c.text("; tendência: ").label("itens", indice, "tendencia", "rotulo", kind="VALOR")
            if tendencia.get("classe") == "SEM_CLASSIFICACAO" and tendencia.get("motivo_texto"):
                c.text(" (").label("itens", indice, "tendencia", "motivo_texto", kind="VALOR").text(")")
            if registro in ("didatico", "tecnico") and tendencia.get("observacoes"):
                _observacoes(c, indice)
            if registro == "tecnico" and tendencia.get("velocidades"):
                _velocidades(c, indice)
        else:
            c.text("; tendência não avaliável")
            if tendencia.get("motivo_texto"):
                c.text(" (").label("itens", indice, "tendencia", "motivo_texto", kind="VALOR").text(")")
    grupo = item.get("grupo")
    if body.get("grupos") is not None and isinstance(grupo, dict) and grupo.get("rotulo"):
        c.text("; grupo: ").label("itens", indice, "grupo", "rotulo", kind="VALOR")
    condicoes = item.get("condicoes")
    if body.get("condicoes") is not None and isinstance(condicoes, dict) and condicoes.get("situacao") in SITUACOES:
        c.text("; condições: " + SITUACOES[condicoes["situacao"]])
    ordem = item.get("ordem")
    if body.get("ordenacao") is not None and isinstance(ordem, dict) and isinstance(ordem.get("posicao"), int):
        c.text("; posição na ordenação: ").number("itens", indice, "ordem", "posicao")
    rotatividade = item.get("rotatividade")
    if body.get("rotatividade") is not None and isinstance(rotatividade, dict):
        if rotatividade.get("avaliavel") and isinstance(rotatividade.get("permanencia_percentual"), (int, float)):
            c.text("; permanência da coorte inicial: ").valor(indice, "permanencia")
        else:
            c.text("; permanência não avaliável")
    if not item.get("avaliavel", {}).get("densidade", True) and item.get("motivos") and registro != "simples":
        c.text(". Motivo: ").label("itens", indice, "motivos", 0, kind="VALOR")
    c.text(".")


def _observacoes(c: Composicao, indice: int) -> None:
    pontos = c.body["itens"][indice]["tendencia"]["observacoes"]
    valores = [ponto["valor"] for ponto in pontos if isinstance(ponto.get("valor"), (int, float))]
    casas = places_for(valores) if valores else 2
    c.text("; valores observados: ")
    for ordem, ponto in enumerate(pontos):
        c.text("; " if ordem else "").period("itens", indice, "tendencia", "observacoes", ordem, "competencia").text(", ")
        if isinstance(ponto.get("valor"), (int, float)):
            c.number("itens", indice, "tendencia", "observacoes", ordem, "valor", places=casas)
        else:
            c.text("sem valor")


def _velocidades(c: Composicao, indice: int) -> None:
    velocidades = c.body["itens"][indice]["tendencia"]["velocidades"]
    tendencia = c.body["tendencia"]
    casas = max(4, places_for(velocidades))
    c.text("; velocidades (variação por " + str(tendencia.get("unidade_tempo") or "período") + "): ")
    for ordem in range(len(velocidades)):
        c.text("; " if ordem else "").number("itens", indice, "tendencia", "velocidades", ordem, places=casas)


# --------------------------------------------------------------------------------------------- respostas
def _sem_resultado() -> dict:
    return {"texto": "Ainda não há um gráfico calculado nesta conversa. Escolha os territórios na Seleção de Territórios "
                     "ou me diga quais quer ver: o nome de um estado ou de municípios, ou “todos os estados”.", "partes": [],
            "segmentos": [],
            "documentacao": [], "acoes": []}


def explicar_resultado(body: dict | None, registro: str = "objetivo", foco: list[int] | None = None) -> dict:
    """O resultado em exibição, no registro pedido. Sempre a partir da frase-resumo do motor (já verificada) e dos fatos de
    cada território (até 4 por extenso; com mais, os extremos contados no motor)."""
    if not body:
        return _sem_resultado()
    c = Composicao(body)
    registro = registro if registro in REGISTROS else "objetivo"
    unidades_ = indices_das_unidades(body)
    alvo = [i for i in (foco or []) if i in unidades_] or (unidades_ if len(unidades_) <= 4 else [])
    singular, plural, feminino = unidades(body)
    if registro == "didatico":
        _didatico(c, body, alvo, plural)
    elif registro == "tecnico":
        _tecnico(c, body, alvo)
    elif registro == "simples":
        _simples_resultado(c, body, alvo, plural, feminino)
    else:
        _copia_resumo(c, body)
        if alvo:
            c.text("\n\nEm detalhe:")
            for indice in alvo:
                c.text("\n• ")
                _fatos_da_unidade(c, indice, "objetivo")
        elif len(unidades_) > 4:
            _extremos(c, body["indicador"], plural)
    _convite(c, body)
    return verificar(c.resultado(), body)


def _copia_resumo(c: Composicao, body: dict) -> None:
    """A frase-resumo do motor como veio (cada segmento copiado de novo da resposta)."""
    resumo = body.get("resumo") or {}
    segmentos = resumo.get("segmentos") or []
    for parte in resumo.get("partes") or []:
        if "segmento" in parte:
            c._add(dict(segmentos[parte["segmento"]]))
        else:
            c.text(parte["texto"])


def _extremos(c: Composicao, atributo: str, plural: str) -> None:
    ordem = c.body["conversa"]["ordem"].get(atributo) or {}
    if not ordem.get("maior"):
        return
    c.text("\n\nMaior valor de " + NOMES_DOS_ATRIBUTOS[atributo] + ": ")
    for k in range(len(ordem["maior"])):
        c.text(", " if k else "").item(atributo, "maior", k)
    c.text(" (").valor(ordem["maior"][0], atributo).text("). Menor valor: ")
    for k in range(len(ordem["menor"])):
        c.text(", " if k else "").item(atributo, "menor", k)
    c.text(" (").valor(ordem["menor"][0], atributo).text(").")


def _simples_resultado(c: Composicao, body: dict, alvo: list[int], plural: str, feminino: bool) -> None:
    indicador = body["indicador"]
    c.text("Em poucas palavras: o gráfico mostra ")
    c.text("quantos profissionais há para cada 1.000 habitantes" if indicador == "densidade" else
           "quantos profissionais há")
    c.text(" em cada " + unidades(body)[0] + ", ")
    _periodo_do_resultado(c).text(".")
    if body.get("comparacao") is not None and (body["comparacao"].get("diferencas") or body["comparacao"].get("maior")):
        comparacao = body["comparacao"]
        if comparacao.get("diferencas"):
            c.text(" ").relation("comparacao", "diferencas", 0)
        else:
            c.text(" Na comparação, ").relation("comparacao", "maior").text(".")
    for indice in alvo:
        c.text("\n• ").label("itens", indice, "rotulo").text(": ").valor(indice, indicador)
        tendencia = body["itens"][indice].get("tendencia")
        if body.get("tendencia") is not None and isinstance(tendencia, dict) and tendencia.get("avaliavel"):
            c.text(" no fim do período; na tendência, ").label("itens", indice, "tendencia", "rotulo", kind="VALOR")
        c.text(".")
    if not alvo:
        _extremos(c, indicador, plural)


def _didatico(c: Composicao, body: dict, alvo: list[int], plural: str) -> None:
    indicador = body["indicador"]
    familia = "tendencia" if body.get("tendencia") is not None else "espacial" if body.get("referencia") is not None \
        else "rotatividade" if body.get("rotatividade") is not None else "distribuicao"
    c.text("Vamos por partes.\n1. O que está no gráfico: ").text(FAMILIAS[familia] + ", com a " +
                                                               ("densidade (profissionais por 1.000 habitantes)"
                                                                if indicador == "densidade" else "quantidade de profissionais"))
    c.text(", ")
    _periodo_do_resultado(c).text(".\n2. O que o motor calculou: ")
    _copia_resumo(c, body)
    if alvo:
        c.text("\n3. Território a território:")
        for indice in alvo:
            c.text("\n• ")
            _fatos_da_unidade(c, indice, "didatico")
    c.text("\n4. Como ler: cada bolha é " + ("uma " if unidades(body)[2] else "um ") + unidades(body)[0] +
           "; a altura mostra o valor, e o tamanho, a população.")
    c.text("\n5. O que o resultado não diz: ele descreve os valores; não identifica causas nem diz se um valor é "
           "adequado ou não (esta versão não tem critério normativo).")


def _tecnico(c: Composicao, body: dict, alvo: list[int]) -> None:
    c.text("Leitura técnica do resultado. ")
    _copia_resumo(c, body)
    if alvo:
        c.text("\n\nValores do motor por unidade:")
        for indice in alvo:
            c.text("\n• ")
            _fatos_da_unidade(c, indice, "tecnico")
    c.text("\n\nMétodo e procedência (notas do motor):")
    antes = len(c.parts)
    c.notas_que_comecam("Tendência (CAP-TEN-01", "Valores de ", "Ordenação por", "Classes de tendência")
    if body.get("referencia") is not None:
        c.text(" ").text("Referência: ").label("referencia", "origem")
    if len(c.parts) == antes:
        c.text(" (sem notas de método nesta resposta).")
    if body.get("tendencia") is not None:
        c.text("\nVersão do método da tendência: ").label("tendencia", "versao_metodo").text(".")


def _convite(c: Composicao, body: dict) -> None:
    sugestoes = []
    if body.get("tendencia") is not None:
        sugestoes.append("o que significa a classe de cada território")
    if len(indices_das_unidades(body)) > 1:
        sugestoes.append("quem tem o maior valor")
    sugestoes.append("explicar de um jeito mais simples ou mais técnico")
    if len(sugestoes) == 1:
        c.text("\n\nSe quiser, posso " + sugestoes[0] + ".")
    else:
        c.text("\n\nSe quiser, pergunte " + ", ".join(sugestoes[:-1]) + ", ou peça para " + sugestoes[-1] + ".")


def explicar_territorio(body: dict | None, indice: int, registro: str = "objetivo") -> dict:
    """"E o que isso quer dizer para esse município?": os fatos do território, no registro pedido, e o que o resultado
    não diz (sem causa e sem juízo)."""
    if not body:
        return _sem_resultado()
    c = Composicao(body)
    c.text("Para ").label("itens", indice, "rotulo").text(", o resultado ")
    _periodo_do_resultado(c).text(" diz o seguinte: ")
    _fatos_da_unidade(c, indice, registro if registro != "objetivo" else "didatico", com_nome=False)
    tendencia = body["itens"][indice].get("tendencia")
    if body.get("tendencia") is not None and isinstance(tendencia, dict) and tendencia.get("avaliavel"):
        c.text("\nO significado de cada classe está em “Entenda esta análise”, na aba Tendência.")
        c.acoes.append({"tipo": "explicar", "aba": "tendencia", "termos": [tendencia.get("classe")]})
    c.text("\nIsso descreve como o indicador se comportou nesses períodos. Não diz por que isso aconteceu nem se a "
           "situação é adequada: para isso seria preciso um critério ou uma análise que esta versão não tem.")
    return verificar(c.resultado(), body)


def _codigos_dos_termos(termos: list[str], body: dict, foco: list[int]) -> list[str]:
    """Os códigos de classe a que os termos se referem, pela família dos territórios em foco: "aceleração" num território
    que cresce é a Aceleração do crescimento; "crescimento" sozinho é a classe Crescimento."""
    familias = {(body["itens"][i].get("tendencia") or {}).get("familia") for i in foco} - {None, "NENHUMA"}
    familia = familias.pop() if len(familias) == 1 else None
    codigos = []
    for termo in termos:
        if termo in ("aceleracao", "desaceleracao"):
            prefixo = "CRESCIMENTO" if familia != "DECLINIO" else "DECLINIO"
            codigos.append(prefixo + ("_ACELERADO" if termo == "aceleracao" else "_DESACELERADO"))
            if familia is None:
                codigos.append(("DECLINIO" if prefixo == "CRESCIMENTO" else "CRESCIMENTO") +
                               ("_ACELERADO" if termo == "aceleracao" else "_DESACELERADO"))
        elif termo == "crescimento":
            codigos.append("CRESCIMENTO")
        elif termo == "declinio":
            codigos.append("DECLINIO")
        elif termo == "sem_classificacao":
            codigos.append("SEM_CLASSIFICACAO")
    return list(dict.fromkeys(codigos))


def explicar_conceito(body: dict | None, termos: list[str], registro: str = "objetivo",
                      foco: list[int] | None = None) -> dict:
    """Pergunta conceitual sobre um termo do resultado ("não entendi a aceleração", "o que é quintil?").

    Temas com formas liberadas do catálogo governado: as formas literais, com os fatos do resultado. Termos da Análise de
    Tendência: os fatos do resultado que mostram o termo (a classe e os valores observados, do motor; no técnico, as
    velocidades e a nota do método), a regra de cada classe em palavras (a ficha autorizada, o mesmo texto da tela) e a
    explicação da tela ("Entenda esta análise"), que a conversa abre e destaca."""
    termos = [t for t in termos if t in TERMOS_DA_TENDENCIA or t in TEMAS_DO_CATALOGO]
    catalogo = [t for t in termos if t in TEMAS_DO_CATALOGO]
    tendencia = [t for t in termos if t in TERMOS_DA_TENDENCIA]
    if catalogo and not tendencia:
        return _conceito_do_catalogo(body, catalogo, registro)
    if not body:
        return {"texto": "Para explicar esse termo com os números certos, preciso de um resultado na tela. A explicação de "
                         "cada análise também está em “Entenda esta análise”, na aba dela.", "partes": [], "segmentos": [],
                "documentacao": [], "acoes": []}
    c = Composicao(body)
    if body.get("tendencia") is None:
        c.text("Esse termo é da Análise de Tendência, e o gráfico em exibição não tem a tendência. Peça, por exemplo, "
               "“mostre a tendência desses municípios”, e eu explico com os valores do motor.")
        return verificar(c.resultado(), body)
    unidades_ = indices_das_unidades(body)
    foco = [i for i in (foco or []) if i in unidades_] or unidades_[:3]
    codigos = _codigos_dos_termos(tendencia, body, foco)
    rotulos = {classe["codigo"]: classe["rotulo"] for classe in body["tendencia"].get("classes") or []}
    nomes = [rotulos[codigo] for codigo in codigos if codigo in rotulos]
    # Fatos do resultado (as classes e a janela, copiadas do motor) e, abaixo, a regra de cada classe pela ficha autorizada.
    if nomes:
        c.text(("“" + "” e “".join(nomes) + "” são classes diferentes" if len(nomes) > 1 else "“" + nomes[0] +
                "” é uma das classes") + " da Análise de Tendência deste gráfico, ")
        _periodo_do_resultado(c).text(".")
    else:
        c.text("A Análise de Tendência deste gráfico vai ")
        _periodo_do_resultado(c).text(".")
    contagens = body["tendencia"].get("contagens") or {}
    presentes = [codigo for codigo in codigos if contagens.get(codigo)]
    if codigos:
        c.text(" No gráfico,")
        for ordem, codigo in enumerate(codigos):
            if codigo not in rotulos:
                continue
            c.text(";" if ordem else "").text(" ").label("tendencia", "classes", _posicao_da_classe(body, codigo), "rotulo")
            c.text(" tem ") if contagens.get(codigo) else c.text(" não tem nenhum território")
            if contagens.get(codigo):
                c.count(*_singular_plural(body), "tendencia", "contagens", codigo)
        c.text(".")
    mostrar = [i for i in unidades_ if (body["itens"][i].get("tendencia") or {}).get("classe") in presentes][:3] or foco
    c.text("\n")
    for indice in mostrar:
        c.text("\n• ").label("itens", indice, "rotulo").text(": ")
        item = body["itens"][indice].get("tendencia") or {}
        if item.get("avaliavel"):
            c.label("itens", indice, "tendencia", "rotulo", kind="VALOR")
            _observacoes(c, indice)
            if (registro == "tecnico" or "velocidade" in tendencia) and item.get("velocidades"):
                _velocidades(c, indice)
        else:
            c.text("tendência não avaliável")
        c.text(".")
    for codigo in codigos:
        if codigo in rotulos and "classe:" + codigo in definicoes.FICHAS:
            c.text("\n\n").ficha("classe:" + codigo)
    if registro == "tecnico" or "velocidade" in tendencia:
        c.text("\n\nNota do método, como o motor registra: ")
        if not c.notas_que_comecam("Tendência (CAP-TEN-01"):
            c.text("(sem a nota nesta resposta).")
    c.text("\n\nA explicação completa, com exemplos, está em “Entenda esta análise”, na aba Tendência" +
           (": abri e destaquei " + ("“" + "” e “".join(nomes) + "”") if nomes else ": abri a explicação") + ".")
    c.acoes.append({"tipo": "explicar", "aba": "tendencia", "termos": codigos})
    return verificar(c.resultado(), body)


def _singular_plural(body: dict) -> tuple[str, str]:
    singular, plural, _ = unidades(body)
    return singular, plural


def _posicao_da_classe(body: dict, codigo: str) -> int:
    return next(i for i, classe in enumerate(body["tendencia"]["classes"]) if classe["codigo"] == codigo)


def _conceito_do_catalogo(body: dict | None, termos: list[str], registro: str) -> dict:
    alvo = body if body else {"itens": [], "indicador": "densidade", "notas": []}
    c = Composicao(alvo)
    temas = list(dict.fromkeys(TEMAS_DO_CATALOGO[t] for t in termos))
    c.text("Pela documentação governada do método:" if registro == "tecnico" else
           "A definição usada pelo sistema é a do catálogo governado do método:")
    for tema in temas:
        chaves = list(TOPICS[tema])
        if registro == "simples" and tema == "density":
            chaves = [chaves[1], chaves[0], *chaves[2:]]  # apresentação progressiva: só reorganiza, sem editar
        if registro == "simples":
            chaves = chaves[:2]
        for chave in chaves:
            c.text("\n\n").documento(chave)
    if body and "densidade" in termos and body.get("indicador") == "densidade":
        unidades_ = indices_das_unidades(body)[:3]
        if unidades_:
            c.text("\n\nNo gráfico:")
            for indice in unidades_:
                c.text("\n• ")
                _fatos_da_unidade(c, indice, "objetivo")
    if "distancia" in termos or "referencia" in termos:
        c.text("\n\n").documento("DOC:TPL-11", forma="mensagem", evidencia="DISTANCIA_VERIFICADA")
    return verificar(c.resultado(), alvo)


def comparar_atributo(body: dict | None, atributo: str, maior: bool = True) -> dict:
    """"Qual deles tem maior densidade?", "e a população?": a ordem contada no motor, com empates, e os valores."""
    if not body:
        return _sem_resultado()
    c = Composicao(body)
    ordem = c.body["conversa"]["ordem"].get(atributo) or {}
    singular, plural, feminino = unidades(body)
    nome = NOMES_DOS_ATRIBUTOS[atributo]
    qual = "maior" if maior else "menor"
    if atributo == "distancia_km" and body.get("referencia") is None:
        c.text("O gráfico em exibição não tem referência, então não há distância para comparar. Faça a Escolha dos "
               "territórios na Análise Espacial ou peça, por exemplo, “use como referência o município de maior "
               "densidade”.")
        return verificar(c.resultado(), body)
    if atributo == "variacao" and not body.get("competencia_inicial"):
        c.text("O gráfico em exibição não tem competência inicial, então não há variação calculada. Peça, por exemplo, "
               "“mostre a variação desde 2021”.")
        return verificar(c.resultado(), body)
    if not ordem.get(qual):
        c.text("Nenhum" + ("a " if feminino else " ") + singular + " do gráfico tem valor de " + nome + " ")
        _periodo_do_resultado(c).text(".")
        return verificar(c.resultado(), body)
    unidades_ = indices_das_unidades(body)
    empate = len(ordem[qual]) > 1
    if len(unidades_) == 1:
        c.text("Só há ").label("itens", unidades_[0], "rotulo").text(" no gráfico: ").valor(unidades_[0], atributo)
        c.text(" de " + nome + ".")
        return verificar(c.resultado(), body)
    if empate and len(ordem[qual]) == ordem["com_valor"]:
        c.text("Todos os " + plural + " com valor têm a mesma " + nome + ": ").valor(ordem[qual][0], atributo).text(".")
    else:
        c.text(("Empatados com a " if empate else "A ") + qual + " " + nome + " ")
        _periodo_do_resultado(c).text(": " if empate else " é a de ")
        for k in range(len(ordem[qual])):
            c.text(", " if k else "").item(atributo, qual, k)
        c.text(", com ").valor(ordem[qual][0], atributo).text(".")
        outros = [i for i in unidades_ if i not in ordem[qual]][:4]
        if outros:
            c.text(" " + ("Os demais" if len(outros) > 1 else "O outro") + ": ")
            for k, indice in enumerate(outros):
                c.text("; " if k else "").label("itens", indice, "rotulo").text(", ").valor(indice, atributo)
            c.text(".")
    if ordem.get("sem_valor"):
        c.text(" ").number("conversa", "ordem", atributo, "sem_valor").text(" sem valor de " + nome + ".")
    if atributo == "distancia_km":
        c.text(" ").documento("DOC:TPL-11", forma="mensagem", evidencia="DISTANCIA_VERIFICADA")
    return verificar(c.resultado(), body)


def diferenca(body: dict | None) -> dict | None:
    """"Qual a diferença entre eles?": a diferença assinada A − B que o motor calculou na comparação; sem comparação
    calculada, None (a conversa oferece abrir a comparação)."""
    if not body or body.get("comparacao") is None or not body["comparacao"].get("diferencas"):
        return None
    c = Composicao(body)
    indicador = body["indicador"]
    unidade = " " + DENSITY_UNIT if indicador == "densidade" else ""
    comparacao = body["comparacao"]
    entrada = comparacao["diferencas"][0]
    posicao = {item["id"]: i for i, item in enumerate(comparacao["itens"])}
    a, b = posicao[entrada["a"]], posicao[entrada["b"]]
    casas = places_for([comparacao["itens"][a]["valor"], comparacao["itens"][b]["valor"]])
    c.text("Na comparação de " + ("densidade" if indicador == "densidade" else "quantidade") + " ")
    _periodo_do_resultado(c).text(": ").label("comparacao", "itens", a, "rotulo", kind="VALOR").text(", ") \
        .number("comparacao", "itens", a, "valor", places=casas).text("; ") \
        .label("comparacao", "itens", b, "rotulo", kind="VALOR").text(", ") \
        .number("comparacao", "itens", b, "valor", places=casas).text(unidade + ". ").relation("comparacao", "diferencas", 0)
    c.text(" A diferença (A − B, com A = ").label("comparacao", "itens", a, "rotulo", kind="VALOR").text(") é de ") \
        .number("comparacao", "diferencas", 0, "diferenca").text(unidade + ".")
    return verificar(c.resultado(), body)


def contagem(body: dict | None) -> dict:
    if not body:
        return _sem_resultado()
    c = Composicao(body)
    singular, plural, _ = unidades(body)
    c.text("O gráfico tem ").count(singular, plural, "resumo", "contagens", "unidades")
    if (body.get("resumo") or {}).get("contagens", {}).get("conjuntos"):
        c.text(" e ").count("conjunto", "conjuntos", "resumo", "contagens", "conjuntos")
    c.text(", ")
    _periodo_do_resultado(c).text(".")
    if (body.get("resumo") or {}).get("contagens", {}).get("sem_valor"):
        c.text(" ").count(singular, plural, "resumo", "contagens", "sem_valor").text(" sem valor nesta competência.")
    return verificar(c.resultado(), body)


# --------------------------------------------------------------------------------------------- limites de interpretação
QUEDA = re.compile(r"\b(?:queda|caiu|cair|cairam|reducao|reduziu|diminuiu|diminuicao|piora|piorou|baixou|declinio)\b")
ALTA = re.compile(r"\b(?:subiu|subida|aumento|aumentou|cresceu|crescimento|alta|melhora|melhorou|elevou)\b")


def _direcoes(body: dict, indices: list[int]) -> dict[int, str]:
    """A direção do que o motor mostra para cada unidade: pela variação (CAP-TMP-01) ou pela família da tendência."""
    saida = {}
    indicador = body["indicador"]
    for indice in indices:
        item = body["itens"][indice]
        variacao = (item.get("variacao_percentual") or {}).get(indicador) if body.get("competencia_inicial") else None
        familia = (item.get("tendencia") or {}).get("familia") if body.get("tendencia") is not None else None
        if isinstance(variacao, (int, float)):
            saida[indice] = "alta" if variacao > 0 else "queda" if variacao < 0 else "estavel"
        elif familia in ("CRESCIMENTO", "DECLINIO"):
            saida[indice] = "alta" if familia == "CRESCIMENTO" else "queda"
    return saida


def limite(body: dict | None, tipo: str, mensagem: str = "", foco: list[int] | None = None) -> dict:
    """O que o resultado permite e não permite concluir, com os fatos do motor e as regras governadas:
    - "normativo" (suficiente, falta, excesso, adequado) e "melhora" (melhorou, piorou): CFG-NOR, sem juízo;
    - "causa" (por que caiu, qual a causa): EXC-03/TPL-06, com a conferência do que a pergunta pressupõe;
    - "acesso" (tempo de viagem, estrada): TPL-11;
    - "procedencia" (de onde vem o número, tem certeza): as notas do motor."""
    alvo = body if body else {"itens": [], "indicador": "densidade", "notas": []}
    c = Composicao(alvo)
    indices = [i for i in (foco or []) if body and i in indices_das_unidades(body)] or \
        (indices_das_unidades(body)[:3] if body else [])
    simples = _simples(mensagem)
    if tipo == "causa":
        direcoes = _direcoes(body, indices) if body else {}
        pede_queda, pede_alta = bool(QUEDA.search(simples)), bool(ALTA.search(simples))
        contraria = [i for i, d in direcoes.items() if (pede_queda and d == "alta") or (pede_alta and d == "queda")]
        if contraria and body:
            c.text("Antes, uma conferência: o resultado não mostra " + ("queda" if pede_queda else "alta") + " para ")
            _lista(c, contraria).text(". ")
        c.text("Quanto à causa, vale a regra do escopo: “").documento("DOC:TPL-06", forma="mensagem", evidencia="ADM-FE") \
            .text("” (inferência causal). A análise descreve o que mudou e quanto; ela não identifica por que mudou.")
        if body and indices:
            c.text("\n\nO que o motor mostra:")
            for indice in indices:
                c.text("\n• ")
                _fatos_da_unidade(c, indice, "didatico")
        c.documentacao.append(materialize("DOC:EXC-03"))
    elif tipo in ("normativo", "melhora"):
        if body and indices:
            c.text("O que o resultado mostra:")
            for indice in indices:
                c.text("\n• ")
                _fatos_da_unidade(c, indice, "objetivo")
            c.text("\n\n")
        if tipo == "melhora":
            c.text("Esses números descrevem como o indicador mudou; eles não dizem se a situação ficou melhor ou pior. ")
        else:
            c.text("Esses números não dizem se há profissionais em número suficiente, insuficiente ou excessivo. ")
        c.text("A regra desta versão: “").documento("DOC:CFG-NOR").text("”")
        c.text("\n\nSe você tiver um critério, posso aplicá-lo como condição, sem rótulo de juízo: por exemplo, “mostre os "
               "municípios com densidade menor que 1”.")
    elif tipo == "acesso":
        c.documento("DOC:TPL-11", forma="mensagem", evidencia="DISTANCIA_VERIFICADA")
        if body and body.get("referencia") is not None and indices:
            c.text("\n\nNo gráfico, as distâncias geográficas diretas até a referência:")
            for indice in indices:
                if isinstance(body["itens"][indice].get("distancia_km"), (int, float)):
                    c.text("\n• ").label("itens", indice, "rotulo").text(": ").valor(indice, "distancia_km")
    else:  # procedência
        c.text("Os números vêm do motor, calculados sobre os dados em uso e conferidos antes de aparecer aqui; a conversa "
               "não calcula nada.")
        if body:
            c.text(" Como o motor registra:")
            if not c.notas_que_comecam("Valores de ", "Tendência (CAP-TEN-01", "Unidade de contagem"):
                c.text(" (sem notas de procedência nesta resposta).")
    return verificar(c.resultado(), alvo)


# --------------------------------------------------------------------------------------------- estado da aplicação
def estado(body: dict | None, assunto: str, ctx: dict | None = None, fonte: dict | None = None,
           anterior: dict | None = None, nome: str = "", indice: int | None = None) -> dict:
    """Perguntas sobre o estado da tela: dados carregados, territórios, seleção, mapa, relatório, análise anterior, o que
    mudou, por que algo não aparece e disponibilidade das análises. Só o que a resposta do motor e o contexto da tela
    trazem; o que não está no contexto não é presumido."""
    ctx = ctx or {}
    alvo = body if body else {"itens": [], "indicador": "densidade", "notas": [], "rotulos": {}}
    c = Composicao(alvo)
    singular, plural, feminino = unidades(alvo)
    if assunto == "dados":
        _dados(c, body, fonte)
    elif assunto == "territorios":
        if not body:
            return _sem_resultado()
        indices = [i for i, item in enumerate(body["itens"])]
        c.text("No gráfico ")
        _periodo_do_resultado(c).text(", " + ("estão " if len(indices) != 1 else "está "))
        c.count(singular, plural, "resumo", "contagens", "unidades")
        if (body.get("resumo") or {}).get("contagens", {}).get("conjuntos"):
            c.text(" e ").count("conjunto", "conjuntos", "resumo", "contagens", "conjuntos")
        c.text(": ")
        _lista(c, indices[:12])
        if len(indices) > 12:
            c.text(", entre outros (a lista completa fica em Detalhes)")
        c.text(".")
    elif assunto == "selecao":
        _selecao(c, body, ctx, singular, plural)
    elif assunto == "mapa":
        _mapa(c, body, ctx)
    elif assunto == "relatorio":
        c.text(EXPORTACAO + " Também há “Baixar método e parâmetros (TXT)”. Os três ficam em Exportar, nas Ferramentas da "
               "análise.")
        if body:
            c.text(" Hoje o CSV teria ").count("item", "itens", "resumo", "contagens", "unidades")
            c.text(" (").count(singular, plural, "resumo", "contagens", "unidades").text(").")
    elif assunto == "anterior":
        if anterior is None:
            c.text("Ainda não há análise anterior nesta conversa, com estes dados. As análises guardadas ficam no Histórico, "
                   "no alto da página.")
        else:
            return _anterior(anterior)
    elif assunto == "mudou":
        if anterior is None or not body:
            c.text("Não tenho um gráfico anterior nesta conversa para comparar com o atual.")
        else:
            return _mudou(body, anterior)
    elif assunto == "ausente":
        _ausente(c, body, nome, indice, singular)
    elif assunto in ("rotatividade", "espacial", "tendencia", "distribuicao", "estados"):
        _disponibilidade(c, body, assunto)
    else:
        c.text("Não identifiquei sobre qual parte da tela é a pergunta. Posso falar dos dados em uso, dos territórios, da "
               "seleção, do mapa, do relatório ou da análise anterior.")
    return verificar(c.resultado(), alvo)


def _dados(c: Composicao, body: dict | None, fonte: dict | None) -> None:
    fonte = fonte or {}
    if fonte.get("tipo") == "brasil":
        c.text("Você está usando os dados do Brasil. " + (fonte.get("descricao") or "").strip())
    elif fonte.get("tipo") == "arquivo":
        c.text("Você está usando a planilha enviada" + (" (" + fonte["nome"] + ")" if fonte.get("nome") else "") +
               ", lida só no servidor local.")
    else:
        c.text("Ainda não identifiquei a fonte dos dados nesta conversa.")
    if body:
        c.text(" O gráfico usa a categoria ").label("categoria").text(" ")
        _periodo_do_resultado(c).text(".")


def _selecao(c: Composicao, body: dict | None, ctx: dict, singular: str, plural: str) -> None:
    municipios = ctx.get("municipios") or {}
    if ctx.get("nivel") == "estados":
        c.text("A seleção está no nível dos estados")
    elif ctx.get("nivel") == "brasil":
        c.text("A seleção é o Brasil como uma unidade (o total nacional)")
    elif municipios.get("todos"):
        c.text("A seleção tem todos os " + plural + " da base")
    else:
        partes = []
        if municipios.get("estados"):
            from territorial_selection import STATES
            nomes = [STATES[chave][1] for chave in municipios["estados"] if chave in STATES] or municipios["estados"]
            partes.append("os " + plural + " de " + (", ".join(nomes[:-1]) + " e " + nomes[-1] if len(nomes) > 1 else nomes[0]))
        if municipios.get("ids"):
            quantos = len(municipios["ids"])
            partes.append(str(quantos) + " " + (singular if quantos == 1 else plural) + " escolhid" +
                          ("a" if unidades(c.body)[2] else "o") + ("" if quantos == 1 else "s") + " um a um")
        c.text("A seleção tem " + (" e ".join(partes) if partes else "nenhum território ainda"))
    c.text(". Ela vale para todas as análises (Distribuição, Análise Espacial, Tendência e Rotatividade) e pode ser mudada a "
           "qualquer momento, na Seleção de Territórios ou pela conversa.")
    if body:
        c.text(" No gráfico, isso dá ").count(singular, plural, "resumo", "contagens", "unidades").text(".")


def _mapa(c: Composicao, body: dict | None, ctx: dict) -> None:
    if ctx.get("mapa_disponivel") is False:
        motivo = (ctx.get("motivo_sem_mapa") or "").strip()
        c.text("O mapa não está disponível nesta análise" + (": " + motivo.rstrip(".") if motivo else "") + ".")
        return
    if ctx.get("vista") not in ("mapa", "lado"):
        c.text("O mapa não está na tela agora (a vista é o gráfico). Peça “ver no mapa” para trocar. ")
    # O que é quintil fica com a forma governada (CAP-DIS-02), pedida à parte; aqui, só o que a tela mostra.
    c.text("No mapa, cada ponto é um município, na coordenada da sede municipal, e a cor mostra o grupo do indicador (os "
           "quintis do motor). Para a definição dos quintis, pergunte “o que é quintil?”.")
    if body and body.get("grupos_mapa"):
        c.text(" Pontos por grupo: ")
        for k in range(len(body["grupos_mapa"].get("rotulos") or [])):
            c.text("; " if k else "").label("grupos_mapa", "rotulos", k).text(", ").number("grupos_mapa", "contagens", k)
        c.text(".")
    c.text(" A posição não mede distância por estradas nem acesso a serviços.")


def _ausente(c: Composicao, body: dict | None, nome: str, indice: int | None, singular: str) -> None:
    if body and indice is not None:
        item = body["itens"][indice]
        c.label("itens", indice, "rotulo").text(" está no gráfico")
        if item.get(body["indicador"]) is None:
            c.text(", mas sem valor de " + body["indicador"] + " nesta competência")
            if item.get("motivos"):
                c.text(": ").label("itens", indice, "motivos", 0, kind="VALOR")
        c.text(". Se não aparece no desenho, confira a régua e os filtros, que escondem bolhas sem mudar o cálculo.")
        return
    c.text("“" + nome + "” não está no gráfico porque não faz parte da seleção atual. Para incluir, peça “inclua " + nome +
           "” ou marque na Seleção de Territórios.")


def _disponibilidade(c: Composicao, body: dict | None, familia: str) -> None:
    disponibilidade = (body or {}).get("disponibilidade") or {}
    entrada = disponibilidade.get(familia)
    nome = FAMILIAS.get(familia, "a visão por estados" if familia == "estados" else familia)
    if not entrada:
        c.text("Não tenho a disponibilidade de " + nome + " no resultado em exibição.")
    elif entrada.get("disponivel"):
        c.text(nome + " está disponível com estes dados. Abra a aba dela ou peça pela conversa.")
    elif entrada.get("motivo"):
        c.label("disponibilidade", familia, "motivo", kind="VALOR")
    else:
        c.text(nome + " não está disponível com estes dados.")


def _anterior(anterior: dict) -> dict:
    c = Composicao(anterior)
    c.text("A análise anterior, nesta conversa, foi: ")
    _copia_resumo(c, anterior)
    return verificar(c.resultado(), anterior)


def _mudou(body: dict, anterior: dict) -> dict:
    """O que mudou entre o gráfico anterior e o atual: os itens que entraram e saíram (pelos identificadores) e a
    frase-resumo do motor de cada um, sem comparar valores por conta própria."""
    combinado = {"atual": body, "anterior": anterior, "itens": [], "indicador": body["indicador"], "notas": []}
    c = Composicao(combinado)
    antes = {item["id"] for item in anterior.get("itens") or []}
    agora = {item["id"] for item in body.get("itens") or []}
    entraram = [i for i, item in enumerate(body["itens"]) if item["id"] not in antes]
    sairam = [i for i, item in enumerate(anterior["itens"]) if item["id"] not in agora]
    if entraram:
        c.text("Entraram no gráfico: ")
        for k, indice in enumerate(entraram[:8]):
            c.text(", " if k else "").label("atual", "itens", indice, "rotulo")
        c.text(". ")
    if sairam:
        c.text("Saíram: ")
        for k, indice in enumerate(sairam[:8]):
            c.text(", " if k else "").label("anterior", "itens", indice, "rotulo")
        c.text(". ")
    if not entraram and not sairam:
        c.text("Os territórios são os mesmos; mudou o que se pede a eles. ")
    for chave, titulo in (("anterior", "Antes"), ("atual", "Agora")):
        resumo = combinado[chave].get("resumo") or {}
        c.text("\n" + titulo + ": ")
        for parte in resumo.get("partes") or []:
            if "segmento" in parte:
                segmento = dict(resumo["segmentos"][parte["segmento"]])
                segmento["caminho"] = [chave] + list(segmento["caminho"])
                c._add(segmento)
            else:
                c.text(parte["texto"])
    if entraram:
        c.text("\n\nDo que entrou:")
        for indice in entraram[:3]:
            item = body["itens"][indice]
            c.text("\n• ").label("atual", "itens", indice, "rotulo").text(": " + body["indicador"] + " de ")
            if isinstance(item.get(body["indicador"]), (int, float)):
                c.number("atual", "itens", indice, body["indicador"]).text(unidade_de_medida(body["indicador"]))
            else:
                c.text("sem valor")
            c.text(".")
    resultado = c.resultado()
    _verifica_combinado(resultado, combinado)
    return resultado


def _verifica_combinado(composicao: dict, combinado: dict) -> None:
    for segmento in composicao["segmentos"]:
        chave = segmento["caminho"][0]
        local = dict(segmento, caminho=segmento["caminho"][1:])
        if chave not in ("atual", "anterior") or not _segmento_confere(local, vista(combinado[chave])):
            raise ComposicaoInvalida("Segmento sem correspondência no resultado: " + str(segmento.get("caminho")))
