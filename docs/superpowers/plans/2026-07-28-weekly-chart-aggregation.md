# Weekly Chart Aggregation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Render weekly averages instead of daily data for historical chart viewports longer than three calendar years.

**Architecture:** Add a pure chart-data utility that determines whether a visible date range exceeds three calendar years and, if so, returns calendar-week buckets with independently averaged numeric fields. Keep viewport state and interaction in `TrendGraphs`; only replace the data passed to Recharts with the utility's output.

**Tech Stack:** React 19, Recharts 3, Vite 8, Node built-in test runner, oxlint.

## Global Constraints

- Do not add runtime dependencies.
- Do not change backend data formats or fetch endpoints.
- Preserve the range controls and wheel-zoom interaction.
- Aggregate only when the visible date span is strictly longer than three calendar years; exactly three years remains daily.
- Average each numeric field independently, ignoring `null` and missing values.

---

## File Structure

- Create `web/src/utils/chartAggregation.js`: Pure date-span and weekly-average transformation for chart rows.
- Create `web/src/utils/chartAggregation.test.mjs`: Node tests for the aggregation threshold, weekly averages, null handling, and date labels.
- Modify `web/src/components/TrendGraphs.jsx`: Transform the existing visible viewport data before passing it to Recharts.

### Task 1: Add and integrate visible-viewport aggregation

**Files:**
- Create: `web/src/utils/chartAggregation.js`
- Create: `web/src/utils/chartAggregation.test.mjs`
- Modify: `web/src/components/TrendGraphs.jsx`

**Interfaces:**
- Produces: `prepareChartData(points: Array<Record<string, unknown>>): Array<Record<string, unknown>>`.
- Consumes: the visible daily data slice already produced in `TrendGraphs`.

- [ ] **Step 1: Write the failing test**

Create `web/src/utils/chartAggregation.test.mjs` with boundary and bucket tests:

```js
import test from 'node:test';
import assert from 'node:assert/strict';
import { prepareChartData } from './chartAggregation.js';

test('keeps a three-calendar-year chart range at daily granularity', () => {
  const points = [
    { date: '2020-01-01', sp500: 100 },
    { date: '2023-01-01', sp500: 200 },
  ];

  assert.equal(prepareChartData(points).length, 2);
});

test('averages numeric fields into calendar weeks over three years', () => {
  const points = [
    { date: '2020-01-01', sp500: 100, vix: 10, cpi_yoy: null },
    { date: '2020-01-02', sp500: 200, vix: null, cpi_yoy: 2 },
    { date: '2020-01-06', sp500: 300, vix: 30, cpi_yoy: 4 },
    { date: '2023-01-02', sp500: 400, vix: 40, cpi_yoy: 6 },
  ];

  assert.deepEqual(prepareChartData(points), [
    { date: '2020-01-02', sp500: 150, vix: 10, cpi_yoy: 2 },
    { date: '2020-01-06', sp500: 300, vix: 30, cpi_yoy: 4 },
    { date: '2023-01-02', sp500: 400, vix: 40, cpi_yoy: 6 },
  ]);
});

test('leaves invalid-date rows outside weekly buckets', () => {
  const points = [
    { date: 'not-a-date', sp500: 100 },
    { date: '2020-01-01', sp500: 200 },
    { date: '2023-01-02', sp500: 300 },
  ];

  assert.deepEqual(prepareChartData(points), [
    { date: 'not-a-date', sp500: 100 },
    { date: '2020-01-01', sp500: 200 },
    { date: '2023-01-02', sp500: 300 },
  ]);
});
```

- [ ] **Step 2: Run test to verify it fails**

Run: `npm test -- --test-name-pattern="calendar"`

Expected: FAIL because `chartAggregation.js` and `prepareChartData` do not exist.

- [ ] **Step 3: Write minimal implementation**

Create `chartAggregation.js` with:

```js
const YEARS_TO_AGGREGATE = 3;

export const prepareChartData = (points) => {
  // Return points unchanged unless the first-to-last valid date exceeds
  // three calendar years. Otherwise group by Sunday-ending UTC week,
  // average finite numeric fields, and retain the last source date.
};
```

Use UTC calendar calculations for consistent week boundaries. Use the latest source date in a week as that weekly point's `date`. Build each output row from numeric fields only; do not copy internal `__index` metadata into aggregated rows. If a week has no finite value for a field, set that field to `null`.

- [ ] **Step 4: Run test to verify it passes**

Run: `npm test -- --test-name-pattern="calendar"`

Expected: PASS for all aggregation tests.

- [ ] **Step 5: Integrate the utility with the chart component**

In `web/src/components/TrendGraphs.jsx`, import `prepareChartData`. Replace the `visibleData` memo with a daily visible slice followed by `prepareChartData`, preserving the full daily dataset for viewport calculations and wheel handling:

```js
const visibleData = useMemo(() => {
  const dailyVisibleData = indexedData.slice(visibleViewport.start, visibleViewport.end);
  return prepareChartData(dailyVisibleData);
}, [indexedData, visibleViewport]);
```

- [ ] **Step 6: Run the web verification suite**

Run:

```bash
npm test
npm run lint
npm run build
```

from `web/`.

Expected: all utility tests pass, oxlint reports no errors, and Vite produces a production build.

- [ ] **Step 7: Commit**

```bash
git add web/src/components/TrendGraphs.jsx web/src/utils/chartAggregation.js web/src/utils/chartAggregation.test.mjs docs/superpowers/plans/2026-07-28-weekly-chart-aggregation.md
git commit -m "feat: aggregate long chart ranges weekly"
```
