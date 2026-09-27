import { useEffect, useState } from 'react';
import PoolEmailExport from './PoolEmailExport';

export default function AdminPickEmCompletionReport({ report, loading, error, onWeekChange, onRefresh }) {
  const [week, setWeek] = useState(report?.week || 1);
  const incompleteEntries = report?.incomplete_entries || [];
  const emailUsers = incompleteEntries
    .filter((entry) => entry.contact_email)
    .map((entry) => ({ email: entry.contact_email }));

  useEffect(() => {
    if (report?.week) setWeek(report.week);
  }, [report?.week]);

  function changeWeek(event) {
    const selectedWeek = Number(event.target.value);
    setWeek(selectedWeek);
    onWeekChange(selectedWeek);
  }

  return <section className="admin-user-overview" aria-labelledby="pickem-completion-title">
    <div className="admin-user-overview__head">
      <div>
        <span>Commissioner follow-up</span>
        <h4 id="pickem-completion-title">Weekly Pick Completion</h4>
        <p>Entries listed below still need one or more picks or a point-total tiebreaker.</p>
      </div>
      <div className="admin-user-overview__tools">
        <label htmlFor="pickem-completion-week">Week</label>
        <div>
          <select id="pickem-completion-week" value={week} disabled={loading} onChange={changeWeek}>
            {Array.from({ length: 18 }, (_, index) => index + 1).map((value) => <option key={value} value={value}>Week {value}</option>)}
          </select>
          <button type="button" disabled={loading} onClick={() => onRefresh(week)}>Refresh completion</button>
        </div>
      </div>
    </div>

    {report && !loading && !error && <p role="status">
      {report.entries_needing_attention} of {report.total_entries} {report.total_entries === 1 ? 'entry needs' : 'entries need'} attention for Week {report.week}.
    </p>}

    <PoolEmailExport
      key={week}
      title={`Week ${week} incomplete-pick emails`}
      description="Copy the email addresses for members who still need picks or a required tiebreaker. Each address appears once."
      copyLabel="Copy incomplete emails"
      copyOnly
      users={emailUsers}
      disabled={loading || Boolean(error) || emailUsers.length === 0}
    />

    {error ? <div className="admin-user-overview__state is-error" role="alert">{error}</div> : loading ?
      <div className="admin-user-overview__state">Loading weekly completion…</div> : incompleteEntries.length === 0 ?
      <div className="admin-user-overview__state">All entries are complete for Week {week}.</div> :
      <div className="admin-user-overview__table-wrap"><table className="admin-user-overview__table">
        <thead><tr><th>Participant</th><th>Entry</th><th>Picks</th><th>Still needed</th><th>Point-total tiebreaker</th></tr></thead>
        <tbody>{incompleteEntries.map((entry) => <tr key={entry.entry_id}>
          <td data-label="Participant"><strong>{entry.participant_name}</strong><small>{entry.contact_email || 'Paper entry — follow up directly'}</small></td>
          <td data-label="Entry">{entry.entry_name}</td>
          <td data-label="Picks">{entry.picks_made} / {entry.picks_required}</td>
          <td data-label="Still needed"><span className={`admin-pick-status ${entry.missing_picks ? 'is-missing' : 'is-complete'}`}>{entry.missing_picks ? `${entry.missing_picks} ${entry.missing_picks === 1 ? 'pick' : 'picks'}` : 'Picks complete'}</span></td>
          <td data-label="Point-total tiebreaker"><span className={`admin-pick-status ${entry.missing_tiebreaker ? 'is-missing' : 'is-complete'}`}>{report.requires_tiebreaker ? (entry.tiebreaker_set ? 'Set' : 'Missing') : 'Not required'}</span></td>
        </tr>)}</tbody>
      </table></div>}
  </section>;
}
