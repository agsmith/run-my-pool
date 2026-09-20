import { test } from "node:test";
import assert from "node:assert/strict";
import {
  chronologicalGames,
  pickLocked,
  unavailable,
  visibleEntriesForWeek,
} from "../src/domain/survivor.ts";
import { pickEmTeamRole } from "../src/domain/teamSpread.ts";
const game = {
  game_id: 1,
  start_time: "2026-09-10T00:20:00Z",
  home_team: { id: 1, name: "Seattle", abbrv: "SEA" },
  away_team: { id: 2, name: "New England", abbrv: "NE" },
};
const later = {
  game_id: 2,
  start_time: "2026-09-13T17:00:00Z",
  home_team: { id: 3, name: "Buffalo", abbrv: "BUF" },
  away_team: { id: 4, name: "Miami", abbrv: "MIA" },
};
const games = [game, later];
const lock = { locked: false, deadline: "2026-09-13T16:00:00Z" };
const kickoff = Date.parse(game.start_time);
test("both teams lock at the exact early kickoff despite Sunday pool deadline", () => {
  for (const team of ["SEA", "NE"]) {
    const pick = { id: "p", entry_id: "e", week: 1, team, locked: false };
    assert.equal(pickLocked(pick, games, lock, kickoff - 1), false);
    assert.equal(pickLocked(pick, games, lock, kickoff), true);
    assert.equal(
      unavailable("BUF", 1, [pick], games, lock, kickoff),
      "Locked — this pick can no longer be changed",
    );
    assert.equal(
      unavailable(team, 1, [], games, lock, kickoff),
      "Locked — game started",
    );
  }
  assert.equal(unavailable("BUF", 1, [], games, lock, kickoff), null);
});
test("reuse is per entry and excludes the selected week", () => {
  const pick = { id: "p", entry_id: "e", week: 1, team: "BUF", locked: false };
  assert.equal(unavailable("BUF", 1, [pick], games, lock, kickoff), null);
  assert.equal(
    unavailable("BUF", 2, [pick], games, lock, kickoff),
    "Used in week 1",
  );
  assert.equal(unavailable("BUF", 2, [], games, lock, kickoff), null);
});
test("Sunday deadline and explicit server locks remain authoritative", () => {
  const now = Date.parse(lock.deadline);
  assert.equal(unavailable("BUF", 1, [], games, lock, now), "Locked — this pick can no longer be changed");
  assert.equal(
    pickLocked(
      { id: "p", entry_id: "e", week: 1, team: "BUF", locked: true },
      games,
      lock,
      kickoff,
    ),
    true,
  );
  assert.equal(
    unavailable("FAKE", 1, [], games, lock, kickoff),
    "Not scheduled",
  );
});

test("eliminated entries remain visible through their elimination week only", () => {
  const entries = [
    { id: "alive", name: "Still Alive", alive: true },
    { id: "week-2", name: "Eliminated Week 2", alive: false },
    { id: "week-1", name: "Eliminated Week 1", alive: false },
  ];
  const picks = {
    alive: [],
    "week-2": [
      { id: "p2", entry_id: "week-2", week: 2, team: "BUF", locked: true, result: "loss" },
    ],
    "week-1": [
      { id: "p1", entry_id: "week-1", week: 1, team: "SEA", locked: true, result: "LOSS" },
    ],
  };
  assert.deepEqual(
    visibleEntriesForWeek(entries, picks, 1).map((entry) => entry.id),
    ["alive", "week-2", "week-1"],
  );
  assert.deepEqual(
    visibleEntriesForWeek(entries, picks, 2).map((entry) => entry.id),
    ["alive", "week-2"],
  );
  assert.deepEqual(
    visibleEntriesForWeek(entries, picks, 3).map((entry) => entry.id),
    ["alive"],
  );
});

test("pick em labels the favorite and underdog without displaying a spread", () => {
  const linedGame = {
    ...game,
    live_line: { spread: 6.5, favorite_team_id: game.home_team.id },
  };
  assert.equal(pickEmTeamRole(linedGame, game.home_team), "Favorite");
  assert.equal(pickEmTeamRole(linedGame, game.away_team), "Underdog");
  assert.equal(
    pickEmTeamRole(
      { ...game, live_line: { spread: 0, favorite_team_id: game.home_team.id } },
      game.home_team,
    ),
    "Even",
  );
});

test("pick em games are ordered by kickoff time", () => {
  assert.deepEqual(
    chronologicalGames([later, game]).map((item) => item.game_id),
    [game.game_id, later.game_id],
  );
});
