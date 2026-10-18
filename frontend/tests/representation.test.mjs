import {readFileSync} from 'node:fs';
import {test} from 'node:test';
import assert from 'node:assert/strict';
import ts from 'typescript';
async function source(name) {
  const code = ts.transpileModule(readFileSync(new URL('../src/' + name + '.ts', import.meta.url), 'utf8'),
    {compilerOptions: {module: ts.ModuleKind.ESNext, target: ts.ScriptTarget.ES2022}}).outputText;
  return import('data:text/javascript;base64,' + Buffer.from(code).toString('base64'));
}
const {niceDomain, tableColumns} = await source('representation');

test('escala vertical em números redondos ao redor dos valores observados', () => {
  assert.deepEqual(niceDomain([1.700594, 1.683583, 1.95, 1.6]), [1.6, 2]);
  assert.deepEqual(niceDomain([0, 10]), [0, 10]);
  assert.deepEqual(niceDomain([5, 5]), [4.5, 5.5]);
  assert.deepEqual(niceDomain([-2, 3]), [-2, 4]);
  assert.deepEqual(niceDomain([0.2, 9.8]), [0, 10]);  // valores positivos nunca ganham eixo negativo
  assert.deepEqual(niceDomain([]), [0, 1]);
});

test('competências aparecem como mês/ano na tabela, sem alterar as demais colunas', () => {
  const [territory, period, initial] = tableColumns(['Território', 'Período', 'Período inicial']);
  assert.equal(territory.display, undefined);
  assert.equal(period.display('202406'), '06/2024');
  assert.equal(initial.display('201401'), '01/2014');
  assert.equal(period.display('Período declarado'), 'Período declarado');
});
