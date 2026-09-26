# Compact SQLite Observation Store

## Goal

Replace the compressed observation CSV with a committed SQLite database that stays below 5,000,000 bytes and speeds up daily updates. Preserve historical revisions, point-in-time reads, and the existing report outputs.

## Storage design

Store one row per indicator key in SQLite. Each row contains an LZMA-compressed, self-describing CSV payload with that indicator's observation rows, including vintage and operator-owned columns. A local prototype with the current 120,400 observations occupied 807,936 bytes. The SQLite database is the source of truth and is committed; the compressed observation CSV is removed after migration.

`MacroStorage` reads only the requested indicator when serving a series or latest observation. A bulk reader exists for the few paths that need all observations. Existing CSV-backed custom-path fixtures may remain supported for compatibility, but production uses SQLite.

## Writes and batching

For an observation update, decompress only the affected indicator payload, apply existing upsert semantics, recompress it, and replace it in one SQLite transaction. Add a batch API accepting multiple indicator frames, and change raw stock-relative and sector valuation writers to submit all their frames in one transaction. Preserve unknown columns and distinct source vintages.

The daily workflow migrates the existing compressed CSV to SQLite, validates the new store, and checks the committed database size before pushing. Migration is repeatable and never removes the CSV until the SQLite data has been verified. No separate observation CSV is committed thereafter.

## Verification

Use failing tests for migration, latest and point-in-time reads, revisions, unknown-column retention, batch atomicity, and size. Run the full Python and web suites, compare representative output against the previous store, benchmark repeated writes, then push and verify a complete GitHub Actions run including deployment.
