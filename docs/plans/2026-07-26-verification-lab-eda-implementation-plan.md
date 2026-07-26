# Verification Lab Integrated EDA Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Replace the verification lab’s three counters and single oversized body-length bar with a Python-only, session-scoped dashboard covering CSV quality, article structure, numeric-claim characteristics, and selected-article evidence.

**Architecture:** Add a pure `clafact.experiment_eda` analysis module that accepts already-decoded CSV rows and returns typed article, sentence, issue, and aggregate records. Add a small pure `clafact.experiment_eda_view` module for chart decisions, filters, pagination-safe problem rows, and selected-article presentation. Keep Streamlit responsible only for file decoding, range selection, session caching, and native dashboard rendering.

**Tech Stack:** Python standard library, existing `clafact.pipeline` rules, Streamlit 1.60 native metrics/charts/dataframes, pytest.

---

### Task 1: CSV quality and article preprocessing model

**Files:**
- Create: `clafact/experiment_eda.py`
- Create: `tests/test_experiment_eda.py`

**Step 1: Write the failing quality tests**

Cover:

```python
def test_analyze_rows_records_missing_invalid_and_duplicate_rows():
    rows = [
        {"title": "정상", "date": "2025-11-04", "url": "https://n/1",
         "body": "입력 2025.11.04. 09:00 소비자물가는 2.4% 올랐다."},
        {"title": "", "date": "not-a-date", "url": "https://n/2", "body": "본문"},
        {"title": "본문 없음", "date": "2025-11-04", "url": "https://n/3", "body": ""},
        {"title": "중복", "date": "2025-11-04", "url": "https://n/1", "body": "다른 본문"},
    ]
    report = analyze_rows(rows)
    assert report.source_row_count == 4
    assert report.valid_article_count == 2
    assert report.excluded_counts == {"missing_body": 1, "duplicate": 1}
    assert report.warning_counts["missing_title"] == 1
    assert report.warning_counts["invalid_date"] == 1
    assert [issue.row_number for issue in report.issues] == [2, 3, 4]
```

Also test:

- body alias detection
- URL duplicate priority
- fallback duplicate fingerprint from normalized title plus cleaned body
- boundary-cleaned empty body
- raw/cleaned/removed character lengths
- original row number preservation
- no original full body on issue-only records

**Step 2: Run tests to verify RED**

Run:

```powershell
python -m pytest -q tests/test_experiment_eda.py
```

Expected: import or symbol failure.

**Step 3: Implement the minimal typed model**

Create immutable dataclasses resembling:

```python
@dataclass(frozen=True)
class EdaIssue:
    row_number: int
    severity: Literal["warning", "excluded"]
    code: str
    message: str

@dataclass(frozen=True)
class EdaArticle:
    row_number: int
    title: str
    article_date: str
    raw_length: int
    clean_length: int
    removed_length: int
    cleaned_body: str
    warnings: tuple[str, ...]
    sentences: tuple["EdaSentence", ...] = ()

@dataclass(frozen=True)
class EdaReport:
    source_row_count: int
    articles: tuple[EdaArticle, ...]
    issues: tuple[EdaIssue, ...]
    excluded_counts: Mapping[str, int]
    warning_counts: Mapping[str, int]
```

Rules:

- Use the existing aliases from `clafact.pipeline.ingest.FIELD_ALIASES`.
- Use `strip_site_chrome` followed by the same earliest article-end boundary and `clean_body`.
- Accept common ISO, slash, and dotted date prefixes; invalid/missing dates are warnings, not exclusions.
- Exclude missing bodies, bodies empty after cleaning, and duplicates.
- Use URL as the duplicate key when present; otherwise hash normalized title plus cleaned body.
- Never synthesize a title, sentence, date, or article body.

**Step 4: Run tests to verify GREEN**

Run:

```powershell
python -m pytest -q tests/test_experiment_eda.py
```

Expected: all Task 1 tests pass.

**Step 5: Commit**

```powershell
git add clafact/experiment_eda.py tests/test_experiment_eda.py
git commit -m "feat: analyze verification CSV quality"
```

---

### Task 2: Article structure and Python numeric-claim features

**Files:**
- Modify: `clafact/experiment_eda.py`
- Modify: `tests/test_experiment_eda.py`

**Step 1: Write failing sentence and aggregate tests**

Test a fixed article containing:

- a percentage increase
- a monetary amount
- a people/household count
- a forecast sentence
- a sentence without a numeric claim

Assert:

```python
assert report.total_sentence_count == 5
assert report.numeric_sentence_count == 4
assert report.python_candidate_count == 4
assert report.quantity_type_counts["percentage"] == 1
assert report.quantity_type_counts["money"] == 1
assert report.period_class_counts["forecast"] == 1
assert report.route_counts["KOSIS_RETRIEVAL"] >= 1
```

