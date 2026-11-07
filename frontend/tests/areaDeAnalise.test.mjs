import {readFileSync} from 'node:fs';
import {test} from 'node:test';
import assert from 'node:assert/strict';
import ts from 'typescript';
async function source(name, ajustar = code => code) {
  const code = ts.transpileModule(readFileSync(new URL('../src/' + name + '.ts', import.meta.url), 'utf8'),
    {compilerOptions: {module: ts.ModuleKind.ESNext, target: ts.ScriptTarget.ES2022}}).outputText;
  return import('data:text/javascript;base64,' + Buffer.from(ajustar(code)).toString('base64'));
}
// Área de análise (23/10/2026): os ajustes dentro de cada análise, a vista do desenho (gráfico, mapa ou lado a lado), as decisões
// puras do mapa (disponibilidade com o motivo, pintura com os quintis do motor, cor contínua, tamanho e ligações), o estado salvo
// com a vista, o aspecto "mapa" dos não avaliáveis, a frase-resumo do motor, os dados do mapa no cliente, os nomes das abas, a
// apresentação de cada aba e as explicações da tendência (painelModel.ts e painelApi.ts, com a sessão substituída por um esboço:
// os testes não fazem pedidos).
const M = await source('painelModel');
const A = await source('painelApi', code => code.replace(/import\s*\{[^}]*\}\s*from\s*["']\.\/conversationSession["'];?/,
  'const contextRevision = () => 0; const fetch = globalThis.fetch;'));

const VAZIO = {populacao: null, quantidade: null, densidade: null};
const municipio = (id, rotulo, valores = {}) => ({id, tipo: 'municipio', rotulo, uf: rotulo.slice(-3, -1), populacao: 1000, quantidade: 10,
  densidade: 10, distancia_km: null, inicial: {...VAZIO}, variacao_percentual: {...VAZIO},
  avaliavel: {densidade: true, distancia: null, variacao: null}, motivos: [], referencia: false, ...valores});
const SEM_REGISTRO = 'Sem registro em junho de 2024 na categoria MEDICINA: valores não avaliáveis, nunca zero (SEM_REGISTRO_OBSERVADO)';
const SEM_PONTO = 'Sem coordenada válida da sede municipal na competência (SEM_INFORMACAO_ESPACIAL)';
const BR = M.ROTULOS_BRASIL;
const DISTRITOS = {unidade: {singular: 'distrito', plural: 'distritos'}, grupo: {singular: 'província', plural: 'províncias'}};
// Planilha fictícia com a unidade feminina (28/10/2026, navegação simulada com comunas agrupadas em condados).
const COMUNAS = {unidade: {singular: 'comuna', plural: 'comunas'}, grupo: {singular: 'condado', plural: 'condados'}};
const definicao = (extra = {}) => ({...M.definicaoInicial({tipo: 'brasil', periodos: ['202306', '202406'], categoria: 'MEDICINA', temGrupos: true}), ...extra});
const resposta = (extra = {}) => ({competencia: '202406', competencia_inicial: null, categoria: 'MEDICINA', versao_base: 'v1', chave_execucao: 'k1',
  nivel: 'municipios', referencia: null, itens: [], dominios: {}, notas: ['Nota do motor.'], limitacoes: [], tendencia: null, grupos: null,
  faixas: null, faixasDistancia: null, condicoes: null, ordenacao: null, comparacao: null, contextoBrasil: null, disponibilidade: {}, sessao: null,
  rotulos: null, indicador: 'densidade', resumo: null, ...extra});

test('ajustes dentro da análise: cada aba só com os seus; o mesmo indicador em todas, menos na rotatividade; nos estados, os da distribuição', () => {
  const a = extra => M.ajustesDaAnalise({familia: 'distribuicao', nivel: 'municipios', disponivel: true, categorias: 1, ...extra});
  assert.deepEqual(a({}), ['indicador', 'competencia', 'agrupar']);
  assert.deepEqual(a({categorias: 2}), ['indicador', 'categoria', 'competencia', 'agrupar']);  // a categoria junto do indicador
  assert.deepEqual(a({familia: 'espacial'}), ['indicador', 'competencia', 'referencia']);
  assert.deepEqual(a({familia: 'tendencia', categorias: 3}), ['indicador', 'categoria', 'janela', 'visao']);
  assert.deepEqual(a({familia: 'rotatividade'}), ['periodos']);
  assert.deepEqual(a({familia: 'rotatividade', categorias: 2}), ['periodos', 'categoria']);
  // O indicador é um só (fica na definição): a escolha acompanha a pessoa em todas as abas que o têm, sempre à vista e em primeiro.
  for (const familia of ['distribuicao', 'espacial', 'tendencia']) assert.equal(a({familia})[0], 'indicador');
  // Nos estados e no Brasil (24/10/2026), a distribuição e a tendência valem; a espacial espera municípios (os ajustes da
  // distribuição). Com o Brasil, uma unidade só, sem grupos nem faixas.
  for (const familia of ['distribuicao', 'espacial']) assert.deepEqual(a({familia, nivel: 'estados'}), ['indicador', 'competencia', 'agrupar']);
  assert.deepEqual(a({familia: 'tendencia', nivel: 'estados'}), ['indicador', 'janela', 'visao']);
  for (const familia of ['distribuicao', 'espacial', 'rotatividade']) assert.deepEqual(a({familia, nivel: 'brasil'}), ['indicador', 'competencia']);
  assert.deepEqual(a({familia: 'tendencia', nivel: 'brasil'}), ['indicador', 'janela', 'visao']);
  assert.deepEqual(a({familia: 'rotatividade', disponivel: false}), ['indicador', 'competencia', 'agrupar']);
  // A escala não é ajuste da análise: fica junto do desenho.
  for (const familia of ['distribuicao', 'espacial', 'tendencia', 'rotatividade']) assert.ok(!a({familia}).includes('escala'));
  assert.equal(M.TEXTO_SEM_POPULACAO, 'Sem população na planilha: só a quantidade.');
});

test('vista do desenho: o mapa nos municípios e, na base do Brasil, nos estados (no ponto de desenho do motor); desligado na planilha sem coordenadas e em Séries', () => {
  const d = extra => M.disponibilidadeDoMapa({fonte: 'brasil', temCoordenadas: true, nivel: 'municipios', series: false, rotatividade: false,
    rotulos: BR, ...extra});
  assert.deepEqual(d({}), {disponivel: true, motivo: null, atalho: null});
  // Vendo por estado (06/11/2026, item 3.2; divergência aprovada da RQ-REP-07, só a bolha no centro): o mapa fica ligado, com cada
  // estado no ponto de desenho que o motor calcula (a média das sedes dos municípios dele). O mapa em grade não foi aprovado.
  assert.deepEqual(d({nivel: 'estados'}), {disponivel: true, motivo: null, atalho: null});
  const semColunas = d({fonte: 'arquivo', temCoordenadas: false, rotulos: DISTRITOS});
  assert.equal(semColunas.disponivel, false);
  assert.equal(semColunas.atalho, null);
  assert.equal(semColunas.motivo, 'A planilha não tem as colunas de latitude e longitude: o mapa precisa das coordenadas de cada distrito. ' +
    'A tabela continua.');
  assert.ok(d({fonte: 'arquivo', temCoordenadas: false, rotatividade: true, rotulos: DISTRITOS}).motivo
    .startsWith('Sem latitude e longitude na planilha, a rotatividade fica nas barras'));
  assert.equal(d({fonte: 'arquivo', temCoordenadas: true, rotatividade: true, rotulos: DISTRITOS}).disponivel, true);
  const series = d({series: true});
  assert.equal(series.disponivel, false);
  assert.equal(series.motivo, 'Na visão Série temporal, cada município é uma linha no tempo: o mapa fica com Tendência e Trajetória.');
  // Numa planilha com grupos, os nomes da planilha: os grupos dela não têm o ponto de desenho (só a base do Brasil, nesta etapa).
  assert.deepEqual(d({fonte: 'arquivo', nivel: 'estados', rotulos: DISTRITOS}), {disponivel: false, atalho: 'Ver os distritos no mapa',
    motivo: 'No mapa desta fonte, cada ponto é um distrito: as províncias não têm um ponto de desenho.'});
  assert.equal(d({fonte: null}).disponivel, false);
  assert.equal(M.LARGURA_LADO_A_LADO, 1600);
});

test('pintura do mapa: a camada do gráfico, a cor contínua da rotatividade ou os 5 grupos iguais (quintis) do motor, sem pergunta', () => {
  const p = extra => M.pinturaDoMapa({camada: 'unica', rotatividade: false, gruposDoMapa: true, ...extra});
  assert.equal(p({}), 'quintis');  // sem cor própria da análise, os quintis que o motor devolveu em grupos_mapa
  assert.equal(p({gruposDoMapa: false}), 'camada');  // sem eles (uma análise guardada antes), a cor única do gráfico
  for (const camada of ['grupos', 'faixas', 'condicoes', 'ordem', 'classes', 'variacao']) {
    assert.equal(p({camada}), 'camada');  // a camada em uso no gráfico vale também no mapa
    assert.equal(p({camada, gruposDoMapa: false}), 'camada');
  }
  assert.equal(p({rotatividade: true}), 'continua');
  assert.equal(M.opcoesDePintura, undefined);  // a pergunta "Como pintar o mapa?" saiu (23/10/2026)
  // O pedido leva os quintis do mapa só quando a análise não tem cor própria e o mapa está disponível.
  const d = extra => definicao({base: {todos: false, estados: ['13'], ids: []}, ...extra});
  const q = (def, familia = 'distribuicao', mapa = true) => M.precisaQuintisDoMapa(def, familia, mapa);
  assert.equal(q(d()), true);
  assert.equal(q(d(), 'espacial'), true);  // a distância nunca pinta o mapa (RQ-REP-02): os quintis do indicador
  assert.equal(q(d(), 'tendencia'), false);  // as classes já pintam
  assert.equal(q(d(), 'rotatividade'), false);  // a permanência já pinta
  assert.equal(q(d(), 'distribuicao', false), false);  // sem mapa (planilha sem coordenadas, visão Séries)
  assert.equal(q(d({nivel: 'estados'})), true);  // vendo por estado, o mapa pinta os estados pelos quintis do motor (06/11/2026)
  assert.equal(q(d({nivel: 'brasil'})), false);
  assert.equal(q(d({agrupar: {tipo: 'quartis', faixas: []}})), false);
  assert.equal(q(d({agrupar: {tipo: 'faixas', faixas: [1, 2]}})), false);
  assert.equal(q(d({agrupar: {tipo: 'faixas', faixas: [1]}})), true);  // faixas incompletas não pintam o gráfico
  assert.equal(q(d({condicoes: [{atributo: 'densidade', operador: '>', valor: 1}]})), false);
  assert.equal(q(d({ordenar: {atributo: 'densidade', ordem: 'desc'}})), false);
  const opcoes = M.montarOpcoes(d(), 'distribuicao', undefined, {quintisDoMapa: true});
  assert.deepEqual(opcoes.grupos_mapa, {tipo: 'quintis'});
  assert.equal(opcoes.grupos, undefined);  // o gráfico continua sem grupos
  assert.equal(M.montarOpcoes(d(), 'distribuicao').grupos_mapa, undefined);
  // Com os quintis do mapa, o indicador muda a resposta: a troca do indicador pede de novo; a troca da vista, não.
  assert.equal(M.pedidoDependeDoIndicador(opcoes), true);
  assert.equal(M.pedidoDependeDoIndicador(M.montarOpcoes(d(), 'distribuicao')), false);
  assert.notEqual(M.chaveDoPedido(opcoes), M.chaveDoPedido({...opcoes, indicador: 'quantidade'}));
  // Cor contínua: o indicador no domínio do motor, ou a permanência da coorte inicial de 0 a 100%.
  const dominios = {densidade: [0.5, 15], quantidade: [1, 105], populacao: [1000, 9000]};
  const cor = M.corContinuaDoMapa({rotatividade: false, indicador: 'densidade', dominios});
  assert.deepEqual([cor.rotulo, cor.dominio], ['Densidade (por 1.000 habitantes)', [0.5, 15]]);
  assert.equal(cor.valor(municipio('code:1', 'A (AM)', {densidade: 2.5})), 2.5);
  assert.equal(cor.valor(municipio('code:1', 'A (AM)', {densidade: null})), null);
  assert.equal(M.corContinuaDoMapa({rotatividade: false, indicador: 'quantidade', dominios}).rotulo, 'Quantidade (profissionais)');
  const permanencia = M.corContinuaDoMapa({rotatividade: true, indicador: 'densidade', dominios});
  assert.deepEqual([permanencia.rotulo, permanencia.dominio], ['Permanência da coorte inicial (%)', [0, 100]]);
  assert.equal(permanencia.valor(municipio('code:2', 'B (AM)', {rotatividade: {coorteInicial: 120, permanencia: 72.5}})), 72.5);
  // Tamanho (área proporcional): população na densidade, quantidade na quantidade, coorte inicial na rotatividade.
  const populacao = M.tamanhoDoMapa({rotatividade: false, indicador: 'densidade', dominios});
  assert.deepEqual([populacao.rotulo, populacao.maximo, populacao.valor(municipio('code:1', 'A (AM)', {populacao: 1234}))], ['População', 9000, 1234]);
  const quantidade = M.tamanhoDoMapa({rotatividade: false, indicador: 'quantidade', dominios});
  assert.deepEqual([quantidade.rotulo, quantidade.maximo, quantidade.valor(municipio('code:1', 'A (AM)', {quantidade: 7}))],
    ['Quantidade de profissionais', 105, 7]);
  const coorte = M.tamanhoDoMapa({rotatividade: true, indicador: 'densidade', dominios});
  assert.deepEqual([coorte.rotulo, coorte.maximo, coorte.valor(municipio('code:2', 'B (AM)', {rotatividade: {coorteInicial: 120}}))],
    ['Coorte inicial', null, 120]);
});

test('ligações ilustrativas do mapa: só das unidades selecionadas, até a referência mais próxima do motor (com o empate), até 30', () => {
  const manaus = {id: 'code:130260', rotulo: 'MANAUS (AM)'};
  const itens = [municipio('code:130260', 'MANAUS (AM)', {referencia: true}),
    municipio('code:130420', 'TEFE (AM)', {referenciaDoItem: [manaus]}),
    municipio('code:130340', 'PARINTINS (AM)', {referenciaDoItem: [manaus, {id: 'code:130185', rotulo: 'IRANDUBA (AM)'}]}),
    municipio('code:350010', 'FORA (SP)', {referenciaDoItem: null}),
    {...municipio('c1', 'Interior'), tipo: 'conjunto', referenciaDoItem: [manaus]}];
  assert.deepEqual(M.ligacoesDoMapa(itens, ['code:130340', 'code:130260', 'code:350010', 'c1', 'code:130420']),
    [{de: 'code:130340', para: ['code:130260', 'code:130185']}, {de: 'code:130420', para: ['code:130260']}]);
  assert.deepEqual(M.ligacoesDoMapa(itens, []), []);
  const muitos = Array.from({length: 40}, (_, i) => municipio('code:' + (100000 + i), 'M' + i + ' (AM)', {referenciaDoItem: [manaus]}));
  assert.equal(M.MAX_LIGACOES, 30);
  assert.equal(M.ligacoesDoMapa(muitos, muitos.map(item => item.id)).length, 30);
});

test('Histórico: a vista do desenho e a cor contínua entram no estado salvo; o estado de antes, sem os campos, continua legível', () => {
  const def = definicao({nivel: 'municipios', base: {todos: false, estados: ['13'], ids: []}});
  const corpo = resposta();
  const salvo = M.salvarEstado('Densidade de médicos', {chave: 'k', familia: 'distribuicao', opcoes: {competencia: '202406', categoria: 'MEDICINA'},
    definicao: def, visual: {escala: 'linear', corte: null, selecionados: [], vista: 'mapa', corContinua: true}}, corpo, '2026-10-23T12:00:00.000Z');
  const lido = M.lerEstadoSalvo(salvo);
  assert.deepEqual(lido.visual, {escala: 'linear', corte: null, selecionados: [], vista: 'mapa', corContinua: true});
  assert.deepEqual(lido, {...salvo.definicao, resposta: corpo});
  const lado = M.salvarEstado('T', {...salvo.definicao, visual: {...salvo.definicao.visual, vista: 'lado'}}, corpo);
  assert.equal(M.lerEstadoSalvo(lado).visual.vista, 'lado');  // numa janela estreita, a área troca pelo mapa
  // Estado de antes de 23/10, sem vista nem cor: reabre sem os campos (a área mostra o gráfico).
  const antigo = {titulo: 'T', quando: '', resposta: corpo, definicao: {versao: 1, chave: 'k', familia: 'distribuicao', opcoes: null, definicao: def,
    visual: {escala: 'logaritmica', corte: null, selecionados: ['code:130260']}}};
  assert.deepEqual(M.lerEstadoSalvo(antigo).visual, {escala: 'logaritmica', corte: null, selecionados: ['code:130260']});
  // Valores estranhos ficam de fora, sem derrubar o estado.
  const estranho = {...antigo, definicao: {...antigo.definicao, visual: {...antigo.definicao.visual, vista: 'tela-cheia', corContinua: 'sim'}}};
  assert.deepEqual(M.lerEstadoSalvo(estranho).visual, {escala: 'logaritmica', corte: null, selecionados: ['code:130260']});
});

test('não avaliáveis no mapa: com o mapa à vista, a unidade sem coordenada válida entra à parte, com o motivo do motor, e continua no gráfico', () => {
  const itens = [municipio('code:130420', 'TEFE (AM)'), municipio('code:130260', 'MANAUS (AM)'),
    municipio('code:130185', 'IRANDUBA (AM)', {populacao: null, quantidade: null, densidade: null, motivos: [SEM_REGISTRO],
      avaliavel: {densidade: false, distancia: null, variacao: null}})];
  const semCoordenada = new Map([['code:130420', SEM_PONTO], ['code:130260', ''], ['code:130185', SEM_PONTO]]);
  const {plotaveis, fora} = M.separarItens(itens, 'densidade', {semCoordenada});
  assert.deepEqual(plotaveis.map(item => item.id), ['code:130260', 'code:130420']);  // no gráfico, as bolhas ficam
  assert.deepEqual(fora.map(item => [item.id, item.aspecto, item.motivo]), [['code:130185', 'indicador', SEM_REGISTRO],
    ['code:130260', 'mapa', 'Sem coordenada válida para o mapa.'], ['code:130420', 'mapa', SEM_PONTO]]);
  // Sem o mapa à vista, a lista não muda.
  assert.deepEqual(M.separarItens(itens, 'densidade', {}).fora.map(item => item.aspecto), ['indicador']);
  assert.deepEqual(M.separarItens(itens, 'densidade', {semCoordenada: null}).fora.map(item => item.aspecto), ['indicador']);
  // Na rotatividade, a coorte avaliável sem coordenada também; a não avaliável fica só com o motivo da coorte.
  const coortes = [municipio('code:3', 'C (AM)', {rotatividade: {coorteInicial: 120, permaneceram: 87, sairam: 33, permanencia: 72.5, saida: 27.5,
    avaliavel: true, motivo: null}}), municipio('code:4', 'D (AM)', {rotatividade: {coorteInicial: null, permaneceram: null, sairam: null,
    permanencia: null, saida: null, avaliavel: false, motivo: 'Não avaliável: sem registro observado em um dos períodos (SEM_REGISTRO_OBSERVADO)'}})];
  const rot = M.separarItens(coortes, 'densidade', {rotatividade: true, semCoordenada: new Map([['code:3', SEM_PONTO], ['code:4', SEM_PONTO]])});
  assert.deepEqual(rot.plotaveis.map(item => item.id), ['code:3']);
  assert.deepEqual(rot.fora.map(item => [item.id, item.aspecto]), [['code:3', 'mapa'], ['code:4', 'rotatividade']]);
  // A dica do ponto na rotatividade traz a permanência e a coorte inicial do motor.
  const dica = M.montarDica(coortes[0], {indicador: 'densidade', competencia: '202406', competenciaInicial: null, distancia: false, variacao: false,
    tendencia: false, nomes: new Map(), rotulos: BR});
  assert.ok(dica.linhas.some(linha => linha.rotulo === 'Permanência da coorte inicial' && linha.valor === '72,50%'));
  assert.ok(dica.linhas.some(linha => linha.rotulo === 'Coorte inicial' && linha.valor === '120'));
  assert.ok(M.montarDica(coortes[1], {indicador: 'densidade', competencia: '202406', competenciaInicial: null, distancia: false, variacao: false,
    tendencia: false, nomes: new Map(), rotulos: BR}).notas.some(nota => nota.endsWith('(SEM_REGISTRO_OBSERVADO)')));
});

test('conversa: "ver no mapa" e "volte ao gráfico" são estado visual; o mapa vale para a análise que resulta do pedido, também nos estados', () => {
  const c = {periodos: ['202306', '202406'], nomes: new Map(), temGrupos: true,
    disponivel: f => M.disponibilidadeDaFamilia(f, {fonte: 'brasil', nivel: 'municipios', disponibilidade: null, temIdentificador: false, rotulos: BR}),
    mapa: d => M.disponibilidadeDoMapa({fonte: 'brasil', temCoordenadas: true, nivel: d.nivel, series: false, rotatividade: false, rotulos: BR})};
  const estados = definicao({nivel: 'estados'});
  // Vendo por estado (06/11/2026), o mapa existe: cada estado no ponto de desenho do motor.
  const noMapa = M.aplicarPedido(estados, {vista: 'mapa'}, c);
  assert.equal(noMapa.vista, 'mapa');
  assert.deepEqual(noMapa.mensagens, []);
  assert.equal(noMapa.definicao.nivel, 'estados');  // a vista não muda a análise
  // Numa fonte em que os grupos não têm o ponto de desenho, o motivo.
  const semPonto = M.aplicarPedido(estados, {vista: 'mapa'}, {...c, mapa: d => M.disponibilidadeDoMapa({fonte: 'arquivo', temCoordenadas: true,
    nivel: d.nivel, series: false, rotatividade: false, rotulos: DISTRITOS})});
  assert.equal(semPonto.vista, null);
  assert.deepEqual(semPonto.mensagens, ['Mapa: No mapa desta fonte, cada ponto é um distrito: as províncias não têm um ponto de desenho.']);
  const amazonas = M.aplicarPedido(estados, {municipios: {todos: false, estados: ['13'], ids: []}, vista: 'mapa'}, c);
  assert.equal(amazonas.vista, 'mapa');
  assert.deepEqual(amazonas.mensagens, []);
  assert.equal(M.aplicarPedido(estados, {vista: 'grafico'}, c).vista, 'grafico');
  assert.equal(M.aplicarPedido(estados, {}, c).vista, null);
  const {mapa, ...semConferencia} = c;
  assert.equal(M.aplicarPedido(estados, {vista: 'mapa'}, semConferencia).vista, 'mapa');
});

