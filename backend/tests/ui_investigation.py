"""Investigação progressiva pela interface e API reais; sem chamadas ao provedor.

Roda com catálogo sintético e base versionada (somente leitura). Nenhum resultado é
fabricado: todos os resultados usados na jornada vêm de /api/analyze.
"""
import json
import os
from pathlib import Path
from playwright.sync_api import TimeoutError as PlaywrightTimeoutError, sync_playwright, expect
from ui_support import end_session, execute_analysis, URL, offline, select

OUTPUT = Path(__file__).resolve().parents[2] / '.local/ui-validation'


def main():
    real = os.getenv('ADT_BLOCK1_REAL') == '1'
    OUTPUT.mkdir(parents=True, exist_ok=True)
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True, channel=os.getenv('ADT_BROWSER_CHANNEL', 'chrome'))
        context = browser.new_context(viewport={'width': 1360, 'height': 900}, accept_downloads=True)
        offline(context)
        context.add_init_script('window.__ADT_TEST__ = true')
        page = context.new_page()
        page.set_default_timeout(15000)
        errors, requests, results = [], [], []
        page.on('pageerror', lambda error: errors.append(str(error)))
        page.on('request', lambda r: requests.append(r) if r.url.endswith('/api/analyze') else None)
        page.goto(URL)
        page.get_by_role('button', name='Li e concordo', exact=True).click()
        chat = page.locator('#assistente')
        board = page.locator('#resultados')
        overview = page.get_by_test_id('investigation-overview')
        inline = page.locator('#preparacao-conversacional')

        def send(message, response=False):
            print('Pedido: ' + message, flush=True)
            page.locator('#assistant-input').fill(message)
            if response:
                with page.expect_response(lambda r: r.url.endswith('/api/llm/interpret-context'), timeout=90000) as event:
                    chat.get_by_role('button', name='Enviar mensagem', exact=True).click()
                assert event.value.status == 200, event.value.text()
                answer = event.value.json()
            else:
                chat.get_by_role('button', name='Enviar mensagem', exact=True).click()
                answer = None
            expect(page.locator('#assistant-input')).to_be_enabled(timeout=90000)
            return answer

        def calculate():
            print('Executando etapa ' + str(len(results) + 1), flush=True)
            button = inline.get_by_role('button', name='Calcular e mostrar resultado', exact=True)
            expect(button).to_be_enabled(timeout=90000)
            with page.expect_response(lambda r: r.url.endswith('/api/analyze'), timeout=120000) as event:
                execute_analysis(page, button)
            assert event.value.status == 200, event.value.text()
            result = event.value.json()
            results.append(result)
            print('Resultado recebido: ' + result['title'], flush=True)
            expect(board.get_by_test_id('result-title')).to_have_text(result['title'])
            expect(overview.get_by_test_id('investigation-card')).to_have_count((len(results) - 1) % 6 + 1)
            return result

        def open_stage(index):
            print('Reabrindo etapa ' + str(index + 1), flush=True)
            button = overview.get_by_test_id('open-investigation-' + str(index))
            expect(button).to_be_enabled(timeout=90000)
            button.click()
            expect(board.get_by_test_id('result-title')).to_have_text(results[index]['title'])

        def method():
            with page.expect_download() as download:
                board.get_by_text('Opções técnicas avançadas', exact=True).click()
                board.get_by_role('button', name='Baixar registro técnico (JSON)', exact=True).click()
                board.get_by_text('Opções técnicas avançadas', exact=True).click()
            return json.loads(Path(download.value.path()).read_text(encoding='utf-8'))

        send('Olá')
        expect(overview).to_have_count(0)
        expect(page.get_by_test_id('investigation-card')).to_have_count(0)
        chat.get_by_role('button', name='Usar dados do Brasil', exact=False).click()
        expect(page.get_by_test_id('current-source')).to_be_visible(timeout=90000)
        send('Mostre a densidade médica dos municípios do Amazonas em junho de 2024.')
        first = calculate()
        assert first['total_rows'] == (62 if real else 3)
        rows = board.locator('#tabela-resultado tbody tr')
        rows.nth(0).click()
        rows.nth(1).click()
        selected = method()['representacao_aplicada']['selecao_visual']
        assert len(selected) == 2
        board.get_by_label('Filtrar Território', exact=True).fill(first['rows'][0]['Território'])
        expect(rows).to_have_count(1)
        board.get_by_role('button', name='Recolher análise', exact=True).click()
        expect(board.get_by_test_id('result-title')).not_to_be_visible()
        page.emulate_media(media='print')
        expect(board.get_by_test_id('result-title')).to_be_visible()
        page.emulate_media(media='screen')
        board.get_by_role('button', name='Expandir análise', exact=True).click()
        expect(rows).to_have_count(1)

        # Escolha direta mantém a preparação explícita e não depende de inferência do chat.
        chat.get_by_text('Escolher outra análise', exact=True).click()
        select(page, 'Distribuição')
        inline.get_by_role('combobox', name='Indicador', exact=True).select_option('density')
        second = calculate()
        assert second['metadata']['operation'] == 'distribution'
        assert second['metadata']['options']['quantile_count'] == 5
        open_stage(0)
        expect(rows).to_have_count(1)
        assert method()['representacao_aplicada']['selecao_visual'] == selected
        expect(overview.get_by_test_id('transfer-selection-1')).to_be_enabled()
        overview.get_by_test_id('transfer-selection-1').click()
        expect(board.get_by_test_id('result-title')).to_have_text(second['title'])
        assert method()['representacao_aplicada']['selecao_visual'] == selected
        # Classes e valores permanecem os do motor; a seleção não modifica a preparação.
        expect(board.get_by_role('region', name='Territórios selecionados')).to_be_visible()
        assert len(requests) == 2
        if real:
            board.get_by_role('tab', name='Mapa', exact=True).click()
            expect(board.get_by_test_id('territory-map')).to_be_visible()
            assert page.evaluate('window.__adtMapModel.selected') == selected

        open_stage(0)
        answer = send('O que esse resultado significa?', response=True)
        assert answer['result_reference']['result_id'] == first['result_id']
        assert answer['result_reference']['origin'] == 'BACKEND_VERIFIED_RESULT'
        assert not answer['executed'] and len(requests) == 2
        board.get_by_role('button', name='Limpar filtros da tabela', exact=True).click()
        expect(rows).to_have_count(first['total_rows'])
        board.get_by_role('button', name='Usar seleção na próxima análise', exact=True).click()
        send('Compare os selecionados.')
        inline.get_by_label('As medidas, unidades e populações são comparáveis entre os territórios.').check()
        compared = calculate()
        assert set(compared['metadata']['options']['territory_ids']) == set(selected)
        open_stage(0)
        expect(overview.get_by_test_id('transfer-selection-2')).to_be_disabled()
        expect(overview.get_by_test_id('investigation-card').nth(2)).to_contain_text('Recortes territoriais diferentes')
        assert len(requests) == 3

        # Parâmetros atuais não alteram os três resultados já calculados.
        send('Mostre a densidade médica dos municípios do Amazonas em janeiro de 2024.')
        expect(board.get_by_test_id('result-title')).to_have_text(first['title'])
        assert method()['result_id'] == first['result_id'] and len(requests) == 3
        def while_loading(route):
            # Segura apenas o transporte até verificar a tela; o cálculo seguinte é real.
            expect(overview.get_by_role('status')).to_contain_text('Preparando a próxima análise')
            expect(board.get_by_test_id('result-title')).to_have_text(first['title'])
            selection = page.get_by_role('region', name='Seleção territorial compartilhada', exact=True)
            expect(selection.get_by_role('searchbox')).to_be_disabled()
            expect(overview.get_by_test_id('transfer-selection-1')).to_be_disabled()
            route.continue_()
        page.route('**/api/analyze', while_loading, times=1)
        fourth = calculate()
        assert fourth['metadata']['periods'] == ['202401']
        open_stage(0)
        expect(overview.get_by_test_id('transfer-selection-3')).to_be_disabled()
        expect(overview.get_by_test_id('investigation-card').nth(3)).to_contain_text('Períodos diferentes')

        for width in (1360, 768, 390):
            page.set_viewport_size({'width': width, 'height': 900})
            overview.scroll_into_view_if_needed()
            assert page.evaluate('document.documentElement.scrollWidth <= innerWidth + 2')
            page.screenshot(path=str(OUTPUT / f'investigacao-{real}-{width}.png'))
        assert len(requests) == 4 and not errors, errors
        # O histórico antigo continua acessível; os novos controles não o substituem.
        history = page.get_by_role('region', name='Histórico de análises')
        history.locator('summary').click()
        expect(history.get_by_role('button')).to_have_count(4)
        if not real:
            history.locator('summary').click()
            page.set_viewport_size({'width': 1360, 'height': 900})
            for period in ('janeiro de 2023', 'junho de 2023'):
                send(f'Mostre a densidade médica dos municípios do Amazonas em {period}.')
                calculate()
            # Acrescenta a dimensão espacial pelo fluxo existente, sem mudar métodos.
            open_stage(0)
            board.get_by_role('button', name='Retomar parâmetros deste resultado', exact=True).click()
            select(page, 'Análise espacial')
            inline.get_by_label('Referencial geodésico', exact=True).select_option('SIRGAS2000')
            reference_label = next(member['label'] for member in first['metadata']['universe']['members'] if member['id'] == 'code:130260')
            inline.get_by_label('Território de referência', exact=True).select_option(label=reference_label)
            spatial = calculate()
            assert spatial['metadata']['operation'] == 'spatial'
            assert all(row['Distância (km)'] == 0 for row in spatial['rows'])  # coordenadas da fixture coincidem
            expect(overview.get_by_role('navigation', name='Etapas da investigação')).to_contain_text('Página 2 de 2')
            overview.get_by_role('button', name='Etapas anteriores', exact=True).click()
            open_stage(0)
            overview.get_by_role('button', name='Etapas seguintes', exact=True).click()
            expect(overview.get_by_test_id('transfer-selection-6')).to_be_enabled()
            overview.get_by_test_id('transfer-selection-6').click()
            expect(board.get_by_test_id('territory-map')).to_be_visible()
            assert page.evaluate('window.__adtMapModel.selected') == selected
            assert method()['representacao_aplicada']['selecao_visual'] == selected
            # Falha de transporte injetada: resultados reais anteriores continuam consultáveis.
            select(page, 'Quantitativos')
            page.route('**/api/analyze', lambda route: route.abort('failed'))
            execute = inline.get_by_role('button', name='Calcular e mostrar resultado', exact=True)
            expect(execute).to_be_enabled(timeout=90000)
            execute_analysis(page, execute)
            expect(board.get_by_role('alert')).to_contain_text('Não foi possível acessar o serviço de análise')
            expect(board.get_by_test_id('result-title')).to_have_text(spatial['title'])
            expect(overview).to_contain_text('7 resultados disponíveis')
            page.unroute('**/api/analyze')
            calculate()
            # Limite real do servidor: preenche as referências com cálculos reais da API.
            headers = {'X-ADT-Session': requests[0].headers['x-adt-session']}
            state = context.request.get(URL.rstrip('/') + '/api/session', headers=headers).json()
            for _ in range(64 - len(results)):
                response = context.request.post(URL.rstrip('/') + '/api/analyze', headers=headers, form={
                    'dataset': 'brazil', 'scope': 'municipal', 'operation': 'counts',
                    'dataset_version': first['metadata']['source']['version'],
                    'mapping': json.dumps(first['metadata']['mapping']), 'options': json.dumps(first['metadata']['options']),
                    'context_revision': str(state['revision']),
                })
                assert response.status == 200, response.text()
                assert response.json()['conversation_reference']['available']
            send('Mostre a densidade médica dos municípios do Amazonas em janeiro de 2023.')
            select(page, 'Quantitativos')
            limited = calculate()
            assert limited['conversation_reference']['available'] is False
            expect(board.get_by_text('O limite de memória das referências conversacionais foi atingido', exact=False)).to_be_visible()
            assert method()['result_id'] == limited['result_id']
            # Troca de fonte preserva consulta e bloqueia reutilização da seleção antiga.
            page.get_by_label('Importar arquivo de dados').set_input_files({'name': 'outra_fonte.csv', 'mimeType': 'text/csv',
                'buffer': b'Municipio;Periodo;Quantidade;Populacao\nOutro;2024;1;100\n'})
            expect(page.get_by_test_id('current-source')).to_contain_text('outra_fonte.csv', timeout=90000)
            overview.get_by_role('button', name='Etapas anteriores', exact=True).click()
            open_stage(0)
            expect(board.get_by_role('button', name='Usar seleção na próxima análise', exact=True)).to_be_disabled()
            # Perda efetiva da sessão no servidor: o próximo controle recebe 410 e descarta a aba.
            assert context.request.post(URL.rstrip('/') + '/api/session/close', headers=headers).status == 200
            # A sessão encerrada pode exibir imediatamente o diálogo obrigatório de privacidade.
            # Se estiver aberto, a interação com a navegação é corretamente bloqueada.
            privacy = page.get_by_role('button', name='Li e concordo', exact=True)
            notice = page.get_by_test_id('session-ended-notice')
            if not privacy.is_visible():
                # O diálogo pode surgir entre is_visible() e click() após o 410.
                # Não forçar clique através do diálogo: aceitar apenas essa corrida
                # comprovada, mantendo falhas de navegação reais visíveis.
                try:
                    page.get_by_role('navigation', name='Navegação principal').get_by_role(
                        'button', name='Resultados', exact=True
                    ).click(timeout=2500)
                except PlaywrightTimeoutError:
                    if not privacy.is_visible():
                        raise
            expect(notice).to_contain_text('expirou ou ficou indisponível', timeout=15000)
            page.get_by_role('button', name='Li e concordo', exact=True).click()
            send('Olá')
            expect(overview).to_have_count(0)
            expect(page.get_by_test_id('investigation-card')).to_have_count(0)
        end_session(page)
        expect(page.get_by_role('button', name='Li e concordo', exact=True)).to_be_visible(timeout=15000)
        expect(page.get_by_test_id('session-ended-notice')).to_contain_text('A sessão anterior foi encerrada.')
        page.get_by_role('button', name='Li e concordo', exact=True).click()
        send('Olá')
        expect(overview).to_have_count(0)
        expect(page.get_by_test_id('investigation-card')).to_have_count(0)
        assert not errors, errors
        browser.close()
    print(f'INVESTIGAÇÃO PASS: {len(results)} resultados reais, reabertura, filtros preservados, destaque compatível, recorte/período incompatíveis, conversa ancorada, exportação, responsividade e encerramento. Volume, distância, falha de rede, limite de referências e perda de sessão exercitados no catálogo sintético. Base real={real}', flush=True)


if __name__ == '__main__':
    main()
