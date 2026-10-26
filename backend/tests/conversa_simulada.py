"""Simulador da página única para os testes da conversa (desafio adversarial, 26/10/2026): faz o papel da tela, sem navegador.

Roteia cada mensagem como frontend/src/AnalysisAssistant.tsx: o pedido de resumo ("o que esse gráfico mostra?") é
respondido com a frase-resumo do motor, como na tela; os demais vão ao intérprete local (/api/exploration/interpret) e, sem
resposta local, ao intérprete contextual (/api/llm/interpret-context). Guarda a memória da conversa como a tela guarda
(a pendência de esclarecimento com as alternativas, a comparação pendente, os estados anteriores do gráfico e a memória que
a resposta devolve) e aplica o campo `painel` ao estado do gráfico numa versão simplificada de
painelModel.aplicarPedido. Depois, pede o gráfico ao motor (/api/painel) com a sessão, para a conversa ler o resultado em
exibição pelo `displayed_result_id`, como na tela. Nada é calculado aqui: os números são os do motor.

Serve aos testes do gestor de diálogo e à avaliação adversarial (antes e depois). Não substitui os roteiros de navegador.
"""
import json
import re
import unicodedata

BRASIL_JUNHOS = ["202106", "202206", "202306", "202406"]
RESUMO = re.compile(r"^(?:(?:e|entao|agora|me|pode|por favor) )*(?:o que (?:esse|este|o) (?:grafico|mapa|resultado) mostra|"
                    r"o que (?:eu )?(?:estou|to) vendo|resuma(?: o grafico| o resultado)?)(?: (?:aqui|ai|agora|por favor))*$")


def dobra(texto):
    """Minúsculas, sem acentos e com a pontuação final fora (como normalizeCommand da tela)."""
    simples = "".join(c for c in unicodedata.normalize("NFD", str(texto).lower()) if not unicodedata.combining(c))
    return " ".join(re.sub(r"[.,!?;:]", " ", simples).split())


class Turno:
    """Uma resposta da conversa como a tela a recebe."""

    def __init__(self, canal, status, corpo, aplicado):
        self.canal, self.status, self.corpo, self.aplicado = canal, status, corpo or {}, aplicado
        self.texto = self.corpo.get("clarification") or self.corpo.get("reply") or self.corpo.get("detail") or ""
        if not isinstance(self.texto, str):
            self.texto = json.dumps(self.texto, ensure_ascii=False)
        self.painel = self.corpo.get("painel")
        self.alternativas = [c for c in self.corpo.get("choices") or (self.corpo.get("clarification") or {}).get("choices", [])
                             if isinstance(c, dict)] if isinstance(self.corpo.get("choices") or
                                                                    self.corpo.get("clarification"), (list, dict)) else []

    def __repr__(self):
        return f"<Turno {self.canal} {self.status}: {self.texto[:160]!r} painel={self.painel}>"


