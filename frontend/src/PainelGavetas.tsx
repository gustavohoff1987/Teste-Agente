import { useEffect, useMemo, useState } from "react";
import { Download, FileText, Plus, Printer, Trash2, X } from "lucide-react";
import type {
  AtributoCondicao, AtributoOrdenacao, CondicaoPedido, OperadorCondicao, OrdenarPedido, PainelConjuntoPedido, PainelIndicador, PainelItem,
  PainelOrdem, PainelResposta, SituacaoCondicao,
} from "./painelApi";
import {
  ATRIBUTOS, MAX_CONJUNTOS, OPERADORES, ORDENS, SIMBOLOS, artigo, formatarIndicador, formatarNumero, formatarVariacao, generoDe, maiuscula,
  numero, ordemNeutra, quantos, variacaoDe, type RotulosTerritoriais,
} from "./painelModel";

// Painéis laterais das funções e das opções das análises. Os valores, as posições, as contagens e as comparações vêm do motor;
// a tela só lista, marca e pede. Cada painel é um formulário curto: o pedido sai só no botão de aplicar.

// ------------------------------------------------------------------------------------------------ condições
type Rascunho = { atributo: AtributoCondicao; operador: OperadorCondicao; valor: string };
type CondicoesProps = { condicoes: CondicaoPedido[]; espacial: boolean; resposta: PainelResposta | null; rotulos: RotulosTerritoriais;
  soAtende: boolean; onSoAtende: (valor: boolean) => void; onAplicar: (condicoes: CondicaoPedido[]) => void };
const UNIDADES: Record<AtributoCondicao, string> = { densidade: "por 1.000 habitantes", quantidade: "profissionais", populacao: "habitantes", distancia_km: "km" };
const lerNumero = (texto: string) => { const valor = Number(texto.trim().replace(/\./g, "").replace(",", ".")); return texto.trim() && Number.isFinite(valor) ? valor : null; };
/** Condições (CAP-SUB-01, o antigo "critérios combinados"): separa quem atende a todas as condições, quem não atende e quem não
 * tem dado para avaliar. Combinação "e". As contagens vêm do motor. */
