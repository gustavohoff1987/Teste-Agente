"""Responsividade, toque e esquemas de cor da página única (05/11/2026, comando do responsável: "a interface funcionar corretamente
em celulares e computadores", com as larguras de 320, 360, 390, 430, 768, 1024 e 1440 px, nos dois esquemas de cor).

Com a base Brasil versionada (suíte base-versionada), em cada largura e esquema, confere o que a tela renderizada de fato mostra
(as caixas do navegador, não o CSS):
- nada passa da largura da janela (sem rolagem horizontal da página; tabelas e abas roláveis, sim, por dentro), na abertura, na
  Seleção de Territórios, na análise e na tendência;
- a Seleção unificada: a raiz Brasil e os estados com o nome inteiro (sem corte), a caixa e o botão da lista com alvo de toque de 40
  px no celular; o Amazonas inteiro e um município do Pará (a combinação, com o Pará em parte); os totais individualizados (o
  Amazonas pela fonte estadual) e a nota do Pará sem total;
- a análise: a legenda das bolhas (a de tamanho e as outras) sem textos sobrepostos; a dica de uma bolha, pelo foco no celular (o
  caminho do teclado e do leitor de tela) e pelo mouse no computador, inteira dentro da janela; no celular, o toque na bolha, que
  desde 06/11/2026 abre o lugar do município, com o cartão dele no alto, inteiro dentro da janela e sem textos sobrepostos (o
  Desfazer volta à seleção); os totais no alto do resultado;
- a tendência: o quadro de setas sem passar da largura e o ritmo de variação da linha escolhida (pelo toque no celular), com o
  título e a explicação;
- no mapa (390 px no claro e 1.440 px no escuro): a legenda de tamanho sem sobreposição;
- no computador (1.440 px), a disposição de referência: a árvore e o que está na análise lado a lado, os estados em colunas.
No escuro, o esquema é o do aparelho, e os textos conferidos ficam a 4,5:1 ou mais do fundo. Tira capturas em .local/ui-validation
(responsivo-*.png). Nunca chama o provedor de IA; nenhum erro de página.
"""
import os
from pathlib import Path

from playwright.sync_api import expect, sync_playwright
from ui_support import URL, abrir_regiao, offline

OUTPUT = Path(__file__).resolve().parents[2] / ".local" / "ui-validation"
AM, PA = "13", "15"
BOLHAS = '[data-testid="analise-bolha"][data-visivel="true"]'
# (largura, esquema, com o mapa)
CASOS = [(320, "light", False), (360, "dark", False), (390, "light", True), (390, "dark", False), (430, "dark", False),
         (768, "light", False), (1024, "dark", False), (1440, "light", False), (1440, "dark", True)]

# Elementos que passam da largura da janela, fora dos contêineres com rolagem horizontal própria.
TRANSBORDA = """() => {
  const largura = document.documentElement.clientWidth, fora = [];
  for (const e of document.querySelectorAll('body *')) {
    const r = e.getBoundingClientRect();
    if (r.width < 1 || r.height < 1) continue;
    const st = getComputedStyle(e);
    if (st.visibility === 'hidden' || st.display === 'none' || st.position === 'fixed') continue;
    let p = e.parentElement, rola = false;
    for (; p; p = p.parentElement) { const s = getComputedStyle(p);
      if (/(auto|scroll|hidden)/.test(s.overflowX) && p.scrollWidth > p.clientWidth + 1) { rola = true; break; } }
    if (rola) continue;
    if (r.right > largura + 1 || r.left < -1)
      fora.push((e.getAttribute('data-testid') || e.tagName.toLowerCase()) + ' [' + Math.round(r.left) + ', ' + Math.round(r.right) + ']');
  }
  return { pagina: document.documentElement.scrollWidth - largura, fora: fora.slice(0, 10) };
}"""

