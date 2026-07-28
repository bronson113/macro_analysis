import test from 'node:test';
import assert from 'node:assert/strict';
import { prepareChartData } from './chartAggregation.js';

test('keeps a three-calendar-year chart range at daily granularity', () => {
  const points = [
    { date: '2020-01-01', sp500: 100 },
    { date: '2023-01-01', sp500: 200 },
  ];

  assert.equal(prepareChartData(points).length, 2);
});

test('aggregates one day past a leap-day calendar anniversary', () => {
  const points = [
    { date: '2020-02-29', sp500: 100, __index: 0 },
    { date: '2023-03-01', sp500: 200, __index: 1 },
  ];

  assert.deepEqual(prepareChartData(points), [
    { date: '2020-02-29', sp500: 100 },
    { date: '2023-03-01', sp500: 200 },
  ]);
});

test('averages numeric fields into calendar weeks over three years', () => {
  const points = [
    { date: '2020-01-01', sp500: 100, vix: 10, cpi_yoy: null },
    { date: '2020-01-02', sp500: 200, vix: null, cpi_yoy: 2 },
    { date: '2020-01-06', sp500: 300, vix: 30, cpi_yoy: 4 },
    { date: '2023-01-02', sp500: 400, vix: 40, cpi_yoy: 6 },
  ];

  assert.deepEqual(prepareChartData(points), [
    { date: '2020-01-02', sp500: 150, vix: 10, cpi_yoy: 2 },
    { date: '2020-01-06', sp500: 300, vix: 30, cpi_yoy: 4 },
    { date: '2023-01-02', sp500: 400, vix: 40, cpi_yoy: 6 },
  ]);
});

test('leaves invalid-date rows outside weekly buckets', () => {
  const points = [
    { date: 'not-a-date', sp500: 100 },
    { date: '2020-01-01', sp500: 200 },
    { date: '2023-01-02', sp500: 300 },
  ];

  assert.deepEqual(prepareChartData(points), [
    { date: 'not-a-date', sp500: 100 },
    { date: '2020-01-01', sp500: 200 },
    { date: '2023-01-02', sp500: 300 },
  ]);
});
