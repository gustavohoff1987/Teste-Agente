import { useCallback, useEffect, useLayoutEffect, useRef, useState, type KeyboardEvent, type PointerEvent, type ReactNode } from "react";
import { GripHorizontal, Minus } from "lucide-react";
import BrandAvatar from "./BrandAvatar";
import { useNarrow } from "./useNarrow";

// Caixa flutuante da conversa, sempre na página única (22/10/2026): o rosto do agente no cabeçalho, no canto inferior
// direito, arrastável pelo cabeçalho (pointer events) e pelo teclado (setas com o cabeçalho focado; Shift acelera; Home volta
// ao canto), minimizável e sempre dentro da janela. Na abertura, antes dos dados, ela fica aberta e mais larga ("ampla"); depois,
// compacta. A posição fica no localStorage, sempre com try/catch (sem armazenamento, vale só nesta tela). No celular, a caixa
// fica ancorada embaixo. A conversa mantém o id "assistente". Desde 04/11/2026, a caixa inteira cabe na janela em qualquer
// altura: ela nunca passa da altura da janela, o histórico e a orientação rolam por dentro e o campo de envio fica sempre à
// vista (styles.css, "Caixa da conversa inteira na janela"). Desde 10/11/2026 (conferência das capturas da pausa 2 do comando
// V22), a caixa minimizada é só o botão redondo com o rosto do agente, sem texto, para não cobrir campos nem botões da página
// (antes, o rosto, "Assistente" e o botão que a abria); arrastar o botão move a caixa. No canto de sempre, a página reserva o
// espaço dela no fim do painel da Seleção (a variável --espaco-da-conversa).

