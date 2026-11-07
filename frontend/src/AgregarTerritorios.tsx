import { useMemo, useRef, useState } from "react";
import { Search, X } from "lucide-react";
import {
  artigo, grupoDaUnidade, maiuscula, nomeDaUnidade, quantos, RESSALVA_DA_SOMA, type GrupoInfo, type RotulosTerritoriais,
  type UnidadeDoCatalogo,
} from "./painelModel";

// Agregar territórios (06/11/2026, item 5 do comando de navegação por níveis; no lugar do Juntar das Ferramentas das análises): na
// Seleção de Territórios, um painel com a mesma busca da Seleção (digitar e marcar) e a lista de um grupo da base para marcar (a
// árvore: escolher o estado e marcar os municípios dele), os escolhidos em etiquetas com ×, o nome do grupo (a sugestão "Grupo N",
// editável), a opção "O grupo fica no lugar dos membros" (marcada) e "Criar grupo". Vale juntar unidades de grupos diferentes
// (municípios de estados diferentes). A soma é do motor (CAP-AGR-01), com a ressalva; nada é calculado aqui. O mesmo painel edita um
// grupo (✎): o nome e os membros.

export type GrupoAgregado = { rotulo: string; membros: string[]; substitui: boolean };

type Props = {
  unidades: UnidadeDoCatalogo[];
  rotulos: RotulosTerritoriais;
  /** Os grupos da base (os estados): a lista de um deles é a árvore do painel. Sem grupos, a lista é a de todas as unidades. */
  grupos: GrupoInfo[];
  /** O nome sugerido ("Grupo 1"). */
  sugestao: string;
  /** O grupo em edição (✎); sem ele, um grupo novo. */
  inicial?: GrupoAgregado | null;
  onCriar: (grupo: GrupoAgregado) => void;
  onCancelar: () => void;
};

const sem = (texto: string) => texto.normalize("NFD").replace(/[̀-ͯ]/g, "").toLowerCase();
const comparar = (a: string, b: string) => a.localeCompare(b, "pt-BR", { numeric: true });
const LIMITE = 20;

