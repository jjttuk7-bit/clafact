# Shadow Semantic Summary Cards — Design

## What this adds

The Shadow Mode page will show two read-only summary areas. They make the
already-implemented KOSIS semantic-verification flow visible without changing
an operational verdict, a Claim completion record, or a downloaded CSV.

## Chosen approach

The page derives its values from the existing research stores and the persisted
`reports/e2e_snapshot_verdict_latest.json` file. This is preferable to a
separate dashboard store (which would duplicate data and risk stale counts) and
to hard-coded demo metrics (which would not show the real state).

## Cards

### Current Shadow run

For the currently open Shadow run, show:

- candidate sentences;
- KOSIS candidate searches;
- reviewed table mappings;
- Evidence snapshots / actual-value comparisons;
- match, mismatch, and unverifiable counts;
- completed Claims.

The counts are derived from the same run records that are later exported to
CSV. A comparison remains a research result; no value in this panel changes an
operational Claim.

### Golden-set E2E overview

For the persisted E2E verdict list, show:

- total candidates;
- final verdict count;
- match, mismatch, and unverifiable counts;
- evidence-backed candidates (one or more snapshot IDs).

The card displays an explicit unavailable state when the JSON file does not
exist or cannot be parsed. It never substitutes a mock result.

## Data flow

`Shadow run + mapping/search/comparison/completion stores` → pure summary
function → Current-run cards

`e2e_snapshot_verdict_latest.json` → pure summary function → Golden-set cards

Existing comparison rows continue separately to the JSON/CSV export path.

## Error handling and tests

Summary helpers tolerate malformed or missing optional values and count only
recognized final verdicts. Unit tests cover current-run aggregation, duplicate
E2E components, evidence-backed counts, and an empty list. The existing Shadow
export and Claim-completion tests remain the regression guard.
