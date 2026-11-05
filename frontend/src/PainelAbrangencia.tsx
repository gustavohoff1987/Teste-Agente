import type { AbrangenciaCompleta, ContextoBrasil } from "./painelApi";
import { exibirCompetencia, formatarNumero, profissionaisDe, quantos, type RotulosTerritoriais } from "./painelModel";

// Totais individualizados da abrangência (05/11/2026, comando de seleção territorial unificada; decisão D3). Com o Brasil inteiro na
// análise dos municípios, o total do Brasil é a contagem nacional (fonte nacional); com estados inteiros, o total de cada estado é a
// contagem estadual de pessoas distintas (fonte estadual, UF-CONTAGEM-ESTADUAL-1). Nenhum deles é a soma dos municípios, e os
// totais dos estados não são somados entre si (quem atua em mais de um estado conta em cada um). Um estado marcado só em parte
// (com exclusões ou com alguns municípios) não tem total individualizado: cada município mostra o próprio quantitativo. Todos os
// números vêm do motor (`contexto` de /api/painel); a tela só os mostra. Sem nada completo na abrangência, o quadro não aparece.

export type GrupoParcial = { id: string; nome: string; marcadas: number; total: number };
type Props = {
  completa: AbrangenciaCompleta | null;
  brasil: ContextoBrasil | null;
  parciais: GrupoParcial[];
  categoria: string;
  rotulos: RotulosTerritoriais;
  /** Na Seleção de Territórios, ao lado do que está marcado: menos linhas à vista e sem a nota longa. */
  compacto?: boolean;
};

const LINHAS = 6, LINHAS_COMPACTO = 3;
const densidadeDe = (valor: number | null) => valor === null ? "densidade não avaliável" : formatarNumero(valor, false) + " por 1.000 habitantes";

export default function PainelAbrangencia(p: Props) {
  const estados = p.completa?.estados ?? [];
  const brasil = !!p.completa?.brasil && !!p.brasil;
  if (!brasil && !estados.length) return null;
  const profissionais = profissionaisDe(p.categoria);
  const unidade = p.rotulos.unidade;
  const competencia = brasil ? p.brasil?.competencia : estados[0]?.competencia;
  const limite = p.compacto ? LINHAS_COMPACTO : LINHAS;
  const linhaDoEstado = (estado: AbrangenciaCompleta["estados"][number]) =>
    <li key={estado.id} data-testid="analise-abrangencia-total" data-id={estado.id} data-fonte="estadual"
      data-quantidade={estado.quantidade ?? ""} data-avaliabilidade={estado.avaliabilidade}>
      <strong className="text-ink">{estado.rotulo}, estado inteiro:</strong>{" "}
      {estado.quantidade === null ? "sem contagem estadual nesta competência" : formatarNumero(estado.quantidade, true) + " " + profissionais +
        " na contagem estadual (pessoas distintas no estado)"} · {densidadeDe(estado.densidade)}
      {estado.motivo && <span className="analise-abrangencia-motivo"> {estado.motivo}</span>}
    </li>;
  return <section data-testid="analise-abrangencia" data-compacto={p.compacto ? "true" : "false"} className="analise-abrangencia"
    aria-label="Totais individualizados da abrangência">
    <p className="analise-abrangencia-titulo">Totais individualizados{competencia ? " · " + exibirCompetencia(competencia) : ""}</p>
    <ul className="analise-abrangencia-lista">
      {brasil && p.brasil && <li data-testid="analise-abrangencia-total" data-id="br" data-fonte="nacional" data-quantidade={p.brasil.quantidade ?? ""}>
        <strong className="text-ink">Brasil inteiro:</strong>{" "}
        {p.brasil.quantidade === null ? "sem contagem nacional nesta competência" : formatarNumero(p.brasil.quantidade, true) + " " + profissionais +
          " na contagem nacional"} · {densidadeDe(p.brasil.densidade)}
      </li>}
      {estados.slice(0, limite).map(linhaDoEstado)}
    </ul>
    {estados.length > limite && <details className="analise-abrangencia-mais">
      <summary>Mais {quantos(estados.length - limite, { singular: "estado inteiro", plural: "estados inteiros", genero: "m" })}</summary>
      <ul className="analise-abrangencia-lista">{estados.slice(limite).map(linhaDoEstado)}</ul>
    </details>}
    <p data-testid="analise-abrangencia-nota" className="analise-abrangencia-nota">
      {brasil ? "O total do Brasil vem da fonte nacional" : "O total de cada estado vem da fonte estadual"}, em que quem atua em mais de{" "}
      {(unidade.genero === "f" ? "uma " : "um ") + unidade.singular} conta uma vez: não é a soma {unidade.genero === "f" ? "das " : "dos "}{unidade.plural},
      que continuam com os próprios valores.{estados.length > 1 && !p.compacto
        ? " Quem atua em mais de um estado conta em cada um, e os totais dos estados não são somados." : ""}</p>
    {p.parciais.length > 0 && <p data-testid="analise-abrangencia-parciais" className="analise-abrangencia-nota">
      Sem total individualizado, porque não {p.parciais.length === 1 ? "está inteiro" : "estão inteiros"}:{" "}
      {p.parciais.slice(0, 4).map(item => item.nome + " (" + item.marcadas.toLocaleString("pt-BR") + " de " + item.total.toLocaleString("pt-BR") + ")").join(", ")}
      {p.parciais.length > 4 ? " e mais " + (p.parciais.length - 4) : ""}; cada {unidade.singular} mostra o próprio quantitativo.</p>}
  </section>;
}
