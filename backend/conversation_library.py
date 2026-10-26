"""Biblioteca de Inteligência Conversacional: trajetórias que orientam a interpretação das mensagens.

Componente interno e independente do provedor de LLM. As trajetórias ficam em JSONL versionado
(backend/biblioteca_conversacional/trajetorias/): mensagens humanas, eventos da interface, a interpretação
esperada no contrato do intérprete, a ação esperada do sistema, as transições de contexto, as restrições e as
referências governadas (id_doc do catálogo PT e requisitos da SPEC). Para cada mensagem, uma recuperação
lexical local escolhe poucos turnos pertinentes à mensagem, ao histórico e ao estado verificado da conversa; o
integrador do provedor (llm_bridge) os apresenta ao modelo mascarados pelas mesmas regras das mensagens do
usuário. As trajetórias não têm texto de resposta: explicações metodológicas vêm só do catálogo governado.

Os exemplos não são dados, resultados nem autorização e não substituem os controles determinísticos.
ADT_BIBLIOTECA_CONVERSACIONAL=0 desliga a biblioteca; o pedido ao provedor volta a ser o de antes.
"""
from collections import Counter, defaultdict
from dataclasses import dataclass
from hashlib import sha256
import json
import math
import os
from pathlib import Path
import re
import threading
import unicodedata

ROOT = Path(__file__).resolve().parent / "biblioteca_conversacional"
TRAJECTORIES = ROOT / "trajetorias"
SCHEMA = 1

DIMENSIONS = {
    "A": "Interações introdutórias", "B": "Compreensão e preparação dos dados", "C": "Seleção de territórios",
    "D": "Métodos de análise", "E": "Ferramentas do sistema", "F": "Combinação de análises",
    "G": "Interpretação dos resultados", "H": "Dúvidas, ambiguidades e dificuldades",
    "I": "Conversas longas e progressivas", "J": "Situações excepcionais",
}
PROFILES = ("gestor", "tecnico", "pesquisador", "estudante", "jornalista", "controle_social", "iniciante")
LANGUAGES = ("pt", "en", "es")
REGISTERS = ("tecnico", "academico", "administrativo", "informal", "abreviado", "impreciso", "indireto")
SOURCES = ("sem_base", "brasil", "importada")
# Operações do motor: as dez do contrato do intérprete e as duas preparadas só por comando determinístico.
ENGINE_OPERATIONS = ("density", "counts", "distribution", "comparisons", "temporal", "aggregate", "spatial",
                     "ranking", "rotation", "report", "nearest", "criteria")
EVENTS = ("FONTE_BRASIL", "FONTE_IMPORTADA", "ANALISE_ESCOLHIDA", "SELECAO_TERRITORIAL", "LIMPA_SELECAO",
          "CALCULO", "HISTORICO", "NOVA_ANALISE", "NOVA_SESSAO")
