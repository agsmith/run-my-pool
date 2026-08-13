export default function BrandLogo({ alt = '', className = '', iconOnly = false, priority = false }) {
  return (
    // This logo is already web-sized and transparent; a direct image avoids
    // generating a separate optimizer request for every navigation render.
    // eslint-disable-next-line @next/next/no-img-element
    <img
      src={iconOnly ? '/brand/run-my-pool-mark.png' : '/brand/run-my-pool-wordmark.png'}
      alt={alt}
      width={iconOnly ? 512 : 720}
      height={iconOnly ? 512 : 180}
      className={`brand-logo ${className}`.trim()}
      fetchPriority={priority ? 'high' : undefined}
      decoding="async"
    />
  );
}
