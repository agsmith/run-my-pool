import { useMemo, useState } from 'react';

export default function PoolLaunchChecklist({ pool, onClose, onNavigate, onInviteCopied, onSendInvite }) {
  const [completed, setCompleted] = useState(() => new Set(['created']));
  const [copyStatus, setCopyStatus] = useState('');
  const [inviteEmail, setInviteEmail] = useState('');
  const [emailStatus, setEmailStatus] = useState('');
  const [sendingEmail, setSendingEmail] = useState(false);
  const inviteUrl = useMemo(
    () => (typeof window === 'undefined' ? '' : `${window.location.origin}/leagues?invite=${encodeURIComponent(pool.id)}`),
    [pool.id],
  );

  const completeAndNavigate = (step, destination) => {
    setCompleted((current) => new Set([...current, step]));
    onNavigate(destination);
  };

  const copyInvite = async () => {
    try {
      await navigator.clipboard.writeText(inviteUrl);
      setCompleted((current) => new Set([...current, 'invite']));
      setCopyStatus(pool.is_private
        ? 'Invite link copied. Send the pool join code separately.'
        : 'Invite link copied. Send it to your players.');
      onInviteCopied?.();
    } catch {
      setCopyStatus('Automatic copy failed. Select and copy the invitation link.');
    }
  };

  const sendInvite = async (event) => {
    event.preventDefault();
    setSendingEmail(true);
    setEmailStatus('');
    try {
      await onSendInvite(inviteEmail.trim());
      setCompleted((current) => new Set([...current, 'invite']));
      setEmailStatus(pool.is_private
        ? 'Invitation sent. Send the private join code separately.'
        : 'Invitation sent.');
      setInviteEmail('');
    } catch (error) {
      setEmailStatus(error.message || 'Unable to send the invitation.');
    } finally {
      setSendingEmail(false);
    }
  };

  return (
    <section className="pool-launch" aria-label="Pool launch checklist">
      <div className="pool-launch__header">
        <div><span>New pool setup</span><h2>GET {pool.name.toUpperCase()} READY</h2><p>{completed.size} of 4 launch steps complete</p></div>
        <button type="button" onClick={onClose} aria-label="Close launch checklist">×</button>
      </div>
      <ol>
        <li className="is-complete"><span>✓</span><div><strong>Pool created</strong><small>Your format, access, and weekly deadline are saved.</small></div></li>
        <li className={completed.has('settings') ? 'is-complete' : ''}><span>{completed.has('settings') ? '✓' : '2'}</span><div><strong>Review commissioner settings</strong><small>Confirm rules, access, and the join code before inviting players.</small><button type="button" onClick={() => completeAndNavigate('settings', `/admin/league/${pool.id}`)}>Review settings</button></div></li>
        <li className={completed.has('invite') ? 'is-complete' : ''}><span>{completed.has('invite') ? '✓' : '3'}</span><div><strong>Invite your players</strong><small>{pool.is_private ? 'Players will need both this link and your pool join code.' : 'Anyone with this link can find and join your public pool.'}</small><div className="pool-launch__invite"><input aria-label="Pool invitation link" value={inviteUrl} readOnly /><button type="button" onClick={copyInvite}>Copy invite link</button></div>{copyStatus && <small role="status">{copyStatus}</small>}<form className="pool-launch__email" onSubmit={sendInvite}><label htmlFor={`pool-invite-email-${pool.id}`}>Or send by email</label><div><input id={`pool-invite-email-${pool.id}`} type="email" value={inviteEmail} onChange={(event) => setInviteEmail(event.target.value)} placeholder="player@example.com" required /><button type="submit" disabled={sendingEmail}>{sendingEmail ? 'Sending…' : 'Send invite'}</button></div></form>{emailStatus && <small role="status">{emailStatus}</small>}</div></li>
        <li className={completed.has('entry') ? 'is-complete' : ''}><span>{completed.has('entry') ? '✓' : '4'}</span><div><strong>{pool.pool_type === 'pickem' ? 'Open your Pick ’Em board' : pool.pool_type === 'squares' ? 'Open your Squares board' : 'Create your first entry'}</strong><small>Experience the same starting point your players will use.</small><button type="button" onClick={() => completeAndNavigate('entry', pool.pool_type === 'pickem' ? `/pool/${pool.id}/pickem` : pool.pool_type === 'squares' ? `/pool/${pool.id}/squares` : `/pool/${pool.id}/entries`)}>{pool.pool_type === 'pickem' ? 'Open Pick ’Em board' : pool.pool_type === 'squares' ? 'Open Squares board' : 'Open My Entries'}</button></div></li>
      </ol>
      <button type="button" className="pool-launch__later" onClick={onClose}>Finish setup later</button>
    </section>
  );
}
