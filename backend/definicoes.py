"""Fichas de método para a paráfrase metodológica controlada (Adendo PAR-20261026 da SPEC), 26/10/2026.

Cada ficha diz, para um conceito que a conversa explica:
- `texto`: a formulação autorizada em linguagem simples, coerente com o motor e com as formas do catálogo governado
  (`docs`, CFG-DOC). É o que o Gemini recebe para explicar com outras palavras e o que aparece quando uma paráfrase não
  passa na conferência (resposta de reserva);
- `essenciais`: os elementos que toda explicação do conceito precisa conservar (variáveis, operação, unidade, condição).
  Cada elemento é um grupo de alternativas; a explicação precisa ter ao menos uma alternativa de cada grupo;
- `proibidos`: afirmações que mudariam o significado (distância por estrada, densidade como suficiência, variação como
  causa, grupos de tamanho igual, critério de classe diferente do motor). Só valem quando afirmadas: a mesma palavra numa
  frase negativa ("não mede acesso") é a própria ressalva e é permitida.
A conferência (fidelidade.py) usa as fichas; nenhuma ficha cria método, classe, critério ou fórmula: elas só descrevem, em
palavras simples, o que o motor já faz. As descrições das classes de tendência são as mesmas da tela ("Entenda esta
análise", painelModel.DESCRICAO_DAS_CLASSES), conferidas por teste.

Os padrões são escritos sobre o texto dobrado (minúsculas, sem acentos).
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field

# Afirmações que nenhuma explicação de método pode fazer (V-03, V-04, V-06; projeção e juízo).
CAUSA = r"\b(?:causa\w*|causou|devid[oa] a|por causa|em razao d|em funcao d|resultado d[aeo]s? (?:politica|programa|investimento)|" \
        r"efeito d|impacto d|levou a|provocou|fez (?:subir|cair|crescer|diminuir)|gra[cç]as a|se deve|deve-se a|" \
        r"relacionad\w* (?:a|ao|aos|as|com)|associad\w* (?:a|ao|aos|as|com)|atribu\w* a|explicad\w* por|motivad\w* por|" \
        r"decorr\w*|consequencia d|reflexo d|fatores?\b|pode (?:ter sido|estar ligad\w*|refletir)|provavelmente|" \
        r"possivelmente|talvez (?:porque|por)|hipotes\w*)"
JUIZO = r"\b(?:suficien\w*|insuficien\w*|adequad\w*|inadequad\w*|carenc\w*|deficit\w*|excess\w*|ideal|ideais|" \
        r"prioritari\w*|melhor\w*|pior\w*|ruim|ruins|bom desempenho|mau desempenho|satisfatori\w*|insatisfatori\w*|" \
        r"precari\w*|deficien\w*|confortave\w*|desconfortave\w*|favorave\w*|desfavorave\w*|excelente\w*|otim[oa]s?|" \
        r"pessim[oa]s?|escass\w*|abundan\w*|desassist\w*|vazios? assistenc\w*|de sobra|sobra(?:m)? (?:de )?medic\w*|" \
        r"falta(?:m)? (?:de )?(?:medic|profission|enfermeir|dentist)\w*|" \
        r"situacao (?:boa|ruim|favoravel|desfavoravel|confortavel|delicada|dificil|precaria|tranquila|positiva|negativa)|" \
        r"(?:resultado|desempenho|cenario|quadro|noticia)s? (?:positiv|negativ|bom|boa|ruim)\w*|" \
        r"(?:bom|boa|positiv\w*|negativ\w*) (?:resultado|desempenho|cenario|quadro|noticia)|" \
        r"se saiu (?:bem|mal)|saiu-se (?:bem|mal)|" \
        r"(?:bem|mal) (?:servid|atendid|abastecid|equipad|assistid|posicionad|colocad)\w*)\b"
ACESSO = r"\b(?:estradas?|rodovi\w*|viari\w*|tempo de (?:viagem|deslocamento|espera)|percurso|trajeto|de carro|" \
         r"de barco|de onibus|horas? de viagem|acessibilidade|acesso real|acesso aos? servic\w*|chegar ao|filas? de espera|" \
         r"(?:encontr|consegu|obt)\w* (?:um |uma )?(?:medic\w*|atendimento|consulta)|atendimento garantido|" \
         r"cobertura (?:assistencial|de saude|de atendimento))\b"
# Previsão: movimento futuro dos valores ("vai passar de", "deve chegar a", "tende a se manter", "nesse ritmo"), não
# instruções de uso ("você deve voltar à aba", "os botões vão continuar funcionando").
_MOVIMENTO = r"(?:crescer|cair|subir|diminuir|aumentar|chegar a|chegar ao|atingir|ultrapassar|superar|alcancar|dobrar|" \
             r"passar de|(?:continuar|seguir) (?:a )?(?:subi\w*|cai\w*|cresce\w*|aumenta\w*|diminui\w*|em alta|em queda)|" \
             r"manter (?:o ritmo|a alta|a queda|o crescimento|a tendencia))"
PROJECAO = r"\b(?:(?:vai|vao|deve|devem|devera|deverao|tende|tendem|tendera|tenderao) (?:a )?(?:se )?" + _MOVIMENTO + \
           r"|(?:tende|tendem|tendera|tenderao) a (?:se )?(?:manter|ficar|permanecer|estabilizar)" \
           r"|a tendencia e (?:de )?(?:a )?" + _MOVIMENTO + \
           r"|espera-se|e esperad[oa] que|esperad[oa] que|provavel que (?:suba|caia|cresca|continue|aumente|diminua)" \
           r"|continuara (?:a )?(?:subi|cai|cresce|aumenta|diminui)\w*|continuara em (?:alta|queda)" \
           r"|crescera|caira|subira|aumentara|diminuira|chegara ao?|atingira|ultrapassara|superara|alcancara" \
           r"|previs\w*|projec\w*|no futuro|proxim[oa]s? (?:anos?|meses|semestres?|competencias?)|ano que vem|daqui a" \
           r"|(?:nesse|neste|no mesmo|mantido o|mantido esse|mantendo esse|mantendo o) ritmo|se continuar assim)\b"
FALTA_DE_DADOS = r"\b(?:falta de dados|sem dados|dados insuficientes|nao ha dados|ausencia de dados)\b"

SUBIR = r"subi\w*|sobe|alta|altas|aument\w*|cresc\w*"
CAIR = r"cai\w*|caiu|queda|quedas|diminu\w*|reduz\w*|redu[cç]\w*|declin\w*|baix\w*"
TODOS = r"todos os periodos|cada periodo|todo periodo|em todos|sempre|cada intervalo|todos os intervalos|" \
        r"em cada (?:passo|etapa)|periodo a periodo"
MAIS_RITMO = r"maior|maiores|ganh\w* ritmo|aceler\w*|mais rapid\w*|cada vez mais|ritmo (?:maior|crescente)"
MENOS_RITMO = r"menor|menores|perd\w* ritmo|desaceler\w*|mais devagar|mais lent\w*|ritmo menor|cada vez menos"


@dataclass(frozen=True)
class Ficha:
    id: str
    titulo: str
    termos: tuple[str, ...]
    texto: str
    essenciais: tuple[str, ...] = ()
    proibidos: tuple[str, ...] = ()
    docs: tuple[str, ...] = field(default=())


# Descrições das classes de tendência: as mesmas de frontend/src/painelModel.ts (DESCRICAO_DAS_CLASSES), conferidas por
# teste (test_fidelidade.py). Não criam classe nem critério; dizem em palavras a regra do motor (trend.classify_speeds).
DESCRICAO_DAS_CLASSES = {
    "CRESCIMENTO": "o indicador subiu e não caiu em nenhum período, mas sem ganhar nem perder ritmo de forma contínua: houve "
                   "uma pausa, ou as altas foram do mesmo tamanho, ou ora maiores, ora menores. Exemplo: 10, 12, 12 e 15.",
    "CRESCIMENTO_ACELERADO": "o indicador subiu em todos os períodos, e cada alta foi do mesmo tamanho ou maior que a "
                             "anterior, com pelo menos uma maior: o crescimento ganhou ritmo. Exemplo: 10, 11, 13 e 16 (altas "
                             "de 1, 2 e 3).",
    "CRESCIMENTO_DESACELERADO": "o indicador subiu em todos os períodos, mas cada alta foi do mesmo tamanho ou menor que a "
                                "anterior, com pelo menos uma menor: continua subindo, em ritmo menor. Exemplo: 10, 13, 15 e "
                                "16 (altas de 3, 2 e 1).",
    "DECLINIO": "o indicador caiu e não subiu em nenhum período, mas sem ganhar nem perder ritmo de forma contínua: houve uma "
                "pausa, ou as quedas foram do mesmo tamanho, ou ora maiores, ora menores. Exemplo: 15, 12, 12 e 10.",
    "DECLINIO_ACELERADO": "o indicador caiu em todos os períodos, e cada queda foi do mesmo tamanho ou maior que a anterior, "
                          "com pelo menos uma maior: a queda ganhou ritmo. Exemplo: 16, 15, 13 e 10 (quedas de 1, 2 e 3).",
    "DECLINIO_DESACELERADO": "o indicador caiu em todos os períodos, mas cada queda foi do mesmo tamanho ou menor que a "
                             "anterior, com pelo menos uma menor: continua caindo, em ritmo menor. Exemplo: 16, 13, 11 e 10 "
                             "(quedas de 3, 2 e 1).",
    "SEM_CLASSIFICACAO": "o indicador subiu num período e caiu em outro (mudou de direção), ou ficou igual em todos. "
                         "Exemplos: 10, 12, 11 e 13; 10, 10, 10 e 10.",
}
ROTULOS_DAS_CLASSES = {"CRESCIMENTO": "Crescimento", "CRESCIMENTO_ACELERADO": "Aceleração do crescimento",
                       "CRESCIMENTO_DESACELERADO": "Desaceleração do crescimento", "DECLINIO": "Declínio",
                       "DECLINIO_ACELERADO": "Aceleração de declínio", "DECLINIO_DESACELERADO": "Desaceleração de declínio",
                       "SEM_CLASSIFICACAO": "Sem classificação"}
_CLASSE_PROIBIDOS = (CAUSA, PROJECAO, JUIZO)
_ESSENCIAIS_DAS_CLASSES = {
    "CRESCIMENTO": (SUBIR, r"nao (?:caiu|cai|teve queda)|sem queda|nenhuma queda|nenhum periodo",
                    r"pausa|mesmo tamanho|ora maior\w*|sem ganhar nem perder ritmo|ritmo (?:irregular|constante)|nao ganhou"),
    "CRESCIMENTO_ACELERADO": (SUBIR, TODOS, MAIS_RITMO),
    "CRESCIMENTO_DESACELERADO": (SUBIR, TODOS, MENOS_RITMO),
    "DECLINIO": (CAIR, r"nao (?:subiu|sobe|teve alta)|sem alta|nenhuma alta|nenhum periodo",
                 r"pausa|mesmo tamanho|ora maior\w*|sem ganhar nem perder ritmo|ritmo (?:irregular|constante)|nao ganhou"),
    "DECLINIO_ACELERADO": (CAIR, TODOS, MAIS_RITMO),
    "DECLINIO_DESACELERADO": (CAIR, TODOS, MENOS_RITMO),
    "SEM_CLASSIFICACAO": (r"mud\w* de direc\w*|direc\w*|subiu .{0,40}(?:caiu|desceu)|caiu .{0,40}subiu|sobe e desce|"
                          r"ficou igual|igual em todos|estavel|nao mudou|alterna\w*",),
}

FICHAS: dict[str, Ficha] = {}


def _registrar(ficha: Ficha) -> None:
    FICHAS[ficha.id] = ficha


_registrar(Ficha(
    "densidade", "Densidade por 1.000 habitantes", ("densidade", "por mil habitantes", "por 1.000 habitantes", "per capita"),
    "A densidade é o número de profissionais da categoria dividido pela população do mesmo território, na mesma "
    "competência, multiplicado por 1.000: quantos profissionais há para cada 1.000 habitantes. O motor calcula em precisão "
    "integral; o arredondamento é só da apresentação. A densidade descreve a relação entre profissionais e população; "
    "sozinha, não diz se há profissionais suficientes nem mede acesso ou qualidade do atendimento.",
    essenciais=(r"profissiona\w*|quantidade|quantitativo|medic\w*|enfermeir\w*|trabalhador\w*",
                r"populac\w*|habitantes|moradores",
                r"1\.?000|\bmil\b",
                r"divid\w*|razao|para cada|por cada|a cada|por 1\.?000|por mil|proporc\w*"),
    proibidos=(JUIZO, r"\b(?:cobertura|qualidade do atendimento|atendimento adequado)\b", r"\bacesso\b", CAUSA),
    docs=("DOC:CAP-IND-02.metodo", "DOC:CAP-IND-02.representacao")))
_registrar(Ficha(
    "quantidade", "Quantidade de profissionais", ("quantidade", "quantitativo", "numero de profissionais", "total de"),
    "A quantidade é o número absoluto de profissionais da categoria no território e na competência, contado em pessoas "
    "pela base. Não há conversão entre pessoas, vínculos e postos, e a quantidade não leva em conta o tamanho da "
    "população: para isso existe a densidade.",
    essenciais=(r"profissiona\w*|pessoas|medic\w*|enfermeir\w*|trabalhador\w*",
                r"absolut\w*|numero|contad\w*|contagem|total|quant\w*"),
    proibidos=(JUIZO, CAUSA)))
_registrar(Ficha(
    "distancia", "Distância geográfica direta", ("distancia", "geodesica", "linha reta", "km", "quilometro"),
    "A distância é a geográfica direta (geodésica), em quilômetros, entre as coordenadas dos territórios, calculada no "
    "elipsoide do referencial geodésico. Não é a distância por estrada, não é o tempo de deslocamento e não mede a "
    "acessibilidade real.",
    essenciais=(r"diret\w*|linha reta|geodesic\w*|em linha", r"\bkm\b|quilometr\w*"),
    proibidos=(ACESSO,),
    docs=("DOC:CAP-ESP-01.metodo", "DOC:TPL-11")))
_registrar(Ficha(
    "referencia", "Referência mais próxima", ("referencia mais proxima", "mais proxima", "referencia"),
    "Para cada território, o motor calcula a distância geográfica direta até cada território de referência e aponta o mais "
    "próximo; empates mantêm todas as referências empatadas. Quando alguma referência não pode ser avaliada, o mais "
    "próximo é dito “entre as referências avaliáveis”. Como toda distância daqui, é em linha reta: não é estrada, tempo de "
    "viagem nem acesso.",
    essenciais=(r"diret\w*|linha reta|geodesic\w*|em linha", r"referenc\w*", r"proxim\w*|menor distancia"),
    proibidos=(ACESSO,),
    docs=("DOC:CAP-ESP-02.metodo", "DOC:CAP-ESP-02.saida", "DOC:TPL-11")))
_registrar(Ficha(
    "grupos", "Grupos por posição (quartis, quintis e decis)", ("quintil", "quintis", "quartil", "quartis", "decil", "decis",
                                                                "grupos por posicao", "pontos de corte"),
    "Os grupos por posição (quartis, quintis ou decis: 4, 5 ou 10 grupos) dividem os valores avaliáveis do indicador por "
    "pontos de corte calculados como percentis. Um valor igual a um ponto de corte fica no grupo de baixo, e valores iguais "
    "sempre ficam no "
    "mesmo grupo, sem desempate; por isso os grupos podem ter tamanhos diferentes, inclusive vazios. Os grupos mostram a "
    "posição relativa dentro do conjunto analisado, não um padrão de qualidade.",
    essenciais=(r"corte\w*|percentil\w*|limite\w*", r"posic\w*|ordem|valores|ordenad\w*"),
    proibidos=(r"\b(?:mesmo tamanho|mesmo numero de|mesma quantidade de|numero igual de|quantidade igual de|"
               r"um quinto dos|um quarto dos|um decimo dos|20 ?% dos|25 ?% dos|10 ?% dos)\b", JUIZO),
    docs=("DOC:CAP-DIS-02.metodo",)))
_registrar(Ficha(
    "agregacao", "Conjunto agregado", ("agregacao", "agregado", "conjunto", "soma"),
    "Um conjunto agregado soma as contagens dos componentes; a densidade do conjunto é a soma das quantidades dividida pela "
    "soma das populações, nunca a média das densidades. A soma das contagens pode contar a mesma pessoa mais de uma vez "
    "(possível dupla contagem) e não representa pessoas únicas.",
    essenciais=(r"soma\w*|somad\w*", r"dupla contagem|mais de uma vez|duas vezes|sobrepos\w*|pessoas unicas|repetid\w*"),
    proibidos=(r"\bmedia das densidades\b", r"\b(?:pessoas (?:unicas|distintas)|profissionais distintos|total de pessoas)\b"),
    docs=("DOC:CAP-AGR-01.metodo",)))
_registrar(Ficha(
    "variacao", "Variação entre duas competências", ("variacao", "mudanca", "diferenca entre", "o que mudou", "aumentou",
                                                     "diminuiu"),
    "A variação compara o valor do indicador na competência final com o da competência inicial, em percentual: (final − "
    "inicial) ÷ inicial × 100. Mostra se o indicador aumentou, diminuiu ou ficou igual entre as duas competências; não "
    "explica por que mudou. Com valor inicial zero, a variação percentual não é avaliável.",
    essenciais=(r"inicial|antes|primeira|anterior", r"final|depois|ultima|atual", r"percent\w*|%"),
    proibidos=(CAUSA, JUIZO)))
_registrar(Ficha(
    "tendencia", "Análise de Tendência", ("tendencia", "classe de tendencia", "classes de tendencia", "trajetoria"),
    "A Análise de Tendência olha o indicador em 4 competências da janela escolhida e calcula a velocidade entre cada par de "
    "competências seguidas (a variação por mês, em aritmética exata). A classe sai da direção dessas velocidades (subir, "
    "cair ou mudar de direção) e de o tamanho delas crescer ou diminuir. Sem classificação é um resultado do método (mudou "
    "de direção ou ficou igual), não falta de dados. A classe descreve o que aconteceu na janela; não explica as causas nem "
    "prevê o futuro.",
    essenciais=(r"\b4\b|quatro", r"velocidade\w*|ritmo|por mes|variac\w*|alta\w*|queda\w*|subi\w*|cai\w*"),
    proibidos=(CAUSA, PROJECAO, JUIZO, FALTA_DE_DADOS)))
_registrar(Ficha(
    "velocidade", "Velocidade", ("velocidade", "velocidades", "ritmo"),
    "A velocidade é a variação do indicador entre duas competências seguidas dividida pelo número de meses entre elas (a "
    "variação por mês), calculada em aritmética exata. A classe de tendência compara a direção e o tamanho dessas "
    "velocidades.",
    essenciais=(r"\bmes\b|meses|por mes|mensal", r"variac\w*|diferenc\w*|mudanc\w*|alta\w*|queda\w*"),
    proibidos=(CAUSA, PROJECAO)))
_registrar(Ficha(
    "comparacao", "Comparação entre territórios", ("comparacao", "comparar", "lado a lado", "relacao a/b", "diferenca a"),
    "Na comparação entre dois territórios, o motor mostra os valores lado a lado, a relação A/B e a diferença assinada "
    "A − B, com A e B em ordem de nome. É uma comparação dos valores do indicador, não um juízo sobre qual está melhor nem "
    "uma explicação das causas da diferença.",
    essenciais=(r"valor\w*|densidade\w*|quantidade\w*|indicador\w*",),
    proibidos=(JUIZO, CAUSA)))
_registrar(Ficha(
    "regua", "Régua de corte", ("regua", "abaixo de", "acima de", "condicao", "condicoes", "filtro"),
    "A régua de corte (“abaixo de”, “acima de”) só filtra visualmente os valores já calculados: não cria classe, não muda "
    "o resultado e não inicia análise.",
    essenciais=(r"filtr\w*|esmaec\w*|destac\w*|mostra|visual\w*",),
    proibidos=(JUIZO,)))
_registrar(Ficha(
    "rotatividade", "Rotatividade", ("rotatividade", "permanencia", "coorte", "sairam", "ficaram"),
    "A rotatividade acompanha a coorte inicial: das pessoas presentes na competência inicial, quantas continuam na final "
    "(permanência) e quantas saíram (saída da coorte inicial). Exige um identificador da mesma pessoa entre os períodos; "
    "sem ele, não é avaliável.",
    essenciais=(r"coorte|presentes|inicial", r"permanenc\w*|continua\w*|ficaram|sairam|saida"),
    proibidos=(JUIZO, CAUSA)))
for _codigo, _descricao in DESCRICAO_DAS_CLASSES.items():
    _registrar(Ficha("classe:" + _codigo, ROTULOS_DAS_CLASSES[_codigo], (_codigo.lower(),),
                     ROTULOS_DAS_CLASSES[_codigo] + ": " + _descricao, essenciais=_ESSENCIAIS_DAS_CLASSES[_codigo],
                     proibidos=_CLASSE_PROIBIDOS + ((FALTA_DE_DADOS,) if _codigo == "SEM_CLASSIFICACAO" else ())))

# Termos do gestor de diálogo (dialogo.TERMOS) → fichas.
DO_TERMO = {"densidade": ("densidade",), "distancia": ("distancia",), "referencia": ("referencia",),
            "quintil": ("grupos",), "agregacao": ("agregacao",), "velocidade": ("velocidade",),
            "tendencia": ("tendencia",), "crescimento": ("classe:CRESCIMENTO",),
            "declinio": ("classe:DECLINIO",), "sem_classificacao": ("classe:SEM_CLASSIFICACAO",),
            "aceleracao": ("classe:CRESCIMENTO_ACELERADO", "classe:DECLINIO_ACELERADO"),
            "desaceleracao": ("classe:CRESCIMENTO_DESACELERADO", "classe:DECLINIO_DESACELERADO")}
# Palavras que, numa mensagem ou num texto, apontam para cada ficha (texto dobrado).
_GATILHOS = {
    "densidade": r"\bdensidades?\b|por (?:1\.?000|mil) habitantes",
    "quantidade": r"\bquantidade absoluta\b|\bquantitativos?\b",
    "distancia": r"\bdistancias?\b|\bgeodesic\w*|\blinha reta\b|\bkm\b",
    "referencia": r"\breferencia mais proxima\b|\bmais proxim[oa] (?:referencia|da referencia)\b",
    "grupos": r"\bquint\w*|\bquart(?:il|is)\b|\bdec(?:il|is)\b|\bgrupos? por posicao\b|\bpontos? de corte\b",
    "agregacao": r"\bagrega\w*|\bconjunto agregado\b|\bsoma das contagens\b",
    "variacao": r"\bvariac\w*\b",
    "tendencia": r"\btendencia\w*|\bclasses? de tendencia\b",
    "velocidade": r"\bvelocidades?\b",
    "comparacao": r"\bcomparac\w*|\blado a lado\b",
    "regua": r"\bregua\b",
    "rotatividade": r"\brotatividade\b|\bpermanencia\b|\bcoorte\b",
    "classe:CRESCIMENTO_ACELERADO": r"\bacelerac\w* do crescimento\b|\bcrescimento acelerado\b",
    "classe:CRESCIMENTO_DESACELERADO": r"\bdesacelerac\w* do crescimento\b|\bcrescimento desacelerado\b",
    "classe:DECLINIO_ACELERADO": r"\bacelerac\w* (?:de|do) declinio\b|\bdeclinio acelerado\b",
    "classe:DECLINIO_DESACELERADO": r"\bdesacelerac\w* (?:de|do) declinio\b|\bdeclinio desacelerado\b",
    "classe:SEM_CLASSIFICACAO": r"\bsem classificacao\b",
}


def dobrar(texto: str) -> str:
    import unicodedata
    return "".join(c for c in unicodedata.normalize("NFKD", str(texto).casefold()) if not unicodedata.combining(c))


def mencionadas(texto: str) -> list[str]:
    """As fichas cujos conceitos o texto menciona (mensagem do usuário, resposta ou contexto)."""
    simples = dobrar(texto)
    return [chave for chave, padrao in _GATILHOS.items() if re.search(padrao, simples)]


def pertinentes(mensagem: str, termos=(), classes=(), familia: str | None = None, extras=()) -> list[Ficha]:
    """As fichas que acompanham uma pergunta: as dos termos que o gestor reconheceu, as que a mensagem menciona, as das
    classes de tendência presentes no resultado e as da família da análise em exibição. Sem repetição, na ordem."""
    chaves: list[str] = []
    for termo in termos:
        chaves += list(DO_TERMO.get(termo, ()))
    chaves += mencionadas(mensagem)
    chaves += ["classe:" + c for c in classes if "classe:" + c in FICHAS]
    if familia in ("tendencia", "espacial", "rotatividade"):
        chaves.append({"tendencia": "tendencia", "espacial": "distancia", "rotatividade": "rotatividade"}[familia])
    chaves += [c for c in extras if c in FICHAS]
    return [FICHAS[c] for c in dict.fromkeys(chaves) if c in FICHAS]


def para_o_provedor(fichas: list[Ficha]) -> list[dict]:
    """O que o Gemini recebe de cada ficha: o título e a formulação autorizada (as regras de conferência ficam aqui)."""
    return [{"conceito": ficha.titulo, "definicao_autorizada": ficha.texto} for ficha in fichas]
