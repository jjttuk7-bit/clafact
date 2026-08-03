# Signed Quantity Parsing Design

**Decision:** Preserve ASCII minus (`-`), Unicode minus (`−`), and explicit plus (`+`) as part of every numeric quantity parsed by ClaFact.

## Problem

The numeric parser begins its quantity pattern at a digit. In `배추(-34.5%)`, it therefore extracts `34.5%` and loses the negative sign. This can invert a verification verdict.

## Scope

- Extend the existing quantity expression with an optional leading sign.
- Normalize Unicode minus to the standard negative numeric value.
- Preserve the original signed text in `Quantity.raw`.
- Ensure scaling applies to signed values, such as `-2만 명 → -20000`.

## Non-goals

- Do not split one sentence into multiple Atomic Claims. That is ISS-002.
- Do not alter period, indicator, KOSIS mapping, or verdict formula logic.

## Data flow

```text
"배추(-34.5%)"
  → Quantity.raw = "-34.5%"
  → Quantity.value = -34.5
  → Quantity.normalized_value = -34.5
  → Claim Card displays "-34.5%"
```

## Verification

Tests must cover ASCII minus, Unicode minus, explicit plus, and scaled negative quantities. Existing positive-number and contextual-identifier tests must remain green.
