const BRAND_ASSETS = {
  dark: {
    src: '/brand/promotional/rmp-alt-horizontal-dark.png',
    width: 455,
    height: 125,
  },
  compact: {
    src: '/brand/promotional/rmp-alt-compact-dark.png',
    width: 300,
    height: 100,
  },
  icon: {
    src: '/brand/promotional/rmp-alt-app-icon-framed.png',
    width: 190,
    height: 190,
  },
};

export default function BrandLogo({ alt = '', className = '', iconOnly = false, priority = false, variant = 'dark' }) {
  const asset = iconOnly ? BRAND_ASSETS.icon : BRAND_ASSETS[variant] || BRAND_ASSETS.dark;

  return (
    // These logo crops are already web-sized; a direct image avoids generating
    // a separate optimizer request for every navigation render.
    // eslint-disable-next-line @next/next/no-img-element
    <img
      src={asset.src}
      alt={alt}
      width={asset.width}
      height={asset.height}
      className={`brand-logo ${className}`.trim()}
      fetchPriority={priority ? 'high' : undefined}
      decoding="async"
    />
  );
}
