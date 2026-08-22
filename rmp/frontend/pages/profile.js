import { useEffect, useRef, useState } from 'react';
import Link from 'next/link';
import ProtectedRoute from '../components/ProtectedRoute';
import { useAuth } from '../context/AuthContext';
import { trackLifecycleEvent } from '../lib/lifecycleAnalytics';

const PLAN_LABELS = {
  'squares-plus': 'Squares Plus',
  commissioner: 'Commish',
  pro: 'Pro',
  club: 'Club',
  'club-unlimited': 'Club Unlimited',
  'club-entry-block': 'Club +100 entries',
};

const PLAN_PRICES = { 'squares-plus': 10, commissioner: 39, pro: 79, club: 129, 'club-unlimited': 249 };
const PLAN_RANKS = { 'squares-plus': 0.5, commissioner: 1, pro: 2, club: 3, 'club-unlimited': 4 };

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

function formatPlanYearDate(value) {
  if (!value) return '';
  const [year, month, day] = value.split('-').map(Number);
  return new Intl.DateTimeFormat('en-US', { month: 'long', day: 'numeric', year: 'numeric', timeZone: 'UTC' })
    .format(new Date(Date.UTC(year, month - 1, day)));
}

export default function Profile() {
  const { user, logout } = useAuth();
  const [billing, setBilling] = useState(null);
  const [billingError, setBillingError] = useState('');
  const [checkoutError, setCheckoutError] = useState('');
  const [checkoutBusy, setCheckoutBusy] = useState('');
  const [entryBlocks, setEntryBlocks] = useState(1);
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
  const poolsCreated = billing?.pools_created ?? billing?.used_pools ?? 0;
  const currentPlanPrice = PLAN_PRICES[entitlement?.plan] || 0;
  const upgradePlans = Object.keys(PLAN_RANKS).filter(
    (plan) => PLAN_RANKS[plan] > (PLAN_RANKS[entitlement?.plan] || 0)
      && (plan !== 'club-unlimited' || entitlement?.plan === 'club'),
  );
  const hasUnusedPaidPool = entitlement?.status === 'active' && billing?.can_create_pool === true;

  const beginCheckout = async ({ plan, orderType = 'plan', quantity = 1 }) => {
    const busyKey = orderType === 'entry_blocks' ? 'entry-blocks' : plan;
    setCheckoutBusy(busyKey);
    setCheckoutError('');
    try {
      const token = localStorage.getItem('access_token');
      const response = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/billing/checkout-session`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${token}` },
        credentials: 'include',
        body: JSON.stringify({ plan, season, order_type: orderType, quantity }),
      });
      const body = await response.json().catch(() => ({}));
      if (!response.ok) throw new Error(body.detail || 'Unable to start secure checkout.');
      trackLifecycleEvent('checkout_started', { page: 'profile', plan: plan || 'club', source: 'billing' });
      window.location.assign(body.checkout_url);
    } catch (error) {
      setCheckoutError(error.message || 'Unable to start secure checkout.');
      setCheckoutBusy('');
    }
  };
  return (
    <ProtectedRoute>
      <main className="account-page">
        <header className="account-page__header">
          <div><span>Account</span><h1>PROFILE & BILLING</h1><p>Manage your identity and review commissioner payments.</p></div>
          <button onClick={logout}>Logout</button>
        </header>

        <section className="account-identity" aria-labelledby="account-identity-title">
          <div><span>Signed in as</span><h2 id="account-identity-title">{user?.email}</h2></div>
          <Link href="/support">Account support</Link>
        </section>

        <section className="billing-overview" aria-labelledby="billing-overview-title">
          <div className="billing-overview__heading">
            <div><span>{season} plan year</span><h2 id="billing-overview-title">Commissioner Billing</h2></div>
            <Link href="/pricing">{entitlement ? 'View upgrade options' : 'View plans'}</Link>
          </div>

          {billingError ? (
            <div className="workspace-alert workspace-alert--error">{billingError} <Link href="/support">Contact billing support</Link>.</div>
          ) : !billing ? (
            <p className="billing-overview__state">Loading your billing details…</p>
          ) : (
            <>
              <div className="billing-plan">
                <div><span>Current plan</span><strong>{entitlement ? PLAN_LABELS[entitlement.plan] || entitlement.plan : 'Free'}</strong></div>
                <div><span>Status</span><strong>{entitlement?.status === 'active' ? 'Active' : 'No paid plan'}</strong></div>
                <div><span>Entry usage</span><strong>{entitlement?.unlimited_entries ? `${billing.used_entries} / Unlimited` : `${billing.used_entries} / ${entitlement?.included_entries ?? 10}`}</strong></div>
                <div><span>Pool creations</span><strong>{entitlement?.max_pools == null && entitlement?.unlimited_entries ? `${poolsCreated} / Unlimited` : `${poolsCreated} / ${entitlement?.max_pools ?? 1}`}</strong></div>
              </div>
              {billing.plan_year_start && billing.plan_year_end && (
                <p className="billing-overview__state">Plan year: {formatPlanYearDate(billing.plan_year_start)} through {formatPlanYearDate(billing.plan_year_end)}. Deleted or concluded pools still count toward the creation allowance.</p>
              )}

              {hasUnusedPaidPool && (
                <div className="billing-actions" aria-labelledby="create-purchased-pool-title">
                  <h3 id="create-purchased-pool-title">Your purchased pool is ready</h3>
                  <p>Your purchase remains attached to this account if you leave pool setup. Return whenever you are ready.</p>
                  <div className="billing-actions__options">
                    <Link href="/create-pool?source=splash">Create your pool</Link>
                  </div>
                </div>
              )}

              {(upgradePlans.length > 0 || entitlement?.plan === 'club') && (
                <div className="billing-actions" aria-labelledby="billing-actions-title">
                  <h3 id="billing-actions-title">Grow your plan</h3>
                  <p>You pay only the difference for this plan year. Your pools, entries, and picks stay in place.</p>
                  <div className="billing-actions__options">
                    {upgradePlans.map((plan) => (
                      <button
                        type="button"
                        key={plan}
                        disabled={Boolean(checkoutBusy)}
                        onClick={() => beginCheckout({ plan })}
                      >
                        Upgrade to {PLAN_LABELS[plan]} — ${PLAN_PRICES[plan] - currentPlanPrice}
                      </button>
                    ))}
                  </div>
                  {entitlement?.plan === 'club' && (
                    <div className="billing-entry-blocks">
                      <label htmlFor="entry-block-count">Additional 100-entry blocks</label>
                      <select id="entry-block-count" value={entryBlocks} onChange={(event) => setEntryBlocks(Number(event.target.value))}>
                        {[1, 2, 3, 4, 5, 10].map((count) => <option value={count} key={count}>{count} (+{count * 100} entries)</option>)}
                      </select>
                      <button type="button" disabled={Boolean(checkoutBusy)} onClick={() => beginCheckout({ orderType: 'entry_blocks', quantity: entryBlocks })}>
                        Add {entryBlocks * 100} entries — ${entryBlocks * 25}
                      </button>
                    </div>
                  )}
                  {checkoutBusy && <p role="status">Opening secure checkout…</p>}
                  {checkoutError && <div className="workspace-alert workspace-alert--error">{checkoutError}</div>}
                </div>
              )}

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
                        <span role="cell">{order.order_type === 'entry_blocks' ? `${order.quantity} × 100 entries` : PLAN_LABELS[order.plan] || order.plan}</span>
                        <span role="cell" className={`is-${order.status}`}>{order.status}</span>
                        <span role="cell">{formatMoney(order.amount_total, order.currency)}</span>
                      </div>
                    ))}
                  </div>
                ) : <p className="billing-overview__state">No payments for this plan year. Members always participate free.</p>}
              </div>
            </>
          )}
        </section>
      </main>
    </ProtectedRoute>
  );
}
