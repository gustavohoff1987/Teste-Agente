import { ArrowRight, MessageCircle, UploadCloud } from "lucide-react";
import territorialDashboard from "./assets/territorial-dashboard.png";

type Props = { onChat: () => void; onImport: () => void };
export default function WelcomeHero({ onChat, onImport }: Props) {
  return <section className="workspace-hero" aria-labelledby="welcome-title">
    <div className="hero-copy">
      <p className="hero-eyebrow"><span/> FORÇA DE TRABALHO NA SAÚDE</p>
      <h1 id="welcome-title">Transforme dados em <span>diagnósticos territoriais.</span></h1>
      <p className="hero-description">Um novo olhar sobre seus dados. Explore territórios, conecte informações e compreenda cenários.</p>
      <div className="hero-actions no-print">
        <button type="button" onClick={onChat}><MessageCircle size={16}/> Começar pelo chat <ArrowRight size={16}/></button>
        <button type="button" onClick={onImport}><UploadCloud size={16}/> Importar uma base</button>
      </div>
    </div>
    <div className="hero-art" style={{ flexBasis: 300 }} aria-hidden="true">
      <img src={territorialDashboard} alt="" width={1536} height={1024} decoding="async" draggable={false}
        className="absolute inset-0 h-full w-full object-contain opacity-90"/>
    </div>
  </section>;
}
