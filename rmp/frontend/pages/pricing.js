import { useCallback, useEffect, useRef, useState } from 'react';
import Link from 'next/link';
import { useRouter } from 'next/router';
import { useAuth } from '../context/AuthContext';
import Seo from '../components/Seo';
import { trackLifecycleEvent } from '../lib/lifecycleAnalytics';
import BrandLogo from '../components/BrandLogo';

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
    name: 'Commish',
    slug: 'commissioner',
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
    features: ['Up to 5 active pools', '500 total entries included', '$25 per additional 100 entries', 'Everything in Pro', 'Full historical access', 'Custom league branding'],
    cta: 'Choose Club',
  },
  {
    name: 'Club Unlimited',
    slug: 'club-unlimited',
    price: '$249',
    cadence: 'per season',
    description: 'The best value for large organizations that want one predictable price and room to grow.',
    features: ['Unlimited entries', 'Unlimited active pools', 'No usage charges', 'Everything in Club', 'Historical access for every season', 'VIP weekend support'],
    cta: 'Go Unlimited',
    featured: true,
    badge: 'Best for large pools',
  },
];

export default function PricingPage() {
  const auth = useAuth();
  const router = useRouter();
  const [checkoutPlan, setCheckoutPlan] = useState('');
  const [checkoutError, setCheckoutError] = useState('');
  const continuedCheckout = useRef(false);
  const freeStartHref = auth?.user ? '/create-pool?source=splash' : '/create-account?plan=free';

  useEffect(() => {
    trackLifecycleEvent('pricing_view', { page: 'pricing', source: 'homepage' });
  }, []);

  const beginCheckout = useCallback(async (planSlug) => {
    const token = auth?.token || (typeof window !== 'undefined' ? localStorage.getItem('access_token') : null);
    if (!token) return false;
    setCheckoutPlan(planSlug);
    setCheckoutError('');
    try {
      const season = Number(process.env.NEXT_PUBLIC_NFL_SEASON) || new Date().getFullYear();
      const response = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/billing/checkout-session`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${token}` },
        credentials: 'include',
        body: JSON.stringify({ plan: planSlug, season }),
      });
      const body = await response.json().catch(() => ({}));
      if (!response.ok) throw new Error(body.detail || 'Unable to start secure checkout.');
      trackLifecycleEvent('checkout_started', { page: 'pricing', plan: planSlug, source: 'pricing' });
      window.location.assign(body.checkout_url);
      return true;
    } catch (error) {
      setCheckoutError(error.message || 'Unable to start secure checkout.');
      setCheckoutPlan('');
      return false;
    }
  }, [auth?.token]);

  useEffect(() => {
    const plan = typeof router.query.checkout === 'string' ? router.query.checkout : '';
    if (!router.isReady || !auth?.token || continuedCheckout.current || !plans.some((item) => (item.slug || item.name.toLowerCase()) === plan)) return;
    continuedCheckout.current = true;
    beginCheckout(plan);
  }, [auth?.token, beginCheckout, router.isReady, router.query.checkout]);

  return (
    <div className="rmp-landing pricing-page">
      <Seo
        title="Football Pool Pricing"
        path="/pricing"
        description="Simple season pricing for NFL Survivor and Pick 'Em pool commissioners. Start free, grow by the hundred, or run unlimited entries for one predictable price."
        structuredData={{
          '@context': 'https://schema.org',
          '@type': 'Product',
          name: 'Run My Pool',
          description: "NFL Survivor and Pick 'Em pool management software for commissioners.",
          brand: { '@type': 'Brand', name: 'Run My Pool' },
          offers: plans.map((plan) => ({
            '@type': 'Offer',
            name: plan.name,
            price: plan.price.replace('$', ''),
            priceCurrency: 'USD',
            url: `https://runmypool.net/create-account?plan=${plan.slug || plan.name.toLowerCase()}`,
            availability: 'https://schema.org/InStock',
          })),
        }}
      />

      <header className="rmp-header">
        <nav className="rmp-shell" aria-label="Pricing navigation">
          <Link href="/" className="rmp-brand" aria-label="Run My Pool home">
            <BrandLogo className="rmp-brand__logo" priority />
          </Link>
          <div className="rmp-nav-links pricing-nav-links">
            <Link href="/#how">How it works</Link>
            <Link href="/#features">Features</Link>
            <Link href="/pricing" aria-current="page">Pricing</Link>
          </div>
          <div className="rmp-nav-actions">
            <Link href="/login" className="rmp-login">Login</Link>
            <Link href={freeStartHref} className="rmp-nav-cta">Start free <span>↗</span></Link>
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
          {router.query.checkout === 'cancelled' && <div className="pricing-checkout-notice">{typeof router.query.plan === 'string' ? `${plans.find((item) => (item.slug || item.name.toLowerCase()) === router.query.plan)?.name || 'Plan'} checkout was canceled.` : 'Checkout was canceled.'} No payment was taken.</div>}
          {checkoutError && <div className="pricing-checkout-notice pricing-checkout-notice--error">{checkoutError}</div>}
          {plans.map((plan, index) => (
            <article className={`pricing-card${plan.featured ? ' pricing-card--featured' : ''}`} key={plan.name}>
              <div className="pricing-card__head">
                <span>0{index + 1}</span>
                {plan.featured && <b>{plan.badge || 'Most popular'}</b>}
              </div>
              <h2>{plan.name}</h2>
              <div className="pricing-card__price"><strong>{plan.price}</strong><small>{plan.cadence}</small></div>
              <p>{plan.description}</p>
              <ul>
                {plan.features.map((feature) => <li key={feature}><span>✓</span>{feature}</li>)}
              </ul>
              <Link
                href={plan.name === 'Free' && auth?.user ? '/create-pool?source=splash' : `/create-account?plan=${plan.slug || plan.name.toLowerCase()}`}
                className={`pricing-card__cta${checkoutPlan === (plan.slug || plan.name.toLowerCase()) ? ' is-loading' : ''}`}
                aria-disabled={Boolean(checkoutPlan)}
                onClick={(event) => {
                  trackLifecycleEvent('plan_selected', {
                    page: 'pricing',
                    plan: plan.slug || plan.name.toLowerCase(),
                    source: 'pricing',
                  });
                  if (plan.name === 'Free' || !auth?.token) return;
                  event.preventDefault();
                  if (!checkoutPlan) beginCheckout(plan.slug || plan.name.toLowerCase());
                }}
              >{checkoutPlan === (plan.slug || plan.name.toLowerCase()) ? 'Opening secure checkout…' : plan.cta}<span>→</span></Link>
            </article>
          ))}
        </section>

        <section className="pricing-promise rmp-shell">
          <div><span>NO RAKE</span><strong>Run My Pool never takes a percentage of your pool.</strong></div>
          <div><span>PLAYERS FREE</span><strong>Only the commissioner purchases the hosting plan.</strong></div>
          <div><span>UNLIMITED VALUE</span><strong>Large pools can lock in unlimited entries for $249.</strong></div>
        </section>

        <section className="pricing-faq rmp-shell">
          <div className="rmp-section-kicker"><span>04</span><b>THE FINE PRINT</b></div>
          <div className="pricing-faq__heading"><h2>STRAIGHT ANSWERS.<br /><em>NO SURPRISES.</em></h2><p>Start with a real pool before paying. Upgrade only when your entry count or commissioner needs grow.</p></div>
          <div className="pricing-faq__grid">
            <article><h3>Do players pay?</h3><p>No. Participants join, make picks, and follow standings at no software charge.</p></article>
            <article><h3>Do you hold prize money?</h3><p>No. Run My Pool provides management software and does not collect stakes or distribute winnings.</p></article>
            <article><h3>Can I upgrade later?</h3><p>Yes. Upgrade through Free, Commish, Pro, and Club without rebuilding your pool. Club Unlimited is a separate seasonal choice and is not available as an upgrade from Club.</p></article>
            <article><h3>What counts as an entry?</h3><p>Each Survivor or Pick &apos;Em entry counts toward the plan limit. One person may own multiple entries if the commissioner allows it.</p></article>
            <article><h3>What happens after 500 Club entries?</h3><p>Club expands in 100-entry blocks for $25 each with no maximum. Purchasing Club does not provide a later path to Club Unlimited.</p></article>
            <article><h3>When should I choose Unlimited?</h3><p>Choose Club Unlimited at the start of the season when you need unlimited entries or pools. It is a separate plan, not an upgrade from Club.</p></article>
          </div>
        </section>

        <section className="pricing-final">
          <div className="rmp-shell"><p className="rmp-eyebrow"><span /> READY FOR KICKOFF</p><h2>YOUR LEAGUE.<br /><em>YOUR RULES.</em></h2><Link href={freeStartHref} className="rmp-button rmp-primary">Start your pool free <span>→</span></Link></div>
        </section>
      </main>

      <footer className="rmp-footer"><div className="rmp-shell"><Link href="/" className="rmp-brand"><BrandLogo className="rmp-brand__logo" alt="Run My Pool" /></Link><p>Simple software pricing. No percentage of prizes. <Link href="/support">Billing and account support</Link></p><span>© 2026 Run My Pool</span></div></footer>
    </div>
  );
}
