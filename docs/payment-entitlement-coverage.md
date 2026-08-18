# Payment and entitlement coverage

This document maps the manual Stripe sandbox matrix to automated coverage. Hosted Stripe Checkout, card declines, 3DS challenges, and receipt delivery remain manual because Stripe does not support reliable automation of its hosted payment UI.

## Automated on every pull request

| Matrix IDs | Coverage |
|---|---|
| A03 | Free entry boundary: entries 1-10 allowed and entry 11 rejected by the API. |
| B01, B03-B05 | Cancellation context, unused-slot recovery, creation affordances, and server pool-slot enforcement. |
| C01-C05 | Direct-plan Stripe price selection, metadata, capacity contract, and account-scoped payment history. |
| D01-D07 | Free Squares behavior, Squares-only restrictions, existing-board entitlement attachment, pool limits, upgrade amount, and feature gates. |
| E01-E08 | Parameterized upgrade differences and blocked duplicate, downgrade, and invalid Unlimited transitions. |
| F01-F05 | Exact Club and Unlimited pool/entry boundaries plus concurrent final-slot enforcement on MySQL 8.4. |
| G01-G06 | Club-only entry blocks, quantity pricing, capacity fulfillment, order history, audit creation, and idempotency. |
| H06 | Repeated success lookup and webhook fulfillment are idempotent. |
| I02-I04 | Duplicate/distinct webhook idempotency, entry-block idempotency, and expired sessions. |
| J02, J04 | Checkout-session and billing-overview account isolation. |

## Manual Stripe sandbox gates

| Matrix IDs | Reason |
|---|---|
| C06 | Stripe test receipt delivery depends on account-level email settings and inbox delivery. |
| H01-H05 | Declines and interactive 3DS success/failure occur in Stripe-hosted Checkout. |
| I01 | Confirm public Stripe-to-AWS webhook delivery and HTTP response in the Stripe Dashboard. |

## Remaining automation work

- A01, A02 and A04 need a full application journey rather than isolated page/API tests.
- B02 needs an application-level cancel, retry, and fulfillment journey.
- E09 and E10 need full ladder payment-history and data-preservation scenarios.
- I05 now has deterministic frontend polling coverage; a local full-stack browser journey remains desirable.
- I06 metadata fields are asserted in backend contract tests; the sandbox Dashboard comparison remains manual.
- J01 and J03 need a two-user full-stack RBAC browser journey.

## Naming convention

New tests include matrix IDs in their names. CI runs a traceability validator that fails if any matrix ID disappears from this coverage map; test execution and skip handling remain enforced by the backend and frontend suites themselves.
