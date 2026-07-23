# Light Theme Surface Design

| 항목 | 내용 |
|---|---|
| Author | Human Team + ClaFact Hermes Agent |
| Reviewed by | Human Team |
| Managed by | ClaFact Hermes Agent |
| Status | Draft |
| Version | v0.1 |
| Last Updated | 2026-07-23 |

## Goal

라이트·시스템 모드에서 앱 배경, 카드, 입력 컨트롤의 표면을 명확히 구분하고 Streamlit 테마 전환을 유지한다.

## Palette

| Surface | Light | Dark |
|---|---|---|
| Page background | `#F3F6F8` | `#071D2B` |
| Card and input surface | `#FFFFFF` | `#0B2636` |
| Border | `#C8D4DC` | `#31576A` |
| Primary text | `#102A3A` | `#E7F0EF` |
| Secondary text | `#4D6473` | `#B3C7CA` |

청록은 주요 상태와 동작에만 사용한다. 색상은 Streamlit 컨트롤에 직접 강제하지 않고, 모드별 CSS 변수로 전달한다.
