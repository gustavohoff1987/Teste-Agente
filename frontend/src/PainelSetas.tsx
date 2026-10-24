import { useEffect, useMemo, useState, type ReactNode } from "react";
import {
  ArrowDownRight, ArrowUpDown, ArrowUpRight, ChevronDown, ChevronsDown, ChevronsUp, ChevronUp, CircleDashed, Minus, type LucideIcon,
} from "lucide-react";
import type { PainelIndicador, PainelItem } from "./painelApi";
import {
  INDICADORES, artigo, descricaoDasSetas, direcaoDaVariacao, exibirCompetencia, explicacaoDaTendencia, formatarNumero, formatarVariacao, generoDe, maiuscula,
  montarSetas, ordemDoQuadro, paginar, paletaDoGrafico, posicoesTemporais, sinalDoAvanco, valorDe, variacaoDe,
  type PaletaDoGrafico, type RotulosTerritoriais, type SinalDoAvanco,
} from "./painelModel";
import { useEsquemaDeCor } from "./useEsquemaDeCor";

// Quadro de setas da Análise de Tendência, visão Classes (24/10/2026, pedido do responsável): como um painel de cotações, uma linha
// por unidade com os períodos da janela, uma seta por avanço (alta, queda ou pausa, pelo sinal da velocidade do motor), o último
// valor, a variação entre o primeiro e o último período (CAP-TMP-01, do motor) e a classe (CAP-TEN-01, do motor). A tela só
// posiciona e ordena; não classifica nada (RQ-REP-02). Cores da paleta validada pela skill de visualização: alta no azul e queda no
// laranja das famílias da tendência (todos os pares PASS nos dois esquemas: CVD ΔE 24,7 no claro e 26,8 no escuro), pausa no cinza
// de apoio (3,5:1 no claro; 4,85:1 no escuro); a forma da seta também diz a direção. Cada linha tem a própria escala vertical: o
// desenho mostra o caminho, e os valores ficam ao lado e na dica. A tabela dos Detalhes é a versão em tabela.

const POR_PAGINA_SETAS = 50;
const LARGURA = 212, ALTURA = 44, MARGEM_X = 10, MARGEM_Y = 8;
const ICONES: Record<string, LucideIcon> = {
  CRESCIMENTO: ChevronUp, CRESCIMENTO_ACELERADO: ChevronsUp, CRESCIMENTO_DESACELERADO: ArrowUpRight,
  DECLINIO: ChevronDown, DECLINIO_ACELERADO: ChevronsDown, DECLINIO_DESACELERADO: ArrowDownRight,
};
const GLIFOS: Record<SinalDoAvanco, string> = { alta: "▲", queda: "▼", pausa: "►" };

/** Cor de cada avanço: as da paleta do esquema em uso (claro ou escuro). */
const corDoSinal = (sinal: SinalDoAvanco, paleta: PaletaDoGrafico) =>
  sinal === "alta" ? paleta.tendencia.CRESCIMENTO : sinal === "queda" ? paleta.tendencia.DECLINIO : paleta.muda;
/** "06/21": o rótulo curto do período no cabeçalho do desenho (a dica e a lista do campo Período trazem o ano inteiro). */
const curta = (c: string) => /^\d{6}$/.test(c) ? c.slice(4) + "/" + c.slice(2, 4) : c;

type Props = {
  itens: PainelItem[];
  janela: string[];
  indicador: PainelIndicador;
  rotulos: RotulosTerritoriais;
  selecionados: string[];
  /** A ordenação do motor em uso: as linhas seguem a posição dela. */
  pelaPosicao: boolean;
  /** Condições em uso: a situação de cada unidade aparece ao lado do nome. */
  condicoes: boolean;
  /** Legenda da camada de cor (as famílias com as contagens do motor), a mesma do gráfico. */
  legenda: ReactNode;
  onAlternar: (id: string) => void;
  /** Destaque cruzado com o mapa no lado a lado. */
  ativoExterno?: string | null;
  onAtivo?: (id: string | null) => void;
};

