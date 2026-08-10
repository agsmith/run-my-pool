export function getPickAvailability(picks = [], week) {
  const currentPick = picks.find((pick) => Number(pick.week) === Number(week)) || null;
  const usedInOtherWeeks = new Set(
    picks
      .filter((pick) => Number(pick.week) !== Number(week))
      .map((pick) => pick.team)
  );

  return { currentPick, usedInOtherWeeks };
}