export default function AgregarTerritorios(p: Props) {
  const [consulta, setConsulta] = useState("");
  const [membros, setMembros] = useState<string[]>(() => [...(p.inicial?.membros ?? [])]);
  const [nome, setNome] = useState(() => p.inicial?.rotulo ?? p.sugestao);
  const [substitui, setSubstitui] = useState(() => p.inicial?.substitui ?? true);
  const temGrupos = p.grupos.length > 0;
  // A árvore do painel: o grupo escolhido na lista (nenhum de início) ou, numa base sem grupos, a lista de todas as unidades, aberta
  // pelo botão.
  const [grupo, setGrupo] = useState("");
  const [verLista, setVerLista] = useState(false);
  const buscaRef = useRef<HTMLInputElement>(null);
  const unidade = p.rotulos.unidade, grupoRotulo = p.rotulos.grupo ?? { singular: "grupo", plural: "grupos" };
  const generoF = artigo(unidade, false) === "a", generoGrupoF = artigo(grupoRotulo, false) === "a";
  const porId = useMemo(() => new Map(p.unidades.map(item => [item.id, item])), [p.unidades]);
  const nomeDoGrupo = useMemo(() => new Map(p.grupos.map(item => [item.id, item.nome])), [p.grupos]);
  const termo = sem(consulta.trim());
  const resultados = useMemo(() => termo.length < 2 ? [] : p.unidades.filter(item => sem(item.name || item.label).includes(termo) ||
    sem(nomeDaUnidade(item)).includes(termo)).slice(0, LIMITE), [p.unidades, termo]);
  // A lista para marcar: as unidades do grupo escolhido (ou todas, numa base sem grupos), em ordem de nome.
  const lista = useMemo(() => (temGrupos ? (grupo ? p.unidades.filter(item => grupoDaUnidade(item) === grupo) : [])
    : verLista ? p.unidades : []).slice().sort((a, b) => comparar(nomeDaUnidade(a), nomeDaUnidade(b))), [p.unidades, grupo, temGrupos, verLista]);
  const rotulo = (id: string) => { const item = porId.get(id); return item ? nomeDaUnidade(item) : id; };
  const alternar = (id: string) => setMembros(atual => atual.includes(id) ? atual.filter(item => item !== id) : [...atual, id]);
  const editando = !!p.inicial;
  const pronto = membros.length >= 2 && !!nome.trim();
  const caixa = (item: UnidadeDoCatalogo, comGrupo: boolean) => {
    const nomeGrupo = comGrupo && temGrupos ? nomeDoGrupo.get(grupoDaUnidade(item)) : "";
    return <label className="analise-caixa analise-agregar-caixa">
      <input type="checkbox" checked={membros.includes(item.id)} onChange={() => alternar(item.id)}/>
      <span>{nomeDaUnidade(item)}{nomeGrupo && <span className="analise-agregar-grupo-do-item"> · {nomeGrupo}</span>}</span>
    </label>;
  };
  return <section data-testid="analise-agregar" aria-labelledby="analise-agregar-titulo" className="analise-agregar">
    <h4 id="analise-agregar-titulo" className="analise-agregar-titulo">{editando ? "Editar o grupo" : "Agregar territórios"}</h4>
    <p className="analise-agregar-apoio">Busque ou marque {generoF ? "duas" : "dois"} ou mais {unidade.plural}
      {temGrupos ? ", também de " + grupoRotulo.plural + " diferentes" : ""}; o grupo vira um território da análise.</p>
    <div className="analise-busca">
      <label className="sr-only" htmlFor="analise-agregar-busca">Buscar {unidade.singular} para o grupo</label>
      <Search size={16} aria-hidden="true" className="analise-busca-icone"/>
      <input ref={buscaRef} id="analise-agregar-busca" type="search" data-testid="analise-agregar-busca" value={consulta} autoComplete="off"
        onChange={event => setConsulta(event.target.value)} placeholder={"Buscar " + unidade.singular} className="analise-campo analise-busca-campo"/>
      {consulta && <button type="button" className="analise-icone analise-busca-limpar" aria-label="Limpar a busca"
        onClick={() => { setConsulta(""); buscaRef.current?.focus(); }}><X size={14} aria-hidden="true"/></button>}
    </div>
    {resultados.length > 0 && <ul data-testid="analise-agregar-resultados" className="analise-agregar-resultados"
      aria-label="Resultados da busca">
      {resultados.map(item => <li key={item.id} data-testid="analise-agregar-resultado" data-id={item.id}>{caixa(item, true)}</li>)}
    </ul>}
    {termo.length >= 2 && !resultados.length && <p className="analise-agregar-apoio">Nenhum{generoF ? "a" : ""} {unidade.singular}{" "}
      com esse nome.</p>}
    {temGrupos ? <label className="analise-rotulo-campo">Ou marque na lista de {generoGrupoF ? "uma" : "um"} {grupoRotulo.singular}
      <select data-testid="analise-agregar-grupo" value={grupo} onChange={event => setGrupo(event.target.value)} className="analise-campo">
        <option value="">Escolha {generoGrupoF ? "uma" : "um"} {grupoRotulo.singular}</option>
        {p.grupos.map(item => <option key={item.id} value={item.id}>{item.nome}</option>)}
      </select>
    </label> : <button type="button" data-testid="analise-agregar-ver-lista" className="analise-botao-secundario analise-agregar-ver-lista"
      aria-expanded={verLista} onClick={() => setVerLista(atual => !atual)}>{verLista ? "Fechar a lista" : "Ou marque na lista"}</button>}
    {lista.length > 0 && <ul data-testid="analise-agregar-lista" className="analise-agregar-lista"
      aria-label={temGrupos ? maiuscula(unidade.plural) + " de " + (nomeDoGrupo.get(grupo) ?? grupo) : maiuscula(unidade.plural)}>
      {lista.map(item => <li key={item.id} data-testid="analise-agregar-unidade" data-id={item.id}>{caixa(item, false)}</li>)}
    </ul>}
    <p id="analise-agregar-escolhidos" className="analise-agregar-rotulo">Escolhidos</p>
    {membros.length > 0 ? <ul data-testid="analise-agregar-membros" className="analise-selecionado-unidades"
      aria-labelledby="analise-agregar-escolhidos" aria-describedby="analise-agregar-quantos">
      {membros.map(id => <li key={id} data-testid="analise-agregar-membro" data-id={id} className="analise-etiqueta">{rotulo(id)}
        <button type="button" className="analise-icone analise-icone-pequeno" aria-label={"Tirar " + rotulo(id) + " do grupo"}
          onClick={() => alternar(id)}><X size={13} aria-hidden="true"/></button></li>)}
    </ul> : <p className="analise-agregar-apoio">Nenhum{generoF ? "a" : ""} {unidade.singular} escolhid{generoF ? "a" : "o"} ainda.</p>}
    <span id="analise-agregar-quantos" className="sr-only">{quantos(membros.length, unidade)}</span>
    <label className="analise-rotulo-campo">Nome do grupo
      <input data-testid="analise-agregar-nome" value={nome} maxLength={60} onChange={event => setNome(event.target.value)}
        className="analise-campo"/>
    </label>
    <label className="analise-caixa analise-agregar-opcao">
      <input type="checkbox" data-testid="analise-agregar-substitui" checked={substitui} onChange={event => setSubstitui(event.target.checked)}/>
      <span>O grupo fica no lugar dos membros</span>
    </label>
    <p data-testid="analise-agregar-ressalva" className="analise-ressalva">{RESSALVA_DA_SOMA}</p>
    <div className="analise-agregar-acoes">
      <button type="button" data-testid="analise-agregar-criar" className="analise-botao-primario" disabled={!pronto}
        onClick={() => p.onCriar({ rotulo: nome.trim(), membros, substitui })}>{editando ? "Salvar grupo" : "Criar grupo"}</button>
      <button type="button" data-testid="analise-agregar-cancelar" className="analise-botao-secundario" onClick={p.onCancelar}>Cancelar</button>
    </div>
  </section>;
}
