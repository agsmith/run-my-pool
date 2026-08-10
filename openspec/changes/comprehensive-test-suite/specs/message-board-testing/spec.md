## ADDED Requirements

### Requirement: Pool membership gates message board access
A user SHALL only be able to read or post messages in a pool if they have at least one Entry row associated with that pool, regardless of entry alive status.

#### Scenario: User with alive entry can post
- **WHEN** a user has an entry with alive=True in the pool
- **THEN** POST /messages/pool/{pool_id} returns HTTP 200

#### Scenario: User with eliminated entry can still post
- **WHEN** a user has an entry with alive=False in the pool (eliminated but not deleted)
- **THEN** POST /messages/pool/{pool_id} returns HTTP 200

#### Scenario: User with no entry in pool cannot post
- **WHEN** a user has no Entry row for the pool
- **THEN** POST /messages/pool/{pool_id} returns HTTP 403 with detail containing "must be a member"

#### Scenario: User whose entry was deleted cannot post
- **WHEN** a user's only entry in the pool has been deleted (no Entry row remains)
- **THEN** POST /messages/pool/{pool_id} returns HTTP 403

#### Scenario: User with no entry cannot read messages
- **WHEN** a user has no Entry row for the pool
- **THEN** GET /messages/pool/{pool_id} returns HTTP 403 with detail containing "must be a member"

### Requirement: Rate limit enforced at 5 messages per 10 minutes per user per pool
The system SHALL reject message posts that exceed 5 messages within any 10-minute rolling window for the same user and pool combination.

#### Scenario: Fifth message succeeds
- **WHEN** a user posts 5 messages to a pool within 10 minutes
- **THEN** all 5 responses are HTTP 200

#### Scenario: Sixth message in window is rejected
- **WHEN** a user posts a 6th message to a pool within the same 10-minute window
- **THEN** the response is HTTP 429 with detail "Rate limit exceeded: maximum 5 messages per 10 minutes per pool."

#### Scenario: Rate limit resets after window expires
- **WHEN** a user posts 5 messages, the 10-minute window passes, then posts again
- **THEN** the new post returns HTTP 200

### Requirement: Message content constraints are enforced
The system SHALL reject messages that are empty, whitespace-only, or exceed 250 characters.

#### Scenario: Empty message is rejected
- **WHEN** a POST /messages/pool/{pool_id} is made with an empty string or whitespace-only body
- **THEN** the response is HTTP 400

#### Scenario: 250-character message is accepted
- **WHEN** a POST /messages/pool/{pool_id} is made with exactly 250 characters
- **THEN** the response is HTTP 200

#### Scenario: 251-character message is rejected
- **WHEN** a POST /messages/pool/{pool_id} is made with 251 characters
- **THEN** the response is HTTP 400

### Requirement: Users can only delete their own messages
The system SHALL allow a user to delete their own messages and SHALL reject attempts to delete another user's message.

#### Scenario: User deletes own message
- **WHEN** a user calls DELETE /messages/{message_id} for a message they posted
- **THEN** the response is HTTP 200 and the message is removed

#### Scenario: User cannot delete another user's message
- **WHEN** a user calls DELETE /messages/{message_id} for a message posted by a different user
- **THEN** the response is HTTP 403 with detail containing "own messages"
