"""Provedor Gemini simulado por HTTP, no formato real da API (generateContent), para os testes do contêiner e do pytest.

O backend chega aqui por ADT_GEMINI_ENDERECO_DE_TESTE (llm_bridge._endereco), que só aceita a própria máquina; a chave enviada
é qualquer texto e nunca é registrada. Nenhuma rede externa. Gatilhos na mensagem atual da pessoa (sem acento, minúsculas):

- "simule demora N" (segundos, com ponto decimal): responde com sucesso depois de N s;
- "simule tempo esgotado": espera 90 s, mais que os 75 s do cliente HTTP do backend;
- "simule erro 500" e "simule erro 503": falha do provedor;
- "simule chave recusada" (403 PERMISSION_DENIED) e "simule chave invalida" (400 INVALID_ARGUMENT com API_KEY_INVALID, a
  resposta real para uma chave inválida);
- "simule cota minuto" e "simule cota dia": 429 RESOURCE_EXHAUSTED com QuotaFailure e RetryInfo, como a API devolve;
- "simule fora do contrato": 200 com um texto que não é o JSON pedido (o backend regenera e, no fim, usa a reserva).

Sem gatilho: uma interpretação válida do contrato (llm_bridge._schema) ou, na redação, a resposta verificada do sistema com
outra abertura, que passa pela conferência de fidelidade. GET /contagem devolve as chamadas recebidas; POST /zerar as zera.

Uso: python backend/tests/serve_gemini_http.py --porta 18300
"""
import argparse
import json
import re
import threading
import time
import unicodedata
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

PREFIXOS_DE_CONTEXTO = ("CONTEXTO_VERIFICADO_PELO_BACKEND", "CONTEXTO_DA_CONVERSA", "CONTINUIDADE_VERIFICADA",
                        "VIOLACOES_DA_TENTATIVA")
_lock = threading.Lock()
_chamadas = {"total": 0, "por_gatilho": {}}


def _sem_acento(texto: str) -> str:
    return "".join(c for c in unicodedata.normalize("NFKD", texto.casefold()) if not unicodedata.combining(c))


def _erro(codigo: int, status: str, mensagem: str, detalhes=None) -> tuple[int, dict]:
    return codigo, {"error": {"code": codigo, "message": mensagem, "status": status, "details": detalhes or []}}


def _cota(escopo: str) -> tuple[int, dict]:
    quota = ("GenerateRequestsPerDayPerProjectPerModel-FreeTier" if escopo == "dia"
             else "GenerateRequestsPerMinutePerProjectPerModel-FreeTier")
    detalhes = [{"@type": "type.googleapis.com/google.rpc.QuotaFailure", "violations": [{
        "quotaMetric": "generativelanguage.googleapis.com/generate_content_free_tier_requests", "quotaId": quota,
        "quotaDimensions": {"location": "global", "model": "gemini-3.5-flash-lite"}, "quotaValue": "10"}]},
        {"@type": "type.googleapis.com/google.rpc.Help", "links": [{"description": "Learn more", "url": "https://ai.google.dev"}]},
        {"@type": "type.googleapis.com/google.rpc.RetryInfo", "retryDelay": "3s" if escopo == "minuto" else "47s"}]
    return _erro(429, "RESOURCE_EXHAUSTED", "You exceeded your current quota, please check your plan and billing details.",
                 detalhes)


def _sucesso(resultado: dict) -> tuple[int, dict]:
    return 200, {"candidates": [{"content": {"parts": [{"text": json.dumps(resultado, ensure_ascii=False)}], "role": "model"},
                                 "finishReason": "STOP"}],
                 "usageMetadata": {"promptTokenCount": 100, "candidatesTokenCount": 20, "totalTokenCount": 120},
                 "modelVersion": "gemini-3.5-flash-lite"}


def _interpretacao(atual: str) -> dict:
    if "distribui" in atual:
        operacao, indicador = "distribution", "density"
    elif "densidade" in atual:
        operacao, indicador = "density", "density"
    else:
        operacao, indicador = "none", "none"
    return {"operation": operacao, "indicator": indicador, "period": "", "category": "", "territory": "",
            "intent": "ANALITICO" if operacao != "none" else "CONVERSACIONAL", "topic": "none"}


