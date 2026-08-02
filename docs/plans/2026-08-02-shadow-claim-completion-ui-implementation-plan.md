# Shadow Claim 완료 UI Implementation Plan

| 항목 | 내용 |
|---|---|
| Author | Human Team + ClaFact Hermes Agent |
| Reviewed by | Human Team |
| Managed by | ClaFact Hermes Agent |
| Status | Approved |
| Version | v0.1 |
| Last Updated | 2026-08-02 |

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** 쉐도우 문장과 확정 KOSIS 근거를 사용자가 명시적으로 완료 처리하고, 동일 판정과 재현 근거를 화면·CSV에서 확인한다.

**Architecture:** 기존 KOSIS 매핑·값 비교·스냅샷을 다시 계산하지 않는다. 새 완료 저장소는 `shadow_run_id + row_index + evidence_id + snapshot_id`를 고유키로 하여 불변 완료 기록을 보관하고, Streamlit은 이 기록만 생성·표시한다. 기존 Shadow CSV는 행별 완료 Claim 필드를 추가해 동일 결과를 내보낸다.

**Tech Stack:** Python 3, SQLite, Streamlit, pytest.

---

### Task 1: 완료 Claim 영속 저장소

**Files:**
- Create: `clafact/claim_completion_store.py`
- Create: `tests/test_claim_completion_store.py`

**Step 1: Write the failing test**

```python
def test_appending_same_completed_claim_twice_keeps_one_immutable_record(tmp_path):
    record = {"shadow_run_id": "shadow-1", "row_index": 1,
              "evidence_id": "DT_TEST:total", "snapshot_id": "kosis-1",
              "verdict": "match", "snapshot": {"snapshot_id": "kosis-1"}}
    with ClaimCompletionStore(tmp_path / "completed.db") as store:
        assert store.append(record) is True
        assert store.append(record) is False
        assert store.list_for_run("shadow-1") == [record]
```

**Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_claim_completion_store.py -q`

Expected: FAIL because `ClaimCompletionStore` does not exist.

**Step 3: Write minimal implementation**

Create `ClaimCompletionStore` using one SQLite table with a composite primary key `(shadow_run_id, row_index, evidence_id, snapshot_id)`. Store the complete JSON payload, reject a different payload for an existing key, and return completed records ordered by sentence and creation order.

**Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_claim_completion_store.py -q`

Expected: PASS.

**Step 5: Commit**

```bash
git add clafact/claim_completion_store.py tests/test_claim_completion_store.py
git commit -m "feat: persist completed Shadow claims"
```

### Task 2: 완료 Claim CSV 필드

**Files:**
- Modify: `clafact/shadow_export.py`
- Modify: `tests/test_shadow_export.py`

**Step 1: Write the failing test**

```python
def test_csv_export_includes_completed_claim_verdict_and_reproducible_evidence(tmp_path):
    completed_by_row = {1: [{"verdict": "mismatch", "snapshot_id": "kosis-1",
                             "evidence": {"source_url": "https://kosis.kr/repro"}}]}
    row = exported_row(tmp_path, completed_by_row=completed_by_row)
    assert row["claim_completion_verdict"] == "mismatch"
    assert row["claim_completion_snapshot_id"] == "kosis-1"
```

**Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_shadow_export.py::test_csv_export_includes_completed_claim_verdict_and_reproducible_evidence -q`

Expected: FAIL because `completed_by_row` and CSV columns are absent.

**Step 3: Write minimal implementation**

Extend `SHADOW_CSV_COLUMNS` and `export_shadow_run_csv()` with an optional `completed_claims_by_row` argument. Flatten only verdict, snapshot ID, KOSIS table ID, and reproducible evidence URL; preserve existing CSV output when no records exist.

**Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_shadow_export.py -q`

Expected: PASS.

**Step 5: Commit**

```bash
git add clafact/shadow_export.py tests/test_shadow_export.py
git commit -m "feat: export completed Shadow claims to CSV"
```

### Task 3: 완료 기록 생성 어댑터

**Files:**
- Modify: `clafact/claim_completion.py`
- Create: `tests/test_claim_completion_from_evidence.py`

**Step 1: Write the failing test**

