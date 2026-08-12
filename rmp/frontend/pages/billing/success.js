import { useEffect, useState } from 'react';
import Link from 'next/link';
import { useRouter } from 'next/router';
import ProtectedRoute from '../../components/ProtectedRoute';

export default function BillingSuccess() {
  const router = useRouter();
  const [order, setOrder] = useState(null);
  const [error, setError] = useState('');

  useEffect(() => {
    if (!router.isReady || typeof router.query.session_id !== 'string') return undefined;
    let cancelled = false;
    let timer;
    let attempts = 0;
    const load = async () => {
      attempts += 1;
      try {
        const token = localStorage.getItem('access_token');
        const response = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/billing/session/${encodeURIComponent(router.query.session_id)}`, {
          headers: { Authorization: `Bearer ${token}` },
          credentials: 'include',
        });
        if (!response.ok) throw new Error('Unable to confirm this payment.');
        const nextOrder = await response.json();
        if (cancelled) return;
        setOrder(nextOrder);
        if (nextOrder.status === 'pending' && attempts < 8) timer = window.setTimeout(load, 1500);
      } catch (err) {
        if (!cancelled) setError(err.message);
      }
    };
    load();
    return () => { cancelled = true; if (timer) window.clearTimeout(timer); };
  }, [router.isReady, router.query.session_id]);

  const paid = order?.status === 'paid';
  return <ProtectedRoute><main className="billing-result-page">
    <section className="billing-result-card">
      <p className="rmp-eyebrow"><span /> SECURE CHECKOUT</p>
      <h1>{paid ? 'PAYMENT CONFIRMED' : 'CONFIRMING PAYMENT'}</h1>
      {error ? <div className="workspace-alert workspace-alert--error">{error}</div> : paid ? <>
        <p>Your <strong>{order.plan.replace('-', ' ')}</strong> commissioner plan is active for the {order.season} season.</p>
        <div className="billing-result-amount">{order.amount_total != null ? new Intl.NumberFormat('en-US', { style: 'currency', currency: (order.currency || 'usd').toUpperCase() }).format(order.amount_total / 100) : 'Paid'}</div>
      </> : <p>Stripe accepted your checkout. We’re waiting for the verified payment notification before activating access.</p>}
      <div className="billing-result-actions"><Link href="/dashboard">Go to dashboard</Link><Link href="/pricing">View plans</Link></div>
      <p>Questions about your payment? <a href="mailto:support@runmypool.net">Contact billing support</a>.</p>
    </section>
  </main></ProtectedRoute>;
}
