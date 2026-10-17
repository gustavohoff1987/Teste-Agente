import { useMemo } from "react";
import { BarChart3, Search } from "lucide-react";
import { ResponsiveContainer, BarChart, Bar, CartesianGrid, Tooltip, XAxis, YAxis } from "recharts";

import { useInvestigationState } from "./InvestigationViewState";
import ResultTable, { type TablePresentation } from "./ResultTable";

type SummaryRow = Record<string, unknown>;
type DetailRow = Record<string, unknown>;
type Props = { summary: SummaryRow[]; detail: DetailRow[]; onExport: (rows: DetailRow[]) => void;
  // Seleção visual compartilhada com o mapa e os gráficos (opcional; sem ela, o comportamento é o anterior).
  highlight?: Set<string>; idOf?: (row: DetailRow) => string | null; onToggle?: (id: string) => void; onlyHighlighted?: boolean;
  onTablePresentation?: (state: TablePresentation) => void };

const fmt = (value: unknown) => {
  if (typeof value === "number") return new Intl.NumberFormat("pt-BR", { maximumFractionDigits: 4 }).format(value);
  return value == null ? "Não informado" : String(value);
};
export const displayPeriod = (value: string): string => {
  if (/^\d{6}$/.test(value)) {
    const month = Number(value.slice(4));
    if (month >= 1 && month <= 12) return value.slice(4) + "/" + value.slice(0, 4);
  }
  return value;
};
const classNumber = (label: unknown) => {
  const match = String(label ?? "").match(/\d+/);
  return match ? Number(match[0]) : 0;
};

