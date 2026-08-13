import { useEffect, useRef, useState } from 'react';
import Link from 'next/link';
import ProtectedRoute from '../components/ProtectedRoute';
import { useAuth } from '../context/AuthContext';
import { trackLifecycleEvent } from '../lib/lifecycleAnalytics';

const PLAN_LABELS = {
  commissioner: 'Commish',
  pro: 'Pro',
  club: 'Club',
  'club-unlimited': 'Club Unlimited',
};

function formatMoney(amount, currency = 'usd') {
  if (amount == null) return 'Amount pending';
  return new Intl.NumberFormat('en-US', {
    style: 'currency',
    currency: currency.toUpperCase(),
  }).format(amount / 100);
}

function formatDate(value) {
  if (!value) return 'Pending';
  const date = new Date(value);
  return Number.isNaN(date.getTime()) ? 'Pending' : date.toLocaleDateString();
}

export default function Profile() {
  const { user, logout } = useAuth();
  const [billing, setBilling] = useState(null);
  const [billingError, setBillingError] = useState('');
  const trackedOverview = useRef(false);
  const season = Number(process.env.NEXT_PUBLIC_NFL_SEASON) || new Date().getFullYear();

  useEffect(() => {
    let cancelled = false;
    const loadBilling = async () => {
      try {
        const token = localStorage.getItem('access_token');
        const response = await fetch(
          `${process.env.NEXT_PUBLIC_API_URL}/billing/overview?season=${season}`,
          { headers: { Authorization: `Bearer ${token}` }, credentials: 'include' },
        );
        if (!response.ok) throw new Error('Unable to load billing details.');
        const data = await response.json();
        if (!cancelled) setBilling(data);
      } catch (error) {
        if (!cancelled) setBillingError(error.message || 'Unable to load billing details.');
      }
    };
    loadBilling();
    return () => { cancelled = true; };
  }, [season]);

  useEffect(() => {
    if (!billing || trackedOverview.current) return;
    trackedOverview.current = true;
    trackLifecycleEvent('billing_overview_view', { page: 'profile' });
  }, [billing]);

  const entitlement = billing?.entitlement;
  return (
    <ProtectedRoute>
      <main className="account-page">
        <header className="account-page__header">
          <div><span>Account</span><h1>PROFILE & BILLING</h1><p>Manage your identity and review commissioner payments.</p></div>
          <button onClick={logout}>Logout</button>
        </header>

        <section className="account-identity" aria-labelledby="account-identity-title">
          <div><span>Signed in as</span><h2 id="account-identity-title">{user?.email}</h2></div>
          <a href="mailto:support@runmypool.net">Account support</a>
        </section>

        <section className="billing-overview" aria-labelledby="billing-overview-title">
          <div className="billing-overview__heading">
            <div><span>{season} season</span><h2 id="billing-overview-title">Commissioner Billing</h2></div>
            <Link href="/pricing">{entitlement ? 'View upgrade options' : 'View plans'}</Link>
          </div>

          {billingError ? (
            <div className="workspace-alert workspace-alert--error">{billingError} <a href="mailto:support@runmypool.net">Contact billing support</a>.</div>
          ) : !billing ? (
            <p className="billing-overview__state">Loading your billing details…</p>
          ) : (
            <>
              <div className="billing-plan">
                <div><span>Current plan</span><strong>{entitlement ? PLAN_LABELS[entitlement.plan] || entitlement.plan : 'Free'}</strong></div>
                <div><span>Status</span><strong>{entitlement?.status === 'active' ? 'Active' : 'No paid plan'}</strong></div>
                <div><span>Entry capacity</span><strong>{entitlement?.unlimited_entries ? 'Unlimited' : entitlement?.included_entries ?? 10}</strong></div>
                <div><span>Pool capacity</span><strong>{entitlement?.max_pools ?? (entitlement?.unlimited_entries ? 'Unlimited' : 1)}</strong></div>
              </div>

              <div className="billing-history">
                <h3>Payment history</h3>
                {billing.orders.length ? (
                  <div className="billing-history__table" role="table" aria-label="Payment history">
                    <div className="billing-history__row billing-history__row--head" role="row">
                      <span role="columnheader">Date</span><span role="columnheader">Plan</span><span role="columnheader">Status</span><span role="columnheader">Amount</span>
                    </div>
                    {billing.orders.map((order) => (
                      <div className="billing-history__row" role="row" key={order.id}>
                        <span role="cell">{formatDate(order.paid_at || order.created_at)}</span>
                        <span role="cell">{PLAN_LABELS[order.plan] || order.plan}</span>
                        <span role="cell" className={`is-${order.status}`}>{order.status}</span>
                        <span role="cell">{formatMoney(order.amount_total, order.currency)}</span>
                      </div>
                    ))}
                  </div>
                ) : <p className="billing-overview__state">No payments for this season. Members always participate free.</p>}
              </div>
            </>
          )}
        </section>
      </main>
    </ProtectedRoute>
  );
}
