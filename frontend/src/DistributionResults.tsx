import { useMemo, useState } from "react";
import { BarChart3, Download, Search } from "lucide-react";
import { ResponsiveContainer, BarChart, Bar, CartesianGrid, Tooltip, XAxis, YAxis } from "recharts";

type SummaryRow = Record<string, unknown>;
type DetailRow = Record<string, unknown>;
type Props = { summary: SummaryRow[]; detail: DetailRow[]; onExport: (rows: DetailRow[]) => void;
  // Seleção visual compartilhada com o mapa e os gráficos (opcional; sem ela, o comportamento é o anterior).
  highlight?: Set<string>; idOf?: (row: DetailRow) => string | null; onToggle?: (id: string) => void; onlyHighlighted?: boolean };

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
const quintileNumber = (label: unknown) => {
  const text = String(label ?? "");
  const match = text.match(/^(?:Q|)([1-9])(?:º|ª|$)/);
  return match ? Number(match[1]) : 0;
};

export default function DistributionResults({ summary, detail, onExport, highlight, idOf, onToggle, onlyHighlighted }: Props) {
  const [chosenQuintile, setChosenQuintile] = useState("");
  const [search, setSearch] = useState("");
  const metric = String(summary[0]?.Indicador || "Indicador selecionado");
  const period = String(summary[0]?.["Período"] ?? "");
  const category = String(summary[0]?.Categoria ?? "");
  const count = summary.reduce((sum, row) => sum + Number(row.Unidades || 0), 0);
  const filtered = useMemo(() => detail.filter(row => {
    const sameQuintile = !chosenQuintile || String(row.Quintil).startsWith(chosenQuintile + "º");
    const chosen = !onlyHighlighted || (!!idOf && !!highlight?.has(idOf(row) || ""));
    return chosen && sameQuintile && (!search || String(row.Território).toLocaleLowerCase("pt-BR").includes(search.toLocaleLowerCase("pt-BR")));
  }), [detail, chosenQuintile, search, onlyHighlighted, highlight, idOf]);
  const labels = ["Menores valores", "Valores baixos", "Valores intermediários", "Valores altos", "Maiores valores"];
  const ordered = [...summary].sort((a, b) => quintileNumber(a.Classe) - quintileNumber(b.Classe));
  const chartData = ordered.map(row => ({
    name: "Q" + quintileNumber(row.Classe),
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
        As unidades foram ordenadas pelo indicador escolhido e classificadas em cinco quintis:
        Q1 reúne os menores valores e Q5 os maiores. Valores iguais permanecem juntos,
        por isso a quantidade de unidades em cada grupo pode variar.
      </p>
    </div>
    <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-5">
      {ordered.map((row, index) => {
        const number = quintileNumber(row.Classe) || index + 1;
        const selected = chosenQuintile === String(number);
        return <button key={index} type="button" onClick={() => setChosenQuintile(selected ? "" : String(number))}
          aria-pressed={selected}
          className={["rounded-2xl border p-4 text-left transition hover:border-teal focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-teal",
            selected ? "border-teal bg-cyan-50 shadow-sm" : "border-line bg-white"].join(" ")}>
          <span className="block text-xs font-bold text-teal">{number}º quintil</span>
          <strong className="mt-2 block text-2xl font-bold text-ink">{fmt(row.Unidades)}</strong>
          <span className="mt-1 block text-xs text-slate-600">unidades territoriais</span>
          <span className="mt-2 block text-xs font-semibold leading-4 text-slate-700">{labels[number - 1] || String(row.Quintil || "Faixa")}</span>
        </button>;
      })}
    </div>
    <div className="rounded-2xl border border-line p-4 sm:p-6">
      <div className="mb-4 flex items-center gap-2"><BarChart3 size={18} className="text-teal"/>
        <h4 className="text-sm font-bold text-ink">Quantas unidades pertencem a cada quintil?</h4>
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
        <button type="button" className="no-print inline-flex items-center gap-2 rounded-lg border border-line px-3 py-2 text-xs font-bold text-teal hover:bg-cyan-50"
          onClick={() => onExport(filtered)} disabled={!filtered.length}><Download size={15}/> Exportar territórios (CSV)</button>
      </div>
      <div className="no-print grid gap-3 border-b border-line bg-slate-50/60 px-5 py-4 sm:grid-cols-2">
        <label className="flex flex-col gap-1 text-xs font-semibold text-slate-700">
          Filtrar pelo quintil
          <select className="rounded-xl border border-line bg-white px-3 py-2.5 text-sm font-normal" value={chosenQuintile}
            onChange={e => setChosenQuintile(e.target.value)}>
            <option value="">Todos os quintis</option>
            {[1,2,3,4,5].map(i => <option key={i} value={i}>{i}º quintil — {labels[i-1]}</option>)}
          </select>
        </label>
        <label className="flex flex-col gap-1 text-xs font-semibold text-slate-700">
          Buscar unidade territorial
          <span className="relative"><Search size={15} className="absolute left-3 top-3 text-slate-400"/>
          <input value={search} onChange={e => setSearch(e.target.value)} placeholder="Nome do território"
            className="w-full rounded-xl border border-line bg-white py-2.5 pl-9 pr-3 text-sm font-normal"/></span>
        </label>
      </div>
      <div className="max-h-[480px] overflow-auto">
        <table className="data-table w-full">
          <thead className="sticky top-0 bg-slate-50"><tr>
            <th>Unidade territorial</th><th>Período</th><th>Categoria profissional</th><th>Quintil</th><th>{metric}</th>
          </tr></thead>
          <tbody>{filtered.slice(0,150).map((row,i) => {
            const id = idOf?.(row) || null, chosen = !!id && !!highlight?.has(id);
            return <tr key={i} aria-selected={onToggle && id ? chosen : undefined} tabIndex={onToggle && id ? 0 : undefined}
              onClick={onToggle && id ? () => onToggle(id) : undefined}
              onKeyDown={onToggle && id ? event => { if (event.key === "Enter" || event.key === " ") { event.preventDefault(); onToggle(id); } } : undefined}
              className={(onToggle && id ? "cursor-pointer " : "") + (chosen ? "bg-blue-50 outline outline-1 outline-blue-300" : "")}>
            <td>{fmt(row.Território)}</td><td>{displayPeriod(String(row["Período"] || ""))}</td>
            <td>{fmt(row.Categoria)}</td><td>{fmt(row.Quintil)}</td><td>{fmt(row[metric])}</td>
          </tr>;})}</tbody>
        </table>
      </div>
      {filtered.length > 150 && <p className="border-t border-line px-5 py-3 text-xs text-slate-500">
        Exibindo as primeiras 150 unidades na tela. O CSV exporta todas as {fmt(filtered.length)} unidades do filtro.
      </p>}
    </div>
  </div>;
}
