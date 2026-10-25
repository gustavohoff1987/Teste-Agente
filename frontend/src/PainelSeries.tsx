import { useMemo, useState } from "react";
import type { PainelIndicador, PainelItem } from "./painelApi";
import {
  INDICADORES, barrasDeVelocidade, dominioDasSeries, exibirCompetencia, formatarNumero, larguraDoTexto, marcas, montarSeries,
  paletaDoGrafico, posicionarRotulos, textoDaMarca, umA, type RotulosTerritoriais,
} from "./painelModel";
import { useLargura } from "./PainelChart";
import { useEsquemaDeCor } from "./useEsquemaDeCor";

// Visão Série temporal da Análise de Tendência (24/10/2026, no lugar da visão Séries): a série histórica de cada unidade escolhida,
// no intervalo pedido (de início, toda a extensão da base, do primeiro ao último período que ela tem), com X = competência, no tempo
// real entre elas, e Y = indicador. Até 12 unidades; com mais de 4, pequenos múltiplos na mesma escala. Um ponto por valor
// observado do motor; lacunas não são ligadas, não há linha ajustada (Parte 13) nem classificação: a série não usa a tendência
// (CAP-TEN-01), e as linhas ficam na cor única do gráfico. Um conjunto com membros diferentes no intervalo fica só com os pontos,
// sem linha (RQ-REP-15). Superfície, tintas, grade e eixo vêm da paleta do esquema de cor do aparelho (modo escuro, 23/10/2026).
export const MAX_SERIES = 12;

type Props = { itens: PainelItem[]; competencias: string[]; indicador: PainelIndicador; rotulos: RotulosTerritoriais };

const observacoesDaSerie = (item: PainelItem) => item.serie?.observacoes ?? [];

