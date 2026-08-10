import { getAuditUsername } from '../utils/auditDisplay';

describe('getAuditUsername', () => {
  it('uses the API-resolved email for legacy events', () => {
    expect(getAuditUsername(
      { username: 'player@example.com', user_id: 'cc5427ed-e383-46e6-9e61-8fcce9ffb535' },
      { additional_data: {} },
    )).toBe('player@example.com');
  });

  it('supports nested context from pick updates', () => {
    expect(getAuditUsername(
      { user_id: 'cc5427ed-e383-46e6-9e61-8fcce9ffb535' },
      { additional_data: { changes: { context: { username: 'update@example.com' } } } },
    )).toBe('update@example.com');
  });

  it('supports top-level context from pick creation', () => {
    expect(getAuditUsername(
      { user_id: 'cc5427ed-e383-46e6-9e61-8fcce9ffb535' },
      { additional_data: { username: 'create@example.com' } },
    )).toBe('create@example.com');
  });

  it('does not present an unresolved UUID as a username', () => {
    expect(getAuditUsername(
      { user_id: 'cc5427ed-e383-46e6-9e61-8fcce9ffb535' },
      { additional_data: {} },
    )).toBe('Unknown user');
  });

  it('labels events without a user as system events', () => {
    expect(getAuditUsername({ user_id: null }, null)).toBe('System');
  });
});
