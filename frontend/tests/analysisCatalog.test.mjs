import {readFileSync} from 'node:fs';
import {test} from 'node:test';
import assert from 'node:assert/strict';
import ts from 'typescript';
async function source(name) {
  const code = ts.transpileModule(readFileSync(new URL('../src/' + name + '.ts', import.meta.url), 'utf8'),
    {compilerOptions: {module: ts.ModuleKind.ESNext, target: ts.ScriptTarget.ES2022}}).outputText;
  return import('data:text/javascript;base64,' + Buffer.from(code).toString('base64'));
}
const {ANALYSIS_LABELS, ownIndicator} = await source('analysisCatalog');

test('caixa Indicador: o indicador próprio de cada análise sem escolha entre quantidade e densidade', () => {
  assert.equal(ownIndicator('density'), 'Densidade por 1.000 habitantes');
  assert.equal(ownIndicator('counts'), 'Quantidade');
  assert.equal(ownIndicator('aggregate'), 'Quantidade e densidade por 1.000 habitantes');
  assert.equal(ownIndicator('ranking'), 'Densidade por 1.000 habitantes');
  assert.equal(ownIndicator('spatial'), 'Distância geodésica (km)');
  assert.equal(ownIndicator('rotation'), 'Permanência e rotatividade da coorte (%)');
  assert.equal(ownIndicator('nearest'), 'Distância à referência mais próxima (km)');
  // Análises com escolha entre quantidade e densidade não têm indicador próprio.
  for (const operation of ['distribution', 'comparisons', 'temporal', 'report']) assert.equal(ownIndicator(operation), '');
  // Todas as demais análises do catálogo têm um indicador na caixa.
  for (const operation of Object.keys(ANALYSIS_LABELS))
    if (!['distribution', 'comparisons', 'temporal', 'report'].includes(operation)) assert.notEqual(ownIndicator(operation), '');
});

test('caixa Indicador dos critérios combinados: os atributos usados ou, sem eles, a indicação dos critérios', () => {
  assert.equal(ownIndicator('criteria'), 'Definido nos critérios');
  assert.equal(ownIndicator('criteria', ['Densidade']), 'Densidade');
  assert.equal(ownIndicator('criteria', ['Densidade', 'População']), 'Densidade e População');
  assert.equal(ownIndicator('criteria', ['Densidade', 'Quantidade', 'Distância à referência mais próxima']),
    'Densidade, Quantidade e Distância à referência mais próxima');
});
