import TerritorialSelection, {type Territory} from "./TerritorialSelection";

export type ReferenceMode = "" | "list" | "criterion";
// Mesmos operadores do motor; nenhum é pré-selecionado e nenhum valor é sugerido.
const OPERATORS = [[">=", "≥ maior ou igual a"], [">", "> maior que"], ["<=", "≤ menor ou igual a"],
  ["<", "< menor que"], ["=", "= igual a"], ["!=", "≠ diferente de"]];

export default function ReferenceSetup(p: {
  mode: ReferenceMode; onMode: (mode: ReferenceMode) => void;
  items: Territory[]; reason?: string; referenceIds: string[]; onReferenceIds: (ids: string[]) => void;
  operator: string; onOperator: (operator: string) => void; value: string; onValue: (value: string) => void;
  showDecimal: boolean; numberFormat?: string; onNumberFormat: (format: string) => void; disabled: boolean;
}) {
  return <fieldset aria-label="Definição das referências" className="min-w-0 space-y-3 rounded-xl border border-amber-300 bg-amber-50/30 p-3 text-sm leading-6">
    <legend className="px-1 text-xs font-semibold text-amber-900">Referências territoriais</legend>
    <p className="text-xs leading-5 text-slate-600">Para cada município-alvo, será indicada a referência geograficamente mais próxima
      entre as que você definir. O sistema não escolhe nem sugere referências.</p>
    <div role="radiogroup" aria-label="Como definir as referências" className="flex flex-wrap gap-x-4 gap-y-1 text-xs">
      <label className="flex min-h-9 items-center gap-2"><input type="radio" name="reference-mode" checked={p.mode === "list"}
        disabled={p.disabled} onChange={() => p.onMode("list")}/>Lista de municípios por nome ou código</label>
      <label className="flex min-h-9 items-center gap-2"><input type="radio" name="reference-mode" checked={p.mode === "criterion"}
        disabled={p.disabled} onChange={() => p.onMode("criterion")}/>Critério simples de densidade</label>
    </div>
    {p.mode === "list" && <TerritorialSelection tone="amber" label="Seleção de referências" title="Municípios de referência"
      listLabel="Referências selecionadas"
      description="Um município pode ser alvo e referência ao mesmo tempo; nesse caso, a distância é zero e fica registrada."
      items={p.items} selected={p.referenceIds} onChange={p.onReferenceIds} disabled={p.disabled} reason={p.reason}/>}
    {p.mode === "criterion" && <div className="space-y-2 text-xs">
      <div className="flex flex-wrap items-end gap-2">
        <span className="pb-2 font-semibold text-ink">Densidade por 1.000 habitantes</span>
        <label className="flex flex-col gap-1">Operador
          <select aria-label="Operador do critério" value={p.operator} disabled={p.disabled}
            onChange={e => p.onOperator(e.target.value)} className="rounded-lg border border-amber-300 bg-white px-2 py-2 text-sm">
            <option value="">Escolher</option>{OPERATORS.map(([value, label]) => <option key={value} value={value}>{label}</option>)}
          </select>
        </label>
        <label className="flex flex-col gap-1">Valor
          <input aria-label="Valor do critério" inputMode="decimal" maxLength={32} value={p.value} disabled={p.disabled}
            onChange={e => p.onValue(e.target.value)} placeholder="por 1.000 habitantes"
            className="w-40 rounded-lg border border-amber-300 bg-white px-2 py-2 text-sm"/>
        </label>
      </div>
      <p className="leading-5 text-slate-600">O critério é aplicado à competência e à categoria escolhidas, com comparação exata e sem
        arredondamento. Municípios sem dados para o critério ficam listados à parte; a condição não tem caráter normativo.</p>
    </div>}
    {p.showDecimal && <label className="flex flex-wrap items-center gap-2 text-xs">Separador decimal das coordenadas
      <select aria-label="Separador decimal das coordenadas" value={p.numberFormat || ""} disabled={p.disabled}
        onChange={e => p.onNumberFormat(e.target.value)} className="rounded-lg border border-amber-300 bg-white px-2 py-1.5 text-sm">
        <option value="">Escolher</option><option value="decimal_comma">Vírgula</option><option value="decimal_point">Ponto</option>
      </select>
    </label>}
  </fieldset>;
}
