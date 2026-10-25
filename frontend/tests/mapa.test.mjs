import {readFileSync} from 'node:fs';
import {test} from 'node:test';
import assert from 'node:assert/strict';
import ts from 'typescript';

// Mapa da página única (23/10/2026): modelo puro do desenho (mapaModel.ts). Projeção só para desenhar, enquadramento nos
// itens e o inicial com contexto, tamanho com área proporcional, cor contínua linear e logarítmica (nunca automática), pintura
// pela camada ou pelos quintis do motor, marcas da legenda, esmaecidos (fora da régua, nunca somem), alvo do clique, nomes sem
// sobreposição, ligações, mapinha e transição entre as vistas.
async function source(name) {
  const code = ts.transpileModule(readFileSync(new URL('../src/' + name + '.ts', import.meta.url), 'utf8'),
    {compilerOptions: {module: ts.ModuleKind.ESNext, target: ts.ScriptTarget.ES2022}}).outputText;
  return import('data:text/javascript;base64,' + Buffer.from(code).toString('base64'));
}
const M = await source('mapaModel');

const perto = (a, b, tolerancia = 1e-9) => Math.abs(a - b) <= tolerancia;
const item = (id, extra = {}) => ({id, tipo: 'municipio', rotulo: id.toUpperCase() + ' (AM)', uf: 'AM', populacao: null, quantidade: null,
  densidade: null, distancia_km: null, motivos: [], referencia: false, ...extra});

test('projeção só para desenhar: longitude × cosseno da latitude média, y = −latitude; coordenada inválida fica de fora', () => {
  const pontos = new Map([['a', [-10, -60]], ['b', [-50, -40]], ['c', [95, 10]], ['d', [Number.NaN, 1]]]);
  const p = M.projetar(pontos);
  assert.deepEqual(p.ids, ['a', 'b']);
  assert.ok(perto(p.k, Math.cos(30 * Math.PI / 180)));
  assert.ok(perto(p.x[0], -60 * p.k));
  assert.equal(p.y[0], 10);
  assert.equal(p.y[1], 50);
  assert.equal(p.indice.get('b'), 1);
  assert.equal(p.indice.has('c'), false);
  assert.equal(M.coordenadaValida(-3.1, -60.02), true);
  assert.equal(M.coordenadaValida(91, 0), false);
  assert.equal(M.coordenadaValida(0, 181), false);
});

test('enquadramento nos pontos dos itens, com folga; um ponto só não vira zoom extremo; tela e mundo são inversos', () => {
  const p = M.projetar(new Map([['a', [-10, -60]], ['b', [-50, -40]]]));
  const limites = M.limitesDe(p, [0, 1]);
  assert.ok(limites);
  const v = M.enquadrar(limites, 400, 300);
  assert.ok(perto(v.escala, 236 / 40));  // a altura (40° de latitude) limita: (300 − 2 × 32) / 40
  for (const i of [0, 1]) {
    const [x, y] = M.paraTela(p.x[i], p.y[i], v, 400, 300);
    assert.ok(x >= 32 - 1e-6 && x <= 400 - 32 + 1e-6 && y >= 32 - 1e-6 && y <= 300 - 32 + 1e-6, 'ponto dentro da folga');
    const [wx, wy] = M.paraMundo(x, y, v, 400, 300);
    assert.ok(perto(wx, p.x[i], 1e-6) && perto(wy, p.y[i], 1e-6));
  }
  const unico = M.enquadrar(M.limitesDe(p, [0]), 400, 300);
  assert.ok(perto(unico.escala, Math.min(336 / M.VAO_MINIMO, 236 / M.VAO_MINIMO)), 'vão mínimo de ' + M.VAO_MINIMO + '°');
  assert.equal(M.limitesDe(p, []), null);
  assert.deepEqual(M.enquadrar(null, 400, 300), {cx: 0, cy: 0, escala: 1});
});

