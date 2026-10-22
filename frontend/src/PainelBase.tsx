import { useMemo, useState, type DragEvent } from "react";
import { Plus, X } from "lucide-react";
import type { PainelMunicipios } from "./painelApi";
import type { Levels } from "./territorialScope";
import type { Territory } from "./TerritorialSelection";

// Municípios base do painel integrado: o universo (todos, estados inteiros ou municípios avulsos, na mesma forma da abrangência)
// e a lista para acrescentar municípios por busca, clique ou arrastando para dentro do gráfico. A seleção acumula. Cada
// mudança aqui é um pedido explícito ao motor; nada é calculado na tela.

/** Tipo do arrasto de um município da lista para o gráfico. */
export const TIPO_ARRASTO = "application/x-adt-municipio";
const normalizar = (texto: string) => texto.normalize("NFD").replace(/[\u0300-\u036f]/g, "").toLowerCase();
export const nomeDoMunicipio = (item: Territory) => item.name ? item.name + (item.state ? " (" + item.state + ")" : "") : item.label;

type Props = {
  niveis: Levels;
  municipios: Territory[];
  base: PainelMunicipios;
  nomes: Map<string, string>;
  onBase: (proxima: PainelMunicipios) => void;
  onAcrescentar: (id: string) => void;
  desabilitado: boolean;
};

