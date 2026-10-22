import { useCallback, useEffect, useLayoutEffect, useRef, useState, type KeyboardEvent, type PointerEvent, type ReactNode } from "react";
import { ChevronUp, GripHorizontal, Minus } from "lucide-react";
import BrandAvatar from "./BrandAvatar";
import { useNarrow } from "./useNarrow";

// Caixa flutuante da conversa, sempre na página única (22/10/2026): o rosto do agente no cabeçalho, no canto inferior
// direito, arrastável pelo cabeçalho (pointer events) e pelo teclado (setas com o cabeçalho focado; Shift acelera; Home volta
// ao canto), minimizável e sempre dentro da janela. Na abertura, antes dos dados, ela fica aberta e mais larga ("ampla"); depois,
// compacta. A posição fica no localStorage, sempre com try/catch (sem armazenamento, vale só nesta tela). No celular, a caixa
// fica ancorada embaixo. A conversa mantém o id "assistente".

const CHAVE = "adt:painel-chat:v1";
const PASSO = 16, PASSO_LONGO = 64;
type Guardado = { x: number | null; y: number | null; minimizada: boolean };
type Posicao = { x: number; y: number };

function ler(): Guardado {
  try {
    const bruto = window.localStorage.getItem(CHAVE);
    if (!bruto) return { x: null, y: null, minimizada: false };
    const valor = JSON.parse(bruto) as Partial<Guardado> | null;
    const numero = (item: unknown) => typeof item === "number" && Number.isFinite(item) ? item : null;
    return { x: numero(valor?.x), y: numero(valor?.y), minimizada: valor?.minimizada === true };
  } catch {
    return { x: null, y: null, minimizada: false };
  }
}

function gravar(valor: Guardado) {
  try { window.localStorage.setItem(CHAVE, JSON.stringify(valor)); }
  catch { /* sem armazenamento: a posição vale só nesta tela */ }
}

/** ampla: a abertura, antes dos dados — a caixa começa aberta (mesmo que tenha sido minimizada antes) e mais larga. */
type Props = { children: ReactNode; ocupado?: boolean; ampla?: boolean };

