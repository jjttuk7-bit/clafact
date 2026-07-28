# KOSIS Evidence Identity Implementation Plan

> **For Codex:** Use test-driven development for each behavior below.

**Goal:** Allow multiple traceable evidence objects from one KOSIS table when their core indicator or selected item differs.

**Architecture:** Keep the KOSIS table ID as source identity, and add a deterministic `evidence_id` calculated from the table ID, indicator, and selected source items. Migrate the research-only SQLite stores without deleting legacy rows. Shadow mappings and exports carry the object ID so a sentence can be connected to the exact rate or item used.

**Tech stack:** Python dataclasses, SQLite, pytest, Streamlit.

---

### Task 1: Evidence-object identity

**Files:** `clafact/kosis_evidence.py`, `tests/test_kosis_evidence.py`

1. Add a failing test showing that `전월비` and `전년동월비` from the same table have different stable IDs.
2. Add deterministic identity generation and serialize it as `evidence_id`.
3. Run the focused test.

### Task 2: Preserve and migrate stored objects

**Files:** `clafact/kosis_evidence_store.py`, `tests/test_kosis_evidence_store.py`

1. Add a failing test that saves both rate objects from one table.
2. Change the SQLite primary key to evidence ID through a safe legacy-table migration.
3. Add a migration test for a legacy table-ID keyed database.
4. Run focused store tests.

### Task 3: Map and export exact evidence objects

**Files:** `clafact/kosis_shadow_mapping.py`, `clafact/kosis_shadow_mapping_store.py`, `clafact/shadow_export.py`, related tests.

1. Add failing tests for two mappings from one table with distinct evidence IDs.
2. Store and export `evidence_id`; retain `table_id` for source lookup.
3. Run focused mapping/export tests.

### Task 4: Wire Streamlit selection to the exact object

**Files:** `streamlit_app.py`, registry/status helpers and tests as needed.

1. Show `표 ID · 핵심 지표 · 선택 항목` in selection labels.
2. Save mappings with the selected evidence ID.
3. Verify static compilation and Streamlit AppTest.
