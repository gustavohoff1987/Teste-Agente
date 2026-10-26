"""Conferência de fidelidade do texto redigido pelo Gemini antes de qualquer exibição (INV-13, RQ-SIN-04 a RQ-SIN-06,
RQ-SIN-10 e Adendo PAR-20261026), 26/10/2026.

O texto só aparece se não tiver violação. A conferência não confia na própria concordância do modelo nem em coincidência
de palavras; ela olha a função de cada frase:
- V-01: todo número (algarismos e numerais por extenso) existe no contexto verificado (resultado em exibição, fatos do
  gestor, fichas, mensagens da conversa), com o mesmo valor; arredondar de outro jeito é mudar o valor;
- V-02: todo nome próprio está no contexto (territórios do resultado, unidades federativas, o que a pessoa escreveu, os
  nomes da tela);
- V-03, V-04, V-06, V-13 e projeção: juízo normativo, causa, acesso, heterogeneidade e previsão só aparecem em frase
  negativa (a ressalva, "não mede acesso"); conectivos causais só quando a frase fala do cálculo, não do fenômeno;
- V-05: classe de tendência atribuída a um território tem de ser a classe que o motor deu a ele;
- V-07: "maior", "menor", "acima de" sobre um território e um indicador conferem com a ordem e os valores do motor;
- V-14 e V-15: distância com a ressalva de linha reta; conjunto agregado com a soma e a possível dupla contagem;
- paráfrase metodológica: quem explica um conceito conserva os elementos essenciais da ficha (variáveis, operação,
  unidade, condição) e não faz as afirmações que a ficha proíbe (distância por estrada, densidade como suficiência,
  variação como causa, grupos de tamanho igual, critério de classe diferente do motor);
- ação: o texto não diz que abriu, mudou, calculou ou criou algo que a resposta não fez;
- forma: sem marcadores de proteção desconhecidos, sem links, sem marcação, tamanho limitado.
Na dúvida que não se resolve pelo contexto, a conferência rejeita (RQ-SIN-06).
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field

import definicoes
import triagem
from territorial_selection import STATES

LIMITE_DE_CARACTERES = 2400
NEGACAO = re.compile(r"\b(?:nao|nem|sem|nunca|jamais|nenhum\w*|tampouco|impede\w*|evite|evitar)\b")
NUMERO = re.compile(r"(?<![\w.,/-])[-−]?\d+(?:\.\d{3})*(?:,\d+)?(?:\.\d+)?(?![\w/]|-[A-Za-z])")
# Valor com a unidade de um indicador ("16 por 1.000 habitantes", "500 profissionais", "40 km"); a escala ("por 1.000
# habitantes", "a cada 1.000 habitantes") não é valor.
COM_UNIDADE = re.compile(r"(?<!por\s)(?<!cada\s)(" + NUMERO.pattern + r")\s*(?:por\s+(?:1\.000|mil)\s+habitantes|"
                         r"habitantes|profissionais|pessoas|km\b|quil[oô]metros|%|por\s*cento)", re.I)
# Números de lista e de passo ("1.", "2)", "passo 1", "3º") organizam o texto; não são valores.
ENUMERACAO = re.compile(r"(?mi)^\s*\d{1,2}[.)]\s|\b(?:passo|etapa|item|ponto|parte)\s+\d{1,2}\b|\b\d{1,2}[ºª]")
CODIGO = re.compile(r"\b[A-Z]{2,4}(?:-[A-Z]{2,4})?-\d{1,3}(?:\.\d+)?\b|\bDOC:[\w.-]+")
EXTENSO = {"dois": 2, "duas": 2, "tres": 3, "quatro": 4, "cinco": 5, "seis": 6, "sete": 7, "oito": 8, "nove": 9, "dez": 10,
           "onze": 11, "doze": 12, "treze": 13, "quinze": 15, "vinte": 20, "trinta": 30, "cem": 100, "cento": 100}
ATRIBUTOS = (("densidade", r"densidade\w*|por (?:1\.?000|mil) habitantes"), ("quantidade", r"quantidade\w*|profissionais|medic\w*"),
             ("populacao", r"populac\w*|habitantes|populos\w*"), ("distancia_km", r"distancia\w*|longe|perto|proxim\w*"),
             ("variacao", r"variac\w*"), ("permanencia", r"permanencia|rotatividade"))
MAIOR = r"\b(?:maior(?:es)?|mais alt[oa]s?|lider\w*|supera\w*|acima d[eoa]s?|na frente|topo|primeiro lugar|o mais)\b"
MENOR = r"\b(?:menor(?:es)?|mais baix[oa]s?|abaixo d[eoa]s?|atras|ultimo lugar|o menos)\b"
# Ações na tela ditas pelo próprio agente ("abri", "vou alterar"). "Inclui" fica de fora: sem acento, é também "a análise
# inclui"; "vou mostrar como ler" é explicação, não ação.
ACAO = re.compile(r"\b(?:abri|mostrei|alterei|mudei|apliquei|calculei|recalculei|criei|tirei|removi|troquei|"
                  r"selecionei|ordenei|filtrei|gerei|exportei|desfiz|voltei|ajustei|atualizei|vou (?:abrir|alterar|mudar|"
                  r"aplicar|calcular|recalcular|criar|incluir|tirar|remover|trocar|gerar|exportar)|estou (?:abrindo|calculando|"
                  r"alterando|gerando))\b")
METODOS_INEXISTENTES = re.compile(r"\b(?:correlac\w*|regress\w*|significancia estatistica|intervalo de confianca|desvio padrao|"
                                  r"media movel|modelo preditivo|machine learning|aprendizado de maquina)\b")
CAUSAL_FORTE = re.compile(definicoes.CAUSA + r"|\b(?:isso|o que|que|fator\w*) explica\w*\b|\bexplica\w* (?:a|o|essa|esse) "
                          r"(?:queda|aumento|alta|redu\w*|diferenc\w*|crescimento|declinio|variac\w*)\b")
CAUSAL_CONECTIVO = re.compile(r"\b(?:porque|por isso|por conta d|ja que|visto que|uma vez que|dai que)\b")
FENOMENO = re.compile(r"\b(?:subi\w*|sobe|caiu|cai|cresce\w*|cresci\w*|aument\w*|diminu\w*|queda|alta|declin\w*|melhor\w*|"
                      r"pior\w*|mudou|variou|tem mais|tem menos|ganhou|perdeu)\b")
FALA_DO_CALCULO = re.compile(r"\b(?:densidade|populac\w*|habitantes|formula|calcul\w*|definic\w*|classe\w*|metodo|criterio\w*|"
                             r"divid\w*|razao|velocidade\w*|corte\w*|percentil\w*|regra|motor|soma\w*|variac\w*|competenc\w*)\b")
JUIZO = re.compile(definicoes.JUIZO)
ACESSO = re.compile(definicoes.ACESSO + r"|\bacesso\b")
PROJECAO = re.compile(definicoes.PROJECAO)
HETEROGENEO = re.compile(r"\bheterogene\w*|\bdesigualdade\w*\b")
DESTAQUE = re.compile(r"\b(?:chama a atencao|notavel|notaveis|alarmante\w*|preocupante\w*|grave\w*|critic[oa]s?|"
                      r"se destac\w*|sobressa\w*|campe[aã]\w*|recordista\w*|fora da curva|outlier\w*|surpreend\w*|"
                      r"impressiona\w*)\b")  # "lidera" é ordem, conferida com as ordens do motor (MAIOR)
# "É positivo para Manaus" é juízo; "a variação foi positiva para Manaus" é o sinal de um valor do motor.
AVALIATIVO_PARA = re.compile(r"\b(?:e|foi|seria|sera|parece|sao|foram) (?:algo |muito |bem |bastante )?(?:positiv|negativ)\w* "
                             r"para\b")
SINAL_DE_VALOR = re.compile(r"\b(?:variac\w*|diferenc\w*|saldo|valor\w*|sinal|velocidade\w*)\b")
# Causa ligada ao fenômeno: "a alta reflete investimentos" (mas "a densidade reflete a relação entre profissionais e
# população" descreve o cálculo).
CAUSAL_FENOMENO = re.compile(r"\b(?:reflet\w*|fruto d|impulsion\w*|puxad\w* por|influenc\w*|contribu\w*|"
                             r"favorecid\w* por|em virtude d|por forca d)")
# Relação multiplicativa calculada pelo modelo ("mais que o dobro", "três vezes maior"): o motor não a entrega.
MULTIPLICATIVO = re.compile(r"\b(?:dobro|triplo|quadruplo|metade d|um terco d|um quarto d|"
                            r"(?:\d+(?:,\d+)?|duas|tres|quatro|cinco|seis|sete|oito|nove|dez) vezes (?:maior|menor|mais|"
                            r"menos|superior|inferior|o valor|a densidade|a taxa|a quantidade)|vezes (?:maior|menor|superior|"
                            r"inferior))")
# Construções em que "melhor" não é juízo sobre os dados ("para entender melhor", "a melhor forma de ler").
BENIGNO = re.compile(r"\b(?:entend\w*|explic\w*|compreend\w*|ver|visualiz\w*|ler|acompanh\w*|esclarec\w*|detalh\w*|"
                     r"organiz\w*|enxerg\w*|respond\w*|interpret\w*|analis\w*|conhec\w*|aproveit\w*|perceb\w*)\b"
                     r"(?: \w+){0,2} melhor\b|\bmelhor (?:forma|maneira|jeito|dizendo)\b|"
                     r"\bmais adequad\w* para (?:entender|ler|ver)\b|"
                     r"\b(?:otima|excelente|boa) (?:pergunta|duvida|observacao)\b|^\s*(?:otimo|excelente)\s*[,!.]|"
                     r"\b(?:quanto a|sobre a|em relacao a|a respeito da|a pergunta sobre a) causa\b")
CLASSES_ROTULOS = {definicoes.dobrar(r): c for c, r in definicoes.ROTULOS_DAS_CLASSES.items()}
NOMES_DA_TELA = ("entenda esta analise", "selecao de territorios", "historico", "detalhes", "tabela", "mapa", "grafico",
                 "graficos", "distribuicao", "analise espacial", "analise de tendencia", "tendencia", "rotatividade",
                 "imprimir", "pdf", "csv", "brasil", "dados do brasil", "enviar meus dados", "colunas", "desfazer",
                 "metodo e limitacoes", "gemini", "agente diagnostico territorial", "ibge", "cnes", "sus", "datasus")


def _numero(token: str) -> float | None:
    texto = token.replace("−", "-")
    try:
        if "," in texto:
            return float(texto.replace(".", "").replace(",", "."))
        if re.fullmatch(r"-?\d{1,3}(?:\.\d{3})+", texto):
            return float(texto.replace(".", ""))
        return float(texto)
    except ValueError:
        return None


def numeros_de(texto: str) -> set[float]:
    """Os valores numéricos de um texto (algarismos no formato da tela e numerais por extenso)."""
    limpo = CODIGO.sub(" ", str(texto))
    valores = {v for v in (_numero(t) for t in NUMERO.findall(limpo)) if v is not None}
    for palavra in re.findall(r"[a-z]+", definicoes.dobrar(limpo)):
        if palavra in EXTENSO:
            valores.add(float(EXTENSO[palavra]))
    return valores


def _frases(texto: str) -> list[str]:
    return [f.strip() for f in re.split(r"(?<=[.!?;:])\s+|\n+", texto) if f.strip()]


def _chave(frase: str) -> str:
    """A frase comparável: dobrada, espaços normalizados, sem marcador de lista e sem pontuação nas pontas."""
    return " ".join(definicoes.dobrar(frase).split()).strip(" •-–.;:!?")


@dataclass
class Referencias:
    """O que sustenta o texto: tudo verificado e montado pelo backend, nunca pelo modelo."""
    textos: list[str] = field(default_factory=list)       # cartão, fatos do gestor, fichas, mensagens da conversa
    nomes: set[str] = field(default_factory=set)           # nomes permitidos, dobrados ("manaus", "manaus (am)")
    itens: list[dict] = field(default_factory=list)        # {"nome", "valores": {atributo: número}, "classe"}
    ordens: dict = field(default_factory=dict)             # atributo -> {"maior": [nomes], "menor": [nomes]}
    indicador: str = "densidade"
    tem_distancia: bool = False
    tem_conjunto: bool = False
    tem_tendencia: bool = False
    acao: bool = False                                     # a resposta muda a tela (pedido do gráfico ou ação)
    fichas: list = field(default_factory=list)             # definicoes.Ficha em pauta
    pedidas: list = field(default_factory=list)            # fichas que a pergunta pede para explicar
    pergunta: str = ""
    marcadores: dict = field(default_factory=dict)         # marcador da triagem -> original (para a tela)
    fatos: str = ""                                        # a resposta verificada do sistema (a reserva)

    def numeros(self) -> set[float]:
        valores = set()
        for texto in self.textos + [self.pergunta] + [f.texto for f in self.fichas]:
            valores |= numeros_de(texto)
        for item in self.itens:
            valores |= {float(v) for v in item.get("valores", {}).values() if isinstance(v, (int, float))}
        return valores

    def numeros_dos_dados(self) -> set[float]:
        """Os números verificados sem os exemplos documentados das fichas ("10, 11, 13 e 16" ilustra a regra de uma classe;
        não é valor de território)."""
        valores = numeros_de(self.pergunta)
        for texto in self.textos:
            for ficha in definicoes.FICHAS.values():
                texto = texto.replace(ficha.texto, " ")
            valores |= numeros_de(texto)
        for item in self.itens:
            valores |= {float(v) for v in item.get("valores", {}).values() if isinstance(v, (int, float))}
        return valores


def _proximo(valor: float, permitidos: set[float]) -> bool:
    return any(abs(valor - p) <= 1e-9 * max(1.0, abs(p)) for p in permitidos)


def _nomes_permitidos(refs: Referencias) -> set[str]:
    nomes = {definicoes.dobrar(n) for n in refs.nomes}
    for _codigo, (sigla, nome) in STATES.items():
        nomes |= {definicoes.dobrar(sigla), definicoes.dobrar(nome)}
    nomes |= set(NOMES_DA_TELA) | set(CLASSES_ROTULOS)
    for texto in refs.textos + [refs.pergunta] + [f.texto for f in refs.fichas] + [f.titulo for f in refs.fichas]:
        for m in triagem.NOMINAL.finditer(texto):
            nomes.add(definicoes.dobrar(m.group(0)))
    return nomes


def _nome_ok(sequencia: str, permitidos: set[str]) -> bool:
    palavras = re.findall(r"[\wÀ-ÿ'-]+", sequencia)
    # Palavras da linguagem comum no começo ("O", "Em", "Entre") não fazem parte do nome.
    while palavras and triagem.funcional(palavras[0]):
        palavras.pop(0)
    if not palavras:
        return True
    nome = definicoes.dobrar(" ".join(palavras))
    if nome in permitidos or all(triagem.funcional(p) for p in palavras):
        return True
    return any(nome == p.split(" (")[0] or p.startswith(nome + " (") for p in permitidos)


def restaurar(texto: str, marcadores: dict) -> tuple[str, list[str]]:
    """Os marcadores da triagem que o modelo repetiu voltam a ser o que a pessoa escreveu (só na tela); marcador
    desconhecido é violação."""
    desconhecidos = []

    def troca(m):
        original = marcadores.get(m.group(0))
        if original is None:
            desconhecidos.append(m.group(0))
            return m.group(0)
        return original
    return triagem.MARCADOR.sub(troca, texto), desconhecidos


def _afirma(frase: str, padrao: re.Pattern) -> bool:
    """O padrão aparece como afirmação: fora de frase negativa e fora das construções benignas."""
    simples = BENIGNO.sub(" ", definicoes.dobrar(frase))
    return bool(padrao.search(simples)) and not NEGACAO.search(simples)


def _cita(frase_dobrada: str, nome: str) -> bool:
    return bool(re.search(r"(?<!\w)" + re.escape(nome) + r"(?!\w)", frase_dobrada))


def _itens_citados(frase_dobrada: str, refs: Referencias) -> list[dict]:
    citados = []
    for item in refs.itens:
        nome = definicoes.dobrar(item["nome"]).split(" (")[0]
        if len(nome) >= 3 and _cita(frase_dobrada, nome):
            citados.append((frase_dobrada.find(nome), item))
    return [item for _, item in sorted(citados, key=lambda par: par[0])]


def _atributo(frase_dobrada: str, padrao_default: str) -> str:
    for nome, padrao in ATRIBUTOS:
        if re.search(r"\b(?:" + padrao + r")", frase_dobrada):
            return nome
    return padrao_default


def _confere_ordens(frase: str, refs: Referencias) -> list[str]:
    simples = definicoes.dobrar(frase)
    maior, menor = re.search(MAIOR, simples), re.search(MENOR, simples)
    if not (maior or menor) or NEGACAO.search(simples):
        return []
    citados = _itens_citados(simples, refs)
    if not citados:
        return []
    atributo = _atributo(simples, refs.indicador)
    direcao = "maior" if maior and (not menor or maior.start() < menor.start()) else "menor"
    if len(citados) >= 2:
        a, b = citados[0], citados[1]
        va, vb = a["valores"].get(atributo), b["valores"].get(atributo)
        if not isinstance(va, (int, float)) or not isinstance(vb, (int, float)):
            return ["comparação de " + atributo + " sem valores no resultado (V-07)"]
        if (direcao == "maior" and not va > vb) or (direcao == "menor" and not va < vb):
            return ["comparação contrária aos valores do motor: " + a["nome"] + " × " + b["nome"] + " (V-07)"]
        return []
    ordem = refs.ordens.get(atributo) or {}
    lista = [definicoes.dobrar(n).split(" (")[0] for n in ordem.get(direcao) or []]
    nome = definicoes.dobrar(citados[0]["nome"]).split(" (")[0]
    if nome not in lista and (len(refs.itens) > 1):
        return ["“" + direcao + "” atribuído a " + citados[0]["nome"] + " sem a ordem do motor (V-07)"]
    return []


def _confere_classes(frase: str, refs: Referencias) -> list[str]:
    simples = definicoes.dobrar(frase)
    rotulos = [r for r in CLASSES_ROTULOS if r in simples]
    if not rotulos or NEGACAO.search(simples):
        return []
    citados = _itens_citados(simples, refs)
    problemas = []
    for item in citados[:1]:
        classe = item.get("classe")
        rotulo_do_item = definicoes.dobrar(definicoes.ROTULOS_DAS_CLASSES.get(classe, "")) if classe else ""
        # O rótulo mais longo citado é o atribuído ("aceleração do crescimento" contém "crescimento").
        citado = max(rotulos, key=len)
        if citado != rotulo_do_item:
            problemas.append("classe de tendência diferente da do motor para " + item["nome"] + " (V-05)")
    return problemas


DEFINICAO = (r"(?:e|sao|significa\w*|quer dizer|querem dizer|mede\w*|representa\w*|corresponde\w*|consiste\w*|"
             r"e calculad\w*|e obtid\w*|se calcula|funciona\w*|define\w*)")
DEITICO = re.compile(r"\b(?:maior|menor|mesma|mesmo|essa|esta|nessa|nesta|dessa|desta|sua|seu)\s*$")


DADO_APOS_O_VERBO = re.compile(r"\s*(?:[-−]?\d|de \d|maior|menor|mais|menos|a de|o de|a do|o do|a da|o da|igual|parecid\w*|"
                               r"semelhante\w*|alt[oa]|baix[oa]|positiv\w*|negativ\w*|nul[oa])")


def _explica(frase_dobrada: str, ficha, refs: "Referencias") -> bool:
    """A frase define o conceito da ficha: o conceito seguido de perto por um verbo de definição ("a densidade é…", "a
    aceleração significa…"). Não é definição o fato dos dados: território entre o conceito e o verbo ("a densidade de
    Manaus é…"), dêixis ("a maior densidade é…") ou valor logo depois do verbo ("a densidade é 23,50", "é maior")."""
    gatilho = definicoes._GATILHOS.get(ficha.id)
    if not gatilho:
        return False
    for m in re.finditer(r"(?:" + gatilho + r")", frase_dobrada):
        if DEITICO.search(frase_dobrada[:m.start()]):
            continue
        verbo = re.match(r"((?:\s+[\w()-]+){0,3}?)\s+" + DEFINICAO + r"\b", frase_dobrada[m.end():])
        if not verbo or _itens_citados(verbo.group(1), refs):
            continue
        if DADO_APOS_O_VERBO.match(frase_dobrada[m.end() + verbo.end():]):
            continue
        return True
    return bool(re.search(r"\b(?:o que (?:e|sao|significa)|chamamos de|define-se)\s+(?:a |o |as |os )?(?:" + gatilho + r")",
                          frase_dobrada))


def conferir(texto: str, refs: Referencias) -> list[str]:
    """As violações do texto (vazia: pode ser exibido)."""
    if not isinstance(texto, str) or not texto.strip():
        return ["texto vazio"]
    violacoes: list[str] = []
    if len(texto) > LIMITE_DE_CARACTERES:
        violacoes.append("texto longo demais para a conversa")
    # Um marcador de proteção seguido de parênteses ("[ENTIDADE_PROTEGIDA_1](AM)") não é link.
    if re.search(r"https?://|<[a-z/][^>]*>|\]\(|```|^#{1,6}\s", triagem.MARCADOR.sub("M", texto), re.M):
        violacoes.append("links ou marcação não permitidos")
    texto, desconhecidos = restaurar(texto, refs.marcadores)
    if desconhecidos:
        violacoes.append("marcadores de proteção desconhecidos: " + ", ".join(sorted(set(desconhecidos))))
    # V-01: números.
    permitidos = refs.numeros()
    sem_enumeracao = ENUMERACAO.sub(" ", texto)
    novos = sorted({v for v in numeros_de(sem_enumeracao) if not _proximo(v, permitidos)})
    if novos:
        violacoes.append("números fora do resultado verificado (V-01): " + ", ".join(
            str(int(v)) if v == int(v) else str(v) for v in novos[:6]))
    # Com a unidade de um indicador, o número tem de vir dos dados verificados, não do exemplo de uma ficha.
    dos_dados = refs.numeros_dos_dados()
    sem_fichas = sem_enumeracao
    for ficha in definicoes.FICHAS.values():
        sem_fichas = sem_fichas.replace(ficha.texto, " ")  # a ficha copiada inteira é o próprio exemplo, no lugar dele
    exemplos = sorted({v for v in (_numero(m.group(1)) for m in COM_UNIDADE.finditer(sem_fichas))
                       if v is not None and _proximo(v, permitidos) and not _proximo(v, dos_dados)})
    if exemplos:
        violacoes.append("número de exemplo documentado usado como valor (V-01): " + ", ".join(
            str(int(v)) if v == int(v) else str(v) for v in exemplos[:6]))
    # V-02: nomes próprios.
    nomes = _nomes_permitidos(refs)
    estranhos = []
    for m in triagem.NOMINAL.finditer(CODIGO.sub(" ", texto)):
        if not _nome_ok(m.group(0), nomes):
            estranhos.append(m.group(0))
    if estranhos:
        violacoes.append("nomes fora do contexto (V-02): " + ", ".join(sorted(set(estranhos))[:6]))
    if METODOS_INEXISTENTES.search(definicoes.dobrar(texto)) and any(
            _afirma(f, METODOS_INEXISTENTES) for f in _frases(texto)):
        violacoes.append("método que o sistema não tem (correlação, regressão, previsão)")
    pedido = definicoes.dobrar(refs.pergunta)
    # A frase copiada da resposta verificada ou de uma ficha não é afirmação nova: já é o texto conferido do sistema.
    verificadas = {_chave(f) for t in [refs.fatos, *(ficha.texto for ficha in refs.fichas)] for f in _frases(t)}
    for frase in _frases(texto):
        simples = definicoes.dobrar(frase)
        if _chave(frase) in verificadas:
            continue
        if _afirma(frase, JUIZO) or (_afirma(frase, AVALIATIVO_PARA) and not SINAL_DE_VALOR.search(simples)):
            violacoes.append("juízo normativo afirmado (V-03): “" + frase[:80] + "”")
        if _afirma(frase, CAUSAL_FORTE):
            violacoes.append("causa afirmada (V-04): “" + frase[:80] + "”")
        elif CAUSAL_CONECTIVO.search(simples) and not NEGACAO.search(simples) and (
                _itens_citados(simples, refs) or (FENOMENO.search(simples) and not FALA_DO_CALCULO.search(simples))):
            # "Porque" sobre um território ou sobre o fenômeno é explicação que os dados não sustentam; sobre a regra do
            # cálculo ("por isso os grupos podem ter tamanhos diferentes"), não.
            violacoes.append("explicação causal sobre o fenômeno (V-04): “" + frase[:80] + "”")
        elif _afirma(frase, CAUSAL_FENOMENO) and FENOMENO.search(simples):
            violacoes.append("causa afirmada (V-04): “" + frase[:80] + "”")
        if MULTIPLICATIVO.search(simples) and not NEGACAO.search(simples) and not any(
                m.group(0) in definicoes.dobrar(t) for m in MULTIPLICATIVO.finditer(simples) for t in refs.textos):
            violacoes.append("relação calculada fora do motor (V-07): “" + frase[:80] + "”")
        if _afirma(frase, ACESSO):
            violacoes.append("distância ou densidade tratada como acesso (V-06): “" + frase[:80] + "”")
        if _afirma(frase, PROJECAO):
            violacoes.append("previsão ou projeção (fora do método): “" + frase[:80] + "”")
        if _afirma(frase, HETEROGENEO):
            violacoes.append("heterogeneidade sem critério formal (V-13): “" + frase[:80] + "”")
        if _afirma(frase, DESTAQUE) and not DESTAQUE.search(pedido):
            violacoes.append("qualificação de destaque sem pedido (V-12): “" + frase[:80] + "”")
        violacoes += _confere_ordens(frase, refs)
        if refs.tem_tendencia:
            violacoes += _confere_classes(frase, refs)
        elif any(r in simples for r in CLASSES_ROTULOS if r not in ("crescimento", "declinio")) and \
                not NEGACAO.search(simples) and not any(f.id.startswith(("classe:", "tendencia")) for f in refs.fichas):
            violacoes.append("classe de tendência sem resultado de tendência (V-05)")
        if ACAO.search(simples) and not refs.acao and not NEGACAO.search(simples):
            violacoes.append("o texto diz que fez uma ação que a resposta não fez: “" + frase[:80] + "”")
    simples_total = definicoes.dobrar(texto)
    # V-14/V-15: ressalvas obrigatórias.
    if refs.tem_distancia and re.search(r"\bkm\b|quilometr", simples_total) and not re.search(
            r"diret\w*|linha reta|geodesic\w*|em linha", simples_total):
        violacoes.append("distância sem a ressalva de linha reta (TPL-11, V-06)")
    if refs.tem_conjunto and re.search(r"\bconjunto\b|\bagregad\w*", simples_total) and re.search(
            r"\d", texto) and not re.search(r"soma\w*", simples_total):
        violacoes.append("conjunto agregado sem dizer que é a soma das contagens (V-14)")
    # Paráfrase metodológica: os elementos essenciais e as afirmações proibidas de cada ficha explicada.
    # A ficha pedida exige os elementos essenciais quando a resposta verificada a explica (traz esses elementos); quando
    # ela só aponta "Entenda esta análise", o texto do modelo não precisa dizer mais do que ela.
    fatos = definicoes.dobrar(refs.fatos)
    explicadas = {f.id: f for f in refs.pedidas
                  if not fatos or all(re.search(r"(?:" + grupo + r")", fatos) for grupo in f.essenciais)}
    for frase in _frases(texto):
        simples = definicoes.dobrar(frase)
        if _chave(frase) in verificadas:
            continue
        for ficha in refs.fichas:
            if _explica(simples, ficha, refs):
                explicadas.setdefault(ficha.id, ficha)
    for ficha in explicadas.values():
        faltam = [grupo for grupo in ficha.essenciais if not re.search(r"(?:" + grupo + r")", simples_total)]
        if faltam:
            violacoes.append("explicação de “" + ficha.titulo + "” sem elemento essencial do método")
        for proibido in ficha.proibidos:
            padrao = re.compile(proibido)
            if any(_afirma(frase, padrao) for frase in _frases(texto)):
                violacoes.append("explicação de “" + ficha.titulo + "” com afirmação que muda o método")
                break
    return list(dict.fromkeys(violacoes))


def texto_para_exibir(texto: str, refs: Referencias) -> str:
    """O texto aprovado como aparece na tela: marcadores de volta ao original e sem ênfase de marcação."""
    restaurado, _ = restaurar(texto, refs.marcadores)
    return re.sub(r"\*\*|__", "", restaurado).strip()