# O que o sistema faz com o turno (canal determinístico ou proposta do intérprete), nunca um texto de resposta.
ACTIONS = {
    "CORTESIA": "Saudação, agradecimento ou confirmação breve, sem conteúdo analítico.",
    "ORIENTA_CAPACIDADES": "Orientação do catálogo local sobre as análises disponíveis.",
    "ORIENTA_DADOS": "Orientação sobre os dados: base do Brasil, importação e estrutura recomendada.",
    "ORIENTA_FLUXO": "Orientação sobre o fluxo: escolher a análise, preparar e calcular.",
    "ORIENTA_PRIVACIDADE": "Orientação sobre privacidade e o que vai ao provedor de IA.",
    "ORIENTA_LIMITES": "Orientação sobre os limites do agente e do intérprete.",
    "EXPLICA_METODO": "Formas governadas do catálogo PT (doc), sem paráfrase.",
    "SIMPLIFICA": "Reapresenta o documento ou o resultado já apresentado, sem texto novo.",
    "ESCOLHE_FONTE": "Escolha da fonte: dados do Brasil ou importação.",
    "PROPOE_ANALISE": "Propõe a análise e abre a preparação; nada é calculado.",
    "PREPARA_RECORTE": "Resolve localmente territórios ou competências citados para a análise; nada é calculado.",
    "PERGUNTA_INDICADOR": "Pergunta o indicador (densidade ou quantidade).",
    "PERGUNTA_TERRITORIOS": "Pergunta quais territórios usar (nomes, segundo município, homônimo, estado ou município).",
    "PERGUNTA_PERIODO": "Pergunta a competência ou informa que ela não existe na base.",
    "PERGUNTA_LEITURA": "Oferece leituras concorrentes ou pede para escolher por qual análise começar.",
    "PERGUNTA_CRITERIO": "Termo avaliativo ou normativo: o critério precisa ser definido pelo usuário.",
    "PEDE_REFORMULACAO": "Sem análise identificável: pergunta qual análise realizar.",
    "ESTRUTURA_CRITERIO": "Critérios combinados: condição, ordenação, N primeiros ou comparação com o anterior.",
    "CORRIGE_INDICADOR": "Corrige o indicador da análise em preparação.",
    "LE_RESULTADO": "Lê o resultado apresentado, com valores e notas copiados do motor.",
    "MOSTRA_CONTEXTO": "Mostra a seleção verificada e as possibilidades do pré-exame.",
    "ALTERA_SELECAO": "Acrescenta ou troca territórios da preparação.",
    "ALTERA_PERIODO": "Prepara outra competência sem alterar o resultado já calculado.",
    "NAVEGA": "Abre a preparação, os territórios ou os resultados.",
    "MUDA_VISUALIZACAO": "Abre o resultado na aba Mapa, Gráficos ou Tabela.",
    "REABRE_RESULTADO_ANTERIOR": "Reabre o resultado anterior da sessão, sem recalcular.",
    "CONFIRMA_NA_TELA": "O cálculo é uma ação do usuário na preparação; a conversa não executa.",
    "INFORMA_INDISPONIVEL": "A análise não é possível com esta base; o pré-exame informa o motivo.",
    "RECUSA_FORA_DO_ESCOPO": "Pedido fora do escopo (causalidade, previsão, fonte externa, dado pessoal).",
    "DESFAZ": "Desfaz a última mudança do gráfico feita pela conversa e pergunta o que a pessoa queria.",
    "VOLTA_ESTADO": "Volta a um estado anterior do gráfico aplicado pela conversa (a comparação anterior, por exemplo).",
}
CONTEXT_KEYS = ("fonte", "operacao", "indicador", "territorios", "periodo", "categoria", "resultado",
                "visualizacao", "criterios", "referencias", "documento")
RESTRICTIONS = {
    "SEM_CALCULO_NA_CONVERSA": "A conversa prepara; o cálculo é do motor, por ação do usuário.",
    "SEM_VALOR_DO_LLM": "Nenhum número, fato ou resultado vem do intérprete.",
    "SEM_DADO_AO_PROVEDOR": "Nenhum valor, campo ou arquivo da base vai ao provedor.",
    "SEM_JUIZO_NORMATIVO": "Sem adjetivação avaliativa (LEX-NORM, LEX-DES) sem critério do usuário.",
    "SEM_CAUSALIDADE": "Sem atribuição de causa (LEX-CAU, EXC-03).",
    "SEM_PERTENCA_INFERIDA": "Pertença a agrupamentos territoriais não é inferida (RQ-ESC-04, RQ-DAD-12).",
    "SEM_LIMIAR_PADRAO": "Sem pontos de corte padrão (CFG-NOR vazio).",
    "DISTANCIA_NAO_E_ACESSO": "Distância geodésica direta, não trajeto, tempo ou acesso (LEX-ACE).",
    "POSSIVEL_DUPLA_CONTAGEM": "Soma de componentes pode contar a mesma pessoa mais de uma vez.",
    "CAPACIDADE_SO_DO_MOTOR": "Referência mais próxima e critérios só por comando determinístico.",
    "RESPOSTA_EM_PT": "Mensagem em inglês ou espanhol; a apresentação continua em português.",
    "EXPLICACAO_SO_DO_CATALOGO": "Explicação metodológica só pelas formas governadas.",
    "ESCOLHA_EXPLICITA": "Nada é escolhido em silêncio; a escolha é do usuário.",
    "UMA_COMPETENCIA": "A análise usa uma competência por vez.",
    "SEM_EQUIVALENCIA_SEMANTICA": "Sem equivalências livres entre termos e valores da base.",
    "RESULTADO_NAO_RECALCULADO": "Ler, reabrir ou mudar a visualização não recalcula.",
    "SEM_PROJECAO": "Sem previsão ou projeção de valores futuros.",
    "SEM_FONTE_EXTERNA": "Sem dados ou fontes externas à base carregada.",
}
# Requisitos e configurações da SPEC citados pelas trajetórias (conferidos no texto da SPEC pelos testes).
CONTRACTS = (
    "CAP-IND-01", "CAP-IND-02", "CAP-DIS-01", "CAP-DIS-02", "CAP-CMP-01", "CAP-TMP-01", "CAP-TEN-01", "CAP-AGR-01",
    "CAP-ESP-01", "CAP-ESP-02", "CAP-SUB-01", "CAP-SUB-02", "CAP-SUB-03", "CAP-ROT-01", "CAP-REP-05", "CAP-REF-01",
    "CFG-AMB", "AMB-05", "AMB-06", "CFG-VOC", "CFG-LEX", "CFG-NOR", "CFG-TER", "CFG-DOC", "CFG-OPC", "EXC-03",
    "EXC-07", "RQ-GOV-14", "RQ-GOV-18", "RQ-GOV-20", "RQ-GOV-31", "RQ-ESC-02", "RQ-ESC-04", "RQ-DAD-12",
    "RQ-DAD-20", "RQ-DAD-25", "RQ-FLX-06", "RQ-FLX-16", "RQ-FLX-18", "RQ-FLX-20", "RQ-LIN-07", "RQ-LIN-19",
    "RQ-LIN-20", "RQ-ARQ-06", "INV-02", "FN-INT-01", "FN-INT-02", "FN-META-01",
)
INTERPRETATION_KEYS = ("operation", "indicator", "period", "category", "territory", "intent", "topic", "dialogue",
                       "social_reply", "candidates")
