import { useEffect, useMemo, useState, type KeyboardEvent } from "react";
import type { PainelIndicador, PainelItem, PainelResposta } from "./painelApi";
import {
  INDICADORES, NOTA_TPL11, avisosDe, exibirCompetencia, formatarIndicador, formatarNumero, formatarPercentual, formatarVariacao, inicialDe,
  maiuscula, numero, ordenarTabela, paginar, textoDaContagem, textoDaLimitacao, variacaoDe, POR_PAGINA, type ColunaTabela, type Familia,
  type NaoAvaliavel, type Ordenacao, type RotulosTerritoriais,
} from "./painelModel";

// Detalhes, abaixo do gráfico: Tabela (os mesmos itens do gráfico, em páginas de 100), Não avaliáveis (à parte, com o motivo do
// motor, RQ-REP-04) e Método e procedência. Na impressão, as três partes aparecem.

type Aba = "tabela" | "nao-avaliaveis" | "metodo";
const ABAS: [Aba, string][] = [["tabela", "Tabela"], ["nao-avaliaveis", "Não avaliáveis"], ["metodo", "Método e procedência"]];
const ASPECTOS: Record<NaoAvaliavel["aspecto"], string> = {
  indicador: "Sem valor do indicador na competência", distancia: "Sem distância até a referência", variacao: "Variação não avaliável",
  tendencia: "Tendência não avaliável", condicoes: "Sem dado para avaliar as condições", rotatividade: "Coorte não avaliável",
  mapa: "Sem coordenada válida para o mapa",
};

type Props = {
  resposta: PainelResposta;
  itens: PainelItem[];
  fora: NaoAvaliavel[];
  familia: Familia;
  indicador: PainelIndicador;
  distancia: boolean;
  variacao: boolean;
  tendencia: boolean;
  rotulos: RotulosTerritoriais;
  selecionados: string[];
  limiares: number[];
  corteAtivo: boolean;
  onAlternar: (id: string) => void;
};

