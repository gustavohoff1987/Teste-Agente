type Props = { onChat?: () => void; onImport?: () => void };

export default function WelcomeHero(_props: Props) {
  return <section className="workspace-hero" aria-labelledby="welcome-title">
    <div className="hero-copy">
      <p className="hero-eyebrow"><span/> FORÇA DE TRABALHO NA SAÚDE</p>
      <h1 id="welcome-title">Transforme dados em <span>diagnósticos territoriais.</span></h1>
      <p className="hero-description">Um novo olhar sobre seus dados. Explore territórios, conecte informações e compreenda cenários.</p>
    </div>
  </section>;
}
