"""Triagem determinística das mensagens antes do provedor de IA (RQ-DAD-20, RQ-DAD-37 a RQ-DAD-39), 26/10/2026.

Quatro classes, como na SPEC:
- A, conteúdo pessoal ou identificador protegido (e-mail, telefone, CPF, CNS, sequências de 10 ou mais dígitos, valores de
  colunas sem papel autorizado, como um identificador individual): substituído por marcador e nunca enviado;
- B, entidade não pessoal com evidência determinística positiva: territórios, grupos territoriais (estados, províncias),
  regiões e categorias da base carregada, as unidades federativas do Brasil e o nome que segue um marcador territorial
  ("município de X", "estado do Y"): liberado, porque a interpretação precisa dele;
- C, metadado não necessário ao modelo (nome de campo, arquivo ou planilha): substituído por marcador;
- D, linguagem funcional não nominal (verbos, negação, operadores, quantificadores, conectivos, referências temporais,
  números de recorte como "2023", "2019-2023" ou "menor que 2", quantidades): liberada.

Os marcadores são tipados e numerados (RQ-DAD-39): [CPF_1], [EMAIL_1], [TELEFONE_1], [IDENTIFICADOR_1],
[ENTIDADE_PROTEGIDA_1], [CAMPO_1], [ARQUIVO_1]. Dentro de um mesmo envio ao provedor (a mensagem, a janela da conversa e o
contexto), o mesmo valor recebe o mesmo marcador, e a continuidade ("e a Maria?") não se perde.

O que fica sem evidência: palavra com inicial maiúscula que não é linguagem funcional conhecida, nem entidade da base, nem
vocabulário do domínio. Ela pode ser um nome de pessoa e recebe [ENTIDADE_PROTEGIDA_n]. A maiúscula sozinha nunca mascara
uma palavra conhecida ("Não", "Explique", "Agora", "Município"); a coincidência com o nome de uma coluna ou com um valor
de outra coluna também não mascara palavra do vocabulário ("município", "se", "sul"). A maiúscula também não decide se algo
é pessoa: tudo o que fica sem evidência é protegido do mesmo jeito, seja pessoa, seja entidade.

A mensagem original nunca é alterada: o texto preparado só vai ao provedor; a tela mostra o que a pessoa escreveu.
"""
from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass

# Marcadores tipados e numerados (RQ-DAD-39): o mesmo valor recebe o mesmo número dentro de um envio ao provedor (a mensagem,
# a janela da conversa e o contexto vão juntos); valores diferentes recebem números diferentes.
TIPOS = ("CPF", "EMAIL", "TELEFONE", "IDENTIFICADOR", "ENTIDADE_PROTEGIDA", "CAMPO", "ARQUIVO")
MARCADOR = re.compile(r"\[(?:" + "|".join(TIPOS) + r")_\d+\]")

# Classe A: identificadores diretos, por regra determinística (RQ-DAD-37). Um número isolado não vira telefone só pela
# quantidade de dígitos: telefone exige prefixo internacional, DDD entre parênteses ou um marcador explícito.
# Quando há o grupo "v", só ele é trocado: o marcador explícito ("CPF", "telefone", "nome:") fica, e a frase continua legível.
_CPF = re.compile(r"\b\d{3}\.\d{3}\.\d{3}-\d{2}\b|\b\d{2}\.\d{3}\.\d{3}/\d{4}-\d{2}\b")
_CPF_MARCADO = re.compile(r"(?i:\b(?:cpf|cnpj)\b\s*(?:n[ºo°.]*\s*)?[:=]?\s*)(?P<v>\d[\d.\-/]{9,17}\d)")
_EMAIL = re.compile(r"[\w.+-]+@[\w-]+(?:\.[\w-]+)*\.[a-zA-Z]{2,}")
_TELEFONE = re.compile(r"\+\d{1,3}[\s-]?\(?\d{2}\)?[\s-]?\d{4,5}[\s-]?\d{4}\b|\(\d{2}\)\s?\d{4,5}-?\d{4}\b")
_TELEFONE_MARCADO = re.compile(r"(?i:\b(?:telefone|celular|fone|whatsapp|tel\.?)\s*[:=]?\s*)(?P<v>\+?\d[\d()\s.-]{7,17}\d)")
_IDENTIFICADOR = re.compile(r"https?://\S+|\b\d{10,}\b")
_IDENTIFICADOR_MARCADO = re.compile(r"(?i:\b(?:cns|rg|matr[ií]cula|nome completo|nome|prontu[aá]rio|passaporte)\s*[:=]\s*)"
                                    r"(?P<v>[^,.;\n]{1,60})")
