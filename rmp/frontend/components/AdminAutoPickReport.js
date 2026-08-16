export default function AdminAutoPickReport({ week, onWeekChange, records, loading, error }) {
  return <section className="admin-user-overview" aria-labelledby="auto-pick-report-title">
    <div className="admin-user-overview__head">
      <div>
        <span>Weekly compliance</span>
        <h4 id="auto-pick-report-title">Autopick report</h4>
        <p>Entries that had no user-submitted pick and received the best available team at lock.</p>
      </div>
      <div className="admin-user-overview__tools">
        <label htmlFor="auto-pick-week">Week</label>
        <select id="auto-pick-week" value={week} onChange={(event) => onWeekChange(Number(event.target.value))}>
          {Array.from({ length: 18 }, (_, index) => index + 1).map((value) => <option key={value} value={value}>Week {value}</option>)}
        </select>
      </div>
    </div>
    {error ? <div className="admin-user-overview__state is-error" role="alert">{error}</div> : loading ?
      <div className="admin-user-overview__state">Loading autopicks…</div> : records.length === 0 ?
      <div className="admin-user-overview__state">No autopicks were made for Week {week}.</div> :
      <div className="admin-user-overview__table-wrap"><table className="admin-user-overview__table">
        <thead><tr><th>User</th><th>Entry</th><th>Autopick</th><th>Selected at</th></tr></thead>
        <tbody>{records.map((record) => <tr key={record.audit_id}>
          <td data-label="User"><strong>{record.user_email}</strong></td>
          <td data-label="Entry">{record.entry_name}</td>
          <td data-label="Autopick">{record.team}</td>
          <td data-label="Selected at">{new Date(record.created_at).toLocaleString()}</td>
        </tr>)}</tbody>
      </table></div>}
  </section>;
}
