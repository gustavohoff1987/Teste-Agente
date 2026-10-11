"""Carrossel, navegação e layout; servidores locais precisam estar ativos.

Executar: py backend/tests/ui_carousel_smoke.py
Não envia dados ao provedor de IA nem utiliza bases pessoais.
"""
import json
import os
from pathlib import Path
from playwright.sync_api import sync_playwright, expect
from ui_support import URL, offline, stage, select

ROOT = Path(__file__).resolve().parents[2]
OUTPUT = ROOT / ".local" / "ui-validation"
TITLES = ["Densidade", "Quantitativos", "Distribuição", "Comparações", "Evolução temporal",
          "Agregações", "Análise espacial", "Recortes e rankings", "Rotatividade", "Relatórios"]


def main():
    OUTPUT.mkdir(parents=True, exist_ok=True)
    with sync_playwright() as p:
        expect.set_options(timeout=15000)
        browser = p.chromium.launch(headless=True, channel=os.getenv("ADT_BROWSER_CHANNEL", "chrome"))
        context = browser.new_context(viewport={"width": 1310, "height": 900})
        offline(context)
        context.route("**/api/llm/status", lambda route: route.fulfill(json={"configured": True}))
        context.route("**/api/llm/interpret*", lambda route: route.abort())
        page = context.new_page()
        errors, posts = [], []
        page.on("pageerror", lambda error: errors.append(str(error)))
        page.on("request", lambda req: posts.append(req.url) if req.method == "POST" else None)
        page.goto(URL)
        page.get_by_role("button", name="Li e concordo", exact=True).click()
        card = page.locator("#analises button[aria-pressed]")
        carousel = page.locator("#analises")
        next_button = carousel.get_by_role("button", name="Próxima análise", exact=True)
        previous = carousel.get_by_role("button", name="Análise anterior", exact=True)
        expect(card).to_have_count(1)
        expect(previous).to_be_disabled()
        expect(card).to_have_attribute("aria-pressed", "false")
        expect(page.get_by_text("Processamento determinístico · Diagnósticos territoriais", exact=True)).to_have_count(0)
        chat_box = page.locator("#assistente").bounding_box()
        carousel_box = carousel.bounding_box()
        assert carousel_box["y"] > chat_box["y"]
        assert chat_box["x"] <= carousel_box["x"]
        assert chat_box["y"] < 650, chat_box
        page.screenshot(path=str(OUTPUT / "carousel-home-desktop.png"))
        # Todos os cards são acessíveis; girar o seletor não escolhe uma análise.
        for i, title in enumerate(TITLES):
            expect(card).to_have_accessible_name("Selecionar análise: " + title)
            expect(card).to_have_attribute("aria-pressed", "false")
            expect(carousel).to_contain_text(f"{i + 1} de 10")
            if i < len(TITLES) - 1:
                next_button.click()
        expect(next_button).to_be_disabled()
        assert not posts
        # Teclado mantém o foco; a seleção por Enter apenas abre os requisitos.
        card.focus()
        card.press("Home")
        expect(card).to_have_accessible_name("Selecionar análise: Densidade")
        card.press("ArrowRight")
        expect(card).to_have_accessible_name("Selecionar análise: Quantitativos")
        expect(card).to_be_focused()
        card.press("ArrowLeft")
        card.press("Enter")
        expect(card).to_have_attribute("aria-pressed", "true")
        expect(card).to_contain_text("Análise selecionada")
        assert not posts
        next_button.click()
        expect(card).to_have_attribute("aria-pressed", "false")
        previous.click()
        expect(card).to_have_attribute("aria-pressed", "true")
        page.locator("#assistente").screenshot(path=str(OUTPUT / "carousel-selected-desktop.png"))
        # Um gesto da roda muda uma opção; as extremidades liberam a página.
        card.hover()
        page.mouse.wheel(0, 95)
        expect(card).to_have_accessible_name("Selecionar análise: Quantitativos")
        page.mouse.wheel(0, 95)
        expect(card).to_have_accessible_name("Selecionar análise: Quantitativos")
        page.wait_for_timeout(220)
        page.mouse.wheel(0, -95)
        expect(card).to_have_accessible_name("Selecionar análise: Densidade")
        card.focus()
        card.press("End")
        expect(card).to_have_accessible_name("Selecionar análise: Relatórios")
        before_scroll = page.evaluate("window.scrollY")
        card.hover()
        page.mouse.wheel(0, 180)
        page.wait_for_function("window.scrollY > " + str(before_scroll))
        expect(card).to_have_accessible_name("Selecionar análise: Relatórios")
        # A roda com Ctrl é reservada ao zoom do navegador.
        assert card.evaluate("el => { const event = new WheelEvent('wheel', {bubbles: true, cancelable: true, deltaY: -80, ctrlKey: true}); return el.dispatchEvent(event); }")
        expect(card).to_have_accessible_name("Selecionar análise: Relatórios")
        card.press("Home")
        card.click()
        expect(page.get_by_role("region", name="Preparação da análise")).to_be_visible()
        expect(page.get_by_text("Carregue os dados do Brasil ou importe um arquivo", exact=False)).to_be_visible()
        assert not posts
        page.get_by_role("button", name="Começar pelo chat", exact=True).click()
        expect(page.locator("#assistente")).to_be_in_viewport()
        # A ação de importação do banner usa o mesmo input e não envia automaticamente.
        with page.expect_file_chooser() as chooser:
            page.get_by_role("button", name="Importar uma base", exact=True).click()
        assert chooser.value.is_multiple() is False
        assert not posts
        # Tela estreita: deslizar muda o card sem selecionar ou bloquear scroll vertical.
        mobile = browser.new_context(viewport={"width": 390, "height": 844}, is_mobile=True, has_touch=True)
        offline(mobile)
        mobile.route("**/api/llm/status", lambda route: route.fulfill(json={"configured": True}))
        mobile.route("**/api/llm/interpret*", lambda route: route.abort())
        narrow = mobile.new_page()
        narrow.on("pageerror", lambda error: errors.append(str(error)))
        narrow.on("request", lambda req: posts.append(req.url) if req.method == "POST" else None)
        narrow.goto(URL)
        narrow.get_by_role("button", name="Li e concordo", exact=True).click()
        narrow.screenshot(path=str(OUTPUT / "carousel-home-mobile.png"))
        mobile_card = narrow.locator("#analises button[aria-pressed]")
        mobile_card.scroll_into_view_if_needed()
        box = mobile_card.bounding_box()
        cdp = mobile.new_cdp_session(narrow)
        x, y = box["x"] + box["width"] * .8, box["y"] + box["height"] * .5
        cdp.send("Input.dispatchTouchEvent", {"type": "touchStart", "touchPoints": [{"x": x, "y": y}]})
        for distance in [20, 45, 80, 120]:
            cdp.send("Input.dispatchTouchEvent", {"type": "touchMove", "touchPoints": [{"x": x-distance, "y": y}]})
        cdp.send("Input.dispatchTouchEvent", {"type": "touchEnd", "touchPoints": []})
        expect(mobile_card).to_have_accessible_name("Selecionar análise: Quantitativos")
        expect(mobile_card).to_have_attribute("aria-pressed", "false")
        mobile_card.tap()
        expect(mobile_card).to_have_attribute("aria-pressed", "true")
        mobile_card.press("ArrowRight")
        expect(mobile_card).to_have_accessible_name("Selecionar análise: Distribuição")
        mobile_card.press("Enter")
        expect(mobile_card).to_have_attribute("aria-pressed", "true")
        mobile_card.press("ArrowLeft")
        mobile_card.tap()
        expect(mobile_card).to_have_attribute("aria-pressed", "true")
        narrow.locator("#analises").screenshot(path=str(OUTPUT / "carousel-selected-mobile.png"))
        assert not posts
        assert narrow.evaluate("document.documentElement.scrollWidth <= window.innerWidth + 2")
        for width in [320, 768, 1024, 1199, 1440]:
            page.set_viewport_size({"width": width, "height": 900})
            assert page.evaluate("document.documentElement.scrollWidth <= window.innerWidth + 2"), width
        page.emulate_media(reduced_motion="reduce")
        assert card.evaluate("el => getComputedStyle(el).transitionDuration") == "0s"
        assert not errors, errors
        (OUTPUT / "carousel-evidence.json").write_text(json.dumps({
            "status": "PASS", "cards": TITLES, "page_errors": errors, "unexpected_posts": posts,
            "chat_top_desktop": chat_box["y"],
            "checks": ["arrows", "keyboard", "wheel", "wheel boundaries", "zoom", "touch swipe",
                       "selection without execution", "visible selected state", "hero actions", "responsive", "reduced motion"],
        }, ensure_ascii=False, indent=2), encoding="utf-8")
        browser.close()
    print("PASS: all ten cards, selection, keyboard, wheel, swipe, hero, responsive layout, reduced motion; no unintended requests or page errors.")


if __name__ == "__main__":
    main()
