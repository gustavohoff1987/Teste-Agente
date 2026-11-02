"""Publica o resumo do relatório sanitizado da validação real do Gemini nas anotações da execução (02/11/2026; comando de
ajustes antes da Fase 2, seções 5 e 7): sem o GitHub CLI e sem extrair tokens, o agente acompanha pela API pública do
GitHub, que entrega as anotações sem login, mas não o log nem os artefatos.

Lê o relatório que validar_gemini_conteiner.py gravou e que verificar_chave_google.py já conferiu, e confere de novo o
padrão de chave em cada anotação: a que o contiver não sai. Só números, estados e os nomes das etapas e dos cenários;
nenhum texto de mensagem ou de resposta (o relatório não os tem).

Uso (no workflow): python .github/scripts/anotar_validacao.py "$RUNNER_TEMP/relatorio/validacao-gemini-real.json"
"""
import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from verificar_chave_google import PADROES  # noqa: E402

ROTEIRO, CHAVE_INVALIDA = "roteiro validar_gemini_real.py", "chave inválida"
LIMITE = 3000  # caracteres por anotação, com folga


def campos(dados: dict, sem=()) -> str:
    """Os campos presentes, na ordem do relatório: "status 200, tempo_s 2.1, chamadas 1"."""
    return ", ".join(f"{chave} {valor}" for chave, valor in dados.items() if chave not in sem and valor is not None) or "—"


def linha(etapa: dict) -> str:
    return f"{etapa.get('etapa')}: " + campos(etapa, sem=("etapa", "turnos"))


def anotacoes(relatorio: dict) -> list[tuple[str, str]]:
    """(título, texto): o resumo, as etapas pelo caminho HTTP do contêiner, o roteiro (um turno por linha) e a chave
    inválida. No máximo quatro anotações, abaixo do limite de anotações por passo."""
    motivo = relatorio.get("interrompida")
    saida = [("Validação real: resumo", f"teto {relatorio.get('teto')}; chamadas reais usadas {relatorio.get('chamadas_usadas')}; "
              + (f"interrompida: {motivo}" if motivo else "sem interrupção") + f"; {relatorio.get('data')}")]
    etapas = relatorio.get("etapas") or []
    http = [e for e in etapas if e.get("etapa") not in (ROTEIRO, CHAVE_INVALIDA)]
    if http:
        saida.append(("Validação real: caminho HTTP do contêiner", "\n".join(linha(e) for e in http)))
    for etapa in (e for e in etapas if e.get("etapa") == ROTEIRO):
        turnos = [f"- {t.get('cenario')}: " + campos(t, sem=("cenario",)) for t in etapa.get("turnos") or []]
        saida.append(("Validação real: " + ROTEIRO, "\n".join([linha(etapa), *turnos])))
    for etapa in (e for e in etapas if e.get("etapa") == CHAVE_INVALIDA):
        saida.append(("Validação real: " + CHAVE_INVALIDA, linha(etapa)))
    return [(titulo, texto[:LIMITE]) for titulo, texto in saida]


def escapar(texto: str, propriedade: bool = False) -> str:
    """O escape dos comandos de workflow do GitHub Actions (no título, também ":" e ",")."""
    texto = texto.replace("%", "%25").replace("\r", "%0D").replace("\n", "%0A")
    return texto.replace(":", "%3A").replace(",", "%2C") if propriedade else texto


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("relatorio", type=Path)
    argumentos = parser.parse_args(argv)
    if not argumentos.relatorio.is_file():
        print("::warning title=Validação real::sem relatório: a validação terminou antes de gravá-lo (ver o log da execução)",
              flush=True)
        return 1
    omitidas = 0
    for titulo, texto in anotacoes(json.loads(argumentos.relatorio.read_text(encoding="utf-8"))):
        if any(padrao.search((titulo + texto).encode("utf-8")) for padrao in PADROES.values()):
            omitidas += 1
            continue
        print(f"::notice title={escapar(titulo, propriedade=True)}::{escapar(texto)}", flush=True)
    if omitidas:
        print(f"::error title=Padrão de chave do Google::{omitidas} anotação(ões) omitida(s); nada do trecho foi mostrado",
              flush=True)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
