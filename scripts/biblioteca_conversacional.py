"""Manutenção da Biblioteca de Inteligência Conversacional (ferramenta de desenvolvimento, fora do produto).

Uso, na raiz do repositório, com as dependências do backend instaladas:
    python scripts/biblioteca_conversacional.py validar                  # biblioteca inteira
    python scripts/biblioteca_conversacional.py validar --arquivo X.jsonl  # um arquivo novo antes de incorporá-lo
    python scripts/biblioteca_conversacional.py estatisticas
    python scripts/biblioteca_conversacional.py consultar "e em gráfico?" --anterior "Quero a densidade" --resultado
    python scripts/biblioteca_conversacional.py avaliar                  # pertinência no conjunto inédito
    python scripts/biblioteca_conversacional.py comparar --turnos 10     # Gemini real, sem e com a biblioteca
    python scripts/biblioteca_conversacional.py comparar --provedor compativel --url http://localhost:11434/v1 \
        --modelo qwen2.5:7b                                              # Qwen, DeepSeek ou Llama em servidor local

Só o comando "comparar" chama um modelo: turnos inéditos sem base, cada um interpretado sem e com os exemplos,
comparados com a interpretação esperada e com o contrato do intérprete ("aceita"). Com o Gemini, exige
GEMINI_API_KEY e gasta a cota do projeto no Google (10 turnos = 20 chamadas). "consultar" mostra o bloco que iria ao modelo (com --base, mascarado pela base Brasil versionada, somente
em leitura).
"""
import argparse
from collections import Counter
from pathlib import Path
import random
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))
sys.path.insert(0, str(ROOT / "backend" / "tests"))

import conversation_library as biblioteca  # noqa: E402
import library_evaluation  # noqa: E402
import llm_bridge  # noqa: E402

INEDITAS = ROOT / "backend" / "tests" / "biblioteca_ineditas"


def carregar(arquivos, pasta):
    if not arquivos:
        return biblioteca.read(pasta)
    registros = []
    for arquivo in arquivos:
        lidos, _ = biblioteca.read_files([Path(arquivo)])
        registros += lidos
    return registros, "arquivos"


def validar(args):
    registros, versao = carregar(args.arquivo, Path(args.pasta))
    spec = (ROOT / "IMPLEMENTATION_SPEC.md").read_text(encoding="utf-8")
    problemas = biblioteca.validate(registros, llm_bridge.library_contract(), spec)
    for problema in problemas[:args.limite]:
        print("PROBLEMA", problema)
    turnos = sum(1 for registro in registros for _ in biblioteca.turns(registro)) if not problemas else "?"
    print(f"{len(registros)} trajetórias, {turnos} turnos, versão {versao}: "
          + ("íntegra." if not problemas else f"{len(problemas)} problema(s)."))
    return 1 if problemas else 0


def estatisticas(args):
    registros, versao = carregar(args.arquivo, Path(args.pasta))
    turnos = [item for registro in registros for item in biblioteca.turns(registro)]
    print(f"versão {versao}: {len(registros)} trajetórias e {len(turnos)} turnos "
          f"({len(turnos) / max(1, len(registros)):.1f} por trajetória)")
    for nome, chave in (("dimensão", "dimensao"), ("idioma", "idioma"), ("registro", "registro"),
                        ("perfil", "perfil"), ("fonte inicial", "fonte")):
        print(f"- {nome}: " + ", ".join(f"{k} {v}" for k, v in sorted(Counter(r[chave] for r in registros).items())))
    for nome, campo in (("operação", "operation"), ("intenção", "intent"), ("tópico", "topic"), ("diálogo", "dialogue")):
        contagem = Counter(item["turn"]["interpretacao"][campo] for item in turnos)
        print(f"- {nome}: " + ", ".join(f"{k} {v}" for k, v in contagem.most_common()))
    print("- ação: " + ", ".join(f"{k} {v}" for k, v in Counter(item["turn"]["acao"] for item in turnos).most_common()))
    longas = sum(1 for registro in registros if sum("usuario" in passo for passo in registro["passos"]) >= 6)
    print(f"- trajetórias com seis turnos ou mais: {longas}")
    return 0