test('enquadramento inicial com contexto: margem em volta dos itens, ao menos um quarto da fonte e nunca mais que ela; sem escala fixa', () => {
  const todos = {minX: 0, maxX: 100, minY: 0, maxY: 80};
  // Um ponto só (um município): um quarto da extensão da fonte em cada direção, centrado nele.
  assert.deepEqual(M.limitesComContexto({minX: 50, maxX: 50, minY: 40, maxY: 40}, todos), {minX: 37.5, maxX: 62.5, minY: 30, maxY: 50});
  // Uma região maior: 25% do vão de margem de cada lado.
  assert.deepEqual(M.limitesComContexto({minX: 10, maxX: 50, minY: 10, maxY: 50}, todos), {minX: 0, maxX: 60, minY: 0, maxY: 60});
  // Toda a fonte: a vista de sempre, a fonte inteira.
  assert.deepEqual(M.limitesComContexto(todos, todos), todos);
  // Sem os itens ou sem a fonte, o que houver.
  assert.deepEqual(M.limitesComContexto(null, todos), todos);
  const itens = {minX: 1, maxX: 2, minY: 1, maxY: 2};
  assert.deepEqual(M.limitesComContexto(itens, null), itens);
  assert.equal(M.limitesComContexto(null, null), null);
  // Proporcional à extensão da fonte, qualquer que seja (uma planilha de outra região dá a mesma vista relativa).
  const k = 0.01, r = M.limitesComContexto({minX: 50 * k, maxX: 50 * k, minY: 40 * k, maxY: 40 * k}, {minX: 0, maxX: 100 * k, minY: 0, maxY: 80 * k});
  assert.ok(perto(r.minX, 0.375, 1e-12) && perto(r.maxX, 0.625, 1e-12) && perto(r.minY, 0.3, 1e-12) && perto(r.maxY, 0.5, 1e-12), JSON.stringify(r));
  // A vista com contexto é mais afastada que o enquadramento só nos itens.
  const soItens = M.enquadrar({minX: 10, maxX: 50, minY: 10, maxY: 50}, 400, 300);
  const comContexto = M.enquadrar(M.limitesComContexto({minX: 10, maxX: 50, minY: 10, maxY: 50}, todos), 400, 300);
  assert.ok(comContexto.escala < soItens.escala);
  assert.equal(M.MARGEM_DE_CONTEXTO, 0.25);
  assert.equal(M.CONTEXTO_MINIMO, 0.25);
});

test('enquadramento com os territórios de referência (25/10/2026): a mira fora do resultado entra no quadro inicial', () => {
  const projecao = M.projetar(new Map([['rr1', [2.8, -60.7]], ['rr2', [3.4, -61.0]], ['am1', [-2.0, -60.0]], ['sp', [-23.5, -46.6]]]));
  const base = M.baseDoMapa([item('rr1'), item('rr2')], projecao);
  const so = M.limitesComReferencias(projecao, base, []);
  assert.deepEqual(so, M.limitesDe(projecao, base.pontos.map(ponto => ponto.indice)));  // sem referência, os mesmos limites dos itens
  const com = M.limitesComReferencias(projecao, base, ['am1', 'fora-da-fonte']);
  const am = projecao.indice.get('am1');
  assert.ok(com.maxY >= projecao.y[am] && com.minY <= so.minY && com.maxY > so.maxY, JSON.stringify([so, com]));
  assert.equal(com.minX, so.minX);  // a referência fica na mesma faixa de longitude: o quadro só cresce para o sul
  assert.equal(M.limitesComReferencias(projecao, {pontos: []}, ['sp']).minX, projecao.x[projecao.indice.get('sp')]);
});

test('zoom em torno do cursor (o ponto sob ele fica no lugar), preso aos limites; arrasto e área à vista', () => {
  const v = {cx: 5, cy: 2, escala: 10};
  const ampliada = M.zoomEm(v, 2, 100, 80, 400, 300, {min: 1, max: 1000});
  assert.equal(ampliada.escala, 20);
  const [ax, ay] = M.paraMundo(100, 80, v, 400, 300), [bx, by] = M.paraMundo(100, 80, ampliada, 400, 300);
  assert.ok(perto(ax, bx) && perto(ay, by));
  assert.equal(M.zoomEm(v, 1000, 0, 0, 400, 300, {min: 1, max: 50}).escala, 50);
  assert.equal(M.zoomEm(v, 0.001, 0, 0, 400, 300, {min: 4, max: 50}).escala, 4);
  const arrastada = M.deslocar(v, 20, -10);
  assert.ok(perto(arrastada.cx, 3) && perto(arrastada.cy, 3));
  assert.deepEqual(M.areaVisivel({cx: 0, cy: 0, escala: 10}, 200, 100, 1), {lonMin: -10, lonMax: 10, latMax: 5, latMin: -5});
});

