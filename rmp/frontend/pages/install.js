import Head from 'next/head';
import Image from 'next/image';
import { useEffect, useState } from 'react';

const steps = {
  ios: [
    'Open runmypool.net in Safari.',
    'Tap the Share button at the bottom of the screen.',
    'Scroll down and tap Add to Home Screen.',
    'Tap Add. Run My Pool will appear with your other apps.',
  ],
  android: [
    'Open runmypool.net in Chrome.',
    'Tap the three-dot menu in the top-right corner.',
    'Tap Install app or Add to Home screen.',
    'Confirm Install.',
  ],
  desktop: [
    'Open runmypool.net in Chrome or Microsoft Edge.',
    'Click the install icon at the right side of the address bar.',
    'Click Install to add Run My Pool as a desktop app.',
  ],
};

function InstallSteps({ number, title, subtitle, items }) {
  return (
    <article className="pwa-guide__card">
      <span className="pwa-guide__number">{number}</span>
      <p className="pwa-guide__kicker">{subtitle}</p>
      <h2>{title}</h2>
      <ol>
        {items.map((item) => <li key={item}>{item}</li>)}
      </ol>
    </article>
  );
}

export default function InstallPage() {
  const [installPrompt, setInstallPrompt] = useState(null);
  const [installed, setInstalled] = useState(false);

  useEffect(() => {
    const capturePrompt = (event) => {
      event.preventDefault();
      setInstallPrompt(event);
    };
    const markInstalled = () => {
      setInstalled(true);
      setInstallPrompt(null);
    };

    setInstalled(window.matchMedia('(display-mode: standalone)').matches || window.navigator.standalone === true);
    window.addEventListener('beforeinstallprompt', capturePrompt);
    window.addEventListener('appinstalled', markInstalled);
    return () => {
      window.removeEventListener('beforeinstallprompt', capturePrompt);
      window.removeEventListener('appinstalled', markInstalled);
    };
  }, []);

  const requestInstall = async () => {
    if (!installPrompt) return;
    await installPrompt.prompt();
    const choice = await installPrompt.userChoice;
    if (choice.outcome === 'accepted') setInstallPrompt(null);
  };

  return (
    <div className="product-page pwa-guide">
      <Head>
        <title>Install Run My Pool</title>
        <meta name="description" content="Install Run My Pool on iPhone, Android, or desktop for fast home-screen access." />
      </Head>
      <main className="product-main pwa-guide__main">
        <section className="pwa-guide__hero">
          <div>
            <p className="workspace-hero__eyebrow">YOUR POOL, ONE TAP AWAY</p>
            <h1>INSTALL<br /><em>RUN MY POOL.</em></h1>
            <p>Get an app-like experience with faster access from your home screen—no app store required.</p>
            {installPrompt && !installed && (
              <button className="pwa-guide__install" onClick={requestInstall}>Install now <span>→</span></button>
            )}
            {installed && <p className="pwa-guide__installed"><span>✓</span> Run My Pool is installed on this device.</p>}
          </div>
          <div className="pwa-guide__icon-wrap">
            <Image src="/icons/icon-512x512.png" alt="Run My Pool app icon" width={220} height={220} priority />
            <span>ADD TO HOME SCREEN</span>
          </div>
        </section>

        <section className="pwa-guide__grid" aria-label="Installation instructions">
          <InstallSteps number="01" subtitle="APPLE" title="iPhone & iPad" items={steps.ios} />
          <InstallSteps number="02" subtitle="GOOGLE" title="Android" items={steps.android} />
          <InstallSteps number="03" subtitle="COMPUTER" title="Desktop" items={steps.desktop} />
        </section>

        <aside className="pwa-guide__note">
          <strong>No download button?</strong>
          <p>Your browser may already have Run My Pool installed, or it may require the manual steps above. On iPhone and iPad, installation must be started from Safari&apos;s Share menu.</p>
        </aside>
      </main>
    </div>
  );
}