export default function PainelBase({ niveis, municipios, base, nomes, onBase, onAcrescentar, desabilitado }: Props) {
  const [consulta, setConsulta] = useState("");
  const [estado, setEstado] = useState("");
  const estados = niveis.estados;
  const nomeDoEstado = (prefixo: string) => estados.find(item => item.prefixo === prefixo)?.nome || prefixo;
  const achados = useMemo(() => {
    const termo = normalizar(consulta.trim());
    if (!termo && !estado) return [];
    return municipios.filter(item => (!estado || item.state_code === estado) && !item.selection_reason &&
      (!termo || normalizar(item.name + " " + item.code + " " + item.label).includes(termo))).slice(0, 40);
  }, [municipios, consulta, estado]);

  function arrastar(event: DragEvent<HTMLLIElement>, id: string) {
    event.dataTransfer.setData(TIPO_ARRASTO, id);
    event.dataTransfer.setData("text/plain", id);
    event.dataTransfer.effectAllowed = "copy";
  }

  return <section aria-label="Municípios base" data-testid="painel-base" className="space-y-3 rounded-2xl border border-line bg-white p-4">
    <div>
      <h3 className="text-sm font-bold text-ink">Municípios base</h3>
      <p className="mt-1 text-xs leading-5 text-slate-600">O universo do gráfico. O motor devolve os valores de todos; a régua só
        escolhe quais aparecem.</p>
    </div>
    <label className="flex min-h-10 items-start gap-2 text-xs leading-5">
      <input type="checkbox" data-testid="painel-base-todos" className="mt-0.5 h-4 w-4 shrink-0 accent-teal" checked={base.todos}
        disabled={desabilitado} onChange={() => onBase(base.todos ? { todos: false, estados: [], ids: [] } : { todos: true, estados: [], ids: [] })}/>
      <span><strong className="text-ink">Todos os municípios</strong> <span className="text-slate-600">
        ({niveis.municipios.total.toLocaleString("pt-BR")})</span></span>
    </label>
    {!base.todos && <div className="space-y-2">
      <label className="block text-xs font-semibold text-ink" htmlFor="painel-base-estado">Estados inteiros</label>
      <select id="painel-base-estado" data-testid="painel-base-estado" value="" disabled={desabilitado}
        onChange={event => { const prefixo = event.target.value; if (prefixo && !base.estados.includes(prefixo)) onBase({ ...base, estados: [...base.estados, prefixo] }); }}
        className="w-full min-w-0 rounded-lg border border-line bg-white px-2 py-2 text-xs text-ink">
        <option value="">Acrescentar um estado inteiro…</option>
        {estados.filter(item => !base.estados.includes(item.prefixo)).map(item =>
          <option key={item.prefixo} value={item.prefixo}>{item.nome} ({item.sigla}) · {item.municipios.toLocaleString("pt-BR")} municípios</option>)}
      </select>
      {base.estados.length > 0 && <ul className="flex flex-wrap gap-1.5" aria-label="Estados inteiros no gráfico">
        {base.estados.map(prefixo => <li key={prefixo} data-testid="painel-base-chip" data-id={"uf:" + prefixo}
          className="inline-flex items-center gap-1 rounded-full border border-teal bg-cyan-50 py-0.5 pl-2.5 pr-1 text-xs font-semibold text-ink">
          {nomeDoEstado(prefixo)}
          <button type="button" aria-label={"Retirar " + nomeDoEstado(prefixo) + " do gráfico"} disabled={desabilitado}
            onClick={() => onBase({ ...base, estados: base.estados.filter(item => item !== prefixo) })}
            className="inline-flex h-6 w-6 items-center justify-center rounded-full hover:bg-white"><X size={13} aria-hidden="true"/></button>
        </li>)}
      </ul>}
    </div>}
    <div className="space-y-2 border-t border-line pt-3">
      <p className="text-xs font-semibold text-ink">Acrescentar municípios</p>
      <div className="grid gap-2 sm:grid-cols-2 lg:grid-cols-1">
        <label className="text-xs text-slate-700">Nome ou código
          <input type="search" data-testid="painel-busca" value={consulta} onChange={event => setConsulta(event.target.value)}
            disabled={desabilitado} placeholder="Ex.: Tefé ou 130420"
            className="mt-1 block w-full min-w-0 rounded-lg border border-line bg-white px-2 py-2 text-sm text-ink"/>
        </label>
        <label className="text-xs text-slate-700">Listar os municípios de
          <select value={estado} onChange={event => setEstado(event.target.value)} disabled={desabilitado} data-testid="painel-lista-estado"
            className="mt-1 block w-full min-w-0 rounded-lg border border-line bg-white px-2 py-2 text-sm text-ink">
            <option value="">Escolha um estado</option>
            {estados.map(item => <option key={item.prefixo} value={item.prefixo}>{item.nome} ({item.sigla})</option>)}
          </select>
        </label>
      </div>
      {achados.length > 0 ? <ul data-testid="painel-lista" aria-label="Municípios para acrescentar"
        className="max-h-60 space-y-1 overflow-y-auto rounded-lg border border-line bg-slate-50 p-1.5">
        {achados.map(item => {
          const nome = nomeDoMunicipio(item);
          return <li key={item.id} draggable={!desabilitado} onDragStart={event => arrastar(event, item.id)} data-testid="painel-lista-item"
            data-id={item.id} title="Clique para acrescentar ou arraste para dentro do gráfico" className="cursor-grab">
            <button type="button" disabled={desabilitado} onClick={() => onAcrescentar(item.id)} aria-label={"Acrescentar " + nome + " ao gráfico"}
              className="flex min-h-9 w-full items-center gap-2 rounded-md bg-white px-2 py-1.5 text-left text-xs text-ink hover:bg-cyan-50 disabled:opacity-40">
              <Plus size={14} aria-hidden="true" className="shrink-0 text-teal"/><span className="min-w-0 flex-1 truncate">{nome}</span>
              <span className="shrink-0 text-[11px] text-slate-500">{item.code}</span>
            </button>
          </li>;
        })}
      </ul> : <p className="text-[11px] leading-4 text-slate-600">{consulta.trim() || estado ? "Nenhum município encontrado."
        : "Digite um nome ou código, ou escolha um estado, para listar municípios. Clique para acrescentar ou arraste para dentro do gráfico."}</p>}
      {base.ids.length > 0 && <ul className="flex flex-wrap gap-1.5" aria-label="Municípios acrescentados">
        {base.ids.map(id => <li key={id} data-testid="painel-base-chip" data-id={id}
          className="inline-flex items-center gap-1 rounded-full border border-line bg-white py-0.5 pl-2.5 pr-1 text-xs text-ink">
          {nomes.get(id) || id}
          <button type="button" aria-label={"Retirar " + (nomes.get(id) || id) + " do gráfico"} disabled={desabilitado}
            onClick={() => onBase({ ...base, ids: base.ids.filter(item => item !== id) })}
            className="inline-flex h-6 w-6 items-center justify-center rounded-full hover:bg-slate-100"><X size={13} aria-hidden="true"/></button>
        </li>)}
      </ul>}
    </div>
  </section>;
}