export function GavetaCondicoes(p: CondicoesProps) {
  const paraRascunho = (c: CondicaoPedido): Rascunho => ({ atributo: c.atributo, operador: c.operador, valor: String(c.valor).replace(".", ",") });
  const [linhas, setLinhas] = useState<Rascunho[]>(() => p.condicoes.length ? p.condicoes.map(paraRascunho) : [{ atributo: "densidade", operador: "<", valor: "" }]);
  useEffect(() => { if (p.condicoes.length) setLinhas(p.condicoes.map(paraRascunho)); }, [JSON.stringify(p.condicoes)]);
  const validas = linhas.map(linha => ({ ...linha, numero: lerNumero(linha.valor) }));
  const prontas = validas.every(linha => linha.numero !== null) && validas.length > 0;
  const contagens = p.resposta?.condicoes?.contagens;
  const unidade = p.rotulos.unidade;
  const mudar = (indice: number, parte: Partial<Rascunho>) => setLinhas(atual => atual.map((linha, i) => i === indice ? { ...linha, ...parte } : linha));
  const NOMES: Record<SituacaoCondicao, string> = { ATENDE: "Atendem a todas", NAO_ATENDE: "Não atendem", NAO_AVALIAVEL: "Sem dado para avaliar" };
  return <section data-testid="analise-condicoes" aria-label="Seleção por condições" className="space-y-3">
    <p className="text-xs leading-5 text-slate-600">Separa {artigo(unidade, true)} {unidade.plural} que atendem a todas as condições escolhidas, os que não atendem
      e os que não têm dado para avaliar. Por exemplo: menos de 1 profissional por 1.000 habitantes e mais de 150 km da referência.</p>
    <ol className="space-y-2">
      {linhas.map((linha, indice) => <li key={indice} data-testid="analise-condicao" className="flex flex-wrap items-end gap-1.5">
        <label className="analise-rotulo-campo min-w-[8rem] flex-1">Indicador
          <select data-testid="analise-condicao-atributo" value={linha.atributo} onChange={event => mudar(indice, { atributo: event.target.value as AtributoCondicao })} className="analise-campo">
            <option value="densidade">Densidade</option><option value="quantidade">Quantidade</option><option value="populacao">População</option>
            <option value="distancia_km" disabled={!p.espacial}>Distância até a referência (km){p.espacial ? "" : " · só na análise espacial"}</option>
          </select>
        </label>
        <label className="analise-rotulo-campo w-28">Condição
          <select data-testid="analise-condicao-operador" value={linha.operador} onChange={event => mudar(indice, { operador: event.target.value as OperadorCondicao })} className="analise-campo">
            {(Object.keys(OPERADORES) as OperadorCondicao[]).map(op => <option key={op} value={op}>{SIMBOLOS[op]} {OPERADORES[op]}</option>)}
          </select>
        </label>
        <label className="analise-rotulo-campo w-28">Valor ({UNIDADES[linha.atributo]})
          <input data-testid="analise-condicao-valor" inputMode="decimal" value={linha.valor} onChange={event => mudar(indice, { valor: event.target.value })}
            className="analise-campo" aria-invalid={!!linha.valor.trim() && lerNumero(linha.valor) === null}/>
        </label>
        {linhas.length > 1 && <button type="button" className="analise-icone" aria-label={"Tirar a condição " + (indice + 1)}
          onClick={() => setLinhas(atual => atual.filter((_, i) => i !== indice))}><Trash2 size={14} aria-hidden="true"/></button>}
      </li>)}
    </ol>
    <div className="flex flex-wrap gap-2">
      <button type="button" data-testid="analise-condicao-mais" className="analise-botao-secundario" disabled={linhas.length >= 5}
        onClick={() => setLinhas(atual => [...atual, { atributo: "densidade", operador: ">", valor: "" }])}><Plus size={14} aria-hidden="true"/>Condição</button>
      <button type="button" data-testid="analise-condicoes-aplicar" className="analise-botao-primario" disabled={!prontas}
        onClick={() => p.onAplicar(validas.map(linha => ({ atributo: linha.atributo, operador: linha.operador, valor: linha.numero as number })))}>
        Aplicar condições</button>
      {p.condicoes.length > 0 && <button type="button" data-testid="analise-condicoes-limpar" className="analise-botao-secundario"
        onClick={() => { p.onAplicar([]); p.onSoAtende(false); }}>Limpar</button>}
    </div>
    {contagens && p.condicoes.length > 0 && <div className="space-y-2">
      <ul className="flex flex-wrap gap-1.5" aria-label="Contagens">
        {(["ATENDE", "NAO_ATENDE", "NAO_AVALIAVEL"] as SituacaoCondicao[]).map(situacao => <li key={situacao} data-testid="analise-condicoes-contagem"
          data-situacao={situacao} data-contagem={contagens[situacao] ?? ""} className="analise-contagem">
          <strong className="tabular-nums text-ink">{contagens[situacao] ?? "—"}</strong> {NOMES[situacao].toLowerCase()}</li>)}
      </ul>
      <label className="analise-caixa">
        <input type="checkbox" data-testid="analise-condicoes-so-atende" checked={p.soAtende} onChange={event => p.onSoAtende(event.target.checked)}/>
        <span>Mostrar no gráfico só quem atende (filtro visual, sem novo cálculo)</span>
      </label>
      {(p.resposta?.condicoes?.textos || []).map(texto => <p key={texto} className="text-[11px] text-slate-600">{texto}</p>)}
    </div>}
  </section>;
}

// ------------------------------------------------------------------------------------------------ ordenar
type OrdenarProps = { ordenar: OrdenarPedido | null; espacial: boolean; mudanca: boolean; resposta: PainelResposta | null;
  indicador: PainelIndicador; onAplicar: (ordenar: OrdenarPedido | null) => void };
