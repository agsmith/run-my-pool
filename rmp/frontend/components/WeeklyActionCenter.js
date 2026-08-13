function weeklyGuidance(summary) {
  if (!summary.total_entries) {
    return {
      message: 'Create your first entry to start making weekly selections.',
      action: 'Create your first entry',
      createEntry: true,
    };
  }
  if (!summary.week_selection_total) {
    return {
      message: `Week ${summary.week} matchups are not available yet. Your entries are ready when the schedule is posted.`,
      action: 'Review entries',
    };
  }
  if (summary.week_selections >= summary.week_selection_total) {
    return {
      message: `You’re set for Week ${summary.week}. You can review or change unlocked selections.`,
      action: 'Review picks',
    };
  }
  const remaining = summary.week_selection_total - summary.week_selections;
  return {
    message: `${remaining} ${remaining === 1 ? 'selection' : 'selections'} still needed for Week ${summary.week}.`,
    action: summary.week_selections ? 'Continue picks' : 'Make picks',
  };
}

export default function WeeklyActionCenter({ summary, loading, error, onAction }) {
  if (loading) {
    return <section className="weekly-action weekly-action--loading" aria-label="Weekly action center">Loading your weekly status…</section>;
  }
  if (error || !summary) {
    return (
      <section className="weekly-action weekly-action--error" aria-label="Weekly action center">
        <strong>Weekly status unavailable</strong>
        <span>You can still open your entries and make picks.</span>
        <button onClick={() => onAction(false)}>Open my entries</button>
      </section>
    );
  }

  const guidance = weeklyGuidance(summary);
  return (
    <section className="weekly-action" aria-labelledby="weekly-action-title">
      <div className="weekly-action__intro">
        <span>This week</span>
        <h2 id="weekly-action-title">Week {summary.week} Action Center</h2>
        <p>{guidance.message}</p>
      </div>
      <dl className="weekly-action__stats">
        <div>
          <dt>Entries remaining</dt>
          <dd>{summary.entries_remaining}/{summary.total_entries}</dd>
        </div>
        <div>
          <dt>Selections submitted</dt>
          <dd>{summary.week_selections}/{summary.week_selection_total}</dd>
        </div>
      </dl>
      <button className="weekly-action__button" onClick={() => onAction(Boolean(guidance.createEntry))}>
        {guidance.action}
      </button>
    </section>
  );
}
