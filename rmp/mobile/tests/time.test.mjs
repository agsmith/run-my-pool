import { test } from "node:test";
import assert from "node:assert/strict";
import { apiTime } from "../src/domain/time.ts";

test("legacy UTC kickoff does not move with the phone timezone", () => {
  const old = process.env.TZ;
  try {
    for (const zone of [
      "America/New_York",
      "America/Los_Angeles",
      "Asia/Tokyo",
    ]) {
      process.env.TZ = zone;
      assert.equal(apiTime("2026-09-10T00:20:00"), 1788999600000);
    }
  } finally {
    if (old === undefined) delete process.env.TZ;
    else process.env.TZ = old;
  }
});
test("explicit API offsets preserve the same instant", () => {
  assert.equal(
    apiTime("2026-09-10T00:20:00Z"),
    apiTime("2026-09-09T20:20:00-04:00"),
  );
  assert.equal(
    apiTime("2026-09-10T00:20:00+00:00"),
    apiTime("2026-09-10T00:20:00"),
  );
});
