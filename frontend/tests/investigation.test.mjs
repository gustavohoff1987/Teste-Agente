import { readFileSync } from 'node:fs';
import { test } from 'node:test';
import assert from 'node:assert/strict';
import ts from 'typescript';

// Executa o módulo real, sem reimplementar a política e sem dependência de um runner adicional.
const code = ts.transpileModule(readFileSync(new URL('../src/investigation.ts', import.meta.url), 'utf8'),
  {compilerOptions: {module: ts.ModuleKind.ESNext, target: ts.ScriptTarget.ES2022}}).outputText;
const {identity, selectionCompatibility} = await import('data:text/javascript;base64,' + Buffer.from(code).toString('base64'));
const entry = () => ({sourceKey: 'brazil-v1-municipal', request: 'Densidade', invalidReason: '', result: {
  result_id: 'one', title: 'Densidade', rows: [{Quantidade: 10}], metadata: {
    validity: 'VALIDO', data_sha256: 'hash', source: {label: 'Brasil', version: 'v1', scope: 'municipal'},
    operation: 'density', method_version: 'deterministic-0.4', mapping: {territory: 'nome', territory_id: 'codigo'},
    periods: ['202406'], categories: ['MEDICINA'], universe: {classification_scope: 'Seleção explícita', members: [{id: 'code:1', label: 'Um'}, {id: 'code:2', label: 'Dois'}]},
    options: {count_unit: 'pessoas', population_denominator_confirmed: true}, indicator: 'density',
    representacao: {versao: 1, vinculo: {coluna: 'Território', chave: 'rotulo'}, indicadores: [{rotulo: 'Densidade', unidade: 'por 1.000 habitantes'}]},
    evaluability: {status: 'AVALIAVEL'},
  }
}});

test('coordena somente identidade territorial; dimensões continuam distintas e imutáveis', () => {
  const a = entry(), b = entry(); b.result.metadata.operation = 'distribution'; b.result.metadata.options.quantile_count = 5;
  const before = JSON.stringify([a,b]);
  const check = selectionCompatibility(a,b);
  assert.equal(check.allowed, true);
  assert.deepEqual(check.differences, ['Operações distintas', 'Parâmetros próprios de cada execução']);
  assert.equal(JSON.stringify([a,b]), before);
  assert.equal(identity(a).indicators[0], 'Densidade (por 1.000 habitantes)');
});

for (const [label, change] of [
  ['outra fonte', b => b.sourceKey = 'outra'],
  ['dados alterados', b => b.result.metadata.data_sha256 = 'alterado'],
  ['versão', b => b.result.metadata.source.version = 'v2'],
  ['escopo da fonte', b => b.result.metadata.source.scope = 'national'],
  ['período', b => b.result.metadata.periods = ['202405']],
  ['categoria', b => b.result.metadata.categories = ['OUTRA']],
  ['método', b => b.result.metadata.method_version = 'outro'],
  ['campos', b => b.result.metadata.mapping.territory_id = 'outro'],
  ['unidade', b => b.result.metadata.options.count_unit = 'vinculos'],
  ['sobreposição', b => b.result.metadata.options.no_overlap_confirmed = true],
  ['duplicatas', b => b.result.metadata.options.duplicate_policy = 'remove_exact'],
  ['subconjunto', b => b.result.metadata.universe.members.pop()],
  ['identificador ambíguo', b => b.result.metadata.universe.members[1].id = 'code:1'],
  ['resultado invalidado', b => b.invalidReason = 'Dados alterados'],
  ['validade ausente', b => delete b.result.metadata.validity],
  ['identidade ausente', b => delete b.result.metadata.data_sha256],
  ['contrato visual ausente', b => delete b.result.metadata.representacao],
  ['agregado', b => b.result.metadata.operation = 'aggregate'],
  ['série temporal', b => b.result.metadata.operation = 'temporal'],
  ['coorte', b => b.result.metadata.operation = 'rotation'],
]) test('bloqueia coordenação por ' + label, () => {
  const a = entry(), b = entry(); change(b);
  const check = selectionCompatibility(a,b);
  assert.equal(check.allowed, false); assert.ok(check.reasons.length);
});

test('nomes semelhantes não substituem identidade', () => {
  const a = entry(), b = entry(); b.result.metadata.universe.members[0].id = 'code:outra';
  assert.equal(selectionCompatibility(a,b).allowed, false);
});
test('ordem de membros e propriedades não altera identidade', () => {
  const a = entry(), b = entry(); b.result.metadata.universe.members.reverse();
  b.result.metadata.mapping = {territory_id: 'codigo', territory: 'nome'};
  assert.equal(selectionCompatibility(a,b).allowed, true);
});
test('camada geográfica não é intercambiável', () => {
  const a = entry(), b = entry(); a.result.metadata.complemento_geografico = {sha256: '1'}; b.result.metadata.complemento_geografico = {sha256: '2'};
  assert.equal(selectionCompatibility(a,b).allowed, false);
});
