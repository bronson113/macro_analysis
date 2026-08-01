import test from 'node:test';
import assert from 'node:assert/strict';

import { buildSourceHealthView } from './sourceHealthPresentation.js';

test('buildSourceHealthView exposes current or stale status and source failure details', () => {
  const view = buildSourceHealthView({
    source: 'FRED',
    fetch_key: 'treasury_10y',
    status: 'ERROR',
    is_stale: true,
    error_category: 'network',
    message: 'Timed out while fetching the series.',
    fetch_time: '2026-08-01T08:00:00Z',
  });

  assert.deepEqual(view, {
    sourceLabel: 'FRED · treasury_10y',
    statusLabel: 'ERROR',
    statusTone: 'negative',
    freshnessLabel: 'Stale',
    errorLabel: 'Network error',
    message: 'Timed out while fetching the series.',
    fetchTimeLabel: '2026-08-01 08:00:00 UTC',
  });
});
