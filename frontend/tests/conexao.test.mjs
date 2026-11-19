import {readFileSync} from 'node:fs';
import {test} from 'node:test';
import assert from 'node:assert/strict';
import ts from 'typescript';

// Estados da conexão (01/11/2026; hospedagem no GitHub Pages + Cloud Run): partida a frio, indisponível com a tentativa curta,
// novas tentativas com intervalo progressivo e teto, pausa com a aba oculta, botão, ocupado e o restabelecimento. O módulo roda
// com um relógio simulado; o roteiro de navegador ui_conexao.py confere o mesmo com o serviço parado e restabelecido.
async function source(name) {
  const code = ts.transpileModule(readFileSync(new URL('../src/' + name + '.ts', import.meta.url), 'utf8'),
    {compilerOptions: {module: ts.ModuleKind.ESNext, target: ts.ScriptTarget.ES2022}}).outputText;
  return import('data:text/javascript;base64,' + Buffer.from(code).toString('base64'));
}
const C = await source('conexao');
const esvaziar = () => new Promise(resolve => setImmediate(resolve));

function relogioFalso() {
  let agora = 0, sequencia = 0;
  const tarefas = new Map();
  return {
    agendar(acao, ms) { const id = ++sequencia; tarefas.set(id, {em: agora + ms, acao}); return id; },
    cancelar(id) { tarefas.delete(id); },
    async avancar(ms) {
      const fim = agora + ms;
      for (;;) {
        const [proxima] = [...tarefas.entries()].filter(([, t]) => t.em <= fim).sort((a, b) => a[1].em - b[1].em);
        if (!proxima) break;
        tarefas.delete(proxima[0]);
        agora = proxima[1].em;
        proxima[1].acao();
        await esvaziar();
      }
      agora = fim;
      await esvaziar();
    },
    pendentes: () => tarefas.size,
  };
}

/** O serviço simulado: cada verificação consome a próxima resposta (true, false ou 'pendente', que fica esperando). */
function servico(respostas) {
  const fila = [...respostas], pendentes = [];
  let chamadas = 0;
  return {
    verificar: () => { chamadas += 1; const r = fila.length ? fila.shift() : false;
      if (r === 'pendente') return new Promise(resolve => pendentes.push(resolve));
      return r === 'erro' ? Promise.reject(new TypeError('Failed to fetch')) : Promise.resolve(r); },
    responder: valor => pendentes.shift()(valor),
    chamadas: () => chamadas,
  };
}

function montar(respostas, visivel = true) {
  const relogio = relogioFalso(), s = servico(respostas), estados = [];
  let aVista = visivel;
  const monitor = C.criarMonitor({verificar: s.verificar, aoMudar: e => estados.push(e), relogio, visivel: () => aVista});
  return {relogio, s, estados, monitor, fases: () => estados.map(e => e.fase), ultimo: () => monitor.estado(),
    esconder: () => { aVista = false; monitor.visibilidade(false); }, mostrar: () => { aVista = true; monitor.visibilidade(true); }};
}

test('a mensagem institucional e os textos dos estados, sem código HTTP, provedor ou infraestrutura', () => {
  assert.equal(C.NOME_OFICIAL, 'Agente Diagnóstico Territorial da Força de Trabalho na Saúde');
  assert.equal(C.TITULO_INDISPONIVEL, 'Serviço temporariamente indisponível');
  assert.equal(C.TEXTO_INDISPONIVEL, 'O Agente Diagnóstico Territorial da Força de Trabalho na Saúde está temporariamente ' +
    'indisponível. Por favor, tente acessar novamente mais tarde. Agradecemos sua compreensão.');
  for (const texto of [C.TEXTO_INDISPONIVEL, C.TEXTO_INICIANDO, C.TEXTO_OCUPADO, C.TEXTO_RESTABELECIDA])
    assert.doesNotMatch(texto, /HTTP|\b\d{3}\b|Google|Cloud|Gemini|R\$|US\$|stack|erro interno/i);
  assert.deepEqual(C.INTERVALOS_MS, [...C.INTERVALOS_MS].sort((a, b) => a - b), 'intervalo progressivo');
  assert.ok(C.INTERVALOS_MS.length >= 3 && C.INTERVALOS_MS.length <= 8, 'teto de tentativas automáticas');
});

test('abertura com o serviço no ar: online, sem aviso', async () => {
  const m = montar([true]);
  m.monitor.iniciar();
  await m.relogio.avancar(0);
  assert.deepEqual(m.fases(), ['online']);
  assert.equal(m.ultimo().restabelecida, false);
  assert.equal(m.relogio.pendentes(), 0);
});