export default function ChatFloatingBox({ children, ocupado = false, ampla = false }: Props) {
  const narrow = useNarrow();
  const caixa = useRef<HTMLElement>(null);
  const [guardado] = useState(ler);
  const [posicao, setPosicao] = useState<Posicao | null>(guardado.x !== null && guardado.y !== null ? { x: guardado.x, y: guardado.y } : null);
  const [minimizada, setMinimizada] = useState(ampla ? false : guardado.minimizada);
  const [anuncio, setAnuncio] = useState("");
  const arrasto = useRef<{ id: number; dx: number; dy: number } | null>(null);

  /** Posição presa à janela: a caixa inteira fica visível. */
  const prender = useCallback((x: number, y: number): Posicao => {
    const box = caixa.current?.getBoundingClientRect();
    const largura = box?.width ?? 0, altura = box?.height ?? 0;
    return { x: Math.round(Math.min(Math.max(0, x), Math.max(0, window.innerWidth - largura))),
      y: Math.round(Math.min(Math.max(0, y), Math.max(0, window.innerHeight - altura))) };
  }, []);

  // Abrir, minimizar ou trocar de largura (da janela ou da caixa) muda o tamanho: a posição volta para dentro da janela.
  useLayoutEffect(() => {
    if (narrow || !posicao) return;
    const presa = prender(posicao.x, posicao.y);
    if (presa.x !== posicao.x || presa.y !== posicao.y) setPosicao(presa);
  }, [narrow, minimizada, ampla, posicao, prender]);
  useEffect(() => {
    const ajustar = () => setPosicao(atual => atual ? prender(atual.x, atual.y) : atual);
    window.addEventListener("resize", ajustar);
    return () => window.removeEventListener("resize", ajustar);
  }, [prender]);
  useEffect(() => {
    const timer = window.setTimeout(() => gravar({ x: posicao?.x ?? null, y: posicao?.y ?? null, minimizada }), 150);
    return () => window.clearTimeout(timer);
  }, [posicao, minimizada]);

  function agarrar(event: PointerEvent<HTMLDivElement>) {
    if (narrow || event.button !== 0 || (event.target as Element).closest("button")) return;
    const box = caixa.current?.getBoundingClientRect();
    if (!box) return;
    arrasto.current = { id: event.pointerId, dx: event.clientX - box.left, dy: event.clientY - box.top };
    event.currentTarget.setPointerCapture(event.pointerId);
    event.preventDefault();
  }
  function mover(event: PointerEvent<HTMLDivElement>) {
    const atual = arrasto.current;
    if (!atual || atual.id !== event.pointerId) return;
    setPosicao(prender(event.clientX - atual.dx, event.clientY - atual.dy));
  }
  function soltar(event: PointerEvent<HTMLDivElement>) {
    if (arrasto.current?.id !== event.pointerId) return;
    arrasto.current = null;
    if (event.currentTarget.hasPointerCapture(event.pointerId)) event.currentTarget.releasePointerCapture(event.pointerId);
    setAnuncio("Caixa da conversa movida.");
  }
  function teclado(event: KeyboardEvent<HTMLDivElement>) {
    if (event.target !== event.currentTarget || narrow) return;
    if (event.key === "Home") {
      event.preventDefault();
      setPosicao(null);
      setAnuncio("Caixa da conversa de volta ao canto inferior direito.");
      return;
    }
    const passo = event.shiftKey ? PASSO_LONGO : PASSO;
    const deslocamento: Record<string, [number, number]> = { ArrowLeft: [-passo, 0], ArrowRight: [passo, 0], ArrowUp: [0, -passo], ArrowDown: [0, passo] };
    const delta = deslocamento[event.key];
    const box = caixa.current?.getBoundingClientRect();
    if (!delta || !box) return;
    event.preventDefault();
    setPosicao(prender(box.left + delta[0], box.top + delta[1]));
    setAnuncio("Caixa da conversa movida.");
  }

  const estilo = !narrow && posicao ? { left: posicao.x, top: posicao.y, right: "auto", bottom: "auto" } : undefined;
  return <section id="assistente" ref={caixa} aria-label="Assistente de análise territorial" data-testid="painel-chat"
    data-minimizada={minimizada ? "true" : "false"} data-ancorada={narrow ? "true" : "false"} data-ampla={ampla ? "true" : "false"}
    className={"painel-chat no-print" + (narrow ? " painel-chat-ancorada" : "")} style={estilo}>
    <div className="painel-chat-cabecalho" data-testid="painel-chat-handle" tabIndex={0} role="group"
      aria-label={narrow ? "Conversa com o agente" : "Conversa com o agente. Para mover a caixa, arraste o cabeçalho ou, com ele focado, use as setas; Shift acelera e Home volta ao canto."}
      onPointerDown={agarrar} onPointerMove={mover} onPointerUp={soltar} onPointerCancel={soltar} onKeyDown={teclado}>
      <BrandAvatar size={34}/>
      <div className="min-w-0 flex-1">
        <p className="truncate text-sm font-bold text-ink">Agente Diagnóstico Territorial</p>
        <p className="truncate text-[11px] text-slate-500">{ocupado ? "Interpretando o pedido…" : narrow ? "Conversa sobre o gráfico" : "Arraste pelo cabeçalho para mover"}</p>
      </div>
      {!narrow && <GripHorizontal size={16} aria-hidden="true" className="shrink-0 text-slate-400"/>}
      <button type="button" data-testid="painel-chat-minimizar" aria-expanded={!minimizada} aria-controls="painel-chat-corpo"
        aria-label={minimizada ? "Abrir a conversa" : "Minimizar a conversa"} title={minimizada ? "Abrir a conversa" : "Minimizar a conversa"}
        onClick={() => setMinimizada(valor => !valor)}
        className="inline-flex h-9 w-9 shrink-0 items-center justify-center rounded-lg border border-line bg-white text-ink hover:bg-cyan-50">
        {minimizada ? <ChevronUp size={16} aria-hidden="true"/> : <Minus size={16} aria-hidden="true"/>}
      </button>
    </div>
    <div id="painel-chat-corpo" className="painel-chat-corpo" hidden={minimizada}>{children}</div>
    <p aria-live="polite" className="sr-only">{anuncio}</p>
  </section>;
}
