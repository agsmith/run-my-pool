# Forum moderation operations

Pool owners and authorized pool administrators review their pool's Forum queue. Platform administrators can review any pool's queue and handle support escalations. The public contact is support@runmypool.net, which must be monitored by the operator.

## Response process

- Check Forum → Moderation and the support inbox at least daily. Aim to review ordinary reports within 24 hours; prioritize credible threats, exposed private information, and sexual content involving children immediately. This is an operational responsibility, not an automated response guarantee.
- Review the stored message, reason, and surrounding context. Remove violations. Suspend repeat or serious abuse; suspension prevents posting and hides the author's posts within that pool. Review reports against moderators through platform support.
- Dismiss reports that do not violate the rules. Reporter names are not exposed in the moderation UI. Resolved records include the decision, time, and reviewing administrator.
- Handle appeals through support. Restore posting only after review. Restoration makes remaining posts visible again; removed messages stay removed.
- If a report remains unresolved or concerns a pool administrator, escalate it to platform support. Do not ask members to disclose their passwords.

## Product behavior

Posting filters run on the server for both website and native clients. They catch configured profanity, slurs, explicit terms, direct threats, and common obfuscations. They are a first pass, not a comprehensive contextual classifier; member reporting and human moderation remain necessary.

A member's block hides the blocked author's posts across pool forums. It does not remove someone else's pool entries or change picks. Reporting hides that message from the reporter and creates one durable report per reporter/message. Deleting a reported message resolves open reports but preserves the report copy for moderation review and appeals. Apply the privacy policy when processing deletion requests for these records.

## Release verification

Use isolated test accounts/pools to verify posting rejection, report receipt, private moderator access, removal, suspension, and restoration. Check that ordinary members cannot access report content or moderation endpoints. Never seed abusive content in a real member pool for QA.

Before App Review, assign an inbox/queue operator and ensure the daily process is active. Code alone does not provide timely human responses. The policy and support contact do not replace completion of App Store privacy declarations.
