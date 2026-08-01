import test from 'node:test';
import assert from 'node:assert/strict';

import { buildAssessmentView } from './evidencePresentation.js';

test('buildAssessmentView exposes posture range coverage and missing evidence', () => {
  const view = buildAssessmentView({
    posture: 'WATCH',
    score_range: [2.1, 5.4],
    coverage_pct: 71.4,
    positive_factors: [{ factor_id: 'liquidity', explanation: 'Liquidity expanding.' }],
    negative_factors: [{ factor_id: 'real_yield', explanation: 'Real yields restrictive.' }],
    missing_evidence: [{ factor_id: 'valuation', missing_reason: 'Insufficient history.' }],
  });

  assert.deepEqual(view, {
    tone: 'positive',
    rangeLabel: '+2.1 to +5.4',
    coverageLabel: '71% evidence coverage',
    positives: ['Liquidity expanding.'],
    negatives: ['Real yields restrictive.'],
    missing: ['Valuation: Insufficient history.'],
  });
});
