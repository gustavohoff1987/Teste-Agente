"""Requisições, bytes e tempos da jornada do Bloco 1 no navegador; nunca registra linhas da base.

Requer um servidor local (serve_ui_offline.py) com o catálogo desejado:
    ADT_UI_URL=http://127.0.0.1:18000/ python backend/tests/bench_ui_journey.py [--json saida.json]
Não captura telas. Por etapa: duração, requisições, abortadas, KiB, tarefas longas e pré-exames
repetidos (carga já enviada antes) ou idênticos ao vigente (mesma carga do último pré-exame
concluído). Cargas aparecem só como impressão digital curta (SHA-256 dos parâmetros).
"""
import argparse
import hashlib
import json
import os
import re
import time
from pathlib import Path

from playwright.sync_api import sync_playwright, expect
from ui_support import URL, offline

LONG_TASKS = """() => { window.__long = []; new PerformanceObserver(list => {
  for (const entry of list.getEntries()) window.__long.push(entry.duration); }).observe({entryTypes: ['longtask']}); }"""
TOGGLE = """async (code) => {
  const box = [...document.querySelectorAll('#resultados details input[type=checkbox]')]
    .find(input => input.parentElement.textContent.includes('[' + code + ']'));
  const start = performance.now(); box.click();
  await new Promise(resolve => requestAnimationFrame(() => setTimeout(resolve, 0)));
  return performance.now() - start;
}"""


