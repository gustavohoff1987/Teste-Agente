import {existsSync, readFileSync} from 'node:fs';
import {test} from 'node:test';
import assert from 'node:assert/strict';
import ts from 'typescript';

// As fichas metodológicas em PDF (comando de ajustes pré-publicação, AJ-03, 18/11/2026): o endereço de cada ficha, na base da página
// (ADT_BASE_DA_PAGINA), com a seção pelo destino nomeado do PDF; os dois arquivos na pasta dos arquivos estáticos da interface (o
// build os copia como estão); e os links das duas ferramentas, numa nova aba. A validade dos PDFs, o título, o idioma, as tags, o
// sumário, os destinos das seções e a impressão digital da fonte ficam em backend/tests/test_fichas_metodologicas.py.
async function source(name) {
  const code = ts.transpileModule(readFileSync(new URL('../src/' + name + '.ts', import.meta.url), 'utf8'),
    {compilerOptions: {module: ts.ModuleKind.ESNext, target: ts.ScriptTarget.ES2022}}).outputText;
  return import('data:text/javascript;base64,' + Buffer.from(code).toString('base64'));
}
const F = await source('fichas');
const ler = caminho => readFileSync(new URL('../src/' + caminho, import.meta.url), 'utf8');

test('o endereço de cada ficha respeita a base da página e leva à seção pelo destino nomeado', () => {
  assert.deepEqual(F.ARQUIVOS_DAS_FICHAS, {detector: 'fichas/ficha-detector.pdf', simulador: 'fichas/ficha-simulador.pdf'});
  assert.equal(F.linkDaFicha('/', 'detector'), '/fichas/ficha-detector.pdf');
  assert.equal(F.linkDaFicha('/Teste-Agente/', 'simulador', 'faixa'), '/Teste-Agente/fichas/ficha-simulador.pdf#nameddest=faixa');
  assert.equal(F.linkDaFicha('', 'detector', 'o-que-e'), '/fichas/ficha-detector.pdf#nameddest=o-que-e');
  assert.equal(F.linkDaFicha('/sub', 'detector', 'niveis'), '/sub/fichas/ficha-detector.pdf#nameddest=niveis');
  // As seções que a página abre: ids simples (letras minúsculas e hífen), que viram os destinos nomeados do PDF.
  assert.deepEqual(F.SECOES_DAS_FICHAS, {detector: {ferramenta: 'o-que-e', sinal: 'sinais', alerta: 'niveis', porQue: 'sinais', ultimo: 'dados'},
    simulador: {ferramenta: 'o-que-e', forma: 'forma-escolhida', faixa: 'faixa'}});
  for (const secoes of Object.values(F.SECOES_DAS_FICHAS)) for (const id of Object.values(secoes)) assert.match(id, /^[a-z][a-z-]*$/, id);
});

test('os dois PDFs saem com os arquivos estáticos da interface, e as duas ferramentas têm o link visível, numa nova aba', () => {
  for (const arquivo of Object.values(F.ARQUIVOS_DAS_FICHAS)) {
    const caminho = new URL('../public/' + arquivo, import.meta.url);
    assert.ok(existsSync(caminho), arquivo);
    assert.equal(readFileSync(caminho).subarray(0, 5).toString('latin1'), '%PDF-', arquivo + ' é um PDF');
  }
  for (const [componente, ferramenta] of [['DetectorDeSinais.tsx', 'detector'], ['SimuladorDeCenarios.tsx', 'simulador']]) {
    const tela = ler(componente);
    assert.ok(tela.includes('const BASE = import.meta.env.BASE_URL || "/";'), componente + ': a base da página');
    assert.ok(tela.includes('<a data-testid="' + ferramenta + '-ficha" className="analise-botao-secundario" href={linkDaFicha(BASE, "' + ferramenta +
      '")} target="_blank" rel="noopener">'), componente + ': o link da ficha');
    assert.ok(tela.includes('Ficha metodológica (PDF)<span className="sr-only"> (abre numa nova aba)</span></a>'), componente + ': o nome do link');
  }
});
