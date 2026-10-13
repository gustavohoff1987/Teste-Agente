"""Responsividade da referência mais próxima no navegador; servidor serve_ui_offline.py ativo.

Uso (raiz do repositório), com o catálogo instalado em ADT_BRASIL_DATA_DIR no servidor:
    ADT_UI_URL=http://127.0.0.1:18000/ python backend/tests/bench_ui_nearest.py [--json saida.json]
Critério de densidade ≥ 2,36 em junho de 2024 para 3 alvos (Manaus, Tefé e Parintins), os
municípios do Amazonas e todos os municípios. Mede, no navegador, a requisição de cálculo, o
intervalo entre a resposta e a primeira linha da tabela, as tarefas longas e a resposta da caixa de
mensagem logo após a renderização; confirma o indicador de processamento e uma única execução.
Registra só contagens e tempos, nunca linhas.
"""
import argparse
import json
import os

from playwright.sync_api import sync_playwright, expect
from ui_support import URL, offline

CASES = [("3 alvos", "Calcule a referência mais próxima de Manaus, Tefé e Parintins."),
         ("municípios do Amazonas", "Calcule a referência mais próxima dos municípios do Amazonas."),
         ("todos os municípios", "Calcule a referência mais próxima.")]
# Tarefas longas e o instante em que a primeira linha da tabela aparece, medidos no próprio navegador.
OBSERVER = """() => { window.__long = []; window.__tableAt = null;
  new PerformanceObserver(list => { for (const entry of list.getEntries()) window.__long.push(entry.duration); })
    .observe({type: "longtask"});
  const watch = new MutationObserver(() => { if (document.querySelector('#resultados .data-table tbody tr')) {
    window.__tableAt = performance.now(); watch.disconnect(); } });
  watch.observe(document.body, {childList: true, subtree: true}); }"""
TIMING = """() => { const entry = performance.getEntriesByType('resource').filter(e => e.name.endsWith('/api/analyze')).pop();
  return {request_ms: entry.responseEnd - entry.startTime, render_ms: window.__tableAt - entry.responseEnd}; }"""


def measure(browser, label, command):
    context = browser.new_context(viewport={"width": 1280, "height": 900})
    offline(context)
    page = context.new_page()
    analyses, failures = [], []
    page.on("request", lambda request: analyses.append(1) if request.url.endswith("/api/analyze") else None)
    page.on("pageerror", lambda error: failures.append(str(error)))
    page.goto(URL)
    page.get_by_role("button", name="Li e concordo", exact=True).click()
    chat, inline = page.locator("#assistente"), page.locator("#preparacao-conversacional")

    def send(message):
        chat.locator("#assistant-input").fill(message)
        chat.get_by_role("button", name="Enviar mensagem", exact=True).click()
        expect(chat.locator("#assistant-input")).to_be_enabled(timeout=120000)

    send("Olá")
    chat.get_by_role("button", name="Usar dados do Brasil").click()
    expect(chat.get_by_text("Os dados do Brasil já estão disponíveis.", exact=False)).to_be_visible(timeout=120000)
    send(command)
    setup = inline.get_by_role("group", name="Definição das referências")
    inline.get_by_label("Escolher períodos da análise").click()
    inline.get_by_role("button", name="junho de 2024", exact=True).click()
    inline.get_by_label("Referencial geodésico").select_option("SIRGAS2000")
    setup.get_by_label("Critério simples de densidade").check()
    setup.get_by_label("Operador do critério").select_option(">=")
    setup.get_by_label("Valor do critério").fill("2,36")
    decimal = setup.get_by_label("Separador decimal das coordenadas")
    expect(decimal).to_be_visible(timeout=120000)  # coordenadas com vírgula: declaração explícita
    decimal.select_option("decimal_comma")
    button = inline.get_by_role("button", name="Calcular e mostrar resultado", exact=True)
    expect(button).to_be_enabled(timeout=120000)
    page.evaluate(OBSERVER)
    with page.expect_response(lambda response: response.url.endswith("/api/analyze"), timeout=300000) as event:
        button.dblclick()
        indicator = page.get_by_role("status").filter(has_text="Preparando seu diagnóstico")
        expect(indicator).to_be_visible(timeout=10000)
    assert event.value.status == 200
    body = event.value.json()
    expect(page.locator("#resultados .data-table tbody tr").first).to_be_visible(timeout=120000)
    timing = page.evaluate(TIMING)
    # Resposta da interface após a renderização: digitação refletida no próximo quadro.
    typing = page.evaluate("""() => new Promise(resolve => { const box = document.querySelector('#assistant-input');
      const t0 = performance.now(); box.focus(); box.value = 'teste'; box.dispatchEvent(new Event('input', {bubbles: true}));
      requestAnimationFrame(() => resolve(performance.now() - t0)); })""")
    page.wait_for_timeout(500)
    long_tasks = page.evaluate("window.__long")
    structured = body["metadata"]["nearest_reference"]
    line = {"caso": label, "alvos": structured["cobertura"]["n_universo"], "referencias": structured["conjunto_referencias"]["n"],
            "minimo_completo": structured["cobertura"]["n_minimo_completo"],
            "somente_avaliaveis": structured["cobertura"]["n_somente_entre_avaliaveis"],
            "nao_avaliaveis": structured["cobertura"]["n_nao_avaliaveis_por_motivo"],
            "requisicao_s": round(timing["request_ms"] / 1000, 3), "resposta_tabela_ms": round(timing["render_ms"]),
            "resposta_kib": len(event.value.body()) // 1024, "tarefas_longas": len(long_tasks),
            "maior_tarefa_ms": round(max(long_tasks, default=0)), "bloqueio_total_ms": round(sum(max(0, t - 50) for t in long_tasks)),
            "digitacao_ms": round(typing, 1), "execucoes": len(analyses), "indicador": True}
    assert len(analyses) == 1 and not failures, (analyses, failures)
    context.close()
    return line


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--json")
    args = parser.parse_args()
    lines = []
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True, channel=os.getenv("ADT_BROWSER_CHANNEL", "chrome"))
        for label, command in CASES:
            lines.append(measure(browser, label, command))
            print(json.dumps(lines[-1], ensure_ascii=False), flush=True)
        browser.close()
    if args.json:
        with open(args.json, "w", encoding="utf-8") as handle:
            json.dump(lines, handle, ensure_ascii=False, indent=2)


if __name__ == "__main__":
    main()