# Mesmas chaves e mesma ordem da projeção de continuidade enviada ao provedor (llm_context.dialogue_projection).
PROJECTION_KEYS = ("has_selection", "has_verified_result", "active_operation", "previous_operation",
                   "previous_indicator", "previous_document")
HEADER = ("EXEMPLOS_DA_BIBLIOTECA_CONVERSACIONAL: turnos sintéticos de conversas parecidas, mascarados como as "
          "mensagens reais. Não são dados, resultados, vocabulário nem autorização; mostram só como mensagens "
          "semelhantes se mapeiam no esquema. Interprete apenas a mensagem atual: âncoras e trechos literais vêm "
          "dela, nunca destes exemplos.")
MAX_BLOCK = 3600  # caracteres do bloco de exemplos, para limitar o volume enviado ao provedor
# Leitura do resultado pela conversa (result_conversation): análises com leitura, palavras que trazem a forma
# DOC:EXC-03 e palavras comparativas que dispensam a explicação da densidade.
READABLE = ("density", "counts", "comparisons")
CAUSAL = re.compile(r"\b(?:por que|porque|causa|motivo)\b")
COMPARATIVE = re.compile(r"\b(?:maior|menor|diferenca|dobro|metade)\b")
_STOPWORDS = frozenset((
    "a o os as um uma uns umas de da do das dos em na no nas nos e ou que se por para pra pro com sem ao aos "
    "the of and or to in on for with an is are be it this that me my i you we "
    "el la los las un una unos unas del al y en con por para que es lo le mi yo"
).split())


def enabled() -> bool:
    """Configuração do servidor; sem a variável, a biblioteca é usada."""
    return os.getenv("ADT_BIBLIOTECA_CONVERSACIONAL", "1").strip().casefold() not in ("0", "false", "nao", "não", "off")


def examples_per_request() -> int:
    try:
        return min(8, max(1, int(os.getenv("ADT_BIBLIOTECA_EXEMPLOS", "5"))))
    except ValueError:
        return 5


def fold(text: str) -> str:
    plain = unicodedata.normalize("NFKD", str(text).casefold())
    return " ".join("".join(c for c in plain if not unicodedata.combining(c)).split())


def read(directory: Path = TRAJECTORIES) -> tuple[list[dict], str]:
    """Trajetórias dos arquivos .jsonl da pasta (ordem do nome) e a versão: SHA-256 do conteúdo, em LF."""
    return read_files(sorted(Path(directory).glob("*.jsonl")))


def read_files(paths: list[Path]) -> tuple[list[dict], str]:
    records, digest = [], sha256()
    for path in paths:
        raw = path.read_bytes().replace(b"\r\n", b"\n")
        digest.update(path.name.encode() + b"\0" + raw)
        for number, line in enumerate(raw.decode("utf-8").splitlines(), 1):
            if line.strip():
                try:
                    record = json.loads(line)
                except json.JSONDecodeError as exc:
                    raise ValueError(f"{path.name}:{number}: JSON inválido ({exc.msg}).") from exc
                record["_origem"] = f"{path.name}:{number}"
                records.append(record)
    return records, digest.hexdigest()[:12]


