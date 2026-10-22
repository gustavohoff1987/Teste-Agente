import {readFileSync} from 'node:fs';
import {test} from 'node:test';
import assert from 'node:assert/strict';
import ts from 'typescript';
async function source(name, ajustar = code => code) {
  const code = ts.transpileModule(readFileSync(new URL('../src/' + name + '.ts', import.meta.url), 'utf8'),
    {compilerOptions: {module: ts.ModuleKind.ESNext, target: ts.ScriptTarget.ES2022}}).outputText;
  return import('data:text/javascript;base64,' + Buffer.from(ajustar(code)).toString('base64'));
}
// Área de análise da página única (22/10/2026): modelo puro (painelModel.ts) e a normalização da resposta do motor no cliente
// (painelApi.ts, com a sessão substituída por um esboço: os testes não fazem pedidos).
const M = await source('painelModel');
const A = await source('painelApi', code => code.replace(/import\s*\{[^}]*\}\s*from\s*["']\.\/conversationSession["'];?/,
  'const contextRevision = () => 0; const fetch = globalThis.fetch;'));

// Itens no formato do motor (backend/painel.py): inicial e variacao_percentual sempre com as três chaves, avaliavel com
// densidade, distancia e variacao (null quando não pedidas), motivos em texto terminado pelo código e referencia booleana.
const VAZIO = {populacao: null, quantidade: null, densidade: null};
const municipio = (id, rotulo, valores = {}) => ({id, tipo: 'municipio', rotulo, uf: rotulo.slice(-3, -1), populacao: 1000, quantidade: 10,
  densidade: 10, distancia_km: null, inicial: {...VAZIO}, variacao_percentual: {...VAZIO},
  avaliavel: {densidade: true, distancia: true, variacao: true}, motivos: [], referencia: false, ...valores});
const SEM_REGISTRO = 'Sem registro em junho de 2024 na categoria MEDICINA: valores não avaliáveis, nunca zero (SEM_REGISTRO_OBSERVADO)';
const BASE_ZERO = 'Variação percentual da quantidade e da densidade não avaliável: valor inicial zero (BASE_ZERO)';
const SEM_COORDENADA = 'Distância não avaliável em junho de 2024: coordenadas ausentes (SEM_INFORMACAO_ESPACIAL)';
const SEM_INICIAL = 'Variação não avaliável: sem registro na competência inicial, junho de 2023 (SEM_REGISTRO_OBSERVADO)';
const PARCIAL = 'Agregado parcial em junho de 2024: 1 de 2 municípios com registro; fora: NOVO AIRAO (AM); o valor não representa o ' +
  'conjunto completo (AGREGADO_PARCIAL)';
const ITENS = [
  municipio('code:130260', 'MANAUS (AM)', {populacao: 1000, quantidade: 15, densidade: 15, distancia_km: 0, referencia: true,
    inicial: {populacao: 1000, quantidade: 12, densidade: 12}, variacao_percentual: {populacao: 0, quantidade: 25, densidade: 25}}),
  municipio('code:130420', 'TEFE (AM)', {populacao: 2000, quantidade: 10, densidade: 5, distancia_km: 523.14,
    inicial: {populacao: 2000, quantidade: 7, densidade: 3.5}, variacao_percentual: {populacao: 0, quantidade: 42.857142857142854, densidade: 42.857142857142854}}),
  municipio('code:130340', 'PARINTINS (AM)', {populacao: 4000, quantidade: 12, densidade: 3, distancia_km: 369.5,
    inicial: {populacao: 4000, quantidade: 0, densidade: 0}, variacao_percentual: {populacao: 0, quantidade: null, densidade: null},
    avaliavel: {densidade: true, distancia: true, variacao: false}, motivos: [BASE_ZERO]}),
  municipio('code:350010', 'FORA (SP)', {populacao: 9000, quantidade: 105, densidade: 11.666666666666666, distancia_km: null,
    inicial: {populacao: 9000, quantidade: 102, densidade: 11.333333333333334}, variacao_percentual: {populacao: 0, quantidade: 2.941176470588235, densidade: 2.941176470588235},
    avaliavel: {densidade: true, distancia: false, variacao: true}, motivos: [SEM_COORDENADA]}),
  municipio('code:130185', 'IRANDUBA (AM)', {populacao: null, quantidade: null, densidade: null,
    avaliavel: {densidade: false, distancia: null, variacao: false}, motivos: [SEM_REGISTRO]}),
  {id: 'c1', tipo: 'conjunto', rotulo: 'Interior', uf: null, membros: ['code:130420', 'code:130340'], populacao: 6000, quantidade: 22,
    densidade: 3.6666666666666665, contagem: 'SOMA_DOS_COMPONENTES', distancia_km: 369.5, distancia_km_max: 523.14,
    inicial: {populacao: 6000, quantidade: 7, densidade: 1.1666666666666667},
    variacao_percentual: {populacao: 0, quantidade: 214.28571428571428, densidade: 214.28571428571428},
    avaliavel: {densidade: true, distancia: true, variacao: true}, motivos: [], referencia: false},
];
// Domínios do motor: os dos indicadores incluem os valores iniciais (o zero inicial de PARINTINS); a distância, o membro mais distante.
const DOMINIOS = {densidade: [0, 15], quantidade: [0, 105], populacao: [1000, 9000], distancia_km: [0, 523.14],
  variacao_densidade: [2.94, 214.29], variacao_quantidade: [2.94, 214.29], variacao_populacao: [0, 0]};
const UNICA = () => ({cor: M.COR_BOLHA, vazada: false, apagada: false});
const BR = M.ROTULOS_BRASIL;
const DISTRITOS = {unidade: {singular: 'distrito', plural: 'distritos'}, grupo: {singular: 'província', plural: 'províncias'}};
const GRUPOS = [{id: '13', nome: 'Amazonas', sigla: 'AM', rotuloGrupo: 'Municípios do Amazonas', unidades: 62},
  {id: '35', nome: 'São Paulo', sigla: 'SP', rotuloGrupo: 'Municípios de São Paulo', unidades: 645}];
const grafico = (extra = {}) => M.montarGrafico({itens: ITENS.slice(0, 4), dominios: DOMINIOS, indicador: 'densidade', escala: 'linear',
  distancia: false, cometa: false, vista: 'final', largura: 800, rotuloDistancia: '', pintura: UNICA, ...extra});
const definicao = (extra = {}) => ({...M.definicaoInicial({tipo: 'brasil', periodos: ['202306', '202406'], categoria: 'MEDICINA', temGrupos: true}), ...extra});

test('variação percentual do motor em pt-BR: sinal, duas casas e nunca zero aparente (RQ-REP-05)', () => {
  assert.equal(M.formatarVariacao(12.4), '+12,40%');
  assert.equal(M.formatarVariacao(-3), '−3,00%');
  assert.equal(M.formatarVariacao(0), '0,00%');
  assert.equal(M.formatarVariacao(42.857142857142854), '+42,86%');
  assert.equal(M.formatarVariacao(1.235), '+1,24%');
  assert.equal(M.formatarVariacao(-1.235), '−1,24%');
  assert.equal(M.formatarVariacao(0.004), '+0,004%');
  assert.equal(M.formatarVariacao(12345.5), '+12.345,50%');
  assert.equal(M.formatarVariacao(null), 'Não avaliável');
  assert.equal(M.formatarVariacao(undefined), 'Não avaliável');
  assert.equal(M.direcaoDaVariacao(3), 'aumento');
  assert.equal(M.direcaoDaVariacao(-3), 'redução');
  assert.equal(M.direcaoDaVariacao(0), 'sem mudança');
});

test('números com unidade; casas aumentadas quando o valor pareceria igual ao limite da régua; competências por extenso', () => {
  assert.equal(M.formatarNumero(4730, true), '4.730');
  assert.equal(M.formatarNumero(-3, true), '−3');
  assert.equal(M.formatarNumero(0.70584), '0,71');
  assert.equal(M.formatarNumero(1.2041, false, [1.2]), '1,204');
  assert.equal(M.formatarNumero(1.2, false, [1.2]), '1,20');
  assert.equal(M.formatarIndicador(0.70584, 'densidade'), '0,71 por 1.000 habitantes');
  assert.equal(M.formatarIndicador(52, 'quantidade'), '52 profissionais');
  assert.equal(M.formatarIndicador(null, 'densidade'), 'Não avaliável');
  assert.equal(M.formatarPercentual(72.5), '72,50%');
  assert.equal(M.formatarPercentual(null), 'Não avaliável');
  assert.equal(M.exibirCompetencia('202406'), '06/2024');
  assert.equal(M.competenciaPorExtenso('202406'), 'junho de 2024');
  assert.equal(M.competenciaPorExtenso('2024'), '2024');
  assert.equal(M.compacto(2000000), '2 mi');
  assert.equal(M.compacto(1500), '1,5 mil');
  assert.deepEqual(M.lerLimites('0; 1,5; 2'), [0, 1.5, 2]);
  assert.deepEqual(M.lerLimites('300 0 100 100'), [0, 100, 300]);
  assert.equal(M.escreverLimites([0, 1.5]), '0; 1,5');
});

test('tamanho = população: área proporcional (raiz quadrada), mínimo visível e legenda de três referências', () => {
  assert.equal(M.raioDaPopulacao(1600, 1600, 30), 30);
  assert.equal(M.raioDaPopulacao(400, 1600, 30), 15);  // um quarto da população, metade do raio
  assert.equal(M.raioDaPopulacao(1, 1600, 30), M.RAIO_MINIMO);
  assert.equal(M.raioDaPopulacao(null, 1600, 30), M.RAIO_MINIMO);
  const legenda = M.legendaDeTamanhos(2279686, 30);
  assert.deepEqual(legenda.map(item => item.valor), [2000000, 500000, 50000]);
  assert.deepEqual(legenda.map(item => item.texto), ['2 mi hab.', '500 mil hab.', '50 mil hab.']);
  assert.ok(Math.abs(legenda[0].raio - 30 * Math.sqrt(2000000 / 2279686)) < 1e-9);
  assert.ok(legenda[0].raio > legenda[1].raio && legenda[1].raio > legenda[2].raio);
  assert.deepEqual(M.legendaDeTamanhos(9000, 30).map(item => item.valor), [5000, 1000, 200]);
  assert.deepEqual(M.legendaDeTamanhos(0, 30), []);
});

test('não avaliáveis à parte, com o motivo do motor, na ordem do código territorial; variação vazia continua bolha', () => {
  const {plotaveis, fora} = M.separarItens([...ITENS].reverse(), 'densidade', {distancia: true, variacao: true});
  assert.deepEqual(plotaveis.map(item => item.id), ['code:130260', 'code:130340', 'code:130420', 'c1']);
  assert.deepEqual(fora.map(item => [item.id, item.aspecto]), [['code:130185', 'indicador'], ['code:130340', 'variacao'], ['code:350010', 'distancia']]);
  assert.equal(fora[0].motivo, SEM_REGISTRO);
  assert.equal(fora[1].motivo, BASE_ZERO);
  assert.equal(fora[2].motivo, SEM_COORDENADA);
  const semDistancia = M.separarItens(ITENS, 'densidade', {});
  assert.ok(semDistancia.plotaveis.some(item => item.id === 'code:350010'));
  assert.deepEqual(semDistancia.fora.map(item => item.id), ['code:130185']);
});

