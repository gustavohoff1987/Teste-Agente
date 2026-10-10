"""Regressão de sessão e fluxos principais; requer Vite e API locais.

Executar: py backend/tests/ui_session_smoke.py
Usa dados sintéticos e respostas de IA simuladas; não chama o provedor.
"""
import csv
import io
import json
import os
from pathlib import Path

from playwright.sync_api import sync_playwright, expect

ROOT = Path(__file__).resolve().parents[2]
OUTPUT = ROOT / ".local" / "ui-validation"
URL = "http://localhost:5173/"
DECLARATION = (
    "Declaro que não compartilharei dados pessoais ou sensíveis, seja por meio "
    "dos arquivos enviados ou das mensagens inseridas no chat."
)
DATA = {
    "name": "base-sintetica.csv",
    "mimeType": "text/csv",
    "buffer": b"Territorio;Ano;Categoria;Quantidade;Populacao\nA;2024;Medicos;100;50000\nB;2024;Medicos;200;100000\n",
}
REPLY = {
    "reply": "Proposta simulada: confira os requisitos de quantitativos.",
    "proposal": {"operation": "counts", "indicator": "quantity", "territory": "", "period": "", "category": ""},
    "executed": False,
    "origin": "INTERPRETACAO_LLM",
    "requires_confirmation": True,
}


def check_layout(page):
    assert page.evaluate("document.documentElement.scrollWidth <= window.innerWidth + 2")