def consultar(args):
    acervo = biblioteca.library()
    estado = {"fonte": "brasil" if args.base else "sem_base", "has_selection": args.selecao,
              "has_verified_result": args.resultado, "active_operation": args.operacao_ativa,
              "previous_operation": args.operacao_ativa, "previous_indicator": None, "previous_document": None}
    historico = args.anterior or []
    escolhidos = acervo.select(args.mensagem, historico, estado)
    if args.base:
        import main
        quadro = main._brazil_sources().frame("municipal")
        protegidos = llm_bridge._protected(main.protected_values(quadro, ""))
        mascara = lambda textos: llm_bridge._minimize_many(textos, protegidos)  # noqa: E731
    else:
        mascara = lambda textos: [llm_bridge._sanitize(texto) for texto in textos]  # noqa: E731
    bloco, ids = biblioteca.render(escolhidos, continuity=args.base, mask=mascara,
                                   anchor=lambda valor, texto: bool(llm_bridge._anchor(valor, texto)))
    print("Exemplos escolhidos:", ", ".join(ids) or "nenhum")
    print(bloco)
    return 0


def _ineditas(caminho):
    """Pasta ou arquivo .jsonl de trajetórias inéditas."""
    caminho = Path(caminho)
    registros, _ = biblioteca.read_files([caminho]) if caminho.is_file() else biblioteca.read(caminho)
    if not registros:
        raise SystemExit(f"Nenhuma trajetória inédita em {caminho}.")
    return registros


def avaliar(args):
    acervo = biblioteca.library()
    ineditas = _ineditas(args.ineditas)
    relatorio = library_evaluation.evaluate(acervo, ineditas)
    print(library_evaluation.table(relatorio))
    return 0


def _compativel(url, modelo, mensagens):
    """Servidor compatível com a API de chat da OpenAI (Ollama, llama.cpp, vLLM), para Qwen, DeepSeek ou Llama.

    Mesmas instruções do pedido ao Gemini; o esquema vai no texto, porque nem todo servidor aceita esquema JSON."""
    import json
    import httpx
    sistema = (llm_bridge._system_instruction() + "\n\nResponda apenas com um objeto JSON neste esquema: "
               + json.dumps(llm_bridge._schema(), ensure_ascii=False))
    corpo = {"model": modelo, "temperature": 0, "max_tokens": 600, "response_format": {"type": "json_object"},
             "messages": [{"role": "system", "content": sistema}, {"role": "user", "content": "\n\n".join(mensagens)}]}
    resposta = httpx.post(url.rstrip("/") + "/chat/completions", json=corpo, timeout=180)
    resposta.raise_for_status()
    return json.loads(resposta.json()["choices"][0]["message"]["content"])


