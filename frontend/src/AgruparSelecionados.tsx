import { useEffect, useMemo, useRef, useState } from "react";
import AgregarTerritorios, { type GrupoAgregado } from "./AgregarTerritorios";
import MapaDosConjuntos from "./MapaDosConjuntos";
import { pedirCriterios, type FonteDoMotor, type PainelMunicipios, type Premissas, type RespostaCriterios, type RotulosTerritoriais } from "./painelApi";
import {
  MAX_CONJUNTOS, RESSALVA_DA_SOMA, artigo, formatarNumero, maiuscula, nomeDaUnidade, nomeRepetido, nomesLivresDeConjunto, quantos,
  textoDaAgregacao, type GrupoInfo, type UnidadeDoCatalogo,
} from "./painelModel";

// "Agrupar territórios selecionados" (comando V22, 9/11/2026, seção 5), aberto pela ação do painel direito da Seleção: agrupa só o que
// já está selecionado, sem criar seleção nova nem trazer territórios de fora, e os que não entram em conjunto continuam selecionados,
// cada um como território individual (a pergunta sobre "levar os sem conjunto" saiu). Duas modalidades:
// - Por escolha livre: a mesma janela de "Agrupar territórios" (busca, lista, mini mapa e nome), só com os selecionados; um ou mais
//   conjuntos, um de cada vez, com nome. Conjuntos reúnem territórios do mesmo nível: municípios, ou estados como unidade (a soma das
//   fontes estaduais, dita no rótulo).
// - Por proximidade (antes, o passo 3 de "Por critérios"): os conjuntos todos a até X km entre si (RQ-CAP-13), pela distância
//   geodésica entre as sedes, calculados pelo motor (POST /api/painel/criterios, partir_de "selecao"), só com os municípios
//   selecionados; os estados como unidade entram só na escolha livre.
// Nada é calculado na tela: as somas e as extensões vêm do motor (CAP-AGR-01, com a ressalva da soma).
export type ConjuntoPorProximidade = { membros: string[]; rotulo: string };
type Modo = "livre" | "proximidade";
type Props = {
  fonte: FonteDoMotor | null;
  rotulos: RotulosTerritoriais;
  brasil: boolean;
  grupos: GrupoInfo[];
  /** Os municípios selecionados individualmente (os candidatos da escolha livre e da proximidade). */
  unidades: UnidadeDoCatalogo[];
  /** Os estados como unidade da seleção (os candidatos de um conjunto de estados). */
  estados: string[];
  base: PainelMunicipios;
  competencia: string;
  categoria: string;
  premissas?: Premissas;
  conjuntosNaAnalise: { id: string; rotulo: string }[];
  coordenadas: Map<string, [number, number]> | null;
  medirExtensao?: (membros: string[], signal: AbortSignal) => Promise<number | null>;
  /** O conjunto em edição (✎), com o nome e os membros. */
  editando?: { id: string; grupo: GrupoAgregado } | null;
  onCriar: (grupo: GrupoAgregado) => void;
  onSalvar: (id: string, grupo: GrupoAgregado) => void;
  onUsarProximidade: (conjuntos: ConjuntoPorProximidade[], km: number) => void;
  onCancelar: () => void;
  /** A distância de um pedido com agrupamento (dos critérios ou da conversa): abre por proximidade, com ela. */
  kmInicial?: number | null;
};

const ESPERA = 300;
const lerNumero = (texto: string) => {
  const limpo = texto.trim();
  if (!limpo || /[,.]$/.test(limpo)) return null;
  const valor = Number(limpo.replace(/\./g, "").replace(",", "."));
  return Number.isFinite(valor) ? valor : null;
};

