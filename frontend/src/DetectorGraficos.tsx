import { useMemo } from "react";
import MapaDosConjuntos, { type PinturaDoPonto } from "./MapaDosConjuntos";
import PainelChart from "./PainelChart";
import PainelSeries from "./PainelSeries";
import type { PainelResposta } from "./painelApi";
import { ROTULOS_BRASIL, paletaDoGrafico } from "./painelModel";
import { useEsquemaDeCor } from "./useEsquemaDeCor";
import {
  CORES_DOS_NIVEIS, NIVEIS, NOMES_DOS_NIVEIS, camadasDoMapa, competenciaCurta, criterioDoContexto, dominiosDoContexto, formatarInteiro, formatarTaxa,
  itensDoContexto, nivelNoDesenho, nomeDoSinal, seriesDoComparativo, textoDosTrechos,
  type DetalheDoDetector, type LinhaDoDetector, type NivelDoAlerta, type RespostaDoDetector,
} from "./detectorModel";

// As visões Mapa e Gráfico do Detector de Sinais (comando V23, Proposta V3, seção B.3) e a série da taxa do detalhe, com os
// componentes que o Agente já tem. Nada é calculado aqui: o mapa, as bolhas e a série desenham os valores, os níveis e as
// coordenadas que o motor mandou (POST /api/detector).
// - MapaDosNiveis: o mapa de pontos da Seleção (MapaDosConjuntos), com cada município pintado pelo nível do alerta (ou, com o
//   filtro "Sinal", pelo nível daquele sinal), os conjuntos pelo contorno e o nome de cada grupo de cima junto aos pontos dele.
//   O produto não tem a malha das divisas: o nome do grupo situa os pontos, sem desenhar divisa que a base não tem.
// - BolhasDoContexto: o gráfico de bolhas do Agente (PainelChart), com X = a distância até o território mais próximo que atende
//   ao critério (sinal 11), Y = a taxa por 1.000 habitantes (sinal 8), o tamanho pela população e a cor pelo nível.
// - SerieDaTaxa: a Série temporal do Agente (PainelSeries), com a taxa do território e a da referência dele (sinais 8 e 10).
// O nível vem sempre escrito também (legenda, dica e lista), nunca só pela cor.

type DoDetector = { resposta: RespostaDoDetector; linhas: LinhaDoDetector[]; sinal: string };
const RAIOS: Record<NivelDoAlerta, number> = { moderado: 3.2, elevado: 4, critico: 4.8 };

/** A legenda dos níveis: a cor, o nome por extenso e quantos territórios à vista. */
function LegendaDosNiveis({ contagens, semNivel }: { contagens: Record<NivelDoAlerta, number>; semNivel: number }) {
  return <p data-testid="detector-legenda-niveis" className="ferramenta-legenda">
    {NIVEIS.map(nivel => <span key={nivel} data-nivel={nivel} data-quantos={contagens[nivel]}>
      <span className="ferramenta-nivel-ponto" style={{ background: CORES_DOS_NIVEIS[nivel] }} aria-hidden="true"/>
      {NOMES_DOS_NIVEIS[nivel]}: {formatarInteiro(contagens[nivel])}</span>)}
    <span data-nivel="" data-quantos={semNivel}><span className="ferramenta-nivel-ponto ferramenta-nivel-ponto-sem" aria-hidden="true"/>
      Sem nível no desenho: {formatarInteiro(semNivel)}</span>
  </p>;
}

export function MapaDosNiveis({ resposta, linhas, sinal, onAbrir }: DoDetector & { onAbrir: (id: string) => void }) {
  const r = resposta.fonte.rotulos;
  const camadas = useMemo(() => camadasDoMapa(resposta, linhas, sinal), [resposta, linhas, sinal]);
  const coordenadas = useMemo(() => new Map(Object.entries(resposta.coordenadas)), [resposta.coordenadas]);
  const nomes = useMemo(() => new Map(resposta.linhas.map(linha => [linha.id, linha.rotulo])), [resposta.linhas]);
  const naLista = useMemo(() => new Set(resposta.linhas.map(linha => linha.id)), [resposta.linhas]);
  const pintura = useMemo(() => {
    const mapa = new Map<string, PinturaDoPonto>();
    for (const nivel of NIVEIS) for (const id of camadas.porNivel[nivel])
      mapa.set(id, { cor: CORES_DOS_NIVEIS[nivel], raio: RAIOS[nivel], chave: nivel, rotulo: "nível " + NOMES_DOS_NIVEIS[nivel].toLowerCase() });
    return mapa;
  }, [camadas]);
  const contagens = { critico: camadas.porNivel.critico.length, elevado: camadas.porNivel.elevado.length, moderado: camadas.porNivel.moderado.length };
  const doQue = sinal === "todos" || sinal === "juntos" || sinal === "registro" ? "do alerta do território" : "de “" + nomeDoSinal(sinal, r) + "”";
  return <figure data-testid="detector-mapa" data-sinal={sinal} data-critico={contagens.critico} data-elevado={contagens.elevado}
    data-moderado={contagens.moderado} data-fundo={camadas.fundo.length} data-conjuntos={camadas.conjuntos.length} data-grupos={camadas.grupos.length}
    className="ferramenta-grafico">
    <MapaDosConjuntos coordenadas={coordenadas} fundo={camadas.fundo} conjuntos={camadas.conjuntos} pintura={pintura} grupos={camadas.grupos}
      nomeDe={id => nomes.get(id) ?? id} largura={760} altura={440}
      rotulo={"Mapa dos territórios à vista em " + competenciaCurta(resposta.janela.fim) + ", pelo nível " + doQue + ": " +
        formatarInteiro(contagens.critico) + " em crítico, " + formatarInteiro(contagens.elevado) + " em elevado e " + formatarInteiro(contagens.moderado) + " em moderado"}
      vazio={"Nenhum " + r.unidade + " à vista tem coordenada válida para o mapa."} onTocar={id => { if (naLista.has(id)) onAbrir(id); }}
      legenda={"pontos coloridos: o nível " + doQue + " · pontos claros: sem nível · tracejado: conjunto · letras: o " + r.grupo + " dos pontos"}/>
    <LegendaDosNiveis contagens={contagens} semNivel={camadas.fundo.length}/>
    <figcaption className="ferramenta-apoio">Onde ficam os territórios à vista, pelo nível {doQue}. Os pontos usam as coordenadas da data avaliada; o{" "}
      {r.grupo} como unidade não tem ponto, e o conjunto aparece pelo contorno, sem nível. A base não tem as divisas: a sigla situa os pontos de cada{" "}
      {r.grupo}. Para ver um sinal só, escolha-o no filtro “Sinal”. Toque num ponto para abrir os detalhes do território.</figcaption>
  </figure>;
}