test('partida a frio (B): a verificação demorada mostra "iniciando" e, quando responde, online', async () => {
  const m = montar(['pendente']);
  m.monitor.iniciar();
  await m.relogio.avancar(C.AVISO_DE_PARTIDA_MS - 1);
  assert.equal(m.ultimo().fase, 'verificando');
  await m.relogio.avancar(1);
  assert.equal(m.ultimo().fase, 'iniciando');
  m.s.responder(true);
  await esvaziar();
  assert.equal(m.ultimo().fase, 'online');
  assert.equal(m.ultimo().restabelecida, false, 'a partida não é um restabelecimento');
});

test('a verificação sem resposta desiste no prazo e segue para a tentativa curta', async () => {
  let abortada = false;
  const relogio = relogioFalso();
  const monitor = C.criarMonitor({relogio, aoMudar: () => {}, verificar: sinal => new Promise((_, rejeitar) => {
    sinal.addEventListener('abort', () => { abortada = true; rejeitar(new Error('abortada')); }); })});
  monitor.iniciar();
  await relogio.avancar(C.PRAZO_DA_VERIFICACAO_MS);
  assert.ok(abortada);
  assert.equal(monitor.estado().fase, 'iniciando');
  monitor.encerrar();
});

test('serviço inacessível (A): a tentativa curta antes, depois as tentativas automáticas progressivas até o teto', async () => {
  const m = montar(Array(20).fill('erro'));
  m.monitor.iniciar();
  await m.relogio.avancar(0);
  assert.equal(m.ultimo().fase, 'iniciando', 'a primeira falha ainda não declara a indisponibilidade');
  await m.relogio.avancar(C.TENTATIVA_CURTA_MS);
  assert.equal(m.ultimo().fase, 'indisponivel');
  assert.equal(m.s.chamadas(), 2);
  for (const [i, intervalo] of C.INTERVALOS_MS.entries()) {
    await m.relogio.avancar(intervalo - 1);
    assert.equal(m.s.chamadas(), 2 + i, 'nenhuma tentativa antes do intervalo ' + intervalo);
    await m.relogio.avancar(1);
    assert.equal(m.s.chamadas(), 3 + i);
  }
  assert.equal(m.ultimo().esgotadas, true);
  assert.equal(m.ultimo().fase, 'indisponivel');
  await m.relogio.avancar(10 * 60 * 1000);
  assert.equal(m.s.chamadas(), 2 + C.INTERVALOS_MS.length, 'depois do teto, só o botão tenta de novo');
  assert.equal(m.relogio.pendentes(), 0);
});

test('o botão "Tentar novamente" verifica na hora, recomeça o ciclo e, com o serviço de volta, mostra o restabelecimento', async () => {
  const m = montar(['erro', 'erro', 'erro', true]);
  m.monitor.iniciar();
  await m.relogio.avancar(0);
  await m.relogio.avancar(C.TENTATIVA_CURTA_MS);
  assert.equal(m.ultimo().fase, 'indisponivel');
  m.monitor.tentarAgora();
  await esvaziar();
  assert.equal(m.s.chamadas(), 3);
  assert.equal(m.ultimo().fase, 'indisponivel');
  assert.equal(m.ultimo().tentativas, 0, 'o botão recomeça o ciclo das automáticas');
  await m.relogio.avancar(C.INTERVALOS_MS[0]);
  assert.equal(m.ultimo().fase, 'online');
  assert.equal(m.ultimo().restabelecida, true);
  await m.relogio.avancar(C.DURACAO_DO_RESTABELECIMENTO_MS);
  assert.equal(m.ultimo().restabelecida, false);
});

test('aba oculta: as tentativas automáticas esperam; ao voltar, a verificação sai na hora', async () => {
  const m = montar(['erro', 'erro', true]);
  m.monitor.iniciar();
  await m.relogio.avancar(0);
  await m.relogio.avancar(C.TENTATIVA_CURTA_MS);
  assert.equal(m.ultimo().fase, 'indisponivel');
  m.esconder();
  assert.equal(m.ultimo().pausada, true);
  await m.relogio.avancar(5 * 60 * 1000);
  assert.equal(m.s.chamadas(), 2, 'nenhuma tentativa com a aba oculta');
  m.mostrar();
  await esvaziar();
  assert.equal(m.s.chamadas(), 3);
  assert.equal(m.ultimo().fase, 'online');
  assert.equal(m.ultimo().pausada, false);
});

