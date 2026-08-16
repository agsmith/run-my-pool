import Head from 'next/head';

const SITE_URL = 'https://runmypool.net';
const DEFAULT_IMAGE = `${SITE_URL}/icons/icon-512x512.png`;

export default function Seo({
  title,
  description,
  path = '/',
  noIndex = false,
  image = DEFAULT_IMAGE,
  type = 'website',
  structuredData,
}) {
  const canonical = `${SITE_URL}${path === '/' ? '' : path}`;
  const fullTitle = title === 'Run My Pool' ? title : `${title} | Run My Pool`;

  return (
    <Head>
      <title>{fullTitle}</title>
      {description && <meta name="description" content={description} key="description" />}
      <meta name="robots" content={noIndex ? 'noindex, nofollow' : 'index, follow, max-image-preview:large'} key="robots" />
      {!noIndex && <link rel="canonical" href={canonical} key="canonical" />}

      <meta property="og:type" content={type} key="og:type" />
      <meta property="og:site_name" content="Run My Pool" key="og:site_name" />
      <meta property="og:locale" content="en_US" key="og:locale" />
      <meta property="og:title" content={fullTitle} key="og:title" />
      {description && <meta property="og:description" content={description} key="og:description" />}
      <meta property="og:url" content={canonical} key="og:url" />
      <meta property="og:image" content={image} key="og:image" />
      <meta property="og:image:width" content="512" key="og:image:width" />
      <meta property="og:image:height" content="512" key="og:image:height" />
      <meta property="og:image:alt" content="Run My Pool football pick manager" key="og:image:alt" />

      <meta name="twitter:card" content="summary" key="twitter:card" />
      <meta name="twitter:title" content={fullTitle} key="twitter:title" />
      {description && <meta name="twitter:description" content={description} key="twitter:description" />}
      <meta name="twitter:image" content={image} key="twitter:image" />

      {structuredData && (
        <script type="application/ld+json" dangerouslySetInnerHTML={{ __html: JSON.stringify(structuredData) }} />
      )}
    </Head>
  );
}

export { DEFAULT_IMAGE, SITE_URL };
