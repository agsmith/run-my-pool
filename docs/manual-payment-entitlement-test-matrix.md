# Manual payment and entitlement test matrix

Use this runbook against the Stripe sandbox. It exercises customer-visible checkout behavior, webhook fulfillment, seasonal entitlements, upgrades, entry capacity, pool-type restrictions, abandoned setup recovery, and account isolation.

## Safety and test setup

- Confirm Stripe is in **test mode** before starting. Never enter a real card.
- Use the current season shown on Run My Pool's Pricing and Profile pages.
- Replace `<run>` in every email with a short unique run identifier, such as `20260817a`. This makes every account unique without changing the role mapping.
- The aliases below assume `agsmith11@gmail.com` receives Gmail plus-addresses. Confirm that inbox can receive Run My Pool verification and Stripe receipt emails before the full run.
- Use one QA-only password stored in a password manager. Do not add it to this file.
- Use a future expiration such as `12/34`, any three-digit CVC, and any valid postal code.
- Record the Stripe Checkout Session ID (`cs_test_...`), Billing Order ID when available, pool ID, and screenshots in the Evidence column.

### Stripe test instruments

| Behavior | Test card |
|---|---|
| Successful Visa payment | `4242 4242 4242 4242` |
| Generic decline | `4000 0000 0000 0002` |
| Insufficient funds | `4000 0000 0000 9995` |
| Requires 3D Secure authentication | `4000 0025 0000 3155` |

Stripe's current test-card reference is <https://docs.stripe.com/testing>.

## Test-user map

| User ID | Email address | Starting purpose | Preserve state between tests? |
|---|---|---|---|
| U01 | `agsmith11+rmp-free-<run>@gmail.com` | Free plan and owner/member baseline | Yes, through F-series |
| U02 | `agsmith11+rmp-cancel-<run>@gmail.com` | Checkout cancellation before payment | Yes |
| U03 | `agsmith11+rmp-resume-<run>@gmail.com` | Paid purchase followed by abandoned pool creation | Yes |
| U04 | `agsmith11+rmp-squares-<run>@gmail.com` | Free Squares to Squares Plus to Commish | Yes; run in order |
| U05 | `agsmith11+rmp-ladder-<run>@gmail.com` | Commish to Pro to Club to Club Unlimited ladder | Yes; run in order |
| U06 | `agsmith11+rmp-pro-<run>@gmail.com` | Direct Pro purchase and one-pool limit | Yes |
| U07 | `agsmith11+rmp-club-<run>@gmail.com` | Direct Club purchase, five pools, and entry blocks | Yes |
| U08 | `agsmith11+rmp-unlimited-<run>@gmail.com` | Direct Club Unlimited purchase | Yes |
| U09 | `agsmith11+rmp-decline-<run>@gmail.com` | Declined and recovered payment | Yes |
| U10 | `agsmith11+rmp-3ds-<run>@gmail.com` | 3D Secure Checkout | Yes |
| U11 | `agsmith11+rmp-isolation-a-<run>@gmail.com` | Cross-account entitlement isolation, owner | Yes |
| U12 | `agsmith11+rmp-isolation-b-<run>@gmail.com` | Cross-account entitlement isolation, other user | Yes |
| U13 | `agsmith11+rmp-squares-new-<run>@gmail.com` | Fresh Squares Plus purchase before board creation | Yes |

## Result notation

Use `Not run`, `Pass`, `Fail`, or `Blocked` in the Status column. A test passes only when both the visible behavior and the entitlement/capacity result match.

## A. Account and free-plan baseline

| ID | User | Procedure | Expected result | Status | Evidence |
|---|---|---|---|---|---|
| A01 | U01 | Register, verify email, log in, and open the Pool Directory. | Account works; no paid plan appears in Profile & Billing; global **Create Pool** is available. | Not run | |
| A02 | U01 | Create a free Survivor pool, cancel setup once before submitting, then return using global **Create Pool**. | Cancel does not strand the user; creation can be started again. | Not run | |
| A03 | U01 | Complete the free Survivor pool and create ten entries. Attempt an eleventh. | First ten entries succeed; the server rejects capacity beyond the free allowance. | Not run | |
| A04 | U01 | Confirm no card or payment is requested for members joining the pool. | Members participate without a software payment. | Not run | |

