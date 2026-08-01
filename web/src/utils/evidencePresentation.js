const POSTURE_TONES = {
  WATCH: 'positive',
  AVOID: 'negative',
};

function formatScore(value) {
  const numeric = Number(value);
  if (!Number.isFinite(numeric)) return 'Unavailable';

  return `${numeric > 0 ? '+' : ''}${numeric.toFixed(1)}`;
}

function formatFactor(factor, missing = false) {
  if (typeof factor === 'string') return factor;
  if (!factor || typeof factor !== 'object') return 'Unavailable evidence detail.';

  const explanation = factor.explanation || factor.missing_reason || factor.reason;
  if (!missing) return explanation || factor.factor_id || 'Unspecified evidence.';

  const factorName = factor.factor_id
    ? `${factor.factor_id.charAt(0).toUpperCase()}${factor.factor_id.slice(1).replaceAll('_', ' ')}`
    : 'Evidence';
  return `${factorName}: ${explanation || 'Unavailable.'}`;
}

export function buildAssessmentView(assessment = {}) {
  const scoreRange = Array.isArray(assessment.score_range) ? assessment.score_range : [];
  const coverage = Number(assessment.coverage_pct);

  return {
    tone: POSTURE_TONES[String(assessment.posture || '').toUpperCase()] || 'neutral',
    rangeLabel: scoreRange.length >= 2
      ? `${formatScore(scoreRange[0])} to ${formatScore(scoreRange[1])}`
      : 'Score range unavailable',
    coverageLabel: Number.isFinite(coverage)
      ? `${Math.round(coverage)}% evidence coverage`
      : 'Evidence coverage unavailable',
    positives: (assessment.positive_factors || []).map(factor => formatFactor(factor)),
    negatives: (assessment.negative_factors || []).map(factor => formatFactor(factor)),
    missing: (assessment.missing_evidence || []).map(factor => formatFactor(factor, true)),
  };
}
