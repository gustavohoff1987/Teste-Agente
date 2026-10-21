import { useEffect, useMemo, useRef, useState, type DragEvent, type KeyboardEvent, type RefObject } from "react";
import type { PainelIndicador, PainelItem, PainelResposta } from "./painelApi";
import {
  COR_NAO_AVALIAVEL, INDICADORES, caudaDoCometa, exibirCompetencia, formatarNumero, formatarVariacao, larguraDoTexto, legendaDeTamanhos,
  limiteDaVariacao, montarDica, montarGrafico, posicionarRotulos, type BolhaDesenho, type Escala, type Vista,
} from "./painelModel";
import { TIPO_ARRASTO } from "./PainelBase";

// Gráfico de bolhas do painel integrado. Só desenha o que o modelo posicionou a partir da resposta do motor: valores, variações e
// distâncias vêm de /api/painel. Marcas finas com anel de 2 px na cor da superfície, alvo de pelo menos 24 px, dica ao passar o
// mouse e ao focar, rótulos diretos seletivos (texto em tinta, nunca na cor da série) e navegação pelas setas entre as bolhas.

const SUPERFICIE = "#fcfcfb", TINTA = "#0b0b0b", TINTA_2 = "#52514e", GRADE = "#e1e0d9", EIXO = "#c9c8c0";

/** Largura do contêiner em pixels (ignora larguras nulas de um painel oculto). */
function useLargura(inicial = 900): [RefObject<HTMLElement>, number] {
  const ref = useRef<HTMLElement>(null);
  const [largura, setLargura] = useState(inicial);
  useEffect(() => {
    const elemento = ref.current;
    if (!elemento) return;
    const medir = () => { if (elemento.clientWidth > 0) setLargura(elemento.clientWidth); };
    medir();
    if (typeof ResizeObserver === "undefined") return;
    const observador = new ResizeObserver(medir);
    observador.observe(elemento);
    return () => observador.disconnect();
  }, []);
  return [ref, largura];
}

export type FaseAnimacao = "parado" | "preparar" | "tocar";
type Props = {
  resposta: PainelResposta;
  /** Itens desenháveis e dentro do corte da régua, na ordem neutra. */
  itens: PainelItem[];
  indicador: PainelIndicador;
  escala: Escala;
  distancia: boolean;
  crescimento: boolean;
  vista: Vista;
  fase: FaseAnimacao;
  selecionados: string[];
  limiares: number[];
  nomes: Map<string, string>;
  carregando: boolean;
  rotuloDistancia: string;
  onAlternar: (id: string) => void;
  onSoltar: (id: string) => void;
};