test('tamanho: área proporcional ao valor, raio máximo menor que o do gráfico e mínimo visível', () => {
  assert.equal(M.RAIO_MAXIMO_MAPA, 16);
  assert.equal(M.raioDeArea(100, 100), 16);
  assert.equal(M.raioDeArea(25, 100), 8);
  const [r64, r16] = [M.raioDeArea(64, 100), M.raioDeArea(16, 100)];
  assert.ok(perto((r64 / r16) ** 2, 4, 1e-9), 'quatro vezes o valor, quatro vezes a área');
  assert.equal(M.raioDeArea(400, 100), 16, 'acima do máximo da escala, preso no raio máximo');
  for (const valor of [0, -3, null, undefined, Number.NaN]) assert.equal(M.raioDeArea(valor, 100), M.RAIO_MINIMO_MAPA);
  assert.equal(M.raioDeArea(0.01, 100), M.RAIO_MINIMO_MAPA, 'valor muito pequeno fica no mínimo visível');
  assert.equal(M.raioDeArea(50, null), M.RAIO_MINIMO_MAPA);
  // Legenda: 1, 2 ou 5 × 10ⁿ abaixo do máximo, com o mesmo raio do desenho, todas na proporção exata (25/10/2026): a referência
  // que ficaria abaixo do mínimo visível (desenhada maior do que a área dela) dá lugar ao menor número redondo que o alcança.
  const marcas = M.marcasDeTamanho(12000000);
  assert.deepEqual(marcas.map(marca => marca.valor), [10000000, 2000000, 500000]);
  assert.ok(perto(marcas[0].raio, 16 * Math.sqrt(10 / 12), 1e-9));
  for (const marca of marcas) assert.ok(marca.raio > M.RAIO_MINIMO_MAPA && perto(marca.raio, 16 * Math.sqrt(marca.valor / 12000000), 1e-9), marca.valor);
  assert.deepEqual(M.marcasDeTamanho(470169).map(marca => marca.valor), [200000, 50000, 20000]);
  assert.deepEqual(M.marcasDeTamanho(null), []);
});

test('cor contínua: rampa de um tom, linear por padrão; logarítmica só por escolha e com domínio positivo; nunca automática', () => {
  assert.deepEqual([...M.RAMPA_CONTINUA], ['#86b6ef', '#5598e7', '#2a78d6', '#1c5cab', '#104281']);
  const dominio = [0, 100];
  assert.equal(M.corContinua(0, dominio, 'linear'), '#86b6ef');
  assert.equal(M.corContinua(25, dominio, 'linear'), '#5598e7');
  assert.equal(M.corContinua(50, dominio, 'linear'), '#2a78d6');
  assert.equal(M.corContinua(100, dominio, 'linear'), '#104281');
  assert.equal(M.corContinua(-5, dominio, 'linear'), '#86b6ef', 'fora do domínio, presa na ponta');
  assert.equal(M.corContinua(500, dominio, 'linear'), '#104281');
  // Logarítmica escolhida, domínio positivo: 100 fica no meio de 1 a 10.000.
  const positivo = [1, 10000];
  assert.equal(M.escalaEfetiva('logaritmica', positivo), 'logaritmica');
  assert.equal(M.corContinua(100, positivo, 'logaritmica'), '#2a78d6');
  assert.ok(perto(M.fracaoDeCor(10, [1, 100], 'logaritmica'), 0.5, 1e-12));
  assert.notEqual(M.corContinua(100, positivo, 'linear'), '#2a78d6', 'na linear, 100 fica perto da ponta clara');
  // Sem log automático: a linear vale mesmo com valores muito assimétricos; o log exige a escolha e o domínio positivo.
  assert.equal(M.escalaEfetiva('linear', [0.23, 81.07]), 'linear');
  assert.equal(M.escalaEfetiva(undefined, [0.23, 81.07]), 'linear');
  assert.equal(M.escalaEfetiva(null, [0.23, 81.07]), 'linear');
  assert.equal(M.escalaEfetiva('logaritmica', [0, 81.07]), 'linear');
  assert.equal(M.escalaEfetiva('logaritmica', [-2, 81.07]), 'linear');
  assert.equal(M.escalaEfetiva('logaritmica', null), 'linear');
  assert.equal(M.corContinua(5, [0, 10], 'logaritmica'), M.corContinua(5, [0, 10], 'linear'));
  assert.equal(M.corContinua(2, [0.23, 81.07], 'linear'), M.corNaRampa((2 - 0.23) / (81.07 - 0.23)));
  // Sem valor ou sem domínio: null (vazado, nunca zero); domínio de um só valor: o meio da rampa.
  assert.equal(M.corContinua(null, dominio, 'linear'), null);
  assert.equal(M.corContinua(Number.NaN, dominio, 'linear'), null);
  assert.equal(M.corContinua(5, null, 'linear'), null);
  assert.equal(M.corContinua(3, [3, 3], 'linear'), '#2a78d6');
  assert.equal(M.misturarCores('#000000', '#ffffff', 0.5), '#808080');
  assert.equal(M.gradienteDaRampa(), 'linear-gradient(to right, #86b6ef 0%, #5598e7 25%, #2a78d6 50%, #1c5cab 75%, #104281 100%)');
});

