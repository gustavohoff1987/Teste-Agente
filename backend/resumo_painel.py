"""Frase-resumo da página única de análise (POST /api/painel com `nivel`; Docs/PAINEL_INTEGRADO.md, seção "Frase-resumo").

Modelo: a frase-resumo de /api/analyze (result_summary.py, decisão D7 de 19/10/2026) e a verificação de segmentos da
conversa sobre resultados (result_conversation.verify_segment). A frase só tem texto fixo de modelos fechados e segmentos
copiados de caminhos da própria resposta; cada segmento é conferido contra o caminho antes de a frase sair (verify), e a
frase inteira é omitida se um deles não confere. Nada é calculado aqui: as contagens e os extremos (a unidade de menor e a
de maior valor) vêm do motor (painel.summary_facts), as classes, grupos, faixas e condições são as contagens do motor, e as
relações da comparação são as que o motor devolveu (comparacao.diferencas, maior e menor).

Regras de redação (SPEC, CFG-LEX e Parte 13; as mesmas de tests/test_result_summary.py):
- sem LEX-DES, LEX-NORM e LEX-CAU; LEX-CMP só nas relações copiadas do motor;
- termos de LEX-TEN só quando a resposta traz a tendência (CAP-TEN-01);
- a taxa do Brasil é referência de contexto: nunca "acima" ou "abaixo", nunca classifica nem colore os itens;
- números pela regra de apresentação (RQ-REP-05): duas casas nas medidas contínuas, contagens inteiras (com separador de
  milhar), mais casas só para preservar a relação entre valores comparados na mesma frase (de quanto a quanto, os itens da
  comparação); escala e unidade junto da densidade ("por 1.000 habitantes");
- conjuntos com a soma das contagens dos componentes, com possível dupla contagem; estados com a ressalva da fonte
  estadual já usada nas notas.

O resumo fica em `resumo` da resposta, só para a interface; nada dele vai ao provedor de IA. Uma falha ao compô-lo nunca
derruba a resposta (main.py registra no log e omite o campo).
"""
from __future__ import annotations

from decimal import Decimal, ROUND_HALF_UP, localcontext

from nearest_reference import TPL_11
from result_conversation import resolve
from territorial_levels import NOTE_STATES, human_period, thousands

VERSION = 1
DENSITY_UNIT = "por 1.000 habitantes"
RELATIONS = {"MAIOR": "maior que", "MENOR": "menor que", "IGUALDADE": "igual ao"}
INDICATOR_TEXT = {"densidade": "densidade", "quantidade": "quantidade"}
NOTE = "Frase composta só com valores, relações e contagens do motor, copiados da resposta e conferidos; nada é calculado na tela."


# --------------------------------------------------------------------------------------------- apresentação
def number(value, places=2) -> str:
    """Número da frase (RQ-REP-05): contagem inteira com separador de milhar; medida contínua com `places` casas, com o
    arredondamento da apresentação de result_conversation.display (meio para cima sobre o decimal mais curto do valor;
    mais casas quando o valor arredondaria para zero)."""
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise TypeError("Valor não numérico na frase-resumo.")
    if isinstance(value, int):
        return thousands(value)
    with localcontext() as context:
        context.prec = 400
        original = Decimal(str(value))
        while original and original.quantize(Decimal(1).scaleb(-places), rounding=ROUND_HALF_UP) == 0:
            places += 1
        rounded = original.quantize(Decimal(1).scaleb(-places), rounding=ROUND_HALF_UP)
    return format(rounded, ",f").replace(",", "_").replace(".", ",").replace("_", ".")


def places_for(values) -> int:
    """Casas comuns de valores comparados na mesma frase: duas, ou mais só quando dois valores diferentes ficariam com o
    mesmo texto (preservar a relação, RQ-REP-05)."""
    places = 2
    while places < 17 and any(a != b and number(a, places) == number(b, places)
                              for a in values for b in values if isinstance(a, float) or isinstance(b, float)):
        places += 1
    return places


