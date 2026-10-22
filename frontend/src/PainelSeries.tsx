import { useMemo, useState } from "react";
import type { PainelIndicador, PainelItem } from "./painelApi";
import {
  CORES_TENDENCIA, INDICADORES, NOMES_FAMILIA_TENDENCIA, barrasDeVelocidade, dominioDasSeries, exibirCompetencia, formatarNumero,
  larguraDoTexto, marcas, montarSeries, posicionarRotulos, textoDaMarca, type RotulosTerritoriais,
} from "./painelModel";
import { useLargura } from "./PainelChart";

// Visão Séries da tendência: linhas por competência (X = competência, no tempo real entre elas; Y = indicador), uma por
// unidade, até 12. Com mais de 4, pequenos múltiplos na mesma escala. Um ponto por observação do motor; lacunas não são
// ligadas e não há linha ajustada (Parte 13). As velocidades da unidade em foco vêm do motor (CAP-TEN-01): barras crescendo
// mostram aceleração; diminuindo, desaceleração. A cor da linha é a família da classe, a mesma da visão Classes.

const SUPERFICIE = "#fcfcfb", TINTA_2 = "#52514e", GRADE = "#e1e0d9", EIXO = "#c3c2b7";
export const MAX_SERIES = 12;

type Props = { itens: PainelItem[]; janela: string[]; indicador: PainelIndicador; rotulos: RotulosTerritoriais; unidadeTempo: string | null };