```python
def test_completes_selected_persisted_evidence_without_refetching_kosis():
    completed = complete_selected_claim(
        shadow_run_id="shadow-1", row_index=1, sentence="2024년 전국 출생아 수는 230,028명이다.",
        mapping={"evidence_id": "DT_1B8000F:births"}, comparison={"status": "match"},
        snapshot={"snapshot_id": "kosis-1", "reproducible_url": "https://kosis.kr/repro"},
    )
    assert completed["verdict"] == "match"
    assert completed["snapshot"]["snapshot_id"] == "kosis-1"
```

**Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_claim_completion_from_evidence.py -q`

Expected: FAIL because `complete_selected_claim` does not exist.

**Step 3: Write minimal implementation**

Add `complete_selected_claim()` to create the immutable completion payload from the already persisted mapping, comparison, and snapshot. It maps comparison `match`/`mismatch` to the same verdict and all other statuses to `hold`; it must not call KOSIS or mutate the source records.

**Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_claim_completion.py tests/test_claim_completion_from_evidence.py -q`

Expected: PASS.

**Step 5: Commit**

```bash
git add clafact/claim_completion.py tests/test_claim_completion_from_evidence.py
git commit -m "feat: complete Claim from selected KOSIS evidence"
```

### Task 4: 쉐도우 화면 연결

**Files:**
- Modify: `streamlit_app.py:48-53, 126-133, 2310-2380, Shadow CSV download section`
- Create: `tests/test_streamlit_claim_completion_contract.py`

**Step 1: Write the failing test**

```python
def test_shadow_screen_offers_explicit_claim_completion_and_csv_export():
    source = Path("streamlit_app.py").read_text(encoding="utf-8")
    assert '"Claim 완료"' in source
    assert "ClaimCompletionStore" in source
    assert "completed_claims_by_row" in source
```

**Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_streamlit_claim_completion_contract.py -q`

Expected: FAIL because the screen has no explicit completion action.

**Step 3: Write minimal implementation**

In the existing selected Shadow sentence area, list only mapped evidence with a persisted value comparison and its corresponding snapshot. Let the user choose one, click `Claim 완료`, build the immutable record, then append it with `ClaimCompletionStore`. Render a read-only result card with verdict, article value, official value, difference/reason, snapshot ID, and reproducible URL. Load completions for the run and pass their row grouping to the existing Shadow CSV download.

Use `st.warning` for `hold`; do not make it appear as a successful completion. On duplicate, show the saved immutable record instead of writing again.

**Step 4: Run tests to verify they pass**

Run: `python -m pytest tests/test_streamlit_claim_completion_contract.py tests/test_shadow_export.py tests/test_claim_completion_store.py tests/test_claim_completion_from_evidence.py -q`

Expected: PASS.

**Step 5: Commit**

```bash
git add streamlit_app.py tests/test_streamlit_claim_completion_contract.py
git commit -m "feat: complete Claims in Shadow mode"
```

### Task 5: 전체 회귀·실제 화면 확인·기록 갱신

**Files:**
- Modify: `C:/Users/USER/Desktop/클라비_아이펠톤/ClaFact_완성형_핵심작업기록/03_검증완료_단순수치_Claim_3건.md`

**Step 1: Run focused regression suite**

Run: `python -m pytest tests/test_claim_completion.py tests/test_claim_completion_report.py tests/test_claim_completion_replay.py tests/test_claim_completion_store.py tests/test_claim_completion_from_evidence.py tests/test_shadow_export.py tests/test_streamlit_claim_completion_contract.py tests/test_kosis_value_comparison.py tests/test_kosis_evidence_snapshot.py -q`

Expected: PASS.

**Step 2: Run full suite**

Run: `python -m pytest`

Expected: exit code 0.

**Step 3: Manually verify Streamlit**

Run the app, open one saved Shadow execution, complete one KOSIS-linked sentence, then download CSV. Confirm the rendered verdict and the CSV’s completion verdict/snapshot ID/reproducible URL agree.

**Step 4: Update only the central outcome record**

Append the actual UI verification evidence and the next single recommended task to the existing core record; do not add a separate narrative report.

**Step 5: Commit code and core record separately**

```bash
git add C:/Users/USER/Desktop/클라비_아이펠톤/ClaFact_완성형_핵심작업기록/03_검증완료_단순수치_Claim_3건.md
git commit -m "docs: record Shadow Claim completion UI verification"
```