def _join(parts):
    parts = list(parts)
    return parts[0] if len(parts) == 1 else ", ".join(parts[:-1]) + " e " + parts[-1]


def relation_text(body, path):
    """Texto de uma relação da comparação, montado só com o que o motor devolveu (como result_conversation.relation_text):
    a relação A/B entre dois itens (comparacao.diferencas) ou os itens de maior e de menor valor (comparacao.maior e
    menor, com empates)."""
    comparison = body["comparacao"]
    labels = {item["id"]: item["rotulo"] for item in comparison["itens"]}
    if len(path) == 3 and path[:2] == ["comparacao", "diferencas"]:
        entry = resolve(body, path)
        relation = RELATIONS.get(entry["relacao"])
        if relation is None:
            return None
        if entry["relacao"] == "IGUALDADE":
            return "O valor de " + labels[entry["a"]] + " é igual ao de " + labels[entry["b"]] + "."
        return "O valor de " + labels[entry["a"]] + " é " + relation + " o de " + labels[entry["b"]] + "."
    if path in (["comparacao", "maior"], ["comparacao", "menor"]) and comparison[path[1]]:
        return path[1] + " valor: " + _join(labels[key] for key in comparison[path[1]])
    return None


# --------------------------------------------------------------------------------------------- composição
class Composer:
    """Monta a frase em partes: texto fixo dos modelos e segmentos copiados de caminhos da resposta."""

    def __init__(self, body: dict):
        self.body = body
        self.parts: list[dict] = []
        self.segments: list[dict] = []

    def text(self, value: str) -> "Composer":
        if value:
            self.parts.append({"texto": value})
        return self

    def _add(self, segment: dict) -> "Composer":
        self.segments.append(segment)
        self.parts.append({"texto": segment["texto"], "segmento": len(self.segments) - 1, "tipo": segment["tipo"],
                           "caminho": segment["caminho"]})
        return self

    def number(self, *path, places=2, kind="VALOR") -> "Composer":
        value = resolve(self.body, list(path))
        segment = {"tipo": kind, "formato": "numero", "caminho": list(path), "texto": number(value, places)}
        if isinstance(value, float):
            segment["casas"] = places
        return self._add(segment)

    def count(self, singular: str, plural: str, *path) -> "Composer":
        """Contagem copiada da resposta seguida do substantivo no singular ou no plural (concordância, não cálculo)."""
        self.number(*path)
        return self.text(" " + (singular if resolve(self.body, list(path)) == 1 else plural))

    def label(self, *path, kind="PARAMETRO") -> "Composer":
        return self._add({"tipo": kind, "formato": "texto", "caminho": list(path),
                          "texto": resolve(self.body, list(path))})

    def period(self, *path) -> "Composer":
        return self._add({"tipo": "PARAMETRO", "formato": "competencia", "caminho": list(path),
                          "texto": human_period(resolve(self.body, list(path)))})

    def note(self, index: int) -> "Composer":
        return self._add({"tipo": "LIMITACAO", "formato": "texto", "caminho": ["notas", index],
                          "texto": self.body["notas"][index]})

    def relation(self, *path) -> "Composer":
        text = relation_text(self.body, list(path))
        if text is None:
            return self
        return self._add({"tipo": "RELACAO", "formato": "relacao", "caminho": list(path), "texto": text})

    def range(self, extremes, field, unit="", each="") -> "Composer":
        """"de X a Y unidade": cópias do valor da unidade de menor e da de maior valor (posições do motor), com as mesmas
        casas; `each` vai depois de cada número (o sinal de %), `unit` só no fim."""
        low, high = (resolve(self.body, ["itens", index] + field) for index in extremes)
        places = places_for([low, high])
        self.text("de ").number("itens", extremes[0], *field, places=places).text(each + " a ")
        return self.number("itens", extremes[1], *field, places=places).text(each + unit)

    @property
    def sentence(self) -> str:
        return "".join(part["texto"] for part in self.parts)