Test sentence records preserve exact substrings returned by `split_sentences`, and expose:

- raw quantity strings
- normalized period or empty string
- period class: past/current/forecast/unknown
- claim type
- source type and route
- Python candidate and actual rule/reason

Test structure summaries:

- min, max, mean, median, Q1, Q3
- IQR outlier row numbers for body length and sentence count
- no outlier classification below four valid articles

**Step 2: Run focused tests to verify RED**

Run:

```powershell
python -m pytest -q tests/test_experiment_eda.py -k "sentence or aggregate or outlier"
```

Expected: new assertions fail.

**Step 3: Implement feature extraction by reusing existing rules**

For every exact sentence from `split_sentences(cleaned_body)`:

```python
quantities = extract_quantities(sentence)
candidate = detect.is_candidate(sentence)
rule_id = detect.which_rule(sentence)
source = source_classify.classify(sentence)
```

Normalize period only for valid article dates. If the date is invalid, preserve quantities and routing but use an empty normalized period rather than inventing a date.

Map quantity types deterministically:

- `%`, `퍼센트`, `%p`, `포인트` → `percentage`
- `원` with any scale → `money`
- `명`, `인`, `가구`, `세대` → `people_household`
- `건`, `배`, `위`, `호` → `count_rank`
- everything else → `other`

Derive period class from the sentence and claim type without HCX:

- forecast claim type or future expression → `forecast`
- normalized period earlier than article date → `past`
- normalized period matching article year/month → `current`
- otherwise → `unknown`

Use a deterministic nearest-rank percentile helper. Only apply the IQR rule for at least four articles.

**Step 4: Run Task 1–2 tests**

Run:

```powershell
python -m pytest -q tests/test_experiment_eda.py
```

Expected: all pass.

**Step 5: Commit**

```powershell
git add clafact/experiment_eda.py tests/test_experiment_eda.py
git commit -m "feat: profile verification article claims"
```

---

### Task 3: Pure dashboard presentation and article filtering

**Files:**
- Create: `clafact/experiment_eda_view.py`
- Create: `tests/test_experiment_eda_view.py`

**Step 1: Write failing view-model tests**

Cover:

```python
def test_single_article_uses_detail_cards_not_distribution():
    view = build_eda_view(single_article_report)
    assert view.structure_chart_mode == "single"
    assert view.body_length_bins == ()

def test_multiple_articles_build_bounded_distribution_bins():
    view = build_eda_view(many_article_report)
    assert view.structure_chart_mode == "distribution"
    assert sum(item.count for item in view.body_length_bins) == len(many_article_report.articles)
```

Also test:

- quality KPI values
- issue-reason chart rows
- independent KPI cards for all sentences, numeric sentences, Python candidates, and KOSIS routing
- Python candidates split into numeric and non-numeric rule candidates
- explicit text that KPI populations can overlap and are not funnel stages; label KOSIS routing as currently scoped to Python candidates
- zero-filled known quantity/period/route categories
- article filtering by issue presence, candidate-count range, and body-length band
- problem-row output contains row number, title, and issue only
- selected-article sentence rows contain only exact stored sentences and extracted evidence
- problem table limit is explicit and deterministic

**Step 2: Run tests to verify RED**

Run:

```powershell
python -m pytest -q tests/test_experiment_eda_view.py
```

Expected: module import failure.

**Step 3: Implement pure presentation helpers**

Create:

```python
def build_eda_view(report: EdaReport) -> EdaView: ...
def filter_articles(
    report: EdaReport,
    *,
    quality: str = "all",
    body_band: str = "all",
    min_candidates: int = 0,
) -> tuple[EdaArticle, ...]: ...
def selected_article_rows(article: EdaArticle) -> tuple[dict[str, object], ...]: ...
```

Keep chart rows small and aggregated. Do not return full cleaned bodies in the problem-row table.

**Step 4: Run view and analysis tests**

Run:

```powershell
python -m pytest -q tests/test_experiment_eda.py tests/test_experiment_eda_view.py
```

Expected: all pass.

**Step 5: Commit**

```powershell
git add clafact/experiment_eda_view.py tests/test_experiment_eda_view.py
git commit -m "feat: build verification EDA view model"
```

---

### Task 4: Streamlit integrated EDA dashboard

**Required skill:** Use `developing-with-streamlit` and load the installed-version references for dashboards, data display, selection widgets, session state, and performance before editing.

**Files:**
- Modify: `streamlit_app.py`
- Modify: `tests/test_experiment_lab_ui.py`
- Create: `tests/test_experiment_eda_session.py`
- Create: `clafact/experiment_eda_session.py`

**Step 1: Write failing session and UI wiring tests**

Pure session helper tests must cover:

- file hash plus selected row range forms the cache key
- a new file invalidates prior EDA and selected article
- 1,000 rows or fewer auto-select the complete range
- 1,001 rows require explicit range confirmation
- selected range never exceeds 1,000 rows

