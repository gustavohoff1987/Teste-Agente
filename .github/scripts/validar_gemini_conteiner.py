"""Validação real do Gemini pelo contêiner (workflow validacao-gemini-real.yml, job "validacao"; seção 6.3 do comando de
implantação de 01/11/2026). Só roda depois da autorização expressa do responsável ("AUTORIZO A VALIDAÇÃO REAL DO GEMINI"),
uma execução por autorização, no ambiente gemini-real, com o revisor aprovando o job.

Teto rígido de --teto chamadas reais somadas (padrão 20), contadas por /api/llm/status do contêiner e pelo relatório de
scripts/validar_gemini_real.py; cada mensagem pode usar até 3 chamadas (a primeira e 2 regenerações), e nenhuma etapa começa
se o saldo não cobrir esse máximo. Um 429 real encerra a validação na hora.
1. Sem a chave (segredo vazio), nada é enviado: sai com 1 antes de qualquer pedido.
2. Autenticação e modelo: /api/llm/status (configurado, modelo gemini-3.5-flash-lite) e uma interpretação.
3. Conversa pelo caminho HTTP real do contêiner: uma pergunta sobre um resultado registrado na sessão, o pedido de explicação
   mais simples e uma pergunta conceitual.
4. scripts/validar_gemini_real.py, com --max-chamadas igual ao saldo do teto (menos 1, reservada para o passo 5); a saída
   dele (com os textos) fica fora do log e do relatório.
5. Uma chave propositalmente inválida, noutro contêiner (--url-chave-invalida): a recusa do provedor (sem consumo de cota)
   precisa aparecer como problema de configuração.
O relatório publicado (--saida) é sanitizado: status, tempos, origem do texto, tentativas e chamadas usadas; nenhum texto de
mensagem ou resposta, nenhuma chave. Antes do envio, o workflow confere o padrão de chave do Google nele.
"""
import argparse
import json
import os
import subprocess
import sys
import time
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[2]
MAXIMO_POR_MENSAGEM = 3
MODELO = "gemini-3.5-flash-lite"


def chave_configurada(ambiente=None) -> bool:
    """O segredo do ambiente chegou (sem ler nem mostrar o valor além de saber se está vazio)."""
    return bool((ambiente if ambiente is not None else os.environ).get("GEMINI_API_KEY", "").strip())


class Orcamento:
    """O teto rígido das chamadas reais somadas."""

    def __init__(self, teto: int):
        self.teto, self.usadas = teto, 0

    def cabe(self, chamadas: int = MAXIMO_POR_MENSAGEM) -> bool:
        return self.usadas + chamadas <= self.teto

    def saldo(self) -> int:
        return max(0, self.teto - self.usadas)

    def registrar(self, chamadas: int) -> None:
        self.usadas += max(0, chamadas)


class Interrompida(Exception):
    """Um 429 real, ou outro motivo que encerra a validação sem novas chamadas."""


def validar(http, orcamento: Orcamento, etapas: list) -> None:
    """Percorre o caminho HTTP real do contêiner, mensagem a mensagem, dentro do teto. `http` faz os pedidos (httpx.Client
    ou o simulado dos testes)."""
    def usadas():
        return http.get("/api/llm/status").json()["requests_used_today"]

    def mensagem(etapa, rota, **kwargs):
        if not orcamento.cabe():
            raise Interrompida(f"teto: o saldo ({orcamento.saldo()}) não cobre a etapa {etapa}")
        antes, inicio = usadas(), time.monotonic()
        resposta = http.post(rota, **kwargs)
        chamadas = usadas() - antes
        orcamento.registrar(chamadas)
        corpo = resposta.json() if resposta.status_code < 500 else {}
        indisponivel = corpo.get("indisponibilidade") or {}
        etapas.append({"etapa": etapa, "status": resposta.status_code, "tempo_s": round(time.monotonic() - inicio, 2),
                       "chamadas": chamadas, "origem": (corpo.get("redacao") or {}).get("origem") or corpo.get("origin"),
                       "tentativas": (corpo.get("redacao") or {}).get("tentativas"),
                       "indisponibilidade": indisponivel.get("tipo")})
        if indisponivel.get("tipo") == "cota":
            raise Interrompida("429 real do provedor: a validação para aqui")
        if indisponivel:
            raise Interrompida("o provedor não respondeu como esperado (" + str(indisponivel.get("tipo")) + ")")
        return corpo

    status = http.get("/api/llm/status").json()
    etapas.append({"etapa": "estado do provedor", "configurado": status.get("configured"), "modelo": status.get("model"),
                   "disponivel": status.get("disponivel")})
    if not status.get("configured") or status.get("model") != MODELO:
        raise Interrompida("o contêiner não está com a chave ou com o modelo esperado")
    mensagem("autenticação e modelo (interpretação)", "/api/llm/interpret", json={"message": "Analisar distribuição da densidade"})
    token = http.post("/api/session").json()["token"]
    sessao = {"X-ADT-Session": token}
    info = http.post("/api/inspect", data={"dataset": "brazil", "scope": "municipal"}).json()
    resultado = http.post("/api/analyze", headers=sessao, data={
        "dataset": "brazil", "scope": "municipal", "dataset_version": info["source"]["version"], "operation": "density",
        "mapping": json.dumps(info["suggested_mapping"]), "options": json.dumps({"period_filter": "202406"})}).json()
    etapas.append({"etapa": "resultado registrado na sessão (sem provedor)", "registrado": bool(resultado.get("result_id"))})
    contexto = {"dataset": "brazil", "scope": "municipal", "dataset_version": info["source"]["version"],
                "mapping": json.dumps(info["suggested_mapping"]), "options": "{}", "history": "[]",
                "displayed_result_id": resultado.get("result_id", "")}
    mensagem("pergunta sobre o resultado", "/api/llm/interpret-context", headers=sessao,
             data={**contexto, "message": "Qual território tem a maior densidade neste resultado?"})
    mensagem("explicação mais simples", "/api/llm/interpret-context", headers=sessao,
             data={**contexto, "message": "Explique de maneira mais simples"})
    mensagem("pergunta conceitual", "/api/llm/interpret", json={"message": "O que é densidade?"})


