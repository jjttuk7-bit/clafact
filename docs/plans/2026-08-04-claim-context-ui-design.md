# Claim Context Inheritance and Selection Label Design

**Decision:** Infer a Claim Card period only from an article-level observation period that is explicit and unambiguous; otherwise keep the card blocked for human confirmation. Show long multi-value sentences with a compact label that preserves the row number and signals multiple numeric values.

## Problem

The selected product-price sentence has no direct time expression. Its Claim Card therefore correctly blocks KOSIS search, but the surrounding article has an explicit observation period (`지난달`, relative to the article date). The current UI also truncates the long sentence label, making `달걀(6.9%)` look inconsistent with the original sentence.

## Chosen approach

1. Scan all Shadow rows in the article for **strong observation-period cues**: absolute year-month or relative `지난달`/`이번달` expressions. Do not use a bare month such as `9월`, because it may be a comparison anchor rather than the article's observation period.
2. If exactly one normalized period is found, provide it to a selected Claim Card only when that card has no direct period. If none or more than one is found, leave the period empty and require review.
3. Record the inherited period in the card notes/UI with its source row number.
4. Build selection labels as `#N · 복수 수치 K개 · <short preview>` for multi-number sentences, avoiding a misleading clipped tail.

## Non-goals

- Do not split a sentence into Atomic Claims; that remains ISS-002.
- Do not inherit a period from a bare month, a baseline date, or ambiguous surrounding text.
- Do not automatically decide the KOSIS item/coordinate.

## Verification

- An article with one `지난달` context gives a later value-only sentence the normalized period.
- An article with conflicting strong periods leaves the value-only sentence without a period.
- A selected multi-number sentence label contains the row ID and `복수 수치` count instead of ending at an arbitrary clipped token.