export default function DistributionResults({ summary, detail, onExport, highlight, idOf, onToggle, onlyHighlighted, onTablePresentation }: Props) {
  const [chosenGroup, setChosenGroup] = useInvestigationState("distribution.group", "");
  const [search, setSearch] = useInvestigationState("distribution.search", "");
  const metric = String(summary[0]?.Indicador || "Indicador selecionado");
  const period = String(summary[0]?.["Período"] ?? "");
  const category = String(summary[0]?.Categoria ?? "");
  const count = summary.reduce((sum, row) => sum + Number(row.Unidades || 0), 0);
  const groupLabel = summary.length === 4 ? "quartil" : summary.length === 10 ? "decil" :
    summary.length === 5 ? "quintil" : "faixa";
  const pluralLabel = groupLabel === "quartil" ? "quartis" : groupLabel === "quintil" ? "quintis" :
    groupLabel === "decil" ? "decis" : "faixas";
  const positionColumn = groupLabel === "faixa" ? "Posição na faixa" : "Posição no " + groupLabel;
  const filtered = useMemo(() => detail.filter(row => {
    const sameGroup = !chosenGroup || classNumber(row.Quintil) === Number(chosenGroup);
    const chosen = !onlyHighlighted || (!!idOf && !!highlight?.has(idOf(row) || ""));
    return chosen && sameGroup && (!search || String(row.Território).toLocaleLowerCase("pt-BR").includes(search.toLocaleLowerCase("pt-BR")));
  }).sort((a, b) => Number(a["Posição geral"] ?? Infinity) - Number(b["Posição geral"] ?? Infinity) ||
    String(a.Território).localeCompare(String(b.Território), "pt-BR")), [detail, chosenGroup, search, onlyHighlighted, highlight, idOf]);
  const labels = ["Menores valores", "Valores baixos", "Valores intermediários", "Valores altos", "Maiores valores"];
  const ordered = [...summary].sort((a, b) => classNumber(a.Classe) - classNumber(b.Classe));
  const chartData = ordered.map(row => ({
    name: (groupLabel === "decil" ? "D" : groupLabel === "faixa" ? "F" : "Q") + classNumber(row.Classe),
    count: Number(row.Unidades || 0),
  }));

  return <div className="mt-7 space-y-6">
    <div className="rounded-2xl border border-cyan-100 bg-cyan-50/50 p-5">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h4 className="text-base font-bold text-ink">Distribuição das unidades territoriais</h4>
          <p className="mt-1 text-sm text-slate-700">
            {metric} · {category || "Categoria selecionada"} · {displayPeriod(period)}
          </p>
        </div>
        <span className="rounded-xl bg-white px-3 py-2 text-sm font-semibold text-teal">
          {fmt(count)} unidades territoriais avaliadas
        </span>
      </div>
      <p className="mt-3 text-xs leading-6 text-slate-600">
        As unidades foram ordenadas pelo indicador escolhido e divididas em {ordered.length} {pluralLabel}.
        O primeiro grupo reúne os menores valores e o último, os maiores. Valores iguais permanecem juntos,
        por isso a quantidade de unidades em cada grupo pode variar.
      </p>
    </div>
    <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-5">
      {ordered.map((row, index) => {
        const number = classNumber(row.Classe) || index + 1;
        const selected = chosenGroup === String(number);
        return <button key={index} type="button" onClick={() => setChosenGroup(selected ? "" : String(number))}
          aria-pressed={selected}
          className={["rounded-2xl border p-4 text-left transition hover:border-teal focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-teal",
            selected ? "border-teal bg-cyan-50 shadow-sm" : "border-line bg-white"].join(" ")}>
          <span className="block text-xs font-bold text-teal">{number}º {groupLabel}</span>
          <strong className="mt-2 block text-2xl font-bold text-ink">{fmt(row.Unidades)}</strong>
          <span className="mt-1 block text-xs text-slate-600">unidades territoriais</span>
          <span className="mt-2 block text-xs font-semibold leading-4 text-slate-700">{groupLabel === "quintil" ? labels[number - 1] : number === 1 ? "Menores valores" : number === ordered.length ? "Maiores valores" : "Valores intermediários"}</span>
        </button>;
      })}
    </div>
    <div className="rounded-2xl border border-line p-4 sm:p-6">
      <div className="mb-4 flex items-center gap-2"><BarChart3 size={18} className="text-teal"/>
        <h4 className="text-sm font-bold text-ink">Quantas unidades pertencem a cada {groupLabel}?</h4>
      </div>
      <div className="h-[245px] w-full overflow-hidden"><ResponsiveContainer width="100%" height="100%">
        <BarChart data={chartData} margin={{top:5,right:10,bottom:5,left:2}}>
          <CartesianGrid strokeDasharray="3 3" stroke="#e9eff4" vertical={false}/>
          <XAxis dataKey="name" tick={{fontSize:12,fill:"#668094"}}/>
          <YAxis allowDecimals={false} tick={{fontSize:11,fill:"#668094"}} width={58}/>
          <Tooltip formatter={(v: number) => [fmt(v), "Unidades territoriais"]} wrapperStyle={{maxWidth: "calc(100% - 72px)"}} contentStyle={{whiteSpace: "normal"}}/>
          <Bar dataKey="count" name="Unidades territoriais" fill="#15919b" radius={[5,5,0,0]}/>
        </BarChart>
      </ResponsiveContainer></div>
    </div>
    <div id="tabela-resultado" className="overflow-hidden rounded-2xl border border-line">
      <div className="flex flex-wrap items-center justify-between gap-3 border-b border-line px-5 py-4">
        <div><h4 className="text-sm font-bold text-ink">Detalhamento por território</h4>
          <p className="mt-1 text-xs text-slate-500">{fmt(filtered.length)} unidades exibidas · {metric}</p>
        </div>

      </div>
      <div className="no-print grid gap-3 border-b border-line bg-slate-50/60 px-5 py-4 sm:grid-cols-2">
        <label className="flex flex-col gap-1 text-xs font-semibold text-slate-700">
          Filtrar por {groupLabel}
          <select className="rounded-xl border border-line bg-white px-3 py-2.5 text-sm font-normal" value={chosenGroup}
            onChange={e => setChosenGroup(e.target.value)}>
            <option value="">Todos os {pluralLabel}</option>
            {ordered.map((row, i) => <option key={i} value={classNumber(row.Classe)}>{classNumber(row.Classe)}º {groupLabel}</option>)}
          </select>
        </label>
        <label className="flex flex-col gap-1 text-xs font-semibold text-slate-700">
          Buscar unidade territorial
          <span className="relative"><Search size={15} className="absolute left-3 top-3 text-slate-400"/>
          <input value={search} onChange={e => setSearch(e.target.value)} placeholder="Nome do território"
            className="w-full rounded-xl border border-line bg-white py-2.5 pl-9 pr-3 text-sm font-normal"/></span>
        </label>
      </div>
      <ResultTable rows={filtered} columns={[
        {key: "Território", label: "Unidade territorial", render: fmt},
        {key: "Período", render: value => displayPeriod(String(value ?? ""))},
        {key: "Categoria", label: "Categoria profissional", render: fmt},
        {key: "Quintil", label: groupLabel === "faixa" ? "Faixa" : groupLabel[0].toUpperCase() + groupLabel.slice(1), render: fmt},
        {key: positionColumn, render: fmt}, {key: "Posição geral", render: fmt}, {key: metric, render: fmt},
      ]} idOf={idOf} selected={highlight} onToggle={onToggle} onExport={onExport} exportLabel="Exportar territórios (CSV)"
        onPresentation={onTablePresentation}/>
    </div>
  </div>;
}
