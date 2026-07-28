# Shadow Lab 변경 이력

| 항목 | 내용 |
| --- | --- |
| Author | Human Team + Codex |
| Reviewed by | Human Team |
| Managed by | Codex |
| Status | Draft |
| Version | v0.1 |
| Last Updated | 2026-07-28 |

이 문서는 Shadow Lab 관련 코드·데이터·화면 변경을 추적한다. 각 항목은 구현 전 또는 구현 직후 기록하며, 운영 파이프라인에 미치는 영향을 명시한다.

## 기록 형식

```text
변경 ID:
일시:
목적:
수정 파일:
변경 내용:
운영 영향: 없음 / 연구 전용 / 운영 변경
검증:
결과:
롤백:
다음 작업:
```

## 예정 변경

### CHG-SHADOW-001

```text
일시: 2026-07-28
목적: Shadow Lab 구현 설계와 변경 추적 기준 수립
수정 파일: docs/plans/2026-07-28-shadow-lab-design.md, docs/SHADOW_LAB_CHANGELOG.md
변경 내용: 연구용 Shadow 실행, 결과 비교, 검토 큐, 내보내기 설계 기록
운영 영향: 없음
검증: 문서 검토 대기
결과: 설계 승인 후 구현 계획 작성 예정
롤백: 문서 삭제 또는 Superseded 상태로 변경
다음 작업: 기존 실험실 모듈과 저장 모델의 정확한 확장 지점 분석
```

## CHG-SHADOW-002

| 항목 | 내용 |
| --- | --- |
| 일시 | 2026-07-28 |
| 목적 | Shadow 실행에 공통 적용할 인구·KOSIS·판단 보류 중심의 안전 정책 모델 추가 |
| 수정 파일 | `clafact/shadow_policy.py`, `tests/test_shadow_policy.py` |
| 변경 내용 | 불변 `ShadowPolicy`, 기본 정책, 허용 Claim 유형·판정 검증, 직렬화·역직렬화 구현 |
| 운영 영향 | 없음 - 연구용 Shadow 정책 모델만 추가 |
| 검증 | `pytest tests/test_shadow_policy.py -v` - 3 passed |
| 롤백 | `shadow_policy.py`와 테스트를 제거하면 기존 운영·실험실 흐름에 영향 없음 |
| 다음 작업 | 연구 전용 Shadow SQLite 저장소 구현 |

## CHG-SHADOW-003 — 연구 전용 실행·저장 기반 추가

- 일시: 2026-07-28
- 변경: `ShadowStore`가 `data/research/shadow_lab.db`에 실험 실행, 행, 검토 이력을 분리 보관한다. `run_shadow_experiment`는 기존 Python·LLM·Hybrid 비교를 Shadow 행과 위험 신호로 변환한다.
- 영향: 운영 검증 결과와 운영 저장소에는 쓰지 않는다. LLM 오류·후보 불일치·필수 슬롯 누락은 검토 대상으로 표시된다.
- 검증: `pytest tests/test_shadow_store.py -v`, `pytest tests/test_shadow_runner.py -v`
- 다음 단계: 실행·저장·정책을 하나의 서비스 경계로 묶고 UI가 호출할 안정된 인터페이스를 만든다.
## CHG-SHADOW-004 — Shadow Lab 서비스 경계 추가

- 일시: 2026-07-28
- 변경: `ShadowLabService`가 실행·연구 저장·조회·검토를 단일 인터페이스로 제공한다.
- 영향: UI는 운영 데이터 저장소를 호출하지 않고 서비스만 호출한다. 연구 데이터는 Shadow 전용 SQLite에만 기록된다.
- 검증: `pytest tests/test_shadow_service.py -v`
- 다음 단계: 실험 실행 결과를 JSON/CSV로 내보내 팀 분석 기록으로 활용하거나, UI 탭을 연결한다.
## CHG-SHADOW-005 — JSON·CSV 실험 기록 내보내기 추가

- 일시: 2026-07-28
- 변경: Shadow 실행 스냅샷을 JSON으로, 행 단위 분석 결과를 Excel 안전 CSV로 내보낸다. 정책·요약·위험 신호·검토 이력이 보존된다.
- 영향: 조회와 내보내기만 수행하며 운영 저장소를 읽거나 쓰지 않는다.
- 검증: `pytest tests/test_shadow_export.py tests/test_shadow_service.py tests/test_shadow_store.py -v`
- 다음 단계: 기존 검증 실험실에 Shadow Mode 탭과 실행·결과·검토·다운로드 UI를 연결한다.
## CHG-SHADOW-006 — 검증 실험실 Shadow Mode UI 연결

- 일시: 2026-07-28
- 변경: 기존 `검증 실험실`을 `기존 비교 실험`과 `Shadow Mode` 탭으로 분리했다. Shadow 탭에서 기사 본문·발행일 기반 실행, 요약·문장별 위험 신호 확인, 승인·보정·보류 검토, JSON·CSV 실행 기록 다운로드를 제공한다.
- 영향: 모든 실행·검토·다운로드는 `data/research/shadow_lab.db`만 사용한다. 운영 Claim, 리뷰 큐, 판정 이력, 기존 비교 실험 저장소는 변경하지 않는다.
- 검증: Shadow·기존 실험실 회귀 테스트 76건 및 Streamlit AppTest로 탭, 실행, 검토 UI, JSON·CSV 다운로드 버튼 렌더링을 확인했다.
- 수동 확인 참고: Playwright 런타임은 이 환경에 없어 실행하지 못했으나, 임시 Streamlit 서버는 정상 기동했고 Streamlit 내장 AppTest로 동일 화면 흐름을 검증했다.
- 다음 단계: 과거 Shadow 실행 이력 선택과 실행 간 비교 화면을 추가할 수 있다.