test('frase-resumo do motor no cliente e no arquivo de método; dados do mapa normalizados (pontos num Map, sem coordenada com o motivo)', () => {
  const bruta = {competencia: '202406', categoria: 'MEDICINA', nivel: 'municipios', indicador: 'quantidade', itens: [],
    resumo: {texto: '  Nos 62 municípios do Amazonas, em junho de 2024, a quantidade de médicos vai de 1 a 4.730.  '}};
  const r = A.normalizarResposta(bruta);
  assert.deepEqual(r.resumo, {texto: 'Nos 62 municípios do Amazonas, em junho de 2024, a quantidade de médicos vai de 1 a 4.730.'});
  assert.equal(r.indicador, 'quantidade');
  const antiga = A.normalizarResposta({competencia: '202406', categoria: 'MEDICINA', itens: []});
  assert.deepEqual([antiga.resumo, antiga.indicador], [null, null]);  // a resposta de antes continua legível
  assert.deepEqual(A.resumoDe('Frase do motor.'), {texto: 'Frase do motor.'});
  assert.equal(A.resumoDe({texto: '   '}), null);
  assert.equal(A.resumoDe(null), null);
  const metodo = M.textoDoMetodo(resposta({resumo: {texto: 'Frase do motor.'}}), 'Densidade de médicos', null);
  assert.deepEqual(metodo.split('\n').slice(0, 4), ['Densidade de médicos', 'Frase do motor.', '', 'Procedência']);
  assert.ok(!M.textoDoMetodo(resposta({resumo: {texto: 'Frase do motor.'}}), 'T', null, null).includes('Frase do motor.'));  // fora da tela, fora do arquivo
  assert.deepEqual(M.textoDoMetodo(resposta(), 'T', null).split('\n').slice(0, 2), ['T', '']);
  // Numa planilha (28/10/2026), as chaves dos parâmetros são ditas com os nomes dela; na base do Brasil, nada muda.
  const opcoesDoMetodo = {nivel: 'municipios', base: {municipios: {todos: true, estados: [], ids: []}}};
  assert.ok(M.textoDoMetodo(resposta(), 'T', opcoesDoMetodo, null, {rotulos: COMUNAS, brasil: false}).includes('Parâmetros da análise\n' +
    'Os nomes das chaves abaixo são os do contrato da API, iguais em toda fonte: nesta planilha, “municipios” são as comunas, e ' +
    '“estados”, os condados.\n{'));
  assert.ok(!M.textoDoMetodo(resposta(), 'T', opcoesDoMetodo, null, {rotulos: BR, brasil: true}).includes('contrato da API'));
  const dados = A.normalizarMapa({competencia: '202406', referencial: 'SIRGAS2000',
    pontos: [{id: 'code:130260', lat: -3.1019, lon: -60.025}, {id: 'code:130420', lat: '-3.35', lon: -64.71}, {id: 'code:1', lat: 95, lon: 0}, {lat: 1, lon: 1}],
    sem_coordenada: [{id: 'code:130185', rotulo: 'IRANDUBA (AM)', motivo: SEM_PONTO}, {rotulo: 'sem identificador'}]});
  assert.equal(dados.competencia, '202406');
  assert.equal(dados.referencial, 'SIRGAS2000');
  assert.ok(dados.pontos instanceof Map);
  assert.deepEqual([...dados.pontos.entries()], [['code:130260', [-3.1019, -60.025]]]);
  assert.deepEqual(dados.semCoordenada, [{id: 'code:130185', rotulo: 'IRANDUBA (AM)', motivo: SEM_PONTO}]);
  assert.throws(() => A.normalizarMapa({competencia: '202406'}), erro => erro instanceof A.ErroDoMotor);
});

test('nomes padronizados: a Seleção de Territórios primeiro, e as quatro análises com o nome completo', () => {
  assert.deepEqual(M.ABAS, ['territorios', 'distribuicao', 'espacial', 'tendencia', 'rotatividade']);
  assert.deepEqual(M.ABAS.map(M.nomeDaAba), ['Seleção de Territórios', 'Análise de Distribuição', 'Análise Espacial',
    'Análise de Tendência', 'Análise de Rotatividade']);
  assert.equal(M.NOME_SELECAO, 'Seleção de Territórios');  // a seleção não é uma análise
  // A orientação da Seleção, curta (24/10/2026), sem instruções sobre as caixas.
  assert.equal(M.TEXTO_DA_SELECAO, 'Escolha os territórios que entram nas análises. A seleção vale para todas elas e pode ser mudada a ' +
    'qualquer momento.');
  // A abertura: a identificação do sistema e a chamada para escolher os dados, com as duas entradas.
  assert.equal(M.TITULO_DO_SISTEMA, 'Diagnóstico Territorial da Força de Trabalho na Saúde');  // o nome da plataforma (24/10/2026)
  assert.equal(M.TEXTO_ESCOLHA_DOS_DADOS, 'Escolha seus dados para começar');
  assert.ok(!/privacidade|modelo/i.test(M.TEXTO_DAS_FONTES), M.TEXTO_DAS_FONTES);
  // A abertura não marca territórios: nada é pedido ao motor até a escolha.
  for (const tipo of ['brasil', 'arquivo']) {
    const inicial = M.definicaoInicial({tipo, periodos: ['202406'], categoria: '', temGrupos: tipo === 'brasil'});
    assert.equal(inicial.nivel, 'municipios');
    assert.deepEqual(inicial.base, {todos: false, estados: [], ids: []});
    assert.equal(M.bloqueioDoPedido(inicial, {fonte: tipo, rotulos: BR}), M.TEXTO_SEM_SELECAO);
  }
});

test('apresentação de cada aba: o que a aba faz, com os nomes territoriais da fonte e sem códigos internos', () => {
  const brasil = aba => M.apresentacaoDaAba(aba, {rotulos: BR, brasil: true, comGrupos: true});
  const planilha = aba => M.apresentacaoDaAba(aba, {rotulos: DISTRITOS, brasil: false, comGrupos: true});
  const tudo = a => [a.titulo, ...a.paragrafos, ...(a.itens || []).flatMap(item => [item.termo, item.texto]), a.nota || ''].join(' ');
  for (const aba of M.ABAS) {
    assert.equal(brasil(aba).titulo, M.nomeDaAba(aba));
    assert.ok(brasil(aba).paragrafos.length >= 1);
    const texto = tudo(planilha(aba));
    assert.ok(!/município|estado|Brasil/i.test(texto), aba + ': ' + texto);  // a planilha fala de distritos e províncias
    // Sem códigos do motor nem do método na tela (24/10/2026: a referência do método fica em Detalhes, na aba Método e procedência).
    assert.ok(!/[A-Z]{3,}_[A-Z]|CAP-|DA-\d/.test(tudo(brasil(aba)) + texto), aba + ': ' + texto);
  }
  // A Seleção: só a orientação curta (as instruções das caixas saíram).
  assert.deepEqual(brasil('territorios').paragrafos, [M.TEXTO_DA_SELECAO]);
  assert.deepEqual(planilha('territorios').paragrafos, [M.TEXTO_DA_SELECAO]);
  const antes = M.apresentacaoDaAba('territorios', {rotulos: M.ROTULOS_GENERICOS, brasil: false, comGrupos: false, semDados: true});
  assert.equal(antes.paragrafos[0], 'Depois de escolher os dados, a lista de territórios aparece aqui.');
  assert.ok(brasil('distribuicao').paragrafos[1].includes('5 grupos iguais (quintis)'));
  assert.ok(brasil('espacial').paragrafos[1].includes('(a sede municipal)'));
  assert.ok(brasil('espacial').paragrafos[1].includes('vendo por estado, ela mostra o botão que leva aos municípios desses estados'));
  assert.ok(!brasil('espacial').paragrafos.join(' ').includes('Brasil não têm'));
  assert.ok(!planilha('espacial').paragrafos[1].includes('sede'));
  assert.ok(brasil('rotatividade').paragrafos[1].includes('envie uma planilha com o identificador individual'));
  assert.ok(!planilha('rotatividade').paragrafos[1].includes('envie'));
  // As classes da tendência, na ordem da SPEC, cada uma com o que quer dizer e um exemplo curto, e o não avaliável.
  const tendencia = brasil('tendencia');
  assert.deepEqual(tendencia.itens.map(item => item.termo), ['Crescimento', 'Aceleração do crescimento', 'Desaceleração do crescimento',
    'Declínio', 'Aceleração de declínio', 'Desaceleração de declínio', 'Sem classificação', 'Não avaliável']);
  assert.ok(tendencia.itens.every(item => item.texto && item.texto.endsWith('.')));
  assert.ok(tendencia.itens.slice(0, 7).every(item => /Exemplos?: /.test(item.texto)), 'cada classe com um exemplo');
  assert.ok(tendencia.paragrafos[0].includes('nos últimos 4 períodos, anuais ou semestrais (você escolhe no campo Período)'));
  assert.ok(tendencia.paragrafos[0].includes('o indicador sobe (alta), cai (queda) ou fica igual (pausa)'));
  assert.ok(tendencia.nota.includes('a seta para cima é alta; para baixo, queda; para o lado, pausa'));
  assert.ok(tendencia.nota.includes('o tamanho de cada alta ou queda é comparado por mês'));
  assert.ok(tendencia.nota.endsWith('A referência do método fica em Detalhes, na aba Método e procedência.'));
  assert.ok(!/janelas longas|trecho|avanço/.test(tendencia.nota + tendencia.paragrafos.join(' ')));
  assert.deepEqual(Object.keys(M.DESCRICAO_DAS_CLASSES), M.CLASSES_TENDENCIA.map(classe => classe.codigo));
});

test('as classes da tendência em palavras simples: os exemplos seguem a regra do motor (CAP-TEN-01), passo a passo', () => {
  // Cada exemplo da explicação, classificado aqui pela mesma regra do motor (backend/trend.py, classify_speeds: o sinal de cada
  // avanço e se o tamanho cresce ou diminui), dá a classe que ele ilustra. Os períodos dos exemplos têm a mesma distância.
  const classe = valores => {
    const v = valores.slice(1).map((x, i) => x - valores[i]);
    if (v.every(x => x === 0)) return 'SEM_CLASSIFICACAO';
    if (v.some(x => x > 0) && v.some(x => x < 0)) return 'SEM_CLASSIFICACAO';
    const base = v.every(x => x >= 0) ? 'CRESCIMENTO' : 'DECLINIO';
    if (v.some(x => x === 0)) return base;
    const m = v.map(Math.abs), passos = m.slice(1).map((x, i) => [m[i], x]);
    if (passos.every(([a, b]) => b >= a) && passos.some(([a, b]) => b > a)) return base + '_ACELERADO';
    if (passos.every(([a, b]) => b <= a) && passos.some(([a, b]) => b < a)) return base + '_DESACELERADO';
    return base;
  };
  for (const [codigo, texto] of Object.entries(M.DESCRICAO_DAS_CLASSES)) {
    const exemplos = texto.split(/Exemplos?: /)[1].split(';').map(trecho => trecho.replace(/\(.*?\)/g, '').match(/\d+/g).map(Number));
    for (const exemplo of exemplos) assert.equal(classe(exemplo), codigo, codigo + ': ' + exemplo.join(', '));
  }
  // O que a classe quer dizer, junto do resultado de um território só: o rótulo do motor e a descrição, sem o exemplo.
  const t = extra => ({classe: 'CRESCIMENTO_ACELERADO', familia: 'CRESCIMENTO', rotulo: 'Aceleração do crescimento', motivo: null,
    motivoCodigo: null, motivoTexto: null, avaliavel: true, observacoes: [], velocidades: [], ...extra});
  assert.equal(M.significadoDaClasse(t()), 'Aceleração do crescimento: o indicador subiu em todos os períodos, e cada alta foi do mesmo ' +
    'tamanho ou maior que a anterior, com pelo menos uma maior: o crescimento ganhou ritmo.');
  assert.equal(M.significadoDaClasse(t({avaliavel: false, classe: null})), 'Não avaliável: ' + M.DESCRICAO_NAO_AVALIAVEL);
  assert.equal(M.significadoDaClasse(null), null);
});

test('tendência: o motivo de cada unidade em palavras, sem o código; a nota das sem classificação conta pelo motor e explica a regra', () => {
  const t = extra => ({classe: 'SEM_CLASSIFICACAO', familia: 'NENHUMA', rotulo: 'Sem classificação', motivo: null, motivoCodigo: null,
    motivoTexto: null, avaliavel: true, observacoes: 22, velocidades: [], ...extra});
  assert.equal(M.explicacaoDaTendencia(t({motivoCodigo: 'MUDANCA_DE_DIRECAO', motivoTexto: 'Mudança de direção'})),
    'Sem classificação: o indicador subiu num período e caiu em outro (mudou de direção).');
  assert.equal(M.explicacaoDaTendencia(t({motivoCodigo: 'SERIE_ESTAVEL'})),
    'Sem classificação: o indicador ficou igual em todos os períodos.');
  assert.equal(M.explicacaoDaTendencia(t({avaliavel: false, classe: null, rotulo: null, motivoCodigo: 'SERIE_INSUFICIENTE',
    motivoTexto: '3 de 4 observações necessárias'})),
    'Não avaliável: falta o valor do indicador em algum dos períodos (3 de 4 observações necessárias).');
  // Sem o código nem o texto do motivo (uma resposta de antes), vale o rótulo do motor, que já diz o motivo.
  assert.equal(M.explicacaoDaTendencia(t({avaliavel: false, classe: null, rotulo: 'Não avaliável: série insuficiente'})),
    'Não avaliável: série insuficiente');
  assert.equal(M.explicacaoDaTendencia(t({avaliavel: false, classe: null, rotulo: 'Não avaliável'})), 'Não avaliável.');
  assert.equal(M.explicacaoDaTendencia(t({motivo: 'Mudança de direção (MUDANCA_DE_DIRECAO)'})), 'Sem classificação: mudança de direção.');
  assert.equal(M.explicacaoDaTendencia(t({classe: 'CRESCIMENTO_ACELERADO', familia: 'CRESCIMENTO', rotulo: 'Aceleração do crescimento'})),
    'Aceleração do crescimento: ' + M.DESCRICAO_DAS_CLASSES.CRESCIMENTO_ACELERADO.replace(/\s*Exemplo:.*$/, ''));
  assert.equal(M.explicacaoDaTendencia(null), null);
  for (const caso of [t({motivoCodigo: 'MUDANCA_DE_DIRECAO'}), t({motivoCodigo: 'SERIE_ESTAVEL'})])
    assert.ok(!/MUDANCA_DE_DIRECAO|SERIE_ESTAVEL/.test(M.explicacaoDaTendencia(caso)));
  const topo = (contagens, porMotivo) => ({contagens, semClassificacaoPorMotivo: porMotivo});
  // Todas as unidades sem classe (o cenário real das 22 competências): a contagem por motivo e a explicação da regra.
  const real = M.notaSemClassificacao(topo({SEM_CLASSIFICACAO: 62}, {MUDANCA_DE_DIRECAO: 62}), {rotulos: BR, brasil: true});
  assert.ok(real.startsWith('Sem classificação: 62 municípios mudaram de direção (o indicador subiu num período e caiu em outro).'), real);
  assert.ok(real.includes('Nenhum município recebeu classe nestes períodos'));
  assert.ok(real.includes('basta subir num e cair em outro para ficar sem classificação'));
  assert.ok(!real.includes('junhos') && !real.includes('Janelas com menos'), real);  // a janela é sempre a dos últimos 4 períodos
  assert.ok(real.endsWith('É o resultado do método, não falta de dados.'));
  // Com unidades classificadas, só a contagem por motivo.
  assert.equal(M.notaSemClassificacao(topo({CRESCIMENTO: 17, SEM_CLASSIFICACAO: 38}, {MUDANCA_DE_DIRECAO: 37, SERIE_ESTAVEL: 1}),
    {rotulos: BR, brasil: true}), 'Sem classificação: 37 municípios mudaram de direção (o indicador subiu num período e caiu em outro); ' +
    '1 município ficou igual em todos os períodos.');
  assert.equal(M.notaSemClassificacao(topo({CRESCIMENTO: 5}, {}), {rotulos: BR, brasil: true}), null);
  assert.equal(M.notaSemClassificacao(null, {rotulos: BR, brasil: true}), null);
  const distritos = M.notaSemClassificacao(topo({SEM_CLASSIFICACAO: 3}, {MUDANCA_DE_DIRECAO: 3}), {rotulos: DISTRITOS, brasil: false});
  assert.ok(distritos.includes('Nenhum distrito recebeu classe') && !distritos.includes('junhos'), distritos);
  // A resposta do motor chega com o motivo separado do código e a contagem por motivo.
  const r = A.normalizarResposta({competencia: '202406', categoria: 'MEDICINA', itens: [{id: 'code:1', tipo: 'municipio', rotulo: 'A (AM)',
    tendencia: {classe: 'SEM_CLASSIFICACAO', familia: 'NENHUMA', rotulo: 'Sem classificação', motivo: 'MUDANCA_DE_DIRECAO',
      motivo_texto: 'Mudança de direção', avaliavel: true, observacoes: 22, velocidades: []}}],
    tendencia: {competencias: ['202306', '202406'], contagens: {SEM_CLASSIFICACAO: 1}, sem_classificacao_por_motivo: {MUDANCA_DE_DIRECAO: 1}}});
  assert.equal(r.itens[0].tendencia.motivoCodigo, 'MUDANCA_DE_DIRECAO');
  assert.equal(r.tendencia.semClassificacaoPorMotivo.MUDANCA_DE_DIRECAO, 1);
});

test('quadro de setas: um ponto por período, uma seta por avanço com o sinal do motor, escala da linha e a ordem por classe', () => {
  const tendencia = (classe, observacoes, velocidades, extra = {}) => ({classe, familia: M.familiaDaClasse(classe), rotulo: classe ? 'Classe' : 'Não avaliável',
    motivo: null, motivoCodigo: null, motivoTexto: null, avaliavel: true, observacoes, velocidades, ...extra});
  const janela = ['202106', '202206', '202306', '202406'];
  const obs = valores => valores.map((valor, i) => ({competencia: janela[i], valor}));
  const vel = valores => valores.slice(1).map((valor, i) => ({de: janela[i], ate: janela[i + 1], valor: (valor - valores[i]) / 12}));
  // Manaus nos últimos 4 junhos (base versionada, arredondado): três altas, cada uma maior que a anterior.
  const valores = [1.81, 1.87, 1.96, 2.07];
  const manaus = tendencia('CRESCIMENTO_ACELERADO', obs(valores), vel(valores), {rotulo: 'Aceleração do crescimento'});
  const caixa = {x0: 0, x1: 120, y0: 0, y1: 40};
  const {pontos, setas} = M.montarSetas(manaus, janela, caixa);
  const arredondar = valor => Math.round(valor * 1e6) / 1e6;  // as posições são contas em ponto flutuante
  assert.deepEqual(pontos.map(p => arredondar(p.x)), [0, 40, 80, 120]);  // a cada 12 meses, no tempo real
  assert.deepEqual([arredondar(pontos[0].y), arredondar(pontos[3].y)], [40, 0]);  // escala da linha: o menor no pé, o maior no topo
  assert.deepEqual(setas.map(s => [s.de, s.ate, s.sinal]), [['202106', '202206', 'alta'], ['202206', '202306', 'alta'], ['202306', '202406', 'alta']]);
  assert.ok(setas.every(s => s.angulo < 0 && s.meioX > s.x1 && s.meioX < s.x2), 'a ponta no meio de cada avanço, subindo');
  // O sinal é o da velocidade do motor (pausa, alta, queda); a amplitude mínima não faz uma série quase parada parecer um salto.
  const quase = M.montarSetas(tendencia('SEM_CLASSIFICACAO', obs([5, 5, 5.0001, 5]), [{de: '202106', ate: '202206', valor: 0},
    {de: '202206', ate: '202306', valor: 0.00001}, {de: '202306', ate: '202406', valor: -0.00001}]), janela, caixa);
  assert.deepEqual(quase.setas.map(s => s.sinal), ['pausa', 'alta', 'queda']);
  assert.ok(Math.max(...quase.pontos.map(p => p.y)) - Math.min(...quase.pontos.map(p => p.y)) < 1, 'quase plana');
  // Período sem valor: nenhum ponto inventado; a seta liga as observações que o motor usou. Semestral: 5 e 7 meses.
  const semestral = ['202301', '202306', '202401', '202406'];
  const lacuna = M.montarSetas(tendencia(null, [{competencia: '202301', valor: 1}, {competencia: '202306', valor: null}, {competencia: '202401', valor: 2},
    {competencia: '202406', valor: 3}], [{de: '202301', ate: '202401', valor: 0.08}, {de: '202401', ate: '202406', valor: 0.2}], {avaliavel: false}),
  semestral, {x0: 0, x1: 170, y0: 0, y1: 40});
  assert.deepEqual(lacuna.pontos.map(p => [p.competencia, arredondar(p.x)]), [['202301', 0], ['202401', 120], ['202406', 170]]);
  assert.deepEqual(lacuna.setas.map(s => [s.de, s.ate]), [['202301', '202401'], ['202401', '202406']]);
  assert.deepEqual(M.montarSetas(null, janela, caixa), {pontos: [], setas: []});
  // Ordem: a classe na ordem da SPEC e, nela, a maior variação primeiro (sem valor no fim); os não avaliáveis por último. Com a
  // ordenação em uso, a posição do motor.
  const item = (id, classe, variacao) => ({id, tipo: 'municipio', rotulo: id, densidade: 1, variacao_percentual: {densidade: variacao},
    tendencia: classe ? tendencia(classe, [], []) : tendencia(null, [], [], {avaliavel: false}), ordem: null});
  const itens = [item('A', 'SEM_CLASSIFICACAO', 9), item('B', 'CRESCIMENTO', 2), item('C', 'CRESCIMENTO', 7), item('D', null, 50),
    item('E', 'CRESCIMENTO_ACELERADO', 1), item('F', 'CRESCIMENTO', null)];
  assert.deepEqual(M.ordemDoQuadro(itens, 'densidade', false).map(i => i.id), ['C', 'B', 'F', 'E', 'A', 'D']);
  const comPosicao = itens.map((i, n) => ({...i, ordem: {posicao: [3, null, 1, 2, null, 4][n]}}));
  assert.deepEqual(M.ordemDoQuadro(comPosicao, 'densidade', true).map(i => i.id), ['C', 'D', 'A', 'F', 'B', 'E']);
  // Para os leitores de tela: a classe do motor e cada período com o valor e o avanço até ele.
  assert.equal(M.descricaoDasSetas({...item('MANAUS (AM)', 'CRESCIMENTO_ACELERADO', 14), tendencia: manaus}, 'densidade'),
    'MANAUS (AM): Aceleração do crescimento. 06/2021: 1,81; 06/2022: 1,87, alta; 06/2023: 1,96, alta; 06/2024: 2,07, alta.');
  assert.equal(M.sinalDoAvanco(-0.1), 'queda');
});