export default function PainelChart(p: Props) {
  const [ref, largura] = useLargura();
  const [ativo, setAtivo] = useState<string | null>(null);
  const [foco, setFoco] = useState<string | null>(null);
  const [soltando, setSoltando] = useState(false);
  const elementos = useRef(new Map<string, SVGGElement>());
  const limite = useMemo(() => limiteDaVariacao(p.resposta, p.indicador, p.itens), [p.resposta, p.indicador, p.itens]);
  const grafico = useMemo(() => montarGrafico({ itens: p.itens, dominios: p.resposta.dominios, indicador: p.indicador, escala: p.escala,
    distancia: p.distancia, crescimento: p.crescimento, vista: p.vista, largura, limiteVariacao: limite, rotuloDistancia: p.rotuloDistancia }),
  [p.itens, p.resposta.dominios, p.indicador, p.escala, p.distancia, p.crescimento, p.vista, largura, limite, p.rotuloDistancia]);
  const selecionados = useMemo(() => new Set(p.selecionados), [p.selecionados]);
  const destaque = p.selecionados.length > 0;
  const competenciaInicial = p.resposta.competencia_inicial || null;

  // Navegação pelo teclado: uma parada de tabulação no gráfico; as setas percorrem as bolhas da esquerda para a direita.
  const navegaveis = useMemo(() => grafico.bolhas.filter(bolha => bolha.visivel)
    .sort((a, b) => a.x - b.x || a.y - b.y || a.id.localeCompare(b.id, "pt-BR", { numeric: true })), [grafico]);
  const focoEfetivo = navegaveis.some(bolha => bolha.id === foco) ? foco : navegaveis[0]?.id ?? null;

  // Rótulos diretos seletivos: selecionados, conjuntos, membros da referência e a bolha sob o mouse ou em foco.
  const textoDoRotulo = (bolha: BolhaDesenho) => {
    const nome = bolha.item.rotulo + (bolha.tipo === "conjunto" ? " (soma)" : "");
    if (p.vista === "inicial" && p.crescimento) return nome + " · " + exibirCompetencia(competenciaInicial);
    if (p.crescimento) return nome + " · " + formatarVariacao(bolha.variacao);
    if (bolha.referencia) return nome + " · referência";
    return nome + " · " + formatarNumero(bolha.valor, INDICADORES[p.indicador].contagem, p.limiares);
  };
  const rotulados = grafico.bolhas.filter(bolha => bolha.visivel && (selecionados.has(bolha.id) || bolha.tipo === "conjunto" ||
    bolha.referencia || bolha.id === ativo));
  const rotulos = posicionarRotulos(rotulados.map(bolha => ({ id: bolha.id, x: bolha.x, y: bolha.y, r: bolha.r,
    largura: larguraDoTexto(textoDoRotulo(bolha)) })), grafico.largura - 4);
  // Ordem de desenho estável: as mais populosas atrás. Não depende do mouse, do foco, do destaque nem da vista, para que nenhum
  // nó mude de lugar ao passar o mouse (mover o nó reiniciaria as transições e o rastro). Os rótulos ficam numa camada própria,
  // por cima de todas as bolhas.
  const ordem = useMemo(() => [...grafico.bolhas].sort((a, b) => (b.item.populacao ?? -1) - (a.item.populacao ?? -1) ||
    a.id.localeCompare(b.id, "pt-BR", { numeric: true })), [grafico]);
  const opacidadeDe = (bolha: BolhaDesenho) => !bolha.visivel ? 0
    : destaque && !selecionados.has(bolha.id) && bolha.id !== ativo ? 0.22 : 1;
  const bolhaAtiva = ativo ? grafico.bolhas.find(bolha => bolha.id === ativo && bolha.visivel) : undefined;
  const dica = bolhaAtiva ? montarDica(bolhaAtiva.item, { indicador: p.indicador, competencia: p.resposta.competencia,
    competenciaInicial, distancia: p.distancia, crescimento: p.crescimento, nomes: p.nomes, limiares: p.limiares }) : null;

  function teclado(event: KeyboardEvent<SVGGElement>, id: string) {
    const indice = navegaveis.findIndex(bolha => bolha.id === id);
    let alvo: string | null = null;
    if (event.key === "ArrowRight" || event.key === "ArrowDown") alvo = navegaveis[Math.min(navegaveis.length - 1, indice + 1)]?.id ?? null;
    else if (event.key === "ArrowLeft" || event.key === "ArrowUp") alvo = navegaveis[Math.max(0, indice - 1)]?.id ?? null;
    else if (event.key === "Home") alvo = navegaveis[0]?.id ?? null;
    else if (event.key === "End") alvo = navegaveis[navegaveis.length - 1]?.id ?? null;
    else if (event.key === "Enter" || event.key === " ") { event.preventDefault(); p.onAlternar(id); return; }
    else if (event.key === "Escape") { setAtivo(null); return; }
    if (!alvo) return;
    event.preventDefault();
    setFoco(alvo);
    elementos.current.get(alvo)?.focus();
  }

  function aceita(event: DragEvent<HTMLElement>): boolean {
    return Array.from(event.dataTransfer?.types || []).includes(TIPO_ARRASTO);
  }
  function soltar(event: DragEvent<HTMLElement>) {
    setSoltando(false);
    const id = event.dataTransfer?.getData(TIPO_ARRASTO) || event.dataTransfer?.getData("text/plain") || "";
    if (!id.startsWith("code:")) return;
    event.preventDefault();
    p.onSoltar(id);
  }

  const especie = INDICADORES[p.indicador];
  const descricao = (bolha: BolhaDesenho) => {
    const partes = [bolha.item.rotulo, especie.rotulo + " " + formatarNumero(bolha.valor, especie.contagem, p.limiares) + " " + especie.unidade];
    if (bolha.item.populacao !== null && bolha.item.populacao !== undefined) partes.push("população " + formatarNumero(bolha.item.populacao, true));
    if (p.distancia && bolha.item.distancia_km !== null && bolha.item.distancia_km !== undefined) partes.push("distância " + formatarNumero(bolha.item.distancia_km) + " km");
    if (p.crescimento) partes.push("variação " + formatarVariacao(bolha.variacao));
    if (bolha.tipo === "conjunto") partes.push("soma das contagens dos componentes");
    return partes.join("; ");
  };
  const larguraDica = Math.min(260, grafico.largura - 16);
  const posicaoDica = bolhaAtiva ? {
    left: Math.max(4, bolhaAtiva.x + bolhaAtiva.r + 12 + larguraDica > grafico.largura ? bolhaAtiva.x - bolhaAtiva.r - 12 - larguraDica : bolhaAtiva.x + bolhaAtiva.r + 12),
    top: Math.max(4, Math.min(grafico.altura - 120, bolhaAtiva.y - 16)),
  } : null;
  const classe = "painel-svg" + (p.fase === "preparar" ? " painel-sem-transicao" : "") + (p.fase === "tocar" ? " painel-reproduzindo" : "");
  const eixoX = grafico.eixoX, eixoY = grafico.eixoY;
  // Legenda dos símbolos, só com o que está desenhado.
  const temConjunto = grafico.bolhas.some(bolha => bolha.tipo === "conjunto"), temReferencia = grafico.bolhas.some(bolha => bolha.referencia);
  const simbolos = [temConjunto ? "anel escuro: conjunto (soma das contagens dos componentes, com possível dupla contagem)" : "",
    temReferencia ? "mira: membro da referência (distância 0)" : "",
    temConjunto && p.distancia ? "traço horizontal: do membro mais próximo ao mais distante do conjunto" : "",
    p.crescimento ? "rastro: da competência inicial (círculo vazado) até a atual; bolha vazada tracejada: variação não avaliável" : ""]
    .filter(Boolean).join("; ").replace(/^./, letra => letra.toUpperCase()) + (temConjunto || temReferencia || p.crescimento ? "." : "");
  const meioX = (grafico.esquerda + grafico.largura - grafico.direita) / 2;

  return <figure ref={ref} data-testid="painel-chart" className={"painel-grafico relative m-0" + (p.carregando ? " painel-carregando" : "")}
    aria-busy={p.carregando || undefined} onDragOver={event => { if (!aceita(event)) return; event.preventDefault(); event.dataTransfer.dropEffect = "copy"; setSoltando(true); }}
    onDragLeave={event => { if (!event.currentTarget.contains(event.relatedTarget as Node | null)) setSoltando(false); }} onDrop={soltar}>
    <svg viewBox={`0 0 ${grafico.largura} ${grafico.altura}`} width="100%" height={grafico.altura} role="group" className={classe}
      aria-label={"Bolhas do painel: " + (eixoY ? "distância até a referência no eixo horizontal e " + especie.rotulo.toLowerCase() + " no vertical"
        : especie.rotulo.toLowerCase() + " no eixo horizontal; a altura é só arranjo visual") + ". Tamanho: população. Use as setas para percorrer as bolhas e Enter para destacar."}>
      {/* Grade recessiva: linhas finas, sólidas, um tom acima da superfície. */}
      {eixoX.marcas.map(marca => <line key={"gx" + marca.valor} x1={marca.pos} x2={marca.pos} y1={grafico.topo} y2={grafico.base} stroke={GRADE} strokeWidth={1}/>)}
      {eixoY?.marcas.map(marca => <line key={"gy" + marca.valor} x1={grafico.esquerda} x2={grafico.largura - grafico.direita} y1={marca.pos} y2={marca.pos}
        stroke={GRADE} strokeWidth={1}/>)}
      <g data-testid="painel-axis-x" data-eixo={eixoX.tipo} data-escala={eixoX.escala} data-dominio={eixoX.dominio.join(",")} aria-hidden="true">
        <line x1={grafico.esquerda} x2={grafico.largura - grafico.direita} y1={grafico.base} y2={grafico.base} stroke={EIXO} strokeWidth={1}/>
        {eixoX.marcas.map(marca => <text key={marca.valor} x={marca.pos} y={grafico.base + 16} textAnchor="middle" className="painel-marca-texto">{marca.texto}</text>)}
        <text x={meioX} y={grafico.base + 38} textAnchor="middle" className="painel-eixo-titulo">{eixoX.rotulo}{eixoX.escala === "logaritmica" ? " · escala logarítmica" : ""}</text>
      </g>
      {eixoY && <g data-testid="painel-axis-y" data-eixo={eixoY.tipo} data-escala={eixoY.escala} data-dominio={eixoY.dominio.join(",")} aria-hidden="true">
        <line x1={grafico.esquerda} x2={grafico.esquerda} y1={grafico.topo} y2={grafico.base} stroke={EIXO} strokeWidth={1}/>
        {eixoY.marcas.map(marca => <text key={marca.valor} x={grafico.esquerda - 6} y={marca.pos + 4} textAnchor="end" className="painel-marca-texto">{marca.texto}</text>)}
        <text transform={`translate(14 ${(grafico.topo + grafico.base) / 2}) rotate(-90)`} textAnchor="middle" className="painel-eixo-titulo">
          {eixoY.rotulo}{eixoY.escala === "logaritmica" ? " · log" : ""}</text>
      </g>}
      {ordem.map(bolha => {
        const selecionado = selecionados.has(bolha.id);
        const opacidade = opacidadeDe(bolha);
        const gradiente = "painel-cometa-" + bolha.id.replace(/[^a-zA-Z0-9_-]/g, "_");
        return <g key={bolha.id} ref={elemento => { if (elemento) elementos.current.set(bolha.id, elemento); else elementos.current.delete(bolha.id); }}
          className="painel-bubble" data-testid="painel-bubble" data-id={bolha.id} data-tipo={bolha.tipo} data-valor={String(bolha.valor)}
          data-populacao={bolha.item.populacao ?? ""} data-distancia={p.distancia ? String(bolha.item.distancia_km ?? "") : undefined}
          data-variacao={p.crescimento && bolha.variacao !== null ? String(bolha.variacao) : undefined}
          data-referencia={bolha.referencia ? "true" : undefined} data-selecionado={selecionado ? "true" : undefined}
          data-visivel={bolha.visivel ? "true" : "false"}
          style={{ transform: `translate(${bolha.x}px, ${bolha.y}px)`, opacity: opacidade, pointerEvents: bolha.visivel ? undefined : "none" }}
          role="button" tabIndex={bolha.visivel && focoEfetivo === bolha.id ? 0 : -1} aria-pressed={selecionado} aria-label={descricao(bolha)}
          aria-hidden={bolha.visivel ? undefined : true} aria-describedby={ativo === bolha.id ? "painel-dica" : undefined}
          onPointerEnter={() => setAtivo(bolha.id)} onPointerLeave={() => setAtivo(atual => atual === bolha.id ? null : atual)}
          onFocus={() => { setFoco(bolha.id); setAtivo(bolha.id); }} onBlur={() => setAtivo(atual => atual === bolha.id ? null : atual)}
          onClick={() => p.onAlternar(bolha.id)} onKeyDown={event => teclado(event, bolha.id)}>
          {bolha.rastro && <g key={bolha.rastro.dx.toFixed(1) + ":" + bolha.rastro.dy.toFixed(1)} className="painel-rastro" data-testid="painel-rastro" aria-hidden="true">
            <defs>
              <linearGradient id={gradiente} gradientUnits="userSpaceOnUse" x1={bolha.rastro.dx} y1={bolha.rastro.dy} x2={0} y2={0}>
                <stop offset="0" stopColor={bolha.cor} stopOpacity={0}/>
                <stop offset="1" stopColor={bolha.cor} stopOpacity={0.6}/>
              </linearGradient>
            </defs>
            <polygon points={caudaDoCometa(bolha.rastro.dx, bolha.rastro.dy, bolha.r)} fill={`url(#${gradiente})`}/>
            <circle cx={bolha.rastro.dx} cy={bolha.rastro.dy} r={3.5} fill={SUPERFICIE} stroke={bolha.cor} strokeWidth={1.5}/>
          </g>}
          {bolha.faixa && <g aria-hidden="true">
            <line x1={0} x2={bolha.faixa.dx} y1={0} y2={0} stroke={TINTA_2} strokeWidth={1.5} strokeLinecap="round"/>
            <line x1={bolha.faixa.dx} x2={bolha.faixa.dx} y1={-5} y2={5} stroke={TINTA_2} strokeWidth={1.5} strokeLinecap="round"/>
          </g>}
          <circle className="painel-marca" r={bolha.r} fill={bolha.cor} fillOpacity={bolha.vazada ? 1 : 0.88}
            stroke={bolha.vazada ? COR_NAO_AVALIAVEL : SUPERFICIE} strokeWidth={bolha.vazada ? 1.5 : 2} strokeDasharray={bolha.vazada ? "3 2" : undefined}/>
          {bolha.tipo === "conjunto" && <circle r={bolha.r + 4} fill="none" stroke={TINTA} strokeOpacity={0.7} strokeWidth={1.25}/>}
          {bolha.referencia && <path d={`M${-(bolha.r + 9)} 0H${-(bolha.r + 3)}M${bolha.r + 3} 0H${bolha.r + 9}M0 ${-(bolha.r + 9)}V${-(bolha.r + 3)}M0 ${bolha.r + 3}V${bolha.r + 9}`}
            stroke={TINTA} strokeWidth={1.5} strokeLinecap="round"/>}
          {(selecionado || ativo === bolha.id) && <circle r={bolha.r + 2} fill="none" stroke={TINTA} strokeWidth={2}/>}
          <circle className="painel-alvo" r={Math.max(bolha.r + 2, 12)} fill="transparent"/>
        </g>;
      })}
      {/* Rótulos diretos seletivos, por cima das bolhas; acompanham a bolha (mesma transição) e não recebem o mouse. */}
      <g className="painel-rotulos" aria-hidden="true" pointerEvents="none">
        {ordem.filter(bolha => rotulos.has(bolha.id)).map(bolha => {
          const rotulo = rotulos.get(bolha.id)!;
          return <g key={bolha.id} className="painel-rotulo-grupo" data-id={bolha.id}
            style={{ transform: `translate(${bolha.x}px, ${bolha.y}px)`, opacity: opacidadeDe(bolha) }}>
            <text x={rotulo.dx} y={rotulo.dy + 4} textAnchor={rotulo.ancora} className="painel-rotulo">{textoDoRotulo(bolha)}</text>
          </g>;
        })}
      </g>
    </svg>
    {!grafico.bolhas.length && <p role="status" className="pointer-events-none absolute inset-x-0 top-1/3 px-6 text-center text-sm text-slate-600">
      Nenhuma bolha para desenhar: os municípios ficaram fora do corte da régua ou não têm valor avaliável (veja a lista de não avaliáveis).</p>}
    {dica && posicaoDica && <div role="tooltip" id="painel-dica" data-testid="painel-tooltip" className="painel-dica"
      style={{ left: posicaoDica.left, top: posicaoDica.top, width: larguraDica }}>
      <strong className="block text-sm text-ink">{dica.titulo}</strong>
      <span className="block text-[11px] text-slate-600">{dica.subtitulo}</span>
      <dl className="mt-1.5 space-y-0.5">
        {dica.linhas.map(linha => <div key={linha.rotulo} className="flex flex-col">
          <dt className="sr-only">{linha.rotulo}</dt>
          <dd className="text-xs"><span className="font-semibold text-ink">{linha.valor}</span> <span className="text-slate-500">· {linha.rotulo}</span></dd>
        </div>)}
      </dl>
      {dica.notas.map(nota => <p key={nota} className="mt-1 text-[11px] leading-4 text-slate-600">{nota}</p>)}
    </div>}
    {soltando && <div className="painel-soltar" aria-hidden="true">Solte para acrescentar o município ao painel</div>}
    <figcaption className="painel-legenda">
      <LegendaDeTamanho maxima={grafico.populacaoMaxima} raioMax={grafico.raioMax}/>
      <div className="min-w-0 max-w-xl space-y-1">
        {!eixoY && <p data-testid="painel-arranjo-nota">Eixo único de {especie.rotulo.toLowerCase()}: a altura das bolhas é só arranjo visual, para
          que não se sobreponham; o valor está no eixo horizontal.</p>}
        {eixoY && <p>Horizontal: distância até a referência, do motor; vertical: {especie.rotulo.toLowerCase()}. Sem reta de tendência nem
          correlação: cada bolha é só um par de valores.</p>}
        {simbolos && <p data-testid="painel-simbolos">{simbolos}</p>}
      </div>
    </figcaption>
  </figure>;
}

