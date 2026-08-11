import Link from 'next/link';
import Seo from '../components/Seo';

const plans = [
  {
    name: 'Free',
    price: '$0',
    cadence: 'forever',
    description: 'Run a small pool and experience the full weekly rhythm.',
    features: ['1 active pool', 'Up to 10 entries', 'Weekly picks and standings', 'Private or public access', 'Message board'],
    cta: 'Start free',
  },
  {
    name: 'Commissioner',
    price: '$39',
    cadence: 'per pool / season',
    description: 'The complete toolkit for a serious friends, family, or office pool.',
    features: ['Up to 50 entries', 'Everything in Free', 'Automated default picks', 'Audit log and CSV exports', 'Entry transfers and corrections', 'Priority commissioner support'],
    cta: 'Choose Commissioner',
    featured: true,
  },
  {
    name: 'Pro',
    price: '$79',
    cadence: 'per pool / season',
    description: 'More capacity and control for large groups and recurring organizers.',
    features: ['Up to 150 entries', 'Everything in Commissioner', 'Multiple commissioners', 'Advanced league controls', 'Reusable member history', 'Priority weekend support'],
    cta: 'Choose Pro',
  },
  {
    name: 'Club',
    price: '$129',
    cadence: 'per season',
    description: 'A season-long home for commissioners who run several pools year after year.',
    features: ['Up to 5 active pools', 'Up to 500 total entries', 'Everything in Pro', 'Full historical access', 'Reusable members and past seasons', 'Custom league branding'],
    cta: 'Choose Club',
  },
];

function FootballMark() {
  return <span className="rmp-mark" aria-hidden="true"><i /><i /><i /></span>;
}

export default function PricingPage() {
  return (
    <div className="rmp-landing pricing-page">
      <Seo
        title="Football Pool Pricing"
        path="/pricing"
        description="Simple season pricing for NFL survivor pool commissioners. Start free, scale to 500 entries, and never pay a percentage of prizes."
        structuredData={{
          '@context': 'https://schema.org',
          '@type': 'Product',
          name: 'Run My Pool',
          description: 'NFL survivor pool management software for commissioners.',
          brand: { '@type': 'Brand', name: 'Run My Pool' },
          offers: plans.map((plan) => ({
            '@type': 'Offer',
            name: plan.name,
            price: plan.price.replace('$', ''),
            priceCurrency: 'USD',
            url: `https://runmypool.net/create-account?plan=${plan.name.toLowerCase()}`,
            availability: 'https://schema.org/InStock',
          })),
        }}
      />

      <header className="rmp-header">
        <nav className="rmp-shell" aria-label="Pricing navigation">
          <Link href="/" className="rmp-brand" aria-label="Run My Pool home">
            <FootballMark /><span>RUN MY <b>POOL</b></span>
          </Link>
          <div className="rmp-nav-links pricing-nav-links">
            <Link href="/#how">How it works</Link>
            <Link href="/#features">Features</Link>
            <Link href="/pricing" aria-current="page">Pricing</Link>
          </div>
          <div className="rmp-nav-actions">
            <Link href="/login" className="rmp-login">Login</Link>
            <Link href="/create-account" className="rmp-nav-cta">Start free <span>↗</span></Link>
          </div>
        </nav>
      </header>

      <main className="pricing-main">
        <section className="pricing-hero rmp-shell">
          <p className="rmp-eyebrow"><span /> SIMPLE COMMISSIONER PRICING</p>
          <h1>RUN THE POOL.<br /><em>SKIP THE BUSYWORK.</em></h1>
          <p>Players always participate free. You pay only when your pool grows beyond ten entries—no percentage of prizes and no surprise fees.</p>
        </section>

        <section className="pricing-grid rmp-shell" aria-label="Pricing plans">
          {plans.map((plan, index) => (
            <article className={`pricing-card${plan.featured ? ' pricing-card--featured' : ''}`} key={plan.name}>
              <div className="pricing-card__head">
                <span>0{index + 1}</span>
                {plan.featured && <b>Most popular</b>}
              </div>
              <h2>{plan.name}</h2>
              <div className="pricing-card__price"><strong>{plan.price}</strong><small>{plan.cadence}</small></div>
              <p>{plan.description}</p>
              <ul>
                {plan.features.map((feature) => <li key={feature}><span>✓</span>{feature}</li>)}
              </ul>
              <Link href={`/create-account?plan=${plan.name.toLowerCase()}`} className="pricing-card__cta">{plan.cta}<span>→</span></Link>
            </article>
          ))}
        </section>

        <section className="pricing-promise rmp-shell">
          <div><span>NO RAKE</span><strong>Run My Pool never takes a percentage of your pool.</strong></div>
          <div><span>PLAYERS FREE</span><strong>Only the commissioner purchases the hosting plan.</strong></div>
          <div><span>ONE SEASON</span><strong>Paid plans cover the full football season.</strong></div>
        </section>

        <section className="pricing-faq rmp-shell">
          <div className="rmp-section-kicker"><span>04</span><b>THE FINE PRINT</b></div>
          <div className="pricing-faq__heading"><h2>STRAIGHT ANSWERS.<br /><em>NO SURPRISES.</em></h2><p>Start with a real pool before paying. Upgrade only when your entry count or commissioner needs grow.</p></div>
          <div className="pricing-faq__grid">
            <article><h3>Do players pay?</h3><p>No. Participants join, make picks, and follow standings at no software charge.</p></article>
            <article><h3>Do you hold prize money?</h3><p>No. Run My Pool provides management software and does not collect stakes or distribute winnings.</p></article>
            <article><h3>Can I upgrade later?</h3><p>Yes. Start free and upgrade without rebuilding your pool or inviting everyone again.</p></article>
            <article><h3>What counts as an entry?</h3><p>Each survivor entry counts toward the plan limit. One person may own multiple entries if the commissioner allows it.</p></article>
          </div>
        </section>

        <section className="pricing-final">
          <div className="rmp-shell"><p className="rmp-eyebrow"><span /> READY FOR KICKOFF</p><h2>YOUR LEAGUE.<br /><em>YOUR RULES.</em></h2><Link href="/create-account" className="rmp-button rmp-primary">Start your pool free <span>→</span></Link></div>
        </section>
      </main>

      <footer className="rmp-footer"><div className="rmp-shell"><Link href="/" className="rmp-brand"><FootballMark /><span>RUN MY <b>POOL</b></span></Link><p>Simple software pricing. No percentage of prizes.</p><span>© 2026 Run My Pool</span></div></footer>
    </div>
  );
}
