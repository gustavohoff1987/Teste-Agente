// Banner de apresentação da página inicial (de volta em 23/10/2026, pedido do responsável pelo produto): a composição e o texto
// do banner das telas anteriores à página única (WelcomeHero, no histórico até ef58a33), com as cores pelas variáveis --hero-* de
// styles.css (claro e escuro). Só apresentação: não muda a análise nem a navegação.
export default function WelcomeHero() {
  return <section className="workspace-hero no-print" data-testid="pagina-banner" aria-labelledby="welcome-title">
    <div className="hero-copy">
      <p className="hero-eyebrow"><span aria-hidden="true"/> FORÇA DE TRABALHO NA SAÚDE</p>
      <h1 id="welcome-title">Transforme dados em <span>diagnósticos territoriais.</span></h1>
      <p className="hero-description">Um novo olhar sobre seus dados. Explore territórios, conecte informações e compreenda cenários.</p>
    </div>
  </section>;
}