## B. Checkout cancellation and paid-setup recovery

| ID | User | Procedure | Expected result | Status | Evidence |
|---|---|---|---|---|---|
| B01 | U02 | Select Commish, reach Stripe Checkout, then use Stripe's back/cancel action without paying. | Returns to Pricing with cancellation context; no active paid entitlement appears; no paid receipt is sent. | Not run | |
| B02 | U02 | Start Commish Checkout again and pay with `4242`. | A second attempt is allowed; success page changes from confirming to **Payment confirmed**; Commish becomes active. | Not run | |
| B03 | U03 | Buy Pro with `4242`. On success, choose Dashboard instead of creating a pool. | Pro remains active; Pool Directory, Profile & Billing, and global navigation provide an intuitive **Create Pool** recovery action. | Not run | |
| B04 | U03 | Enter pool setup, fill several fields, click Cancel, then return to Pool Directory. | Entitlement is unchanged; **Create your purchased pool** remains available. | Not run | |
| B05 | U03 | Create the Pro pool, then revisit Pool Directory, Profile, and global navigation. | The one included pool slot is consumed and creation actions disappear; a direct second creation attempt is rejected server-side. | Not run | |

## C. Direct product purchases

| ID | User | Procedure | Expected result | Status | Evidence |
|---|---|---|---|---|---|
| C01 | U13 | With no paid plan, purchase Squares Plus for $10 using `4242`. | Exactly $10 is shown and charged; Squares Plus is active for the current season. | Not run | |
| C02 | U06 | Purchase Pro directly using `4242`. | Exactly $79 is shown and charged; one pool and 150-entry capacity are granted. | Not run | |
| C03 | U07 | Purchase Club directly using `4242`. | Exactly $129 is shown and charged; five pool slots and 500 shared entries are granted. | Not run | |
| C04 | U08 | Purchase Club Unlimited directly using `4242`. | Exactly $249 is shown and charged; pool and entry capacity display as unlimited. | Not run | |
| C05 | U03 | Review Profile payment history after the Pro purchase. | Paid date, plan, status, and $79 amount are correct and scoped to U03. | Not run | |
| C06 | U03 | Check the purchasing inbox and Stripe test customer. | Stripe receipt is delivered if test-mode successful-payment emails are enabled; customer email and payment match U03. | Not run | |

## D. Squares entitlement path

Run D01-D04 and D06-D07 in order with U04. D05 continues U13 after C01.

| ID | User | Procedure | Expected result | Status | Evidence |
|---|---|---|---|---|---|
| D01 | U04 | Before paying, create one free Squares board. | One owner-managed 100-square board is allowed; online invitations/self-service joining are unavailable. | Not run | |
| D02 | U04 | Attempt a second free Squares board. | Server rejects the second free board and presents the Squares Plus upgrade. | Not run | |
| D03 | U04 | Purchase Squares Plus for $10. | Existing eligible Squares board is associated with the entitlement; online joining and self-service reservations become available. | Not run | |
| D04 | U04 | Use **Create Pool** while Squares Plus is active and its one slot is already consumed. | Creation capability is unavailable; direct creation is rejected because the one pool slot is used. | Not run | |
| D05 | U13 | After purchasing Squares Plus before creating any board, enter pool setup. | Only Squares can be selected; Survivor and Pick 'Em are not offered. | Not run | |
| D06 | U04 | Upgrade Squares Plus to Commish. | Checkout charges the $29 difference; entitlement becomes Commish without losing the board or claims. | Not run | |
| D07 | U04 | Confirm Commish features on the existing board. | Advanced Squares administration and supported pot modes become available; existing board data remains intact. | Not run | |

## E. Upgrade ladder and invalid transitions

Run E01-E10 in order with U05 unless another user is specified.