def turns(trajectory: dict):
    """Turnos do usuário com o estado verificado antes de cada um, derivado dos turnos e eventos anteriores."""
    state = {"fonte": trajectory["fonte"], "pendente": None, **dict.fromkeys(PROJECTION_KEYS)}
    # Fora da projeção: a operação que o motor calcularia e a do resultado na tela (None quando desconhecida).
    state.update(has_selection=False, has_verified_result=False, engine_operation=None, result_operation=None)
    history, number = [], 0
    for step in trajectory["passos"]:
        if "evento" in step:
            _event(state, step)
            continue
        number += 1
        yield {"id": f"{trajectory['id']}#{number}", "trajectory": trajectory, "turn": step,
               "history": list(history[-4:]), "state": dict(state)}
        history.append(step["usuario"])
        interpretation = step["interpretacao"]
        if interpretation["operation"] != "none":
            # Como a sessão (conversation_session.remember) e a escolha da análise pela interface.
            state["previous_operation"] = interpretation["operation"]
            state["previous_indicator"] = None if interpretation["indicator"] == "none" else interpretation["indicator"]
            if state["fonte"] == "sem_base":
                state["pendente"] = interpretation["operation"]
            else:
                state["active_operation"] = state["engine_operation"] = interpretation["operation"]
        if interpretation["dialogue"] == "previous_result":
            state["result_operation"] = None  # o resultado reaberto não está descrito na trajetória
        if step.get("doc") and step.get("acao") == "EXPLICA_METODO":
            state["previous_document"] = step["doc"][0]


def _event(state: dict, step: dict) -> None:
    kind = step["evento"]
    if kind in ("FONTE_BRASIL", "FONTE_IMPORTADA"):
        # Outra fonte limpa a memória do diálogo (conversation_session.capture); a proposta pendente vira a análise.
        pending = state["pendente"]
        state.update(dict.fromkeys(PROJECTION_KEYS), has_selection=False, has_verified_result=False, pendente=None,
                     fonte="brasil" if kind == "FONTE_BRASIL" else "importada", active_operation=pending,
                     engine_operation=pending, result_operation=None)
    elif kind == "ANALISE_ESCOLHIDA":
        # O provedor só conhece as dez operações do contrato; referência mais próxima e critérios ficam fora.
        operation = step["operacao"]
        state["active_operation"] = None if operation in ("nearest", "criteria") else operation
        state["engine_operation"] = operation
    elif kind == "SELECAO_TERRITORIAL":
        state["has_selection"] = True
    elif kind == "LIMPA_SELECAO":
        state["has_selection"] = False
    elif kind == "CALCULO":
        state.update(has_verified_result=True, result_operation=state["engine_operation"])
    elif kind == "HISTORICO":
        state.update(has_verified_result=True, result_operation=None)  # resultado do histórico, qualquer análise
    elif kind == "NOVA_ANALISE":
        state.update(active_operation=None, engine_operation=None, has_verified_result=False, result_operation=None)
    elif kind == "NOVA_SESSAO":
        state.update(dict.fromkeys(PROJECTION_KEYS), has_selection=False, has_verified_result=False, pendente=None,
                     fonte="sem_base", engine_operation=None, result_operation=None)


def projection(state: dict) -> dict:
    return {key: state[key] for key in PROJECTION_KEYS}


def mode(state: dict) -> str:
    return "sem_base" if state["fonte"] == "sem_base" else "base"


# ---------------------------------------------------------------------------------------------- validação

@dataclass(frozen=True)
class Contract:
    """Contrato do intérprete fornecido pelo integrador; a biblioteca não depende de um provedor."""
    operations: tuple
    indicators: tuple
    intents: tuple
    topics: tuple
    dialogue: tuple
    check: object  # check(interpretação, mensagens sanitizadas) -> lista de problemas
    sanitize: object  # mesma minimização das mensagens sem base carregada
    doc_ids: frozenset
    doc_topics: dict  # tópico -> ids governados apresentados pelo sistema