/** Ordenar (CAP-SUB-02 e CAP-SUB-03): a ordem e as posições do motor, com empates na mesma posição, e os N primeiros. */
export function GavetaOrdenar(p: OrdenarProps) {
  const [atributo, setAtributo] = useState<AtributoOrdenacao>(p.ordenar?.atributo ?? p.indicador);
  const [ordem, setOrdem] = useState<PainelOrdem>(p.ordenar?.ordem ?? "desc");
  const [primeiros, setPrimeiros] = useState(p.ordenar?.primeiros ? String(p.ordenar.primeiros) : "10");
  const n = Number(primeiros);
  const valido = !primeiros.trim() || (Number.isInteger(n) && n > 0);
  const ordenacao = p.resposta?.ordenacao;
  const posicionados = useMemo(() => (p.resposta?.itens || []).filter(item => item.ordem?.posicao !== null && item.ordem?.posicao !== undefined)
    .sort((a, b) => (a.ordem!.posicao as number) - (b.ordem!.posicao as number) || ordemNeutra(a, b)), [p.resposta]);
  const limite = ordenacao?.primeiros ?? null;
  const mostrados = limite !== null ? posicionados.filter(item => (item.ordem!.posicao as number) <= limite) : posicionados.slice(0, 20);
  const valorDe = (item: PainelItem) => {
    const a = ordenacao?.atributo || atributo;
    if (a === "variacao") return formatarVariacao(variacaoDe(item, p.indicador));
    if (a === "distancia_km") return numero(item.distancia_km) === null ? "Não avaliável" : formatarNumero(item.distancia_km as number) + " km";
    if (a === "populacao") return numero(item.populacao) === null ? "Não avaliável" : formatarNumero(item.populacao as number, true) + " habitantes";
    if (a === "quantidade" || a === "densidade") return formatarIndicador(numero(item[a]), a);
    return "";
  };
  return <section data-testid="analise-ordenar" aria-label="Ordenar" className="space-y-3">
    <p className="text-xs leading-5 text-slate-600">A ordem segue o indicador e o sentido que você escolher; empates ficam na mesma posição (1, 2, 2, 4).
      "Os N primeiros" mostra só as posições até N, com todos os empatados no corte.</p>
    <div className="grid gap-2 sm:grid-cols-3">
      <label className="analise-rotulo-campo">Indicador
        <select data-testid="analise-ordenar-atributo" value={atributo} onChange={event => setAtributo(event.target.value as AtributoOrdenacao)} className="analise-campo">
          <option value="densidade">Densidade</option><option value="quantidade">Quantidade</option><option value="populacao">População</option>
          <option value="distancia_km" disabled={!p.espacial}>Distância (km){p.espacial ? "" : " · só na análise espacial"}</option>
          <option value="variacao" disabled={!p.mudanca}>Variação (%){p.mudanca ? "" : " · só na mudança"}</option>
        </select>
      </label>
      <label className="analise-rotulo-campo">Ordem
        <select data-testid="analise-ordenar-ordem" value={ordem} onChange={event => setOrdem(event.target.value as PainelOrdem)} className="analise-campo">
          <option value="desc">Da maior para a menor</option><option value="asc">Da menor para a maior</option>
        </select>
      </label>
      <label className="analise-rotulo-campo">Os N primeiros
        <input data-testid="analise-ordenar-primeiros" inputMode="numeric" value={primeiros} onChange={event => setPrimeiros(event.target.value)}
          className="analise-campo" aria-invalid={!valido} placeholder="todos"/>
      </label>
    </div>
    <div className="flex flex-wrap gap-2">
      <button type="button" data-testid="analise-ordenar-aplicar" className="analise-botao-primario" disabled={!valido}
        onClick={() => p.onAplicar({ atributo, ordem, ...(primeiros.trim() ? { primeiros: n } : {}) })}>Ordenar</button>
      {p.ordenar && <button type="button" data-testid="analise-ordenar-limpar" className="analise-botao-secundario" onClick={() => p.onAplicar(null)}>Limpar</button>}
    </div>
    {ordenacao && p.ordenar && <div className="space-y-1.5">
      <p className="text-xs text-slate-700">{ordenacao.texto || "Ordem por " + (ATRIBUTOS[ordenacao.atributo] || ordenacao.atributo) + ", " +
        (ORDENS[ordenacao.ordem as PainelOrdem] || ordenacao.ordem) + "."}{ordenacao.empatesNoCorte ? " Há empate no corte: os empatados entram juntos." : ""}</p>
      <ol data-testid="analise-ordenar-lista" className="analise-lista-rolavel">
        {mostrados.map(item => <li key={item.id} data-id={item.id} data-posicao={item.ordem!.posicao ?? ""} className="flex items-center gap-2 px-2 py-1 text-xs">
          <span className="w-9 shrink-0 tabular-nums text-slate-600">{item.ordem!.posicao}º</span>
          <span className="min-w-0 flex-1 truncate text-ink">{item.rotulo}</span>
          <span className="shrink-0 tabular-nums text-slate-700">{valorDe(item)}</span>
        </li>)}
      </ol>
      {limite === null && posicionados.length > 20 && <p className="text-[11px] text-slate-600">Os 20 primeiros; a ordem completa fica na tabela (coluna Posição).</p>}
    </div>}
  </section>;
}

