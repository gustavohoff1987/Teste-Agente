import { useEffect, useRef, type ReactNode } from "react";
import type { Requirement } from "./RequirementChecklist";

export function preparationRequirements(requirements: Requirement[]) {
  const seen = new Set<string>();
  return requirements.flatMap(item => {
    const code = item.status === "needs_confirmation" &&
      /Confirme a associação de Código territorial|Confirme que o código identifica/.test(item.detail);
    const next = code ? { ...item, title: "Identificador territorial", detail: item.status === "met" ? item.detail :
      "Confirme o identificador territorial. Ele distingue municípios de mesmo nome; reconhecer a unidade territorial não confirma seu código." } : item;
    const key = next.status + next.detail;
    if (seen.has(key)) return [];
    seen.add(key);
    return [next];
  });
}

export function requirementStep(item: Requirement): number {
  const text = item.detail.toLowerCase();
  if (/popula|denominador|comparab|comparação|compare|convenção|filtro|selecione|escolha|coorte|cobertura|contagem|quantitativo|coordenad|latitude|longitude|geodésico|sobrepos|duplic|registros|partes|identificador individual/.test(text)) return 1;
  if (/identificador territorial|código|objeto|categoria|profissão|força de trabalho|associação|associe período|referência temporal|dimensão territorial/.test(text)) return 0;
  return 1;
}

type Props = { title: string; step: number; onStep: (step: number) => void; checking: boolean;
  requirements: Requirement[]; ready: boolean; children: ReactNode; notice?: string };

const STEPS = ["Identificar os dados", "Parâmetros e confirmações", "Revisar e executar"];
export default function PreparationPanel({ title, step, onStep, checking, requirements, ready, children, notice }: Props) {
  const scroll = useRef<HTMLDivElement>(null);
  const pending = requirements.filter(item => item.status !== "met");
  useEffect(() => { scroll.current?.scrollTo({ top: 0 }); }, [step, title]);
  return <section id="preparacao" aria-label="Preparação da análise" className="preparation-panel">
    <header className="border-b border-line p-4 sm:p-5">
      <p className="text-xs font-bold text-teal">Etapa {step + 1} de 3</p>
      <h2 className="mt-1 text-lg font-bold text-ink">{title}</h2>
      <nav aria-label="Etapas da preparação" className="mt-3 flex flex-wrap gap-2">
        {STEPS.map((label, index) => {
          const count = pending.filter(item => requirementStep(item) === index).length;
          return <button key={label} type="button" aria-current={step === index ? "step" : undefined}
            onClick={() => onStep(index)} className={"rounded-lg border px-3 py-2 text-left text-xs font-semibold " +
              (step === index ? "border-teal bg-teal-50 text-teal" : "border-line text-slate-600 hover:bg-slate-50")}>
            {index + 1}. {label}{!checking && count > 0 && <span className="ml-1 text-amber-800"> · {count} pend.</span>}
          </button>;
        })}
      </nav>
    </header>
    <div ref={scroll} className="preparation-scroll p-4 sm:p-5">
      {notice && <p role="status" className="mb-3 rounded-lg bg-blue-50 p-3 text-xs leading-5 text-blue-900">{notice}</p>}
      {checking ? <p role="status" className="mb-3 text-sm text-teal">Atualizando as pendências…</p> :
        <div aria-live="polite" className="mb-3 space-y-2">
          {(step === 2 ? pending : pending.filter(item => requirementStep(item) === step)).map(item =>
            <div key={item.detail} className="rounded-lg border border-amber-200 bg-amber-50 p-3 text-xs leading-5">
              <strong>{item.title}</strong><p>{item.detail}</p>
              {step === 2 && <button type="button" className="mt-1 font-bold text-teal underline"
                onClick={() => onStep(requirementStep(item))}>Resolver na etapa {requirementStep(item) + 1}</button>}
            </div>)}
          {ready && <p className="text-xs text-emerald-700">Requisitos atendidos. Você pode revisar e executar.</p>}
        </div>}
      {children}
    </div>
    <footer className="flex items-center justify-between gap-3 border-t border-line p-4">
      <button type="button" disabled={step === 0} onClick={() => onStep(step - 1)}
        className="rounded-lg border border-line px-4 py-2 text-sm font-semibold disabled:opacity-40">Voltar etapa</button>
      <span className="text-xs text-slate-500">{STEPS[step]}</span>
      {step < 2 && <button type="button" onClick={() => onStep(step + 1)}
        className="rounded-lg bg-teal px-4 py-2 text-sm font-bold text-white">Avançar</button>}
    </footer>
  </section>;
}
