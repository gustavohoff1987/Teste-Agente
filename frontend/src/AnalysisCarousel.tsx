import { useEffect, useRef, useState } from "react";
import type { CSSProperties } from "react";
import { ArrowRight, Check, ChevronLeft, ChevronRight, Mouse } from "lucide-react";
import type { LucideIcon } from "lucide-react";
import AnalysisIllustration from "./AnalysisIllustration";

type Feature<T extends string> = { id: T; title: string; detail: string; icon: LucideIcon; tone: string };
type Props<T extends string> = {
  features: Feature<T>[];
  active: T | null;
  capabilities?: Partial<Record<T, { status: "available" | "needs_confirmation" | "unavailable"; reasons: string[] }>>;
  checking: boolean;
  hasData: boolean;
  scopeChanges?: T[];
  onSelect: (operation: T) => void;
  onRequirements: () => void;
};
const PALETTES: Record<string, [string, string]> = {
  teal: ["#087e8b", "#e8f8f8"], indigo: ["#5452c6", "#eeedff"],
  violet: ["#8245bb", "#f4ecfc"], orange: ["#b65823", "#fff1e8"],
  blue: ["#326ac6", "#eaf2ff"], emerald: ["#14845f", "#e7f7ef"],
  rose: ["#b3446c", "#ffedf3"], amber: ["#9e6a12", "#fff6de"],
  cyan: ["#0d7f9f", "#e7f7fc"], slate: ["#4b6580", "#edf2f8"],
};

