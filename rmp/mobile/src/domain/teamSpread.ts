import type { Game, Team } from "./survivor";
export function teamSpread(game: Game, team: Team) {
  const line = game.official_line || game.live_line;
  if (line?.spread == null || !Number.isFinite(Number(line.spread))) return 'Spread unavailable';
  const points = Math.abs(Number(line.spread));
  if (points === 0) return '0';
  if (![game.home_team.id, game.away_team.id].includes(line.favorite_team_id ?? -1)) return 'Spread unavailable';
  return line.favorite_team_id === team.id ? `−${points}` : `+${points}`;
}
