const SECTION_PATTERN = /^##\s+\d+\.\s+/gm;

export const DASHBOARD_SECTIONS = Object.freeze([
  { key: 'editorial', headingId: 'editorial-review-heading', navLabel: 'Editorial Review' },
  { key: 'dailyBrief', headingId: 'big-update-heading', navLabel: 'Daily Brief' },
  { key: 'trends', headingId: 'trends-heading', navLabel: 'Trends' },
  { key: 'indicators', headingId: 'indicators-heading', navLabel: 'Indicators' },
  { key: 'deepDive', headingId: 'deep-dive-heading', navLabel: 'Deep Dive' },
  { key: 'sourceHealth', headingId: 'source-health-heading', navLabel: 'Source Health' },
]);

function findSectionStart(markdown, titleIncludes) {
  const target = titleIncludes.toLowerCase();
  let match;

  SECTION_PATTERN.lastIndex = 0;
  while ((match = SECTION_PATTERN.exec(markdown)) !== null) {
    const lineEnd = markdown.indexOf('\n', match.index);
    const heading = markdown
      .slice(match.index, lineEnd === -1 ? markdown.length : lineEnd)
      .toLowerCase();

    if (heading.includes(target)) {
      return match.index;
    }
  }

  return -1;
}

function sliceSection(markdown, startIndex) {
  if (startIndex === -1) return '';

  SECTION_PATTERN.lastIndex = startIndex + 1;
  const nextMatch = SECTION_PATTERN.exec(markdown);
  return markdown.slice(startIndex, nextMatch?.index ?? markdown.length).trim();
}

export function splitReportSections(markdown) {
  const activeStart = findSectionStart(markdown, 'active macro situation');
  const risksStart = findSectionStart(markdown, 'market risk');
  const summary = activeStart === -1 ? markdown : markdown.slice(0, activeStart).trim();

  return {
    summary: summary || markdown,
    active: sliceSection(markdown, activeStart),
    risks: sliceSection(markdown, risksStart),
    full: markdown,
  };
}

function formatDateTime(date) {
  if (!date || Number.isNaN(date.getTime())) return 'Unavailable';

  return new Intl.DateTimeFormat(undefined, {
    dateStyle: 'medium',
    timeStyle: 'short',
  }).format(date);
}

function formatAge(totalHours) {
  if (totalHours < 1) return '<1h old';
  if (totalHours < 24) return `${totalHours}h old`;

  const days = Math.floor(totalHours / 24);
  const hours = totalHours % 24;
  return hours ? `${days}d ${hours}h old` : `${days}d old`;
}

export function buildFreshnessStatus({ generatedAt, now = new Date() }) {
  const generatedDate = generatedAt ? new Date(generatedAt) : null;

  if (!generatedDate || Number.isNaN(generatedDate.getTime())) {
    return {
      tone: 'stale',
      label: 'Unknown',
      ageLabel: 'No timestamp',
      generatedLabel: 'Unavailable',
    };
  }

  const ageMs = Math.max(0, now.getTime() - generatedDate.getTime());
  const ageHours = Math.floor(ageMs / (1000 * 60 * 60));

  if (ageHours <= 24) {
    return {
      tone: 'fresh',
      label: 'Fresh',
      ageLabel: formatAge(ageHours),
      generatedLabel: formatDateTime(generatedDate),
    };
  }

  if (ageHours <= 48) {
    return {
      tone: 'aging',
      label: 'Aging',
      ageLabel: formatAge(ageHours),
      generatedLabel: formatDateTime(generatedDate),
    };
  }

  return {
    tone: 'stale',
    label: 'Stale',
    ageLabel: formatAge(ageHours),
    generatedLabel: formatDateTime(generatedDate),
  };
}

const REGIME_SECTION_ORDER = Object.freeze([
  { key: 'currentState', label: 'Current State' },
  { key: 'momentum', label: 'Momentum' },
  { key: 'consensus', label: 'Consensus' },
  { key: 'interpretation', label: 'Interpretation' },
  { key: 'dataQuality', label: 'Data Quality' },
]);

const POLICY_LEVEL_HELP = 'Policy level uses the real-policy gap: real policy rate minus neutral real rate (r-star). A gap above +0.50 pp is restrictive; below -0.50 pp is accommodative.';
const LIQUIDITY_LEVEL_HELP = 'Liquidity level uses normalized reserve liquidity as a share of GDP against a trailing historical sample. Below P40 is scarce; above P60 is abundant.';
const MOMENTUM_HELP = 'Momentum is a separate 30-day or 90-day change overlay. It does not change the current level or quadrant.';
const CONSENSUS_HELP = 'Consensus is an optional, forward-looking survey overlay. Missing or stale consensus never changes the current state.';