_PRIVADOS = (("EMAIL", _EMAIL), ("CPF", _CPF), ("CPF", _CPF_MARCADO), ("TELEFONE", _TELEFONE),
             ("TELEFONE", _TELEFONE_MARCADO), ("IDENTIFICADOR", _IDENTIFICADOR_MARCADO), ("IDENTIFICADOR", _IDENTIFICADOR))
ARQUIVOS = re.compile(r"(?i)(?<![\w.])[\w.-]+\.(?:csv|xlsx|xls|ods|txt|json)\b")
MARCADOR_TERRITORIAL = re.compile(
    r"(?i)\b(?:munic[ií]pios?|cidades?|estados?|capital|prov[ií]ncias?|distritos?|regi[aã]o)\s+(?:de|do|da|dos|das)\s+"
    r"((?:[A-ZÁÉÍÓÚÂÊÔÃÕÇ][\wÀ-ÿ'-]*)(?:\s+(?:de|do|da|dos|das|e)?\s*[A-ZÁÉÍÓÚÂÊÔÃÕÇ][\wÀ-ÿ'-]*){0,4})")
CODIGO_GOVERNADO = re.compile(r"\bDOC:[\w.-]+|\b[A-Z]{2,4}(?:-[A-Z]{2,4})?-\d{1,3}(?:\.\d+)?\b|\b(?:CFG|LEX)-[A-Z]{2,5}\b")
# Sequência nominal: palavras com inicial maiúscula, com os conectivos dos nomes de lugar entre elas ("Rio de Janeiro").
NOMINAL = re.compile(r"(?<![\w\[])[A-ZÁÉÍÓÚÂÊÔÃÕÇ][\wÀ-ÿ'-]*(?:\s+(?:(?:de|da|do|das|dos|e)\s+)?[A-ZÁÉÍÓÚÂÊÔÃÕÇ][\wÀ-ÿ'-]*)*")


def dobrar(texto: str) -> str:
    """Minúsculas e sem acentos, para comparar."""
    return "".join(c for c in unicodedata.normalize("NFKD", str(texto).casefold()) if not unicodedata.combining(c))


def _palavras(texto: str) -> list[str]:
    return re.findall(r"[a-z0-9]+", dobrar(texto))


