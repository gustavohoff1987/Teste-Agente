import { AlertCircle, CheckCircle2, Clock3, HelpCircle, MapPinned, UsersRound } from "lucide-react";

type Role = "territory" | "period" | "category";
type FieldState = { status: "recognized" | "confirmed" | "proposed" | "unmapped"; column: string };
type Mapping = Partial<Record<Role, string>>;

type Props = {
  columns: string[];
  mapping: Mapping;
  fieldStates?: Partial<Record<Role, FieldState>>;
  categories: string[];
  suggestedCategory: string;
  objectDraft: string;
  objectConfirmed: boolean;
  onSelect: (role: Role, column: string) => void;
  onConfirmRole: (role: Role) => void;
  onDraft: (value: string) => void;
  onConfirmObject: () => void;
};

const DIMENSIONS = [
  {
    role: "territory" as const,
    heading: "Unidade territorial de análise",
    question: "Onde?",
    Icon: MapPinned,
    description: "Indique o território em que deseja analisar a força de trabalho na saúde. Pode ser um município, estado, região geográfica, distrito, província ou outra unidade territorial presente na sua base de dados."
  },
  {
    role: "period" as const,
    heading: "Unidade temporal de análise",
    question: "Quando?",
    Icon: Clock3,
    description: "Indique a referência temporal dos dados que deseja analisar. Ela pode corresponder a anos, meses, competências ou outros períodos, conforme a estrutura da sua base."
  },
];

export default function ContextConfig(props: Props) {
  const { columns, mapping, fieldStates, categories, suggestedCategory,
          objectDraft, objectConfirmed, onSelect, onConfirmRole, onDraft, onConfirmObject } = props;
  return <div id="associacoes" className="section-anchor mt-5 rounded-[22px] border border-line bg-white p-5 shadow-card sm:p-7">
    <div className="mb-6">
      <h3 className="text-lg font-bold text-ink">Configuração da análise</h3>
      <p className="mt-2 max-w-3xl text-sm leading-6 text-slate-600">
        Confira onde, quando e o que deseja analisar. O sistema já sugeriu as associações identificadas na sua base.
        Ajuste somente o que for necessário.
      </p>
    </div>
    <div className="grid gap-4 lg:grid-cols-3">
      {DIMENSIONS.map(({ role, heading, question, Icon, description }) => {
        const selected = mapping[role] || "";
        const state = fieldStates?.[role]?.status;
        const established = !!selected && (state === "recognized" || state === "confirmed");
        return <div key={role} className="flex flex-col rounded-[18px] border border-line bg-slate-50/40 p-4 sm:p-5">
          <div className="mb-3 flex items-center justify-between">
            <span className="flex h-10 w-10 items-center justify-center rounded-xl bg-cyan-50 text-teal"><Icon size={20}/></span>
            <span className="text-[11px] font-bold text-slate-400">{question}</span>
          </div>
          <h4 className="text-sm font-bold text-ink">{heading}</h4>
          <p className="mt-2 text-xs leading-[1.7] text-slate-600 lg:min-h-[118px]">{description}</p>
          <label className="mt-4 flex flex-col gap-2 text-xs font-semibold text-slate-700">
            Associação sugerida pelo sistema
            <select className="w-full min-w-0 rounded-xl border border-line bg-white px-3 py-3 text-sm font-normal text-ink"
              value={selected} onChange={e => onSelect(role, e.target.value)}>
              <option value="">Não identificada</option>
              {columns.map(col => <option key={col} value={col}>{col}</option>)}
            </select>
          </label>
          <div className="mt-3 flex items-center gap-2" aria-live="polite">
            {established
              ? <><CheckCircle2 size={17} className="text-emerald-600"/><span className="text-xs font-semibold text-emerald-700">Associação identificada</span></>
              : selected
                ? <><AlertCircle size={17} className="text-amber-600"/><span className="text-xs font-semibold text-amber-800">Confirmação necessária</span></>
                : <><HelpCircle size={17} className="text-slate-400"/><span className="text-xs font-medium text-slate-500">Aguardando identificação</span></>}
          </div>
          {selected && !established && <button type="button" onClick={() => onConfirmRole(role)}
            className="mt-2 self-start rounded-lg border border-amber-200 bg-amber-50 px-3 py-2 text-xs font-bold text-amber-900 hover:bg-amber-100">
            Confirmar associação
          </button>}
        </div>;
      })}
      <div className="flex flex-col rounded-[18px] border border-line bg-slate-50/40 p-4 sm:p-5">
        <div className="mb-3 flex items-center justify-between">
          <span className="flex h-10 w-10 items-center justify-center rounded-xl bg-cyan-50 text-teal"><UsersRound size={20}/></span>
          <span className="text-[11px] font-bold text-slate-400">O quê?</span>
        </div>
        <h4 className="text-sm font-bold text-ink">Objeto de análise</h4>
        <p className="mt-2 text-xs leading-[1.7] text-slate-600 lg:min-h-[118px]">
          Indique a profissão, categoria profissional ou conjunto de trabalhadores que deseja analisar ao longo do tempo e nos territórios selecionados.
        </p>
        <label className="mt-4 flex flex-col gap-2 text-xs font-semibold text-slate-700">
          Como a categoria aparece na sua base?
          <select className="w-full min-w-0 rounded-xl border border-line bg-white px-3 py-3 text-sm font-normal text-ink"
            value={mapping.category || ""} onChange={e => onSelect("category", e.target.value)}>
            <option value="">Uma categoria para toda a base</option>
            {columns.map(col => <option key={col} value={col}>{col}</option>)}
          </select>
        </label>
        {mapping.category
          ? <div className="mt-3 rounded-xl border border-cyan-100 bg-white p-3">
              <p className="text-xs font-semibold text-slate-700">Categorias profissionais encontradas</p>
              <p className="mt-1 text-xs leading-5 text-slate-600">
                {categories.length ? categories.slice(0, 5).join(", ") + (categories.length > 5 ? " e outras" : "") :
                  "Confirme que essa coluna identifica a profissão ou categoria profissional."}
              </p>
            </div>
          : <label className="mt-3 flex flex-col gap-2 text-xs font-semibold text-slate-700">
              Categoria profissional identificada
              <input className="w-full rounded-xl border border-line bg-white px-3 py-3 text-sm font-normal text-ink"
                value={objectDraft} placeholder="Informe a profissão ou categoria"
                onChange={e => onDraft(e.target.value)}/>
              {!objectDraft && suggestedCategory && <span className="text-xs font-normal text-slate-500">O sistema encontrou uma categoria que pode ser confirmada.</span>}
            </label>}
        <div className="mt-3 flex items-center gap-2" aria-live="polite">
          {objectConfirmed
            ? <><CheckCircle2 size={17} className="text-emerald-600"/><span className="text-xs font-semibold text-emerald-700">Objeto confirmado</span></>
            : <><AlertCircle size={17} className="text-amber-600"/><span className="text-xs font-semibold text-amber-800">Confirmação necessária</span></>}
        </div>
        {!objectConfirmed && <button type="button" onClick={onConfirmObject}
          disabled={!mapping.category && !objectDraft.trim()}
          className="mt-3 self-start rounded-lg bg-teal px-3 py-2 text-xs font-bold text-white hover:bg-ink disabled:opacity-40">
          Confirmar objeto de análise
        </button>}
      </div>
    </div>
    <p className="mt-5 text-xs leading-5 text-slate-500">
      A confirmação não executa cálculos. Cada análise informa separadamente os requisitos que precisa cumprir.
    </p>
  </div>;
}