export default function AnalysisCarousel<T extends string>({ features, active, capabilities, checking, hasData, scopeChanges = [],
  onSelect, onRequirements }: Props<T>) {
  const [index, setIndex] = useState(0);
  const deckRef = useRef<HTMLDivElement>(null);
  const wheel = useRef({ total: 0, last: 0, moved: false });
  const gesture = useRef<{ x: number; y: number; id: number; onCard: boolean } | null>(null);
  const suppressPointerClick = useRef(false);
  const feature = features[index];
  const selected = active === feature.id;
  const capability = capabilities?.[feature.id];
  const changesScope = scopeChanges.includes(feature.id);
  const status = checking ? "Verificando..." : !hasData ? "Importe uma base para habilitar" :
    changesScope ? "Selecione para conferir o recorte" :
    capability?.status === "available" ? "Disponível" : capability?.status === "needs_confirmation" ?
    "Confirmação necessária" : "Não habilitada";
  const [accent, soft] = PALETTES[feature.tone] || PALETTES.teal;

  // Propostas escolhidas no chat também levam o seletor à análise correspondente.
  useEffect(() => {
    const next = features.findIndex(item => item.id === active);
    if (next >= 0) setIndex(next);
  }, [active, features]);

  useEffect(() => {
    const deck = deckRef.current;
    function rotate(event: WheelEvent) {
      if (event.ctrlKey || event.metaKey) return;
      const delta = Math.abs(event.deltaX) > Math.abs(event.deltaY) ? event.deltaX : event.deltaY;
      if (!delta) return;
      const direction = Math.sign(delta);
      // Nas extremidades, a rolagem volta à página; zoom permanece nativo.
      if ((index === 0 && direction < 0) || (index === features.length - 1 && direction > 0)) return;
      event.preventDefault();
      const now = performance.now();
      if (now - wheel.current.last > 180) wheel.current = { total: 0, last: now, moved: false };
      wheel.current.last = now;
      if (wheel.current.moved) return;
      wheel.current.total += delta * (event.deltaMode === 1 ? 16 : event.deltaMode === 2 ? 240 : 1);
      if (Math.abs(wheel.current.total) < 35) return;
      wheel.current.moved = true;
      setIndex(current => Math.max(0, Math.min(features.length - 1, current + direction)));
    }
    deck?.addEventListener("wheel", rotate, { passive: false });
    return () => deck?.removeEventListener("wheel", rotate);
  }, [index, features.length]);

  function move(step: number) {
    setIndex(current => Math.max(0, Math.min(features.length - 1, current + step)));
  }

  return <section id="analises" aria-labelledby="analysis-carousel-title" aria-roledescription="carrossel"
    className="analysis-carousel section-anchor no-print"
    style={{ "--card-accent": accent, "--card-soft": soft } as CSSProperties}>
    <div className="carousel-heading">
      <div><span className="workspace-eyebrow">EXPLORE AS POSSIBILIDADES</span>
        <h2 id="analysis-carousel-title">Tipos de análise</h2></div>
      <span className="carousel-count" aria-hidden="true">{String(index + 1).padStart(2, "0")}<span> / {features.length}</span></span>
    </div>
    <div ref={deckRef} className="analysis-deck" onKeyDown={event => {
      if (event.altKey || event.ctrlKey || event.metaKey) return;
      if (["ArrowRight", "ArrowDown", "ArrowLeft", "ArrowUp", "Home", "End"].includes(event.key)) {
        event.preventDefault();
        if (event.key === "Home") setIndex(0);
        else if (event.key === "End") setIndex(features.length - 1);
        else move(event.key === "ArrowRight" || event.key === "ArrowDown" ? 1 : -1);
      }
    }} onPointerDown={event => {
      if (!event.isPrimary || event.button !== 0) return;
      gesture.current = { x: event.clientX, y: event.clientY, id: event.pointerId,
        onCard: event.target instanceof Element && !!event.target.closest(".analysis-card") };
      suppressPointerClick.current = false;
    }} onPointerUp={event => {
      const start = gesture.current;
      gesture.current = null;
      if (!start || start.id !== event.pointerId) return;
      const dx = event.clientX - start.x;
      const dy = event.clientY - start.y;
      if (Math.abs(dx) > 45 && Math.abs(dx) > Math.abs(dy) * 1.4) {
        suppressPointerClick.current = true;
        move(dx < 0 ? 1 : -1);
      } else if (event.pointerType === "touch" && start.onCard && Math.abs(dx) < 10 && Math.abs(dy) < 10) {
        // Após um deslize, alguns navegadores omitem o click do próximo toque.
        // O pointerup conclui esse toque; o click sintético não deve duplicá-lo.
        suppressPointerClick.current = true;
        onSelect(feature.id);
      }
    }} onPointerCancel={() => { gesture.current = null; }} onClickCapture={event => {
      if (suppressPointerClick.current && event.detail > 0) {
        event.preventDefault(); event.stopPropagation();
      }
      suppressPointerClick.current = false;
    }}>
      <div className="deck-sheet deck-sheet-back" aria-hidden="true"/>
      <div className="deck-sheet deck-sheet-front" aria-hidden="true"/>
      <button type="button" className={"analysis-card" + (selected ? " analysis-card-selected" : "")}
        aria-label={"Selecionar análise: " + feature.title} aria-pressed={selected}
        aria-describedby="analysis-card-detail analysis-card-status"
        title={changesScope ? "Ao selecionar, os requisitos serão conferidos no recorte apropriado da base Brasil." : capability?.reasons.join(" ") || "Selecione para conferir os requisitos"}
        onClick={() => onSelect(feature.id)}>
        <span className="card-selection">{selected ? <><Check size={13}/> Selecionada</> : "ANÁLISE TERRITORIAL"}</span>
        <span className="analysis-art"><AnalysisIllustration kind={feature.id}/></span>
        <span className="analysis-card-copy">
          <span className="analysis-card-title">{feature.title}</span>
          <span id="analysis-card-detail" className="analysis-card-detail">{feature.detail}</span>
        </span>
        <span id="analysis-card-status" className="analysis-card-status" data-status={checking ? "checking" : capability?.status || "unavailable"}>
          <span aria-hidden="true"/>{status}
        </span>
        <span className="analysis-card-action">{selected ? "Análise selecionada" : "Selecionar análise"}<ArrowRight size={16}/></span>
      </button>
    </div>
    <div className="carousel-controls">
      <button type="button" aria-label="Análise anterior" disabled={index === 0} onClick={() => move(-1)}><ChevronLeft size={19}/></button>
      <p aria-live="polite" aria-atomic="true"><span className="sr-only">{feature.title}, análise </span>{index + 1} de {features.length}</p>
      <button type="button" aria-label="Próxima análise" disabled={index === features.length - 1} onClick={() => move(1)}><ChevronRight size={19}/></button>
    </div>
    <div className="carousel-progress" aria-hidden="true">{features.map((item, position) => <span key={item.id} className={position === index ? "current" : ""}/>)}</div>
    <p className="carousel-hint"><Mouse size={13}/><span>Role sobre o card ou deslize para explorar</span></p>
    {active && <button type="button" className="carousel-requirements" onClick={onRequirements}>
      Ver requisitos de {features.find(item => item.id === active)?.title}<ArrowRight size={14}/>
    </button>}
  </section>;
}