# ------------------------------------------------------------------------------------------------ linguagem funcional (D)
_FECHADAS = """
a o as os um uma uns umas ao aos à às de do da dos das dum duma num numa em no na nos nas por pelo pela pelos pelas para pra
pro pros pras com sem sob sobre entre até ate desde contra perante após apos ante durante mediante segundo conforme exceto
e ou mas porém porem contudo todavia entretanto logo portanto pois porque que se caso quando enquanto embora como onde aonde
qual quais quanto quanta quantos quantas quem cujo cuja cujos cujas que
eu tu você voce vocês voces ele ela eles elas nós nos vós me mim comigo te ti contigo lhe lhes se si consigo nosso nossa
nossos nossas meu minha meus minhas teu tua seu sua seus suas dele dela deles delas
este esta estes estas esse essa esses essas aquele aquela aqueles aquelas isto isso aquilo neste nesta nesse nessa naquele
naquela nisso nisto daquilo disso disto deste desta desse dessa daquele daquela outro outra outros outras mesmo mesma
mesmos mesmas próprio propria próprios todo toda todos todas tudo nada nenhum nenhuma algum alguma alguns algumas cada
qualquer quaisquer vários varios várias varias muito muita muitos muitas pouco pouca poucos poucas mais menos tanto tanta
tão tao bem mal já ja ainda agora hoje ontem amanhã amanha sempre nunca jamais também tambem só so somente apenas talvez
sim não nao nem tampouco aqui ali lá la aí ai cá ca então entao depois antes assim inclusive exatamente realmente
afinal enfim aliás alias primeiro primeira segundo segunda terceiro terceira último ultimo última ultima anterior
seguinte próximo proximo próxima proxima novo nova novos novas velho bom boa bons boas melhor pior maior menor grande
pequeno alto alta baixo baixa igual diferente diferentes certo certa errado errada claro clara simples
ok okay oi olá ola obrigado obrigada valeu tchau beleza favor por gentileza desculpa desculpe licença licenca
hum hmm ah oh eh ué ue
zero um dois duas três tres quatro cinco seis sete oito nove dez onze doze vinte trinta cem mil milhão milhao
vez vezes ponto parte lado tipo forma maneira jeito modo caso exemplo pergunta resposta coisa coisas ideia
"""
_DOMINIO = """
município municipio municípios municipios cidade cidades estado estados capital capitais região regiao regiões regioes
país pais brasil território territorio territórios territorios unidade unidades localidade localidades
uf ufs distrito distritos província provincia províncias provincias condado condados grupo grupos
densidade densidades quantidade quantidades quantitativo quantitativos população populacao habitante habitantes
profissional profissionais médico medico médicos medicos médica medica médicas medicas medicina enfermeiro enfermeira
enfermeiros enfermeiras enfermagem saúde saude trabalhador trabalhadores força forca trabalho fts categoria categorias
indicador indicadores análise analise análises analises gráfico grafico gráficos graficos mapa mapas tabela tabelas
resultado resultados resumo relatório relatorio relatórios csv pdf exportar exportação exportacao detalhes histórico historico
tendência tendencia tendências distribuição distribuicao comparação comparacao comparações agregação agregacao rotatividade
espacial referência referencia referências distância distancia distâncias quintil quintis quartil quartis decil decis
percentil corte cortes classe classes classificação classificacao aceleração aceleracao desaceleração desaceleracao
crescimento declínio declinio variação variacao velocidade velocidades período periodo períodos periodos competência
competencia competências ano anos mês mes meses semestre semestral anual série serie trajetória trajetoria
filtro filtros régua regua condição condicao condições condicoes critério criterio critérios ordem ordenação ranking
seleção selecao vista visão visao dado dados base bases planilha planilhas coluna colunas campo campos valor valores
número numero números numeros média media mediana soma total totais taxa taxas percentual porcentagem
km quilômetro quilometro quilômetros quilometros geodésica geodesica coordenada coordenadas latitude longitude
entenda funcionalidade funcionalidades botão botao botões botoes controle controles conversa assistente agente plataforma
gemini ibge cnes datasus sus método metodo métodos fórmula formula definição definicao conceito conceitos
código codigo códigos codigos identificador identificadores
cpf cnpj cns rg telefone celular email e-mail endereço endereco nome nomes documento documentos
"""
# Palavras comuns que costumam abrir uma frase na conversa (sem elas, a maiúscula inicial as protegeria à toa).
_COMUNS = """
fenômeno fenomeno fenômenos cenário cenario panorama situação situacao situações realidade contexto motivo motivos razão razao
problema problemas questão questao questões assunto tema temas aspecto aspectos detalhe informação informacao informações
informacoes dúvida duvida dúvidas curiosidade interessante estranho estranha legal ótimo otimo ótima perfeito perfeita
excelente bacana show certeza verdade mentira importante necessário necessario possível possivel impossível provável
provavelmente obviamente evidentemente sinceramente honestamente basicamente resumindo resumo enfim afinal pronto
pergunto pergunta perguntinha esqueci lembrei gostei adorei entendo compreendo concordo discordo acredito imagino suponho
suposição hipótese hipotese conclusão conclusao interpretação interpretacao leitura sentido significado impressão
diferença diferenca diferenças semelhança semelhanças padrão padrao padrões comportamento movimento mudança mudanca
mudanças aumento queda subida redução reducao alta baixa estabilidade oscilação oscilacao variações nível nivel níveis
grupo lista ranking topo fundo meio centro norte sul leste oeste nordeste sudeste centro-oeste interior litoral capital
urbano rural pessoas pessoa gente população populacional demográfico profissão profissões ocupação ocupacao ocupações
atendimento serviço servico serviços hospital hospitais posto postos unidade sistema rede atenção atencao primária
secundária pública publica privado privada governo prefeitura secretaria ministério ministerio política politica
políticas programa programas recurso recursos investimento planejamento gestão gestao gestor gestora equipe equipes
apresentação apresentacao decisão decisao formato conteúdo conteudo entrada entradas saída saida elemento elementos
etapa etapas exemplo exemplos né ne
doutor doutora doutores senhor senhora senhores professor professora dr dra sr sra srs sras prof profa
"""
_MESES = "janeiro fevereiro março marco abril maio junho julho agosto setembro outubro novembro dezembro jan fev mar abr mai " \
         "jun jul ago set out nov dez"
