import { useRef, type KeyboardEvent, type PointerEvent } from "react";
import { RotateCcw } from "lucide-react";
import type { PainelDominio, PainelIndicador } from "./painelApi";
import { INDICADORES, ajustarValor, formatarNumero, fracao, moverCursor, valorNaFracao, type Corte, type Escala } from "./painelModel";

// Régua "acima de / abaixo de": dois cursores arrastáveis (pointer events) e com teclado (setas, Page Up/Down, Home e End) sobre o
// indicador ativo, no domínio devolvido pelo motor. Só esconde (RQ-REP-06): nada é recalculado, e os limites ficam incluídos.
// Conjuntos e membros da referência continuam à vista.

type Cursor = "minimo" | "maximo";
type Props = { indicador: PainelIndicador; dominio: PainelDominio | null; escala: Escala; corte: Corte | null;
  onCorte: (corte: Corte | null) => void; desabilitado?: boolean; plural: string };

export default function PainelRuler({ indicador, dominio, escala, corte, onCorte, desabilitado = false, plural }: Props) {
  const trilho = useRef<HTMLDivElement>(null);
  const arrasto = useRef<{ cursor: Cursor; id: number } | null>(null);
  const especie = INDICADORES[indicador];
  if (!dominio || !(dominio[1] >= dominio[0])) {
    return <section data-testid="analise-regua" data-indicador={indicador} aria-label="Régua" className="text-xs text-slate-600">
      Régua indisponível: o motor não devolveu valores avaliáveis de {especie.rotulo.toLowerCase()} para estes itens.
    </section>;
  }
  const [inicio, fim] = dominio;
  const atual: Corte = corte ?? { minimo: inicio, maximo: fim };
  const ativo = atual.minimo > inicio || atual.maximo < fim;
  const percentual = (valor: number) => fracao(valor, dominio, escala) * 100;
  const texto = (valor: number) => formatarNumero(valor, especie.contagem);

  function aplicar(cursor: Cursor, valor: number) {
    const proximo = cursor === "minimo" ? { minimo: Math.min(valor, atual.maximo), maximo: atual.maximo }
      : { minimo: atual.minimo, maximo: Math.max(valor, atual.minimo) };
    onCorte(proximo.minimo <= inicio && proximo.maximo >= fim ? null : proximo);
  }
  function valorNoPonto(clientX: number): number {
    const caixa = trilho.current?.getBoundingClientRect();
    if (!caixa || caixa.width <= 0) return inicio;
    return ajustarValor(valorNaFracao((clientX - caixa.left) / caixa.width, [inicio, fim], escala), [inicio, fim], escala, especie.contagem);
  }
  function agarrar(cursor: Cursor, event: PointerEvent<HTMLDivElement>) {
    if (desabilitado || event.button !== 0) return;
    event.preventDefault();
    event.stopPropagation();
    event.currentTarget.setPointerCapture(event.pointerId);
    event.currentTarget.focus();
    arrasto.current = { cursor, id: event.pointerId };
  }
  function mover(event: PointerEvent<HTMLDivElement>) {
    const estado = arrasto.current;
    if (!estado || estado.id !== event.pointerId) return;
    aplicar(estado.cursor, valorNoPonto(event.clientX));
  }
  function soltar(event: PointerEvent<HTMLDivElement>) {
    if (arrasto.current?.id === event.pointerId) arrasto.current = null;
  }
  /** Clique no trilho: o cursor mais próximo vai até o ponto. */
  function tocarTrilho(event: PointerEvent<HTMLDivElement>) {
    if (desabilitado || event.button !== 0) return;
    const valor = valorNoPonto(event.clientX);
    const cursor: Cursor = Math.abs(percentual(valor) - percentual(atual.minimo)) <= Math.abs(percentual(valor) - percentual(atual.maximo))
      ? "minimo" : "maximo";
    aplicar(cursor, valor);
  }
  function teclado(cursor: Cursor, event: KeyboardEvent<HTMLDivElement>) {
    if (desabilitado) return;
    const valor = cursor === "minimo" ? atual.minimo : atual.maximo;
    const passo = (sentido: 1 | -1, grande: boolean) => moverCursor(valor, sentido, grande, [inicio, fim], escala, especie.contagem);
    const novo = event.key === "ArrowRight" || event.key === "ArrowUp" ? passo(1, false)
      : event.key === "ArrowLeft" || event.key === "ArrowDown" ? passo(-1, false)
      : event.key === "PageUp" ? passo(1, true) : event.key === "PageDown" ? passo(-1, true)
      : event.key === "Home" ? (cursor === "minimo" ? inicio : atual.minimo)
      : event.key === "End" ? (cursor === "minimo" ? atual.maximo : fim) : null;
    if (novo === null) return;
    event.preventDefault();
    aplicar(cursor, novo);
  }

  const cursor = (qual: Cursor) => {
    const valor = qual === "minimo" ? atual.minimo : atual.maximo;
    const rotulo = qual === "minimo" ? "Acima de" : "Abaixo de";
    return <div role="slider" tabIndex={desabilitado ? -1 : 0} data-testid={qual === "minimo" ? "analise-regua-min" : "analise-regua-max"}
      aria-label={rotulo + " (" + (qual === "minimo" ? "limite inferior" : "limite superior") + " da régua de " + especie.rotulo.toLowerCase() + ")"}
      aria-valuemin={qual === "minimo" ? inicio : atual.minimo} aria-valuemax={qual === "minimo" ? atual.maximo : fim} aria-valuenow={valor}
      aria-valuetext={rotulo.toLowerCase() + " " + texto(valor) + " " + especie.unidade} aria-orientation="horizontal"
      aria-disabled={desabilitado || undefined} className="analise-cursor" style={{ left: percentual(valor) + "%" }}
      onPointerDown={event => agarrar(qual, event)} onPointerMove={mover} onPointerUp={soltar} onPointerCancel={soltar}
      onKeyDown={event => teclado(qual, event)}/>;
  };

  return <section data-testid="analise-regua" aria-label={"Régua: " + especie.rotulo.toLowerCase()} data-indicador={indicador}
    data-dominio-min={inicio} data-dominio-max={fim} data-minimo={atual.minimo} data-maximo={atual.maximo} data-ativo={ativo ? "true" : "false"}
    className="space-y-2">
    <div className="flex flex-wrap items-center justify-between gap-2">
      <p className="text-xs font-semibold text-ink">{especie.rotulo}{especie.contagem ? "" : " (" + especie.unidade + ")"}</p>
      <button type="button" data-testid="analise-regua-limpar" disabled={!ativo || desabilitado} onClick={() => onCorte(null)} className="analise-botao-secundario">
        <RotateCcw size={13} aria-hidden="true"/>Mostrar todos</button>
    </div>
    <div className="px-3">
      <div ref={trilho} className="analise-trilho" onPointerDown={tocarTrilho}>
        <span className="analise-faixa-corte" aria-hidden="true"
          style={{ left: percentual(atual.minimo) + "%", width: Math.max(0, percentual(atual.maximo) - percentual(atual.minimo)) + "%" }}/>
        {cursor("minimo")}
        {cursor("maximo")}
      </div>
      <div className="flex justify-between text-[11px] tabular-nums text-slate-500" aria-hidden="true">
        <span>{texto(inicio)}</span><span>{texto(fim)}</span>
      </div>
    </div>
    <p className="text-xs leading-5 text-slate-600" data-testid="analise-regua-texto">{ativo
      ? <>Aparecem só {plural} com {especie.rotulo.toLowerCase()} acima de <strong className="text-ink">{texto(atual.minimo)}</strong> e
        abaixo de <strong className="text-ink">{texto(atual.maximo)}</strong> {especie.unidade} (limites incluídos). Conjuntos e a referência
        continuam à vista. A régua só esconde: nada é recalculado.</>
      : <>Arraste os cursores (ou use as setas com um cursor focado) para mostrar só o que fica acima de um valor, abaixo de outro
        ou entre os dois. A régua só esconde: nada é recalculado.</>}</p>
  </section>;
}
