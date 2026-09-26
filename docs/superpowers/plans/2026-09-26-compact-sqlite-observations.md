# Compact SQLite Observations Implementation Plan

> **For agentic workers:** Use test-driven development and verify each task before moving on.

**Goal:** Commit an observation SQLite store below 5,000,000 bytes and batch pipeline writes without changing analytical results.

**Architecture:** One SQLite row per indicator contains an LZMA-compressed CSV payload. `MacroStorage` delegates observation reads and writes to a focused store module. The store updates affected indicator rows in a single transaction and exposes a bulk frame reader for existing consumers.

**Tech Stack:** Python standard-library `sqlite3` and `lzma`, pandas, pytest, GitHub Actions.

## Global Constraints

- Preserve revision and as-of behavior, unknown columns, and public `MacroStorage` return shapes.
- Production SQLite database must stay below 5,000,000 bytes after a daily run.
- Remove the committed observation CSV only after the SQLite migration verifies every row.
- Add no new runtime dependency.

---

### Task 1: SQLite store and migration

**Files:** Create `observation_sqlite.py`; modify `config.py`, `storage.py`; add tests in `tests/test_storage_resilience.py` or a new test file.

- [ ] Write failing tests for import/export parity, compressed size, revisions, as-of reads, and operator-owned columns.
- [ ] Implement compact SQLite schema, migration, per-key reads, and transactional writes.
- [ ] Verify focused tests and benchmark a representative write against current CSV storage.

### Task 2: Batch pipeline observation writes

**Files:** Modify `storage.py`, `raw_data_engine.py`, `valuation.py`; add focused pipeline tests.

- [ ] Write failing tests that require multiple indicator frames to commit in one transaction and preserve existing outputs.
- [ ] Implement `save_observation_batches` and make stock-relative and sector valuation writers use it.
- [ ] Verify focused tests and measure the write-path improvement.

### Task 3: Update direct readers and workflow

**Files:** Modify `weekly_digest.py`, `backfill_snapshots.py`, `validate_fresh_macro_data.py`, `main.py`, `.github/workflows/daily_macro.yml`, `README.md`, and relevant tests.

- [ ] Write failing tests for each direct reader against the SQLite store and the workflow size gate.
- [ ] Migrate the committed data, remove the compressed CSV, and update the workflow to commit the SQLite database.
- [ ] Run full Python and web tests, lint, build, and data parity checks.
- [ ] Commit, push, and verify GitHub Actions completes through Pages deployment.
