import { useEffect } from 'react';
import Link from 'next/link';
import { trackLifecycleEvent } from '../lib/lifecycleAnalytics';

const supportCategories = [
  {
    name: 'Account access',
    description: 'Account creation, sign-in, email changes, or password resets.',
    subject: 'Run My Pool account support',
    selfService: { label: 'Reset your password', href: '/forgot-password' },
  },
  {
    name: 'Pool & picks',
    description: 'Joining a pool, entries, weekly picks, locks, autopicks, or results.',
    subject: 'Run My Pool pool and picks support',
    selfService: { label: 'Browse pools', href: '/leagues' },
  },
  {
    name: 'Billing',
    description: 'Plans, checkout, upgrades, payment confirmation, or receipts.',
    subject: 'Run My Pool billing support',
    selfService: { label: 'Review plans', href: '/pricing' },
  },
  {
    name: 'Technical issue',
    description: 'Errors, display problems, browser compatibility, or unexpected behavior.',
    subject: 'Run My Pool technical support',
    selfService: { label: 'Install or refresh the app', href: '/install' },
  },
];

function supportHref(subject) {
  const body = 'Please describe what happened, what you expected, and the pool name if applicable. Do not include passwords or payment card information.';
  return `mailto:support@runmypool.net?subject=${encodeURIComponent(subject)}&body=${encodeURIComponent(body)}`;
}

export default function SupportPage() {
  useEffect(() => {
    trackLifecycleEvent('support_hub_view', { page: 'support' });
  }, []);

  const contactSupport = () => {
    trackLifecycleEvent('support_contact_clicked', { page: 'support' });
  };

  return (
    <main className="support-page">
      <header className="support-hero">
        <div>
          <span>Run My Pool support</span>
          <h1>HOW CAN WE HELP?</h1>
          <p>Start with the fastest self-service option, or email the platform owner directly. You do not need to be signed in to get help.</p>
        </div>
        <div className="support-hero__contact">
          <span>Direct support</span>
          <a href={supportHref('Run My Pool support request')} onClick={contactSupport}>support@runmypool.net</a>
          <small>Please never send a password or payment-card number.</small>
        </div>
      </header>

      <section className="support-categories" aria-labelledby="support-categories-title">
        <div className="support-section-heading">
          <span>Choose a topic</span>
          <h2 id="support-categories-title">Get to the right answer faster</h2>
        </div>
        <div className="support-category-grid">
          {supportCategories.map((category, index) => (
            <article key={category.name}>
              <span>0{index + 1}</span>
              <h3>{category.name}</h3>
              <p>{category.description}</p>
              <div>
                <Link href={category.selfService.href}>{category.selfService.label}</Link>
                <a href={supportHref(category.subject)} onClick={contactSupport}>Email support</a>
              </div>
            </article>
          ))}
        </div>
      </section>

      <section className="support-details" aria-labelledby="support-details-title">
        <div>
          <span>What to include</span>
          <h2 id="support-details-title">Help us troubleshoot quickly</h2>
        </div>
        <ul>
          <li>Your account email address</li>
          <li>The pool name and entry name, when relevant</li>
          <li>What you were trying to do and the exact error shown</li>
          <li>Your device and browser, such as iPhone Safari or Chrome</li>
        </ul>
      </section>

      <section className="support-faq" aria-labelledby="support-faq-title">
        <div className="support-section-heading"><span>Quick answers</span><h2 id="support-faq-title">Before you email</h2></div>
        <details><summary>I cannot sign in. What should I do?</summary><p>Use <Link href="/forgot-password">Forgot Password</Link> first. If no email arrives, check spam and then contact support with your account email.</p></details>
        <details><summary>I cannot join a private pool.</summary><p>Private pools require the exact join password supplied by the pool commissioner. Pool passwords are ordinary text and are case-sensitive.</p></details>
        <details><summary>My weekly pick looks missing.</summary><p>Open the pool’s My Entries page and check the current week. Include the pool and entry names if you contact support.</p></details>
        <details><summary>My payment is still confirming.</summary><p>Stripe confirmation can take a short time. Review Profile & Billing, then email billing support if the plan is not active.</p></details>
      </section>
    </main>
  );
}
