import { useEffect, useMemo, useRef, useState } from "react";
import { Search, X } from "lucide-react";
import MapaDosConjuntos from "./MapaDosConjuntos";
import {
  artigo, formatarNumero, grupoDaUnidade, maiuscula, nomeDaUnidade, nomeRepetido, quantos, RESSALVA_DA_SOMA, type GrupoInfo, type RotulosTerritoriais,
  type UnidadeDoCatalogo,
} from "./painelModel";

// "Agrupar territórios" (07/11/2026, comando de 07/11/2026, itens 1, 7.8 e 8; antes, "Agregar territórios", do comando de navegação
// por níveis de 06/11/2026), um dos modos da Seleção de Territórios: o mini mapa no alto, que também é um jeito de escolher (tocar num
// ponto cinza põe o território no conjunto; num ponto cheio, tira; a linha-resumo diz o que mudou e a extensão de ponta a ponta, que o
// motor mede), a mesma busca da Seleção, a lista de um grupo da base para marcar (o caminho pelo teclado), os escolhidos em etiquetas
// com ×, o nome do conjunto (a sugestão "Conjunto A"…, editável, sem repetir o de outro conjunto da análise), a opção "O conjunto fica
// no lugar dos membros" (marcada) e "Criar conjunto". Vale juntar unidades de grupos diferentes. A soma é do motor (CAP-AGR-01), com a
// ressalva; nada é calculado aqui. O mesmo modo edita um conjunto (✎): o nome e os membros.

export type GrupoAgregado = { rotulo: string; membros: string[]; substitui: boolean };

type Props = {
  unidades: UnidadeDoCatalogo[];
  rotulos: RotulosTerritoriais;
  /** Os grupos da base (os estados): a lista de um deles é a árvore do modo. Sem grupos, a lista é a de todas as unidades. */
  grupos: GrupoInfo[];
  /** O nome sugerido ("Conjunto A", a próxima letra livre). */
  sugestao: string;
  /** Os nomes dos outros conjuntos da análise (o nome não pode repetir nenhum). */
  nomesDosOutros: string[];
  /** O conjunto em edição (✎) ou os marcados na lista ("Agrupar os marcados"); sem ele, um conjunto novo vazio. */
  inicial?: GrupoAgregado | null;
  editando?: boolean;
  /** Coordenadas autorizadas para o mini mapa (do motor), só para desenhar. */
  coordenadas: Map<string, [number, number]> | null;
  /** A extensão de ponta a ponta dos escolhidos (km), medida pelo motor; null quando não dá para medir. */
  medirExtensao?: (membros: string[], signal: AbortSignal) => Promise<number | null>;
  onCriar: (grupo: GrupoAgregado) => void;
  onCancelar: () => void;
  /** O título da janela; null quando ela vem dentro de "Agrupar territórios selecionados" (comando V22), que já tem o dele. */
  titulo?: string | null;
};

const sem = (texto: string) => texto.normalize("NFD").replace(/[̀-ͯ]/g, "").toLowerCase();
const comparar = (a: string, b: string) => a.localeCompare(b, "pt-BR", { numeric: true });
const LIMITE = 20;
const ESPERA_DA_EXTENSAO = 300;

