import { AlertCircle, CheckCircle2, Clock3, HelpCircle, MapPinned, UsersRound } from "lucide-react";
import { fieldOptions, periodValue, SINGLE_PERIOD } from "./fieldChoices";

type Role = "territory" | "period" | "category";
type Origin = "PERFIL_GOVERNADO" | "REGRA_CONFIGURADA" | "ESCOLHA_DO_USUARIO" | "SUGESTAO_NAO_ESCOLHIDA";
type FieldState = { status: "recognized" | "confirmed" | "proposed" | "unmapped"; column: string; origin?: Origin };
type Mapping = Partial<Record<Role, string>>;
type SuperiorLevel = "territorio_superior_1" | "territorio_superior_2";
export type ObjectState = { status: "reconhecido" | "informado" | "ausente"; origin: string | null };

type Props = {
  columns: string[];
  mapping: Mapping;
  fieldStates?: Partial<Record<Role | "territory_id", FieldState>>;
  suggestions?: Partial<Record<string, string[]>>;
  categories: string[];
  suggestedCategory: string;
  objectDraft: string;
  objectState?: ObjectState;
  onSelect: (role: Role, column: string) => void;
  onDraft: (value: string) => void;
  territoryCode?: string;
  onSelectCode: (column: string) => void;
  singlePeriod: boolean;
  onSinglePeriod: (value: boolean) => void;
  detectedLevels?: {role: string; column: string}[];
  selectedLevels?: Partial<Record<SuperiorLevel, string>>;
  onSelectLevel: (level: SuperiorLevel, column: string) => void;
  periodSources?: string[];
  spatial?: boolean;
};

