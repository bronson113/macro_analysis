import test from 'node:test';
import assert from 'node:assert/strict';

import {
  buildFreshnessStatus,
  buildRegimePresentation,
  DASHBOARD_SECTIONS,
  splitReportSections,
} from './dashboardPresentation.js';

const fixture = {
  macro_regime: {
    current_state: {
      policy: 'RESTRICTIVE',
      liquidity: 'ABUNDANT',
      situation_id: 4,
    },
    policy: {
      state: 'RESTRICTIVE',
      policy_gap: 0.8,
      historical_percentile: 78,
    },
    liquidity: {
      state: 'ABUNDANT',
      normalized_liquidity_pct_gdp: 19.5,
      current_percentile: 75,
      historical_p40: 13,
      historical_p60: 17,
    },
    momentum: {
      policy: { '30d': 'EASING', '90d': 'EASING' },
      liquidity: { '30d': 'DETERIORATING', '90d': 'STABLE' },
    },
    consensus: { quality: 'UNAVAILABLE' },
    quadrant: {
      situation_id: 4,
      description: 'Policy remains restrictive while reserve liquidity is abundant.',
    },
    data_quality: { quality: 'OK' },
  },
};

test('presents level state separately from momentum and consensus', () => {
  const view = buildRegimePresentation(fixture);

  assert.deepEqual(view.sections.map(section => section.label), [
    'Current State', 'Momentum', 'Consensus', 'Interpretation', 'Data Quality',
  ]);
  assert.equal(view.sections[0].value.includes('Restrictive + Abundant'), true);
  assert.equal(view.sections[1].value.includes('Deteriorating'), true);
});

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