test('planilha com a coluna-mãe: os grupos da Seleção vêm do catálogo do pré-exame (a província de cada distrito)', () => {
  const unidade = (id, nome, provincia) => ({id, name: nome, code: '', label: nome, state: '', state_name: '', state_code: '',
    parents: provincia ? [provincia] : []});
  const catalogo = [unidade('name:Alfa', 'Alfa', 'Norte'), unidade('name:Beta', 'Beta', 'Norte'), unidade('name:Gama', 'Gama', 'Sul'),
    unidade('name:Delta', 'Delta', 'Sul')];
  assert.deepEqual(M.gruposDaFonte(undefined, catalogo).map(grupo => [grupo.id, grupo.nome, grupo.unidades]), [['Norte', 'Norte', 2],
    ['Sul', 'Sul', 2]]);
  assert.equal(M.grupoDaUnidade(catalogo[2]), 'Sul');
  // Sem a coluna-mãe, a lista fica sem grupos; na base do Brasil, o estado pelo código IBGE continua valendo.
  assert.deepEqual(M.gruposDaFonte(undefined, catalogo.map(item => ({...item, parents: []}))), []);
  assert.equal(M.grupoDaUnidade({...catalogo[0], state: 'AM', state_code: '13', parents: ['Amazonas']}), '13');
  // A província marcada inteira vai ao motor pelo valor dela, e os distritos dela saem da lista solta.
  assert.deepEqual(M.normalizarBase({todos: false, estados: ['Sul'], ids: ['name:Gama', 'name:Alfa']}, id =>
    M.grupoDaUnidade(catalogo.find(item => item.id === id))), {todos: false, estados: ['Sul'], ids: ['name:Alfa']});
});

// ================================================================================================ ajustes de 24/10/2026 (segunda rodada)
test('Desfazer: um passo por ação, o arraste contínuo vira um passo só, com o estado de antes, e o texto do botão diz o que desfaz', () => {
  let pilha = [];
  pilha = M.empilharPasso(pilha, {rotulo: 'MANAUS (AM) marcado', tipo: 'MANAUS (AM) marcado', quando: 1000, estado: {n: 0}});
  pilha = M.empilharPasso(pilha, {rotulo: 'TEFE (AM) marcado', tipo: 'TEFE (AM) marcado', quando: 1500, estado: {n: 1}});
  assert.deepEqual(pilha.map(passo => passo.estado.n), [0, 1]);
  // A régua arrastada: passos seguidos do mesmo tipo contínuo ficam como um só, com o estado de antes do primeiro.
  pilha = M.empilharPasso(pilha, {rotulo: 'Ajustar a régua', tipo: 'continuo:regua', quando: 2000, estado: {n: 2}});
  pilha = M.empilharPasso(pilha, {rotulo: 'Ajustar a régua', tipo: 'continuo:regua', quando: 2300, estado: {n: 3}});
  pilha = M.empilharPasso(pilha, {rotulo: 'Ajustar a régua', tipo: 'continuo:regua', quando: 2900, estado: {n: 4}});
  assert.deepEqual(pilha.map(passo => passo.estado.n), [0, 1, 2]);
  // Depois de uma pausa de PASSO_CONTINUO_MS, outro arraste é outro passo; ações discretas iguais nunca se juntam.
  pilha = M.empilharPasso(pilha, {rotulo: 'Ajustar a régua', tipo: 'continuo:regua', quando: 2900 + M.PASSO_CONTINUO_MS, estado: {n: 5}});
  pilha = M.empilharPasso(pilha, {rotulo: 'TEFE (AM) marcado', tipo: 'TEFE (AM) marcado', quando: 9000, estado: {n: 6}});
  pilha = M.empilharPasso(pilha, {rotulo: 'TEFE (AM) marcado', tipo: 'TEFE (AM) marcado', quando: 9100, estado: {n: 7}});
  assert.deepEqual(pilha.map(passo => passo.estado.n), [0, 1, 2, 5, 6, 7]);
  // A pilha guarda até MAX_PASSOS passos (os mais antigos saem).
  let longa = [];
  for (let i = 0; i < M.MAX_PASSOS + 5; i++) longa = M.empilharPasso(longa, {rotulo: 'p' + i, tipo: 'p' + i, quando: i * 5000, estado: i});
  assert.equal(longa.length, M.MAX_PASSOS);
  assert.equal(longa[0].estado, 5);
  // O botão se chama Desfazer desde 25/10/2026 (antes, Voltar): o title diz o que o próximo clique desfaz, sem o ponto final do
  // passo, e o aviso diz o que foi desfeito; o nome próprio no começo do passo fica como é.
  assert.equal(M.textoDoDesfazer(null), 'Nada para desfazer ainda');
  assert.equal(M.textoDoDesfazer({rotulo: 'Limpar seleção'}), 'Desfazer: limpar seleção');
  assert.equal(M.textoDoDesfazer({rotulo: 'Abrir a Análise de Tendência'}), 'Desfazer: abrir a Análise de Tendência');
  assert.equal(M.textoDoDesfazer({rotulo: 'Todos os estados marcados.'}), 'Desfazer: todos os estados marcados');
  assert.equal(M.textoDoDesfeito({rotulo: 'Abrir a Seleção de Territórios'}), 'Desfeito: abrir a Seleção de Territórios.');
  assert.equal(M.textoDoDesfeito({rotulo: 'Municípios do Amazonas desmarcados.'}), 'Desfeito: municípios do Amazonas desmarcados.');
  assert.equal(M.textoDoDesfazer({rotulo: 'Marcar MANAUS (AM)'}), 'Desfazer: marcar MANAUS (AM)');
  assert.equal(M.textoDoVoltar, undefined, 'o texto antigo saiu com o nome Voltar');
});

test('período com que a tendência abre: o anual, à vista; sem ele, o único ritmo da base; sem nenhum, a escolha', () => {
  const semestrais = ['201401', '201406', '201501', '201506', '201601', '201606', '201701', '201706', '201801', '201806', '201901', '201906',
    '202001', '202006', '202101', '202106', '202201', '202206', '202301', '202306', '202401', '202406'];
  assert.deepEqual(M.janelaPadrao(semestrais), ['202106', '202206', '202306', '202406']);
  // Dois anos de competências trimestrais: o anual não tem 4 períodos, e o semestral é o único ritmo (RQ-GOV-14).
  const trimestrais = ['202301', '202303', '202306', '202309', '202312', '202403', '202406'];
  assert.deepEqual(M.janelaPadrao(trimestrais), ['202301', '202306', '202312', '202406']);
  assert.deepEqual(M.janelaPadrao(trimestrais), M.ritmosDaBase(trimestrais).find(item => item.ritmo === 'semestral').janela);
  // Sem nenhum ritmo com 4 períodos: nada é escolhido, e o aviso pede a escolha.
  assert.deepEqual(M.janelaPadrao(['202306', '202406']), []);
  // A definição inicial continua sem janela: ela entra ao abrir a Análise de Tendência, na visão Tendência.
  const inicial = M.definicaoInicial({tipo: 'brasil', periodos: semestrais, categoria: 'MEDICINA', temGrupos: true});
  assert.deepEqual([inicial.janela, inicial.visao, inicial.serie], [[], 'classes', []]);
});

test('visões da tendência: Tendência, Trajetória e Série temporal, nesta ordem; a Série temporal tem o intervalo nos ajustes', () => {
  assert.deepEqual(M.ORDEM_DAS_VISOES.map(visao => M.NOMES_VISOES[visao]), ['Tendência', 'Trajetória', 'Série temporal']);
  const a = extra => M.ajustesDaAnalise({familia: 'tendencia', nivel: 'municipios', disponivel: true, categorias: 1, ...extra});
  assert.deepEqual(a({visao: 'classes'}), ['indicador', 'janela', 'visao']);
  assert.deepEqual(a({visao: 'mudanca'}), ['indicador', 'janela', 'visao']);
  assert.deepEqual(a({visao: 'series'}), ['indicador', 'serie', 'visao']);
  // A Tendência sem 4 competências vira Trajetória; a Série temporal não depende da janela e não tem cor de classe.
  assert.equal(M.visaoEfetiva(definicao({familia: 'tendencia', visao: 'classes', janela: ['202306', '202406']})), 'mudanca');
  assert.equal(M.visaoEfetiva(definicao({familia: 'tendencia', visao: 'series', janela: []})), 'series');
  assert.equal(M.camadaDeCor('tendencia', 'series', resposta(), definicao()), 'unica');
});

test('Série temporal: toda a extensão da base, lida dos dados, ou o intervalo escolhido; o CSV com uma coluna por competência', () => {
  const periodos = ['202406', '201401', '201906', '202106'];
  assert.deepEqual(M.intervaloDaSerie({serie: []}, periodos), ['201401', '201906', '202106', '202406']);  // do primeiro ao último
  assert.deepEqual(M.intervaloDaSerie({serie: ['202106', '201906']}, periodos), ['201906', '202106']);
  assert.deepEqual(M.intervaloEntre(periodos, '201906', '202406'), ['201906', '202106', '202406']);
  assert.deepEqual(M.intervaloEntre(periodos, '202406', '201906'), ['201906', '202106', '202406']);  // a ordem dos campos não importa
  assert.deepEqual(M.intervaloEntre(periodos, '201401', '202406'), []);  // a extensão inteira volta a ser "toda a série"
  // O cliente lê a série da resposta: o intervalo no topo e as observações de cada item (null sem valor, nunca zero).
  const r = A.normalizarResposta({competencia: '202406', categoria: 'MEDICINA', nivel: 'municipios', indicador: 'densidade',
    serie: {janela: {inicio: '201401', fim: '202406', competencias: ['201401', '202106', '202406']}, competencias: 3, unidade_valor: 'por 1.000 habitantes'},
    itens: [municipio('code:130260', 'MANAUS (AM)', {serie: {observacoes: [{competencia: '201401', valor: 1.37}, {competencia: '202106', valor: null},
      {competencia: '202406', valor: 2.07}], comparavel: true, motivo: null}}),
      {...municipio('c1', 'Capitais'), tipo: 'conjunto', serie: {observacoes: [{competencia: '201401', valor: 1.4}], comparavel: false,
        motivo: 'Série não comparável: os membros mudam (INCOMPARABILIDADE)'}}]});
  assert.deepEqual(r.serie, {competencias: ['201401', '202106', '202406'], inicio: '201401', fim: '202406', unidadeValor: 'por 1.000 habitantes'});
  assert.deepEqual(r.itens[0].serie.observacoes.map(obs => obs.valor), [1.37, null, 2.07]);
  assert.equal(r.itens[1].serie.comparavel, false);
  const csv = M.montarCsv(r, {familia: 'tendencia', indicador: 'densidade', rotulos: BR}).slice(1).split('\r\n');
  assert.ok(csv[0].includes('"Densidade em 01/2014";"Densidade em 06/2021";"Densidade em 06/2024";"Série comparável"'), csv[0]);
  assert.ok(csv.some(linha => linha.startsWith('"code:130260"') && linha.includes('"1.37";"";"2.07";"sim"')));
  assert.ok(M.textoDoMetodo(r, 'Série temporal', null).includes('- Série temporal: 01/2014 a 06/2024 (3 competências)'));
});

test('Série temporal no desenho: a cor única do gráfico (sem classe) e, sem comparabilidade, só os pontos, sem linha', () => {
  const competencias = ['201401', '201406', '201501'];
  const item = (id, valores, comparavel = true) => ({...municipio(id, id + ' (AM)'), tendencia: {classe: 'CRESCIMENTO', familia: 'CRESCIMENTO',
    rotulo: 'Crescimento', avaliavel: true, observacoes: [], velocidades: []},
    serie: {observacoes: competencias.map((competencia, i) => ({competencia, valor: valores[i]})), comparavel, motivo: null}});
  const itens = [item('a', [1, 2, 3]), item('b', [2, null, 4]), item('c', [1, 1, 1], false)];
  const observacoesDe = it => it.serie.observacoes;
  const dominio = M.dominioDasSeries(itens, observacoesDe);
  const {series} = M.montarSeries({itens, janela: competencias, dominio, x0: 0, x1: 100, y0: 0, y1: 100, observacoesDe, corUnica: '#008b9e',
    ligar: it => it.serie.comparavel});
  assert.ok(series.every(serie => serie.cor === '#008b9e' && serie.familia === null), 'sem a cor da classe');
  assert.deepEqual(series.map(serie => serie.pontos.length), [3, 2, 3]);
  assert.deepEqual(series.map(serie => serie.caminhos.length), [1, 0, 0]);  // a lacuna não é ligada; o não comparável fica sem linha
  assert.deepEqual(series.map(serie => serie.ligada), [true, true, false]);
  // Sem os parâmetros novos, as séries continuam como antes (as observações da tendência, na cor da classe).
  assert.equal(M.montarSeries({itens: [item('a', [1, 2, 3])], janela: competencias, dominio, x0: 0, x1: 100, y0: 0, y1: 100}).series[0].familia,
    'CRESCIMENTO');
});

test('Trajetória: os períodos do meio, como foram observados, no caminho do rastro e na dica; sem a variação, sem caminho', () => {
  const janela = ['202106', '202206', '202306', '202406'];
  const tendencia = valores => ({classe: 'SEM_CLASSIFICACAO', familia: 'SEM_CLASSIFICACAO', rotulo: 'Sem classificação', avaliavel: true,
    motivo: null, motivoCodigo: 'MUDANCA_DE_DIRECAO', motivoTexto: null, observacoes: valores.map((valor, i) => ({competencia: janela[i], valor})),
    velocidades: []});
  const sobe = municipio('code:1', 'A (AM)', {densidade: 4, inicial: {populacao: 1000, quantidade: 2, densidade: 2},
    variacao_percentual: {populacao: 0, quantidade: 100, densidade: 100}, tendencia: tendencia([2, 5, null, 4])});
  const semVariacao = municipio('code:2', 'B (AM)', {densidade: 3, tendencia: tendencia([1, 2, 3, 3])});
  const pintura = () => ({cor: '#008b9e', vazada: false, apagada: false});
  const comum = {indicador: 'densidade', escala: 'linear', distancia: false, cometa: true, vista: 'final', largura: 800, rotuloDistancia: '', pintura};
  const g = M.montarGrafico({...comum, itens: [sobe, semVariacao], dominios: {densidade: [1, 4], tendencia: [1, 5]}, trajetoria: true});
  const a = g.bolhas.find(b => b.id === 'code:1'), b = g.bolhas.find(b => b.id === 'code:2');
  assert.deepEqual(a.trajeto.map(passo => [passo.competencia, passo.valor, passo.dx]), [['202206', 5, 0]]);  // sem imputar 06/2023
  assert.ok(a.trajeto[0].dy < 0, 'o valor 5 fica acima do valor final (4)');
  assert.equal(b.trajeto, null);  // sem a variação, não há caminho (RQ-REP-15)
  assert.ok(g.eixoY.dominio[1] >= 5, 'o eixo cabe o valor do meio');
  // Sem a Trajetória, nada muda no desenho.
  assert.equal(M.montarGrafico({...comum, itens: [sobe], dominios: {densidade: [1, 4]}}).bolhas[0].trajeto, null);
  const dica = M.montarDica(sobe, {indicador: 'densidade', competencia: '202406', competenciaInicial: '202106', distancia: false, variacao: true,
    tendencia: false, nomes: new Map(), rotulos: BR, trajetoria: true});
  assert.deepEqual(dica.linhas.filter(linha => /^Densidade em /.test(linha.rotulo)).map(linha => [linha.rotulo, linha.valor]),
    [['Densidade em 06/2021', '2,00 por 1.000 habitantes'], ['Densidade em 06/2022', '5,00 ▲'], ['Densidade em 06/2023', 'sem valor']]);
});

