import { readFileSync } from 'node:fs';
import { test } from 'node:test';
import assert from 'node:assert/strict';
import ts from 'typescript';
const code = ts.transpileModule(readFileSync(new URL('../src/diagnostics.ts', import.meta.url), 'utf8'),
  {compilerOptions: {module: ts.ModuleKind.ESNext, target: ts.ScriptTarget.ES2022}}).outputText;
const { analyticalRequest, attachResult, presentationIntent, diagnosticLabel } = await import('data:text/javascript;base64,' + Buffer.from(code).toString('base64'));

test('independentes, composição ordenada e reutilização preservam identidade sem alterar grupos anteriores', () => {
  const initial = [{id: 1, resultIds: ['a']}];
  const independent = attachResult(initial, 2, 'b');
  const composed = attachResult(independent, 1, 'c');
  assert.deepEqual(initial, [{id: 1, resultIds: ['a']}]);
  assert.deepEqual(composed, [{id: 1, resultIds: ['a', 'c']}, {id: 2, resultIds: ['b']}]);
  assert.equal(attachResult(composed, 1, 'a'), composed);
  assert.deepEqual(attachResult(composed, 2, 'a')[1].resultIds, ['b', 'a']);
  assert.match(diagnosticLabel(composed[0]), /Diagnóstico 1 · 2 componentes/);
  assert.equal(diagnosticLabel(composed[1]), 'Análise independente 2');
});
test('comando de organização preserva integralmente recortes e termos analíticos para validação', () => {
  const request = 'densidade médica dos municípios do Amazonas em janeiro de 2024.';
  assert.equal(analyticalRequest('Faça uma análise independente da ' + request), request);
  assert.equal(analyticalRequest('Acrescente ao diagnóstico atual a ' + request), 'a ' + request);
  assert.equal(analyticalRequest('Acrescente a densidade de Manaus ao diagnóstico atual.'), 'Acrescente a densidade de Manaus.');
  for (const unchanged of ['Não acrescente ao diagnóstico atual a densidade', 'Explique análise independente',
    'Análise independente ou acrescente ao diagnóstico', 'Compare Manaus e Território Inexistente']) {
    assert.equal(analyticalRequest(unchanged), unchanged);
  }
  assert.equal(analyticalRequest('Faça uma análise independente da densidade de Território Inexistente em janeiro de 2099.'),
    'densidade de Território Inexistente em janeiro de 2099.');
});
test('intenção de apresentação exige pedido explícito e não interpreta capacidade ou valores', () => {
  assert.equal(presentationIntent('Faça uma análise independente da densidade'), 'independent');
  assert.equal(presentationIntent('Acrescente a distribuição ao diagnóstico atual'), 'append');
  assert.equal(presentationIntent('Compare os selecionados'), null);
  assert.equal(presentationIntent('Análise independente ou acrescente ao diagnóstico'), null);
  assert.equal(presentationIntent('O que significa esse diagnóstico?'), null);
  assert.equal(presentationIntent('Não acrescente ao diagnóstico'), null);
  assert.equal(presentationIntent('Explique análise independente'), null);
  assert.equal(presentationIntent('Pode fazer uma análise independente?'), 'independent');
});
