import { Play } from "lucide-react";
import { fieldOptions } from "./fieldChoices";
import { PAPEIS, REFERENCIAIS, SEPARADORES, UNIDADES_DE_CONTAGEM, editarRotulo, escolherColuna, type Disponibilidade,
  type EscolhasDaPlanilha } from "./paginaUnica";

// Painel "Colunas" de uma planilha enviada (22/10/2026). A estrutura é a da base do Brasil, com os nomes que a planilha usar
// (distrito, condado, província…): unidade territorial, código, grupo territorial (a coluna-mãe), período, categoria,
// quantidade, população, latitude, longitude e identificador individual. As colunas reconhecidas por regra já vêm escolhidas;
// as sugestões aparecem no topo de cada lista, com "(sugerida)", e nunca são usadas sem a escolha da pessoa (D1). A pessoa
// também diz o que a quantidade conta, o referencial das coordenadas (só SIRGAS 2000 é admitido) e como se chamam as unidades
// e os grupos. Abaixo, o que a planilha permite, pelo pré-exame do backend. Nada é calculado aqui.

type Props = {
  colunas: string[];
  sugestoes: Partial<Record<string, string[]>>;
  escolhas: EscolhasDaPlanilha;
  disponibilidade: Disponibilidade[];
  pedirSeparador: boolean;
  conferindo: boolean;
  erro: string;
  pendencias: string[] | null;
  /** Planilha já em uso: o botão aplica as colunas, e a análise recomeça com elas. */
  emUso: boolean;
  onEscolhas: (proximas: EscolhasDaPlanilha) => void;
  onComecar: () => void;
};

const CAMPO = "w-full min-w-0 rounded-lg border border-line bg-white px-2 py-1.5 text-sm text-ink";

