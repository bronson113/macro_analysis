import test from 'node:test';
import assert from 'node:assert/strict';
import { getNextTabIndex } from './keyboardNavigation.js';

test('getNextTabIndex wraps arrow-key movement across tabs', () => {
  assert.equal(getNextTabIndex({ key: 'ArrowRight', currentIndex: 2, tabCount: 3 }), 0);
  assert.equal(getNextTabIndex({ key: 'ArrowLeft', currentIndex: 0, tabCount: 3 }), 2);
});

test('getNextTabIndex moves to the first and last tabs with Home and End', () => {
  assert.equal(getNextTabIndex({ key: 'Home', currentIndex: 1, tabCount: 3 }), 0);
  assert.equal(getNextTabIndex({ key: 'End', currentIndex: 1, tabCount: 3 }), 2);
});

test('getNextTabIndex leaves unrelated keys unchanged', () => {
  assert.equal(getNextTabIndex({ key: 'Enter', currentIndex: 1, tabCount: 3 }), null);
});