export function BolhasDoContexto({ resposta, linhas, sinal, onAbrir }: DoDetector & { onAbrir: (id: string) => void }) {
  const paleta = paletaDoGrafico(useEsquemaDeCor());
  const r = resposta.fonte.rotulos;
  const itens = useMemo(() => itensDoContexto(linhas), [linhas]);
  const dados = useMemo(() => ({ competencia: resposta.janela.fim, competencia_inicial: null,
    dominios: dominiosDoContexto(itens) }) as unknown as PainelResposta, [resposta.janela.fim, itens]);
  const nomes = useMemo(() => new Map(itens.map(item => [item.id, item.rotulo])), [itens]);
  const niveis = useMemo(() => new Map(linhas.map(linha => [linha.id, nivelNoDesenho(linha, sinal)])), [linhas, sinal]);
  const criterio = resposta.comparacao.contexto;
  if (!itens.length) return <p data-testid="detector-bolhas-vazio" role="status" className="ferramenta-apoio">Nenhum território à vista tem distância a
    mostrar: os que atendem ao critério não têm distância, e o {r.grupo} como unidade não tem um ponto único.</p>;
  const contagens = { critico: 0, elevado: 0, moderado: 0 };
  let semNivel = 0;
  for (const item of itens) { const nivel = niveis.get(item.id); if (nivel) contagens[nivel] += 1; else semNivel += 1; }
  return <figure data-testid="detector-bolhas" data-itens={itens.length} data-critico={contagens.critico} data-elevado={contagens.elevado}
    data-moderado={contagens.moderado} className="ferramenta-grafico">
    <PainelChart resposta={dados} itens={itens} todos={itens} indicador="densidade" escala="linear" distancia cometa={false} porItem vista="final"
      fase="parado" pintura={item => { const nivel = niveis.get(item.id); return { cor: nivel ? CORES_DOS_NIVEIS[nivel] : paleta.neutra, vazada: false, apagada: !nivel }; }}
      selecionados={[]} limiares={[]} nomes={nomes}
      carregando={false} rotuloDistancia={"Distância até o " + r.unidade + " mais próximo que atende ao critério (km)"} rotulos={ROTULOS_BRASIL}
      contextoBrasil={criterio.taxaMinima !== null ? { valor: criterio.taxaMinima, rotulo: "Critério " + formatarTaxa(criterio.taxaMinima) } : null}
      cortes={[]} corte={null} faixasDistancia={[]} unidadesDoGrupo={() => null} legendaCor={null} notas={[]} onAlternar={() => undefined}
      onAbrirGrupo={() => undefined} onAbrirUnidade={onAbrir}/>
    <LegendaDosNiveis contagens={contagens} semNivel={semNivel}/>
    <figcaption className="ferramenta-apoio">Cada bolha é um território à vista com distância a mostrar ({formatarInteiro(itens.length)}), pintado pelo
      nível. Na horizontal, a distância em linha reta até o {criterioDoContexto(criterio.taxaMinima, r) ?? r.unidade + " mais próximo que atende ao critério"};
      na vertical, a taxa de {r.profissionais} por 1.000 habitantes em {competenciaCurta(resposta.janela.fim)}; o tamanho mostra a população. A linha
      tracejada é a taxa do critério. A distância é só contexto: não é distância por estrada nem acesso, e nunca vira alerta. Toque numa bolha para abrir os
      detalhes do território.</figcaption>
  </figure>;
}

export function SerieDaTaxa({ detalhe, profissionais = "médicos" }: { detalhe: DetalheDoDetector; profissionais?: string }) {
  const series = useMemo(() => seriesDoComparativo(detalhe), [detalhe]);
  if (!series || !detalhe.comparativo) return null;
  return <figure data-testid="detector-serie-da-taxa" data-referencias={series.referencias.length} className="ferramenta-grafico">
    <PainelSeries itens={[series.item]} competencias={detalhe.comparativo.competencias} indicador="densidade" rotulos={ROTULOS_BRASIL}
      referencias={series.referencias}/>
    <figcaption className="ferramenta-apoio">Taxa de {profissionais} por 1.000 habitantes de {detalhe.rotulo} em cada registro{series.referencias.length
      ? " e, tracejada, a dos " + detalhe.comparativo.referencia.rotulo : ""}. O valor de cada data vale nela; a variação entre datas só é
      lida {textoDosTrechos(detalhe.comparativo.trechos)}, quando a população da base é comparável de um ano para o outro.
      {detalhe.comparativo.referencia.motivo ? " " + detalhe.comparativo.referencia.motivo : ""}</figcaption>
  </figure>;
}
