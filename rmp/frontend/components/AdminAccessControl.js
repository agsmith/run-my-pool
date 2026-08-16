import { useState } from 'react';

export default function AdminAccessControl({ poolId, onChanged }) {
  const [email, setEmail] = useState('');
  const [message, setMessage] = useState('');
  const [saving, setSaving] = useState(false);

  const updateAccess = async (grant) => {
    const normalizedEmail = email.trim();
    if (!normalizedEmail) {
      setMessage('Enter the pool member’s email address.');
      return;
    }
    setSaving(true);
    setMessage('');
    try {
      const token = localStorage.getItem('access_token');
      const url = `${process.env.NEXT_PUBLIC_API_URL}/admin/pools/${poolId}/admins${grant ? '' : `?email=${encodeURIComponent(normalizedEmail)}`}`;
      const response = await fetch(url, {
        method: grant ? 'PUT' : 'DELETE',
        headers: {
          Authorization: `Bearer ${token}`,
          ...(grant ? { 'Content-Type': 'application/json' } : {}),
        },
        ...(grant ? { body: JSON.stringify({ email: normalizedEmail }) } : {}),
      });
      const data = await response.json().catch(() => ({}));
      if (!response.ok) throw new Error(data.detail || 'Unable to update administrator access');
      if (!data.changed) {
        setMessage(grant ? `${data.email} is already a pool admin.` : `${data.email} is not a pool admin.`);
      } else {
        setMessage(grant ? `Pool admin access granted to ${data.email}.` : `Pool admin access revoked from ${data.email}.`);
      }
      if (onChanged) await onChanged();
    } catch (error) {
      setMessage(error.message || 'Unable to update administrator access');
    } finally {
      setSaving(false);
    }
  };

  return <section className="admin-access-control" aria-labelledby="admin-access-control-title">
    <span>Owner controls</span>
    <h4 id="admin-access-control-title">Pool administrator access</h4>
    <p>Pool admins can manage users, entries, locks, and audit records for this pool. Only the pool owner can grant or revoke this access.</p>
    <label htmlFor="league-admin-email">Member email</label>
    <input id="league-admin-email" type="email" value={email} onChange={(event) => setEmail(event.target.value)} placeholder="member@example.com" />
    <div className="admin-access-control__actions">
      <button type="button" disabled={saving} onClick={() => updateAccess(true)}>{saving ? 'Saving…' : 'Grant admin access'}</button>
      <button type="button" className="is-secondary" disabled={saving} onClick={() => updateAccess(false)}>Revoke admin access</button>
    </div>
    {message && <p className="admin-access-control__message" role="status">{message}</p>}
  </section>;
}