# Textos que se sobrepõem dentro de um elemento (texto do SVG e elementos folha de texto).
SOBREPOSTOS = """(raiz) => {
  const caixas = [];
  for (const e of raiz.querySelectorAll('text, span, p, strong, small, dd, li, label')) {
    if (e.tagName !== 'text' && [...e.children].some(f => (f.textContent || '').trim())) continue;
    if (!(e.textContent || '').trim()) continue;
    const r = e.getBoundingClientRect();
    if (r.width < 2 || r.height < 2) continue;
    const st = getComputedStyle(e);
    if (st.visibility === 'hidden' || st.display === 'none') continue;
    caixas.push({ e, r, t: (e.textContent || '').trim().slice(0, 40) });
  }
  const pares = [];
  for (let i = 0; i < caixas.length; i++) for (let j = i + 1; j < caixas.length; j++) {
    const a = caixas[i], b = caixas[j];
    if (a.e.contains(b.e) || b.e.contains(a.e)) continue;
    const x = Math.min(a.r.right, b.r.right) - Math.max(a.r.left, b.r.left);
    const y = Math.min(a.r.bottom, b.r.bottom) - Math.max(a.r.top, b.r.top);
    if (x > 2 && y > 2) pares.push(a.t + ' × ' + b.t);
  }
  return pares;
}"""

CONTRASTE = """(e) => {
  const ler = t => { const m = /rgba?\\(([^)]+)\\)/.exec(t || ''); if (!m) return null;
    const p = m[1].split(/[\\s,\\/]+/).filter(Boolean).map(Number); return [p[0], p[1], p[2], p.length > 3 ? p[3] : 1]; };
  const lum = c => { const f = v => { v /= 255; return v <= 0.04045 ? v / 12.92 : ((v + 0.055) / 1.055) ** 2.4; };
    return 0.2126 * f(c[0]) + 0.7152 * f(c[1]) + 0.0722 * f(c[2]); };
  const camadas = [];
  for (let x = e; x; x = x.parentElement) { const c = ler(getComputedStyle(x).backgroundColor);
    if (c && c[3] > 0) { camadas.push(c); if (c[3] >= 1) break; } }
  let f = [255, 255, 255];
  for (let i = camadas.length - 1; i >= 0; i--) { const [r, g, b, a] = camadas[i]; f = [r * a + f[0] * (1 - a), g * a + f[1] * (1 - a), b * a + f[2] * (1 - a)]; }
  const c = ler(getComputedStyle(e).color) || [0, 0, 0, 1];
  const cor = [0, 1, 2].map(i => c[i] * c[3] + f[i] * (1 - c[3]));
  const [a, b] = [lum(cor), lum(f)].sort((m, n) => n - m);
  return { razao: (a + 0.05) / (b + 0.05), fundo: lum(f) };
}"""