_VERBOS_AR = """
analisar acelerar acrescentar adicionar agrupar ajudar ajustar alterar apagar aplicar apontar apresentar aprofundar aumentar
avaliar baixar botar buscar calcular cancelar carregar checar chegar colocar começar comecar comparar completar conferir
confirmar considerar consultar continuar contar cotejar criar cruzar custar dar deixar demorar desacelerar desenhar
destacar detalhar diminuir encontrar enviar errar esclarecer escutar esperar esquecer estar explicar exportar falar faltar
ficar filtrar focar gostar ilustrar importar indicar informar jogar juntar lembrar limpar listar localizar mandar mapear
marcar melhorar mencionar mostrar mudar notar observar olhar ordenar parar passar pegar pensar perguntar piorar plotar
precisar procurar puxar recalcular reformular remover repetir resumir retirar sinalizar somar tentar tirar tomar trabalhar
traçar tracar trocar usar validar variar verificar visualizar voltar acertar acompanhar adotar agradecer alcançar alcancar
apresentar arrumar caminhar cortar declarar demonstrar desculpar detectar diferenciar distinguir duvidar elaborar
encerrar entregar estimar examinar ganhar governar habilitar imaginar inverter levar limitar liberar manter negar
organizar priorizar provar reduzir registrar relacionar simplificar sintetizar situar sugerir superar testar tratar
"""
_VERBOS_ER = """
aparecer atender beber chover compreender conhecer converter correr crescer depender descer descrever desfazer devolver
entender escolher escrever esquecer fazer mexer mover parecer perceber perder poder querer receber refazer resolver
responder rever saber ser ter trazer valer vender ver viver dever acontecer aprender comer conter desenvolver dizer
envolver estabelecer interromper manter merecer oferecer pertencer prever reconhecer remeter suceder
"""
_VERBOS_IR = """
abrir admitir assistir cobrir concluir consumir construir decidir definir demitir descobrir destruir discutir distribuir
dividir excluir existir exprimir garantir imprimir incluir inserir ir medir omitir partir permitir persistir pedir
preferir produzir proibir reduzir refletir repartir resumir seguir sentir servir subir sugerir unir vir abrir agir atribuir
cair conseguir constituir contribuir corrigir dirigir emitir exibir instruir introduzir investir possuir reunir substituir
"""
_IRREGULARES = """
sou és é somos são era eras éramos eram fui foi fomos foram seja sejam sendo sido será seria serão
estou está estás estamos estão estava estavam esteve estiveram esteja estejam estando estado estaria estará
tenho tens tem temos têm tinha tinham teve tiveram tenha tenham tendo tido terá teria
vou vais vai vamos vão ia iam fui foi irei irá iria vá vá indo
faço fazes faz fazemos fazem fazia faziam fiz fez fizeram faça façam fazendo feito fará faria
digo dizes diz dizemos dizem dizia diziam disse disseram diga digam dizendo dito dirá diria
posso podes pode podemos podem podia podiam pôde puderam possa possam podendo podido poderá poderia
quero queres quer queremos querem queria queriam quis quiseram queira queiram querendo querido quererá quereria
sei sabes sabe sabemos sabem sabia sabiam soube souberam saiba saibam sabendo sabido saberá saberia
vejo vês vê vemos veem via viam vi viu viram veja vejam vendo visto verá veria
venho vens vem vimos vêm vinha vinham vim veio vieram venha venham vindo virá viria
dou dás dá damos dão dava davam dei deu deram dê deem dando dado dará daria
ponho pões põe pomos põem punha punham pus pôs puseram ponha ponham pondo posto porá poria pôr por
trago trazes traz trazemos trazem trazia traziam trouxe trouxeram traga tragam trazendo trazido trará traria
há havia houve haja haverá haveria haver
caio cai caímos caem caía caíam caiu caíram caia caiam caindo caído
incluo inclui incluem incluiu incluíram inclua incluam excluo exclui excluem excluiu exclua distribui distribua constitui
peço pede pedem pedi pediu peça peçam meço mede medi mediu meça sigo segue seguem segui seguiu siga sigam
prefiro prefere preferem prefira subo sobe sobem suba subam sinto sente sintam sirvo serve servem sirva
desfaça desfaz desfez desfiz refaça refaz refez reveja revê reviu
gostaria gostaríamos queria poderia poderíamos deveria seria daria faria diria
"""


