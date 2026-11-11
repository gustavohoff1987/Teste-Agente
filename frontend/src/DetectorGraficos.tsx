import { useMemo } from "react";
import MapaDosConjuntos from "./MapaDosConjuntos";
import PainelChart from "./PainelChart";
import PainelSeries from "./PainelSeries";
import type { PainelResposta } from "./painelApi";
import { ROTULOS_BRASIL, paletaDoGrafico } from "./painelModel";
import { useEsquemaDeCor } from "./useEsquemaDeCor";
import {
  FILTROS_DE_FENOMENO, camadasDoMapa, competenciaCurta, dominiosDoContexto, formatarInteiro, formatarTaxa, itensDoContexto, seriesDoComparativo,
  type DetalheDoDetector, type LinhaDoDetector, type RespostaDoDetector,
} from "./detectorModel";

// Os fenômenos 8 a 12 do Detector de Sinais Territoriais em gráfico e mapa (comando V22, etapa 5; pedido do responsável em
// 10/11/2026: reaproveitar os componentes que o Agente já tem, com a tabela como detalhe). Nada é calculado aqui: as bolhas, a série
// e o mapa desenham os valores e as coordenadas que o motor mandou (POST /api/detector).
// - BolhasDoContexto: o gráfico de bolhas do Agente (PainelChart), com X = a distância até o município mais próximo que atende ao
//   critério (fenômeno 11), Y = a taxa por 1.000 habitantes (fenômeno 8) e o tamanho pela população.
// - MapaDosSinais: o mapa de pontos da Seleção (MapaDosConjuntos), com os territórios do fenômeno em destaque, os conjuntos pelo
//   contorno e os municípios de referência do contexto geográfico vazados.
// - SerieDaTaxa: a Série temporal do Agente (PainelSeries), com a taxa do território e a da referência dele (fenômenos 8 e 10).

type DoDetector = { resposta: RespostaDoDetector; linhas: LinhaDoDetector[] };

export function BolhasDoContexto({ resposta, linhas, onAbrir }: DoDetector & { onAbrir: (id: string) => void }) {
  const paleta = paletaDoGrafico(useEsquemaDeCor());
  const itens = useMemo(() => itensDoContexto(linhas), [linhas]);
  const dados = useMemo(() => ({ competencia: resposta.janela.fim, competencia_inicial: null,
    dominios: dominiosDoContexto(itens) }) as unknown as PainelResposta, [resposta.janela.fim, itens]);
  const nomes = useMemo(() => new Map(itens.map(item => [item.id, item.rotulo])), [itens]);
  const criterio = resposta.comparacao.contexto;
  if (!itens.length) return <p data-testid="detector-bolhas-vazio" role="status" className="ferramenta-apoio">Nenhum território à vista tem distância a
    mostrar: os que atendem ao critério não têm distância, e os estados como unidade não têm um ponto único.</p>;
  return <figure data-testid="detector-bolhas" data-itens={itens.length} className="ferramenta-grafico">
    <PainelChart resposta={dados} itens={itens} todos={itens} indicador="densidade" escala="linear" distancia cometa={false} porItem vista="final"
      fase="parado" pintura={() => ({ cor: paleta.bolha, vazada: false, apagada: false })} selecionados={[]} limiares={[]} nomes={nomes}
      carregando={false} rotuloDistancia="Distância até o município mais próximo que atende ao critério (km)" rotulos={ROTULOS_BRASIL}
      contextoBrasil={criterio.taxaMinima !== null ? { valor: criterio.taxaMinima, rotulo: "Critério " + formatarTaxa(criterio.taxaMinima) } : null}
      cortes={[]} corte={null} faixasDistancia={[]} unidadesDoGrupo={() => null} legendaCor={null} notas={[]} onAlternar={() => undefined}
      onAbrirGrupo={() => undefined} onAbrirUnidade={onAbrir}/>
    <figcaption className="ferramenta-apoio">Cada bolha é um território da tabela com distância a mostrar ({formatarInteiro(itens.length)}). Na horizontal, a
      distância em linha reta até o município mais próximo que atende ao critério; na vertical, a taxa de médicos por 1.000 habitantes em{" "}
      {competenciaCurta(resposta.janela.fim)}; o tamanho mostra a população. A linha tracejada é a taxa do critério. É só contexto: não é distância por
      estrada, acesso nem isolamento, e não tem intensidade. Toque numa bolha para abrir os detalhes do território.</figcaption>
  </figure>;
}

