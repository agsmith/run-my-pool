import { getPickAvailability } from '../utils/pickAvailability';

describe('getPickAvailability', () => {
  const picks = [
    { week: 1, team: 'BUF' },
    { week: 2, team: 'KC' },
    { week: 3, team: 'PHI' },
  ];

  it('keeps teams from other weeks unavailable', () => {
    const { usedInOtherWeeks, usedWeekByTeam } = getPickAvailability(picks, 2);
    expect([...usedInOtherWeeks]).toEqual(['BUF', 'PHI']);
    expect(usedWeekByTeam.get('BUF')).toBe(1);
    expect(usedWeekByTeam.get('PHI')).toBe(3);
  });

  it('separates the current saved pick from previously used teams', () => {
    const { currentPick, usedInOtherWeeks } = getPickAvailability(picks, 2);
    expect(currentPick.team).toBe('KC');
    expect(usedInOtherWeeks.has('KC')).toBe(false);
  });

  it('handles a week without a saved pick', () => {
    const { currentPick, usedInOtherWeeks } = getPickAvailability(picks, 4);
    expect(currentPick).toBeNull();
    expect(usedInOtherWeeks.size).toBe(3);
  });
});