def _conjugar(lema: str) -> set[str]:
    """Formas regulares mais usadas numa conversa: infinitivo, presente, imperativo, passado, imperfeito, gerúndio,
    particípio, futuro e condicional (com as trocas ortográficas c→qu, g→gu e ç→c no imperativo)."""
    radical, terminacao = lema[:-2], lema[-2:]
    if terminacao == "ar":
        imperativo = radical + "e"
        if radical.endswith("c"):
            imperativo = radical[:-1] + "que"
        elif radical.endswith("g"):
            imperativo = radical[:-1] + "gue"
        elif radical.endswith("ç"):
            imperativo = radical[:-1] + "ce"
        formas = {"o", "a", "as", "amos", "am", "ei", "ou", "aram", "ava", "avam", "ando", "ado", "ada", "ados", "adas",
                  "arei", "ará", "aria", "ariam", "aríamos"}
        return {lema, imperativo, imperativo + "m", imperativo + "mos"} | {radical + f for f in formas}
    if terminacao == "er":
        formas = {"o", "e", "es", "emos", "em", "i", "eu", "eram", "ia", "iam", "endo", "ido", "ida", "a", "am", "erá",
                  "eria", "eriam"}
        return {lema} | {radical + f for f in formas}
    formas = {"o", "e", "es", "imos", "em", "i", "iu", "iram", "ia", "iam", "indo", "ido", "ida", "a", "am", "irá", "iria",
              "iriam"}
    return {lema} | {radical + f for f in formas}


def _vocabulario() -> frozenset[str]:
    palavras: set[str] = set()
    for bloco in (_FECHADAS, _DOMINIO, _COMUNS, _MESES, _IRREGULARES):
        palavras.update(dobrar(p) for p in bloco.split())
    for bloco in (_VERBOS_AR, _VERBOS_ER, _VERBOS_IR):
        for lema in bloco.split():
            palavras.update(dobrar(forma) for forma in _conjugar(lema))
    return frozenset(palavras)