| ID | User | Procedure | Expected result | Status | Evidence |
|---|---|---|---|---|---|
| E01 | U05 | Purchase Commish. | Checkout charges $39; Commish entitlement is active. | Not run | |
| E02 | U05 | Upgrade Commish to Pro. | Checkout charges only $40; entitlement changes to Pro; existing pools and entries remain. | Not run | |
| E03 | U05 | Upgrade Pro to Club. | Checkout charges only $50; entitlement changes to Club; capacity becomes five pools/500 entries. | Not run | |
| E04 | U05 | Upgrade Club to Club Unlimited. | Checkout charges only $120; entitlement becomes Club Unlimited. | Not run | |
| E05 | U05 | Attempt to purchase Commish, Pro, Club, or Unlimited again. | Duplicate or downgrade purchase is blocked; no second charge or duplicate entitlement occurs. | Not run | |
| E06 | U06 | Attempt Pro directly to Club Unlimited. | Upgrade is blocked with guidance that Unlimited is available initially or from Club. | Not run | |
| E07 | U06 | Upgrade Pro to Club, then Club to Unlimited. | Both allowed transitions succeed at $50 and $120 respectively. | Not run | |
| E08 | U08 | Attempt Club Unlimited to Club or another Club Unlimited purchase. | Downgrade/duplicate is blocked and existing Unlimited entitlement remains unchanged. | Not run | |
| E09 | U05 | Review payment history after the full ladder. | Four paid plan orders appear with $39, $40, $50, and $120 amounts; current plan is Unlimited. | Not run | |
| E10 | U05 | Open all pools and entries created before upgrades. | No pool, membership, entry, pick, or Squares data was lost during upgrades. | Not run | |

## F. Pool-slot and entry-capacity enforcement

| ID | User | Procedure | Expected result | Status | Evidence |
|---|---|---|---|---|---|
| F01 | U06 | With direct Pro, create one Survivor or Pick 'Em pool, then attempt another. | First pool succeeds; second is blocked; global and recovery Create Pool actions disappear after slot consumption. | Not run | |
| F02 | U07 | With Club, create five mixed pool types. Observe creation affordances after each. | Creation remains available through slot five and disappears after the fifth; sixth pool is rejected server-side. | Not run | |
| F03 | U07 | Create entries across multiple Club pools until shared usage reaches 500, then attempt one more. | Capacity is shared across entitlement-linked pools; entry 501 is rejected. | Not run | |
| F04 | U08 | Create more than five pools and exceed 500 entries. | No plan-capacity rejection occurs for Club Unlimited. | Not run | |
| F05 | U06 | After consuming Pro's pool slot, attempt to submit another pool from a setup tab opened before the first pool was created. | Backend remains authoritative and rejects the request even if stale UI still displays a button. | Not run | |

## G. Club entry blocks

Run G01-G06 in order with U07.

| ID | User | Procedure | Expected result | Status | Evidence |
|---|---|---|---|---|---|
| G01 | U07 | From Profile & Billing, buy one +100 entry block. | Checkout charges $25; Club capacity changes from 500 to 600. | Not run | |
| G02 | U07 | Buy three +100 blocks in one Checkout. | Checkout charges $75; capacity increases by exactly 300, not by 100. | Not run | |
| G03 | U07 | Cancel a block Checkout before payment. | Returns to Profile; no capacity is added and no paid receipt is sent. | Not run | |
| G04 | U06 | While on Pro, attempt to purchase an entry block through any available/stale path. | Server rejects it because blocks require active Club. | Not run | |
| G05 | U05 | After Club has upgraded to Unlimited, attempt to buy a Club entry block. | Server rejects it because the active plan is no longer Club. | Not run | |
| G06 | U07 | Review payment history. | Block orders show quantity and paid amount separately from plan purchases. | Not run | |

## H. Declines, authentication, and retry behavior

