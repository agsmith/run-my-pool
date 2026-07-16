## ADDED Requirements

### Requirement: Message board posts are rate-limited to prevent spam

A user may post a maximum of 5 messages to a single pool's message board within any rolling 10-minute window. Exceeding this limit returns HTTP 429.

#### Scenario: User posts within the limit
- **WHEN** a user posts 5 or fewer messages to a pool within 10 minutes
- **THEN** all messages are accepted with HTTP 200

#### Scenario: User exceeds the rate limit
- **WHEN** a user posts a 6th message to the same pool within 10 minutes of their 5th
- **THEN** the request is rejected with HTTP 429 and a message indicating the limit and window

#### Scenario: Rate limit resets after the window passes
- **WHEN** a user has posted 5 messages and more than 10 minutes have elapsed since their earliest message in the window
- **THEN** a new post is accepted with HTTP 200

#### Scenario: Rate limit is per user per pool
- **WHEN** User A has hit the limit in Pool X
- **THEN** User A can still post to Pool Y, and User B can still post to Pool X

#### Scenario: Rate limit error message is clear
- **WHEN** HTTP 429 is returned
- **THEN** the response body includes the maximum count (5) and the window duration (10 minutes) in the detail field
