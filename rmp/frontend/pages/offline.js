export default function OfflinePage() {
  return (
    <div style={{
      display: 'flex',
      flexDirection: 'column',
      alignItems: 'center',
      justifyContent: 'center',
      minHeight: '100vh',
      padding: '2rem',
      textAlign: 'center',
      fontFamily: 'system-ui, -apple-system, sans-serif',
    }}>
      <h1 style={{ fontSize: '1.5rem', marginBottom: '1rem', color: '#1a1a1a' }}>
        You&apos;re offline
      </h1>
      <p style={{ color: '#666', maxWidth: '320px', lineHeight: '1.6' }}>
        Check your connection and try again. Your picks are safe &mdash; they&apos;ll sync when you&apos;re back online.
      </p>
      <button
        onClick={() => window.location.reload()}
        style={{
          marginTop: '2rem',
          padding: '0.75rem 1.5rem',
          background: '#667eea',
          color: '#fff',
          border: 'none',
          borderRadius: '8px',
          fontSize: '1rem',
          cursor: 'pointer',
          minHeight: '44px',
        }}
      >
        Try Again
      </button>
    </div>
  )
}
