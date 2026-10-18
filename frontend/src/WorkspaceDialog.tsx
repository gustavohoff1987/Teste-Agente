import { useEffect, useRef, type ReactNode } from "react";
import BrandAvatar from "./BrandAvatar";

/** O diálogo nativo contém o foco, bloqueia o fundo e devolve o foco ao acionador. */
export default function WorkspaceDialog({ title, id, onClose, children, busy = false }: {
  title: string; id: string; onClose: () => void; children: ReactNode; busy?: boolean;
}) {
  const dialog = useRef<HTMLDialogElement>(null);
  useEffect(() => {
    const trigger = document.activeElement as HTMLElement | null;
    dialog.current?.showModal();
    return () => { dialog.current?.close(); trigger?.focus(); };
  }, []);
  return <dialog ref={dialog} data-testid={id} aria-labelledby={id + "-title"}
    className="workspace-dialog no-print" onCancel={event => { event.preventDefault(); if (!busy) onClose(); }}
    onKeyDown={event => {
      if (event.key !== "Tab") return;
      const controls = [...event.currentTarget.querySelectorAll<HTMLElement>('button:not(:disabled), a[href], input:not(:disabled), select:not(:disabled), textarea:not(:disabled), [tabindex="0"]')];
      const first = controls[0], last = controls.at(-1);
      if (!first || !last) {event.preventDefault(); return;}
      if (event.shiftKey && document.activeElement === first) {event.preventDefault(); last.focus();}
      else if (!event.shiftKey && document.activeElement === last) {event.preventDefault(); first.focus();}
    }}>
    <div className="flex items-center gap-3"><BrandAvatar size={42}/>
      <h2 id={id + "-title"} className="text-lg font-bold text-ink">{title}</h2></div>
    {children}
  </dialog>;
}
