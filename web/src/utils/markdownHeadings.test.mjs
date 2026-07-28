import test from 'node:test';
import assert from 'node:assert/strict';

import { getNestedMarkdownHeadingLevel } from './markdownHeadings.js';

test('getNestedMarkdownHeadingLevel nests report headings below their section heading', () => {
  assert.equal(getNestedMarkdownHeadingLevel(1), 3);
  assert.equal(getNestedMarkdownHeadingLevel(2), 4);
  assert.equal(getNestedMarkdownHeadingLevel(3), 5);
  assert.equal(getNestedMarkdownHeadingLevel(4), 6);
});

test('getNestedMarkdownHeadingLevel caps deep markdown headings at h6', () => {
  assert.equal(getNestedMarkdownHeadingLevel(5), 6);
  assert.equal(getNestedMarkdownHeadingLevel(6), 6);
});
