import { pickEmTeamRole, teamSpread } from '../lib/teamSpread';
const home={id:1}, away={id:2};
const game={home_team:home,away_team:away};
test.each([1,2])('shows opposite signed spreads for either favorite', (favorite) => {
 const g={...game,live_line:{spread:3.5,favorite_team_id:favorite}};
 expect(teamSpread(g,{id:favorite})).toBe('Favorite −3.5');
 expect(teamSpread(g,{id:favorite===1?2:1})).toBe('Underdog +3.5');
});
test('uses official line when available and handles even games',()=>{
 expect(teamSpread({...game,official_line:{spread:0},live_line:{spread:7,favorite_team_id:1}},home)).toBe('Even · 0');
});
test.each([null,{}, {spread:null}, {spread:4,favorite_team_id:99}])('does not invent unavailable spreads',line=>{
 expect(teamSpread({...game,live_line:line},home)).toBe('Spread unavailable');
});
test('pick em identifies favorite and underdog without showing the spread',()=>{
 const g={...game,live_line:{spread:6.5,favorite_team_id:1}};
 expect(pickEmTeamRole(g,home)).toBe('Favorite');
 expect(pickEmTeamRole(g,away)).toBe('Underdog');
 expect(pickEmTeamRole({...game,live_line:{spread:0,favorite_team_id:1}},home)).toBe('Even');
});
