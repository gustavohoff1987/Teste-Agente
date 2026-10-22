import {readFileSync} from 'node:fs';
import {test} from 'node:test';
import assert from 'node:assert/strict';
import ts from 'typescript';
async function source(name) {
  const code = ts.transpileModule(readFileSync(new URL('../src/' + name + '.ts', import.meta.url), 'utf8'),
    {compilerOptions: {module: ts.ModuleKind.ESNext, target: ts.ScriptTarget.ES2022}}).outputText;
  return import('data:text/javascript;base64,' + Buffer.from(code).toString('base64'));
}
const M = await source('painelModel');

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
});

test('números com unidade; casas aumentadas quando o valor pareceria igual ao limite da régua', () => {
  assert.equal(M.formatarNumero(4730, true), '4.730');
  assert.equal(M.formatarNumero(0.70584), '0,71');
  assert.equal(M.formatarNumero(1.2041, false, [1.2]), '1,204');
  assert.equal(M.formatarNumero(1.2, false, [1.2]), '1,20');
  assert.equal(M.formatarIndicador(0.70584, 'densidade'), '0,71 por 1.000 habitantes');
  assert.equal(M.formatarIndicador(52, 'quantidade'), '52 profissionais');
  assert.equal(M.formatarIndicador(null, 'densidade'), 'Não avaliável');
  assert.equal(M.exibirCompetencia('202406'), '06/2024');
  assert.equal(M.compacto(2000000), '2 mi');
  assert.equal(M.compacto(1500), '1,5 mil');
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
  assert.deepEqual(M.legendaDeTamanhos(1000, 30).map(item => item.valor), [1000, 200, 20]);
  assert.deepEqual(M.legendaDeTamanhos(0, 30), []);
});

test('não avaliáveis à parte, com o motivo do motor, na ordem do código territorial; variação vazia continua bolha', () => {
  const {plotaveis, fora} = M.separarItens([...ITENS].reverse(), 'densidade', true, true);
  assert.deepEqual(plotaveis.map(item => item.id), ['code:130260', 'code:130340', 'code:130420', 'c1']);
  assert.deepEqual(fora.map(item => [item.id, item.aspecto]), [['code:130185', 'indicador'], ['code:130340', 'variacao'], ['code:350010', 'distancia']]);
  assert.equal(fora[0].motivo, SEM_REGISTRO);
  assert.equal(fora[1].motivo, BASE_ZERO);
  assert.equal(fora[2].motivo, SEM_COORDENADA);
  const semDistancia = M.separarItens(ITENS, 'densidade', false, false);
  assert.ok(semDistancia.plotaveis.some(item => item.id === 'code:350010'));
  assert.deepEqual(semDistancia.fora.map(item => item.id), ['code:130185']);
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
  assert.deepEqual(M.motivosDe(ITENS[4], 'distancia'), [SEM_REGISTRO]);  // sem registro vale para todos os aspectos
  assert.deepEqual(M.motivosDe(ITENS[2], 'distancia'), []);
  const parcial = {...ITENS[5], motivos: [PARCIAL, 'Distância não avaliável em junho de 2024: sem coordenada válida em MANACAPURU (AM) ' +
    '(DEPENDENCIA_NAO_AVALIAVEL)']};
  assert.deepEqual(M.avisosDe(parcial), [PARCIAL]);
  assert.deepEqual(M.motivosDe(parcial, 'distancia'), [parcial.motivos[1]]);
  assert.deepEqual(M.motivosDe(parcial, 'indicador'), []);  // o aviso não é motivo de valor não avaliável
  const dica = M.montarDica(parcial, {indicador: 'densidade', competencia: '202406', competenciaInicial: null, distancia: true,
    crescimento: false, nomes: new Map()});
  assert.ok(dica.notas.includes(PARCIAL));
  assert.equal(M.textoDaLimitacao('SOMA_COM_POSSIVEL_DUPLA_CONTAGEM'), 'Conjuntos: soma das contagens dos componentes, com possível dupla contagem.');
  assert.equal(M.textoDaLimitacao('CODIGO_NOVO'), 'Limitação registrada pelo motor: CODIGO_NOVO.');
});