def _note_index(body, text):
    return next((index for index, note in enumerate(body.get("notas") or []) if note == text), None)


def _units(body):
    """Nome das unidades do gráfico: municípios (ou o nome da planilha) e, no nível estados, os estados."""
    rotulos = body["rotulos"]
    unit = rotulos["grupo"] if body["nivel"] == "estados" else rotulos["unidade"]
    return unit["singular"], unit["plural"], "as" if unit.get("genero") == "f" else "os"


def _lead(c: Composer, body: dict, facts: dict):
    singular, plural, article = _units(body)
    indicator = body["indicador"]
    unit = " " + DENSITY_UNIT if indicator == "densidade" else ""
    c.text("Em ").period("competencia").text(", o gráfico tem ").count(singular, plural, "resumo", "contagens", "unidades")
    if facts["contagens"]["conjuntos"]:
        c.text(" e ").count("conjunto", "conjuntos", "resumo", "contagens", "conjuntos")
    c.text(".")
    extremes = facts["extremos"]["indicador"]
    if extremes is None:
        c.text(" Sem valor de " + INDICATOR_TEXT[indicator] + " em ").count(singular, plural, "resumo", "contagens",
                                                                          "sem_valor").text(".")
        return
    c.text(" Entre " + article + " " + plural + ", a " + INDICATOR_TEXT[indicator] + " vai ")
    c.range(extremes, [indicator], unit).text("; ").count(singular, plural, "resumo", "contagens", "sem_valor") \
        .text(" sem valor.")


def _bands(c: Composer, body: dict, key: str, title: str, missing: str):
    bands = body[key]
    c.text(" " + title + ": ")
    for index in range(len(bands["rotulos"])):
        c.text("; " if index else "").label(key, "rotulos", index).text(", ").number(key, "contagens", index)
    c.text("; fora das faixas, ").number(key, "fora").text("; " + missing + ", ").number(key, "nao_avaliaveis").text(".")


def _groups(c: Composer, body: dict):
    c.text(" Grupos por posição (").label("grupos", "tipo").text("): ")
    for index in range(len(body["grupos"]["rotulos"])):
        c.text("; " if index else "").label("grupos", "rotulos", index).text(", ").number("grupos", "contagens", index)
    c.text("; sem valor, ").number("grupos", "nao_avaliaveis").text(".")


def _change(c: Composer, body: dict, facts: dict):
    singular, plural, _ = _units(body)
    indicator = body["indicador"]
    c.text(" Variação de " + INDICATOR_TEXT[indicator] + " entre ").period("competencia_inicial").text(" e ") \
        .period("competencia").text(": ")
    extremes = facts["extremos"]["variacao"]
    if extremes is not None:
        c.range(extremes, ["variacao_percentual", indicator], each="%").text("; ")
    c.count(singular, plural, "resumo", "contagens", "sem_variacao").text(" sem variação avaliável.")


def _spatial(c: Composer, body: dict, facts: dict):
    singular, plural, _ = _units(body)
    members = body["referencia"]["membros"]
    c.text(" Distância em linha reta até " + ("a referência " if len(members) == 1 else
                                              "o membro mais próximo da referência ("))
    for index in range(len(members)):
        c.text(", " if 0 < index < len(members) - 1 else " e " if index else "").label("referencia", "membros", index,
                                                                                         "rotulo")
    c.text(": " if len(members) == 1 else "): ")
    extremes = facts["extremos"]["distancia"]
    if extremes is not None:
        c.range(extremes, ["distancia_km"], " km").text("; ")
    c.count(singular, plural, "resumo", "contagens", "sem_distancia").text(" sem distância.")
    if body.get("faixas_distancia") is not None:
        _bands(c, body, "faixas_distancia", "Faixas de distância (km)", "sem distância")
    note = _note_index(body, TPL_11)
    if note is not None:
        c.text(" ").note(note)


