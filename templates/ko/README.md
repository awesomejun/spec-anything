# 한국어 산출물 템플릿 규약 (`01`–`12`)

`goal.json.output_language == "ko"`일 때 서술 본문·표 제목·요약은 한국어 존댓말로 작성하되, 검증 스크립트가 파싱하는 아래 기계 판독 요소는 반드시 영어로 원형 보존합니다.

- 기능 식별자: `F-001`, `F-002`, ...
- 동작 근거 식별자: `EV-001`, `EV-002`, ...
- 화면 캡처 식별자: `SCR-001`, `SCR-002`, ...
- 대조 테스트 식별자: `TC-001`, `TC-002`, ...
- 소스 라인 인용: `[REF: relative/path.ext:start-end]`
- 상태 열거값: `observed` | `code-verified` | `inferred` | `assumed` | `unverified`
- 필수 근거 섹션 제목: `## Sources Read`
- Mermaid 도표: 구조 전용(하드코딩 색상·`style fill:`·`classDef` 색상 금지)

완결된 실측 예제는 `examples/01-pocketbase-v0.40.6/`을 참조하십시오.