// ------------------------------------------------------------------------------------------------ comparar
type CompararProps = { itens: PainelItem[]; selecionados: string[]; pedidos: string[]; resposta: PainelResposta | null;
  nomes: Map<string, string>; rotulos: RotulosTerritoriais;
  onAlternar: (id: string) => void; onLimpar: () => void; onComparar: (ids: string[]) => void };
/** Comparar (CAP-CMP-01): 2 ou 3 itens lado a lado, com maior, menor e diferença vindos do motor. Desde 24/10/2026, a escolha é
 * só a orientação e as etiquetas dos itens (os cartões com densidade, população e outros valores saíram: os valores estão no
 * gráfico, na dica e na tabela); o resultado da comparação continua. */
export function GavetaComparar(p: CompararProps) {
  const escolhidos = p.selecionados.map(id => p.itens.find(item => item.id === id)).filter((item): item is PainelItem => !!item);
  const comparacao = p.resposta?.comparacao;
  const atual = p.pedidos.length >= 2 && [...p.pedidos].sort().join() === [...p.selecionados].sort().join();
  const nome = (id: string) => p.nomes.get(id) || id;
  const valorComparado = (atributo: string, valor: number | null) => valor === null ? "Não avaliável"
    : atributo === "densidade" || atributo === "quantidade" ? formatarIndicador(valor, atributo)
    : atributo === "populacao" ? formatarNumero(valor, true) + " habitantes" : atributo === "distancia_km" ? formatarNumero(valor) + " km"
    : atributo.startsWith("variacao") ? formatarVariacao(valor) : formatarNumero(valor);
  const faltam = Math.max(0, 2 - escolhidos.length);
  return <section data-testid="analise-comparar" aria-label="Comparar" className="space-y-3">
    <p data-testid="analise-comparar-orientacao" className="text-xs leading-5 text-slate-600">Escolha dois ou três itens: clique nas bolhas do gráfico (ou nas
      linhas do quadro de setas) ou marque a caixa na tabela dos Detalhes. Depois, use Comparar: o resultado diz qual é o maior, o menor e a
      diferença, e, no gráfico de bolhas, os demais esmaecem para destacar os comparados.</p>
    {escolhidos.length > 0 ? <ul className="flex flex-wrap gap-1.5" aria-label="Itens escolhidos">
      {escolhidos.map(item => <li key={item.id} data-testid="analise-comparar-item" data-id={item.id} className="analise-etiqueta">
        {item.rotulo}
        <button type="button" aria-label={"Tirar " + item.rotulo} onClick={() => p.onAlternar(item.id)} className="analise-icone"><X size={13} aria-hidden="true"/></button>
      </li>)}
      <li><button type="button" onClick={p.onLimpar} className="analise-link text-xs">Limpar a escolha</button></li>
    </ul> : <p className="text-xs text-slate-600">Nenhum item escolhido.</p>}
    {faltam > 0 && <p className="text-xs text-slate-600">Falta{faltam > 1 ? "m" : ""} {faltam === 1 ? "um item" : "dois itens"} para comparar.</p>}
    {escolhidos.length > 3 && <p className="text-xs text-amber-900">Para comparar lado a lado, deixe até três itens. Com mais, use Juntar.</p>}
    <button type="button" data-testid="analise-comparar-calcular" className="analise-botao-primario"
      disabled={escolhidos.length < 2 || escolhidos.length > 3 || atual} onClick={() => p.onComparar(escolhidos.map(item => item.id))}>
      {atual ? "Comparação em exibição" : "Comparar"}</button>
    {atual && comparacao && <section data-testid="analise-comparacao" aria-label="Resultado da comparação" className="space-y-2 rounded-xl border border-line bg-white p-3 text-xs">
      <h4 className="font-bold text-ink">Resultado da comparação</h4>
      {comparacao.linhas.map(linha => <div key={linha.atributo} data-testid="analise-comparacao-linha" data-atributo={linha.atributo} className="space-y-0.5">
        {linha.atributo && <p className="font-semibold text-ink">{maiuscula(ATRIBUTOS[linha.atributo] || linha.atributo)}</p>}
        {linha.maior.length > 0 && <p>Maior: {linha.maior.map(item => item.rotulo + " (" + valorComparado(linha.atributo, item.valor) + ")").join(" e ")}
          {linha.maior.length > 1 ? " (empate)" : ""}</p>}
        {linha.menor.length > 0 && <p>Menor: {linha.menor.map(item => item.rotulo + " (" + valorComparado(linha.atributo, item.valor) + ")").join(" e ")}
          {linha.menor.length > 1 ? " (empate)" : ""}</p>}
        {linha.diferencas.map((dif, indice) => <p key={indice}>Diferença{dif.entre.length === 2 ? " entre " + nome(dif.entre[0]) + " e " + nome(dif.entre[1]) : ""}:{" "}
          {dif.texto || valorComparado(linha.atributo, dif.valor)}</p>)}
      </div>)}
      {comparacao.textos.map(texto => <p key={texto} className="text-slate-600">{texto}</p>)}
    </section>}
  </section>;
}

