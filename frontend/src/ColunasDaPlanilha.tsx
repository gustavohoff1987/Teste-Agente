import { Play } from "lucide-react";
import { fieldOptions } from "./fieldChoices";
import { ARTIGOS_DO_TODO, PAPEIS, REFERENCIAIS, SEPARADORES, UNIDADES_DE_CONTAGEM, editarGenero, editarRotulo, editarTodo,
  escolherColuna, type Disponibilidade, type EscolhasDaPlanilha } from "./paginaUnica";
import { generoDe } from "./painelModel";

// Painel "Colunas" de uma planilha enviada (22/10/2026). A estrutura é a da base do Brasil, com os nomes que a planilha usar
// (distrito, condado, província…): unidade territorial, código, grupo territorial (a coluna-mãe), período, categoria,
// quantidade, população, latitude, longitude e identificador individual. As colunas reconhecidas por regra já vêm escolhidas;
// as sugestões aparecem no topo de cada lista, com "(sugerida)", e nunca são usadas sem a escolha da pessoa (D1). A pessoa
// também diz o que a quantidade conta, o referencial em que as coordenadas foram coletadas (SIRGAS 2000 ou WGS 84, sem
// conversão de um no outro) e como se chamam as unidades e os grupos. Abaixo, o que a planilha permite, pelo pré-exame do
// backend. Nada é calculado aqui.

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
  // Os nomes editáveis: a unidade, o grupo e, desde 07/11/2026 (item 1 do comando), o grupo de cima (test id "grupo-superior").
  type Qual = "unidade" | "grupo" | "grupo_superior";
  const doNome = (qual: Qual) => qual === "unidade" ? rotulos.unidade : qual === "grupo" ? rotulos.grupo : rotulos.grupo_superior;
  const testid = (qual: Qual) => qual.replace("_", "-");
  const nome = (qual: Qual, forma: "singular" | "plural", rotulo: string) =>
    <label className="colunas-campo">
      <span>{rotulo}</span>
      <input aria-label={rotulo} data-testid={"colunas-" + testid(qual) + "-" + forma} className={CAMPO}
        value={doNome(qual)?.[forma] ?? ""}
        onChange={event => onEscolhas(editarRotulo(escolhas, qual, forma, event.target.value))}/>
    </label>;
  // O gênero (07/11/2026, item 1 do comando): o escolhido ou o da terminação, para a concordância ("a comuna", "o distrito").
  const genero = (qual: Qual, rotulo: string) => {
    const atual = doNome(qual);
    return atual && <label className="colunas-campo">
      <span>{rotulo}</span>
      <select aria-label={rotulo} data-testid={"colunas-" + testid(qual) + "-genero"} className={CAMPO} value={atual.genero ?? generoDe(atual)}
        onChange={event => onEscolhas(editarGenero(escolhas, qual, event.target.value === "f" ? "f" : "m"))}>
        <option value="m">Masculino (o, os)</option>
        <option value="f">Feminino (a, as)</option>
      </select>
    </label>;
  };
  return <section className="colunas-painel" aria-labelledby="colunas-titulo" data-testid="colunas-painel">
    <h2 id="colunas-titulo" className="text-base font-bold text-ink">Colunas</h2>
    <p className="mt-1 text-xs leading-5 text-slate-600">Confira a coluna de cada campo. As sugestões aparecem no topo de cada
      lista, marcadas “(sugerida)”, e só valem depois da sua escolha. Os campos com * são necessários.</p>
    <div className="colunas-grade mt-3">
      {PAPEIS.map(({ papel, rotulo, ajuda, obrigatorio, vazio }) => {
        const valor = mapeamento[papel] || "";
        // O grupo de cima fica acima do grupo territorial (07/11/2026): sem ele, o seletor espera.
        const espera = papel === "grupo_territorial_superior" && !mapeamento.grupo_territorial && !valor;
        return <label key={papel} className="colunas-campo" data-testid={"colunas-campo-" + papel}>
          <span>{rotulo}{obrigatorio ? " *" : ""}</span>
          <select aria-label={rotulo} data-testid={"colunas-" + papel} value={valor} className={CAMPO} disabled={espera}
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
      {!mapeamento.category && <label className="colunas-campo" data-testid="colunas-campo-objeto">
        <span>Quem são os trabalhadores contados? *</span>
        <input aria-label="Quem são os trabalhadores contados?" data-testid="colunas-objeto" className={CAMPO}
          placeholder="Por exemplo: médicos" value={escolhas.objeto}
          onChange={event => onEscolhas({ ...escolhas, objeto: event.target.value })}/>
        <small>Sem coluna de categoria, diga a profissão ou o conjunto de trabalhadores que a planilha conta.</small>
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
      <p className="mt-1 text-[12px] leading-4 text-slate-600" data-testid="colunas-referencial-ajuda">Informe o referencial em que
        as coordenadas foram coletadas: SIRGAS 2000 ou WGS 84. O sistema não converte um no outro. Com outro referencial, ou sem
        saber qual é, a análise espacial fica indisponível: nada é presumido.</p>
    </fieldset>}
    <fieldset className="colunas-bloco" data-testid="colunas-nomes">
      <legend>Nomes</legend>
      <p className="text-[12px] leading-4 text-slate-600">Como se chamam o território inteiro, as unidades{rotulos.grupo ? " e os grupos" : ""} desta
        planilha? Os nomes aparecem nos textos do gráfico, da trilha e da conversa.</p>
      <div className="colunas-grade mt-1">
        <label className="colunas-campo">
          <span>Nome do todo (opcional)</span>
          <input aria-label="Nome do todo" data-testid="colunas-todo-nome" className={CAMPO} maxLength={60} placeholder="Toda a base"
            value={rotulos.todo?.nome ?? ""} onChange={event => onEscolhas(editarTodo(escolhas, "nome", event.target.value))}/>
          <small>O nome próprio do território inteiro, como Portugal. Sem ele, a tela diz “Toda a base”.</small>
        </label>
        {!!rotulos.todo?.nome?.trim() && <label className="colunas-campo">
          <span>Como se diz</span>
          <select aria-label="Artigo do nome do todo" data-testid="colunas-todo-artigo" className={CAMPO} value={rotulos.todo.artigo}
            onChange={event => onEscolhas(editarTodo(escolhas, "artigo", event.target.value))}>
            {ARTIGOS_DO_TODO.map(([valor, texto]) => <option key={valor || "nenhum"} value={valor}>{texto}</option>)}
          </select>
        </label>}
        {nome("unidade", "singular", "Unidade, no singular")}
        {nome("unidade", "plural", "Unidades, no plural")}
        {genero("unidade", "Gênero da unidade")}
        {rotulos.grupo && nome("grupo", "singular", "Grupo, no singular")}
        {rotulos.grupo && nome("grupo", "plural", "Grupos, no plural")}
        {rotulos.grupo && genero("grupo", "Gênero do grupo")}
        {rotulos.grupo_superior && nome("grupo_superior", "singular", "Grupo de cima, no singular")}
        {rotulos.grupo_superior && nome("grupo_superior", "plural", "Grupos de cima, no plural")}
        {rotulos.grupo_superior && genero("grupo_superior", "Gênero do grupo de cima")}
      </div>
    </fieldset>
    <div className="colunas-bloco" data-testid="colunas-disponibilidade" aria-live="polite">
      <h3 className="text-sm font-bold text-ink">O que esta planilha permite</h3>
      {conferindo ? <p role="status" className="text-xs text-teal-texto">Conferindo as colunas…</p>
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
      className="mt-3 inline-flex min-h-10 items-center gap-2 rounded-xl bg-ink px-4 py-2 text-sm font-semibold text-white hover:bg-ink-realce">
      <Play size={15} aria-hidden="true"/>{emUso ? "Aplicar as colunas" : "Começar a análise"}</button>
  </section>;
}
