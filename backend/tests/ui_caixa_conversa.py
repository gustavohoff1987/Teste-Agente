"""A caixa da conversa inteira na janela, com zoom de 100%, em várias resoluções (04/11/2026; suíte "bloco1").

Com zoom de 100% numa janela baixa (como 1366 × 768), parte da caixa ficava cortada, inclusive o campo de envio. Em cada
resolução, com a página a 100% (device_scale_factor 1, sem zoom do navegador), este roteiro confere:
- na abertura (a caixa ampla, antes dos dados) e depois de várias mensagens: a caixa inteira dentro da janela; o campo de
  envio e o botão de enviar inteiros dentro da caixa e da janela, utilizáveis;
- o histórico com rolagem interna quando as mensagens não cabem (a caixa não cresce para fora da janela);
- no computador: arrastar o cabeçalho até além dos quatro cantos mantém a caixa inteira na janela; minimizar e abrir de novo
  mantém a caixa na janela e o campo de envio de volta; a janela encolhendo traz a caixa para dentro; Home volta ao canto;
- no celular: a caixa ancorada embaixo, inteira na janela, com o campo de envio à vista.
Catálogo sintético do Bloco 1; servidor serve_ui_offline.py, sem provedor de IA (as mensagens têm resposta local).
"""
import os

from playwright.sync_api import expect, sync_playwright
from ui_support import URL, accept_privacy, offline, send

RESOLUCOES = [(1366, 768), (1280, 720), (1280, 600), (1024, 768), (1440, 900), (1920, 1080), (390, 844)]
MENSAGENS = ["Obrigado", "O que é densidade?", "O que posso fazer nesta página?", "Obrigado pela explicação",
             "Como escolho os territórios?", "Obrigado"]


def dentro(caixa, largura, altura, margem=0.5):
    return (caixa["x"] >= -margem and caixa["y"] >= -margem and caixa["x"] + caixa["width"] <= largura + margem
            and caixa["y"] + caixa["height"] <= altura + margem)


def contido(interno, externo, margem=0.5):
    return (interno["x"] >= externo["x"] - margem and interno["y"] >= externo["y"] - margem
            and interno["x"] + interno["width"] <= externo["x"] + externo["width"] + margem
            and interno["y"] + interno["height"] <= externo["y"] + externo["height"] + margem)


def conferir(page, chat, rotulo):
    largura, altura = page.viewport_size["width"], page.viewport_size["height"]
    caixa = chat.bounding_box()
    assert caixa and dentro(caixa, largura, altura), (rotulo, "a caixa sai da janela", caixa, largura, altura)
    campo = chat.locator("#assistant-input")
    enviar = chat.get_by_role("button", name="Enviar mensagem", exact=True)
    expect(campo).to_be_visible()
    for nome, alvo in (("o campo de envio", campo.bounding_box()), ("o botão de enviar", enviar.bounding_box())):
        assert alvo and contido(alvo, caixa) and dentro(alvo, largura, altura), (rotulo, nome + " cortado", alvo, caixa)
    # O ponto central do campo é o próprio campo (nada por cima dele): dá para clicar e digitar.
    meio = campo.bounding_box()
    acima = page.evaluate("([x, y]) => document.elementFromPoint(x, y)?.id || ''",
                          [meio["x"] + meio["width"] / 2, meio["y"] + meio["height"] / 2])
    assert acima == "assistant-input", (rotulo, "o campo de envio está coberto", acima)
    return caixa


