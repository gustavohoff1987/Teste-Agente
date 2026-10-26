"""Redação opcional pelo Gemini das explicações do gestor de diálogo (desafio adversarial, 26/10/2026).

Quando a pessoa pede outra formulação ("de outro jeito", "mais simples", "de forma didática") e o provedor está
configurado, o Gemini reescreve só a parte linguística da explicação já composta e verificada (explicacao.py):
- o que vai ao provedor é o esqueleto, com todo segmento do motor e do catálogo trocado por um marcador opaco (⟦1⟧, ⟦2⟧…)
  e o tipo dele (valor, parâmetro, nome, relação, nota, forma documental), mais o registro pedido e a mensagem sanitizada;
  nenhum nome, número, competência, classe ou nota da base atravessa (política dos dados do Brasil, RQ-ARQ-06);
- o texto devolvido passa pelo validador de saída (INV-13, RQ-SIN-04) antes de qualquer exibição: cada marcador exatamente
  uma vez e nenhum outro; nenhum número novo fora dos marcadores (V-01); nenhum termo novo de causalidade (V-04), juízo
  normativo (V-03), tendência (V-05), acessibilidade (V-06), relação quantitativa (V-07), destaque (V-12) ou
  heterogeneidade (V-13) além dos que o texto verificado já tinha; nenhum nome próprio novo (V-02); tamanho limitado;
- violação provoca nova tentativa com a lista das violações, até 2 regenerações (RQ-SIN-05); persistindo, vale o texto
  determinístico verificado, com a mensagem fixa de TPL-08. O texto rejeitado nunca é exibido.
Os marcadores voltam a ser os segmentos verificados: valores, classes, relações e formas metodológicas não mudam (RQ-SIN-07);
muda a organização e o tom (RQ-SIN-08). A redação metodológica livre (paráfrase das formas do catálogo) não é feita aqui:
depende de decisão normativa (proposta registrada em Docs/DIALOGO_GOVERNADO.md).

ADT_REDACAO_GEMINI=0 desliga a redação; sem GEMINI_API_KEY ela não é tentada.
"""
from __future__ import annotations

import os
import re
import unicodedata

from document_catalog import materialize

TENTATIVAS = 3  # a primeira e até 2 regenerações (RQ-SIN-05)
MARCADOR = re.compile(r"⟦(\d{1,3})⟧")
# CFG-LEX (SPEC 4.4.15), em português, e as variações comuns de flexão.
LEXICOS = {
    "V-03 juízo normativo": r"adequad\w*|inadequad\w*|suficient\w*|insuficient\w*|deficit\w*|prioritari\w*|critic\w*|"
                            r"problematic\w*|ideal|ideais|excess\w*|carenci\w*|melhor\w*|pior\w*|bom|boa|ruim",
    "V-04 causalidade": r"causa\w*|explica\w*|devido|em razao de|leva a|levou|impacto\w*|efeito\w*|resulta\w* de|"
                        r"porque|por causa",
    "V-05 tendência": r"tendenci\w*|acelera\w*|desacelera\w*|crescimento|declinio",
    "V-06 acessibilidade": r"tempo de viagem|tempo de deslocamento|deslocamento|acesso|acessibilidade|isolamento",
    "V-07 relação quantitativa": r"maioria|maior parte|dobro|metade|maior|maiores|menor|menores|percentual|porcentagem|"
                                r"proporcao|razao|primeir\w*|segund\w*|terceir\w*",
    "V-12 destaque": r"destaca\w*|chama atencao|notavel|principal|mais importante",
    "V-13 heterogeneidade": r"heterogene\w*",
}
TIPOS = {"VALOR": "valor do motor", "PARAMETRO": "parâmetro (competência, categoria ou escala)",
         "LIMITACAO": "nota ou limitação do motor", "RELACAO": "relação calculada pelo motor",
         "ORDENACAO": "território na ordem do motor", "EXPLICACAO_METODOLOGICA": "forma documental governada (fixa)"}