test('tendência, condições e rotatividade não avaliáveis: listados à parte com o motivo do motor; a bolha da tendência fica', () => {
  const insuficiente = {classe: null, rotulo: 'Não avaliável: série insuficiente', motivo: 'Não avaliável: série insuficiente', familia: null,
    avaliavel: false, observacoes: [], velocidades: []};
  const itens = [municipio('code:1', 'A (AM)', {tendencia: insuficiente,
      condicoes: {situacao: 'NAO_AVALIAVEL', porCondicao: [{texto: 'distância > 150 km', situacao: 'NAO_AVALIAVEL'}], motivo: null}}),
    municipio('code:2', 'B (AM)', {tendencia: {...insuficiente, classe: 'CRESCIMENTO', rotulo: 'Crescimento', motivo: null, familia: 'CRESCIMENTO', avaliavel: true}})];
  const {plotaveis, fora} = M.separarItens(itens, 'densidade', {tendencia: true, condicoes: true});
  assert.deepEqual(plotaveis.map(item => item.id), ['code:1', 'code:2']);
  assert.deepEqual(fora.map(item => [item.id, item.aspecto, item.motivo]), [['code:1', 'tendencia', 'Não avaliável: série insuficiente'],
    ['code:1', 'condicoes', 'distância > 150 km']]);
  const coortes = [municipio('code:3', 'C (AM)', {rotatividade: {coorteInicial: 120, permaneceram: 87, sairam: 33, permanencia: 72.5, saida: 27.5, avaliavel: true, motivo: null}}),
    municipio('code:4', 'D (AM)', {rotatividade: {coorteInicial: null, permaneceram: null, sairam: null, permanencia: null, saida: null, avaliavel: false,
      motivo: 'Não avaliável: sem registro observado em um dos períodos (SEM_REGISTRO_OBSERVADO)'}})];
  const rot = M.separarItens(coortes, 'densidade', {rotatividade: true});
  assert.deepEqual(rot.plotaveis.map(item => item.id), ['code:3']);
  assert.deepEqual(rot.fora.map(item => [item.id, item.aspecto]), [['code:4', 'rotatividade']]);
  assert.ok(rot.fora[0].motivo.endsWith('(SEM_REGISTRO_OBSERVADO)'));
});

test('motivos do motor classificados pelo começo do texto, nunca pela posição; agregado parcial é aviso', () => {
  assert.equal(M.aspectoDoMotivo(SEM_COORDENADA), 'distancia');
  assert.equal(M.aspectoDoMotivo(BASE_ZERO), 'variacao');
  assert.equal(M.aspectoDoMotivo(SEM_INICIAL), 'variacao');
  assert.equal(M.aspectoDoMotivo(SEM_REGISTRO), 'geral');
  const misto = municipio('code:130250', 'MANACAPURU (AM)', {motivos: [SEM_COORDENADA, SEM_INICIAL]});
  assert.deepEqual(M.motivosDe(misto, 'variacao'), [SEM_INICIAL]);
  assert.deepEqual(M.motivosDe(misto, 'distancia'), [SEM_COORDENADA]);
  assert.deepEqual(M.motivosDe(misto, 'indicador'), []);
  assert.deepEqual(M.motivosDe(misto), [SEM_COORDENADA, SEM_INICIAL]);
  assert.deepEqual(M.motivosDe(ITENS[4], 'distancia'), [SEM_REGISTRO]);
  const parcial = {...ITENS[5], motivos: [PARCIAL, 'Distância não avaliável em junho de 2024: sem coordenada válida em MANACAPURU (AM) ' +
    '(DEPENDENCIA_NAO_AVALIAVEL)']};
  assert.deepEqual(M.avisosDe(parcial), [PARCIAL]);
  assert.deepEqual(M.motivosDe(parcial, 'distancia'), [parcial.motivos[1]]);
  assert.deepEqual(M.motivosDe(parcial, 'indicador'), []);
  const dica = M.montarDica(parcial, {indicador: 'densidade', competencia: '202406', competenciaInicial: null, distancia: true,
    variacao: false, tendencia: false, nomes: new Map(), rotulos: BR});
  assert.ok(dica.notas.includes(PARCIAL));
  assert.equal(M.textoDaLimitacao('SOMA_COM_POSSIVEL_DUPLA_CONTAGEM'), 'Conjuntos: soma das contagens dos componentes, com possível dupla contagem.');
  assert.equal(M.textoDaLimitacao('CODIGO_NOVO'), 'Limitação registrada pelo motor: CODIGO_NOVO.');
});

test('régua: limites incluídos, só as unidades; conjuntos e referência sempre à vista; passos redondos', () => {
  const visiveis = corte => ITENS.filter(item => M.noCorte(item, 'densidade', corte)).map(item => item.id);
  assert.deepEqual(visiveis(null), ITENS.map(item => item.id));
  assert.deepEqual(visiveis({minimo: 3, maximo: 5}), ['code:130260', 'code:130420', 'code:130340', 'c1']);
  assert.deepEqual(visiveis({minimo: 3.5, maximo: 15}), ['code:130260', 'code:130420', 'code:350010', 'c1']);
  assert.equal(M.noCorte({...ITENS[1], id: 'uf:13', tipo: 'estado'}, 'densidade', {minimo: 6, maximo: 9}), false);  // estados também
  assert.equal(M.corteAtivo(null, [3, 15]), false);
  assert.equal(M.corteAtivo({minimo: 3, maximo: 15}, [3, 15]), false);
  assert.equal(M.corteAtivo({minimo: 4, maximo: 15}, [3, 15]), true);
  assert.equal(M.passoDaRegua([0, 2.07], false), 0.05);
  assert.equal(M.passoDaRegua([5, 4732], true), 50);
  assert.equal(M.ajustarValor(1.2345, [0, 2.07], 'linear', false), 1.25);
  assert.equal(M.ajustarValor(0.05, [0.1234, 2.0713], 'linear', false), 0.1234);
  assert.equal(M.ajustarValor(3, [0.1234, 2.0713], 'linear', false), 2.0713);
  assert.equal(M.ajustarValor(12.4, [3, 15], 'linear', true), 12);
  assert.equal(M.moverCursor(0.1234, 1, false, [0.1234, 2.0713], 'linear', false), 0.14);
  assert.equal(M.moverCursor(3, 1, false, [3, 15], 'linear', true), 4);
  assert.equal(M.moverCursor(3, 1, false, [3, 15], 'logaritmica', true), 4);
  assert.equal(M.moverCursor(15, 1, false, [3, 15], 'linear', true), 15);
  assert.equal(M.moverCursor(15, -1, true, [3, 15], 'linear', true), 5);
});

test('arranjo do eixo único: sem sobreposição, determinístico e independente da ordem de entrada', () => {
  const capsulas = Array.from({length: 40}, (_, i) => ({id: 'code:' + (100 + i), x0: 100 + (i % 7) * 3, x1: 100 + (i % 7) * 3, r: 4 + (i % 5)}));
  const a = M.arranjar(capsulas), b = M.arranjar([...capsulas].reverse());
  assert.deepEqual([...a.entries()].sort(), [...b.entries()].sort());
  for (let i = 0; i < capsulas.length; i++) for (let j = i + 1; j < capsulas.length; j++) {
    const p = capsulas[i], q = capsulas[j];
    assert.ok(Math.hypot(p.x0 - q.x0, a.get(p.id) - a.get(q.id)) >= p.r + q.r + 1.5 - 1e-6, p.id + ' x ' + q.id);
  }
  assert.equal(M.arranjar([{id: 'x', x0: 10, x1: 10, r: 5}]).get('x'), 0);
  const cometas = [{id: 'a', x0: 10, x1: 200, r: 6}, {id: 'b', x0: 150, x1: 60, r: 8}, {id: 'c', x0: 190, x1: 300, r: 5}];
  const y = M.arranjar(cometas);
  for (let i = 0; i < 3; i++) for (let j = i + 1; j < 3; j++) {
    const p = cometas[i], q = cometas[j];
    const lacuna = Math.max(0, Math.min(q.x0, q.x1) - Math.max(p.x0, p.x1), Math.min(p.x0, p.x1) - Math.max(q.x0, q.x1));
    assert.ok(Math.hypot(lacuna, y.get(p.id) - y.get(q.id)) >= p.r + q.r + 1.5 - 1e-6);
  }
});

test('modo leve: arranjo numa faixa limitada, determinístico, sem custo quadrático e preso à largura do gráfico', () => {
  assert.equal(M.LIMITE_LEVE, 400);
  const poucas = Array.from({length: 30}, (_, i) => ({id: 'code:' + (200 + i), x0: 100 + (i % 6) * 4, x1: 100 + (i % 6) * 4, r: 4 + (i % 3)}));
  const a = M.arranjarDenso(poucas, 120), b = M.arranjarDenso([...poucas].reverse(), 120);
  assert.deepEqual([...a.entries()].sort(), [...b.entries()].sort());
  for (let i = 0; i < poucas.length; i++) for (let j = i + 1; j < poucas.length; j++) {
    const p = poucas[i], q = poucas[j];
    assert.ok(Math.hypot(p.x0 - q.x0, a.get(p.id) - a.get(q.id)) >= p.r + q.r - 3, p.id + ' x ' + q.id);
  }
  assert.ok([...a.values()].every(y => Math.abs(y) <= 120 && Math.abs(y % 2) === 0));
  const muitas = Array.from({length: 5570}, (_, i) => ({id: 'code:' + (100000 + i), x0: 300 + (i % 250), x1: 300 + (i % 250) + (i % 7), r: 4 + (i % 4)}));
  const inicio = performance.now();
  const y = M.arranjarDenso(muitas, 150);
  assert.ok(performance.now() - inicio < 5000);
  assert.equal(y.size, muitas.length);
  assert.ok([...y.values()].every(valor => Math.abs(valor) <= 150));
  // No gráfico, o modo leve espalha as bolhas na horizontal dentro da largura, com o indicador no eixo vertical.
  const itens = Array.from({length: 600}, (_, i) => ({...ITENS[1], id: 'code:' + (300000 + i), densidade: (i % 50) / 10 + 0.1, populacao: 1000 + i}));
  const leve = M.montarGrafico({itens, dominios: {...DOMINIOS, densidade: [0.1, 5.1], populacao: [1000, 1600]}, indicador: 'densidade',
    escala: 'linear', distancia: false, cometa: false, vista: 'final', largura: 860, rotuloDistancia: '', pintura: UNICA, denso: true});
  assert.equal(leve.arranjo, 'leve');
  assert.equal(leve.eixoX, null);
  assert.equal(leve.bolhas.length, 600);
  assert.ok(leve.altura <= 14 + 520 + 12, String(leve.altura));
  assert.ok(leve.bolhas.every(b => b.x - b.r >= leve.esquerda - 1e-9 && b.x + b.r <= leve.largura - leve.direita + 1e-9));
});

test('eixo Y é o indicador; sem análise espacial, a posição horizontal é só arranjo, sem sobreposição; raio pela população', () => {
  const g = grafico();
  assert.equal(g.eixoX, null);
  assert.equal(g.eixoY.tipo, 'densidade');
  assert.equal(g.eixoY.rotulo, 'Densidade (profissionais por 1.000 habitantes)');
  assert.deepEqual(g.eixoY.dominio, [0, 15]);
  assert.deepEqual(g.eixoY.marcas.map(marca => marca.valor), [0, 5, 10, 15]);
  assert.equal(g.arranjo, 'exato');
  const y = id => g.bolhas.find(bolha => bolha.id === id).y;
  // Valor maior, mais acima (y menor).
  assert.ok(y('code:130260') < y('code:350010') && y('code:350010') < y('code:130420') && y('code:130420') < y('code:130340'));
  assert.equal(g.bolhas.find(bolha => bolha.id === 'code:350010').r, g.raioMax);
  assert.ok(g.bolhas.every(bolha => bolha.cor === M.COR_BOLHA && !bolha.rastro && bolha.visivel));
  for (const p of g.bolhas) for (const q of g.bolhas) if (p.id < q.id) assert.ok(Math.hypot(p.x - q.x, p.y - q.y) >= p.r + q.r);
  assert.ok(g.bolhas.every(b => b.x - b.r >= g.esquerda - 1e-9 && b.x + b.r <= g.largura - g.direita + 1e-9));
  const quantidade = grafico({indicador: 'quantidade'});
  assert.equal(quantidade.eixoY.tipo, 'quantidade');
  assert.deepEqual(quantidade.eixoY.dominio, [0, 125]);
});