function isRecord(value) {
  return Boolean(value) && typeof value === 'object' && !Array.isArray(value);
}

function asRecord(value) {
  return isRecord(value) ? value : {};
}

function mergeRecords(...values) {
  return Object.assign({}, ...values.map(asRecord));
}

function firstPresent(...values) {
  return values.find(value => value !== undefined && value !== null && value !== '') ?? null;
}

function sectionData(sections, label) {
  if (Array.isArray(sections)) {
    const match = sections.find(section => (
      String(section?.name ?? section?.label ?? '').toLowerCase() === label.toLowerCase()
    ));
    return asRecord(match?.data ?? match?.value);
  }

  return asRecord(sections?.[label] ?? sections?.[label.toLowerCase()]);
}

function titleCase(value) {
  if (value === undefined || value === null || value === '') return 'Unavailable';
  return String(value)
    .toLowerCase()
    .replace(/[_-]+/g, ' ')
    .replace(/(^|\s)([a-z])/g, (_, prefix, character) => `${prefix}${character.toUpperCase()}`);
}

function stateFrom(...values) {
  const value = firstPresent(...values);
  if (isRecord(value)) return firstPresent(value.state, value.level, value.policy_state, value.liquidity_state);
  return value;
}

function formatNumber(value, digits = 2, suffix = '') {
  if (value === undefined || value === null || value === '') return 'Unavailable';
  const number = Number(value);
  if (!Number.isFinite(number)) return 'Unavailable';
  return `${new Intl.NumberFormat('en-US', {
    minimumFractionDigits: digits,
    maximumFractionDigits: digits,
  }).format(number)}${suffix}`;
}

function formatSignedNumber(value, digits = 2, suffix = '') {
  if (value === undefined || value === null || value === '') return 'Unavailable';
  const number = Number(value);
  if (!Number.isFinite(number)) return 'Unavailable';
  const sign = number > 0 ? '+' : '';
  return `${sign}${formatNumber(number, digits, suffix)}`;
}

function formatDateValue(value) {
  if (value === undefined || value === null || value === '') return 'Unavailable';
  const parsed = new Date(value);
  return Number.isNaN(parsed.getTime()) ? String(value) : parsed.toISOString().slice(0, 10);
}

function detail(label, value, help) {
  return { label, value, ...(help ? { help } : {}) };
}

function readMomentum(axis, horizon, momentum, measurement) {
  const axisOverlay = asRecord(momentum[axis]);
  return firstPresent(
    axisOverlay[`${horizon}d`],
    axisOverlay[horizon],
    momentum[`${axis}_${horizon}d`],
    measurement[`momentum_${horizon}d`],
  );
}

function readMomentumValue(axis, horizon, momentum, measurement) {
  const axisOverlay = asRecord(momentum[axis]);
  return firstPresent(
    axisOverlay[`${horizon}d_value`],
    axisOverlay[`${horizon}_value`],
    momentum[`${axis}_${horizon}d_value`],
    measurement[`momentum_${horizon}d_value`],
  );
}

function normalizeRegime(input) {
  const payload = asRecord(input);
  const regime = isRecord(payload.macro_regime) ? payload.macro_regime : payload;
  const sections = payload.macro_regime_sections ?? regime.macro_regime_sections ?? regime.sections;
  const currentSection = sectionData(sections, 'Current State');
  const momentumSection = sectionData(sections, 'Momentum');
  const consensusSection = sectionData(sections, 'Consensus');
  const interpretationSection = sectionData(sections, 'Interpretation');
  const dataQualitySection = sectionData(sections, 'Data Quality');
  const currentState = mergeRecords(regime.current_state, currentSection);
  const currentPolicy = isRecord(currentState.policy) ? currentState.policy : {};
  const currentLiquidity = isRecord(currentState.liquidity) ? currentState.liquidity : {};
  const policy = mergeRecords(currentPolicy, regime.policy, currentState.policy_measurement);
  const liquidity = mergeRecords(currentLiquidity, regime.liquidity, currentState.liquidity_measurement);
  const quadrant = mergeRecords(payload.macro_situation, regime.quadrant, currentState.quadrant, interpretationSection);
  const momentum = mergeRecords(regime.momentum, momentumSection);
  const consensus = mergeRecords(regime.consensus, consensusSection);
  const dataQuality = mergeRecords(regime.data_quality, dataQualitySection);
  const available = Boolean(
    Object.keys(regime).length
    || Object.keys(currentSection).length
    || Object.keys(momentumSection).length
    || Object.keys(consensusSection).length
    || Object.keys(interpretationSection).length
    || Object.keys(dataQualitySection).length
    || Object.keys(asRecord(payload.macro_situation)).length
  );

  return {
    regime,
    currentState,
    policy,
    liquidity,
    momentum,
    consensus,
    quadrant,
    dataQuality,
    available,
  };
}

