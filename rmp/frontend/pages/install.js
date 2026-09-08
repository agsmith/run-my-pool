import Image from 'next/image';
import { useEffect, useState } from 'react';
import Seo from '../components/Seo';

const steps = {
  ios: [
    'Open Safari (the blue compass icon). Tap the address bar, type runmypool.net, and tap Go.',
    'Find Share: a square with an arrow pointing up out of it. Look in the toolbar at the bottom or top of Safari. If it is hidden, tap the More button (•••) beside the address bar, then Share.',
    'In the Share menu that opens, swipe up to scroll past the contacts and app icons. Tap Add to Home Screen in the list of actions.',
    'Keep the name Run My Pool. If you see Open as Web App, leave it switched on. Tap Add to finish.',
    'Return to your Home Screen (where your app icons are). Swipe between pages if needed, then tap the Run My Pool icon. Sign in with your existing account if asked.',
  ],
  android: [
    'Open Google Chrome (the red, yellow, green, and blue circle). Tap the address bar, type runmypool.net, and tap Go or the arrow on your keyboard.',
    'Tap the More menu: three dots stacked vertically (⋮), usually at the top right beside the address bar.',
    'Tap Add to home screen, then Install. Some versions show Install app directly in the menu.',
    'In the confirmation box, tap Install and follow any prompts. If Chrome offers Create shortcut instead, you can use it for quick access; confirm Add when asked.',
    'Return to your Home Screen and tap Run My Pool. If the icon is missing, check your list of all apps. Sign in with your existing account if asked.',
  ],
  desktop: [
    'Open runmypool.net in Chrome or Microsoft Edge.',
    'Click the install icon at the right side of the address bar.',
    'Click Install to add Run My Pool as a desktop app.',
  ],
};

function InstallSteps({ number, title, subtitle, items, children }) {
  return (
    <article className="pwa-guide__card">
      <span className="pwa-guide__number">{number}</span>
      <p className="pwa-guide__kicker">{subtitle}</p>
      <h2>{title}</h2>
      {children}
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
      <Seo
        title="Install the Run My Pool App"
        path="/install"
        description="Install Run My Pool on iPhone, Android, or desktop for fast home-screen access to picks and standings."
      />
      <main className="product-main pwa-guide__main">
        <section className="pwa-guide__hero">
          <div>
            <p className="workspace-hero__eyebrow">YOUR POOL, ONE TAP AWAY</p>
            <h1>INSTALL<br /><em>RUN MY POOL.</em></h1>
            <p>Add Run My Pool to your phone’s Home Screen so you can open it by tapping an icon, just like your other apps. You install it through your web browser—no App Store or Google Play download is needed.</p>
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
          <InstallSteps number="01" subtitle="APPLE" title="iPhone & iPad" items={steps.ios}>
            <figure style={{ margin: '0 0 24px', display: 'flex', alignItems: 'center', gap: 12 }}>
              <svg width="40" height="48" viewBox="0 0 32 40" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true" focusable="false" style={{ flexShrink: 0, color: 'var(--bn-cyan)' }}>
                <path d="M16 25V3m-7 7 7-7 7 7M10 16H4v20h24V16h-6" />
              </svg>
              <figcaption><strong>This is the Share icon.</strong><br />A square with an arrow pointing up.</figcaption>
            </figure>
          </InstallSteps>
          <InstallSteps number="02" subtitle="GOOGLE" title="Android" items={steps.android} />
          <InstallSteps number="03" subtitle="COMPUTER" title="Desktop" items={steps.desktop} />
        </section>

        <aside className="pwa-guide__note">
          <strong>Opened a link in another app?</strong>
          <p>If you are viewing this inside Facebook, Instagram, Gmail, or another app, open Safari on iPhone or Chrome on Android yourself and type runmypool.net into the address bar. Then follow the steps above.</p>
        </aside>
        <aside className="pwa-guide__note">
          <strong>Can&apos;t find the option?</strong>
          <p>On iPhone or iPad, scroll to the bottom of the Share menu and tap Edit Actions if Add to Home Screen is missing, then add it. On Android, check for both Install app and Add to home screen. If neither appears, check whether Run My Pool is already in your apps and try updating Chrome. You can also keep using runmypool.net in your browser.</p>
        </aside>
        <aside className="pwa-guide__note">
          <strong>Already have an account?</strong>
          <p>Use the same login after installing. Your pools and picks stay with your account; there is no need to create a new one. Need more help? See the <a href="https://support.apple.com/guide/iphone/iphea86e5236/ios">Apple installation guide</a> or <a href="https://support.google.com/chrome/answer/9658361?co=GENIE.Platform%3DAndroid&amp;hl=en">Google Chrome installation guide</a>.</p>
        </aside>
      </main>
    </div>
  );
}