def validate(records: list[dict], contract: Contract, spec_text: str = "") -> list[str]:
    """Problemas de esquema, coerência e governança; lista vazia quando a biblioteca está íntegra."""
    problems, seen, signatures, texts = [], set(), {}, Counter()
    for record in records:
        where = record.get("_origem", "?") + " " + str(record.get("id"))
        problems += [where + ": " + text for text in _validate_record(record, contract, spec_text)]
        if record.get("id") in seen:
            problems.append(where + ": id repetido.")
        seen.add(record.get("id"))
        try:
            users = tuple(fold(step["usuario"]) for step in record["passos"] if "usuario" in step)
        except (KeyError, TypeError):
            continue
        if users in signatures:
            problems.append(where + ": trajetória igual a " + signatures[users] + ".")
        signatures.setdefault(users, str(record.get("id")))
        texts.update(set(users))
    # Repetição superficial: a mesma mensagem longa em muitas trajetórias.
    for text, count in texts.items():
        if len(text) > 30 and count > 3:
            problems.append(f"mensagem repetida em {count} trajetórias: «{text[:60]}»")
    return problems


def _validate_record(record: dict, contract: Contract, spec_text: str) -> list[str]:
    problems = []
    expected = {"id", "dimensao", "tema", "perfil", "idioma", "registro", "fonte", "passos"}
    present = set(record) - {"_origem"}
    if present != expected:
        return ["campos da trajetória fora do esquema: " + ", ".join(sorted(present ^ expected))]
    if not re.fullmatch(r"[A-J]-\d{4}|N[A-J]-\d{4}", str(record["id"])) or record["id"].lstrip("N")[0] != record["dimensao"]:
        problems.append("id deve ser <dimensão>-NNNN (ou N<dimensão>-NNNN no conjunto inédito).")
    for key, allowed in (("dimensao", DIMENSIONS), ("perfil", PROFILES), ("idioma", LANGUAGES),
                         ("registro", REGISTERS), ("fonte", SOURCES)):
        if record[key] not in allowed:
            problems.append(f"{key} fora da lista: {record[key]!r}.")
    if not isinstance(record["tema"], str) or not 10 <= len(record["tema"]) <= 200:
        problems.append("tema deve ter de 10 a 200 caracteres.")
    steps = record["passos"]
    if not isinstance(steps, list) or not 2 <= len(steps) <= 40:
        return problems + ["passos: de 2 a 40 por trajetória."]
    users = [step for step in steps if isinstance(step, dict) and "usuario" in step]
    if len(users) < 2:
        problems.append("a trajetória precisa de pelo menos dois turnos do usuário.")
    for step in steps:
        if not isinstance(step, dict):
            problems.append("passo inválido.")
        elif "evento" in step:
            if step["evento"] not in EVENTS or set(step) - {"evento", "operacao"}:
                problems.append(f"evento inválido: {step}.")
            elif (step["evento"] == "ANALISE_ESCOLHIDA") != ("operacao" in step) or (
                    "operacao" in step and step["operacao"] not in ENGINE_OPERATIONS):
                problems.append("ANALISE_ESCOLHIDA exige operacao do motor (e só ele a usa).")
        elif not {"usuario", "interpretacao", "acao"} <= set(step) or not isinstance(step["interpretacao"], dict) or \
                not set(INTERPRETATION_KEYS) <= set(step["interpretacao"]):
            problems.append("turno sem usuario, acao ou interpretacao com todos os campos do contrato.")
    if problems:
        return problems
    for item in turns(record):
        problems += [f"turno {item['id']}: {text}" for text in _validate_turn(item, record, contract, spec_text)]
    return problems