test('marcas da legenda: extremos do domínio e marcas de leitura (não limites de classe); marca do Brasil só de contexto', () => {
  assert.deepEqual(M.marcasDaLegenda([0, 100], 'linear'), [
    {valor: 0, posicao: 0, extremo: true}, {valor: 25, posicao: 0.25, extremo: false}, {valor: 50, posicao: 0.5, extremo: false},
    {valor: 75, posicao: 0.75, extremo: false}, {valor: 100, posicao: 1, extremo: true}]);
  // Logarítmica: 1, 2 e 5 × 10ⁿ; com muitas, só as potências de 10.
  const log = M.marcasDaLegenda([1, 1000], 'logaritmica');
  assert.deepEqual(log.map(marca => marca.valor), [1, 10, 100, 1000]);
  assert.ok(perto(log[1].posicao, 1 / 3, 1e-9));
  // Logarítmica pedida com zero no domínio: marcas da linear.
  assert.deepEqual(M.marcasDaLegenda([0, 100], 'logaritmica').map(marca => marca.valor), [0, 25, 50, 75, 100]);
  for (const marca of M.marcasDaLegenda([0.23, 81.07], 'linear').filter(marca => !marca.extremo))
    assert.ok(marca.posicao >= 0.12 && marca.posicao <= 0.88, 'marcas de leitura longe das pontas');
  assert.deepEqual(M.marcasDaLegenda([4, 4], 'linear'), [{valor: 4, posicao: 0.5, extremo: true}]);
  assert.deepEqual(M.marcasDaLegenda(null, 'linear'), []);
  assert.deepEqual(M.posicaoDoContexto(50, [0, 100], 'linear'), {posicao: 0.5, fora: false});
  assert.deepEqual(M.posicaoDoContexto(150, [0, 100], 'linear'), {posicao: 1, fora: true});
  assert.equal(M.posicaoDoContexto(null, [0, 100], 'linear'), null);
});

test('cena: unidades com coordenada viram ponto; estados e conjuntos não; fundo, membros e sem coordenada à parte', () => {
  const pontos = new Map([['m1', [-3, -60]], ['m2', [-4, -61]], ['m4', [-5, -62]]]);
  const itens = [item('m1', {populacao: 400}), item('m2', {populacao: 100}), item('m3', {populacao: 25}),
    item('uf:13', {tipo: 'estado'}), item('c1', {tipo: 'conjunto', membros: ['m1', 'm2', 'm9']})];
  const projecao = M.projetar(pontos);
  const base = M.baseDoMapa(itens, projecao);
  assert.deepEqual(base.pontos.map(ponto => ponto.item.id), ['m1', 'm2']);
  assert.deepEqual(base.semPonto, ['m3']);
  assert.deepEqual(base.fundo.map(i => projecao.ids[i]), ['m4']);
  assert.deepEqual(base.aneis.map(anel => anel.membro), ['m1', 'm2']);
  assert.equal(base.assinatura, M.assinaturaDe(['m1', 'm2']));
  assert.notEqual(M.assinaturaDe(['m1', 'm2']), M.assinaturaDe(['m1', 'm3']));
  assert.notEqual(M.assinaturaDe(['m1']), M.assinaturaDe(['m1', 'm2']));
});

