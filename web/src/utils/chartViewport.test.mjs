import test from 'node:test';
import assert from 'node:assert/strict';

import {
  createTrailingViewport,
  getWheelAnchorRatio,
  getVisibleViewport,
  updateViewportWithWheel,
} from './chartViewport.js';

test('createTrailingViewport returns a latest-anchored window', () => {
  assert.deepEqual(createTrailingViewport(90, 500), { start: 410, end: 500 });
  assert.deepEqual(createTrailingViewport(900, 500), { start: 0, end: 500 });
});

test('updateViewportWithWheel zooms around the cursor anchor', () => {
  const viewport = updateViewportWithWheel({
    viewport: { start: 100, end: 500 },
    length: 1000,
    deltaY: -100,
    anchorRatio: 0.25,
  });

  assert.equal(viewport.start, 110);
  assert.equal(viewport.end, 470);
});

test('getWheelAnchorRatio clamps the pointer position inside chart bounds', () => {
  assert.equal(getWheelAnchorRatio({ clientX: 150, left: 100, width: 200 }), 0.25);
  assert.equal(getWheelAnchorRatio({ clientX: 40, left: 100, width: 200 }), 0);
  assert.equal(getWheelAnchorRatio({ clientX: 340, left: 100, width: 200 }), 1);
  assert.equal(getWheelAnchorRatio({ clientX: 150, left: 100, width: 0 }), 0.5);
});

test('updateViewportWithWheel pans with horizontal wheel movement', () => {
  const viewport = updateViewportWithWheel({
    viewport: { start: 100, end: 500 },
    length: 1000,
    deltaX: 120,
  });

  assert.deepEqual(viewport, { start: 113, end: 513 });
});

test('getVisibleViewport clamps against available data and minimum window', () => {
  assert.deepEqual(getVisibleViewport({ start: -10, end: 2 }, 100), { start: 0, end: 30 });
  assert.deepEqual(getVisibleViewport({ start: 980, end: 1030 }, 1000), { start: 950, end: 1000 });
});