export default function ColunasDaPlanilha({ colunas, sugestoes, escolhas, disponibilidade, pedirSeparador, conferindo, erro,
  pendencias, emUso, onEscolhas, onComecar }: Props) {
  const { mapeamento, rotulos } = escolhas;
  const coordenadas = !!mapeamento.latitude && !!mapeamento.longitude;
  const nome = (qual: "unidade" | "grupo", forma: "singular" | "plural", rotulo: string) =>
    <label className="colunas-campo">
      <span>{rotulo}</span>
      <input aria-label={rotulo} data-testid={"colunas-" + qual + "-" + forma} className={CAMPO}
        value={(qual === "unidade" ? rotulos.unidade : rotulos.grupo)?.[forma] ?? ""}
        onChange={event => onEscolhas(editarRotulo(escolhas, qual, forma, event.target.value))}/>
    </label>;
  return <section className="colunas-painel" aria-labelledby="colunas-titulo" data-testid="colunas-painel">
    <h2 id="colunas-titulo" className="text-base font-bold text-ink">Colunas</h2>
    <p className="mt-1 text-xs leading-5 text-slate-600">Confira a coluna de cada campo. As sugestões aparecem no topo de cada
      lista, marcadas “(sugerida)”, e só valem depois da sua escolha. Os campos com * são necessários.</p>
    <div className="colunas-grade mt-3">
      {PAPEIS.map(({ papel, rotulo, ajuda, obrigatorio, vazio }) => {
        const valor = mapeamento[papel] || "";
        return <label key={papel} className="colunas-campo" data-testid={"colunas-campo-" + papel}>
          <span>{rotulo}{obrigatorio ? " *" : ""}</span>
          <select aria-label={rotulo} data-testid={"colunas-" + papel} value={valor} className={CAMPO}
            onChange={event => onEscolhas(escolherColuna(escolhas, papel, event.target.value))}>
            <option value="">{vazio}</option>
            {fieldOptions(colunas, sugestoes, papel, { current: valor }).map(opcao =>
              <option key={opcao.value} value={opcao.value}>{opcao.label}</option>)}
          </select>
          <small>{ajuda}</small>
        </label>;
      })}
      {mapeamento.count && <label className="colunas-campo" data-testid="colunas-campo-unidade-de-contagem">
        <span>O que a quantidade conta? *</span>
        <select aria-label="O que a quantidade conta?" data-testid="colunas-unidade-de-contagem" className={CAMPO}
          value={escolhas.unidadeDeContagem} onChange={event => onEscolhas({ ...escolhas, unidadeDeContagem: event.target.value })}>
          <option value="">Escolher</option>
          {UNIDADES_DE_CONTAGEM.map(([valor, texto]) => <option key={valor} value={valor}>{texto}</option>)}
        </select>
        {escolhas.unidadeDeContagem === "outro" && <input aria-label="Qual é a unidade de contagem?" data-testid="colunas-unidade-texto"
          className={CAMPO + " mt-1"} placeholder="Por exemplo: equipes" value={escolhas.textoDaUnidade}
          onChange={event => onEscolhas({ ...escolhas, textoDaUnidade: event.target.value })}/>}
      </label>}
    </div>
    {coordenadas && <fieldset className="colunas-bloco" data-testid="colunas-coordenadas">
      <legend>Coordenadas</legend>
      <div className="colunas-grade">
        <label className="colunas-campo">
          <span>Referencial das coordenadas</span>
          <select aria-label="Referencial das coordenadas" data-testid="colunas-referencial" className={CAMPO} value={escolhas.referencial}
            onChange={event => onEscolhas({ ...escolhas, referencial: event.target.value })}>
            <option value="">Escolher</option>
            {REFERENCIAIS.map(([valor, texto]) => <option key={valor} value={valor}>{texto}</option>)}
          </select>
        </label>
        {pedirSeparador && <label className="colunas-campo">
          <span>Separador decimal das coordenadas</span>
          <select aria-label="Separador decimal das coordenadas" data-testid="colunas-separador" className={CAMPO} value={escolhas.separador}
            onChange={event => onEscolhas({ ...escolhas, separador: event.target.value })}>
            <option value="">Escolher</option>
            {SEPARADORES.map(([valor, texto]) => <option key={valor} value={valor}>{texto}</option>)}
          </select>
        </label>}
      </div>
      <p className="mt-1 text-[11px] leading-4 text-slate-600">Só o referencial SIRGAS 2000 é admitido. Com outro, ou sem saber qual é,
        a análise espacial fica indisponível: nada é presumido.</p>
    </fieldset>}
    <fieldset className="colunas-bloco" data-testid="colunas-nomes">
      <legend>Nomes</legend>
      <p className="text-[11px] leading-4 text-slate-600">Como se chamam as unidades{rotulos.grupo ? " e os grupos" : ""} desta planilha?
        Os nomes aparecem nos textos do gráfico e da conversa.</p>
      <div className="colunas-grade mt-1">
        {nome("unidade", "singular", "Unidade, no singular")}
        {nome("unidade", "plural", "Unidades, no plural")}
        {rotulos.grupo && nome("grupo", "singular", "Grupo, no singular")}
        {rotulos.grupo && nome("grupo", "plural", "Grupos, no plural")}
      </div>
    </fieldset>
    <div className="colunas-bloco" data-testid="colunas-disponibilidade" aria-live="polite">
      <h3 className="text-sm font-bold text-ink">O que esta planilha permite</h3>
      {conferindo ? <p role="status" className="text-xs text-teal">Conferindo as colunas…</p>
        : erro ? <p role="alert" className="text-xs text-rose-800">{erro}</p>
        : <ul className="mt-1 space-y-0.5 text-xs leading-5 text-slate-700">
          {disponibilidade.map(item => <li key={item.familia} data-testid={"colunas-disponibilidade-" + item.familia}
            data-disponivel={item.disponivel ? "true" : "false"}>
            <strong className="font-semibold text-ink">{item.rotulo}:</strong> {item.disponivel ? "disponível" : "indisponível. " + item.motivo}
          </li>)}
        </ul>}
    </div>
    {!!pendencias?.length && <div role="alert" data-testid="colunas-pendencias" className="mt-3 rounded-lg border border-amber-200 bg-amber-50 px-3 py-2 text-xs text-amber-900">
      <p className="font-semibold">Falta escolher:</p>
      <ul className="mt-1 list-disc pl-5">{pendencias.map(item => <li key={item}>{item}</li>)}</ul>
    </div>}
    <button type="button" data-testid="colunas-comecar" onClick={onComecar}
      className="mt-3 inline-flex min-h-10 items-center gap-2 rounded-xl bg-ink px-4 py-2 text-sm font-semibold text-white hover:bg-[#1d4d71]">
      <Play size={15} aria-hidden="true"/>{emUso ? "Aplicar as colunas" : "Começar a análise"}</button>
  </section>;
}