def _validate_turn(item: dict, record: dict, contract: Contract, spec_text: str) -> list[str]:
    turn, problems = item["turn"], []
    allowed = {"usuario", "interpretacao", "acao", "altera", "preserva", "restricoes", "doc", "contrato", "nota"}
    if set(turn) - allowed or not {"usuario", "interpretacao", "acao"} <= set(turn):
        return ["campos do turno fora do esquema (obrigatórios: usuario, interpretacao, acao)."]
    text = turn["usuario"]
    if not isinstance(text, str) or not 2 <= len(text.strip()) <= 800 or "\n" in text or "\r" in text:
        return ["usuario deve ter de 2 a 800 caracteres, numa linha só."]
    if turn["acao"] not in ACTIONS:
        problems.append(f"acao fora da lista: {turn['acao']!r}.")
    for key, allowed_values in (("altera", CONTEXT_KEYS), ("preserva", CONTEXT_KEYS), ("restricoes", RESTRICTIONS),
                                ("contrato", CONTRACTS), ("doc", contract.doc_ids)):
        values = turn.get(key, [])
        if not isinstance(values, list) or any(value not in allowed_values for value in values) or len(set(values)) != len(values):
            problems.append(f"{key} com valor fora da lista ou repetido: {values}.")
    if spec_text:
        problems += [f"contrato {code} não aparece na SPEC." for code in turn.get("contrato", []) if code not in spec_text]
    if not isinstance(turn.get("nota", ""), str) or len(turn.get("nota", "")) > 240:
        problems.append("nota deve ter até 240 caracteres.")
    interpretation = turn["interpretacao"]
    if not isinstance(interpretation, dict) or set(interpretation) != set(INTERPRETATION_KEYS):
        return problems + ["interpretacao precisa ter exatamente: " + ", ".join(INTERPRETATION_KEYS) + "."]
    enums = [f"{key} fora do contrato: {interpretation[key]!r}." for key, values in (
        ("operation", contract.operations), ("indicator", contract.indicators), ("intent", contract.intents),
        ("topic", contract.topics), ("dialogue", contract.dialogue)) if interpretation[key] not in values]
    if enums:
        return problems + enums
    for slot in ("period", "category", "territory"):
        value = interpretation[slot]
        # Valores só quando literalmente presentes na mensagem atual (o backend descarta os demais).
        if not isinstance(value, str) or (value and not literal(value, text)):
            problems.append(f"{slot} {value!r} não é trecho literal da mensagem.")
    candidates = interpretation["candidates"]
    if not isinstance(candidates, list) or len(candidates) == 1 or len(candidates) > 5:
        problems.append("candidates: vazio ou de 2 a 5 leituras concorrentes.")
    elif any(not isinstance(c, dict) or set(c) != {"operation", "indicator", "anchor"} or
             not literal(c["anchor"], text) for c in candidates):
        return problems + ["cada candidata tem operation, indicator e anchor literal da mensagem."]
    history = [contract.sanitize(message) for message in item["history"]]
    problems += contract.check(interpretation, [*history, contract.sanitize(text)])
    problems += _coherence(turn, interpretation, record, contract, item["state"])
    return problems


def reading_documents(message: str, state: dict, contract: Contract) -> list | None:
    """Formas governadas que a leitura do resultado apresenta (result_conversation.answer_result, explain_result);
    None quando a trajetória não diz qual resultado está na tela."""
    operation = state.get("result_operation")
    if not state["has_verified_result"] or not operation:
        return None
    if operation not in READABLE:
        return ["DOC:CFG-DOC.comportamento"]  # "documentação insuficiente": a leitura não existe para esta análise
    text = fold(message)
    return ((["DOC:EXC-03"] if CAUSAL.search(text) else [])
            + (list(contract.doc_topics["density"]) if operation == "density" and not COMPARATIVE.search(text) else []))


def _coherence(turn: dict, interpretation: dict, record: dict, contract: Contract, state: dict) -> list[str]:
    """Regras que ligam a interpretação esperada à ação, às restrições e às referências."""
    action, problems = turn["acao"], []
    operation, dialogue, topic = interpretation["operation"], interpretation["dialogue"], interpretation["topic"]
    if action == "PROPOE_ANALISE" and operation == "none":
        problems.append("PROPOE_ANALISE exige uma operação.")
    if len(interpretation["candidates"]) >= 2 and action != "PERGUNTA_LEITURA":
        problems.append("leituras concorrentes exigem a ação PERGUNTA_LEITURA.")
    if action == "EXPLICA_METODO":
        if topic not in contract.doc_topics or not turn.get("doc"):
            problems.append("EXPLICA_METODO exige um tópico governado e os ids apresentados.")
        elif turn["doc"] != list(contract.doc_topics[topic]):
            problems.append(f"doc deve ser exatamente {list(contract.doc_topics[topic])} (formas do tópico {topic}).")
    elif topic in contract.doc_topics and action not in ("SIMPLIFICA",):
        problems.append(f"tópico {topic} é respondido pelas formas governadas (acao EXPLICA_METODO).")
    views = {"show_map": "MUDA_VISUALIZACAO", "show_chart": "MUDA_VISUALIZACAO", "show_table": "MUDA_VISUALIZACAO",
             "previous_result": "REABRE_RESULTADO_ANTERIOR"}
    if dialogue in views and action != views[dialogue]:
        problems.append(f"dialogue {dialogue} exige a ação {views[dialogue]}.")
    if action in ("MUDA_VISUALIZACAO", "REABRE_RESULTADO_ANTERIOR") and dialogue not in views:
        problems.append(f"{action} exige dialogue de visualização ou de resultado anterior.")
    # Atos do gestor de diálogo (dialogo.py): desfazer e voltar a um estado anterior têm ação própria.
    for act, required in (("undo", "DESFAZ"), ("previous_state", "VOLTA_ESTADO")):
        if (dialogue == act) != (action == required):
            problems.append(f"dialogue {act} e a ação {required} andam juntos.")
    expected = reading_documents(turn["usuario"], state, contract) if action == "LE_RESULTADO" else None
    if expected is not None and dialogue == "explain_result" and turn.get("doc", []) != expected:
        problems.append(f"leitura do resultado: doc deve ser {expected} (formas que o sistema apresenta).")
    if record["idioma"] != "pt" and "RESPOSTA_EM_PT" not in turn.get("restricoes", []):
        problems.append("mensagem em inglês ou espanhol exige a restrição RESPOSTA_EM_PT.")
    if interpretation["social_reply"] and interpretation["intent"] != "CONVERSACIONAL":
        problems.append("social_reply só em intenção CONVERSACIONAL.")
    return problems