def amostra_do_roteiro(orcamento: Orcamento, etapas: list, pasta: Path) -> None:
    """scripts/validar_gemini_real.py com o saldo (menos 1, reservada à chave inválida); só os números vão ao relatório."""
    saldo = orcamento.saldo() - 1
    if saldo < MAXIMO_POR_MENSAGEM:
        etapas.append({"etapa": "roteiro validar_gemini_real.py", "pulado": f"saldo de {saldo} chamada(s)"})
        return
    saida = pasta / "saida-do-roteiro.txt"  # fica fora do relatório publicado (tem os textos das respostas)
    with saida.open("w", encoding="utf-8") as arquivo:
        feito = subprocess.run([sys.executable, str(RAIZ / "scripts" / "validar_gemini_real.py"), "--max-chamadas", str(saldo)],
                               cwd=RAIZ, stdout=arquivo, stderr=subprocess.STDOUT, timeout=1800)
    relatorios = sorted((RAIZ / ".local" / "validacao-gemini").glob("relatorio-*.json"))
    dados = json.loads(relatorios[-1].read_text(encoding="utf-8")) if relatorios else {}
    chamadas = (dados.get("resumo") or {}).get("chamadas_reais", 0)
    orcamento.registrar(chamadas)
    etapas.append({"etapa": "roteiro validar_gemini_real.py", "codigo": feito.returncode, "chamadas": chamadas,
                   "turnos": [{"cenario": t.get("cenario"), "status": t.get("status"), "canal": t.get("canal"),
                               "origem": (t.get("redacao") or {}).get("origem"),
                               "tentativas": (t.get("redacao") or {}).get("tentativas"),
                               "indisponibilidade": (t.get("indisponibilidade") or {}).get("tipo")}
                              for t in dados.get("turnos") or []]})
    if any((t.get("indisponibilidade") or {}).get("tipo") == "cota" for t in dados.get("turnos") or []):
        raise Interrompida("429 real do provedor no roteiro: a validação para aqui")


def chave_invalida(http, orcamento: Orcamento, etapas: list) -> None:
    """Uma chamada com a chave propositalmente inválida (o provedor recusa sem consumir cota): problema de configuração."""
    if not orcamento.cabe(1):
        etapas.append({"etapa": "chave inválida", "pulado": "sem saldo"})
        return
    resposta = http.post("/api/llm/interpret", json={"message": "Analisar distribuição da densidade"})
    status = http.get("/api/llm/status").json()
    orcamento.registrar(status.get("requests_used_today", 1))
    espera = status.get("espera") or {}
    etapas.append({"etapa": "chave inválida", "status": resposta.status_code,
                   "indisponibilidade": (resposta.json().get("indisponibilidade") or {}).get("tipo"),
                   "causa": espera.get("causa"), "escopo": espera.get("escopo"),
                   "mensagem_de_configuracao": espera.get("causa") == "configuracao"})


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--url", required=True)
    parser.add_argument("--url-chave-invalida", required=True)
    parser.add_argument("--teto", type=int, default=20)
    parser.add_argument("--saida", type=Path, required=True)
    argumentos = parser.parse_args(argv)
    if not chave_configurada():
        print("O segredo GEMINI_API_KEY do ambiente gemini-real está vazio: nada foi enviado ao provedor.", flush=True)
        return 1
    import httpx
    argumentos.saida.mkdir(parents=True, exist_ok=True)
    orcamento, etapas, motivo = Orcamento(argumentos.teto), [], None
    with httpx.Client(base_url=argumentos.url, timeout=180) as http:
        try:
            validar(http, orcamento, etapas)
            amostra_do_roteiro(orcamento, etapas, argumentos.saida.parent)
        except Interrompida as exc:
            motivo = str(exc)
    if motivo is None or "teto" in motivo:
        with httpx.Client(base_url=argumentos.url_chave_invalida, timeout=180) as invalida:
            chave_invalida(invalida, orcamento, etapas)
    relatorio = {"teto": argumentos.teto, "chamadas_usadas": orcamento.usadas, "interrompida": motivo, "etapas": etapas,
                 "data": time.strftime("%Y-%m-%d %H:%M:%S")}
    (argumentos.saida / "validacao-gemini-real.json").write_text(json.dumps(relatorio, ensure_ascii=False, indent=1),
                                                                 encoding="utf-8")
    print(json.dumps({k: v for k, v in relatorio.items() if k != "etapas"}, ensure_ascii=False), flush=True)
    for etapa in etapas:
        print(json.dumps(etapa, ensure_ascii=False), flush=True)
    sucesso = motivo is None and orcamento.usadas <= argumentos.teto and any(
        e.get("etapa") == "chave inválida" and e.get("mensagem_de_configuracao") for e in etapas)
    return 0 if sucesso else 1


if __name__ == "__main__":
    sys.exit(main())