test('escolha dos territórios (27/10/2026): o objeto da consulta, a leitura sem perda, o que falta completar, a frase por modelo e o pedido', () => {
  const lado = (tipo, {regioes = [], ufs = [], filtros = [], modo = 'todos', municipios = []} = {}) =>
    ({partir_de: {tipo, regioes, ufs}, filtros, escolha: {modo, municipios}});
  const f = (indicador, operador, valor) => ({indicador, operador, valor});
  const consulta = (base, referencia) => ({base, referencia, distancia: {medida: 'geodesica', ate: 'referencia_mais_proxima'}});
  // A janela abre com a base na seleção prévia e a referência no país, sem filtros. Desde 06/11/2026 (item 4.1 do comando, uma
  // seleção só; muda de propósito este teste), também sem territórios selecionados: até essa data, a base partia do país.
  assert.deepEqual(M.consultaInicial({comSelecao: true}), consulta(lado('selecao_previa'), lado('pais')));
  assert.equal(M.consultaInicial({comSelecao: false}).base.partir_de.tipo, 'selecao_previa');
  assert.deepEqual(M.consultaInicial(), M.consultaInicial({comSelecao: true}));
  // A seleção em uso vazia deixa incompleto o lado que parte dela, com o caminho (a Seleção de Territórios).
  assert.deepEqual(M.pendenciasDaConsulta(M.consultaInicial(), BR, {selecaoVazia: true}),
    {base: ['escolha os municípios na Seleção de Territórios'], referencia: []});
  assert.deepEqual(M.pendenciasDaConsulta(M.consultaInicial(), BR), {base: [], referencia: []});
  // O exemplo do comando, sem o filtro de distância (retirado em 27/10/2026, a pedido do responsável: a distância até a referência
  // mais próxima aparece no eixo X do resultado): municípios do Norte com densidade abaixo de 0,5 e, como referência, os do Acre com
  // densidade acima de 2.
  const exemplo = consulta(lado('regioes', {regioes: ['Norte'], filtros: [f('densidade', '<', 0.5)]}),
    lado('ufs', {ufs: ['12'], filtros: [f('densidade', '>', 2)]}));
  // Serializa e desserializa sem perda (critério 18), também com o rascunho guardando o que a opção em uso não usa.
  const rascunho = consulta(lado('pais', {regioes: ['Sul'], ufs: ['43'], filtros: [f('populacao', '>=', null)], modo: 'todos',
    municipios: ['code:4314902']}), lado('mesma_uf_da_base', {filtros: [f('quantidade', '<=', 10)], modo: 'marcados', municipios: ['code:1200401']}));
  for (const c of [exemplo, rascunho, M.consultaInicial({comSelecao: true})]) assert.deepEqual(M.lerConsulta(JSON.parse(JSON.stringify(c))), c);
  // Forma que não confere: null (a distância não é filtro em nenhum dos lados, as opções relativas só na referência, operador e
  // valor fora do contrato).
  assert.equal(M.lerConsulta(consulta(lado('pais'), lado('pais', {filtros: [f('distancia', '>', 1)]}))), null);
  assert.equal(M.lerConsulta(consulta(lado('mesma_uf_da_base'), lado('pais'))), null);
  assert.equal(M.lerConsulta(consulta(lado('pais', {filtros: [f('distancia', '>', 300)]}), lado('pais'))), null);
  assert.equal(M.lerConsulta(consulta(lado('pais', {filtros: [f('distancia', '<=', 50)]}), lado('pais'))), null);
  assert.equal(M.lerConsulta(consulta(lado('pais', {filtros: [f('densidade', '!=', 1)]}), lado('pais'))), null);
  assert.equal(M.lerConsulta(consulta(lado('pais', {filtros: [f('densidade', '<', -1)]}), lado('pais'))), null);
  assert.equal(M.lerConsulta({...exemplo, distancia: {medida: 'estrada', ate: 'referencia_mais_proxima'}}), null);
  assert.equal(M.lerConsulta(null), null);
  // Para o motor, só o que vale para cada opção, em ordem; "A consulta mudou" só quando muda o que ele calcula.
  assert.deepEqual(M.consultaParaOMotor(rascunho), consulta(lado('pais', {filtros: [f('populacao', '>=', null)]}),
    lado('mesma_uf_da_base', {filtros: [f('quantidade', '<=', 10)], modo: 'marcados', municipios: ['code:1200401']})));
  assert.deepEqual(M.consultaParaOMotor(consulta(lado('regioes', {regioes: ['Sul', 'Norte']}), lado('pais'))).base.partir_de.regioes, ['Norte', 'Sul']);
  assert.equal(M.mesmaConsulta(rascunho, M.consultaParaOMotor(rascunho)), true);
  assert.equal(M.mesmaConsulta(exemplo, null), false);
  assert.equal(M.mesmaConsulta(exemplo, consulta(exemplo.base, lado('ufs', {ufs: ['12'], filtros: [f('densidade', '>', 2.5)]}))), false);
  // O que falta completar, com os textos do comando (os mesmos do motor), na ordem das etapas; cada lado só pelas próprias etapas.
  assert.deepEqual(M.pendenciasDaConsulta(exemplo, BR), {base: [], referencia: []});
  const faltas = consulta(lado('regioes', {filtros: [f('densidade', '<', null)], modo: 'marcados'}),
    lado('ufs', {filtros: [f('densidade', '>', 2)]}));
  assert.deepEqual(M.pendenciasDaConsulta(faltas, BR), {base: ['escolha ao menos uma região', 'preencha o valor do filtro',
    'marque ao menos um município'], referencia: ['escolha ao menos um estado']});
  assert.equal(M.textoDaPendencia('base', 'escolha ao menos uma região'), 'Base incompleta: escolha ao menos uma região.');
  assert.deepEqual(M.pendenciasDoLado(consulta(lado('ufs'), lado('pais')), 'base', DISTRITOS), ['escolha ao menos uma província']);
  assert.deepEqual(M.pendenciasDoLado(consulta(lado('pais', {modo: 'marcados'}), lado('pais')), 'base', {...DISTRITOS,
    unidade: {singular: 'unidade', plural: 'unidades', genero: 'f'}}), ['marque ao menos uma unidade']);
  // A frase-resumo por modelo, no formato "{Base} → referência: {Referência}".
  const grupos = [{id: '12', nome: 'Acre', sigla: 'AC', rotuloGrupo: 'Municípios do Acre', unidades: 22},
    {id: '13', nome: 'Amazonas', sigla: 'AM', rotuloGrupo: 'Municípios do Amazonas', unidades: 62},
    {id: '11', nome: 'Rondônia', sigla: 'RO', rotuloGrupo: 'Municípios de Rondônia', unidades: 52},
    {id: '14', nome: 'Roraima', sigla: 'RR', rotuloGrupo: 'Municípios de Roraima', unidades: 15}];
  const nomes = new Map([['code:1302603', 'MANAUS (AM)'], ['code:1501402', 'BELEM (PA)'], ['code:1200401', 'RIO BRANCO (AC)'],
    ['code:1100205', 'PORTO VELHO (RO)']]);
  const ctx = {rotulos: BR, brasil: true, grupos, nomes};
  const frase = c => M.textoDaFraseDaConsulta(M.fraseDaConsulta(c, ctx));
  // A referência diz de quem é a mais próxima (27/10/2026, pedido do responsável: "o mais próximo da Bahia" parecia o mais próximo
  // do estado): de cada território da base, entre os do conjunto de referências.
  assert.equal(frase(exemplo), 'Municípios do Norte com densidade abaixo de 0,5 → referência: o mais próximo de cada um, entre os ' +
    'municípios do Acre com densidade acima de 2');
  assert.equal(frase(consulta(lado('pais'), lado('pais'))), 'Municípios de todo o país → referência: o mais próximo de cada um, entre os ' +
    'municípios de todo o país');
  assert.equal(frase(consulta(lado('pais'), lado('mesma_uf_da_base', {filtros: [f('densidade', '>', 1.5)]}))),
    'Municípios de todo o país → referência: o mais próximo de cada um, entre os municípios do mesmo estado com densidade acima de 1,5');
  assert.equal(M.fraseDaConsulta(consulta(lado('pais'), lado('mesma_regiao_da_base')), ctx).referencia.texto,
    'o mais próximo de cada um, entre os municípios da mesma região');
  // O caso relatado: a base e a referência na Bahia.
  const comBahia = {...ctx, grupos: [...grupos, {id: '29', nome: 'Bahia', sigla: 'BA', rotuloGrupo: 'Municípios da Bahia', unidades: 417}]};
  assert.equal(M.textoDaFraseDaConsulta(M.fraseDaConsulta(consulta(lado('ufs', {ufs: ['29'], filtros: [f('densidade', '<', 0.5),
    f('populacao', '>', 10000)]}), lado('ufs', {ufs: ['29'], filtros: [f('densidade', '>', 1.5)]})), comBahia)),
    'Municípios da Bahia com densidade abaixo de 0,5 e população acima de 10.000 → referência: o mais próximo de cada um, entre os ' +
    'municípios da Bahia com densidade acima de 1,5');
  assert.equal(M.fraseDaConsulta(consulta(lado('regioes', {regioes: ['Centro-Oeste'], filtros: [f('populacao', '>', 20000), f('densidade', '<', 1)]}),
    lado('pais')), ctx).base.texto, 'Municípios do Centro-Oeste com população acima de 20.000 e densidade abaixo de 1');
  assert.equal(M.fraseDaConsulta(consulta(lado('pais', {filtros: [f('densidade', '>=', 0.5), f('densidade', '<', 1)]}), lado('pais')), ctx).base.texto,
    'Municípios de todo o país com densidade a partir de 0,5 e abaixo de 1');
  assert.equal(M.fraseDaConsulta(consulta(lado('selecao_previa', {modo: 'marcados', municipios: ['code:1302603', 'code:1501402']}), lado('pais')),
    ctx).base.texto, 'MANAUS (AM) e BELEM (PA)');
  assert.equal(M.fraseDaConsulta(consulta(lado('pais', {modo: 'marcados', municipios: [...nomes.keys(), 'code:9']}), lado('pais')), ctx).base.texto,
    'MANAUS (AM), BELEM (PA), RIO BRANCO (AC) e mais 2');
  assert.equal(M.fraseDaConsulta(consulta(lado('ufs', {ufs: ['14', '12', '13', '11']}), lado('selecao_previa', {filtros: [f('quantidade', '>=', 10)]})),
    ctx).base.texto, 'Municípios de Rondônia, do Acre, do Amazonas e de mais 1 estado');
  assert.equal(M.fraseDaConsulta(consulta(lado('pais'), lado('selecao_previa', {filtros: [f('quantidade', '>=', 10)]})), ctx).referencia.texto,
    'o mais próximo de cada um, entre os municípios da seleção prévia com quantidade a partir de 10');
  assert.equal(M.fraseDaConsulta(consulta(lado('pais'), lado('pais', {modo: 'marcados', municipios: ['code:1302603']})), ctx).referencia.texto, 'MANAUS (AM)');
  assert.equal(M.fraseDaConsulta(consulta(lado('pais'), lado('regioes', {regioes: ['Norte', 'Nordeste'], modo: 'marcados',
    municipios: ['code:1302603', 'code:1501402']})), ctx).referencia.texto, 'o mais próximo de cada um, entre MANAUS (AM) e BELEM (PA)');
  // Os marcados conforme a base: o recorte de cada território da base.
  assert.equal(M.fraseDaConsulta(consulta(lado('pais'), lado('mesma_uf_da_base', {modo: 'marcados', municipios: ['code:1302603']})), ctx)
    .referencia.texto, 'MANAUS (AM), para os municípios do mesmo estado');
  assert.equal(M.fraseDaConsulta(consulta(lado('pais'), lado('mesma_regiao_da_base', {modo: 'marcados', municipios: ['code:1302603',
    'code:1501402']})), ctx).referencia.texto, 'o mais próximo de cada um, entre MANAUS (AM) e BELEM (PA), na mesma região');
  assert.deepEqual(M.fraseDaConsulta(faltas, ctx), {base: {texto: 'base incompleta', incompleta: true}, referencia: {texto: 'referência incompleta', incompleta: true}});
  // Numa planilha, os rótulos dela.
  const planilha = {rotulos: {...DISTRITOS, unidade: {singular: 'unidade', plural: 'unidades', genero: 'f'}}, brasil: false,
    grupos: [{id: 'Norte', nome: 'Província Norte', sigla: '', rotuloGrupo: '', unidades: 3}], nomes};
  assert.equal(M.textoDaFraseDaConsulta(M.fraseDaConsulta(consulta(lado('ufs', {ufs: ['Norte']}), lado('mesma_uf_da_base')), planilha)),
    'Unidades de Província Norte → referência: a mais próxima de cada uma, entre as unidades da mesma província');
  // Desde 07/11/2026 (item 1 do comando, os nomes da base; muda de propósito): "de toda a base" (antes, "de toda a planilha");
  // com o nome do todo, ele, com o artigo pedido.
  assert.equal(M.fraseDaConsulta(consulta(lado('pais'), lado('pais')), planilha).referencia.texto,
    'a mais próxima de cada uma, entre as unidades de toda a base');
  const nomeada = {...planilha, rotulos: {...planilha.rotulos, todo: {nome: 'Solária', artigo: 'a'}}};
  assert.equal(M.fraseDaConsulta(consulta(lado('pais'), lado('pais')), nomeada).referencia.texto,
    'a mais próxima de cada uma, entre as unidades da Solária');
  // Os candidatos e as referências usadas (27/10/2026, pedido do responsável: "175 municípios" na Referência parecia a referência,
  // quando só o mais próximo de cada território da base é usado).
  assert.deepEqual([M.quantosCandidatos(175, BR.unidade), M.quantosCandidatos(1, BR.unidade), M.quantosCandidatos(2, planilha.rotulos.unidade)],
    ['175 candidatos', '1 candidato', '2 candidatas']);
  const usadas = (tipo, candidatos, referencias, base = null, rotulos = BR) => M.textoDasReferenciasUsadas({rotulos, brasil: rotulos === BR,
    tipo, candidatos, usadas: referencias && {referencias, base}});
  assert.equal(usadas('ufs', 175, null), 'Para cada município da base, só o candidato mais próximo fica como referência.');
  assert.equal(usadas('mesma_uf_da_base', 3455, null),
    'Para cada município da base, só o candidato mais próximo fica como referência, entre os do mesmo estado.');
  assert.equal(usadas('ufs', 175, ['ITAGUACU DA BAHIA (BA)'], 'PILAO ARCADO (BA)'),
    'Ficou como referência 1 dos 175 candidatos: ITAGUACU DA BAHIA (BA), o mais próximo de PILAO ARCADO (BA).');
  assert.equal(usadas('ufs', 3, ['CRUZEIRO DO SUL (AC)', 'RIO BRANCO (AC)']),
    'Ficaram como referência 2 dos 3 candidatos: CRUZEIRO DO SUL (AC) e RIO BRANCO (AC), cada um o mais próximo de algum município da base.');
  assert.equal(usadas('ufs', 3, ['RIO BRANCO (AC)']), 'Ficou como referência 1 dos 3 candidatos: RIO BRANCO (AC), o mais próximo dos ' +
    'municípios da base.');
  assert.equal(usadas('mesma_uf_da_base', 3455, ['A', 'B', 'C', 'D']), 'Ficaram como referência 4 dos 3.455 candidatos: A, B, C e mais 1, ' +
    'cada um o mais próximo de algum município da base no mesmo estado.');
  assert.equal(usadas('pais', 1, ['MANAUS (AM)'], 'TEFE (AM)'), 'Ficou como referência o único candidato: MANAUS (AM), o mais próximo de TEFE (AM).');
  assert.equal(usadas('pais', 3, []), 'Nenhum dos 3 candidatos ficou como referência de um município da base.');
  assert.equal(usadas('ufs', 0, []), 'Sem candidatos, nenhum município da base tem referência.');
  assert.equal(usadas('mesma_uf_da_base', 2, ['X', 'Y'], null, planilha.rotulos), 'Ficaram como referência 2 das 2 candidatas: X e Y, cada ' +
    'uma a mais próxima de alguma unidade da base na mesma província.');
  // O pedido: na análise espacial dos municípios, a consulta (como o motor a recebe) e a seleção prévia em `base`. Desde 06/11/2026
  // (item 4.1 do comando, uma seleção só; muda de propósito este teste), sem seleção a base fica incompleta e nada é pedido, também
  // com a consulta (até essa data, a consulta não esperava pela seleção).
  const am = {nivel: 'municipios', base: {todos: false, estados: ['13'], ids: []}};
  const opcoes = M.montarOpcoes(definicao({...am, familia: 'espacial', consulta: rascunho, faixasDistancia: [0, 100]}), 'espacial');
  assert.deepEqual(opcoes.consulta, M.consultaParaOMotor(rascunho));
  assert.deepEqual(opcoes.base, {municipios: {todos: false, estados: ['13'], ids: []}});
  assert.deepEqual(opcoes.faixas_distancia, [0, 100]);
  assert.equal('referencia' in opcoes, false);
  assert.equal(M.familiaCalculada(definicao({...am, familia: 'espacial', consulta: exemplo}), true), 'espacial');
  assert.equal(M.familiaCalculada(definicao({...am, familia: 'espacial'}), true), 'distribuicao');
  const semSelecao = definicao({nivel: 'municipios', familia: 'espacial', consulta: exemplo});
  assert.equal(M.bloqueioDoPedido(semSelecao, {fonte: 'brasil', rotulos: BR}), M.TEXTO_SEM_SELECAO);
  assert.equal(M.semTerritorios(semSelecao), true);
  assert.equal(M.bloqueioDoPedido({...semSelecao, familia: 'distribuicao'}, {fonte: 'brasil', rotulos: BR}), M.TEXTO_SEM_SELECAO);
  assert.equal(M.avisoDaFamilia(definicao({...am, familia: 'espacial'}), {disponivel: true, pendente: false, motivo: ''}), M.TEXTO_ESCOLHA_DA_REFERENCIA);
  // As Grandes Regiões e o valor digitado: a densidade com decimais; a população e a quantidade, inteiros.
  assert.deepEqual(M.REGIOES_DO_BRASIL.map(r => r.nome), ['Norte', 'Nordeste', 'Sudeste', 'Sul', 'Centro-Oeste']);
  assert.deepEqual([M.regiaoDoEstado('12'), M.regiaoDoEstado('43'), M.regiaoDoEstado('53')], ['Norte', 'Sul', 'Centro-Oeste']);
  assert.equal(M.lerValorDeCorte('2,36', 'densidade'), 2.36);
  assert.equal(M.lerValorDeCorte('2.36', 'densidade'), 2.36);
  assert.equal(M.lerValorDeCorte('1.234,5', 'densidade'), 1234.5);
  assert.equal(M.lerValorDeCorte('50.000', 'populacao'), 50000);
  assert.equal(M.lerValorDeCorte(' 50000 ', 'populacao'), 50000);
  assert.equal(M.lerValorDeCorte('0', 'quantidade'), 0);
  assert.equal(M.lerValorDeCorte('2,5', 'quantidade'), null);  // profissionais são inteiros
  assert.equal(M.lerValorDeCorte('-1', 'densidade'), null);
  assert.equal(M.lerValorDeCorte('abc', 'populacao'), null);
  assert.equal(M.lerValorDeCorte('', 'densidade'), null);
  assert.equal(M.lerValorDoFiltro('0,5', 'densidade'), 0.5);
  assert.equal(M.lerValorDoFiltro('20.000', 'populacao'), 20000);
  assert.equal(M.lerValorDoFiltro('2,5', 'quantidade'), null);
  assert.equal(M.UNIDADES_DO_CORTE.densidade.unidade, 'profissionais por 1.000 habitantes');
  assert.equal(M.UNIDADES_DO_CORTE.quantidade.unidade, 'profissionais');
  assert.equal(M.UNIDADES_DO_CORTE.populacao.unidade, 'habitantes');
  // Os textos fixos da janela: OU e NÃO ficam em Critérios combinados; a distância é a geodésica até a referência mais próxima. Os
  // filtros são os mesmos nos dois lados, sem a distância.
  assert.equal(M.TEXTO_DE_APOIO_DOS_FILTROS, 'Densidade é profissionais por 1.000 habitantes. Os filtros valem juntos (E); OU e NÃO ficam em ' +
    'Critérios combinados.');
  assert.equal(M.notaDaDistanciaDaConsulta(BR), 'Distância em linha reta (geodésica) até a referência mais próxima de cada município da base.');
  assert.deepEqual(Object.keys(M.NOMES_DOS_FILTROS), ['densidade', 'populacao', 'quantidade']);
  assert.equal('OPERADORES_DA_DISTANCIA' in M, false);
  assert.deepEqual(M.OPERADORES_DO_FILTRO.map(op => M.TEXTO_DOS_OPERADORES[op]), ['abaixo de', 'até', 'acima de', 'a partir de']);
  // A resposta com a consulta: as contagens de cada lado e a referência mais próxima de cada item (referencia_do_item).
  const r = A.normalizarResposta({competencia: '202406', categoria: 'MEDICINA', nivel: 'municipios', indicador: 'densidade',
    referencia: {tipo: 'consulta', consulta: M.consultaParaOMotor(exemplo), texto: 'do estado escolhido (Acre) com densidade > 2 por 1.000 habitantes',
      base_texto: 'da Região Norte com densidade < 0,5 por 1.000 habitantes', contagens: {
        base: {partir_de: 450, filtros: 40, final: 40, nao_avaliaveis: 0},
        referencia: {partir_de: 22, filtros: 3, final: 3, nao_avaliaveis: 0}},
      membros: [{id: 'code:1200203', rotulo: 'CRUZEIRO DO SUL (AC)', uf: 'AC', populacao: 91888, quantidade: 200, densidade: 2.17}],
      origem: 'Para cada município da base, o município mais próximo…'},
    itens: [municipio('code:1300607', 'BENJAMIN CONSTANT (AM)', {distancia_km: 724.17,
      referencia_do_item: {id: 'code:1200203', rotulo: 'CRUZEIRO DO SUL (AC)', empate: []}})]});
  assert.equal(r.referencia.tipo, 'consulta');
  assert.deepEqual(r.referencia.consulta, M.consultaParaOMotor(exemplo));
  assert.deepEqual(r.referencia.contagens, {base: {partirDe: 450, filtros: 40, final: 40, naoAvaliaveis: 0},
    referencia: {partirDe: 22, filtros: 3, final: 3, naoAvaliaveis: 0}});
  assert.equal('semReferencia' in r.referencia, false);
  assert.equal(r.referencia.texto, 'do estado escolhido (Acre) com densidade > 2 por 1.000 habitantes');
  assert.deepEqual(r.itens[0].referenciaDoItem, [{id: 'code:1200203', rotulo: 'CRUZEIRO DO SUL (AC)'}]);
  const dica = M.montarDica(r.itens[0], {indicador: 'densidade', competencia: '202406', competenciaInicial: null, distancia: true, variacao: false,
    tendencia: false, nomes: new Map(), rotulos: BR, porItem: true});
  assert.deepEqual(dica.linhas.filter(linha => /referência/i.test(linha.rotulo)).map(linha => [linha.rotulo, linha.valor]),
    [['Distância até a referência mais próxima', '724,17 km'], ['Referência mais próxima', 'CRUZEIRO DO SUL (AC)']]);
  const csv = M.montarCsv(r, {familia: 'espacial', indicador: 'densidade', rotulos: BR}).slice(1).split('\r\n');
  assert.ok(csv[0].includes('"Distância até a referência mais próxima (km)";"Referência mais próxima"'), csv[0]);
  assert.ok(!csv[0].includes('Membro da referência'));
  assert.ok(csv[1].includes('"CRUZEIRO DO SUL (AC)"'));
  assert.ok(csv[0].startsWith('"Identificador";"Tipo";"Território";"UF";"Competência"'), csv[0]);
  // A coluna do grupo (28/10/2026): numa planilha, o nome do grupo dela, com a coluna-mãe que o motor devolve (grupo_territorial);
  // sem grupo, nenhuma coluna; "UF" fica só na base do Brasil.
  const daPlanilha = A.normalizarResposta({competencia: '2024', categoria: 'Medicina', nivel: 'municipios', indicador: 'densidade',
    rotulos: {unidade: {singular: 'comuna', plural: 'comunas', genero: 'f'}, grupo: {singular: 'condado', plural: 'condados', genero: 'm'}},
    itens: [{...municipio('code:SOL-0101', 'Vesperina [SOL-0101]'), uf: null, grupo_territorial: 'Alto Vésper'}]});
  assert.equal(daPlanilha.itens[0].grupoTerritorial, 'Alto Vésper');
  const csvDaPlanilha = M.montarCsv(daPlanilha, {familia: 'distribuicao', indicador: 'densidade', rotulos: COMUNAS, brasil: false})
    .slice(1).split('\r\n');
  assert.ok(csvDaPlanilha[0].startsWith('"Identificador";"Tipo";"Território";"Condado";"Competência"') && !csvDaPlanilha[0].includes('"UF"'),
    csvDaPlanilha[0]);
  assert.ok(csvDaPlanilha[1].startsWith('"code:SOL-0101";"comuna";"Vesperina [SOL-0101]";"Alto Vésper";"2024"'), csvDaPlanilha[1]);
  const semGrupo = M.montarCsv(daPlanilha, {familia: 'distribuicao', indicador: 'densidade', rotulos: {...COMUNAS, grupo: null},
    brasil: false}).slice(1).split('\r\n');
  assert.ok(semGrupo[0].startsWith('"Identificador";"Tipo";"Território";"Competência"'), semGrupo[0]);
  // O nome do grupo que repete outro cabeçalho (29/10/2026): com os nomes que o modelo de planilha sugere, unidade e grupo se
  // chamam "território", e o CSV tinha duas colunas "Território".
  const territorios = {unidade: {singular: 'território', plural: 'territórios', genero: 'm'},
    grupo: {singular: 'território', plural: 'territórios', genero: 'm'}};
  const repetido = M.montarCsv(daPlanilha, {familia: 'distribuicao', indicador: 'densidade', rotulos: territorios, brasil: false})
    .slice(1).split('\r\n');
  assert.ok(repetido[0].startsWith('"Identificador";"Tipo";"Território";"Território (grupo)";"Competência"'), repetido[0]);
  assert.deepEqual(M.ligacoesDoMapa(r.itens, ['code:1300607']), [{de: 'code:1300607', para: ['code:1200203']}]);
  // As contagens da janela (POST /api/painel/territorios), nos tipos da tela; nada é calculado aqui.
  const t = A.normalizarTerritorios({competencia: '202406', categoria: 'MEDICINA', selecao_previa: {total: 62, nomes: ['ALVARAES (AM)']},
    base: {contagens: {partir_de: 450, filtros: 40, final: null, nao_avaliaveis: 0}, pendencias: ['marque ao menos um município'],
      previa: null, marcados: []},
    referencia: {contagens: {partir_de: 22, filtros: 3, final: 3, nao_avaliaveis: 0}, pendencias: [],
      previa: {total: 3, nomes: ['BRASILEIA (AC)', 'CRUZEIRO DO SUL (AC)', 'RIO BRANCO (AC)']},
      marcados: [{id: 'code:1200401', rotulo: 'RIO BRANCO (AC)', uf: 'AC', densidade: 2.9, passa: true}]},
    lista: {lado: 'referencia', busca: 'rio', total: 1, limite: 100, itens: [{id: 'code:1200401', rotulo: 'RIO BRANCO (AC)', uf: 'AC', densidade: 2.9}]}});
  assert.deepEqual(t.selecaoPrevia, {total: 62, nomes: ['ALVARAES (AM)']});
  assert.deepEqual(t.base.contagens, {partirDe: 450, filtros: 40, final: null, naoAvaliaveis: 0});
  assert.deepEqual(t.base.pendencias, ['marque ao menos um município']);
  assert.deepEqual(t.referencia.previa, {total: 3, nomes: ['BRASILEIA (AC)', 'CRUZEIRO DO SUL (AC)', 'RIO BRANCO (AC)']});
  assert.deepEqual(t.referencia.marcados, [{id: 'code:1200401', rotulo: 'RIO BRANCO (AC)', uf: 'AC', densidade: 2.9, passa: true}]);
  assert.deepEqual(t.lista, {lado: 'referencia', busca: 'rio', total: 1, limite: 100, itens: [{id: 'code:1200401', rotulo: 'RIO BRANCO (AC)', uf: 'AC', densidade: 2.9}]});
  assert.throws(() => A.normalizarTerritorios(null), /não segue o contrato/);
  // A apresentação da análise espacial fala da Escolha dos territórios, e o próprio território nunca é referência.
  const espacial = M.apresentacaoDaAba('espacial', {rotulos: BR, brasil: true, comGrupos: true}).paragrafos.join(' ');
  // Desde 06/11/2026 (item 4.1 do comando), a base é sempre a seleção em uso; a janela escolhe a referência em três etapas.
  assert.ok(espacial.includes('A base é sempre a seleção em uso, a da trilha e da Seleção de Territórios'), espacial);
  assert.ok(espacial.includes('Na Escolha dos territórios, a referência é escolhida em três etapas'), espacial);
  assert.ok(espacial.includes('no mesmo estado ou na mesma região de cada município da base'), espacial);
  assert.ok(espacial.includes('O próprio município nunca é a sua referência'), espacial);
  assert.ok(!/mais distante|pelo nome|um conjunto deles|também pela distância/.test(espacial), espacial);
  assert.ok(M.apresentacaoDaAba('espacial', {rotulos: DISTRITOS, brasil: false, comGrupos: true}).paragrafos[0]
    .includes('toda a base, uma ou mais províncias ou a seleção prévia'));  // até 07/11/2026, "a planilha inteira"
  assert.ok(espacial.includes('a referência mais próxima dele.') && espacial.includes('todos os que atendem ou só dos marcados'), espacial);
  // Com a unidade feminina (28/10/2026): "dela" (antes saía "delea") e "todas as que atendem ou só das marcadas".
  const comunas = M.apresentacaoDaAba('espacial', {rotulos: COMUNAS, brasil: false, comGrupos: true}).paragrafos.join(' ');
  assert.ok(comunas.includes('entre cada comuna da base e a referência mais próxima dela.'), comunas);
  assert.ok(comunas.includes('todas as que atendem ou só das marcadas') && !/delea|todos os que/.test(comunas), comunas);
});