function buildCurrentStateSection({ currentState, policy, liquidity, quadrant }) {
  const policyState = stateFrom(
    currentState.policy_state,
    currentState.policy_level,
    currentState.policy,
    policy.state,
    quadrant.policy_state,
  );
  const liquidityState = stateFrom(
    currentState.liquidity_state,
    currentState.liquidity_level,
    currentState.liquidity,
    liquidity.state,
    quadrant.liquidity_state,
  );
  const situationId = firstPresent(currentState.situation_id, quadrant.situation_id);
  const situationLabel = situationId === null ? '' : ` · Situation ${situationId}`;
  const policyGap = firstPresent(policy.policy_gap, policy.policy_gap_pct);
  const percentile = firstPresent(
    liquidity.current_percentile,
    liquidity.liquidity_percentile,
    liquidity.historical_percentile,
  );
  const p40 = firstPresent(liquidity.historical_p40, liquidity.threshold_40, liquidity.historical_40th_percentile);
  const p60 = firstPresent(liquidity.historical_p60, liquidity.threshold_60, liquidity.historical_60th_percentile);
  const policyHistoryStart = firstPresent(policy.history_start, policy.history_sample_start);
  const policyHistoryEnd = firstPresent(policy.history_end, policy.history_sample_end);
  const liquidityHistoryStart = firstPresent(liquidity.history_start, liquidity.history_sample_start);
  const liquidityHistoryEnd = firstPresent(liquidity.history_end, liquidity.history_sample_end);

  return {
    key: 'currentState',
    label: 'Current State',
    value: `${titleCase(policyState)} + ${titleCase(liquidityState)}${situationLabel}`,
    details: [
      detail('Policy level', titleCase(policyState), POLICY_LEVEL_HELP),
      detail('Real-policy gap', formatSignedNumber(policyGap, 2, ' pp'), POLICY_LEVEL_HELP),
      detail('Policy history', `${formatDateValue(policyHistoryStart)} to ${formatDateValue(policyHistoryEnd)} · ${formatNumber(policy.history_count, 0)} observations`),
      detail('Liquidity level', titleCase(liquidityState), LIQUIDITY_LEVEL_HELP),
      detail('Normalized liquidity', formatNumber(firstPresent(liquidity.normalized_liquidity_pct_gdp, liquidity.normalized_liquidity), 2, '% of GDP'), LIQUIDITY_LEVEL_HELP),
      detail('Historical percentile', formatNumber(percentile, 1, 'th percentile'), LIQUIDITY_LEVEL_HELP),
      detail('Historical thresholds', `P40 ${formatNumber(p40, 2)} · P60 ${formatNumber(p60, 2)}`, LIQUIDITY_LEVEL_HELP),
      detail('Liquidity history', `${formatDateValue(liquidityHistoryStart)} to ${formatDateValue(liquidityHistoryEnd)} · ${formatNumber(firstPresent(liquidity.history_count, liquidity.history_sample_count), 0)} observations`),
    ],
  };
}

function buildMomentumSection({ momentum, policy, liquidity }) {
  const details = [30, 90].flatMap(horizon => [
    detail(
      `Policy ${horizon}d`,
      `${titleCase(readMomentum('policy', horizon, momentum, policy))} (${formatSignedNumber(readMomentumValue('policy', horizon, momentum, policy), 3, ' pp')})`,
      MOMENTUM_HELP,
    ),
    detail(
      `Liquidity ${horizon}d`,
      `${titleCase(readMomentum('liquidity', horizon, momentum, liquidity))} (${formatSignedNumber(readMomentumValue('liquidity', horizon, momentum, liquidity), 3, ' pp of GDP')})`,
      MOMENTUM_HELP,
    ),
  ]);

  return {
    key: 'momentum',
    label: 'Momentum',
    value: details.map(item => `${item.label}: ${item.value}`).join(' · '),
    details,
    summary: '30-day and 90-day momentum are separate overlays; neither changes the current level-based quadrant.',
  };
}

