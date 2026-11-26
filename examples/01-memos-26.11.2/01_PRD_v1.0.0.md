# 01. PRD — `usememos/memos` 26.11.2 재구현 제품 요구사항 정의서 v1.0.0

- **대상 오픈소스**: `usememos/memos` (MIT License, GitHub ~64.7k stars)
- **기준 릴리스 / 커밋**: 태그 `26.11.2` · 커밋 `00fcd170281a75fc0e95ec4f2f54f43d32fe81bd`
- **관찰 등급**: Tier 3 (정적 소스 + 공식 `darwin_arm64` 배포본 REA 대조 + 격리 실행 + UI 8상태 촬영 + 대조 테스트 통과)
- **기능 마스터 참조**: 모든 요구사항은 `03_재현_범위표_v1.0.0.md`의 `F-001`~`F-012` 단일 기능 ID로 추적됩니다.

---

## 1. 제품 목표 및 사용자 페르소나

`usememos/memos`는 외부 클라우드 의존 없이 단일 바이너리와 로컬 데이터베이스(SQLite 기본)로 자가 호스팅(Self-hosted)할 수 있는 경량 타임라인형 Markdown 메모 애플리케이션입니다 (`[REF: cmd/memos/main.go:1-60]`, `[REF: server/server.go:1-90]`).

| 페르소나 | 핵심 목표 | 관련 기능 ID |
| :--- | :--- | :--- |
| **호스트 관리자 (Host Admin)** | 초기 구동 직후 첫 계정으로 인스턴스를 소유하고, 메모 작성·고정·보관·공유·데이터 영속성을 완전 통제 | `F-002`, `F-004`, `F-005`, `F-006`, `F-007`, `F-008`, `F-009`, `F-010` |
| **일반 인증 사용자 (Authenticated User)** | 개인(`PRIVATE`)·보호(`PROTECTED`)·공개(`PUBLIC`) 메모를 Markdown과 `#tag`로 기록하고 CEL 필터로 즉시 검색 | `F-005`, `F-006`, `F-007`, `F-008`, `F-009`, `F-011` |
| **비인증 방문자 (Anonymous Guest)** | 공개 타임라인(`/explore`)과 공개 메모 상세 페이지, 또는 유효한 공유 링크(`/memos/shares/:token`)가 부여된 메모만 읽기 전용으로 열람 | `F-001`, `F-003`, `F-009`, `F-011` |

---

## 2. 핵심 사용자 흐름 및 기능 요구사항 (기능 ID 매핑)

### 2.1 부트스트랩·인증·접근 제어 (`F-001`~`F-005`)
1. **임베디드 SPA 및 정적 캐시 정책 (`F-001`) `[observed]`**
   - 배포 바이너리는 `/` 요청에 대해 컴파일된 React SPA HTML을 `Cache-Control: no-cache, no-store, must-revalidate` 헤더로 응답해야 합니다 (`[REF: server/frontend/frontend.go:22-119]`).
   - `/assets/*` 해시 에셋은 장기 불변 캐시(`public, max-age=2592000, immutable`)를 적용하며, `/api/*`·`/file/*`·`/.well-known/*`·`/memos.api.*` 네임스페이스는 정적 파일 폴백으로 가로채지 않고 백엔드 핸들러로 전달합니다 (`[REF: server/frontend/frontend.go:88-100]`).
2. **인스턴스 초기화 상태 확인 및 최초 호스트 온보딩 (`F-002`, `F-004`) `[observed]`**
   - 비인증 상태에서 `GET /api/instance/profile`을 호출해 `needsSetup: true` 여부와 `accessMode`(기본값 `PRIVATE`)를 판별합니다 (`[REF: server/api/instance_service.go:43-75]`). `admin` 필드는 비인증 호출자에게 노출되지 않습니다.
   - 사용자 테이블이 비어 있는 상태에서 `POST /api/users`로 생성된 최초 계정은 `ADMIN` 역할을 획득하며, 응답 JSON의 `password` 필드는 평문을 반환하지 않고 빈 문자열(`""`)로 직렬화됩니다 (`[REF: proto/api/user_service.proto:45-51]`, `EV-004`).
3. **비인증 경계 차단 및 세션 회전 (`F-003`, `F-005`) `[observed]`**
   - `PublicMethods` 외의 모든 RPC/REST 엔드포인트는 비인증 요청을 `401 Unauthorized`(`code: 16`)로 거부합니다 (`[REF: server/api/acl_config.go:11-56]`).
   - 잘못된 비밀번호 로그인은 `400 Bad Request`(`codes.InvalidArgument`)를 반환합니다 (`[REF: server/api/auth_service.go:80-86]`).
   - Connect-RPC(`POST /memos.api.AuthService/SignIn`)는 `HeaderCarrier`를 통해 단기 JWT `accessToken`과 `HttpOnly` Refresh 쿠키를 동시에 발급하며, `RefreshToken`으로 회전하고 `SignOut`으로 즉시 폐기합니다. 반면 gRPC-Gateway REST(`POST /api/auth/signin`)는 `accessToken`만 본문으로 반환하고 HTTP `Set-Cookie` 헤더를 내리지 않습니다 (`[REF: server/api/header_carrier.go:75-87]`, `EV-005`).

