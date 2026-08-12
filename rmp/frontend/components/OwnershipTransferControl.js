import { useState } from 'react';

export default function OwnershipTransferControl({ poolId, poolName, onTransferred }) {
  const [email, setEmail] = useState('');
  const [confirmation, setConfirmation] = useState('');
  const [message, setMessage] = useState('');
  const [saving, setSaving] = useState(false);
  const confirmed = Boolean(email.trim()) && confirmation === poolName;

  const transferOwnership = async () => {
    if (!confirmed) {
      setMessage(`Enter the member email and type “${poolName}” exactly to confirm.`);
      return;
    }
    setSaving(true);
    setMessage('');
    try {
      const token = localStorage.getItem('access_token');
      const response = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/admin/pools/${poolId}/owner`, {
        method: 'PUT',
        headers: { Authorization: `Bearer ${token}`, 'Content-Type': 'application/json' },
        body: JSON.stringify({ email: email.trim() }),
      });
      const data = await response.json().catch(() => ({}));
      if (!response.ok) throw new Error(data.detail || 'Unable to transfer pool ownership');
      setMessage(`Ownership transferred to ${data.owner_email}. You remain a pool admin.`);
      setConfirmation('');
      if (onTransferred) await onTransferred(data);
    } catch (error) {
      setMessage(error.message || 'Unable to transfer pool ownership');
    } finally {
      setSaving(false);
    }
  };

  return <section className="ownership-transfer-control" aria-labelledby="ownership-transfer-title">
    <span>High-impact action</span>
    <h4 id="ownership-transfer-title">Transfer pool ownership</h4>
    <p>The new owner receives sole ownership authority. Your account remains a Pool Admin after the transfer.</p>
    <div className="ownership-transfer-control__fields">
      <div><label htmlFor="new-owner-email">New owner email</label><input id="new-owner-email" type="email" value={email} onChange={(event) => setEmail(event.target.value)} placeholder="member@example.com" /></div>
      <div><label htmlFor="ownership-confirmation">Type {poolName} to confirm</label><input id="ownership-confirmation" value={confirmation} onChange={(event) => setConfirmation(event.target.value)} autoComplete="off" /></div>
    </div>
    <button type="button" disabled={saving || !confirmed} onClick={transferOwnership}>{saving ? 'Transferring…' : 'Transfer ownership'}</button>
    {message && <p className="ownership-transfer-control__message" role="status">{message}</p>}
  </section>;
}