// ------------------------------------------------------------------------------------------------ juntar
type JuntarProps = { itens: PainelItem[]; selecionados: string[]; conjuntos: PainelConjuntoPedido[]; rotulos: RotulosTerritoriais;
  nivelGrupos: boolean; onJuntar: (rotulo: string) => void; onDesfazer: (id: string) => void; onAlternar: (id: string) => void };
/** Juntar (CAP-AGR-01): as unidades escolhidas viram uma bolha agregada pelo motor, com a soma das contagens dos componentes e
 * possível dupla contagem (RQ-REP-14). Estados e municípios nunca se somam: na visão dos grupos, Juntar fica desligado. Desde
 * 24/10/2026, a escolha aparece como no Comparar: a orientação e as etiquetas dos escolhidos, cada uma com o ×. */
export function GavetaJuntar(p: JuntarProps) {
  const [nome, setNome] = useState("");
  const unidades = p.selecionados.map(id => p.itens.find(item => item.id === id)).filter((item): item is PainelItem => !!item && item.tipo === "municipio");
  const unidade = p.rotulos.unidade;
  return <section data-testid="analise-juntar" aria-label="Juntar" className="space-y-3">
    <p data-testid="analise-juntar-orientacao" className="text-xs leading-5 text-slate-600">Escolha {generoDe(unidade) === "f" ? "duas" : "dois"} ou mais{" "}
      {unidade.plural}: clique nas bolhas do gráfico ou marque a caixa na tabela dos Detalhes. Juntar faz uma bolha só, com a soma das
      populações e das contagens dos membros (soma das contagens dos componentes, com possível dupla contagem).</p>
    {p.nivelGrupos ? <p className="text-xs text-amber-900">Na visão dos {(p.rotulos.grupo?.plural || "grupos")}, Juntar fica desligado: {p.rotulos.grupo?.plural || "grupos"} e{" "}
      {unidade.plural} nunca se somam aqui. Abra {unidade.plural} para juntar.</p> : <>
      {unidades.length ? <ul className="flex flex-wrap gap-1.5" aria-label="Escolhidos para juntar">
        {unidades.map(item => <li key={item.id} data-testid="analise-juntar-item" data-id={item.id} className="analise-etiqueta">
          {item.rotulo}
          <button type="button" aria-label={"Tirar " + item.rotulo} onClick={() => p.onAlternar(item.id)} className="analise-icone"><X size={13} aria-hidden="true"/></button>
        </li>)}
      </ul> : <p className="text-xs text-slate-600">Nenhum escolhido.</p>}
      <div className="flex flex-wrap items-end gap-2">
        <label className="analise-rotulo-campo min-w-[12rem] flex-1">Nome do conjunto
          <input data-testid="analise-juntar-nome" value={nome} onChange={event => setNome(event.target.value)} maxLength={60}
            placeholder={"Conjunto " + (p.conjuntos.length + 1)} className="analise-campo"/>
        </label>
        <button type="button" data-testid="analise-juntar-criar" disabled={unidades.length < 2 || p.conjuntos.length >= MAX_CONJUNTOS}
          onClick={() => { p.onJuntar(nome); setNome(""); }} className="analise-botao-primario">Juntar escolhidos</button>
      </div>
    </>}
    {p.conjuntos.length >= MAX_CONJUNTOS && <p className="text-[11px] text-amber-900">O gráfico aceita até {MAX_CONJUNTOS} conjuntos.</p>}
    {p.conjuntos.length > 0 && <ul className="space-y-1" aria-label="Conjuntos">
      {p.conjuntos.map(conjunto => <li key={conjunto.id} data-testid="analise-conjunto" data-id={conjunto.id}
        className="flex flex-wrap items-center justify-between gap-2 rounded-lg border border-line bg-white px-3 py-2 text-xs">
        <span className="min-w-0"><strong className="text-ink">{conjunto.rotulo}</strong> · {quantos(conjunto.membros.length, unidade)} · soma das contagens dos
          componentes, com possível dupla contagem</span>
        <button type="button" onClick={() => p.onDesfazer(conjunto.id)} className="analise-link">Desfazer</button>
      </li>)}
    </ul>}
  </section>;
}

