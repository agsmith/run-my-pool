export function getAuditUsername(log, details) {
  const data = details?.additional_data || {};
  return (
    log?.username ||
    data?.changes?.context?.username ||
    data?.username ||
    (log?.user_id ? 'Unknown user' : 'System')
  );
}
