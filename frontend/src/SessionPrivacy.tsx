import { useEffect, useRef, useState } from "react";
import { ShieldCheck } from "lucide-react";

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
    } catch {
      // Se o navegador bloquear o armazenamento, mantém o aceite nesta página.
    }
    setAccepted(true);
  }

  return { accepted, accept };
}

export default function SessionPrivacy({ onAccept }: { onAccept: () => void }) {
  const dialogRef = useRef<HTMLDialogElement>(null);

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

  return <dialog ref={dialogRef} aria-labelledby="privacy-title" aria-describedby="privacy-declaration"
    onCancel={event => event.preventDefault()}
    className="privacy-dialog no-print m-auto max-h-[calc(100dvh_-_2rem)] w-[calc(100%_-_2rem)] max-w-lg overflow-y-auto rounded-3xl border border-line bg-white p-6 text-ink shadow-2xl sm:p-8">
    <span className="mb-5 inline-flex rounded-2xl bg-cyan-50 p-3 text-teal"><ShieldCheck size={28}/></span>
    <h2 id="privacy-title" className="text-xl font-bold">Antes de começar</h2>
    <p id="privacy-declaration" className="mt-4 text-sm leading-7 text-slate-700">
      Declaro que não compartilharei dados pessoais ou sensíveis, seja por meio dos arquivos enviados ou das mensagens inseridas no chat.
    </p>
    <p className="mt-3 text-xs leading-5 text-slate-500">Esta sessão e seu conteúdo são eliminados ao acionar Encerrar sessão ou após 30 minutos (1800 segundos) sem interação efetiva sua. Fechar a interface não encerra imediatamente. Atividade automática não renova o prazo. Exporte o que deseja conservar antes do encerramento; não há retomada entre sessões.</p>
    <button type="button" autoFocus onClick={onAccept}
      className="mt-6 w-full rounded-xl bg-blue-600 px-5 py-3 text-sm font-semibold text-white hover:bg-blue-700">
      Li e concordo
    </button>
  </dialog>;
}
