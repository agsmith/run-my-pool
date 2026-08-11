# Stripe commissioner payments

Run My Pool uses Stripe-hosted Checkout for one-time seasonal commissioner plans. The browser redirect never grants access. The backend activates a seasonal entitlement only after a signed `checkout.session.completed` or `checkout.session.async_payment_succeeded` webhook reports a paid session.

## 1. Create test-mode products and one-time prices

Create these products in Stripe test mode:

| Product | One-time price |
|---|---:|
| Commissioner | $39 USD |
| Pro | $79 USD |
| Club | $129 USD |
| Club Unlimited | $249 USD |

Copy each `price_...` identifier. The backend accepts plan slugs only and selects the matching Price ID server-side, so a browser cannot submit its own amount.

## 2. Create the webhook

Add a Stripe webhook destination:

`https://runmypool.net/billing/webhook`

Subscribe to:

- `checkout.session.completed`
- `checkout.session.async_payment_succeeded`
- `checkout.session.async_payment_failed`
- `checkout.session.expired`

Copy its `whsec_...` signing secret.

For local testing, run:

```bash
stripe listen --forward-to localhost:8000/billing/webhook
```

Use the signing secret printed by the Stripe CLI as `STRIPE_WEBHOOK_SECRET`.

## 3. Store production secrets

Store the Stripe secret API key and webhook signing secret as two separate AWS Secrets Manager secrets. Do not put either value in Terraform variables, GitHub secrets used as plain environment variables, or the repository.

Pass their full ARNs to Terraform:

```bash
export TF_VAR_stripe_secret_key_secret_arn='arn:aws:secretsmanager:us-east-1:ACCOUNT:secret:runmypool/stripe-secret-key-SUFFIX'
export TF_VAR_stripe_webhook_secret_arn='arn:aws:secretsmanager:us-east-1:ACCOUNT:secret:runmypool/stripe-webhook-secret-SUFFIX'
```

Set the non-secret test-mode Price IDs:

```bash
export TF_VAR_stripe_price_commissioner='price_...'
export TF_VAR_stripe_price_pro='price_...'
export TF_VAR_stripe_price_club='price_...'
export TF_VAR_stripe_price_club_unlimited='price_...'
```

Apply Terraform to add the `/billing/*` load-balancer route and inject configuration into the backend task definition.

## 4. Test before live mode

1. Sign in to Run My Pool.
2. Select a paid plan on `/pricing`.
3. Complete Checkout with Stripe's test card `4242 4242 4242 4242` and any future expiration/CVC.
4. Confirm the success page changes from `Confirming payment` to `Payment confirmed`.
5. Confirm a paid `billing_orders` record and an active `commissioner_entitlements` record exist.
6. Resend the webhook event and confirm no second entitlement is created.

After this passes, repeat the product, Price, API key, and webhook setup in Stripe live mode and update the two AWS secrets and four Terraform Price ID variables.

Stripe Tax remains disabled by default. Enable `TF_VAR_stripe_automatic_tax=true` only after the appropriate tax registrations and product tax settings are configured in Stripe.