test('cena: pintura da camada, dos quintis ou contínua; vazada nunca zero; os maiores atrás; esmaecidos no lugar, nunca somem', () => {
  const projecao = M.projetar(new Map([['m1', [-3, -60]], ['m2', [-4, -61]], ['m3', [-5, -62]]]));
  const base = M.baseDoMapa([item('m2', {populacao: 100}), item('m1', {populacao: 400}), item('m3', {populacao: null})], projecao);
  const entrada = {dentro: new Set(['m1', 'm2', 'm3']), pintura: 'camada', dominio: [0, 100], escala: 'linear', maximoTamanho: 400,
    tamanho: it => it.populacao, valorContinuo: it => ({m1: 50, m2: null, m3: 0})[it.id],
    pintar: it => it.id === 'm2' ? {cor: '#ffffff', vazada: true, apagada: false}
      : it.id === 'm3' ? {cor: '#c9c7bf', vazada: false, apagada: true} : {cor: '#008b9e', vazada: false, apagada: false}};
  const camada = M.montarCena(base, entrada);
  assert.deepEqual(camada.pontos.map(ponto => ponto.id), ['m1', 'm2', 'm3'], 'os maiores atrás (ordem de desenho)');
  assert.deepEqual(camada.pontos.map(ponto => ponto.r), [16, 8, M.RAIO_MINIMO_MAPA]);
  const porId = id => camada.pontos[camada.porId.get(id)];
  assert.equal(porId('m1').cor, '#008b9e');
  assert.equal(porId('m2').vazada, true);
  assert.equal(porId('m2').cor, M.MAPA_CORES.superficie, 'vazada: anel tracejado sobre a superfície, nunca preenchida como zero');
  assert.equal(porId('m3').apagada, true);
  assert.equal(camada.vazadas, 1);
  assert.equal(camada.esmaecidos, 0);
  // Contínua: o valor do motor no domínio; sem valor, vazada.
  const continua = M.montarCena(base, {...entrada, pintura: 'continua'});
  const c = id => continua.pontos[continua.porId.get(id)];
  assert.equal(c('m1').cor, '#2a78d6');
  assert.equal(c('m3').cor, '#86b6ef');
  assert.equal(c('m2').vazada, true);
  // Quintis do motor (sem a pergunta "Como pintar o mapa?"): pintados como uma camada, com a cor do grupo que a área entrega.
  const quintis = M.montarCena(base, {...entrada, pintura: 'quintis'});
  assert.deepEqual(quintis.pontos.map(ponto => [ponto.id, ponto.cor, ponto.vazada, ponto.apagada]),
    camada.pontos.map(ponto => [ponto.id, ponto.cor, ponto.vazada, ponto.apagada]));
  // Régua e filtros: quem fica fora esmaece, no mesmo lugar e no mesmo tamanho; ninguém some.
  const regua = M.montarCena(base, {...entrada, dentro: new Set(['m1'])});
  assert.equal(regua.pontos.length, 3);
  assert.equal(regua.esmaecidos, 2);
  assert.deepEqual(regua.pontos.filter(ponto => ponto.esmaecido).map(ponto => ponto.id).sort(), ['m2', 'm3']);
  assert.deepEqual(regua.pontos.map(ponto => ponto.r), camada.pontos.map(ponto => ponto.r));
  assert.equal(M.montarCena(base, {...entrada, dentro: new Set()}).esmaecidos, 3);
  // Sem máximo do motor, a escala usa o maior valor dos itens (só para o desenho).
  const semMaximo = M.montarCena(base, {...entrada, maximoTamanho: null});
  assert.equal(semMaximo.maximoTamanho, 400);
  assert.deepEqual(semMaximo.pontos.map(ponto => ponto.r), [16, 8, M.RAIO_MINIMO_MAPA]);
});

