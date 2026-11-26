# `spec-anything` Flagship Example — `usememos/memos` 26.11.2 (MIT)

> **Turn any open-source repository + official release binary into an evidence-backed, 12-artifact reimplementation spec with executable parity tests.**

본 패키지는 GitHub ~64.7k stars · **MIT License** 오픈소스 앱 [usememos/memos](https://github.com/usememos/memos) 공식 릴리스 **`26.11.2`** (커밋 `00fcd170281a75fc0e95ec4f2f54f43d32fe81bd`)을 대상으로 **소스 코드 + 공식 `darwin_arm64` 배포본 REA 역분석 + 격리 구동·UI 8상태 촬영 + 12종 고정 명세(`01`~`12`) + 실행 가능한 대조 테스트(`07`) + 통합 품질 게이트(`G-01`~`G-10`)**까지 실제로 완주해 검증한 대표 공개 예제입니다.

---

## 1. 이 예제가 정적 코드 요약 도구와 다른 5가지 실측 증거

정적 코드만 읽으면 놓치는 실제 동작 5가지를 공식 `26.11.2` 바이너리 격리 실행과 REA 대조로 잡아서 `06_evidence/evidence_v1.0.0.jsonl`과 `07_tests/test_memos_parity.py`에 자동 검증 규칙으로 고정했습니다.

1. **공식 바이너리 `+dirty` 원인 규명 (`REA-02`, `REA-03`, `EV-001`)**: 소스 아카이브의 `server/frontend/dist/index.html`은 244B 스텁(`No embeddable frontend found.`)이지만, 공식 `darwin_arm64` 바이너리는 `checksums.txt` SHA-256과 100% 일치하면서 CI 빌드 시 컴파일된 4,781B Vite SPA를 주입해 `vcs.modified=true` 및 `-s -w` 심볼 스트립 상태를 보입니다.
2. **신규 인스턴스 기본 `INSTANCE_ACCESS_MODE_PRIVATE` 경계 (`EV-002`, `EV-009`, `UI-07`)**: 비인증 `/robots.txt`는 `404`, 비인증 `GET /api/memos`는 `401`, `/explore`는 `/auth?redirect=%2Fexplore`로 리다이렉트되지만, `memo_share` 공유 토큰 조회(`GET /api/shares/{token}/memo`)는 `AuthBootstrapMethods`로 `PRIVATE` 메모를 `200 OK` 서빙합니다.
3. **Connect-RPC 대 REST `Set-Cookie` 트랜스포트 분기 및 오입력 `400` (`EV-005`, `EV-010`)**: 비밀번호 오입력은 `401`이 아니라 `400 Bad Request`(`codes.InvalidArgument`)를 반환하며, `HttpOnly` Refresh 쿠키 발급·회전·로그아웃 폐기는 `HeaderCarrier`가 주입되는 Connect-RPC(`/memos.api.AuthService/*`)에서 동작합니다.
4. **생성 시 `pinned` 무시 규약 (`EV-006`, `EV-007`)**: `POST /api/memos`에 `pinned: true`를 보내도 생성 시에는 `false`로 저장되며 `PATCH /api/memos/{uid}?updateMask=pinned`에서만 반영됩니다.
5. **CEL 필터 리터럴 SQL 와일드카드 이스케이프 및 `SIGTERM` 재시작 영속성 (`EV-008`, `EV-011`)**: `content.contains("50%_off")`는 `1`건, `content.contains("50X_off")`는 `0`건을 반환하며, 프로세스 종료 후 재기동 시 SQLite 13개 테이블·일반/고정/보관 메모·공유 링크가 100% 복구됩니다.

---

## 2. 흡수된 외부 프로젝트 장점 (`cc-rsg` + `Reverse_Spec_and_PRD`)

- **From `daishir0/cc-rsg`**: `.spec-anything/state.json` 중단·재개 상태 머신, `.spec-anything/goal.json`, 7개 카테고리 Question Bank(`.spec-anything/questions.json`), 5개 보편 테이블 역할형 결정론적 추출기(`scripts/extract_source_map.py`: 845파일·1,612단위 추출 + 미지원 확장자 Loud Warning), 영어 기계 계층 고정 + 다국어 본문 출력, 정적 참조 커버리지 게이트.
- **From `WindowHyun/Reverse_Spec_and_PRD`**: 비밀키·JWT·인증서 자동 유출 차단기(`scripts/secret_guard.py`, 0건 통과), `file://` 참조를 차단하는 안전한 정적 HTML 리뷰 대시보드 렌더러(`scripts/render_review.py` → `review_v1.0.0.html`).

---

## 3. 빠른 재검증 명령

```bash
# 1) 06 실측 JSONL 기반 11개 대조 테스트 실행 (원본 또는 클린룸 재구현본 대상)
python3 07_tests/test_memos_parity.py \
  --evidence 06_evidence/evidence_v1.0.0.jsonl \
  --binary /path/to/memos \
  --report-out 07_tests/verification_results_v1.0.0.json

# 2) 10개 이중 품질 게이트 (01-12 완전성, 03 외래키, [REF:], 05 해시, 06 JSONL, 07 통과, 09 OpenAPI/SQLite, 비밀키 0건, SHA256SUMS)
python3 scripts/validate_bundle.py --bundle-dir . --verify-checksums
```