export function MapaDosSinais({ resposta, linhas, fenomeno, onAbrir }: DoDetector & { fenomeno: string; onAbrir: (id: string) => void }) {
  const camadas = useMemo(() => camadasDoMapa(resposta, linhas, fenomeno), [resposta, linhas, fenomeno]);
  const coordenadas = useMemo(() => new Map(Object.entries(resposta.coordenadas)), [resposta.coordenadas]);
  const nomes = useMemo(() => {
    const mapa = new Map(resposta.linhas.map(linha => [linha.id, linha.rotulo]));
    for (const linha of resposta.linhas) if (linha.contexto.referenciaId && linha.contexto.referencia && !mapa.has(linha.contexto.referenciaId))
      mapa.set(linha.contexto.referenciaId, linha.contexto.referencia + " (atende ao critério)");
    return mapa;
  }, [resposta.linhas]);
  const naTabela = useMemo(() => new Set(resposta.linhas.map(linha => linha.id)), [resposta.linhas]);
  const sinal = FILTROS_DE_FENOMENO.find(item => item.chave === camadas.sinal)?.rotulo ?? camadas.sinal;
  const contagem = formatarInteiro(camadas.destaque.length) + (camadas.destaque.length === 1 ? " município" : " municípios");
  return <figure data-testid="detector-mapa" data-sinal={camadas.sinal} data-destaque={camadas.destaque.length} data-fundo={camadas.fundo.length}
    data-referencias={camadas.referencias.length} data-conjuntos={camadas.conjuntos.length} className="ferramenta-grafico">
    <MapaDosConjuntos coordenadas={coordenadas} fundo={camadas.fundo} destaque={camadas.destaque} conjuntos={camadas.conjuntos}
      semConjunto={camadas.referencias} nomeDe={id => nomes.get(id) ?? id} largura={760} altura={440}
      rotulo={"Mapa dos territórios da seleção em " + competenciaCurta(resposta.janela.fim) + ": em destaque, " + contagem + " com “" + sinal + "”"}
      vazio="Nenhum município da seleção tem coordenada válida para o mapa." onTocar={id => { if (naTabela.has(id)) onAbrir(id); }}
      legenda={"pontos cheios: “" + sinal + "” (" + contagem + ") · pontos claros: os demais municípios à vista · tracejado: conjunto · vazados: " +
        "o município mais próximo que atende ao critério do contexto geográfico"}/>
    <figcaption className="ferramenta-apoio">Onde ficam os territórios à vista. Os pontos usam as coordenadas da competência avaliada; estados como unidade
      não têm ponto. Para destacar outro fenômeno, escolha-o no filtro “Fenômeno”. Toque num ponto da seleção para abrir os detalhes.</figcaption>
  </figure>;
}

export function SerieDaTaxa({ detalhe }: { detalhe: DetalheDoDetector }) {
  const series = useMemo(() => seriesDoComparativo(detalhe), [detalhe]);
  if (!series || !detalhe.comparativo) return null;
  return <figure data-testid="detector-serie-da-taxa" data-referencias={series.referencias.length} className="ferramenta-grafico">
    <PainelSeries itens={[series.item]} competencias={detalhe.comparativo.competencias} indicador="densidade" rotulos={ROTULOS_BRASIL}
      referencias={series.referencias}/>
    <figcaption className="ferramenta-apoio">Taxa de médicos por 1.000 habitantes de {detalhe.rotulo} em cada registro{series.referencias.length
      ? " e, tracejada, a da referência (" + detalhe.comparativo.referencia.rotulo + ")" : ""}. O valor de cada data vale nela; a variação entre datas só é
      lida de 2014 a 2017 e de 2018 a 2021, quando a população é comparável (de 2021 a 2023 ela se repete, e a de 2024 é de outra base).
      {detalhe.comparativo.referencia.motivo ? " " + detalhe.comparativo.referencia.motivo : ""}</figcaption>
  </figure>;
}
