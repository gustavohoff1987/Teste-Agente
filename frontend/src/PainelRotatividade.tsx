import { useEffect, useState } from "react";
import type { PainelItem } from "./painelApi";
import { COR_BOLHA, COR_NEUTRA, exibirCompetencia, formatarNumero, formatarPercentual, paginar, umA, type RotulosTerritoriais } from "./painelModel";

// Rotatividade (CAP-ROT-01) em barras de 100% (Adendo BOL aprovado em 22/10/2026): uma barra por unidade, com a permanência
// e a saída da coorte inicial. Os percentuais e as contagens vêm do motor; a tela não divide nada. "Da coorte inicial" vai em
// todo rótulo (RQ-REP-11). Sem linha nem série (L1794). As coortes não avaliáveis ficam em Não avaliáveis, com o motivo.

const POR_PAGINA = 30;
type Props = { itens: PainelItem[]; rotulos: RotulosTerritoriais; inicial: string; final: string };

export default function PainelRotatividade({ itens, rotulos, inicial, final }: Props) {
  const [pagina, setPagina] = useState(0);
  useEffect(() => setPagina(0), [itens]);
  const atual = paginar(itens, pagina, POR_PAGINA);
  return <figure data-testid="analise-rotatividade" className="analise-grafico m-0">
    <ul className="space-y-2" aria-label={"Permanência e saída da coorte inicial, de " + exibirCompetencia(inicial) + " a " + exibirCompetencia(final)}>
      {atual.linhas.map(item => {
        const r = item.rotatividade!;
        const temBarra = r.permanencia !== null && r.saida !== null;
        return <li key={item.id} data-testid="analise-rot-linha" data-id={item.id} data-permanencia={r.permanencia ?? ""} data-saida={r.saida ?? ""}
          className="analise-rot-linha">
          <span className="analise-rot-nome" title={item.rotulo}>{item.rotulo}</span>
          <span className="analise-rot-barra" aria-hidden="true">
            {temBarra && <>
              {r.permanencia! > 0 && <span style={{ width: `calc(${r.permanencia}% - ${r.saida! > 0 ? 1 : 0}px)`, background: COR_BOLHA }}
                className="analise-rot-segmento analise-rot-inicio"/>}
              {r.saida! > 0 && <span style={{ width: `calc(${r.saida}% - ${r.permanencia! > 0 ? 1 : 0}px)`, background: COR_NEUTRA }}
                className="analise-rot-segmento analise-rot-fim"/>}
            </>}
          </span>
          <span className="analise-rot-texto">
            <strong className="text-ink">{formatarPercentual(r.permanencia)}</strong> permaneceram ·{" "}
            <strong className="text-ink">{formatarPercentual(r.saida)}</strong> saíram da coorte inicial
            {r.coorteInicial !== null && <> (coorte inicial: {formatarNumero(r.coorteInicial, true)}
              {r.permaneceram !== null ? "; permaneceram " + formatarNumero(r.permaneceram, true) : ""}
              {r.sairam !== null ? "; saíram " + formatarNumero(r.sairam, true) : ""})</>}
          </span>
        </li>;
      })}
    </ul>
    {!itens.length && <p role="status" className="analise-grafico-vazio">Nenhuma coorte avaliável para desenhar (veja Não avaliáveis, em Detalhes).</p>}
    {atual.paginas > 1 && <div className="mt-3 flex flex-wrap items-center gap-2 text-xs text-slate-600">
      <span role="status">Barras {formatarNumero(atual.pagina * POR_PAGINA + 1, true)} a {formatarNumero(Math.min(itens.length, (atual.pagina + 1) * POR_PAGINA), true)} de {formatarNumero(itens.length, true)}</span>
      <button type="button" className="analise-botao-secundario" disabled={atual.pagina === 0} onClick={() => setPagina(atual.pagina - 1)}>Anteriores</button>
      <button type="button" className="analise-botao-secundario" disabled={atual.pagina >= atual.paginas - 1} onClick={() => setPagina(atual.pagina + 1)}>Próximas</button>
    </div>}
    <figcaption className="analise-legenda">
      <ul className="flex flex-wrap gap-x-4 gap-y-1" aria-label="Partes da barra">
        <li className="flex items-center gap-1.5"><span className="analise-amostra" style={{ background: COR_BOLHA }} aria-hidden="true"/>Permaneceram (da coorte inicial)</li>
        <li className="flex items-center gap-1.5"><span className="analise-amostra" style={{ background: COR_NEUTRA }} aria-hidden="true"/>Saíram (da coorte inicial)</li>
      </ul>
      <p className="max-w-xl">Cada barra é {umA(rotulos.unidade)}: a coorte inicial reúne as pessoas distintas
        de {exibirCompetencia(inicial)}, e a permanência é conferida em {exibirCompetencia(final)}. Percentuais e contagens do motor.</p>
    </figcaption>
  </figure>;
}
