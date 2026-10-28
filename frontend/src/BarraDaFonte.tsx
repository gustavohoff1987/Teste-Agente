import { useState, type ReactNode } from "react";
import { Columns3, LoaderCircle, RefreshCw, X } from "lucide-react";

// Barra da fonte no alto da página única (22/10/2026): o resumo da fonte em uso, com "Trocar" (e, numa planilha, "Colunas").
// Desde 23/10/2026, as entradas dos dados (Dados do Brasil, Enviar meus dados e o modelo de planilha XLSX) ficam só na área
// central e na conversa: "Trocar" leva a escolha para a área central. A troca só vale quando a nova fonte fica pronta: até lá, o
// gráfico continua com a fonte em uso, e "Cancelar" desiste. Aqui também ficam a leitura, a escolha da aba de uma planilha com
// várias abas, os erros da leitura e o painel "Colunas" (children).

/** Identidade técnica da base do Brasil (sem conteúdo), para o "Diagnóstico técnico da fonte". */
export type CatalogoDaFonte = { modo: string; versao: string; versao_fixada?: string | null; integridade: string;
  complemento_geografico?: { estado: string; versao?: string; token: string } };

type Props = {
  desabilitado: boolean;
  ativa: { tipo: "brasil" | "arquivo"; resumo: string } | null;
  /** "Trocar" pedido: a escolha está na área central (o botão some até ela terminar ou ser cancelada). */
  escolhendo: boolean;
  preparo: { tipo: "brasil" | "arquivo"; nome: string; lendo: boolean; erro: string; abas: string[] | null; aba: string;
    colunas: boolean } | null;
  catalogo: CatalogoDaFonte | null;
  apiBase: string;
  onTrocar: () => void;
  onCancelar: () => void;
  onAba: (aba: string) => void;
  onColunas?: () => void;
  children?: ReactNode;
};

const BOTAO = "inline-flex min-h-10 items-center gap-2 rounded-xl px-3 py-2 text-sm font-semibold transition disabled:opacity-40";

export default function BarraDaFonte({ desabilitado, ativa, escolhendo, preparo, catalogo, apiBase, onTrocar,
  onCancelar, onAba, onColunas, children }: Props) {
  const [diagnostico, setDiagnostico] = useState<Record<string, unknown> | null>(null);
  // Antes dos dados e sem leitura em curso, a barra não aparece: as entradas estão na área central e na conversa.
  if (!ativa && !preparo) return null;
  return <section className="fonte-barra" aria-label="Fonte dos dados" data-testid="fonte-barra">
    {ativa && <div className="fonte-atual">
      <span className="fonte-rotulo">Fonte</span>
      <p data-testid="current-source" className="fonte-resumo">{ativa.resumo}</p>
      {!escolhendo && !preparo && <div className="no-print flex flex-wrap gap-2">
        <button type="button" data-testid="fonte-trocar" onClick={onTrocar} disabled={desabilitado}
          className={BOTAO + " border border-teal bg-white text-teal-texto hover:bg-cyan-50"}><RefreshCw size={15} aria-hidden="true"/>Trocar</button>
        {onColunas && <button type="button" data-testid="colunas-abrir" onClick={onColunas} disabled={desabilitado}
          className={BOTAO + " border border-line bg-white text-ink hover:bg-slate-50"}><Columns3 size={15} aria-hidden="true"/>Colunas</button>}
      </div>}
    </div>}
    {preparo && <div className="fonte-preparo" data-testid="fonte-preparo">
      {preparo.lendo && <p role="status" className="flex items-center gap-2 text-sm text-teal-texto">
        <LoaderCircle size={16} className="animate-spin" aria-hidden="true"/>
        {preparo.tipo === "brasil" ? "Preparando os dados do Brasil…" : "Lendo " + preparo.nome + "…"}</p>}
      {preparo.erro && <p role="alert" data-testid="fonte-erro" className="text-sm text-rose-800">{preparo.erro}</p>}
      {preparo.abas && <label className="flex flex-wrap items-center gap-2 text-sm text-slate-700">Qual aba deseja utilizar?
        <select aria-label="Qual aba deseja utilizar?" data-testid="fonte-aba" value={preparo.aba} disabled={preparo.lendo}
          onChange={event => onAba(event.target.value)} className="rounded-lg border border-line bg-white px-2 py-1.5">
          <option value="">Selecione uma aba</option>
          {preparo.abas.map(nome => <option key={nome} value={nome}>{nome}</option>)}
        </select>
      </label>}
      {children}
      {!preparo.lendo && <button type="button" data-testid="fonte-cancelar-preparo" onClick={onCancelar}
        className={BOTAO + " no-print text-slate-600 hover:bg-slate-100"}><X size={15} aria-hidden="true"/>
        {ativa ? "Cancelar e continuar com a fonte em uso" : "Cancelar"}</button>}
    </div>}
    {ativa?.tipo === "brasil" && catalogo && !preparo && <details className="fonte-diagnostico no-print"
      onToggle={event => { if (event.currentTarget.open) void fetch(apiBase + "/api/brazil/source").then(resposta => resposta.json())
        .then(setDiagnostico).catch(() => setDiagnostico(null)); }}>
      <summary className="cursor-pointer">Diagnóstico técnico da fonte</summary>
      <p>Origem: {catalogo.modo === "repositorio" ? "arquivos versionados no repositório" : "pasta externa configurada"} · versão{" "}
        {catalogo.versao.slice(0, 12)} · integridade {catalogo.integridade}{catalogo.versao_fixada ? " · versão fixada explicitamente" : ""}
        {catalogo.complemento_geografico && " · camada geográfica complementar: " + catalogo.complemento_geografico.estado +
          (catalogo.complemento_geografico.versao ? " (versão " + catalogo.complemento_geografico.versao + ")" : "")}</p>
      {diagnostico && <pre tabIndex={0} aria-label="Origem física e identidade da base"
        className="mt-1 max-h-40 overflow-auto whitespace-pre-wrap break-all">{JSON.stringify(diagnostico, null, 2)}</pre>}
    </details>}
  </section>;
}