def literal(value: str, text: str) -> bool:
    """Mesmo critério das âncoras do intérprete: trecho literal, sem marcadores, após caixa e acentos."""
    if not isinstance(value, str) or not value or len(value) > 100 or "[" in value or "]" in value:
        return False

    def plain(item):
        return "".join(c for c in unicodedata.normalize("NFKD", item.casefold()) if not unicodedata.combining(c))
    return bool(re.search(r"(?<!\w)" + re.escape(plain(value)) + r"(?!\w)", plain(text)))


# ---------------------------------------------------------------------------------------------- recuperação

def _features(text: str) -> Counter:
    """Palavras, prefixos de cinco letras (aproximam flexões e línguas: densidade/density) e 4-gramas internos."""
    features = Counter()
    for token in re.findall(r"\w+", fold(text)):
        if token in _STOPWORDS:
            continue
        features["w:" + token] += 1
        if len(token) > 5:
            features["p:" + token[:5]] += 1
        if len(token) >= 6 and not token.isdigit():
            for start in range(len(token) - 3):
                features["g:" + token[start:start + 4]] += 1
    return features


_WEIGHTS = {"w": 1.0, "p": 0.6, "g": 0.15}


class _BM25:
    def __init__(self, documents: list[Counter]):
        self.postings = defaultdict(list)
        self.lengths = [sum(doc.values()) for doc in documents]
        self.average = (sum(self.lengths) / len(self.lengths)) if documents else 1.0
        for index, doc in enumerate(documents):
            for feature, count in doc.items():
                self.postings[feature].append((index, count))
        total = len(documents)
        # 4-gramas muito frequentes ("dade", "icip") não distinguem exemplos e só encarecem a consulta; palavras e
        # prefixos ficam sempre, com o peso do idf.
        self.idf = {feature: math.log(1 + (total - len(postings) + 0.5) / (len(postings) + 0.5))
                    for feature, postings in self.postings.items()
                    if feature[0] != "g" or len(postings) <= max(50, total * 0.05)}

    def scores(self, query: Counter, k1=1.2, b=0.75) -> dict:
        result = defaultdict(float)
        for feature, weight in query.items():
            idf = self.idf.get(feature)
            if idf is None:
                continue
            factor = _WEIGHTS[feature[0]] * idf * min(weight, 2)
            for index, count in self.postings[feature]:
                result[index] += factor * count * (k1 + 1) / (count + k1 * (1 - b + b * self.lengths[index] / self.average))
        return result