VOCABULARIO = _vocabulario()


def funcional(palavra: str) -> bool:
    """Palavra de linguagem funcional ou do domínio (classe D), inclusive o advérbio em -mente de um adjetivo conhecido."""
    simples = dobrar(palavra)
    if simples in VOCABULARIO:
        return True
    return simples.endswith("mente") and len(simples) > 7 and (simples[:-5] in VOCABULARIO or
                                                               simples[:-5].removesuffix("a") + "o" in VOCABULARIO)


# ------------------------------------------------------------------------------------------------ proteção da base
@dataclass(frozen=True)
class Protecao:
    """O que a base carregada informa à triagem; tudo já dobrado (minúsculas, sem acentos).

    liberados: entidades não pessoais com evidência positiva (classe B); protegidos: valores de colunas sem papel
    autorizado, que podem ser pessoais (classe A); metadados: nomes de campo, arquivo e planilha (classe C)."""
    liberados: frozenset = frozenset()
    protegidos: frozenset = frozenset()
    metadados: frozenset = frozenset()


def _ocorrencias(texto_dobrado: str, valores, limite: int = 0) -> list[tuple[int, int]]:
    """Posições (no texto dobrado) das ocorrências inteiras dos valores, os mais longos primeiro."""
    trechos = []
    for valor in sorted(valores, key=len, reverse=True):
        if len(valor) < max(2, limite) or valor not in texto_dobrado:
            continue
        for m in re.finditer(r"(?<![\w])" + re.escape(valor) + r"(?![\w])", texto_dobrado):
            trechos.append((m.start(), m.end()))
    return trechos


def _mapa(texto: str) -> tuple[str, list[int]]:
    """O texto dobrado e, para cada caractere dele, a posição no original."""
    dobrado, origem = [], []
    for posicao, caractere in enumerate(texto):
        for simples in dobrar(caractere):
            dobrado.append(simples)
            origem.append(posicao)
    return "".join(dobrado), origem


def _no_original(intervalos, origem: list[int]) -> list[tuple[int, int]]:
    return [(origem[a], origem[b - 1] + 1) for a, b in intervalos if b > a]


def _sobrepoe(a: tuple[int, int], intervalos) -> bool:
    return any(a[0] < b[1] and b[0] < a[1] for b in intervalos)


class Numeracao:
    """Os números dos marcadores de um envio ao provedor: o mesmo valor (comparado sem caixa e sem acentos) recebe o mesmo
    marcador; outro valor, outro número. Vale para todos os textos do mesmo envio."""

    def __init__(self):
        self._numeros: dict[tuple[str, str], int] = {}
        self._contagem: dict[str, int] = {}
        self._originais: dict[str, str] = {}

    def marcador(self, tipo: str, original: str) -> str:
        chave = (tipo, " ".join(dobrar(original).split()))
        if chave not in self._numeros:
            self._contagem[tipo] = self._contagem.get(tipo, 0) + 1
            self._numeros[chave] = self._contagem[tipo]
        rotulo = "[" + tipo + "_" + str(self._numeros[chave]) + "]"
        self._originais.setdefault(rotulo, original)
        return rotulo

    def usados(self) -> dict[str, int]:
        return dict(self._contagem)

    def protegidos(self) -> list[tuple[str, str]]:
        """(tipo, valor dobrado) de tudo o que já virou marcador neste envio, os valores mais longos primeiro."""
        return sorted(self._numeros, key=lambda chave: len(chave[1]), reverse=True)

    def originais(self) -> dict[str, str]:
        """Marcador → o que a pessoa escreveu. Fica no backend local: serve só para devolver à tela o texto dela quando o
        modelo repete um marcador; nunca vai ao provedor."""
        return dict(self._originais)


