"""Navegação compartilhada dos roteiros de navegador da página única (22/10/2026); só permite URLs locais.

A estrutura da página (cabeçalho, fonte, painel "Colunas", Histórico e conversa) usa os data-testid da frente B1. A área de
análise é da frente B2: os seletores dela que os roteiros da estrutura usam ficam em AREA, num lugar só, para alinhar com os
data-testid que a área documentar. Os roteiros da estrutura conferem o que a área pede ao motor pela rede (/api/painel), sem
depender do desenho do gráfico.
"""
import json
import os
import re
from urllib.parse import urlparse

from playwright.sync_api import expect

URL = os.getenv("ADT_UI_URL", "http://127.0.0.1:5173/")
assert urlparse(URL).hostname in ("127.0.0.1", "localhost", "::1")

# Área de análise (frente B2): só a raiz. O resto da área é conferido pelo roteiro dela (ui_area_de_analise.py).
AREA = {"raiz": "area-de-analise"}
PRIVACIDADE = "Declaro que não compartilharei dados pessoais ou sensíveis"


def offline(context):
    context.route("**/*", lambda route: route.continue_() if urlparse(route.request.url).hostname
                  in ("127.0.0.1", "localhost", "::1") else route.abort())


def accept_privacy(page):
    page.get_by_role("button", name="Li e concordo", exact=True).click()


def form_field(request, name):
    """Campo de texto de um formulário multipart (FormData) enviado pela página, ou None."""
    body = request.post_data or ""
    head = 'name="' + name + '"\r\n\r\n'
    if head not in body:
        return None
    return body.split(head, 1)[1].split("\r\n--", 1)[0]


def options_of(request):
    return json.loads(form_field(request, "options") or "{}")


def uploaded_filename(request):
    """Nome do arquivo enviado no campo "file" do formulário, ou None (base do Brasil)."""
    match = re.search(r'name="file"; filename="([^"]*)"', request.post_data or "")
    return match.group(1) if match else None


def is_post(response, suffix):
    return response.url.endswith(suffix) and response.request.method == "POST"


def open_chat(page):
    """A caixa da conversa fica sempre na página; minimizada, abre pelo botão do cabeçalho dela."""
    chat = page.get_by_test_id("painel-chat")
    if chat.get_attribute("data-minimizada") == "true":
        chat.get_by_test_id("painel-chat-minimizar").click()
    expect(chat.locator("#assistant-input")).to_be_visible()
    return chat


def send(page, message, timeout=90000):
    """Envia uma mensagem pela caixa da conversa e espera o campo voltar a aceitar texto."""
    chat = open_chat(page)
    chat.locator("#assistant-input").fill(message)
    chat.get_by_role("button", name="Enviar mensagem", exact=True).click()
    expect(chat.locator("#assistant-input")).to_be_enabled(timeout=timeout)


def end_session(page):
    page.get_by_test_id("nav-new-session").click()
    expect(page.get_by_test_id("new-session-confirmation")).to_be_visible()
    page.get_by_test_id("confirm-new-session").click()


def history_label(count):
    """Texto acessível do resumo do Histórico (visível para leitores de tela): "1 análise nesta sessão"."""
    return str(count) + (" análise" if count == 1 else " análises") + " nesta sessão"


def no_horizontal_scroll(page, label=""):
    assert page.evaluate("document.documentElement.scrollWidth <= window.innerWidth + 2"), (label, page.evaluate(
        "[...document.querySelectorAll('body *')].filter(e => e.getBoundingClientRect().right > innerWidth + 2)"
        ".slice(0, 10).map(e => e.tagName + '.' + (typeof e.className === 'string' ? e.className.slice(0, 60) : ''))"))
