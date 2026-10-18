import {readFileSync} from 'node:fs';
import {test} from 'node:test';
import assert from 'node:assert/strict';
import ts from 'typescript';
async function source(name) {
  const code = ts.transpileModule(readFileSync(new URL('../src/' + name + '.ts', import.meta.url), 'utf8'),
    {compilerOptions: {module: ts.ModuleKind.ESNext, target: ts.ScriptTarget.ES2022}}).outputText;
  return import('data:text/javascript;base64,' + Buffer.from(code).toString('base64'));
}
const {compactPeriods, describePeriods, periodRange} = await source('periods');
// Ordem do arquivo da base Brasil: não cronológica.
const all = ['201401', '201406', '201501', '201506', '201606', '201701', '201601', '202406', '202401'];

test('resumo de períodos em ordem cronológica, por intervalo e com lacunas nomeadas', () => {
  assert.equal(describePeriods(['202401'], all), 'janeiro de 2024');
  assert.equal(describePeriods(all, all), 'todas as 9 competências, de janeiro de 2014 a junho de 2024');
  assert.equal(describePeriods(['201506', '201401', '201501', '201406'], all), '4 competências, de janeiro de 2014 a junho de 2015');
  assert.equal(describePeriods(all.filter(item => !['201401', '201506'].includes(item)), all),
    '7 competências, de junho de 2014 a junho de 2024, exceto junho de 2015');
  assert.equal(describePeriods(['201401', '202406'], all), '2 competências, de janeiro de 2014 a junho de 2024 (7 competências do intervalo não incluídas)');
  assert.equal(describePeriods([], all), 'nenhum período selecionado');
});

test('competências de um resultado: até três por extenso, acima disso quantidade e extremos', () => {
  const format = value => value.slice(4) + '/' + value.slice(0, 4);
  assert.equal(compactPeriods(['202406', '202401'], format), '01/2024, 06/2024');
  assert.equal(compactPeriods(all, format), '9 competências, de 01/2014 a 06/2024');
});

test('intervalo de competências é inclusivo e independe da ordem de início e fim', () => {
  assert.deepEqual(periodRange(all, '201401', '201506'), ['201401', '201406', '201501', '201506']);
  assert.deepEqual(periodRange(all, '201506', '201401'), ['201401', '201406', '201501', '201506']);
  assert.deepEqual(periodRange(all, '209901', '201401'), []);
});
