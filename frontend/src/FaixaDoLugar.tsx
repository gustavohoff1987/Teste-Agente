import type { ReactNode } from "react";
import { ChevronRight } from "lucide-react";
import type { NivelDoLugar, PainelItem, PainelNivel, RespostaLugar } from "./painelApi";
import { competenciaCurta } from "./paginaUnica";
import {
  RESSALVA_DA_SOMA, formatarIndicador, formatarNumero, formatarVariacao, generoDe, maiuscula, nomeCurtoDoNivel, populacaoResumida,
  profissionaisDe, textoDaReferencia, type LugarDaTrilha, type OpcaoVerPor, type ParteDaTrilha, type RotulosTerritoriais,
} from "./painelModel";

// Navegação por níveis (comando do responsável de 06/11/2026, itens 2 e 3). A trilha, no alto da área de análise e igual em todas
// as abas, mostra o lugar em uso ("Brasil › Pará › MARABA (PA)"): cada parte leva àquele nível, e a atual fica marcada
// (aria-current). A faixa, no alto de todas as abas de análise, traz os números do lugar em uso na competência da análise
// (profissionais, população, densidade e a variação da densidade desde o primeiro dos últimos 4 períodos anuais) e, abaixo do
// todo, o valor do todo como referência ("Pará 1,19 · Brasil 2,36"); as competências como no comando ("Desde jun/2021"); com
// ela, o "Ver por" (no lugar de "Cada ponto da análise é"),
// que muda só quem é comparado. No nível da unidade, o cartão do território faz o papel da faixa: o valor dela e a comparação com
// o grupo e o todo, em barras. Todo número vem do motor (POST /api/painel/lugar e o resultado do gráfico); a tela só mostra.

type TrilhaProps = { partes: ParteDaTrilha[]; vazia: boolean; onIr: (parte: ParteDaTrilha) => void;
  /** O lugar atual é um grupo só em parte (uma seleção que cabe nele): a parte atual leva ao grupo inteiro. */
  grupoParcial: boolean };

export function Trilha({ partes, vazia, onIr, grupoParcial }: TrilhaProps) {
  return <nav data-testid="analise-trilha" aria-label="Trilha do lugar em uso" className="analise-trilha analise-nao-imprimir">
    <ol className="analise-trilha-lista">
      {partes.map((parte, indice) => {
        // O grupo (ou o grupo de cima, 07/11/2026) só em parte continua tocável: leva a ele inteiro.
        const tocavel = !parte.atual || ((parte.chave === "grupo" || parte.chave === "regiao") && grupoParcial);
        return <li key={parte.chave + ":" + (parte.id ?? "")} className="analise-trilha-item">
          {indice > 0 && <ChevronRight size={14} aria-hidden="true" className="analise-trilha-seta"/>}
          {tocavel ? <button type="button" data-testid="analise-trilha-parte" data-chave={parte.chave} data-id={parte.id ?? ""}
            aria-current={parte.atual ? "location" : undefined} className="analise-trilha-parte" onClick={() => onIr(parte)}
            title={parte.atual ? "Ver " + parte.rotulo + " inteiro" : "Ir para " + parte.rotulo}>{parte.rotulo}</button>
            : <span data-testid="analise-trilha-parte" data-chave={parte.chave} data-id={parte.id ?? ""} aria-current="location"
              className="analise-trilha-parte analise-trilha-atual">{parte.rotulo}</span>}
        </li>;
      })}
      {vazia && <li className="analise-trilha-item analise-trilha-dica">nenhum território escolhido: toque no nome para ver o todo ou use
        a Seleção de Territórios</li>}
    </ol>
  </nav>;
}

type VerPorProps = { opcoes: OpcaoVerPor[]; nivel: PainelNivel; onEscolher: (nivel: PainelNivel) => void; prefixo?: string };
/** "Ver por" (no lugar de "Cada ponto da análise é"): só com duas opções ou mais; com uma, o controle não aparece. */
export function VerPor({ opcoes, nivel, onEscolher, prefixo = "analise-ver-por" }: VerPorProps) {
  if (opcoes.length < 2) return null;
  return <div className="analise-ver-por">
    <span id={prefixo + "-titulo"} className="analise-ver-por-titulo">Ver por</span>
    <div role="radiogroup" aria-labelledby={prefixo + "-titulo"} data-testid={prefixo} className="analise-segmentos">
      {opcoes.map(opcao => <button key={opcao.nivel} type="button" role="radio" aria-checked={nivel === opcao.nivel}
        data-testid={prefixo + "-" + opcao.nivel} title={maiuscula(opcao.apoio)} onClick={() => nivel !== opcao.nivel && onEscolher(opcao.nivel)}>
        {opcao.rotulo}</button>)}
    </div>
  </div>;
}

