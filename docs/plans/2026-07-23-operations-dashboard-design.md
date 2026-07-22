# Operations Dashboard Design

| 항목 | 내용 |
|---|---|
| Author | Human Team + ClaFact Hermes Agent |
| Reviewed by | Human Team |
| Managed by | ClaFact Hermes Agent |
| Status | Draft |
| Version | v0.1 |
| Last Updated | 2026-07-23 |

## Goal

Streamlit의 `📡 운영 홈`을 검증 운영자가 현재 처리 상태와 다음 조치를 빠르게 판단하는 공공 데이터 콘솔로 개선한다.

## Visual Direction

- 딥 네이비 표면과 청록 신호를 중심으로 한 신뢰 중심의 공공 데이터 콘솔
- 정상·대기·실패 상태는 색상뿐 아니라 아이콘과 명시적 문구로 함께 표시
- 얇은 경계선, 절제된 그림자, 고정폭 숫자와 충분한 여백으로 감사 가능한 인상을 유지

## Layout

1. 상단 운영 헤더: 제품명, KOSIS 기반 검증 상태, 설명
2. 운영 지표: 기사·처리 대기·처리 실패·리뷰 대기 카드
3. 운영 실행: 기사 파일 경로와 처리 한도를 입력하고 등록·배치를 실행하는 패널
4. 최근 감사 로그: Claim, 처리 상태, 판정, 등급, HCX 신호, 오류를 한눈에 보는 표

## Behavior and Accessibility

- 기존 내부 FastAPI 호출과 데이터베이스 조회 로직은 변경하지 않는다.
- API 오류는 사용자가 조치할 수 있는 문구로 표시한다.
- 버튼과 입력은 명확한 레이블과 충분한 터치 영역을 유지한다.
- 상태는 색상만으로 전달하지 않으며, 좁은 화면에서는 카드와 패널을 세로로 배치한다.

## Verification

- 기존 API 회귀 테스트를 유지한다.
- Streamlit 앱을 컴파일하고 로컬 실행 화면에서 운영 홈의 데스크톱·모바일 레이아웃과 등록·처리 제어를 확인한다.