test('falha de rede durante o uso: a verificação silenciosa mantém a tela; só a segunda falha seguida declara a indisponibilidade', async () => {
  const m = montar([true, true, 'erro', 'erro']);
  m.monitor.iniciar();
  await m.relogio.avancar(0);
  m.monitor.falhaDeRede();
  await m.relogio.avancar(0);
  assert.equal(m.ultimo().fase, 'online', 'o serviço respondeu à verificação: a falha foi passageira');
  m.monitor.falhaDeRede();
  await m.relogio.avancar(0);
  assert.equal(m.ultimo().fase, 'online', 'a primeira falha não muda a tela');
  await m.relogio.avancar(C.TENTATIVA_CURTA_MS);
  assert.equal(m.ultimo().fase, 'indisponivel');
  assert.ok(!m.fases().includes('iniciando'), 'durante o uso, sem o aviso de partida');
});

test('ocupado (C): o aviso com o texto do serviço, sem a indisponibilidade; sai com a resposta de uma rota com limite ou sozinho', async () => {
  const m = montar([true]);
  m.monitor.iniciar();
  await m.relogio.avancar(0);
  m.monitor.ocupado('Muitas solicitações agora.');
  assert.equal(m.ultimo().fase, 'ocupado');
  assert.equal(m.ultimo().textoOcupado, 'Muitas solicitações agora.');
  m.monitor.respondeu(false);
  assert.equal(m.ultimo().fase, 'ocupado', 'a sessão e a saúde respondem mesmo com o serviço no limite: o aviso fica');
  m.monitor.respondeu(true);
  assert.equal(m.ultimo().fase, 'online');
  m.monitor.ocupado();
  assert.equal(m.ultimo().textoOcupado, C.TEXTO_OCUPADO);
  await m.relogio.avancar(C.DURACAO_DO_OCUPADO_MS);
  assert.equal(m.ultimo().fase, 'online');
  assert.ok(!m.fases().includes('indisponivel'));
});

/** Desde o PA-02, o observador consulta a fase e espera o serviço: um monitor online cujo serviço não responde de novo (a espera
 * depois de uma falha termina como indisponível, e a falha aparece como antes). */
function monitorOnlineSemNovaResposta() {
  return {estado: () => ({fase: 'online'}), marco: () => 0, aguardar: () => Promise.resolve('indisponivel')};
}

test('a observação dos pedidos: falha de rede, abortado, ocupado e resposta comum, sem mudar o resultado do pedido', async () => {
  const chamadas = [];
  const monitor = {falhaDeRede: () => chamadas.push('falha'), ocupado: texto => chamadas.push('ocupado:' + texto),
    respondeu: comLimite => chamadas.push('respondeu:' + comLimite), ...monitorOnlineSemNovaResposta()};
  const respostas = {
    'https://api.exemplo/api/rede': () => Promise.reject(new TypeError('Failed to fetch')),
    'https://api.exemplo/api/abortado': () => Promise.reject(Object.assign(new Error('aborted'), {name: 'AbortError'})),
    'https://api.exemplo/api/ocupado': () => Promise.resolve(new Response(JSON.stringify({detail: 'Ocupado agora.', ocupado: true}),
      {status: 503, headers: {'content-type': 'application/json'}})),
    'https://api.exemplo/api/plataforma': () => Promise.resolve(new Response('<html>', {status: 503})),
    'https://api.exemplo/api/ok': () => Promise.resolve(new Response('{}', {status: 200})),
    'https://api.exemplo/api/painel/mapa?v=1': () => Promise.resolve(new Response('{}', {status: 200})),
    'https://api.exemplo/api/session': () => Promise.resolve(new Response('{}', {status: 200})),
    'https://outro.exemplo/x': () => Promise.resolve(new Response('{}', {status: 200})),
  };
  const alvo = {fetch(url) { return respostas[url](); }};
  const original = alvo.fetch;
  const desfazer = C.observarRespostas(monitor, 'https://api.exemplo', alvo);
  await assert.rejects(alvo.fetch('https://api.exemplo/api/rede'), TypeError);
  await assert.rejects(alvo.fetch('https://api.exemplo/api/abortado'), {name: 'AbortError'});
  const ocupado = await alvo.fetch('https://api.exemplo/api/ocupado');
  assert.equal(ocupado.status, 503);
  assert.equal((await ocupado.json()).detail, 'Ocupado agora.', 'o corpo continua legível para quem pediu');
  assert.equal((await alvo.fetch('https://api.exemplo/api/plataforma')).status, 503);
  assert.equal((await alvo.fetch('https://api.exemplo/api/ok')).status, 200);
  await alvo.fetch('https://api.exemplo/api/painel/mapa?v=1');
  await alvo.fetch('https://api.exemplo/api/session');
  await alvo.fetch('https://outro.exemplo/x');
  assert.deepEqual(chamadas, ['falha', 'ocupado:Ocupado agora.', 'respondeu:false', 'respondeu:false', 'respondeu:true',
    'respondeu:false'], 'só a rota com limite (o mapa, com a consulta) conta como rota com limite');
  desfazer();
  assert.equal(alvo.fetch, original);
});