export default function AgregarTerritorios(p: Props) {
  const [consulta, setConsulta] = useState("");
  const [membros, setMembros] = useState<string[]>(() => [...(p.inicial?.membros ?? [])]);
  const [nome, setNome] = useState(() => p.inicial?.rotulo || p.sugestao);
  const [substitui, setSubstitui] = useState(() => p.inicial?.substitui ?? true);
  const [mudanca, setMudanca] = useState("");
  const [extensao, setExtensao] = useState<{ chave: string; km: number | null } | null>(null);
  const temGrupos = p.grupos.length > 0;
  // A árvore do modo: o grupo escolhido na lista (de início, o do primeiro escolhido) ou, numa base sem grupos, a lista de todas as
  // unidades, aberta pelo botão.
  const porId = useMemo(() => new Map(p.unidades.map(item => [item.id, item])), [p.unidades]);
  const [grupo, setGrupo] = useState(() => { const primeiro = membros[0] ? porId.get(membros[0]) : undefined; return primeiro ? grupoDaUnidade(primeiro) : ""; });
  const [verLista, setVerLista] = useState(false);
  const buscaRef = useRef<HTMLInputElement>(null);
  const unidade = p.rotulos.unidade, grupoRotulo = p.rotulos.grupo ?? { singular: "grupo", plural: "grupos" };
  const generoF = artigo(unidade, false) === "a", generoGrupoF = artigo(grupoRotulo, false) === "a";
  const nomeDoGrupo = useMemo(() => new Map(p.grupos.map(item => [item.id, item.nome])), [p.grupos]);
  const termo = sem(consulta.trim());
  const resultados = useMemo(() => termo.length < 2 ? [] : p.unidades.filter(item => sem(item.name || item.label).includes(termo) ||
    sem(nomeDaUnidade(item)).includes(termo)).slice(0, LIMITE), [p.unidades, termo]);
  // A lista para marcar: as unidades do grupo escolhido (ou todas, numa base sem grupos), em ordem de nome.
  const lista = useMemo(() => (temGrupos ? (grupo ? p.unidades.filter(item => grupoDaUnidade(item) === grupo) : [])
    : verLista ? p.unidades : []).slice().sort((a, b) => comparar(nomeDaUnidade(a), nomeDaUnidade(b))), [p.unidades, grupo, temGrupos, verLista]);
  const rotulo = (id: string) => { const item = porId.get(id); return item ? nomeDaUnidade(item) : id; };
  const alternar = (id: string) => {
    const saiu = membros.includes(id);
    setMembros(atual => saiu ? atual.filter(item => item !== id) : [...atual, id]);
    setMudanca(rotulo(id) + (saiu ? " saiu do conjunto." : " entrou no conjunto."));
  };
  const editando = !!p.editando;
  const repetido = nomeRepetido(nome, p.nomesDosOutros);
  const pronto = membros.length >= 2 && !!nome.trim() && !repetido;

  // A extensão de ponta a ponta, pelo motor, a cada mudança nos escolhidos (espera curta e o pedido anterior cancelado).
  const chaveDaExtensao = [...membros].sort().join(",");
  useEffect(() => {
    if (!p.medirExtensao || membros.length < 2) return;
    const controle = new AbortController();
    const espera = setTimeout(() => {
      p.medirExtensao!(membros, controle.signal).then(km => { if (!controle.signal.aborted) setExtensao({ chave: chaveDaExtensao, km }); })
        .catch(() => { if (!controle.signal.aborted) setExtensao({ chave: chaveDaExtensao, km: null }); });
    }, ESPERA_DA_EXTENSAO);
    return () => { clearTimeout(espera); controle.abort(); };
  }, [chaveDaExtensao]);
  const kmAtual = extensao && extensao.chave === chaveDaExtensao ? extensao.km : null;
  const resumo = quantos(membros.length, unidade) + (membros.length >= 2 && kmAtual !== null
    ? " · " + formatarNumero(Math.round(kmAtual), true) + " km de ponta a ponta" : "");

  // O mini mapa (item 7.8): os escolhidos, cheios, no contorno do conjunto; em cinza claro, os demais do grupo aberto na lista e dos
  // grupos dos escolhidos, para situar.
  const fundo = useMemo(() => {
    const gruposVisiveis = new Set([grupo, ...membros.map(id => { const item = porId.get(id); return item ? grupoDaUnidade(item) : ""; })]
      .filter(Boolean));
    return p.unidades.filter(item => !item.selection_reason && (temGrupos ? gruposVisiveis.has(grupoDaUnidade(item)) : true)).map(item => item.id);
  }, [p.unidades, grupo, membros, temGrupos, porId]);
  const caixa = (item: UnidadeDoCatalogo, comGrupo: boolean) => {
    const nomeGrupo = comGrupo && temGrupos ? nomeDoGrupo.get(grupoDaUnidade(item)) : "";
    return <label className="analise-caixa analise-agregar-caixa">
      <input type="checkbox" checked={membros.includes(item.id)} onChange={() => alternar(item.id)}/>
      <span>{nomeDaUnidade(item)}{nomeGrupo && <span className="analise-agregar-grupo-do-item"> · {nomeGrupo}</span>}</span>
    </label>;
  };
  return <section data-testid="analise-agregar" aria-labelledby={p.titulo !== null ? "analise-agregar-titulo" : undefined}
    aria-label={p.titulo === null ? "Formar um conjunto" : undefined} className="analise-agregar">
    {p.titulo !== null && <h4 id="analise-agregar-titulo" className="analise-agregar-titulo">{p.titulo ?? (editando ? "Editar o conjunto" : "Agrupar territórios")}</h4>}
    <div className="analise-criterios-alto">
      <p data-testid="analise-agregar-resumo" className="analise-criterios-resumo" aria-live="polite">{resumo}{mudanca ? " · " + mudanca : ""}</p>
      {p.coordenadas && <MapaDosConjuntos coordenadas={p.coordenadas} fundo={fundo} conjuntos={[{ id: "novo", nome: nome.trim() || p.sugestao, membros }]}
        nomeDe={rotulo} onTocar={alternar} rotulo={"Mini mapa do conjunto: " + resumo + ". Toque num ponto para pôr ou tirar " + (generoF ? "a " : "o ") +
          unidade.singular + "."} vazio={"O mapa aparece com " + (generoF ? "a primeira escolhida" : "o primeiro escolhido") +
          (temGrupos ? " ou com a lista de " + (generoGrupoF ? "uma " : "um ") + grupoRotulo.singular + " aberta" : "") + "."}/>}
    </div>
    <p className="analise-agregar-apoio">Busque, marque ou toque no mapa {generoF ? "duas" : "dois"} ou mais {unidade.plural}
      {temGrupos ? ", também de " + grupoRotulo.plural + " diferentes" : ""}; o conjunto vira um território da análise.</p>
    <div className="analise-busca">
      <label className="sr-only" htmlFor="analise-agregar-busca">Buscar {unidade.singular} para o conjunto</label>
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
        <button type="button" className="analise-icone analise-icone-pequeno" aria-label={"Tirar " + rotulo(id) + " do conjunto"}
          onClick={() => alternar(id)}><X size={13} aria-hidden="true"/></button></li>)}
    </ul> : <p className="analise-agregar-apoio">Nenhum{generoF ? "a" : ""} {unidade.singular} escolhid{generoF ? "a" : "o"} ainda.</p>}
    <span id="analise-agregar-quantos" className="sr-only">{quantos(membros.length, unidade)}</span>
    <label className="analise-rotulo-campo">Nome do conjunto
      <input data-testid="analise-agregar-nome" value={nome} maxLength={60} aria-invalid={repetido || !nome.trim()} onChange={event => setNome(event.target.value)}
        className="analise-campo"/>
    </label>
    {repetido && <p role="alert" data-testid="analise-agregar-nome-repetido" className="analise-faixa-erro">Já existe um conjunto com esse nome na análise.</p>}
    <label className="analise-caixa analise-agregar-opcao">
      <input type="checkbox" data-testid="analise-agregar-substitui" checked={substitui} onChange={event => setSubstitui(event.target.checked)}/>
      <span>O conjunto fica no lugar dos membros</span>
    </label>
    <p data-testid="analise-agregar-ressalva" className="analise-ressalva">{RESSALVA_DA_SOMA}</p>
    <div className="analise-criterios-rodape analise-agregar-acoes">
      <button type="button" data-testid="analise-agregar-criar" className="analise-botao-primario" disabled={!pronto}
        onClick={() => p.onCriar({ rotulo: nome.trim(), membros, substitui })}>{editando ? "Salvar conjunto" : "Criar conjunto"}</button>
      <button type="button" data-testid="analise-agregar-cancelar" className="analise-botao-secundario" onClick={p.onCancelar}>Cancelar</button>
    </div>
  </section>;
}
