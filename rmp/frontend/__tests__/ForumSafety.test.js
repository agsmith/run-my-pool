import "@testing-library/jest-dom";
import React from "react";
import { render, screen, fireEvent } from "@testing-library/react";
import {
  ForumMessageActions,
  ForumSafetyPanel,
} from "../components/ForumSafety";

const base = () => ({
  poolId: "pool-1",
  busy: false,
  mutate: jest.fn(),
  refresh: jest.fn(),
  state: { can_moderate: false, blocks: [], reports: [], bans: [] },
});

test("reporting submits the selected reason for the correct message", () => {
  const safety = base();
  render(
    <ForumMessageActions
      message={{ id: "message-1", user_id: "author-1" }}
      safety={safety}
    />,
  );
  fireEvent.click(screen.getByText("Report message"));
  fireEvent.change(screen.getByLabelText("Report reason"), {
    target: { value: "Personal information" },
  });
  fireEvent.click(screen.getByText("Send report"));
  expect(safety.mutate).toHaveBeenCalledWith(
    "/messages/message-1/report",
    "POST",
    { reason: "Personal information" },
    expect.any(String),
  );
});

test("blocking requires confirmation and targets the author", () => {
  const safety = base();
  const confirm = jest.spyOn(window, "confirm").mockReturnValue(false);
  render(
    <ForumMessageActions
      message={{ id: "message-1", user_id: "author-1" }}
      safety={safety}
    />,
  );
  fireEvent.click(screen.getByText("Block member"));
  expect(safety.mutate).not.toHaveBeenCalled();
  confirm.mockReturnValue(true);
  fireEvent.click(screen.getByText("Block member"));
  expect(safety.mutate).toHaveBeenCalledWith(
    "/messages/pool/pool-1/blocks/author-1",
    "PUT",
    undefined,
    "Member blocked.",
  );
  confirm.mockRestore();
});

test("ordinary members see support and unblock controls but no moderation queue", () => {
  const safety = base();
  safety.state.blocks = [{ id: "author-1", name: "Member" }];
  render(<ForumSafetyPanel safety={safety} />);
  expect(
    screen.getByRole("link", { name: "support@runmypool.net" }),
  ).toHaveAttribute("href", expect.stringContaining("mailto:"));
  expect(screen.queryByText(/open reports/)).not.toBeInTheDocument();
  fireEvent.click(screen.getByText("Unblock Member"));
  expect(safety.mutate).toHaveBeenCalledWith(
    "/messages/blocks/author-1",
    "DELETE",
  );
});

test("moderators can review reports and restore posting after confirmation", () => {
  const safety = base();
  safety.state.can_moderate = true;
  safety.state.reports = [
    {
      id: "report-1",
      reason: "Spam or scam",
      message: "Reported content",
      created_at: "2026-09-10T12:00:00",
    },
  ];
  safety.state.bans = [{ id: "author-1", name: "Member" }];
  const confirm = jest.spyOn(window, "confirm").mockReturnValue(true);
  render(<ForumSafetyPanel safety={safety} />);
  fireEvent.click(screen.getByText("Remove and suspend author"));
  expect(safety.mutate).toHaveBeenCalledWith(
    "/messages/pool/pool-1/reports/report-1/review",
    "POST",
    { action: "suspend" },
  );
  fireEvent.click(screen.getByText("Restore posting: Member"));
  expect(safety.mutate).toHaveBeenCalledWith(
    "/messages/pool/pool-1/suspensions/author-1",
    "DELETE",
  );
  confirm.mockRestore();
});