test('alvo do clique maior que o ponto (12 px no mouse, 18 px no toque); esmaecidos sem interação; na frente vence o empate', () => {
  assert.equal(M.ALVO_MOUSE, 12);
  assert.equal(M.ALVO_TOQUE, 18);
  const xs = [10, 100], ys = [10, 100], raios = [16, 3], todos = () => true;
  assert.equal(M.alvoMaisProximo(24, 10, xs, ys, raios, todos, M.ALVO_MOUSE), 0, 'dentro do raio de um ponto grande');
  assert.equal(M.alvoMaisProximo(114, 100, xs, ys, raios, todos, M.ALVO_MOUSE), -1);
  assert.equal(M.alvoMaisProximo(114, 100, xs, ys, raios, todos, M.ALVO_TOQUE), 1);
  assert.equal(M.alvoMaisProximo(100, 100, xs, ys, raios, i => i !== 1, M.ALVO_MOUSE), -1, 'esmaecido não responde');
  assert.equal(M.alvoMaisProximo(50, 50, [50, 50], [50, 50], [10, 3], todos, M.ALVO_MOUSE), 1, 'o desenhado por último (menor, na frente)');
});

test('teclado: o vizinho na direção pedida, no máximo a 60° do eixo', () => {
  const xs = [0, 10, -10, 0, 0, 20], ys = [0, 1, 0, 10, -10, 0], todos = () => true;
  assert.equal(M.vizinhoNaDirecao(0, 'direita', xs, ys, todos), 1);
  assert.equal(M.vizinhoNaDirecao(0, 'esquerda', xs, ys, todos), 2);
  assert.equal(M.vizinhoNaDirecao(0, 'baixo', xs, ys, todos), 3);
  assert.equal(M.vizinhoNaDirecao(0, 'cima', xs, ys, todos), 4);
  assert.equal(M.vizinhoNaDirecao(5, 'direita', xs, ys, todos), -1);
  assert.equal(M.vizinhoNaDirecao(0, 'direita', xs, ys, i => i !== 1), 5);
});

test('nomes junto aos pontos sem cobrir uns aos outros; o não obrigatório sem lugar não aparece', () => {
  const nomes = M.posicionarNomes([
    {id: 'a', x: 100, y: 100, r: 4, largura: 60, obrigatorio: true},
    {id: 'b', x: 100, y: 110, r: 4, largura: 60, obrigatorio: true},
    {id: 'c', x: 102, y: 105, r: 4, largura: 60, obrigatorio: false},
    {id: 'd', x: 300, y: 200, r: 4, largura: 60, obrigatorio: false},
  ], 400, 300, [{x0: 346, y0: 0, x1: 400, y1: 132}]);
  assert.ok(nomes.some(nome => nome.id === 'a') && nomes.some(nome => nome.id === 'b') && nomes.some(nome => nome.id === 'd'));
  const cruza = (p, q) => p.x0 < q.x1 && p.x1 > q.x0 && p.y0 < q.y1 && p.y1 > q.y0;
  for (const [i, p] of nomes.entries()) for (const q of nomes.slice(i + 1)) assert.ok(!cruza(p.caixa, q.caixa), p.id + ' e ' + q.id + ' se cobrem');
  for (const nome of nomes) assert.ok(nome.caixa.x0 >= 2 && nome.caixa.x1 <= 398 && nome.caixa.y0 >= 2 && nome.caixa.y1 <= 298);
  assert.deepEqual(M.posicionarNomes([{id: 'x', x: 40, y: 20, r: 3, largura: 200, obrigatorio: false}], 80, 40), []);
  const obrigatorio = M.posicionarNomes([{id: 'x', x: 40, y: 20, r: 3, largura: 200, obrigatorio: true}], 80, 40);
  assert.equal(obrigatorio.length, 1);
  assert.equal(obrigatorio[0].x, 4);
});