test('sem escala logarítmica automática (Parte 13, L1994): a logarítmica só por escolha e só com valores positivos', () => {
  assert.equal(M.escalaPossivel([0.1, 1000], 'linear'), 'linear');
  assert.equal(M.escalaPossivel([0.1, 1000], 'logaritmica'), 'logaritmica');
  assert.equal(M.escalaPossivel([0, 3], 'logaritmica'), 'linear');
  const desiguais = Array.from({length: 600}, (_, i) => ({...ITENS[1], id: 'code:' + (400000 + i), densidade: i === 0 ? 50 : 0.1 + (i % 10) / 100}));
  const linear = M.montarGrafico({itens: desiguais, dominios: {densidade: [0.1, 50], populacao: [2000, 2000]}, indicador: 'densidade', escala: 'linear',
    distancia: false, cometa: false, vista: 'final', largura: 800, rotuloDistancia: '', pintura: UNICA, denso: true});
  assert.equal(linear.eixoY.escala, 'linear');
  const log = M.montarGrafico({itens: desiguais, dominios: {densidade: [0.1, 50], populacao: [2000, 2000]}, indicador: 'densidade', escala: 'logaritmica',
    distancia: false, cometa: false, vista: 'final', largura: 800, rotuloDistancia: '', pintura: UNICA, denso: true});
  assert.equal(log.eixoY.escala, 'logaritmica');
});

test('análise espacial: X = distância até a referência, Y = indicador; conjunto com a faixa do membro mais próximo ao mais distante', () => {
  const itens = M.separarItens(ITENS, 'densidade', {distancia: true}).plotaveis;
  const g = M.montarGrafico({itens, dominios: DOMINIOS, indicador: 'densidade', escala: 'linear', distancia: true, cometa: false,
    vista: 'final', largura: 800, rotuloDistancia: 'Distância até a referência (km)', pintura: UNICA});
  assert.equal(g.eixoX.tipo, 'distancia');
  assert.equal(g.eixoX.rotulo, 'Distância até a referência (km)');
  assert.equal(g.eixoY.tipo, 'densidade');
  assert.equal(g.arranjo, 'dados');
  const bolha = id => g.bolhas.find(item => item.id === id);
  assert.ok(bolha('code:130260').x < bolha('code:130340').x && bolha('code:130340').x < bolha('code:130420').x);
  assert.ok(bolha('code:130260').y < bolha('code:130420').y);  // densidade maior, mais acima
  assert.ok(bolha('code:130260').referencia);
  assert.ok(Math.abs(bolha('c1').x + bolha('c1').faixa.dx - bolha('code:130420').x) < 1e-9);
});

test('mudança entre duas competências: cometa vertical só com a variação do motor, cor divergente e vista da primeira competência', () => {
  const itens = M.separarItens(ITENS, 'densidade', {variacao: true}).plotaveis;
  const limite = M.limiteDaVariacao({dominios: DOMINIOS}, 'densidade', itens);
  assert.equal(limite, 214.29);
  const parametros = {camada: 'variacao', indicador: 'densidade', limiteVariacao: limite, totalGrupos: 0, totalFaixas: 0, primeiros: null};
  const pintura = item => M.pintar(item, parametros);
  const g = M.montarGrafico({itens, dominios: DOMINIOS, indicador: 'densidade', escala: 'linear', distancia: false, cometa: true,
    vista: 'final', largura: 800, rotuloDistancia: '', pintura});
  const bolha = id => g.bolhas.find(item => item.id === id);
  assert.equal(bolha('code:130260').rastro.dx, 0);  // eixo vertical: o rastro sobe ou desce
  assert.ok(bolha('code:130260').rastro.dy > 0);  // aumentou: veio de baixo
  assert.equal(bolha('code:130340').rastro, null);  // variação não avaliável (base zero): sem rastro, bolha vazada
  assert.equal(bolha('code:130340').vazada, true);
  assert.equal(bolha('code:130340').cor, '#ffffff');
  assert.notEqual(bolha('code:350010').cor, M.COR_NEUTRA);  // +2,94%: sinal visível
  const inicial = M.montarGrafico({itens, dominios: DOMINIOS, indicador: 'densidade', escala: 'linear', distancia: false, cometa: true,
    vista: 'inicial', largura: 800, rotuloDistancia: '', pintura});
  const antes = id => inicial.bolhas.find(item => item.id === id);
  assert.ok(Math.abs(antes('code:130260').y - (bolha('code:130260').y + bolha('code:130260').rastro.dy)) < 1e-9);
  assert.equal(antes('code:130260').x, bolha('code:130260').x);  // a faixa do cometa não muda entre as vistas
  assert.equal(antes('code:130340').visivel, false);
  assert.equal(M.corDaVariacao(0, 40), M.COR_NEUTRA);
  assert.equal(M.corDaVariacao(10, 40), M.RAMPA_AUMENTO[1]);
  assert.equal(M.corDaVariacao(-10, 40), M.RAMPA_REDUCAO[1]);
  assert.notEqual(M.corDaVariacao(2, 40), M.RAMPA_AUMENTO[0]);
  assert.equal(M.corDaVariacao(40, 40), M.RAMPA_AUMENTO[2]);
  assert.equal(M.corDaVariacao(-80, 40), M.RAMPA_REDUCAO[2]);
  assert.equal(M.caudaDoCometa(-100, 0, 10), '-100,0 0,-6 0,6');
  assert.equal(M.caudaDoCometa(0, 0.5, 10), '');
});

test('camadas de cor só traduzem o motor: classe de tendência pela família, grupos e faixas em rampa ordinal, condições e ordem', () => {
  const p = camada => ({camada, indicador: 'densidade', limiteVariacao: 0, totalGrupos: 4, totalFaixas: 3, primeiros: 2});
  const tendencia = (familia, classe, avaliavel = true) => municipio('code:9', 'X (AM)', {tendencia: {classe, rotulo: '', motivo: null, familia,
    avaliavel, observacoes: [], velocidades: []}});
  assert.equal(M.pintar(tendencia('DECLINIO', 'DECLINIO'), p('classes')).cor, '#eb6834');
  assert.equal(M.pintar(tendencia('CRESCIMENTO', 'CRESCIMENTO_ACELERADO'), p('classes')).cor, '#2a78d6');
  assert.equal(M.pintar(tendencia(null, 'SEM_CLASSIFICACAO'), p('classes')).cor, '#1baf7a');
  assert.deepEqual(M.pintar(tendencia(null, null, false), p('classes')), {cor: '#ffffff', vazada: true, apagada: false});
  assert.equal(M.pintar(municipio('code:9', 'X (AM)', {grupo: {indice: 2, rotulo: '2º quartil'}}), p('grupos')).cor, '#3987e5');
  assert.equal(M.pintar(municipio('code:9', 'X (AM)', {grupo: {indice: 7, rotulo: '7º decil'}}), {...p('grupos'), totalGrupos: 10}).cor, M.COR_BOLHA);
  assert.equal(M.pintar(municipio('code:9', 'X (AM)', {grupo: null}), p('grupos')).vazada, true);
  assert.equal(M.pintar(municipio('code:9', 'X (AM)', {faixa: {indice: 1, rotulo: '0 a 1'}}), p('faixas')).cor, '#86b6ef');
  assert.equal(M.pintar(municipio('code:9', 'X (AM)', {faixa: 'fora'}), p('faixas')).cor, M.COR_NEUTRA);
  assert.deepEqual(M.pintar(municipio('code:9', 'X (AM)', {condicoes: {situacao: 'NAO_ATENDE', porCondicao: [], motivo: null}}), p('condicoes')),
    {cor: M.COR_NEUTRA, vazada: false, apagada: true});
  assert.equal(M.pintar(municipio('code:9', 'X (AM)', {condicoes: {situacao: 'ATENDE', porCondicao: [], motivo: null}}), p('condicoes')).cor, M.COR_BOLHA);
  assert.equal(M.pintar(municipio('code:9', 'X (AM)', {ordem: {posicao: 3}}), p('ordem')).apagada, true);
  assert.equal(M.pintar(municipio('code:9', 'X (AM)', {ordem: {posicao: 2}}), p('ordem')).cor, M.COR_BOLHA);
  assert.equal(M.pintar(municipio('code:9', 'X (AM)'), p('unica')).cor, M.COR_BOLHA);
  assert.equal(M.familiaDaClasse('DECLINIO_DESACELERADO'), 'DECLINIO');
  assert.deepEqual(M.CLASSES_TENDENCIA.map(item => item.rotulo), ['Crescimento', 'Aceleração do crescimento', 'Desaceleração do crescimento',
    'Declínio', 'Aceleração do declínio', 'Desaceleração do declínio', 'Sem classificação']);
  assert.equal(M.corOrdinal(1, 5), '#86b6ef');
  assert.equal(M.corOrdinal(5, 5), '#104281');
  assert.equal(M.corOrdinal(1, 10), null);
});

test('conjunto rotulado como soma das contagens dos componentes, com possível dupla contagem (RQ-REP-14)', () => {
  const conjunto = ITENS[5];
  assert.equal(M.textoDaContagem(conjunto.contagem), 'soma das contagens dos componentes, com possível dupla contagem');
  const dica = M.montarDica(conjunto, {indicador: 'densidade', competencia: '202406', competenciaInicial: '202306', distancia: true,
    variacao: true, tendencia: false, nomes: new Map([['code:130420', 'TEFE (AM)'], ['code:130340', 'PARINTINS (AM)']]), rotulos: BR});
  assert.equal(dica.subtitulo, 'Conjunto de municípios · soma das contagens dos componentes, com possível dupla contagem');
  assert.ok(dica.notas.some(nota => nota.includes('possível dupla contagem')));
  assert.ok(dica.notas.includes('Membros: TEFE (AM), PARINTINS (AM).'));
  assert.deepEqual(dica.linhas.find(linha => linha.rotulo.startsWith('Variação da densidade')),
    {rotulo: 'Variação da densidade desde 06/2023 (aumento)', valor: '+214,29%'});
  assert.deepEqual(dica.linhas.find(linha => linha.rotulo === 'Distância (membro mais distante)'), {rotulo: 'Distância (membro mais distante)', valor: '523,14 km'});
  assert.ok(!JSON.stringify(dica).includes('pessoas únicas') && !JSON.stringify(dica).includes('profissionais distintos'));
  assert.equal(dica.acao, null);
  const tefe = M.montarDica(ITENS[1], {indicador: 'densidade', competencia: '202406', competenciaInicial: null, distancia: true,
    variacao: false, tendencia: false, nomes: new Map(), rotulos: BR});
  assert.equal(tefe.titulo, 'TEFE (AM)');
  assert.equal(tefe.subtitulo, 'Município · AM');
  assert.deepEqual(tefe.linhas.map(linha => linha.valor), ['2.000 habitantes', '10', '5,00 por 1.000 habitantes', '523,14 km']);
  const distrito = M.montarDica(ITENS[1], {indicador: 'densidade', competencia: '202406', competenciaInicial: null, distancia: false,
    variacao: false, tendencia: false, nomes: new Map(), rotulos: DISTRITOS});
  assert.equal(distrito.subtitulo, 'Distrito · AM');
  const novo = M.novoConjunto([{id: 'c1', rotulo: 'Interior', membros: []}], ['code:1', 'code:2', 'code:1'], '  ');
  assert.deepEqual(novo, {id: 'c2', rotulo: 'Conjunto 2', membros: ['code:1', 'code:2']});
});

test('estados em bolhas: a dica mostra a ação de ver os municípios do estado', () => {
  const amazonas = {...ITENS[1], id: 'uf:13', tipo: 'estado', rotulo: 'Amazonas (AM)', uf: 'AM'};
  const dica = M.montarDica(amazonas, {indicador: 'densidade', competencia: '202406', competenciaInicial: null, distancia: false, variacao: false,
    tendencia: false, nomes: new Map(), rotulos: BR, unidadesDoGrupo: id => id === 'uf:13' ? 62 : null});
  assert.equal(dica.subtitulo, 'Estado');
  assert.equal(dica.acao, 'Ver os 62 municípios');
  const provincia = M.montarDica(amazonas, {indicador: 'densidade', competencia: '202406', competenciaInicial: null, distancia: false, variacao: false,
    tendencia: false, nomes: new Map(), rotulos: DISTRITOS, unidadesDoGrupo: () => 12});
  assert.equal(provincia.subtitulo, 'Província');
  assert.equal(provincia.acao, 'Ver os 12 distritos');
});

