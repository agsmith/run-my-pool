import Link from 'next/link';

export function WorkspaceHeader({ eyebrow, title, description, meta, actions }) {
  return (
    <section className="workspace-hero">
      <div className="workspace-hero__copy">
        {eyebrow && <div className="workspace-hero__eyebrow">{eyebrow}</div>}
        <h1>{title}</h1>
        {description && <p>{description}</p>}
      </div>
      {(meta || actions) && (
        <div className="workspace-hero__aside">
          {meta && <div className="workspace-hero__meta">{meta}</div>}
          {actions && <div className="workspace-hero__actions">{actions}</div>}
        </div>
      )}
    </section>
  );
}

export function PoolWorkspaceNav({ poolId, poolName, active, showAdmin = false }) {
  if (!poolId) return null;

  const items = [
    { id: 'overview', label: 'Pool Home', href: `/pool/${poolId}` },
    { id: 'entries', label: 'Picks & Entries', href: `/pool/${poolId}/entries` },
    { id: 'matchups', label: 'Matchups & Lines', href: `/pool/${poolId}/matchups` },
    { id: 'messages', label: 'Pool Messages', href: `/pool/${poolId}/messages` },
  ];

  if (showAdmin) {
    items.push({ id: 'admin', label: 'Commissioner', href: `/admin/league/${poolId}` });
  }

  return (
    <div className="pool-workspace-nav" aria-label={`${poolName || 'Pool'} navigation`}>
      <div className="pool-workspace-nav__identity">
        <span className="pool-workspace-nav__live">Live pool</span>
        <strong>{poolName || 'Pool workspace'}</strong>
      </div>
      <nav>
        {items.map((item) => (
          <Link
            key={item.id}
            href={item.href}
            className={active === item.id ? 'is-active' : ''}
            aria-current={active === item.id ? 'page' : undefined}
          >
            {item.label}
          </Link>
        ))}
      </nav>
    </div>
  );
}
