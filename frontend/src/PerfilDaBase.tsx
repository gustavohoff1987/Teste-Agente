import { useEffect, useState } from "react";
import { ChevronDown, ChevronRight, LoaderCircle } from "lucide-react";
import { ErroDoMotor, pedirAoMotor, type FonteDoMotor } from "./painelApi";
import { competenciaCurta, formatarInteiro, normalizarPerfil, type OpcoesDaBase, type PerfilDaBase as Perfil } from "./detectorModel";

// Perfil da base (comando V23, seção 2; Proposta V3, seção A.3): antes das ferramentas, o Agente diz o que leu da base — as datas
// e os intervalos, a série anual, os portes, o grupo de cima, a população, as coordenadas, o que a contagem conta e os nomes — e o
// resumo "com esta base, dá para… / não dá para… (motivo)". Vale para a base do Brasil e para uma planilha enviada. Tudo vem do
// motor (POST /api/detector com `{"perfil": true}`), que lê a base sem o provedor de IA; a tela só mostra.
// Numa base nova (a planilha enviada), o perfil abre sozinho; na base do Brasil, fica fechado até a pessoa pedir, e só então é lido.

type Props = {
  fonte: FonteDoMotor;
  /** Numa planilha enviada, o que o pedido diz dela (os nomes, as premissas e a categoria), como no pedido das ferramentas. */
  daBase?: OpcoesDaBase;
  /** Aberto ao aparecer: uma base nova (a planilha enviada). */
  abertoDeInicio: boolean;
};

/** Os perfis já lidos nesta página, por base: fechar e abrir de novo, ou trocar de ferramenta, não pede outra vez. */
const lidos = new Map<string, Perfil>();
const chaveDe = (fonte: FonteDoMotor, daBase?: OpcoesDaBase) => JSON.stringify([fonte.tipo, fonte.datasetVersion, fonte.sheet, fonte.mapping,
  fonte.arquivo ? [fonte.arquivo.name, fonte.arquivo.size, fonte.arquivo.lastModified] : null, daBase ?? null]);

export default function PerfilDaBase({ fonte, daBase, abertoDeInicio }: Props) {
  const chave = chaveDe(fonte, daBase);
  const [aberto, setAberto] = useState(abertoDeInicio);
  const [perfil, setPerfil] = useState<Perfil | null>(() => lidos.get(chave) ?? null);
  const [erro, setErro] = useState<string | null>(null);
  const [tentativa, setTentativa] = useState(0);

  useEffect(() => {
    const guardado = lidos.get(chave) ?? null;
    setPerfil(guardado); setErro(null);
    if (!aberto || guardado) return;
    const controle = new AbortController();
    pedirAoMotor(fonte, "/api/detector", { ...(daBase ?? {}), perfil: true }, controle.signal)
      .then(bruto => {
        if (controle.signal.aborted) return;
        const lido = normalizarPerfil(bruto);
        if (!lido) { setErro("O perfil da base não veio na resposta."); return; }
        lidos.set(chave, lido);
        while (lidos.size > 6) lidos.delete(lidos.keys().next().value as string);
        setPerfil(lido);
      })
      .catch((exc: unknown) => {
        if (!controle.signal.aborted) setErro(exc instanceof ErroDoMotor || exc instanceof Error ? exc.message : "Não foi possível ler o perfil da base.");
      });
    return () => controle.abort();
  }, [chave, aberto, tentativa]);

  return <section data-testid="perfil-da-base" data-estado={!aberto ? "fechado" : erro ? "erro" : perfil ? "pronto" : "carregando"}
    data-origem={perfil?.origem ?? ""} aria-label="Perfil da base" className="ferramenta-perfil analise-nao-imprimir">
    <button type="button" data-testid="perfil-da-base-botao" className="ferramenta-perfil-botao" aria-expanded={aberto}
      onClick={() => setAberto(valor => !valor)}>
      {aberto ? <ChevronDown size={15} aria-hidden="true"/> : <ChevronRight size={15} aria-hidden="true"/>}
      <span className="ferramenta-perfil-nome">Perfil da base</span>
      <span className="ferramenta-apoio">o que o Agente leu dela e o que dá para fazer com ela</span>
    </button>
    {aberto && erro && <p data-testid="perfil-da-base-erro" role="alert" className="analise-motivo">{erro}{" "}
      <button type="button" className="analise-link" onClick={() => setTentativa(valor => valor + 1)}>Tentar de novo</button></p>}
    {aberto && !erro && !perfil && <p role="status" className="ferramenta-apoio"><LoaderCircle size={14} className="animate-spin inline" aria-hidden="true"/> Lendo a base…</p>}
    {aberto && !erro && perfil && <div data-testid="perfil-da-base-corpo" className="ferramenta-perfil-corpo">
      <p data-testid="perfil-da-base-resumo" className="ferramenta-apoio">{formatarInteiro(perfil.territorios)} {perfil.territorios === 1 ? "território" : "territórios"} ·{" "}
        {formatarInteiro(perfil.registros)} registros, de {competenciaCurta(perfil.primeira)} a {competenciaCurta(perfil.ultima)}.</p>
      <div className="ferramenta-perfil-colunas">
        <div data-testid="perfil-da-para" data-itens={perfil.daPara.length} className="ferramenta-perfil-lista">
          <p className="ferramenta-perfil-titulo">Com esta base, dá para</p>
          {perfil.daPara.length ? <ul>{perfil.daPara.map(frase => <li key={frase}>{frase}</li>)}</ul>
            : <p className="ferramenta-apoio">A base ainda não sustenta nenhum nível de alerta comparado com ela mesma.</p>}
        </div>
        <div data-testid="perfil-nao-da-para" data-itens={perfil.naoDaPara.length} className="ferramenta-perfil-lista">
          <p className="ferramenta-perfil-titulo">Não dá para</p>
          {perfil.naoDaPara.length ? <ul>{perfil.naoDaPara.map(item => <li key={item.oQue}><strong>{item.oQue}:</strong> {item.motivo}</li>)}</ul>
            : <p className="ferramenta-apoio">Nada ficou de fora: a base sustenta todos os sinais e os três níveis.</p>}
        </div>
      </div>
      <div className="ferramenta-rolagem"><table data-testid="perfil-da-base-itens" className="analise-tabela ferramenta-tabela">
        <caption className="ferramenta-apoio">O que o Agente leu da base, antes de abrir as ferramentas.</caption>
        <thead><tr><th scope="col">O quê</th><th scope="col">Como o Agente leu</th><th scope="col">Se faltar</th></tr></thead>
        <tbody>{perfil.itens.map(item => <tr key={item.chave} data-chave={item.chave} data-falta={item.falta ? "true" : "false"}>
          <th scope="row">{item.titulo}</th><td>{item.lido}</td><td>{item.falta ?? "—"}</td></tr>)}</tbody>
      </table></div>
      {perfil.avisos.map(aviso => <p key={aviso} data-testid="perfil-da-base-aviso" role="note" className="ferramenta-aviso">{aviso}</p>)}
    </div>}
  </section>;
}