| ID | User | Procedure | Expected result | Status | Evidence |
|---|---|---|---|---|---|
| H01 | U09 | Attempt Commish with generic-decline card `4000 0000 0000 0002`. | Stripe displays a decline; Run My Pool grants no entitlement. | Not run | |
| H02 | U09 | Retry with insufficient-funds card `4000 0000 0000 9995`. | Stripe displays insufficient funds; no entitlement or paid order is granted. | Not run | |
| H03 | U09 | Retry the same plan with `4242`. | Payment succeeds; one active entitlement is granted despite earlier failed attempts. | Not run | |
| H04 | U10 | Purchase Pro with `4000 0025 0000 3155` and complete Stripe's authentication challenge successfully. | Checkout returns successfully and Pro activates only after the paid webhook. | Not run | |
| H05 | U10 | Repeat on a fresh order but fail/cancel the authentication challenge. | No paid entitlement is granted; the user can retry. | Not run | |
| H06 | U09 | Refresh or revisit a successful `checkout/success?session_id=...` URL. | Status remains paid; no duplicate charge, order, or entitlement is created. | Not run | |

## I. Webhook fulfillment and idempotency

These checks require Stripe test Dashboard access. Database confirmation may be performed with the read-only production connection or Platform Admin where the field is visible; do not edit production billing rows manually.

| ID | User | Procedure | Expected result | Status | Evidence |
|---|---|---|---|---|---|
| I01 | U03 | In Stripe test events, find the successful Checkout event and confirm delivery to `/billing/webhook`. | Delivery is HTTP 2xx and the corresponding Run My Pool order becomes paid. | Not run | |
| I02 | U03 | Resend the same successful webhook event twice. | Still exactly one paid order effect and one active seasonal entitlement; no duplicate capacity. | Not run | |
| I03 | U07 | Resend the three-block successful event twice. | Capacity does not increase again; quantity remains three and the entitlement total is unchanged. | Not run | |
| I04 | U02 | Expire an unpaid Checkout Session from Stripe or wait for expiration and deliver `checkout.session.expired`. | Order is not paid, no entitlement is granted, and a new checkout can be started. | Not run | |
| I05 | U03 | Temporarily observe the success page before webhook fulfillment completes. | Page may show **Confirming payment**, polls safely, then becomes **Payment confirmed** after fulfillment. | Not run | |
| I06 | U03 | Compare Stripe metadata with Run My Pool data. | `order_id`, `user_id`, plan, season, order type, and quantity identify the same purchase. | Not run | |

## J. Account isolation and authorization

| ID | User | Procedure | Expected result | Status | Evidence |
|---|---|---|---|---|---|
| J01 | U11 | Purchase Pro and create its pool. Log out and sign in as U12. | U12 cannot see U11's entitlement, orders, receipt details, or owner-only pool controls. | Not run | |
| J02 | U12 | Open U11's copied Checkout success/session URL while authenticated as U12. | Run My Pool reports the session as unavailable/not found; no payment data leaks. | Not run | |
| J03 | U12 | Join U11's pool as a member. | Membership does not transfer ownership or entitlement; U12 cannot create entries beyond U11's pool rules or administer billing. | Not run | |
| J04 | U11 | Return to Profile and Pool Directory. | U11 still sees its correct entitlement, capacity, payment history, and creation capability. | Not run | |

## Completion summary

| Area | Pass | Fail | Blocked | Notes |
|---|---:|---:|---:|---|
| Account/free baseline | 0 | 0 | 0 | |
| Cancellation/recovery | 0 | 0 | 0 | |
| Direct purchases | 0 | 0 | 0 | |
| Squares | 0 | 0 | 0 | |
| Upgrades | 0 | 0 | 0 | |
| Capacity | 0 | 0 | 0 | |
| Entry blocks | 0 | 0 | 0 | |
| Declines/3DS | 0 | 0 | 0 | |
| Webhooks | 0 | 0 | 0 | |
| Isolation/RBAC | 0 | 0 | 0 | |

## Cleanup after a run

1. Export or retain the completed matrix and screenshots.
2. Keep at least one successful test customer/event for webhook troubleshooting.
3. Delete or deactivate only the `<run>` test users, pools, Stripe test customers, and test-mode objects that are no longer needed.
4. Never delete real users, live-mode Stripe objects, production entitlements, or audit records as part of QA cleanup.
5. Start the next pass with a new `<run>` suffix rather than attempting to reuse partially upgraded accounts.
