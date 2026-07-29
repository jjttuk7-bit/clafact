# Golden Set Seed 100 Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Build a research-only Seed 100 goldenset template, validator, and Shadow Mode status view for five KOSIS/news domains.

**Architecture:** A pure `clafact.goldenset` module owns the schema, CSV/JSONL conversion, validation, and summary model. Versioned files in `data/research/goldenset/` remain the source of truth; `streamlit_app.py` only reads them to render a download-and-status panel in Shadow Mode. No operational Store, Claim, review queue, or KOSIS research SQLite store is written by this feature.

**Tech Stack:** Python 3.11+, standard library `csv`/`json`/`dataclasses`, pytest, Streamlit.

---

### Task 1: Define the research schema and a blank Seed template

**Files:**
- Create: `clafact/goldenset.py`
- Create: `data/research/goldenset/seed_v0.1.csv`
- Create: `data/research/goldenset/seed_v0.1.jsonl`
- Create: `data/research/goldenset/seed_manifest_v0.1.json`
- Create: `data/research/goldenset/annotation_guideline_v1.md`
- Test: `tests/test_goldenset.py`

**Step 1: Write the failing test**

```python
from clafact.goldenset import REQUIRED_COLUMNS, blank_seed_rows, seed_manifest


def test_blank_seed_has_the_research_columns_and_five_domain_targets():
    assert {"claim_id", "domain", "sentence", "review_status", "kosis_table_id"} <= set(REQUIRED_COLUMNS)
    assert blank_seed_rows() == []
    assert seed_manifest().domain_targets == {
        "물가": 20, "고용": 20, "인구": 20, "주거": 20, "보건": 20,
    }
```

**Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_goldenset.py::test_blank_seed_has_the_research_columns_and_five_domain_targets -q`

Expected: FAIL because `clafact.goldenset` does not exist.

**Step 3: Write minimal implementation**

Create a frozen `SeedManifest` dataclass plus constants for the 5 domain targets, controlled review statuses (`draft`, `needs_review`, `approved`, `on_hold`), controlled claim types, and exact CSV column order. Add `blank_seed_rows()` and `seed_manifest()`.

Create an empty CSV with only the exact header, an empty JSONL, a manifest with version `v0.1` and target `100`, and a Korean guide that explains each column, allowed labels, one valid example, and the two-person approval rule.

**Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_goldenset.py::test_blank_seed_has_the_research_columns_and_five_domain_targets -q`

Expected: PASS.

**Step 5: Commit**

```bash
git add clafact/goldenset.py tests/test_goldenset.py data/research/goldenset
git commit -m "feat: add goldenset seed schema"
```

### Task 2: Validate records, files, duplicates, and approval gates

**Files:**
- Modify: `clafact/goldenset.py`
- Modify: `tests/test_goldenset.py`

**Step 1: Write failing tests**

```python
from clafact.goldenset import validate_rows


def test_approved_row_requires_traceable_kosis_answer():
    errors = validate_rows([{
        "claim_id": "seed-001", "domain": "물가", "sentence": "물가가 2.4% 올랐다.",
        "review_status": "approved", "kosis_table_id": "", "official_value": "",
    }])
    assert any(error.code == "approved_kosis_required" for error in errors)


def test_duplicate_claim_id_and_normalized_sentence_are_errors():
    errors = validate_rows([valid_row("seed-001"), valid_row("seed-001")])
    assert {error.code for error in errors} >= {"duplicate_claim_id", "duplicate_sentence"}
```

**Step 2: Run tests to verify they fail**

Run: `python -m pytest tests/test_goldenset.py -q`

Expected: FAIL because validation is not implemented.

**Step 3: Write minimal implementation**

Add `ValidationIssue(code, severity, claim_id, field, message)` and `validate_rows(rows)`.

Validate required fields, controlled labels, domain names, distinct claim IDs, normalized duplicate sentences, and the stricter rule for `approved`: metric, value, unit, period, KOSIS table ID, selected item, official value, official URL, snapshot ID, author, and reviewer must be present. Return issues; never alter source rows.

Add `load_csv(path)`, `load_jsonl(path)`, and a semantic parity validator that reports if CSV and JSONL have different IDs or field values.