const CHAVE = "adt:painel-chat:v1";
const PASSO = 16, PASSO_LONGO = 64;
/** Até aqui (em px), o ponteiro no botão redondo ainda é um clique; além disso, é um arrasto. */
const FOLGA_DO_CLIQUE = 6;
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
  const arrasto = useRef<{ id: number; dx: number; dy: number; x0: number; y0: number; moveu: boolean } | null>(null);
  /** O botão redondo foi arrastado: o clique que encerra o arrasto não abre a caixa. */
  const arrastada = useRef(false);
  /** Abrir e minimizar trocam o botão por outro: o foco vai para o botão novo, para o teclado não perder o lugar. */
  const focar = useRef(false);
  useEffect(() => {
    if (!focar.current) return;
    focar.current = false;
    caixa.current?.querySelector<HTMLButtonElement>('[data-testid="painel-chat-minimizar"]')?.focus({ preventScroll: true });
  }, [minimizada]);

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
  // A caixa também cresce sozinha (mensagens novas, avisos, a orientação): a posição volta para dentro da janela sempre que o
  // tamanho dela muda (04/11/2026; antes, só ao abrir, minimizar, trocar de largura ou redimensionar a janela).
  useEffect(() => {
    const alvo = caixa.current;
    if (!alvo || typeof ResizeObserver === "undefined") return;
    const observador = new ResizeObserver(() => setPosicao(atual => {
      if (!atual) return atual;
      const presa = prender(atual.x, atual.y);
      return presa.x === atual.x && presa.y === atual.y ? atual : presa;
    }));
    observador.observe(alvo);
    return () => observador.disconnect();
  }, [prender]);
  useEffect(() => {
    const timer = window.setTimeout(() => gravar({ x: posicao?.x ?? null, y: posicao?.y ?? null, minimizada }), 150);
    return () => window.clearTimeout(timer);
  }, [posicao, minimizada]);
  // Minimizada no canto de sempre (ou ancorada embaixo, no celular), a caixa fica por cima do fim da tela: quem prende um painel à
  // janela desconta esse espaço (o botão redondo, de 52 px, com a borda e a margem do canto).
  useEffect(() => {
    const raiz = document.documentElement;
    raiz.style.setProperty("--espaco-da-conversa", minimizada && (narrow || !posicao) ? "80px" : "0px");
    return () => { raiz.style.removeProperty("--espaco-da-conversa"); };
  }, [minimizada, narrow, posicao]);

  function agarrar(event: PointerEvent<HTMLDivElement>) {
    const botao = (event.target as Element).closest("button");
    // Aberta, os botões do cabeçalho não arrastam. Minimizada, a caixa é o botão redondo: ele arrasta depois de uma folga.
    if (narrow || event.button !== 0 || (botao && !minimizada)) return;
    const box = caixa.current?.getBoundingClientRect();
    if (!box) return;
    arrastada.current = false;
    arrasto.current = { id: event.pointerId, dx: event.clientX - box.left, dy: event.clientY - box.top, x0: event.clientX, y0: event.clientY,
      moveu: !botao };
    // No botão redondo, a captura fica nele (o clique continua sendo dele), e os movimentos sobem até o cabeçalho.
    (botao ?? event.currentTarget).setPointerCapture(event.pointerId);
    if (!botao) event.preventDefault();
  }
  function mover(event: PointerEvent<HTMLDivElement>) {
    const atual = arrasto.current;
    if (!atual || atual.id !== event.pointerId) return;
    if (!atual.moveu) {
      if (Math.hypot(event.clientX - atual.x0, event.clientY - atual.y0) < FOLGA_DO_CLIQUE) return;
      atual.moveu = true;
      arrastada.current = true;
    }
    setPosicao(prender(event.clientX - atual.dx, event.clientY - atual.dy));
  }
  function soltar(event: PointerEvent<HTMLDivElement>) {
    const atual = arrasto.current;
    if (atual?.id !== event.pointerId) return;
    arrasto.current = null;
    for (const alvo of [event.target as Element, event.currentTarget as Element])
      if (alvo.hasPointerCapture?.(event.pointerId)) alvo.releasePointerCapture(event.pointerId);
    if (atual.moveu) setAnuncio("Caixa da conversa movida.");
    // O clique do botão (se houver) vem logo depois deste evento; passado ele, um arrasto antigo não engole o clique seguinte.
    window.setTimeout(() => { arrastada.current = false; }, 0);
  }
  function alternar() {
    if (arrastada.current) { arrastada.current = false; return; }
    focar.current = true;
    setMinimizada(valor => !valor);
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
    <div className="painel-chat-cabecalho" data-testid="painel-chat-handle" tabIndex={minimizada ? -1 : 0} role="group"
      aria-label={narrow ? "Conversa com o agente" : "Conversa com o agente. Para mover a caixa, arraste o cabeçalho ou, com ele focado, use as setas; Shift acelera e Home volta ao canto."}
      onPointerDown={agarrar} onPointerMove={mover} onPointerUp={soltar} onPointerCancel={soltar} onKeyDown={teclado}>
      {minimizada
        // Minimizada: só o botão redondo com o rosto do agente. O nome do botão diz o que ele faz e, com um pedido em curso, isso também.
        ? <button type="button" data-testid="painel-chat-minimizar" data-ocupado={ocupado ? "true" : "false"} aria-expanded={false}
            aria-controls="painel-chat-corpo" aria-label={ocupado ? "Abrir a conversa (o agente está interpretando o pedido)" : "Abrir a conversa"}
            title={ocupado ? "Abrir a conversa (interpretando o pedido…)" : "Abrir a conversa"} onClick={alternar} className="painel-chat-redonda">
            <BrandAvatar size={40}/>
          </button>
        : <>
          <BrandAvatar size={34}/>
          <div className="min-w-0 flex-1">
            <p className="truncate text-[15px] font-bold tracking-[-0.01em] text-ink">Agente Diagnóstico Territorial</p>
            <p className="truncate text-[12px] text-slate-600">{ocupado ? "Interpretando o pedido…" : narrow ? "Conversa sobre o gráfico" : "Arraste pelo cabeçalho para mover"}</p>
          </div>
          {!narrow && <GripHorizontal size={16} aria-hidden="true" className="shrink-0 text-slate-400"/>}
          <button type="button" data-testid="painel-chat-minimizar" aria-expanded={true} aria-controls="painel-chat-corpo"
            aria-label="Minimizar a conversa" title="Minimizar a conversa" onClick={alternar}
            className="inline-flex h-9 w-9 shrink-0 items-center justify-center rounded-lg border border-line bg-white text-ink hover:bg-cyan-50">
            <Minus size={16} aria-hidden="true"/>
          </button>
        </>}
    </div>
    <div id="painel-chat-corpo" className="painel-chat-corpo" hidden={minimizada}>{children}</div>
    <p aria-live="polite" className="sr-only">{anuncio}</p>
  </section>;
}
