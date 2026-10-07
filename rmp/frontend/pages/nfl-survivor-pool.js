import PoolFormatLanding from '../components/PoolFormatLanding';

const format = {
  eyebrow: 'NFL SURVIVOR POOL SOFTWARE',
  title: 'NFL Survivor Pool',
  accent: 'Survivor',
  path: '/nfl-survivor-pool',
  analyticsPage: 'survivor_landing',
  description: 'Run an NFL Survivor pool online with weekly picks, configurable deadlines, eligible autopicks, automatic results, and live season standings.',
  intro: 'Give every entry one team each week. A winner advances, a loser is eliminated, and a team cannot be reused. Run My Pool handles deadlines, eligible autopicks, results, and standings for you.',
  steps: [
    { title: 'Create the pool', copy: 'Set the entry rules, privacy, weekly deadline, timezone, and autopick policy for your group.' },
    { title: 'Invite players', copy: 'Share one link so members can join, name their entries, and manage every pick in one place.' },
    { title: 'Lock the week', copy: 'Picks lock at your deadline or when the selected game begins. Eligible missing picks can receive an autopick.' },
    { title: 'Advance survivors', copy: 'Final scores settle the picks automatically and keep surviving entries above eliminated entries.' },
  ],
  features: [
    'One unique NFL team per surviving entry each week',
    'Commissioner-defined weekly lock day, time, and timezone',
    'Eligible autopicks with a visible AP label after lock',
    'Automatic wins, losses, eliminations, and weeks survived',
    'Weekly Pick Breakdown after the deadline',
    'Season leaderboard for surviving and eliminated entries',
    'Mobile-friendly website and native iPhone app',
    'Commissioner exports, pick corrections, and audit history',
  ],
  faqs: [
    { question: 'What is an NFL Survivor pool?', answer: 'Each entry chooses one NFL team to win each week. A winning team advances the entry, a losing team eliminates it, and teams generally cannot be selected twice by the same entry.' },
    { question: 'What happens when someone forgets to pick?', answer: 'If the commissioner enables autopicks, Run My Pool can select an eligible team at the weekly deadline. The revealed pick is labeled AP so members can distinguish it from a member selection.' },
    { question: 'Can Thursday games lock before the weekly deadline?', answer: 'Yes. A selection involving an early game locks when that game starts, even when the general pool deadline is later.' },
    { question: 'Can I run a private Survivor pool?', answer: 'Yes. A commissioner can require a pool password and share the join link only with invited members.' },
    { question: 'Does Run My Pool collect entry fees or prizes?', answer: 'No. Run My Pool provides pool-management software and does not collect stakes, hold prize funds, or distribute winnings.' },
  ],
};

export default function NflSurvivorPoolPage() {
  return <PoolFormatLanding format={format} />;
}