**Step 4: Run tests to verify they pass**

Run: `python -m pytest tests/test_goldenset.py -q`

Expected: PASS.

**Step 5: Commit**

```bash
git add clafact/goldenset.py tests/test_goldenset.py
git commit -m "feat: validate goldenset records"
```

### Task 3: Build an immutable progress and downloadable validation report

**Files:**
- Modify: `clafact/goldenset.py`
- Modify: `tests/test_goldenset.py`

**Step 1: Write failing tests**

```python
from clafact.goldenset import summarize_rows, validation_report_csv


def test_summary_reports_domain_gap_and_review_counts():
    summary = summarize_rows([
        valid_row("seed-001", domain="물가", review_status="approved"),
        valid_row("seed-002", domain="고용", review_status="needs_review"),
    ])
    assert summary.domain_counts["물가"].current == 1
    assert summary.domain_counts["물가"].gap == 19
    assert summary.review_counts["approved"] == 1
    assert "issue_code" in validation_report_csv(summary.issues)
```

**Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_goldenset.py::test_summary_reports_domain_gap_and_review_counts -q`

Expected: FAIL because summary helpers do not exist.

**Step 3: Write minimal implementation**

Create pure summary dataclasses that expose total target/current, domain target/current/gap, review status counts, valid evaluation count (approved rows with no error), and `ValidationIssue` list. Create an UTF-8-sig CSV report with claim ID, severity, issue code, field, and Korean message.

**Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_goldenset.py -q`

Expected: PASS.

**Step 5: Commit**

```bash
git add clafact/goldenset.py tests/test_goldenset.py
git commit -m "feat: summarize goldenset quality"
```

### Task 4: Render a read-only Golden Set status panel in Shadow Mode

**Files:**
- Modify: `streamlit_app.py:1844-2700`
- Modify: `tests/test_streamlit_shadow_guide_safety.py`
- Test: `tests/test_goldenset.py`

**Step 1: Write the failing source-contract test**

```python
def test_shadow_mode_renders_goldenset_status_and_downloads():
    source = Path("streamlit_app.py").read_text(encoding="utf-8")
    assert "골든셋 Seed 100 현황" in source
    assert "골든셋 CSV 템플릿 다운로드" in source
    assert "골든셋 검증 결과 다운로드" in source
```

**Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_streamlit_shadow_guide_safety.py -q`

Expected: FAIL because the panel is not rendered.

**Step 3: Write minimal implementation**

Add a small read-only expander after the Shadow step guide and before the candidate-search controls. It loads only `data/research/goldenset/seed_v0.1.csv` through `clafact.goldenset`, shows target/current, approved/needs-review/on-hold counts, compact domain progress, and errors/missing fields. Add download buttons for the blank CSV template and current validation report.

Do not add upload, persistence, or any writes. If files are missing or malformed, show a clear research-only warning and retain all Shadow Mode controls.

**Step 4: Run UI and module tests**

Run: `python -m pytest tests/test_goldenset.py tests/test_streamlit_shadow_guide_safety.py -q`

Expected: PASS.

**Step 5: Commit**

```bash
git add streamlit_app.py clafact/goldenset.py tests/test_goldenset.py tests/test_streamlit_shadow_guide_safety.py
git commit -m "feat: show goldenset seed status in shadow mode"
```

### Task 5: Verify the full research-only feature

**Files:**
- Modify: `docs/plans/2026-07-29-goldenset-seed-100-design.md` only if design changed during implementation

**Step 1: Run focused checks**

Run:

```bash
python -m pytest tests/test_goldenset.py tests/test_streamlit_shadow_guide_safety.py -q
python -m py_compile streamlit_app.py clafact/goldenset.py
```

Expected: PASS.

**Step 2: Run the full suite**

Run: `python -m pytest -q`

Expected: PASS with only the repository’s existing skips.

**Step 3: Inspect scope**

Run:

```bash
git diff --check main...HEAD
git diff --stat main...HEAD
```

Expected: only goldenset data/module/tests, Shadow Mode read-only UI, and associated documentation.

**Step 4: Commit documentation changes if any**

```bash
git add docs/plans/2026-07-29-goldenset-seed-100-design.md
git commit -m "docs: finalize goldenset seed guidance"
```