test('nomenclatura territorial: na base do Brasil, os textos de sempre; numa planilha, distritos e províncias com concordância', () => {
  assert.equal(M.textoTodosOsGrupos(BR, 27), 'Todos os estados (27)');
  assert.equal(M.textoTodasAsUnidades(BR, 5570, true), 'Todos os municípios do Brasil (5.570)');
  assert.equal(M.textoVerUnidades(BR, 62), 'Ver os 62 municípios');
  assert.equal(M.textoVerUnidades(BR, 1), 'Ver o 1 município');
  assert.equal(M.textoTodasAsUnidadesDoGrupo(BR, GRUPOS[0]), 'Todos os municípios do Amazonas');
  assert.equal(M.textoInstrucaoGrupos(BR), 'Clique num estado para ver os municípios dele. Pelo teclado, use as setas e Enter.');
  assert.equal(M.textoCadaBolha(BR.unidade), 'Cada bolha é um município. O tamanho mostra a população.');
  assert.equal(M.apoioDaFamilia('distribuicao', BR), 'Como os municípios se distribuem');
  assert.equal(M.generoDe(DISTRITOS.unidade), 'm');
  assert.equal(M.generoDe(DISTRITOS.grupo), 'f');
  assert.equal(M.generoDe({singular: 'região', plural: 'regiões'}), 'f');
  assert.equal(M.generoDe({singular: 'cantão', plural: 'cantões'}), 'm');
  assert.equal(M.generoDe({singular: 'condado', plural: 'condados'}), 'm');
  assert.equal(M.generoDe({singular: 'bairro', plural: 'bairros', genero: 'f'}), 'f');  // o informado vale
  assert.equal(M.textoTodosOsGrupos(DISTRITOS, 5), 'Todas as províncias (5)');
  assert.equal(M.textoTodasAsUnidades(DISTRITOS, 40, false), 'Todos os distritos da planilha (40)');
  assert.equal(M.textoVerUnidades(DISTRITOS, 12), 'Ver os 12 distritos');
  assert.equal(M.textoTodasAsUnidadesDoGrupo(DISTRITOS, {nome: 'Buenos Aires', rotuloGrupo: ''}), 'Todos os distritos de Buenos Aires');
  assert.equal(M.textoInstrucaoGrupos(DISTRITOS), 'Clique numa província para ver os distritos dela. Pelo teclado, use as setas e Enter.');
  assert.equal(M.textoCadaBolha(DISTRITOS.unidade), 'Cada bolha é um distrito. O tamanho mostra a população.');
  const comunas = {unidade: {singular: 'comuna', plural: 'comunas'}, grupo: {singular: 'região', plural: 'regiões'}};
  assert.equal(M.textoVerUnidades(comunas, 12), 'Ver as 12 comunas');
  assert.equal(M.textoCadaBolha(comunas.unidade), 'Cada bolha é uma comuna. O tamanho mostra a população.');
  assert.equal(M.textoTodasAsUnidades(comunas, 3, false), 'Todas as comunas da planilha (3)');
  assert.equal(M.apoioDaFamilia('distribuicao', comunas), 'Como as comunas se distribuem');
  assert.deepEqual(M.rotulosEfetivos(null, null, 'brasil'), BR);
  assert.deepEqual(M.rotulosEfetivos(null, DISTRITOS, 'arquivo'), DISTRITOS);
  assert.deepEqual(M.rotulosEfetivos(comunas, DISTRITOS, 'arquivo'), comunas);  // os do motor, quando houver
  assert.deepEqual(M.rotulosEfetivos(null, null, 'arquivo'), M.ROTULOS_GENERICOS);
});

test('escolha de territórios: marcar e desmarcar unidades e grupos, sem perder o resto do universo', () => {
  const [a, b, c, d] = ['code:130260', 'code:130420', 'code:130340', 'code:350010'];
  const am = [a, b, c], grupos = ['13', '35'];
  assert.deepEqual(M.alternarUnidade({todos: false, estados: ['13'], ids: []}, b, '13', am, grupos), {todos: false, estados: [], ids: [a, c]});
  assert.deepEqual(M.alternarUnidade({todos: false, estados: [], ids: [a, c]}, b, '13', am, grupos), {todos: false, estados: ['13'], ids: []});
  assert.deepEqual(M.alternarUnidade({todos: true, estados: [], ids: []}, a, '13', am, grupos), {todos: false, estados: ['35'], ids: [b, c]});
  assert.deepEqual(M.alternarUnidade({todos: false, estados: [], ids: [d]}, a, '13', am, grupos), {todos: false, estados: [], ids: [d, a]});
  assert.deepEqual(M.marcarGrupo({todos: false, estados: [], ids: [a, d]}, '13', am), {todos: false, estados: ['13'], ids: [d]});
  assert.deepEqual(M.desmarcarGrupo({todos: false, estados: ['13', '35'], ids: []}, '13', am, grupos), {todos: false, estados: ['35'], ids: []});
  assert.deepEqual(M.desmarcarGrupo({todos: true, estados: [], ids: []}, '13', am, grupos), {todos: false, estados: ['35'], ids: []});
  assert.equal(M.marcadasNoGrupo({todos: false, estados: [], ids: [a, d]}, '13', am), 1);
  assert.equal(M.marcadasNoGrupo({todos: false, estados: ['13'], ids: []}, '13', am), 3);
  assert.equal(M.unidadeMarcada({todos: false, estados: ['13'], ids: []}, b, '13'), true);
  assert.equal(M.unidadesNoUniverso({todos: false, estados: ['13'], ids: [d]}, GRUPOS, 5570, M.prefixoDe), 63);
  assert.equal(M.unidadesNoUniverso({todos: true, estados: [], ids: []}, GRUPOS, 5570, M.prefixoDe), 5570);
  // Planilha sem coluna-mãe: desmarcar de "todas" deixa as demais; marcar a última que faltava volta a "todas".
  const todas = ['name:x', 'name:y'];
  assert.deepEqual(M.alternarUnidade({todos: true, estados: [], ids: []}, 'name:x', '', [], [], todas), {todos: false, estados: [], ids: ['name:y']});
  assert.deepEqual(M.alternarUnidade({todos: false, estados: [], ids: ['name:y']}, 'name:x', '', [], [], todas), {todos: true, estados: [], ids: []});
  assert.deepEqual(M.normalizarBase({todos: false, estados: ['35', '13', '13'], ids: ['code:130260', 'code:290070', 'code:290070']}),
    {todos: false, estados: ['13', '35'], ids: ['code:290070']});
  assert.deepEqual(M.normalizarBase({todos: false, estados: ['BA'], ids: ['name:x', 'name:z']}, id => id === 'name:x' ? 'BA' : 'CO'),
    {todos: false, estados: ['BA'], ids: ['name:z']});
  // Grupos: os estados da base do Brasil ou os valores da coluna-mãe da planilha.
  assert.deepEqual(M.gruposDaFonte({estados: [{prefixo: '13', sigla: 'AM', nome: 'Amazonas', rotulo_grupo: 'Municípios do Amazonas', municipios: 62}],
    municipios: {total: 62}}, []), [GRUPOS[0]]);
  const catalogo = [{id: 'name:a', name: 'A', code: '', label: 'A', state: 'BA', state_name: 'Buenos Aires'},
    {id: 'name:b', name: 'B', code: '', label: 'B', state: 'BA', state_name: 'Buenos Aires'},
    {id: 'name:c', name: 'C', code: '', label: 'C', state: 'CO', state_name: 'Córdoba'}];
  assert.deepEqual(M.gruposDaFonte(undefined, catalogo), [{id: 'BA', nome: 'Buenos Aires', sigla: '', rotuloGrupo: '', unidades: 2},
    {id: 'CO', nome: 'Córdoba', sigla: '', rotuloGrupo: '', unidades: 1}]);
  assert.equal(M.grupoDaUnidade(catalogo[2]), 'CO');
  // A bolha de um estado do motor volta ao item da lista: pelo identificador, pela sigla ou pelo nome.
  assert.equal(M.grupoDoItem({id: 'uf:13', uf: 'AM', rotulo: 'Amazonas (AM)'}, GRUPOS), '13');
  assert.equal(M.grupoDoItem({id: 'estado-amazonas', uf: null, rotulo: 'Amazonas (AM)'}, GRUPOS), '13');
  assert.equal(M.grupoDoItem({id: 'x', uf: null, rotulo: 'São Paulo'}, GRUPOS), '35');
  assert.equal(M.grupoDoItem({id: 'x', uf: null, rotulo: 'Pará'}, GRUPOS), null);
});

test('trilha de volta e lugar no título: "Brasil › Amazonas › 3 municípios"', () => {
  const c = {grupos: GRUPOS, rotulos: BR, brasil: true, temGrupos: true, total: 5570, grupoDe: M.prefixoDe};
  const base = (estados, ids = [], todos = false) => ({todos, estados, ids});
  assert.deepEqual(M.trilhaDoUniverso({...c, nivel: 'estados', base: base([])}), [{rotulo: 'Brasil', acao: null}, {rotulo: 'Todos os estados (2)', acao: null}]);
  assert.deepEqual(M.trilhaDoUniverso({...c, nivel: 'municipios', base: base(['13'])}),
    [{rotulo: 'Brasil', acao: {tipo: 'estados'}}, {rotulo: 'Amazonas (62 municípios)', acao: null}]);
  assert.deepEqual(M.trilhaDoUniverso({...c, nivel: 'municipios', base: base([], ['code:130260', 'code:130420', 'code:130340'])}),
    [{rotulo: 'Brasil', acao: {tipo: 'estados'}}, {rotulo: 'Amazonas', acao: {tipo: 'grupo', id: '13'}}, {rotulo: '3 municípios', acao: null}]);
  assert.deepEqual(M.trilhaDoUniverso({...c, nivel: 'municipios', base: base([], [], true)}),
    [{rotulo: 'Brasil', acao: {tipo: 'estados'}}, {rotulo: 'Todos os municípios (5.570)', acao: null}]);
  assert.deepEqual(M.trilhaDoUniverso({...c, nivel: 'municipios', base: base([])}),
    [{rotulo: 'Brasil', acao: {tipo: 'estados'}}, {rotulo: 'Nenhum município marcado', acao: null}]);
  assert.deepEqual(M.trilhaDoUniverso({...c, nivel: 'municipios', base: base(['13', '35'])}),
    [{rotulo: 'Brasil', acao: {tipo: 'estados'}}, {rotulo: 'Amazonas, São Paulo (707 municípios)', acao: null}]);
  assert.deepEqual(M.trilhaDoUniverso({nivel: 'municipios', base: base([], ['name:a']), grupos: [{id: 'BA', nome: 'Buenos Aires', sigla: '', rotuloGrupo: '', unidades: 12}],
    rotulos: DISTRITOS, brasil: false, temGrupos: false, total: 40, grupoDe: () => 'BA'}),
    [{rotulo: 'Planilha', acao: {tipo: 'todos'}}, {rotulo: 'Buenos Aires', acao: {tipo: 'grupo', id: 'BA'}}, {rotulo: '1 distrito', acao: null}]);
  const lugar = (nivel, b, rotulos = BR, brasil = true, grupos = GRUPOS, grupoDe = M.prefixoDe) =>
    M.lugarDoUniverso({nivel, base: b, conjuntos: 0, grupos, rotulos, brasil, grupoDe});
  assert.deepEqual(lugar('municipios', base(['13'])), {lugar: 'nos municípios do Amazonas', curto: 'Amazonas'});
  assert.deepEqual(lugar('municipios', base(['13', '35'])), {lugar: 'nos municípios do Amazonas e de São Paulo', curto: 'Amazonas e São Paulo'});
  assert.deepEqual(lugar('municipios', base([], ['code:130260', 'code:130420', 'code:130340'])),
    {lugar: 'em 3 municípios do Amazonas', curto: '3 municípios do Amazonas'});
  assert.deepEqual(lugar('municipios', base([], [], true)), {lugar: 'nos municípios do Brasil', curto: 'Brasil'});
  assert.deepEqual(lugar('estados', base([])), {lugar: 'nos estados', curto: 'Brasil'});
  assert.deepEqual(lugar('municipios', base(['BA']), DISTRITOS, false, [{id: 'BA', nome: 'Buenos Aires', sigla: '', rotuloGrupo: '', unidades: 12}], () => 'BA'),
    {lugar: 'nos distritos de Buenos Aires', curto: 'Buenos Aires'});
  assert.deepEqual(lugar('municipios', base([], [], true), {unidade: {singular: 'comuna', plural: 'comunas'}, grupo: null}, false),
    {lugar: 'nas comunas da planilha', curto: 'Planilha'});
});

