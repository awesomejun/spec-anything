# 04 Reproduction Environment & REA Release Audit

Machine-readable audit record: `04_environment/release_audit.json`. Licensing & UI asset boundaries: `04_environment/LICENSING.md`.

## 1. Pinned Upstream Source & Official Release Artifact
| Attribute | Verified Value |
|---|---|
| Upstream Repository | `https://github.com/pocketbase/pocketbase` |
| Tag / Commit SHA | `v0.40.6` / `9d281ccaba65f2686eb7b0b614ccda72d1116a1b` |
| Upstream License | MIT (`LICENSE.md`) |
| Official Release Archive | `pocketbase_0.40.6_darwin_arm64.zip` (`12,235,482` bytes) |
| Archive SHA-256 | `7f2f7544e9ee5994ab69f84b22a4ab9a3bcfed58c1dad7206d05ebeb753f968b` (**matched upstream `checksums.txt`**) |
| Extracted Binary | `pocketbase` (`32,397,138` bytes, `Mach-O 64-bit executable arm64`) |
| Binary SHA-256 | `d313ba59879e96a5ab566c6763f4ae9b63dc62e9fee78782276407808905d54f` |

## 2. REA Release-to-Source Verification Findings (`F-014`)
Executed via `scripts/inspect_release.py` (`go version -m`, `otool -L`, `codesign -dv`, raw binary probes):
- **Compiler & Flags**: `go1.27.3`, `GOOS=darwin`, `GOARCH=arm64`, `CGO_ENABLED=0`, `-ldflags="-s -w -X github.com/pocketbase/pocketbase.Version=0.40.6"`.
- **Provenance Match**: Embedded Go VCS metadata reports `vcs.revision=9d281ccaba65f2686eb7b0b614ccda72d1116a1b`, `vcs.modified=false`, `vcs.time=2026-10-23T10:44:14Z`—cryptographically confirming clean build provenance from tag `v0.40.6`.
- **Entrypoint Confirmation**: Compiled main package is `github.com/pocketbase/pocketbase/examples/base` (`examples/base/main.go`), bundling `goja` JS hooks, migrations (`--migrationsDir`), and the embedded Admin UI SPA (`index.html`, `/_/`).
- **Dynamic Dependencies**: Only 4 macOS system libraries (`libSystem.B.dylib`, `libresolv.9.dylib`, `CoreFoundation`, `Security`), confirming pure-Go SQLite (`modernc.org/sqlite`).
- **Code Signature**: `Mach-O thin (arm64)`, `Signature=adhoc`, `TeamIdentifier=not set`.

## 3. Isolated Execution Environment & Synthetic Fixtures
- **Host OS & Tools**: macOS Darwin arm64, Python 3.13, Playwright Chromium, SQLite 3, `otool`, `codesign`, `go`.
- **Isolation Rule**: Every run isolates `--dir=<temp>/pb_data`, `--migrationsDir=<temp>/pb_migrations`, and binds loopback `127.0.0.1:<ephemeral_port>`. Note: isolating `--migrationsDir` prevents PocketBase's `automigrate` plugin from leaking schema migrations across repeated runs.
- **Synthetic Seed Data**:
  - Superuser: `admin@example.com` / synthetic local password (never a real credential).
  - Collection: `articles` (`title` text min 3 max 120 required, `slug` text min 2 max 64 unique, `published` bool, `views` number >= 0).
  - Records: `alpha` (`views=42`, `published=true`), `beta` (`views=7`, `published=false`), `gamma` (`views=100`, `published=true`), `realtime-1` (`views=99`, `published=true`).
- **External Service Doubles**: SMTP, S3 storage, and external OAuth2 providers remain disabled in the offline isolated harness; affected flows (`F-018`) are explicitly marked `code-verified` rather than falsely claiming live external verification.