### 2.2 메모 생명주기·검색·가시성·공유 (`F-006`~`F-009`)
1. **메모 생성 및 고정 규약 (`F-006`) `[observed]`**
   - `POST /api/memos`는 Markdown 본문에서 `#tag`를 자동 추출하고 기본 상태 `NORMAL`로 저장합니다. 생성 요청 본문에 `pinned: true`가 들어와도 **생성 시점에는 무시되어 `pinned: false`로 저장**됩니다 (`[REF: proto/api/memo_service.proto:38-44]`).
2. **수정·고정·보관·삭제 (`F-007`) `[observed]`**
   - `PATCH /api/memos/{uid}?updateMask=...`로 본문 수정, 체크리스트(`- [x]`) 파싱(`property.hasTaskList`), 고정(`pinned: true`), 보관(`state: ARCHIVED`) 전이를 수행합니다 (`[REF: proto/api/memo_service.proto:48-54]`).
   - `DELETE /api/memos/{uid}` 수행 후 동일 리소스 `GET` 요청은 `404 Not Found`를 반환해야 합니다 (`[REF: proto/api/memo_service.proto:59-61]`).
3. **CEL 필터 검색 및 와일드카드 안전성 (`F-008`) `[observed]`**
   - `GET /api/memos?filter=...`는 CEL 식(`tag in ["release"]`, `content.contains("50%_off")`)을 SQL로 컴파일합니다. SQL `LIKE` 메타문자(`%`, `_`)는 리터럴로 이스케이프되어 `50%_off`가 `50X_off`와 오매칭되지 않아야 하며, 미정의 필드 식(`invalid_field == 123`)은 `400 Bad Request`를 반환합니다 (`[REF: filter/engine_test.go:171-205]`).
4. **가시성 격리 및 공유 토큰 (`F-009`) `[observed]`**
   - 기본 `accessMode=PRIVATE` 상태에서는 비인증 `GET /api/memos` 및 `GET /api/memos/{uid}`가 `401 Unauthorized`로 거부되고, 브라우저 `/explore` 접근도 `/auth?redirect=%2Fexplore`로 리다이렉트되며 `/robots.txt`도 `404`를 반환합니다(`EV-001`, `EV-009`, `UI-07`).
   - 그럼에도 소유자가 `POST /api/memos/{uid}/shares`로 발급한 공유 토큰을 사용하면 `AuthBootstrapMethods` 규약에 따라 비인증 사용자도 `GET /api/shares/{token}/memo`로 해당 `PRIVATE` 메모를 `200 OK` 읽기 전용으로 열람할 수 있습니다 (`[REF: proto/api/memo_service.proto:135-154]`, `[REF: server/api/acl_config.go:63-80]`).

### 2.3 영속성·UI·외부 확장 경계 (`F-010`~`F-012`)
- **재시작 영속성 (`F-010`) `[observed]`**: SQLite 스키마 기반 저장 데이터(사용자, 일반/고정/보관 메모, 공유 토큰)는 프로세스 `SIGTERM` 종료 후 재기동해도 손실 없이 복구되어야 합니다 (`[REF: store/migration/sqlite/LATEST.sql:1-145]`).
- **반응형 SPA 화면 (`F-011`) `[observed]`**: 데스크톱(`1440x900`) 및 모바일(`390x844`) 뷰포트에서 온보딩, 빈 상태, 목록, 필터, 상세, 보관함, 비인증 탐색 화면이 깨짐 없이 렌더링되어야 합니다 (`05_원본_UI_기준_자료_v1.0.0.md`, `11_UI_구현_자료_v1.0.0.md` 참조).
- **외부 연동 경계 (`F-012`) `[code-verified]`**: OAuth2 SSO, S3 스토리지, SMTP 알림, AI 서비스, MySQL/PostgreSQL 드라이버는 소스·프로토콜 수준으로만 확인되며 오프라인 단독 재현에서는 테스트 대역 분리가 필수입니다.

---

## 3. 예외·오류·수용 기준

| 시나리오 | 기대 결과 | 검증 근거 / 테스트 |
| :--- | :--- | :--- |
| 잘못된 비밀번호로 로그인 | `400 Bad Request` (`codes.InvalidArgument`) 반환, 세션 쿠키 미발급 | `EV-005` / `T-005` |
| 비인증 상태에서 `GET /api/auth/me` 또는 `POST /api/memos` | `401 Unauthorized` 반환 | `EV-003` / `T-003` |
| 생성 요청에 `pinned: true` 포함 | 무시되어 `pinned: false`로 생성 후 `PATCH`에서만 변경 허용 | `EV-006`, `EV-007` / `T-006`, `T-007` |
| 잘못된 CEL 필터 식 전달 | `400 Bad Request` 반환 | `EV-008` / `T-008` |
| 삭제된 메모 재조회 | `404 Not Found` 반환 | `EV-007` / `T-007` |
| 로그아웃 후 기존 Refresh 쿠키로 갱신 시도 | `401 Unauthorized` 거부 | `EV-010` / `T-010` |
| `SIGTERM` 재시작 후 로그인·목록·보관함·공유 링크 조회 | 재시작 전 상태와 100% 일치 | `EV-011` / `T-011` |