UI smoke assertions must require:

- `CSV 통합 EDA`
- quality, structure, numeric-claim, and selected-article sections
- explicit “Python 규칙만 사용하며 HCX를 자동 호출하지 않습니다”
- over-limit range form
- no old raw `st.bar_chart([len(article["body"]) ...])`
- no EDA call to `HcxClient`, operating `Store`, `process_pending`, or KOSIS clients

**Step 2: Run tests to verify RED**

Run:

```powershell
python -m pytest -q tests/test_experiment_eda_session.py tests/test_experiment_lab_ui.py
```

Expected: new helper/module/UI assertions fail.

**Step 3: Implement session-scope cache helpers**

Create helpers such as:

```python
MAX_EDA_ROWS = 1_000

def eda_file_signature(payload: bytes) -> str: ...
def resolve_eda_range(row_count: int, requested_start: int | None,
                      requested_end: int | None) -> EdaRange: ...
def eda_cache_key(signature: str, selected_range: EdaRange) -> str: ...
```

These helpers must not retain payload bytes or article bodies.

**Step 4: Replace the existing EDA expander**

Render:

1. quality KPI cards and reason chart
2. structure statistics and either single-article cards or distribution charts
3. independent numeric-claim KPI cards, numeric/non-numeric Python candidate split, and category charts
4. filter controls, problem rows, and selected-article evidence table

Use native Streamlit containers, metrics, charts, dataframe, forms, stable keys, and `width="stretch"` or defaults. Do not add deprecated `use_container_width`.

For more than 1,000 source rows:

- render the range form first
- do not call `analyze_rows` until submitted
- allow a maximum span of 1,000
- label all results with the analyzed row interval and total source rows

For one valid article, show cards and the selected-article table without a distribution chart.

**Step 5: Run focused Streamlit-related tests**

Run:

```powershell
python -m pytest -q tests/test_experiment_eda.py tests/test_experiment_eda_view.py tests/test_experiment_eda_session.py tests/test_experiment_lab_ui.py
```

Expected: all pass.

**Step 6: Compile and inspect**

Run:

```powershell
python -m py_compile clafact/experiment_eda.py clafact/experiment_eda_view.py clafact/experiment_eda_session.py streamlit_app.py
git diff --check
```

Expected: both commands exit zero.

**Step 7: Commit**

```powershell
git add clafact/experiment_eda_session.py streamlit_app.py tests/test_experiment_eda_session.py tests/test_experiment_lab_ui.py
git commit -m "feat: add integrated verification EDA dashboard"
```

---

### Task 5: Safety, regression, and issue-ledger evidence

**Files:**
- Modify: `docs/VERIFICATION_LAB_ISSUE_LEDGER.md`
- Modify: `tests/test_experiment_eda.py`
- Modify: `tests/test_experiment_lab_ui.py`

**Step 1: Add safety regression tests**

Assert:

- every displayed EDA sentence is a substring of its cleaned uploaded article
- analysis invokes no HCX judge
- no operating or research store is constructed by EDA
- invalid dates do not cause current-date fabrication
- one bad row does not abort later rows
- problem tables do not expose entire raw bodies

**Step 2: Run tests to verify RED where applicable**

Run:

```powershell
python -m pytest -q tests/test_experiment_eda.py tests/test_experiment_lab_ui.py
```

Expected: any newly uncovered contract fails before the fix.

**Step 3: Apply minimal fixes and update the issue ledger**

Add a new ledger entry documenting:

- the one-row oversized chart failure
- lack of data-quality visibility
- chosen Python-only EDA boundary
- 1,000-row analysis guard
- tests and implementation commits
- any remaining limitations

Do not mark limitations resolved unless verified.

**Step 4: Run the feature suite**

Run:

```powershell
python -m pytest -q tests/test_experiment_eda.py tests/test_experiment_eda_view.py tests/test_experiment_eda_session.py tests/test_experiment_lab.py tests/test_experiment_lab_ui.py tests/test_experiment_input.py
```

Expected: all pass.

**Step 5: Run full verification**

Run:

```powershell
python -m pytest -q
python -m py_compile clafact/experiment_eda.py clafact/experiment_eda_view.py clafact/experiment_eda_session.py streamlit_app.py
git diff --check
git status --short
```

Expected:

- no new failures beyond the three existing main baseline source-string tests
- compilation and diff checks pass
- worktree is clean after the final commit

Re-run the three baseline failures on `main` before classifying them as pre-existing.

**Step 6: Commit**

```powershell
git add docs/VERIFICATION_LAB_ISSUE_LEDGER.md tests/test_experiment_eda.py tests/test_experiment_lab_ui.py
git commit -m "docs: record integrated EDA quality evidence"
```

