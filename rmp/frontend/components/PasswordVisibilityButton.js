export default function PasswordVisibilityButton({ visible, onToggle, fieldName = 'password' }) {
  return (
    <button
      type="button"
      className="password-visibility-toggle"
      onClick={onToggle}
      aria-label={`${visible ? 'Hide' : 'Show'} ${fieldName}`}
      aria-pressed={visible}
    >
      <svg viewBox="0 0 24 24" aria-hidden="true" focusable="false">
        <path d="M2.25 12s3.5-6 9.75-6 9.75 6 9.75 6-3.5 6-9.75 6S2.25 12 2.25 12Z" />
        <circle cx="12" cy="12" r="3" />
        {!visible && <path d="m4 4 16 16" />}
      </svg>
    </button>
  );
}
