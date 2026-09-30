# App Review demo account

Apple reviews the iOS app with the fixed ordinary-member account
`zz_test_member@gmail.com`. The account must stay active and verified. It must
not be a pool administrator.

`prepare_app_review_account.py` is an idempotent production-safe setup command.
It creates three private demo pools owned by fixture users and makes the review
account a member. The pools include:

- Survivor entries, settled picks, leaderboard rows, Pick Breakdown data, and
  an auto-pick label.
- Pick 'Em entries, settled weekly picks, season standings, and tiebreakers.
- A locked Squares board with several named claims and a final result.
- Website Forum fixtures used by website moderation tests. The native app does
  not expose the Forum or any other member-posting feature.

The command removes any `PoolAdmin` grants from the review account and sets its
global role to `USER`. It does not delete or modify normal customer pools.

For the established fixed account, preserve its current password while adding
or refreshing the demo content:

```bash
python prepare_app_review_account.py --preserve-password
```

To set a new review password, run it only in the backend container or another
environment that already has the production database variables:

```bash
export APP_REVIEW_PASSWORD='the password stored in App Store Connect'
python prepare_app_review_account.py
unset APP_REVIEW_PASSWORD
```

Do not put the password in source control or shell history. Verify the account
and demo row counts without changing anything:

```bash
python prepare_app_review_account.py --verify-only
```

Before resubmission, sign in on a physical iPhone or iPad and verify all three
demo pools appear under **My Pools**. Open My Picks, Weekly Pick Breakdown, and
Season Leaderboard or Results in each applicable pool. Confirm there is no
Forum, chat, direct messaging, comments, or other member-posting feature in the
native app.
