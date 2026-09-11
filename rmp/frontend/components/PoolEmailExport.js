import { useState } from 'react';

export default function PoolEmailExport({ users = [], poolName = 'Pool', disabled = false }) {
  const [message, setMessage] = useState('');
  const emails = [...new Set(users.map((user) => (user.email || '').trim().toLowerCase()).filter(Boolean))].sort();
  const text = emails.join(', ');
  const unavailable = disabled || !emails.length;

  async function copyEmails() {
    try {
      await navigator.clipboard.writeText(text);
      setMessage(`Copied ${emails.length} email addresses.`);
    } catch {
      setMessage('Copy was unavailable. Select and copy the addresses below.');
    }
  }

  function downloadEmails() {
    const url = URL.createObjectURL(new Blob([text + '\n'], { type: 'text/plain;charset=utf-8' }));
    const link = document.createElement('a');
    link.href = url;
    link.download = `${poolName.replace(/[^a-z0-9]+/gi, '-').replace(/^-|-$/g, '') || 'pool'}-emails.txt`;
    document.body.appendChild(link);
    link.click();
    link.remove();
    setTimeout(() => URL.revokeObjectURL(url), 1000);
  }

  return <section className="pool-email-export" aria-label="Pool email export">
    <h4>Group email list</h4>
    <p>All pool users, including those without entries and eliminated players. Each address appears once, regardless of the search below. Paste into your email’s Bcc field to keep addresses private.</p>
    <div className="actions">
      <button type="button" disabled={unavailable} onClick={copyEmails}>Copy all emails</button>
      <button type="button" disabled={unavailable} onClick={downloadEmails}>Download email list (.txt)</button>
      <span>{disabled ? 'Email list unavailable' : `${emails.length} unique email addresses`}</span>
    </div>
    {!unavailable && <details><summary>Select addresses manually</summary><textarea aria-label="All pool email addresses" readOnly value={text} onFocus={(event) => event.target.select()} /></details>}
    <p role="status">{message}</p>
    <style jsx>{`
      .pool-email-export { border: 1px solid #40555a; padding: 16px; margin: 16px 0; }
      h4 { margin: 0 0 8px; }
      p { line-height: 1.5; }
      .actions { display: flex; flex-wrap: wrap; gap: 12px; align-items: center; }
      button { min-height: 44px; padding: 10px 14px; cursor: pointer; }
      button:disabled { opacity: .5; cursor: default; }
      details { margin-top: 12px; }
      summary { cursor: pointer; padding: 8px 0; }
      textarea { box-sizing: border-box; width: 100%; min-height: 110px; margin-top: 8px; padding: 10px; font: inherit; }
      p:empty { display: none; }
    `}</style>
  </section>;
}
