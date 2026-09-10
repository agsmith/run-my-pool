export type Team = { id: number; abbrv: string; name: string; logo?: string };
export type Game = {
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
  team: string;
  team_name: string;
  count: number;
  entries: { entry_id: string; entry_name: string }[];
};
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