def _substituir(texto: str, trocas: list[tuple[int, int, str]], numeracao: Numeracao) -> str:
    # Numeração na ordem de leitura; a troca, do fim para o começo, para as posições continuarem valendo.
    rotulos = {(inicio, fim): numeracao.marcador(tipo, texto[inicio:fim]) for inicio, fim, tipo in sorted(trocas)}
    for inicio, fim, _ in sorted(trocas, reverse=True):
        texto = texto[:inicio] + rotulos[(inicio, fim)] + texto[fim:]
    return texto


def preparar(texto: str, protecao: Protecao | None = None, numeracao: Numeracao | None = None, nominal: bool = True) -> str:
    """A representação da mensagem enviada ao provedor. O original fica intacto para a tela.

    nominal=False vale para texto montado pelo próprio backend a partir do resultado verificado e do catálogo (o cartão do
    contexto e a resposta verificada): os nomes ali já vêm da base ou da documentação, e só as classes A e C
    (identificadores, valores protegidos, campos e arquivos) são trocadas, além do que já virou marcador no mesmo envio."""
    protecao = protecao or Protecao()
    numeracao = numeracao or Numeracao()
    texto = str(texto)
    trocas: list[tuple[int, int, str]] = []
    ocupados: list[tuple[int, int]] = []
    # Classe A, identificadores diretos, e classe C, nomes de arquivo, antes de tudo.
    for tipo, padrao in (*_PRIVADOS, ("ARQUIVO", ARQUIVOS)):
        for m in padrao.finditer(texto):
            trecho = m.span("v") if "v" in padrao.groupindex else m.span()
            if trecho[1] > trecho[0] and not _sobrepoe(trecho, ocupados):
                trocas.append((trecho[0], trecho[1], tipo))
                ocupados.append(trecho)
    dobrado, origem = _mapa(texto)
    # O que já foi protegido neste envio continua protegido em qualquer texto dele, com o mesmo marcador: a resposta
    # verificada do sistema que repete o nome escrito pela pessoa ("Não encontrei “Fulano”") não o revela.
    for tipo, valor in numeracao.protegidos():
        for trecho in _no_original(_ocorrencias(dobrado, (valor,)), origem):
            if not _sobrepoe(trecho, ocupados):
                trocas.append((trecho[0], trecho[1], tipo))
                ocupados.append(trecho)
    # Classe B: entidades da base e o nome que segue um marcador territorial ficam liberados.
    liberados = [t for t in _no_original(_ocorrencias(dobrado, protecao.liberados), origem) if not _sobrepoe(t, ocupados)]
    liberados += [m.span(1) for m in MARCADOR_TERRITORIAL.finditer(texto) if not _sobrepoe(m.span(1), ocupados)]
    # Códigos governados (TPL-06, CAP-TEN-01, DOC:...) são vocabulário do sistema, não nomes.
    liberados += [m.span() for m in CODIGO_GOVERNADO.finditer(texto) if not _sobrepoe(m.span(), ocupados)]
    ocupados += liberados
    # Classe C: nome de campo, arquivo ou planilha (não o vocabulário comum, como "município" ou "uf").
    for inicio, fim in _no_original(_ocorrencias(dobrado, protecao.metadados, 3), origem):
        trecho = texto[inicio:fim]
        if _sobrepoe((inicio, fim), ocupados) or all(funcional(p) for p in re.findall(r"[^\W_]+", trecho)):
            continue
        trocas.append((inicio, fim, "CAMPO"))
        ocupados.append((inicio, fim))
    # Classe A: valores de colunas sem papel autorizado (não o vocabulário comum, como "se" ou "sul").
    for inicio, fim in _no_original(_ocorrencias(dobrado, protecao.protegidos, 2), origem):
        trecho = texto[inicio:fim]
        if _sobrepoe((inicio, fim), ocupados) or all(funcional(p) or p.isdigit() for p in _palavras(trecho)):
            continue
        trocas.append((inicio, fim, "IDENTIFICADOR"))
        ocupados.append((inicio, fim))
    if not nominal:
        return _substituir(texto, trocas, numeracao).strip()
    # Sem evidência: sequência com inicial maiúscula que não é vocabulário conhecido nem entidade liberada. É protegida da
    # primeira palavra desconhecida em diante ("O Dr. João" mantém o artigo e o título; "Explica-me" é avaliada por partes).
    # "Maria e João" são dois nomes: a sequência é dividida no "e" ("João da Silva" continua um só). Cada parte é vista
    # palavra a palavra, fora dos trechos já liberados ou trocados ("Compare Joaquim Silva e Manaus": Manaus fica liberado
    # e Joaquim Silva é protegido).
    for m in NOMINAL.finditer(texto):
        for parte in re.finditer(r"(?:(?!\s+e\s+).)+", m.group(0)):
            base = m.start() + parte.start()
            corrida: list[tuple[int, int, str]] = []
            for p in [*re.finditer(r"[\wÀ-ÿ'-]+", parte.group(0)), None]:
                trecho = (base + p.start(), base + p.end()) if p is not None else None
                if trecho is not None and not _sobrepoe(trecho, ocupados):
                    corrida.append((trecho[0], trecho[1], p.group(0)))
                    continue
                # Uma letra sozinha (o D de "D(u, p, c)", uma inicial) não identifica ninguém.
                desconhecidas = [(a, b) for a, b, palavra in corrida if palavra not in ("de", "da", "do", "das", "dos") and
                                 len(palavra) > 1 and
                                 not all(funcional(pedaco) for pedaco in re.split(r"[-']", palavra) if pedaco)]
                if desconhecidas:  # da primeira palavra desconhecida ao fim do nome ("Rio Grande do Sul" inteiro)
                    trocas.append((desconhecidas[0][0], corrida[-1][1], "ENTIDADE_PROTEGIDA"))
                corrida = []
    return _substituir(texto, trocas, numeracao).strip()


