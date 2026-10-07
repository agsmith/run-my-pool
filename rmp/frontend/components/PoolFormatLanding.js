import Link from 'next/link';
import { useEffect } from 'react';
import BrandLogo from './BrandLogo';
import Seo from './Seo';
import { trackLifecycleEvent } from '../lib/lifecycleAnalytics';

export default function PoolFormatLanding({ format }) {
  const {
    eyebrow,
    title,
    accent,
    description,
    path,
    intro,
    steps,
    features,
    faqs,
  } = format;

  useEffect(() => {
    trackLifecycleEvent('landing_view', { page: format.analyticsPage, source: 'direct' });
  }, [format.analyticsPage]);

  const structuredData = {
    '@context': 'https://schema.org',
    '@graph': [
      {
        '@type': 'SoftwareApplication',
        name: title,
        applicationCategory: 'SportsApplication',
        operatingSystem: 'Web, iOS',
        url: `https://runmypool.net${path}`,
        description,
        offers: { '@type': 'Offer', price: '0', priceCurrency: 'USD' },
      },
      {
        '@type': 'FAQPage',
        mainEntity: faqs.map(({ question, answer }) => ({
          '@type': 'Question',
          name: question,
          acceptedAnswer: { '@type': 'Answer', text: answer },
        })),
      },
    ],
  };

  return (
    <div className="rmp-landing format-landing">
      <Seo title={title} description={description} path={path} structuredData={structuredData} />
      <header className="rmp-header">
        <nav className="rmp-shell" aria-label={`${accent} pool navigation`}>
          <Link href="/" className="rmp-brand" aria-label="Run My Pool home">
            <BrandLogo className="rmp-brand__logo" priority />
          </Link>
          <div className="rmp-nav-links">
            <Link href="/nfl-survivor-pool">Survivor</Link>
            <Link href="/nfl-pick-em-pool">Pick &apos;Em</Link>
            <Link href="/football-squares-pool">Squares</Link>
            <Link href="/pricing">Pricing</Link>
          </div>
          <div className="rmp-nav-actions">
            <Link href="/login" className="rmp-login">Login</Link>
            <Link href="/pricing" className="rmp-nav-cta">Start a pool <span>↗</span></Link>
          </div>
        </nav>
      </header>

      <main>
        <section className="format-hero">
          <div className="rmp-shell format-hero__grid">
            <div>
              <p className="rmp-eyebrow"><span /> {eyebrow}</p>
              <h1>{title.toUpperCase()}<br /><em>{accent.toUpperCase()}.</em></h1>
              <p className="format-hero__intro">{intro}</p>
              <div className="rmp-hero-actions">
                <Link href="/pricing" className="rmp-button rmp-primary">Start free <span>→</span></Link>
                <a href="#how-it-works" className="rmp-button rmp-secondary">How it works</a>
              </div>
            </div>
            <aside className="format-scorecard" aria-label={`${accent} pool features`}>
              <span>RUN MY POOL</span>
              <strong>{accent}</strong>
              <p>{description}</p>
              <ul>{features.slice(0, 4).map((feature) => <li key={feature}>✓ {feature}</li>)}</ul>
            </aside>
          </div>
        </section>

        <section className="format-section" id="how-it-works">
          <div className="rmp-shell">
            <div className="rmp-section-kicker"><span>01</span><b>HOW IT WORKS</b></div>
            <h2>FROM INVITE<br />TO <em>FINAL WHISTLE.</em></h2>
            <div className="format-steps">
              {steps.map((step, index) => (
                <article key={step.title}>
                  <span>0{index + 1}</span>
                  <h3>{step.title}</h3>
                  <p>{step.copy}</p>
                </article>
              ))}
            </div>
          </div>
        </section>

        <section className="format-section format-section--dark">
          <div className="rmp-shell">
            <div className="rmp-section-kicker rmp-light"><span>02</span><b>BUILT FOR COMMISSIONERS</b></div>
            <h2>LESS CHASING.<br /><em>MORE FOOTBALL.</em></h2>
            <div className="format-feature-grid">
              {features.map((feature) => <article key={feature}><span>✓</span><p>{feature}</p></article>)}
            </div>
          </div>
        </section>

        <section className="format-section format-faq">
          <div className="rmp-shell">
            <div className="rmp-section-kicker"><span>03</span><b>COMMON QUESTIONS</b></div>
            <h2>{accent.toUpperCase()} POOL<br /><em>FAQ.</em></h2>
            <div className="rmp-home-faq__grid">
              {faqs.map(({ question, answer }) => (
                <details key={question}>
                  <summary>{question}<span aria-hidden="true">+</span></summary>
                  <p>{answer}</p>
                </details>
              ))}
            </div>
          </div>
        </section>

        <section className="format-final">
          <div className="rmp-shell">
            <p className="rmp-eyebrow"><span /> READY FOR KICKOFF</p>
            <h2>RUN YOUR {accent.toUpperCase()} POOL<br /><em>WITHOUT THE SPREADSHEET.</em></h2>
            <Link href="/pricing" className="rmp-button rmp-primary">See plans and start free <span>→</span></Link>
          </div>
        </section>
      </main>

      <footer className="rmp-footer">
        <div className="rmp-shell">
          <Link href="/" className="rmp-brand"><BrandLogo className="rmp-brand__logo" alt="Run My Pool" /></Link>
          <p><Link href="/nfl-survivor-pool">NFL Survivor</Link> · <Link href="/nfl-pick-em-pool">NFL Pick &apos;Em</Link> · <Link href="/football-squares-pool">Football Squares</Link> · <Link href="/pricing">Pricing</Link></p>
          <span>© 2026 Run My Pool</span>
        </div>
      </footer>
    </div>
  );
}
