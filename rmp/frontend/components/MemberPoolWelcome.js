export default function MemberPoolWelcome({ pool, onCreateEntry, onDismiss }) {
  const isPickEm = pool.pool_type === 'pickem';
  return (
    <section className="member-pool-welcome" aria-label="Pool membership welcome">
      <div>
        <span>YOU&apos;RE IN</span>
        <h2>WELCOME TO {pool.name.toUpperCase()}</h2>
        <p>{isPickEm
          ? 'Create an entry, then pick the winner of every game each week. Every correct pick earns one point.'
          : 'Create your first entry, then choose one eligible team each week and keep surviving.'}</p>
      </div>
      <div className="member-pool-welcome__actions">
        <button type="button" onClick={onCreateEntry}>Create your first entry</button>
        <button type="button" onClick={onDismiss}>Explore pool first</button>
      </div>
    </section>
  );
}
