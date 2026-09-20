export function teamSpread(game, team) {
  const line = game.official_line || game.live_line;
  if (line?.spread == null || line.spread === '' || !Number.isFinite(Number(line.spread))) return 'Spread unavailable';
  const points = Math.abs(Number(line.spread));
  if (points === 0) return 'Even · 0';
  if (![game.home_team.id, game.away_team.id].includes(line.favorite_team_id)) return 'Spread unavailable';
  return line.favorite_team_id === team.id ? `Favorite −${points}` : `Underdog +${points}`;
}

export function pickEmTeamRole(game, team) {
  const line = game.official_line || game.live_line;
  if (line?.spread == null || line.spread === '' || !Number.isFinite(Number(line.spread))) return 'Line unavailable';
  if (![game.home_team.id, game.away_team.id].includes(line.favorite_team_id)) return 'Line unavailable';
  if (Math.abs(Number(line.spread)) === 0) return 'Even';
  return line.favorite_team_id === team.id ? 'Favorite' : 'Underdog';
}
