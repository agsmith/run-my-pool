import { getAuditUsername } from './auditDisplay';
import { formatAuditTimestamp } from './auditTime';

const csvCell = (value) => {
  let text = value == null ? '' : String(value);
  if (/^[=+\-@]/.test(text)) text = `'${text}`;
  return `"${text.replace(/"/g, '""')}"`;
};

const parseDetails = (details) => {
  if (!details) return {};
  try { return JSON.parse(details); } catch { return { description: details }; }
};

export function buildAuditCsv(logs) {
  const columns = ['Timestamp (Eastern Time)', 'Action', 'Username', 'User ID', 'Description', 'Entry', 'Week', 'Old Team', 'New Team', 'Details'];
  const rows = logs.map((log) => {
    const details = parseDetails(log.details);
    const data = details.additional_data || {};
    const context = data.changes?.context || data;
    const teamChange = data.changes?.team || {};
    return [
      formatAuditTimestamp(log.created_at, ''),
      log.action || '',
      getAuditUsername(log, details),
      log.user_id || '',
      details.description || '',
      context.entry_name || '',
      context.week || '',
      context.old_team_name || data.changes?.old_team_name || teamChange.old || '',
      context.new_team_name || data.changes?.new_team_name || teamChange.new || '',
      log.details || '',
    ];
  });
  return [columns, ...rows].map((row) => row.map(csvCell).join(',')).join('\r\n');
}

export function downloadAuditCsv(logs, filename) {
  const blob = new Blob([`\uFEFF${buildAuditCsv(logs)}`], { type: 'text/csv;charset=utf-8' });
  const url = URL.createObjectURL(blob);
  const link = document.createElement('a');
  link.href = url;
  link.download = filename;
  document.body.appendChild(link);
  link.click();
  link.remove();
  URL.revokeObjectURL(url);
}