export default function AgruparSelecionados(p: Props) {
  const unidade = p.rotulos.unidade, grupo = p.rotulos.grupo ?? { singular: "estado", plural: "estados" };
  const generoF = artigo(unidade, false) === "a", grupoF = artigo(grupo, false) === "a";
  const comUnidades = p.unidades.length >= 2, comEstados = p.estados.length >= 2;
  const [modo, setModo] = useState<Modo>(p.kmInicial ? "proximidade" : "livre");
  const [nivel, setNivel] = useState<"municipios" | "estados">(() => p.editando ? (p.editando.grupo.membros.every(id => id.startsWith("uf:"))
    ? "estados" : "municipios") : comUnidades || !comEstados ? "municipios" : "estados");
  const [estadosEscolhidos, setEstadosEscolhidos] = useState<string[]>([]);
  const [nomeDosEstados, setNomeDosEstados] = useState(() => nomesLivresDeConjunto(p.conjuntosNaAnalise.map(c => c.rotulo), 1)[0]);
  const [substituiEstados, setSubstituiEstados] = useState(true);
  const [km, setKm] = useState(p.kmInicial ? String(p.kmInicial).replace(".", ",") : "");
  const [previa, setPrevia] = useState<{ chave: string; dados: RespostaCriterios } | null>(null);
  const [carregando, setCarregando] = useState(false);
  const [erro, setErro] = useState("");
  const [nomes, setNomes] = useState<Record<string, string>>({});
  const controle = useRef<AbortController | null>(null);
  const nomeDoGrupo = useMemo(() => new Map(p.grupos.map(item => [item.id, item.nome])), [p.grupos]);
  const porId = useMemo(() => new Map(p.unidades.map(item => [item.id, item])), [p.unidades]);
  const nomeDe = (id: string) => { const item = porId.get(id); return item ? nomeDaUnidade(item) : id; };
  const existentes = p.conjuntosNaAnalise.filter(c => c.id !== p.editando?.id).map(c => c.rotulo);
  const gruposComSelecionados = useMemo(() => {
    const usados = new Set(p.unidades.map(item => item.state_code || item.state || item.parents?.[0] || ""));
    return p.grupos.filter(item => usados.has(item.id));
  }, [p.unidades, p.grupos]);

  // ------------------------------------------------------------------------------------------ proximidade: a prévia do motor
  const kmValido = lerNumero(km);
  const pronto = modo === "proximidade" && !!p.fonte && comUnidades && kmValido !== null && kmValido > 0;
  const chave = JSON.stringify([p.competencia, p.base, kmValido]);
  useEffect(() => {
    if (!pronto || !p.fonte) return;
    controle.current?.abort();
    const meu = new AbortController();
    controle.current = meu;
    const espera = setTimeout(() => {
      setCarregando(true); setErro("");
      pedirCriterios(p.fonte!, { competencia: p.competencia, categoria: p.categoria, criterios: { partir_de: { tipo: "selecao" }, filtros: [] },
        agrupar: { km: kmValido! }, base: { municipios: p.base }, ...(p.premissas && Object.keys(p.premissas).length ? { premissas: p.premissas } : {}),
        ...(p.fonte!.tipo === "arquivo" ? { rotulos: p.rotulos } : {}) }, meu.signal)
        .then(dados => { if (controle.current === meu) { setPrevia({ chave, dados }); setNomes({}); } })
        .catch(falha => {
          if (controle.current === meu && !(falha instanceof DOMException && falha.name === "AbortError"))
            setErro(falha instanceof Error ? falha.message : "Não foi possível calcular a prévia.");
        })
        .finally(() => { if (controle.current === meu) setCarregando(false); });
    }, ESPERA);
    return () => { clearTimeout(espera); meu.abort(); };
  }, [chave, pronto]);
  const atual = previa && previa.chave === chave ? previa.dados : null;
  const grupos = atual?.grupos ?? [];
  const sugeridos = useMemo(() => nomesLivresDeConjunto(existentes, grupos.length), [grupos.length, existentes.join("|")]);
  const nomeFinal = (id: string, i: number) => (nomes[id] ?? sugeridos[i] ?? "").trim();
  const finais = grupos.map((g, i) => nomeFinal(g.id, i));
  const problema = (i: number) => !finais[i] ? "Dê um nome ao conjunto." : nomeRepetido(finais[i], [...finais.filter((_, j) => j !== i), ...existentes])
    ? "Já existe um conjunto com esse nome." : "";
  const comProblema = grupos.some((_, i) => !!problema(i));
  const acimaDoLimite = grupos.length + existentes.length > MAX_CONJUNTOS;
  const semConjunto = atual ? [...(atual.isolados ?? []), ...(atual.semPosicao ?? [])] : [];
  const coordenadas = useMemo(() => p.coordenadas?.size ? p.coordenadas
    : new Map((atual?.pontos ?? []).map(ponto => [ponto.id, [ponto.lat, ponto.lon] as [number, number]])), [p.coordenadas, atual]);

  // ------------------------------------------------------------------------------------------ estados como unidade
  const nomeRepetidoDosEstados = nomeRepetido(nomeDosEstados, existentes);
  const prontoEstados = estadosEscolhidos.length >= 2 && !!nomeDosEstados.trim() && !nomeRepetidoDosEstados;

  const cabecalho = <>
    <h4 className="analise-agregar-titulo">{p.editando ? "Editar o conjunto" : "Agrupar territórios selecionados"}</h4>
    {!p.editando && <div role="radiogroup" aria-label="Como agrupar" data-testid="analise-agrupar-modos" className="analise-selecao-modos">
      {(["livre", "proximidade"] as Modo[]).map(item => <button key={item} type="button" role="radio" aria-checked={modo === item}
        data-testid={"analise-agrupar-" + item} className="analise-selecao-modo" onClick={() => setModo(item)}>
        {item === "livre" ? "Por escolha livre" : "Por proximidade"}</button>)}
    </div>}
    <p className="analise-agregar-apoio" data-testid="analise-agrupar-regra">Só os territórios já selecionados entram; os que ficam sem conjunto continuam
      selecionados, cada um como território individual. Um conjunto reúne territórios do mesmo nível.</p>
  </>;

  if (modo === "proximidade") return <section data-testid="analise-agrupamento" data-modo="proximidade" className="analise-agregar">
    {cabecalho}
    {!comUnidades ? <p className="analise-agregar-apoio">Selecione ao menos {generoF ? "duas" : "dois"} {unidade.plural} para agrupar por proximidade
      (os {grupo.plural} como unidade entram só na escolha livre).</p> : <>
      <label className="analise-rotulo-campo" htmlFor="analise-agrupar-km">Distância máxima entre os membros do conjunto (km)</label>
      <input id="analise-agrupar-km" data-testid="analise-agrupar-km" inputMode="decimal" value={km} onChange={event => setKm(event.target.value)}
        className="analise-campo"/>
      <p className="analise-agregar-apoio">Todos os territórios de um conjunto ficam a até essa distância uns dos outros, em linha reta entre as sedes
        (distância geodésica). Só {generoF ? "as" : "os"} {quantos(p.unidades.length, unidade)} selecionad{generoF ? "as" : "os"} individualmente entram;
        {p.estados.length ? " " + artigo(grupo, true) + " " + grupo.plural + " como unidade entram só na escolha livre." : ""}</p>
      <MapaDosConjuntos coordenadas={coordenadas} fundo={p.unidades.map(item => item.id)} conjuntos={grupos.map((g, i) => ({ id: g.id,
        nome: finais[i] || g.rotulo, membros: g.membros, descricao: (finais[i] || g.rotulo) + " (" + g.membros.map(nomeDe).join(", ") + ")" }))}
        semConjunto={semConjunto} nomeDe={nomeDe} escalaKm={kmValido} esmaecido={!atual && !!previa}
        rotulo={"Mini mapa do agrupamento por proximidade"} vazio="O mapa aparece com a distância escolhida."/>
      <p data-testid="analise-agrupar-estado" role="status" className={"analise-criterios-estado" + (erro ? " analise-faixa-erro" : "")}>
        {erro || (kmValido === null ? "Falta a distância do agrupamento." : carregando || !atual ? "Calculando a prévia…"
          : quantos(grupos.length, { singular: "conjunto", plural: "conjuntos" }) + " · " + quantos(semConjunto.length, unidade) + " sem conjunto (continu" +
            (semConjunto.length === 1 ? "a" : "am") + " selecionad" + (generoF ? "a" : "o") + (semConjunto.length === 1 ? "" : "s") + " individualmente)." +
            (acimaDoLimite ? " A análise aceita até " + MAX_CONJUNTOS + " conjuntos: diminua a distância." : ""))}</p>
      {grupos.length > 0 && <ol className="analise-criterios-grupos" aria-label="Conjuntos por proximidade">
        {grupos.map((g, i) => <li key={g.id} data-testid="analise-agrupar-conjunto" data-id={g.id}>
          <label className="analise-rotulo-campo">Nome do conjunto
            <input data-testid="analise-agrupar-conjunto-nome" value={nomes[g.id] ?? sugeridos[i] ?? ""} maxLength={60} className="analise-campo"
              aria-invalid={!!problema(i)} onChange={event => setNomes(atual => ({ ...atual, [g.id]: event.target.value }))}/>
          </label>
          {problema(i) && <p role="alert" className="analise-faixa-erro">{problema(i)}</p>}
          <p className="analise-agregar-apoio">{quantos(g.membros.length, unidade)} · {formatarNumero(Math.round(g.extensaoKm), true)} km de ponta a ponta:
            {" "}{g.membros.map(nomeDe).join(", ")}</p>
        </li>)}
      </ol>}
    </>}
    <p className="analise-ressalva">{RESSALVA_DA_SOMA}</p>
    <div className="analise-criterios-rodape analise-agregar-acoes">
      <button type="button" data-testid="analise-agrupar-usar" className="analise-botao-primario" disabled={!atual || !grupos.length || comProblema || acimaDoLimite}
        onClick={() => p.onUsarProximidade(grupos.map((g, i) => ({ membros: g.membros, rotulo: finais[i] })), kmValido!)}>
        Usar cada conjunto como um território</button>
      <button type="button" data-testid="analise-agrupar-cancelar" className="analise-botao-secundario" onClick={p.onCancelar}>Cancelar</button>
    </div>
  </section>;

  return <section data-testid="analise-agrupamento" data-modo="livre" className="analise-agregar">
    {cabecalho}
    {comUnidades && comEstados && !p.editando && <div role="radiogroup" aria-label="Nível do conjunto" className="analise-selecao-modos">
      <button type="button" role="radio" aria-checked={nivel === "municipios"} data-testid="analise-agrupar-nivel-municipios" className="analise-selecao-modo"
        onClick={() => setNivel("municipios")}>{maiuscula(unidade.plural)}</button>
      <button type="button" role="radio" aria-checked={nivel === "estados"} data-testid="analise-agrupar-nivel-estados" className="analise-selecao-modo"
        onClick={() => setNivel("estados")}>{maiuscula(grupo.plural)} como unidade</button>
    </div>}
    {nivel === "estados" ? <>
      {!comEstados ? <p className="analise-agregar-apoio">Ponha ao menos {grupoF ? "duas" : "dois"} {grupo.plural} na seleção como unidade (“Só {artigo(grupo, false)}
        {" "}{grupo.singular}”) para formar um conjunto de {grupo.plural}.</p> : <>
        <fieldset className="analise-criterios-bloco"><legend>{maiuscula(grupo.plural)} como unidade</legend>
          {p.estados.map(id => <label key={id} className="analise-caixa"><input type="checkbox" data-testid="analise-agrupar-estado" data-id={id}
            checked={estadosEscolhidos.includes(id)} onChange={() => setEstadosEscolhidos(atual => atual.includes(id) ? atual.filter(item => item !== id) : [...atual, id])}/>
            <span>{nomeDoGrupo.get(id) ?? id}</span></label>)}
        </fieldset>
        <label className="analise-rotulo-campo">Nome do conjunto
          <input data-testid="analise-agrupar-estados-nome" value={nomeDosEstados} maxLength={60} aria-invalid={nomeRepetidoDosEstados || !nomeDosEstados.trim()}
            onChange={event => setNomeDosEstados(event.target.value)} className="analise-campo"/>
        </label>
        {nomeRepetidoDosEstados && <p role="alert" className="analise-faixa-erro">Já existe um conjunto com esse nome na análise.</p>}
        <label className="analise-caixa analise-agregar-opcao">
          <input type="checkbox" data-testid="analise-agrupar-estados-substitui" checked={substituiEstados} onChange={event => setSubstituiEstados(event.target.checked)}/>
          <span>O conjunto fica no lugar dos membros</span>
        </label>
        <p className="analise-ressalva">{maiuscula(textoDaAgregacao(true))}; o total não é o número de médicos diferentes do conjunto nem o
          total {p.brasil ? "do Brasil" : "da base"}.</p>
      </>}
      <div className="analise-criterios-rodape analise-agregar-acoes">
        <button type="button" data-testid="analise-agrupar-estados-criar" className="analise-botao-primario" disabled={!prontoEstados}
          onClick={() => p.onCriar({ rotulo: nomeDosEstados.trim(), membros: estadosEscolhidos.map(id => "uf:" + id), substitui: substituiEstados })}>
          Criar conjunto</button>
        <button type="button" data-testid="analise-agrupar-cancelar" className="analise-botao-secundario" onClick={p.onCancelar}>Cancelar</button>
      </div>
    </> : !comUnidades && !p.editando ? <>
      <p className="analise-agregar-apoio">Selecione ao menos {generoF ? "duas" : "dois"} {unidade.plural} individualmente para formar um conjunto
        (busque ou marque na lista à esquerda).</p>
      <div className="analise-criterios-rodape analise-agregar-acoes">
        <button type="button" data-testid="analise-agrupar-cancelar" className="analise-botao-secundario" onClick={p.onCancelar}>Cancelar</button>
      </div>
    </> : <AgregarTerritorios key={p.editando?.id ?? "novo"} unidades={p.unidades} rotulos={p.rotulos} grupos={gruposComSelecionados}
      sugestao={nomesLivresDeConjunto(existentes, 1)[0]} nomesDosOutros={existentes} inicial={p.editando?.grupo ?? null} editando={!!p.editando}
      coordenadas={p.coordenadas} medirExtensao={p.medirExtensao} onCancelar={p.onCancelar} titulo={null}
      onCriar={grupoNovo => p.editando ? p.onSalvar(p.editando.id, grupoNovo) : p.onCriar(grupoNovo)}/>}
  </section>;
}
