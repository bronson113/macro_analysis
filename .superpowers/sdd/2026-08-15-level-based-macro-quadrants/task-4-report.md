# Task 4 Review: Analyzer, Matrix, and Backward-Compatible Snapshot Integration

## Scope

Implemented Task 4 on master `0336898` while preserving the merged evidence-analysis
architecture. The change is limited to the Task 4 integration boundary:

- `analyzer.py`
- `macro_matrix.py`
- `storage.py`
- `raw_data_engine.py`
- `tests/test_macro_pipeline.py`

The generated CSV/JSON and lock-file changes present in the checkout were treated as
concurrent artifacts and were not edited, staged, restored, or deleted.

## TDD Evidence

The new state-based tests were written before production integration. The required
focused RED run was:

```text
PYTHONPATH=. .venv/bin/pytest tests/test_macro_pipeline.py -q
9 failed, 45 passed
```

The failures were the expected old-matrix signature, missing analyzer method and
consensus constructor boundary, missing raw-payload argument, and absent snapshot
fields. After the smallest complete implementation, the same focused suite passed.

## Implementation

### Level-only matrix

`MacroMatrixEngine.classify_situation(policy_state, liquidity_state, *, quality,
context)` now accepts the current policy and liquidity level states as its only
quadrant axes:

| Policy | Liquidity | Situation |
| --- | --- | ---: |
| `ACCOMMODATIVE` | `ABUNDANT` | 1 |
| `ACCOMMODATIVE` | `SCARCE` | 2 |
| `RESTRICTIVE` | `SCARCE` | 3 |
| `RESTRICTIVE` | `ABUNDANT` | 4 |

Neutral, unsupported, missing, stale, insufficient, or materially conflicted inputs
return Situation 0. `PARTIAL` quality can preserve a valid level quadrant. CPI,
Sahm, yield-curve, M2, momentum, and consensus values are carried as interpretation
context only; changing them cannot change `situation_id`. Existing sector hypotheses
and contextual warnings remain attached to the returned structured result.

### Analyzer orchestration

`MacroAnalyzer.analyze_macro_regime(as_of=None, consensus_records=None)` now:

1. Loads the complete dated policy/liquidity input series from storage, with a
   configurable neutral-rate key fallback (`rstar`, `neutral_real_rate`, or
   `hlw_rstar`).
2. Calls the pure `classify_policy_level` and `classify_liquidity_level` boundaries.
3. Retrieves optional consensus through an injectable provider or the storage
   `get_consensus_records()` boundary. Retrieval/parsing failure yields an unavailable
   overlay and never blocks the current level analysis.
4. Composes policy/liquidity quality, input ages, missing reasons, conflicts, and
   independent 30/90-day momentum into `current_state`, `momentum`, `consensus`, and
   `data_quality` result sections.
5. Passes only the two current state strings plus explicit quality/context to the
   matrix.

`generate_full_snapshot()` now persists the new scalar regime fields, returns the
   structured regime sections, and passes the structured regime to the raw payload
   writer.

### Snapshot compatibility

`SNAPSHOT_COLUMNS` now covers current policy/liquidity levels and thresholds, real
policy/r-star/gap values, policy and liquidity momentum, consensus directions/values/
dates/quality, quadrant quality and situation ID, and both canonical and source-age
aliases. Existing `_normalize_schema`/`_upsert_rows` behavior continues to union
incoming fields with existing/operator-owned columns. Legacy snapshot headers are
readable with missing new fields represented as blank values (`pd.NA`).

### Raw payload

`RawDataEngine.build_raw_payload(..., macro_regime=...)` exports the structured regime
alongside the existing evidence payload. JSON cleaning now serializes pandas/datetime
timestamps and missing scalar values safely.

## Tests

Fresh verification with `PYTHONPATH=.`:

```text
PYTHONPATH=. .venv/bin/pytest tests/test_macro_pipeline.py -q
54 passed in 1.76s

PYTHONPATH=. .venv/bin/pytest tests/test_macro_pipeline.py tests/test_dashboard_history.py -q
57 passed in 2.09s

PYTHONPATH=. .venv/bin/pytest -q
157 passed in 7.31s
```

Additional static verification passed:

```text
git diff --check -- analyzer.py macro_matrix.py storage.py raw_data_engine.py tests/test_macro_pipeline.py
python -m py_compile analyzer.py macro_matrix.py storage.py raw_data_engine.py
```

## Self-review

- No P2-or-higher integration issue remains in the reviewed Task 4 boundary.
- The matrix has no fallback from level states to recent direction; legacy injected
  test doubles are supported only by a narrowly scoped keyword-signature fallback in
  the analyzer migration path.
- Consensus remains explicitly optional and is not used to select or withhold a
  valid current quadrant.
- Existing generated data artifacts remain dirty by design and are excluded from the
  Task 4 commit.

## Result

Task 4 is ready to commit. The final commit should include only the five Task 4 source/
test files and this report.