test('título dinâmico: diz o indicador, onde e quando; o subtítulo explica a leitura', () => {
  const t = extra => M.tituloDaAnalise({fonte: 'brasil', familia: 'distribuicao', visao: 'classes', indicador: 'densidade', nivel: 'municipios',
    categoria: 'MEDICINA', competencia: '202406', janela: [], rotatividade: null, lugar: {lugar: 'nos municípios do Amazonas', curto: 'Amazonas'},
    referencia: null, rotulos: BR, ...extra});
  assert.deepEqual(t({}), {titulo: 'Densidade de médicos nos municípios do Amazonas · junho de 2024',
    subtitulo: 'Cada bolha é um município. O tamanho mostra a população.'});
  assert.deepEqual(t({nivel: 'estados', lugar: {lugar: 'nos estados', curto: 'Brasil'}}),
    {titulo: 'Densidade de médicos nos estados · junho de 2024', subtitulo: 'Cada bolha é um estado. O tamanho mostra a população.'});
  assert.equal(t({indicador: 'quantidade'}).titulo, 'Quantidade de médicos nos municípios do Amazonas · junho de 2024');
  assert.equal(t({familia: 'espacial', referencia: 'MANAUS (AM)'}).titulo, 'Densidade de médicos e distância até MANAUS (AM) · Amazonas · junho de 2024');
  assert.equal(t({familia: 'tendencia', janela: ['202106', '202206', '202306', '202406']}).titulo,
    'Tendência da densidade de médicos · Amazonas · junho de 2021 a junho de 2024');
  assert.equal(t({familia: 'tendencia', janela: ['202306', '202406']}).titulo, 'Mudança da densidade de médicos · Amazonas · junho de 2023 a junho de 2024');
  assert.equal(t({familia: 'tendencia', visao: 'series', janela: ['202106', '202206', '202306', '202406']}).subtitulo,
    'Cada linha é um município, nas competências da janela.');
  assert.equal(t({familia: 'rotatividade', rotatividade: {inicial: '202306', final: '202406'}}).titulo,
    'Rotatividade e permanência da coorte inicial · Amazonas · junho de 2023 a junho de 2024');
  assert.equal(t({fonte: null}).titulo, 'Diagnóstico territorial da força de trabalho em saúde');
  assert.deepEqual(t({fonte: 'arquivo', categoria: 'ENFERMAGEM', competencia: '2024', rotulos: DISTRITOS,
    lugar: {lugar: 'nos distritos da planilha', curto: 'Planilha'}}),
    {titulo: 'Densidade de profissionais de enfermagem nos distritos da planilha · 2024', subtitulo: 'Cada bolha é um distrito. O tamanho mostra a população.'});
  assert.equal(M.profissionaisDe('MEDICINA'), 'médicos');
});

test('pedido ao motor com as chaves do contrato: nível e indicador em todo pedido; estados na abertura, municípios, grupos, faixas, espacial, tendência e rotatividade', () => {
  const inicial = definicao();
  assert.equal(inicial.nivel, 'estados');
  assert.equal(inicial.competencia, '202406');
  assert.deepEqual(inicial.janela, []);  // a janela da tendência é escolha da pessoa (decisão 5a)
  assert.deepEqual(M.montarOpcoes(inicial, 'distribuicao'), {competencia: '202406', categoria: 'MEDICINA', nivel: 'estados', indicador: 'densidade'});
  assert.equal(M.definicaoInicial({tipo: 'arquivo', periodos: ['2024'], categoria: 'ENFERMAGEM', temGrupos: false}).nivel, 'municipios');
  // A planilha abre com todas as unidades (não há estados nem bolhas de grupo); a base do Brasil, sem nenhuma (os estados).
  assert.deepEqual(M.definicaoInicial({tipo: 'arquivo', periodos: ['2024'], categoria: 'ENFERMAGEM', temGrupos: false}).base,
    {todos: true, estados: [], ids: []});
  assert.deepEqual(inicial.base, {todos: false, estados: [], ids: []});
  const am = {nivel: 'municipios', base: {todos: false, estados: ['13'], ids: []}};
  const base = {nivel: 'municipios', indicador: 'densidade', base: {municipios: {todos: false, estados: ['13'], ids: []}}};
  assert.deepEqual(M.montarOpcoes(definicao(am), 'distribuicao'), {competencia: '202406', categoria: 'MEDICINA', ...base});
  assert.deepEqual(M.montarOpcoes(definicao({...am, agrupar: {tipo: 'quartis', faixas: []}}), 'distribuicao'),
    {competencia: '202406', categoria: 'MEDICINA', ...base, grupos: {tipo: 'quartis'}, indicador: 'densidade'});
  assert.deepEqual(M.montarOpcoes(definicao({...am, indicador: 'quantidade', agrupar: {tipo: 'faixas', faixas: [0, 1, 2]}}), 'distribuicao'),
    {competencia: '202406', categoria: 'MEDICINA', ...base, faixas: [0, 1, 2], indicador: 'quantidade'});
  assert.deepEqual(M.montarOpcoes(definicao({...am, agrupar: {tipo: 'faixas', faixas: [1]}}), 'distribuicao'), {competencia: '202406', categoria: 'MEDICINA', ...base});
  const espacial = definicao({...am, familia: 'espacial', referencia: {membros: ['code:130260'], criterio: {atributo: 'densidade', ordem: 'desc'}},
    faixasDistancia: [0, 100, 300], condicoes: [{atributo: 'densidade', operador: '<', valor: 1}, {atributo: 'distancia_km', operador: '>', valor: 150}]});
  assert.deepEqual(M.montarOpcoes(espacial, 'espacial'), {competencia: '202406', categoria: 'MEDICINA', ...base,
    referencia: {membros: ['code:130260'], criterio: {atributo: 'densidade', ordem: 'desc'}}, faixas_distancia: [0, 100, 300],
    condicoes: [{atributo: 'densidade', operador: '<', valor: 1}, {atributo: 'distancia_km', operador: '>', valor: 150}]});
  assert.deepEqual(M.montarOpcoes(espacial, 'distribuicao'), {competencia: '202406', categoria: 'MEDICINA', ...base,
    condicoes: [{atributo: 'densidade', operador: '<', valor: 1}]});  // sem referência, a condição de distância não vai
  const janela = ['202106', '202206', '202306', '202406'];
  assert.deepEqual(M.montarOpcoes(definicao({...am, familia: 'tendencia', janela}), 'tendencia'), {competencia: '202406', categoria: 'MEDICINA', ...base,
    competencia_inicial: '202106', tendencia: {competencias: janela}, indicador: 'densidade'});
  // A visão é estado visual: Mudança, Classes e Séries pedem o mesmo.
  assert.deepEqual(M.montarOpcoes(definicao({...am, familia: 'tendencia', janela, visao: 'mudanca'}), 'tendencia'),
    M.montarOpcoes(definicao({...am, familia: 'tendencia', janela, visao: 'series'}), 'tendencia'));
  assert.deepEqual(M.montarOpcoes(definicao({...am, familia: 'tendencia', janela: ['202306', '202406'], ordenar: {atributo: 'variacao', ordem: 'desc'}}), 'tendencia'),
    {competencia: '202406', categoria: 'MEDICINA', ...base, competencia_inicial: '202306', ordenar: {atributo: 'variacao', ordem: 'desc'}});
  assert.deepEqual(M.montarOpcoes(definicao({...am, ordenar: {atributo: 'variacao', ordem: 'desc'}}), 'distribuicao'), {competencia: '202406', categoria: 'MEDICINA', ...base});
  assert.deepEqual(M.montarOpcoes(definicao({...am, ordenar: {atributo: 'densidade', ordem: 'asc', primeiros: 10}, comparar: ['code:130260', 'code:130420']}), 'distribuicao'),
    {competencia: '202406', categoria: 'MEDICINA', ...base, ordenar: {atributo: 'densidade', ordem: 'asc', primeiros: 10}, comparar: ['code:130260', 'code:130420']});
  assert.deepEqual(M.montarOpcoes(definicao({...am, familia: 'rotatividade', rotatividade: {inicial: '202306', final: '202406'},
    comparar: ['code:130260', 'code:130420'], condicoes: [{atributo: 'densidade', operador: '<', valor: 1}]}), 'rotatividade'),
    {competencia: '202406', categoria: 'MEDICINA', ...base, rotatividade: {inicial: '202306', final: '202406'}});
  assert.deepEqual(M.montarOpcoes(definicao({...am, premissas: {crs: 'SIRGAS2000'}}), 'distribuicao'),
    {competencia: '202406', categoria: 'MEDICINA', ...base, premissas: {crs: 'SIRGAS2000'}});
  // Conjuntos vão com a base; na visão dos estados, nunca (estados e municípios nunca se somam).
  const conjunto = {id: 'c1', rotulo: 'Interior', membros: ['code:130420', 'code:130340']};
  assert.deepEqual(M.montarOpcoes(definicao({...am, conjuntos: [conjunto]}), 'distribuicao').conjuntos, [conjunto]);
  assert.equal(M.montarOpcoes(definicao({conjuntos: [conjunto]}), 'distribuicao').conjuntos, undefined);
});

test('o que falta para pedir e o que a família espera; a família calculada enquanto isso', () => {
  const vazio = definicao({nivel: 'municipios'});
  assert.equal(M.bloqueioDoPedido(vazio, {fonte: 'brasil', rotulos: BR}), 'Marque os municípios na lista de territórios para ver o gráfico.');
  assert.equal(M.bloqueioDoPedido(vazio, {fonte: 'arquivo', rotulos: DISTRITOS}), 'Marque os distritos na lista de territórios para ver o gráfico.');
  assert.equal(M.bloqueioDoPedido(vazio, {fonte: null, rotulos: BR}), 'Escolha os dados para começar.');
  assert.equal(M.bloqueioDoPedido(definicao(), {fonte: 'brasil', rotulos: BR}), null);
  const ok = {disponivel: true, motivo: '', pendente: false, enviarDados: false};
  const am = {nivel: 'municipios', base: {todos: false, estados: ['13'], ids: []}};
  assert.ok(M.avisoDaFamilia(definicao({...am, familia: 'tendencia'}), ok).startsWith('Escolha a janela da tendência'));
  assert.equal(M.avisoDaFamilia(definicao({...am, familia: 'tendencia', janela: ['202306', '202406']}), ok),
    'A análise de tendência exige quatro observações válidas. Com 2 competências, aparece a mudança entre a primeira e a última.');
  assert.equal(M.avisoDaFamilia(definicao({...am, familia: 'espacial'}), ok), 'Escolha a referência da distância: por critério ou pelo nome.');
  assert.equal(M.avisoDaFamilia(definicao({...am}), ok), null);
  assert.equal(M.familiaCalculada(definicao({...am, familia: 'tendencia'}), true), 'distribuicao');
  assert.equal(M.familiaCalculada(definicao({...am, familia: 'tendencia', janela: ['202306', '202406']}), true), 'tendencia');
  assert.equal(M.familiaCalculada(definicao({...am, familia: 'espacial'}), true), 'distribuicao');
  assert.equal(M.familiaCalculada(definicao({...am, familia: 'espacial', referencia: {membros: ['code:130260']}}), true), 'espacial');
  assert.equal(M.familiaCalculada(definicao({familia: 'espacial', referencia: {membros: ['code:130260']}}), true), 'distribuicao');  // estados
  assert.equal(M.familiaCalculada(definicao({...am, familia: 'rotatividade', rotatividade: {inicial: '202306', final: '202406'}}), false), 'distribuicao');
  assert.equal(M.visaoEfetiva(definicao({...am, janela: ['202306', '202406'], visao: 'classes'})), 'mudanca');
  assert.equal(M.visaoEfetiva(definicao({...am, janela: ['202106', '202206', '202306', '202406'], visao: 'series'})), 'series');
});