export default function PainelDetalhes(p: Props) {
  const [aba, setAba] = useState<Aba>("tabela");
  const [ordenacao, setOrdenacao] = useState<Ordenacao>(null);
  const [pagina, setPagina] = useState(0);
  const rotatividade = p.familia === "rotatividade";
  const linhas = useMemo(() => ordenarTabela(p.itens, ordenacao, p.indicador), [p.itens, ordenacao, p.indicador]);
  useEffect(() => setPagina(0), [linhas]);
  const atual = paginar(linhas, pagina);
  const especie = INDICADORES[p.indicador];
  const temGrupo = p.itens.some(item => item.grupo), temFaixa = p.itens.some(item => item.faixa);
  const temCondicao = p.itens.some(item => item.condicoes), temPosicao = p.itens.some(item => item.ordem?.posicao !== null && item.ordem !== null);
  const temProxima = p.distancia && p.itens.some(item => item.referenciaDoItem?.length);
  // Escolha dos territórios (27/10/2026): a referência é a mais próxima de cada item.
  const porItem = p.resposta.referencia?.tipo === "consulta";
  const ordenar = (coluna: ColunaTabela) => setOrdenacao(atual => !atual || atual.coluna !== coluna ? { coluna, sentido: "desc" }
    : atual.sentido === "desc" ? { coluna, sentido: "asc" } : null);
  const ordemDe = (coluna: ColunaTabela): "ascending" | "descending" | "none" => !ordenacao || ordenacao.coluna !== coluna ? "none"
    : ordenacao.sentido === "asc" ? "ascending" : "descending";
  const cabecalho = (coluna: ColunaTabela, rotulo: string) => <th scope="col" aria-sort={ordemDe(coluna)}>
    <button type="button" onClick={() => ordenar(coluna)} className="analise-th">
      {rotulo}{ordemDe(coluna) === "ascending" ? " ↑" : ordemDe(coluna) === "descending" ? " ↓" : ""}</button></th>;
  const grupos = (Object.keys(ASPECTOS) as NaoAvaliavel["aspecto"][]).map(aspecto => ({ aspecto, itens: p.fora.filter(item => item.aspecto === aspecto) }))
    .filter(grupo => grupo.itens.length > 0);
  function teclado(event: KeyboardEvent<HTMLButtonElement>, indice: number) {
    const proxima = event.key === "ArrowRight" ? (indice + 1) % ABAS.length : event.key === "ArrowLeft" ? (indice + ABAS.length - 1) % ABAS.length
      : event.key === "Home" ? 0 : event.key === "End" ? ABAS.length - 1 : null;
    if (proxima === null) return;
    event.preventDefault();
    setAba(ABAS[proxima][0]);
    document.getElementById("analise-detalhes-aba-" + ABAS[proxima][0])?.focus();
  }
  const r = p.resposta;

  return <section data-testid="analise-detalhes" aria-labelledby="analise-detalhes-titulo" className="analise-detalhes">
    <h3 id="analise-detalhes-titulo" className="text-sm font-bold text-ink">Detalhes</h3>
    <div role="tablist" aria-label="Detalhes" className="analise-abas analise-nao-imprimir">
      {ABAS.map(([chave, rotulo], indice) => <button key={chave} id={"analise-detalhes-aba-" + chave} type="button" role="tab"
        data-testid={"analise-detalhes-" + chave} aria-selected={aba === chave} aria-controls={"analise-detalhes-painel-" + chave}
        tabIndex={aba === chave ? 0 : -1} onClick={() => setAba(chave)} onKeyDown={event => teclado(event, indice)}>
        {rotulo}{chave === "nao-avaliaveis" && p.fora.length ? " (" + p.fora.length + ")" : ""}</button>)}
    </div>

    <div role="tabpanel" id="analise-detalhes-painel-tabela" aria-labelledby="analise-detalhes-aba-tabela" hidden={aba !== "tabela"}
      data-testid="analise-tabela-painel" className="analise-painel-detalhe">
      <p className="text-xs leading-5 text-slate-600">Os mesmos itens do gráfico, com os valores em {exibirCompetencia(r.competencia)}. A ordem
        padrão é a do código territorial; clicar num cabeçalho só reordena a tabela, sem criar posições.{p.corteAtivo ? " O que a régua esconde não aparece." : ""}
        {atual.paginas > 1 ? " Com muitos itens, a tabela mostra " + POR_PAGINA + " linhas por vez." : ""}</p>
      <div className="mt-2 overflow-x-auto">
        <table data-testid="analise-tabela" className="analise-tabela min-w-full">
          <thead><tr>
            <th scope="col"><span className="sr-only">Destacar</span></th>
            {cabecalho("territorio", "Território")}
            {rotatividade ? <>
              {cabecalho("coorte", "Coorte inicial")}
              <th scope="col">Permaneceram</th><th scope="col">Saíram</th>
              {cabecalho("permanencia", "Permanência (%)")}
              <th scope="col">Saída (%)</th>
            </> : <>
              {cabecalho("populacao", "População")}
              {cabecalho("quantidade", "Profissionais")}
              {cabecalho("densidade", "Densidade")}
              {p.distancia && cabecalho("distancia", "Distância (km)")}
              {temProxima && <th scope="col">{porItem ? "Referência mais próxima" : "Membro da referência mais próximo"}</th>}
              {p.variacao && cabecalho("variacao", "Variação (" + especie.rotulo.toLowerCase() + ")")}
              {p.tendencia && cabecalho("classe", "Tendência")}
              {temGrupo && cabecalho("grupo", "Grupo")}
              {temFaixa && cabecalho("faixa", "Faixa")}
              {temCondicao && cabecalho("condicao", "Condições")}
              {temPosicao && cabecalho("posicao", "Posição")}
            </>}
            <th scope="col">Observação</th>
          </tr></thead>
          <tbody>{atual.linhas.map(item => {
            const variacao = variacaoDe(item, p.indicador), inicial = inicialDe(item, p.indicador);
            const observacao = [item.tipo === "conjunto" ? textoDaContagem(item.contagem) : "",
              item.referencia ? (item.tipo === "conjunto" ? "Conjunto igual à referência" : "Membro da referência") : "",
              item.tendencia?.motivo || "", ...avisosDe(item)].filter(Boolean).join(". ");
            const rot = item.rotatividade;
            return <tr key={item.id} data-testid="analise-linha" data-id={item.id} data-tipo={item.tipo}>
              <td><input type="checkbox" className="h-4 w-4 accent-teal" checked={p.selecionados.includes(item.id)} onChange={() => p.onAlternar(item.id)}
                aria-label={"Destacar " + item.rotulo}/></td>
              <td className="font-semibold text-ink">{item.rotulo}</td>
              {rotatividade ? <>
                <td className="tabular-nums">{rot?.coorteInicial === null || !rot ? "Não avaliável" : formatarNumero(rot.coorteInicial, true)}</td>
                <td className="tabular-nums">{rot?.permaneceram === null || !rot ? "—" : formatarNumero(rot.permaneceram, true)}</td>
                <td className="tabular-nums">{rot?.sairam === null || !rot ? "—" : formatarNumero(rot.sairam, true)}</td>
                <td className="tabular-nums">{formatarPercentual(rot?.permanencia)}</td>
                <td className="tabular-nums">{formatarPercentual(rot?.saida)}</td>
              </> : <>
                <td className="tabular-nums">{numero(item.populacao) === null ? "Não avaliável" : formatarNumero(item.populacao as number, true)}</td>
                <td className="tabular-nums">{numero(item.quantidade) === null ? "Não avaliável"
                  : formatarNumero(item.quantidade as number, true, p.indicador === "quantidade" ? p.limiares : [])}</td>
                <td className="tabular-nums">{formatarIndicador(numero(item.densidade), "densidade", p.indicador === "densidade" ? p.limiares : [])}</td>
                {p.distancia && <td className="tabular-nums">{numero(item.distancia_km) === null ? "Não avaliável" : formatarNumero(item.distancia_km as number) +
                  (item.tipo === "conjunto" && numero(item.distancia_km_max) !== null ? " a " + formatarNumero(item.distancia_km_max as number) : "")}</td>}
                {temProxima && <td>{(item.referenciaDoItem || []).map(ref => ref.rotulo).join(", ")}</td>}
                {p.variacao && <td className="tabular-nums" data-variacao={variacao ?? ""}>{formatarVariacao(variacao)}
                  {inicial !== null && <span className="block text-[11px] text-slate-500">em {exibirCompetencia(r.competencia_inicial)}:{" "}
                    {formatarNumero(inicial, especie.contagem)}</span>}</td>}
                {p.tendencia && <td data-classe={item.tendencia?.classe ?? ""}>{item.tendencia?.rotulo ?? "Não avaliável"}</td>}
                {temGrupo && <td>{item.grupo?.rotulo ?? "Não avaliável"}</td>}
                {temFaixa && <td>{item.faixa === "fora" ? "fora das faixas" : item.faixa?.rotulo ?? "Não avaliável"}</td>}
                {temCondicao && <td data-situacao={item.condicoes?.situacao ?? ""}>{item.condicoes?.situacao === "ATENDE" ? "Atende"
                  : item.condicoes?.situacao === "NAO_ATENDE" ? "Não atende" : item.condicoes ? "Sem dado" : ""}</td>}
                {temPosicao && <td className="tabular-nums">{item.ordem?.posicao !== null && item.ordem ? item.ordem.posicao + "º" : "—"}</td>}
              </>}
              <td className="whitespace-normal text-xs text-slate-600">{observacao}</td>
            </tr>;
          })}</tbody>
        </table>
      </div>
      {atual.paginas > 1 && <div data-testid="analise-paginas" className="mt-3 flex flex-wrap items-center gap-2 text-xs text-slate-600">
        <span role="status">Linhas {formatarNumero(atual.pagina * POR_PAGINA + 1, true)} a {formatarNumero(Math.min(linhas.length,
          (atual.pagina + 1) * POR_PAGINA), true)} de {formatarNumero(linhas.length, true)}</span>
        <button type="button" data-testid="analise-pagina-anterior" disabled={atual.pagina === 0} onClick={() => setPagina(atual.pagina - 1)}
          className="analise-botao-secundario">Anteriores</button>
        <button type="button" data-testid="analise-pagina-proxima" disabled={atual.pagina >= atual.paginas - 1} onClick={() => setPagina(atual.pagina + 1)}
          className="analise-botao-secundario">Próximas</button>
      </div>}
    </div>

    <div role="tabpanel" id="analise-detalhes-painel-nao-avaliaveis" aria-labelledby="analise-detalhes-aba-nao-avaliaveis" hidden={aba !== "nao-avaliaveis"}
      data-testid="analise-nao-avaliaveis" className="analise-painel-detalhe">
      <p className="text-xs leading-5 text-slate-600">Não avaliável não é zero: sem o valor, o item fica fora do gráfico (ou vazado, com contorno tracejado, quando
        só a camada de cor não tem valor) e aparece aqui com o motivo.{p.fora.some(item => item.aspecto === "mapa")
          ? " Com o mapa à vista, quem não tem coordenada válida fica fora do mapa (no gráfico, continua) e também aparece aqui." : ""}</p>
      {grupos.length ? grupos.map(grupo => <div key={grupo.aspecto} className="mt-2">
        <p className="text-xs font-semibold text-ink">{ASPECTOS[grupo.aspecto]}{grupo.aspecto === "indicador" ? " (" + especie.rotulo.toLowerCase() + ")" : ""}</p>
        <ul className="mt-1 space-y-0.5 text-xs text-slate-700">
          {grupo.itens.map(item => <li key={grupo.aspecto + item.id} data-testid="analise-nao-avaliavel" data-id={item.id} data-aspecto={item.aspecto}>
            <strong className="font-semibold text-ink">{item.rotulo}</strong>: {item.motivo}</li>)}
        </ul>
      </div>) : <p className="mt-2 text-xs text-slate-600">Nenhum item sem valor no estado atual do gráfico.</p>}
    </div>

    <div role="tabpanel" id="analise-detalhes-painel-metodo" aria-labelledby="analise-detalhes-aba-metodo" hidden={aba !== "metodo"}
      data-testid="analise-metodo" className="analise-painel-detalhe text-xs leading-5 text-slate-700">
      <ul className="list-disc space-y-1 pl-5">
        {r.referencia?.origem && p.distancia && <li>Referência: {r.referencia.origem}.</li>}
        {p.distancia && <li data-testid="analise-metodo-tpl11">{NOTA_TPL11}</li>}
        {r.tendencia && r.tendencia.janela.length > 0 && <li>Janela da tendência: {r.tendencia.janela.map(exibirCompetencia).join(", ")} (CAP-TEN-01,
          rótulos de DA-15).{r.tendencia.bloqueio ? " " + r.tendencia.bloqueio : ""}</li>}
        {r.serie && <li data-testid="analise-metodo-serie">Série temporal: {exibirCompetencia(r.serie.inicio)} a {exibirCompetencia(r.serie.fim)}{" "}
          ({r.serie.competencias.length} competências), com o valor observado em cada uma, sem classificação.</li>}
        {r.grupos && <li>Grupos por posição ({r.grupos.tipo}) calculados com o método dos quantis (CAP-DIS-02); com empates, os grupos podem ter tamanhos diferentes.</li>}
        {r.faixas && <li>Faixas digitadas: intervalos [a, b) com as contagens de cada faixa (CAP-DIS-03).</li>}
        {(r.notas || []).map(nota => <li key={"n" + nota}>{nota}</li>)}
        {(r.limitacoes || []).map(codigo => <li key={"l" + codigo} data-limitacao={codigo}>{textoDaLimitacao(codigo)}</li>)}
        <li>Na tela, os valores aparecem arredondados (duas casas nas medidas contínuas); a precisão integral fica no cálculo e no CSV.</li>
      </ul>
      <p className="mt-2 text-[11px] text-slate-600">{maiuscula(p.rotulos.unidade.plural)} · competência {exibirCompetencia(r.competencia)}
        {r.competencia_inicial ? " · competência inicial " + exibirCompetencia(r.competencia_inicial) : ""} · categoria {r.categoria} · versão da
        base {String(r.versao_base || "").slice(0, 12)} · chave de execução {String(r.chave_execucao || "").slice(0, 12)}
        {r.sessao?.registrado ? " · registrado na sessão" : ""}</p>
    </div>
  </section>;
}