SISTEMA = (
    "Você reescreve, em português do Brasil, a redação de uma explicação já pronta de um painel de diagnóstico territorial "
    "da força de trabalho em saúde. O texto tem marcadores como ⟦1⟧, ⟦2⟧: cada um é um conteúdo fixo e verificado (um valor, "
    "um nome, uma competência, uma relação, uma nota ou uma forma documental) que você não vê e não pode mudar. Regras: "
    "mantenha cada marcador exatamente uma vez, sem alterar, juntar, traduzir ou inventar marcadores; não escreva números, "
    "nomes de lugares, datas nem valores fora dos marcadores; não acrescente fatos, causas, juízos (adequado, suficiente, "
    "melhor, pior), tendências, comparações nem explicações de método que não estejam no texto; pode reordenar as frases, "
    "trocar conectivos, juntar ou separar frases e ajustar o tom ao registro pedido (simples: frases curtas e palavras do dia "
    "a dia; didático: passo a passo; técnico: preciso e enxuto; objetivo: direto). Responda só o JSON do esquema."
)
ESQUEMA = {"type": "OBJECT", "properties": {"texto": {"type": "STRING"}}, "required": ["texto"]}


def ativa() -> bool:
    import llm_bridge
    return os.getenv("ADT_REDACAO_GEMINI", "1").strip() != "0" and llm_bridge._enabled()


def _dobra(texto: str) -> str:
    return "".join(c for c in unicodedata.normalize("NFD", texto.lower()) if not unicodedata.combining(c))


def esqueleto(composicao: dict) -> tuple[str, dict[str, str], dict[str, str]]:
    """O texto com os segmentos trocados por marcadores; o mapa marcador → texto verificado e marcador → tipo."""
    partes, textos, tipos = [], {}, {}
    numeros = {}
    for parte in composicao["partes"]:
        if "segmento" in parte:
            indice = parte["segmento"]
            if indice not in numeros:
                numeros[indice] = len(numeros) + 1
            marcador = "⟦" + str(numeros[indice]) + "⟧"
            textos[marcador] = parte["texto"]
            tipos[marcador] = TIPOS.get(composicao["segmentos"][indice].get("tipo"), "conteúdo fixo")
            partes.append(marcador)
        else:
            partes.append(parte["texto"])
    return "".join(partes).strip(), textos, tipos


def _livre(texto: str) -> str:
    return MARCADOR.sub(" ", texto)


def _contagens(texto: str) -> dict[str, int]:
    simples = _dobra(_livre(texto))
    return {nome: len(re.findall(r"\b(?:" + padrao + r")\b", simples)) for nome, padrao in LEXICOS.items()}


def _nomes_proprios(texto: str) -> set[str]:
    """Palavras com inicial maiúscula fora do começo de frase (possíveis nomes próprios)."""
    livre = _livre(texto)
    nomes = set()
    for encontrado in re.finditer(r"[A-ZÁÉÍÓÚÂÊÔÃÕÇ][\wÀ-ÿ'-]{2,}", livre):
        antes = livre[:encontrado.start()].rstrip()
        if antes and antes[-1] not in ".!?:;•“\n(":
            nomes.add(encontrado.group(0))
    return nomes