test('régua: limites incluídos, só municípios base; conjuntos e referência sempre à vista; passos redondos', () => {
  const visiveis = corte => ITENS.filter(item => M.noCorte(item, 'densidade', corte)).map(item => item.id);
  assert.deepEqual(visiveis(null), ITENS.map(item => item.id));
  assert.deepEqual(visiveis({minimo: 3, maximo: 5}), ['code:130260', 'code:130420', 'code:130340', 'c1']);
  assert.deepEqual(visiveis({minimo: 3.5, maximo: 15}), ['code:130260', 'code:130420', 'code:350010', 'c1']);
  assert.equal(M.corteAtivo(null, [3, 15]), false);
  assert.equal(M.corteAtivo({minimo: 3, maximo: 15}, [3, 15]), false);
  assert.equal(M.corteAtivo({minimo: 4, maximo: 15}, [3, 15]), true);
  assert.equal(M.passoDaRegua([0, 2.07], false), 0.05);
  assert.equal(M.passoDaRegua([5, 4732], true), 50);
  assert.equal(M.ajustarValor(1.2345, [0, 2.07], 'linear', false), 1.25);
  assert.equal(M.ajustarValor(0.05, [0.1234, 2.0713], 'linear', false), 0.1234);  // pontas exatas: todos à vista
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
  // Cometas (do valor inicial ao atual) também não se cruzam.
  const cometas = [{id: 'a', x0: 10, x1: 200, r: 6}, {id: 'b', x0: 150, x1: 60, r: 8}, {id: 'c', x0: 190, x1: 300, r: 5}];
  const y = M.arranjar(cometas);
  for (let i = 0; i < 3; i++) for (let j = i + 1; j < 3; j++) {
    const p = cometas[i], q = cometas[j];
    const lacuna = Math.max(0, Math.min(q.x0, q.x1) - Math.max(p.x0, p.x1), Math.min(p.x0, p.x1) - Math.max(q.x0, q.x1));
    assert.ok(Math.hypot(lacuna, y.get(p.id) - y.get(q.id)) >= p.r + q.r + 1.5 - 1e-6);
  }
});

test('modo leve: arranjo numa faixa de altura limitada, determinístico e sem custo quadrático', () => {
  assert.equal(M.LIMITE_LEVE, 400);
  // Com espaço na faixa, nenhuma bolha se sobrepõe (tolerância de uma célula da grade de 2 px).
  const poucas = Array.from({length: 30}, (_, i) => ({id: 'code:' + (200 + i), x0: 100 + (i % 6) * 4, x1: 100 + (i % 6) * 4, r: 4 + (i % 3)}));
  const a = M.arranjarDenso(poucas, 120), b = M.arranjarDenso([...poucas].reverse(), 120);
  assert.deepEqual([...a.entries()].sort(), [...b.entries()].sort());
  for (let i = 0; i < poucas.length; i++) for (let j = i + 1; j < poucas.length; j++) {
    const p = poucas[i], q = poucas[j];
    assert.ok(Math.hypot(p.x0 - q.x0, a.get(p.id) - a.get(q.id)) >= p.r + q.r - 3, p.id + ' x ' + q.id);
  }
  assert.ok([...a.values()].every(y => Math.abs(y) <= 120 && Math.abs(y % 2) === 0));
  // Milhares de bolhas: a altura não sai da faixa (com a faixa cheia, elas se sobrepõem, semitransparentes) e o cálculo
  // leva bem menos de 5 s (o arranjo exato levava mais de um minuto com 5.570 municípios).
  const muitas = Array.from({length: 5570}, (_, i) => ({id: 'code:' + (100000 + i), x0: 300 + (i % 250), x1: 300 + (i % 250) + (i % 7), r: 4 + (i % 4)}));
  const inicio = performance.now();
  const y = M.arranjarDenso(muitas, 150);
  assert.ok(performance.now() - inicio < 5000);
  assert.equal(y.size, muitas.length);
  assert.ok([...y.values()].every(valor => Math.abs(valor) <= 150));
  // No gráfico, o modo leve limita a altura do eixo único.
  const itens = Array.from({length: 600}, (_, i) => ({...ITENS[0], id: 'code:' + (300000 + i), densidade: (i % 50) / 10 + 0.1, populacao: 1000 + i}));
  const leve = M.montarGrafico({itens, dominios: {...DOMINIOS, densidade: [0.1, 5.1], populacao: [1000, 1600]}, indicador: 'densidade',
    escala: 'linear', distancia: false, crescimento: false, vista: 'final', largura: 860, limiteVariacao: 0, rotuloDistancia: '', denso: true});
  assert.ok(leve.altura <= 16 + 2 * 230 + 24 + 50 + 2 * 30, leve.altura);
  assert.equal(leve.bolhas.length, 600);
});

