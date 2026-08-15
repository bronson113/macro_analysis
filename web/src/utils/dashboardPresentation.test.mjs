import test from 'node:test';
import assert from 'node:assert/strict';

import {
  buildFreshnessStatus,
  DASHBOARD_SECTIONS,
  splitReportSections,
} from './dashboardPresentation.js';

test('dashboard sections follow decision relevance with source health last', () => {
  assert.deepEqual(
    DASHBOARD_SECTIONS.map(({ key, navLabel }) => [key, navLabel]),
    [
      ['editorial', 'Editorial Review'],
      ['dailyBrief', 'Daily Brief'],
      ['trends', 'Trends'],
      ['indicators', 'Indicators'],
      ['deepDive', 'Deep Dive'],
      ['sourceHealth', 'Source Health'],
    ],
  );
});

test('splitReportSections extracts summary, active situation, risks, and full report tabs', () => {
  const markdown = [
    '# Daily Report',
    '',
    '## Notable Summary',
    '- First summary item',
    '',
    '## 1. Active Macro Situation (2x2 Matrix Analysis)',
    'Active macro body',
    '',
    '## 2. Federal Reserve & Reserve Liquidity Proxy',
    'Liquidity body',
    '',
    '## 8. Market Risk, Volatility & Commodities',
    'Risk body',
    '',
    '*Report auto-generated.*',
  ].join('\n');

  const sections = splitReportSections(markdown);

  assert.equal(sections.summary.includes('- First summary item'), true);
  assert.equal(sections.active.includes('Active macro body'), true);
  assert.equal(sections.active.includes('Liquidity body'), false);
  assert.equal(sections.risks.includes('Risk body'), true);
  assert.equal(sections.full, markdown);
});

test('buildFreshnessStatus reports fresh, aging, and stale data using exact timestamps', () => {
  const fresh = buildFreshnessStatus({
    generatedAt: '2026-07-28T12:00:00Z',
    now: new Date('2026-07-28T18:00:00Z'),
  });
  const aging = buildFreshnessStatus({
    generatedAt: '2026-07-27T12:00:00Z',
    now: new Date('2026-07-28T18:00:00Z'),
  });
  const stale = buildFreshnessStatus({
    generatedAt: '2026-07-25T12:00:00Z',
    now: new Date('2026-07-28T18:00:00Z'),
  });

  assert.equal(fresh.tone, 'fresh');
  assert.equal(fresh.label, 'Fresh');
  assert.equal(fresh.ageLabel, '6h old');
  assert.equal(aging.tone, 'aging');
  assert.equal(aging.ageLabel, '1d 6h old');
  assert.equal(stale.tone, 'stale');
  assert.equal(stale.label, 'Stale');
});