def validar(texto: str, original: str, marcadores: dict[str, str]) -> list[str]:
    """Violações do texto redigido contra o esqueleto verificado (vazia: o texto pode ser exibido)."""
    violacoes = []
    if not isinstance(texto, str) or not texto.strip():
        return ["texto vazio"]
    encontrados = MARCADOR.findall(texto)
    for marcador in marcadores:
        quantos = texto.count(marcador)
        if quantos != 1:
            violacoes.append(f"marcador {marcador} aparece {quantos} vez(es); deve aparecer exatamente uma")
    desconhecidos = sorted({"⟦" + n + "⟧" for n in encontrados} - set(marcadores))
    if desconhecidos:
        violacoes.append("marcadores inexistentes: " + ", ".join(desconhecidos))
    if re.search(r"[⟦⟧]", MARCADOR.sub("", texto)):
        violacoes.append("marcador incompleto ou alterado")
    numeros_novos = len(re.findall(r"\d", _livre(texto))) - len(re.findall(r"\d", _livre(original)))
    if numeros_novos > 0:
        violacoes.append("números fora dos marcadores (V-01)")
    antes, depois = _contagens(original), _contagens(texto)
    for nome, quantos in depois.items():
        if quantos > antes[nome]:
            violacoes.append("termo novo de " + nome)
    novos = _nomes_proprios(texto) - _nomes_proprios(original) - {"Análise", "Tendência", "Entenda", "Distribuição",
                                                                     "Espacial", "Rotatividade", "Detalhes", "Brasil"}
    if novos:
        violacoes.append("nomes próprios novos (V-02): " + ", ".join(sorted(novos))[:120])
    if len(_livre(texto)) > 1.8 * len(_livre(original)) + 200:
        violacoes.append("texto longo demais para a mesma explicação")
    if re.search(r"https?://|<[a-z]+|\]\(", texto):
        violacoes.append("links ou marcação não permitidos")
    return violacoes


def _sem_dados(esqueleto_: str, body: dict | None) -> bool:
    """Conferência da política dos dados antes do envio: nenhum nome de território, rótulo ou valor da resposta do motor
    aparece fora dos marcadores."""
    if not body:
        return True
    livre = _dobra(_livre(esqueleto_))
    for item in body.get("itens") or []:
        nome = _dobra(str(item.get("rotulo", "")).split(" (")[0])
        if len(nome) >= 3 and re.search(r"\b" + re.escape(nome) + r"\b", livre):
            return False
    return True


async def redigir(composicao: dict, mensagem: str, registro: str, body: dict | None = None) -> dict:
    """A explicação no registro pedido, redigida pelo Gemini e validada; ou o texto determinístico verificado (com TPL-08
    quando as tentativas se esgotam). Sempre devolve {"texto", "origem", "tentativas", "violacoes"}."""
    import llm_bridge
    base = {"texto": composicao["texto"], "origem": "DETERMINISTICA", "tentativas": 0, "violacoes": []}
    if not ativa() or not composicao.get("partes"):
        return base
    original, textos, tipos = esqueleto(composicao)
    if not _sem_dados(original, body):
        return {**base, "violacoes": ["esqueleto com dado da base fora dos marcadores: redação não enviada"]}
    pedido = llm_bridge._finish(mensagem)  # números e nomes protegidos, como nas mensagens ao intérprete
    violacoes: list[str] = []
    for tentativa in range(1, TENTATIVAS + 1):
        entrada = ("REGISTRO: " + registro + "\nPEDIDO_SANITIZADO: " + pedido + "\nMARCADORES: " +
                   "; ".join(m + " = " + t for m, t in tipos.items()) + "\nTEXTO:\n" + original)
        if violacoes:
            entrada += "\nVIOLACOES_DA_TENTATIVA_ANTERIOR: " + "; ".join(violacoes)
        try:
            saida = await llm_bridge.generate_structured(SISTEMA, [entrada], ESQUEMA)
        except llm_bridge.LLMError as exc:
            return {**base, "tentativas": tentativa, "violacoes": ["provedor indisponível: " + str(exc)]}
        texto = saida.get("texto") if isinstance(saida, dict) else None
        violacoes = validar(texto or "", original, textos)
        if not violacoes:
            final = MARCADOR.sub(lambda m: textos["⟦" + m.group(1) + "⟧"], texto.strip())
            return {"texto": final, "origem": "REDACAO_GEMINI_VALIDADA", "tentativas": tentativa, "violacoes": []}
    aviso = materialize("DOC:TPL-08", form="mensagem", evidence="REGENERACAO_ESGOTADA")["text"]
    return {"texto": composicao["texto"] + "\n\n" + aviso, "origem": "DETERMINISTICA", "tentativas": TENTATIVAS,
            "violacoes": violacoes}
