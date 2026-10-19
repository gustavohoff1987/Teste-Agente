import {readFileSync} from 'node:fs';
import {test} from 'node:test';
import assert from 'node:assert/strict';
import ts from 'typescript';
async function source(name) {
  const code = ts.transpileModule(readFileSync(new URL('../src/' + name + '.ts', import.meta.url), 'utf8'),
    {compilerOptions: {module: ts.ModuleKind.ESNext, target: ts.ScriptTarget.ES2022}}).outputText;
  return import('data:text/javascript;base64,' + Buffer.from(code).toString('base64'));
}
const {addsMunicipalities, describeScope} = await source('territorialScope');

test('caixa da abrangência territorial: total nacional, todos os municípios ou os marcados', () => {
  assert.equal(describeScope(true, ['MANAUS (AM)']), 'Brasil (total nacional)');
  assert.equal(describeScope(false, []), 'Todos os municípios');
  assert.equal(describeScope(false, ['MANAUS (AM)']), 'MANAUS (AM)');
  assert.equal(describeScope(false, ['MANAUS (AM)', 'TEFE (AM)']), 'MANAUS (AM) e TEFE (AM)');
  assert.equal(describeScope(false, ['MANAUS (AM)', 'TEFE (AM)', 'PARINTINS (AM)', 'FORA (SP)']),
    '4 municípios: MANAUS (AM), TEFE (AM) e mais 2');
});

test('no total nacional, só marcar municípios troca o recorte; desmarcar e limpar não', () => {
  assert.equal(addsMunicipalities(['code:1'], []), true);
  assert.equal(addsMunicipalities(['code:1', 'code:2'], ['code:1']), true);
  assert.equal(addsMunicipalities(['code:1'], ['code:1', 'code:2']), false);
  assert.equal(addsMunicipalities([], ['code:1']), false);
  assert.equal(addsMunicipalities([], []), false);
});