def _trend(c: Composer, body: dict):
    trend = body["tendencia"]
    c.text(" Tendência na janela de ").period("tendencia", "janela", "inicio").text(" a ") \
        .period("tendencia", "janela", "fim").text(": ")
    if trend.get("bloqueio"):
        c.label("tendencia", "bloqueio", "texto", kind="LIMITACAO")
        return
    c.text("família do crescimento, ").number("tendencia", "familias", "CRESCIMENTO") \
        .text("; família do declínio, ").number("tendencia", "familias", "DECLINIO") \
        .text("; sem classificação, ").number("tendencia", "familias", "NENHUMA") \
        .text("; não avaliável, ").number("tendencia", "nao_avaliaveis").text(".")


def _conditions(c: Composer, body: dict):
    c.text(" Condições ").label("condicoes", "descricao").text(": atendem, ") \
        .number("condicoes", "contagens", "ATENDE").text("; não atendem, ") \
        .number("condicoes", "contagens", "NAO_ATENDE").text("; sem dado, ") \
        .number("condicoes", "contagens", "NAO_AVALIAVEL").text(".")


def _comparison(c: Composer, body: dict):
    comparison = body["comparacao"]
    indicator = body["indicador"]
    unit = " " + DENSITY_UNIT if indicator == "densidade" else ""
    position = {item["id"]: index for index, item in enumerate(comparison["itens"])}
    if comparison["diferencas"]:
        entry = comparison["diferencas"][0]
        shown = [position[entry["a"]], position[entry["b"]]]
    elif comparison["maior"]:
        shown = [index for index, item in enumerate(comparison["itens"]) if item["valor"] is not None]
    else:
        if comparison["notas"]:
            c.text(" Comparação: ").label("comparacao", "notas", 0, kind="LIMITACAO")
        return
    places = places_for([comparison["itens"][index]["valor"] for index in shown])
    c.text(" Comparação de " + INDICATOR_TEXT[indicator] + ": ")
    for order, index in enumerate(shown):
        c.text("; " if order else "").label("comparacao", "itens", index, "rotulo", kind="VALOR").text(", ") \
            .number("comparacao", "itens", index, "valor", places=places)
    if comparison["diferencas"]:
        c.text(unit + ". ").relation("comparacao", "diferencas", 0).text(" Diferença A − B: ") \
            .number("comparacao", "diferencas", 0, "diferenca").text(unit + ".")
    else:
        c.text(unit + "; ").relation("comparacao", "maior").text("; ").relation("comparacao", "menor") \
            .text("; sem diferenças automáticas entre pares.")


def _rotation(c: Composer, body: dict, facts: dict):
    singular, plural, _ = _units(body)
    c.text(" Permanência da coorte inicial entre ").period("rotatividade", "inicial").text(" e ") \
        .period("rotatividade", "final").text(": ")
    extremes = facts["extremos"]["permanencia"]
    if extremes is not None:
        c.range(extremes, ["rotatividade", "permanencia_percentual"], each="%").text("; ")
    c.count(singular, plural, "resumo", "contagens", "sem_permanencia").text(" sem permanência avaliável.")


def _context(c: Composer, body: dict):
    line = (body.get("contexto") or {}).get("brasil")
    if body["indicador"] != "densidade" or not line or line.get("densidade") is None:
        return
    c.text(" Referência de contexto: taxa nacional de ").number("contexto", "brasil", "densidade", kind="PARAMETRO") \
        .text(" " + DENSITY_UNIT + " (Brasil, total nacional); não classifica nem colore os itens do gráfico.")


