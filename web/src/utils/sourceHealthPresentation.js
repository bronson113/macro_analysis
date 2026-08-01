const ERROR_LABELS = {
  network: 'Network error',
  parse: 'Parse error',
  validation: 'Validation error',
  unknown: 'Unknown error',
};

function isStale(value) {
  return value === true || ['true', '1', 'yes'].includes(String(value).toLowerCase());
}

function formatFetchTime(value) {
  const date = value ? new Date(value) : null;
  if (!date || Number.isNaN(date.getTime())) return 'Unavailable';

  return date.toISOString().replace('T', ' ').replace('.000Z', ' UTC');
}

export function buildSourceHealthView(record = {}) {
  const statusLabel = String(record.status || 'UNKNOWN').toUpperCase();
  const statusTone = statusLabel === 'CURRENT'
    ? 'positive'
    : statusLabel === 'ERROR'
      ? 'negative'
      : 'neutral';
  const source = record.source || 'Unknown source';
  const fetchKey = record.fetch_key || 'Unknown fetch key';
  const errorCategory = String(record.error_category || '').toLowerCase();

  return {
    sourceLabel: `${source} · ${fetchKey}`,
    statusLabel,
    statusTone,
    freshnessLabel: isStale(record.is_stale) ? 'Stale' : 'Current',
    errorLabel: ERROR_LABELS[errorCategory] || 'No error recorded',
    message: record.message || 'No provider message recorded.',
    fetchTimeLabel: formatFetchTime(record.fetch_time),
  };
}
