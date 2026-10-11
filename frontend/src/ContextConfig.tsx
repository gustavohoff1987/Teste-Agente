import { AlertCircle, CheckCircle2, Clock3, HelpCircle, MapPinned, UsersRound } from "lucide-react";

type Role = "territory" | "period" | "category";
type FieldState = { status: "recognized" | "confirmed" | "proposed" | "unmapped"; column: string };
type Mapping = Partial<Record<Role, string>>;
type SuperiorLevel = "territorio_superior_1" | "territorio_superior_2";

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
  territoryCode?: string;
  codeConfirmed?: boolean;
  onSelectCode: (column: string) => void;
  onConfirmCode: () => void;
  detectedLevels?: {role: string; column: string}[];
  selectedLevels?: Partial<Record<SuperiorLevel, string>>;
  onSelectLevel: (level: SuperiorLevel, column: string) => void;
  periodSources?: string[];
  spatial?: boolean;
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
    <div className="grid gap-4 sm:grid-cols-2">
      {DIMENSIONS.filter(item => !props.spatial || item.role === "territory").map(({ role, heading, question, Icon, description }) => {
        const selected = mapping[role] || "";
        const state = fieldStates?.[role]?.status;
        const established = !!selected && (state === "recognized" || state === "confirmed");
        return <div key={role} className="flex flex-col rounded-[18px] border border-line bg-slate-50/40 p-4 sm:p-5">
          <div className="mb-3 flex items-center justify-between">
            <span className="flex h-10 w-10 items-center justify-center rounded-xl bg-cyan-50 text-teal"><Icon size={20}/></span>
            <span className="text-[11px] font-bold text-slate-400">{question}</span>
          </div>
          <h4 className="text-sm font-bold text-ink">{heading}</h4>
          <details open={!established} className="mt-2">
            <summary className="cursor-pointer text-xs font-semibold text-teal">{selected || "Escolher coluna"} · {established ? "associação identificada (editar)" : "confirmação necessária"}</summary>
          <p className="mt-2 text-xs leading-[1.7] text-slate-600">{description}</p>
          <label className="mt-4 flex flex-col gap-2 text-xs font-semibold text-slate-700">
            Associação sugerida pelo sistema
            <select className="w-full min-w-0 rounded-xl border border-line bg-white px-3 py-3 text-sm font-normal text-ink"
              aria-label={heading}
              value={selected} onChange={e => onSelect(role, e.target.value)}>
              <option value="">Não identificada</option>
              {columns.map(col => <option key={col} value={col}>{col}</option>)}
            </select>
          </label>
          {role === "period" && props.periodSources && <p className="mt-2 text-xs leading-5 text-slate-600">
            Período composto de {props.periodSources.join(" e ")} no formato AAAAMM.
            Os campos originais foram preservados. Confirme se essa é a referência temporal dos dados.
          </p>}
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
          </details>
          {role === "territory" && selected && <div className="mt-4 border-t border-line pt-3">
            <h5 className="text-xs font-bold text-teal">Identificador territorial · {props.codeConfirmed ? "confirmado" : props.territoryCode ? "confirmação pendente" : "não informado"}</h5>
            <p className="my-2 text-xs leading-5 text-slate-600">Se lugares diferentes tiverem o mesmo nome, indique a coluna que diferencia cada unidade territorial.</p>
            <label className="flex flex-col gap-2 text-xs font-semibold text-slate-700">
              Código ou identificador da unidade
              <select className="w-full rounded-xl border border-line bg-white px-3 py-2.5 text-sm font-normal text-ink"
                value={props.territoryCode || ""} onChange={e => props.onSelectCode(e.target.value)}>
                <option value="">Não informado</option>
                {columns.filter(col => col !== selected).map(col => <option key={col} value={col}>{col}</option>)}
              </select>
            </label>
            {props.territoryCode && !props.codeConfirmed && <button type="button"
              onClick={props.onConfirmCode}
              className="mt-3 rounded-lg border border-amber-200 bg-amber-50 px-3 py-2 text-xs font-bold text-amber-900">
              Confirmar identificador territorial
            </button>}
            {props.territoryCode && props.codeConfirmed && <p className="mt-2 text-xs font-semibold text-emerald-700">Código confirmado</p>}
            <details className="mt-4 border-t border-line pt-3">
              <summary className="cursor-pointer text-xs font-bold text-teal">
                Hierarquia territorial · níveis superiores (opcionais)
              </summary>
              <p className="mt-2 text-xs leading-5 text-slate-600">
                O território de análise está contido no superior 1, que está contido no superior 2.
                O sistema reconhece nomes conhecidos; para cabeçalhos diferentes, indique a coluna.
                Isso não autoriza automaticamente somar dados de territórios distintos.
              </p>
              {(["territorio_superior_1", "territorio_superior_2"] as const).map((level, index) => {
                const inferred = props.detectedLevels?.find(item => item.role === level)?.column || "";
                const value = props.selectedLevels?.[level] || inferred;
                return <label key={level} className="mt-3 flex flex-col gap-2 text-xs font-semibold text-slate-700">
                  Território superior {index + 1}
                  <select aria-label={"Território superior " + (index + 1)}
                    className="w-full rounded-xl border border-line bg-white px-3 py-2.5 text-sm font-normal text-ink"
                    value={value} onChange={e => props.onSelectLevel(level, e.target.value)}>
                    <option value="">Não informado</option>
                    {columns.filter(col => col !== selected && col !== props.territoryCode).map(col =>
                      <option key={col} value={col}>{col}</option>)}
                  </select>
                  {inferred && !props.selectedLevels?.[level] && <span className="text-[11px] font-normal text-emerald-700">Reconhecido pelo cabeçalho</span>}
                </label>;
              })}
            </details>
          </div>}
        </div>;
      })}
      {!props.spatial && <div className="flex flex-col rounded-[18px] border border-line bg-slate-50/40 p-4 sm:p-5">
        <div className="mb-3 flex items-center justify-between">
          <span className="flex h-10 w-10 items-center justify-center rounded-xl bg-cyan-50 text-teal"><UsersRound size={20}/></span>
          <span className="text-[11px] font-bold text-slate-400">O quê?</span>
        </div>
        <h4 className="text-sm font-bold text-ink">Objeto de análise</h4>
        <details open={!objectConfirmed} className="mt-2">
          <summary className="cursor-pointer text-xs font-semibold text-teal">{objectConfirmed ? "Objeto confirmado (editar)" : "Identificar e confirmar o objeto"}</summary>
        <p className="mt-2 text-xs leading-[1.7] text-slate-600">
          Indique a profissão, categoria profissional ou conjunto de trabalhadores que deseja analisar ao longo do tempo e nos territórios selecionados.
        </p>
        <label className="mt-4 flex flex-col gap-2 text-xs font-semibold text-slate-700">
          Como a categoria aparece na sua base?
          <select className="w-full min-w-0 rounded-xl border border-line bg-white px-3 py-3 text-sm font-normal text-ink"
            aria-label="Como a categoria aparece na sua base?"
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
        </details>
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
      </div>}
    </div>
    <p className="mt-5 text-xs leading-5 text-slate-500">
      A confirmação não executa cálculos. Cada análise informa separadamente os requisitos que precisa cumprir.
    </p>
  </div>;
}
