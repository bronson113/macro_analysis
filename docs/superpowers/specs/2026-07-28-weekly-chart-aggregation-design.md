# Weekly Chart Aggregation for Long Historical Views

## Objective

Prevent lag in historical charts by replacing daily points with weekly averages whenever the currently displayed chart window is longer than three calendar years.

## Scope

- Apply the rule to every historical chart in `TrendGraphs`.
- Determine the rule from the active visible viewport, so it applies equally to range presets and wheel-zoomed custom ranges.
- Keep views of exactly three years or less at their existing daily granularity.
- Leave the history endpoint, stored data, range controls, and wheel interaction unchanged.

## Design

Add a small chart-data utility that accepts the visible history rows and returns chart-ready rows.

1. If the first-to-last visible date spans more than three calendar years, group the rows into calendar weeks.
2. For each weekly group, use the latest source date as the displayed date.
3. Average every numeric field independently, ignoring `null` or missing values. A field with no numeric values in a week remains `null`.
4. If the visible window is three calendar years or shorter, return the original daily rows without aggregation.

`TrendGraphs` will continue to calculate its viewport from the full daily dataset, then pass only its visible slice through this utility before supplying it to all four Recharts charts. This retains existing time-range and wheel-zoom behavior while limiting long views to roughly 52 points per year.

## Error Handling

- Empty input returns an empty array.
- Invalid or absent date values do not cause a crash; they remain ungrouped rather than being incorrectly placed in a calendar-week bucket.
- Non-numeric metadata such as `date` is never averaged.

## Testing

Add focused Node tests for:

- daily data remaining unchanged at exactly three years;
- daily data aggregating once the range exceeds three years;
- numeric averages, null handling, and the latest date label for a weekly bucket;
- aggregation applying based on the visible slice rather than the selected preset.

Run the web test suite, linter, and production build after implementation.
