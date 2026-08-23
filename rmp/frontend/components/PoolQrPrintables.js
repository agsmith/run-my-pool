import { useEffect, useMemo, useState } from 'react';
import { createPoolPrintable, loadPrintableLogo, PRINT_FORMATS } from '../utils/poolQrPrintables';

export default function PoolQrPrintables({ pool }) {
  const [format, setFormat] = useState('letter');
  const [logo, setLogo] = useState(null);
  const [joinCode, setJoinCode] = useState('');
  const [joinCodeMessage, setJoinCodeMessage] = useState('');
  const [message, setMessage] = useState('');
  const [busyAction, setBusyAction] = useState('');
  const inviteUrl = useMemo(() => (
    typeof window === 'undefined' ? '' : `${window.location.origin}/leagues?invite=${encodeURIComponent(pool.id)}`
  ), [pool.id]);

  useEffect(() => {
    let cancelled = false;
    if (!pool.is_private) {
      setJoinCode('');
      setJoinCodeMessage('Public pool - no join code required.');
      return () => { cancelled = true; };
    }
    const loadJoinCode = async () => {
      setJoinCodeMessage('Loading the current join code...');
      try {
        const response = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/pools/${pool.id}/join-password`, {
          headers: { Authorization: `Bearer ${localStorage.getItem('access_token')}` },
          cache: 'no-store',
        });
        const data = await response.json().catch(() => ({}));
        if (!response.ok) throw new Error(data.detail || 'Unable to load the current join code.');
        if (!cancelled) {
          setJoinCode(data.password || '');
          setJoinCodeMessage(data.password ? 'The current join code will be printed.' : 'Enter the join code you want printed.');
        }
      } catch (error) {
        if (!cancelled) setJoinCodeMessage(`${error.message || 'Unable to load the current join code.'} Enter it manually below.`);
      }
    };
    loadJoinCode();
    return () => { cancelled = true; };
  }, [pool.id, pool.is_private]);

  const chooseLogo = async (event) => {
    setMessage('');
    try {
      const nextLogo = await loadPrintableLogo(event.target.files?.[0]);
      if (nextLogo) {
        setLogo(nextLogo);
        setMessage(`${nextLogo.name} will appear on the printable.`);
      }
    } catch (error) {
      setLogo(null);
      setMessage(error.message || 'Unable to use that logo.');
    } finally {
      event.target.value = '';
    }
  };

  const build = async () => createPoolPrintable({
    format,
    poolName: pool.name,
    poolId: pool.id,
    isPrivate: pool.is_private,
    joinCode: joinCode.trim(),
    logo,
    origin: window.location.origin,
  });

  const download = async () => {
    setBusyAction('download');
    setMessage('');
    try {
      const { doc, filename } = await build();
      doc.save(filename);
      setMessage(`${PRINT_FORMATS[format].label} PDF downloaded.`);
    } catch (error) {
      setMessage(error.message || 'Unable to create the PDF.');
    } finally {
      setBusyAction('');
    }
  };

  const print = async () => {
    const printWindow = window.open('', '_blank');
    if (!printWindow) {
      setMessage('Allow pop-ups to open the printable PDF.');
      return;
    }
    setBusyAction('print');
    setMessage('');
    try {
      printWindow.document.write('<title>Preparing pool printable...</title><p>Preparing print-ready PDF...</p>');
      const { doc } = await build();
      const objectUrl = URL.createObjectURL(doc.output('blob'));
      printWindow.location.replace(objectUrl);
      setMessage('Printable opened. Use your browser PDF viewer to print at 100% or Actual Size.');
      window.setTimeout(() => URL.revokeObjectURL(objectUrl), 60000);
    } catch (error) {
      printWindow.close();
      setMessage(error.message || 'Unable to open the printable.');
    } finally {
      setBusyAction('');
    }
  };

  return (
    <section className="pool-qr-printables" aria-labelledby="pool-qr-printables-title">
      <div className="pool-qr-printables__heading">
        <div>
          <span>Promote your pool</span>
          <h4 id="pool-qr-printables-title">QR Join Printables</h4>
          <p>Give players a scannable link to the correct pool. Add your logo locally, choose a print size, then download or print the PDF.</p>
        </div>
        <div className="pool-qr-printables__qr" aria-hidden="true">QR</div>
      </div>

      <div className="pool-qr-printables__url">
        <span>QR destination</span>
        <strong>{inviteUrl}</strong>
        {pool.is_private && <small>The join code shown below will be printed next to the QR. It is not embedded in the QR itself.</small>}
      </div>

      <div className="pool-qr-printables__controls">
        <fieldset>
          <legend>1. Choose a print size</legend>
          <div className="pool-qr-printables__formats">
            {Object.entries(PRINT_FORMATS).map(([id, option]) => (
              <label key={id} className={format === id ? 'is-selected' : ''}>
                <input type="radio" name="pool-print-format" value={id} checked={format === id} onChange={() => setFormat(id)} />
                <span><strong>{option.label}</strong><small>{option.description}</small></span>
              </label>
            ))}
          </div>
        </fieldset>

        <div className="pool-qr-printables__logo">
          <label htmlFor="pool-print-logo">2. Add a logo <small>Optional</small></label>
          <input id="pool-print-logo" type="file" accept="image/png,image/jpeg,image/webp" onChange={chooseLogo} />
          <small>PNG, JPG, or WebP up to 5 MB. The image stays in this browser and is not uploaded to Run My Pool.</small>
          {logo && <div className="pool-qr-printables__logo-preview"><img src={logo.dataUrl} alt="Uploaded printable logo preview" /><span>{logo.name}</span><button type="button" onClick={() => { setLogo(null); setMessage('Logo removed.'); }}>Remove</button></div>}
        </div>
      </div>

      <div className="pool-qr-printables__join-code">
        <label htmlFor="pool-print-join-code">3. Join code on printable</label>
        <input
          id="pool-print-join-code"
          type="text"
          value={pool.is_private ? joinCode : 'No join code required'}
          disabled={!pool.is_private}
          maxLength={72}
          autoComplete="off"
          data-1p-ignore="true"
          data-lpignore="true"
          onChange={(event) => setJoinCode(event.target.value)}
          placeholder="Enter the pool join code"
        />
        <small>{joinCodeMessage} Anyone holding a printed copy can read this code.</small>
      </div>

      <div className="pool-qr-printables__actions">
        <button type="button" onClick={download} disabled={Boolean(busyAction)}>{busyAction === 'download' ? 'Creating PDF...' : 'Download PDF'}</button>
        <button type="button" className="is-secondary" onClick={print} disabled={Boolean(busyAction)}>{busyAction === 'print' ? 'Preparing...' : 'Open to print'}</button>
        <small>For accurate sizing, print at 100% or select Actual Size.</small>
      </div>
      {message && <p className="pool-qr-printables__message" role="status">{message}</p>}
    </section>
  );
}