test('disponibilidade das famílias: rotatividade só com identificador; motivos do motor; nos estados, espacial e tendência esperam', () => {
  const c = extra => ({fonte: 'brasil', nivel: 'municipios', disponibilidade: null, temIdentificador: false, rotulos: BR, ...extra});
  const brasil = M.disponibilidadeDaFamilia('rotatividade', c({}));
  assert.equal(brasil.disponivel, false);
  assert.equal(brasil.enviarDados, true);
  assert.ok(brasil.motivo.startsWith('A base do Brasil tem contagens, não pessoas'));
  const semId = M.disponibilidadeDaFamilia('rotatividade', c({fonte: 'arquivo'}));
  assert.equal(semId.disponivel, false);
  assert.ok(semId.motivo.startsWith('A planilha não tem a coluna do identificador individual'));
  assert.equal(M.disponibilidadeDaFamilia('rotatividade', c({fonte: 'arquivo', temIdentificador: true})).disponivel, true);
  assert.deepEqual(M.disponibilidadeDaFamilia('rotatividade', c({fonte: 'arquivo', temIdentificador: true,
    disponibilidade: {rotatividade: {disponivel: false, motivo: 'Sem identificador.'}}})),
    {disponivel: false, motivo: 'Sem identificador.', pendente: false, enviarDados: false});
  assert.deepEqual(M.disponibilidadeDaFamilia('espacial', c({fonte: 'arquivo', disponibilidade: {espacial: {disponivel: false, motivo: 'Planilha sem coordenadas.'}}})),
    {disponivel: false, motivo: 'Planilha sem coordenadas.', pendente: false, enviarDados: false});
  const nosEstados = M.disponibilidadeDaFamilia('espacial', c({nivel: 'estados'}));
  assert.equal(nosEstados.disponivel, true);
  assert.equal(nosEstados.pendente, true);
  assert.ok(nosEstados.motivo.includes('os estados não têm coordenadas'));
  assert.equal(M.disponibilidadeDaFamilia('tendencia', c({nivel: 'estados'})).pendente, true);
  assert.equal(M.disponibilidadeDaFamilia('tendencia', c({fonte: null})).pendente, true);
  assert.deepEqual(M.disponibilidadeDaFamilia('distribuicao', c({nivel: 'estados'})), {disponivel: true, motivo: '', pendente: false, enviarDados: false});
});

test('comando da conversa aplicado ao gráfico: cada campo validado; o que não vale vira mensagem', () => {
  const nomes = new Map([['code:130260', 'MANAUS (AM)'], ['code:130420', 'TEFE (AM)'], ['code:130340', 'PARINTINS (AM)']]);
  const c = {periodos: ['202306', '202406'], nomes, temGrupos: true,
    disponivel: f => M.disponibilidadeDaFamilia(f, {fonte: 'brasil', nivel: 'municipios', disponibilidade: null, temIdentificador: false, rotulos: BR})};
  const def = definicao();
  const para = M.aplicarPedido(def, {municipios: {todos: false, estados: ['15'], ids: []}}, c);
  assert.equal(para.definicao.nivel, 'municipios');
  assert.deepEqual(para.definicao.base, {todos: false, estados: ['15'], ids: []});
  assert.deepEqual(para.mensagens, []);
  assert.equal(M.aplicarPedido(para.definicao, {nivel: 'estados'}, c).definicao.nivel, 'estados');
  const rot = M.aplicarPedido(def, {familia: 'rotatividade'}, c);
  assert.equal(rot.definicao.familia, 'distribuicao');
  assert.ok(rot.mensagens[0].startsWith('Rotatividade: A base do Brasil'));
  const ref = M.aplicarPedido(def, {referencia: {membros: ['code:150140']}}, c);
  assert.equal(ref.definicao.familia, 'espacial');
  assert.deepEqual(ref.definicao.referencia, {membros: ['code:150140']});
  assert.equal(ref.definicao.nivel, 'municipios');
  const comCriterio = M.aplicarPedido(def, {referencia: {membros: ['code:150140'], criterio: {atributo: 'densidade', ordem: 'desc'}}}, c);
  assert.deepEqual(comCriterio.definicao.referencia, {membros: ['code:150140'], criterio: {atributo: 'densidade', ordem: 'desc'}});
  const janela = M.aplicarPedido(def, {janela: ['202406', '202306', '209913']}, c);
  assert.deepEqual(janela.definicao.janela, ['202306', '202406']);
  assert.equal(janela.definicao.familia, 'tendencia');
  assert.deepEqual(M.aplicarPedido(def, {competencia: '202413'}, c).mensagens, ['A competência 202413 não existe nesta base.']);
  assert.equal(M.aplicarPedido(def, {competencia: '202306'}, c).definicao.competencia, '202306');
  assert.equal(M.aplicarPedido(def, {indicador: 'quantidade'}, c).definicao.indicador, 'quantidade');
  const compara = M.aplicarPedido(def, {funcao: 'comparar', selecao: ['code:130260', 'code:130420']}, c);
  assert.deepEqual(compara.definicao.comparar, ['code:130260', 'code:130420']);
  assert.equal(compara.abrir, 'comparar');
  assert.deepEqual(compara.selecao, ['code:130260', 'code:130420']);
  const junta = M.aplicarPedido(def, {funcao: 'juntar', selecao: ['code:130260', 'code:130420', 'code:130340']}, c);
  assert.deepEqual(junta.definicao.conjuntos, [{id: 'c1', rotulo: 'MANAUS (AM), TEFE (AM), PARINTINS (AM)', membros: ['code:130260', 'code:130420', 'code:130340']}]);
  assert.deepEqual(junta.selecao, ['c1']);
  assert.equal(junta.definicao.nivel, 'municipios');
  const ordena = M.aplicarPedido(def, {ordenar: {atributo: 'densidade', ordem: 'desc', primeiros: 5}}, c);
  assert.deepEqual(ordena.definicao.ordenar, {atributo: 'densidade', ordem: 'desc', primeiros: 5});
  assert.equal(ordena.abrir, 'ordenar');
  assert.deepEqual(M.aplicarPedido(def, {ordenar: {atributo: 'x'}}, c).mensagens, ['A ordenação pedida não foi reconhecida.']);
  const condiciona = M.aplicarPedido(definicao({nivel: 'municipios', base: {todos: false, estados: ['13'], ids: []}}),
    {condicoes: [{atributo: 'densidade', operador: '<', valor: 1}, {atributo: 'distancia_km', operador: '>', valor: 150}]}, c);
  assert.deepEqual(condiciona.definicao.condicoes, [{atributo: 'densidade', operador: '<', valor: 1}, {atributo: 'distancia_km', operador: '>', valor: 150}]);
  assert.equal(condiciona.definicao.familia, 'espacial');
  assert.equal(condiciona.abrir, 'condicoes');
  assert.deepEqual(M.aplicarPedido(def, {condicoes: [{atributo: 'densidade'}]}, c).mensagens, ['As condições pedidas não foram reconhecidas.']);
});

test('janela da tendência: atalhos sem janela padrão; posições no tempo; séries sem ligar lacunas; velocidades em barras', () => {
  const periodos = ['202001', '202006', '202101', '202106', '202201', '202206', '202301', '202306', '202401', '202406'];
  assert.deepEqual(M.janelaDoAtalho('ultimos4junhos', periodos), ['202106', '202206', '202306', '202406']);
  assert.deepEqual(M.janelaDoAtalho('anualjunho', periodos), ['202006', '202106', '202206', '202306', '202406']);
  assert.deepEqual(M.janelaDoAtalho('todas', [...periodos].reverse()), periodos);
  const sintetico = ['202301', '202306', '202401', '202406'];
  assert.deepEqual(M.janelaDoAtalho('ultimos4junhos', sintetico), []);  // só dois junhos
  assert.deepEqual(M.janelaDoAtalho('anualjunho', sintetico), ['202306', '202406']);
  assert.deepEqual([...M.posicoesTemporais(['202306', '202301', '202406', '202401']).entries()],
    [['202301', 0], ['202306', 5], ['202401', 12], ['202406', 17]]);  // janeiro e junho a 5 e 7 meses, como são
  assert.deepEqual([...M.posicoesTemporais(['2021', '2020']).entries()], [['2020', 0], ['2021', 1]]);
  const tendencia = observacoes => ({classe: 'CRESCIMENTO', rotulo: 'Crescimento', motivo: null, familia: 'CRESCIMENTO', avaliavel: true, observacoes, velocidades: []});
  const comLacuna = municipio('code:1', 'A (AM)', {tendencia: tendencia([{competencia: '202306', valor: 1}, {competencia: '202401', valor: null},
    {competencia: '202406', valor: 2}])});
  const continua = municipio('code:2', 'B (AM)', {tendencia: tendencia([{competencia: '202306', valor: 1}, {competencia: '202401', valor: 1.5},
    {competencia: '202406', valor: 2}])});
  const {series, marcasX} = M.montarSeries({itens: [comLacuna, continua], janela: ['202306', '202401', '202406'], dominio: [0, 2], x0: 0, x1: 120, y0: 0, y1: 100});
  assert.deepEqual(marcasX.map(marca => marca.competencia), ['202306', '202401', '202406']);
  assert.equal(series[0].pontos.length, 2);
  assert.deepEqual(series[0].caminhos, []);  // a lacuna separa as duas observações: nenhuma linha inventada
  assert.equal(series[0].cor, M.CORES_TENDENCIA.CRESCIMENTO);
  assert.deepEqual(series[1].caminhos, ['M0.0 50.0 L70.0 25.0 L120.0 0.0']);
  assert.deepEqual([series[1].fim.x, series[1].fim.y], [120, 0]);
  const barras = M.barrasDeVelocidade([1, 2, 4], 100, 50);
  assert.equal(barras.base, 48);
  assert.deepEqual(barras.barras.map(barra => barra.altura), [11.5, 23, 46]);
  assert.ok(barras.barras.every(barra => barra.y + barra.altura === 48));
  const comZero = M.barrasDeVelocidade([0, 2], 100, 50);
  assert.deepEqual([comZero.barras[0].altura, comZero.barras[0].sinal, comZero.barras[0].y], [2, 0, 47]);
  assert.equal(M.barrasDeVelocidade([-1, 1], 100, 50).base, 25);
});

test('tabela: ordem do código territorial por padrão; reordenar é pedido do usuário, sem valor por último; páginas de 100', () => {
  const itens = ITENS.slice(0, 4);
  assert.deepEqual(M.ordenarTabela([...itens].reverse(), null, 'densidade').map(item => item.id),
    ['code:130260', 'code:130340', 'code:130420', 'code:350010']);
  assert.deepEqual(M.ordenarTabela(itens, {coluna: 'variacao', sentido: 'desc'}, 'densidade').map(item => item.id),
    ['code:130420', 'code:130260', 'code:350010', 'code:130340']);
  assert.deepEqual(M.ordenarTabela(itens, {coluna: 'densidade', sentido: 'asc'}, 'densidade').map(item => item.id),
    ['code:130340', 'code:130420', 'code:350010', 'code:130260']);
  const posicoes = [municipio('code:1', 'A (AM)', {ordem: {posicao: 2}}), municipio('code:2', 'B (AM)', {ordem: {posicao: null}}),
    municipio('code:3', 'C (AM)', {ordem: {posicao: 1}})];
  assert.deepEqual(M.ordenarTabela(posicoes, {coluna: 'posicao', sentido: 'asc'}, 'densidade').map(item => item.id), ['code:3', 'code:1', 'code:2']);
  const linhas = Array.from({length: 250}, (_, i) => i);
  const pagina = M.paginar(linhas, 2);
  assert.deepEqual([pagina.pagina, pagina.paginas, pagina.linhas.length, pagina.linhas[0]], [2, 3, 50, 200]);
  assert.equal(M.paginar(linhas, 9).pagina, 2);
  assert.deepEqual(M.paginar([], 0), {linhas: [], pagina: 0, paginas: 1});
});