test('a observação no mesmo endereço da página (sem apiBase): o caminho relativo da rota com limite', async () => {
  const chamadas = [];
  const monitor = {falhaDeRede: () => chamadas.push('falha'), ocupado: () => chamadas.push('ocupado'),
    respondeu: comLimite => chamadas.push(comLimite), ...monitorOnlineSemNovaResposta()};
  const alvo = {fetch: () => Promise.resolve(new Response('{}', {status: 200}))};
  C.observarRespostas(monitor, '', alvo);
  await alvo.fetch('/api/inspect');
  await alvo.fetch('/api/session/interact');
  await alvo.fetch(new URL('http://127.0.0.1:5173/api/llm/interpret-context'));
  assert.deepEqual(chamadas, [true, false, true]);
  assert.ok(C.ROTAS_COM_LIMITE.has('/api/painel') && !C.ROTAS_COM_LIMITE.has('/api/health'));
});

// ------------------------------------------------------------------------------------------- PA-02: a página que espera
const ok = () => Promise.resolve(new Response('{}', {status: 200}));
const rede = () => Promise.reject(new TypeError('Failed to fetch'));

/** A página com o monitor de verdade (relógio simulado) e o fetch roteirizado: cada chamada registra a URL e o método. */
function pagina(verificacoes, roteiro) {
  const m = montar(verificacoes), feitos = [];
  const alvo = {fetch: (url, init) => {
    feitos.push(String(url) + ' ' + ((init && init.method) || 'GET'));
    return roteiro(String(url), init, feitos.length);
  }};
  C.observarRespostas(m.monitor, 'https://api.exemplo', alvo);
  return {...m, alvo, feitos};
}
const API = 'https://api.exemplo/api/';

test('PA-02: na partida, o pedido espera o serviço responder antes de sair, com o aviso de partida, e sai uma vez só', async () => {
  const p = pagina(['pendente'], ok);
  p.monitor.iniciar();
  await p.relogio.avancar(C.AVISO_DE_PARTIDA_MS);
  assert.equal(p.ultimo().fase, 'iniciando');
  let resposta = null;
  const pedido = p.alvo.fetch(API + 'inspect', {method: 'POST', body: new FormData()}).then(r => { resposta = r; });
  await p.relogio.avancar(20000);
  assert.deepEqual(p.feitos, [], 'o pedido espera, sem erro na tela');
  assert.equal(resposta, null);
  p.s.responder(true);   // o serviço abriu a porta
  await p.relogio.avancar(0);
  await pedido;
  assert.equal(p.ultimo().fase, 'online');
  assert.deepEqual(p.feitos, [API + 'inspect POST']);
  assert.equal(resposta.status, 200);
});

test('PA-02: se o monitor for para indisponível durante a espera, o pedido sai e falha como antes, sem se repetir', async () => {
  const p = pagina(['erro', 'erro'], rede);
  p.monitor.iniciar();
  await p.relogio.avancar(0);
  assert.equal(p.ultimo().fase, 'iniciando', 'a primeira verificação falhou: a tentativa curta');
  const falha = assert.rejects(p.alvo.fetch(API + 'painel', {method: 'POST', body: '{}'}), TypeError);
  await p.relogio.avancar(C.TENTATIVA_CURTA_MS);
  await falha;
  assert.equal(p.ultimo().fase, 'indisponivel');
  assert.deepEqual(p.feitos, [API + 'painel POST'], 'saiu uma vez, depois da indisponibilidade');
});