test('base e referência (25/10/2026; Escolha dos territórios, 27/10/2026): cada território da base ligado à referência mais próxima, com os valores do motor', () => {
  // Com a Escolha dos territórios, o motor manda a UF e os valores de cada referência; o item diz qual é a mais próxima dele.
  const SEM_REF = 'Sem referência no recorte: nenhum outro município da referência no mesmo estado (Roraima) em junho de 2024 ' +
    '(DEPENDENCIA_NAO_AVALIAVEL, CONJUNTO_REFERENCIAS_VAZIO)';
  const r = A.normalizarResposta({competencia: '202406', categoria: 'MEDICINA', nivel: 'municipios', indicador: 'densidade',
    referencia: {tipo: 'consulta', texto: 'de todo o país com densidade > 2 por 1.000 habitantes',
      contagens: {base: {partir_de: 15, filtros: 15, final: 15, nao_avaliaveis: 0},
        referencia: {partir_de: 5570, filtros: 2510, final: 2510, nao_avaliaveis: 0}},
      membros: [{id: 'code:130353', rotulo: 'PRESIDENTE FIGUEIREDO (AM)', uf: 'AM', populacao: 33004, quantidade: 71, densidade: 2.1512543934068598},
        {id: 'code:140010', rotulo: 'BOA VISTA (RR)', uf: 'RR', populacao: 470169, quantidade: 1181, densidade: 2.5118627557325133}],
      origem: 'Para cada município da base, o município mais próximo…'},
    itens: [
      municipio('code:140002', 'AMAJARI (RR)', {populacao: 15583, distancia_km: 124.43, referencia_do_item: {id: 'code:140010', rotulo: 'BOA VISTA (RR)', empate: []}}),
      municipio('code:140010', 'BOA VISTA (RR)', {populacao: 470169, quantidade: 1181, densidade: 2.5118627557325133, distancia_km: 543.82,
        referencia_do_item: {id: 'code:130353', rotulo: 'PRESIDENTE FIGUEIREDO (AM)', empate: []}}),
      municipio('code:140015', 'BONFIM (RR)', {distancia_km: null, referencia_do_item: null, motivos: [SEM_REF]}),
      municipio('code:140020', 'CARACARAI (RR)', {distancia_km: 100, referencia_do_item: {id: 'code:140010', rotulo: 'BOA VISTA (RR)',
        empate: [{id: 'code:140010', rotulo: 'BOA VISTA (RR)'}, {id: 'code:130353', rotulo: 'PRESIDENTE FIGUEIREDO (AM)'}]}}),
      {...municipio('c1', 'Juntos'), tipo: 'conjunto'}, {...municipio('uf:14', 'Roraima (RR)'), tipo: 'estado'}]});
  assert.deepEqual(r.referencia.membros[0], {id: 'code:130353', rotulo: 'PRESIDENTE FIGUEIREDO (AM)', uf: 'AM', populacao: 33004, quantidade: 71,
    densidade: 2.1512543934068598});
  // Os territórios da base na resposta: as unidades, sem conjuntos nem estados, na ordem dos nomes.
  const bases = M.basesPossiveis(r.itens);
  assert.deepEqual(bases.map(base => base.rotulo), ['AMAJARI (RR)', 'BOA VISTA (RR)', 'BONFIM (RR)', 'CARACARAI (RR)']);
  const TODAS = ['code:140002', 'code:140010', 'code:140015', 'code:140020'];
  // A referência fora da base: contexto no gráfico (não é desenhada lá), com os valores dos membros e a distância do item.
  const boaVista = M.parDaBase(r, 'code:140010');
  assert.equal(boaVista.base.id, 'code:140010');
  assert.deepEqual(boaVista.referencias, [{id: 'code:130353', rotulo: 'PRESIDENTE FIGUEIREDO (AM)', uf: 'AM', populacao: 33004, quantidade: 71,
    densidade: 2.1512543934068598, noGrafico: false, emAnalise: false}]);
  assert.deepEqual([boaVista.distancia, boaVista.motivo], [543.82, null]);
  assert.equal(M.textoDoParDaBase(boaVista), 'Base: BOA VISTA (RR) · referência mais próxima: PRESIDENTE FIGUEIREDO (AM), a 543,82 km em linha reta.');
  // A referência que também está na base (com a sua própria distância): o contexto continua.
  const [deAmajari] = M.parDaBase(r, 'code:140002').referencias;
  assert.deepEqual([deAmajari.id, deAmajari.noGrafico, deAmajari.emAnalise, deAmajari.densidade], ['code:140010', false, true, 2.5118627557325133]);
  // Empate: todas as empatadas, a primeira antes (CAP-ESP-02); sem referência no recorte, o motivo do motor; sem base ou com a base
  // fora da resposta, nada.
  const caracarai = M.parDaBase(r, 'code:140020');
  assert.deepEqual(caracarai.referencias.map(ref => ref.id), ['code:140010', 'code:130353']);
  assert.equal(M.textoDoParDaBase(caracarai), 'Base: CARACARAI (RR) · referência mais próxima: BOA VISTA (RR) (empate com PRESIDENTE ' +
    'FIGUEIREDO (AM)), a 100,00 km em linha reta.');
  const bonfim = M.parDaBase(r, 'code:140015');
  assert.deepEqual([bonfim.referencias, bonfim.motivo], [[], SEM_REF]);
  assert.equal(M.textoDoParDaBase(bonfim), 'Base: BONFIM (RR). ' + SEM_REF);
  assert.equal(M.parDaBase(r, 'c1'), null);
  assert.equal(M.parDaBase(r, 'code:999999'), null);
  assert.equal(M.parDaBase(r, null), null);
  assert.equal(M.parDaBase(null, 'code:140010'), null);
  // Um par por território da base, na ordem dos nomes; as referências de contexto uma vez cada, com os territórios ligados a elas e
  // a distância de cada um.
  const pares = M.paresDasBases(r, bases.map(base => base.id));
  assert.deepEqual(pares.map(par => par.base.id), TODAS);
  assert.deepEqual(M.paresDasBases(r, ['code:140010', 'code:999999']).map(par => par.base.id), ['code:140010']);
  const contextos = M.referenciasDeContexto(pares);
  assert.deepEqual(contextos.map(c => [c.referencia.id, c.bases.map(item => [item.base.id, item.distancia])]), [
    ['code:140010', [['code:140002', 124.43], ['code:140020', 100]]],
    ['code:130353', [['code:140010', 543.82], ['code:140020', 100]]]]);
  // A dica de uma referência de contexto: os valores do motor e a distância até cada território da base ligado a ela.
  const [deBoaVista, dePresidente] = contextos;
  const dica = M.dicaDaReferenciaDeContexto(dePresidente);
  assert.equal(dica.titulo, 'PRESIDENTE FIGUEIREDO (AM)');
  assert.equal(dica.subtitulo, 'Referência mais próxima de BOA VISTA (RR) e CARACARAI (RR)');
  assert.deepEqual(dica.linhas.map(linha => [linha.rotulo, linha.valor]), [['População', '33.004 habitantes'], ['Profissionais', '71'],
    ['Densidade', '2,15 por 1.000 habitantes'], ['Distância até BOA VISTA (RR)', '543,82 km'], ['Distância até CARACARAI (RR)', '100,00 km']]);
  assert.deepEqual(dica.notas, ['Fora da base: aparece só como referência, no início do eixo (0 km).']);
  assert.match(M.dicaDaReferenciaDeContexto(deBoaVista).notas[0], /^Também está na base/);
  // Com mais de quatro territórios ligados à mesma referência: três nomes no subtítulo, as quatro primeiras distâncias e quantas faltam.
  const seis = {referencia: dePresidente.referencia, bases: Array.from({length: 6}, (_, i) => ({base: {...r.itens[0], rotulo: 'B' + i}, distancia: i}))};
  const cheia = M.dicaDaReferenciaDeContexto(seis);
  assert.equal(cheia.subtitulo, 'Referência mais próxima de B0, B1, B2 e mais 3');
  assert.deepEqual(cheia.linhas.slice(3).map(linha => linha.rotulo), ['Distância até B0', 'Distância até B1', 'Distância até B2', 'Distância até B3']);
  assert.equal(cheia.notas[0], 'E mais 2 territórios da base ligados a esta referência (as distâncias estão na tabela).');
  // A linha acima do desenho: com um território na base, o par dele; com mais, quantos, os quatro primeiros pares e, quando o gráfico
  // liga menos do que os pares com referência, quantas ligações ele desenha; sem base, o que falta.
  assert.equal(M.textoDosTerritoriosBase({pares: [boaVista], ligados: 1}), M.textoDoParDaBase(boaVista));
  assert.equal(M.textoDosTerritoriosBase({pares: [boaVista], ligados: 0}),
    M.textoDoParDaBase(boaVista) + ' Nenhuma ligação à vista no gráfico: a bolha da base está fora da régua ou dos filtros.');
  assert.equal(M.textoDosTerritoriosBase({pares, ligados: 3}),
    'Base: 4 · cada um ligado à sua referência mais próxima por linha tracejada: AMAJARI (RR) → BOA VISTA (RR), 124,43 km; BOA VISTA (RR) → ' +
    'PRESIDENTE FIGUEIREDO (AM), 543,82 km; BONFIM (RR): sem referência; CARACARAI (RR) → BOA VISTA (RR) ou PRESIDENTE FIGUEIREDO (AM) ' +
    '(empate), 100,00 km.');
  assert.match(M.textoDosTerritoriosBase({pares: [...pares, M.parDaBase(r, 'code:140002')], ligados: 2}),
    /^Base: 5 · cada um ligado à sua referência mais próxima por linha tracejada: .+; e mais 1 \(nas dicas e na tabela\)\. O gráfico desenha 2 dessas ligações: no máximo 30, e só das bolhas à vista\.$/);
  assert.equal(M.textoDosTerritoriosBase({pares: [], ligados: 0}),
    'Nenhum território na base: o gráfico e o mapa não mostram as ligações até a referência.');
  // Com a unidade feminina (28/10/2026), "cada uma ligada"; com os rótulos do Brasil, como antes.
  assert.ok(M.textoDosTerritoriosBase({pares, ligados: 3, rotulos: COMUNAS}).startsWith('Base: 4 · cada uma ligada à sua referência mais próxima'));
  assert.ok(M.textoDosTerritoriosBase({pares, ligados: 3, rotulos: BR}).startsWith('Base: 4 · cada um ligado à sua referência mais próxima'));
  // Pelos membros escolhidos (o contrato de 21/10), o membro já está no gráfico, a distância zero, com a mira: os valores vêm do
  // item, a ligação vai até a bolha dele, e ele não entra como contexto.
  const pelosMembros = A.normalizarResposta({competencia: '202406', categoria: 'MEDICINA', nivel: 'municipios', indicador: 'densidade',
    referencia: {tipo: 'municipio', membros: [{id: 'code:130260', rotulo: 'MANAUS (AM)'}], origem: 'Referência escolhida.'},
    itens: [municipio('code:130260', 'MANAUS (AM)', {populacao: 2000, quantidade: 50, densidade: 25, distancia_km: 0, referencia: true}),
      municipio('code:130420', 'TEFE (AM)', {distancia_km: 522.5, referencia_mais_proxima: {id: 'code:130260', rotulo: 'MANAUS (AM)', empate: []}})]});
  const tefe = M.parDaBase(pelosMembros, 'code:130420');
  const [manaus] = tefe.referencias;
  assert.deepEqual([manaus.noGrafico, manaus.emAnalise, manaus.populacao, manaus.densidade], [true, false, 2000, 25]);
  assert.deepEqual(M.parDaBase(pelosMembros, 'code:130260').referencias, []);  // o próprio membro não tem outra referência
  assert.deepEqual(M.referenciasDeContexto([tefe]), []);
  assert.deepEqual(M.basesPossiveis(pelosMembros.itens).map(base => base.id), ['code:130420']);  // o membro é a referência, não base
  // O estado salvo guarda a consulta; um estado de antes da Escolha dos territórios vira a consulta equivalente (a referência por
  // elegibilidade ou pelos membros, com os territórios base de então como marcados); o "mais distante" não tem equivalente.
  const consulta = M.consultaInicial({comSelecao: true});
  const espacial = definicao({nivel: 'municipios', base: {todos: false, estados: ['14'], ids: []}, familia: 'espacial', consulta});
  assert.equal(M.definicaoInicial({tipo: 'brasil', periodos: ['202406'], categoria: 'MEDICINA', temGrupos: true}).consulta, null);
  const salvar = def => M.salvarEstado('t', {chave: 'k', familia: 'espacial', opcoes: null, definicao: def,
    visual: {escala: 'linear', corte: null, selecionados: []}}, null);
  assert.deepEqual(M.lerEstadoSalvo(salvar(espacial)).definicao.consulta, consulta);
  assert.equal(M.lerEstadoSalvo(salvar({...espacial, consulta: {base: 7}})).definicao.consulta, null);
  const {consulta: _, ...semConsulta} = espacial;
  const deAntes = (extra) => M.lerEstadoSalvo(salvar({...semConsulta, ...extra})).definicao;
  const elegivel = {relacao: 'mais_proxima', delimitacao: {tipo: 'mesmo_grupo'}, condicao: {atributo: 'densidade', operador: '>', valor: 2}};
  const migrada = deAntes({referencia: elegivel, territoriosBase: ['code:140010', 7]});
  // Desde 06/11/2026 (item 4.1, uma seleção só; muda de propósito este teste), os territórios base de então viram a seleção, e a
  // base da consulta é a seleção em uso; antes, eles ficavam como os marcados da base.
  assert.deepEqual(migrada.consulta, {base: {partir_de: {tipo: 'selecao_previa', regioes: [], ufs: []}, filtros: [],
    escolha: {modo: 'todos', municipios: []}}, referencia: {partir_de: {tipo: 'mesma_uf_da_base', regioes: [], ufs: []},
    filtros: [{indicador: 'densidade', operador: '>', valor: 2}], escolha: {modo: 'todos', municipios: []}},
    distancia: {medida: 'geodesica', ate: 'referencia_mais_proxima'}});
  assert.deepEqual([migrada.base, migrada.nivel], [{todos: false, estados: [], ids: ['code:140010']}, 'municipios']);
  const lidaMigrada = M.lerEstadoSalvo(salvar({...semConsulta, referencia: elegivel, territoriosBase: ['code:140010']}));
  assert.deepEqual([lidaMigrada.resposta, lidaMigrada.chave, lidaMigrada.opcoes], [null, '', null]);  // calculada de novo
  assert.deepEqual(['referencia' in migrada, 'territoriosBase' in migrada], [false, false]);
  assert.deepEqual(deAntes({referencia: {...elegivel, delimitacao: {tipo: 'regioes', valores: ['Norte']}}, territoriosBase: null}).consulta.referencia.partir_de,
    {tipo: 'regioes', regioes: ['Norte'], ufs: []});
  assert.deepEqual(deAntes({referencia: {...elegivel, delimitacao: {tipo: 'grupos', valores: ['12']}}}).consulta.base.escolha, {modo: 'todos', municipios: []});
  assert.deepEqual(deAntes({referencia: {membros: ['code:130260']}, territorioBase: 'code:140010'}).consulta.referencia,
    {partir_de: {tipo: 'pais', regioes: [], ufs: []}, filtros: [], escolha: {modo: 'marcados', municipios: ['code:130260']}});
  assert.equal(deAntes({referencia: {...elegivel, relacao: 'mais_distante'}}).consulta, null);
  assert.equal(deAntes({referencia: null}).consulta, null);
  // A referência pelo nome pedida na conversa vira os marcados da Referência, a partir do país; a base é a seleção em uso, com os
  // filtros da consulta (06/11/2026).
  const pedida = M.consultaComReferenciaMarcada(consulta, ['code:130260'], true);
  assert.deepEqual(pedida.base, consulta.base);
  const comFiltro = {...consulta, base: {partir_de: {tipo: 'pais', regioes: [], ufs: []}, filtros: [{indicador: 'densidade', operador: '<', valor: 1}],
    escolha: {modo: 'todos', municipios: []}}};
  assert.deepEqual(M.consultaComReferenciaMarcada(comFiltro, ['code:130260']).base, {partir_de: {tipo: 'selecao_previa', regioes: [], ufs: []},
    filtros: [{indicador: 'densidade', operador: '<', valor: 1}], escolha: {modo: 'todos', municipios: []}});
  assert.deepEqual(pedida.referencia, {partir_de: {tipo: 'pais', regioes: [], ufs: []}, filtros: [], escolha: {modo: 'marcados', municipios: ['code:130260']}});
  // O gráfico cobre as referências de contexto: o eixo com o valor delas e a escala de tamanho com a população delas.
  const grafico = (extra = {}) => M.montarGrafico({itens: r.itens.slice(0, 2), dominios: {}, indicador: 'densidade', escala: 'linear',
    distancia: true, cometa: false, vista: 'final', largura: 900, rotuloDistancia: 'Distância (km)', pintura: () => ({cor: '#123', vazada: false, apagada: false}), ...extra});
  assert.equal(grafico().populacaoMaxima, 470169);
  assert.equal(grafico({extrasPopulacao: [900000]}).populacaoMaxima, 900000);
  assert.ok(grafico().eixoY.dominio[1] < 40, String(grafico().eixoY.dominio));
  const alto = grafico({extras: [40]});
  assert.ok(alto.eixoY.dominio[1] >= 40, String(alto.eixoY.dominio));
});