function buildConsensusSection({ consensus }) {
  const quality = firstPresent(consensus.quality, consensus.status);
  const policyDirection = firstPresent(consensus.policy_direction, consensus.policy);
  const balanceSheetDirection = firstPresent(consensus.balance_sheet_direction, consensus.balance_sheet);
  const hasDirection = policyDirection !== null || balanceSheetDirection !== null;
  const qualityLabel = titleCase(quality);
  const value = hasDirection
    ? `Policy ${titleCase(policyDirection)} · Fed balance-sheet ${titleCase(balanceSheetDirection)} · Quality ${qualityLabel}`
    : `${qualityLabel} · optional overlay; current state unchanged`;

  return {
    key: 'consensus',
    label: 'Consensus',
    value,
    details: [
      detail('Policy consensus', titleCase(policyDirection), CONSENSUS_HELP),
      detail('Fed balance-sheet consensus', titleCase(balanceSheetDirection), CONSENSUS_HELP),
      detail('Survey quality', qualityLabel, CONSENSUS_HELP),
      detail('Survey / target dates', `${formatDateValue(firstPresent(consensus.selected_survey_date, consensus.survey_date))} / ${formatDateValue(firstPresent(consensus.selected_target_date, consensus.target_date))}`),
      ...(Array.isArray(consensus.reasons) && consensus.reasons.length
        ? [detail('Consensus reasons', consensus.reasons.join('; '))]
        : []),
    ],
    summary: 'Consensus is forward-looking and optional. Unavailable or stale survey data never changes the current state.',
  };
}

function buildInterpretationSection({ quadrant }) {
  const favored = Array.isArray(quadrant.favored_sectors) ? quadrant.favored_sectors.join(', ') : 'None listed';
  const disfavored = Array.isArray(quadrant.disfavored_sectors) ? quadrant.disfavored_sectors.join(', ') : 'None listed';
  return {
    key: 'interpretation',
    label: 'Interpretation',
    value: firstPresent(quadrant.description, quadrant.name, 'No structured interpretation is available.'),
    details: [
      detail('Favored sector hypotheses', favored),
      detail('Disfavored sector hypotheses', disfavored),
    ],
    summary: 'Sector mappings are research hypotheses; independent evidence and source health remain visible elsewhere on the dashboard.',
  };
}

function buildDataQualitySection({ dataQuality, policy, liquidity, regime, quadrant }) {
  const quality = firstPresent(dataQuality.quality, dataQuality.overall, regime.quality, quadrant.quality);
  const reasons = [
    ...(Array.isArray(dataQuality.reasons) ? dataQuality.reasons : []),
    ...(Array.isArray(dataQuality.policy_reasons) ? dataQuality.policy_reasons : []),
    ...(Array.isArray(dataQuality.liquidity_reasons) ? dataQuality.liquidity_reasons : []),
    ...(Array.isArray(regime.missing_inputs) ? regime.missing_inputs : []),
    ...(Array.isArray(regime.conflicts) ? regime.conflicts : []),
  ].filter(Boolean).filter((reason, index, values) => values.indexOf(reason) === index);
  const ages = firstPresent(dataQuality.input_ages, dataQuality.ages);
  const ageText = isRecord(ages)
    ? Object.entries(ages)
      .filter(([, age]) => age !== null && age !== undefined)
      .map(([name, age]) => `${name} ${age}d`)
      .join(' · ') || 'Unavailable'
    : 'Unavailable';

  return {
    key: 'dataQuality',
    label: 'Data Quality',
    value: `Overall ${titleCase(quality)} · Policy ${titleCase(policy.quality)} · Liquidity ${titleCase(liquidity.quality)}`,
    details: [
      detail('Input ages', ageText),
      detail('Reasons and conflicts', reasons.length ? reasons.join('; ') : 'None reported'),
    ],
  };
}

/**
 * Format the structured regime for the dashboard without coupling formatting
 * to React. The exporter supplies both ``macro_regime`` and ordered
 * ``macro_regime_sections``; either shape is accepted for backwards safety.
 */
export function buildRegimePresentation(input = {}) {
  const normalized = normalizeRegime(input);
  const sections = [
    buildCurrentStateSection(normalized),
    buildMomentumSection(normalized),
    buildConsensusSection(normalized),
    buildInterpretationSection(normalized),
    buildDataQualitySection(normalized),
  ];

  return {
    available: normalized.available,
    sections: REGIME_SECTION_ORDER.map(({ key, label }) => {
      const section = sections.find(candidate => candidate.key === key);
      return { ...section, label };
    }),
  };
}
