import Head from 'next/head';
import policy from '../lib/privacyPolicy.json';

export default function PrivacyPage() {
  return <main className="privacy-page">
    <Head><title>Privacy Policy | Run My Pool</title><meta name="description" content="How Run My Pool collects, uses, shares, and protects information on its website and mobile app." /></Head>
    <header><h1>{policy.title}</h1><p>Last updated: {policy.updated}</p><p>{policy.intro}</p></header>
    {policy.sections.map(section => <section key={section.title}><h2>{section.title}</h2>{section.paragraphs.map(paragraph => <p key={paragraph}>{paragraph}</p>)}</section>)}
    <p><a href={`mailto:${policy.contact}`}>Contact Run My Pool about privacy</a></p>
    <style jsx>{`
      .privacy-page { max-width: 800px; margin: 0 auto; padding: 32px 20px 64px; color: #f4f8f5; overflow-wrap: anywhere; }
      h1 { font-size: clamp(2rem, 8vw, 3rem); line-height: 1.15; }
      h2 { font-size: 1.35rem; line-height: 1.35; margin-top: 32px; }
      p { font-size: 1rem; line-height: 1.75; color: #cad5d8; }
      a { color: #b4e9f3; text-decoration: underline; }
    `}</style>
  </main>;
}
