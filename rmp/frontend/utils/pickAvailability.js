export function getPickAvailability(picks = [], week) {
  const currentPick = picks.find((pick) => Number(pick.week) === Number(week)) || null;
  const otherWeekPicks = picks.filter((pick) => Number(pick.week) !== Number(week));
  const usedInOtherWeeks = new Set(
    otherWeekPicks.map((pick) => pick.team)
  );
  const usedWeekByTeam = new Map(otherWeekPicks.map((pick) => [pick.team, Number(pick.week)]));

  return { currentPick, usedInOtherWeeks, usedWeekByTeam };
}