test('PA-02: a falha de rede de um pedido que só lê ou calcula espera o serviço responder e se repete uma vez (DA-26)', async () => {
  assert.equal(C.REPETICOES_DEPOIS_DA_FALHA, 1, 'uma repetição, como na DA-26 (decisão do responsável de 19/11/2026)');
  const p = pagina([true, true], (url, init, n) => n === 1 ? rede() : ok());
  p.monitor.iniciar();
  await p.relogio.avancar(0);
  const resposta = await p.alvo.fetch(API + 'detector', {method: 'POST', body: '{}'});
  assert.equal(resposta.status, 200, 'sem erro e sem segundo clique');
  assert.equal(p.feitos.length, 2, 'o pedido e a repetição');
  assert.equal(p.s.chamadas(), 2, 'a repetição só sai depois de uma verificação com resposta');
  assert.equal(p.ultimo().fase, 'online');
  // A repetição que também falha: o erro aparece como antes, sem uma segunda repetição.
  const sempre = pagina([true, true, true], rede);
  sempre.monitor.iniciar();
  await sempre.relogio.avancar(0);
  await assert.rejects(sempre.alvo.fetch(API + 'simulador', {method: 'POST', body: '{}'}), TypeError);
  assert.equal(sempre.feitos.length, 2, 'o pedido e uma repetição só');
  // As leituras também se repetem; a criação da sessão, o exame da base e o mapa, também.
  for (const [rota, metodo] of [['brazil/description', 'GET'], ['session', 'POST'], ['inspect', 'POST'], ['painel/mapa', 'POST']]) {
    const uma = pagina([true, true], (url, init, n) => n === 1 ? rede() : ok());
    uma.monitor.iniciar();
    await uma.relogio.avancar(0);
    assert.equal((await uma.alvo.fetch(API + rota, {method: metodo})).status, 200, rota);
    assert.equal(uma.feitos.length, 2, rota);
  }
});

test('PA-02: a repetição desiste quando o serviço fica indisponível e quando a página cancela', async () => {
  const p = pagina([true, 'erro', 'erro'], rede);
  p.monitor.iniciar();
  await p.relogio.avancar(0);
  const falha = assert.rejects(p.alvo.fetch(API + 'painel', {method: 'POST', body: '{}'}), TypeError);
  await p.relogio.avancar(0);   // a falha dispara a verificação, que falha e agenda a tentativa curta
  await p.relogio.avancar(C.TENTATIVA_CURTA_MS);
  await falha;
  assert.equal(p.ultimo().fase, 'indisponivel');
  assert.equal(p.feitos.length, 1, 'sem repetição com o serviço indisponível');
  const q = pagina([true, 'pendente'], rede);
  q.monitor.iniciar();
  await q.relogio.avancar(0);
  const controle = new AbortController();
  const cancelado = assert.rejects(q.alvo.fetch(API + 'detector', {method: 'POST', body: '{}', signal: controle.signal}),
    {name: 'AbortError'});
  await q.relogio.avancar(0);
  controle.abort();
  await cancelado;
  assert.equal(q.feitos.length, 1, 'cancelado durante a espera: não sai de novo');
});

test('PA-02: nunca se repetem sozinhos a conversa, os eventos da sessão, o pré-exame, o envio de arquivo, o cancelado e o ocupado', async () => {
  const arquivo = new FormData();
  arquivo.append('file', new Blob(['a;b\n1;2\n']), 'planilha.csv');
  const casos = [['llm/interpret', {method: 'POST', body: '{}'}], ['llm/interpret-context', {method: 'POST', body: '{}'}],
    ['exploration/interpret', {method: 'POST', body: '{}'}], ['session/interact', {method: 'POST', body: '{}'}],
    ['session/revision', {method: 'POST', body: '{}'}], ['session/close', {method: 'POST'}], ['preflight', {method: 'POST', body: '{}'}],
    ['painel', {method: 'POST', body: arquivo}], ['inspect', {method: 'POST', body: arquivo}], ['session', {method: 'GET'}]];
  for (const [rota, init] of casos) {
    const p = pagina([true, true, true], rede);
    p.monitor.iniciar();
    await p.relogio.avancar(0);
    await assert.rejects(p.alvo.fetch(API + rota, init), TypeError, rota);
    assert.equal(p.feitos.length, 1, rota + ': uma vez só');
  }
  const abortado = pagina([true, true], () => Promise.reject(Object.assign(new Error('aborted'), {name: 'AbortError'})));
  abortado.monitor.iniciar();
  await abortado.relogio.avancar(0);
  await assert.rejects(abortado.alvo.fetch(API + 'painel', {method: 'POST', body: '{}'}), {name: 'AbortError'});
  assert.equal(abortado.feitos.length, 1);
  for (const corpo of [JSON.stringify({detail: 'Ocupado agora.', ocupado: true}), '<html>']) {
    const p = pagina([true, true], () => Promise.resolve(new Response(corpo, {status: 503})));
    p.monitor.iniciar();
    await p.relogio.avancar(0);
    assert.equal((await p.alvo.fetch(API + 'painel', {method: 'POST', body: '{}'})).status, 503, 'a resposta legível, como antes');
    assert.equal(p.feitos.length, 1);
  }
});