function Desenho({ item, janela, paleta }: { item: PainelItem; janela: string[]; paleta: PaletaDoGrafico }) {
  const { pontos, setas } = montarSetas(item.tendencia, janela, { x0: MARGEM_X, x1: LARGURA - MARGEM_X, y0: MARGEM_Y, y1: ALTURA - MARGEM_Y });
  return <svg width={LARGURA} height={ALTURA} viewBox={`0 0 ${LARGURA} ${ALTURA}`} aria-hidden="true" className="analise-setas-desenho">
    <line x1={MARGEM_X} x2={LARGURA - MARGEM_X} y1={ALTURA - 1} y2={ALTURA - 1} stroke={paleta.grade} strokeWidth={1}/>
    {setas.map(seta => {
      const cor = corDoSinal(seta.sinal, paleta);
      return <g key={seta.de + seta.ate} data-testid="analise-seta" data-sinal={seta.sinal} data-de={seta.de} data-ate={seta.ate}>
        <line x1={seta.x1} y1={seta.y1} x2={seta.x2} y2={seta.y2} stroke={cor} strokeWidth={2} strokeLinecap="round"/>
        {/* A ponta da seta só quando o avanço tem espaço para ela (numa janela longa, pedida na conversa, fica só a cor). */}
        {Math.hypot(seta.x2 - seta.x1, seta.y2 - seta.y1) >= 18 && <path d="M -3.5 -4.5 L 2 0 L -3.5 4.5" fill="none" stroke={cor}
          strokeWidth={2} strokeLinecap="round" strokeLinejoin="round"
          transform={`translate(${seta.meioX.toFixed(1)} ${seta.meioY.toFixed(1)}) rotate(${seta.angulo.toFixed(1)})`}/>}
      </g>;
    })}
    {pontos.map(ponto => <circle key={ponto.competencia} cx={ponto.x} cy={ponto.y} r={4} fill={paleta.tinta2} stroke={paleta.superficie} strokeWidth={2}
      data-testid="analise-seta-ponto" data-competencia={ponto.competencia} data-valor={ponto.valor}/>)}
  </svg>;
}

function Classe({ item, paleta }: { item: PainelItem; paleta: PaletaDoGrafico }) {
  const t = item.tendencia;
  if (!t || !t.avaliavel || !t.classe) return <span className="analise-seta-classe">
    <CircleDashed size={16} color={paleta.naoAvaliavel} aria-hidden="true"/><span>Não avaliável</span></span>;
  const Icone = ICONES[t.classe] ?? (t.motivoCodigo === "SERIE_ESTAVEL" ? Minus : ArrowUpDown);
  return <span className="analise-seta-classe">
    <Icone size={16} strokeWidth={2.4} color={paleta.tendencia[t.familia ?? "NENHUMA"]} aria-hidden="true"/><span>{t.rotulo}</span></span>;
}

/** A dica da linha (no mouse e no foco): cada período com o valor e o avanço até ele, a variação do motor e o que a classe quer dizer. */
function Dica({ item, indicador, paleta, id }: { item: PainelItem; indicador: PainelIndicador; paleta: PaletaDoGrafico; id: string }) {
  const t = item.tendencia, especie = INDICADORES[indicador];
  const sinalAte = new Map((t?.velocidades ?? []).map(v => [v.ate, sinalDoAvanco(v.valor)]));
  const observacoes = t?.observacoes ?? [];
  const variacao = variacaoDe(item, indicador);
  const primeira = observacoes[0]?.competencia, ultima = observacoes.at(-1)?.competencia;
  return <div id={id} role="tooltip" data-testid="analise-seta-dica" className="analise-seta-dica">
    <p className="analise-seta-dica-titulo">{item.rotulo}</p>
    <ol className="analise-seta-dica-periodos">
      {observacoes.map(obs => {
        const sinal = sinalAte.get(obs.competencia);
        return <li key={obs.competencia}>
          <span className="tabular-nums">{exibirCompetencia(obs.competencia)}</span>
          <strong className="tabular-nums">{obs.valor === null ? "sem valor" : formatarNumero(obs.valor, especie.contagem)}</strong>
          {sinal ? <span><span aria-hidden="true" style={{ color: corDoSinal(sinal, paleta) }}>{GLIFOS[sinal]}</span> {sinal}</span> : <span/>}
        </li>;
      })}
    </ol>
    {primeira && ultima && primeira !== ultima && <p>Variação da {especie.rotulo.toLowerCase()} de {exibirCompetencia(primeira)} a{" "}
      {exibirCompetencia(ultima)}: <strong className="tabular-nums">{formatarVariacao(variacao)}</strong> ({direcaoDaVariacao(variacao)}).</p>}
    {t && <p>{explicacaoDaTendencia(t)}</p>}
  </div>;
}

