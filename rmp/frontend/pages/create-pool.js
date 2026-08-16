import { useState } from 'react';
import { useRouter } from 'next/router';
import ProtectedRoute from '../components/ProtectedRoute';

const DAYS = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday'];
const TIMEZONES = [
  ['America/New_York', 'Eastern Time (ET)'],
  ['America/Chicago', 'Central Time (CT)'],
  ['America/Denver', 'Mountain Time (MT)'],
  ['America/Los_Angeles', 'Pacific Time (PT)'],
];

export function getServerSideProps({ query }) {
  if (query.source !== 'splash') return { redirect: { destination: '/', permanent: false } };
  return { props: {} };
}

export default function CreatePool() {
  const router = useRouter();
  const [form, setForm] = useState({
    name: '', description: '', pool_type: 'survivor',
    pickem_games_per_week: 'all',
    squares_game_ids: [],
    lock_day_of_week: 6, lock_time_of_day: '13:00', lock_timezone: 'America/New_York',
    is_private: false, join_password: '',
  });
  const [error, setError] = useState('');
  const [nameSuggestions, setNameSuggestions] = useState([]);
  const [loading, setLoading] = useState(false);
  const [upcomingGames, setUpcomingGames] = useState([]);

  const update = (field, value) => {
    setForm((current) => ({ ...current, [field]: value }));
    if (field === 'name') setNameSuggestions([]);
  };

  const selectType = (poolType) => {
    setForm((current) => ({ ...current, pool_type: poolType }));
    setError('');
    if (poolType === 'squares' && upcomingGames.length === 0) {
      fetch(`${process.env.NEXT_PUBLIC_API_URL}/schedule/`)
        .then((response) => response.ok ? response.json() : [])
        .then((games) => setUpcomingGames(games.filter((game) => new Date(game.start_time) > new Date()).slice(0, 80)))
        .catch(() => setError('Unable to load upcoming NFL games.'));
    }
  };

  const handleSubmit = async (event) => {
    event.preventDefault();
    setError('');
    setNameSuggestions([]);
    setLoading(true);
    try {
      const response = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/pools/create`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${localStorage.getItem('access_token')}`,
        },
        body: JSON.stringify({
          name: form.name.trim(),
          description: form.description.trim() || null,
          pool_type: form.pool_type,
          pickem_games_per_week: form.pool_type === 'pickem' && form.pickem_games_per_week !== 'all'
            ? Number(form.pickem_games_per_week)
            : null,
          squares_game_ids: form.pool_type === 'squares' ? form.squares_game_ids.map(Number) : null,
          lock_day_of_week: Number(form.lock_day_of_week),
          lock_time_of_day: `${form.lock_time_of_day}:00`,
          lock_timezone: form.lock_timezone,
          is_private: form.is_private,
          join_password: form.is_private ? form.join_password.trim() : null,
          rule_values: [],
        }),
      });
      const data = await response.json().catch(() => ({}));
      if (!response.ok) {
        if (data.detail?.code === 'league_name_taken') {
          setNameSuggestions(data.detail.suggestions || []);
          throw new Error(data.detail.message);
        }
        throw new Error(typeof data.detail === 'string' ? data.detail : 'Failed to create pool');
      }
      router.push(form.pool_type === 'squares' ? `/pool/${data.id}/squares` : `/pool/${data.id}?launched=1`);
    } catch (requestError) {
      setError(requestError.message || 'Failed to create pool');
    } finally {
      setLoading(false);
    }
  };

  const isPickEm = form.pool_type === 'pickem';
  const isSquares = form.pool_type === 'squares';
  const toggleSquaresGame = (gameId) => setForm((current) => ({
    ...current,
    squares_game_ids: current.squares_game_ids.includes(gameId)
      ? current.squares_game_ids.filter((id) => id !== gameId)
      : [...current.squares_game_ids, gameId],
  }));

  return <ProtectedRoute><main className="create-pool-page">
    <header className="create-pool-header">
      <button type="button" className="create-pool-brand" onClick={() => router.push('/')}>🏈 Run My Pool</button>
      <button type="button" className="create-pool-exit" onClick={() => router.push('/dashboard')}>Cancel</button>
    </header>

    <form className="create-pool-form" onSubmit={handleSubmit}>
      <div className="create-pool-intro">
        <span>New pool</span>
        <h1>Set up your pool</h1>
        <p>Choose a format, set the weekly deadline, and invite players.</p>
      </div>

      <fieldset className="create-pool-section create-pool-format">
        <legend>1. Choose a format</legend>
        <div className="create-pool-format-grid">
          <label className={form.pool_type === 'survivor' ? 'is-selected' : ''}>
            <input type="radio" name="pool_type" value="survivor" checked={form.pool_type === 'survivor'} onChange={() => selectType('survivor')} />
            <span className="create-pool-format-title">Survivor <b>Classic</b></span>
            <strong>One team per week</strong>
            <small>A correct pick survives. A losing pick eliminates the entry. Teams cannot be reused.</small>
          </label>
          <label className={isSquares ? 'is-selected' : ''}>
            <input type="radio" name="pool_type" value="squares" checked={isSquares} onChange={() => selectType('squares')} />
            <span className="create-pool-format-title">Squares <b>Game day</b></span>
            <strong>Claim a spot on the 10×10 grid</strong>
            <small>Score digits are securely randomized when the board locks. Winners are recorded after each quarter.</small>
          </label>
          <label className={isPickEm ? 'is-selected' : ''}>
            <input type="radio" name="pool_type" value="pickem" checked={isPickEm} onChange={() => selectType('pickem')} />
            <span className="create-pool-format-title">Pick ’Em</span>
            <strong>Pick the weekly slate</strong>
            <small>No spreads. Default to every game or require a smaller number. Every correct winner earns one point.</small>
          </label>
        </div>
      </fieldset>

      {isPickEm && <section className="create-pool-section">
        <h2>2. Pick ’Em slate</h2>
        <p className="create-pool-help">Choose how many games each entry needs to pick every week. Members may select any games from that week&apos;s schedule.</p>
        <label className="create-pool-field">
          <span>Required games per week</span>
          <select aria-label="Required games per week" value={form.pickem_games_per_week} onChange={(event) => update('pickem_games_per_week', event.target.value)}>
            <option value="all">All scheduled games (default)</option>
            {Array.from({ length: 16 }, (_, index) => index + 1).map((count) => <option key={count} value={count}>{count} game{count === 1 ? '' : 's'}</option>)}
          </select>
          <small>{form.pickem_games_per_week === 'all' ? 'The target automatically matches the number of games scheduled that week.' : `Each entry can make up to ${form.pickem_games_per_week} selections per week.`}</small>
        </label>
      </section>}

      {isSquares && <section className="create-pool-section">
        <h2>2. Choose the games</h2>
        <p className="create-pool-help">Select one or many games for this board. The same squares and randomized digits apply to every game, and the entire board locks at the earliest selected kickoff.</p>
        <div className="create-pool-game-picker" role="group" aria-label="Squares games">
          {upcomingGames.map((game) => {
            const gameId = String(game.game_id);
            const selected = form.squares_game_ids.includes(gameId);
            return <label key={game.game_id} className={selected ? 'is-selected' : ''}>
              <input type="checkbox" checked={selected} onChange={() => toggleSquaresGame(gameId)} />
              <strong>{game.away_team.abbrv} at {game.home_team.abbrv}</strong>
              <small>{new Date(game.start_time).toLocaleString()}</small>
            </label>;
          })}
        </div>
        <small className="create-pool-selection-count">{form.squares_game_ids.length} game{form.squares_game_ids.length === 1 ? '' : 's'} selected</small>
      </section>}

      <section className="create-pool-section">
        <h2>{isPickEm || isSquares ? '3' : '2'}. Pool details</h2>
        <label className="create-pool-field">
          <span>Pool name <b>*</b></span>
          <input type="text" value={form.name} onChange={(event) => update('name', event.target.value)} required maxLength={255} placeholder="Enter pool name" autoFocus />
        </label>
        <label className="create-pool-field">
          <span>Description <small>Optional</small></span>
          <textarea value={form.description} onChange={(event) => update('description', event.target.value)} rows={3} placeholder={isPickEm ? 'Example: Pick every winner and climb the season standings.' : 'Example: Survive every week without reusing a team.'} />
        </label>
      </section>

      {!isSquares && <section className="create-pool-section">
        <h2>{isPickEm ? '4' : '3'}. Weekly pick deadline</h2>
        <p className="create-pool-help">All selections lock at this time each week. Games that start earlier lock individually at kickoff.</p>
        <div className="create-pool-deadline-grid">
          <label className="create-pool-field"><span>Day</span><select aria-label="Lock day" value={form.lock_day_of_week} onChange={(event) => update('lock_day_of_week', event.target.value)}>{DAYS.map((day, index) => <option key={day} value={index}>{day}</option>)}</select></label>
          <label className="create-pool-field"><span>Time</span><input aria-label="Lock time" type="time" value={form.lock_time_of_day} onChange={(event) => update('lock_time_of_day', event.target.value)} required /></label>
          <label className="create-pool-field"><span>Time zone</span><select aria-label="Lock time zone" value={form.lock_timezone} onChange={(event) => update('lock_timezone', event.target.value)}>{TIMEZONES.map(([value, label]) => <option key={value} value={value}>{label}</option>)}</select></label>
        </div>
        <div className="create-pool-note"><strong>{isPickEm ? 'Pick ’Em lock behavior' : 'Survivor lock behavior'}</strong><span>{isPickEm ? 'Submitted game picks become final. Missing games receive no selection and no point.' : 'Submitted picks become final. Entries without a selection receive the best available automatic pick.'}</span></div>
      </section>}

      <section className="create-pool-section">
        <h2>{isPickEm ? '5' : isSquares ? '4' : '4'}. Player access</h2>
        <div className="create-pool-access-grid">
          <label className={!form.is_private ? 'is-selected' : ''}><input type="radio" name="visibility" checked={!form.is_private} onChange={() => update('is_private', false)} /><strong>Public</strong><small>Anyone can find and join this pool.</small></label>
          <label className={form.is_private ? 'is-selected' : ''}><input type="radio" name="visibility" checked={form.is_private} onChange={() => update('is_private', true)} /><strong>Private</strong><small>Visible in the directory, but a join code is required.</small></label>
        </div>
        {form.is_private && <label className="create-pool-field create-pool-password"><span>Join code <b>*</b></span><input type="text" value={form.join_password} onChange={(event) => update('join_password', event.target.value)} minLength={6} maxLength={72} required autoComplete="off" data-1p-ignore="true" data-lpignore="true" placeholder="At least 6 characters" /><small>This is an ordinary shareable pool code, not an account password.</small></label>}
      </section>

      {error && <div className="create-pool-error" role="alert"><strong>Pool could not be created</strong><span>{error}</span>{nameSuggestions.length > 0 && <div><small>Try an available name:</small>{nameSuggestions.map((suggestion) => <button key={suggestion} type="button" onClick={() => { update('name', suggestion); setError(''); }}>{suggestion}</button>)}</div>}</div>}

      <footer className="create-pool-actions">
        <button type="button" onClick={() => router.push('/dashboard')}>Cancel</button>
        <button type="submit" disabled={loading || !form.name.trim() || (isSquares && form.squares_game_ids.length === 0)}>{loading ? 'Creating pool…' : `Create ${isPickEm ? 'Pick ’Em' : isSquares ? 'Squares' : 'Survivor'} Pool`}</button>
      </footer>
    </form>
  </main></ProtectedRoute>;
}