def main():
    OUTPUT.mkdir(parents=True, exist_ok=True)
    notas = []
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True, channel=os.getenv("ADT_BROWSER_CHANNEL", "chrome"))
        for largura, esquema, com_mapa in CASOS:
            movel = largura < 700
            nome = f"{esquema}-{largura}"
            contexto = browser.new_context(viewport={"width": largura, "height": 800 if movel else 900}, color_scheme=esquema,
                                           has_touch=movel, is_mobile=movel)
            offline(contexto)
            page = contexto.new_page()
            erros, chamadas_llm = [], []
            page.on("pageerror", lambda error: erros.append(str(error)))
            page.on("request", lambda request: chamadas_llm.append(request.url) if "/api/llm/interpret" in request.url else None)

            def sem_transbordar(onde):
                medida = page.evaluate(TRANSBORDA)
                assert medida["pagina"] <= 1 and not medida["fora"], (nome, onde, "passa da largura da janela", medida)

            def legivel(locator, rotulo):
                if esquema != "dark":
                    return
                medida = locator.evaluate(CONTRASTE)
                assert medida["fundo"] < 0.08, (nome, rotulo, "fundo claro no escuro", medida)
                assert medida["razao"] >= 4.5, (nome, rotulo, "contraste abaixo de 4,5:1", medida)

            def sem_sobrepor(locator, rotulo):
                pares = locator.evaluate(SOBREPOSTOS)
                assert not pares, (nome, rotulo, "textos sobrepostos", pares[:6])

            def dentro_da_janela(locator, rotulo):
                caixa = locator.bounding_box()
                assert caixa, (nome, rotulo, "sem caixa")
                assert caixa["x"] >= -1 and caixa["x"] + caixa["width"] <= largura + 1, (nome, rotulo, "passa da largura", caixa)

            def toca(locator):
                locator.scroll_into_view_if_needed()
                if movel:
                    locator.tap()
                else:
                    locator.click()

            def marca(locator):
                locator.scroll_into_view_if_needed()
                locator.focus()
                locator.press("Space")

            def painel(acao, timeout=180000):
                with page.expect_response(lambda r: r.url.endswith("/api/painel") and r.request.method == "POST", timeout=timeout) as evento:
                    acao()
                assert evento.value.status == 200, evento.value.text()[:1500]
                return evento.value.json()

            # 1. Abertura: o esquema do aparelho e nada passando da largura.
            page.goto(URL)
            page.get_by_role("button", name="Li e concordo", exact=True).click()
            area = page.get_by_test_id("area-de-analise")
            expect(area).to_be_visible(timeout=60000)
            assert page.evaluate("getComputedStyle(document.documentElement).colorScheme") == ("dark" if esquema == "dark" else "light")
            chat = page.get_by_test_id("painel-chat")
            if chat.get_attribute("data-minimizada") != "true":
                chat.get_by_test_id("painel-chat-minimizar").click()
            sem_transbordar("abertura")

            # 2. A Seleção do comando V22 (9/11/2026): a árvore Brasil → região → estado → município, com o resumo do universo na
            # linha do Brasil e as regiões recolhidas (abertas pela seta); os estados com o nome inteiro, os alvos de toque e nada
            # passando da largura.
            toca(area.get_by_test_id("analise-fonte-brasil"))
            territorios = area.get_by_test_id("analise-territorios")
            expect(territorios).to_be_visible(timeout=180000)
            expect(territorios.get_by_test_id("analise-raiz-universo")).to_have_text("5.570 municípios | 27 UFs")
            expect(territorios.locator('[data-testid="analise-regiao"]')).to_have_count(5)
            sem_transbordar("Seleção de Territórios")
            for regiao in ("1", "2", "5", "3", "4"):
                abrir_regiao(territorios, regiao)
            linhas = territorios.locator('[data-testid="analise-grupo"]')
            expect(linhas).to_have_count(27)
            medidas = linhas.evaluate_all("""els => els.map(e => { const n = e.querySelector('.analise-no-nome');
              const v = e.querySelector('[data-testid=analise-grupo-ver]'), c = e.querySelector('.analise-no-caixa');
              const r = document.createRange(); r.selectNodeContents(n);
              const linhas = new Set([...r.getClientRects()].map(x => Math.round(x.top))).size;
              return { id: e.dataset.id, nome: n.textContent, cortado: n.scrollWidth > n.clientWidth + 1, largura: n.getBoundingClientRect().width,
                linhas, ver: [v.getBoundingClientRect().width, v.getBoundingClientRect().height], caixa: c.getBoundingClientRect().height }; })""")
            for medida in medidas:
                # Espremido: com menos de 60 px e o nome quebrado em linhas. Um nome curto ("Pará (PA)", 58 px) cabe inteiro numa linha.
                espremido = medida["largura"] < 60 and medida["linhas"] > 1
                assert not medida["cortado"] and not espremido, (nome, "nome do estado cortado ou espremido", medida)
                if movel:
                    assert min(medida["ver"]) >= 39.5 and medida["caixa"] >= 39.5, (nome, "alvo de toque menor que 40 px", medida)
            legivel(territorios.locator('[data-testid="analise-grupo"][data-id="' + AM + '"] .analise-no-nome'), "nome do estado")
            legivel(territorios.get_by_test_id("analise-territorios-instrucao"), "orientação da árvore")
            # O Amazonas inteiro e um município do Pará: a combinação, com o Pará em parte.
            painel(lambda: marca(territorios.locator('[data-testid="analise-grupo"][data-id="' + AM + '"]').get_by_test_id("analise-grupo-todos")))
            linha_pa = territorios.locator('[data-testid="analise-grupo"][data-id="' + PA + '"]')
            toca(linha_pa.get_by_test_id("analise-grupo-ver"))
            expect(linha_pa).to_have_attribute("data-aberto", "true")
            corpo = painel(lambda: marca(linha_pa.get_by_test_id("analise-unidade").first.locator("input")))
            expect(linha_pa).to_have_attribute("data-situacao", "parcial")
            assert [item["id"] for item in corpo["contexto"]["estados"]] == ["uf:" + AM], corpo["contexto"]
            totais = territorios.get_by_test_id("analise-abrangencia")
            expect(totais.locator('[data-id="uf:' + AM + '"]')).to_have_attribute(
                "data-quantidade", str(corpo["contexto"]["estados"][0]["quantidade"]))
            expect(totais.get_by_test_id("analise-abrangencia-parciais")).to_contain_text("Pará (1 de 144)")
            dentro_da_janela(totais, "totais na Seleção")
            legivel(totais.locator('[data-id="uf:' + AM + '"]'), "total individualizado do estado")
            sem_transbordar("Seleção com o Pará aberto")
            if largura >= 1440:
                # A disposição de referência no computador: a árvore e o painel dos selecionados lado a lado. Desde o comando V22
                # (seção 3; muda de propósito esta conferência, que via os estados em colunas), a árvore, com os estados recuados
                # sob a região deles.
                lista = territorios.get_by_test_id("analise-territorios-lista").bounding_box()
                lado = territorios.get_by_test_id("analise-selecionados").bounding_box()
                assert lista["x"] + lista["width"] <= lado["x"] + 1 and abs(lista["y"] - lado["y"]) < 8, (nome, lista, lado)
                x_regiao = territorios.locator('[data-testid="analise-regiao"][data-id="1"]').bounding_box()["x"]
                recuos = {round(caixa["x"]) for caixa in linhas.evaluate_all("els => els.map(e => e.getBoundingClientRect().toJSON())")}
                assert len(recuos) == 1 and min(recuos) > x_regiao + 8, (nome, "os estados recuados sob a região", recuos, x_regiao)
            page.screenshot(path=str(OUTPUT / ("responsivo-" + nome + "-selecao.png")))

            # 3. A análise: a legenda sem textos sobrepostos, a dica dentro da janela e os totais no alto do resultado.
            toca(territorios.get_by_test_id("analise-confirmar-selecao"))
            expect(area).to_have_attribute("data-aba", "distribuicao")
            expect(area.locator(BOLHAS).first).to_be_visible(timeout=60000)
            page.wait_for_timeout(800)  # transições do gráfico
            sem_transbordar("análise")
            legenda = area.locator("figcaption.analise-legenda").first
            sem_sobrepor(legenda, "legenda das bolhas")
            expect(area.get_by_test_id("analise-legenda-tamanho")).to_be_visible()
            dentro_da_janela(area.get_by_test_id("analise-legenda-tamanho"), "legenda de tamanho")
            totais_resultado = area.get_by_test_id("analise-abrangencia")
            expect(totais_resultado.locator('[data-id="uf:' + AM + '"]')).to_be_visible()
            dentro_da_janela(totais_resultado, "totais no resultado")
            bolha = area.locator(BOLHAS).first
            bolha.scroll_into_view_if_needed()
            # Desde 06/11/2026, o toque numa bolha de município abre o lugar dele (item 3.4 do comando): no celular, a dica aparece
            # com o foco (o caminho do teclado e do leitor de tela); no computador, com o mouse.
            if movel:
                bolha.focus()
            else:
                bolha.hover()
            dica = area.get_by_test_id("analise-dica")
            expect(dica).to_be_visible(timeout=10000)
            dentro_da_janela(dica, "dica da bolha")
            legivel(dica.locator("strong").first, "título da dica")
            page.screenshot(path=str(OUTPUT / ("responsivo-" + nome + "-analise.png")))
            if not movel:
                page.mouse.move(2, 2)
            else:
                # O toque abre o município: o cartão dele no alto (os valores do motor e as barras do município, do estado e do
                # Brasil), inteiro dentro da janela; a trilha termina nele. O Desfazer volta à seleção, da memória da tela.
                bolha.press("Escape")
                expect(dica).to_have_count(0)
                id_bolha = bolha.get_attribute("data-id")
                painel(lambda: bolha.tap())
                cartao = area.get_by_test_id("analise-cartao")
                expect(cartao).to_have_attribute("data-id", id_bolha, timeout=60000)
                expect(cartao.get_by_test_id("analise-cartao-barra")).to_have_count(3, timeout=60000)
                dentro_da_janela(cartao, "cartão do município")
                sem_sobrepor(cartao, "cartão do município")
                legivel(cartao.get_by_test_id("analise-cartao-quantidade"), "quantidade no cartão")
                atual = area.get_by_test_id("analise-trilha").locator('[aria-current="location"]')
                expect(atual).to_have_attribute("data-id", id_bolha)
                dentro_da_janela(area.get_by_test_id("analise-trilha"), "trilha")
                sem_transbordar("cartão do município")
                page.screenshot(path=str(OUTPUT / ("responsivo-" + nome + "-cartao.png")))
                toca(area.get_by_test_id("analise-desfazer"))
                expect(area.locator(BOLHAS).first).to_be_visible(timeout=60000)
                expect(cartao).to_have_count(0)

            # 4. A tendência: o quadro de setas sem passar da largura e o ritmo de variação da linha escolhida.
            painel(lambda: toca(area.get_by_test_id("analise-familia-tendencia")))
            quadro = area.get_by_test_id("analise-setas")
            expect(quadro).to_be_visible(timeout=60000)
            sem_transbordar("tendência")
            toca(quadro.get_by_test_id("analise-seta-linha").first)
            ritmo = area.get_by_test_id("analise-velocidades")
            expect(ritmo.get_by_test_id("analise-ritmo-titulo")).to_contain_text("Ritmo de variação — ")
            expect(ritmo.get_by_test_id("analise-ritmo-explicacao")).to_contain_text("aceleração, desaceleração ou mudança de direção")
            dentro_da_janela(ritmo, "ritmo de variação")
            sem_sobrepor(ritmo, "ritmo de variação")
            legivel(ritmo.get_by_test_id("analise-ritmo-titulo"), "título do ritmo de variação")
            page.screenshot(path=str(OUTPUT / ("responsivo-" + nome + "-tendencia.png")))

            # 5. O mapa: a legenda de tamanho sem sobreposição e nada passando da largura.
            if com_mapa:
                toca(area.get_by_test_id("analise-familia-distribuicao"))
                toca(area.get_by_test_id("analise-desenho-mapa"))
                mapa = area.get_by_test_id("mapa-analise")
                expect(mapa).to_be_visible(timeout=120000)
                tamanho = mapa.get_by_test_id("mapa-legenda-tamanho")
                expect(tamanho).to_be_visible(timeout=60000)
                sem_sobrepor(tamanho, "legenda de tamanho do mapa")
                dentro_da_janela(tamanho, "legenda de tamanho do mapa")
                sem_transbordar("mapa")
                page.screenshot(path=str(OUTPUT / ("responsivo-" + nome + "-mapa.png")))
            assert not erros, (nome, erros)
            assert not chamadas_llm, (nome, chamadas_llm)
            notas.append(nome)
            contexto.close()
        browser.close()
    print("RESPONSIVO PASS: " + ", ".join(notas) + " (sem rolagem horizontal, nomes inteiros, toque de 40 px, legendas sem "
          "sobreposição, dica, cartão do município e ritmo de variação dentro da janela, totais individualizados, mapa e "
          "disposição do computador).")


if __name__ == "__main__":
    main()
