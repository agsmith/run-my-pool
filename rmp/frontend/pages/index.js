import Link from 'next/link';
import { useAuth } from '../context/AuthContext';
import Seo from '../components/Seo';

const games = [
  { number: '01', time: 'SUN 1:00', away: 'BUF', awayName: 'Buffalo', home: 'NYJ', homeName: 'New York', className: 'blue' },
  { number: '02', time: 'SUN 4:25', away: 'GB', awayName: 'Green Bay', home: 'CHI', homeName: 'Chicago', className: 'green', selected: true },
  { number: '03', time: 'SNF 8:20', away: 'DAL', awayName: 'Dallas', home: 'PHI', homeName: 'Philadelphia', className: 'navy' },
];

const features = [
  { number: '01', title: 'Highly Configurable', copy: 'Set lock times, entry rules, autopicks, scoring, and tiebreakers. Your pool, your call.' },
  { number: '02', title: 'Affordable', copy: 'Everything your commissioner needs without enterprise pricing or surprise fees.' },
  { number: '03', title: 'Mobile App', copy: 'Make picks, check results, and follow the leaderboard from any screen.' },
];

function FootballMark() {
  return <span className="rmp-mark" aria-hidden="true"><i /><i /><i /></span>;
}

export default function Home() {
  const { user } = useAuth();
  const createPoolHref = user ? '/create-pool?source=splash' : '/create-account?intent=create-pool';

  return (
    <div className="rmp-landing">
      <Seo
        title="Run My Pool"
        description="Run a professional NFL survivor pool with automated picks, standings, deadlines, commissioner controls, and mobile access."
        structuredData={{
          '@context': 'https://schema.org',
          '@type': 'SoftwareApplication',
          name: 'Run My Pool',
          applicationCategory: 'SportsApplication',
          operatingSystem: 'Web',
          url: 'https://runmypool.net',
          description: 'NFL survivor pool management software for commissioners and players.',
          offers: { '@type': 'Offer', price: '0', priceCurrency: 'USD' },
        }}
      />
      <header className="rmp-header">
        <nav className="rmp-shell" aria-label="Main navigation">
          <Link href="/" className="rmp-brand" aria-label="Run My Pool home">
            <FootballMark /><span>RUN MY <b>POOL</b></span>
          </Link>
          <div className="rmp-nav-links">
            <a href="#how">How it works</a>
            <a href="#features">Features</a>
            <a href="#pool-types">Pool formats</a>
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
              <p className="rmp-hero-intro">Run a survivor pool your crew talks about all week. Set it up in minutes, automate the busywork, and follow every pick from kickoff to the final whistle.</p>
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
            <div className="rmp-section-heading"><h2>FROM GROUP CHAT<br />TO <em>GAME ON.</em></h2><p>We handle the repetitive stuff. You set the rules, invite your people, and enjoy the season.</p></div>
            <div className="rmp-steps">
              <article><span>01</span><div className="rmp-step-icon rmp-sliders"><i/><i/><i/></div><h3>SET THE RULES</h3><p>Choose your schedule, lock time, entry limits, and autopick behavior.</p></article>
              <article><span>02</span><div className="rmp-step-icon rmp-people"><i/><i/><i/></div><h3>INVITE THE CREW</h3><p>Share one simple link. Players can join and make picks from any device.</p></article>
              <article><span>03</span><div className="rmp-step-icon rmp-trophy"><i>★</i></div><h3>LET IT RUN</h3><p>Results and standings update automatically. You just bring the banter.</p></article>
            </div>
          </div>
        </section>

        <section className="rmp-features" id="features">
          <div className="rmp-shell">
            <div className="rmp-section-kicker rmp-light"><span>02</span><b>COMMISSIONER ADVANTAGE</b></div>
            <div className="rmp-feature-heading"><div><h3>Why Choose Run My Pool?</h3><h2>LESS ADMIN.<br /><em>MORE FOOTBALL.</em></h2></div><p>Everything you need to run a polished pool without chasing picks, fixing formulas, or spending Monday morning on standings.</p></div>
            <div className="rmp-feature-grid">
              {features.map((feature) => <article key={feature.title}><span>{feature.number}</span><div className="rmp-feature-icon">{feature.number === '01' ? '≡' : feature.number === '02' ? '$' : '↗'}</div><h4>{feature.title}</h4><p>{feature.copy}</p></article>)}
            </div>
          </div>
        </section>

        <section className="rmp-pool-types" id="pool-types">
          <div className="rmp-shell">
            <p className="rmp-eyebrow"><span /> CLASSIC SURVIVOR, DONE RIGHT</p>
            <h2>ONE TEAM. EVERY WEEK.<br /><em>LAST ENTRY STANDING.</em></h2>
            <p>Choose a team you haven&apos;t used. Win and advance. Lose and your run is over. Run My Pool keeps every entry, deadline, and result organized automatically.</p>
            <Link href={createPoolHref} className="rmp-button rmp-primary">Create your survivor pool <span>→</span></Link>
          </div>
        </section>
      </main>

      <footer className="rmp-footer"><div className="rmp-shell"><Link href="/" className="rmp-brand"><FootballMark /><span>RUN MY <b>POOL</b></span></Link><p>Built for football fans, by football fans. <Link href="/pricing">Pricing</Link> · <Link href="/install">Install the app</Link> · <a href="mailto:support@runmypool.net">Contact support</a></p><span>© 2026 Run My Pool</span></div></footer>
    </div>
  );
}
