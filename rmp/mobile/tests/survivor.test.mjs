import { test } from "node:test";
import assert from "node:assert/strict";
import { pickLocked, unavailable } from "../src/domain/survivor.ts";
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
