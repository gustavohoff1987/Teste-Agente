import type { ReactNode } from "react";
import { AlertCircle, CheckCircle2, LoaderCircle, XCircle } from "lucide-react";

export type Requirement = {
  status: "met" | "needs_confirmation" | "missing";
  title: string;
  detail: string;
};

type Props = {
  analysis: string;
  status: "available" | "needs_confirmation" | "unavailable" | "loading";
  requirements: Requirement[];
  onExecute: () => void;
  executing: boolean;
  children?: ReactNode;
};

export default function RequirementChecklist({ analysis, status, requirements,
                                                onExecute, executing, children }: Props) {
  const available = status === "available";
  const label = available ? "Disponível" : status === "needs_confirmation" ?
    "Confirmação necessária" : status === "loading" ? "Verificando..." : "Não habilitada";
  return <section id="requisitos" aria-label={"Requisitos de " + analysis}
    className="section-anchor mt-5 rounded-[20px] border border-line bg-white p-5 shadow-card sm:p-6">
    <div className="flex flex-wrap items-start justify-between gap-3">
      <div>
        <h3 className="text-base font-bold text-ink">Requisitos para {analysis}</h3>
        <p className="mt-1 text-xs leading-5 text-slate-600">
          Confira as condições para esta análise. Os sinais indicam o que já foi validado, o que precisa de confirmação e o que está faltando.
        </p>
      </div>
      <span className={["rounded-full px-3 py-1.5 text-xs font-bold",
        available ? "bg-emerald-50 text-emerald-700" :
        status === "needs_confirmation" ? "bg-amber-50 text-amber-800" :
        "bg-slate-100 text-slate-600"].join(" ")}>{label}</span>
    </div>
    {status === "loading" ? <p role="status" className="mt-5 flex items-center gap-2 text-sm text-teal"><LoaderCircle size={17} className="animate-spin"/> Aguardando a verificação da base...</p> :
      <div className="mt-5 grid gap-3 md:grid-cols-2">
        {requirements.length ? requirements.map((requirement, index) => (
          <div key={requirement.status + requirement.title + index}
            className="flex items-start gap-3 rounded-xl border border-line bg-slate-50/40 p-3.5">
            {requirement.status === "met" ? <CheckCircle2 aria-label="Atendido" size={21} className="mt-0.5 shrink-0 text-emerald-600"/> :
              requirement.status === "needs_confirmation" ? <AlertCircle aria-label="Confirmação necessária" size={21} className="mt-0.5 shrink-0 text-amber-600"/> :
              <XCircle aria-label="Não atendido" size={21} className="mt-0.5 shrink-0 text-rose-600"/>}
            <div className="min-w-0">
              <p className="text-sm font-semibold text-ink">{requirement.title}</p>
              <p className="mt-1 text-xs leading-5 text-slate-600">{requirement.detail}</p>
            </div>
          </div>
        )) : <p className="text-sm text-slate-500">Carregue uma base de dados para consultar os requisitos.</p>}
      </div>}
    {children}
    <div className="mt-5 flex flex-wrap items-center justify-between gap-3 border-t border-line pt-5">
      <p className="max-w-lg text-xs leading-5 text-slate-500">
        {available ? "As condições verificadas permitem solicitar esta análise." :
          "A análise não será executada enquanto houver condições obrigatórias pendentes."}
      </p>
      <button type="button" disabled={!available || executing} onClick={onExecute}
        className="inline-flex items-center gap-2 rounded-xl bg-teal px-4 py-3 text-sm font-bold text-white hover:bg-ink disabled:cursor-not-allowed disabled:bg-slate-200 disabled:text-slate-500">
        {executing ? <LoaderCircle className="animate-spin" size={17}/> :
          available ? <CheckCircle2 size={17}/> : <XCircle size={17}/>}
        {executing ? "Executando..." : "Executar análise"}
      </button>
    </div>
  </section>;
}
