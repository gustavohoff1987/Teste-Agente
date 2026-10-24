import { useRef } from "react";
import { FileSpreadsheet, Upload } from "lucide-react";
import WorkspaceDialog from "./WorkspaceDialog";

// Janela "Enviar meus dados" (24/10/2026): a mesma para a abertura, a conversa, o "Trocar" da fonte e o atalho da rotatividade,
// para que enviar dados seja um fluxo só. Nela ficam a escolha do arquivo, o que acontece depois do envio e o modelo de planilha
// (XLSX), para consultar as colunas ou baixar. Nada é lido aqui: o arquivo escolhido vai para a preparação de sempre (as
// validações de formato e de tamanho, a leitura, a escolha da aba e o painel Colunas, em App.tsx).

type Props = { apiBase: string; onArquivo: (arquivo: File | undefined) => void; onFechar: () => void };

export default function JanelaDeEnvio({ apiBase, onArquivo, onFechar }: Props) {
  const inputRef = useRef<HTMLInputElement>(null);
  return <WorkspaceDialog id="envio-de-dados" title="Enviar meus dados" onClose={onFechar}>
    <p className="mt-4 text-sm leading-6">Envie uma planilha em CSV ou Excel (XLS ou XLSX), de até 30 MB, com uma linha por território,
      categoria profissional e período. Depois do envio, você confere as colunas antes de começar a análise.</p>
    <input ref={inputRef} type="file" accept=".csv,.xls,.xlsx" className="sr-only" tabIndex={-1} data-testid="fonte-arquivo-input"
      aria-label="Arquivo CSV ou Excel" onChange={event => { const arquivo = event.target.files?.[0]; event.target.value = ""; onArquivo(arquivo); }}/>
    <button type="button" data-testid="envio-escolher-arquivo" className="envio-escolher" onClick={() => inputRef.current?.click()}>
      <Upload size={18} aria-hidden="true"/>Escolher o arquivo</button>
    <section data-testid="envio-modelo" className="envio-modelo" aria-labelledby="envio-modelo-titulo">
      <h3 id="envio-modelo-titulo" className="flex items-center gap-2 text-sm font-semibold text-ink">
        <FileSpreadsheet size={16} aria-hidden="true"/>Modelo de planilha</h3>
      <p className="mt-1 text-xs leading-5">O modelo mostra como organizar os seus dados, com uma legenda ao lado da tabela: o território,
        o território que o contém (por exemplo, o estado), o código, a latitude e a longitude (para o mapa e as distâncias), a categoria
        profissional, o ano, o mês, a quantidade e a população.</p>
      <a href={apiBase + "/api/modelo/estrutura-recomendada"} download="modelo_territorial_recomendado.xlsx" data-testid="envio-modelo-baixar"
        className="envio-modelo-baixar">Baixar o modelo de planilha (XLSX)</a>
    </section>
    <div className="dialog-actions">
      <button type="button" data-testid="envio-cancelar" onClick={onFechar}>Cancelar</button>
    </div>
  </WorkspaceDialog>;
}