def payload_key(request):
    """Corpo multipart sem os delimitadores, que mudam a cada envio."""
    body = request.post_data or ""
    return "\n".join(line for line in body.splitlines() if not line.startswith("------"))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--json", type=Path)
    args = parser.parse_args()
    steps, current = [], {"name": "início", "requests": []}
    pending, seen, vigente = {}, set(), {"payload": None}
    origin = time.perf_counter()
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True, channel=os.getenv("ADT_BROWSER_CHANNEL", "chrome"))
        context = browser.new_context(viewport={"width": 1280, "height": 900})
        offline(context)
        page = context.new_page()

        def started(request):
            if "/api/" not in request.url:
                return
            entry = {"endpoint": request.url.split("/api/")[1], "t0": time.perf_counter() - origin}
            if entry["endpoint"] == "preflight":
                key = payload_key(request)
                entry.update(payload=hashlib.sha256(key.encode()).hexdigest()[:8],
                             repeated=key in seen, same_as_current=key == vigente["payload"])
                seen.add(key)
                entry["key"] = key
            pending[request] = entry

        def ended(request, aborted):
            entry = pending.pop(request, None)
            if entry is None:
                return
            response = None if aborted else request.response()
            entry.update(status=response.status if response else None, aborted=aborted,
                         kib=(len(response.body()) if response else 0) / 1024,
                         s=time.perf_counter() - origin - entry["t0"])
            key = entry.pop("key", None)
            if key is not None and not aborted and entry["status"] == 200:
                vigente["payload"] = key
            current["requests"].append(entry)

        page.on("request", started)
        page.on("requestfinished", lambda request: ended(request, False))
        page.on("requestfailed", lambda request: ended(request, True))
        chat = page.locator("#assistente")
        inline = page.locator("#preparacao-conversacional")
        selection = page.get_by_role("region", name="Seleção territorial compartilhada")
        history = page.get_by_role("navigation", name="Histórico de resultados")

        def step(name, action):
            nonlocal current
            current = {"name": name, "requests": []}
            page.evaluate("() => { window.__long = []; }")
            start = time.perf_counter()
            action()
            page.wait_for_timeout(400)  # recolhe pré-exames disparados pela própria etapa
            current["s"] = time.perf_counter() - start
            current["long_tasks_ms"] = page.evaluate("() => window.__long || []")
            steps.append(current)
            calls = current["requests"]
            checks = [c for c in calls if c["endpoint"] == "preflight"]
            print(f"{name:<34} {current['s']:6.2f}s requisições={len(calls):2d} abortadas={sum(c['aborted'] for c in calls)} "
                  f"KiB={sum(c['kib'] for c in calls):8.1f} repetidos={sum(c['repeated'] for c in checks)} "
                  f"iguais_ao_vigente={sum(c['same_as_current'] for c in checks)} "
                  f"longas={sum(current['long_tasks_ms']):6.0f}ms " + ", ".join(sorted({c['endpoint'] for c in calls})), flush=True)

        def send(message):
            chat.locator("#assistant-input").fill(message)
            chat.get_by_role("button", name="Enviar mensagem", exact=True).click()
            expect(chat.locator("#assistant-input")).to_be_enabled(timeout=120000)

        def calculate(count):
            button = inline.get_by_role("button", name="Calcular e mostrar resultado", exact=True)
            expect(button).to_be_enabled(timeout=120000)
            button.click()
            expect(history.locator("ol > li")).to_have_count(count, timeout=120000)

        page.add_init_script("(" + LONG_TASKS + ")()")
        page.goto(URL)
        page.get_by_role("button", name="Li e concordo", exact=True).click()
        send("Olá")
        step("1 dados do Brasil", lambda: (chat.get_by_role("button", name="Usar dados do Brasil").click(), expect(
            chat.get_by_text("Os dados do Brasil já estão disponíveis.", exact=False)).to_be_visible(timeout=120000)))
        step("2 pergunta Amazonas", lambda: (send("Mostre a densidade médica dos municípios do Amazonas em junho de 2024."),
                                             expect(selection.get_by_text(re.compile(r"^[1-9]\d* selecionados$"))).to_be_visible(timeout=120000)))
        step("3 densidade (resultado)", lambda: calculate(1))

        def choose_trio():
            selection.get_by_role("button", name="Limpar seleção", exact=True).click()
            for code in ("130260", "130420", "130340"):
                selection.get_by_role("searchbox").fill(code)
                selection.get_by_role("checkbox").check()
            expect(selection.get_by_text("3 selecionados", exact=True)).to_be_visible()
        step("4 seleção Manaus/Tefé/Parintins", choose_trio)
        step("5 comparação", lambda: (send("Compare os selecionados."), inline.get_by_label(
            "As medidas, unidades e populações são comparáveis entre os territórios.").check(), calculate(2)))
        step("6 evolução", lambda: (send("Mostre a evolução dos municípios selecionados."),
                                    inline.get_by_label("Confirmo que os quantitativos e os períodos são comparáveis.").check(),
                                    inline.get_by_label("Os territórios correspondem às mesmas unidades ao longo do tempo.").check(),
                                    calculate(3)))

        def aggregate():
            send("Agregue os municípios selecionados.")
            inline.get_by_label("Escolher períodos da análise").click()
            inline.get_by_role("button", name="junho de 2024", exact=True).click()
            inline.get_by_label("As populações são partes sem sobreposição do conjunto agregado.").check()
            inline.get_by_label("Caso contrário, autorizo somar componentes, mesmo com possível dupla contagem.").check()
            calculate(4)
        step("7 agregação", aggregate)

        def restore():
            history.get_by_role("button", name="2. Comparação territorial", exact=False).click()
            board = page.locator("#resultados")
            details = board.locator("details", has=page.locator("summary", has_text="Consultar solicitação e parâmetros"))
            if not details.evaluate("element => element.open"):
                details.locator("summary").click()
            board.get_by_role("button", name="Retomar parâmetros deste resultado", exact=True).click()
            button = inline.get_by_role("button", name="Calcular e mostrar resultado", exact=True)
            expect(button).to_be_enabled(timeout=120000)
            button.click()
            expect(page.get_by_text("Resultado existente recuperado, sem recalcular.", exact=True)).to_be_visible(timeout=120000)
        step("8 retomada (reaproveitada)", restore)
        page.wait_for_timeout(1500)
        board = page.locator("#resultados")
        history.get_by_role("button", name="1. Densidade de profissionais", exact=False).click()
        members = board.locator("details", has=page.locator("summary", has_text="Selecionar territórios deste resultado"))
        if not members.evaluate("element => element.open"):
            members.locator("summary").click()
        toggles = []
        for code in ("130420", "130420"):
            toggles.append(page.evaluate(TOGGLE, code))
            page.wait_for_timeout(4000)
        heap = page.evaluate("() => performance.memory ? performance.memory.usedJSHeapSize / 1048576 : null")
        browser.close()
    calls = [c for s in steps for c in s["requests"]]
    checks = [c for c in calls if c["endpoint"] == "preflight"]
    summary = {"requests": len(calls), "aborted": sum(c["aborted"] for c in calls),
               "long_tasks_ms": sum(sum(s["long_tasks_ms"]) for s in steps), "wall_s": sum(s["s"] for s in steps),
               "repeated_preflights": sum(c["repeated"] for c in checks),
               "same_as_current_preflights": sum(c["same_as_current"] for c in checks),
               "kib": sum(c["kib"] for c in calls), "by_endpoint": {}}
    for c in calls:
        entry = summary["by_endpoint"].setdefault(c["endpoint"], {"n": 0, "kib": 0, "s": 0, "aborted": 0})
        entry["n"] += 1
        entry["kib"] += c["kib"]
        entry["s"] += c["s"]
        entry["aborted"] += c["aborted"]
    print("total:", json.dumps(summary, ensure_ascii=False))
    print(f"marcar/desmarcar membro do resultado: {', '.join(f'{t:.0f} ms' for t in toggles)} | heap JS {heap:.0f} MiB")
    if args.json:
        args.json.write_text(json.dumps({"steps": steps, "summary": summary, "toggle_ms": toggles, "heap_mib": heap},
                                        ensure_ascii=False, indent=2), encoding="utf-8")


if __name__ == "__main__":
    main()