test('eixo único do indicador: X pelo valor do motor, altura só arranjo, raio pela população', () => {
  const itens = ITENS.slice(0, 4);
  const g = M.montarGrafico({itens, dominios: DOMINIOS, indicador: 'densidade', escala: 'linear', distancia: false, crescimento: false,
    vista: 'final', largura: 800, limiteVariacao: 0, rotuloDistancia: ''});
  assert.equal(g.eixoY, null);
  assert.equal(g.eixoX.tipo, 'densidade');
  assert.deepEqual(g.eixoX.dominio, [0, 15]);
  assert.deepEqual(g.eixoX.marcas.map(marca => marca.valor), [0, 5, 10, 15]);
  const x = id => g.bolhas.find(bolha => bolha.id === id).x;
  assert.ok(x('code:130340') < x('code:130420') && x('code:130420') < x('code:350010') && x('code:350010') < x('code:130260'));
  assert.equal(g.bolhas.find(bolha => bolha.id === 'code:350010').r, g.raioMax);
  assert.ok(g.bolhas.every(bolha => bolha.cor === M.COR_BOLHA && !bolha.rastro && bolha.visivel));
  for (const p of g.bolhas) for (const q of g.bolhas) if (p.id < q.id) assert.ok(Math.hypot(p.x - q.x, p.y - q.y) >= p.r + q.r);
  const quantidade = M.montarGrafico({itens, dominios: DOMINIOS, indicador: 'quantidade', escala: 'linear', distancia: false,
    crescimento: false, vista: 'final', largura: 800, limiteVariacao: 0, rotuloDistancia: ''});
  assert.equal(quantidade.eixoX.tipo, 'quantidade');
  assert.deepEqual(quantidade.eixoX.dominio, [0, 125]);
  const log = M.montarGrafico({itens, dominios: {...DOMINIOS, quantidade: [10, 105]}, indicador: 'quantidade', escala: 'logaritmica', distancia: false,
    crescimento: false, vista: 'final', largura: 800, limiteVariacao: 0, rotuloDistancia: ''});
  assert.equal(log.eixoX.escala, 'logaritmica');
  assert.deepEqual(log.eixoX.dominio, [10, 200]);
});

test('com distância: X = distância até a referência, Y = indicador; conjunto com a faixa do membro mais próximo ao mais distante', () => {
  const itens = M.separarItens(ITENS, 'densidade', true, false).plotaveis;
  const g = M.montarGrafico({itens, dominios: DOMINIOS, indicador: 'densidade', escala: 'linear', distancia: true, crescimento: false,
    vista: 'final', largura: 800, limiteVariacao: 0, rotuloDistancia: 'Distância até a referência (km)'});
  assert.equal(g.eixoX.tipo, 'distancia');
  assert.equal(g.eixoX.rotulo, 'Distância até a referência (km)');
  assert.equal(g.eixoY.tipo, 'densidade');
  const bolha = id => g.bolhas.find(item => item.id === id);
  assert.ok(bolha('code:130260').x < bolha('code:130340').x && bolha('code:130340').x < bolha('code:130420').x);
  assert.ok(bolha('code:130260').y < bolha('code:130420').y);  // densidade maior, mais acima
  assert.ok(bolha('code:130260').referencia);
  assert.ok(Math.abs(bolha('c1').x + bolha('c1').faixa.dx - bolha('code:130420').x) < 1e-9);
});