def responder(corpo: dict) -> tuple[int, dict, str, float]:
    """(status, corpo da resposta, gatilho, espera em segundos) para um pedido generateContent."""
    textos = [parte.get("text", "") for conteudo in corpo.get("contents") or [] for parte in conteudo.get("parts") or []]
    pessoa = [t for t in textos if not t.startswith(PREFIXOS_DE_CONTEXTO)]
    atual = _sem_acento(pessoa[-1] if pessoa else "")
    redacao = set(((corpo.get("generationConfig") or {}).get("responseSchema") or {}).get("properties", {})) == {"resposta"}
    espera = 0.0
    achado = re.search(r"simule demora (\d+(?:\.\d+)?)", atual)
    if achado:
        espera = min(60.0, float(achado.group(1)))
    if "simule tempo esgotado" in atual:
        return 200, {}, "tempo_esgotado", 90.0
    for marca, resposta in (("simule erro 500", _erro(500, "INTERNAL", "Internal error encountered.")),
                            ("simule erro 503", _erro(503, "UNAVAILABLE", "The model is overloaded. Please try again later.")),
                            ("simule chave recusada", _erro(403, "PERMISSION_DENIED", "Permission denied on resource.")),
                            ("simule chave invalida", _erro(400, "INVALID_ARGUMENT", "API key not valid. Please pass a valid API key.",
                                                            [{"@type": "type.googleapis.com/google.rpc.ErrorInfo",
                                                              "reason": "API_KEY_INVALID", "domain": "googleapis.com"}])),
                            ("simule cota minuto", _cota("minuto")), ("simule cota dia", _cota("dia"))):
        if marca in atual:
            return resposta[0], resposta[1], marca.replace("simule ", "").replace(" ", "_"), espera
    if "simule fora do contrato" in atual:
        return 200, {"candidates": [{"content": {"parts": [{"text": "isto não é o JSON pedido"}]}}]}, "fora_do_contrato", espera
    if redacao:
        contexto = next((t for t in textos if t.startswith("CONTEXTO_DA_CONVERSA: ")), "")
        try:
            cartao = json.loads(contexto[len("CONTEXTO_DA_CONVERSA: "):]) if contexto else {}
        except ValueError:
            cartao = {}
        verificada = cartao.get("resposta_verificada_do_sistema") or ""
        return (*_sucesso({"resposta": ("Em outras palavras: " + verificada) if verificada else ""}), "redacao", espera)
    return (*_sucesso(_interpretacao(atual)), "demora" if achado else "sucesso", espera)


class Manipulador(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"

    def log_message(self, *args):  # sem log: nenhuma chave nem mensagem é registrada
        pass

    def _json(self, status: int, corpo: dict):
        dados = json.dumps(corpo, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(dados)))
        self.end_headers()
        self.wfile.write(dados)

    def do_GET(self):
        if self.path.startswith("/contagem"):
            with _lock:
                self._json(200, json.loads(json.dumps(_chamadas)))
        else:
            self._json(404, {})

    def do_POST(self):
        tamanho = int(self.headers.get("Content-Length") or 0)
        bruto = self.rfile.read(tamanho) if tamanho else b""
        if self.path.startswith("/zerar"):
            with _lock:
                _chamadas.update(total=0, por_gatilho={})
            self._json(200, {"zerado": True})
            return
        if ":generateContent" not in self.path or not self.headers.get("x-goog-api-key"):
            self._json(*_erro(401, "UNAUTHENTICATED", "Request had invalid authentication credentials."))
            return
        try:
            corpo = json.loads(bruto or b"{}")
        except ValueError:
            self._json(*_erro(400, "INVALID_ARGUMENT", "Invalid JSON payload received."))
            return
        status, resposta, gatilho, espera = responder(corpo)
        with _lock:
            _chamadas["total"] += 1
            _chamadas["por_gatilho"][gatilho] = _chamadas["por_gatilho"].get(gatilho, 0) + 1
        if espera:
            time.sleep(espera)
        try:
            self._json(status, resposta)
        except (BrokenPipeError, ConnectionResetError):
            pass  # o cliente desistiu (tempo esgotado do lado do backend)


def iniciar(porta: int = 0, host: str = "127.0.0.1") -> ThreadingHTTPServer:
    """O servidor numa thread (para o pytest); devolve o servidor, com a porta em server_address[1]."""
    servidor = ThreadingHTTPServer((host, porta), Manipulador)
    servidor.daemon_threads = True
    threading.Thread(target=servidor.serve_forever, name="gemini-simulado", daemon=True).start()
    return servidor


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--porta", type=int, default=18300)
    parser.add_argument("--host", default="127.0.0.1")
    argumentos = parser.parse_args()
    servidor = ThreadingHTTPServer((argumentos.host, argumentos.porta), Manipulador)
    servidor.daemon_threads = True
    print(f"Gemini simulado em http://{argumentos.host}:{argumentos.porta}", flush=True)
    servidor.serve_forever()
