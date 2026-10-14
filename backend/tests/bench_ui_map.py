"""Bloco 3: tempos do mapa e das visualizações no navegador; servidor serve_ui_offline.py ativo.

Uso (raiz do repositório), com o catálogo instalado em ADT_BRASIL_DATA_DIR no servidor:
    ADT_UI_URL=http://127.0.0.1:18000/ python backend/tests/bench_ui_map.py [--json saida.json]
Cenário de bench_ui_criteria.py em junho de 2024 com todos os municípios: densidade < 2,36 E distância
> 155 km até a referência mais próxima (referências com densidade ≥ 2,36, cobertura parcial aceita
explicitamente). Mede no próprio navegador: mapa disponível após a resposta, primeiro desenho,
resposta à seleção (soltar o clique → anel desenhado e detalhes na tela), quadros de zoom e arrasto,
troca da forma de visualização, atualização das barras ao trocar o indicador e heap JS antes e depois.
Confere que o modelo desenhado é a geometria da resposta e que nenhuma interação visual gera nova
análise. Registra só tempos e contagens, nunca linhas.
"""
import argparse
import json
import statistics

from playwright.sync_api import sync_playwright, expect
from bench_ui_criteria import OBSERVER
from ui_support import URL, offline

# Instante de soltar o clique no canvas e do primeiro quadro em que a seleção aparece desenhada e
# descrita no painel de detalhes (medidos no relógio da página).
SELECTION = """label => { window.__selectionWait = new Promise(resolve => {
  const canvas = document.querySelector('[data-testid="territory-map"]');
  canvas.addEventListener('pointerup', event => {
    const t0 = event.timeStamp, drawn = window.__adtMapStats.length;
    const tick = () => {
      const stats = window.__adtMapStats.slice(drawn).find(item => item.at > t0);
      const region = document.querySelector('[aria-label="Territórios selecionados"]');
      if (stats && region && region.textContent.includes(label))
        resolve({desenho_ms: stats.at - t0, detalhes_ms: performance.now() - t0, quadro_ms: stats.drawMs});
      else requestAnimationFrame(tick);
    };
    requestAnimationFrame(tick);
  }, {once: true});
}); }"""
# Clique numa aba da forma de visualização até o conteúdo dela existir no quadro seguinte.
SWITCH = """([name, test]) => new Promise(resolve => {
  const tab = [...document.querySelectorAll('[role="tab"]')].find(item => item.textContent.trim().startsWith(name));
  const drawn = window.__adtMapStats.length;
  const ready = {graficos: () => document.querySelector('figure svg.recharts-surface'),
    tabela: () => [...document.querySelectorAll('p')].some(item => item.textContent.startsWith('Visualização em tabela')),
    mapa: () => window.__adtMapStats.length > drawn}[test];
  tab.addEventListener('click', event => {
    const t0 = event.timeStamp;
    const tick = () => ready() ? requestAnimationFrame(() => resolve(performance.now() - t0)) : requestAnimationFrame(tick);
    requestAnimationFrame(tick);
  }, {once: true});
  tab.click();
})"""
# Troca do indicador das barras até o título da figura refletir o novo indicador.
BARS = """([column, title]) => new Promise(resolve => {
  const select = document.querySelector('select[aria-label="Indicador das barras"]');
  const t0 = performance.now();
  select.value = column;
  select.dispatchEvent(new Event('change', {bubbles: true}));
  const tick = () => document.querySelector('figure[aria-label^="' + title + '"] svg.recharts-surface')
    ? requestAnimationFrame(() => resolve(performance.now() - t0)) : requestAnimationFrame(tick);
  requestAnimationFrame(tick);
})"""


def summary(values):
    ordered = sorted(values)
    return {"n": len(ordered), "mediana": round(statistics.median(ordered), 1),
            "p95": round(ordered[min(len(ordered) - 1, int(round(0.95 * (len(ordered) - 1))))], 1), "maximo": round(ordered[-1], 1)}


