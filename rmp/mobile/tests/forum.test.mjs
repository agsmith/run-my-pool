import { test } from "node:test";
import assert from "node:assert/strict";
import { fetchAllForumMessages } from "../src/domain/forum.ts";

test("loads every forum page until the conversation is complete", async () => {
  const all = Array.from({ length: 1_205 }, (_, index) => ({ id: index }));
  const requests = [];

  const messages = await fetchAllForumMessages(async (skip, limit) => {
    requests.push({ skip, limit });
    return all.slice(skip, skip + limit);
  });

  assert.deepEqual(messages, all);
  assert.deepEqual(requests, [
    { skip: 0, limit: 500 },
    { skip: 500, limit: 500 },
    { skip: 1000, limit: 500 },
  ]);
});

test("stops after one request when the forum has fewer than 500 messages", async () => {
  let calls = 0;
  const messages = await fetchAllForumMessages(async () => {
    calls += 1;
    return [{ id: "only" }];
  });

  assert.deepEqual(messages, [{ id: "only" }]);
  assert.equal(calls, 1);
});
