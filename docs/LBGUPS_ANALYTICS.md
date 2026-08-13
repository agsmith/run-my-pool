# LBGUPS lifecycle analytics

Run My Pool records privacy-safe lifecycle events as structured backend logs. The browser sends a random, session-scoped identifier; events do not include email addresses, passwords, pool passwords, payment details, or form contents.

## Current Learn and Buy events

| Event | Meaning |
|---|---|
| `landing_view` | A visitor viewed the marketing homepage. |
| `pricing_view` | A visitor viewed package options. |
| `plan_selected` | A visitor selected a specific package. |
| `account_creation_view` | A visitor reached account creation, optionally with a selected package. |
| `checkout_started` | Stripe returned a secure checkout URL for the selected paid package. |
| `payment_confirmed` | The authenticated success page observed a server-confirmed paid order. |
| `pool_launch_checklist_view` | A new commissioner viewed the post-creation launch checklist. |
| `pool_invite_link_copied` | A commissioner successfully copied the secure pool invitation link. |
| `member_onboarding_view` | A newly joined member saw the pool-specific first-entry guidance. |
| `weekly_action_center_view` | A pool member saw their current-week entry and selection status. |
| `weekly_picks_action_clicked` | A pool member opened entry creation or the weekly pick flow from the action center. |
| `billing_overview_view` | A signed-in user viewed their seasonal plan and payment history. |

All accepted events are explicitly allowlisted by the backend schema. Unknown events, properties, plans, pages, and sources are rejected.

The public receiver also limits declared request bodies to 2 KB, permits 120 events per observed client per minute, suppresses identical events from the same browser session for 10 seconds, and returns no customer data. These controls bound accidental or hostile CloudWatch log volume without placing analytics on the critical customer path.

## CloudWatch Logs Insights

Choose the production backend ECS log group and use:

```text
fields @timestamp, lifecycle_event, plan, page, session_id
| filter event = "customer_lifecycle_event"
| stats count(*) as events, count_distinct(session_id) as sessions by lifecycle_event
| sort sessions desc
```

Package interest:

```text
fields lifecycle_event, plan, session_id
| filter event = "customer_lifecycle_event" and lifecycle_event = "plan_selected"
| stats count(*) as selections, count_distinct(session_id) as sessions by plan
| sort selections desc
```

Basic Learn-to-Buy funnel:

```text
fields lifecycle_event, session_id
| filter event = "customer_lifecycle_event"
| stats
    count_distinct(if(lifecycle_event = "landing_view", session_id, null)) as landing_sessions,
    count_distinct(if(lifecycle_event = "pricing_view", session_id, null)) as pricing_sessions,
    count_distinct(if(lifecycle_event = "plan_selected", session_id, null)) as selecting_sessions,
    count_distinct(if(lifecycle_event = "account_creation_view", session_id, null)) as signup_sessions
```

Registration success is already represented by the backend `user_registered` structured event. Later LBGUPS stages should use server-authoritative events for pool creation, invitations, picks, Stripe payments, and support outcomes wherever possible.

Successful membership is recorded by the server-authoritative `pool_joined` structured event. It contains pool and user identifiers plus public/private status, but no pool password.