class Tela:
    """Estado do gráfico e da conversa de uma aba da página única com a base do Brasil."""

    def __init__(self, client, info, competencia="202406"):
        self.client, self.info = client, info
        self.version = info["source"]["version"]
        self.mapping = info["suggested_mapping"]
        self.sessao = client.post("/api/session").json()["token"]
        self.revisao = 0
        self.familia, self.indicador, self.nivel = "distribuicao", "densidade", "municipios"
        self.municipios = {"todos": False, "estados": [], "ids": []}
        self.estados = None
        self.competencia, self.janela = competencia, list(BRASIL_JUNHOS)
        self.comparar, self.referencia, self.ordenar, self.condicoes, self.grupos = None, None, None, None, None
        self.vista = "grafico"
        self.resposta, self.result_id = None, ""
        self.pendente = None  # esclarecimento com alternativas ainda sem resposta
        self.pendencia_territorial = None  # "compare Manaus" -> "com qual outro?"
        self.memoria = None  # devolvida pelo backend (gestor de diálogo)
        self.anteriores = []  # estados do gráfico antes de cada pedido aplicado pela conversa
        self.historico = []  # mensagens do usuário (as quatro últimas vão ao intérprete contextual)
        self.turnos = []

    # ------------------------------------------------------------------ estado do gráfico
    def _estado(self):
        return {"familia": self.familia, "indicador": self.indicador, "nivel": self.nivel,
                "municipios": json.loads(json.dumps(self.municipios)), "estados": self.estados,
                "competencia": self.competencia, "janela": list(self.janela), "comparar": self.comparar,
                "referencia": self.referencia, "ordenar": self.ordenar, "condicoes": self.condicoes, "grupos": self.grupos,
                "vista": self.vista}

    def _restaura(self, estado):
        for chave, valor in estado.items():
            setattr(self, chave, json.loads(json.dumps(valor)))

    def ids_no_grafico(self):
        return [item["id"] for item in (self.resposta or {}).get("itens", [])]

    def pedido_do_estado(self):
        """O estado do gráfico como um pedido que a conversa pode reaplicar (para os estados anteriores)."""
        pedido = {"familia": self.familia, "indicador": self.indicador, "nivel": self.nivel,
                  "municipios": json.loads(json.dumps(self.municipios)), "competencia": self.competencia}
        if self.familia == "tendencia":
            pedido["janela"] = list(self.janela)
        if self.comparar:
            pedido.update(funcao="comparar", selecao=list(self.comparar))
        return pedido

    def rotulo_do_estado(self):
        return (self.resposta or {}).get("resumo", {}).get("texto", "")[:120] or self.familia

    def aplica(self, painel):
        """Versão simplificada de painelModel.aplicarPedido: só as chaves não nulas mudam o estado."""
        if not isinstance(painel, dict):
            return False
        mudou = False
        self.anteriores.append({"rotulo": self.rotulo_do_estado(), "pedido": self.pedido_do_estado(), "estado": self._estado()})
        self.anteriores = self.anteriores[-10:]
        if painel.get("indicador") in ("densidade", "quantidade"):
            self.indicador, mudou = painel["indicador"], True
        if isinstance(painel.get("municipios"), dict):
            m = painel["municipios"]
            self.municipios = {"todos": m.get("todos") is True, "estados": list(m.get("estados") or []),
                               "ids": list(m.get("ids") or [])}
            self.nivel, mudou = "municipios", True
        if painel.get("nivel") in ("estados", "municipios", "brasil"):
            self.nivel, mudou = painel["nivel"], True
        if isinstance(painel.get("competencia"), str):
            self.competencia, mudou = painel["competencia"], True
        if isinstance(painel.get("janela"), list) and len(painel["janela"]) >= 4:
            self.janela, self.familia, mudou = list(painel["janela"])[-4:], "tendencia", True
        if painel.get("familia") in ("distribuicao", "espacial", "tendencia", "rotatividade"):
            self.familia, mudou = painel["familia"], True
        selecao = [s for s in painel.get("selecao") or [] if isinstance(s, str)]
        if painel.get("funcao") == "comparar" and 2 <= len(selecao) <= 3:
            self.comparar, mudou = selecao, True
            if all(s.startswith("uf:") for s in selecao):
                self.nivel, self.estados = "estados", [s[3:] for s in selecao]
            elif self.nivel == "municipios" and not self.municipios["todos"]:
                faltam = [s for s in selecao if s not in self.municipios["ids"]]
                if faltam and not self.municipios["estados"]:
                    self.municipios["ids"] = self.municipios["ids"] + faltam
        elif painel.get("funcao") and painel.get("funcao") != "comparar":
            self.comparar = None
        elif isinstance(painel.get("municipios"), dict) and self.comparar:
            ficam = [s for s in self.comparar if s in self.municipios["ids"]]
            self.comparar = ficam if len(ficam) >= 2 else None
        grupos = painel.get("grupos")
        if isinstance(grupos, dict) and grupos.get("tipo") in ("quartis", "quintis", "decis", "nenhum"):
            self.grupos = None if grupos["tipo"] == "nenhum" else {"tipo": grupos["tipo"]}
            self.familia, mudou = (self.familia if grupos["tipo"] == "nenhum" else "distribuicao"), True
        if painel.get("vista") in ("grafico", "mapa"):
            self.vista, mudou = painel["vista"], True
        if not mudou:
            self.anteriores.pop()
        return mudou

    def opcoes_do_painel(self):
        opcoes = {"nivel": self.nivel, "indicador": self.indicador, "competencia": self.competencia}
        if self.nivel == "municipios":
            opcoes["base"] = {"municipios": self.municipios}
        elif self.nivel == "estados" and self.estados:
            opcoes["estados"] = self.estados
        if self.familia == "tendencia":
            opcoes["tendencia"] = {"competencias": self.janela}
        if self.comparar:
            opcoes["comparar"] = self.comparar
        if self.grupos and self.familia == "distribuicao":
            opcoes["grupos"] = {"tipo": self.grupos["tipo"]}
        return opcoes

    def calcula(self):
        """Pede o gráfico ao motor com a sessão, como a área de análise."""
        if self.nivel == "municipios" and not (self.municipios["todos"] or self.municipios["estados"] or
                                               self.municipios["ids"]):
            self.resposta, self.result_id = None, ""
            return None
        resposta = self.client.post("/api/painel", headers={"X-ADT-Session": self.sessao}, data={
            "dataset": "brazil", "scope": "municipal", "dataset_version": self.version,
            "context_revision": str(self.revisao), "mapping": json.dumps(self.mapping),
            "options": json.dumps(self.opcoes_do_painel())})
        if resposta.status_code != 200:
            self.comparar = None  # a tela tira a função que o motor recusou e mantém o recorte
            return resposta
        self.resposta = resposta.json()
        self.result_id = (self.resposta.get("sessao") or {}).get("result_id") or ""
        return resposta

    # ------------------------------------------------------------------ conversa
    def opcoes_da_conversa(self):
        """Como conversaGrafico.opcoesDaConversa: o estado do gráfico em options (as chaves painel_* ficam no backend)."""
        opcoes = {"conversation_today": "2026-10-26"}
        if self.resposta is None:
            opcoes["painel_familia"] = None
        else:
            operacao = {"distribuicao": "counts" if self.indicador == "quantidade" else "density", "espacial": "spatial",
                        "tendencia": "temporal", "rotatividade": "rotation"}[self.familia]
            indicador = "quantity" if self.indicador == "quantidade" else "density"
            ids = [i for i in self.ids_no_grafico() if i.startswith(("code:", "name:"))] \
                if self.nivel == "municipios" and not self.municipios["todos"] else []
            periodo = {"period_filter": "", "period_filters": list(self.janela)} if self.familia == "tendencia" else \
                {"period_filter": self.competencia, "period_filters": []}
            opcoes.update({**({"territory_ids": ids} if ids else {}), "exploration_operation": operacao,
                           "exploration_indicator": indicador, "comparison_indicator": indicador,
                           "temporal_indicator": indicador, **periodo, "painel_familia": self.familia,
                           "painel_indicador": self.indicador, "painel_nivel": self.nivel,
                           "painel_municipios": self.municipios, "painel_competencia": self.competencia,
                           "painel_vista": self.vista, "painel_mapa_disponivel": self.nivel == "municipios",
                           **({"painel_janela": list(self.janela)} if self.familia == "tendencia" else {}),
                           **({"painel_resumo": self.resposta["resumo"]["texto"]} if self.resposta.get("resumo") else {})})
        if self.pendencia_territorial:
            opcoes.update(conversation_pending_operation=self.pendencia_territorial["operation"],
                          conversation_requested_count=None,
                          **({"conversation_pending_ids": self.pendencia_territorial["ids"]}
                             if self.pendencia_territorial.get("ids") else {}))
        return opcoes

    def conversa(self):
        """O que a tela envia como memória da conversa (campo `conversa`)."""
        return {"pendente": self.pendente, "memoria": self.memoria,
                "anteriores": [{"rotulo": item["rotulo"], "pedido": item["pedido"]} for item in self.anteriores[-6:]]}

    def _form(self, mensagem):
        return {"dataset": "brazil", "scope": "municipal", "dataset_version": self.version, "sheet": "",
                "mapping": json.dumps(self.mapping), "context_revision": str(self.revisao), "message": mensagem,
                "options": json.dumps(self.opcoes_da_conversa()), "conversa": json.dumps(self.conversa(), ensure_ascii=False),
                "displayed_result_id": self.result_id}

    def _aceita(self, canal, status, corpo):
        aplicado = False
        if isinstance(corpo, dict):
            if corpo.get("pending_operation"):
                self.pendencia_territorial = {"operation": corpo["pending_operation"], "ids": corpo.get("pending_ids") or []}
            elif (corpo.get("operation") or corpo.get("painel")) and not corpo.get("clarification"):
                self.pendencia_territorial = None
            if "memoria" in corpo:
                self.memoria = corpo["memoria"]
            painel = corpo.get("painel")
            antes = len(self.anteriores)
            if painel and self.aplica(painel):
                self.calcula()
                aplicado = True
            if corpo.get("desfazer"):
                # Desfazer e voltar: a tela volta ao estado guardado e o tira da pilha, sem guardar o atual.
                self.anteriores = self.anteriores[:max(0, antes - int(corpo["desfazer"]))]
        turno = Turno(canal, status, corpo, aplicado)
        alternativas = [c for c in (corpo or {}).get("choices") or [] if isinstance(c, dict)] if isinstance(corpo, dict) else []
        if alternativas:
            original = corpo.get("pedido_original") if isinstance(corpo, dict) else None
            self.pendente = {"pergunta": turno.texto, "pedido": original or (self.turnos[-1] if self.turnos else ""),
                             "alternativas": [{"rotulo": c.get("label", ""), "rascunho": c.get("draft", ""),
                                               **({"operacao": c["operation"]} if c.get("operation") else {}),
                                               **({"indicador": c["indicator"]} if c.get("indicator") else {})}
                                              for c in alternativas]}
        elif isinstance(corpo, dict) and corpo.get("modelo_de_resposta"):
            self.pendente = {"pergunta": turno.texto, "pedido": self.turnos[-1] if self.turnos else "", "alternativas": [],
                             "modelo": corpo["modelo_de_resposta"]}
        else:
            self.pendente = None
        return turno

    def diga(self, mensagem):
        """Uma mensagem do usuário, pelo mesmo caminho da tela."""
        self.turnos.append(mensagem)
        if self.resposta is not None and RESUMO.match(dobra(mensagem)):
            self.memoria = {"ato": "resumo", "topico": "resultado", "registro": "objetivo"}
            return Turno("TELA", 200, {"reply": self.resposta.get("resumo", {}).get("texto", "")}, False)
        cabecalho = {"X-ADT-Session": self.sessao}
        resposta = self.client.post("/api/exploration/interpret", headers=cabecalho, data=self._form(mensagem))
        corpo = resposta.json() if resposta.headers.get("content-type", "").startswith("application/json") else {}
        if resposta.status_code == 200 and corpo.get("handled"):
            turno = self._aceita("LOCAL", 200, corpo)
        else:
            dados = {**self._form(mensagem), "history": json.dumps(self.historico[-4:], ensure_ascii=False),
                     "context_ready": "true"}
            resposta = self.client.post("/api/llm/interpret-context", headers=cabecalho, data=dados)
            corpo = resposta.json() if resposta.headers.get("content-type", "").startswith("application/json") else {}
            if resposta.status_code == 200 and isinstance(corpo.get("exploration"), dict) and corpo["exploration"].get("handled"):
                explorado = {**corpo["exploration"], "painel": corpo["exploration"].get("painel") or corpo.get("painel")}
                if "memoria" in corpo:
                    explorado["memoria"] = corpo["memoria"]
                turno = self._aceita("CONTEXTUAL", 200, explorado)
            else:
                turno = self._aceita("CONTEXTUAL", resposta.status_code, corpo)
        self.historico.append(mensagem)
        return turno

    def continua(self, turno):
        """A continuação que a resposta pediu (`continuar`, 26/10/2026): a tela a envia sozinha depois que o motor calcula o
        gráfico novo, sem mostrá-la como mensagem da pessoa (o histórico da conversa não muda)."""
        texto = turno.corpo.get("continuar")
        assert isinstance(texto, str) and texto.strip(), turno
        historico, turnos = list(self.historico), list(self.turnos)
        resposta = self.diga(texto)
        self.historico, self.turnos = historico, turnos
        return resposta

    def seleciona(self, ids=(), estados=(), familia=None, indicador=None, comparar=None):
        """Escolha direta na tela (Seleção de Territórios e ajustes), sem a conversa."""
        self.nivel = "municipios"
        self.municipios = {"todos": False, "estados": list(estados), "ids": list(ids)}
        if familia:
            self.familia = familia
        if indicador:
            self.indicador = indicador
        self.comparar = list(comparar) if comparar else None
        return self.calcula()
