export type Team = { id: number; abbrv: string; name: string; logo?: string };
export type GameLine = { spread: number | null; favorite_team_id: number | null };
export type Game = {
  official_line?: GameLine | null;
  live_line?: GameLine | null;
  game_id: number;
  start_time: string;
  home_team: Team;
  away_team: Team;
};
export type Pick = {
  id: string;
  entry_id: string;
  week: number;
  team: string;
  locked: boolean;
  result?: string;
};
export type Entry = { id: string; name: string; alive: boolean };
export type WeekLock = { locked: boolean; deadline: string | null };
export type Breakdown = {
  result?: string | null;
  team: string;
  team_name: string;
  team_abbrv?: string;
  count: number;
  entries: { entry_id: string; entry_name: string }[];
};
export type PickEmWeeklyStanding = {
  rank: number;
  entry_id: string;
  entry_name: string;
  user_display_name: string;
  points: number;
  completed_picks: number;
  predicted_total?: number | null;
  actual_total?: number | null;
  tiebreak_difference?: number | null;
};

/**
 * Keep an entry on the board through the week in which it was eliminated.
 * Once a loss is settled, later weeks should not show that entry as if it
 * still needs a pick. Entries without a settled loss remain visible.
 */
export function visibleEntriesForWeek(
  entries: Entry[],
  picks: Record<string, Pick[]>,
  week: number,
) {
  return entries.filter((entry) => {
    const lossWeeks = (picks[entry.id] || [])
      .filter((pick) => pick.result?.toLowerCase() === "loss")
      .map((pick) => pick.week);
    const eliminatedWeek = lossWeeks.length ? Math.min(...lossWeeks) : null;
    return eliminatedWeek === null || week <= eliminatedWeek;
  });
}

export function started(game: Game, now: number) {
  return Date.parse(game.start_time) <= now;
}
export function pickLocked(
  pick: Pick | undefined,
  games: Game[],
  lock: WeekLock | undefined,
  now: number,
) {
  return Boolean(
    lock?.locked ||
      (lock?.deadline && Date.parse(lock.deadline) <= now) ||
      pick?.locked ||
      (pick &&
        games.some(
          (game) =>
            [game.home_team.abbrv, game.away_team.abbrv].includes(pick.team) &&
            started(game, now),
        )),
  );
}
export function unavailable(
  team: string,
  week: number,
  picks: Pick[],
  games: Game[],
  lock: WeekLock | undefined,
  now: number,
) {
  if (
    pickLocked(
      picks.find((p) => p.week === week),
      games,
      lock,
      now,
    )
  )
    return "Locked — this pick can no longer be changed";
  const used = picks.find((p) => p.week !== week && p.team === team);
  if (used) return `Used in week ${used.week}`;
  const game = games.find((g) =>
    [g.home_team.abbrv, g.away_team.abbrv].includes(team),
  );
  if (!game) return "Not scheduled";
  if (started(game, now)) return "Locked — game started";
  return null;
}
