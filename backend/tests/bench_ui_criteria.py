"""Responsividade dos critérios combinados no navegador; servidor serve_ui_offline.py ativo.

Uso (raiz do repositório), com o catálogo instalado em ADT_BRASIL_DATA_DIR no servidor:
    ADT_UI_URL=http://127.0.0.1:18000/ python backend/tests/bench_ui_criteria.py [--json saida.json]
Cenário do pedido do usuário em junho de 2024 com todos os municípios: densidade < 2,36 E distância
> 155 km até a referência mais próxima (referências com densidade ≥ 2,36, cobertura parcial aceita
explicitamente), depois ordenação decrescente pela distância e 20 primeiros. Mede a requisição, o
intervalo entre a resposta e a primeira linha da tabela, as tarefas longas e a resposta da caixa de
mensagem; confirma uma única execução por pedido. Registra só tempos e contagens, nunca linhas.
"""
import argparse
import json

from playwright.sync_api import sync_playwright, expect
from bench_ui_nearest import TIMING
from ui_support import URL, offline

# Instante em que a tabela do NOVO resultado aparece: o painel de resultados é remontado a cada resultado,
# então o nó anterior (se houver) é ignorado; tarefas longas medidas no próprio navegador.
OBSERVER = """() => { window.__long = []; window.__tableAt = null;
  const selector = '#resultados section[aria-label="Territórios classificados"]';
  const previous = document.querySelector(selector);
  new PerformanceObserver(list => { for (const entry of list.getEntries()) window.__long.push(entry.duration); })
    .observe({type: "longtask"});
  const watch = new MutationObserver(() => { const current = document.querySelector(selector);
    if (current && current !== previous && current.querySelector('.data-table tbody tr')) {
      window.__tableAt = performance.now(); watch.disconnect(); } });
  watch.observe(document.body, {childList: true, subtree: true}); }"""


def main(output):
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True, channel="chromium")
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

        def run(label):
            page.evaluate(OBSERVER)
            before = len(analyses)
            button = inline.get_by_role("button", name="Calcular e mostrar resultado", exact=True)
            expect(button).to_be_enabled(timeout=120000)
            with page.expect_response(lambda r: r.url.endswith("/api/analyze"), timeout=300000) as event:
                button.dblclick()
                expect(page.get_by_role("status").filter(has_text="Preparando seu diagnóstico")).to_be_visible(timeout=10000)
            assert event.value.status == 200, event.value.status
            page.wait_for_function("window.__tableAt !== null", timeout=120000)
            timing = page.evaluate(TIMING)
            # Mesmo método da Etapa 1: digitação refletida no próximo quadro, medida dentro da página.
            typing = page.evaluate("""() => new Promise(resolve => { const box = document.querySelector('#assistant-input');
              const t0 = performance.now(); box.focus(); box.value = 'teste'; box.dispatchEvent(new Event('input', {bubbles: true}));
              requestAnimationFrame(() => resolve(performance.now() - t0)); })""")
            page.wait_for_timeout(500)
            long_tasks = page.evaluate("window.__long")
            body = event.value.json()
            assert len(analyses) == before + 1, "uma execução por pedido, mesmo com clique duplo"
            return {"caso": label, "requisicao_ms": round(timing["request_ms"]), "resposta_ate_tabela_ms": round(timing["render_ms"]),
                    "tarefas_longas": len(long_tasks), "maior_tarefa_longa_ms": round(max(long_tasks, default=0)),
                    "bloqueio_total_ms": round(sum(max(0, t - 50) for t in long_tasks)), "digitacao_ms": round(typing, 1),
                    "territorios": body["metadata"]["criterios"]["universo"]["n"],
                    "atendem": body["metadata"]["criterios"]["contagens"]["ATENDE"], "resposta_mb": round(len(event.value.body()) / 1e6, 2)}

        send("Olá")
        chat.get_by_role("button", name="Usar dados do Brasil").click()
        expect(chat.get_by_text("Os dados do Brasil já estão disponíveis.", exact=False)).to_be_visible(timeout=120000)
        send("Mostre os municípios com menos de 2,36 médicos por mil habitantes.")
        send("Agora considere também distância superior a 155 km.")
        builder = inline.get_by_role("group", name="Critérios combinados")
        setup = builder.get_by_role("group", name="Definição das referências")
        setup.get_by_label("Critério simples de densidade").check()
        setup.get_by_label("Operador do critério").select_option(">=")
        setup.get_by_label("Valor do critério").fill("2,36")
        builder.get_by_text("Aceito, quando alguma referência não tiver coordenada válida", exact=False).click()
        inline.get_by_label("Referencial geodésico").select_option("SIRGAS2000")
        inline.get_by_label("Escolher períodos da análise").click()
        inline.get_by_role("button", name="junho de 2024", exact=True).click()
        decimal = setup.get_by_label("Separador decimal das coordenadas")  # vírgula declarada, nunca presumida
        expect(decimal).to_be_visible(timeout=120000)
        decimal.select_option("decimal_comma")
        results = [run("densidade e distância, todos os municípios")]
        send("Ordene esses municípios pela distância, decrescente.")
        send("Mostre os 20 primeiros.")
        results.append(run("com ordenação e 20 primeiros"))
        assert not failures, failures
        browser.close()
    print(json.dumps(results, ensure_ascii=False, indent=2))
    if output:
        with open(output, "w", encoding="utf-8") as handle:
            json.dump(results, handle, ensure_ascii=False, indent=2)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--json")
    main(parser.parse_args().json)
