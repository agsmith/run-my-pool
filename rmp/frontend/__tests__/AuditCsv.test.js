import { buildAuditCsv } from '../utils/auditCsv';

describe('audit CSV export', () => {
  test('exports stable columns and structured audit context', () => {
    const csv = buildAuditCsv([{
      id: 'audit-1',
      created_at: '2026-09-01T12:00:00Z',
      action: 'UPDATE_PICK',
      username: 'member@example.com',
      user_id: 'user-1',
      details: JSON.stringify({
        description: 'Corrected a pick',
        additional_data: { changes: { context: { entry_name: 'Entry 1', week: 2 }, team: { old: 'BUF', new: 'MIA' } } },
      }),
    }]);

    expect(csv).toContain('"Timestamp (UTC)","Action","Username","User ID"');
    expect(csv).toContain('"Sep 1, 2026, 12:00:00 PM UTC"');
    expect(csv).toContain('"UPDATE_PICK"');
    expect(csv).toContain('"member@example.com"');
    expect(csv).toContain('"Entry 1","2","BUF","MIA"');
  });

  test('neutralizes spreadsheet formulas and escapes quotes', () => {
    const csv = buildAuditCsv([{
      action: '=HYPERLINK("bad")',
      username: '+attacker',
      details: 'plain details',
    }]);

    expect(csv).toContain('"\'=HYPERLINK(""bad"")"');
    expect(csv).toContain('"\'+attacker"');
  });
});
