# LBGUPS lifecycle analytics

Run My Pool records privacy-safe lifecycle events as structured backend logs. The browser sends a random, session-scoped identifier; events do not include email addresses, passwords, pool passwords, payment details, or form contents.

## Current lifecycle events

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
| `support_hub_view` | A visitor viewed the public support and self-service hub. |
| `support_contact_clicked` | A visitor opened a categorized email to platform support. |

## Stage scorecard

| Stage | Customer goal | Primary signal | Confirmed outcome |
|---|---|---|---|
| Learn | Understand the product | `landing_view` | Visitor continues to pricing or account creation. |
| Buy | Choose a suitable plan | `plan_selected`, `checkout_started` | `payment_confirmed` for a paid order. |
| Get | Create an account and enter a pool | `account_creation_view`, `member_onboarding_view` | Server events `user_registered` and `pool_joined`. |
| Use | Create entries and make weekly picks | `weekly_action_center_view`, `weekly_picks_action_clicked` | Server audit records for entry and pick creation. |
| Pay | Understand charges and manage the seasonal plan | `billing_overview_view` | Stripe-backed order and webhook records. |
| Support | Resolve a problem or contact the platform owner | `support_hub_view`, `support_contact_clicked` | A resolved support conversation; this currently lives in the support mailbox. |

Browser events measure intent and navigation. Server events, database records, and Stripe webhooks measure completed outcomes. Do not treat a button click as proof that registration, pool membership, a pick, or payment succeeded.

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

Lifecycle stage traffic:

```text
fields lifecycle_event, session_id
| filter event = "customer_lifecycle_event"
| fields case(
    lifecycle_event = "landing_view", "Learn",
    lifecycle_event in ["pricing_view", "plan_selected", "checkout_started", "payment_confirmed"], "Buy",
    lifecycle_event in ["account_creation_view", "pool_launch_checklist_view", "pool_invite_link_copied", "member_onboarding_view"], "Get",
    lifecycle_event in ["weekly_action_center_view", "weekly_picks_action_clicked"], "Use",
    lifecycle_event = "billing_overview_view", "Pay",
    lifecycle_event in ["support_hub_view", "support_contact_clicked"], "Support",
    "Other"
  ) as stage, session_id
| stats count(*) as events, count_distinct(session_id) as sessions by stage
| sort stage asc
```

Weekly customer-intent trend:

```text
fields @timestamp, lifecycle_event, session_id
| filter event = "customer_lifecycle_event"
| stats count_distinct(session_id) as sessions by bin(7d), lifecycle_event
| sort bin(7d) asc
```

Support self-service versus contact intent:

```text
fields lifecycle_event, session_id
| filter event = "customer_lifecycle_event"
  and lifecycle_event in ["support_hub_view", "support_contact_clicked"]
| stats
    count_distinct(if(lifecycle_event = "support_hub_view", session_id, null)) as support_sessions,
    count_distinct(if(lifecycle_event = "support_contact_clicked", session_id, null)) as contact_sessions
```

Review these measures weekly during launch. A stage with healthy traffic but weak confirmed outcomes indicates a product or reliability problem; weak traffic into a stage usually indicates a navigation, messaging, or discoverability problem.

Registration success is represented by the backend `user_registered` structured event. Continue preferring server-authoritative events, audit records, and payment records for completed pool creation, invitations, picks, Stripe payments, and support outcomes wherever possible.

Successful membership is recorded by the server-authoritative `pool_joined` structured event. It contains pool and user identifiers plus public/private status, but no pool password.