type FaixaProps = {
  lugar: LugarDaTrilha;
  numeros: RespostaLugar | null;
  carregando: boolean;
  erro: string | null;
  categoria: string;
  rotulos: RotulosTerritoriais;
  /** O que está na análise, em poucas palavras (a seleção livre e o grupo em parte). */
  resumo: string;
  verPor: OpcaoVerPor[];
  nivel: PainelNivel;
  onVerPor: (nivel: PainelNivel) => void;
  /** No nível da unidade: o item dela no resultado do gráfico (os valores do motor) e, na Análise Espacial, a distância. */
  unidade: PainelItem | null;
  distancia: { valor: number | null; texto: string } | null;
};

const numeroOuTraco = (valor: number | null, contagem = false) => valor === null ? "não avaliável" : formatarNumero(valor, contagem);

function Numeros({ nivel, categoria }: { nivel: NivelDoLugar; categoria: string }) {
  const variacao = nivel.variacaoPercentual?.densidade ?? null;
  const profissionais = profissionaisDe(categoria);
  return <dl className="analise-faixa-numeros">
    <div data-testid="analise-faixa-numero" data-chave="profissionais" data-valor={nivel.quantidade ?? ""} className="analise-faixa-numero">
      <dt>{maiuscula(profissionais)}</dt><dd><strong>{numeroOuTraco(nivel.quantidade, true)}</strong></dd></div>
    <div data-testid="analise-faixa-numero" data-chave="populacao" data-valor={nivel.populacao ?? ""} className="analise-faixa-numero">
      <dt>População</dt><dd><strong>{nivel.populacao === null ? "não avaliável" : populacaoResumida(nivel.populacao)}</strong>
        {nivel.populacao !== null && <span className="analise-faixa-apoio">{formatarNumero(nivel.populacao, true)} habitantes</span>}</dd></div>
    <div data-testid="analise-faixa-numero" data-chave="densidade" data-valor={nivel.densidade ?? ""} className="analise-faixa-numero">
      <dt>Densidade</dt><dd><strong>{numeroOuTraco(nivel.densidade)}</strong>
        {nivel.densidade !== null && <span className="analise-faixa-apoio">por 1.000 habitantes</span>}</dd></div>
    {nivel.desde && <div data-testid="analise-faixa-numero" data-chave="variacao" data-valor={variacao ?? ""} data-desde={nivel.desde}
      className="analise-faixa-numero">
      <dt>Desde {competenciaCurta(nivel.desde)}</dt><dd><strong>{formatarVariacao(variacao)}</strong>
        <span className="analise-faixa-apoio">na densidade</span></dd></div>}
  </dl>;
}

/** As referências da faixa abaixo do todo: "Pará 1,19 · Brasil 2,36 (por 1.000 habitantes)", do motor. */
function Referencias({ niveis }: { niveis: (NivelDoLugar | null)[] }) {
  const comValor = niveis.filter((nivel): nivel is NivelDoLugar => !!nivel && nivel.densidade !== null);
  if (!comValor.length) return null;
  return <p data-testid="analise-faixa-referencia" className="analise-faixa-referencia">
    {comValor.map(nivel => textoDaReferencia(nomeCurtoDoNivel(nivel), nivel.densidade!)).join(" · ")}
    <span className="analise-faixa-apoio"> (densidade por 1.000 habitantes)</span></p>;
}

/** O cartão do território (item 3.4): o valor da unidade e a comparação da densidade com o grupo e o todo, em barras (mapeamento
 * visual contínuo dos valores do motor, sem classe nem posição). */
function CartaoDaUnidade({ item, grupo, todo, categoria, competencia, distancia }: { item: PainelItem; grupo: NivelDoLugar | null;
  todo: NivelDoLugar | null; categoria: string; competencia: string; distancia: FaixaProps["distancia"] }) {
  const barras = [{ chave: "unidade", nome: item.rotulo, valor: item.densidade },
    ...(grupo ? [{ chave: "grupo", nome: nomeCurtoDoNivel(grupo), valor: grupo.densidade }] : []),
    ...(todo ? [{ chave: "todo", nome: nomeCurtoDoNivel(todo), valor: todo.densidade }] : [])];
  const maior = Math.max(0, ...barras.map(barra => barra.valor ?? 0));
  return <div data-testid="analise-cartao" data-id={item.id} className="analise-cartao">
    <p className="analise-cartao-titulo"><strong data-testid="analise-cartao-quantidade" data-valor={item.quantidade ?? ""}>
      {item.quantidade === null ? "Sem contagem" : formatarNumero(item.quantidade, true) + " " + profissionaisDe(categoria)}</strong>
      {competencia && <span className="analise-faixa-apoio"> · {competenciaCurta(competencia)}</span>}
      {item.populacao !== null && <span className="analise-faixa-apoio"> · {formatarNumero(item.populacao, true)} habitantes</span>}</p>
    <p className="analise-cartao-subtitulo">Densidade ({maiuscula(profissionaisDe(categoria))} por 1.000 habitantes)</p>
    <ul className="analise-cartao-barras" aria-label="Densidade comparada">
      {barras.map(barra => <li key={barra.chave} data-testid="analise-cartao-barra" data-chave={barra.chave} data-valor={barra.valor ?? ""}
        className="analise-cartao-barra">
        <span className="analise-cartao-nome">{barra.nome}</span>
        <span className="analise-cartao-trilho" aria-hidden="true">
          <span className={"analise-cartao-preenchido analise-cartao-" + barra.chave}
            style={{ width: barra.valor !== null && maior > 0 ? Math.max(2, barra.valor / maior * 100) + "%" : "0%" }}/></span>
        <span className="analise-cartao-valor">{barra.valor === null ? "não avaliável" : formatarIndicador(barra.valor, "densidade")}</span>
      </li>)}
    </ul>
    {distancia && <p data-testid="analise-cartao-distancia" data-valor={distancia.valor ?? ""} className="analise-cartao-distancia">
      <strong>{distancia.valor === null ? "Sem distância avaliável" : formatarNumero(distancia.valor) + " km"}</strong>
      <span className="analise-faixa-apoio"> · {distancia.texto}</span></p>}
  </div>;
}