test('"Usar o primeiro": a 1ª posição do motor; com empate, todos os empatados para a escolha', () => {
  assert.deepEqual(M.primeirosColocados([{id: 'a', posicao: 1}, {id: 'b', posicao: 1}, {id: 'c', posicao: 3}]).map(item => item.id), ['a', 'b']);
  assert.deepEqual(M.primeirosColocados([{id: 'a', posicao: 1}, {id: 'b', posicao: 2}]).map(item => item.id), ['a']);
  assert.deepEqual(M.primeirosColocados([{id: 'a', posicao: null}]), []);
  assert.equal(M.maisRecente(['202406', '202301', '202306', '202401']), '202406');
  assert.deepEqual(M.anteriores(['202406', '202301', '202306', '202401'], '202406'), ['202301', '202306', '202401']);
});

test('exportar: CSV com precisão integral, avaliabilidade e motivo; método em texto; estado salvo reabre sem recalcular', () => {
  const item = (id, rotulo, extra) => ({id, tipo: 'municipio', rotulo, uf: null, populacao: 9000, quantidade: 105, densidade: 11.666666666666666,
    distancia_km: null, inicial: {...VAZIO}, variacao_percentual: {...VAZIO}, avaliavel: {densidade: true, distancia: null, variacao: null}, motivos: [],
    referencia: false, tendencia: null, grupo: null, faixa: null, faixa_distancia: null, referencia_mais_proxima: null, condicoes: null, ordem: null,
    rotatividade: null, ...extra});
  const resposta = {competencia: '202406', competencia_inicial: null, categoria: 'MEDICINA', versao_base: 'v1', chave_execucao: 'k1', nivel: 'municipios',
    referencia: null, itens: [item('code:350010', 'FORA (SP)', {}), item('code:130260', '=SOMA(A1)', {densidade: null,
      avaliavel: {densidade: false, distancia: null, variacao: null}, motivos: [SEM_REGISTRO]})],
    dominios: {}, notas: ['Nota do motor.'], limitacoes: ['UNIDADES_NAO_AVALIAVEIS'], tendencia: null, grupos: null, faixas: null, faixasDistancia: null,
    condicoes: null, ordenacao: null, comparacao: null, contextoBrasil: null, disponibilidade: {}, sessao: null, rotulos: null};
  const csv = M.montarCsv(resposta, {familia: 'distribuicao', indicador: 'densidade', rotulos: BR});
  assert.ok(csv.startsWith('﻿'));
  const linhas = csv.slice(1).split('\r\n');
  assert.equal(linhas.length, 3);
  assert.equal(linhas[0], ['Identificador', 'Tipo', 'Território', 'UF', 'Competência', 'Categoria', 'População', 'Quantidade',
    'Densidade por 1.000 habitantes', 'Tipo de contagem', 'Avaliável', 'Motivos'].map(nome => '"' + nome + '"').join(';'));
  assert.ok(linhas[1].startsWith('"code:130260";"município";"\'=SOMA(A1)";""'));  // ordem neutra e proteção contra fórmula
  assert.ok(linhas[1].includes('"não"') && linhas[1].includes('(SEM_REGISTRO_OBSERVADO)'));
  assert.ok(linhas[2].includes('"11.666666666666666"'));  // precisão integral, como veio do motor
  const metodo = M.textoDoMetodo(resposta, 'Densidade de médicos', {competencia: '202406', categoria: 'MEDICINA'});
  assert.ok(metodo.startsWith('Densidade de médicos'));
  assert.ok(metodo.includes('Nota do motor.') && metodo.includes('Parâmetros enviados ao motor') && metodo.includes('"competencia": "202406"'));
  const def = definicao({nivel: 'municipios', base: {todos: false, estados: ['13'], ids: []}});
  const salvo = M.salvarEstado('Densidade de médicos', {chave: 'k', familia: 'distribuicao', opcoes: {competencia: '202406', categoria: 'MEDICINA'},
    definicao: def, visual: {escala: 'linear', corte: null, selecionados: ['code:130260']}}, resposta, '2026-10-22T12:00:00.000Z');
  assert.equal(salvo.titulo, 'Densidade de médicos');
  assert.equal(salvo.quando, '2026-10-22T12:00:00.000Z');
  assert.deepEqual(M.lerEstadoSalvo(salvo), {...salvo.definicao, resposta});
  assert.equal(M.lerEstadoSalvo({titulo: 'x', definicao: {versao: 2}, resposta: null, quando: ''}), null);
  assert.equal(M.lerEstadoSalvo(null), null);
});

test('contexto do gráfico para a página e a conversa: família, indicador, universo, unidades na tela, competência e referência', () => {
  const def = definicao({familia: 'espacial', nivel: 'municipios', base: {todos: false, estados: ['13'], ids: ['code:130260']},
    referencia: {membros: ['code:130260']}});
  assert.deepEqual(M.contextoDoGrafico(def, ['code:130260'], 'T'), {familia: 'espacial', indicador: 'densidade', nivel: 'municipios',
    municipios: {todos: false, estados: ['13'], ids: []}, idsNaTela: ['code:130260'], competencia: '202406', janela: [], referencia: ['code:130260'], titulo: 'T'});
  const tendencia = M.contextoDoGrafico(definicao({familia: 'tendencia', janela: ['202306', '202406'], competencia: '202306'}), [], 'T');
  assert.equal(tendencia.competencia, '202406');
  assert.deepEqual(tendencia.referencia, []);
});

test('cliente do motor: a resposta normalizada para a tela (tendência, grupos, faixas, condições, ordem, comparação, rotulos)', () => {
  const bruta = {
    competencia: '202406', competencia_inicial: '202106', categoria: 'MEDICINA', versao_base: 'abc', chave_execucao: 'k', referencia: null,
    itens: [{id: 'code:130260', tipo: 'municipio', rotulo: 'MANAUS (AM)', uf: 'AM', populacao: 1000, quantidade: 15, densidade: 15, distancia_km: null,
      inicial: {populacao: 1000, quantidade: 12, densidade: 12}, variacao_percentual: {populacao: 0, quantidade: 25, densidade: 25},
      avaliavel: {densidade: true, distancia: null, variacao: true}, motivos: [], referencia: false,
      tendencia: {classe: 'CRESCIMENTO_ACELERADO', rotulo: 'Aceleração do crescimento', motivo: null, avaliavel: true,
        observacoes: [{competencia: '202106', valor: 10}, {competencia: '202206', valor: 11}, {competencia: '202306', valor: 13}, {competencia: '202406', valor: 16}],
        velocidades: [0.0833, 0.1667, 0.25]},
      grupo: {indice: 4, rotulo: '4º quartil'}, faixa: 'fora', referencia_mais_proxima: {id: 'code:1', rotulo: 'A'},
      condicoes: {situacao: 'NAO_ATENDE', por_condicao: [{condicao: 'densidade < 1', situacao: 'NAO_ATENDE'}]}, ordem: {posicao: 1},
      rotatividade: {coorte_inicial: 120, permanencia: 87, saida: 33, percentuais: {permanencia: 72.5, saida: 27.5}}},
      {semId: true}],
    dominios: {densidade: [0, 15], distancia_km: null}, notas: ['n'], limitacoes: ['L'],
    tendencia: {janela: ['202106', '202206', '202306', '202406'], contagens: {CRESCIMENTO_ACELERADO: 1, SEM_CLASSIFICACAO: 0}},
    grupos: {tipo: 'quartis', cortes: [1, 2, 3], contagens: {'1': 1, '2': 0, '3': 0, '4': 1}},
    condicoes: {contagens: {ATENDE: 0, NAO_ATENDE: 1, NAO_AVALIAVEL: 0}},
    ordenacao: {atributo: 'densidade', ordem: 'desc', primeiros: 5, empates_no_corte: false},
    comparacao: {itens: ['code:130260', 'code:130420'], maior: {densidade: {id: 'code:130260', rotulo: 'MANAUS (AM)', valor: 15}},
      menor: {densidade: {id: 'code:130420', rotulo: 'TEFE (AM)', valor: 5}}, diferencas: {densidade: [{entre: ['code:130260', 'code:130420'], valor: 10}]}},
    contexto: {brasil: {densidade: 2.36, quantidade: 500000, populacao: 212000000, competencia: '202406'}},
    disponibilidade: {rotatividade: {disponivel: false, motivo: 'Sem identificador individual.'}, espacial: {disponivel: true, motivo: ''}},
    sessao: {registrado: true, result_id: 'r1'},
    rotulos: {unidade: {singular: 'distrito', plural: 'distritos'}, grupo: {singular: 'província', plural: 'províncias'}},
  };
  const r = A.normalizarResposta(bruta);
  assert.equal(r.itens.length, 1);  // item sem id fica de fora
  assert.equal(r.nivel, 'municipios');
  const item = r.itens[0];
  assert.equal(item.tendencia.familia, 'CRESCIMENTO');
  assert.deepEqual(item.tendencia.velocidades, [{de: '202106', ate: '202206', valor: 0.0833}, {de: '202206', ate: '202306', valor: 0.1667},
    {de: '202306', ate: '202406', valor: 0.25}]);
  assert.equal(item.faixa, 'fora');
  assert.deepEqual(item.grupo, {indice: 4, rotulo: '4º quartil'});
  assert.deepEqual(item.referencia_mais_proxima, [{id: 'code:1', rotulo: 'A'}]);
  assert.deepEqual(item.condicoes, {situacao: 'NAO_ATENDE', porCondicao: [{texto: 'densidade < 1', situacao: 'NAO_ATENDE'}], motivo: null});
  assert.deepEqual(item.ordem, {posicao: 1});
  assert.deepEqual(item.rotatividade, {coorteInicial: 120, permaneceram: 87, sairam: 33, permanencia: 72.5, saida: 27.5, avaliavel: true, motivo: null});
  assert.deepEqual(r.grupos.contagens, [1, 0, 0, 1]);
  assert.deepEqual(r.grupos.cortes, [1, 2, 3]);
  assert.equal(r.grupos.rotulos[3], '4º quartil');
  assert.deepEqual(r.tendencia.janela, ['202106', '202206', '202306', '202406']);
  assert.deepEqual(r.tendencia.contagens, {CRESCIMENTO_ACELERADO: 1, SEM_CLASSIFICACAO: 0});
  assert.deepEqual(r.condicoes.contagens, {ATENDE: 0, NAO_ATENDE: 1, NAO_AVALIAVEL: 0});
  assert.deepEqual(r.ordenacao, {atributo: 'densidade', ordem: 'desc', primeiros: 5, empatesNoCorte: false, texto: null});
  assert.deepEqual(r.comparacao, {itens: ['code:130260', 'code:130420'], linhas: [{atributo: 'densidade',
    maior: [{id: 'code:130260', rotulo: 'MANAUS (AM)', valor: 15}], menor: [{id: 'code:130420', rotulo: 'TEFE (AM)', valor: 5}],
    diferencas: [{entre: ['code:130260', 'code:130420'], valor: 10, texto: null}]}], textos: []});
  assert.deepEqual(r.contextoBrasil, {densidade: 2.36, quantidade: 500000, populacao: 212000000, competencia: '202406'});
  assert.deepEqual(r.disponibilidade, {rotatividade: {disponivel: false, motivo: 'Sem identificador individual.'}, espacial: {disponivel: true, motivo: ''}});
  assert.deepEqual(r.sessao, {registrado: true, resultId: 'r1'});
  assert.deepEqual(r.rotulos, {unidade: {singular: 'distrito', plural: 'distritos'}, grupo: {singular: 'província', plural: 'províncias'}});
  assert.deepEqual(r.dominios, {densidade: [0, 15], distancia_km: null});
  assert.equal(r.faixas, null);
  // O motor de antes (sem as extensões) continua legível; só estados: nível dos estados.
  const estados = A.normalizarResposta({competencia: '202406', categoria: 'MEDICINA', itens: [{id: 'uf:13', tipo: 'estado', rotulo: 'Amazonas (AM)',
    populacao: 4000000, quantidade: 5000, densidade: 1.25}]});
  assert.equal(estados.nivel, 'estados');
  assert.deepEqual(estados.itens[0].avaliavel, {densidade: true, distancia: null, variacao: null});
  assert.equal(estados.itens[0].tendencia, null);
  assert.deepEqual(estados.disponibilidade, {});
  assert.throws(() => A.normalizarResposta({}), erro => erro instanceof A.ErroDoMotor);
  assert.deepEqual(A.rotulosDe({unidade: {singular: 'comuna', plural: 'comunas', genero: 'f'}}),
    {unidade: {singular: 'comuna', plural: 'comunas', genero: 'f'}, grupo: null});
  // Comparação em lista, com o atributo em cada objeto.
  const lista = A.normalizarResposta({competencia: '202406', categoria: 'MEDICINA', itens: [],
    comparacao: {itens: [{id: 'a'}, {id: 'b'}], maior: [{atributo: 'quantidade', id: 'a', rotulo: 'A', valor: 3}],
      menor: [{atributo: 'quantidade', id: 'b', rotulo: 'B', valor: 1}], diferencas: [{atributo: 'quantidade', de: 'a', para: 'b', diferenca: 2}]}});
  assert.deepEqual(lista.comparacao.linhas, [{atributo: 'quantidade', maior: [{id: 'a', rotulo: 'A', valor: 3}], menor: [{id: 'b', rotulo: 'B', valor: 1}],
    diferencas: [{entre: ['a', 'b'], valor: 2, texto: null}]}]);
  assert.deepEqual(lista.comparacao.itens, ['a', 'b']);
});

