import test from 'node:test';
import assert from 'node:assert/strict';

import {
  buildFreshnessStatus,
  buildRegimePresentation,
  DASHBOARD_SECTIONS,
  splitReportSections,
} from './dashboardPresentation.js';
import { descriptions } from './descriptions.js';

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
    consensus: {
      quality: 'OK',
      selected_survey_date: '2026-07-01',
      publication_date: '2026-07-10',
      selected_target_date: '2027-01-01',
      selected_horizon_months: 6,
      metric: 'FED_FUNDS_RATE_AND_FED_BALANCE_SHEET_ASSETS',
      unit: 'percent_and_billions_usd',
      source_url: 'https://www.newyorkfed.org/sme',
      parsing_status: 'OK',
    },
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
  const consensus = view.sections.find(section => section.label === 'Consensus');
  assert.equal(consensus.details.find(item => item.label === 'Publication date').value, '2026-07-10');
  assert.equal(consensus.details.find(item => item.label === 'Horizon').value, '6 months');
  assert.equal(consensus.details.find(item => item.label === 'Source URL').value, 'https://www.newyorkfed.org/sme');
});

test('uses inclusive scarce and abundant liquidity boundary copy', () => {
  assert.match(descriptions.liquidity_level, /at-or-below P40/);
  assert.match(descriptions.liquidity_level, /at-or-above P60/);
});

test('renders unavailable when every input age is null', () => {
  const view = buildRegimePresentation({
    ...fixture,
    macro_regime: {
      ...fixture.macro_regime,
      data_quality: {
        quality: 'PARTIAL',
        input_ages: { dff: null, core_pce: null, rstar: null },
      },
    },
  });
  const qualitySection = view.sections.find(section => section.label === 'Data Quality');
  const ages = qualitySection.details.find(item => item.label === 'Input ages');

  assert.equal(ages.value, 'Unavailable');
});

test('renders stale or unavailable consensus metadata and data-quality reasons', () => {
  const view = buildRegimePresentation({
    ...fixture,
    macro_regime: {
      ...fixture.macro_regime,
      consensus: {
        quality: 'STALE',
        publication_date: '2026-01-01',
        selected_horizon_months: 6,
        parsing_status: 'UNAVAILABLE',
        reasons: ['Consensus survey is stale (226 days old)'],
      },
      data_quality: {
        quality: 'PARTIAL',
        actionability: 'WITHHELD',
        actionability_reasons: ['Policy axis is neutral'],
        input_ages: { dff: 2, rstar: 80 },
      },
    },
  });

  const consensus = view.sections.find(section => section.label === 'Consensus');
  assert.equal(consensus.value.includes('Stale'), true);
  assert.equal(consensus.details.find(item => item.label === 'Publication date').value, '2026-01-01');
  assert.equal(consensus.details.find(item => item.label === 'Parsing status').value, 'UNAVAILABLE');
  assert.equal(
    consensus.details.find(item => item.label === 'Consensus reasons').value,
    'Consensus survey is stale (226 days old)',
  );

  const quality = view.sections.find(section => section.label === 'Data Quality');
  assert.equal(quality.details.find(item => item.label === 'Input ages').value, 'dff 2d · rstar 80d');
  assert.match(
    quality.details.find(item => item.label === 'Reasons and conflicts').value,
    /Policy axis is neutral/,
  );
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