test('conversa (28/10/2026): a Escolha dos territórios pedida vale como a feita na janela; a inválida vira mensagem; o contexto leva a consulta', () => {
  const c = {periodos: ['202306', '202406'], nomes: new Map(), temGrupos: true,
    disponivel: f => M.disponibilidadeDaFamilia(f, {fonte: 'brasil', nivel: 'municipios', disponibilidade: null, temIdentificador: false, rotulos: BR})};
  const lado = (tipo, {filtros = [], modo = 'todos', municipios = []} = {}) => ({partir_de: {tipo, regioes: [], ufs: []}, filtros,
    escolha: {modo, municipios}});
  // "O município de menor densidade e o mais próximo a ele com densidade de no mínimo 1,5": o extremo na base (marcado) e, na
  // referência, os da seleção com a condição.
  const pedida = {base: lado('selecao_previa', {modo: 'marcados', municipios: ['code:171888']}),
    referencia: lado('selecao_previa', {filtros: [{indicador: 'densidade', operador: '>=', valor: 1.5}]}),
    distancia: {medida: 'geodesica', ate: 'referencia_mais_proxima'}};
  const tocantins = definicao({base: {todos: false, estados: ['17'], ids: []}, comparar: ['code:170210', 'code:172100']});
  const r = M.aplicarPedido(tocantins, {familia: 'espacial', nivel: 'municipios', consulta: JSON.parse(JSON.stringify(pedida))}, c);
  assert.deepEqual([r.definicao.familia, r.definicao.nivel, r.mensagens, r.abrir], ['espacial', 'municipios', [], null]);
  assert.deepEqual(r.definicao.comparar, []);  // a base passa a ser a da consulta: a comparação de antes sai
  // Desde 06/11/2026 (item 4.1 do comando, uma seleção só; muda de propósito este teste): a base marcada vira a seleção (a trilha
  // vai a ela), a base da consulta é a seleção em uso, e a referência que partia da seleção nomeia a de antes (o Tocantins
  // inteiro). Até essa data, a seleção continuava o Tocantins, e a base da consulta guardava o extremo como marcado.
  assert.deepEqual(r.definicao.base, {todos: false, estados: [], ids: ['code:171888']});
  assert.deepEqual(r.definicao.consulta, {base: lado('selecao_previa'),
    referencia: {partir_de: {tipo: 'ufs', regioes: [], ufs: ['17']}, filtros: [{indicador: 'densidade', operador: '>=', valor: 1.5}],
      escolha: {modo: 'todos', municipios: []}}, distancia: {medida: 'geodesica', ate: 'referencia_mais_proxima'}});
  // Com municípios avulsos na seleção de antes, a referência os nomeia, com os de cada estado inteiro.
  const avulsos = definicao({base: {todos: false, estados: ['11'], ids: ['code:130260']}});
  const comAvulsos = M.aplicarPedido(avulsos, {consulta: pedida}, {...c, unidadesDoGrupo: g => g === '11' ? ['code:110001', 'code:110002'] : []});
  assert.deepEqual(comAvulsos.definicao.consulta.referencia.partir_de, {tipo: 'pais', regioes: [], ufs: []});
  assert.deepEqual(comAvulsos.definicao.consulta.referencia.escolha, {modo: 'marcados', municipios: ['code:110001', 'code:110002', 'code:130260']});
  // Uma base que já é a seleção em uso não muda a seleção.
  const naSelecao = M.aplicarPedido(tocantins, {consulta: {...pedida, base: lado('selecao_previa')}}, c);
  assert.deepEqual(naSelecao.definicao.base, tocantins.base);
  assert.equal(M.consultaEmUso(r.definicao), true);
  assert.equal(M.familiaCalculada(r.definicao, true), 'espacial');
  // Forma que não confere: nada muda, e a mensagem diz o motivo.
  const invalida = M.aplicarPedido(tocantins, {consulta: {...pedida, base: lado('mesma_uf_da_base')}}, c);
  assert.deepEqual([invalida.definicao.familia, invalida.definicao.consulta, invalida.mensagens],
    ['distribuicao', null, ['A Escolha dos territórios pedida não foi reconhecida.']]);
  // A seleção prévia sem territórios escolhidos: aplica e avisa (nada é escolhido em silêncio). Desde 06/11/2026, o extremo vira a
  // seleção, e a referência que partia da seleção vazia continua nela, sem virar o país inteiro.
  const semSelecao = M.aplicarPedido(definicao(), {consulta: pedida}, c);
  assert.deepEqual(semSelecao.mensagens, ['A Escolha dos territórios parte da seleção prévia: escolha os territórios na Seleção de Territórios.']);
  assert.deepEqual(semSelecao.definicao.base, {todos: false, estados: [], ids: ['code:171888']});
  assert.deepEqual(semSelecao.definicao.consulta.referencia.partir_de, {tipo: 'selecao_previa', regioes: [], ufs: []});
  // O contexto da conversa leva a consulta em uso (para "e em todo o país?"), só na Análise Espacial com a consulta.
  assert.deepEqual(M.contextoDoGrafico(r.definicao, [], 'Título').consulta, M.consultaParaOMotor(r.definicao.consulta));
  assert.equal(M.contextoDoGrafico(tocantins, [], 'Título').consulta, null);
  assert.equal(M.contextoDoGrafico({...r.definicao, familia: 'distribuicao'}, [], 'Título').consulta, null);
});

test('decisão 4 (25/10/2026): "maior/menor" da conversa vira o operador; Limpar seleção tira a seleção inteira (05/11/2026)', () => {
  // Decisão 4: a ordem do critério da conversa vira o operador da condição; o valor de corte, a relação e a delimitação ficam com
  // a pessoa (nenhum território é escolhido pela posição na ordem).
  assert.equal(M.operadorDoCriterio({atributo: 'densidade', ordem: 'desc'}), '>');
  assert.equal(M.operadorDoCriterio({atributo: 'populacao', ordem: 'asc'}), '<');
  assert.equal(M.operadorDoCriterio(null), null);
  // Desde a seleção unificada (05/11/2026; antes, a decisão 5 de 25/10/2026: cada nível guardava a sua escolha, e Limpar tirava só a
  // do nível em uso): Limpar tira a árvore inteira, os estados como unidades e os conjuntos, e a unidade volta aos municípios.
  const municipios = {todos: false, estados: ['13'], ids: ['code:150140']};
  const conjunto = {nome: 'Conjunto 1', membros: ['code:130260', 'code:130340']};
  const vazia = {nivel: 'municipios', base: {todos: false, estados: [], ids: []}, estados: [], conjuntos: []};
  assert.deepEqual(M.limparEscolha({nivel: 'municipios', base: municipios, estados: [], conjuntos: [conjunto]}), vazia);
  assert.deepEqual(M.limparEscolha({nivel: 'municipios', base: {todos: true, estados: [], ids: []}, estados: [], conjuntos: []}), vazia);
  assert.deepEqual(M.limparEscolha({nivel: 'estados', base: {todos: false, estados: ['13', '15'], ids: []}, estados: ['13', '15'], conjuntos: []}), vazia);
  assert.deepEqual(M.limparEscolha({nivel: 'brasil', base: {todos: true, estados: [], ids: []}, estados: [], conjuntos: []}), vazia);
  // Sem nada marcado, nada a limpar.
  assert.equal(M.limparEscolha(vazia), null);
});

test('seleção unificada (05/11/2026): equivalências completas, unidades de análise permitidas e a árvore alinhada aos pedidos', () => {
  // Três estados de brinquedo: 13 com três municípios, 15 com dois e 35 com um; seis municípios no total.
  const membros = {'13': ['code:130001', 'code:130002', 'code:130003'], '15': ['code:150001', 'code:150002'], '35': ['code:350001']};
  const grupos = Object.entries(membros).map(([id, ids]) => ({id, nome: 'Estado ' + id, sigla: '', rotuloGrupo: '', unidades: ids.length}));
  const c = {grupos, unidadesDoGrupo: g => membros[g] ?? [], grupoDe: id => id.slice(5, 7), total: 6};
  const base = (estados = [], ids = [], todos = false) => ({todos, estados, ids});
  // Os municípios de um estado marcados todos, um a um, viram o estado inteiro; todos os estados inteiros, o Brasil inteiro.
  assert.deepEqual(M.normalizarArvore(base([], ['code:150001', 'code:150002', 'code:130001']), c), base(['15'], ['code:130001']));
  assert.deepEqual(M.normalizarArvore(base(['13', '15'], ['code:350001']), c), base([], [], true));
  // Um estado inteiro absorve os seus municípios avulsos (sem sobreposição).
  assert.deepEqual(M.normalizarArvore(base(['13'], ['code:130002']), c), base(['13'], []));
  // Numa planilha em que os grupos não cobrem todas as unidades, todos os grupos inteiros não viram "todos".
  assert.deepEqual(M.normalizarArvore(base(['13', '15', '35']), {...c, total: 7}), base(['13', '15', '35']));
  // Unidades permitidas: os estados só com estados inteiros (sem avulsos); o Brasil só com o Brasil inteiro; sem nada, os atalhos.
  assert.deepEqual(M.unidadesPossiveis(base(['13', '15']), c), {estados: ['13', '15'], brasil: false, vazia: false});
  assert.deepEqual(M.unidadesPossiveis(base(['13'], ['code:150001']), c), {estados: null, brasil: false, vazia: false});
  assert.deepEqual(M.unidadesPossiveis(base([], [], true), c), {estados: ['13', '15', '35'], brasil: true, vazia: false});
  assert.deepEqual(M.unidadesPossiveis(base(), c), {estados: null, brasil: false, vazia: true});
  // A unidade de análise escolhida.
  const escolha = (nivel, b, estados = []) => ({nivel, base: b, estados, conjuntos: []});
  assert.deepEqual(M.escolhaDaUnidade(escolha('municipios', base(['13', '15'])), 'estados', c), escolha('estados', base(['13', '15']), ['13', '15']));
  assert.equal(M.escolhaDaUnidade(escolha('municipios', base(['13'], ['code:150001'])), 'estados', c), null);
  assert.equal(M.escolhaDaUnidade(escolha('municipios', base(['13'])), 'brasil', c), null);
  assert.deepEqual(M.escolhaDaUnidade(escolha('municipios', base()), 'estados', c), escolha('estados', base([], [], true), ['13', '15', '35']));
  assert.deepEqual(M.escolhaDaUnidade(escolha('municipios', base()), 'brasil', c), escolha('brasil', base([], [], true)));
  assert.deepEqual(M.escolhaDaUnidade(escolha('estados', base(['13']), ['13']), 'municipios', c), escolha('municipios', base(['13']), ['13']));
  // Uma mudança na árvore: a unidade continua quando ainda vale; senão, volta aos municípios.
  assert.deepEqual(M.escolhaDaArvore(escolha('estados', base(['13', '15']), ['13', '15']), base(['13']), c), escolha('estados', base(['13']), ['13']));
  assert.deepEqual(M.escolhaDaArvore(escolha('estados', base(['13']), ['13']), base([], ['code:130001', 'code:130002']), c),
    escolha('municipios', base([], ['code:130001', 'code:130002']), ['13']));
  assert.deepEqual(M.escolhaDaArvore(escolha('brasil', base([], [], true)), base(['13', '15']), c), escolha('municipios', base(['13', '15'])));
  assert.deepEqual(M.escolhaDaArvore(escolha('brasil', base([], [], true)), base(['13', '15', '35']), c), escolha('brasil', base([], [], true)));
  // A escolha de fora da árvore (a conversa, o Histórico): a árvore marca o que está na análise.
  assert.deepEqual(M.unificarEscolha(escolha('estados', base(['35'], ['code:130001']), ['13', '15']), c), escolha('estados', base(['13', '15']), ['13', '15']));
  assert.deepEqual(M.unificarEscolha(escolha('brasil', base(['13'])), c), escolha('brasil', base([], [], true)));
  assert.deepEqual(M.unificarEscolha(escolha('municipios', base(['13', '15', '35'])), c), escolha('municipios', base([], [], true)));
  // Os estados marcados em parte não têm total individualizado: a tela diz quais, com quantos de quantos.
  assert.deepEqual(M.gruposParciais(base(['15'], ['code:130001']), c), [{id: '13', nome: 'Estado 13', marcadas: 1, total: 3}]);
  assert.deepEqual(M.gruposParciais(base([], [], true), c), []);
  // O motivo, quando a unidade não vale.
  assert.ok(M.motivoDaUnidade('estados', BR).includes('inteiros'));
  assert.ok(M.motivoDaUnidade('brasil', BR).includes('Brasil inteiro'));
  // Numa planilha (07/11/2026, item 1 do comando), cada grupo vem das unidades dele: nada de contagem estadual.
  const PLANILHA = {unidade: {singular: 'comuna', plural: 'comunas', genero: 'f'}, grupo: {singular: 'condado', plural: 'condados', genero: 'm'}};
  const motivo = M.motivoDaUnidade('estados', PLANILHA, false);
  assert.ok(motivo.startsWith('Os condados como unidades valem com condados inteiros marcados, sem comunas avulsas'), motivo);
  assert.ok(motivo.endsWith('cada condado vem de todas as comunas dele.'), motivo);
  assert.ok(!motivo.includes('médicos'), motivo);
  assert.ok(M.motivoDaUnidade('estados', BR).includes('médicos únicos de cada estado'));
});

// ================================================================================================ ajustes de 25/10/2026
test('mapa com todas as unidades em análise: também as que o gráfico deixa de fora, no lugar delas, com os filtros que esmaecem', () => {
  // Roraima com o território de referência no mesmo estado: BOA VISTA fica sem distância; IRACEMA, sem o indicador.
  const boaVista = municipio('code:140010', 'BOA VISTA (RR)', {distancia_km: null});
  const altoAlegre = municipio('code:140005', 'ALTO ALEGRE (RR)', {distancia_km: 74.2});
  const iracema = municipio('code:140028', 'IRACEMA (RR)', {populacao: null, densidade: null, distancia_km: 83.3});
  const conjunto = {...municipio('c1', 'NORTE (soma)', {distancia_km: 10}), tipo: 'conjunto', membros: ['code:140005']};
  const roraima = {...municipio('uf:14', 'Roraima (RR)'), tipo: 'estado'};
  const itens = [iracema, conjunto, roraima, boaVista, altoAlegre];
  const {plotaveis, fora} = M.separarItens(itens.filter(item => item.tipo !== 'estado'), 'densidade', {distancia: true});
  assert.deepEqual(plotaveis.map(item => item.id), ['code:140005', 'c1'], 'no gráfico, só quem tem a distância e o indicador');
  assert.deepEqual(fora.map(item => [item.id, item.aspecto]), [['code:140010', 'distancia'], ['code:140028', 'indicador']]);
  // No mapa, todas as unidades (os estados não têm ponto; o conjunto dá o anel aos membros), na ordem neutra do gráfico.
  assert.deepEqual(M.itensParaOMapa(itens).map(item => item.id), ['code:140005', 'code:140010', 'code:140028', 'c1']);
  const filtros = {indicador: 'densidade', corte: null, soAtende: false, condicoes: false, filtroClasse: null, tendencia: false};
  assert.ok(M.itensParaOMapa(itens).every(item => M.dentroDosFiltros(item, filtros)), 'sem filtros, ninguém esmaece no mapa');
  // Com a régua, quem não tem o valor do indicador fica fora do corte (esmaece no mapa, nunca some); o conjunto não entra na régua.
  const corte = {minimo: 5, maximo: 20};
  assert.deepEqual(M.itensParaOMapa(itens).filter(item => !M.dentroDosFiltros(item, {...filtros, corte})).map(item => item.id), ['code:140028']);
  assert.deepEqual(M.itensParaOMapa(itens).filter(item => !M.dentroDosFiltros(item, {...filtros, corte: {minimo: 11, maximo: 20}}))
    .map(item => item.id), ['code:140005', 'code:140010', 'code:140028']);
  // Os mesmos filtros do gráfico: "Mostrar só quem atende" (com as condições no desenho) e a classe escolhida na tendência.
  const atende = municipio('code:1', 'A (AM)', {condicoes: {situacao: 'ATENDE', porCondicao: [], motivo: null}});
  const naoAtende = municipio('code:2', 'B (AM)', {condicoes: {situacao: 'NAO_ATENDE', porCondicao: [], motivo: null}});
  assert.equal(M.dentroDosFiltros(atende, {...filtros, soAtende: true, condicoes: true}), true);
  assert.equal(M.dentroDosFiltros(naoAtende, {...filtros, soAtende: true, condicoes: true}), false);
  assert.equal(M.dentroDosFiltros(naoAtende, {...filtros, soAtende: true, condicoes: false}), true, 'sem as condições no desenho, não filtra');
  const cresce = municipio('code:3', 'C (AM)', {tendencia: {classe: 'CRESCIMENTO', avaliavel: true}});
  const semClasse = municipio('code:4', 'D (AM)', {tendencia: {classe: null, avaliavel: false}});
  assert.equal(M.dentroDosFiltros(cresce, {...filtros, tendencia: true, filtroClasse: 'CRESCIMENTO'}), true);
  assert.equal(M.dentroDosFiltros(semClasse, {...filtros, tendencia: true, filtroClasse: 'CRESCIMENTO'}), false);
  assert.equal(M.dentroDosFiltros(semClasse, {...filtros, tendencia: true, filtroClasse: 'NAO_AVALIAVEL'}), true);
  // Sem camada de cor, a cor única não codifica nada: no mapa, a unidade sem o indicador fica vazada, nunca preenchida; a que
  // só não tem a distância continua com a cor única (o mapa não desenha a distância).
  const p = {camada: 'unica', indicador: 'densidade', limiteVariacao: 0, totalGrupos: 0, totalFaixas: 0, primeiros: null};
  assert.deepEqual(M.pintar(iracema, p), {cor: M.PALETA_CLARA.vazia, vazada: true, apagada: false});
  assert.deepEqual(M.pintar(boaVista, p), {cor: M.COR_BOLHA, vazada: false, apagada: false});
  assert.deepEqual(M.pintar(iracema, {...p, indicador: 'quantidade'}), {cor: M.COR_BOLHA, vazada: false, apagada: false},
    'com a quantidade, IRACEMA tem o valor do indicador');
});

test('fora do gráfico: o aviso diz quem ficou de fora e por quê, com o caminho do motivo e o mapa', () => {
  const boaVista = municipio('code:140010', 'BOA VISTA (RR)', {distancia_km: null});
  const altoAlegre = municipio('code:140005', 'ALTO ALEGRE (RR)', {distancia_km: 74.2});
  const iracema = municipio('code:140028', 'IRACEMA (RR)', {populacao: null, densidade: null, distancia_km: 83.3});
  const so = M.separarItens([boaVista, altoAlegre], 'densidade', {distancia: true}).fora;
  assert.equal(M.textoForaDoDesenho(so, {rotulos: BR, mapa: true}), 'Fora do gráfico, sem distância até a referência: BOA VISTA (RR). ' +
    'O motivo está em Não avaliáveis, nos Detalhes; no mapa, o município aparece no lugar dele.');
  assert.equal(M.textoForaDoDesenho(so, {rotulos: BR, mapa: false}), 'Fora do gráfico, sem distância até a referência: BOA VISTA (RR). ' +
    'O motivo está em Não avaliáveis, nos Detalhes.');
  // Dois motivos, cada um com os seus nomes; o indicador primeiro.
  const dois = M.separarItens([iracema, boaVista, altoAlegre], 'densidade', {distancia: true}).fora;
  assert.equal(M.textoForaDoDesenho(dois, {rotulos: BR, mapa: true}), 'Fora do gráfico, sem valor do indicador na competência: IRACEMA (RR). ' +
    'Sem distância até a referência: BOA VISTA (RR). O motivo de cada um está em Não avaliáveis, nos Detalhes; no mapa, os municípios ' +
    'aparecem no lugar deles.');
  // Muitos: os cinco primeiros pelo nome e a contagem; numa planilha, os nomes dela (no feminino, "cada uma" e "dela").
  const muitos = Array.from({length: 7}, (_, i) => ({id: 'code:' + (i + 1), rotulo: 'M' + (i + 1), tipo: 'municipio', aspecto: 'distancia', motivo: 'x'}));
  assert.equal(M.textoForaDoDesenho(muitos, {rotulos: BR, mapa: false}), 'Fora do gráfico, sem distância até a referência (7): M1, M2, M3, M4, M5 ' +
    'e mais 2. O motivo de cada um está em Não avaliáveis, nos Detalhes.');
  const unidades = {unidade: {singular: 'unidade', plural: 'unidades'}};
  assert.equal(M.textoForaDoDesenho(muitos.slice(0, 1), {rotulos: unidades, mapa: true}), 'Fora do gráfico, sem distância até a referência: M1. ' +
    'O motivo está em Não avaliáveis, nos Detalhes; no mapa, a unidade aparece no lugar dela.');
  // Um conjunto não tem ponto no mapa; a rotatividade sem coorte também fica dita. Os aspectos que não tiram do desenho não entram.
  assert.equal(M.textoForaDoDesenho([{id: 'c1', rotulo: 'NORTE (soma)', tipo: 'conjunto', aspecto: 'indicador', motivo: 'x'}], {rotulos: BR, mapa: true}),
    'Fora do gráfico, sem valor do indicador na competência: NORTE (soma). O motivo está em Não avaliáveis, nos Detalhes.');
  assert.match(M.textoForaDoDesenho([{id: 'code:9', rotulo: 'X', tipo: 'municipio', aspecto: 'rotatividade', motivo: 'x'}], {rotulos: BR, mapa: false}),
    /^Fora do gráfico, sem coorte inicial avaliável: X\./);
  assert.equal(M.textoForaDoDesenho([{id: 'code:9', rotulo: 'X', tipo: 'municipio', aspecto: 'variacao', motivo: 'x'},
    {id: 'code:8', rotulo: 'Y', tipo: 'municipio', aspecto: 'mapa', motivo: 'x'}], {rotulos: BR, mapa: true}), null);
  assert.equal(M.textoForaDoDesenho([], {rotulos: BR, mapa: true}), null);
});

test('bolhas: marcar não esmaece as outras; só a pintura apagada fica mais clara, e a bolha sem posição na vista, oculta', () => {
  // A opacidade não depende da seleção (25/10/2026): as marcadas ganham o anel escuro e o nome, como no mapa.
  assert.equal(M.opacidadeDaBolha({visivel: true, apagada: false}), 1);
  assert.equal(M.opacidadeDaBolha({visivel: true, apagada: true}), 0.45);
  assert.equal(M.opacidadeDaBolha({visivel: false, apagada: false}), 0);
  assert.equal(M.opacidadeDaBolha.length, 1, 'só a bolha decide: nada da seleção, do mouse ou do foco');
});