/** Legenda de tamanho: três populações de referência com o mesmo raio do gráfico (área proporcional à população). */
function LegendaDeTamanho({ maxima, raioMax }: { maxima: number; raioMax: number }) {
  const tamanhos = legendaDeTamanhos(maxima, raioMax);
  if (!tamanhos.length) return null;
  const maior = Math.max(...tamanhos.map(item => item.raio));
  const base = Math.ceil(2 * maior + 6), larguraTexto = 78;
  // Círculos alinhados embaixo; cada rótulo no topo do seu círculo, afastado do anterior quando os topos ficam próximos.
  let anterior = -Infinity;
  const posicoes = tamanhos.map(item => {
    const cy = base - 2 - item.raio, topo = cy - item.raio, y = Math.max(topo + 4, anterior + 12);
    anterior = y;
    return { item, cy, topo, y };
  });
  const altura = Math.max(base, Math.ceil(anterior + 4));
  return <div data-testid="painel-size-legend" aria-label={"Tamanho: população. Referências: " + tamanhos.map(item => item.texto).join(", ")}
    className="flex items-end gap-2">
    <svg width={2 * maior + 10 + larguraTexto} height={altura} aria-hidden="true" className="overflow-visible">
      {posicoes.map(({ item, cy, topo, y }) => <g key={item.valor} data-testid="painel-size-item" data-valor={item.valor} data-raio={item.raio.toFixed(2)}>
        <circle cx={maior + 2} cy={cy} r={item.raio} fill="none" stroke={TINTA_2} strokeWidth={1}/>
        <line x1={maior + 2} x2={2 * maior + 8} y1={topo} y2={y - 4} stroke={EIXO} strokeWidth={1}/>
        <text x={2 * maior + 11} y={y} className="painel-marca-texto">{item.texto}</text>
      </g>)}
    </svg>
    <span className="max-w-[9rem] leading-4">Área proporcional à população; as muito pequenas ficam no tamanho mínimo visível.</span>
  </div>;
}