const ORIGIN_LABEL: Record<Origin, string> = {
  PERFIL_GOVERNADO: "Reconhecida pelo perfil oficial",
  REGRA_CONFIGURADA: "Reconhecida por regra",
  ESCOLHA_DO_USUARIO: "Escolhida por você",
  SUGESTAO_NAO_ESCOLHIDA: "Escolha pendente",
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

/** Situação de um campo: origem do papel (perfil, regra ou escolha), escolha pendente ou coluna a escolher. */
function fieldBadge(selected: string, state?: FieldState) {
  const established = !!selected && (state?.status === "recognized" || state?.status === "confirmed");
  const label = !selected ? "Escolher coluna" : established ? ORIGIN_LABEL[state?.origin || "ESCOLHA_DO_USUARIO"] : ORIGIN_LABEL.SUGESTAO_NAO_ESCOLHIDA;
  return {established, label};
}

export default function ContextConfig(props: Props) {
  const { columns, mapping, fieldStates, suggestions, categories, suggestedCategory, objectDraft, objectState, onSelect, onDraft } = props;
  const objectReady = objectState?.status === "reconhecido" || objectState?.status === "informado";
  return <div id="associacoes" className="section-anchor mt-5 rounded-[22px] border border-line bg-white p-5 shadow-card sm:p-7">
    <div className="mb-6">
      <h3 className="text-lg font-bold text-ink">Configuração da análise</h3>
      <p className="mt-2 max-w-3xl text-sm leading-6 text-slate-600">
        Confira onde, quando e o que deseja analisar. Os campos reconhecidos já vêm escolhidos; as sugestões aparecem no topo
        de cada lista e só valem depois que você as escolher.
      </p>
    </div>
    <div className="grid gap-4 sm:grid-cols-2">
      {DIMENSIONS.filter(item => !props.spatial || item.role === "territory").map(({ role, heading, question, Icon, description }) => {
        const selected = mapping[role] || "";
        const value = role === "period" ? periodValue(selected, props.singlePeriod) : selected;
        const badge = fieldBadge(role === "period" && !selected && props.singlePeriod ? "única" : selected,
          role === "period" && !selected && props.singlePeriod ? {status: "confirmed", column: "", origin: "ESCOLHA_DO_USUARIO"} : fieldStates?.[role]);
        return <div key={role} className="flex flex-col rounded-[18px] border border-line bg-slate-50/40 p-4 sm:p-5">
          <div className="mb-3 flex items-center justify-between">
            <span className="flex h-10 w-10 items-center justify-center rounded-xl bg-cyan-50 text-teal"><Icon size={20}/></span>
            <span className="text-[11px] font-bold text-slate-400">{question}</span>
          </div>
          <h4 className="text-sm font-bold text-ink">{heading}</h4>
          <details open={!badge.established} className="mt-2">
            <summary className="cursor-pointer text-xs font-semibold text-teal">{selected || (value === SINGLE_PERIOD ? "Período único" : "Escolher coluna")} · {badge.label}</summary>
          <p className="mt-2 text-xs leading-[1.7] text-slate-600">{description}</p>
          <label className="mt-4 flex flex-col gap-2 text-xs font-semibold text-slate-700">
            Coluna escolhida
            <select className="w-full min-w-0 rounded-xl border border-line bg-white px-3 py-3 text-sm font-normal text-ink"
              aria-label={heading} data-testid={"context-choice-" + role}
              value={value} onChange={e => {
                if (role === "period" && e.target.value === SINGLE_PERIOD) { onSelect(role, ""); props.onSinglePeriod(true); return; }
                if (role === "period") props.onSinglePeriod(false);
                onSelect(role, e.target.value);
              }}>
              <option value="">Escolher coluna</option>
              {fieldOptions(columns, suggestions, role, {singlePeriod: role === "period", current: selected}).map(option =>
                <option key={option.value} value={option.value}>{option.label}</option>)}
            </select>
          </label>
          {role === "period" && props.periodSources && <p className="mt-2 text-xs leading-5 text-slate-600">
            Composição verificada: {props.periodSources.join(" × 100 + ")} (ano × 100 + mês), no formato AAAAMM.
            Os campos originais foram preservados.
          </p>}
          <div className="mt-3 flex items-center gap-2" aria-live="polite">
            {badge.established
              ? <><CheckCircle2 size={17} className="text-emerald-600"/><span className="text-xs font-semibold text-emerald-700">{badge.label}</span></>
              : selected
                ? <><AlertCircle size={17} className="text-amber-600"/><span className="text-xs font-semibold text-amber-800">{badge.label}</span></>
                : <><HelpCircle size={17} className="text-slate-400"/><span className="text-xs font-medium text-slate-500">Escolher coluna</span></>}
          </div>
          </details>
          {role === "territory" && selected && <div className="mt-4 border-t border-line pt-3">
            <h5 className="text-xs font-bold text-teal">Identificador territorial (opcional) · {props.territoryCode
              ? fieldBadge(props.territoryCode, fieldStates?.territory_id).label : "sem código"}</h5>
            <p className="my-2 text-xs leading-5 text-slate-600">Se lugares diferentes tiverem o mesmo nome, escolha a coluna que diferencia cada unidade territorial.</p>
            <label className="flex flex-col gap-2 text-xs font-semibold text-slate-700">
              Código ou identificador da unidade
              <select aria-label="Código ou identificador da unidade" data-testid="context-choice-territory_id"
                className="w-full rounded-xl border border-line bg-white px-3 py-2.5 text-sm font-normal text-ink"
                value={props.territoryCode || ""} onChange={e => props.onSelectCode(e.target.value)}>
                {fieldOptions(columns.filter(col => col !== selected), suggestions, "territory_id",
                  {optional: true, current: props.territoryCode || ""}).map(option =>
                  <option key={option.value} value={option.value}>{option.label}</option>)}
              </select>
            </label>
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
        <details open={!objectReady} className="mt-2">
          <summary className="cursor-pointer text-xs font-semibold text-teal">{objectState?.status === "reconhecido" ? "Reconhecido pelo catálogo"
            : objectState?.status === "informado" ? "Informado por você" : "Informe o objeto"}</summary>
        <p className="mt-2 text-xs leading-[1.7] text-slate-600">
          Indique a profissão, categoria profissional ou conjunto de trabalhadores que deseja analisar ao longo do tempo e nos territórios selecionados.
        </p>
        <label className="mt-4 flex flex-col gap-2 text-xs font-semibold text-slate-700">
          Como a categoria aparece na sua base?
          <select className="w-full min-w-0 rounded-xl border border-line bg-white px-3 py-3 text-sm font-normal text-ink"
            aria-label="Como a categoria aparece na sua base?" data-testid="context-choice-category"
            value={mapping.category || ""} onChange={e => onSelect("category", e.target.value)}>
            <option value="">Uma categoria para toda a base</option>
            {fieldOptions(columns, suggestions, "category", {current: mapping.category || ""}).map(option =>
              <option key={option.value} value={option.value}>{option.label}</option>)}
          </select>
        </label>
        {mapping.category && <div className="mt-3 rounded-xl border border-cyan-100 bg-white p-3">
          <p className="text-xs font-semibold text-slate-700">Categorias profissionais encontradas</p>
          <p className="mt-1 text-xs leading-5 text-slate-600">
            {categories.length ? categories.slice(0, 5).join(", ") + (categories.length > 5 ? " e outras" : "") :
              "Nenhuma categoria encontrada nesta coluna."}
          </p>
        </div>}
        {(!mapping.category || objectState?.status !== "reconhecido") && <label className="mt-3 flex flex-col gap-2 text-xs font-semibold text-slate-700">
          {mapping.category ? "Objeto de análise (as categorias não são reconhecidas pelo catálogo)" : "Categoria profissional ou conjunto de trabalhadores"}
          <input aria-label="Objeto de análise" data-testid="object-draft"
            className="w-full rounded-xl border border-line bg-white px-3 py-3 text-sm font-normal text-ink"
            value={objectDraft} placeholder="Informe a profissão ou categoria"
            onChange={e => onDraft(e.target.value)}/>
          {!objectDraft && suggestedCategory && <button type="button" onClick={() => onDraft(suggestedCategory)}
            className="self-start rounded-md border border-blue-200 bg-white px-2 py-1 text-xs font-semibold text-teal">
            Usar sugestão: {suggestedCategory}</button>}
        </label>}
        </details>
        <div className="mt-3 flex items-center gap-2" aria-live="polite">
          {objectReady
            ? <><CheckCircle2 size={17} className="text-emerald-600"/><span className="text-xs font-semibold text-emerald-700">
              {objectState?.status === "reconhecido" ? "Reconhecido pelo catálogo" : "Informado por você"}</span></>
            : <><AlertCircle size={17} className="text-amber-600"/><span className="text-xs font-semibold text-amber-800">Informe o objeto</span></>}
        </div>
      </div>}
    </div>
    <p className="mt-5 text-xs leading-5 text-slate-500">
      As escolhas não executam cálculos. Cada análise informa separadamente os requisitos que precisa cumprir.
    </p>
  </div>;
}
