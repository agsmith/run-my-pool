import Link from 'next/link';
import { useEffect } from 'react';
import { useAuth } from '../context/AuthContext';
import Seo from '../components/Seo';
import { trackLifecycleEvent } from '../lib/lifecycleAnalytics';
import BrandLogo from '../components/BrandLogo';

const games = [
  { number: '01', time: 'SUN 1:00', away: 'BUF', awayName: 'Buffalo', home: 'NYJ', homeName: 'New York', className: 'blue' },
  { number: '02', time: 'SUN 4:25', away: 'GB', awayName: 'Green Bay', home: 'CHI', homeName: 'Chicago', className: 'green', selected: true },
  { number: '03', time: 'SNF 8:20', away: 'DAL', awayName: 'Dallas', home: 'PHI', homeName: 'Philadelphia', className: 'navy' },
];

const features = [
  { number: '01', icon: '≡', title: 'Configurable Pool Setup', copy: 'Start with the format and access model that fits your group.', details: ["Survivor, Pick 'Em, and Squares formats", 'Public or password-protected pools', 'Custom lock schedule, timezone, and entry rules'] },
  { number: '02', icon: '⚡', title: 'Weekly Automation', copy: 'Keep every NFL week moving without spreadsheets or reminder chains.', details: ['Scheduled weekly pick locks', 'Eligible Survivor autopicks', 'Automatic winners, eliminations, points, and standings'] },
  { number: '03', icon: '↗', title: 'Member Experience', copy: 'Give every player a clear, mobile-friendly place to manage the season.', details: ['Multiple named entries per account', 'Pick progress and entries remaining', 'Weekly matchups, standings, and forum access'] },
  { number: '04', icon: '⌁', title: 'Commissioner Controls', copy: 'Manage the pool without exposing platform-wide users or data.', details: ['Pool-scoped users, entries, picks, and roles', 'Lock management, pick corrections, and transfers', 'Autopick review and participation reporting'] },
  { number: '05', icon: '✓', title: 'Transparent Competition', copy: 'Make the rules and weekly activity understandable to the entire pool.', details: ['All surviving picks revealed at weekly lock', 'Clickable team totals with member and entry detail', 'Exportable audit history for administrative changes'] },
  { number: '06', icon: '+', title: 'Affordable Growth', copy: 'Begin free and add capacity only when the pool actually needs it.', details: ['Free entry-level package', 'Season plans for 50, 150, or 500 entries', 'Club expansion blocks and an unlimited option'] },
];

const howSteps = [
  {
    number: '01',
    eyebrow: 'COMMISSIONER SETUP',
    title: 'BUILD YOUR POOL',
    copy: "Choose Survivor, Pick 'Em, or single-game Squares, name the pool, and make it public or password-protected.",
    details: ['Set weekly lock day, time, and timezone', 'Choose entry limits, rules, and autopick behavior'],
  },
  {
    number: '02',
    eyebrow: 'INVITE & ENTER',
    title: 'BRING IN YOUR CREW',
    copy: 'Share the pool link. Members create a free account, join the correct pool, and add their entries.',
    details: ['Private pools require the join password', 'Each member can manage all of their own entries'],
  },
  {
    number: '03',
    eyebrow: 'EVERY WEEK',
    title: 'MAKE THE PICKS',
    copy: 'Members make or change selections until the commissioner-defined weekly deadline.',
    details: ['Missing Survivor picks can receive an eligible autopick', 'At lock, surviving-entry picks are revealed to the pool'],
  },
  {
    number: '04',
    eyebrow: 'KICKOFF TO FINAL',
    title: 'FOLLOW THE RESULTS',
    copy: 'Run My Pool records winners, updates entry status and standings, and keeps the conversation together.',
    details: ['Survivor winners advance; losing entries are eliminated', "Pick 'Em awards one point for each correct winner", 'Squares records quarter, halftime, and final winners'],
  },
];

const homepageFaqs = [
  {
    question: 'When do weekly picks lock?',
    answer: 'The commissioner sets the weekly lock time. Members can change picks until that deadline; after it passes, picks are locked and the week’s surviving-entry picks are revealed.',
  },
  {
    question: 'Can a pool be private?',
    answer: 'Yes. Private pools appear in the Pool Directory, but a member must enter the pool’s join password before joining.',
  },
  {
    question: 'What happens if someone forgets to pick?',
    answer: 'When autopicks are enabled, Run My Pool selects the best available eligible team at the weekly lock. Commissioners can review which entries received an autopick.',
  },
  {
    question: 'Do members have to pay?',
    answer: 'No. Members join pools, manage entries, make picks, and follow results for free. Only the commissioner purchases hosting when a pool exceeds the Free plan.',
  },
  {
    question: 'Does Run My Pool handle prize money?',
    answer: 'No. Run My Pool provides pool-management software and never collects entry stakes, holds prize funds, or distributes winnings.',
  },
  {
    question: 'How do I get help?',
    answer: 'Email support@runmypool.net for account, pool, billing, or technical assistance.',
  },
];

