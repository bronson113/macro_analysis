const YEARS_TO_AGGREGATE = 3;

const parseUtcDate = (value) => {
  if (typeof value !== 'string') return null;

  const match = /^(\d{4})-(\d{2})-(\d{2})$/.exec(value);
  if (!match) return null;

  const [, year, month, day] = match;
  const date = new Date(Date.UTC(Number(year), Number(month) - 1, Number(day)));
  if (
    date.getUTCFullYear() !== Number(year) ||
    date.getUTCMonth() !== Number(month) - 1 ||
    date.getUTCDate() !== Number(day)
  ) {
    return null;
  }

  return date;
};

const exceedsThreeCalendarYears = (firstDate, lastDate) => {
  const anniversaryYear = firstDate.getUTCFullYear() + YEARS_TO_AGGREGATE;
  const anniversaryMonth = firstDate.getUTCMonth();
  const lastDayOfAnniversaryMonth = new Date(Date.UTC(
    anniversaryYear,
    anniversaryMonth + 1,
    0,
  )).getUTCDate();
  const anniversary = new Date(Date.UTC(
    anniversaryYear,
    anniversaryMonth,
    Math.min(firstDate.getUTCDate(), lastDayOfAnniversaryMonth),
  ));

  return lastDate > anniversary;
};

const getWeekKey = (date) => {
  const weekEnd = new Date(date);
  weekEnd.setUTCDate(date.getUTCDate() + ((7 - date.getUTCDay()) % 7));
  return weekEnd.toISOString().slice(0, 10);
};

export const prepareChartData = (points) => {
  const validDates = points
    .map((point) => parseUtcDate(point.date))
    .filter(Boolean);

  if (validDates.length < 2 || !exceedsThreeCalendarYears(validDates[0], validDates.at(-1))) {
    return points;
  }

  const numericFields = new Set();
  for (const point of points) {
    for (const [field, value] of Object.entries(point)) {
      if (field !== 'date' && field !== '__index' && Number.isFinite(value)) {
        numericFields.add(field);
      }
    }
  }

  const rows = [];
  const buckets = new Map();
  for (const point of points) {
    const date = parseUtcDate(point.date);
    if (!date) {
      rows.push({ type: 'point', value: point });
      continue;
    }

    const key = getWeekKey(date);
    let bucket = buckets.get(key);
    if (!bucket) {
      bucket = { date: point.date, sums: {}, counts: {} };
      buckets.set(key, bucket);
      rows.push({ type: 'bucket', value: bucket });
    }

    bucket.date = point.date;
    for (const field of numericFields) {
      if (Number.isFinite(point[field])) {
        bucket.sums[field] = (bucket.sums[field] ?? 0) + point[field];
        bucket.counts[field] = (bucket.counts[field] ?? 0) + 1;
      }
    }
  }

  return rows.map(({ type, value }) => {
    if (type === 'point') return value;

    const row = { date: value.date };
    for (const field of numericFields) {
      row[field] = value.counts[field] ? value.sums[field] / value.counts[field] : null;
    }
    return row;
  });
};