/** A faixa fixa do lugar em uso (item 2.2): os números do todo, do grupo ou da seleção e o "Ver por"; no nível da unidade, o
 * cartão do território. Sem números ainda (o primeiro pedido), o espaço com o aviso de carregamento. */
export default function FaixaDoLugar(p: FaixaProps) {
  if (p.lugar.tipo === "nenhum") return null;
  const todo = p.numeros?.todo ?? null, grupo = p.numeros?.grupo ?? null, regiao = p.numeros?.regiao ?? null;
  const titulo = p.lugar.partes.find(parte => parte.atual)?.rotulo ?? "";
  const competencia = p.numeros?.competencia ?? "";
  const cabecalho = <div className="analise-faixa-cabeca">
    <p className="analise-faixa-titulo"><strong>{p.lugar.tipo === "selecao" ? "Seleção" : titulo}</strong>
      {(p.lugar.tipo === "selecao" || (p.lugar.tipo === "grupo" && !p.lugar.grupoInteiro) || (p.lugar.tipo === "regiao" && !p.lugar.regiaoInteira)) && p.resumo &&
        <span data-testid="analise-faixa-resumo" className="analise-faixa-apoio"> · {p.resumo}</span>}
      {competencia && <span className="analise-faixa-apoio"> · {competenciaCurta(competencia)}</span>}</p>
    <VerPor opcoes={p.verPor} nivel={p.nivel} onEscolher={p.onVerPor}/>
  </div>;
  const estado = p.erro ? <p role="alert" className="analise-faixa-erro">Os números do lugar não vieram: {p.erro}</p>
    : p.carregando && !p.numeros ? <p role="status" className="analise-faixa-apoio">Buscando os números do lugar…</p> : null;
  let corpo: ReactNode = null;
  if (p.lugar.tipo === "unidade") {
    corpo = p.unidade ? <CartaoDaUnidade item={p.unidade} grupo={grupo} todo={todo} categoria={p.categoria} competencia={competencia}
      distancia={p.distancia}/> : null;
  } else if (p.lugar.tipo === "todo") {
    corpo = todo ? <Numeros nivel={todo} categoria={p.categoria}/> : null;
  } else if (p.lugar.tipo === "grupo") {
    corpo = <>{grupo && <Numeros nivel={grupo} categoria={p.categoria}/>}<Referencias niveis={[grupo, todo]}/></>;
  } else if (p.lugar.tipo === "regiao") {
    // O grupo de cima de uma planilha com dois níveis (07/11/2026): os números dele, pelas unidades, e o todo como referência.
    corpo = <>{regiao && <Numeros nivel={regiao} categoria={p.categoria}/>}<Referencias niveis={[regiao, todo]}/></>;
  } else {
    corpo = <Referencias niveis={[todo]}/>;
  }
  // Numa planilha (07/11/2026, item 1.4 do comando), a faixa diz de onde vem o total: pessoas únicas pelo identificador ou a soma
  // das unidades, com a ressalva da soma (G3). Na base do Brasil, os números vêm prontos nas fontes, sem a linha.
  const origem = (p.lugar.tipo === "grupo" ? grupo?.origem : p.lugar.tipo === "regiao" ? regiao?.origem : null) ?? todo?.origem ?? null;
  const unidade = p.rotulos.unidade;
  const daOrigem = origem === "soma" ? "Total: a soma d" + (generoDe(unidade) === "f" ? "as " : "os ") + unidade.plural + ". " + RESSALVA_DA_SOMA
    : origem === "pessoas_unicas" ? "Total: pessoas únicas, pelo identificador individual (quem atua em mais de " +
      (generoDe(unidade) === "f" ? "uma " : "um ") + unidade.singular + " conta uma vez)." : "";
  return <section data-testid="analise-faixa" data-lugar={p.lugar.tipo} data-grupo={p.lugar.grupo ?? ""} data-carregando={p.carregando ? "true" : "false"}
    aria-label={"Números do lugar em uso: " + titulo} className={"analise-faixa" + (p.lugar.tipo === "unidade" ? " analise-faixa-unidade" : "")}>
    {cabecalho}
    {corpo}
    {daOrigem && <p data-testid="analise-faixa-origem" data-origem={origem ?? ""} className="analise-faixa-apoio">{daOrigem}</p>}
    {estado}
  </section>;
}
