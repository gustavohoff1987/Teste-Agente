"""Amostra dirigida de interações com o Gemini real (seção 12 da missão de 26/10/2026), fora do CI.

Percorre, com a base do Brasil versionada (somente leitura) e o mesmo caminho da página única (o simulador da tela,
backend/tests/conversa_simulada.py), um conjunto pequeno e delimitado de cenários: integridade da triagem (sem chamada),
continuidade, explicação do resultado, explicação progressiva, outra formulação, paráfrase metodológica, cobertura
funcional e governança. Cada resposta mostra o canal, a origem do texto (GEMINI_VALIDADO, quando o texto do Gemini passou
na conferência de fidelidade; DETERMINISTICA, quando valeu a reserva) e o número de tentativas.

Economia de franquia: o roteiro para antes de passar de --max-chamadas chamadas reais (padrão 14), contadas pelo
monitoramento do backend; um sinal de limite do provedor encerra a amostra. Nada habilita faturamento. Sem GEMINI_API_KEY,
nada é enviado e o roteiro diz isso.

Uso, na raiz do repositório:
    GEMINI_API_KEY=... python scripts/validar_gemini_real.py [--max-chamadas 14]
O relatório fica em .local/validacao-gemini/ (JSON) e é impresso no terminal.
"""
import argparse
import json
import os
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))
sys.path.insert(0, str(ROOT / "backend" / "tests"))

CENARIOS = [
    # (cenário, mensagem, seleção antes da mensagem ou None)
    ("B continuidade", "Compare Rio de Janeiro com Porto Alegre.", None),
    ("B continuidade", "Município.", None),
    ("B continuidade", "E em relação à população?", None),
    ("C explicação", "Explique esse resultado.", None),
    ("D progressiva", "Explique de um jeito mais simples.", None),
    ("D progressiva", "E o que isso quer dizer para Porto Alegre?", None),
    ("D progressiva", "Agora explique de maneira mais técnica.", None),
    ("E liberdade", "Me conta de outro jeito o que esse gráfico está mostrando.", None),
    ("F paráfrase", "O que é densidade, sem termos técnicos?", None),
    ("F paráfrase", "Não entendi a aceleração.", "tendencia"),
    ("G cobertura", "O que mais dá para fazer nesta página com esses dados?", None),
    ("H governança", "Recomende uma política para aumentar os médicos de Porto Alegre.", None),
    ("H governança", "Qual foi a causa dessa diferença entre as duas cidades?", None),
]
TRIAGEM = ["Não era isso que eu queria.", "Município.", "Caiu em 2023?", "Compare Rio de Janeiro com Porto Alegre.",
           "Meu CPF é 123.456.789-09 e o Dr. Severino Quaresma atende em Manaus?"]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("--max-chamadas", type=int, default=14)
    args = parser.parse_args()
    if not os.getenv("GEMINI_API_KEY", "").strip():
        print("Defina GEMINI_API_KEY para a validação real; nada foi enviado ao provedor.")
        return 1
    import main as backend
    import llm_bridge
    import triagem
    from fastapi.testclient import TestClient
    from conversa_simulada import Tela

    relatorio = {"data": time.strftime("%Y-%m-%d %H:%M"), "modelo": llm_bridge.status()["model"],
                 "triagem": [{"original": t, "enviado": triagem.preparar(t)} for t in TRIAGEM], "turnos": []}
    print("A. Integridade da triagem (sem chamada):")
    for item in relatorio["triagem"]:
        print("  ", item["original"], "->", item["enviado"])
    client = TestClient(backend.app)
    info = client.post("/api/inspect", data={"dataset": "brazil", "scope": "municipal"}).json()
    tela = Tela(client, info)
    inicio = llm_bridge.status()["requests_used_today"]
    for cenario, mensagem, preparo in CENARIOS:
        usadas = llm_bridge.status()["requests_used_today"] - inicio
        if usadas >= args.max_chamadas:
            print("Teto da amostra atingido (" + str(usadas) + " chamadas); o restante fica de fora.")
            break
        if preparo == "tendencia" and tela.comparar:
            tela.familia = "tendencia"
            tela.calcula()
        turno = tela.diga(mensagem)
        corpo = turno.corpo
        registro = {"cenario": cenario, "mensagem": mensagem, "canal": turno.canal, "status": turno.status,
                    "texto": turno.texto, "redacao": corpo.get("redacao"), "indisponibilidade": corpo.get("indisponibilidade"),
                    "reserva": corpo.get("reserva", False), "mudou_o_grafico": turno.aplicado,
                    "chamadas_acumuladas": llm_bridge.status()["requests_used_today"] - inicio}
        relatorio["turnos"].append(registro)
        origem = (registro["redacao"] or {}).get("origem", "LOCAL")
        print("\n[" + cenario + "] " + mensagem + "\n  canal " + turno.canal + " · origem " + origem +
              " · tentativas " + str((registro["redacao"] or {}).get("tentativas", 0)) + "\n  " +
              turno.texto.replace("\n", "\n  "))
        if registro["indisponibilidade"]:
            print("O provedor ficou indisponível (" + registro["indisponibilidade"]["tipo"] + "); a amostra para aqui.")
            break
    relatorio["status_final"] = llm_bridge.status()
    validados = sum(1 for t in relatorio["turnos"] if (t["redacao"] or {}).get("origem") == "GEMINI_VALIDADO")
    reservas = sum(1 for t in relatorio["turnos"] if (t["redacao"] or {}).get("origem") == "DETERMINISTICA")
    relatorio["resumo"] = {"turnos": len(relatorio["turnos"]), "redigidos_pelo_gemini_e_aprovados": validados,
                           "reserva_verificada": reservas,
                           "chamadas_reais": relatorio["status_final"]["requests_used_today"] - inicio}
    pasta = ROOT / ".local" / "validacao-gemini"
    pasta.mkdir(parents=True, exist_ok=True)
    caminho = pasta / ("relatorio-" + time.strftime("%Y%m%d-%H%M%S") + ".json")
    caminho.write_text(json.dumps(relatorio, ensure_ascii=False, indent=2, default=str), encoding="utf-8")
    print("\nResumo:", json.dumps(relatorio["resumo"], ensure_ascii=False), "\nRelatório:", caminho)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