test('crescimento: cometa só entre os dois valores observados, cor divergente e vista da competência inicial', () => {
  const itens = M.separarItens(ITENS, 'densidade', false, true).plotaveis;
  const limite = M.limiteDaVariacao({dominios: DOMINIOS}, 'densidade', itens);
  assert.equal(limite, 214.29);
  const g = M.montarGrafico({itens, dominios: DOMINIOS, indicador: 'densidade', escala: 'linear', distancia: false, crescimento: true,
    vista: 'final', largura: 800, limiteVariacao: limite, rotuloDistancia: ''});
  const bolha = id => g.bolhas.find(item => item.id === id);
  assert.ok(bolha('code:130260').rastro.dx < 0 && bolha('code:130260').rastro.dy === 0);  // cresceu: veio da esquerda
  assert.equal(bolha('code:130340').rastro, null);  // variação não avaliável: sem rastro, bolha vazada
  assert.equal(bolha('code:130340').vazada, true);
  assert.equal(bolha('code:130340').cor, '#ffffff');
  assert.notEqual(bolha('code:350010').cor, M.COR_NEUTRA);  // +2,94%: sinal visível
  const inicial = M.montarGrafico({itens, dominios: DOMINIOS, indicador: 'densidade', escala: 'linear', distancia: false, crescimento: true,
    vista: 'inicial', largura: 800, limiteVariacao: limite, rotuloDistancia: ''});
  const antes = id => inicial.bolhas.find(item => item.id === id);
  assert.ok(Math.abs(antes('code:130260').x - (bolha('code:130260').x + bolha('code:130260').rastro.dx)) < 1e-9);
  assert.equal(antes('code:130260').y, bolha('code:130260').y);  // a faixa do cometa não muda entre as vistas
  assert.equal(antes('code:130340').visivel, false);  // sem variação avaliável, sem posição na competência inicial
  assert.equal(M.corDaVariacao(0, 40), M.COR_NEUTRA);
  // Escala pela raiz quadrada (22/10/2026): o meio de cada braço vale um quarto do limite.
  assert.equal(M.corDaVariacao(10, 40), M.RAMPA_CRESCIMENTO[1]);
  assert.equal(M.corDaVariacao(-10, 40), M.RAMPA_QUEDA[1]);
  assert.notEqual(M.corDaVariacao(2, 40), M.RAMPA_CRESCIMENTO[0]);  // pequena, mas já com mais cor que o tom claro inicial
  assert.equal(M.corDaVariacao(40, 40), M.RAMPA_CRESCIMENTO[2]);
  assert.equal(M.corDaVariacao(-80, 40), M.RAMPA_QUEDA[2]);
  assert.equal(M.caudaDoCometa(-100, 0, 10), '-100,0 0,-6 0,6');
  assert.equal(M.caudaDoCometa(0, 0.5, 10), '');
});

test('conjunto rotulado como soma das contagens dos componentes, com possível dupla contagem (RQ-REP-14)', () => {
  const conjunto = ITENS[5];
  assert.equal(M.textoDaContagem(conjunto.contagem), 'soma das contagens dos componentes, com possível dupla contagem');
  const dica = M.montarDica(conjunto, {indicador: 'densidade', competencia: '202406', competenciaInicial: '202306', distancia: true,
    crescimento: true, nomes: new Map([['code:130420', 'TEFE (AM)'], ['code:130340', 'PARINTINS (AM)']])});
  assert.equal(dica.subtitulo, 'Conjunto de municípios · soma das contagens dos componentes, com possível dupla contagem');
  assert.ok(dica.notas.some(nota => nota.includes('possível dupla contagem')));
  assert.ok(dica.notas.includes('Membros: TEFE (AM), PARINTINS (AM).'));
  assert.deepEqual(dica.linhas.find(linha => linha.rotulo.startsWith('Variação da densidade')),
    {rotulo: 'Variação da densidade desde 06/2023', valor: '+214,29%'});
  assert.deepEqual(dica.linhas.find(linha => linha.rotulo === 'Distância (membro mais distante)'), {rotulo: 'Distância (membro mais distante)', valor: '523,14 km'});
  assert.ok(!JSON.stringify(dica).includes('pessoas únicas') && !JSON.stringify(dica).includes('profissionais distintos'));
  const tefe = M.montarDica(ITENS[1], {indicador: 'densidade', competencia: '202406', competenciaInicial: null, distancia: true,
    crescimento: false, nomes: new Map()});
  assert.equal(tefe.titulo, 'TEFE (AM)');
  assert.equal(tefe.subtitulo, 'Município · AM');
  assert.deepEqual(tefe.linhas.map(linha => linha.valor), ['2.000 habitantes', '10', '5,00 por 1.000 habitantes', '523,14 km']);
  const novo = M.novoConjunto([{id: 'c1', rotulo: 'Interior', membros: []}], ['code:1', 'code:2', 'code:1'], '  ');
  assert.deepEqual(novo, {id: 'c2', rotulo: 'Conjunto 2', membros: ['code:1', 'code:2']});
});

test('"Usar o primeiro": a 1ª posição do motor; com empate, todos os empatados para a escolha', () => {
  assert.deepEqual(M.primeirosColocados([{id: 'a', posicao: 1}, {id: 'b', posicao: 1}, {id: 'c', posicao: 3}]).map(item => item.id), ['a', 'b']);
  assert.deepEqual(M.primeirosColocados([{id: 'a', posicao: 1}, {id: 'b', posicao: 2}]).map(item => item.id), ['a']);
  assert.deepEqual(M.primeirosColocados([{id: 'a', posicao: null}]), []);
});