test('ligações ilustrativas: dos selecionados até a referência indicada, no máximo 30, sem ponto ligado a ele mesmo', () => {
  const temPonto = id => ['a', 'b', 'c', 'r1'].includes(id);
  assert.deepEqual(M.segmentosDasLigacoes([{de: 'a', para: ['r1', 'r2']}, {de: 'b', para: ['b']}, {de: 'c', para: ['r1', 'r1']},
    {de: 'x', para: ['r1']}], temPonto), [{de: 'a', para: 'r1'}, {de: 'c', para: 'r1'}]);
  const muitas = Array.from({length: 40}, (_, i) => ({de: 'u' + i, para: ['r']}));
  assert.equal(M.segmentosDasLigacoes(muitas, () => true).length, M.MAX_LIGACOES);
  assert.equal(M.MAX_LIGACOES, 30);
});

test('mapinha: um quadradinho por pixel ocupado; retângulo da área à vista preso às bordas e com tamanho mínimo', () => {
  const pontos = new Map([['a', [-10, -50]], ['b', [-10, -50]], ['c', [-20, -40]]]);
  const geo = M.geometriaDoMiniMapa(pontos, 120);
  assert.equal(geo.largura, 120);
  assert.equal(geo.ocupados, 2, 'pontos no mesmo pixel viram um só');
  assert.equal(geo.caminho.split('M').length - 1, 2);
  for (const [lat, lon] of pontos.values()) {
    const [x, y] = M.noMiniMapa(geo, lat, lon);
    assert.ok(x >= 0 && x <= 120 && y >= 0 && y <= 120);
  }
  const tudo = M.retanguloNoMiniMapa(geo, {latMin: -90, latMax: 90, lonMin: -180, lonMax: 180});
  assert.deepEqual(tudo, {x: 0.5, y: 0.5, largura: 119, altura: 119});
  const pequeno = M.retanguloNoMiniMapa(geo, {latMin: -10.0001, latMax: -9.9999, lonMin: -50.0001, lonMax: -49.9999});
  assert.ok(pequeno.largura >= 3.99 && pequeno.altura >= 3.99, 'um zoom profundo ainda aparece no mapinha');
  assert.equal(M.geometriaDoMiniMapa(new Map(), 120).ocupados, 0);
});

test('transição entre as vistas: posição, raio e cor interpolados; quem só existe num lado some ou aparece aos poucos', () => {
  assert.equal(M.suavizar(0), 0);
  assert.equal(M.suavizar(0.5), 0.5);
  assert.equal(M.suavizar(1), 1);
  assert.equal(M.suavizar(0.25), 0.0625);
  const origem = new Map([['a', {x: 0, y: 0, r: 4, cor: '#000000'}], ['o', {x: 10, y: 10, r: 2, cor: '#000000'}]]);
  const destino = new Map([['a', {x: 100, y: 50, r: 8, cor: '#ffffff'}], ['d', {x: 5, y: 5, r: 3, cor: '#ffffff'}]]);
  const quadro = M.quadroDaTransicao(origem, destino, 0.5);
  const de = id => quadro.find(ponto => ponto.id === id);
  assert.deepEqual(de('a'), {id: 'a', x: 50, y: 25, r: 6, cor: '#808080', alfa: 1});
  assert.equal(de('o').alfa, 0.5);
  assert.equal(de('d').alfa, 0.5);
  assert.deepEqual(quadro.map(ponto => ponto.id), ['a', 'd', 'o'], 'os maiores atrás');
  assert.deepEqual(M.quadroDaTransicao(origem, destino, 1).find(ponto => ponto.id === 'a'), {id: 'a', x: 100, y: 50, r: 8, cor: '#ffffff', alfa: 1});
  assert.equal(M.quadroDaTransicao(origem, destino, 1).find(ponto => ponto.id === 'o').alfa, 0);
  assert.ok(M.LIMITE_TRANSICAO >= 400, 'com milhares de pontos, a troca é direta');
});

test('cores do mapa em constantes (o modo escuro troca só o objeto): superfície e tintas da paleta validada', () => {
  assert.equal(M.MAPA_CORES.superficie, '#fcfcfb');
  assert.equal(M.MAPA_CORES.tinta, '#0b0b0b');
  assert.equal(M.MAPA_CORES.naoAvaliavel, '#898781');
  for (const [chave, valor] of Object.entries(M.MAPA_CORES))
    assert.match(valor, /^(#[0-9a-f]{6}|rgba\(\d+, \d+, \d+, 0?\.\d+\))$/, chave);
});