test('PA-02: na partida, a consulta e os eventos da sessão saem na hora, como antes; a criação da sessão e a conversa esperam', async () => {
  const daSessao = (url, init) => (url === API + 'session' && !(init && init.method)) || url === API + 'session/interact';
  const p = pagina(['pendente'], (url, init) => daSessao(url, init) ? rede() : ok());   // o serviço ainda não abriu a porta
  p.monitor.iniciar();
  await p.relogio.avancar(C.AVISO_DE_PARTIDA_MS);
  await assert.rejects(p.alvo.fetch(API + 'session', {headers: {'X-ADT-Session': 't'}}), TypeError);
  await assert.rejects(p.alvo.fetch(API + 'session/interact', {method: 'POST', body: '{}'}), TypeError);
  assert.deepEqual(p.feitos, [API + 'session GET', API + 'session/interact POST'], 'saíram na hora e falharam como antes');
  assert.equal(p.ultimo().fase, 'iniciando');
  const criacao = p.alvo.fetch(API + 'session', {method: 'POST'});
  const conversa = p.alvo.fetch(API + 'llm/interpret', {method: 'POST', body: '{}'});
  await p.relogio.avancar(5000);
  assert.equal(p.feitos.length, 2, 'a criação da sessão e a mensagem esperam o serviço');
  p.s.responder(true);
  await p.relogio.avancar(0);
  await Promise.all([criacao, conversa]);
  assert.deepEqual(p.feitos.slice(2).sort(), [API + 'llm/interpret POST', API + 'session POST'], 'a mensagem sai uma vez só');
});

test('PA-02: o cancelamento durante a espera da partida cancela, sem o pedido sair', async () => {
  const p = pagina(['pendente'], ok);
  p.monitor.iniciar();
  await p.relogio.avancar(C.AVISO_DE_PARTIDA_MS);
  const controle = new AbortController();
  const pedido = assert.rejects(p.alvo.fetch(API + 'painel', {method: 'POST', body: '{}', signal: controle.signal}),
    {name: 'AbortError'});
  controle.abort();
  await pedido;
  p.s.responder(true);
  await p.relogio.avancar(0);
  assert.deepEqual(p.feitos, []);
});

test('PA-02: a espera do monitor: online, indisponível, prazo, cancelada e uma resposta nova depois de um marco', async () => {
  const m = montar(['pendente']);
  m.monitor.iniciar();
  const online = m.monitor.aguardar();
  const curta = m.monitor.aguardar({prazoMs: 1000});
  const controle = new AbortController();
  const cancelada = m.monitor.aguardar({sinal: controle.signal});
  controle.abort();
  assert.equal(await cancelada, 'abortado');
  await m.relogio.avancar(1000);
  assert.equal(await curta, 'prazo');
  m.s.responder(true);
  await m.relogio.avancar(0);
  assert.equal(await online, 'online');
  const marco = m.monitor.marco();
  let nova = null;
  m.monitor.aguardar({depoisDe: marco}).then(d => { nova = d; });
  await m.relogio.avancar(0);
  assert.equal(nova, null, 'online, mas sem resposta nova depois do marco');
  m.monitor.respondeu(false);
  await m.relogio.avancar(0);
  assert.equal(nova, 'online');
  const fora = montar(['erro', 'erro']);
  fora.monitor.iniciar();
  const indisponivel = fora.monitor.aguardar();
  await fora.relogio.avancar(0);   // a abertura falhou: a tentativa curta fica agendada
  await fora.relogio.avancar(C.TENTATIVA_CURTA_MS);
  assert.equal(await indisponivel, 'indisponivel');
  const encerrado = montar(['pendente']);
  encerrado.monitor.iniciar();
  const espera = encerrado.monitor.aguardar();
  encerrado.monitor.encerrar();
  assert.equal(await espera, 'prazo', 'com o monitor encerrado, os pedidos saem como antes');
});