def main():
    OUTPUT.mkdir(parents=True, exist_ok=True)
    errors = []
    with sync_playwright() as p:
        expect.set_options(timeout=15000)
        browser = p.chromium.launch(headless=True, channel=os.getenv("ADT_BROWSER_CHANNEL", "chrome"))
        context = browser.new_context(viewport={"width": 1310, "height": 900}, accept_downloads=True)
        context.on("page", lambda page: page.on("pageerror", lambda error: errors.append(str(error))))
        status_state = {"configured": True}
        context.route("**/api/llm/status", lambda route: route.fulfill(json=status_state))
        llm_requests = []

        def reply(route):
            llm_requests.append(route.request)
            body = dict(REPLY)
            if route.request.url.endswith("interpret-context"):
                body["verification"] = {
                    "source": "BACKEND_PREFLIGHT", "capability_status": "needs_confirmation",
                    "slots": {"period": "not_requested", "category": "not_requested", "territory": "not_requested"},
                    "blockers": [], "ready_to_execute": False, "next_action": "confirm_in_interface",
                }
            route.fulfill(json=body)

        context.route("**/api/llm/interpret*", reply)
        page = context.new_page()
        writes = []
        page.on("request", lambda request: writes.append(request.url) if request.method == "POST" else None)
        page.goto(URL)
        modal = page.get_by_role("dialog", name="Antes de começar")
        accept = modal.get_by_role("button", name="Li e concordo")
        expect(modal).to_be_visible()
        expect(modal.get_by_text(DECLARATION, exact=True)).to_be_visible()
        expect(accept).to_be_focused()
        expect(page.locator('input[type="file"]')).to_be_disabled()
        expect(page.get_by_role("textbox", name="Descreva sua análise ou faça uma pergunta")).to_be_disabled()
        expect(page.get_by_role("button", name="Enviar mensagem")).to_be_disabled()
        page.keyboard.press("Escape")
        expect(modal).to_be_visible()
        # A navegação de teclado não pode alcançar os controles sob o modal.
        page.keyboard.press("Shift+Tab")
        page.keyboard.press("Tab")
        expect(accept).to_be_focused()
        assert not writes
        page.screenshot(path=str(OUTPUT / "session-dialog-desktop.png"))
        page.reload()
        expect(modal).to_be_visible()  # Recarregar não aceita a declaração.
        accept.click()
        expect(modal).to_have_count(0)
        expect(page.locator('input[type="file"]')).to_be_enabled()
        assert page.evaluate("document.body.style.overflow") == ""
        expect(page.get_by_text("Informações do serviço", exact=True)).to_have_count(0)
        expect(page.get_by_role("link", name="Documentação", exact=True)).to_have_count(0)
        expect(page.locator('#assistente input[type="checkbox"]')).to_have_count(0)
        page.reload()
        expect(page.get_by_role("heading", level=1)).to_be_visible()
        expect(modal).to_have_count(0)  # O aceite sobrevive à recarga na mesma aba.
        page.get_by_role("button", name="Resultados", exact=True).click()
        page.get_by_role("button", name="Início", exact=True).click()
        expect(modal).to_have_count(0)
        check_layout(page)
        page.screenshot(path=str(OUTPUT / "session-home-desktop.png"))
        page.get_by_role("img", name="Jovem negro de óculos e jaleco, em estilo de animação").first.screenshot(path=str(OUTPUT / "session-avatar.png"))
        # Conversa sem base: Enter envia após um único aceite, sem iniciar cálculo.
        prompt = page.get_by_role("textbox", name="Descreva sua análise ou faça uma pergunta")
        prompt.fill("Quero analisar quantitativos")
        prompt.press("Enter")
        expect(page.get_by_role("log")).to_contain_text(REPLY["reply"])
        assert len(llm_requests) == 1
        assert llm_requests[0].post_data_json["message"] == "Quero analisar quantitativos"
        page.get_by_role("button", name="Ver requisitos de Quantitativos", exact=True).click()
        expect(page.locator("#analises .analysis-card")).to_have_accessible_name("Selecionar análise: Quantitativos")
        expect(page.locator("#analises .analysis-card")).to_have_attribute("aria-pressed", "true")
        assert not any(url.endswith("/api/analyze") for url in writes)
        # Importação real, confirmações e cálculo real com resultado independente.
        page.locator('input[type="file"]').set_input_files(DATA)
        expect(page.get_by_role("heading", name="Configuração da análise", exact=True)).to_be_visible()
        expect(page.get_by_role("log")).not_to_contain_text(REPLY["reply"])
        expect(modal).to_have_count(0)
        page.get_by_role("button", name="Confirmar objeto de análise", exact=True).click()
        page.locator("#analises .analysis-card").press("Home")
        page.get_by_role("button", name="Selecionar análise: Densidade", exact=True).click()
        execute = page.get_by_role("button", name="Executar análise", exact=True)
        expect(execute).to_be_disabled()
        assert not any(url.endswith("/api/analyze") for url in writes)
        page.get_by_label("O que o quantitativo representa?", exact=True).select_option("pessoas")
        page.get_by_label("Confirmo que a população corresponde aos territórios e períodos analisados", exact=True).check()
        expect(execute).to_be_enabled()
        # Conversa com base mantém o contrato contextual e o aceite da sessão.
        prompt.fill("Quero analisar quantitativos com esta base")
        expect(page.get_by_role("button", name="Enviar mensagem")).to_be_enabled()
        page.get_by_role("button", name="Enviar mensagem").click()
        expect(page.get_by_role("log")).to_contain_text(REPLY["reply"])
        assert len(llm_requests) == 2 and llm_requests[-1].url.endswith("/api/llm/interpret-context")
        assert 'name="file"' in llm_requests[-1].post_data
        assert not any(url.endswith("/api/analyze") for url in writes)
        with page.expect_response(lambda response: response.url.endswith("/api/analyze")) as result_event:
            execute.click()
        result = result_event.value
        assert result.status == 200
        assert result.json()["total_rows"] == 2
        assert all(row["Densidade por 1.000"] == 2 for row in result.json()["rows"])
        expect(page.locator(".data-table tbody tr")).to_have_count(2)
        with page.expect_download() as download:
            page.get_by_role("button", name="CSV", exact=True).click()
        rows = list(csv.DictReader(io.StringIO(Path(download.value.path()).read_text(encoding="utf-8-sig")), delimiter=";"))
        assert len(rows) == 2
        page.get_by_role("button", name="Início", exact=True).click()
        expect(modal).to_have_count(0)
        # Explorar outro card não invalida a análise que o usuário já executou.
        page.get_by_role("button", name="Próxima análise", exact=True).click()
        expect(page.locator("#analises .analysis-card")).to_have_attribute("aria-pressed", "false")
        page.get_by_role("button", name="Resultados", exact=True).click()
        expect(page.locator(".data-table tbody tr")).to_have_count(2)
        expect(page.get_by_role("button", name="CSV", exact=True)).to_be_enabled()
        page.get_by_role("button", name="Início", exact=True).click()
        # Nova aba = nova sessão; layout, aceite e navegação em tela estreita.
        mobile = context.new_page()
        mobile.set_viewport_size({"width": 390, "height": 844})
        mobile.goto(URL)
        expect(mobile.get_by_role("dialog")).to_be_visible()
        check_layout(mobile)
        mobile.screenshot(path=str(OUTPUT / "session-dialog-mobile.png"))
        mobile.get_by_role("button", name="Li e concordo").click()
        mobile.get_by_role("button", name="Abrir menu").click()
        mobile.get_by_role("button", name="Resultados", exact=True).click()
        mobile.get_by_role("button", name="Abrir menu").click()
        mobile.get_by_role("button", name="Início", exact=True).click()
        mobile.reload()
        expect(mobile.get_by_role("heading", level=1)).to_be_visible()
        expect(mobile.get_by_role("dialog")).to_have_count(0)
        check_layout(mobile)
        mobile.screenshot(path=str(OUTPUT / "session-home-mobile.png"))
        mobile.close()
        # Falha/recuperação da conversa não bloqueia as análises.
        status_state["configured"] = False
        page.reload()
        expect(page.get_by_role("button", name="Tentar novamente", exact=True)).to_be_visible()
        expect(page.locator('input[type="file"]')).to_be_enabled()
        expect(page.get_by_role("button", name="Enviar mensagem")).to_be_disabled()
        status_state["configured"] = True
        page.get_by_role("button", name="Tentar novamente", exact=True).click()
        expect(page.get_by_role("button", name="Tentar novamente", exact=True)).to_have_count(0)
        page.get_by_role("textbox", name="Descreva sua análise ou faça uma pergunta").fill("Quero analisar quantitativos")
        expect(page.get_by_role("button", name="Enviar mensagem")).to_be_enabled()
        # Navegadores com sessionStorage bloqueado ainda permitem aceite em memória.
        blocked = context.new_page()
        blocked.add_init_script("Object.defineProperty(window, 'sessionStorage', { get() { throw new DOMException('Storage blocked', 'SecurityError'); } });")
        blocked.goto(URL)
        expect(blocked.get_by_role("dialog")).to_be_visible()
        blocked.get_by_role("button", name="Li e concordo").click()
        expect(blocked.get_by_role("dialog")).to_have_count(0)
        expect(blocked.locator('input[type="file"]')).to_be_enabled()
        blocked.get_by_role("button", name="Resultados", exact=True).click()
        blocked.get_by_role("button", name="Início", exact=True).click()
        expect(blocked.get_by_role("dialog")).to_have_count(0)
        assert not errors, errors
        browser.close()
    (OUTPUT / "session-evidence.json").write_text(json.dumps({
        "status": "PASS", "page_errors": errors, "real_analysis_rows": 2,
        "density_per_thousand": 2, "mocked_llm_requests": len(llm_requests),
        "checks": ["consent required", "keyboard focus", "Escape", "reload before/after consent", "new tab", "navigation",
                   "CSV upload", "analysis confirmation", "density", "CSV download", "chat with/without dataset",
                   "service recovery", "blocked storage", "desktop/mobile"],
    }, ensure_ascii=False, indent=2), encoding="utf-8")
    print("PASS: session, keyboard, upload, real density, CSV, mocked chat, service recovery, blocked storage, desktop/mobile; no page errors.")


if __name__ == "__main__":
    main()