export default function PainelSeries({ itens, competencias, indicador, rotulos }: Props) {
  const [ref, largura] = useLargura(800);
  const paleta = paletaDoGrafico(useEsquemaDeCor());
  const [foco, setFoco] = useState<string | null>(null);
  const [ponto, setPonto] = useState<{ serie: string; competencia: string } | null>(null);
  const mostrados = itens.slice(0, MAX_SERIES);
  const dominio = useMemo(() => dominioDasSeries(mostrados, observacoesDaSerie), [mostrados]);
  const multiplos = mostrados.length > 4;
  const especie = INDICADORES[indicador];
  const focoEfetivo = mostrados.some(item => item.id === foco) ? foco : null;
  const colunas = multiplos ? (largura >= 900 ? 3 : largura >= 560 ? 2 : 1) : 1;
  const larguraGrafico = multiplos ? Math.floor((largura - (colunas - 1) * 12) / colunas) : largura;
  const altura = multiplos ? 180 : Math.round(Math.min(440, Math.max(280, largura * 0.42)));

  const desenhar = (grupo: PainelItem[], larguraSvg: number, alturaSvg: number, titulo: string | null) => {
    const esquerda = 52, direita = multiplos ? 12 : 150, topo = 12, base = alturaSvg - 34;
    const { series, marcasX } = montarSeries({ itens: grupo, janela: competencias, dominio, x0: esquerda + 6, x1: larguraSvg - direita, y0: topo + 6,
      y1: base - 6, paleta, observacoesDe: observacoesDaSerie, corUnica: paleta.bolha, ligar: item => item.serie?.comparavel !== false });
    const y = (valor: number) => base - 6 - (base - topo - 12) * ((valor - dominio[0]) / ((dominio[1] - dominio[0]) || 1));
    const ticksY = marcas(dominio, "linear", multiplos ? 3 : 5);
    const passo = Math.max(1, Math.ceil(marcasX.length / (multiplos ? 3 : 8)));
    const fins = series.filter(serie => serie.fim);
    const rotulosFim = posicionarRotulos(fins.map(serie => ({ id: serie.id, x: serie.fim!.x, y: serie.fim!.y, r: 4,
      largura: larguraDoTexto(serie.rotulo, 11) })), larguraSvg - 2, 14);
    return <svg width="100%" height={alturaSvg} viewBox={`0 0 ${larguraSvg} ${alturaSvg}`} role="img" className="analise-svg"
      aria-label={(titulo ? titulo + ": " : "") + "série temporal de " + especie.rotulo.toLowerCase() + ", " + grupo.length + " " +
        (grupo.length === 1 ? rotulos.unidade.singular : rotulos.unidade.plural) + ", de " + exibirCompetencia(competencias[0]) + " a " +
        exibirCompetencia(competencias[competencias.length - 1])}>
      {ticksY.map(valor => <line key={"g" + valor} x1={esquerda} x2={larguraSvg - direita} y1={y(valor)} y2={y(valor)} stroke={paleta.grade} strokeWidth={1}/>)}
      <line x1={esquerda} x2={esquerda} y1={topo} y2={base} stroke={paleta.eixo} strokeWidth={1}/>
      <line x1={esquerda} x2={larguraSvg - direita} y1={base} y2={base} stroke={paleta.eixo} strokeWidth={1}/>
      {ticksY.map(valor => <text key={"t" + valor} x={esquerda - 6} y={y(valor) + 4} textAnchor="end" className="analise-marca-texto">{textoDaMarca(valor)}</text>)}
      {marcasX.filter((_, indice) => indice % passo === 0 || indice === marcasX.length - 1).map(marca =>
        <text key={marca.competencia} x={marca.x} y={base + 16} textAnchor="middle" className="analise-marca-texto">{exibirCompetencia(marca.competencia)}</text>)}
      {series.map(serie => <g key={serie.id} data-testid="analise-serie" data-id={serie.id} data-comparavel={serie.ligada ? "true" : "false"}
        data-pontos={serie.pontos.length} opacity={focoEfetivo && focoEfetivo !== serie.id && !multiplos ? 0.3 : 1}>
        {serie.caminhos.map((d, indice) => <path key={indice} d={d} fill="none" stroke={serie.cor} strokeWidth={focoEfetivo === serie.id ? 3 : 2}
          strokeLinejoin="round" strokeLinecap="round"/>)}
        {serie.pontos.map(item => <circle key={item.competencia} cx={item.x} cy={item.y} r={3.5} fill={serie.cor} stroke={paleta.superficie} strokeWidth={1.5}
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
        const texto = serie.rotulo + " · " + formatarNumero(alvo.valor, especie.contagem) + " · " + exibirCompetencia(alvo.competencia);
        const larguraTexto = larguraDoTexto(texto, 11) + 8;
        const x = Math.min(larguraSvg - larguraTexto - 2, Math.max(2, alvo.x - larguraTexto / 2));
        return <g key="dica" pointerEvents="none" data-testid="analise-serie-dica">
          <rect x={x} y={Math.max(0, alvo.y - 28)} width={larguraTexto} height={20} rx={6} fill={paleta.dica} stroke={paleta.eixo}/>
          <text x={x + larguraTexto / 2} y={Math.max(0, alvo.y - 28) + 14} textAnchor="middle" className="analise-marca-texto">{texto}</text>
        </g>;
      })}
    </svg>;
  };

  const naoComparaveis = mostrados.filter(item => item.serie?.comparavel === false);
  return <section ref={ref} data-testid="analise-series" data-competencias={competencias.length} aria-label="Série temporal" className="space-y-3">
    {itens.length > MAX_SERIES && <p className="text-xs text-amber-900">Mostrando {MAX_SERIES} de {itens.length}: a Série temporal
      desenha até {MAX_SERIES} {rotulos.unidade.plural}. Desmarque alguns para trocar.</p>}
    {multiplos ? <div className="analise-multiplos" style={{ gridTemplateColumns: `repeat(${colunas}, minmax(0, 1fr))` }}>
      {mostrados.map(item => <figure key={item.id} className="m-0 min-w-0 rounded-xl border border-line bg-white p-2">
        <figcaption className="px-1 text-xs"><span className="block truncate font-semibold text-ink" title={item.rotulo}>{item.rotulo}</span></figcaption>
        {desenhar([item], larguraGrafico - 16, altura, item.rotulo)}
      </figure>)}
    </div> : <figure className="m-0">{desenhar(mostrados, largura, altura, null)}</figure>}
    {!multiplos && mostrados.length > 1 && <div className="flex flex-wrap gap-1.5" role="group" aria-label="Destacar uma linha">
      {mostrados.map(item => <button key={item.id} type="button" aria-pressed={focoEfetivo === item.id}
        onClick={() => setFoco(atual => atual === item.id ? null : item.id)} className="analise-chip">{item.rotulo}</button>)}
    </div>}
    {naoComparaveis.length > 0 && <p data-testid="analise-serie-nao-comparavel" className="text-xs text-amber-900">
      {naoComparaveis.map(item => item.rotulo).join(", ")}: {naoComparaveis[0].serie?.motivo}</p>}
  </section>;
}

/** A explicação da Série temporal, no painel ao lado do desenho (24/10/2026). */
export function LegendaDaSerie({ indicador, rotulos }: { indicador: PainelIndicador; rotulos: RotulosTerritoriais }) {
  return <div data-testid="analise-serie-legenda" className="analise-explicacao-bloco">
    <p>Cada linha é {umA(rotulos.unidade)}: um ponto para cada competência com valor, no tempo real entre elas. Eixo vertical:{" "}
      {INDICADORES[indicador].eixo.toLowerCase()}.</p>
    <p>Competência sem valor fica sem ponto, e as lacunas não são ligadas. Não há classificação nem linha ajustada: a série mostra os
      valores como foram observados.</p>
  </div>;
}

/** As velocidades da tendência de uma unidade (CAP-TEN-01, do motor): a variação absoluta por unidade de tempo entre períodos
 * vizinhos, em barras. Ficam no painel ao lado do quadro de setas, para a linha escolhida (24/10/2026; antes, na visão Séries). */
export function Velocidades({ item, indicador, unidadeTempo }: { item: PainelItem; indicador: PainelIndicador; unidadeTempo: string | null }) {
  const paleta = paletaDoGrafico(useEsquemaDeCor());
  const especie = INDICADORES[indicador];
  const velocidades = item.tendencia?.velocidades ?? [];
  const largura = 280;
  const barras = barrasDeVelocidade(velocidades.map(v => v.valor), largura, 80);
  const porTempo = "por " + (unidadeTempo || "mês");
  return <section data-testid="analise-velocidades" data-id={item.id} aria-label={"Velocidades de " + item.rotulo} className="analise-explicacao-bloco">
    <p className="font-semibold text-ink">Velocidades de {item.rotulo} · {item.tendencia?.rotulo ?? "Não avaliável"}</p>
    <p>Variação absoluta {porTempo} entre períodos vizinhos. Barras do mesmo lado e crescendo indicam aceleração; diminuindo,
      desaceleração; trocando de lado, mudança de direção.</p>
    {velocidades.length ? <>
      <svg width={largura} height={80} className="block max-w-full" aria-hidden="true">
        <line x1={0} x2={largura} y1={barras.base} y2={barras.base} stroke={paleta.eixo} strokeWidth={1}/>
        {barras.barras.map((barra, indice) => <rect key={indice} x={barra.x} y={barra.y} width={barra.largura} height={barra.altura} rx={2}
          fill={barra.sinal === 0 ? paleta.tinta2 : paleta.tendencia[item.tendencia?.familia ?? "NENHUMA"]}/>)}
      </svg>
      <ol className="grid gap-0.5">
        {velocidades.map(v => <li key={v.de + v.ate} data-testid="analise-velocidade" data-valor={v.valor}>
          <span className="font-semibold tabular-nums text-ink">{v.valor > 0 ? "+" : ""}{formatarNumero(v.valor, false)}</span>{" "}
          {especie.unidade} {porTempo} · {exibirCompetencia(v.de)} a {exibirCompetencia(v.ate)}</li>)}
      </ol>
    </> : <p>Sem velocidades: a série não tem períodos vizinhos com valor{item.tendencia?.motivo ? " (" + item.tendencia.motivo + ")" : ""}.</p>}
  </section>;
}