test('destaque da análise: os comparados ficam inteiros, e as demais bolhas esmaecem', () => {
  // Pedido de 26/10/2026: comparando alguns dos selecionados, as outras bolhas esmaecem; marcar, sozinho, continua sem esmaecer
  // (teste acima). Na Análise Espacial, desde a Escolha dos territórios (27/10/2026), toda bolha é da base: nada a destacar além da
  // comparação.
  const noGrafico = new Set(['code:1', 'code:2', 'code:3', 'code:4']);
  assert.deepEqual(M.destaqueDaAnalise(['code:1', 'code:3'], noGrafico), ['code:1', 'code:3']);
  assert.deepEqual(M.destaqueDaAnalise(['code:1', 'code:9'], noGrafico), [], 'comparado fora do gráfico não conta');
  assert.deepEqual(M.destaqueDaAnalise(['code:1', 'code:2', 'code:3'], noGrafico), ['code:1', 'code:2', 'code:3']);
  assert.deepEqual(M.destaqueDaAnalise([], noGrafico), []);
  const destaque = new Set(['code:1']);
  assert.equal(M.opacidadeComDestaque({id: 'code:1', visivel: true, apagada: false}, destaque), 1);
  assert.equal(M.opacidadeComDestaque({id: 'code:2', visivel: true, apagada: false}, destaque), M.OPACIDADE_FORA_DO_DESTAQUE);
  assert.equal(M.OPACIDADE_FORA_DO_DESTAQUE, 0.25);
  assert.equal(M.opacidadeComDestaque({id: 'code:2', visivel: true, apagada: true}, destaque), 0.25);
  assert.equal(M.opacidadeComDestaque({id: 'code:2', visivel: false, apagada: false}, destaque), 0, 'sem posição, oculta');
  assert.equal(M.opacidadeComDestaque({id: 'code:2', visivel: true, apagada: true}, null), 0.45, 'sem destaque, a regra de sempre');
  assert.equal(M.opacidadeComDestaque({id: 'code:2', visivel: true, apagada: false}, new Set()), 1);
});

// ================================================================================================ navegação por níveis (06/11/2026)
// Comando do responsável de 06/11/2026, itens 2 e 3: o todo como referência fixa, o "Ver por", a faixa do lugar em uso e a trilha.
const NIVEIS = {'13': ['code:130001', 'code:130002', 'code:130003'], '15': ['code:150001', 'code:150002'], '35': ['code:350001']};
const ARVORE = {grupos: Object.entries(NIVEIS).map(([id, ids]) => ({id, nome: {'13': 'Amazonas', '15': 'Pará', '35': 'São Paulo'}[id], sigla: '',
  rotuloGrupo: '', unidades: ids.length})), unidadesDoGrupo: g => NIVEIS[g] ?? [], grupoDe: id => id.slice(5, 7), total: 6};
const TRILHA = {arvore: ARVORE, nomeDoTodo: 'Brasil', nomes: new Map([['code:150001', 'MARABA (PA)'], ['code:130001', 'MANAUS (AM)']]), comGrupos: true};
const escolhaDaTrilha = (nivel, estados = [], ids = [], todos = false, conjuntos = [], estadosUnidade = []) =>
  ({nivel, base: {todos, estados, ids}, estados: estadosUnidade, conjuntos});
const partes = lugar => lugar.partes.map(parte => [parte.chave, parte.rotulo, parte.atual]);

test('trilha: o todo, o grupo inteiro, a unidade, a seleção que cabe num grupo e a seleção livre', () => {
  // Nada escolhido: a parte do todo à vista, sem ser a atual (tocar nela leva ao todo).
  const nada = M.lugarDaTrilha(escolhaDaTrilha('municipios'), TRILHA);
  assert.equal(nada.tipo, 'nenhum');
  assert.deepEqual(partes(nada), [['todo', 'Brasil', false]]);
  // O Brasil inteiro, vendo por estado ou por município: o todo.
  for (const escolha of [escolhaDaTrilha('estados', [], [], true, [], ['13', '15', '35']), escolhaDaTrilha('municipios', [], [], true),
    escolhaDaTrilha('municipios', ['13', '15', '35'])])
    assert.deepEqual(partes(M.lugarDaTrilha(escolha, TRILHA)), [['todo', 'Brasil', true]]);
  // O Pará inteiro: "Brasil › Pará".
  const para = M.lugarDaTrilha(escolhaDaTrilha('municipios', ['15']), TRILHA);
  assert.deepEqual([para.tipo, para.grupo, para.grupoInteiro], ['grupo', '15', true]);
  assert.deepEqual(partes(para), [['todo', 'Brasil', false], ['grupo', 'Pará', true]]);
  // Uma unidade: "Brasil › Pará › MARABA (PA)".
  const maraba = M.lugarDaTrilha(escolhaDaTrilha('municipios', [], ['code:150001']), TRILHA);
  assert.deepEqual([maraba.tipo, maraba.grupo, maraba.unidade], ['unidade', '15', 'code:150001']);
  assert.deepEqual(partes(maraba), [['todo', 'Brasil', false], ['grupo', 'Pará', false], ['unidade', 'MARABA (PA)', true]]);
  // Tudo dentro de um estado só (municípios dele ou um conjunto dos membros dele): a trilha mostra o estado, em parte.
  const parte = M.lugarDaTrilha(escolhaDaTrilha('municipios', [], ['code:130001', 'code:130002']), TRILHA);
  assert.deepEqual([parte.tipo, parte.grupo, parte.grupoInteiro], ['grupo', '13', false]);
  const comConjunto = M.lugarDaTrilha(escolhaDaTrilha('municipios', [], ['code:130003'], false,
    [{id: 'c1', rotulo: 'Carajás', membros: ['code:130001', 'code:130002']}]), TRILHA);
  assert.deepEqual([comConjunto.tipo, comConjunto.grupo], ['grupo', '13']);
  // Escolhas livres (vários estados, municípios de estados diferentes): "Brasil › Seleção".
  for (const escolha of [escolhaDaTrilha('municipios', ['13', '15']), escolhaDaTrilha('municipios', [], ['code:130001', 'code:150001']),
    escolhaDaTrilha('estados', ['13', '15'], [], false, [], ['13', '15'])])
    assert.deepEqual(partes(M.lugarDaTrilha(escolha, TRILHA)), [['todo', 'Brasil', false], ['selecao', 'Seleção', true]]);
  // Um estado só, vendo por estado: o grupo.
  assert.equal(M.lugarDaTrilha(escolhaDaTrilha('estados', ['15'], [], false, [], ['15']), TRILHA).tipo, 'grupo');
  // Numa planilha sem a coluna-mãe: o todo, a unidade ou a seleção, sem grupos.
  const planilha = {...TRILHA, nomeDoTodo: 'Toda a base', comGrupos: false, arvore: {...ARVORE, grupos: [], grupoDe: () => ''}};
  assert.deepEqual(partes(M.lugarDaTrilha(escolhaDaTrilha('municipios', [], ['code:130001']), planilha)),
    [['todo', 'Toda a base', false], ['unidade', 'MANAUS (AM)', true]]);
  assert.equal(M.lugarDaTrilha(escolhaDaTrilha('municipios', [], ['code:130001', 'code:150001']), planilha).tipo, 'selecao');
  assert.equal(M.nomeDoTodo(true), 'Brasil');
  // O nome do todo (07/11/2026, item 1 do comando): numa planilha, o do painel Colunas; sem ele, "Toda a base" (antes, "Toda a
  // planilha"). A trilha começa nele.
  const portugal = {...DISTRITOS, todo: {nome: 'Portugal', artigo: ''}}, solaria = {...DISTRITOS, todo: {nome: 'Solária', artigo: 'a'}};
  assert.equal(M.nomeDoTodo(false), 'Toda a base');
  assert.equal(M.nomeDoTodo(false, DISTRITOS), 'Toda a base');
  assert.equal(M.nomeDoTodo(false, portugal), 'Portugal');
  assert.equal(M.nomeDoTodo(true, portugal), 'Brasil');
  assert.deepEqual([M.doTodo(true), M.doTodo(false), M.doTodo(false, portugal), M.doTodo(false, solaria)],
    ['do Brasil', 'da base', 'de Portugal', 'da Solária']);
  assert.deepEqual([M.deTodoOTodo(true), M.deTodoOTodo(false, DISTRITOS), M.deTodoOTodo(false, solaria)],
    ['de todo o país', 'de toda a base', 'da Solária']);
  assert.deepEqual([M.todoMarcado(true), M.todoMarcado(false), M.todoMarcado(false, portugal), M.todoMarcado(false, solaria, false)],
    ['Brasil inteiro marcado', 'Toda a base marcada', 'Portugal inteiro marcado', 'Solária inteira desmarcada']);
  assert.deepEqual(partes(M.lugarDaTrilha(escolhaDaTrilha('municipios', [], ['code:130001']), {...planilha, nomeDoTodo: M.nomeDoTodo(false, portugal)})),
    [['todo', 'Portugal', false], ['unidade', 'MANAUS (AM)', true]]);
});

test('Ver por: só os níveis abaixo do lugar em uso; o todo nunca é opção; com uma opção, o controle não aparece', () => {
  const c = {arvore: ARVORE, comNiveis: true, rotulos: BR};
  const opcoes = escolha => M.opcoesVerPor(M.lugarDaTrilha(escolha, TRILHA), escolha, c).map(opcao => [opcao.nivel, opcao.rotulo]);
  const estadoEMunicipio = [['estados', 'Estado'], ['municipios', 'Município']];
  assert.deepEqual(opcoes(escolhaDaTrilha('municipios', [], [], true)), estadoEMunicipio);  // no todo
  assert.deepEqual(opcoes(escolhaDaTrilha('municipios')), estadoEMunicipio);  // nada escolhido: o estado é o atalho de todos
  assert.deepEqual(opcoes(escolhaDaTrilha('municipios', ['13', '15'])), estadoEMunicipio);  // seleção de estados inteiros
  assert.deepEqual(opcoes(escolhaDaTrilha('municipios', ['15'])), []);  // "Brasil › Pará": só o município
  assert.deepEqual(opcoes(escolhaDaTrilha('municipios', [], ['code:130001', 'code:150001'])), []);
  assert.deepEqual(opcoes(escolhaDaTrilha('municipios', [], ['code:150001'])), []);
  assert.ok(!M.opcoesVerPor(M.lugarDaTrilha(escolhaDaTrilha('municipios', [], [], true), TRILHA), escolhaDaTrilha('municipios', [], [], true), c)
    .some(opcao => opcao.nivel === 'brasil'), 'o Brasil deixa de ser uma opção de unidade');
  assert.deepEqual(M.opcoesVerPor(M.lugarDaTrilha(escolhaDaTrilha('municipios', [], [], true), TRILHA), escolhaDaTrilha('municipios', [], [], true),
    {...c, comNiveis: false}), [], 'sem a fonte estadual (ou numa planilha), sem o Ver por');
});

// O segundo nível de grupo (07/11/2026, item 1 do comando: "Ver por: Região | Distrito | Concelho"): os grupos de cima pelo catálogo
// (o segundo valor da hierarquia), o "Ver por" com três opções e a escolha do nível de cima.
const CONCELHOS = [['Barcelos', 'Braga', 'Norte'], ['Braga', 'Braga', 'Norte'], ['Porto', 'Porto', 'Norte'], ['Évora', 'Évora', 'Alentejo'],
  ['Beja', 'Beja', 'Alentejo']].map(([nome, distrito, regiao]) => ({id: 'name:' + nome, name: nome, code: '', label: nome,
  parents: [distrito, regiao], selection_reason: '', state: '', state_name: '', state_code: ''}));
const PORTUGAL = {unidade: {singular: 'concelho', plural: 'concelhos', genero: 'm'}, grupo: {singular: 'distrito', plural: 'distritos', genero: 'm'},
  grupo_superior: {singular: 'região', plural: 'regiões', genero: 'f'}, todo: {nome: 'Portugal', artigo: ''}};

test('dois níveis de grupo: os grupos de cima, o Ver por "Região | Distrito | Concelho" e a escolha do nível de cima', () => {
  const grupos = M.gruposDaFonte(null, CONCELHOS);
  assert.deepEqual(grupos.map(g => [g.id, g.unidades]), [['Beja', 1], ['Braga', 2], ['Évora', 1], ['Porto', 1]]);
  const {regioes, regiaoDoGrupo} = M.regioesDaFonte(CONCELHOS, grupos);
  assert.deepEqual(regioes.map(r => [r.id, r.unidades]), [['Alentejo', 2], ['Norte', 3]]);
  assert.equal(regiaoDoGrupo.get('Braga'), 'Norte');
  // Um distrito em duas regiões: a hierarquia não é consistente, e não há grupos de cima (o motor diz o motivo).
  const quebrada = [...CONCELHOS, {...CONCELHOS[0], id: 'name:Outro', name: 'Outro', label: 'Outro', parents: ['Braga', 'Alentejo']}];
  assert.deepEqual(M.regioesDaFonte(quebrada, M.gruposDaFonte(null, quebrada)).regioes, []);
  // Sem o segundo valor da hierarquia, nenhum.
  assert.deepEqual(M.regioesDaFonte(CONCELHOS.map(item => ({...item, parents: [item.parents[0]]})), grupos).regioes, []);
  const porGrupo = new Map();
  for (const item of CONCELHOS) porGrupo.set(item.parents[0], [...(porGrupo.get(item.parents[0]) ?? []), item.id]);
  const arvore = {grupos, unidadesDoGrupo: g => porGrupo.get(g) ?? [], grupoDe: id => CONCELHOS.find(item => item.id === id)?.parents[0] ?? '',
    total: CONCELHOS.length, regioes, regiaoDoGrupo: g => regiaoDoGrupo.get(g) ?? ''};
  assert.deepEqual(M.gruposDaRegiao('Norte', arvore), ['Braga', 'Porto']);
  const trilha = {arvore, nomeDoTodo: M.nomeDoTodo(false, PORTUGAL), nomes: new Map(), comGrupos: true};
  const c = {arvore, comNiveis: true, rotulos: PORTUGAL, comRegioes: true};
  const opcoes = escolha => M.opcoesVerPor(M.lugarDaTrilha(escolha, trilha), escolha, c).map(opcao => [opcao.nivel, opcao.rotulo, opcao.apoio]);
  const tres = [['regioes', 'Região', 'cada ponto é uma região'], ['estados', 'Distrito', 'cada ponto é um distrito'],
    ['municipios', 'Concelho', 'cada ponto é um concelho']];
  assert.deepEqual(opcoes(escolhaDaTrilha('municipios', [], [], true)), tres);  // no todo
  assert.deepEqual(opcoes(escolhaDaTrilha('municipios')), tres);  // nada escolhido
  assert.deepEqual(opcoes(escolhaDaTrilha('municipios', ['Braga', 'Porto', 'Beja'])).map(([nivel]) => nivel), ['estados', 'municipios'],
    'distritos que não fecham as regiões: sem a região');
  // O Norte inteiro (os distritos dele) é o lugar em uso na trilha (a parte C2): o Ver por dentro dele tem o distrito e o concelho.
  assert.deepEqual(opcoes(escolhaDaTrilha('municipios', ['Braga', 'Porto'])).map(([nivel]) => nivel), ['estados', 'municipios'],
    'o Norte inteiro: o lugar é a região, e o Ver por fica abaixo dela');
  assert.deepEqual(M.opcoesVerPor(M.lugarDaTrilha(escolhaDaTrilha('municipios', [], [], true), trilha), escolhaDaTrilha('municipios', [], [], true),
    {...c, comRegioes: false}).map(opcao => opcao.nivel), ['estados', 'municipios'], 'sem o nível no motor, as duas opções de antes');
  // A escolha do nível de cima: sem nada marcado, todas as regiões; com o Norte inteiro (Braga e Porto), o Norte; com distritos que não
  // fecham uma região, não vale.
  assert.deepEqual(M.escolhaDaUnidade(escolhaDaTrilha('municipios'), 'regioes', arvore),
    escolhaDaTrilha('regioes', [], [], true, [], ['Alentejo', 'Norte']));
  assert.deepEqual(M.escolhaDaUnidade(escolhaDaTrilha('municipios', ['Braga', 'Porto']), 'regioes', arvore).estados, ['Norte']);
  assert.equal(M.escolhaDaUnidade(escolhaDaTrilha('municipios', ['Braga']), 'regioes', arvore), null);
  assert.equal(M.escolhaDaUnidade(escolhaDaTrilha('municipios'), 'regioes', {...arvore, regioes: undefined}), null);
  // A árvore mostra o que está na análise: o Norte marca os distritos dele.
  assert.deepEqual(M.unificarEscolha(escolhaDaTrilha('regioes', [], [], false, [], ['Norte']), arvore).base, {todos: false, estados: ['Braga', 'Porto'], ids: []});
  // Trocar a árvore mantém o nível de cima enquanto as regiões continuam inteiras.
  assert.deepEqual(M.escolhaDaArvore(escolhaDaTrilha('regioes', [], [], true, [], ['Alentejo', 'Norte']), {todos: false, estados: ['Braga', 'Porto'], ids: []},
    arvore).estados, ['Norte']);
  assert.equal(M.escolhaDaArvore(escolhaDaTrilha('regioes', [], [], true, [], ['Alentejo', 'Norte']), {todos: false, estados: ['Braga'], ids: []},
    arvore).nivel, 'municipios');
  // A trilha e os textos no nível de cima: todas as regiões são o todo; o resumo e o lugar falam das regiões.
  assert.deepEqual(partes(M.lugarDaTrilha(escolhaDaTrilha('regioes', [], [], true, [], ['Alentejo', 'Norte']), trilha)), [['todo', 'Portugal', true]]);
  const resumo = estados => M.resumoDoUniverso({nivel: 'regioes', base: {todos: true, estados: [], ids: []}, estados, conjuntos: 0, grupos,
    regioes, rotulos: PORTUGAL, total: 5, grupoDe: arvore.grupoDe});
  assert.deepEqual([resumo(['Alentejo', 'Norte']), resumo(['Norte']), resumo([])], ['Todas as regiões (2)', 'Norte', 'Nenhuma região marcada']);
  assert.equal(M.lugarDoUniverso({nivel: 'regioes', base: {todos: true, estados: [], ids: []}, conjuntos: 0, grupos, regioes, rotulos: PORTUGAL,
    brasil: false, grupoDe: arvore.grupoDe, estados: ['Alentejo', 'Norte']}).lugar, 'nas regiões');
  assert.ok(M.emGrupos('regioes') && M.emGrupos('estados') && !M.emGrupos('municipios'));
  assert.deepEqual(M.rotulosDaVista(PORTUGAL, 'regioes').grupo, PORTUGAL.grupo_superior);
  assert.ok(M.motivoDaUnidade('regioes', PORTUGAL, false).startsWith('As regiões como unidades valem com regiões inteiras marcadas'));
  // O mapa no nível de cima de uma planilha: os grupos de cima não têm um ponto de desenho.
  const mapa = M.disponibilidadeDoMapa({fonte: 'arquivo', temCoordenadas: true, nivel: 'regioes', series: false, rotatividade: false, rotulos: PORTUGAL});
  assert.deepEqual([mapa.disponivel, mapa.atalho], [false, 'Ver os concelhos no mapa']);
  assert.ok(mapa.motivo.endsWith('as regiões não têm um ponto de desenho.'), mapa.motivo);
});

test('dois níveis de grupo na trilha: "Portugal › Norte › Braga › Barcelos", a região inteira e em parte, e o Ver por dentro dela', () => {
  const grupos = M.gruposDaFonte(null, CONCELHOS);
  const {regioes, regiaoDoGrupo} = M.regioesDaFonte(CONCELHOS, grupos);
  const porGrupo = new Map();
  for (const item of CONCELHOS) porGrupo.set(item.parents[0], [...(porGrupo.get(item.parents[0]) ?? []), item.id]);
  const arvore = {grupos, unidadesDoGrupo: g => porGrupo.get(g) ?? [], grupoDe: id => CONCELHOS.find(item => item.id === id)?.parents[0] ?? '',
    total: CONCELHOS.length, regioes, regiaoDoGrupo: g => regiaoDoGrupo.get(g) ?? ''};
  const trilha = {arvore, nomeDoTodo: M.nomeDoTodo(false, PORTUGAL), nomes: new Map([['name:Barcelos', 'Barcelos']]), comGrupos: true};
  const lugar = escolha => M.lugarDaTrilha(escolha, trilha);
  // O aceite do comando: uma unidade, com o grupo e o grupo de cima dela.
  const barcelos = lugar(escolhaDaTrilha('municipios', [], ['name:Barcelos']));
  assert.deepEqual(partes(barcelos), [['todo', 'Portugal', false], ['regiao', 'Norte', false], ['grupo', 'Braga', false],
    ['unidade', 'Barcelos', true]]);
  assert.deepEqual([barcelos.tipo, barcelos.grupo, barcelos.regiao], ['unidade', 'Braga', 'Norte']);
  // O grupo inteiro: "Portugal › Norte › Braga".
  assert.deepEqual(partes(lugar(escolhaDaTrilha('municipios', ['Braga']))), [['todo', 'Portugal', false], ['regiao', 'Norte', false],
    ['grupo', 'Braga', true]]);
  // O Norte inteiro (os distritos dele, inteiros): "Portugal › Norte", inteiro; parte dele (um distrito e um concelho de outro), em parte.
  const norte = lugar(escolhaDaTrilha('municipios', ['Braga', 'Porto']));
  assert.deepEqual(partes(norte), [['todo', 'Portugal', false], ['regiao', 'Norte', true]]);
  assert.deepEqual([norte.tipo, norte.regiao, norte.regiaoInteira], ['regiao', 'Norte', true]);
  const parte = lugar(escolhaDaTrilha('municipios', ['Porto'], ['name:Barcelos']));
  assert.deepEqual([parte.tipo, parte.regiao, parte.regiaoInteira], ['regiao', 'Norte', false]);
  // Regiões diferentes: a seleção; no nível de cima, uma região só é o lugar dela.
  assert.equal(lugar(escolhaDaTrilha('municipios', ['Braga', 'Beja'])).tipo, 'selecao');
  assert.deepEqual(partes(lugar(escolhaDaTrilha('regioes', ['Braga', 'Porto'], [], false, [], ['Norte']))),
    [['todo', 'Portugal', false], ['regiao', 'Norte', true]]);
  assert.deepEqual(partes(lugar(escolhaDaTrilha('estados', ['Braga', 'Porto'], [], false, [], ['Braga', 'Porto']))),
    [['todo', 'Portugal', false], ['regiao', 'Norte', true]], 'vendo por distrito, os distritos do Norte: o Norte');
  // Sem o nome do todo, a trilha começa em "Toda a base".
  assert.equal(partes(M.lugarDaTrilha(escolhaDaTrilha('municipios', [], ['name:Barcelos']), {...trilha, nomeDoTodo: M.nomeDoTodo(false)}))[0][1],
    'Toda a base');
  // Dentro do Norte inteiro, o Ver por tem o distrito e o concelho (a região é o lugar); em parte, nenhum.
  const c = {arvore, comNiveis: true, rotulos: PORTUGAL, comRegioes: true};
  assert.deepEqual(M.opcoesVerPor(norte, escolhaDaTrilha('municipios', ['Braga', 'Porto']), c).map(opcao => opcao.rotulo), ['Distrito', 'Concelho']);
  assert.deepEqual(M.opcoesVerPor(parte, escolhaDaTrilha('municipios', ['Porto'], ['name:Barcelos']), c), []);
  // A conversa: "mostre as regiões" leva ao nível de cima, com todas; sem o nível, o motivo.
  const def = M.definicaoInicial({tipo: 'arquivo', periodos: ['2024'], categoria: 'Enfermagem', temGrupos: true, temPopulacao: true});
  const pedido = (todasAsRegioes) => M.aplicarPedido(def, {nivel: 'regioes'}, {periodos: ['2024'], nomes: new Map(), temGrupos: true,
    disponivel: () => ({disponivel: true, motivo: '', pendente: false, enviarDados: false}), todasAsRegioes});
  assert.deepEqual([pedido(['Alentejo', 'Norte']).definicao.nivel, pedido(['Alentejo', 'Norte']).definicao.estados], ['regioes', ['Alentejo', 'Norte']]);
  assert.ok(pedido([]).mensagens.includes('Esta fonte não tem um nível de grupo acima dos grupos.'), pedido([]).mensagens.join(' | '));
  assert.equal(pedido([]).definicao.nivel, 'municipios');
});