def main(output):
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True, channel="chromium")
        context = browser.new_context(viewport={"width": 1280, "height": 900})
        offline(context)
        context.add_init_script("window.__ADT_TEST__ = true")
        page = context.new_page()
        cdp = context.new_cdp_session(page)
        cdp.send("Performance.enable")
        analyses, failures = [], []
        page.on("request", lambda request: analyses.append(1) if request.url.endswith("/api/analyze") else None)
        page.on("pageerror", lambda error: failures.append(str(error)))

        def heap_mb():
            cdp.send("HeapProfiler.collectGarbage")
            metrics = {item["name"]: item["value"] for item in cdp.send("Performance.getMetrics")["metrics"]}
            return round(metrics["JSHeapUsedSize"] / 1e6, 1)

        page.goto(URL)
        page.get_by_role("button", name="Li e concordo", exact=True).click()
        chat, inline = page.locator("#assistente"), page.locator("#preparacao-conversacional")
        board = page.locator("#resultados")

        def send(message):
            chat.locator("#assistant-input").fill(message)
            chat.get_by_role("button", name="Enviar mensagem", exact=True).click()
            expect(chat.locator("#assistant-input")).to_be_enabled(timeout=120000)

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
        button = inline.get_by_role("button", name="Calcular e mostrar resultado", exact=True)
        expect(button).to_be_enabled(timeout=120000)
        heap_before = heap_mb()

        # 1. Execução: resposta, tabela e mapa (primeiro desenho) medidos a partir do fim da resposta.
        page.evaluate(OBSERVER)
        with page.expect_response(lambda r: r.url.endswith("/api/analyze"), timeout=300000) as event:
            button.click()
        assert event.value.status == 200, event.value.status
        body = event.value.json()
        size_mb = round(len(event.value.body()) / 1e6, 2)
        page.wait_for_function("window.__tableAt !== null", timeout=120000)
        page.wait_for_function("window.__adtMapModel && window.__adtMapModel.resultId === '" + body["result_id"] +
                               "' && window.__adtMapStats && window.__adtMapStats.length > 0", timeout=120000)
        timing = page.evaluate("""() => { const entry = performance.getEntriesByType('resource').filter(e => e.name.endsWith('/api/analyze')).pop();
          const first = window.__adtMapStats[0];
          return {request_ms: entry.responseEnd - entry.startTime, table_ms: window.__tableAt - entry.responseEnd,
                  map_ms: first.at - entry.responseEnd, first_draw_ms: first.drawMs, points: first.points}; }""")
        page.wait_for_timeout(500)
        long_tasks = page.evaluate("window.__long")
        geometry = body["metadata"]["representacao"]["geometria"]
        model = page.evaluate("window.__adtMapModel")
        assert model["ids"] == geometry["ids"] and model["lat"] == geometry["lat"] and model["lon"] == geometry["lon"]
        states = {item["elemento"]: item["estado"] for item in body["metadata"]["criterios"]["avaliacoes"]}
        drawn_meets = [key for key in model["ids"] if states.get(key) == "ATENDE"]
        assert sum(model["passes"]) == len(drawn_meets)  # filtro inicial: Atendem (estado do motor)
        references = {item["id"] for item in body["metadata"]["criterios"]["referencias"]["membros"]}
        assert set(model["references"]) == references
        heap_result = heap_mb()
        calls = len(analyses)

        # 2. Seleção: cinco pontos que atendem, o primeiro por clique simples e os demais com Shift.
        canvas = board.get_by_test_id("territory-map")
        labels = {item["id"]: item["label"] for item in body["metadata"]["universe"]["members"]}
        selection = []
        for index, key in enumerate(drawn_meets[:5]):
            canvas.scroll_into_view_if_needed()
            x, y = page.evaluate("id => window.__adtMapLocate(id)", key)
            box = canvas.bounding_box()
            page.evaluate(SELECTION, labels[key])
            page.mouse.move(box["x"] + x, box["y"] + y)
            if index:
                page.keyboard.down("Shift")
            page.mouse.click(box["x"] + x, box["y"] + y)
            if index:
                page.keyboard.up("Shift")
            selection.append(page.evaluate("window.__selectionWait"))
            page.wait_for_function(f"window.__adtMapModel.selected.length === {index + 1}")
        assert page.evaluate("window.__adtMapModel.selected") == drawn_meets[:5]

        # 3. Zoom e arrasto: duração de cada quadro desenhado durante a navegação.
        canvas.scroll_into_view_if_needed()
        box = canvas.bounding_box()
        start = page.evaluate("window.__adtMapStats.length")
        cx, cy = box["x"] + box["width"] / 2, box["y"] + box["height"] / 2
        page.mouse.move(cx, cy)
        page.keyboard.down("Control")
        for _ in range(8):
            page.mouse.wheel(0, -240)
            page.wait_for_timeout(30)
        page.keyboard.up("Control")
        page.mouse.down()
        for step in range(1, 25):
            page.mouse.move(cx + step * 8, cy + step * 4)
            page.wait_for_timeout(16)
        page.mouse.up()
        page.keyboard.down("Control")
        for _ in range(8):
            page.mouse.wheel(0, 240)
            page.wait_for_timeout(30)
        page.keyboard.up("Control")
        page.wait_for_timeout(200)
        frames = page.evaluate(f"window.__adtMapStats.slice({start}).map(item => item.drawMs)")

        # 4. Troca da forma de visualização e atualização das barras pelo indicador.
        switches = {"mapa_para_graficos_ms": page.evaluate(SWITCH, ["Gráficos", "graficos"])}
        numeric = [item for item in body["metadata"]["representacao"]["indicadores"] if item["tipo"] in ("CONTINUO", "CONTAGEM")]
        bars = None
        if len(numeric) > 1:
            target = numeric[1]
            title = target["rotulo"] + (" (" + target["unidade"] + ")" if target.get("unidade") else "")
            bars = page.evaluate(BARS, [target["coluna"], title])
        switches["graficos_para_tabela_ms"] = page.evaluate(SWITCH, ["Tabela", "tabela"])
        switches["tabela_para_mapa_ms"] = page.evaluate(SWITCH, ["Mapa", "mapa"])
        heap_after = heap_mb()
        assert len(analyses) == calls, "zoom, seleção e troca de visualização não geram análise"
        assert not failures, failures
        browser.close()

    representation_kib = len(json.dumps(body["metadata"]["representacao"], ensure_ascii=False).encode()) // 1024
    result = {"cenario": "densidade < 2,36 E distância > 155 km, junho de 2024, todos os municípios",
              "territorios": body["metadata"]["criterios"]["universo"]["n"], "pontos_no_mapa": timing["points"],
              "sem_geometria": len(geometry["sem_geometria"]), "complementados": len(geometry["complementados"]),
              "referencias": len(references), "atendem": body["metadata"]["criterios"]["contagens"]["ATENDE"],
              "atendem_no_mapa": len(drawn_meets),
              "requisicao_ms": round(timing["request_ms"]), "resposta_ate_tabela_ms": round(timing["table_ms"]),
              "resposta_ate_mapa_ms": round(timing["map_ms"]), "primeiro_desenho_ms": round(timing["first_draw_ms"], 1),
              "tarefas_longas": len(long_tasks), "maior_tarefa_longa_ms": round(max(long_tasks, default=0)),
              "selecao_ate_desenho_ms": summary([item["desenho_ms"] for item in selection]),
              "selecao_ate_detalhes_ms": summary([item["detalhes_ms"] for item in selection]),
              "quadros_zoom_arrasto_ms": summary(frames), "troca_visualizacao_ms": {k: round(v, 1) for k, v in switches.items()},
              "barras_troca_indicador_ms": round(bars, 1) if bars is not None else None,
              "heap_js_mb": {"antes": heap_before, "com_resultado_e_mapa": heap_result, "apos_interacoes": heap_after},
              "resposta_mb": size_mb, "representacao_kib": representation_kib}
    print(json.dumps(result, ensure_ascii=False, indent=2))
    if output:
        with open(output, "w", encoding="utf-8") as handle:
            json.dump(result, handle, ensure_ascii=False, indent=2)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--json")
    main(parser.parse_args().json)
