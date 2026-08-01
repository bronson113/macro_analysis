const SECTION_PATTERN = /^##\s+\d+\.\s+/gm;

export const DASHBOARD_SECTIONS = Object.freeze([
  { key: 'editorial', headingId: 'editorial-review-heading', navLabel: 'Editorial Review' },
  { key: 'dailyBrief', headingId: 'big-update-heading', navLabel: 'Daily Brief' },
  { key: 'evidence', headingId: 'evidence-heading', navLabel: 'Evidence' },
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