def comparar(args):
    """Turnos inéditos sem base interpretados pelo mesmo modelo sem e com os exemplos; nada é executado."""
    import asyncio
    import json
    import os
    if args.provedor == "gemini":
        chave = os.getenv("GEMINI_API_KEY", "").strip()
        if not chave:
            print("Defina GEMINI_API_KEY para comparar com o Gemini real; nada foi enviado.")
            return 1
        modelo = llm_bridge._configured_model()

        def chamar(mensagens):
            return asyncio.run(llm_bridge._call_gemini(mensagens, modelo, chave))
    else:
        if not args.url or not args.modelo:
            print("Informe --url (ex.: http://localhost:11434/v1) e --modelo do servidor compatível; nada foi enviado.")
            return 1

        def chamar(mensagens):
            return _compativel(args.url, args.modelo, mensagens)
    acervo = biblioteca.library()
    ineditas = _ineditas(args.ineditas)
    turnos = [item for registro in ineditas for item in biblioteca.turns(registro)
              if biblioteca.mode(item["state"]) == "sem_base"]
    amostra = random.Random(args.semente).sample(turnos, min(args.turnos, len(turnos)))
    campos = ("operation", "indicator", "intent", "topic", "dialogue")
    vazio = {"operation": "none", "indicator": "none", "period": "", "category": "", "territory": "",
             "intent": "CONVERSACIONAL", "topic": "none", "dialogue": "none", "social_reply": "", "candidates": []}
    acertos = {"sem": Counter(), "com": Counter()}
    registros = []
    for item in amostra:
        mensagens = [llm_bridge._sanitize(texto) for texto in [*item["history"], item["turn"]["usuario"]]]
        escolhidos = acervo.select(item["turn"]["usuario"], item["history"], item["state"])
        bloco, ids = biblioteca.render(escolhidos, continuity=False,
                                       mask=lambda textos: [llm_bridge._sanitize(t) for t in textos],
                                       anchor=lambda valor, texto: bool(llm_bridge._anchor(valor, texto)))
        esperado = item["turn"]["interpretacao"]
        for nome, exemplos in (("sem", ""), ("com", bloco)):
            token = llm_bridge._EXAMPLES.set(exemplos)
            try:
                saida = chamar(mensagens)
            except Exception as erro:  # noqa: BLE001 - ferramenta: registra e encerra sem repetir chamadas
                print("Falha do provedor:", erro)
                return 1
            finally:
                llm_bridge._EXAMPLES.reset(token)
            completa = {**vazio, **(saida if isinstance(saida, dict) else {})}
            acertos[nome]["turnos"] += 1
            acertos[nome]["aceita"] += not llm_bridge._library_check(completa, mensagens)
            acertos[nome]["rotulo"] += library_evaluation.label(completa) == library_evaluation.label(esperado)
            for campo in campos:
                acertos[nome][campo] += completa[campo] == esperado[campo]
            registros.append({"turno": item["id"], "biblioteca": nome, "exemplos": ids if nome == "com" else [],
                              "esperado": library_evaluation.label(esperado), "obtido": library_evaluation.label(completa)})
    for nome in ("sem", "com"):
        total = acertos[nome]["turnos"] or 1
        print(f"{nome} biblioteca: " + ", ".join(f"{campo} {acertos[nome][campo] / total:.0%}"
                                                  for campo in ("rotulo", "aceita", *campos)) + f" ({total} turnos)")
    if args.registro:
        Path(args.registro).write_text("".join(json.dumps(r, ensure_ascii=False) + "\n" for r in registros), encoding="utf-8")
    return 0


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = parser.add_subparsers(dest="comando", required=True)
    for nome in ("validar", "estatisticas"):
        item = sub.add_parser(nome)
        item.add_argument("--arquivo", action="append", default=[])
        item.add_argument("--pasta", default=str(biblioteca.TRAJECTORIES))
        item.add_argument("--limite", type=int, default=200)
    item = sub.add_parser("consultar")
    item.add_argument("mensagem")
    item.add_argument("--anterior", action="append")
    item.add_argument("--base", action="store_true")
    item.add_argument("--selecao", action="store_true")
    item.add_argument("--resultado", action="store_true")
    item.add_argument("--operacao-ativa", default=None)
    item = sub.add_parser("avaliar")
    item.add_argument("--ineditas", default=str(INEDITAS))
    item = sub.add_parser("comparar")
    item.add_argument("--provedor", choices=("gemini", "compativel"), default="gemini")
    item.add_argument("--url", help="servidor compatível com a API de chat da OpenAI, ex.: http://localhost:11434/v1")
    item.add_argument("--modelo", help="nome do modelo no servidor compatível, ex.: qwen2.5:7b")
    item.add_argument("--ineditas", default=str(INEDITAS))
    item.add_argument("--turnos", type=int, default=10)
    item.add_argument("--semente", type=int, default=20261020)
    item.add_argument("--registro", help="arquivo .jsonl com o rótulo esperado e o obtido em cada turno")
    args = parser.parse_args()
    return {"validar": validar, "estatisticas": estatisticas, "consultar": consultar, "avaliar": avaliar,
            "comparar": comparar}[args.comando](args)


if __name__ == "__main__":
    sys.exit(main())