def main():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True, channel=os.getenv("ADT_BROWSER_CHANNEL", "chrome"))
        for largura, altura in RESOLUCOES:
            rotulo = f"{largura}×{altura}"
            context = browser.new_context(viewport={"width": largura, "height": altura}, device_scale_factor=1)
            offline(context)
            page = context.new_page()
            page.goto(URL)
            page.evaluate("() => { try { localStorage.removeItem('adt:painel-chat:v1'); } catch (e) {} }")
            page.reload()
            accept_privacy(page)
            chat = page.get_by_test_id("painel-chat")
            expect(chat).to_be_visible()
            conferir(page, chat, rotulo + ", abertura")

            for mensagem in MENSAGENS:
                send(page, mensagem)
            expect(chat.get_by_test_id("chat-processando")).to_have_count(0, timeout=60000)
            conferir(page, chat, rotulo + ", depois das mensagens")
            historico = chat.get_by_test_id("chat-historico")
            rolagem = historico.evaluate("e => ({altura: e.scrollHeight, visivel: e.clientHeight, estilo: getComputedStyle(e).overflowY})")
            assert rolagem["estilo"] in ("auto", "scroll"), (rotulo, rolagem)
            if rolagem["altura"] > rolagem["visivel"] + 1:
                historico.evaluate("e => { e.scrollTop = 0; }")
                assert historico.evaluate("e => e.scrollTop") == 0, rotulo
                historico.evaluate("e => { e.scrollTop = e.scrollHeight; }")
                assert historico.evaluate("e => e.scrollTop") > 0, (rotulo, "o histórico rola por dentro")

            if largura < 640:
                expect(chat).to_have_attribute("data-ancorada", "true")
                context.close()
                continue

            # Arrastar o cabeçalho até além dos quatro cantos: a caixa fica inteira na janela.
            handle = chat.get_by_test_id("painel-chat-handle")
            for dx, dy in ((-3000, -3000), (3000, -3000), (-3000, 3000), (3000, 3000)):
                cabeca = handle.bounding_box()
                x, y = cabeca["x"] + cabeca["width"] * 0.35, cabeca["y"] + cabeca["height"] / 2
                page.mouse.move(x, y)
                page.mouse.down()
                page.mouse.move(x + dx, y + dy, steps=6)
                page.mouse.up()
                conferir(page, chat, f"{rotulo}, arrastada ({dx}, {dy})")
            # Minimizar e abrir de novo, com a caixa no alto da janela.
            cabeca = handle.bounding_box()
            page.mouse.move(cabeca["x"] + cabeca["width"] * 0.35, cabeca["y"] + cabeca["height"] / 2)
            page.mouse.down()
            page.mouse.move(cabeca["x"] - 3000, cabeca["y"] - 3000, steps=6)
            page.mouse.up()
            chat.get_by_test_id("painel-chat-minimizar").click()
            expect(chat).to_have_attribute("data-minimizada", "true")
            assert dentro(chat.bounding_box(), largura, altura), rotulo
            chat.get_by_test_id("painel-chat-minimizar").click()
            expect(chat).to_have_attribute("data-minimizada", "false")
            conferir(page, chat, rotulo + ", aberta de novo")
            # A janela encolhendo traz para dentro a caixa encostada no canto inferior direito.
            cabeca = handle.bounding_box()
            page.mouse.move(cabeca["x"] + cabeca["width"] * 0.35, cabeca["y"] + cabeca["height"] / 2)
            page.mouse.down()
            page.mouse.move(cabeca["x"] + 3000, cabeca["y"] + 3000, steps=6)
            page.mouse.up()
            page.set_viewport_size({"width": max(700, largura - 300), "height": max(560, altura - 200)})
            page.wait_for_timeout(300)
            conferir(page, chat, rotulo + ", janela menor")
            page.set_viewport_size({"width": largura, "height": altura})
            handle.focus()
            handle.press("Home")
            page.wait_for_timeout(300)
            conferir(page, chat, rotulo + ", de volta ao canto")
            context.close()
        browser.close()
    print("CAIXA DA CONVERSA PASS: inteira na janela com zoom de 100% em " + ", ".join(f"{l}×{a}" for l, a in RESOLUCOES)
          + "; campo de envio à vista e utilizável, histórico com rolagem interna, arrastar, minimizar e a janela menor.")


if __name__ == "__main__":
    main()
