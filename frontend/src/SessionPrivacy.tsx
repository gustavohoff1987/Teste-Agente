import { useEffect, useRef, useState } from "react";

const SESSION_KEY = "adt:privacy-accepted:v1";

export function useSessionPrivacy() {
  const [accepted, setAccepted] = useState(() => {
    try {
      return window.sessionStorage.getItem(SESSION_KEY) === "true";
    } catch {
      return false;
    }
  });

  function accept() {
    try {
      window.sessionStorage.setItem(SESSION_KEY, "true");
      window.sessionStorage.removeItem("adt:session-ended");
    } catch {
      // Se o navegador bloquear o armazenamento, mantém o aceite nesta página.
    }
    setAccepted(true);
  }

  return { accepted, accept };
}

export default function SessionPrivacy({ onAccept }: { onAccept: () => void }) {
  const dialogRef = useRef<HTMLDialogElement>(null);
  const [endedReason] = useState(() => {
    try { return sessionStorage.getItem("adt:session-ended"); } catch { return null; }
  });

  useEffect(() => {
    const dialog = dialogRef.current;
    const previousOverflow = document.body.style.overflow;
    dialog?.showModal();
    document.body.style.overflow = "hidden";
    return () => {
      dialog?.close();
      document.body.style.overflow = previousOverflow;
    };
  }, []);

  // O pop-up de início traz só a declaração (decisão do responsável pelo produto, 19/10/2026); a
  // declaração também dá nome ao diálogo para o leitor de tela.
  return <dialog ref={dialogRef} aria-labelledby="privacy-declaration"
    onCancel={event => event.preventDefault()}
    className="privacy-dialog no-print m-auto max-h-[calc(100dvh_-_2rem)] w-[calc(100%_-_2rem)] max-w-lg overflow-y-auto rounded-3xl border border-line bg-white p-6 text-ink shadow-2xl sm:p-8">
    {endedReason && <p role="status" data-testid="session-ended-notice" className="mb-4 rounded-lg border border-amber-200 bg-amber-50 p-3 text-sm text-amber-900">
      {endedReason === "closed" ? "A sessão anterior foi encerrada." : "A sessão anterior expirou ou ficou indisponível no servidor."}
      {" "}Os resultados e a investigação temporária foram descartados. Eles não podem ser reabertos nesta nova sessão.
    </p>}
    <p id="privacy-declaration" className="text-base leading-7 text-slate-700">
      Declaro que não compartilharei dados pessoais ou sensíveis, seja por meio dos arquivos enviados ou das mensagens inseridas no chat.
    </p>
    <button type="button" autoFocus onClick={onAccept}
      className="mt-6 w-full rounded-xl bg-blue-600 px-5 py-3 text-sm font-semibold text-white hover:bg-blue-700">
      Li e concordo
    </button>
  </dialog>;
}
