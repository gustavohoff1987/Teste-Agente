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

test('a observação dos pedidos: falha de rede, abortado, ocupado e resposta comum, sem mudar o resultado do pedido', async () => {
  const chamadas = [];
  const monitor = {falhaDeRede: () => chamadas.push('falha'), ocupado: texto => chamadas.push('ocupado:' + texto),
    respondeu: comLimite => chamadas.push('respondeu:' + comLimite)};
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
    respondeu: comLimite => chamadas.push(comLimite)};
  const alvo = {fetch: () => Promise.resolve(new Response('{}', {status: 200}))};
  C.observarRespostas(monitor, '', alvo);
  await alvo.fetch('/api/inspect');
  await alvo.fetch('/api/session/interact');
  await alvo.fetch(new URL('http://127.0.0.1:5173/api/llm/interpret-context'));
  assert.deepEqual(chamadas, [true, false, true]);
  assert.ok(C.ROTAS_COM_LIMITE.has('/api/painel') && !C.ROTAS_COM_LIMITE.has('/api/health'));
});
