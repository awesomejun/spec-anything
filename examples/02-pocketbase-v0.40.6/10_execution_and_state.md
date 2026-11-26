# 10 Execution & State Transition Diagrams

All diagrams follow the **Structure-Only Mermaid Contract** (no hardcoded node colors, `style fill:`, or `classDef` color literals) so they render cleanly in light and dark themes.

## 1. End-to-End Write, Persistence & Realtime SSE Broadcast (`F-007`, `F-009`, `F-012`)
Cited from `[REF: apis/record_crud.go:195-260]`, `[REF: apis/realtime.go:32-190]`, and `[REF: core/db.go:1-120]`.

```mermaid
sequenceDiagram
    participant Client as API or Admin UI Client
    participant Router as HTTP Router and Middlewares
    participant CRUD as Record CRUD Handler
    participant DB as SQLite WAL data.db
    participant Broker as SSE Realtime Broker

    Client->>Router: GET /api/realtime
    Router->>Broker: Register clientId channel
    Broker-->>Client: SSE event PB_CONNECT (clientId)
    Client->>Router: POST /api/realtime (subscriptions articles/*)
    Router->>Broker: Bind topic filter
    Broker-->>Client: HTTP 204 No Content

    Client->>Router: POST /api/collections/articles/records
    Router->>CRUD: loadAuthToken + rule evaluation
    CRUD->>CRUD: Validate fields (ozzo-validation)
    alt Validation fails
        CRUD-->>Client: HTTP 400 validation_min_text_constraint
    else Valid payload
        CRUD->>DB: INSERT INTO articles (WAL txn)
        alt Unique index violation
            DB-->>CRUD: SQLITE_CONSTRAINT_UNIQUE
            CRUD-->>Client: HTTP 400 validation_not_unique
        else Commit succeeds
            DB-->>CRUD: Row persisted (15-char id)
            CRUD->>Broker: OnRecordAfterCreateSuccess
            Broker-->>Client: SSE event articles/* (action=create)
            CRUD-->>Client: HTTP 200 persisted record JSON
        end
    end
```

## 2. Server Process Lifecycle & Restart Durability State Machine (`F-002`, `F-010`, `F-011`, `F-012`)
Cited from `[REF: cmd/serve.go:14-45]` and `[REF: apis/backup.go:18-130]`.

```mermaid
stateDiagram-v2
    [*] --> Bootstrapping: pocketbase serve --dir
    Bootstrapping --> WALReady: Open data.db (PRAGMA journal_mode=wal)
    WALReady --> Serving: Bind 127.0.0.1 HTTP listener
    Serving --> BackupSnapshot: POST /api/backups
    BackupSnapshot --> Serving: Archive written to pb_data/backups
    Serving --> Stopping: SIGTERM received
    Stopping --> Checkpointed: Flush WAL and close listeners
    Checkpointed --> Bootstrapping: Relaunch on new port with same --dir
    Checkpointed --> [*]
```

## 3. Superuser Authentication State Transitions (`F-004`, `F-005`)
Cited from `[REF: ui/src/auth/pageSuperuserLogin.js:1-120]` and `[REF: apis/record_auth_with_password.go:15-105]`.

```mermaid
stateDiagram-v2
    [*] --> Unauthenticated: Visit /_/
    Unauthenticated --> LoadingAuthMethods: GET /auth-methods
    LoadingAuthMethods --> PasswordForm: password.enabled=true
    PasswordForm --> AuthErrorToast: POST auth-with-password -> HTTP 400
    AuthErrorToast --> PasswordForm: Retry with valid credentials
    PasswordForm --> AuthenticatedSession: HTTP 200 (JWT issued)
    AuthenticatedSession --> Unauthenticated: Token cleared or expired (HTTP 401)
```

## Sources Read
- `apis/record_crud.go`
- `apis/realtime.go`
- `apis/record_auth_with_password.go`
- `apis/backup.go`
- `cmd/serve.go`
- `core/db.go`
- `ui/src/auth/pageSuperuserLogin.js`
