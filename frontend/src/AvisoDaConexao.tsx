import { useLayoutEffect, useRef, useState } from "react";
import { LoaderCircle, RefreshCw } from "lucide-react";
import { criarMonitor, observarRespostas, TEXTO_INDISPONIVEL, TEXTO_INICIANDO, TEXTO_RESTABELECIDA, TITULO_INDISPONIVEL,
  type EstadoDaConexao, type Monitor } from "./conexao";

// Aviso dos estados da conexão (01/11/2026; conexao.ts). Sem códigos HTTP, mensagens do provedor, valores ou detalhes da
// infraestrutura. Enquanto o serviço responde, nada aparece.

const INICIAL: EstadoDaConexao = { fase: "verificando", tentativas: 0, esgotadas: false, pausada: false, textoOcupado: "",
  restabelecida: false };

/** O monitor da conexão da página: verifica o serviço na abertura e observa as respostas de todos os pedidos da tela. Criado
 * num efeito de layout, antes dos efeitos dos componentes filhos (que fazem os primeiros pedidos). */
export function useConexao(api: string) {
  const [estado, setEstado] = useState<EstadoDaConexao>(INICIAL);
  const monitor = useRef<Monitor | null>(null);
  useLayoutEffect(() => {
    const buscar = window.fetch.bind(window);  // a verificação não passa pela observação
    const atual = criarMonitor({
      verificar: async sinal => {
        const resposta = await buscar(api + "/api/health", { signal: sinal, cache: "no-store" });
        if (!resposta.ok) return false;
        const corpo = await resposta.json().catch(() => null) as { status?: unknown } | null;
        return corpo?.status === "ok";
      },
      aoMudar: setEstado,
      visivel: () => document.visibilityState !== "hidden",
    });
    monitor.current = atual;
    const desfazer = observarRespostas(atual, api, window);
    const aoMudarVisibilidade = () => atual.visibilidade(document.visibilityState !== "hidden");
    document.addEventListener("visibilitychange", aoMudarVisibilidade);
    atual.iniciar();
    return () => {
      document.removeEventListener("visibilitychange", aoMudarVisibilidade);
      desfazer();
      atual.encerrar();
      if (monitor.current === atual) monitor.current = null;
    };
  }, [api]);
  return { estado, tentar: () => monitor.current?.tentarAgora() };
}

export default function AvisoDaConexao({ estado, onTentar }: { estado: EstadoDaConexao; onTentar: () => void }) {
  if (estado.fase === "indisponivel")
    return <section role="alert" aria-labelledby="conexao-titulo" data-testid="conexao-indisponivel"
      className="conexao conexao-indisponivel no-print">
      <h2 id="conexao-titulo">{TITULO_INDISPONIVEL}</h2>
      <p data-testid="conexao-texto">{TEXTO_INDISPONIVEL}</p>
      <p className="conexao-nota" data-testid="conexao-nota">{estado.esgotadas
        ? "As novas tentativas automáticas terminaram. Use o botão para tentar de novo."
        : estado.pausada ? "As novas tentativas automáticas continuam quando esta aba voltar a ficar à vista."
          : "Uma nova tentativa automática será feita em instantes."}</p>
      <button type="button" data-testid="conexao-tentar" onClick={onTentar}>
        <RefreshCw size={15} aria-hidden="true"/>Tentar novamente</button>
    </section>;
  if (estado.fase === "iniciando")
    return <p role="status" data-testid="conexao-iniciando" className="conexao conexao-iniciando no-print">
      <LoaderCircle size={16} className="animate-spin" aria-hidden="true"/>{TEXTO_INICIANDO}</p>;
  if (estado.fase === "ocupado")
    return <p role="status" data-testid="conexao-ocupado" className="conexao conexao-ocupado no-print">{estado.textoOcupado}</p>;
  if (estado.restabelecida)
    return <p role="status" data-testid="conexao-restabelecida" className="conexao conexao-restabelecida no-print">
      {TEXTO_RESTABELECIDA}</p>;
  return null;
}
