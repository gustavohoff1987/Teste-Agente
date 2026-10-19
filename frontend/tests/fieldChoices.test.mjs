import {readFileSync} from 'node:fs';
import {test} from 'node:test';
import assert from 'node:assert/strict';
import ts from 'typescript';

const code = ts.transpileModule(readFileSync(new URL('../src/fieldChoices.ts', import.meta.url), 'utf8'),
  {compilerOptions: {module: ts.ModuleKind.ESNext, target: ts.ScriptTarget.ES2022}}).outputText;
const {fieldOptions, periodValue, SINGLE_PERIOD, SINGLE_PERIOD_LABEL} = await import('data:text/javascript;base64,' + Buffer.from(code).toString('base64'));

const columns = ['municipio', 'cod_ibge', 'ano', 'quantidade'];

test('sugestões ficam no topo com "(sugerida)", sem serem escolhidas', () => {
  const options = fieldOptions(columns, {territory_id: ['cod_ibge']}, 'territory_id');
  assert.deepEqual(options.map(o => o.value), ['cod_ibge', 'municipio', 'ano', 'quantidade']);
  assert.equal(options[0].label, 'cod_ibge (sugerida)');
  assert.ok(options.every(o => o.value !== ''), 'sem opção vazia: o seletor mostra "Escolher campo" até a escolha');
});

test('coluna já escolhida perde o rótulo de sugestão; sugestões fora da base são ignoradas', () => {
  const options = fieldOptions(columns, {territory_id: ['cod_ibge', 'nao_existe']}, 'territory_id', {current: 'cod_ibge'});
  assert.equal(options[0].label, 'cod_ibge');
  assert.ok(!options.some(o => o.value === 'nao_existe'));
});

test('código territorial opcional: primeira opção "Sem código"', () => {
  const options = fieldOptions(columns, {}, 'territory_id', {optional: true});
  assert.deepEqual(options[0], {value: '', label: 'Sem código'});
});

test('período tem a opção "A base tem um único período"', () => {
  const options = fieldOptions(columns, {period: ['ano']}, 'period', {singlePeriod: true});
  assert.deepEqual(options.at(-1), {value: SINGLE_PERIOD, label: SINGLE_PERIOD_LABEL});
  assert.equal(SINGLE_PERIOD_LABEL, 'A base tem um único período');
  assert.equal(periodValue('', true), SINGLE_PERIOD);
  assert.equal(periodValue('ano', true), 'ano');
  assert.equal(periodValue(undefined, false), '');
  assert.ok(!fieldOptions(columns, {}, 'count', {singlePeriod: true}).some(o => o.value === SINGLE_PERIOD));
});