export default function Home() {
  const { user } = useAuth();
  const createPoolHref = user ? '/create-pool?source=splash' : '/pricing';

  useEffect(() => {
    trackLifecycleEvent('landing_view', { page: 'home', source: 'direct' });
  }, []);

  return (
    <div className="rmp-landing">
      <Seo
        title="Run My Pool"
        description="Run NFL Survivor or Pick 'Em pools with automated picks, standings, deadlines, commissioner controls, and mobile access."
        structuredData={{
          '@context': 'https://schema.org',
          '@graph': [
            {
              '@type': 'SoftwareApplication',
              name: 'Run My Pool',
              applicationCategory: 'SportsApplication',
              operatingSystem: 'Web',
              url: 'https://runmypool.net',
              description: "NFL Survivor and Pick 'Em pool management software for commissioners and players.",
              offers: { '@type': 'Offer', price: '0', priceCurrency: 'USD' },
            },
            {
              '@type': 'FAQPage',
              mainEntity: homepageFaqs.map((faq) => ({
                '@type': 'Question',
                name: faq.question,
                acceptedAnswer: { '@type': 'Answer', text: faq.answer },
              })),
            },
          ],
        }}
      />
      <header className="rmp-header">
        <nav className="rmp-shell" aria-label="Main navigation">
          <Link href="/" className="rmp-brand" aria-label="Run My Pool home">
            <BrandLogo className="rmp-brand__logo" priority />
          </Link>
          <div className="rmp-nav-links">
            <a href="#how">How it works</a>
            <a href="#features">Features</a>
            <a href="#pool-types">Pool formats</a>
            <a href="#faq">FAQ</a>
            <Link href="/pricing">Pricing</Link>
          </div>
          <div className="rmp-nav-actions">
            <Link href="/login" className="rmp-login">Login</Link>
            <Link href={createPoolHref} className="rmp-nav-cta">Start a pool <span>↗</span></Link>
          </div>
        </nav>
      </header>

      <main className="rmp-main">
        <section className="rmp-hero">
          <div className="rmp-shell rmp-hero-grid">
            <div className="rmp-hero-copy">
              <p className="rmp-eyebrow"><span /> BUILT FOR FOOTBALL PEOPLE</p>
              <h1><span className="rmp-sr-only">Run My Pool: </span>RUN THE POOL.<br /><em>OWN THE SEASON.</em></h1>
              <h2>Highly Configurable, Affordable, Scalable Pool Management System</h2>
              <p className="rmp-hero-intro">Run a Survivor, Pick &apos;Em, or Squares pool your crew talks about all week. Set it up in minutes, automate the busywork, and follow the action from kickoff to the final whistle.</p>
              <div className="rmp-hero-actions">
                <Link href={createPoolHref} className="rmp-button rmp-primary">Get Started Free <span>→</span></Link>
                <a href="#how" className="rmp-button rmp-secondary"><i>▶</i> See how it works</a>
              </div>
              <div className="rmp-proof">
                <div className="rmp-avatars"><span>JM</span><span>AK</span><span>SR</span><span>+</span></div>
                <p><b>Made for commissioners</b><small>Less admin. More football.</small></p>
              </div>
            </div>

            <div className="rmp-product-stage" aria-label="Run My Pool survivor pick preview">
              <div className="rmp-stage-glow" />
              <div className="rmp-week-chip"><i>●</i> PICKS OPEN <b>WEEK 08</b></div>
              <div className="rmp-pick-card">
                <div className="rmp-card-head">
                  <div><small>SUNDAY SURVIVOR</small><h3>Make your pick</h3></div>
                  <div className="rmp-deadline"><small>LOCKS IN</small><b>02:41:16</b></div>
                </div>
                <div className="rmp-progress"><div><span>1 PICK REQUIRED</span><span>WEEK 08</span></div><i><b /></i></div>
                <div className="rmp-game-list">
                  {games.map((game) => (
                    <div className={`rmp-game rmp-game-${game.className}`} key={game.away}>
                      <div className="rmp-game-time"><span>{game.number}</span><small>{game.time}</small></div>
                      <button className="rmp-team" type="button"><i>{game.away}</i><span><b>{game.awayName}</b><small>Available</small></span></button>
                      <span className="rmp-versus">VS</span>
                      <button className={`rmp-team rmp-home ${game.selected ? 'rmp-selected' : ''}`} type="button"><span><b>{game.homeName}</b><small>{game.selected ? 'Your pick' : 'Available'}</small></span><i>{game.selected ? '✓' : game.home}</i></button>
                    </div>
                  ))}
                </div>
                <button className="rmp-lock-picks" type="button">LOCK IN PICK <span>→</span></button>
                <div className="rmp-card-foot"><span>Auto-saved 12:38 PM</span><b><i /> LIVE SCORING ON</b></div>
              </div>
              <div className="rmp-rank-toast"><span>↑</span><div><small>YOUR RANK</small><b>Up 3 spots this week</b></div><strong>#04</strong></div>
            </div>
          </div>
          <div className="rmp-ticker"><div><span>LIVE</span><b>NYJ 17</b><i>3RD · 08:42</i><b>BUF 20</b></div><p>REAL-TIME SCORES <i>•</i> AUTOMATIC STANDINGS <i>•</i> ZERO SPREADSHEETS</p></div>
        </section>

        <section className="rmp-how" id="how">
          <div className="rmp-shell">
            <div className="rmp-section-kicker"><span>01</span><b>GAME PLAN</b></div>
            <div className="rmp-section-heading"><h2>FROM SETUP<br />TO <em>GAME DAY.</em></h2><p>A clear path for commissioners and members—from choosing a format to making picks, locking the week, and following the standings.</p></div>
            <div className="rmp-steps">
              {howSteps.map((step) => (
                <article key={step.number}>
                  <div className="rmp-step-number"><span>{step.number}</span><b>{step.eyebrow}</b></div>
                  <h3>{step.title}</h3>
                  <p>{step.copy}</p>
                  <ul>{step.details.map((detail) => <li key={detail}>{detail}</li>)}</ul>
                </article>
              ))}
            </div>
            <div className="rmp-how-roles">
              <div><span>FOR COMMISSIONERS</span><p>See participation, identify autopicks, manage locks and members, correct entries when needed, and export the audit log.</p></div>
              <div><span>FOR MEMBERS</span><p>See your remaining entries and weekly progress, change unlocked picks, review revealed pick counts, follow standings, and join the forum.</p></div>
            </div>
          </div>
        </section>

        <section className="rmp-features" id="features">
          <div className="rmp-shell">
            <div className="rmp-section-kicker rmp-light"><span>02</span><b>COMMISSIONER ADVANTAGE</b></div>
            <div className="rmp-feature-heading"><div><h3>Why Choose Run My Pool?</h3><h2>LESS ADMIN.<br /><em>MORE FOOTBALL.</em></h2></div><p>Everything you need to run a polished pool without chasing picks, fixing formulas, or spending Monday morning on standings.</p></div>
            <div className="rmp-feature-grid">
              {features.map((feature) => <article key={feature.title}><span>{feature.number}</span><div className="rmp-feature-icon">{feature.icon}</div><h4>{feature.title}</h4><p>{feature.copy}</p><ul>{feature.details.map((detail) => <li key={detail}>{detail}</li>)}</ul></article>)}
            </div>
          </div>
        </section>

        <section className="rmp-pool-types" id="pool-types">
          <div className="rmp-shell">
            <p className="rmp-eyebrow"><span /> TWO WAYS TO PLAY</p>
            <h2>YOUR CREW.<br /><em>YOUR FORMAT.</em></h2>
            <div className="rmp-format-grid">
              <article>
                <span>01 · SURVIVOR</span>
                <h3>LAST ENTRY STANDING</h3>
                <p>Pick one team each week without reusing it. Win and advance; lose and that entry is eliminated.</p>
                <ul><li>One pick per surviving entry</li><li>Configurable weekly lock time</li><li>Automatic results and autopicks</li></ul>
              </article>
              <article>
                <span>02 · PICK &apos;EM</span>
                <h3>MOST WINS TAKES IT</h3>
                <p>Pick the winner of every game each week with no point spreads. Every correct pick earns one point.</p>
                <ul><li>Every NFL matchup each week</li><li>One point for every winner</li><li>Season-long standings</li></ul>
              </article>
            </div>
            <Link href={createPoolHref} className="rmp-button rmp-primary">Compare packages and start <span>→</span></Link>
          </div>
        </section>

        <section className="rmp-home-faq" id="faq">
          <div className="rmp-shell">
            <div className="rmp-section-kicker"><span>04</span><b>BEFORE KICKOFF</b></div>
            <div className="rmp-home-faq__heading">
              <h2>QUESTIONS,<br /><em>ANSWERED.</em></h2>
              <p>The essentials for commissioners and members before the first pick is made.</p>
            </div>
            <div className="rmp-home-faq__grid">
              {homepageFaqs.map((faq) => (
                <details key={faq.question}>
                  <summary>{faq.question}<span aria-hidden="true">+</span></summary>
                  <p>{faq.answer}</p>
                </details>
              ))}
            </div>
            <p className="rmp-home-faq__support">Still need help? <Link href="/support">Contact support</Link>.</p>
          </div>
        </section>
      </main>

      <footer className="rmp-footer"><div className="rmp-shell"><Link href="/" className="rmp-brand"><BrandLogo className="rmp-brand__logo" alt="Run My Pool" /></Link><p>Built for football fans, by football fans. <Link href="/pricing">Pricing</Link> · <Link href="/install">Install the app</Link> · <Link href="/support">Contact support</Link></p><span>© 2026 Run My Pool</span></div></footer>
    </div>
  );
}
