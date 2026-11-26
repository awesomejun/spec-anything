<div align="center">

# spec-anything

**어떤 오픈소스 앱이든 검증된 클린룸 명세서로 바꾸고, 명세만으로 다시 만든 앱이 원본과 똑같이 동작하는지 자동 증명합니다.**

[![License: MIT](https://img.shields.io/badge/License-MIT-10b981.svg?style=flat-square)](LICENSE)
[![Agents](https://img.shields.io/badge/Agents-Claude%20Code%20%7C%20Codex%20%7C%20OpenBot-0f172a.svg?style=flat-square)](SKILL.md)
[![Verified](https://img.shields.io/badge/Verified-39%2F39%20Gates%20%C2%B7%2041%2F41%20Parity-3b82f6.svg?style=flat-square)](#예제-미리보기)

[English](README.md) · **한국어**

</div>

---

`spec-anything`은 오픈소스 앱의 **소스 코드**, **공식 배포 바이너리**, **실제 실행 화면**을 함께 조사해 **12개 고정 명세 파일(`01`–`12`)**과 **실행 가능한 대조 테스트**를 만드는 AI 코딩 스킬입니다.

## 예제 미리보기

아래 3개 예제는 원본 소스 코드와 브랜드 자산을 전혀 복사하지 않고, 생성된 명세서만으로 처음부터 다시 구현해 자동 검증했습니다.

<img src="assets/reimpl-proof-banner.png" alt="Excalidraw, Handy, Pomotroid 원본 대비 클린룸 재구현 시각 비교" width="100%" />

| 앱 (MIT) | 한 줄 설명 | 대조 테스트 | 화면 일치율 | 산출물 |
| :--- | :--- | :---: | :---: | :--- |
| [**Excalidraw**](https://github.com/excalidraw/excalidraw) `v0.18.1` | 손그림 화이트보드 그림판 | `12 / 12` | `99.5%` (`0.46%` MAE) | [명세](examples/01-excalidraw-v0.18.1/) · [재구현](examples/01-excalidraw-v0.18.1/cleanroom-reimpl/) |
| [**Handy**](https://github.com/cjpais/Handy) `v0.10.2` *(2026)* | 오프라인 음성 받아쓰기 앱 | `15 / 15` | `98.3%` (`1.67%` MAE) | [명세](examples/02-handy-v0.10.2/) · [재구현](examples/02-handy-v0.10.2/cleanroom-reimpl/) |
| [**Pomotroid**](https://github.com/Splode/pomotroid) `v1.7.1` | 원형 뽀모도로 공부 타이머 | `14 / 14` | `99.2%` (`0.83%` MAE) | [명세](examples/03-pomotroid-v1.7.1/) · [재구현](examples/03-pomotroid-v1.7.1/cleanroom-reimpl/) |

> 로컬 브라우저에서 [`assets/reimpl-proof-interactive.html`](assets/reimpl-proof-interactive.html)을 열면 6개 화면을 좌우 슬라이더로 비교할 수 있습니다 (한·영 지원).

## 동작 방식

1. **코드·공식 배포본 동시 점검** — 소스 코드와 실제 공식 배포 패키지(`.dmg`, `.app`, npm 배포본)를 함께 대조합니다.
2. **격리 실행 실측** — 앱을 격리 환경에서 직접 구동해 화면 캡처, UI 토큰, 스키마, 실제 상태 전이를 기록합니다.
3. **12종 명세·대조 테스트 생성** — 서로 연결된 12개 산출물(`01`–`12`)과 원본·재구현본을 같은 기준으로 검사하는 실행 테스트를 만듭니다.

<details>
<summary><strong>생성되는 12개 산출물(01–12) 한눈에 보기</strong></summary>

| 구분 | 산출물 |
| :--- | :--- |
| **기획·아키텍처** | `01` PRD · `02` SDD · `03` 재현 범위표 · `08` 클린룸 구현 청사진 · `12` 구현 순서표 |
| **실측 근거** | `04` 환경·배포본 감사 · `05` UI 기준 스크린샷 · `06` 실행 근거 기록 (`JSONL`) |
| **계약·검증** | `07` 실행형 대조 테스트 · `09` 기계 판독 계약 (JSON Schema / OpenAPI / SQL) · `10` 실행·상태 도표 · `11` UI 디자인 토큰 |

</details>

## 빠른 시작

### 1. 스킬 설치

```bash
mkdir -p ~/.claude/skills/spec-anything
cp -r SKILL.md LICENSE schemas scripts agents references templates ~/.claude/skills/spec-anything/
```

Python `3.10+` 환경이 필요합니다. UI 캡처, 픽셀 차분, PDF/DOCX 리뷰 문서 생성까지 쓰려면 아래 패키지를 추가로 설치합니다.

```bash
pip install jsonschema markdown pillow playwright python-docx && playwright install chromium
```

### 2. 에이전트에서 실행

```text
spec-anything 스킬로 https://github.com/Splode/pomotroid (v1.7.1, 티어 T3)를 분석해
01–12 산출물과 클린룸 재구현본을 만들고 모든 대조 테스트를 통과시켜줘.
```

### 3. 포함된 예제 60초 검증

```bash
for ex in examples/*; do python3 scripts/validate_bundle.py "$ex" --tier T3 --verify-checksums; done
python3 scripts/secret_guard.py . --fail-on-hit
```

## 기존 방식과의 차이

| 기능 | 정방향 SDD | 정적 역공학 명세 | `spec-anything` |
| :--- | :---: | :---: | :---: |
| 소스 구조 추출 및 재개형 워크플로 | — | ✓ | ✓ |
| 공식 배포 바이너리·패키지 감사 (`SHA-256`) | — | — | ✓ |
| 실구동 UI 캡처·CSS 토큰·동작 기록 | — | — | ✓ |
| 실행형 대조 테스트 및 픽셀 차분 증명 | — | — | ✓ |

## 상세 문서 및 라이선스

- **[아키텍처·배포본 감사 근거·스크립트 안내](docs/ARCHITECTURE.ko.md)** — 7단계 파이프라인, 12종 산출물 도식, 공식 배포본 실측 사례, 7개 자동화 스크립트, 상세 도구 비교.
- **[스킬 정의서](SKILL.md)** — 전체 에이전트 작업 절차 및 품질 게이트 규칙.
- **라이선스** — [MIT](LICENSE). 권한이 있는 클린룸 기능 재구현 및 상호운용성 검증 목적으로만 사용합니다 (접근 제어·DRM 우회 및 상표 무단 재사용 제외).