test('escalas e rótulos: domínio redondo, marcas, logarítmica só com valores positivos, rótulos sem colisão', () => {
  assert.deepEqual(M.enquadrar([0.12, 2.07], 'logaritmica'), [0.1, 5]);
  assert.deepEqual(M.marcas([0.1, 5], 'logaritmica'), [0.1, 0.2, 0.5, 1, 2, 5]);
  assert.deepEqual(M.enquadrar([0.12, 2.07], 'linear'), [0, 2.5]);
  assert.deepEqual(M.marcas([0, 15], 'linear'), [0, 5, 10, 15]);
  assert.equal(M.escalaPossivel([0, 3], 'logaritmica'), 'linear');
  assert.equal(M.escalaPossivel([1, 3], 'logaritmica'), 'logaritmica');
  assert.ok(Math.abs(M.fracao(10, [1, 100], 'logaritmica') - 0.5) < 1e-12);
  assert.ok(Math.abs(M.valorNaFracao(0.5, [1, 100], 'logaritmica') - 10) < 1e-9);
  const rotulos = M.posicionarRotulos([{id: 'a', x: 100, y: 100, r: 5, largura: 80}, {id: 'b', x: 104, y: 102, r: 5, largura: 80}], 800);
  assert.equal(rotulos.get('a').ancora, 'start');
  assert.notEqual(rotulos.get('a').dy, rotulos.get('b').dy);
  assert.equal(M.posicionarRotulos([{id: 'c', x: 780, y: 50, r: 5, largura: 80}], 800).get('c').ancora, 'end');
});

test('integração com o motor: planilha sem população começa na quantidade; as premissas da fonte vão em todo pedido', () => {
  const semPopulacao = M.definicaoInicial({tipo: 'arquivo', periodos: ['2023', '2024'], categoria: 'ENFERMAGEM', temGrupos: false,
    temPopulacao: false, premissas: {count_unit: 'pessoas', crs: 'SIRGAS2000'}});
  assert.equal(semPopulacao.indicador, 'quantidade');
  assert.deepEqual(semPopulacao.premissas, {count_unit: 'pessoas', crs: 'SIRGAS2000'});
  assert.deepEqual(M.montarOpcoes({...semPopulacao, base: {todos: true, estados: [], ids: []}}, 'distribuicao'),
    {competencia: '2024', categoria: 'ENFERMAGEM', nivel: 'municipios', indicador: 'quantidade',
      base: {municipios: {todos: true, estados: [], ids: []}}, premissas: {count_unit: 'pessoas', crs: 'SIRGAS2000'}});
  // Com população, a densidade; na base do Brasil, nenhuma premissa vai ao motor (o perfil oficial vale sozinho).
  assert.equal(M.definicaoInicial({tipo: 'arquivo', periodos: ['2024'], categoria: 'X', temGrupos: false, temPopulacao: true}).indicador,
    'densidade');
  assert.deepEqual(M.definicaoInicial({tipo: 'brasil', periodos: ['202406'], categoria: 'MEDICINA', temGrupos: true,
    premissas: {crs: 'SIRGAS2000'}}).premissas, {});
});

test('comando da conversa: grupos e referência por critério (a lista abre nessa ordem; a escolha é da pessoa)', () => {
  const c = {periodos: ['202306', '202406'], nomes: new Map(), temGrupos: true,
    disponivel: f => M.disponibilidadeDaFamilia(f, {fonte: 'brasil', nivel: 'municipios', disponibilidade: null, temIdentificador: false, rotulos: BR})};
  const def = definicao({nivel: 'municipios', base: {todos: false, estados: ['13'], ids: []}});
  const quintis = M.aplicarPedido(def, {grupos: {tipo: 'quintis'}}, c);
  assert.deepEqual(quintis.definicao.agrupar, {tipo: 'quintis', faixas: []});
  assert.equal(quintis.definicao.familia, 'distribuicao');
  assert.equal(quintis.criterio, null);
  assert.deepEqual(M.aplicarPedido(quintis.definicao, {grupos: {tipo: 'nenhum'}}, c).definicao.agrupar, {tipo: 'nenhum', faixas: []});
  assert.deepEqual(M.aplicarPedido(def, {grupos: {tipo: 'tercis'}}, c).mensagens, ['Os grupos pedidos não foram reconhecidos.']);
  const porCriterio = M.aplicarPedido(def, {referencia: {membros: [], criterio: {atributo: 'densidade', ordem: 'desc'}}}, c);
  assert.deepEqual(porCriterio.criterio, {atributo: 'densidade', ordem: 'desc'});
  assert.equal(porCriterio.abrir, 'referencia');
  assert.equal(porCriterio.definicao.familia, 'espacial');
  assert.equal(porCriterio.definicao.referencia, null);  // nenhuma referência é escolhida no lugar da pessoa
  assert.equal(M.aplicarPedido(def, {referencia: {membros: [], criterio: {atributo: 'x', ordem: 'desc'}}}, c).abrir, null);
});

test('cliente do motor: a resposta no formato do motor (empate, condições por estado, limites em texto, comparação por ids)', () => {
  const tefe = {id: 'code:130420', tipo: 'municipio', rotulo: 'TEFE (AM)', uf: 'AM', populacao: 79278, quantidade: 69,
    densidade: 0.8703549534549307, distancia_km: 521.2473967291248, inicial: {...VAZIO}, variacao_percentual: {...VAZIO},
    avaliavel: {densidade: true, distancia: true, variacao: null}, motivos: [], referencia: false, grupo_territorial: '13',
    referencia_mais_proxima: {id: 'code:130260', rotulo: 'MANAUS (AM)',
      empate: [{id: 'code:130260', rotulo: 'MANAUS (AM)'}, {id: 'code:130185', rotulo: 'IRANDUBA (AM)'}]},
    tendencia: {classe: 'SEM_CLASSIFICACAO', familia: 'NENHUMA', rotulo: 'Sem classificação', motivo: 'MUDANCA_DE_DIRECAO',
      motivo_texto: 'Mudança de direção', avaliavel: true,
      observacoes: [{competencia: '202306', valor: 0.91}, {competencia: '202406', valor: 0.87}], velocidades: [-0.0034]},
    grupo: {indice: 3, rotulo: '3º quartil'},
    condicoes: {situacao: 'ATENDE', por_condicao: [{estado: 'ATENDE', valor: 0.87, motivos: []},
      {estado: 'NAO_AVALIAVEL', valor: null, motivos: ['SEM_INFORMACAO_ESPACIAL']}]},
    ordem: {posicao: 28, selecionado: false}};
  const r = A.normalizarResposta({competencia: '202406', categoria: 'MEDICINA', nivel: 'municipios', itens: [tefe],
    faixas: {atributo: 'densidade', capacidade: 'CAP-DIS-03', limites: ['0', '0.5', '1000'], convencao: '[a, b)',
      rotulos: ['0 a <0,5', '0,5 a 1000'], contagens: [10, 52], fora: 0, nao_avaliaveis: 0, universo: 62},
    condicoes: {contagens: {ATENDE: 37, NAO_ATENDE: 25, NAO_AVALIAVEL: 0}, universo: 62, combinacao: 'E', descricao: '(…)',
      definicao: [{atributo: 'densidade', operador: '<', valor: 1, texto: 'densidade < 1 por 1.000 habitantes'},
        {atributo: 'distancia_km', operador: '>', valor: 150, texto: 'distância à referência mais próxima > 150 km'}]},
    comparacao: {indicador: 'densidade', itens: [
      {id: 'code:130260', rotulo: 'MANAUS (AM)', tipo: 'municipio', valor: 2.07, avaliavel: true, motivos: []},
      {id: 'code:130420', rotulo: 'TEFE (AM)', tipo: 'municipio', valor: 0.87, avaliavel: true, motivos: []}],
      maior: ['code:130260'], menor: ['code:130420'],
      diferencas: [{a: 'code:130260', b: 'code:130420', relacao: 'MAIOR', diferenca: 1.2}], relacoes: [],
      notas: ['Entre dois objetos: A e B em ordem de nome, relação A/B e diferença assinada A − B.']},
    tendencia: {desfecho: 'RES-VAL', bloqueio: null, nao_avaliaveis: 0, contagens: {SEM_CLASSIFICACAO: 1}, familias: {NENHUMA: 1},
      unidade_tempo: 'mês', janela: {periodos: ['202306', '202406'], inicio: '202306', fim: '202406'}}});
  const item = r.itens[0];
  // O empate lista todos os membros à mesma menor distância, o primeiro incluído: cada um aparece uma vez.
  assert.deepEqual(item.referencia_mais_proxima, [{id: 'code:130260', rotulo: 'MANAUS (AM)'}, {id: 'code:130185', rotulo: 'IRANDUBA (AM)'}]);
  assert.deepEqual(item.condicoes.porCondicao, [{texto: 'densidade < 1 por 1.000 habitantes', situacao: 'ATENDE'},
    {texto: 'distância à referência mais próxima > 150 km', situacao: 'NAO_AVALIAVEL'}]);
  assert.equal(item.tendencia.motivo, 'Mudança de direção (MUDANCA_DE_DIRECAO)');
  assert.equal(item.tendencia.familia, 'NENHUMA');
  assert.deepEqual(item.ordem, {posicao: 28});
  assert.deepEqual(r.faixas.limites, [0, 0.5, 1000]);
  assert.deepEqual(r.faixas.contagens, [10, 52]);
  assert.deepEqual(r.condicoes.textos, ['densidade < 1 por 1.000 habitantes', 'distância à referência mais próxima > 150 km']);
  assert.deepEqual(r.comparacao, {itens: ['code:130260', 'code:130420'], linhas: [{atributo: 'densidade',
    maior: [{id: 'code:130260', rotulo: 'MANAUS (AM)', valor: 2.07}], menor: [{id: 'code:130420', rotulo: 'TEFE (AM)', valor: 0.87}],
    diferencas: [{entre: ['code:130260', 'code:130420'], valor: 1.2, texto: null}]}],
    textos: ['Entre dois objetos: A e B em ordem de nome, relação A/B e diferença assinada A − B.']});
  assert.deepEqual(r.tendencia.janela, ['202306', '202406']);
});