def compose(body: dict, facts: dict) -> Composer:
    """A frase de uma resposta da página única, na ordem das análises: itens e indicador (distribuição), grupos e faixas,
    mudança, análise espacial, tendência, condições, comparação, rotatividade, ressalvas (conjuntos e estados) e a linha de
    contexto do Brasil. Os grupos que pintam o mapa (`grupos_mapa`, pedidos pela tela junto com toda análise) não entram:
    a frase descreve o que o gráfico mostra, e é a mesma com ou sem eles."""
    view = {**body, "resumo": {"contagens": facts["contagens"]}}  # os caminhos como ficam na resposta
    c = Composer(view)
    _lead(c, view, facts)
    if view.get("grupos") is not None:
        _groups(c, view)
    if view.get("faixas") is not None:
        _bands(c, view, "faixas", "Faixas de " + INDICATOR_TEXT[view["indicador"]], "sem valor")
    if view.get("competencia_inicial"):
        _change(c, view, facts)
    if view.get("referencia") is not None:
        _spatial(c, view, facts)
    if view.get("tendencia") is not None:
        _trend(c, view)
    if view.get("condicoes") is not None:
        _conditions(c, view)
    if view.get("comparacao") is not None:
        _comparison(c, view)
    if view.get("rotatividade") is not None:
        _rotation(c, view, facts)
    if facts["contagens"]["conjuntos"]:
        c.text(" Conjuntos: soma das contagens dos componentes, com possível dupla contagem.")
    if view["nivel"] == "estados":
        note = _note_index(view, NOTE_STATES)
        if note is not None:
            c.text(" ").note(note)
    _context(c, view)
    return c


# --------------------------------------------------------------------------------------------- verificação
def verify_segment(segment: dict, body: dict) -> bool:
    """Um segmento é cópia literal do caminho na resposta, na regra de apresentação do seu formato, ou a relação do
    motor (o mesmo princípio de result_conversation.verify_segment)."""
    try:
        if set(segment) - {"tipo", "formato", "caminho", "texto", "casas"} or not segment["caminho"]:
            return False
        path = segment["caminho"]
        if segment["formato"] == "relacao":
            return segment["tipo"] == "RELACAO" and segment["texto"] == relation_text(body, path)
        value = resolve(body, path)
        if segment["formato"] == "numero":
            places = segment.get("casas", 2)
            return (isinstance(value, (int, float)) and not isinstance(value, bool) and
                    ("casas" in segment) == isinstance(value, float) and segment["texto"] == number(value, places))
        if segment["formato"] == "competencia":
            return isinstance(value, str) and segment["texto"] == human_period(value)
        if segment["formato"] == "texto":  # nome ou nota como está na resposta; notas e bloqueios são LIMITACAO
            return isinstance(value, str) and segment["texto"] == value and \
                (segment["tipo"] == "LIMITACAO") == ("notas" in path or "bloqueio" in path)
        return False
    except (KeyError, IndexError, TypeError, ValueError):
        return False


def verify(body: dict) -> bool:
    """O resumo da resposta: todos os segmentos conferem, e as partes, na ordem, são o texto (cada parte de segmento é o
    próprio segmento)."""
    resumo = body.get("resumo")
    try:
        segments, parts = resumo["segmentos"], resumo["partes"]
        if not segments or "".join(part["texto"] for part in parts) != resumo["texto"]:
            return False
        for part in parts:
            if "segmento" in part:
                segment = segments[part["segmento"]]
                if (part["texto"], part["caminho"], part["tipo"]) != (segment["texto"], segment["caminho"],
                                                                     segment["tipo"]):
                    return False
        return all(verify_segment(segment, body) for segment in segments)
    except (KeyError, IndexError, TypeError):
        return False


def summary(body: dict, facts: dict) -> dict | None:
    """Resumo da resposta da página única: frase em partes verificadas e as contagens do motor que ela copia. None quando
    um segmento não confere (a frase não sai)."""
    composer = compose(body, facts)
    out = {"versao": VERSION, "texto": composer.sentence, "partes": composer.parts, "segmentos": composer.segments,
           "contagens": facts["contagens"], "nota": NOTE}
    return out if verify({**body, "resumo": out}) else None
