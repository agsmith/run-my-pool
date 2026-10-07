import PoolFormatLanding from '../components/PoolFormatLanding';

const format = {
  eyebrow: 'NFL PICK EM POOL SOFTWARE',
  title: "NFL Pick 'Em Pool",
  accent: "Pick 'Em",
  path: '/nfl-pick-em-pool',
  analyticsPage: 'pickem_landing',
  description: "Run an NFL Pick 'Em pool online with every weekly matchup, configurable deadlines, tiebreakers, automatic scoring, and season standings.",
  intro: 'Players choose the winner of every NFL game with no point spreads. Each correct winner earns one point, and Run My Pool scores the week, applies the Monday-night total tiebreaker, and updates the season leaderboard.',
  steps: [
    { title: 'Create the pool', copy: 'Choose privacy, entry limits, the weekly deadline, timezone, and the games included in each week.' },
    { title: 'Make every pick', copy: 'Members choose one winner per matchup and enter the Monday-night total score tiebreaker.' },
    { title: 'Reveal after lock', copy: 'Weekly Pick Breakdown shows each entry, its selections, current wins, losses, and tiebreaker.' },
    { title: 'Score the season', copy: 'Completed games add points automatically and the Season Leaderboard keeps the highest totals on top.' },
  ],
  features: [
    'Straight-up NFL winners with no against-the-spread scoring',
    'Game list ordered chronologically by kickoff time',
    'Monday-night combined-score tiebreaker',
    'Automatic weekly wins, losses, and point totals',
    'Weekly Pick Breakdown after the pool deadline',
    'Season Leaderboard ranked by total correct picks',
    'Commissioner report for missing picks and tiebreakers',
    'Mobile-friendly website and native iPhone app',
  ],
  faqs: [
    { question: "How does NFL Pick 'Em scoring work?", answer: 'Every correct straight-up winner earns one point. The entry with the most correct picks wins the week, and points accumulate in the season standings.' },
    { question: 'Are picks made against the point spread?', answer: 'No. Run My Pool Pick ’Em uses straight-up winners. Favorite and underdog labels provide context without making the pool against the spread.' },
    { question: 'How does the weekly tiebreaker work?', answer: 'Players predict the combined score of the designated Monday-night game. Closest wins; when two entries are equally close, the lower prediction wins. A remaining tie can be handled under the pool rules.' },
    { question: 'When can members see everyone’s picks?', answer: 'Weekly picks remain private until the pool deadline. After lock, members can open Weekly Pick Breakdown to see the entries and selections.' },
    { question: 'Does Run My Pool handle money or wagering?', answer: 'No. Run My Pool is entertainment pool-management software and does not accept wagers, collect entry stakes, hold funds, or distribute prizes.' },
  ],
};

export default function NflPickEmPoolPage() {
  return <PoolFormatLanding format={format} />;
}
