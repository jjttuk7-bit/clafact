# Weekly Quality Record Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** R2·R3의 골든셋이 준비되면 ClaFact 팀이 통계표 매핑과 판정 품질을 매주 같은 방식으로 기록할 수 있게 한다.

**Architecture:** `docs/quality/weekly_mapping_quality.md`는 사람이 읽는 주간 기록의 단일 기준 문서다. 골든셋 원본은 R2·R3가 소유하며, 첫 주에는 원본 위치와 표본 수를 연결한 뒤 수동 계산값을 기록한다. 골든셋 열 구조가 확정되면 별도 자동 측정 도구를 설계한다.

**Tech Stack:** Markdown, Git, R2·R3 골든셋 원본

---

### Task 1: 주간 품질 기록 템플릿 만들기

**Files:**
- Create: `docs/quality/weekly_mapping_quality.md`
- Test: 문서 자체의 완료 기준 점검

**Step 1: 템플릿의 빈 상태를 정의한다.**

첫 주 기록에는 골든셋 원본 위치, 담당자, 표본 수, Hit@1·Hit@3, 판정 일치율, 판단불가 비율, 실패 사례, 다음 주 개선 항목이 있어야 한다. 값이 준비되지 않은 항목은 `대기`로 표시한다.

**Step 2: 템플릿이 설계와 맞는지 확인한다.**

Run: `rg "Hit@1|Hit@3|판정 일치율|판단불가 비율|실패 사례" docs/quality/weekly_mapping_quality.md`

Expected: 다섯 항목이 모두 검색된다.

**Step 3: 최소 템플릿을 작성한다.**

문서 메타데이터와 `2026-W31` 첫 주차 섹션을 만들고, 골든셋 수령 전 상태를 명확히 적는다.

**Step 4: 템플릿을 다시 점검한다.**

Run: `rg "Hit@1|Hit@3|판정 일치율|판단불가 비율|실패 사례" docs/quality/weekly_mapping_quality.md`

Expected: PASS.

**Step 5: Commit**

```bash
git add docs/quality/weekly_mapping_quality.md
git commit -m "docs: add weekly quality record template"
```

### Task 2: 골든셋 인수 규칙 기록하기

**Files:**
- Modify: `docs/quality/weekly_mapping_quality.md`
- Test: 문서 자체의 완료 기준 점검

**Step 1: 필요한 입력을 명시한다.**

R2·R3가 제공할 각 Claim별 최소 정보는 `claim_id`, 기사 문장, 정답 통계표 식별자, 기대 판정, 제외 사유다.

**Step 2: 인수 규칙이 빠져 있는지 점검한다.**

Run: `rg "claim_id|정답 통계표|기대 판정|제외 사유" docs/quality/weekly_mapping_quality.md`

Expected: FAIL.

**Step 3: 인수 규칙을 최소한으로 추가한다.**

골든셋 원본의 파일 형식은 강제하지 않고, 위 다섯 입력이 제공되면 측정 가능하다고 명시한다.

**Step 4: 인수 규칙을 검증한다.**

Run: `rg "claim_id|정답 통계표|기대 판정|제외 사유" docs/quality/weekly_mapping_quality.md`

Expected: PASS.

**Step 5: Commit**

```bash
git add docs/quality/weekly_mapping_quality.md
git commit -m "docs: define goldset handoff criteria"
```

### Task 3: 첫 주 측정과 회고 진행하기

**Files:**
- Modify: `docs/quality/weekly_mapping_quality.md`
- Input: R2·R3의 확정 골든셋 30~50건

**Step 1: 골든셋 수령 상태를 확인한다.**

정답 통계표·기대 판정이 포함된 확정본인지 R2·R3에 확인한다. 확정 전이면 수치를 기록하지 않는다.

**Step 2: 표본별 결과를 대조한다.**

각 Claim에서 1순위/상위 3개 추천 통계표와 정답 통계표를 비교하고, 자동 판정과 기대 판정을 비교한다.

**Step 3: 지표를 계산해 기록한다.**

Hit@1, Hit@3, 판정 일치율, 판단불가 비율을 계산하고 분모에서 제외한 Claim과 이유를 남긴다.

**Step 4: 실패 사례를 세 유형으로 분류한다.**

`검색어·주제`, `통계표·기간·단위`, `Claim·입력 품질` 중 하나 이상으로 표기한다.

**Step 5: 다음 주 개선 항목을 최대 세 건으로 확정한다.**

R1은 지표를, R2·R3는 매핑 개선을, R4·R5는 운영 문제를 각각 확인한 뒤 개선 우선순위를 합의한다.