export default function PainelSeries({ itens, janela, indicador, rotulos, unidadeTempo }: Props) {
  const [ref, largura] = useLargura(800);
  const [foco, setFoco] = useState<string | null>(null);
  const [ponto, setPonto] = useState<{ serie: string; competencia: string } | null>(null);
  const mostrados = itens.slice(0, MAX_SERIES);
  const dominio = useMemo(() => dominioDasSeries(mostrados), [mostrados]);
  const multiplos = mostrados.length > 4;
  const especie = INDICADORES[indicador];
  const focoEfetivo = mostrados.some(item => item.id === foco) ? foco : mostrados[0]?.id ?? null;
  const itemFoco = mostrados.find(item => item.id === focoEfetivo) || null;
  const colunas = multiplos ? (largura >= 900 ? 3 : largura >= 560 ? 2 : 1) : 1;
  const larguraGrafico = multiplos ? Math.floor((largura - (colunas - 1) * 12) / colunas) : largura;
  const altura = multiplos ? 180 : Math.round(Math.min(420, Math.max(260, largura * 0.42)));

  const desenhar = (grupo: PainelItem[], larguraSvg: number, alturaSvg: number, titulo: string | null) => {
    const esquerda = 52, direita = multiplos ? 12 : 150, topo = 12, base = alturaSvg - 34;
    const { series, marcasX } = montarSeries({ itens: grupo, janela, dominio, x0: esquerda + 6, x1: larguraSvg - direita, y0: topo + 6, y1: base - 6 });
    const y = (valor: number) => base - 6 - (base - topo - 12) * ((valor - dominio[0]) / ((dominio[1] - dominio[0]) || 1));
    const ticksY = marcas(dominio, "linear", multiplos ? 3 : 5);
    const passo = Math.max(1, Math.ceil(marcasX.length / (multiplos ? 3 : 8)));
    const fins = series.filter(serie => serie.fim);
    const rotulosFim = posicionarRotulos(fins.map(serie => ({ id: serie.id, x: serie.fim!.x, y: serie.fim!.y, r: 4,
      largura: larguraDoTexto(serie.rotulo, 11) })), larguraSvg - 2, 14);
    return <svg width="100%" height={alturaSvg} viewBox={`0 0 ${larguraSvg} ${alturaSvg}`} role="img" className="analise-svg"
      aria-label={(titulo ? titulo + ": " : "") + "linhas por competência de " + especie.rotulo.toLowerCase() + ", " + grupo.length + " " +
        (grupo.length === 1 ? rotulos.unidade.singular : rotulos.unidade.plural)}>
      {ticksY.map(valor => <line key={"g" + valor} x1={esquerda} x2={larguraSvg - direita} y1={y(valor)} y2={y(valor)} stroke={GRADE} strokeWidth={1}/>)}
      <line x1={esquerda} x2={esquerda} y1={topo} y2={base} stroke={EIXO} strokeWidth={1}/>
      <line x1={esquerda} x2={larguraSvg - direita} y1={base} y2={base} stroke={EIXO} strokeWidth={1}/>
      {ticksY.map(valor => <text key={"t" + valor} x={esquerda - 6} y={y(valor) + 4} textAnchor="end" className="analise-marca-texto">{textoDaMarca(valor)}</text>)}
      {marcasX.filter((_, indice) => indice % passo === 0 || indice === marcasX.length - 1).map(marca =>
        <text key={marca.competencia} x={marca.x} y={base + 16} textAnchor="middle" className="analise-marca-texto">{exibirCompetencia(marca.competencia)}</text>)}
      {series.map(serie => <g key={serie.id} data-testid="analise-serie" data-id={serie.id} data-familia={serie.familia ?? "NAO_AVALIAVEL"}
        data-pontos={serie.pontos.length} opacity={focoEfetivo && focoEfetivo !== serie.id && !multiplos ? 0.45 : 1}>
        {serie.caminhos.map((d, indice) => <path key={indice} d={d} fill="none" stroke={serie.cor} strokeWidth={2} strokeLinejoin="round" strokeLinecap="round"/>)}
        {serie.pontos.map(item => <circle key={item.competencia} cx={item.x} cy={item.y} r={4} fill={serie.cor} stroke={SUPERFICIE} strokeWidth={2}
          data-testid="analise-serie-ponto" data-competencia={item.competencia} data-valor={item.valor}
          onPointerEnter={() => setPonto({ serie: serie.id, competencia: item.competencia })} onPointerLeave={() => setPonto(null)}/>)}
      </g>)}
      {!multiplos && fins.map(serie => {
        const rotulo = rotulosFim.get(serie.id)!;
        return <text key={"r" + serie.id} x={serie.fim!.x + rotulo.dx} y={serie.fim!.y + rotulo.dy + 4} textAnchor={rotulo.ancora}
          className="analise-rotulo analise-rotulo-pequeno">{serie.rotulo}</text>;
      })}
      {ponto && series.filter(serie => serie.id === ponto.serie).map(serie => {
        const alvo = serie.pontos.find(item => item.competencia === ponto.competencia);
        if (!alvo) return null;
        const texto = formatarNumero(alvo.valor, especie.contagem) + " · " + exibirCompetencia(alvo.competencia);
        const larguraTexto = larguraDoTexto(texto, 11) + 8;
        const x = Math.min(larguraSvg - larguraTexto - 2, Math.max(2, alvo.x - larguraTexto / 2));
        return <g key="dica" pointerEvents="none" data-testid="analise-serie-dica">
          <rect x={x} y={Math.max(0, alvo.y - 28)} width={larguraTexto} height={20} rx={6} fill="#ffffff" stroke={EIXO}/>
          <text x={x + larguraTexto / 2} y={Math.max(0, alvo.y - 28) + 14} textAnchor="middle" className="analise-marca-texto">{texto}</text>
        </g>;
      })}
    </svg>;
  };

  const velocidades = itemFoco?.tendencia?.velocidades ?? [];
  const barras = barrasDeVelocidade(velocidades.map(item => item.valor), Math.min(520, largura), 90);
  const porTempo = "por " + (unidadeTempo || "mês");
  const familiasNaTela = [...new Set(mostrados.map(item => item.tendencia?.avaliavel ? item.tendencia.familia : null))];

  return <section ref={ref} data-testid="analise-series" aria-label="Séries da tendência" className="space-y-3">
    {itens.length > MAX_SERIES && <p className="text-xs text-amber-900">Mostrando {MAX_SERIES} de {itens.length}: a visão Séries
      desenha até {MAX_SERIES} {rotulos.unidade.plural}. Desmarque alguns para trocar.</p>}
    {multiplos ? <div className="analise-multiplos" style={{ gridTemplateColumns: `repeat(${colunas}, minmax(0, 1fr))` }}>
      {mostrados.map(item => <figure key={item.id} className="m-0 min-w-0 rounded-xl border border-line bg-white p-2">
        <figcaption className="flex items-baseline justify-between gap-2 px-1 text-xs">
          <button type="button" className="analise-link truncate text-left font-semibold text-ink" aria-pressed={focoEfetivo === item.id}
            onClick={() => setFoco(item.id)} title={item.rotulo}>{item.rotulo}</button>
          <span className="shrink-0 text-[11px] text-slate-600">{item.tendencia?.rotulo ?? "Não avaliável"}</span>
        </figcaption>
        {desenhar([item], larguraGrafico - 16, altura, item.rotulo)}
      </figure>)}
    </div> : <figure className="m-0">{desenhar(mostrados, largura, altura, null)}</figure>}
    <div className="analise-legenda">
      <ul className="flex flex-wrap gap-x-4 gap-y-1" aria-label="Cor das linhas: família da classe de tendência">
        {familiasNaTela.map(familia => <li key={familia ?? "na"} className="flex items-center gap-1.5">
          <svg width="18" height="8" aria-hidden="true"><line x1="1" x2="17" y1="4" y2="4" stroke={familia ? CORES_TENDENCIA[familia] : "#898781"} strokeWidth={2}/></svg>
          {familia ? NOMES_FAMILIA_TENDENCIA[familia] : "Não avaliável"}</li>)}
      </ul>
      <p className="max-w-xl">Um ponto por competência observada; lacunas não são ligadas e não há linha ajustada. Eixo vertical: {especie.eixo.toLowerCase()}.</p>
    </div>
    {!multiplos && mostrados.length > 1 && <div className="flex flex-wrap gap-1.5" role="group" aria-label="Unidade em foco">
      {mostrados.map(item => <button key={item.id} type="button" aria-pressed={focoEfetivo === item.id} onClick={() => setFoco(item.id)}
        className="analise-chip">{item.rotulo}</button>)}
    </div>}
    {itemFoco && <section data-testid="analise-velocidades" data-id={itemFoco.id} aria-label={"Velocidades de " + itemFoco.rotulo}
      className="rounded-xl border border-line bg-white p-3">
      <h4 className="text-xs font-bold text-ink">Velocidades de {itemFoco.rotulo} · {itemFoco.tendencia?.rotulo ?? "Não avaliável"}</h4>
      <p className="mt-1 text-[11px] leading-4 text-slate-600">Variação absoluta {porTempo} entre competências vizinhas, do motor. Barras do mesmo lado
        e crescendo indicam aceleração; diminuindo, desaceleração; trocando de lado, mudança de direção.</p>
      {velocidades.length ? <>
        <svg width={Math.min(520, largura)} height={90} className="mt-2 block max-w-full" aria-hidden="true">
          <line x1={0} x2={Math.min(520, largura)} y1={barras.base} y2={barras.base} stroke={EIXO} strokeWidth={1}/>
          {barras.barras.map((barra, indice) => <rect key={indice} x={barra.x} y={barra.y} width={barra.largura} height={barra.altura} rx={2}
            fill={barra.sinal === 0 ? TINTA_2 : CORES_TENDENCIA[itemFoco.tendencia?.familia ?? "NENHUMA"]}/>)}
        </svg>
        <ol className="mt-2 grid gap-0.5 text-[11px] text-slate-700 sm:grid-cols-2">
          {velocidades.map(item => <li key={item.de + item.ate} data-testid="analise-velocidade" data-valor={item.valor}>
            <span className="font-semibold tabular-nums text-ink">{item.valor > 0 ? "+" : ""}{formatarNumero(item.valor, false)}</span>{" "}
            {especie.unidade} {porTempo} · {exibirCompetencia(item.de)} a {exibirCompetencia(item.ate)}</li>)}
        </ol>
      </> : <p className="mt-2 text-xs text-slate-600">Sem velocidades: a série não tem observações vizinhas suficientes{itemFoco.tendencia?.motivo
        ? " (" + itemFoco.tendencia.motivo + ")" : ""}.</p>}
    </section>}
  </section>;
}
