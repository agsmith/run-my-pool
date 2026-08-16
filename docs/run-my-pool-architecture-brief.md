# RunMyPool — Architecture Brief

## Table of Contents

- [Overview](#overview)
- [Problem Definitions & Business Context](#problem-definitions--business-context)
- [C4 System Context Diagram](#c4-system-context-diagram)
- [System Overview](#system-overview)
  - [C4 Container Diagram](#c4-container-diagram)
  - [C4 Container Diagram Explanation](#c4-container-diagram-explanation)
  - [Request Flow Sequence](#request-flow-sequence)
  - [Technology Stack](#technology-stack)
- [System Data Models](#system-data-models)
  - [Data Model ER Diagram](#data-model-er-diagram)
  - [Data Model Explanation](#data-model-explanation)
- [API Endpoints](#api-endpoints)
  - [Auth](#auth--auth)
  - [Users](#users--users)
  - [Pools](#pools--pools)
  - [Entries](#entries--entries)
  - [Picks](#picks--picks)
  - [Admin](#admin)
  - [Schedule & Teams](#schedule--teams)
  - [Billing](#billing--billing)
  - [Message Board](#message-board--message-board)
  - [Audit & Analytics](#audit--analytics)
  - [Platform Admin](#platform-admin--platform-admin)
  - [Health](#health)
- [Deployment Architecture](#deployment-architecture)
- [Document Metadata](#document-metadata)


## Overview

RunMyPool (`runmypool.net`) is a SaaS sports pool management platform for the NFL season. Commissioners create and manage football pools — starting with Survivor format — while members join, make weekly picks, and compete across an 18-week season. The platform handles pick lock enforcement, automated result ingestion from ESPN, billing via Stripe, and transactional email via AWS SES, all deployed on AWS ECS Fargate behind an Application Load Balancer.


## Problem Definitions & Business Context

> **This section is the foundation of the architecture brief.** It grounds all subsequent technical decisions by establishing _why_ the system exists and _what_ problems it solves.

### Problem Statement

Football pool management has historically been manual — spreadsheets, group texts, and honor-system tracking. This creates:

- **No enforcement of pick lock deadlines** — late picks accepted informally
- **No automated result processing** — someone manually updates standings after each game week
- **No scalable entry management** — commissioners with dozens of entries struggle to track eliminations and dues
- **No audit trail** — disputes about who picked what and when are unresolvable

RunMyPool replaces this with an automated platform: picks lock on schedule, ESPN results are ingested automatically, standings update without manual intervention, and every action is logged.

### Business Context

- **Primary Users**: NFL pool commissioners (who pay for the platform) and pool members (who join free)
- **Use Cases**:
  - Create a Survivor pool and invite members
  - Members create entries and submit weekly team picks before the lock deadline
  - System auto-picks for members who miss the deadline
  - Results ingested from ESPN after game completion; surviving entries advance, losing entries are eliminated
  - Commissioner manages dues, admin overrides, and pool configuration
- **Non-Functional Requirements**:
  - Availability: deployed on ECS Fargate with autoscaling; ALB health checks; RDS with CloudWatch alarms
  - Security: bcrypt passwords, JWT HttpOnly cookies, rate-limited login, one-time-use reset tokens, security headers via ASGI middleware
  - Scalability: connection pooling, ECS autoscaling on CPU/memory
  - Auditability: every action written to `audit_logs` table
- **Integration Points**: ESPN public API (NFL schedule/scores), Stripe (billing), AWS SES (transactional email), AWS Secrets Manager (secrets injection), AWS SSM Parameter Store (Lambda idempotency)
- **Monetization**: Four Stripe billing tiers gate pool creation capacity:

  | Plan | Max Entries | Max Pools |
  |---|---|---|
  | Commissioner | 50 | 1 |
  | Pro | 150 | 1 |
  | Club | 500 | 5 |
  | Club Unlimited | Unlimited | Unlimited |


## C4 System Context Diagram

```mermaid
graph TD
    subgraph Users ["👥 Users"]
        COMM["👤 Commissioner<br/>Creates pools, manages members<br/>pays for billing plan"]
        MEMBER["👤 Pool Member<br/>Joins pools, submits picks<br/>tracks survival status"]
        PADMIN["👤 Platform Admin<br/>Super-admin user management<br/>system oversight"]
    end

    subgraph RunMyPool ["📦 RunMyPool Platform"]
        SYSTEM["🎯 RunMyPool<br/>Web Application<br/>Next.js + FastAPI on AWS ECS"]
    end

    subgraph External ["🌐 External Services"]
        ESPN["🏈 ESPN Public API<br/>NFL schedule & scores<br/>site.api.espn.com"]
        STRIPE["💳 Stripe<br/>Billing & payments<br/>Checkout + webhooks"]
        SES["📧 AWS SES<br/>Transactional email<br/>Password reset, invites"]
        SECRETS["🔐 AWS Secrets Manager<br/>DATABASE_URL, JWT secret<br/>Stripe keys"]
        SSM["📋 AWS SSM Parameter Store<br/>Lambda idempotency flag<br/>nfl-games-done-date"]
    end

    COMM -->|HTTPS — pool management| SYSTEM
    MEMBER -->|HTTPS — weekly picks| SYSTEM
    PADMIN -->|HTTPS — admin portal| SYSTEM
    SYSTEM -->|HTTPS GET — scoreboard API| ESPN
    SYSTEM -->|HTTPS — Checkout session, webhook| STRIPE
    STRIPE -->|HTTPS POST webhook| SYSTEM
    SYSTEM -->|HTTPS — send email| SES
    SYSTEM -->|HTTPS — fetch secrets at startup| SECRETS
    SYSTEM -->|HTTPS — idempotency flag| SSM

    classDef user fill:#fff3e0,stroke:#ef6c00,color:#bf360c,stroke-width:2px
    classDef system fill:#e1f5fe,stroke:#0277bd,color:#01579b,stroke-width:2px
    classDef external fill:#f3e5f5,stroke:#7b1fa2,color:#4a148c,stroke-width:2px

    class COMM,MEMBER,PADMIN user
    class SYSTEM system
    class ESPN,STRIPE,SES,SECRETS,SSM external
```


## System Overview

### C4 Container Diagram

```mermaid
graph TD
    subgraph Browser ["🌐 Client Browser"]
        FE_BROWSER["👤 User Browser<br/>PWA — Service Worker cached"]
    end

    subgraph AWS ["☁️ AWS us-east-1"]
        ALB["🔀 Application Load Balancer<br/>HTTPS termination<br/>path-based routing"]

        subgraph ECS ["📦 ECS Fargate Cluster — run-my-pool-cluster"]
            FRONTEND["🖥️ Frontend Service<br/>Next.js 16 / Node 20<br/>0.25 vCPU / 0.5 GB — port 3000"]
            BACKEND["⚙️ Backend Service<br/>FastAPI 0.139 / Python 3.13<br/>0.5 vCPU / 1 GB — port 8000"]
            UPDATER["🔄 Result Updater Task<br/>ECS scheduled task<br/>Python 3.13 — CLI script"]
        end

        subgraph Lambda ["λ Lambda"]
            LAMBDA["λ NFL Game Updater<br/>Python 3.13<br/>EventBridge triggered — legacy"]
        end

        RDS[("💾 Amazon RDS<br/>MySQL 8.x<br/>private subnet")]
        ECR["📦 ECR<br/>Container Registry<br/>10-image retention"]
        SECRETSMGR["🔐 Secrets Manager<br/>DATABASE_URL<br/>JWT_SECRET, Stripe keys"]
        SSM_STORE["📋 SSM Parameter Store<br/>nfl-games-done-date"]
    end

    subgraph External ["🌐 External"]
        ESPN_API["🏈 ESPN API<br/>site.api.espn.com"]
        STRIPE_SVC["💳 Stripe<br/>Checkout + webhooks"]
        SES_SVC["📧 AWS SES<br/>us-east-1"]
    end

    FE_BROWSER -->|HTTPS| ALB
    ALB -->|HTTP /api/* → port 8000| BACKEND
    ALB -->|HTTP /* → port 3000| FRONTEND
    FRONTEND -->|HTTPS REST /api/*| BACKEND
    BACKEND -->|SQL — mysql-connector-python| RDS
    BACKEND -->|HTTPS — SES send_email| SES_SVC
    BACKEND -->|HTTPS — Checkout, webhook verify| STRIPE_SVC
    BACKEND -->|HTTPS — get-secret-value| SECRETSMGR
    UPDATER -->|SQL — mysql-connector-python| RDS
    UPDATER -->|HTTPS GET — scoreboard| ESPN_API
    UPDATER -->|HTTPS — get-secret-value| SECRETSMGR
    LAMBDA -->|SQL| RDS
    LAMBDA -->|HTTPS GET — scoreboard| ESPN_API
    LAMBDA -->|HTTPS — get-parameter| SSM_STORE

    classDef frontend fill:#e8f5e9,stroke:#388e3c,color:#1b5e20,stroke-width:2px
    classDef backend fill:#e1f5fe,stroke:#0277bd,color:#01579b,stroke-width:2px
    classDef database fill:#fce4ec,stroke:#d81b60,color:#880e4f,stroke-width:2px
    classDef infra fill:#f3e5f5,stroke:#7b1fa2,color:#4a148c,stroke-width:2px
    classDef external fill:#fff8e1,stroke:#f9a825,color:#e65100,stroke-width:2px
    classDef user fill:#fff3e0,stroke:#ef6c00,color:#bf360c,stroke-width:2px

    class FRONTEND frontend
    class BACKEND,UPDATER,LAMBDA backend
    class RDS database
    class ALB,ECR,SECRETSMGR,SSM_STORE infra
    class ESPN_API,STRIPE_SVC,SES_SVC external
    class FE_BROWSER user
```

### C4 Container Diagram Explanation

The platform is a standard three-tier web application deployed on AWS ECS Fargate.

**ALB** terminates HTTPS and routes traffic by path: API calls (`/api/*`) go to the FastAPI backend on port 8000; all other paths go to the Next.js frontend on port 3000.

**Frontend** (`Next.js 16 / React 19`) renders server-side and client-side pages. It is packaged as a PWA with a Workbox-based service worker for offline capability. The frontend makes authenticated REST calls to the backend using the JWT stored in an HttpOnly cookie.

**Backend** (`FastAPI / Python 3.13`) is the sole application server. It handles authentication (JWT, bcrypt), business logic (pool management, pick locking, entitlement gating), and all database writes. A background async task (`_weekly_lock_worker`) polls every 60 seconds to enforce pick lock schedules. The backend uses SQLAlchemy + mysql-connector-python to talk to RDS.

**Result Updater** is an ECS-scheduled task (and legacy Lambda) that fetches NFL game results from the ESPN public API and reconciles pick outcomes and Survivor eliminations in the database. The ECS task uses a MySQL advisory lock for safe concurrent execution. The Lambda variant is in transition to retirement.

**RDS (MySQL 8.x)** is the single data store for all application state. It lives in a private subnet, accessible only from within the VPC.

**Secrets Manager** injects `DATABASE_URL`, `JWT_SECRET`, and Stripe API keys into ECS task environments at startup — never baked into images.

#### Request Flow Sequence

The most critical flow is a member submitting a weekly pick before the lock deadline.

```mermaid
sequenceDiagram
    actor Member
    participant FE as Next.js Frontend<br/>port 3000
    participant ALB as Application<br/>Load Balancer
    participant BE as FastAPI Backend<br/>port 8000
    participant DB as RDS MySQL

    Member->>FE: Selects team for Week N
    FE->>ALB: POST /api/picks/ HTTPS<br/>Cookie: session_jwt=...
    ALB->>BE: POST /picks/ HTTP
    BE->>BE: Validate JWT from HttpOnly cookie
    BE->>DB: SELECT entry, existing picks for entry_id
    DB-->>BE: Entry rows, prior picks
    BE->>BE: Check pick lock — is week N locked?
    alt Week is locked
        BE-->>FE: 400 Bad Request — pick is locked
        FE-->>Member: Error: pick deadline has passed
    else Week is open
        BE->>BE: Validate team not already picked this entry
        BE->>DB: INSERT INTO picks — upsert on entry_id+week+game_id
        DB-->>BE: Pick saved
        BE-->>FE: 200 OK — pick confirmed
        FE-->>Member: Pick saved confirmation
    end
```

### Technology Stack

**Runtime & Languages:**

- Python 3.13 — backend and result updater
- Node.js 20 — frontend build and runtime
- Next.js 16.3.0 — frontend framework (SSR + SSG)
- React 19.2.8 — frontend UI library
- FastAPI 0.139.2 — backend REST framework (ASGI)
- Pydantic v2 (2.13.4) — request/response validation and serialization
- SQLAlchemy — ORM (async-compatible sessions)
- Alembic 1.16.5 — database migrations

**Data Storage:**

- Amazon RDS MySQL 8.x — primary application database (production)
- SQLite (in-memory) — test database

**Infrastructure:**

- AWS ECS Fargate — container runtime for frontend, backend, result updater
- AWS Application Load Balancer — HTTPS termination, path-based routing
- AWS Lambda — legacy NFL result updater (EventBridge triggered)
- AWS ECR — container image registry (10-image retention policy)
- Terraform — infrastructure as code (ECS, ALB, RDS alarms, SES, Lambda)
- GitHub Actions — CI/CD pipelines for backend, frontend, Lambda

**Monitoring & Security:**

- AWS CloudWatch — ECS and RDS logs, RDS alarms
- bcrypt via passlib — password hashing
- PyJWT — JWT HS256 token issuance (24-hour expiry)
- ASGI security middleware — CSP, HSTS, X-Frame-Options, X-Content-Type-Options, Referrer-Policy, Permissions-Policy
- Codecov — backend test coverage reporting


## System Data Models

### Data Model ER Diagram

```mermaid
erDiagram
    User {
        string id PK "UUID"
        string email UK "normalized, unique"
        string hashed_password "bcrypt"
        string role "USER / POOL_ADMIN / SUPER_ADMIN"
        boolean email_verified
        boolean mfa_enabled
    }

    Pool {
        string id PK "UUID"
        string name UK
        string pool_type "survivor / pickem"
        string owner_id FK
        string entitlement_id FK
        boolean is_private
        string join_password_hash
        datetime lock_datetime
        string lock_day_of_week
        string lock_time_of_day
        string lock_timezone
        datetime join_lock_time
    }

    Entry {
        string id PK "UUID"
        string user_id FK
        string pool_id FK
        string name
        boolean alive "Survivor elimination flag"
    }

    Pick {
        string id PK "UUID"
        string entry_id FK
        int week "1-18"
        string team_abbrev
        int team_id FK
        int game_id FK
        boolean locked
        string result "win / loss / pending"
    }

    Schedule {
        int game_id PK
        int season
        int week_num
        int home_team_id FK
        int away_team_id FK
        datetime start_time
        string status
        int home_score
        int away_score
        int winning_team_id FK
    }

    Team {
        int id PK
        string name
        string abbreviation UK
        string logo_url
    }

    PoolMember {
        string user_id FK
        string pool_id FK
        datetime joined_at
        boolean dues_paid
    }

    PoolAdmin {
        string user_id FK
        string pool_id FK
    }

    PoolRule {
        string id PK
        string pool_id FK
        string rule_id FK
    }

    Rule {
        string id PK
        string name
        string pool_type
        string description
    }

    AuditLog {
        string id PK
        string user_id FK
        string action
        string details "JSON"
        datetime timestamp
    }

    CommissionerEntitlement {
        string id PK
        string user_id FK
        string plan
        int season
        datetime granted_at
    }

    BillingOrder {
        string id PK
        string user_id FK
        string stripe_session_id UK
        string plan
        string status
        datetime paid_at
    }

    MessageBoard {
        string id PK
        string pool_id FK
        string user_id FK
        string content "max 250 chars"
        datetime created_at
    }

    PoolGameLine {
        string id PK
        string pool_id FK
        int game_id FK
        float spread "frozen at pick-lock time"
    }

    User ||--o{ Pool : "owns"
    User ||--o{ Entry : "has"
    User ||--o{ PoolMember : "joins"
    User ||--o{ PoolAdmin : "administers"
    User ||--o{ AuditLog : "generates"
    User ||--o{ CommissionerEntitlement : "holds"
    User ||--o{ BillingOrder : "places"
    User ||--o{ MessageBoard : "posts"
    Pool ||--o{ Entry : "contains"
    Pool ||--o{ PoolMember : "has"
    Pool ||--o{ PoolAdmin : "has"
    Pool ||--o{ PoolRule : "has"
    Pool ||--o{ MessageBoard : "has"
    Pool ||--o{ PoolGameLine : "has"
    Entry ||--o{ Pick : "has"
    Pick }o--|| Team : "picks"
    Pick }o--|| Schedule : "references"
    Schedule }o--|| Team : "home team"
    Schedule }o--|| Team : "away team"
    Rule ||--o{ PoolRule : "applied via"
    CommissionerEntitlement ||--o{ Pool : "enables"
```

### Data Model Explanation

The data model is organized around five core entities:

**User** is the root identity. A user can own pools (Commissioner role), join pools as a member, or hold super-admin privileges. Passwords are bcrypt-hashed and never stored in plaintext (a known bug exists in one admin endpoint).

**Pool** represents a football pool. Its `pool_type` determines the game format (`survivor` or `pickem`). Pools have configurable pick lock schedules — either a fixed `lock_datetime` or a recurring `lock_day_of_week` + `lock_time_of_day` + `lock_timezone`. A pool is gated by a `CommissionerEntitlement` that limits how many pools and entries the owner can create.

**Entry** is a user's participation slot in a pool. A user may have multiple entries. In Survivor format, `alive=False` marks elimination. Entries lock at the pool-level `join_lock_time`, preventing new entries mid-season.

**Pick** is a single weekly team selection within an entry. The unique constraint on `(entry_id, week, game_id)` prevents duplicate picks. The `result` field is updated by the result updater after ESPN confirms game outcomes. `locked=True` prevents further changes.

**Schedule** / **Team** provide the NFL data layer. `Schedule` rows are imported from ESPN and indexed heavily for query performance (by season+week, by team, by start_time). `PoolGameLine` freezes point spreads at pick-lock time for future Pick'em scoring support.

**Supporting entities:**
- `PoolMember` / `PoolAdmin` — join tables for membership and admin assignment
- `AuditLog` — append-only action log with JSON `details` for every significant operation
- `CommissionerEntitlement` + `BillingOrder` — Stripe billing lifecycle; entitlements are the governing record for pool creation limits
- `MessageBoard` — pool-scoped chat with 250-char limit and rate limiting enforced at the API layer
- `UpdaterRun` — durable execution record for the ECS result updater to prevent duplicate processing
- `StripeWebhookEvent` — idempotency guard for Stripe webhook replay
- `UsedPasswordResetToken` — SHA-256 digests of consumed tokens for one-time-use enforcement
- `LoginAttempt` — rate-limiting table; cleared on successful login


## API Endpoints

### Auth — `/auth`

**Public API Endpoints:**

| Method | Path | Description |
|---|---|---|
| `POST` | `/auth/register` | Create account — bcrypt hash, email normalization, audit log |
| `POST` | `/auth/login` | Authenticate — returns JWT as HttpOnly Secure SameSite=Lax cookie; rate-limited 5 attempts / 15 min per email |
| `POST` | `/auth/logout` | Clear session cookie |
| `GET` | `/auth/me` | Return current authenticated user |
| `POST` | `/auth/forgot-password` | Send SES password reset email (opaque response — no user enumeration) |
| `POST` | `/auth/reset-password` | Token-validated password reset; token consumed via SHA-256 digest |

### Users — `/users`

**Internal API Endpoints:**

| Method | Path | Description |
|---|---|---|
| `GET` | `/users/` | List users — **known gap: publicly accessible, user enumeration risk** |
| `GET` | `/users/{id}` | Get user by ID |
| `DELETE` | `/users/{id}` | Delete user |
| `PATCH` | `/users/{id}/email` | Update user email |
| `PATCH` | `/users/{id}/password` | Admin password reset — **known bug: stores plaintext** |

### Pools — `/pools`

**Public API Endpoints:**

| Method | Path | Description |
|---|---|---|
| `POST` | `/pools/` | Create pool (Commissioner role; entitlement-gated) |
| `GET` | `/pools/` | Get current user's pools |
| `GET` | `/pools/{id}` | Get pool by ID |
| `PATCH` | `/pools/{id}` | Update pool settings (owner or admin) |
| `DELETE` | `/pools/{id}` | Delete pool (owner only) |
| `POST` | `/pools/{id}/join` | Join pool — optional password for private pools |
| `POST` | `/pools/{id}/invite` | Send SES email invite to prospective member |
| `GET` | `/pools/{id}/invite-info` | Get invite preview (public — for invite link landing) |
| `GET` | `/pools/{id}/check-admin` | Check whether current user has admin access |

### Entries — `/entries`

**Public API Endpoints:**

| Method | Path | Description |
|---|---|---|
| `POST` | `/entries/` | Create entry in pool — HTTP 423 if pool join-lock has passed |
| `GET` | `/entries/{id}` | Get entry |
| `PATCH` | `/entries/{id}` | Update entry name |
| `DELETE` | `/entries/{id}` | Delete entry — HTTP 423 if pool join-lock has passed |

### Picks — `/picks`

**Public API Endpoints:**

| Method | Path | Description |
|---|---|---|
| `POST` | `/picks/` | Create or upsert pick for week — HTTP 400 if week is locked |
| `GET` | `/picks/entry/{entry_id}` | Get all picks for an entry |
| `PATCH` | `/picks/{id}` | Update pick — HTTP 400 if pick is locked |
| `DELETE` | `/picks/{id}` | Delete pick — HTTP 400 if pick is locked |

### Admin

**Internal API Endpoints (pool-scoped):**

| Method | Path | Description |
|---|---|---|
| `POST` | `/admin/transfer-entry` | Transfer entry ownership to another user |
| `DELETE` | `/admin/entries/{id}` | Delete any entry in pool |
| `POST` | `/admin/lock-week/{week}` | Lock a week and auto-pick all entries missing a pick |
| `PATCH` | `/admin/picks/{id}` | Override any pick — locked or unlocked |
| `GET` | `/admin/members` | List pool members |
| `PATCH` | `/admin/members/{user_id}/dues` | Update dues paid status |
| `POST` | `/admin/members/{user_id}/lock` | Lock (suspend) a user within a pool |
| `POST` | `/admin/members/{user_id}/unlock` | Unlock a suspended user |
| `GET` | `/admin/user-overview` | League admin user summary |
| `GET` | `/admin/auto-pick-report` | Auto-pick audit report |
| `GET` | `/admin/admins` | List pool admins |
| `PATCH` | `/admin/admins` | Assign or revoke pool admin role |
| `POST` | `/admin/transfer-ownership` | Transfer pool ownership to another user |

### Schedule & Teams

**Public API Endpoints:**

| Method | Path | Description |
|---|---|---|
| `GET` | `/schedule/` | All NFL schedule entries |
| `GET` | `/schedule/week/{week_num}` | Games for a specific week |
| `GET` | `/schedule/teams/{week_num}` | Teams playing in a given week |
| `GET` | `/teams/` | List all NFL teams |
| `GET` | `/rules/` | List available pool rule types |

### Billing — `/billing`

**Public API Endpoints:**

| Method | Path | Description |
|---|---|---|
| `POST` | `/billing/checkout` | Create Stripe Checkout session for a billing plan |
| `POST` | `/billing/webhook` | Stripe webhook handler — idempotent via `StripeWebhookEvent` table |
| `GET` | `/billing/overview` | User's billing history and active entitlement |
| `GET` | `/billing/success` | Post-payment confirmation page data |

### Message Board — `/message-board`

**Public API Endpoints:**

| Method | Path | Description |
|---|---|---|
| `GET` | `/message-board/{pool_id}` | List pool messages — pool members only |
| `POST` | `/message-board/` | Post message — rate-limited 5 posts / 10 min per user per pool; max 250 chars |
| `DELETE` | `/message-board/{id}` | Delete own message |

### Audit & Analytics

**Internal API Endpoints:**

| Method | Path | Description |
|---|---|---|
| `GET` | `/audit/` | Search audit logs — filter by user_id, date range, action text |
| `GET` | `/audit/filter-options` | Available filter values for the audit search UI |
| `POST` | `/analytics/lifecycle` | Record user lifecycle funnel events |

### Platform Admin — `/platform-admin`

**Internal API Endpoints (super-admin only):**

| Method | Path | Description |
|---|---|---|
| `GET` | `/platform-admin/users` | List all users with pool counts |
| `PATCH` | `/platform-admin/users/{id}/lock` | Lock a user account platform-wide |
| `PATCH` | `/platform-admin/users/{id}/role` | Assign or revoke roles |

### Health

**Backend:**

| Method | Path | Description |
|---|---|---|
| `GET` | `/` | Welcome message |
| `GET` | `/health` | `{"status": "healthy"}` — ALB health check target |

**Frontend (Next.js API routes):**

| Method | Path | Description |
|---|---|---|
| `GET` | `/api/health` | `{status: "healthy", service: ..., timestamp: ...}` |
| `GET` | `/api/live` | Liveness probe |
| `GET` | `/api/ready` | Readiness probe |


## Deployment Architecture

All resources deploy to **AWS us-east-1**. VPC, subnets, IAM roles, RDS instance, and ECR repositories are pre-existing; the Terraform in this repo manages ECS cluster, ECS services, ALB configuration, SES, CloudWatch alarms, and the Lambda function.

```mermaid
graph TD
    subgraph Internet ["🌐 Internet"]
        CLIENT["👤 Browser / PWA"]
    end

    subgraph AWS ["☁️ AWS us-east-1"]
        subgraph Public ["Public Subnets"]
            ALB_NODE["🔀 ALB<br/>HTTPS :443<br/>SSL termination"]
        end

        subgraph Private ["Private Subnets"]
            subgraph ECS_CLUSTER ["📦 ECS Fargate Cluster<br/>run-my-pool-cluster"]
                FE_TASK["🖥️ Frontend Tasks<br/>Next.js — port 3000<br/>0.25 vCPU / 0.5 GB<br/>autoscaling on CPU"]
                BE_TASK["⚙️ Backend Tasks<br/>FastAPI — port 8000<br/>0.5 vCPU / 1 GB<br/>autoscaling on CPU + mem"]
                UP_TASK["🔄 Result Updater<br/>ECS scheduled task<br/>Python CLI — runs on schedule"]
            end
            RDS_NODE[("💾 RDS MySQL 8.x<br/>private subnet<br/>CloudWatch alarms")]
        end

        ECR_NODE["📦 ECR<br/>frontend:sha, backend:sha<br/>10-image retention"]
        SECRETS_NODE["🔐 Secrets Manager<br/>DB URL, JWT, Stripe"]
        CW["📊 CloudWatch<br/>ECS logs, RDS alarms"]
    end

    subgraph External ["🌐 External"]
        ESPN_EXT["🏈 ESPN API"]
        STRIPE_EXT["💳 Stripe"]
        SES_EXT["📧 AWS SES"]
    end

    CLIENT -->|HTTPS :443| ALB_NODE
    ALB_NODE -->|HTTP :3000| FE_TASK
    ALB_NODE -->|HTTP :8000| BE_TASK
    FE_TASK -->|HTTPS REST| BE_TASK
    BE_TASK -->|SQL TCP :3306| RDS_NODE
    UP_TASK -->|SQL TCP :3306| RDS_NODE
    UP_TASK -->|HTTPS GET| ESPN_EXT
    BE_TASK -->|HTTPS| STRIPE_EXT
    BE_TASK -->|HTTPS| SES_EXT
    BE_TASK -->|HTTPS| SECRETS_NODE
    UP_TASK -->|HTTPS| SECRETS_NODE
    FE_TASK -->|pull image| ECR_NODE
    BE_TASK -->|pull image| ECR_NODE
    UP_TASK -->|pull image| ECR_NODE
    FE_TASK -.->|logs| CW
    BE_TASK -.->|logs| CW
    UP_TASK -.->|logs| CW
    RDS_NODE -.->|alarms| CW

    classDef frontend fill:#e8f5e9,stroke:#388e3c,color:#1b5e20,stroke-width:2px
    classDef backend fill:#e1f5fe,stroke:#0277bd,color:#01579b,stroke-width:2px
    classDef database fill:#fce4ec,stroke:#d81b60,color:#880e4f,stroke-width:2px
    classDef infra fill:#f3e5f5,stroke:#7b1fa2,color:#4a148c,stroke-width:2px
    classDef external fill:#fff8e1,stroke:#f9a825,color:#e65100,stroke-width:2px
    classDef user fill:#fff3e0,stroke:#ef6c00,color:#bf360c,stroke-width:2px

    class FE_TASK frontend
    class BE_TASK,UP_TASK backend
    class RDS_NODE database
    class ALB_NODE,ECR_NODE,SECRETS_NODE,CW infra
    class ESPN_EXT,STRIPE_EXT,SES_EXT external
    class CLIENT user
```

**CI/CD Pipeline (GitHub Actions):**

| Trigger | Pipeline | Steps |
|---|---|---|
| Push to `rmp/backend/**` | `build-backend.yml` | pytest (SQLite) → MySQL integration tests → Docker smoke test → ECR push → ECS force-deploy |
| Push to `rmp/frontend/**` | `build-frontend.yml` | Jest + lint + build → npm audit → ECR push → ECS force-deploy |
| Push to `lambda/**` | `deploy-lambda.yml` | pytest → pip-audit → Terraform apply |

**Known Technical Debt:**

| Issue | Severity |
|---|---|
| `GET /users/` is publicly accessible — user enumeration risk | High |
| `PATCH /users/{id}/password` stores plaintext password | Critical |
| `user_id: int` type mismatch — User.id is UUID string | Medium |
| No JWT refresh / expiry handling in frontend auth context | Medium |
| Lambda result updater lacks VPC connectivity | Operational |
| Lambda and ECS result updater must not run concurrently | Operational |

---

## Document Metadata

| Field | Value |
|---|---|
| Repository | `run-my-pool` |
| Generated | 2026-08-13 |
| Backend version | FastAPI 0.139.2 / Python 3.13 |
| Frontend version | Next.js 16.3.0 / React 19.2.8 |
| Database | MySQL 8.x (Amazon RDS) |
| Infrastructure | AWS ECS Fargate, us-east-1 |
| Migrations | 15 Alembic revisions |
| Test coverage | 298 backend tests, 64 frontend tests |