export default function PainelSetas(p: Props) {
  const paleta = paletaDoGrafico(useEsquemaDeCor());
  const [ativo, setAtivo] = useState<string | null>(null);
  const [pagina, setPagina] = useState(0);
  const ordenados = useMemo(() => ordemDoQuadro(p.itens, p.indicador, p.pelaPosicao), [p.itens, p.indicador, p.pelaPosicao]);
  // Um filtro novo (classe, régua, condições) recomeça na primeira página.
  useEffect(() => setPagina(0), [p.itens, p.pelaPosicao]);
  const atual = paginar(ordenados, pagina, POR_PAGINA_SETAS);
  const especie = INDICADORES[p.indicador];
  const unidade = p.rotulos.unidade;
  const tempos = posicoesTemporais(p.janela);
  const fim = Math.max(1, ...tempos.values());
  const selecionados = new Set(p.selecionados);
  const ativar = (id: string | null) => { setAtivo(id); p.onAtivo?.(id); };

  return <section data-testid="analise-setas" aria-label={"Quadro de setas da tendência: " + formatarNumero(ordenados.length, true) + " " +
    (ordenados.length === 1 ? unidade.singular : unidade.plural)} className="analise-setas">
    {ordenados.length ? <>
      <div className="analise-setas-cabecalho" aria-hidden="true">
        <span>{maiuscula(unidade.singular)}</span>
        <svg width={LARGURA} height={16} viewBox={`0 0 ${LARGURA} 16`} className="analise-setas-eixo">
          {p.janela.map((c, indice) => {
            // Até 5 períodos, todos os rótulos; numa janela longa, só o primeiro e o último, sem se sobreporem.
            if (p.janela.length > 5 && indice !== 0 && indice !== p.janela.length - 1) return null;
            const x = MARGEM_X + (LARGURA - MARGEM_X * 2) * ((tempos.get(c) ?? 0) / fim);
            return <text key={c} x={x} y={12} textAnchor={indice === 0 ? "start" : indice === p.janela.length - 1 ? "end" : "middle"}
              className="analise-marca-texto">{curta(c)}</text>;
          })}
        </svg>
        <span>Último valor · variação</span>
        <span>Classe (do motor)</span>
      </div>
      <ol className="analise-setas-linhas">
        {atual.linhas.map(item => {
          const valor = valorDe(item, p.indicador), variacao = variacaoDe(item, p.indicador);
          const direcao = variacao === null ? null : variacao > 0 ? "alta" : variacao < 0 ? "queda" : "pausa";
          const posicao = p.pelaPosicao && item.ordem?.posicao ? item.ordem.posicao + "º " : "";
          const idDica = "analise-seta-dica-" + item.id.replace(/[^a-zA-Z0-9_-]/g, "_");
          return <li key={item.id} className="analise-seta-item">
            <button type="button" data-testid="analise-seta-linha" data-id={item.id} data-classe={item.tendencia?.avaliavel ? item.tendencia.classe ?? "" : "NAO_AVALIAVEL"}
              data-selecionado={selecionados.has(item.id) ? "true" : "false"} data-ativo={p.ativoExterno === item.id ? "true" : undefined}
              aria-pressed={selecionados.has(item.id)} aria-describedby={ativo === item.id ? idDica : undefined}
              aria-label={(posicao ? posicao + "lugar, " : "") + descricaoDasSetas(item, p.indicador)} className="analise-seta-linha"
              onClick={() => p.onAlternar(item.id)} onPointerEnter={() => ativar(item.id)} onPointerLeave={() => ativar(null)}
              onFocus={() => ativar(item.id)} onBlur={() => ativar(null)} onKeyDown={event => { if (event.key === "Escape") ativar(null); }}>
              <span className="analise-seta-nome">
                {posicao && <span className="analise-seta-posicao">{posicao}</span>}
                <span className="truncate" title={item.rotulo}>{item.rotulo}</span>
                {p.condicoes && item.condicoes && <span className="analise-seta-condicao">{item.condicoes.situacao === "ATENDE" ? "atende"
                  : item.condicoes.situacao === "NAO_ATENDE" ? "não atende" : "sem dado"}</span>}
              </span>
              <Desenho item={item} janela={p.janela} paleta={paleta}/>
              <span className="analise-seta-numeros">
                <strong className="tabular-nums">{valor === null ? "—" : formatarNumero(valor, especie.contagem)}</strong>
                <span className="tabular-nums">{direcao && <span aria-hidden="true" style={{ color: corDoSinal(direcao, paleta) }}>{GLIFOS[direcao]} </span>}
                  {formatarVariacao(variacao)}</span>
              </span>
              <Classe item={item} paleta={paleta}/>
            </button>
            {ativo === item.id && <Dica item={item} indicador={p.indicador} paleta={paleta} id={idDica}/>}
          </li>;
        })}
      </ol>
      {atual.paginas > 1 && <div data-testid="analise-setas-paginas" className="mt-3 flex flex-wrap items-center gap-2 text-xs text-slate-600">
        <span role="status">Linhas {formatarNumero(atual.pagina * POR_PAGINA_SETAS + 1, true)} a {formatarNumero(Math.min(ordenados.length,
          (atual.pagina + 1) * POR_PAGINA_SETAS), true)} de {formatarNumero(ordenados.length, true)}</span>
        <button type="button" data-testid="analise-setas-anterior" disabled={atual.pagina === 0} onClick={() => setPagina(atual.pagina - 1)}
          className="analise-botao-secundario">Anteriores</button>
        <button type="button" data-testid="analise-setas-proxima" disabled={atual.pagina >= atual.paginas - 1} onClick={() => setPagina(atual.pagina + 1)}
          className="analise-botao-secundario">Próximas</button>
      </div>}
    </> : <p className="analise-vazio">Nenhum{generoDe(unidade) === "f" ? "a" : ""} {unidade.singular} com estes filtros.</p>}
    <div className="analise-legenda">
      <ul data-testid="analise-setas-legenda" className="flex flex-wrap gap-x-4 gap-y-1" aria-label="Setas: o avanço de um período para o seguinte">
        {(["alta", "queda", "pausa"] as const).map(sinal => <li key={sinal} className="flex items-center gap-1.5">
          <span aria-hidden="true" style={{ color: corDoSinal(sinal, paleta) }}>{GLIFOS[sinal]}</span>
          {sinal === "alta" ? "Alta" : sinal === "queda" ? "Queda" : "Pausa"}</li>)}
      </ul>
      {p.legenda}
      <p className="max-w-xl">Cada seta é o avanço de um período para o seguinte, pelo sinal calculado pelo motor. Cada linha tem a própria escala
        vertical: o desenho mostra o caminho, e os valores estão ao lado, na dica e na tabela dos Detalhes. Clique numa linha para escolher{" "}
        {artigo(unidade, false)} {unidade.singular} (Séries e Comparar).</p>
    </div>
  </section>;
}