class Library:
    """Trajetórias carregadas e o índice dos turnos (só da própria biblioteca, nunca do conjunto inédito)."""

    def __init__(self, records: list[dict], version: str):
        self.version, self.records = version, records
        self.turns = [item for record in records for item in turns(record)]
        self.current = _BM25([_features(item["turn"]["usuario"]) for item in self.turns])
        self.previous = _BM25([_features(item["history"][-1]) if item["history"] else Counter() for item in self.turns])

    def select(self, message: str, history: list[str], state: dict, k: int | None = None) -> list[dict]:
        """Turnos mais pertinentes à mensagem, ao histórico e ao estado; no máximo um por trajetória."""
        k = k or examples_per_request()
        wanted = mode(state)
        lexical = self.current.scores(_features(message))
        if history:
            for index, score in self.previous.scores(_features(history[-1])).items():
                if index in lexical:
                    lexical[index] += 0.35 * score
        candidates = [(score, index) for index, score in lexical.items() if mode(self.turns[index]["state"]) == wanted]
        if not candidates:
            return []
        candidates = sorted(candidates, reverse=True)[:80]
        top = candidates[0][0] or 1.0
        content = len([token for token in re.findall(r"\w+", fold(message)) if token not in _STOPWORDS])
        weight = 0.4 if content <= 3 else 0.2  # mensagens curtas dependem mais do estado da conversa
        ranked = sorted(((1 - weight) * score / top + weight * _context(state, self.turns[index]["state"]), index)
                        for score, index in candidates)[::-1]
        picked, trajectories, labels = [], set(), Counter()
        for _, index in ranked:
            item = self.turns[index]
            interpretation = item["turn"]["interpretacao"]
            label = tuple(interpretation[key] for key in ("operation", "intent", "topic", "dialogue"))
            if item["trajectory"]["id"] in trajectories or labels[label] >= 2:
                continue
            picked.append(item)
            trajectories.add(item["trajectory"]["id"])
            labels[label] += 1
            if len(picked) == k:
                break
        return picked


def _context(query: dict, example: dict) -> float:
    score = 0.0
    score += 0.35 * (query.get("active_operation") == example["active_operation"])
    score += 0.3 * (bool(query.get("has_verified_result")) == example["has_verified_result"])
    score += 0.2 * (bool(query.get("has_selection")) == example["has_selection"])
    score += 0.15 * (bool(query.get("previous_document")) == bool(example["previous_document"]))
    return score


def render(selected: list[dict], *, continuity: bool, mask, anchor=None) -> tuple[str, list[str]]:
    """Bloco de exemplos para o provedor, mascarado como as mensagens reais; exemplos incoerentes ficam de fora.

    mask(textos) aplica a mesma minimização do pedido atual; anchor(valor, texto) é o critério de âncora do
    integrador; continuity diz se o pedido real leva a projeção de continuidade. Valores que deixam de ser
    literais depois da máscara saem da saída, como faria o backend."""
    anchor = anchor or literal
    parts, ids, size = [HEADER], [], len(HEADER)
    for number, item in enumerate(selected, 1):
        previous = item["history"][-2:]
        masked = mask([*previous, item["turn"]["usuario"]])
        current, earlier = masked[-1], masked[:-1]
        output = _output(item["turn"]["interpretacao"], current, anchor)
        if output is None:
            continue
        lines = [f"Exemplo {len(ids) + 1}"]
        if continuity:
            lines.append("CONTINUIDADE_VERIFICADA: " + json.dumps(projection(item["state"]), ensure_ascii=False))
        if earlier:
            lines.append("Mensagens anteriores: " + " | ".join("«" + text + "»" for text in earlier))
        lines += ["Mensagem atual: «" + current + "»",
                  "Saída: " + json.dumps(output, ensure_ascii=False, separators=(",", ":"))]
        text = "\n".join(lines)
        if size + len(text) > MAX_BLOCK:
            break
        parts.append(text)
        ids.append(item["id"])
        size += len(text) + 2
    return ("\n\n".join(parts), ids) if ids else ("", [])


def _output(interpretation: dict, current: str, anchor) -> dict | None:
    output = {key: interpretation[key] for key in INTERPRETATION_KEYS}
    for slot in ("period", "category", "territory"):
        if output[slot] and not anchor(output[slot], current):
            output[slot] = ""
    candidates = [dict(c) for c in interpretation["candidates"] if anchor(c["anchor"], current)]
    if interpretation["candidates"] and len(candidates) < 2:
        return None  # a ambiguidade não sobrevive à máscara: o exemplo ensinaria outra coisa
    output["candidates"] = candidates
    return output


_LOCK = threading.Lock()
_LOADED: dict = {}


def library() -> Library:
    """Carga única por processo (o arquivo é lido na primeira mensagem que chega ao provedor)."""
    with _LOCK:
        if "library" not in _LOADED:
            records, version = read()
            _LOADED["library"] = Library(records, version)
        return _LOADED["library"]