// ------------------------------------------------------------------------------------------------ exportar
type ExportarProps = { pronto: boolean; onCsv: () => void; onImprimir: () => void; onMetodo: () => void };
/** Exportar (CAP-REP-05/06): CSV com precisão integral, avaliabilidade e motivo; Imprimir/PDF; método e parâmetros. */
export function GavetaExportar({ pronto, onCsv, onImprimir, onMetodo }: ExportarProps) {
  return <section data-testid="analise-exportar" aria-label="Exportar" className="space-y-3">
    <p className="text-xs leading-5 text-slate-600">O CSV traz todos os itens do resultado (com ou sem a régua), com os valores em precisão integral,
      a avaliabilidade e o motivo de cada um. Imprimir / PDF leva o título, o gráfico, as legendas e os detalhes.</p>
    <div className="flex flex-col gap-2">
      <button type="button" data-testid="analise-exportar-csv" disabled={!pronto} onClick={onCsv} className="analise-botao-primario justify-start">
        <Download size={15} aria-hidden="true"/>Baixar CSV (precisão integral)</button>
      <button type="button" data-testid="analise-exportar-imprimir" disabled={!pronto} onClick={onImprimir} className="analise-botao-secundario justify-start">
        <Printer size={15} aria-hidden="true"/>Imprimir / PDF</button>
      <button type="button" data-testid="analise-exportar-metodo" disabled={!pronto} onClick={onMetodo} className="analise-botao-secundario justify-start">
        <FileText size={15} aria-hidden="true"/>Baixar método e parâmetros (TXT)</button>
    </div>
    <p className="text-[11px] leading-4 text-slate-600">A sessão é temporária: para guardar a análise, exporte agora ou use o Histórico.</p>
  </section>;
}

