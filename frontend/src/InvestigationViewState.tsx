import { createContext, useContext, useState, type Dispatch, type SetStateAction } from "react";

// Uma pequena bolsa de controles por resultado; não contém linhas nem cópias dos resultados.
export type ViewMemory = Record<string, unknown>;
export const InvestigationViewState = createContext<ViewMemory | null>(null);

export function useInvestigationState<T>(key: string, initial: T | (() => T)): [T, Dispatch<SetStateAction<T>>] {
  const memory = useContext(InvestigationViewState);
  const [value, setValue] = useState<T>(() => memory && key in memory ? memory[key] as T :
    typeof initial === "function" ? (initial as () => T)() : initial);
  const update: Dispatch<SetStateAction<T>> = action => setValue(previous => {
    const next = typeof action === "function" ? (action as (p: T) => T)(previous) : action;
    if (memory) memory[key] = next;
    return next;
  });
  return [value, update];
}