def preparar_varios(textos: list[str], protecao: Protecao | None = None, numeracao: Numeracao | None = None) -> list[str]:
    """Vários textos do mesmo envio, com a mesma numeração dos marcadores."""
    numeracao = numeracao or Numeracao()
    return [preparar(texto, protecao, numeracao) for texto in textos]


def protecao_da_base(colunas: dict[str, list], papeis: dict[str, str], nomes_extras=(), metadados_extras=()) -> Protecao:
    """A proteção a partir das colunas da base (nome → valores únicos) e dos papéis reconhecidos (papel → coluna).

    Liberados: valores das colunas de território, grupo territorial, região e categoria, mais os nomes extras (as
    unidades federativas, na base do Brasil). Protegidos: valores de texto das demais colunas, inclusive identificador
    individual. Metadados: os nomes das colunas e os metadados extras (arquivo e planilha)."""
    autorizadas = {coluna for papel, coluna in papeis.items()
                   if papel in ("territory", "category", "grupo_territorial", "region") and coluna}
    for coluna in colunas:
        if dobrar(coluna).replace("_", " ").strip() in ("uf", "estado", "regiao", "regiao geografica", "provincia",
                                                        "distrito", "grupo territorial", "sigla uf"):
            autorizadas.add(coluna)
    identidade = {coluna for papel, coluna in papeis.items() if papel == "identity" and coluna}
    liberados, protegidos = set(dobrar(n) for n in nomes_extras), set()
    for coluna, valores in colunas.items():
        destino = liberados if coluna in autorizadas and coluna not in identidade else protegidos
        for valor in valores:
            texto = str(valor).strip()
            if not texto or (destino is protegidos and re.fullmatch(r"[-+]?\d+(?:[.,]\d+)?", texto)):
                continue
            destino.add(dobrar(texto))
    metadados = {dobrar(str(c)) for c in colunas} | {dobrar(str(m)) for m in metadados_extras if str(m).strip()}
    return Protecao(frozenset(liberados), frozenset(protegidos - liberados), frozenset(metadados))