test('pedido ao motor com os nomes do contrato; universo normalizado e competências', () => {
  assert.deepEqual(M.normalizarBase({todos: false, estados: ['35', '13', '13'], ids: ['code:130260', 'code:290070', 'code:290070']}),
    {todos: false, estados: ['13', '35'], ids: ['code:290070']});
  assert.deepEqual(M.normalizarBase({todos: true, estados: ['13'], ids: ['code:1']}), {todos: true, estados: [], ids: []});
  assert.deepEqual(M.baseInicial({todos: false, grupos: []}, [], 62), {todos: true, estados: [], ids: []});
  // Sem escolha, todos os municípios, também na base com milhares (22/10/2026: página principal com o Brasil inteiro).
  assert.deepEqual(M.baseInicial({todos: false, grupos: []}, [], 5570), {todos: true, estados: [], ids: []});
  assert.deepEqual(M.baseInicial({todos: false, grupos: []}, [], 0), {todos: false, estados: [], ids: []});
  assert.deepEqual(M.baseInicial({todos: false, grupos: ['13']}, ['code:130260', 'code:350010'], 5570),
    {todos: false, estados: ['13'], ids: ['code:350010']});
  const completo = M.montarOpcoes({competencia: '202406', competenciaInicial: '202006', categoria: 'MEDICINA',
    base: {todos: false, estados: ['13'], ids: []}, conjuntos: [{id: 'c1', rotulo: 'Manaus e entorno', membros: ['code:130260', 'code:130185']}],
    referencia: {membros: ['code:130260'], criterio: {atributo: 'densidade', ordem: 'desc'}}});
  assert.deepEqual(completo, {competencia: '202406', categoria: 'MEDICINA', base: {municipios: {todos: false, estados: ['13'], ids: []}},
    competencia_inicial: '202006', conjuntos: [{id: 'c1', rotulo: 'Manaus e entorno', membros: ['code:130260', 'code:130185']}],
    referencia: {membros: ['code:130260'], criterio: {atributo: 'densidade', ordem: 'desc'}}});
  const minimo = M.montarOpcoes({competencia: '202406', competenciaInicial: '', categoria: 'MEDICINA', base: {todos: true, estados: [], ids: []},
    conjuntos: [], referencia: null});
  assert.deepEqual(Object.keys(minimo).sort(), ['base', 'categoria', 'competencia']);
  // Base vazia vale com conjunto (o motor aceita); sem os dois, nada é pedido. O universo da lista vai no critério da referência.
  const conjunto = {id: 'c1', rotulo: 'Interior', membros: ['code:130420', 'code:130340']};
  const vazia = {todos: false, estados: [], ids: []};
  assert.equal(M.semPedido(vazia, []), true);
  assert.equal(M.semPedido(vazia, [conjunto]), false);
  assert.equal(M.semPedido({todos: true, estados: [], ids: []}, []), false);
  const referencia = {membros: ['code:130260'], criterio: {atributo: 'densidade', ordem: 'desc', universo: {municipios: {todos: true, estados: [], ids: []}}}};
  assert.deepEqual(M.montarOpcoes({competencia: '202406', competenciaInicial: '', categoria: 'MEDICINA', base: vazia, conjuntos: [conjunto], referencia}),
    {competencia: '202406', categoria: 'MEDICINA', base: {municipios: vazia}, conjuntos: [conjunto], referencia});
  const periodos = ['202406', '202301', '202306', '202401'];
  assert.equal(M.maisRecente(periodos), '202406');
  assert.deepEqual(M.anteriores(periodos, '202406'), ['202301', '202306', '202401']);
  assert.equal(M.inicialSugerida(periodos, '202406'), '202306');
  assert.equal(M.inicialSugerida(['202401', '202406'], '202406'), '202401');
  assert.equal(M.inicialSugerida(['202406'], '202406'), '');
});

test('tabela: ordem do código territorial por padrão; reordenar é pedido do usuário, sem valor por último', () => {
  const itens = ITENS.slice(0, 4);
  assert.deepEqual(M.ordenarTabela([...itens].reverse(), null, 'densidade').map(item => item.id),
    ['code:130260', 'code:130340', 'code:130420', 'code:350010']);
  assert.deepEqual(M.ordenarTabela(itens, {coluna: 'variacao', sentido: 'desc'}, 'densidade').map(item => item.id),
    ['code:130420', 'code:130260', 'code:350010', 'code:130340']);
  assert.deepEqual(M.ordenarTabela(itens, {coluna: 'densidade', sentido: 'asc'}, 'densidade').map(item => item.id),
    ['code:130340', 'code:130420', 'code:350010', 'code:130260']);
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
