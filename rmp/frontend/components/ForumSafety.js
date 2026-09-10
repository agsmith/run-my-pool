import { useCallback, useEffect, useState } from "react";

const reasons = [
  "Harassment or hate",
  "Threats or violence",
  "Sexual content",
  "Spam or scam",
  "Personal information",
  "Other",
];
export function useForumSafety(poolId, onChange) {
  const [state, setState] = useState(null);
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");
  const [busy, setBusy] = useState(false);
  const request = useCallback(async (path, method = "GET", body) => {
    const response = await fetch(`${process.env.NEXT_PUBLIC_API_URL}${path}`, {
      method,
      credentials: "include",
        cache: "no-store",
      headers: {
        "Content-Type": "application/json",
        Authorization: `Bearer ${localStorage.getItem("access_token")}`,
      },
      ...(body === undefined ? {} : { body: JSON.stringify(body) }),
    });
    const data = await response.json();
    if (!response.ok)
      throw new Error(
        typeof data.detail === "string"
          ? data.detail
          : "Unable to update Forum safety settings.",
      );
    return data;
  }, []);
  const refresh = useCallback(async () => {
    if (!poolId) return;
    try {
      setState(await request(`/messages/pool/${poolId}/safety`));
    } catch (e) {
      setError(e.message);
    }
  }, [poolId, request]);
  useEffect(() => {
    refresh();
  }, [refresh]);
  async function mutate(path, method, body, message = "Updated.") {
    if (busy) return;
    setBusy(true);
    setError("");
    setNotice("");
    try {
      await request(path, method, body);
      setNotice(message);
      await refresh();
      await onChange();
    } catch (e) {
      setError(e.message);
    } finally {
      setBusy(false);
    }
  }
  return { state, error, notice, busy, mutate, refresh, poolId };
}
const buttonStyle = {
  padding: "10px 14px",
  margin: "4px",
  border: "1px solid #6b8790",
  borderRadius: 8,
  cursor: "pointer",
  color: "#e8f4f5",
  background: "#14292e",
  minHeight: 44,
};
export function ForumMessageActions({ message, safety }) {
  const [reason, setReason] = useState(reasons[0]);
  const [reporting, setReporting] = useState(false);
  return (
    <div>
      <button
        type="button"
        style={buttonStyle}
        disabled={safety.busy}
        onClick={() => setReporting(!reporting)}
      >
        Report message
      </button>
      <button
        type="button"
        style={buttonStyle}
        disabled={safety.busy}
        onClick={() => {
          if (
            window.confirm(
              "Hide this member’s messages from you across all pool forums? You can unblock them in Forum safety.",
            )
          )
            safety.mutate(
              `/messages/pool/${safety.poolId}/blocks/${message.user_id}`,
              "PUT",
              undefined,
              "Member blocked.",
            );
        }}
      >
        Block member
      </button>
      {reporting && (
        <div>
          <label>
            Report reason{" "}
            <select
              aria-label="Report reason"
              value={reason}
              onChange={(e) => setReason(e.target.value)}
            >
              {reasons.map((r) => (
                <option key={r}>{r}</option>
              ))}
            </select>
          </label>
          <button
            type="button"
            style={buttonStyle}
            disabled={safety.busy}
            onClick={() =>
              safety.mutate(
                `/messages/${message.id}/report`,
                "POST",
                { reason },
                "Report received. The message is hidden from you and queued for moderator review.",
              )
            }
          >
            Send report
          </button>
          <button
            type="button"
            style={buttonStyle}
            onClick={() => setReporting(false)}
          >
            Cancel report
          </button>
        </div>
      )}
    </div>
  );
}
export function ForumSafetyPanel({ safety }) {
  const { state, poolId, busy, mutate } = safety;
  return (
    <section
      style={{
        padding: 20,
        margin: "20px 0",
        background: "#102126",
        borderRadius: 12,
        color: "#e8f4f5",
        overflowWrap: "anywhere",
      }}
    >
      <h2>Forum safety</h2>
      <p>
        No harassment, hate speech, threats, explicit content, scams, spam, or
        sharing someone’s private information. By posting, you agree to these
        rules. Posting filters are a first check; report anything they miss.
      </p>
      <p>
        Reports go to pool and platform moderators. For urgent concerns,
        questions, or appeals, email{" "}
        <a href="mailto:support@runmypool.net?subject=Forum%20safety">
          support@runmypool.net
        </a>
        .
      </p>
      {safety.error && <p role="alert">{safety.error}</p>}
      {safety.notice && <p role="status">{safety.notice}</p>}
      {state?.suspended && (
        <p role="alert">
          Your posting access in this pool is suspended. Contact support to
          appeal.
        </p>
      )}
      {!!state?.blocks?.length && (
        <div>
          <h3>Blocked members</h3>
          {state.blocks.map((b) => (
            <button
              key={b.id}
              style={buttonStyle}
              disabled={busy}
              onClick={() => mutate(`/messages/blocks/${b.id}`, "DELETE")}
            >
              Unblock {b.name}
            </button>
          ))}
        </div>
      )}
      {state?.can_moderate && (
        <div>
          <h3>Moderation · {state.reports.length} open reports</h3>
          <p>
            Review promptly, oldest first. Remove violations and suspend
            repeated abuse. Escalate threats or appeals to support. Reporter
            identities are private.
          </p>
          <button style={buttonStyle} onClick={safety.refresh}>
            Refresh reports
          </button>
          {state.reports.map((r) => (
            <article
              key={r.id}
              style={{ borderTop: "1px solid #6b8790", padding: "16px 0" }}
            >
              <strong>{r.reason}</strong>
              <p>{r.message}</p>
              <time>{new Date(`${r.created_at}Z`).toLocaleString()}</time>
              <div>
                {[
                  ["dismiss", "Dismiss report"],
                  ["remove", "Remove message"],
                  ["suspend", "Remove and suspend author"],
                ].map(([action, label]) => (
                  <button
                    key={action}
                    style={buttonStyle}
                    disabled={busy}
                    onClick={() => {
                      if (
                        window.confirm(
                          `${label}? Suspension hides the author’s posts and prevents posting in this pool until restored.`,
                        )
                      )
                        mutate(
                          `/messages/pool/${poolId}/reports/${r.id}/review`,
                          "POST",
                          { action },
                        );
                    }}
                  >
                    {label}
                  </button>
                ))}
              </div>
            </article>
          ))}
          {state.bans.map((b) => (
            <button
              key={b.id}
              style={buttonStyle}
              disabled={busy}
              onClick={() => {
                if (
                  window.confirm(
                    "Restore posting and show this member’s remaining messages?",
                  )
                )
                  mutate(
                    `/messages/pool/${poolId}/suspensions/${b.id}`,
                    "DELETE",
                  );
              }}
            >
              Restore posting: {b.name}
            </button>
          ))}
        </div>
      )}
    </section>
  );
}