test('total do todo informado (07/11/2026, item 1.4c): vai em todo pedido de uma planilha', () => {
  const def = {...M.definicaoInicial({tipo: 'arquivo', periodos: ['2024'], categoria: 'Enfermagem', temGrupos: true, temPopulacao: true}),
    base: {todos: true, estados: [], ids: []}};
  const total = {quantidade: 50, competencia: '2024', fonte: 'Cadastro do conselho'};
  assert.deepEqual(M.montarOpcoes(def, 'distribuicao', undefined, {totalInformado: total}).total_informado, total);
  assert.equal('total_informado' in M.montarOpcoes(def, 'distribuicao', undefined, {}), false);
  assert.equal('total_informado' in M.montarOpcoes(def, 'distribuicao', undefined, {totalInformado: null}), false);
});

test('selecionar por critérios (07/11/2026, item 6): a trilha diz a regra enquanto a seleção for a dela', () => {
  const base = M.normalizarArvore({todos: false, estados: [], ids: ['code:130001', 'code:150001']}, ARVORE);
  const regra = {texto: 'densidade abaixo de 0,5', competencia: '202406', total: 2, base, conjuntos: [], pedido: {criterios: {}, agrupar: null}};
  assert.equal(M.textoDaRegra(regra), 'densidade abaixo de 0,5 em jun/2024 (2)');
  assert.equal(M.competenciaAbreviada('202403'), 'mar/2024');
  const escolha = {nivel: 'municipios', base, estados: [], conjuntos: []};
  assert.ok(M.regraConfere(regra, escolha));
  assert.deepEqual(partes(M.lugarDaTrilha(escolha, {...TRILHA, regra})),
    [['todo', 'Brasil', false], ['selecao', 'Seleção: densidade abaixo de 0,5 em jun/2024 (2)', true]]);
  // A seleção mudou (um município a mais, ou outro nível): a regra deixa de valer, e a trilha volta à de sempre.
  const outra = {...escolha, base: {...base, ids: [...base.ids, 'code:350001']}};
  assert.ok(!M.regraConfere(regra, outra));
  assert.deepEqual(partes(M.lugarDaTrilha(outra, {...TRILHA, regra})), [['todo', 'Brasil', false], ['selecao', 'Seleção', true]]);
  assert.ok(!M.regraConfere(regra, {...escolha, nivel: 'estados'}));
  assert.ok(!M.regraConfere(null, escolha));
  // Com os grupos agregados: a regra vale com os mesmos grupos, com os mesmos membros, e os isolados na base; renomear um grupo
  // não muda a seleção, mas tirar ou pôr um membro (o ✎ de Agregar territórios) muda, e a regra sai de vista.
  const grupo = {id: 'c1', rotulo: 'Grupo 1', membros: ['code:130002', 'code:130003']};
  const comGrupos = {...regra, conjuntos: [{id: 'c1', membros: ['code:130003', 'code:130002']}]};
  assert.ok(M.regraConfere(comGrupos, {...escolha, conjuntos: [grupo]}));
  assert.ok(M.regraConfere(comGrupos, {...escolha, conjuntos: [{...grupo, rotulo: 'Bico do Papagaio'}]}));
  assert.ok(!M.regraConfere(comGrupos, {...escolha, conjuntos: [{...grupo, membros: ['code:130002']}]}));
  assert.ok(!M.regraConfere(comGrupos, escolha));
  // No arquivo de método, a regra abre a Procedência; sem regra em uso, nada muda.
  const metodo = M.textoDoMetodo(resposta(), 'T', null, null, {rotulos: BR, brasil: true, regra: M.textoDaRegra(regra)});
  assert.deepEqual(metodo.split('\n').slice(0, 4), ['T', '', 'Procedência', '- Seleção por critérios: densidade abaixo de 0,5 em jun/2024 (2)']);
  assert.ok(!M.textoDoMetodo(resposta(), 'T', null, null, {rotulos: BR, brasil: true, regra: null}).includes('Seleção por critérios'));
});

test('faixa do lugar: a competência inicial da variação, os números e as referências', () => {
  const periodos = ['202006', '202101', '202106', '202201', '202206', '202301', '202306', '202401', '202406'];
  assert.equal(M.desdeDaFaixa(periodos, '202406'), '202106');  // os últimos 4 períodos anuais até a competência da análise
  assert.equal(M.desdeDaFaixa(periodos, '202306'), '202006');
  assert.equal(M.desdeDaFaixa(periodos, '202206'), null);  // sem 4 períodos anuais até ela, a faixa não mostra a variação
  assert.equal(M.desdeDaFaixa(periodos, ''), null);
  assert.equal(M.populacaoResumida(212583750), '212,6 milhões');
  assert.equal(M.populacaoResumida(1250000), '1,3 milhão');
  assert.equal(M.populacaoResumida(8100), '8,1 mil');
  assert.equal(M.populacaoResumida(950), '950');
  assert.equal(M.textoDaReferencia('Brasil', 2.3612), 'Brasil 2,36');
  assert.equal(M.textoDaReferencia('Pará', 1.185), 'Pará 1,19');
  assert.equal(M.nomeCurtoDoNivel({nome: 'Pará', rotulo: 'Pará (PA)'}), 'Pará');
  assert.equal(M.nomeCurtoDoNivel({nome: null, rotulo: 'Pará (PA)'}), 'Pará');
  assert.equal(M.nomeCurtoDoNivel({rotulo: 'Brasil'}), 'Brasil');
});

test('mapa vendo por estado: os estados entram só quando a área os pede (com o ponto de desenho); a dica da unidade oferece abri-la', () => {
  const rondonia = {...municipio('uf:11', 'Rondônia (RO)'), tipo: 'estado'};
  const acre = {...municipio('uf:12', 'Acre (AC)'), tipo: 'estado'};
  assert.deepEqual(M.itensParaOMapa([acre, rondonia]).map(item => item.id), []);
  assert.deepEqual(M.itensParaOMapa([acre, rondonia], true).map(item => item.id), ['uf:11', 'uf:12']);
  const unidade = municipio('code:150001', 'MARABA (PA)');
  const contexto = {indicador: 'densidade', competencia: '202406', competenciaInicial: null, distancia: false, variacao: false, tendencia: false,
    nomes: new Map(), rotulos: BR};
  assert.equal(M.montarDica(unidade, {...contexto, abrirUnidade: true}).acao, 'Abrir MARABA (PA)');
  assert.equal(M.montarDica(unidade, contexto).acao, null);  // com a escolha de itens em curso (Comparar), tocar marca
  assert.equal(M.montarDica(rondonia, {...contexto, abrirUnidade: true, unidadesDoGrupo: () => 52}).acao, 'Ver os 52 municípios');
});

test('o todo deixa de ser unidade: o pedido do Brasil e o estado guardado com ele levam ao todo, vendo por estado', () => {
  const c = {periodos: ['202306', '202406'], nomes: new Map(), temGrupos: true, temBrasil: true, todosOsEstados: ['13', '15', '35'],
    disponivel: f => M.disponibilidadeDaFamilia(f, {fonte: 'brasil', nivel: 'municipios', disponibilidade: null, temIdentificador: false, rotulos: BR})};
  const brasil = M.aplicarPedido(definicao(), {nivel: 'brasil'}, c);
  assert.equal(brasil.definicao.nivel, 'estados');
  assert.deepEqual(brasil.definicao.base, {todos: true, estados: [], ids: []});
  assert.deepEqual(brasil.definicao.estados, ['13', '15', '35']);
  assert.deepEqual(brasil.mensagens, []);
  const salvo = M.salvarEstado('Brasil', {chave: 'k', familia: 'distribuicao', opcoes: {nivel: 'brasil'}, definicao: definicao({nivel: 'brasil'}),
    visual: {escala: 'linear', corte: null, selecionados: []}}, resposta({nivel: 'brasil'}));
  const lido = M.lerEstadoSalvo(salvo);
  assert.equal(lido.definicao.nivel, 'estados');
  assert.deepEqual(lido.definicao.base, {todos: true, estados: [], ids: []});
  assert.equal(lido.resposta, null);  // o pedido é outro: a área calcula de novo
  assert.equal(lido.opcoes, null);
});

test('cliente do motor: os números do lugar em uso e os pontos de desenho dos estados no mapa', () => {
  const lugar = A.normalizarLugar({competencia: '202406', categoria: 'MEDICINA', desde: '202106', notas: ['Nota.'],
    todo: {id: 'br', nivel: 'todo', rotulo: 'Brasil', fonte: 'nacional', regra: 'BR-POP-JUNHO-1', competencia: '202406', quantidade: 502495,
      populacao: 212583750, densidade: 2.3637, avaliabilidade: 'AVALIAVEL', motivo: null, desde: '202106',
      inicial: {populacao: 213317639, quantidade: 422541, densidade: 1.9808}, variacao_percentual: {populacao: -0.34, quantidade: 18.92, densidade: 19.33},
      motivos_variacao: [], serie: [{competencia: '202306', quantidade: 1, populacao: 2, densidade: 0.5}, {competencia: '202406', quantidade: null,
        populacao: null, densidade: null}]},
    grupo: {id: 'uf:15', nivel: 'grupo', rotulo: 'Pará (PA)', nome: 'Pará', sigla: 'PA', fonte: 'estadual', competencia: '202406', quantidade: 10307,
      populacao: 8664306, densidade: 1.1896, avaliabilidade: 'AVALIAVEL', motivo: null, desde: null, inicial: null, variacao_percentual: null,
      motivos_variacao: [], serie: null}});
  assert.equal(lugar.todo.quantidade, 502495);
  assert.equal(lugar.todo.variacaoPercentual.densidade, 19.33);
  assert.deepEqual(lugar.todo.serie[1], {competencia: '202406', quantidade: null, populacao: null, densidade: null});
  assert.deepEqual([lugar.grupo.id, lugar.grupo.nome, lugar.grupo.sigla, lugar.grupo.serie], ['uf:15', 'Pará', 'PA', null]);
  assert.equal(A.normalizarLugar({competencia: '202406', todo: null, grupo: null}).grupo, null);
  assert.throws(() => A.normalizarLugar(null), erro => erro instanceof A.ErroDoMotor);
  const mapa = A.normalizarMapa({competencia: '202406', referencial: 'SIRGAS2000', pontos: [{id: 'code:150001', lat: -5.3, lon: -49.1}],
    sem_coordenada: [], grupos: [{id: 'uf:15', lat: -4.2, lon: -51.1, unidades: 144}, {id: 'uf:99', lat: 200, lon: 0}],
    nota_grupos: 'Cada estado aparece no mapa na média das coordenadas das sedes dos seus municípios.'});
  assert.deepEqual([...mapa.grupos.entries()], [['uf:15', [-4.2, -51.1]]]);  // ponto fora do intervalo fica de fora
  assert.ok(mapa.notaDosGrupos.startsWith('Cada estado aparece no mapa'));
  assert.equal(A.normalizarMapa({competencia: '202406', pontos: [], sem_coordenada: []}).grupos, undefined);
});

test('uma seleção só (06/11/2026, item 4.1): a base da Espacial é a seleção em uso; a base que parte de outro lugar vira a seleção', () => {
  const lado = (tipo, {regioes = [], ufs = [], filtros = [], modo = 'todos', municipios = []} = {}) =>
    ({partir_de: {tipo, regioes, ufs}, filtros, escolha: {modo, municipios}});
  const f = {indicador: 'densidade', operador: '<', valor: 0.5};
  // A base na seleção guarda os filtros e deixa a partida e os marcados.
  assert.deepEqual(M.baseNaSelecao(lado('regioes', {regioes: ['Norte'], filtros: [f], modo: 'marcados', municipios: ['code:150001']})),
    lado('selecao_previa', {filtros: [f]}));
  assert.equal(M.baseEhASelecao(lado('selecao_previa')), true);
  assert.equal(M.baseEhASelecao(lado('selecao_previa', {modo: 'marcados', municipios: ['code:150001']})), false);
  // As equivalências do comando: os marcados viram a seleção; o país, o todo; um estado, ele inteiro; as regiões, os estados delas.
  const estados = ['11', '12', '13', '15', '29', '35'];
  assert.deepEqual(M.selecaoDaBase(lado('pais', {modo: 'marcados', municipios: ['code:150002', 'code:150001']}), estados),
    {todos: false, estados: [], ids: ['code:150001', 'code:150002']});
  assert.deepEqual(M.selecaoDaBase(lado('pais'), estados), {todos: true, estados: [], ids: []});
  assert.deepEqual(M.selecaoDaBase(lado('ufs', {ufs: ['15', '13']}), estados), {todos: false, estados: ['13', '15'], ids: []});
  assert.deepEqual(M.selecaoDaBase(lado('regioes', {regioes: ['Norte']}), estados), {todos: false, estados: ['11', '12', '13', '15'], ids: []});
  assert.equal(M.selecaoDaBase(lado('regioes', {regioes: ['Norte']}), []), null);  // sem a lista dos estados, nenhuma seleção inventada
  assert.equal(M.selecaoDaBase(lado('selecao_previa'), estados), null);
  // A consulta na seleção: com a base no país, a seleção vira o todo, e a referência que partia da seleção nomeia a de antes.
  const consulta = {base: lado('pais', {filtros: [f]}), referencia: lado('selecao_previa'), distancia: {medida: 'geodesica', ate: 'referencia_mais_proxima'}};
  const doPara = M.consultaNaSelecao(consulta, {todos: false, estados: ['15'], ids: []}, {todosOsEstados: estados, unidadesDoGrupo: () => []});
  assert.deepEqual(doPara.selecao, {todos: true, estados: [], ids: []});
  assert.deepEqual(doPara.consulta.base, lado('selecao_previa', {filtros: [f]}));
  assert.deepEqual(doPara.consulta.referencia, lado('ufs', {ufs: ['15']}));
  const doTodo = M.consultaNaSelecao({...consulta, base: lado('ufs', {ufs: ['13']})}, {todos: true, estados: [], ids: []},
    {todosOsEstados: estados, unidadesDoGrupo: () => []});
  assert.deepEqual([doTodo.selecao, doTodo.consulta.referencia], [{todos: false, estados: ['13'], ids: []}, lado('pais')]);
  // Sem a seleção, nada é pedido ao motor, também com a Escolha dos territórios em uso (antes, a consulta bastava).
  const vazia = {familia: 'espacial', nivel: 'municipios', base: {todos: false, estados: [], ids: []}, estados: [], conjuntos: [],
    consulta: M.consultaInicial()};
  assert.equal(M.semTerritorios(vazia), true);
  assert.equal(M.semTerritorios({...vazia, base: {todos: false, estados: ['15'], ids: []}}), false);
});

test('proteção (06/11/2026, item 4.6): de que lugar é o resultado à vista, com a preposição', () => {
  const comRotulo = {...TRILHA, arvore: {...ARVORE, grupos: ARVORE.grupos.map(g => g.id === '15' ? {...g, rotuloGrupo: 'Municípios do Pará'} : g)}};
  const grupos = comRotulo.arvore.grupos;
  assert.equal(M.deOndeEhOResultado(M.lugarDaTrilha(escolhaDaTrilha('estados', [], [], true, [], ['13', '15', '35']), comRotulo), {grupos}), 'do Brasil');
  assert.equal(M.deOndeEhOResultado(M.lugarDaTrilha(escolhaDaTrilha('municipios', ['15']), comRotulo), {grupos}), 'do Pará');
  assert.equal(M.deOndeEhOResultado(M.lugarDaTrilha(escolhaDaTrilha('municipios', ['13']), comRotulo), {grupos}), 'de Amazonas');
  assert.equal(M.deOndeEhOResultado(M.lugarDaTrilha(escolhaDaTrilha('municipios', [], ['code:150001']), comRotulo), {grupos}), 'de MARABA (PA)');
  assert.equal(M.deOndeEhOResultado(M.lugarDaTrilha(escolhaDaTrilha('municipios', ['13', '15']), comRotulo), {grupos}), 'de outra seleção');
  const planilha = {...comRotulo, nomeDoTodo: 'Toda a base', comGrupos: false};
  assert.equal(M.deOndeEhOResultado(M.lugarDaTrilha(escolhaDaTrilha('municipios', [], [], true), planilha), {grupos: []}), 'de toda a base');
  // Com o nome do todo (07/11/2026, item 1), ele mesmo, com o artigo, sem passar para a minúscula: "da Solária".
  assert.equal(M.deOndeEhOResultado(M.lugarDaTrilha(escolhaDaTrilha('municipios', [], [], true), {...planilha, nomeDoTodo: 'Solária'}),
    {grupos: [], brasil: false, rotulos: {...DISTRITOS, todo: {nome: 'Solária', artigo: 'a'}}}), 'da Solária');
});

test('confirmação conferida (06/11/2026, item 4.4): o pedido que leva a um lugar só conclui com a trilha e os itens desse lugar', () => {
  const lugarDe = (...args) => M.lugarDaTrilha(escolhaDaTrilha(...args), TRILHA);
  const atualDe = lugar => lugar.partes.find(parte => parte.atual);
  const maraba = {parte: atualDe(lugarDe('municipios', [], ['code:150001'])), escolha: escolhaDaTrilha('municipios', [], ['code:150001'])};
  const itensDe = (...ids) => ids.map(id => ({id, tipo: 'municipio'}));
  // A trilha em Marabá e só Marabá no gráfico: confere.
  assert.equal(M.lugarConfere(maraba, lugarDe('municipios', [], ['code:150001']), itensDe('code:150001')), null);
  // A trilha ainda no Pará (o caso do comando: a seleção mudou, a análise não): o que faltou, em palavras.
  assert.equal(M.lugarConfere(maraba, lugarDe('municipios', ['15']), itensDe('code:150001', 'code:150002')),
    'A área de análise não está em MARABA (PA): a trilha mostra Brasil › Pará.');
  // A trilha certa, mas o gráfico com outros itens.
  assert.equal(M.lugarConfere(maraba, lugarDe('municipios', [], ['code:150001']), itensDe('code:150001', 'code:150002')),
    'O gráfico ainda mostra territórios fora de MARABA (PA).');
  // O estado inteiro: os municípios dele conferem pelo grupo; os conjuntos não contam.
  const para = {parte: atualDe(lugarDe('municipios', ['15'])), escolha: escolhaDaTrilha('municipios', ['15'])};
  assert.equal(M.lugarConfere(para, lugarDe('municipios', ['15']), [...itensDe('code:150001', 'code:150002'), {id: 'c1', tipo: 'conjunto'}]), null);
  assert.equal(M.lugarConfere(para, lugarDe('municipios', ['13']), itensDe('code:130001')),
    'A área de análise não está em Pará: a trilha mostra Brasil › Amazonas.');
});

test('grupos em tela estreita (06/11/2026, item 7): a ordem do motor no cliente e os destaques das bolhas, com os empates no corte', () => {
  assert.deepEqual(A.ordemDoIndicadorDe({atributo: 'densidade', ordem: 'desc', itens: [{id: 'uf:53', posicao: 1}, {id: 'uf:21', posicao: null}]}),
    {atributo: 'densidade', itens: [{id: 'uf:53', posicao: 1}, {id: 'uf:21', posicao: null}]});
  assert.equal(A.ordemDoIndicadorDe(null), null);
  assert.equal(A.ordemDoIndicadorDe({itens: [{posicao: 1}]}), null);
  assert.equal(A.normalizarResposta({competencia: '202406', categoria: 'MEDICINA', itens: []}).ordemDoIndicador, null);
  // Os 3 maiores e os 3 menores pela ordem do motor; a tela não compara valores.
  const ordem = {itens: ['a', 'b', 'c', 'd', 'e', 'f', 'g', 'h'].map((id, i) => ({id, posicao: i + 1}))};
  assert.deepEqual([...M.destaquesDaOrdem(ordem)].sort(), ['a', 'b', 'c', 'f', 'g', 'h']);
  // Os empates no corte entram; os não avaliáveis, não.
  const empates = {itens: [{id: 'a', posicao: 1}, {id: 'b', posicao: 2}, {id: 'c', posicao: 3}, {id: 'd', posicao: 3}, {id: 'e', posicao: 5},
    {id: 'f', posicao: 6}, {id: 'g', posicao: 6}, {id: 'h', posicao: 8}, {id: 'x', posicao: null}]};
  assert.deepEqual([...M.destaquesDaOrdem(empates)].sort(), ['a', 'b', 'c', 'd', 'f', 'g', 'h']);
  assert.deepEqual([...M.destaquesDaOrdem({itens: [{id: 'a', posicao: 1}, {id: 'b', posicao: 2}]})].sort(), ['a', 'b']);
  assert.equal(M.destaquesDaOrdem(null).size, 0);
});
