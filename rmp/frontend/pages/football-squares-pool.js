import PoolFormatLanding from '../components/PoolFormatLanding';

const format = {
  eyebrow: 'ONLINE FOOTBALL SQUARES',
  title: 'Football Squares Pool',
  accent: 'Squares',
  path: '/football-squares-pool',
  analyticsPage: 'squares_landing',
  description: 'Run a 100-square football pool online with player reservations, randomized score digits, automatic quarter winners, and printable boards.',
  intro: 'Create a clean 10×10 football squares board, let members reserve available squares, and randomize the score digits when the board locks. Run My Pool identifies the winning square at each configured scoring period.',
  steps: [
    { title: 'Create the board', copy: 'Choose the teams, game, board lock, privacy, and the scoring periods used by your group.' },
    { title: 'Fill 100 squares', copy: 'Invite members to reserve open squares or enter externally received selections as the owner.' },
    { title: 'Randomize digits', copy: 'When the board is ready, assign each axis the score-ending digits zero through nine.' },
    { title: 'Find each winner', copy: 'Match the score’s final digit for each team to the board at quarter, halftime, or final.' },
  ],
  features: [
    'Complete 10×10 board with 100 reservable squares',
    'Online member reservations or owner-managed entry',
    'Randomized row and column score digits',
    'Quarter, halftime, and final winning-square tracking',
    'Printable board and branded PDF export',
    'Public or password-protected access',
    'Mobile-friendly board and commissioner controls',
    'Free owner-managed board option',
  ],
  faqs: [
    { question: 'How does a football squares pool work?', answer: 'A 10×10 grid has one team on each axis. After the squares are filled, each axis receives the digits zero through nine. The last digit of each team’s score identifies the winning square at each scoring period.' },
    { question: 'Can players choose squares online?', answer: 'Yes on Squares Plus and commissioner plans. The Free plan also supports a complete board that the owner fills using selections received outside Run My Pool.' },
    { question: 'When are the score digits assigned?', answer: 'The commissioner randomizes the row and column digits after the board is ready, preserving the familiar football-squares format.' },
    { question: 'Can I print the completed board?', answer: 'Yes. Commissioners can generate a clean branded printout or PDF for sharing and game-day display.' },
    { question: 'Does Run My Pool collect money for squares?', answer: 'No. Run My Pool manages the board only. It does not collect stakes, hold funds, or distribute prizes.' },
  ],
};

export default function FootballSquaresPoolPage() {
  return <PoolFormatLanding format={format} />;
}
